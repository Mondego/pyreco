__FILENAME__ = AdvancedNewFile
import sublime
import sys

VERSION = int(sublime.version())

reloader = "advanced_new_file.reloader"

if VERSION > 3000:
    reloader = 'AdvancedNewFile.' + reloader
    from imp import reload


# Make sure all dependencies are reloaded on upgrade
if reloader in sys.modules:
    reload(sys.modules[reloader])

if VERSION > 3000:
    from .advanced_new_file import reloader
    from .advanced_new_file.commands import *
else:
    from advanced_new_file import reloader
    from advanced_new_file.commands import *

########NEW FILE########
__FILENAME__ = anf_util
import sublime
import re
import os

ALIAS_SETTING = "alias"
DEFAULT_INITIAL_SETTING = "default_initial"
USE_CURSOR_TEXT_SETTING = "use_cursor_text"
SHOW_FILES_SETTING = "show_files"
SHOW_PATH_SETTING = "show_path"
DEFAULT_ROOT_SETTING = "default_root"
DEFAULT_PATH_SETTING = "default_path"
DEFAULT_FOLDER_INDEX_SETTING = "default_folder_index"
OS_SPECIFIC_ALIAS_SETTING = "os_specific_alias"
IGNORE_CASE_SETTING = "ignore_case"
ALIAS_ROOT_SETTING = "alias_root"
ALIAS_PATH_SETTING = "alias_path"
ALIAS_FOLDER_INDEX_SETTING = "alias_folder_index"
DEBUG_SETTING = "debug"
AUTO_REFRESH_SIDEBAR_SETTING = "auto_refresh_sidebar"
COMPLETION_TYPE_SETTING = "completion_type"
COMPLETE_SINGLE_ENTRY_SETTING = "complete_single_entry"
USE_FOLDER_NAME_SETTING = "use_folder_name"
RELATIVE_FROM_CURRENT_SETTING = "relative_from_current"
DEFAULT_EXTENSION_SETTING = "default_extension"
FILE_PERMISSIONS_SETTING = "file_permissions"
FOLDER_PERMISSIONS_SETTING = "folder_permissions"
RENAME_DEFAULT_SETTING = "rename_default"
VCS_MANAGEMENT_SETTING = "vcs_management"
FILE_TEMPLATES_SETTING = "file_templates"
SHELL_INPUT_SETTING = "shell_input"
APPEND_EXTENSION_ON_MOVE_SETTING = "append_extension_on_move"
RELATIVE_FALLBACK_INDEX_SETTING = "relative_fallback_index"

SETTINGS = [
    ALIAS_SETTING,
    DEFAULT_INITIAL_SETTING,
    USE_CURSOR_TEXT_SETTING,
    SHOW_FILES_SETTING,
    SHOW_PATH_SETTING,
    DEFAULT_ROOT_SETTING,
    DEFAULT_PATH_SETTING,
    DEFAULT_FOLDER_INDEX_SETTING,
    OS_SPECIFIC_ALIAS_SETTING,
    IGNORE_CASE_SETTING,
    ALIAS_ROOT_SETTING,
    ALIAS_PATH_SETTING,
    ALIAS_FOLDER_INDEX_SETTING,
    DEBUG_SETTING,
    AUTO_REFRESH_SIDEBAR_SETTING,
    COMPLETION_TYPE_SETTING,
    COMPLETE_SINGLE_ENTRY_SETTING,
    USE_FOLDER_NAME_SETTING,
    RELATIVE_FROM_CURRENT_SETTING,
    DEFAULT_EXTENSION_SETTING,
    FILE_PERMISSIONS_SETTING,
    FOLDER_PERMISSIONS_SETTING,
    RENAME_DEFAULT_SETTING,
    VCS_MANAGEMENT_SETTING,
    FILE_TEMPLATES_SETTING,
    SHELL_INPUT_SETTING,
    APPEND_EXTENSION_ON_MOVE_SETTING,
    RELATIVE_FALLBACK_INDEX_SETTING
]

NIX_ROOT_REGEX = r"^/"
WIN_ROOT_REGEX = r"[a-zA-Z]:(/|\\)"
HOME_REGEX = r"^~"
PLATFORM = sublime.platform()
TOP_LEVEL_SPLIT_CHAR = ":"
IS_ST3 = int(sublime.version()) > 3000
IS_X64 = sublime.arch() == "x64"


def generate_creation_path(settings, base, path, append_extension=False):
        if PLATFORM == "windows":
            if not re.match(WIN_ROOT_REGEX, base):
                if IS_ST3:
                    drive, _ = os.path.splitdrive(base)
                else:
                    drive, _ = os.path.splitunc(base)
                if len(drive) == 0:
                    return base + TOP_LEVEL_SPLIT_CHAR + path
                else:
                    return os.path.join(base, path)
        else:
            if not re.match(NIX_ROOT_REGEX, base):
                return base + TOP_LEVEL_SPLIT_CHAR + path

        tokens = re.split(r"[/\\]", base) + re.split(r"[/\\]", path)
        if tokens[0] == "":
            tokens[0] = "/"
        if PLATFORM == "windows":
            tokens[0] = base[0:3]

        full_path = os.path.abspath(os.path.join(*tokens))
        if re.search(r"[/\\]$", path) or len(path) == 0:
            full_path += os.path.sep
        elif re.search(r"\.", tokens[-1]):
            if re.search(r"\.$", tokens[-1]):
                full_path += "."
        elif append_extension:
            filename = os.path.basename(full_path)
            if not os.path.exists(full_path):
                full_path += settings.get(DEFAULT_EXTENSION_SETTING)
        return full_path


def get_settings(view):
    settings = sublime.load_settings("AdvancedNewFile.sublime-settings")
    project_settings = {}
    local_settings = {}
    if view is not None:
        project_settings = view.settings().get('AdvancedNewFile', {})

    for setting in SETTINGS:
        local_settings[setting] = settings.get(setting)

    if type(project_settings) != dict:
        print("Invalid type %s for project settings" % type(project_settings))
        return local_settings

    for key in project_settings:
        if key in SETTINGS:
            if key == "alias":
                if IS_ST3:
                    local_settings[key] = dict(
                        local_settings[key].items() |
                        project_settings.get(key).items()
                    )
                else:
                    local_settings[key] = dict(
                        local_settings[key].items() +
                        project_settings.get(key).items()
                    )
            else:
                local_settings[key] = project_settings[key]
        else:
            print("AdvancedNewFile[Warning]: Invalid key " +
                  "'%s' in project settings.", key)

    return local_settings


