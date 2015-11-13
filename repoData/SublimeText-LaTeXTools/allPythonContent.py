__FILENAME__ = pdfBuilder
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
	_ST3 = False
else:
	_ST3 = True

import os.path

DEBUG = False


#---------------------------------------------------------------
# PdfBuilder class
#
# Build engines subclass PdfBuilder
# NOTE: this will have to be moved eventually.
#

class PdfBuilder(object):
	"""Base class for build engines"""

	# Configure parameters here
	#
	# tex_root: the full path to the tex root file
	# output: object in main thread responsible for writing to the output panel
	# builder_settings : a dictionary containing the "builder_settings" from LaTeXTools.sublime-settings
	# platform_settings : a dictionary containing the "platform_settings" from LaTeXTools.sublime-settings
	#
	# E.g.: self.path = prefs["path"]
	#
	# Your __init__ method *must* call this (via super) to ensure that
	# tex_root is properly split into the root tex file's directory,
	# its base name, and extension, etc.

	def __init__(self, tex_root, output, builder_settings, platform_settings):
		self.tex_root = tex_root
		self.tex_dir, self.tex_name = os.path.split(tex_root)
		self.base_name, self.tex_ext = os.path.splitext(self.tex_name)
		self.output_callable = output
		self.out = ""
		self.builder_settings = builder_settings
		self.platform_settings = platform_settings

	# Send to callable object
	# Usually no need to override
	def display(self, data):
		self.output_callable(data)

	# Save command output
	# Usually no need to override
	def set_output(self, out):
		if DEBUG:
			print("Setting out")
			print(out)
		self.out = out

	# This is where the real work is done. This generator must yield (cmd, msg) tuples,
	# as a function of the parameters and the output from previous commands (via send()).
	# "cmd" is the command to be run, as an array
	# "msg" is the message to be displayed (or None)
	# As of now, this function *must* yield at least *one* tuple.
	# If no command must be run, just yield ("","")
	# Remember that we are now in the root file's directory
	def commands(self):
		pass

	# Clean up after ourselves
	# Only the build system knows what to delete for sure, so give this option
	# Return True if we actually handle this, False if not
	#
	# NOTE: problem. Either we make the builder class persistent, or we have to
	# pass the tex root again. Need to think about this
	def cleantemps(self):
		return False


########NEW FILE########
__FILENAME__ = scriptBuilder
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
	_ST3 = False
else:
	_ST3 = True

from pdfBuilder import PdfBuilder
import re
import os, os.path
import codecs

DEBUG = False


#----------------------------------------------------------------
# ScriptBuilder class
#
# Launch a user-specified script
# STILL NOT FUNCTIONAL!!!
#
class ScriptBuilder(PdfBuilder):

	def __init__(self, tex_root, output, builder_settings, platform_settings):
		# Sets the file name parts, plus internal stuff
		super(TraditionalBuilder, self).__init__(tex_root, output, builder_settings, platform_settings) 
		# Now do our own initialization: set our name
		self.name = "Script Builder"
		# Display output?
		self.display_log = builder_settings.get("display_log", False)
		plat = sublime.platform()
		self.cmd = builder_settings[plat]["command"]
		self.env = builder_settings[plat]["env"]


	#
	# Very simple here: we yield a single command
	# Also add environment variables
	#
	def commands(self):
		# Print greeting
		self.display("\n\nScriptBuilder: ")

		# figure out safe way to pass self.env back
		# OK, probably need to modify yield call throughout
		# and pass via Popen. Wait for now

		# pass the base name, without extension
		yield (cmd + [self.base_name], " ".join(cmd) + "... ")

		self.display("done.\n")
		
		# This is for debugging purposes 
		if self.display_log:
			self.display("\nCommand results:\n")
			self.display(self.out)
			self.display("\n\n")	

########NEW FILE########
__FILENAME__ = simpleBuilder
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
	_ST3 = False
else:
	_ST3 = True

import os.path
import re
# This will work because makePDF.py puts the appropriate
# builders directory in sys.path
from pdfBuilder import PdfBuilder

DEBUG = False




#----------------------------------------------------------------
# SimpleBuilder class
#
# Just call a bunch of commands in sequence
# Demonstrate basics
#

class SimpleBuilder(PdfBuilder):

	def __init__(self, tex_root, output, builder_settings, platform_settings):
		# Sets the file name parts, plus internal stuff
		super(SimpleBuilder, self).__init__(tex_root, output, builder_settings, platform_settings) 
		# Now do our own initialization: set our name, see if we want to display output
		self.name = "Simple Builder"
		self.display_log = builder_settings.get("display_log", False)

	def commands(self):
		# Print greeting
		self.display("\n\nSimpleBuilder: ")

		pdflatex = ["pdflatex", "-interaction=nonstopmode", "-synctex=1"]
		bibtex = ["bibtex"]

		# Regex to look for missing citations
		# This works for plain latex; apparently natbib requires special handling
		# TODO: does it work with biblatex?
		citations_rx = re.compile(r"Warning: Citation `.+' on page \d+ undefined")

		# We have commands in our PATH, and are in the same dir as the master file

		# This is for debugging purposes 
		def display_results(n):
			if self.display_log:
				self.display("Command results, run %d:\n" % (n,) )
				self.display(self.out)
				self.display("\n")	

		run = 1
		brun = 0
		yield (pdflatex + [self.base_name], "pdflatex run %d; " % (run, ))
		display_results(run)

		# Check for citations
		# Use search, not match: match looks at the beginning of the string
		# We need to run pdflatex twice after bibtex
		if citations_rx.search(self.out):
			brun = brun + 1
			yield (bibtex + [self.base_name], "bibtex run %d; " % (brun,))
			display_results(1)
			run = run + 1
			yield (pdflatex + [self.base_name], "pdflatex run %d; " % (run, ))
			display_results(run)
			run = run + 1
			yield (pdflatex + [self.base_name], "pdflatex run %d; " % (run, ))
			display_results(run)

		# Apparently natbib needs separate processing
		if "Package natbib Warning: There were undefined citations." in self.out:
			brun = brun + 1
			yield (bibtex + [self.base_name], "bibtex run %d; " % (brun,))
			display_results(2)
			run = run + 1
			yield (pdflatex + [self.base_name], "pdflatex run %d; " % (run, ))
			display_results(run)
			run = run + 1
			yield (pdflatex + [self.base_name], "pdflatex run %d; " % (run, ))
			display_results(run)

		# Check for changed labels
		# Do this at the end, so if there are also citations to resolve,
		# we may save one pdflatex run
		if "Rerun to get cross-references right." in self.out:
			run = run + 1
			yield (pdflatex + [self.base_name], "pdflatex run %d; " % (run, ))
			display_results(run)

		self.display("done.\n")
			








########NEW FILE########
__FILENAME__ = traditionalBuilder
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
	_ST3 = False
else:
	_ST3 = True

from pdfBuilder import PdfBuilder
import sublime_plugin
import re
import os, os.path
import codecs

DEBUG = False

DEFAULT_COMMAND_LATEXMK = ["latexmk", "-cd",
				"-e", "$pdflatex = '%E -interaction=nonstopmode -synctex=1 %S %O'",
				"-f", "-pdf"]

DEFAULT_COMMAND_WINDOWS_MIKTEX = ["texify", 
					"-b", "-p",
					"--tex-option=\"--synctex=1\""]


#----------------------------------------------------------------
# TraditionalBuilder class
#
# Implement existing functionality, more or less
# NOTE: move this to a different file, too
#
class TraditionalBuilder(PdfBuilder):

	def __init__(self, tex_root, output, builder_settings, platform_settings):
		# Sets the file name parts, plus internal stuff
		super(TraditionalBuilder, self).__init__(tex_root, output, builder_settings, platform_settings) 
		# Now do our own initialization: set our name
		self.name = "Traditional Builder"
		# Display output?
		self.display_log = builder_settings.get("display_log", False)
		# Build command, with reasonable defaults
		plat = sublime.platform()
		# Figure out which distro we are using
		try:
			distro = platform_settings["distro"]
		except KeyError: # default to miktex on windows and texlive elsewhere
			if plat == 'windows':
				distro = "miktex"
			else:
				distro = "texlive"
		if distro in ["miktex", ""]:
			default_command = DEFAULT_COMMAND_WINDOWS_MIKTEX
		else: # osx, linux, windows/texlive, everything else really!
			default_command = DEFAULT_COMMAND_LATEXMK
		self.cmd = builder_settings.get("command", default_command)
		# Default tex engine (pdflatex if none specified)
		self.engine = builder_settings.get("program", "pdflatex")
		# Sanity check: if "strange" engine, default to pdflatex (silently...)
		if not(self.engine in ['pdflatex', 'xelatex', 'lualatex']):
			self.engine = 'pdflatex'



	#
	# Very simple here: we yield a single command
	# Only complication is handling custom tex engines
	#
	def commands(self):
		# Print greeting
		self.display("\n\nTraditionalBuilder: ")

		# See if the root file specifies a custom engine
		engine = self.engine
		cmd = self.cmd[:] # Warning! If I omit the [:], cmd points to self.cmd!
		for line in codecs.open(self.tex_root, "r", "UTF-8", "ignore").readlines():
			if not line.startswith('%'):
				break
			else:
				# We have a comment match; check for a TS-program match
				mroot = re.match(r"%\s*!TEX\s+(?:TS-)?program *= *(xelatex|lualatex|pdflatex)\s*$",line)
				if mroot:
					# Sanity checks
					if "texify" == cmd[0]:
						sublime.error_message("Sorry, cannot select engine using a %!TEX program directive on MikTeX.\n")
						yield("", "Could not compile.")
					if not re.match(r"\$pdflatex\s?=\s?'%E", cmd[3]): # fixup blanks (linux)
						sublime.error_message("You are using a custom build command.\n"\
							"Cannot select engine using a %!TEX program directive.\n")
						yield("", "Could not compile.")
					engine = mroot.group(1)
					break
		if engine != self.engine:
			self.display("Engine: " + self.engine + " -> " + engine + ". ")
			
		cmd[3] = cmd[3].replace("%E", engine)

		# texify wants the .tex extension; latexmk doesn't care either way
		yield (cmd + [self.tex_name], "Invoking " + cmd[0] + "... ")

		self.display("done.\n")
		
		# This is for debugging purposes 
		if self.display_log:
			self.display("\nCommand results:\n")
			self.display(self.out)
			self.display("\n\n")	

########NEW FILE########
__FILENAME__ = delete_temp_files
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
	_ST3 = False
	# we are on ST2 and Python 2.X
	import getTeXRoot
else:
	_ST3 = True
	from . import getTeXRoot


import sublime_plugin
import os

class Delete_temp_filesCommand(sublime_plugin.WindowCommand):
	def run(self):
		# Retrieve file and dirname.
		view = self.window.active_view()
		self.file_name = getTeXRoot.get_tex_root(view)
		if not os.path.isfile(self.file_name):
			sublime.error_message(self.file_name + ": file not found.")
			return

		self.tex_base, self.tex_ext = os.path.splitext(self.file_name)


		# Delete the files.
		temp_exts = ['.blg','.bbl','.aux','.log','.brf','.nlo','.out','.dvi','.ps',
			'.lof','.toc','.fls','.fdb_latexmk','.pdfsync','.synctex.gz','.ind','.ilg','.idx']

		for temp_ext in temp_exts:
			file_name_to_del = self.tex_base + temp_ext
			#print file_name_to_del
			if os.path.exists(file_name_to_del):
				#print ' deleted '
				os.remove(file_name_to_del)

		sublime.status_message("Deleted the temp files")
		
########NEW FILE########
__FILENAME__ = getTeXRoot
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
	# we are on ST2 and Python 2.X
	_ST3 = False
else:
	_ST3 = True


import os.path, re
import codecs


# Parse magic comments to retrieve TEX root
# Stops searching for magic comments at first non-comment line of file
# Returns root file or current file or None (if there is no root file,
# and the current buffer is an unnamed unsaved file)

# Contributed by Sam Finn

def get_tex_root(view):
	try:
		root = os.path.abspath(view.settings().get('TEXroot'))
		if os.path.isfile(root):
			print("Main file defined in project settings : " + root)
			return root
	except:
		pass


	texFile = view.file_name()
	root = texFile
	if texFile is None:
		# We are in an unnamed, unsaved file.
		# Read from the buffer instead.
		if view.substr(0) != '%':
			return None
		reg = view.find(r"^%[^\n]*(\n%[^\n]*)*", 0)
		if not reg:
			return None
		line_regs = view.lines(reg)
		lines = map(view.substr, line_regs)
		is_file = False

	else:
		# This works on ST2 and ST3, but does not automatically convert line endings.
		# We should be OK though.
		lines = codecs.open(texFile, "r", "UTF-8")
		is_file = True

	for line in lines:
		if not line.startswith('%'):
			break
		else:
			# We have a comment match; check for a TEX root match
			mroot = re.match(r"%\s*!TEX\s+root *= *(.*(tex|TEX))\s*$",line)
			if mroot:
				# we have a TEX root match 
				# Break the match into path, file and extension
				# Create TEX root file name
				# If there is a TEX root path, use it
				# If the path is not absolute and a src path exists, pre-pend it
				root = mroot.group(1)
				if not os.path.isabs(root) and texFile is not None:
					(texPath, texName) = os.path.split(texFile)
					root = os.path.join(texPath,root)
				root = os.path.normpath(root)
				break

	if is_file: # Not very Pythonic, but works...
		lines.close()

	return root
