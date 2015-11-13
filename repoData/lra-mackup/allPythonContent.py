__FILENAME__ = application
"""
An Application Profile contains all the information about an application in
Mackup. Name, files, ...
"""
import os

from .mackup import Mackup
from . import utils


class ApplicationProfile(object):
    """Instantiate this class with application specific data"""

    def __init__(self, mackup, files):
        """
        Create an ApplicationProfile instance

        Args:
            mackup (Mackup)
            files (list)
        """
        assert isinstance(mackup, Mackup)
        assert isinstance(files, set)

        self.mackup = mackup
        self.files = list(files)

    def backup(self):
        """
        Backup the application config files

        Algorithm:
            if exists home/file
              if home/file is a real file
                if exists mackup/file
                  are you sure ?
                  if sure
                    rm mackup/file
                    mv home/file mackup/file
                    link mackup/file home/file
                else
                  mv home/file mackup/file
                  link mackup/file home/file
        """

        # For each file used by the application
        for filename in self.files:
            # Get the full path of each file
            filepath = os.path.join(os.environ['HOME'], filename)
            mackup_filepath = os.path.join(self.mackup.mackup_folder, filename)

            # If the file exists and is not already a link pointing to Mackup
            if ((os.path.isfile(filepath) or os.path.isdir(filepath))
                and not (os.path.islink(filepath)
                         and (os.path.isfile(mackup_filepath)
                              or os.path.isdir(mackup_filepath))
                         and os.path.samefile(filepath, mackup_filepath))):

                print "Backing up {}...".format(filename)

                # Check if we already have a backup
                if os.path.exists(mackup_filepath):

                    # Name it right
                    if os.path.isfile(mackup_filepath):
                        file_type = 'file'
                    elif os.path.isdir(mackup_filepath):
                        file_type = 'folder'
                    elif os.path.islink(mackup_filepath):
                        file_type = 'link'
                    else:
                        raise ValueError("Unsupported file: {}"
                                         .format(mackup_filepath))

                    # Ask the user if he really want to replace it
                    if utils.confirm("A {} named {} already exists in the"
                                     " backup.\nAre you sure that your want to"
                                     " replace it ?"
                                     .format(file_type, mackup_filepath)):
                        # Delete the file in Mackup
                        utils.delete(mackup_filepath)
                        # Copy the file
                        utils.copy(filepath, mackup_filepath)
                        # Delete the file in the home
                        utils.delete(filepath)
                        # Link the backuped file to its original place
                        utils.link(mackup_filepath, filepath)
                else:
                    # Copy the file
                    utils.copy(filepath, mackup_filepath)
                    # Delete the file in the home
                    utils.delete(filepath)
                    # Link the backuped file to its original place
                    utils.link(mackup_filepath, filepath)

    def restore(self):
        """
        Restore the application config files

        Algorithm:
            if exists mackup/file
              if exists home/file
                are you sure ?
                if sure
                  rm home/file
                  link mackup/file home/file
              else
                link mackup/file home/file
        """

        # For each file used by the application
        for filename in self.files:
            # Get the full path of each file
            mackup_filepath = os.path.join(self.mackup.mackup_folder, filename)
            home_filepath = os.path.join(os.environ['HOME'], filename)

            # If the file exists and is not already pointing to the mackup file
            # and the folder makes sense on the current platform (Don't sync
            # any subfolder of ~/Library on GNU/Linux)
            if ((os.path.isfile(mackup_filepath)
                 or os.path.isdir(mackup_filepath))
                and not (os.path.islink(home_filepath)
                         and os.path.samefile(mackup_filepath,
                                              home_filepath))
                and utils.can_file_be_synced_on_current_platform(filename)):

                print "Restoring {}...".format(filename)

                # Check if there is already a file in the home folder
                if os.path.exists(home_filepath):
                    # Name it right
                    if os.path.isfile(home_filepath):
                        file_type = 'file'
                    elif os.path.isdir(home_filepath):
                        file_type = 'folder'
                    elif os.path.islink(home_filepath):
                        file_type = 'link'
                    else:
                        raise ValueError("Unsupported file: {}"
                                         .format(mackup_filepath))

                    if utils.confirm("You already have a {} named {} in your"
                                     " home.\nDo you want to replace it with"
                                     " your backup ?"
                                     .format(file_type, filename)):
                        utils.delete(home_filepath)
                        utils.link(mackup_filepath, home_filepath)
                else:
                    utils.link(mackup_filepath, home_filepath)

    def uninstall(self):
        """
        Uninstall Mackup.
        Restore any file where it was before the 1st Mackup backup.

        Algorithm:
            for each file in config
                if mackup/file exists
                    if home/file exists
                        delete home/file
                    copy mackup/file home/file
            delete the mackup folder
            print how to delete mackup
        """
        # For each file used by the application
        for filename in self.files:
            # Get the full path of each file
            mackup_filepath = os.path.join(self.mackup.mackup_folder, filename)
            home_filepath = os.path.join(os.environ['HOME'], filename)

            # If the mackup file exists
            if (os.path.isfile(mackup_filepath)
                or os.path.isdir(mackup_filepath)):

                # Check if there is a corresponding file in the home folder
                if os.path.exists(home_filepath):
                    print "Moving {} back into your home...".format(filename)
                    # If there is, delete it as we are gonna copy the Dropbox
                    # one there
                    utils.delete(home_filepath)

                    # Copy the Dropbox file to the home folder
                    utils.copy(mackup_filepath, home_filepath)