def get_project_folder_data(use_folder_name):
    folders = []
    folder_entries = []
    window = sublime.active_window()
    project_folders = window.folders()

    if IS_ST3:
        project_data = window.project_data()

        if project_data is not None:
            if use_folder_name:
                for folder in project_data.get("folders", []):
                    folder_entries.append({})
            else:
                folder_entries = project_data.get("folders", [])
    else:
        for folder in project_folders:
            folder_entries.append({})
    for index in range(len(folder_entries)):
        folder_path = project_folders[index]
        folder_entry = folder_entries[index]
        if "name" in folder_entry:
            folders.append((folder_entry["name"], folder_path))
        else:
            folders.append((os.path.basename(folder_path), folder_path))

    return folders

########NEW FILE########
__FILENAME__ = command_base
import errno
import os
import re
import sublime
import shlex

from ..anf_util import *
from ..platform.windows_platform import WindowsPlatform
from ..platform.nix_platform import NixPlatform
from ..completions.nix_completion import NixCompletion
from ..completions.windows_completion import WindowsCompletion

VIEW_NAME = "AdvancedNewFileCreation"


class AdvancedNewFileBase(object):

    def __init__(self, window):
        super(AdvancedNewFileBase, self).__init__(window)

        if PLATFORM == "windows":
            self.platform = WindowsPlatform(window.active_view())
        else:
            self.platform = NixPlatform()

    def __generate_default_root(self):
        root_setting = self.settings.get(DEFAULT_ROOT_SETTING)
        path, folder_index = self.__parse_path_setting(
            root_setting, DEFAULT_FOLDER_INDEX_SETTING)
        if path is None and folder_index is None:
            return os.path.expanduser(self.settings.get(DEFAULT_PATH_SETTING))
        elif path is None:
            return self.__project_folder_from_index(folder_index)
        return path

    def __generate_alias_root(self):
        path, folder_index = self.__parse_path_setting(
            self.settings.get(ALIAS_ROOT_SETTING), ALIAS_FOLDER_INDEX_SETTING)
        if path is None and folder_index is None:
            return os.path.expanduser(self.settings.get(ALIAS_PATH_SETTING))
        elif path is None:
            if folder_index >= 0:
                return self.window.folders()[folder_index]
            else:
                return os.path.expanduser("~/")
        return path

    def generate_initial_path(self, initial_path=None):
        # Search for initial string
        if initial_path is not None:
            path = initial_path
        else:
            if self.settings.get(USE_CURSOR_TEXT_SETTING, False):
                cursor_text = self.get_cursor_path()
                if cursor_text != "":
                    path = cursor_text
            else:
                path = self.settings.get(DEFAULT_INITIAL_SETTING)

        return path

    def run_setup(self):
        self.view = self.window.active_view()
        self.settings = get_settings(self.view)
        self.root = None
        self.alias_root = None
        self.aliases = self.__get_aliases()

        self.root = self.__generate_default_root()
        self.alias_root = self.__generate_alias_root()

        # Need to fix this
        debug = self.settings.get(DEBUG_SETTING) or False

        completion_type = self.settings.get(COMPLETION_TYPE_SETTING)
        if completion_type == "windows":
            self.completion = WindowsCompletion(self)
        else:
            self.completion = NixCompletion(self)

    def __get_aliases(self):
        aliases = self.settings.get(ALIAS_SETTING)
        all_os_aliases = self.settings.get(OS_SPECIFIC_ALIAS_SETTING)
        for key in all_os_aliases:
            if PLATFORM in all_os_aliases.get(key):
                aliases[key] = all_os_aliases.get(key).get(PLATFORM)

        return aliases

    def __parse_path_setting(self, setting, index_setting):
        root = None
        folder_index = None
        if setting == "home":
            root = os.path.expanduser("~/")
        elif setting == "current":
            filename = self.view.file_name()
            if filename is not None:
                root = os.path.dirname(filename)
            else:
                root = os.path.expanduser("~/")
        elif setting == "project_folder":
            folder_index = self.settings.get(index_setting)
            folder_index = self.__validate_folder_index(folder_index)
        elif setting == "top_folder":
            folder_index = self.__validate_folder_index(0)
        elif setting == "path":
            pass
        else:
            print("Invalid root specifier")

        return (root, folder_index)

    def __validate_folder_index(self, folder_index):
        num_folders = len(self.window.folders())
        if num_folders == 0:
            folder_index = -1
        elif num_folders < folder_index:
            folder_index = 0
        return folder_index

    def split_path(self, path=""):
        HOME_REGEX = r"^~[/\\]"
        root = None
        try:
            root, path = self.platform.split(path)
            if self.settings.get(SHELL_INPUT_SETTING, False) and len(path) > 0:
                split_path = shlex.split(str(path))
                path = " ".join(split_path)
            # Parse if alias
            if TOP_LEVEL_SPLIT_CHAR in path and root is None:
                parts = path.rsplit(TOP_LEVEL_SPLIT_CHAR, 1)
                root, path = self.__translate_alias(parts[0])
                path_list = []
                if path != "":
                    path_list.append(path)
                if parts[1] != "":
                    path_list.append(parts[1])
                path = TOP_LEVEL_SPLIT_CHAR.join(path_list)
            elif re.match(r"^/", path):
                root, path_offset = self.platform.parse_nix_path(root, path)
                path = path[path_offset:]
            # Parse if tilde used
            elif re.match(HOME_REGEX, path) and root is None:
                root = os.path.expanduser("~")
                path = path[2:]
            elif (re.match(r"^\.{1,2}[/\\]", path) and
                  self.settings.get(RELATIVE_FROM_CURRENT_SETTING, False)):
                path_index = 2
                if self.view.file_name() is not None:
                    root = os.path.dirname(self.view.file_name())
                else:
                    folder_index = self.settings.get(RELATIVE_FALLBACK_INDEX_SETTING, 0)
                    folder_index = self.__validate_folder_index(folder_index)
                    root = self.__project_folder_from_index(folder_index)
                if re.match(r"^\.{2}[/\\]", path):
                    root = os.path.dirname(root)
                    path_index = 3
                path = path[path_index:]

            # Default
            if root is None:
                root = self.root
        except IndexError:
            root = os.path.expanduser("~")

        return root, path

    def __project_folder_from_index(self, folder_index):
        if folder_index >= 0:
            return self.window.folders()[folder_index]
        else:
            return os.path.expanduser("~/")

    def bash_expansion(self, path):
        if len(path) == 0:
            return path

        split_path = shlex.split(path)
        new_path = " ".join(split_path)
        return new_path

    def __translate_alias(self, path):
        root = None
        split_path = None
        if path == "" and self.view is not None:
            filename = self.view.file_name()
            if filename is not None:
                root = os.path.dirname(filename)
        else:
            split_path = path.split(TOP_LEVEL_SPLIT_CHAR)
            join_index = len(split_path) - 1
            target = path
            root_found = False
            use_folder_name = self.settings.get(USE_FOLDER_NAME_SETTING)
            while join_index >= 0 and not root_found:
                # Folder aliases
                for name, folder in get_project_folder_data(use_folder_name):
                    if name == target:
                        root = folder
                        root_found = True
                        break
                # Aliases from settings.
                for alias in self.aliases.keys():
                    if alias == target:
                        alias_path = self.aliases.get(alias)
                        if re.search(HOME_REGEX, alias_path) is None:
                            root = self.platform.get_alias_absolute_path(
                                self.alias_root, alias_path)
                            if root is not None:
                                break
                        root = os.path.expanduser(alias_path)
                        root_found = True
                        break
                remove = re.escape(split_path[join_index])
                target = re.sub(r":%s$" % remove, "", target)
                join_index -= 1

        if root is None:
            # Nothing found
            return None, path
        elif split_path is None:
            # Current directory as alias
            return os.path.abspath(root), ""
        else:
            # Add to index so we re
            join_index += 2
            return (os.path.abspath(root),
                    TOP_LEVEL_SPLIT_CHAR.join(split_path[join_index:]))

    def input_panel_caption(self):
        return ""

    def show_filename_input(self, initial):
        self.input_panel_view = self.window.show_input_panel(
            self.input_panel_caption(), initial,
            self.on_done, self.__update_filename_input, self.clear
        )

        self.input_panel_view.set_name(VIEW_NAME)
        self.input_panel_view.settings().set("auto_complete_commit_on_tab",
                                             False)
        self.input_panel_view.settings().set("tab_completion", False)
        self.input_panel_view.settings().set("translate_tabs_to_spaces", False)
        self.input_panel_view.settings().set("anf_panel", True)

    def __update_filename_input(self, path_in):
        new_content = path_in
        if self.settings.get(COMPLETION_TYPE_SETTING) == "windows":
            if "prev_text" in dir(self) and self.prev_text != path_in:
                if self.view is not None:
                    self.view.erase_status("AdvancedNewFile2")
        if path_in.endswith("\t"):
            new_content = self.completion.completion(path_in.replace("\t", ""))
        if new_content != path_in:
            self.input_panel_view.run_command("anf_replace",
                                              {"content": new_content})
        else:
            base, path = self.split_path(path_in)

            creation_path = generate_creation_path(self.settings, base, path,
                                                   True)
            if self.settings.get(SHOW_PATH_SETTING, False):
                self.update_status_message(creation_path)

    def update_status_message(self, creation_path):
        pass

    def entered_file_action(self, path):
        pass

    def on_done(self, input_string):
        if len(input_string) != 0:
            self.entered_filename(input_string)

        self.clear()
        self.refresh_sidebar()

    def entered_filename(self, filename):
        # Check if valid root specified for windows.
        if PLATFORM == "windows":
            if re.match(WIN_ROOT_REGEX, filename):
                root = filename[0:3]
                if not os.path.isdir(root):
                    sublime.error_message(root + " is not a valid root.")
                    self.clear()
                    return

        base, path = self.split_path(filename)
        file_path = generate_creation_path(self.settings, base, path, True)
        # Check for invalid alias specified.
        is_valid = (TOP_LEVEL_SPLIT_CHAR in filename and
                    not self.platform.is_absolute_path(base))
        if is_valid:
            if base == "":
                error_message = "Current file cannot be resolved."
            else:
                error_message = "'" + base + "' is an invalid alias."
            sublime.error_message(error_message)

        self.entered_file_action(file_path)

    def open_file(self, file_path):
        new_view = None
        if os.path.isdir(file_path):
            if not re.search(r"(/|\\)$", file_path):
                sublime.error_message("Cannot open view for '" + file_path +
                                      "'. It is a directory. ")
        else:
            new_view = self.window.open_file(file_path)
        return new_view

    def refresh_sidebar(self):
        if self.settings.get(AUTO_REFRESH_SIDEBAR_SETTING):
            try:
                self.window.run_command("refresh_folder_list")
            except:
                pass

    def clear(self):
        if self.view is not None:
            self.view.erase_status("AdvancedNewFile")
            self.view.erase_status("AdvancedNewFile2")

    def create(self, filename):
        base, filename = os.path.split(filename)
        self.create_folder(base)
        if filename != "":
            creation_path = os.path.join(base, filename)
            self.create_file(creation_path)

    def create_file(self, name):
        open(name, "a").close()
        if self.settings.get(FILE_PERMISSIONS_SETTING, "") != "":
            file_permissions = self.settings.get(FILE_PERMISSIONS_SETTING, "")
            os.chmod(name, int(file_permissions, 8))

    def create_folder(self, path):
        init_list = []
        temp_path = path
        while not os.path.exists(temp_path):
            init_list.append(temp_path)
            temp_path = os.path.dirname(temp_path)
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

        file_permissions = self.settings.get(FILE_PERMISSIONS_SETTING, "")
        folder_permissions = self.settings.get(FOLDER_PERMISSIONS_SETTING, "")
        for entry in init_list:
            if self.is_python:
                creation_path = os.path.join(entry, '__init__.py')
                open(creation_path, 'a').close()
                if file_permissions != "":
                    os.chmod(creation_path, int(file_permissions, 8))
            if folder_permissions != "":
                os.chmod(entry, int(folder_permissions, 8))

    def get_cursor_path(self):
        if self.view is None:
            return ""

        view = self.view
        path = ""
        for region in view.sel():
            syntax = view.scope_name(region.begin())
            if region.begin() != region.end():
                path = view.substr(region)
                break
            if (re.match(".*string.quoted.double", syntax) or
                    re.match(".*string.quoted.single", syntax)):
                path = view.substr(view.extract_scope(region.begin()))
                path = re.sub('^"|\'', '',  re.sub('"|\'$', '', path.strip()))
                break

        return path

    def _find_open_file(self, file_name):
        window = self.window
        if IS_ST3:
            return window.find_open_file(file_name)
        else:
            for view in window.views():
                view_name = view.file_name()
                if view_name != "" and view_name == file_name:
                    return view
        return None

