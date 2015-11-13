__FILENAME__ = linking
#!/usr/bin/env python
# Encoding: iso-8859-1
# -----------------------------------------------------------------------------
# Project           :   Sink
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   BSD License (revised)
# -----------------------------------------------------------------------------
# Creation date     :   23-Jul-2007
# Last mod.         :   29-Sep-2009
# -----------------------------------------------------------------------------

# TODO: Make it standalone (so it can be intergrated into Mercurial Contrib)

import os, sys, hashlib, stat, getopt, shutil

#------------------------------------------------------------------------------
#
#  Exceptions
#
#------------------------------------------------------------------------------

class LinksCollectionError(Exception):
	"""Raised when an error happens in the configuration process."""

class RuntimeError(Exception):
	"""Raised when an error happens in the engine."""

CFG_BAD_ROOT = "Directory or symlink expected for collection root"
CFG_NOT_A_CHILD = "Link destination must be a subpath of %s"
ERR_NOT_FOUND = "Path does not exist: %s"
ERR_SOURCE_NOT_FOUND = "Link source for '%s' not found: %s"
ERR_LINK_IS_NEWER = "Link is newer, update has to be forced: %s"
ERR_ORIGIN_IS_NEWER = "Origin is newer, update has to be forced: %s"

#------------------------------------------------------------------------------
#
#  Basic path operations
#
#------------------------------------------------------------------------------

def expand_path( path ):
	"""Completely expands the given path (vars, user and make it absolute)."""
	assert type(path) in (str, unicode), "String expected:%s" % (path)
	return os.path.expandvars(os.path.expanduser(path))

def path_is_child( path, parent ):
	"""Returns 'True' if the given 'path' is a child of the given 'parent'
	path."""
	e_path   = expand_path(path)
	e_parent = expand_path(parent)
	return e_path.startswith(e_parent)

def make_relative( path, relative_to="." ):
	"""Expresses the given 'path' relatively to the 'relative_to' path."""
	path, relative_to = map(expand_path, (path, relative_to))
	if path.startswith(relative_to):
		path = path[len(relative_to):]
		if path and path[0] == "/": path = path[1:]
		return path
	else:
		return path

def has_hg( path ):
	"""Returns the path of the (possible) Mercurial repository contained at the
	given location, or returns None if it was not found."""
	if not path: return None
	path = os.path.abspath(path)
	parent = os.path.dirname(path)
	hg_path = os.path.join(path, ".hg")
	if os.path.exists(hg_path):
		return hg_path
	elif parent != path:
		return has_hg(parent)
	else:
		return None

#------------------------------------------------------------------------------
#
#  LinksCollection Class
#
#------------------------------------------------------------------------------

DB_FILE     = ".sinklinks"
DB_FILE_HG  = os.path.join(".hg",  "sinklinks")
DB_FILE_GIT = os.path.join(".git", "sinklinks")

class LinksCollection:

	@staticmethod
	def lookup( path="." ):
		"""Looks for a file '.versions-links' or '.hg/version-links' in the
		current path or in a parent path."""
		if not path: return None
		path = os.path.abspath(path)
		parent = os.path.dirname(path)
		fs_vlinks  = os.path.join(path, DB_FILE)
		hg_vlinks  = os.path.join(path, DB_FILE_HG)
		git_vlinks = os.path.join(path, DB_FILE_GIT)
		if os.path.exists(fs_vlinks):
			return LinksCollection(path, DB_FILE)
		elif os.path.exists(hg_vlinks):
			return LinksCollection(path, DB_FILE_HG)
		elif os.path.exists(hg_vlinks):
			return LinksCollection(path, DB_FILE_GIT)
		elif parent != path:
			return LinksCollection.lookup(parent)
		else:
			return None

	def __init__( self, root, dbfile=DB_FILE ):
		"""Creates a new link collection object, using the given root."""
		self.links = {}
		root  = expand_path(root)
		if not os.path.exists(root):
			raise LinksCollectionError(CFG_BAD_ROOT)
		self.root   = root
		self.dbfile = dbfile
		if self.exists():
			self.load()

	def getLinks( self ):
		"""Returns a list of '(source, dest)' where source and dest are absolute
		_expanded paths_ representing the link source and destination."""
		res = []
		for d, s in self.links.items():
			res.append(map(expand_path,(s,os.path.join(self.root,d))))
		return res

	def getSource( self, destination ):
		"""Returns the source for the given destination, in its _unexpanded_
		form."""
		n_destination = self._normalizeDestination(destination)
		return self.links.get(n_destination)
	
	def expand( self, path ):
		"""Expands the given path, which will be interepreted as relative to this links collection root"""
		path = expand_path(path)
		if os.path.abspath(path) != path:
			return os.path.abspath(os.path.join(self.root, path))
		else:
			return path

	def _normalizeDestination( self, destination ):
		"""Normalizes the destination path, making it relative to the
		collection root, and discarding the leading '/'"""
		e_destination = expand_path(destination)
		assert e_destination.startswith(self.root)
		n_destination = e_destination[len(self.root):]
		assert n_destination[0] == "/"
		n_destination = n_destination[1:]
		return n_destination

	def registerLink( self, source, destination ):
		"""Registers a link from the given source path to the given destination.
		*Source* is stored as-is (meaning that variables *won't be expanded*), and
		*destination will be expanded* and be expressed relatively to the
		collection root.
		
		This implies that destination must be contained in the collection
		root directory."""
		# TODO: Should we check the source ?
		e_destination = expand_path(destination)
		if not path_is_child(e_destination, self.root):
			raise LinksCollectionError(CFG_NOT_A_CHILD % (self.root))
		n_destination = self._normalizeDestination(e_destination)
		self.links[n_destination] = source
		return e_destination, source

	def removeLink( self, link, delete=False ):
		"""Removes the link from this link collection. The file is only delete
		if the delete option is True."""
		assert self.getSource(link)
		e_link = expand_path(link)
		n_link = self._normalizeDestination(e_link)
		if delete and os.path.exists(e_link):
			os.unlink(e_link)
		del self.links[n_link]

	def save( self ):
		"""Saves the link collection to the 'dbpath()' file."""
		f = file(self.dbpath(), 'w')
		f.write(str(self))
		f.close()

	def load( self ):
		"""Loads the given collection."""
		f = file(self.dbpath(), 'r')
		c = f.readlines()
		f.close()
		links_count = 0
		for line in c: 
			line = line[:-1]
			line = line.strip()
			if not line: continue
			if line.startswith("#"): continue
			elements = line.split("\t")
			command, args = elements[0], elements[1:]
			command = command.strip()[:-1]
			if   command == "dbfile":
				# TODO: Check that the dbfile has the same value
				pass
			elif command == "root":
				# TODO: Check that root has the same value
				pass
			elif command == "links":
				links_count = int(args[0])
			elif command == "link":
				self.links[args[0]] = args[1]
		assert len(self.links.items()) == links_count

	def dbpath( self ):
		"""Returns the absolute patht ot the DB file."""
		return expand_path(os.path.join(self.root, self.dbfile))

	def exists( self ):
		"""Tells if the collection exists on the filesystem."""
		return os.path.exists(self.dbpath())

	def __str__( self ):
		"""Serializes the collection to a string"""
		res = []
		res.append("# Sink Link Database")
		res.append("root:\t%s" % (self.root))
		res.append("dbfile:\t%s" % (self.dbfile))
		res.append("links:\t%s" % (len(self.links)))
		for d,s in self.links.items():
			res.append("link:\t%s\t%s" % (d,s))
		res.append("# EOF")
		return "\n".join(res)

#------------------------------------------------------------------------------
#
#  Engine Class
#
#------------------------------------------------------------------------------

