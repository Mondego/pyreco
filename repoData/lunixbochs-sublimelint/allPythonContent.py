__FILENAME__ = commands
import sublime
import sublime_plugin
from lint import persist

def error_command(f):
	def run(self, edit, **kwargs):
		vid = self.view.id()
		if vid in persist.errors and persist.errors[vid]:
			f(self, self.view, persist.errors[vid], **kwargs)

	return run

def select_line(view, line):
	sel = view.sel()
	point = view.text_point(line, 0)
	sel.clear()
	sel.add(view.line(point))

class sublimelint_next_error(sublime_plugin.TextCommand):
	@error_command
	def run(self, view, errors, direction=1):
		self.view.run_command('single_selection')
		sel = view.sel()
		if len(sel) == 0:
			sel.add((0, 0))

		line = view.rowcol(sel[0].a)[0]
		errors = list(errors)
		if line in errors: errors.remove(line)
		errors = sorted(errors + [line])

		i = errors.index(line) + direction
		if i >= len(errors):
			i -= len(errors)

		select_line(view, errors[i])
		view.show_at_center(sel[0])

class sublimelint_all_errors(sublime_plugin.TextCommand):
	@error_command
	def run(self, view, errors):
		options = []
		option_to_line = []

		for lineno, messages in sorted(errors.items()):
			line = view.substr(
				view.full_line(view.text_point(lineno, 0))
			)
			while messages:
				option_to_line.append(lineno)
				options.append(
					[("%i| %s" % (lineno + 1, line.strip())).encode('ascii', 'replace')] +
					[m.encode('ascii', 'replace') for m in messages[:2]]
				)

				messages = messages[2:]

		def center_line(i):
			if i != -1:
				select_line(view, option_to_line[i])
				view.show_at_center(view.sel()[0])

		view.window().show_quick_panel(options, center_line, sublime.MONOSPACE_FONT)

########NEW FILE########
__FILENAME__ = c
import os

from lint.linter import Linter
from lint.util import find

def find_includes(filename):
    includes = []
    if filename:
        parent = os.path.dirname(filename)
        includes.append('-I' + parent)
        inc = find(parent, 'include')
        if inc:
            includes.append('-I' + inc)

    return includes


class C(Linter):
    language = 'c'
    cmd = ('clang', '-xc', '-fsyntax-only', '-std=c99', '-Werror',
        '-pedantic')
    regex = (
        r'^<stdin>:(?P<line>\d+):(?P<col>\d+):'
        r'(?:(?P<ranges>[{}0-9:\-]+):)?\s+'
        r'(?P<error>.+)'
    )

    def communicate(self, cmd, code):
        cmd += ('-',) + tuple(find_includes(self.filename))
        return super(C, self).communicate(cmd, code)

class CPP(C):
    language = 'c++'
    cmd = ('clang++', '-xc++', '-fsyntax-only', '-std=c++11', '-Werror',
        '-pedantic')

########NEW FILE########
__FILENAME__ = eclim
import json
import os
import tempfile

from lint.linter import Linter
from lint.util import communicate, find

class Java(Linter):
    language = 'java'
    cmd = ('eclim', '-command', 'java_src_update')
    regex = r'.'

    def communicate(self, cmd, code):
        project = find(os.path.dirname(self.filename), '.project', True)
        if not project:
            return

        filename = self.filename.replace(project, '', 1).lstrip(os.sep)
        project = os.path.basename(project)

        # can't stdin or temp use file - hack time?
        # this *could* become a tmp directory
        # but I'd need to know all files to copy
        # from the source project
        tmp = tempfile.mktemp()
        os.rename(self.filename, tmp)
        # at least we get some inode protection on posix
        inode = None

        with open(self.filename, 'wb') as f:
            f.write(code)
            if os.name == 'posix':
                inode = os.stat(self.filename).st_ino

        try:
            cmd = cmd + ('-p', project, '-f', filename, '-v')
            output = communicate(cmd, '')
        finally:
            if inode is not None:
                new_inode = os.stat(self.filename).st_ino
                if new_inode != inode:
                    # they saved over our tmp file, bail
                    return output

            os.unlink(self.filename)
            os.rename(tmp, self.filename)

        return output

    def find_errors(self, output):
        try:
            obj = json.loads(output)
            for item in obj:
                # TODO: highlight warnings in a different color?
                # warning = item['warning']
                line, col = item['line']-1, item['column']-1
                message = item['message']
                yield True, line, col, message, None
        except Exception:
            error = 'eclim error'
            if 'Connection refused' in output:
                error += ' Connection Refused'
            yield True, 0, None, error, None
            # maybe do this on line one?
            # yield {"eclim_exception": str(e)}

########NEW FILE########
__FILENAME__ = extras
# extras.py - sublimelint plugin for simple external linters

from lint.linter import Linter
import os

class Coffee(Linter):
	language = 'coffeescript'
	cmd = ('coffee', '--compile', '--stdio')
	regex = r'^[A-Za-z]+: (?P<error>.+) on line (?P<line>\d+)'

class CSS(Linter):
	language = 'css'
	cmd = ('csslint',)
	regex = (
		r'^\d+: (?P<type>(error|warning)) at line (?P<line>\d+), col (?P<col>\d+)$\W'
		r'^(?P<error>.*)$'
	)
	multiline = True

	def communicate(self, cmd, code):
		return self.tmpfile(cmd, code, suffix='.css')

class HAML(Linter):
	language = 'ruby haml'
	cmd = ('haml', '-c')
	regex = r'^.*line (?P<line>\d+):\s*(?P<error>.+)$'

# this doesn't work very well with projects/imports
# class Java(Linter):
# 	language = 'java'
# 	cmd = ('javac', '-Xlint')
# 	regex = r'^[^:]+:(?P<line>\d+): (?P<error>.*)$'
# 
# 	def communicate(self, *args):
# 		return self.tmpfile(*args, suffix='.java')

class JavaScript(Linter):
	language = 'javascript'
	cmd = ('jsl', '-stdin')
	regex = r'^\((?P<line>\d+)\):\s+(?P<error>.+)'

class Lua(Linter):
	language = 'lua'
	cmd = ('luac', '-p')
	regex = '^luac: [^:]+:(?P<line>\d+): (?P<error>.+?)(?P<near> near .+)?'

	def communicate(self, cmd, code):
		return self.tmpfile(cmd, code, suffix='.lua')

class Nasm(Linter):
	language = 'x86 assembly'
	cmd = ('nasm', '-X', 'gnu', '-I.', '-o', os.devnull)
	regex = r'^[^:]+:(?P<line>\d+): (?P<error>.*)$'

	def communicate(self, cmd, code):
		return self.tmpfile(cmd, code, suffix='.asm')

class Perl(Linter):
	language = 'perl'
	cmd = ('perl', '-c')
	regex = r'(?P<error>.+?) at .+? line (?P<line>\d+)(, near "(?P<near>.+?)")?'

class PHP(Linter):
	language = ('php', 'html')
	cmd = ('php', '-l', '-d display_errors=On')
	regex = r'^Parse error:\s*(?P<type>parse|syntax) error,?\s*(?P<error>.+?)?\s+in\s+.+?\s*line\s+(?P<line>\d+)'

	def match_error(self, r, line):
		match, row, col, error, near = super(PHP, self).match_error(r, line)

		if match and match.group('type') == 'parse' and not error:
			error = 'parse error'

		return match, row, col, error, near