########NEW FILE########
__FILENAME__ = delete_file_command
import os
import sublime
import sublime_plugin
import sys
from ..anf_util import *
from ..vcs.git.git_command_base import GitCommandBase
from .command_base import AdvancedNewFileBase


class AdvancedNewFileDelete(AdvancedNewFileBase, sublime_plugin.WindowCommand,
                            GitCommandBase):
    def __init__(self, window):
        super(AdvancedNewFileDelete, self).__init__(window)

    def run(self, current=False):
        self.run_setup()
        if current:
            self._delete_current_file()
        else:
            self.settings[SHOW_FILES_SETTING] = True
            self.show_filename_input("")

    def input_panel_caption(self):
        return 'Enter path of file to delete'

    def entered_file_action(self, path):
        self._delete_file(path)

    def update_status_message(self, creation_path):
        if self.view is not None:
            self.view.set_status("AdvancedNewFile", "Delete file at %s " %
                                 creation_path)
        else:
            sublime.status_message("Delete file at %s" % creation_path)

    def _git_rm(self, filepath):
        path, filename = os.path.split(filepath)
        result = self.run_command(["rm", filename], path)
        if result != 0:
            sublime.error_message("Git remove of %s failed." % (filepath))

    def _delete_current_file(self):
        filepath = self.window.active_view().file_name()
        self._delete_file(filepath)

    def _delete_file(self, filepath):
        if not filepath:
            return
        elif not os.path.isfile(filepath):
            sublime.error_message("%s is not a file" % filepath)
            return

        if not sublime.ok_cancel_dialog("Delete this file?\n%s" % filepath):
            return

        vcs_tracking = (self.file_tracked_by_git(filepath) and
                        self.settings.get(VCS_MANAGEMENT_SETTING))

        self.close_view(filepath)

        if vcs_tracking:
            self._git_rm(filepath)
        else:
            self._execute_delete_file(filepath)

        self.refresh_sidebar()

    def _execute_delete_file(self, filepath):
        if IS_ST3 and self._side_bar_enhancements_installed():
            import Default.send2trash as send2trash
            send2trash.send2trash(filepath)
        else:
            self.window.run_command("delete_file", {"files": [filepath]})

    def _side_bar_enhancements_installed(self):
        return "SideBarEnhancements.SideBar" in sys.modules

    def close_view(self, filepath):
        file_view = self._find_open_file(filepath)

        if file_view is not None:
            file_view.set_scratch(True)
            self.window.focus_view(file_view)
            self.window.run_command("close")