USAGE = """\
sink [-l|link] COMMAND [ARGUMENT ARGUMENT...]

Creates a platform-independen links database between files. This can be used
as a replacement to 'ln' when symlinks are not appropriate.

Commands:

   init   [PATH]                        Creates a new link database
   add    [OPTIONS] SOURCE DEST         Creates a link between two file
   remove LINK [LINK]                   Removes the given links
   status [PATH|LINK]                   Show the status of links
   pull   [OPTIONS] [PATH|LINK]         Pulls changes from sources
   push   [OPTIONS] [PATH|LINK]         Pushes changes to source

sink -l init [PATH]

  Initialises the link database for the current folder, or the folder at the
  given PATH. If PATH is omitted, it will use the current folder, or will look
  for a Mercurial (.hg) or Git (.git) repository in the parent directories, and
  will use it to store the links database as a 'sinklinks' file.

  There are no options for this command.

sink -l add [OPTIONS] SOURCE* DESTINATION

  Creates a link from the the SOURCE to the DESTINATION. The DESTINATION must
  be contained in a directory where the 'link init' command was run.

  Options:

    -w, --writable    Link will be made writable (so that you can update them)

sink -l remove LINK [LINK..]

    Removes one or more link from the link database. The links destinations
    won't be removed from the filesystem unlesse you specify '--delete'.

    Options:

      -d, --delete      Deletes the link destination (your local file)

sink -l status [PATH|LINK]...

   Returns the status of the given links. If no link is given, the status of
   all links will be returned. When no argument is given, the current
   directory (or one of its parent) must contain a link database, otherwise
   you should give a PATH containing a link databae.

sink -l pull [OPTIONS] [PATH|LINK]...

   Updates the given local links in the current or given PATH, or updates only the
   given list of LINKs (they must belong to the same link DB, accessible from
   the current path).

   If the link is newer than the origin and has modifications, then the update
   will not happen unless it is --force'd.

   You can also merge back the changes by using '--merge'. This will start
   your favorite $MERGETOOL.

   Options:

     -f, --force       Forces the update, ignoring local modifications
     -d, --difftool    Overrides your $MERGETOOL

sink -l push [OPTIONS] [PATH|LINK]...

    Same as pull, but updates the origin according to your local version.

   Options:

     -f, --force       Forces the update, ignoring local modifications
     -d, --difftool    Overrides your $MERGETOOL
"""

class Engine:
	"""Implements operations that can be done on a link collection. Operations
	include giving status, resolving a link, and updating a link."""

	ST_SAME      = "="
	ST_DIFFERENT = "+"
	ST_EMPTY     = "_"
	ST_NOT_THERE = "!"
	ST_NEWER     = ">"
	ST_OLDER     = "<"

	def __init__( self, logger, config=None ):
		self.logger        = logger
		self.linksReadOnly = True
		if config: self.setup(config)

	def setup( self, config ):
		"""Sets up the engine using the given configuration object."""
		# TODO: Setup difftool/mergetool

	def run( self, arguments ):
		"""Runs the command using the given list of arguments (a list of
		strings)."""
		logger = self.logger
		if not arguments:
			return self.logger.message(USAGE)
		command = arguments[0]
		rest    = arguments[1:]
		# -- INIT command
		if command == "init":
			path = "."
			if len(rest) > 1:
				return self.logger.error("Too many arguments")
			elif len(rest) == 1:
				path = rest[0]
			self.init(path)
			return 1
		# -- ADD command
		elif command == "add":
			try:
				optlist, args = getopt.getopt( rest, "w", ["writable"])
			except Exception, e:
				return self.logger.error(e)
			self.linksReadOnly = True
			for opt, arg in optlist:
				if opt in ('-w', '--writable'):
					self.linksReadOnly = False
					raise Exception("--writable not implemented yet")
			if len(args) < 2:
				return self.logger.error("Adding a link requires a SOURCE and DESTINATION")
			collection = LinksCollection.lookup(".") or LinksCollection(".")
			dest       = args[-1]
			if len(args) == 2:
				self.add(collection, args[0], args[1])
			else:
				if not os.path.isdir(dest):
					return self.logger.error("DESTINATION must be a directory when given multiple files")
				for source in args[:-1]:
					dest_path = os.path.join(dest, os.path.basename(source))
					self.add(collection, source, dest_path)
		# -- STATUS command
		elif command == "status":
			collection = LinksCollection.lookup(".") or LinksCollection(".")
			self.status(collection)
		# -- PUSH or PULL command
		elif command == "push" or command == "pull":
			try:
				optlist, args = getopt.getopt( rest, "fmd", ["force", "merge", "difftool"])
			except Exception, e:
				return self.logger.error(e)
			self.forceUpdate = False
			for opt, arg in optlist:
				if opt in ('-f', '--force'):
					self.forceUpdate = True
				if opt in ('-d', '--difftool'):
					raise Exception("--difftool option not implemented yet")
				if opt in ('-m', '--merge'):
					raise Exception("--merge option not implemented yet")
			collection = LinksCollection.lookup(".") or LinksCollection(".")
			self.update(command, collection, *args)
		# -- REMOVE command
		elif command == "remove":
			try:
				optlist, args = getopt.getopt( rest, "d", ["delete"])
			except Exception, e:
				return self.logger.error(e)
			delete = False
			for opt, arg in optlist:
				if opt in ('-d', '--delete'):
					delete = True
			if not args:
				return self.logger.error("At least one link is expected")
			collection = LinksCollection.lookup(".") or LinksCollection(".")
			self.remove(collection, args, delete)
		else:
			return self.logger.error("Uknown command: %s" % (command))

	def init( self, path="." ):
		"""Initializes a link collection (link db) at the given location."""
		path = expand_path(path)
		hg_path = has_hg(path)
		if not os.path.exists(path) and (hg_path and not os.path.exists(hg_path)):
			return self.logger.error("Given path does not exist: %s" % (path))
		if hg_path:
			collection = LinksCollection(os.path.dirname(hg_path), DB_FILE_HG)
		else:
			collection = LinksCollection(path, DB_FILE)
		if collection.exists():
			return self.logger.error("Link database already exists: ", make_relative(collection.dbpath(), "."))
		collection.save()
		self.logger.info("Link database created: ", make_relative(collection.dbpath(), "."))
		return collection

	def add( self, collection, source, destination ):
		"""Adds a link from the source to the destination"""
		if os.path.isdir(destination):
			destination = os.path.join(destination, os.path.basename(source))
		self.logger.message("Adding a link from %s to %s" % (source, destination))
		if not collection.exists():
			return self.logger.error("Link database was not initialized: %s" % (collection.root))
		exists = collection.getSource(destination)
		destination, source = collection.registerLink(source, destination)
		# TODO: Remove the WRITABLE mode from the destinatino
		if not os.path.exists(destination):
			self.logger.info("File does not exist, creating it")
			dirname = os.path.dirname(destination)
			if not os.path.exists(dirname):
				self.logger.info("Parent directory does not exist, creating it: %s" %( make_relative(dirname, ".")))
				os.makedirs(dirname)
			f = file(destination, "w")
			f.write(self._readLocal(source))
			f.close()
		if exists == source:
			self.logger.info("Link source is the same as the existing one: %s" % (make_relative(exists, ".")))
		elif exists:
			self.logger.warning("Previous link source was replaced: %s" % (make_relative(exists, ".")))
		collection.save()

	def status( self, collection ):
		links    = []
		link_max = 0
		src_max  = 0
		for s, l in collection.getLinks():
			l = make_relative(l, ".")
			link_max = max(len(l), link_max) 
			src_max  = max(len(s), src_max)
			links.append([s, l])
		links.sort()
		template = "[%s] %-" + str(link_max) + "s  %-s  %" + str(src_max) + "s"
		for s, l in links:
			try:
				content, date = self.linkStatus(collection, l)
				if content == self.ST_EMPTY: date = self.ST_OLDER
				self.logger.message(template % (content, l,date,s))
			except Exception, e:
				self.logger.error(e)

	def update( self, command, collection, *links ):
		"""Updates the given links, or all if no link is specified."""
		assert command in ("push", "pull")
		col_links = collection.getLinks()
		dst_links = map(lambda x:x[1], col_links)
		if not col_links:
			return self.logger.warning("No link registered in the collection")
		links = map(expand_path, links)
		# We make sure that the link are registered
		for link in links:
			if not link in dst_links:
				return self.logger.error("Link is not registered: %s" % (
					make_relative(link, ".")
				))
		# Then we update the links
		for s, l in col_links:
			content, date = self.linkStatus(collection, l)
			# We ignore the links that are not in the 'links' list, if this list
			# is not empty
			if links and not (l in links):
				continue
			if command == "pull":
				if content == self.ST_NOT_THERE or content == self.ST_EMPTY \
				or content == self.ST_DIFFERENT and date != self.ST_NEWER:
					self.logger.message("Updating from origin ", make_relative(l,"."))
					self.pullLink(collection, l, self.forceUpdate)
				elif content == self.ST_DIFFERENT:
					# FIXME: Should do a merge
					self.logger.warning("Skipping update of", make_relative(l,"."), "(file has local modifications)")
				else:
					self.logger.message("Link is already up to date: ", make_relative(l,"."))
			else:
				if   content == self.ST_NOT_THERE or content == self.ST_EMPTY:
					self.logger.message("Link destination destination was removed or is empty, keeping origin")
				elif content == self.ST_DIFFERENT and date == self.ST_NEWER:
					# FIXME: Should do a merge
					self.logger.message("Updating origin from", make_relative(l,"."))
					self.pushLink(collection, l)
				elif content == self.ST_DIFFERENT and date != self.ST_NEWER:
					self.logger.warning("Skipping update", make_relative(l,"."), "(origin is newer)")
				else:
					self.logger.message("Link is already up to date: ", make_relative(l,"."))

	def remove( self, collection, links, delete=False ):
		"""Remove the given list of links from the collection."""
		for link in links:
			if not collection.getSource(link):
				return self.logger.error("Link does not exist: %s" % (make_relative(link)))
		for link in links:
			self.logger.message("Removing link: %s" % (make_relative(link)))
			collection.removeLink(expand_path(link), delete)
		collection.save()

	def linkStatus( self, collection, link ):
		"""Returns a couple '(CONTENT_STATUS, FILE_STATUS)' where
		'CONTENT_STATUS' is any of 'ST_SAME, ST_DIFFERENT', 'ST_EMPTY',
		'ST_NOT_THERE' and 'FILE_STATUS' is any of 'ST_SAME, ST_NEWER,
		ST_OLDER'."""
		source = collection.getSource(link)
		source_path = collection.expand(source)
		if not source_path or not os.path.exists(source_path):
			raise RuntimeError(ERR_SOURCE_NOT_FOUND % (link, source))
		source_path, s_content = self._read(source_path)
		if not os.path.exists(link):
			return (self.ST_NOT_THERE, self.ST_NEWER)
		dest,   d_content = self._read(link)
		s_sig = self._sha(s_content)
		d_sig = self._sha(d_content)
		s_tme = self._mtime(source_path)
		d_tme = self._mtime(dest)
		res_0 = self.ST_DIFFERENT
		if s_sig == d_sig: res_0 = self.ST_SAME
		if not d_content: res_0 = self.ST_EMPTY
		res_1 = self.ST_SAME
		if s_tme < d_tme: res_1 = self.ST_NEWER
		if s_tme > d_tme: res_1 = self.ST_OLDER
		return (res_0, res_1)

	def pullLink( self, collection, link, force=False ):
		"""Updates the given link to the content of the link source"""
		c, d = self.linkStatus(collection, link)
		#if not force and (not (c in (self.ST_EMPTY, self.ST_NOT_THERE)) and d != self.ST_SAME):
		if not force and (d == self.ST_NEWER and not (c==self.ST_EMPTY or c==self.ST_NOT_THERE)):
			raise RuntimeError(ERR_LINK_IS_NEWER % (link))
		e_link = expand_path(link)
		path, content = self.resolveLink(collection, e_link)
		shutil.copyfile(path,e_link)
		shutil.copystat(path,e_link)

	def pushLink( self, collection, link, force=False ):
		"""Updates the given link to the content of the link source"""
		c, d = self.linkStatus(collection, link)
		print c, d
		if not force and (c in (self.ST_EMPTY, self.ST_NOT_THERE) or d == self.ST_OLDER):
			raise RuntimeError(ERR_ORIGIN_IS_NEWER % (link))
		e_link = expand_path(link)
		path, content = self.resolveLink(collection, e_link)
		shutil.copyfile(e_link, path)
		shutil.copystat(e_link, path)

	def resolveLink( self, collection, link ):
		"""Returns ta couple ('path', 'content') corresponding to the resolution
		of the given link.
		
		The return value is the same as the '_read' method."""
		source = collection.getSource(link)
		return self._read(collection.expand(source))

	def _read( self, path, getContent=True ):
		"""Resolves the given path and returns a couple '(path, content)' when
		'getContent=True', or '(path, callback)' where callback will return the
		content of the file when invoked."""
		path = expand_path(path)
		if not os.path.exists(path):
			raise RuntimeError(ERR_NOT_FOUND % (path))
		if getContent:
			return (path, self._readLocal(path))
		else:
			return (path, lambda: self._readLocal(path))

	def _readLocal( self, path ):
		"""Reads a file from the local file system."""
		f = file(expand_path(path), 'r')
		c = f.read()
		f.close()
		return c

	def _sha( self, content ):
		return hashlib.sha1(content).hexdigest()

	def _mtime( self, path ):
		"""Returns the modification time of the file at the give path."""
		return os.stat(path)[stat.ST_MTIME]

	def _size( self, path ):
		"""Returns the size of the file at the give path."""
		return os.stat(path)[stat.ST_SIZE]