########NEW FILE########
__FILENAME__ = appsdb
"""
The Applications Database provides an easy to use interface to load application
data from the Mackup Database (files)
"""
import os

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


from .constants import APPS_DIR
from .constants import CUSTOM_APPS_DIR


class ApplicationsDatabase(object):
    """Database containing all the configured applications"""

    def __init__(self):
        """
        Create a ApplicationsDatabase instance
        """
        # Build the dict that will contain the properties of each application
        self.apps = dict()

        for config_file in ApplicationsDatabase.get_config_files():
            config = configparser.SafeConfigParser(allow_no_value=True)

            # Needed to not lowercase the configuration_files in the ini files
            config.optionxform = str

            if config.read(config_file):
                # Get the filename without the directory name
                filename = os.path.basename(config_file)
                # The app name is the cfg filename with the extension
                app_name = filename[:-len('.cfg')]

                # Start building a dict for this app
                self.apps[app_name] = dict()

                # Add the fancy name for the app, for display purpose
                app_pretty_name = config.get('application', 'name')
                self.apps[app_name]['name'] = app_pretty_name

                # Add the configuration files to sync
                self.apps[app_name]['configuration_files'] = set()
                if config.has_section('configuration_files'):
                    for path in config.options('configuration_files'):
                        if path.startswith('/'):
                            raise ValueError('Unsupported absolute path: {}'
                                             .format(path))
                        self.apps[app_name]['configuration_files'].add(path)

    @staticmethod
    def get_config_files():
        """
        Return a list of configuration files describing the apps supported by
        Mackup. The files return are absolute fullpath to those files.
        e.g. /usr/lib/mackup/applications/bash.cfg

        Returns:
            set of strings.
        """
        # Configure the config parser
        apps_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                APPS_DIR)
        custom_apps_dir = os.path.join(os.environ['HOME'], CUSTOM_APPS_DIR)

        # Build the list of stock application config files
        config_files = set()
        for filename in os.listdir(apps_dir):
            if filename.endswith('.cfg'):
                config_files.add(os.path.join(apps_dir, filename))

        # Append the list of custom application config files
        if os.path.isdir(custom_apps_dir):
            for filename in os.listdir(custom_apps_dir):
                if filename.endswith('.cfg'):
                    config_files.add(os.path.join(custom_apps_dir,
                                                  filename))
        return config_files

    def get_name(self, name):
        """
        Return the fancy name of an application

        Args:
            name (str)

        Returns:
            str
        """
        return self.apps[name]['name']

    def get_files(self, name):
        """
        Return the list of config files of an application

        Args:
            name (str)

        Returns:
            set of str.
        """
        return self.apps[name]['configuration_files']

    def get_app_names(self):
        """
        Return the list of application names that are available in the database

        Returns:
            set of str.
        """
        app_names = set()
        for name in self.apps:
            app_names.add(name)

        return app_names

    def get_pretty_app_names(self):
        """
        Return the list of pretty app names that are available in the database

        Returns:
            set of str.
        """
        pretty_app_names = set()
        for app_name in self.get_app_names():
            pretty_app_names.add(self.get_name(app_name))

        return pretty_app_names

########NEW FILE########
__FILENAME__ = config
"""
Package used to manage the .mackup.cfg config file
"""

import os
import os.path

from constants import (MACKUP_BACKUP_PATH,
                       MACKUP_CONFIG_FILE,
                       ENGINE_DROPBOX,
                       ENGINE_GDRIVE,
                       ENGINE_FS)

from utils import (error,
                   get_dropbox_folder_location,
                   get_google_drive_folder_location)
try:
    import configparser
except ImportError:
    import ConfigParser as configparser