class Ruby(Linter):
	language = 'ruby'
	cmd = ('ruby', '-wc')
	regex = r'^.+:(?P<line>\d+):\s+(?P<error>.+)'

class XML(Linter):
	language = 'xml'
	cmd = ('xmllint', '-noout', '-')
	regex = r'^.+:(?P<line>\d+):\s+(parser error : )?(?P<error>.+)'

########NEW FILE########
__FILENAME__ = go
import os
import shlex
from lint.linter import Linter

class Golang(Linter):
	language = 'go'
	cmd = ('go', 'build', '-gcflags', '-e -o ' + os.devnull)
	# can't use this calling method because compiler name changes
	# cmd = ('go', 'tool', '6g', '-e', '-o', os.devnull)
	regex = r'.+?:(?P<line>\d+): (?P<error>.+)'

	def communicate(self, cmd, code):
		posix = (os.name == 'posix')
		if not self.filename:
			tools = self.popen(('go', 'tool')).communicate()[0].split('\n')
			for compiler in ('6g', '8g'):
				if compiler in tools:
					return self.tmpfile(('go', 'tool', compiler, '-e', '-o', os.devnull), code, suffix='.go')

		else:
			path = os.path.split(self.filename)[0]
			cwd = os.getcwd()
			os.chdir(path)
			out = self.popen(('go', 'build', '-n')).communicate()
			# might have an error determining packages, return if so
			if out[1].strip(): return out[1]

			cmds = out[0]
			for line in cmds.split('\n'):
				if line:
					compiler = os.path.splitext(
						os.path.split(
							shlex.split(line, posix=posix)[0]
						)[1]
					)[0]

					if compiler in ('6g', '8g'):
						break
			else:
				return

			args = shlex.split(line, posix=posix)
			files = [arg for arg in args if arg.startswith(('./', '.\\'))]

			answer = self.tmpdir(cmd, files, code)

			os.chdir(cwd)
			return answer

########NEW FILE########
__FILENAME__ = python
# python.py - Lint checking for Python
# input: a filename and the contents of a Python source file
# output: a list of line numbers to outline, offsets to highlight, and error messages
#
# todo:
# * fix regex for variable names inside strings (quotes)
#

from _pyflakes import check, messages, OffsetError, PythonError
from lint.linter import Linter

class Python(Linter):
	language = 'python'

	def lint(self, code):
		self.check(code)

	def check(self, code, filename='untitled'):
		stripped_lines = []
		good_lines = []
		lines = code.split('\n')
		for i in xrange(len(lines)):
			line = lines[i]
			if not line.strip() or line.strip().startswith('#'):
				stripped_lines.append(i)
			else:
				good_lines.append(line)
			
		text = '\n'.join(good_lines)
		errors = check(text, filename)

		def underlineWord(lineno, word):
			regex = r'((and|or|not|if|elif|while|in)\s+|[+\-*^%%<>=\(\{])*\s*(?P<underline>[\w\.]*%s[\w]*)' % (word)
			self.highlight.regex(lineno, regex, word)
		
		def underlineImport(lineno, word):
			linematch = '(from\s+[\w_\.]+\s+)?import\s+(?P<match>[^#;]+)'
			regex = '(^|\s+|,\s*|as\s+)(?P<underline>[\w]*%s[\w]*)' % word
			self.highlight.regex(lineno, regex, word, linematch)
		
		def underlineForVar(lineno, word):
			regex = 'for\s+(?P<underline>[\w]*%s[\w*])' % word
			self.highlight.regex(lineno, regex, word)
		
		def underlineDuplicateArgument(lineno, word):
			regex = 'def [\w_]+\(.*?(?P<underline>[\w]*%s[\w]*)' % word
			self.highlight.regex(lineno, regex, word)

		for error in errors:
			# we need to adjust line numbers in the error
			# to make up for stripping blank lines earlier
			orig_lineno = None
			if hasattr(error, 'orig_lineno'):
				orig_lineno = error.orig_lineno - 1

			error.lineno -= 1
			for i in stripped_lines:
				if error.lineno >= i:
					error.lineno += 1

				if orig_lineno is not None:
					if orig_lineno >= i:
						orig_lineno += 1

			if orig_lineno is not None:
				error.orig_lineno = orig_lineno
				error.message_args = (error.name, int(error.orig_lineno) + 1)

				new = str(error)
				if isinstance(error, messages.UndefinedLocal):
					new = (
						'local variable %r (referenced on line %r) '
						'assigned after first reference' % (
							error.name, error.lineno + 1
					))
				else:
					new = new.replace(
						'from line %r' % (orig_lineno + 1),
						'on line %r' % (error.lineno + 1)
					)

				self.error(orig_lineno, new)

			self.error(error.lineno, error)
			if isinstance(error, OffsetError):
				self.highlight.range(error.lineno, error.offset)

			elif isinstance(error, PythonError):
				pass

			elif isinstance(error, messages.UnusedImport):
				underlineImport(error.lineno, error.name)
			
			elif isinstance(error, messages.RedefinedWhileUnused):
				underlineWord(error.lineno, error.name)

			elif isinstance(error, messages.ImportShadowedByLoopVar):
				underlineForVar(error.lineno, error.name)

			elif isinstance(error, messages.ImportStarUsed):
				underlineImport(error.lineno, '\*')

			elif isinstance(error, messages.UndefinedName):
				underlineWord(error.lineno, error.name)

			elif isinstance(error, messages.UndefinedExport):
				underlineWord(error.lineno, error.name)

			elif isinstance(error, messages.UndefinedLocal):
				underlineWord(error.lineno, error.name)

			elif isinstance(error, messages.DuplicateArgument):
				underlineDuplicateArgument(error.lineno, error.name)

			elif isinstance(error, messages.RedefinedFunction):
				underlineWord(error.lineno, error.name)

			elif isinstance(error, messages.LateFutureImport):
				pass

			elif isinstance(error, messages.UnusedVariable):
				underlineWord(error.lineno, error.name)

			else:
				print 'SublimeLint (Python): Oops, we missed an error type!'

########NEW FILE########
__FILENAME__ = todo
from lint.linter import Linter

class TODO(Linter):
	scope = 'string'
	selector = 'comment'
	outline = False

	@classmethod
	def can_lint(cls, language):
		return True

	def lint(self, code):
		lines = code.split('\n')
		for i in xrange(len(lines)):
			if 'TODO' in lines[i]:
				todo = lines[i].index('TODO')
				self.highlight.range(i, todo, 4)
				self.error(i,
					lines[i].split('TODO', 1)[1].lstrip(': ') or 'TODO'
				)

# TODO

# TODO

########NEW FILE########
__FILENAME__ = _pyflakes
# pyflakes.py - Python code linting
# This specific module is a derivative of PyFlakes and part of the SublimeLint project.
# SublimeLint is (c) 2012 Ryan Hileman and licensed under the MIT license.
# URL: https://github.com/lunixbochs/sublimelint
#
# The original copyright notices for this file/project follows:
#
# (c) 2005-2008 Divmod, Inc.
# See LICENSE file for details
#
# The LICENSE file is as follows:
#
# Copyright (c) 2005 Divmod, Inc., http://www.divmod.com/
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import sys