# EOF - vim: ts=4 sw=4 noet

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# -----------------------------------------------------------------------------
# Project           :   Sink                 <http://github.com/sebastien/sink>
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   BSD License (revised)
# -----------------------------------------------------------------------------
# Creation date     :   03-Dec-2004
# Last mod.         :   29-Sep-2009
# -----------------------------------------------------------------------------

import os, sys, shutil, getopt, string, ConfigParser
from os.path import basename, dirname, exists

# We try to import the sink module. If we have trouble, we simply insert the
# path into the Python path
try:
	from sink import tracking, linking, snapshot
except:
	sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
	from sink import tracking, linking, snapshot

__version__ = "1.0.0"

#------------------------------------------------------------------------------
#
#  Logger
#
#------------------------------------------------------------------------------

class Logger:
	"""A logger instance allows to properly output information to the user
	through the terminal."""

	@staticmethod
	def default():
		"""Returs the default logger instance."""
		if not hasattr(Logger, "DEFAULT"):
			Logger.DEFAULT = Logger()
		return Logger.DEFAULT

	def __init__( self ):
		self._out = sys.stdout
		self._err = sys.stderr

	def error( self, *message ):
		self._write(self._err,  "[ERROR]", *message)
		return -1

	def warning( self, *message ):
		self._write(self._out, "[!]", *message)
		return 0

	def message( self, *message ):
		self._write(self._out, *message)
		return 0

	def info( self, *message ):
		self._write(self._out,  *message)
		return 0

	def _write( self, stream, *a ):
		stream.write(" ".join(map(str,a)) + "\n")
		stream.flush()

#------------------------------------------------------------------------------
#
#  Main
#
#------------------------------------------------------------------------------

USAGE = """\
sink (%s)

Sink is the swiss army-knife for many common directory comparison and 
synchronization.

Usage:    sink [MODE] [OPTIONS]

Modes:

  (diff/-d/--diff)    Lists the changes between two or more directories
  (link/-l/--link)    Manages a links between files
  (snap/-s/--snap)    Takes snapshot of a directory
  (help/-h/--help)    Gives detailed help about a specific operation

Options:

  See 'sink --help changes' and 'sink --help link' for more information
  about each mode options.

Examples:

   sink DIR1 DIR2 DIR3           Compares the contents of DIR1, DIR2 and DIR3
   sink -n1 DIR1 DIR2            Shows difference between version of file 1
                                 in the listing given by 'sink DIR1 DIR2'
   sink --only '*.py' D1 D2      Comparens the '*.py' files in D1 and D2

""" % (__version__)

DEFAULTS = {
	"sink.mode"       : tracking.CONTENT_MODE,
	"sink.diff"       : "diff -u",
	"sink.whitespace" : True,
	"filters.accepts" : [],
	"filters.rejects" : []
}

OPERATIONS = {
	"-d":tracking.Engine,
	"-l":linking.Engine,
	"-s":snapshot.Engine,
	"--diff":tracking.Engine,
	"--link":linking.Engine,
	"--snap":snapshot.Engine,
	"diff":tracking.Engine,
	"link":linking.Engine,
	"snap":snapshot.Engine,
	"":tracking.Engine
}

def run( arguments, runningPath=".", logger=None ):
	"""Runs Sink using the given list of arguments, given either as a
	string or as a list."""

	# Ensures that the running path is actually a path (it may be simply the
	# full path to the executable )
	runningPath = os.path.abspath(runningPath)

	# If arguments are given as a string, split them
	if type(arguments) in (type(""), type(u"")):
		arguments = arguments.split(" ")

	# And the logger
	if logger==None:
		logger = Logger.default()

	# TODO: Add a better command/engine integration, where engines have a change
	# to set defaults, and parse config

	# Reads the configuration
	config = DEFAULTS.copy()
	config_path = os.path.expanduser("~/.sinkrc")
	if os.path.isfile(config_path):
		parser = ConfigParser.ConfigParser()
		parser.read(config_path)
		for section in parser.sections():
			for option in parser.options(section):
				key = section.lower() + "." + option.lower()
				val = parser.get(section, option).strip()
				if key == "sink.mode":
					if val in ("content", "contents"):
						config[key] = CONTENT_MODE
					elif val in ("time", "date"):
						config[key] = TIME_MODE
					else:
						print "Expected 'content' or 'time': ", val
				elif key == "sink.whitespace":
					if val == "ignore":
						config[key] = False
					else:
						config[key] = True
				elif key == "filters.accepts":
					config["filters.accepts"].extend(map(string.strip, val.split(",")))
				elif key in ("filters.rejects", "filters.reject", "filters.ignore", "filters.ignores"):
					config["filters.rejects"].extend(map(string.strip, val.split(",")))
				elif key == "sink.diff":
					config[key] = val.strip()
				else:
					print "Invalid configuration option:", key

	# If there is no arguments
	args = arguments
	if not args or args[0] in ('-h', '--help'):
		if len(args) == 2:
			if   args[1] == "diff":
				print tracking.USAGE
			elif args[1] == "link":
				print linking.USAGE
			elif args[1] == "snap":
				print snapshot.USAGE
			else:
				print USAGE
			return
		else:
			print USAGE
			return
	elif args[0] == '--version':
		print __version__
		return
	elif args[0] in OPERATIONS.keys():
		engine = OPERATIONS[args[0]](logger, config)
		return engine.run(args[1:])
		#try:
		#	return engine.run(args[1:])
		#except Exception, e:
		#	return logger.error(str(e))
	else:
		engine = OPERATIONS[""](logger, config)
		return engine.run(args)
		#try:
		#	return engine.run(args)
		#except Exception, e:
		#	return logger.error(str(e))

