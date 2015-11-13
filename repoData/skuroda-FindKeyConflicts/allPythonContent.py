__FILENAME__ = find_key_conflicts
import sublime
import sublime_plugin
import os
import json
import threading
import copy
import logging
import traceback

VERSION = int(sublime.version())

if VERSION >=3006:
    from FindKeyConflicts.lib.package_resources import *
    from FindKeyConflicts.lib.strip_commas import strip_dangling_commas
    from FindKeyConflicts.lib.minify_json import json_minify
else:
    from lib.package_resources import *
    from lib.strip_commas import strip_dangling_commas
    from lib.minify_json import json_minify


PACKAGES_PATH = sublime.packages_path()
PLATFORM = sublime.platform().title()
if PLATFORM == "Osx":
    PLATFORM = "OSX"
MODIFIERS = ('shift', 'ctrl', 'alt', 'super')

DONE_TEXT = "(Done)"
VIEW_SELECTED_LIST_TEXT = "(View Selected)"
VIEW_PACKAGES_LIST_TEXT = "(View Packages)"

# Set up logger
logging.basicConfig(format='[FindKeyConflicts] %(levelname)s %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.WARNING)


class GenerateKeymaps(object):
    def run(self, package=None):
        plugin_settings = sublime.load_settings("FindKeyConflicts.sublime-settings")

        self.window = self.window
        self.view = self.window.active_view()
        self.display_internal_conflicts = plugin_settings.get("display_internal_conflicts", True)
        self.show_args = plugin_settings.get("show_args", False)

        packages = get_packages_list()
        if package is None:
            thread = FindKeyConflictsCall(plugin_settings, packages)
        else:
            thread = FindPackageCommandsCall(plugin_settings, package)

        thread.start()
        self.handle_thread(thread)

    def generate_package_list(self):
        plugin_settings = sublime.load_settings("FindKeyConflicts.sublime-settings")
        view = self.window.active_view()
        packages = get_packages_list()
        packages.sort()

        ignored_packages = view.settings().get("ignored_packages", [])
        ignored_packages += plugin_settings.get("ignored_packages", [])

        packages = self.remove_ignored_packages(packages, ignored_packages)
        return packages

    def handle_thread(self, thread, i=0, move=1):
        if thread.is_alive():
            # This animates a little activity indicator in the status area
            before = i % 8
            after = (7) - before
            if not after:
                move = -1
            if not before:
                move = 1
            i += move
            self.view.set_status('find_key_conflicts', 'FindKeyConflicts [%s=%s]' % \
                (' ' * before, ' ' * after))

            # Timer to check again.
            sublime.set_timeout(lambda: self.handle_thread(thread, i, move), 100)
        else:
            self.view.erase_status('find_key_conflicts')
            sublime.status_message('FindKeyConflicts finished.')
            if thread.debug:
                content = ""
                for package in thread.debug_minified:
                    content += "%s\n" % package
                    content += "%s\n" % thread.debug_minified[package]

                panel = sublime.active_window().new_file()
                panel.set_scratch(True)
                panel.settings().set('word_wrap', False)
                panel.set_name("Debug")
                panel.run_command("insert_content", {"content": content})
            self.handle_results(thread.all_key_map)

    def handle_results(self, all_key_map):
        raise NotImplementedError("Should have implemented this")

    def remove_ignored_packages(self, packages, ignored_packages):
        for ignored_package in ignored_packages:
            try:
                packages.remove(ignored_package)
            except:
                logger.warning("FindKeyConflicts: Package '" + ignored_package + "' does not exist.")

        return packages

    def remove_non_conflicts(self, all_key_map):
        keylist = list(all_key_map.keys())

        keylist.sort()
        new_key_map = {}
        for key in keylist:
            value = all_key_map[key]
            if len(value["packages"]) > 1:
                new_key_map[key] = value
            elif len(value[value["packages"][0]]) > 1 and self.display_internal_conflicts:
                new_key_map[key] = value
        return new_key_map

    def find_overlap_conflicts(self, all_key_map):
        keylist = list(all_key_map.keys())
        keylist.sort()
        conflicts = {}
        for key in keylist:
            for key_nested in keylist:
                if key_nested.startswith(key + ","):
                    if key in conflicts:
                        conflicts[key].append(key_nested)
                    else:
                        conflicts[key] = [key_nested]
        return conflicts


class GenerateOutput(object):
    def __init__(self, all_key_map, show_args, window=None):
        self.window = window
        self.all_key_map = all_key_map
        self.show_args = show_args

    def generate_header(self, header):
        return '%s\n%s\n%s\n' % ('-' * len(header), header, '-' * len(header))

    def generate_overlapping_key_text(self, conflict_map):
        content = ""
        keys = list(conflict_map.keys())
        keys.sort()
        potential_conflicts_keys = list(conflict_map.keys())
        potential_conflicts_keys.sort()
        offset = 2
        for key_string in potential_conflicts_keys:
            content += self.generate_text(key_string, self.all_key_map, 0)
            for conflict in conflict_map[key_string]:
                content += self.generate_text(conflict, self.all_key_map, offset, "(", ")")
        return content

    def generate_key_map_text(self, key_map):
        content = ''
        keys = list(key_map.keys())

        keys.sort()
        for key_string in keys:
            content += self.generate_text(key_string, key_map)

        return content

    def generate_file(self, content, name="Keys"):
        panel = sublime.active_window().new_file()
        panel.set_scratch(True)
        panel.settings().set('word_wrap', False)
        panel.set_name(name)
        # content output
        panel.run_command("insert_content", {"content": content})

    def longest_command_length(self, key_map):
        pass

    def longest_package_length(self, key_map):
        pass

    def generate_text(self, key_string, key_map, offset=0, key_wrap_in='[', key_wrap_out=']'):
        content = ''
        item = key_map.get(key_string)
        content += " " * offset
        content += ' %s%s%s\n' % (key_wrap_in, key_string, key_wrap_out)
        packages = item.get("packages")

        for package in packages:
            package_map = item.get(package)
            for entry in package_map:
                content += " " * offset
                content += '   %*s %*s  %s\n' % \
                    (-40 + offset, entry['command'], -20, package, \
                    json.dumps(entry['context']) if "context" in entry else '')

        return content

    def generate_output_quick_panel(self, key_map):
        self.key_map = key_map
        quick_panel_items = []
        keylist = list(key_map.keys())
        keylist.sort()
        self.list = []
        for key in keylist:
            self.list.append(key)
            value = key_map[key]
            quick_panel_item = [key, ", ".join(value["packages"])]
            quick_panel_items.append(quick_panel_item)

        self.window.show_quick_panel(quick_panel_items, self.quick_panel_callback)

    def quick_panel_callback(self, index):
        if index == -1:
            return
        entry = self.list[index]
        content = self.generate_header("Entry Details")
        content += self.generate_text(entry, self.key_map)
        self.generate_file(content, "[%s] Details" % entry)


class FindKeyConflictsCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self, output="quick_panel"):
        self.output = output
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args, self.window)

        new_key_map = self.remove_non_conflicts(all_key_map)
        if self.output == "quick_panel":
            output.generate_output_quick_panel(new_key_map)
        elif self.output == "buffer":
            content = output.generate_header("Key Conflicts (Only direct conflicts)")
            content += output.generate_key_map_text(new_key_map)
            output.generate_file(content, "Key Conflicts")
        else:
            logger.warning("FindKeyConflicts[Warning]: Invalid output type specified")


class FindAllKeyConflictsCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self):
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args)
        new_key_map = self.remove_non_conflicts(all_key_map)
        overlapping_confilicts_map = self.find_overlap_conflicts(all_key_map)

        content = output.generate_header("Multi Part Key Conflicts")
        content += output.generate_overlapping_key_text(overlapping_confilicts_map)
        content += output.generate_header("Key Conflicts (Only direct conflicts)")
        content += output.generate_key_map_text(new_key_map)
        output.generate_file(content,  "All Key Conflicts")


class FindOverlapConflictsCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self):
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args)
        overlapping_confilicts_map = self.find_overlap_conflicts(all_key_map)

        content = output.generate_header("Multi Part Key Conflicts")
        content += output.generate_overlapping_key_text(overlapping_confilicts_map)
        output.generate_file(content,  "Overlap Key Conflicts")


class FindKeyMappingsCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self, output="quick_panel"):
        self.output = output
        GenerateKeymaps.run(self)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args, self.window)
        if self.output == "quick_panel":
            output.generate_output_quick_panel(all_key_map)
        elif self.output == "buffer":
            content = output.generate_header("All Key Mappings")
            content += output.generate_key_map_text(all_key_map)
            output.generate_file(content, "All Key Mappings")
        else:
            logger.warning("FindKeyConflicts[Warning]: Invalid output type specified")


class FindKeyConflictsWithPackageCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self, multiple=False):
        self.package_list = [entry for entry in GenerateKeymaps.generate_package_list(self)]
        self.multiple = multiple
        self.selected_list = []

        self.generate_quick_panel(self.package_list, self.package_list_callback, False)

    def generate_quick_panel(self, packages, callback, selected_list):
        self.quick_panel_list = copy.copy(packages)
        if self.multiple:
            if selected_list:
                self.quick_panel_list.append(VIEW_PACKAGES_LIST_TEXT)
            else:
                self.quick_panel_list.append(VIEW_SELECTED_LIST_TEXT)
            self.quick_panel_list.append(DONE_TEXT)
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.quick_panel_list, callback), 10)

    def selected_list_callback(self, index):
        if index == -1:
            return

        entry_text = self.quick_panel_list[index]
        if entry_text != VIEW_PACKAGES_LIST_TEXT and entry_text != DONE_TEXT:
            self.package_list.append(entry_text)
            self.selected_list.remove(entry_text)
        self.package_list.sort()

        if entry_text == DONE_TEXT:
            if len(self.selected_list) > 0:
                GenerateKeymaps.run(self)
        elif entry_text == VIEW_PACKAGES_LIST_TEXT:
            self.generate_quick_panel(self.package_list, self.package_list_callback, False)
        else:
            self.generate_quick_panel(self.selected_list, self.selected_list_callback, True)

    def package_list_callback(self, index):
        if index == -1:
            return

        if self.quick_panel_list[index] != DONE_TEXT and self.quick_panel_list[index] != VIEW_SELECTED_LIST_TEXT:
            self.selected_list.append(self.quick_panel_list[index])
            self.package_list.remove(self.quick_panel_list[index])
        self.selected_list.sort()

        if not self.multiple or self.quick_panel_list[index] == DONE_TEXT:
            if len(self.selected_list) > 0:
                GenerateKeymaps.run(self)
        elif self.quick_panel_list[index] == VIEW_SELECTED_LIST_TEXT:
            self.generate_quick_panel(self.selected_list, self.selected_list_callback, True)
        else:
            self.generate_quick_panel(self.package_list, self.package_list_callback, False)

    def handle_results(self, all_key_map):
        output = GenerateOutput(all_key_map, self.show_args)

        output_keymap = {}
        overlapping_conflicts_map = {}
        conflict_key_map = self.remove_non_conflicts(all_key_map)
        all_overlapping_confilicts_map = self.find_overlap_conflicts(all_key_map)
        for key in conflict_key_map:
            package_list = conflict_key_map[key]["packages"]
            for package in self.selected_list:
                if package in package_list:
                    output_keymap[key] = conflict_key_map[key]
                    break

        for overlap_base_key in all_overlapping_confilicts_map:
            for package in self.selected_list:
                if package in all_key_map[overlap_base_key]["packages"]:
                    overlapping_conflicts_map[overlap_base_key] = all_overlapping_confilicts_map[overlap_base_key]
                    break

            for overlap_key in all_overlapping_confilicts_map[overlap_base_key]:
                if package in all_key_map[overlap_key]["packages"]:
                    overlapping_conflicts_map[overlap_base_key] = all_overlapping_confilicts_map[overlap_base_key]
                    break

        content = "Key conflicts involving the following packages:\n"
        content += ", ".join(self.selected_list) + "\n\n"

        content += output.generate_header("Multi Part Key Conflicts")
        content += output.generate_overlapping_key_text(overlapping_conflicts_map)
        content += output.generate_header("Key Conflicts")
        content += output.generate_key_map_text(output_keymap)
        output.generate_file(content, "Key Conflicts")


class FindKeyConflictsCommandSearchCommand(GenerateKeymaps, sublime_plugin.WindowCommand):
    def run(self):
        packages = [entry for entry in GenerateKeymaps.generate_package_list(self)]
        self.package_list = []

        for package in packages:
            if len(find_resource("Default( \(%s\))?.sublime-keymap$" % PLATFORM, package)) > 0:
                self.package_list.append(package)


        self.generate_quick_panel(self.package_list, self.package_list_callback)

    def generate_quick_panel(self, packages, callback):
        self.window.show_quick_panel(packages, callback)

    def package_list_callback(self, index):
        if index == -1:
            return
        GenerateKeymaps.run(self, self.package_list[index])

    def handle_results(self, key_binding_commands):
        self.key_bindings = key_binding_commands
        entries = []
        for key_entry in key_binding_commands:
            entry = []
            entry.append(str(key_entry["command"]))
            entry.append(str(key_entry["keys"]))
            if "args" in key_entry:
                entry.append(str(key_entry["args"]))
            entries.append(entry)
        self.window.show_quick_panel(entries, self.entry_callback)

    def entry_callback(self, index):
        if index == -1:
            return
        command = self.key_bindings[index]["command"]
        args = None
        if "args" in self.key_bindings[index]:
            args = self.key_bindings[index]["args"]
        view = self.window.active_view()
        if view is not None:
            view.run_command(command, args)
        self.window.run_command(command, args)
        sublime.run_command(command, args)

