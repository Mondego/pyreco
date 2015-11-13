__FILENAME__ = launcher
#!/usr/bin/env python
"""
This is the launcher for MIDAS
"""

import logging
from subprocess import Popen, PIPE
from os import listdir
from os.path import dirname, realpath, isfile, join, splitext, basename
from collections import namedtuple
from itertools import chain
from socket import gethostname
from time import strftime, gmtime

# Types
TyLanguage = namedtuple("TyLanguage", "supported_extensions execution_string")

# Configurations
logging.basicConfig(format='%(message)s', level=logging.INFO)

# Contants
CURRENT_DIR = dirname(realpath(__file__))

MODULES_DIR = join(CURRENT_DIR, "modules")

LOG_DIR = join(CURRENT_DIR, "log")

HOSTNAME = gethostname()

DATE = strftime("%Y-%m-%dT%H:%M:%S%z", gmtime())

MODULES = [
    join(MODULES_DIR, fname) for fname in listdir(MODULES_DIR)\
    if isfile(join(MODULES_DIR, fname))
]

PYTHON_LANGUAGE = TyLanguage(
    supported_extensions = [".py", ".pyc"],
    execution_string = "python",
)

RUBY_LANGUAGE = TyLanguage(
    supported_extensions = [".rb"],
    execution_string = "ruby"
)

BASH_LANGUAGE = TyLanguage(
    supported_extensions = [".bash", ".sh"],
    execution_string = "/bin/bash"
)

SUPPORTED_LANGUAGES = [
    PYTHON_LANGUAGE,
    RUBY_LANGUAGE,
    BASH_LANGUAGE,
]

# Functions
def log_line(log_name, line):
    """log_line accepts a line a returns a properly formatted log line"""
    return "%s %s ty[%s]: %s" % (
        DATE,
        HOSTNAME,
        log_name,
        line,
    )

def spawn_module(module, current_lang, mod_name):
    """spawn_module executes an individual Tripyarn module"""
    log_file = join(LOG_DIR, mod_name + ".log")

    command = list(chain(
        current_lang.execution_string.split(" "),
        [module],
    ))

    execution = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout = execution.stdout.readlines()
    stderr = execution.stderr.readlines()

    file_handler = open(log_file, "a")

    for stdout_line in stdout:
        file_handler.write(log_line(mod_name, stdout_line))

    for stderr_line in stderr:
        file_handler.write(log_line(mod_name, stderr_line))

def launch_modules():
    """launch_modules launches Tripyarn's executable modules"""
    for module in MODULES:
        current_lang = None
        mod_name, ext = splitext(basename(module))

        for language in SUPPORTED_LANGUAGES:
            if ext in language.supported_extensions:
                current_lang = language
                break

        if current_lang is not None and isinstance(current_lang, TyLanguage):
            spawn_module(module, current_lang, mod_name)

if __name__ == "__main__":
    launch_modules()

########NEW FILE########
__FILENAME__ = example_analyzefirewallapplications
#!/usr/bin/env python
"""
This is an example MIDAS module
"""

from os.path import isfile
from os import chmod
from time import time, gmtime, strftime
import logging
from sys import argv

from lib.ty_orm import TyORM
from lib.plist import read_plist, get_plist_key
from lib.config import Config
from lib.data_science import DataScience
from lib.helpers.utilities import error_running_file
from lib.tables.example import tables
from lib.decorators import run_every_60



@run_every_60
class AnalyzeFirewallApplications(object):
    """Analyzes firewalled application state in the systems firewall"""

    def __init__(self):
        self.data = []

    def check_firewall_applications(self):
        """
        Checks firewalled application state in the systems firewall
        """
        alf = read_plist('/Library/Preferences/com.apple.alf.plist')
        if alf:
            applications = get_plist_key(alf, "applications")
            if applications:
                for i in applications:
                    try:
                        name = i['bundleid']
                        state = str(i['state'])
                    except KeyError:
                        continue
                    except Exception:
                        continue
                    self.data.append({
                        "name": name,
                        "date": exec_date,
                        "state": state
                    })

    def analyze(self):
        """
        This is the 'main' method that launches all of the other checks
        """
        self.check_firewall_applications()

if __name__ == "__main__":

    start = time()

    # the "exec_date" is used as the "date" field in the datastore
    exec_date = strftime("%a, %d %b %Y %H:%M:%S", gmtime())

    # the table definitions are stored in a library file. this is instantiating
    # the ORM object and initializing the tables
    ORM = TyORM(Config.get("database"))
    if isfile(Config.get("database")):
        chmod(Config.get("database"), 0600)
    for k, v in tables.iteritems():
        ORM.initialize_table(k, v)

    ###########################################################################
    # Gather data
    ###########################################################################
    try:
        a = AnalyzeFirewallApplications()
        if a is not None:
            a.analyze()
            firewall_applications_data = a.data

            data_science = DataScience(
                ORM,
                firewall_applications_data,
                "firewall_applications"
            )
            data_science.get_all()
    except Exception, error:
        print error_running_file(__file__,
                                 "analyze_firewall_applications",
                                 error)

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    logging.info("Execution took %s seconds.", str(end - start))

########NEW FILE########
__FILENAME__ = example_analyzefirewallexceptions
#!/usr/bin/env python
"""
This is an example MIDAS module
"""

from os.path import isfile
from os import chmod
from time import time, gmtime, strftime
import logging
from sys import argv

from lib.ty_orm import TyORM
from lib.plist import read_plist, get_plist_key
from lib.config import Config
from lib.data_science import DataScience
from lib.helpers.utilities import error_running_file
from lib.tables.example import tables
from lib.decorators import run_every_60

@run_every_60
class AnalyzeFirewallExceptions(object):
    """Analyzes the systems firewall exceptions"""

    def __init__(self):
        self.data = []

    def check_firewall_exceptions(self):
        """
        Checks the systems firewall exceptions
        """
        alf = read_plist('/Library/Preferences/com.apple.alf.plist')
        if alf:
            exceptions = get_plist_key(alf, "exceptions")
            if exceptions:
                for i in exceptions:
                    try:
                        self.data.append({
                            "name": i['path'],
                            "date": exec_date,
                            "state": str(i['state'])
                        })
                    except OSError:
                        pass
                    except Exception:
                        pass

    def analyze(self):
        """
        This is the 'main' method that launches all of the other checks
        """
        self.check_firewall_exceptions()


if __name__ == "__main__":

    start = time()

    # the "exec_date" is used as the "date" field in the datastore
    exec_date = strftime("%a, %d %b %Y %H:%M:%S", gmtime())

    # the table definitions are stored in a library file. this is instantiating
    # the ORM object and initializing the tables
    ORM = TyORM(Config.get("database"))
    if isfile(Config.get("database")):
        chmod(Config.get("database"), 0600)
    for k, v in tables.iteritems():
        ORM.initialize_table(k, v)

    ###########################################################################
    # Gather data
    ###########################################################################
    try:
        a = AnalyzeFirewallExceptions()
        if a is not None:
            a.analyze()
            firewall_exceptions_data = a.data

            data_science = DataScience(
                ORM,
                firewall_exceptions_data,
                "firewall_exceptions"
            )
            data_science.get_all()
    except Exception, error:
        print error_running_file(__file__,
                                 "analyze_firewall_exceptions",
                                 error)

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    logging.info("Execution took %s seconds.", str(end - start))

########NEW FILE########
__FILENAME__ = example_analyzefirewallexplicitauths
#!/usr/bin/env python
"""
This is an example MIDAS module
"""

from os.path import isfile
from os import chmod
from time import time, gmtime, strftime
import logging
from sys import argv

from lib.ty_orm import TyORM
from lib.plist import read_plist, get_plist_key
from lib.config import Config
from lib.data_science import DataScience
from lib.helpers.utilities import error_running_file
from lib.tables.example import tables
from lib.decorators import run_every_60



@run_every_60
class AnalyzeFirewallExplicitauths(object):
    """Analyzes the firewall's explicit auth"""

    def __init__(self):
        self.data = []

    def check_firewall_explicitauths(self):
        """
        Checks the systems firewall explicitauths
        """
        alf = read_plist('/Library/Preferences/com.apple.alf.plist')
        if alf:
            explicitauths = get_plist_key(alf, "explicitauths")
            if explicitauths:
                for i in explicitauths:
                    try:
                        self.data.append({"name": i['id'], "date": exec_date})
                    except OSError:
                        pass
                    except Exception:
                        pass

    def analyze(self):
        """
        This is the 'main' method that launches all of the other checks
        """
        self.check_firewall_explicitauths()


if __name__ == "__main__":

    start = time()

    # the "exec_date" is used as the "date" field in the datastore
    exec_date = strftime("%a, %d %b %Y %H:%M:%S", gmtime())

    # the table definitions are stored in a library file. this is instantiating
    # the ORM object and initializing the tables
    ORM = TyORM(Config.get("database"))
    if isfile(Config.get("database")):
        chmod(Config.get("database"), 0600)
    for k, v in tables.iteritems():
        ORM.initialize_table(k, v)

    ###########################################################################
    # Gather data
    ###########################################################################
    try:
        a = AnalyzeFirewallExplicitauths()
        if a is not None:
            a.analyze()
            firewall_explicitauths_data = a.data

            data_science = DataScience(
                ORM,
                firewall_explicitauths_data,
                "firewall_explicitauths"
            )
            data_science.get_all()
    except Exception, error:
        print error_running_file(__file__,
                                 "analyze_firewall_explicit_auths",
                                 error)

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    logging.info("Execution took %s seconds.", str(end - start))

########NEW FILE########
__FILENAME__ = example_analyzefirewallkeys
#!/usr/bin/env python
"""
This is an example MIDAS module
"""

from os.path import isfile
from os import chmod
from time import time, gmtime, strftime
import logging
from sys import argv

from lib.ty_orm import TyORM
from lib.plist import read_plist, get_plist_key
from lib.config import Config
from lib.data_science import DataScience
from lib.helpers.utilities import error_running_file
from lib.tables.example import tables
from lib.decorators import run_every_60


@run_every_60
class AnalyzeFirewallKeys(object):
    """
    AnalyzeFirewallKeys analyzes the top level keys of com.apple.alf.plist
    """

    def __init__(self):
        self.data = []

    def check_firewall_keys(self):
        """
        Checks the top level keys of com.apple.alf.plist
        """
        alf = read_plist('/Library/Preferences/com.apple.alf.plist')
        if alf:
            for i in Config.get("firewall_keys"):
                key = str(get_plist_key(alf, i))
                if key:
                    self.data.append({
                        "name": i,
                        "date": exec_date,
                        "value": key
                    })

    def analyze(self):
        """
        This is the 'main' method that launches all of the other checks
        """
        self.check_firewall_keys()