if __name__ == "__main__" :
	#import profile
	if len( sys.argv ) > 1:
		#profile.run("run(sys.argv[1:])")
		run(sys.argv[1:])
	else:
		run([])

# EOF - vim: sw=4 ts=4 tw=80 noet

########NEW FILE########
__FILENAME__ = snapshot
#!/usr/bin/env python
# Encoding: iso-8859-1
# -----------------------------------------------------------------------------
# Project           :   Sink
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# License           :   BSD License (revised)
# -----------------------------------------------------------------------------
# Creation date     :   29-Sep-2009
# Last mod.         :   30-Sep-2009
# -----------------------------------------------------------------------------

import os, simplejson
from sink import tracking

#------------------------------------------------------------------------------
#
#  File system node
#
#------------------------------------------------------------------------------

#TODO: Describe -d option
USAGE = """\
sink [-s|snap] [OPTIONS] DIRECTORY|FILE

Takes a snapshot of the given DIRECTORY and outputs it to the stdout. The
output format is JSON. If FILE is given instead, then displays the content
of the snapshot.

Options:

  -c, --content (dflt)   Uses content analysis to detect changes
  -t, --time             Uses timestamp to detect changes
  --ignore-spaces        Ignores the spaces when analyzing the content
  --ignore   GLOBS       Ignores the files that match the glob
  --only     GLOBS       Only accepts the file that match glob
  
Examples:

  Taking a snapshot of the state of /etc

  $ sink -s /etc > etc-`date +'%Y%m%d`.json

  Listing the content of a snapshot

  $ sink -s etc-20090930.json

  Comparing two snapshots

  $ sink -c etc-20090930.json etc-20091001.json

""" 

class Engine:
	"""Implements operations used by the Sink main command-line interface."""

	def __init__( self, logger, config=None ):
		self.logger        = logger
		if config: self.setup(config)

	def setup( self, config ):
		"""Sets up the engine using the given configuration object."""

	def run( self, arguments ):
		"""Runs the command using the given list of arguments (a list of
		strings)."""
		logger   = self.logger
		accepts  = []
		rejects  = []
		if not arguments:
			print self.usage()
			return -1
		#arguments = arguments[0], arguments[1:]
		args = arguments
		# We ensure that there are enough arguments
		if len(args) != 1:
			print args
			logger.error("Bad number of arguments\n" + USAGE)
			return -1
		root_path = args[0]
		# Ensures that the directory exists
		if os.path.isdir(root_path):
			# We take a state snapshot of the given directory
			root_state = tracking.State(root_path, accepts=accepts, rejects=rejects)
			root_state.populate( lambda x: True )
			print simplejson.dumps(root_state.exportToDict())
		else:
			f = file(root_path, 'r')
			d = simplejson.loads(f.read())
			print tracking.State.FromDict(d)
		return 0

	def usage( self ):
		return USAGE

# EOF - vim: sw=4 ts=4 tw=80 noet

########NEW FILE########
__FILENAME__ = tracking
#!/usr/bin/env python
# Encoding: iso-8859-1
# -----------------------------------------------------------------------------
# Project           :   Sink
# -----------------------------------------------------------------------------
# Author            :   Sebastien Pierre                 <sebastien@type-z.org>
# -----------------------------------------------------------------------------
# License           :   BSD License (revised)
# -----------------------------------------------------------------------------
# Creation date     :   09-Dec-2003
# Last mod.         :   30-Sep-2009
# -----------------------------------------------------------------------------
# Notes             :   NodeStates SHOULD not be created directly, because they
#                       MUST be cached (signature and location) in their
#                       containing state to be processable by the change
#                       tracker.
# -----------------------------------------------------------------------------

import os, hashlib, stat, time, fnmatch, getopt, simplejson

# Error messages

BAD_DOCUMENT_ELEMENT = "Bad document element"
NO_LOCATION = "No `location' attribute."
UNKNOWN_ELEMENT = "Unknown element %s"

#------------------------------------------------------------------------------
#
#  File system node
#
#------------------------------------------------------------------------------

FILE_SYSTEM_ATTRIBUTES = (
	"Size", "Creation", "Modification", "Owner", "Group", "Permissions",
)

