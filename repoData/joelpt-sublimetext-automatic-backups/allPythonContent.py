__FILENAME__ = AutomaticBackups
# Sublime Text 2 event listeners and commands interface for automatic backups.

import sublime
import sublime_plugin
import os
import shutil

import backup_paths
from backups_navigator import BackupsNavigator

nav = BackupsNavigator()  # our backup navigator state manager
settings = sublime.load_settings('Automatic Backups.sublime-settings')


class AutomaticBackupsEventListener(sublime_plugin.EventListener):

    """Creates an automatic backup of every file you save. This
    gives you a rudimentary mechanism for making sure you don't lose
    information while working."""

    def on_post_save(self, view):
        """When a file is saved, put a copy of the file into the
        backup directory."""
        self.save_view_to_backup(view)

    def on_activated(self, view):
        """Reinit backups navigator on view activation, just in case
        file was modified outside of ST2."""
        if view.file_name() != nav.current_file:
            nav.reinit()

    def on_load(self, view):
        """When a file is opened, put a copy of the file into the
        backup directory if backup_on_open_file setting is true."""
        if settings.get('backup_on_open_file', False):
            self.save_view_to_backup(view)

    def save_view_to_backup(self, view):
        """When a file is opened, put a copy of the file into the
        backup directory."""

        # don't save files above configured size
        if view.size() > settings.get("max_backup_file_size_bytes"):
            print 'Backup not saved, file too large (%d bytes)' % view.size()
            return

        filename = view.file_name()
        newname = backup_paths.get_backup_filepath(filename)
        if newname == None:
            return

        (backup_dir, file_to_write) = os.path.split(newname)

        # make sure that we have a directory to write into
        if os.access(backup_dir, os.F_OK) == False:
            os.makedirs(backup_dir)

        shutil.copy(filename, newname)
        print 'Backup saved to:', newname

        nav.reinit()


class AutomaticBackupsCommand(sublime_plugin.TextCommand):

    """Wires up received commands from keybindings to our BackupsNavigator
    instance."""

    def is_enabled(self, **kwargs):
        return self.view.file_name() is not None

    def run(self, edit, **kwargs):
        command = kwargs['command']

        if command in ('jump', 'step'):
            forward = kwargs['forward']

        if nav.index is None:
            nav.find_backups(self.view)

        if command == 'step':  # move 1 step forward or backward in history
            if forward:
                nav.nav_forwards()
            else:
                nav.nav_backwards()
        elif command == 'jump':  # jump to beginning/end of history
            if forward:
                nav.nav_end()
            else:
                nav.nav_start()

        if not nav.found_backup_files:
            sublime.status_message('No automatic backups found of this file')
            return

        if nav.at_last_backup():
            if command == 'merge':
                sublime.error_message('You are viewing the current version of this file. Navigate to a backup version before merging.')
                return
            if nav.just_reverted:
                sublime.status_message('Showing current version')
            else:
                nav.revert(self.view)
            return

        nav.backup = nav.found_backup_files[nav.index]
        nav.backup_full_path = os.path.join(nav.backup_path,
                nav.backup)

        if command == 'merge':
            nav.merge(self.view)
        else:
            nav.load_backup_to_view(self.view, edit)

########NEW FILE########
__FILENAME__ = backups_navigator
# Manages backup history navigation state and operations.

import os
import re
import sublime
from subprocess import Popen

import backup_paths

settings = sublime.load_settings('Automatic Backups.sublime-settings')


class BackupsNavigator:

    """Stateful manager for navigating through a view's backup history."""

    index = None
    just_reverted = False
    found_backup_files = None
    current_file = None

    def __init__(self):
        self.reinit()

    def reinit(self):
        self.index = None
        self.just_reverted = False
        self.found_backup_files = None
        self.current_file = None

    def find_backups(self, view):
        """Look in the backup folder for all backups of view's file."""
        fn = view.file_name()
        self.current_file = fn

        (f, ext) = os.path.splitext(os.path.split(fn)[1])
        self.backup_path = backup_paths.get_backup_path(view.file_name())

        dir_listing = os.listdir(self.backup_path)
        dir_listing.sort()

        date = r'-[0-9]{4}-[0-9]{2}-[0-9]{2}[_\-][0-9]{2}-[0-9]{2}-[0-9]{2}'
        pattern = '%s%s%s' % (f, date, ext)
        matcher = re.compile(pattern)

        self.found_backup_files = filter(lambda x: matcher.match(x),
                dir_listing)

        self.index = len(self.found_backup_files) - 1

    def nav_forwards(self):
        self.index += 1
        self.index = min(len(self.found_backup_files) - 1, self.index)

    def nav_backwards(self):
        self.index -= 1
        self.index = max(0, self.index)
        self.just_reverted = False

    def nav_start(self):
        self.index = 0

    def nav_end(self):
        self.index = len(self.found_backup_files) - 1

    def revert(self, view):
        """Revert current view to current file (drop all unsaved changes)."""
        sublime.set_timeout(lambda: do_revert(view), 50)
        self.just_reverted = True
        sublime.status_message('Showing current version')

    def at_last_backup(self):
        return self.index == len(self.found_backup_files) - 1

    def load_backup_to_view(self, view, edit):
        """Replaces contents of view with navigator's current backup file."""
        pos = view.viewport_position()

        with file(self.backup_full_path) as old_file:
            view.erase(edit, sublime.Region(0, view.size()))

            data = old_file.read()

            current_encoding = view.encoding()
            if current_encoding == 'Western (Windows 1252)':
                current_encoding = 'windows-1252'
            elif current_encoding == 'Undefined':
                current_encoding = 'utf-8'

            try:
                unicoded = unicode(data, current_encoding)
            except UnicodeDecodeError:
                unicoded = unicode(data, 'latin-1')  # should always work

            view.insert(edit, 0, unicoded)

        sublime.status_message('%s [%s of %s]' % (self.backup,
                               self.index + 1,
                               len(self.found_backup_files) - 1))

        reposition_view(view, pos)

    def merge(self, view):
        """Perform a merge with an external tool defined in settings."""
        merge_cmd = settings.get('backup_merge_command')

        if not merge_cmd:
            sublime.error_message(
                'Merge command is not set.\n' +
                'Set one in Preferences->Package Settings->Automatic Backups.')
            return

        cmd = merge_cmd.format(
           oldfilename=self.backup,
           oldfilepath=self.backup_full_path,
           curfilename=os.path.split(self.current_file)[1],
           curfilepath=self.current_file)
        sublime.status_message('Launching external merge tool')

        try:
            Popen(cmd)
        except Exception as e:
            sublime.error_message(
                'There was an error running your external merge command.\n' +
                'Please check your backup_merge_command setting.\n\n' +
                'Error given was:\n' + e.strerror + '\n\n' +
                'Check View->Show Console to view the command line that failed.'
            )
            print 'Attempted to execute:\n' + cmd