class Config(object):

    def __init__(self, filename=None):
        """
        Args:
            filename (str): Optional filename of the config file. If empty,
                            defaults to MACKUP_CONFIG_FILE
        """
        assert isinstance(filename, str) or filename is None

        # Initialize the parser
        self._parser = self._setup_parser(filename)

        # Do we have an old config file ?
        self._warn_on_old_config()

        # Get the storage engine
        self._engine = self._parse_engine()

        # Get the path where the Mackup folder is
        self._path = self._parse_path()

        # Get the directory replacing 'Mackup', if any
        self._directory = self._parse_directory()

        # Get the list of apps to ignore
        self._apps_to_ignore = self._parse_apps_to_ignore()

        # Get the list of apps to allow
        self._apps_to_sync = self._parse_apps_to_sync()

    @property
    def engine(self):
        """
        The engine used by the storage.
        ENGINE_DROPBOX, ENGINE_GDRIVE or ENGINE_FS.

        Returns:
            str
        """
        return str(self._engine)

    @property
    def path(self):
        """
        The path to the directory where Mackup is gonna create and store his
        directory.

        Returns:
            str
        """
        return str(self._path)

    @property
    def directory(self):
        """
        The name of the Mackup directory, named Mackup by default.

        Returns:
            str
        """
        return str(self._directory)

    @property
    def fullpath(self):
        """
        The full path to the directory when Mackup is storing the configuration
        files.

        Returns:
            str
        """
        return str(os.path.join(self.path, self.directory))

    @property
    def apps_to_ignore(self):
        """
        Get the list of applications ignored in the config file.

        Returns:
            set. Set of application names to ignore, lowercase
        """
        return set(self._apps_to_ignore)

    @property
    def apps_to_sync(self):
        """
        Get the list of applications allowed in the config file.

        Returns:
            set. Set of application names to allow, lowercase
        """
        return set(self._apps_to_sync)

    def _setup_parser(self, filename=None):
        """
        Args:
            filename (str) or None

        Returns:
            SafeConfigParser
        """
        assert isinstance(filename, str) or filename is None

        # If we are not overriding the config filename
        if not filename:
            filename = MACKUP_CONFIG_FILE

        parser = configparser.SafeConfigParser(allow_no_value=True)
        parser.read(os.path.join(os.path.join(os.environ['HOME'], filename)))

        return parser

    def _warn_on_old_config(self):
        # Is an old setion is in the config file ?
        old_sections = ['Allowed Applications', 'Ignored Applications']
        for old_section in old_sections:
            if self._parser.has_section(old_section):
                error("Old config file detected. Aborting.\n"
                      "\n"
                      "An old section (e.g. [Allowed Applications]"
                      " or [Ignored Applications] has been detected"
                      " in your {} file.\n"
                      "I'd rather do nothing than do something you"
                      " do not want me to do.\n"
                      "\n"
                      "Please read the up to date documentation on"
                      " <https://github.com/lra/mackup> and migrate"
                      " your configuration file."
                      .format(MACKUP_CONFIG_FILE))

    def _parse_engine(self):
        """
        Returns:
            str
        """
        if self._parser.has_option('storage', 'engine'):
            engine = str(self._parser.get('storage', 'engine'))
        else:
            engine = ENGINE_DROPBOX

        assert isinstance(engine, str)

        if engine not in [ENGINE_DROPBOX, ENGINE_GDRIVE, ENGINE_FS]:
            raise ConfigError('Unknown storage engine: {}'.format(engine))

        return str(engine)

    def _parse_path(self):
        """
        Returns:
            str
        """
        if self.engine == ENGINE_DROPBOX:
            path = get_dropbox_folder_location()
        elif self.engine == ENGINE_GDRIVE:
            path = get_google_drive_folder_location()
        elif self.engine == ENGINE_FS:
            if self._parser.has_option('storage', 'path'):
                cfg_path = self._parser.get('storage', 'path')
                path = os.path.join(os.environ['HOME'], cfg_path)
            else:
                raise ConfigError("The required 'path' can't be found while"
                                  " the 'file_system' engine is used.")

        return str(path)

    def _parse_directory(self):
        """
        Returns:
            str
        """
        if self._parser.has_option('storage', 'directory'):
            directory = self._parser.get('storage', 'directory')
        else:
            directory = MACKUP_BACKUP_PATH

        return str(directory)

    def _parse_apps_to_ignore(self):
        """
        Returns:
            set
        """
        # We ignore nothing by default
        apps_to_ignore = set()

        # Is the "[applications_to_ignore]" in the cfg file ?
        section_title = 'applications_to_ignore'
        if self._parser.has_section(section_title):
            apps_to_ignore = set(self._parser.options(section_title))

        return apps_to_ignore

    def _parse_apps_to_sync(self):
        """
        Returns:
            set
        """
        # We allow nothing by default
        apps_to_sync = set()

        # Is the "[applications_to_sync]" section in the cfg file ?
        section_title = 'applications_to_sync'
        if self._parser.has_section(section_title):
            apps_to_sync = set(self._parser.options(section_title))

        return apps_to_sync


class ConfigError(Exception):
    pass

########NEW FILE########
__FILENAME__ = constants
"""Constants used in Mackup"""
# Current version
VERSION = '0.7.3'

# Mode used to list supported applications
LIST_MODE = 'list'

# Mode used to backup files to Dropbox
BACKUP_MODE = 'backup'

# Mode used to restore files from Dropbox
RESTORE_MODE = 'restore'

# Mode used to remove Mackup and reset and config file
UNINSTALL_MODE = 'uninstall'

# Support platforms
PLATFORM_DARWIN = 'Darwin'
PLATFORM_LINUX = 'Linux'

# Directory containing the application configs
APPS_DIR = 'applications'

# Default Mackup backup path where it stores its files in Dropbox
MACKUP_BACKUP_PATH = 'Mackup'

# Mackup config file
MACKUP_CONFIG_FILE = '.mackup.cfg'

# Directory that can contains user defined app configs
CUSTOM_APPS_DIR = '.mackup'

# Supported engines
ENGINE_DROPBOX = 'dropbox'
ENGINE_GDRIVE = 'google_drive'
ENGINE_FS = 'file_system'

########NEW FILE########
__FILENAME__ = mackup
"""
The Mackup class is keeping all the state that mackup needs to keep during its
runtime. It also provides easy to use interface that is used by the Mackup UI.
The only UI for now is the command line.
"""
import os
import os.path
import shutil
import tempfile

from . import utils
from . import config
from . import appsdb