if __name__ == "__main__":

    start = time()

    # the "exec_date" is used as the "date" field in the datastore
    exec_date = strftime("%a, %d %b %Y %H:%M:%S", gmtime())

    # the table definitions are stored in a library file. this is instantiating
    # the ORM object and initializing the tables
    ORM = TyORM(Config.get("database"))
    if isfile(Config.get("database")):
        chmod(Config.get("database"), 0600)
    for k, v in tables.iteritems():
        ORM.initialize_table(k, v)

    ###########################################################################
    # Gather data
    ###########################################################################
    try:
        a = AnalyzeFirewallKeys()
        if a is not None:
            a.analyze()
            firewall_keys_data = a.data

            data_science = DataScience(
                ORM,
                firewall_keys_data,
                "firewall_keys"
            )
            data_science.get_all()
    except Exception, error:
        print error_running_file(__file__, "analyze_firewall_keys", error)

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    logging.info("Execution took %s seconds.", str(end - start))

########NEW FILE########
__FILENAME__ = example_analyzefirewallprocesses
#!/usr/bin/env python
"""
This is an example MIDAS module
"""

from os.path import isfile
from os import chmod
from time import time, gmtime, strftime
import logging
from sys import argv

from lib.ty_orm import TyORM
from lib.plist import read_plist, get_plist_key
from lib.config import Config
from lib.data_science import DataScience
from lib.helpers.utilities import error_running_file
from lib.tables.example import tables
from lib.decorators import run_every_60

@run_every_60
class AnalyzeFirewallProcesses(object):
    """Analyzes the firewalled processes in the system firewall"""

    def __init__(self):
        self.data = []

    def check_firewall_processes(self):
        """
        Checks the firewalled processes in the system firewall
        """
        alf = read_plist('/Library/Preferences/com.apple.alf.plist')
        if alf:
            processes = get_plist_key(alf, "firewall")
            if processes:
                for key, value in processes.iteritems():
                    try:
                        name = key
                        state = str(value['state'])
                        process = value['proc']
                        try:
                            servicebundleid = value['servicebundleid']
                        except KeyError:
                            servicebundleid = "KEY DNE"
                        self.data.append({
                            "name": name,
                            "date": exec_date,
                            "state": state,
                            "process": process,
                            "servicebundleid": servicebundleid
                        })
                    except KeyError:
                        pass
                    except Exception:
                        pass

    def analyze(self):
        """
        This is the 'main' method that launches all of the other checks
        """
        self.check_firewall_processes()


if __name__ == "__main__":

    start = time()

    # the "exec_date" is used as the "date" field in the datastore
    exec_date = strftime("%a, %d %b %Y %H:%M:%S", gmtime())

    # the table definitions are stored in a library file. this is instantiating
    # the ORM object and initializing the tables
    ORM = TyORM(Config.get("database"))
    if isfile(Config.get("database")):
        chmod(Config.get("database"), 0600)
    for k, v in tables.iteritems():
        ORM.initialize_table(k, v)

    ###########################################################################
    # Gather data
    ###########################################################################
    try:
        a = AnalyzeFirewallProcesses()
        if a is not None:
            a.analyze()
            firewall_processes_data = a.data

            data_science = DataScience(
                ORM,
                firewall_processes_data,
                "firewall_processes"
            )
            data_science.get_all()
    except Exception, error:
        print error_running_file(__file__, "analyze_firewall_processes", error)

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    logging.info("Execution took %s seconds.", str(end - start))

########NEW FILE########
__FILENAME__ = example_analyzekexts
#!/usr/bin/env python
"""
This is an example MIDAS module
"""

from os.path import isfile
from os import chmod
from time import time, gmtime, strftime
import logging
from sys import argv

from lib.ty_orm import TyORM
from lib.config import Config
from lib.data_science import DataScience
from lib.helpers.filesystem import hash_kext
from lib.helpers.system import get_kextstat, get_kextfind
from lib.helpers.utilities import error_running_file
from lib.tables.example import tables



class AnalyzeKexts(object):
    """AnalyzeKexts analyzes and aggregates currently installed kernel
    extensions"""

    def __init__(self):
        self.data = []

    def check_kernel_extensions(self):
        """
        Log all loaded kernel extensions
        """
        kernel_extensions = get_kextstat()
        extension_paths = get_kextfind()
        for i in kernel_extensions.itervalues():
            try:
                file_hash = hash_kext(extension_paths, i['Name'])
                if not file_hash:
                    file_hash = "KEY DNE"
                self.data.append({
                    "name": i['Name'],
                    "date": exec_date,
                    "hash": file_hash
                })
            except KeyError:
                pass

    def analyze(self):
        """
        This is the 'main' method that launches all of the other checks
        """
        self.check_kernel_extensions()


if __name__ == "__main__":

    start = time()

    # the "exec_date" is used as the "date" field in the datastore
    exec_date = strftime("%a, %d %b %Y %H:%M:%S", gmtime())

    # the table definitions are stored in a library file. this is instantiating
    # the ORM object and initializing the tables
    ORM = TyORM(Config.get("database"))
    if isfile(Config.get("database")):
        chmod(Config.get("database"), 0600)
    for k, v in tables.iteritems():
        ORM.initialize_table(k, v)

    ###########################################################################
    # Gather data
    ###########################################################################
    try:
        a = AnalyzeKexts()
        if a is not None:
            a.analyze()
            kext_data = a.data

            data_science = DataScience(ORM, kext_data, "kexts")
            data_science.get_all()
    except Exception, error:
        print error_running_file(__file__, "analyze_kexts", error)

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    logging.info("Execution took %s seconds.", str(end - start))

########NEW FILE########
__FILENAME__ = example_analyzeplist
#!/usr/bin/env python
"""
This is an example MIDAS module
"""

from os.path import isfile
from os import chmod
from time import time, gmtime, strftime
import logging
from sys import argv

from lib.ty_orm import TyORM
from lib.plist import read_plist, get_plist_key
from lib.config import Config
from lib.data_science import DataScience
from lib.helpers.filesystem import hash_file, list_launch_agents, \
    list_launch_daemons, list_app_info_plist, list_plugin_info_plist, \
    list_current_host_pref_files
from lib.helpers.utilities import to_ascii, encode, error_running_file
from lib.tables.example import tables


class AnalyzePlist(object):
    """AnalyzePlist analyzes property list files installed on the system"""

    def __init__(self):
        self.data = {}
        self.pre_changed_files = []
        self.post_changed_files = []
        self.pre_new_files = []
        self.post_new_files = []
        self.check_keys = Config.get("plist_check_keys")
        self.check_keys_hash = Config.get("plist_check_keys_hash")
        self.hashes = self.gather_hashes()
        self.files = list_launch_agents() + list_launch_daemons() + \
            list_app_info_plist() + list_plugin_info_plist() + \
            list_current_host_pref_files()
        self.changed_files, self.new_files, \
        self.same_files = self.bucket_files(
            self.files,
            self.hashes,
        )
        self.plist_name = None
        self.plist_file = None

        if self.changed_files:
            self.analyze_changed_files()

        if self.new_files:
            self.analyze_new_files()

    def gather_hashes(self):
        """
        return a dictionary of plist names and their corresponding hashes
        """
        hash_data = ORM.select("plist", ["name", "hash"])
        hash_dict = {}
        if hash_data:
            for i in hash_data:
                hash_dict[i['name']] = i['hash']
        return hash_dict

    def bucket_files(self, files, hashes):
        """
        takes an array of files and a dictionary in {file: hash} form and
        returns data structures indicitive of which files have changed since
        the last execution
        """
        # changed files and new_files are dicts so that we can store the hash
        # when we compute and thus not have to compute it twice
        changed_files = {}
        new_files = {}

        # since the hash of same_files hasn't changed, we don't need to store
        # it past the comparison
        same_files = []

        for fname in files:
            file_hash = hash_file(fname)
            if fname in hashes:
                if hashes[fname] == file_hash:
                    same_files.append(fname)
                else:
                    changed_files[fname] = file_hash
            else:
                new_files[fname] = file_hash

        return changed_files, new_files, same_files

    def check_key(self, key):
        """
        Log the values of the launch agent/daemon keys in self.check_keys
        """
        value = get_plist_key(self.plist_file, key)
        if value:
            self.data[key.lower()] = str(to_ascii(value))
        else:
            self.data[key.lower()] = "KEY DNE"

    def check_key_executable(self, key):
        """
        Log the values of the launch agent/daemon keys in self.check_keys_hash
        """
        key = key.lower()
        key_hash = "%s_hash" % (key.lower(), )

        value = get_plist_key(self.plist_file, key)
        if value:
            try:
                if isinstance(value, basestring):
                    # This should only get triggered by the Program key
                    self.data[key] = str(to_ascii(value))
                    self.data[key_hash] = hash_file(str(to_ascii(value)))
                elif isinstance(value, (list, tuple)):
                    # This should only get triggered by the
                    # ProgramArguments key
                    self.data[key] = encode(" ".join(value))
                    self.data[key_hash] = hash_file(str(value[0]))
            except IOError:
                self.data[key_hash] = "File DNE"
        else:
            self.data[key] = "KEY DNE"
            self.data[key_hash] = "KEY DNE"

    def analyze_changed_files(self):
        """
        analyze plists that have changed since last execution
        """
        where_params = self.changed_files.keys()
        where_statement = "name=%s" % (" OR name=".join(
            ['?'] * len(where_params)), )
        where_clause = [where_statement, where_params]
        self.pre_changed_files = ORM.select("plist", None, where_clause)
        for fname, fname_hash in self.changed_files.iteritems():
            self.data = {}
            self.plist_name = fname
            self.plist_file = read_plist(fname)
            self.data["name"] = self.plist_name
            self.data["date"] = exec_date
            self.data["hash"] = fname_hash

            for i in self.check_keys_hash:
                self.check_key_executable(i)
            for i in self.check_keys:
                self.check_key(i)

            # Aggregate self.data
            self.post_changed_files.append(self.data)

    def analyze_new_files(self):
        """
        analyze new plists that are on the host
        """
        where_params = self.new_files.keys()
        where_statement = "name=%s" % (" OR name=".join(
            ['?'] * len(where_params)), )
        where_clause = [where_statement, where_params]
        self.pre_new_files = ORM.select("plist", None, where_clause)
        self.post_new_files = []
        for fname, fname_hash in self.new_files.iteritems():
            self.data = {}
            self.plist_name = fname
            self.plist_file = read_plist(fname)
            self.data["name"] = self.plist_name
            self.data["date"] = exec_date
            self.data["hash"] = fname_hash

            for i in self.check_keys_hash:
                self.check_key_executable(i)
            for i in self.check_keys:
                self.check_key(i)

            # Aggregate self.data
            self.post_new_files.append(self.data)