########NEW FILE########
__FILENAME__ = helper_commands
import sublime
import sublime_plugin


class AnfReplaceCommand(sublime_plugin.TextCommand):
    def run(self, edit, content):
        self.view.replace(edit, sublime.Region(0, self.view.size()), content)


class AdvancedNewFileCommand(sublime_plugin.WindowCommand):
    def run(self, is_python=False, initial_path=None,
            rename=False, rename_file=None):
        args = {}
        if rename:
            args["is_python"] = is_python
            args["initial_path"] = initial_path
            args["rename_file"] = rename_file
            self.window.run_command("advanced_new_file_move", args)
        else:
            args["is_python"] = is_python
            args["initial_path"] = initial_path
            self.window.run_command("advanced_new_file_new", args)

########NEW FILE########
__FILENAME__ = move_file_command
import os
import re
import shutil
import sublime_plugin

from ..vcs.git.git_command_base import GitCommandBase
from .command_base import AdvancedNewFileBase
from ..anf_util import *


class AdvancedNewFileMove(AdvancedNewFileBase, sublime_plugin.WindowCommand,
                          GitCommandBase):
    def __init__(self, window):
        super(AdvancedNewFileMove, self).__init__(window)

    def run(self, is_python=False, initial_path=None, rename_file=None):
        self.is_python = is_python
        self.run_setup()
        self.rename_filename = rename_file

        path = self.settings.get(RENAME_DEFAULT_SETTING)
        current_file = self.view.file_name()
        if current_file:
            directory, current_file_name = os.path.split(current_file)
            path = path.replace("<filepath>", current_file)
            path = path.replace("<filedirectory>", directory + os.sep)
        else:
            current_file_name = ""

        path = path.replace("<filename>", current_file_name)
        self.show_filename_input(
            path if len(path) > 0 else self.generate_initial_path())

    def input_panel_caption(self):
        caption = 'Enter a new path for current file'
        view = self.window.active_view()
        self.original_name = None
        if view is not None:
            view_file_name = view.file_name()
            if view_file_name:
                self.original_name = os.path.basename(view_file_name)

        if self.original_name is None:
            self.original_name = ""

        if self.is_python:
            caption = '%s (creates __init__.py in new dirs)' % caption
        return caption

    def _git_mv(self, from_filepath, to_filepath):
        path, filename = os.path.split(from_filepath)
        args = ["mv", filename, to_filepath]
        result = self.run_command(args, path)
        if result != 0:
            sublime.error_message("Git move of %s to %s failed" %
                                 (from_filepath, to_filepath))

    def entered_file_action(self, path):
        attempt_open = True
        path = self.try_append_extension(path)

        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            try:
                self.create_folder(directory)
            except OSError as e:
                attempt_open = False
                sublime.error_message("Cannot create '" + path + "'." +
                                      " See console for details")
                print("Exception: %s '%s'" % (e.strerror, e.filename))

        if attempt_open:
            self._rename_file(path)

    def is_copy_original_name(self, path):
        return (os.path.isdir(path) or
               os.path.basename(path) == "")

    def try_append_extension(self, path):
        if self.settings.get(APPEND_EXTENSION_ON_MOVE_SETTING, False):
            if not self.is_copy_original_name(path):
                _, new_path_extension = os.path.splitext(path)
                if new_path_extension == "":
                    if self.rename_filename is None:
                        _, extension = os.path.splitext(self.view.file_name())
                    else:
                        _, extension = os.path.splitext(self.rename_filename)
                    path += extension
        return path

    def _rename_file(self, file_path):
        if os.path.isdir(file_path) or re.search(r"(/|\\)$", file_path):
            # use original name if a directory path has been passed in.
            file_path = os.path.join(file_path, self.original_name)

        window = self.window
        if self.rename_filename:
            file_view = self._find_open_file(self.rename_filename)
            if file_view is not None:
                self.view.run_command("save")
                window.focus_view(file_view)
                window.run_command("close")

            self._move_action(self.rename_filename, file_path)

            if file_view is not None:
                self.open_file(file_path)

        elif self.view is not None and self.view.file_name() is not None:
            filename = self.view.file_name()
            if filename:
                self.view.run_command("save")
                window.focus_view(self.view)
                window.run_command("close")
                self._move_action(filename, file_path)
            else:
                content = self.view.substr(sublime.Region(0, self.view.size()))
                self.view.set_scratch(True)
                window.focus_view(self.view)
                window.run_command("close")
                with open(file_path, "w") as file_obj:
                    file_obj.write(content)
            self.open_file(file_path)
        else:
            sublime.error_message("Unable to move file. No file to move.")

    def _move_action(self, from_file, to_file):
        tracked_by_git = self.file_tracked_by_git(from_file)
        if tracked_by_git and self.settings.get(VCS_MANAGEMENT_SETTING):
            self._git_mv(from_file, to_file)
        else:
            shutil.move(from_file, to_file)

    def update_status_message(self, creation_path):
        if self.is_copy_original_name(creation_path):
            creation_path = os.path.join(creation_path, self.original_name)
        else:
            creation_path = self.try_append_extension(creation_path)
        if self.view is not None:
            self.view.set_status("AdvancedNewFile", "Moving file to %s " %
                                 creation_path)
        else:
            sublime.status_message("Moving file to %s" % creation_path)