def do_revert(view):
    """Perform a revert of the current view (drop all changes)."""
    pos = view.viewport_position()
    view.run_command('revert')
    sublime.set_timeout(lambda: reposition_view(view, pos), 50)  # must delay


def reposition_view(view, pos):
    """Set viewport's scroll position in view to pos."""
    # I don't know why this works, but it does: Setting viewport to just pos
    # makes it scroll to the top of the buffer. Setting it to +1 then +0
    # position works. Probably something to do with ST2 getting confused that
    # the buffer changed and giving it a different pos causes it to resync
    # things vs. just giving it the same pos again.
    view.set_viewport_position((pos[0], pos[1] + 1))
    view.set_viewport_position((pos[0], pos[1] + 0))

########NEW FILE########
__FILENAME__ = backup_paths
# Helper functions for building backup file paths.

import sublime
import os
import re
import datetime

if sublime.platform() == 'windows':
    import win32helpers

settings = sublime.load_settings('Automatic Backups.sublime-settings')


def get_base_dir():
    """Returns the base dir for where we should store backups.
    If not configured in .sublime-settings, we'll take a best guess
    based on the user's OS."""

    # Configured setting
    backup_dir = settings.get('backup_dir', '')
    if backup_dir != '':
        return os.path.expanduser(backup_dir)

    # Windows: <user folder>/My Documents/Sublime Text Backups
    if sublime.platform() == 'windows':
        return os.path.join(
            win32helpers.get_shell_folder('Personal'),
            'Sublime Text Backups')

    # Linux/OSX/other: ~/sublime_backups
    return os.path.expanduser('~/.sublime/backups')


def timestamp_file(filename):
    """Puts a datestamp in filename, just before the extension."""

    now = datetime.datetime.today()
    (filepart, extensionpart) = os.path.splitext(filename)
    return '%s-%04d-%02d-%02d_%02d-%02d-%02d%s' % (
        filepart,
        now.year,
        now.month,
        now.day,
        now.hour,
        now.minute,
        now.second,
        extensionpart,
        )


def get_backup_path(filepath):
    """Returns a path where we want to backup filepath."""
    path = os.path.expanduser(os.path.split(filepath)[0])
    backup_base = get_base_dir()

    if sublime.platform() != 'windows':
        # remove any leading / before combining with backup_base
        path = re.sub(r'^/', '', path)
        return os.path.join(backup_base, path)

    # windows only: transform C: into just C
    path = re.sub(r'^(\w):', r'\1', path)

    # windows only: transform \\remotebox\share into network\remotebox\share
    path = re.sub(r'^\\\\([\w\-]{2,})', r'network\\\1', path)

    return os.path.join(backup_base, path)


def get_backup_filepath(filepath):
    """Returns a full file path for where we want to store a backup copy
    for filepath. Filename in file path returned will be timestamped."""
    filename = os.path.split(filepath)[1]
    return os.path.join(get_backup_path(filepath), timestamp_file(filename))

########NEW FILE########
__FILENAME__ = win32helpers
import os
import re
import sublime

try:
    import _winreg
except ImportError:
    if sublime.platform() == 'windows':
        sublime.error_message('There was an error importing the _winreg module required by the Automatic Backups plugin.')

def _substenv(m):
    return os.environ.get(m.group(1), m.group(0))


def get_shell_folder(name):
    """Returns the shell folder with the given name, eg "AppData", "Personal",
    "Programs". Environment variables in values of type REG_EXPAND_SZ are expanded
    if possible."""

    HKCU = _winreg.HKEY_CURRENT_USER
    USER_SHELL_FOLDERS = \
        r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
    key = _winreg.OpenKey(HKCU, USER_SHELL_FOLDERS)
    ret = _winreg.QueryValueEx(key, name)
    key.Close()
    if ret[1] == _winreg.REG_EXPAND_SZ and '%' in ret[0]:
        return re.compile(r'%([^|<>=^%]+)%').sub(_substenv, ret[0])
    else:
        return ret[0]

########NEW FILE########
