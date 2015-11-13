__FILENAME__ = jedibackend
"""Elpy backend using the Jedi library.

This backend uses the Jedi library:

https://github.com/davidhalter/jedi

"""

import sys


from elpy.backends.nativebackend import get_source
from elpy.backends.nativebackend import NativeBackend


class JediBackend(NativeBackend):
    """The Jedi backend class.

    Implements the RPC calls we can pass on to Jedi. Also subclasses
    the native backend to provide methods Jedi does not provide, if
    any.

    """
    def __new__(cls):
        try:
            import jedi
        except:
            return None
        obj = super(JediBackend, cls).__new__(cls)
        obj.jedi = jedi
        return obj

    def __init__(self):
        super(JediBackend, self).__init__()
        self.name = "jedi"

    def rpc_get_completions(self, project_root, filename, source, offset):
        source = get_source(source)
        line, column = pos_to_linecol(source, offset)
        sys.path.append(project_root)
        try:
            script = self.jedi.Script(source, line, column, filename,
                                      encoding='utf-8')
            proposals = script.completions()
        finally:
            sys.path.pop()
        return [[proposal.complete, proposal.docstring()]
                for proposal in proposals]

    def rpc_get_definition(self, project_root, filename, source, offset):
        source = get_source(source)
        line, column = pos_to_linecol(source, offset)
        sys.path.append(project_root)
        try:
            script = self.jedi.Script(source, line, column, filename,
                                      encoding='utf-8')
            locations = script.goto_definitions()
            # goto_definitions() can return silly stuff like __builtin__
            # for int variables, so we fall back on goto() in those
            # cases. See issue #76.
            if (
                    locations and
                    locations[0].module_path is None
            ):
                locations = script.goto_assignments()
        finally:
            sys.path.pop()
        if not locations:
            return None
        else:
            loc = locations[-1]
            try:
                if loc.module_path:
                    with open(loc.module_path) as f:
                        offset = linecol_to_pos(f.read(),
                                                loc.line,
                                                loc.column)
            except IOError:
                return None
            return (loc.module_path, offset)

    def rpc_get_calltip(self, project_root, filename, source, offset):
        source = get_source(source)
        line, column = pos_to_linecol(source, offset)
        sys.path.append(project_root)
        try:
            script = self.jedi.Script(source, line, column, filename,
                                      encoding='utf-8')
            call = script.call_signatures()
            if call:
                call = call[0]
            else:
                call = None
        finally:
            sys.path.pop()
        if call is None:
            return None
        return "{0}({1})".format(call.name,
                                 ", ".join(param.description.strip()
                                           for param in call.params))

    def rpc_get_docstring(self, project_root, filename, source, offset):
        """Return a docstring for the symbol at offset.

        This uses the nativebackend, as apparently, Jedi does not know
        how to do this. It can do a completion and find docstrings for
        that, but not for the symbol at a location. Huh.

        """
        source = get_source(source)
        return super(JediBackend, self).rpc_get_docstring(project_root,
                                                          filename,
                                                          source,
                                                          offset)


# From the Jedi documentation:
#
#   line is the current line you want to perform actions on (starting
#   with line #1 as the first line). column represents the current
#   column/indent of the cursor (starting with zero). source_path
#   should be the path of your file in the file system.
#
# Now, why you'd offset a program to a piece of code in a string using
# line/column indeces is a bit beyond me. And even moreso, why you'd
# make lines one-based and columns zero-based is a complete mystery.
# But well, that's what it says.

def pos_to_linecol(text, pos):
    """Return a tuple of line and column for offset pos in text.

    Lines are one-based, columns zero-based.

    This is how Jedi wants it. Don't ask me why.

    """
    line_start = text.rfind("\n", 0, pos) + 1
    line = text.count("\n", 0, line_start) + 1
    col = pos - line_start
    return line, col


def linecol_to_pos(text, line, col):
    """Return the offset of this line and column in text.

    Lines are one-based, columns zero-based.

    This is how Jedi wants it. Don't ask me why.

    """
    nth_newline_offset = 0
    for i in range(line - 1):
        new_offset = text.find("\n", nth_newline_offset)
        if new_offset < 0:
            raise ValueError("Text does not have {0} lines."
                             .format(line))
        nth_newline_offset = new_offset + 1
    offset = nth_newline_offset + col
    if offset > len(text):
        raise ValueError("Line {0} column {1} is not within the text"
                         .format(line, col))
    return offset

########NEW FILE########
__FILENAME__ = nativebackend
"""Elpy backend using native Python methods.

This backend does not use any external packages, so should work even
if only the core Python library is available. This does make it
somewhat limited compared to the other backends.

On the other hand, this backend also serves as a root class for the
other backends, so they can fall back to the native method if the
specific solutions do not work.

"""

import io
import os
import pydoc
import re
import rlcompleter


class NativeBackend(object):
    """Elpy backend that uses native Python implementations.

    Works as a stand-alone backend or as a fallback for other
    backends.

    """

    def __init__(self):
        self.name = "native"

    def rpc_get_pydoc_documentation(self, symbol):
        """Get the Pydoc documentation for the given symbol.

        Uses pydoc and can return a string with backspace characters
        for bold highlighting.

        """
        try:
            return pydoc.render_doc(str(symbol),
                                    "Elpy Pydoc Documentation for %s",
                                    False)
        except (ImportError, pydoc.ErrorDuringImport):
            return None

    def rpc_get_completions(self, project_root, filename, source, offset):
        """Get completions for symbol at the offset.

        Wrapper around rlcompleter.

        """
        source = get_source(source)
        completer = rlcompleter.Completer()
        symbol, start, end = find_dotted_symbol_backward(source, offset)
        completions = []
        i = 0
        while True:
            res = completer.complete(symbol, i)
            if res is None:
                break
            completion = res[len(symbol):].rstrip("(")
            completions.append((completion, None))
            i += 1
        return completions

    def rpc_get_definition(self, project_root, filename, source, offset):
        """Get the location of the definition for the symbol at the offset.

        Not implemented in the native backend.

        """
        get_source(source)
        return None

    def rpc_get_calltip(self, project_root, filename, source, offset):
        """Get the calltip for the function at the offset.

        Not implemented in the native backend.

        """
        get_source(source)
        return None

    def rpc_get_docstring(self, project_root, filename, source, offset):
        """Get the docstring for the symbol at the offset.

        Uses pydoc and can return a string with backspace characters
        for bold highlighting.

        """
        source = get_source(source)
        symbol, start, end = find_dotted_symbol(source, offset)
        return self.rpc_get_pydoc_documentation(symbol)


# Helper functions

_SYMBOL_RX = re.compile("[A-Za-z0-9_]")
_DOTTED_SYMBOL_RX = re.compile("[A-Za-z0-9_.]")


def find_symbol_backward(source, offset, regexp=_SYMBOL_RX):
    """Find the Python symbol at offset in source.

    This will move backwards from offset until a non-symbol
    constituing character is found. It will NOT move forwards.

    """
    end = offset
    start = offset
    while (start > 0 and
           regexp.match(source[start - 1])):
        start -= 1
    return (source[start:end], start, end)


def find_dotted_symbol_backward(source, offset):
    """Find the Python symbol with dots at offset in source.

    This will move backwards from offset until a non-symbol
    constituing character is found. It will NOT move forwards.

    """
    return find_symbol_backward(source, offset,
                                _DOTTED_SYMBOL_RX)


def find_symbol(source, offset, regexp=_SYMBOL_RX):
    """Find the Python symbol at offset.

    This will move forward and backward from offset.

    """
    symbol, start, end = find_symbol_backward(source, offset,
                                              regexp)
    while (end < len(source) and
           regexp.match(source[end])):
        end += 1
    return (source[start:end], start, end)


def find_dotted_symbol(source, offset):
    """Find the dotted Python symbol at offset.

    This will move forward and backward from offset.

    """
    return find_symbol(source, offset, _DOTTED_SYMBOL_RX)


def get_source(fileobj):
    """Translate fileobj into file contents.

    fileobj is either a string or a dict. If it's a string, that's the
    file contents. If it's a string, then the filename key contains
    the name of the file whose contents we are to use.

    If the dict contains a true value for the key delete_after_use,
    the file should be deleted once read.

    """
    if not isinstance(fileobj, dict):
        return fileobj
    else:
        try:
            with io.open(fileobj["filename"], encoding="utf-8") as f:
                return f.read()
        finally:
            if fileobj.get('delete_after_use'):
                try:
                    os.remove(fileobj["filename"])
                except:
                    pass

########NEW FILE########
__FILENAME__ = ropebackend
"""Elpy backend using the Rope library.

This backend uses the Rope library:

http://rope.sourceforge.net/

"""
import os
import time
from functools import wraps

from elpy.backends.nativebackend import get_source
from elpy.backends.nativebackend import NativeBackend
import elpy.utils.pydocutils

VALIDATE_EVERY_SECONDS = 5
MAXFIXES = 5


class RopeBackend(NativeBackend):
    """The Rope backend class.

    Implements the RPC calls we can pass on to Rope. Also subclasses
    the native backend to provide methods Rope does not provide, if
    any.

    """

    def __init__(self):
        super(RopeBackend, self).__init__()
        self.name = "rope"
        self.projects = {}
        self.last_validation = {}

    def __new__(cls):
        values = cls.initialize()
        if values is None:
            return None
        obj = super(RopeBackend, cls).__new__(cls)
        obj.__dict__.update(values)
        return obj

    @classmethod
    def initialize(cls):
        try:
            from rope.contrib import codeassist
            from rope.base import project
            from rope.base import libutils
            from rope.base.exceptions import BadIdentifierError
            from rope.base.exceptions import ModuleSyntaxError
            from rope.contrib import findit
            patch_codeassist(codeassist)
            return {'codeassist': codeassist,
                    'projectlib': project,
                    'libutils': libutils,
                    'BadIdentifierError': BadIdentifierError,
                    'ModuleSyntaxError': ModuleSyntaxError,
                    'findit': findit
                    }
        except:
            return None

    def get_project(self, project_root):
        """Return a project object for the given path.

        This caches previously used project objects so they do not
        have to be re-created.

        """
        if project_root is None:
            raise ValueError("No project root is specified, "
                             "but required for Rope")
        if not os.path.isdir(project_root):
            return None
        project = self.projects.get(project_root)
        if project is None:
            prefs = dict(ignored_resources=['*.pyc', '*~', '.ropeproject',
                                            '.hg', '.svn', '_svn', '.git'],
                         python_files=['*.py'],
                         save_objectdb=False,
                         compress_objectdb=False,
                         automatic_soa=True,
                         soa_followed_calls=0,
                         perform_doa=True,
                         validate_objectdb=True,
                         max_history_items=32,
                         save_history=False,
                         compress_history=False,
                         indent_size=4,
                         extension_modules=[],
                         import_dynload_stdmods=True,
                         ignore_syntax_errors=False,
                         ignore_bad_imports=False)
            project = self.projectlib.Project(project_root,
                                              ropefolder=None,
                                              **prefs)

            self.projects[project_root] = project
        last_validation = self.last_validation.get(project_root, 0.0)
        now = time.time()
        if (now - last_validation) > VALIDATE_EVERY_SECONDS:
            project.validate()
            self.last_validation[project_root] = now
        return project

    def get_resource(self, project, filename):
        if filename is not None and os.path.exists(filename):
            return self.libutils.path_to_resource(project,
                                                  filename,
                                                  'file')
        else:
            return None

    def rpc_get_completions(self, project_root, filename, source, offset):
        source = get_source(source)
        project = self.get_project(project_root)
        resource = self.get_resource(project, filename)
        try:
            proposals = self.codeassist.code_assist(project, source, offset,
                                                    resource,
                                                    maxfixes=MAXFIXES)
            starting_offset = self.codeassist.starting_offset(source, offset)
        except self.ModuleSyntaxError:
            # Rope can't parse this file
            return []
        except IndentationError:
            # Rope can't parse this file
            return []
        except IndexError as e:
            # Bug in Rope, see #186
            return []
        prefixlen = offset - starting_offset
        return [[proposal.name[prefixlen:], proposal.get_doc()]
                for proposal in proposals]

    def rpc_get_definition(self, project_root, filename, source, offset):
        source = get_source(source)
        project = self.get_project(project_root)
        resource = self.get_resource(project, filename)
        # The find_definition call fails on an empty strings
        if source == '':
            return None

        try:
            location = self.findit.find_definition(project, source, offset,
                                                   resource, MAXFIXES)
        except (self.ModuleSyntaxError, IndentationError):
            # Rope can't parse this file
            return None

        if location is None:
            return None
        else:
            return (location.resource.real_path, location.offset)

    def rpc_get_calltip(self, project_root, filename, source, offset):
        source = get_source(source)
        offset = find_called_name_offset(source, offset)
        project = self.get_project(project_root)
        resource = self.get_resource(project, filename)
        try:
            return self.codeassist.get_calltip(project, source, offset,
                                               resource, MAXFIXES,
                                               remove_self=True)
        except (self.ModuleSyntaxError, IndentationError):
            # Rope can't parse this file
            return None
        except (self.BadIdentifierError, IndexError):
            # IndexError seems to be a bug in Rope. I don't know what
            # it causing it, exactly.
            return None

    def rpc_get_docstring(self, project_root, filename, source, offset):
        source = get_source(source)
        project = self.get_project(project_root)
        resource = self.get_resource(project, filename)
        try:
            docstring = self.codeassist.get_doc(project, source, offset,
                                                resource, MAXFIXES)
        except (self.ModuleSyntaxError, IndentationError):
            # Rope can't parse this file
            docstring = None
        except (self.BadIdentifierError, IndexError):
            docstring = None
        if docstring is None:
            super(RopeBackend, self).rpc_get_docstring(project_root, filename,
                                                       source, offset)
        else:
            return docstring