class NodeState:
	"""The abstract class for representing the state of filesystem files
	and directories."""

	ADDED    = "+"
	REMOVED  = "-"
	MODIFIED = "m"
	COUNTER  = 0
	
	@staticmethod
	def FromDict( state, data ):
		assert state
		location = data["attributes"].get("location")
		if   data["type"] == FileNodeState.__name__:
			return FileNodeState(state, location, data=data)
		elif data["type"] == DirectoryNodeState.__name__:
			return DirectoryNodeState(state, location, data=data)
		else:
			assert None, "Unsupported type: %s" % (data["type"])

	def __init__( self, state, location, usesSignature=True, accepts=(),
	rejects=(), data=None ):
		"""Creates a file system node with the given location. The location
		is relative to the state root. The usesSignature parameter allows to
		specify wether the node should use a signature or not. Large file nodes may take
		too long to compute their signature, in which case this attributes
		comes in handy.

		The `update' method should be called to initilize the signature and
		attributes attributes from the local filesystem, but this implies that the
		nodes exists on the file system. Otherwise the `_attributes' and `_contentSignature'
		attributes can be set by hand."""
		self._uid    = "N%s" % (NodeState.COUNTER)
		self._parent = None
		self._state  = None
		self._cached = False
		self._accepts = accepts
		self._rejects = rejects
		self._attributes = {}
		self._tags = {}
		self._contentSignature = None
		self._attributesSignature = None
		self._usesSignature = usesSignature
		self._belongsToState( state )
		NodeState.COUNTER += 1
		if data: self.importFromDict(data)
		self.location( location )
		assert type(self._accepts) in (tuple, list)
		assert type(self._rejects) in (tuple, list)
		state.onNodeCreated(self)

	def exportToDict( self ):
		result = {
			"parent":self._parent and self._parent.location(),
			"type": self.__class__.__name__,
			"uid": self._uid,
			"accepts":self._accepts,
			"rejects":self._rejects,
			"attributes":self._attributes,
			"tags":self._tags,
			"contentSignature":self._contentSignature,
			"attributesSignature":self._usesSignature,
		}
		return result

	def importFromDict( self, data ):
		self._accepts    = data["accepts"]
		self._rejects    = data["rejects"]
		self._attributes = data["attributes"]
		self._tags       = data["tags"]
		self._contentSignature    = data["contentSignature"]
		self._attributesSignature = data["attributesSignature"]
		return self

	def isDirectory( self ):
		"""Tells wether the node is a directory or not."""
		return False
	
	def hasChildren( self ):
		"""Tells if this node has any children."""
		return 0
	
	def children( self ):
		"""Returns the children of this node."""
		return ()

	def doOnParents(self, function):
		"""Apply this function on this node parent, on the parent parent...
		until the root node is reached."""
		if self._parent:
			function(self._parent)
			self._parent.doOnParents(function)
	
	def usesSignature( self ):
		"""Tells wether this node should copmute its SHA-1 signature when updated."""
		return self._usesSignature
	
	def _appendToWalkPath( self, walkPath ):
		"""Appends this node to the given walk path. This allows to iterate
		nodes using the given `walkPath', which is a list."""
		walkPath.append(self)

	def _belongsToState( self, state ):
		"""Tells that this node belongs to the given state. This clears the node
		cache."""
		self._state = state
		self._cached = False

	def _setParent( self, nodeState ):
		"""Sets the parent NodeState for this node."""
		self._parent = nodeState

	# Tagging___________________________________________________________________

	def tag(self, _name=None, **tags):
		"""Tags the given node with the following list of tags (given as named
		arguments). If a single argument is given, then the value of the given
		tag is returned."""
		if _name:
			return self._tags.get(_name)
		else:
			for key in tags:
				self._tags[key] = tags[key]
			return True

	# Caching__________________________________________________________________

	def isCached( self, value=None ):
		"""Tells wether the node is cached, or not."""
		if value == None:
			return self._cached
		else:
			self._iscached = value

	def location( self, location=None ):
		"""Sets the location that this node represents, relatively to the state
		root"""
		if location == None:
			return self._attributes["Location"]
		else:
			location = os.path.normpath(location)
			self._attributes["Location"] = location

	def name(self):
		"""Returns the name of this node. This corresponds to the basename of
		this node location."""
		return os.path.basename(self.location())

	def getAbsoluteLocation( self ):
		"""Returns the node location, which implies that the location has been
		assigned a state."""
		assert self._state != None
		return self._state.getAbsoluteLocation(self.location())

	def exists( self ):
		"""Returns true if the node exists on the local filesystem"""
		return os.path.exists( self.getAbsoluteLocation() )

	def update( self, signatureFilter=lambda x:True ):
		"""Creates the node by making the proper initilisation. The node MUST
		be available on the local filesystem when this method is run."""
		# Links may point to unexisting locations
		assert os.path.islink(self.getAbsoluteLocation()) or self.exists()
		self._updateAttributes()
		if self._usesSignature: self._updateSignature()
		self._state.cacheNodeState(self)

	def _updateAttributes( self ):
		"""Gathers the attributes related to this file system node."""
		path = self.getAbsoluteLocation()
		assert self.exists()
		stat_info = map(lambda x:str(x), os.stat(path))
		self._attributes["Size"] = stat_info[stat.ST_SIZE]
		self._attributes["Creation"] = stat_info[stat.ST_CTIME]
		self._attributes["Modification"] = stat_info[stat.ST_MTIME]
		self._attributes["Owner"] = stat_info[stat.ST_UID]
		self._attributes["Group"] = stat_info[stat.ST_GID]
		self._attributes["Permissions"] = stat_info[stat.ST_MODE]

	def getAttribute( self, info ):
		"""Returns the attributes information with the given name"""
		return self._attributes[info]

	def getAttributes( self ):
		"""Returns the attributes of this node."""
		return self._attributes

	def getSize( self ):
		"""Alias to 'getAttribute("Size")'"""
		return self.getAttribute("Size")

	def getCreation( self ):
		"""Alias to 'getAttribute("Creation")'"""
		return self.getAttribute("Creation")

	def getModification( self ):
		"""Alias to 'getAttribute("Modification")'"""
		return self.getAttribute("Modification")

	def _attributeInSignature( self, attributeName ):
		"""Tells wether the given attribute name should be used in the computation
		of the signature."""
		if attributeName not in ( "Creation" ):
			return True
		else:
			return False

	def _updateSignature( self ):
		"""Creates the signature of this file system node."""

		# The content signature is up to concrete subclasses, so we only
		# set it to None (which is its default value)
		self._contentSignature = None

		# Updates the attributes signature
		items = self._attributes.items()
		items.sort()
		signature = []
		for key, value in items:
			# Creation attribute does not appear in the attributes signature
			if self._attributeInSignature(key):
				signature.append(str(key)+str(value))
		self._attributesSignature = hashlib.sha1("".join(signature)).hexdigest()

	def getContentSignature( self ):
		if self._contentSignature == None: self._updateSignature()
		return self._contentSignature

	def getAttributesSignature( self ):
		"""Returns the signature of the attributes. Attributes listed in
		ATTRIBUTES_NOT_IN_SIGNATURE are not taken into account in the
		computation of the node signature."""
		if self._attributesSignature == None: self._updateSignature()
		return self._attributesSignature

	def getSignature( self ):
		"""Returns the concatenation of the content signature and the
		attributes signature, separated by a dash."""
		assert self.usesSignature(), "Node does not use signature:" + str(self)
		return str(self.getContentSignature())+"-"+str(self.getAttributesSignature())
	
	def __repr__(self):
		return self.location()
		
#------------------------------------------------------------------------------
#
#  DirectoryNodeState
#
#------------------------------------------------------------------------------

class DirectoryNodeState(NodeState):
	"""A node representing a directory on the filesystem"""

	def __init__( self, state, location, accepts=(), rejects=(), data=None ):
		"""Creates a new directory node.

		Same operations as the file system node."""
		# The list of child nodes
		self._children = []
		NodeState.__init__(self, state, location, usesSignature=False,
		accepts=accepts, rejects=rejects, data=data )

	def exportToDict( self ):
		result = NodeState.exportToDict(self)
		result["children"] = tuple(n.exportToDict() for n in self._children)
		return result

	def importFromDict( self, data ):
		result = NodeState.importFromDict(self, data)
		for child in data["children"]:
			self._children.append(NodeState.FromDict(self._state, child))
		return self

	def isDirectory( self ):
		"""Returns True."""
		return True
	
	def hasChildren( self ):
		return len(self._children)
	
	def children( self ):
		return self._children
	
	def _belongsToState( self, state ):
		"""Sets the given state as this node state. This invalidates makes the
		node uncached."""
		NodeState._belongsToState(self, state)
		for child in self.getChildren(): child._belongsToState(state)

	def update( self, nodeSignatureFilter=lambda x:True ):
		"""Updates the given directory node signature and attributes-information. The
		directory node location MUST exist.

		The nodeSignatureFilter allows to filter each node and decided wether its signature
		should be computed or not. By default, every node has its signature computed.

		WARNING: Updating a directory nodes updates its children list according
		to the local file system, so new nodes are always created for new
		directories and files."""
		# We ensure that the directory exists
		assert self.exists()
		# We retrieve an order list of the directory content
		try:
			content = os.listdir(self.getAbsoluteLocation())
		except OSError:
			return
		self._children = []
		# We create new nodes for each content
		for element_loc in content:
			# We ensure that the node is accepted
			matched = True
			for a in self._accepts:
				if not fnmatch.fnmatch(element_loc, a):
					matched = False
					break
			for a in self._rejects:
				if fnmatch.fnmatch(element_loc, a):
					matched = False
					break
			if not matched:
				continue
			element_loc = os.path.join( self.location(), element_loc )
			abs_element_loc = self._state.getAbsoluteLocation(element_loc)
			# Skips symlinks
			if os.path.islink( abs_element_loc):
				continue
			elif os.path.isdir( abs_element_loc ):
				node = DirectoryNodeState( self._state, element_loc,
				accepts=self._accepts, rejects=self._rejects )
				node.update(nodeSignatureFilter)
			else:
				if nodeSignatureFilter(abs_element_loc):
					node = FileNodeState( self._state, element_loc, True )
				else:
					node = FileNodeState( self._state, element_loc, False )
				node.update()
			if node: self.appendChild(node)
		# This is VERY IMPORTANT : we ensure that the children are canonicaly
		# sorted
		self._children.sort(lambda x,y: cmp(x.location(), y.location()))
		# We can only update the node after children were added, see
		# _updateSignature
		NodeState.update(self)

	def _appendToWalkPath( self, walkPath ):
		"""Appends this node to the given walk path. This allows to iterate
		nodes using the given `walkPath', which is a list.

		Directory node is appended first, then children are appended in
		alphabetical order."""
		NodeState._appendToWalkPath(self, walkPath)
		for child in self._children: child._appendToWalkPath(walkPath)

	def iterateDescendants( self ):
		for child in self._children:
			yield child
			if child.hasChildren():
				for descendant in child.iterateDescendants():
					yield descendant

	def walkChildren( self, function, context=None ):
		"""Applies the given function to every child of this node."""
		for child in self._children:
			if context != None:
				function(child, context)
			else:
				function(child)
			if child.hasChildren():
				child.walkChildren(function, context)

	def getChildren( self, types = None ):
		"""Returns the children of this directory. The optional `types' list
		enumerates the classes of the the returned children, acting as a type
		filter. By default, types are DirectoryNodeState and FileNodeState."""
		if types == None: types = ( DirectoryNodeState, FileNodeState )
		# Returns only elements of the listed types
		def typefilter(x):
			for atype in types:
				if isinstance(x,atype): return True
			return False
		# We execute the filter
		return filter( typefilter, self._children )

	def appendChild( self, child ):
		"""Appends a child node to this directory. The list of children is
		automatically maintained as sorted."""
		self._children.append(child)
		child._setParent(self)
		# We make sure the list of children is sorted.
		self._children.sort()

	def _attributeInSignature( self, attributeName ):
		"""Tells wether the given attribute name should be used in the computation
		of the signature."""
		if attributeName not in ( "Creation", "Modification" ):
			return True
		else:
			return False

	def _updateSignature( self ):
		"""A directory signature is the signature of the string composed of the
		names of all of its elements."""
		NodeState._updateSignature(self)
		children = []
		for child in self.getChildren():
			children.append(os.path.basename(child.location()))
		self._contentSignature = hashlib.sha1("".join(children)).hexdigest()

	def __repr__(self):
		res = [self.location()]
		for child in self._children:
			res.append (child.__repr__())
		return "\n".join(res)