import __builtin__
import os.path
import compiler
from compiler import ast

class messages:
	class Message(object):
		message = ''
		message_args = ()
		def __init__(self, filename, lineno):
			self.filename = filename
			self.lineno = lineno
		def __str__(self):
			return self.message % self.message_args


	class UnusedImport(Message):
		message = '%r imported but unused'
		def __init__(self, filename, lineno, name):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.message_args = (name,)


	class RedefinedWhileUnused(Message):
		message = 'redefinition of unused %r from line %r'
		def __init__(self, filename, lineno, name, orig_lineno):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.orig_lineno = orig_lineno
			self.message_args = (name, orig_lineno)


	class ImportShadowedByLoopVar(Message):
		message = 'import %r from line %r shadowed by loop variable'
		def __init__(self, filename, lineno, name, orig_lineno):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.orig_lineno = orig_lineno
			self.message_args = (name, orig_lineno)


	class ImportStarUsed(Message):
		message = "'from %s import *' used; unable to detect undefined names"
		def __init__(self, filename, lineno, modname):
			messages.Message.__init__(self, filename, lineno)
			self.modname = modname
			self.message_args = (modname,)


	class UndefinedName(Message):
		message = 'undefined name %r'
		def __init__(self, filename, lineno, name):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.message_args = (name,)



	class UndefinedExport(Message):
		message = 'undefined name %r in __all__'
		def __init__(self, filename, lineno, name):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.message_args = (name,)



	class UndefinedLocal(Message):
		message = "local variable %r (defined in enclosing scope on line %r) referenced before assignment"
		def __init__(self, filename, lineno, name, orig_lineno):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.orig_lineno = orig_lineno
			self.message_args = (name, orig_lineno)


	class DuplicateArgument(Message):
		message = 'duplicate argument %r in function definition'
		def __init__(self, filename, lineno, name):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.message_args = (name,)


	class RedefinedFunction(Message):
		message = 'redefinition of function %r from line %r'
		def __init__(self, filename, lineno, name, orig_lineno):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.orig_lineno = orig_lineno
			self.message_args = (name, orig_lineno)


	class LateFutureImport(Message):
		message = 'future import(s) %r after other statements'
		def __init__(self, filename, lineno, names):
			messages.Message.__init__(self, filename, lineno)
			self.names = names
			self.message_args = (names,)


	class UnusedVariable(Message):
		"""
		Indicates that a variable has been explicity assigned to but not actually
		used.
		"""

		message = 'local variable %r is assigned to but never used'
		def __init__(self, filename, lineno, name):
			messages.Message.__init__(self, filename, lineno)
			self.name = name
			self.message_args = (name,)

class Binding(object):
	"""
	Represents the binding of a value to a name.

	The checker uses this to keep track of which names have been bound and
	which names have not. See L{Assignment} for a special type of binding that
	is checked with stricter rules.

	@ivar used: pair of (L{Scope}, line-number) indicating the scope and
				line number that this binding was last used
	"""

	def __init__(self, name, source):
		self.name = name
		self.source = source
		self.used = False


	def __str__(self):
		return self.name


	def __repr__(self):
		return '<%s object %r from line %r at 0x%x>' % (self.__class__.__name__,
														self.name,
														self.source.lineno,
														id(self))

class UnBinding(Binding):
	'''Created by the 'del' operator.'''



class Importation(Binding):
	"""
	A binding created by an import statement.

	@ivar fullName: The complete name given to the import statement,
		possibly including multiple dotted components.
	@type fullName: C{str}
	"""
	def __init__(self, name, source):
		self.fullName = name
		name = name.split('.')[0]
		super(Importation, self).__init__(name, source)



class Argument(Binding):
	"""
	Represents binding a name as an argument.
	"""



class Assignment(Binding):
	"""
	Represents binding a name with an explicit assignment.

	The checker will raise warnings for any Assignment that isn't used. Also,
	the checker does not consider assignments in tuple/list unpacking to be
	Assignments, rather it treats them as simple Bindings.
	"""



class FunctionDefinition(Binding):
	pass



class ExportBinding(Binding):
	"""
	A binding created by an C{__all__} assignment.  If the names in the list
	can be determined statically, they will be treated as names for export and
	additional checking applied to them.

	The only C{__all__} assignment that can be recognized is one which takes
	the value of a literal list containing literal strings.  For example::

		__all__ = ["foo", "bar"]

	Names which are imported and not otherwise used but appear in the value of
	C{__all__} will not have an unused import warning reported for them.
	"""
	def names(self):
		"""
		Return a list of the names referenced by this binding.
		"""
		names = []
		if isinstance(self.source, ast.List):
			for node in self.source.nodes:
				if isinstance(node, ast.Const):
					names.append(node.value)
		return names



class Scope(dict):
	importStarred = False       # set to True when import * is found


	def __repr__(self):
		return '<%s at 0x%x %s>' % (self.__class__.__name__, id(self), dict.__repr__(self))


	def __init__(self):
		super(Scope, self).__init__()



class ClassScope(Scope):
	pass



class FunctionScope(Scope):
	"""
	I represent a name scope for a function.

	@ivar globals: Names declared 'global' in this function.
	"""
	def __init__(self):
		super(FunctionScope, self).__init__()
		self.globals = {}



class ModuleScope(Scope):
	pass


# Globally defined names which are not attributes of the __builtin__ module.
_MAGIC_GLOBALS = ['__file__', '__builtins__']



