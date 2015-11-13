__FILENAME__ = git_gutter
import sublime
import sublime_plugin
try:
    from GitGutter.view_collection import ViewCollection
except ImportError:
    from view_collection import ViewCollection


def plugin_loaded():
    """
    Ugly hack for icons in ST3
    kudos:
    github.com/facelessuser/BracketHighlighter/blob/BH2ST3/bh_core.py#L1380
    """
    from os import makedirs
    from os.path import exists, join

    icon_path = join(sublime.packages_path(), "Theme - Default")
    if not exists(icon_path):
        makedirs(icon_path)


class GitGutterCommand(sublime_plugin.WindowCommand):
    region_names = ['deleted_top', 'deleted_bottom',
                    'deleted_dual', 'inserted', 'changed',
                    'untracked', 'ignored']

    def run(self, force_refresh=False):
        self.view = self.window.active_view()
        if not self.view:
            # View is not ready yet, try again later.
            sublime.set_timeout(self.run, 1)
            return
        self.clear_all()
        if ViewCollection.untracked(self.view):
            self.bind_files('untracked')
        elif ViewCollection.ignored(self.view):
            self.bind_files('ignored')
        else:
            # If the file is untracked there is no need to execute the diff
            # update
            if force_refresh:
                ViewCollection.clear_git_time(self.view)
            inserted, modified, deleted = ViewCollection.diff(self.view)
            self.lines_removed(deleted)
            self.bind_icons('inserted', inserted)
            self.bind_icons('changed', modified)

    def clear_all(self):
        for region_name in self.region_names:
            self.view.erase_regions('git_gutter_%s' % region_name)

    def lines_to_regions(self, lines):
        regions = []
        for line in lines:
            position = self.view.text_point(line - 1, 0)
            region = sublime.Region(position, position)
            regions.append(region)
        return regions

    def lines_removed(self, lines):
        top_lines = lines
        bottom_lines = [line - 1 for line in lines if line > 1]
        dual_lines = []
        for line in top_lines:
            if line in bottom_lines:
                dual_lines.append(line)
        for line in dual_lines:
            bottom_lines.remove(line)
            top_lines.remove(line)

        self.bind_icons('deleted_top', top_lines)
        self.bind_icons('deleted_bottom', bottom_lines)
        self.bind_icons('deleted_dual', dual_lines)

    def icon_path(self, icon_name):
        if icon_name in ['deleted_top','deleted_bottom','deleted_dual']:
            if self.view.line_height() > 15:
                icon_name = icon_name + "_arrow"

        if int(sublime.version()) < 3014:
            path = '..'
            extn = ''
        else:
            path = 'Packages'
            extn = '.png'
        
        return path + '/GitGutter/icons/' + icon_name + extn

    def bind_icons(self, event, lines):
        regions = self.lines_to_regions(lines)
        event_scope = event
        if event.startswith('deleted'):
            event_scope = 'deleted'
        scope = 'markup.%s.git_gutter' % event_scope
        icon = self.icon_path(event)
        self.view.add_regions('git_gutter_%s' % event, regions, scope, icon)

    def bind_files(self, event):
        lines = []
        lineCount = ViewCollection.total_lines(self.view)
        i = 0
        while i < lineCount:
            lines += [i + 1]
            i = i + 1
        self.bind_icons(event, lines)

########NEW FILE########
__FILENAME__ = git_gutter_change
import sublime
import sublime_plugin
try:
    from GitGutter.view_collection import ViewCollection
except ImportError:
    from view_collection import ViewCollection


class GitGutterBaseChangeCommand(sublime_plugin.WindowCommand):

    def lines_to_blocks(self, lines):
        blocks = []
        last_line = -2
        for line in lines:
            if line > last_line + 1:
                blocks.append(line)
            last_line = line
        return blocks

    def run(self):
        view = self.window.active_view()

        inserted, modified, deleted = ViewCollection.diff(view)
        inserted = self.lines_to_blocks(inserted)
        modified = self.lines_to_blocks(modified)
        all_changes = sorted(inserted + modified + deleted)
        if all_changes:
            row, col = view.rowcol(view.sel()[0].begin())

            current_row = row + 1

            line = self.jump(all_changes, current_row)

            self.window.active_view().run_command("goto_line", {"line": line})


class GitGutterNextChangeCommand(GitGutterBaseChangeCommand):

    def jump(self, all_changes, current_row):
        return next((change for change in all_changes
                    if change > current_row), all_changes[0])


class GitGutterPrevChangeCommand(GitGutterBaseChangeCommand):

    def jump(self, all_changes, current_row):
        return next((change for change in reversed(all_changes)
                    if change < current_row), all_changes[-1])