def find_called_name_offset(source, orig_offset):
    """Return the offset of a calling function.

    This only approximates movement.

    """
    offset = min(orig_offset, len(source) - 1)
    paren_count = 0
    while True:
        if offset <= 1:
            return orig_offset
        elif source[offset] == '(':
            if paren_count == 0:
                return offset - 1
            else:
                paren_count -= 1
        elif source[offset] == ')':
            paren_count += 1
        offset -= 1


##################################################################
# Monkey patching a method in rope because it doesn't complete import
# statements.

def patch_codeassist(codeassist):
    if getattr(codeassist._PythonCodeAssist._code_completions,
               'patched_by_elpy', False):
        return

    def wrapper(fun):
        @wraps(fun)
        def inner(self):
            proposals = get_import_completions(self)
            if proposals:
                return proposals
            else:
                return fun(self)
        inner.patched_by_elpy = True
        return inner

    codeassist._PythonCodeAssist._code_completions = \
        wrapper(codeassist._PythonCodeAssist._code_completions)


def get_import_completions(self):
    if not self.word_finder.is_import_statement(self.offset):
        return []
    modulename = self.word_finder.get_primary_at(self.offset)
    # Rope can handle modules in packages
    if "." in modulename:
        return []
    return dict((name, FakeProposal(name))
                for name in elpy.utils.pydocutils.get_modules()
                if name.startswith(modulename))


class FakeProposal(object):
    def __init__(self, name):
        self.name = name

    def get_doc(self):
        return None

########NEW FILE########
__FILENAME__ = compat
"""Python 2/3 compatibility definitions.

These are used by the rest of Elpy to keep compatibility definitions
in one place.

"""

import sys


if sys.version_info >= (3, 0):
    PYTHON3 = True

    from io import StringIO

    def ensure_not_unicode(obj):
        return obj
else:
    PYTHON3 = False

    from StringIO import StringIO

    def ensure_not_unicode(obj):
        """Return obj. If it's a unicode string, convert it to str first.

        Pydoc functions simply don't find anything for unicode
        strings. No idea why.

        """
        if isinstance(obj, unicode):
            return obj.encode("utf-8")
        else:
            return obj

########NEW FILE########
__FILENAME__ = refactor
"""Refactoring methods for elpy.

This interfaces directly with rope, regardless of the backend used,
because the other backends don't really offer refactoring choices.
Once Jedi is similarly featureful as Rope we can try and offer both.


# Too complex:

- Restructure: Interesting, but too complex, and needs deep Rope
  knowledge to do well.

- ChangeSignature: Slightly less complex interface, but still to
  complex, requiring a large effort for the benefit.


# Too useless:

I could not get these to work in any useful fashion. I might be doing
something wrong.

- ExtractVariable does not replace the code extracted with the
  variable, making it a glorified copy&paste function. Emacs can do
  better than this interface by itself.

- EncapsulateField: Getter/setter methods are outdated, this should be
  using properties.

- IntroduceFactory: Inserts a trivial method to the current class.
  Cute.

- IntroduceParameter: Introduces a parameter correctly, but does not
  replace the old code with the parameter. So it just edits the
  argument list and adds a shiny default.

- LocalToField: Seems to just add "self." in front of all occurrences
  of a variable in the local scope.

- MethodObject: This turns the current method into a callable
  class/object. Not sure what that would be good for.


# Can't even get to work:

- ImportOrganizer expand_star_imports, handle_long_imports,
  relatives_to_absolutes: Seem not to do anything.

- create_move: I was not able to figure out what it would like to see
  as its attrib argument.

"""

try:
    from rope.base.project import Project
    from rope.base.libutils import path_to_resource
    from rope.base import change as rope_change
    from rope.base import worder
    from rope.refactor.importutils import ImportOrganizer
    from rope.refactor.topackage import ModuleToPackage
    from rope.refactor.rename import Rename
    from rope.refactor.move import create_move
    from rope.refactor.inline import create_inline
    from rope.refactor.extract import ExtractMethod
    from rope.refactor.usefunction import UseFunction
    ROPE_AVAILABLE = True
except ImportError:
    ROPE_AVAILABLE = False


def options(description, **kwargs):
    """Decorator to set some options on a method."""
    def set_notes(function):
        function.refactor_notes = {'name': function.__name__,
                                   'category': "Miscellaneous",
                                   'description': description,
                                   'doc': getattr(function, '__doc__',
                                                  ''),
                                   'args': []}
        function.refactor_notes.update(kwargs)
        return function
    return set_notes


class Refactor(object):
    """The main refactoring interface.

    Once initialized, the first call should be to get_refactor_options
    to get a list of refactoring options at a given position. The
    returned value will also list any additional options required.

    Once you picked one, you can call get_changes to get the actual
    refactoring changes.

    """
    def __init__(self, project_root, filename):
        self.project_root = project_root
        if ROPE_AVAILABLE:
            self.project = Project(project_root, ropefolder=None)
            self.resource = path_to_resource(self.project, filename)
        else:
            self.project = None
            self.resource = FakeResource(filename)

    def get_refactor_options(self, start, end=None):
        """Return a list of options for refactoring at the given position.

        If `end` is also given, refactoring on a region is assumed.

        Each option is a dictionary of key/value pairs. The value of
        the key 'name' is the one to be used for get_changes.

        The key 'args' contains a list of additional arguments
        required for get_changes.

        """
        result = []
        for symbol in dir(self):
            if not symbol.startswith("refactor_"):
                continue
            method = getattr(self, symbol)
            if not method.refactor_notes.get('available', True):
                continue
            category = method.refactor_notes['category']
            if end is not None and category != 'Region':
                continue
            if end is None and category == 'Region':
                continue
            is_on_symbol = self._is_on_symbol(start)
            if not is_on_symbol and category in ('Symbol', 'Method'):
                continue
            requires_import = method.refactor_notes.get('only_on_imports',
                                                        False)
            if requires_import and not self._is_on_import_statement(start):
                continue
            result.append(method.refactor_notes)
        return result

    def _is_on_import_statement(self, offset):
        "Does this offset point to an import statement?"
        data = self.resource.read()
        bol = data.rfind("\n", 0, offset) + 1
        eol = data.find("\n", 0, bol)
        if eol == -1:
            eol = len(data)
        line = data[bol:eol]
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            return True
        else:
            return False

    def _is_on_symbol(self, offset):
        "Is this offset on a symbol?"
        if not ROPE_AVAILABLE:
            return False
        data = self.resource.read()
        if offset >= len(data):
            return False
        if data[offset] != '_' and not data[offset].isalnum():
            return False
        word = worder.get_name_at(self.resource, offset)
        if word:
            return True
        else:
            return False

    def get_changes(self, name, *args):
        """Return a list of changes for the named refactoring action.

        Changes are dictionaries describing a single action to be
        taken for the refactoring to be successful.

        A change has an action and possibly a type. In the description
        below, the action is before the slash and the type after it.

        change: Change file contents
        - file: The path to the file to change
        - contents: The new contents for the file
        - Diff: A unified diff showing the changes introduced

        create/file: Create a new file
        - file: The file to create

        create/directory: Create a new directory
        - path: The directory to create

        move/file: Rename a file
        - source: The path to the source file
        - destination: The path to the destination file name

        move/directory: Rename a directory
        - source: The path to the source directory
        - destination: The path to the destination directory name

        delete/file: Delete a file
        - file: The file to delete

        delete/directory: Delete a directory
        - path: The directory to delete

        """
        if not name.startswith("refactor_"):
            raise ValueError("Bad refactoring name {0}".format(name))
        method = getattr(self, name)
        if not method.refactor_notes.get('available', True):
            raise RuntimeError("Method not available")
        return method(*args)

    @options("Convert from x import y to import x.y as y", category="Imports",
             args=[("offset", "offset", None)],
             only_on_imports=True,
             available=ROPE_AVAILABLE)
    def refactor_froms_to_imports(self, offset):
        """Converting imports of the form "from ..." to "import ..."."""
        refactor = ImportOrganizer(self.project)
        changes = refactor.froms_to_imports(self.resource, offset)
        return translate_changes(changes)

    @options("Reorganize and clean up", category="Imports",
             available=ROPE_AVAILABLE)
    def refactor_organize_imports(self):
        """Clean up and organize imports."""
        refactor = ImportOrganizer(self.project)
        changes = refactor.organize_imports(self.resource)
        return translate_changes(changes)

    @options("Convert the current module into a package", category="Module",
             available=ROPE_AVAILABLE)
    def refactor_module_to_package(self):
        """Convert the current module into a package."""
        refactor = ModuleToPackage(self.project, self.resource)
        changes = refactor.get_changes()
        return translate_changes(changes)

    @options("Rename symbol at point", category="Symbol",
             args=[("offset", "offset", None),
                   ("new_name", "string", "Rename to: ")],
             available=ROPE_AVAILABLE)
    def refactor_rename_at_point(self, offset, new_name):
        """Rename the symbol at point."""
        refactor = Rename(self.project, self.resource, offset)
        changes = refactor.get_changes(new_name)
        return translate_changes(changes)

    @options("Rename current module", category="Module",
             args=[("new_name", "string", "Rename to: ")],
             available=ROPE_AVAILABLE)
    def refactor_rename_current_module(self, new_name):
        """Rename the current module."""
        refactor = Rename(self.project, self.resource, None)
        changes = refactor.get_changes(new_name)
        return translate_changes(changes)

    @options("Move the current module to a different package",
             category="Module",
             args=[("new_name", "directory", "Destination package: ")],
             available=ROPE_AVAILABLE)
    def refactor_move_module(self, new_name):
        """Move the current module."""
        refactor = create_move(self.project, self.resource)
        resource = path_to_resource(self.project, new_name)
        changes = refactor.get_changes(resource)
        return translate_changes(changes)

    @options("Inline function call at point", category="Symbol",
             args=[("offset", "offset", None),
                   ("only_this", "boolean", "Only this occurrence? ")],
             available=ROPE_AVAILABLE)
    def refactor_create_inline(self, offset, only_this):
        """Inline the function call at point."""
        refactor = create_inline(self.project, self.resource, offset)
        if only_this:
            changes = refactor.get_changes(remove=False, only_current=True)
        else:
            changes = refactor.get_changes(remove=True, only_current=False)
        return translate_changes(changes)

    @options("Extract current region as a method", category="Region",
             args=[("start", "start_offset", None),
                   ("end", "end_offset", None),
                   ("name", "string", "Method name: "),
                   ("make_global", "boolean", "Create global method? ")],
             available=ROPE_AVAILABLE)
    def refactor_extract_method(self, start, end, name,
                                make_global):
        """Extract region as a method."""
        refactor = ExtractMethod(self.project, self.resource, start, end)
        changes = refactor.get_changes(name, similar=True, global_=make_global)
        return translate_changes(changes)

    @options("Use the function at point wherever possible", category="Method",
             args=[("offset", "offset", None)],
             available=ROPE_AVAILABLE)
    def refactor_use_function(self, offset):
        """Use the function at point wherever possible."""
        refactor = UseFunction(self.project, self.resource, offset)
        changes = refactor.get_changes()
        return translate_changes(changes)


