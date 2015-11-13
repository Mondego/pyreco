__FILENAME__ = browser
import subprocess
import platform

s1 = """
tell application "Google Chrome"
	set windowsList to windows as list
	repeat with currWindow in windowsList
		set tabsList to currWindow's tabs as list
		repeat with currTab in tabsList
			if "%s" is in currTab's URL then execute currTab javascript "%s"
		end repeat
	end repeat
end tell
"""

s2 = """
tell application "Safari"
	if (count of windows) is greater than 0 then
		set windowsList to windows as list
		repeat with currWindow in windowsList
			set tabsList to currWindow's tabs as list
			repeat with currTab in tabsList
				if "%s" is in currTab's URL then 
					tell currTab to do JavaScript "%s"
				end if
			end repeat
		end repeat
	end if
end tell
"""

s3 = """
window.location.reload()
"""

s4 = """
(function() {
	function updateQueryStringParameter(uri, key, value) {
	
	
		// console.log('updateQueryStringParameter')
		// console.log(uri)
		// console.log(key)
		// console.log(value)
		
		var re = new RegExp('([?|&])' + key + '=.*?(&|$)', 'i');
		separator = uri.indexOf('?') !== -1 ? '&' : '?';
		
		if (uri.match(re)) {
			return uri.replace(re, '$1' + separator + key + '=' + value + '$2');
		} else {
			return uri + separator + key + '=' + value;
		}
	}

	var links = document.getElementsByTagName('link'); 
	
	for (var i = 0; i < links.length;i++) { 
	
		var link = links[i];
		
		console.log('inspect', link);
		
		if (link.rel === 'stylesheet') {
			
			// Don't reload external urls, they likely did not change
			if (link.href.indexOf('127.0.0.1') == -1 && link.href.indexOf('localhost') == -1) {
				continue;
			}
			
			var updatedLink = updateQueryStringParameter(link.href, 'cactus.reload', new Date().getTime());
			
			// This is really hacky, but needed because the regex gets magically broken by piping it
			// through applescript. This replaces the first occurence of ? with & if there was no &.
			if (updatedLink.indexOf('?') == -1) {
				updatedLink = updatedLink.replace('&', '?');
			}
			
			link.href = updatedLink;
		}
	}
})()
"""

def applescript(input):
	
	# Bail if we're not on mac os for now
	if platform.system() != "Darwin":
		return
	
	command = "osascript<<END%sEND" % input
	return subprocess.check_output(command, shell=True)

def _insertJavascript(urlMatch, js):
	
	apps = appsRunning(['Safari', 'Google Chrome'])
	
	if apps['Google Chrome']:
		try: applescript(s1 % (urlMatch, js))
		except Exception, e: pass
	
	if apps['Safari']:
		try: applescript(s2 % (urlMatch, js))
		except Exception, e: pass

def browserReload(url):
	_insertJavascript(url, s3)

def browserReloadCSS(url):
	_insertJavascript(url, s4)

def appsRunning(l):
	psdata = subprocess.check_output(['ps aux'], shell=True)
	retval = {}
	for app in l: retval[app] = app in psdata
	return retval

########NEW FILE########
__FILENAME__ = cli
#!/usr/bin/env python
# encoding: utf-8

import sys
import os
import time

import cactus

def create(path):
	"Creates a new project at the given path."
	
	if os.path.exists(path):
		if raw_input('Path %s exists, move aside (y/n): ' % path) == 'y':
			os.rename(path, '%s.%s.moved' % (path, int(time.time())))
		else:
			sys.exit()
	
	site = cactus.Site(path)
	site.bootstrap()


def build(path):
	"Build a cactus project"
	
	site = cactus.Site(path)
	site.verify()
	site.build()

def serve(path, port=8000, browser=True):
	"Serve the project and watch changes"
	
	site = cactus.Site(path)
	site.verify()
	site.serve(port=port, browser=browser)

def deploy(path):
	"Upload the project to S3"
	
	site = cactus.Site(path)
	site.verify()
	site.upload()

def help():
	print
	print 'Usage: cactus [create|build|serve|deploy]'
	print
	print '    create: Create a new website skeleton at path'
	print '    build: Rebuild your site from source files'
	print '    serve <port>: Serve you website at local development server'
	print '    deploy: Upload and deploy your site to S3'
	print

def exit(msg):
	print msg
	sys.exit()

def main():
	
	command = sys.argv[1] if len(sys.argv) > 1 else None
	option1 = sys.argv[2] if len(sys.argv) > 2 else None
	option2 = sys.argv[3] if len(sys.argv) > 3 else None
	
	# If we miss a command we exit and print help
	if not command:
		help()
		sys.exit()

	# Run the command
	if command == 'create':
		if not option1: exit('Missing path')
		create(option1)

	elif command == 'build':
		build(os.getcwd())

	elif command == 'serve':
		
		if option1:
			try: option1 = int(option1)
			except: exit('port should be a round number like 5000, 8000, 8080')
		else:
			option1 = 8000

		browser = False if option2 == '-n' else True

		serve(os.getcwd(), port=option1, browser=browser)

	elif command == 'deploy':
		deploy(os.getcwd())

	else:
		print 'Unknown command: %s' % command
		help()

if __name__ == "__main__":
	sys.exit(main())
########NEW FILE########
__FILENAME__ = config
import json

class Config(object):
	
	def __init__(self, path):
		self.path = path
		self.load()
	
	def get(self, key):
		return self._data.get(key, None)
	
	def set(self, key, value):
		self._data[key] = value
	
	def load(self):
		try:
			self._data = json.load(open(self.path, 'r'))
		except:
			self._data = {}
	
	def write(self):
		json.dump(self._data, open(self.path, 'w'), sort_keys=True, indent=4)
########NEW FILE########
__FILENAME__ = file
import os
import codecs
import logging
import hashlib
import mime
import socket

from .utils import compressString, getURLHeaders, fileSize, retry, memoize

class File(object):
	
	CACHE_EXPIRATION = 60 * 60 * 24 * 7 # One week
	COMPRESS_TYPES = ['html', 'css', 'js', 'txt', 'xml', 'ttf', 'svg', 'eot']
	COMPRESS_MIN_SIZE = 1024 # 1kb
	PROGRESS_MIN_SIZE = (1024 * 1024) / 2 # 521 kb
	
	def __init__(self, site, path):
		self.site = site
		self.path = path

		self.paths = {
			'full': os.path.join(site.path, '.build', self.path)
		}
	
	def data(self):
		if not hasattr(self, '_data'):
			f = open(self.paths['full'], 'r')
			self._data = f.read()
			f.close()
		return self._data
	
	# @memoize
	def payload(self):
		"""
		The representation of the data that should be uploaded to the
		server. This might be compressed based on the content type and size.
		"""
		if not hasattr(self, '_payload'):
			if self.shouldCompress():
				self._payload = compressString(self.data())
			else:
				self._payload = self.data()
				
		return self._payload

			
		return self.data()
	
	def checksum(self):
		"""
		An amazon compatible md5 of the payload data.
		"""
		return hashlib.md5(self.payload()).hexdigest()
	
	def remoteChecksum(self):
		return getURLHeaders(self.remoteURL()).get('etag', '').strip('"')
		
	def remoteURL(self):
		return 'http://%s/%s' % (self.site.config.get('aws-bucket-website'), self.path)
	
	def extension(self):
		return os.path.splitext(self.path)[1].strip('.').lower()
		
	def shouldCompress(self):
		
		if not self.extension() in self.COMPRESS_TYPES:
			return False
		
		if len(self.data()) < self.COMPRESS_MIN_SIZE:
			return False
		
		return True
	
	@retry(socket.error, tries=5, delay=3, backoff=2)
	def upload(self, bucket):
		
		self.lastUpload = 0
		headers = {'Cache-Control': 'max-age=%s' % self.CACHE_EXPIRATION}
		
		if self.shouldCompress():
			headers['Content-Encoding'] = 'gzip'
		
		changed = self.checksum() != self.remoteChecksum()
		
		if changed:
		
			# Show progress if the file size is big
			progressCallback = None
			progressCallbackCount = int(len(self.payload()) / (1024 * 1024))
		
			if len(self.payload()) > self.PROGRESS_MIN_SIZE:
				def progressCallback(current, total):
					if current > self.lastUpload:
						uploadPercentage = (float(current) / float(total)) * 100
						logging.info('+ %s upload progress %.1f%%' % (self.path, uploadPercentage))
						self.lastUpload = current
			
			# Create a new key from the file path and guess the mime type
			key = bucket.new_key(self.path)
			mimeType = mime.guess(self.path)
			
			if mimeType:
				key.content_type = mimeType
			
			# Upload the data
			key.set_contents_from_string(self.payload(), headers, 
				policy='public-read',
				cb=progressCallback,
				num_cb=progressCallbackCount)
 		
		op1 = '+' if changed else '-'
		op2 = ' (%s compressed)' % (fileSize(len(self.payload()))) if self.shouldCompress() else ''
		
		logging.info('%s %s - %s%s' % (op1, self.path, fileSize(len(self.data())), op2))
		
		return {'changed': changed, 'size': len(self.payload())}
		
		
########NEW FILE########
__FILENAME__ = listener
import os
import sys
import time
import thread

from .utils import fileList
from .utils import retry

class Listener(object):
	
	def __init__(self, path, f, delay=.5, ignore=None):
		self.path = path
		self.f = f
		self.delay = delay
		self.ignore = ignore
		self._pause = False
		self._checksums = {}
	
	def checksums(self):
		checksumMap = {}
		
		for f in fileList(self.path):
			
			if f.startswith('.'):
				continue
			
			if self.ignore and self.ignore(f) == True:
				continue
			
			try:
				checksumMap[f] = int(os.stat(f).st_mtime)
			except OSError, e:
				continue

		return checksumMap
	
	def run(self):
		# self._loop()
		t = thread.start_new_thread(self._loop, ())
	
	def pause(self):
		self._pause = True
	
	def resume(self):
		self._checksums = self.checksums()
		self._pause = False
	
	def _loop(self):
		
		self._checksums = self.checksums()
		
		while True and self._pause == False:
			self._run()
	
	@retry(Exception, tries=5, delay=0.5)
	def _run(self):
			
		oldChecksums = self._checksums
		newChecksums = self.checksums()
		
		result = {
			'added': [],
			'deleted': [],
			'changed': [],
		}
		
		for k, v in oldChecksums.iteritems():
			if k not in newChecksums:
				result['deleted'].append(k)
			elif v != newChecksums[k]:
				result['changed'].append(k)
		
		for k, v in newChecksums.iteritems():
			if k not in oldChecksums:
				result['added'].append(k)
			
		result['any'] = result['added'] + result['deleted'] + result['changed']
		
		if result['any']:
			self._checksums = newChecksums
			self.f(result)
		
		time.sleep(self.delay)