########NEW FILE########
__FILENAME__ = git_gutter_compare
import sublime
import sublime_plugin

ST3 = int(sublime.version()) >= 3000
if ST3:
    from GitGutter.view_collection import ViewCollection
else:
    from view_collection import ViewCollection

class GitGutterCompareCommit(sublime_plugin.WindowCommand):
    def run(self):
        self.view = self.window.active_view()
        self.handler = ViewCollection.get_handler(self.view)

        self.results = self.commit_list()
        if self.results:
            self.window.show_quick_panel(self.results, self.on_select)

    def commit_list(self):
        result = self.handler.git_commits().decode("utf-8")
        return [r.split('\a', 2) for r in result.strip().split('\n')]

    def item_to_commit(self, item):
        return item[1].split(' ')[0]

    def on_select(self, selected):
        if 0 > selected < len(self.results):
            return
        item = self.results[selected]
        commit = self.item_to_commit(item)
        ViewCollection.set_compare(commit)
        ViewCollection.clear_git_time(self.view)
        ViewCollection.add(self.view)

class GitGutterCompareBranch(GitGutterCompareCommit):
    def commit_list(self):
        result = self.handler.git_branches().decode("utf-8")
        return [self.parse_result(r) for r in result.strip().split('\n')]

    def parse_result(self, result):
        pieces = result.split('\a')
        message = pieces[0]
        branch  = pieces[1].split("/")[2]
        commit  = pieces[2][0:7]
        return [branch, commit + " " + message]

class GitGutterCompareTag(GitGutterCompareCommit):
    def commit_list(self):
        result = self.handler.git_tags().decode("utf-8")
        if result:
            return [self.parse_result(r) for r in result.strip().split('\n')]
        else:
            sublime.message_dialog("No tags found in repository")

    def parse_result(self, result):
        pieces = result.split(' ')
        commit = pieces[0]
        tag    = pieces[1].replace("refs/tags/", "")
        return [tag, commit]

    def item_to_commit(self, item):
        return item[1]

class GitGutterCompareHead(sublime_plugin.WindowCommand):
    def run(self):
        self.view = self.window.active_view()
        ViewCollection.set_compare("HEAD")
        ViewCollection.clear_git_time(self.view)
        ViewCollection.add(self.view)

class GitGutterShowCompare(sublime_plugin.WindowCommand):
    def run(self):
        comparing = ViewCollection.get_compare()
        sublime.message_dialog("GitGutter is comparing against: " + comparing)


########NEW FILE########
__FILENAME__ = git_gutter_events
import time

import sublime
import sublime_plugin

ST3 = int(sublime.version()) >= 3000
if ST3:
    from GitGutter.view_collection import ViewCollection
else:
    from view_collection import ViewCollection


class GitGutterEvents(sublime_plugin.EventListener):

    def __init__(self):
        self._settings_loaded = False
        self.latest_keypresses = {}

    # Synchronous

    def on_modified(self, view):
        if self.settings_loaded():
            if not self.non_blocking and self.live_mode:
                ViewCollection.add(view)

    def on_clone(self, view):
        if self.settings_loaded():
            if not self.non_blocking:
                ViewCollection.add(view)

    def on_post_save(self, view):
        if self.settings_loaded():
            if not self.non_blocking:
                ViewCollection.add(view)

    def on_load(self, view):
        if self.settings_loaded():
            if not self.non_blocking and not self.live_mode:
                ViewCollection.add(view)

    def on_activated(self, view):
        if self.settings_loaded():
            if not self.non_blocking and self.focus_change_mode:
                ViewCollection.add(view)

    # Asynchronous

    def debounce(self, view, event_type, func):
        key = (event_type, view.file_name())
        this_keypress = time.time()
        self.latest_keypresses[key] = this_keypress

        def callback():
            latest_keypress = self.latest_keypresses.get(key, None)
            if this_keypress == latest_keypress:
                func(view)

        sublime.set_timeout_async(callback, settings.get("debounce_delay"))

    def on_modified_async(self, view):
        if self.settings_loaded() and self.non_blocking and self.live_mode:
            self.debounce(view, "modified", ViewCollection.add)

    def on_clone_async(self, view):
        if self.settings_loaded() and self.non_blocking and self.live_mode:
            self.debounce(view, "clone", ViewCollection.add)

    def on_post_save_async(self, view):
        if self.settings_loaded() and self.non_blocking and self.live_mode:
            self.debounce(view, "save", ViewCollection.add)

    def on_load_async(self, view):
        if self.settings_loaded() and self.non_blocking and not self.live_mode:
            self.debounce(view, "load", ViewCollection.add)

    def on_activated_async(self, view):
        if self.settings_loaded() and self.non_blocking and self.live_mode:
            self.debounce(view, "activated", ViewCollection.add)

    # Settings

    def settings_loaded(self):
        if settings and not self._settings_loaded:
            self._settings_loaded = self.load_settings()

        return self._settings_loaded


    def load_settings(self):
        self.live_mode = settings.get('live_mode')
        if self.live_mode is None:
            self.live_mode = True

        self.focus_change_mode = settings.get('focus_change_mode')
        if self.focus_change_mode is None:
            self.focus_change_mode = True

        self.non_blocking = settings.get('non_blocking')
        if self.non_blocking is None or int(sublime.version()) < 3014:
            self.non_blocking = False

        return True