if __name__ == "__main__":

    start = time()

    # the "exec_date" is used as the "date" field in the datastore
    exec_date = strftime("%a, %d %b %Y %H:%M:%S", gmtime())

    # the table definitions are stored in a library file. this is instantiating
    # the ORM object and initializing the tables
    ORM = TyORM(Config.get("database"))
    if isfile(Config.get("database")):
        chmod(Config.get("database"), 0600)
    for k, v in tables.iteritems():
        ORM.initialize_table(k, v)

    ###########################################################################
    # Gather data
    ###########################################################################
    try:
        a = AnalyzePlist()
        if a is not None:
            plist_pre_changed_files = a.pre_changed_files
            plist_post_changed_files = a.post_changed_files
            plist_pre_new_files = a.pre_new_files
            plist_post_new_files = a.post_new_files

            data_science = DataScience(
                ORM,
                plist_post_changed_files,
                "plist",
                "name",
                plist_pre_changed_files,
            )
            data_science.get_changed_entries()

            data_science = DataScience(
                ORM,
                plist_post_new_files,
                "plist",
                "name",
                plist_pre_new_files,
            )
            data_science.get_new_entries()
    except Exception, error:
        print error_running_file(__file__, "lad", error)

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    logging.info("Execution took %s seconds.", str(end - start))

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
"""
This is the config for MIDAS
"""
from os.path import dirname, realpath


config = {}

current_dir = dirname(realpath(__file__))
if "/Users" in current_dir:
    config['database'] = 'midas_hids.sqlite'
else:
    config['database'] = '/tmp/midas_hids.sqlite'

config['plist_check_keys'] = [
    'RunAtLoad',
    'WatchPaths',
    'KeepAlive',
    'StartInterval',
    'StartOnMount',
    'OnDemand',
    'QueueDirectories',
    'StandardInPath',
    'StandardOutPath',
    'StandardErrorPath',
    'Debug',
    'LaunchOnlyOnce',
    'Sockets',
    'OSAXHandlers',
    'LSEnvironment',
    'CFBundleVersion',
]

config['plist_check_keys_hash'] = [
    'Program',
    'ProgramArguments'
]

config['firewall_keys'] = [
    'allowsignedenabled',
    'firewallunload',
    'globalstate',
    'loggingenabled',
    'previousonstate',
    'stealthenabled',
    'version',
]


# Maintain backwards compatibility
Config = config

########NEW FILE########
__FILENAME__ = data_science
#!/usr/bin/env python
"""
This file exposes a class that you can use for simple data aggregation and
analytics. The naming of this file should inspire fun and laughter rather than
hatred and anger.
"""

from helpers.utilities import diff
from copy import copy


class DataScience():
    """This is the main class for the data_science utility"""

    def __init__(self, orm_object, new_data, tablename, key="name",
                 all_data=None):
        self.orm = orm_object
        self.new_data = new_data
        self.tablename = tablename
        self.key = key

        if not all_data:
            self.all_data = self.orm.select(self.tablename)
        else:
            self.all_data = all_data

    def get_all(self):
        """get_all is a simple wrapper around new, changed and removed
        entries"""
        self.get_new_entries()
        self.get_changed_entries()
        self.get_removed_entries()

    def find_in_data(self, data, column, value):
        """find_in_data finds given subdata in data and returns None if it's
        not there"""
        if not data or not column or not value:
            return None
        for i in data:
            if i[column] == value:
                return i
        return None

    def get_new_entries(self):
        """get_new_entries returns all new entries in a given dataset"""
        new_entries = []
        if self.new_data:
            for i in self.new_data:
                data = self.find_in_data(self.all_data, self.key, i[self.key])
                if not data:
                    new_entries.append(i)

        for i in new_entries:
            master = 'ty_name="%s" ' % (self.tablename, )
            for key, value in i.iteritems():
                if value != "KEY DNE":
                    master += '%s="%s"' % (key, value)
            self.orm.insert(self.tablename, i)
            print master
        return new_entries

    def __master_string(self, tablename, key):
        """master_string is an internal helper for generating a log ling"""
        return 'ty_name="%s" name="%s" changed_entry="true"' % (
            tablename, key)

    def __diff_string(self, changed_field, i_key, data, key, diff_string):
        """diff_string is an internal helpers for get_changed_entries"""
        master = ' %s="%s" %s_old="%s" %s_last_updated="%s"' % (
            changed_field,
            i_key,
            changed_field,
            data[key],
            changed_field,
            data["date"],)
        if diff_string != [data[key], i_key]:
            master += ' %s_diff_added="%s" %s_diff_removed="%s"' % (
                changed_field,
                diff_string[0],
                changed_field,
                diff_string[1],)
        return master

    def get_changed_entries(self):
        """
        get_changed_entries returns all changed entries in a given dataset
        """
        if self.new_data and self.all_data:
            for i in self.new_data:
                try:
                    data = self.find_in_data(
                        self.all_data,
                        self.key,
                        i[self.key]
                    )
                except IndexError:
                    continue
                if data:
                    data_copy = {}
                    for key, value in data.iteritems():
                        if not key.startswith("_") and key != "date":
                            data_copy[key] = value
                    i_copy = copy(i)
                    del(i_copy["date"])

                    if i_copy != data_copy:
                        master = self.__master_string(
                            self.tablename, i_copy[self.key]
                        )
                        data["date"] = i["date"]
                        for key, value in i_copy.iteritems():
                            if i[key] != data[key]:
                                changed_field = key
                                diff_string = diff(str(i[key]), str(data[key]))
                                string = self.__diff_string(
                                    changed_field,
                                    i[key],
                                    data,
                                    key,
                                    diff_string,
                                )
                                data[key] = i[key]
                                master += string
                        print master
                        self.orm.update(data)

    def get_removed_entries(self):
        """get_removed_entries return all removed entries in a given dataset"""
        if self.all_data and self.new_data:
            for i in self.all_data:
                data = self.find_in_data(self.new_data, self.key, i[self.key])
                if not data:
                    master = 'ty_name="%s" removed_entry="true" ' % (
                        self.tablename,)
                    for key, value in i.iteritems():
                        if value != "KEY DNE" and not key.startswith("_"):
                            master += '%s="%s" ' % (key, value)
                    print master
                    self.orm.delete(i)

########NEW FILE########
__FILENAME__ = decorators
#!/usr/bin/env python
"""
This is the declaration file for a set of useful decorators.
"""

from time import strftime, gmtime, time

def run_every_n_minutes(n_minutes, func):
    """
    a decorator for running functions every n minutes
    """
    def decorated(*args, **kwargs):
        """
        internal decorator method
        """
        minute = int(strftime("%M", gmtime()))
        ret = None
        if minute % n_minutes == 0:
            ret = func(*args, **kwargs)
        return ret
    return decorated


def run_every_5(func):
    """
    a decorator for running functions every 5 minutes
    """
    return run_every_n_minutes(5, func)


def run_every_10(func):
    """
    a decorator for running functions every 10 minutes
    """
    return run_every_n_minutes(10, func)


def run_every_15(func):
    """
    a decorator for running functions every 15 minutes
    """
    return run_every_n_minutes(15, func)

def run_every_20(func):
    """
    a decorator for running functions every 20 minutes
    """
    return run_every_n_minutes(20, func)


def run_every_30(func):
    """
    a decorator for running functions every 30 minutes
    """
    return run_every_n_minutes(30, func)

def run_every_60(func):
    """
    a decorator for running functions every 60 minutes
    """
    return run_every_n_minutes(60, func)


def timer(func):
    """
    a decorator for timing code execution
    """
    def decorated(*args, **kwargs):
        """
        internal decorator method
        """
        start = time()
        ret = func(*args, **kwargs)
        end = time()
        print "ty_name=perf function=\"%s\" time=\"%.4f\"" % (
            func.__name__,
            end - start,
        )
        return ret
    return decorated

########NEW FILE########
__FILENAME__ = filesystem
#!/usr/bin/env python
"""
This is a set of helper functions for filesystem utilities
"""

from os import listdir, walk, stat
from os.path import isfile, isdir, join, getmtime, islink
from itertools import product
from hashlib import sha1
from stat import ST_MODE
from sys import getsizeof
from base64 import b64decode
from re import match
from operator import itemgetter

from system import shell_out


def list_all_in_dir(directory):
    """
    Returns an array of all files and dirs that are present in a directory.

    Arguments:
      - dir: the directory to be searched

    """
    try:
        if not directory.endswith('/'):
            directory = "%s/" % (directory, )
    except AttributeError:
        return []
    except OSError:
        return []
    return [directory + f for f in listdir(directory)]


def list_files_in_dir(directory):
    """
    Returns an array of files that are present in a directory. Note that this
    will not display any subdirectories that are present in the directory

    Arguments:
      - dir: the directory to be searched

    """
    try:
        if not directory.endswith('/'):
            directory = "%s/" % (directory, )
    except AttributeError:
        return []
    except OSError:
        return []
    return [directory + f for f in listdir(directory)\
            if isfile(join(directory, f))]


def list_dirs_in_dir(directory):
    """
    Returns an array of directories that are present in a directory.

    Arguments:
      - dir: the directory to be searched

    """
    try:
        if not directory.endswith('/'):
            directory = "%s/" % (directory, )
    except AttributeError:
        return []
    except OSError:
        return []
    return [directory + f for f in listdir(directory)\
            if isdir(join(directory, f))]


def get_most_recently_updated_file(directory):
    """
    Returns the path of the most recently updated file in a directory
    """
    try:
        files = list_files_in_dir(directory)
    except OSError:
        return None
    if files:
        try:
            return max(filter(lambda e: not islink(e), files), key=getmtime)
        except OSError:
            return None
    else:
        return None


def hash_file(filename):
    """
    Return the SHA1 hash of the supplied file

    Arguments:
      - filename: the file to be hashed
    """
    return sha1(file(filename, 'r').read()).hexdigest()


def get_executables():
    """
    Find all executable files on the system with mdfind
    """
    return shell_out("mdfind kMDItemContentType==public.unix-executable")


def get_documents():
    """
    Find all document files on the system with mdfind
    """
    files = []
    file_extensions = [
        "docx", "doc",
        "xlsx", "xls",
        "pptx", "ppt",
        "pdf",
        "key",
        "pages",
        "numbers"
    ]
    for ext in file_extensions:
        arg = "kMDItemDisplayName == *.%s" % (ext, )
        files += shell_out("mdfind %s" % (arg, ))
    return filter(None, files)