########NEW FILE########
__FILENAME__ = mime
import os
import mimetypes

MIMETYPE_MAP = {
	'.js': 'text/javascript',
	'.mov': 'video/quicktime',
	'.mp4': 'video/mp4',
	'.m4v': 'video/x-m4v',
	'.3gp': 'video/3gpp',
	'.woff': 'application/font-woff',
}

def guess(path):
	
	base, ext = os.path.splitext(path)
	
	if ext.lower() in MIMETYPE_MAP:
		return MIMETYPE_MAP[ext.lower()]
	
	suggested = mimetypes.guess_type(path)
	
	if suggested:
		return suggested[0]
	
	return 'application/octet-stream'

########NEW FILE########
__FILENAME__ = page
import os
import codecs
import logging

from .utils import parseValues

from django.template import Template, Context
from django.template import loader as templateLoader

class Page(object):
	
	def __init__(self, site, path):
		self.site = site
		self.path = path

		self.paths = {
			'full': os.path.join(self.site.path, 'pages', self.path),
			# 'build': os.path.join('.build', self.path),
			'full-build': os.path.join(site.paths['build'], self.path),
		}
		
	def data(self):
		f = codecs.open(self.paths['full'], 'r', 'utf-8')
		data = f.read()
		f.close()
		return data
	
	def context(self):
		"""
		The page context.
		"""
		
                # Site context, making a shallow-copy using dict so that the
                # things we add to this page's context below won't be added to
                # the site's context. if in the future we make non-top-level
                # changes to the page's context the shallow copy won't be
                # enough, we'd need to look at copy.deepcopy
		context = dict(self.site._contextCache)
		
		# Relative url context
		prefix = '/'.join(['..' for i in xrange(len(self.path.split('/')) - 1)]) or '.'
		
		context.update({
			'STATIC_URL': os.path.join(prefix, 'static'),
			'ROOT_URL': prefix,
			'PAGE_URL': self.path
		})
		
		# Page context (parse header)
		context.update(parseValues(self.data())[0])
		
		return Context(context)

	def render(self):
		"""
		Takes the template data with contect and renders it to the final output file.
		"""
		
		data = parseValues(self.data())[1]
		context = self.context()
		
		# Run the prebuild plugins, we can't use the standard method here because
		# plugins can chain-modify the context and data.
		for plugin in self.site._plugins:
			if hasattr(plugin, 'preBuildPage'):
				context, data = plugin.preBuildPage(self.site, self, context, data)

		return Template(data).render(context)

	def build(self):
		"""
		Save the rendered output to the output file.
		"""
		logging.info("Building %s", self.path)
		
		data = self.render()
		
		# Make sure a folder for the output path exists
		try: os.makedirs(os.path.dirname(self.paths['full-build']))
		except OSError: pass
		
		# Write the data to the output file
		f = codecs.open(self.paths['full-build'], 'w', 'utf-8')
		f.write(data)
		f.close()
		
		# Run all plugins
		self.site.pluginMethod('postBuildPage', self.site, self.paths['full-build'])

########NEW FILE########
__FILENAME__ = server
import os
import sys

import SimpleHTTPServer
import SocketServer

import mime

# See: https://github.com/koenbok/Cactus/issues/8
# class Server(SocketServer.ForkingMixIn, SocketServer.TCPServer):
#	allow_reuse_address = True