class Checker(object):
	"""
	I check the cleanliness and sanity of Python code.

	@ivar _deferredFunctions: Tracking list used by L{deferFunction}.  Elements
		of the list are two-tuples.  The first element is the callable passed
		to L{deferFunction}.  The second element is a copy of the scope stack
		at the time L{deferFunction} was called.

	@ivar _deferredAssignments: Similar to C{_deferredFunctions}, but for
		callables which are deferred assignment checks.
	"""

	nodeDepth = 0
	traceTree = False

	def __init__(self, tree, filename='(none)'):
		self._deferredFunctions = []
		self._deferredAssignments = []
		self.dead_scopes = []
		self.messages = []
		self.filename = filename
		self.scopeStack = [ModuleScope()]
		self.futuresAllowed = True
		self.handleChildren(tree)
		self._runDeferred(self._deferredFunctions)
		# Set _deferredFunctions to None so that deferFunction will fail
		# noisily if called after we've run through the deferred functions.
		self._deferredFunctions = None
		self._runDeferred(self._deferredAssignments)
		# Set _deferredAssignments to None so that deferAssignment will fail
		# noisly if called after we've run through the deferred assignments.
		self._deferredAssignments = None
		del self.scopeStack[1:]
		self.popScope()
		self.check_dead_scopes()


	def deferFunction(self, callable):
		'''
		Schedule a function handler to be called just before completion.

		This is used for handling function bodies, which must be deferred
		because code later in the file might modify the global scope. When
		`callable` is called, the scope at the time this is called will be
		restored, however it will contain any new bindings added to it.
		'''
		self._deferredFunctions.append((callable, self.scopeStack[:]))


	def deferAssignment(self, callable):
		"""
		Schedule an assignment handler to be called just after deferred
		function handlers.
		"""
		self._deferredAssignments.append((callable, self.scopeStack[:]))


	def _runDeferred(self, deferred):
		"""
		Run the callables in C{deferred} using their associated scope stack.
		"""
		for handler, scope in deferred:
			self.scopeStack = scope
			handler()


	def scope(self):
		return self.scopeStack[-1]
	scope = property(scope)

	def popScope(self):
		self.dead_scopes.append(self.scopeStack.pop())


	def check_dead_scopes(self):
		"""
		Look at scopes which have been fully examined and report names in them
		which were imported but unused.
		"""
		for scope in self.dead_scopes:
			export = isinstance(scope.get('__all__'), ExportBinding)
			if export:
				all = scope['__all__'].names()
				if os.path.split(self.filename)[1] != '__init__.py':
					# Look for possible mistakes in the export list
					undefined = set(all) - set(scope)
					for name in undefined:
						self.report(
							messages.UndefinedExport,
							scope['__all__'].source.lineno,
							name)
			else:
				all = []

			# Look for imported names that aren't used.
			for importation in scope.itervalues():
				if isinstance(importation, Importation):
					if not importation.used and importation.name not in all:
						self.report(
							messages.UnusedImport,
							importation.source.lineno,
							importation.name)


	def pushFunctionScope(self):
		self.scopeStack.append(FunctionScope())

	def pushClassScope(self):
		self.scopeStack.append(ClassScope())

	def report(self, messageClass, *args, **kwargs):
		self.messages.append(messageClass(self.filename, *args, **kwargs))

	def handleChildren(self, tree):
		for node in tree.getChildNodes():
			self.handleNode(node, tree)

	def handleNode(self, node, parent):
		node.parent = parent
		if self.traceTree:
			print '  ' * self.nodeDepth + node.__class__.__name__
		self.nodeDepth += 1
		nodeType = node.__class__.__name__.upper()
		if nodeType not in ('STMT', 'FROM'):
			self.futuresAllowed = False
		try:
			handler = getattr(self, nodeType)
			handler(node)
		finally:
			self.nodeDepth -= 1
		if self.traceTree:
			print '  ' * self.nodeDepth + 'end ' + node.__class__.__name__

	def ignore(self, node):
		pass

	STMT = PRINT = PRINTNL = TUPLE = LIST = ASSTUPLE = ASSATTR = \
	ASSLIST = GETATTR = SLICE = SLICEOBJ = IF = CALLFUNC = DISCARD = \
	RETURN = ADD = MOD = SUB = NOT = UNARYSUB = INVERT = ASSERT = COMPARE = \
	SUBSCRIPT = AND = OR = TRYEXCEPT = RAISE = YIELD = DICT = LEFTSHIFT = \
	RIGHTSHIFT = KEYWORD = TRYFINALLY = WHILE = EXEC = MUL = DIV = POWER = \
	FLOORDIV = BITAND = BITOR = BITXOR = LISTCOMPFOR = LISTCOMPIF = \
	AUGASSIGN = BACKQUOTE = UNARYADD = GENEXPR = GENEXPRFOR = GENEXPRIF = \
	IFEXP = handleChildren

	CONST = PASS = CONTINUE = BREAK = ELLIPSIS = ignore

	def addBinding(self, lineno, value, reportRedef=True):
		'''Called when a binding is altered.

		- `lineno` is the line of the statement responsible for the change
		- `value` is the optional new value, a Binding instance, associated
		  with the binding; if None, the binding is deleted if it exists.
		- if `reportRedef` is True (default), rebinding while unused will be
		  reported.
		'''
		if (isinstance(self.scope.get(value.name), FunctionDefinition)
					and isinstance(value, FunctionDefinition)):
			self.report(messages.RedefinedFunction,
						lineno, value.name, self.scope[value.name].source.lineno)

		if not isinstance(self.scope, ClassScope):
			for scope in self.scopeStack[::-1]:
				existing = scope.get(value.name)
				if (isinstance(existing, Importation)
						and not existing.used
						and (not isinstance(value, Importation) or value.fullName == existing.fullName)
						and reportRedef):

					self.report(messages.RedefinedWhileUnused,
								lineno, value.name, scope[value.name].source.lineno)

		if isinstance(value, UnBinding):
			try:
				del self.scope[value.name]
			except KeyError:
				self.report(messages.UndefinedName, lineno, value.name)
		else:
			self.scope[value.name] = value


	def WITH(self, node):
		"""
		Handle C{with} by checking the target of the statement (which can be an
		identifier, a list or tuple of targets, an attribute, etc) for
		undefined names and defining any it adds to the scope and by continuing
		to process the suite within the statement.
		"""
		# Check the "foo" part of a "with foo as bar" statement.  Do this no
		# matter what, since there's always a "foo" part.
		self.handleNode(node.expr, node)

		if node.vars is not None:
			self.handleNode(node.vars, node)

		self.handleChildren(node.body)


	def GLOBAL(self, node):
		"""
		Keep track of globals declarations.
		"""
		if isinstance(self.scope, FunctionScope):
			self.scope.globals.update(dict.fromkeys(node.names))

	def LISTCOMP(self, node):
		for qual in node.quals:
			self.handleNode(qual, node)
		self.handleNode(node.expr, node)

	GENEXPRINNER = LISTCOMP

	def FOR(self, node):
		"""
		Process bindings for loop variables.
		"""
		vars = []
		def collectLoopVars(n):
			if hasattr(n, 'name'):
				vars.append(n.name)
			else:
				for c in n.getChildNodes():
					collectLoopVars(c)

		collectLoopVars(node.assign)
		for varn in vars:
			if (isinstance(self.scope.get(varn), Importation)
					# unused ones will get an unused import warning
					and self.scope[varn].used):
				self.report(messages.ImportShadowedByLoopVar,
							node.lineno, varn, self.scope[varn].source.lineno)

		self.handleChildren(node)

	def NAME(self, node):
		"""
		Locate the name in locals / function / globals scopes.
		"""
		# try local scope
		importStarred = self.scope.importStarred
		try:
			self.scope[node.name].used = (self.scope, node.lineno)
		except KeyError:
			pass
		else:
			return

		# try enclosing function scopes

		for scope in self.scopeStack[-2:0:-1]:
			importStarred = importStarred or scope.importStarred
			if not isinstance(scope, FunctionScope):
				continue
			try:
				scope[node.name].used = (self.scope, node.lineno)
			except KeyError:
				pass
			else:
				return

		# try global scope

		importStarred = importStarred or self.scopeStack[0].importStarred
		try:
			self.scopeStack[0][node.name].used = (self.scope, node.lineno)
		except KeyError:
			if ((not hasattr(__builtin__, node.name))
					and node.name not in _MAGIC_GLOBALS
					and not importStarred):
				if (os.path.basename(self.filename) == '__init__.py' and
					node.name == '__path__'):
					# the special name __path__ is valid only in packages
					pass
				else:
					self.report(messages.UndefinedName, node.lineno, node.name)


	def FUNCTION(self, node):
		if getattr(node, "decorators", None) is not None:
			self.handleChildren(node.decorators)
		self.addBinding(node.lineno, FunctionDefinition(node.name, node))
		self.LAMBDA(node)

	def LAMBDA(self, node):
		for default in node.defaults:
			self.handleNode(default, node)

		def runFunction():
			args = []

			def addArgs(arglist):
				for arg in arglist:
					if isinstance(arg, tuple):
						addArgs(arg)
					else:
						if arg in args:
							self.report(messages.DuplicateArgument, node.lineno, arg)
						args.append(arg)

			self.pushFunctionScope()
			addArgs(node.argnames)
			for name in args:
				self.addBinding(node.lineno, Argument(name, node), reportRedef=False)
			self.handleNode(node.code, node)
			def checkUnusedAssignments():
				"""
				Check to see if any assignments have not been used.
				"""
				for name, binding in self.scope.iteritems():
					if (not binding.used and not name in self.scope.globals
						and isinstance(binding, Assignment)):
						self.report(messages.UnusedVariable,
									binding.source.lineno, name)
			self.deferAssignment(checkUnusedAssignments)
			self.popScope()

		self.deferFunction(runFunction)


	def CLASS(self, node):
		"""
		Check names used in a class definition, including its decorators, base
		classes, and the body of its definition.  Additionally, add its name to
		the current scope.
		"""
		if getattr(node, "decorators", None) is not None:
			self.handleChildren(node.decorators)
		for baseNode in node.bases:
			self.handleNode(baseNode, node)
		self.addBinding(node.lineno, Binding(node.name, node))
		self.pushClassScope()
		self.handleChildren(node.code)
		self.popScope()


	def ASSNAME(self, node):
		if node.flags == 'OP_DELETE':
			if isinstance(self.scope, FunctionScope) and node.name in self.scope.globals:
				del self.scope.globals[node.name]
			else:
				self.addBinding(node.lineno, UnBinding(node.name, node))
		else:
			# if the name hasn't already been defined in the current scope
			if isinstance(self.scope, FunctionScope) and node.name not in self.scope:
				# for each function or module scope above us
				for scope in self.scopeStack[:-1]:
					if not isinstance(scope, (FunctionScope, ModuleScope)):
						continue
					# if the name was defined in that scope, and the name has
					# been accessed already in the current scope, and hasn't
					# been declared global
					if (node.name in scope
							and scope[node.name].used
							and scope[node.name].used[0] is self.scope
							and node.name not in self.scope.globals):
						# then it's probably a mistake
						self.report(messages.UndefinedLocal,
									scope[node.name].used[1],
									node.name,
									scope[node.name].source.lineno)
						break

			if isinstance(node.parent,
						  (ast.For, ast.ListCompFor, ast.GenExprFor,
						   ast.AssTuple, ast.AssList)):
				binding = Binding(node.name, node)
			elif (node.name == '__all__' and
				  isinstance(self.scope, ModuleScope) and
				  isinstance(node.parent, ast.Assign)):
				binding = ExportBinding(node.name, node.parent.expr)
			else:
				binding = Assignment(node.name, node)
			if node.name in self.scope:
				binding.used = self.scope[node.name].used
			self.addBinding(node.lineno, binding)

	def ASSIGN(self, node):
		self.handleNode(node.expr, node)
		for subnode in node.nodes[::-1]:
			self.handleNode(subnode, node)

	def IMPORT(self, node):
		for name, alias in node.names:
			name = alias or name
			importation = Importation(name, node)
			self.addBinding(node.lineno, importation)

	def FROM(self, node):
		if node.modname == '__future__':
			if not self.futuresAllowed:
				self.report(messages.LateFutureImport, node.lineno, [n[0] for n in node.names])
		else:
			self.futuresAllowed = False

		for name, alias in node.names:
			if name == '*':
				self.scope.importStarred = True
				self.report(messages.ImportStarUsed, node.lineno, node.modname)
				continue
			name = alias or name
			importation = Importation(name, node)
			if node.modname == '__future__':
				importation.used = (self.scope, node.lineno)
			self.addBinding(node.lineno, importation)