#------------------------------------------------------------------------------
#
#  FileNodeState
#
#------------------------------------------------------------------------------

class FileNodeState(NodeState):
	"""A node representing a file on the filesystem."""

	def isDirectory( self ):
		"""Returns False."""
		return False

	def getData( self ):
		"""Returns the data contained in this file as a string."""
		fd = None
		try:
			fd = open(self.getAbsoluteLocation(), "r")
			assert fd!=None
			data = fd.read()
			fd.close()
		except IOError:
			data = ""
		return data

	def _updateSignature( self ):
		"""A file signature is the signature of its content."""
		NodeState._updateSignature(self)
		# We only compute the content signature if the node is said to. This
		# allows to perform quick changes detection when large files are
		# involved.
		# if self.usesSignature():
		self._contentSignature = hashlib.sha1(self.getData()).hexdigest()

#------------------------------------------------------------------------------
#
#  Ancestor guessing
#
#------------------------------------------------------------------------------

def guessNodeStateAncestors( node, nodes ):
	"""Returns an order list of (percentage, nodes) indicating the
	probability for each node to be an ancestor of the current node.

	You should look at the source code for more information on how the
	percentage is avaluated."""
	# TODO: Make more test and try to explain why this should work. I think
	# this should be tuned by usage.
	assert len(nodes)>0
	# Computes the difference between the given node and the current node
	# attributes information value
	def difference( node, info ):
		return abs(int(node.getAttribute(info)) - int(node.getAttribute(info)))
	# Initialises the maxima table for the given attributes info
	maxima = {
		"Creation":difference(nodes[0], "Creation"),
		"Size":difference(nodes[0], "Size")
	}
	# We get the maxima for each attributes info
	for attributes in ("Creation", "Size"):
		for node in nodes:
			maxima[attributes] = max(maxima[attributes], difference(node, attributes))
	# We calculate the possible ancestry rate
	result = []
	for node in nodes:
		node_rate = 0.0
		# Same class, rate 40%
		if node.__class__ == node.__class__:
			node_rate += 0.40
		# Creation rate, up to 25%
		creation_rate = 0.25 * ( 1 - float(difference(node, "Creation")) /
			maxima["Creation"] )
		# Divided by two if rated node creation date is > to current node
		# creation date
		if node.getAttribute("Creation") > \
		   node.getAttribute("Creation"):
			creation_rate = creation_rate / 2.0
		node_rate += creation_rate
		# If modification date is < to current modification date, add 15%
		if node.getAttribute("Modification") < \
		   node.getAttribute("Modification"):
			node_rate += 0.15
		# Size rate, up to 10%
		node_rate += 0.10 * ( 1 - float(difference(node, "Size")) /
			maxima["Size"] )
		# If owner is the same then add 3%
		if node.getAttribute("Owner") ==\
		   node.getAttribute("Owner"):
			node_rate += 0.03
		# If group is the same then add 3%
		if node.getAttribute("Group") ==\
		   node.getAttribute("Group"):
			node_rate += 0.03
		# If permissions are the same then add 3%
		if node.getAttribute("Permissions") ==\
		   node.getAttribute("Permissions"):
			node_rate += 0.03
		result.append((node_rate, node))
	result.sort(lambda x,y: cmp(x[0], y[0]))
	return result

#------------------------------------------------------------------------------
#
#  File system state
#
#------------------------------------------------------------------------------

class State:
	"""A state object reflects the state of a particular file system location by
	creating node objects (NodeStates) that represent the file system state at a
	particular moment.. These nodes can be later queried by location and
	signature."""

	@staticmethod
	def FromJSONFile( path ):
		assert os.path.exists(path)
		f = file(path, 'r')
		d = f.read()
		f.close()
		return State.FromDict(simplejson.loads(d))

	@staticmethod
	def FromDict( data ):
		root = data["rootNodeState"]
		state = State(
			data["rootLocation"],
			None,
			populate=False,
			accepts=list(data["accepts"]),
			rejects=list(data["rejects"])
		)
		root = NodeState.FromDict(state, root)
		state.root(root)
		state.cacheNodeStates()
		return state

	def __init__( self, rootLocation, rootNodeState=None, populate=False,
	accepts=(), rejects=() ):
		"""Creates a new state with the given location as the root. If the populate
		variable is set to True, then the state is populated with the data gathered
		from the fielsystem.

		Note that the given rootNodeState is NOT UPDATED automatically, because
		it may not exist on the local filesystem.

		By default, no root node is created, you can create one with the
		'populate' method."""
		# Signatures and locations are used by the change tracking system
		# Signatures is a map with signatures as key and a list of file system
		# nodes as values.
		self._contentSignatures = {}
		# Locations is a map with location as keys and file system nodes as
		# values.
		self._accepts   = []
		self._rejects   = []
		self._locations = {}
		self._rootNodeState = None
		self._rootLocation  = None
		if rootLocation: self.location(os.path.abspath(rootLocation))
		else: self.location(None)
		self.root(rootNodeState)
		self.accepts(accepts)
		self.rejects(rejects)
		if populate:
				self.populate()

	def exportToDict( self ):
		locations = {}
		for k,v in self._locations.items():
			locations[k] = v._uid
		result = {
			"accepts":self._accepts,
			"rejects":self._rejects,
			"rootLocation": self._rootLocation,
			"rootNodeState":self._rootNodeState and self._rootNodeState.exportToDict()
		}
		return result

	def onNodeCreated( self, node ):
		"""A callback placeholder that can be used to output stuff when a node
		is created."""
		return None

	def accepts( self, a ):
		"""Specifies the GLOBS (as strings) that all inserted node must
		match."""
		if type(a) in (tuple,list): self._accepts.extend(a)
		else: self._accepts.append(a)

	def rejects( self, a ):
		"""Specifies the GLOBS (as strings) that tell which node should never be
		added."""
		if type(a) in (tuple,list): self._rejects.extend(a)
		else: self._rejects.append(a)

	def populate( self, nodeSignatureFilter=lambda x:True):
		"""Creates the root node for this state. This node will be
		automatically updated and cached.

		The nodeSignatureFilter is a predicate which tells if a node at the
		given location should compute its signature or not.
		"""
		rootNodeState = DirectoryNodeState(self, "", accepts=self._accepts,
		rejects=self._rejects)
		rootNodeState.update(nodeSignatureFilter)
		self._creationTime = time.localtime()
		self.root(rootNodeState)

	def root( self, node=None ):
		"""Returns this state root node."""
		if node != None: self._rootNodeState = node
		else: return self._rootNodeState

	def getCreationTime( self ):
		"""Returns the time at which this state was created"""
		return self._creationTime

	def location( self, path=None ):
		"""Returns the absolute location of this state in the local
		filesystem."""
		if path == None:
			return self._rootLocation
		else:
			self._rootLocation = path

	def getAbsoluteLocation( self, location ):
		"""Returns the absolute location of the given relative location"""
		return os.path.normpath(self.location() + os.sep + location)

	def cacheNodeState( self, node ):
		"""Caches a node information in this state. This registers the node
		signature and location so that it can be processed by the change
		tracking."""
		self._locations[node.location()] = node
		result = None
		# We make sure that the singature exists
		if node.usesSignature():
			try:
				result = self._contentSignatures[node.getContentSignature()]
			except:
				result = []
				self._contentSignatures[node.getContentSignature()] = result
			# And we append the node
			result.append(node)
		node.isCached(True)
		return node

	def cacheNodeStates( self ):
		assert self.root()
		self.cacheNodeState(self.root())
		for node in self.root().iterateDescendants():
			if not node.isCached():
				self.cacheNodeState(node)

	def nodes( self ):
		"""Returns the list of all nodes registered in this state"""
		return self._locations.values()

	def nodesWithContentSignature( self, signature ):
		"""Returns a list of nodes with the given content signature. The node
		may not exist, in which case None is returned."""
		try:
			return self._contentSignatures[signature]
		except:
			return ()

	def nodeWithLocation( self, location ):
		"""Returns the node with the given location. The node may not exist, in
		which case None is returned."""
		return self._locations.get(location)

	def nodesByLocation( self ):
		return self._locations

	def nodesByContentSignature( self ):
		return self._contentSignatures

	def __repr__(self):
		return repr(self.root())