########NEW FILE########
__FILENAME__ = jumpToPDF
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
	_ST3 = False
	import getTeXRoot
else:
	_ST3 = True
	from . import getTeXRoot


import sublime_plugin, os.path, subprocess, time

# Jump to current line in PDF file
# NOTE: must be called with {"from_keybinding": <boolean>} as arg

class jump_to_pdfCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		# Check prefs for PDF focus and sync
		s = sublime.load_settings("LaTeXTools.sublime-settings")
		prefs_keep_focus = s.get("keep_focus", True)
		keep_focus = self.view.settings().get("keep focus",prefs_keep_focus)
		prefs_forward_sync = s.get("forward_sync", True)
		forward_sync = self.view.settings().get("forward_sync",prefs_forward_sync)

		prefs_lin = s.get("linux")

		# If invoked from keybinding, we sync
		# Rationale: if the user invokes the jump command, s/he wants to see the result of the compilation.
		# If the PDF viewer window is already visible, s/he probably wants to sync, or s/he would have no
		# need to invoke the command. And if it is not visible, the natural way to just bring up the
		# window without syncing is by using the system's window management shortcuts.
		# As for focusing, we honor the toggles / prefs.
		from_keybinding = args["from_keybinding"]
		if from_keybinding:
			forward_sync = True
		print (from_keybinding, keep_focus, forward_sync)

		texFile, texExt = os.path.splitext(self.view.file_name())
		if texExt.upper() != ".TEX":
			sublime.error_message("%s is not a TeX source file: cannot jump." % (os.path.basename(view.fileName()),))
			return
		quotes = "\""
		srcfile = texFile + u'.tex'
		root = getTeXRoot.get_tex_root(self.view)
		print ("!TEX root = ", repr(root) ) # need something better here, but this works.
		rootName, rootExt = os.path.splitext(root)
		pdffile = rootName + u'.pdf'
		(line, col) = self.view.rowcol(self.view.sel()[0].end())
		print ("Jump to: ", line,col)
		# column is actually ignored up to 0.94
		# HACK? It seems we get better results incrementing line
		line += 1

		# Query view settings to see if we need to keep focus or let the PDF viewer grab it
		# By default, we respect settings in Preferences
		

		# platform-specific code:
		plat = sublime_plugin.sys.platform
		if plat == 'darwin':
			options = ["-r","-g"] if keep_focus else ["-r"]		
			if forward_sync:
				subprocess.Popen(["/Applications/Skim.app/Contents/SharedSupport/displayline"] + 
								options + [str(line), pdffile, srcfile])
			else:
				skim = os.path.join(sublime.packages_path(),
								'LaTeXTools', 'skim', 'displayfile')
				subprocess.Popen(['sh', skim] + options + [pdffile])
		elif plat == 'win32':
			# determine if Sumatra is running, launch it if not
			print ("Windows, Calling Sumatra")
			# hide console
			# NO LONGER NEEDED with new Sumatra?
			# startupinfo = subprocess.STARTUPINFO()
			# startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			# tasks = subprocess.Popen(["tasklist"], stdout=subprocess.PIPE,
			# 		startupinfo=startupinfo).communicate()[0]
			# # Popen returns a byte stream, i.e. a single line. So test simply:
			# # Wait! ST3 is stricter. We MUST convert to str
			# tasks_str = tasks.decode('UTF-8') #guess..
			# if "SumatraPDF.exe" not in tasks_str:
			# 	print ("Sumatra not running, launch it")
			# 	self.view.window().run_command("view_pdf")
			# 	time.sleep(0.5) # wait 1/2 seconds so Sumatra comes up
			setfocus = 0 if keep_focus else 1
			# First send an open command forcing reload, or ForwardSearch won't 
			# reload if the file is on a network share
			# command = u'[Open(\"%s\",0,%d,1)]' % (pdffile,setfocus)
			# print (repr(command))
			# self.view.run_command("send_dde",
			# 		{ "service": "SUMATRA", "topic": "control", "command": command})
			# Now send ForwardSearch command if needed

			si = subprocess.STARTUPINFO()
			if setfocus == 0:
				si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
				si.wShowWindow = 4 #constant for SHOWNOACTIVATE

			startCommands = ["SumatraPDF.exe","-reuse-instance"]
			if forward_sync:
				startCommands.append("-forward-search")
				startCommands.append(srcfile)
				startCommands.append(str(line))

			startCommands.append(pdffile)

			subprocess.Popen(startCommands, startupinfo = si)
				# command = "[ForwardSearch(\"%s\",\"%s\",%d,%d,0,%d)]" \
				# 			% (pdffile, srcfile, line, col, setfocus)
				# print (command)
				# self.view.run_command("send_dde",
				# 		{ "service": "SUMATRA", "topic": "control", "command": command})

		
		elif 'linux' in plat: # for some reason, I get 'linux2' from sys.platform
			print ("Linux!")
			
			# the required scripts are in the 'evince' subdir
			ev_path = os.path.join(sublime.packages_path(), 'LaTeXTools', 'evince')
			ev_fwd_exec = os.path.join(ev_path, 'evince_forward_search')
			ev_sync_exec = os.path.join(ev_path, 'evince_sync') # for inverse search!
			#print ev_fwd_exec, ev_sync_exec
			
			# Run evince if either it's not running, or if focus PDF was toggled
			# Sadly ST2 has Python <2.7, so no check_output:
			running_apps = subprocess.Popen(['ps', 'xw'], stdout=subprocess.PIPE).communicate()[0]
			# If there are non-ascii chars in the output just captured, we will fail.
			# Thus, decode using the 'ignore' option to simply drop them---we don't need them
			running_apps = running_apps.decode(sublime_plugin.sys.getdefaultencoding(), 'ignore')
			
			# Run scripts through sh because the script files will lose their exec bit on github

			# Get python binary if set:
			py_binary = prefs_lin["python2"] or 'python'
			sb_binary = prefs_lin["sublime"] or 'sublime-text'
			# How long we should wait after launching sh before syncing
			sync_wait = prefs_lin["sync_wait"] or 1.0

			evince_running = ("evince " + pdffile in running_apps)
			if (not keep_focus) or (not evince_running):
				print ("(Re)launching evince")
				subprocess.Popen(['sh', ev_sync_exec, py_binary, sb_binary, pdffile], cwd=ev_path)
				print ("launched evince_sync")
				if not evince_running: # Don't wait if we have already shown the PDF
					time.sleep(sync_wait)
			if forward_sync:
				subprocess.Popen([py_binary, ev_fwd_exec, pdffile, str(line), srcfile])
		else: # ???
			pass
########NEW FILE########
__FILENAME__ = latexCommand
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = True
else:
    _ST3 = False

import sublime_plugin
import re


# Insert LaTeX command based on current word
# Position cursor inside braces

class latexcmdCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		view = self.view

		# Workaround: env* and friends trip ST2 up because * is a word boundary,
		# so we search for a word boundary

		# Code is similar to latex_cite_completions.py (should prbly factor out)
		point = view.sel()[0].b
		line = view.substr(sublime.Region(view.line(point).a, point))
		line = line[::-1]
		# Stop at space, {,[,( or $
		rex = re.compile(r"([^\s\{\[\(\$]*)\s?\{?")
		expr = re.match(rex, line)
		if expr:
			command = expr.group(1)[::-1]
			command_region = sublime.Region(point-len(command),point)
			view.erase(edit, command_region)
			# Be forgiving and skip \ if the user provided one (by mistake...)
			bslash = "" if command[0] == '\\' else "\\\\" 
			snippet = bslash + command + "{$1} $0"
			view.run_command("insert_snippet", {'contents': snippet})
		else:
			sublime.status_message("LATEXTOOLS INTERNAL ERROR: could not find command to expand")


########NEW FILE########
__FILENAME__ = latexEnvCloser
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
else:
    _ST3 = True


import sublime_plugin

# Insert environment closer
# this only looks at the LAST \begin{...}
# need to extend to allow for nested \begin's

class latex_env_closerCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		view = self.view
		pattern = r'\\(begin|end)\{[^\}]+\}'
		b = []
		currpoint = view.sel()[0].b
		point = 0
		r = view.find(pattern, point)
		while r and r.end() <= currpoint:
			be = view.substr(r)
			point = r.end()
			if "\\begin" == be[0:6]:
				b.append(be[6:])
			else:
				if be[4:] == b[-1]:
					b.pop()
				else:
					sublime.error_message("\\begin%s closed with %s on line %d"
					% (b[-1], be, view.rowcol(point)[0])) 
					return
			r = view.find(pattern, point)
		# now either b = [] or b[-1] is unmatched
		if b == []:
			sublime.error_message("Every environment is closed")
		else:
			# note the double escaping of \end
			#view.run_command("insertCharacters \"\\\\end" + b[-1] + "\\n\"")
			print ("now we insert")
			# for some reason insert does not work
			view.run_command("insert_snippet", 
								{'contents': "\\\\end" + b[-1] + "\n"})

########NEW FILE########
__FILENAME__ = latexEnvironment
import sublime, sublime_plugin
import re

# Insert LaTeX environment based on current word
# Position cursor inside environment

class latexenvCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		view = self.view

		# Workaround: env* and friends trip ST2 up because * is a word boundary,
		# so we search for a word boundary

		# Code is similar to latex_cite_completions.py (should prbly factor out)
		point = view.sel()[0].b
		line = view.substr(sublime.Region(view.line(point).a, point))
		line = line[::-1]
		rex = re.compile(r"([^\s\{]*)\s?\{?")
		expr = re.match(rex, line)
		if expr:
			environment = expr.group(1)[::-1]
			environment_region = sublime.Region(point-len(environment),point)
			view.erase(edit, environment_region)
			snippet = "\\\\begin{" + environment + "}\n$1\n\\\\end{" + environment + "}$0"
			view.run_command("insert_snippet", {'contents' : snippet})
		else:
			sublime.status_message("LATEXTOOLS INTERNAL ERROR: could not find environment to expand")


########NEW FILE########
__FILENAME__ = latex_cite_completions
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
    import getTeXRoot
else:
    _ST3 = True
    from . import getTeXRoot


import sublime_plugin
import os, os.path
import re
import codecs


class UnrecognizedCiteFormatError(Exception): pass
class NoBibFilesError(Exception): pass

class BibParsingError(Exception):
    def __init__(self, filename=""):
        self.filename = filename


OLD_STYLE_CITE_REGEX = re.compile(r"([^_]*_)?([a-zX*]*?)etic(?:\\|\b)")
NEW_STYLE_CITE_REGEX = re.compile(r"([^{},]*)(?:,[^{},]*)*\{(?:\].*?\[){0,2}([a-zX*]*?)etic\\")


def match(rex, str):
    m = rex.match(str)
    if m:
        return m.group(0)
    else:
        return None

# recursively search all linked tex files to find all
# included bibliography tags in the document and extract
# the absolute filepaths of the bib files
def find_bib_files(rootdir, src, bibfiles):
    if src[-4:].lower() != ".tex":
        src = src + ".tex"

    file_path = os.path.normpath(os.path.join(rootdir,src))
    print("Searching file: " + repr(file_path))
    # See latex_ref_completion.py for why the following is wrong:
    #dir_name = os.path.dirname(file_path)

    # read src file and extract all bibliography tags
    try:
        src_file = codecs.open(file_path, "r", 'UTF-8')
    except IOError:
        sublime.status_message("LaTeXTools WARNING: cannot open included file " + file_path)
        print ("WARNING! I can't find it! Check your \\include's and \\input's.")
        return

    src_content = re.sub("%.*","",src_file.read())
    src_file.close()

    m = re.search(r"\\usepackage\[(.*?)\]\{inputenc\}", src_content)
    if m:
        f = None
        try:
            f = codecs.open(file_path, "r", m.group(1))
            src_content = re.sub("%.*", "", f.read())
        except:
            pass
        finally:
            if f and not f.closed:
                f.close()

    bibtags =  re.findall(r'\\bibliography\{[^\}]+\}', src_content)
    bibtags += re.findall(r'\\addbibresource\{[^\}]+.bib\}', src_content)

    # extract absolute filepath for each bib file
    for tag in bibtags:
        bfiles = re.search(r'\{([^\}]+)', tag).group(1).split(',')
        for bf in bfiles:
            if bf[-4:].lower() != '.bib':
                bf = bf + '.bib'
            # We join with rootdir - everything is off the dir of the master file
            bf = os.path.normpath(os.path.join(rootdir,bf))
            bibfiles.append(bf)

    # search through input tex files recursively
    for f in re.findall(r'\\(?:input|include)\{[^\}]+\}',src_content):
        input_f = re.search(r'\{([^\}]+)', f).group(1)
        find_bib_files(rootdir, input_f, bibfiles)