class OffsetError(messages.Message):
	message = '%r at offset %r'
	def __init__(self, filename, lineno, text, offset):
		messages.Message.__init__(self, filename, lineno)
		self.offset = offset
		self.message_args = (text, offset)

class PythonError(messages.Message):
	message = '%r'
	def __init__(self, filename, lineno, text):
		messages.Message.__init__(self, filename, lineno)
		self.message_args = (text,)

def check(codeString, filename):
	codeString = codeString.rstrip()
	try:
		try:
			compile(codeString, filename, "exec")
		except MemoryError:
			# Python 2.4 will raise MemoryError if the source can't be
			# decoded.
			if sys.version_info[:2] == (2, 4):
				raise SyntaxError(None)
			raise
	except (SyntaxError, IndentationError), value:
		# print traceback.format_exc() # helps debug new cases
		msg = value.args[0]

		lineno, offset, text = value.lineno, value.offset, value.text

		# If there's an encoding problem with the file, the text is None.
		if text is None:
			# Avoid using msg, since for the only known case, it contains a
			# bogus message that claims the encoding the file declared was
			# unknown.
			if msg.startswith('duplicate argument'):
				arg = msg.split('duplicate argument ',1)[1].split(' ',1)[0].strip('\'"')
				error = messages.DuplicateArgument(filename, lineno, arg)
			else:
				error = PythonError(filename, lineno, msg)
		else:
			line = text.splitlines()[-1]

			if offset is not None:
				offset = offset - (len(text) - len(line))

			if offset is not None:
				error = OffsetError(filename, lineno, msg, offset)
			else:
				error = PythonError(filename, lineno, msg)

		return [error]
	except ValueError, e:
		return [PythonError(filename, 0, e.args[0])]
	else:
		# Okay, it's syntactically valid.  Now parse it into an ast and check
		# it.
		tree = compiler.parse(codeString)
		w = Checker(tree, filename)
		w.messages.sort(lambda a, b: cmp(a.lineno, b.lineno))
		return w.messages

# end pyflakes
########NEW FILE########
__FILENAME__ = highlight
import sublime
import re

class HighlightSet:
	def __init__(self):
		self.all = {}

	def add(self, h):
		if not h.scope in self.all:
			self.all[h.scope] = set()

		self.all[h.scope].add(h)

	def draw(self, view, prefix='lint'):
		for scope in self.all:
			highlight = Highlight(scope=scope)
			for h in self.all[scope]:
				highlight.update(h)

			highlight.draw(view, prefix=prefix)

	def clear(self, view, prefix='lint'):
		for scope in self.all:
			view.erase_regions('%s-%s-underline' % (prefix, scope))
			view.erase_regions('%s-%s-outline' % (prefix, scope))