class Mackup(object):
    """Main Mackup class"""

    def __init__(self):
        """Mackup Constructor"""
        self._config = config.Config()

        self.mackup_folder = self._config.fullpath
        self.temp_folder = tempfile.mkdtemp(prefix="mackup_tmp_")

    def check_for_usable_environment(self):
        """Check if the current env is usable and has everything's required"""

        # Do not let the user run Mackup as root
        if os.geteuid() == 0:
            utils.error("Running Mackup as a superuser is useless and"
                        " dangerous. Don't do it!")

        # Do we have a folder to put the Mackup folder ?
        if not os.path.isdir(self._config.path):
            utils.error("Unable to find the storage folder: {}"
                        .format(self._config.path))

        # Is Sublime Text running ?
        #if is_process_running('Sublime Text'):
        #    error("Sublime Text is running. It is known to cause problems"
        #          " when Sublime Text is running while I backup or restore"
        #          " its configuration files. Please close Sublime Text and"
        #          " run me again.")

    def check_for_usable_backup_env(self):
        """Check if the current env can be used to back up files"""
        self.check_for_usable_environment()
        self.create_mackup_home()

    def check_for_usable_restore_env(self):
        """Check if the current env can be used to restore files"""
        self.check_for_usable_environment()

        if not os.path.isdir(self.mackup_folder):
            utils.error("Unable to find the Mackup folder: {}\n"
                        "You might want to backup some files or get your"
                        " storage directory synced first."
                        .format(self.mackup_folder))

    def clean_temp_folder(self):
        """Delete the temp folder and files created while running"""
        shutil.rmtree(self.temp_folder)

    def create_mackup_home(self):
        """If the Mackup home folder does not exist, create it"""
        if not os.path.isdir(self.mackup_folder):
            if utils.confirm("Mackup needs a directory to store your"
                             " configuration files\n"
                             "Do you want to create it now ? <{}>"
                             .format(self.mackup_folder)):
                os.mkdir(self.mackup_folder)
            else:
                utils.error("Mackup can't do anything without a home =(")

    def get_apps_to_backup(self):
        """
        Get the list of application that should be backup by Mackup.
        It's the list of allowed apps minus the list of ignored apps.

        Returns:
            (set) List of application names to backup
        """
        # Instantiate the app db
        app_db = appsdb.ApplicationsDatabase()

        # If a list of apps to sync is specify, we only allow those
        if self._config.apps_to_sync:
            apps_to_backup = self._config.apps_to_sync
        else:
            # We allow every supported app by default
            apps_to_backup = app_db.get_app_names()

        # Remove the specified apps to ignore
        for app_name in self._config.apps_to_ignore:
            apps_to_backup.discard(app_name)

        return apps_to_backup