#------------------------------------------------------------------------------
#
#  Change tracking
#
#------------------------------------------------------------------------------

def sets( firstSet, secondSet, objectAccessor=lambda x:x ):
	"""
	Returns elements that are unique to first and second set, then elements
	that are common to both.

	Returns the following sets:

		- elements only in first set
		- elements only in second set
		- elements common to both sets

	The objectAccessor operation is used on each object of the set to access
	the element that will be used as a comparison basis. By default, it is the
	element itself."""

	# We precompute the maps
	set_first_acc  = map(objectAccessor, firstSet)
	set_second_acc = map(objectAccessor, secondSet)

	# Declare the filtering predicates
	# First set elements not in second set
	def first_only(x): return objectAccessor(x) not in set_second_acc
	# Second set elements not in first set
	def second_only(x): return objectAccessor(x) not in set_first_acc
	# First sets elements in second set == second set elts in first set
	def common(x): return objectAccessor(x) in set_second_acc

	# Compute the result
	return	filter(first_only, firstSet),\
			filter(second_only, secondSet),\
			filter(common, firstSet)

class Change:
	"""A change represents differences between two states."""

	def __init__ ( self, newState, previousState ):
		# created+copied+moved = total of nodes only in new state
		self._created   = [] # Only in NEW
		self._copied    = [] # Only in NEW
		self._moved     = [] # Only in NEW
		# removed = total of nodes only in old state
		self._removed   = [] # Only in OLD
		# changed + unchanged = total of nodes in both STATES
		self._modified   = []
		self._unmodified = []
		# We do not count untracked, because this is a superset
		self._all =  [
			self._created,
			self._copied,
			self._moved,
			self._removed,
			self._modified,
			self._unmodified
		]
		self.newState      = newState
		self.previousState = previousState

	def anyChanges( self ):
		"""Tells wether there were any changes"""
		for group in self._all[:-1]:
			if group: return True
		return False

	def removeLocation( self, location ):
		"""Removes the nodes that start with the given location from this
		change set."""
		if location == None: return
		for _set in self._all:
			i = 0
			# We cannot iterate on the array, because we may remove the
			# iterated value, which seems to fuck up the iteration
			while i < len(_set):
				node = _set[i]
				if node.location().find(location) == 0:
					_set.pop(i)
				else:
					i += 1

	def getOnlyInNewState( self ):
		res = []
		res.extend(self._created)
		res.extend(self._copied)
		res.extend(self._moved)
		return res

	def getOnlyInOldState( self ):
		return self._removed

	def getOnlyInBothStates( self ):
		res = []
		res.extend(self._modified)
		res.extend(self._unmodified)

	def getCreated( self ):
		return self._created

	def getCopied( self ):
		return self._copied

	def getRemoved( self ):
		return self._removed

	def getMoved( self ):
		return self._moved

	def getModified( self ):
		return self._modified

	def getUnmodified( self ):
		return self._unmodified

	def _filterAll( self, f ):
		result = []
		for _set in self._all: result.extend(filter(f,_set))
		return result

	def count( self ):
		"""Returns the number of elements in this change."""
		# FIXME: This is false !
		count = 0
		for _set in self._all: count += len(_set)
		return count

class Tracker:
	"""Creates a change object that characterises the difference between  the
	two states."""

	TIME = "Time"
	SHA1 = "SHA-1"

	def detectChanges( self, newState, previousState, method=TIME ):
		"""Detects the changes between the new state and the previous state. This
		returns a Change object representing all changes."""

		changes = Change(newState, previousState)

		# We look for new nodes, nodes that are only in the previous location,
		# and nodes that are still there
		new_locations, prev_locations, same_locations = sets(
			newState.nodesByLocation().items(),
			previousState.nodesByLocation().items(),
			lambda x:x[0]
		)

		# TODO: This should be improved with copied and moved files, but this
		# would require a GUI

		# TODO: changes._all, ._new and ._old are not space efficient

		for location, node in new_locations:
			self.onCreated(node)
			changes._created.append(node)

		for location, node in prev_locations:
			self.onRemoved(node)
			changes._removed.append(node)

		for location, node in same_locations:
			previous_node = previousState.nodeWithLocation(location)
			if method == Tracker.SHA1:
				assert previous_node.getContentSignature()
				assert node.getContentSignature()
				if previous_node.getContentSignature() != node.getContentSignature():
					changes._modified.append(node)
					self.onModified(previous_node, node)
				else:
					changes._unmodified.append(node)
					self.onUnmodified(previous_node, node)
			else:
				ptime = previous_node.getAttribute("Modification")
				ntime = node.getAttribute("Modification")
				if ptime != ntime:
					changes._modified.append(node)
					self.onModified(previous_node, node)
				else:
					changes._unmodified.append(node)
					self.onUnmodified(previous_node, node)

		# We make sure that we classified every node of the state
		assert len(new_locations) + len(prev_locations) + len(same_locations)\
		== changes.count()
		return changes

	def onCreated( self, node ):
		"""Handler called when a node was created, ie. it is present in the new
		state and not in the old one."""
		node.tag(event=NodeState.ADDED)
		node.doOnParents(lambda x:x.tag("event") == None and x.tag(event=NodeState.MODIFIED))
	
	def onModified(self, newNode, oldNode):
		"""Handler called when a node was modified, ie. it is not the same in
		the new and in the old state."""
		newNode.tag(event=NodeState.MODIFIED)
		oldNode.tag(event=NodeState.MODIFIED)

	def onUnmodified(self, newNode, oldNode):
		newNode.tag(event=None)
		oldNode.tag(event=None)

	def onRemoved(self, node):
		"""Handler called when a node was removed, ie. it is not the in
		the new state but is in the old state."""
		node.tag(event=NodeState.REMOVED)

#------------------------------------------------------------------------------
#
#  File system node
#
#------------------------------------------------------------------------------

#TODO: Describe -d option
USAGE = """\
sink [-d|diff] [OPTIONS] [OPERATION] ORIGIN COMPARED...

ORIGIN    is the directory to which we want to compare the others
COMPARED  is a list of directories that will be compared to ORIGIN

Options:

  -c, --content (dflt)   Uses content analysis to detect changes
  -t, --time             Uses timestamp to detect changes
  -dNUM                  Compares the file at line NUM in the listing
  --ignore-spaces        Ignores the spaces when analyzing the content
  --ignore   GLOBS       Ignores the files that match the glob
  --only     GLOBS       Only accepts the file that match glob
  --difftool TOOL        Specifies a specific too for the -n option

You can also specify what you want to be listed in the diff:

  [-+]A                  Hides/Shows ALL files
  [-+]s                  Hides/Shows SAME files       [=]
  [-+]a                  Hides/Shows ADDED files      [+]
  [-+]r                  Hides/Shows REMOVED files    [-]
  [-+]m                  Hides/Shows MODIFIED files   [>] or [<]
  [-+]n                  Hides/Shows NEWER files      [>]
  [-+]o                  Hides/Shows OLDER files      [<]

GLOBS understand '*' and '?', will refer to the basename and can be
separated by commas. If a directory matches the glob, it will not be
traversed (ex: --ignore '*.pyc,*.bak,.[a-z]*')

Legend:

[=] no changes         [+] file added           [>] changed/newer
                       [-] file removed         [<] changed/older
                       -!- file missing
""" 

CONTENT_MODE = True
TIME_MODE    = False
ADDED        = "[+]"
REMOVED      = "[-]"
NEWER        = "[>]"
OLDER        = "[<]"
SAME         = "[=]"
ABSENT       = "-!-"

