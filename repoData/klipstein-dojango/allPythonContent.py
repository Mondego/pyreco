__FILENAME__ = dojo_serve
import os
import wsgiref.handlers

from dojango.appengine import memcache_zipserve

from google.appengine.ext import webapp

# setup the environment
from common.appenginepatch.aecmd import setup_env
setup_env(manage_py_env=True)
from dojango.conf import settings

# creating a handler structure for the zip-files within the release folder
release_dir = '%s/release/%s' % (settings.BASE_MEDIA_ROOT, settings.DOJO_VERSION)
handlers = []
for zip_file in os.listdir(release_dir):
    if zip_file.endswith(".zip"):
        module = os.path.splitext(zip_file)[0]
        handler = [os.path.join(release_dir, zip_file)]
        handlers.append(handler)

class FlushCache(webapp.RequestHandler):
    """
    Handler for flushing the whole memcache instance.
    """
    from google.appengine.ext.webapp.util import login_required
    @login_required 
    def get(self):
        from google.appengine.api import memcache
        from google.appengine.api import users
        if users.is_current_user_admin():
            stats = memcache.get_stats()
            memcache.flush_all()
            self.response.out.write("Memcache successfully flushed!<br/>")
            if stats:
                self.response.out.write("<p>Memcache stats:</p><p>")
                for key in stats.keys():
                    self.response.out.write("%s: %s<br/>" % (key, stats[key]))
                self.response.out.write("</p>")

def main():
  application = webapp.WSGIApplication([
      ('%s/%s/(.*)' % (settings.BUILD_MEDIA_URL, settings.DOJO_VERSION),
        memcache_zipserve.create_handler(handlers, max_age=31536000)
      ),
      ('%s/_flushcache[/]{0,1}' % settings.BUILD_MEDIA_URL, FlushCache)
  ], debug=False)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = memcache_zipserve
#!/usr/bin/env python
#
# Copyright 2008 Google Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""A class to serve pages from zip files and use memcache for performance.

This contains a class and a function to create an anonymous instance of the
class to serve HTTP GET requests. Memcache is used to increase response speed
and lower processing cycles used in serving. Credit to Guido van Rossum and
his implementation of zipserve which served as a reference as I wrote this.

NOTE: THIS FILE WAS MODIFIED TO SUPPORT CLIENT CACHING

  MemcachedZipHandler: Class that serves request
  create_handler: method to create instance of MemcachedZipHandler