def get_cite_completions(view, point, autocompleting=False):
    line = view.substr(sublime.Region(view.line(point).a, point))
    # print line

    # Reverse, to simulate having the regex
    # match backwards (cool trick jps btw!)
    line = line[::-1]
    #print line

    # Check the first location looks like a cite_, but backward
    # NOTE: use lazy match for the fancy cite part!!!
    # NOTE2: restrict what to match for fancy cite
    rex = OLD_STYLE_CITE_REGEX
    expr = match(rex, line)

    # See first if we have a cite_ trigger
    if expr:
        # Do not match on plain "cite[a-zX*]*?" when autocompleting,
        # in case the user is typing something else
        if autocompleting and re.match(r"[a-zX*]*etic\\?", expr):
            raise UnrecognizedCiteFormatError()
        # Return the completions
        prefix, fancy_cite = rex.match(expr).groups()
        preformatted = False
        if prefix:
            prefix = prefix[::-1]  # reverse
            prefix = prefix[1:]  # chop off _
        else:
            prefix = ""  # because this could be a None, not ""
        if fancy_cite:
            fancy_cite = fancy_cite[::-1]
            # fancy_cite = fancy_cite[1:] # no need to chop off?
            if fancy_cite[-1] == "X":
                fancy_cite = fancy_cite[:-1] + "*"
        else:
            fancy_cite = ""  # again just in case
        # print prefix, fancy_cite

    # Otherwise, see if we have a preformatted \cite{}
    else:
        rex = NEW_STYLE_CITE_REGEX
        expr = match(rex, line)

        if not expr:
            raise UnrecognizedCiteFormatError()

        preformatted = True
        prefix, fancy_cite = rex.match(expr).groups()
        if prefix:
            prefix = prefix[::-1]
        else:
            prefix = ""
        if fancy_cite:
            fancy_cite = fancy_cite[::-1]
            if fancy_cite[-1] == "X":
                fancy_cite = fancy_cite[:-1] + "*"
        else:
            fancy_cite = ""
        # print prefix, fancy_cite

    # Reverse back expr
    expr = expr[::-1]

    post_brace = "}"

    if not preformatted:
        # Replace cite_blah with \cite{blah
        pre_snippet = "\cite" + fancy_cite + "{"
        # The "latex_tools_replace" command is defined in latex_ref_cite_completions.py
        view.run_command("latex_tools_replace", {"a": point-len(expr), "b": point, "replacement": pre_snippet + prefix})        
        # save prefix begin and endpoints points
        new_point_a = point - len(expr) + len(pre_snippet)
        new_point_b = new_point_a + len(prefix)

    else:
        # Don't include post_brace if it's already present
        suffix = view.substr(sublime.Region(point, point + len(post_brace)))
        new_point_a = point - len(prefix)
        new_point_b = point
        if post_brace == suffix:
            post_brace = ""

    #### GET COMPLETIONS HERE #####

    root = getTeXRoot.get_tex_root(view)

    if root is None:
        # This is an unnamed, unsaved file
        # FIXME: should probably search the buffer instead of giving up
        raise NoBibFilesError()

    print ("TEX root: " + repr(root))
    bib_files = []
    find_bib_files(os.path.dirname(root), root, bib_files)
    # remove duplicate bib files
    bib_files = list(set(bib_files))
    print ("Bib files found: ")
    print (repr(bib_files))

    if not bib_files:
        # sublime.error_message("No bib files found!") # here we can!
        raise NoBibFilesError()

    bib_files = ([x.strip() for x in bib_files])

    print ("Files:")
    print (repr(bib_files))

    completions = []
    kp = re.compile(r'@[^\{]+\{(.+),')
    # new and improved regex
    # we must have "title" then "=", possibly with spaces
    # then either {, maybe repeated twice, or "
    # then spaces and finally the title
    # # We capture till the end of the line as maybe entry is broken over several lines
    # # and in the end we MAY but need not have }'s and "s
    # tp = re.compile(r'\btitle\s*=\s*(?:\{+|")\s*(.+)', re.IGNORECASE)  # note no comma!
    # # Tentatively do the same for author
    # # Note: match ending } or " (surely safe for author names!)
    # ap = re.compile(r'\bauthor\s*=\s*(?:\{|")\s*(.+)(?:\}|"),?', re.IGNORECASE)
    # # Editors
    # ep = re.compile(r'\beditor\s*=\s*(?:\{|")\s*(.+)(?:\}|"),?', re.IGNORECASE)
    # # kp2 = re.compile(r'([^\t]+)\t*')
    # # and year...
    # # Note: year can be provided without quotes or braces (yes, I know...)
    # yp = re.compile(r'\byear\s*=\s*(?:\{+|"|\b)\s*(\d+)[\}"]?,?', re.IGNORECASE)

    # This may speed things up
    # So far this captures: the tag, and the THREE possible groups
    multip = re.compile(r'\b(author|title|year|editor|journal|eprint)\s*=\s*(?:\{|"|\b)(.+?)(?:\}+|"|\b)\s*,?\s*\Z',re.IGNORECASE)

    for bibfname in bib_files:
        # # THIS IS NO LONGER NEEDED as find_bib_files() takes care of it
        # if bibfname[-4:] != ".bib":
        #     bibfname = bibfname + ".bib"
        # texfiledir = os.path.dirname(view.file_name())
        # # fix from Tobias Schmidt to allow for absolute paths
        # bibfname = os.path.normpath(os.path.join(texfiledir, bibfname))
        # print repr(bibfname)
        try:
            bibf = codecs.open(bibfname,'r','UTF-8', 'ignore')  # 'ignore' to be safe
        except IOError:
            print ("Cannot open bibliography file %s !" % (bibfname,))
            sublime.status_message("Cannot open bibliography file %s !" % (bibfname,))
            continue
        else:
            bib = bibf.readlines()
            bibf.close()
        print ("%s has %s lines" % (repr(bibfname), len(bib)))

        keywords = []
        titles = []
        authors = []
        years = []
        journals = []
        #
        entry = {   "keyword": "", 
                    "title": "",
                    "author": "", 
                    "year": "", 
                    "editor": "",
                    "journal": "",
                    "eprint": "" }
        for line in bib:
            line = line.strip()
            # Let's get rid of irrelevant lines first
            if line == "" or line[0] == '%':
                continue
            if line.lower()[0:8] == "@comment":
                continue
            if line.lower()[0:7] == "@string":
                continue
            if line[0] == "@":
                # First, see if we can add a record; the keyword must be non-empty, other fields not
                if entry["keyword"]:
                    keywords.append(entry["keyword"])
                    titles.append(entry["title"])
                    years.append(entry["year"])
                    # For author, if there is an editor, that's good enough
                    authors.append(entry["author"] or entry["editor"] or "????")
                    journals.append(entry["journal"] or entry["eprint"] or "????")
                    # Now reset for the next iteration
                    entry["keyword"] = ""
                    entry["title"] = ""
                    entry["year"] = ""
                    entry["author"] = ""
                    entry["editor"] = ""
                    entry["journal"] = ""
                    entry["eprint"] = ""
                # Now see if we get a new keyword
                kp_match = kp.search(line)
                if kp_match:
                    entry["keyword"] = kp_match.group(1) # No longer decode. Was: .decode('ascii','ignore')
                else:
                    print ("Cannot process this @ line: " + line)
                    print ("Previous record " + entry)
                continue
            # Now test for title, author, etc.
            # Note: we capture only the first line, but that's OK for our purposes
            multip_match = multip.search(line)
            if multip_match:
                key = multip_match.group(1).lower()     # no longer decode. Was:    .decode('ascii','ignore')
                value = multip_match.group(2)           #                           .decode('ascii','ignore')
                entry[key] = value
            continue

        # at the end, we are left with one bib entry
        keywords.append(entry["keyword"])
        titles.append(entry["title"])
        years.append(entry["year"])
        authors.append(entry["author"] or entry["editor"] or "????")
        journals.append(entry["journal"] or entry["eprint"] or "????")

        print ( "Found %d total bib entries" % (len(keywords),) )

        # # Filter out }'s at the end. There should be no commas left
        titles = [t.replace('{\\textquoteright}', '').replace('{','').replace('}','') for t in titles]

        # format author field
        def format_author(authors):
            # print(authors)
            # split authors using ' and ' and get last name for 'last, first' format
            authors = [a.split(", ")[0].strip(' ') for a in authors.split(" and ")]
            # get last name for 'first last' format (preserve {...} text)
            authors = [a.split(" ")[-1] if a[-1] != '}' or a.find('{') == -1 else re.sub(r'{|}', '', a[len(a) - a[::-1].index('{'):-1]) for a in authors]
            #     authors = [a.split(" ")[-1] for a in authors]
            # truncate and add 'et al.'
            if len(authors) > 2:
                authors = authors[0] + " et al."
            else:
                authors = ' & '.join(authors)
            # return formated string
            # print(authors)
            return authors

        # format list of authors
        authors_short = [format_author(author) for author in authors]

        # short title
        sep = re.compile(":|\.|\?")
        titles_short = [sep.split(title)[0] for title in titles]
        titles_short = [title[0:60] + '...' if len(title) > 60 else title for title in titles_short]

        # completions object
        completions += zip(keywords, titles, authors, years, authors_short, titles_short, journals)


    #### END COMPLETIONS HERE ####

    return completions, prefix, post_brace, new_point_a, new_point_b


# Based on html_completions.py
# see also latex_ref_completions.py
#
# It expands citations; activated by 
# cite<tab>
# citep<tab> and friends
#
# Furthermore, you can "pre-filter" the completions: e.g. use
#
# cite_sec
#
# to select all citation keywords starting with "sec". 
#
# There is only one problem: if you have a keyword "sec:intro", for instance,
# doing "cite_intro:" will find it correctly, but when you insert it, this will be done
# right after the ":", so the "cite_intro:" won't go away. The problem is that ":" is a
# word boundary. Then again, TextMate has similar limitations :-)
#
# There is also another problem: * is also a word boundary :-( So, use e.g. citeX if
# what you want is \cite*{...}; the plugin handles the substitution