def plugin_loaded():
    global settings
    settings = sublime.load_settings('GitGutter.sublime-settings')

if not ST3:
    plugin_loaded()


########NEW FILE########
__FILENAME__ = git_gutter_handler
import os
import sublime
import subprocess
import encodings
import re

try:
    from GitGutter import git_helper
    from GitGutter.view_collection import ViewCollection
except ImportError:
    import git_helper
    from view_collection import ViewCollection


class GitGutterHandler:

    def __init__(self, view):
        self.load_settings()
        self.view = view
        self.git_temp_file = ViewCollection.git_tmp_file(self.view)
        self.buf_temp_file = ViewCollection.buf_tmp_file(self.view)
        if self.on_disk():
            self.git_tree = git_helper.git_tree(self.view)
            self.git_dir = git_helper.git_dir(self.git_tree)
            self.git_path = git_helper.git_file_path(self.view, self.git_tree)

    def _get_view_encoding(self):
        # get encoding and clean it for python ex: "Western (ISO 8859-1)"
        # NOTE(maelnor): are we need regex here?
        pattern = re.compile(r'.+\((.*)\)')
        encoding = self.view.encoding()
        if pattern.match(encoding):
            encoding = pattern.sub(r'\1', encoding)

        encoding = encoding.replace('with BOM', '')
        encoding = encoding.replace('Windows', 'cp')
        encoding = encoding.replace('-', '_')
        encoding = encoding.replace(' ', '')
        return encoding

    def on_disk(self):
        # if the view is saved to disk
        return self.view.file_name() is not None

    def reset(self):
        if self.on_disk() and self.git_path and self.view.window():
            self.view.window().run_command('git_gutter')

    def get_git_path(self):
        return self.git_path

    def update_buf_file(self):
        chars = self.view.size()
        region = sublime.Region(0, chars)

        # Try conversion
        try:
            contents = self.view.substr(
                region).encode(self._get_view_encoding())
        except UnicodeError:
            # Fallback to utf8-encoding
            contents = self.view.substr(region).encode('utf-8')
        except LookupError:
            # May encounter an encoding we don't have a codec for
            contents = self.view.substr(region).encode('utf-8')

        contents = contents.replace(b'\r\n', b'\n')
        contents = contents.replace(b'\r', b'\n')
        f = open(self.buf_temp_file.name, 'wb')

        f.write(contents)
        f.close()

    def update_git_file(self):
        # the git repo won't change that often
        # so we can easily wait 5 seconds
        # between updates for performance
        if ViewCollection.git_time(self.view) > 5:
            open(self.git_temp_file.name, 'w').close()
            args = [
                self.git_binary_path,
                '--git-dir=' + self.git_dir,
                '--work-tree=' + self.git_tree,
                'show',
                ViewCollection.get_compare() + ':' + self.git_path,
            ]
            try:
                contents = self.run_command(args)
                contents = contents.replace(b'\r\n', b'\n')
                contents = contents.replace(b'\r', b'\n')
                f = open(self.git_temp_file.name, 'wb')
                f.write(contents)
                f.close()
                ViewCollection.update_git_time(self.view)
            except Exception:
                pass

    def total_lines(self):
        chars = self.view.size()
        region = sublime.Region(0, chars)
        lines = self.view.lines(region)
        return len(lines)

    # Parse unified diff with 0 lines of context.
    # Hunk range info format:
    #   @@ -3,2 +4,0 @@
    #     Hunk originally starting at line 3, and occupying 2 lines, now
    #     starts at line 4, and occupies 0 lines, i.e. it was deleted.
    #   @@ -9 +10,2 @@
    #     Hunk size can be omitted, and defaults to one line.
    # Dealing with ambiguous hunks:
    #   "A\nB\n" -> "C\n"
    #   Was 'A' modified, and 'B' deleted? Or 'B' modified, 'A' deleted?
    #   Or both deleted? To minimize confusion, let's simply mark the
    #   hunk as modified.
    def process_diff(self, diff_str):
        inserted = []
        modified = []
        deleted = []
        hunk_re = '^@@ \-(\d+),?(\d*) \+(\d+),?(\d*) @@'
        hunks = re.finditer(hunk_re, diff_str, re.MULTILINE)
        for hunk in hunks:
            start = int(hunk.group(3))
            old_size = int(hunk.group(2) or 1)
            new_size = int(hunk.group(4) or 1)
            if not old_size:
                inserted += range(start, start + new_size)
            elif not new_size:
                deleted += [start + 1]
            else:
                modified += range(start, start + new_size)
        if len(inserted) == self.total_lines() and not self.show_untracked:
            # All lines are "inserted"
            # this means this file is either:
            # - New and not being tracked *yet*
            # - Or it is a *gitignored* file
            return ([], [], [])
        else:
            return (inserted, modified, deleted)

    def diff(self):
        if self.on_disk() and self.git_path:
            self.update_git_file()
            self.update_buf_file()
            args = [
                self.git_binary_path, 'diff', '-U0', '--no-color',
                self.ignore_whitespace,
                self.patience_switch,
                self.git_temp_file.name,
                self.buf_temp_file.name,
            ]
            args = list(filter(None, args))  # Remove empty args
            results = self.run_command(args)
            encoding = self._get_view_encoding()
            try:
                decoded_results = results.decode(encoding.replace(' ', ''))
            except UnicodeError:
                decoded_results = results.decode("utf-8")
            return self.process_diff(decoded_results)
        else:
            return ([], [], [])

    def untracked(self):
        return self.handle_files([])

    def ignored(self):
        return self.handle_files(['-i'])

    def handle_files(self, additionnal_args):
        if self.show_untracked and self.on_disk() and self.git_path:
            args = [
                self.git_binary_path,
                '--git-dir=' + self.git_dir,
                '--work-tree=' + self.git_tree,
                'ls-files', '--other', '--exclude-standard',
            ] + additionnal_args + [
                os.path.join(self.git_tree, self.git_path),
            ]
            args = list(filter(None, args))  # Remove empty args
            results = self.run_command(args)
            encoding = self._get_view_encoding()
            try:
                decoded_results = results.decode(encoding.replace(' ', ''))
            except UnicodeError:
                decoded_results = results.decode("utf-8")
            return (decoded_results != "")
        else:
            return False

    def git_commits(self):
        args = [
            self.git_binary_path,
            '--git-dir=' + self.git_dir,
            '--work-tree=' + self.git_tree,
            'log', '--all',
            '--pretty=%s\a%h %an <%aE>\a%ad (%ar)',
            '--date=local', '--max-count=9000'
        ]
        results = self.run_command(args)
        return results

    def git_branches(self):
        args = [
            self.git_binary_path,
            '--git-dir=' + self.git_dir,
            '--work-tree=' + self.git_tree,
            'for-each-ref',
            '--sort=-committerdate',
            '--format=%(subject)\a%(refname)\a%(objectname)',
            'refs/heads/'
        ]
        results = self.run_command(args)
        return results

    def git_tags(self):
        args = [
            self.git_binary_path,
            '--git-dir=' + self.git_dir,
            '--work-tree=' + self.git_tree,
            'show-ref',
            '--tags',
            '--abbrev=7'
        ]
        results = self.run_command(args)
        return results

    def run_command(self, args):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                startupinfo=startupinfo, stderr=subprocess.PIPE)
        return proc.stdout.read()

    def load_settings(self):
        self.settings = sublime.load_settings('GitGutter.sublime-settings')
        self.user_settings = sublime.load_settings(
            'Preferences.sublime-settings')

        # Git Binary Setting
        self.git_binary_path = 'git'
        git_binary = self.user_settings.get(
            'git_binary') or self.settings.get('git_binary')
        if git_binary:
            self.git_binary_path = git_binary

        # Ignore White Space Setting
        self.ignore_whitespace = self.settings.get('ignore_whitespace')
        if self.ignore_whitespace == 'all':
            self.ignore_whitespace = '-w'
        elif self.ignore_whitespace == 'eol':
            self.ignore_whitespace = '--ignore-space-at-eol'
        else:
            self.ignore_whitespace = ''

        # Patience Setting
        self.patience_switch = ''
        patience = self.settings.get('patience')
        if patience:
            self.patience_switch = '--patience'

        # Untracked files
        self.show_untracked = self.settings.get(
            'show_markers_on_untracked_file')