def hash_kext(kextfind, kext):
    """
    Looks in /System/Library/Extensions/ for a supplied kext and returns it's
    hash if it exists, None if it doesn't
    """
    kext = kext.split(".")[-1]
    found = None
    for i in kextfind:
        if i.split('/')[-1].strip('.kext') == kext:
            path = join(i, "Contents", "MacOS", kext)
            if isfile(path):
                found = path
                break
    else:
        ext_root = join('/System', 'Library', 'Extensions')

        path = join(ext_root,
                    "%s.kext" % (kext, ),
                    'Contents', 'MacOS',
                    kext)

        if isfile(path):
            return hash_file(path)

        path = join(ext_root,
                    "Apple%s.kext" % (kext, ),
                    'Contents', 'MacOS',
                    "Apple%s" % (kext, ))

        if isfile(path):
            return hash_file(path)

        path = join(ext_root, "%s.kext" % (kext, ), kext)

        if isfile(path):
            return hash_file(path)

        path = join('/System', 'Library', 'Filesystems', 'AppleShare',
                     "%s.kext" % (kext, ),
                     'Contents', 'MacOS',
                     kext)

        if isfile(path):
            return hash_file(path)

    if found is None:
        return found
    else:
        return hash_file(found)


def list_home_dirs():
    """
    Returns an array of all directories in /Users
    """
    return list_dirs_in_dir("/Users/")


def get_environment_files():
    """
    Returns an array of all potential environment files on the system
    """
    files = [
        ".MacOS/environment",
    ]
    env = []
    for i in product(list_home_dirs(), files):
        env.append("/".join(i))
    return env


def list_recentitems():
    """
    Returns an array of all com.apple.recentitems files
    """
    files = ["Library/Preferences/com.apple.recentitems.plist"]
    items = []
    for i in product(list_home_dirs(), files):
        if isfile("/".join(i)):
            items.append("/".join(i))
    return items


def find_with_perms(directory, perms):
    """
    Returns an array of all files and directories in a given directory
    that have given permissions

    Arguments:
      - dir: the directory to search
      - perms: the permissions to filter by (in regex form)
    """
    files = []
    for [i, _, _] in walk(directory):
        if match(r"%s" % (perms, ), oct(stat(i)[ST_MODE])[-3:]):
            files.append(i)
        for fname in list_files_in_dir(i):
            if match(r"%s" % (perms, ), oct(stat(i)[ST_MODE])[-3:]):
                files.append(fname)
    return files


def list_authorized_keys():
    """
    Returns an array of all authorized_keys files on the filesystem
    """
    files = [
        ".ssh/authorized_keys",
        ".ssh2/authorized_keys",
    ]

    keys = []
    for i in product(["/var/root/"], files):
        if isfile("/".join(i)):
            keys.append("/".join(i))
    for i in product(list_home_dirs(), files):
        if isfile("/".join(i)):
            keys.append("/".join(i))
    return keys


def list_ssh_keys(no_password=False):
    """
    Returns a list of all ssh keys on a system

    Arguments:
      - no_password: only return keys without a password. defaults to false,
        which returns all keys
    """
    files = [
        ".ssh/id_rsa",
    ]

    ssh_keys = []
    for i in product(list_home_dirs(), files):
        if isfile("/".join(i)):
            ssh_keys.append("/".join(i))
    if not no_password:
        return ssh_keys
    else:
        no_passphrase = []
        for key_file in ssh_keys:
            passphrase = False
            with open(key_file) as fname:
                for line in fname:
                    if "ENCRYPTED" in line:
                        passphrase = True
                        break
                if not passphrase:
                    no_passphrase.append(key_file)
        return no_passphrase


def list_weak_keys():
    """
    Returns an array of all authorized_keys file that contain the public keys
    to weak weak private keys

    Currently, this function looks for keys that
    - Are DSA keys (maximum of 1024 bit key length)
    - Are RSA keys with a hash that has a length of < 300 bytes
      2048 bit RSA keys have a public key hash size that are in between 315 and
      319 bytes
    """
    weak_keys = []
    for i in list_authorized_keys():
        try:
            with open(i) as fname:
                for line in fname:
                    alg = line.split(' ')[0]
                    key = line.split(' ')[1]
                    if alg == "ssh-rsa" and getsizeof(b64decode(key)) < 300:
                        weak_keys.append(i)
                    elif alg == "ssh-dss":
                        weak_keys.append(i)
        except IOError:
            pass
    return weak_keys


def list_current_host_pref_files():
    """
    Return an array of the files that are present in
    ~/Library/Prefernces/ByHost
    """
    files = []
    for home_dir in list_home_dirs():
        try:
            files += list_files_in_dir(
                home_dir + "/Library/Preferences/ByHost/"
            )
        except OSError:
            pass

    return files


def list_launch_agents():
    """
    Return an array of the files that are present in ~/Library/LaunchAgents,
    /System/Library/LaunchAgents/ and /Library/LaunchAgents/
    """
    files = list_system_launch_agents()
    files += list_library_launch_agents()
    files += list_homedir_launch_agents()
    return files


def list_system_launch_agents():
    """
    Return an array of the files that are present in
    /System/Library/LaunchAgents/
    """
    return list_files_in_dir("/System/Library/LaunchAgents/")


def list_library_launch_agents():
    """
    Return an array of the files that are present in /Library/LaunchAgents/
    """
    return list_files_in_dir("/Library/LaunchAgents/")


def list_homedir_launch_agents():
    """
    Return an array of the files that are present in ~/Library/LaunchAgents
    """
    files = []
    for home_dir in list_home_dirs():
        try:
            files += list_files_in_dir(home_dir + "/Library/LaunchAgents/")
        except OSError:
            pass

    return files


def list_launch_daemons():
    """
    Return an array of the files that are present in /Library/LaunchDaemons/
    and /System/Library/LaunchDaemons/
    """
    files = list_files_in_dir("/Library/LaunchDaemons/")
    files += list_files_in_dir("/System/Library/LaunchDaemons/")

    return files


def list_startup_items():
    """
    Return an array of files that are present in /Library/StartupItems/ and
    /System/Library/StartupItems/
    """
    files = list_all_in_dir("/Library/StartupItems/")
    files += list_all_in_dir("/System/Library/StartupItems/")

    return files


def list_scripting_additions():
    """
    Return an array of files that are present in /Library/ScriptingAdditions/
    """
    return list_files_in_dir("/Library/ScriptingAdditions")


def list_app_info_plist():
    """
    Returns an array of Info.plist files in the /Applications directory
    """
    applications = list_dirs_in_dir("/Applications")
    info = []
    if applications:
        for app in applications:
            filename = join(app, 'Contents', 'Info.plist')
            if isfile(filename):
                info.append(filename)
    return info


def list_plugin_info_plist():
    """
    Returns an array of Info.plist files in the /Library/Internet Plugins/
    directory
    """
    plugins = list_dirs_in_dir("/Library/Internet Plug-Ins")
    info = []
    if plugins:
        for plugin in plugins:
            filename = join(plugin, 'Contents', 'Info.plist')
            if isfile(filename):
                info.append(filename)
    return info


def is_ssh_key(filename):
    """
    Returns True if a file might be an ssh key, False if not
    """
    if isfile(filename) and getsizeof(filename) < 10000:
        with open(filename, 'rb') as key:
            line1 = next(key)
            return match("^[-]*BEGIN.*PRIVATE KEY[-]*$", line1) is not None
    else:
        return False


def find_ssh_keys():
    """
    Returns an array of SSH private keys on the host
    """
    keys = []
    keys1 = shell_out("mdfind kMDItemFSName=='id_*sa'")
    if keys1:
        for key in keys1:
            if key and not match("^/Users/[a-zA-Z0-9]*/.ssh", key):
                keys.append(key)

    keys2 = shell_out("mdfind kMDItemFSName=='*.id'")
    if keys2:
        for key in keys2:
            try:
                if isfile(key) and is_ssh_key(key):
                    keys.append(key)
            except OSError:
                pass
            except Exception:
                pass

    return keys

########NEW FILE########
__FILENAME__ = network
#!/usr/bin/env python
"""
This is a set of helper functions for network utilities
"""

from system import shell_out
from datetime import datetime
import re


def get_ifconfig():
    """
    Returns a JSON array of `ifconfig`
    """
    ifconfig = shell_out("ifconfig -a")
    json = {}
    if ifconfig:
        for i in ifconfig:
            if not i.startswith('\t'):
                interface = i.split(':')[0]
                json[interface] = {}
                curr = interface
            else:
                i = i[1:]
                i_space = i.find(' ')
                i_equals = i.find('=')
                greater_than = i_space if i_space > i_equals else i_equals
                k = i[:greater_than].strip(':')
                j = i[greater_than:].split(' ')
                if j[0] == '':
                    j = j[1::]
                json[curr][k] = j
    return json


def parse_date(line):
    """
    Parse the date from a syslog line
    """
    try:
        date = "%s %s" % (
            str(datetime.today().year),
            ' '.join(line.split(' ')[:3])
        )
        ret = datetime.strptime(date, "%Y %b %d %H:%M:%S")
    except IOError:
        ret = None
    except Exception:
        ret = None
    if ret:
        today = datetime.today()
        if (ret.month > today.month) or\
        ((ret.month == today.month) and\
        (ret.day > today.day)):
            return None
    return ret


def get_ssid():
    """
    Returns the currently connected SSID
    """
    command = "".join([
        "System/Library/PrivateFrameworks/Apple80211.framework/Versions/",
        "Current/Resources/airport -I",
    ])
    airport = shell_out(command)
    for i in airport:
        if re.match(r'^SSID:', i.strip()):
            return i.strip().strip("SSID: ")


def get_default_gateway_ip():
    """
    Returns the IP address of the currently connected gateway
    """
    netstat = shell_out("netstat -nr")
    for i in netstat:
        if i.startswith("default"):
            return filter(None, i.split(' '))[1]


def get_default_gateway_mac():
    """
    Returns the MAC address of the currently connected gateway
    """
    ip_addr = get_default_gateway_ip()
    arp = shell_out("arp -an")
    for i in arp:
        if ("(%s)" % ip_addr) in i:
            return i.split(' ')[3]


def is_mac_addr(mac):
    """
    Returns true if the inputted var is a propper MAC address, false
    if it's not
    """
    if type(mac) != 'str':
        return False
    if re.match(r'([0-9A-F]{2}[:-]){5}([0-9A-F]{2})', mac, re.IGNORECASE):
        return True
    else:
        return False


def ssh_length():
    """
    Returns an array of times that open ssh connections have been open
    """
    ssh_times = []
    ps_ax = shell_out("ps -ax -o etime,command -c")
    for i in ps_ax:
        data = i.strip().strip('\n').split(' ')
        if len(data) == 2 and data[-1] == 'ssh':
            ssh_times.append(data[0])
    return ssh_times