class AdvancedNewFileMoveAtCommand(sublime_plugin.WindowCommand):
    def run(self, files):
        if len(files) != 1:
            return
        self.window.run_command("advanced_new_file_move",
                                {"rename_file": files[0]})

    def is_visible(self, files):
        return len(files) == 1

########NEW FILE########
__FILENAME__ = new_file_command
import sublime
import sublime_plugin
import os
import re
import xml.etree.ElementTree as ET

from .command_base import AdvancedNewFileBase
from ..lib.package_resources import get_resource
from ..anf_util import *


class AdvancedNewFileNew(AdvancedNewFileBase, sublime_plugin.WindowCommand):
    def __init__(self, window):
        super(AdvancedNewFileNew, self).__init__(window)

    def run(self, is_python=False, initial_path=None):
        self.is_python = is_python
        self.run_setup()
        self.show_filename_input(self.generate_initial_path(initial_path))

    def input_panel_caption(self):
        caption = 'Enter a path for a new file'
        if self.is_python:
            caption = '%s (creates __init__.py in new dirs)' % caption
        return caption

    def entered_file_action(self, path):
        if self.settings.get(SHELL_INPUT_SETTING, False):
            self.multi_file_action(self.curly_brace_expansion(path))
        else:
            self.single_file_action(path)

    def multi_file_action(self, paths):
        for path in paths:
            self.single_file_action(path, False)

    def single_file_action(self, path, apply_template=True):
        attempt_open = True
        file_exist = os.path.exists(path)
        if not file_exist:
            try:
                self.create(path)
            except OSError as e:
                attempt_open = False
                sublime.error_message("Cannot create '" + path +
                                      "'. See console for details")
                print("Exception: %s '%s'" % (e.strerror, e.filename))
        if attempt_open and os.path.isfile(path):
            file_view = self.open_file(path)
            if not file_exist and apply_template:
                file_view.settings().set("_anf_new", True)

    def curly_brace_expansion(self, path):
        if not self.curly_braces_balanced(path) or "{" not in path:
            return [path]
        paths = self.expand_single_curly_brace(path)

        while True:
            path_len = len(paths)
            temp_paths = []
            for expanded_path in paths:
                temp_paths.append(self.expand_single_curly_brace(expanded_path))
            paths = self.flatten_list(temp_paths)
            if path_len == len(paths):
                break

        return self.flatten_list(paths)

    def flatten_list(self, initial_list):
        if isinstance(initial_list, list):
            return [flattened for entry in initial_list for flattened in self.flatten_list(entry)]
        else:
            return [initial_list]


    # Assumes curly braces are balanced
    def expand_single_curly_brace(self, path):
        if "{" not in path:
            return [path]
        start, end = self.curly_brace_indecies(path)
        all_tokens = path[start + 1:end]
        paths = []
        for token in all_tokens.split(","):
            temp = path[0:start] + token + path[end + 1:]
            paths.append(temp)
        return paths

    # Assumes curly braces are balanced.
    def curly_brace_indecies(self, path, count=0,open_index=None):
        if len(path) == 0:
            return None
        c = path[0]
        if c == "{":
            return self.curly_brace_indecies(path[1:], count + 1, count)
        elif c == "}":
            return open_index, count
        else:
            return self.curly_brace_indecies(path[1:], count + 1, open_index)

    def curly_braces_balanced(self, path, count=0):
        if len(path) == 0 or count < 0:
            return count == 0

        c = path[0]
        if c == "{":
            return self.curly_braces_balanced(path[1:], count + 1)
        elif c == "}":
            return self.curly_braces_balanced(path[1:], count - 1)
        else:
            return self.curly_braces_balanced(path[1:], count)

    def update_status_message(self, creation_path):
        if self.view is not None:
            self.view.set_status("AdvancedNewFile", "Creating file at %s " %
                                 creation_path)
        else:
            sublime.status_message("Creating file at %s" % creation_path)


class AdvancedNewFileNewAtCommand(sublime_plugin.WindowCommand):
    def run(self, dirs):
        if len(dirs) != 1:
            return
        path = dirs[0] + os.sep
        self.window.run_command("advanced_new_file_new",
                                {"initial_path": path})

    def is_visible(self, dirs):
        return len(dirs) == 1


class AdvancedNewFileNewEventListener(sublime_plugin.EventListener):
    def on_load(self, view):
        if view.settings().get("_anf_new", False):
            absolute_file_path = view.file_name()
            if absolute_file_path is None:
                return
            file_name = self.get_basename(absolute_file_path)
            _, full_extension = os.path.splitext(file_name)
            if len(full_extension) == 0:
                extension = file_name
            else:
                extension = full_extension[1:]
            settings = get_settings(view)
            if extension in settings.get(FILE_TEMPLATES_SETTING):
                template = settings.get(FILE_TEMPLATES_SETTING)[extension]
                if type(template) == list:
                    if len(template) == 1:
                        view.run_command("insert_snippet", {"contents": self.get_snippet_from_file(template[0])})
                    else:
                        entries = list(map(self.get_basename, template))
                        self.entries = list(map(self.expand_path, template))
                        self.view = view
                        sublime.set_timeout(lambda: view.window().show_quick_panel(entries, self.quick_panel_selection), 10)
                else:
                    view.run_command("insert_snippet", {"contents": template})
            view.settings().set("_anf_new", "")

    def get_basename(self, path):
        return os.path.basename(os.path.expanduser(path))

    def expand_path(self, path):
        return os.path.expanduser(path)

    def quick_panel_selection(self, index):
        if index < 0:
            return
        self.view.run_command("insert_snippet", {"contents": self.get_snippet_from_file(self.entries[index])})

    def get_snippet_from_file(self, path):
        match = re.match(r"Packages/([^/]+)/(.+)", path)
        if match:
            tree = ET.fromstring(get_resource(match.group(1), match.group(2)))
        else:
            tree = ET.parse(os.path.expanduser(path))
        content = tree.find("content")
        return content.text

########NEW FILE########
__FILENAME__ = completion_base
import re
import os
from ..anf_util import *