class Highlight:
	def __init__(self, code='',
			draw_type=sublime.DRAW_EMPTY_AS_OVERWRITE|sublime.DRAW_OUTLINED,
			scope='keyword', outline=True):

		self.code = code
		self.draw_type = draw_type
		self.scope = scope
		self.outline = outline
		self.underlines = []
		self.lines = set()

		self.line_offset = 0
		self.char_offset = 0

		# find all the newlines, so we can look for line positions
		# without merging back into the main thread for APIs
		self.newlines = newlines = [0]
		last = -1
		while True:
			last = code.find('\n', last+1)
			if last == -1: break
			newlines.append(last+1)

		newlines.append(len(code))

	def full_line(self, line):
		a, b = self.newlines[line:line+2]
		return a, b + 1

	def range(self, line, pos, length=1):
		self.line(line)
		a, b = self.full_line(line)
		pos += a

		for i in xrange(length):
			self.underlines.append(sublime.Region(pos + i + self.char_offset))

	def regex(self, line, regex, word_match=None, line_match=None):
		self.line(line)
		offset = 0

		a, b = self.full_line(line)
		lineText = self.code[a:b]
		if line_match:
			match = re.match(line_match, lineText)
			if match:
				lineText = match.group('match')
				offset = match.start('match')
			else:
				return

		iters = re.finditer(regex, lineText)
		results = [(result.start('underline'), result.end('underline')) 
					for result in iters if
					not word_match or
					result.group('underline') == word_match]

		for start, end in results:
			self.range(line, start+offset, end-start)

	def near(self, line, near):
		self.line(line)
		a, b = self.full_line(line)
		text = self.code[a:b]

		start = text.find(near)
		if start != -1:
			self.range(line, start, len(near))

	def update(self, other):
		if self.outline:
			self.lines.update(other.lines)
		self.underlines.extend(other.underlines)

	def draw(self, view, prefix='lint'):
		if self.underlines:
			underlines = [sublime.Region(u.a, u.b) for u in self.underlines]
			view.add_regions('%s-%s-underline' % (prefix, self.scope), underlines, self.scope, self.draw_type)
		
		if self.lines and self.outline:
			outlines = [view.full_line(view.text_point(line, 0)) for line in self.lines]
			view.add_regions('%s-%s-outline' % (prefix, self.scope), outlines, self.scope, self.draw_type)

	def clear(self, view, prefix='lint'):
		view.erase_regions('%s-%s-underline' % (prefix, self.scope))
		view.erase_regions('%s-%s-outline' % (prefix, self.scope))

	def line(self, line):
		if self.outline:
			self.lines.add(line + self.line_offset)

	def shift(self, line, char):
		self.line_offset = line
		self.char_offset = char

########NEW FILE########
__FILENAME__ = linter
import sublime
import re
import persist
import util

from Queue import Queue

from highlight import Highlight

syntax_re = re.compile(r'/([^/]+)\.tmLanguage$')

class Tracker(type):
	def __init__(cls, name, bases, attrs):
		if bases:
			bases[-1].add_subclass(cls, name, attrs)

class Linter:
	__metaclass__ = Tracker
	language = ''
	cmd = ()
	regex = ''
	multiline = False
	flags = 0
	tab_size = 1
	
	scope = 'keyword'
	selector = None
	outline = True
	needs_api = False

	languages = {}
	linters = {}
	errors = None
	highlight = None

	def __init__(self, view, syntax, filename=None):
		self.view = view
		self.syntax = syntax
		self.filename = filename

		if self.regex:
			if self.multiline:
				self.flags |= re.MULTILINE

			self.regex = re.compile(self.regex, self.flags)

		self.highlight = Highlight(scope=self.scope)

	@property
	def settings(self):
		return self.__class__.lint_settings

	@classmethod
	def add_subclass(cls, sub, name, attrs):
		if name:
			plugins = persist.settings.get('plugins', {})
			sub.lint_settings = plugins.get(name, {})

			sub.name = name
			cls.languages[name] = sub

	@classmethod
	def assign(cls, view):
		'''
		find a linter for a specified view if possible, then add it to our mapping of view <--> lint class and return it
		each view has its own linter to make it feasible for linters to store persistent data about a view
		'''
		try:
			vid = view.id()
		except RuntimeError:
			pass

		settings = view.settings()
		syn = settings.get('syntax')
		if not syn:
			cls.remove(vid)
			return

		match = syntax_re.search(syn)

		if match:
			syntax, = match.groups()
		else:
			syntax = syn

		if syntax:
			if vid in cls.linters and cls.linters[vid]:
				if tuple(cls.linters[vid])[0].syntax == syntax:
					return

			linters = set()
			for name, entry in cls.languages.items():
				if entry.can_lint(syntax):
					linter = entry(view, syntax, view.file_name())
					linters.add(linter)

			if linters:
				cls.linters[vid] = linters
				return linters

		cls.remove(vid)

	@classmethod
	def remove(cls, vid):
		if vid in cls.linters:
			for linter in cls.linters[vid]:
				linter.clear()

			del cls.linters[vid]

	@classmethod
	def reload(cls, mod=None):
		'''
		reload all linters, optionally filtering by module
		'''
		plugins = persist.settings.get('plugins', {})
		for name, linter in cls.languages.items():
			linter.lint_settings = plugins.get(name, {})

		for id, linters in cls.linters.items():
			for linter in linters:
				if mod and linter.__module__ != mod:
					continue

				linter.clear()
				cls.linters[id].remove(linter)
				linter = cls.languages[linter.name](linter.view, linter.syntax, linter.filename)
				cls.linters[id].add(linter)
				linter.draw()

		return

	@classmethod
	def text(cls, view):
		return view.substr(sublime.Region(0, view.size())).encode('utf-8')

	@classmethod
	def lint_view(cls, view_id, filename, code, sections, callback):
		if view_id in cls.linters:
			selectors = Linter.get_selectors(view_id)

			linters = tuple(cls.linters[view_id])
			linter_text = (', '.join(l.name for l in linters))
			persist.debug('SublimeLint: `%s` as %s' % (filename or 'untitled', linter_text))
			for linter in linters:
				if linter.settings.get('disable'):
					continue

				if not linter.selector:
					linter.filename = filename
					linter.pre_lint(code)

			for sel, linter in selectors:
				if sel in sections:
					highlight = Highlight(code, scope=linter.scope, outline=linter.outline)
					errors = {}

					for line_offset, left, right in sections[sel]:
						highlight.shift(line_offset, left)
						linter.pre_lint(code[left:right], highlight=highlight)

						for line, error in linter.errors.items():
							errors[line+line_offset] = error

					linter.errors = errors

			# merge our result back to the main thread
			sublime.set_timeout(lambda: callback(linters[0].view, linters), 0)

	@classmethod
	def get_view(cls, view_id):
		if view_id in cls.linters:
			return tuple(cls.linters[view_id])[0].view

	@classmethod
	def get_linters(cls, view_id):
		if view_id in cls.linters:
			return tuple(cls.linters[view_id])

		return ()

	@classmethod
	def get_selectors(cls, view_id):
		return [(linter.selector, linter) for linter in cls.get_linters(view_id) if linter.selector]

	def pre_lint(self, code, highlight=None):
		self.errors = {}
		self.highlight = highlight or Highlight(code, scope=self.scope, outline=self.outline)

		if not code: return
		
		# if this linter needs the api, we want to merge back into the main thread
		# but stall this thread until it's done so we still have the return
		if self.needs_api:
			q = Queue()
			def callback():
				q.get()
				self.lint(code)
				q.task_done()

			q.put(1)
			sublime.set_timeout(callback, 1)
			q.join()
		else:
			self.lint(code)

	def lint(self, code):
		if not (self.language and self.cmd and self.regex):
			raise NotImplementedError

		output = self.communicate(self.cmd, code)
		if output:
			persist.debug('Output:', repr(output))

			for match, row, col, message, near in self.find_errors(output):
				if match:
					if row or row is 0:
						if col or col is 0:
							# adjust column numbers to match the linter's tabs if necessary
							if self.tab_size > 1:
								start, end = self.highlight.full_line(row)
								code_line = code[start:end]
								diff = 0
								for i in xrange(len(code_line)):
									if code_line[i] == '\t':
										diff += (self.tab_size - 1)

									if col - diff <= i:
										col = i
										break

							self.highlight.range(row, col)
						elif near:
							self.highlight.near(row, near)
						else:
							self.highlight.line(row)

					self.error(row, message)

	def draw(self, prefix='lint'):
		self.highlight.draw(self.view, prefix)

	def clear(self, prefix='lint'):
		self.highlight.clear(self.view, prefix)

	# helper methods

	@classmethod
	def can_lint(cls, language):
		language = language.lower()
		if cls.language:
			if language == cls.language:
				return True
			elif isinstance(cls.language, (tuple, list)) and language in cls.language:
				return True
			else:
				return False

	def error(self, line, error):
		self.highlight.line(line)

		error = str(error)
		if line in self.errors:
			self.errors[line].append(error)
		else:
			self.errors[line] = [error]

	def find_errors(self, output):
		if self.multiline:
			errors = self.regex.finditer(output)
			if errors:
				for error in errors:
					yield self.split_match(error)
			else:
				yield self.split_match(None)
		else:
			for line in output.splitlines():
				yield self.match_error(self.regex, line.strip())

	def split_match(self, match):
		if match:
			items = {'row':None, 'col':None, 'error':'', 'near':None}
			items.update(match.groupdict())
			error, row, col, near = [items[k] for k in ('error', 'line', 'col', 'near')]

			row = int(row) - 1
			if col:
				col = int(col) - 1

			return match, row, col, error, near

		return match, None, None, '', None

	def match_error(self, r, line):
		return self.split_match(r.match(line))

	# popen wrappers
	def communicate(self, cmd, code):
		return util.communicate(cmd, code)

	def tmpfile(self, cmd, code, suffix=''):
		return util.tmpfile(cmd, code, suffix)

	def tmpdir(self, cmd, files, code):
		return util.tmpdir(cmd, files, self.filename, code)

	def popen(self, cmd, env=None):
		return util.popen(cmd, env)