########NEW FILE########
__FILENAME__ = main
"""
Keep your application settings in sync.

Copyright (C) 2013 Laurent Raufaste <http://glop.org/>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import os

from .appsdb import ApplicationsDatabase
from .application import ApplicationProfile
from .constants import (BACKUP_MODE,
                        RESTORE_MODE,
                        UNINSTALL_MODE,
                        LIST_MODE,
                        VERSION)
from .mackup import Mackup
from . import utils


def main():
    """Main function"""

    # Get the command line arg
    args = utils.parse_cmdline_args()

    mckp = Mackup()
    app_db = ApplicationsDatabase()

    if args.mode == BACKUP_MODE:
        # Check the env where the command is being run
        mckp.check_for_usable_backup_env()

        # Backup each application
        for app_name in mckp.get_apps_to_backup():
            app = ApplicationProfile(mckp, app_db.get_files(app_name))
            app.backup()

    elif args.mode == RESTORE_MODE:
        # Check the env where the command is being run
        mckp.check_for_usable_restore_env()

        for app_name in app_db.get_app_names():
            app = ApplicationProfile(mckp, app_db.get_files(app_name))
            app.restore()

    elif args.mode == UNINSTALL_MODE:
        # Check the env where the command is being run
        mckp.check_for_usable_restore_env()

        if utils.confirm("You are going to uninstall Mackup.\n"
                         "Every configuration file, setting and dotfile"
                         " managed by Mackup will be unlinked and moved back"
                         " to their original place, in your home folder.\n"
                         "Are you sure ?"):
            for app_name in app_db.get_app_names():
                app = ApplicationProfile(mckp, app_db.get_files(app_name))
                app.uninstall()

            # Delete the Mackup folder in Dropbox
            # Don't delete this as there might be other Macs that aren't
            # uninstalled yet
            # delete(mckp.mackup_folder)

            print ("\n"
                   "All your files have been put back into place. You can now"
                   " safely uninstall Mackup.\n"
                   "\n"
                   "Thanks for using Mackup !"
                   .format(os.path.abspath(__file__)))

    elif args.mode == LIST_MODE:
        # Display the list of supported applications
        mckp.check_for_usable_environment()
        output = "Supported applications:\n"
        for app_name in sorted(app_db.get_app_names()):
            output += " - {}\n".format(app_name)
        output += "\n"
        output += ("{} applications supported in Mackup v{}"
                   .format(len(app_db.get_app_names()), VERSION))
        print output
    else:
        raise ValueError("Unsupported mode: {}".format(args.mode))

    # Delete the tmp folder
    mckp.clean_temp_folder()

########NEW FILE########
__FILENAME__ = utils
"""System static utilities being used by the modules"""
import argparse
import base64
import os
import platform
import shutil
import stat
import subprocess
import sys
import sqlite3

from . import constants


def confirm(question):
    """
    Ask the user if he really want something to happen

    Args:
        question(str): What can happen

    Returns:
        (boolean): Confirmed or not
    """
    while True:
        answer = raw_input(question + ' <Yes|No>')
        if answer == 'Yes':
            confirmed = True
            break
        if answer == 'No':
            confirmed = False
            break

    return confirmed


def delete(filepath):
    """
    Delete the given file, directory or link.
    Should support undelete later on.

    Args:
        filepath (str): Absolute full path to a file. e.g. /path/to/file
    """
    # Some files have ACLs, let's remove them recursively
    remove_acl(filepath)

    # Some files have immutable attributes, let's remove them recursively
    remove_immutable_attribute(filepath)

    # Finally remove the files and folders
    if os.path.isfile(filepath) or os.path.islink(filepath):
        os.remove(filepath)
    elif os.path.isdir(filepath):
        shutil.rmtree(filepath)


def copy(src, dst):
    """
    Copy a file or a folder (recursively) from src to dst.
    For simplicity sake, both src and dst must be absolute path and must
    include the filename of the file or folder.
    Also do not include any trailing slash.

    e.g. copy('/path/to/src_file', '/path/to/dst_file')
    or copy('/path/to/src_folder', '/path/to/dst_folder')

    But not: copy('/path/to/src_file', 'path/to/')
    or copy('/path/to/src_folder/', '/path/to/dst_folder')

    Args:
        src (str): Source file or folder
        dst (str): Destination file or folder
    """
    assert isinstance(src, str)
    assert os.path.exists(src)
    assert isinstance(dst, str)

    # Create the path to the dst file if it does not exists
    abs_path = os.path.dirname(os.path.abspath(dst))
    if not os.path.isdir(abs_path):
        os.makedirs(abs_path)

    # We need to copy a single file
    if os.path.isfile(src):
        # Copy the src file to dst
        shutil.copy(src, dst)

    # We need to copy a whole folder
    elif os.path.isdir(src):
        shutil.copytree(src, dst)

    # What the heck is this ?
    else:
        raise ValueError("Unsupported file: {}".format(src))

    # Set the good mode to the file or folder recursively
    chmod(dst)


def link(target, link):
    """
    Create a link to a target file or a folder.
    For simplicity sake, both target and link must be absolute path and must
    include the filename of the file or folder.
    Also do not include any trailing slash.

    e.g. link('/path/to/file', '/path/to/link')

    But not: link('/path/to/file', 'path/to/')
    or link('/path/to/folder/', '/path/to/link')

    Args:
        target (str): file or folder the link will point to
        link (str): Link to create
    """
    assert isinstance(target, str)
    assert os.path.exists(target)
    assert isinstance(link, str)

    # Create the path to the link if it does not exists
    abs_path = os.path.dirname(os.path.abspath(link))
    if not os.path.isdir(abs_path):
        os.makedirs(abs_path)

    # Make sure the file or folder recursively has the good mode
    chmod(target)

    # Create the link to target
    os.symlink(target, link)


def chmod(target):
    """
    Recursively set the chmod for files to 0600 and 0700 for folders.
    It's ok unless we need something more specific.

    Args:
        target (str): Root file or folder
    """
    assert isinstance(target, str)
    assert os.path.exists(target)

    file_mode = stat.S_IRUSR | stat.S_IWUSR
    folder_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR

    # Remove the immutable attribute recursively if there is one
    remove_immutable_attribute(target)

    if os.path.isfile(target):
        os.chmod(target, file_mode)

    elif os.path.isdir(target):
        # chmod the root item
        os.chmod(target, folder_mode)

        # chmod recursively in the folder it it's one
        for root, dirs, files in os.walk(target):
            for cur_dir in dirs:
                os.chmod(os.path.join(root, cur_dir), folder_mode)
            for cur_file in files:
                os.chmod(os.path.join(root, cur_file), file_mode)

    else:
        raise ValueError("Unsupported file type: {}".format(target))


def error(message):
    """
    Throw an error with the given message and immediately quit.

    Args:
        message(str): The message to display.
    """
    sys.exit("Error: {}".format(message))


def parse_cmdline_args():
    """
    Setup the engine that's gonna parse the command line arguments

    Returns:
        (argparse.Namespace)
    """

    # Format the description text
    description = ("Mackup {}\n"
                   "Keep your application settings in sync.\n"
                   "Copyright (C) 2013-2014 Laurent Raufaste"
                   " <http://glop.org/>\n"
                   .format(constants.VERSION))

    # Format some epilog text
    epilog = ("Mackup modes of action:\n"
              " - backup: sync your conf files to your synced storage, use"
              " this the 1st time you use Mackup.\n"
              " - restore: link the conf files already in your synced storage"
              " on your system, use it on any new system you use.\n"
              " - uninstall: reset everything as it was before using Mackup.\n"
              " - list: display a list of all supported applications.\n")

    help_msg = "Required action mode for Mackup, see below for details."

    # Setup the global parser
    parser = argparse.ArgumentParser(
        description=description,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add the required arg
    parser.add_argument("mode",
                        choices=[constants.BACKUP_MODE,
                                 constants.RESTORE_MODE,
                                 constants.UNINSTALL_MODE,
                                 constants.LIST_MODE],
                        help=help_msg)

    # Parse the command line and return the parsed options
    return parser.parse_args()


def get_dropbox_folder_location():
    """
    Try to locate the Dropbox folder

    Returns:
        (str) Full path to the current Dropbox folder
    """
    host_db_path = os.path.join(os.environ['HOME'], '.dropbox/host.db')
    try:
        with open(host_db_path, 'r') as f_hostdb:
            data = f_hostdb.read().split()
    except IOError:
        error("Unable to find your Dropbox install =(")
    dropbox_home = base64.b64decode(data[1])

    return dropbox_home


def get_google_drive_folder_location():
    """
    Try to locate the Google Drive folder

    Returns:
        (unicode) Full path to the current Google Drive folder
    """
    gdrive_db_path = 'Library/Application Support/Google/Drive/sync_config.db'
    googledrive_home = None

    gdrive_db = os.path.join(os.environ['HOME'], gdrive_db_path)
    if (os.path.isfile(gdrive_db)):
        con = sqlite3.connect(gdrive_db)
        if con:
            cur = con.cursor()
            query = ("SELECT data_value "
                     "FROM data "
                     "WHERE entry_key = 'local_sync_root_path';")
            cur.execute(query)
            data = cur.fetchone()
            googledrive_home = unicode(data[0])
            con.close()

    if not googledrive_home:
        error("Unable to find your Google Drive install =(")

    return googledrive_home


def is_process_running(process_name):
    """
    Check if a process with the given name is running

    Args:
        (str): Process name, e.g. "Sublime Text"

    Returns:
        (bool): True if the process is running
    """
    is_running = False

    # On systems with pgrep, check if the given process is running
    if os.path.isfile('/usr/bin/pgrep'):
        dev_null = open(os.devnull, 'wb')
        returncode = subprocess.call(['/usr/bin/pgrep', process_name],
                                     stdout=dev_null)
        is_running = bool(returncode == 0)

    return is_running


def remove_acl(path):
    """
    Remove the ACL of the file or folder located on the given path.
    Also remove the ACL of any file and folder below the given one,
    recursively.

    Args:
        path (str): Path to the file or folder to remove the ACL for,
                    recursively.
    """
    # Some files have ACLs, let's remove them recursively
    if (platform.system() == constants.PLATFORM_DARWIN
        and os.path.isfile('/bin/chmod')):
        subprocess.call(['/bin/chmod', '-R', '-N', path])
    elif ((platform.system() == constants.PLATFORM_LINUX)
          and os.path.isfile('/bin/setfacl')):
        subprocess.call(['/bin/setfacl', '-R', '-b', path])


def remove_immutable_attribute(path):
    """
    Remove the immutable attribute of the file or folder located on the given
    path. Also remove the immutable attribute of any file and folder below the
    given one, recursively.

    Args:
        path (str): Path to the file or folder to remove the immutable
                    attribute for, recursively.
    """
    # Some files have ACLs, let's remove them recursively
    if ((platform.system() == constants.PLATFORM_DARWIN)
        and os.path.isfile('/usr/bin/chflags')):
        subprocess.call(['/usr/bin/chflags', '-R', 'nouchg', path])
    elif (platform.system() == constants.PLATFORM_LINUX
          and os.path.isfile('/usr/bin/chattr')):
        subprocess.call(['/usr/bin/chattr', '-R', '-i', path])


def can_file_be_synced_on_current_platform(path):
    """
    Check if it makes sens to sync the file at the given path on the current
    platform.
    For now we don't sync any file in the ~/Library folder on GNU/Linux.
    There might be other exceptions in the future.

    Args:
        (str): Path to the file or folder to check. If relative, prepend it
               with the home folder.
               'abc' becomes '~/abc'
               '/def' stays '/def'

    Returns:
        (bool): True if given file can be synced
    """
    can_be_synced = True

    # If the given path is relative, prepend home
    fullpath = os.path.join(os.environ['HOME'], path)

    # Compute the ~/Library path on OS X
    # End it with a slash because we are looking for this specific folder and
    # not any file/folder named LibrarySomething
    library_path = os.path.join(os.environ['HOME'], 'Library/')

    if platform.system() == constants.PLATFORM_LINUX:
        if fullpath.startswith(library_path):
            can_be_synced = False

    return can_be_synced

########NEW FILE########
__FILENAME__ = config_tests
import unittest
import os.path

from mackup.constants import (ENGINE_DROPBOX,
                              ENGINE_GDRIVE,
                              ENGINE_FS)
from mackup.config import Config, ConfigError


class TestConfig(unittest.TestCase):

    def setUp(self):
        realpath = os.path.dirname(os.path.realpath(__file__))
        os.environ['HOME'] = os.path.join(realpath, 'fixtures')

    def test_config_empty(self):
        cfg = Config('mackup-empty.cfg')

        assert isinstance(cfg.engine, str)
        assert cfg.engine == ENGINE_DROPBOX

        assert isinstance(cfg.path, str)
        assert cfg.path == u'/home/some_user/Dropbox'

        assert isinstance(cfg.directory, str)
        assert cfg.directory == u'Mackup'

        assert isinstance(cfg.fullpath, str)
        assert cfg.fullpath == u'/home/some_user/Dropbox/Mackup'

        assert cfg.apps_to_ignore == set()
        assert cfg.apps_to_sync == set()

    def test_config_engine_dropbox(self):
        cfg = Config('mackup-engine-dropbox.cfg')

        assert isinstance(cfg.engine, str)
        assert cfg.engine == ENGINE_DROPBOX

        assert isinstance(cfg.path, str)
        assert cfg.path == u'/home/some_user/Dropbox'

        assert isinstance(cfg.directory, str)
        assert cfg.directory == u'some_weirld_name'

        assert isinstance(cfg.fullpath, str)
        assert cfg.fullpath == u'/home/some_user/Dropbox/some_weirld_name'

        assert cfg.apps_to_ignore == set()
        assert cfg.apps_to_sync == set()

    def test_config_engine_filesystem_absolute(self):
        cfg = Config('mackup-engine-file_system-absolute.cfg')

        assert isinstance(cfg.engine, str)
        assert cfg.engine == ENGINE_FS

        assert isinstance(cfg.path, str)
        assert cfg.path == u'/some/absolute/folder'

        assert isinstance(cfg.directory, str)
        assert cfg.directory == u'custom_folder'

        assert isinstance(cfg.fullpath, str)
        assert cfg.fullpath == u'/some/absolute/folder/custom_folder'

        assert cfg.apps_to_ignore == set(['subversion', 'sequel-pro'])
        assert cfg.apps_to_sync == set()

    def test_config_engine_filesystem(self):
        cfg = Config('mackup-engine-file_system.cfg')

        assert isinstance(cfg.engine, str)
        assert cfg.engine == ENGINE_FS

        assert isinstance(cfg.path, str)
        assert cfg.path.endswith(os.path.join(os.environ[u'HOME'],
                                              u'some/relative/folder'))

        assert isinstance(cfg.directory, str)
        assert cfg.directory == u'Mackup'

        assert isinstance(cfg.fullpath, str)
        assert cfg.fullpath == os.path.join(os.environ[u'HOME'],
                                            u'some/relative/folder',
                                            u'Mackup')

        assert cfg.apps_to_ignore == set()
        assert cfg.apps_to_sync == set(['sabnzbd', 'sublime-text-3', 'x11'])

    def test_config_engine_google_drive(self):
        cfg = Config('mackup-engine-google_drive.cfg')

        assert isinstance(cfg.engine, str)
        assert cfg.engine == ENGINE_GDRIVE

        assert isinstance(cfg.path, str)
        assert cfg.path == u'/Users/whatever/Google Drive'

        assert isinstance(cfg.directory, str)
        assert cfg.directory == u'Mackup'

        assert isinstance(cfg.fullpath, str)
        assert cfg.fullpath.endswith(u'/Google Drive/Mackup')

        assert cfg.apps_to_ignore == set(['subversion',
                                          'sequel-pro',
                                          'sabnzbd'])
        assert cfg.apps_to_sync == set(['sublime-text-3', 'x11', 'sabnzbd'])

    def test_config_engine_filesystem_no_path(self):
        with self.assertRaises(ConfigError):
            Config('mackup-engine-file_system-no_path.cfg')

    def test_config_engine_unknown(self):
        with self.assertRaises(ConfigError):
            Config('mackup-engine-unknown.cfg')

    def test_config_apps_to_ignore(self):
        cfg = Config('mackup-apps_to_ignore.cfg')

        assert isinstance(cfg.engine, str)
        assert cfg.engine == ENGINE_DROPBOX

        assert isinstance(cfg.path, str)
        assert cfg.path == u'/home/some_user/Dropbox'

        assert isinstance(cfg.directory, str)
        assert cfg.directory == u'Mackup'

        assert isinstance(cfg.fullpath, str)
        assert cfg.fullpath == u'/home/some_user/Dropbox/Mackup'

        assert cfg.apps_to_ignore == set(['subversion',
                                          'sequel-pro',
                                          'sabnzbd'])
        assert cfg.apps_to_sync == set()

    def test_config_apps_to_sync(self):
        cfg = Config('mackup-apps_to_sync.cfg')

        assert isinstance(cfg.engine, str)
        assert cfg.engine == ENGINE_DROPBOX

        assert isinstance(cfg.path, str)
        assert cfg.path == u'/home/some_user/Dropbox'

        assert isinstance(cfg.directory, str)
        assert cfg.directory == u'Mackup'

        assert isinstance(cfg.fullpath, str)
        assert cfg.fullpath == u'/home/some_user/Dropbox/Mackup'

        assert cfg.apps_to_ignore == set()
        assert cfg.apps_to_sync == set(['sabnzbd',
                                        'sublime-text-3',
                                        'x11'])

    def test_config_apps_to_ignore_and_sync(self):
        cfg = Config('mackup-apps_to_ignore_and_sync.cfg')

        assert isinstance(cfg.engine, str)
        assert cfg.engine == ENGINE_DROPBOX

        assert isinstance(cfg.path, str)
        assert cfg.path == u'/home/some_user/Dropbox'

        assert isinstance(cfg.directory, str)
        assert cfg.directory == u'Mackup'

        assert isinstance(cfg.fullpath, str)
        assert cfg.fullpath == u'/home/some_user/Dropbox/Mackup'

        assert cfg.apps_to_ignore == set(['subversion',
                                          'sequel-pro',
                                          'sabnzbd'])
        assert cfg.apps_to_sync == set(['sabnzbd',
                                        'sublime-text-3',
                                        'x11',
                                        'vim'])

########NEW FILE########
__FILENAME__ = utils_test
import os
import tempfile
import unittest
import stat

# from unittest.mock import patch

from mackup import utils


class TestMackup(unittest.TestCase):

    def test_confirm_yes(self):
        # Override the raw_input used in utils
        def custom_raw_input(_):
            return 'Yes'
        utils.raw_input = custom_raw_input
        assert utils.confirm('Answer Yes to this question')

    def test_confirm_no(self):
        # Override the raw_input used in utils
        def custom_raw_input(_):
            return 'No'
        utils.raw_input = custom_raw_input
        assert not utils.confirm('Answer No to this question')

    def test_confirm_typo(self):
        # Override the raw_input used in utils
        def custom_raw_input(_):
            return 'No'
        utils.raw_input = custom_raw_input
        assert not utils.confirm('Answer garbage to this question')

    def test_delete_file(self):
        # Create a tmp file
        tf = tempfile.NamedTemporaryFile(delete=False)
        tfpath = tf.name
        tf.close()

        # Make sure the created file exists
        assert os.path.isfile(tfpath)

        # Check if mackup can really delete it
        utils.delete(tfpath)
        assert not os.path.exists(tfpath)

    def test_delete_folder_recursively(self):
        # Create a tmp folder
        tfpath = tempfile.mkdtemp()

        # Let's put a file in it just for fun
        tf = tempfile.NamedTemporaryFile(dir=tfpath, delete=False)
        filepath = tf.name
        tf.close()

        # Let's put another folder in it
        subfolder_path = tempfile.mkdtemp(dir=tfpath)

        # And a file in the subfolder
        tf = tempfile.NamedTemporaryFile(dir=subfolder_path, delete=False)
        subfilepath = tf.name
        tf.close()

        # Make sure the created files and folders exists
        assert os.path.isdir(tfpath)
        assert os.path.isfile(filepath)
        assert os.path.isdir(subfolder_path)
        assert os.path.isfile(subfilepath)

        # Check if mackup can really delete it
        utils.delete(tfpath)
        assert not os.path.exists(tfpath)
        assert not os.path.exists(filepath)
        assert not os.path.exists(subfolder_path)
        assert not os.path.exists(subfilepath)

    def test_copy_file(self):
        # Create a tmp file
        tf = tempfile.NamedTemporaryFile(delete=False)
        srcfile = tf.name
        tf.close()

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()
        # Set the destination filename
        dstfile = os.path.join(dstpath, "subfolder", os.path.basename(srcfile))

        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert os.path.isfile(srcfile)
        assert os.path.isdir(dstpath)
        assert not os.path.exists(dstfile)

        # Check if mackup can copy it
        utils.copy(srcfile, dstfile)
        assert os.path.isfile(srcfile)
        assert os.path.isdir(dstpath)
        assert os.path.exists(dstfile)

        # Let's clean up
        utils.delete(dstpath)

    def test_copy_fail(self):
        # Create a tmp FIFO file
        tf = tempfile.NamedTemporaryFile()
        srcfile = tf.name
        tf.close()
        os.mkfifo(srcfile)

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()
        # Set the destination filename
        dstfile = os.path.join(dstpath, "subfolder", os.path.basename(srcfile))

        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert not os.path.isfile(srcfile)
        assert stat.S_ISFIFO(os.stat(srcfile).st_mode)
        assert os.path.isdir(dstpath)
        assert not os.path.exists(dstfile)

        # Check if mackup can copy it
        self.assertRaises(ValueError, utils.copy, srcfile, dstfile)
        assert not os.path.isfile(srcfile)
        assert stat.S_ISFIFO(os.stat(srcfile).st_mode)
        assert os.path.isdir(dstpath)
        assert not os.path.exists(dstfile)

        # Let's clean up
        utils.delete(srcfile)
        utils.delete(dstpath)

    def test_copy_dir(self):
        # Create a tmp folder
        srcpath = tempfile.mkdtemp()

        # Create a tmp file
        tf = tempfile.NamedTemporaryFile(delete=False, dir=srcpath)
        srcfile = tf.name
        tf.close()

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()

        # Set the destination filename
        srcpath_basename = os.path.basename(srcpath)
        dstfile = os.path.join(dstpath,
                               'subfolder',
                               srcpath_basename,
                               os.path.basename(srcfile))
        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert os.path.isdir(srcpath)
        assert os.path.isfile(srcfile)
        assert os.path.isdir(dstpath)
        assert not os.path.exists(dstfile)

        # Check if mackup can copy it
        utils.copy(srcfile, dstfile)
        assert os.path.isdir(srcpath)
        assert os.path.isfile(srcfile)
        assert os.path.isdir(dstpath)
        assert os.path.exists(dstfile)

        # Let's clean up
        utils.delete(srcpath)
        utils.delete(dstpath)

    def test_link_file(self):
        # Create a tmp file
        tf = tempfile.NamedTemporaryFile(delete=False)
        srcfile = tf.name
        tf.close()

        # Create a tmp folder
        dstpath = tempfile.mkdtemp()
        # Set the destination filename
        dstfile = os.path.join(dstpath, "subfolder", os.path.basename(srcfile))

        # Make sure the source file and destination folder exist and the
        # destination file doesn't yet exist
        assert os.path.isfile(srcfile)
        assert os.path.isdir(dstpath)
        assert not os.path.exists(dstfile)

        # Check if mackup can link it and the link points to the correct place
        utils.link(srcfile, dstfile)
        assert os.path.isfile(srcfile)
        assert os.path.isdir(dstpath)
        assert os.path.exists(dstfile)
        assert os.readlink(dstfile) == srcfile

        # Let's clean up
        utils.delete(dstpath)

########NEW FILE########