########NEW FILE########
__FILENAME__ = git_helper
import os


def git_file_path(view, git_path):
    if not git_path:
        return False
    full_file_path = os.path.realpath(view.file_name())
    git_path_to_file = full_file_path.replace(git_path, '').replace('\\', '/')
    if git_path_to_file[0] == '/':
        git_path_to_file = git_path_to_file[1:]
    return git_path_to_file


def git_root(directory):
    if os.path.exists(os.path.join(directory, '.git')):
        return directory
    else:
        parent = os.path.realpath(os.path.join(directory, os.path.pardir))
        if parent == directory:
            # we have reached root dir
            return False
        else:
            return git_root(parent)


def git_tree(view):
    full_file_path = view.file_name()
    file_parent_dir = os.path.realpath(os.path.dirname(full_file_path))
    return git_root(file_parent_dir)


def git_dir(directory):
    if not directory:
        return False
    pre_git_dir = os.path.join(directory, '.git')
    if os.path.isfile(pre_git_dir):
        submodule_path = ''
        with open(pre_git_dir) as submodule_git_file:
            submodule_path = submodule_git_file.read()
            submodule_path = os.path.join('..', submodule_path.split()[1])

            submodule_git_dir = os.path.abspath(
                os.path.join(pre_git_dir, submodule_path))

        return submodule_git_dir
    else:
        return pre_git_dir