def translate_changes(initial_change):
    """Translate rope.base.change.Change instances to dictionaries.

    See Refactor.get_changes for an explanation of the resulting
    dictionary.

    """
    agenda = [initial_change]
    result = []
    while agenda:
        change = agenda.pop(0)
        if isinstance(change, rope_change.ChangeSet):
            agenda.extend(change.changes)
        elif isinstance(change, rope_change.ChangeContents):
            result.append({'action': 'change',
                           'file': change.resource.real_path,
                           'contents': change.new_contents,
                           'diff': change.get_description()})
        elif isinstance(change, rope_change.CreateFile):
            result.append({'action': 'create',
                           'type': 'file',
                           'file': change.resource.real_path})
        elif isinstance(change, rope_change.CreateFolder):
            result.append({'action': 'create',
                           'type': 'directory',
                           'path': change.resource.real_path})
        elif isinstance(change, rope_change.MoveResource):
            result.append({'action': 'move',
                           'type': ('directory'
                                    if change.new_resource.is_folder()
                                    else 'file'),
                           'source': change.resource.real_path,
                           'destination': change.new_resource.real_path})
        elif isinstance(change, rope_change.RemoveResource):
            if change.resource.is_folder():
                result.append({'action': 'delete',
                               'type': 'directory',
                               'path': change.resource.real_path})
            else:
                result.append({'action': 'delete',
                               'type': 'file',
                               'file': change.resource.real_path})
    return result


class FakeResource(object):
    """A fake resource in case Rope is absence."""

    def __init__(self, filename):
        self.real_path = filename

    def read(self):
        with open(self.real_path) as f:
            return f.read()

########NEW FILE########
__FILENAME__ = rpc
"""A simple JSON-RPC-like server.

The server will read and write lines of JSON-encoded method calls and
responses.

See the documentation of the JSONRPCServer class for further details.

"""

import json
import sys
import traceback


class JSONRPCServer(object):
    """Simple JSON-RPC-like server.

    This class will read single-line JSON expressions from stdin,
    decode them, and pass them to a handler. Return values from the
    handler will be JSON-encoded and written to stdout.

    To implement a handler, you need to subclass this class and add
    methods starting with "rpc_". Methods then will be found.

    Method calls should be encoded like this:

    {"id": 23, "method": "method_name", "params": ["foo", "bar"]}

    This will call self.rpc_method("foo", "bar").

    Responses will be encoded like this:

    {"id": 23, "result": "foo"}

    Errors will be encoded like this:

    {"id": 23, "error": "Simple error message"}

    See http://www.jsonrpc.org/ for the inspiration of the protocol.

    """

    def __init__(self, stdin=None, stdout=None):
        """Return a new JSON-RPC server object.

        It will read lines of JSON data from stdin, and write the
        responses to stdout.

        """
        if stdin is None:
            self.stdin = sys.stdin
        else:
            self.stdin = stdin
        if stdout is None:
            self.stdout = sys.stdout
        else:
            self.stdout = stdout

    def read_json(self):
        """Read a single line and decode it as JSON.

        Can raise an EOFError() when the input source was closed.

        """
        line = self.stdin.readline()
        if line == '':
            raise EOFError()
        return json.loads(line)

    def write_json(self, **kwargs):
        """Write an JSON object on a single line.

        The keyword arguments are interpreted as a single JSON object.
        It's not possible with this method to write non-objects.

        """
        self.stdout.write(json.dumps(kwargs) + "\n")
        self.stdout.flush()

    def handle_request(self):
        """Handle a single JSON-RPC request.

        Read a request, call the appropriate handler method, and
        return the encoded result. Errors in the handler method are
        caught and encoded as error objects. Errors in the decoding
        phase are not caught, as we can not respond with an error
        response to them.

        """
        request = self.read_json()
        if 'method' not in request:
            raise ValueError("Received a bad request: {0}"
                             .format(request))
        method_name = request['method']
        request_id = request.get('id', None)
        params = request.get('params') or []
        try:
            method = getattr(self, "rpc_" + method_name, None)
            if method is not None:
                result = method(*params)
            else:
                result = self.handle(method_name, params)
            if request_id is not None:
                self.write_json(result=result,
                                id=request_id)
        except Warning as e:
            self.write_json(error={"message": str(e)},
                            id=request_id)
        except Exception as e:
            self.write_json(error={"message": str(e),
                                   "traceback": traceback.format_exc()},
                            id=request_id)

    def handle(self, method_name, args):
        """Handle the call to method_name.

        You should overwrite this method in a subclass.
        """
        raise Fault("Unknown method {0}".format(method_name))

    def serve_forever(self):
        """Serve requests forever.

        Errors are not caught, so this is a slight misnomer.

        """
        while True:
            try:
                self.handle_request()
            except (KeyboardInterrupt, EOFError, SystemExit):
                break


class Fault(Exception):
    def __init__(self, message, code=500, data=None):
        super(Fault, self).__init__(message)
        self.code = code
        self.data = data


class Warning(Fault):
    """A warning.

    This does not include a traceback in the error result.
    """
    pass

########NEW FILE########
__FILENAME__ = server
"""Method implementations for the Elpy JSON-RPC server.

This file implements the methods exported by the JSON-RPC server. It
handles backend selection and passes methods on to the selected
backend.

"""
import sys

import elpy

from elpy.utils.pydocutils import get_pydoc_completions
from elpy.rpc import JSONRPCServer, Fault

from elpy.backends.nativebackend import NativeBackend
from elpy.backends.ropebackend import RopeBackend
from elpy.backends.jedibackend import JediBackend

BACKEND_MAP = {
    'native': NativeBackend,
    'rope': RopeBackend,
    'jedi': JediBackend,
}


class ElpyRPCServer(JSONRPCServer):
    """The RPC server for elpy.

    See the rpc_* methods for exported method documentation.

    """

    def __init__(self):
        """Return a new RPC server object.

        As the default backend, we choose the first available from
        rope, jedi, or native.

        """
        super(ElpyRPCServer, self).__init__()
        for cls in [RopeBackend, JediBackend, NativeBackend]:
            backend = cls()
            if backend is not None:
                self.backend = backend
                break

    def handle(self, method_name, args):
        """Call the RPC method method_name with the specified args.

        """
        method = getattr(self.backend, "rpc_" + method_name, None)
        if method is None:
            raise Fault("Unknown method {0}".format(method_name))
        return method(*args)

    def rpc_version(self):
        """Return the version of the elpy RPC backend."""
        return elpy.__version__

    def rpc_echo(self, *args):
        """Return the arguments.

        This is a simple test method to see if the protocol is
        working.

        """
        return args

    def rpc_set_backend(self, backend_name):
        """Set the current backend to backend_name.

        This will change the current backend. If the backend is not
        found or can not find its library, it will raise a ValueError.

        """

        backend_cls = BACKEND_MAP.get(backend_name)
        if backend_cls is None:
            raise ValueError("Unknown backend {0}"
                             .format(backend_name))
        backend = backend_cls()
        if backend is None:
            raise ValueError("Backend {0} could not find the "
                             "required Python library"
                             .format(backend_name))
        self.backend = backend

    def rpc_get_backend(self):
        """Return the name of the current backend."""
        return self.backend.name

    def rpc_get_available_backends(self):
        """Return a list of names of the  available backends.

        A backend is "available" if the libraries it uses can be
        loaded.

        """
        result = []
        for cls in BACKEND_MAP.values():
            backend = cls()
            if backend is not None:
                result.append(backend.name)
        return result

    def rpc_get_pydoc_completions(self, name=None):
        """Return a list of possible strings to pass to pydoc.

        If name is given, the strings are under name. If not, top
        level modules are returned.

        """
        return get_pydoc_completions(name)

    def rpc_get_refactor_options(self, project_root, filename,
                                 start, end=None):
        """Return a list of possible refactoring options.

        This list will be filtered depending on whether it's
        applicable at the point START and possibly the region between
        START and END.

        """
        try:
            from elpy import refactor
        except:
            raise ImportError("Rope not installed, refactorings unavailable")
        ref = refactor.Refactor(project_root, filename)
        return ref.get_refactor_options(start, end)

    def rpc_refactor(self, project_root, filename, method, args):
        """Return a list of changes from the refactoring action.

        A change is a dictionary describing the change. See
        elpy.refactor.translate_changes for a description.

        """
        try:
            from elpy import refactor
        except:
            raise ImportError("Rope not installed, refactorings unavailable")
        if args is None:
            args = ()
        ref = refactor.Refactor(project_root, filename)
        return ref.get_changes(method, *args)

########NEW FILE########
__FILENAME__ = compat
"""Python 2/3 compatibility definitions.

These are used by the rest of Elpy to keep compatibility definitions
in one place.

"""

import sys


if sys.version_info >= (3, 0):
    PYTHON3 = True
    import builtins
    from io import StringIO
else:
    PYTHON3 = False
    import __builtin__ as builtins
    from StringIO import StringIO

########NEW FILE########
__FILENAME__ = support
"""Support classes and functions for the elpy test code."""

import os
import shutil
import tempfile
import unittest


class BackendTestCase(unittest.TestCase):
    """Base class for backend tests.

    This class sets up a project root directory and provides an easy
    way to create files within the project root.

    """

    def setUp(self):
        """Create the project root and make sure it gets cleaned up."""
        self.project_root = tempfile.mkdtemp(prefix="elpy-test")
        self.addCleanup(shutil.rmtree, self.project_root, True)

    def project_file(self, relname, contents):
        """Create a file named relname within the project root.

        Write contents into that file.

        """
        full_name = os.path.join(self.project_root, relname)
        try:
            os.makedirs(os.path.dirname(full_name))
        except OSError:
            pass
        with open(full_name, "w") as f:
            f.write(contents)
        return full_name


def source_and_offset(source):
    """Return a source and offset from a source description.

    >>> source_and_offset("hello, _|_world")
    ("hello, world", 7)
    >>> source_and_offset("_|_hello, world")
    ("hello, world", 0)
    >>> source_and_offset("hello, world_|_")
    ("hello, world", 12)
    """
    offset = source.index("_|_")
    return source[:offset] + source[offset + 3:], offset

########NEW FILE########
__FILENAME__ = test_jedibackend
"""Tests for the elpy.backends.jedibackend module."""

import unittest

import mock

from elpy.tests import compat
from elpy.backends import jedibackend
from elpy.tests.support import BackendTestCase, source_and_offset


class JediBackendTestCase(BackendTestCase):
    def setUp(self):
        super(JediBackendTestCase, self).setUp()
        self.backend = jedibackend.JediBackend()


class TestInit(JediBackendTestCase):
    def test_should_have_jedi_as_name(self):
        self.assertEqual(self.backend.name, "jedi")

    def test_should_return_object_if_jedi_available(self):
        self.assertIsNotNone(jedibackend.JediBackend())

    @mock.patch.object(compat.builtins, '__import__')
    def test_should_return_none_if_no_rope(self, import_):
        import_.side_effect = ImportError
        self.assertIsNone(jedibackend.JediBackend())