class GenerateCompletionListBase(object):
    """docstring for GenerateCompletionListBase"""
    def __init__(self, command):
        super(GenerateCompletionListBase, self).__init__()
        self.top_level_split_char = ":"
        self.command = command
        self.aliases = command.aliases
        self.settings = command.settings

    def is_home(self, path):
        return re.match(r"^~[/\\]", path)

    def is_alias(self, path):
        return self.top_level_split_char in path

    def generate_completion_list(self, path_in):
        alias_list = []
        dir_list = []
        file_list = []
        if self.is_alias(path_in) or self.is_home(path_in):
            pass
        else:
            directory, filename = os.path.split(path_in)
            if len(directory) == 0:
                alias_list += self.generate_alias_auto_complete(filename)
                alias_list += self.generate_project_auto_complete(filename)
        base, path = self.command.split_path(path_in)
        full_path = generate_creation_path(self.settings, base, path)

        directory, filename = os.path.split(full_path)
        if os.path.isdir(directory):
            for d in os.listdir(directory):
                full_path = os.path.join(directory, d)
                if os.path.isdir(full_path):
                    is_file = False
                elif self.settings.get(SHOW_FILES_SETTING):
                    is_file = True
                else:
                    continue

                if self.compare_entries(d, filename):
                    if is_file:
                        file_list.append(d)
                    else:
                        dir_list.append(d)

        completion_list = alias_list + dir_list + file_list

        return sorted(completion_list), alias_list, dir_list, file_list

    def generate_project_auto_complete(self, base):
        folder_data = get_project_folder_data(
            self.settings.get(USE_FOLDER_NAME_SETTING))
        if len(folder_data) > 1:
            folders = [x[0] for x in folder_data]
            return self.generate_auto_complete(base, folders)
        return []

    def generate_alias_auto_complete(self, base):
        return self.generate_auto_complete(base, self.aliases)

    def generate_auto_complete(self, base, iterable_var):
        sugg = []
        for entry in iterable_var:
            compare_entry = entry
            compare_base = base
            if self.settings.get(IGNORE_CASE_SETTING):
                compare_entry = compare_entry.lower()
                compare_base = compare_base.lower()

            if self.compare_entries(compare_entry, compare_base):
                if entry not in sugg:
                    sugg.append(entry)
        return sugg

    def compare_entries(self, compare_entry, compare_base):
        if self.settings.get(IGNORE_CASE_SETTING):
            compare_entry = compare_entry.lower()
            compare_base = compare_base.lower()

        return compare_entry.startswith(compare_base)

########NEW FILE########
__FILENAME__ = nix_completion
import os
import re
import sublime

from .completion_base import GenerateCompletionListBase
from ..anf_util import *


class NixCompletion(GenerateCompletionListBase):
    def __init__(self, command):
        super(NixCompletion, self).__init__(command)

    def completion(self, path_in):
        pattern = r"(.*[/\\:])(.*)"

        (completion_list, alias_list,
            dir_list, file_list) = self.generate_completion_list(path_in)
        new_content = path_in
        if len(completion_list) > 0:
            common = os.path.commonprefix(completion_list)
            match = re.match(pattern, path_in)
            if match:
                new_content = re.sub(pattern, r"\1", path_in)
                new_content += common
            else:
                new_content = common
            if len(completion_list) > 1:
                dir_list = map(lambda s: s + "/", dir_list)
                alias_list = map(lambda s: s + ":", alias_list)
                status_message_list = sorted(list(dir_list) +
                                             list(alias_list) + file_list)
                sublime.status_message(", ".join(status_message_list))
            else:
                if completion_list[0] in alias_list:
                    new_content += ":"
                elif completion_list[0] in dir_list:
                    new_content += "/"

        return new_content

########NEW FILE########
__FILENAME__ = windows_completion
import re
from .completion_base import GenerateCompletionListBase
from ..anf_util import *


class WindowsCompletion(GenerateCompletionListBase):
    def __init__(self, command):
        super(WindowsCompletion, self).__init__(command)
        self.view = command.view

    def completion(self, path_in):
        pattern = r"(.*[/\\:])(.*)"
        match = re.match(pattern, path_in)
        if "prev_text" in dir(self) and self.prev_text == path_in:
            self.offset = (self.offset + 1) % len(self.completion_list)
        else:
            # Generate new completion list
            (self.completion_list, self.alias_list, self.dir_list,
                self.file_list) = self.generate_completion_list(path_in)
            self.offset = 0

            if len(self.completion_list) == 0:
                if match:
                    self.completion_list = [match.group(2)]
                else:
                    self.completion_list = [path_in]
        match = re.match(pattern, path_in)
        if match:
            completion = self.completion_list[self.offset]
            if self.settings.get(COMPLETE_SINGLE_ENTRY_SETTING):
                if len(self.completion_list) == 1:
                    if completion in self.alias_list:
                        completion += ":"
                    elif completion in self.dir_list:
                        completion += "/"
            new_content = re.sub(pattern, r"\1", path_in)
            new_content += completion
            first_token = False
        else:
            completion = self.completion_list[self.offset]
            if self.settings.get(COMPLETE_SINGLE_ENTRY_SETTING):
                if len(self.completion_list) == 1:
                    if completion in self.alias_list:
                        completion += ":"
                    elif completion in self.dir_list:
                        completion += "/"
            new_content = completion
            first_token = True

        if len(self.completion_list) > 1:
            if first_token:
                if self.view is not None:
                    if completion in self.alias_list:
                        self.view.set_status(
                            "AdvancedNewFile2", "Alias Completion")
                    elif completion in self.dir_list:
                        self.view.set_status(
                            "AdvancedNewFile2", "Directory Completion")
            self.prev_text = new_content
        else:
            self.prev_text = None

        return new_content

########NEW FILE########
__FILENAME__ = package_resources
"""
MIT License
Copyright (c) 2014 Scott Kuroda <scott.kuroda@gmail.com>

SHA: 623a4c1ec46dbbf3268bd88131bf0dfc845af787
"""
import sublime
import os
import zipfile
import tempfile
import re
import codecs

__all__ = [
    "get_resource",
    "get_binary_resource",
    "find_resource",
    "list_package_files",
    "get_package_and_resource_name",
    "get_packages_list",
    "extract_package",
    "get_sublime_packages"
]


VERSION = int(sublime.version())

def get_resource(package_name, resource, encoding="utf-8"):
    return _get_resource(package_name, resource, encoding=encoding)

def get_binary_resource(package_name, resource):
    return _get_resource(package_name, resource, return_binary=True)