class Engine:
	"""Implements operations used by the Sink main command-line interface."""

	def __init__( self, logger, config=None ):
		self.logger        = logger
		self.mode          = CONTENT_MODE
		self.ignore_spaces = True
		self.rejects       = []
		self.accepts       = []
		self.diffs         = []
		self.show          = {}
		if config: self.setup(config)

	def setup( self, config ):
		"""Sets up the engine using the given configuration object."""
		self.mode          = config["sink.mode"]
		self.diff_command  = config["sink.diff"]
		self.diffs         = []
		self.accepts       = config["filters.accepts"]
		self.rejects       = config["filters.rejects"]
		self.ignore_spaces = config["sink.whitespace"]
		if os.environ.get("DIFF"): self.diff_command = os.environ.get("DIFF")
		self.show          = {}

	def _parseOptions( self, arguments ):
		return getopt.getopt( arguments, "cthVvld:iarsmno",\
		["version", "help", "verbose", "list", "checkin", "checkout",
		"modified",
		"time", "content", "ignore-spaces", "ignorespaces", "diff=", "ignore=",
		"ignores=", "accept=", "accepts=", "filter", "only="])
		
	def configure( self, arguments ):
		# We extract the arguments
		optlist, args = self._parseOptions(arguments)
		# We parse the options
		for opt, arg in optlist:
			if opt in ('-h', '--help'):
				print USAGE ; return 0
			elif opt in ('-v', '--version'):
				print __version__
				return 0
			elif opt in ('-c', '--content'):
				self.mode   = CONTENT_MODE
			elif opt in ('-t', '--time'):
				self.mode = TIME_MODE
			elif opt in ('--ignorespaces', '--ignore-spaces'):
				self.ignore_spaces = True
			elif opt in ('--ignore', '--ignores'):
				self.rejects.extend(arg.split(","))
			elif opt in ('--only', '--accept','--accepts'):
				self.accepts.extend(arg.split("."))
			elif opt == '-d':
				if arg.find(":") == -1: diff, _dir = int(arg), 0
				else: diff, _dir = map(int, arg.split(":"))
				self.diffs.append((diff, _dir))
			elif opt == '--difftool':
				self.diff_command = arg
			elif opt == "+A":
				for t in [ADDED, REMOVED, SAME, NEWER, OLDER]:
					self.show[t]   = False
			elif opt in ('-a'):
				self.show[ADDED]   = False
			elif opt in ('-r'):
				self.show[REMOVED] = False
			elif opt in ('-s'):
				self.show[SAME]    = False
			elif opt in ('-m'):
				self.show[NEWER]   = False
				self.show[OLDER]   = False
			elif opt in ('-n'):
				self.show[NEWER]   = False
			elif opt in ('-o'):
				self.show[OLDER]   = False
		# We adjust the show
		nargs = []
		for arg in args:
			if   arg == "+A":
				for t in [ADDED, REMOVED, SAME, NEWER, OLDER]:
					self.show[t] = True
			elif arg == "+a":
				self.show[ADDED] = True
			elif arg == "+r":
				self.show[REMOVED] = True
			elif arg == "+s":
				self.show[SAME] = True
			elif arg == "+m":
				self.show[NEWER] = self.show[OLDER] = True
			elif arg == "+o":
				self.show[OLDER] = True
			elif arg == "+n":
				self.show[OLDER] = True
			else:
				nargs.append(arg)
		args = nargs
		# We set the default values for the show, only if there was no + option
		if self.show == {} or filter(lambda x:not x, self.show.values()):
			for key,value in { ADDED:True, REMOVED:True, NEWER:True, OLDER:True,
			SAME:False }.items():
				self.show.setdefault(key, value)
		return args

	def run( self, arguments ):
		"""Runs the command using the given list of arguments (a list of
		strings)."""
		logger   = self.logger
		accepts  = self.accepts
		rejects  = self.rejects
		show     = self.show
		diffs    = self.diffs

		try:
			args = self.configure(arguments)
		except Exception, e:
			return logger.error(e)

		# We ensure that there are enough arguments
		if len(args) < 2:
			logger.error("Bad number of arguments\n" + USAGE)
			return -1
		origin_path    = args[0]
		compared_paths = args[1:]
		# Wensures that the origin and compared directories exist
		if not os.path.exists(origin_path):
			logger.error("Origin directory does not exist.") ; return -1
		for path in compared_paths:
			if not os.path.exists(path):
				logger.error("Compared directory does not exist.") ; return -1

		# Detects changes between source and destination
		tracker         = Tracker()
		# FIXME: Support accepts and rejects
		if os.path.isfile(origin_path):
			origin_state = State.FromJSONFile(origin_path)
		else:
			origin_state = State(origin_path, accepts=accepts, rejects=rejects)
			origin_state.populate( lambda x: self.mode )
		compared_states = []
		for path in compared_paths:
			if os.path.isfile(path):
				compared_states.append(State.FromJSONFile(path))
			else:
				state = State(path, accepts=accepts, rejects=rejects)
				state.populate(lambda x: self.mode )
				compared_states.append(state)

		changes     = []
		any_changes = False
		for state in compared_states:
			#logger.message("Comparing '%s' to origin" % (state.location()))
			if self.mode == CONTENT_MODE:
				changes.append(tracker.detectChanges(state, origin_state,
				method=Tracker.SHA1))
			else:
				changes.append(tracker.detectChanges(state, origin_state,
				method=Tracker.TIME))
			any_changes = changes[-1].anyChanges() or any_changes
		# We apply the operation
		if any_changes:
			self.listChanges(
				changes, origin_state, compared_states,
				diffs, diffcommand=self.diff_command, show=show
			)
		else:
			logger.message("No differences")
		return 0

	def usage( self ):
		return USAGE

	def listChanges( self, changes, origin, compared, diffs=[], diffcommand="diff", show=None ):
		"""Outputs a list of changes, with files only in source, fiels only in
		destination and modified files."""
		assert show
		all_locations = []
		all_locations_keys = {}
		# We get the locations by changes
		for change in changes:
			locations = {}
			removed   = change.getOnlyInOldState()
			added     = change.getOnlyInNewState()
			changed   = change.getModified()
			unchanged = change.getUnmodified()
			added.sort(lambda a,b:cmp(a.location(), b.location()))
			removed.sort(lambda a,b:cmp(a.location(), b.location()))
			changed.sort(lambda a,b:cmp(a.location(), b.location()))
			for node in added:
				if not show.get(ADDED): break
				if node.isDirectory(): continue
				all_locations_keys[node.location()] = True
				locations[node.location()] = ADDED
			for node in removed:
				if not show.get(REMOVED): break
				if node.isDirectory(): continue
				all_locations_keys[node.location()] = True
				locations[node.location()] = REMOVED
			for node in changed:
				if not show.get(NEWER) or not show.get(OLDER): break
				if node.isDirectory(): continue
				all_locations_keys[node.location()] = True
				old_node = change.previousState.nodeWithLocation(node.location())
				new_node = change.newState.nodeWithLocation(node.location())
				if old_node.getAttribute("Modification") < new_node.getAttribute("Modification"):
					if not show.get(NEWER): continue
					locations[node.location()] = NEWER
				else:
					if not show.get(OLDER): continue
					locations[node.location()] = OLDER
			for node in unchanged:
				if not show.get(SAME): break
				if node.isDirectory(): continue
				all_locations_keys[node.location()] = True
				locations[node.location()] = SAME
			all_locations.append(locations)
		# Now we print the result
		all_locations_keys = all_locations_keys.keys()
		all_locations_keys.sort(lambda a,b:cmp((a.count("/"),a),(b.count("/"), b)))
		format  = "%0" + str(len(str(len(all_locations_keys))) ) + "d %s %s"
		counter = 0
		def find_diff( num ):
			for _diff, _dir in diffs:
				if _diff == num: return _dir
			return None
		commands_to_execute = []
		for loc in all_locations_keys:
			# For the origin, the node is either ABSENT or SAME
			if origin.nodeWithLocation(loc) == None:
				state = ABSENT
			else:
				state = SAME
			# For all locations
			for locations in all_locations:
				node = locations.get(loc)
				if node == None:
					if origin.nodeWithLocation(loc) == None:
						state += ABSENT
					else:
						state += SAME
				else:
					state += node
			self.logger.message(format % (counter, state, loc))
			found_diff = find_diff(counter)
			if found_diff != None:
				src = origin.nodeWithLocation(loc)
				found_diff -= 1
				if found_diff == -1:
					self.logger.message("Given DIR is too low, using 1 as default")
					found_diff = 0
				if found_diff >= len(compared):
					self.logger.message("Given DIR is too high, using %s as default" % (len(compared)))
					found_diff = len(compared)-1
				dst = compared[found_diff-1].nodeWithLocation(loc)
				if not src:
					self.logger.message("Cannot diff\nFile only in dest:   " + dst.getAbsoluteLocation())
				elif not dst:
					self.logger.message("Cannot diff\nFile only in source: " + src.getAbsoluteLocation())
				else:
					src = src.getAbsoluteLocation()
					dst = dst.getAbsoluteLocation()
					self.logger.message("Diff: '%s' --> '%s'" % (src,dst))
					command = '%s %s %s' % ( diffcommand,src,dst)
					commands_to_execute.append(command)
			counter += 1
		# if added:     self.logger.message( "\t%5s were added    [+]" % (len(added)))
		# if removed:   self.logger.message( "\t%5s were removed   ! " % (len(removed)))
		# if changed:   self.logger.message( "\t%5s were modified [>]" % (len(changed)))
		# if unchanged: self.logger.message( "\t%5s are the same  [=]" % (len(unchanged)))
		if not all_locations_keys: self.logger.message("No changes found.")
		for command in commands_to_execute:
			print ">>", command
			os.system(command)

# EOF - vim: sw=4 ts=4 tw=80 noet

########NEW FILE########