class TestGetCompletions(JediBackendTestCase):
    def test_should_complete_builtin(self):
        source, offset = source_and_offset("o_|_")
        self.assertEqual(sorted([name for (name, doc) in
                                 self.backend.rpc_get_completions(
                                     None, "test.py", source, offset)]),
                         sorted(['SError', 'bject', 'ct', 'pen', 'r',
                                 'rd', 'verflowError']))

    def test_should_find_with_trailing_text(self):
        source, offset = source_and_offset(
            "import threading\nthreading.T_|_mumble mumble")
        if compat.PYTHON3:
            expected = ["hread", "hreadError", "IMEOUT_MAX", "imer"]
        else:
            expected = ["hread", "hread", "hreadError", "imer"]
        self.assertEqual(sorted([name for (name, doc) in
                                 self.backend.rpc_get_completions(
                                     None, "test.py", source, offset)]),
                         sorted(expected))

    def test_should_not_fail_on_inexisting_file(self):
        self.backend.rpc_get_completions(self.project_root,
                                         "doesnotexist.py",
                                         "", 0)

    def test_should_not_fail_if_file_is_none(self):
        self.backend.rpc_get_completions(self.project_root,
                                         None,
                                         "open", 0)

    def test_should_find_completion_different_package(self):
        # See issue #74
        self.project_file("project/__init__.py", "")
        source1 = ("class Add:\n"
                   "    def add(self, a, b):\n"
                   "        return a + b\n")
        self.project_file("project/add.py", source1)
        source2, offset = source_and_offset(
            "from project.add import Add\n"
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        c = Add()\n"
            "        c.ad_|_\n")
        file2 = self.project_file("project/calculator.py", source2)
        proposals = self.backend.rpc_get_completions(self.project_root,
                                                     file2,
                                                     source2,
                                                     offset)
        self.assertEqual(proposals, [['d', 'add(self, a, b)\n\n']])

    @mock.patch('elpy.backends.jedibackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_completions(self.project_root, None,
                                         "test-source", 0)

        get_source.assert_called_with("test-source")


