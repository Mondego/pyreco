__FILENAME__ = PHP Companion
from .php_companion.commands.expand_fqcn_command import ExpandFqcnCommand
from .php_companion.commands.find_use_command import FindUseCommand
from .php_companion.commands.import_namespace_command import ImportNamespaceCommand
from .php_companion.commands.import_use_command import ImportUseCommand
from .php_companion.commands.replace_fqcn_command import ReplaceFqcnCommand
from .php_companion.commands.goto_definition_scope import GotoDefinitionScopeCommand

########NEW FILE########
__FILENAME__ = expand_fqcn_command
import sublime
import sublime_plugin

import re

from ..utils import find_symbol

class ExpandFqcnCommand(sublime_plugin.TextCommand):
    def run(self, edit, leading_separator=False):
        view = self.view
        self.region = view.word(view.sel()[0])
        symbol = view.substr(self.region)

        if re.match(r"\w", symbol) is None:
            return sublime.status_message('Not a valid symbol "%s" !' % symbol)

        self.namespaces = find_symbol(symbol, view.window())
        self.leading_separator = leading_separator

        if len(self.namespaces) == 1:
            self.view.run_command("replace_fqcn", {"region_start": self.region.begin(), "region_end": self.region.end(), "namespace": self.namespaces[0][0], "leading_separator": self.leading_separator})

        if len(self.namespaces) > 1:
            view.window().show_quick_panel(self.namespaces, self.on_done)

    def on_done(self, index):
        if index == -1:
            return

        self.view.run_command("replace_fqcn", {"region_start": self.region.begin(), "region_end": self.region.end(), "namespace": self.namespaces[index][0], "leading_separator": self.leading_separator})
########NEW FILE########
__FILENAME__ = find_use_command
import sublime
import sublime_plugin

import re

from ..utils import find_symbol

class FindUseCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        view = self.view
        symbol = view.substr(view.word(view.sel()[0]))

        if re.match(r"\w", symbol) is None:
            return sublime.status_message('Not a valid symbol "%s" !' % symbol)

        self.namespaces = find_symbol(symbol, view.window())

        if len(self.namespaces) == 1:
            self.view.run_command("import_use", {"namespace": self.namespaces[0][0]})

        if len(self.namespaces) > 1:
            view.window().show_quick_panel(self.namespaces, self.on_done)

    def on_done(self, index):
        if index == -1:
            return

        self.view.run_command("import_use", {"namespace": self.namespaces[index][0]})
########NEW FILE########
__FILENAME__ = goto_definition_scope
import sublime
import sublime_plugin

import re

class GotoDefinitionScopeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        run = GTDRun(self.view, self.view.window())
        run.do()

class GTDRun:
    def __init__(self, view, window):
        self.view = view
        self.window = window
        self.selected_region = self.view.word(self.view.sel()[0])

    def do(self):
        if self.in_class_scope():
            selected_str = self.view.substr(self.selected_region)
            for symbol in self.view.symbols():
                if symbol[1] == selected_str:
                    self.view.sel().clear()
                    self.view.sel().add(symbol[0])
                    self.view.show(symbol[0])
                    return

        # falls back to the original functionality
        self.window.run_command("goto_definition")

    def in_class_scope(self):
        selected_point = self.selected_region.begin()
        # the search area is 60 pts wide, maybe it is not enough
        search_str = self.view.substr(sublime.Region(selected_point - 60,selected_point))

        return re.search("(\$this->|self::|static::)(\s)*$", search_str) != None

########NEW FILE########
__FILENAME__ = import_namespace_command
import sublime
import sublime_plugin

import os
import re

from ..settings import filename as settings_filename

class ImportNamespaceCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings(settings_filename()).get

        region = self.view.find(r"^(<\?php){0,1}\s*namespace\s[\w\\]+;", 0)

        if not region.empty():
            return sublime.status_message('namespace definition already exist !')

        # Filename to namespace
        filename = self.view.file_name()

        if (not filename.endswith(".php")):
            sublime.error_message("No .php extension")
            return

        # namespace begin at first camelcase dir
        namespaceStmt = os.path.dirname(filename)

        if (settings("start_dir_pattern")):
            pattern = re.compile(settings("start_dir_pattern"))
        else:
            pattern = r"^.*?((?:\/[A-Z][^\/]*)+)$"

        namespaceStmt = re.sub(pattern, '\\1', namespaceStmt)
        namespaceStmt = re.sub('/', '\\\\', namespaceStmt)
        namespaceStmt = namespaceStmt.strip("\\")

        region = self.view.find(r"<\?php", 0)
        if not region.empty():
            line = self.view.line(region)
            namespacePosition = settings("namespace_position");

            if namespacePosition == 'newline':
                line_contents = '\n\n' + "namespace " + namespaceStmt + ";"
            elif namespacePosition == 'inline':
                line_contents = ' ' + "namespace " + namespaceStmt + ";"

            self.view.insert(edit, line.end(), line_contents)
            return True