########NEW FILE########
__FILENAME__ = modules
# modules.py - loads and reloads plugin scripts from a folder

import os
import sys
import glob

import traceback
import persist

class Modules:
	def __init__(self, cwd, path):
		self.base = cwd
		self.path = path
		self.abspath = os.path.abspath(path)
		self.modules = {}

	def load(self, name):
		persist.debug('SublimeLint: loading `%s`' % name)
		pushd = os.getcwd()
		os.chdir(self.base)
		path = list(sys.path)

		sys.path.insert(0, self.path)

		mod = None
		try:
			__import__(name)

			# first, we get the actual module from sys.modules, not the base mod returned by __import__
			# second, we get an updated version of the module with reload() so development is easier
			mod = sys.modules[name] = reload(sys.modules[name])
		except:
			persist.debug('SublimeLint: error importing `%s`' % name)
			persist.debug('-'*20)
			persist.debug(traceback.format_exc())
			persist.debug('-'*20)

		if not mod:
			return

		self.modules[name] = mod

		# update module's __file__ with the absolute path so we know to reload it if Sublime Text saves that path
		mod.__file__ = os.path.abspath(mod.__file__).rstrip('co') # strip .pyc/.pyo to just .py

		sys.path = path
		os.chdir(pushd)

		return mod

	def reload(self, mod):
		name = mod.__name__
		if name in self.modules:
			return self.load(name)

	def load_all(self):
		pushd = os.getcwd()
		os.chdir(self.base)
		for mod in glob.glob('%s/*.py' % self.path):
			base, name = os.path.split(mod)
			name = name.split('.', 1)[0]
			if name.startswith('_'):
				continue

			self.load(name)

		os.chdir(pushd)
		return self

########NEW FILE########
__FILENAME__ = persist
import thread
import traceback
import time
import sublime

from Queue import Queue, Empty

class Daemon:
	running = False
	callback = None
	q = Queue()
	views = {}
	last_run = {}

	def __init__(self):
		self.settings = {}
		self.sub_settings = sublime.load_settings('SublimeLint.sublime-settings')
		self.sub_settings.add_on_change('lint-persist-settings', self.update_settings)

	def update_settings(self):
		settings = self.sub_settings.get('default')
		user = self.sub_settings.get('user')
		if user:
			settings.update(user)

		self.settings.clear()
		self.settings.update(settings)

		# reattach settings objects to linters
		import sys
		import linter
		linter = sys.modules.get('lint.linter') or linter
		if linter:
			linter.Linter.reload()

	def start(self, callback):
		self.callback = callback

		if self.running:
			self.q.put('reload')
			return
		else:
			self.running = True
			thread.start_new_thread(self.loop, ())

	def reenter(self, view_id):
		sublime.set_timeout(lambda: self.callback(view_id), 0)

	def loop(self):
		while True:
			try:
				try:
					item = self.q.get(True, 0.5)
				except Empty:
					for view_id, ts in self.views.items():
						if ts < time.time() - 0.5:
							self.last_run[view_id] = time.time()
							del self.views[view_id]
							self.reenter(view_id)
					
					continue

				if isinstance(item, tuple):
					view_id, ts = item
					if view_id in self.last_run and ts < self.last_run[view_id]:
						continue

					self.views[view_id] = ts

				elif isinstance(item, (int, float)):
					time.sleep(item)

				elif isinstance(item, basestring):
					if item == 'reload':
						self.printf('SublimeLint daemon detected a reload')
				else:
					self.printf('SublimeLint: Unknown message sent to daemon:', item)
			except:
				self.printf('Error in SublimeLint daemon:')
				self.printf('-'*20)
				self.printf(traceback.format_exc())
				self.printf('-'*20)

	def hit(self, view):
		self.q.put((view.id(), time.time()))

	def delay(self):
		self.q.put(0.01)

	def printf(self, *args):
		if not self.settings.get('debug'): return

		for arg in args:
			print arg,
		print

if not 'already' in globals():
	queue = Daemon()
	debug = queue.printf
	settings = queue.settings
	queue.update_settings()

	errors = {}
	already = True

########NEW FILE########
__FILENAME__ = util
import os
import shutil
import tempfile
import subprocess

import persist

def memoize(f):
	rets = {}

	def wrap(*args):
		if not args in rets:
			rets[args] = f(*args)

		return rets[args]

	wrap.__name__ = f.__name__
	return wrap

def climb(top):
    right = True
    while right:
        top, right = os.path.split(top)
        yield top

@memoize
def find(top, name, parent=False):
    for d in climb(top):
        target = os.path.join(d, name)
        if os.path.exists(target):
            if parent:
                return d

            return target

def extract_path(cmd, delim=':'):
	path = popen(cmd, os.environ).communicate()[0]
	path = path.split('__SUBL__', 1)[1].strip('\r\n')
	return ':'.join(path.split(delim))

def find_path(env):
	# find PATH using shell --login
	if 'SHELL' in env:
		shell_path = env['SHELL']
		shell = os.path.basename(shell_path)

		if shell in ('bash', 'zsh'):
			return extract_path(
				(shell_path, '--login', '-c', 'echo __SUBL__$PATH')
			)
		elif shell == 'fish':
			return extract_path(
				(shell_path, '--login', '-c', 'echo __SUBL__; for p in $PATH; echo $p; end'),
				'\n'
			)

	# guess PATH if we haven't returned yet
	split = env['PATH'].split(':')
	p = env['PATH']
	for path in (
		'/usr/bin', '/usr/local/bin',
		'/usr/local/php/bin', '/usr/local/php5/bin'
				):
		if not path in split:
			p += (':' + path)

	return p