def _get_resource(package_name, resource, return_binary=False, encoding="utf-8"):
    packages_path = sublime.packages_path()
    content = None
    if VERSION > 3013:
        try:
            if return_binary:
                content = sublime.load_binary_resource("Packages/" + package_name + "/" + resource)
            else:
                content = sublime.load_resource("Packages/" + package_name + "/" + resource)
        except IOError:
            pass
    else:
        path = None
        if os.path.exists(os.path.join(packages_path, package_name, resource)):
            path = os.path.join(packages_path, package_name, resource)
            content = _get_directory_item_content(path, return_binary, encoding)

        if VERSION >= 3006:
            sublime_package = package_name + ".sublime-package"

            packages_path = sublime.installed_packages_path()
            if content is None:
                if os.path.exists(os.path.join(packages_path, sublime_package)):
                    content = _get_zip_item_content(os.path.join(packages_path, sublime_package), resource, return_binary, encoding)

            packages_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"

            if content is None:
                if os.path.exists(os.path.join(packages_path, sublime_package)):
                    content = _get_zip_item_content(os.path.join(packages_path, sublime_package), resource, return_binary, encoding)

    return content


def find_resource(resource_pattern, package=None):
    file_set = set()
    if package == None:
        for package in get_packages_list():
            file_set.update(find_resource(resource_pattern, package))

        ret_list = list(file_set)
    else:
        file_set.update(_find_directory_resource(os.path.join(sublime.packages_path(), package), resource_pattern))

        if VERSION >= 3006:
            zip_location = os.path.join(sublime.installed_packages_path(), package + ".sublime-package")
            file_set.update(_find_zip_resource(zip_location, resource_pattern))
            zip_location = os.path.join(os.path.dirname(sublime.executable_path()), "Packages", package + ".sublime-package")
            file_set.update(_find_zip_resource(zip_location, resource_pattern))
        ret_list = map(lambda e: package + "/" + e, file_set)

    return sorted(ret_list)


def list_package_files(package, ignore_patterns=[]):
    """
    List files in the specified package.
    """
    package_path = os.path.join(sublime.packages_path(), package, "")
    path = None
    file_set = set()
    file_list = []
    if os.path.exists(package_path):
        for root, directories, filenames in os.walk(package_path):
            temp = root.replace(package_path, "")
            for filename in filenames:
                file_list.append(os.path.join(temp, filename))

    file_set.update(file_list)

    if VERSION >= 3006:
        sublime_package = package + ".sublime-package"
        packages_path = sublime.installed_packages_path()

        if os.path.exists(os.path.join(packages_path, sublime_package)):
            file_set.update(_list_files_in_zip(packages_path, sublime_package))

        packages_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"

        if os.path.exists(os.path.join(packages_path, sublime_package)):
           file_set.update(_list_files_in_zip(packages_path, sublime_package))

    file_list = []

    for filename in file_set:
        if not _ignore_file(filename, ignore_patterns):
            file_list.append(_normalize_to_sublime_path(filename))

    return sorted(file_list)

def _ignore_file(filename, ignore_patterns=[]):
    ignore = False
    directory, base = os.path.split(filename)
    for pattern in ignore_patterns:
        if re.match(pattern, base):
            return True

    if len(directory) > 0:
        ignore = _ignore_file(directory, ignore_patterns)

    return ignore


def _normalize_to_sublime_path(path):
    path = os.path.normpath(path)
    path = re.sub(r"^([a-zA-Z]):", "/\\1", path)
    path = re.sub(r"\\", "/", path)
    return path

def get_package_and_resource_name(path):
    """
    This method will return the package name and resource name from a path.

    Arguments:
    path    Path to parse for package and resource name.
    """
    package = None
    resource = None
    path = _normalize_to_sublime_path(path)
    if os.path.isabs(path):
        packages_path = _normalize_to_sublime_path(sublime.packages_path())
        if path.startswith(packages_path):
            package, resource = _search_for_package_and_resource(path, packages_path)

        if int(sublime.version()) >= 3006:
            packages_path = _normalize_to_sublime_path(sublime.installed_packages_path())
            if path.startswith(packages_path):
                package, resource = _search_for_package_and_resource(path, packages_path)

            packages_path = _normalize_to_sublime_path(os.path.dirname(sublime.executable_path()) + os.sep + "Packages")
            if path.startswith(packages_path):
                package, resource = _search_for_package_and_resource(path, packages_path)
    else:
        path = re.sub(r"^Packages/", "", path)
        split = re.split(r"/", path, 1)
        package = split[0]
        package = package.replace(".sublime-package", "")
        resource = split[1]

    return (package, resource)

def get_packages_list(ignore_packages=True, ignore_patterns=[]):
    """
    Return a list of packages.
    """
    package_set = set()
    package_set.update(_get_packages_from_directory(sublime.packages_path()))

    if int(sublime.version()) >= 3006:
        package_set.update(_get_packages_from_directory(sublime.installed_packages_path(), ".sublime-package"))

        executable_package_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"
        package_set.update(_get_packages_from_directory(executable_package_path, ".sublime-package"))


    if ignore_packages:
        ignored_list = sublime.load_settings(
            "Preferences.sublime-settings").get("ignored_packages", [])
    else:
        ignored_list = []

    for package in package_set:
        for pattern in ignore_patterns:
            if re.match(pattern, package):
                ignored_list.append(package)
                break

    for ignored in ignored_list:
        package_set.discard(ignored)

    return sorted(list(package_set))

def get_sublime_packages(ignore_packages=True, ignore_patterns=[]):
    package_list = get_packages_list(ignore_packages, ignore_patterns)
    extracted_list = _get_packages_from_directory(sublime.packages_path())
    return [x for x in package_list if x not in extracted_list]

def _get_packages_from_directory(directory, file_ext=""):
    package_list = []
    for package in os.listdir(directory):
        if not package.endswith(file_ext):
            continue
        else:
            package = package.replace(file_ext, "")

        package_list.append(package)
    return package_list

def _search_for_package_and_resource(path, packages_path):
    """
    Derive the package and resource from  a path.
    """
    relative_package_path = path.replace(packages_path + "/", "")

    package, resource = re.split(r"/", relative_package_path, 1)
    package = package.replace(".sublime-package", "")
    return (package, resource)


def _list_files_in_zip(package_path, package):
    if not os.path.exists(os.path.join(package_path, package)):
        return []

    ret_value = []
    with zipfile.ZipFile(os.path.join(package_path, package)) as zip_file:
        ret_value = zip_file.namelist()
    return ret_value

def _get_zip_item_content(path_to_zip, resource, return_binary, encoding):
    if not os.path.exists(path_to_zip):
        return None

    ret_value = None

    with zipfile.ZipFile(path_to_zip) as zip_file:
        namelist = zip_file.namelist()
        if resource in namelist:
            ret_value = zip_file.read(resource)
            if not return_binary:
                ret_value = ret_value.decode(encoding)

    return ret_value