class ThreadBase(threading.Thread):
    def manage_package(self, package):
        self.done = False
        file_list = list_package_files(package)
        platform_keymap = "default (%s).sublime-keymap" % (PLATFORM.lower())
        for filename in file_list:

            if filename.lower().endswith("default.sublime-keymap")or \
            filename.lower().endswith(platform_keymap):
                content = get_resource(package, filename)
                if content == None:
                    continue

                try:
                    if VERSION < 3013:
                        minified_content = json_minify(content)
                        minified_content = strip_dangling_commas(minified_content)
                        minified_content = minified_content.replace("\n", "\\\n")
                        if self.debug:
                            self.debug_minified[package] = minified_content
                        key_map = json.loads(minified_content)
                    else:
                        key_map = sublime.decode_value(content)
                except:
                    if not self.prev_error:
                        traceback.print_exc()
                        self.prev_error = True
                        sublime.error_message("Could not parse a keymap file. See console for details")
                    #error_path = os.path.join(os.path.basename(orig_path), filename)
                    logger.warning("FindKeyConflicts[Warning]: An error " + "occured while parsing '" + package + "'")
                    continue
                self.handle_key_map(package, key_map)
        self.done = True

    def check_ignore(self, key_array):
        if ",".join(key_array) in self.ignore_patterns:
            return True
        if len(key_array) > 1 or not self.ignore_single_key:
            return False

        for key_string in key_array:
            split_keys = key_string.split("+")
            try:
                i = split_keys.index("")
                split_keys[i] = "+"
                split_keys.remove("")
            except:
                pass

            if len(split_keys) == 1 and self.ignore_single_key:
                return True

        return False

    def order_key_string(self, key_string):
        split_keys = key_string.split("+")
        try:
            i = split_keys.index("")
            split_keys[i] = "+"
            split_keys.remove("")
        except:
            pass

        modifiers = []
        keys = []
        for key in split_keys:
            if key in MODIFIERS:
                modifiers.append(key)
            else:
                keys.append(key)
        modifiers.sort()
        keys.sort()
        ordered_key_string = "+".join(modifiers + keys)
        return ordered_key_string

    def handle_key_map(self, package, key_map):
        raise NotImplementedError("Should have implemented this")


class FindKeyConflictsCall(ThreadBase):
    def __init__(self, settings, packages):
        self.ignore_single_key = settings.get("ignore_single_key", False)
        self.ignore_patterns = settings.get("ignore_patterns", [])
        self.packages = packages
        self.all_key_map = {}
        self.debug_minified = {}
        self.debug = settings.get("debug", False)
        self.prev_error = False
        threading.Thread.__init__(self)

    def run(self):
        run_user = False
        temp = []
        for ignore_pattern in self.ignore_patterns:
            temp.append(self.order_key_string(ignore_pattern))
        self.ignore_patterns = temp
        if "Default" in self.packages:
            self.manage_package("Default")
            self.packages.remove("Default")
        if "User" in self.packages:
            run_user = True
            self.packages.remove("User")

        for package in self.packages:
            self.manage_package(package)
        if run_user:
            self.manage_package("User")

    def handle_key_map(self, package, key_map):
        for entry in key_map:
            keys = entry["keys"]
            # if "context" in entry:
            #     print(entry["context"])
            #     entry["context"].sort()
            key_array = []
            key_string = ""
            for key in keys:
                key_array.append(self.order_key_string(key))

            if self.check_ignore(key_array):
                continue
            key_string = ",".join(key_array)

            if key_string in self.all_key_map:
                tmp = self.all_key_map.get(key_string)
                if package not in tmp["packages"]:
                    tmp["packages"].append(package)
                    tmp[package] = [entry]
                else:
                    tmp[package].append(entry)

                self.all_key_map[key_string] = tmp
            else:
                new_entry = {}
                new_entry["packages"] = [package]
                new_entry[package] = [entry]
                self.all_key_map[key_string] = new_entry


class FindPackageCommandsCall(ThreadBase):
    def __init__(self, settings, package):
        self.package = package
        self.all_key_map = []
        self.debug_minified = {}
        self.debug = settings.get("debug", False)
        self.prev_error = False
        threading.Thread.__init__(self)

    def run(self):
        self.manage_package(self.package)

    def handle_key_map(self, package, key_map):
        for entry in key_map:
            keys = entry["keys"]
            key_array = []
            key_string = ""
            for key in keys:
                key_array.append(self.order_key_string(key))

            key_string = ",".join(key_array)

            entry["keys"] = key_string
            self.all_key_map.append(entry)