@memoize
def create_environment():
	if os.name == 'posix':
		os.environ['PATH'] = find_path(os.environ)

	return os.environ

# popen methods
def communicate(cmd, code):
	out = popen(cmd)
	if out is not None:
		out = out.communicate(code)
		return (out[0] or '') + (out[1] or '')
	else:
		return ''


def tmpfile(cmd, code, suffix=''):
	if isinstance(cmd, basestring):
		cmd = cmd,

	f = tempfile.NamedTemporaryFile(suffix=suffix)
	f.write(code)
	f.flush()

	cmd = tuple(cmd) + (f.name,)
	out = popen(cmd)
	if out:
		out = out.communicate()
		return (out[0] or '') + (out[1] or '')
	else:
		return ''

def tmpdir(cmd, files, filename, code):
	filename = os.path.split(filename)[1]
	d = tempfile.mkdtemp()

	for f in files:
		try: os.makedirs(os.path.split(f)[0])
		except: pass

		target = os.path.join(d, f)
		if os.path.split(target)[1] == filename:
			# source file hasn't been saved since change, so update it from our live buffer
			f = open(target, 'wb')
			f.write(code)
			f.close()
		else:
			shutil.copyfile(f, target)

	os.chdir(d)
	out = popen(cmd)
	if out:
		out = out.communicate()
		out = (out[0] or '') + '\n' + (out[1] or '')
		
		# filter results from build to just this filename
		# no guarantee all languages are as nice about this as Go
		# may need to improve later or just defer to communicate()
		out = '\n'.join([
			line for line in out.split('\n') if filename in line.split(':', 1)[0]
		])
	else:
		out = ''

	shutil.rmtree(d, True)
	return out

def popen(cmd, env=None):
	if isinstance(cmd, basestring):
		cmd = cmd,

	info = None
	if os.name == 'nt':
		info = subprocess.STARTUPINFO()
		info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		info.wShowWindow = subprocess.SW_HIDE

	if env is None:
		env = create_environment()

	try:
		return subprocess.Popen(cmd, stdin=subprocess.PIPE,
			stdout=subprocess.PIPE, stderr=subprocess.PIPE,
			startupinfo=info, env=env)
	except OSError, err:
		persist.debug('SublimeLint: Error launching', repr(cmd))
		persist.debug('Error was:', err.strerror)

########NEW FILE########
__FILENAME__ = sublimelint
# sublimelint.py
# SublimeLint is a code linting support framework for Sublime Text 2
#
# Project: https://github.com/lunixbochs/sublimelint
# License: MIT

import sublime
import sublime_plugin

import os
import thread
import time
import json

from lint.modules import Modules
from lint.linter import Linter
from lint.highlight import HighlightSet
import lint.persist as persist

cwd = os.getcwd()

class SublimeLint(sublime_plugin.EventListener):
	def __init__(self, *args, **kwargs):
		sublime_plugin.EventListener.__init__(self, *args, **kwargs)

		self.loaded = set()
		self.linted = set()
		self.modules = Modules(cwd, 'languages').load_all()
		self.last_syntax = {}
		persist.queue.start(self.lint)

		# this gives us a chance to lint the active view on fresh install
		window = sublime.active_window()
		if window:
			sublime.set_timeout(
				lambda: self.on_activated(window.active_view()), 100
			)

		self.start = time.time()

	def lint(self, view_id):
		view = Linter.get_view(view_id)

		sections = {}
		for sel, _ in Linter.get_selectors(view_id):
			sections[sel] = []
			for result in view.find_by_selector(sel):
				sections[sel].append(
					(view.rowcol(result.a)[0], result.a, result.b)
				)

		if view is not None:
			filename = view.file_name()
			code = Linter.text(view)
			thread.start_new_thread(Linter.lint_view, (view_id, filename, code, sections, self.finish))

	def finish(self, view, linters):
		errors = {}
		highlights = HighlightSet()

		for linter in linters:
			if linter.highlight:
				highlights.add(linter.highlight)

			if linter.errors:
				errors.update(linter.errors)

		highlights.clear(view)
		highlights.draw(view)
		persist.errors[view.id()] = errors
		self.on_selection_modified(view)

	# helpers

	def hit(self, view):
		self.linted.add(view.id())
		if view.size() == 0:
			for l in Linter.get_linters(view.id()):
				l.clear()

			return

		persist.queue.hit(view)

	def check_syntax(self, view, lint=False):
		vid = view.id()
		syntax = view.settings().get('syntax')

		# syntax either has never been set or just changed
		if not vid in self.last_syntax or self.last_syntax[vid] != syntax:
			self.last_syntax[vid] = syntax

			# assign a linter, then maybe trigger a lint if we get one
			if Linter.assign(view) and lint:
				self.hit(view)

	# callins
	def on_modified(self, view):
		self.check_syntax(view)
		self.hit(view)

	def on_load(self, view):
		self.on_new(view)

	def on_activated(self, view):
		sublime.set_timeout(lambda: self.check_syntax(view, True), 50)

		view_id = view.id()
		if not view_id in self.linted:
			if not view_id in self.loaded:
				# it seems on_activated can be called before loaded on first start
				if time.time() - self.start < 5: return
				self.on_new(view)

			self.hit(view)

	def on_open_settings(self, view):
		# handle opening user preferences file
		if view.file_name():
			filename = view.file_name()
			dirname = os.path.basename(os.path.dirname(filename))
			if filename != 'SublimeLint.sublime-settings':
				return

			if dirname.lower() == 'sublimelint':
				return

			settings = persist.settings
			edit = view.begin_edit()
			view.replace(edit, sublime.Region(0, view.size()),
				json.dumps({'user': settings}, indent=4)
			)
			view.end_edit(edit)

	def on_new(self, view):
		self.on_open_settings(view)
		vid = view.id()
		self.loaded.add(vid)
		self.last_syntax[vid] = view.settings().get('syntax')
		Linter.assign(view)

	def on_post_save(self, view):
		# this will reload submodules if they are saved with sublime text
		for name, module in self.modules.modules.items():
			if os.name == 'posix' and (
				os.stat(module.__file__).st_ino == os.stat(view.file_name()).st_ino
			) or module.__file__ == view.file_name():
				self.modules.reload(module)
				Linter.reload(name)
				break

		# linting here doesn't matter, because we lint on load and on modify
		# self.hit(view)

	def on_selection_modified(self, view):
		vid = view.id()
		lineno = view.rowcol(view.sel()[0].end())[0]

		view.erase_status('sublimelint')
		if vid in persist.errors:
			errors = persist.errors[vid]
			if errors:
				plural = 's' if len(errors) > 1 else ''
				if lineno in errors:
					status = ''
					if plural:
						num = sorted(list(errors)).index(lineno) + 1
						status += '%i/%i errors: ' % (num, len(errors))

					# sublime statusbar can't hold unicode
					status += '; '.join(set(errors[lineno])).encode('ascii', 'replace')
				else:
					status = '%i error%s' % (len(errors), plural)

				view.set_status('sublimelint', status)

		persist.queue.delay()

########NEW FILE########