########NEW FILE########
__FILENAME__ = import_use_command
import sublime
import sublime_plugin

class ImportUseCommand(sublime_plugin.TextCommand):
    def run(self, edit, namespace):
        self.namespace = namespace

        if self.is_already_used():
            return sublime.status_message('Use already exist !')

        self.insert_use(edit)

    def insert_use(self, edit):
        if self.is_first_use():
            for location in [r"^\s*namespace\s+[\w\\]+[;{]", r"<\?php"]:
                inserted = self.insert_first_use(location, edit)

                if inserted:
                    break
        else:
            self.insert_use_among_others(edit)

    def insert_first_use(self, where, edit):
        region = self.view.find(where, 0)
        if not region.empty():
            line = self.view.line(region)
            self.view.insert(edit, line.end(), "\n\n" + self.build_uses())
            sublime.status_message('Successfully imported' + self.namespace)

            return True

        return False

    def insert_use_among_others(self, edit):
        regions = self.view.find_all(r"^(use\s+.+[;])", 0)
        if len(regions) > 0:
            region = regions[0]
            for r in regions:
                region = region.cover(r)

            self.view.replace(edit, region, self.build_uses())
            sublime.status_message('Successfully imported' + self.namespace)

    def build_uses(self):
        uses = []
        use_stmt = "use " + self.namespace + ";"

        self.view.find_all(r"^(use\s+.+[;])", 0, '$1', uses)
        uses.append(use_stmt)
        uses = list(set(uses))
        uses.sort()

        return "\n".join(uses)

    def is_already_used(self):
        region = self.view.find(("use " + self.namespace + ";").replace('\\', '\\\\'), 0)
        return not region.empty()

    def is_first_use(self):
        return len(self.view.find_all(r"^(use\s+.+[;])", 0)) == 0
########NEW FILE########
__FILENAME__ = replace_fqcn_command
import sublime
import sublime_plugin

class ReplaceFqcnCommand(sublime_plugin.TextCommand):
    def run(self, edit, region_start, region_end, namespace, leading_separator):
        region = sublime.Region(region_start, region_end)

        if (leading_separator):
            namespace = '\\' + namespace

        self.view.replace(edit, region, namespace)

        return True
########NEW FILE########
__FILENAME__ = settings
def filename():
    return 'PHP Companion.sublime-settings'
########NEW FILE########
__FILENAME__ = utils
import sublime

import re
import mmap
import contextlib
import subprocess
import json

from .settings import filename as settings_filename

def normalize_to_system_style_path(path):
    if sublime.platform() == "windows":
        path = re.sub(r"/([A-Za-z])/(.+)", r"\1:/\2", path)
        path = re.sub(r"/", r"\\", path)
    return path

def find_symbol(symbol, window):
    files = window.lookup_symbol_in_index(symbol)
    namespaces = []
    pattern = re.compile(b'^\s*namespace\s+([^;]+);', re.MULTILINE)
    settings = sublime.load_settings(settings_filename()).get

    def filter_file(file):
        if settings('exclude_dir'):
            for pattern in settings('exclude_dir'):
                pattern = re.compile(pattern)
                if pattern.match(file[1]):
                    return False

        return file

    for file in files:
        if filter_file(file):
            with open(normalize_to_system_style_path(file[0]), "rb") as f:
                with contextlib.closing(mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)) as m:
                    for match in re.findall(pattern, m):
                        namespaces.append([match.decode('utf-8') + "\\" + symbol, file[1]])
                        break

    if settings('allow_use_from_global_namespace'):
        namespaces += find_in_global_namespace(symbol)

    return namespaces

def find_in_global_namespace(symbol):
    definedClasses = subprocess.check_output(["php", "-r", "echo json_encode(get_declared_classes());"]);
    definedClasses = definedClasses.decode('utf-8')
    definedClasses = json.loads(definedClasses)
    definedClasses.sort()

    matches = []
    for phpClass in definedClasses:
        if symbol == phpClass:
            matches.append([phpClass, phpClass])

    return matches

########NEW FILE########