def _get_directory_item_content(filename, return_binary, encoding):
    content = None
    if os.path.exists(filename):
        if return_binary:
            mode = "rb"
            encoding = None
        else:
            mode = "r"
        with codecs.open(filename, mode, encoding=encoding) as file_obj:
            content = file_obj.read()
    return content

def _find_zip_resource(path_to_zip, pattern):
    ret_list = []
    if os.path.exists(path_to_zip):
        with zipfile.ZipFile(path_to_zip) as zip_file:
            namelist = zip_file.namelist()
            for name in namelist:
                if re.search(pattern, name):
                    ret_list.append(name)

    return ret_list

def _find_directory_resource(path, pattern):
    ret_list = []
    if os.path.exists(path):
        path = os.path.join(path, "")
        for root, directories, filenames in os.walk(path):
            temp = root.replace(path, "")
            for filename in filenames:
                if re.search(pattern, os.path.join(temp, filename)):
                    ret_list.append(os.path.join(temp, filename))
    return ret_list

def extract_zip_resource(path_to_zip, resource, extract_dir=None):
    if extract_dir is None:
        extract_dir = tempfile.mkdtemp()

    file_location = None
    if os.path.exists(path_to_zip):
        with zipfile.ZipFile(path_to_zip) as zip_file:
            file_location = zip_file.extract(resource, extract_dir)

    return file_location

def extract_package(package):
    if VERSION >= 3006:
        package_location = os.path.join(sublime.installed_packages_path(), package + ".sublime-package")
        if not os.path.exists(package_location):
            package_location = os.path.join(os.path.dirname(sublime.executable_path()), "Packages", package + ".sublime-package")
            if not os.path.exists(package_location):
                package_location = None
        if package_location:
            with zipfile.ZipFile(package_location) as zip_file:
                extract_location = os.path.join(sublime.packages_path(), package)
                zip_file.extractall(extract_location)


########NEW FILE########
__FILENAME__ = nix_platform
import re
import os

from ..anf_util import *


class NixPlatform():
    def split(self, path):
        return None, path

    def parse_nix_path(self, root, path):
        return "/", 1

    def get_alias_absolute_path(self, root, path):
        if re.search(NIX_ROOT_REGEX, path) is None:
            return os.path.join(root, path)
        return None

    def is_absolute_path(self, path):
        return re.match(NIX_ROOT_REGEX, path) is not None

########NEW FILE########
__FILENAME__ = windows_platform
import re
import os

from ..anf_util import *


class WindowsPlatform(object):
    """docstring for WindowsPlatform"""
    def __init__(self, view):
        super(WindowsPlatform, self).__init__()
        self.view = view

    def split(self, path):
        if re.match(WIN_ROOT_REGEX, path):
            return path[0:3], path[3:]
        else:
            return None, path

    def parse_nix_path(self, root, path):
        path_offset = 1
        match = re.match(r"^/([a-zA-Z])/", path)
        if match:
            root = "%s:\\" % match.group(1)
            path_offset = 3
        else:
            root, _ = os.path.splitdrive(self.view.file_name())
            root += "\\"

        return root, path_offset

    def get_alias_absolute_path(self, root, path):
        if re.search(WIN_ROOT_REGEX, path) is None:
            return os.path.join(root, path)
        return None

    def is_absolute_path(self, path):
        return re.match(WIN_ROOT_REGEX, path) is not None

########NEW FILE########
__FILENAME__ = reloader
# Adapted from @wbond's resource loader.

import sys
import sublime

VERSION = int(sublime.version())

mod_prefix = "advanced_new_file"
reload_mods = []

if VERSION > 3000:
    mod_prefix = "AdvancedNewFile." + mod_prefix
    from imp import reload
    for mod in sys.modules:
        if mod[0:15] == 'AdvancedNewFile' and sys.modules[mod] is not None:
            reload_mods.append(mod)
else:

    for mod in sorted(sys.modules):
        if mod[0:17] == 'advanced_new_file' and sys.modules[mod] is not None:
            reload_mods.append(mod)

mods_load_order = [
    '',
    '.anf_util',
    '.completion_base',

    ".lib",
    ".lib.package_resources",

    ".completions",
    '.completions.nix_completion',
    '.completions.windows_completion',

    ".platform",
    ".platform.windows_platform",
    ".platform.nix_platform",

    ".vcs",
    ".vcs.git",
    ".vcs.git.git_command_base",

    ".commands",
    ".commands.command_base",
    ".commands.helper_commands",
    '.commands.new_file_command',
    ".commands.move_file_command",
    ".commands.delete_file_command"
]

for suffix in mods_load_order:
    mod = mod_prefix + suffix
    if mod in reload_mods:
        reload(sys.modules[mod])

########NEW FILE########
__FILENAME__ = git_command_base
import sublime
import subprocess
import os
from ...anf_util import *


# The Code to find git path is copied verbatim from kemayo's Git plugin.
# https://github.com/kemayo/sublime-text-git
def _test_paths_for_executable(paths, test_file):
    for directory in paths:
        file_path = os.path.join(directory, test_file)
        if os.path.exists(file_path) and os.access(file_path, os.X_OK):
            return file_path


def find_git():
    # It turns out to be difficult to reliably run git, with varying paths
    # and subprocess environments across different platforms. So. Let's hack
    # this a bit.
    # (Yes, I could fall back on a hardline "set your system path properly"
    # attitude. But that involves a lot more arguing with people.)
    path = os.environ.get('PATH', '').split(os.pathsep)
    if os.name == 'nt':
        git_cmd = 'git.exe'
    else:
        git_cmd = 'git'

    git_path = _test_paths_for_executable(path, git_cmd)

    if not git_path:
        # /usr/local/bin:/usr/local/git/bin
        if os.name == 'nt':
            extra_paths = (
                os.path.join(os.environ["ProgramFiles"], "Git", "bin"),
            )
            if IS_X64:
                extra_paths = extra_paths + (
                    os.path.join(
                        os.environ["ProgramFiles(x86)"], "Git", "bin"),
                )
        else:
            extra_paths = (
                '/usr/local/bin',
                '/usr/local/git/bin',
            )
        git_path = _test_paths_for_executable(extra_paths, git_cmd)
    return git_path

GIT = find_git()


# Base for git commands
class GitCommandBase(object):
    def __init__(self, window):
        pass

    # Command specific
    def file_tracked_by_git(self, filepath):
        git = GIT
        if git is not None:
            path, file_name = os.path.split(filepath)
            return self.run_command(
                ["ls-files", file_name, "--error-unmatch"], path) == 0
        else:
            return False

    def run_command(self, args, cwd):
        use_shell = PLATFORM == "windows"
        return subprocess.call([GIT] + args, cwd=cwd, shell=use_shell)

########NEW FILE########