class InsertContentCommand(sublime_plugin.TextCommand):
    def run(self, edit, content):
        self.view.insert(edit, 0, content)
########NEW FILE########
__FILENAME__ = minify_json
'''
Created on 20/01/2011

v0.1 (C) Gerald Storer
MIT License
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.

Based on JSON.minify.js:
https://github.com/getify/JSON.minify
'''

import re

def json_minify(json,strip_space=True):
    tokenizer=re.compile('"|(/\*)|(\*/)|(//)|\n|\r')
    in_string = False
    in_multiline_comment = False
    in_singleline_comment = False

    new_str = []
    from_index = 0 # from is a keyword in Python

    for match in re.finditer(tokenizer,json):

        if not in_multiline_comment and not in_singleline_comment:
            tmp2 = json[from_index:match.start()]
            if not in_string and strip_space:
                tmp2 = re.sub('[ \t\n\r]*','',tmp2) # replace only white space defined in standard
            new_str.append(tmp2)

        from_index = match.end()

        if match.group() == '"' and not in_multiline_comment and not in_singleline_comment:
            escaped = re.search('(\\\\)*$',json[:match.start()])
            if not in_string or escaped is None or len(escaped.group()) % 2 == 0:
                # start of string with ", or unescaped " character found to end string
                in_string = not in_string
            from_index -= 1 # include " character in next catch

        elif match.group() == '/*' and not in_string and not in_multiline_comment and not in_singleline_comment:
            in_multiline_comment = True
        elif match.group() == '*/' and not in_string and in_multiline_comment and not in_singleline_comment:
            in_multiline_comment = False
        elif match.group() == '//' and not in_string and not in_multiline_comment and not in_singleline_comment:
            in_singleline_comment = True
        elif (match.group() == '\n' or match.group() == '\r') and not in_string and not in_multiline_comment and in_singleline_comment:
            in_singleline_comment = False
        elif not in_multiline_comment and not in_singleline_comment and (
             match.group() not in ['\n','\r',' ','\t'] or not strip_space):
                new_str.append(match.group())

    if not in_singleline_comment:
        new_str.append(json[from_index:])

    return ''.join(new_str)
########NEW FILE########
__FILENAME__ = package_resources
"""
MIT License
Copyright (c) 2013 Scott Kuroda <scott.kuroda@gmail.com>

SHA: d10b8514a1a7c06ef18677ef07256db65aefff4f
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
    "get_packages_list"
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

def get_packages_list(ignore_packages=True):
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
        ignored_package_list = sublime.load_settings(
            "Preferences.sublime-settings").get("ignored_packages", [])
        for ignored in ignored_package_list:
            package_set.discard(ignored)

    return sorted(list(package_set))

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

####################### Force resource viewer to reload ########################
import sys
if VERSION > 3000:
    from imp import reload
    if "FindKeyConflicts.find_key_conflicts" in sys.modules:
        reload(sys.modules["FindKeyConflicts.find_key_conflicts"])
else:
    if "find_key_conflicts" in sys.modules:
        reload(sys.modules["find_key_conflicts"])

########NEW FILE########
__FILENAME__ = strip_commas
'''
File Strip
Licensed under MIT
Copyright (c) 2012 Isaac Muse <isaacmuse@gmail.com>
'''

import re
import sublime

def strip_dangling_commas(text, preserve_lines=False):
    regex = re.compile(
        # ([1st group] dangling commas) | ([8th group] everything else)
        r"""((,([\s\r\n]*)(\]))|(,([\s\r\n]*)(\})))|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|.[^,"']*)""",
        re.MULTILINE | re.DOTALL
    )

    def remove_comma(m, preserve_lines=False):
        if preserve_lines:
            # ,] -> ] else ,} -> }
            return m.group(3) + m.group(4) if m.group(2) else m.group(6) + m.group(7)
        else:
            # ,] -> ] else ,} -> }
            return m.group(4) if m.group(2) else m.group(7)

    return (
        ''.join(
            map(
                lambda m: m.group(8) if m.group(8) else remove_comma(m, preserve_lines),
                regex.finditer(text)
            )
        )
    )

####################### Force resource viewer to reload ########################
import sys
if int(sublime.version()) > 3000:
    from imp import reload
    if "FindKeyConflicts.find_key_conflicts" in sys.modules:
        reload(sys.modules["FindKeyConflicts.find_key_conflicts"])
else:
    if "find_key_conflicts" in sys.modules:
        reload(sys.modules["find_key_conflicts"])

########NEW FILE########