def scutil_dns():
    """
    Returns a dictinoary with the search domain, nameserver0 and nameserver1
    """
    scutil_command = shell_out("scutil --dns")
    scutil = {}
    if scutil_command:
        for i in scutil_command:
            j = filter(None, i.split(" "))
            if 'domain[0]' in j:
                scutil['search_domain'] = j[-1]
                continue
            elif 'nameserver[0]' in j:
                scutil['nameserver0'] = j[-1]
                continue
            elif 'nameserver[1]' in j:
                scutil['nameserver1'] = j[-1]
                continue
    return scutil

########NEW FILE########
__FILENAME__ = system
#!/usr/bin/env python
"""
This is a set of helper functions for system utilities
"""

from subprocess import Popen, PIPE, call
import plistlib
from re import IGNORECASE
from re import compile as recompile
from os.path import isfile, split


def shell_out(command):
    """
    Executes a shell command and returns it's output as an array of lines

    Arguments
      - command: the full command to be executed
    """
    return Popen(
        command.split(' '),
        stdout=PIPE,
        stderr=PIPE
    ).communicate()[0].strip('\n').split('\n')


def get_kextstat():
    """
    Returns a nice JSON array of `kextstat`
    """
    kextstat = shell_out("kextstat -l")
    header = [
        'Index',
        'Refs',
        'Address',
        'Size',
        'Wired',
        'Name',
        'Version',
        'Linked Against'
    ]
    kextstat_json = {}
    for i in range(len(kextstat)):
        mod = filter(None, kextstat[i].split(" "))
        mod = mod[:7] + ["-".join(mod[7:])]
        kextstat[i] = mod

    for i in kextstat:
        j = dict(zip(header, i))
        kextstat_json[j["Index"]] = j

    return kextstat_json


def get_kextfind():
    """
    Returns an array of .kext files
    """
    kextfind = shell_out("kextfind")
    if kextfind:
        return kextfind
    else:
        return None


def get_launchctl():
    """
    Returns a nice JSON array of `launchctl list`
    """
    launchctl = shell_out("/bin/launchctl list")
    header = ["PID", "Status", "Label"]
    launchctl_json = {}

    launchctl = launchctl[1::]

    for i in range(len(launchctl)):
        mod = filter(None, launchctl[i].split("\t"))
        launchctl[i] = mod

    for i in range(len(launchctl)):
        j = dict(zip(header, launchctl[i]))
        launchctl_json[i] = j

    return launchctl_json


def strings(executable):
    """
    Returns an array of unique strings found in a supplied executable
    """
    if isfile(executable):
        try:
            strings_list = list(set(shell_out("strings %s" % executable)))
        except OSError:
            return []
        except Exception:
            return []
        if strings_list:
            return strings_list
        else:
            return []
    else:
        return []


def delete_file(filename):
    """
    Calls "rm" on a supplied file
    """
    call(["rm", "-f", filename])


def installed(program):
    """
    Returns the path of a supplied program if the supplied program is installed
    and returns False if it is not
    """
    which = shell_out("mdfind -name %s" % program)
    if which:
        for i in which:
            _, fname = split(i)
            if fname == program:
                return i
    else:
        return False


def last_user_name():
    """
    Returns the last logged in username from com.apple.loginwindow.plist
    """
    command = " ".join([
        "defaults",
        "read",
        "/Library/Preferences/com.apple.loginwindow.plist",
        "lastUserName",
    ])
    last_user = shell_out(command)
    if len(last_user) != 1:
        return False
    else:
        last_user = last_user[0]
    return last_user


def crontab_for_user(user):
    """
    Returns False is a supplied user doesn't have a crontab, and returns the
    crontab (pipes in place of newlines) if the user does have one
    """
    crontab = filter(None, shell_out("crontab -u %s -l" % user))
    if crontab:
        return '|'.join(crontab)
    else:
        return False


def last():
    """
    Returns the first two columns of the `last` command
    """
    last_command = shell_out("last")[:-2]
    last_output = []
    for i in last_command:
        last_output.append(filter(None, i.split(" "))[:2])
    return last_output


def list_users():
    """
    Returns an array of all 'users' on the system
    """
    users = []
    dscacheutil = shell_out("dscacheutil -q user")
    if dscacheutil:
        for i in dscacheutil:
            if i.startswith('name: '):
                users.append(i[6:])
    return users


def run_file(filename):
    """
    Returns file information on a given filename. Returns None if file doesn't
    exist
    """
    if isfile(filename):
        output = shell_out("file %s" % filename)
        if output:
            try:
                output = output[0]
            except OSError:
                return None
            except:
                return None
            if output:
                return output
        return None


def lsof():
    """
    Returns a array of lsof -i data
    """
    lsof_output = shell_out("lsof -i")
    lsof_data = []
    headers = [
        'command',
        'pid',
        'user',
        'fd',
        'type',
        'device',
        'size/off',
        'node',
        'name',
    ]
    lsof_output = lsof_output[1:]

    for i in lsof_output:
        lsof_data.append(dict(zip(headers, filter(None, i.split(" ")))))

    return lsof_data


def is_fde_enabled():
    """
    Returns True if FDE is enabled, False if it is not
    """
    fde = shell_out("fdesetup status")
    if fde == ['FileVault is On.']:
        return True
    return False

########NEW FILE########
__FILENAME__ = utilities
#!/usr/bin/env python
"""
This is a set of helper functions for general utilities
"""

import difflib


def diff(string1, string2):
    """
    Returns an array where array[0] is the content of s2 that have been added
    in regards to s1 and array[1] is the content of s2 that has been removed
    from s1
    """
    differ = difflib.Differ()
    added = ""
    removed = ""
    for i in differ.compare(string1, string2):
        if i[0] == "+":
            added += i[2]
        elif i[0] == "-":
            removed += i[2]
    return [added, removed]


def to_ascii(value):
    """
    Returns the ascii representation of a given string
    """
    if isinstance(value, basestring):
        try:
            return value.encode("ascii", "replace")
        except UnicodeError:
            return None
        except Exception:
            return None
    elif isinstance(value, dict):
        try:
            temp_dict = {}
            for i, j in value.iteritems():
                temp_dict[i] = to_ascii(j)
            return temp_dict
        except UnicodeError:
            return None
        except Exception:
            return None


def encode(string):
    """
    URL encodes single quotes and double quotes in an inputted string. This
    isn't done for any security reasons, it's just done so that splunk doesn't
    misinterpret key="value" strings
    """
    string = string.replace("'", "%27")
    string = string.replace('"', "%22")
    return string


def error_running_file(filename, section, error):
    """returns a string in log format if a module errors out"""
    file_error = "ty_error_running_file=%s" % (filename, )
    section_error = "ty_error_section=%s" % (section, )
    error_message = "ty_error_message=%r" % (error, )

    return " ".join([
        file_error,
        section_error,
        error_message,
    ])