class Server(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	allow_reuse_address = True

class RequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
	
	def send_head(self):
		"""Common code for GET and HEAD commands.

		This sends the response code and MIME headers.

		Return value is either a file object (which has to be copied
		to the outputfile by the caller unless the command was HEAD,
		and must be closed by the caller under all circumstances), or
		None, in which case the caller has nothing further to do.

		"""
		
		path = self.translate_path(self.path)
		
		f = None
		if os.path.isdir(path):
			if not self.path.endswith('/'):
				# redirect browser - doing basically what apache does
				self.send_response(301)
				self.send_header("Location", self.path + "/")
				self.end_headers()
				return None
			for index in "index.html", "index.htm":
				index = os.path.join(path, index)
				if os.path.exists(index):
					path = index
					break
			# else:
			# 	return self.list_directory(path)
		
		try:
			# Always read in binary mode. Opening files in text mode may cause
			# newline translations, making the actual size of the content
			# transmitted *less* than the content-length!
			f = open(path, 'rb')
			
		except IOError:
			
			errorPagePath = self.translate_path('/error.html')
			
			if os.path.exists(errorPagePath):
				return self.send_content(404, 
					{"Content-type": "text/html"}, 
					open(errorPagePath, 'rb'))
			else:
				self.send_error(404, "File not found")
			return None
		
		fs = os.fstat(f.fileno())
		tp = self.guess_type(path)
		
		headers = {
			"Content-type": tp,
			"Content-Length": str(fs[6]),
			"Cache-Control": "no-cache, must-revalidate",
		}
		
		# Last-Modified", self.date_time_string(fs.st_mtime)
		
		return self.send_content(200, headers, f)
	
	def send_content(self, code, headers, fileHandler):
		
		self.send_response(code)
		
		for key, value in headers.iteritems():
			self.send_header(key, value)
		
		self.end_headers()
		
		return fileHandler
	
	def log_message(self, format, *args):
		sys.stdout.write("%s\n" % format%args)

	def log_request(self, code='', size=''):
		try:
			self.log_message('%s %s %s', str(code), 
				self.requestline.split(' ')[0], 
				self.requestline.split(' ')[1])
		except:
			pass

	def guess_type(self, path):
		return mime.guess(path)

########NEW FILE########
__FILENAME__ = site
import os, os.path
import sys
import shutil
import logging
import subprocess
import webbrowser
import getpass
import imp
import base64
import traceback
import socket
import tempfile
import tarfile
import zipfile
import urllib

import boto

from .config import Config
from .utils import *
from .page import Page
from .listener import Listener
from .file import File
from .server import Server, RequestHandler
from .browser import browserReload, browserReloadCSS


class Site(object):
	
	def __init__(self, path):
		
		self.path = path

		self.paths = {
			'config': os.path.join(path, 'config.json'),
			'build': os.path.join(path, '.build'),
			'pages': os.path.join(path, 'pages'),
			'templates': os.path.join(path, 'templates'),
			'plugins': os.path.join(path, 'plugins'),
			'static': os.path.join(path, 'static'),
			'script': os.path.join(os.getcwd(), __file__)
		}
		
		self.config = Config(self.paths['config'])
	
	def setup(self):
		"""
		Configure django to use both our template and pages folder as locations
		to look for included templates.
		"""
		try:
			from django.conf import settings
			settings.configure(
				TEMPLATE_DIRS=[self.paths['templates'], self.paths['pages']],
				INSTALLED_APPS=['django.contrib.markup']
			)
		except:
			pass
	
	def verify(self):
		"""
		Check if this path looks like a Cactus website
		"""
		for p in ['pages', 'static', 'templates', 'plugins']:
			if not os.path.isdir(os.path.join(self.path, p)):
				logging.info('This does not look like a (complete) cactus project (missing "%s" subfolder)', p)
				sys.exit()
	
	def bootstrap(self, skeleton=None):
		"""
		Bootstrap a new project at a given path. If provided, the skeleton argument will be used as the basis for the new cactus project, in place of the default skeleton. If provided, the argument can be a filesystem path to a directory, a tarfile, a zipfile, or a URL which retrieves a tarfile or a zipfile.
		"""
		
		skeletonArchive = skeletonFile = None
		if skeleton is None:
			from .skeleton import data
			logging.info("Building from data")
			temp = tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz')
			temp.write(base64.b64decode(data))
			temp.close()
			skeletonArchive = tarfile.open(name=temp.name, mode='r')
		elif os.path.isfile(skeleton):
			skeletonFile = skeleton
		else: 
			# Assume it's a URL
			skeletonFile, headers = urllib.urlretrieve(skeleton)

		if skeletonFile:
			if tarfile.is_tarfile(skeletonFile):
				skeletonArchive = tarfile.open(name=skeletonFile, mode='r')
			elif zipfile.is_zipfile(skeletonFile):
				skeletonArchive = zipfile.ZipFile(skeletonFile)
			else:
				logging.error("File %s is an unknown file archive type. At this time, skeleton argument must be a directory, a zipfile, or a tarball." % skeletonFile)
				sys.exit()

		if skeletonArchive:
			os.mkdir(self.path)
			skeletonArchive.extractall(path=self.path)
			skeletonArchive.close()
			logging.info('New project generated at %s', self.path)
		elif os.path.isdir(skeleton):
			shutil.copytree(skeleton, self.path)
			logging.info('New project generated at %s', self.path)
		else:
			logging.error("Cannot process skeleton '%s'. At this time, skeleton argument must be a directory, a zipfile, or a tarball." % skeleton)

	def context(self):
		"""
		Base context for the site: all the html pages.
		"""
		return {'CACTUS': {'pages': [p for p in self.pages() if p.path.endswith('.html')]}}
	
	def clean(self):
		"""
		Remove all build files.
		"""
		if os.path.isdir(self.paths['build']):
			shutil.rmtree(self.paths['build'])
	
	def build(self):
		"""
		Generate fresh site from templates.
		"""

		# Set up django settings
		self.setup()

		# Bust the context cache
		self._contextCache = self.context()
		
		# Load the plugin code, because we want fresh plugin code on build
		# refreshes if we're running the web server with listen.
		self.loadPlugins()
		
		logging.info('Plugins: %s', ', '.join([p.id for p in self._plugins]))

		self.pluginMethod('preBuild', self)
		
		# Make sure the build path exists
		if not os.path.exists(self.paths['build']):
			os.mkdir(self.paths['build'])
		
		# Copy the static files
		self.buildStatic()
		
		# Render the pages to their output files
		
		# Comment for non threaded building, crashes randomly
		multiMap = map
		
		multiMap(lambda p: p.build(), self.pages())
		
		self.pluginMethod('postBuild', self)
	
	def buildStatic(self):
		"""
		Copy static files to build folder. If platform supports symlinking
		(Windows doesn't, except for admins) we do that for speed instead.
		"""
		staticBuildPath = os.path.join(self.paths['build'], 'static')

    		if not hasattr(self, 'nosymlink') and callable(getattr(os, "symlink", None)):
			# If there is a folder, replace it with a symlink
			if os.path.lexists(staticBuildPath) and not os.path.exists(staticBuildPath):
				os.remove(staticBuildPath)
		
			if not os.path.lexists(staticBuildPath):
				os.symlink(self.paths['static'], staticBuildPath)
		else:
			try:
				if os.path.exists(staticBuildPath):
					shutil.rmtree(staticBuildPath) # copytree fails if destination exists

				shutil.copytree(self.paths['static'], staticBuildPath)
			except Exception:
				logging.info('*** Error copying %s to %s' % (self.paths['static'], staticBuildPath))
	
	def ignorePatterns(self):
		
		# Page filters
		defaultPatterns = [".*", "*~"]
		configPatterns  = self.config.get("ignore")
		
		# Add the config values to the default ignore list
		if type(configPatterns) is types.ListType:
			defaultPatterns += configPatterns
		
		return defaultPatterns
	
	def pages(self):
		"""
		List of pages.
		"""
		
		paths = fileList(self.paths['pages'], relative=True)

		# Filter out the ignored paths
		paths = filterPaths(paths, self.ignorePatterns())
		
		return [Page(self, p) for p in paths]

	def serve(self, browser=True, port=8000):
		"""
		Start a http server and rebuild on changes.
		"""
		self.clean()
		self.build()
	
		logging.info('Running webserver at 0.0.0.0:%s for %s' % (port, self.paths['build']))
		logging.info('Type control-c to exit')
	
		os.chdir(self.paths['build'])
		
		def rebuild(changes):
			logging.info('*** Rebuilding (%s changed)' % self.path)
			
			# We will pause the listener while building so scripts that alter the output
			# like coffeescript and less don't trigger the listener again immediately.
			self.listener.pause()
			try: self.build()
			except Exception, e: 
				logging.info('*** Error while building\n%s', e)
				traceback.print_exc(file=sys.stdout)
			
			# When we have changes, we want to refresh the browser tabs with the updates.
			# Mostly we just refresh the browser except when there are just css changes,
			# then we reload the css in place.
			if  len(changes["added"]) == 0 and \
				len(changes["deleted"]) == 0 and \
				set(map(lambda x: os.path.splitext(x)[1], changes["changed"])) == set([".css"]):
				browserReloadCSS('http://127.0.0.1:%s' % port)
			else:
				browserReload('http://127.0.0.1:%s' % port)
			
			self.listener.resume()
	
		self.listener = Listener(self.path, rebuild, ignore=lambda x: '/.build/' in x)
		self.listener.run()
		
		try:
			httpd = Server(("", port), RequestHandler)
		except socket.error, e:
			logging.info('Could not start webserver, port is in use. To use another port:')
			logging.info('  cactus serve %s' % (int(port) + 1))
			return
		
		if browser is True:
			webbrowser.open('http://127.0.0.1:%s' % port)

		try: 
			httpd.serve_forever() 
		except (KeyboardInterrupt, SystemExit):
			httpd.server_close() 

		logging.info('See you!')

	
	def upload(self):
		"""
		Upload the site to the server.
		"""

		# Make sure we have internet
		if not internetWorking():
			logging.info('There does not seem to be internet here, check your connection')
			return

		logging.debug('Start upload')
		
		self.clean()
		self.build()
		
		logging.debug('Start preDeploy')
		self.pluginMethod('preDeploy', self)
		logging.debug('End preDeploy')
		
		# Get access information from the config or the user
		awsAccessKey = self.config.get('aws-access-key') or \
			raw_input('Amazon access key (http://bit.ly/Agl7A9): ').strip()
		awsSecretKey = getpassword('aws', awsAccessKey) or \
			getpass._raw_input('Amazon secret access key (will be saved in keychain): ').strip()
		
		# Try to fetch the buckets with the given credentials
		connection = boto.connect_s3(awsAccessKey.strip(), awsSecretKey.strip())
		
		logging.debug('Start get_all_buckets')
		# Exit if the information was not correct
		try:
			buckets = connection.get_all_buckets()
		except:
			logging.info('Invalid login credentials, please try again...')
			return
		logging.debug('end get_all_buckets')
		
		# If it was correct, save it for the future
		self.config.set('aws-access-key', awsAccessKey)
		self.config.write()
	
		setpassword('aws', awsAccessKey, awsSecretKey)
	
		awsBucketName = self.config.get('aws-bucket-name') or \
			raw_input('S3 bucket name (www.yoursite.com): ').strip().lower()
	
		if awsBucketName not in [b.name for b in buckets]:
			if raw_input('Bucket does not exist, create it? (y/n): ') == 'y':
				
				logging.debug('Start create_bucket')
				try:
					self.bucket = connection.create_bucket(awsBucketName, policy='public-read')
				except boto.exception.S3CreateError, e:
					logging.info('Bucket with name %s already is used by someone else, please try again with another name' % awsBucketName)
					return
				logging.debug('end create_bucket')
				
				# Configure S3 to use the index.html and error.html files for indexes and 404/500s.
				self.bucket.configure_website('index.html', 'error.html')

				self.config.set('aws-bucket-website', self.bucket.get_website_endpoint())
				self.config.set('aws-bucket-name', awsBucketName)
				self.config.write()

				logging.info('Bucket %s was selected with website endpoint %s' % (self.config.get('aws-bucket-name'), self.config.get('aws-bucket-website')))
				logging.info('You can learn more about s3 (like pointing to your own domain) here: https://github.com/koenbok/Cactus')


			else: return
		else:
			
			# Grab a reference to the existing bucket
			for b in buckets:
				if b.name == awsBucketName:
					self.bucket = b

		self.config.set('aws-bucket-website', self.bucket.get_website_endpoint())
		self.config.set('aws-bucket-name', awsBucketName)
		self.config.write()
		
		logging.info('Uploading site to bucket %s' % awsBucketName)
		
		# Upload all files concurrently in a thread pool
		totalFiles = multiMap(lambda p: p.upload(self.bucket), self.files())
		changedFiles = [r for r in totalFiles if r['changed'] == True]
		
		self.pluginMethod('postDeploy', self)
		
		# Display done message and some statistics
		logging.info('\nDone\n')
		
		logging.info('%s total files with a size of %s' % \
			(len(totalFiles), fileSize(sum([r['size'] for r in totalFiles]))))
		logging.info('%s changed files with a size of %s' % \
			(len(changedFiles), fileSize(sum([r['size'] for r in changedFiles]))))
		
		logging.info('\nhttp://%s\n' % self.config.get('aws-bucket-website'))


	def files(self):
		"""
		List of build files.
		"""
		
		paths = fileList(self.paths['build'], relative=True)
		paths = filterPaths(paths, self.ignorePatterns())
		
		return [File(self, p) for p in paths]


	def loadPlugins(self, force=False):
		"""
		Load plugins from the plugins directory and import the code.
		"""
		
		plugins = []
		
		# Figure out the files that can possibly be plugins
		for pluginPath in fileList(self.paths['plugins']):
	
			if not pluginPath.endswith('.py'):
				continue

			if 'disabled' in pluginPath:
				continue
			
			pluginHandle = os.path.splitext(os.path.basename(pluginPath))[0]
			
			# Try to load the code from a plugin
			try:
				plugin = imp.load_source('plugin_%s' % pluginHandle, pluginPath)
			except Exception, e:
				logging.info('Error: Could not load plugin at path %s\n%s' % (pluginPath, e))
				sys.exit()
			
			# Set an id based on the file name
			plugin.id = pluginHandle
			
			plugins.append(plugin)
		
		# Sort the plugins by their defined order (optional)
		def getOrder(plugin):
			if hasattr(plugin, 'ORDER'):
				return plugin.ORDER
			return -1
		
		self._plugins = sorted(plugins, key=getOrder)
	
	def pluginMethod(self, method, *args, **kwargs):
		"""
		Run this method on all plugins
		"""
		
		if not hasattr(self, '_plugins'):
			self.loadPlugins()
		
		for plugin in self._plugins:
			if hasattr(plugin, method):
				getattr(plugin, method)(*args, **kwargs)

########NEW FILE########
__FILENAME__ = skeleton
data = """
H4sIAMRnT1IAA+09a3PbOJLz1fwB9xkjr4vSRKKethOP5T2P40w8k1fFzu5N
JTkdRUIWbYrUEKRtbS5V97vub9xvuKr7GdfdAEjq4XidVSTvLrtmYhEEGo1H
P9BogG/sm+fcdnlUd5Io4kHsetF3S4ZGo7G7vc2+2yXI/jYUtJpt1my1Wu3m
bmd7p8UgYbvZ+I7dLJuQRZCI2I6AlAtbhEE/DGJ7cb6z58fPDo+Of3r9+tcP
T8OR7QXsneCRyDUSgKV//06g+Zide263+Xh3p9ls7O4+Npq7LIGU9uNOe6cJ
42S0GsyJvRHvNtuPIcdOu7GDaXaa9qS9vd2GtDY7PXp+8uI3y+VX3eYOlG21
GrlkLwi729s7nXbrScOAilVy4HvBZXfHWHdX/FOCVf/2dWj+/y/4/S//979N
/Bv+T+2/GxlM8z/MnU7rO7b97Un7p+d/q/4m1QBj+5yLu4vcG+4v/xvbO+1C
/q8C1iT/m4X8fxhgSa7/plrg3vK/1Wh0moX8XwVMyX8/OfeC5WuAO+U/jLka
/522tP9hAVDI/1XA/eX/bqvRWij/24/Zi5OfDt+CVP/TseVEHHJAf85qjnto
iR2j+WRaSzRbhZpYKlia67+hBriH/Ff83+i02oX8XwXk5T/0ROw5y6/jK+z/
3e3C/l8JrMX+Rwyz9v92IdjXAZbi+m+5APgK+x9+F/J/FZCX/zEfjX07XroP
6P7yv9nZaRXyfxWwHvnf3J6T/+1C/q8DrIzrv5kK+Ar5v9tpFPJ/FZAf/0wT
9G3BrWE88pdSB/THTqdzH/nfbrc7hfxfBSxJ/qNEv4/8n7f/m4X8Xwfk+X+5
XJ+B5v//+m6h/G82t2f5v7WN8r+xZDoWwj85/+9/74ZOPBlzhgN/YOzrP6AI
DoyN/RGPbeYM7UjwuFtK4kHtcSlNH8bxuMZ/T7yrbunfau8Oa0fhaAxyoe/z
EnOgL3kAhU6Ou9w951VnGIUoMbLygQ3PpSuPX4/DKM4VufbceNgFMeI5vEYP
UAhKoaRgEfe7JTGEEk4SMw8Kldgw4oNu6dMndnp2eHZy1Hv39gX7/Lk+sK/w
vQX/lA7YNIJ44nMx5Dy+tbQjRJ2yWfCLCPi0xfp+6FyyIelJtvUZcMZe7POD
P3Pfgebt1+Uj5eWBK7NDPmO/Lvt0vx+6k4McLtVqQvYS55VKmEeRlRFO5I1j
IQmQD0xETrdUr9sX9o11HobnPrfHnrCAKkqr+15f1C9+T3g0qTetXaupHqyR
F1gX0MD9usR0MINzrmMuRB0ZYLbQDLn7ddlSaDjNqXVP9QIWQOr/yYw/mOzL
reMr1v/bncL/uxJYk/93d87+6xTyYR2Q8j8qu29Ux/3X/034r1j/rwIWyH9v
dL7cOr5G/rd2C/m/CliT/3c+/rvw/64FUv4Hrn9I8r+xXcj/VcAC+X/xAPb/
2juF/F8JrEn+twr7/2FAyv8XD2r/b6dTyP+VQH78MxVgnXuxdx6EEV9GHV+x
/9dpF/HfK4FlyP/dx5Dz8b3kf7vY/3sYkOf/5XJ9Bnfs/y2Q/60djP8u9v++
PSyW/2p3Z0l13F/+t3Zbhf9/JbCm+I9OIf8fBuT5f7lcn8Gd8n93jv+b6P8t
5P+3hz+U3dBJRjyIK1YEwn9SHiSBgwf3yhX2ydhwwkCEPrf88Lxces59P/y+
VPnR+Az/r5v0ApYAU/7fb7QA/Ir13/Zusf5bCaxp/Td//0Oh/9cCU/z/jRaA
X7H+290p1n8rgan4j4cj/3dw/6+Q/98e1iP/G48L+f8wYIr/H5D83y3WfyuB
W+R/Gva+jDq+Qv53iv3/1cB6/H+NJ4X8fxgwxf9L5foM7vb/Nef2f3D9X8j/
bw94RAf9fANo+R5rdsY39abV3uYjdhh5tl9lz7l/xWGC2FUm7EDUoM3e4Efj
87oJL2ApkN3/lTv97YfnlusJu+9z1xpP/tY6GveO/+u0dor130pgLfq/9WT+
/E+h/9cCGf8vm+szaHw5/q/Tae/O+f8bhf5fCXgjPHrNQmGoX64dc+Rs/Qyz
AqbHuWG8fvv0+C3rsidPnhhvXp+enfbeHJ49hwRzHIpYmOwRYLEEH8u38OL9
R8MYROGIuRd2cB5a+qYBplAf4Tnnm3hhHssP6YS1ynrO455+9aX8vdg+F7rQ
T3gS+VXo8io7vol54Ap8MAyXDxAhPpR1+ao8dX0TdxVV5UpVnk83RdK/4E5s
VvaMjVKpZGz8zGNV/fQJbsGIMpulRBkbeER+r45GtnMZXvFo4IfXdCT794QL
3GYV9dbO493mbrtubEiktWF4XXPsoObVgMqaXaNKaogbHtJekLQMwogF0BAG
81G/Ajo3vAHzBLB1bAcOLwfUCWl/VJgduFTMwiaybpeaiuU2Ih4nUSBfRtBn
PCqrnqnAa+4vQpzr3Uoeie5kWRP843siTnta9i9gjWxPcEDi8DFtPJewEDO3
YE45YeIjpTHrczYIEyA711CrxLYUEjmq44j/lHi+WxZejKQYG+d+2Ld9RlMS
HjcZvWe277N4yBlNXdmLeA82IseiFl2KXa6onsQnSIqHFgqLWFx78bCc8QBV
tAG4Ty+9MRAb0F0KEjdD1GHfCxPBIo4yRmBeQIqNyhBj/xFak27gMGU/4vZ7
7AUJVxU886ADbCbG3PEGnsOgzV7AXXZlg7EOcps6B5uFbdHdLIviiMfDKLyG
8td2FABPM6DimpsRZyNPCEqILcyNXQmI3TL1raIEGJrIdTR/ULJqCE0jvLpA
Zt5QUgNU/iAsl15q9PAkx5U6HPqHbQkcQ6qomnVHRSLX88g0jdyTY8G8UiVM
s6K6Ro2rbjXVwG1nSNVgFvyreBua8unzTNp7ky5uMD/CS2q7eq7M5bOTeBhG
uYwqYT4nytJcPnqcz4UNplxp8+ey4CqNsmiOysvDctZtSmSVMH9J98wbvLyD
poVLwjeIQ+gn+h2SZMNscTSRQ7e4AVorWOkPEUdj/FFeUADGZcutbY1qW7/J
9nLi7YzFq0wKm3SeqBlZLj1FsmDsRnZME8sJowhIZCmHbglYiA5JLIBIcN3a
aFSbTD4EaiKlfQFVqFk0xUPEtZY9HgPD5UmvkHA4RbWRygXWn1DDjQ2t0QS8
565k/Sq75JOub4/6rs1u9tiNbn1F5QfxCQJf8DLihgnAb7gAHDcRCHleblSZ
zwOJqoI5sIUe8pDKqqX4o2Y+UUqy995HmDeA/w3QSQOkkh81P6pitduKBdDa
2WI1KDYtQd9AP5IUlVyZE9rQSDtVhYeuS/2Fgp2FA9VvMMGw6ZMpOQSdB9KG
gWIzNmzH4UJgyZHUmddDTr3FQinASAirOpyUUcjOSMlWfUZiBJpKaVpgQ1rG
WDnOolmnEFrJ2CX2gcw4AFq85Bu6bvPsm8Oi9b8TDgacy2tdlrEiuL//f6fR
LOJ/VwJrWv8X+78PBDL+XzbXZ3CX/7+9M7v/u91q7hTr/1XA3Pp/7I25MAxY
yvPgyovC4L2JaxxSu2Y9EVG97wV78h98EvRLpM+wxrT9+syjGNoRrwfjEb0w
lakBendqtQaKeTTCdQrUJGcjqzlg8OVC1H+w5AsTbD2i1Po9CWNpqZCCF2As
I04yw9AfMRFgJ5cV5kohZGZgkf6Xl8f1HD8USQR/w9HY83n01ULh3vq/3Wh1
ivjflcCa9H+x//9AIOP/ZXN9Bnfo/ybw/Yz+3+10ivivlcAmw1t/Xb3u5jf2
aOzjmt3lcmUup4Wxya61z6XP4xg98wO5Ulc3kV7DAh7Xzg4sqQP432UDL0Jv
bz9Bl4odKwRecBX6V4jQDkJAAAt4moDKQckDlW9oX3F0JNi+H14z7lFWfjP2
PccDe4V2BvRvUFq4RbGJHgikaQATV2QIJ2FiZggFLPPH8DItR34LyQT4PkoC
y7K0OSSS/jgK0Vshtx3Qn5xuSsDvW0wZBoDOCXWNKjQPM5fNaWPmQqAds8h2
kRgQojCMe9JLr7BZkYCWx2WzalZZs/K+8THN7HKBzs3SltCXugL+FEOajZx9
LAdZKy1nyJ3LHhhtfvm9eWFf2VCJWbuwI/ybM+l8r19XssJSb2s1aFBVUame
e2ESj5O4h0MC75BAsMx0vcovmKv+CCrm7hv5dBxFYTRN6RhGLGbmL6fsSAoo
BvbdmA1sD0WUuW52+ruDRfbf0B75S47/uKf/p9PaKb7/vhJYU/zn/P1/hf23
Fsj4f9lcn8Fd9t/O7qz/p93ZLe7/XwloM2eSOoAyVxAagY4wwK56DiZYHO7B
L4Qf2Anu//s+wzkznrAyRjmIvXr9HMy0pE/xDRegv/nIA20e1Z9DtjeTSlrc
wnLKSruGLEwtNly0v2j/W740VPyIYztxIqwk9vw0uAMzvPCEih6RhFiKnjS+
RC5hDOPoxfHhq3dvVEzKokgBbbChHYbmmkY/5VmiqACyzlKbZDMM/Anlxrvv
sTlQHslIc6Rb/TO7/Lbc5c8bN9lOZYoez+SrHbYAOkSnY+keJUGb5DhZ4ZgH
Zbn1aaI9xgN4AfZt16TPNpjygH+5YpH5SIVxazKtSg0C4caBwHEwMtJkX0J1
ulvLmR0njTwiRa0alT0naSxn5Fam2jb2bYdT1+RRvcEx6MoeU3l0h0HTVHxE
Ds91BGNEnZROnfQljQf1jEJcNa/NCrMFG0z3/cAiNGXZlBx6NXf0nrFCk0ac
LLL8VdCJKjk3t1R6Vr80aqe7QUDTR+EVpxGVPZ2fxcvi/0X2n4+G+Hrtv3Zx
/nM1sCb7rzj//0Ag4/9lc30Gd+3/7Tbn7L/tRuH/Wwksx82FKleHAM46uvBg
2Q84ue7n69IoU2+XNeftEpGTy7jICYbfbfrbPGBIuCOdW2jbRNiOKta8NF9W
iapgMvqIYwhjEAa1v/AoBJQeIIRuTESVjX1uC86IOnRpRgwLguUOU/am9LXj
v0j/j23nEgOmliUM7tT/O+r8Xwt+7TZR/+8W339YDdxb/z9+0t55slD/tx+z
Fyc/Hb4Frf6nY8uBxQaGeuYsh91Wo/XXWwk7nSfFLbHfHDL+XzbXZ/Bl/Y8f
+27P8n+zXcT/rASUjh/aYuh7fe35AS0dxWHop64g+GN8yVUU8en4IfVwKASH
5TJNrEhaFn3RSc/ncDuJvUHin4bJGN1MOuf3+DuJBTs6PaVtvF/sK/tUbqVJ
r1HEBzzigcPpPAhpQ1r7x+E5p51CWOCHAYUtS6XNXcBZvvJs9tu7kzQ1jORR
mPy+ZVX6DMidwP2x3lOcaoplbKJXzL7C7UM/BEoh1/OzszdAGB3sEcwTuFvJ
A+FdcYud4P4m81xu++w6jHxX0kzx0bn9TiAZ8GKryaOEpEES+0U+A5rYFGiF
CfzEJvpooLUMjxXZ59gcqIphIDUV9ALHT1zORDiCLpH7o33vXO7Fetg9/oQF
nLu0+4unuydgYFF90BgiL7IjDpkS3CAm35fFzhA/EKEaDTjjCIyGcDCQG65D
nkSeALtPULA3NQ3KZ7vMA+qhwJlgLWlvYVHfu+S+NwxDV+7k2tjjgvU5drLK
ifZRDCbSOTQ1YHQQIZ01LLYvcdsXjEzaw7bHYIjZznAPsNv+5C/YtTiSCi/1
Azp1bIo6l2dFKNQdieknziWPZYS67ThhhJ407PHroQcZQ/S8ycKIVc06GmcZ
vo4UgBnqQLOrRFLMlS8qUMdzqP50HgtN1mH1p+oRbrejX7QP1KqRhik6gPkT
xDAgpFs5oQ3OfcRHPcDKOEsq5EYE+YQEo5O2DWThQR/ccnddkLRsFEaSCNrw
1vH2esN8QqUUEqJHVxApquiojWwIpcvxgpzpjIXHI6TO4fDXDbkIzJj9YPvX
9kT8oHud+gNKqXkd2DCoMl7Aw2iB6FJYeamAk/bV6zM8u8LRFUeTaARjixIj
h4KIuAC5DpM0vBQ0YQLgzpcvYK5yGXmA0QnnCfAM+hsBI/wKA+pqoBA7pZ8E
LnY8Mo7IxArGB3A3gWbpqUskPoPxQGzoIX8Df3l0hagjDzQrcDwNrYw3AMnB
TpMxyj+Y2j40DY9OqCgEzAdkU7/g6YNaEGY9/DS8DvCQo2QWlY6ScBTG6aQW
IXIuHrJIJwVxMo4v9A9yIdMXvMp66PUFHl2E9RF2OgogLTQFTQWQR/VfTqt4
piNAd7aHXa3EC8oZdOxiL/waAInAxiMvJtOPuqNpAeWACH3gQjac/WuqSnDt
QufGYOG5yVo0UyXBUtrTcU6QQjh9kBTIitNLjMNYn3Ub2dFlMq5KqjLZiNwl
uwA7lwSR3H+A9arDFWP7fo53z4Yeie1UYNI8gK69BgJweDyizYQZhq5iUBdp
8AvWJrGjzHek3BB4c4aQvAtL2n4Ivd3ng1DJZ3uAUTRYGZNxMKTAymGk64F8
bohkYB6JXYBMcoYTpu/slT5rnGkZ1RWYkcbmJjt5dXp2+OLF4dnJ61c4ECJx
Q9TOzFObN9PKeUGGvtbPAvRzx5Boj16/enby87u3hJdtoh58BtXDghpJzXoc
5hcFigzxeA5kcHk/obNeVYzAwV45ixKuxGmUBGK6rDw/RJIGWeY19tA1HhNV
hZ/ZviC5SGpMz3UoCLLBDycW+w3YYAS8rMN+HFg+BwwjfxIc8kAZEiA/Emjr
ZM94c3j06+HPx70Xr4+g237rPT3+6d3PrCtrMk5eHb149/S49/b45euz497h
6ekxnQijRmzi+SUtHwY4RHkeVSwKZGJfUGAU7m29PHl18uy33rOTF8evDl8e
n+qqAFuYthaHQaPRjg6R6Yac4YIMnQt/0hlxShhHr1++eXt8iqdVqY2a8LRV
r9+e/Hzy6vBFRk3v5FUPir08fpU2M+0htE9mkn5JUw7fnb3++fhVDyp8dvJv
FMp90zOhUWTRgFgZeDdqN4Sa5aZbfTRd0DfUi9ABFOFRU9pNKpv/Xv7j97jH
+J8f6h/qFbNigF0CTb7irhctyv3BegT5HkFGJRdp409Kql6aBH9wAww9Wz1P
vMDqnyEC2nFBV406EQa4RzYMajlPYZXJjRlZXPq6cGNIHZpT4pG8ZV0aV8Io
80HdobDU/hYhnNpmlJnwGGWaim4mlLw5rNKXNIfwAkTGonD4qspaydolE1QL
cKqALjylNNWIJPLz/TBLM7yuzjW9orsEcp2FEl3mM7wVJ5F9Rzfi/KpIDKoO
EN1PvSgbMOgijdATbv5NWqHaZeMwIlPpuhyUQt4p50cXqnnhBZeijIKQ0AFf
4n7mJU0jSLTwhG8PXYYmJptg88VxJLqfqAoQ5b65x8zsm/NmVb7AL8/DG5Ii
QPxiKYO0svzcg7KfK+zRbM2E3swN8HvJaaRhM4rVhrQ5bWGYmOnGIrI/Zu2W
q66Zlmu1N9d2+SJrPbB9Gh+KxoaIHFNuYpv4c2kNn6lWIX8FpgJk32SWZZFA
ztOCdl9ZSoQv9Jguca8+I8X6DBa7ZTBfJBPj8uqK5wQBTGLoPnhPh9nlPKig
nkyTsA2Ugs2QcxsKyTm7CdREI9v3/gJKwIlC9AMnfZi6YHuA1cnp6DLtH9MC
ldu0eilZ9RIiLFnwg/BIKkC+QenytEzFs/WK1zCnrD1//8E842vv9iZzhnjG
mZlZrOsgDE3UjmYd7Am/bvdF6Ccx15sEFkmp+nR+hU4SeZs8uVVwVaa4nOMV
FQKVJGok3IzA+GXoa30BhuIeOefMCyFrT2/2kGMlL8Q4UokqAELSZyrtsiXg
P2uLdjvKuc0BVX01F8JBLhdr5G6XdTUVa8hvXA/serx/ZL60SsnX+yU5q0cO
554enCklaMGCEMU4MgnOezKSwEbCawUiVSCLoCB5vyB8QodOpK0wMoaCMqk+
oEgOXIf9GVAqw9Mto9lbZeptb2SPpWaVfCOVJnA7tHTKXUTFJONSQVeqeLkd
BUOFnDkjt0FuLJRoTK3Purcxb9qPMl8g1x45inVXTMfvkMyKw96tOv+vU3dT
Sk6SEvDrnhz9KfU5XeFUn74n0j+mLdEYsna4GffKwBO5YsZbW37EZTBITRuX
g/SREGgp2OfQ6SBmdBg/3UIjpTyylF64qv02YB6YxZHtxIprMtaUVcpQIGWb
EZrUQMRbFOjSCHQN0MI+RMfCmEczteim6Fgd1co0mGeTySP/0g3kxGD5Uys1
a8xKBKlWsomutMC0iN4DtJKptH7JbfJhVmSqfLAUpL2nonikUpGoXuY7ZQE9
JKHy9ZE9kasOseHkV4pZPaY2CUy8bikzQkqVGUr1hCH5rgrP5FEkw6/p9pAC
m26QtjKRErD7Y+DdSbliUVgaWOnvzp5hUFqmNrVEeKaWL3I+o3uE2HTEI3ip
t4fNXs+Usx5md1mzAfo39FUyuiw2gLaQoVQOx8y+sjGjIiy8z4pyvG9+xJHA
yzroucIOWFOpCdOQinl2LSfHcJrivLzPvZkS+e/3dj9CvZm8N5hS7EjThdRa
6dtcOCG8qiiaULmhHNRb8rNLA0JXZTPrtEd5aolhgrBHpleP1hE4siF530Ez
lNWtJ+O9mYVTJd/x2RTQtFRnkMqxV97Zw8BVM4BEsMhiDMREgOHhgpJXisY8
pCJo02y57NxG+YOeYSk8lEG0pX3WFozlFg1IGQcRaSunGxwWmCpeYOHWRA8T
0QdYlogqlYq8o0U/GlLz5sgZ+IkYlnNqCGWtvF3IQHHjckA5Qla9Rn9Udm9N
KttI0uFLg2U+ve7MboPqIU2IoUIHyqYLpqEMhaTbY1JHLcp1HiQwpPJ+IIlX
abu57lScbH6IsEZyG8sK0y6lO4O2cl7H8pZb33IrumNV16YVgSaDGdWU3Zem
SlFSmSVCd6JSmrJjevNzRinoBWKCEhQCxao6ke13gVvR+C+neOjKtJjNeUVy
BqwXZ+fdhOf7E+XGI7co+YvJ65ru0pTSjlfuWy8W3B+UUoRg+IcKEw6VLZc1
EoF0M05PCVle3tAFpKD/s89TCuRdXQutjk12pHYHcMFDzq9hhrzKYDZ6Ay91
u2CR6cmmsupZoR61MXqbuTk3bqn5mvZad77HdR5dqIfOXND2PS/AA6gjZXr/
dW4qNbvSoCRprXmpJ1yP7rxZRMHGM/QbCwXPh+AdWhDY/2QegXKLHCljbhUN
t18uJ/tXBTufpx4bXCHVlNtGNiezwfOXHqgrv8xoxiInR3L3dot7oALBb7e6
9bBYeMKPK9vli0SUrvulaSr0qkAb6tMIjZkxmlqWSBRZCDSl4holdeLi3Wdg
Dg4GMFnmxSFuRhwdHp29O2Uvj8+ev356elvQP4hoGe4AQzdCK0n625HpXGI6
ULFYH7XdBh0paKtX8w4NZxCqstoFelusHDDzQiezWoR8SQ2m9D8l9/YUTpRl
fyNeTevUrV/KczZ3rSHOXuP2cw1xdq5Bqn8c6/tM4IXLPT1nK9P9+MtpbgUn
tN2PJmF2Mdv0qu5myiGTW2NNrQtn6zk6XV5FuSVpJTcAsyO7ma7GcRNALSLl
poXcupa7YrQ5bwcT3NNVZh+5uwckTWR0Zip56G25guvkSz4hBx4my81uiyyj
Bf5cxpKAqunO2H+Xe+xSLk/Umpjw08V4QnUg6mJZGu3mhpJ58hDvh+AIW4gs
B60E80JVM9VWfSEcbqlGe+hVyaFMZT3UiPVTC9Q7LYdUZU8/xGjSL3QXQWlL
2r00/3Jd4nIfTLgeNiitc90hO0uFRfGfwl7/+Y9mcf53JbCm8x+tIrLzYUDG
/8vm+gzuOv/R2t6eO/9R3P+2Grjt/rdbj3tkd6qlDkATpw6rxblgS1arKVfr
zEEQC/OiFs+5FdldV7nJld0/mOZ9GLBQ/zt5SfC3i4Kv0f+7hf5fCaxJ/xcn
Ox4I5PT/krk+g7vu/2js7Mx//704/7kSmNP/ueMdU0c5xBCv31hwLdpfcUWH
gfe4U3ituustwdDi8eTUETICPbIDQV+GIUtCOTlCigo21F0je4ZBAarcFpOe
jlCVKCR+Q37CgKjBuaypoBzycCa8Rg8tHqssl47ST4tgIJFClR6zVDXssdsq
xc8rGEen2VdwMivHhD5ZdJWIzo1X3Robt/jPkHT59Y/Urw+Zc/4zfcGHdplt
bGBQEvpmlIsM8zvkb0c6y5U0MJJu7jdmkeWu2KC68YoNomEq1mNjI43yEKKy
7llbwLJgof03pqjy1Z3/nbP/thvtwv5bCazJ/usU9t/DgJz9t2Suz+AO+6/V
BJ6fvf+xvV3Yf6uAJdh/C427cz+Rt+3SrAJbDHcN9wz1OTx8S9ZKPORuiHeX
Red1HtTRBhRx/ffEcy4p1Ji2E/M2YPk1nveRJ6TYtR3EuUouxnhkK6wY/Yhf
p6eYfK9/MebntxQN8SNWGEY9xnN+yjKKPXiaQaNSF1qh3thID08lQZbsG3Nn
qhYmYnfkbdj04hVIXvzprNSMNTMzFo/ZYpE9tiU+BC/tSf+LZixmRUccfTzv
5OXPs4asNzrXMsG8xdDN3hu/Hv9GUXlv3h7/qXf0/Pjo19N3L9WHHujKEpGM
9GmM/HceRu42+w8ywLfQhTgZczb4j9mvO2jqKulHmuaua5HXtunvPOAnwrjv
y13XxXv/aCQnUXSkaMO76zSZuerwG1u5LOc8xmB/tW0Iba5SdD6Z3HhCEzdk
oySQe+PyGCxuXsrZjxGAKjLeJfN/uv4uy1eGFrfaPpdrhelzLfmlxIZkTSsa
4fHW7BUWhFKjy6kC+a9imMSltRos3oa8D5KQR/gUhWP4oyY83qNTkv/UatDn
9ClMjG3XvVRlKW6qUsz3Ub6hxdrhQcEi+1/FWy/NALi//d9ube8U9v8qYE32
/3Zh/z8MyPh/2VyfwV32f6s96/9tdXYK+38lkNn/xsmrZ68xdt3YMDEYCg+s
/knOCUZBrzwyq/DOVd+Ig3TMgl8AtfURHbSo9UQSVnwTq1sO6HIVeTLfND5j
eOYpjzHoi84E6Y9pp98Hx1sfpNWmk84ghT7HPLZxyWGk3/ulmyzojupFRt4m
21DhX/qNCWk68+z2di63fmVmVVEI7y31zcRNzn8tdZ4QLGLK7Ph20cdHF5A6
H6C5gOgZ1GmXyQjDrA0LQ0rJkpWDKgcMvwCPd6hMjSsZpXLqJJEPS6xW+px+
QF4n4ADiF33TBHWveLrM4TGRCCjloTaKAKD7btQ5K/ta1GRAXu2a9+kuEzA1
lds7wa9DI9EnA3lOzRPqFoRIxLoNaTyvvg5C3tKA+UJfxsKTlU0nbLOvIesq
ZBMt+Etuc1MtY7fEVKegWUxnJLH5sCDpPrYa+tJt9ggI/RDgh6zTvYgNNXL5
rYiULFwM0FfD8zXAuubSG4/xi8mWVcq+tI4dQLQ+wv74EKujUe/nP9schNfl
CiwiQvmNZQwC1+NDX2jHBDUg2PewpozKFfyWXv6S8bvvGjCn+kVuJcA/STzA
e8jlRoLajlgc/ypn7bql4z8+gP7HtWnO+ud4USn5XZZVx/3t/9bOdqew/1cB
a/r+XxH/+UBA8//yuT6Du+I/wNyf5f/GdhH/sRL4tCXPE7uClfD0NE2BEtv6
bMCbvh86l/oODEzb19eyTca8W0JLtY6fiJOpJXRuRoLH3RJ9cKSE1710S/rb
MPaFfWPJrwnaY0/QR2IwDb8kJ+oXvyc8mtSbVsfqqAf9CbuD/bqs4MC4JwEH
xsYfyvquNGmJTcr6+juwyWCpA4bTRr1OBi9dJufJw5VoiKqrEbESyPSHcmkT
UksVCxPK117ghtcWnuKMadUMBhAdIfkxxfnMuyEEGIuh8wnmTiCbh7eLTyTW
IX7hBUUgoMZ10iyBGxhLUr6yI+Z1Gz8yb/+2quV3Xcr1D/X6ecXyeXAeD2st
KPHoUQXxQGVoH1fovhqoN+KDUlVeBgPW6YKXFWrMZ9WkzxUjPxBj6NzTMIom
6nwpLI72+wwURwl7Ccasf6Cu/0S7tg/2eJgE6juTeMkeneexACUgwkkYuHK2
wSxbN0/8M8G8/Qezi9+s3f5rtwr7bxWwJvuviP99IKD5f/lcn8Ed9h8YgLPf
f2k1WoX9txK4n/33Z+7TXbZgGh1RwO/3he7++4Z5/R+F/TAmv92y6vgK/b/b
KPZ/VwJr0v9F/OcDAc3/y+f6DO7U/zDlZvi/2WwW+n8VAOob1uF9ZGZU39ik
GkyIIN5jPxhPPWH7fni9ZxinXszxpkvanIMf1s3IV7o/X37dzSngnjCv/3MD
vKQ6viL+C9IK/b8KWJP+L+K/Hgho/l8+12dwl/7fbszt/7RanUL/rwL2/wgj
rmNMuqWm1ShlH44v0R29pT8eMGM/iXy8qg9yB0Ju6uzV69fX12pLh7ZzhDOE
SZROpnrDetwpHYCVkL8CUV7MJy9BBJMB3nqD7PpD9n2XmdlmpIlGBd7+gfUf
pHeG7Puhc/DpU67Y58/7dUzMsshIe/zc2IFre/5kv55LybKNIy+MvHhyAE3f
r6dPstI61iqtHCCSiIWf2BrcDKvLPjlY9xgWUEABBRRQQAEFFFBAAQUUUEAB
BRRQwG3w/99bzmwAGAEA
"""

########NEW FILE########
__FILENAME__ = utils
import os
import re
import httplib
import urlparse
import urllib
import urllib2
import types
import logging
import time
import fnmatch
import multiprocessing.pool

from functools import partial

def fileList(paths, relative=False, folders=False):
	"""
	Generate a recursive list of files from a given path.
	"""
	
	if not type(paths) == types.ListType:
		paths = [paths]
	
	files = []
	
	for path in paths:	
		for fileName in os.listdir(path):
		
			if fileName.startswith('.'):
				continue
		
			filePath = os.path.join(path, fileName)
		
			if os.path.isdir(filePath):
				if folders:
					files.append(filePath)
				files += fileList(filePath)
			else:
				files.append(filePath)
	
		if relative:
			files = map(lambda x: x[len(path)+1:], files)
		
	return files

def multiMap(f, items, workers=8):
	pool = multiprocessing.pool.ThreadPool(workers)
	return pool.map(f, items)
	
def getpassword(service, account):
	
	def decode_hex(s):
		s = eval('"' + re.sub(r"(..)", r"\x\1", s) + '"')
		if "" in s: s = s[:s.index("")]
		return s

	cmd = ' '.join([
		"/usr/bin/security",
		" find-generic-password",
		"-g -s '%s' -a '%s'" % (service, account),
		"2>&1 >/dev/null"
	])
	p = os.popen(cmd)
	s = p.read()
	p.close()
	m = re.match(r"password: (?:0x([0-9A-F]+)\s*)?\"(.*)\"$", s)
	if m:
		hexform, stringform = m.groups()
		if hexform: 
			return decode_hex(hexform)
		else:
			return stringform

def setpassword(service, account, password):
	cmd = 'security add-generic-password -U -a %s -s %s -p %s' % (account, service, password)
	p = os.popen(cmd)
	s = p.read()
	p.close()

def compressString(s):
	"""Gzip a given string."""
	import cStringIO, gzip

	# Nasty monkeypatch to avoid gzip changing every time
	class FakeTime:
		def time(self):
			return 1111111111.111

	gzip.time = FakeTime()
	
	zbuf = cStringIO.StringIO()
	zfile = gzip.GzipFile(mode='wb', compresslevel=9, fileobj=zbuf)
	zfile.write(s)
	zfile.close()
	return zbuf.getvalue()


def getURLHeaders(url):
	
	url = urlparse.urlparse(url)
	
	conn = httplib.HTTPConnection(url.netloc)
	conn.request('HEAD', urllib.quote(url.path))

	response = conn.getresponse()

	return dict(response.getheaders())


def fileSize(num):
	for x in ['b','kb','mb','gb','tb']:
		if num < 1024.0:
			return "%.0f%s" % (num, x)
		num /= 1024.0


def parseValues(data, splitChar=':'):
	"""
	Values like
	
	name: koen
	age: 29
	
	will be converted in a dict: {'name': 'koen', 'age': '29'}
	"""

	values = {}
	lines  = data.splitlines()
	
	if not lines:
		return {}, ''
	
	for i in xrange(len(lines)):

		line = lines[i]

		if not line:
			continue
		
		elif splitChar in line:
			line = line.split(splitChar)
			values[line[0].strip()] = (splitChar.join(line[1:])).strip()
		
		else:
			break
	
	return values, '\n'.join(lines[i:])
		
def retry(ExceptionToCheck, tries=4, delay=3, backoff=2):
	def deco_retry(f):
		def f_retry(*args, **kwargs):
			mtries, mdelay = tries, delay
			try_one_last_time = True
			while mtries > 1:
				try:
					return f(*args, **kwargs)
					try_one_last_time = False
					break
				except ExceptionToCheck, e:
					logging.warning("%s, Retrying in %.1f seconds..." % (str(e), mdelay))
					time.sleep(mdelay)
					mtries -= 1
					mdelay *= backoff
			if try_one_last_time:
				return f(*args, **kwargs)
			return
		return f_retry  # true decorator
	return deco_retry

class memoize(object):
	def __init__(self, func):
		self.func = func
	def __get__(self, obj, objtype=None):
		if obj is None:
			return self.func
		return partial(self, obj)
	def __call__(self, *args, **kw):
		obj = args[0]
		try:
			cache = obj.__cache
		except AttributeError:
			cache = obj.__cache = {}
		key = (self.func, args[1:], frozenset(kw.items()))
		try:
			res = cache[key]
		except KeyError:
			res = cache[key] = self.func(*args, **kw)
		return res

def internetWorking():

	def check(url):
		try:
			response = urllib2.urlopen(url, timeout=1)
			return True
		except urllib2.URLError as err: pass
		return False

	return True in multiMap(check, [
		'http://www.google.com', 
		'http://www.apple.com'])


def filterPaths(paths, patterns):

	def ignorePath(path):

		fileName = os.path.basename(path)
		
		for pattern in patterns:
			if fnmatch.fnmatch(fileName, pattern):
				return True
		return False
			
	return filter(lambda x: not ignorePath(x), paths)

########NEW FILE########
__FILENAME__ = blog.disabled
import os
import datetime
import logging

ORDER = 999
POSTS_PATH = 'posts' + os.sep
POSTS = []

from django.template import Context
from django.template.loader import get_template
from django.template.loader_tags import BlockNode, ExtendsNode

def getNode(template, context=Context(), name='subject'):
	"""
	Get django block contents from a template.
	http://stackoverflow.com/questions/2687173/
	django-how-can-i-get-a-block-from-a-template
	"""
	for node in template:
		if isinstance(node, BlockNode) and node.name == name:
			return node.render(context)
		elif isinstance(node, ExtendsNode):
			return getNode(node.nodelist, context, name)
	raise Exception("Node '%s' could not be found in template." % name)


def preBuild(site):

	global POSTS

	# Build all the posts
	for page in site.pages():
		if page.path.startswith(POSTS_PATH):

			# Skip non html posts for obious reasons
			if not page.path.endswith('.html'):
				continue

			# Find a specific defined variable in the page context,
			# and throw a warning if we're missing it.
			def find(name):
				c = page.context()
				if not name in c:
					logging.info("Missing info '%s' for post %s" % (name, page.path))
					return ''
				return c.get(name, '')

			# Build a context for each post
			postContext = {}
			postContext['title'] = find('title')
			postContext['author'] = find('author')
			postContext['date'] = find('date')
			postContext['path'] = page.path
			postContext['body'] = getNode(get_template(page.path), name="body")

			# Parse the date into a date object
			try:
				postContext['date'] = datetime.datetime.strptime(postContext['date'], '%d-%m-%Y')
			except Exception, e:
				logging.warning("Date format not correct for page %s, should be dd-mm-yy\n%s" % (page.path, e))
				continue

			POSTS.append(postContext)

	# Sort the posts by date
	POSTS = sorted(POSTS, key=lambda x: x['date'])
	POSTS.reverse()

	indexes = xrange(0, len(POSTS))

	for i in indexes:
		if i+1 in indexes: POSTS[i]['prevPost'] = POSTS[i+1]
		if i-1 in indexes: POSTS[i]['nextPost'] = POSTS[i-1]


def preBuildPage(site, page, context, data):
	"""
	Add the list of posts to every page context so we can
	access them from wherever on the site.
	"""
	context['posts'] = POSTS

	for post in POSTS:
		if post['path'] == page.path:
			context.update(post)

	return context, data
########NEW FILE########
__FILENAME__ = coffeescript.disabled
import os
import pipes

os.environ['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/local/share/npm/bin:'

def postBuild(site):
	command = 'coffee -c %s/static/js/*.coffee' % pipes.quote(site.paths['build'])
	os.system(command)

########NEW FILE########
__FILENAME__ = google_closure_compiler.disabled
# based on the example code from google
# would be better if the scripts were concatenated first, but that would involve
# another plugin and then would have to allow either explicit or implicit ordering
# of the files and then you'd have to setup an ordering of plugins to run...
import subprocess
from glob import glob

def postBuild(site):
    for script in glob('%s/static/js/*js' % site.paths['build']):
        root_name = script.rsplit(',', 1)[0]
        dest = "%s.min.js" % root_name
        try:
            subprocess.check_call(['java', '-jar', '/usr/local/lib/closure.jar', '--js', script, '--js_output_file', dest])
        except subprocess.CalledProcessError:
            print 'JS Compile step failed.'
########NEW FILE########
__FILENAME__ = haml.disabled
import sys
import os
import codecs

# How to:
#     * Install hamlpy (https://github.com/jessemiller/HamlPy)
#     * .haml files will compiled to .html files


from cactus.utils import fileList
from hamlpy.hamlpy import Compiler

CLEANUP = []

def preBuild(site):
    for path in fileList(site.paths['pages']):

        #only file ends with haml
        if not path.endswith('.haml'):
            continue

        #read the lines
        haml_lines = codecs.open(path, 'r', encoding='utf-8').read().splitlines()

        #compile haml to html
        compiler = Compiler()
        output = compiler.process_lines(haml_lines)

        #replace path
        outPath = path.replace('.haml', '.html')

        #write the html file
        with open(outPath,'w') as f:
            f.write(output)

        CLEANUP.append(outPath)


def postBuild(site):
    global CLEANUP
    for path in CLEANUP:
        print path
        os.remove(path)
    CLEANUP = []
########NEW FILE########
__FILENAME__ = less.disabled
import subprocess
from glob import glob

def postBuild(site):
    for filename in glob('%s/static/css/*less' % site.paths['build']):
        root_name = filename.rsplit('.', 1)[0]
        src = filename
        dest = "%s.css" % root_name
        try:
            subprocess.check_call(['lessc', '--compress', src, dest])
        except subprocess.CalledProcessError:
            print "lessc returned a non-zero exit status, please check your less syntax"
########NEW FILE########
__FILENAME__ = package.disabled
import hashlib
import itertools
import urllib
import sys
import os
import re
import pipes
import AssetPackager
from bs4 import BeautifulSoup

# Packager!
# Puts CSS and JavaScript files referenced in your html together as one, compressed
# (via YUI compressor) and concatenated, with the help of the AssetPackager.
#
# Having lots of HTTP requests is expensive. In an ideal world your page would have one
# CSS file and one JS file. It's possible to get overagressive here and include something
# big that is only needed on, say, 1 one of your rarely used pages. There's lots of
# tradeoffs and heuristics we could use based on frequency of requests and likelihood
# of assets being requested at a given time. Packager takes a simple approach: analyze
# the assets that appear on each page, and bucket them according to which ones appear
# together. In the simplest case, a site with one page that references assets A,B,C
# will be able to confidently create a single package (file) containing all 3. If we
# add 12 more pages to the site and they all contain A,B, packager will build one package
# of A,B and one of C since C doesn't *always* appear with A,B. It's naive, but it works.

# Packager is NOT a dependency manager! It's naive and just looks at an HTML tree
# and figures out a resonable way to bundle things together to reduce requests.

# Features:
# Preserves original asset order.
# Supports blacklisting of assest with data-nopackage
# Downloads and packages remote assets so you can package your site's base function with your js framework
# Compresses all CSS/JS, even if it's included inline

# Known limitations:
# 1. Does not support @import syntax in css
# 2. If your script tags aren't all in one spot in the markup, it's possible that packaging could
#    force them all together. This is something to be aware of if you've written scripts that
#    expect themselves to come both before and after some other html (or if you're doing some
#    sketchy document.writes or something).


## INSTALLATION:
# sudo pip install AssetPackager
# sudo pip install beautifulsoup4



## CONFIGURATION ##
# For trying packaging on localhost or debugging, set to True which runs packaging on every build.
# Otherwise set to False to only package on deploy. You may have to clean up autogen files manually:
PACKAGE_LOCALLY_DEBUG = False
INCLUDE_REMOTE_ASSETS = True # whether to fetch and package remotely hosted files
MINIFY_FILENAMES = False # otherwise all package filenames will be a concatenation of the filenames within
COMPRESS_PACKAGES = True
INCLUDE_ORIGINAL_FILENAMES_IN_COMMENTS = True
PACKAGE_CSS = True
PACKAGE_JS = True
AUTOGEN_PREFIX = 'cx_' # file prefix for packaged files


localpath_re = re.compile('^(?!http|\/\/)')
relativedir_re = re.compile('^(\.+\/)+')
shortfilename_re = re.compile('(\.js|\.css)$')
assets = []
inline_assets = set()

def _isLocalFile(path):
  return re.match(localpath_re, path)

def _staticPath(site, includeBuild=False):
  static = os.path.relpath(site.paths['static'], site.path)
  if includeBuild:
    static = os.path.join(site.paths['build'], static)
  return static

def _withoutStatic(site, url):
  return os.path.relpath(url, _staticPath(site))

def _relToStaticBuild(site, url):
  return os.path.join(_staticPath(site, includeBuild=True), url)

def _getDir(path):
  if os.path.isdir(path):
    return path
  else:
    return os.path.dirname(path)

def _getLinks(soup):
  def _isValid(tag):
    if tag.name != 'link' and tag.name != 'style' or \
       tag.has_attr('data-nopackage'):
      return False

    if tag.name == 'link':
      href = tag.get('href')
      if not href or \
         'stylesheet' not in tag.get('rel') or \
         not (INCLUDE_REMOTE_ASSETS or _isLocalFile(href)):
        return False

    return True

  return soup.find_all(_isValid)

def _getScripts(soup):
  def _isValid(tag):
    src = tag.get('src')
    if tag.name != 'script' or \
       tag.has_attr('data-nopackage') or \
       not (INCLUDE_REMOTE_ASSETS or not src or _isLocalFile(src)):
      return False

    return True

  return soup.find_all(_isValid)

def _getAssetFrom(tag, site, save=False):
  url = tag.get('href') or tag.get('src') or None
  if url:
    # normalize across subdirectories by removing leading "./" or "../"
    url = re.sub(relativedir_re, '', url)
    if url.startswith(_staticPath(site)):
      # change 'static/js/foo' to '/full/absolute/static/.build/static/js/foo'
      url = _relToStaticBuild(site, _withoutStatic(site, url))
  else:
    extension = 'css' if tag.name == 'style' else 'js'
    contents = tag.renderContents()
    url = 'inline_%s_%s.%s' % (
        extension,
        hashlib.md5(contents).hexdigest(),
        extension
      )
    url = _relToStaticBuild(site, url)
    if save:
      inline_assets.add(url) # for cleanup later
      with open(url, 'w') as f:
        f.write(contents)

  return url

def _replaceHTMLWithPackaged(html, replace_map, path, site):
  soup = BeautifulSoup(html)
  replaced = []
  for tag in _getLinks(soup) + _getScripts(soup):
    asset = _getAssetFrom(tag, site)
    if asset not in replace_map:
      continue

    path_to_static = os.path.relpath(_staticPath(site, includeBuild=True), _getDir(path))
    new_url = os.path.join(path_to_static, replace_map[asset])
    if new_url in replaced:
      # remove HTML node; this was already covered by another node with same package
      tag.extract()
    else:
      # replace assets with packaged version, but just once per package
      replaced.append(new_url)

      # update the actual HTML
      if tag.name == 'script':
        if not tag.get('src'): # inline scripts
          tag.clear()
        tag['src'] = urllib.quote(new_url, '/:')
      else:
        if tag.name == 'style': # inline styles
          new_tag = soup.new_tag('link', rel="stylesheet")
          tag.replace_with(new_tag)
          tag = new_tag
        tag['href'] = urllib.quote(new_url, '/:')
  return str(soup)

def _getPackagedFilename(path_list):
  def shortFileName(path):
    return re.sub(shortfilename_re, '', os.path.basename(path))

  split = path_list[-1].rsplit('.', 1)
  extension = '.' + split[1] if len(split) > 1 else ''
  merged_name = '__'.join(map(shortFileName, path_list)) + extension

  if MINIFY_FILENAMES:
    merged_name = hashlib.md5(merged_name).hexdigest()[:7] + extension

  subdir = 'css' if extension.endswith('css') else 'js'
  filename = os.path.join(subdir, AUTOGEN_PREFIX + merged_name)

  no_local_paths = not filter(lambda p: _isLocalFile(p), path_list)
  return filename, no_local_paths

def analyzeAndPackageAssets(site):
  sys.stdout.write('Analyzing %d gathered assets across %d pages...' %
    (len(list(itertools.chain.from_iterable(assets))), len(assets))
  )
  sys.stdout.flush()
  replace_map = {}

  # determine what should be packaged with what
  packages = AssetPackager.analyze(assets)
  print('done')

  for i, package in enumerate(packages):
    sys.stdout.write(
      '\rPacking analyzed assets into %d packages (%d/%d)' %
      (len(packages), i + 1, len(packages))
    )
    sys.stdout.flush()

    packaged_filename, no_local = _getPackagedFilename(package)

    if len(package) <= 1 and (no_local or not COMPRESS_PACKAGES):
      # it would be silly to compress a remote file and "package it with itself"
      # also silly for a local file to be packaged with itself if we won't be compressing it
      continue

    # Create and save the packaged, minified files
    AssetPackager.package(
      package,
      _relToStaticBuild(site, packaged_filename),
      compress = COMPRESS_PACKAGES,
      filename_markers_in_comments = INCLUDE_ORIGINAL_FILENAMES_IN_COMMENTS
    )

    for asset in package:
      replace_map[asset] = packaged_filename

  sys.stdout.write('\nUpdating HTML sources...')
  sys.stdout.flush()
  for page in site.pages():
    path = page.paths['full-build']

    with open(pipes.quote(path), 'r') as f:
      html = _replaceHTMLWithPackaged(f.read(), replace_map, path, site)
      f.close()
    with open(pipes.quote(path), "wb") as f:
      f.write(html)
      f.close()

  for asset in inline_assets:
    os.remove(asset) # clean up temp buffers
  print('done')



# CACTUS METHODS

def preBuild(site):
  # disable symlinking so we don't end up with a mess of files
  site.nosymlink = True

def postBuild(site):
  if PACKAGE_LOCALLY_DEBUG:
    analyzeAndPackageAssets(site)

def preDeploy(site):
  if not PACKAGE_LOCALLY_DEBUG:
    analyzeAndPackageAssets(site)

def postBuildPage(site, path):
  # Skip non html pages
  if not path.endswith('.html'):
    return

  with open(pipes.quote(path), 'r') as f:
    soup = BeautifulSoup(f.read())
  if PACKAGE_JS:
    assets.append(map(lambda x: _getAssetFrom(x, site, save=True), _getScripts(soup)))
  if PACKAGE_CSS:
    assets.append(map(lambda x: _getAssetFrom(x, site, save=True), _getLinks(soup)))

def postDeploy(site):
  # cleanup all static files that aren't used anymore
  files = [f.path for f in site.files()]
  keys = site.bucket.list(_staticPath(site))
  unused = filter(lambda k: k.name not in files, keys)
  if len(unused) > 0:
    print '\nCleaning up %d unused static files on the server:' % len(unused)
    for key in list(unused):
      print 'D\t' + _withoutStatic(site, key.name)
    site.bucket.delete_keys(unused)

########NEW FILE########
__FILENAME__ = sass.disabled
import os
import pipes

def postBuild(site):
    os.system(
        'sass -t compressed --update %s/static/css/*.sass' % 
            pipes.quote(site.paths['build']
    ))

########NEW FILE########
__FILENAME__ = scss.disabled.
import os
import sys
import pipes
import shutil
import subprocess

from cactus.utils import fileList

"""
This plugin uses pyScss to translate sass files to css

Install:

sudo easy_install pyScss

"""

try:
	from scss import Scss
except:
	sys.exit("Could not find pyScss, please install: sudo easy_install pyScss")


CSS_PATH = 'static/css'

for path in fileList(CSS_PATH):
	
	if not path.endswith('.scss'):
		continue
	
	with open(path, 'r') as f:
		data = f.read()
	
	css = Scss().compile(data)

	with open(path.replace('.scss', '.css'), 'w') as f:
		f.write(css)
########NEW FILE########
__FILENAME__ = sprites.disabled
import os
import sys
import pipes
import shutil
import subprocess

"""
This plugin uses glue to sprite images:
http://glue.readthedocs.org/en/latest/quickstart.html

Install:

(Only if you want to sprite jpg too)
brew install libjpeg

(Only if you want to optimize pngs with optipng)
brew install optipng

sudo easy_install pip
sudo pip uninstall pil
sudo pip install pil
sudo pip install glue
"""

try:
	import glue
except Exception, e:
	sys.exit('Could not use glue: %s\nMaybe install: sudo easy_install glue' % e)


IMG_PATH = 'static/img/sprites'
CSS_PATH = 'static/css/sprites'

KEY = '_PREV_CHECKSUM'

def checksum(path):
	command = 'md5 `find %s -type f`' % pipes.quote(IMG_PATH)
	return subprocess.check_output(command, shell=True)

def preBuild(site):
	
	currChecksum = checksum(IMG_PATH)
	prevChecksum = getattr(site, KEY, None)
	
	# Don't run if none of the images has changed
	if currChecksum == prevChecksum:
		return
	
	if os.path.isdir(CSS_PATH):
		shutil.rmtree(CSS_PATH)
	
	os.mkdir(CSS_PATH)
	os.system('glue --cachebuster --crop --optipng "%s" "%s" --project' % (IMG_PATH, CSS_PATH))
	
	setattr(site, KEY, currChecksum)
########NEW FILE########
__FILENAME__ = version
import os

INFO = {
	'name': 'Version Updater',
	'description': 'Add a version to /versions.txt after each deploy'
}

# Set up extra django template tags

def templateTags():
	pass


# Build actions

# def preBuild(site):
# 	print 'preBuild'
# 
# def postBuild(site):
# 	print 'postBuild'

# Build page actions

# def preBuildPage(site, path, context, data):
# 	print 'preBuildPage', path
# 	return context, data
# 
# def postBuildPage(site, path):
# 	print 'postBuildPage', path
# 	pass


# Deploy actions

def preDeploy(site):
	
	# Add a deploy log at /versions.txt
	
	import urllib2
	import datetime
	import platform
	import codecs
	import getpass
	
	url = site.config.get('aws-bucket-website')
	data = u''
	
	# If this is the first deploy we don't have to fetch the old file
	if url:
		try:
			data = urllib2.urlopen('http://%s/versions.txt' % url, timeout=8.0).read() + u'\n'
		except:
			print "Could not fetch the previous versions.txt, skipping..."
			return
	
	data += u'\t'.join([datetime.datetime.now().isoformat(), platform.node(), getpass.getuser()])
	codecs.open(os.path.join(site.paths['build'], 'versions.txt'), 'w', 'utf8').write(data)

def postDeploy(site):
	pass

########NEW FILE########
__FILENAME__ = test_basic
import os
import shutil
import codecs
import unittest

from cactus import Site
from cactus.utils import fileList

TEST_PATH = '/tmp/www.testcactus.com'


def readFile(path):
	f = codecs.open(path, 'r', 'utf8')
	d = f.read()
	f.close()
	return d

def writeFile(path, data):
	f = codecs.open(path, 'w', 'utf8')
	f.write(data)
	f.close()

def mockFile(name):
	return readFile(os.path.join('tests', 'data', name))

class SimpleTest(unittest.TestCase):
	
	@classmethod
	def setUpClass(cls):
		if os.path.exists(TEST_PATH):
			shutil.rmtree(TEST_PATH)

		cls.site = Site(TEST_PATH)
	
	def testBootstrap(self):
		
		self.site.bootstrap()
		
		self.assertEqual(
			set(fileList(TEST_PATH, relative=True)), 
			set(fileList("skeleton", relative=True)), 
		)


	def testBuild(self):
		
		self.site.build()
		
		# Make sure we build to .build and not build
		self.assertEqual(os.path.exists(os.path.join(TEST_PATH, 'build')), False)
		
		self.assertEqual(
            set(fileList(os.path.join(TEST_PATH, '.build'), relative=True)), 
            set([
			'error.html',
			'index.html',
			'robots.txt',
			'sitemap.xml',
			'static/css/style.css',
			'static/js/main.js' 
            ])
        )
	
	#def testRenderPage(self):
		
		# Create a new page called test.html and see if it get rendered
		
		writeFile(
			os.path.join(TEST_PATH, 'pages', 'test.html'),
			mockFile('test-in.html')
		)
		
		self.site.build()
		
		self.assertEqual(
			readFile(os.path.join(TEST_PATH, '.build', 'test.html')),
			mockFile('test-out.html')
		)
	
	#def testSiteContext(self):
		
		self.assertEqual(
			[page.path for page in self.site.context()['CACTUS']['pages']],
			['error.html', 'index.html', 'test.html']
		)
	
	#def testPageContext(self):

		writeFile(
			os.path.join(TEST_PATH, 'pages', 'koenpage.html'),
			mockFile('koenpage-in.html')
		)
		
		for page in self.site.context()['CACTUS']['pages']:
			if page.path == 'koenpage.html':
				context = page.context()
				self.assertEqual(context['name'], 'Koen Bok')
				self.assertEqual(context['age'], '29')

		self.site.build()
		
		self.assertEqual(
			readFile(os.path.join(TEST_PATH, '.build', 'koenpage.html')),
			mockFile('koenpage-out.html')
		)
	
	##def testIgnoreFiles
	
		writeFile(os.path.join(TEST_PATH, 'pages', 'koen.psd'), "Not really a psd")
		
		self.site.config.set("ignore", ["*.psd"])
		
		self.site.config.write()
		self.site.config.load()
		
		self.site.build()

		self.assertEqual(os.path.exists(os.path.join(TEST_PATH, '.build', 'koen.psd')), False)

	

########NEW FILE########
__FILENAME__ = test_parser
import os
import shutil
import codecs
import unittest

from cactus import Site
from cactus.utils import parseValues

class SimpleTest(unittest.TestCase):
	
	def testBootstrap(self):

		data = """
		name: Koen Bok
		age: 29
		It's a nice boy.
		"""

		self.assertEqual(
			parseValues(data)[0], 
			{'name': 'Koen Bok', 'age': '29'}
		)

		self.assertEqual(
			parseValues(data)[1], 
			'\t\tIt\'s a nice boy.\n\t\t'
		)
########NEW FILE########