########NEW FILE########
__FILENAME__ = view_collection
import tempfile
import time


class ViewCollection:
    views = {} # Todo: these aren't really views but handlers. Refactor/Rename.
    git_times = {}
    git_files = {}
    buf_files = {}
    compare_against = "HEAD"

    @staticmethod
    def add(view):
        key = ViewCollection.get_key(view)
        try:
            from GitGutter.git_gutter_handler import GitGutterHandler
        except ImportError:
            from git_gutter_handler import GitGutterHandler
        handler = ViewCollection.views[key] = GitGutterHandler(view)
        handler.reset()
        return handler

    @staticmethod
    def git_path(view):
        key = ViewCollection.get_key(view)
        if key in ViewCollection.views:
            return ViewCollection.views[key].get_git_path()
        else:
            return False

    @staticmethod
    def get_key(view):
        return view.file_name()

    @staticmethod
    def has_view(view):
        key = ViewCollection.get_key(view)
        return key in ViewCollection.views

    @staticmethod
    def get_handler(view):
        if ViewCollection.has_view(view):
            key = ViewCollection.get_key(view)
            return ViewCollection.views[key]
        else:
            return ViewCollection.add(view)

    @staticmethod
    def diff(view):
        key = ViewCollection.get_key(view)
        return ViewCollection.views[key].diff()

    @staticmethod
    def untracked(view):
        key = ViewCollection.get_key(view)
        return ViewCollection.views[key].untracked()

    @staticmethod
    def ignored(view):
        key = ViewCollection.get_key(view)
        return ViewCollection.views[key].ignored()

    @staticmethod
    def total_lines(view):
        key = ViewCollection.get_key(view)
        return ViewCollection.views[key].total_lines()

    @staticmethod
    def git_time(view):
        key = ViewCollection.get_key(view)
        if not key in ViewCollection.git_times:
            ViewCollection.git_times[key] = 0
        return time.time() - ViewCollection.git_times[key]

    @staticmethod
    def clear_git_time(view):
        key = ViewCollection.get_key(view)
        ViewCollection.git_times[key] = 0

    @staticmethod
    def update_git_time(view):
        key = ViewCollection.get_key(view)
        ViewCollection.git_times[key] = time.time()

    @staticmethod
    def git_tmp_file(view):
        key = ViewCollection.get_key(view)
        if not key in ViewCollection.git_files:
            ViewCollection.git_files[key] = tempfile.NamedTemporaryFile()
            ViewCollection.git_files[key].close()
        return ViewCollection.git_files[key]

    @staticmethod
    def buf_tmp_file(view):
        key = ViewCollection.get_key(view)
        if not key in ViewCollection.buf_files:
            ViewCollection.buf_files[key] = tempfile.NamedTemporaryFile()
            ViewCollection.buf_files[key].close()
        return ViewCollection.buf_files[key]

    @staticmethod
    def set_compare(commit):
        print("GitGutter now comparing against:",commit)
        ViewCollection.compare_against = commit

    @staticmethod
    def get_compare():
        if ViewCollection.compare_against:
            return ViewCollection.compare_against
        else:
            return "HEAD"

########NEW FILE########