########NEW FILE########
__FILENAME__ = plist
#!/usr/bin/env python
"""
This is a set of wrappers around biplist.

The original biplist licence:

Copyright (c) 2010, Andrew Wooster
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of biplist nor the names of its contributors may be
      used to endorse or promote products derived from this software without
      specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from collections import namedtuple
import calendar
import datetime
import math
import plistlib
from struct import pack, unpack
import StringIO

from json import loads
from subprocess import Popen, PIPE


def read_plist(plist_file):
    """
    Returns a dict once given the path of a plist file

    First, it trys biplist's readPlist, which trys to read it using it's own
    magic if it's binary and uses plistlib if it's normal XML.

    If those fail, it will try shelling out to plutil
    """
    try:
        output = readPlist(plist_file)
    except OSError:
        output = False
    except Exception:
        output = False
    if not output:
        try:
            output = read_plist_plutil(plist_file)
        except OSError:
            output = False
        except Exception:
            output = False
    return output


def get_plist_key(plist_file, key):
    """
    Returns the value of a given plist key, given the JSON encoded equivalent
    of a plist file (this goes hand in hand with read_plist)
    """
    try:
        return plist_file[key]
    except (KeyError, TypeError):
        return False

###############################################################################
# You should never directly call any of the following functions
###############################################################################


def read_plist_plutil(plist_file, format_type="json"):
    """
    Returns a JSON encoded representation once given the path of a plist file
    """
    arg_array = ["plutil", "-convert", format_type, "-o", "-", plist_file]
    try:
        output = Popen(arg_array, stdout=PIPE, stderr=PIPE).communicate()[0]
        return loads(output)
    except OSError:
        return False
    except Exception:
        return False

###############################################################################
# Thus begins biplist code
###############################################################################

__all__ = [
    'Uid', 'Data', 'readPlist', 'writePlist', 'readPlistFromString',
    'writePlistToString', 'InvalidPlistException', 'NotBinaryPlistException'
]

apple_reference_date_offset = 978307200


class Uid(int):
    """Wrapper around integers for representing UID values. This
       is used in keyed archiving."""
    def __repr__(self):
        return "Uid(%d)" % self


class Data(str):
    """Wrapper around str types for representing Data values."""
    pass


class InvalidPlistException(Exception):
    """Raised when the plist is incorrectly formatted."""
    pass


class NotBinaryPlistException(Exception):
    """Raised when a binary plist was expected but not encountered."""
    pass


def readPlist(pathOrFile):
    """Raises NotBinaryPlistException, InvalidPlistException"""
    didOpen = False
    result = None
    if isinstance(pathOrFile, (str, unicode)):
        pathOrFile = open(pathOrFile, 'rb')
        didOpen = True
    try:
        reader = PlistReader(pathOrFile)
        result = reader.parse()
    except NotBinaryPlistException as e:
        try:
            pathOrFile.seek(0)
            result = plistlib.readPlist(pathOrFile)
            result = wrapDataObject(result, for_binary=True)
        except Exception as e:
            raise InvalidPlistException(e)
    if didOpen:
        pathOrFile.close()
    return result


def wrapDataObject(o, for_binary=False):
    if isinstance(o, Data) and not for_binary:
        o = plistlib.Data(o)
    elif isinstance(o, plistlib.Data) and for_binary:
        o = Data(o.data)
    elif isinstance(o, tuple):
        o = wrapDataObject(list(o), for_binary)
        o = tuple(o)
    elif isinstance(o, list):
        for i in range(len(o)):
            o[i] = wrapDataObject(o[i], for_binary)
    elif isinstance(o, dict):
        for k in o:
            o[k] = wrapDataObject(o[k], for_binary)
    return o


def writePlist(rootObject, pathOrFile, binary=True):
    if not binary:
        rootObject = wrapDataObject(rootObject, binary)
        return plistlib.writePlist(rootObject, pathOrFile)
    else:
        didOpen = False
        if isinstance(pathOrFile, (str, unicode)):
            pathOrFile = open(pathOrFile, 'wb')
            didOpen = True
        writer = PlistWriter(pathOrFile)
        result = writer.writeRoot(rootObject)
        if didOpen:
            pathOrFile.close()
        return result


def readPlistFromString(data):
    return readPlist(StringIO.StringIO(data))


def writePlistToString(rootObject, binary=True):
    if not binary:
        rootObject = wrapDataObject(rootObject, binary)
        return plistlib.writePlistToString(rootObject)
    else:
        io = StringIO.StringIO
        writer = PlistWriter(io)
        writer.writeRoot(rootObject)
        return io.getvalue()


def is_stream_binary_plist(stream):
    stream.seek(0)
    header = stream.read(7)
    if header == 'bplist0':
        return True
    else:
        return False

PlistTrailer = namedtuple(
    'PlistTrailer',
    'offsetSize, objectRefSize, offsetCount, topLevelObjectNumber, offsetTableOffset')

PlistByteCounts = namedtuple(
    'PlistByteCounts',
    'nullBytes, boolBytes, intBytes, realBytes, dateBytes, dataBytes, stringBytes, uidBytes, arrayBytes, setBytes, dictBytes')


class PlistReader(object):
    file = None
    contents = ''
    offsets = None
    trailer = None
    currentOffset = 0

    def __init__(self, fileOrStream):
        """Raises NotBinaryPlistException."""
        self.reset()
        self.file = fileOrStream

    def parse(self):
        return self.readRoot()

    def reset(self):
        self.trailer = None
        self.contents = ''
        self.offsets = []
        self.currentOffset = 0

    def readRoot(self):
        result = None
        self.reset()
        # Get the header, make sure it's a valid file.
        if not is_stream_binary_plist(self.file):
            raise NotBinaryPlistException()
        self.file.seek(0)
        self.contents = self.file.read()
        if len(self.contents) < 32:
            raise InvalidPlistException("File is too short.")
        trailerContents = self.contents[-32:]
        try:
            self.trailer = PlistTrailer._make(unpack("!xxxxxxBBQQQ",
                                                     trailerContents))
            offset_size = self.trailer.offsetSize * self.trailer.offsetCount
            offset = self.trailer.offsetTableOffset
            offset_contents = self.contents[offset:offset + offset_size]
            offset_i = 0
            while offset_i < self.trailer.offsetCount:
                begin = self.trailer.offsetSize * offset_i
                tmp_contents = offset_contents[ begin:begin + self.trailer.offsetSize]
                tmp_sized = self.getSizedInteger(tmp_contents,
                                                 self.trailer.offsetSize)
                self.offsets.append(tmp_sized)
                offset_i += 1
            self.setCurrentOffsetToObjectNumber(self.trailer.topLevelObjectNumber)
            result = self.readObject()
        except TypeError as e:
            raise InvalidPlistException(e)
        return result

    def setCurrentOffsetToObjectNumber(self, objectNumber):
        self.currentOffset = self.offsets[objectNumber]

    def readObject(self):
        result = None
        tmp_byte = self.contents[self.currentOffset:self.currentOffset + 1]
        marker_byte = unpack("!B", tmp_byte)[0]
        format = (marker_byte >> 4) & 0x0f
        extra = marker_byte & 0x0f
        self.currentOffset += 1

        def proc_extra(extra):
            if extra == 0b1111:
                #self.currentOffset += 1
                extra = self.readObject()
            return extra

        # bool, null, or fill byte
        if format == 0b0000:
            if extra == 0b0000:
                result = None
            elif extra == 0b1000:
                result = False
            elif extra == 0b1001:
                result = True
            elif extra == 0b1111:
                pass  # fill byte
            else:
                raise InvalidPlistException("Invalid object found at offset: %d" % (self.currentOffset - 1))
        # int
        elif format == 0b0001:
            extra = proc_extra(extra)
            result = self.readInteger(pow(2, extra))
        # real
        elif format == 0b0010:
            extra = proc_extra(extra)
            result = self.readReal(extra)
        # date
        elif format == 0b0011 and extra == 0b0011:
            result = self.readDate()
        # data
        elif format == 0b0100:
            extra = proc_extra(extra)
            result = self.readData(extra)
        # ascii string
        elif format == 0b0101:
            extra = proc_extra(extra)
            result = self.readAsciiString(extra)
        # Unicode string
        elif format == 0b0110:
            extra = proc_extra(extra)
            result = self.readUnicode(extra)
        # uid
        elif format == 0b1000:
            result = self.readUid(extra)
        # array
        elif format == 0b1010:
            extra = proc_extra(extra)
            result = self.readArray(extra)
        # set
        elif format == 0b1100:
            extra = proc_extra(extra)
            result = set(self.readArray(extra))
        # dict
        elif format == 0b1101:
            extra = proc_extra(extra)
            result = self.readDict(extra)
        else:
            raise InvalidPlistException("Invalid object found: {format: %s, extra: %s}" % (bin(format), bin(extra)))
        return result

    def readInteger(self, bytes):
        result = 0
        original_offset = self.currentOffset
        data = self.contents[self.currentOffset:self.currentOffset + bytes]
        result = self.getSizedInteger(data, bytes)
        self.currentOffset = original_offset + bytes
        return result

    def readReal(self, length):
        result = 0.0
        to_read = pow(2, length)
        data = self.contents[self.currentOffset:self.currentOffset + to_read]
        if length == 2:  # 4 bytes
            result = unpack('>f', data)[0]
        elif length == 3:  # 8 bytes
            result = unpack('>d', data)[0]
        else:
            raise InvalidPlistException("Unknown real of length %d bytes" % to_read)
        return result

    def readRefs(self, count):
        refs = []
        i = 0
        while i < count:
            fragment = self.contents[self.currentOffset:self.currentOffset + self.trailer.objectRefSize]
            ref = self.getSizedInteger(fragment, len(fragment))
            refs.append(ref)
            self.currentOffset += self.trailer.objectRefSize
            i += 1
        return refs

    def readArray(self, count):
        result = []
        values = self.readRefs(count)
        i = 0
        while i < len(values):
            self.setCurrentOffsetToObjectNumber(values[i])
            value = self.readObject()
            result.append(value)
            i += 1
        return result

    def readDict(self, count):
        result = {}
        keys = self.readRefs(count)
        values = self.readRefs(count)
        i = 0
        while i < len(keys):
            self.setCurrentOffsetToObjectNumber(keys[i])
            key = self.readObject()
            self.setCurrentOffsetToObjectNumber(values[i])
            value = self.readObject()
            result[key] = value
            i += 1
        return result

    def readAsciiString(self, length):
        result = unpack("!%ds" % length, self.contents[self.currentOffset:self.currentOffset + length])[0]
        self.currentOffset += length
        return result

    def readUnicode(self, length):
        actual_length = length * 2
        data = self.contents[self.currentOffset:self.currentOffset + actual_length]
        # unpack not needed?!! data = unpack(">%ds" % (actual_length), data)[0]
        self.currentOffset += actual_length
        return data.decode('utf_16_be')

    def readDate(self):
        global apple_reference_date_offset
        result = unpack(">d", self.contents[self.currentOffset:self.currentOffset + 8])[0]
        result = datetime.datetime.utcfromtimestamp(result + apple_reference_date_offset)
        self.currentOffset += 8
        return result

    def readData(self, length):
        result = self.contents[self.currentOffset:self.currentOffset + length]
        self.currentOffset += length
        return Data(result)

    def readUid(self, length):
        return Uid(self.readInteger(length + 1))

    def getSizedInteger(self, data, bytes):
        result = 0
        # 1, 2, and 4 byte integers are unsigned
        if bytes == 1:
            result = unpack('>B', data)[0]
        elif bytes == 2:
            result = unpack('>H', data)[0]
        elif bytes == 4:
            result = unpack('>L', data)[0]
        elif bytes == 8:
            result = unpack('>q', data)[0]
        else:
            raise InvalidPlistException("Encountered integer longer than 8 bytes.")
        return result


class HashableWrapper(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "<HashableWrapper: %s>" % [self.value]


class BoolWrapper(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return "<BoolWrapper: %s>" % self.value


class PlistWriter(object):
    header = 'bplist00bybiplist1.0'
    file = None
    byteCounts = None
    trailer = None
    computedUniques = None
    writtenReferences = None
    referencePositions = None
    wrappedTrue = None
    wrappedFalse = None

    def __init__(self, file):
        self.reset()
        self.file = file
        self.wrappedTrue = BoolWrapper(True)
        self.wrappedFalse = BoolWrapper(False)

    def reset(self):
        self.byteCounts = PlistByteCounts(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.trailer = PlistTrailer(0, 0, 0, 0, 0)

        # A set of all the uniques which have been computed.
        self.computedUniques = set()
        # A list of all the uniques which have been written.
        self.writtenReferences = {}
        # A dict of the positions of the written uniques.
        self.referencePositions = {}

    def positionOfObjectReference(self, obj):
        """If the given object has been written already, return its
           position in the offset table. Otherwise, return None."""
        return self.writtenReferences.get(obj)

    def writeRoot(self, root):
        """
        Strategy is:
        - write header
        - wrap root object so everything is hashable
        - compute size of objects which will be written
          - need to do this in order to know how large the object refs
            will be in the list/dict/set reference lists
        - write objects
          - keep objects in writtenReferences
          - keep positions of object references in referencePositions
          - write object references with the length computed previously
        - computer object reference length
        - write object reference positions
        - write trailer
        """
        output = self.header
        wrapped_root = self.wrapRoot(root)
        should_reference_root = True  #not isinstance(wrapped_root, HashableWrapper)
        self.computeOffsets(wrapped_root, asReference=should_reference_root, isRoot=True)
        self.trailer = self.trailer._replace(**{'objectRefSize':self.intSize(len(self.computedUniques))})
        (_, output) = self.writeObjectReference(wrapped_root, output)
        output = self.writeObject(wrapped_root, output, setReferencePosition=True)

        # output size at this point is an upper bound on how big the
        # object reference offsets need to be.
        self.trailer = self.trailer._replace(**{
            'offsetSize': self.intSize(len(output)),
            'offsetCount': len(self.computedUniques),
            'offsetTableOffset': len(output),
            'topLevelObjectNumber': 0
        })

        output = self.writeOffsetTable(output)
        output += pack('!xxxxxxBBQQQ', *self.trailer)
        self.file.write(output)

    def wrapRoot(self, root):
        if isinstance(root, bool):
            if root is True:
                return self.wrappedTrue
            else:
                return self.wrappedFalse
        elif isinstance(root, set):
            n = set()
            for value in root:
                n.add(self.wrapRoot(value))
            return HashableWrapper(n)
        elif isinstance(root, dict):
            n = {}
            for key, value in root.iteritems():
                n[self.wrapRoot(key)] = self.wrapRoot(value)
            return HashableWrapper(n)
        elif isinstance(root, list):
            n = []
            for value in root:
                n.append(self.wrapRoot(value))
            return HashableWrapper(n)
        elif isinstance(root, tuple):
            n = tuple([self.wrapRoot(value) for value in root])
            return HashableWrapper(n)
        else:
            return root

    def incrementByteCount(self, field, incr=1):
        self.byteCounts = self.byteCounts._replace(**{field:self.byteCounts.__getattribute__(field) + incr})

    def computeOffsets(self, obj, asReference=False, isRoot=False):
        def check_key(key):
            if key is None:
                raise InvalidPlistException(
                    'Dictionary keys cannot be null in plists.')
            elif isinstance(key, Data):
                raise InvalidPlistException(
                    'Data cannot be dictionary keys in plists.')
            elif not isinstance(key, (str, unicode)):
                raise InvalidPlistException('Keys must be strings.')

        def proc_size(size):
            if size > 0b1110:
                size += self.intSize(size)
            return size
        # If this should be a reference, then we keep a record of it in the
        # uniques table.
        if asReference:
            if obj in self.computedUniques:
                return
            else:
                self.computedUniques.add(obj)

        if obj is None:
            self.incrementByteCount('nullBytes')
        elif isinstance(obj, BoolWrapper):
            self.incrementByteCount('boolBytes')
        elif isinstance(obj, Uid):
            size = self.intSize(obj)
            self.incrementByteCount('uidBytes', incr=1 + size)
        elif isinstance(obj, (int, long)):
            size = self.intSize(obj)
            self.incrementByteCount('intBytes', incr=1 + size)
        elif isinstance(obj, (float)):
            size = self.realSize(obj)
            self.incrementByteCount('realBytes', incr=1 + size)
        elif isinstance(obj, datetime.datetime):
            self.incrementByteCount('dateBytes', incr=2)
        elif isinstance(obj, Data):
            size = proc_size(len(obj))
            self.incrementByteCount('dataBytes', incr=1 + size)
        elif isinstance(obj, (unicode, str)):
            size = proc_size(len(obj))
            self.incrementByteCount('stringBytes', incr=1 + size)
        elif isinstance(obj, HashableWrapper):
            obj = obj.value
            if isinstance(obj, set):
                size = proc_size(len(obj))
                self.incrementByteCount('setBytes', incr=1 + size)
                for value in obj:
                    self.computeOffsets(value, asReference=True)
            elif isinstance(obj, (list, tuple)):
                size = proc_size(len(obj))
                self.incrementByteCount('arrayBytes', incr=1 + size)
                for value in obj:
                    asRef = True
                    self.computeOffsets(value, asReference=True)
            elif isinstance(obj, dict):
                size = proc_size(len(obj))
                self.incrementByteCount('dictBytes', incr=1 + size)
                for key, value in obj.iteritems():
                    check_key(key)
                    self.computeOffsets(key, asReference=True)
                    self.computeOffsets(value, asReference=True)
        else:
            raise InvalidPlistException("Unknown object type.")

    def writeObjectReference(self, obj, output):
        """Tries to write an object reference, adding it to the references
           table. Does not write the actual object bytes or set the reference
           position. Returns a tuple of whether the object was a new reference
           (True if it was, False if it already was in the reference table)
           and the new output.
        """
        position = self.positionOfObjectReference(obj)
        if position is None:
            self.writtenReferences[obj] = len(self.writtenReferences)
            output += self.binaryInt(len(self.writtenReferences) - 1, bytes=self.trailer.objectRefSize)
            return (True, output)
        else:
            output += self.binaryInt(position, bytes=self.trailer.objectRefSize)
            return (False, output)

    def writeObject(self, obj, output, setReferencePosition=False):
        """Serializes the given object to the output. Returns output.
           If setReferencePosition is True, will set the position the
           object was written.
        """
        def proc_variable_length(format, length):
            result = ''
            if length > 0b1110:
                result += pack('!B', (format << 4) | 0b1111)
                result = self.writeObject(length, result)
            else:
                result += pack('!B', (format << 4) | length)
            return result

        if isinstance(obj, unicode) and obj == unicode('', "unicode_escape"):
            # The Apple Plist decoder can't decode a zero length Unicode string
            obj = ''

        if setReferencePosition:
            self.referencePositions[obj] = len(output)

        if obj is None:
            output += pack('!B', 0b00000000)
        elif isinstance(obj, BoolWrapper):
            if obj.value is False:
                output += pack('!B', 0b00001000)
            else:
                output += pack('!B', 0b00001001)
        elif isinstance(obj, Uid):
            size = self.intSize(obj)
            output += pack('!B', (0b1000 << 4) | size - 1)
            output += self.binaryInt(obj)
        elif isinstance(obj, (int, long)):
            bytes = self.intSize(obj)
            root = math.log(bytes, 2)
            output += pack('!B', (0b0001 << 4) | int(root))
            output += self.binaryInt(obj)
        elif isinstance(obj, float):
            # just use doubles
            output += pack('!B', (0b0010 << 4) | 3)
            output += self.binaryReal(obj)
        elif isinstance(obj, datetime.datetime):
            timestamp = calendar.timegm(obj.utctimetuple())
            timestamp -= apple_reference_date_offset
            output += pack('!B', 0b00110011)
            output += pack('!d', float(timestamp))
        elif isinstance(obj, Data):
            output += proc_variable_length(0b0100, len(obj))
            output += obj
        elif isinstance(obj, unicode):
            bytes = obj.encode('utf_16_be')
            output += proc_variable_length(0b0110, len(bytes) // 2)
            output += bytes
        elif isinstance(obj, str):
            bytes = obj
            output += proc_variable_length(0b0101, len(bytes))
            output += bytes
        elif isinstance(obj, HashableWrapper):
            obj = obj.value
            if isinstance(obj, (set, list, tuple)):
                if isinstance(obj, set):
                    output += proc_variable_length(0b1100, len(obj))
                else:
                    output += proc_variable_length(0b1010, len(obj))

                objectsToWrite = []
                for objRef in obj:
                    (isNew, output) = self.writeObjectReference(objRef, output)
                    if isNew:
                        objectsToWrite.append(objRef)
                for objRef in objectsToWrite:
                    output = self.writeObject(
                        objRef, output, setReferencePosition=True)
            elif isinstance(obj, dict):
                output += proc_variable_length(0b1101, len(obj))
                keys = []
                values = []
                objectsToWrite = []
                for key, value in obj.iteritems():
                    keys.append(key)
                    values.append(value)
                for key in keys:
                    (isNew, output) = self.writeObjectReference(key, output)
                    if isNew:
                        objectsToWrite.append(key)
                for value in values:
                    (isNew, output) = self.writeObjectReference(value, output)
                    if isNew:
                        objectsToWrite.append(value)
                for objRef in objectsToWrite:
                    output = self.writeObject(
                        objRef, output, setReferencePosition=True)
        return output

    def writeOffsetTable(self, output):
        """Writes all of the object reference offsets."""
        all_positions = []
        writtenReferences = list(self.writtenReferences.items())
        writtenReferences.sort(key=lambda x: x[1])
        for obj, order in writtenReferences:
            # Porting note: Elsewhere we deliberately replace empty
            # unicdoe strings with empty binary strings, but the empty
            # unicode string goes into writtenReferences.  This isn't
            # an issue in Py2 because u'' and b'' have the same hash;
            # but it is in Py3, where they don't.
            position = self.referencePositions.get(obj)
            if position is None:
                raise InvalidPlistException("Error while writing offsets table. Object not found. %s" % obj)
            output += self.binaryInt(position, self.trailer.offsetSize)
            all_positions.append(position)
        return output

    def binaryReal(self, obj):
        # just use doubles
        result = pack('>d', obj)
        return result

    def binaryInt(self, obj, bytes=None):
        result = ''
        if bytes is None:
            bytes = self.intSize(obj)
        if bytes == 1:
            result += pack('>B', obj)
        elif bytes == 2:
            result += pack('>H', obj)
        elif bytes == 4:
            result += pack('>L', obj)
        elif bytes == 8:
            result += pack('>q', obj)
        else:
            raise InvalidPlistException("Core Foundation can't handle integers with size greater than 8 bytes.")
        return result

    def intSize(self, obj):
        """Returns the number of bytes necessary to store the given integer."""
        # SIGNED
        if obj < 0:  # Signed integer, always 8 bytes
            return 8
        # UNSIGNED
        elif obj <= 0xFF:  # 1 byte
            return 1
        elif obj <= 0xFFFF:  # 2 bytes
            return 2
        elif obj <= 0xFFFFFFFF:  # 4 bytes
            return 4
        # SIGNED
        # 0x7FFFFFFFFFFFFFFF is the max.
        elif obj <= 0x7FFFFFFFFFFFFFFF:  # 8 bytes
            return 8
        else:
            raise InvalidPlistException("Core Foundation can't handle integers with size greater than 8 bytes.")

    def realSize(self, obj):
        return 8

########NEW FILE########
__FILENAME__ = example
#!/usr/bin/env python
"""
This is an example table definition
"""

tables = {
    "plist" : {
        "name" : {
            "type" : "text",
            "nullable" : False,
        },
        "date" : {
            "type" : "text",
            "nullable" : False,
        },
        "hash" : {
            "type" : "text",
            "default" : "NULL",
        },
        "program" : {
            "type" : "text",
            "default" : "NULL",
        },
        "program_hash" : {
            "type" : "text",
            "default" : "NULL",
        },
        "programarguments" : {
            "type" : "text",
            "default" : "NULL",
        },
        "programarguments_hash" : {
            "type" : "text",
            "default" : "NULL",
        },
        "runatload" : {
            "type" : "text",
            "default" : "NULL",
        },
        "watchpaths" : {
            "type" : "text",
            "default" : "NULL",
        },
        "keepalive" : {
            "type" : "text",
            "default" : "NULL",
        },
        "startinterval" : {
            "type" : "text",
            "default" : "NULL",
        },
        "startonmount" : {
            "type" : "text",
            "default" : "NULL",
        },
        "ondemand" : {
            "type" : "text",
            "default" : "NULL",
        },
        "queuedirectories" : {
            "type" : "text",
            "default" : "NULL",
        },
        "standardinpath" : {
            "type" : "text",
            "default" : "NULL",
        },
        "standardoutpath" : {
            "type" : "text",
            "default" : "NULL",
        },
        "standarderrorpath" : {
            "type" : "text",
            "default" : "NULL",
        },
        "debug" : {
            "type" : "text",
            "default" : "NULL",
        },
        "launchonlyonce" : {
            "type" : "text",
            "default" : "NULL",
        },
        "sockets" : {
            "type" : "text",
            "default" : "NULL",
        },
        "osaxhandlers" : {
            "type" : "text",
            "default" : "NULL",
        },
        "lsenvironment" : {
            "type" : "text",
            "default" : "NULL",
        },
        "cfbundleversion" : {
            "type" : "text",
            "default" : "NULL",
        },
    },
    "kexts" : {
        "name" : {
            "type" : "text",
            "nullable" : False,
        },
        "date" : {
            "type" : "text",
            "nullable" : False,
        },
        "hash" : {
            "type" : "text",
            "default" : "NULL",
        },
    },
    "firewall_keys" : {
        "name" : {
            "type" : "text",
            "nullable" : False,
        },
        "date" : {
            "type" : "text",
            "nullable" : False,
        },
        "value" : {
            "type" : "text",
            "default" : "NULL",
        },
    },
    "firewall_exceptions" : {
        "name" : {
            "type" : "text",
            "nullable" : False,
        },
        "date" : {
            "type" : "text",
            "nullable" : False,
        },
        "state" : {
            "type" : "text",
            "default" : "NULL",
        },
    },
    "firewall_explicitauths" : {
        "name" : {
            "type" : "text",
            "nullable" : False,
        },
        "date" : {
            "type" : "text",
            "nullable" : False,
        },
    },
    "firewall_processes" : {
        "name" : {
            "type" : "text",
            "nullable" : False,
        },
        "date" : {
            "type" : "text",
            "nullable" : False,
        },
        "state" : {
            "type" : "text",
            "default" : "NULL",
        },
        "process" : {
            "type" : "text",
            "default" : "NULL",
        },
        "servicebundleid" : {
            "type" : "text",
            "default" : "NULL",
        },
    },
    "firewall_applications" : {
        "name" : {
            "type" : "text",
            "nullable" : False,
        },
        "date" : {
            "type" : "text",
            "nullable" : False,
        },
        "state" : {
            "type" : "text",
            "default" : "NULL",
        },
    },
}

########NEW FILE########
__FILENAME__ = ty_orm
#!/usr/bin/env python
"""
This is MIDAS' lightweight ORM
"""

import sqlite3
from helpers.utilities import to_ascii

class TyORM():
    """
    This is Tripyarn's lightweight ORM class
    """

    def __init__(self, filename):
        self.conn = sqlite3.connect(filename)
        self.cursor = self.conn.cursor()

    def __del__(self):
        self.conn.close()

    def commit(self):
        """commit is a simple wrapper around self.conn.commit()"""
        self.conn.commit()

    def raw_sql(self, sql, params=None):
        """raw_sql executes raw SQL provided to it in the 'sql' parameter"""
        if params:
            self.cursor.execute(sql, params)
        else:
            self.cursor.execute(sql)
        fetchall = self.cursor.fetchall()
        self.commit()
        return fetchall

    ###########################################################################
    # Create / alter table methods
    ###########################################################################

    def parse_attr(self, attr):
        """parse_attr parses table attributes"""
        i = attr.keys()[0]
        sql_col = "\"%s\" %s" % (i, attr[i]['type'])
        try:
            if attr[i]["default"]:
                sql_col += " DEFAULT %s" % attr[i]["default"]
        except KeyError:
            pass
        try:
            if not attr[i]["nullable"]:
                sql_col += " NOT NULL"
        except KeyError:
            pass
        try:
            if attr[i]["attrs"]:
                sql_col += " %s" % attr[i]["attrs"]
        except KeyError:
            pass
        try:
            if attr[i]["primary_key"]:
                sql_col += " PRIMARY KEY"
        except KeyError:
            pass
        return sql_col

    def create_table(self, table_name, attrs):
        """create_table create a table defined by a supplied table name and
        table attributes"""
        sql = "CREATE TABLE IF NOT EXISTS \"%s\"(\n\t" % table_name
        sql += "\"id\" integer PRIMARY KEY,\n\t"
        for attr in attrs:
            i = {attr : attrs[attr]}
            sql += self.parse_attr(i)
            sql += ",\n\t"
        sql = sql.strip(",\n\t")
        sql += "\n);"
        self.raw_sql(sql)

    def alter_table(self, table_name, attrs):
        """alter_table alters a given table based on a supplied table name and
        potentially updated table attributes"""
        sql = "PRAGMA table_info(\"%s\")" % table_name
        table_info = self.raw_sql(sql)
        db_cols = []
        new_cols = attrs.keys()
        for each in table_info:
            db_cols.append(each[1])
        alter_cols = list(set(new_cols) - set(db_cols))

        sql = "ALTER TABLE \"%s\" ADD COLUMN " % table_name

        new_attrs = {}
        for i in attrs:
            if i in alter_cols:
                new_attrs[i] = attrs[i]
                alter_sql = "%s%s%s" % (sql, self.parse_attr(new_attrs), ";")
                self.raw_sql(alter_sql)
                new_attrs = {}

    def create_index(self, indexes):
        """create_index creates a supplied index on a given table"""
        for index in indexes:
            sql = "CREATE INDEX IF NOT EXISTS %s;" % index
            index = self.raw_sql(sql)

    def initialize_table(self, table_name, attrs, indexes=None):
        """initialize_table creates the table if it doesn't exist, alters the
        table if it's definition is different and creates any indexes that it
        needs to if they don't already exist"""
        self.create_table(table_name, attrs)
        self.alter_table(table_name, attrs)
        if indexes:
            self.create_index(indexes)

    ###########################################################################
    # Create methods
    ###########################################################################

    def insert(self, table_name, data):
        """insert is your basic insertion method"""
        data = to_ascii(data)
        if data is None:
            return None
        sql = "INSERT INTO %s" % table_name
        sql += "(id, %s) VALUES" % ', '.join(data.keys())
        sql += "(NULL, "
        sql += ', '.join(['?'] * len(data.values()))
        sql = "%s);" % sql
        params = data.values()
        self.raw_sql(sql, params)

    ###########################################################################
    # Read methods
    ###########################################################################
    def __parse_columns(self, table_name, columns):
        """internal helper for column parsing"""
        select_columns = []
        if columns is None or columns == "*":
            sql = "PRAGMA table_info(\"%s\");" % table_name
            results = self.raw_sql(sql)
            columns = []
            for result in results:
                columns.append(result[1])
        if isinstance(columns, (list, tuple)):
            select_columns = columns
        elif isinstance(column, basestring):
            columns = columns.replace(" ", "").split(",")
            select_columns = columns

        if isinstance(select_columns, (list, tuple)) and select_columns:
            select_columns = ', '.join(select_columns)

        original_columns = []
        for i in columns:
            original_columns.append("_%s" % i)

        return columns, select_columns, original_columns

    def select(self, table_name, columns=None, where=None, limit=None, \
        order_by=None):
        """select is your basic selection method"""

        columns, select_columns, original_columns = self.__parse_columns(
            table_name,
            columns
        )

        sql = "SELECT %s FROM \"%s\"" % (select_columns, table_name)

        parameterized_attrs = None
        if where is not None:
            if not isinstance(where, (tuple, list)):
                sql += " WHERE %s" % where
            else:
                sql += "WHERE %s" % where[0]
                parameterized_attrs = where[1]

        if limit is not None:
            sql += " LIMIT %s" % limit

        if order_by is not None:
            sql += " ORDER BY %s" % order_by

        sql += ";"

        if not parameterized_attrs:
            results = self.raw_sql(sql)
        else:
            results = self.raw_sql(sql, parameterized_attrs)

        return_values = []

        for i in results:
            data = dict(zip(columns, i))
            if 'id' in data:
                del(data['id'])
            final_data = dict(
                data.items() +\
                dict(zip(original_columns, i)).items() + \
                {"_table": table_name}.items()
            )
            return_values.append(final_data)

        if not return_values:
            return None
        return return_values

    ###########################################################################
    # Update methods
    ###########################################################################

    def update(self, data):
        """update is your basic update method"""
        data = to_ascii(data)
        if data is None:
            return None
        original_data = {}
        updated_data = {}
        for i in data:
            if i.startswith("_") and i != "_table" and i != "_id":
                original_data[i] = data[i]
            else:
                updated_data[i] = data[i]

        to_change = {}
        for i in updated_data:
            if i != "_table" and i != "_id":
                if updated_data[i] != original_data["_%s" % i]:
                    to_change[i] = updated_data[i]

        sql = "UPDATE \"%s\" SET" % data["_table"]

        if not to_change:
            return None

        for i in to_change:
            sql += " %s=?," % i

        sql = sql.strip(",")

        sql += " WHERE id = ?;"

        params = to_change.values()
        params.append(data["_id"])

        self.raw_sql(sql, params)

    ###########################################################################
    # Delete methods
    ###########################################################################

    def delete(self, data):
        """delete is your basic deletion method"""
        data = to_ascii(data)
        if data is None:
            return None
        if isinstance(data, dict):
            sql = "DELETE FROM \"%s\" WHERE id = ?;" % data["_table"]
            self.raw_sql(sql, [data["_id"]])
            return
        elif isinstance(data, (list, tuple)):
            tables_and_ids = {}
            for i in data:
                table = i["_table"]
                if table not in tables_and_ids:
                    tables_and_ids[table] = []
                tables_and_ids[table].append(i["_id"])
            for k, j in tables_and_ids.iteritems():
                sql = "DELETE FROM \"%s\" WHERE id IN (%s);" % (
                    k,
                    ', '.join(['?']*len(j))
                )
                self.raw_sql(sql, j)

########NEW FILE########
__FILENAME__ = module
#!/usr/bin/env python
"""
This is a template MIDAS module.
"""

from time import time
from sys import argv
import logging


def analyze_something():
    """
    Use a function to do the heavy work of the analysis, check or verification
    """
    pass

class AnalyzeSomethingComplex(object):
    """Template class for analyzing something complex"""

    def __init__(self):
        """
        If the check requires a lot of related tasks that are better
        abstracted out into several functions, make a class
        """
        var = self.helper_function_1()
        if var:
            for each in var:
                self.helper_function_2(each)

    def helper_function_1(self):
        """
        Don't forget to write docstrings for every function!
        """
        return []

    def helper_function_2(self, each):
        """
        Don't forget to write docstrings for every function!
        """
        pass

if __name__ == "__main__":

    start = time()

    try:
        analyze_something()
        AnalyzeSomethingComplex()
    except Exception, error:
        print "ty_error_running_file=%s ty_error_message=\"%s\"" % (
            __file__,
            repr(error),
        )

    end = time()

    # to see how long this module took to execute, launch the module with
    # "--log" as a command line argument
    if "--log" in argv[1:]:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    logging.info("Execution took %s seconds." % str(end-start))

########NEW FILE########
