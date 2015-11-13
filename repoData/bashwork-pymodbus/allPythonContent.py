__FILENAME__ = build
#!/usr/bin/env python
'''
Doxygen API Builder
---------------------
'''
import os, shutil

def is_exe(path):
    ''' Returns if the program is executable
    :param path: The path to the file
    :return: True if it is, False otherwise
    '''
    return os.path.exists(path) and os.access(path, os.X_OK)

def which(program):
    ''' Check to see if an executable exists
    :param program: The program to check for
    :return: The full path of the executable or None if not found
    '''
    fpath, name = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

if which('doxygen') is not None:
    print "Building Doxygen API Documentation"
    os.system("doxygen .doxygen")
    if os.path.exists('../../../build'):
        shutil.move("html", "../../../build/doxygen")
else: print "Doxygen not available...not building"

########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python
'''
Epydoc API Runner
------------------

Using pkg_resources, we attempt to see if epydoc is installed,
if so, we use its cli program to compile the documents
'''
try:
    import sys, os, shutil
    import pkg_resources
    pkg_resources.require("epydoc")

    from epydoc.cli import cli
    sys.argv = '''epydoc.py pymodbus
        --html --simple-term --quiet
        --include-log
        --graph=all
        --docformat=plaintext
        --debug
        --exclude=._
        --exclude=tests
        --output=html/
    '''.split()
    #bugs in trunk for --docformat=restructuredtext

    if not os.path.exists("./html"):
        os.mkdir("./html")

    print "Building Epydoc API Documentation"
    cli()

    if os.path.exists('../../../build'):
        shutil.move("html", "../../../build/epydoc")
except Exception, ex:
    import traceback,sys
    traceback.print_exc(file=sys.stdout)
    print "Epydoc not avaliable...not building"

########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python
"""
Pydoc sub-class for generating documentation for entire packages.

Taken from: http://pyopengl.sourceforge.net/pydoc/OpenGLContext.pydoc.pydoc2.html
Author: Mike Fletcher
"""
import logging
import pydoc, inspect, os, string, shutil
import sys, imp, os, stat, re, types, inspect
from repr import Repr
from string import expandtabs, find, join, lower, split, strip, rfind, rstrip

_log = logging.getLogger(__name__)

def classify_class_attrs(cls):
	"""Return list of attribute-descriptor tuples.

	For each name in dir(cls), the return list contains a 4-tuple
	with these elements:

		0. The name (a string).

		1. The kind of attribute this is, one of these strings:
			   'class method'    created via classmethod()
			   'static method'   created via staticmethod()
			   'property'        created via property()
			   'method'          any other flavor of method
			   'data'            not a method

		2. The class which defined this attribute (a class).

		3. The object as obtained directly from the defining class's
		   __dict__, not via getattr.  This is especially important for
		   data attributes:  C.data is just a data object, but
		   C.__dict__['data'] may be a data descriptor with additional
		   info, like a __doc__ string.
	
	Note: This version is patched to work with Zope Interface-bearing objects
	"""

	mro = inspect.getmro(cls)
	names = dir(cls)
	result = []
	for name in names:
		# Get the object associated with the name.
		# Getting an obj from the __dict__ sometimes reveals more than
		# using getattr.  Static and class methods are dramatic examples.
		if name in cls.__dict__:
			obj = cls.__dict__[name]
		else:
			try:
				obj = getattr(cls, name)
			except AttributeError, err:
				continue

		# Figure out where it was defined.
		homecls = getattr(obj, "__objclass__", None)
		if homecls is None:
			# search the dicts.
			for base in mro:
				if name in base.__dict__:
					homecls = base
					break

		# Get the object again, in order to get it from the defining
		# __dict__ instead of via getattr (if possible).
		if homecls is not None and name in homecls.__dict__:
			obj = homecls.__dict__[name]

		# Also get the object via getattr.
		obj_via_getattr = getattr(cls, name)

		# Classify the object.
		if isinstance(obj, staticmethod):
			kind = "static method"
		elif isinstance(obj, classmethod):
			kind = "class method"
		elif isinstance(obj, property):
			kind = "property"
		elif (inspect.ismethod(obj_via_getattr) or
			  inspect.ismethoddescriptor(obj_via_getattr)):
			kind = "method"
		else:
			kind = "data"

		result.append((name, kind, homecls, obj))

	return result
inspect.classify_class_attrs = classify_class_attrs


class DefaultFormatter(pydoc.HTMLDoc):
	def docmodule(self, object, name=None, mod=None, packageContext = None, *ignored):
		"""Produce HTML documentation for a module object."""
		name = object.__name__ # ignore the passed-in name
		parts = split(name, '.')
		links = []
		for i in range(len(parts)-1):
			links.append(
				'<a href="%s.html"><font color="#ffffff">%s</font></a>' %
				(join(parts[:i+1], '.'), parts[i]))
		linkedname = join(links + parts[-1:], '.')
		head = '<big><big><strong>%s</strong></big></big>' % linkedname
		try:
			path = inspect.getabsfile(object)
			url = path
			if sys.platform == 'win32':
				import nturl2path
				url = nturl2path.pathname2url(path)
			filelink = '<a href="file:%s">%s</a>' % (url, path)
		except TypeError:
			filelink = '(built-in)'
		info = []
		if hasattr(object, '__version__'):
			version = str(object.__version__)
			if version[:11] == '$' + 'Revision: ' and version[-1:] == '$':
				version = strip(version[11:-1])
			info.append('version %s' % self.escape(version))
		if hasattr(object, '__date__'):
			info.append(self.escape(str(object.__date__)))
		if info:
			head = head + ' (%s)' % join(info, ', ')
		result = self.heading(
			head, '#ffffff', '#7799ee', '<a href=".">index</a><br>' + filelink)

		modules = inspect.getmembers(object, inspect.ismodule)

		classes, cdict = [], {}
		for key, value in inspect.getmembers(object, inspect.isclass):
			if (inspect.getmodule(value) or object) is object:
				classes.append((key, value))
				cdict[key] = cdict[value] = '#' + key
		for key, value in classes:
			for base in value.__bases__:
				key, modname = base.__name__, base.__module__
				module = sys.modules.get(modname)
				if modname != name and module and hasattr(module, key):
					if getattr(module, key) is base:
						if not cdict.has_key(key):
							cdict[key] = cdict[base] = modname + '.html#' + key
		funcs, fdict = [], {}
		for key, value in inspect.getmembers(object, inspect.isroutine):
			if inspect.isbuiltin(value) or inspect.getmodule(value) is object:
				funcs.append((key, value))
				fdict[key] = '#-' + key
				if inspect.isfunction(value): fdict[value] = fdict[key]
		data = []
		for key, value in inspect.getmembers(object, pydoc.isdata):
			if key not in ['__builtins__', '__doc__']:
				data.append((key, value))

		doc = self.markup(pydoc.getdoc(object), self.preformat, fdict, cdict)
		doc = doc and '<tt>%s</tt>' % doc
		result = result + '<p>%s</p>\n' % doc

		packageContext.clean ( classes, object )
		packageContext.clean ( funcs, object )
		packageContext.clean ( data, object )
		
		if hasattr(object, '__path__'):
			modpkgs = []
			modnames = []
			for file in os.listdir(object.__path__[0]):
				path = os.path.join(object.__path__[0], file)
				modname = inspect.getmodulename(file)
				if modname and modname not in modnames:
					modpkgs.append((modname, name, 0, 0))
					modnames.append(modname)
				elif pydoc.ispackage(path):
					modpkgs.append((file, name, 1, 0))
			modpkgs.sort()
			contents = self.multicolumn(modpkgs, self.modpkglink)
##			result = result + self.bigsection(
##				'Package Contents', '#ffffff', '#aa55cc', contents)
			result = result + self.moduleSection( object, packageContext)
		elif modules:
			contents = self.multicolumn(
				modules, lambda (key, value), s=self: s.modulelink(value))
			result = result + self.bigsection(
				'Modules', '#fffff', '#aa55cc', contents)

		
		if classes:
			classlist = map(lambda (key, value): value, classes)
			contents = [
				self.formattree(inspect.getclasstree(classlist, 1), name)]
			for key, value in classes:
				contents.append(self.document(value, key, name, fdict, cdict))
			result = result + self.bigsection(
				'Classes', '#ffffff', '#ee77aa', join(contents))
		if funcs:
			contents = []
			for key, value in funcs:
				contents.append(self.document(value, key, name, fdict, cdict))
			result = result + self.bigsection(
				'Functions', '#ffffff', '#eeaa77', join(contents))
		if data:
			contents = []
			for key, value in data:
				try:
					contents.append(self.document(value, key))
				except Exception, err:
					pass
			result = result + self.bigsection(
				'Data', '#ffffff', '#55aa55', join(contents, '<br>\n'))
		if hasattr(object, '__author__'):
			contents = self.markup(str(object.__author__), self.preformat)
			result = result + self.bigsection(
				'Author', '#ffffff', '#7799ee', contents)
		if hasattr(object, '__credits__'):
			contents = self.markup(str(object.__credits__), self.preformat)
			result = result + self.bigsection(
				'Credits', '#ffffff', '#7799ee', contents)

		return result

	def classlink(self, object, modname):
		"""Make a link for a class."""
		name, module = object.__name__, sys.modules.get(object.__module__)
		if hasattr(module, name) and getattr(module, name) is object:
			return '<a href="%s.html#%s">%s</a>' % (
				module.__name__, name, name
			)
		return pydoc.classname(object, modname)
	
	def moduleSection( self, object, packageContext ):
		"""Create a module-links section for the given object (module)"""
		modules = inspect.getmembers(object, inspect.ismodule)
		packageContext.clean ( modules, object )
		packageContext.recurseScan( modules )

		if hasattr(object, '__path__'):
			modpkgs = []
			modnames = []
			for file in os.listdir(object.__path__[0]):
				path = os.path.join(object.__path__[0], file)
				modname = inspect.getmodulename(file)
				if modname and modname not in modnames:
					modpkgs.append((modname, object.__name__, 0, 0))
					modnames.append(modname)
				elif pydoc.ispackage(path):
					modpkgs.append((file, object.__name__, 1, 0))
			modpkgs.sort()
			# do more recursion here...
			for (modname, name, ya,yo) in modpkgs:
				packageContext.addInteresting( join( (object.__name__, modname), '.'))
			items = []
			for (modname, name, ispackage,isshadowed) in modpkgs:
				try:
					# get the actual module object...
##					if modname == "events":
##						import pdb
##						pdb.set_trace()
					module = pydoc.safeimport( "%s.%s"%(name,modname) )
					description, documentation = pydoc.splitdoc( inspect.getdoc( module ))
					if description:
						items.append(
							"""%s -- %s"""% (
								self.modpkglink( (modname, name, ispackage, isshadowed) ),
								description,
							)
						)
					else:
						items.append(
							self.modpkglink( (modname, name, ispackage, isshadowed) )
						)
				except:
					items.append(
						self.modpkglink( (modname, name, ispackage, isshadowed) )
					)
			contents = string.join( items, '<br>')
			result = self.bigsection(
				'Package Contents', '#ffffff', '#aa55cc', contents)
		elif modules:
			contents = self.multicolumn(
				modules, lambda (key, value), s=self: s.modulelink(value))
			result = self.bigsection(
				'Modules', '#fffff', '#aa55cc', contents)
		else:
			result = ""
		return result
	
	
class AlreadyDone(Exception):
	pass
	


class PackageDocumentationGenerator:
	"""A package document generator creates documentation
	for an entire package using pydoc's machinery.

	baseModules -- modules which will be included
		and whose included and children modules will be
		considered fair game for documentation
	destinationDirectory -- the directory into which
		the HTML documentation will be written
	recursion -- whether to add modules which are
		referenced by and/or children of base modules
	exclusions -- a list of modules whose contents will
		not be shown in any other module, commonly
		such modules as OpenGL.GL, wxPython.wx etc.
	recursionStops -- a list of modules which will
		explicitly stop recursion (i.e. they will never
		be included), even if they are children of base
		modules.
	formatter -- allows for passing in a custom formatter
		see DefaultFormatter for sample implementation.
	"""
	def __init__ (
		self, baseModules, destinationDirectory = ".",
		recursion = 1, exclusions = (),
		recursionStops = (),
		formatter = None
	):
		self.destinationDirectory = os.path.abspath( destinationDirectory)
		self.exclusions = {}
		self.warnings = []
		self.baseSpecifiers = {}
		self.completed = {}
		self.recursionStops = {}
		self.recursion = recursion
		for stop in recursionStops:
			self.recursionStops[ stop ] = 1
		self.pending = []
		for exclusion in exclusions:
			try:
				self.exclusions[ exclusion ]= pydoc.locate ( exclusion)
			except pydoc.ErrorDuringImport, value:
				self.warn( """Unable to import the module %s which was specified as an exclusion module"""% (repr(exclusion)))
		self.formatter = formatter or DefaultFormatter()
		for base in baseModules:
			self.addBase( base )
	def warn( self, message ):
		"""Warnings are used for recoverable, but not necessarily ignorable conditions"""
		self.warnings.append (message)
	def info (self, message):
		"""Information/status report"""
		_log.debug(message)

	def addBase(self, specifier):
		"""Set the base of the documentation set, only children of these modules will be documented"""
		try:
			self.baseSpecifiers [specifier] = pydoc.locate ( specifier)
			self.pending.append (specifier)
		except pydoc.ErrorDuringImport, value:
			self.warn( """Unable to import the module %s which was specified as a base module"""% (repr(specifier)))
	def addInteresting( self, specifier):
		"""Add a module to the list of interesting modules"""
		if self.checkScope( specifier):
			self.pending.append (specifier)
		else:
			self.completed[ specifier] = 1
	def checkScope (self, specifier):
		"""Check that the specifier is "in scope" for the recursion"""
		if not self.recursion:
			return 0
		items = string.split (specifier, ".")
		stopCheck = items [:]
		while stopCheck:
			name = string.join(items, ".")
			if self.recursionStops.get( name):
				return 0
			elif self.completed.get (name):
				return 0
			del stopCheck[-1]
		while items:
			if self.baseSpecifiers.get( string.join(items, ".")):
				return 1
			del items[-1]
		# was not within any given scope
		return 0

	def process( self ):
		"""Having added all of the base and/or interesting modules,
		proceed to generate the appropriate documentation for each
		module in the appropriate directory, doing the recursion
		as we go."""
		try:
			while self.pending:
				try:
					if self.completed.has_key( self.pending[0] ):
						raise AlreadyDone( self.pending[0] )
					self.info( """Start %s"""% (repr(self.pending[0])))
					object = pydoc.locate ( self.pending[0] )
					self.info( """   ... found %s"""% (repr(object.__name__)))
				except AlreadyDone:
					pass
				except pydoc.ErrorDuringImport, value:
					self.info( """   ... FAILED %s"""% (repr( value)))
					self.warn( """Unable to import the module %s"""% (repr(self.pending[0])))
				except (SystemError, SystemExit), value:
					self.info( """   ... FAILED %s"""% (repr( value)))
					self.warn( """Unable to import the module %s"""% (repr(self.pending[0])))
				except Exception, value:
					self.info( """   ... FAILED %s"""% (repr( value)))
					self.warn( """Unable to import the module %s"""% (repr(self.pending[0])))
				else:
					page = self.formatter.page(
						pydoc.describe(object),
						self.formatter.docmodule(
							object,
							object.__name__,
							packageContext = self,
						)
					)
					file = open (
						os.path.join(
							self.destinationDirectory,
							self.pending[0] + ".html",
						),
						'w',
					)
					file.write(page)
					file.close()
					self.completed[ self.pending[0]] = object
				del self.pending[0]
		finally:
			for item in self.warnings:
				_log.info(item)
			
	def clean (self, objectList, object):
		"""callback from the formatter object asking us to remove
		those items in the key, value pairs where the object is
		imported from one of the excluded modules"""
		for key, value in objectList[:]:
			for excludeObject in self.exclusions.values():
				if hasattr( excludeObject, key ) and excludeObject is not object:
					if (
						getattr( excludeObject, key) is value or
						(hasattr( excludeObject, '__name__') and
						 excludeObject.__name__ == "Numeric"
						 )
					):
						objectList[:] = [ (k,o) for k,o in objectList if k != key ]
	def recurseScan(self, objectList):
		"""Process the list of modules trying to add each to the
		list of interesting modules"""
		for key, value in objectList:
			self.addInteresting( value.__name__ )

#---------------------------------------------------------------------------# 		
# Main Runner
#---------------------------------------------------------------------------# 		
if __name__ == "__main__":
    if not os.path.exists("./html"):
        os.mkdir("./html")

    print "Building Pydoc API Documentation"
    PackageDocumentationGenerator(
        baseModules = ['pymodbus', '__builtin__'],
        destinationDirectory = "./html/",
        exclusions = ['math', 'string', 'twisted'],
        recursionStops = [],
    ).process ()

    if os.path.exists('../../../build'):
        shutil.move("html", "../../../build/pydoc")

########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python
'''
Pydoctor API Runner
---------------------

Using pkg_resources, we attempt to see if pydoctor is installed,
if so, we use its cli program to compile the documents
'''
try:
    import sys, os, shutil
    import pkg_resources
    pkg_resources.require("pydoctor")

    from pydoctor.driver import main
    sys.argv = '''pydoctor.py --quiet
        --project-name=Pymodbus
        --project-url=http://code.google.com/p/pymodbus/
        --add-package=../../../pymodbus
        --html-output=html
        --html-write-function-pages --make-html'''.split()

    print "Building Pydoctor API Documentation"
    main(sys.argv[1:])

    if os.path.exists('../../../build'):
        shutil.move("html", "../../../build/pydoctor")
except: print "Pydoctor unavailable...not building"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# PyModbus documentation build configuration file, created by
# sphinx-quickstart on Tue Apr 14 19:11:16 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Pymodbus'
copyright = u'2009, Galen Collins'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for extensions ---------------------------------------------------
autodoc_default_flags = ['members', 'inherited-members', 'show-inheritance']
autoclass_content = 'both'

# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pymodbus'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Pymodbus.tex', ur'Pymodbus Documentation',
   ur'Galen Collins', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = asynchronous-client
#!/usr/bin/env python
'''
Pymodbus Asynchronous Client Examples
--------------------------------------------------------------------------

The following is an example of how to use the asynchronous modbus
client implementation from pymodbus.
'''
#---------------------------------------------------------------------------# 
# import needed libraries
#---------------------------------------------------------------------------# 
from twisted.internet import reactor, protocol
from pymodbus.constants import Defaults

#---------------------------------------------------------------------------# 
# choose the requested modbus protocol
#---------------------------------------------------------------------------# 
from pymodbus.client.async import ModbusClientProtocol
#from pymodbus.client.async import ModbusUdpClientProtocol

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# helper method to test deferred callbacks
#---------------------------------------------------------------------------# 
def dassert(deferred, callback):
    def _assertor(value): assert(value)
    deferred.addCallback(lambda r: _assertor(callback(r)))
    deferred.addErrback(lambda  _: _assertor(False))

#---------------------------------------------------------------------------# 
# example requests
#---------------------------------------------------------------------------# 
# simply call the methods that you would like to use. An example session
# is displayed below along with some assert checks. Note that unlike the
# synchronous version of the client, the asynchronous version returns
# deferreds which can be thought of as a handle to the callback to send
# the result of the operation.  We are handling the result using the
# deferred assert helper(dassert).
#---------------------------------------------------------------------------# 
def beginAsynchronousTest(client):
    rq = client.write_coil(1, True)
    rr = client.read_coils(1,1)
    dassert(rq, lambda r: r.function_code < 0x80)     # test that we are not an error
    dassert(rr, lambda r: r.bits[0] == True)          # test the expected value
    
    rq = client.write_coils(1, [True]*8)
    rr = client.read_coils(1,8)
    dassert(rq, lambda r: r.function_code < 0x80)     # test that we are not an error
    dassert(rr, lambda r: r.bits == [True]*8)         # test the expected value
    
    rq = client.write_coils(1, [False]*8)
    rr = client.read_discrete_inputs(1,8)
    dassert(rq, lambda r: r.function_code < 0x80)     # test that we are not an error
    dassert(rr, lambda r: r.bits == [True]*8)         # test the expected value
    
    rq = client.write_register(1, 10)
    rr = client.read_holding_registers(1,1)
    dassert(rq, lambda r: r.function_code < 0x80)     # test that we are not an error
    dassert(rr, lambda r: r.registers[0] == 10)       # test the expected value
    
    rq = client.write_registers(1, [10]*8)
    rr = client.read_input_registers(1,8)
    dassert(rq, lambda r: r.function_code < 0x80)     # test that we are not an error
    dassert(rr, lambda r: r.registers == [17]*8)      # test the expected value
    
    arguments = {
        'read_address':    1,
        'read_count':      8,
        'write_address':   1,
        'write_registers': [20]*8,
    }
    rq = client.readwrite_registers(**arguments)
    rr = client.read_input_registers(1,8)
    dassert(rq, lambda r: r.registers == [20]*8)      # test the expected value
    dassert(rr, lambda r: r.registers == [17]*8)      # test the expected value

    #-----------------------------------------------------------------------# 
    # close the client at some time later
    #-----------------------------------------------------------------------# 
    reactor.callLater(1, client.transport.loseConnection)
    reactor.callLater(2, reactor.stop)

#---------------------------------------------------------------------------# 
# extra requests
#---------------------------------------------------------------------------# 
# If you are performing a request that is not available in the client
# mixin, you have to perform the request like this instead::
#
# from pymodbus.diag_message import ClearCountersRequest
# from pymodbus.diag_message import ClearCountersResponse
#
# request  = ClearCountersRequest()
# response = client.execute(request)
# if isinstance(response, ClearCountersResponse):
#     ... do something with the response
#
#---------------------------------------------------------------------------# 

#---------------------------------------------------------------------------# 
# choose the client you want
#---------------------------------------------------------------------------# 
# make sure to start an implementation to hit against. For this
# you can use an existing device, the reference implementation in the tools
# directory, or start a pymodbus server.
#---------------------------------------------------------------------------# 
defer = protocol.ClientCreator(reactor, ModbusClientProtocol
        ).connectTCP("localhost", Defaults.Port)
defer.addCallback(beginAsynchronousTest)
reactor.run()

########NEW FILE########
__FILENAME__ = asynchronous-processor
#!/usr/bin/env python
'''
Pymodbus Asynchronous Processor Example
--------------------------------------------------------------------------

The following is a full example of a continuous client processor. Feel
free to use it as a skeleton guide in implementing your own.
'''
#---------------------------------------------------------------------------# 
# import the neccessary modules
#---------------------------------------------------------------------------# 
from twisted.internet import serialport, reactor
from twisted.internet.protocol import ClientFactory
from pymodbus.factory import ClientDecoder
from pymodbus.client.async import ModbusClientProtocol

#---------------------------------------------------------------------------# 
# Choose the framer you want to use
#---------------------------------------------------------------------------# 
#from pymodbus.transaction import ModbusBinaryFramer as ModbusFramer
#from pymodbus.transaction import ModbusAsciiFramer as ModbusFramer
#from pymodbus.transaction import ModbusRtuFramer as ModbusFramer
from pymodbus.transaction import ModbusSocketFramer as ModbusFramer

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger("pymodbus")
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# state a few constants
#---------------------------------------------------------------------------# 
SERIAL_PORT  = "/dev/ttyS0"
STATUS_REGS  = (1, 2)
STATUS_COILS = (1, 3)
CLIENT_DELAY = 1


#---------------------------------------------------------------------------# 
# an example custom protocol
#---------------------------------------------------------------------------# 
# Here you can perform your main procesing loop utilizing defereds and timed
# callbacks.
#---------------------------------------------------------------------------# 
class ExampleProtocol(ModbusClientProtocol):

    def __init__(self, framer, endpoint):
        ''' Initializes our custom protocol

        :param framer: The decoder to use to process messages
        :param endpoint: The endpoint to send results to
        '''
        ModbusClientProtocol.__init__(self, framer)
        self.endpoint = endpoint
        log.debug("Beginning the processing loop")
        reactor.callLater(CLIENT_DELAY, self.fetch_holding_registers)

    def fetch_holding_registers(self):
        ''' Defer fetching holding registers
        '''
        log.debug("Starting the next cycle")
        d = self.read_holding_registers(*STATUS_REGS)
        d.addCallbacks(self.send_holding_registers, self.error_handler)

    def send_holding_registers(self, response):
        ''' Write values of holding registers, defer fetching coils

        :param response: The response to process
        '''
        self.endpoint.write(response.getRegister(0))
        self.endpoint.write(response.getRegister(1))
        d = self.read_coils(*STATUS_COILS)
        d.addCallbacks(self.start_next_cycle, self.error_handler)

    def start_next_cycle(self, response):
        ''' Write values of coils, trigger next cycle

        :param response: The response to process
        '''
        self.endpoint.write(response.getBit(0))
        self.endpoint.write(response.getBit(1))
        self.endpoint.write(response.getBit(2))
        reactor.callLater(CLIENT_DELAY, self.fetch_holding_registers)

    def error_handler(self, failure):
        ''' Handle any twisted errors

        :param failure: The error to handle
        '''
        log.error(failure)


#---------------------------------------------------------------------------# 
# a factory for the example protocol
#---------------------------------------------------------------------------# 
# This is used to build client protocol's if you tie into twisted's method
# of processing. It basically produces client instances of the underlying
# protocol::
#
#     Factory(Protocol) -> ProtocolInstance
#
# It also persists data between client instances (think protocol singelton).
#---------------------------------------------------------------------------# 
class ExampleFactory(ClientFactory):

    protocol = ExampleProtocol

    def __init__(self, framer, endpoint):
        ''' Remember things necessary for building a protocols '''
        self.framer = framer
        self.endpoint = endpoint

    def buildProtocol(self, _):
        ''' Create a protocol and start the reading cycle '''
        proto = self.protocol(self.framer, self.endpoint)
        proto.factory = self
        return proto


#---------------------------------------------------------------------------# 
# a custom client for our device
#---------------------------------------------------------------------------# 
# Twisted provides a number of helper methods for creating and starting
# clients:
# - protocol.ClientCreator
# - reactor.connectTCP
#
# How you start your client is really up to you.
#---------------------------------------------------------------------------# 
class SerialModbusClient(serialport.SerialPort):

    def __init__(self, factory, *args, **kwargs):
        ''' Setup the client and start listening on the serial port

        :param factory: The factory to build clients with
        '''
        protocol = factory.buildProtocol(None)
        self.decoder = ClientDecoder()
        serialport.SerialPort.__init__(self, protocol, *args, **kwargs)


#---------------------------------------------------------------------------# 
# a custom endpoint for our results
#---------------------------------------------------------------------------# 
# An example line reader, this can replace with:
# - the TCP protocol
# - a context recorder
# - a database or file recorder
#---------------------------------------------------------------------------# 
class LoggingLineReader(object):

    def write(self, response):
        ''' Handle the next modbus response

        :param response: The response to process
        '''
        log.info("Read Data: %d" % response)

#---------------------------------------------------------------------------# 
# start running the processor
#---------------------------------------------------------------------------# 
# This initializes the client, the framer, the factory, and starts the
# twisted event loop (the reactor). It should be noted that a number of
# things could be chanegd as one sees fit:
# - The ModbusRtuFramer could be replaced with a ModbusAsciiFramer
# - The SerialModbusClient could be replaced with reactor.connectTCP
# - The LineReader endpoint could be replaced with a database store
#---------------------------------------------------------------------------# 
def main():
    log.debug("Initializing the client")
    framer  = ModbusFramer(ClientDecoder())
    reader  = LoggingLineReader()
    factory = ExampleFactory(framer, reader)
    SerialModbusClient(factory, SERIAL_PORT, reactor)
    #factory = reactor.connectTCP("localhost", 502, factory)
    log.debug("Starting the client")
    reactor.run()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = asynchronous-server
#!/usr/bin/env python
'''
Pymodbus Asynchronous Server Example
--------------------------------------------------------------------------

The asynchronous server is a high performance implementation using the
twisted library as its backend.  This allows it to scale to many thousands
of nodes which can be helpful for testing monitoring software.
'''
#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus.server.async import StartTcpServer
from pymodbus.server.async import StartUdpServer
from pymodbus.server.async import StartSerialServer

from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer

#---------------------------------------------------------------------------# 
# configure the service logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# initialize your data store
#---------------------------------------------------------------------------# 
# The datastores only respond to the addresses that they are initialized to.
# Therefore, if you initialize a DataBlock to addresses of 0x00 to 0xFF, a
# request to 0x100 will respond with an invalid address exception. This is
# because many devices exhibit this kind of behavior (but not all)::
#
#     block = ModbusSequentialDataBlock(0x00, [0]*0xff)
#
# Continuing, you can choose to use a sequential or a sparse DataBlock in
# your data context.  The difference is that the sequential has no gaps in
# the data while the sparse can. Once again, there are devices that exhibit
# both forms of behavior::
#
#     block = ModbusSparseDataBlock({0x00: 0, 0x05: 1})
#     block = ModbusSequentialDataBlock(0x00, [0]*5)
#
# Alternately, you can use the factory methods to initialize the DataBlocks
# or simply do not pass them to have them initialized to 0x00 on the full
# address range::
#
#     store = ModbusSlaveContext(di = ModbusSequentialDataBlock.create())
#     store = ModbusSlaveContext()
#
# Finally, you are allowed to use the same DataBlock reference for every
# table or you you may use a seperate DataBlock for each table. This depends
# if you would like functions to be able to access and modify the same data
# or not::
#
#     block = ModbusSequentialDataBlock(0x00, [0]*0xff)
#     store = ModbusSlaveContext(di=block, co=block, hr=block, ir=block)
#
# The server then makes use of a server context that allows the server to
# respond with different slave contexts for different unit ids. By default
# it will return the same context for every unit id supplied (broadcast
# mode). However, this can be overloaded by setting the single flag to False
# and then supplying a dictionary of unit id to context mapping::
#
#     slaves  = {
#         0x01: ModbusSlaveContext(...),
#         0x02: ModbusSlaveContext(...),
#         0x03: ModbusSlaveContext(...),
#     }
#     context = ModbusServerContext(slaves=slaves, single=False)
#---------------------------------------------------------------------------# 
store = ModbusSlaveContext(
    di = ModbusSequentialDataBlock(0, [17]*100),
    co = ModbusSequentialDataBlock(0, [17]*100),
    hr = ModbusSequentialDataBlock(0, [17]*100),
    ir = ModbusSequentialDataBlock(0, [17]*100))
context = ModbusServerContext(slaves=store, single=True)

#---------------------------------------------------------------------------# 
# initialize the server information
#---------------------------------------------------------------------------# 
# If you don't set this or any fields, they are defaulted to empty strings.
#---------------------------------------------------------------------------# 
identity = ModbusDeviceIdentification()
identity.VendorName  = 'Pymodbus'
identity.ProductCode = 'PM'
identity.VendorUrl   = 'http://github.com/bashwork/pymodbus/'
identity.ProductName = 'Pymodbus Server'
identity.ModelName   = 'Pymodbus Server'
identity.MajorMinorRevision = '1.0'

#---------------------------------------------------------------------------# 
# run the server you want
#---------------------------------------------------------------------------# 
StartTcpServer(context, identity=identity, address=("localhost", 5020))
#StartUdpServer(context, identity=identity, address=("localhost", 502))
#StartSerialServer(context, identity=identity, port='/dev/pts/3', framer=ModbusRtuFramer)
#StartSerialServer(context, identity=identity, port='/dev/pts/3', framer=ModbusAsciiFramer)

########NEW FILE########
__FILENAME__ = callback-server
#!/usr/bin/env python
'''
Pymodbus Server With Callbacks
--------------------------------------------------------------------------

This is an example of adding callbacks to a running modbus server
when a value is written to it. In order for this to work, it needs
a device-mapping file.
'''
#---------------------------------------------------------------------------# 
# import the modbus libraries we need
#---------------------------------------------------------------------------# 
from pymodbus.server.async import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSparseDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer

#---------------------------------------------------------------------------# 
# import the python libraries we need
#---------------------------------------------------------------------------# 
from multiprocessing import Queue, Process

#---------------------------------------------------------------------------# 
# configure the service logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# create your custom data block with callbacks
#---------------------------------------------------------------------------# 
class CallbackDataBlock(ModbusSparseDataBlock):
    ''' A datablock that stores the new value in memory
    and passes the operation to a message queue for further
    processing.
    '''

    def __init__(self, devices, queue):
        '''
        '''
        self.devices = devices
        self.queue = queue

        values = {k:0 for k in devices.iterkeys()}
        values[0xbeef] = len(values) # the number of devices
        super(CallbackDataBlock, self).__init__(values)

    def setValues(self, address, value):
        ''' Sets the requested values of the datastore

        :param address: The starting address
        :param values: The new values to be set
        '''
        super(CallbackDataBlock, self).setValues(address, value)
        self.queue.put((self.devices.get(address, None), value))

#---------------------------------------------------------------------------# 
# define your callback process
#---------------------------------------------------------------------------# 
def rescale_value(value):
    ''' Rescale the input value from the range
    of 0..100 to -3200..3200.

    :param value: The input value to scale
    :returns: The rescaled value
    '''
    s = 1 if value >= 50 else -1
    c = value if value < 50 else (value - 50)
    return s * (c * 64)

def device_writer(queue):
    ''' A worker process that processes new messages
    from a queue to write to device outputs

    :param queue: The queue to get new messages from
    '''
    while True:
        device, value = queue.get()
        scaled = rescale_value(value[0])
        log.debug("Write(%s) = %s" % (device, value))
        if not device: continue
        # do any logic here to update your devices

#---------------------------------------------------------------------------# 
# initialize your device map
#---------------------------------------------------------------------------# 
def read_device_map(path):
    ''' A helper method to read the device
    path to address mapping from file::

       0x0001,/dev/device1 
       0x0002,/dev/device2 

    :param path: The path to the input file
    :returns: The input mapping file
    '''
    devices = {}
    with open(path, 'r') as stream:
        for line in stream:
            piece = line.strip().split(',')
            devices[int(piece[0], 16)] = piece[1]
    return devices

#---------------------------------------------------------------------------# 
# initialize your data store
#---------------------------------------------------------------------------# 
queue   = Queue()
devices = read_device_map("device-mapping")
block   = CallbackDataBlock(devices, queue)
store   = ModbusSlaveContext(di=block, co=block, hr=block, ir=block)
context = ModbusServerContext(slaves=store, single=True)

#---------------------------------------------------------------------------# 
# initialize the server information
#---------------------------------------------------------------------------# 
identity = ModbusDeviceIdentification()
identity.VendorName  = 'pymodbus'
identity.ProductCode = 'PM'
identity.VendorUrl   = 'http://github.com/bashwork/pymodbus/'
identity.ProductName = 'pymodbus Server'
identity.ModelName   = 'pymodbus Server'
identity.MajorMinorRevision = '1.0'

#---------------------------------------------------------------------------# 
# run the server you want
#---------------------------------------------------------------------------# 
p = Process(target=device_writer, args=(queue,))
p.start()
StartTcpServer(context, identity=identity, address=("localhost", 5020))

########NEW FILE########
__FILENAME__ = changing-framers
#!/usr/bin/env python
'''
Pymodbus Client Framer Overload
--------------------------------------------------------------------------

All of the modbus clients are designed to have pluggable framers
so that the transport and protocol are decoupled. This allows a user
to define or plug in their custom protocols into existing transports
(like a binary framer over a serial connection).

It should be noted that although you are not limited to trying whatever
you would like, the library makes no gurantees that all framers with
all transports will produce predictable or correct results (for example
tcp transport with an RTU framer). However, please let us know of any
success cases that are not documented!
'''
#---------------------------------------------------------------------------# 
# import the modbus client and the framers
#---------------------------------------------------------------------------# 
from pymodbus.client.sync import ModbusTcpClient as ModbusClient

#---------------------------------------------------------------------------# 
# Import the modbus framer that you want
#---------------------------------------------------------------------------# 
#---------------------------------------------------------------------------# 
#from pymodbus.transaction import ModbusSocketFramer as ModbusFramer
from pymodbus.transaction import ModbusRtuFramer as ModbusFramer
#from pymodbus.transaction import ModbusBinaryFramer as ModbusFramer
#from pymodbus.transaction import ModbusAsciiFramer as ModbusFramer

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# Initialize the client
#---------------------------------------------------------------------------# 
client = ModbusClient('localhost', port=5020, framer=ModbusFramer)
client.connect()

#---------------------------------------------------------------------------# 
# perform your requests
#---------------------------------------------------------------------------# 
rq = client.write_coil(1, True)
rr = client.read_coils(1,1)
assert(rq.function_code < 0x80)     # test that we are not an error
assert(rr.bits[0] == True)          # test the expected value

#---------------------------------------------------------------------------# 
# close the client
#---------------------------------------------------------------------------# 
client.close()

########NEW FILE########
__FILENAME__ = custom-message
#!/usr/bin/env python
'''
Pymodbus Synchrnonous Client Examples
--------------------------------------------------------------------------

The following is an example of how to use the synchronous modbus client
implementation from pymodbus.

It should be noted that the client can also be used with
the guard construct that is available in python 2.5 and up::

    with ModbusClient('127.0.0.1') as client:
        result = client.read_coils(1,10)
        print result
'''
import struct
#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus.pdu import ModbusRequest, ModbusResponse
from pymodbus.client.sync import ModbusTcpClient as ModbusClient

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# create your custom message
#---------------------------------------------------------------------------# 
# The following is simply a read coil request that always reads 16 coils.
# Since the function code is already registered with the decoder factory,
# this will be decoded as a read coil response. If you implement a new 
# method that is not currently implemented, you must register the request
# and response with a ClientDecoder factory.
#---------------------------------------------------------------------------# 
class CustomModbusRequest(ModbusRequest):

    function_code = 1

    def __init__(self, address):
        ModbusRequest.__init__(self)
        self.address = address
        self.count = 16

    def encode(self):
        return struct.pack('>HH', self.address, self.count)

    def decode(self, data):
        self.address, self.count = struct.unpack('>HH', data)

    def execute(self, context):
        if not (1 <= self.count <= 0x7d0):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, self.count):
            return self.doException(merror.IllegalAddress)
        values = context.getValues(self.function_code, self.address, self.count)
        return CustomModbusResponse(values)

#---------------------------------------------------------------------------# 
# This could also have been defined as
#---------------------------------------------------------------------------# 
from pymodbus.bit_read_message import ReadCoilsRequest

class Read16CoilsRequest(ReadCoilsRequest):

    def __init__(self, address):
        ''' Initializes a new instance

        :param address: The address to start reading from
        '''
        ReadCoilsRequest.__init__(self, address, 16)

#---------------------------------------------------------------------------# 
# execute the request with your client
#---------------------------------------------------------------------------# 
# using the with context, the client will automatically be connected
# and closed when it leaves the current scope.
#---------------------------------------------------------------------------# 
with ModbusClient('127.0.0.1') as client:
    request = CustomModbusRequest(0)
    result  = client.execute(request)
    print result


########NEW FILE########
__FILENAME__ = modbus-logging
#!/usr/bin/env python
'''
Pymodbus Logging Examples
--------------------------------------------------------------------------
'''
import logging
import logging.handlers as Handlers

#---------------------------------------------------------------------------# 
# This will simply send everything logged to console
#---------------------------------------------------------------------------# 
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# This will send the error messages in the specified namespace to a file.
# The available namespaces in pymodbus are as follows:
#---------------------------------------------------------------------------# 
# * pymodbus.*          - The root namespace
# * pymodbus.server.*   - all logging messages involving the modbus server
# * pymodbus.client.*   - all logging messages involving the client
# * pymodbus.protocol.* - all logging messages inside the protocol layer
#---------------------------------------------------------------------------# 
logging.basicConfig()
log = logging.getLogger('pymodbus.server')
log.setLevel(logging.ERROR)

#---------------------------------------------------------------------------# 
# This will send the error messages to the specified handlers:
# * docs.python.org/library/logging.html
#---------------------------------------------------------------------------# 
log = logging.getLogger('pymodbus')
log.setLevel(logging.ERROR)
handlers = [
    Handlers.RotatingFileHandler("logfile", maxBytes=1024*1024),
    Handlers.SMTPHandler("mx.host.com", "pymodbus@host.com", ["support@host.com"], "Pymodbus"),
    Handlers.SysLogHandler(facility="daemon"),
    Handlers.DatagramHandler('localhost', 12345),
] 
[log.addHandler(h) for h in handlers]

########NEW FILE########
__FILENAME__ = modbus-payload
#!/usr/bin/env python
'''
Pymodbus Payload Building/Decoding Example
--------------------------------------------------------------------------
'''
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.payload import BinaryPayloadBuilder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

#---------------------------------------------------------------------------# 
# We are going to use a simple client to send our requests
#---------------------------------------------------------------------------# 
client = ModbusClient('127.0.0.1')
client.connect()

#---------------------------------------------------------------------------# 
# If you need to build a complex message to send, you can use the payload
# builder to simplify the packing logic.
#
# Here we demonstrate packing a random payload layout, unpacked it looks
# like the following:
#
# - a 8 byte string 'abcdefgh'
# - a 32 bit float 22.34
# - a 16 bit unsigned int 0x1234
# - an 8 bit int 0x12
# - an 8 bit bitstring [0,1,0,1,1,0,1,0]
#---------------------------------------------------------------------------# 
builder = BinaryPayloadBuilder(endian=Endian.Little)
builder.add_string('abcdefgh')
builder.add_32bit_float(22.34)
builder.add_16bit_uint(0x1234)
builder.add_8bit_int(0x12)
builder.add_bits([0,1,0,1,1,0,1,0])
payload = builder.build()
address = 0x01
result  = client.write_registers(address, payload, skip_encode=True)

#---------------------------------------------------------------------------# 
# If you need to decode a collection of registers in a weird layout, the
# payload decoder can help you as well.
#
# Here we demonstrate decoding a random register layout, unpacked it looks
# like the following:
#
# - a 8 byte string 'abcdefgh'
# - a 32 bit float 22.34
# - a 16 bit unsigned int 0x1234
# - an 8 bit int 0x12
# - an 8 bit bitstring [0,1,0,1,1,0,1,0]
#---------------------------------------------------------------------------# 
address = 0x01
count   = 8
result  = client.read_input_registers(address, count)
decoder = BinaryPayloadDecoder.fromRegisters(result.registers, endian=Endian.Little)
decoded = {
    'string': decoder.decode_string(8),
    'float': decoder.decode_32bit_float(),
    '16uint': decoder.decode_16bit_uint(),
    '8int': decoder.decode_8bit_int(),
    'bits': decoder.decode_bits(),
}

print "-" * 60
print "Decoded Data"
print "-" * 60
for name, value in decoded.iteritems():
    print ("%s\t" % name), value

#---------------------------------------------------------------------------# 
# close the client
#---------------------------------------------------------------------------# 
client.close()

########NEW FILE########
__FILENAME__ = performance
#!/usr/bin/env python
'''
Pymodbus Performance Example
--------------------------------------------------------------------------

The following is an quick performance check of the synchronous
modbus client.
'''
#---------------------------------------------------------------------------# 
# import the necessary modules
#---------------------------------------------------------------------------# 
import logging, os
from time import time
from multiprocessing import log_to_stderr
from pymodbus.client.sync import ModbusTcpClient

#---------------------------------------------------------------------------# 
# choose between threads or processes
#---------------------------------------------------------------------------# 
#from multiprocessing import Process as Worker
from threading import Thread as Worker

#---------------------------------------------------------------------------# 
# initialize the test
#---------------------------------------------------------------------------# 
# Modify the parameters below to control how we are testing the client:
#
# * workers - the number of workers to use at once
# * cycles  - the total number of requests to send
# * host    - the host to send the requests to
#---------------------------------------------------------------------------# 
workers = 1
cycles  = 10000
host    = '127.0.0.1'


#---------------------------------------------------------------------------# 
# perform the test
#---------------------------------------------------------------------------# 
# This test is written such that it can be used by many threads of processes
# although it should be noted that there are performance penalties
# associated with each strategy.
#---------------------------------------------------------------------------# 
def single_client_test(host, cycles):
    ''' Performs a single threaded test of a synchronous
    client against the specified host

    :param host: The host to connect to
    :param cycles: The number of iterations to perform
    '''
    logger = log_to_stderr()
    logger.setLevel(logging.DEBUG)
    logger.debug("starting worker: %d" % os.getpid())

    try:
        count  = 0
        client = ModbusTcpClient(host)
        while count < cycles:
            result = client.read_holding_registers(10, 1).getRegister(0)
            count += 1
    except: logger.exception("failed to run test successfully")
    logger.debug("finished worker: %d" % os.getpid())

#---------------------------------------------------------------------------# 
# run our test and check results
#---------------------------------------------------------------------------# 
# We shard the total number of requests to perform between the number of
# threads that was specified. We then start all the threads and block on
# them to finish. This may need to switch to another mechanism to signal
# finished as the process/thread start up/shut down may skew the test a bit.
#---------------------------------------------------------------------------# 
args  = (host, int(cycles * 1.0 / workers))
procs = [Worker(target=single_client_test, args=args) for _ in range(workers)]
start = time()
any(p.start() for p in procs)   # start the workers
any(p.join()  for p in procs)   # wait for the workers to finish
stop  = time()
print "%d requests/second" % ((1.0 * cycles) / (stop - start))

########NEW FILE########
__FILENAME__ = synchronous-client-ext
#!/usr/bin/env python
'''
Pymodbus Synchronous Client Extended Examples
--------------------------------------------------------------------------

The following is an example of how to use the synchronous modbus client
implementation from pymodbus to perform the extended portions of the
modbus protocol.
'''
#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
#from pymodbus.client.sync import ModbusUdpClient as ModbusClient
#from pymodbus.client.sync import ModbusSerialClient as ModbusClient

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# choose the client you want
#---------------------------------------------------------------------------# 
# make sure to start an implementation to hit against. For this
# you can use an existing device, the reference implementation in the tools
# directory, or start a pymodbus server.
#
# It should be noted that you can supply an ipv4 or an ipv6 host address for
# both the UDP and TCP clients.
#---------------------------------------------------------------------------# 
client = ModbusClient('127.0.0.1')
client.connect()

#---------------------------------------------------------------------------# 
# import the extended messages to perform
#---------------------------------------------------------------------------# 
from pymodbus.diag_message import *
from pymodbus.file_message import *
from pymodbus.other_message import *
from pymodbus.mei_message import *

#---------------------------------------------------------------------------# 
# extra requests
#---------------------------------------------------------------------------# 
# If you are performing a request that is not available in the client
# mixin, you have to perform the request like this instead::
#
# from pymodbus.diag_message import ClearCountersRequest
# from pymodbus.diag_message import ClearCountersResponse
#
# request  = ClearCountersRequest()
# response = client.execute(request)
# if isinstance(response, ClearCountersResponse):
#     ... do something with the response
#
#
# What follows is a listing of all the supported methods. Feel free to
# comment, uncomment, or modify each result set to match with your reference.
#---------------------------------------------------------------------------# 

#---------------------------------------------------------------------------# 
# information requests
#---------------------------------------------------------------------------# 
rq = ReadDeviceInformationRequest()
rr = client.execute(rq)
#assert(rr == None)                             # not supported by reference
assert(rr.function_code < 0x80)                 # test that we are not an error
assert(rr.information[0] == 'proconX Pty Ltd')  # test the vendor name
assert(rr.information[1] == 'FT-MBSV')          # test the product code
assert(rr.information[2] == 'EXPERIMENTAL')     # test the code revision

rq = ReportSlaveIdRequest()
rr = client.execute(rq)
assert(rr == None)                              # not supported by reference
#assert(rr.function_code < 0x80)                # test that we are not an error
#assert(rr.identifier  == 0x00)                 # test the slave identifier
#assert(rr.status  == 0x00)                     # test that the status is ok

rq = ReadExceptionStatusRequest()
rr = client.execute(rq)
#assert(rr == None)                             # not supported by reference
assert(rr.function_code < 0x80)                 # test that we are not an error
assert(rr.status == 0x55)                       # test the status code

rq = GetCommEventCounterRequest()
rr = client.execute(rq)
assert(rr == None)                              # not supported by reference
#assert(rr.function_code < 0x80)                # test that we are not an error
#assert(rr.status == True)                      # test the status code
#assert(rr.count == 0x00)                       # test the status code

rq = GetCommEventLogRequest()
rr = client.execute(rq)
#assert(rr == None)                             # not supported by reference
#assert(rr.function_code < 0x80)                # test that we are not an error
#assert(rr.status == True)                      # test the status code
#assert(rr.event_count == 0x00)                 # test the number of events
#assert(rr.message_count == 0x00)               # test the number of messages
#assert(len(rr.events) == 0x00)                 # test the number of events

#---------------------------------------------------------------------------# 
# diagnostic requests
#---------------------------------------------------------------------------# 
rq = ReturnQueryDataRequest()
rr = client.execute(rq)
assert(rr == None)                             # not supported by reference
#assert(rr.message[0] == 0x0000)               # test the resulting message

rq = RestartCommunicationsOptionRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference
#assert(rr.message == 0x0000)                  # test the resulting message

rq = ReturnDiagnosticRegisterRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ChangeAsciiInputDelimiterRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ForceListenOnlyModeRequest()
client.execute(rq)                             # does not send a response

rq = ClearCountersRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ReturnBusCommunicationErrorCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ReturnBusExceptionErrorCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ReturnSlaveMessageCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ReturnSlaveNoResponseCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ReturnSlaveNAKCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ReturnSlaveBusyCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ReturnSlaveBusCharacterOverrunCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ReturnIopOverrunCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = ClearOverrunCountRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

rq = GetClearModbusPlusRequest()
rr = client.execute(rq)
#assert(rr == None)                            # not supported by reference

#---------------------------------------------------------------------------# 
# close the client
#---------------------------------------------------------------------------# 
client.close()

########NEW FILE########
__FILENAME__ = synchronous-client
#!/usr/bin/env python
'''
Pymodbus Synchronous Client Examples
--------------------------------------------------------------------------

The following is an example of how to use the synchronous modbus client
implementation from pymodbus.

It should be noted that the client can also be used with
the guard construct that is available in python 2.5 and up::

    with ModbusClient('127.0.0.1') as client:
        result = client.read_coils(1,10)
        print result
'''
#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
#from pymodbus.client.sync import ModbusUdpClient as ModbusClient
#from pymodbus.client.sync import ModbusSerialClient as ModbusClient

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# choose the client you want
#---------------------------------------------------------------------------# 
# make sure to start an implementation to hit against. For this
# you can use an existing device, the reference implementation in the tools
# directory, or start a pymodbus server.
#
# If you use the UDP or TCP clients, you can override the framer being used
# to use a custom implementation (say RTU over TCP). By default they use the
# socket framer::
#
#    client = ModbusClient('localhost', port=5020, framer=ModbusRtuFramer)
#
# It should be noted that you can supply an ipv4 or an ipv6 host address for
# both the UDP and TCP clients.
#
# There are also other options that can be set on the client that controls
# how transactions are performed. The current ones are:
#
# * retries - Specify how many retries to allow per transaction (default = 3)
# * retry_on_empty - Is an empty response a retry (default = False)
# * source_address - Specifies the TCP source address to bind to
#
# Here is an example of using these options::
#
#    client = ModbusClient('localhost', retries=3, retry_on_empty=True)
#---------------------------------------------------------------------------# 
client = ModbusClient('localhost', port=502)
#client = ModbusClient(method='ascii', port='/dev/pts/2', timeout=1)
#client = ModbusClient(method='rtu', port='/dev/pts/2', timeout=1)
client.connect()

#---------------------------------------------------------------------------# 
# example requests
#---------------------------------------------------------------------------# 
# simply call the methods that you would like to use. An example session
# is displayed below along with some assert checks. Note that some modbus
# implementations differentiate holding/input discrete/coils and as such
# you will not be able to write to these, therefore the starting values
# are not known to these tests. Furthermore, some use the same memory
# blocks for the two sets, so a change to one is a change to the other.
# Keep both of these cases in mind when testing as the following will
# _only_ pass with the supplied async modbus server (script supplied).
#---------------------------------------------------------------------------# 
rq = client.write_coil(1, True)
rr = client.read_coils(1,1)
assert(rq.function_code < 0x80)     # test that we are not an error
assert(rr.bits[0] == True)          # test the expected value

rq = client.write_coils(1, [True]*8)
rr = client.read_coils(1,8)
assert(rq.function_code < 0x80)     # test that we are not an error
assert(rr.bits == [True]*8)         # test the expected value

rq = client.write_coils(1, [False]*8)
rr = client.read_discrete_inputs(1,8)
assert(rq.function_code < 0x80)     # test that we are not an error
assert(rr.bits == [False]*8)         # test the expected value

rq = client.write_register(1, 10)
rr = client.read_holding_registers(1,1)
assert(rq.function_code < 0x80)     # test that we are not an error
assert(rr.registers[0] == 10)       # test the expected value

rq = client.write_registers(1, [10]*8)
rr = client.read_input_registers(1,8)
assert(rq.function_code < 0x80)     # test that we are not an error
assert(rr.registers == [10]*8)      # test the expected value

arguments = {
    'read_address':    1,
    'read_count':      8,
    'write_address':   1,
    'write_registers': [20]*8,
}
rq = client.readwrite_registers(**arguments)
rr = client.read_input_registers(1,8)
assert(rq.function_code < 0x80)     # test that we are not an error
assert(rq.registers == [20]*8)      # test the expected value
assert(rr.registers == [20]*8)      # test the expected value

#---------------------------------------------------------------------------# 
# close the client
#---------------------------------------------------------------------------# 
client.close()

########NEW FILE########
__FILENAME__ = synchronous-server
#!/usr/bin/env python
'''
Pymodbus Synchronous Server Example
--------------------------------------------------------------------------

The synchronous server is implemented in pure python without any third
party libraries (unless you need to use the serial protocols which require
pyserial). This is helpful in constrained or old environments where using
twisted just is not feasable. What follows is an examle of its use:
'''
#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus.server.sync import StartTcpServer
from pymodbus.server.sync import StartUdpServer
from pymodbus.server.sync import StartSerialServer

from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

#---------------------------------------------------------------------------# 
# configure the service logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# initialize your data store
#---------------------------------------------------------------------------# 
# The datastores only respond to the addresses that they are initialized to.
# Therefore, if you initialize a DataBlock to addresses of 0x00 to 0xFF, a
# request to 0x100 will respond with an invalid address exception. This is
# because many devices exhibit this kind of behavior (but not all)::
#
#     block = ModbusSequentialDataBlock(0x00, [0]*0xff)
#
# Continuing, you can choose to use a sequential or a sparse DataBlock in
# your data context.  The difference is that the sequential has no gaps in
# the data while the sparse can. Once again, there are devices that exhibit
# both forms of behavior::
#
#     block = ModbusSparseDataBlock({0x00: 0, 0x05: 1})
#     block = ModbusSequentialDataBlock(0x00, [0]*5)
#
# Alternately, you can use the factory methods to initialize the DataBlocks
# or simply do not pass them to have them initialized to 0x00 on the full
# address range::
#
#     store = ModbusSlaveContext(di = ModbusSequentialDataBlock.create())
#     store = ModbusSlaveContext()
#
# Finally, you are allowed to use the same DataBlock reference for every
# table or you you may use a seperate DataBlock for each table. This depends
# if you would like functions to be able to access and modify the same data
# or not::
#
#     block = ModbusSequentialDataBlock(0x00, [0]*0xff)
#     store = ModbusSlaveContext(di=block, co=block, hr=block, ir=block)
#
# The server then makes use of a server context that allows the server to
# respond with different slave contexts for different unit ids. By default
# it will return the same context for every unit id supplied (broadcast
# mode). However, this can be overloaded by setting the single flag to False
# and then supplying a dictionary of unit id to context mapping::
#
#     slaves  = {
#         0x01: ModbusSlaveContext(...),
#         0x02: ModbusSlaveContext(...),
#         0x03: ModbusSlaveContext(...),
#     }
#     context = ModbusServerContext(slaves=slaves, single=False)
#---------------------------------------------------------------------------# 
store = ModbusSlaveContext(
    di = ModbusSequentialDataBlock(0, [17]*100),
    co = ModbusSequentialDataBlock(0, [17]*100),
    hr = ModbusSequentialDataBlock(0, [17]*100),
    ir = ModbusSequentialDataBlock(0, [17]*100))
context = ModbusServerContext(slaves=store, single=True)

#---------------------------------------------------------------------------# 
# initialize the server information
#---------------------------------------------------------------------------# 
# If you don't set this or any fields, they are defaulted to empty strings.
#---------------------------------------------------------------------------# 
identity = ModbusDeviceIdentification()
identity.VendorName  = 'Pymodbus'
identity.ProductCode = 'PM'
identity.VendorUrl   = 'http://github.com/bashwork/pymodbus/'
identity.ProductName = 'Pymodbus Server'
identity.ModelName   = 'Pymodbus Server'
identity.MajorMinorRevision = '1.0'

#---------------------------------------------------------------------------# 
# run the server you want
#---------------------------------------------------------------------------# 
StartTcpServer(context, identity=identity, address=("localhost", 5020))
#StartUdpServer(context, identity=identity, address=("localhost", 502))
#StartSerialServer(context, identity=identity, port='/dev/pts/3', timeout=1)

########NEW FILE########
__FILENAME__ = updating-server
#!/usr/bin/env python
'''
Pymodbus Server With Updating Thread
--------------------------------------------------------------------------

This is an example of having a background thread updating the
context while the server is operating. This can also be done with
a python thread::

    from threading import Thread

    thread = Thread(target=updating_writer, args=(context,))
    thread.start()
'''
#---------------------------------------------------------------------------# 
# import the modbus libraries we need
#---------------------------------------------------------------------------# 
from pymodbus.server.async import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer

#---------------------------------------------------------------------------# 
# import the twisted libraries we need
#---------------------------------------------------------------------------# 
from twisted.internet.task import LoopingCall

#---------------------------------------------------------------------------# 
# configure the service logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# define your callback process
#---------------------------------------------------------------------------# 
def updating_writer(a):
    ''' A worker process that runs every so often and
    updates live values of the context. It should be noted
    that there is a race condition for the update.

    :param arguments: The input arguments to the call
    '''
    log.debug("updating the context")
    context  = a[0]
    register = 3
    slave_id = 0x00
    address  = 0x10
    values   = context[slave_id].getValues(register, address, count=5)
    values   = [v + 1 for v in values]
    log.debug("new values: " + str(values))
    context[slave_id].setValues(register, address, values)

#---------------------------------------------------------------------------# 
# initialize your data store
#---------------------------------------------------------------------------# 
store = ModbusSlaveContext(
    di = ModbusSequentialDataBlock(0, [17]*100),
    co = ModbusSequentialDataBlock(0, [17]*100),
    hr = ModbusSequentialDataBlock(0, [17]*100),
    ir = ModbusSequentialDataBlock(0, [17]*100))
context = ModbusServerContext(slaves=store, single=True)

#---------------------------------------------------------------------------# 
# initialize the server information
#---------------------------------------------------------------------------# 
identity = ModbusDeviceIdentification()
identity.VendorName  = 'pymodbus'
identity.ProductCode = 'PM'
identity.VendorUrl   = 'http://github.com/bashwork/pymodbus/'
identity.ProductName = 'pymodbus Server'
identity.ModelName   = 'pymodbus Server'
identity.MajorMinorRevision = '1.0'

#---------------------------------------------------------------------------# 
# run the server you want
#---------------------------------------------------------------------------# 
time = 5 # 5 seconds delay
loop = LoopingCall(f=updating_writer, a=(context,))
loop.start(time, now=False) # initially delay by time
StartTcpServer(context, identity=identity, address=("localhost", 5020))

########NEW FILE########
__FILENAME__ = bcd-payload
'''
Modbus BCD Payload Builder
-----------------------------------------------------------

This is an example of building a custom payload builder
that can be used in the pymodbus library. Below is a 
simple binary coded decimal builder and decoder.
'''
from struct import pack, unpack
from pymodbus.constants import Endian
from pymodbus.interfaces import IPayloadBuilder
from pymodbus.utilities import pack_bitstring
from pymodbus.utilities import unpack_bitstring
from pymodbus.exceptions import ParameterException

def convert_to_bcd(decimal):
    ''' Converts a decimal value to a bcd value

    :param value: The decimal value to to pack into bcd
    :returns: The number in bcd form
    '''
    place, bcd = 0, 0
    while decimal > 0:
        nibble = decimal % 10
        bcd += nibble << place
        decimal /= 10
        place += 4
    return bcd


def convert_from_bcd(bcd):
    ''' Converts a bcd value to a decimal value

    :param value: The value to unpack from bcd
    :returns: The number in decimal form
    '''
    place, decimal = 1, 0
    while bcd > 0:
        nibble = bcd & 0xf
        decimal += nibble * place
        bcd >>= 4
        place *= 10
    return decimal

def count_bcd_digits(bcd):
    ''' Count the number of digits in a bcd value

    :param bcd: The bcd number to count the digits of
    :returns: The number of digits in the bcd string
    '''
    count = 0
    while bcd > 0:
        count += 1
        bcd >>= 4
    return count


class BcdPayloadBuilder(IPayloadBuilder):
    '''
    A utility that helps build binary coded decimal payload
    messages to be written with the various modbus messages.
    example::

        builder = BcdPayloadBuilder()
        builder.add_number(1)
        builder.add_number(int(2.234 * 1000))
        payload = builder.build()
    '''

    def __init__(self, payload=None, endian=Endian.Little):
        ''' Initialize a new instance of the payload builder

        :param payload: Raw payload data to initialize with
        :param endian: The endianess of the payload
        '''
        self._payload = payload or []
        self._endian  = endian

    def __str__(self):
        ''' Return the payload buffer as a string

        :returns: The payload buffer as a string
        '''
        return ''.join(self._payload)

    def reset(self):
        ''' Reset the payload buffer
        '''
        self._payload = []

    def build(self):
        ''' Return the payload buffer as a list

        This list is two bytes per element and can
        thus be treated as a list of registers.

        :returns: The payload buffer as a list
        '''
        string = str(self)
        length = len(string)
        string = string + ('\x00' * (length % 2))
        return [string[i:i+2] for i in xrange(0, length, 2)]

    def add_bits(self, values):
        ''' Adds a collection of bits to be encoded

        If these are less than a multiple of eight,
        they will be left padded with 0 bits to make
        it so.

        :param value: The value to add to the buffer
        '''
        value = pack_bitstring(values)
        self._payload.append(value)

    def add_number(self, value, size=None):
        ''' Adds any 8bit numeric type to the buffer

        :param value: The value to add to the buffer
        '''
        encoded = []
        value = convert_to_bcd(value)
        size = size or count_bcd_digits(value)
        while size > 0:
            nibble = value & 0xf
            encoded.append(pack('B', nibble))
            value >>= 4
            size -= 1
        self._payload.extend(encoded)

    def add_string(self, value):
        ''' Adds a string to the buffer

        :param value: The value to add to the buffer
        '''
        self._payload.append(value)


class BcdPayloadDecoder(object):
    '''
    A utility that helps decode binary coded decimal payload
    messages from a modbus reponse message. What follows is
    a simple example::

        decoder = BcdPayloadDecoder(payload)
        first   = decoder.decode_int(2)
        second  = decoder.decode_int(5) / 100
    '''

    def __init__(self, payload):
        ''' Initialize a new payload decoder

        :param payload: The payload to decode with
        '''
        self._payload = payload
        self._pointer = 0x00

    @staticmethod
    def fromRegisters(registers, endian=Endian.Little):
        ''' Initialize a payload decoder with the result of
        reading a collection of registers from a modbus device.

        The registers are treated as a list of 2 byte values.
        We have to do this because of how the data has already
        been decoded by the rest of the library.

        :param registers: The register results to initialize with
        :param endian: The endianess of the payload
        :returns: An initialized PayloadDecoder
        '''
        if isinstance(registers, list): # repack into flat binary
            payload = ''.join(pack('>H', x) for x in registers)
            return BinaryPayloadDecoder(payload, endian)
        raise ParameterException('Invalid collection of registers supplied')

    @staticmethod
    def fromCoils(coils, endian=Endian.Little):
        ''' Initialize a payload decoder with the result of
        reading a collection of coils from a modbus device.

        The coils are treated as a list of bit(boolean) values.

        :param coils: The coil results to initialize with
        :param endian: The endianess of the payload
        :returns: An initialized PayloadDecoder
        '''
        if isinstance(coils, list):
            payload = pack_bitstring(coils)
            return BinaryPayloadDecoder(payload, endian)
        raise ParameterException('Invalid collection of coils supplied')

    def reset(self):
        ''' Reset the decoder pointer back to the start
        '''
        self._pointer = 0x00

    def decode_int(self, size=1):
        ''' Decodes a int or long from the buffer
        '''
        self._pointer += size
        handle = self._payload[self._pointer - size:self._pointer]
        return convert_from_bcd(handle)

    def decode_bits(self):
        ''' Decodes a byte worth of bits from the buffer
        '''
        self._pointer += 1
        handle = self._payload[self._pointer - 1:self._pointer]
        return unpack_bitstring(handle)

    def decode_string(self, size=1):
        ''' Decodes a string from the buffer

        :param size: The size of the string to decode
        '''
        self._pointer += size
        return self._payload[self._pointer - size:self._pointer]


#---------------------------------------------------------------------------#
# Exported Identifiers
#---------------------------------------------------------------------------#
__all__ = ["BcdPayloadBuilder", "BcdPayloadDecoder"]

########NEW FILE########
__FILENAME__ = concurrent-client
#!/usr/bin/env python
'''
Concurrent Modbus Client
---------------------------------------------------------------------------

This is an example of writing a high performance modbus client that allows
a high level of concurrency by using worker threads/processes to handle
writing/reading from one or more client handles at once.
'''
#--------------------------------------------------------------------------#
# import system libraries
#--------------------------------------------------------------------------#
import multiprocessing
import threading
import logging
import time
import itertools
from collections import namedtuple

# we are using the future from the concurrent.futures released with
# python3. Alternatively we will try the backported library::
#   pip install futures
try:
    from concurrent.futures import Future
except ImportError:
    from futures import Future

#--------------------------------------------------------------------------#
# import neccessary modbus libraries
#--------------------------------------------------------------------------#
from pymodbus.client.common import ModbusClientMixin

#--------------------------------------------------------------------------#
# configure the client logging
#--------------------------------------------------------------------------#
import logging
log = logging.getLogger("pymodbus")
log.setLevel(logging.DEBUG)
logging.basicConfig()


#--------------------------------------------------------------------------#
# Initialize out concurrency primitives
#--------------------------------------------------------------------------#
class _Primitives(object):
    ''' This is a helper class used to group the
    threading primitives depending on the type of
    worker situation we want to run (threads or processes).
    '''

    def __init__(self, **kwargs):
        self.queue  = kwargs.get('queue')
        self.event  = kwargs.get('event')
        self.worker = kwargs.get('worker')

    @classmethod
    def create(klass, in_process=False):
        ''' Initialize a new instance of the concurrency
        primitives.

        :param in_process: True for threaded, False for processes
        :returns: An initialized instance of concurrency primitives
        '''
        if in_process:
            from Queue import Queue
            from threading import Thread
            from threading import Event
            return klass(queue=Queue, event=Event, worker=Thread)
        else:
            from multiprocessing import Queue
            from multiprocessing import Event
            from multiprocessing import Process
            return klass(queue=Queue, event=Event, worker=Process)


#--------------------------------------------------------------------------#
# Define our data transfer objects
#--------------------------------------------------------------------------#
# These will be used to serialize state between the various workers.
# We use named tuples here as they are very lightweight while giving us
# all the benefits of classes.
#--------------------------------------------------------------------------#
WorkRequest  = namedtuple('WorkRequest',  'request, work_id')
WorkResponse = namedtuple('WorkResponse', 'is_exception, work_id, response')

#--------------------------------------------------------------------------#
# Define our worker processes
#--------------------------------------------------------------------------#
def _client_worker_process(factory, input_queue, output_queue, is_shutdown):
    ''' This worker process takes input requests, issues them on its
    client handle, and then sends the client response (success or failure)
    to the manager to deliver back to the application.

    It should be noted that there are N of these workers and they can
    be run in process or out of process as all the state serializes.

    :param factory: A client factory used to create a new client
    :param input_queue: The queue to pull new requests to issue
    :param output_queue: The queue to place client responses
    :param is_shutdown: Condition variable marking process shutdown
    '''
    log.info("starting up worker : %s", threading.current_thread())
    client = factory()
    while not is_shutdown.is_set():
        try:
            workitem = input_queue.get(timeout=1)
            log.debug("dequeue worker request: %s", workitem)
            if not workitem: continue
            try:
                log.debug("executing request on thread: %s", workitem)
                result = client.execute(workitem.request)
                output_queue.put(WorkResponse(False, workitem.work_id, result))
            except Exception, exception:
                log.exception("error in worker thread: %s", threading.current_thread())
                output_queue.put(WorkResponse(True, workitem.work_id, exception))
        except Exception, ex: pass
    log.info("request worker shutting down: %s", threading.current_thread())


def _manager_worker_process(output_queue, futures, is_shutdown):
    ''' This worker process manages taking output responses and
    tying them back to the future keyed on the initial transaction id.
    Basically this can be thought of as the delivery worker.

    It should be noted that there are one of these threads and it must
    be an in process thread as the futures will not serialize across
    processes..

    :param output_queue: The queue holding output results to return
    :param futures: The mapping of tid -> future
    :param is_shutdown: Condition variable marking process shutdown
    '''
    log.info("starting up manager worker: %s", threading.current_thread())
    while not is_shutdown.is_set():
        try:
            workitem = output_queue.get()
            future = futures.get(workitem.work_id, None)
            log.debug("dequeue manager response: %s", workitem)
            if not future: continue
            if workitem.is_exception:
                future.set_exception(workitem.response)
            else: future.set_result(workitem.response)
            log.debug("updated future result: %s", future)
            del futures[workitem.work_id]
        except Exception, ex: log.exception("error in manager")
    log.info("manager worker shutting down: %s", threading.current_thread())


#--------------------------------------------------------------------------#
# Define our concurrent client
#--------------------------------------------------------------------------#
class ConcurrentClient(ModbusClientMixin):
    ''' This is a high performance client that can be used
    to read/write a large number of reqeusts at once asyncronously.
    This operates with a backing worker pool of processes or threads
    to achieve its performance.
    '''

    def __init__(self, **kwargs):
        ''' Initialize a new instance of the client
        '''
        worker_count      = kwargs.get('count', multiprocessing.cpu_count())
        self.factory      = kwargs.get('factory')
        primitives        = _Primitives.create(kwargs.get('in_process', False))
        self.is_shutdown  = primitives.event() # condition marking process shutdown
        self.input_queue  = primitives.queue() # input requests to process
        self.output_queue = primitives.queue() # output results to return
        self.futures      = {}                 # mapping of tid -> future
        self.workers      = []                 # handle to our worker threads
        self.counter      = itertools.count()

        # creating the response manager
        self.manager = threading.Thread(target=_manager_worker_process,
            args=(self.output_queue, self.futures, self.is_shutdown))
        self.manager.start()
        self.workers.append(self.manager)

        # creating the request workers
        for i in range(worker_count):
            worker = primitives.worker(target=_client_worker_process,
                args=(self.factory, self.input_queue, self.output_queue, self.is_shutdown))
            worker.start()
            self.workers.append(worker)

    def shutdown(self):
        ''' Shutdown all the workers being used to 
        concurrently process the requests.
        '''
        log.info("stating to shut down workers")
        self.is_shutdown.set()
        self.output_queue.put(WorkResponse(None, None, None)) # to wake up the manager
        for worker in self.workers:
            worker.join()
        log.info("finished shutting down workers")

    def execute(self, request):
        ''' Given a request, enqueue it to be processed
        and then return a future linked to the response
        of the call.

        :param request: The request to execute
        :returns: A future linked to the call's response
        '''
        future, work_id = Future(), self.counter.next()
        self.input_queue.put(WorkRequest(request, work_id))
        self.futures[work_id] = future
        return future

    def execute_silently(self, request):
        ''' Given a write request, enqueue it to
        be processed without worrying about calling the
        application back (fire and forget)

        :param request: The request to execute
        '''
        self.input_queue.put(WorkRequest(request, None))

if __name__ == "__main__":
    from pymodbus.client.sync import ModbusTcpClient

    def client_factory():
        log.debug("creating client for: %s", threading.current_thread())
        client = ModbusTcpClient('127.0.0.1', port=5020)
        client.connect()
        return client

    client = ConcurrentClient(factory = client_factory)
    try:
        log.info("issuing concurrent requests")
        futures = [client.read_coils(i * 8, 8) for i in range(10)]
        log.info("waiting on futures to complete")
        for future in futures:
            log.info("future result: %s", future.result(timeout=1))
    finally: client.shutdown()

########NEW FILE########
__FILENAME__ = database-datastore
import sqlalchemy
import sqlalchemy.types as sqltypes
from sqlalchemy.sql import and_
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql.expression import bindparam

from pymodbus.exceptions import NotImplementedException
from pymodbus.interfaces import IModbusSlaveContext

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging;
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Context
#---------------------------------------------------------------------------#
class DatabaseSlaveContext(IModbusSlaveContext):
    '''
    This creates a modbus data model with each data access
    stored in its own personal block
    '''

    def __init__(self, *args, **kwargs):
        ''' Initializes the datastores

        :param kwargs: Each element is a ModbusDataBlock
        '''
        self.table = kwargs.get('table', 'pymodbus')
        self.database = kwargs.get('database', 'sqlite:///pymodbus.db')
        self.__db_create(self.table, self.database)

    def __str__(self):
        ''' Returns a string representation of the context

        :returns: A string representation of the context
        '''
        return "Modbus Slave Context"

    def reset(self):
        ''' Resets all the datastores to their default values '''
        self._metadata.drop_all()
        self.__db_create(self.table, self.database)
        raise NotImplementedException()  # TODO drop table?

    def validate(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to test
        :returns: True if the request in within range, False otherwise
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("validate[%d] %d:%d" % (fx, address, count))
        return self.__validate(self.decode(fx), address, count)

    def getValues(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("get-values[%d] %d:%d" % (fx, address, count))
        return self.__get(self.decode(fx), address, count)

    def setValues(self, fx, address, values):
        ''' Sets the datastore with the supplied values

        :param fx: The function we are working with
        :param address: The starting address
        :param values: The new values to be set
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("set-values[%d] %d:%d" % (fx, address, len(values)))
        self.__set(self.decode(fx), address, values)

    #--------------------------------------------------------------------------#
    # Sqlite Helper Methods
    #--------------------------------------------------------------------------#
    def __db_create(self, table, database):
        ''' A helper method to initialize the database and handles

        :param table: The table name to create
        :param database: The database uri to use
        '''
        self._engine = sqlalchemy.create_engine(database, echo=False)
        self._metadata = sqlalchemy.MetaData(self._engine)
        self._table = sqlalchemy.Table(table, self._metadata,
            sqlalchemy.Column('type', sqltypes.String(1)),
            sqlalchemy.Column('index', sqltypes.Integer),
            sqlalchemy.Column('value', sqltypes.Integer),
            UniqueConstraint('type', 'index', name='key'))
        self._table.create(checkfirst=True)
        self._connection = self._engine.connect()

    def __get(self, type, offset, count):
        '''

        :param type: The key prefix to use
        :param offset: The address offset to start at
        :param count: The number of bits to read
        :returns: The resulting values
        '''
        query  = self._table.select(and_(
            self._table.c.type == type,
            self._table.c.index >= offset,
            self._table.c.index <= offset + count))
        query = query.order_by(self._table.c.index.asc())
        result = self._connection.execute(query).fetchall()
        return [row.value for row in result]

    def __build_set(self, type, offset, values, p=''):
        ''' A helper method to generate the sql update context

        :param type: The key prefix to use
        :param offset: The address offset to start at
        :param values: The values to set
        '''
        result = []
        for index, value in enumerate(values):
            result.append({
                p + 'type'  : type,
                p + 'index' : offset + index,
                    'value' : value
            })
        return result

    def __set(self, type, offset, values):
        '''

        :param key: The type prefix to use
        :param offset: The address offset to start at
        :param values: The values to set
        '''
        context = self.__build_set(type, offset, values)
        query   = self._table.insert()
        result  = self._connection.execute(query, context)
        return result.rowcount == len(values)

    def __update(self, type, offset, values):
        '''

        :param type: The type prefix to use
        :param offset: The address offset to start at
        :param values: The values to set
        '''
        context = self.__build_set(type, offset, values, p='x_')
        query   = self._table.update().values(name='value')
        query   = query.where(and_(
            self._table.c.type  == bindparam('x_type'),
            self._table.c.index == bindparam('x_index')))
        result  = self._connection.execute(query, context)
        return result.rowcount == len(values)

    def __validate(self, key, offset, count):
        '''
        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param count: The number of bits to read
        :returns: The result of the validation
        '''
        query  = self._table.select(and_(
            self._table.c.type == type,
            self._table.c.index >= offset,
            self._table.c.index <= offset + count))
        result = self._connection.execute(query)
        return result.rowcount == count

########NEW FILE########
__FILENAME__ = message-generator
#!/usr/bin/env python
'''
Modbus Message Generator
--------------------------------------------------------------------------

The following is an example of how to generate example encoded messages
for the supplied modbus format:

* tcp    - `./generate-messages.py -f tcp -m rx -b`
* ascii  - `./generate-messages.py -f ascii -m tx -a`
* rtu    - `./generate-messages.py -f rtu -m rx -b`
* binary - `./generate-messages.py -f binary -m tx -b`
'''
from optparse import OptionParser
#--------------------------------------------------------------------------#
# import all the available framers
#--------------------------------------------------------------------------#
from pymodbus.transaction import ModbusSocketFramer
from pymodbus.transaction import ModbusBinaryFramer
from pymodbus.transaction import ModbusAsciiFramer
from pymodbus.transaction import ModbusRtuFramer
#--------------------------------------------------------------------------#
# import all available messages
#--------------------------------------------------------------------------#
from pymodbus.bit_read_message import *
from pymodbus.bit_write_message import *
from pymodbus.diag_message import *
from pymodbus.file_message import *
from pymodbus.other_message import *
from pymodbus.mei_message import *
from pymodbus.register_read_message import *
from pymodbus.register_write_message import *

#--------------------------------------------------------------------------#
# initialize logging
#--------------------------------------------------------------------------#
import logging
modbus_log = logging.getLogger("pymodbus")


#--------------------------------------------------------------------------#
# enumerate all request messages
#--------------------------------------------------------------------------#
_request_messages = [
    ReadHoldingRegistersRequest,
    ReadDiscreteInputsRequest,
    ReadInputRegistersRequest,
    ReadCoilsRequest,
    WriteMultipleCoilsRequest,
    WriteMultipleRegistersRequest,
    WriteSingleRegisterRequest,
    WriteSingleCoilRequest,
    ReadWriteMultipleRegistersRequest,
    
    ReadExceptionStatusRequest,
    GetCommEventCounterRequest,
    GetCommEventLogRequest,
    ReportSlaveIdRequest,
    
    ReadFileRecordRequest,
    WriteFileRecordRequest,
    MaskWriteRegisterRequest,
    ReadFifoQueueRequest,
    
    ReadDeviceInformationRequest,

    ReturnQueryDataRequest,
    RestartCommunicationsOptionRequest,
    ReturnDiagnosticRegisterRequest,
    ChangeAsciiInputDelimiterRequest,
    ForceListenOnlyModeRequest,
    ClearCountersRequest,
    ReturnBusMessageCountRequest,
    ReturnBusCommunicationErrorCountRequest,
    ReturnBusExceptionErrorCountRequest,
    ReturnSlaveMessageCountRequest,
    ReturnSlaveNoResponseCountRequest,
    ReturnSlaveNAKCountRequest,
    ReturnSlaveBusyCountRequest,
    ReturnSlaveBusCharacterOverrunCountRequest,
    ReturnIopOverrunCountRequest,
    ClearOverrunCountRequest,
    GetClearModbusPlusRequest,
]


#--------------------------------------------------------------------------#
# enumerate all response messages
#--------------------------------------------------------------------------#
_response_messages = [
    ReadHoldingRegistersResponse,
    ReadDiscreteInputsResponse,
    ReadInputRegistersResponse,
    ReadCoilsResponse,
    WriteMultipleCoilsResponse,
    WriteMultipleRegistersResponse,
    WriteSingleRegisterResponse,
    WriteSingleCoilResponse,
    ReadWriteMultipleRegistersResponse,
    
    ReadExceptionStatusResponse,
    GetCommEventCounterResponse,
    GetCommEventLogResponse,
    ReportSlaveIdResponse,

    ReadFileRecordResponse,
    WriteFileRecordResponse,
    MaskWriteRegisterResponse,
    ReadFifoQueueResponse,

    ReadDeviceInformationResponse,

    ReturnQueryDataResponse,
    RestartCommunicationsOptionResponse,
    ReturnDiagnosticRegisterResponse,
    ChangeAsciiInputDelimiterResponse,
    ForceListenOnlyModeResponse,
    ClearCountersResponse,
    ReturnBusMessageCountResponse,
    ReturnBusCommunicationErrorCountResponse,
    ReturnBusExceptionErrorCountResponse,
    ReturnSlaveMessageCountResponse,
    ReturnSlaveNoReponseCountResponse,
    ReturnSlaveNAKCountResponse,
    ReturnSlaveBusyCountResponse,
    ReturnSlaveBusCharacterOverrunCountResponse,
    ReturnIopOverrunCountResponse,
    ClearOverrunCountResponse,
    GetClearModbusPlusResponse,
]


#--------------------------------------------------------------------------#
# build an arguments singleton
#--------------------------------------------------------------------------#
# Feel free to override any values here to generate a specific message
# in question. It should be noted that many argument names are reused
# between different messages, and a number of messages are simply using
# their default values.
#--------------------------------------------------------------------------#
_arguments = {
    'address'           : 0x12,
    'count'             : 0x08,
    'value'             : 0x01,
    'values'            : [0x01] * 8,
    'read_address'      : 0x12,
    'read_count'        : 0x08,
    'write_address  '   : 0x12,
    'write_registers'   : [0x01] * 8,
    'transaction'       : 0x01,
    'protocol'          : 0x00,
    'unit'              : 0x01,
}


#---------------------------------------------------------------------------# 
# generate all the requested messages
#---------------------------------------------------------------------------# 
def generate_messages(framer, options):
    ''' A helper method to parse the command line options

    :param framer: The framer to encode the messages with
    :param options: The message options to use
    '''
    messages = _request_messages if options.messages == 'tx' else _response_messages
    for message in messages:
        message = message(**_arguments)
        print "%-44s = " % message.__class__.__name__,
        packet = framer.buildPacket(message)
        if not options.ascii:
            packet = packet.encode('hex') + '\n'
        print packet,   # because ascii ends with a \r\n


#---------------------------------------------------------------------------# 
# initialize our program settings
#---------------------------------------------------------------------------# 
def get_options():
    ''' A helper method to parse the command line options

    :returns: The options manager
    '''
    parser = OptionParser()

    parser.add_option("-f", "--framer",
        help="The type of framer to use (tcp, rtu, binary, ascii)",
        dest="framer", default="tcp")

    parser.add_option("-D", "--debug",
        help="Enable debug tracing",
        action="store_true", dest="debug", default=False)

    parser.add_option("-a", "--ascii",
        help="The indicates that the message is ascii",
        action="store_true", dest="ascii", default=True)

    parser.add_option("-b", "--binary",
        help="The indicates that the message is binary",
        action="store_false", dest="ascii")

    parser.add_option("-m", "--messages",
        help="The messages to encode (rx, tx)",
        dest="messages", default='rx')

    (opt, arg) = parser.parse_args()
    return opt

def main():
    ''' The main runner function
    '''
    option = get_options()

    if option.debug:
        try:
            modbus_log.setLevel(logging.DEBUG)
    	    logging.basicConfig()
        except Exception, e:
    	    print "Logging is not supported on this system"

    framer = lookup = {
        'tcp':    ModbusSocketFramer,
        'rtu':    ModbusRtuFramer,
        'binary': ModbusBinaryFramer,
        'ascii':  ModbusAsciiFramer,
    }.get(option.framer, ModbusSocketFramer)(None)

    generate_messages(framer, option)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = message-parser
#!/usr/bin/env python
'''
Modbus Message Parser
--------------------------------------------------------------------------

The following is an example of how to parse modbus messages
using the supplied framers for a number of protocols:

* tcp
* ascii
* rtu
* binary
'''
#---------------------------------------------------------------------------# 
# import needed libraries
#---------------------------------------------------------------------------# 
import sys
import collections
import textwrap
from optparse import OptionParser
from pymodbus.utilities import computeCRC, computeLRC
from pymodbus.factory import ClientDecoder, ServerDecoder
from pymodbus.transaction import ModbusSocketFramer
from pymodbus.transaction import ModbusBinaryFramer
from pymodbus.transaction import ModbusAsciiFramer
from pymodbus.transaction import ModbusRtuFramer

#--------------------------------------------------------------------------#
# Logging
#--------------------------------------------------------------------------#
import logging
modbus_log = logging.getLogger("pymodbus")


#---------------------------------------------------------------------------# 
# build a quick wrapper around the framers
#---------------------------------------------------------------------------# 
class Decoder(object):

    def __init__(self, framer, encode=False):
        ''' Initialize a new instance of the decoder

        :param framer: The framer to use
        :param encode: If the message needs to be encoded
        '''
        self.framer = framer
        self.encode = encode

    def decode(self, message):
        ''' Attempt to decode the supplied message

        :param message: The messge to decode
        '''
        value = message if self.encode else message.encode('hex')
        print "="*80
        print "Decoding Message %s" % value
        print "="*80
        decoders = [
            self.framer(ServerDecoder()),
            self.framer(ClientDecoder()),
        ]
        for decoder in decoders:
            print "%s" % decoder.decoder.__class__.__name__
            print "-"*80
            try:
                decoder.addToFrame(message)
                if decoder.checkFrame():
                    decoder.advanceFrame()
                    decoder.processIncomingPacket(message, self.report)
                else: self.check_errors(decoder, message)
            except Exception, ex: self.check_errors(decoder, message)

    def check_errors(self, decoder, message):
        ''' Attempt to find message errors

        :param message: The message to find errors in
        '''
        pass

    def report(self, message):
        ''' The callback to print the message information

        :param message: The message to print
        '''
        print "%-15s = %s" % ('name', message.__class__.__name__)
        for k,v in message.__dict__.iteritems():
            if isinstance(v, dict):
                print "%-15s =" % k
                for kk,vv in v.items():
                    print "  %-12s => %s" % (kk, vv)

            elif isinstance(v, collections.Iterable):
                print "%-15s =" % k
                value = str([int(x) for x  in v])
                for line in textwrap.wrap(value, 60):
                    print "%-15s . %s" % ("", line)
            else: print "%-15s = %s" % (k, hex(v))
        print "%-15s = %s" % ('documentation', message.__doc__)


#---------------------------------------------------------------------------# 
# and decode our message
#---------------------------------------------------------------------------# 
def get_options():
    ''' A helper method to parse the command line options

    :returns: The options manager
    '''
    parser = OptionParser()

    parser.add_option("-p", "--parser",
        help="The type of parser to use (tcp, rtu, binary, ascii)",
        dest="parser", default="tcp")

    parser.add_option("-D", "--debug",
        help="Enable debug tracing",
        action="store_true", dest="debug", default=False)

    parser.add_option("-m", "--message",
        help="The message to parse",
        dest="message", default=None)

    parser.add_option("-a", "--ascii",
        help="The indicates that the message is ascii",
        action="store_true", dest="ascii", default=True)

    parser.add_option("-b", "--binary",
        help="The indicates that the message is binary",
        action="store_false", dest="ascii")

    parser.add_option("-f", "--file",
        help="The file containing messages to parse",
        dest="file", default=None)

    (opt, arg) = parser.parse_args()

    if not opt.message and len(arg) > 0:
        opt.message = arg[0]

    return opt

def get_messages(option):
    ''' A helper method to generate the messages to parse

    :param options: The option manager
    :returns: The message iterator to parse
    '''
    if option.message:
        if not option.ascii:
            option.message = option.message.decode('hex')
        yield option.message
    elif option.file:
        with open(option.file, "r") as handle:
            for line in handle:
                if line.startswith('#'): continue
                if not option.ascii:
                    line = line.strip()
                    line = line.decode('hex')
                yield line

def main():
    ''' The main runner function
    '''
    option = get_options()

    if option.debug:
        try:
            modbus_log.setLevel(logging.DEBUG)
    	    logging.basicConfig()
        except Exception, e:
    	    print "Logging is not supported on this system"

    framer = lookup = {
        'tcp':    ModbusSocketFramer,
        'rtu':    ModbusRtuFramer,
        'binary': ModbusBinaryFramer,
        'ascii':  ModbusAsciiFramer,
    }.get(option.parser, ModbusSocketFramer)

    decoder = Decoder(framer, option.ascii)
    for message in get_messages(option):
        decoder.decode(message)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = modbus-scraper
#!/usr/bin/env python
'''
This is a simple scraper that can be pointed at a
modbus device to pull down all its values and store
them as a collection of sequential data blocks.
'''
import pickle
from optparse import OptionParser
from twisted.internet import serialport, reactor
from twisted.internet.protocol import ClientFactory
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext
from pymodbus.factory import ClientDecoder
from pymodbus.client.async import ModbusClientProtocol

#--------------------------------------------------------------------------#
# Configure the client logging
#--------------------------------------------------------------------------#
import logging
log = logging.getLogger("pymodbus")

#---------------------------------------------------------------------------# 
# Choose the framer you want to use
#---------------------------------------------------------------------------# 
from pymodbus.transaction import ModbusBinaryFramer
from pymodbus.transaction import ModbusAsciiFramer
from pymodbus.transaction import ModbusRtuFramer
from pymodbus.transaction import ModbusSocketFramer

#---------------------------------------------------------------------------# 
# Define some constants
#---------------------------------------------------------------------------# 
COUNT = 8    # The number of bits/registers to read at once
DELAY = 0    # The delay between subsequent reads
SLAVE = 0x01 # The slave unit id to read from

#---------------------------------------------------------------------------# 
# A simple scraper protocol
#---------------------------------------------------------------------------# 
# I tried to spread the load across the device, but feel free to modify the
# logic to suit your own purpose.
#---------------------------------------------------------------------------# 
class ScraperProtocol(ModbusClientProtocol):

    def __init__(self, framer, endpoint):
        ''' Initializes our custom protocol

        :param framer: The decoder to use to process messages
        :param endpoint: The endpoint to send results to
        '''
        ModbusClientProtocol.__init__(self, framer)
        self.endpoint = endpoint

    def connectionMade(self):
        ''' Callback for when the client has connected
        to the remote server.
        '''
        super(ScraperProtocol, self).connectionMade()
        log.debug("Beginning the processing loop")
        self.address  = self.factory.starting
        reactor.callLater(DELAY, self.scrape_holding_registers)

    def connectionLost(self, reason):
        ''' Callback for when the client disconnects from the
        server.

        :param reason: The reason for the disconnection
        '''
        reactor.callLater(DELAY, reactor.stop)

    def scrape_holding_registers(self):
        ''' Defer fetching holding registers
        '''
        log.debug("reading holding registers: %d" % self.address)
        d = self.read_holding_registers(self.address, count=COUNT, unit=SLAVE)
        d.addCallbacks(self.scrape_discrete_inputs, self.error_handler)

    def scrape_discrete_inputs(self, response):
        ''' Defer fetching holding registers
        '''
        log.debug("reading discrete inputs: %d" % self.address)
        self.endpoint.write((3, self.address, response.registers))
        d = self.read_discrete_inputs(self.address, count=COUNT, unit=SLAVE)
        d.addCallbacks(self.scrape_input_registers, self.error_handler)

    def scrape_input_registers(self, response):
        ''' Defer fetching holding registers
        '''
        log.debug("reading discrete inputs: %d" % self.address)
        self.endpoint.write((2, self.address, response.bits))
        d = self.read_input_registers(self.address, count=COUNT, unit=SLAVE)
        d.addCallbacks(self.scrape_coils, self.error_handler)

    def scrape_coils(self, response):
        ''' Write values of holding registers, defer fetching coils

        :param response: The response to process
        '''
        log.debug("reading coils: %d" % self.address)
        self.endpoint.write((4, self.address, response.registers))
        d = self.read_coils(self.address, count=COUNT, unit=SLAVE)
        d.addCallbacks(self.start_next_cycle, self.error_handler)

    def start_next_cycle(self, response):
        ''' Write values of coils, trigger next cycle

        :param response: The response to process
        '''
        log.debug("starting next round: %d" % self.address)
        self.endpoint.write((1, self.address, response.bits))
        self.address += COUNT
        if self.address >= self.factory.ending:
            self.endpoint.finalize()
            self.transport.loseConnection()
        else: reactor.callLater(DELAY, self.scrape_holding_registers)

    def error_handler(self, failure):
        ''' Handle any twisted errors

        :param failure: The error to handle
        '''
        log.error(failure)


#---------------------------------------------------------------------------# 
# a factory for the example protocol
#---------------------------------------------------------------------------# 
# This is used to build client protocol's if you tie into twisted's method
# of processing. It basically produces client instances of the underlying
# protocol::
#
#     Factory(Protocol) -> ProtocolInstance
#
# It also persists data between client instances (think protocol singelton).
#---------------------------------------------------------------------------# 
class ScraperFactory(ClientFactory):

    protocol = ScraperProtocol

    def __init__(self, framer, endpoint, query):
        ''' Remember things necessary for building a protocols '''
        self.framer   = framer
        self.endpoint = endpoint
        self.starting, self.ending = query

    def buildProtocol(self, _):
        ''' Create a protocol and start the reading cycle '''
        protocol = self.protocol(self.framer, self.endpoint)
        protocol.factory = self
        return protocol


#---------------------------------------------------------------------------# 
# a custom client for our device
#---------------------------------------------------------------------------# 
# Twisted provides a number of helper methods for creating and starting
# clients:
# - protocol.ClientCreator
# - reactor.connectTCP
#
# How you start your client is really up to you.
#---------------------------------------------------------------------------# 
class SerialModbusClient(serialport.SerialPort):

    def __init__(self, factory, *args, **kwargs):
        ''' Setup the client and start listening on the serial port

        :param factory: The factory to build clients with
        '''
        protocol = factory.buildProtocol(None)
        self.decoder = ClientDecoder()
        serialport.SerialPort.__init__(self, protocol, *args, **kwargs)


#---------------------------------------------------------------------------# 
# a custom endpoint for our results
#---------------------------------------------------------------------------# 
# An example line reader, this can replace with:
# - the TCP protocol
# - a context recorder
# - a database or file recorder
#---------------------------------------------------------------------------# 
class LoggingContextReader(object):

    def __init__(self, output):
        ''' Initialize a new instance of the logger

        :param output: The output file to save to
        '''
        self.output  = output
        self.context = ModbusSlaveContext(
            di = ModbusSequentialDataBlock.create(),
            co = ModbusSequentialDataBlock.create(),
            hr = ModbusSequentialDataBlock.create(),
            ir = ModbusSequentialDataBlock.create())

    def write(self, response):
        ''' Handle the next modbus response

        :param response: The response to process
        '''
        log.info("Read Data: %s" % str(response))
        fx, address, values = response
        self.context.setValues(fx, address, values)

    def finalize(self):
        with open(self.output, "w") as handle:
            pickle.dump(self.context, handle)


#--------------------------------------------------------------------------#
# Main start point
#--------------------------------------------------------------------------#
def get_options():
    ''' A helper method to parse the command line options

    :returns: The options manager
    '''
    parser = OptionParser()

    parser.add_option("-o", "--output",
        help="The resulting output file for the scrape",
        dest="output", default="datastore.pickle")

    parser.add_option("-p", "--port",
        help="The port to connect to", type='int',
        dest="port", default=502)

    parser.add_option("-s", "--server",
        help="The server to scrape",
        dest="host", default="127.0.0.1")

    parser.add_option("-r", "--range",
        help="The address range to scan",
        dest="query", default="0:1000")

    parser.add_option("-d", "--debug",
        help="Enable debug tracing",
        action="store_true", dest="debug", default=False)

    (opt, arg) = parser.parse_args()
    return opt

def main():    
    ''' The main runner function '''
    options = get_options()

    if options.debug:
        try:
            log.setLevel(logging.DEBUG)
    	    logging.basicConfig()
        except Exception, ex:
    	    print "Logging is not supported on this system"

    # split the query into a starting and ending range
    query = [int(p) for p in options.query.split(':')]

    try:
        log.debug("Initializing the client")
        framer  = ModbusSocketFramer(ClientDecoder())
        reader  = LoggingContextReader(options.output)
        factory = ScraperFactory(framer, reader, query)

        # how to connect based on TCP vs Serial clients
        if isinstance(framer, ModbusSocketFramer):
            reactor.connectTCP(options.host, options.port, factory)
        else: SerialModbusClient(factory, options.port, reactor)

        log.debug("Starting the client")
        reactor.run()
        log.debug("Finished scraping the client")
    except Exception, ex:
        print ex

#---------------------------------------------------------------------------#
# Main jumper
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = modbus-simulator
#!/usr/bin/env python
'''
An example of creating a fully implemented modbus server
with read/write data as well as user configurable base data
'''

import pickle
from optparse import OptionParser
from twisted.internet import reactor

from pymodbus.server.async import StartTcpServer
from pymodbus.datastore import ModbusServerContext,ModbusSlaveContext

#--------------------------------------------------------------------------#
# Logging
#--------------------------------------------------------------------------#
import logging
logging.basicConfig()

server_log   = logging.getLogger("pymodbus.server")
protocol_log = logging.getLogger("pymodbus.protocol")

#---------------------------------------------------------------------------#
# Extra Global Functions
#---------------------------------------------------------------------------#
# These are extra helper functions that don't belong in a class
#---------------------------------------------------------------------------#
import getpass
def root_test():
    ''' Simple test to see if we are running as root '''
    return True # removed for the time being as it isn't portable
    #return getpass.getuser() == "root"

#--------------------------------------------------------------------------#
# Helper Classes
#--------------------------------------------------------------------------#
class ConfigurationException(Exception):
    ''' Exception for configuration error '''

    def __init__(self, string):
        ''' Initializes the ConfigurationException instance

        :param string: The message to append to the exception
        '''
        Exception.__init__(self, string)
        self.string = string

    def __str__(self):
        ''' Builds a representation of the object

        :returns: A string representation of the object
        '''
        return 'Configuration Error: %s' % self.string

class Configuration:
    '''
    Class used to parse configuration file and create and modbus
    datastore.

    The format of the configuration file is actually just a
    python pickle, which is a compressed memory dump from
    the scraper.
    '''

    def __init__(self, config):
        '''
        Trys to load a configuration file, lets the file not
        found exception fall through

        :param config: The pickled datastore
        '''
        try:
            self.file = open(config, "r")
        except Exception:
            raise ConfigurationException("File not found %s" % config)

    def parse(self):
        ''' Parses the config file and creates a server context
        '''
        handle = pickle.load(self.file)
        try: # test for existance, or bomb
            dsd = handle['di']
            csd = handle['ci']
            hsd = handle['hr']
            isd = handle['ir']
        except Exception:
            raise ConfigurationException("Invalid Configuration")
        slave = ModbusSlaveContext(d=dsd, c=csd, h=hsd, i=isd)
        return ModbusServerContext(slaves=slave)

#--------------------------------------------------------------------------#
# Main start point
#--------------------------------------------------------------------------#
def main():
    ''' Server launcher '''
    parser = OptionParser()
    parser.add_option("-c", "--conf",
                    help="The configuration file to load",
                    dest="file")
    parser.add_option("-D", "--debug",
                    help="Turn on to enable tracing",
                    action="store_true", dest="debug", default=False)
    (opt, arg) = parser.parse_args()

    # enable debugging information
    if opt.debug:
        try:
            server_log.setLevel(logging.DEBUG)
            protocol_log.setLevel(logging.DEBUG)
        except Exception, e:
    	    print "Logging is not supported on this system"

    # parse configuration file and run
    try:
        conf = Configuration(opt.file)
        StartTcpServer(context=conf.parse())
    except ConfigurationException, err:
        print err
        parser.print_help()

#---------------------------------------------------------------------------#
# Main jumper
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    if root_test():
        main()
    else: print "This script must be run as root!"


########NEW FILE########
__FILENAME__ = modbus_mapper
'''
Given a modbus mapping file, this is used to generate
decoder blocks so that non-programmers can define the
register values and then decode a modbus device all
without having to write a line of code for decoding.

Currently supported formats are:

* csv
* json
* xml

Here is an example of generating and using a mapping decoder
(note that this is still in the works and will be greatly
simplified in the final api; it is just an example of the
requested functionality)::

    from modbus_mapper import csv_mapping_parser
    from modbus_mapper import mapping_decoder
    from pymodbus.client.sync import ModbusTcpClient
    from pymodbus.payload import BinaryModbusDecoder

    template = ['address', 'size', 'function', 'name', 'description']
    raw_mapping = csv_mapping_parser('input.csv', template)
    mapping = mapping_decoder(raw_mapping)
    
    index, size = 1, 100
    client = ModbusTcpClient('localhost')
    response = client.read_holding_registers(index, size)
    decoder = BinaryModbusDecoder.fromRegisters(response.registers)
    while index < size:
        print "[{}]\t{}".format(i, mapping[i]['type'](decoder))
        index += mapping[i]['size']

Also, using the same input mapping parsers, we can generate
populated slave contexts that can be run behing a modbus server::

    from modbus_mapper import csv_mapping_parser
    from modbus_mapper import modbus_context_decoder
    from pymodbus.client.ssync import StartTcpServer
    from pymodbus.datastore.context import ModbusServerContext

    template = ['address', 'value', 'function', 'name', 'description']
    raw_mapping = csv_mapping_parser('input.csv', template)
    slave_context = modbus_context_decoder(raw_mapping)
    context = ModbusServerContext(slaves=slave_context, single=True)
    StartTcpServer(context)
'''
import csv
import json
from collections import defaultdict
from StringIO import StringIO
from tokenize import generate_tokens
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.datastore.store import ModbusSparseDataBlock
from pymodbus.datastore.context import ModbusSlaveContext


#---------------------------------------------------------------------------# 
# raw mapping input parsers
#---------------------------------------------------------------------------# 
# These generate the raw mapping_blocks from some form of input
# which can then be passed to the decoder in question to supply
# the requested output result.
#---------------------------------------------------------------------------# 
def csv_mapping_parser(path, template):
    ''' Given a csv file of the the mapping data for
    a modbus device, return a mapping layout that can
    be used to decode an new block.

    .. note:: For the template, a few values are required
    to be defined: address, size, function, and type. All the remaining
    values will be stored, but not formatted by the application.
    So for example::

        template = ['address', 'type', 'size', 'name', 'function']
        mappings = json_mapping_parser('mapping.json', template)

    :param path: The path to the csv input file
    :param template: The row value template
    :returns: The decoded csv dictionary
    '''
    mapping_blocks = defaultdict(dict)
    with open(path, 'r') as handle:
        reader = csv.reader(handle)
        reader.next() # skip the csv header
        for row in reader:
            mapping = dict(zip(template, row))
            fid = mapping.pop('function')
            aid = int(mapping['address'])
            mapping_blocks[aid] = mapping
    return mapping_blocks


def json_mapping_parser(path, template):
    ''' Given a json file of the the mapping data for
    a modbus device, return a mapping layout that can
    be used to decode an new block.

    .. note:: For the template, a few values are required
    to be mapped: address, size, and type. All the remaining
    values will be stored, but not formatted by the application.
    So for example::

        template = {
            'Start': 'address',
            'DataType': 'type',
            'Length': 'size'
            # the remaining keys will just pass through
        }
        mappings = json_mapping_parser('mapping.json', template)

    :param path: The path to the csv input file
    :param template: The row value template
    :returns: The decoded csv dictionary
    '''
    mapping_blocks = {}
    with open(path, 'r') as handle:
        for tid, rows in json.load(handle).iteritems():
            mappings = {}
            for key, values in rows.iteritems():
                mapping = {template.get(k, k) : v for k, v in values.iteritems()}
                mappings[int(key)] = mapping
            mapping_blocks[tid] = mappings
    return mapping_blocks


def xml_mapping_parser(path):
    ''' Given an xml file of the the mapping data for
    a modbus device, return a mapping layout that can
    be used to decode an new block.

    .. note:: The input of the xml file is defined as
    follows::

    :param path: The path to the xml input file
    :returns: The decoded csv dictionary
    '''
    pass


#---------------------------------------------------------------------------# 
# modbus context decoders
#---------------------------------------------------------------------------# 
# These are used to decode a raw mapping_block into a slave context with
# populated function data blocks.
#---------------------------------------------------------------------------# 
def modbus_context_decoder(mapping_blocks):
    ''' Given a mapping block input, generate a backing
    slave context with initialized data blocks.

    .. note:: This expects the following for each block:
    address, value, and function where function is one of
    di (discretes), co (coils), hr (holding registers), or
    ir (input registers).

    :param mapping_blocks: The mapping blocks
    :returns: The initialized modbus slave context
    '''
    blocks = defaultdict(dict)
    for block in mapping_blocks.itervalues():
        for mapping in block.itervalues():
            value    = int(mapping['value'])
            address  = int(mapping['address'])
            function = mapping['function']
            blocks[function][address] = value
    return ModbusSlaveContext(**blocks)


#---------------------------------------------------------------------------# 
# modbus mapping decoder
#---------------------------------------------------------------------------# 
# These are used to decode a raw mapping_block into a request decoder.
# So this allows one to simply grab a number of registers, and then
# pass them to this decoder which will do the rest.
#---------------------------------------------------------------------------# 
class ModbusTypeDecoder(object):
    ''' This is a utility to determine the correct
    decoder to use given a type name. By default this
    supports all the types available in the default modbus
    decoder, however this can easily be extended this class
    and adding new types to the mapper::

        class CustomTypeDecoder(ModbusTypeDecoder):
            def __init__(self):
                ModbusTypeDecode.__init__(self)
                self.mapper['type-token'] = self.callback

            def parse_my_bitfield(self, tokens):
                return lambda d: d.decode_my_type()

    '''
    def __init__(self):
        ''' Initializes a new instance of the decoder
        '''
        self.default = lambda m: self.parse_16bit_uint
        self.parsers = {
            'uint':    self.parse_16bit_uint,
            'uint8':   self.parse_8bit_uint,
            'uint16':  self.parse_16bit_uint,
            'uint32':  self.parse_32bit_uint,
            'uint64':  self.parse_64bit_uint,
            'int':     self.parse_16bit_int,
            'int8':    self.parse_8bit_int,
            'int16':   self.parse_16bit_int,
            'int32':   self.parse_32bit_int,
            'int64':   self.parse_64bit_int,
            'float':   self.parse_32bit_float,
            'float32': self.parse_32bit_float,
            'float64': self.parse_64bit_float,
            'string':  self.parse_32bit_int,
            'bits':    self.parse_bits,
        }

    #------------------------------------------------------------
    # Type parsers
    #------------------------------------------------------------
    def parse_string(self, tokens):
        _ = tokens.next()
        size = int(tokens.next())
        return lambda d: d.decode_string(size=size)

    def parse_bits(self, tokens):
        return lambda d: d.decode_bits()

    def parse_8bit_uint(self, tokens):
        return lambda d: d.decode_8bit_uint()

    def parse_16bit_uint(self, tokens):
        return lambda d: d.decode_16bit_uint()

    def parse_32bit_uint(self, tokens):
        return lambda d: d.decode_32bit_uint()

    def parse_64bit_uint(self, tokens):
        return lambda d: d.decode_64bit_uint()

    def parse_8bit_int(self, tokens):
        return lambda d: d.decode_8bit_int()

    def parse_16bit_int(self, tokens):
        return lambda d: d.decode_16bit_int()

    def parse_32bit_int(self, tokens):
        return lambda d: d.decode_32bit_int()

    def parse_64bit_int(self, tokens):
        return lambda d: d.decode_64bit_int()

    def parse_32bit_float(self, tokens):
        return lambda d: d.decode_32bit_float()

    def parse_64bit_float(self, tokens):
        return lambda d: d.decode_64bit_float()

    #------------------------------------------------------------
    # Public Interface
    #------------------------------------------------------------
    def tokenize(self, value):
        ''' Given a value, return the tokens
    
        :param value: The value to tokenize
        :returns: A token generator
        '''
        tokens = generate_tokens(StringIO(value).readline)
        for toknum, tokval, _, _, _ in tokens:
            yield tokval

    def parse(self, value):
        ''' Given a type value, return a function
        that supplied with a decoder, will decode
        the correct value.

        :param value: The type of value to parse
        :returns: The decoder method to use
        '''
        tokens = self.tokenize(value)
        token  = tokens.next().lower()
        parser = self.parsers.get(token, self.default)
        return parser(tokens)


def mapping_decoder(mapping_blocks, decoder=None):
    ''' Given the raw mapping blocks, convert
    them into modbus value decoder map.

    :param mapping_blocks: The mapping blocks
    :param decoder: The type decoder to use
    '''
    decoder = decoder or ModbusTypeDecoder()
    for block in mapping_blocks.itervalues():
        for mapping in block.itervalues():
            mapping['address'] = int(mapping['address'])
            mapping['size']    = int(mapping['size'])
            mapping['type']    = decoder.parse(mapping['type'])



########NEW FILE########
__FILENAME__ = modbus_saver
'''
These are a collection of helper methods that can be
used to save a modbus server context to file for backup,
checkpointing, or any other purpose. There use is very
simple::

    context = server.context
    saver   = JsonDatastoreSaver(context)
    saver.save()

These can then be re-opened by the parsers in the
modbus_mapping module. At the moment, the supported
output formats are:

* csv
* json
* xml

To implement your own, simply subclass ModbusDatastoreSaver
and supply the needed callbacks for your given format:

* handle_store_start(self, store)
* handle_store_end(self, store)
* handle_slave_start(self, slave)
* handle_slave_end(self, slave)
* handle_save_start(self)
* handle_save_end(self)
'''
import csv
import json
import xml.etree.ElementTree as xml


class ModbusDatastoreSaver(object):
    ''' An abstract base class that can be used to implement
    a persistance format for the modbus server context. In
    order to use it, just complete the neccessary callbacks
    (SAX style) that your persistance format needs.
    '''

    def __init__(self, context, path=None):
        ''' Initialize a new instance of the saver.

        :param context: The modbus server context
        :param path: The output path to save to
        '''
        self.context = context
        self.path = path or 'modbus-context-dump'

    def save(self):
        ''' The main runner method to save the
        context to file which calls the various
        callbacks which the sub classes will
        implement.
        '''
        with open(self.path, 'w') as self.file_handle:
            self.handle_save_start()
            for slave_name, slave in self.context:
                self.handle_slave_start(slave_name)
                for store_name, store in slave.store.iteritems():
                    self.handle_store_start(store_name)
                    self.handle_store_values(iter(store))
                    self.handle_store_end(store_name)
                self.handle_slave_end(slave_name)
            self.handle_save_end()

    #------------------------------------------------------------
    # predefined state machine callbacks
    #------------------------------------------------------------
    def handle_save_start(self): pass
    def handle_store_start(self, store): pass
    def handle_store_end(self, store): pass
    def handle_slave_start(self, slave): pass
    def handle_slave_end(self, slave): pass
    def handle_save_end(self): pass


#----------------------------------------------------------------
# Implementations of the data store savers
#----------------------------------------------------------------
class JsonDatastoreSaver(ModbusDatastoreSaver):
    ''' An implementation of the modbus datastore saver
    that persists the context as a json document.
    '''

    STORE_NAMES = {
        'i' : 'input-registers',
        'd' : 'discretes',
        'h' : 'holding-registers',
        'c' : 'coils',
    }

    def handle_save_start(self):
        self._context = dict()
    def handle_slave_start(self, slave):
        self._context[hex(slave)] = self._slave = dict()
    def handle_store_start(self, store):
        self._store = self.STORE_NAMES[store]
    def handle_store_values(self, values):
        self._slave[self._store] = dict(values)
    def handle_save_end(self):
        json.dump(self._context, self.file_handle)


class CsvDatastoreSaver(ModbusDatastoreSaver):
    ''' An implementation of the modbus datastore saver
    that persists the context as a csv document.
    '''
    NEWLINE = '\r\n'
    HEADER = "slave,store,address,value" + NEWLINE
    STORE_NAMES = {
        'i' : 'i',
        'd' : 'd',
        'h' : 'h',
        'c' : 'c',
    }

    def handle_save_start(self):
        self.file_handle.write(self.HEADER)
    def handle_slave_start(self, slave):
        self._line = [str(slave)]
    def handle_store_start(self, store):
        self._line.append(self.STORE_NAMES[store])
    def handle_store_values(self, values):
        self.file_handle.writelines(self.handle_store_value(values))
    def handle_store_end(self, store):
        self._line.pop()
    def handle_store_value(self, values):
        for a, v in values:
            yield ','.join(self._line + [str(a), str(v)]) + self.NEWLINE


class XmlDatastoreSaver(ModbusDatastoreSaver):
    ''' An implementation of the modbus datastore saver
    that persists the context as a XML document.
    '''
    STORE_NAMES = {
        'i' : 'input-registers',
        'd' : 'discretes',
        'h' : 'holding-registers',
        'c' : 'coils',
    }

    def handle_save_start(self):
        self._context = xml.Element("context")
        self._root = xml.ElementTree(self._context)
    def handle_slave_start(self, slave):
        self._slave = xml.SubElement(self._context, "slave")
        self._slave.set("id", str(slave))
    def handle_store_start(self, store):
        self._store = xml.SubElement(self._slave, "store")
        self._store.set("function", self.STORE_NAMES[store])
    def handle_store_values(self, values):
        for address, value in values:
            entry = xml.SubElement(self._store, "entry")
            entry.text = str(value)
            entry.set("address", str(address))
    def handle_save_end(self):
        self._root.write(self.file_handle)

########NEW FILE########
__FILENAME__ = modicon-payload
'''
Modbus Modicon Payload Builder
-----------------------------------------------------------

This is an example of building a custom payload builder
that can be used in the pymodbus library. Below is a 
simple modicon encoded builder and decoder.
'''
from struct import pack, unpack
from pymodbus.constants import Endian
from pymodbus.interfaces import IPayloadBuilder
from pymodbus.utilities import pack_bitstring
from pymodbus.utilities import unpack_bitstring
from pymodbus.exceptions import ParameterException


class ModiconPayloadBuilder(IPayloadBuilder):
    '''
    A utility that helps build modicon encoded payload
    messages to be written with the various modbus messages.
    example::

        builder = ModiconPayloadBuilder()
        builder.add_8bit_uint(1)
        builder.add_16bit_uint(2)
        payload = builder.build()
    '''

    def __init__(self, payload=None, endian=Endian.Little):
        ''' Initialize a new instance of the payload builder

        :param payload: Raw payload data to initialize with
        :param endian: The endianess of the payload
        '''
        self._payload = payload or []
        self._endian  = endian

    def __str__(self):
        ''' Return the payload buffer as a string

        :returns: The payload buffer as a string
        '''
        return ''.join(self._payload)

    def reset(self):
        ''' Reset the payload buffer
        '''
        self._payload = []

    def build(self):
        ''' Return the payload buffer as a list

        This list is two bytes per element and can
        thus be treated as a list of registers.

        :returns: The payload buffer as a list
        '''
        string = str(self)
        length = len(string)
        string = string + ('\x00' * (length % 2))
        return [string[i:i+2] for i in xrange(0, length, 2)]

    def add_bits(self, values):
        ''' Adds a collection of bits to be encoded

        If these are less than a multiple of eight,
        they will be left padded with 0 bits to make
        it so.

        :param value: The value to add to the buffer
        '''
        value = pack_bitstring(values)
        self._payload.append(value)

    def add_8bit_uint(self, value):
        ''' Adds a 8 bit unsigned int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'B'
        self._payload.append(pack(fstring, value))

    def add_16bit_uint(self, value):
        ''' Adds a 16 bit unsigned int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'H'
        self._payload.append(pack(fstring, value))

    def add_32bit_uint(self, value):
        ''' Adds a 32 bit unsigned int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'I'
        handle = pack(fstring, value)
        handle = handle[2:] + handle[:2]
        self._payload.append(handle)

    def add_8bit_int(self, value):
        ''' Adds a 8 bit signed int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'b'
        self._payload.append(pack(fstring, value))

    def add_16bit_int(self, value):
        ''' Adds a 16 bit signed int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'h'
        self._payload.append(pack(fstring, value))

    def add_32bit_int(self, value):
        ''' Adds a 32 bit signed int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'i'
        handle = pack(fstring, value)
        handle = handle[2:] + handle[:2]
        self._payload.append(handle)

    def add_32bit_float(self, value):
        ''' Adds a 32 bit float to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'f'
        handle = pack(fstring, value)
        handle = handle[2:] + handle[:2]
        self._payload.append(handle)

    def add_string(self, value):
        ''' Adds a string to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 's'
        for c in value:
            self._payload.append(pack(fstring, c))


class ModiconPayloadDecoder(object):
    '''
    A utility that helps decode modicon encoded payload
    messages from a modbus reponse message. What follows is
    a simple example::

        decoder = ModiconPayloadDecoder(payload)
        first   = decoder.decode_8bit_uint()
        second  = decoder.decode_16bit_uint()
    '''

    def __init__(self, payload):
        ''' Initialize a new payload decoder

        :param payload: The payload to decode with
        '''
        self._payload = payload
        self._pointer = 0x00

    @staticmethod
    def fromRegisters(registers, endian=Endian.Little):
        ''' Initialize a payload decoder with the result of
        reading a collection of registers from a modbus device.

        The registers are treated as a list of 2 byte values.
        We have to do this because of how the data has already
        been decoded by the rest of the library.

        :param registers: The register results to initialize with
        :param endian: The endianess of the payload
        :returns: An initialized PayloadDecoder
        '''
        if isinstance(registers, list): # repack into flat binary
            payload = ''.join(pack('>H', x) for x in registers)
            return ModiconPayloadDecoder(payload, endian)
        raise ParameterException('Invalid collection of registers supplied')

    @staticmethod
    def fromCoils(coils, endian=Endian.Little):
        ''' Initialize a payload decoder with the result of
        reading a collection of coils from a modbus device.

        The coils are treated as a list of bit(boolean) values.

        :param coils: The coil results to initialize with
        :param endian: The endianess of the payload
        :returns: An initialized PayloadDecoder
        '''
        if isinstance(coils, list):
            payload = pack_bitstring(coils)
            return ModiconPayloadDecoder(payload, endian)
        raise ParameterException('Invalid collection of coils supplied')

    def reset(self):
        ''' Reset the decoder pointer back to the start
        '''
        self._pointer = 0x00

    def decode_8bit_uint(self):
        ''' Decodes a 8 bit unsigned int from the buffer
        '''
        self._pointer += 1
        fstring = self._endian + 'B'
        handle = self._payload[self._pointer - 1:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_16bit_uint(self):
        ''' Decodes a 16 bit unsigned int from the buffer
        '''
        self._pointer += 2
        fstring = self._endian + 'H'
        handle = self._payload[self._pointer - 2:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_32bit_uint(self):
        ''' Decodes a 32 bit unsigned int from the buffer
        '''
        self._pointer += 4
        fstring = self._endian + 'I'
        handle = self._payload[self._pointer - 4:self._pointer]
        handle = handle[2:] + handle[:2]
        return unpack(fstring, handle)[0]

    def decode_8bit_int(self):
        ''' Decodes a 8 bit signed int from the buffer
        '''
        self._pointer += 1
        fstring = self._endian + 'b'
        handle = self._payload[self._pointer - 1:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_16bit_int(self):
        ''' Decodes a 16 bit signed int from the buffer
        '''
        self._pointer += 2
        fstring = self._endian + 'h'
        handle = self._payload[self._pointer - 2:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_32bit_int(self):
        ''' Decodes a 32 bit signed int from the buffer
        '''
        self._pointer += 4
        fstring = self._endian + 'i'
        handle = self._payload[self._pointer - 4:self._pointer]
        handle = handle[2:] + handle[:2]
        return unpack(fstring, handle)[0]

    def decode_32bit_float(self, size=1):
        ''' Decodes a float from the buffer
        '''
        self._pointer += 4
        fstring = self._endian + 'f'
        handle = self._payload[self._pointer - 4:self._pointer]
        handle = handle[2:] + handle[:2]
        return unpack(fstring, handle)[0]

    def decode_bits(self):
        ''' Decodes a byte worth of bits from the buffer
        '''
        self._pointer += 1
        handle = self._payload[self._pointer - 1:self._pointer]
        return unpack_bitstring(handle)

    def decode_string(self, size=1):
        ''' Decodes a string from the buffer

        :param size: The size of the string to decode
        '''
        self._pointer += size
        return self._payload[self._pointer - size:self._pointer]


#---------------------------------------------------------------------------#
# Exported Identifiers
#---------------------------------------------------------------------------#
__all__ = ["BcdPayloadBuilder", "BcdPayloadDecoder"]

########NEW FILE########
__FILENAME__ = redis-datastore
import redis
from pymodbus.interfaces import IModbusSlaveContext
from pymodbus.utilities import pack_bitstring, unpack_bitstring

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging;
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Context
#---------------------------------------------------------------------------#
class RedisSlaveContext(IModbusSlaveContext):
    '''
    This is a modbus slave context using redis as a backing
    store.
    '''

    def __init__(self, **kwargs):
        ''' Initializes the datastores

        :param host: The host to connect to
        :param port: The port to connect to
        :param prefix: A prefix for the keys
        '''
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 6379)
        self.prefix = kwargs.get('prefix', 'pymodbus')
        self.client = kwargs.get('client', redis.Redis(host=host, port=port))
        self.__build_mapping()

    def __str__(self):
        ''' Returns a string representation of the context

        :returns: A string representation of the context
        '''
        return "Redis Slave Context %s" % self.client

    def reset(self):
        ''' Resets all the datastores to their default values '''
        self.client.flushall()

    def validate(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to test
        :returns: True if the request in within range, False otherwise
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("validate[%d] %d:%d" % (fx, address, count))
        return self.__val_callbacks[self.decode(fx)](address, count)

    def getValues(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("getValues[%d] %d:%d" % (fx, address, count))
        return self.__get_callbacks[self.decode(fx)](address, count)

    def setValues(self, fx, address, values):
        ''' Sets the datastore with the supplied values

        :param fx: The function we are working with
        :param address: The starting address
        :param values: The new values to be set
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("setValues[%d] %d:%d" % (fx, address, len(values)))
        self.__set_callbacks[self.decode(fx)](address, values)

    #--------------------------------------------------------------------------#
    # Redis Helper Methods
    #--------------------------------------------------------------------------#
    def __get_prefix(self, key):
        ''' This is a helper to abstract getting bit values

        :param key: The key prefix to use
        :returns: The key prefix to redis
        '''
        return "%s:%s" % (self.prefix, key)

    def __build_mapping(self):
        '''
        A quick helper method to build the function
        code mapper.
        '''
        self.__val_callbacks = {
            'd' : lambda o, c: self.__val_bit('d', o, c),
            'c' : lambda o, c: self.__val_bit('c', o, c),
            'h' : lambda o, c: self.__val_reg('h', o, c),
            'i' : lambda o, c: self.__val_reg('i', o, c),
        }
        self.__get_callbacks = {
            'd' : lambda o, c: self.__get_bit('d', o, c),
            'c' : lambda o, c: self.__get_bit('c', o, c),
            'h' : lambda o, c: self.__get_reg('h', o, c),
            'i' : lambda o, c: self.__get_reg('i', o, c),
        }
        self.__set_callbacks = {
            'd' : lambda o, v: self.__set_bit('d', o, v),
            'c' : lambda o, v: self.__set_bit('c', o, v),
            'h' : lambda o, v: self.__set_reg('h', o, v),
            'i' : lambda o, v: self.__set_reg('i', o, v),
        }

    #--------------------------------------------------------------------------#
    # Redis discrete implementation
    #--------------------------------------------------------------------------#
    __bit_size    = 16
    __bit_default = '\x00' * (__bit_size % 8)

    def __get_bit_values(self, key, offset, count):
        ''' This is a helper to abstract getting bit values

        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param count: The number of bits to read
        '''
        key = self.__get_prefix(key)
        s = divmod(offset, self.__bit_size)[0]
        e = divmod(offset + count, self.__bit_size)[0]

        request  = ('%s:%s' % (key, v) for v in range(s, e + 1))
        response = self.client.mget(request)
        return response

    def __val_bit(self, key, offset, count):
        ''' Validates that the given range is currently set in redis.
        If any of the keys return None, then it is invalid.

        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param count: The number of bits to read
        '''
        response = self.__get_bit_values(key, offset, count)
        return None not in response

    def __get_bit(self, key, offset, count):
        '''

        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param count: The number of bits to read
        '''
        response = self.__get_bit_values(key, offset, count)
        response = (r or self.__bit_default for r in response)
        result = ''.join(response)
        result = unpack_bitstring(result)
        return result[offset:offset + count]

    def __set_bit(self, key, offset, values):
        '''

        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param values: The values to set
        '''
        count = len(values)
        s = divmod(offset, self.__bit_size)[0]
        e = divmod(offset + count, self.__bit_size)[0]
        value = pack_bitstring(values)

        current = self.__get_bit_values(key, offset, count)
        current = (r or self.__bit_default for r in current)
        current = ''.join(current)
        current = current[0:offset] + value + current[offset + count:]
        final   = (current[s:s + self.__bit_size] for s in range(0, count, self.__bit_size))

        key = self.__get_prefix(key)
        request = ('%s:%s' % (key, v) for v in range(s, e + 1))
        request = dict(zip(request, final))
        self.client.mset(request)

    #--------------------------------------------------------------------------#
    # Redis register implementation
    #--------------------------------------------------------------------------#
    __reg_size    = 16
    __reg_default = '\x00' * (__reg_size % 8)

    def __get_reg_values(self, key, offset, count):
        ''' This is a helper to abstract getting register values

        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param count: The number of bits to read
        '''
        key = self.__get_prefix(key)
        #s = divmod(offset, self.__reg_size)[0]
        #e = divmod(offset+count, self.__reg_size)[0]

        #request  = ('%s:%s' % (key, v) for v in range(s, e + 1))
        request  = ('%s:%s' % (key, v) for v in range(offset, count + 1))
        response = self.client.mget(request)
        return response

    def __val_reg(self, key, offset, count):
        ''' Validates that the given range is currently set in redis.
        If any of the keys return None, then it is invalid.

        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param count: The number of bits to read
        '''
        response = self.__get_reg_values(key, offset, count)
        return None not in response

    def __get_reg(self, key, offset, count):
        '''

        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param count: The number of bits to read
        '''
        response = self.__get_reg_values(key, offset, count)
        response = [r or self.__reg_default for r in response]
        return response[offset:offset + count]

    def __set_reg(self, key, offset, values):
        '''

        :param key: The key prefix to use
        :param offset: The address offset to start at
        :param values: The values to set
        '''
        count = len(values)
        #s = divmod(offset, self.__reg_size)
        #e = divmod(offset+count, self.__reg_size)

        #current = self.__get_reg_values(key, offset, count)

        key = self.__get_prefix(key)
        request = ('%s:%s' % (key, v) for v in range(offset, count + 1))
        request = dict(zip(request, values))
        self.client.mset(request)

########NEW FILE########
__FILENAME__ = serial-forwarder
#!/usr/bin/env python
'''
Pymodbus Synchronous Serial Forwarder
--------------------------------------------------------------------------

We basically set the context for the tcp serial server to be that of a
serial client! This is just an example of how clever you can be with
the data context (basically anything can become a modbus device).
'''
#---------------------------------------------------------------------------# 
# import the various server implementations
#---------------------------------------------------------------------------# 
from pymodbus.server.sync import StartTcpServer as StartServer
from pymodbus.client.sync import ModbusSerialClient as ModbusClient

from pymodbus.datastore.remote import RemoteSlaveContext
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

#---------------------------------------------------------------------------# 
# configure the service logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# initialize the datastore(serial client)
#---------------------------------------------------------------------------# 
client = ModbusClient(method='ascii', port='/dev/pts/14')
store = RemoteSlaveContext(client)
context = ModbusServerContext(slaves=store, single=True)

#---------------------------------------------------------------------------# 
# run the server you want
#---------------------------------------------------------------------------# 
StartServer(context)

########NEW FILE########
__FILENAME__ = sunspec_client
from pymodbus.constants import Endian
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from twisted.internet.defer import Deferred


#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
logging.basicConfig()


#---------------------------------------------------------------------------# 
# Sunspec Common Constants
#---------------------------------------------------------------------------# 
class SunspecDefaultValue(object):
    ''' A collection of constants to indicate if
    a value is not implemented.
    '''
    Signed16        = 0x8000
    Unsigned16      = 0xffff
    Accumulator16   = 0x0000
    Scale           = 0x8000
    Signed32        = 0x80000000
    Float32         = 0x7fc00000
    Unsigned32      = 0xffffffff
    Accumulator32   = 0x00000000
    Signed64        = 0x8000000000000000
    Unsigned64      = 0xffffffffffffffff
    Accumulator64   = 0x0000000000000000
    String          = '\x00'


class SunspecStatus(object):
    ''' Indicators of the current status of a
    sunspec device
    '''
    Normal  = 0x00000000
    Error   = 0xfffffffe
    Unknown = 0xffffffff


class SunspecIdentifier(object):
    ''' Assigned identifiers that are pre-assigned
    by the sunspec protocol.
    '''
    Sunspec = 0x53756e53


class SunspecModel(object):
    ''' Assigned device indentifiers that are pre-assigned
    by the sunspec protocol.
    '''
    #---------------------------------------------
    # 0xx Common Models
    #---------------------------------------------
    CommonBlock                              = 1
    AggregatorBlock                          = 2

    #---------------------------------------------
    # 1xx Inverter Models
    #---------------------------------------------
    SinglePhaseIntegerInverter               = 101
    SplitPhaseIntegerInverter                = 102
    ThreePhaseIntegerInverter                = 103
    SinglePhaseFloatsInverter                = 103
    SplitPhaseFloatsInverter                 = 102
    ThreePhaseFloatsInverter                 = 103

    #---------------------------------------------
    # 2xx Meter Models
    #---------------------------------------------
    SinglePhaseMeter                         = 201
    SplitPhaseMeter                          = 201
    WyeConnectMeter                          = 201
    DeltaConnectMeter                        = 201

    #---------------------------------------------
    # 3xx Environmental Models
    #---------------------------------------------
    BaseMeteorological                       = 301
    Irradiance                               = 302
    BackOfModuleTemperature                  = 303
    Inclinometer                             = 304
    Location                                 = 305
    ReferencePoint                           = 306
    BaseMeteorological                       = 307
    MiniMeteorological                       = 308

    #---------------------------------------------
    # 4xx String Combiner Models             
    #---------------------------------------------
    BasicStringCombiner                      = 401
    AdvancedStringCombiner                   = 402

    #---------------------------------------------
    # 5xx Panel Models
    #---------------------------------------------
    PanelFloat                               = 501
    PanelInteger                             = 502

    #---------------------------------------------
    # 641xx Outback Blocks
    #---------------------------------------------
    OutbackDeviceIdentifier                  = 64110
    OutbackChargeController                  = 64111
    OutbackFMSeriesChargeController          = 64112
    OutbackFXInverterRealTime                = 64113
    OutbackFXInverterConfiguration           = 64114
    OutbackSplitPhaseRadianInverter          = 64115
    OutbackRadianInverterConfiguration       = 64116
    OutbackSinglePhaseRadianInverterRealTime = 64117
    OutbackFLEXNetDCRealTime                 = 64118
    OutbackFLEXNetDCConfiguration            = 64119
    OutbackSystemControl                     = 64120

    #---------------------------------------------
    # 64xxx Vender Extension Block
    #---------------------------------------------
    EndOfSunSpecMap                          = 65535

    @classmethod
    def lookup(klass, code):
        ''' Given a device identifier, return the
        device model name for that identifier

        :param code: The device code to lookup
        :returns: The device model name, or None if none available
        '''
        values = dict((v, k) for k, v in klass.__dict__.iteritems()
            if not callable(v))
        return values.get(code, None)


class SunspecOffsets(object):
    ''' Well known offsets that are used throughout
    the sunspec protocol
    '''
    CommonBlock             = 40000
    CommonBlockLength       = 69
    AlternateCommonBlock    = 50000


#---------------------------------------------------------------------------# 
# Common Functions
#---------------------------------------------------------------------------# 
def defer_or_apply(func):
    ''' Decorator to apply an adapter method
    to a result regardless if it is a deferred
    or a concrete response.

    :param func: The function to decorate
    '''
    def closure(future, adapt):
        if isinstance(defer, Deferred):
            d = Deferred()
            future.addCallback(lambda r: d.callback(adapt(r)))
            return d
        return adapt(future)
    return closure


def create_sunspec_sync_client(host):
    ''' A quick helper method to create a sunspec
    client.

    :param host: The host to connect to
    :returns: an initialized SunspecClient
    '''
    modbus = ModbusTcpClient(host)
    modbus.connect()
    client = SunspecClient(modbus)
    client.initialize()
    return client


#---------------------------------------------------------------------------# 
# Sunspec Client
#---------------------------------------------------------------------------# 
class SunspecDecoder(BinaryPayloadDecoder):
    ''' A decoder that deals correctly with the sunspec
    binary format.
    '''

    def __init__(self, payload, endian):
        ''' Initialize a new instance of the SunspecDecoder

        .. note:: This is always set to big endian byte order
        as specified in the protocol.
        '''
        endian = Endian.Big
        BinaryPayloadDecoder.__init__(self, payload, endian)

    def decode_string(self, size=1):
        ''' Decodes a string from the buffer

        :param size: The size of the string to decode
        '''
        self._pointer += size
        string = self._payload[self._pointer - size:self._pointer]
        return string.split(SunspecDefaultValue.String)[0]


class SunspecClient(object):

    def __init__(self, client):
        ''' Initialize a new instance of the client

        :param client: The modbus client to use
        '''
        self.client = client
        self.offset = SunspecOffsets.CommonBlock

    def initialize(self):
        ''' Initialize the underlying client values

        :returns: True if successful, false otherwise
        '''
        decoder  = self.get_device_block(self.offset, 2)
        if decoder.decode_32bit_uint() == SunspecIdentifier.Sunspec:
            return True
        self.offset = SunspecOffsets.AlternateCommonBlock
        decoder  = self.get_device_block(self.offset, 2)
        return decoder.decode_32bit_uint() == SunspecIdentifier.Sunspec

    def get_common_block(self):
        ''' Read and return the sunspec common information
        block.

        :returns: A dictionary of the common block information
        '''
        length  = SunspecOffsets.CommonBlockLength
        decoder = self.get_device_block(self.offset, length)
        return {
            'SunSpec_ID':       decoder.decode_32bit_uint(),
            'SunSpec_DID':      decoder.decode_16bit_uint(),
            'SunSpec_Length':   decoder.decode_16bit_uint(),
            'Manufacturer':     decoder.decode_string(size=32),
            'Model':            decoder.decode_string(size=32),
            'Options':          decoder.decode_string(size=16),
            'Version':          decoder.decode_string(size=16),
            'SerialNumber':     decoder.decode_string(size=32),
            'DeviceAddress':    decoder.decode_16bit_uint(),
            'Next_DID':         decoder.decode_16bit_uint(),
            'Next_DID_Length':  decoder.decode_16bit_uint(),
        }

    def get_device_block(self, offset, size):
        ''' A helper method to retrieve the next device block

        .. note:: We will read 2 more registers so that we have
        the information for the next block.

        :param offset: The offset to start reading at
        :param size: The size of the offset to read
        :returns: An initialized decoder for that result
        '''
        _logger.debug("reading device block[{}..{}]".format(offset, offset + size))
        response = self.client.read_holding_registers(offset, size + 2)
        return SunspecDecoder.fromRegisters(response.registers)

    def get_all_device_blocks(self):
        ''' Retrieve all the available blocks in the supplied
        sunspec device.

        .. note:: Since we do not know how to decode the available
        blocks, this returns a list of dictionaries of the form:

            decoder: the-binary-decoder,
            model:   the-model-identifier (name)

        :returns: A list of the available blocks
        '''
        blocks = []
        offset = self.offset + 2
        model  = SunspecModel.CommonBlock
        while model != SunspecModel.EndOfSunSpecMap:
            decoder = self.get_device_block(offset, 2)
            model   = decoder.decode_16bit_uint()
            length  = decoder.decode_16bit_uint()
            blocks.append({
                'model' : model,
                'name'  : SunspecModel.lookup(model),
                'length': length,
                'offset': offset + length + 2
            })
            offset += length + 2
        return blocks


#------------------------------------------------------------
# A quick test runner
#------------------------------------------------------------
if __name__ == "__main__":
    client = create_sunspec_sync_client("YOUR.HOST.GOES.HERE")

    # print out all the device common block
    common = client.get_common_block()
    for key, value in common.iteritems():
        if key == "SunSpec_DID":
            value = SunspecModel.lookup(value)
        print "{:<20}: {}".format(key, value)

    # print out all the available device blocks
    blocks = client.get_all_device_blocks()
    for block in blocks:
        print block

    client.client.close()


########NEW FILE########
__FILENAME__ = thread_safe_datastore
import threading
from contextlib import contextmanager
from pymodbus.datastore.store import BaseModbusDataBlock


class ContextWrapper(object):
    ''' This is a simple wrapper around enter
    and exit functions that conforms to the pyhton
    context manager protocol:

    with ContextWrapper(enter, leave):
        do_something()
    '''

    def __init__(self, enter=None, leave=None, factory=None):
        self._enter = enter
        self._leave = leave
        self._factory = factory

    def __enter__(self):
        if self.enter: self._enter()
        return self if not self._factory else self._factory()

    def __exit__(self, args):
        if self._leave: self._leave()


class ReadWriteLock(object):
    ''' This reader writer lock gurantees write order, but not
    read order and is generally biased towards allowing writes
    if they are available to prevent starvation.

    TODO:

    * allow user to choose between read/write/random biasing
    - currently write biased
    - read biased allow N readers in queue
    - random is 50/50 choice of next
    '''

    def __init__(self):
        ''' Initializes a new instance of the ReadWriteLock
        '''
        self.queue   = []                                  # the current writer queue
        self.lock    = threading.Lock()                    # the underlying condition lock
        self.read_condition = threading.Condition(self.lock) # the single reader condition
        self.readers = 0                                   # the number of current readers
        self.writer  = False                               # is there a current writer

    def __is_pending_writer(self):
        return (self.writer                                # if there is a current writer
            or (self.queue                                 # or if there is a waiting writer
           and (self.queue[0] != self.read_condition)))    # or if the queue head is not a reader

    def acquire_reader(self):
        ''' Notifies the lock that a new reader is requesting
        the underlying resource.
        '''
        with self.lock:
            if self.__is_pending_writer():                 # if there are existing writers waiting
                if self.read_condition not in self.queue:  # do not pollute the queue with readers
                    self.queue.append(self.read_condition) # add the readers in line for the queue
                while self.__is_pending_writer():          # until the current writer is finished
                    self.read_condition.wait(1)            # wait on our condition
                if self.queue and self.read_condition == self.queue[0]: # if the read condition is at the queue head
                    self.queue.pop(0)                      # then go ahead and remove it
            self.readers += 1                              # update the current number of readers

    def acquire_writer(self):
        ''' Notifies the lock that a new writer is requesting
        the underlying resource.
        '''
        with self.lock:
            if self.writer or self.readers:                # if we need to wait on a writer or readers
                condition = threading.Condition(self.lock) # create a condition just for this writer
                self.queue.append(condition)               # and put it on the waiting queue
                while self.writer or self.readers:         # until the write lock is free
                    condition.wait(1)                      # wait on our condition
                self.queue.pop(0)                          # remove our condition after our condition is met
            self.writer = True                             # stop other writers from operating

    def release_reader(self):
        ''' Notifies the lock that an existing reader is
        finished with the underlying resource.
        '''
        with self.lock:
            self.readers = max(0, self.readers - 1)        # readers should never go below 0
            if not self.readers and self.queue:            # if there are no active readers
                self.queue[0].notify_all()                 # then notify any waiting writers

    def release_writer(self):
        ''' Notifies the lock that an existing writer is
        finished with the underlying resource.
        '''
        with self.lock:
            self.writer = False                            # give up current writing handle
            if self.queue:                                 # if someone is waiting in the queue
                self.queue[0].notify_all()                 # wake them up first
            else: self.read_condition.notify_all()         # otherwise wake up all possible readers

    @contextmanager
    def get_reader_lock(self):
        ''' Wrap some code with a reader lock using the
        python context manager protocol::

            with rwlock.get_reader_lock():
                do_read_operation()
        '''
        try:
            self.acquire_reader()
            yield self
        finally: self.release_reader()

    @contextmanager
    def get_writer_lock(self):
        ''' Wrap some code with a writer lock using the
        python context manager protocol::

            with rwlock.get_writer_lock():
                do_read_operation()
        '''
        try:
            self.acquire_writer()
            yield self
        finally: self.release_writer()


class ThreadSafeDataBlock(BaseModbusDataBlock):
    ''' This is a simple decorator for a data block. This allows
    a user to inject an existing data block which can then be
    safely operated on from multiple cocurrent threads.

    It should be noted that the choice was made to lock around the
    datablock instead of the manager as there is less source of 
    contention (writes can occur to slave 0x01 while reads can
    occur to slave 0x02).
    '''

    def __init__(self, block):
        ''' Initialize a new thread safe decorator

        :param block: The block to decorate
        '''
        self.rwlock = ReadWriteLock()
        self.block  = block

    def validate(self, address, count=1):
        ''' Checks to see if the request is in range

        :param address: The starting address
        :param count: The number of values to test for
        :returns: True if the request in within range, False otherwise
        '''
        with self.rwlock.get_reader_lock():
            return self.block.validate(address, count)

    def getValues(self, address, count=1):
        ''' Returns the requested values of the datastore

        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        with self.rwlock.get_reader_lock():
            return self.block.getValues(address, count)
 
    def setValues(self, address, values):
        ''' Sets the requested values of the datastore

        :param address: The starting address
        :param values: The new values to be set
        '''
        with self.rwlock.get_writer_lock():
            return self.block.setValues(address, values)


if __name__ == "__main__":

    class AtomicCounter(object):
        def __init__(self, **kwargs):
            self.counter = kwargs.get('start', 0)
            self.finish  = kwargs.get('finish', 1000)
            self.lock    = threading.Lock()

        def increment(self, count=1):
            with self.lock:
                self.counter += count

        def is_running(self):
            return self.counter <= self.finish

    locker = ReadWriteLock()
    readers, writers = AtomicCounter(), AtomicCounter()

    def read():
        while writers.is_running() and readers.is_running():
            with locker.get_reader_lock():
                readers.increment()

    def write():
        while writers.is_running() and readers.is_running():
            with locker.get_writer_lock():
                writers.increment()

    rthreads = [threading.Thread(target=read)  for i in range(50)]
    wthreads = [threading.Thread(target=write) for i in range(2)]
    for t in rthreads + wthreads: t.start()
    for t in rthreads + wthreads: t.join()
    print "readers[%d] writers[%d]" % (readers.counter, writers.counter) 

########NEW FILE########
__FILENAME__ = asynchronous-ascii-client
#!/usr/bin/env python
import unittest
from pymodbus.client.async import ModbusSerialClient as ModbusClient
from base_runner import Runner

class AsynchronousAsciiClient(Runner, unittest.TestCase):
    '''
    These are the integration tests for the asynchronous
    serial ascii client.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        super(Runner, self).setUp()
        self.client = ModbusClient(method='ascii')

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.client.close()
        self.shutdown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = asynchronous-rtu-client
#!/usr/bin/env python
import unittest
from pymodbus.client.async import ModbusSerialClient as ModbusClient
from base_runner import Runner

class AsynchronousRtuClient(Runner, unittest.TestCase):
    '''
    These are the integration tests for the asynchronous
    serial rtu client.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        super(Runner, self).setUp()
        self.client = ModbusClient(method='rtu')

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.client.close()
        super(Runner, self).tearDown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = asynchronous-tcp-client
#!/usr/bin/env python
import unittest
from twisted.internet import reactor, protocol
from pymodbus.constants import Defaults
from pymodbus.client.async import ModbusClientProtocol
from base_runner import Runner

class AsynchronousTcpClient(Runner, unittest.TestCase):
    '''
    These are the integration tests for the asynchronous
    tcp client.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        def _callback(client): self.client = client
        self.initialize(["../tools/reference/diagslave", "-m", "tcp", "-p", "12345"])
        defer = protocol.ClientCreator(reactor, ModbusClientProtocol
                ).connectTCP("localhost", Defaults.Port)
        defer.addCallback(_callback)
        reactor.run()

    def tearDown(self):
        ''' Cleans up the test environment '''
        reactor.callLater(1, client.transport.loseConnection)
        reactor.callLater(2, reactor.stop)
        reactor.shutdown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = asynchronous-udp-client
#!/usr/bin/env python
import unittest
from pymodbus.client.sync import ModbusUdpClient as ModbusClient
from base_runner import Runner

class AsynchronousUdpClient(Runner, unittest.TestCase):
    '''
    These are the integration tests for the asynchronous
    udp client.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        super(Runner, self).setUp()
        self.client = ModbusClient()

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.client.close()
        super(Runner, self).tearDown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = base_context
import os
import time
from subprocess import Popen as execute
from twisted.internet.defer import Deferred

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
log = logging.getLogger(__name__)

class ContextRunner(object):
    '''
    This is the base runner class for all the integration tests
    '''
    __bit_functions = [2,1] # redundant are removed for now
    __reg_functions = [4,3] # redundant are removed for now

    def initialize(self, service=None):
        ''' Initializes the test environment '''
        if service:
            self.fnull   = open(os.devnull, 'w')
            self.service = execute(service, stdout=self.fnull, stderr=self.fnull)
            log.debug("%s service started: %s", service, self.service.pid)
            time.sleep(0.2)
        else: self.service = None
        log.debug("%s context started", self.context)

    def shutdown(self):
        ''' Cleans up the test environment '''
        try:
            if self.service:
                self.service.kill()
                self.fnull.close()
            self.context.reset()
        except: pass
        log.debug("%s context stopped" % self.context)

    def testDataContextRegisters(self):
        ''' Test that the context gets and sets registers '''
        address = 10
        values = [0x1234] * 32
        for fx in self.__reg_functions:
            self.context.setValues(fx, address, values)
            result = self.context.getValues(fx, address, len(values))
            self.assertEquals(len(result), len(values))
            self.assertEquals(result, values)

    def testDataContextDiscretes(self):
        ''' Test that the context gets and sets discretes '''
        address = 10
        values = [True] * 32
        for fx in self.__bit_functions:
            self.context.setValues(fx, address, values)
            result = self.context.getValues(fx, address, len(values))
            self.assertEquals(len(result), len(values))
            self.assertEquals(result, values)


########NEW FILE########
__FILENAME__ = base_runner
import os
import time
from subprocess import Popen as execute
from twisted.internet.defer import Deferred

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
log = logging.getLogger(__name__)

class Runner(object):
    '''
    This is the base runner class for all the integration tests
    '''

    def initialize(self, service):
        ''' Initializes the test environment '''
        self.fnull  = open(os.devnull, 'w')
        self.server = execute(service, stdout=self.fnull, stderr=self.fnull)
        log.debug("%s service started: %s", service, self.server.pid)
        time.sleep(0.2)

    def shutdown(self):
        ''' Cleans up the test environment '''
        self.server.kill()
        self.fnull.close()
        log.debug("service stopped")

    def testReadWriteCoil(self):
        rq = self.client.write_coil(1, True)
        rr = self.client.read_coils(1,1)
        self.__validate(rq, lambda r: r.function_code < 0x80)
        self.__validate(rr, lambda r: r.bits[0] == True)
        
    def testReadWriteCoils(self):
        rq = self.client.write_coils(1, [True]*8)
        rr = self.client.read_coils(1,8)
        self.__validate(rq, lambda r: r.function_code < 0x80)
        self.__validate(rr, lambda r: r.bits == [True]*8)
        
    def testReadWriteDiscreteRegisters(self):
        rq = self.client.write_coils(1, [False]*8)
        rr = self.client.read_discrete_inputs(1,8)
        self.__validate(rq, lambda r: r.function_code < 0x80)
        self.__validate(rr, lambda r: r.bits == [False]*8)
        
    def testReadWriteHoldingRegisters(self):
        rq = self.client.write_register(1, 10)
        rr = self.client.read_holding_registers(1,1)
        self.__validate(rq, lambda r: r.function_code < 0x80)
        self.__validate(rr, lambda r: r.registers[0] == 10)
        
    def testReadWriteInputRegisters(self):
        rq = self.client.write_registers(1, [10]*8)
        rr = self.client.read_input_registers(1,8)
        self.__validate(rq, lambda r: r.function_code < 0x80)
        self.__validate(rr, lambda r: r.registers == [10]*8)
        
    def testReadWriteRegistersTogether(self):
        arguments = {
            'read_address':    1,
            'read_count':      8,
            'write_address':   1,
            'write_registers': [20]*8,
        }
        rq = self.client.readwrite_registers(**arguments)
        rr = self.client.read_input_registers(1,8)
        self.__validate(rq, lambda r: r.function_code < 0x80)
        self.__validate(rr, lambda r: r.registers == [20]*8)

    def __validate(self, result, test):
        ''' Validate the result whether it is a result or a deferred.

        :param result: The result to __validate
        :param callback: The test to __validate
        '''
        if isinstance(result, Deferred):
            deferred.callback(lambda : self.assertTrue(test(result)))
            deferred.errback(lambda _: self.assertTrue(False))
        else: self.assertTrue(test(result))


########NEW FILE########
__FILENAME__ = database-slave-context
#!/usr/bin/env python
import unittest, os
from pymodbus.datastore.database import DatabaseSlaveContext
from base_context import ContextRunner

class DatabaseSlaveContextTest(ContextRunner, unittest.TestCase):
    '''
    These are the integration tests for using the redis
    slave context.
    '''
    __database = 'sqlite:///pymodbus-test.db'

    def setUp(self):
        ''' Initializes the test environment '''
        path = './' + self.__database.split('///')[1]
        if os.path.exists(path): os.remove(path)
        self.context = DatabaseSlaveContext(database=self.__database)
        self.initialize()

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.context._connection.close()
        self.shutdown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = memory-slave-context
#!/usr/bin/env python
import unittest
from pymodbus.datastore.context import ModbusSlaveContext
from pymodbus.datastore.store import ModbusSequentialDataBlock
from base_context import ContextRunner

class MemorySlaveContextTest(ContextRunner, unittest.TestCase):
    '''
    These are the integration tests for using the in memory
    slave context.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        self.context = ModbusSlaveContext(**{
            'di' : ModbusSequentialDataBlock(0, [0]*100),
            'co' : ModbusSequentialDataBlock(0, [0]*100),
            'ir' : ModbusSequentialDataBlock(0, [0]*100),
            'hr' : ModbusSequentialDataBlock(0, [0]*100)})
        self.initialize()

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.shutdown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = redis-slave-context
#!/usr/bin/env python
import unittest
import os
from subprocess import Popen as execute
from pymodbus.datastore.modredis import RedisSlaveContext
from base_context import ContextRunner

class RedisSlaveContextTest(ContextRunner, unittest.TestCase):
    '''
    These are the integration tests for using the redis
    slave context.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        self.context = RedisSlaveContext() # the redis client will block, so no wait needed
        self.initialize("redis-server")

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.server.kill()
        self.fnull.close()
        self.shutdown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = remote-slave-context
#!/usr/bin/env python
import unittest
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.datastore.remote import RemoteSlaveContext
from base_context import ContextRunner

class RemoteSlaveContextTest(ContextRunner, unittest.TestCase):
    '''
    These are the integration tests for using the redis
    slave context.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        self.context = RemoteSlaveContext(client=None) # for the log statment
        self.initialize(["../tools/reference/diagslave", "-m", "tcp", "-p", "12345"])
        self.client = ModbusTcpClient(port=12345)
        self.context = RemoteSlaveContext(client=self.client)

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.client.close()
        self.shutdown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = synchronous-ascii-client
#!/usr/bin/env python
import unittest
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from base_runner import Runner

class SynchronousAsciiClient(Runner, unittest.TestCase):
    '''
    These are the integration tests for the synchronous
    serial ascii client.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        super(Runner, self).setUp()
        #    "../tools/nullmodem/linux/run",
        self.initialize(["../tools/reference/diagslave", "-m", "ascii", "/dev/pts/14"])
        self.client = ModbusClient(method='ascii', timeout=0.2, port='/dev/pts/13')
        self.client.connect()

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.client.close()
        super(Runner, self).tearDown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = synchronous-rtu-client
#!/usr/bin/env python
import unittest
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from base_runner import Runner

class SynchronousRtuClient(Runner, unittest.TestCase):
    '''
    These are the integration tests for the synchronous
    serial rtu client.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        super(Runner, self).setUp()
        self.initialize(["../tools/reference/diagslave", "-m", "rtu", "/dev/pts/14"])
        self.client = ModbusClient(method='rtu', timeout=0.2, port='/dev/pts/13')
        self.client.connect()

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.client.close()
        super(Runner, self).tearDown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = synchronous-tcp-client
#!/usr/bin/env python
import unittest
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
from base_runner import Runner

class SynchronousTcpClient(Runner, unittest.TestCase):
    '''
    These are the integration tests for the synchronous
    tcp client.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        self.initialize(["../tools/reference/diagslave", "-m", "tcp", "-p", "12345"])
        self.client = ModbusClient(port=12345)

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.client.close()
        self.shutdown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = synchronous-udp-client
#!/usr/bin/env python
import unittest
from pymodbus.client.sync import ModbusUdpClient as ModbusClient
from base_runner import Runner

class SynchronousUdpClient(Runner, unittest.TestCase):
    '''
    These are the integration tests for the synchronous
    udp client.
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        super(Runner, self).setUp()
        self.client = ModbusClient()

    def tearDown(self):
        ''' Cleans up the test environment '''
        self.client.close()
        super(Runner, self).tearDown()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = frontend
'''
Pymodbus Web Frontend
=======================================

This is a simple web frontend using bottle as the web framework.
This can be hosted using any wsgi adapter.
'''
import json, inspect
from bottle import route, request, Bottle
from bottle import static_file
from bottle import jinja2_template as template

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# REST API
#---------------------------------------------------------------------------# 
class Response(object):
    '''
    A collection of common responses for the frontend api
    '''
    success = { 'status' : 200 }
    failure = { 'status' : 500 }

class ModbusApiWebApp(object):
    '''
    This is the web REST api interace into the pymodbus
    service.  It can be consumed by any utility that can
    make web requests (javascript).
    '''
    _namespace = '/api/v1'

    def __init__(self, server):
        ''' Initialize a new instance of the ModbusApi

        :param server: The current server instance
        '''
        self._server = server

    #---------------------------------------------------------------------#
    # Device API
    #---------------------------------------------------------------------#
    def get_device(self):
        return {
            'mode'        : self._server.control.Mode,
            'delimiter'   : self._server.control.Delimiter,
            'readonly'    : self._server.control.ListenOnly,
            'identity'    : self._server.control.Identity.summary(),
            'counters'    : dict(self._server.control.Counter),
            'diagnostic'  : self._server.control.getDiagnosticRegister(),
        }
    
    def get_device_identity(self):
        return {
            'identity' : dict(self._server.control.Identity)
        }

    def get_device_counters(self):
        return {
            'counters' : dict(self._server.control.Counter)
        }
    
    def get_device_events(self):
        return {
            'events' : self._server.control.Events
        }

    def get_device_plus(self):
        return {
            'plus' : dict(self._server.control.Plus)
        }
    
    def delete_device_events(self):
        self._server.control.clearEvents()
        return Response.success
    
    def get_device_host(self):
        return {
            'hosts' : list(self._server.access)
        }
    
    def post_device_host(self):
        value = request.forms.get('host')
        if value:
            self._server.access.add(value)
        return Response.success
    
    def delete_device_host(self):
        value = request.forms.get('host')
        if value:
            self._server.access.remove(value)
        return Response.success
    
    def post_device_delimiter(self):
        value = request.forms.get('delimiter')
        if value:
            self._server.control.Delimiter = value
        return Response.success
    
    def post_device_mode(self):
        value = request.forms.get('mode')
        if value:
            self._server.control.Mode = value
        return Response.success
    
    def post_device_reset(self):
        self._server.control.reset()
        return Response.success

    #---------------------------------------------------------------------#
    # Datastore Get API
    #---------------------------------------------------------------------#
    def __get_data(self, store, address, count, slave='00'):
        try:
            address, count = int(address), int(count)
            context = self._server.store[int(store)]
            values  = context.getValues(store, address, count)
            values  = dict(zip(range(address, address + count), values))
            result  = { 'data' : values }
            result.update(Response.success)
            return result
        except Exception, ex: log.error(ex)
        return Response.failure

    def get_coils(self, address='0', count='1'):
        return self.__get_data(1, address, count)

    def get_discretes(self, address='0', count='1'):
        return self.__get_data(2, address, count)

    def get_holdings(self, address='0', count='1'):
        return self.__get_data(3, address, count)

    def get_inputs(self, address='0', count='1'):
        return self.__get_data(4, address, count)

    #---------------------------------------------------------------------#
    # Datastore Update API
    #---------------------------------------------------------------------#
    def __set_data(self, store, address, values, slave='00'):
        try:
            address = int(address)
            values  = json.loads(values)
            print values
            context = self._server.store[int(store)]
            context.setValues(store, address, values)
            return Response.success
        except Exception, ex: log.error(ex)
        return Response.failure

    def post_coils(self, address='0'):
        values = request.forms.get('data')
        return self.__set_data(1, address, values)

    def post_discretes(self, address='0'):
        values = request.forms.get('data')
        return self.__set_data(2, address, values)

    def post_holding(self, address='0'):
        values = request.forms.get('data')
        return self.__set_data(3, address, values)

    def post_inputs(self, address='0'):
        values = request.forms.get('data')
        return self.__set_data(4, address, values)

#---------------------------------------------------------------------#
# webpage routes
#---------------------------------------------------------------------#
def register_web_routes(application, register):
    ''' A helper method to register the default web routes of
    a single page application.

    :param application: The application instance to register
    :param register: The bottle instance to register the application with
    '''
    def get_index_file():
        return template('index.html')
    
    def get_static_file(filename):
        return static_file(filename, root='./media')

    register.route('/', method='GET', name='get_index_file')(get_index_file)
    register.route('/media/<filename:path>', method='GET', name='get_static_file')(get_static_file)

#---------------------------------------------------------------------------# 
# Configurations
#---------------------------------------------------------------------------# 
def register_api_routes(application, register):
    ''' A helper method to register the routes of an application
    based on convention. This is easier to manage than having to
    decorate each method with a static route name.

    :param application: The application instance to register
    :param register: The bottle instance to register the application with
    '''
    log.info("installing application routes:")
    methods = inspect.getmembers(application)
    methods = filter(lambda n: not n[0].startswith('_'), methods)
    for method, func in dict(methods).iteritems():
        pieces = method.split('_')
        verb, path = pieces[0], pieces[1:]
        args = inspect.getargspec(func).args[1:]
        args = ['<%s>' % arg for arg in args]
        args = '/'.join(args)
        args = '' if len(args) == 0 else '/' + args
        path.insert(0, application._namespace)
        path = '/'.join(path) + args 
        log.info("%6s: %s" % (verb, path))
        register.route(path, method=verb, name=method)(func)

def build_application(server):
    ''' Helper method to create and initiailze a bottle application

    :param server: The modbus server to pull instance data from
    :returns: An initialied bottle application
    '''
    log.info("building web application")
    api = ModbusApiWebApp(server)
    register = Bottle()
    register_api_routes(api, register)
    register_web_routes(api, register)
    return register

#---------------------------------------------------------------------------# 
# Start Methods
#---------------------------------------------------------------------------# 
def RunModbusFrontend(server, port=8080):
    ''' Helper method to host bottle in twisted

    :param server: The modbus server to pull instance data from
    :param port: The port to host the service on
    '''
    from bottle import TwistedServer, run

    application = build_application(server)
    run(app=application, server=TwistedServer, port=port)

def RunDebugModbusFrontend(server, port=8080):
    ''' Helper method to start the bottle server

    :param server: The modbus server to pull instance data from
    :param port: The port to host the service on
    '''
    from bottle import run

    application = build_application(server)
    run(app=application, port=port)

if __name__ == '__main__':
    # ------------------------------------------------------------
    # an example server configuration
    # ------------------------------------------------------------
    from pymodbus.server.async import ModbusServerFactory
    from pymodbus.constants import Defaults
    from pymodbus.device import ModbusDeviceIdentification
    from pymodbus.datastore import ModbusSequentialDataBlock
    from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
    from twisted.internet import reactor

    # ------------------------------------------------------------
    # initialize the identity
    # ------------------------------------------------------------

    identity = ModbusDeviceIdentification()
    identity.VendorName  = 'Pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl   = 'http://github.com/bashwork/pymodbus/'
    identity.ProductName = 'Pymodbus Server'
    identity.ModelName   = 'Pymodbus Server'
    identity.MajorMinorRevision = '1.0'

    # ------------------------------------------------------------
    # initialize the datastore
    # ------------------------------------------------------------
    store = ModbusSlaveContext(
        di = ModbusSequentialDataBlock(0, [17]*100),
        co = ModbusSequentialDataBlock(0, [17]*100),
        hr = ModbusSequentialDataBlock(0, [17]*100),
        ir = ModbusSequentialDataBlock(0, [17]*100))
    context = ModbusServerContext(slaves=store, single=True)

    # ------------------------------------------------------------
    # initialize the factory 
    # ------------------------------------------------------------
    address = ("", Defaults.Port)
    factory = ModbusServerFactory(context, None, identity)

    # ------------------------------------------------------------
    # start the servers
    # ------------------------------------------------------------
    log.info("Starting Modbus TCP Server on %s:%s" % address)
    reactor.listenTCP(address[1], factory, interface=address[0])
    RunDebugModbusFrontend(factory)

########NEW FILE########
__FILENAME__ = simulator
#!/usr/bin/env python
#---------------------------------------------------------------------------#
# System
#---------------------------------------------------------------------------#
import os
import getpass
import pickle
from threading import Thread

#---------------------------------------------------------------------------#
# For Gui
#---------------------------------------------------------------------------#
from twisted.internet import gtk2reactor
gtk2reactor.install()
import gtk
from gtk import glade

#---------------------------------------------------------------------------#
# SNMP Simulator
#---------------------------------------------------------------------------#
from twisted.internet import reactor
from twisted.internet import error as twisted_error
from pymodbus.server.async import ModbusServerFactory
from pymodbus.datastore import ModbusServerContext,ModbusSlaveContext

#--------------------------------------------------------------------------#
# Logging
#--------------------------------------------------------------------------#
import logging
log = logging.getLogger(__name__)

#---------------------------------------------------------------------------#
# Application Error
#---------------------------------------------------------------------------#
class ConfigurationException(Exception):
    ''' Exception for configuration error '''

    def __init__(self, string):
        Exception.__init__(self, string)
        self.string = string

    def __str__(self):
        return 'Configuration Error: %s' % self.string

#---------------------------------------------------------------------------#
# Extra Global Functions
#---------------------------------------------------------------------------#
# These are extra helper functions that don't belong in a class
#---------------------------------------------------------------------------#
def root_test():
    ''' Simple test to see if we are running as root '''
    return getpass.getuser() == "root"

#---------------------------------------------------------------------------#
# Simulator Class
#---------------------------------------------------------------------------#
class Simulator(object):
    '''
    Class used to parse configuration file and create and modbus
    datastore.

    The format of the configuration file is actually just a
    python pickle, which is a compressed memory dump from
    the scraper.
    '''

    def __init__(self, config):
        '''
        Trys to load a configuration file, lets the file not
        found exception fall through

        @param config The pickled datastore
        '''
        try:
            self.file = open(config, "r")
        except Exception:
            raise ConfigurationException("File not found %s" % config)

    def _parse(self):
        ''' Parses the config file and creates a server context '''
        try:
            handle = pickle.load(self.file)
            dsd = handle['di']
            csd = handle['ci']
            hsd = handle['hr']
            isd = handle['ir']
        except KeyError:
            raise ConfigurationException("Invalid Configuration")
        slave = ModbusSlaveContext(d=dsd, c=csd, h=hsd, i=isd)
        return ModbusServerContext(slaves=slave)

    def _simulator(self):
        ''' Starts the snmp simulator '''
        ports = [502]+range(20000,25000)
        for port in ports:
            try:
                reactor.listenTCP(port, ModbusServerFactory(self._parse()))
                print 'listening on port', port
                return port
            except twisted_error.CannotListenError:
                pass

    def run(self):
        ''' Used to run the simulator '''
        reactor.callWhenRunning(self._simulator)

#---------------------------------------------------------------------------#
# Network reset thread
#---------------------------------------------------------------------------#
# This is linux only, maybe I should make a base class that can be filled
# in for linux(debian/redhat)/windows/nix
#---------------------------------------------------------------------------#
class NetworkReset(Thread):
    '''
    This class is simply a daemon that is spun off at the end of the
    program to call the network restart function (an easy way to
    remove all the virtual interfaces)
    '''
    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        ''' Run the network reset '''
        os.system("/etc/init.d/networking restart")

#---------------------------------------------------------------------------#
# Main Gui Class
#---------------------------------------------------------------------------#
# Note, if you are using gtk2 before 2.12, the file_set signal is not
# introduced.  To fix this, you need to apply the following patch
#---------------------------------------------------------------------------#
#Index: simulator.py
#===================================================================
#--- simulator.py       (revision 60)
#+++ simulator.py       (working copy)
#@@ -158,7 +161,7 @@
#                       "on_helpBtn_clicked"    : self.help_clicked,
#                       "on_quitBtn_clicked"    : self.close_clicked,
#                       "on_startBtn_clicked"   : self.start_clicked,
#-                      "on_file_changed"       : self.file_changed,
#+                      #"on_file_changed"      : self.file_changed,
#                       "on_window_destroy"     : self.close_clicked
#               }
#               self.tree.signal_autoconnect(actions)
#@@ -235,6 +238,7 @@
#                       return False
#
#               # check input file
#+              self.file_changed(self.tdevice)
#               if os.path.exists(self.file):
#                       self.grey_out()
#                       handle = Simulator(config=self.file)
#---------------------------------------------------------------------------#
class SimulatorApp(object):
    '''
    This class implements the GUI for the flasher application
    '''
    file = "none"
    subnet = 205
    number = 1
    restart = 0

    def __init__(self, xml):
        ''' Sets up the gui, callback, and widget handles '''

        #---------------------------------------------------------------------------#
        # Action Handles
        #---------------------------------------------------------------------------#
        self.tree    = glade.XML(xml)
        self.bstart  = self.tree.get_widget("startBtn")
        self.bhelp   = self.tree.get_widget("helpBtn")
        self.bclose  = self.tree.get_widget("quitBtn")
        self.window  = self.tree.get_widget("window")
        self.tdevice = self.tree.get_widget("fileTxt")
        self.tsubnet = self.tree.get_widget("addressTxt")
        self.tnumber = self.tree.get_widget("deviceTxt")

        #---------------------------------------------------------------------------#
        # Actions
        #---------------------------------------------------------------------------#
        actions = {
            "on_helpBtn_clicked"  : self.help_clicked,
            "on_quitBtn_clicked"  : self.close_clicked,
            "on_startBtn_clicked" : self.start_clicked,
            "on_file_changed"     : self.file_changed,
            "on_window_destroy"   : self.close_clicked
        }
        self.tree.signal_autoconnect(actions)
        if not root_test():
            self.error_dialog("This program must be run with root permissions!", True)

#---------------------------------------------------------------------------#
# Gui helpers
#---------------------------------------------------------------------------#
# Not callbacks, but used by them
#---------------------------------------------------------------------------#
    def show_buttons(self, state=False, all=0):
        ''' Greys out the buttons '''
        if all:
            self.window.set_sensitive(state)
        self.bstart.set_sensitive(state)
        self.tdevice.set_sensitive(state)
        self.tsubnet.set_sensitive(state)
        self.tnumber.set_sensitive(state)

    def destroy_interfaces(self):
        ''' This is used to reset the virtual interfaces '''
        if self.restart:
            n = NetworkReset()
            n.start()

    def error_dialog(self, message, quit=False):
        ''' Quick pop-up for error messages '''
        dialog = gtk.MessageDialog(
            parent         = self.window,
            flags          = gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_MODAL,
            type           = gtk.MESSAGE_ERROR,
            buttons        = gtk.BUTTONS_CLOSE,
            message_format = message)
        dialog.set_title('Error')
        if quit:
            dialog.connect("response", lambda w, r: gtk.main_quit())
        else:
            dialog.connect("response", lambda w, r: w.destroy())
        dialog.show()

#---------------------------------------------------------------------------#
# Button Actions
#---------------------------------------------------------------------------#
# These are all callbacks for the various buttons
#---------------------------------------------------------------------------#
    def start_clicked(self, widget):
        ''' Starts the simulator '''
        start = 1
        base = "172.16"

        # check starting network
        net = self.tsubnet.get_text()
        octets = net.split('.')
        if len(octets) == 4:
            base = "%s.%s" % (octets[0], octets[1])
            net = int(octets[2]) % 255
            start = int(octets[3]) % 255
        else:
            self.error_dialog("Invalid starting address!");
            return False

        # check interface size
        size = int(self.tnumber.get_text())
        if (size >= 1):
            for i in range(start, (size + start)):
                j = i % 255
                cmd = "/sbin/ifconfig eth0:%d %s.%d.%d" % (i, base, net, j)
                os.system(cmd)
                if j == 254: net = net + 1
            self.restart = 1
        else:
            self.error_dialog("Invalid number of devices!");
            return False

        # check input file
        if os.path.exists(self.file):
            self.show_buttons(state=False)
            try:
                handle = Simulator(config=self.file)
                handle.run()
            except ConfigurationException, ex:
                self.error_dialog("Error %s" % ex)
                self.show_buttons(state=True)
        else:
            self.error_dialog("Device to emulate does not exist!");
            return False

    def help_clicked(self, widget):
        ''' Quick pop-up for about page '''
        data = gtk.AboutDialog()
        data.set_version("0.1")
        data.set_name(('Modbus Simulator'))
        data.set_authors(["Galen Collins"])
        data.set_comments(('First Select a device to simulate,\n'
            + 'then select the starting subnet of the new devices\n'
            + 'then select the number of device to simulate and click start'))
        data.set_website("http://code.google.com/p/pymodbus/")
        data.connect("response", lambda w,r: w.hide())
        data.run()

    def close_clicked(self, widget):
        ''' Callback for close button '''
        self.destroy_interfaces()
        reactor.stop()          # quit twisted

    def file_changed(self, widget):
        ''' Callback for the filename change '''
        self.file = widget.get_filename()

#---------------------------------------------------------------------------#
# Main handle function
#---------------------------------------------------------------------------#
# This is called when the application is run from a console
# We simply start the gui and start the twisted event loop
#---------------------------------------------------------------------------#
def main():
    '''
    Main control function
    This either launches the gui or runs the command line application
    '''
    debug = True
    if debug:
        try:
            log.setLevel(logging.DEBUG)
    	    logging.basicConfig()
        except Exception, e:
    	    print "Logging is not supported on this system"
    simulator = SimulatorApp('./simulator.glade')
    reactor.run()

#---------------------------------------------------------------------------#
# Library/Console Test
#---------------------------------------------------------------------------#
# If this is called from console, we start main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = gui-common
#!/usr/bin/env python
#---------------------------------------------------------------------------#
# System
#---------------------------------------------------------------------------#
import os
import getpass
import pickle
from threading import Thread

#---------------------------------------------------------------------------#
# SNMP Simulator
#---------------------------------------------------------------------------#
from twisted.internet import reactor
from twisted.internet import error as twisted_error
from pymodbus.server.async import ModbusServerFactory
from pymodbus.datastore import ModbusServerContext,ModbusSlaveContext

#--------------------------------------------------------------------------#
# Logging
#--------------------------------------------------------------------------#
import logging
log = logging.getLogger("pymodbus")

#---------------------------------------------------------------------------#
# Application Error
#---------------------------------------------------------------------------#
class ConfigurationException(Exception):
    ''' Exception for configuration error '''
    pass

#---------------------------------------------------------------------------#
# Extra Global Functions
#---------------------------------------------------------------------------#
# These are extra helper functions that don't belong in a class
#---------------------------------------------------------------------------#
def root_test():
    ''' Simple test to see if we are running as root '''
    return getpass.getuser() == "root"

#---------------------------------------------------------------------------#
# Simulator Class
#---------------------------------------------------------------------------#
class Simulator(object):
    '''
    Class used to parse configuration file and create and modbus
    datastore.

    The format of the configuration file is actually just a
    python pickle, which is a compressed memory dump from
    the scraper.
    '''

    def __init__(self, config):
        '''
        Trys to load a configuration file, lets the file not
        found exception fall through

        :param config: The pickled datastore
        '''
        try:
            self.file = open(config, "r")
        except Exception:
            raise ConfigurationException("File not found %s" % config)

    def _parse(self):
        ''' Parses the config file and creates a server context '''
        try:
            handle = pickle.load(self.file)
            dsd = handle['di']
            csd = handle['ci']
            hsd = handle['hr']
            isd = handle['ir']
        except KeyError:
            raise ConfigurationException("Invalid Configuration")
        slave = ModbusSlaveContext(d=dsd, c=csd, h=hsd, i=isd)
        return ModbusServerContext(slaves=slave)

    def _simulator(self):
        ''' Starts the snmp simulator '''
        ports = [502]+range(20000,25000)
        for port in ports:
            try:
                reactor.listenTCP(port, ModbusServerFactory(self._parse()))
                log.debug('listening on port %d' % port)
                return port
            except twisted_error.CannotListenError:
                pass

    def run(self):
        ''' Used to run the simulator '''
        log.debug('simulator started')
        reactor.callWhenRunning(self._simulator)

#---------------------------------------------------------------------------#
# Network reset thread
#---------------------------------------------------------------------------#
# This is linux only, maybe I should make a base class that can be filled
# in for linux(debian/redhat)/windows/nix
#---------------------------------------------------------------------------#
class NetworkReset(Thread):
    '''
    This class is simply a daemon that is spun off at the end of the
    program to call the network restart function (an easy way to
    remove all the virtual interfaces)
    '''

    def __init__(self):
        ''' Initialize a new network reset thread '''
        Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        ''' Run the network reset '''
        os.system("/etc/init.d/networking restart")


########NEW FILE########
__FILENAME__ = simulator
#!/usr/bin/env python
'''
Note that this is not finished
'''
#---------------------------------------------------------------------------#
# System
#---------------------------------------------------------------------------#
import os
import getpass
import pickle
from threading import Thread

#---------------------------------------------------------------------------#
# For Gui
#---------------------------------------------------------------------------#
from Tkinter import *
from tkFileDialog import askopenfilename as OpenFilename
from twisted.internet import tksupport
root = Tk()
tksupport.install(root)

#---------------------------------------------------------------------------#
# SNMP Simulator
#---------------------------------------------------------------------------#
from twisted.internet import reactor
from twisted.internet import error as twisted_error
from pymodbus.server.async import ModbusServerFactory
from pymodbus.datastore import ModbusServerContext,ModbusSlaveContext

#--------------------------------------------------------------------------#
# Logging
#--------------------------------------------------------------------------#
import logging
log = logging.getLogger(__name__)

#---------------------------------------------------------------------------#
# Application Error
#---------------------------------------------------------------------------#
class ConfigurationException(Exception):
    ''' Exception for configuration error '''
    pass

#---------------------------------------------------------------------------#
# Extra Global Functions
#---------------------------------------------------------------------------#
# These are extra helper functions that don't belong in a class
#---------------------------------------------------------------------------#
def root_test():
    ''' Simple test to see if we are running as root '''
    return getpass.getuser() == "root"

#---------------------------------------------------------------------------#
# Simulator Class
#---------------------------------------------------------------------------#
class Simulator(object):
    '''
    Class used to parse configuration file and create and modbus
    datastore.

    The format of the configuration file is actually just a
    python pickle, which is a compressed memory dump from
    the scraper.
    '''

    def __init__(self, config):
        '''
        Trys to load a configuration file, lets the file not
        found exception fall through

        @param config The pickled datastore
        '''
        try:
            self.file = open(config, "r")
        except Exception:
            raise ConfigurationException("File not found %s" % config)

    def _parse(self):
        ''' Parses the config file and creates a server context '''
        try:
            handle = pickle.load(self.file)
            dsd = handle['di']
            csd = handle['ci']
            hsd = handle['hr']
            isd = handle['ir']
        except KeyError:
            raise ConfigurationException("Invalid Configuration")
        slave = ModbusSlaveContext(d=dsd, c=csd, h=hsd, i=isd)
        return ModbusServerContext(slaves=slave)

    def _simulator(self):
        ''' Starts the snmp simulator '''
        ports = [502]+range(20000,25000)
        for port in ports:
            try:
                reactor.listenTCP(port, ModbusServerFactory(self._parse()))
                log.info('listening on port %d' % port)
                return port
            except twisted_error.CannotListenError:
                pass

    def run(self):
        ''' Used to run the simulator '''
        reactor.callWhenRunning(self._simulator)

#---------------------------------------------------------------------------#
# Network reset thread
#---------------------------------------------------------------------------#
# This is linux only, maybe I should make a base class that can be filled
# in for linux(debian/redhat)/windows/nix
#---------------------------------------------------------------------------#
class NetworkReset(Thread):
    '''
    This class is simply a daemon that is spun off at the end of the
    program to call the network restart function (an easy way to
    remove all the virtual interfaces)
    '''
    def __init__(self):
        Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        ''' Run the network reset '''
        os.system("/etc/init.d/networking restart")

#---------------------------------------------------------------------------#
# Main Gui Class
#---------------------------------------------------------------------------#
class SimulatorFrame(Frame):
    '''
    This class implements the GUI for the flasher application
    '''
    subnet  = 205
    number  = 1
    restart = 0

    def __init__(self, master, font):
        ''' Sets up the gui, callback, and widget handles '''
        Frame.__init__(self, master)
        self._widgets = []

        #---------------------------------------------------------------------------#
        # Initialize Buttons Handles
        #---------------------------------------------------------------------------#
        frame = Frame(self)
        frame.pack(side=BOTTOM, pady=5)

        button = Button(frame, text="Apply", command=self.start_clicked, font=font)
        button.pack(side=LEFT, padx=15)
        self._widgets.append(button)

        button = Button(frame, text="Help",  command=self.help_clicked, font=font)
        button.pack(side=LEFT, padx=15)
        self._widgets.append(button)

        button = Button(frame, text="Close", command=self.close_clicked, font=font)
        button.pack(side=LEFT, padx=15)
        #self._widgets.append(button) # we don't want to grey this out

        #---------------------------------------------------------------------------#
        # Initialize Input Fields
        #---------------------------------------------------------------------------#
        frame = Frame(self)
        frame.pack(side=TOP, padx=10, pady=5)

        self.tsubnet_value = StringVar()
        label = Label(frame, text="Starting Address", font=font)
        label.grid(row=0, column=0, pady=10)
        entry = Entry(frame, textvariable=self.tsubnet_value, font=font)
        entry.grid(row=0, column=1, pady=10)
        self._widgets.append(entry)

        self.tdevice_value = StringVar()
        label = Label(frame, text="Device to Simulate", font=font)
        label.grid(row=1, column=0, pady=10)
        entry = Entry(frame, textvariable=self.tdevice_value, font=font)
        entry.grid(row=1, column=1, pady=10)
        self._widgets.append(entry)

        image = PhotoImage(file='fileopen.gif')
        button = Button(frame, image=image, command=self.file_clicked)
        button.image = image
        button.grid(row=1, column=2, pady=10)
        self._widgets.append(button)

        self.tnumber_value = StringVar()
        label = Label(frame, text="Number of Devices", font=font)
        label.grid(row=2, column=0, pady=10)
        entry = Entry(frame, textvariable=self.tnumber_value, font=font)
        entry.grid(row=2, column=1, pady=10)
        self._widgets.append(entry)

        #if not root_test():
        #    self.error_dialog("This program must be run with root permissions!", True)

#---------------------------------------------------------------------------#
# Gui helpers
#---------------------------------------------------------------------------#
# Not callbacks, but used by them
#---------------------------------------------------------------------------#
    def show_buttons(self, state=False):
        ''' Greys out the buttons '''
        state = 'active' if state else 'disabled'
        for widget in self._widgets:
            widget.configure(state=state)

    def destroy_interfaces(self):
        ''' This is used to reset the virtual interfaces '''
        if self.restart:
            n = NetworkReset()
            n.start()

    def error_dialog(self, message, quit=False):
        ''' Quick pop-up for error messages '''
        dialog = gtk.MessageDialog(
            parent          = self.window,
            flags           = gtk.DIALOG_DESTROY_WITH_PARENT | gtk.DIALOG_MODAL,
            type            = gtk.MESSAGE_ERROR,
            buttons         = gtk.BUTTONS_CLOSE,
            message_format  = message)
        dialog.set_title('Error')
        if quit:
            dialog.connect("response", lambda w, r: gtk.main_quit())
        else: dialog.connect("response", lambda w, r: w.destroy())
        dialog.show()

#---------------------------------------------------------------------------#
# Button Actions
#---------------------------------------------------------------------------#
# These are all callbacks for the various buttons
#---------------------------------------------------------------------------#
    def start_clicked(self):
        ''' Starts the simulator '''
        start = 1
        base = "172.16"

        # check starting network
        net = self.tsubnet_value.get()
        octets = net.split('.')
        if len(octets) == 4:
            base = "%s.%s" % (octets[0], octets[1])
            net = int(octets[2]) % 255
            start = int(octets[3]) % 255
        else:
            self.error_dialog("Invalid starting address!");
            return False

        # check interface size
        size = int(self.tnumber_value.get())
        if (size >= 1):
            for i in range(start, (size + start)):
                j = i % 255
                cmd = "/sbin/ifconfig eth0:%d %s.%d.%d" % (i, base, net, j)
                os.system(cmd)
                if j == 254: net = net + 1
            self.restart = 1
        else:
            self.error_dialog("Invalid number of devices!");
            return False

        # check input file
        filename = self.tdevice_value.get()
        if os.path.exists(filename):
            self.show_buttons(state=False)
            try:
                handle = Simulator(config=filename)
                handle.run()
            except ConfigurationException, ex:
                self.error_dialog("Error %s" % ex)
                self.show_buttons(state=True)
        else:
            self.error_dialog("Device to emulate does not exist!");
            return False

    def help_clicked(self):
        ''' Quick pop-up for about page '''
        data = gtk.AboutDialog()
        data.set_version("0.1")
        data.set_name(('Modbus Simulator'))
        data.set_authors(["Galen Collins"])
        data.set_comments(('First Select a device to simulate,\n'
            + 'then select the starting subnet of the new devices\n'
            + 'then select the number of device to simulate and click start'))
        data.set_website("http://code.google.com/p/pymodbus/")
        data.connect("response", lambda w,r: w.hide())
        data.run()

    def close_clicked(self):
        ''' Callback for close button '''
        #self.destroy_interfaces()
        reactor.stop()

    def file_clicked(self):
        ''' Callback for the filename change '''
        file = OpenFilename()
        self.tdevice_value.set(file)

class SimulatorApp(object):
    ''' The main wx application handle for our simulator
    '''

    def __init__(self, master):
        '''
        Called by wxWindows to initialize our application

        :param master: The master window to connect to
        '''
        font  = ('Helvetica', 12, 'normal')
        frame = SimulatorFrame(master, font)
        frame.pack()

#---------------------------------------------------------------------------#
# Main handle function
#---------------------------------------------------------------------------#
# This is called when the application is run from a console
# We simply start the gui and start the twisted event loop
#---------------------------------------------------------------------------#
def main():
    '''
    Main control function
    This either launches the gui or runs the command line application
    '''
    debug = True
    if debug:
        try:
            log.setLevel(logging.DEBUG)
    	    logging.basicConfig()
        except Exception, e:
    	    print "Logging is not supported on this system"
    simulator = SimulatorApp(root)
    root.title("Modbus Simulator")
    reactor.run()

#---------------------------------------------------------------------------#
# Library/Console Test
#---------------------------------------------------------------------------#
# If this is called from console, we start main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = simulator
#!/usr/bin/env python
'''
Note that this is not finished
'''
#---------------------------------------------------------------------------#
# System
#---------------------------------------------------------------------------#
import os
import getpass
import pickle
from threading import Thread

#---------------------------------------------------------------------------#
# For Gui
#---------------------------------------------------------------------------#
import wx
from twisted.internet import wxreactor
wxreactor.install()

#---------------------------------------------------------------------------#
# SNMP Simulator
#---------------------------------------------------------------------------#
from twisted.internet import reactor
from twisted.internet import error as twisted_error
from pymodbus.server.async import ModbusServerFactory
from pymodbus.datastore import ModbusServerContext,ModbusSlaveContext

#--------------------------------------------------------------------------#
# Logging
#--------------------------------------------------------------------------#
import logging
log = logging.getLogger(__name__)

#---------------------------------------------------------------------------#
# Application Error
#---------------------------------------------------------------------------#
class ConfigurationException(Exception):
    ''' Exception for configuration error '''
    pass

#---------------------------------------------------------------------------#
# Extra Global Functions
#---------------------------------------------------------------------------#
# These are extra helper functions that don't belong in a class
#---------------------------------------------------------------------------#
def root_test():
    ''' Simple test to see if we are running as root '''
    return getpass.getuser() == "root"

#---------------------------------------------------------------------------#
# Simulator Class
#---------------------------------------------------------------------------#
class Simulator(object):
    '''
    Class used to parse configuration file and create and modbus
    datastore.

    The format of the configuration file is actually just a
    python pickle, which is a compressed memory dump from
    the scraper.
    '''

    def __init__(self, config):
        '''
        Trys to load a configuration file, lets the file not
        found exception fall through

        @param config The pickled datastore
        '''
        try:
            self.file = open(config, "r")
        except Exception:
            raise ConfigurationException("File not found %s" % config)

    def _parse(self):
        ''' Parses the config file and creates a server context '''
        try:
            handle = pickle.load(self.file)
            dsd = handle['di']
            csd = handle['ci']
            hsd = handle['hr']
            isd = handle['ir']
        except KeyError:
            raise ConfigurationException("Invalid Configuration")
        slave = ModbusSlaveContext(d=dsd, c=csd, h=hsd, i=isd)
        return ModbusServerContext(slaves=slave)

    def _simulator(self):
        ''' Starts the snmp simulator '''
        ports = [502]+range(20000,25000)
        for port in ports:
            try:
                reactor.listenTCP(port, ModbusServerFactory(self._parse()))
                print 'listening on port', port
                return port
            except twisted_error.CannotListenError:
                pass

    def run(self):
        ''' Used to run the simulator '''
        reactor.callWhenRunning(self._simulator)

#---------------------------------------------------------------------------#
# Network reset thread
#---------------------------------------------------------------------------#
# This is linux only, maybe I should make a base class that can be filled
# in for linux(debian/redhat)/windows/nix
#---------------------------------------------------------------------------#
class NetworkReset(Thread):
    '''
    This class is simply a daemon that is spun off at the end of the
    program to call the network restart function (an easy way to
    remove all the virtual interfaces)
    '''
    def __init__(self):
        ''' Initializes a new instance of the network reset thread '''
        Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        ''' Run the network reset '''
        os.system("/etc/init.d/networking restart")

#---------------------------------------------------------------------------#
# Main Gui Class
#---------------------------------------------------------------------------#
class SimulatorFrame(wx.Frame):
    '''
    This class implements the GUI for the flasher application
    '''
    subnet = 205
    number = 1
    restart = 0

    def __init__(self, parent, id, title):
        '''
        Sets up the gui, callback, and widget handles
        '''
        wx.Frame.__init__(self, parent, id, title)
        wx.EVT_CLOSE(self, self.close_clicked)

        #---------------------------------------------------------------------------#
        # Add button row
        #---------------------------------------------------------------------------#
        panel = wx.Panel(self, -1)
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(wx.Button(panel, 1, 'Apply'), 1)
        box.Add(wx.Button(panel, 2, 'Help'),  1)
        box.Add(wx.Button(panel, 3, 'Close'), 1)
        panel.SetSizer(box)

        #---------------------------------------------------------------------------#
        # Add input boxes
        #---------------------------------------------------------------------------#
        #self.tdevice    = self.tree.get_widget("fileTxt")
        #self.tsubnet    = self.tree.get_widget("addressTxt")
        #self.tnumber    = self.tree.get_widget("deviceTxt")

        #---------------------------------------------------------------------------#
        # Tie callbacks
        #---------------------------------------------------------------------------#
        self.Bind(wx.EVT_BUTTON, self.start_clicked, id=1)
        self.Bind(wx.EVT_BUTTON, self.help_clicked,  id=2)
        self.Bind(wx.EVT_BUTTON, self.close_clicked, id=3)

        #if not root_test():
        #    self.error_dialog("This program must be run with root permissions!", True)

#---------------------------------------------------------------------------#
# Gui helpers
#---------------------------------------------------------------------------#
# Not callbacks, but used by them
#---------------------------------------------------------------------------#
    def show_buttons(self, state=False, all=0):
        ''' Greys out the buttons '''
        if all:
            self.window.set_sensitive(state)
        self.bstart.set_sensitive(state)
        self.tdevice.set_sensitive(state)
        self.tsubnet.set_sensitive(state)
        self.tnumber.set_sensitive(state)

    def destroy_interfaces(self):
        ''' This is used to reset the virtual interfaces '''
        if self.restart:
            n = NetworkReset()
            n.start()

    def error_dialog(self, message, quit=False):
        ''' Quick pop-up for error messages '''
        log.debug("error event called")
        dialog = wx.MessageDialog(self, message, 'Error',
            wx.OK | wx.ICON_ERROR)
        dialog.ShowModel()
        if quit: self.Destroy()
        dialog.Destroy()

#---------------------------------------------------------------------------#
# Button Actions
#---------------------------------------------------------------------------#
# These are all callbacks for the various buttons
#---------------------------------------------------------------------------#
    def start_clicked(self, widget):
        ''' Starts the simulator '''
        start = 1
        base = "172.16"

        # check starting network
        net = self.tsubnet.get_text()
        octets = net.split('.')
        if len(octets) == 4:
            base = "%s.%s" % (octets[0], octets[1])
            net = int(octets[2]) % 255
            start = int(octets[3]) % 255
        else:
            self.error_dialog("Invalid starting address!");
            return False

        # check interface size
        size = int(self.tnumber.get_text())
        if (size >= 1):
            for i in range(start, (size + start)):
                j = i % 255
                cmd = "/sbin/ifconfig eth0:%d %s.%d.%d" % (i, base, net, j)
                os.system(cmd)
                if j == 254: net = net + 1
            self.restart = 1
        else:
            self.error_dialog("Invalid number of devices!");
            return False

        # check input file
        if os.path.exists(self.file):
            self.show_buttons(state=False)
            try:
                handle = Simulator(config=self.file)
                handle.run()
            except ConfigurationException, ex:
                self.error_dialog("Error %s" % ex)
                self.show_buttons(state=True)
        else:
            self.error_dialog("Device to emulate does not exist!");
            return False

    def help_clicked(self, widget):
        ''' Quick pop-up for about page '''
        data = gtk.AboutDialog()
        data.set_version("0.1")
        data.set_name(('Modbus Simulator'))
        data.set_authors(["Galen Collins"])
        data.set_comments(('First Select a device to simulate,\n'
            + 'then select the starting subnet of the new devices\n'
            + 'then select the number of device to simulate and click start'))
        data.set_website("http://code.google.com/p/pymodbus/")
        data.connect("response", lambda w,r: w.hide())
        data.run()

    def close_clicked(self, event):
        ''' Callback for close button '''
        log.debug("close event called")
        reactor.stop()

    def file_changed(self, event):
        ''' Callback for the filename change '''
        self.file = widget.get_filename()

class SimulatorApp(wx.App):
    ''' The main wx application handle for our simulator
    '''

    def OnInit(self):
        ''' Called by wxWindows to initialize our application

        :returns: Always True
        '''
        log.debug("application initialize event called")
        reactor.registerWxApp(self)
        frame = SimulatorFrame(None, -1, "Pymodbus Simulator")
        frame.CenterOnScreen()
        frame.Show(True)
        self.SetTopWindow(frame)
        return True

#---------------------------------------------------------------------------#
# Main handle function
#---------------------------------------------------------------------------#
# This is called when the application is run from a console
# We simply start the gui and start the twisted event loop
#---------------------------------------------------------------------------#
def main():
    '''
    Main control function
    This either launches the gui or runs the command line application
    '''
    debug = True
    if debug:
        try:
            log.setLevel(logging.DEBUG)
    	    logging.basicConfig()
        except Exception, e:
    	    print "Logging is not supported on this system"
    simulator = SimulatorApp(0)
    reactor.run()

#---------------------------------------------------------------------------#
# Library/Console Test
#---------------------------------------------------------------------------#
# If this is called from console, we start main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = build-datastore
#!/usr/bin/env python
'''
This creates a dummy datastore for use with the modbus simulator.

It is also used to convert datastores to and from a register list
dump.  This allows users to build their own data from scratch or
modifiy an exisiting dump.
'''
import pickle
from sys import exit
from optparse import OptionParser

from pymodbus.datastore import ModbusSequentialDataBlock as seqblock
from pymodbus.datastore import ModbusSparseDataBlock as sparblock

#--------------------------------------------------------------------------#
# Helper Classes
#--------------------------------------------------------------------------#
class ConfigurationException(Exception):
    ''' Exception for configuration error '''

    def __init__(self, string):
        ''' A base string to make pylint happy
        :param string: Additional information to append to exception
        '''
        Exception.__init__(self, string)
        self.string = string

    def __str__(self):
        return 'Configuration Error: %s' % self.string

#--------------------------------------------------------------------------#
# Datablock Builders
#--------------------------------------------------------------------------#
def build_translation(option, opt, value, parser):
    ''' Converts a register dump list to a pickeld datastore

    :param option: The option instance
    :param opt: The option string specified
    :param value: The file to translate
    :param parser: The parser object
    '''
    raise ConfigurationException("This function is not implemented yet")
    try:
        with open(value, "r") as input:
            data = pickle.load(input)
    except:
        raise ConfigurationException("File Not Found %s" % value)

    with open(value + ".trans", "w") as output:
        pass # TODO
    exit() # So we don't start a dummy build

def build_conversion(option, opt, value, parser):
    ''' This converts a pickled datastore to a register dump list

    :param option: The option instance
    :param opt: The option string specified
    :param value: The file to convert
    :param parser: The parser object
    '''
    try:
        with open(value, "r") as input:
            data = pickle.load(input)
    except:
        raise ConfigurationException("File Not Found %s" % value)

    with open(value + ".dump", "w") as output:
        for dk,dv in data.iteritems():
            output.write("[ %s ]\n\n" % dk)

            # handle sequential
            if isinstance(dv.values, list):
                output.write("\n".join(["[%d] = %d" % (vk,vv)
                        for vk,vv in enumerate(dv.values)]))

            # handle sparse
            elif isinstance(data[k].values, dict):
                output.write("\n".join(["[%d] = %d" % (vk,vv)
                        for vk,vv in dv.values.iteritems()]))
            else: raise ConfigurationException("Datastore is corrupted %s" % value)
            output.write("\n\n")
    exit() # So we don't start a dummy build

#--------------------------------------------------------------------------#
# Datablock Builders
#--------------------------------------------------------------------------#
def build_sequential():
    '''
    This builds a quick mock sequential datastore with 100 values for each
    discrete, coils, holding, and input bits/registers.
    '''
    data = {
        'di' : seqblock(0, [bool(x) for x in range(1, 100)]),
        'ci' : seqblock(0, [bool(not x) for x in range(1, 100)]),
        'hr' : seqblock(0, [int(x) for x in range(1, 100)]),
        'ir' : seqblock(0, [int(2*x) for x in range(1, 100)]),
    }
    return data

def build_sparse():
    '''
    This builds a quick mock sparse datastore with 100 values for each
    discrete, coils, holding, and input bits/registers.
    '''
    data = {
        'di' : sparblock([bool(x) for x in range(1, 100)]),
        'ci' : sparblock([bool(not x) for x in range(1, 100)]),
        'hr' : sparblock([int(x) for x in range(1, 100)]),
        'ir' : sparblock([int(2*x) for x in range(1, 100)]),
    }
    return data

def main():
    ''' The main function for this script '''
    parser = OptionParser()
    parser.add_option("-o", "--output",
        help="The output file to write to",
        dest="file", default="example.store")
    parser.add_option("-t", "--type",
        help="The type of block to create (sequential,sparse)",
        dest="type", default="sparse")
    parser.add_option("-c", "--convert",
        help="Convert a file datastore to a register dump",
        type="string",
        action="callback", callback=build_conversion)
    parser.add_option("-r", "--restore",
        help="Convert a register dump to a file datastore",
        type="string",
        action="callback", callback=build_translation)
    try:
        (opt, arg) = parser.parse_args() # so we can catch the csv callback

        if opt.type == "sparse":
            result = build_sparse()
        elif opt.type == "sequential":
            result = build_sequential()
        else:
            raise ConfigurationException("Unknown block type %s" % opt.type)

        with open(opt.file, "w") as output:
            pickle.dump(result, output)
        print "Created datastore: %s\n" % opt.file

    except ConfigurationException, ex:
        print ex
        parser.print_help()

#---------------------------------------------------------------------------#
# Main jumper
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = convert
#!/usr/bin/env python
'''
This script is used to convert an XML dump to a
serialized ModbusDataStore for use with the simulator.

This is used to convert from the nmodbus datastore xml dump
to our modbus pickled version.
'''
from pymodbus.datastore import ModbusSparseDataBlock as sblock
from optparse import OptionParser
from lxml import etree
import pickle

#--------------------------------------------------------------------------#
# Helper Classes
#--------------------------------------------------------------------------#
class ConversionException(Exception):
    ''' Exception for configuration error '''

    def __init__(self, string):
        ''' Initialize a ConversionException instance

        :param string: Additional information to append to exception
        '''
        Exception.__init__(self, string)
        self.string = string

    def __str__(self):
        ''' Builds a string representation of the object

        :returns: The string representation of the object
        '''
        return 'Conversion Error: %s' % self.string

#--------------------------------------------------------------------------#
# Lxml Parser Tree
#--------------------------------------------------------------------------#
class ModbusXML:
    convert = {
        'true':True,
        'false':False,
    }
    lookup = {
        'InputRegisters':'ir',
        'HoldingRegisters':'hr',
        'CoilDiscretes':'ci',
        'InputDiscretes':'di'
    }

    def __init__(self):
        '''
        Initializer for the parser object
        '''
        self.next  = 0
        self.result = {'di':{}, 'ci':{}, 'ir':{}, 'hr':{}}

    def start(self, tag, attrib):
        '''
        Callback for start node
        @param tag The starting tag found
        @param attrib Attributes dict found in the tag
        '''
        if tag == "value":
            try:
                self.next = attrib['index']
            except KeyError: raise ConversionException("Invalid XML: index")
        elif tag in self.lookup:
            self.h = self.result[self.lookup[tag]]

    def end(self, tag):
        '''
        Callback for end node
        @param tag The end tag found
        '''
        pass

    def data(self, data):
        '''
        Callback for node data
        @param data The data for the current node
        '''
        if data in self.convert:
            result = self.convert[data]
        else: result = data
        self.h[self.next] = data

    def comment(self, text):
        '''
        Callback for node data
        @param data The data for the current node
        '''
        pass

    def close(self):
        '''
        Callback for node data
        @param data The data for the current node
        '''
        return self.result

#--------------------------------------------------------------------------#
# Helper Functions
#--------------------------------------------------------------------------#
def store_dump(result, file):
    '''
    Quick function to dump a result to a pickle
    @param result The resulting parsed data
    '''
    result['di'] = sblock(result['di'])
    result['ci'] = sblock(result['ci'])
    result['hr'] = sblock(result['hr'])
    result['ir'] = sblock(result['ir'])

    with open(file, "w") as input:
        pickle.dump(result, input)

def main():
    '''
    The main function for this script
    '''
    parser = OptionParser()
    parser.add_option("-o", "--output",
                    help="The output file to write to",
                    dest="output", default="example.store")
    parser.add_option("-i", "--input",
                    help="File to convert to a datastore",
                    dest="input", default="scrape.xml")
    try:
        (opt, arg) = parser.parse_args()

        parser = etree.XMLParser(target = ModbusXML())
        result = etree.parse(opt.input, parser)
        store_dump(result, opt.output)
        print "Created datastore: %s\n" % opt.output

    except ConversionException, ex:
        print ex
        parser.print_help()

#---------------------------------------------------------------------------#
# Main jumper
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = reindent
#!/usr/bin/python
"""reindent [-d][-r][-v] path ...

-d  Dry run.  Analyze, but don't make any changes to, files.
-r  Recurse.  Search for all .py files in subdirectories too.
-v  Verbose.  Print informative msgs; else no output.

Change Python (.py) files to use 4-space indents and no hard tab characters.
Also trim excess whitespace from ends of lines, and empty lines at the ends
of files.  Ensure the last line ends with a newline.

Pass one or more file and/or directory paths.  When a directory path, all
.py files within the directory will be examined, and, if the -r option is
given, likewise recursively for subdirectories.

Overwrites files in place, renaming the originals with a .bak extension.
If reindent finds nothing to change, the file is left alone.  If reindent
does change a file, the changed file is a fixed-point for reindent (i.e.,
running reindent on the resulting .py file won't change it again).

The hard part of reindenting is figuring out what to do with comment
lines.  So long as the input files get a clean bill of health from
tabnanny.py, reindent should do a good job.
"""

__version__ = "1"

import tokenize
import os
import sys

verbose = 0
recurse = 0
dryrun  = 0

def errprint(*args):
    sep = ""
    for arg in args:
        sys.stderr.write(sep + str(arg))
        sep = " "
    sys.stderr.write("\n")

def main():
    import getopt
    global verbose, recurse, dryrun
    try:
        opts, args = getopt.getopt(sys.argv[1:], "drv")
    except getopt.error, msg:
        errprint(msg)
        return
    for o, a in opts:
        if o == '-d':
            dryrun += 1
        elif o == '-r':
            recurse += 1
        elif o == '-v':
            verbose += 1
    if not args:
        errprint("Usage:", __doc__)
        return
    for arg in args:
        check(arg)

def check(file):
    if os.path.isdir(file) and not os.path.islink(file):
        if verbose:
            print "listing directory", file
        names = os.listdir(file)
        for name in names:
            fullname = os.path.join(file, name)
            if ((recurse and os.path.isdir(fullname) and
                 not os.path.islink(fullname))
                or name.lower().endswith(".py")):
                check(fullname)
        return

    if verbose:
        print "checking", file, "...",
    try:
        f = open(file)
    except IOError, msg:
        errprint("%s: I/O Error: %s" % (file, str(msg)))
        return

    r = Reindenter(f)
    f.close()
    if r.run():
        if verbose:
            print "changed."
            if dryrun:
                print "But this is a dry run, so leaving it alone."
        if not dryrun:
            bak = file + ".bak"
            if os.path.exists(bak):
                os.remove(bak)
            os.rename(file, bak)
            if verbose:
                print "renamed", file, "to", bak
            f = open(file, "w")
            r.write(f)
            f.close()
            if verbose:
                print "wrote new", file
    else:
        if verbose:
            print "unchanged."

class Reindenter:

    def __init__(self, f, eol="\n"):
        self.find_stmt = 1  # next token begins a fresh stmt?
        self.level = 0      # current indent level
        self.eol = eol
        
        # Raw file lines.
        self.raw = f.readlines()

        # File lines, rstripped & tab-expanded.  Dummy at start is so
        # that we can use tokenize's 1-based line numbering easily.
        # Note that a line is all-blank iff it's "\n".
        self.lines = [line.rstrip().expandtabs() + self.eol
                      for line in self.raw]
        self.lines.insert(0, None)
        self.index = 1  # index into self.lines of next line

        # List of (lineno, indentlevel) pairs, one for each stmt and
        # comment line.  indentlevel is -1 for comment lines, as a
        # signal that tokenize doesn't know what to do about them;
        # indeed, they're our headache!
        self.stats = []

    def run(self):
        tokenize.tokenize(self.getline, self.tokeneater)
        # Remove trailing empty lines.
        lines = self.lines
        while lines and lines[-1] == self.eol:
            lines.pop()
        # Sentinel.
        stats = self.stats
        stats.append((len(lines), 0))
        # Map count of leading spaces to # we want.
        have2want = {}
        # Program after transformation.
        after = self.after = []
        for i in range(len(stats)-1):
            thisstmt, thislevel = stats[i]
            nextstmt = stats[i+1][0]
            have = getlspace(lines[thisstmt])
            want = thislevel * 4
            if want < 0:
                # A comment line.
                if have:
                    # An indented comment line.  If we saw the same
                    # indentation before, reuse what it most recently
                    # mapped to.
                    want = have2want.get(have, -1)
                    if want < 0:
                        # Then it probably belongs to the next real stmt.
                        for j in xrange(i+1, len(stats)-1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                if have == getlspace(lines[jline]):
                                    want = jlevel * 4
                                break
                    if want < 0:           # Maybe it's a hanging
                                           # comment like this one,
                        # in which case we should shift it like its base
                        # line got shifted.
                        for j in xrange(i-1, -1, -1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                want = have + getlspace(after[jline-1]) - \
                                       getlspace(lines[jline])
                                break
                    if want < 0:
                        # Still no luck -- leave it alone.
                        want = have
                else:
                    want = 0
            assert want >= 0
            have2want[have] = want
            diff = want - have
            if diff == 0 or have == 0:
                after.extend(lines[thisstmt:nextstmt])
            else:
                for line in lines[thisstmt:nextstmt]:
                    if diff > 0:
                        if line == self.eol:
                            after.append(line)
                        else:
                            after.append(" " * diff + line)
                    else:
                        remove = min(getlspace(line), -diff)
                        after.append(line[remove:])
        return self.raw != self.after

    def write(self, f):
        f.writelines(self.after)

    # Line-getter for tokenize.
    def getline(self):
        if self.index >= len(self.lines):
            line = ""
        else:
            line = self.lines[self.index]
            self.index += 1
        return line

    # Line-eater for tokenize.
    def tokeneater(self, type, token, params, end, line,
                   INDENT=tokenize.INDENT,
                   DEDENT=tokenize.DEDENT,
                   NEWLINE=tokenize.NEWLINE,
                   COMMENT=tokenize.COMMENT,
                   NL=tokenize.NL):
        sline, scol = params
        if type == NEWLINE:
            # A program statement, or ENDMARKER, will eventually follow,
            # after some (possibly empty) run of tokens of the form
            #     (NL | COMMENT)* (INDENT | DEDENT+)?
            self.find_stmt = 1

        elif type == INDENT:
            self.find_stmt = 1
            self.level += 1

        elif type == DEDENT:
            self.find_stmt = 1
            self.level -= 1

        elif type == COMMENT:
            if self.find_stmt:
                self.stats.append((sline, -1))
                # but we're still looking for a new stmt, so leave
                # find_stmt alone

        elif type == NL:
            pass

        elif self.find_stmt:
            # This is the first "real token" following a NEWLINE, so it
            # must be the first token of the next program statement, or an
            # ENDMARKER.
            self.find_stmt = 0
            if line:   # not endmarker
                self.stats.append((sline, self.level))

# Count number of leading blanks.
def getlspace(line):
    i, n = 0, len(line)
    while i < n and line[i] == " ":
        i += 1
    return i

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = pymodbus_plugin
'''
'''
from zope.interface import implements

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet

from pymodbus.constants import Defaults
from pymodbus.server.async import ModbusServerFactory
from pymodbus.transaction import ModbusSocketFramer
from pymodbus.internal.ptwisted import InstallManagementConsole

class Options(usage.Options):
    '''
    The following are the options available to the
    pymodbus server.
    '''
    optParameters = [
        ["port", "p", Defaults.Port, "The port number to listen on."],
        ["type", "t", "tcp", "The type of server to host (tcp, udp, ascii, rtu)"],
        ["store", "s", "./datastore", "The pickled datastore to use"],
        ["console", "c", False, "Should the management console be started"],
    ]

class ModbusServiceMaker(object):
    '''
    A helper class used to build a twisted plugin
    '''
    implements(IServiceMaker, IPlugin)
    tapname = "pymodbus"
    description = "A modbus server"
    options = Options

    def makeService(self, options):
        '''
        Construct a service from the given options
        '''
        if options["type"] == "tcp":
            server = internet.TCPServer
        else: server = internet.UDPServer


        framer = ModbusSocketFramer
        context = self._build_context(options['store'])
        factory = ModbusServerFactory(None, framer)
        if options['console']:
            InstallManagementConsole({ 'server' : factory })
        return server(int(options["port"]), factory)

    def _build_context(self, path):
        '''
        A helper method to unpickle a datastore,
        note, this should be a ModbusServerContext.
        '''
        import pickle
        try:
            context = pickle.load(path)
        except Exception: context = None
        return context

serviceMaker = ModbusServiceMaker()

########NEW FILE########
__FILENAME__ = bit_read_message
"""
Bit Reading Request/Response messages
--------------------------------------

"""
import struct
from pymodbus.pdu import ModbusRequest
from pymodbus.pdu import ModbusResponse
from pymodbus.pdu import ModbusExceptions as merror
from pymodbus.utilities import pack_bitstring, unpack_bitstring


class ReadBitsRequestBase(ModbusRequest):
    ''' Base class for Messages Requesting bit values '''

    _rtu_frame_size = 8

    def __init__(self, address, count, **kwargs):
        ''' Initializes the read request data

        :param address: The start address to read from
        :param count: The number of bits after 'address' to read
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.address = address
        self.count   = count

    def encode(self):
        ''' Encodes a request pdu

        :returns: The encoded pdu
        '''
        return struct.pack('>HH', self.address, self.count)

    def decode(self, data):
        ''' Decodes a request pdu

        :param data: The packet data to decode
        '''
        self.address, self.count = struct.unpack('>HH', data)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "ReadBitRequest(%d,%d)" % (self.address, self.count)


class ReadBitsResponseBase(ModbusResponse):
    ''' Base class for Messages responding to bit-reading values '''

    _rtu_byte_count_pos = 2

    def __init__(self, values, **kwargs):
        ''' Initializes a new instance

        :param values: The requested values to be returned
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.bits = values or []

    def encode(self):
        ''' Encodes response pdu

        :returns: The encoded packet message
        '''
        result = pack_bitstring(self.bits)
        packet = struct.pack(">B", len(result)) + result
        return packet

    def decode(self, data):
        ''' Decodes response pdu

        :param data: The packet data to decode
        '''
        self.byte_count = struct.unpack(">B", data[0])[0]
        self.bits = unpack_bitstring(data[1:])

    def setBit(self, address, value=1):
        ''' Helper function to set the specified bit

        :param address: The bit to set
        :param value: The value to set the bit to
        '''
        self.bits[address] = (value != 0)

    def resetBit(self, address):
        ''' Helper function to set the specified bit to 0

        :param address: The bit to reset
        '''
        self.setBit(address, 0)

    def getBit(self, address):
        ''' Helper function to get the specified bit's value

        :param address: The bit to query
        :returns: The value of the requested bit
        '''
        return self.bits[address]

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "ReadBitResponse(%d)" % len(self.bits)


class ReadCoilsRequest(ReadBitsRequestBase):
    '''
    This function code is used to read from 1 to 2000(0x7d0) contiguous status
    of coils in a remote device. The Request PDU specifies the starting
    address, ie the address of the first coil specified, and the number of
    coils. In the PDU Coils are addressed starting at zero. Therefore coils
    numbered 1-16 are addressed as 0-15.
    '''
    function_code = 1

    def __init__(self, address=None, count=None, **kwargs):
        ''' Initializes a new instance

        :param address: The address to start reading from
        :param count: The number of bits to read
        '''
        ReadBitsRequestBase.__init__(self, address, count, **kwargs)

    def execute(self, context):
        ''' Run a read coils request against a datastore

        Before running the request, we make sure that the request is in
        the max valid range (0x001-0x7d0). Next we make sure that the
        request is valid against the current datastore.

        :param context: The datastore to request from
        :returns: The initializes response message, exception message otherwise
        '''
        if not (1 <= self.count <= 0x7d0):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, self.count):
            return self.doException(merror.IllegalAddress)
        values = context.getValues(self.function_code, self.address, self.count)
        return ReadCoilsResponse(values)


class ReadCoilsResponse(ReadBitsResponseBase):
    '''
    The coils in the response message are packed as one coil per bit of
    the data field. Status is indicated as 1= ON and 0= OFF. The LSB of the
    first data byte contains the output addressed in the query. The other
    coils follow toward the high order end of this byte, and from low order
    to high order in subsequent bytes.

    If the returned output quantity is not a multiple of eight, the
    remaining bits in the final data byte will be padded with zeros
    (toward the high order end of the byte). The Byte Count field specifies
    the quantity of complete bytes of data.
    '''
    function_code = 1

    def __init__(self, values=None, **kwargs):
        ''' Intializes a new instance

        :param values: The request values to respond with
        '''
        ReadBitsResponseBase.__init__(self, values, **kwargs)


class ReadDiscreteInputsRequest(ReadBitsRequestBase):
    '''
    This function code is used to read from 1 to 2000(0x7d0) contiguous status
    of discrete inputs in a remote device. The Request PDU specifies the
    starting address, ie the address of the first input specified, and the
    number of inputs. In the PDU Discrete Inputs are addressed starting at
    zero. Therefore Discrete inputs numbered 1-16 are addressed as 0-15.
    '''
    function_code = 2

    def __init__(self, address=None, count=None, **kwargs):
        ''' Intializes a new instance

        :param address: The address to start reading from
        :param count: The number of bits to read
        '''
        ReadBitsRequestBase.__init__(self, address, count, **kwargs)

    def execute(self, context):
        ''' Run a read discrete input request against a datastore

        Before running the request, we make sure that the request is in
        the max valid range (0x001-0x7d0). Next we make sure that the
        request is valid against the current datastore.

        :param context: The datastore to request from
        :returns: The initializes response message, exception message otherwise
        '''
        if not (1 <= self.count <= 0x7d0):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, self.count):
            return self.doException(merror.IllegalAddress)
        values = context.getValues(self.function_code, self.address, self.count)
        return ReadDiscreteInputsResponse(values)


class ReadDiscreteInputsResponse(ReadBitsResponseBase):
    '''
    The discrete inputs in the response message are packed as one input per
    bit of the data field. Status is indicated as 1= ON; 0= OFF. The LSB of
    the first data byte contains the input addressed in the query. The other
    inputs follow toward the high order end of this byte, and from low order
    to high order in subsequent bytes.

    If the returned input quantity is not a multiple of eight, the
    remaining bits in the final data byte will be padded with zeros
    (toward the high order end of the byte). The Byte Count field specifies
    the quantity of complete bytes of data.
    '''
    function_code = 2

    def __init__(self, values=None, **kwargs):
        ''' Intializes a new instance

        :param values: The request values to respond with
        '''
        ReadBitsResponseBase.__init__(self, values, **kwargs)

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "ReadCoilsRequest", "ReadCoilsResponse",
    "ReadDiscreteInputsRequest", "ReadDiscreteInputsResponse",
]

########NEW FILE########
__FILENAME__ = bit_write_message
"""
Bit Writing Request/Response
------------------------------

TODO write mask request/response
"""
import struct
from pymodbus.constants import ModbusStatus
from pymodbus.pdu import ModbusRequest
from pymodbus.pdu import ModbusResponse
from pymodbus.pdu import ModbusExceptions as merror
from pymodbus.utilities import pack_bitstring, unpack_bitstring

#---------------------------------------------------------------------------#
# Local Constants
#---------------------------------------------------------------------------#
# These are defined in the spec to turn a coil on/off
#---------------------------------------------------------------------------#
_turn_coil_on  = struct.pack(">H", ModbusStatus.On)
_turn_coil_off = struct.pack(">H", ModbusStatus.Off)


class WriteSingleCoilRequest(ModbusRequest):
    '''
    This function code is used to write a single output to either ON or OFF
    in a remote device.

    The requested ON/OFF state is specified by a constant in the request
    data field. A value of FF 00 hex requests the output to be ON. A value
    of 00 00 requests it to be OFF. All other values are illegal and will
    not affect the output.

    The Request PDU specifies the address of the coil to be forced. Coils
    are addressed starting at zero. Therefore coil numbered 1 is addressed
    as 0. The requested ON/OFF state is specified by a constant in the Coil
    Value field. A value of 0XFF00 requests the coil to be ON. A value of
    0X0000 requests the coil to be off. All other values are illegal and
    will not affect the coil.
    '''
    function_code = 5
    _rtu_frame_size = 8

    def __init__(self, address=None, value=None, **kwargs):
        ''' Initializes a new instance

        :param address: The variable address to write
        :param value: The value to write at address
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.address = address
        self.value = bool(value)

    def encode(self):
        ''' Encodes write coil request

        :returns: The byte encoded message
        '''
        result  = struct.pack('>H', self.address)
        if self.value: result += _turn_coil_on
        else: result += _turn_coil_off
        return result

    def decode(self, data):
        ''' Decodes a write coil request

        :param data: The packet data to decode
        '''
        self.address, value = struct.unpack('>HH', data)
        self.value = (value == ModbusStatus.On)

    def execute(self, context):
        ''' Run a write coil request against a datastore

        :param context: The datastore to request from
        :returns: The populated response or exception message
        '''
        #if self.value not in [ModbusStatus.Off, ModbusStatus.On]:
        #    return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, 1):
            return self.doException(merror.IllegalAddress)

        context.setValues(self.function_code, self.address, [self.value])
        values = context.getValues(self.function_code, self.address, 1)
        return WriteSingleCoilResponse(self.address, values[0])

    def __str__(self):
        ''' Returns a string representation of the instance

        :return: A string representation of the instance
        '''
        return "WriteCoilRequest(%d, %s) => " % (self.address, self.value)


class WriteSingleCoilResponse(ModbusResponse):
    '''
    The normal response is an echo of the request, returned after the coil
    state has been written.
    '''
    function_code = 5
    _rtu_frame_size = 8

    def __init__(self, address=None, value=None, **kwargs):
        ''' Initializes a new instance

        :param address: The variable address written to
        :param value: The value written at address
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.address = address
        self.value = value

    def encode(self):
        ''' Encodes write coil response

        :return: The byte encoded message
        '''
        result  = struct.pack('>H', self.address)
        if self.value: result += _turn_coil_on
        else: result += _turn_coil_off
        return result

    def decode(self, data):
        ''' Decodes a write coil response

        :param data: The packet data to decode
        '''
        self.address, value = struct.unpack('>HH', data)
        self.value = (value == ModbusStatus.On)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "WriteCoilResponse(%d) => %d" % (self.address, self.value)


class WriteMultipleCoilsRequest(ModbusRequest):
    '''
    "This function code is used to force each coil in a sequence of coils to
    either ON or OFF in a remote device. The Request PDU specifies the coil
    references to be forced. Coils are addressed starting at zero. Therefore
    coil numbered 1 is addressed as 0.

    The requested ON/OFF states are specified by contents of the request
    data field. A logical '1' in a bit position of the field requests the
    corresponding output to be ON. A logical '0' requests it to be OFF."
    '''
    function_code = 15
    _rtu_byte_count_pos = 6

    def __init__(self, address=None, values=None, **kwargs):
        ''' Initializes a new instance

        :param address: The starting request address
        :param values: The values to write
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.address = address
        if not values: values = []
        elif not hasattr(values, '__iter__'): values = [values]
        self.values  = values
        self.byte_count = (len(self.values) + 7) / 8

    def encode(self):
        ''' Encodes write coils request

        :returns: The byte encoded message
        '''
        count   = len(self.values)
        self.byte_count = (count + 7) / 8
        packet  = struct.pack('>HHB', self.address, count, self.byte_count)
        packet += pack_bitstring(self.values)
        return packet

    def decode(self, data):
        ''' Decodes a write coils request

        :param data: The packet data to decode
        '''
        self.address, count, self.byte_count = struct.unpack('>HHB', data[0:5])
        values = unpack_bitstring(data[5:])
        self.values = values[:count]

    def execute(self, context):
        ''' Run a write coils request against a datastore

        :param context: The datastore to request from
        :returns: The populated response or exception message
        '''
        count = len(self.values)
        if not (1 <= count <= 0x07b0):
            return self.doException(merror.IllegalValue)
        if (self.byte_count != (count + 7) / 8):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, count):
            return self.doException(merror.IllegalAddress)

        context.setValues(self.function_code, self.address, self.values)
        return WriteMultipleCoilsResponse(self.address, count)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        params = (self.address, len(self.values))
        return "WriteNCoilRequest (%d) => %d " % params


class WriteMultipleCoilsResponse(ModbusResponse):
    '''
    The normal response returns the function code, starting address, and
    quantity of coils forced.
    '''
    function_code = 15
    _rtu_frame_size = 8

    def __init__(self, address=None, count=None, **kwargs):
        ''' Initializes a new instance

        :param address: The starting variable address written to
        :param count: The number of values written
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.address = address
        self.count = count

    def encode(self):
        ''' Encodes write coils response

        :returns: The byte encoded message
        '''
        return struct.pack('>HH', self.address, self.count)

    def decode(self, data):
        ''' Decodes a write coils response

        :param data: The packet data to decode
        '''
        self.address, self.count = struct.unpack('>HH', data)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "WriteNCoilResponse(%d, %d)" % (self.address, self.count)

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "WriteSingleCoilRequest", "WriteSingleCoilResponse",
    "WriteMultipleCoilsRequest", "WriteMultipleCoilsResponse",
]

########NEW FILE########
__FILENAME__ = async
"""
Implementation of a Modbus Client Using Twisted
--------------------------------------------------

Example run::

    from twisted.internet import reactor, protocol
    from pymodbus.client.async import ModbusClientProtocol

    def printResult(result):
        print "Result: %d" % result.bits[0]

    def process(client):
        result = client.write_coil(1, True)
        result.addCallback(printResult)
        reactor.callLater(1, reactor.stop)

    defer = protocol.ClientCreator(reactor, ModbusClientProtocol
            ).connectTCP("localhost", 502)
    defer.addCallback(process)

Another example::

    from twisted.internet import reactor
    from pymodbus.client.async import ModbusClientFactory

    def process():
        factory = reactor.connectTCP("localhost", 502, ModbusClientFactory())
        reactor.stop()

    if __name__ == "__main__":
       reactor.callLater(1, process)
       reactor.run()
"""
from twisted.internet import defer, protocol
from pymodbus.factory import ClientDecoder
from pymodbus.exceptions import ConnectionException
from pymodbus.transaction import ModbusSocketFramer
from pymodbus.transaction import FifoTransactionManager
from pymodbus.transaction import DictTransactionManager
from pymodbus.client.common import ModbusClientMixin
from twisted.python.failure import Failure

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Connected Client Protocols
#---------------------------------------------------------------------------#
class ModbusClientProtocol(protocol.Protocol, ModbusClientMixin):
    '''
    This represents the base modbus client protocol.  All the application
    layer code is deferred to a higher level wrapper.
    '''

    def __init__(self, framer=None, **kwargs):
        ''' Initializes the framer module

        :param framer: The framer to use for the protocol
        '''
        self._connected = False
        self.framer = framer or ModbusSocketFramer(ClientDecoder())
        if isinstance(self.framer, ModbusSocketFramer):
            self.transaction = DictTransactionManager(self, **kwargs)
        else: self.transaction = FifoTransactionManager(self, **kwargs)

    def connectionMade(self):
        ''' Called upon a successful client connection.
        '''
        _logger.debug("Client connected to modbus server")
        self._connected = True

    def connectionLost(self, reason):
        ''' Called upon a client disconnect

        :param reason: The reason for the disconnect
        '''
        _logger.debug("Client disconnected from modbus server: %s" % reason)
        self._connected = False
        for tid in self.transaction:
            self.transaction.getTransaction(tid).errback(Failure(
                ConnectionException('Connection lost during request')))

    def dataReceived(self, data):
        ''' Get response, check for valid message, decode result

        :param data: The data returned from the server
        '''
        self.framer.processIncomingPacket(data, self._handleResponse)

    def execute(self, request):
        ''' Starts the producer to send the next request to
        consumer.write(Frame(request))
        '''
        request.transaction_id = self.transaction.getNextTID()
        packet = self.framer.buildPacket(request)
        self.transport.write(packet)
        return self._buildResponse(request.transaction_id)

    def _handleResponse(self, reply):
        ''' Handle the processed response and link to correct deferred

        :param reply: The reply to process
        '''
        if reply is not None:
            tid = reply.transaction_id
            handler = self.transaction.getTransaction(tid)
            if handler:
                handler.callback(reply)
            else: _logger.debug("Unrequested message: " + str(reply))

    def _buildResponse(self, tid):
        ''' Helper method to return a deferred response
        for the current request.

        :param tid: The transaction identifier for this response
        :returns: A defer linked to the latest request
        '''
        if not self._connected:
            return defer.fail(Failure(
                ConnectionException('Client is not connected')))

        d = defer.Deferred()
        self.transaction.addTransaction(d, tid)
        return d

    #----------------------------------------------------------------------#
    # Extra Functions
    #----------------------------------------------------------------------#
    #if send_failed:
    #       if self.retry > 0:
    #               deferLater(clock, self.delay, send, message)
    #               self.retry -= 1


#---------------------------------------------------------------------------#
# Not Connected Client Protocol
#---------------------------------------------------------------------------#
class ModbusUdpClientProtocol(protocol.DatagramProtocol, ModbusClientMixin):
    '''
    This represents the base modbus client protocol.  All the application
    layer code is deferred to a higher level wrapper.
    '''

    def __init__(self, framer=None, **kwargs):
        ''' Initializes the framer module

        :param framer: The framer to use for the protocol
        '''
        self.framer = framer or ModbusSocketFramer(ClientDecoder())
        if isinstance(self.framer, ModbusSocketFramer):
            self.transaction = DictTransactionManager(self, **kwargs)
        else: self.transaction = FifoTransactionManager(self, **kwargs)

    def datagramReceived(self, data, params):
        ''' Get response, check for valid message, decode result

        :param data: The data returned from the server
        :param params: The host parameters sending the datagram
        '''
        _logger.debug("Datagram from: %s:%d" % params)
        self.framer.processIncomingPacket(data, self._handleResponse)

    def execute(self, request):
        ''' Starts the producer to send the next request to
        consumer.write(Frame(request))
        '''
        request.transaction_id = self.transaction.getNextTID()
        packet = self.framer.buildPacket(request)
        self.transport.write(packet)
        return self._buildResponse(request.transaction_id)

    def _handleResponse(self, reply):
        ''' Handle the processed response and link to correct deferred

        :param reply: The reply to process
        '''
        if reply is not None:
            tid = reply.transaction_id
            handler = self.transaction.getTransaction(tid)
            if handler:
                handler.callback(reply)
            else: _logger.debug("Unrequested message: " + str(reply))

    def _buildResponse(self, tid):
        ''' Helper method to return a deferred response
        for the current request.

        :param tid: The transaction identifier for this response
        :returns: A defer linked to the latest request
        '''
        d = defer.Deferred()
        self.transaction.addTransaction(d, tid)
        return d


#---------------------------------------------------------------------------#
# Client Factories
#---------------------------------------------------------------------------#
class ModbusClientFactory(protocol.ReconnectingClientFactory):
    ''' Simple client protocol factory '''

    protocol = ModbusClientProtocol

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "ModbusClientProtocol", "ModbusUdpClientProtocol",
    "ModbusClientFactory",
]

########NEW FILE########
__FILENAME__ = common
'''
Modbus Client Common
----------------------------------

This is a common client mixin that can be used by
both the synchronous and asynchronous clients to
simplify the interface.
'''
from pymodbus.bit_read_message import *
from pymodbus.bit_write_message import *
from pymodbus.register_read_message import *
from pymodbus.register_write_message import *
from pymodbus.diag_message import *
from pymodbus.file_message import *
from pymodbus.other_message import *


class ModbusClientMixin(object):
    '''
    This is a modbus client mixin that provides additional factory
    methods for all the current modbus methods. This can be used
    instead of the normal pattern of::

       # instead of this
       client = ModbusClient(...)
       request = ReadCoilsRequest(1,10)
       response = client.execute(request)

       # now like this
       client = ModbusClient(...)
       response = client.read_coils(1, 10)
    '''

    def read_coils(self, address, count=1, **kwargs):
        '''

        :param address: The starting address to read from
        :param count: The number of coils to read
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = ReadCoilsRequest(address, count, **kwargs)
        return self.execute(request)

    def read_discrete_inputs(self, address, count=1, **kwargs):
        '''

        :param address: The starting address to read from
        :param count: The number of discretes to read
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = ReadDiscreteInputsRequest(address, count, **kwargs)
        return self.execute(request)

    def write_coil(self, address, value, **kwargs):
        '''

        :param address: The starting address to write to
        :param value: The value to write to the specified address
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = WriteSingleCoilRequest(address, value, **kwargs)
        return self.execute(request)

    def write_coils(self, address, values, **kwargs):
        '''

        :param address: The starting address to write to
        :param values: The values to write to the specified address
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = WriteMultipleCoilsRequest(address, values, **kwargs)
        return self.execute(request)

    def write_register(self, address, value, **kwargs):
        '''

        :param address: The starting address to write to
        :param value: The value to write to the specified address
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = WriteSingleRegisterRequest(address, value, **kwargs)
        return self.execute(request)

    def write_registers(self, address, values, **kwargs):
        '''

        :param address: The starting address to write to
        :param values: The values to write to the specified address
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = WriteMultipleRegistersRequest(address, values, **kwargs)
        return self.execute(request)

    def read_holding_registers(self, address, count=1, **kwargs):
        '''

        :param address: The starting address to read from
        :param count: The number of registers to read
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = ReadHoldingRegistersRequest(address, count, **kwargs)
        return self.execute(request)

    def read_input_registers(self, address, count=1, **kwargs):
        '''

        :param address: The starting address to read from
        :param count: The number of registers to read
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = ReadInputRegistersRequest(address, count, **kwargs)
        return self.execute(request)

    def readwrite_registers(self, *args, **kwargs):
        '''

        :param read_address: The address to start reading from
        :param read_count: The number of registers to read from address
        :param write_address: The address to start writing to
        :param write_registers: The registers to write to the specified address
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = ReadWriteMultipleRegistersRequest(*args, **kwargs)
        return self.execute(request)

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [ 'ModbusClientMixin' ]

########NEW FILE########
__FILENAME__ = sync
import socket
import serial

from pymodbus.constants import Defaults
from pymodbus.factory import ClientDecoder
from pymodbus.exceptions import NotImplementedException, ParameterException
from pymodbus.exceptions import ConnectionException
from pymodbus.transaction import FifoTransactionManager
from pymodbus.transaction import DictTransactionManager
from pymodbus.transaction import ModbusSocketFramer, ModbusBinaryFramer
from pymodbus.transaction import ModbusAsciiFramer, ModbusRtuFramer
from pymodbus.client.common import ModbusClientMixin

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# The Synchronous Clients
#---------------------------------------------------------------------------#
class BaseModbusClient(ModbusClientMixin):
    '''
    Inteface for a modbus synchronous client. Defined here are all the
    methods for performing the related request methods.  Derived classes
    simply need to implement the transport methods and set the correct
    framer.
    '''

    def __init__(self, framer, **kwargs):
        ''' Initialize a client instance

        :param framer: The modbus framer implementation to use
        '''
        self.framer = framer
        if isinstance(self.framer, ModbusSocketFramer):
            self.transaction = DictTransactionManager(self, **kwargs)
        else: self.transaction = FifoTransactionManager(self, **kwargs)

    #-----------------------------------------------------------------------#
    # Client interface
    #-----------------------------------------------------------------------#
    def connect(self):
        ''' Connect to the modbus remote host

        :returns: True if connection succeeded, False otherwise
        '''
        raise NotImplementedException("Method not implemented by derived class")

    def close(self):
        ''' Closes the underlying socket connection
        '''
        pass

    def _send(self, request):
        ''' Sends data on the underlying socket

        :param request: The encoded request to send
        :return: The number of bytes written
        '''
        raise NotImplementedException("Method not implemented by derived class")

    def _recv(self, size):
        ''' Reads data from the underlying descriptor

        :param size: The number of bytes to read
        :return: The bytes read
        '''
        raise NotImplementedException("Method not implemented by derived class")

    #-----------------------------------------------------------------------#
    # Modbus client methods
    #-----------------------------------------------------------------------#
    def execute(self, request=None):
        '''
        :param request: The request to process
        :returns: The result of the request execution
        '''
        if not self.connect():
            raise ConnectionException("Failed to connect[%s]" % (self.__str__()))
        return self.transaction.execute(request)

    #-----------------------------------------------------------------------#
    # The magic methods
    #-----------------------------------------------------------------------#
    def __enter__(self):
        ''' Implement the client with enter block

        :returns: The current instance of the client
        '''
        if not self.connect():
            raise ConnectionException("Failed to connect[%s]" % (self.__str__()))
        return self

    def __exit__(self, klass, value, traceback):
        ''' Implement the client with exit block '''
        self.close()

    def __str__(self):
        ''' Builds a string representation of the connection

        :returns: The string representation
        '''
        return "Null Transport"


#---------------------------------------------------------------------------#
# Modbus TCP Client Transport Implementation
#---------------------------------------------------------------------------#
class ModbusTcpClient(BaseModbusClient):
    ''' Implementation of a modbus tcp client
    '''

    def __init__(self, host='127.0.0.1', port=Defaults.Port,
        framer=ModbusSocketFramer, **kwargs):
        ''' Initialize a client instance

        :param host: The host to connect to (default 127.0.0.1)
        :param port: The modbus port to connect to (default 502)
        :param source_address: The source address tuple to bind to (default ('', 0))
        :param framer: The modbus framer to use (default ModbusSocketFramer)

        .. note:: The host argument will accept ipv4 and ipv6 hosts
        '''
        self.host = host
        self.port = port
        self.source_address = kwargs.get('source_address', ('', 0))
        self.socket = None
        BaseModbusClient.__init__(self, framer(ClientDecoder()), **kwargs)

    def connect(self):
        ''' Connect to the modbus tcp server

        :returns: True if connection succeeded, False otherwise
        '''
        if self.socket: return True
        try:
            address = (self.host, self.port)
            self.socket = socket.create_connection((self.host, self.port),
                timeout=Defaults.Timeout, source_address=self.source_address)
        except socket.error, msg:
            _logger.error('Connection to (%s, %s) failed: %s' % \
                (self.host, self.port, msg))
            self.close()
        return self.socket != None

    def close(self):
        ''' Closes the underlying socket connection
        '''
        if self.socket:
            self.socket.close()
        self.socket = None

    def _send(self, request):
        ''' Sends data on the underlying socket

        :param request: The encoded request to send
        :return: The number of bytes written
        '''
        if not self.socket:
            raise ConnectionException(self.__str__())
        if request:
            return self.socket.send(request)
        return 0

    def _recv(self, size):
        ''' Reads data from the underlying descriptor

        :param size: The number of bytes to read
        :return: The bytes read
        '''
        if not self.socket:
            raise ConnectionException(self.__str__())
        return self.socket.recv(size)

    def __str__(self):
        ''' Builds a string representation of the connection

        :returns: The string representation
        '''
        return "%s:%s" % (self.host, self.port)


#---------------------------------------------------------------------------#
# Modbus UDP Client Transport Implementation
#---------------------------------------------------------------------------#
class ModbusUdpClient(BaseModbusClient):
    ''' Implementation of a modbus udp client
    '''

    def __init__(self, host='127.0.0.1', port=Defaults.Port,
        framer=ModbusSocketFramer, **kwargs):
        ''' Initialize a client instance

        :param host: The host to connect to (default 127.0.0.1)
        :param port: The modbus port to connect to (default 502)
        :param framer: The modbus framer to use (default ModbusSocketFramer)
        '''
        self.host = host
        self.port = port
        self.socket = None
        BaseModbusClient.__init__(self, framer(ClientDecoder()), **kwargs)

    @classmethod
    def _get_address_family(cls, address):
        ''' A helper method to get the correct address family
        for a given address.

        :param address: The address to get the af for
        :returns: AF_INET for ipv4 and AF_INET6 for ipv6
        '''
        try:
            _ = socket.inet_pton(socket.AF_INET6, address)
        except socket.error: # not a valid ipv6 address
            return socket.AF_INET
        return socket.AF_INET6

    def connect(self):
        ''' Connect to the modbus tcp server

        :returns: True if connection succeeded, False otherwise
        '''
        if self.socket: return True
        try:
            family = ModbusUdpClient._get_address_family(self.host)
            self.socket = socket.socket(family, socket.SOCK_DGRAM)
        except socket.error, ex:
            _logger.error('Unable to create udp socket %s' % ex)
            self.close()
        return self.socket != None

    def close(self):
        ''' Closes the underlying socket connection
        '''
        self.socket = None

    def _send(self, request):
        ''' Sends data on the underlying socket

        :param request: The encoded request to send
        :return: The number of bytes written
        '''
        if not self.socket:
            raise ConnectionException(self.__str__())
        if request:
            return self.socket.sendto(request, (self.host, self.port))
        return 0

    def _recv(self, size):
        ''' Reads data from the underlying descriptor

        :param size: The number of bytes to read
        :return: The bytes read
        '''
        if not self.socket:
            raise ConnectionException(self.__str__())
        return self.socket.recvfrom(size)[0]

    def __str__(self):
        ''' Builds a string representation of the connection

        :returns: The string representation
        '''
        return "%s:%s" % (self.host, self.port)


#---------------------------------------------------------------------------#
# Modbus Serial Client Transport Implementation
#---------------------------------------------------------------------------#
class ModbusSerialClient(BaseModbusClient):
    ''' Implementation of a modbus serial client
    '''

    def __init__(self, method='ascii', **kwargs):
        ''' Initialize a serial client instance

        The methods to connect are::

          - ascii
          - rtu
          - binary

        :param method: The method to use for connection
        :param port: The serial port to attach to
        :param stopbits: The number of stop bits to use
        :param bytesize: The bytesize of the serial messages
        :param parity: Which kind of parity to use
        :param baudrate: The baud rate to use for the serial device
        :param timeout: The timeout between serial requests (default 3s)
        '''
        self.method   = method
        self.socket   = None
        BaseModbusClient.__init__(self, self.__implementation(method), **kwargs)

        self.port     = kwargs.get('port', 0)
        self.stopbits = kwargs.get('stopbits', Defaults.Stopbits)
        self.bytesize = kwargs.get('bytesize', Defaults.Bytesize)
        self.parity   = kwargs.get('parity',   Defaults.Parity)
        self.baudrate = kwargs.get('baudrate', Defaults.Baudrate)
        self.timeout  = kwargs.get('timeout',  Defaults.Timeout)

    @staticmethod
    def __implementation(method):
        ''' Returns the requested framer

        :method: The serial framer to instantiate
        :returns: The requested serial framer
        '''
        method = method.lower()
        if   method == 'ascii':  return ModbusAsciiFramer(ClientDecoder())
        elif method == 'rtu':    return ModbusRtuFramer(ClientDecoder())
        elif method == 'binary': return ModbusBinaryFramer(ClientDecoder())
        elif method == 'socket': return ModbusSocketFramer(ClientDecoder())
        raise ParameterException("Invalid framer method requested")

    def connect(self):
        ''' Connect to the modbus serial server

        :returns: True if connection succeeded, False otherwise
        '''
        if self.socket: return True
        try:
            self.socket = serial.Serial(port=self.port, timeout=self.timeout,
                bytesize=self.bytesize, stopbits=self.stopbits,
                baudrate=self.baudrate, parity=self.parity)
        except serial.SerialException, msg:
            _logger.error(msg)
            self.close()
        return self.socket != None

    def close(self):
        ''' Closes the underlying socket connection
        '''
        if self.socket:
            self.socket.close()
        self.socket = None

    def _send(self, request):
        ''' Sends data on the underlying socket

        :param request: The encoded request to send
        :return: The number of bytes written
        '''
        if not self.socket:
            raise ConnectionException(self.__str__())
        if request:
            return self.socket.write(request)
        return 0

    def _recv(self, size):
        ''' Reads data from the underlying descriptor

        :param size: The number of bytes to read
        :return: The bytes read
        '''
        if not self.socket:
            raise ConnectionException(self.__str__())
        return self.socket.read(size)

    def __str__(self):
        ''' Builds a string representation of the connection

        :returns: The string representation
        '''
        return "%s baud[%s]" % (self.method, self.baudrate)

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "ModbusTcpClient", "ModbusUdpClient", "ModbusSerialClient"
]

########NEW FILE########
__FILENAME__ = constants
'''
Constants For Modbus Server/Client
----------------------------------

This is the single location for storing default
values for the servers and clients.
'''
from pymodbus.interfaces import Singleton


class Defaults(Singleton):
    ''' A collection of modbus default values

    .. attribute:: Port

       The default modbus tcp server port (502)

    .. attribute:: Retries

       The default number of times a client should retry the given
       request before failing (3)

    .. attribute:: RetryOnEmpty

       A flag indicating if a transaction should be retried in the
       case that an empty response is received. This is useful for
       slow clients that may need more time to process a requst.

    .. attribute:: Timeout

       The default amount of time a client should wait for a request
       to be processed (3 seconds)

    .. attribute:: Reconnects

       The default number of times a client should attempt to reconnect
       before deciding the server is down (0)

    .. attribute:: TransactionId

       The starting transaction identifier number (0)

    .. attribute:: ProtocolId

       The modbus protocol id.  Currently this is set to 0 in all
       but proprietary implementations.

    .. attribute:: UnitId

       The modbus slave addrss.  Currently this is set to 0x00 which
       means this request should be broadcast to all the slave devices
       (really means that all the devices should respons).

    .. attribute:: Baudrate

       The speed at which the data is transmitted over the serial line.
       This defaults to 19200.

    .. attribute:: Parity

       The type of checksum to use to verify data integrity. This can be
       on of the following::

         - (E)ven - 1 0 1 0 | P(0)
         - (O)dd  - 1 0 1 0 | P(1)
         - (N)one - 1 0 1 0 | no parity

       This defaults to (N)one.

    .. attribute:: Bytesize

       The number of bits in a byte of serial data.  This can be one of
       5, 6, 7, or 8. This defaults to 8.

    .. attribute:: Stopbits

       The number of bits sent after each character in a message to
       indicate the end of the byte.  This defaults to 1.
    '''
    Port          = 502
    Retries       = 3
    RetryOnEmpty  = False
    Timeout       = 3
    Reconnects    = 0
    TransactionId = 0
    ProtocolId    = 0
    UnitId        = 0x00
    Baudrate      = 19200
    Parity        = 'N'
    Bytesize      = 8
    Stopbits      = 1


class ModbusStatus(Singleton):
    '''
    These represent various status codes in the modbus
    protocol.

    .. attribute:: Waiting

       This indicates that a modbus device is currently
       waiting for a given request to finish some running task.

    .. attribute:: Ready

       This indicates that a modbus device is currently
       free to perform the next request task.

    .. attribute:: On

       This indicates that the given modbus entity is on

    .. attribute:: Off

       This indicates that the given modbus entity is off

    .. attribute:: SlaveOn

       This indicates that the given modbus slave is running

    .. attribute:: SlaveOff

       This indicates that the given modbus slave is not running
    '''
    Waiting  = 0xffff
    Ready    = 0x0000
    On       = 0xff00
    Off      = 0x0000
    SlaveOn  = 0xff
    SlaveOff = 0x00


class Endian(Singleton):
    ''' An enumeration representing the various byte endianess.

    .. attribute:: Auto

       This indicates that the byte order is chosen by the
       current native environment.

    .. attribute:: Big

       This indicates that the bytes are in little endian format

    .. attribute:: Little

       This indicates that the bytes are in big endian format

    .. note:: I am simply borrowing the format strings from the
       python struct module for my convenience.
    '''
    Auto   = '@'
    Big    = '>'
    Little = '<'


class ModbusPlusOperation(Singleton):
    ''' Represents the type of modbus plus request

    .. attribute:: GetStatistics

       Operation requesting that the current modbus plus statistics
       be returned in the response.

    .. attribute:: ClearStatistics

       Operation requesting that the current modbus plus statistics
       be cleared and not returned in the response.
    '''
    GetStatistics   = 0x0003
    ClearStatistics = 0x0004


class DeviceInformation(Singleton):
    ''' Represents what type of device information to read

    .. attribute:: Basic

       This is the basic (required) device information to be returned.
       This includes VendorName, ProductCode, and MajorMinorRevision
       code.

    .. attribute:: Regular

       In addition to basic data objects, the device provides additional
       and optinoal identification and description data objects. All of
       the objects of this category are defined in the standard but their
       implementation is optional.

    .. attribute:: Extended

       In addition to regular data objects, the device provides additional
       and optional identification and description private data about the
       physical device itself. All of these data are device dependent.

    .. attribute:: Specific

       Request to return a single data object.
    '''
    Basic    = 0x01
    Regular  = 0x02
    Extended = 0x03
    Specific = 0x04


class MoreData(Singleton):
    ''' Represents the more follows condition

    .. attribute:: Nothing

       This indiates that no more objects are going to be returned.

    .. attribute:: KeepReading

       This indicates that there are more objects to be returned.
    '''
    Nothing     = 0x00
    KeepReading = 0xFF

#---------------------------------------------------------------------------#
# Exported Identifiers
#---------------------------------------------------------------------------#
__all__ = [
    "Defaults", "ModbusStatus", "Endian",
    "ModbusPlusOperation",
    "DeviceInformation", "MoreData",
]

########NEW FILE########
__FILENAME__ = context
from pymodbus.exceptions import ParameterException
from pymodbus.interfaces import IModbusSlaveContext
from pymodbus.datastore.store import ModbusSequentialDataBlock
from pymodbus.constants import Defaults

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging;
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Slave Contexts
#---------------------------------------------------------------------------#
class ModbusSlaveContext(IModbusSlaveContext):
    '''
    This creates a modbus data model with each data access
    stored in its own personal block
    '''

    def __init__(self, *args, **kwargs):
        ''' Initializes the datastores, defaults to fully populated
        sequential data blocks if none are passed in.

        :param kwargs: Each element is a ModbusDataBlock

            'di' - Discrete Inputs initializer
            'co' - Coils initializer
            'hr' - Holding Register initializer
            'ir' - Input Registers iniatializer
        '''
        self.store = {}
        self.store['d'] = kwargs.get('di', ModbusSequentialDataBlock.create())
        self.store['c'] = kwargs.get('co', ModbusSequentialDataBlock.create())
        self.store['i'] = kwargs.get('ir', ModbusSequentialDataBlock.create())
        self.store['h'] = kwargs.get('hr', ModbusSequentialDataBlock.create())

    def __str__(self):
        ''' Returns a string representation of the context

        :returns: A string representation of the context
        '''
        return "Modbus Slave Context"

    def reset(self):
        ''' Resets all the datastores to their default values '''
        for datastore in self.store.itervalues():
            datastore.reset()

    def validate(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to test
        :returns: True if the request in within range, False otherwise
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("validate[%d] %d:%d" % (fx, address, count))
        return self.store[self.decode(fx)].validate(address, count)

    def getValues(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("getValues[%d] %d:%d" % (fx, address, count))
        return self.store[self.decode(fx)].getValues(address, count)

    def setValues(self, fx, address, values):
        ''' Sets the datastore with the supplied values

        :param fx: The function we are working with
        :param address: The starting address
        :param values: The new values to be set
        '''
        address = address + 1  # section 4.4 of specification
        _logger.debug("setValues[%d] %d:%d" % (fx, address, len(values)))
        self.store[self.decode(fx)].setValues(address, values)


class ModbusServerContext(object):
    ''' This represents a master collection of slave contexts.
    If single is set to true, it will be treated as a single
    context so every unit-id returns the same context. If single
    is set to false, it will be interpreted as a collection of
    slave contexts.
    '''

    def __init__(self, slaves=None, single=True):
        ''' Initializes a new instance of a modbus server context.

        :param slaves: A dictionary of client contexts
        :param single: Set to true to treat this as a single context
        '''
        self.single   = single
        self.__slaves = slaves or {}
        if self.single:
            self.__slaves = {Defaults.UnitId: self.__slaves}

    def __iter__(self):
        ''' Iterater over the current collection of slave
        contexts.

        :returns: An iterator over the slave contexts
        '''
        return self.__slaves.iteritems()

    def __contains__(self, slave):
        ''' Check if the given slave is in this list

        :param slave: slave The slave to check for existance
        :returns: True if the slave exists, False otherwise
        '''
        return slave in self.__slaves

    def __setitem__(self, slave, context):
        ''' Used to set a new slave context

        :param slave: The slave context to set
        :param context: The new context to set for this slave
        '''
        if self.single: slave = Defaults.UnitId
        if 0xf7 >= slave >= 0x00:
            self.__slaves[slave] = context
        else: raise ParameterException('slave index out of range')

    def __delitem__(self, slave):
        ''' Wrapper used to access the slave context

        :param slave: The slave context to remove
        '''
        if not self.single and (0xf7 >= slave >= 0x00):
            del self.__slaves[slave]
        else: raise ParameterException('slave index out of range')

    def __getitem__(self, slave):
        ''' Used to get access to a slave context

        :param slave: The slave context to get
        :returns: The requested slave context
        '''
        if self.single: slave = Defaults.UnitId
        if slave in self.__slaves:
            return self.__slaves.get(slave)
        else: raise ParameterException("slave does not exist, or is out of range")

########NEW FILE########
__FILENAME__ = remote
from pymodbus.exceptions import NotImplementedException
from pymodbus.interfaces import IModbusSlaveContext

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Context
#---------------------------------------------------------------------------#
class RemoteSlaveContext(IModbusSlaveContext):
    ''' TODO
    This creates a modbus data model that connects to
    a remote device (depending on the client used)
    '''

    def __init__(self, client):
        ''' Initializes the datastores

        :param client: The client to retrieve values with
        '''
        self._client = client
        self.__build_mapping()

    def reset(self):
        ''' Resets all the datastores to their default values '''
        raise NotImplementedException()

    def validate(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to test
        :returns: True if the request in within range, False otherwise
        '''
        _logger.debug("validate[%d] %d:%d" % (fx, address, count))
        result = self.__get_callbacks[self.decode(fx)](address, count)
        return result.function_code < 0x80

    def getValues(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        # TODO deal with deferreds
        _logger.debug("get values[%d] %d:%d" % (fx, address, count))
        result = self.__get_callbacks[self.decode(fx)](address, count)
        return self.__extract_result(self.decode(fx), result)

    def setValues(self, fx, address, values):
        ''' Sets the datastore with the supplied values

        :param fx: The function we are working with
        :param address: The starting address
        :param values: The new values to be set
        '''
        # TODO deal with deferreds
        _logger.debug("set values[%d] %d:%d" % (fx, address, len(values)))
        self.__set_callbacks[self.decode(fx)](address, values)

    def __str__(self):
        ''' Returns a string representation of the context

        :returns: A string representation of the context
        '''
        return "Remote Slave Context(%s)" % self._client

    def __build_mapping(self):
        '''
        A quick helper method to build the function
        code mapper.
        '''
        self.__get_callbacks = {
            'd': lambda a, c: self._client.read_discrete_inputs(a, c),
            'c': lambda a, c: self._client.read_coils(a, c),
            'h': lambda a, c: self._client.read_holding_registers(a, c),
            'i': lambda a, c: self._client.read_input_registers(a, c),
        }
        self.__set_callbacks = {
            'd': lambda a, v: self._client.write_coils(a, v),
            'c': lambda a, v: self._client.write_coils(a, v),
            'h': lambda a, v: self._client.write_registers(a, v),
            'i': lambda a, v: self._client.write_registers(a, v),
        }

    def __extract_result(self, fx, result):
        ''' A helper method to extract the values out of
        a response.  TODO make this consistent (values?)
        '''
        if result.function_code < 0x80:
            if fx in ['d', 'c']: return result.bits
            if fx in ['h', 'i']: return result.registers
        else: return result

########NEW FILE########
__FILENAME__ = store
"""
Modbus Server Datastore
-------------------------

For each server, you will create a ModbusServerContext and pass
in the default address space for each data access.  The class
will create and manage the data.

Further modification of said data accesses should be performed
with [get,set][access]Values(address, count)

Datastore Implementation
-------------------------

There are two ways that the server datastore can be implemented.
The first is a complete range from 'address' start to 'count'
number of indecies.  This can be thought of as a straight array::

    data = range(1, 1 + count)
    [1,2,3,...,count]

The other way that the datastore can be implemented (and how
many devices implement it) is a associate-array::

    data = {1:'1', 3:'3', ..., count:'count'}
    [1,3,...,count]

The difference between the two is that the latter will allow
arbitrary gaps in its datastore while the former will not.
This is seen quite commonly in some modbus implementations.
What follows is a clear example from the field:

Say a company makes two devices to monitor power usage on a rack.
One works with three-phase and the other with a single phase. The
company will dictate a modbus data mapping such that registers::

    n:      phase 1 power
    n+1:    phase 2 power
    n+2:    phase 3 power

Using this, layout, the first device will implement n, n+1, and n+2,
however, the second device may set the latter two values to 0 or
will simply not implmented the registers thus causing a single read
or a range read to fail.

I have both methods implemented, and leave it up to the user to change
based on their preference.
"""
from pymodbus.exceptions import NotImplementedException, ParameterException

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Datablock Storage
#---------------------------------------------------------------------------#
class BaseModbusDataBlock(object):
    '''
    Base class for a modbus datastore

    Derived classes must create the following fields:
            @address The starting address point
            @defult_value The default value of the datastore
            @values The actual datastore values

    Derived classes must implemented the following methods:
            validate(self, address, count=1)
            getValues(self, address, count=1)
            setValues(self, address, values)
    '''

    def default(self, count, value=False):
        ''' Used to initialize a store to one value

        :param count: The number of fields to set
        :param value: The default value to set to the fields
        '''
        self.default_value = value
        self.values = [self.default_value] * count
        self.address = 0x00

    def reset(self):
        ''' Resets the datastore to the initialized default value '''
        self.values = [self.default_value] * len(self.values)

    def validate(self, address, count=1):
        ''' Checks to see if the request is in range

        :param address: The starting address
        :param count: The number of values to test for
        :returns: True if the request in within range, False otherwise
        '''
        raise NotImplementedException("Datastore Address Check")

    def getValues(self, address, count=1):
        ''' Returns the requested values from the datastore

        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        raise NotImplementedException("Datastore Value Retrieve")

    def setValues(self, address, values):
        ''' Returns the requested values from the datastore

        :param address: The starting address
        :param values: The values to store
        '''
        raise NotImplementedException("Datastore Value Retrieve")

    def __str__(self):
        ''' Build a representation of the datastore

        :returns: A string representation of the datastore
        '''
        return "DataStore(%d, %d)" % (len(self.values), self.default_value)

    def __iter__(self):
        ''' Iterater over the data block data

        :returns: An iterator of the data block data
        '''
        if isinstance(self.values, dict):
            return self.values.iteritems()
        return enumerate(self.values, self.address)


class ModbusSequentialDataBlock(BaseModbusDataBlock):
    ''' Creates a sequential modbus datastore '''

    def __init__(self, address, values):
        ''' Initializes the datastore

        :param address: The starting address of the datastore
        :param values: Either a list or a dictionary of values
        '''
        self.address = address
        if hasattr(values, '__iter__'):
            self.values = list(values)
        else: self.values = [values]
        self.default_value = self.values[0].__class__()

    @classmethod
    def create(klass):
        ''' Factory method to create a datastore with the
        full address space initialized to 0x00

        :returns: An initialized datastore
        '''
        return klass(0x00, [0x00] * 65536)

    def validate(self, address, count=1):
        ''' Checks to see if the request is in range

        :param address: The starting address
        :param count: The number of values to test for
        :returns: True if the request in within range, False otherwise
        '''
        result  = (self.address <= address)
        result &= ((self.address + len(self.values)) >= (address + count))
        return result

    def getValues(self, address, count=1):
        ''' Returns the requested values of the datastore

        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        start = address - self.address
        return self.values[start:start + count]

    def setValues(self, address, values):
        ''' Sets the requested values of the datastore

        :param address: The starting address
        :param values: The new values to be set
        '''
        if not isinstance(values, list):
            values = [values]
        start = address - self.address
        self.values[start:start + len(values)] = values


class ModbusSparseDataBlock(BaseModbusDataBlock):
    ''' Creates a sparse modbus datastore '''

    def __init__(self, values):
        ''' Initializes the datastore

        Using the input values we create the default
        datastore value and the starting address

        :param values: Either a list or a dictionary of values
        '''
        if isinstance(values, dict):
            self.values = values
        elif hasattr(values, '__iter__'):
            self.values = dict(enumerate(values))
        else: raise ParameterException(
            "Values for datastore must be a list or dictionary")
        self.default_value = self.values.itervalues().next().__class__()
        self.address = self.values.iterkeys().next()

    @classmethod
    def create(klass):
        ''' Factory method to create a datastore with the
        full address space initialized to 0x00

        :returns: An initialized datastore
        '''
        return klass([0x00] * 65536)

    def validate(self, address, count=1):
        ''' Checks to see if the request is in range

        :param address: The starting address
        :param count: The number of values to test for
        :returns: True if the request in within range, False otherwise
        '''
        if count == 0: return False
        handle = set(range(address, address + count))
        return handle.issubset(set(self.values.iterkeys()))

    def getValues(self, address, count=1):
        ''' Returns the requested values of the datastore

        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        return [self.values[i] for i in range(address, address + count)]

    def setValues(self, address, values):
        ''' Sets the requested values of the datastore

        :param address: The starting address
        :param values: The new values to be set
        '''
        if isinstance(values, dict):
            for idx, val in values.iteritems():
                self.values[idx] = val
        else:
            if not isinstance(values, list):
                values = [values]
            for idx, val in enumerate(values):
                self.values[address + idx] = val

########NEW FILE########
__FILENAME__ = device
"""
Modbus Device Controller
-------------------------

These are the device management handlers.  They should be
maintained in the server context and the various methods
should be inserted in the correct locations.
"""
from itertools import izip
from pymodbus.constants import DeviceInformation
from pymodbus.interfaces import Singleton
from pymodbus.utilities import dict_property


#---------------------------------------------------------------------------#
# Network Access Control
#---------------------------------------------------------------------------#
class ModbusAccessControl(Singleton):
    '''
    This is a simple implementation of a Network Management System table.
    Its purpose is to control access to the server (if it is used).
    We assume that if an entry is in the table, it is allowed accesses to
    resources.  However, if the host does not appear in the table (all
    unknown hosts) its connection will simply be closed.

    Since it is a singleton, only one version can possible exist and all
    instances pull from here.
    '''
    __nmstable = [
            "127.0.0.1",
    ]

    def __iter__(self):
        ''' Iterater over the network access table

        :returns: An iterator of the network access table
        '''
        return self.__nmstable.__iter__()

    def __contains__(self, host):
        ''' Check if a host is allowed to access resources

        :param host: The host to check
        '''
        return host in self.__nmstable

    def add(self, host):
        ''' Add allowed host(s) from the NMS table

        :param host: The host to add
        '''
        if not isinstance(host, list):
            host = [host]
        for entry in host:
            if entry not in self.__nmstable:
                self.__nmstable.append(entry)

    def remove(self, host):
        ''' Remove allowed host(s) from the NMS table

        :param host: The host to remove
        '''
        if not isinstance(host, list):
            host = [host]
        for entry in host:
            if entry in self.__nmstable:
                self.__nmstable.remove(entry)

    def check(self, host):
        ''' Check if a host is allowed to access resources

        :param host: The host to check
        '''
        return host in self.__nmstable


#---------------------------------------------------------------------------#
# Modbus Plus Statistics
#---------------------------------------------------------------------------#
class ModbusPlusStatistics(object):
    '''
    This is used to maintain the current modbus plus statistics count. As of
    right now this is simply a stub to complete the modbus implementation.
    For more information, see the modbus implementation guide page 87.
    '''

    __data = {
        'node_type_id'                   : [0x00] * 2, # 00
        'software_version_number'        : [0x00] * 2, # 01
        'network_address'                : [0x00] * 2, # 02
        'mac_state_variable'             : [0x00] * 2, # 03
        'peer_status_code'               : [0x00] * 2, # 04
        'token_pass_counter'             : [0x00] * 2, # 05
        'token_rotation_time'            : [0x00] * 2, # 06

        'program_master_token_failed'    : [0x00],     # 07 hi
        'data_master_token_failed'       : [0x00],     # 07 lo
        'program_master_token_owner'     : [0x00],     # 08 hi
        'data_master_token_owner'        : [0x00],     # 08 lo
        'program_slave_token_owner'      : [0x00],     # 09 hi
        'data_slave_token_owner'         : [0x00],     # 09 lo
        'data_slave_command_transfer'    : [0x00],     # 10 hi
        '__unused_10_lowbit'             : [0x00],     # 10 lo

        'program_slave_command_transfer' : [0x00],     # 11 hi
        'program_master_rsp_transfer'    : [0x00],     # 11 lo
        'program_slave_auto_logout'      : [0x00],     # 12 hi
        'program_master_connect_status'  : [0x00],     # 12 lo
        'receive_buffer_dma_overrun'     : [0x00],     # 13 hi
        'pretransmit_deferral_error'     : [0x00],     # 13 lo
        'frame_size_error'               : [0x00],     # 14 hi
        'repeated_command_received'      : [0x00],     # 14 lo
        'receiver_alignment_error'       : [0x00],     # 15 hi
        'receiver_collision_abort_error' : [0x00],     # 15 lo
        'bad_packet_length_error'        : [0x00],     # 16 hi
        'receiver_crc_error'             : [0x00],     # 16 lo
        'transmit_buffer_dma_underrun'   : [0x00],     # 17 hi
        'bad_link_address_error'         : [0x00],     # 17 lo

        'bad_mac_function_code_error'    : [0x00],     # 18 hi
        'internal_packet_length_error'   : [0x00],     # 18 lo
        'communication_failed_error'     : [0x00],     # 19 hi
        'communication_retries'          : [0x00],     # 19 lo
        'no_response_error'              : [0x00],     # 20 hi
        'good_receive_packet'            : [0x00],     # 20 lo
        'unexpected_path_error'          : [0x00],     # 21 hi
        'exception_response_error'       : [0x00],     # 21 lo
        'forgotten_transaction_error'    : [0x00],     # 22 hi
        'unexpected_response_error'      : [0x00],     # 22 lo

        'active_station_bit_map'         : [0x00] * 8, # 23-26
        'token_station_bit_map'          : [0x00] * 8, # 27-30
        'global_data_bit_map'            : [0x00] * 8, # 31-34
        'receive_buffer_use_bit_map'     : [0x00] * 8, # 35-37
        'data_master_output_path'        : [0x00] * 8, # 38-41
        'data_slave_input_path'          : [0x00] * 8, # 42-45
        'program_master_outptu_path'     : [0x00] * 8, # 46-49
        'program_slave_input_path'       : [0x00] * 8, # 50-53
    }

    def __init__(self):
        '''
        Initialize the modbus plus statistics with the default
        information.
        '''
        self.reset()

    def __iter__(self):
        ''' Iterater over the statistics

        :returns: An iterator of the modbus plus statistics
        '''
        return self.__data.iteritems()

    def reset(self):
        ''' This clears all of the modbus plus statistics
        '''
        for key in self.__data:
            self.__data[key] = [0x00] * len(self.__data[key])

    def summary(self):
        ''' Returns a summary of the modbus plus statistics

        :returns: 54 16-bit words representing the status
        '''
        return self.__data.values()

    def encode(self):
        ''' Returns a summary of the modbus plus statistics

        :returns: 54 16-bit words representing the status
        '''
        total, values = [], sum(self.__data.values(), [])
        for c in xrange(0, len(values), 2):
            total.append((values[c] << 8) | values[c+1])
        return total


#---------------------------------------------------------------------------#
# Device Information Control
#---------------------------------------------------------------------------#
class ModbusDeviceIdentification(object):
    '''
    This is used to supply the device identification
    for the readDeviceIdentification function

    For more information read section 6.21 of the modbus
    application protocol.
    '''
    __data = {
        0x00: '',  # VendorName
        0x01: '',  # ProductCode
        0x02: '',  # MajorMinorRevision
        0x03: '',  # VendorUrl
        0x04: '',  # ProductName
        0x05: '',  # ModelName
        0x06: '',  # UserApplicationName
        0x07: '',  # reserved
        0x08: '',  # reserved
        # 0x80 -> 0xFF are private
    }

    __names = [
        'VendorName',
        'ProductCode',
        'MajorMinorRevision',
        'VendorUrl',
        'ProductName',
        'ModelName',
        'UserApplicationName',
    ]

    def __init__(self, info=None):
        '''
        Initialize the datastore with the elements you need.
        (note acceptable range is [0x00-0x06,0x80-0xFF] inclusive)

        :param information: A dictionary of {int:string} of values
        '''
        if isinstance(info, dict):
            for key in info:
                if (0x06 >= key >= 0x00) or (0x80 > key > 0x08):
                    self.__data[key] = info[key]

    def __iter__(self):
        ''' Iterater over the device information

        :returns: An iterator of the device information
        '''
        return self.__data.iteritems()

    def summary(self):
        ''' Return a summary of the main items

        :returns: An dictionary of the main items
        '''
        return dict(zip(self.__names, self.__data.itervalues()))

    def update(self, value):
        ''' Update the values of this identity
        using another identify as the value

        :param value: The value to copy values from
        '''
        self.__data.update(value)

    def __setitem__(self, key, value):
        ''' Wrapper used to access the device information

        :param key: The register to set
        :param value: The new value for referenced register
        '''
        if key not in [0x07, 0x08]:
            self.__data[key] = value

    def __getitem__(self, key):
        ''' Wrapper used to access the device information

        :param key: The register to read
        '''
        return self.__data.setdefault(key, '')

    def __str__(self):
        ''' Build a representation of the device

        :returns: A string representation of the device
        '''
        return "DeviceIdentity"

    #-------------------------------------------------------------------------#
    # Properties
    #-------------------------------------------------------------------------#
    VendorName          = dict_property(lambda s: s.__data, 0)
    ProductCode         = dict_property(lambda s: s.__data, 1)
    MajorMinorRevision  = dict_property(lambda s: s.__data, 2)
    VendorUrl           = dict_property(lambda s: s.__data, 3)
    ProductName         = dict_property(lambda s: s.__data, 4)
    ModelName           = dict_property(lambda s: s.__data, 5)
    UserApplicationName = dict_property(lambda s: s.__data, 6)


class DeviceInformationFactory(Singleton):
    ''' This is a helper factory that really just hides
    some of the complexity of processing the device information
    requests (function code 0x2b 0x0e).
    '''

    __lookup = {
        DeviceInformation.Basic:    lambda c,r,i: c.__gets(r, range(0x00, 0x03)),
        DeviceInformation.Regular:  lambda c,r,i: c.__gets(r, range(0x00, 0x08)),
        DeviceInformation.Extended: lambda c,r,i: c.__gets(r, range(0x80, i)),
        DeviceInformation.Specific: lambda c,r,i: c.__get(r, i),
    }

    @classmethod
    def get(cls, control, read_code=DeviceInformation.Basic, object_id=0x00):
        ''' Get the requested device data from the system

        :param control: The control block to pull data from
        :param read_code: The read code to process
        :param object_id: The specific object_id to read
        :returns: The requested data (id, length, value)
        '''
        identity = control.Identity
        return cls.__lookup[read_code](cls, identity, object_id)

    @classmethod
    def __get(cls, identity, object_id):
        ''' Read a single object_id from the device information

        :param identity: The identity block to pull data from
        :param object_id: The specific object id to read
        :returns: The requested data (id, length, value)
        '''
        return { object_id:identity[object_id] }

    @classmethod
    def __gets(cls, identity, object_ids):
        ''' Read multiple object_ids from the device information

        :param identity: The identity block to pull data from
        :param object_ids: The specific object ids to read
        :returns: The requested data (id, length, value)
        '''
        return dict((oid, identity[oid]) for oid in object_ids)


#---------------------------------------------------------------------------#
# Counters Handler
#---------------------------------------------------------------------------#
class ModbusCountersHandler(object):
    '''
    This is a helper class to simplify the properties for the counters::

    0x0B  1  Return Bus Message Count

             Quantity of messages that the remote
             device has detected on the communications system since its
             last restart, clear counters operation, or power-up.  Messages
             with bad CRC are not taken into account.

    0x0C  2  Return Bus Communication Error Count

             Quantity of CRC errors encountered by the remote device since its
             last restart, clear counters operation, or power-up.  In case of
             an error detected on the character level, (overrun, parity error),
             or in case of a message length < 3 bytes, the receiving device is
             not able to calculate the CRC. In such cases, this counter is
             also incremented.

    0x0D  3  Return Slave Exception Error Count

             Quantity of MODBUS exception error detected by the remote device
             since its last restart, clear counters operation, or power-up.  It
             comprises also the error detected in broadcast messages even if an
             exception message is not returned in this case.
             Exception errors are described and listed in "MODBUS Application
             Protocol Specification" document.

    0xOE  4  Return Slave Message Count

             Quantity of messages addressed to the remote device,  including
             broadcast messages, that the remote device has processed since its
             last restart, clear counters operation, or power-up.

    0x0F  5  Return Slave No Response Count

             Quantity of messages received by the remote device for which it
             returned no response (neither a normal response nor an exception
             response), since its last restart, clear counters operation, or
             power-up. Then, this counter counts the number of broadcast
             messages it has received.

    0x10  6  Return Slave NAK Count

             Quantity of messages addressed to the remote device for which it
             returned a Negative Acknowledge (NAK) exception response, since
             its last restart, clear counters operation, or power-up. Exception
             responses are described and listed in "MODBUS Application Protocol
             Specification" document.

    0x11  7  Return Slave Busy Count

             Quantity of messages addressed to the remote device for which it
             returned a Slave Device Busy exception response, since its last
             restart, clear counters operation, or power-up. Exception
             responses are described and listed in "MODBUS Application
             Protocol Specification" document.

    0x12  8  Return Bus Character Overrun Count

             Quantity of messages addressed to the remote device that it could
             not handle due to a character overrun condition, since its last
             restart, clear counters operation, or power-up. A character
             overrun is caused by data characters arriving at the port faster
             than they can.

    .. note:: I threw the event counter in here for convinience
    '''
    __data = dict([(i, 0x0000) for i in range(9)])
    __names   = [
        'BusMessage',
        'BusCommunicationError',
        'SlaveExceptionError',
        'SlaveMessage',
        'SlaveNoResponse',
        'SlaveNAK',
        'SlaveBusy',
        'BusCharacterOverrun'
        'Event '
    ]

    def __iter__(self):
        ''' Iterater over the device counters

        :returns: An iterator of the device counters
        '''
        return izip(self.__names, self.__data.itervalues())

    def update(self, values):
        ''' Update the values of this identity
        using another identify as the value

        :param values: The value to copy values from
        '''
        for k, v in values.iteritems():
            v += self.__getattribute__(k)
            self.__setattr__(k, v)

    def reset(self):
        ''' This clears all of the system counters
        '''
        self.__data = dict([(i, 0x0000) for i in range(9)])

    def summary(self):
        ''' Returns a summary of the counters current status

        :returns: A byte with each bit representing each counter
        '''
        count, result = 0x01, 0x00
        for i in self.__data.itervalues():
            if i != 0x00: result |= count
            count <<= 1
        return result

    #-------------------------------------------------------------------------#
    # Properties
    #-------------------------------------------------------------------------#
    BusMessage            = dict_property(lambda s: s.__data, 0)
    BusCommunicationError = dict_property(lambda s: s.__data, 1)
    BusExceptionError     = dict_property(lambda s: s.__data, 2)
    SlaveMessage          = dict_property(lambda s: s.__data, 3)
    SlaveNoResponse       = dict_property(lambda s: s.__data, 4)
    SlaveNAK              = dict_property(lambda s: s.__data, 5)
    SlaveBusy             = dict_property(lambda s: s.__data, 6)
    BusCharacterOverrun   = dict_property(lambda s: s.__data, 7)
    Event                 = dict_property(lambda s: s.__data, 8)


#---------------------------------------------------------------------------#
# Main server controll block
#---------------------------------------------------------------------------#
class ModbusControlBlock(Singleton):
    '''
    This is a global singleotn that controls all system information

    All activity should be logged here and all diagnostic requests
    should come from here.
    '''

    __mode = 'ASCII'
    __diagnostic = [False] * 16
    __instance = None
    __listen_only = False
    __delimiter = '\r'
    __counters = ModbusCountersHandler()
    __identity = ModbusDeviceIdentification()
    __plus     = ModbusPlusStatistics()
    __events   = []

    #-------------------------------------------------------------------------#
    # Magic
    #-------------------------------------------------------------------------#
    def __str__(self):
        ''' Build a representation of the control block

        :returns: A string representation of the control block
        '''
        return "ModbusControl"

    def __iter__(self):
        ''' Iterater over the device counters

        :returns: An iterator of the device counters
        '''
        return self.__counters.__iter__()

    #-------------------------------------------------------------------------#
    # Events
    #-------------------------------------------------------------------------#
    def addEvent(self, event):
        ''' Adds a new event to the event log

        :param event: A new event to add to the log
        '''
        self.__events.insert(0, event)
        self.__events = self.__events[0:64]  # chomp to 64 entries
        self.Counter.Event += 1

    def getEvents(self):
        ''' Returns an encoded collection of the event log.

        :returns: The encoded events packet
        '''
        events = [event.encode() for event in self.__events]
        return ''.join(events)

    def clearEvents(self):
        ''' Clears the current list of events
        '''
        self.__events = []

    #-------------------------------------------------------------------------#
    # Other Properties
    #-------------------------------------------------------------------------#
    Identity = property(lambda s: s.__identity)
    Counter  = property(lambda s: s.__counters)
    Events   = property(lambda s: s.__events)
    Plus     = property(lambda s: s.__plus)

    def reset(self):
        ''' This clears all of the system counters and the
            diagnostic register
        '''
        self.__events = []
        self.__counters.reset()
        self.__diagnostic = [False] * 16

    #-------------------------------------------------------------------------#
    # Listen Properties
    #-------------------------------------------------------------------------#
    def _setListenOnly(self, value):
        ''' This toggles the listen only status

        :param value: The value to set the listen status to
        '''
        self.__listen_only = bool(value)

    ListenOnly = property(lambda s: s.__listen_only, _setListenOnly)

    #-------------------------------------------------------------------------#
    # Mode Properties
    #-------------------------------------------------------------------------#
    def _setMode(self, mode):
        ''' This toggles the current serial mode

        :param mode: The data transfer method in (RTU, ASCII)
        '''
        if mode in ['ASCII', 'RTU']:
            self.__mode = mode

    Mode = property(lambda s: s.__mode, _setMode)

    #-------------------------------------------------------------------------#
    # Delimiter Properties
    #-------------------------------------------------------------------------#
    def _setDelimiter(self, char):
        ''' This changes the serial delimiter character

        :param char: The new serial delimiter character
        '''
        if isinstance(char, str):
            self.__delimiter = char
        elif isinstance(char, int):
            self.__delimiter = chr(char)

    Delimiter = property(lambda s: s.__delimiter, _setDelimiter)

    #-------------------------------------------------------------------------#
    # Diagnostic Properties
    #-------------------------------------------------------------------------#
    def setDiagnostic(self, mapping):
        ''' This sets the value in the diagnostic register

        :param mapping: Dictionary of key:value pairs to set
        '''
        for entry in mapping.iteritems():
            if entry[0] >= 0 and entry[0] < len(self.__diagnostic):
                self.__diagnostic[entry[0]] = (entry[1] != 0)

    def getDiagnostic(self, bit):
        ''' This gets the value in the diagnostic register

        :param bit: The bit to get
        :returns: The current value of the requested bit
        '''
        if bit >= 0 and bit < len(self.__diagnostic):
            return self.__diagnostic[bit]
        return None

    def getDiagnosticRegister(self):
        ''' This gets the entire diagnostic register

        :returns: The diagnostic register collection
        '''
        return self.__diagnostic

#---------------------------------------------------------------------------#
# Exported Identifiers
#---------------------------------------------------------------------------#
__all__ = [
        "ModbusAccessControl",
        "ModbusPlusStatistics",
        "ModbusDeviceIdentification",
        "DeviceInformationFactory",
        "ModbusControlBlock"
]

########NEW FILE########
__FILENAME__ = diag_message
'''
Diagnostic Record Read/Write
------------------------------

These need to be tied into a the current server context
or linked to the appropriate data
'''
import struct

from pymodbus.constants import ModbusStatus, ModbusPlusOperation
from pymodbus.pdu import ModbusRequest
from pymodbus.pdu import ModbusResponse
from pymodbus.device import ModbusControlBlock
from pymodbus.exceptions import NotImplementedException
from pymodbus.utilities import pack_bitstring

_MCB = ModbusControlBlock()


#---------------------------------------------------------------------------#
# Diagnostic Function Codes Base Classes
# diagnostic 08, 00-18,20
#---------------------------------------------------------------------------#
# TODO Make sure all the data is decoded from the response
#---------------------------------------------------------------------------#
class DiagnosticStatusRequest(ModbusRequest):
    '''
    This is a base class for all of the diagnostic request functions
    '''
    function_code = 0x08
    _rtu_frame_size = 8

    def __init__(self, **kwargs):
        '''
        Base initializer for a diagnostic request
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.message = None

    def encode(self):
        '''
        Base encoder for a diagnostic response
        we encode the data set in self.message

        :returns: The encoded packet
        '''
        packet = struct.pack('>H', self.sub_function_code)
        if self.message is not None:
            if isinstance(self.message, str):
                packet += self.message
            elif isinstance(self.message, list):
                for piece in self.message:
                    packet += struct.pack('>H', piece)
            elif isinstance(self.message, int):
                packet += struct.pack('>H', self.message)
        return packet

    def decode(self, data):
        ''' Base decoder for a diagnostic request

        :param data: The data to decode into the function code
        '''
        self.sub_function_code, self.message = struct.unpack('>HH', data)


class DiagnosticStatusResponse(ModbusResponse):
    '''
    This is a base class for all of the diagnostic response functions

    It works by performing all of the encoding and decoding of variable
    data and lets the higher classes define what extra data to append
    and how to execute a request
    '''
    function_code = 0x08
    _rtu_frame_size = 8

    def __init__(self, **kwargs):
        '''
        Base initializer for a diagnostic response
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.message = None

    def encode(self):
        '''
        Base encoder for a diagnostic response
        we encode the data set in self.message

        :returns: The encoded packet
        '''
        packet = struct.pack('>H', self.sub_function_code)
        if self.message is not None:
            if isinstance(self.message, str):
                packet += self.message
            elif isinstance(self.message, list):
                for piece in self.message:
                    packet += struct.pack('>H', piece)
            elif isinstance(self.message, int):
                packet += struct.pack('>H', self.message)
        return packet

    def decode(self, data):
        ''' Base decoder for a diagnostic response

        :param data: The data to decode into the function code
        '''
        self.sub_function_code, self.message = struct.unpack('>HH', data)


class DiagnosticStatusSimpleRequest(DiagnosticStatusRequest):
    '''
    A large majority of the diagnostic functions are simple
    status request functions.  They work by sending 0x0000
    as data and their function code and they are returned
    2 bytes of data.

    If a function inherits this, they only need to implement
    the execute method
    '''

    def __init__(self, data=0x0000, **kwargs):
        '''
        General initializer for a simple diagnostic request

        The data defaults to 0x0000 if not provided as over half
        of the functions require it.

        :param data: The data to send along with the request
        '''
        DiagnosticStatusRequest.__init__(self, **kwargs)
        self.message = data

    def execute(self, *args):
        ''' Base function to raise if not implemented '''
        raise NotImplementedException("Diagnostic Message Has No Execute Method")


class DiagnosticStatusSimpleResponse(DiagnosticStatusResponse):
    '''
    A large majority of the diagnostic functions are simple
    status request functions.  They work by sending 0x0000
    as data and their function code and they are returned
    2 bytes of data.
    '''

    def __init__(self, data=0x0000, **kwargs):
        ''' General initializer for a simple diagnostic response

        :param data: The resulting data to return to the client
        '''
        DiagnosticStatusResponse.__init__(self, **kwargs)
        self.message = data


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 00
#---------------------------------------------------------------------------#
class ReturnQueryDataRequest(DiagnosticStatusRequest):
    '''
    The data passed in the request data field is to be returned (looped back)
    in the response. The entire response message should be identical to the
    request.
    '''
    sub_function_code = 0x0000

    def __init__(self, message=0x0000, **kwargs):
        ''' Initializes a new instance of the request

        :param message: The message to send to loopback
        '''
        DiagnosticStatusRequest.__init__(self, **kwargs)
        if isinstance(message, list):
            self.message = message
        else: self.message = [message]

    def execute(self, *args):
        ''' Executes the loopback request (builds the response)

        :returns: The populated loopback response message
        '''
        return ReturnQueryDataResponse(self.message)


class ReturnQueryDataResponse(DiagnosticStatusResponse):
    '''
    The data passed in the request data field is to be returned (looped back)
    in the response. The entire response message should be identical to the
    request.
    '''
    sub_function_code = 0x0000

    def __init__(self, message=0x0000, **kwargs):
        ''' Initializes a new instance of the response

        :param message: The message to loopback
        '''
        DiagnosticStatusResponse.__init__(self, **kwargs)
        if isinstance(message, list):
            self.message = message
        else: self.message = [message]


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 01
#---------------------------------------------------------------------------#
class RestartCommunicationsOptionRequest(DiagnosticStatusRequest):
    '''
    The remote device serial line port must be initialized and restarted, and
    all of its communications event counters are cleared. If the port is
    currently in Listen Only Mode, no response is returned. This function is
    the only one that brings the port out of Listen Only Mode. If the port is
    not currently in Listen Only Mode, a normal response is returned. This
    occurs before the restart is executed.
    '''
    sub_function_code = 0x0001

    def __init__(self, toggle=False, **kwargs):
        ''' Initializes a new request

        :param toggle: Set to True to toggle, False otherwise
        '''
        DiagnosticStatusRequest.__init__(self, **kwargs)
        if toggle:
            self.message   = [ModbusStatus.On]
        else: self.message = [ModbusStatus.Off]

    def execute(self, *args):
        ''' Clear event log and restart

        :returns: The initialized response message
        '''
        #if _MCB.ListenOnly:
        return RestartCommunicationsOptionResponse(self.message)


class RestartCommunicationsOptionResponse(DiagnosticStatusResponse):
    '''
    The remote device serial line port must be initialized and restarted, and
    all of its communications event counters are cleared. If the port is
    currently in Listen Only Mode, no response is returned. This function is
    the only one that brings the port out of Listen Only Mode. If the port is
    not currently in Listen Only Mode, a normal response is returned. This
    occurs before the restart is executed.
    '''
    sub_function_code = 0x0001

    def __init__(self, toggle=False, **kwargs):
        ''' Initializes a new response

        :param toggle: Set to True if we toggled, False otherwise
        '''
        DiagnosticStatusResponse.__init__(self, **kwargs)
        if toggle:
            self.message   = [ModbusStatus.On]
        else: self.message = [ModbusStatus.Off]


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 02
#---------------------------------------------------------------------------#
class ReturnDiagnosticRegisterRequest(DiagnosticStatusSimpleRequest):
    '''
    The contents of the remote device's 16-bit diagnostic register are
    returned in the response
    '''
    sub_function_code = 0x0002

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        #if _MCB.isListenOnly():
        register = pack_bitstring(_MCB.getDiagnosticRegister())
        return ReturnDiagnosticRegisterResponse(register)


class ReturnDiagnosticRegisterResponse(DiagnosticStatusSimpleResponse):
    '''
    The contents of the remote device's 16-bit diagnostic register are
    returned in the response
    '''
    sub_function_code = 0x0002


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 03
#---------------------------------------------------------------------------#
class ChangeAsciiInputDelimiterRequest(DiagnosticStatusSimpleRequest):
    '''
    The character 'CHAR' passed in the request data field becomes the end of
    message delimiter for future messages (replacing the default LF
    character). This function is useful in cases of a Line Feed is not
    required at the end of ASCII messages.
    '''
    sub_function_code = 0x0003

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        char = (self.message & 0xff00) >> 8
        _MCB.Delimiter = char
        return ChangeAsciiInputDelimiterResponse(self.message)


class ChangeAsciiInputDelimiterResponse(DiagnosticStatusSimpleResponse):
    '''
    The character 'CHAR' passed in the request data field becomes the end of
    message delimiter for future messages (replacing the default LF
    character). This function is useful in cases of a Line Feed is not
    required at the end of ASCII messages.
    '''
    sub_function_code = 0x0003


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 04
#---------------------------------------------------------------------------#
class ForceListenOnlyModeRequest(DiagnosticStatusSimpleRequest):
    '''
    Forces the addressed remote device to its Listen Only Mode for MODBUS
    communications.  This isolates it from the other devices on the network,
    allowing them to continue communicating without interruption from the
    addressed remote device. No response is returned.
    '''
    sub_function_code = 0x0004

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        _MCB.ListenOnly = True
        return ForceListenOnlyModeResponse()


class ForceListenOnlyModeResponse(DiagnosticStatusResponse):
    '''
    Forces the addressed remote device to its Listen Only Mode for MODBUS
    communications.  This isolates it from the other devices on the network,
    allowing them to continue communicating without interruption from the
    addressed remote device. No response is returned.

    This does not send a response
    '''
    sub_function_code = 0x0004
    should_respond    = False

    def __init__(self, **kwargs):
        ''' Initializer to block a return response
        '''
        DiagnosticStatusResponse.__init__(self, **kwargs)
        self.message = []


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 10
#---------------------------------------------------------------------------#
class ClearCountersRequest(DiagnosticStatusSimpleRequest):
    '''
    The goal is to clear ll counters and the diagnostic register.
    Also, counters are cleared upon power-up
    '''
    sub_function_code = 0x000A

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        _MCB.reset()
        return ClearCountersResponse(self.message)


class ClearCountersResponse(DiagnosticStatusSimpleResponse):
    '''
    The goal is to clear ll counters and the diagnostic register.
    Also, counters are cleared upon power-up
    '''
    sub_function_code = 0x000A


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 11
#---------------------------------------------------------------------------#
class ReturnBusMessageCountRequest(DiagnosticStatusSimpleRequest):
    '''
    The response data field returns the quantity of messages that the
    remote device has detected on the communications systems since its last
    restart, clear counters operation, or power-up
    '''
    sub_function_code = 0x000B

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.BusMessage
        return ReturnBusMessageCountResponse(count)


class ReturnBusMessageCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of messages that the
    remote device has detected on the communications systems since its last
    restart, clear counters operation, or power-up
    '''
    sub_function_code = 0x000B


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 12
#---------------------------------------------------------------------------#
class ReturnBusCommunicationErrorCountRequest(DiagnosticStatusSimpleRequest):
    '''
    The response data field returns the quantity of CRC errors encountered
    by the remote device since its last restart, clear counter operation, or
    power-up
    '''
    sub_function_code = 0x000C

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.BusCommunicationError
        return ReturnBusCommunicationErrorCountResponse(count)


class ReturnBusCommunicationErrorCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of CRC errors encountered
    by the remote device since its last restart, clear counter operation, or
    power-up
    '''
    sub_function_code = 0x000C


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 13
#---------------------------------------------------------------------------#
class ReturnBusExceptionErrorCountRequest(DiagnosticStatusSimpleRequest):
    '''
    The response data field returns the quantity of modbus exception
    responses returned by the remote device since its last restart,
    clear counters operation, or power-up
    '''
    sub_function_code = 0x000D

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.BusExceptionError
        return ReturnBusExceptionErrorCountResponse(count)


class ReturnBusExceptionErrorCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of modbus exception
    responses returned by the remote device since its last restart,
    clear counters operation, or power-up
    '''
    sub_function_code = 0x000D


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 14
#---------------------------------------------------------------------------#
class ReturnSlaveMessageCountRequest(DiagnosticStatusSimpleRequest):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device, or broadcast, that the remote device has processed since
    its last restart, clear counters operation, or power-up
    '''
    sub_function_code = 0x000E

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.SlaveMessage
        return ReturnSlaveMessageCountResponse(count)


class ReturnSlaveMessageCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device, or broadcast, that the remote device has processed since
    its last restart, clear counters operation, or power-up
    '''
    sub_function_code = 0x000E


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 15
#---------------------------------------------------------------------------#
class ReturnSlaveNoResponseCountRequest(DiagnosticStatusSimpleRequest):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device, or broadcast, that the remote device has processed since
    its last restart, clear counters operation, or power-up
    '''
    sub_function_code = 0x000F

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.SlaveNoResponse
        return ReturnSlaveNoReponseCountResponse(count)


class ReturnSlaveNoReponseCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device, or broadcast, that the remote device has processed since
    its last restart, clear counters operation, or power-up
    '''
    sub_function_code = 0x000F


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 16
#---------------------------------------------------------------------------#
class ReturnSlaveNAKCountRequest(DiagnosticStatusSimpleRequest):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device for which it returned a Negative Acknowledge (NAK) exception
    response, since its last restart, clear counters operation, or power-up.
    Exception responses are described and listed in section 7 .
    '''
    sub_function_code = 0x0010

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.SlaveNAK
        return ReturnSlaveNAKCountResponse(count)


class ReturnSlaveNAKCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device for which it returned a Negative Acknowledge (NAK) exception
    response, since its last restart, clear counters operation, or power-up.
    Exception responses are described and listed in section 7.
    '''
    sub_function_code = 0x0010


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 17
#---------------------------------------------------------------------------#
class ReturnSlaveBusyCountRequest(DiagnosticStatusSimpleRequest):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device for which it returned a Slave Device Busy exception response,
    since its last restart, clear counters operation, or power-up.
    '''
    sub_function_code = 0x0011

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.SlaveBusy
        return ReturnSlaveBusyCountResponse(count)


class ReturnSlaveBusyCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device for which it returned a Slave Device Busy exception response,
    since its last restart, clear counters operation, or power-up.
    '''
    sub_function_code = 0x0011


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 18
#---------------------------------------------------------------------------#
class ReturnSlaveBusCharacterOverrunCountRequest(DiagnosticStatusSimpleRequest):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device that it could not handle due to a character overrun condition,
    since its last restart, clear counters operation, or power-up. A character
    overrun is caused by data characters arriving at the port faster than they
    can be stored, or by the loss of a character due to a hardware malfunction.
    '''
    sub_function_code = 0x0012

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.BusCharacterOverrun
        return ReturnSlaveBusCharacterOverrunCountResponse(count)


class ReturnSlaveBusCharacterOverrunCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of messages addressed to the
    remote device that it could not handle due to a character overrun condition,
    since its last restart, clear counters operation, or power-up. A character
    overrun is caused by data characters arriving at the port faster than they
    can be stored, or by the loss of a character due to a hardware malfunction.
    '''
    sub_function_code = 0x0012


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 19
#---------------------------------------------------------------------------#
class ReturnIopOverrunCountRequest(DiagnosticStatusSimpleRequest):
    '''
    An IOP overrun is caused by data characters arriving at the port
    faster than they can be stored, or by the loss of a character due
    to a hardware malfunction.  This function is specific to the 884.
    '''
    sub_function_code = 0x0013

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        count = _MCB.Counter.BusCharacterOverrun
        return ReturnIopOverrunCountResponse(count)


class ReturnIopOverrunCountResponse(DiagnosticStatusSimpleResponse):
    '''
    The response data field returns the quantity of messages
    addressed to the slave that it could not handle due to an 884
    IOP overrun condition, since its last restart, clear counters
    operation, or power-up.
    '''
    sub_function_code = 0x0013


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 20
#---------------------------------------------------------------------------#
class ClearOverrunCountRequest(DiagnosticStatusSimpleRequest):
    '''
    Clears the overrun error counter and reset the error flag

    An error flag should be cleared, but nothing else in the
    specification mentions is, so it is ignored.
    '''
    sub_function_code = 0x0014

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        _MCB.Counter.BusCharacterOverrun = 0x0000
        return ClearOverrunCountResponse(self.message)


class ClearOverrunCountResponse(DiagnosticStatusSimpleResponse):
    '''
    Clears the overrun error counter and reset the error flag
    '''
    sub_function_code = 0x0014


#---------------------------------------------------------------------------#
# Diagnostic Sub Code 21
#---------------------------------------------------------------------------#
class GetClearModbusPlusRequest(DiagnosticStatusSimpleRequest):
    '''
    In addition to the Function code (08) and Subfunction code
    (00 15 hex) in the query, a two-byte Operation field is used
    to specify either a 'Get Statistics' or a 'Clear Statistics'
    operation.  The two operations are exclusive - the 'Get'
    operation cannot clear the statistics, and the 'Clear'
    operation does not return statistics prior to clearing
    them. Statistics are also cleared on power-up of the slave
    device.
    '''
    sub_function_code = 0x0015

    def execute(self, *args):
        ''' Execute the diagnostic request on the given device

        :returns: The initialized response message
        '''
        message = None # the clear operation does not return info
        if self.message == ModbusPlusOperation.ClearStatistics:
            _MCB.Plus.reset()
        else: message = _MCB.Plus.encode()
        return GetClearModbusPlusResponse(message)


class GetClearModbusPlusResponse(DiagnosticStatusSimpleResponse):
    '''
    Returns a series of 54 16-bit words (108 bytes) in the data field
    of the response (this function differs from the usual two-byte
    length of the data field). The data contains the statistics for
    the Modbus Plus peer processor in the slave device.
    '''
    sub_function_code = 0x0015


#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "DiagnosticStatusRequest", "DiagnosticStatusResponse",
    "ReturnQueryDataRequest", "ReturnQueryDataResponse",
    "RestartCommunicationsOptionRequest", "RestartCommunicationsOptionResponse",
    "ReturnDiagnosticRegisterRequest", "ReturnDiagnosticRegisterResponse",
    "ChangeAsciiInputDelimiterRequest", "ChangeAsciiInputDelimiterResponse",
    "ForceListenOnlyModeRequest", "ForceListenOnlyModeResponse",
    "ClearCountersRequest", "ClearCountersResponse",
    "ReturnBusMessageCountRequest", "ReturnBusMessageCountResponse",
    "ReturnBusCommunicationErrorCountRequest", "ReturnBusCommunicationErrorCountResponse",
    "ReturnBusExceptionErrorCountRequest", "ReturnBusExceptionErrorCountResponse",
    "ReturnSlaveMessageCountRequest", "ReturnSlaveMessageCountResponse",
    "ReturnSlaveNoResponseCountRequest", "ReturnSlaveNoReponseCountResponse",
    "ReturnSlaveNAKCountRequest", "ReturnSlaveNAKCountResponse",
    "ReturnSlaveBusyCountRequest", "ReturnSlaveBusyCountResponse",
    "ReturnSlaveBusCharacterOverrunCountRequest", "ReturnSlaveBusCharacterOverrunCountResponse",
    "ReturnIopOverrunCountRequest", "ReturnIopOverrunCountResponse",
    "ClearOverrunCountRequest", "ClearOverrunCountResponse",
    "GetClearModbusPlusRequest", "GetClearModbusPlusResponse",
]

########NEW FILE########
__FILENAME__ = events
'''
Modbus Remote Events
------------------------------------------------------------

An event byte returned by the Get Communications Event Log function
can be any one of four types. The type is defined by bit 7
(the high-order bit) in each byte. It may be further defined by bit 6.
'''
from pymodbus.exceptions import NotImplementedException
from pymodbus.exceptions import ParameterException
from pymodbus.utilities import pack_bitstring, unpack_bitstring


class ModbusEvent(object):

    def encode(self):
        ''' Encodes the status bits to an event message

        :returns: The encoded event message
        '''
        raise NotImplementedException()

    def decode(self, event):
        ''' Decodes the event message to its status bits

        :param event: The event to decode
        '''
        raise NotImplementedException()


class RemoteReceiveEvent(ModbusEvent):
    ''' Remote device MODBUS Receive Event

    The remote device stores this type of event byte when a query message
    is received. It is stored before the remote device processes the message.
    This event is defined by bit 7 set to logic '1'. The other bits will be
    set to a logic '1' if the corresponding condition is TRUE. The bit layout
    is::

        Bit Contents
        ----------------------------------
        0   Not Used
        2   Not Used
        3   Not Used
        4   Character Overrun
        5   Currently in Listen Only Mode
        6   Broadcast Receive
        7   1
    '''

    def __init__(self, **kwargs):
        ''' Initialize a new event instance
        '''
        self.overrun   = kwargs.get('overrun', False)
        self.listen    = kwargs.get('listen', False)
        self.broadcast = kwargs.get('broadcast', False)

    def encode(self):
        ''' Encodes the status bits to an event message

        :returns: The encoded event message
        '''
        bits  = [False] * 3
        bits += [self.overrun, self.listen, self.broadcast, True]
        packet = pack_bitstring(bits)
        return packet

    def decode(self, event):
        ''' Decodes the event message to its status bits

        :param event: The event to decode
        '''
        bits = unpack_bitstring(event)
        self.overrun   = bits[4]
        self.listen    = bits[5]
        self.broadcast = bits[6]


class RemoteSendEvent(ModbusEvent):
    ''' Remote device MODBUS Send Event

    The remote device stores this type of event byte when it finishes
    processing a request message. It is stored if the remote device
    returned a normal or exception response, or no response.

    This event is defined by bit 7 set to a logic '0', with bit 6 set to a '1'.
    The other bits will be set to a logic '1' if the corresponding
    condition is TRUE. The bit layout is::

        Bit Contents
        -----------------------------------------------------------
        0   Read Exception Sent (Exception Codes 1-3)
        1   Slave Abort Exception Sent (Exception Code 4)
        2   Slave Busy Exception Sent (Exception Codes 5-6)
        3   Slave Program NAK Exception Sent (Exception Code 7)
        4   Write Timeout Error Occurred
        5   Currently in Listen Only Mode
        6   1
        7   0
    '''

    def __init__(self, **kwargs):
        ''' Initialize a new event instance
        '''
        self.read          = kwargs.get('read', False)
        self.slave_abort   = kwargs.get('slave_abort', False)
        self.slave_busy    = kwargs.get('slave_busy', False)
        self.slave_nak     = kwargs.get('slave_nak', False)
        self.write_timeout = kwargs.get('write_timeout', False)
        self.listen        = kwargs.get('listen', False)

    def encode(self):
        ''' Encodes the status bits to an event message

        :returns: The encoded event message
        '''
        bits = [self.read, self.slave_abort, self.slave_busy,
            self.slave_nak, self.write_timeout, self.listen]
        bits  += [True, False]
        packet = pack_bitstring(bits)
        return packet

    def decode(self, event):
        ''' Decodes the event message to its status bits

        :param event: The event to decode
        '''
        # todo fix the start byte count
        bits = unpack_bitstring(event)
        self.read          = bits[0]
        self.slave_abort   = bits[1]
        self.slave_busy    = bits[2]
        self.slave_nak     = bits[3]
        self.write_timeout = bits[4]
        self.listen        = bits[5]


class EnteredListenModeEvent(ModbusEvent):
    ''' Remote device Entered Listen Only Mode

    The remote device stores this type of event byte when it enters
    the Listen Only Mode. The event is defined by a content of 04 hex.
    '''

    value = 0x04
    __encoded = '\x04'

    def encode(self):
        ''' Encodes the status bits to an event message

        :returns: The encoded event message
        '''
        return self.__encoded

    def decode(self, event):
        ''' Decodes the event message to its status bits

        :param event: The event to decode
        '''
        if event != self.__encoded:
            raise ParameterException('Invalid decoded value')


class CommunicationRestartEvent(ModbusEvent):
    ''' Remote device Initiated Communication Restart

    The remote device stores this type of event byte when its communications
    port is restarted. The remote device can be restarted by the Diagnostics
    function (code 08), with sub-function Restart Communications Option
    (code 00 01).

    That function also places the remote device into a 'Continue on Error'
    or 'Stop on Error' mode. If the remote device is placed  into 'Continue on
    Error' mode, the event byte is added to the existing event log. If the
    remote device is placed into 'Stop on Error' mode, the byte is added to
    the log and the rest of the log is cleared to zeros.

    The event is defined by a content of zero.
    '''

    value = 0x00
    __encoded = '\x00'

    def encode(self):
        ''' Encodes the status bits to an event message

        :returns: The encoded event message
        '''
        return self.__encoded

    def decode(self, event):
        ''' Decodes the event message to its status bits

        :param event: The event to decode
        '''
        if event != self.__encoded:
            raise ParameterException('Invalid decoded value')

########NEW FILE########
__FILENAME__ = exceptions
'''
Pymodbus Exceptions
--------------------

Custom exceptions to be used in the Modbus code.
'''


class ModbusException(Exception):
    ''' Base modbus exception '''

    def __init__(self, string):
        ''' Initialize the exception
        :param string: The message to append to the error
        '''
        self.string = string

    def __str__(self):
        return 'Modbus Error: %s' % self.string


class ModbusIOException(ModbusException):
    ''' Error resulting from data i/o '''

    def __init__(self, string=""):
        ''' Initialize the exception
        :param string: The message to append to the error
        '''
        message = "[Input/Output] %s" % string
        ModbusException.__init__(self, message)


class ParameterException(ModbusException):
    ''' Error resulting from invalid paramater '''

    def __init__(self, string=""):
        ''' Initialize the exception
        :param string: The message to append to the error
        '''
        message = "[Invalid Paramter] %s" % string
        ModbusException.__init__(self, message)


class NotImplementedException(ModbusException):
    ''' Error resulting from not implemented function '''

    def __init__(self, string=""):
        ''' Initialize the exception
        :param string: The message to append to the error
        '''
        message = "[Not Implemented] %s" % string
        ModbusException.__init__(self, message)


class ConnectionException(ModbusException):
    ''' Error resulting from a bad connection '''

    def __init__(self, string=""):
        ''' Initialize the exception
        :param string: The message to append to the error
        '''
        message = "[Connection] %s" % string
        ModbusException.__init__(self, message)

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "ModbusException", "ModbusIOException",
    "ParameterException", "NotImplementedException",
    "ConnectionException",
]

########NEW FILE########
__FILENAME__ = factory
"""
Modbus Request/Response Decoder Factories
-------------------------------------------

The following factories make it easy to decode request/response messages.
To add a new request/response pair to be decodeable by the library, simply
add them to the respective function lookup table (order doesn't matter, but
it does help keep things organized).

Regardless of how many functions are added to the lookup, O(1) behavior is
kept as a result of a pre-computed lookup dictionary.
"""

from pymodbus.pdu import IllegalFunctionRequest
from pymodbus.pdu import ExceptionResponse
from pymodbus.pdu import ModbusExceptions as ecode
from pymodbus.interfaces import IModbusDecoder
from pymodbus.exceptions import ModbusException
from pymodbus.bit_read_message import *
from pymodbus.bit_write_message import *
from pymodbus.diag_message import *
from pymodbus.file_message import *
from pymodbus.other_message import *
from pymodbus.mei_message import *
from pymodbus.register_read_message import *
from pymodbus.register_write_message import *

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Server Decoder
#---------------------------------------------------------------------------#
class ServerDecoder(IModbusDecoder):
    ''' Request Message Factory (Server)

    To add more implemented functions, simply add them to the list
    '''
    __function_table = [
            ReadHoldingRegistersRequest,
            ReadDiscreteInputsRequest,
            ReadInputRegistersRequest,
            ReadCoilsRequest,
            WriteMultipleCoilsRequest,
            WriteMultipleRegistersRequest,
            WriteSingleRegisterRequest,
            WriteSingleCoilRequest,
            ReadWriteMultipleRegistersRequest,

            DiagnosticStatusRequest,

            ReadExceptionStatusRequest,
            GetCommEventCounterRequest,
            GetCommEventLogRequest,
            ReportSlaveIdRequest,

            ReadFileRecordRequest,
            WriteFileRecordRequest,
            MaskWriteRegisterRequest,
            ReadFifoQueueRequest,

            ReadDeviceInformationRequest,
    ]
    __sub_function_table = [
            ReturnQueryDataRequest,
            RestartCommunicationsOptionRequest,
            ReturnDiagnosticRegisterRequest,
            ChangeAsciiInputDelimiterRequest,
            ForceListenOnlyModeRequest,
            ClearCountersRequest,
            ReturnBusMessageCountRequest,
            ReturnBusCommunicationErrorCountRequest,
            ReturnBusExceptionErrorCountRequest,
            ReturnSlaveMessageCountRequest,
            ReturnSlaveNoResponseCountRequest,
            ReturnSlaveNAKCountRequest,
            ReturnSlaveBusyCountRequest,
            ReturnSlaveBusCharacterOverrunCountRequest,
            ReturnIopOverrunCountRequest,
            ClearOverrunCountRequest,
            GetClearModbusPlusRequest,

            ReadDeviceInformationRequest,
    ]

    def __init__(self):
        ''' Initializes the client lookup tables
        '''
        functions = set(f.function_code for f in self.__function_table)
        self.__lookup = dict([(f.function_code, f) for f in self.__function_table])
        self.__sub_lookup = dict((f, {}) for f in functions)
        for f in self.__sub_function_table:
            self.__sub_lookup[f.function_code][f.sub_function_code] = f

    def decode(self, message):
        ''' Wrapper to decode a request packet

        :param message: The raw modbus request packet
        :return: The decoded modbus message or None if error
        '''
        try:
            return self._helper(message)
        except ModbusException, er:
            _logger.warn("Unable to decode request %s" % er)
        return None

    def lookupPduClass(self, function_code):
        ''' Use `function_code` to determine the class of the PDU.

        :param function_code: The function code specified in a frame.
        :returns: The class of the PDU that has a matching `function_code`.
        '''
        return self.__lookup.get(function_code, ExceptionResponse)

    def _helper(self, data):
        '''
        This factory is used to generate the correct request object
        from a valid request packet. This decodes from a list of the
        currently implemented request types.

        :param data: The request packet to decode
        :returns: The decoded request or illegal function request object
        '''
        function_code = ord(data[0])
        _logger.debug("Factory Request[%d]" % function_code)
        request = self.__lookup.get(function_code, lambda: None)()
        if not request:
            request = IllegalFunctionRequest(function_code)
        request.decode(data[1:])

        if hasattr(request, 'sub_function_code'):
            lookup = self.__sub_lookup.get(request.function_code, {})
            subtype = lookup.get(request.sub_function_code, None)
            if subtype: request.__class__ = subtype

        return request


#---------------------------------------------------------------------------#
# Client Decoder
#---------------------------------------------------------------------------#
class ClientDecoder(IModbusDecoder):
    ''' Response Message Factory (Client)

    To add more implemented functions, simply add them to the list
    '''
    __function_table = [
            ReadHoldingRegistersResponse,
            ReadDiscreteInputsResponse,
            ReadInputRegistersResponse,
            ReadCoilsResponse,
            WriteMultipleCoilsResponse,
            WriteMultipleRegistersResponse,
            WriteSingleRegisterResponse,
            WriteSingleCoilResponse,
            ReadWriteMultipleRegistersResponse,

            DiagnosticStatusResponse,

            ReadExceptionStatusResponse,
            GetCommEventCounterResponse,
            GetCommEventLogResponse,
            ReportSlaveIdResponse,

            ReadFileRecordResponse,
            WriteFileRecordResponse,
            MaskWriteRegisterResponse,
            ReadFifoQueueResponse,

            ReadDeviceInformationResponse,
    ]
    __sub_function_table = [
            ReturnQueryDataResponse,
            RestartCommunicationsOptionResponse,
            ReturnDiagnosticRegisterResponse,
            ChangeAsciiInputDelimiterResponse,
            ForceListenOnlyModeResponse,
            ClearCountersResponse,
            ReturnBusMessageCountResponse,
            ReturnBusCommunicationErrorCountResponse,
            ReturnBusExceptionErrorCountResponse,
            ReturnSlaveMessageCountResponse,
            ReturnSlaveNoReponseCountResponse,
            ReturnSlaveNAKCountResponse,
            ReturnSlaveBusyCountResponse,
            ReturnSlaveBusCharacterOverrunCountResponse,
            ReturnIopOverrunCountResponse,
            ClearOverrunCountResponse,
            GetClearModbusPlusResponse,

            ReadDeviceInformationResponse,
    ]

    def __init__(self):
        ''' Initializes the client lookup tables
        '''
        functions = set(f.function_code for f in self.__function_table)
        self.__lookup = dict([(f.function_code, f) for f in self.__function_table])
        self.__sub_lookup = dict((f, {}) for f in functions)
        for f in self.__sub_function_table:
            self.__sub_lookup[f.function_code][f.sub_function_code] = f

    def lookupPduClass(self, function_code):
        ''' Use `function_code` to determine the class of the PDU.

        :param function_code: The function code specified in a frame.
        :returns: The class of the PDU that has a matching `function_code`.
        '''
        return self.__lookup.get(function_code, ExceptionResponse)

    def decode(self, message):
        ''' Wrapper to decode a response packet

        :param message: The raw packet to decode
        :return: The decoded modbus message or None if error
        '''
        try:
            return self._helper(message)
        except ModbusException, er:
            _logger.error("Unable to decode response %s" % er)
        return None

    def _helper(self, data):
        '''
        This factory is used to generate the correct response object
        from a valid response packet. This decodes from a list of the
        currently implemented request types.

        :param data: The response packet to decode
        :returns: The decoded request or an exception response object
        '''
        function_code = ord(data[0])
        _logger.debug("Factory Response[%d]" % function_code)
        response = self.__lookup.get(function_code, lambda: None)()
        if function_code > 0x80:
            code = function_code & 0x7f  # strip error portion
            response = ExceptionResponse(code, ecode.IllegalFunction)
        if not response:
            raise ModbusException("Unknown response %d" % function_code)
        response.decode(data[1:])

        if hasattr(response, 'sub_function_code'):
            lookup = self.__sub_lookup.get(response.function_code, {})
            subtype = lookup.get(response.sub_function_code, None)
            if subtype: response.__class__ = subtype

        return response

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = ['ServerDecoder', 'ClientDecoder']

########NEW FILE########
__FILENAME__ = file_message
'''
File Record Read/Write Messages
-------------------------------

Currently none of these messages are implemented
'''
import struct
from pymodbus.pdu import ModbusRequest
from pymodbus.pdu import ModbusResponse
from pymodbus.pdu import ModbusExceptions as merror


#---------------------------------------------------------------------------#
# File Record Types
#---------------------------------------------------------------------------#
class FileRecord(object):
    ''' Represents a file record and its relevant data.
    '''

    def __init__(self, **kwargs):
        ''' Initializes a new instance

        :params reference_type: Defaults to 0x06 (must be)
        :params file_number: Indicates which file number we are reading
        :params record_number: Indicates which record in the file
        :params record_data: The actual data of the record
        :params record_length: The length in registers of the record
        :params response_length: The length in bytes of the record
        '''
        self.reference_type  = kwargs.get('reference_type', 0x06)
        self.file_number     = kwargs.get('file_number', 0x00)
        self.record_number   = kwargs.get('record_number', 0x00)
        self.record_data     = kwargs.get('record_data', '')
        self.record_length   = kwargs.get('record_length',   len(self.record_data) / 2)
        self.response_length = kwargs.get('response_length', len(self.record_data) + 1)

    def __eq__(self, relf):
        ''' Compares the left object to the right
        '''
        return self.reference_type == relf.reference_type \
           and self.file_number    == relf.file_number    \
           and self.record_number  == relf.record_number  \
           and self.record_length  == relf.record_length  \
           and self.record_data    == relf.record_data

    def __ne__(self, relf):
        ''' Compares the left object to the right
        '''
        return not self.__eq__(relf)

    def __repr__(self):
        ''' Gives a representation of the file record
        '''
        params = (self.file_number, self.record_number, self.record_length)
        return 'FileRecord(file=%d, record=%d, length=%d)' % params


#---------------------------------------------------------------------------#
# File Requests/Responses
#---------------------------------------------------------------------------#
class ReadFileRecordRequest(ModbusRequest):
    '''
    This function code is used to perform a file record read. All request
    data lengths are provided in terms of number of bytes and all record
    lengths are provided in terms of registers.

    A file is an organization of records. Each file contains 10000 records,
    addressed 0000 to 9999 decimal or 0x0000 to 0x270f. For example, record
    12 is addressed as 12. The function can read multiple groups of
    references. The groups can be separating (non-contiguous), but the
    references within each group must be sequential. Each group is defined
    in a seperate 'sub-request' field that contains seven bytes::

        The reference type: 1 byte (must be 0x06)
        The file number: 2 bytes
        The starting record number within the file: 2 bytes
        The length of the record to be read: 2 bytes

    The quantity of registers to be read, combined with all other fields
    in the expected response, must not exceed the allowable length of the
    MODBUS PDU: 235 bytes.
    '''
    function_code = 0x14
    _rtu_byte_count_pos = 2

    def __init__(self, records=None, **kwargs):
        ''' Initializes a new instance

        :param records: The file record requests to be read
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.records  = records or []

    def encode(self):
        ''' Encodes the request packet

        :returns: The byte encoded packet
        '''
        packet = struct.pack('B', len(self.records) * 7)
        for record in self.records:
            packet += struct.pack('>BHHH', 0x06, record.file_number,
                record.record_number, record.record_length)
        return packet

    def decode(self, data):
        ''' Decodes the incoming request

        :param data: The data to decode into the address
        '''
        self.records = []
        byte_count = struct.unpack('B', data[0])[0]
        for count in xrange(1, byte_count, 7):
            decoded = struct.unpack('>BHHH', data[count:count+7])
            record  = FileRecord(file_number=decoded[1],
                record_number=decoded[2], record_length=decoded[3])
            if decoded[0] == 0x06: self.records.append(record)

    def execute(self, context):
        ''' Run a read exeception status request against the store

        :param context: The datastore to request from
        :returns: The populated response
        '''
        # TODO do some new context operation here
        # if file number, record number, or address + length
        # is too big, return an error.
        files = []
        return ReadFileRecordResponse(files)


class ReadFileRecordResponse(ModbusResponse):
    '''
    The normal response is a series of 'sub-responses,' one for each
    'sub-request.' The byte count field is the total combined count of
    bytes in all 'sub-responses.' In addition, each 'sub-response'
    contains a field that shows its own byte count.
    '''
    function_code = 0x14
    _rtu_byte_count_pos = 2

    def __init__(self, records=None, **kwargs):
        ''' Initializes a new instance

        :param records: The requested file records
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.records = records or []

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        total  = sum(record.response_length + 1 for record in self.records)
        packet = struct.pack('B', total)
        for record in self.records:
            packet += struct.pack('>BB', 0x06, record.record_length)
            packet += record.record_data
        return packet

    def decode(self, data):
        ''' Decodes a the response

        :param data: The packet data to decode
        '''
        count, self.records = 1, []
        byte_count = struct.unpack('B', data[0])[0]
        while count < byte_count:
            response_length, reference_type = struct.unpack('>BB', data[count:count+2])
            count += response_length + 1 # the count is not included
            record = FileRecord(response_length=response_length,
                record_data=data[count - response_length + 1:count])
            if reference_type == 0x06: self.records.append(record)


class WriteFileRecordRequest(ModbusRequest):
    '''
    This function code is used to perform a file record write. All
    request data lengths are provided in terms of number of bytes
    and all record lengths are provided in terms of the number of 16
    bit words.
    '''
    function_code = 0x15
    _rtu_byte_count_pos = 2

    def __init__(self, records=None, **kwargs):
        ''' Initializes a new instance

        :param records: The file record requests to be read
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.records  = records or []

    def encode(self):
        ''' Encodes the request packet

        :returns: The byte encoded packet
        '''
        total_length = sum((record.record_length * 2) + 7 for record in self.records)
        packet = struct.pack('B', total_length)
        for record in self.records:
            packet += struct.pack('>BHHH', 0x06, record.file_number,
                record.record_number, record.record_length)
            packet += record.record_data
        return packet

    def decode(self, data):
        ''' Decodes the incoming request

        :param data: The data to decode into the address
        '''
        count, self.records = 1, []
        byte_count = struct.unpack('B', data[0])[0]
        while count < byte_count:
            decoded = struct.unpack('>BHHH', data[count:count+7])
            response_length = decoded[3] * 2
            count  += response_length + 7
            record  = FileRecord(record_length=decoded[3],
                file_number=decoded[1], record_number=decoded[2],
                record_data=data[count - response_length:count])
            if decoded[0] == 0x06: self.records.append(record)

    def execute(self, context):
        ''' Run the write file record request against the context

        :param context: The datastore to request from
        :returns: The populated response
        '''
        # TODO do some new context operation here
        # if file number, record number, or address + length
        # is too big, return an error.
        return WriteFileRecordResponse(self.records)


class WriteFileRecordResponse(ModbusResponse):
    '''
    The normal response is an echo of the request.
    '''
    function_code = 0x15
    _rtu_byte_count_pos = 2

    def __init__(self, records=None, **kwargs):
        ''' Initializes a new instance

        :param records: The file record requests to be read
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.records  = records or []

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        total_length = sum((record.record_length * 2) + 7 for record in self.records)
        packet = struct.pack('B', total_length)
        for record in self.records:
            packet += struct.pack('>BHHH', 0x06, record.file_number,
                record.record_number, record.record_length)
            packet += record.record_data
        return packet

    def decode(self, data):
        ''' Decodes the incoming request

        :param data: The data to decode into the address
        '''
        count, self.records = 1, []
        byte_count = struct.unpack('B', data[0])[0]
        while count < byte_count:
            decoded = struct.unpack('>BHHH', data[count:count+7])
            response_length = decoded[3] * 2
            count  += response_length + 7
            record  = FileRecord(record_length=decoded[3],
                file_number=decoded[1], record_number=decoded[2],
                record_data=data[count - response_length:count])
            if decoded[0] == 0x06: self.records.append(record)


class MaskWriteRegisterRequest(ModbusRequest):
    '''
    This function code is used to modify the contents of a specified holding
    register using a combination of an AND mask, an OR mask, and the
    register's current contents. The function can be used to set or clear
    individual bits in the register.
    '''
    function_code = 0x16
    _rtu_frame_size = 10

    def __init__(self, address=0x0000, and_mask=0xffff, or_mask=0x0000, **kwargs):
        ''' Initializes a new instance

        :param address: The mask pointer address (0x0000 to 0xffff)
        :param and_mask: The and bitmask to apply to the register address
        :param or_mask: The or bitmask to apply to the register address
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.address  = address
        self.and_mask = and_mask
        self.or_mask  = or_mask

    def encode(self):
        ''' Encodes the request packet

        :returns: The byte encoded packet
        '''
        return struct.pack('>HHH', self.address, self.and_mask, self.or_mask)

    def decode(self, data):
        ''' Decodes the incoming request

        :param data: The data to decode into the address
        '''
        self.address, self.and_mask, self.or_mask = struct.unpack('>HHH', data)

    def execute(self, context):
        ''' Run a mask write register request against the store

        :param context: The datastore to request from
        :returns: The populated response
        '''
        if not (0x0000 <= self.and_mask <= 0xffff):
            return self.doException(merror.IllegalValue)
        if not (0x0000 <= self.or_mask <= 0xffff):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, 1):
            return self.doException(merror.IllegalAddress)
        values = context.getValues(self.function_code, self.address, 1)[0]
        values = ((values & self.and_mask) | self.or_mask)
        context.setValues(self.function_code, self.address, [values])
        return MaskWriteRegisterResponse(self.address, self.and_mask, self.or_mask)


class MaskWriteRegisterResponse(ModbusResponse):
    '''
    The normal response is an echo of the request. The response is returned
    after the register has been written.
    '''
    function_code = 0x16
    _rtu_frame_size = 10

    def __init__(self, address=0x0000, and_mask=0xffff, or_mask=0x0000, **kwargs):
        ''' Initializes a new instance

        :param address: The mask pointer address (0x0000 to 0xffff)
        :param and_mask: The and bitmask applied to the register address
        :param or_mask: The or bitmask applied to the register address
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.address  = address
        self.and_mask = and_mask
        self.or_mask  = or_mask

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        return struct.pack('>HHH', self.address, self.and_mask, self.or_mask)

    def decode(self, data):
        ''' Decodes a the response

        :param data: The packet data to decode
        '''
        self.address, self.and_mask, self.or_mask = struct.unpack('>HHH', data)


class ReadFifoQueueRequest(ModbusRequest):
    '''
    This function code allows to read the contents of a First-In-First-Out
    (FIFO) queue of register in a remote device. The function returns a
    count of the registers in the queue, followed by the queued data.
    Up to 32 registers can be read: the count, plus up to 31 queued data
    registers.

    The queue count register is returned first, followed by the queued data
    registers.  The function reads the queue contents, but does not clear
    them.
    '''
    function_code = 0x18
    _rtu_frame_size = 6

    def __init__(self, address=0x0000, **kwargs):
        ''' Initializes a new instance

        :param address: The fifo pointer address (0x0000 to 0xffff)
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.address = address
        self.values = []  # this should be added to the context

    def encode(self):
        ''' Encodes the request packet

        :returns: The byte encoded packet
        '''
        return struct.pack('>H', self.address)

    def decode(self, data):
        ''' Decodes the incoming request

        :param data: The data to decode into the address
        '''
        self.address = struct.unpack('>H', data)[0]

    def execute(self, context):
        ''' Run a read exeception status request against the store

        :param context: The datastore to request from
        :returns: The populated response
        '''
        if not (0x0000 <= self.address <= 0xffff):
            return self.doException(merror.IllegalValue)
        if len(self.values) > 31:
            return self.doException(merror.IllegalValue)
        # TODO pull the values from some context
        return ReadFifoQueueResponse(self.values)


class ReadFifoQueueResponse(ModbusResponse):
    '''
    In a normal response, the byte count shows the quantity of bytes to
    follow, including the queue count bytes and value register bytes
    (but not including the error check field).  The queue count is the
    quantity of data registers in the queue (not including the count register).

    If the queue count exceeds 31, an exception response is returned with an
    error code of 03 (Illegal Data Value).
    '''
    function_code = 0x18

    @classmethod
    def calculateRtuFrameSize(cls, buffer):
        ''' Calculates the size of the message

        :param buffer: A buffer containing the data that have been received.
        :returns: The number of bytes in the response.
        '''
        hi_byte = struct.unpack(">B", buffer[2])[0]
        lo_byte = struct.unpack(">B", buffer[3])[0]
        return (hi_byte << 16) + lo_byte + 6

    def __init__(self, values=None, **kwargs):
        ''' Initializes a new instance

        :param values: The list of values of the fifo to return
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.values = values or []

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        length = len(self.values) * 2
        packet = struct.pack('>HH', 2 + length, length)
        for value in self.values:
            packet += struct.pack('>H', value)
        return packet

    def decode(self, data):
        ''' Decodes a the response

        :param data: The packet data to decode
        '''
        self.values = []
        _, count = struct.unpack('>HH', data[0:4])
        for index in xrange(0, count - 4):
            idx = 4 + index * 2
            self.values.append(struct.unpack('>H', data[idx:idx + 2])[0])

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "FileRecord",
    "ReadFileRecordRequest", "ReadFileRecordResponse",
    "WriteFileRecordRequest", "WriteFileRecordResponse",
    "MaskWriteRegisterRequest", "MaskWriteRegisterResponse",
    "ReadFifoQueueRequest", "ReadFifoQueueResponse",
]

########NEW FILE########
__FILENAME__ = interfaces
'''
Pymodbus Interfaces
---------------------

A collection of base classes that are used throughout
the pymodbus library.
'''
from pymodbus.exceptions import NotImplementedException


#---------------------------------------------------------------------------#
# Generic
#---------------------------------------------------------------------------#
class Singleton(object):
    '''
    Singleton base class
    http://mail.python.org/pipermail/python-list/2007-July/450681.html
    '''
    def __new__(cls, *args, **kwargs):
        ''' Create a new instance
        '''
        if '_inst' not in vars(cls):
            cls._inst = object.__new__(cls)
        return cls._inst


#---------------------------------------------------------------------------#
# Project Specific
#---------------------------------------------------------------------------#
class IModbusDecoder(object):
    ''' Modbus Decoder Base Class

    This interface must be implemented by a modbus message
    decoder factory. These factories are responsible for
    abstracting away converting a raw packet into a request / response
    message object.
    '''

    def decode(self, message):
        ''' Wrapper to decode a given packet

        :param message: The raw modbus request packet
        :return: The decoded modbus message or None if error
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")

    def lookupPduClass(self, function_code):
        ''' Use `function_code` to determine the class of the PDU.

        :param function_code: The function code specified in a frame.
        :returns: The class of the PDU that has a matching `function_code`.
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")


class IModbusFramer(object):
    '''
    A framer strategy interface. The idea is that we abstract away all the
    detail about how to detect if a current message frame exists, decoding
    it, sending it, etc so that we can plug in a new Framer object (tcp,
    rtu, ascii).
    '''

    def checkFrame(self):
        ''' Check and decode the next frame

        :returns: True if we successful, False otherwise
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")

    def advanceFrame(self):
        ''' Skip over the current framed message
        This allows us to skip over the current message after we have processed
        it or determined that it contains an error. It also has to reset the
        current frame header handle
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")

    def addToFrame(self, message):
        ''' Add the next message to the frame buffer

        This should be used before the decoding while loop to add the received
        data to the buffer handle.

        :param message: The most recent packet
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")

    def isFrameReady(self):
        ''' Check if we should continue decode logic

        This is meant to be used in a while loop in the decoding phase to let
        the decoder know that there is still data in the buffer.

        :returns: True if ready, False otherwise
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")

    def getFrame(self):
        ''' Get the next frame from the buffer

        :returns: The frame data or ''
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")

    def populateResult(self, result):
        ''' Populates the modbus result with current frame header

        We basically copy the data back over from the current header
        to the result header. This may not be needed for serial messages.

        :param result: The response packet
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")

    def processIncomingPacket(self, data, callback):
        ''' The new packet processing pattern

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.  This handles the case when we read N + 1 or 1 / N
        messages at a time instead of 1.

        The processed and decoded messages are pushed to the callback
        function to process and send.

        :param data: The new packet data
        :param callback: The function to send results to
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")

    def buildPacket(self, message):
        ''' Creates a ready to send modbus packet

        The raw packet is built off of a fully populated modbus
        request / response message.

        :param message: The request/response to send
        :returns: The built packet
        '''
        raise NotImplementedException(
            "Method not implemented by derived class")


class IModbusSlaveContext(object):
    '''
    Interface for a modbus slave data context

    Derived classes must implemented the following methods:
            reset(self)
            validate(self, fx, address, count=1)
            getValues(self, fx, address, count=1)
            setValues(self, fx, address, values)
    '''
    __fx_mapper = {2: 'd', 4: 'i'}
    __fx_mapper.update([(i, 'h') for i in [3, 6, 16, 22, 23]])
    __fx_mapper.update([(i, 'c') for i in [1, 5, 15]])

    def decode(self, fx):
        ''' Converts the function code to the datastore to

        :param fx: The function we are working with
        :returns: one of [d(iscretes),i(inputs),h(oliding),c(oils)
        '''
        return self.__fx_mapper[fx]

    def reset(self):
        ''' Resets all the datastores to their default values
        '''
        raise NotImplementedException("Context Reset")

    def validate(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to test
        :returns: True if the request in within range, False otherwise
        '''
        raise NotImplementedException("validate context values")

    def getValues(self, fx, address, count=1):
        ''' Validates the request to make sure it is in range

        :param fx: The function we are working with
        :param address: The starting address
        :param count: The number of values to retrieve
        :returns: The requested values from a:a+c
        '''
        raise NotImplementedException("get context values")

    def setValues(self, fx, address, values):
        ''' Sets the datastore with the supplied values

        :param fx: The function we are working with
        :param address: The starting address
        :param values: The new values to be set
        '''
        raise NotImplementedException("set context values")


class IPayloadBuilder(object):
    '''
    This is an interface to a class that can build a payload
    for a modbus register write command. It should abstract
    the codec for encoding data to the required format
    (bcd, binary, char, etc).
    '''

    def build(self):
        ''' Return the payload buffer as a list

        This list is two bytes per element and can
        thus be treated as a list of registers.

        :returns: The payload buffer as a list
        '''
        raise NotImplementedException("set context values")

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    'Singleton',
    'IModbusDecoder', 'IModbusFramer', 'IModbusSlaveContext',
    'IPayloadBuilder',
]

########NEW FILE########
__FILENAME__ = ptwisted
'''
A collection of twisted utility code
'''
from twisted.cred import portal, checkers
from twisted.conch import manhole, manhole_ssh
from twisted.conch.insults import insults

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Twisted Helper Methods
#---------------------------------------------------------------------------#
def InstallManagementConsole(namespace, users={'admin': 'admin'}, port=503):
    ''' Helper method to start an ssh management console
        for the modbus server.

    :param namespace: The data to constrain the server to
    :param users: The users to login with
    :param port: The port to host the server on
    '''
    from twisted.internet import reactor

    def build_protocol():
        p = insults.ServerProtocol(manhole.ColoredManhole, namespace)
        return p

    r = manhole_ssh.TerminalRealm()
    r.chainedProtocolFactory = build_protocol
    c = checkers.InMemoryUsernamePasswordDatabaseDontUse(**users)
    p = portal.Portal(r, [c])
    factory = manhole_ssh.ConchFactory(p)
    reactor.listenTCP(port, factory)


########NEW FILE########
__FILENAME__ = mei_message
'''
Encapsulated Interface (MEI) Transport Messages
-----------------------------------------------

'''
import struct
from pymodbus.constants import DeviceInformation, MoreData
from pymodbus.pdu import ModbusRequest
from pymodbus.pdu import ModbusResponse
from pymodbus.device import ModbusControlBlock
from pymodbus.device import DeviceInformationFactory
from pymodbus.pdu import ModbusExceptions as merror

_MCB = ModbusControlBlock()


#---------------------------------------------------------------------------#
# Read Device Information
#---------------------------------------------------------------------------#
class ReadDeviceInformationRequest(ModbusRequest):
    '''
    This function code allows reading the identification and additional
    information relative to the physical and functional description of a
    remote device, only.

    The Read Device Identification interface is modeled as an address space
    composed of a set of addressable data elements. The data elements are
    called objects and an object Id identifies them.  
    '''
    function_code = 0x2b
    sub_function_code = 0x0e
    _rtu_frame_size = 3

    def __init__(self, read_code=None, object_id=0x00, **kwargs):
        ''' Initializes a new instance

        :param read_code: The device information read code
        :param object_id: The object to read from
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.read_code = read_code or DeviceInformation.Basic
        self.object_id = object_id

    def encode(self):
        ''' Encodes the request packet

        :returns: The byte encoded packet
        '''
        packet = struct.pack('>BBB', self.sub_function_code,
            self.read_code, self.object_id)
        return packet

    def decode(self, data):
        ''' Decodes data part of the message.

        :param data: The incoming data
        '''
        params = struct.unpack('>BBB', data)
        self.sub_function_code, self.read_code, self.object_id = params

    def execute(self, context):
        ''' Run a read exeception status request against the store

        :param context: The datastore to request from
        :returns: The populated response
        '''
        if not (0x00 <= self.object_id <= 0xff):
            return self.doException(merror.IllegalValue)
        if not (0x00 <= self.read_code <= 0x04):
            return self.doException(merror.IllegalValue)

        information = DeviceInformationFactory.get(_MCB,
            self.read_code, self.object_id)
        return ReadDeviceInformationResponse(self.read_code, information)

    def __str__(self):
        ''' Builds a representation of the request

        :returns: The string representation of the request
        '''
        params = (self.read_code, self.object_id)
        return "ReadDeviceInformationRequest(%d,%d)" % params


class ReadDeviceInformationResponse(ModbusResponse):
    '''
    '''
    function_code = 0x2b
    sub_function_code = 0x0e

    @classmethod
    def calculateRtuFrameSize(cls, buffer):
        ''' Calculates the size of the message

        :param buffer: A buffer containing the data that have been received.
        :returns: The number of bytes in the response.
        '''
        size  = 8 # skip the header information
        count = struct.unpack('>B', buffer[7])[0]

        while count > 0:
            _, object_length = struct.unpack('>BB', buffer[size:size+2])
            size += object_length + 2
            count -= 1
        return size + 2

    def __init__(self, read_code=None, information=None, **kwargs):
        ''' Initializes a new instance

        :param read_code: The device information read code
        :param information: The requested information request
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.read_code = read_code or DeviceInformation.Basic
        self.information = information or {}
        self.number_of_objects = len(self.information)
        self.conformity = 0x83 # I support everything right now

        # TODO calculate
        self.next_object_id = 0x00 # self.information[-1](0)
        self.more_follows = MoreData.Nothing

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        packet = struct.pack('>BBBBBB', self.sub_function_code,
            self.read_code, self.conformity, self.more_follows,
            self.next_object_id, self.number_of_objects)

        for (object_id, data) in self.information.iteritems():
            packet += struct.pack('>BB', object_id, len(data))
            packet += data

        return packet

    def decode(self, data):
        ''' Decodes a the response

        :param data: The packet data to decode
        '''
        params = struct.unpack('>BBBBBB', data[0:6])
        self.sub_function_code, self.read_code = params[0:2]
        self.conformity, self.more_follows = params[2:4]
        self.next_object_id, self.number_of_objects = params[4:6]
        self.information, count = {}, 6 # skip the header information

        while count < len(data):
            object_id, object_length = struct.unpack('>BB', data[count:count+2])
            count += object_length + 2
            self.information[object_id] = data[count-object_length:count]

    def __str__(self):
        ''' Builds a representation of the response

        :returns: The string representation of the response
        '''
        return "ReadDeviceInformationResponse(%d)" % self.read_code

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "ReadDeviceInformationRequest", "ReadDeviceInformationResponse",
]

########NEW FILE########
__FILENAME__ = other_message
'''
Diagnostic record read/write

Currently not all implemented
'''
import struct
from pymodbus.constants import ModbusStatus
from pymodbus.pdu import ModbusRequest
from pymodbus.pdu import ModbusResponse
from pymodbus.device import ModbusControlBlock

_MCB = ModbusControlBlock()


#---------------------------------------------------------------------------#
# TODO Make these only work on serial
#---------------------------------------------------------------------------#
class ReadExceptionStatusRequest(ModbusRequest):
    '''
    This function code is used to read the contents of eight Exception Status
    outputs in a remote device.  The function provides a simple method for
    accessing this information, because the Exception Output references are
    known (no output reference is needed in the function).
    '''
    function_code = 0x07
    _rtu_frame_size = 4

    def __init__(self, **kwargs):
        ''' Initializes a new instance
        '''
        ModbusRequest.__init__(self, **kwargs)

    def encode(self):
        ''' Encodes the message
        '''
        return ''

    def decode(self, data):
        ''' Decodes data part of the message.

        :param data: The incoming data
        '''
        pass

    def execute(self):
        ''' Run a read exeception status request against the store

        :returns: The populated response
        '''
        status = _MCB.Counter.summary()
        return ReadExceptionStatusResponse(status)

    def __str__(self):
        ''' Builds a representation of the request

        :returns: The string representation of the request
        '''
        return "ReadExceptionStatusRequest(%d)" % (self.function_code)


class ReadExceptionStatusResponse(ModbusResponse):
    '''
    The normal response contains the status of the eight Exception Status
    outputs. The outputs are packed into one data byte, with one bit
    per output. The status of the lowest output reference is contained
    in the least significant bit of the byte.  The contents of the eight
    Exception Status outputs are device specific.
    '''
    function_code = 0x07
    _rtu_frame_size = 5

    def __init__(self, status=0x00, **kwargs):
        ''' Initializes a new instance

        :param status: The status response to report
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.status = status

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        return struct.pack('>B', self.status)

    def decode(self, data):
        ''' Decodes a the response

        :param data: The packet data to decode
        '''
        self.status = struct.unpack('>B', data)[0]

    def __str__(self):
        ''' Builds a representation of the response

        :returns: The string representation of the response
        '''
        arguments = (self.function_code, self.status)
        return "ReadExceptionStatusResponse(%d, %s)" % arguments

# Encapsulate interface transport 43, 14
# CANopen general reference 43, 13


#---------------------------------------------------------------------------#
# TODO Make these only work on serial
#---------------------------------------------------------------------------#
class GetCommEventCounterRequest(ModbusRequest):
    '''
    This function code is used to get a status word and an event count from
    the remote device's communication event counter.

    By fetching the current count before and after a series of messages, a
    client can determine whether the messages were handled normally by the
    remote device.

    The device's event counter is incremented once  for each successful
    message completion. It is not incremented for exception responses,
    poll commands, or fetch event counter commands.

    The event counter can be reset by means of the Diagnostics function
    (code 08), with a subfunction of Restart Communications Option
    (code 00 01) or Clear Counters and Diagnostic Register (code 00 0A).
    '''
    function_code = 0x0b
    _rtu_frame_size = 4

    def __init__(self, **kwargs):
        ''' Initializes a new instance
        '''
        ModbusRequest.__init__(self, **kwargs)

    def encode(self):
        ''' Encodes the message
        '''
        return ''

    def decode(self, data):
        ''' Decodes data part of the message.

        :param data: The incoming data
        '''
        pass

    def execute(self):
        ''' Run a read exeception status request against the store

        :returns: The populated response
        '''
        status = _MCB.Counter.Event
        return GetCommEventCounterResponse(status)

    def __str__(self):
        ''' Builds a representation of the request

        :returns: The string representation of the request
        '''
        return "GetCommEventCounterRequest(%d)" % (self.function_code)


class GetCommEventCounterResponse(ModbusResponse):
    '''
    The normal response contains a two-byte status word, and a two-byte
    event count. The status word will be all ones (FF FF hex) if a
    previously-issued program command is still being processed by the
    remote device (a busy condition exists). Otherwise, the status word
    will be all zeros.
    '''
    function_code = 0x0b
    _rtu_frame_size = 8

    def __init__(self, count=0x0000, **kwargs):
        ''' Initializes a new instance

        :param count: The current event counter value
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.count = count
        self.status = True  # this means we are ready, not waiting

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        if self.status: ready = ModbusStatus.Ready
        else: ready = ModbusStatus.Waiting
        return struct.pack('>HH', ready, self.count)

    def decode(self, data):
        ''' Decodes a the response

        :param data: The packet data to decode
        '''
        ready, self.count = struct.unpack('>HH', data)
        self.status = (ready == ModbusStatus.Ready)

    def __str__(self):
        ''' Builds a representation of the response

        :returns: The string representation of the response
        '''
        arguments = (self.function_code, self.count, self.status)
        return "GetCommEventCounterResponse(%d, %d, %d)" % arguments


#---------------------------------------------------------------------------#
# TODO Make these only work on serial
#---------------------------------------------------------------------------#
class GetCommEventLogRequest(ModbusRequest):
    '''
    This function code is used to get a status word, event count, message
    count, and a field of event bytes from the remote device.

    The status word and event counts are identical  to that returned by
    the Get Communications Event Counter function (11, 0B hex).

    The message counter contains the quantity of  messages processed by the
    remote device since its last restart, clear counters operation, or
    power-up.  This count is identical to that returned by the Diagnostic
    function (code 08), sub-function Return Bus Message Count (code 11,
    0B hex).

    The event bytes field contains 0-64 bytes, with each byte corresponding
    to the status of one MODBUS send or receive operation for the remote
    device.  The remote device enters the events into the field in
    chronological order.  Byte 0 is the most recent event. Each new byte
    flushes the oldest byte from the field.
    '''
    function_code = 0x0c
    _rtu_frame_size = 4

    def __init__(self, **kwargs):
        ''' Initializes a new instance
        '''
        ModbusRequest.__init__(self, **kwargs)

    def encode(self):
        ''' Encodes the message
        '''
        return ''

    def decode(self, data):
        ''' Decodes data part of the message.

        :param data: The incoming data
        '''
        pass

    def execute(self):
        ''' Run a read exeception status request against the store

        :returns: The populated response
        '''
        results = {
            'status'        : True,
            'message_count' : _MCB.Counter.BusMessage,
            'event_count'   : _MCB.Counter.Event,
            'events'        : _MCB.getEvents(),
        }
        return GetCommEventLogResponse(**results)

    def __str__(self):
        ''' Builds a representation of the request

        :returns: The string representation of the request
        '''
        return "GetCommEventLogRequest(%d)" % self.function_code


class GetCommEventLogResponse(ModbusResponse):
    '''
    The normal response contains a two-byte status word field,
    a two-byte event count field, a two-byte message count field,
    and a field containing 0-64 bytes of events. A byte count
    field defines the total length of the data in these four field
    '''
    function_code = 0x0c
    _rtu_byte_count_pos = 3

    def __init__(self, **kwargs):
        ''' Initializes a new instance

        :param status: The status response to report
        :param message_count: The current message count
        :param event_count: The current event count
        :param events: The collection of events to send
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.status = kwargs.get('status', True)
        self.message_count = kwargs.get('message_count', 0)
        self.event_count = kwargs.get('event_count', 0)
        self.events = kwargs.get('events', [])

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        if self.status: ready = ModbusStatus.Ready
        else: ready = ModbusStatus.Waiting
        packet  = struct.pack('>B', 6 + len(self.events))
        packet += struct.pack('>H', ready)
        packet += struct.pack('>HH', self.event_count, self.message_count)
        packet += ''.join(struct.pack('>B', e) for e in self.events)
        return packet

    def decode(self, data):
        ''' Decodes a the response

        :param data: The packet data to decode
        '''
        length = struct.unpack('>B', data[0])[0]
        status = struct.unpack('>H', data[1:3])[0]
        self.status = (status == ModbusStatus.Ready)
        self.event_count = struct.unpack('>H', data[3:5])[0]
        self.message_count = struct.unpack('>H', data[5:7])[0]

        self.events = []
        for e in xrange(7, length + 1):
            self.events.append(struct.unpack('>B', data[e])[0])

    def __str__(self):
        ''' Builds a representation of the response

        :returns: The string representation of the response
        '''
        arguments = (self.function_code, self.status, self.message_count, self.event_count)
        return "GetCommEventLogResponse(%d, %d, %d, %d)" % arguments


#---------------------------------------------------------------------------#
# TODO Make these only work on serial
#---------------------------------------------------------------------------#
class ReportSlaveIdRequest(ModbusRequest):
    '''
    This function code is used to read the description of the type, the
    current status, and other information specific to a remote device.
    '''
    function_code = 0x11
    _rtu_frame_size = 4

    def __init__(self, **kwargs):
        ''' Initializes a new instance
        '''
        ModbusRequest.__init__(self, **kwargs)

    def encode(self):
        ''' Encodes the message
        '''
        return ''

    def decode(self, data):
        ''' Decodes data part of the message.

        :param data: The incoming data
        '''
        pass

    def execute(self):
        ''' Run a read exeception status request against the store

        :returns: The populated response
        '''
        identifier = '\x70\x79\x6d\x6f\x64\x62\x75\x73'
        return ReportSlaveIdResponse(identifier)

    def __str__(self):
        ''' Builds a representation of the request

        :returns: The string representation of the request
        '''
        return "ResportSlaveIdRequest(%d)" % self.function_code


class ReportSlaveIdResponse(ModbusResponse):
    '''
    The format of a normal response is shown in the following example.
    The data contents are specific to each type of device.
    '''
    function_code = 0x11
    _rtu_byte_count_pos = 2

    def __init__(self, identifier='\x00', status=True, **kwargs):
        ''' Initializes a new instance

        :param identifier: The identifier of the slave
        :param status: The status response to report
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.identifier = identifier
        self.status = status

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        if self.status: status = ModbusStatus.SlaveOn
        else: status = ModbusStatus.SlaveOff
        length = len(self.identifier) + 2
        packet = struct.pack('>B', length)
        packet += self.identifier  # we assume it is already encoded
        packet += struct.pack('>B', status)
        return packet

    def decode(self, data):
        ''' Decodes a the response

        Since the identifier is device dependent, we just return the
        raw value that a user can decode to whatever it should be.

        :param data: The packet data to decode
        '''
        length = struct.unpack('>B', data[0])[0]
        self.identifier = data[1:length + 1]
        status = struct.unpack('>B', data[-1])[0]
        self.status = status == ModbusStatus.SlaveOn

    def __str__(self):
        ''' Builds a representation of the response

        :returns: The string representation of the response
        '''
        arguments = (self.function_code, self.identifier, self.status)
        return "ResportSlaveIdResponse(%d, %d, %d)" % arguments

#---------------------------------------------------------------------------#
# TODO Make these only work on serial
#---------------------------------------------------------------------------#
# report device identification 43, 14

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "ReadExceptionStatusRequest", "ReadExceptionStatusResponse",
    "GetCommEventCounterRequest", "GetCommEventCounterResponse",
    "GetCommEventLogRequest", "GetCommEventLogResponse",
    "ReportSlaveIdRequest", "ReportSlaveIdResponse",
]

########NEW FILE########
__FILENAME__ = payload
'''
Modbus Payload Builders
------------------------

A collection of utilities for building and decoding
modbus messages payloads.
'''
from struct import pack, unpack
from pymodbus.interfaces import IPayloadBuilder
from pymodbus.constants import Endian
from pymodbus.utilities import pack_bitstring
from pymodbus.utilities import unpack_bitstring
from pymodbus.exceptions import ParameterException


class BinaryPayloadBuilder(IPayloadBuilder):
    '''
    A utility that helps build payload messages to be
    written with the various modbus messages. It really is just
    a simple wrapper around the struct module, however it saves
    time looking up the format strings. What follows is a simple
    example::

        builder = BinaryPayloadBuilder(endian=Endian.Little)
        builder.add_8bit_uint(1)
        builder.add_16bit_uint(2)
        payload = builder.build()
    '''

    def __init__(self, payload=None, endian=Endian.Little):
        ''' Initialize a new instance of the payload builder

        :param payload: Raw payload data to initialize with
        :param endian: The endianess of the payload
        '''
        self._payload = payload or []
        self._endian  = endian

    def __str__(self):
        ''' Return the payload buffer as a string

        :returns: The payload buffer as a string
        '''
        return ''.join(self._payload)

    def reset(self):
        ''' Reset the payload buffer
        '''
        self._payload = []

    def build(self):
        ''' Return the payload buffer as a list

        This list is two bytes per element and can
        thus be treated as a list of registers.

        :returns: The payload buffer as a list
        '''
        string = str(self)
        length = len(string)
        string = string + ('\x00' * (length % 2))
        return [string[i:i+2] for i in xrange(0, length, 2)]

    def add_bits(self, values):
        ''' Adds a collection of bits to be encoded

        If these are less than a multiple of eight,
        they will be left padded with 0 bits to make
        it so.

        :param value: The value to add to the buffer
        '''
        value = pack_bitstring(values)
        self._payload.append(value)

    def add_8bit_uint(self, value):
        ''' Adds a 8 bit unsigned int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'B'
        self._payload.append(pack(fstring, value))

    def add_16bit_uint(self, value):
        ''' Adds a 16 bit unsigned int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'H'
        self._payload.append(pack(fstring, value))

    def add_32bit_uint(self, value):
        ''' Adds a 32 bit unsigned int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'I'
        self._payload.append(pack(fstring, value))

    def add_64bit_uint(self, value):
        ''' Adds a 64 bit unsigned int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'Q'
        self._payload.append(pack(fstring, value))

    def add_8bit_int(self, value):
        ''' Adds a 8 bit signed int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'b'
        self._payload.append(pack(fstring, value))

    def add_16bit_int(self, value):
        ''' Adds a 16 bit signed int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'h'
        self._payload.append(pack(fstring, value))

    def add_32bit_int(self, value):
        ''' Adds a 32 bit signed int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'i'
        self._payload.append(pack(fstring, value))

    def add_64bit_int(self, value):
        ''' Adds a 64 bit signed int to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'q'
        self._payload.append(pack(fstring, value))

    def add_32bit_float(self, value):
        ''' Adds a 32 bit float to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'f'
        self._payload.append(pack(fstring, value))

    def add_64bit_float(self, value):
        ''' Adds a 64 bit float(double) to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 'd'
        self._payload.append(pack(fstring, value))

    def add_string(self, value):
        ''' Adds a string to the buffer

        :param value: The value to add to the buffer
        '''
        fstring = self._endian + 's'
        for c in value:
            self._payload.append(pack(fstring, c))


class BinaryPayloadDecoder(object):
    '''
    A utility that helps decode payload messages from a modbus
    reponse message.  It really is just a simple wrapper around
    the struct module, however it saves time looking up the format
    strings. What follows is a simple example::

        decoder = BinaryPayloadDecoder(payload)
        first   = decoder.decode_8bit_uint()
        second  = decoder.decode_16bit_uint()
    '''

    def __init__(self, payload, endian=Endian.Little):
        ''' Initialize a new payload decoder

        :param payload: The payload to decode with
        :param endian: The endianess of the payload
        '''
        self._payload = payload
        self._pointer = 0x00
        self._endian  = endian

    @classmethod
    def fromRegisters(klass, registers, endian=Endian.Little):
        ''' Initialize a payload decoder with the result of
        reading a collection of registers from a modbus device.

        The registers are treated as a list of 2 byte values.
        We have to do this because of how the data has already
        been decoded by the rest of the library.

        :param registers: The register results to initialize with
        :param endian: The endianess of the payload
        :returns: An initialized PayloadDecoder
        '''
        if isinstance(registers, list): # repack into flat binary
            payload = ''.join(pack('>H', x) for x in registers)
            return klass(payload, endian)
        raise ParameterException('Invalid collection of registers supplied')

    @classmethod
    def fromCoils(klass, coils, endian=Endian.Little):
        ''' Initialize a payload decoder with the result of
        reading a collection of coils from a modbus device.

        The coils are treated as a list of bit(boolean) values.

        :param coils: The coil results to initialize with
        :param endian: The endianess of the payload
        :returns: An initialized PayloadDecoder
        '''
        if isinstance(coils, list):
            payload = pack_bitstring(coils)
            return klass(payload, endian)
        raise ParameterException('Invalid collection of coils supplied')

    def reset(self):
        ''' Reset the decoder pointer back to the start
        '''
        self._pointer = 0x00

    def decode_8bit_uint(self):
        ''' Decodes a 8 bit unsigned int from the buffer
        '''
        self._pointer += 1
        fstring = self._endian + 'B'
        handle = self._payload[self._pointer - 1:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_bits(self):
        ''' Decodes a byte worth of bits from the buffer
        '''
        self._pointer += 1
        fstring = self._endian + 'B'
        handle = self._payload[self._pointer - 1:self._pointer]
        return unpack_bitstring(handle)

    def decode_16bit_uint(self):
        ''' Decodes a 16 bit unsigned int from the buffer
        '''
        self._pointer += 2
        fstring = self._endian + 'H'
        handle = self._payload[self._pointer - 2:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_32bit_uint(self):
        ''' Decodes a 32 bit unsigned int from the buffer
        '''
        self._pointer += 4
        fstring = self._endian + 'I'
        handle = self._payload[self._pointer - 4:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_64bit_uint(self):
        ''' Decodes a 64 bit unsigned int from the buffer
        '''
        self._pointer += 8
        fstring = self._endian + 'Q'
        handle = self._payload[self._pointer - 8:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_8bit_int(self):
        ''' Decodes a 8 bit signed int from the buffer
        '''
        self._pointer += 1
        fstring = self._endian + 'b'
        handle = self._payload[self._pointer - 1:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_16bit_int(self):
        ''' Decodes a 16 bit signed int from the buffer
        '''
        self._pointer += 2
        fstring = self._endian + 'h'
        handle = self._payload[self._pointer - 2:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_32bit_int(self):
        ''' Decodes a 32 bit signed int from the buffer
        '''
        self._pointer += 4
        fstring = self._endian + 'i'
        handle = self._payload[self._pointer - 4:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_64bit_int(self):
        ''' Decodes a 64 bit signed int from the buffer
        '''
        self._pointer += 8
        fstring = self._endian + 'q'
        handle = self._payload[self._pointer - 8:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_32bit_float(self):
        ''' Decodes a 32 bit float from the buffer
        '''
        self._pointer += 4
        fstring = self._endian + 'f'
        handle = self._payload[self._pointer - 4:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_64bit_float(self):
        ''' Decodes a 64 bit float(double) from the buffer
        '''
        self._pointer += 8
        fstring = self._endian + 'd'
        handle = self._payload[self._pointer - 8:self._pointer]
        return unpack(fstring, handle)[0]

    def decode_string(self, size=1):
        ''' Decodes a string from the buffer

        :param size: The size of the string to decode
        '''
        self._pointer += size
        return self._payload[self._pointer - size:self._pointer]

#---------------------------------------------------------------------------#
# Exported Identifiers
#---------------------------------------------------------------------------#
__all__ = ["BinaryPayloadBuilder", "BinaryPayloadDecoder"]

########NEW FILE########
__FILENAME__ = pdu
'''
Contains base classes for modbus request/response/error packets
'''
from pymodbus.interfaces import Singleton
from pymodbus.exceptions import NotImplementedException
from pymodbus.constants import Defaults
from pymodbus.utilities import rtuFrameSize

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Base PDU's
#---------------------------------------------------------------------------#
class ModbusPDU(object):
    '''
    Base class for all Modbus mesages

    .. attribute:: transaction_id

       This value is used to uniquely identify a request
       response pair.  It can be implemented as a simple counter

    .. attribute:: protocol_id

       This is a constant set at 0 to indicate Modbus.  It is
       put here for ease of expansion.

    .. attribute:: unit_id

       This is used to route the request to the correct child. In
       the TCP modbus, it is used for routing (or not used at all. However,
       for the serial versions, it is used to specify which child to perform
       the requests against. The value 0x00 represents the broadcast address
       (also 0xff).

    .. attribute:: check

       This is used for LRC/CRC in the serial modbus protocols

    .. attribute:: skip_encode

       This is used when the message payload has already been encoded.
       Generally this will occur when the PayloadBuilder is being used
       to create a complicated message. By setting this to True, the
       request will pass the currently encoded message through instead
       of encoding it again.
    '''

    def __init__(self, **kwargs):
        ''' Initializes the base data for a modbus request '''
        self.transaction_id = kwargs.get('transaction', Defaults.TransactionId)
        self.protocol_id = kwargs.get('protocol', Defaults.ProtocolId)
        self.unit_id = kwargs.get('unit', Defaults.UnitId)
        self.skip_encode = kwargs.get('skip_encode', False)
        self.check = 0x0000

    def encode(self):
        ''' Encodes the message

        :raises: A not implemented exception
        '''
        raise NotImplementedException()

    def decode(self, data):
        ''' Decodes data part of the message.

        :param data: is a string object
        :raises: A not implemented exception
        '''
        raise NotImplementedException()

    @classmethod
    def calculateRtuFrameSize(cls, buffer):
        ''' Calculates the size of a PDU.

        :param buffer: A buffer containing the data that have been received.
        :returns: The number of bytes in the PDU.
        '''
        if hasattr(cls, '_rtu_frame_size'):
            return cls._rtu_frame_size
        elif hasattr(cls, '_rtu_byte_count_pos'):
            return rtuFrameSize(buffer, cls._rtu_byte_count_pos)
        else: raise NotImplementedException(
            "Cannot determine RTU frame size for %s" % cls.__name__)


class ModbusRequest(ModbusPDU):
    ''' Base class for a modbus request PDU '''

    def __init__(self, **kwargs):
        ''' Proxy to the lower level initializer '''
        ModbusPDU.__init__(self, **kwargs)

    def doException(self, exception):
        ''' Builds an error response based on the function

        :param exception: The exception to return
        :raises: An exception response
        '''
        _logger.error("Exception Response F(%d) E(%d)" %
                (self.function_code, exception))
        return ExceptionResponse(self.function_code, exception)


class ModbusResponse(ModbusPDU):
    ''' Base class for a modbus response PDU

    .. attribute:: should_respond

       A flag that indicates if this response returns a result back
       to the client issuing the request

    .. attribute:: _rtu_frame_size

       Indicates the size of the modbus rtu response used for
       calculating how much to read.
    '''

    should_respond = True

    def __init__(self, **kwargs):
        ''' Proxy to the lower level initializer '''
        ModbusPDU.__init__(self, **kwargs)


#---------------------------------------------------------------------------#
# Exception PDU's
#---------------------------------------------------------------------------#
class ModbusExceptions(Singleton):
    '''
    An enumeration of the valid modbus exceptions
    '''
    IllegalFunction         = 0x01
    IllegalAddress          = 0x02
    IllegalValue            = 0x03
    SlaveFailure            = 0x04
    Acknowledge             = 0x05
    SlaveBusy               = 0x06
    MemoryParityError       = 0x08
    GatewayPathUnavailable  = 0x0A
    GatewayNoResponse       = 0x0B

    @classmethod
    def decode(cls, code):
        ''' Given an error code, translate it to a
        string error name. 
        
        :param code: The code number to translate
        '''
        values = dict((v, k) for k, v in cls.__dict__.iteritems()
            if not k.startswith('__') and not callable(v))
        return values.get(code, None)


class ExceptionResponse(ModbusResponse):
    ''' Base class for a modbus exception PDU '''
    ExceptionOffset = 0x80
    _rtu_frame_size = 5

    def __init__(self, function_code, exception_code=None, **kwargs):
        ''' Initializes the modbus exception response

        :param function_code: The function to build an exception response for
        :param exception_code: The specific modbus exception to return
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.original_code = function_code
        self.function_code = function_code | self.ExceptionOffset
        self.exception_code = exception_code

    def encode(self):
        ''' Encodes a modbus exception response

        :returns: The encoded exception packet
        '''
        return chr(self.exception_code)

    def decode(self, data):
        ''' Decodes a modbus exception response

        :param data: The packet data to decode
        '''
        self.exception_code = ord(data[0])

    def __str__(self):
        ''' Builds a representation of an exception response

        :returns: The string representation of an exception response
        '''
        message = ModbusExceptions.decode(self.exception_code)
        parameters = (self.function_code, self.original_code, message)
        return "Exception Response(%d, %d, %s)" % parameters


class IllegalFunctionRequest(ModbusRequest):
    '''
    Defines the Modbus slave exception type 'Illegal Function'
    This exception code is returned if the slave::

        - does not implement the function code **or**
        - is not in a state that allows it to process the function
    '''
    ErrorCode = 1

    def __init__(self, function_code, **kwargs):
        ''' Initializes a IllegalFunctionRequest

        :param function_code: The function we are erroring on
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.function_code = function_code

    def decode(self, data):
        ''' This is here so this failure will run correctly

        :param data: Not used
        '''
        pass

    def execute(self, context):
        ''' Builds an illegal function request error response

        :param context: The current context for the message
        :returns: The error response packet
        '''
        return ExceptionResponse(self.function_code, self.ErrorCode)

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    'ModbusRequest', 'ModbusResponse', 'ModbusExceptions',
    'ExceptionResponse', 'IllegalFunctionRequest',
]

########NEW FILE########
__FILENAME__ = register_read_message
'''
Register Reading Request/Response
---------------------------------
'''
import struct
from pymodbus.pdu import ModbusRequest
from pymodbus.pdu import ModbusResponse
from pymodbus.pdu import ModbusExceptions as merror


class ReadRegistersRequestBase(ModbusRequest):
    '''
    Base class for reading a modbus register
    '''
    _rtu_frame_size = 8

    def __init__(self, address, count, **kwargs):
        ''' Initializes a new instance

        :param address: The address to start the read from
        :param count: The number of registers to read
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.address = address
        self.count = count

    def encode(self):
        ''' Encodes the request packet

        :return: The encoded packet
        '''
        return struct.pack('>HH', self.address, self.count)

    def decode(self, data):
        ''' Decode a register request packet

        :param data: The request to decode
        '''
        self.address, self.count = struct.unpack('>HH', data)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "ReadRegisterRequest (%d,%d)" % (self.address, self.count)


class ReadRegistersResponseBase(ModbusResponse):
    '''
    Base class for responsing to a modbus register read
    '''

    _rtu_byte_count_pos = 2

    def __init__(self, values, **kwargs):
        ''' Initializes a new instance

        :param values: The values to write to
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.registers = values or []

    def encode(self):
        ''' Encodes the response packet

        :returns: The encoded packet
        '''
        result = chr(len(self.registers) * 2)
        for register in self.registers:
            result += struct.pack('>H', register)
        return result

    def decode(self, data):
        ''' Decode a register response packet

        :param data: The request to decode
        '''
        byte_count = ord(data[0])
        self.registers = []
        for i in range(1, byte_count + 1, 2):
            self.registers.append(struct.unpack('>H', data[i:i + 2])[0])

    def getRegister(self, index):
        ''' Get the requested register

        :param index: The indexed register to retrieve
        :returns: The request register
        '''
        return self.registers[index]

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "ReadRegisterResponse (%d)" % len(self.registers)


class ReadHoldingRegistersRequest(ReadRegistersRequestBase):
    '''
    This function code is used to read the contents of a contiguous block
    of holding registers in a remote device. The Request PDU specifies the
    starting register address and the number of registers. In the PDU
    Registers are addressed starting at zero. Therefore registers numbered
    1-16 are addressed as 0-15.
    '''
    function_code = 3

    def __init__(self, address=None, count=None, **kwargs):
        ''' Initializes a new instance of the request

        :param address: The starting address to read from
        :param count: The number of registers to read from address
        '''
        ReadRegistersRequestBase.__init__(self, address, count, **kwargs)

    def execute(self, context):
        ''' Run a read holding request against a datastore

        :param context: The datastore to request from
        :returns: An initialized response, exception message otherwise
        '''
        if not (1 <= self.count <= 0x7d):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, self.count):
            return self.doException(merror.IllegalAddress)
        values = context.getValues(self.function_code, self.address, self.count)
        return ReadHoldingRegistersResponse(values)


class ReadHoldingRegistersResponse(ReadRegistersResponseBase):
    '''
    This function code is used to read the contents of a contiguous block
    of holding registers in a remote device. The Request PDU specifies the
    starting register address and the number of registers. In the PDU
    Registers are addressed starting at zero. Therefore registers numbered
    1-16 are addressed as 0-15.
    '''
    function_code = 3

    def __init__(self, values=None, **kwargs):
        ''' Initializes a new response instance

        :param values: The resulting register values
        '''
        ReadRegistersResponseBase.__init__(self, values, **kwargs)


class ReadInputRegistersRequest(ReadRegistersRequestBase):
    '''
    This function code is used to read from 1 to approx. 125 contiguous
    input registers in a remote device. The Request PDU specifies the
    starting register address and the number of registers. In the PDU
    Registers are addressed starting at zero. Therefore input registers
    numbered 1-16 are addressed as 0-15.
    '''
    function_code = 4

    def __init__(self, address=None, count=None, **kwargs):
        ''' Initializes a new instance of the request

        :param address: The starting address to read from
        :param count: The number of registers to read from address
        '''
        ReadRegistersRequestBase.__init__(self, address, count, **kwargs)

    def execute(self, context):
        ''' Run a read input request against a datastore

        :param context: The datastore to request from
        :returns: An initialized response, exception message otherwise
        '''
        if not (1 <= self.count <= 0x7d):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, self.count):
            return self.doException(merror.IllegalAddress)
        values = context.getValues(self.function_code, self.address, self.count)
        return ReadInputRegistersResponse(values)


class ReadInputRegistersResponse(ReadRegistersResponseBase):
    '''
    This function code is used to read from 1 to approx. 125 contiguous
    input registers in a remote device. The Request PDU specifies the
    starting register address and the number of registers. In the PDU
    Registers are addressed starting at zero. Therefore input registers
    numbered 1-16 are addressed as 0-15.
    '''
    function_code = 4

    def __init__(self, values=None, **kwargs):
        ''' Initializes a new response instance

        :param values: The resulting register values
        '''
        ReadRegistersResponseBase.__init__(self, values, **kwargs)


class ReadWriteMultipleRegistersRequest(ModbusRequest):
    '''
    This function code performs a combination of one read operation and one
    write operation in a single MODBUS transaction. The write
    operation is performed before the read.

    Holding registers are addressed starting at zero. Therefore holding
    registers 1-16 are addressed in the PDU as 0-15.

    The request specifies the starting address and number of holding
    registers to be read as well as the starting address, number of holding
    registers, and the data to be written. The byte count specifies the
    number of bytes to follow in the write data field."
    '''
    function_code = 23
    _rtu_byte_count_pos = 10

    def __init__(self, **kwargs):
        ''' Initializes a new request message

        :param read_address: The address to start reading from
        :param read_count: The number of registers to read from address
        :param write_address: The address to start writing to
        :param write_registers: The registers to write to the specified address
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.read_address    = kwargs.get('read_address', 0x00)
        self.read_count      = kwargs.get('read_count', 0)
        self.write_address   = kwargs.get('write_address', 0x00)
        self.write_registers = kwargs.get('write_registers', None)
        if not hasattr(self.write_registers, '__iter__'):
            self.write_registers = [self.write_registers]
        self.write_count = len(self.write_registers)
        self.write_byte_count = self.write_count * 2

    def encode(self):
        ''' Encodes the request packet

        :returns: The encoded packet
        '''
        result = struct.pack('>HHHHB',
                self.read_address,  self.read_count, \
                self.write_address, self.write_count, self.write_byte_count)
        for register in self.write_registers:
            result += struct.pack('>H', register)
        return result

    def decode(self, data):
        ''' Decode the register request packet

        :param data: The request to decode
        '''
        self.read_address,  self.read_count,  \
        self.write_address, self.write_count, \
        self.write_byte_count = struct.unpack('>HHHHB', data[:9])
        self.write_registers  = []
        for i in range(9, self.write_byte_count + 9, 2):
            register = struct.unpack('>H', data[i:i + 2])[0]
            self.write_registers.append(register)

    def execute(self, context):
        ''' Run a write single register request against a datastore

        :param context: The datastore to request from
        :returns: An initialized response, exception message otherwise
        '''
        if not (1 <= self.read_count <= 0x07d):
            return self.doException(merror.IllegalValue)
        if not (1 <= self.write_count <= 0x079):
            return self.doException(merror.IllegalValue)
        if (self.write_byte_count != self.write_count * 2):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.write_address,
                                self.write_count):
            return self.doException(merror.IllegalAddress)
        if not context.validate(self.function_code, self.read_address,
                                self.read_count):
            return self.doException(merror.IllegalAddress)
        context.setValues(self.function_code, self.write_address,
                          self.write_registers)
        registers = context.getValues(self.function_code, self.read_address,
                                      self.read_count)
        return ReadWriteMultipleRegistersResponse(registers)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        params = (self.read_address, self.read_count, self.write_address,
                  self.write_count)
        return "ReadWriteNRegisterRequest R(%d,%d) W(%d,%d)" % params


class ReadWriteMultipleRegistersResponse(ModbusResponse):
    '''
    The normal response contains the data from the group of registers that
    were read. The byte count field specifies the quantity of bytes to
    follow in the read data field.
    '''
    function_code = 23
    _rtu_byte_count_pos = 2

    def __init__(self, values=None, **kwargs):
        ''' Initializes a new instance

        :param values: The register values to write
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.registers = values or []

    def encode(self):
        ''' Encodes the response packet

        :returns: The encoded packet
        '''
        result = chr(len(self.registers) * 2)
        for register in self.registers:
            result += struct.pack('>H', register)
        return result

    def decode(self, data):
        ''' Decode the register response packet

        :param data: The response to decode
        '''
        bytecount = ord(data[0])
        for i in range(1, bytecount, 2):
            self.registers.append(struct.unpack('>H', data[i:i + 2])[0])

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "ReadWriteNRegisterResponse (%d)" % len(self.registers)

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "ReadHoldingRegistersRequest", "ReadHoldingRegistersResponse",
    "ReadInputRegistersRequest", "ReadInputRegistersResponse",
    "ReadWriteMultipleRegistersRequest", "ReadWriteMultipleRegistersResponse",
]

########NEW FILE########
__FILENAME__ = register_write_message
'''
Register Writing Request/Response Messages
-------------------------------------------
'''
import struct
from pymodbus.pdu import ModbusRequest
from pymodbus.pdu import ModbusResponse
from pymodbus.pdu import ModbusExceptions as merror


class WriteSingleRegisterRequest(ModbusRequest):
    '''
    This function code is used to write a single holding register in a
    remote device.

    The Request PDU specifies the address of the register to
    be written. Registers are addressed starting at zero. Therefore register
    numbered 1 is addressed as 0.
    '''
    function_code = 6
    _rtu_frame_size = 8

    def __init__(self, address=None, value=None, **kwargs):
        ''' Initializes a new instance

        :param address: The address to start writing add
        :param value: The values to write
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.address = address
        self.value = value

    def encode(self):
        ''' Encode a write single register packet packet request

        :returns: The encoded packet
        '''
        if self.skip_encode:
            return self.value
        return struct.pack('>HH', self.address, self.value)

    def decode(self, data):
        ''' Decode a write single register packet packet request

        :param data: The request to decode
        '''
        self.address, self.value = struct.unpack('>HH', data)

    def execute(self, context):
        ''' Run a write single register request against a datastore

        :param context: The datastore to request from
        :returns: An initialized response, exception message otherwise
        '''
        if not (0 <= self.value <= 0xffff):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, 1):
            return self.doException(merror.IllegalAddress)

        context.setValues(self.function_code, self.address, [self.value])
        values = context.getValues(self.function_code, self.address, 1)
        return WriteSingleRegisterResponse(self.address, values[0])

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "WriteRegisterRequest %d => %d" % (self.address, self.value)


class WriteSingleRegisterResponse(ModbusResponse):
    '''
    The normal response is an echo of the request, returned after the
    register contents have been written.
    '''
    function_code = 6
    _rtu_frame_size = 8

    def __init__(self, address=None, value=None, **kwargs):
        ''' Initializes a new instance

        :param address: The address to start writing add
        :param value: The values to write
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.address = address
        self.value = value

    def encode(self):
        ''' Encode a write single register packet packet request

        :returns: The encoded packet
        '''
        return struct.pack('>HH', self.address, self.value)

    def decode(self, data):
        ''' Decode a write single register packet packet request

        :param data: The request to decode
        '''
        self.address, self.value = struct.unpack('>HH', data)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        params = (self.address, self.value)
        return "WriteRegisterResponse %d => %d" % params


#---------------------------------------------------------------------------#
# Write Multiple Registers
#---------------------------------------------------------------------------#
class WriteMultipleRegistersRequest(ModbusRequest):
    '''
    This function code is used to write a block of contiguous registers (1
    to approx. 120 registers) in a remote device.

    The requested written values are specified in the request data field.
    Data is packed as two bytes per register.
    '''
    function_code = 16
    _rtu_byte_count_pos = 6

    def __init__(self, address=None, values=None, **kwargs):
        ''' Initializes a new instance

        :param address: The address to start writing to
        :param values: The values to write
        '''
        ModbusRequest.__init__(self, **kwargs)
        self.address = address
        self.values = values or []
        if not hasattr(values, '__iter__'):
            values = [values]
        self.count = len(self.values)
        self.byte_count = self.count * 2

    def encode(self):
        ''' Encode a write single register packet packet request

        :returns: The encoded packet
        '''
        packet = struct.pack('>HHB', self.address, self.count, self.byte_count)
        if self.skip_encode:
            return packet + ''.join(self.values)
        
        for value in self.values:
            packet += struct.pack('>H', value)

        return packet

    def decode(self, data):
        ''' Decode a write single register packet packet request

        :param data: The request to decode
        '''
        self.address, self.count, \
        self.byte_count = struct.unpack('>HHB', data[:5])
        self.values = []  # reset
        for idx in range(5, (self.count * 2) + 5, 2):
            self.values.append(struct.unpack('>H', data[idx:idx + 2])[0])

    def execute(self, context):
        ''' Run a write single register request against a datastore

        :param context: The datastore to request from
        :returns: An initialized response, exception message otherwise
        '''
        if not (1 <= self.count <= 0x07b):
            return self.doException(merror.IllegalValue)
        if (self.byte_count != self.count * 2):
            return self.doException(merror.IllegalValue)
        if not context.validate(self.function_code, self.address, self.count):
            return self.doException(merror.IllegalAddress)

        context.setValues(self.function_code, self.address, self.values)
        return WriteMultipleRegistersResponse(self.address, self.count)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        params = (self.address, self.count)
        return "WriteMultipleRegisterRequest %d => %d" % params


class WriteMultipleRegistersResponse(ModbusResponse):
    '''
    "The normal response returns the function code, starting address, and
    quantity of registers written.
    '''
    function_code = 16
    _rtu_frame_size = 8

    def __init__(self, address=None, count=None, **kwargs):
        ''' Initializes a new instance

        :param address: The address to start writing to
        :param count: The number of registers to write to
        '''
        ModbusResponse.__init__(self, **kwargs)
        self.address = address
        self.count = count

    def encode(self):
        ''' Encode a write single register packet packet request

        :returns: The encoded packet
        '''
        return struct.pack('>HH', self.address, self.count)

    def decode(self, data):
        ''' Decode a write single register packet packet request

        :param data: The request to decode
        '''
        self.address, self.count = struct.unpack('>HH', data)

    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        params = (self.address, self.count)
        return "WriteMultipleRegisterResponse (%d,%d)" % params

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "WriteSingleRegisterRequest", "WriteSingleRegisterResponse",
    "WriteMultipleRegistersRequest", "WriteMultipleRegistersResponse",
]

########NEW FILE########
__FILENAME__ = async
'''
Implementation of a Twisted Modbus Server
------------------------------------------

'''
from binascii import b2a_hex
from twisted.internet import protocol
from twisted.internet.protocol import ServerFactory

from pymodbus.constants import Defaults
from pymodbus.factory import ServerDecoder
from pymodbus.datastore import ModbusServerContext
from pymodbus.device import ModbusControlBlock
from pymodbus.device import ModbusAccessControl
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.transaction import ModbusSocketFramer, ModbusAsciiFramer
from pymodbus.pdu import ModbusExceptions as merror
from pymodbus.internal.ptwisted import InstallManagementConsole

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Modbus TCP Server
#---------------------------------------------------------------------------#
class ModbusTcpProtocol(protocol.Protocol):
    ''' Implements a modbus server in twisted '''

    def connectionMade(self):
        ''' Callback for when a client connects

        ..note:: since the protocol factory cannot be accessed from the
                 protocol __init__, the client connection made is essentially
                 our __init__ method.
        '''
        _logger.debug("Client Connected [%s]" % self.transport.getHost())
        self.framer = self.factory.framer(decoder=self.factory.decoder)

    def connectionLost(self, reason):
        ''' Callback for when a client disconnects

        :param reason: The client's reason for disconnecting
        '''
        _logger.debug("Client Disconnected: %s" % reason)

    def dataReceived(self, data):
        ''' Callback when we receive any data

        :param data: The data sent by the client
        '''
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(" ".join([hex(ord(x)) for x in data]))
        if not self.factory.control.ListenOnly:
            self.framer.processIncomingPacket(data, self._execute)

    def _execute(self, request):
        ''' Executes the request and returns the result

        :param request: The decoded request message
        '''
        try:
            context = self.factory.store[request.unit_id]
            response = request.execute(context)
        except Exception, ex:
            _logger.debug("Datastore unable to fulfill request: %s" % ex)
            response = request.doException(merror.SlaveFailure)
        #self.framer.populateResult(response)
        response.transaction_id = request.transaction_id
        response.unit_id = request.unit_id
        self._send(response)

    def _send(self, message):
        ''' Send a request (string) to the network

        :param message: The unencoded modbus response
        '''
        if message.should_respond:
            self.factory.control.Counter.BusMessage += 1
            pdu = self.framer.buildPacket(message)
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug('send: %s' % b2a_hex(pdu))
            return self.transport.write(pdu)


class ModbusServerFactory(ServerFactory):
    '''
    Builder class for a modbus server

    This also holds the server datastore so that it is
    persisted between connections
    '''

    protocol = ModbusTcpProtocol

    def __init__(self, store, framer=None, identity=None):
        ''' Overloaded initializer for the modbus factory

        If the identify structure is not passed in, the ModbusControlBlock
        uses its own empty structure.

        :param store: The ModbusServerContext datastore
        :param framer: The framer strategy to use
        :param identity: An optional identify structure

        '''
        self.decoder = ServerDecoder()
        self.framer = framer or ModbusSocketFramer
        self.store = store or ModbusServerContext()
        self.control = ModbusControlBlock()
        self.access = ModbusAccessControl()

        if isinstance(identity, ModbusDeviceIdentification):
            self.control.Identity.update(identity)


#---------------------------------------------------------------------------#
# Modbus UDP Server
#---------------------------------------------------------------------------#
class ModbusUdpProtocol(protocol.DatagramProtocol):
    ''' Implements a modbus udp server in twisted '''

    def __init__(self, store, framer=None, identity=None):
        ''' Overloaded initializer for the modbus factory

        If the identify structure is not passed in, the ModbusControlBlock
        uses its own empty structure.

        :param store: The ModbusServerContext datastore
        :param framer: The framer strategy to use
        :param identity: An optional identify structure

        '''
        framer = framer or ModbusSocketFramer
        self.framer = framer(decoder=ServerDecoder())
        self.store = store or ModbusServerContext()
        self.control = ModbusControlBlock()
        self.access = ModbusAccessControl()

        if isinstance(identity, ModbusDeviceIdentification):
            self.control.Identity.update(identity)

    def datagramReceived(self, data, addr):
        ''' Callback when we receive any data

        :param data: The data sent by the client
        '''
        _logger.debug("Client Connected [%s:%s]" % addr)
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(" ".join([hex(ord(x)) for x in data]))
        if not self.control.ListenOnly:
            continuation = lambda request: self._execute(request, addr)
            self.framer.processIncomingPacket(data, continuation)

    def _execute(self, request, addr):
        ''' Executes the request and returns the result

        :param request: The decoded request message
        '''
        try:
            context = self.store[request.unit_id]
            response = request.execute(context)
        except Exception, ex:
            _logger.debug("Datastore unable to fulfill request: %s" % ex)
            response = request.doException(merror.SlaveFailure)
        #self.framer.populateResult(response)
        response.transaction_id = request.transaction_id
        response.unit_id = request.unit_id
        self._send(response, addr)

    def _send(self, message, addr):
        ''' Send a request (string) to the network

        :param message: The unencoded modbus response
        :param addr: The (host, port) to send the message to
        '''
        self.control.Counter.BusMessage += 1
        pdu = self.framer.buildPacket(message)
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug('send: %s' % b2a_hex(pdu))
        return self.transport.write(pdu, addr)


#---------------------------------------------------------------------------#
# Starting Factories
#---------------------------------------------------------------------------#
def StartTcpServer(context, identity=None, address=None, console=False):
    ''' Helper method to start the Modbus Async TCP server

    :param context: The server data context
    :param identify: The server identity to use (default empty)
    :param address: An optional (interface, port) to bind to.
    :param console: A flag indicating if you want the debug console
    '''
    from twisted.internet import reactor

    address = address or ("", Defaults.Port)
    framer  = ModbusSocketFramer
    factory = ModbusServerFactory(context, framer, identity)
    if console: InstallManagementConsole({'factory': factory})

    _logger.info("Starting Modbus TCP Server on %s:%s" % address)
    reactor.listenTCP(address[1], factory, interface=address[0])
    reactor.run()


def StartUdpServer(context, identity=None, address=None):
    ''' Helper method to start the Modbus Async Udp server

    :param context: The server data context
    :param identify: The server identity to use (default empty)
    :param address: An optional (interface, port) to bind to.
    '''
    from twisted.internet import reactor

    address = address or ("", Defaults.Port)
    framer  = ModbusSocketFramer
    server  = ModbusUdpProtocol(context, framer, identity)

    _logger.info("Starting Modbus UDP Server on %s:%s" % address)
    reactor.listenUDP(address[1], server, interface=address[0])
    reactor.run()


def StartSerialServer(context, identity=None,
    framer=ModbusAsciiFramer, **kwargs):
    ''' Helper method to start the Modbus Async Serial server

    :param context: The server data context
    :param identify: The server identity to use (default empty)
    :param framer: The framer to use (default ModbusAsciiFramer)
    :param port: The serial port to attach to
    :param baudrate: The baud rate to use for the serial device
    :param console: A flag indicating if you want the debug console
    '''
    from twisted.internet import reactor
    from twisted.internet.serialport import SerialPort

    port = kwargs.get('port', '/dev/ttyS0')
    baudrate = kwargs.get('baudrate', Defaults.Baudrate)
    console = kwargs.get('console', False)

    _logger.info("Starting Modbus Serial Server on %s" % port)
    factory = ModbusServerFactory(context, framer, identity)
    if console: InstallManagementConsole({'factory': factory})

    protocol = factory.buildProtocol(None)
    SerialPort.getHost = lambda self: port # hack for logging
    SerialPort(protocol, port, reactor, baudrate)
    reactor.run()

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "StartTcpServer", "StartUdpServer", "StartSerialServer",
]

########NEW FILE########
__FILENAME__ = sync
'''
Implementation of a Threaded Modbus Server
------------------------------------------

'''
from binascii import b2a_hex
import SocketServer
import serial
import socket

from pymodbus.constants import Defaults
from pymodbus.factory import ServerDecoder
from pymodbus.datastore import ModbusServerContext
from pymodbus.device import ModbusControlBlock
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.transaction import *
from pymodbus.exceptions import NotImplementedException
from pymodbus.pdu import ModbusExceptions as merror

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# Protocol Handlers
#---------------------------------------------------------------------------#
class ModbusBaseRequestHandler(SocketServer.BaseRequestHandler):
    ''' Implements the modbus server protocol

    This uses the socketserver.BaseRequestHandler to implement
    the client handler.
    '''

    def setup(self):
        ''' Callback for when a client connects
        '''
        _logger.debug("Client Connected [%s:%s]" % self.client_address)
        self.running = True
        self.framer = self.server.framer(self.server.decoder)
        self.server.threads.append(self)

    def finish(self):
        ''' Callback for when a client disconnects
        '''
        _logger.debug("Client Disconnected [%s:%s]" % self.client_address)
        self.server.threads.remove(self)

    def execute(self, request):
        ''' The callback to call with the resulting message

        :param request: The decoded request message
        '''
        try:
            context = self.server.context[request.unit_id]
            response = request.execute(context)
        except Exception, ex:
            _logger.debug("Datastore unable to fulfill request: %s" % ex)
            response = request.doException(merror.SlaveFailure)
        response.transaction_id = request.transaction_id
        response.unit_id = request.unit_id
        self.send(response)

    #---------------------------------------------------------------------------#
    # Base class implementations
    #---------------------------------------------------------------------------#
    def handle(self):
        ''' Callback when we receive any data
        '''
        raise NotImplementedException("Method not implemented by derived class")

    def send(self, message):
        ''' Send a request (string) to the network

        :param message: The unencoded modbus response
        '''
        raise NotImplementedException("Method not implemented by derived class")


class ModbusSingleRequestHandler(ModbusBaseRequestHandler):
    ''' Implements the modbus server protocol

    This uses the socketserver.BaseRequestHandler to implement
    the client handler for a single client(serial clients)
    '''

    def handle(self):
        ''' Callback when we receive any data
        '''
        while self.running:
            try:
                data = self.request.recv(1024)
                if data:
                    if _logger.isEnabledFor(logging.DEBUG):
                        _logger.debug(" ".join([hex(ord(x)) for x in data]))
                    self.framer.processIncomingPacket(data, self.execute)
            except Exception, msg:
                # since we only have a single socket, we cannot exit
                _logger.error("Socket error occurred %s" % msg)

    def send(self, message):
        ''' Send a request (string) to the network

        :param message: The unencoded modbus response
        '''
        if message.should_respond:
            #self.server.control.Counter.BusMessage += 1
            pdu = self.framer.buildPacket(message)
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug('send: %s' % b2a_hex(pdu))
            return self.request.send(pdu)


class ModbusConnectedRequestHandler(ModbusBaseRequestHandler):
    ''' Implements the modbus server protocol

    This uses the socketserver.BaseRequestHandler to implement
    the client handler for a connected protocol (TCP).
    '''

    def handle(self):
        ''' Callback when we receive any data
        '''
        while self.running:
            try:
                data = self.request.recv(1024)
                if not data: self.running = False
                if _logger.isEnabledFor(logging.DEBUG):
                    _logger.debug(" ".join([hex(ord(x)) for x in data]))
                # if not self.server.control.ListenOnly:
                self.framer.processIncomingPacket(data, self.execute)
            except socket.timeout: pass
            except socket.error, msg:
                _logger.error("Socket error occurred %s" % msg)
                self.running = False
            except: self.running = False

    def send(self, message):
        ''' Send a request (string) to the network

        :param message: The unencoded modbus response
        '''
        if message.should_respond:
            #self.server.control.Counter.BusMessage += 1
            pdu = self.framer.buildPacket(message)
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug('send: %s' % b2a_hex(pdu))
            return self.request.send(pdu)


class ModbusDisconnectedRequestHandler(ModbusBaseRequestHandler):
    ''' Implements the modbus server protocol

    This uses the socketserver.BaseRequestHandler to implement
    the client handler for a disconnected protocol (UDP). The
    only difference is that we have to specify who to send the
    resulting packet data to.
    '''

    def handle(self):
        ''' Callback when we receive any data
        '''
        while self.running:
            try:
                data, self.request = self.request
                if not data: self.running = False
                if _logger.isEnabledFor(logging.DEBUG):
                    _logger.debug(" ".join([hex(ord(x)) for x in data]))
                # if not self.server.control.ListenOnly:
                self.framer.processIncomingPacket(data, self.execute)
            except socket.timeout: pass
            except socket.error, msg:
                _logger.error("Socket error occurred %s" % msg)
                self.running = False
            except: self.running = False

    def send(self, message):
        ''' Send a request (string) to the network

        :param message: The unencoded modbus response
        '''
        if message.should_respond:
            #self.server.control.Counter.BusMessage += 1
            pdu = self.framer.buildPacket(message)
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug('send: %s' % b2a_hex(pdu))
            return self.request.sendto(pdu, self.client_address)


#---------------------------------------------------------------------------#
# Server Implementations
#---------------------------------------------------------------------------#
class ModbusTcpServer(SocketServer.ThreadingTCPServer):
    '''
    A modbus threaded tcp socket server

    We inherit and overload the socket server so that we
    can control the client threads as well as have a single
    server context instance.
    '''

    def __init__(self, context, framer=None, identity=None, address=None):
        ''' Overloaded initializer for the socket server

        If the identify structure is not passed in, the ModbusControlBlock
        uses its own empty structure.

        :param context: The ModbusServerContext datastore
        :param framer: The framer strategy to use
        :param identity: An optional identify structure
        :param address: An optional (interface, port) to bind to.
        '''
        self.threads = []
        self.decoder = ServerDecoder()
        self.framer  = framer  or ModbusSocketFramer
        self.context = context or ModbusServerContext()
        self.control = ModbusControlBlock()
        self.address = address or ("", Defaults.Port)

        if isinstance(identity, ModbusDeviceIdentification):
            self.control.Identity.update(identity)

        SocketServer.ThreadingTCPServer.__init__(self,
            self.address, ModbusConnectedRequestHandler)

    def process_request(self, request, client):
        ''' Callback for connecting a new client thread

        :param request: The request to handle
        :param client: The address of the client
        '''
        _logger.debug("Started thread to serve client at " + str(client))
        SocketServer.ThreadingTCPServer.process_request(self, request, client)

    def server_close(self):
        ''' Callback for stopping the running server
        '''
        _logger.debug("Modbus server stopped")
        self.socket.close()
        for thread in self.threads:
            thread.running = False


class ModbusUdpServer(SocketServer.ThreadingUDPServer):
    '''
    A modbus threaded udp socket server

    We inherit and overload the socket server so that we
    can control the client threads as well as have a single
    server context instance.
    '''

    def __init__(self, context, framer=None, identity=None, address=None):
        ''' Overloaded initializer for the socket server

        If the identify structure is not passed in, the ModbusControlBlock
        uses its own empty structure.

        :param context: The ModbusServerContext datastore
        :param framer: The framer strategy to use
        :param identity: An optional identify structure
        :param address: An optional (interface, port) to bind to.
        '''
        self.threads = []
        self.decoder = ServerDecoder()
        self.framer  = framer  or ModbusSocketFramer
        self.context = context or ModbusServerContext()
        self.control = ModbusControlBlock()
        self.address = address or ("", Defaults.Port)

        if isinstance(identity, ModbusDeviceIdentification):
            self.control.Identity.update(identity)

        SocketServer.ThreadingUDPServer.__init__(self,
            self.address, ModbusDisconnectedRequestHandler)

    def process_request(self, request, client):
        ''' Callback for connecting a new client thread

        :param request: The request to handle
        :param client: The address of the client
        '''
        packet, socket = request # TODO I might have to rewrite
        _logger.debug("Started thread to serve client at " + str(client))
        SocketServer.ThreadingUDPServer.process_request(self, request, client)

    def server_close(self):
        ''' Callback for stopping the running server
        '''
        _logger.debug("Modbus server stopped")
        self.socket.close()
        for thread in self.threads:
            thread.running = False


class ModbusSerialServer(object):
    '''
    A modbus threaded udp socket server

    We inherit and overload the socket server so that we
    can control the client threads as well as have a single
    server context instance.
    '''

    def __init__(self, context, framer=None, identity=None, **kwargs):
        ''' Overloaded initializer for the socket server

        If the identify structure is not passed in, the ModbusControlBlock
        uses its own empty structure.

        :param context: The ModbusServerContext datastore
        :param framer: The framer strategy to use
        :param identity: An optional identify structure
        :param port: The serial port to attach to
        :param stopbits: The number of stop bits to use
        :param bytesize: The bytesize of the serial messages
        :param parity: Which kind of parity to use
        :param baudrate: The baud rate to use for the serial device
        :param timeout: The timeout to use for the serial device

        '''
        self.threads = []
        self.decoder = ServerDecoder()
        self.framer  = framer  or ModbusAsciiFramer
        self.context = context or ModbusServerContext()
        self.control = ModbusControlBlock()

        if isinstance(identity, ModbusDeviceIdentification):
            self.control.Identity.update(identity)

        self.device   = kwargs.get('port', 0)
        self.stopbits = kwargs.get('stopbits', Defaults.Stopbits)
        self.bytesize = kwargs.get('bytesize', Defaults.Bytesize)
        self.parity   = kwargs.get('parity',   Defaults.Parity)
        self.baudrate = kwargs.get('baudrate', Defaults.Baudrate)
        self.timeout  = kwargs.get('timeout',  Defaults.Timeout)
        self.socket   = None
        self._connect()
        self.is_running = True

    def _connect(self):
        ''' Connect to the serial server

        :returns: True if connection succeeded, False otherwise
        '''
        if self.socket: return True
        try:
            self.socket = serial.Serial(port=self.device, timeout=self.timeout,
                bytesize=self.bytesize, stopbits=self.stopbits,
                baudrate=self.baudrate, parity=self.parity)
        except serial.SerialException, msg:
            _logger.error(msg)
        return self.socket != None

    def _build_handler(self):
        ''' A helper method to create and monkeypatch
            a serial handler.

        :returns: A patched handler
        '''
        request = self.socket
        request.send = request.write
        request.recv = request.read
        handler = ModbusSingleRequestHandler(request,
            (self.device, self.device), self)
        return handler

    def serve_forever(self):
        ''' Callback for connecting a new client thread

        :param request: The request to handle
        :param client: The address of the client
        '''
        _logger.debug("Started thread to serve client")
        handler = self._build_handler()
        while self.is_running:
            handler.handle()

    def server_close(self):
        ''' Callback for stopping the running server
        '''
        _logger.debug("Modbus server stopped")
        self.is_running = False
        self.socket.close()


#---------------------------------------------------------------------------#
# Creation Factories
#---------------------------------------------------------------------------#
def StartTcpServer(context=None, identity=None, address=None):
    ''' A factory to start and run a tcp modbus server

    :param context: The ModbusServerContext datastore
    :param identity: An optional identify structure
    :param address: An optional (interface, port) to bind to.
    '''
    framer = ModbusSocketFramer
    server = ModbusTcpServer(context, framer, identity, address)
    server.serve_forever()


def StartUdpServer(context=None, identity=None, address=None):
    ''' A factory to start and run a udp modbus server

    :param context: The ModbusServerContext datastore
    :param identity: An optional identify structure
    :param address: An optional (interface, port) to bind to.
    '''
    framer = ModbusSocketFramer
    server = ModbusUdpServer(context, framer, identity, address)
    server.serve_forever()


def StartSerialServer(context=None, identity=None, **kwargs):
    ''' A factory to start and run a udp modbus server

    :param context: The ModbusServerContext datastore
    :param identity: An optional identify structure
    :param port: The serial port to attach to
    :param stopbits: The number of stop bits to use
    :param bytesize: The bytesize of the serial messages
    :param parity: Which kind of parity to use
    :param baudrate: The baud rate to use for the serial device
    :param timeout: The timeout to use for the serial device
    '''
    framer = ModbusAsciiFramer
    server = ModbusSerialServer(context, framer, identity, **kwargs)
    server.serve_forever()

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "StartTcpServer", "StartUdpServer", "StartSerialServer"
]

########NEW FILE########
__FILENAME__ = transaction
'''
Collection of transaction based abstractions
'''
import sys
import struct
import socket
from binascii import b2a_hex, a2b_hex

from pymodbus.exceptions import ModbusIOException
from pymodbus.constants  import Defaults
from pymodbus.interfaces import IModbusFramer
from pymodbus.utilities  import checkCRC, computeCRC
from pymodbus.utilities  import checkLRC, computeLRC

#---------------------------------------------------------------------------#
# Logging
#---------------------------------------------------------------------------#
import logging
_logger = logging.getLogger(__name__)


#---------------------------------------------------------------------------#
# The Global Transaction Manager
#---------------------------------------------------------------------------#
class ModbusTransactionManager(object):
    ''' Impelements a transaction for a manager

    The transaction protocol can be represented by the following pseudo code::

        count = 0
        do
          result = send(message)
          if (timeout or result == bad)
             count++
          else break
        while (count < 3)

    This module helps to abstract this away from the framer and protocol.
    '''

    def __init__(self, client, **kwargs):
        ''' Initializes an instance of the ModbusTransactionManager

        :param client: The client socket wrapper
        :param retry_on_empty: Should the client retry on empty
        :param retries: The number of retries to allow
        '''
        self.tid = Defaults.TransactionId
        self.client = client
        self.retry_on_empty = kwargs.get('retry_on_empty', Defaults.RetryOnEmpty)
        self.retries = kwargs.get('retries', Defaults.Retries)

    def execute(self, request):
        ''' Starts the producer to send the next request to
        consumer.write(Frame(request))
        '''
        retries = self.retries
        request.transaction_id = self.getNextTID()
        _logger.debug("Running transaction %d" % request.transaction_id)

        while retries > 0:
            try:
                self.client.connect()
                self.client._send(self.client.framer.buildPacket(request))
                # I need to fix this to read the header and the result size,
                # as this may not read the full result set, but right now
                # it should be fine...
                result = self.client._recv(1024)
                if not result and self.retry_on_empty:
                    retries -= 1
                    continue
                self.client.framer.processIncomingPacket(result, self.addTransaction)
                break;
            except socket.error, msg:
                self.client.close()
                _logger.debug("Transaction failed. (%s) " % msg)
                retries -= 1
        return self.getTransaction(request.transaction_id)

    def addTransaction(self, request, tid=None):
        ''' Adds a transaction to the handler

        This holds the requets in case it needs to be resent.
        After being sent, the request is removed.

        :param request: The request to hold on to
        :param tid: The overloaded transaction id to use
        '''
        raise NotImplementedException("addTransaction")

    def getTransaction(self, tid):
        ''' Returns a transaction matching the referenced tid

        If the transaction does not exist, None is returned

        :param tid: The transaction to retrieve
        '''
        raise NotImplementedException("getTransaction")

    def delTransaction(self, tid):
        ''' Removes a transaction matching the referenced tid

        :param tid: The transaction to remove
        '''
        raise NotImplementedException("delTransaction")

    def getNextTID(self):
        ''' Retrieve the next unique transaction identifier

        This handles incrementing the identifier after
        retrieval

        :returns: The next unique transaction identifier
        '''
        self.tid = (self.tid + 1) & 0xffff
        return self.tid

    def reset(self):
        ''' Resets the transaction identifier '''
        self.tid = Defaults.TransactionId
        self.transactions = type(self.transactions)()


class DictTransactionManager(ModbusTransactionManager):
    ''' Impelements a transaction for a manager where the
    results are keyed based on the supplied transaction id.
    '''

    def __init__(self, client, **kwargs):
        ''' Initializes an instance of the ModbusTransactionManager

        :param client: The client socket wrapper
        '''
        self.transactions = {}
        super(DictTransactionManager, self).__init__(client, **kwargs)

    def __iter__(self):
        ''' Iterater over the current managed transactions

        :returns: An iterator of the managed transactions
        '''
        return iter(self.transactions.keys())

    def addTransaction(self, request, tid=None):
        ''' Adds a transaction to the handler

        This holds the requets in case it needs to be resent.
        After being sent, the request is removed.

        :param request: The request to hold on to
        :param tid: The overloaded transaction id to use
        '''
        tid = tid if tid != None else request.transaction_id
        _logger.debug("adding transaction %d" % tid)
        self.transactions[tid] = request

    def getTransaction(self, tid):
        ''' Returns a transaction matching the referenced tid

        If the transaction does not exist, None is returned

        :param tid: The transaction to retrieve
        '''
        _logger.debug("getting transaction %d" % tid)
        return self.transactions.pop(tid, None)

    def delTransaction(self, tid):
        ''' Removes a transaction matching the referenced tid

        :param tid: The transaction to remove
        '''
        _logger.debug("deleting transaction %d" % tid)
        self.transactions.pop(tid, None)


class FifoTransactionManager(ModbusTransactionManager):
    ''' Impelements a transaction for a manager where the
    results are returned in a FIFO manner.
    '''

    def __init__(self, client, **kwargs):
        ''' Initializes an instance of the ModbusTransactionManager

        :param client: The client socket wrapper
        '''
        super(FifoTransactionManager, self).__init__(client, **kwargs)
        self.transactions = []

    def __iter__(self):
        ''' Iterater over the current managed transactions

        :returns: An iterator of the managed transactions
        '''
        return iter(self.transactions)

    def addTransaction(self, request, tid=None):
        ''' Adds a transaction to the handler

        This holds the requets in case it needs to be resent.
        After being sent, the request is removed.

        :param request: The request to hold on to
        :param tid: The overloaded transaction id to use
        '''
        tid = tid if tid != None else request.transaction_id
        _logger.debug("adding transaction %d" % tid)
        self.transactions.append(request)

    def getTransaction(self, tid):
        ''' Returns a transaction matching the referenced tid

        If the transaction does not exist, None is returned

        :param tid: The transaction to retrieve
        '''
        _logger.debug("getting transaction %s" % str(tid))
        return self.transactions.pop(0) if self.transactions else None

    def delTransaction(self, tid):
        ''' Removes a transaction matching the referenced tid

        :param tid: The transaction to remove
        '''
        _logger.debug("deleting transaction %d" % tid)
        if self.transactions: self.transactions.pop(0)


#---------------------------------------------------------------------------#
# Modbus TCP Message
#---------------------------------------------------------------------------#
class ModbusSocketFramer(IModbusFramer):
    ''' Modbus Socket Frame controller

    Before each modbus TCP message is an MBAP header which is used as a
    message frame.  It allows us to easily separate messages as follows::

        [         MBAP Header         ] [ Function Code] [ Data ]
        [ tid ][ pid ][ length ][ uid ]
          2b     2b     2b        1b           1b           Nb

        while len(message) > 0:
            tid, pid, length`, uid = struct.unpack(">HHHB", message)
            request = message[0:7 + length - 1`]
            message = [7 + length - 1:]

        * length = uid + function code + data
        * The -1 is to account for the uid byte
    '''

    def __init__(self, decoder):
        ''' Initializes a new instance of the framer

        :param decoder: The decoder factory implementation to use
        '''
        self.__buffer = ''
        self.__header = {'tid':0, 'pid':0, 'len':0, 'uid':0}
        self.__hsize  = 0x07
        self.decoder  = decoder

    #-----------------------------------------------------------------------#
    # Private Helper Functions
    #-----------------------------------------------------------------------#
    def checkFrame(self):
        '''
        Check and decode the next frame Return true if we were successful
        '''
        if len(self.__buffer) > self.__hsize:
            self.__header['tid'], self.__header['pid'], \
            self.__header['len'], self.__header['uid'] = struct.unpack(
                    '>HHHB', self.__buffer[0:self.__hsize])

            # someone sent us an error? ignore it
            if self.__header['len'] < 2:
                self.advanceFrame()
            # we have at least a complete message, continue
            elif len(self.__buffer) - self.__hsize + 1 >= self.__header['len']:
                return True
        # we don't have enough of a message yet, wait
        return False

    def advanceFrame(self):
        ''' Skip over the current framed message
        This allows us to skip over the current message after we have processed
        it or determined that it contains an error. It also has to reset the
        current frame header handle
        '''
        length = self.__hsize + self.__header['len'] - 1
        self.__buffer = self.__buffer[length:]
        self.__header = {'tid':0, 'pid':0, 'len':0, 'uid':0}

    def isFrameReady(self):
        ''' Check if we should continue decode logic
        This is meant to be used in a while loop in the decoding phase to let
        the decoder factory know that there is still data in the buffer.

        :returns: True if ready, False otherwise
        '''
        return len(self.__buffer) > self.__hsize

    def addToFrame(self, message):
        ''' Adds new packet data to the current frame buffer

        :param message: The most recent packet
        '''
        self.__buffer += message

    def getFrame(self):
        ''' Return the next frame from the buffered data

        :returns: The next full frame buffer
        '''
        length = self.__hsize + self.__header['len'] - 1
        return self.__buffer[self.__hsize:length]

    def populateResult(self, result):
        '''
        Populates the modbus result with the transport specific header
        information (pid, tid, uid, checksum, etc)

        :param result: The response packet
        '''
        result.transaction_id = self.__header['tid']
        result.protocol_id = self.__header['pid']
        result.unit_id = self.__header['uid']

    #-----------------------------------------------------------------------#
    # Public Member Functions
    #-----------------------------------------------------------------------#
    def processIncomingPacket(self, data, callback):
        ''' The new packet processing pattern

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.  This handles the case when we read N + 1 or 1 / N
        messages at a time instead of 1.

        The processed and decoded messages are pushed to the callback
        function to process and send.

        :param data: The new packet data
        :param callback: The function to send results to
        '''
        _logger.debug(" ".join([hex(ord(x)) for x in data]))
        self.addToFrame(data)
        while self.isFrameReady():
            if self.checkFrame():
                result = self.decoder.decode(self.getFrame())
                if result is None:
                    raise ModbusIOException("Unable to decode request")
                self.populateResult(result)
                self.advanceFrame()
                callback(result)  # defer or push to a thread?
            else: break

    def buildPacket(self, message):
        ''' Creates a ready to send modbus packet

        :param message: The populated request/response to send
        '''
        data = message.encode()
        packet = struct.pack('>HHHBB',
            message.transaction_id,
            message.protocol_id,
            len(data) + 2,
            message.unit_id,
            message.function_code) + data
        return packet


#---------------------------------------------------------------------------#
# Modbus RTU Message
#---------------------------------------------------------------------------#
class ModbusRtuFramer(IModbusFramer):
    '''
    Modbus RTU Frame controller::

        [ Start Wait ] [Address ][ Function Code] [ Data ][ CRC ][  End Wait  ]
          3.5 chars     1b         1b               Nb      2b      3.5 chars

    Wait refers to the amount of time required to transmist at least x many
    characters.  In this case it is 3.5 characters.  Also, if we recieve a
    wait of 1.5 characters at any point, we must trigger an error message.
    Also, it appears as though this message is little endian. The logic is
    simplified as the following::

        block-on-read:
            read until 3.5 delay
            check for errors
            decode

    The following table is a listing of the baud wait times for the specified
    baud rates::

        ------------------------------------------------------------------
         Baud  1.5c (18 bits)   3.5c (38 bits)
        ------------------------------------------------------------------
         1200   13333.3 us       31666.7 us
         4800    3333.3 us        7916.7 us
         9600    1666.7 us        3958.3 us
        19200     833.3 us        1979.2 us
        38400     416.7 us         989.6 us
        ------------------------------------------------------------------
        1 Byte = start + 8 bits + parity + stop = 11 bits
        (1/Baud)(bits) = delay seconds
    '''

    def __init__(self, decoder):
        ''' Initializes a new instance of the framer

        :param decoder: The decoder factory implementation to use
        '''
        self.__buffer = ''
        self.__header = {}
        self.__hsize  = 0x01
        self.__end    = '\x0d\x0a'
        self.__min_frame_size = 4
        self.decoder  = decoder

    #-----------------------------------------------------------------------#
    # Private Helper Functions
    #-----------------------------------------------------------------------#
    def checkFrame(self):
        '''
        Check if the next frame is available. Return True if we were
        successful.
        '''
        try:
            self.populateHeader()
            frame_size = self.__header['len']
            data = self.__buffer[:frame_size - 2]
            crc = self.__buffer[frame_size - 2:frame_size]
            crc_val = (ord(crc[0]) << 8) + ord(crc[1])
            return checkCRC(data, crc_val)
        except (IndexError, KeyError):
            return False

    def advanceFrame(self):
        ''' Skip over the current framed message
        This allows us to skip over the current message after we have processed
        it or determined that it contains an error. It also has to reset the
        current frame header handle
        '''
        self.__buffer = self.__buffer[self.__header['len']:]
        self.__header = {}

    def resetFrame(self):
        ''' Reset the entire message frame.
        This allows us to skip ovver errors that may be in the stream.
        It is hard to know if we are simply out of sync or if there is
        an error in the stream as we have no way to check the start or
        end of the message (python just doesn't have the resolution to
        check for millisecond delays).
        '''
        self.__buffer = ''
        self.__header = {}

    def isFrameReady(self):
        ''' Check if we should continue decode logic
        This is meant to be used in a while loop in the decoding phase to let
        the decoder know that there is still data in the buffer.

        :returns: True if ready, False otherwise
        '''
        return len(self.__buffer) > self.__hsize

    def populateHeader(self):
        ''' Try to set the headers `uid`, `len` and `crc`.

        This method examines `self.__buffer` and writes meta
        information into `self.__header`. It calculates only the
        values for headers that are not already in the dictionary.

        Beware that this method will raise an IndexError if
        `self.__buffer` is not yet long enough.
        '''
        self.__header['uid'] = struct.unpack('>B', self.__buffer[0])[0]
        func_code = struct.unpack('>B', self.__buffer[1])[0]
        pdu_class = self.decoder.lookupPduClass(func_code)
        size = pdu_class.calculateRtuFrameSize(self.__buffer)
        self.__header['len'] = size
        self.__header['crc'] = self.__buffer[size - 2:size]

    def addToFrame(self, message):
        '''
        This should be used before the decoding while loop to add the received
        data to the buffer handle.

        :param message: The most recent packet
        '''
        self.__buffer += message

    def getFrame(self):
        ''' Get the next frame from the buffer

        :returns: The frame data or ''
        '''
        start  = self.__hsize
        end    = self.__header['len'] - 2
        buffer = self.__buffer[start:end]
        if end > 0: return buffer
        return ''

    def populateResult(self, result):
        ''' Populates the modbus result header

        The serial packets do not have any header information
        that is copied.

        :param result: The response packet
        '''
        result.unit_id = self.__header['uid']

    #-----------------------------------------------------------------------#
    # Public Member Functions
    #-----------------------------------------------------------------------#
    def processIncomingPacket(self, data, callback):
        ''' The new packet processing pattern

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.  This handles the case when we read N + 1 or 1 / N
        messages at a time instead of 1.

        The processed and decoded messages are pushed to the callback
        function to process and send.

        :param data: The new packet data
        :param callback: The function to send results to
        '''
        self.addToFrame(data)
        while self.isFrameReady():
            if self.checkFrame():
                result = self.decoder.decode(self.getFrame())
                if result is None:
                    raise ModbusIOException("Unable to decode response")
                self.populateResult(result)
                self.advanceFrame()
                callback(result)  # defer or push to a thread?
            else: self.resetFrame() # clear possible errors

    def buildPacket(self, message):
        ''' Creates a ready to send modbus packet

        :param message: The populated request/response to send
        '''
        data = message.encode()
        packet = struct.pack('>BB',
            message.unit_id,
            message.function_code) + data
        packet += struct.pack(">H", computeCRC(packet))
        return packet


#---------------------------------------------------------------------------#
# Modbus ASCII Message
#---------------------------------------------------------------------------#
class ModbusAsciiFramer(IModbusFramer):
    '''
    Modbus ASCII Frame Controller::

        [ Start ][Address ][ Function ][ Data ][ LRC ][ End ]
          1c        2c         2c         Nc     2c      2c

        * data can be 0 - 2x252 chars
        * end is '\\r\\n' (Carriage return line feed), however the line feed
          character can be changed via a special command
        * start is ':'

    This framer is used for serial transmission.  Unlike the RTU protocol,
    the data in this framer is transferred in plain text ascii.
    '''

    def __init__(self, decoder):
        ''' Initializes a new instance of the framer

        :param decoder: The decoder implementation to use
        '''
        self.__buffer = ''
        self.__header = {'lrc':'0000', 'len':0, 'uid':0x00}
        self.__hsize  = 0x02
        self.__start  = ':'
        self.__end    = "\r\n"
        self.decoder  = decoder

    #-----------------------------------------------------------------------#
    # Private Helper Functions
    #-----------------------------------------------------------------------#
    def checkFrame(self):
        ''' Check and decode the next frame

        :returns: True if we successful, False otherwise
        '''
        start = self.__buffer.find(self.__start)
        if start == -1: return False
        if start > 0 :  # go ahead and skip old bad data
            self.__buffer = self.__buffer[start:]
            start = 0

        end = self.__buffer.find(self.__end)
        if (end != -1):
            self.__header['len'] = end
            self.__header['uid'] = int(self.__buffer[1:3], 16)
            self.__header['lrc'] = int(self.__buffer[end - 2:end], 16)
            data = a2b_hex(self.__buffer[start + 1:end - 2])
            return checkLRC(data, self.__header['lrc'])
        return False

    def advanceFrame(self):
        ''' Skip over the current framed message
        This allows us to skip over the current message after we have processed
        it or determined that it contains an error. It also has to reset the
        current frame header handle
        '''
        self.__buffer = self.__buffer[self.__header['len'] + 2:]
        self.__header = {'lrc':'0000', 'len':0, 'uid':0x00}

    def isFrameReady(self):
        ''' Check if we should continue decode logic
        This is meant to be used in a while loop in the decoding phase to let
        the decoder know that there is still data in the buffer.

        :returns: True if ready, False otherwise
        '''
        return len(self.__buffer) > 1

    def addToFrame(self, message):
        ''' Add the next message to the frame buffer
        This should be used before the decoding while loop to add the received
        data to the buffer handle.

        :param message: The most recent packet
        '''
        self.__buffer += message

    def getFrame(self):
        ''' Get the next frame from the buffer

        :returns: The frame data or ''
        '''
        start  = self.__hsize + 1
        end    = self.__header['len'] - 2
        buffer = self.__buffer[start:end]
        if end > 0: return a2b_hex(buffer)
        return ''

    def populateResult(self, result):
        ''' Populates the modbus result header

        The serial packets do not have any header information
        that is copied.

        :param result: The response packet
        '''
        result.unit_id = self.__header['uid']

    #-----------------------------------------------------------------------#
    # Public Member Functions
    #-----------------------------------------------------------------------#
    def processIncomingPacket(self, data, callback):
        ''' The new packet processing pattern

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.  This handles the case when we read N + 1 or 1 / N
        messages at a time instead of 1.

        The processed and decoded messages are pushed to the callback
        function to process and send.

        :param data: The new packet data
        :param callback: The function to send results to
        '''
        self.addToFrame(data)
        while self.isFrameReady():
            if self.checkFrame():
                result = self.decoder.decode(self.getFrame())
                if result is None:
                    raise ModbusIOException("Unable to decode response")
                self.populateResult(result)
                self.advanceFrame()
                callback(result)  # defer this
            else: break

    def buildPacket(self, message):
        ''' Creates a ready to send modbus packet
        Built off of a  modbus request/response

        :param message: The request/response to send
        :return: The encoded packet
        '''
        encoded  = message.encode()
        buffer   = struct.pack('>BB', message.unit_id, message.function_code)
        checksum = computeLRC(encoded + buffer)

        params = (message.unit_id, message.function_code, b2a_hex(encoded))
        packet = '%02x%02x%s' % params
        packet = '%c%s%02x%s' % (self.__start, packet, checksum, self.__end)
        return packet.upper()


#---------------------------------------------------------------------------#
# Modbus Binary Message
#---------------------------------------------------------------------------#
class ModbusBinaryFramer(IModbusFramer):
    '''
    Modbus Binary Frame Controller::

        [ Start ][Address ][ Function ][ Data ][ CRC ][ End ]
          1b        1b         1b         Nb     2b     1b

        * data can be 0 - 2x252 chars
        * end is   '}'
        * start is '{'

    The idea here is that we implement the RTU protocol, however,
    instead of using timing for message delimiting, we use start
    and end of message characters (in this case { and }). Basically,
    this is a binary framer.

    The only case we have to watch out for is when a message contains
    the { or } characters.  If we encounter these characters, we
    simply duplicate them.  Hopefully we will not encounter those
    characters that often and will save a little bit of bandwitch
    without a real-time system.

    Protocol defined by jamod.sourceforge.net.
    '''

    def __init__(self, decoder):
        ''' Initializes a new instance of the framer

        :param decoder: The decoder implementation to use
        '''
        self.__buffer = ''
        self.__header = {'crc':0x0000, 'len':0, 'uid':0x00}
        self.__hsize  = 0x02
        self.__start  = '\x7b'  # {
        self.__end    = '\x7d'  # }
        self.decoder  = decoder

    #-----------------------------------------------------------------------#
    # Private Helper Functions
    #-----------------------------------------------------------------------#
    def checkFrame(self):
        ''' Check and decode the next frame

        :returns: True if we are successful, False otherwise
        '''
        start = self.__buffer.find(self.__start)
        if start == -1: return False
        if start > 0 :  # go ahead and skip old bad data
            self.__buffer = self.__buffer[start:]

        end = self.__buffer.find(self.__end)
        if (end != -1):
            self.__header['len'] = end
            self.__header['uid'] = struct.unpack('>B', self.__buffer[1:2])
            self.__header['crc'] = struct.unpack('>H', self.__buffer[end - 2:end])[0]
            data = self.__buffer[start + 1:end - 2]
            return checkCRC(data, self.__header['crc'])
        return False

    def advanceFrame(self):
        ''' Skip over the current framed message
        This allows us to skip over the current message after we have processed
        it or determined that it contains an error. It also has to reset the
        current frame header handle
        '''
        self.__buffer = self.__buffer[self.__header['len'] + 2:]
        self.__header = {'crc':0x0000, 'len':0, 'uid':0x00}

    def isFrameReady(self):
        ''' Check if we should continue decode logic
        This is meant to be used in a while loop in the decoding phase to let
        the decoder know that there is still data in the buffer.

        :returns: True if ready, False otherwise
        '''
        return len(self.__buffer) > 1

    def addToFrame(self, message):
        ''' Add the next message to the frame buffer
        This should be used before the decoding while loop to add the received
        data to the buffer handle.

        :param message: The most recent packet
        '''
        self.__buffer += message

    def getFrame(self):
        ''' Get the next frame from the buffer

        :returns: The frame data or ''
        '''
        start  = self.__hsize + 1
        end    = self.__header['len'] - 2
        buffer = self.__buffer[start:end]
        if end > 0: return buffer
        return ''

    def populateResult(self, result):
        ''' Populates the modbus result header

        The serial packets do not have any header information
        that is copied.

        :param result: The response packet
        '''
        result.unit_id = self.__header['uid']

    #-----------------------------------------------------------------------#
    # Public Member Functions
    #-----------------------------------------------------------------------#
    def processIncomingPacket(self, data, callback):
        ''' The new packet processing pattern

        This takes in a new request packet, adds it to the current
        packet stream, and performs framing on it. That is, checks
        for complete messages, and once found, will process all that
        exist.  This handles the case when we read N + 1 or 1 / N
        messages at a time instead of 1.

        The processed and decoded messages are pushed to the callback
        function to process and send.

        :param data: The new packet data
        :param callback: The function to send results to
        '''
        self.addToFrame(data)
        while self.isFrameReady():
            if self.checkFrame():
                result = self.decoder.decode(self.getFrame())
                if result is None:
                    raise ModbusIOException("Unable to decode response")
                self.populateResult(result)
                self.advanceFrame()
                callback(result)  # defer or push to a thread?
            else: break

    def buildPacket(self, message):
        ''' Creates a ready to send modbus packet

        :param message: The request/response to send
        :returns: The encoded packet
        '''
        data = self._preflight(message.encode())
        packet = struct.pack('>BB',
            message.unit_id,
            message.function_code) + data
        packet += struct.pack(">H", computeCRC(packet))
        packet = '%s%s%s' % (self.__start, packet, self.__end)
        return packet

    def _preflight(self, data):
        ''' Preflight buffer test

        This basically scans the buffer for start and end
        tags and if found, escapes them.

        :param data: The message to escape
        :returns: the escaped packet
        '''
        def _filter(a):
            if a in ['}', '{']: return a * 2
            else: return a
        return ''.join(map(_filter, data))

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    "FifoTransactionManager",
    "DictTransactionManager",
    "ModbusSocketFramer", "ModbusRtuFramer",
    "ModbusAsciiFramer", "ModbusBinaryFramer",
]

########NEW FILE########
__FILENAME__ = utilities
'''
Modbus Utilities
-----------------

A collection of utilities for packing data, unpacking
data computing checksums, and decode checksums.
'''
import struct


#---------------------------------------------------------------------------#
# Helpers
#---------------------------------------------------------------------------#
def default(value):
    '''
    Given a python object, return the default value
    of that object.

    :param value: The value to get the default of
    :returns: The default value
    '''
    return type(value)()


def dict_property(store, index):
    ''' Helper to create class properties from a dictionary.
    Basically this allows you to remove a lot of possible
    boilerplate code.

    :param store: The store store to pull from
    :param index: The index into the store to close over
    :returns: An initialized property set
    '''
    if hasattr(store, '__call__'):
        getter = lambda self: store(self)[index]
        setter = lambda self, value: store(self).__setitem__(index, value)
    elif isinstance(store, str):
        getter = lambda self: self.__getattribute__(store)[index]
        setter = lambda self, value: self.__getattribute__(store).__setitem__(
            index, value)
    else:
        getter = lambda self: store[index]
        setter = lambda self, value: store.__setitem__(index, value)

    return property(getter, setter)


#---------------------------------------------------------------------------#
# Bit packing functions
#---------------------------------------------------------------------------#
def pack_bitstring(bits):
    ''' Creates a string out of an array of bits

    :param bits: A bit array

    example::

        bits   = [False, True, False, True]
        result = pack_bitstring(bits)
    '''
    ret = ''
    i = packed = 0
    for bit in bits:
        if bit: packed += 128
        i += 1
        if i == 8:
            ret += chr(packed)
            i = packed = 0
        else: packed >>= 1
    if i > 0 and i < 8:
        packed >>= (7 - i)
        ret += chr(packed)
    return ret


def unpack_bitstring(string):
    ''' Creates bit array out of a string

    :param string: The modbus data packet to decode

    example::

        bytes  = 'bytes to decode'
        result = unpack_bitstring(bytes)
    '''
    byte_count = len(string)
    bits = []
    for byte in range(byte_count):
        value = ord(string[byte])
        for _ in range(8):
            bits.append((value & 1) == 1)
            value >>= 1
    return bits


#---------------------------------------------------------------------------#
# Error Detection Functions
#---------------------------------------------------------------------------#
def __generate_crc16_table():
    ''' Generates a crc16 lookup table

    .. note:: This will only be generated once
    '''
    result = []
    for byte in range(256):
        crc = 0x0000
        for _ in range(8):
            if (byte ^ crc) & 0x0001:
                crc = (crc >> 1) ^ 0xa001
            else: crc >>= 1
            byte >>= 1
        result.append(crc)
    return result

__crc16_table = __generate_crc16_table()


def computeCRC(data):
    ''' Computes a crc16 on the passed in string. For modbus,
    this is only used on the binary serial protocols (in this
    case RTU).

    The difference between modbus's crc16 and a normal crc16
    is that modbus starts the crc value out at 0xffff.

    :param data: The data to create a crc16 of
    :returns: The calculated CRC
    '''
    crc = 0xffff
    for a in data:
        idx = __crc16_table[(crc ^ ord(a)) & 0xff];
        crc = ((crc >> 8) & 0xff) ^ idx
    swapped = ((crc << 8) & 0xff00) | ((crc >> 8) & 0x00ff)
    return swapped


def checkCRC(data, check):
    ''' Checks if the data matches the passed in CRC

    :param data: The data to create a crc16 of
    :param check: The CRC to validate
    :returns: True if matched, False otherwise
    '''
    return computeCRC(data) == check


def computeLRC(data):
    ''' Used to compute the longitudinal redundancy check
    against a string. This is only used on the serial ASCII
    modbus protocol. A full description of this implementation
    can be found in appendex B of the serial line modbus description.

    :param data: The data to apply a lrc to
    :returns: The calculated LRC

    '''
    lrc = sum(ord(a) for a in data) & 0xff
    lrc = (lrc ^ 0xff) + 1
    return lrc & 0xff


def checkLRC(data, check):
    ''' Checks if the passed in data matches the LRC

    :param data: The data to calculate
    :param check: The LRC to validate
    :returns: True if matched, False otherwise
    '''
    return computeLRC(data) == check


def rtuFrameSize(buffer, byte_count_pos):
    ''' Calculates the size of the frame based on the byte count.

    :param buffer: The buffer containing the frame.
    :param byte_count_pos: The index of the byte count in the buffer.
    :returns: The size of the frame.

    The structure of frames with a byte count field is always the
    same:

    - first, there are some header fields
    - then the byte count field
    - then as many data bytes as indicated by the byte count,
    - finally the CRC (two bytes).

    To calculate the frame size, it is therefore sufficient to extract
    the contents of the byte count field, add the position of this
    field, and finally increment the sum by three (one byte for the
    byte count field, two for the CRC).
    '''
    return struct.unpack('>B', buffer[byte_count_pos])[0] + byte_count_pos + 3

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = [
    'pack_bitstring', 'unpack_bitstring', 'default',
    'computeCRC', 'checkCRC', 'computeLRC', 'checkLRC', 'rtuFrameSize'
]

########NEW FILE########
__FILENAME__ = version
'''
Handle the version information here; you should only have to
change the version tuple.

Since we are using twisted's version class, we can also query
the svn version as well using the local .entries file.
'''


class Version(object):

    def __init__(self, package, major, minor, micro):
        '''

        :param package: Name of the package that this is a version of.
        :param major: The major version number.
        :param minor: The minor version number.
        :param micro: The micro version number.
        '''
        self.package = package
        self.major = major
        self.minor = minor
        self.micro = micro

    def short(self):
        ''' Return a string in canonical short version format
        <major>.<minor>.<micro>
        '''
        return '%d.%d.%d' % (self.major, self.minor, self.micro)

    def __str__(self):
        ''' Returns a string representation of the object

        :returns: A string representation of this object
        '''
        return '[%s, version %s]' % (self.package, self.short())

version = Version('pymodbus', 1, 2, 0)
version.__name__ = 'pymodbus'  # fix epydoc error

#---------------------------------------------------------------------------#
# Exported symbols
#---------------------------------------------------------------------------#
__all__ = ["version"]

########NEW FILE########
__FILENAME__ = modbus_mocks
from pymodbus.interfaces import IModbusSlaveContext

#---------------------------------------------------------------------------#
# Mocks
#---------------------------------------------------------------------------#
class mock(object): pass

class MockContext(IModbusSlaveContext):

    def __init__(self, valid=False, default=True):
        self.valid = valid
        self.default = default

    def validate(self, fx, address, count):
        return self.valid

    def getValues(self, fx, address, count):
        return [self.default] * count

    def setValues(self, fx, address, count):
        pass

class FakeList(object):
    ''' todo, replace with magic mock '''

    def __init__(self, size):
        self.size = size

    def __len__(self):
        return self.size

    def __iter__(self):
        return []


########NEW FILE########
__FILENAME__ = test_all_messages
#!/usr/bin/env python
import unittest
from pymodbus.constants import Defaults
from pymodbus.bit_read_message import *
from pymodbus.bit_write_message import *
from pymodbus.register_read_message import *
from pymodbus.register_write_message import *

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class ModbusAllMessagesTests(unittest.TestCase):

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#

    def setUp(self):
        '''
        Initializes the test environment and builds request/result
        encoding pairs
        '''
        arguments = {
            'read_address': 1, 'read_count': 1,
            'write_address': 1, 'write_registers': 1
        }
        self.requests = [
            lambda unit: ReadCoilsRequest(1, 5, unit=unit),
            lambda unit: ReadDiscreteInputsRequest(1, 5, unit=unit),
            lambda unit: WriteSingleCoilRequest(1, 1, unit=unit),
            lambda unit: WriteMultipleCoilsRequest(1, [1], unit=unit),
            lambda unit: ReadHoldingRegistersRequest(1, 5, unit=unit),
            lambda unit: ReadInputRegistersRequest(1, 5, unit=unit),
            lambda unit: ReadWriteMultipleRegistersRequest(unit=unit, **arguments),
            lambda unit: WriteSingleRegisterRequest(1, 1, unit=unit),
            lambda unit: WriteMultipleRegistersRequest(1, [1], unit=unit),
        ]
        self.responses = [
            lambda unit: ReadCoilsResponse([1], unit=unit),
            lambda unit: ReadDiscreteInputsResponse([1], unit=unit),
            lambda unit: WriteSingleCoilResponse(1, 1, unit=unit),
            lambda unit: WriteMultipleCoilsResponse(1, [1], unit=unit),
            lambda unit: ReadHoldingRegistersResponse([1], unit=unit),
            lambda unit: ReadInputRegistersResponse([1], unit=unit),
            lambda unit: ReadWriteMultipleRegistersResponse([1], unit=unit),
            lambda unit: WriteSingleRegisterResponse(1, 1, unit=unit),
            lambda unit: WriteMultipleRegistersResponse(1, 1, unit=unit),
        ]

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    def testInitializingSlaveAddressRequest(self):
        ''' Test that every request can initialize the unit id '''
        unit_id = 0x12
        for factory in self.requests:
            request = factory(unit_id)
            self.assertEqual(request.unit_id, unit_id)

    def testInitializingSlaveAddressResponse(self):
        ''' Test that every response can initialize the unit id '''
        unit_id = 0x12
        for factory in self.responses:
            response = factory(unit_id)
            self.assertEqual(response.unit_id, unit_id)

    def testForwardingKwargsToPdu(self):
        ''' Test that the kwargs are forwarded to the pdu correctly '''
        request = ReadCoilsRequest(1,5, unit=0x12, transaction=0x12, protocol=0x12)
        self.assertEqual(request.unit_id, 0x12)
        self.assertEqual(request.transaction_id, 0x12)
        self.assertEqual(request.protocol_id, 0x12)

        request = ReadCoilsRequest(1,5)
        self.assertEqual(request.unit_id, Defaults.UnitId)
        self.assertEqual(request.transaction_id, Defaults.TransactionId)
        self.assertEqual(request.protocol_id, Defaults.ProtocolId)

########NEW FILE########
__FILENAME__ = test_bit_read_messages
#!/usr/bin/env python
'''
Bit Message Test Fixture
--------------------------------
This fixture tests the functionality of all the 
bit based request/response messages:

* Read/Write Discretes
* Read Coils
'''
import unittest, struct
from pymodbus.bit_read_message import *
from pymodbus.bit_read_message import ReadBitsRequestBase
from pymodbus.bit_read_message import ReadBitsResponseBase
from pymodbus.exceptions import *
from pymodbus.pdu import ModbusExceptions

from modbus_mocks import MockContext

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class ModbusBitMessageTests(unittest.TestCase):

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#

    def setUp(self):
        '''
        Initializes the test environment and builds request/result
        encoding pairs
        '''
        pass

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    def testReadBitBaseClassMethods(self):
        ''' Test basic bit message encoding/decoding '''
        handle = ReadBitsRequestBase(1, 1)
        msg    = "ReadBitRequest(1,1)"
        self.assertEqual(msg, str(handle))
        handle = ReadBitsResponseBase([1,1])
        msg    = "ReadBitResponse(2)"
        self.assertEqual(msg, str(handle))

    def testBitReadBaseRequestEncoding(self):
        ''' Test basic bit message encoding/decoding '''
        for i in xrange(20):
            handle = ReadBitsRequestBase(i, i)
            result = struct.pack('>HH',i, i)
            self.assertEqual(handle.encode(), result)
            handle.decode(result)
            self.assertEqual((handle.address, handle.count), (i,i))

    def testBitReadBaseResponseEncoding(self):
        ''' Test basic bit message encoding/decoding '''
        for i in xrange(20):
            input  = [True] * i
            handle = ReadBitsResponseBase(input)
            result = handle.encode()
            handle.decode(result)
            self.assertEqual(handle.bits[:i], input)

    def testBitReadBaseResponseHelperMethods(self):
        ''' Test the extra methods on a ReadBitsResponseBase '''
        input  = [False] * 8
        handle = ReadBitsResponseBase(input)
        for i in [1,3,5]: handle.setBit(i, True)
        for i in [1,3,5]: handle.resetBit(i)
        for i in xrange(8):
            self.assertEqual(handle.getBit(i), False)

    def testBitReadBaseRequests(self):
        ''' Test bit read request encoding '''
        messages = {
            ReadBitsRequestBase(12, 14)        : '\x00\x0c\x00\x0e',
            ReadBitsResponseBase([1,0,1,1,0])  : '\x01\x0d',
        }
        for request, expected in messages.iteritems():
            self.assertEqual(request.encode(), expected)

    def testBitReadMessageExecuteValueErrors(self):
        ''' Test bit read request encoding '''
        context = MockContext()
        requests = [
            ReadCoilsRequest(1,0x800),
            ReadDiscreteInputsRequest(1,0x800),
        ]
        for request in requests:
            result = request.execute(context)
            self.assertEqual(ModbusExceptions.IllegalValue,
                result.exception_code)

    def testBitReadMessageExecuteAddressErrors(self):
        ''' Test bit read request encoding '''
        context = MockContext()
        requests = [
            ReadCoilsRequest(1,5),
            ReadDiscreteInputsRequest(1,5),
        ]
        for request in requests:
            result = request.execute(context)
            self.assertEqual(ModbusExceptions.IllegalAddress, result.exception_code)

    def testBitReadMessageExecuteSuccess(self):
        ''' Test bit read request encoding '''
        context = MockContext()
        context.validate = lambda a,b,c: True
        requests = [
            ReadCoilsRequest(1,5),
            ReadDiscreteInputsRequest(1,5),
        ]
        for request in requests:
            result = request.execute(context)
            self.assertEqual(result.bits, [True] * 5)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_bit_write_messages
#!/usr/bin/env python
'''
Bit Message Test Fixture
--------------------------------
This fixture tests the functionality of all the 
bit based request/response messages:

* Read/Write Discretes
* Read Coils
'''
import unittest
from pymodbus.bit_write_message import *
from pymodbus.exceptions import *
from pymodbus.pdu import ModbusExceptions

from modbus_mocks import MockContext, FakeList

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class ModbusBitMessageTests(unittest.TestCase):

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#

    def setUp(self):
        '''
        Initializes the test environment and builds request/result
        encoding pairs
        '''
        pass

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    def testBitWriteBaseRequests(self):
        messages = {
            WriteSingleCoilRequest(1, 0xabcd)      : '\x00\x01\xff\x00',
            WriteSingleCoilResponse(1, 0xabcd)     : '\x00\x01\xff\x00',
            WriteMultipleCoilsRequest(1, [True]*5) : '\x00\x01\x00\x05\x01\x1f',
            WriteMultipleCoilsResponse(1, 5)       : '\x00\x01\x00\x05',
        }
        for request, expected in messages.iteritems():
            self.assertEqual(request.encode(), expected)

    def testWriteMultipleCoilsRequest(self):
        request = WriteMultipleCoilsRequest(1, [True]*5)
        request.decode('\x00\x01\x00\x05\x01\x1f')
        self.assertEqual(request.byte_count, 1)
        self.assertEqual(request.address, 1)
        self.assertEqual(request.values, [True]*5)

    def testInvalidWriteMultipleCoilsRequest(self):
        request = WriteMultipleCoilsRequest(1, None)
        self.assertEquals(request.values, [])

    def testWriteSingleCoilRequestEncode(self):
        request = WriteSingleCoilRequest(1, False)
        self.assertEquals(request.encode(), '\x00\x01\x00\x00')

    def testWriteSingleCoilExecute(self):
        context = MockContext(False, default=True)
        request = WriteSingleCoilRequest(2, True)
        result  = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalAddress)

        context.valid = True
        result = request.execute(context)
        self.assertEqual(result.encode(), '\x00\x02\xff\x00')

        context = MockContext(True, default=False)
        request = WriteSingleCoilRequest(2, False)
        result = request.execute(context)
        self.assertEqual(result.encode(), '\x00\x02\x00\x00')

    def testWriteMultipleCoilsExecute(self):
        context = MockContext(False)
        # too many values
        request = WriteMultipleCoilsRequest(2, FakeList(0x123456))
        result  = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalValue)

        # bad byte count
        request = WriteMultipleCoilsRequest(2, [0x00]*4)
        request.byte_count = 0x00
        result  = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalValue)

        # does not validate
        context.valid = False
        request = WriteMultipleCoilsRequest(2, [0x00]*4)
        result  = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalAddress)

        # validated request
        context.valid = True
        result  = request.execute(context)
        self.assertEqual(result.encode(), '\x00\x02\x00\x04')

    def testWriteMultipleCoilsResponse(self):
        response = WriteMultipleCoilsResponse()
        response.decode('\x00\x80\x00\x08')
        self.assertEqual(response.address, 0x80)
        self.assertEqual(response.count, 0x08)

    def testSerializingToString(self):
        requests = [
            WriteSingleCoilRequest(1, 0xabcd),
            WriteSingleCoilResponse(1, 0xabcd),
            WriteMultipleCoilsRequest(1, [True]*5),
            WriteMultipleCoilsResponse(1, 5),
        ]
        for request in requests:
            self.assertTrue(str(request) != None)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_client_async
#!/usr/bin/env python
import unittest
from mock import Mock
from pymodbus.client.async import ModbusClientProtocol, ModbusUdpClientProtocol
from pymodbus.client.async import ModbusClientFactory
from pymodbus.exceptions import ConnectionException
from pymodbus.exceptions import ParameterException
from pymodbus.transaction import ModbusSocketFramer
from pymodbus.bit_read_message import ReadCoilsRequest, ReadCoilsResponse

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class AsynchronousClientTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.client.async module
    '''

    #-----------------------------------------------------------------------#
    # Test Client Protocol
    #-----------------------------------------------------------------------#

    def testClientProtocolInit(self):
        ''' Test the client protocol initialize '''
        protocol = ModbusClientProtocol()
        self.assertEqual(0, len(list(protocol.transaction)))
        self.assertFalse(protocol._connected)
        self.assertTrue(isinstance(protocol.framer, ModbusSocketFramer))

        framer = object()
        protocol = ModbusClientProtocol(framer=framer)
        self.assertEqual(0, len(list(protocol.transaction)))
        self.assertFalse(protocol._connected)
        self.assertTrue(framer is protocol.framer)

    def testClientProtocolConnect(self):
        ''' Test the client protocol connect '''
        protocol = ModbusClientProtocol()
        self.assertFalse(protocol._connected)
        protocol.connectionMade()
        self.assertTrue(protocol._connected)

    def testClientProtocolDisconnect(self):
        ''' Test the client protocol disconnect '''
        protocol = ModbusClientProtocol()
        protocol.connectionMade()
        def handle_failure(failure):
            self.assertTrue(isinstance(failure.value, ConnectionException))
        d = protocol._buildResponse(0x00)
        d.addErrback(handle_failure)

        self.assertTrue(protocol._connected)
        protocol.connectionLost('because')
        self.assertFalse(protocol._connected)

    def testClientProtocolDataReceived(self):
        ''' Test the client protocol data received '''
        protocol = ModbusClientProtocol()
        protocol.connectionMade()
        out = []
        data = '\x00\x00\x12\x34\x00\x06\xff\x01\x01\x02\x00\x04'

        # setup existing request
        d = protocol._buildResponse(0x00)
        d.addCallback(lambda v: out.append(v))

        protocol.dataReceived(data)
        self.assertTrue(isinstance(out[0], ReadCoilsResponse))

    def testClientProtocolExecute(self):
        ''' Test the client protocol execute method '''
        protocol = ModbusClientProtocol()
        protocol.connectionMade()
        protocol.transport = Mock()
        protocol.transport.write = Mock()

        request = ReadCoilsRequest(1, 1)
        d = protocol.execute(request)
        tid = request.transaction_id
        self.assertEqual(d, protocol.transaction.getTransaction(tid))

    def testClientProtocolHandleResponse(self):
        ''' Test the client protocol handles responses '''
        protocol = ModbusClientProtocol()
        protocol.connectionMade()
        out = []
        reply = ReadCoilsRequest(1, 1)
        reply.transaction_id = 0x00

        # handle skipped cases
        protocol._handleResponse(None)
        protocol._handleResponse(reply)

        # handle existing cases
        d = protocol._buildResponse(0x00)
        d.addCallback(lambda v: out.append(v))
        protocol._handleResponse(reply)
        self.assertEqual(out[0], reply)

    def testClientProtocolBuildResponse(self):
        ''' Test the udp client protocol builds responses '''
        protocol = ModbusClientProtocol()
        self.assertEqual(0, len(list(protocol.transaction)))

        def handle_failure(failure):
            self.assertTrue(isinstance(failure.value, ConnectionException))
        d = protocol._buildResponse(0x00)
        d.addErrback(handle_failure)
        self.assertEqual(0, len(list(protocol.transaction)))

        protocol._connected = True
        d = protocol._buildResponse(0x00)
        self.assertEqual(1, len(list(protocol.transaction)))

    #-----------------------------------------------------------------------#
    # Test Udp Client Protocol
    #-----------------------------------------------------------------------#

    def testUdpClientProtocolInit(self):
        ''' Test the udp client protocol initialize '''
        protocol = ModbusUdpClientProtocol()
        self.assertEqual(0, len(list(protocol.transaction)))
        self.assertTrue(isinstance(protocol.framer, ModbusSocketFramer))

        framer = object()
        protocol = ModbusClientProtocol(framer=framer)
        self.assertTrue(framer is protocol.framer)

    def testUdpClientProtocolDataReceived(self):
        ''' Test the udp client protocol data received '''
        protocol = ModbusUdpClientProtocol()
        out = []
        data = '\x00\x00\x12\x34\x00\x06\xff\x01\x01\x02\x00\x04'
        server = ('127.0.0.1', 12345)

        # setup existing request
        d = protocol._buildResponse(0x00)
        d.addCallback(lambda v: out.append(v))

        protocol.datagramReceived(data, server)
        self.assertTrue(isinstance(out[0], ReadCoilsResponse))

    def testUdpClientProtocolExecute(self):
        ''' Test the udp client protocol execute method '''
        protocol = ModbusUdpClientProtocol()
        protocol.transport = Mock()
        protocol.transport.write = Mock()

        request = ReadCoilsRequest(1, 1)
        d = protocol.execute(request)
        tid = request.transaction_id
        self.assertEqual(d, protocol.transaction.getTransaction(tid))

    def testUdpClientProtocolHandleResponse(self):
        ''' Test the udp client protocol handles responses '''
        protocol = ModbusUdpClientProtocol()
        out = []
        reply = ReadCoilsRequest(1, 1)
        reply.transaction_id = 0x00

        # handle skipped cases
        protocol._handleResponse(None)
        protocol._handleResponse(reply)

        # handle existing cases
        d = protocol._buildResponse(0x00)
        d.addCallback(lambda v: out.append(v))
        protocol._handleResponse(reply)
        self.assertEqual(out[0], reply)

    def testUdpClientProtocolBuildResponse(self):
        ''' Test the udp client protocol builds responses '''
        protocol = ModbusUdpClientProtocol()
        self.assertEqual(0, len(list(protocol.transaction)))

        d = protocol._buildResponse(0x00)
        self.assertEqual(1, len(list(protocol.transaction)))

    #-----------------------------------------------------------------------#
    # Test Client Factories
    #-----------------------------------------------------------------------#

    def testModbusClientFactory(self):
        ''' Test the base class for all the clients '''
        factory = ModbusClientFactory()
        self.assertTrue(factory is not None)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_client_common
#!/usr/bin/env python
import unittest
from pymodbus.client.common import ModbusClientMixin
from pymodbus.bit_read_message import *
from pymodbus.bit_write_message import *
from pymodbus.register_read_message import *
from pymodbus.register_write_message import *

#---------------------------------------------------------------------------#
# Mocks
#---------------------------------------------------------------------------#
class MockClient(ModbusClientMixin):

    def execute(self, request):
        return request

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class ModbusCommonClientTests(unittest.TestCase):

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#
    def setUp(self):
        '''
        Initializes the test environment and builds request/result
        encoding pairs
        '''
        self.client = MockClient()

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.client

    #-----------------------------------------------------------------------#
    # Tests
    #-----------------------------------------------------------------------#
    def testModbusClientMixinMethods(self):
        ''' This tests that the mixing returns the correct request object '''
        arguments = {
            'read_address': 1, 'read_count': 1,
            'write_address': 1, 'write_registers': 1
        }
        self.assertTrue(isinstance(self.client.read_coils(1,1), ReadCoilsRequest))
        self.assertTrue(isinstance(self.client.read_discrete_inputs(1,1), ReadDiscreteInputsRequest))
        self.assertTrue(isinstance(self.client.write_coil(1,True), WriteSingleCoilRequest))
        self.assertTrue(isinstance(self.client.write_coils(1,[True]), WriteMultipleCoilsRequest))
        self.assertTrue(isinstance(self.client.write_register(1,0x00), WriteSingleRegisterRequest))
        self.assertTrue(isinstance(self.client.write_registers(1,[0x00]), WriteMultipleRegistersRequest))
        self.assertTrue(isinstance(self.client.read_holding_registers(1,1), ReadHoldingRegistersRequest))
        self.assertTrue(isinstance(self.client.read_input_registers(1,1), ReadInputRegistersRequest))
        self.assertTrue(isinstance(self.client.readwrite_registers(**arguments), ReadWriteMultipleRegistersRequest))

########NEW FILE########
__FILENAME__ = test_client_sync
#!/usr/bin/env python
import unittest
import socket
import serial
from mock import patch, Mock
from twisted.test import test_protocols
from pymodbus.client.sync import ModbusTcpClient, ModbusUdpClient
from pymodbus.client.sync import ModbusSerialClient, BaseModbusClient
from pymodbus.exceptions import ConnectionException, NotImplementedException
from pymodbus.exceptions import ParameterException
from pymodbus.transaction import ModbusAsciiFramer, ModbusRtuFramer
from pymodbus.transaction import ModbusBinaryFramer

#---------------------------------------------------------------------------#
# Mock Classes
#---------------------------------------------------------------------------#
class mockSocket(object):
    def close(self): return True
    def recv(self, size): return '\x00'*size
    def read(self, size): return '\x00'*size
    def send(self, msg): return len(msg)
    def write(self, msg): return len(msg)
    def recvfrom(self, size): return ['\x00'*size]
    def sendto(self, msg, *args): return len(msg)

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class SynchronousClientTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.client.sync module
    '''

    #-----------------------------------------------------------------------#
    # Test Base Client
    #-----------------------------------------------------------------------#

    def testBaseModbusClient(self):
        ''' Test the base class for all the clients '''

        client = BaseModbusClient(None)
        client.transaction = None
        self.assertRaises(NotImplementedException, lambda: client.connect())
        self.assertRaises(NotImplementedException, lambda: client._send(None))
        self.assertRaises(NotImplementedException, lambda: client._recv(None))
        self.assertRaises(NotImplementedException, lambda: client.__enter__())
        self.assertRaises(NotImplementedException, lambda: client.execute())
        self.assertEquals("Null Transport", str(client))
        client.close()
        client.__exit__(0,0,0)

        # a successful execute
        client.connect = lambda: True
        client.transaction = Mock(**{'execute.return_value': True})
        self.assertEqual(client, client.__enter__())
        self.assertTrue(client.execute())

        # a unsuccessful connect
        client.connect = lambda: False
        self.assertRaises(ConnectionException, lambda: client.__enter__())
        self.assertRaises(ConnectionException, lambda: client.execute())

    #-----------------------------------------------------------------------#
    # Test UDP Client
    #-----------------------------------------------------------------------#

    def testSyncUdpClientInstantiation(self):
        client = ModbusUdpClient()
        self.assertNotEqual(client, None)

    def testBasicSyncUdpClient(self):
        ''' Test the basic methods for the udp sync client'''

        # receive/send
        client = ModbusUdpClient()
        client.socket = mockSocket()
        self.assertEqual(0, client._send(None))
        self.assertEqual(1, client._send('\x00'))
        self.assertEqual('\x00', client._recv(1))

        # connect/disconnect
        self.assertTrue(client.connect())
        client.close()

        # already closed socket
        client.socket = False
        client.close()

        self.assertEqual("127.0.0.1:502", str(client))

    def testUdpClientAddressFamily(self):
        ''' Test the Udp client get address family method'''
        client = ModbusUdpClient()
        self.assertEqual(socket.AF_INET, client._get_address_family('127.0.0.1'))
        self.assertEqual(socket.AF_INET6, client._get_address_family('::1'))

    def testUdpClientConnect(self):
        ''' Test the Udp client connection method'''
        with patch.object(socket, 'socket') as mock_method:
            mock_method.return_value = object()
            client = ModbusUdpClient()
            self.assertTrue(client.connect())

        with patch.object(socket, 'socket') as mock_method:
            mock_method.side_effect = socket.error()
            client = ModbusUdpClient()
            self.assertFalse(client.connect())

    def testUdpClientSend(self):
        ''' Test the udp client send method'''
        client = ModbusUdpClient()
        self.assertRaises(ConnectionException, lambda: client._send(None))

        client.socket = mockSocket()
        self.assertEqual(0, client._send(None))
        self.assertEqual(4, client._send('1234'))

    def testUdpClientRecv(self):
        ''' Test the udp client receive method'''
        client = ModbusUdpClient()
        self.assertRaises(ConnectionException, lambda: client._recv(1024))

        client.socket = mockSocket()
        self.assertEqual('', client._recv(0))
        self.assertEqual('\x00'*4, client._recv(4))

    #-----------------------------------------------------------------------#
    # Test TCP Client
    #-----------------------------------------------------------------------#
    
    def testSyncTcpClientInstantiation(self):
        client = ModbusTcpClient()
        self.assertNotEqual(client, None)

    def testBasicSyncTcpClient(self):
        ''' Test the basic methods for the tcp sync client'''

        # receive/send
        client = ModbusTcpClient()
        client.socket = mockSocket()
        self.assertEqual(0, client._send(None))
        self.assertEqual(1, client._send('\x00'))
        self.assertEqual('\x00', client._recv(1))

        # connect/disconnect
        self.assertTrue(client.connect())
        client.close()

        # already closed socket
        client.socket = False
        client.close()

        self.assertEqual("127.0.0.1:502", str(client))

    def testTcpClientConnect(self):
        ''' Test the tcp client connection method'''
        with patch.object(socket, 'create_connection') as mock_method:
            mock_method.return_value = object()
            client = ModbusTcpClient()
            self.assertTrue(client.connect())

        with patch.object(socket, 'create_connection') as mock_method:
            mock_method.side_effect = socket.error()
            client = ModbusTcpClient()
            self.assertFalse(client.connect())

    def testTcpClientSend(self):
        ''' Test the tcp client send method'''
        client = ModbusTcpClient()
        self.assertRaises(ConnectionException, lambda: client._send(None))

        client.socket = mockSocket()
        self.assertEqual(0, client._send(None))
        self.assertEqual(4, client._send('1234'))

    def testTcpClientRecv(self):
        ''' Test the tcp client receive method'''
        client = ModbusTcpClient()
        self.assertRaises(ConnectionException, lambda: client._recv(1024))

        client.socket = mockSocket()
        self.assertEqual('', client._recv(0))
        self.assertEqual('\x00'*4, client._recv(4))
    
    #-----------------------------------------------------------------------#
    # Test Serial Client
    #-----------------------------------------------------------------------#

    def testSyncSerialClientInstantiation(self):
        client = ModbusSerialClient()
        self.assertNotEqual(client, None)
        self.assertTrue(isinstance(ModbusSerialClient(method='ascii').framer, ModbusAsciiFramer))
        self.assertTrue(isinstance(ModbusSerialClient(method='rtu').framer, ModbusRtuFramer))
        self.assertTrue(isinstance(ModbusSerialClient(method='binary').framer, ModbusBinaryFramer))
        self.assertRaises(ParameterException, lambda: ModbusSerialClient(method='something'))

    def testBasicSyncSerialClient(self):
        ''' Test the basic methods for the serial sync client'''

        # receive/send
        client = ModbusSerialClient()
        client.socket = mockSocket()
        self.assertEqual(0, client._send(None))
        self.assertEqual(1, client._send('\x00'))
        self.assertEqual('\x00', client._recv(1))

        # connect/disconnect
        self.assertTrue(client.connect())
        client.close()

        # already closed socket
        client.socket = False
        client.close()

        self.assertEqual('ascii baud[19200]', str(client))

    def testSerialClientConnect(self):
        ''' Test the serial client connection method'''
        with patch.object(serial, 'Serial') as mock_method:
            mock_method.return_value = object()
            client = ModbusSerialClient()
            self.assertTrue(client.connect())

        with patch.object(serial, 'Serial') as mock_method:
            mock_method.side_effect = serial.SerialException()
            client = ModbusSerialClient()
            self.assertFalse(client.connect())

    def testSerialClientSend(self):
        ''' Test the serial client send method'''
        client = ModbusSerialClient()
        self.assertRaises(ConnectionException, lambda: client._send(None))

        client.socket = mockSocket()
        self.assertEqual(0, client._send(None))
        self.assertEqual(4, client._send('1234'))

    def testSerialClientRecv(self):
        ''' Test the serial client receive method'''
        client = ModbusSerialClient()
        self.assertRaises(ConnectionException, lambda: client._recv(1024))

        client.socket = mockSocket()
        self.assertEqual('', client._recv(0))
        self.assertEqual('\x00'*4, client._recv(4))

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_datastore
#!/usr/bin/env python
import unittest
from pymodbus.datastore import *
from pymodbus.datastore.store import BaseModbusDataBlock
from pymodbus.exceptions import NotImplementedException
from pymodbus.exceptions import ParameterException
from pymodbus.datastore.remote import RemoteSlaveContext

class ModbusDataStoreTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.datastore module
    '''

    def setUp(self):
        pass

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    def testModbusDataBlock(self):
        ''' Test a base data block store '''
        block = BaseModbusDataBlock()
        block.default(10, True)

        self.assertNotEqual(str(block), None)
        self.assertEqual(block.default_value, True)
        self.assertEqual(block.values, [True]*10)

        block.default_value = False
        block.reset()
        self.assertEqual(block.values, [False]*10)

    def testModbusDataBlockIterate(self):
        ''' Test a base data block store '''
        block = BaseModbusDataBlock()
        block.default(10, False)
        for idx,value in block:
            self.assertEqual(value, False)

        block.values = {0 : False, 2 : False, 3 : False }
        for idx,value in block:
            self.assertEqual(value, False)

    def testModbusDataBlockOther(self):
        ''' Test a base data block store '''
        block = BaseModbusDataBlock()
        self.assertRaises(NotImplementedException, lambda: block.validate(1,1))
        self.assertRaises(NotImplementedException, lambda: block.getValues(1,1))
        self.assertRaises(NotImplementedException, lambda: block.setValues(1,1))

    def testModbusSequentialDataBlock(self):
        ''' Test a sequential data block store '''
        block = ModbusSequentialDataBlock(0x00, [False]*10)
        self.assertFalse(block.validate(-1, 0))
        self.assertFalse(block.validate(0, 20))
        self.assertFalse(block.validate(10, 1))
        self.assertTrue(block.validate(0x00, 10))

        block.setValues(0x00, True)
        self.assertEqual(block.getValues(0x00, 1), [True])

        block.setValues(0x00, [True]*10)
        self.assertEqual(block.getValues(0x00, 10), [True]*10)

    def testModbusSequentialDataBlockFactory(self):
        ''' Test the sequential data block store factory '''
        block = ModbusSequentialDataBlock.create()
        self.assertEqual(block.getValues(0x00, 65536), [False]*65536)
        block = ModbusSequentialDataBlock(0x00, 0x01)
        self.assertEqual(block.values, [0x01])

    def testModbusSparseDataBlock(self):
        ''' Test a sparse data block store '''
        values = dict(enumerate([True]*10))
        block = ModbusSparseDataBlock(values)
        self.assertFalse(block.validate(-1, 0))
        self.assertFalse(block.validate(0, 20))
        self.assertFalse(block.validate(10, 1))
        self.assertTrue(block.validate(0x00, 10))
        self.assertTrue(block.validate(0x00, 10))
        self.assertFalse(block.validate(0, 0))
        self.assertFalse(block.validate(5, 0))

        block.setValues(0x00, True)
        self.assertEqual(block.getValues(0x00, 1), [True])

        block.setValues(0x00, [True]*10)
        self.assertEqual(block.getValues(0x00, 10), [True]*10)

        block.setValues(0x00, dict(enumerate([False]*10)))
        self.assertEqual(block.getValues(0x00, 10), [False]*10)

    def testModbusSparseDataBlockFactory(self):
        ''' Test the sparse data block store factory '''
        block = ModbusSparseDataBlock.create()
        self.assertEqual(block.getValues(0x00, 65536), [False]*65536)

    def testModbusSparseDataBlockOther(self):
        block = ModbusSparseDataBlock([True]*10)
        self.assertEqual(block.getValues(0x00, 10), [True]*10)
        self.assertRaises(ParameterException,
            lambda: ModbusSparseDataBlock(True))

    def testModbusSlaveContext(self):
        ''' Test a modbus slave context '''
        store = {
            'di' : ModbusSequentialDataBlock(0, [False]*10),
            'co' : ModbusSequentialDataBlock(0, [False]*10),
            'ir' : ModbusSequentialDataBlock(0, [False]*10),
            'hr' : ModbusSequentialDataBlock(0, [False]*10),
        }
        context = ModbusSlaveContext(**store)
        self.assertNotEqual(str(context), None)
        
        for fx in [1,2,3,4]:
            context.setValues(fx, 0, [True]*10)
            self.assertTrue(context.validate(fx, 0,10))
            self.assertEqual(context.getValues(fx, 0,10), [True]*10)
        context.reset()

        for fx in [1,2,3,4]:
            self.assertTrue(context.validate(fx, 0,10))
            self.assertEqual(context.getValues(fx, 0,10), [False]*10)

    def testModbusServerContext(self):
        ''' Test a modbus server context '''
        def _set(ctx):
            ctx[0xffff] = None
        context = ModbusServerContext(single=False)
        self.assertRaises(ParameterException, lambda: _set(context))
        self.assertRaises(ParameterException, lambda: context[0xffff])

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_device
#!/usr/bin/env python
import unittest
from pymodbus.device import *
from pymodbus.events import ModbusEvent, RemoteReceiveEvent
from pymodbus.constants import DeviceInformation

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class SimpleDataStoreTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.device module
    '''

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#

    def setUp(self):
        self.info = {
            0x00: 'Bashwork',               # VendorName
            0x01: 'PTM',                    # ProductCode
            0x02: '1.0',                    # MajorMinorRevision
            0x03: 'http://internets.com',   # VendorUrl
            0x04: 'pymodbus',               # ProductName
            0x05: 'bashwork',               # ModelName
            0x06: 'unittest',               # UserApplicationName
            0x07: 'x',                      # reserved
            0x08: 'x',                      # reserved
            0x10: 'private'                 # private data
        }
        self.ident   = ModbusDeviceIdentification(self.info)
        self.control = ModbusControlBlock()
        self.access  = ModbusAccessControl()
        self.control.reset()

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.ident
        del self.control
        del self.access

    def testUpdateIdentity(self):
        ''' Test device identification reading '''
        self.control.Identity.update(self.ident)
        self.assertEqual(self.control.Identity.VendorName, 'Bashwork')
        self.assertEqual(self.control.Identity.ProductCode, 'PTM')
        self.assertEqual(self.control.Identity.MajorMinorRevision, '1.0')
        self.assertEqual(self.control.Identity.VendorUrl, 'http://internets.com')
        self.assertEqual(self.control.Identity.ProductName, 'pymodbus')
        self.assertEqual(self.control.Identity.ModelName, 'bashwork')
        self.assertEqual(self.control.Identity.UserApplicationName, 'unittest')

    def testDeviceInformationFactory(self):
        ''' Test device identification reading '''
        self.control.Identity.update(self.ident)
        result = DeviceInformationFactory.get(self.control, DeviceInformation.Specific, 0x00)
        self.assertEqual(result[0x00], 'Bashwork')

        result = DeviceInformationFactory.get(self.control, DeviceInformation.Basic, 0x00)
        self.assertEqual(result[0x00], 'Bashwork')
        self.assertEqual(result[0x01], 'PTM')
        self.assertEqual(result[0x02], '1.0')

        result = DeviceInformationFactory.get(self.control, DeviceInformation.Regular, 0x00)
        self.assertEqual(result[0x00], 'Bashwork')
        self.assertEqual(result[0x01], 'PTM')
        self.assertEqual(result[0x02], '1.0')
        self.assertEqual(result[0x03], 'http://internets.com')
        self.assertEqual(result[0x04], 'pymodbus')
        self.assertEqual(result[0x05], 'bashwork')
        self.assertEqual(result[0x06], 'unittest')

    def testBasicCommands(self):
        ''' Test device identification reading '''
        self.assertEqual(str(self.ident),   "DeviceIdentity")
        self.assertEqual(str(self.control), "ModbusControl")

    def testModbusDeviceIdentificationGet(self):
        ''' Test device identification reading '''
        self.assertEqual(self.ident[0x00], 'Bashwork')
        self.assertEqual(self.ident[0x01], 'PTM')
        self.assertEqual(self.ident[0x02], '1.0')
        self.assertEqual(self.ident[0x03], 'http://internets.com')
        self.assertEqual(self.ident[0x04], 'pymodbus')
        self.assertEqual(self.ident[0x05], 'bashwork')
        self.assertEqual(self.ident[0x06], 'unittest')
        self.assertNotEqual(self.ident[0x07], 'x')
        self.assertNotEqual(self.ident[0x08], 'x')
        self.assertEqual(self.ident[0x10], 'private')
        self.assertEqual(self.ident[0x54], '')

    def testModbusDeviceIdentificationSummary(self):
        ''' Test device identification summary creation '''
        summary  = sorted(self.ident.summary().values())
        expected = sorted(self.info.values()[:-3]) # remove private
        self.assertEqual(summary, expected)

    def testModbusDeviceIdentificationSet(self):
        ''' Test a device identification writing '''
        self.ident[0x07] = 'y'
        self.ident[0x08] = 'y'
        self.ident[0x10] = 'public'
        self.ident[0x54] = 'testing'

        self.assertNotEqual('y', self.ident[0x07])
        self.assertNotEqual('y', self.ident[0x08])
        self.assertEqual('public', self.ident[0x10])
        self.assertEqual('testing', self.ident[0x54])

    def testModbusControlBlockAsciiModes(self):
        ''' Test a server control block ascii mode '''
        self.assertEqual(id(self.control), id(ModbusControlBlock()))
        self.control.Mode = 'RTU'
        self.assertEqual('RTU', self.control.Mode)
        self.control.Mode = 'FAKE'
        self.assertNotEqual('FAKE', self.control.Mode)

    def testModbusControlBlockCounters(self):
        ''' Tests the MCB counters methods '''
        self.assertEqual(0x0, self.control.Counter.BusMessage)
        for _ in range(10):
            self.control.Counter.BusMessage += 1
            self.control.Counter.SlaveMessage += 1
        self.assertEqual(10, self.control.Counter.BusMessage)
        self.control.Counter.BusMessage = 0x00
        self.assertEqual(0,  self.control.Counter.BusMessage)
        self.assertEqual(10, self.control.Counter.SlaveMessage)
        self.control.Counter.reset()
        self.assertEqual(0, self.control.Counter.SlaveMessage)

    def testModbusControlBlockUpdate(self):
        ''' Tests the MCB counters upate methods '''
        values = {'SlaveMessage':5, 'BusMessage':5}
        self.control.Counter.BusMessage += 1
        self.control.Counter.SlaveMessage += 1
        self.control.Counter.update(values)
        self.assertEqual(6, self.control.Counter.SlaveMessage)
        self.assertEqual(6, self.control.Counter.BusMessage)

    def testModbusControlBlockIterator(self):
        ''' Tests the MCB counters iterator '''
        self.control.Counter.reset()
        for _,count in self.control:
            self.assertEqual(0, count)

    def testModbusCountersHandlerIterator(self):
        ''' Tests the MCB counters iterator '''
        self.control.Counter.reset()
        for _,count in self.control.Counter:
            self.assertEqual(0, count)

    def testModbusControlBlockCounterSummary(self):
        ''' Tests retrieving the current counter summary '''
        self.assertEqual(0x00, self.control.Counter.summary())
        for _ in range(10):
            self.control.Counter.BusMessage += 1
            self.control.Counter.SlaveMessage += 1
            self.control.Counter.SlaveNAK += 1
            self.control.Counter.BusCharacterOverrun += 1
        self.assertEqual(0xa9, self.control.Counter.summary())
        self.control.Counter.reset()
        self.assertEqual(0x00, self.control.Counter.summary())

    def testModbusControlBlockListen(self):
        ''' Tests the MCB listen flag methods '''
        
        self.control.ListenOnly = False        
        self.assertEqual(self.control.ListenOnly, False)
        self.control.ListenOnly = not self.control.ListenOnly
        self.assertEqual(self.control.ListenOnly, True)

    def testModbusControlBlockDelimiter(self):
        ''' Tests the MCB delimiter setting methods '''
        self.control.Delimiter = '\r'
        self.assertEqual(self.control.Delimiter, '\r')
        self.control.Delimiter = '='
        self.assertEqual(self.control.Delimiter, '=')
        self.control.Delimiter = 61
        self.assertEqual(self.control.Delimiter, '=')

    def testModbusControlBlockDiagnostic(self):
        ''' Tests the MCB delimiter setting methods '''
        self.assertEqual([False] * 16, self.control.getDiagnosticRegister())
        for i in [1,3,4,6]:
            self.control.setDiagnostic({i:True});
        self.assertEqual(True, self.control.getDiagnostic(1))
        self.assertEqual(False, self.control.getDiagnostic(2))
        actual = [False, True, False, True, True, False, True] + [False] * 9
        self.assertEqual(actual, self.control.getDiagnosticRegister())
        for i in range(16):
            self.control.setDiagnostic({i:False});

    def testModbusControlBlockInvalidDiagnostic(self):
        ''' Tests querying invalid MCB counters methods '''
        self.assertEqual(None, self.control.getDiagnostic(-1))
        self.assertEqual(None, self.control.getDiagnostic(17))
        self.assertEqual(None, self.control.getDiagnostic(None))
        self.assertEqual(None, self.control.getDiagnostic([1,2,3]))

    def testAddRemoveSingleClients(self):
        ''' Test adding and removing a host '''
        self.assertFalse(self.access.check("192.168.1.1"))
        self.access.add("192.168.1.1")
        self.assertTrue(self.access.check("192.168.1.1"))
        self.access.add("192.168.1.1")
        self.access.remove("192.168.1.1")
        self.assertFalse(self.access.check("192.168.1.1"))

    def testAddRemoveMultipleClients(self):
        ''' Test adding and removing a host '''
        clients = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        self.access.add(clients)
        for host in clients:
            self.assertTrue(self.access.check(host))
        self.access.remove(clients)

    def testNetworkAccessListIterator(self):
        ''' Test adding and removing a host '''
        clients = ["127.0.0.1", "192.168.1.1", "192.168.1.2", "192.168.1.3"]
        self.access.add(clients)
        for host in self.access:
            self.assertTrue(host in clients)
        for host in clients:
            self.assertTrue(host in self.access)

    def testClearingControlEvents(self):
        ''' Test adding and clearing modbus events '''
        self.assertEqual(self.control.Events, [])
        event = ModbusEvent()
        self.control.addEvent(event)
        self.assertEqual(self.control.Events, [event])
        self.assertEqual(self.control.Counter.Event, 1)
        self.control.clearEvents()
        self.assertEqual(self.control.Events, [])
        self.assertEqual(self.control.Counter.Event, 1)

    def testRetrievingControlEvents(self):
        ''' Test adding and removing a host '''
        self.assertEqual(self.control.Events, [])
        event = RemoteReceiveEvent()
        self.control.addEvent(event)
        self.assertEqual(self.control.Events, [event])
        packet = self.control.getEvents()
        self.assertEqual(packet, '\x40')

    def testModbusPlusStatistics(self):
        ''' Test device identification reading '''
        default = [0x0000] * 55
        statistics = ModbusPlusStatistics()
        self.assertEqual(default, statistics.encode())
        statistics.reset()
        self.assertEqual(default, statistics.encode())
        self.assertEqual(default, self.control.Plus.encode())



    def testModbusPlusStatisticsHelpers(self):
        ''' Test modbus plus statistics helper methods '''
        statistics = ModbusPlusStatistics()
        summary = [
             [0],[0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0],[0],
             [0,0,0,0,0,0,0,0],[0],[0],[0],[0],[0,0],[0],[0],[0],[0],
             [0],[0],[0],[0,0],[0],[0],[0],[0],[0,0,0,0,0,0,0,0],[0],
             [0,0,0,0,0,0,0,0],[0,0],[0],[0,0,0,0,0,0,0,0],
             [0,0,0,0,0,0,0,0],[0],[0],[0,0],[0],[0],[0],[0],[0,0],
             [0],[0],[0],[0],[0],[0,0],[0],[0,0,0,0,0,0,0,0]]
        self.assertEqual(summary, statistics.summary())
        self.assertEqual(0x00, sum(sum(value[1]) for value in statistics))

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_diag_messages
#!/usr/bin/env python
import unittest
from pymodbus.exceptions import *
from pymodbus.constants import ModbusPlusOperation
from pymodbus.diag_message import *
from pymodbus.diag_message import DiagnosticStatusRequest
from pymodbus.diag_message import DiagnosticStatusResponse
from pymodbus.diag_message import DiagnosticStatusSimpleRequest
from pymodbus.diag_message import DiagnosticStatusSimpleResponse

class SimpleDataStoreTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.diag_message module
    '''

    def setUp(self):
        self.requests = [
            #(DiagnosticStatusRequest,                      '\x00\x00\x00\x00'),
            #(DiagnosticStatusSimpleRequest,                '\x00\x00\x00\x00'),
            (RestartCommunicationsOptionRequest,            '\x00\x01\x00\x00', '\x00\x01\xff\x00'),
            (ReturnDiagnosticRegisterRequest,               '\x00\x02\x00\x00', '\x00\x02\x00\x00'),
            (ChangeAsciiInputDelimiterRequest,              '\x00\x03\x00\x00', '\x00\x03\x00\x00'),
            (ForceListenOnlyModeRequest,                    '\x00\x04\x00\x00', '\x00\x04'),
            (ReturnQueryDataRequest,                        '\x00\x00\x00\x00', '\x00\x00\x00\x00'),
            (ClearCountersRequest,                          '\x00\x0a\x00\x00', '\x00\x0a\x00\x00'),
            (ReturnBusMessageCountRequest,                  '\x00\x0b\x00\x00', '\x00\x0b\x00\x00'),
            (ReturnBusCommunicationErrorCountRequest,       '\x00\x0c\x00\x00', '\x00\x0c\x00\x00'),
            (ReturnBusExceptionErrorCountRequest,           '\x00\x0d\x00\x00', '\x00\x0d\x00\x00'),
            (ReturnSlaveMessageCountRequest,                '\x00\x0e\x00\x00', '\x00\x0e\x00\x00'),
            (ReturnSlaveNoResponseCountRequest,             '\x00\x0f\x00\x00', '\x00\x0f\x00\x00'),
            (ReturnSlaveNAKCountRequest,                    '\x00\x10\x00\x00', '\x00\x10\x00\x00'),
            (ReturnSlaveBusyCountRequest,                   '\x00\x11\x00\x00', '\x00\x11\x00\x00'),
            (ReturnSlaveBusCharacterOverrunCountRequest,    '\x00\x12\x00\x00', '\x00\x12\x00\x00'),
            (ReturnIopOverrunCountRequest,                  '\x00\x13\x00\x00', '\x00\x13\x00\x00'),
            (ClearOverrunCountRequest,                      '\x00\x14\x00\x00', '\x00\x14\x00\x00'),
            (GetClearModbusPlusRequest,                     '\x00\x15\x00\x00', '\x00\x15' + '\x00\x00' * 55),
        ]

        self.responses = [
            #(DiagnosticStatusResponse,                     '\x00\x00\x00\x00'),
            #(DiagnosticStatusSimpleResponse,               '\x00\x00\x00\x00'),
            (ReturnQueryDataResponse,                      '\x00\x00\x00\x00'),
            (RestartCommunicationsOptionResponse,          '\x00\x01\x00\x00'),
            (ReturnDiagnosticRegisterResponse,             '\x00\x02\x00\x00'),
            (ChangeAsciiInputDelimiterResponse,            '\x00\x03\x00\x00'),
            (ForceListenOnlyModeResponse,                  '\x00\x04'),
            (ReturnQueryDataResponse,                      '\x00\x00\x00\x00'),
            (ClearCountersResponse,                        '\x00\x0a\x00\x00'),
            (ReturnBusMessageCountResponse,                '\x00\x0b\x00\x00'),
            (ReturnBusCommunicationErrorCountResponse,     '\x00\x0c\x00\x00'),
            (ReturnBusExceptionErrorCountResponse,         '\x00\x0d\x00\x00'),
            (ReturnSlaveMessageCountResponse,              '\x00\x0e\x00\x00'),
            (ReturnSlaveNoReponseCountResponse,            '\x00\x0f\x00\x00'),
            (ReturnSlaveNAKCountResponse,                  '\x00\x10\x00\x00'),
            (ReturnSlaveBusyCountResponse,                 '\x00\x11\x00\x00'),
            (ReturnSlaveBusCharacterOverrunCountResponse,  '\x00\x12\x00\x00'),
            (ReturnIopOverrunCountResponse,                '\x00\x13\x00\x00'),
            (ClearOverrunCountResponse,                    '\x00\x14\x00\x00'),
            (GetClearModbusPlusResponse,                   '\x00\x15' + '\x00\x00' * 55),
        ]

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.requests
        del self.responses

    def testDiagnosticRequestsDecode(self):
        ''' Testing diagnostic request messages encoding '''
        for msg,enc,exe in self.requests:
            handle = DiagnosticStatusRequest()
            handle.decode(enc)
            self.assertEqual(handle.sub_function_code, msg.sub_function_code)

    def testDiagnosticSimpleRequests(self):
        ''' Testing diagnostic request messages encoding '''
        request = DiagnosticStatusSimpleRequest('\x12\x34')
        request.sub_function_code = 0x1234
        self.assertRaises(NotImplementedException, lambda: request.execute())
        self.assertEqual(request.encode(), '\x12\x34\x12\x34')

        response = DiagnosticStatusSimpleResponse(None)

    def testDiagnosticResponseDecode(self):
        ''' Testing diagnostic request messages encoding '''
        for msg,enc,exe in self.requests:
            handle = DiagnosticStatusResponse()
            handle.decode(enc)
            self.assertEqual(handle.sub_function_code, msg.sub_function_code)

    def testDiagnosticRequestsEncode(self):
        ''' Testing diagnostic request messages encoding '''
        for msg,enc,exe in self.requests:
            self.assertEqual(msg().encode(), enc)

    #def testDiagnosticResponse(self):
    #    ''' Testing diagnostic request messages '''
    #    for msg,enc in self.responses:
    #        self.assertEqual(msg().encode(), enc)

    def testDiagnosticExecute(self):
        ''' Testing diagnostic message execution '''
        for msg,enc,exe in self.requests:
            self.assertEqual(msg().execute().encode(), exe)

    def testReturnQueryDataRequest(self):
        ''' Testing diagnostic message execution '''
        message = ReturnQueryDataRequest([0x0000]*2)
        self.assertEqual(message.encode(), '\x00\x00\x00\x00\x00\x00');
        message = ReturnQueryDataRequest(0x0000)
        self.assertEqual(message.encode(), '\x00\x00\x00\x00');

    def testReturnQueryDataResponse(self):
        ''' Testing diagnostic message execution '''
        message = ReturnQueryDataResponse([0x0000]*2)
        self.assertEqual(message.encode(), '\x00\x00\x00\x00\x00\x00');
        message = ReturnQueryDataResponse(0x0000)
        self.assertEqual(message.encode(), '\x00\x00\x00\x00');

    def testRestartCommunicationsOption(self):
        ''' Testing diagnostic message execution '''
        request = RestartCommunicationsOptionRequest(True);
        self.assertEqual(request.encode(), '\x00\x01\xff\x00')
        request = RestartCommunicationsOptionRequest(False);
        self.assertEqual(request.encode(), '\x00\x01\x00\x00')

        response = RestartCommunicationsOptionResponse(True);
        self.assertEqual(response.encode(), '\x00\x01\xff\x00')
        response = RestartCommunicationsOptionResponse(False);
        self.assertEqual(response.encode(), '\x00\x01\x00\x00')

    def testGetClearModbusPlusRequestExecute(self):
        ''' Testing diagnostic message execution '''
        request = GetClearModbusPlusRequest(ModbusPlusOperation.ClearStatistics);
        response = request.execute()
        self.assertEqual(response.message, None)

        request = GetClearModbusPlusRequest(ModbusPlusOperation.GetStatistics);
        response = request.execute()
        self.assertEqual(response.message, [0x00] * 55)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_events
#!/usr/bin/env python
import unittest
from pymodbus.events import *
from pymodbus.exceptions import NotImplementedException
from pymodbus.exceptions import ParameterException

class ModbusEventsTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.device module
    '''

    def setUp(self):
        ''' Sets up the test environment '''
        pass

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    def testModbusEventBaseClass(self):
        event = ModbusEvent()
        self.assertRaises(NotImplementedException, event.encode)
        self.assertRaises(NotImplementedException, lambda: event.decode(None))

    def testRemoteReceiveEvent(self):
        event = RemoteReceiveEvent()
        event.decode('\x70')
        self.assertTrue(event.overrun)
        self.assertTrue(event.listen)
        self.assertTrue(event.broadcast)

    def testRemoteSentEvent(self):
        event = RemoteSendEvent()
        result = event.encode()
        self.assertEqual(result, '\x40')
        event.decode('\x7f')
        self.assertTrue(event.read)
        self.assertTrue(event.slave_abort)
        self.assertTrue(event.slave_busy)
        self.assertTrue(event.slave_nak)
        self.assertTrue(event.write_timeout)
        self.assertTrue(event.listen)

    def testRemoteSentEventEncode(self):
        arguments = {
            'read'          : True,
            'slave_abort'   : True,
            'slave_busy'    : True,
            'slave_nak'     : True,
            'write_timeout' : True,
            'listen'        : True,
        }
        event = RemoteSendEvent(**arguments)
        result = event.encode()
        self.assertEqual(result, '\x7f')

    def testEnteredListenModeEvent(self):
        event = EnteredListenModeEvent()
        result = event.encode()
        self.assertEqual(result, '\x04')
        event.decode('\x04')
        self.assertEqual(event.value, 0x04)
        self.assertRaises(ParameterException, lambda: event.decode('\x00'))

    def testCommunicationRestartEvent(self):
        event = CommunicationRestartEvent()
        result = event.encode()
        self.assertEqual(result, '\x00')
        event.decode('\x00')
        self.assertEqual(event.value, 0x00)
        self.assertRaises(ParameterException, lambda: event.decode('\x04'))

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_exceptions
#!/usr/bin/env python
import unittest
from pymodbus.exceptions import *

class SimpleExceptionsTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.exceptions module
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        self.exceptions = [
                ModbusException("bad base"),
                ModbusIOException("bad register"),
                ParameterException("bad paramater"),
                NotImplementedException("bad function"),
                ConnectionException("bad connection"),
        ]

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    def testExceptions(self):
        ''' Test all module exceptions '''
        for ex in self.exceptions:
            try:
                raise ex
            except ModbusException, ex:
                self.assertTrue("Modbus Error:" in str(ex))
                pass
            else: self.fail("Excepted a ModbusExceptions")

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_factory
#!/usr/bin/env python
import unittest
from pymodbus.factory import ServerDecoder, ClientDecoder
from pymodbus.exceptions import ModbusException

def _raise_exception(_):
    raise ModbusException('something')

class SimpleFactoryTest(unittest.TestCase):
    '''
    This is the unittest for the pymod.exceptions module
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        self.client  = ClientDecoder()
        self.server  = ServerDecoder()
        self.request = (
                (0x01, '\x01\x00\x01\x00\x01'),                       # read coils
                (0x02, '\x02\x00\x01\x00\x01'),                       # read discrete inputs
                (0x03, '\x03\x00\x01\x00\x01'),                       # read holding registers
                (0x04, '\x04\x00\x01\x00\x01'),                       # read input registers
                (0x05, '\x05\x00\x01\x00\x01'),                       # write single coil
                (0x06, '\x06\x00\x01\x00\x01'),                       # write single register
                (0x07, '\x07'),                                       # read exception status
                (0x08, '\x08\x00\x00\x00\x00'),                       # read diagnostic
                (0x0b, '\x0b'),                                       # get comm event counters
                (0x0c, '\x0c'),                                       # get comm event log
                (0x0f, '\x0f\x00\x01\x00\x08\x01\x00\xff'),           # write multiple coils
                (0x10, '\x10\x00\x01\x00\x02\x04\0xff\xff'),          # write multiple registers
                (0x11, '\x11'),                                       # report slave id
                (0x14, '\x14\x0e\x06\x00\x04\x00\x01\x00\x02' \
                       '\x06\x00\x03\x00\x09\x00\x02'),               # read file record
                (0x15, '\x15\x0d\x06\x00\x04\x00\x07\x00\x03' \
                       '\x06\xaf\x04\xbe\x10\x0d'),                   # write file record
                (0x16, '\x16\x00\x01\x00\xff\xff\x00'),               # mask write register
                (0x17, '\x17\x00\x01\x00\x01\x00\x01\x00\x01\x02\x12\x34'),# read/write multiple registers
                (0x18, '\x18\x00\x01'),                               # read fifo queue
                (0x2b, '\x2b\x0e\x01\x00'),                           # read device identification
        )

        self.response = (
                (0x01, '\x01\x01\x01'),                               # read coils
                (0x02, '\x02\x01\x01'),                               # read discrete inputs
                (0x03, '\x03\x02\x01\x01'),                           # read holding registers
                (0x04, '\x04\x02\x01\x01'),                           # read input registers
                (0x05, '\x05\x00\x01\x00\x01'),                       # write single coil
                (0x06, '\x06\x00\x01\x00\x01'),                       # write single register
                (0x07, '\x07\x00'),                                   # read exception status
                (0x08, '\x08\x00\x00\x00\x00'),                       # read diagnostic
                (0x0b, '\x0b\x00\x00\x00\x00'),                       # get comm event counters
                (0x0c, '\x0c\x08\x00\x00\x01\x08\x01\x21\x20\x00'),   # get comm event log
                (0x0f, '\x0f\x00\x01\x00\x08'),                       # write multiple coils
                (0x10, '\x10\x00\x01\x00\x02'),                       # write multiple registers
                (0x11, '\x11\x03\x05\x01\x54'),                       # report slave id (device specific)
                (0x14, '\x14\x0c\x05\x06\x0d\xfe\x00\x20\x05' \
                       '\x06\x33\xcd\x00\x40'),                       # read file record
                (0x15, '\x15\x0d\x06\x00\x04\x00\x07\x00\x03' \
                       '\x06\xaf\x04\xbe\x10\x0d'),                   # write file record
                (0x16, '\x16\x00\x01\x00\xff\xff\x00'),               # mask write register
                (0x17, '\x17\x02\x12\x34'),                           # read/write multiple registers
                (0x18, '\x18\x00\x01\x00\x01\x00\x00'),               # read fifo queue
                (0x2b, '\x2b\x0e\x01\x01\x00\x00\x01\x00\x01\x77'),   # read device identification
        )

        self.exception = (
                (0x81, '\x81\x01\xd0\x50'),                           # illegal function exception
                (0x82, '\x82\x02\x90\xa1'),                           # illegal data address exception
                (0x83, '\x83\x03\x50\xf1'),                           # illegal data value exception
                (0x84, '\x84\x04\x13\x03'),                           # skave device failure exception
                (0x85, '\x85\x05\xd3\x53'),                           # acknowledge exception
                (0x86, '\x86\x06\x93\xa2'),                           # slave device busy exception
                (0x87, '\x87\x08\x53\xf2'),                           # memory parity exception
                (0x88, '\x88\x0a\x16\x06'),                           # gateway path unavailable exception
                (0x89, '\x89\x0b\xd6\x56'),                           # gateway target failed exception
        )

        self.bad = (
                (0x80, '\x80\x00\x00\x00'),                           # Unknown Function
                (0x81, '\x81\x00\x00\x00'),                           # error message
        )

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.bad
        del self.request
        del self.response

    def testExceptionLookup(self):
        ''' Test that we can look up exception messages '''
        for func, _ in self.exception:
            response = self.client.lookupPduClass(func)
            self.assertNotEqual(response, None)

        for func, _ in self.exception:
            response = self.server.lookupPduClass(func)
            self.assertNotEqual(response, None)

    def testResponseLookup(self):
        ''' Test a working response factory lookup '''
        for func, _ in self.response:
            response = self.client.lookupPduClass(func)
            self.assertNotEqual(response, None)

    def testRequestLookup(self):
        ''' Test a working request factory lookup '''
        for func, _ in self.request:
            request = self.client.lookupPduClass(func)
            self.assertNotEqual(request, None)

    def testResponseWorking(self):
        ''' Test a working response factory decoders '''
        for func, msg in self.response:
            try:
                self.client.decode(msg)
            except ModbusException:
                self.fail("Failed to Decode Response Message", func)

    def testResponseErrors(self):
        ''' Test a response factory decoder exceptions '''
        self.assertRaises(ModbusException, self.client._helper, self.bad[0][1])
        self.assertEqual(self.client.decode(self.bad[1][1]).function_code, self.bad[1][0],
                "Failed to decode error PDU")

    def testRequestsWorking(self):
        ''' Test a working request factory decoders '''
        for func, msg in self.request:
            try:
                self.server.decode(msg)
            except ModbusException:
                self.fail("Failed to Decode Request Message", func)

    def testClientFactoryFails(self):
        ''' Tests that a client factory will fail to decode a bad message '''
        self.client._helper = _raise_exception
        actual = self.client.decode(None)
        self.assertEquals(actual, None)

    def testServerFactoryFails(self):
        ''' Tests that a server factory will fail to decode a bad message '''
        self.server._helper = _raise_exception
        actual = self.server.decode(None)
        self.assertEquals(actual, None)

#---------------------------------------------------------------------------#
# I don't actually know what is supposed to be returned here, I assume that
# since the high bit is set, it will simply echo the resulting message
#---------------------------------------------------------------------------#
    def testRequestErrors(self):
        ''' Test a request factory decoder exceptions '''
        for func, msg in self.bad:
            result = self.server.decode(msg)
            self.assertEqual(result.ErrorCode, 1,
                    "Failed to decode invalid requests")
            self.assertEqual(result.execute(None).function_code, func,
                    "Failed to create correct response message")

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_file_message
#!/usr/bin/env python
'''
Bit Message Test Fixture
--------------------------------

This fixture tests the functionality of all the 
bit based request/response messages:

* Read/Write Discretes
* Read Coils
'''
import unittest
from pymodbus.file_message import *
from pymodbus.exceptions import *
from pymodbus.pdu import ModbusExceptions

from modbus_mocks import MockContext

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class ModbusBitMessageTests(unittest.TestCase):

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#

    def setUp(self):
        '''
        Initializes the test environment and builds request/result
        encoding pairs
        '''
        pass

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    #-----------------------------------------------------------------------#
    # Read Fifo Queue
    #-----------------------------------------------------------------------#

    def testReadFifoQueueRequestEncode(self):
        ''' Test basic bit message encoding/decoding '''
        handle  = ReadFifoQueueRequest(0x1234)
        result  = handle.encode()
        self.assertEqual(result, '\x12\x34')

    def testReadFifoQueueRequestDecode(self):
        ''' Test basic bit message encoding/decoding '''
        handle  = ReadFifoQueueRequest(0x0000)
        handle.decode('\x12\x34')
        self.assertEqual(handle.address, 0x1234)

    def testReadFifoQueueRequest(self):
        ''' Test basic bit message encoding/decoding '''
        context = MockContext()
        handle  = ReadFifoQueueRequest(0x1234)
        result  = handle.execute(context)
        self.assertTrue(isinstance(result, ReadFifoQueueResponse))

        handle.address = -1
        result  = handle.execute(context)
        self.assertEqual(ModbusExceptions.IllegalValue,
                result.exception_code)

        handle.values = [0x00]*33
        result  = handle.execute(context)
        self.assertEqual(ModbusExceptions.IllegalValue,
                result.exception_code)

    def testReadFifoQueueRequestError(self):
        ''' Test basic bit message encoding/decoding '''
        context = MockContext()
        handle  = ReadFifoQueueRequest(0x1234)
        handle.values = [0x00]*32
        result = handle.execute(context)
        self.assertEqual(result.function_code, 0x98)

    def testReadFifoQueueResponseEncode(self):
        ''' Test that the read fifo queue response can encode '''
        message = '\x00\n\x00\x08\x00\x01\x00\x02\x00\x03\x00\x04'
        handle  = ReadFifoQueueResponse([1,2,3,4])
        result  = handle.encode()
        self.assertEqual(result, message)

    def testReadFifoQueueResponseDecode(self):
        ''' Test that the read fifo queue response can decode '''
        message = '\x00\n\x00\x08\x00\x01\x00\x02\x00\x03\x00\x04'
        handle  = ReadFifoQueueResponse([1,2,3,4])
        handle.decode(message)
        self.assertEqual(handle.values, [1,2,3,4])

    def testRtuFrameSize(self):
        ''' Test that the read fifo queue response can decode '''
        message = '\x00\n\x00\x08\x00\x01\x00\x02\x00\x03\x00\x04'
        result  = ReadFifoQueueResponse.calculateRtuFrameSize(message)
        self.assertEqual(result, 14)

    #-----------------------------------------------------------------------#
    # File Record
    #-----------------------------------------------------------------------#

    def testFileRecordLength(self):
        ''' Test file record length generation '''
        record = FileRecord(file_number=0x01, record_number=0x02,
            record_data='\x00\x01\x02\x04')
        self.assertEqual(record.record_length, 0x02)
        self.assertEqual(record.response_length, 0x05)

    def testFileRecordComapre(self):
        ''' Test file record comparison operations '''
        record1 = FileRecord(file_number=0x01, record_number=0x02, record_data='\x00\x01\x02\x04')
        record2 = FileRecord(file_number=0x01, record_number=0x02, record_data='\x00\x0a\x0e\x04')
        record3 = FileRecord(file_number=0x02, record_number=0x03, record_data='\x00\x01\x02\x04')
        record4 = FileRecord(file_number=0x01, record_number=0x02, record_data='\x00\x01\x02\x04')
        self.assertTrue(record1 == record4)
        self.assertTrue(record1 != record2)
        self.assertNotEqual(record1, record2)
        self.assertNotEqual(record1, record3)
        self.assertNotEqual(record2, record3)
        self.assertEqual(record1, record4)
        self.assertEqual(str(record1), "FileRecord(file=1, record=2, length=2)")
        self.assertEqual(str(record2), "FileRecord(file=1, record=2, length=2)")
        self.assertEqual(str(record3), "FileRecord(file=2, record=3, length=2)")

    #-----------------------------------------------------------------------#
    # Read File Record Request
    #-----------------------------------------------------------------------#

    def testReadFileRecordRequestEncode(self):
        ''' Test basic bit message encoding/decoding '''
        records = [FileRecord(file_number=0x01, record_number=0x02)]
        handle  = ReadFileRecordRequest(records)
        result  = handle.encode()
        self.assertEqual(result, '\x07\x06\x00\x01\x00\x02\x00\x00')

    def testReadFileRecordRequestDecode(self):
        ''' Test basic bit message encoding/decoding '''
        record  = FileRecord(file_number=0x04, record_number=0x01, record_length=0x02)
        request = '\x0e\x06\x00\x04\x00\x01\x00\x02\x06\x00\x03\x00\x09\x00\x02'
        handle  = ReadFileRecordRequest()
        handle.decode(request)
        self.assertEqual(handle.records[0], record)

    def testReadFileRecordRequestRtuFrameSize(self):
        ''' Test basic bit message encoding/decoding '''
        request = '\x00\x00\x0e\x06\x00\x04\x00\x01\x00\x02\x06\x00\x03\x00\x09\x00\x02'
        handle  = ReadFileRecordRequest()
        size    = handle.calculateRtuFrameSize(request)
        self.assertEqual(size, 0x0e + 5)

    def testReadFileRecordRequestExecute(self):
        ''' Test basic bit message encoding/decoding '''
        handle  = ReadFileRecordRequest()
        result  = handle.execute(None)
        self.assertTrue(isinstance(result, ReadFileRecordResponse))

    #-----------------------------------------------------------------------#
    # Read File Record Response
    #-----------------------------------------------------------------------#

    def testReadFileRecordResponseEncode(self):
        ''' Test basic bit message encoding/decoding '''
        records = [FileRecord(record_data='\x00\x01\x02\x03')]
        handle  = ReadFileRecordResponse(records)
        result  = handle.encode()
        self.assertEqual(result, '\x06\x06\x02\x00\x01\x02\x03')

    def testReadFileRecordResponseDecode(self):
        ''' Test basic bit message encoding/decoding '''
        record  = FileRecord(file_number=0x00, record_number=0x00,
            record_data='\x0d\xfe\x00\x20')
        request = '\x0c\x05\x06\x0d\xfe\x00\x20\x05\x05\x06\x33\xcd\x00\x40'
        handle  = ReadFileRecordResponse()
        handle.decode(request)
        self.assertEqual(handle.records[0], record)

    def testReadFileRecordResponseRtuFrameSize(self):
        ''' Test basic bit message encoding/decoding '''
        request = '\x00\x00\x0c\x05\x06\x0d\xfe\x00\x20\x05\x05\x06\x33\xcd\x00\x40'
        handle  = ReadFileRecordResponse()
        size    = handle.calculateRtuFrameSize(request)
        self.assertEqual(size, 0x0c + 5)

    #-----------------------------------------------------------------------#
    # Write File Record Request
    #-----------------------------------------------------------------------#

    def testWriteFileRecordRequestEncode(self):
        ''' Test basic bit message encoding/decoding '''
        records = [FileRecord(file_number=0x01, record_number=0x02, record_data='\x00\x01\x02\x03')]
        handle  = WriteFileRecordRequest(records)
        result  = handle.encode()
        self.assertEqual(result, '\x0b\x06\x00\x01\x00\x02\x00\x02\x00\x01\x02\x03')

    def testWriteFileRecordRequestDecode(self):
        ''' Test basic bit message encoding/decoding '''
        record  = FileRecord(file_number=0x04, record_number=0x07,
            record_data='\x06\xaf\x04\xbe\x10\x0d')
        request = '\x0d\x06\x00\x04\x00\x07\x00\x03\x06\xaf\x04\xbe\x10\x0d'
        handle  = WriteFileRecordRequest()
        handle.decode(request)
        self.assertEqual(handle.records[0], record)

    def testWriteFileRecordRequestRtuFrameSize(self):
        ''' Test write file record request rtu frame size calculation '''
        request = '\x00\x00\x0d\x06\x00\x04\x00\x07\x00\x03\x06\xaf\x04\xbe\x10\x0d'
        handle  = WriteFileRecordRequest()
        size    = handle.calculateRtuFrameSize(request)
        self.assertEqual(size, 0x0d + 5)

    def testWriteFileRecordRequestExecute(self):
        ''' Test basic bit message encoding/decoding '''
        handle  = WriteFileRecordRequest()
        result  = handle.execute(None)
        self.assertTrue(isinstance(result, WriteFileRecordResponse))

    #-----------------------------------------------------------------------#
    # Write File Record Response
    #-----------------------------------------------------------------------#

    def testWriteFileRecordResponseEncode(self):
        ''' Test basic bit message encoding/decoding '''
        records = [FileRecord(file_number=0x01, record_number=0x02, record_data='\x00\x01\x02\x03')]
        handle  = WriteFileRecordResponse(records)
        result  = handle.encode()
        self.assertEqual(result, '\x0b\x06\x00\x01\x00\x02\x00\x02\x00\x01\x02\x03')

    def testWriteFileRecordResponseDecode(self):
        ''' Test basic bit message encoding/decoding '''
        record  = FileRecord(file_number=0x04, record_number=0x07,
            record_data='\x06\xaf\x04\xbe\x10\x0d')
        request = '\x0d\x06\x00\x04\x00\x07\x00\x03\x06\xaf\x04\xbe\x10\x0d'
        handle  = WriteFileRecordResponse()
        handle.decode(request)
        self.assertEqual(handle.records[0], record)

    def testWriteFileRecordResponseRtuFrameSize(self):
        ''' Test write file record response rtu frame size calculation '''
        request = '\x00\x00\x0d\x06\x00\x04\x00\x07\x00\x03\x06\xaf\x04\xbe\x10\x0d'
        handle  = WriteFileRecordResponse()
        size    = handle.calculateRtuFrameSize(request)
        self.assertEqual(size, 0x0d + 5)

    #-----------------------------------------------------------------------#
    # Mask Write Register Request
    #-----------------------------------------------------------------------#

    def testMaskWriteRegisterRequestEncode(self):
        ''' Test basic bit message encoding/decoding '''
        handle  = MaskWriteRegisterRequest(0x0000, 0x0101, 0x1010)
        result  = handle.encode()
        self.assertEqual(result, '\x00\x00\x01\x01\x10\x10')

    def testMaskWriteRegisterRequestDecode(self):
        ''' Test basic bit message encoding/decoding '''
        request = '\x00\x04\x00\xf2\x00\x25'
        handle  = MaskWriteRegisterRequest()
        handle.decode(request)
        self.assertEqual(handle.address, 0x0004)
        self.assertEqual(handle.and_mask, 0x00f2)
        self.assertEqual(handle.or_mask, 0x0025)

    def testMaskWriteRegisterRequestExecute(self):
        ''' Test write register request valid execution '''
        context = MockContext(valid=True, default=0x0000)
        handle  = MaskWriteRegisterRequest(0x0000, 0x0101, 0x1010)
        result  = handle.execute(context)
        self.assertTrue(isinstance(result, MaskWriteRegisterResponse))

    def testMaskWriteRegisterRequestInvalidExecute(self):
        ''' Test write register request execute with invalid data '''
        context = MockContext(valid=False, default=0x0000)
        handle  = MaskWriteRegisterRequest(0x0000, -1, 0x1010)
        result  = handle.execute(context)
        self.assertEqual(ModbusExceptions.IllegalValue,
                result.exception_code)

        handle  = MaskWriteRegisterRequest(0x0000, 0x0101, -1)
        result  = handle.execute(context)
        self.assertEqual(ModbusExceptions.IllegalValue,
                result.exception_code)

        handle  = MaskWriteRegisterRequest(0x0000, 0x0101, 0x1010)
        result  = handle.execute(context)
        self.assertEqual(ModbusExceptions.IllegalAddress,
                result.exception_code)

    #-----------------------------------------------------------------------#
    # Mask Write Register Response
    #-----------------------------------------------------------------------#

    def testMaskWriteRegisterResponseEncode(self):
        ''' Test basic bit message encoding/decoding '''
        handle  = MaskWriteRegisterResponse(0x0000, 0x0101, 0x1010)
        result  = handle.encode()
        self.assertEqual(result, '\x00\x00\x01\x01\x10\x10')

    def testMaskWriteRegisterResponseDecode(self):
        ''' Test basic bit message encoding/decoding '''
        request = '\x00\x04\x00\xf2\x00\x25'
        handle  = MaskWriteRegisterResponse()
        handle.decode(request)
        self.assertEqual(handle.address, 0x0004)
        self.assertEqual(handle.and_mask, 0x00f2)
        self.assertEqual(handle.or_mask, 0x0025)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_fixes
#!/usr/bin/env python
import unittest

class ModbusFixesTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus._version code
    '''

    def testTrueFalseDefined(self):
        ''' Test that True and False are defined on all versions'''
        try:
            True,False
        except NameError:
            import pymodbus
            self.assertEqual(True, 1)
            self.assertEqual(False, 1)

    def testNullLoggerAttached(self):
        ''' Test that the null logger is attached'''
        import logging
        logger = logging.getLogger('pymodbus')
        self.assertEqual(len(logger.handlers), 1)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_interfaces
#!/usr/bin/env python
import unittest
from pymodbus.interfaces import *
from pymodbus.exceptions import NotImplementedException

class _SingleInstance(Singleton):
    pass

class ModbusInterfaceTestsTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.interfaces module
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        pass

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    def testSingletonInterface(self):
        ''' Test that the singleton interface works '''
        first  = _SingleInstance()
        second = _SingleInstance()
        self.assertEquals(first, second)

    def testModbusDecoderInterface(self):
        ''' Test that the base class isn't implemented '''
        x = None
        instance = IModbusDecoder()
        self.assertRaises(NotImplementedException, lambda: instance.decode(x))
        self.assertRaises(NotImplementedException, lambda: instance.lookupPduClass(x))

    def testModbusFramerInterface(self):
        ''' Test that the base class isn't implemented '''
        x = None
        instance = IModbusFramer()
        self.assertRaises(NotImplementedException, instance.checkFrame)
        self.assertRaises(NotImplementedException, instance.advanceFrame)
        self.assertRaises(NotImplementedException, instance.isFrameReady)
        self.assertRaises(NotImplementedException, instance.getFrame)
        self.assertRaises(NotImplementedException, lambda: instance.addToFrame(x))
        self.assertRaises(NotImplementedException, lambda: instance.populateResult(x))
        self.assertRaises(NotImplementedException, lambda: instance.processIncomingPacket(x,x))
        self.assertRaises(NotImplementedException, lambda: instance.buildPacket(x))

    def testModbusSlaveContextInterface(self):
        ''' Test that the base class isn't implemented '''
        x = None
        instance = IModbusSlaveContext()
        self.assertRaises(NotImplementedException, instance.reset)
        self.assertRaises(NotImplementedException, lambda: instance.validate(x,x,x))
        self.assertRaises(NotImplementedException, lambda: instance.getValues(x,x,x))
        self.assertRaises(NotImplementedException, lambda: instance.setValues(x,x,x))

    def testModbusPayloadBuilderInterface(self):
        ''' Test that the base class isn't implemented '''
        x = None
        instance = IPayloadBuilder()
        self.assertRaises(NotImplementedException, lambda: instance.build())

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mei_messages
#!/usr/bin/env python
'''
MEI Message Test Fixture
--------------------------------

This fixture tests the functionality of all the 
mei based request/response messages:
'''
import unittest
from pymodbus.mei_message import *
from pymodbus.constants import DeviceInformation, MoreData
from pymodbus.pdu import ModbusExceptions
from pymodbus.device import ModbusControlBlock

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class ModbusMeiMessageTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.mei_message module
    '''

    #-----------------------------------------------------------------------#
    # Read Device Information
    #-----------------------------------------------------------------------#

    def testReadDeviceInformationRequestEncode(self):
        ''' Test basic bit message encoding/decoding '''
        params  = {'read_code':DeviceInformation.Basic, 'object_id':0x00 }
        handle  = ReadDeviceInformationRequest(**params)
        result  = handle.encode()
        self.assertEqual(result, '\x0e\x01\x00')
        self.assertEqual("ReadDeviceInformationRequest(1,0)", str(handle))

    def testReadDeviceInformationRequestDecode(self):
        ''' Test basic bit message encoding/decoding '''
        handle  = ReadDeviceInformationRequest()
        handle.decode('\x0e\x01\x00')
        self.assertEqual(handle.read_code, DeviceInformation.Basic)
        self.assertEqual(handle.object_id, 0x00)

    def testReadDeviceInformationRequest(self):
        ''' Test basic bit message encoding/decoding '''
        context = None
        control = ModbusControlBlock()
        control.Identity.VendorName  = "Company"
        control.Identity.ProductCode = "Product"
        control.Identity.MajorMinorevision = "v2.1.12"

        handle  = ReadDeviceInformationRequest()
        result  = handle.execute(context)
        self.assertTrue(isinstance(result, ReadDeviceInformationResponse))
        self.assertTrue(result.information[0x00], "Company")
        self.assertTrue(result.information[0x01], "Product")
        self.assertTrue(result.information[0x02], "v2.1.12")

    def testReadDeviceInformationRequestError(self):
        ''' Test basic bit message encoding/decoding '''
        handle  = ReadDeviceInformationRequest()
        handle.read_code = -1
        self.assertEqual(handle.execute(None).function_code, 0xab)
        handle.read_code = 0x05
        self.assertEqual(handle.execute(None).function_code, 0xab)
        handle.object_id = -1
        self.assertEqual(handle.execute(None).function_code, 0xab)
        handle.object_id = 0x100
        self.assertEqual(handle.execute(None).function_code, 0xab)

    def testReadDeviceInformationResponseEncode(self):
        ''' Test that the read fifo queue response can encode '''
        message  = '\x0e\x01\x83\x00\x00\x03'
        message += '\x00\x07Company\x01\x07Product\x02\x07v2.1.12' 
        dataset  = {
            0x00: 'Company',
            0x01: 'Product',
            0x02: 'v2.1.12',
        }
        handle  = ReadDeviceInformationResponse(
            read_code=DeviceInformation.Basic, information=dataset)
        result  = handle.encode()
        self.assertEqual(result, message)
        self.assertEqual("ReadDeviceInformationResponse(1)", str(handle))

    def testReadDeviceInformationResponseDecode(self):
        ''' Test that the read device information response can decode '''
        message  = '\x0e\x01\x01\x00\x00\x03'
        message += '\x00\x07Company\x01\x07Product\x02\x07v2.1.12' 
        handle  = ReadDeviceInformationResponse(read_code=0x00, information=[])
        handle.decode(message)
        self.assertEqual(handle.read_code, DeviceInformation.Basic)
        self.assertEqual(handle.conformity, 0x01)
        self.assertEqual(handle.information[0x00], 'Company')
        self.assertEqual(handle.information[0x01], 'Product')
        self.assertEqual(handle.information[0x02], 'v2.1.12')

    def testRtuFrameSize(self):
        ''' Test that the read device information response can decode '''
        message = '\x04\x2B\x0E\x01\x81\x00\x01\x01\x00\x06\x66\x6F\x6F\x62\x61\x72\xD7\x3B'
        result  = ReadDeviceInformationResponse.calculateRtuFrameSize(message)
        self.assertEqual(result, 18)


#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_other_messages
#!/usr/bin/env python
import unittest
from pymodbus.other_message import *

class ModbusOtherMessageTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.other_message module
    '''

    def setUp(self):
        self.requests = [
            ReadExceptionStatusRequest,
            GetCommEventCounterRequest,
            GetCommEventLogRequest,
            ReportSlaveIdRequest,
        ]

        self.responses = [
            lambda: ReadExceptionStatusResponse(0x12),
            lambda: GetCommEventCounterResponse(0x12),
            GetCommEventLogResponse,
            lambda: ReportSlaveIdResponse(0x12),
        ]

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.requests
        del self.responses

    def testOtherMessagesToString(self):
        for message in self.requests:
            self.assertNotEqual(str(message()), None)
        for message in self.responses:
            self.assertNotEqual(str(message()), None)

    def testReadExceptionStatus(self):
        request = ReadExceptionStatusRequest()
        request.decode('\x12')
        self.assertEqual(request.encode(), '')
        self.assertEqual(request.execute().function_code, 0x07)

        response = ReadExceptionStatusResponse(0x12)
        self.assertEqual(response.encode(), '\x12')
        response.decode('\x12')
        self.assertEqual(response.status, 0x12)

    def testGetCommEventCounter(self):
        request = GetCommEventCounterRequest()
        request.decode('\x12')
        self.assertEqual(request.encode(), '')
        self.assertEqual(request.execute().function_code, 0x0b)

        response = GetCommEventCounterResponse(0x12)
        self.assertEqual(response.encode(), '\x00\x00\x00\x12')
        response.decode('\x00\x00\x00\x12')
        self.assertEqual(response.status, True)
        self.assertEqual(response.count, 0x12)

        response.status = False
        self.assertEqual(response.encode(), '\xFF\xFF\x00\x12')

    def testGetCommEventLog(self):
        request = GetCommEventLogRequest()
        request.decode('\x12')
        self.assertEqual(request.encode(), '')
        self.assertEqual(request.execute().function_code, 0x0c)

        response = GetCommEventLogResponse()
        self.assertEqual(response.encode(), '\x06\x00\x00\x00\x00\x00\x00')
        response.decode('\x06\x00\x00\x00\x12\x00\x12')
        self.assertEqual(response.status, True)
        self.assertEqual(response.message_count, 0x12)
        self.assertEqual(response.event_count, 0x12)
        self.assertEqual(response.events, [])

        response.status = False
        self.assertEqual(response.encode(), '\x06\xff\xff\x00\x12\x00\x12')

    def testGetCommEventLogWithEvents(self):
        response = GetCommEventLogResponse(events=[0x12,0x34,0x56])
        self.assertEqual(response.encode(), '\x09\x00\x00\x00\x00\x00\x00\x12\x34\x56')
        response.decode('\x09\x00\x00\x00\x12\x00\x12\x12\x34\x56')
        self.assertEqual(response.status, True)
        self.assertEqual(response.message_count, 0x12)
        self.assertEqual(response.event_count, 0x12)
        self.assertEqual(response.events, [0x12,0x34,0x56])

    def testReportSlaveId(self):
        request = ReportSlaveIdRequest()
        request.decode('\x12')
        self.assertEqual(request.encode(), '')
        self.assertEqual(request.execute().function_code, 0x11)

        response = ReportSlaveIdResponse(request.execute().identifier, True)
        self.assertEqual(response.encode(), '\x0apymodbus\xff')
        response.decode('\x03\x12\x00')
        self.assertEqual(response.status, False)
        self.assertEqual(response.identifier, '\x12\x00')

        response.status = False
        self.assertEqual(response.encode(), '\x04\x12\x00\x00')

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_payload
#!/usr/bin/env python
'''
Payload Utilities Test Fixture
--------------------------------
This fixture tests the functionality of the payload
utilities.

* PayloadBuilder
* PayloadDecoder
'''
import unittest
from pymodbus.exceptions import ParameterException
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class ModbusPayloadUtilityTests(unittest.TestCase):

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#

    def setUp(self):
        '''
        Initializes the test environment and builds request/result
        encoding pairs
        '''
        self.little_endian_payload = \
                       '\x01\x02\x00\x03\x00\x00\x00\x04\x00\x00\x00\x00' \
                       '\x00\x00\x00\xff\xfe\xff\xfd\xff\xff\xff\xfc\xff' \
                       '\xff\xff\xff\xff\xff\xff\x00\x00\xa0\x3f\x00\x00' \
                       '\x00\x00\x00\x00\x19\x40\x74\x65\x73\x74\x11'

        self.big_endian_payload = \
                       '\x01\x00\x02\x00\x00\x00\x03\x00\x00\x00\x00\x00' \
                       '\x00\x00\x04\xff\xff\xfe\xff\xff\xff\xfd\xff\xff' \
                       '\xff\xff\xff\xff\xff\xfc\x3f\xa0\x00\x00\x40\x19' \
                       '\x00\x00\x00\x00\x00\x00\x74\x65\x73\x74\x11'

        self.bitstring = [True, False, False, False, True, False, False, False]

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    #-----------------------------------------------------------------------#
    # Payload Builder Tests
    #-----------------------------------------------------------------------#

    def testLittleEndianPayloadBuilder(self):
        ''' Test basic bit message encoding/decoding '''
        builder = BinaryPayloadBuilder(endian=Endian.Little)
        builder.add_8bit_uint(1)
        builder.add_16bit_uint(2)
        builder.add_32bit_uint(3)
        builder.add_64bit_uint(4)
        builder.add_8bit_int(-1)
        builder.add_16bit_int(-2)
        builder.add_32bit_int(-3)
        builder.add_64bit_int(-4)
        builder.add_32bit_float(1.25)
        builder.add_64bit_float(6.25)
        builder.add_string('test')
        builder.add_bits(self.bitstring)
        self.assertEqual(self.little_endian_payload, str(builder))

    def testBigEndianPayloadBuilder(self):
        ''' Test basic bit message encoding/decoding '''
        builder = BinaryPayloadBuilder(endian=Endian.Big)
        builder.add_8bit_uint(1)
        builder.add_16bit_uint(2)
        builder.add_32bit_uint(3)
        builder.add_64bit_uint(4)
        builder.add_8bit_int(-1)
        builder.add_16bit_int(-2)
        builder.add_32bit_int(-3)
        builder.add_64bit_int(-4)
        builder.add_32bit_float(1.25)
        builder.add_64bit_float(6.25)
        builder.add_string('test')
        builder.add_bits(self.bitstring)
        self.assertEqual(self.big_endian_payload, str(builder))

    def testPayloadBuilderReset(self):
        ''' Test basic bit message encoding/decoding '''
        builder = BinaryPayloadBuilder()
        builder.add_8bit_uint(0x12)
        builder.add_8bit_uint(0x34)
        builder.add_8bit_uint(0x56)
        builder.add_8bit_uint(0x78)
        self.assertEqual('\x12\x34\x56\x78', str(builder))
        self.assertEqual(['\x12\x34', '\x56\x78'], builder.build())
        builder.reset()
        self.assertEqual('', str(builder))
        self.assertEqual([], builder.build())

    #-----------------------------------------------------------------------#
    # Payload Decoder Tests
    #-----------------------------------------------------------------------#

    def testLittleEndianPayloadDecoder(self):
        ''' Test basic bit message encoding/decoding '''
        decoder = BinaryPayloadDecoder(self.little_endian_payload, endian=Endian.Little)
        self.assertEqual(1,      decoder.decode_8bit_uint())
        self.assertEqual(2,      decoder.decode_16bit_uint())
        self.assertEqual(3,      decoder.decode_32bit_uint())
        self.assertEqual(4,      decoder.decode_64bit_uint())
        self.assertEqual(-1,     decoder.decode_8bit_int())
        self.assertEqual(-2,     decoder.decode_16bit_int())
        self.assertEqual(-3,     decoder.decode_32bit_int())
        self.assertEqual(-4,     decoder.decode_64bit_int())
        self.assertEqual(1.25,   decoder.decode_32bit_float())
        self.assertEqual(6.25,   decoder.decode_64bit_float())
        self.assertEqual('test', decoder.decode_string(4))
        self.assertEqual(self.bitstring, decoder.decode_bits())

    def testBigEndianPayloadDecoder(self):
        ''' Test basic bit message encoding/decoding '''
        decoder = BinaryPayloadDecoder(self.big_endian_payload, endian=Endian.Big)
        self.assertEqual(1,      decoder.decode_8bit_uint())
        self.assertEqual(2,      decoder.decode_16bit_uint())
        self.assertEqual(3,      decoder.decode_32bit_uint())
        self.assertEqual(4,      decoder.decode_64bit_uint())
        self.assertEqual(-1,     decoder.decode_8bit_int())
        self.assertEqual(-2,     decoder.decode_16bit_int())
        self.assertEqual(-3,     decoder.decode_32bit_int())
        self.assertEqual(-4,     decoder.decode_64bit_int())
        self.assertEqual(1.25,   decoder.decode_32bit_float())
        self.assertEqual(6.25,   decoder.decode_64bit_float())
        self.assertEqual('test', decoder.decode_string(4))
        self.assertEqual(self.bitstring, decoder.decode_bits())

    def testPayloadDecoderReset(self):
        ''' Test the payload decoder reset functionality '''
        decoder = BinaryPayloadDecoder('\x12\x34')
        self.assertEqual(0x12, decoder.decode_8bit_uint())
        self.assertEqual(0x34, decoder.decode_8bit_uint())
        decoder.reset()   
        self.assertEqual(0x3412, decoder.decode_16bit_uint())

    def testPayloadDecoderRegisterFactory(self):
        ''' Test the payload decoder reset functionality '''
        payload = [1,2,3,4]
        decoder = BinaryPayloadDecoder.fromRegisters(payload, endian=Endian.Little)
        encoded = '\x00\x01\x00\x02\x00\x03\x00\x04'
        self.assertEqual(encoded, decoder.decode_string(8))

        decoder = BinaryPayloadDecoder.fromRegisters(payload, endian=Endian.Big)
        encoded = '\x00\x01\x00\x02\x00\x03\x00\x04'
        self.assertEqual(encoded, decoder.decode_string(8))

        self.assertRaises(ParameterException,
            lambda: BinaryPayloadDecoder.fromRegisters('abcd'))

    def testPayloadDecoderCoilFactory(self):
        ''' Test the payload decoder reset functionality '''
        payload = [1,0,0,0, 1,0,0,0, 0,0,0,1, 0,0,0,1]
        decoder = BinaryPayloadDecoder.fromCoils(payload, endian=Endian.Little)
        encoded = '\x11\x88'
        self.assertEqual(encoded, decoder.decode_string(2))

        decoder = BinaryPayloadDecoder.fromCoils(payload, endian=Endian.Big)
        encoded = '\x11\x88'
        self.assertEqual(encoded, decoder.decode_string(2))

        self.assertRaises(ParameterException,
            lambda: BinaryPayloadDecoder.fromCoils('abcd'))


#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pdu
#!/usr/bin/env python
import unittest
from pymodbus.pdu import *
from pymodbus.exceptions import *

class SimplePduTest(unittest.TestCase):
    '''
    This is the unittest for the pymod.pdu module
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        self.badRequests = (
        #       ModbusPDU(),
                ModbusRequest(),
                ModbusResponse(),
        )
        self.illegal = IllegalFunctionRequest(1)
        self.exception = ExceptionResponse(1,1)

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.badRequests
        del self.illegal
        del self.exception

    def testNotImpelmented(self):
        ''' Test a base classes for not implemented funtions '''
        for r in self.badRequests:
            self.assertRaises(NotImplementedException, r.encode)

        for r in self.badRequests:
            self.assertRaises(NotImplementedException, r.decode, None)

    def testErrorMethods(self):
        ''' Test all error methods '''
        self.illegal.decode("12345")
        self.illegal.execute(None)

        result = self.exception.encode()
        self.exception.decode(result)
        self.assertEqual(result, '\x01')
        self.assertEqual(self.exception.exception_code, 1)

    def testRequestExceptionFactory(self):
        ''' Test all error methods '''
        request = ModbusRequest()
        request.function_code = 1
        errors = dict((ModbusExceptions.decode(c), c) for c in range(1,20))
        for error, code in errors.iteritems():
            result = request.doException(code)
            self.assertEqual(str(result), "Exception Response(129, 1, %s)" % error)

    def testCalculateRtuFrameSize(self):
        ''' Test the calculation of Modbus/RTU frame sizes '''
        self.assertRaises(NotImplementedException,
                          ModbusRequest.calculateRtuFrameSize, "")
        ModbusRequest._rtu_frame_size = 5
        self.assertEqual(ModbusRequest.calculateRtuFrameSize(""), 5)
        del ModbusRequest._rtu_frame_size

        ModbusRequest._rtu_byte_count_pos = 2
        self.assertEqual(ModbusRequest.calculateRtuFrameSize(
            "\x11\x01\x05\xcd\x6b\xb2\x0e\x1b\x45\xe6"), 0x05 + 5)
        del ModbusRequest._rtu_byte_count_pos
        
        self.assertRaises(NotImplementedException,
                          ModbusResponse.calculateRtuFrameSize, "")
        ModbusResponse._rtu_frame_size = 12
        self.assertEqual(ModbusResponse.calculateRtuFrameSize(""), 12)
        del ModbusResponse._rtu_frame_size
        ModbusResponse._rtu_byte_count_pos = 2
        self.assertEqual(ModbusResponse.calculateRtuFrameSize(
            "\x11\x01\x05\xcd\x6b\xb2\x0e\x1b\x45\xe6"), 0x05 + 5)
        del ModbusResponse._rtu_byte_count_pos
        
        
#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_ptwisted
#!/usr/bin/env python
import unittest

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class TwistedInternalCodeTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.internal.ptwisted code
    '''

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#

    def testInstallConch(self):
        ''' Test that we can install the conch backend '''
        pass

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_register_read_messages
#!/usr/bin/env python
import unittest
from pymodbus.register_read_message import *
from pymodbus.register_read_message import ReadRegistersRequestBase
from pymodbus.register_read_message import ReadRegistersResponseBase
from pymodbus.exceptions import *
from pymodbus.pdu import ModbusExceptions

from modbus_mocks import MockContext, FakeList

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class ReadRegisterMessagesTest(unittest.TestCase):
    '''
    Register Message Test Fixture
    --------------------------------
    This fixture tests the functionality of all the 
    register based request/response messages:
    
    * Read/Write Input Registers
    * Read Holding Registers
    '''

    def setUp(self):
        '''
        Initializes the test environment and builds request/result
        encoding pairs
        '''
        arguments = {
            'read_address':  1, 'read_count': 5,
            'write_address': 1, 'write_registers': [0x00]*5,
        }
        self.value  = 0xabcd
        self.values = [0xa, 0xb, 0xc]
        self.request_read  = {
            ReadRegistersRequestBase(1, 5)                  :'\x00\x01\x00\x05',
            ReadHoldingRegistersRequest(1, 5)               :'\x00\x01\x00\x05',
            ReadInputRegistersRequest(1,5)                  :'\x00\x01\x00\x05',
            ReadWriteMultipleRegistersRequest(**arguments)  :'\x00\x01\x00\x05\x00\x01\x00'
                                                             '\x05\x0a\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        }
        self.response_read  = {
            ReadRegistersResponseBase(self.values)          :'\x06\x00\x0a\x00\x0b\x00\x0c',
            ReadHoldingRegistersResponse(self.values)       :'\x06\x00\x0a\x00\x0b\x00\x0c',
            ReadInputRegistersResponse(self.values)         :'\x06\x00\x0a\x00\x0b\x00\x0c',
            ReadWriteMultipleRegistersResponse(self.values) :'\x06\x00\x0a\x00\x0b\x00\x0c',
        }

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.request_read
        del self.response_read

    def testReadRegisterResponseBase(self):
        response = ReadRegistersResponseBase(range(10))
        for index in range(10):
            self.assertEqual(response.getRegister(index), index)

    def testRegisterReadRequests(self):
        for request, response in self.request_read.iteritems():
            self.assertEqual(request.encode(), response)

    def testRegisterReadResponses(self):
        for request, response in self.response_read.iteritems():
            self.assertEqual(request.encode(), response)

    def testRegisterReadResponseDecode(self):
        registers = [
            [0x0a,0x0b,0x0c],
            [0x0a,0x0b,0x0c],
            [0x0a,0x0b,0x0c],
            [0x0a,0x0b,0x0c, 0x0a,0x0b,0x0c],
        ]
        values = sorted(self.response_read.iteritems())
        for packet, register in zip(values, registers):
            request, response = packet
            request.decode(response)
            self.assertEqual(request.registers, register)

    def testRegisterReadRequestsCountErrors(self):
        '''
        This tests that the register request messages
        will break on counts that are out of range
        '''
        mock = FakeList(0x800)
        requests = [
            ReadHoldingRegistersRequest(1, 0x800),
            ReadInputRegistersRequest(1,0x800),
            ReadWriteMultipleRegistersRequest(read_address=1,
                read_count=0x800, write_address=1, write_registers=5),
            ReadWriteMultipleRegistersRequest(read_address=1,
                read_count=5, write_address=1, write_registers=mock),
        ]
        for request in requests:
            result = request.execute(None)
            self.assertEqual(ModbusExceptions.IllegalValue,
                result.exception_code)

    def testRegisterReadRequestsValidateErrors(self):
        '''
        This tests that the register request messages
        will break on counts that are out of range
        '''
        context = MockContext()
        requests = [
            ReadHoldingRegistersRequest(-1, 5),
            ReadInputRegistersRequest(-1,5),
            #ReadWriteMultipleRegistersRequest(-1,5,1,5),
            #ReadWriteMultipleRegistersRequest(1,5,-1,5),
        ]
        for request in requests:
            result = request.execute(context)
            self.assertEqual(ModbusExceptions.IllegalAddress,
                result.exception_code)

    def testRegisterReadRequestsExecute(self):
        '''
        This tests that the register request messages
        will break on counts that are out of range
        '''
        context = MockContext(True)
        requests = [
            ReadHoldingRegistersRequest(-1, 5),
            ReadInputRegistersRequest(-1,5),
        ]
        for request in requests:
            response = request.execute(context)
            self.assertEqual(request.function_code, response.function_code)

    def testReadWriteMultipleRegistersRequest(self):
        context = MockContext(True)
        request = ReadWriteMultipleRegistersRequest(read_address=1,
            read_count=10, write_address=1, write_registers=[0x00])
        response = request.execute(context)
        self.assertEqual(request.function_code, response.function_code)

    def testReadWriteMultipleRegistersValidate(self):
        context = MockContext()
        context.validate = lambda f,a,c: a == 1
        request = ReadWriteMultipleRegistersRequest(read_address=1,
            read_count=10, write_address=2, write_registers=[0x00])
        response = request.execute(context)
        self.assertEqual(response.exception_code, ModbusExceptions.IllegalAddress)

        context.validate = lambda f,a,c: a == 2
        response = request.execute(context)
        self.assertEqual(response.exception_code, ModbusExceptions.IllegalAddress)

        request.write_byte_count = 0x100
        response = request.execute(context)
        self.assertEqual(response.exception_code, ModbusExceptions.IllegalValue)

    def testReadWriteMultipleRegistersRequestDecode(self):
        request, response = sorted(self.request_read.items())[-1]
        request.decode(response)
        self.assertEqual(request.read_address, 0x01)
        self.assertEqual(request.write_address, 0x01)
        self.assertEqual(request.read_count, 0x05)
        self.assertEqual(request.write_count, 0x05)
        self.assertEqual(request.write_byte_count, 0x0a)
        self.assertEqual(request.write_registers, [0x00]*5)

    def testSerializingToString(self):
        for request in self.request_read.iterkeys():
            self.assertTrue(str(request) != None)
        for request in self.response_read.iterkeys():
            self.assertTrue(str(request) != None)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_register_write_messages
#!/usr/bin/env python
import unittest
from pymodbus.register_write_message import *
from pymodbus.exceptions import ParameterException
from pymodbus.pdu import ModbusExceptions

from modbus_mocks import MockContext

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class WriteRegisterMessagesTest(unittest.TestCase):
    '''
    Register Message Test Fixture
    --------------------------------
    This fixture tests the functionality of all the 
    register based request/response messages:
    
    * Read/Write Input Registers
    * Read Holding Registers
    '''

    def setUp(self):
        '''
        Initializes the test environment and builds request/result
        encoding pairs
        '''
        self.value  = 0xabcd
        self.values = [0xa, 0xb, 0xc]
        self.write = {
            WriteSingleRegisterRequest(1, self.value)       : '\x00\x01\xab\xcd',
            WriteSingleRegisterResponse(1, self.value)      : '\x00\x01\xab\xcd',
            WriteMultipleRegistersRequest(1, self.values)   : '\x00\x01\x00\x03\x06\x00\n\x00\x0b\x00\x0c',
            WriteMultipleRegistersResponse(1, 5)            : '\x00\x01\x00\x05',
        }

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.write

    def testRegisterWriteRequestsEncode(self):
        for request, response in self.write.iteritems():
            self.assertEqual(request.encode(), response)

    def testRegisterWriteRequestsDecode(self):
        addresses = [1,1,1,1]
        values = sorted(self.write.items())
        for packet, address in zip(values, addresses):
            request, response = packet
            request.decode(response)
            self.assertEqual(request.address, address)

    def testInvalidWriteMultipleRegistersRequest(self):
        request = WriteMultipleRegistersRequest(0, None)
        self.assertEquals(request.values, [])

    def testSerializingToString(self):
        for request in self.write.iterkeys():
            self.assertTrue(str(request) != None)

    def testWriteSingleRegisterRequest(self):
        context = MockContext()
        request = WriteSingleRegisterRequest(0x00, 0xf0000)
        result = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalValue)

        request.value = 0x00ff
        result = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalAddress)

        context.valid = True
        result = request.execute(context)
        self.assertEqual(result.function_code, request.function_code)

    def testWriteMultipleRegisterRequest(self):
        context = MockContext()
        request = WriteMultipleRegistersRequest(0x00, [0x00]*10)
        result = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalAddress)

        request.count = 0x05 # bytecode != code * 2
        result = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalValue)

        request.count = 0x800 # outside of range
        result = request.execute(context)
        self.assertEqual(result.exception_code, ModbusExceptions.IllegalValue)

        context.valid = True
        request = WriteMultipleRegistersRequest(0x00, [0x00]*10)
        result = request.execute(context)
        self.assertEqual(result.function_code, request.function_code)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_remote_datastore
#!/usr/bin/env python
import unittest
from pymodbus.exceptions import NotImplementedException
from pymodbus.datastore.remote import RemoteSlaveContext
from pymodbus.bit_read_message import *
from pymodbus.bit_write_message import *
from pymodbus.register_read_message import *
from pymodbus.pdu import ExceptionResponse
from modbus_mocks import mock

class RemoteModbusDataStoreTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.datastore.remote module
    '''

    def testRemoteSlaveContext(self):
        ''' Test a modbus remote slave context '''
        context = RemoteSlaveContext(None)
        self.assertNotEqual(str(context), None)
        self.assertRaises(NotImplementedException, lambda: context.reset())

    def testRemoteSlaveSetValues(self):
        ''' Test setting values against a remote slave context '''
        client  = mock()
        client.write_coils = lambda a,b: WriteMultipleCoilsResponse()

        context = RemoteSlaveContext(client)
        result  = context.setValues(1, 0, [1])
        self.assertTrue(True)

    def testRemoteSlaveGetValues(self):
        ''' Test getting values from a remote slave context '''
        client  = mock()
        client.read_coils = lambda a,b: ReadCoilsResponse([1]*10)
        client.read_input_registers = lambda a,b: ReadInputRegistersResponse([10]*10)
        client.read_holding_registers = lambda a,b: ExceptionResponse(0x15)

        context = RemoteSlaveContext(client)
        result  = context.getValues(1, 0, 10)
        self.assertEqual(result, [1]*10)

        result  = context.getValues(4, 0, 10)
        self.assertEqual(result, [10]*10)

        result  = context.getValues(3, 0, 10)
        self.assertNotEqual(result, [10]*10)

    def testRemoteSlaveValidateValues(self):
        ''' Test validating against a remote slave context '''
        client  = mock()
        client.read_coils = lambda a,b: ReadCoilsResponse([1]*10)
        client.read_input_registers = lambda a,b: ReadInputRegistersResponse([10]*10)
        client.read_holding_registers = lambda a,b: ExceptionResponse(0x15)

        context = RemoteSlaveContext(client)
        result  = context.validate(1, 0, 10)
        self.assertTrue(result)

        result  = context.validate(4, 0, 10)
        self.assertTrue(result)

        result  = context.validate(3, 0, 10)
        self.assertFalse(result)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_server_async
#!/usr/bin/env python
import unittest
from mock import patch, Mock
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server.async import ModbusTcpProtocol, ModbusUdpProtocol
from pymodbus.server.async import ModbusServerFactory
from pymodbus.server.async import StartTcpServer, StartUdpServer, StartSerialServer
from pymodbus.exceptions import ConnectionException, NotImplementedException
from pymodbus.exceptions import ParameterException
from pymodbus.bit_read_message import ReadCoilsRequest, ReadCoilsResponse

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class AsynchronousServerTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.server.async module
    '''

    #-----------------------------------------------------------------------#
    # Setup/TearDown
    #-----------------------------------------------------------------------#

    def setUp(self):
        '''
        Initializes the test environment
        '''
        values = dict((i, '') for i in range(10))
        identity = ModbusDeviceIdentification(info=values)

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    #-----------------------------------------------------------------------#
    # Test Modbus Server Factory
    #-----------------------------------------------------------------------#

    def testModbusServerFactory(self):
        ''' Test the base class for all the clients '''
        factory = ModbusServerFactory(store=None)
        self.assertEqual(factory.control.Identity.VendorName, '')

        identity = ModbusDeviceIdentification(info={0x00: 'VendorName'})
        factory = ModbusServerFactory(store=None, identity=identity)
        self.assertEqual(factory.control.Identity.VendorName, 'VendorName')

    #-----------------------------------------------------------------------#
    # Test Modbus TCP Server
    #-----------------------------------------------------------------------#
    def testTCPServerDisconnect(self):
        protocol = ModbusTcpProtocol()
        protocol.connectionLost('because of an error')

    #-----------------------------------------------------------------------#
    # Test Modbus UDP Server
    #-----------------------------------------------------------------------#
    def testUdpServerInitialize(self):
        protocol = ModbusUdpProtocol(store=None)
        self.assertEqual(protocol.control.Identity.VendorName, '')

        identity = ModbusDeviceIdentification(info={0x00: 'VendorName'})
        protocol = ModbusUdpProtocol(store=None, identity=identity)
        self.assertEqual(protocol.control.Identity.VendorName, 'VendorName')

    #-----------------------------------------------------------------------#
    # Test Modbus Server Startups
    #-----------------------------------------------------------------------#

    def testTcpServerStartup(self):
        ''' Test that the modbus tcp async server starts correctly '''
        with patch('twisted.internet.reactor') as mock_reactor:
            StartTcpServer(context=None, console=True)
            self.assertEqual(mock_reactor.listenTCP.call_count, 2)
            self.assertEqual(mock_reactor.run.call_count, 1)

    def testUdpServerStartup(self):
        ''' Test that the modbus udp async server starts correctly '''
        with patch('twisted.internet.reactor') as mock_reactor:
            StartUdpServer(context=None)
            self.assertEqual(mock_reactor.listenUDP.call_count, 1)
            self.assertEqual(mock_reactor.run.call_count, 1)

    def testSerialServerStartup(self):
        ''' Test that the modbus serial async server starts correctly '''
        with patch('twisted.internet.reactor') as mock_reactor:
            StartSerialServer(context=None, port='/dev/ptmx')
            self.assertEqual(mock_reactor.run.call_count, 1)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_server_context
#!/usr/bin/env python
import unittest
from pymodbus.datastore import *
from pymodbus.exceptions import *

class ModbusServerSingleContextTest(unittest.TestCase):
    ''' This is the unittest for the pymodbus.datastore.ModbusServerContext
    using a single slave context.
    '''

    def setUp(self):
        ''' Sets up the test environment '''
        self.slave = ModbusSlaveContext()
        self.context = ModbusServerContext(slaves=self.slave, single=True)

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.context

    def testSingleContextGets(self):
        ''' Test getting on a single context '''
        for id in xrange(0, 0xff):
            self.assertEqual(self.slave, self.context[id])

    def testSingleContextDeletes(self):
        ''' Test removing on multiple context '''
        def _test():
            del self.context[0x00]
        self.assertRaises(ParameterException, _test)

    def testSingleContextIter(self):
        ''' Test iterating over a single context '''
        expected = (0, self.slave)
        for slave in self.context:
            self.assertEqual(slave, expected)

    def testSingleContextDefault(self):
        ''' Test that the single context default values work '''
        self.context = ModbusServerContext()
        slave = self.context[0x00]
        self.assertEqual(slave, {})

    def testSingleContextSet(self):
        ''' Test a setting a single slave context '''
        slave = ModbusSlaveContext()
        self.context[0x00] = slave
        actual = self.context[0x00]
        self.assertEqual(slave, actual)

class ModbusServerMultipleContextTest(unittest.TestCase):
    ''' This is the unittest for the pymodbus.datastore.ModbusServerContext
    using multiple slave contexts.
    '''

    def setUp(self):
        ''' Sets up the test environment '''
        self.slaves  = dict((id, ModbusSlaveContext()) for id in xrange(10))
        self.context = ModbusServerContext(slaves=self.slaves, single=False)

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.context

    def testMultipleContextGets(self):
        ''' Test getting on multiple context '''
        for id in xrange(0, 10):
            self.assertEqual(self.slaves[id], self.context[id])

    def testMultipleContextDeletes(self):
        ''' Test removing on multiple context '''
        del self.context[0x00]
        self.assertRaises(ParameterException, lambda: self.context[0x00])

    def testMultipleContextIter(self):
        ''' Test iterating over multiple context '''
        for id, slave in self.context:
            self.assertEqual(slave, self.slaves[id])
            self.assertTrue(id in self.context)

    def testMultipleContextDefault(self):
        ''' Test that the multiple context default values work '''
        self.context = ModbusServerContext(single=False)
        self.assertRaises(ParameterException, lambda: self.context[0x00])

    def testMultipleContextSet(self):
        ''' Test a setting multiple slave contexts '''
        slaves = dict((id, ModbusSlaveContext()) for id in xrange(10))
        for id, slave in slaves.iteritems():
            self.context[id] = slave
        for id, slave in slaves.iteritems():
            actual = self.context[id]
            self.assertEqual(slave, actual)

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_server_sync
#!/usr/bin/env python
import unittest
from mock import patch, Mock
import SocketServer
import serial
import socket

from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server.sync import ModbusBaseRequestHandler
from pymodbus.server.sync import ModbusSingleRequestHandler
from pymodbus.server.sync import ModbusConnectedRequestHandler
from pymodbus.server.sync import ModbusDisconnectedRequestHandler
from pymodbus.server.sync import ModbusTcpServer, ModbusUdpServer, ModbusSerialServer
from pymodbus.server.sync import StartTcpServer, StartUdpServer, StartSerialServer
from pymodbus.exceptions import NotImplementedException
from pymodbus.bit_read_message import ReadCoilsRequest, ReadCoilsResponse

#---------------------------------------------------------------------------#
# Mock Classes
#---------------------------------------------------------------------------#
class MockServer(object):
    def __init__(self):
        self.framer  = lambda _: "framer"
        self.decoder = "decoder"
        self.threads = []
        self.context = {}

#---------------------------------------------------------------------------#
# Fixture
#---------------------------------------------------------------------------#
class SynchronousServerTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.server.sync module
    '''

    #-----------------------------------------------------------------------#
    # Test Base Request Handler
    #-----------------------------------------------------------------------#

    def testBaseHandlerUndefinedMethods(self):
        ''' Test the base handler undefined methods'''
        handler = SocketServer.BaseRequestHandler(None, None, None)
        handler.__class__ = ModbusBaseRequestHandler
        self.assertRaises(NotImplementedException, lambda: handler.send(None))
        self.assertRaises(NotImplementedException, lambda: handler.handle())

    def testBaseHandlerMethods(self):
        ''' Test the base class for all the clients '''
        request = ReadCoilsRequest(1, 1)
        address = ('server', 12345)
        server  = MockServer()
        
        with patch.object(ModbusBaseRequestHandler, 'handle') as mock_handle:
            with patch.object(ModbusBaseRequestHandler, 'send') as mock_send:
                mock_handle.return_value = True
                mock_send.return_value = True
                handler = ModbusBaseRequestHandler(request, address, server)
                self.assertEqual(handler.running, True)
                self.assertEqual(handler.framer, 'framer')

                handler.execute(request)
                self.assertEqual(mock_send.call_count, 1)

                server.context[0x00] = object()
                handler.execute(request)
                self.assertEqual(mock_send.call_count, 2)

    #-----------------------------------------------------------------------#
    # Test Single Request Handler
    #-----------------------------------------------------------------------#
    def testModbusSingleRequestHandlerSend(self):
        handler = SocketServer.BaseRequestHandler(None, None, None)
        handler.__class__ = ModbusSingleRequestHandler
        handler.framer  = Mock()
        handler.framer.buildPacket.return_value = "message"
        handler.request = Mock()
        request = ReadCoilsResponse([1])
        handler.send(request)
        self.assertEqual(handler.request.send.call_count, 1)

        request.should_respond = False
        handler.send(request)
        self.assertEqual(handler.request.send.call_count, 1)

    def testModbusSingleRequestHandlerHandle(self):
        handler = SocketServer.BaseRequestHandler(None, None, None)
        handler.__class__ = ModbusSingleRequestHandler
        handler.framer  = Mock()
        handler.framer.buildPacket.return_value = "message"
        handler.request = Mock()
        handler.request.recv.return_value = "\x12\x34"

        # exit if we are not running
        handler.running = False
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 0)

        # run forever if we are running
        def _callback1(a, b):
            handler.running = False # stop infinite loop
        handler.framer.processIncomingPacket.side_effect = _callback1
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 1)

        # exceptions are simply ignored
        def _callback2(a, b):
            if handler.framer.processIncomingPacket.call_count == 2:
                raise Exception("example exception")
            else: handler.running = False # stop infinite loop
        handler.framer.processIncomingPacket.side_effect = _callback2
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 3)

    #-----------------------------------------------------------------------#
    # Test Connected Request Handler
    #-----------------------------------------------------------------------#
    def testModbusConnectedRequestHandlerSend(self):
        handler = SocketServer.BaseRequestHandler(None, None, None)
        handler.__class__ = ModbusConnectedRequestHandler
        handler.framer  = Mock()
        handler.framer.buildPacket.return_value = "message"
        handler.request = Mock()
        request = ReadCoilsResponse([1])
        handler.send(request)
        self.assertEqual(handler.request.send.call_count, 1)

        request.should_respond = False
        handler.send(request)
        self.assertEqual(handler.request.send.call_count, 1)

    def testModbusConnectedRequestHandlerHandle(self):
        handler = SocketServer.BaseRequestHandler(None, None, None)
        handler.__class__ = ModbusConnectedRequestHandler
        handler.framer  = Mock()
        handler.framer.buildPacket.return_value = "message"
        handler.request = Mock()
        handler.request.recv.return_value = "\x12\x34"

        # exit if we are not running
        handler.running = False
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 0)

        # run forever if we are running
        def _callback(a, b):
            handler.running = False # stop infinite loop
        handler.framer.processIncomingPacket.side_effect = _callback
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 1)

        # socket errors cause the client to disconnect
        handler.framer.processIncomingPacket.side_effect = socket.error()
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 2)

        # every other exception causes the client to disconnect
        handler.framer.processIncomingPacket.side_effect = Exception()
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 3)

        # receiving no data causes the client to disconnect
        handler.request.recv.return_value = None
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 3)

    #-----------------------------------------------------------------------#
    # Test Disconnected Request Handler
    #-----------------------------------------------------------------------#
    def testModbusDisconnectedRequestHandlerSend(self):
        handler = SocketServer.BaseRequestHandler(None, None, None)
        handler.__class__ = ModbusDisconnectedRequestHandler
        handler.framer  = Mock()
        handler.framer.buildPacket.return_value = "message"
        handler.request = Mock()
        request = ReadCoilsResponse([1])
        handler.send(request)
        self.assertEqual(handler.request.sendto.call_count, 1)

        request.should_respond = False
        handler.send(request)
        self.assertEqual(handler.request.sendto.call_count, 1)

    def testModbusDisconnectedRequestHandlerHandle(self):
        handler = SocketServer.BaseRequestHandler(None, None, None)
        handler.__class__ = ModbusDisconnectedRequestHandler
        handler.framer  = Mock()
        handler.framer.buildPacket.return_value = "message"
        handler.request = ("\x12\x34", handler.request)

        # exit if we are not running
        handler.running = False
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 0)

        # run forever if we are running
        def _callback(a, b):
            handler.running = False # stop infinite loop
        handler.framer.processIncomingPacket.side_effect = _callback
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 1)

        # socket errors cause the client to disconnect
        handler.request = ("\x12\x34", handler.request)
        handler.framer.processIncomingPacket.side_effect = socket.error()
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 2)

        # every other exception causes the client to disconnect
        handler.request = ("\x12\x34", handler.request)
        handler.framer.processIncomingPacket.side_effect = Exception()
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 3)

        # receiving no data causes the client to disconnect
        handler.request = (None, handler.request)
        handler.running = True
        handler.handle()
        self.assertEqual(handler.framer.processIncomingPacket.call_count, 3)

    #-----------------------------------------------------------------------#
    # Test TCP Server
    #-----------------------------------------------------------------------#
    def testTcpServerClose(self):
        ''' test that the synchronous TCP server closes correctly '''
        with patch.object(socket.socket, 'bind') as mock_socket:
            identity = ModbusDeviceIdentification(info={0x00: 'VendorName'})
            server = ModbusTcpServer(context=None, identity=identity)
            server.threads.append(Mock(**{'running': True}))
            server.server_close()
            self.assertEqual(server.control.Identity.VendorName, 'VendorName')
            self.assertFalse(server.threads[0].running)

    def testTcpServerProcess(self):
        ''' test that the synchronous TCP server processes requests '''
        with patch('SocketServer.ThreadingTCPServer') as mock_server:
            server = ModbusTcpServer(None)
            server.process_request('request', 'client')
            self.assertTrue(mock_server.process_request.called)

    #-----------------------------------------------------------------------#
    # Test UDP Server
    #-----------------------------------------------------------------------#
    def testUdpServerClose(self):
        ''' test that the synchronous UDP server closes correctly '''
        with patch.object(socket.socket, 'bind') as mock_socket:
            identity = ModbusDeviceIdentification(info={0x00: 'VendorName'})
            server = ModbusUdpServer(context=None, identity=identity)
            server.threads.append(Mock(**{'running': True}))
            server.server_close()
            self.assertEqual(server.control.Identity.VendorName, 'VendorName')
            self.assertFalse(server.threads[0].running)

    def testUdpServerProcess(self):
        ''' test that the synchronous UDP server processes requests '''
        with patch('SocketServer.ThreadingUDPServer') as mock_server:
            server = ModbusUdpServer(None)
            request = ('data', 'socket')
            server.process_request(request, 'client')
            self.assertTrue(mock_server.process_request.called)

    #-----------------------------------------------------------------------#
    # Test Serial Server
    #-----------------------------------------------------------------------#
    def testSerialServerConnect(self):
        with patch.object(serial, 'Serial') as mock_serial:
            mock_serial.return_value = "socket"
            identity = ModbusDeviceIdentification(info={0x00: 'VendorName'})
            server = ModbusSerialServer(context=None, identity=identity)
            self.assertEqual(server.socket, "socket")
            self.assertEqual(server.control.Identity.VendorName, 'VendorName')

            server._connect()
            self.assertEqual(server.socket, "socket")

        with patch.object(serial, 'Serial') as mock_serial:
            mock_serial.side_effect = serial.SerialException()
            server = ModbusSerialServer(None)
            self.assertEqual(server.socket, None)

    def testSerialServerServeForever(self):
        ''' test that the synchronous serial server closes correctly '''
        with patch.object(serial, 'Serial') as mock_serial:
            with patch('pymodbus.server.sync.ModbusSingleRequestHandler') as mock_handler:
                server = ModbusSerialServer(None)
                instance = mock_handler.return_value
                instance.handle.side_effect = server.server_close
                server.serve_forever()
                instance.handle.assert_any_call()

    def testSerialServerClose(self):
        ''' test that the synchronous serial server closes correctly '''
        with patch.object(serial, 'Serial') as mock_serial:
            instance = mock_serial.return_value
            server = ModbusSerialServer(None)
            server.server_close()
            instance.close.assert_any_call()

    #-----------------------------------------------------------------------#
    # Test Synchronous Factories
    #-----------------------------------------------------------------------#
    def testStartTcpServer(self):
        ''' Test the tcp server starting factory '''
        with patch.object(ModbusTcpServer, 'serve_forever') as mock_server:
            with patch.object(SocketServer.TCPServer, 'server_bind') as mock_binder:
                StartTcpServer()

    def testStartUdpServer(self):
        ''' Test the udp server starting factory '''
        with patch.object(ModbusUdpServer, 'serve_forever') as mock_server:
            with patch.object(SocketServer.UDPServer, 'server_bind') as mock_binder:
                StartUdpServer()

    def testStartSerialServer(self):
        ''' Test the serial server starting factory '''
        with patch.object(ModbusSerialServer, 'serve_forever') as mock_server:
            StartSerialServer()

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_transaction
#!/usr/bin/env python
import unittest
from binascii import a2b_hex
from pymodbus.pdu import *
from pymodbus.transaction import *
from pymodbus.factory import ServerDecoder

class ModbusTransactionTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus.transaction module
    '''

    #---------------------------------------------------------------------------#
    # Test Construction
    #---------------------------------------------------------------------------#
    def setUp(self):
        ''' Sets up the test environment '''
        self.client   = None
        self.decoder  = ServerDecoder()
        self._tcp     = ModbusSocketFramer(decoder=self.decoder)
        self._rtu     = ModbusRtuFramer(decoder=self.decoder)
        self._ascii   = ModbusAsciiFramer(decoder=self.decoder)
        self._binary  = ModbusBinaryFramer(decoder=self.decoder)
        self._manager = DictTransactionManager(self.client)
        self._queue_manager = FifoTransactionManager(self.client)

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self._manager
        del self._tcp
        del self._rtu
        del self._ascii

    #---------------------------------------------------------------------------# 
    # Dictionary based transaction manager
    #---------------------------------------------------------------------------# 
    def testDictTransactionManagerTID(self):
        ''' Test the dict transaction manager TID '''
        for tid in range(1, self._manager.getNextTID() + 10):
            self.assertEqual(tid+1, self._manager.getNextTID())
        self._manager.reset()
        self.assertEqual(1, self._manager.getNextTID())

    def testGetDictTransactionManagerTransaction(self):
        ''' Test the dict transaction manager '''
        class Request: pass
        self._manager.reset()
        handle = Request()
        handle.transaction_id = self._manager.getNextTID()
        handle.message = "testing"
        self._manager.addTransaction(handle)
        result = self._manager.getTransaction(handle.transaction_id)
        self.assertEqual(handle.message, result.message)

    def testDeleteDictTransactionManagerTransaction(self):
        ''' Test the dict transaction manager '''
        class Request: pass
        self._manager.reset()
        handle = Request()
        handle.transaction_id = self._manager.getNextTID()
        handle.message = "testing"

        self._manager.addTransaction(handle)
        self._manager.delTransaction(handle.transaction_id)
        self.assertEqual(None, self._manager.getTransaction(handle.transaction_id))

    #---------------------------------------------------------------------------# 
    # Queue based transaction manager
    #---------------------------------------------------------------------------# 
    def testFifoTransactionManagerTID(self):
        ''' Test the fifo transaction manager TID '''
        for tid in range(1, self._queue_manager.getNextTID() + 10):
            self.assertEqual(tid+1, self._queue_manager.getNextTID())
        self._queue_manager.reset()
        self.assertEqual(1, self._queue_manager.getNextTID())

    def testGetFifoTransactionManagerTransaction(self):
        ''' Test the fifo transaction manager '''
        class Request: pass
        self._queue_manager.reset()
        handle = Request()
        handle.transaction_id = self._queue_manager.getNextTID()
        handle.message = "testing"
        self._queue_manager.addTransaction(handle)
        result = self._queue_manager.getTransaction(handle.transaction_id)
        self.assertEqual(handle.message, result.message)

    def testDeleteFifoTransactionManagerTransaction(self):
        ''' Test the fifo transaction manager '''
        class Request: pass
        self._queue_manager.reset()
        handle = Request()
        handle.transaction_id = self._queue_manager.getNextTID()
        handle.message = "testing"

        self._queue_manager.addTransaction(handle)
        self._queue_manager.delTransaction(handle.transaction_id)
        self.assertEqual(None, self._queue_manager.getTransaction(handle.transaction_id))

    #---------------------------------------------------------------------------# 
    # TCP tests
    #---------------------------------------------------------------------------#
    def testTCPFramerTransactionReady(self):
        ''' Test a tcp frame transaction '''
        msg = "\x00\x01\x12\x34\x00\x04\xff\x02\x12\x34"
        self.assertFalse(self._tcp.isFrameReady())
        self.assertFalse(self._tcp.checkFrame())
        self._tcp.addToFrame(msg)
        self.assertTrue(self._tcp.isFrameReady())
        self.assertTrue(self._tcp.checkFrame())
        self._tcp.advanceFrame()
        self.assertFalse(self._tcp.isFrameReady())
        self.assertFalse(self._tcp.checkFrame())
        self.assertEqual('', self._ascii.getFrame())

    def testTCPFramerTransactionFull(self):
        ''' Test a full tcp frame transaction '''
        msg = "\x00\x01\x12\x34\x00\x04\xff\x02\x12\x34"
        self._tcp.addToFrame(msg)
        self.assertTrue(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual(msg[7:], result)
        self._tcp.advanceFrame()

    def testTCPFramerTransactionHalf(self):
        ''' Test a half completed tcp frame transaction '''
        msg1 = "\x00\x01\x12\x34\x00"
        msg2 = "\x04\xff\x02\x12\x34"
        self._tcp.addToFrame(msg1)
        self.assertFalse(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual('', result)
        self._tcp.addToFrame(msg2)
        self.assertTrue(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual(msg2[2:], result)
        self._tcp.advanceFrame()

    def testTCPFramerTransactionHalf2(self):
        ''' Test a half completed tcp frame transaction '''
        msg1 = "\x00\x01\x12\x34\x00\x04\xff"
        msg2 = "\x02\x12\x34"
        self._tcp.addToFrame(msg1)
        self.assertFalse(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual('', result)
        self._tcp.addToFrame(msg2)
        self.assertTrue(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual(msg2, result)
        self._tcp.advanceFrame()

    def testTCPFramerTransactionHalf3(self):
        ''' Test a half completed tcp frame transaction '''
        msg1 = "\x00\x01\x12\x34\x00\x04\xff\x02\x12"
        msg2 = "\x34"
        self._tcp.addToFrame(msg1)
        self.assertFalse(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual(msg1[7:], result)
        self._tcp.addToFrame(msg2)
        self.assertTrue(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual(msg1[7:] + msg2, result)
        self._tcp.advanceFrame()

    def testTCPFramerTransactionShort(self):
        ''' Test that we can get back on track after an invalid message '''
        msg1 = "\x99\x99\x99\x99\x00\x01\x00\x01"
        msg2 = "\x00\x01\x12\x34\x00\x04\xff\x02\x12\x34"
        self._tcp.addToFrame(msg1)
        self.assertFalse(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual('', result)
        self._tcp.advanceFrame()
        self._tcp.addToFrame(msg2)
        self.assertEqual(10, len(self._tcp._ModbusSocketFramer__buffer))
        self.assertTrue(self._tcp.checkFrame())
        result = self._tcp.getFrame()
        self.assertEqual(msg2[7:], result)
        self._tcp.advanceFrame()

    def testTCPFramerPopulate(self):
        ''' Test a tcp frame packet build '''
        expected = ModbusRequest()
        expected.transaction_id = 0x0001
        expected.protocol_id    = 0x1234
        expected.unit_id        = 0xff
        msg = "\x00\x01\x12\x34\x00\x04\xff\x02\x12\x34"
        self._tcp.addToFrame(msg)
        self.assertTrue(self._tcp.checkFrame())
        actual = ModbusRequest()
        self._tcp.populateResult(actual)
        for name in ['transaction_id', 'protocol_id', 'unit_id']:
            self.assertEqual(getattr(expected, name), getattr(actual, name))
        self._tcp.advanceFrame()

    def testTCPFramerPacket(self):
        ''' Test a tcp frame packet build '''
        old_encode = ModbusRequest.encode
        ModbusRequest.encode = lambda self: ''
        message = ModbusRequest()
        message.transaction_id = 0x0001
        message.protocol_id    = 0x1234
        message.unit_id        = 0xff
        message.function_code  = 0x01
        expected = "\x00\x01\x12\x34\x00\x02\xff\x01"
        actual = self._tcp.buildPacket(message)
        self.assertEqual(expected, actual)
        ModbusRequest.encode = old_encode

    #---------------------------------------------------------------------------#
    # RTU tests
    #---------------------------------------------------------------------------#
    def testRTUFramerTransactionReady(self):
        ''' Test if the checks for a complete frame work '''
        self.assertFalse(self._rtu.isFrameReady())

        msg_parts = ["\x00\x01\x00", "\x00\x00\x01\xfc\x1b"]
        self._rtu.addToFrame(msg_parts[0])
        self.assertTrue(self._rtu.isFrameReady())
        self.assertFalse(self._rtu.checkFrame())

        self._rtu.addToFrame(msg_parts[1])
        self.assertTrue(self._rtu.isFrameReady())
        self.assertTrue(self._rtu.checkFrame())

    def testRTUFramerTransactionFull(self):
        ''' Test a full rtu frame transaction '''
        msg = "\x00\x01\x00\x00\x00\x01\xfc\x1b"
        stripped_msg = msg[1:-2]
        self._rtu.addToFrame(msg)
        self.assertTrue(self._rtu.checkFrame())
        result = self._rtu.getFrame()
        self.assertEqual(stripped_msg, result)
        self._rtu.advanceFrame()

    def testRTUFramerTransactionHalf(self):
        ''' Test a half completed rtu frame transaction '''
        msg_parts = ["\x00\x01\x00", "\x00\x00\x01\xfc\x1b"]
        stripped_msg = "".join(msg_parts)[1:-2]
        self._rtu.addToFrame(msg_parts[0])
        self.assertFalse(self._rtu.checkFrame())
        self._rtu.addToFrame(msg_parts[1])
        self.assertTrue(self._rtu.isFrameReady())
        self.assertTrue(self._rtu.checkFrame())
        result = self._rtu.getFrame()
        self.assertEqual(stripped_msg, result)
        self._rtu.advanceFrame()

    def testRTUFramerPopulate(self):
        ''' Test a rtu frame packet build '''
        request = ModbusRequest()
        msg = "\x00\x01\x00\x00\x00\x01\xfc\x1b"
        self._rtu.addToFrame(msg)
        self._rtu.populateHeader()
        self._rtu.populateResult(request)

        header_dict = self._rtu._ModbusRtuFramer__header
        self.assertEqual(len(msg), header_dict['len'])
        self.assertEqual(ord(msg[0]), header_dict['uid'])
        self.assertEqual(msg[-2:], header_dict['crc'])

        self.assertEqual(0x00, request.unit_id)

    def testRTUFramerPacket(self):
        ''' Test a rtu frame packet build '''
        old_encode = ModbusRequest.encode
        ModbusRequest.encode = lambda self: ''
        message = ModbusRequest()
        message.unit_id        = 0xff
        message.function_code  = 0x01
        expected = "\xff\x01\x81\x80" # only header + CRC - no data
        actual = self._rtu.buildPacket(message)
        self.assertEqual(expected, actual)
        ModbusRequest.encode = old_encode

    def testRTUDecodeException(self):
        ''' Test that the RTU framer can decode errors '''
        message = "\x00\x90\x02\x9c\x01"
        actual = self._rtu.addToFrame(message)
        result = self._rtu.checkFrame()
        self.assertTrue(result)

    #---------------------------------------------------------------------------#
    # ASCII tests
    #---------------------------------------------------------------------------#
    def testASCIIFramerTransactionReady(self):
        ''' Test a ascii frame transaction '''
        msg = ':F7031389000A60\r\n'
        self.assertFalse(self._ascii.isFrameReady())
        self.assertFalse(self._ascii.checkFrame())
        self._ascii.addToFrame(msg)
        self.assertTrue(self._ascii.isFrameReady())
        self.assertTrue(self._ascii.checkFrame())
        self._ascii.advanceFrame()
        self.assertFalse(self._ascii.isFrameReady())
        self.assertFalse(self._ascii.checkFrame())
        self.assertEqual('', self._ascii.getFrame())

    def testASCIIFramerTransactionFull(self):
        ''' Test a full ascii frame transaction '''
        msg = 'sss:F7031389000A60\r\n'
        pack = a2b_hex(msg[6:-4])
        self._ascii.addToFrame(msg)
        self.assertTrue(self._ascii.checkFrame())
        result = self._ascii.getFrame()
        self.assertEqual(pack, result)
        self._ascii.advanceFrame()

    def testASCIIFramerTransactionHalf(self):
        ''' Test a half completed ascii frame transaction '''
        msg1 = 'sss:F7031389'
        msg2 = '000A60\r\n'
        pack = a2b_hex(msg1[6:] + msg2[:-4])
        self._ascii.addToFrame(msg1)
        self.assertFalse(self._ascii.checkFrame())
        result = self._ascii.getFrame()
        self.assertEqual('', result)
        self._ascii.addToFrame(msg2)
        self.assertTrue(self._ascii.checkFrame())
        result = self._ascii.getFrame()
        self.assertEqual(pack, result)
        self._ascii.advanceFrame()

    def testASCIIFramerPopulate(self):
        ''' Test a ascii frame packet build '''
        request = ModbusRequest()
        self._ascii.populateResult(request)
        self.assertEqual(0x00, request.unit_id)

    def testASCIIFramerPacket(self):
        ''' Test a ascii frame packet build '''
        old_encode = ModbusRequest.encode
        ModbusRequest.encode = lambda self: ''
        message = ModbusRequest()
        message.unit_id        = 0xff
        message.function_code  = 0x01
        expected = ":FF0100\r\n"
        actual = self._ascii.buildPacket(message)
        self.assertEqual(expected, actual)
        ModbusRequest.encode = old_encode

    #---------------------------------------------------------------------------#
    # Binary tests
    #---------------------------------------------------------------------------#
    def testBinaryFramerTransactionReady(self):
        ''' Test a binary frame transaction '''
        msg  = '\x7b\x01\x03\x00\x00\x00\x05\x85\xC9\x7d'
        self.assertFalse(self._binary.isFrameReady())
        self.assertFalse(self._binary.checkFrame())
        self._binary.addToFrame(msg)
        self.assertTrue(self._binary.isFrameReady())
        self.assertTrue(self._binary.checkFrame())
        self._binary.advanceFrame()
        self.assertFalse(self._binary.isFrameReady())
        self.assertFalse(self._binary.checkFrame())
        self.assertEqual('', self._binary.getFrame())

    def testBinaryFramerTransactionFull(self):
        ''' Test a full binary frame transaction '''
        msg  = '\x7b\x01\x03\x00\x00\x00\x05\x85\xC9\x7d'
        pack = msg[3:-3]
        self._binary.addToFrame(msg)
        self.assertTrue(self._binary.checkFrame())
        result = self._binary.getFrame()
        self.assertEqual(pack, result)
        self._binary.advanceFrame()

    def testBinaryFramerTransactionHalf(self):
        ''' Test a half completed binary frame transaction '''
        msg1 = '\x7b\x01\x03\x00'
        msg2 = '\x00\x00\x05\x85\xC9\x7d'
        pack = msg1[3:] + msg2[:-3]
        self._binary.addToFrame(msg1)
        self.assertFalse(self._binary.checkFrame())
        result = self._binary.getFrame()
        self.assertEqual('', result)
        self._binary.addToFrame(msg2)
        self.assertTrue(self._binary.checkFrame())
        result = self._binary.getFrame()
        self.assertEqual(pack, result)
        self._binary.advanceFrame()

    def testBinaryFramerPopulate(self):
        ''' Test a binary frame packet build '''
        request = ModbusRequest()
        self._binary.populateResult(request)
        self.assertEqual(0x00, request.unit_id)

    def testBinaryFramerPacket(self):
        ''' Test a binary frame packet build '''
        old_encode = ModbusRequest.encode
        ModbusRequest.encode = lambda self: ''
        message = ModbusRequest()
        message.unit_id        = 0xff
        message.function_code  = 0x01
        expected = '\x7b\xff\x01\x81\x80\x7d'
        actual = self._binary.buildPacket(message)
        self.assertEqual(expected, actual)
        ModbusRequest.encode = old_encode

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utilities
#!/usr/bin/env python
import unittest
import struct
from pymodbus.utilities import pack_bitstring, unpack_bitstring
from pymodbus.utilities import checkCRC, checkLRC
from pymodbus.utilities import dict_property, default

_test_master = {4 : 'd'}
class DictPropertyTester(object):
    def __init__(self):
        self.test   = {1 : 'a'}
        self._test  = {2 : 'b'}
        self.__test = {3 : 'c'}

    l1 = dict_property(lambda s: s.test, 1)
    l2 = dict_property(lambda s: s._test, 2)
    l3 = dict_property(lambda s: s.__test, 3)
    s1 = dict_property('test', 1)
    s2 = dict_property('_test', 2)
    g1 = dict_property(_test_master, 4)


class SimpleUtilityTest(unittest.TestCase):
    '''
    This is the unittest for the pymod.utilities module
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        self.data = struct.pack('>HHHH', 0x1234, 0x2345, 0x3456, 0x4567)
        self.string = "test the computation"
        self.bits = [True, False, True, False, True, False, True, False]

    def tearDown(self):
        ''' Cleans up the test environment '''
        del self.bits
        del self.string

    def testDictProperty(self):
        ''' Test all string <=> bit packing functions '''
        d = DictPropertyTester()
        self.assertEqual(d.l1, 'a')
        self.assertEqual(d.l2, 'b')
        self.assertEqual(d.l3, 'c')
        self.assertEqual(d.s1, 'a')
        self.assertEqual(d.s2, 'b')
        self.assertEqual(d.g1, 'd')

        for store in 'l1 l2 l3 s1 s2 g1'.split(' '):
            setattr(d, store, 'x')

        self.assertEqual(d.l1, 'x')
        self.assertEqual(d.l2, 'x')
        self.assertEqual(d.l3, 'x')
        self.assertEqual(d.s1, 'x')
        self.assertEqual(d.s2, 'x')
        self.assertEqual(d.g1, 'x')

    def testDefaultValue(self):
        ''' Test all string <=> bit packing functions '''
        self.assertEqual(default(1), 0)
        self.assertEqual(default(1.1), 0.0)
        self.assertEqual(default(1+1j), 0j)
        self.assertEqual(default('string'), '')
        self.assertEqual(default([1,2,3]), [])
        self.assertEqual(default({1:1}), {})
        self.assertEqual(default(True), False)

    def testBitPacking(self):
        ''' Test all string <=> bit packing functions '''
        self.assertEqual(unpack_bitstring('\x55'), self.bits)
        self.assertEqual(pack_bitstring(self.bits), '\x55')

    def testLongitudinalRedundancyCheck(self):
        ''' Test the longitudinal redundancy check code '''
        self.assertTrue(checkLRC(self.data, 0x1c))
        self.assertTrue(checkLRC(self.string, 0x0c))

    def testCyclicRedundancyCheck(self):
        ''' Test the cyclic redundancy check code '''
        self.assertTrue(checkCRC(self.data, 0xe2db))
        self.assertTrue(checkCRC(self.string, 0x889e))

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_version
#!/usr/bin/env python
import unittest
from pymodbus.version import Version

class ModbusVersionTest(unittest.TestCase):
    '''
    This is the unittest for the pymodbus._version code
    '''

    def setUp(self):
        ''' Initializes the test environment '''
        pass

    def tearDown(self):
        ''' Cleans up the test environment '''
        pass

    def testVersionClass(self):
        version = Version('test', 1,2,3)
        self.assertEqual(version.short(), '1.2.3')
        self.assertEqual(str(version), '[test, version 1.2.3]')

#---------------------------------------------------------------------------#
# Main
#---------------------------------------------------------------------------#
if __name__ == "__main__":
    unittest.main()

########NEW FILE########