"""

__author__ = 'j.c@google.com (Justin Mattson)'

import email.Utils
import datetime
import logging
import mimetypes
import os
import time
import zipfile

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from django.utils.hashcompat import md5_constructor

def create_handler(zip_files, max_age=None, public=None, client_caching=None):
  """Factory method to create a MemcachedZipHandler instance.

  Args:
    zip_files: A list of file names, or a list of lists of file name, first
        member of file mappings. See MemcachedZipHandler documentation for
        more information about using the list of lists format
    max_age: The maximum client-side cache lifetime
    public: Whether this should be declared public in the client-side cache
  Returns:
    A MemcachedZipHandler wrapped in a pretty, anonymous bow for use with App
    Engine

  Raises:
    ValueError: if the zip_files argument is not a list
  """
  # verify argument integrity. If the argument is passed in list format,
  # convert it to list of lists format
  
  if zip_files and type(zip_files).__name__ == 'list':
    num_items = len(zip_files)
    while num_items > 0:
      if type(zip_files[num_items - 1]).__name__ != 'list':
        zip_files[num_items - 1] = [zip_files[num_items-1]]
      num_items -= 1
  else:
    raise ValueError('File name arguments must be a list')

  class HandlerWrapper(MemcachedZipHandler):
    """Simple wrapper for an instance of MemcachedZipHandler.

    I'm still not sure why this is needed
    """
    
    def get(self, name):
      self.zipfilenames = zip_files
      if max_age is not None:
        self.MAX_AGE = max_age
      if public is not None:
        self.PUBLIC = public
      if client_caching is not None:
        self.CLIENT_CACHING = client_caching
      self.TrueGet(name)

  return HandlerWrapper


class CacheFile(object):
    pass

class MemcachedZipHandler(webapp.RequestHandler):
  """Handles get requests for a given URL.

  Serves a GET request from a series of zip files. As files are served they are
  put into memcache, which is much faster than retreiving them from the zip
  source file again. It also uses considerably fewer CPU cycles.
  """
  zipfile_cache = {}                # class cache of source zip files
  current_last_modified = None      # where we save the current last modified datetime
  current_etag = None               # the current ETag of a file served
  CLIENT_CACHING = True             # is client caching enabled? (sending Last-Modified and ETag within response!)
  MAX_AGE = 600                     # max client-side cache lifetime
  PUBLIC = True                     # public cache setting
  CACHE_PREFIX = "cache://"         # memcache key prefix for actual URLs
  NEG_CACHE_PREFIX = "noncache://"  # memcache key prefix for non-existant URL

  def TrueGet(self, name):
    """The top-level entry point to serving requests.

    Called 'True' get because it does the work when called from the wrapper
    class' get method

    Args:
      name: URL requested

    Returns:
      None
    """
    name = self.PreprocessUrl(name)

    # see if we have the page in the memcache
    resp_data = self.GetFromCache(name)
    if resp_data is None:
      logging.info('Cache miss for %s', name)
      resp_data = self.GetFromNegativeCache(name)
      if resp_data is None or resp_data == -1:
        resp_data = self.GetFromStore(name)
        # IF we have the file, put it in the memcache
        # ELSE put it in the negative cache
        if resp_data is not None:
          self.StoreOrUpdateInCache(name, resp_data)
        else:
          logging.info('Adding %s to negative cache, serving 404', name)
          self.StoreInNegativeCache(name)
          self.Write404Error()
          return
      else:
        self.Write404Error()
        return

    content_type, encoding = mimetypes.guess_type(name)
    if content_type:
      self.response.headers['Content-Type'] = content_type
    self.current_last_modified = resp_data.lastmod
    self.current_etag = resp_data.etag
    self.SetCachingHeaders()
    # if the received ETag matches
    if resp_data.etag == self.request.headers.get('If-None-Match'):
        self.error(304)
        return
    # if-modified-since was passed by the browser
    if self.request.headers.has_key('If-Modified-Since'):
        dt = self.request.headers.get('If-Modified-Since').split(';')[0]
        modsince = datetime.datetime.strptime(dt, "%a, %d %b %Y %H:%M:%S %Z")
        if modsince >= self.current_last_modified:
            # The file is older than the cached copy (or exactly the same)
            self.error(304)
            return
    self.response.out.write(resp_data.file)

  def PreprocessUrl(self, name):
    """Any preprocessing work on the URL when it comes it.

    Put any work related to interpretting the incoming URL here. For example,
    this is used to redirect requests for a directory to the index.html file
    in that directory. Subclasses should override this method to do different
    preprocessing.

    Args:
      name: The incoming URL

    Returns:
      The processed URL
    """
    if name[len(name) - 1:] == '/':
      return "%s%s" % (name, 'index.html')
    else:
      return name

  def GetFromStore(self, file_path):
    """Retrieve file from zip files.

    Get the file from the source, it must not have been in the memcache. If
    possible, we'll use the zip file index to quickly locate where the file
    should be found. (See MapToFileArchive documentation for assumptions about
    file ordering.) If we don't have an index or don't find the file where the
    index says we should, look through all the zip files to find it.

    Args:
      file_path: the file that we're looking for

    Returns:
      The contents of the requested file
    """
    resp_data = None
    file_itr = iter(self.zipfilenames)

    # check the index, if we have one, to see what archive the file is in
    archive_name = self.MapFileToArchive(file_path)
    if not archive_name:
      archive_name = file_itr.next()[0]
    
    while resp_data is None and archive_name:
      zip_archive = self.LoadZipFile(archive_name)
      if zip_archive:

        # we expect some lookups will fail, and that's okay, 404s will deal
        # with that
        try:
          resp_data = CacheFile()
          info = os.stat(archive_name)
          #lastmod = datetime.datetime.fromtimestamp(info[8])
          lastmod = datetime.datetime(*zip_archive.getinfo(file_path).date_time)
          resp_data.file = zip_archive.read(file_path)
          resp_data.lastmod = lastmod
          resp_data.etag = '"%s"' % md5_constructor(resp_data.file).hexdigest()
        except (KeyError, RuntimeError), err:
          # no op
          x = False
          resp_data = None
        if resp_data is not None:
          logging.info('%s read from %s', file_path, archive_name)
          
      try:
        archive_name = file_itr.next()[0]
      except (StopIteration), err:
        archive_name = False

    return resp_data

  def LoadZipFile(self, zipfilename):
    """Convenience method to load zip file.

    Just a convenience method to load the zip file from the data store. This is
    useful if we ever want to change data stores and also as a means of
    dependency injection for testing. This method will look at our file cache
    first, and then load and cache the file if there's a cache miss

    Args:
      zipfilename: the name of the zip file to load

    Returns:
      The zip file requested, or None if there is an I/O error
    """
    zip_archive = None
    zip_archive = self.zipfile_cache.get(zipfilename)
    if zip_archive is None:
      try:
        zip_archive = zipfile.ZipFile(zipfilename)
        self.zipfile_cache[zipfilename] = zip_archive
      except (IOError, RuntimeError), err:
        logging.error('Can\'t open zipfile %s, cause: %s' % (zipfilename,
                                                             err))
    return zip_archive

  def MapFileToArchive(self, file_path):
    """Given a file name, determine what archive it should be in.

    This method makes two critical assumptions.
    (1) The zip files passed as an argument to the handler, if concatenated
        in that same order, would result in a total ordering
        of all the files. See (2) for ordering type.
    (2) Upper case letters before lower case letters. The traversal of a
        directory tree is depth first. A parent directory's files are added
        before the files of any child directories

    Args:
      file_path: the file to be mapped to an archive

    Returns:
      The name of the archive where we expect the file to be
    """
    num_archives = len(self.zipfilenames)
    while num_archives > 0:
      target = self.zipfilenames[num_archives - 1]
      if len(target) > 1:
        if self.CompareFilenames(target[1], file_path) >= 0:
          return target[0]
      num_archives -= 1

    return None

  def CompareFilenames(self, file1, file2):
    """Determines whether file1 is lexigraphically 'before' file2.

    WARNING: This method assumes that paths are output in a depth-first,
    with parent directories' files stored before childs'

    We say that file1 is lexigraphically before file2 if the last non-matching
    path segment of file1 is alphabetically before file2. 

    Args:
      file1: the first file path
      file2: the second file path

    Returns:
      A positive number if file1 is before file2
      A negative number if file2 is before file1
      0 if filenames are the same
    """
    f1_segments = file1.split('/')
    f2_segments = file2.split('/')

    segment_ptr = 0
    while (segment_ptr < len(f1_segments) and
           segment_ptr < len(f2_segments) and
           f1_segments[segment_ptr] == f2_segments[segment_ptr]):
      segment_ptr += 1

    if len(f1_segments) == len(f2_segments):

      # we fell off the end, the paths much be the same
      if segment_ptr == len(f1_segments):
        return 0

      # we didn't fall of the end, compare the segments where they differ
      if f1_segments[segment_ptr] < f2_segments[segment_ptr]:
        return 1
      elif f1_segments[segment_ptr] > f2_segments[segment_ptr]:
        return -1
      else:
        return 0

      # the number of segments differs, we either mismatched comparing
      # directories, or comparing a file to a directory
    else:

      # IF we were looking at the last segment of one of the paths,
      # the one with fewer segments is first because files come before
      # directories
      # ELSE we just need to compare directory names
      if (segment_ptr + 1 == len(f1_segments) or
          segment_ptr + 1 == len(f2_segments)):
        return len(f2_segments) - len(f1_segments)
      else:
        if f1_segments[segment_ptr] < f2_segments[segment_ptr]:
          return 1
        elif f1_segments[segment_ptr] > f2_segments[segment_ptr]:
          return -1
        else:
          return 0

  def SetCachingHeaders(self):
    """Set caching headers for the request."""
    max_age = self.MAX_AGE
    self.response.headers['Expires'] = email.Utils.formatdate(
        time.time() + max_age, usegmt=True)
    cache_control = []
    if self.PUBLIC:
      cache_control.append('public')
    cache_control.append('max-age=%d' % max_age)
    self.response.headers['Cache-Control'] = ', '.join(cache_control)
    # adding caching headers for the client
    if self.CLIENT_CACHING:
        if self.current_last_modified:
            self.response.headers['Last-Modified'] = self.current_last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
        if self.current_etag:
            self.response.headers['ETag'] = self.current_etag

  def GetFromCache(self, filename):
    """Get file from memcache, if available.

    Args:
      filename: The URL of the file to return

    Returns:
      The content of the file
    """
    return memcache.get("%s%s" % (self.CACHE_PREFIX, filename))

  def StoreOrUpdateInCache(self, filename, data):
    """Store data in the cache.

    Store a piece of data in the memcache. Memcache has a maximum item size of
    1*10^6 bytes. If the data is too large, fail, but log the failure. Future
    work will consider compressing the data before storing or chunking it

    Args:
      filename: the name of the file to store
      data: the data of the file

    Returns:
      None
    """
    try:
      if not memcache.add("%s%s" % (self.CACHE_PREFIX, filename), data):
        memcache.replace("%s%s" % (self.CACHE_PREFIX, filename), data)
    except (ValueError), err:
      logging.warning("Data size too large to cache\n%s" % err)

  def Write404Error(self):
    """Ouptut a simple 404 response."""
    self.error(404)
    self.response.out.write('Error 404, file not found')

  def StoreInNegativeCache(self, filename):
    """If a non-existant URL is accessed, cache this result as well.

    Future work should consider setting a maximum negative cache size to
    prevent it from from negatively impacting the real cache.

    Args:
      filename: URL to add ot negative cache

    Returns:
      None
    """
    memcache.add("%s%s" % (self.NEG_CACHE_PREFIX, filename), -1)

  def GetFromNegativeCache(self, filename):
    """Retrieve from negative cache.

    Args:
      filename: URL to retreive

    Returns:
      The file contents if present in the negative cache.
    """
    return memcache.get("%s%s" % (self.NEG_CACHE_PREFIX, filename))


def main():
  application = webapp.WSGIApplication([('/([^/]+)/(.*)',
                                         MemcachedZipHandler)])
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = dojobuild
#!/usr/bin/env python
# This is the alternate dojo build command so it can be used
# with older versions of django (mainly because of AppEngine, it uses version 0.96)
import os
import sys
from optparse import OptionParser

def setup_environ():
    # we assume, that dojango is installed within your django's project dir
    project_directory = os.path.abspath(os.path.dirname(__file__)+'/../../')
    settings_filename = "settings.py"
    if not project_directory:
        project_directory = os.getcwd()
    project_name = os.path.basename(project_directory)
    settings_name = os.path.splitext(settings_filename)[0]
    sys.path.append(project_directory)
    sys.path.append(os.path.abspath(project_directory + "/.."))
    project_module = __import__(project_name, {}, {}, [''])
    sys.path.pop()
    # Set DJANGO_SETTINGS_MODULE appropriately.
    os.environ['DJANGO_SETTINGS_MODULE'] = '%s.%s' % (project_name, settings_name)
    return project_directory

project_dir = setup_environ()
from dojango.management.commands.dojobuild import Command

if __name__ == "__main__":
    my_build = Command()
    parser = OptionParser(option_list=my_build.option_list)
    options, args = parser.parse_args(sys.argv)
    my_build.handle(*args[1:], **options.__dict__)
########NEW FILE########
__FILENAME__ = settings
import os
from django.conf import settings

DEBUG = getattr(settings, "DEBUG", False)
DEFAULT_CHARSET = getattr(settings, 'DEFAULT_CHARSET', 'utf-8')

DOJO_VERSION = getattr(settings, "DOJANGO_DOJO_VERSION", "1.7.2")
# NOTE: you have to use "google_xd" for dojo versions < 1.7.0
DOJO_PROFILE = getattr(settings, "DOJANGO_DOJO_PROFILE", "google")

DOJO_MEDIA_URL = getattr(settings, "DOJANGO_DOJO_MEDIA_URL", 'dojo-media')
BASE_MEDIA_URL = getattr(settings, "DOJANGO_BASE_MEDIA_URL", '/dojango/%s' % DOJO_MEDIA_URL)
BUILD_MEDIA_URL = getattr(settings, "DOJANGO_BUILD_MEDIA_URL", '%s/release' % BASE_MEDIA_URL)
BASE_MEDIA_ROOT = getattr(settings, "DOJANGO_BASE_MEDIA_ROOT", os.path.abspath(os.path.dirname(__file__)+'/../dojo-media/'))
BASE_DOJO_ROOT = getattr(settings, "DOJANGO_BASE_DOJO_ROOT", BASE_MEDIA_ROOT + "/src")
# as default the dijit theme folder is used
DOJO_THEME_URL = getattr(settings, "DOJANGO_DOJO_THEME_URL", False)
DOJO_THEME = getattr(settings, "DOJANGO_DOJO_THEME", "claro")
DOJO_DEBUG = getattr(settings, "DOJANGO_DOJO_DEBUG", DEBUG) # using the default django DEBUG setting
DOJO_SECURE_JSON = getattr(settings, "DOJANGO_DOJO_SECURE_JSON", True) # if you are using dojo version < 1.2.0 you have set it to False
CDN_USE_SSL = getattr(settings, "DOJANGO_CDN_USE_SSL", False) # is dojo served via https from google? doesn't work for aol!

# set the urls for actual possible paths for dojo
# one dojo profile must at least contain a path that defines the base url of a dojo installation
# the following settings can be set for each dojo profile:
# - base_url: where do the dojo files reside (without the version folder!)
# - use_xd: use the crossdomain-build? used to build the correct filename (e.g. dojo.xd.js)
# - versions: this list defines all possible versions that are available in the defined profile
# - uncompressed: use the uncompressed version of dojo (dojo.xd.js.uncompressed.js)
# - use_gfx: there is a special case, when using dojox.gfx from aol (see http://dev.aol.com/dojo)
# - is_local: marks a profile being local. this is needed when using the dojo module loader
# - is_local_build: profile being a locally builded version
_aol_versions = ('0.9.0', '1.0.0', '1.0.2', '1.1.0', '1.1.1', '1.2.0', '1.2.3', '1.3', '1.3.0', '1.3.1', '1.3.2', '1.4', '1.4.0', '1.4.1', '1.4.3', '1.5', '1.5.0', '1.6', '1.6.0')
_aol_gfx_versions = ('0.9.0', '1.0.0', '1.0.2', '1.1.0', '1.1.1',)
_google_xd_versions = ('1.1.1', '1.2', '1.2.0', '1.2.3', '1.3', '1.3.0', '1.3.1', '1.3.2', '1.4', '1.4.0', '1.4.1', '1.4.3', '1.5', '1.5.0', '1.6', '1.6.0', '1.6.1')
_google_versions = ('1.7', '1.7.0', '1.7.1', '1.7.2', '1.7.3', '1.7.4', '1.8.0', '1.8.1', '1.8.2', '1.8.3', '1.8.4', '1.8.5', '1.9.0', '1.9.1', '1.9.2',) # since Dojo 1.7.0 an alternative loading mechanism is in place
DOJO_PROFILES = {
    'google': {'base_url':(CDN_USE_SSL and 'https' or 'http') + '://ajax.googleapis.com/ajax/libs/dojo', 'use_xd':False, 'versions':_google_versions},
    'google_uncompressed': {'base_url':(CDN_USE_SSL and 'https' or 'http') + '://ajax.googleapis.com/ajax/libs/dojo', 'use_xd':False, 'uncompressed':True, 'versions':_google_versions},
    'google_xd': {'base_url':(CDN_USE_SSL and 'https' or 'http') + '://ajax.googleapis.com/ajax/libs/dojo', 'use_xd':True, 'versions':_google_xd_versions}, # google just supports version >= 1.1.1
    'google_uncompressed_xd': {'base_url':(CDN_USE_SSL and 'https' or 'http') + '://ajax.googleapis.com/ajax/libs/dojo', 'use_xd':True, 'uncompressed':True, 'versions':_google_xd_versions},
    'aol': {'base_url':'http://o.aolcdn.com/dojo', 'use_xd':True, 'versions':_aol_versions},
    'aol_uncompressed': {'base_url':'http://o.aolcdn.com/dojo', 'use_xd':True, 'uncompressed':True, 'versions':_aol_versions},
    'aol_gfx': {'base_url':'http://o.aolcdn.com/dojo', 'use_xd':True, 'use_gfx':True, 'versions':_aol_gfx_versions},
    'aol_gfx-uncompressed': {'base_url':'http://o.aolcdn.com/dojo', 'use_xd':True, 'use_gfx':True, 'uncompressed':True, 'versions':_aol_gfx_versions},
    'local': {'base_url': '%(BASE_MEDIA_URL)s', 'is_local':True}, # we don't have a restriction on version names, name them as you like
    'local_release': {'base_url': '%(BUILD_MEDIA_URL)s', 'is_local':True, 'is_local_build':True}, # this will be available after the first dojo build!
    'local_release_uncompressed': {'base_url': '%(BUILD_MEDIA_URL)s', 'uncompressed':True, 'is_local':True, 'is_local_build':True} # same here
}

# we just want users to append/overwrite own profiles
DOJO_PROFILES.update(getattr(settings, "DOJANGO_DOJO_PROFILES", {}))

# =============================================================================================
# =================================== NEEDED FOR DOJO BUILD ===================================
# =============================================================================================
# general doc: http://dojotoolkit.org/book/dojo-book-0-9/part-4-meta-dojo/package-system-and-custom-builds
# see http://www.sitepen.com/blog/2008/04/02/dojo-mini-optimization-tricks-with-the-dojo-toolkit/ for details
DOJO_BUILD_VERSION = getattr(settings, "DOJANGO_DOJO_BUILD_VERSION", '1.7.2')
# this is the default build profile, that is used, when calling "./manage.py dojobuild"
# "./manage.py dojobuild dojango" would have the same effect
DOJO_BUILD_PROFILE = getattr(settings, "DOJANGO_DOJO_BUILD_PROFILE", "dojango")
# This dictionary defines your build profiles you can use within the custom command "./manage.py dojobuild
# You can set your own build profile within the main settings.py of the project by defining a dictionary
# DOJANGO_DOJO_BUILD_PROFILES, that sets the following key/value pairs for each defined profile name:
#   profile_file: which dojo profile file is used for the build (see dojango.profile.js how it has to look)
#   options: these are the options that are passed to the build command (see the dojo doc for details)
#   OPTIONAL SETTINGS (see DOJO_BUILD_PROFILES_DEFAULT):
#   base_root: in which directory will the dojo version be builded to? 
#   used_src_version: which version should be used for the dojo build (e.g. 1.1.1)
#   build_version: what is the version name of the builded release (e.g. dojango1.1.1) - this option can be overwritten by the commandline parameter --build_version=...
#   minify_extreme_skip_files: a tupel of files/folders (each expressed as regular expression) that should be kept when doing a minify extreme (useful when you have several layers and don't want some files)
#                              this tupel will be appended to the default folders/files that are skipped: see SKIP_FILES in management/commands/dojobuild.py 
DOJO_BUILD_PROFILES = {
    'dojango': {
        'options': (DOJO_VERSION > '1.6' and 'profile' or 'profileFile') + '="%(BASE_MEDIA_ROOT)s/dojango.profile.js" action=release optimize=shrinksafe.keepLines cssOptimize=comments.keepLines',
    },
    'dojango_optimized': {
        'options': (DOJO_VERSION > '1.6' and 'profile' or 'profileFile') + '="%(BASE_MEDIA_ROOT)s/dojango_optimized.profile.js" action=release optimize=shrinksafe.keepLines cssOptimize=comments.keepLines',
        'build_version': '%(DOJO_BUILD_VERSION)s-dojango-optimized-with-dojo',
    },
}

# these defaults are mixed into each DOJO_BUILD_PROFILES element
# but you can overwrite each attribute within your own build profile element
# e.g. DOJANGO_BUILD_PROFILES = {'used_src_version': '1.2.2', ....}
DOJO_BUILD_PROFILES_DEFAULT = getattr(settings, "DOJANGO_DOJO_BUILD_PROFILES_DEFAULT", {
    # build the release in the media directory of dojango
    # use a formatting string, so this can be set in the project's settings.py without getting the dojango settings
    'base_root': '%(BASE_MEDIA_ROOT)s/release',
    'used_src_version': '%(DOJO_BUILD_VERSION)s',
    'build_version': '%(DOJO_BUILD_VERSION)s-dojango-with-dojo',
})
# TODO: we should also enable the already pre-delivered dojo default profiles

# you can add/overwrite your own build profiles
DOJO_BUILD_PROFILES.update(getattr(settings, "DOJANGO_DOJO_BUILD_PROFILES", {}))
DOJO_BUILD_JAVA_EXEC = getattr(settings, 'DOJANGO_DOJO_BUILD_JAVA_EXEC', 'java')
# a version string that must have the following form: '1.0.0', '1.2.1', ....
# this setting is used witin the dojobuild, because the build process changed since version 1.2.0
DOJO_BUILD_USED_VERSION = getattr(settings, 'DOJANGO_DOJO_BUILD_USED_VERSION', DOJO_BUILD_VERSION)

########NEW FILE########
__FILENAME__ = context_processors
from dojango.util.config import Config

def config(request):
    '''Make several dojango constants available in the template, like:
      
      {{ DOJANGO.DOJO_BASE_URL }}, {{ DOJANGO.DOJO_URL }}, ...
      
    You can also use the templatetag 'set_dojango_context' in your templates.
    Just set the following at the top of your template to set these context
    contants:
    
    If you want to use the default DOJANGO_DOJO_VERSION/DOJANGO_DOJO_PROFILE:
    
      {% load dojango_base %}
      {% set_dojango_context %}
      
    Using a difernet profile set the following:
    
      {% load dojango_base %}
      {% set_dojango_context "google" "1.1.1" %} 
    '''
    context_extras = {'DOJANGO': {}}
    config = Config()
    context_extras['DOJANGO'] = config.get_context_dict()
    return context_extras
########NEW FILE########
__FILENAME__ = forms
from django.contrib.auth import forms as aforms
from django.utils.translation import ugettext_lazy as _

from dojango import forms

class SetPasswordForm(aforms.SetPasswordForm):
    """
    A form that lets a user change set his/her password without
    entering the old password
    """
    new_password1 = forms.CharField(label=_("New password"), widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=forms.PasswordInput)

class PasswordChangeForm(SetPasswordForm):
    """
    A form that lets a user change his/her password by entering
    their old password.
    """
    old_password = forms.CharField(label=_("Old password"), widget=forms.PasswordInput)

########NEW FILE########
__FILENAME__ = exceptions
""" Django ModelStore exception classes
"""

__all__ = ('MethodException', 'FieldException',
            'StoreException', 'ServiceException')

class MethodException(Exception):
    """ Raised when an error occurs related to a custom
        method (Method, ObjectMethod, etc.) call
    """
    pass

class FieldException(Exception):
    """ Raised when an error occurs related to a custom
        StoreField definition
    """
    pass

class StoreException(Exception):
    """ Raised when an error occurs related to a
        Store definition
    """

class ServiceException(Exception):
    """ Raised when an error occurs related to a custom
        Service definition or servicemethod call
    """

########NEW FILE########
__FILENAME__ = fields
import utils
from exceptions import FieldException
import methods

__all__ = ('FieldException', 'StoreField'
            'ReferenceField', 'DojoDateField')

class StoreField(object):
    """ The base StoreField from which all ```StoreField```s derive
    """

    def __init__(self, model_field=None, store_field=None, get_value=None, sort_field=None, can_sort=True):
        """ A StoreField corresponding to a field on a model.

            Arguments (all optional):

                model_field
                    The name of the field on the model.  If omitted then
                    it's assumed to be the attribute name given to this StoreField
                    in the Store definition.

                    Example:

                    >>> class MyStore(Store):
                    >>>     field_1 = StoreField() # The model_field will be Model.field_1
                    >>>     field_2 = StoreField('my_field') # The model_field will be Model.my_field

                store_field
                    The name of the field in the final store.  If omitted then
                    it will be the attribute name given to this StoreField in the
                    Store definition.

                    Example:

                    >>> class MyStore(Store):
                    >>>     field_1 = StoreField() # The store_field will be 'field_1'
                    >>>     field_2 = StoreField(store_field='my_store_field')

                get_value
                    An instance of modelstore.methods.BaseMethod (or any callable)
                    used to get the final value from the field (or anywhere) that
                    will go in the store.

                    Example:

                    def get_custom_value():
                        return 'my custom value'

                    >>> class MyStore(Store):
                            # get_custom_value will be called with no arguments
                    >>>     field_1 = StoreField(get_value=get_custom_value) 

                            # Wrap your method in an instance of methods.BaseMethod if you want to pass
                            # custom arguments -- see methods.BaseMethod (and it's derivatives) for full docs.
                    >>>     field_2 = StoreField(get_value=Method(get_custom_value, arg1, arg2, arg3))

                sort_field
                    Denotes the string used with QuerySet.order_by() to sort the objects
                    by this field.

                    Either the value passed to 'order_by()' on Django
                    QuerySets or an instance of modelstore.methods.BaseMethod
                    (or any callable) which returns the value.

                    Requests to sort descending are handled automatically by prepending the sort field
                    with '-'

                    Example:

                    >>> class MyStore(Store):
                            # QuerySet.order_by() will be called like: QuerySet.order_by('my_model_field')
                    >>>     field_1 = StoreField('my_model_field')

                            # Sorting by dotted fields.
                    >>>     field_2 = StoreField('my.dotted.field', sort_field='my__dotted__field')

                can_sort
                    Whether or not this field can be order_by()'d -- Default is True.

                    If this is False, then attempts to sort by this field will be ignored.
        """

        self._model_field_name = model_field
        self._store_field_name = store_field
        self._store_attr_name = None # We don't know this yet
        self.can_sort = can_sort
        self._sort_field = sort_field
        self._get_value = get_value

        # Attach a reference to this field to the get_value method
        # so it can access proxied_args
        if self._get_value:
            setattr(self._get_value, 'field', self)

        # Proxied arguments (ie, RequestArg, ObjectArg etc.)
        self.proxied_args = {}

    def _get_sort_field(self):
        """ Return the name of the field to be passed to
            QuerySet.order_by().

            Either the name of the value passed to 'order_by()' on Django
            QuerySets or some method which returns the value.
        """
        if (self._sort_field is None) or isinstance(self._sort_field, (str, unicode) ):
            return self._sort_field
        else:
            return self._sort_field()
    sort_field = property(_get_sort_field)

    def _get_store_field_name(self):
        """ Return the name of the field in the final store.

            If an explicit store_field is given in the constructor then that is
            used, otherwise it's the attribute name given to this field in the
            Store definition.
        """
        return self._store_field_name or self._store_attr_name
    store_field_name = property(_get_store_field_name)

    def _get_model_field_name(self):
        """ Return the name of the field on the Model that this field
            corresponds to.

            If an explicit model_field (the first arg) is given in the constructor
            then that is used, otherwise it's assumed to be the attribute name
            given to this field in the Store definition.
        """
        return self._model_field_name or self._store_attr_name
    model_field_name = property(_get_model_field_name)

    def get_value(self):
        """ Returns the value for this field
        """
        if not self._get_value:
            self._get_value = methods.ObjectMethod(self.model_field_name)
            self._get_value.field = self

        return self._get_value()

class ReferenceField(StoreField):
    """ A StoreField that handles '_reference' items

        Corresponds to model fields that refer to other models,
        ie, ForeignKey, ManyToManyField etc.
    """

    def get_value(self):
        """ Returns a list (if more than one) or dict
            of the form:

            {'_reference': '<item identifier>'}
        """

        # The Store we're attached to
        store = self.proxied_args['StoreArg']

        items = []

        if not self._get_value:
            self._get_value = methods.ObjectMethod(self.model_field_name)
            self._get_value.field = self

        related = self._get_value()

        if not bool(related):
            return items

        # Is this a model instance (ie from ForeignKey) ?
        if hasattr(related, '_get_pk_val'):
            return {'_reference': store.get_identifier(related)}

        # Django Queryset or Manager
        if hasattr(related, 'iterator'):
            related = related.iterator()

        try:
            for item in related:
                items.append({'_reference': store.get_identifier(item)})
        except TypeError:
            raise FieldException('Cannot iterate on field "%s"' % (
                self.model_field_name
            ))

        return items

###
# Pre-built custom Fields
###

class DojoDateField(StoreField):

    def get_value(self):

        self._get_value = methods.DojoDateMethod
        self._get_value.field = self
        return self._get_value()

########NEW FILE########
__FILENAME__ = methods
import utils
from exceptions import MethodException

class Arg(object):
    """ The base placeholder argument class

        There is no reason to use this class directly and really
        only exists to do some type checking on classes that
        inherit from it
    """
    pass

class RequestArg(Arg):
    """ Placeholder argument that represents the current
        Request object.
    """
    pass

class ModelArg(Arg):
    """ Placeholder argument that represents the current
        Model object.

        >>> user = User.objects.get(pk=1)
        >>>

            In this case 'user' is the ObjectArg and
            and 'User' is the ModelArg.
    """
    pass

class ObjectArg(Arg):
    """ Placeholder argument that represents the current
        Model object instance.

        user = User.objects.get(pk=1)

        'user' is the ObjectArg, 'User' is the ModelArg
    """
    pass

class StoreArg(Arg):
    """ Placeholder argument that represents the current
        Store instance.
    """
    pass

class FieldArg(Arg):
    """ Placeholder argument that represents the current
        Field instance.

        This is the field specified on the Store object,
        not the Model object.
    """
    pass


class BaseMethod(object):
    """ The base class from which all proxied methods
        derive.
    """

    def __init__(self, method_or_methodname, *args, **kwargs):
        """ The first argument is either the name of a method
            or the method object itself (ie, pointer to the method)

            The remaining arguments are passed to the given method
            substituting any proxied arguments as needed.

            Usage:
                >>> method = Method('my_method', RequestArg, ObjectArg, 'my other arg', my_kwarg='Something')
                >>> method()
                'My Result'
                >>>

                The method call looks like:
                >>> my_method(request, model_instance, 'my_other_arg', my_kwarg='Something')
        """

        self.method_or_methodname = method_or_methodname
        self.args = args
        self.kwargs = kwargs
        self.field = None # Don't have a handle on the field yet

    def __call__(self):
        """ Builds the arguments and returns the value of the method call
        """

        self._build_args()
        return self.get_value()

    def _build_args(self):
        """ Builds the arguments to be passed to the given method

            Substitutes placeholder args (ie RequestArg, ObjectArg etc.)
            with the actual objects.
        """

        args = []
        for arg in self.args:
            try:
                arg = self.field.proxied_args.get(arg.__name__, arg)
            except AttributeError: # No __name__ attr on the arg
                pass
            args.append(arg)
        self.args = args

        for key, val in self.kwargs.items():
            self.kwargs.update({
                key: self.field.proxied_args.get(hasattr(val, '__name__') and val.__name__ or val, val)
            })

    def get_value(self):
        """ Calls the given method with the requested arguments.
        """
        raise NotImplementedError('get_value() not implemented in BaseMethod')

    def get_method(self, obj=None):
        """ Resolves the given method into a callable object.

            If 'obj' is provided, the method will be looked for as an
            attribute of the 'obj'

            Supports dotted names.

            Usage:
                >>> method = Method('obj.obj.method', RequestArg)
                >>> method()
                'Result of method called with: obj.obj.method(request)'
                >>>

                Dotted attributes are most useful when using something like an
                an ObjectMethod:

                (where 'user' is an instance of Django's 'User' model,
                    the Object in this example is the 'user' instance)

                >>> method = ObjectMethod('date_joined.strftime', '%Y-%m-%d %H:%M:%S')
                >>> method()
                2009-10-02 09:58:39
                >>>

                The actual method call looks like:
                >>> user.date_joined.strftime('%Y-%m-%d %H:%M:%S')
                2009-10-02 09:58:39
                >>>

                It also supports attributes which are not actually methods:

                >>> method = ObjectMethod('first_name', 'ignored arguments', ...) # Arguments to a non-callable are ignored.
                >>> method()
                u'Bilbo'
                >>> method = ValueMethod('first_name', 'upper') # Called on the returned value
                >>> method()
                u'BILBO'
                >>>

                The method call for the last one looks like:
                >>> user.first_name.upper()
                u'BILBO'
                >>>

        """

        if callable(self.method_or_methodname):
            return self.method_or_methodname

        if not isinstance(self.method_or_methodname, (str, unicode) ):
            raise MethodException('Method must a string or callable')

        if obj is not None:

            try:
                method = utils.resolve_dotted_attribute(obj, self.method_or_methodname)
            except AttributeError:
                raise MethodException('Cannot resolve method "%s" in object "%s"' % (
                    self.method_or_methodname, type(obj)
                ))

            if not callable(method):

                # Turn this into a callable
                m = method
                def _m(*args, **kwargs): return m
                method = _m

            return method

        try:
            return eval(self.method_or_methodname) # Just try to get it in current scope
        except NameError:
            raise MethodException('Cannot resolve method "%s"' % self.method_or_methodname)

class Method(BaseMethod):
    """ Basic method proxy class.

        Usage:

            >>> method = Method('my_global_method')
            >>> result = method()

            >>> method = Method(my_method, RequestArg, ObjectArg)
            >>> result = method()

            The real method call would look like:
            >>> my_method(request, model_object)

        Notes:

            If the method passed is the string name of a method,
            it is evaluated in the global scope to get the actual
            method, or MethodException is raised.

            >>> method = Method('my_method')

                Under the hood:
                    >>> try:
                    >>>     method = eval('my_method')
                    >>> except NameError:
                    >>>     ...

    """
    def get_value(self):
        return self.get_method()(*self.args, **self.kwargs)

class ModelMethod(BaseMethod):
    """ A method proxy that will look for the given method
        as an attribute on the Model.
    """
    def get_value(self):
        obj = self.field.proxied_args['ModelArg']
        return self.get_method(obj)(*self.args, **self.kwargs)

class ObjectMethod(BaseMethod):
    """ A method proxy that will look for the given method
        as an attribute on the Model instance.

        Example:

            >>> method = ObjectMethod('get_full_name')
            >>> method()
            u'Bilbo Baggins'

            Assuming this is used on an instance of Django's 'User' model,
            the method call looks like:
            >>> user.get_full_name()

    """
    def get_value(self):
        obj = self.field.proxied_args['ObjectArg']
        return self.get_method(obj)(*self.args, **self.kwargs)

class StoreMethod(BaseMethod):
    """ A method proxy that will look for the given method
        as an attribute on the Store.
    """
    def get_value(self):
        obj = self.field.proxied_args['StoreArg']
        return self.get_method(obj)(*self.args, **self.kwargs)

class FieldMethod(BaseMethod):
    """ A method proxy that will look for the given method
        as an attribute on the Field.

        Notes:
            Field is the field on the Store, not the Model.
    """
    def get_value(self):
        obj = self.field.proxied_args['FieldArg']
        return self.get_method(obj)(*self.args, **self.kwargs)

class ValueMethod(BaseMethod):
    """ A method proxy that will look for the given method
        as an attribute on the value of a field.

        Usage:
            >>> user = User.objects.get(pk=1)
            >>> user.date_joined
            datetime.datetime(..)
            >>>

            A ValueMethod would look for the given method on
            the datetime object:

            >>> method = ValueMethod('strftime', '%Y-%m-%d %H:%M:%S')
            >>> method()
            u'2009-10-02 12:32:12'
            >>>
    """
    def get_value(self):
        obj = self.field.proxied_args['ObjectArg']
        val = utils.resolve_dotted_attribute(obj, self.field.model_field_name)

        # Prevent throwing a MethodException if the value is None
        if val is None:
            return None
        return self.get_method(val)(*self.args, **self.kwargs)

###
# Pre-built custom Methods
###
DojoDateMethod = ValueMethod('strftime', '%Y-%m-%dT%H:%M:%S')

########NEW FILE########
__FILENAME__ = services
import sys, inspect

from django import VERSION as django_version
if django_version >= (1, 5, 0):
    import json
else:
    from django.utils import simplejson as json

from exceptions import ServiceException

def servicemethod(*args, **kwargs):
    """ The Service method decorator.

        Decorate a function or method to expose it remotely
        via RPC (or other mechanism.)

        Arguments:

            name (optional):
                The name of this method as seen remotely.

            store (required if not decorating a bound Store method):
                A reference to the Store this method operates on.

                This is required if the method is a regular function,
                a staticmethod or otherwise defined outside a Store instance.
                (ie doesn't take a 'self' argument)

            store_arg (optional):
                Specifies whether this method should be passed the Store instance
                as the first argument (default is True so that servicemethods bound to
                a store instance can get a proper 'self' reference.)

            request_arg (optional):
                Specifies whether this method should be passed a reference to the current
                Request object.  (Default is True)

            If both store_arg and request_arg are True, the the store will be passed first,
            then the request (to appease bound store methods that need a 'self' as the first arg)

            If only one is True then that one will be passed first.  This is useful for using
            standard Django view functions as servicemethods since they require the 'request'
            as the first argument.
    """
    # Default options
    options = {'name': None, 'store': None, 'request_arg': True, 'store_arg': True}

    # Figure out if we were called with arguments
    # If we were called with args, ie:
    # @servicemethod(name='Foo')
    # Then the only argument here will be the pre-decorated function/method object.
    method = ( (len(args) == 1) and callable(args[0]) ) and args[0] or None

    if method is None:
        # We were called with args, (or  @servicemethod() )
        # so figure out what they were ...

        # The method name should be either the first non-kwarg
        # or the kwarg 'name'
        # Example: @servicemethod('my_method', ...) or @servicemethod(name='my_method')
        options.update({
            'name': bool(args) and args[0] or kwargs.pop('name', None),
            'store': (len(args) >= 2) and args[1] or kwargs.pop('store', None),
            'request_arg': kwargs.pop('request_arg', True),
            'store_arg': kwargs.pop('store_arg', True),
        })
    else:
        options['name'] = method.__name__
        method.__servicemethod__ = options

    def method_with_args_wrapper(method):
        """ Wrapper for a method decorated with decorator arguments
        """
        if options['name'] is None:
            options['name'] = method.__name__
        method.__servicemethod__ = options

        if options['store'] is not None:
            options['store'].service.add_method(method)

        return method

    return method or method_with_args_wrapper

class BaseService(object):
    """ The base Service class that manages servicemethods and
        service method descriptions
    """
    def __init__(self):
        """ BaseService constructor
        """
        self.methods = {}
        self._store = None

    def _get_store(self):
        """ Property getter for the store this service is
            bound to
        """
        return self._store

    def _set_store(self, store):
        """ Property setter for the store this service is
            bound to.  Automatically updates the store
            reference in all the __servicemethod__
            properties on servicemethods in this service
        """
        for method in self.methods.values():
            method.__servicemethod__['store'] = store
        self._store = store
    store = property(_get_store, _set_store)

    def _get_method_args(self, method, request, params):
        """ Decide if we should pass store_arg and/or request_arg
            to the servicemethod
        """
        idx = 0

        if method.__servicemethod__['store_arg']:
            params.insert(idx, method.__servicemethod__['store'])
            idx += 1

        if method.__servicemethod__['request_arg']:
            params.insert(idx, request)

        return params

    def add_method(self, method, name=None, request_arg=True, store_arg=True):
        """ Adds a method as a servicemethod to this service.
        """
        # Was this a decorated servicemethod?
        if hasattr(method, '__servicemethod__'):
            options = method.__servicemethod__
        else:
            options = {'name': name or method.__name__, 'store': self.store,
                'request_arg': request_arg, 'store_arg': store_arg}

        method.__servicemethod__ = options
        self.methods[ options['name'] ] = method

    def get_method(self, name):
        """ Returns the servicemethod given by name
        """
        try:
            return self.methods[name]
        except KeyError:
            raise ServiceException('Service method "%s" not registered' % name)

    def list_methods(self):
        """ Returns a list of all servicemethod names
        """
        return self.methods.keys()

    def process_request(self, request):
        """ Processes a request object --

            This is generally the entry point for all
            servicemethod calls
        """
        raise NotImplementedError('process_request not implemented in BaseService')

    def process_response(self, id, result):
        """ Prepares a response from a servicemethod call
        """
        raise NotImplementedError('process_response not implemented in BaseService')

    def process_error(self, id, code, error):
        """ Prepares an error response from a servicemethod call
        """
        raise NotImplementedError('process_error not implemented in BaseService')

    def get_smd(self, url):
        """ Returns a service method description of all public servicemethods
        """
        raise NotImplementedError('get_smd not implemented in BaseService')

class JsonService(BaseService):
    """ Implements a JSON-RPC version 1.1 service
    """

    def __call__(self, request):
        """ JSON-RPC method calls come in as POSTs
            --
            Requests for the SMD come in as GETs
        """

        if request.method == 'POST':
            response = self.process_request(request)

        else:
            response = self.get_smd(request.get_full_path())

        return json.dumps(response)

    def process_request(self, request):
        """ Handle the request
        """
        try:
            data = json.loads(request.raw_post_data)
            id, method_name, params = data["id"], data["method"], data["params"]

        # Doing a blanket except here because God knows kind of crazy
        # POST data might come in.
        except:
            return self.process_error(0, 100, 'Invalid JSON-RPC request')

        try:
            method = self.get_method(method_name)
        except ServiceException:
            return self.process_error(id, 100, 'Unknown method: "%s"' % method_name)

        params = self._get_method_args(method, request, params)

        try:
            result = method(*params)
            return self.process_response(id, result)

        except BaseException:
            etype, eval, etb = sys.exc_info()
            return self.process_error(id, 100, '%s: %s' % (etype.__name__, eval) )

        except:
            etype, eval, etb = sys.exc_info()
            return self.process_error(id, 100, 'Exception %s: %s' % (etype, eval) )

    def process_response(self, id, result):
        """ Build a JSON-RPC 1.1 response dict
        """
        return {
            'version': '1.1',
            'id': id,
            'result': result,
            'error': None,
        }

    def process_error(self, id, code, error):
        """ Build a JSON-RPC 1.1 error dict
        """
        return {
            'id': id,
            'version': '1.1',
            'error': {
                'name': 'JSONRPCError',
                'code': code,
                'message': error,
            },
        }

    def get_smd(self, url):
        """ Generate a JSON-RPC 1.1 Service Method Description (SMD)
        """
        smd = {
            'serviceType': 'JSON-RPC',
            'serviceURL': url,
            'methods': []
        }

        for name, method in self.methods.items():

            # Figure out what params to report --
            # we don't want to report the 'store' and 'request'
            # params to the remote method.
            idx = 0
            idx += method.__servicemethod__['store_arg'] and 1 or 0
            idx += method.__servicemethod__['request_arg'] and 1 or 0

            sig = inspect.getargspec(method)
            smd['methods'].append({
                'name': name,
                'parameters': [ {'name': val} for val in sig.args[idx:] ]
            })

        return smd

########NEW FILE########
__FILENAME__ = stores
from django import VERSION as django_version
if django_version >= (1, 5, 0):
    import json
else:
    from django.utils import simplejson as json

from django.utils.encoding import smart_unicode
from django.core.paginator import Paginator

from utils import get_fields_and_servicemethods
from exceptions import StoreException, ServiceException
from services import JsonService, servicemethod

__all__ = ('Store', 'ModelQueryStore')

class StoreMetaclass(type):
    """ This class (mostly) came from django/forms/forms.py
        See the original class 'DeclarativeFieldsMetaclass' for doc and comments.
    """
    def __new__(cls, name, bases, attrs):

        # Get the declared StoreFields and service methods
        fields, servicemethods = get_fields_and_servicemethods(bases, attrs)

        attrs['servicemethods'] = servicemethods

        # Tell each field the name of the attribute used to reference it
        # in the Store
        for fieldname, field in fields.items():
            setattr(field, '_store_attr_name', fieldname)
        attrs['fields'] = fields

        return super(StoreMetaclass, cls).__new__(cls, name, bases, attrs)

class BaseStore(object):
    """ The base Store from which all Stores derive
    """

    class Meta(object):
        """ Inner class to hold store options.

            Same basic concept as Django's Meta class
            on Model definitions.
        """
        pass

    def __init__(self, objects=None, stores=None, identifier=None, label=None, is_nested=False):
        """ Store instance constructor.

            Arguments (all optional):

                objects:
                    The list (or any iterable, ie QuerySet) of objects that will
                    fill the store.

                stores:
                    One or more Store objects to combine together into a single
                    store.  Useful when using ReferenceFields to build a store
                    with objects of more than one 'type' (like Django models
                    via ForeignKeys, ManyToManyFields etc.)

                identifier:
                    The 'identifier' attribute used in the store.

                label:
                    The 'label' attribute used in the store.
                
                is_nested:
                    This is required, if we want to return the items as direct
                    array and not as dictionary including 
                    {'identifier': "id", 'label', ...}
                    It mainly is required, if children of a tree structure needs
                    to be rendered (see TreeStore).
        """

        # Instantiate the inner Meta class
        self._meta = self.Meta()

        # Move the fields into the _meta instance
        self.set_option('fields', self.fields)

        # Set the identifier
        if identifier:
            self.set_option('identifier', identifier)
        elif not self.has_option('identifier'):
            self.set_option('identifier', 'id')

        # Set the label
        if label:
            self.set_option('label', label)
        elif not self.has_option('label'):
            self.set_option('label', 'label')
        
        # Is this a nested store? (indicating that it should be rendered as array)
        self.is_nested = is_nested

        # Set the objects
        if objects != None:
            self.set_option('objects', objects)
        elif not self.has_option('objects'):
            self.set_option('objects', [])

        # Set the stores
        if stores:
            self.set_option('stores', stores)
        elif not self.has_option('stores'):
            self.set_option('stores', [])

        # Instantiate the stores (if required)
        self.set_option('stores', [ isinstance(s, Store) and s or s() for s in self.get_option('stores') ])

        # Do we have service set?
        try:
            self.service = self.get_option('service')
            self.service.store = self

            # Populate all the declared servicemethods
            for method in self.servicemethods.values():
                self.service.add_method(method)

        except StoreException:
            self.service = None

        self.request = None # Placeholder for the Request object (if used)
        self.data = self.is_nested and [] or {} # The serialized data in it's final form

    def has_option(self, option):
        """ True/False whether the given option is set in the store
        """
        try:
            self.get_option(option)
        except StoreException:
            return False
        return True

    def get_option(self, option):
        """ Returns the given store option.
            Raises a StoreException if the option isn't set.
        """
        try:
            return getattr(self._meta, option)
        except AttributeError:
            raise StoreException('Option "%s" not set in store' % option)

    def set_option(self, option, value):
        """ Sets a store option.
        """
        setattr(self._meta, option, value)

    def __call__(self, request):
        """ Called when an instance of this store is called
            (ie as a Django 'view' function from a URLConf).

            It accepts the Request object as it's only param, which
            it makes available to other methods at 'self.request'.

            Returns the serialized store as Json.
        """
        self.request = request

        if self.service:
            self._merge_servicemethods()
            if not self.is_nested:
                self.data['SMD'] = self.service.get_smd( request.get_full_path() )

            if request.method == 'POST':
                return self.service(request)

        return self.to_json()

    def __str__(self):
        """ Renders the store as Json.
        """
        return self.to_json()

    def __repr__(self):
        """ Renders the store as Json.
        """
        count = getattr(self.get_option('objects'), 'count', '__len__')()
        return '<%s: identifier: %s, label: %s, objects: %d>' % (
            self.__class__.__name__, self.get_option('identifier'), self.get_option('label'), count)

    def get_identifier(self, obj):
        """ Returns a (theoretically) unique key for a given
            object of the form: <appname>.<modelname>__<pk>
        """
        return smart_unicode('%s__%s' % (
            obj._meta,
            obj._get_pk_val(),
        ), strings_only=True)

    def get_label(self, obj):
        """ Calls the object's __unicode__ method
            to get the label if available or just returns
            the identifier.
        """
        try:
            return obj.__unicode__()
        except AttributeError:
            return self.get_identifier(obj)

    def _merge_servicemethods(self):
        """ Merges the declared service methods from multiple
            stores into a single store.  The store reference on each
            method will still point to the original store.
        """
        # only run if we have a service set
        if self.service:

            for store in self.get_option('stores'):
                if not store.service: # Ignore when no service is defined.
                    continue

                for name, method in store.service.methods.items():
                    try:
                        self.service.get_method(name)
                        raise StoreException('Combined stores have conflicting service method name "%s"' % name)
                    except ServiceException: # This is what we want

                        # Don't use service.add_method since we want the 'foreign' method to
                        # stay attached to the original store
                        self.service.methods[name] = method

    def _merge_stores(self):
        """ Merge all the stores into one.
        """
        for store in self.get_option('stores'):

            # The other stores will (temporarily) take on this store's 'identifier' and
            # 'label' settings
            orig_identifier = store.get_option('identifier')
            orig_label = store.get_option('label')
            for attr in ('identifier', 'label'):
                store.set_option(attr, self.get_option(attr))

            self.data['items'] += store.to_python()['items']

            # Reset the old values for label and identifier
            store.set_option('identifier', orig_identifier)
            store.set_option('label', orig_label)

    def add_store(self, *stores):
        """ Add one or more stores to this store.

            Arguments (required):

                stores:
                    One or many Stores (or Store instances) to add to this store.

            Usage:

                >>> store.add_store(MyStore1, MyStore2(), ...)
                >>>
        """
        # If a non-instance Store is given, instantiate it.
        stores = [ isinstance(s, Store) and s or s() for s in stores ]
        self.set_option('stores', list( self.get_option('stores') ) + stores )

    def to_python(self, objects=None):
        """ Serialize the store into a Python dictionary.

            Arguments (optional):

                objects:
                    The list (or any iterable, ie QuerySet) of objects that will
                    fill the store -- the previous 'objects' setting will be restored
                    after serialization is finished.
        """

        if objects is not None:
            # Save the previous objects setting
            old_objects = self.get_option('objects')
            self.set_option('objects', objects)
            self._serialize()
            self.set_option('objects', old_objects)
        else:
            self._serialize()

        return self.data

    def to_json(self, *args, **kwargs):
        """ Serialize the store as Json.

            Arguments (all optional):

                objects:
                    (The kwarg 'objects')
                    The list (or any iterable, ie QuerySet) of objects that will
                    fill the store.

                All other args and kwargs are passed to json.dumps
        """
        objects = kwargs.pop('objects', None)
        return json.dumps( self.to_python(objects), *args, **kwargs )

    def _start_serialization(self):
        """ Called when serialization of the store begins
        """
        if not self.is_nested:
            self.data['identifier'] = self.get_option('identifier')

        # Don't set a label field in the store if it's not wanted
        if bool( self.get_option('label') ) and not self.is_nested:
            self.data['label'] = self.get_option('label')

        if self.is_nested:
            self.data = []
        else:
            self.data['items'] = []

    def _start_object(self, obj):
        """ Called when starting to serialize each object in 'objects'

            Requires an object as the only argument.
        """
        # The current object in it's serialized state.
        self._item = {self.get_option('identifier'): self.get_identifier(obj)}

        label = self.get_option('label')

        # Do we have a 'label' and is it already the
        # name of one of the declared fields?
        if label and ( label not in self.get_option('fields').keys() ):

            # Have we defined a 'get_label' method on the store?
            if callable( getattr(self, 'get_label', None) ):
                self._item[label] = self.get_label(obj)

    def _handle_field(self, obj, field):
        """ Handle the given field in the Store
        """
        # Fill the proxied_args on the field (for get_value methods that use them)
        field.proxied_args.update({
            'RequestArg': self.request,
            'ObjectArg': obj,
            'ModelArg': obj.__class__,
            'FieldArg': field,
            'StoreArg': self,
        })

        # Get the value
        self._item[field.store_field_name] = field.get_value()

    def _end_object(self, obj):
        """ Called when serializing an object ends.
        """
        if self.is_nested:
            self.data.append(self._item)
        else:
            self.data['items'].append(self._item)
        self._item = None

    def _end_serialization(self):
        """ Called when serialization of the store ends
        """
        pass

    def _serialize(self):
        """ Serialize the defined objects and stores into it's final form
        """
        self._start_serialization()
        for obj in self.get_option('objects'):
            self._start_object(obj)

            for field in self.get_option('fields').values():
                self._handle_field(obj, field)

            self._end_object(obj)
        self._end_serialization()
        self._merge_stores()

class Store(BaseStore):
    """ Just defines the __metaclass__

        All the real functionality is implemented in
        BaseStore
    """
    __metaclass__ = StoreMetaclass

class ModelQueryStore(Store):
    """ A store designed to be used with dojox.data.QueryReadStore

        Handles paging, sorting and filtering

        At the moment it requires a custom subclass of QueryReadStore
        that implements the necessary mechanics to handle server queries
        the the exported Json RPC 'fetch' method.  Soon it will support
        QueryReadStore itself.
    """
    def __init__(self, *args, **kwargs):
        """
        """

        objects_per_query = kwargs.pop('objects_per_query', None)

        super(ModelQueryStore, self).__init__(*args, **kwargs)

        if objects_per_query is not None:
            self.set_option('objects_per_query', objects_per_query)
        elif not self.has_option('objects_per_query'):
            self.set_option('objects_per_query', 25)

    def filter_objects(self, request, objects, query):
        """ Overridable method used to filter the objects
            based on the query dict.
        """
        return objects

    def sort_objects(self, request, objects, sort_attr, descending):
        """ Overridable method used to sort the objects based
            on the attribute given by sort_attr
        """
        return objects

    def __call__(self, request):
        """
        """
        self.request = request

        # We need the request.GET QueryDict to be mutable.
        query_dict = {}
        for k,v in request.GET.items():
            query_dict[k] = v

        # dojox.data.QueryReadStore only handles sorting by a single field
        sort_attr   = query_dict.pop('sort', None)
        descending  = False
        if sort_attr and sort_attr.startswith('-'):
            descending = True
            sort_attr = sort_attr.lstrip('-')

        # Paginator is 1-indexed
        start_index = int( query_dict.pop('start', 0) ) + 1

        # Calculate the count taking objects_per_query into account
        objects_per_query = self.get_option('objects_per_query')
        count = query_dict.pop('count', objects_per_query)

        # We don't want the client to be able to ask for a million records.
        # They can ask for less, but not more ...
        if count == 'Infinity' or int(count) > objects_per_query:
            count = objects_per_query
        else:
            count = int(count)

        objects = self.filter_objects(request, self.get_option('objects'), query_dict)
        objects = self.sort_objects(request, objects, sort_attr, descending)

        paginator = Paginator(objects, count)

        page_num = 1
        for i in xrange(1, paginator.num_pages + 1):
            if paginator.page(i).start_index() <= start_index <= paginator.page(i).end_index():
                page_num = i
                break

        page = paginator.page(page_num)

        data = self.to_python(objects=page.object_list)
        data['numRows'] = paginator.count
        return data

########NEW FILE########
__FILENAME__ = treestore
from stores import Store
from fields import StoreField
from methods import BaseMethod

class ChildrenMethod(BaseMethod):
    """ A method proxy that will resolve the children
        of a model that has a tree structure.
        "django-treebeard" and "django-mptt" both attach a get_children method
        to the model.
    """
    def get_value(self):
        store = self.field.proxied_args['StoreArg']
        obj = self.field.proxied_args['ObjectArg']
        ret = []
        # TODO: optimize using get_descendants()
        if hasattr(obj, "get_children"):
            ret = store.__class__(objects=obj.get_children(), is_nested=True).to_python()
        return ret

class ChildrenField(StoreField):
    """ A field that renders children items
        If your model provides a get_children method you can use that field
        to render all children recursively. 
        (see "django-treebeard", "django-mptt")
    """
    def get_value(self):
        self._get_value = ChildrenMethod(self.model_field_name)
        self._get_value.field = self
        return self._get_value()

class TreeStore(Store):
    """ A store that already includes the children field with no additional
        options. Just subclass that Store, add the to-be-rendered fields and
        attach a django-treebeard (or django-mptt) model to its Meta class:
        
        class MyStore(TreeStore):
            username = StoreField()
            first_name = StoreField()
            
            class Meta:
                objects = YourTreeModel.objects.filter(id=1) # using treebeard or mptt
                label = 'username'
    """
    children = ChildrenField()
########NEW FILE########
__FILENAME__ = utils
from django.utils.datastructures import SortedDict
from django.db.models import get_model
from fields import StoreField
from exceptions import StoreException

def get_object_from_identifier(identifier, valid=None):
    """ Helper function to resolve an item identifier
        into a model instance.

        Raises StoreException if the identifier is invalid
        or the requested Model could not be found

        Raises <Model>.DoesNotExist if the object lookup fails

        Arguments (optional):

            valid
                One or more Django model classes to compare the
                returned model instance to.
    """
    try:
        model_str, pk = identifier.split('__')
    except ValueError:
        raise StoreException('Invalid identifier string')

    Model = get_model(*model_str.split('.'))
    if Model is None:
        raise StoreException('Model from identifier string "%s" not found' % model_str)

    if valid is not None:
        if not isinstance(valid, (list, tuple) ):
            valid = (valid,)
        if Model not in valid:
            raise StoreException('Model type mismatch')

    # This will raise Model.DoesNotExist if lookup fails
    return Model._default_manager.get(pk=pk)

def get_fields_and_servicemethods(bases, attrs, include_bases=True):
    """ This function was pilfered (and slightly modified) from django/forms/forms.py
        See the original function for doc and comments.
    """
    fields = [ (field_name, attrs.pop(field_name)) for \
        field_name, obj in attrs.items() if isinstance(obj, StoreField)]

    # Get the method name directly from the __servicemethod__ dict
    # as set by the decorator
    methods = [ (method.__servicemethod__['name'], method) for \
        method in attrs.values() if hasattr(method, '__servicemethod__') ]

    if include_bases:
        for base in bases[::-1]:

            # Grab the fields and servicemethods from the base classes
            try:
                fields = base.fields.items() + fields
            except AttributeError:
                pass

            try:
                methods = base.servicemethods.items() + methods
            except AttributeError:
                pass

    return SortedDict(fields), SortedDict(methods)

def resolve_dotted_attribute(obj, attr, allow_dotted_names=True):
    """ resolve_dotted_attribute(a, 'b.c.d') => a.b.c.d

        Resolves a dotted attribute name to an object.  Raises
        an AttributeError if any attribute in the chain starts with a '_'

        Modification Note:
        (unless it's the special '__unicode__' method)

        If the optional allow_dotted_names argument is False, dots are not
        supported and this function operates similar to getattr(obj, attr).

        NOTE:
        This method was (mostly) copied straight over from SimpleXMLRPCServer.py in the
        standard library
    """
    if allow_dotted_names:
        attrs = attr.split('.')
    else:
        attrs = [attr]

    for i in attrs:
        if i.startswith('_') and i != '__unicode__': # Allow the __unicode__ method to be called
            raise AttributeError(
                'attempt to access private attribute "%s"' % i
                )
        else:
            obj = getattr(obj,i)
    return obj

########NEW FILE########
__FILENAME__ = emitters
from django import VERSION as django_version
if django_version >= (1, 5, 0):
    import json
else:
    from django.utils import simplejson as json
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.db.models.query import QuerySet
from piston.emitters import Emitter
from piston.validate_jsonp import is_valid_jsonp_callback_value


class DojoDataEmitter(Emitter):
    """
    This emitter is designed to render dojo.data.ItemFileReadStore compatible
    data.

    Requires your handler to expose the `id` field of your model, that Piston
    excludes in the default setting. The item's label is the unicode
    representation of your model unless it already has a field with the
    name `_unicode`.

    Optional GET variables:
        `callback`: JSONP callback
        `indent`: Number of spaces for JSON indentation

    If you serialize Django models and nest related models (which is a common
    case), make sure to set the `hierarchical` parameter of the
    ItemFileReadStore to false (which defaults to true).
    """

    def render(self, request):
        """
        Renders dojo.data compatible JSON if self.data is a QuerySet, falls
        back to standard JSON.
        """
        callback = request.GET.get('callback', None)
        try:
            indent = int(request.GET['indent'])
        except (KeyError, ValueError):
            indent = None

        data = self.construct()

        if isinstance(self.data, QuerySet):
            unicode_lookup_table = dict()

            [unicode_lookup_table.__setitem__(item.pk, unicode(item)) \
                for item in self.data]

            for dict_item in data:
                try:
                    id = dict_item['id']
                except KeyError:
                    raise KeyError('The handler of the model that you want '\
                        'to emit as DojoData needs to expose the `id` field!')
                else:
                    dict_item.setdefault('_unicode', unicode_lookup_table[id])

            data = {
                'identifier': 'id',
                'items': data,
                'label': '_unicode',
                'numRows': self.data.count(),
            }

        serialized_data = json.dumps(data, ensure_ascii=False,
            cls=DateTimeAwareJSONEncoder, indent=indent)

        if callback and is_valid_jsonp_callback_value(callback):
            return '%s(%s)' % (callback, serialized_data)

        return serialized_data


def register_emitters():
    """
    Registers the DojoDataEmitter with the name 'dojodata'.
    """
    Emitter.register('dojodata', DojoDataEmitter,
        'application/json; charset=utf-8')

########NEW FILE########
__FILENAME__ = decorators
from django import VERSION as django_version
if django_version >= (1, 5, 0):
    import json
else:
    from django.utils import simplejson as json
from django.http import HttpResponseNotAllowed, HttpResponseServerError

from util import to_json_response
from util import to_dojo_data

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.

def expect_post_request(func):
    """Allow only POST requests to come in, throw an exception otherwise.
    
    This relieves from checking every time that the request is 
    really a POST request, which it should be when using this 
    decorator.
    """
    def _ret(*args, **kwargs):
        ret = func(*args, **kwargs)
        request = args[0]
        if not request.method=='POST':
            return HttpResponseNotAllowed(['POST'])
        return ret
    return _ret

def add_request_getdict(func):
    """Add the method getdict() to the request object.
    
    This works just like getlist() only that it decodes any nested 
    JSON encoded object structure.
    Since sending deep nested structures is not possible via
    GET/POST by default, this enables it. Of course you need to
    make sure that on the JavaScript side you are also sending
    the data properly, which dojango.send() automatically does.
    Example:
        this is being sent:
            one:1
            two:{"three":3, "four":4}
        using
            request.POST.getdict('two')
        returns a dict containing the values sent by the JavaScript.
    """
    def _ret(*args, **kwargs):
        args[0].POST.__class__.getdict = __getdict
        ret = func(*args, **kwargs)
        return ret
    return _ret

def __getdict(self, key):
    ret = self.get(key)
    try:
        ret = json.loads(ret)
    except ValueError: # The value was not JSON encoded :-)
        raise Exception('"%s" was not JSON encoded as expected (%s).' % (key, str(ret)))
    return ret

def json_response(func):
    """
    A simple json response decorator. Use it on views, where a python data object should be converted
    to a json response:

        @json_response
        def my_view(request):
           my_data = {'foo': 'bar'}
           return my_data
    """
    def inner(request, *args, **kwargs):
        ret = func(request, *args, **kwargs)
        return __prepare_json_ret(request, ret)
    return wraps(func)(inner)

def jsonp_response_custom(callback_param_name):
    """
    A jsonp (JSON with Padding) response decorator, where you can define your own callbackParamName.
    It acts like the json_response decorator but with the difference, that it
    wraps the returned json string into a client-specified function name (that is the Padding).
    
    You can add this decorator to a function like that:
    
        @jsonp_response_custom("my_callback_param")
        def my_view(request):
            my_data = {'foo': 'bar'}
            return my_data

    Your now can access this view from a foreign URL using JSONP.
    An example with Dojo looks like that:
    
        dojo.io.script.get({ url:"http://example.com/my_url/",
                             callbackParamName:"my_callback_param",
                             load: function(response){
                                 console.log(response);
                             }
                           });
                           
    Note: the callback_param_name in the decorator and in your JavaScript JSONP call must be the same.
    """
    def decorator(func):
        def inner(request, *args, **kwargs):
            ret = func(request, *args, **kwargs)
            return __prepare_json_ret(request, ret, callback_param_name=callback_param_name)
        return wraps(func)(inner)
    return decorator

jsonp_response = jsonp_response_custom("jsonp_callback")
jsonp_response.__doc__ = "A predefined jsonp response decorator using 'jsoncallback' as a fixed callback_param_name."

def json_iframe_response(func):
    """
    A simple json response decorator but wrapping the json response into a html page.
    It helps when doing a json request using an iframe (e.g. file up-/download):

        @json_iframe
        def my_view(request):
           my_data = {'foo': 'bar'}
           return my_data
    """
    def inner(request, *args, **kwargs):
        ret = func(request, *args, **kwargs)
        return __prepare_json_ret(request, ret, use_iframe=True)
    return wraps(func)(inner)

def __prepare_json_ret(request, ret, callback_param_name=None, use_iframe=False):
    if ret==False:
        ret = {'success':False}
    elif ret==None: # Sometimes there is no return.
        ret = {}
    # Add the 'ret'=True, since it was obviously no set yet and we got valid data, no exception.
    func_name = None
    if callback_param_name:
        func_name = request.GET.get(callback_param_name, "callbackParamName")
    try:
        if not ret.has_key('success'):
            ret['success'] = True
    except AttributeError, e:
        raise Exception("The returned data of your function must be a dictionary!")
    json_ret = ""
    try:
        # Sometimes the serialization fails, i.e. when there are too deeply nested objects or even classes inside
        json_ret = to_json_response(ret, func_name, use_iframe)
    except Exception, e:
        print '\n\n===============Exception=============\n\n'+str(e)+'\n\n' 
        print ret
        print '\n\n'
        return HttpResponseServerError(content=str(e))
    return json_ret

########NEW FILE########
__FILENAME__ = fields
from django.forms import *
from django.conf import settings as dj_settings
from django.utils import formats

from dojango.forms import widgets
from dojango.util import json_encode

__all__ = (
    'Field', 'MultiValueField', 'ComboField', # original django classes
    'DojoFieldMixin', 'CharField', 'ChoiceField', 'TypedChoiceField',
    'IntegerField', 'BooleanField', 'FileField', 'ImageField',
    'DateField', 'TimeField', 'DateTimeField', 'SplitDateTimeField',
    'RegexField', 'DecimalField', 'FloatField', 'FilePathField',
    'MultipleChoiceField', 'NullBooleanField', 'EmailField',
    'IPAddressField', 'URLField', 'SlugField',
)

class DojoFieldMixin(object):
    """
    A general mixin for all custom django/dojo form fields.
    It passes the field attributes in 'passed_attrs' to the form widget, so
    they can be used there. The widget itself then evaluates which of these
    fiels will be used.
    """
    passed_attrs = [ # forwarded field->widget attributes
        'required',
        'help_text',
        'min_value',
        'max_value',
        'max_length',
        'max_digits',
        'decimal_places',
        'js_regex', # special key for some dojo widgets
    ]
    
    def widget_attrs(self, widget):
        """Called, when the field is instanitating the widget. Here we collect
        all field attributes and pass it to the attributes of the widgets using
        the 'extra_field_attrs' key. These additional attributes will be
        evaluated by the widget and deleted within the 'DojoWidgetMixin'.
        """
        ret = {'extra_field_attrs': {}}
        for field_attr in self.passed_attrs:
            field_val = getattr(self, field_attr, None)
            #print field_attr, widget, field_val
            if field_val is not None:
                ret['extra_field_attrs'][field_attr] = field_val
        return ret

###############################################
# IMPLEMENTATION OF ALL EXISTING DJANGO FIELDS
###############################################

class CharField(DojoFieldMixin, fields.CharField):
    widget = widgets.ValidationTextInput

class ChoiceField(DojoFieldMixin, fields.ChoiceField):
    widget = widgets.Select
    
class TypedChoiceField(DojoFieldMixin, fields.TypedChoiceField):
    widget = widgets.Select

class IntegerField(DojoFieldMixin, fields.IntegerField):
    decimal_places = 0

    def __init__(self, *args, **kwargs):
        if 'widget' not in kwargs:
            kwargs['widget'] = widgets.NumberTextInput
        super(IntegerField, self).__init__(*args, **kwargs)

class BooleanField(DojoFieldMixin, fields.BooleanField):
    widget = widgets.CheckboxInput

class FileField(DojoFieldMixin, fields.FileField):
    widget = widgets.FileInput
    
class ImageField(DojoFieldMixin, fields.ImageField):
    widget = widgets.FileInput

class DateField(DojoFieldMixin, fields.DateField):
    widget = widgets.DateInput
    
    def __init__(self, input_formats=None, min_value=None, max_value=None, *args, **kwargs):
        kwargs['input_formats'] = input_formats or \
            tuple(list(formats.get_format('DATE_INPUT_FORMATS')) + [
                '%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S' # also support dojo's default date-strings
            ])
        self.max_value = max_value
        self.min_value = min_value
        super(DateField, self).__init__(*args, **kwargs)

class TimeField(DojoFieldMixin, fields.TimeField):
    widget = widgets.TimeInput
    
    def __init__(self, input_formats=None, min_value=None, max_value=None, *args, **kwargs):
        kwargs['input_formats'] = input_formats or \
            tuple(list(formats.get_format('TIME_INPUT_FORMATS')) + [
                '%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', 'T%H:%M:%S', 'T%H:%M' # also support dojo's default time-strings
            ])
        self.max_value = max_value
        self.min_value = min_value
        super(TimeField, self).__init__(*args, **kwargs)

class SplitDateTimeField(DojoFieldMixin, fields.SplitDateTimeField):
    widget = widgets.DateTimeInput
    
    def __init__(self, min_value=None, max_value=None, *args, **kwargs):
        self.max_value = max_value
        self.min_value = min_value
        super(SplitDateTimeField, self).__init__(*args, **kwargs)
        # Overwrite the SplitDateTimeField
        # copied from original SplitDateTimeField of django
        errors = self.default_error_messages.copy()
        if 'error_messages' in kwargs:
            errors.update(kwargs['error_messages'])
        fields = (
            DateField(error_messages={'invalid': errors['invalid_date']}),
            TimeField(error_messages={'invalid': errors['invalid_time']}),
        )
        # copied from original MultiValueField of django
        for f in fields:
            f.required = False
        self.fields = fields
    
DateTimeField = SplitDateTimeField # datetime-field is always splitted
    
class RegexField(DojoFieldMixin, fields.RegexField):
    widget = widgets.ValidationTextInput
    js_regex = None # we additionally have to define a custom javascript regexp, because the python one is not compatible to javascript
    
    def __init__(self, js_regex=None, *args, **kwargs):
        self.js_regex = js_regex
        super(RegexField, self).__init__(*args, **kwargs)
        
class DecimalField(DojoFieldMixin, fields.DecimalField):
    widget = widgets.NumberTextInput

class FloatField(DojoFieldMixin, fields.FloatField):
    widget = widgets.ValidationTextInput
    
class FilePathField(DojoFieldMixin, fields.FilePathField):
    widget = widgets.Select
    
class MultipleChoiceField(DojoFieldMixin, fields.MultipleChoiceField):
    widget = widgets.SelectMultiple
    
class NullBooleanField(DojoFieldMixin, fields.NullBooleanField):
    widget = widgets.NullBooleanSelect
    
class EmailField(DojoFieldMixin, fields.EmailField):
    widget = widgets.EmailTextInput
    
class IPAddressField(DojoFieldMixin, fields.IPAddressField):
    widget = widgets.IPAddressTextInput
    
class URLField(DojoFieldMixin, fields.URLField):
    widget = widgets.URLTextInput

class SlugField(DojoFieldMixin, fields.SlugField):
    widget = widgets.ValidationTextInput
    js_regex = '^[-\w]+$' # we cannot extract the original regex input from the python regex

########NEW FILE########
__FILENAME__ = formsets
from django.forms.formsets import *
from django.forms.util import ValidationError
from django.utils.translation import ugettext as _
from django.forms.formsets import TOTAL_FORM_COUNT
from django.forms.formsets import INITIAL_FORM_COUNT
from django.forms.formsets import DELETION_FIELD_NAME
from django.forms.formsets import ORDERING_FIELD_NAME
from django.forms.formsets import formset_factory as django_formset_factory
from django.forms.forms import Form

from fields import IntegerField, BooleanField
from widgets import Media, HiddenInput

from django.forms.formsets import BaseFormSet

__all__ = ('BaseFormSet', 'all_valid')

class ManagementForm(Form):
    """
    Changed ManagementForm. It is using the dojango form fields.
    """
    def __init__(self, *args, **kwargs):
        self.base_fields[TOTAL_FORM_COUNT] = IntegerField(widget=HiddenInput)
        self.base_fields[INITIAL_FORM_COUNT] = IntegerField(widget=HiddenInput)
        Form.__init__(self, *args, **kwargs)

class BaseFormSet(BaseFormSet):
    """
    Overwritten BaseFormSet. Basically using the form extension of dojango.
    """
    def _dojango_management_form(self):
        """Attaching our own ManagementForm"""
        if self.data or self.files:
            form = ManagementForm(self.data, auto_id=self.auto_id, prefix=self.prefix)
            if not form.is_valid():
                raise ValidationError('ManagementForm data is missing or has been tampered with')
        else:
            is_dojo_1_0 = getattr(self, "_total_form_count", False)
            # this is for django versions before 1.1
            initial = {
                TOTAL_FORM_COUNT: is_dojo_1_0 and self._total_form_count or self.total_form_count(),
                INITIAL_FORM_COUNT: is_dojo_1_0 and self._initial_form_count or self.initial_form_count()
            }
            form = ManagementForm(auto_id=self.auto_id, prefix=self.prefix, initial=initial)
        return form
    dojango_management_form = property(_dojango_management_form)

    def __getattribute__(self, anatt):
        """This is the superhack for overwriting the management_form
        property of the super class using a newly defined ManagementForm.
        In Django this property should've be defined lazy:
        management_form = property(lambda self: self._management_form())
        """
        if anatt == 'management_form':
            anatt = "dojango_management_form"
        return super(BaseFormSet, self).__getattribute__(anatt)

    def add_fields(self, form, index):
        """Using the dojango form fields instead of the django ones"""
        is_dojo_1_0 = getattr(self, "_total_form_count", False)
        if self.can_order:
            # Only pre-fill the ordering field for initial forms.
            # before django 1.1 _total_form_count was used!
            if index < (is_dojo_1_0 and self._total_form_count or self.total_form_count()):
                form.fields[ORDERING_FIELD_NAME] = IntegerField(label=_(u'Order'), initial=index+1, required=False)
            else:
                form.fields[ORDERING_FIELD_NAME] = IntegerField(label=_(u'Order'), required=False)
        if self.can_delete:
            form.fields[DELETION_FIELD_NAME] = BooleanField(label=_(u'Delete'), required=False)
            
def formset_factory(*args, **kwargs):
    """Formset factory function that uses the dojango BaseFormSet"""
    if not kwargs.has_key("formset"):
        kwargs["formset"] = BaseFormSet
    return django_formset_factory(*args, **kwargs)

########NEW FILE########
__FILENAME__ = models
from django.forms import *
from django.forms.models import BaseModelFormSet
from django.forms.models import BaseInlineFormSet
from django.forms.models import ModelChoiceIterator
from django.forms.models import InlineForeignKeyField

from django.utils.text import capfirst

from formsets import BaseFormSet

from django.db.models import fields

from dojango.forms.fields import *
from dojango.forms.widgets import DojoWidgetMixin, Textarea, Select, SelectMultiple, HiddenInput

__all__ = (
    'ModelForm', 'BaseModelForm', 'model_to_dict', 'fields_for_model',
    'save_instance', 'ModelChoiceField', 'ModelMultipleChoiceField',
)
    
class ModelChoiceField(DojoFieldMixin, models.ModelChoiceField):
    """
    Overwritten 'ModelChoiceField' using the 'DojoFieldMixin' functionality.
    """
    widget = Select

class ModelMultipleChoiceField(DojoFieldMixin, models.ModelMultipleChoiceField):
    """
    Overwritten 'ModelMultipleChoiceField' using the 'DojoFieldMixin' functonality.
    """
    widget = SelectMultiple

# Fields #####################################################################

class InlineForeignKeyField(DojoFieldMixin, InlineForeignKeyField, Field):
    """
    Overwritten InlineForeignKeyField to use the dojango HiddenInput
    the dojango InlineForeignKeyHiddenInput as widget.
    """
    widget = HiddenInput

# our customized model field => form field map
# here it is defined which form field is used by which model field, when creating a ModelForm
MODEL_TO_FORM_FIELD_MAP = (
    # (model_field, form_field, [optional widget])
    # the order of these fields is very important for inherited model fields
    # e.g. the CharField must be checked at last, because several other
    # fields are a subclass of it.
    (fields.CommaSeparatedIntegerField, CharField),
    (fields.DateTimeField, DateTimeField), # must be in front of the DateField
    (fields.DateField, DateField),
    (fields.DecimalField, DecimalField),
    (fields.EmailField, EmailField),
    (fields.FilePathField, FilePathField),
    (fields.FloatField, FloatField),
    (fields.related.ForeignKey, ModelChoiceField),
    (fields.files.ImageField, ImageField),
    (fields.files.FileField, FileField),
    (fields.IPAddressField, IPAddressField),
    (fields.related.ManyToManyField, ModelMultipleChoiceField),
    (fields.NullBooleanField, CharField),
    (fields.BooleanField, BooleanField),
    (fields.PositiveSmallIntegerField, IntegerField),
    (fields.PositiveIntegerField, IntegerField),
    (fields.SlugField, SlugField),
    (fields.SmallIntegerField, IntegerField),
    (fields.IntegerField, IntegerField),
    (fields.TimeField, TimeField),
    (fields.URLField, URLField),
    (fields.TextField, CharField, Textarea),
    (fields.CharField, CharField),
)

def formfield_function(field, **kwargs):
    """
    Custom formfield function, so we can inject our own form fields. The 
    mapping of model fields to form fields is defined in 'MODEL_TO_FORM_FIELD_MAP'.
    It uses the default django mapping as fallback, if there is no match in our
    custom map.
    
    field -- a model field
    """
    for field_map in MODEL_TO_FORM_FIELD_MAP:
        if isinstance(field, field_map[0]):
            defaults = {}
            if field.choices:
                # the normal django field forms.TypedChoiceField is wired hard
                # within the original db/models/fields.py.
                # If we use our custom Select widget, we also have to pass in
                # some additional validation field attributes.
                defaults['widget'] = Select(attrs={
                    'extra_field_attrs':{
                        'required':not field.blank,
                        'help_text':field.help_text,
                    }
                })
            elif len(field_map) == 3:
                defaults['widget']=field_map[2]
            defaults.update(kwargs)
            return field.formfield(form_class=field_map[1], **defaults)
    # return the default formfield, if there is no equivalent
    return field.formfield(**kwargs)

# ModelForms #################################################################

def fields_for_model(*args, **kwargs):
    """Changed fields_for_model function, where we use our own formfield_callback"""
    kwargs["formfield_callback"] = formfield_function
    return models.fields_for_model(*args, **kwargs)

class ModelFormMetaclass(models.ModelFormMetaclass):
    """
    Overwritten 'ModelFormMetaClass'. We attach our own formfield generation
    function.
    """
    def __new__(cls, name, bases, attrs):
        # this is how we can replace standard django form fields with dojo ones
        attrs["formfield_callback"] = formfield_function
        return super(ModelFormMetaclass, cls).__new__(cls, name, bases, attrs)

class ModelForm(models.ModelForm):
    """
    Overwritten 'ModelForm' using the metaclass defined above.
    """
    __metaclass__ = ModelFormMetaclass

def modelform_factory(*args, **kwargs):
    """Changed modelform_factory function, where we use our own formfield_callback"""
    kwargs["formfield_callback"] = formfield_function
    kwargs["form"] = ModelForm
    return models.modelform_factory(*args, **kwargs)

# ModelFormSets ##############################################################

class BaseModelFormSet(BaseModelFormSet, BaseFormSet):
    
    def add_fields(self, form, index):
        """Overwritten BaseModelFormSet using the dojango BaseFormSet and
        the ModelChoiceField. 
        NOTE: This method was copied from django 1.3 beta 1"""
        from django.db.models import AutoField, OneToOneField, ForeignKey
        self._pk_field = pk = self.model._meta.pk
        def pk_is_not_editable(pk):
            return ((not pk.editable) or (pk.auto_created or isinstance(pk, AutoField))
                or (pk.rel and pk.rel.parent_link and pk_is_not_editable(pk.rel.to._meta.pk)))
        if pk_is_not_editable(pk) or pk.name not in form.fields:
            if form.is_bound:
                pk_value = form.instance.pk
            else:
                try:
                    if index is not None:
                        pk_value = self.get_queryset()[index].pk
                    else:
                        pk_value = None
                except IndexError:
                    pk_value = None
            if isinstance(pk, OneToOneField) or isinstance(pk, ForeignKey):
                qs = pk.rel.to._default_manager.get_query_set()
            else:
                qs = self.model._default_manager.get_query_set()
            qs = qs.using(form.instance._state.db)
            form.fields[self._pk_field.name] = ModelChoiceField(qs, initial=pk_value, required=False, widget=HiddenInput)
        BaseFormSet.add_fields(self, form, index)

def modelformset_factory(*args, **kwargs):
    """Changed modelformset_factory function, where we use our own formfield_callback"""
    kwargs["formfield_callback"] = kwargs.get("formfield_callback", formfield_function)
    kwargs["formset"] = kwargs.get("formset", BaseModelFormSet)
    return models.modelformset_factory(*args, **kwargs)

# InlineFormSets #############################################################

class BaseInlineFormSet(BaseInlineFormSet, BaseModelFormSet):
    """Overwritten BaseInlineFormSet using the dojango InlineForeignKeyFields.
    NOTE: This method was copied from django 1.1"""
    def add_fields(self, form, index):
        super(BaseInlineFormSet, self).add_fields(form, index)
        if self._pk_field == self.fk:
            form.fields[self._pk_field.name] = InlineForeignKeyField(self.instance, pk_field=True)
        else:
            kwargs = {
                'label': getattr(form.fields.get(self.fk.name), 'label', capfirst(self.fk.verbose_name))
            }
            if self.fk.rel.field_name != self.fk.rel.to._meta.pk.name:
                kwargs['to_field'] = self.fk.rel.field_name
            form.fields[self.fk.name] = InlineForeignKeyField(self.instance, **kwargs)
            
def inlineformset_factory(*args, **kwargs):
    """Changed inlineformset_factory function, where we use our own formfield_callback"""
    kwargs["formfield_callback"] = kwargs.get("formfield_callback", formfield_function)
    kwargs["formset"] = kwargs.get("formset", BaseInlineFormSet)
    return models.inlineformset_factory(*args, **kwargs)

########NEW FILE########
__FILENAME__ = widgets
import datetime
import time

from django.forms import *
from django.utils import formats
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.forms.util import flatatt
from django.utils import datetime_safe

from dojango.util import json_encode
from dojango.util.config import Config

from dojango.util import dojo_collector

__all__ = (
    'Media', 'MediaDefiningClass', # original django classes
    'DojoWidgetMixin', 'Input', 'Widget', 'TextInput', 'PasswordInput',
    'HiddenInput', 'MultipleHiddenInput', 'FileInput', 'Textarea',
    'DateInput', 'DateTimeInput', 'TimeInput', 'CheckboxInput', 'Select',
    'NullBooleanSelect', 'SelectMultiple', 'RadioInput', 'RadioFieldRenderer',
    'RadioSelect', 'CheckboxSelectMultiple', 'MultiWidget', 'SplitDateTimeWidget',
    'SplitHiddenDateTimeWidget', 'SimpleTextarea', 'EditorInput', 'HorizontalSliderInput',
    'VerticalSliderInput', 'ValidationTextInput', 'ValidationPasswordInput',
    'EmailTextInput', 'IPAddressTextInput', 'URLTextInput', 'NumberTextInput',
    'RangeBoundTextInput', 'NumberSpinnerInput', 'RatingInput', 'DateInputAnim',
    'DropDownSelect', 'CheckedMultiSelect', 'FilteringSelect', 'ComboBox',
    'ComboBoxStore', 'FilteringSelectStore', 'ListInput',
)

dojo_config = Config() # initialize the configuration

class DojoWidgetMixin:
    """A helper mixin, that is used by every custom dojo widget.
    Some dojo widgets can utilize the validation information of a field and here
    we mixin those attributes into the widget. Field attributes that are listed
    in the 'valid_extra_attrs' will be mixed into the attributes of a widget.

    The 'default_field_attr_map' property contains the default mapping of field
    attributes to dojo widget attributes.

    This mixin also takes care passing the required dojo modules to the collector.
    'dojo_type' defines the used dojo module type of this widget and adds this
    module to the collector, if no 'alt_require' property is defined. When
    'alt_require' is set, this module will be passed to the collector. By using
    'extra_dojo_require' it is possible to pass additional dojo modules to the
    collector.
    """
    dojo_type = None # this is the dojoType definition of the widget. also used for generating the dojo.require call
    alt_require = None # alternative dojo.require call (not using the dojo_type)
    extra_dojo_require = [] # these dojo modules also needs to be loaded for this widget

    default_field_attr_map = { # the default map for mapping field attributes to dojo attributes
        'required':'required',
        'help_text':'promptMessage',
        'min_value':'constraints.min',
        'max_value':'constraints.max',
        'max_length':'maxLength',
        'max_digits':'maxLength',
        'decimal_places':'constraints.places',
        'js_regex':'regExp',
        'multiple':'multiple',
    }
    field_attr_map = {} # used for overwriting the default attr-map
    valid_extra_attrs = [] # these field_attributes are valid for the current widget

    def _mixin_attr(self, attrs, key, value):
        """Mixes in the passed key/value into the passed attrs and returns that
        extended attrs dictionary.

        A 'key', that is separated by a dot, e.g. 'constraints.min', will be
        added as:

        {'constraints':{'min':value}}
        """
        dojo_field_attr = key.split(".")
        inner_dict = attrs
        len_fields = len(dojo_field_attr)
        count = 0
        for i in dojo_field_attr:
            count = count+1
            if count == len_fields and inner_dict.get(i, None) is None:
                if isinstance(value, datetime.datetime):
                    if isinstance(self, TimeInput):
                        value = value.strftime('T%H:%M:%S')
                    if isinstance(self, DateInput):
                        value = value.strftime('%Y-%m-%d')
                    value = str(value).replace(' ', 'T') # see dojo.date.stamp
                if isinstance(value, datetime.date):
                    value = str(value)
                if isinstance(value, datetime.time):
                    value = "T" + str(value) # see dojo.date.stamp
                inner_dict[i] = value
            elif not inner_dict.has_key(i):
                inner_dict[i] = {}
            inner_dict = inner_dict[i]
        return attrs

    def build_attrs(self, extra_attrs=None, **kwargs):
        """Overwritten helper function for building an attribute dictionary.
        This helper also takes care passing the used dojo modules to the
        collector. Furthermore it mixes in the used field attributes into the
        attributes of this widget.
        """
        # gathering all widget attributes
        attrs = dict(self.attrs, **kwargs)
        field_attr = self.default_field_attr_map.copy() # use a copy of that object. otherwise changed field_attr_map would overwrite the default-map for all widgets!
        field_attr.update(self.field_attr_map) # the field-attribute-mapping can be customzied
        if extra_attrs:
            attrs.update(extra_attrs)
        # assigning dojoType to our widget
        dojo_type = getattr(self, "dojo_type", False)
        if dojo_type:
            attrs["dojoType"] = dojo_type # add the dojoType attribute

        # fill the global collector object
        if getattr(self, "alt_require", False):
            dojo_collector.add_module(self.alt_require)
        elif dojo_type:
            dojo_collector.add_module(self.dojo_type)
        extra_requires = getattr(self, "extra_dojo_require", [])
        for i in extra_requires:
            dojo_collector.add_module(i)

        # mixin those additional field attrs, that are valid for this widget
        extra_field_attrs = attrs.get("extra_field_attrs", False)
        if extra_field_attrs:
            for i in self.valid_extra_attrs:
                field_val = extra_field_attrs.get(i, None)
                new_attr_name = field_attr.get(i, None)
                if field_val is not None and new_attr_name is not None:
                    attrs = self._mixin_attr(attrs, new_attr_name, field_val)
            del attrs["extra_field_attrs"]

        # now encode several attributes, e.g. False = false, True = true
        for i in attrs:
            if isinstance(attrs[i], bool):
                attrs[i] = json_encode(attrs[i])
        return attrs

#############################################
# ALL OVERWRITTEN DEFAULT DJANGO WIDGETS
#############################################

class Widget(DojoWidgetMixin, widgets.Widget):
    dojo_type = 'dijit._Widget'

class Input(DojoWidgetMixin, widgets.Input):
    pass

class TextInput(DojoWidgetMixin, widgets.TextInput):
    dojo_type = 'dijit.form.TextBox'
    valid_extra_attrs = [
        'max_length',
    ]

class PasswordInput(DojoWidgetMixin, widgets.PasswordInput):
    dojo_type = 'dijit.form.TextBox'
    valid_extra_attrs = [
        'max_length',
    ]

class HiddenInput(DojoWidgetMixin, widgets.HiddenInput):
    dojo_type = 'dijit.form.TextBox' # otherwise dijit.form.Form can't get its values

class MultipleHiddenInput(DojoWidgetMixin, widgets.MultipleHiddenInput):
    dojo_type = 'dijit.form.TextBox' # otherwise dijit.form.Form can't get its values

class FileInput(DojoWidgetMixin, widgets.FileInput):
    dojo_type = 'dojox.form.FileInput'
    class Media:
        css = {
            'all': ('%(base_url)s/dojox/form/resources/FileInput.css' % {
                'base_url':dojo_config.dojo_base_url
            },)
        }

class Textarea(DojoWidgetMixin, widgets.Textarea):
    """Auto resizing textarea"""
    dojo_type = 'dijit.form.Textarea'
    valid_extra_attrs = [
        'max_length'
    ]

if DateInput:
    class DateInput(DojoWidgetMixin, widgets.DateInput):
        manual_format = True
        format = '%Y-%m-%d' # force to US format (dojo will do the locale-specific formatting)
        dojo_type = 'dijit.form.DateTextBox'
        valid_extra_attrs = [
            'required',
            'help_text',
            'min_value',
            'max_value',
        ]
else:  # fallback for older django versions
    class DateInput(TextInput):
        """Copy of the implementation in Django 1.1. Before this widget did not exists."""
        dojo_type = 'dijit.form.DateTextBox'
        valid_extra_attrs = [
            'required',
            'help_text',
            'min_value',
            'max_value',
        ]
        format = '%Y-%m-%d'     # '2006-10-25'
        def __init__(self, attrs=None, format=None):
            super(DateInput, self).__init__(attrs)
            if format:
                self.format = format

        def render(self, name, value, attrs=None):
            if value is None:
                value = ''
            elif hasattr(value, 'strftime'):
                value = datetime_safe.new_date(value)
                value = value.strftime(self.format)
            return super(DateInput, self).render(name, value, attrs)

if TimeInput:
    class TimeInput(DojoWidgetMixin, widgets.TimeInput):
        dojo_type = 'dijit.form.TimeTextBox'
        valid_extra_attrs = [
            'required',
            'help_text',
            'min_value',
            'max_value',
        ]
        manual_format = True
        format = "T%H:%M:%S" # special for dojo: 'T12:12:33'
        
        def __init__(self, attrs=None, format=None):
            # always passing the dojo time format
            super(TimeInput, self).__init__(attrs, format=self.format)
        
        def _has_changed(self, initial, data):
            try:
                input_format = self.format
                initial = datetime.time(*time.strptime(initial, input_format)[3:6])
            except (TypeError, ValueError):
                pass
            return super(TimeInput, self)._has_changed(self._format_value(initial), data)

else: # fallback for older django versions
    class TimeInput(TextInput):
        """Copy of the implementation in Django 1.1. Before this widget did not exists."""
        dojo_type = 'dijit.form.TimeTextBox'
        valid_extra_attrs = [
            'required',
            'help_text',
            'min_value',
            'max_value',
        ]
        format = "T%H:%M:%S"    # special for dojo: 'T12:12:33'
        def __init__(self, attrs=None, format=None):
            super(TimeInput, self).__init__(attrs)
            if format:
                self.format = format

        def render(self, name, value, attrs=None):
            if value is None:
                value = ''
            elif hasattr(value, 'strftime'):
                value = value.strftime(self.format)
            return super(TimeInput, self).render(name, value, attrs)

class CheckboxInput(DojoWidgetMixin, widgets.CheckboxInput):
    dojo_type = 'dijit.form.CheckBox'

class Select(DojoWidgetMixin, widgets.Select):
    dojo_type = dojo_config.version < '1.4' and 'dijit.form.FilteringSelect' or 'dijit.form.Select'
    valid_extra_attrs = dojo_config.version < '1.4' and \
        ['required', 'help_text',] or \
        ['required',]

class NullBooleanSelect(DojoWidgetMixin, widgets.NullBooleanSelect):
    dojo_type = dojo_config.version < '1.4' and 'dijit.form.FilteringSelect' or 'dijit.form.Select'
    valid_extra_attrs = dojo_config.version < '1.4' and \
        ['required', 'help_text',] or \
        ['required',]

class SelectMultiple(DojoWidgetMixin, widgets.SelectMultiple):
    dojo_type = 'dijit.form.MultiSelect'

RadioInput = widgets.RadioInput
RadioFieldRenderer = widgets.RadioFieldRenderer

class RadioSelect(DojoWidgetMixin, widgets.RadioSelect):
    dojo_type = 'dijit.form.RadioButton'

    def __init__(self, *args, **kwargs):
        if dojo_config.version < '1.3':
            self.alt_require = 'dijit.form.CheckBox'
        super(RadioSelect, self).__init__(*args, **kwargs)

class CheckboxSelectMultiple(DojoWidgetMixin, widgets.CheckboxSelectMultiple):
    dojo_type = 'dijit.form.CheckBox'

class MultiWidget(DojoWidgetMixin, widgets.MultiWidget):
    dojo_type = None

class SplitDateTimeWidget(widgets.SplitDateTimeWidget):
    "DateTimeInput is using two input fields."
    try:
        # for older django versions 
        date_format = DateInput.format
        time_format = TimeInput.format
    except AttributeError:
        date_format = None
        time_format = None


    def __init__(self, attrs=None, date_format=None, time_format=None):
        if date_format:
            self.date_format = date_format
        if time_format:
            self.time_format = time_format
        split_widgets = (DateInput(attrs=attrs, format=self.date_format),
                   TimeInput(attrs=attrs, format=self.time_format))
        # Note that we're calling MultiWidget, not SplitDateTimeWidget, because
        # we want to define widgets.
        widgets.MultiWidget.__init__(self, split_widgets, attrs)

class SplitHiddenDateTimeWidget(DojoWidgetMixin, widgets.SplitHiddenDateTimeWidget):
    dojo_type = "dijit.form.TextBox"

DateTimeInput = SplitDateTimeWidget

#############################################
# MORE ENHANCED DJANGO/DOJO WIDGETS
#############################################

class SimpleTextarea(Textarea):
    """No autoexpanding textarea"""
    dojo_type = "dijit.form.SimpleTextarea"

class EditorInput(Textarea):
    dojo_type = 'dijit.Editor'

    def render(self, name, value, attrs=None):
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        # dijit.Editor must be rendered in a div (see dijit/_editor/RichText.js)
        return mark_safe(u'<div%s>%s</div>' % (flatatt(final_attrs),
                force_unicode(value))) # we don't escape the value for the editor

class HorizontalSliderInput(TextInput):
    dojo_type = 'dijit.form.HorizontalSlider'
    valid_extra_attrs = [
        'max_value',
        'min_value',
    ]
    field_attr_map = {
        'max_value': 'maximum',
        'min_value': 'minimum',
    }

    def __init__(self, attrs=None):
        if dojo_config.version < '1.3':
            self.alt_require = 'dijit.form.Slider'
        super(HorizontalSliderInput, self).__init__(attrs)

class VerticalSliderInput(HorizontalSliderInput):
    dojo_type = 'dijit.form.VerticalSlider'

class ValidationTextInput(TextInput):
    dojo_type = 'dijit.form.ValidationTextBox'
    valid_extra_attrs = [
        'required',
        'help_text',
        'js_regex',
        'max_length',
    ]
    js_regex_func = None

    def render(self, name, value, attrs=None):
        if self.js_regex_func:
            attrs = self.build_attrs(attrs, regExpGen=self.js_regex_func)
        return super(ValidationTextInput, self).render(name, value, attrs)

class ValidationPasswordInput(PasswordInput):
    dojo_type = 'dijit.form.ValidationTextBox'
    valid_extra_attrs = [
        'required',
        'help_text',
        'js_regex',
        'max_length',
    ]

class EmailTextInput(ValidationTextInput):
    extra_dojo_require = [
        'dojox.validate.regexp'
    ]
    js_regex_func = "dojox.validate.regexp.emailAddress"

    def __init__(self, attrs=None):
        if dojo_config.version < '1.3':
            self.js_regex_func = 'dojox.regexp.emailAddress'
        super(EmailTextInput, self).__init__(attrs)

class IPAddressTextInput(ValidationTextInput):
    extra_dojo_require = [
        'dojox.validate.regexp'
    ]
    js_regex_func = "dojox.validate.regexp.ipAddress"

    def __init__(self, attrs=None):
        if dojo_config.version < '1.3':
            self.js_regex_func = 'dojox.regexp.ipAddress'
        super(IPAddressTextInput, self).__init__(attrs)

class URLTextInput(ValidationTextInput):
    extra_dojo_require = [
        'dojox.validate.regexp'
    ]
    js_regex_func = "dojox.validate.regexp.url"

    def __init__(self, attrs=None):
        if dojo_config.version < '1.3':
            self.js_regex_func = 'dojox.regexp.url'
        super(URLTextInput, self).__init__(attrs)

class NumberTextInput(TextInput):
    dojo_type = 'dijit.form.NumberTextBox'
    valid_extra_attrs = [
        'min_value',
        'max_value',
        'required',
        'help_text',
        'decimal_places',
        'max_digits',
    ]

class RangeBoundTextInput(NumberTextInput):
    dojo_type = 'dijit.form.RangeBoundTextBox'

class NumberSpinnerInput(NumberTextInput):
    dojo_type = 'dijit.form.NumberSpinner'

class RatingInput(TextInput):
    dojo_type = 'dojox.form.Rating'
    valid_extra_attrs = [
        'max_value',
    ]
    field_attr_map = {
        'max_value': 'numStars',
    }

    class Media:
        css = {
            'all': ('%(base_url)s/dojox/form/resources/Rating.css' % {
                'base_url':dojo_config.dojo_base_url
            },)
        }

class DateInputAnim(DateInput):
    dojo_type = 'dojox.form.DateTextBox'
    class Media:
        css = {
            'all': ('%(base_url)s/dojox/widget/Calendar/Calendar.css' % {
                'base_url':dojo_config.dojo_base_url
            },)
        }

class DropDownSelect(Select):
    dojo_type = 'dojox.form.DropDownSelect'
    valid_extra_attrs = []
    class Media:
        css = {
            'all': ('%(base_url)s/dojox/form/resources/DropDownSelect.css' % {
                'base_url':dojo_config.dojo_base_url
            },)
        }

class CheckedMultiSelect(SelectMultiple):
    dojo_type = 'dojox.form.CheckedMultiSelect'
    valid_extra_attrs = []
    # TODO: fix attribute multiple=multiple 
    # seems there is a dependency in dojox.form.CheckedMultiSelect for dijit.form.MultiSelect,
    # but CheckedMultiSelect is not extending that

    class Media:
        css = {
            'all': ('%(base_url)s/dojox/form/resources/CheckedMultiSelect.css' % {
                'base_url':dojo_config.dojo_base_url
            },)
        }

class ComboBox(DojoWidgetMixin, widgets.Select):
    """Nearly the same as FilteringSelect, but ignoring the option value."""
    dojo_type = 'dijit.form.ComboBox'
    valid_extra_attrs = [
        'required', 
        'help_text',
    ]

class FilteringSelect(ComboBox):
    dojo_type = 'dijit.form.FilteringSelect'

class ComboBoxStore(TextInput):
    """A combobox that is receiving data from a given dojo data url.
    As default dojo.data.ItemFileReadStore is used. You can overwrite
    that behaviour by passing a different store name 
    (e.g. dojox.data.QueryReadStore).
    Usage:
        ComboBoxStore("/dojo-data-store-url/")
    """
    dojo_type = 'dijit.form.ComboBox'
    valid_extra_attrs = [
        'required', 
        'help_text',
    ]
    store = 'dojo.data.ItemFileReadStore'
    store_attrs = {}
    url = None
    
    def __init__(self, url, attrs=None, store=None, store_attrs={}):
        self.url = url
        if store:
            self.store = store
        if store_attrs:
            self.store_attrs = store_attrs
        self.extra_dojo_require.append(self.store)
        super(ComboBoxStore, self).__init__(attrs)
    
    def render(self, name, value, attrs=None):
        if value is None: value = ''
        store_id = self.get_store_id(getattr(attrs, "id", None), name)
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name, store=store_id)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(self._format_value(value))
        self.store_attrs.update({
            'dojoType': self.store,
            'url': self.url,
            'jsId':store_id
        })
        # TODO: convert store attributes to valid js-format (False => false, dict => {}, array = [])
        store_node = '<div%s></div>' % flatatt(self.store_attrs)
        return mark_safe(u'%s<input%s />' % (store_node, flatatt(final_attrs)))

    def get_store_id(self, id, name):
        return "_store_" + (id and id or name)

class FilteringSelectStore(ComboBoxStore):
    dojo_type = 'dijit.form.FilteringSelect'
    
class ListInput(DojoWidgetMixin, widgets.TextInput):
    dojo_type = 'dojox.form.ListInput'
    class Media:
        css = {
            'all': ('%(base_url)s/dojox/form/resources/ListInput.css' % {
                'base_url':dojo_config.dojo_base_url
            },)
        }

# THE RANGE SLIDER NEEDS A DIFFERENT REPRESENTATION WITHIN HTML
# SOMETHING LIKE:
# <div dojoType="dojox.form.RangeSlider"><input value="5"/><input value="10"/></div>
'''class HorizontalRangeSlider(HorizontalSliderInput):
    """This just can be used with a comma-separated-value like: 20,40"""
    dojo_type = 'dojox.form.HorizontalRangeSlider'
    alt_require = 'dojox.form.RangeSlider'

    class Media:
        css = {
            'all': ('%(base_url)s/dojox/form/resources/RangeSlider.css' % {
                'base_url':dojo_config.dojo_base_url
            },)
        }
'''
# TODO: implement
# dojox.form.RangeSlider
# dojox.form.MultiComboBox
# dojox.form.FileUploader

########NEW FILE########
__FILENAME__ = dojobuild
from optparse import make_option

import os
import re
import shutil
import subprocess # since python 2.4
import sys
from dojango.conf import settings

try:
    from django.core.management.base import BaseCommand, CommandError
except ImportError:
    # Fake BaseCommand out so imports on django 0.96 don't fail.
    BaseCommand = object
    class CommandError(Exception):
        pass

class Command(BaseCommand):
    '''This command is used to create your own dojo build. To start a build, you just
    have to type:
    
       ./manage.py dojobuild
    
    in your django project path. With this call, the default build profile "dojango" is used 
    and dojango.profile.js will act as its dojo build configuration. You can also add the 
    option --build_version=dev1.1.1 (for example) to mark the build with it.
    If you want to call a specific build profile from DOJO_BUILD_PROFILES, you just have to 
    append the profile name to this commandline call:
    
       ./manage.py dojobuild profilename
    
    '''
    
    option_list = BaseCommand.option_list + (
        make_option('--build_version', dest='build_version',
            help='Set the version of the build release (e.g. dojango_1.1.1).'),
        make_option('--minify', dest='minify', action="store_true", default=False,
            help='Does a dojo mini build (mainly removing unneeded files (tests/templates/...)'),
        make_option('--minify_extreme', dest='minify_extreme', action="store_true", default=False,
            help='Does a dojo extreme-mini build (keeps only what is defined in build profile and all media files)'),
        make_option('--prepare_zipserve', dest='prepare_zipserve', action="store_true", default=False,
            help='Zips everything you have built, so it can be deployed to Google AppEngine'),
    )
    help = "Builds a dojo release."
    args = '[dojo build profile name]'
    dojo_base_dir = None
    dojo_release_dir = None
    skip_files = None
    
    def handle(self, *args, **options):
        if len(args)==0:
            # with no param, we use the default profile, that is defined in the settings
            profile_name = settings.DOJO_BUILD_PROFILE
        else:
            profile_name = args[0]
        profile = self._get_profile(profile_name)
        used_src_version = profile['used_src_version'] % {'DOJO_BUILD_VERSION': settings.DOJO_BUILD_VERSION} # no dependencies to project's settings.py file!
        # used by minify_extreme!
        self.skip_files = profile.get("minify_extreme_skip_files", ())
        self.dojo_base_dir = "%(dojo_root)s/%(version)s" % \
                             {'dojo_root':settings.BASE_DOJO_ROOT, 
                             'version':used_src_version}
        # does the defined dojo-directory exist?
        util_base_dir = "%(dojo_base_dir)s/util" % {'dojo_base_dir':self.dojo_base_dir}
        if not os.path.exists(util_base_dir):
            raise CommandError('Put the the dojo source files (version \'%(version)s\') in the folder \'%(folder)s/%(version)s\' or set a different version in settings.DOJANGO_DOJO_BUILD_VERSION' % \
                               {'version':used_src_version,
                                'folder':settings.BASE_DOJO_ROOT})
        # check, if java is installed
        try:
            # ignoring output of the java call
            subprocess.call(settings.DOJO_BUILD_JAVA_EXEC, stdout=subprocess.PIPE) # will work with python >= 2.4
        except:
            raise CommandError('Please install java. You need it for building dojo.')
        buildscript_dir = os.path.abspath('%s/buildscripts' % util_base_dir)
        if settings.DOJO_BUILD_USED_VERSION < '1.2.0':
            executable = '%(java_exec)s -jar ../shrinksafe/custom_rhino.jar build.js' % \
                         {'java_exec':settings.DOJO_BUILD_JAVA_EXEC}
        else:
            # use the new build command line call!
            if(os.path.sep == "\\"):
                executable = 'build.bat'
            else:
                executable = './build.sh'
                # force executable rights!
                os.chmod(os.path.join(buildscript_dir, 'build.sh'), 0755)
        # use the passed version for building
        version = options.get('build_version', None)
        if not version:
            # if no option --build_version was passed, we use the default build version
            version = profile['build_version'] % {'DOJO_BUILD_VERSION': settings.DOJO_BUILD_VERSION} # no dependencies to project's settings.py file!
        # we add the version to our destination base path
        self.dojo_release_dir = '%(base_path)s/%(version)s' % {
                          'base_path':profile['base_root'] % {'BASE_MEDIA_ROOT':settings.BASE_MEDIA_ROOT},
                          'version':version} # we don't want to have a dependancy to the project's settings file!
        release_dir = os.path.abspath(os.path.join(self.dojo_release_dir, "../"))
        # the build command handling is so different between the versions!
        # sometimes we need to add /, sometimes not :-(
        if settings.DOJO_BUILD_USED_VERSION < '1.2.0':
            release_dir = release_dir + os.path.sep
        # setting up the build command
        build_addons = ""
        if settings.DOJO_BUILD_USED_VERSION >= '1.2.0':
            # since version 1.2.0 there is an additional commandline option that does the mini build (solved within js!)
            build_addons = "mini=true"
        exe_command = 'cd "%(buildscript_dir)s" && %(executable)s version=%(version)s releaseName="%(version)s" releaseDir="%(release_dir)s" %(options)s %(build_addons)s' % \
                      {'buildscript_dir':buildscript_dir,
                       'executable':executable,
                       'version':version,
                       'release_dir':release_dir,
                       'options':profile['options'] % {'BASE_MEDIA_ROOT':settings.BASE_MEDIA_ROOT},
                       'build_addons':build_addons}
        # print exe_command
        minify = options['minify']
        minify_extreme = options['minify_extreme']
        prepare_zipserve = options['prepare_zipserve']
        if settings.DOJO_BUILD_USED_VERSION < '1.2.0' and (minify or minify_extreme):
            self._dojo_mini_before_build()
        if sys.platform == 'win32': # fixing issue #39, if dojango is installed on a different drive
            exe_command = os.path.splitdrive(buildscript_dir)[0] + ' && ' + exe_command
        
        # do the build
        exit_code = os.system(exe_command)
        if exit_code: # != 0
            sys.exit(1) # dojobuild exits because of shrinksafe error
        if settings.DOJO_BUILD_USED_VERSION < '1.2.0':
            if minify or minify_extreme:
                self._dojo_mini_after_build()
        if minify_extreme:
            self._dojo_mini_extreme()
        if prepare_zipserve:
            self._dojo_prepare_zipserve()
        
    def _get_profile(self, name):
        default_profile_settings = settings.DOJO_BUILD_PROFILES_DEFAULT
        try:
            profile = settings.DOJO_BUILD_PROFILES[name]
            # mixing in the default settings for the build profiles!
            default_profile_settings.update(profile)
            return default_profile_settings
        except KeyError:
            raise CommandError('The profile \'%s\' does not exist in DOJO_BUILD_PROFILES' % name)
        
    def _dojo_mini_before_build(self):
        # FIXME: refs #6616 - could be able to set a global copyright file and null out build_release.txt
        shutil.move("%s/util/buildscripts/copyright.txt" % self.dojo_base_dir, "%s/util/buildscripts/_copyright.txt" % self.dojo_base_dir)
        if not os.path.exists("%s/util/buildscripts/copyright_mini.txt" % self.dojo_base_dir):
            f = open("%s/util/buildscripts/copyright.txt" % self.dojo_base_dir, 'w')
            f.write('''/*
Copyright (c) 2004-2008, The Dojo Foundation All Rights Reserved.
Available via Academic Free License >= 2.1 OR the modified BSD license.
see: http://dojotoolkit.org/license for details
*/''')
            f.close()
        else:
            shutil.copyfile("%s/util/buildscripts/copyright_mini.txt" % self.dojo_base_dir, "%s/util/buildscripts/copyright.txt" % self.dojo_base_dir)
        shutil.move("%s/util/buildscripts/build_notice.txt" % self.dojo_base_dir, "%s/util/buildscripts/_build_notice.txt" % self.dojo_base_dir)
        # create an empty build-notice-file
        f = open("%s/util/buildscripts/build_notice.txt" % self.dojo_base_dir, 'w')
        f.close()
    
    def _dojo_mini_after_build(self):
        try: 
            '''Copied from the build_mini.sh shell script (thank you Pete Higgins :-))'''
            if not os.path.exists(self.dojo_release_dir):
                raise CommandError('The dojo build failed! Check messages above!')
            else:
                # remove dojox tests and demos - they all follow this convetion
                self._remove_files('%s/dojox' % self.dojo_release_dir, ('^tests$', '^demos$'))
                # removed dijit tests
                dijit_tests = ("dijit/tests", "dijit/demos", "dijit/bench", 
                               "dojo/tests", "util",
                               "dijit/themes/themeTesterImages")
                self._remove_folders(dijit_tests)
                # noir isn't worth including yet
                noir_theme_path = ("%s/dijit/themes/noir" % self.dojo_release_dir,)
                self._remove_folders(noir_theme_path)
                # so the themes are there, lets assume that, piggyback on noir: FIXME later
                self._remove_files('%s/dijit/themes' % self.dojo_release_dir, ('^.*\.html$',))
                self._remove_files(self.dojo_release_dir, ('^.*\.uncompressed\.js$',))
                # WARNING: templates have been inlined into the .js -- if you are using dynamic templates,
                # or other build trickery, these lines might not work!
                self._remove_files("dijit/templates", ("^\.html$",))
                self._remove_files("dijit/form/templates", ("^\.html$",))
                self._remove_files("dijit/layout/templates", ("^\.html$",))
                # .. assume you didn't, and clean up all the README's (leaving LICENSE, mind you)
                self._remove_files('%s/dojo/dojox' % self.dojo_release_dir, ('^README$',))
                dojo_folders = ("dojo/_base",)
                self._remove_folders(dojo_folders)
                os.remove("%s/dojo/_base.js" % self.dojo_release_dir)
                os.remove("%s/dojo/build.txt" % self.dojo_release_dir)
                os.remove("%s/dojo/tests.js" % self.dojo_release_dir)
        except Exception, e:
            print e
            sys.exit(1)
        # cleanup from above, refs #6616
        shutil.move("%s/util/buildscripts/_copyright.txt" % self.dojo_base_dir, "%s/util/buildscripts/copyright.txt" % self.dojo_base_dir)
        shutil.move("%s/util/buildscripts/_build_notice.txt" % self.dojo_base_dir, "%s/util/buildscripts/build_notice.txt" % self.dojo_base_dir)
        
    def _remove_folders(self, folders):
        for folder in folders:
            if os.path.exists("%s/%s" % (self.dojo_release_dir, folder)):
                shutil.rmtree("%s/%s" % (self.dojo_release_dir, folder))
            
    def _remove_files(self, base_folder, regexp_list):
        for root, dirs, files in os.walk(base_folder):
            for file in files:
                # remove all html-files
                for regexp in regexp_list:
                    my_re = re.compile(regexp)
                    if my_re.match(file):
                        os.remove(os.path.join(root, file))
            for dir in dirs:
                for regexp in regexp_list:
                    my_re = re.compile(regexp)
                    if my_re.match(dir):
                        shutil.rmtree(os.path.join(root, dir))
    
    SKIP_FILES = (
        '(.*\.png)',
        '(.*\.gif)',
        '(.*\.jpg)',
        '(.*\.svg)',
        '(.*\.swf)',
        '(.*\.fla)',
        '(.*\.mov)',
        '(.*\.smd)',
        '(dojo/_firebug/firebug\..*)',
        '(dojo/dojo\.(xd\.)?js)',
        '(dojo/nls/.*)',
        '(dojo/resources/dojo\.css)',
        '(dojo/resources/blank\.html)',
        '(dojo/resources/iframe_history\.html)',
        '(dijit/themes/tundra/tundra\.css)',
        '(dijit/themes/soria/soria\.css)',
        '(dijit/themes/nihilo/nihilo\.css)',
        '(dojox/dtl/contrib/.*)',
        '(dojox/dtl/ext-dojo/.*)',
        '(dojox/dtl/filter/.*)',
        '(dojox/dtl/render/.*)',
        '(dojox/dtl/tag/.*)',
        '(dojox/dtl/utils/.*)',
        '(dojox/io/proxy/xip_.*\.html)',
    )
    def _dojo_mini_extreme(self):
        """
        This method removes all js files and just leaves all layer dojo files and static files (like "png", "gif", "svg", "swf", ...)
        """
        # prepare the regexp of files not to be removed!
        # mixin the profile specific skip files
        skip_files = self.SKIP_FILES + self.skip_files
        my_re = re.compile('^(.*/)?(%s)$' % "|".join(skip_files))
        try:
            '''Copied from the build_mini.sh shell script'''
            if not os.path.exists(self.dojo_release_dir):
                raise CommandError('The dojo build failed! Check messages above!')
            else:
                for root, dirs, files in os.walk(self.dojo_release_dir):
                    for file in files:
                        # remove all html-files
                        my_file = os.path.abspath(os.path.join(root, file))
                        if not my_re.match(my_file):
                            os.remove(my_file)
                # now remove all empty directories
                for root, dirs, files in os.walk(self.dojo_release_dir):
                    for dir in dirs:
                        try:
                            # just empty directories will be removed!
                            os.removedirs(os.path.join(root, dir))
                        except OSError:
                            pass
        except Exception, e:
            print e
            sys.exit(1)

    DOJO_ZIP_SPECIAL = {'dojox': ['form', 'widget', 'grid']} # these modules will be zipped separately
    def _dojo_prepare_zipserve(self):
        """
        Creates zip packages for each dojo module within the current release folder.
        It splits the module dojox into several modules, so it fits the 1000 files limit of
        Google AppEngine.
        """
        for folder in os.listdir(self.dojo_release_dir):
            module_dir = '%s/%s' % (self.dojo_release_dir, folder)
            if os.path.isdir(module_dir):
                if folder in self.DOJO_ZIP_SPECIAL.keys():
                    for special_module in self.DOJO_ZIP_SPECIAL[folder]:
                        special_module_dir = os.path.join(module_dir, special_module)
                        create_zip(special_module_dir, 
                                   '%(base_module)s/%(special_module)s' % {
                                       'base_module': folder,
                                       'special_module': special_module
                                   },
                                   '%(module_dir)s.%(special_module)s.zip' % {
                                       'module_dir': module_dir,
                                       'special_module': special_module
                                   }
                        )
                        # remove the whole special module
                        shutil.rmtree(special_module_dir)
                # now add the 
                create_zip(module_dir, folder, module_dir + ".zip")
                shutil.rmtree(module_dir)
                        

def zipfolder(path, relname, archive):
    paths = os.listdir(path)
    for p in paths:
        p1 = os.path.join(path, p) 
        p2 = os.path.join(relname, p)
        if os.path.isdir(p1): 
            zipfolder(p1, p2, archive)
        else:
            archive.write(p1, p2) 

def create_zip(path, relname, archname):
    import zipfile
    archive = zipfile.ZipFile(archname, "w", zipfile.ZIP_DEFLATED)
    if os.path.isdir(path):
        zipfolder(path, relname, archive)
    else:
        archive.write(path, relname)
    archive.close()

########NEW FILE########
__FILENAME__ = dojoload
import os
import sys
import urllib
import zipfile

from optparse import make_option
from dojango.conf import settings

try:
    from django.core.management.base import BaseCommand, CommandError
except ImportError:
    # Fake BaseCommand out so imports on django 0.96 don't fail.
    BaseCommand = object
    class CommandError(Exception):
        pass

class Command(BaseCommand):
    '''This command helps with downloading a dojo source release. To download 
    the currently defined 'settings.DOJANGO_DOJO_VERSION' just type:

       ./manage.py dojoload

    in your django project path. For downloading a specific version a version 
    string can be appended.

       ./manage.py dojoload --version 1.2.3
    '''

    option_list = BaseCommand.option_list + (
        make_option('--dojo_version', dest='dojo_version',
            help='Download a defined version (e.g. 1.2.3) instead of the default (%s).' % settings.DOJO_VERSION),
    )
    help = "Downloads a dojo source release."
    dl_url = "http://download.dojotoolkit.org/release-%(version)s/dojo-release-%(version)s-src.zip"
    dl_to_path = settings.BASE_DOJO_ROOT + "/dojo-release-%(version)s-src.zip"
    move_from_dir = settings.BASE_DOJO_ROOT + "/dojo-release-%(version)s-src"
    move_to_dir = settings.BASE_DOJO_ROOT + "/%(version)s"
    extract_to_dir = settings.BASE_DOJO_ROOT
    total_kb = 0
    downloaded_kb = 0


    def handle(self, *args, **options):
        version = settings.DOJO_VERSION
        passed_version = options.get('dojo_version', None)
        if passed_version:
            version = passed_version
        dl_url = self.dl_url % {'version': version}
        dl_to_path = self.dl_to_path % {'version': version}
        move_from_dir = self.move_from_dir % {'version': version}
        move_to_dir = self.move_to_dir % {'version': version}
        if os.path.exists(move_to_dir):
            raise CommandError("You've already downloaded version %(version)s to %(move_to_dir)s" % {
                'version':version,
                'move_to_dir':move_to_dir,
            })
        else:
            print "Downloading %s to %s" % (dl_url, dl_to_path)
            self.download(dl_url, dl_to_path)
            if self.total_kb == -1: # stupid bug in urllib (there is no IOError thrown, when a 404 occurs
                os.remove(dl_to_path)
                print ""
                raise CommandError("There is no source release at %(url)s" % {
                    'url':dl_url,
                    'dir':dl_to_path,
                })
            print "\nExtracting file %s to %s" % (dl_to_path, move_to_dir)
            self.unzip_file_into_dir(dl_to_path, self.extract_to_dir)
            os.rename(move_from_dir, move_to_dir)
            print "Removing previous downloaded file %s" % dl_to_path
            os.remove(dl_to_path)

    def download(self, dl_url, to_dir):
        try:
            urllib.urlretrieve(dl_url, to_dir, self.dl_reporthook)
        except IOError:
            raise CommandError("Downloading from %(url)s to directory %(dir)s failed." % {
                'url':dl_url,
                'dir':to_dir,
            })

    def dl_reporthook(self, block_count, block_size, total_size):
        self.total_kb = total_size / 1024
        self.downloaded_kb = (block_count * block_size) / 1024
        sys.stdout.write('%s%d KB of %d KB downloaded' % (
                40*"\b", # replacing the current line
                self.downloaded_kb,
                self.total_kb
            )
        )
        sys.stdout.flush()

    def unzip_file_into_dir(self, file, dir):
        try:
            os.mkdir(dir)
        except:
            pass
        zfobj = zipfile.ZipFile(file)
        for name in zfobj.namelist():
            if name.endswith('/'):
                os.mkdir(os.path.join(dir, name))
            else:
                outfile = open(os.path.join(dir, name), 'wb')
                outfile.write(zfobj.read(name))
                outfile.close()

########NEW FILE########
__FILENAME__ = middleware
import re

from django.conf import settings
from django.http import HttpResponseServerError
from django.utils.encoding import smart_unicode

from dojango.util import dojo_collector

class AJAXSimpleExceptionResponse:
    """Thanks to newmaniese of http://www.djangosnippets.org/snippets/650/ .

    Full doc (copied from link above).
    When debugging AJAX with Firebug, if a response is 500, it is a
    pain to have to view the entire source of the pretty exception page.
    This is a simple middleware that just returns the exception without
    any markup. You can add this anywhere in your python path and then
    put it in you settings file. It will only unprettify your exceptions
    when there is a XMLHttpRequest header. Tested in FF2 with the YUI XHR.
    Comments welcome.
    """
    def process_exception(self, request, exception):
        #if settings.DEBUG:
        # we should use that setting in future version of dojango
        #if request.is_ajax(): # new in django version 1.0
        if request.META.get('HTTP_X_REQUESTED_WITH', None) == 'XMLHttpRequest':
            import sys, traceback
            (exc_type, exc_info, tb) = sys.exc_info()
            response = "%s\n" % exc_type.__name__
            response += "%s\n\n" % exc_info
            response += "TRACEBACK:\n"
            for tb in traceback.format_tb(tb):
                response += "%s\n" % tb
            return HttpResponseServerError(response)

class DojoCollector:
    """This middleware enables/disables the global collector object for each 
    request. It is needed, when the dojango.forms integration is used.
    """
    def process_request(self, request):
        dojo_collector.activate()

    def process_response(self, request, response):
        dojo_collector.deactivate()
        return response
    
class DojoAutoRequire:
    """
    USE THE MIDDLEWARE ABOVE (IT IS USING A GLOBAL COLLECTOR OBEJCT)!
    
    This middleware detects all dojoType="*" definitions in the returned
    response and uses that information to generate all needed dojo.require
    statements and places a <script> block in front of the </body> tag.

    It is just processed for text/html documents!
    """
    def process_response(self, request, response):
        # just process html-pages that were returned by a view
        if response and\
           response.get("Content-Type", "") == "text/html; charset=%s" % settings.DEFAULT_CHARSET and\
           len(response.content) > 0: # just for html pages!
            dojo_type_re = re.compile('\sdojoType\s*\=\s*[\'\"]([\w\d\.\-\_]*)[\'\"]\s*')
            unique_dojo_modules = set(dojo_type_re.findall(response.content)) # we just need each module once
            if len(unique_dojo_modules) > 0:
                tail, sep, head = smart_unicode(response.content).rpartition("</body>")
                response.content = "%(tail)s%(script)s%(sep)s%(head)s" % {
                    'tail':tail,
                    'script':'<script type="text/javascript">\n%s\n</script>\n' % self._get_dojo_requires(unique_dojo_modules),
                    'sep':sep,
                    'head':head,
                }
        return response

    def _get_dojo_requires(self, dojo_modules):
        return "\n".join([u"dojo.require(\"%s\");" % require for require in dojo_modules])

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = dojango_base
from django import template

from dojango.conf import settings # using the app-specific settings
from dojango.util import json_encode as util_json_encode
from dojango.util.config import Config

register = template.Library()

class DojangoParamsNode(template.Node):
    '''We set the DOJANGO context with this node!'''
    def __init__(self, profile=settings.DOJO_PROFILE, version=settings.DOJO_VERSION):
        self.profile = profile
        self.version = version
    def render(self, context):
        config = Config(self.profile, self.version)
        if not config.config:
            raise template.TemplateSyntaxError, "Could not find the profile '%s' in the DOJANGO_DOJO_PROFILES settings" % (self.profile)
        if not config.dojo_base_url:
            raise template.TemplateSyntaxError, "The version %s is not supported by the dojango profile '%s'" % (self.version, self.profile)
        context['DOJANGO'] = config.get_context_dict()
        return ''
        
@register.tag
def set_dojango_context(parser, token):
    '''Sets the DOJANGO context constant in the context.
    It is also possible to set the used profile/version with it, e.g.:
      {% set_dojango_context "google" "1.1.1" %}'''
    tlist = token.split_contents()
    # the profile was passed
    if len(tlist) == 2:
        return DojangoParamsNode(tlist[1][1:-1])
    if len(tlist) == 3:
        return DojangoParamsNode(tlist[1][1:-1], tlist[2][1:-1])
    return DojangoParamsNode()

# TODO: Implement template-tag for layout components to register e.g. dojoType="dijit.layout.TabContainer"
# {% dojo_type "dijit.layout.TabContainer" %}
# This template tag informs the collector about new modules


########NEW FILE########
__FILENAME__ = dojango_filters
from django.template import Library

from dojango.util import json_encode

register = Library()

@register.filter
def json(input):
    return json_encode(input)

########NEW FILE########
__FILENAME__ = dojango_grid
from django import template
from django.db.models import get_model
from django.db import models
from django.template import TemplateSyntaxError
from django.template.loader import get_template

from dojango.util import extract_nodelist_options
from dojango.util.dojo_collector import add_module
from dojango.util.perms import access_model
from django.core.urlresolvers import reverse, NoReverseMatch

import random

register = template.Library()
disp_list_guid = 0
 
FIELD_ATTRIBUTES = ('column_width', 'label', 'formatter')

@register.tag
def simple_datagrid(parser, token):
    """
    Generates a dojo datagrid for a given app's model.
    i.e.  {% simple_datagrid myapp mymodel %}
    """
    bits = token.split_contents()
    if len(bits) < 3:
        raise TemplateSyntaxError, "You have to pass app- and model-name to {% simple_datagrid app model %}"
    return DatagridNode(bits[1],bits[2],None)

@register.tag
def datagrid(parser, token):
    """
     Generates a dojo datagrid for a given app's model. renders
     the contents until {% enddatagrid %} and takes options in
     the form of option=value per line.
    """
    bits = token.split_contents()
    nodelist = parser.parse(('enddatagrid',))
    parser.delete_first_token()
    app, model = None, None
    if len(bits) == 3:
        app = bits[1]
        model = bits[2]
    return DatagridNode(app, model,nodelist)
                 
class DatagridNode(template.Node):
    """
    If nodelist is not None this will render the contents under the templates
    context then render the dojango/templatetag/datagrid_disp.html template
    under a context created by the options parsed out of the block.
    
    Available options:
    
    list_display:      list or tuple of model attributes (model fields or model functions). defaults to all of the sql fields of the model
    column_width:      dict with model attribute:width
    default_width:     default width if not specified by column_width. defaults to "auto"
    width:             width of the datagrid, defaults to "100%"
    height:            height of datagrid, defaults to "100%"
    id:                id of datagird, optional but useful to if planning on using dojo.connect to the grid.
    label:             dict of attribute:label for header. (other ways exist of setting these)
    query:             way to specify conditions for the table. i.e. to only display elements whose id>10: query={ 'id__gt':10 }
    search:            list or tuple of fields to query against when searching
    show_search:       Display search field (default: True). If False, you'll create your custom search field and call do_{{id}}_search 
    nosort:            fields not to sort on
    formatter:         dict of attribute:js formatter function
    json_store_url:    URL for the ReadQueryStore 
    selection_mode:    dojo datagrid selectionMode
    """
    model = None
    app_name = None
    model_name = None

    def __init__(self, app, model, options):
        if app and model:
            self.model = get_model(app,model)
            self.app_name = app
            self.model_name = model
        self.options = options
        
    def render(self, context):
        opts = {}
        global disp_list_guid
        disp_list_guid = disp_list_guid + 1
        # add dojo modules
        add_module("dojox.data.QueryReadStore")
        add_module("dojox.grid.DataGrid")
        
        # Setable options, not listed: label, query, search, nosort
        if self.model:
            opts['list_display'] = [x.attname for x in self.model._meta.fields]
        opts['width'] = {}
        opts['label'] = {}
        opts['default_width'] = "auto"
        opts['width'] = "100%"
        opts['height'] = "100%"
        opts['query']={}
        opts['query']['inclusions']=[]
        
        opts['id'] = "disp_list_%s_%s" % (disp_list_guid,random.randint(10000,99999))
        try:
            # reverse lookup of the datagrid-list url (see dojango/urls.py)
            if self.model:
                opts['json_store_url'] = reverse("dojango-datagrid-list", args=(self.app_name, self.model_name))
        except NoReverseMatch:
            pass
        
        # User overrides
        if self.options:
            opts.update(extract_nodelist_options(self.options,context))
        if not opts['query'].has_key('inclusions'): opts['query']['inclusions'] = []
            
        # we must ensure that the json_store_url is defined
        if not opts.get('json_store_url', False):
            raise TemplateSyntaxError, "Please enable the url 'dojango-datagrid-list' in your urls.py or pass a 'json_store_url' to the datagrid templatetag."
        
        # Incase list_display was passed as tuple, turn to list for mutability
        if not self.model and not opts.get('list_display', False):
            raise TemplateSyntaxError, "'list_display' not defined. If you use your own 'json_store_url' you have to define which fields are visible."
        opts['list_display'] = list(opts['list_display'])
        
        # Config for template
        opts['headers'] = []

        # Get field labels using verbose name (take into account i18n), will be used
        # for column labels
        verbose_field_names = {}
        if self.model:
            verbose_field_names = dict([(f.name, f.verbose_name) for f in self.model._meta.fields])

        for field in opts['list_display']:
            ret = {'attname':field}
            for q in FIELD_ATTRIBUTES:
                if opts.has_key(q) and opts[q].has_key(field):
                     ret[q] = opts[q][field]
            # custom default logic
            if not ret.has_key('label'):
                ret['label'] = verbose_field_names.get(field, field.replace('_', ' '))
            if not ret.has_key('column_width'):
                ret['column_width']= opts['default_width']
            # add as inclusion if not a attribute of model
            if self.model and not field in map(lambda x: x.attname, self.model._meta.fields):
                opts['query']['inclusions'].append(field)
            # add to header
            opts['headers'].append(ret)
              
        # no sort fields
        if opts.has_key("nosort"): 
            opts['nosort'] = "".join(["||row==%s"%(opts['list_display'].index(r)+1) for r in opts['nosort']])
        
        # additional context info/modifications
        opts["model_name"] = self.model_name
        opts["app_name"] = self.app_name
        opts['query']['inclusions'] = ",".join(opts['query']['inclusions'])
        if opts.has_key('search'):
            opts['search_fields'] = ",".join(opts['search'])
            opts['show_search'] = opts.get('show_search', True)
        else:
            opts['show_search'] = False

        # return rendered template
        return get_template("dojango/templatetag/datagrid_disp.html").render(template.Context(opts))

########NEW FILE########
__FILENAME__ = urls
from django import VERSION as django_version
if django_version >= (1, 5, 0):
    from django.conf.urls import patterns, url
else:
    from django.conf.urls.defaults import *
from django.conf import settings

from dojango.util import media

urlpatterns = patterns('dojango',
    url(r'^test/$', 'views.test', name='dojango-test'),
    url(r'^test/countries/$', 'views.test_countries'),
    url(r'^test/states/$', 'views.test_states'),
    # Note: define accessible objects in DOJANGO_DATAGRID_ACCESS setting
    url(r'^datagrid-list/(?P<app_name>.+)/(?P<model_name>.+)/$', 'views.datagrid_list', name="dojango-datagrid-list"),
)

if settings.DEBUG:
    # serving the media files for dojango / dojo (js/css/...)
    urlpatterns += media.url_patterns

########NEW FILE########
__FILENAME__ = config
from dojango.conf import settings # using the app-specific settings
from dojango.util import dojo_collector
from dojango.util import media

class Config:

    profile = None
    version = None
    config = None
    dojo_base_url = None

    def __init__(self, profile=settings.DOJO_PROFILE, version=settings.DOJO_VERSION):
        self.profile = profile
        self.version = version
        self.config = self._get_config()
        self.dojo_base_url = self._get_dojo_url()

    def _get_config(self):
        '''Getting a config dictionary using the giving profile. See the profile list in conf/settings.py'''
        try:
            config = settings.DOJO_PROFILES[self.profile]
            return config
        except KeyError:
            pass
        return None

    def _get_dojo_url(self):
        '''Getting the dojo-base-path dependend on the profile and the version'''
        # the configuration of this profile (e.g. use crossdomain, uncompressed version, ....)
        # if no version is set you are free to use your own
        if self.config == None or not self.version in self.config.get('versions', (self.version)):
            return None
        # so we simply append our own profile without importing the dojango settings.py to the project's settings.py
        config_base_url = self.config.get('base_url', '') % \
                          {'BASE_MEDIA_URL':settings.BASE_MEDIA_URL,
                           'BUILD_MEDIA_URL':settings.BUILD_MEDIA_URL}
        # and putting the complete url together
        return "%(base)s/%(version)s" % {"base":config_base_url,
            "version":self.version}

    def get_context_dict(self):
        ret = {}
        # all constants must be uppercase
        for key in self.config:
            ret[key.upper()] = self.config[key]
        ret['IS_LOCAL_BUILD'] = self.config.get("is_local_build", False)
        ret['IS_LOCAL'] = self.config.get("is_local", False)
        ret['UNCOMPRESSED'] = self.config.get("uncompressed", False)
        ret['USE_GFX'] = self.config.get("use_gfx", False)
        ret['VERSION'] = self.version
        # preparing all dojo related urls here
        ret['THEME_CSS_URL'] = self.theme_css_url()
        ret['THEME'] = settings.DOJO_THEME
        ret['BASE_MEDIA_URL'] = settings.BASE_MEDIA_URL
        ret['DOJO_BASE_PATH'] = self.version > '1.6' and self.dojo_base_path() or '%s/dojo/' % self.dojo_base_path()
        ret['DOJO_URL'] = self.dojo_url()
        ret['DIJIT_URL'] = self.dijit_url()
        ret['DOJOX_URL'] = self.dojox_url()
        ret['DOJO_SRC_FILE'] = self.dojo_src_file()
        ret['DOJANGO_SRC_FILE'] = self.dojango_src_file()
        ret['DEBUG'] = settings.DOJO_DEBUG
        ret['COLLECTOR'] = dojo_collector.get_modules()
        ret['CDN_USE_SSL'] = settings.CDN_USE_SSL
        # adding all installed dojo-media namespaces
        ret.update(self.dojo_media_urls())
        return ret

    def dojo_src_file(self):
        '''Get the main dojo javascript file
        Look in conf/settings.py for available profiles.'''
        # set some special cases concerning the configuration
        uncompressed_str = ""
        gfx_str = ""
        xd_str = ""
        if self.config.get('uncompressed', False):
            uncompressed_str = ".uncompressed.js"
        if self.config.get('use_gfx', False):
            gfx_str = "gfx-"
        if self.config.get('use_xd', False):
            xd_str = ".xd"
        return "%(path)s/dojo/%(gfx)sdojo%(xd)s.js%(uncompressed)s" % {"path":self.dojo_base_url,
            "xd": xd_str,
            "gfx": gfx_str,
            "uncompressed": uncompressed_str}

    def dojango_src_file(self):
        '''Getting the main javascript profile file url of this awesome app :-)
        You need to include this within your html to achieve the advantages
        of this app.
        TODO: Listing some advantages!
        '''
        return "%s/dojango.js" % self.dojango_url()

    def dojo_media_urls(self):
        '''Getting dict of 'DOJONAMESPACE_URL's for each installed dojo ns in app/dojo-media'''
        ret = {}
        for app in media.dojo_media_library:
            if media.dojo_media_library[app]:
                for dojo_media in media.dojo_media_library[app]:
                    ret["%s_URL" % dojo_media[1].upper()] = '%s/%s' % (self.dojo_base_path(), dojo_media[1])
        return ret

    def dojango_url(self):
        return '%s/%s/dojango' % (settings.BASE_MEDIA_URL, self.version)

    def dojo_url(self):
        '''Like the "dojango_dojo_src_file" templatetag, but just returning the base path
        of dojo.'''
        return "%s/dojo" % self.dojo_base_url

    def dijit_url(self):
        '''Like the "dojango_dojo_src_file" templatetag, but just returning the base path
        of dijit.'''
        return "%s/dijit" % self.dojo_base_url

    def dojox_url(self):
        '''Like the "dojango_dojo_src_file" templatetag, but just returning the base path
        of dojox.'''
        return "%s/dojox" % self.dojo_base_url

    def dojo_base_path(self):
        '''djConfig.baseUrl can be used to mix an external xd-build with some local dojo modules.
        If we use an external build it must be '/' and for a local version, we just have to set the
        path to the dojo path.
        Use it within djConfig.baseUrl by appending "dojo/". 
        '''
        base_path = '%s/%s' % (settings.BASE_MEDIA_URL, self.version)
        if self.config.get('is_local', False):
             base_path = self.dojo_base_url
        return base_path

    def theme_css_url(self):
        '''Like the "dojango_dojo_src_file" templatetag, but returning the theme css path. It uses the
        DOJO_THEME and DOJO_THEME_PATH settings to determine the right path.'''
        if settings.DOJO_THEME_URL:
            # if an own them is used, the theme must be located in themename/themename.css
            return settings.DOJO_THEME_URL + "/%s/%s.css" % (settings.DOJO_THEME, settings.DOJO_THEME)
        return "%s/dijit/themes/%s/%s.css" % (self.dojo_base_url, settings.DOJO_THEME, settings.DOJO_THEME)

    def theme(self):
        return settings.DOJO_THEME

########NEW FILE########
__FILENAME__ = dojo_collector
from threading import local

__all__ = ['activate', 'deactivate', 'get_collector', 'add_module']

_active = local()

def activate():
    """
    Activates a global accessible object, where we can save information about
    required dojo modules.
    """
    class Collector:
        used_dojo_modules = []

        def add(self, module):
            # just add a module once!
            if not module in self.used_dojo_modules:
                self.used_dojo_modules.append(module)

    _active.value = Collector()

def deactivate():
    """
    Resets the currently active global object
    """
    if hasattr(_active, "value"):
        del _active.value

def get_collector():
    """Returns the currently active collector object."""
    t = getattr(_active, "value", None)
    if t is not None:
        try:
            return t
        except AttributeError:
            return None
    return None

def get_modules():
    collector = get_collector()
    if collector is not None:
        return collector.used_dojo_modules
    return []

def add_module(module):
    collector = get_collector()
    if collector is not None:
        collector.add(module)
    # otherwise do nothing
    pass


########NEW FILE########
__FILENAME__ = form
from dojango.util import is_number

def get_combobox_data(request):
    """Return the standard live search data that are posted from a ComboBox widget.
    summary:
        A ComboBox using the QueryReadStore sends the following data:
            name - is the search string (it always ends with a '*', that is how the dojo.data API defined it)
            start - the paging start
            count - the number of entries to return
        The ComboBox and QueryReadStore usage should be like this:
            <div dojoType="dojox.data.QueryReadStore" jsId="topicStore" url="/topic/live-search/..." requestMethod="post" doClientPaging="false"></div>
            <input {% dojo_widget "rs.widget.Tagcombobox" "addTopicInput" %} store="topicStore" style="width:150px" pageSize="20" />
        The most important things here are the attributes requestMethod and doClientPaging!
        The 'doClientPaging' makes the combobox send 'start' and 'count' parameters and the server
        shall do the paging.
        
    returns:
        a tuple containing
            search_string - the string typed into the combobox
            start - at which data set to start
            end - at which data set to stop
        'start' and 'end' are already prepared to be directly used in the 
        limit part of the queryset, i.e. Idea.objects.all()[start:end]
    
    throws:
        Exception - if the request method is not POST.
        ValueError - if start or count parameter is not an int.
    """
    if not request.method=='POST':
        raise Exception('POST request expected.')
    string = request.POST.get('name', '')
    if string.endswith('*'): # Actually always the case.
        string = string[:-1]
    start = int(request.POST.get('start', 0))
    end = request.POST.get('count', 10)
    if not is_number(end): # The dojo combobox may return "Infinity" tsss
        end = 10
    end = start+int(end)
    return string, start, end
########NEW FILE########
__FILENAME__ = media
from django import VERSION as django_version
from django.conf import settings
from dojango.conf import settings as dojango_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils._os import safe_join
from django.utils.encoding import force_str
if django_version >= (1, 5, 0):
    from django.conf.urls import patterns
else:
    from django.conf.urls.defaults import patterns
from os import path, listdir

def find_app_dir(app_name):
    """Given an app name (from settings.INSTALLED_APPS) return the abspath
    to that app directory"""
    i = app_name.rfind('.')
    if i == -1:
        m, a = app_name, None
    else:
        m, a = app_name[:i], app_name[i+1:]
    try:
        if a is None:
            mod = __import__(m, {}, {}, [])
        else:
            mod = getattr(__import__(m, {}, {}, [force_str(a)]), a)
        return path.dirname(path.abspath(mod.__file__))
    except ImportError, e:
        raise ImproperlyConfigured, 'ImportError %s: %s' % (app_name, e.args[0])

def find_app_dojo_dir(app_name):
    """Checks, if a dojo-media directory exists within a given app and returns the absolute path to it."""
    base = find_app_dir(app_name)
    if base:
        media_dir = safe_join(base, 'dojo-media')
        if path.isdir(media_dir): return media_dir
    return None # no dojo-media directory was found within that app

def find_app_dojo_dir_and_url(app_name):
    """Returns a list of tuples of dojo modules within an apps 'dojo-media' directory.
    Each tuple contains the abspath to the module directory and the module name.
    """
    ret = []
    media_dir = find_app_dojo_dir(app_name)
    if not media_dir: return None
    for d in listdir(media_dir):
        if path.isdir(safe_join(media_dir, d)):
            if d not in ("src", "release") and not d.startswith("."):
                ret.append(tuple([safe_join(media_dir, d), "%(module)s" % {
                    'module': d
                }]))
    return tuple(ret)

dojo_media_library = dict((app, find_app_dojo_dir_and_url(app))
                         for app in settings.INSTALLED_APPS)
dojo_media_apps = tuple(app for app in settings.INSTALLED_APPS
                       if dojo_media_library[app])

def _check_app_dojo_dirs():
    """Checks, that each dojo module is just present once. Otherwise it would throw an error."""
    check = {}
    for app in dojo_media_apps:
        root_and_urls = dojo_media_library[app]
        for elem in root_and_urls:
            root, url = elem
            if url in check and root != dojo_media_library[check[url]][0]:
                raise ImproperlyConfigured, (
                    "Two apps (%s, %s) contain the same dojo module (%s) in the dojo-media-directory pointing to two different directories (%s, %s)" %
                    (repr(app), repr(check[url]), repr(root.split("/")[-1]), repr(root), repr(dojo_media_library[check[url]][0][0])))
            check[url] = app

def _build_urlmap():
    """Creating a url map for all dojo modules (dojo-media directory), that are available within activated apps."""
    seen = {}
    valid_urls = [] # keep the order!
    for app in dojo_media_apps:
        root_and_urls = dojo_media_library[app]
        for elem in root_and_urls:
            root, url = elem
            if url.startswith('/'): url = url[1:]
            if url in seen: continue
            valid_urls.append((url, root))
            seen[url] = root
    base_url = dojango_settings.DOJO_MEDIA_URL # dojango_settings.BASE_MEDIA_URL
    if base_url.startswith('/'): base_url = base_url[1:]
    # all new modules need to be available next to dojo, so we need to allow a version-string in between
    # e.g. /dojo-media/1.3.1/mydojonamespace == /dojo-media/1.2.0/mydojonamespace
    valid_urls = [("%(base_url)s/([\w\d\.\-]*/)?%(url)s" % {
        'base_url': base_url,
        'url': m[0]
    }, m[1]) for m in valid_urls]
    
    valid_urls.append(("%(base_url)s/release/" % {'base_url': base_url}, path.join(dojango_settings.BASE_MEDIA_ROOT, "release")))
    valid_urls.append(("%(base_url)s/" % {'base_url': base_url}, path.join(dojango_settings.BASE_MEDIA_ROOT, "src")))
    return valid_urls

_check_app_dojo_dirs() # is each dojo module just created once?

dojo_media_urls = _build_urlmap()
urls = [ ('^%s(?P<path>.*)$' % url, 'serve', {'document_root': root, 'show_indexes': True} )
         for url, root in dojo_media_urls ]
url_patterns = patterns('django.views.static', *urls) # url_patterns that can be used directly within urls.py

########NEW FILE########
__FILENAME__ = perms
from django.conf import settings

def access_model(app_name, model_name, request=None, instance=None):
    """
    Return true to allow access to a given instance of app_name.model_name
    """
    acl = getattr(settings, "DOJANGO_DATAGRID_ACCESS", [])
    for x in acl:
        try:
            if x.find(".")>0:
                app,model = x.split('.')
                if app_name == app and model_name==model: return True
            else:
                if app_name == x or model_name==x: return True
        except:
            pass
    return False

def access_model_field(app_name, model_name, field_name, request=None, instance=None):
    """
    Return true to allow access of a given field_name to model app_name.model_name given
    a specific object of said model.
    """
    # in django version 1.2 a new attribute is on all models: _state of type ModelState
    # that field shouldn't be accessible
    return not field_name in ('delete', '_state',)
########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.db.models import get_model
from django.db import models
from django.shortcuts import render_to_response
from django.conf import settings

from dojango.util import to_dojo_data, json_encode
from dojango.decorators import json_response
from dojango.util import to_dojo_data
from dojango.util.form import get_combobox_data
from dojango.util.perms import access_model, access_model_field

import operator
    
# prof included for people using http://www.djangosnippets.org/snippets/186/
AVAILABLE_OPTS =  ('search_fields','prof','inclusions','sort','search','count','order','start')

@json_response
def datagrid_list(request, app_name, model_name, access_model_callback=access_model, access_field_callback=access_model_field):
    """
    Renders a json representation of a model within an app.  Set to handle GET params passed
    by dojos ReadQueryStore for the dojango datagrid.  The following GET params are handled with
    specially:
      'search_fields','inclusions','sort','search','count','order','start'
      
    search_fields: list of fields for model to equal the search, each OR'd together.
    search: see search_fields
    sort: sets order_by
    count: sets limit
    start: sets offset
    inclusions: list of functions in the model that will be called and result added to JSON
     
    any other GET param will be added to the filter on the model to determine what gets returned.  ie
    a GET param of id__gt=5 will result in the equivalent of model.objects.all().filter( id__gt=5 )
    
    The access_model_callback is a function that gets passed the request, app_name, model_name, and
    an instance of the model which will only be added to the json response if returned True
    
    The access_field_callback gets passed the request, app_name, model_name, field_name,
    and the instance.  Return true to allow access of a given field_name to model 
    app_name.model_name given instance model.
    
    The default callbacks will allow access to any model in added to the DOJANGO_DATAGRID_ACCESS
    in settings.py and any function/field that is not "delete"
    """
    
    # get the model
    model = get_model(app_name,model_name)
    
    # start with a very broad query set
    target = model.objects.all()
    
    # modify query set based on the GET params, dont do the start/count splice
    # custom options passed from "query" param in datagrid
    for key in [ d for d in request.GET.keys() if not d in AVAILABLE_OPTS]:
        target = target.filter(**{str(key):request.GET[key]})
    num = target.count()

    # until after all clauses added
    if request.GET.has_key('search') and request.GET.has_key('search_fields'):
        ored = [models.Q(**{str(k).strip(): unicode(request.GET['search'])} ) for k in request.GET['search_fields'].split(",")]
        target = target.filter(reduce(operator.or_, ored))

    if request.GET.has_key('sort') and request.GET["sort"] not in request.GET["inclusions"] and request.GET["sort"][1:] not in request.GET["inclusions"]:
		# if the sort field is in inclusions, it must be a function call.. 
        target = target.order_by(request.GET['sort'])
    else:
		if request.GET.has_key('sort') and request.GET["sort"].startswith('-'):
			target = sorted(target, lambda x,y: cmp(getattr(x,request.GET["sort"][1:])(),getattr(y,request.GET["sort"][1:])()));
			target.reverse();
		elif request.GET.has_key('sort'):
			target =  sorted(target, lambda x,y: cmp(getattr(x,request.GET["sort"])(),getattr(y,request.GET["sort"])()));
    
    
    # get only the limit number of models with a given offset
    target=target[int(request.GET['start']):int(request.GET['start'])+int(request.GET['count'])]
    # create a list of dict objects out of models for json conversion
    complete = []
    for data in target:
        # TODO: complete rewrite to use dojangos already existing serializer (or the dojango ModelStore)
        if access_model_callback(app_name, model_name, request, data):   
            ret = {}
            for f in data._meta.fields:
                if access_field_callback(app_name, model_name, f.attname, request, data):
                    if isinstance(f, models.ImageField) or isinstance(f, models.FileField): # filefields can't be json serialized
                        ret[f.attname] = unicode(getattr(data, f.attname))
                    else:
                        ret[f.attname] = getattr(data, f.attname) #json_encode() this?
            fields = dir(data.__class__) + ret.keys()
            add_ons = [k for k in dir(data) if k not in fields and access_field_callback(app_name, model_name, k, request, data)]
            for k in add_ons:
                ret[k] = getattr(data, k)
            if request.GET.has_key('inclusions'):
                for k in request.GET['inclusions'].split(','):
                    if k == "": continue
                    if access_field_callback(app_name, model_name, k, request, data): 
                        try:
                            ret[k] = getattr(data,k)()
                        except:
                            try:
                                ret[k] = eval("data.%s"%".".join(k.split("__")))
                            except:
                                ret[k] = getattr(data,k)
            complete.append(ret)
        else:
            raise Exception, "You're not allowed to query the model '%s.%s' (add it to the array of the DOJANGO_DATAGRID_ACCESS setting)" % (model_name, app_name)
    return to_dojo_data(complete, identifier=model._meta.pk.name, num_rows=num)

###########
#  Tests  #
###########

def test(request):
    return render_to_response('dojango/test.html')

@json_response
def test_countries(request):
    countries = { 'identifier': 'name',
                  'label': 'name',
                  'items': [
                      { 'name':'Africa', 'type':'continent', 'population':'900 million', 'area': '30,221,532 sq km',
                         'timezone': '-1 UTC to +4 UTC',
                          'children':[{'_reference':'Egypt'}, {'_reference':'Kenya'}, {'_reference':'Sudan'}] },
                      { 'name':'Egypt', 'type':'country' },
                      { 'name':'Kenya', 'type':'country',
                          'children':[{'_reference':'Nairobi'}, {'_reference':'Mombasa'}] },
                      { 'name':'Nairobi', 'type':'city' },
                      { 'name':'Mombasa', 'type':'city' },
                      { 'name':'Sudan', 'type':'country',
                          'children':{'_reference':'Khartoum'} },
                      { 'name':'Khartoum', 'type':'city' },
                      { 'name':'Asia', 'type':'continent',
                          'children':[{'_reference':'China'}, {'_reference':'India'}, {'_reference':'Russia'}, {'_reference':'Mongolia'}] },
                      { 'name':'China', 'type':'country' },
                      { 'name':'India', 'type':'country' },
                      { 'name':'Russia', 'type':'country' },
                      { 'name':'Mongolia', 'type':'country' },
                      { 'name':'Australia', 'type':'continent', 'population':'21 million',
                          'children':{'_reference':'Commonwealth of Australia'}},
                      { 'name':'Commonwealth of Australia', 'type':'country', 'population':'21 million'},
                      { 'name':'Europe', 'type':'continent',
                          'children':[{'_reference':'Germany'}, {'_reference':'France'}, {'_reference':'Spain'}, {'_reference':'Italy'}] },
                      { 'name':'Germany', 'type':'country' },
                      { 'name':'Spain', 'type':'country' },
                      { 'name':'Italy', 'type':'country' },
                      { 'name':'North America', 'type':'continent',
                          'children':[{'_reference':'Mexico'}, {'_reference':'Canada'}, {'_reference':'United States of America'}] },
                      { 'name':'Mexico', 'type':'country',  'population':'108 million', 'area':'1,972,550 sq km',
                          'children':[{'_reference':'Mexico City'}, {'_reference':'Guadalajara'}] },
                      { 'name':'Mexico City', 'type':'city', 'population':'19 million', 'timezone':'-6 UTC'},
                      { 'name':'Guadalajara', 'type':'city', 'population':'4 million', 'timezone':'-6 UTC' },
                      { 'name':'Canada', 'type':'country',  'population':'33 million', 'area':'9,984,670 sq km',
                          'children':[{'_reference':'Ottawa'}, {'_reference':'Toronto'}] },
                      { 'name':'Ottawa', 'type':'city', 'population':'0.9 million', 'timezone':'-5 UTC'},
                      { 'name':'Toronto', 'type':'city', 'population':'2.5 million', 'timezone':'-5 UTC' },
                      { 'name':'United States of America', 'type':'country' },
                      { 'name':'South America', 'type':'continent',
                          'children':[{'_reference':'Brazil'}, {'_reference':'Argentina'}] },
                      { 'name':'Brazil', 'type':'country', 'population':'186 million' },
                      { 'name':'Argentina', 'type':'country', 'population':'40 million' },
                  ]
                  }

    return countries

@json_response
def test_states(request):
    states = [
        {'name':"Alabama", 'label':"<img width='97px' height='127px' src='images/Alabama.jpg'/>Alabama",'abbreviation':"AL"},
        {'name':"Alaska", 'label':"Alaska",'abbreviation':"AK"},
        {'name':"American Samoa", 'label':"American Samoa",'abbreviation':"AS"},
        {'name':"Arizona", 'label':"Arizona",'abbreviation':"AZ"},
        {'name':"Arkansas", 'label':"Arkansas",'abbreviation':"AR"},
        {'name':"Armed Forces Europe", 'label':"Armed Forces Europe",'abbreviation':"AE"},
        {'name':"Armed Forces Pacific", 'label':"Armed Forces Pacific",'abbreviation':"AP"},
        {'name':"Armed Forces the Americas", 'label':"Armed Forces the Americas",'abbreviation':"AA"},
        {'name':"California", 'label':"California",'abbreviation':"CA"},
        {'name':"Colorado", 'label':"Colorado",'abbreviation':"CO"},
        {'name':"Connecticut", 'label':"Connecticut",'abbreviation':"CT"},
        {'name':"Delaware", 'label':"Delaware",'abbreviation':"DE"},
        {'name':"District of Columbia", 'label':"District of Columbia",'abbreviation':"DC"},
        {'name':"Federated States of Micronesia", 'label':"Federated States of Micronesia",'abbreviation':"FM"},
        {'name':"Florida", 'label':"Florida",'abbreviation':"FL"},
        {'name':"Georgia", 'label':"Georgia",'abbreviation':"GA"},
        {'name':"Guam", 'label':"Guam",'abbreviation':"GU"},
        {'name':"Hawaii", 'label':"Hawaii",'abbreviation':"HI"},
        {'name':"Idaho", 'label':"Idaho",'abbreviation':"ID"},
        {'name':"Illinois", 'label':"Illinois",'abbreviation':"IL"},
        {'name':"Indiana", 'label':"Indiana",'abbreviation':"IN"},
        {'name':"Iowa", 'label':"Iowa",'abbreviation':"IA"},
        {'name':"Kansas", 'label':"Kansas",'abbreviation':"KS"},
        {'name':"Kentucky", 'label':"Kentucky",'abbreviation':"KY"},
        {'name':"Louisiana", 'label':"Louisiana",'abbreviation':"LA"},
        {'name':"Maine", 'label':"Maine",'abbreviation':"ME"},
        {'name':"Marshall Islands", 'label':"Marshall Islands",'abbreviation':"MH"},
        {'name':"Maryland", 'label':"Maryland",'abbreviation':"MD"},
        {'name':"Massachusetts", 'label':"Massachusetts",'abbreviation':"MA"},
        {'name':"Michigan", 'label':"Michigan",'abbreviation':"MI"},
        {'name':"Minnesota", 'label':"Minnesota",'abbreviation':"MN"},
        {'name':"Mississippi", 'label':"Mississippi",'abbreviation':"MS"},
        {'name':"Missouri", 'label':"Missouri",'abbreviation':"MO"},
        {'name':"Montana", 'label':"Montana",'abbreviation':"MT"},
        {'name':"Nebraska", 'label':"Nebraska",'abbreviation':"NE"},
        {'name':"Nevada", 'label':"Nevada",'abbreviation':"NV"},
        {'name':"New Hampshire", 'label':"New Hampshire",'abbreviation':"NH"},
        {'name':"New Jersey", 'label':"New Jersey",'abbreviation':"NJ"},
        {'name':"New Mexico", 'label':"New Mexico",'abbreviation':"NM"},
        {'name':"New York", 'label':"New York",'abbreviation':"NY"},
        {'name':"North Carolina", 'label':"North Carolina",'abbreviation':"NC"},
        {'name':"North Dakota", 'label':"North Dakota",'abbreviation':"ND"},
        {'name':"Northern Mariana Islands", 'label':"Northern Mariana Islands",'abbreviation':"MP"},
        {'name':"Ohio", 'label':"Ohio",'abbreviation':"OH"},
        {'name':"Oklahoma", 'label':"Oklahoma",'abbreviation':"OK"},
        {'name':"Oregon", 'label':"Oregon",'abbreviation':"OR"},
        {'name':"Pennsylvania", 'label':"Pennsylvania",'abbreviation':"PA"},
        {'name':"Puerto Rico", 'label':"Puerto Rico",'abbreviation':"PR"},
        {'name':"Rhode Island", 'label':"Rhode Island",'abbreviation':"RI"},
        {'name':"South Carolina", 'label':"South Carolina",'abbreviation':"SC"},
        {'name':"South Dakota", 'label':"South Dakota",'abbreviation':"SD"},
        {'name':"Tennessee", 'label':"Tennessee",'abbreviation':"TN"},
        {'name':"Texas", 'label':"Texas",'abbreviation':"TX"},
        {'name':"Utah", 'label':"Utah",'abbreviation':"UT"},
        {'name':"Vermont", 'label':"Vermont",'abbreviation':"VT"},
        {'name': "Virgin Islands, U.S.",'label':"Virgin Islands, U.S.",'abbreviation':"VI"},
        {'name':"Virginia", 'label':"Virginia",'abbreviation':"VA"},
        {'name':"Washington", 'label':"Washington",'abbreviation':"WA"},
        {'name':"West Virginia", 'label':"West Virginia",'abbreviation':"WV"},
        {'name':"Wisconsin", 'label':"Wisconsin",'abbreviation':"WI"},
        {'name':"Wyoming", 'label':"Wyoming",'abbreviation':"WY"}
    ]
    # Implement a very simple search!
    search_string, start, end = get_combobox_data(request)
    ret = []
    for state in states:
        if state['name'].lower().startswith(search_string.lower()):
            ret.append(state)
    ret = ret[start:end]
    
    # Convert the data into dojo.date-store compatible format.
    return to_dojo_data(ret, identifier='abbreviation')

########NEW FILE########