class LatexCiteCompletions(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        # Only trigger within LaTeX
        if not view.match_selector(locations[0],
                "text.tex.latex"):
            return []

        point = locations[0]

        try:
            completions, prefix, post_brace, new_point_a, new_point_b = get_cite_completions(view, point, autocompleting=True)
        except UnrecognizedCiteFormatError:
            return []
        except NoBibFilesError:
            sublime.status_message("No bib files found!")
            return []
        except BibParsingError as e:
            sublime.status_message("Bibliography " + e.filename + " is broken!")
            return []

        if prefix:
            completions = [comp for comp in completions if prefix.lower() in "%s %s" % (comp[0].lower(), comp[1].lower())]
            prefix += " "

        # get preferences for formating of autocomplete entries
        s = sublime.load_settings("LaTeXTools.sublime-settings")
        cite_autocomplete_format = s.get("cite_autocomplete_format", "{keyword}: {title}")

        r = [(prefix + cite_autocomplete_format.format(keyword=keyword, title=title, author=author, year=year, author_short=author_short, title_short=title_short, journal=journal),
                keyword + post_brace) for (keyword, title, author, year, author_short, title_short, journal) in completions]

        # print "%d bib entries matching %s" % (len(r), prefix)

        return r


class LatexCiteCommand(sublime_plugin.TextCommand):

    # Remember that this gets passed an edit object
    def run(self, edit):
        # get view and location of first selection, which we expect to be just the cursor position
        view = self.view
        point = view.sel()[0].b
        print (point)
        # Only trigger within LaTeX
        # Note using score_selector rather than match_selector
        if not view.score_selector(point,
                "text.tex.latex"):
            return

        try:
            completions, prefix, post_brace, new_point_a, new_point_b = get_cite_completions(view, point)
        except UnrecognizedCiteFormatError:
            sublime.error_message("Not a recognized format for citation completion")
            return
        except NoBibFilesError:
            sublime.error_message("No bib files found!")
            return
        except BibParsingError as e:
            sublime.error_message("Bibliography " + e.filename + " is broken!")
            return

        # filter against keyword, title, or author
        if prefix:
            completions = [comp for comp in completions if prefix.lower() in "%s %s %s" \
                                                    % (comp[0].lower(), comp[1].lower(), comp[2].lower())]

        # Note we now generate citation on the fly. Less copying of vectors! Win!
        def on_done(i):
            print ("latex_cite_completion called with index %d" % (i,) )

            # Allow user to cancel
            if i<0:
                return

            cite = completions[i][0] + post_brace

            #print("DEBUG: types of new_point_a and new_point_b are " + repr(type(new_point_a)) + " and " + repr(type(new_point_b)))
            # print "selected %s:%s by %s" % completions[i][0:3]
            # Replace cite expression with citation
            # the "latex_tools_replace" command is defined in latex_ref_cite_completions.py
            view.run_command("latex_tools_replace", {"a": new_point_a, "b": new_point_b, "replacement": cite})
            # Unselect the replaced region and leave the caret at the end
            caret = view.sel()[0].b
            view.sel().subtract(view.sel()[0])
            view.sel().add(sublime.Region(caret, caret))

        # get preferences for formating of quick panel
        s = sublime.load_settings("LaTeXTools.sublime-settings")
        cite_panel_format = s.get("cite_panel_format", ["{title} ({keyword})", "{author}"])

        # show quick
        view.window().show_quick_panel([[str.format(keyword=keyword, title=title, author=author, year=year, author_short=author_short, title_short=title_short, journal=journal) for str in cite_panel_format] \
                                        for (keyword, title, author, year, author_short, title_short,journal) in completions], on_done)

########NEW FILE########
__FILENAME__ = latex_ref_cite_completions
# ST2/ST3 compat
from __future__ import print_function
import sys
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
    import getTeXRoot
    from latex_cite_completions import OLD_STYLE_CITE_REGEX, NEW_STYLE_CITE_REGEX
    from latex_ref_completions import OLD_STYLE_REF_REGEX, NEW_STYLE_REF_REGEX
else:
    _ST3 = True
    from . import getTeXRoot
    from .latex_cite_completions import OLD_STYLE_CITE_REGEX, NEW_STYLE_CITE_REGEX
    from .latex_ref_completions import OLD_STYLE_REF_REGEX, NEW_STYLE_REF_REGEX


## Match both refs and cites, then dispatch as needed

# First stab: ideally we should do all matching here, then dispatch via Python, without
# invoking commands

import sublime_plugin
import re


class LatexRefCiteCommand(sublime_plugin.TextCommand):

    # Remember that this gets passed an edit object
    def run(self, edit, insert_char=""):
        # get view and location of first selection, which we expect to be just the cursor position
        view = self.view
        point = view.sel()[0].b
        print (point)
        # Only trigger within LaTeX
        # Note using score_selector rather than match_selector
        if not view.score_selector(point,
                "text.tex.latex"):
            return


        if insert_char:
#            ed = view.begin_edit()
#            point += view.insert(ed, point, insert_char)
#            view.end_edit(ed)
            # The above was roundabout and did not work on ST3!
            point += view.insert(edit, point, insert_char)
            # Get prefs and toggles to see if we are auto-triggering
            # This is only the case if we also must insert , or {, so we don't need a separate arg
            s = sublime.load_settings("LaTeXTools.sublime-settings")
            do_ref = self.view.settings().get("ref auto trigger",s.get("ref_auto_trigger", True))
            do_cite = self.view.settings().get("cite auto trigger",s.get("cite_auto_trigger", True))
        else: # if we didn't autotrigger, we must surely run
            do_ref = True
            do_cite = True

        print (do_ref,do_cite)

        # Get the contents of the current line, from the beginning of the line to
        # the current point
        line = view.substr(sublime.Region(view.line(point).a, point))
        # print line

        # Reverse
        line = line[::-1]


        if re.match(OLD_STYLE_REF_REGEX, line) or re.match(NEW_STYLE_REF_REGEX, line):
            if do_ref:
                print ("Dispatching ref")
                view.run_command("latex_ref")
            else:
                pass # Don't do anything if we match ref completion but we turned it off
        elif re.match(OLD_STYLE_CITE_REGEX, line) or re.match(NEW_STYLE_CITE_REGEX, line):
            if do_cite:
                print ("Dispatching cite")
                view.run_command("latex_cite")
            else:
                pass # ditto for cite
        else: # here we match nothing, so error out regardless of autotrigger settings
            sublime.error_message("Ref/cite: unrecognized format.")
            return

# ST3 cannot use an edit object after the TextCommand has returned; and on_done gets 
# called after TextCommand has returned. Thus, we need this work-around (works on ST2, too)
# Used by both cite and ref completion
class LatexToolsReplaceCommand(sublime_plugin.TextCommand):
    def run(self, edit, a, b, replacement):
        #print("DEBUG: types of a and b are " + repr(type(a)) + " and " + repr(type(b)))
        # On ST2, a and b are passed as long, but received as floats
        # It's probably a bug. Convert to be safe.
        if _ST3:
            region = sublime.Region(a, b)
        else:
            region = sublime.Region(long(a), long(b))
        self.view.replace(edit, region, replacement)
########NEW FILE########
__FILENAME__ = latex_ref_completions
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
    import getTeXRoot
else:
    _ST3 = True
    from . import getTeXRoot

import sublime_plugin
import os, os.path
import re
import codecs


class UnrecognizedRefFormatError(Exception): pass

_ref_special_commands = "|".join(["", "eq", "page", "v", "V", "auto", "name", "c", "C", "cpage"])[::-1]

OLD_STYLE_REF_REGEX = re.compile(r"([^_]*_)?(p)?fer(" + _ref_special_commands + r")?(?:\\|\b)")
NEW_STYLE_REF_REGEX = re.compile(r"([^{}]*)\{fer(" + _ref_special_commands + r")?\\(\()?")


def match(rex, str):
    m = rex.match(str)
    if m:
        return m.group(0)
    else:
        return None


# recursively search all linked tex files to find all
# included \label{} tags in the document and extract
def find_labels_in_files(rootdir, src, labels):
    if src[-4:].lower() != ".tex":
        src = src + ".tex"

    file_path = os.path.normpath(os.path.join(rootdir, src))
    print ("Searching file: " + repr(file_path))
    # The following was a mistake:
    #dir_name = os.path.dirname(file_path)
    # THe reason is that \input and \include reference files **from the directory
    # of the master file**. So we must keep passing that (in rootdir).

    # read src file and extract all label tags

    # We open with utf-8 by default. If you use a different encoding, too bad.
    # If we really wanted to be safe, we would read until \begin{document},
    # then stop. Hopefully we wouldn't encounter any non-ASCII chars there. 
    # But for now do the dumb thing.
    try:
        src_file = codecs.open(file_path, "r", "UTF-8")
    except IOError:
        sublime.status_message("LaTeXTools WARNING: cannot find included file " + file_path)
        print ("WARNING! I can't find it! Check your \\include's and \\input's." )
        return

    src_content = re.sub("%.*", "", src_file.read())
    src_file.close()

    # If the file uses inputenc with a DIFFERENT encoding, try re-opening
    # This is still not ideal because we may still fail to decode properly, but still... 
    m = re.search(r"\\usepackage\[(.*?)\]\{inputenc\}", src_content)
    if m and (m.group(1) not in ["utf8", "UTF-8", "utf-8"]):
        print("reopening with encoding " + m.group(1))
        f = None
        try:
            f = codecs.open(file_path, "r", m.group(1))
            src_content = re.sub("%.*", "", f.read())
        except:
            print("Uh-oh, could not read file " + file_path + " with encoding " + m.group(1))
        finally:
            if f and not f.closed:
                f.close()

    labels += re.findall(r'\\label\{([^{}]+)\}', src_content)

    # search through input tex files recursively
    for f in re.findall(r'\\(?:input|include)\{([^\{\}]+)\}', src_content):
        find_labels_in_files(rootdir, f, labels)


# get_ref_completions forms the guts of the parsing shared by both the
# autocomplete plugin and the quick panel command
def get_ref_completions(view, point, autocompleting=False):
    # Get contents of line from start up to point
    line = view.substr(sublime.Region(view.line(point).a, point))
    # print line

    # Reverse, to simulate having the regex
    # match backwards (cool trick jps btw!)
    line = line[::-1]
    #print line

    # Check the first location looks like a ref, but backward
    rex = OLD_STYLE_REF_REGEX
    expr = match(rex, line)
    # print expr

    if expr:
        # Do not match on plain "ref" when autocompleting,
        # in case the user is typing something else
        if autocompleting and re.match(r"p?fer(?:" + _ref_special_commands + r")?\\?", expr):
            raise UnrecognizedRefFormatError()
        # Return the matched bits, for mangling
        prefix, has_p, special_command = rex.match(expr).groups()
        preformatted = False
        if prefix:
            prefix = prefix[::-1]   # reverse
            prefix = prefix[1:]     # chop off "_"
        else:
            prefix = ""
        #print prefix, has_p, special_command

    else:
        # Check to see if the location matches a preformatted "\ref{blah"
        rex = NEW_STYLE_REF_REGEX
        expr = match(rex, line)

        if not expr:
            raise UnrecognizedRefFormatError()

        preformatted = True
        # Return the matched bits (barely needed, in this case)
        prefix, special_command, has_p = rex.match(expr).groups()
        if prefix:
            prefix = prefix[::-1]   # reverse
        else:
            prefix = ""
        #print prefix, has_p, special_command

    pre_snippet = "\\" + special_command[::-1] + "ref{"
    post_snippet = "}"

    if has_p:
        pre_snippet = "(" + pre_snippet
        post_snippet = post_snippet + ")"

    if not preformatted:
        # Replace ref_blah with \ref{blah
        # The "latex_tools_replace" command is defined in latex_ref_cite_completions.py
        view.run_command("latex_tools_replace", {"a": point-len(expr), "b": point, "replacement": pre_snippet + prefix})
        # save prefix begin and endpoints points
        new_point_a = point - len(expr) + len(pre_snippet)
        new_point_b = new_point_a + len(prefix)
#        view.end_edit(ed)

    else:
        # Don't include post_snippet if it's already present
        suffix = view.substr(sublime.Region(point, point + len(post_snippet)))
        new_point_a = point - len(prefix)
        new_point_b = point
        if post_snippet == suffix:
            post_snippet = ""

    completions = []
    # Check the file buffer first:
    #    1) in case there are unsaved changes
    #    2) if this file is unnamed and unsaved, get_tex_root will fail
    view.find_all(r'\\label\{([^\{\}]+)\}', 0, '\\1', completions)

    root = getTeXRoot.get_tex_root(view)
    if root:
        print ("TEX root: " + repr(root))
        find_labels_in_files(os.path.dirname(root), root, completions)

    # remove duplicates
    completions = list(set(completions))

    return completions, prefix, post_snippet, new_point_a, new_point_b


# Based on html_completions.py
#
# It expands references; activated by 
# ref<tab>
# refp<tab> [this adds parentheses around the ref]
# eqref<tab> [obvious]
#
# Furthermore, you can "pre-filter" the completions: e.g. use
#
# ref_sec
#
# to select all labels starting with "sec". 
#
# There is only one problem: if you have a label "sec:intro", for instance,
# doing "ref_sec:" will find it correctly, but when you insert it, this will be done
# right after the ":", so the "ref_sec:" won't go away. The problem is that ":" is a
# word boundary. Then again, TextMate has similar limitations :-)

class LatexRefCompletions(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        # Only trigger within LaTeX
        if not view.match_selector(locations[0],
                "text.tex.latex"):
            return []

        point = locations[0]

        try:
            completions, prefix, post_snippet, new_point_a, new_point_b = get_ref_completions(view, point, autocompleting=True)
        except UnrecognizedRefFormatError:
            return []

        # r = [(label + "\t\\ref{}", label + post_snippet) for label in completions]
        r = [(label, label + post_snippet) for label in completions]
        #print r
        return (r, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)


### Ref completions using the quick panel

class LatexRefCommand(sublime_plugin.TextCommand):

    # Remember that this gets passed an edit object
    def run(self, edit):
        # get view and location of first selection, which we expect to be just the cursor position
        view = self.view
        point = view.sel()[0].b
        print (point)
        # Only trigger within LaTeX
        # Note using score_selector rather than match_selector
        if not view.score_selector(point,
                "text.tex.latex"):
            return

        try:
            completions, prefix, post_snippet, new_point_a, new_point_b = get_ref_completions(view, point)
        except UnrecognizedRefFormatError:
            sublime.error_message("Not a recognized format for reference completion")
            return

        # filter! Note matching is "less fuzzy" than ST2. Room for improvement...
        completions = [c for c in completions if prefix in c]

        if not completions:
            sublime.error_message("No label matches %s !" % (prefix,))
            return

        # Note we now generate refs on the fly. Less copying of vectors! Win!
        def on_done(i):
            print ("latex_ref_completion called with index %d" % (i,))
            
            # Allow user to cancel
            if i<0:
                return

            ref = completions[i] + post_snippet
            

            # Replace ref expression with reference and possibly post_snippet
            # The "latex_tools_replace" command is defined in latex_ref_cite_completions.py
            view.run_command("latex_tools_replace", {"a": new_point_a, "b": new_point_b, "replacement": ref})
            # Unselect the replaced region and leave the caret at the end
            caret = view.sel()[0].b
            view.sel().subtract(view.sel()[0])
            view.sel().add(sublime.Region(caret, caret))
        
        view.window().show_quick_panel(completions, on_done)
########NEW FILE########
__FILENAME__ = makePDF
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
	_ST3 = False
	import getTeXRoot
	import parseTeXlog
else:
	_ST3 = True
	from . import getTeXRoot
	from . import parseTeXlog

import sublime_plugin
import sys
import imp
import os, os.path
import threading
import functools
import subprocess
import types
import re
import codecs

DEBUG = False

# Compile current .tex file to pdf
# Allow custom scripts and build engines!

# The actual work is done by builders, loaded on-demand from prefs

# Encoding: especially useful for Windows
# TODO: counterpart for OSX? Guess encoding of files?
def getOEMCP():
    # Windows OEM/Ansi codepage mismatch issue.
    # We need the OEM cp, because texify and friends are console programs
    import ctypes
    codepage = ctypes.windll.kernel32.GetOEMCP()
    return str(codepage)





# First, define thread class for async processing

class CmdThread ( threading.Thread ):

	# Use __init__ to pass things we need
	# in particular, we pass the caller in teh main thread, so we can display stuff!
	def __init__ (self, caller):
		self.caller = caller
		threading.Thread.__init__ ( self )

	def run ( self ):
		print ("Welcome to thread " + self.getName())
		self.caller.output("[Compiling " + self.caller.file_name + "]")

		# Handle path; copied from exec.py
		if self.caller.path:
			old_path = os.environ["PATH"]
			# The user decides in the build system  whether he wants to append $PATH
			# or tuck it at the front: "$PATH;C:\\new\\path", "C:\\new\\path;$PATH"
			# Handle differently in Python 2 and 3, to be safe:
			if not _ST3:
				os.environ["PATH"] = os.path.expandvars(self.caller.path).encode(sys.getfilesystemencoding())
			else:
				os.environ["PATH"] = os.path.expandvars(self.caller.path)

		# Set up Windows-specific parameters
		if self.caller.plat == "windows":
			# make sure console does not come up
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

		# Now, iteratively call the builder iterator
		#
		cmd_iterator = self.caller.builder.commands()
		for (cmd, msg) in cmd_iterator:

			# If there is a message, display it
			if msg:
				self.caller.output(msg)

			# If there is nothing to be done, exit loop
			# (Avoids error with empty cmd_iterator)
			if cmd == "":
				break
			print(cmd)
			# Now create a Popen object
			try:
				if self.caller.plat == "windows":
					proc = subprocess.Popen(cmd, startupinfo=startupinfo, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
				else:
					proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
			except:
				self.caller.output("\n\nCOULD NOT COMPILE!\n\n")
				self.caller.output("Attempted command:")
				self.caller.output(" ".join(cmd))
				self.caller.output("\nBuild engine: " + self.caller.builder.name)
				self.caller.proc = None
				if self.caller.path:
					os.environ["PATH"] = old_path
				return
			
			# Now actually invoke the command, making sure we allow for killing
			# First, save process handle into caller; then communicate (which blocks)
			self.caller.proc = proc
			out, err = proc.communicate()
			self.caller.builder.set_output(out.decode(self.caller.encoding,"ignore"))

			# Here the process terminated, but it may have been killed. If so, stop and don't read log
			# Since we set self.caller.proc above, if it is None, the process must have been killed.
			# TODO: clean up?
			if not self.caller.proc:
				print (proc.returncode)
				self.caller.output("\n\n[User terminated compilation process]\n")
				self.caller.finish(False)	# We kill, so won't switch to PDF anyway
				return
			# Here we are done cleanly:
			self.caller.proc = None
			print ("Finished normally")
			print (proc.returncode)

			# At this point, out contains the output from the current command;
			# we pass it to the cmd_iterator and get the next command, until completion

		# Clean up
		cmd_iterator.close()

		# restore path if needed
		if self.caller.path:
			os.environ["PATH"] = old_path

		# CHANGED 12-10-27. OK, here's the deal. We must open in binary mode on Windows
		# because silly MiKTeX inserts ASCII control characters in over/underfull warnings.
		# In particular it inserts EOFs, which stop reading altogether; reading in binary
		# prevents that. However, that's not the whole story: if a FS character is encountered,
		# AND if we invoke splitlines on a STRING, it sadly breaks the line in two. This messes up
		# line numbers in error reports. If, on the other hand, we invoke splitlines on a
		# byte array (? whatever read() returns), this does not happen---we only break at \n, etc.
		# However, we must still decode the resulting lines using the relevant encoding.
		# 121101 -- moved splitting and decoding logic to parseTeXlog, where it belongs.
		
		# Note to self: need to think whether we don't want to codecs.open this, too...
		# Also, we may want to move part of this logic to the builder...
		data = open(self.caller.tex_base + ".log", 'rb').read()		

		errors = []
		warnings = []

		try:
			(errors, warnings) = parseTeXlog.parse_tex_log(data)
			content = [""]
			if errors:
				content.append("Errors:") 
				content.append("")
				content.extend(errors)
			else:
				content.append("No errors.")
			if warnings:
				if errors:
					content.extend(["", "Warnings:"])
				else:
					content[-1] = content[-1] + " Warnings:" 
				content.append("")
				content.extend(warnings)
			else:
				content.append("")
		except Exception as e:
			content=["",""]
			content.append("LaTeXtools could not parse the TeX log file")
			content.append("(actually, we never should have gotten here)")
			content.append("")
			content.append("Python exception: " + repr(e))
			content.append("")
			content.append("Please let me know on GitHub. Thanks!")

		self.caller.output(content)
		self.caller.output("\n\n[Done!]\n")
		self.caller.finish(len(errors) == 0)


# Actual Command

class make_pdfCommand(sublime_plugin.WindowCommand):

	def run(self, cmd="", file_regex="", path=""):
		
		# Try to handle killing
		if hasattr(self, 'proc') and self.proc: # if we are running, try to kill running process
			self.output("\n\n### Got request to terminate compilation ###")
			self.proc.kill()
			self.proc = None
			return
		else: # either it's the first time we run, or else we have no running processes
			self.proc = None
		
		view = self.window.active_view()

		self.file_name = getTeXRoot.get_tex_root(view)
		if not os.path.isfile(self.file_name):
			sublime.error_message(self.file_name + ": file not found.")
			return

		self.tex_base, self.tex_ext = os.path.splitext(self.file_name)
		tex_dir = os.path.dirname(self.file_name)
		
		# Output panel: from exec.py
		if not hasattr(self, 'output_view'):
			self.output_view = self.window.get_output_panel("exec")

		# Dumb, but required for the moment for the output panel to be picked
        # up as the result buffer
		self.window.get_output_panel("exec")

		self.output_view.settings().set("result_file_regex", "^([^:\n\r]*):([0-9]+):?([0-9]+)?:? (.*)$")
		# self.output_view.settings().set("result_line_regex", line_regex)
		self.output_view.settings().set("result_base_dir", tex_dir)

		self.window.run_command("show_panel", {"panel": "output.exec"})
		
		self.output_view.settings().set("result_file_regex", file_regex)

		if view.is_dirty():
			print ("saving...")
			view.run_command('save') # call this on view, not self.window
		
		if self.tex_ext.upper() != ".TEX":
			sublime.error_message("%s is not a TeX source file: cannot compile." % (os.path.basename(view.file_name()),))
			return
		
		self.plat = sublime.platform()
		if self.plat == "osx":
			self.encoding = "UTF-8"
		elif self.plat == "windows":
			self.encoding = getOEMCP()
		elif self.plat == "linux":
			self.encoding = "UTF-8"
		else:
			sublime.error_message("Platform as yet unsupported. Sorry!")
			return	
		
		# Get platform settings, builder, and builder settings
		s = sublime.load_settings("LaTeXTools.sublime-settings")
		platform_settings  = s.get(self.plat)
		builder_name = s.get("builder")
		# This *must* exist, so if it doesn't, the user didn't migrate
		if builder_name is None:
			sublime.error_message("LaTeXTools: you need to migrate your preferences. See the README file for instructions.")
			return
		# Default to 'traditional' builder
		if builder_name in ['', 'default']:
			builder_name = 'traditional'
		builder_path = s.get("builder_path") # relative to ST packages dir!
		builder_file_name   = builder_name + 'Builder.py'
		builder_class_name  = builder_name.capitalize() + 'Builder'
		builder_settings = s.get("builder_settings")

		# Safety check: if we are using a built-in builder, disregard
		# builder_path, even if it was specified in the pref file
		if builder_name in ['simple', 'traditional', 'script', 'default','']:
			builder_path = None

		# Now actually get the builder
		ltt_path = os.path.join(sublime.packages_path(),'LaTeXTools','builders')
		if builder_path:
			bld_path = os.path.join(sublime.packages_path(), builder_path)
		else:
			bld_path = ltt_path
		bld_file = os.path.join(bld_path, builder_file_name)

		if not os.path.isfile(bld_file):
			sublime.error_message("Cannot find builder " + builder_name + ".\n" \
							      "Check your LaTeXTools Preferences")
			return
		
		# We save the system path and TEMPORARILY add the builders path to it,
		# so we can simply "import pdfBuilder" in the builder module
		# For custom builders, we need to add both the LaTeXTools builders
		# path, as well as the custom path specified above.
		# The mechanics are from http://effbot.org/zone/import-string.htm

		syspath_save = list(sys.path)
		sys.path.insert(0, ltt_path)
		if builder_path:
			sys.path.insert(0, bld_path)
		builder_module = __import__(builder_name + 'Builder')
		sys.path[:] = syspath_save
		
		print(repr(builder_module))
		builder_class = getattr(builder_module, builder_class_name)
		print(repr(builder_class))
		# We should now be able to construct the builder object
		self.builder = builder_class(self.file_name, self.output, builder_settings, platform_settings)
		
		# Restore Python system path
		sys.path[:] = syspath_save
		
		# Now get the tex binary path from prefs, change directory to
		# that of the tex root file, and run!
		self.path = platform_settings['texpath']
		os.chdir(tex_dir)
		CmdThread(self).start()
		print (threading.active_count())


	# Threading headaches :-)
	# The following function is what gets called from CmdThread; in turn,
	# this spawns append_data, but on the main thread.

	def output(self, data):
		sublime.set_timeout(functools.partial(self.do_output, data), 0)

	def do_output(self, data):
        # if proc != self.proc:
        #     # a second call to exec has been made before the first one
        #     # finished, ignore it instead of intermingling the output.
        #     if proc:
        #         proc.kill()
        #     return

		# try:
		#     str = data.decode(self.encoding)
		# except:
		#     str = "[Decode error - output not " + self.encoding + "]"
		#     proc = None

		# decoding in thread, so we can pass coded and decoded data
		# handle both lists and strings
		# Need different handling for python 2 and 3
		if not _ST3:
			strdata = data if isinstance(data, types.StringTypes) else "\n".join(data)
		else:
			strdata = data if isinstance(data, str) else "\n".join(data)

		# Normalize newlines, Sublime Text always uses a single \n separator
		# in memory.
		strdata = strdata.replace('\r\n', '\n').replace('\r', '\n')

		selection_was_at_end = (len(self.output_view.sel()) == 1
		    and self.output_view.sel()[0]
		        == sublime.Region(self.output_view.size()))
		self.output_view.set_read_only(False)
		# Move this to a TextCommand for compatibility with ST3
		self.output_view.run_command("do_output_edit", {"data": strdata, "selection_was_at_end": selection_was_at_end})
		# edit = self.output_view.begin_edit()
		# self.output_view.insert(edit, self.output_view.size(), strdata)
		# if selection_was_at_end:
		#     self.output_view.show(self.output_view.size())
		# self.output_view.end_edit(edit)
		self.output_view.set_read_only(True)	

	# Also from exec.py
	# Set the selection to the start of the output panel, so next_result works
	# Then run viewer

	def finish(self, can_switch_to_pdf):
		sublime.set_timeout(functools.partial(self.do_finish, can_switch_to_pdf), 0)

	def do_finish(self, can_switch_to_pdf):
		# Move to TextCommand for compatibility with ST3
		# edit = self.output_view.begin_edit()
		# self.output_view.sel().clear()
		# reg = sublime.Region(0)
		# self.output_view.sel().add(reg)
		# self.output_view.show(reg) # scroll to top
		# self.output_view.end_edit(edit)
		self.output_view.run_command("do_finish_edit")
		if can_switch_to_pdf:
			self.window.active_view().run_command("jump_to_pdf", {"from_keybinding": False})


class DoOutputEditCommand(sublime_plugin.TextCommand):
    def run(self, edit, data, selection_was_at_end):
        self.view.insert(edit, self.view.size(), data)
        if selection_was_at_end:
            self.view.show(self.view.size())

class DoFinishEditCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.sel().clear()
        reg = sublime.Region(0)
        self.view.sel().add(reg)
        self.view.show(reg)

########NEW FILE########
__FILENAME__ = migrate
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
	_ST3 = False
	import getTeXRoot
	import parseTeXlog
else:
	_ST3 = True
	from . import getTeXRoot
	from . import parseTeXlog

import sublime_plugin
#import sys
#import imp
import os, os.path
import shutil
#import threading
#import functools
#import subprocess
#import types
import re
import codecs

DEBUG = False

# Copy settings from default file to user directory
# Try to incorporate existing user settings

DEFAULT_SETTINGS = "LaTeXTools.default-settings"
USER_SETTINGS = "LaTeXTools.sublime-settings"
OLD_SETTINGS = "LaTeXTools Preferences.sublime-settings"

# Settings to be ported over
# "key" is the preference key
# "type" is the type, for fixups (e.g. true vs. True)
# "line" is the line in the .default-settings file (starting from 0, not 1);
#        the code below looks for it, but set to -1 to flag errors, issues, etc.
# "tabs" is the number of tabs before the key
# "last" is True if it's the last line in a {...} block (so must omit comma at the end)
# WARNING: obviously, this works ONLY with a known default-settings file.
settings = [	{"key": "cite_auto_trigger", "type": "bool", "line": -1, "tabs": 1, "last": False},
				{"key": "ref_auto_trigger", "type": "bool", "line": -1, "tabs": 1, "last": False},
				{"key": "keep_focus", "type": "bool", "line": -1, "tabs": 1, "last": False},
				{"key": "forward_sync", "type": "bool", "line": -1, "tabs": 1, "last": False},
				{"key": "python2", "type": "string", "line": -1, "tabs": 2, "last": False},
				{"key": "sublime", "type": "string", "line": -1, "tabs": 2, "last": False},
				{"key": "sync_wait", "type": "num", "line": -1, "tabs": 2, "last": True},
				{"key": "cite_panel_format", "type": "list", "line": -1, "tabs": 1, "last": False },
				{"key": "cite_autocomplete_format", "type": "string", "line": -1, "tabs": 1, "last": True}
				]

class latextoolsMigrateCommand(sublime_plugin.ApplicationCommand):

	def run(self):
		
		# First of all, try to load new settings
		# If they exist, either the user copied them manually, or we already did this
		# Hence, quit
		# NOTE: we will move this code somewhere else, but for now, it's here

		print ("Running migrate")
		sublime.status_message("Reconfiguring and migrating settings...")
		ltt_path = os.path.join(sublime.packages_path(),"LaTeXTools")
		user_path = os.path.join(sublime.packages_path(),"User")
		default_file = os.path.join(ltt_path,DEFAULT_SETTINGS)
		user_file = os.path.join(user_path,USER_SETTINGS)
		old_file = os.path.join(user_path,OLD_SETTINGS)

		killall = False # So final message check works even if there is no existing setting file
		if os.path.exists(user_file):
			killall = sublime.ok_cancel_dialog(USER_SETTINGS + " already exists in the User directory!\n"
				"Are you sure you want to DELETE YOUR CURRENT SETTINGS and revert them to default?",
				"DELETE current settings")
			if not killall:
				sublime.message_dialog("OK, I will preserve your existing settings.")
				return
		
		with codecs.open(default_file,'r','UTF-8') as def_fp:
			def_lines = def_fp.readlines()

		quotes = "\""

		# Find lines where keys are in the default file
		comments = False
		for i in range(len(def_lines)):
			l = def_lines[i].strip() # Get rid of tabs and leading spaces
			# skip comments
			# This works as long as multiline comments do not start/end on a line that
			# also contains code.
			# It's also safest if a line with code does NOT also contain comments
			beg_cmts = l[:2]
			end_cmts = l[-2:]
			if comments:
				if beg_cmts == "*/":
					comments = False
					l = l[2:] # and process the line just in case
				elif end_cmts == "*/":
					comments = False
					continue
				else: # HACK: this fails if we have "...*/ <code>", which however is bad form
					continue
			if beg_cmts=="//": # single-line comments
				continue
			if beg_cmts=="/*": # Beginning of multiline comment.
				comments = True # HACK: this fails if "<code> /* ..." begins a multiline comment
				continue
			for s in settings:
				# Be conservative: precise match.
				m = quotes + s["key"] + quotes + ":"
				if m == l[:len(m)]:
					s["line"] = i
					print(s["key"] + " is on line " + str(i) + " (0-based)")

		# Collect needed modifications
		def_modify = {}
		s_old = sublime.load_settings(OLD_SETTINGS)
		for s in settings:
			key = s["key"]
			print("Trying " + key)
			s_old_entry = s_old.get(key)
			if s_old_entry is not None: # Checking for True misses all bool's set to False!
				print("Porting " + key)
				l = s["tabs"]*"\t" + quotes + key + quotes + ": "
				if s["type"]=="bool":
					l += "true" if s_old_entry==True else "false"
				elif s["type"]=="num":
					l += str(s_old_entry)
				elif s["type"]=="list": # HACK HACK HACK! List of strings only!
					l += "["
					for el in s_old_entry:
						l += quotes + el + quotes + ","
					l = l[:-1] + "]" # replace last comma with bracket
				else:
					l += quotes + s_old_entry + quotes
				if s["last"]: # Add comma, unless at the end of a {...} block
					l+= "\n"
				else:
					l += ",\n"
				print(l)
				def_lines[s["line"]] = l

		# Modify text saying "don't touch this!" in the default file
		def_lines[0] = '// LaTeXTools Preferences\n'
		def_lines[2] = '// Keep in the User directory. Personalize as needed\n'
		for i in range(3,10):
			def_lines.pop(3) # Must be 3: 4 becomes 3, then 5 becomes 3...

		with codecs.open(user_file,'w','UTF-8') as user_fp:
			user_fp.writelines(def_lines)

		if killall:
			msg_preserved = ""
		else:
			msg_preserved = "Your existing settings, if any, have been migrated."
		sublime.status_message("Reconfiguration complete.")
		sublime.message_dialog("LaTeXTools settings successfully reconfigured. " + msg_preserved)
		return


########NEW FILE########
__FILENAME__ = parseTeXlog
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
else:
    _ST3 = True


import re
import sys
import os.path


# To accommodate both Python 2 and 3
def advance_iterator(it):
	if not _ST3:
		return it.next()
	else:
		return next(it)


print_debug = False
interactive = False
extra_file_ext = []

def debug(s):
	if print_debug:
		print ("parseTeXlog: " + s.encode('UTF-8')) # I think the ST2 console wants this

# The following function is only used when debugging interactively.
#
# If file is not found, ask me if we are debugging
# Rationale: if we are debugging from the command line, perhaps we are parsing
# a log file from a user, so apply heuristics and / or ask if the file not
# found is actually legit
#
# Return value: the question is, "Should I skip this file?" Hence:
# 	True means YES, DO SKIP IT, IT IS NOT A FILE
#	False means NO, DO NOT SKIP IT, IT IS A FILE
def debug_skip_file(f):
	# If we are not debugging, then it's not a file for sure, so skip it
	if not (print_debug and interactive):
		return True
	debug("debug_skip_file: " + f)
	f_ext = os.path.splitext(f)[1].lower()[1:]
	# Heuristic: TeXlive on Mac or Linux (well, Ubuntu at least) or Windows / MiKTeX
	# Known file extensions:
	known_file_exts = ['tex','sty','cls','cfg','def','mkii','fd','map','clo', 'dfu', \
						'ldf', 'bdf', 'bbx','cbx','lbx']
	if (f_ext in known_file_exts) and \
	   (("/usr/local/texlive/" in f) or ("/usr/share/texlive/" in f) or ("Program Files\\MiKTeX" in f) \
	   	or re.search(r"\\MiKTeX\\\d\.\d+\\tex",f)) or ("\\MiKTeX\\tex\\" in f):
		print ("TeXlive / MiKTeX FILE! Don't skip it!")
		return False
	# Heuristic: "version 2010.12.02"
	if re.match(r"version \d\d\d\d\.\d\d\.\d\d", f):
		print ("Skip it!")
		return True
	# Heuristic: TeX Live line
	if re.match(r"TeX Live 20\d\d(/Debian)?\) \(format", f):
		print ("Skip it!")
		return True
	# Heuristic: MiKTeX line
	if re.match("MiKTeX \d\.\d\d?",f):
		print ("Skip it!")
		return True
	# Heuristic: no two consecutive spaces in file name
	if "  " in f:
		print ("Skip it!")
		return True
	# Heuristic: various diagnostic messages
	if f=='e.g.,' or "ext4): destination with the same identifier" in f or "Kristoffer H. Rose" in f:
		print ("Skip it!")
		return True
	# Heuristic: file in local directory with .tex ending
	file_exts = extra_file_ext + ['tex', 'aux', 'bbl', 'cls', 'sty','out']
	if f[0:2] in ['./', '.\\', '..'] and f_ext in file_exts:
		print ("File! Don't skip it")
		return False
	if raw_input() == "":
		print ("Skip it")
		return True
	else:
		print ("FILE! Don't skip it")
		return False


# More robust parsing code: October / November 2012
# Input: tex log file, read in **binary** form, unprocessed
# Output: content to be displayed in output panel, split into lines

def parse_tex_log(data):
	debug("Parsing log file")
	errors = []
	warnings = []
	parsing = []

	guessed_encoding = 'UTF-8' # for now

	# Split data into lines while in binary form
	# Then decode using guessed encoding
	# We need the # of bytes per line, not the # of chars (codepoints), to undo TeX's line breaking
	# so we construct an array of tuples:
	#   (decoded line, length of original byte array)

	try:
		log = [(l.decode(guessed_encoding, 'ignore'), len(l))  for l in data.splitlines()]
	except UnicodeError:
		debug("log file not in UTF-8 encoding!")
		errors.append("ERROR: your log file is not in UTF-8 encoding.")
		errors.append("Sorry, I can't process this file")
		return (errors, warnings)

	# loop over all log lines; construct error message as needed
	# This will be useful for multi-file documents

	# some regexes
	# file_rx = re.compile(r"\(([^)]+)$") # OLD
	# Structure (+ means captured, - means not captured)
	# + maybe " (for Windows)
	# + maybe a drive letter and : (for Windows)
	# + maybe . NEW: or ../ or ..\, with repetitions
	# + then any char, matched NON-GREEDILY (avoids issues with multiple files on one line?)
	# + then .
	# + then any char except for whitespace or " or ); at least ONE such char
	# + then maybe " (on Windows/MikTeX)
 	# - then whitespace or ), or end of line
 	# + then anything else, captured for recycling
	# This should take care of e.g. "(./test.tex [12" or "(./test.tex (other.tex"
	# NOTES:
	# 1. we capture the initial and ending " if there is one; we'll need to remove it later
	# 2. we define the basic filename parsing regex so we can recycle it
	# 3. we allow for any character besides "(" before a file name starts. This gives a lot of 
	#	 false positives but we kill them with os.path.isfile
	file_basic = r"\"?(?:[a-zA-Z]\:)?(?:\.|(?:\.\./)|(?:\.\.\\))*.+?\.[^\s\"\)\.]+\"?"
	file_rx = re.compile(r"[^\(]*?\((" + file_basic + r")(\s|\"|\)|$)(.*)")
	# Useless file #1: {filename.ext}; capture subsequent text
	# Will avoid nested {'s as these can't really appear, except if file names have braces
	# which is REALLY bad!!!
	file_useless1_rx = re.compile(r"\{\"?(?:\.|\.\./)*[^\.]+\.[^\{\}]*\"?\}(.*)")
	# Useless file #2: <filename.ext>; capture subsequent text
	file_useless2_rx = re.compile(r"<\"?(?:\.|\.\./)*[^\.]+\.[^>]*\"?>(.*)")
	pagenum_begin_rx = re.compile(r"\s*\[\d*(.*)")
	line_rx = re.compile(r"^l\.(\d+)\s(.*)")		# l.nn <text>
	warning_rx = re.compile(r"^(.*?) Warning: (.+)") # Warnings, first line
	line_rx_latex_warn = re.compile(r"input line (\d+)\.$") # Warnings, line number
	matched_parens_rx = re.compile(r"\([^()]*\)") # matched parentheses, to be deleted (note: not if nested)
	assignment_rx = re.compile(r"\\[^=]*=")	# assignment, heuristics for line merging
	# Special case: the xy package, which reports end of processing with "loaded)" or "not reloaded)"
	xypic_begin_rx = re.compile(r"[^()]*?(?:not re)?loaded\)(.*)")
	xypic_rx = re.compile(r".*?(?:not re)?loaded\)(.*)")
	# Special case: the comment package, which prints ")" after some text
	comment_rx = re.compile(r"Excluding comment '.*?'(.*)")

	files = []
	xypic_flag = False # If we have seen xypic, report a warning, not an error for incorrect parsing

	# Support function to handle warnings
	def handle_warning(l):

		if files==[]:
			location = "[no file]"
			parsing.append("PERR [handle_warning no files] " + l)
		else:
			location = files[-1]		

		warn_match_line = line_rx_latex_warn.search(l)
		if warn_match_line:
			warn_line = warn_match_line.group(1)
			warnings.append(location + ":" + warn_line + ": " + l)
		else:
			warnings.append(location + ": " + l)

	
	# State definitions
	STATE_NORMAL = 0
	STATE_SKIP = 1
	STATE_REPORT_ERROR = 2
	STATE_REPORT_WARNING = 3
	
	state = STATE_NORMAL

	# Use our own iterator instead of for loop
	log_iterator = log.__iter__()
	line_num=0
	line = ""
	linelen = 0

	recycle_extra = False		# Should we add extra to newly read line?
	reprocess_extra = False		# Should we reprocess extra, without reading a new line?
	emergency_stop = False		# If TeX stopped processing, we can't pop all files
	incomplete_if = False  		# Ditto if some \if... statement is not complete	

	while True:
		# first of all, see if we have a line to recycle (see heuristic for "l.<nn>" lines)
		if recycle_extra:
			line, linelen = extra, extralen
			recycle_extra = False
			line_num +=1
		elif reprocess_extra:
			line = extra # NOTE: we must remember that we are reprocessing. See long-line heuristics
		else: # we read a new line
			# save previous line for "! File ended while scanning use of..." message
			prev_line = line
			try:
				line, linelen = advance_iterator(log_iterator) # will fail when no more lines
				line_num += 1
			except StopIteration:
				break
		# Now we deal with TeX's decision to truncate all log lines at 79 characters
		# If we find a line of exactly 79 characters, we add the subsequent line to it, and continue
		# until we find a line of less than 79 characters
		# The problem is that there may be a line of EXACTLY 79 chars. We keep our fingers crossed but also
		# use some heuristics to avoid disastrous consequences
		# We are inspired by latexmk (which has no heuristics, though)

		# HEURISTIC: the first line is always long, and we don't care about it
		# also, the **<file name> line may be long, but we skip it, too (to avoid edge cases)
		# We make sure we are NOT reprocessing a line!!!
		# Also, we make sure we do not have a filename match, or it would be clobbered by exending!
		if (not reprocess_extra) and line_num>1 and linelen>=79 and line[0:2] != "**": 
			debug ("Line %d is %d characters long; last char is %s" % (line_num, len(line), line[-1]))
			# HEURISTICS HERE
			extend_line = True
			recycle_extra = False
			# HEURISTIC: check first if we just have a long "(.../file.tex" (or similar) line
			# A bit inefficient as we duplicate some of the code below for filename matching
			file_match = file_rx.match(line)
			if file_match:
				debug("MATCHED (long line)")
				file_name = file_match.group(1)
				file_extra = file_match.group(2) + file_match.group(3) # don't call it "extra"
				# remove quotes if necessary, but first save the count for a later check
				quotecount = file_name.count("\"")
				file_name = file_name.replace("\"", "")
				# NOTE: on TL201X pdftex sometimes writes "pdfTeX warning" right after file name
				# This may or may not be a stand-alone long line, but in any case if we
				# extend, the file regex will fire regularly
				if file_name[-6:]=="pdfTeX" and file_extra[:8]==" warning":
					debug("pdfTeX appended to file name, extending")
				# Else, if the extra stuff is NOT ")" or "", we have more than a single
				# file name, so again the regular regex will fire
				elif file_extra not in [")", ""]:
					debug("additional text after file name, extending")
				# If we have exactly ONE quote, we are on Windows but we are missing the final quote
				# in which case we extend, because we may be missing parentheses otherwise
				elif quotecount==1:
					debug("only one quote, extending")
				# Now we have a long line consisting of a potential file name alone
				# Check if it really is a file name
				elif (not os.path.isfile(file_name)) and debug_skip_file(file_name):
					debug("Not a file name")
				else:
					debug("IT'S A (LONG) FILE NAME WITH NO EXTRA TEXT")
					extend_line = False # so we exit right away and continue with parsing

			while extend_line:
				debug("extending: " + line)
				try:
					# different handling for Python 2 and 3
					extra, extralen = advance_iterator(log_iterator)
					debug("extension? " + extra)
					line_num += 1 # for debugging purposes
					# HEURISTIC: if extra line begins with "Package:" "File:" "Document Class:",
					# or other "well-known markers",
					# we just had a long file name, so do not add
					if extralen>0 and \
					   (extra[0:5]=="File:" or extra[0:8]=="Package:" or extra[0:15]=="Document Class:") or \
					   (extra[0:9]=="LaTeX2e <") or assignment_rx.match(extra):
						extend_line = False
						# no need to recycle extra, as it's nothing we are interested in
					# HEURISTIC: when TeX reports an error, it prints some surrounding text
					# and may use the whole line. Then it prints "...", and "l.<nn> <text>" on a new line
					# pdftex warnings also use "..." at the end of a line.
					# If so, do not extend
					elif line[-3:]=="...": # and line_rx.match(extra): # a bit inefficient as we match twice
						debug("Found [...]")
						extend_line = False
						recycle_extra = True # make sure we process the "l.<nn>" line!
					else:
						line += extra
						debug("Extended: " + line)
						linelen += extralen
						if extralen < 79:
							extend_line = False
				except StopIteration:
					extend_line = False # end of file, so we must be done. This shouldn't happen, btw
		# We may skip the above "if" because we are reprocessing a line, so reset flag:
		reprocess_extra = False
		# Check various states
		if state==STATE_SKIP:
			state = STATE_NORMAL
			continue
		if state==STATE_REPORT_ERROR:
			# skip everything except "l.<nn> <text>"
			debug("Reporting error in line: " + line)
			# We check for emergency stops here, too, because it may occur before the l.nn text
			if "! Emergency stop." in line:
				emergency_stop = True
				debug("Emergency stop found")
				continue
			err_match = line_rx.match(line)
			if not err_match:
				continue
			# now we match!
			state = STATE_NORMAL
			err_line = err_match.group(1)
			err_text = err_match.group(2)
			# err_msg is set from last time
			if files==[]:
				location = "[no file]"
				parsing.append("PERR [STATE_REPORT_ERROR no files] " + line)
			else:
				location = files[-1]
			debug("Found error: " + err_msg)		
			errors.append(location + ":" + err_line + ": " + err_msg + " [" + err_text + "]")
			continue
		if state==STATE_REPORT_WARNING:
			# add current line and check if we are done or not
			current_warning += line
			if line[-1]=='.':
				handle_warning(current_warning)
				current_warning = None
				state = STATE_NORMAL # otherwise the state stays at REPORT_WARNING
			continue
		if line=="":
			continue

		# Sometimes an \if... is not completed; in this case some files may remain on the stack
		# I think the same format may apply to different \ifXXX commands, so make it flexible
		if len(line)>0 and line.strip()[:23]=="(\\end occurred when \\if" and \
						   line.strip()[-15:]=="was incomplete)":
			incomplete_if = True
			debug(line)

		# Skip things that are clearly not file names, though they may trigger false positives
		if len(line)>0 and \
			(line[0:5]=="File:" or line[0:8]=="Package:" or line[0:15]=="Document Class:") or \
			(line[0:9]=="LaTeX2e <"):
			continue

		# Are we done? Get rid of extra spaces, just in case (we may have extended a line, etc.)
		if line.strip() == "Here is how much of TeX's memory you used:":
			if len(files)>0:
				if emergency_stop or incomplete_if:
					debug("Done processing, files on stack due to known conditions (all is fine!)")
				elif xypic_flag:
					parsing.append("PERR [files on stack (xypic)] " + ";".join(files))
				else:
					parsing.append("PERR [files on stack] " + ";".join(files))
				files=[]			
			# break
			# We cannot stop here because pdftex may yet have errors to report.

		# Special error reporting for e.g. \footnote{text NO MATCHING PARENS & co
		if "! File ended while scanning use of" in line:
			scanned_command = line[35:-2] # skip space and period at end
			# we may be unable to report a file by popping it, so HACK HACK HACK
			file_name, linelen = advance_iterator(log_iterator) # <inserted text>
			file_name, linelen = advance_iterator(log_iterator) #      \par
			file_name, linelen = advance_iterator(log_iterator)
			file_name = file_name[3:] # here is the file name with <*> in front
			errors.append("TeX STOPPED: " + line[2:-2]+prev_line[:-5])
			errors.append("TeX reports the error was in file:" + file_name)
			continue

		# Here, make sure there was no uncaught error, in which case we do more special processing
		# This will match both tex and pdftex Fatal Error messages
		if "==> Fatal error occurred," in line:
			debug("Fatal error detected")
			if errors == []:
				errors.append("TeX STOPPED: fatal errors occurred. Check the TeX log file for details")
			continue

		# If tex just stops processing, we will be left with files on stack, so we keep track of it
		if "! Emergency stop." in line:
			state = STATE_SKIP
			emergency_stop = True
			debug("Emergency stop found")
			continue

		# TOo many errors: will also have files on stack. For some reason
		# we have to do differently from above (need to double-check: why not stop processing if
		# emergency stop, too?)
		if "(That makes 100 errors; please try again.)" in line:
			errors.append("Too many errors. TeX stopped.")
			debug("100 errors, stopping")
			break

		# catch over/underfull
		# skip everything for now
		# Over/underfull messages end with [] so look for that
		if line[0:8] == "Overfull" or line[0:9] == "Underfull":
			if line[-2:]=="[]": # one-line over/underfull message
				continue
			ou_processing = True
			while ou_processing:
				try:
					line, linelen = advance_iterator(log_iterator) # will fail when no more lines
				except StopIteration:
					debug("Over/underfull: StopIteration (%d)" % line_num)
					break
				line_num += 1
				debug("Over/underfull: skip " + line + " (%d) " % line_num)
				# Sometimes it's " []" and sometimes it's "[]"...
				if len(line)>0 and line in [" []", "[]"]:
					ou_processing = False
			if ou_processing:
				warnings.append("Malformed LOG file: over/underfull")
				warnings.append("Please let me know via GitHub")
				break
			else:
				continue

		# Special case: the bibgerm package, which has comments starting and ending with
		# **, and then finishes with "**)"
		if len(line)>0 and line[:2] == "**" and line[-3:] == "**)" \
						and files and "bibgerm" in files[-1]:
			debug("special case: bibgerm")
			debug(" "*len(files) + files[-1] + " (%d)" % (line_num,))
			files.pop()
			continue

		# Special case: the relsize package, which puts ")" at the end of a
		# line beginning with "Examine \". Ah well!
		if len(line)>0 and line[:9] == "Examine \\" and line[-3:] == ". )" \
						and files and  "relsize" in files[-1]:
			debug("special case: relsize")
			debug(" "*len(files) + files[-1] + " (%d)" % (line_num,))
			files.pop()
			continue
		
		# Special case: the comment package, which puts ")" at the end of a 
		# line beginning with "Excluding comment 'something'"
		# Since I'm not sure, we match "Excluding comment 'something'" and recycle the rest
		comment_match = comment_rx.match(line)
		if comment_match and files and "comment" in files[-1]:
			debug("special case: comment")
			extra = comment_match.group(1)
			debug("Reprocessing " + extra)
			reprocess_extra = True
			continue

		# Special case: the numprint package, which prints a line saying
		# "No configuration file... found.)"
		# if there is no config file (duh!), and that (!!!) signals the end of processing :-(

		if len(line)>0 and line.strip() == "No configuration file `numprint.cfg' found.)" \
						and files and "numprint" in files[-1]:
			debug("special case: numprint")
			debug(" "*len(files) + files[-1] + " (%d)" % (line_num,))
			files.pop()
			continue	

		# Special case: xypic's "loaded)" at the BEGINNING of a line. Will check later
		# for matches AFTER other text.
		xypic_match = xypic_begin_rx.match(line)
		if xypic_match:
			debug("xypic match before: " + line)
			# Do an extra check to make sure we are not too eager: is the topmost file
			# likely to be an xypic file? Look for xypic in the file name
			if files and "xypic" in files[-1]:
				debug(" "*len(files) + files[-1] + " (%d)" % (line_num,))
				files.pop()
				extra = xypic_match.group(1)
				debug("Reprocessing " + extra)
				reprocess_extra = True
				continue
			else:
				debug("Found loaded) but top file name doesn't have xy")


		line = line.strip() # get rid of initial spaces
		# note: in the next line, and also when we check for "!", we use the fact that "and" short-circuits
		if len(line)>0 and line[0]==')': # denotes end of processing of current file: pop it from stack
			if files:
				debug(" "*len(files) + files[-1] + " (%d)" % (line_num,))
				files.pop()
				extra = line[1:]
				debug("Reprocessing " + extra)
				reprocess_extra = True
				continue
			else:
				parsing.append("PERR [')' no files]")
				break

		# Opening page indicators: skip and reprocess
		# Note: here we look for matches at the BEGINNING of a line. We check again below
		# for matches elsewhere, but AFTER matching for file names.
		pagenum_begin_match = pagenum_begin_rx.match(line)
		if pagenum_begin_match:
			extra = pagenum_begin_match.group(1)
			debug("Reprocessing " + extra)
			reprocess_extra = True
			continue

		# Closing page indicators: skip and reprocess
		# Also, sometimes we have a useless file <file.tex, then a warning happens and the
		# last > appears later. Pick up such stray >'s as well.
		if len(line)>0 and line[0] in [']', '>']:
			extra = line[1:]
			debug("Reprocessing " + extra)
			reprocess_extra = True
			continue

		# Useless file matches: {filename.ext} or <filename.ext>. We just throw it out
		file_useless_match = file_useless1_rx.match(line) or file_useless2_rx.match(line)
		if file_useless_match: 
			extra = file_useless_match.group(1)
			debug("Useless file: " + line)
			debug("Reprocessing " + extra)
			reprocess_extra = True
			continue


		# this seems to happen often: no need to push / pop it
		if line[:12]=="(pdftex.def)":
			continue

		# Now we should have a candidate file. We still have an issue with lines that
		# look like file names, e.g. "(Font)     blah blah data 2012.10.3" but those will
		# get killed by the isfile call. Not very efficient, but OK in practice
		debug("FILE? Line:" + line)
		file_match = file_rx.match(line)
		if file_match:
			debug("MATCHED")
			file_name = file_match.group(1)
			extra = file_match.group(2) + file_match.group(3)
			# remove quotes if necessary
			file_name = file_name.replace("\"", "")
			# on TL2011 pdftex sometimes writes "pdfTeX warning" right after file name
			# so fix it
			# TODO: report pdftex warning
			if file_name[-6:]=="pdfTeX" and extra[:8]==" warning":
				debug("pdfTeX appended to file name; removed")
				file_name = file_name[:-6]
				extra = "pdfTeX" + extra
			# This kills off stupid matches
			if (not os.path.isfile(file_name)) and debug_skip_file(file_name):
				#continue
				# NOTE BIG CHANGE HERE: CONTINUE PROCESSING IF NO MATCH
				pass
			else:
				debug("IT'S A FILE!")
				files.append(file_name)
				debug(" "*len(files) + files[-1] + " (%d)" % (line_num,))
				# Check if it's a xypic file
				if (not xypic_flag) and "xypic" in file_name:
					xypic_flag = True
					debug("xypic detected, demoting parsing error to warnings")
				# now we recycle the remainder of this line
				debug("Reprocessing " + extra)
				reprocess_extra = True
				continue

		# Special case: match xypic's " loaded)" markers
		# You may think we already checked for this. But, NO! We must check both BEFORE and
		# AFTER looking for file matches. The problem is that we
		# may have the " loaded)" marker either after non-file text, or after a loaded
		# file name. Aaaarghh!!!
		xypic_match = xypic_rx.match(line)
		if xypic_match:
			debug("xypic match after: " + line)
			# Do an extra check to make sure we are not too eager: is the topmost file
			# likely to be an xypic file? Look for xypic in the file name
			if files and "xypic" in files[-1]:
				debug(" "*len(files) + files[-1] + " (%d)" % (line_num,))
				files.pop()
				extra = xypic_match.group(1)
				debug("Reprocessing " + extra)
				reprocess_extra = True
				continue
			else:
				debug("Found loaded) but top file name doesn't have xy")

		if len(line)>0 and line[0]=='!': # Now it's surely an error
			debug("Error found: " + line)
			# If it's a pdftex error, it's on the current line, so report it
			if "pdfTeX error" in line:
				err_msg = line[1:].strip() # remove '!' and possibly spaces
				# This may or may not have a file location associated with it. 
				# Be conservative and do not try to report one.
				errors.append(err_msg)
				errors.append("Check the TeX log file for more information")
				continue
			# Now it's a regular TeX error 
			err_msg = line[2:] # skip "! "
			# next time around, err_msg will be set and we'll extract all info
			state = STATE_REPORT_ERROR
			continue

		# Second match for opening page numbers. We now use "search" which matches
		# everywhere, not just at the beginning. We do so AFTER matching file names so we
		# don't miss any.
		pagenum_begin_match = pagenum_begin_rx.search(line)
		if pagenum_begin_match:
			debug("Matching [xx after some text")
			extra = pagenum_begin_match.group(1)
			debug("Reprocessing " + extra)
			reprocess_extra = True
			continue		


		warning_match = warning_rx.match(line)
		if warning_match:
			# if last character is a dot, it's a single line
			if line[-1] == '.':
				handle_warning(line)
				continue
			# otherwise, accumulate it
			current_warning = line
			state = STATE_REPORT_WARNING
			continue

	# If there were parsing issues, output them to debug
	if parsing:
		warnings.append("(Log parsing issues. Disregard unless something else is wrong.)")
		print_debug = True
		for l in parsing:
			debug(l)
	return (errors, warnings)


# If invoked from the command line, parse provided log file

if __name__ == '__main__':
	print_debug = True
	interactive = True
	try:
		logfilename = sys.argv[1]
		# logfile = open(logfilename, 'r') \
		# 		.read().decode(enc, 'ignore') \
		# 		.encode(enc, 'ignore').splitlines()
		if len(sys.argv) == 3:
			extra_file_ext = sys.argv[2].split(" ")
		data = open(logfilename,'r').read()
		(errors,warnings) = parse_tex_log(data)
		print ("")
		print ("Warnings:")
		for warn in warnings:
			print (warn.encode('UTF-8'))
		print ("")
		print ("Errors:")
		for err in errors:
			print (err.encode('UTF-8'))

	except Exception as e:
		import traceback
		traceback.print_exc()
########NEW FILE########
__FILENAME__ = texMacro
import sublime, sublime_plugin

macros = { 
'a' : '\\alpha',
'b' : '\\beta',
'c' : '\\chi',
'd' : '\\delta',
'e' : '\\epsilon',
'f' : '\\phi',
'g' : '\\gamma',
'h' : '\\eta',
'i' : '\\iota',
'j' : '\\phi',
'k' : '\\kappa',
'l' : '\\lambda',
'm' : '\\mu',
'n' : '\\nu',
'o' : '\\omicron',
'p' : '\\pi',
'q' : '\\theta',
'r' : '\\rho',
's' : '\\sigma',
't' : '\\tau',
'u' : '\\upsilon',
'v' : '\\psi',
'w' : '\\omega',
'x' : '\\xi',
'y' : '\\vartheta',
'z' : '\\zeta',
'A' : '\\forall',
'B' : 'FREE',
'C' : '\\Chi',
'D' : '\\Delta',
'E' : '\\exists',
'F' : '\\Phi',
'G' : '\\Gamma',
'H' : 'FREE',
'I' : '\\bigcap',
'J' : '\\Phi',
'K' : 'FREE',
'L' : '\\Lambda',
'M' : '\\int',
'N' : '\\sum',
'O' : '\\emptyset',
'P' : '\\Pi',
'Q' : '\\Theta',
'R' : 'FREE',
'S' : '\\Sigma',
'T' : '\\times',
'U' : '\\bigcup',
'V' : '\\Psi',
'W' : '\\Omega',
'X' : '\\Xi',
'Y' : '\\Upsilon',
'Z' : '\\sum',
'ge' : '\\geq',
'le' : '\\leq',
'la' : '\\leftarrow',
'ra' : '\\rightarrow',
'La' : '\\Leftarrow',
'Ra' : '\\Rightarrow',
'lra' : '\\leftrightarrow',
'up' : '\\uparrow',
'dn' : '\\downarrow',
'iff' : '\\Leftrightarrow',
'raa' : '\\rangle',
'laa' : '\\langle',
'lp' : '\\left(',
'rp' : '\\right)',
'lbk' : '\\left[',
'rbk' : '\\right]',
'lbr' : '\\left\{',
'rbr' : '\\right\}'
}

class tex_macroCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		currsel = self.view.sel()[0]
		currword = self.view.word(currsel)
		k = self.view.substr(currword)
		if macros.has_key(k):
			self.view.replace(edit, currword, macros[k])
		else:
			sublime.error_message("%s is not a valid TeX symbol shortcut" % (k,))

########NEW FILE########
__FILENAME__ = texSections
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
else:
    _ST3 = True


import sublime_plugin, os, os.path, re

# References and citations

spaces = {'part' : '', 'chapter' : '  ', 'section' : '    ',
		  'subsection' : '      ', 'subsubsection' : '        ',
		  'subsubsubsection' : '          '}

# ST2 note: we must keep the NamingConventionCommand style in the Python code,
# but the key bindings need "command": "naming_convention" 
#
# Also, for now must explicitly add key bindings in Preferences | User Key Bindings


class TexSectionsCommand(sublime_plugin.TextCommand):
	# ST2 note: (0) import sublime_plugin, not sublimeplugin
	#			(1) second arg is Edit, not View
	#               to get view, use self.view (?)
	#           (2) third arg is **args, not args
	#           (3) remember to change someMethod to some_method
	#           (4) panel not yet implemented :-(
	#			(5) to insert snippets (instead of insertInlineSnippet cmd):
	#				view.run_command('insert_snippet', {'contents' : 'TEXT'})
	#			(6) view.erase(region) becomes view.erase(edit, region) (?)
	#			(7) class names cannot have caps except for first one
	#				they must be: my_command_nameCommand
	#			(8) some commands, e.g. view.replace, require edit as param
	def run(self, edit, **args):
		# First get raw \section{xxx} lines
		# Capture the entire line beginning with our pattern, do processing later
		secRegions = self.view.find_all(r'^\\(begin\{frame\}|part|chapter|(?:sub)*section).*$')
		# Remove \section, etc and only leave spaces and titles
		# Handle frames separately
		# For sections, match \ followed by type followed by * or {, then
		# match everything. This captures the last }, which we'll remove
		secRe = re.compile(r'\\([^{*]+)\*?\{(.*)') # \, then anything up to a * or a {
		# Also, we need to remove \label{} statements
		labelRe = re.compile(r'\\label\{.*\}')
		# And also remove comments at the end of the line
		commentRe = re.compile(r'%.*$')
		# This is to match frames
		# Here we match the \begin{frame} command, with the optional [...]
		# and capture the rest of the line for further processing
		# TODO: find a way to capture \frametitle's on a different line
		frameRe = re.compile(r'\\begin\{frame\}(?:\[[^\]]\])?(.*$)')
		frameTitleRe = re.compile(r'\{(.*)\}')
		def prettify(s):
			s = commentRe.sub('',s).strip() # kill comments at the end of the line, blanks
			s = labelRe.sub('',s).strip() # kill label statements
			frameMatch = frameRe.match(s)
			if frameMatch:
				frame = frameMatch.group(1)
				frameTitleMatch = frameTitleRe.search(frame)
				if frameTitleMatch:
					return "frame: " + frameTitleMatch.group(1)
				else:
					return "frame: (untitled)"
			else:
				m = secRe.match(s)
				#print m.group(1,2)
				secTitle = m.group(2)
				if secTitle[-1]=='}':
					secTitle = secTitle[:-1]
				return spaces[m.group(1)]+secTitle
		prettySecs = [prettify(self.view.substr(reg)) for reg in secRegions]
		
		def onSelect(i):
			#print view.substr(secRegions[i])
			self.view.show(secRegions[i])
			s = self.view.sel() # RegionSet
			s.clear()
			s.add(secRegions[i])
			self.view.runCommand("moveTo bol")

		print (prettySecs)
		#self.view.window().show_select_panel(prettySecs, onSelect, None, 0)

########NEW FILE########
__FILENAME__ = toggle_auto
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
else:
    _ST3 = True


import sublime_plugin

# Toggle focus after jumping to PDF

class ToggleAutoCommand(sublime_plugin.TextCommand):
	def run(self, edit, which, **args):
		print ("Toggling Auto " + which)
		s = sublime.load_settings("LaTeXTools.sublime-settings")
		prefs_auto = s.get(which+"_auto_trigger", True)
        
		if self.view.settings().get(which + " auto trigger",prefs_auto):
			self.view.settings().set(which + " auto trigger", False)
			sublime.status_message(which + " auto trigger OFF")
			print (which + " auto OFF")
		else:
			self.view.settings().set(which + " auto trigger", True)
			sublime.status_message(which + " auto trigger ON")
			print (which + " auto ON")


########NEW FILE########
__FILENAME__ = toggle_focus
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
else:
    _ST3 = True


import sublime_plugin

# Toggle focus after jumping to PDF

class toggle_focusCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		s = sublime.load_settings("LaTeXTools.sublime-settings")
		prefs_keep_focus = s.get("keep_focus", True)

		if self.view.settings().get("keep focus",prefs_keep_focus):
			self.view.settings().set("keep focus", False)
			sublime.status_message("Focus PDF")
			print ("Focus PDF")
		else:
			self.view.settings().set("keep focus", True)
			sublime.status_message("Focus editor")
			print ("Focus ST2")


########NEW FILE########
__FILENAME__ = toggle_fwdsync
# ST2/ST3 compat
from __future__ import print_function 
import sublime
if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
else:
    _ST3 = True


import sublime, sublime_plugin

# Toggle forward syncing to PDF after compiling

class toggle_fwdsyncCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		s = sublime.load_settings("LaTeXTools.sublime-settings")
		prefs_forward_sync = s.get("forward_sync", True)

		if self.view.settings().get("forward_sync",prefs_forward_sync):
			self.view.settings().set("forward_sync", False)
			sublime.status_message("Do not forward sync PDF (keep current position)")
			print ("Do not forward sync PDF")
		else:
			self.view.settings().set("forward_sync", True)
			sublime.status_message("Forward sync PDF after compiling")
			print ("Forward sync PDF")


########NEW FILE########
__FILENAME__ = toggle_show
import sublime, sublime_plugin

# Show current toggles and prefs

class toggle_showCommand(sublime_plugin.TextCommand):
	def run(self, edit, **args):
		s = sublime.load_settings("LaTeXTools.sublime-settings")
		prefs_keep_focus = s.get("keep_focus", "(default)")
		prefs_forward_sync = s.get("forward_sync", "(default)")
		prefs_auto_ref = s.get("ref_auto_trigger", "(default)")
		prefs_auto_cite = s.get("cite_auto_trigger", "(default)")
		keep_focus = self.view.settings().get("keep focus","undefined")
		forward_sync = self.view.settings().get("forward_sync","undefined")
		auto_ref = self.view.settings().get("ref auto trigger", "undefined")
		auto_cite = self.view.settings().get("cite auto trigger", "undefined")


		sublime.status_message("Keep focus: pref %s toggle %s         Forward sync: pref %s toggle %s         Auto ref: pref %s toggle %s         Auto cite: pref %s toggle %s" 
			% (prefs_keep_focus, keep_focus, prefs_forward_sync, forward_sync, prefs_auto_ref, auto_ref,prefs_auto_cite,auto_cite))

########NEW FILE########
__FILENAME__ = viewPDF
# ST2/ST3 compat
from __future__ import print_function
import sublime
if sublime.version() < '3000':
	# we are on ST2 and Python 2.X
	_ST3 = False
	import getTeXRoot
else:
	_ST3 = True
	from . import getTeXRoot

import sublime_plugin, os, os.path, platform
from subprocess import Popen


# View PDF file corresonding to TEX file in current buffer
# Assumes that the SumatraPDF viewer is used (great for inverse search!)
# and its executable is on the %PATH%
# Warning: we do not do "deep" safety checks (e.g. see if PDF file is old)

class View_pdfCommand(sublime_plugin.WindowCommand):
	def run(self):
		s = sublime.load_settings("LaTeXTools.sublime-settings")
		prefs_keep_focus = s.get("keep_focus", True)
		prefs_lin = s.get("linux")

		view = self.window.active_view()
		texFile, texExt = os.path.splitext(view.file_name())
		if texExt.upper() != ".TEX":
			sublime.error_message("%s is not a TeX source file: cannot view." % (os.path.basename(view.file_name()),))
			return
		quotes = ""# \"" MUST CHECK WHETHER WE NEED QUOTES ON WINDOWS!!!
		root = getTeXRoot.get_tex_root(view)

		rootFile, rootExt = os.path.splitext(root)
		pdfFile = quotes + rootFile + '.pdf' + quotes
		s = platform.system()
		script_path = None
		if s == "Darwin":
			# for inverse search, set up a "Custom" sync profile, using
			# "subl" as command and "%file:%line" as argument
			# you also have to put a symlink to subl somewhere on your path
			# Also check the box "check for file changes"
			viewercmd = ["open", "-a", "Skim"]
		elif s == "Windows":
			# with new version of SumatraPDF, can set up Inverse 
			# Search in the GUI: under Settings|Options...
			# Under "Set inverse search command-line", set:
			# sublime_text "%f":%l
			viewercmd = ["SumatraPDF", "-reuse-instance"]		
		elif s == "Linux":
			# the required scripts are in the 'evince' subdir
			script_path = os.path.join(sublime.packages_path(), 'LaTeXTools', 'evince')
			ev_sync_exec = os.path.join(script_path, 'evince_sync') # so we get inverse search
			# Get python binary if set in preferences:
			py_binary = prefs_lin["python2"] or 'python'
			sb_binary = prefs_lin["sublime"] or 'sublime-text'
			viewercmd = ['sh', ev_sync_exec, py_binary, sb_binary]
		else:
			sublime.error_message("Platform as yet unsupported. Sorry!")
			return	
		print (viewercmd + [pdfFile])
		try:
			Popen(viewercmd + [pdfFile], cwd=script_path)
		except OSError:
			sublime.error_message("Cannot launch Viewer. Make sure it is on your PATH.")

			

########NEW FILE########