class TestGetDefinition(JediBackendTestCase):
    def test_should_return_definition_location_same_file(self):
        source, offset = source_and_offset("import threading\n"
                                           "def test_function(a, b):\n"
                                           "    return a + b\n"
                                           "\n"
                                           "test_func_|_tion(\n")
        filename = self.project_file("test.py", source)
        self.assertEqual(self.backend.rpc_get_definition(self.project_root,
                                                         filename,
                                                         source,
                                                         offset),
                         (filename, 17))

    def test_should_return_none_if_file_does_not_exist(self):
        source, offset = source_and_offset(
            "def foo():\n"
            "    pass\n"
            "\n"
            "fo_|_o()\n")
        self.assertIsNone(
            self.backend.rpc_get_definition(self.project_root,
                                            self.project_root +
                                            "/doesnotexist.py",
                                            source,
                                            offset))

    def test_should_return_none_if_not_found(self):
        source, offset = source_and_offset(
            "fo_|_o()\n")
        filename = self.project_file("test.py", source)
        self.assertIsNone(
            self.backend.rpc_get_definition(self.project_root,
                                            filename,
                                            source,
                                            offset))

    def test_should_return_definition_location_different_file(self):
        source1 = ("def test_function(a, b):\n"
                   "    return a + b\n")
        file1 = self.project_file("test1.py", source1)
        source2, offset = source_and_offset("from test1 import test_function\n"
                                            "test_function_|_(1, 2)\n")
        file2 = self.project_file("test2.py", source2)
        location = self.backend.rpc_get_definition(self.project_root,
                                                   file2,
                                                   source2,
                                                   offset)
        self.assertEqual(location, (file1, 0))

    def test_should_return_definition_location_different_package(self):
        # See issue #74
        self.project_file("project/__init__.py", "")
        source1 = ("class Add:\n"
                   "    def add(self, a, b):\n"
                   "        return a + b\n")
        file1 = self.project_file("project/add.py", source1)
        source2, offset = source_and_offset(
            "from project.add import Add\n"
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return Add_|_().add(a, b)\n")
        file2 = self.project_file("project/calculator.py", source2)
        location = self.backend.rpc_get_definition(self.project_root,
                                                   file2,
                                                   source2,
                                                   offset)
        self.assertEqual(location, (file1, 0))

    def test_should_not_fail_on_inexisting_file(self):
        self.backend.rpc_get_definition(self.project_root,
                                        "doesnotexist.py",
                                        "open", 0)

    def test_should_not_fail_if_file_is_none(self):
        self.backend.rpc_get_definition(self.project_root,
                                        None,
                                        "open", 0)

    def test_should_find_variable_definition(self):
        source, offset = source_and_offset("SOME_VALUE = 1\n"
                                           "\n"
                                           "variable = _|_SOME_VALUE\n")
        filename = self.project_file("test.py", source)
        self.assertEqual(self.backend.rpc_get_definition(self.project_root,
                                                         filename,
                                                         source,
                                                         offset),
                         (filename, 0))

    @mock.patch('elpy.backends.jedibackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_definition(self.project_root, None,
                                        "test-source", 0)

        get_source.assert_called_with("test-source")


class TestGetCalltip(JediBackendTestCase):
    def test_should_return_calltip(self):
        filename = self.project_file("test.py", "")
        source, offset = source_and_offset("import threading\n"
                                           "threading.Thread(_|_")
        calltip = self.backend.rpc_get_calltip(self.project_root,
                                               filename,
                                               source, offset)
        if compat.PYTHON3:
            self.assertEqual(calltip.replace(" = ", "="),
                             "Thread(group=None, target=None, name=None, "
                             "args=(), kwargs=None, daemon=None)")
        else:
            self.assertEqual(calltip.replace(" = ", "="),
                             "Thread(group=None, target=None, name=None, "
                             "args=(), kwargs=None, verbose=None)")

    def test_should_return_none_outside_of_all(self):
        filename = self.project_file("test.py", "")
        source, offset = source_and_offset("import thr_|_eading\n")
        calltip = self.backend.rpc_get_calltip(self.project_root,
                                               filename,
                                               source, offset)
        self.assertIsNone(calltip)

    def test_should_not_fail_on_inexisting_file(self):
        self.backend.rpc_get_calltip(self.project_root,
                                     "doesnotexist.py",
                                     "open(", 5)

    def test_should_not_fail_if_file_is_none(self):
        self.backend.rpc_get_calltip(self.project_root,
                                     None,
                                     "open", 0)

    def test_should_find_calltip_different_package(self):
        # See issue #74
        self.project_file("project/__init__.py", "")
        source1 = ("class Add:\n"
                   "    def add(self, a, b):\n"
                   "        return a + b\n")
        self.project_file("project/add.py", source1)
        source2, offset = source_and_offset(
            "from project.add import Add\n"
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        c = Add()\n"
            "        c.add(_|_\n")
        file2 = self.project_file("project/calculator.py", source2)
        calltip = self.backend.rpc_get_calltip(self.project_root,
                                               file2,
                                               source2,
                                               offset)
        self.assertEqual(calltip, 'add(a, b)')

    @mock.patch('elpy.backends.jedibackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_calltip(self.project_root, None,
                                     "test-source", 0)

        get_source.assert_called_with("test-source")


class TestGetDocstring(JediBackendTestCase):
    def test_should_get_docstring(self):
        filename = self.project_file("test.py", "")
        source, offset = source_and_offset(
            "import threading\nthreading.Thread.join_|_(")
        docstring = self.backend.rpc_get_docstring(self.project_root,
                                                   filename,
                                                   source,
                                                   offset)

        import pydoc
        wanted = pydoc.render_doc("threading.Thread.join",
                                  "Elpy Pydoc Documentation for %s",
                                  False)
        self.assertEqual(docstring, wanted)

    def test_should_not_fail_on_inexisting_file(self):
        self.backend.rpc_get_docstring(self.project_root,
                                       "doesnotexist.py",
                                       "open", 0)

    def test_should_not_fail_if_file_is_none(self):
        self.backend.rpc_get_docstring(self.project_root,
                                       None,
                                       "open", 0)

    @mock.patch('elpy.backends.jedibackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_docstring(self.project_root, None,
                                       "test-source", 0)

        get_source.assert_called_with("test-source")


class TestPosToLinecol(unittest.TestCase):
    def test_should_handle_beginning_of_string(self):
        self.assertEqual(jedibackend.pos_to_linecol("foo", 0),
                         (1, 0))

    def test_should_handle_end_of_line(self):
        self.assertEqual(jedibackend.pos_to_linecol("foo\nbar\nbaz\nqux", 9),
                         (3, 1))

    def test_should_handle_end_of_string(self):
        self.assertEqual(jedibackend.pos_to_linecol("foo\nbar\nbaz\nqux", 14),
                         (4, 2))


class TestLinecolToPos(unittest.TestCase):
    def test_should_handle_beginning_of_string(self):
        self.assertEqual(jedibackend.linecol_to_pos("foo", 1, 0),
                         0)

    def test_should_handle_end_of_string(self):
        self.assertEqual(jedibackend.linecol_to_pos("foo\nbar\nbaz\nqux",
                                                    3, 1),
                         9)

    def test_should_return_offset(self):
        self.assertEqual(jedibackend.linecol_to_pos("foo\nbar\nbaz\nqux",
                                                    4, 2),
                         14)

    def test_should_fail_for_line_past_text(self):
        self.assertRaises(ValueError,
                          jedibackend.linecol_to_pos, "foo\n", 3, 1)

    def test_should_fail_for_column_past_text(self):
        self.assertRaises(ValueError,
                          jedibackend.linecol_to_pos, "foo\n", 1, 10)

########NEW FILE########
__FILENAME__ = test_nativebackend
# coding: utf-8
"""Tests for the elpy.backends.nativebackend backend."""

import mock
import os
import pydoc
import tempfile

from elpy.backends import nativebackend
from elpy.tests.support import BackendTestCase, source_and_offset


class NativeBackendTestCase(BackendTestCase):
    def setUp(self):
        super(NativeBackendTestCase, self).setUp()
        self.backend = nativebackend.NativeBackend()


class TestInit(NativeBackendTestCase):
    def test_should_have_native_as_name(self):
        self.assertEqual(self.backend.name, "native")


class TestRPCGetDefinition(NativeBackendTestCase):
    def test_should_have_rpc_get_definition(self):
        self.assertIsNone(self.backend.rpc_get_definition(None, None,
                                                          None, None))

    @mock.patch('elpy.backends.nativebackend.get_source')
    def test_should_call_get_source(self, get_source):
        self.backend.rpc_get_definition(None, None, "test-source", None)

        get_source.assert_called_with("test-source")


class TestRPCGetCalltip(NativeBackendTestCase):
    def test_should_have_rpc_get_calltip(self):
        self.assertIsNone(self.backend.rpc_get_calltip(None, None,
                                                       None, None))

    @mock.patch('elpy.backends.nativebackend.get_source')
    def test_should_call_get_source(self, get_source):
        self.backend.rpc_get_calltip(None, None, "test-source", None)

        get_source.assert_called_with("test-source")


class TestGetCompletions(NativeBackendTestCase):
    def test_should_complete_simple_calls(self):
        source, offset = source_and_offset("o_|_")
        self.assertEqual(sorted([name for (name, doc) in
                                 self.backend.rpc_get_completions(
                                     None, None, source, offset)]),
                         sorted(["bject", "ct", "pen", "r", "rd"]))

    @mock.patch('elpy.backends.nativebackend.get_source')
    def test_should_call_get_source(self, get_source):
        self.backend.rpc_get_completions(None, None, "test-source", 0)

        get_source.assert_called_with("test-source")


class TestGetDocstring(NativeBackendTestCase):
    def test_should_find_documentation(self):
        source = "foo(open("
        offset = 6  # foo(op_|_en(
        docstring = pydoc.render_doc("open",
                                     "Elpy Pydoc Documentation for %s",
                                     False)
        self.assertEqual(self.backend.rpc_get_docstring(None, None,
                                                        source, offset),
                         docstring)

    @mock.patch('elpy.backends.nativebackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_docstring(None, None, "test-source", 0)

        get_source.assert_called_with("test-source")


class TestGetPydocDocumentation(NativeBackendTestCase):
    def test_should_find_documentation(self):
        docstring = pydoc.render_doc("open",
                                     "Elpy Pydoc Documentation for %s",
                                     False)
        self.assertEqual(self.backend.rpc_get_pydoc_documentation("open"),
                         docstring)


class TestFindSymbol(NativeBackendTestCase):
    def test_should_find_symbol(self):
        source, offset = source_and_offset("threading.current_th_|_read")
        result = nativebackend.find_symbol_backward(source, offset)
        self.assertEqual(result[0], "current_th")
        self.assertEqual(source[result[1]:result[2]],
                         "current_th")
        result = nativebackend.find_symbol(source, offset)
        self.assertEqual(result[0], "current_thread")
        self.assertEqual(source[result[1]:result[2]],
                         "current_thread")

    def test_should_find_empty_string_at_start_of_source(self):
        source, offset = source_and_offset("_|_threading")
        result = nativebackend.find_symbol_backward(source, offset)
        self.assertEqual(result[0], "")
        self.assertEqual(source[result[1]:result[2]],
                         "")

    def test_should_find_empty_string_at_start_of_symbol(self):
        source, offset = source_and_offset("threading._|_current_thread()")
        result = nativebackend.find_symbol_backward(source, offset)
        self.assertEqual(result[0], "")
        self.assertEqual(source[result[1]:result[2]],
                         "")

    def test_should_find_symbol_at_start_of_source(self):
        source, offset = source_and_offset("thr_|_eading")
        result = nativebackend.find_symbol_backward(source, offset)
        self.assertEqual(result[0], "thr")
        self.assertEqual(source[result[1]:result[2]],
                         "thr")


class TestFindDottedSymbol(NativeBackendTestCase):
    def test_should_find_symbol(self):
        source, offset = source_and_offset(
            "foo(threading.current_th_|_read())")
        result = nativebackend.find_dotted_symbol_backward(source, offset)
        self.assertEqual(result[0], "threading.current_th")
        self.assertEqual(source[result[1]:result[2]],
                         "threading.current_th")
        result = nativebackend.find_dotted_symbol(source, offset)
        self.assertEqual(result[0], "threading.current_thread")
        self.assertEqual(source[result[1]:result[2]],
                         "threading.current_thread")

    def test_should_find_empty_string_at_start_of_source(self):
        source = "threading.current_thread"
        offset = 0
        result = nativebackend.find_dotted_symbol_backward(source, offset)
        self.assertEqual(result[0], "")
        self.assertEqual(source[result[1]:result[2]],
                         "")

    def test_should_find_empty_string_at_start_of_symbol(self):
        source = "foo(threading.current_thread)"
        offset = 4  # foo(_|_thr
        result = nativebackend.find_dotted_symbol_backward(source, offset)
        self.assertEqual(result[0], "")
        self.assertEqual(source[result[1]:result[2]],
                         "")

    def test_should_find_symbol_at_start_of_source(self):
        source = "threading.current_thread"
        offset = 13  # threading.cur_|_rent
        result = nativebackend.find_dotted_symbol_backward(source, offset)
        self.assertEqual(result[0], "threading.cur")
        self.assertEqual(source[result[1]:result[2]],
                         "threading.cur")


class TestGetSource(NativeBackendTestCase):
    def test_should_return_string_by_default(self):
        self.assertEqual(nativebackend.get_source("foo"),
                         "foo")

    def test_should_return_file_contents(self):
        fd, filename = tempfile.mkstemp(prefix="elpy-test-")
        self.addCleanup(os.remove, filename)
        with open(filename, "w") as f:
            f.write("file contents")

        fileobj = {'filename': filename}

        self.assertEqual(nativebackend.get_source(fileobj),
                         "file contents")

    def test_should_clean_up_tempfile(self):
        fd, filename = tempfile.mkstemp(prefix="elpy-test-")
        with open(filename, "w") as f:
            f.write("file contents")

        fileobj = {'filename': filename,
                   'delete_after_use': True}

        self.assertEqual(nativebackend.get_source(fileobj),
                         "file contents")
        self.assertFalse(os.path.exists(filename))

    def test_should_support_utf8(self):
        fd, filename = tempfile.mkstemp(prefix="elpy-test-")
        self.addCleanup(os.remove, filename)
        with open(filename, "wb") as f:
            f.write(u"möp".encode("utf-8"))

        source = nativebackend.get_source({'filename': filename})

        self.assertEqual(source, u"möp")

########NEW FILE########
__FILENAME__ = test_pydocutils
import unittest
import mock
import elpy.utils.pydocutils


class TestGetPydocCompletions(unittest.TestCase):
    def test_should_return_top_level_modules(self):
        modules = elpy.utils.pydocutils.get_pydoc_completions("")
        self.assertIn('sys', modules)
        self.assertIn('json', modules)
        self.assertIn('elpy', modules)

    def test_should_return_submodules(self):
        modules = elpy.utils.pydocutils.get_pydoc_completions("elpy")
        self.assertIn("elpy.rpc", modules)
        self.assertIn("elpy.server", modules)
        modules = elpy.utils.pydocutils.get_pydoc_completions("os")
        self.assertIn("os.path", modules)

    def test_should_find_objects_in_module(self):
        self.assertIn("elpy.tests.test_pydocutils.TestGetPydocCompletions",
                      elpy.utils.pydocutils.get_pydoc_completions
                      ("elpy.tests.test_pydocutils"))

    def test_should_find_attributes_of_objects(self):
        attribs = elpy.utils.pydocutils.get_pydoc_completions(
            "elpy.tests.test_pydocutils.TestGetPydocCompletions")
        self.assertIn("elpy.tests.test_pydocutils.TestGetPydocCompletions."
                      "test_should_find_attributes_of_objects",
                      attribs)

    def test_should_return_none_for_inexisting_module(self):
        self.assertEqual([],
                         elpy.utils.pydocutils.get_pydoc_completions
                         ("does_not_exist"))

    def test_should_work_for_unicode_strings(self):
        self.assertIsNotNone(elpy.utils.pydocutils.get_pydoc_completions
                             (u"sys"))

    def test_should_find_partial_completions(self):
        self.assertIn("multiprocessing",
                      elpy.utils.pydocutils.get_pydoc_completions
                      ("multiprocess"))
        self.assertIn("multiprocessing.util",
                      elpy.utils.pydocutils.get_pydoc_completions
                      ("multiprocessing.ut"))

    def test_should_ignore_trailing_dot(self):
        self.assertIn("elpy.utils",
                      elpy.utils.pydocutils.get_pydoc_completions
                      ("elpy."))


class TestGetModules(unittest.TestCase):
    def test_should_return_top_level_modules(self):
        modules = elpy.utils.pydocutils.get_modules()
        self.assertIn('sys', modules)
        self.assertIn('json', modules)
        self.assertIn('elpy', modules)

    def test_should_return_submodules(self):
        modules = elpy.utils.pydocutils.get_modules("elpy")
        self.assertIn("rpc", modules)
        self.assertIn("server", modules)

    @mock.patch.object(elpy.utils.pydocutils, 'safeimport')
    def test_should_catch_import_errors(self, safeimport):
        def raise_function(message):
            raise elpy.utils.pydocutils.ErrorDuringImport(message,
                                                          (None, None, None))
        safeimport.side_effect = raise_function
        self.assertEqual([], elpy.utils.pydocutils.get_modules("foo.bar"))

########NEW FILE########
__FILENAME__ = test_refactor
import unittest
import tempfile
import shutil
import os
import mock

from elpy import refactor


class RefactorTestCase(unittest.TestCase):
    def setUp(self):
        self.project_root = tempfile.mkdtemp(prefix="test-refactor-root")
        self.addCleanup(shutil.rmtree, self.project_root,
                        ignore_errors=True)

    def create_file(self, name, contents=""):
        filename = os.path.join(self.project_root, name)
        offset = contents.find("_|_")
        if offset > -1:
            contents = contents[:offset] + contents[offset + 3:]
        with open(filename, "w") as f:
            f.write(contents)
        return filename, offset


class TestGetRefactorOptions(RefactorTestCase):
    def test_should_only_return_importsmodule_if_not_on_symbol(self):
        filename, offset = self.create_file("foo.py",
                                            "import foo\n"
                                            "_|_")
        ref = refactor.Refactor(self.project_root, filename)
        options = ref.get_refactor_options(offset)
        self.assertTrue(all(opt['category'] in ('Imports',
                                                'Module')
                            for opt in options))
        filename, offset = self.create_file("foo.py",
                                            "_|_\n"
                                            "import foo\n")
        ref = refactor.Refactor(self.project_root, filename)
        options = ref.get_refactor_options(offset)
        self.assertTrue(all(opt['category'] in ('Imports',
                                                'Module')
                            for opt in options))

    def test_should_return_all_if_on_symbol(self):
        filename, offset = self.create_file("foo.py",
                                            "import _|_foo")
        ref = refactor.Refactor(self.project_root, filename)
        options = ref.get_refactor_options(offset)
        self.assertTrue(all(opt['category'] in ('Imports',
                                                'Method',
                                                'Module',
                                                'Symbol')
                            for opt in options))

    def test_should_return_only_region_if_endoffset(self):
        filename, offset = self.create_file("foo.py",
                                            "import foo")
        ref = refactor.Refactor(self.project_root, filename)
        options = ref.get_refactor_options(offset, 5)
        self.assertTrue(all(opt['category'] == 'Region'
                            for opt in options))

    @unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
    def test_should_treat_from_import_special(self):
        filename, offset = self.create_file("foo.py",
                                            "import foo\n"
                                            "_|_")
        ref = refactor.Refactor(self.project_root, filename)
        options = ref.get_refactor_options(offset)
        self.assertFalse(any(opt['name'] == "refactor_froms_to_imports"
                             for opt in options))
        filename, offset = self.create_file("foo.py",
                                            "imp_|_ort foo")
        ref = refactor.Refactor(self.project_root, filename)
        options = ref.get_refactor_options(offset)
        self.assertTrue(any(opt['name'] == "refactor_froms_to_imports"
                            for opt in options))


class TestGetChanges(RefactorTestCase):
    def test_should_fail_if_method_is_not_refactoring(self):
        filename, offset = self.create_file("foo.py")
        ref = refactor.Refactor(self.project_root, filename)
        self.assertRaises(ValueError, ref.get_changes, "bad_name")

    def test_should_return_method_results(self):
        filename, offset = self.create_file("foo.py")
        ref = refactor.Refactor(self.project_root, filename)
        with mock.patch.object(ref, 'refactor_extract_method') as test:
            test.return_value = "Meep!"
            self.assertEqual(ref.get_changes("refactor_extract_method",
                                             1, 2),
                             "Meep!")
            test.assert_called_with(1, 2)


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestIsOnSymbol(RefactorTestCase):
    def test_should_find_symbol(self):
        filename, offset = self.create_file("test.py", "__B_|_AR = 100")
        r = refactor.Refactor(self.project_root, filename)
        self.assertTrue(r._is_on_symbol(offset))

    # Issue #111
    def test_should_find_symbol_with_underscores(self):
        filename, offset = self.create_file("test.py", "_|___BAR = 100")
        r = refactor.Refactor(self.project_root, filename)
        self.assertTrue(r._is_on_symbol(offset))

    def test_should_not_find_weird_places(self):
        filename, offset = self.create_file("test.py", "hello = _|_ 1 + 1")
        r = refactor.Refactor(self.project_root, filename)
        self.assertFalse(r._is_on_symbol(offset))


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestFromsToImports(RefactorTestCase):
    def test_should_refactor(self):
        filename, offset = self.create_file(
            "foo.py",
            "_|_from datetime import datetime\n"
            "\n"
            "d = datetime(2013, 4, 7)\n")
        ref = refactor.Refactor(self.project_root, filename)
        (change,) = ref.get_changes("refactor_froms_to_imports", offset)
        self.assertEqual(change['action'], 'change')
        self.assertEqual(change['file'], filename)
        self.assertEqual(change['contents'],
                         "import datetime\n"
                         "\n"
                         "d = datetime.datetime(2013, 4, 7)\n")


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestOrganizeImports(RefactorTestCase):
    def test_should_refactor(self):
        filename, offset = self.create_file(
            "foo.py",
            "import unittest, base64\n"
            "import datetime, json\n"
            "\n"
            "obj = json.dumps(23)\n"
            "unittest.TestCase()\n")
        ref = refactor.Refactor(self.project_root, filename)
        (change,) = ref.get_changes("refactor_organize_imports")
        self.assertEqual(change['action'], 'change')
        self.assertEqual(change['file'], filename)
        self.assertEqual(change['contents'],
                         "import json\n"
                         "import unittest\n"
                         "\n"
                         "\n"
                         "obj = json.dumps(23)\n"
                         "unittest.TestCase()\n")


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestModuleToPackage(RefactorTestCase):
    def test_should_refactor(self):
        filename, offset = self.create_file(
            "foo.py",
            "_|_import os\n")
        ref = refactor.Refactor(self.project_root, filename)
        changes = ref.refactor_module_to_package()
        a, b, c = changes
        # Not sure why the a change is there. It's a CHANGE that
        # changes nothing...
        self.assertEqual(a['diff'], '')

        self.assertEqual(b['action'], 'create')
        self.assertEqual(b['type'], 'directory')
        self.assertEqual(b['path'], os.path.join(self.project_root, "foo"))

        self.assertEqual(c['action'], 'move')
        self.assertEqual(c['type'], 'file')
        self.assertEqual(c['source'], os.path.join(self.project_root,
                                                   "foo.py"))
        self.assertEqual(c['destination'], os.path.join(self.project_root,
                                                        "foo/__init__.py"))


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestRenameAtPoint(RefactorTestCase):
    def test_should_refactor(self):
        filename, offset = self.create_file(
            "foo.py",
            "class Foo(object):\n"
            "    def _|_foo(self):\n"
            "        return 5\n"
            "\n"
            "    def bar(self):\n"
            "        return self.foo()\n")
        file2, offset2 = self.create_file(
            "bar.py",
            "import foo\n"
            "\n"
            "\n"
            "x = foo.Foo()\n"
            "x.foo()")
        ref = refactor.Refactor(self.project_root, filename)
        first, second = ref.refactor_rename_at_point(offset, "frob")
        if first['file'] == filename:
            a, b = first, second
        else:
            a, b = second, first
        self.assertEqual(a['action'], 'change')
        self.assertEqual(a['file'], filename)
        self.assertEqual(a['contents'],
                         "class Foo(object):\n"
                         "    def frob(self):\n"
                         "        return 5\n"
                         "\n"
                         "    def bar(self):\n"
                         "        return self.frob()\n")
        self.assertEqual(b['action'], 'change')
        self.assertEqual(b['file'], file2)
        self.assertEqual(b['contents'],
                         "import foo\n"
                         "\n"
                         "\n"
                         "x = foo.Foo()\n"
                         "x.frob()")


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestRenameCurrentModule(RefactorTestCase):
    def test_should_refactor(self):
        filename, offset = self.create_file(
            "foo.py",
            "_|_import os\n")
        file2, offset = self.create_file(
            "bar.py",
            "_|_import foo\n"
            "foo.os\n")
        dest = os.path.join(self.project_root, "frob.py")
        ref = refactor.Refactor(self.project_root, filename)
        a, b = ref.refactor_rename_current_module("frob")

        self.assertEqual(a['action'], 'change')
        self.assertEqual(a['file'], file2)
        self.assertEqual(a['contents'],
                         "import frob\n"
                         "frob.os\n")

        self.assertEqual(b['action'], 'move')
        self.assertEqual(b['type'], 'file')
        self.assertEqual(b['source'], filename)
        self.assertEqual(b['destination'], dest)


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestMoveModule(RefactorTestCase):
    def test_should_refactor(self):
        filename, offset = self.create_file(
            "foo.py",
            "_|_import os\n")
        file2, offset = self.create_file(
            "bar.py",
            "_|_import foo\n"
            "foo.os\n")
        dest = os.path.join(self.project_root, "frob")
        os.mkdir(dest)
        with open(os.path.join(dest, "__init__.py"), "w") as f:
            f.write("")
        ref = refactor.Refactor(self.project_root, filename)
        a, b = ref.refactor_move_module(dest)

        self.assertEqual(a['action'], 'change')
        self.assertEqual(a['file'], file2)
        self.assertEqual(a['contents'],
                         "import frob.foo\n"
                         "frob.foo.os\n")

        self.assertEqual(b['action'], 'move')
        self.assertEqual(b['type'], 'file')
        self.assertEqual(b['source'], filename)
        self.assertEqual(b['destination'],
                         os.path.join(dest, "foo.py"))


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestCreateInline(RefactorTestCase):
    def setUp(self):
        super(TestCreateInline, self).setUp()
        self.filename, self.offset = self.create_file(
            "foo.py",
            "def add(a, b):\n"
            "    return a + b\n"
            "\n"
            "x = _|_add(2, 3)\n"
            "y = add(17, 4)\n")

    def test_should_refactor_single_occurrenc(self):
        ref = refactor.Refactor(self.project_root, self.filename)
        (change,) = ref.refactor_create_inline(self.offset, True)

        self.assertEqual(change['action'], 'change')
        self.assertEqual(change['file'], self.filename)
        self.assertEqual(change['contents'],
                         "def add(a, b):\n"
                         "    return a + b\n"
                         "\n"
                         "x = 2 + 3\n"
                         "y = add(17, 4)\n")

    def test_should_refactor_all_occurrencs(self):
        ref = refactor.Refactor(self.project_root, self.filename)
        (change,) = ref.refactor_create_inline(self.offset, False)

        self.assertEqual(change['action'], 'change')
        self.assertEqual(change['file'], self.filename)
        self.assertEqual(change['contents'],
                         "x = 2 + 3\n"
                         "y = 17 + 4\n")


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestExtractMethod(RefactorTestCase):
    def setUp(self):
        super(TestExtractMethod, self).setUp()
        self.filename, self.offset = self.create_file(
            "foo.py",
            "class Foo(object):\n"
            "    def spaghetti(self, a, b):\n"
            "        _|_x = a + 5\n"
            "        y = b + 23\n"
            "        return y\n")

    def test_should_refactor_local(self):
        ref = refactor.Refactor(self.project_root, self.filename)
        (change,) = ref.refactor_extract_method(self.offset, 104,
                                                "calc", False)
        self.assertEqual(change['action'], 'change')
        self.assertEqual(change['file'], self.filename)
        expected = ("class Foo(object):\n"
                    "    def spaghetti(self, a, b):\n"
                    "        return self.calc(a, b)\n"
                    "\n"
                    "    def calc(self, a, b):\n"
                    "        x = a + 5\n"
                    "        y = b + 23\n"
                    "        return y\n")
        expected2 = expected.replace("return self.calc(a, b)",
                                     "return self.calc(b, a)")
        expected2 = expected2.replace("def calc(self, a, b)",
                                      "def calc(self, b, a)")
        if change['contents'] == expected2:
            self.assertEqual(change['contents'], expected2)
        else:
            self.assertEqual(change['contents'], expected)

    def test_should_refactor_global(self):
        ref = refactor.Refactor(self.project_root, self.filename)
        (change,) = ref.refactor_extract_method(self.offset, 104,
                                                "calc", True)
        self.assertEqual(change['action'], 'change')
        self.assertEqual(change['file'], self.filename)
        expected = ("class Foo(object):\n"
                    "    def spaghetti(self, a, b):\n"
                    "        return calc(a, b)\n"
                    "\n"
                    "def calc(a, b):\n"
                    "    x = a + 5\n"
                    "    y = b + 23\n"
                    "    return y\n")
        expected2 = expected.replace("return calc(a, b)",
                                     "return calc(b, a)")
        expected2 = expected2.replace("def calc(a, b)",
                                      "def calc(b, a)")
        if change['contents'] == expected2:
            self.assertEqual(change['contents'], expected2)
        else:
            self.assertEqual(change['contents'], expected)


@unittest.skipIf(not refactor.ROPE_AVAILABLE, "Requires Rope")
class TestUseFunction(RefactorTestCase):
    def test_should_refactor(self):
        filename, offset = self.create_file(
            "foo.py",
            "def _|_add_and_multiply(a, b, c):\n"
            "    temp = a + b\n"
            "    return temp * c\n"
            "\n"
            "f = 1 + 2\n"
            "g = f * 3\n")

        ref = refactor.Refactor(self.project_root, filename)
        (change,) = ref.refactor_use_function(offset)

        self.assertEqual(change['action'], 'change')
        self.assertEqual(change['file'], filename)
        self.assertEqual(change['contents'],
                         "def add_and_multiply(a, b, c):\n"
                         "    temp = a + b\n"
                         "    return temp * c\n"
                         "\n"
                         "g = add_and_multiply(1, 2, 3)\n")

########NEW FILE########
__FILENAME__ = test_ropebackend
"""Tests for elpy.backends.ropebackend."""

import mock

from elpy.tests import compat
from elpy.tests.support import BackendTestCase, source_and_offset
from elpy.backends import ropebackend


class RopeBackendTestCase(BackendTestCase):
    def setUp(self):
        super(RopeBackendTestCase, self).setUp()
        self.backend = ropebackend.RopeBackend()


class TestInit(RopeBackendTestCase):
    def test_should_have_rope_as_name(self):
        self.assertEqual(self.backend.name, "rope")

    def test_should_return_object_if_rope_available(self):
        self.assertIsNotNone(ropebackend.RopeBackend())

    @mock.patch.object(compat.builtins, '__import__')
    def test_should_return_none_if_no_rope(self, import_):
        import_.side_effect = ImportError
        self.assertIsNone(ropebackend.RopeBackend())


class TestGetProject(RopeBackendTestCase):
    def test_should_raise_error_for_none_as_project_root(self):
        self.assertRaises(ValueError,
                          self.backend.get_project, None)

    def test_should_return_none_for_inexisting_directory(self):
        self.assertIsNone(self.backend.get_project(self.project_root +
                                                   "/doesnotexist/"))


class TestGetCompletions(RopeBackendTestCase):
    def test_should_return_completions(self):
        source, offset = source_and_offset("import json\n"
                                           "json.J_|_")
        filename = self.project_file("test.py", source)
        completions = self.backend.rpc_get_completions(self.project_root,
                                                       filename,
                                                       source,
                                                       offset)
        self.assertEqual(sorted(name for (name, doc) in completions),
                         sorted(["SONDecoder", "SONEncoder"]))
        self.assertIn("Simple JSON",
                      dict(completions)['SONDecoder'])

    def test_should_not_fail_on_inexisting_file(self):
        filename = self.project_root + "/doesnotexist.py"
        self.backend.rpc_get_completions(self.project_root,
                                         filename,
                                         "",
                                         0)

    def test_should_not_fail_if_file_is_none(self):
        self.backend.rpc_get_completions(self.project_root,
                                         None,
                                         "",
                                         0)

    def test_should_not_fail_for_module_syntax_errors(self):
        source, offset = source_and_offset(
            "class Foo(object):\n"
            "  def bar(self):\n"
            "    foo(_|_"
            "    bar("
            "\n"
            "  def a(self):\n"
            "    pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
        )

        filename = self.project_file("test.py", source)
        self.assertEquals([],
                          self.backend.rpc_get_completions
                          (self.project_root, filename, source, offset))

    def test_should_not_fail_for_bad_indentation(self):
        source, offset = source_and_offset(
            "def foo():\n"
            "       print 23_|_\n"
            "      print 17\n")
        filename = self.project_file("test.py", source)
        self.assertEquals([],
                          self.backend.rpc_get_completions
                          (self.project_root, filename, source, offset))

    def test_should_complete_top_level_modules_for_import(self):
        source, offset = source_and_offset("import multi_|_")
        filename = self.project_file("test.py", source)
        completions = self.backend.rpc_get_completions(self.project_root,
                                                       filename,
                                                       source,
                                                       offset)
        if compat.PYTHON3:
            expected = ["processing"]
        else:
            expected = ["file", "processing"]
        self.assertEqual(sorted(name for (name, doc) in completions),
                         sorted(expected))

    def test_should_complete_packages_for_import(self):
        source, offset = source_and_offset("import threading.current_t_|_")
        filename = self.project_file("test.py", source)
        completions = self.backend.rpc_get_completions(self.project_root,
                                                       filename,
                                                       source,
                                                       offset)
        self.assertEqual(sorted(name for (name, doc) in completions),
                         sorted(["hread"]))

    def test_should_not_complete_for_import(self):
        source, offset = source_and_offset("import foo.Conf_|_")
        filename = self.project_file("test.py", source)
        completions = self.backend.rpc_get_completions(self.project_root,
                                                       filename,
                                                       source,
                                                       offset)
        self.assertNotEqual(sorted(name for (name, doc) in completions),
                            sorted(["igParser"]))

    def test_should_not_fail_for_short_module(self):
        # This throws an error in Rope which elpy hopefully catches.
        # See #186
        source, offset = source_and_offset("from .. import foo_|_")
        filename = self.project_file("test.py", source)
        completions = self.backend.rpc_get_completions(self.project_root,
                                                       filename,
                                                       source,
                                                       offset)
        # This is strictly speaking superfluous. Just avoid an error.
        self.assertIsNotNone(completions)

    def test_should_complete_sys(self):
        source, offset = source_and_offset("import sys\nsys._|_")
        filename = self.project_file("test.py", source)
        completions = self.backend.rpc_get_completions(self.project_root,
                                                       filename,
                                                       source,
                                                       offset)
        self.assertIn('path', [symbol for (symbol, doc) in completions])

    @mock.patch('elpy.backends.ropebackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_completions(self.project_root, None,
                                         "test-source", 0)

        get_source.assert_called_with("test-source")


class TestGetDefinition(RopeBackendTestCase):
    def test_should_return_location_in_same_file(self):
        source, offset = source_and_offset(
            "import threading\n"
            "\n"
            "\n"
            "def other_function():\n"
            "    test_f_|_unction(1, 2)\n"
            "\n"
            "\n"
            "def test_function(a, b):\n"
            "    return a + b\n")
        if compat.PYTHON3:
            source = source.replace("(a, b)", "(b, a)")
        filename = self.project_file("test.py", "")  # Unsaved
        definition = self.backend.rpc_get_definition(self.project_root,
                                                     filename,
                                                     source,
                                                     offset)
        self.assertEqual(definition, (filename, 71))

    def test_should_return_location_in_different_file(self):
        source1 = ("def test_function(a, b):\n"
                   "    return a + b\n")
        file1 = self.project_file("test1.py", source1)
        source2, offset = source_and_offset("from test1 import test_function\n"
                                            "test_funct_|_ion(1, 2)\n")
        file2 = self.project_file("test2.py", source2)
        definition = self.backend.rpc_get_definition(self.project_root,
                                                     file2,
                                                     source2,
                                                     offset)
        self.assertEqual(definition, (file1, 4))

    def test_should_return_none_if_location_not_found(self):
        source, offset = source_and_offset("test_f_|_unction()\n")
        filename = self.project_file("test.py", source)
        definition = self.backend.rpc_get_definition(self.project_root,
                                                     filename,
                                                     source,
                                                     offset)
        self.assertIsNone(definition)

    def test_should_return_none_if_outside_of_symbol(self):
        source, offset = source_and_offset("test_function(_|_)\n")
        filename = self.project_file("test.py", source)
        definition = self.backend.rpc_get_definition(self.project_root,
                                                     filename,
                                                     source,
                                                     offset)
        self.assertIsNone(definition)

    def test_should_not_fail_on_inexisting_file(self):
        filename = self.project_root + "/doesnotexist.py"
        self.backend.rpc_get_definition(self.project_root,
                                        filename,
                                        "",
                                        0)

    def test_should_not_fail_on_empty_file(self):
        filename = self.project_file("test.py", "")
        self.backend.rpc_get_definition(self.project_root,
                                        filename,
                                        "",
                                        0)

    def test_should_not_fail_if_file_is_none(self):
        self.backend.rpc_get_definition(self.project_root,
                                        None,
                                        "",
                                        0)

    @mock.patch('elpy.backends.ropebackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_definition(self.project_root, None,
                                        "test-source", 0)

        get_source.assert_called_with("test-source")


class TestGetCalltip(RopeBackendTestCase):
    def test_should_get_calltip(self):
        source, offset = source_and_offset(
            "import threading\nthreading.Thread(_|_")
        filename = self.project_file("test.py", source)
        calltip = self.backend.rpc_get_calltip(self.project_root,
                                               filename,
                                               source,
                                               offset)
        if compat.PYTHON3:
            expected = ("threading.Thread.__init__(group=None, target=None, "
                        "name=None, args=(), kwargs=None, daemon=None, *)")
        else:
            expected = ("threading.Thread.__init__(group=None, target=None, "
                        "name=None, args=(), kwargs=None, verbose=None)")
        self.assertEqual(calltip, expected)

    def test_should_get_calltip_even_after_parens(self):
        source, offset = source_and_offset(
            "import threading\nthreading.Thread(foo()_|_")
        filename = self.project_file("test.py", source)
        calltip = self.backend.rpc_get_calltip(self.project_root,
                                               filename,
                                               source,
                                               offset)
        if compat.PYTHON3:
            expected = ("threading.Thread.__init__(group=None, target=None, "
                        "name=None, args=(), kwargs=None, daemon=None, *)")
        else:
            expected = ("threading.Thread.__init__(group=None, target=None, "
                        "name=None, args=(), kwargs=None, verbose=None)")
        self.assertEqual(calltip, expected)

    def test_should_return_none_for_bad_identifier(self):
        source, offset = source_and_offset(
            "froblgoo(_|_")
        filename = self.project_file("test.py", source)
        calltip = self.backend.rpc_get_calltip(self.project_root,
                                               filename,
                                               source,
                                               offset)
        self.assertIsNone(calltip)

    def test_should_not_fail_on_inexisting_file(self):
        filename = self.project_root + "/doesnotexist.py"
        self.backend.rpc_get_calltip(self.project_root,
                                     filename,
                                     "",
                                     0)

    def test_should_not_fail_if_file_is_none(self):
        self.backend.rpc_get_calltip(self.project_root,
                                     None,
                                     "",
                                     0)

    def test_should_return_none_for_module_syntax_errors(self):
        source, offset = source_and_offset(
            "class Foo(object):\n"
            "  def bar(self):\n"
            "    foo(_|_"
            "    bar("
            "\n"
            "  def a(self):\n"
            "    pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n"
            "\n"
            "  def b(self):\n"
            "  pass\n")

        filename = self.project_file("test.py", source)
        calltip = self.backend.rpc_get_calltip(self.project_root,
                                               filename,
                                               source,
                                               offset)
        self.assertIsNone(calltip)

    def test_should_return_none_for_bad_indentation(self):
        source, offset = source_and_offset(
            "def foo():\n"
            "       _|_print 23\n"
            "      print 17\n")
        filename = self.project_file("test.py", source)
        calltip = self.backend.rpc_get_calltip(self.project_root,
                                               filename,
                                               source,
                                               offset)
        self.assertIsNone(calltip)

    @mock.patch('elpy.backends.ropebackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_calltip(self.project_root, None, "test-source", 0)

        get_source.assert_called_with("test-source")


class TestGetDocstring(RopeBackendTestCase):
    def test_should_get_docstring(self):
        source, offset = source_and_offset(
            "import threading\nthreading.Thread.join_|_(")
        filename = self.project_file("test.py", source)
        docstring = self.backend.rpc_get_docstring(self.project_root,
                                                   filename,
                                                   source,
                                                   offset)

        def first_line(s):
            return s[:s.index("\n")]

        self.assertEqual(first_line(docstring),
                         'Thread.join(self, timeout=None):')

    def test_should_return_none_for_bad_identifier(self):
        source, offset = source_and_offset(
            "froblgoo_|_(\n")
        filename = self.project_file("test.py", source)
        docstring = self.backend.rpc_get_docstring(self.project_root,
                                                   filename,
                                                   source,
                                                   offset)
        self.assertIsNone(docstring)

    def test_should_not_fail_on_inexisting_file(self):
        filename = self.project_root + "/doesnotexist.py"
        self.backend.rpc_get_docstring(self.project_root,
                                       filename,
                                       "",
                                       0)

    def test_should_not_fail_if_file_is_none(self):
        self.backend.rpc_get_docstring(self.project_root,
                                       None,
                                       "",
                                       0)

    @mock.patch('elpy.backends.ropebackend.get_source')
    def test_should_call_get_source(self, get_source):
        get_source.return_value = "test-source"

        self.backend.rpc_get_docstring(self.project_root, None,
                                       "test-source", 0)

        get_source.assert_called_with("test-source")

########NEW FILE########
__FILENAME__ = test_rpc
"""Tests for elpy.rpc."""

import json
import unittest
import sys

from elpy import rpc
from elpy.tests.compat import StringIO


class TestFault(unittest.TestCase):
    def test_should_have_code_and_data(self):
        fault = rpc.Fault("Hello", code=250, data="Fnord")
        self.assertEqual(str(fault), "Hello")
        self.assertEqual(fault.code, 250)
        self.assertEqual(fault.data, "Fnord")

    def test_should_have_defaults_for_code_and_data(self):
        fault = rpc.Fault("Hello")
        self.assertEqual(str(fault), "Hello")
        self.assertEqual(fault.code, 500)
        self.assertIsNone(fault.data)


class TestJSONRPCServer(unittest.TestCase):
    def setUp(self):
        self.stdin = StringIO()
        self.stdout = StringIO()
        self.rpc = rpc.JSONRPCServer(self.stdin, self.stdout)

    def write(self, s):
        self.stdin.seek(0)
        self.stdin.truncate()
        self.stdout.seek(0)
        self.stdout.truncate()
        self.stdin.write(s)
        self.stdin.seek(0)

    def read(self):
        value = self.stdout.getvalue()
        self.stdin.seek(0)
        self.stdin.truncate()
        self.stdout.seek(0)
        self.stdout.truncate()
        return value


class TestInit(TestJSONRPCServer):
    def test_should_use_arguments(self):
        self.assertEqual(self.rpc.stdin, self.stdin)
        self.assertEqual(self.rpc.stdout, self.stdout)

    def test_should_default_to_sys(self):
        testrpc = rpc.JSONRPCServer()
        self.assertEqual(sys.stdin, testrpc.stdin)
        self.assertEqual(sys.stdout, testrpc.stdout)


class TestReadJson(TestJSONRPCServer):
    def test_should_read_json(self):
        objlist = [{'foo': 'bar'},
                   {'baz': 'qux', 'fnord': 'argl\nbargl'},
                   "beep\r\nbeep\r\nbeep"]
        self.write("".join([(json.dumps(obj) + "\n")
                            for obj in objlist]))
        for obj in objlist:
            self.assertEqual(self.rpc.read_json(),
                             obj)

    def test_should_raise_eof_on_eof(self):
        self.assertRaises(EOFError, self.rpc.read_json)

    def test_should_fail_on_malformed_json(self):
        self.write("malformed json\n")
        self.assertRaises(ValueError,
                          self.rpc.read_json)


class TestWriteJson(TestJSONRPCServer):
    def test_should_write_json_line(self):
        objlist = [{'foo': 'bar'},
                   {'baz': 'qux', 'fnord': 'argl\nbargl'},
                   ]
        for obj in objlist:
            self.rpc.write_json(**obj)
            self.assertEqual(json.loads(self.read()),
                             obj)


class TestHandleRequest(TestJSONRPCServer):
    def test_should_fail_if_json_does_not_contain_a_method(self):
        self.write(json.dumps(dict(params=[],
                                   id=23)))
        self.assertRaises(ValueError,
                          self.rpc.handle_request)

    def test_should_call_right_method(self):
        self.write(json.dumps(dict(method='foo',
                                   params=[1, 2, 3],
                                   id=23)))
        self.rpc.rpc_foo = lambda *params: params
        self.rpc.handle_request()
        self.assertEqual(json.loads(self.read()),
                         dict(id=23,
                              result=[1, 2, 3]))

    def test_should_pass_defaults_for_missing_parameters(self):
        def test_method(*params):
            self.args = params

        self.write(json.dumps(dict(method='foo')))
        self.rpc.rpc_foo = test_method
        self.rpc.handle_request()
        self.assertEqual(self.args, ())
        self.assertEqual(self.read(), "")

    def test_should_return_error_for_missing_method(self):
        self.write(json.dumps(dict(method='foo',
                                   id=23)))
        self.rpc.handle_request()
        result = json.loads(self.read())

        self.assertEqual(result["id"], 23)
        self.assertEqual(result["error"]["message"],
                         "Unknown method foo")

    def test_should_return_error_for_exception_in_method(self):
        def test_method():
            raise ValueError("An error was raised")

        self.write(json.dumps(dict(method='foo',
                                   id=23)))
        self.rpc.rpc_foo = test_method

        self.rpc.handle_request()
        result = json.loads(self.read())

        self.assertEqual(result["id"], 23)
        self.assertEqual(result["error"]["message"], "An error was raised")
        self.assertIn("traceback", result["error"])

    def test_should_not_include_traceback_for_warnings(self):
        def test_method():
            raise rpc.Warning("This is a warning")

        self.write(json.dumps(dict(method="foo",
                                   id=23)))
        self.rpc.rpc_foo = test_method

        self.rpc.handle_request()
        result = json.loads(self.read())

        self.assertEqual(result["id"], 23)
        self.assertEqual(result["error"]["message"], "This is a warning")
        self.assertNotIn("traceback", result["error"])

    def test_should_call_handle_for_unknown_method(self):
        def test_handle(method_name, args):
            return "It works"
        self.write(json.dumps(dict(method="doesnotexist",
                                   id=23)))
        self.rpc.handle = test_handle
        self.rpc.handle_request()
        self.assertEqual(json.loads(self.read()),
                         dict(id=23,
                              result="It works"))


class TestServeForever(TestJSONRPCServer):
    def handle_request(self):
        self.hr_called += 1
        if self.hr_called > 10:
            raise self.error()

    def setUp(self):
        super(TestServeForever, self).setUp()
        self.hr_called = 0
        self.error = KeyboardInterrupt
        self.rpc.handle_request = self.handle_request

    def test_should_call_handle_request_repeatedly(self):
        self.rpc.serve_forever()
        self.assertEqual(self.hr_called, 11)

    def test_should_return_on_some_errors(self):
        self.error = KeyboardInterrupt
        self.rpc.serve_forever()
        self.error = EOFError
        self.rpc.serve_forever()
        self.error = SystemExit
        self.rpc.serve_forever()

    def test_should_fail_on_most_errors(self):
        self.error = RuntimeError
        self.assertRaises(RuntimeError,
                          self.rpc.serve_forever)

########NEW FILE########
__FILENAME__ = test_server
"""Tests for the elpy.server module"""

import sys
import unittest

import mock

import elpy
from elpy import server


class TestServer(unittest.TestCase):
    def setUp(self):
        self.patches = [mock.patch.object(server, 'NativeBackend'),
                        mock.patch.object(server, 'RopeBackend'),
                        mock.patch.object(server, 'JediBackend')]
        (self.NativeBackend,
         self.RopeBackend,
         self.JediBackend) = [patch.__enter__() for patch in self.patches]
        (server.BACKEND_MAP["native"],
         server.BACKEND_MAP["rope"],
         server.BACKEND_MAP["jedi"]) = (self.NativeBackend,
                                        self.RopeBackend,
                                        self.JediBackend)
        self.NativeBackend.return_value.name = "native"
        self.RopeBackend.return_value.name = "rope"
        self.JediBackend.return_value.name = "jedi"

    def tearDown(self):
        for patch in self.patches:
            patch.__exit__(None, None)


class TestInit(TestServer):
    def test_should_select_rope_if_available(self):
        srv = server.ElpyRPCServer()
        self.assertEqual(srv.rpc_get_backend(), "rope")

    def test_should_select_jedi_if_rope_is_not_available(self):
        self.RopeBackend.return_value = None
        srv = server.ElpyRPCServer()
        self.assertEqual(srv.rpc_get_backend(), "jedi")

    def test_should_select_native_if_nothing_else_is_available(self):
        self.RopeBackend.return_value = None
        self.JediBackend.return_value = None
        srv = server.ElpyRPCServer()
        self.assertEqual(srv.rpc_get_backend(), "native")


class TestHandle(TestServer):
    def test_should_fail_for_missing_method(self):
        srv = server.ElpyRPCServer()
        srv.backend = object()
        self.assertRaises(server.Fault,
                          srv.handle, "does_not_exist", ())

    def test_should_call_method(self):
        srv = server.ElpyRPCServer()
        srv.backend = mock.MagicMock()
        srv.backend.rpc_does_exist.return_value = "It works"
        self.assertEqual(srv.handle("does_exist", (1, 2, 3)),
                         "It works")
        srv.backend.rpc_does_exist.assert_called_with(1, 2, 3)


class TestRPCVersion(TestServer):
    def test_should_return_current_version(self):
        srv = server.ElpyRPCServer()
        self.assertEqual(srv.rpc_version(),
                         elpy.__version__)


class TestRPCEcho(TestServer):
    def test_should_return_arguments(self):
        srv = server.ElpyRPCServer()
        self.assertEqual(srv.rpc_echo("hello", "world"),
                         ("hello", "world"))


class TestRPCGetSetBackend(TestServer):
    def test_should_fail_on_inexisting_backend(self):
        srv = server.ElpyRPCServer()
        self.assertRaises(ValueError,
                          srv.rpc_set_backend, "doesnotexist")

    def test_should_fail_if_backend_is_inactive(self):
        self.JediBackend.return_value = None
        srv = server.ElpyRPCServer()
        self.assertRaises(ValueError,
                          srv.rpc_set_backend, "jedi")

    def test_should_get_new_backend(self):
        srv = server.ElpyRPCServer()
        srv.rpc_set_backend("jedi")
        self.assertEqual(srv.rpc_get_backend(),
                         "jedi")


class TestRPCGetAvailableBackends(TestServer):
    def test_should_return_available_backends(self):
        srv = server.ElpyRPCServer()
        self.JediBackend.return_value = None
        self.assertEqual(sorted(srv.rpc_get_available_backends()),
                         sorted(["native", "rope"]))


class TestRPCGetPydocCompletions(TestServer):
    @mock.patch.object(server, 'get_pydoc_completions')
    def test_should_call_pydoc_completions(self, get_pydoc_completions):
        srv = server.ElpyRPCServer()
        srv.rpc_get_pydoc_completions()
        get_pydoc_completions.assert_called_with(None)
        srv.rpc_get_pydoc_completions("foo")
        get_pydoc_completions.assert_called_with("foo")


from elpy.tests import compat
from elpy.tests.support import BackendTestCase

import elpy.refactor


class RopeTestCase(BackendTestCase):
    def setUp(self):
        super(RopeTestCase, self).setUp()


class TestRPCGetRefactorOptions(RopeTestCase):
    @mock.patch.object(compat.builtins, '__import__')
    def test_should_fail_if_rope_is_not_available(self, import_):
        import_.side_effect = ImportError
        filename = self.project_file("foo.py", "")
        srv = server.ElpyRPCServer()
        self.assertRaises(ImportError, srv.rpc_get_refactor_options,
                          self.project_root, filename, 0)

    @mock.patch.object(elpy.refactor, 'Refactor')
    def test_should_initialize_and_call_refactor_object(self, Refactor):
        filename = self.project_file("foo.py", "import foo")
        srv = server.ElpyRPCServer()
        srv.rpc_get_refactor_options(self.project_root, filename, 5)
        Refactor.assert_called_with(self.project_root, filename)
        Refactor.return_value.get_refactor_options.assert_called_with(5, None)


class TestRPCRefactor(RopeTestCase):
    @mock.patch.object(compat.builtins, '__import__')
    def test_should_fail_if_rope_is_not_available(self, import_):
        import_.side_effect = ImportError
        filename = self.project_file("foo.py", "")
        srv = server.ElpyRPCServer()
        self.assertRaises(ImportError, srv.rpc_refactor,
                          self.project_root, filename, 'foo', ())

    @mock.patch.object(elpy.refactor, 'Refactor')
    def test_should_initialize_and_call_refactor_object_with_args(
            self, Refactor):
        filename = self.project_file("foo.py", "import foo")
        srv = server.ElpyRPCServer()
        srv.rpc_refactor(self.project_root, filename, 'foo', (1, 2, 3))
        Refactor.assert_called_with(self.project_root, filename)
        Refactor.return_value.get_changes.assert_called_with('foo', 1, 2, 3)

    @mock.patch.object(elpy.refactor, 'Refactor')
    def test_should_initialize_and_call_refactor_object_without_args(
            self, Refactor):
        filename = self.project_file("foo.py", "import foo")
        srv = server.ElpyRPCServer()
        srv.rpc_refactor(self.project_root, filename, 'foo', None)
        Refactor.assert_called_with(self.project_root, filename)
        Refactor.return_value.get_changes.assert_called_with('foo')

########NEW FILE########
__FILENAME__ = test_support
"""Tests for elpy.tests.support. Yep, we test test code."""

import unittest

from elpy.tests.support import source_and_offset


class TestSourceAndOffset(unittest.TestCase):
    def test_should_return_source_and_offset(self):
        self.assertEqual(source_and_offset("hello, _|_world"),
                         ("hello, world", 7))

    def test_should_handle_beginning_of_string(self):
        self.assertEqual(source_and_offset("_|_hello, world"),
                         ("hello, world", 0))

    def test_should_handle_end_of_string(self):
        self.assertEqual(source_and_offset("hello, world_|_"),
                         ("hello, world", 12))

########NEW FILE########
__FILENAME__ = pydocutils
import sys
import types

from pydoc import safeimport, resolve, ErrorDuringImport
from pkgutil import iter_modules

from elpy import compat

# Types we want to recurse into (nodes).
CONTAINER_TYPES = (type, types.ModuleType)
# Types of attributes we can get documentation for (leaves).
PYDOC_TYPES = (type,
               types.FunctionType,
               types.BuiltinFunctionType,
               types.BuiltinMethodType,
               types.MethodType,
               types.ModuleType)
if not compat.PYTHON3:  # Python 2 old style classes
    CONTAINER_TYPES = tuple(list(CONTAINER_TYPES) + [types.ClassType])
    PYDOC_TYPES = tuple(list(PYDOC_TYPES) + [types.ClassType])


def get_pydoc_completions(modulename):
    """Get possible completions for modulename for pydoc.

    Returns a list of possible values to be passed to pydoc.

    """
    modulename = compat.ensure_not_unicode(modulename)
    modulename = modulename.rstrip(".")
    if modulename == "":
        return sorted(get_modules())
    candidates = get_completions(modulename)
    if candidates:
        return sorted(candidates)
    needle = modulename
    if "." in needle:
        modulename, part = needle.rsplit(".", 1)
        candidates = get_completions(modulename)
    else:
        candidates = get_modules()
    return sorted(candidate for candidate in candidates
                  if candidate.startswith(needle))


def get_completions(modulename):
    modules = set("{0}.{1}".format(modulename, module)
                  for module in get_modules(modulename))

    try:
        module, name = resolve(modulename)
    except ImportError:
        return modules
    if isinstance(module, CONTAINER_TYPES):
        modules.update("{0}.{1}".format(modulename, name)
                       for name in dir(module)
                       if not name.startswith("_") and
                       isinstance(getattr(module, name),
                                  PYDOC_TYPES))
    return modules


def get_modules(modulename=None):
    """Return a list of modules and packages under modulename.

    If modulename is not given, return a list of all top level modules
    and packages.

    """
    modulename = compat.ensure_not_unicode(modulename)
    if not modulename:
        return ([modname for (importer, modname, ispkg)
                 in iter_modules()
                 if not modname.startswith("_")] +
                list(sys.builtin_module_names))
    try:
        module = safeimport(modulename)
    except ErrorDuringImport:
        return []
    if module is None:
        return []
    if hasattr(module, "__path__"):
        return [modname for (importer, modname, ispkg)
                in iter_modules(module.__path__)
                if not modname.startswith("_")]
    return []

########NEW FILE########
__FILENAME__ = __main__
"""Main interface to the RPC server.

You should be able to just run the following to use this module:

python -m elpy

The first line should be "elpy-rpc ready". If it isn't, something
broke.

"""

import sys

import elpy
from elpy.server import ElpyRPCServer

if __name__ == '__main__':
    sys.stdout.write('elpy-rpc ready ({0})\n'
                     .format(elpy.__version__))
    sys.stdout.flush()
    ElpyRPCServer().serve_forever()

########NEW FILE########
