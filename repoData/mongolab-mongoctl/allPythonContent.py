__FILENAME__ = configure
__author__ = 'abdul'

import mongoctl.repository as repository
from mongoctl.utils import document_pretty_string
from mongoctl.mongoctl_logging import log_info

from mongoctl.objects.replicaset_cluster import ReplicaSetCluster
from mongoctl.errors import MongoctlException

###############################################################################
# configure cluster command
###############################################################################
def configure_cluster_command(parsed_options):
    cluster_id = parsed_options.cluster
    cluster = repository.lookup_and_validate_cluster(cluster_id)
    if not isinstance(cluster, ReplicaSetCluster):
        raise MongoctlException("Cluster '%s' is not a replicaset cluster" %
                                cluster.id)
    force_primary_server_id = parsed_options.forcePrimaryServer

    if parsed_options.dryRun:
        dry_run_configure_cluster(cluster,
                                  force_primary_server_id=
                                  force_primary_server_id)
    else:
        configure_cluster(cluster,
                          force_primary_server_id=
                          force_primary_server_id)

###############################################################################
# ReplicaSetCluster Methods
###############################################################################
def configure_cluster(cluster, force_primary_server_id=None):
    force_primary_server = None
    # validate force primary
    if force_primary_server_id:
        force_primary_server = \
            repository.lookup_and_validate_server(force_primary_server_id)

    configure_replica_cluster(cluster,
                              force_primary_server=force_primary_server)

###############################################################################
def configure_replica_cluster(replica_cluster, force_primary_server=None):
    replica_cluster.configure_replicaset(force_primary_server=
    force_primary_server)


###############################################################################
def dry_run_configure_cluster(cluster, force_primary_server_id=None):
    log_info("\n************ Dry Run ************\n")
    db_command = None
    force = force_primary_server_id is not None
    if cluster.is_replicaset_initialized():
        log_info("Replica set already initialized. "
                 "Making the replSetReconfig command...")
        db_command = cluster.get_replicaset_reconfig_db_command(force=force)
    else:
        log_info("Replica set has not yet been initialized."
                 " Making the replSetInitiate command...")
        db_command = cluster.get_replicaset_init_all_db_command()

    log_info("Executing the following command on the current primary:")
    log_info(document_pretty_string(db_command))

########NEW FILE########
__FILENAME__ = list_clusters
__author__ = 'abdul'

import mongoctl.repository as repository

from mongoctl.mongoctl_logging import log_info
from mongoctl.utils import to_string
###############################################################################
# list clusters command
###############################################################################
def list_clusters_command(parsed_options):
    clusters = repository.lookup_all_clusters()
    if not clusters or len(clusters) < 1:
        log_info("No clusters configured")
        return

    # sort clusters by id
    clusters = sorted(clusters, key=lambda c: c.id)
    bar = "-"*80
    print bar
    formatter = "%-25s %-40s %s"
    print formatter % ("_ID", "DESCRIPTION", "MEMBERS")
    print bar

    for cluster in clusters:
        desc = to_string(cluster.get_description())

        members_info = "[ %s ]" % ", ".join(cluster.get_members_info())

        print formatter % (cluster.id, desc, members_info)
    print "\n"


########NEW FILE########
__FILENAME__ = show
__author__ = 'abdul'

import mongoctl.repository as repository

from mongoctl.errors import MongoctlException
from mongoctl.mongoctl_logging import log_info

###############################################################################
# show cluster command
###############################################################################
def show_cluster_command(parsed_options):
    cluster = repository.lookup_cluster(parsed_options.cluster)
    if cluster is None:
        raise MongoctlException("Could not find cluster '%s'." %
                                parsed_options.cluster)
    log_info("Configuration for cluster '%s':" % parsed_options.cluster)
    print cluster



########NEW FILE########
__FILENAME__ = command_utils
__author__ = 'abdul'

import os
import re

import mongoctl.repository as repository
from mongoctl.mongoctl_logging import *
from mongoctl import config
from mongoctl.errors import MongoctlException
from mongoctl.utils import is_exe, which, resolve_path, execute_command
from mongoctl.mongo_version import make_version_info, MongoEdition
from mongoctl.mongo_uri_tools import is_mongo_uri

###############################################################################
# CONSTS
###############################################################################

MONGO_HOME_ENV_VAR = "MONGO_HOME"

MONGO_VERSIONS_ENV_VAR = "MONGO_VERSIONS"

# VERSION CHECK PREFERENCE CONSTS
VERSION_PREF_EXACT = 0
VERSION_PREF_GREATER = 1
VERSION_PREF_MAJOR_GE = 2
VERSION_PREF_LATEST_STABLE = 3
VERSION_PREF_EXACT_OR_MINOR = 4

def extract_mongo_exe_options(parsed_args, supported_options):
    options_extract = {}

    # Iterating over parsed options dict
    # Yeah in a hacky way since there is no clean documented way of doing that
    # See http://bugs.python.org/issue11076 for more details
    # this should be changed when argparse provides a cleaner way

    for (option_name,option_val) in parsed_args.__dict__.items():
        if option_name in supported_options and option_val is not None:
            options_extract[option_name] = option_val

    return options_extract



###############################################################################
def get_mongo_executable(version_info,
                         executable_name,
                         version_check_pref=VERSION_PREF_EXACT):

    mongo_home = os.getenv(MONGO_HOME_ENV_VAR)
    mongo_installs_dir = config.get_mongodb_installs_dir()
    version_number = version_info and version_info.version_number
    mongo_edition = version_info and (version_info.edition or
                                            MongoEdition.COMMUNITY)

    ver_disp = "[Unspecified]" if version_number is None else version_number
    log_verbose("Looking for a compatible %s for mongoVersion=%s." %
                (executable_name, ver_disp))
    exe_version_tuples = find_all_executables(executable_name)

    if len(exe_version_tuples) > 0:
        selected_exe = best_executable_match(executable_name,
                                             exe_version_tuples,
                                             version_info,
                                             version_check_pref=
                                             version_check_pref)
        if selected_exe is not None:
            log_info("Using %s at '%s' version '%s'..." %
                     (executable_name,
                      selected_exe.path,
                      selected_exe.version))
            return selected_exe

    ## ok nothing found at all. wtf case
    msg = ("Unable to find a compatible '%s' executable "
           "for version %s (edition %s). You may need to run 'mongoctl "
           "install-mongodb %s %s' to install it.\n\n"
           "Here is your enviroment:\n\n"
           "$PATH=%s\n\n"
           "$MONGO_HOME=%s\n\n"
           "mongoDBInstallationsDirectory=%s (in mongoctl.config)" %
           (executable_name, ver_disp, mongo_edition, ver_disp,
            "--edition %s" % mongo_edition if
            mongo_edition != MongoEdition.COMMUNITY else "",
            os.getenv("PATH"),
            mongo_home,
            mongo_installs_dir))

    raise MongoctlException(msg)

###############################################################################
def find_all_executables(executable_name):
    # create a list of all available executables found and then return the best
    # match if applicable
    executables_found = []

    ####### Look in $PATH
    path_executable = which(executable_name)
    if path_executable is not None:
        add_to_executables_found(executables_found, path_executable)

    #### Look in $MONGO_HOME if set
    mongo_home = os.getenv(MONGO_HOME_ENV_VAR)

    if mongo_home is not None:
        mongo_home = resolve_path(mongo_home)
        mongo_home_exe = get_mongo_home_exe(mongo_home, executable_name)
        add_to_executables_found(executables_found, mongo_home_exe)
        # Look in mongod_installs_dir if set
    mongo_installs_dir = config.get_mongodb_installs_dir()

    if mongo_installs_dir is not None:
        if os.path.exists(mongo_installs_dir):
            for mongo_installation in os.listdir(mongo_installs_dir):
                child_mongo_home = os.path.join(mongo_installs_dir,
                                                mongo_installation)

                child_mongo_exe = get_mongo_home_exe(child_mongo_home,
                                                     executable_name)

                add_to_executables_found(executables_found, child_mongo_exe)

    return get_exe_version_tuples(executables_found)

###############################################################################
def add_to_executables_found(executables_found, executable):
    if is_valid_mongo_exe(executable):
        if executable not in executables_found:
            executables_found.append(executable)
    else:
        log_verbose("Not a valid executable '%s'. Skipping..." % executable)

###############################################################################
def best_executable_match(executable_name,
                          exe_version_tuples,
                          version_object,
                          version_check_pref=VERSION_PREF_EXACT):

    match_func = exact_exe_version_match

    exe_versions_str = exe_version_tuples_to_strs(exe_version_tuples)

    log_verbose("Found the following %s's. Selecting best match "
                "for version %s\n%s" %(executable_name, version_object,
                                       exe_versions_str))

    if version_object is None:
        log_verbose("mongoVersion is null. "
                    "Selecting default %s" % executable_name)
        match_func = default_match
    elif version_check_pref == VERSION_PREF_LATEST_STABLE:
        match_func = latest_stable_exe
    elif version_check_pref == VERSION_PREF_MAJOR_GE:
        match_func = major_ge_exe_version_match
    elif version_check_pref == VERSION_PREF_EXACT_OR_MINOR:
        match_func = exact_or_minor_exe_version_match

    return match_func(executable_name, exe_version_tuples, version_object)

###############################################################################
def default_match(executable_name, exe_version_tuples, version):
    default_exe = latest_stable_exe(executable_name, exe_version_tuples)
    if default_exe is None:
        log_verbose("No stable %s found. Looking for any latest available %s "
                    "..." % (executable_name, executable_name))
        default_exe = latest_exe(executable_name, exe_version_tuples)
    return default_exe

###############################################################################
def exact_exe_version_match(executable_name, exe_version_tuples, version):

    for mongo_exe,exe_version in exe_version_tuples:
        if exe_version == version:
            return mongo_exe_object(mongo_exe, exe_version)

    return None

###############################################################################
def latest_stable_exe(executable_name, exe_version_tuples, version=None):
    log_verbose("Find the latest stable %s" % executable_name)
    # find greatest stable exe
    # hold values in a list of (exe,version) tuples
    stable_exes = []
    for mongo_exe,exe_version in exe_version_tuples:
        # get the release number (e.g. A.B.C, release number is B here)
        release_num = exe_version.parts[0][1]
        # stable releases are the even ones
        if (release_num % 2) == 0:
            stable_exes.append((mongo_exe, exe_version))

    return latest_exe(executable_name, stable_exes)

###############################################################################
def latest_exe(executable_name, exe_version_tuples, version=None):

    # Return nothing if nothing compatible
    if len(exe_version_tuples) == 0:
        return None
        # sort desc by version
    exe_version_tuples.sort(key=lambda t: t[1], reverse=True)

    exe = exe_version_tuples[0]
    return mongo_exe_object(exe[0], exe[1])

###############################################################################
def major_ge_exe_version_match(executable_name, exe_version_tuples, version):
    # find all compatible exes then return closet match (min version)
    # hold values in a list of (exe,version) tuples
    compatible_exes = []
    for mongo_exe,exe_version in exe_version_tuples:
        if exe_version.parts[0][0] >= version.parts[0][0]:
            compatible_exes.append((mongo_exe, exe_version))

    # Return nothing if nothing compatible
    if len(compatible_exes) == 0:
        return None
        # find the best fit
    compatible_exes.sort(key=lambda t: t[1])
    exe = compatible_exes[-1]
    return mongo_exe_object(exe[0], exe[1])

###############################################################################
def exact_or_minor_exe_version_match(executable_name,
                                     exe_version_tuples,
                                     version):
    """
    IF there is an exact match then use it
     OTHERWISE try to find a minor version match
    """
    exe = exact_exe_version_match(executable_name,
                                  exe_version_tuples,
                                  version)

    if not exe:
        exe = minor_exe_version_match(executable_name,
                                      exe_version_tuples,
                                      version)
    return exe

###############################################################################
def minor_exe_version_match(executable_name,
                            exe_version_tuples,
                            version):

    # hold values in a list of (exe,version) tuples
    compatible_exes = []
    for mongo_exe,exe_version in exe_version_tuples:
        # compatible ==> major + minor equality
        if (exe_version.parts[0][0] == version.parts[0][0] and
                    exe_version.parts[0][1] == version.parts[0][1]):
            compatible_exes.append((mongo_exe, exe_version))

    # Return nothing if nothing compatible
    if len(compatible_exes) == 0:
        return None
        # find the best fit
    compatible_exes.sort(key=lambda t: t[1])
    exe = compatible_exes[-1]
    return mongo_exe_object(exe[0], exe[1])

###############################################################################
def get_exe_version_tuples(executables):
    exe_ver_tuples = []
    for mongo_exe in executables:
        try:
            exe_version = mongo_exe_version(mongo_exe)
            exe_ver_tuples.append((mongo_exe, exe_version))
        except Exception, e:
            log_exception(e)
            log_verbose("Skipping executable '%s': %s" % (mongo_exe, e))

    return exe_ver_tuples

###############################################################################
def exe_version_tuples_to_strs(exe_ver_tuples):
    strs = []
    for mongo_exe,exe_version in exe_ver_tuples:
        strs.append("%s = %s" % (mongo_exe, exe_version))
    return "\n".join(strs)

###############################################################################
def is_valid_mongo_exe(path):
    return path is not None and is_exe(path)


###############################################################################
def get_mongo_home_exe(mongo_home, executable_name):
    return os.path.join(mongo_home, 'bin', executable_name)

###############################################################################
def mongo_exe_version(mongo_exe):
    mongod_path = os.path.join(os.path.dirname(mongo_exe), "mongod")

    try:
        re_expr = "v?((([0-9]+)\.([0-9]+)\.([0-9]+))([^, ]*))"
        vers_spew = execute_command([mongod_path, "--version"])
        # only take first line of spew
        vers_spew_line = vers_spew.split('\n')[0]
        vers_grep = re.findall(re_expr, vers_spew_line)
        full_version = vers_grep[-1][0]
        edition = (MongoEdition.ENTERPRISE if "subscription" in
                                              vers_spew else None)
        result = make_version_info(full_version, edition=edition)
        if result is not None:
            return result
        else:
            raise MongoctlException("Cannot parse mongo version from the"
                                    " output of '%s --version'" % mongod_path)
    except Exception, e:
        log_exception(e)
        raise MongoctlException("Unable to get mongo version of '%s'."
                                " Cause: %s" % (mongod_path, e))

###############################################################################
class MongoExeObject():
    pass

###############################################################################
def mongo_exe_object(exe_path, exe_version):
    exe_obj = MongoExeObject()
    exe_obj.path =  exe_path
    exe_obj.version =  exe_version

    return exe_obj

###############################################################################
def options_to_command_args(args):

    command_args=[]

    for (arg_name,arg_val) in sorted(args.iteritems()):
    # append the arg name and val as needed
        if not arg_val:
            continue
        elif arg_val == True:
            command_args.append("--%s" % arg_name)
        else:
            command_args.append("--%s" % arg_name)
            command_args.append(str(arg_val))

    return command_args


###############################################################################
def is_server_or_cluster_db_address(value):
    """
    checks if the specified value is in the form of
    [server or cluster id][/database]
    """
    # check if value is an id string
    id_path = value.split("/")
    id = id_path[0]
    return len(id_path) <= 2 and (repository.lookup_server(id) or
                                  repository.lookup_cluster(id))

###############################################################################
def is_db_address(value):
    """
    Checks if the specified value is a valid mongoctl database address
    """
    return value and (is_mongo_uri(value) or
                      is_server_or_cluster_db_address(value))


###############################################################################
def is_dbpath(value):
    """
    Checks if the specified value is a dbpath. dbpath could be an absolute
    file path, relative path or a file uri
    """

    value = resolve_path(value)
    return os.path.exists(value)



########NEW FILE########
__FILENAME__ = connect
__author__ = 'abdul'

import mongoctl.repository as repository

from mongoctl.commands.command_utils import (
    extract_mongo_exe_options, get_mongo_executable, options_to_command_args,
    VERSION_PREF_MAJOR_GE
)
from mongoctl.mongoctl_logging import log_info, log_error
from mongoctl.mongo_uri_tools import is_mongo_uri, parse_mongo_uri

from mongoctl.errors import MongoctlException

from mongoctl.utils import call_command
from mongoctl.objects.server import Server

from mongoctl.objects.mongod import MongodServer

###############################################################################
# CONSTS
###############################################################################
SUPPORTED_MONGO_SHELL_OPTIONS = [
    "shell",
    "norc",
    "quiet",
    "eval",
    "verbose",
    "ipv6",
    ]

###############################################################################
# connect command
###############################################################################
def connect_command(parsed_options):
    shell_options = extract_mongo_shell_options(parsed_options)
    open_mongo_shell_to(parsed_options.dbAddress,
                        username=parsed_options.username,
                        password=parsed_options.password,
                        shell_options=shell_options,
                        js_files=parsed_options.jsFiles)


###############################################################################
def extract_mongo_shell_options(parsed_args):
    return extract_mongo_exe_options(parsed_args,
                                     SUPPORTED_MONGO_SHELL_OPTIONS)


###############################################################################
# open_mongo_shell_to
###############################################################################
def open_mongo_shell_to(db_address,
                        username=None,
                        password=None,
                        shell_options={},
                        js_files=[]):
    if is_mongo_uri(db_address):
        open_mongo_shell_to_uri(db_address, username, password,
                                shell_options, js_files)
        return

    # db_address is an id string
    id_path = db_address.split("/")
    id = id_path[0]
    database = id_path[1] if len(id_path) == 2 else None

    server = repository.lookup_server(id)
    if server:
        open_mongo_shell_to_server(server, database, username, password,
                                   shell_options, js_files)
        return

    # Maybe cluster?
    cluster = repository.lookup_cluster(id)
    if cluster:
        open_mongo_shell_to_cluster(cluster, database, username, password,
                                    shell_options, js_files)
        return
        # Unknown destination
    raise MongoctlException("Unknown db address '%s'" % db_address)

###############################################################################
def open_mongo_shell_to_server(server,
                               database=None,
                               username=None,
                               password=None,
                               shell_options={},
                               js_files=[]):
    repository.validate_server(server)

    if not database:
        if isinstance(server, MongodServer) and server.is_arbiter_server():
            database = "local"
        else:
            database = "admin"

    if username or server.needs_to_auth(database):
        # authenticate and grab a working username/password
        username, password = server.get_working_login(database, username,
                                                      password)



    do_open_mongo_shell_to(server.get_connection_address(),
                           database,
                           username,
                           password,
                           server.get_mongo_version_info(),
                           shell_options,
                           js_files)

###############################################################################
def open_mongo_shell_to_cluster(cluster,
                                database=None,
                                username=None,
                                password=None,
                                shell_options={},
                                js_files=[]):

    log_info("Locating default server for cluster '%s'..." % cluster.id)
    default_server = cluster.get_default_server()
    if default_server:
        log_info("Connecting to server '%s'" % default_server.id)
        open_mongo_shell_to_server(default_server,
                                   database=database,
                                   username=username,
                                   password=password,
                                   shell_options=shell_options,
                                   js_files=js_files)
    else:
        log_error("No default server found for cluster '%s'" %
                  cluster.id)

###############################################################################
def open_mongo_shell_to_uri(uri,
                            username=None,
                            password=None,
                            shell_options={},
                            js_files=[]):

    uri_wrapper = parse_mongo_uri(uri)
    database = uri_wrapper.database
    username = username if username else uri_wrapper.username
    password = password if password else uri_wrapper.password

    server_or_cluster = repository.build_server_or_cluster_from_uri(uri)

    if isinstance(server_or_cluster, Server):
        open_mongo_shell_to_server(server_or_cluster,
                                   database=database,
                                   username=username,
                                   password=password,
                                   shell_options=shell_options,
                                   js_files=js_files)
    else:
        open_mongo_shell_to_cluster(server_or_cluster,
                                    database=database,
                                    username=username,
                                    password=password,
                                    shell_options=shell_options,
                                    js_files=js_files)

###############################################################################
def do_open_mongo_shell_to(address,
                           database=None,
                           username=None,
                           password=None,
                           server_version=None,
                           shell_options={},
                           js_files=[]):

    # default database to admin
    database = database if database else "admin"


    connect_cmd = [get_mongo_shell_executable(server_version),
                   "%s/%s" % (address, database)]

    if username:
        connect_cmd.extend(["-u",username, "-p"])
        if password:
            connect_cmd.extend([password])

    # append shell options
    if shell_options:
        connect_cmd.extend(options_to_command_args(shell_options))

    # append js files
    if js_files:
        connect_cmd.extend(js_files)

    cmd_display =  connect_cmd[:]
    # mask user/password
    if username:
        cmd_display[cmd_display.index("-u") + 1] =  "****"
        if password:
            cmd_display[cmd_display.index("-p") + 1] =  "****"

    log_info("Executing command: \n%s" % " ".join(cmd_display))
    call_command(connect_cmd, bubble_exit_code=True)


###############################################################################
def get_mongo_shell_executable(server_version):
    shell_exe = get_mongo_executable(server_version,
                                     'mongo',
                                     version_check_pref=VERSION_PREF_MAJOR_GE)
    return shell_exe.path
########NEW FILE########
__FILENAME__ = dump
__author__ = 'abdul'


import mongoctl.repository as repository

from mongoctl.mongo_uri_tools import is_mongo_uri, parse_mongo_uri

from mongoctl.utils import resolve_path
from mongoctl.mongoctl_logging import log_info , log_warning

from mongoctl.commands.command_utils import (
    is_db_address, is_dbpath, extract_mongo_exe_options, get_mongo_executable,
    options_to_command_args,
    VERSION_PREF_EXACT_OR_MINOR
    )
from mongoctl.errors import MongoctlException

from mongoctl.utils import call_command
from mongoctl.objects.server import Server
from mongoctl.mongo_version import make_version_info, VersionInfo


###############################################################################
# CONSTS
###############################################################################

SUPPORTED_MONGO_DUMP_OPTIONS = [
    "directoryperdb",
    "journal",
    "collection",
    "out",
    "query",
    "oplog",
    "repair",
    "forceTableScan",
    "ipv6",
    "verbose",
    "authenticationDatabase",
    "dumpDbUsersAndRoles"
]


###############################################################################
# dump command
###############################################################################
def dump_command(parsed_options):

    # get and validate dump target
    target = parsed_options.target
    use_best_secondary = parsed_options.useBestSecondary
    #max_repl_lag = parsed_options.maxReplLag
    is_addr = is_db_address(target)
    is_path = is_dbpath(target)

    if is_addr and is_path:
        msg = ("Ambiguous target value '%s'. Your target matches both a dbpath"
               " and a db address. Use prefix 'file://', 'cluster://' or"
               " 'server://' to make it more specific" % target)

        raise MongoctlException(msg)

    elif not (is_addr or is_path):
        raise MongoctlException("Invalid target value '%s'. Target has to be"
                                " a valid db address or dbpath." % target)
    dump_options = extract_mongo_dump_options(parsed_options)

    if is_addr:
        mongo_dump_db_address(target,
                              username=parsed_options.username,
                              password=parsed_options.password,
                              use_best_secondary=use_best_secondary,
                              max_repl_lag=None,
                              dump_options=dump_options)
    else:
        dbpath = resolve_path(target)
        mongo_dump_db_path(dbpath, dump_options=dump_options)

###############################################################################
# mongo_dump
###############################################################################
def mongo_dump_db_address(db_address,
                          username=None,
                          password=None,
                          use_best_secondary=False,
                          max_repl_lag=None,
                          dump_options=None):

    if is_mongo_uri(db_address):
        mongo_dump_uri(uri=db_address, username=username, password=password,
                       use_best_secondary=use_best_secondary,
                       dump_options=dump_options)
        return

    # db_address is an id string
    id_path = db_address.split("/")
    id = id_path[0]
    database = id_path[1] if len(id_path) == 2 else None

    server = repository.lookup_server(id)
    if server:
        mongo_dump_server(server, database=database, username=username,
                          password=password, dump_options=dump_options)
        return
    else:
        cluster = repository.lookup_cluster(id)
        if cluster:
            mongo_dump_cluster(cluster, database=database, username=username,
                               password=password,
                               use_best_secondary=use_best_secondary,
                               max_repl_lag=max_repl_lag,
                               dump_options=dump_options)
            return

            # Unknown destination
    raise MongoctlException("Unknown db address '%s'" % db_address)

###############################################################################
def mongo_dump_db_path(dbpath, dump_options=None):

    do_mongo_dump(dbpath=dbpath,
                  dump_options=dump_options)

###############################################################################
def mongo_dump_uri(uri,
                   username=None,
                   password=None,
                   use_best_secondary=False,
                   dump_options=None):

    uri_wrapper = parse_mongo_uri(uri)
    database = uri_wrapper.database
    username = username if username else uri_wrapper.username
    password = password if password else uri_wrapper.password

    server_or_cluster = repository.build_server_or_cluster_from_uri(uri)

    if isinstance(server_or_cluster, Server):
        mongo_dump_server(server_or_cluster,
                          database=database,
                          username=username,
                          password=password,
                          dump_options=dump_options)
    else:
        mongo_dump_cluster(server_or_cluster,
                           database=database,
                           username=username,
                           password=password,
                           use_best_secondary=use_best_secondary,
                           dump_options=dump_options)

###############################################################################
def mongo_dump_server(server,
                      database=None,
                      username=None,
                      password=None,
                      dump_options=None):
    repository.validate_server(server)

    auth_db = database or "admin"
    # auto complete password if possible
    if username:
        if not password and database:
            password = server.lookup_password(database, username)
        if not password:
            password = server.lookup_password("admin", username)


    do_mongo_dump(host=server.get_connection_host_address(),
                  port=server.get_port(),
                  database=database,
                  username=username,
                  password=password,
                  version_info=server.get_mongo_version_info(),
                  dump_options=dump_options)

###############################################################################
def mongo_dump_cluster(cluster,
                       database=None,
                       username=None,
                       password=None,
                       use_best_secondary=False,
                       max_repl_lag=False,
                       dump_options=None):
    repository.validate_cluster(cluster)

    if use_best_secondary:
        mongo_dump_cluster_best_secondary(cluster=cluster,
                                          max_repl_lag=max_repl_lag,
                                          database=database,
                                          username=username,
                                          password=password,
                                          dump_options=dump_options)
    else:
        mongo_dump_cluster_primary(cluster=cluster,
                                   database=database,
                                   username=username,
                                   password=password,
                                   dump_options=dump_options)
###############################################################################
def mongo_dump_cluster_primary(cluster,
                               database=None,
                               username=None,
                               password=None,
                               dump_options=None):
    log_info("Locating default server for cluster '%s'..." % cluster.id)
    default_server = cluster.get_default_server()
    if default_server:
        log_info("Dumping default server '%s'..." % default_server.id)
        mongo_dump_server(default_server,
                          database=database,
                          username=username,
                          password=password,
                          dump_options=dump_options)
    else:
        raise MongoctlException("No default server found for cluster '%s'" %
                                cluster.id)


###############################################################################
def mongo_dump_cluster_best_secondary(cluster,
                                      max_repl_lag=None,
                                      database=None,
                                      username=None,
                                      password=None,
                                      dump_options=None):

    #max_repl_lag = max_repl_lag or 3600
    log_info("Finding best secondary server for cluster '%s' with replication"
             " lag less than max (%s seconds)..." %
             (cluster.id, max_repl_lag))
    best_secondary = cluster.get_dump_best_secondary(max_repl_lag=max_repl_lag)
    if best_secondary:
        server = best_secondary.get_server()

        log_info("Found secondary server '%s'. Dumping..." % server.id)
        mongo_dump_server(server, database=database, username=username,
                          password=password, dump_options=dump_options)
    else:
        raise MongoctlException("No secondary server found for cluster '%s'" %
                                cluster.id)

###############################################################################
def do_mongo_dump(host=None,
                  port=None,
                  dbpath=None,
                  database=None,
                  username=None,
                  password=None,
                  version_info=None,
                  dump_options=None):


    # create dump command with host and port
    dump_cmd = [get_mongo_dump_executable(version_info)]

    if host:
        dump_cmd.extend(["--host", host])
    if port:
        dump_cmd.extend(["--port", str(port)])

    # dbpath
    if dbpath:
        dump_cmd.extend(["--dbpath", dbpath])

    # database
    if database:
        dump_cmd.extend(["-d", database])

    # username and password
    if username:
        dump_cmd.extend(["-u", username, "-p"])
        if password:
            dump_cmd.append(password)

    # ignore authenticationDatabase option is version_info is less than 2.4.0
    if (dump_options and "authenticationDatabase" in dump_options and
            version_info and version_info < VersionInfo("2.4.0")):
        dump_options.pop("authenticationDatabase", None)

    # ignore dumpDbUsersAndRoles option is version_info is less than 2.6.0
    if (dump_options and "dumpDbUsersAndRoles" in dump_options and
            version_info and version_info < VersionInfo("2.6.0")):
        dump_options.pop("dumpDbUsersAndRoles", None)

    # append shell options
    if dump_options:
        dump_cmd.extend(options_to_command_args(dump_options))


    cmd_display =  dump_cmd[:]
    # mask user/password
    if username:
        cmd_display[cmd_display.index("-u") + 1] = "****"
        if password:
            cmd_display[cmd_display.index("-p") + 1] =  "****"



    log_info("Executing command: \n%s" % " ".join(cmd_display))
    call_command(dump_cmd, bubble_exit_code=True)


###############################################################################
def extract_mongo_dump_options(parsed_args):
    return extract_mongo_exe_options(parsed_args,
                                     SUPPORTED_MONGO_DUMP_OPTIONS)

###############################################################################
def get_mongo_dump_executable(version_info):
    dump_exe = get_mongo_executable(version_info,
                                    'mongodump',
                                    version_check_pref=
                                    VERSION_PREF_EXACT_OR_MINOR)
    # Warn the user if it is not an exact match (minor match)
    if version_info and version_info != dump_exe.version:
        log_warning("Using mongodump '%s' that does not exactly match "
                    "server version '%s'" % (dump_exe.version, version_info))

    return dump_exe.path

########NEW FILE########
__FILENAME__ = restore
__author__ = 'abdul'

import mongoctl.repository as repository

from mongoctl.mongo_uri_tools import is_mongo_uri, parse_mongo_uri

from mongoctl.utils import resolve_path
from mongoctl.mongoctl_logging import log_info , log_warning

from mongoctl.commands.command_utils import (
    is_db_address, is_dbpath, extract_mongo_exe_options, get_mongo_executable,
    options_to_command_args,
    VERSION_PREF_EXACT_OR_MINOR
)
from mongoctl.errors import MongoctlException

from mongoctl.utils import call_command
from mongoctl.objects.server import Server
from mongoctl.mongo_version import make_version_info, VersionInfo

###############################################################################
# CONSTS
###############################################################################
SUPPORTED_MONGO_RESTORE_OPTIONS = [
    "directoryperdb",
    "journal",
    "collection",
    "ipv6",
    "filter",
    "objcheck",
    "drop",
    "oplogReplay",
    "keepIndexVersion",
    "verbose",
    "authenticationDatabase",
    "restoreDbUsersAndRoles"
]


###############################################################################
# restore command
###############################################################################
def restore_command(parsed_options):

    # get and validate source/destination
    source = parsed_options.source
    destination = parsed_options.destination

    is_addr = is_db_address(destination)
    is_path = is_dbpath(destination)

    if is_addr and is_path:
        msg = ("Ambiguous destination value '%s'. Your destination matches"
               " both a dbpath and a db address. Use prefix 'file://',"
               " 'cluster://' or 'server://' to make it more specific" %
               destination)

        raise MongoctlException(msg)

    elif not (is_addr or is_path):
        raise MongoctlException("Invalid destination value '%s'. Destination has to be"
                                " a valid db address or dbpath." % destination)
    restore_options = extract_mongo_restore_options(parsed_options)

    if is_addr:
        mongo_restore_db_address(destination,
                                 source,
                                 username=parsed_options.username,
                                 password=parsed_options.password,
                                 restore_options=restore_options)
    else:
        dbpath = resolve_path(destination)
        mongo_restore_db_path(dbpath, source, restore_options=restore_options)


###############################################################################
# mongo_restore
###############################################################################
def mongo_restore_db_address(db_address,
                             source,
                             username=None,
                             password=None,
                             restore_options=None):

    if is_mongo_uri(db_address):
        mongo_restore_uri(db_address, source, username, password,
                          restore_options)
        return

    # db_address is an id string
    id_path = db_address.split("/")
    id = id_path[0]
    database = id_path[1] if len(id_path) == 2 else None

    server = repository.lookup_server(id)
    if server:
        mongo_restore_server(server, source, database=database,
                             username=username, password=password,
                             restore_options=restore_options)
        return
    else:
        cluster = repository.lookup_cluster(id)
        if cluster:
            mongo_restore_cluster(cluster, source, database=database,
                                  username=username, password=password,
                                  restore_options=restore_options)
            return

    raise MongoctlException("Unknown db address '%s'" % db_address)

###############################################################################
def mongo_restore_db_path(dbpath, source, restore_options=None):
    do_mongo_restore(source, dbpath=dbpath, restore_options=restore_options)

###############################################################################
def mongo_restore_uri(uri, source,
                      username=None,
                      password=None,
                      restore_options=None):

    uri_wrapper = parse_mongo_uri(uri)
    database = uri_wrapper.database
    username = username if username else uri_wrapper.username
    password = password if password else uri_wrapper.password

    server_or_cluster = repository.build_server_or_cluster_from_uri(uri)

    if isinstance(server_or_cluster, Server):
        mongo_restore_server(server_or_cluster, source, database=database,
                             username=username, password=password,
                             restore_options=restore_options)
    else:
        mongo_restore_cluster(server_or_cluster, source, database=database,
                              username=username, password=password,
                              restore_options=restore_options)

###############################################################################
def mongo_restore_server(server, source,
                         database=None,
                         username=None,
                         password=None,
                         restore_options=None):
    repository.validate_server(server)

    # auto complete password if possible
    if username:
        if not password and database:
            password = server.lookup_password(database, username)
        if not password:
            password = server.lookup_password("admin", username)

    do_mongo_restore(source,
                     host=server.get_connection_host_address(),
                     port=server.get_port(),
                     database=database,
                     username=username,
                     password=password,
                     version_info=server.get_mongo_version_info(),
                     restore_options=restore_options)

###############################################################################
def mongo_restore_cluster(cluster, source,
                          database=None,
                          username=None,
                          password=None,
                          restore_options=None):
    repository.validate_cluster(cluster)
    log_info("Locating default server for cluster '%s'..." % cluster.id)
    default_server = cluster.get_default_server()
    if default_server:
        log_info("Restoring default server '%s'" % default_server.id)
        mongo_restore_server(default_server, source,
                             database=database,
                             username=username,
                             password=password,
                             restore_options=restore_options)
    else:
        raise MongoctlException("No default server found for cluster '%s'" %
                                cluster.id)

###############################################################################
def do_mongo_restore(source,
                     host=None,
                     port=None,
                     dbpath=None,
                     database=None,
                     username=None,
                     password=None,
                     version_info=None,
                     restore_options=None):


    # create restore command with host and port
    restore_cmd = [get_mongo_restore_executable(version_info)]

    if host:
        restore_cmd.extend(["--host", host])
    if port:
        restore_cmd.extend(["--port", str(port)])

    # dbpath
    if dbpath:
        restore_cmd.extend(["--dbpath", dbpath])

    # database
    if database:
        restore_cmd.extend(["-d", database])

    # username and password
    if username:
        restore_cmd.extend(["-u", username, "-p"])
        if password:
            restore_cmd.append(password)

    # ignore authenticationDatabase option is version_info is less than 2.4.0
    if (restore_options and "authenticationDatabase" in restore_options and
            version_info and version_info < make_version_info("2.4.0")):
        restore_options.pop("authenticationDatabase", None)

    # ignore restoreDbUsersAndRoles option is version_info is less than 2.6.0
    if (restore_options and "restoreDbUsersAndRoles" in restore_options and
            version_info and version_info < make_version_info("2.6.0")):
        restore_options.pop("restoreDbUsersAndRoles", None)

    # append shell options
    if restore_options:
        restore_cmd.extend(options_to_command_args(restore_options))

    # pass source arg
    restore_cmd.append(source)

    cmd_display =  restore_cmd[:]
    # mask user/password
    if username:
        cmd_display[cmd_display.index("-u") + 1] =  "****"
        if password:
            cmd_display[cmd_display.index("-p") + 1] =  "****"

    # execute!
    log_info("Executing command: \n%s" % " ".join(cmd_display))
    call_command(restore_cmd, bubble_exit_code=True)


###############################################################################
def get_mongo_restore_executable(version_info):
    restore_exe = get_mongo_executable(version_info,
                                       'mongorestore',
                                       version_check_pref=
                                       VERSION_PREF_EXACT_OR_MINOR)
    # Warn the user if it is not an exact match (minor match)
    if version_info and version_info != restore_exe.version:
        log_warning("Using mongorestore '%s' that does not exactly match"
                    "server version '%s'" % (restore_exe.version,
                                             version_info))

    return restore_exe.path

###############################################################################
def extract_mongo_restore_options(parsed_args):
    return extract_mongo_exe_options(parsed_args,
                                     SUPPORTED_MONGO_RESTORE_OPTIONS)

########NEW FILE########
__FILENAME__ = status
__author__ = 'abdul'

import mongoctl.repository as repository

from mongoctl.mongoctl_logging import *
from mongoctl.errors import MongoctlException
from mongoctl.utils import document_pretty_string

###############################################################################
# status command TODO: parsed?
###############################################################################
def status_command(parsed_options):
    # we need to print status json to stdout so that its seperate from all
    # other messages that are printed on stderr. This is so scripts can read
    # status json and parse it if it needs

    id = parsed_options.id
    server = repository.lookup_server(id)
    if server:
        log_info("Status for server '%s':" % id)
        status = server.get_status(admin=True)
    else:
        cluster = repository.lookup_cluster(id)
        if cluster:
            log_info("Status for cluster '%s':" % id)
            status = cluster.get_status()
        else:
            raise MongoctlException("Cannot find a server or a cluster with"
                                    " id '%s'" % id)

    status_str = document_pretty_string(status)
    stdout_log(status_str)
    return status

########NEW FILE########
__FILENAME__ = install
__author__ = 'abdul'

import os
import platform
import urllib
import shutil

from mongoctl.mongo_version import is_valid_version_info

import mongoctl.config as config
from mongoctl.prompt import prompt_execute_task, is_interactive_mode

from mongoctl.utils import ensure_dir, dir_exists
from mongoctl.mongoctl_logging import *

from mongoctl.errors import MongoctlException

from mongoctl.utils import call_command, which

from mongoctl.mongo_version import make_version_info
from mongoctl.commands.command_utils import find_all_executables
from mongoctl.objects.server import EDITION_COMMUNITY, EDITION_ENTERPRISE
###############################################################################
# CONSTS
###############################################################################
LATEST_VERSION_FILE_URL = "https://raw.github.com/mongolab/mongoctl/master/" \
                          "mongo_latest_stable_version.txt"


###############################################################################
# install command
###############################################################################
def install_command(parsed_options):
    install_mongodb(parsed_options.version, edition=parsed_options.edition)

###############################################################################
# uninstall command
###############################################################################
def uninstall_command(parsed_options):
    uninstall_mongodb(parsed_options.version, edition=parsed_options.edition)


###############################################################################
# list-versions command
###############################################################################
def list_versions_command(parsed_options):
    mongo_installations = find__all_mongo_installations()

    bar = "-" * 80
    print bar
    formatter = "%-20s %-20s %s"
    print formatter % ("VERSION", "EDITION", "LOCATION")
    print bar

    for install_dir,version in mongo_installations:
        print formatter % (version.version_number,
                           version.edition, install_dir)
    print "\n"


###############################################################################
# install_mongodb
###############################################################################
def install_mongodb(version_number, edition=None):

    bits = platform.architecture()[0].replace("bit", "")
    os_name = platform.system().lower()

    if os_name == 'darwin' and platform.mac_ver():
        os_name = "osx"

    if version_number is None:
        version_number = fetch_latest_stable_version()
        log_info("Installing latest stable MongoDB version '%s'..." %
                 version_number)

    version_info = make_version_info(version_number, edition)
    return do_install_mongodb(os_name, bits, version_info)

###############################################################################
def do_install_mongodb(os_name, bits, version_info):

    mongodb_installs_dir = config.get_mongodb_installs_dir()
    if not mongodb_installs_dir:
        raise MongoctlException("No mongoDBInstallationsDirectory configured"
                                " in mongoctl.config")

    platform_spec = get_validate_platform_spec(os_name, bits)

    log_verbose("INSTALL_MONGODB: OS='%s' , BITS='%s' , VERSION='%s', "
                "PLATFORM_SPEC='%s'" % (os_name, bits, version_info,
                                        platform_spec))

    os_dist_name, os_dist_version = get_os_dist_info()
    if os_dist_name:
        dist_info = "(%s %s)" % (os_dist_name, os_dist_version)
    else:
        dist_info = ""
    log_info("Running install for %s %sbit %s to "
             "mongoDBInstallationsDirectory (%s)..." % (os_name, bits,
                                                        dist_info,
                                                        mongodb_installs_dir))

    mongo_installation = get_mongo_installation(version_info)

    if mongo_installation is not None: # no-op
        log_info("You already have MongoDB %s installed ('%s'). "
                 "Nothing to do." % (version_info, mongo_installation))
        return mongo_installation

    url = get_download_url(os_name, platform_spec, os_dist_name,
                           os_dist_version, version_info)


    archive_name = url.split("/")[-1]
    # Validate if the version exists
    response = urllib.urlopen(url)

    if response.getcode() != 200:
        msg = ("Unable to download from url '%s' (response code '%s'). "
               "It could be that version '%s' you specified does not exist."
               " Please double check the version you provide" %
               (url, response.getcode(), version_info))
        raise MongoctlException(msg)

    mongo_dir_name = archive_name.replace(".tgz", "")
    install_dir = os.path.join(mongodb_installs_dir, mongo_dir_name)

    ensure_dir(mongodb_installs_dir)

    # XXX LOOK OUT! Two processes installing same version simultaneously => BAD.
    # TODO: mutex to protect the following

    if not dir_exists(install_dir):
        try:
            ## download the url
            download(url)
            extract_archive(archive_name)

            log_info("Moving extracted folder to %s" % mongodb_installs_dir)
            shutil.move(mongo_dir_name, mongodb_installs_dir)

            os.remove(archive_name)
            log_info("Deleting archive %s" % archive_name)

            log_info("MongoDB %s installed successfully!" % version_info)
            return install_dir
        except Exception, e:
            log_exception(e)
            log_error("Failed to install MongoDB '%s'. Cause: %s" %
                      (version_info, e))

###############################################################################
# uninstall_mongodb
###############################################################################
def uninstall_mongodb(version_number, edition=None):

    version_info = make_version_info(version_number, edition=edition)
    # validate version string
    if not is_valid_version_info(version_info):
        raise MongoctlException("Invalid version '%s'. Please provide a"
                                " valid MongoDB version." % version_info)

    mongo_installation = get_mongo_installation(version_info)

    if mongo_installation is None: # no-op
        msg = ("Cannot find a MongoDB installation for version '%s'. Please"
               " use list-versions to see all possible versions " %
               version_info)
        log_info(msg)
        return

    log_info("Found MongoDB '%s' in '%s'" % (version_info, mongo_installation))

    def rm_mongodb():
        log_info("Deleting '%s'" % mongo_installation)
        shutil.rmtree(mongo_installation)
        log_info("MongoDB '%s' Uninstalled successfully!" % version_info)

    prompt_execute_task("Proceed uninstall?" , rm_mongodb)

###############################################################################
def fetch_latest_stable_version():
    response = urllib.urlopen(LATEST_VERSION_FILE_URL)
    if response.getcode() == 200:
        return response.read().strip()
    else:
        raise MongoctlException("Unable to fetch MongoDB latest stable version"
                                " from '%s' (Response code %s)" %
                                (LATEST_VERSION_FILE_URL, response.getcode()))

###############################################################################
def get_mongo_installation(version_info):
    # get all mongod installation dirs and return the one
    # whose version == specified version. If any...
    for install_dir, install_version in find__all_mongo_installations():
        if install_version == version_info:
            return install_dir

    return None

###############################################################################
def find__all_mongo_installations():
    all_installs = []
    all_mongod_exes = find_all_executables('mongod')
    for exe_path, exe_version in all_mongod_exes:
        # install dir is exe parent's (bin) parent
        install_dir = os.path.dirname(os.path.dirname(exe_path))
        all_installs.append((install_dir,exe_version))

    return all_installs

###############################################################################
def get_validate_platform_spec(os_name, bits):

    if os_name not in ["linux", "osx", "win32", "sunos5"]:
        raise MongoctlException("Unsupported OS %s" % os_name)

    if bits == "64":
        return "%s-x86_64" % os_name
    else:
        if os_name == "linux":
            return "linux-i686"
        elif os_name in ["osx" , "win32"]:
            return "%s-i386" % os_name
        elif os_name == "sunos5":
            return "i86pc"

###############################################################################
def download(url):
    log_info("Downloading %s..." % url)

    if which("curl"):
        download_cmd = ['curl', '-O']
        if not is_interactive_mode():
            download_cmd.append('-Ss')
    elif which("wget"):
        download_cmd = ['wget']
    else:
        msg = ("Cannot download file.You need to have 'curl' or 'wget"
               "' command in your path in order to proceed.")
        raise MongoctlException(msg)

    download_cmd.append(url)
    call_command(download_cmd)

###############################################################################
def extract_archive(archive_name):
    log_info("Extracting %s..." % archive_name)
    if not which("tar"):
        msg = ("Cannot extract archive.You need to have 'tar' command in your"
               " path in order to proceed.")
        raise MongoctlException(msg)

    tar_cmd = ['tar', 'xvf', archive_name]
    call_command(tar_cmd)

###############################################################################
def get_os_dist_info():
    """
        Returns true if the current os supports fsfreeze that is os running
        Ubuntu 12.04 or later and there is an fsfreeze exe in PATH
    """

    distribution = platform.dist()
    dist_name = distribution[0].lower()
    dist_version_str = distribution[1]
    if dist_name and dist_version_str:
        return dist_name, dist_version_str
    else:
        return None, None

###############################################################################
def get_download_url(os_name, platform_spec, os_dist_name, os_dist_version,
                     version_info):

    mongo_version = version_info.version_number
    edition = version_info.edition
    if edition == EDITION_COMMUNITY:
        archive_name = "mongodb-%s-%s.tgz" % (platform_spec, mongo_version)
        domain = "fastdl.mongodb.org"
    elif edition == EDITION_ENTERPRISE:
        archive_name = ("mongodb-%s-subscription-%s%s-%s.tgz" %
                        (platform_spec, os_dist_name,
                         os_dist_version.replace('.', ''),
                         mongo_version))
        domain = "downloads.mongodb.com"
    else:
        raise MongoctlException("Unknown mongodb edition '%s'" % edition)

    return "http://%s/%s/%s" % (domain, os_name, archive_name)



########NEW FILE########
__FILENAME__ = print_uri
__author__ = 'abdul'

import mongoctl.repository as repository
from mongoctl.errors import MongoctlException
###############################################################################
# print uri command
###############################################################################
def print_uri_command(parsed_options):
    id = parsed_options.id
    db = parsed_options.db
    # check if the id is a server id

    server = repository.lookup_server(id)
    if server:
        print server.get_mongo_uri_template(db=db)
    else:
        cluster = repository.lookup_cluster(id)
        if cluster:
            print cluster.get_mongo_uri_template(db=db)
        else:
            raise MongoctlException("Cannot find a server or a cluster with"
                                    " id '%s'." % id)


########NEW FILE########
__FILENAME__ = list_servers
__author__ = 'abdul'

import mongoctl.repository as repository
from mongoctl.mongoctl_logging import log_info
from mongoctl.utils import to_string
###############################################################################
# list servers command
###############################################################################
def list_servers_command(parsed_options):
    servers = repository.lookup_all_servers()
    if not servers or len(servers) < 1:
        log_info("No servers have been configured.")
        return

    servers = sorted(servers, key=lambda s: s.id)
    bar = "-"*80
    print bar
    formatter = "%-25s %-40s %s"
    print formatter % ("_ID", "DESCRIPTION", "CONNECT TO")
    print bar


    for server in servers:
        print formatter % (server.id,
                           to_string(server.get_description()),
                           to_string(server.get_address_display()))
    print "\n"



########NEW FILE########
__FILENAME__ = restart
__author__ = 'abdul'

import mongoctl.repository as repository

from mongoctl.mongoctl_logging import log_info
from start import extract_server_options, do_start_server
from stop import do_stop_server

###############################################################################
# restart command
###############################################################################
def restart_command(parsed_options):
    server_id = parsed_options.server
    server = repository.lookup_and_validate_server(server_id)

    options_override = extract_server_options(server, parsed_options)

    restart_server(parsed_options.server, options_override)


###############################################################################
# restart server
###############################################################################
def restart_server(server_id, options_override=None):
    server = repository.lookup_and_validate_server(server_id)
    do_restart_server(server, options_override)

###############################################################################
def do_restart_server(server, options_override=None):
    log_info("Restarting server '%s'..." % server.id)

    if server.is_online():
        do_stop_server(server)
    else:
        log_info("Server '%s' is not running." % server.id)

    do_start_server(server, options_override)

########NEW FILE########
__FILENAME__ = resync_secondary
__author__ = 'abdul'

import mongoctl.repository as repository
import shutil

from mongoctl.mongoctl_logging import log_info
from mongoctl.errors import MongoctlException
from stop import do_stop_server
from start import do_start_server

###############################################################################
# re-sync secondary command
###############################################################################
def resync_secondary_command(parsed_options):
    resync_secondary(parsed_options.server)

###############################################################################
def resync_secondary(server_id):

    server = repository.lookup_and_validate_server(server_id)
    server.validate_local_op("resync-secondary")

    log_info("Checking if server '%s' is secondary..." % server_id)
    # get the server status
    status = server.get_status(admin=True)
    if not status['connection']:
        msg = ("Server '%s' does not seem to be running. For more details,"
               " run 'mongoctl status %s'" % (server_id, server_id))
        raise MongoctlException(msg)
    elif 'error' in status:
        msg = ("There was an error while connecting to server '%s' (error:%s)."
               " For more details, run 'mongoctl status %s'" %
               (server_id, status['error'], server_id))
        raise MongoctlException(msg)

    rs_state = None
    if 'selfReplicaSetStatusSummary' in status:
        rs_state = status['selfReplicaSetStatusSummary']['stateStr']

    if rs_state not in ['SECONDARY', 'RECOVERING']:
        msg = ("Server '%s' is not a secondary member or cannot be determined"
               " as secondary (stateStr='%s'. For more details, run 'mongoctl"
               " status %s'" % (server_id, rs_state, server_id))
        raise MongoctlException(msg)

    do_stop_server(server)

    log_info("Deleting server's '%s' dbpath '%s'..." %
             (server_id, server.get_db_path()))

    shutil.rmtree(server.get_db_path())

    do_start_server(server)

########NEW FILE########
__FILENAME__ = show
__author__ = 'abdul'

import mongoctl.repository as repository
from mongoctl.mongoctl_logging import log_info

from mongoctl.errors import MongoctlException

###############################################################################
# show server command
###############################################################################
def show_server_command(parsed_options):
    server = repository.lookup_server(parsed_options.server)
    if server is None:
        raise MongoctlException("Could not find server '%s'." %
                                parsed_options.server)
    log_info("Configuration for server '%s':" % parsed_options.server)
    print server


########NEW FILE########
__FILENAME__ = start
__author__ = 'abdul'

import os
import stat
import subprocess
import re
import signal
import resource

import mongoctl.repository as repository

from mongoctl.commands.command_utils import (
    options_to_command_args, extract_mongo_exe_options
)

from mongoctl.mongoctl_logging import *
from mongoctl.errors import MongoctlException
from mongoctl import users
from mongoctl.processes import(
    communicate_to_child_process, create_subprocess, get_child_processes
    )
from mongoctl.prompt import prompt_execute_task
from mongoctl.utils import (
    ensure_dir, which, wait_for, dir_exists, is_pid_alive
)
from tail_log import tail_server_log, stop_tailing
from mongoctl.commands.command_utils import (
    get_mongo_executable, VERSION_PREF_EXACT
    )

from mongoctl.prompt import prompt_confirm

from mongoctl.objects.mongod import MongodServer
from mongoctl.objects.mongos import MongosServer

###############################################################################
# CONSTS
###############################################################################
# OS resource limits to impose on the 'mongod' process (see setrlimit(2))
PROCESS_LIMITS = [
    # Many TCP/IP connections to mongod ==> many threads to handle them ==>
    # RAM footprint of many stacks.  Ergo, limit the stack size per thread:
    ('RLIMIT_STACK', "stack size (in bytes)", 1024 * 1024),
    # Speaking of connections, we'd like to be able to have a lot of them:
    ('RLIMIT_NOFILE', "number of file descriptors", 65536)
]

###############################################################################
# start command
###############################################################################

def start_command(parsed_options):
    server_id = parsed_options.server
    server = repository.lookup_and_validate_server(server_id)
    options_override = extract_server_options(server, parsed_options)

    rs_add = parsed_options.rsAdd or parsed_options.rsAddNoInit
    if parsed_options.dryRun:
        dry_run_start_server_cmd(server, options_override)
    else:
        start_server(server,
                     options_override=options_override,
                     rs_add=rs_add,
                     no_init=parsed_options.rsAddNoInit)



###############################################################################
def extract_server_options(server, parsed_args):
    if isinstance(server, MongodServer):
        return extract_mongo_exe_options(parsed_args, SUPPORTED_MONGOD_OPTIONS)
    elif isinstance(server, MongosServer):
        return extract_mongo_exe_options(parsed_args, SUPPORTED_MONGOS_OPTIONS)


###############################################################################
def dry_run_start_server_cmd(server, options_override=None):
    # ensure that the start was issued locally. Fail otherwise
    server.validate_local_op("start")

    log_info("************ Dry Run ************\n")

    start_cmd = generate_start_command(server, options_override)
    start_cmd_str = " ".join(start_cmd)

    log_info("\nCommand:")
    log_info("%s\n" % start_cmd_str)



###############################################################################
# start server
###############################################################################
def start_server(server, options_override=None, rs_add=False, no_init=False):
    do_start_server(server,
                    options_override=options_override,
                    rs_add=rs_add,
                    no_init=no_init)

###############################################################################
__mongod_pid__ = None
__current_server__ = None

###############################################################################
def do_start_server(server, options_override=None, rs_add=False, no_init=False):
    # ensure that the start was issued locally. Fail otherwise
    server.validate_local_op("start")

    log_info("Checking to see if server '%s' is already running"
             " before starting it..." % server.id)
    status = server.get_status()
    if status['connection']:
        log_info("Server '%s' is already running." %
                 server.id)
        return
    elif "timedOut" in status:
        raise MongoctlException("Unable to start server: Server '%s' seems to"
                                " be already started but is"
                                " not responding (connection timeout)."
                                " Or there might some server running on the"
                                " same port %s" %
                                (server.id, server.get_port()))
    # check if there is another process running on the same port
    elif "error" in status and ("closed" in status["error"] or
                                        "reset" in status["error"] or
                                        "ids don't match" in status["error"]):
        raise MongoctlException("Unable to start server: Either server '%s' is "
                                "started but not responding or port %s is "
                                "already in use." %
                                (server.id, server.get_port()))

    # do necessary work before starting the mongod process
    _pre_server_start(server, options_override=options_override)

    server.log_server_activity("start")

    server_pid = start_server_process(server, options_override)

    _post_server_start(server, server_pid, rs_add=rs_add, no_init=no_init)

    # Note: The following block has to be the last block
    # because server_process.communicate() will not return unless you
    # interrupt the server process which will kill mongoctl, so nothing after
    # this block will be executed. Almost never...

    if not server.is_fork():
        communicate_to_child_process(server_pid)

###############################################################################
def _pre_server_start(server, options_override=None):
    if isinstance(server, MongodServer):
        _pre_mongod_server_start(server, options_override=options_override)

###############################################################################
def _pre_mongod_server_start(server, options_override=None):
    """
    Does necessary work before starting a server

    1- An efficiency step for arbiters running with --no-journal
        * there is a lock file ==>
        * server must not have exited cleanly from last run, and does not know
          how to auto-recover (as a journalled server would)
        * however:  this is an arbiter, therefore
        * there is no need to repair data files in any way ==>
        * i can rm this lockfile and start my server
    """

    lock_file_path = server.get_lock_file_path()

    no_journal = (server.get_cmd_option("nojournal") or
                  (options_override and "nojournal" in options_override))
    if (os.path.exists(lock_file_path) and
            server.is_arbiter_server() and
            no_journal):

        log_warning("WARNING: Detected a lock file ('%s') for your server '%s'"
                    " ; since this server is an arbiter, there is no need for"
                    " repair or other action. Deleting mongod.lock and"
                    " proceeding..." % (lock_file_path, server.id))
        try:
            os.remove(lock_file_path)
        except Exception, e:
            log_exception(e)
            raise MongoctlException("Error while trying to delete '%s'. "
                                    "Cause: %s" % (lock_file_path, e))


###############################################################################
def _post_server_start(server, server_pid, **kwargs):
    if isinstance(server, MongodServer):
        _post_mongod_server_start(server, server_pid, **kwargs)

###############################################################################
def _post_mongod_server_start(server, server_pid, **kwargs):
    try:

        # prepare the server
        prepare_mongod_server(server)
        maybe_config_server_repl_set(server, rs_add=kwargs.get("rs_add"),
                                     no_init=kwargs.get("no_init"))
    except Exception, e:
        log_exception(e)
        log_error("Unable to fully prepare server '%s'. Cause: %s \n"
                  "Stop server now if more preparation is desired..." %
                  (server.id, e))
        shall_we_terminate(server_pid)
        exit(1)

###############################################################################
def prepare_mongod_server(server):
    """
     Contains post start server operations
    """
    log_info("Preparing server '%s' for use as configured..." %
             server.id)

    # setup the local users if server supports that
    if users.server_supports_local_users(server):
        users.setup_server_local_users(server)

    if not server.is_cluster_member() or server.is_config_server():
        users.setup_server_users(server)

###############################################################################
def shall_we_terminate(mongod_pid):
    def killit():
        utils.kill_process(mongod_pid, force=True)
        log_info("Server process terminated at operator behest.")

    (condemned, _) = prompt_execute_task("Kill server now?", killit)
    return condemned

###############################################################################
def maybe_config_server_repl_set(server, rs_add=False, no_init=False):
    # if the server belongs to a replica set cluster,
    # then prompt the user to init the replica set IF not already initialized
    # AND server is NOT an Arbiter
    # OTHERWISE prompt to add server to replica if server is not added yet

    cluster = server.get_replicaset_cluster()

    if cluster is not None:
        log_verbose("Server '%s' is a member in the configuration for"
                    " cluster '%s'." % (server.id,cluster.id))

        if not cluster.is_replicaset_initialized():
            log_info("Replica set cluster '%s' has not been initialized yet." %
                     cluster.id)
            if cluster.get_member_for(server).can_become_primary():
                if not no_init:
                    if rs_add:
                        cluster.initialize_replicaset(server)
                    else:
                        prompt_init_replica_cluster(cluster, server)
                else:
                    log_warning("Replicaset is not initialized and you "
                                "specified --rs-add-nonit. Not adding to "
                                "replicaset...")
            else:
                log_info("Skipping replica set initialization because "
                         "server '%s' cannot be elected primary." %
                         server.id)
        else:
            log_verbose("No need to initialize cluster '%s', as it has"
                        " already been initialized." % cluster.id)
            if not cluster.is_member_configured_for(server):
                if rs_add:
                    cluster.add_member_to_replica(server)
                else:
                    prompt_add_member_to_replica(cluster, server)
            else:
                log_verbose("Server '%s' is already added to the replicaset"
                            " conf of cluster '%s'." %
                            (server.id, cluster.id))


###############################################################################
def prompt_init_replica_cluster(replica_cluster,
                                suggested_primary_server):

    prompt = ("Do you want to initialize replica set cluster '%s' using "
              "server '%s'?" %
              (replica_cluster.id, suggested_primary_server.id))

    def init_repl_func():
        replica_cluster.initialize_replicaset(suggested_primary_server)
    prompt_execute_task(prompt, init_repl_func)


###############################################################################
def prompt_add_member_to_replica(replica_cluster, server):

    prompt = ("Do you want to add server '%s' to replica set cluster '%s'?" %
              (server.id, replica_cluster.id))

    def add_member_func():
        replica_cluster.add_member_to_replica(server)
    prompt_execute_task(prompt, add_member_func)

###############################################################################
def _start_server_process_4real(server, options_override=None):
    mk_server_home_dir(server)
    # if the pid file is not created yet then this is the first time this
    # server is started (or at least by mongoctl)

    first_time = os.path.exists(server.get_pid_file_path())

    # generate key file if needed
    if server.needs_repl_key():
        get_generate_key_file(server)

    # create the start command line
    start_cmd = generate_start_command(server, options_override)

    start_cmd_str = " ".join(start_cmd)
    first_time_msg = " for the first time" if first_time else ""

    log_info("Starting server '%s'%s..." % (server.id, first_time_msg))
    log_info("\nExecuting command:\n%s\n" % start_cmd_str)

    child_process_out = None
    if server.is_fork():
        child_process_out = subprocess.PIPE

    global __mongod_pid__
    global __current_server__

    parent_mongod = create_subprocess(start_cmd,
                                      stdout=child_process_out,
                                      preexec_fn=server_process_preexec)



    if server.is_fork():
        __mongod_pid__ = get_forked_mongod_pid(parent_mongod)
    else:
        __mongod_pid__ = parent_mongod.pid

    __current_server__ = server
    return __mongod_pid__

###############################################################################
def get_forked_mongod_pid(parent_mongod):
    output = parent_mongod.communicate()[0]
    pid_re_expr = "forked process: ([0-9]+)"
    pid_str = re.search(pid_re_expr, output).groups()[0]

    return int(pid_str)

###############################################################################
def start_server_process(server,options_override=None):

    mongod_pid = _start_server_process_4real(server, options_override)

    log_info("Will now wait for server '%s' to start up."
             " Enjoy mongod's log for now!" %
             server.id)
    log_info("\n****************************************************************"
             "***************")
    log_info("* START: tail of log file at '%s'" % server.get_log_file_path())
    log_info("******************************************************************"
             "*************\n")

    log_tailer = tail_server_log(server)
    # wait until the server starts
    try:
        is_online = wait_for(server_started_predicate(server, mongod_pid),
                             timeout=300)
    finally:
        # stop tailing
        stop_tailing(log_tailer)

    log_info("\n****************************************************************"
             "***************")
    log_info("* END: tail of log file at '%s'" % server.get_log_file_path())
    log_info("******************************************************************"
             "*************\n")

    if not is_online:
        raise MongoctlException("Timed out waiting for server '%s' to start. "
                                "Please tail the log file to monitor further "
                                "progress." %
                                server.id)

    log_info("Server '%s' started successfully! (pid=%s)\n" %
             (server.id, mongod_pid))

    return mongod_pid

###############################################################################
def server_process_preexec():
    """ make the server ignore ctrl+c signals and have the global mongoctl
        signal handler take care of it
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    _set_process_limits()

###############################################################################
def _set_process_limits():
    for (res_name, description, desired_limit) in PROCESS_LIMITS :
        _set_a_process_limit(res_name, desired_limit, description)

###############################################################################
def _set_a_process_limit(resource_name, desired_limit, description):
    which_resource = getattr(resource, resource_name)
    (soft, hard) = resource.getrlimit(which_resource)
    def set_resource(attempted_value):
        log_verbose("Trying setrlimit(resource.%s, (%d, %d))" %
                    (resource_name, attempted_value, hard))
        resource.setrlimit(which_resource, (attempted_value, hard))

    log_info("Setting OS limit on %s for process (desire up to %d)..."
             "\n\t Current limit values: soft = %d, hard = %d" %
             (description, desired_limit, soft, hard))

    _negotiate_process_limit(set_resource, desired_limit, soft, hard)
    log_info("Resulting OS limit on %s for process: " % description +
             "soft = %d, hard = %d" % resource.getrlimit(which_resource))

###############################################################################
def _rlimit_min(one_val, nother_val):
    """Returns the more stringent rlimit value.  -1 means no limit."""
    if one_val < 0 or nother_val < 0 :
        return max(one_val, nother_val)
    else:
        return min(one_val, nother_val)

###############################################################################
def _negotiate_process_limit(set_resource, desired_limit, soft, hard):

    best_possible = _rlimit_min(hard, desired_limit)
    worst_possible = soft
    attempt = best_possible           # be optimistic for initial attempt

    while abs(best_possible - worst_possible) > 1 :
        try:
            set_resource(attempt)
            log_verbose("  That worked!  Should I negotiate further?")
            worst_possible = attempt
        except:
            log_verbose("  Phooey.  That didn't work.")
            if attempt < 0 :
                log_info("\tCannot remove soft limit on resource.")
                return
            best_possible = attempt + (1 if best_possible < attempt else -1)

        attempt = (best_possible + worst_possible) / 2



###############################################################################
# MONGOD Start Command functions
###############################################################################
def generate_start_command(server, options_override=None):
    """
        Check if we need to use numactl if we are running on a NUMA box.
        10gen recommends using numactl on NUMA. For more info, see
        http://www.mongodb.org/display/DOCS/NUMA
        """
    command = []

    if mongod_needs_numactl():
        log_info("Running on a NUMA machine...")
        command = apply_numactl(command)

    # append the mongod executable
    command.append(get_server_executable(server))

    # create the command args
    cmd_options = server.export_cmd_options(options_override=options_override)

    command.extend(options_to_command_args(cmd_options))
    return command


###############################################################################
def server_stopped_predicate(server, pid):
    def server_stopped():
        return (not server.is_online() and
                (pid is None or not is_pid_alive(pid)))

    return server_stopped

###############################################################################
def server_started_predicate(server, mongod_pid):
    def server_started():
        # check if the command failed
        if not is_pid_alive(mongod_pid):
            raise MongoctlException("Could not start the server. Please check"
                                    " the log file.")

        return server.is_online()

    return server_started

###############################################################################
# NUMA Related functions
###############################################################################
def mongod_needs_numactl():
    """ Logic kind of copied from MongoDB (mongodb-src/util/version.cpp) ;)

        Return true IF we are on a box with a NUMA enabled kernel and more
        than 1 numa node (they start at node0).
    """
    return dir_exists("/sys/devices/system/node/node1")

###############################################################################
def apply_numactl(command):

    numactl_exe = get_numactl_exe()

    if numactl_exe:
        log_info("Using numactl '%s'" % numactl_exe)
        return [numactl_exe, "--interleave=all"] + command
    else:
        msg = ("You are running on a NUMA machine. It is recommended to run "
               "your server using numactl but we cannot find a numactl "
               "executable in your PATH. Proceeding might cause problems that"
               " will manifest in strange ways, such as massive slow downs for"
               " periods of time or high system cpu time. Proceed?")
        if not prompt_confirm(msg):
            exit(0)

###############################################################################
def get_numactl_exe():
    return which("numactl")


###############################################################################
def mk_server_home_dir(server):
    # ensure server home dir exists if it has one
    server_dir = server.get_server_home()

    if not server_dir:
        return

    log_verbose("Ensuring that server's home dir '%s' exists..." % server_dir)
    if ensure_dir(server_dir):
        log_verbose("server home dir %s already exists!" % server_dir)
    else:
        log_verbose("server home dir '%s' created successfully" % server_dir)

###############################################################################
def get_generate_key_file(server):
    cluster = server.get_cluster()
    key_file_path = server.get_key_file() or server.get_default_key_file_path()

    # Generate the key file if it does not exist
    if not os.path.exists(key_file_path):
        key_file = open(key_file_path, 'w')
        key_file.write(cluster.get_repl_key())
        key_file.close()
        # set the permissions required by mongod
        os.chmod(key_file_path,stat.S_IRUSR)
    return key_file_path

###############################################################################
def get_server_executable(server):
    if isinstance(server, MongodServer):
        return get_mongod_executable(server)
    elif isinstance(server, MongosServer):
        return get_mongos_executable(server)

###############################################################################
def get_mongod_executable(server):
    mongod_exe = get_mongo_executable(server.get_mongo_version_info(),
                                      'mongod',
                                      version_check_pref=VERSION_PREF_EXACT)
    return mongod_exe.path

###############################################################################
def get_mongos_executable(server):
    mongos_exe = get_mongo_executable(server.get_mongo_version_info(),
                                      'mongos',
                                      version_check_pref=VERSION_PREF_EXACT)
    return mongos_exe.path


###############################################################################
# SIGNAL HANDLER FUNCTIONS
###############################################################################
#TODO Remove this ugly signal handler and use something more elegant
def mongoctl_signal_handler(signal_val, frame):
    global __mongod_pid__

    # otherwise prompt to kill server
    global __current_server__

    def kill_child(child_process):
        try:
            if child_process.poll() is None:
                log_verbose("Killing child process '%s'" % child_process )
                child_process.terminate()
        except Exception, e:
            log_exception(e)
            log_verbose("Unable to kill child process '%s': Cause: %s" %
                        (child_process, e))

    def exit_mongoctl():
        # kill all children then exit
        map(kill_child, get_child_processes())
        exit(0)

        # if there is no mongod server yet then exit
    if __mongod_pid__ is None:
        exit_mongoctl()
    else:
        prompt_execute_task("Kill server '%s'?" % __current_server__.id,
                            exit_mongoctl)

###############################################################################
# Register the global mongoctl signal handler
signal.signal(signal.SIGINT, mongoctl_signal_handler)

###############################################################################
SUPPORTED_MONGOD_OPTIONS = [
    "verbose",
    "quiet",
    "port",
    "bind_ip",
    "maxConns",
    "objcheck",
    "logpath",
    "logappend",
    "pidfilepath",
    "keyFile",
    "nounixsocket",
    "unixSocketPrefix",
    "auth",
    "cpu",
    "dbpath",
    "diaglog",
    "directoryperdb",
    "journal",
    "journalOptions",
    "journalCommitInterval",
    "ipv6",
    "jsonp",
    "noauth",
    "nohttpinterface",
    "nojournal",
    "noprealloc",
    "notablescan",
    "nssize",
    "profile",
    "quota",
    "quotaFiles",
    "rest",
    "repair",
    "repairpath",
    "slowms",
    "smallfiles",
    "syncdelay",
    "sysinfo",
    "upgrade",
    "fastsync",
    "oplogSize",
    "master",
    "slave",
    "source",
    "only",
    "slavedelay",
    "autoresync",
    "replSet",
    "configsvr",
    "shardsvr",
    "noMoveParanoia",
    "setParameter"
]


###############################################################################
SUPPORTED_MONGOS_OPTIONS = [
    "verbose",
    "quiet",
    "port",
    "bind_ip",
    "maxConns",
    "logpath",
    "logappend",
    "pidfilepath",
    "keyFile",
    "nounixsocket",
    "unixSocketPrefix",
    "ipv6",
    "jsonp",
    "nohttpinterface",
    "upgrade",
    "setParameter",
    "syslog",
    "configdb",
    "localThreshold",
    "test",
    "chunkSize",
    "noscripting"
]

########NEW FILE########
__FILENAME__ = stop
__author__ = 'abdul'

from bson.son import SON
from mongoctl.utils import (
    document_pretty_string, wait_for, kill_process, is_pid_alive
)
from mongoctl.mongoctl_logging import *
from mongoctl.errors import MongoctlException

import mongoctl.repository
import mongoctl.objects.server

from start import server_stopped_predicate
from mongoctl.prompt import prompt_execute_task

###############################################################################
# Constants
###############################################################################

MAX_SHUTDOWN_WAIT = 45

###############################################################################
# stop command
###############################################################################
def stop_command(parsed_options):
    stop_server(parsed_options.server, force=parsed_options.forceStop)



###############################################################################
# stop server
###############################################################################
def stop_server(server_id, force=False):
    do_stop_server(mongoctl.repository.lookup_and_validate_server(server_id),
                   force)

###############################################################################
def do_stop_server(server, force=False):
    # ensure that the stop was issued locally. Fail otherwise
    server.validate_local_op("stop")

    log_info("Checking to see if server '%s' is actually running before"
             " stopping it..." % server.id)

    # init local flags
    can_stop_mongoly = True
    shutdown_success = False

    status = server.get_status()
    if not status['connection']:
        if "timedOut" in status:
            log_info("Unable to issue 'shutdown' command to server '%s'. "
                     "The server is not responding (connection timed out) "
                     "although port %s is open, possibly for mongod." %
                     (server.id, server.get_port()))
            can_stop_mongoly = False
        else:
            log_info("Server '%s' is not running." %
                     server.id)
            return

    pid = server.get_pid()
    pid_disp = pid if pid else "[Cannot be determined]"
    log_info("Stopping server '%s' (pid=%s)..." %
             (server.id, pid_disp))
    # log server activity stop
    server.log_server_activity("stop")
    # TODO: Enable this again when stabilized
    # step_down_if_needed(server, force)

    if can_stop_mongoly:
        log_verbose("  ... issuing db 'shutdown' command ... ")
        shutdown_success = mongo_stop_server(server, pid, force=False)

    if not can_stop_mongoly or not shutdown_success:
        log_verbose("  ... taking more forceful measures ... ")
        shutdown_success = \
            prompt_or_force_stop_server(server, pid, force,
                                        try_mongo_force=can_stop_mongoly)

    if shutdown_success:
        log_info("Server '%s' has stopped." % server.id)
    else:
        raise MongoctlException("Unable to stop server '%s'." %
                                server.id)

###############################################################################
def step_down_if_needed(server, force):
    ## if server is a primary replica member then step down
    if server.is_primary():
        if force:
            step_server_down(server, force)
        else:
            prompt_step_server_down(server, force)

###############################################################################
def mongo_stop_server(server, pid, force=False):

    try:
        shutdown_cmd = SON( [('shutdown', 1),('force', force)])
        log_info("\nSending the following command to %s:\n%s\n" %
                 (server.get_connection_address(),
                  document_pretty_string(shutdown_cmd)))
        server.disconnecting_db_command(shutdown_cmd, "admin")

        log_info("Will now wait for server '%s' to stop." % server.id)
        # Check that the server has stopped
        stop_pred = server_stopped_predicate(server, pid)
        wait_for(stop_pred,timeout=MAX_SHUTDOWN_WAIT)

        if not stop_pred():
            log_error("Shutdown command failed...")
            return False
        else:
            return True
    except Exception, e:
        log_exception(e)
        log_error("Failed to gracefully stop server '%s'. Cause: %s" %
                  (server.id, e))
        return False

###############################################################################
def force_stop_server(server, pid, try_mongo_force=True):
    success = False
    # try mongo force stop if server is still online
    if server.is_online() and try_mongo_force:
        success = mongo_stop_server(server, pid, force=True)

    if not success or not try_mongo_force:
        success = kill_stop_server(server, pid)

    return success

###############################################################################
def kill_stop_server(server, pid):
    if pid is None:
        log_error("Cannot forcibly stop the server because the server's process"
                  " ID cannot be determined; pid file '%s' does not exist." %
                  server.get_pid_file_path())
        return False

    log_info("Forcibly stopping server '%s'...\n" % server.id)
    log_info("Sending kill -1 (HUP) signal to server '%s' (pid=%s)..." %
             (server.id, pid))

    kill_process(pid, force=False)

    log_info("Will now wait for server '%s' (pid=%s) to die." %
             (server.id, pid))
    wait_for(pid_dead_predicate(pid), timeout=MAX_SHUTDOWN_WAIT)

    if is_pid_alive(pid):
        log_error("Failed to kill server process with -1 (HUP).")
        log_info("Sending kill -9 (SIGKILL) signal to server"
                 "'%s' (pid=%s)..." % (server.id, pid))
        kill_process(pid, force=True)

        log_info("Will now wait for server '%s' (pid=%s) to die." %
                 (server.id, pid))
        wait_for(pid_dead_predicate(pid), timeout=MAX_SHUTDOWN_WAIT)

    if not is_pid_alive(pid):
        log_info("Forcefully-stopped server '%s'." % server.id)
        return True
    else:
        log_error("Forceful stop of server '%s' failed." % server.id)
        return False

###############################################################################
def prompt_or_force_stop_server(server, pid,
                                force=False, try_mongo_force=True):
    if force:
        return force_stop_server(server, pid,
                                 try_mongo_force=try_mongo_force)

    def stop_func():
        return force_stop_server(server, pid,
                                 try_mongo_force=try_mongo_force)

    if try_mongo_force:
        result = prompt_execute_task("Issue the shutdown with force command?",
                                     stop_func)
    else:
        result = prompt_execute_task("Forcefully stop the server process?",
                                     stop_func)

    return result[1]


###############################################################################
def step_server_down(server, force=False):
    log_info("Stepping down server '%s'..." % server.id)

    try:
        cmd = SON( [('replSetStepDown', 10),('force', force)])
        server.disconnecting_db_command(cmd, "admin")
        log_info("Server '%s' stepped down successfully!" % server.id)
        return True
    except Exception, e:
        log_exception(e)
        log_error("Failed to step down server '%s'. Cause: %s" %
                  (server.id, e))
        return False

###############################################################################
def prompt_step_server_down(server, force):
    def step_down_func():
        step_server_down(server, force)

    return prompt_execute_task("Server '%s' is a primary server. "
                               "Step it down before proceeding to shutdown?" %
                               server.id,
                               step_down_func)

###############################################################################
def pid_dead_predicate(pid):
    def pid_dead():
        return not is_pid_alive(pid)

    return pid_dead

########NEW FILE########
__FILENAME__ = tail_log
__author__ = 'abdul'

import os

from mongoctl.processes import create_subprocess
from mongoctl.mongoctl_logging import *
from mongoctl import repository
from mongoctl.utils import execute_command

###############################################################################
# tail log command
###############################################################################
def tail_log_command(parsed_options):
    server = repository.lookup_server(parsed_options.server)
    server.validate_local_op("tail-log")
    log_path = server.get_log_file_path()
    # check if log file exists
    if os.path.exists(log_path):
        log_tailer = tail_server_log(server)
        log_tailer.communicate()
    else:
        log_info("Log file '%s' does not exist." % log_path)


###############################################################################
def tail_server_log(server):
    try:
        logpath = server.get_log_file_path()
        # touch log file to make sure it exists
        log_verbose("Touching log file '%s'" % logpath)
        execute_command(["touch", logpath])

        tail_cmd = ["tail", "-f", logpath]
        log_verbose("Executing command: %s" % (" ".join(tail_cmd)))
        return create_subprocess(tail_cmd)
    except Exception, e:
        log_exception(e)
        log_error("Unable to tail server log file. Cause: %s" % e)
        return None

###############################################################################
def stop_tailing(log_tailer):
    try:
        if log_tailer:
            log_verbose("-- Killing tail log path subprocess")
            log_tailer.terminate()
    except Exception, e:
        log_exception(e)
        log_verbose("Failed to kill tail subprocess. Cause: %s" % e)

########NEW FILE########
__FILENAME__ = sharding
__author__ = 'abdul'

import mongoctl.repository as repository
from mongoctl.utils import document_pretty_string
from mongoctl.mongoctl_logging import log_info

from mongoctl.objects.sharded_cluster import ShardedCluster

from mongoctl.errors import MongoctlException



###############################################################################
# configure shard cluster command
###############################################################################
def configure_sharded_cluster_command(parsed_options):
    cluster_id = parsed_options.cluster
    cluster = repository.lookup_and_validate_cluster(cluster_id)

    if not isinstance(cluster, ShardedCluster):
        raise MongoctlException("Cluster '%s' is not a ShardedCluster cluster" %
                                cluster.id)

    if parsed_options.dryRun:
        dry_run_configure_sharded_cluster(cluster)
    else:
        configure_sharded_cluster(cluster)

###############################################################################
# ShardedCluster Methods
###############################################################################

def configure_sharded_cluster(cluster):
    cluster.configure_sharded_cluster()

###############################################################################
def dry_run_configure_sharded_cluster(cluster):

    log_info("\n************ Dry Run ************\n")

    db_command = cluster.get_shardset_configure_command()

    log_info("Executing the following command")
    log_info(document_pretty_string(db_command))

###############################################################################
# Add shard command
###############################################################################
def add_shard_command(parsed_options):
    shard_id = parsed_options.shardId

    # determine if the shard is a replicaset cluster or a server
    shard = repository.lookup_cluster(shard_id)

    if not shard:
        shard = repository.lookup_server(shard_id)

    if not shard:
        raise MongoctlException("Unknown shard '%s'" % shard_id)

    sharded_cluster = repository.lookup_cluster_by_shard(shard)

    if not sharded_cluster:
        raise MongoctlException("'%s' is not a shard" % shard_id)


    if parsed_options.dryRun:
        dry_run_add_shard(shard, sharded_cluster)
    else:
        add_shard(shard, sharded_cluster)


###############################################################################
def add_shard(shard, sharded_cluster):
    sharded_cluster.add_shard(shard)

###############################################################################
def dry_run_add_shard(shard, sharded_cluster):
    log_info("\n************ Dry Run ************\n")

    shard_member = sharded_cluster.get_shard_member(shard)
    db_command = sharded_cluster.get_add_shard_command(shard_member)

    log_info("Executing the following command")
    log_info(document_pretty_string(db_command))



###############################################################################
# Remove shard command
###############################################################################
def remove_shard_command(parsed_options):
    shard_id = parsed_options.shardId

    # determine if the shard is a replicaset cluster or a server
    shard = repository.lookup_cluster(shard_id)

    if not shard:
        shard = repository.lookup_server(shard_id)

    if not shard:
        raise MongoctlException("Unknown shard '%s'" % shard_id)

    sharded_cluster = repository.lookup_cluster_by_shard(shard)

    if not sharded_cluster:
        raise MongoctlException("'%s' is not a shard" % shard_id)


    dest = getattr(parsed_options, "unshardedDataDestination")
    synchronized = getattr(parsed_options, "synchronized")

    if parsed_options.dryRun:
        dry_run_remove_shard(shard, sharded_cluster)
    else:
        sharded_cluster.remove_shard(shard,
                                      unsharded_data_dest_id=dest,
                                      synchronized=synchronized)



###############################################################################
def dry_run_remove_shard(shard, sharded_cluster):
    log_info("\n************ Dry Run ************\n")

    shard_member = sharded_cluster.get_shard_member(shard)
    db_command = sharded_cluster.get_validate_remove_shard_command(
        shard_member)

    log_info("Executing the following command")
    log_info(document_pretty_string(db_command))
########NEW FILE########
__FILENAME__ = config
__author__ = 'abdul'

import json
import urllib
import mongoctl_globals

from utils import *

from minify_json import minify_json
from errors import MongoctlException

from bson import json_util

###############################################################################
# CONSTS
###############################################################################
MONGOCTL_CONF_FILE_NAME = "mongoctl.config"


###############################################################################
# Config root / files stuff
###############################################################################
__config_root__ = mongoctl_globals.DEFAULT_CONF_ROOT

def _set_config_root(root_path):
    if not is_url(root_path) and not dir_exists(root_path):
        raise MongoctlException("Invalid config-root value: %s does not"
                                " exist or is not a directory" % root_path)
    global __config_root__
    __config_root__ = root_path


###############################################################################
# Configuration Functions
###############################################################################

def get_mongoctl_config_val(key, default=None):
    return get_mongoctl_config().get(key, default)

###############################################################################
def set_mongoctl_config_val(key, value):
    get_mongoctl_config()[key] = value

###############################################################################
def get_database_repository_conf():
    return get_mongoctl_config_val('databaseRepository')

###############################################################################
def get_file_repository_conf():
    return get_mongoctl_config_val('fileRepository')

###############################################################################
def get_mongodb_installs_dir():
    installs_dir = get_mongoctl_config_val('mongoDBInstallationsDirectory')
    if installs_dir:
        return resolve_path(installs_dir)

###############################################################################
def set_mongodb_installs_dir(installs_dir):
    set_mongoctl_config_val('mongoDBInstallationsDirectory', installs_dir)

###############################################################################

def get_default_users():
    return get_mongoctl_config_val('defaultUsers', {})

###############################################################################
def get_cluster_member_alt_address_mapping():
    return get_mongoctl_config_val('clusterMemberAltAddressesMapping', {})


###############################################################################
def to_full_config_path(path_or_url):
    global __config_root__


    # handle abs paths and abs URLS
    if os.path.isabs(path_or_url):
        return resolve_path(path_or_url)
    elif is_url(path_or_url):
        return path_or_url
    else:
        result =  os.path.join(__config_root__, path_or_url)
        if not is_url(__config_root__):
            result = resolve_path(result)

        return result

###############################################################################
## Global variable CONFIG: a dictionary of configurations read from config file
__mongo_config__ = None

def get_mongoctl_config():

    global __mongo_config__

    if __mongo_config__ is None:
        __mongo_config__ = read_config_json("mongoctl",
                                            MONGOCTL_CONF_FILE_NAME)

    return __mongo_config__


###############################################################################
def read_config_json(name, path_or_url):

    try:
        log_verbose("Reading %s configuration"
                    " from '%s'..." % (name, path_or_url))

        json_str = read_json_string(path_or_url)
        # minify the json/remove comments and sh*t
        json_str = minify_json.json_minify(json_str)
        json_val =json.loads(json_str,
                             object_hook=json_util.object_hook)

        if not json_val and not isinstance(json_val,list): # b/c [] is not True
            raise MongoctlException("Unable to load %s "
                                    "config file: %s" % (name, path_or_url))
        else:
            return json_val
    except MongoctlException,e:
        raise e
    except Exception, e:
        raise MongoctlException("Unable to load %s "
                                "config file: %s: %s" % (name, path_or_url, e))

###############################################################################
def read_json_string(path_or_url, validate_exists=True):
    path_or_url = to_full_config_path(path_or_url)
    # if the path is just filename then append config root

    # check if its a file
    if not is_url(path_or_url):
        if os.path.isfile(path_or_url):
            return open(path_or_url).read()
        elif validate_exists:
            raise MongoctlException("Config file %s does not exist." %
                                    path_or_url)
        else:
            return None

    # Then its url
    response = urllib.urlopen(path_or_url)

    if response.getcode() != 200:
        msg = ("Unable to open url '%s' (response code '%s')."
               % (path_or_url, response.getcode()))

        if validate_exists:
            raise MongoctlException(msg)
        else:
            log_verbose(msg)
            return None
    else:
        return response.read()

########NEW FILE########
__FILENAME__ = errors
__author__ = 'abdul'


###############################################################################
# Mongoctl Exception class
###############################################################################
class MongoctlException(Exception):
    def __init__(self, message, cause=None):
        super(MongoctlException, self).__init__(message)
        self._cause = cause
########NEW FILE########
__FILENAME__ = minify_json
'''
Created on 20/01/2011

v0.1 (C) Gerald Storer
MIT License

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
    
    new_str.append(json[from_index:])
    return ''.join(new_str)

if __name__ == '__main__':
    import json # requires Python 2.6+ to run tests
    
    def test_json(s):
        return json.loads(json_minify(s))
    
    test1 = '''// this is a JSON file with comments
{
    "foo": "bar",    // this is cool
    "bar": [
        "baz", "bum", "zam"
    ],
/* the rest of this document is just fluff
   in case you are interested. */
    "something": 10,
    "else": 20
}

/* NOTE: You can easily strip the whitespace and comments 
   from such a file with the JSON.minify() project hosted 
   here on github at http://github.com/getify/JSON.minify 
*/
'''

    test1_res = '''{"foo":"bar","bar":["baz","bum","zam"],"something":10,"else":20}'''
    
    test2 = '''
{"/*":"*/","//":"",/*"//"*/"/*/"://
"//"}

'''
    test2_res = '''{"/*":"*/","//":"","/*/":"//"}'''
    
    test3 = r'''/*
this is a 
multi line comment */{

"foo"
:
    "bar/*"// something
    ,    "b\"az":/*
something else */"blah"

}
'''
    test3_res = r'''{"foo":"bar/*","b\"az":"blah"}'''
    
    test4 = r'''{"foo": "ba\"r//", "bar\\": "b\\\"a/*z", 
    "baz\\\\": /* yay */ "fo\\\\\"*/o" 
}
'''
    test4_res = r'''{"foo":"ba\"r//","bar\\":"b\\\"a/*z","baz\\\\":"fo\\\\\"*/o"}'''
    
    assert test_json(test1) == json.loads(test1_res),'Failed test 1'
    assert test_json(test2) == json.loads(test2_res),'Failed test 2'
    assert test_json(test3) == json.loads(test3_res),'Failed test 3'
    assert test_json(test4) == json.loads(test4_res),'Failed test 4'
    if __debug__: # Don't print passed message if the asserts didn't run
        print 'Passed all tests'
########NEW FILE########
__FILENAME__ = mongoctl
#!/usr/bin/env python

# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

__author__ = 'abdul'

###############################################################################
# Imports
###############################################################################

import sys
import traceback

import os

import config
import objects.server

from dargparse import dargparse
from mongoctl_logging import (
    log_error, log_info, turn_logging_verbose_on, log_verbose, log_exception
)

from mongoctl_command_config import MONGOCTL_PARSER_DEF
from errors import MongoctlException
from prompt import (
    is_interactive_mode, set_interactive_mode, say_yes_to_everything,
    say_no_to_everything
)

from utils import namespace_get_property
from users import parse_global_login_user_arg

###############################################################################
# Constants
###############################################################################

CONF_ROOT_ENV_VAR = "MONGOCTL_CONF"

SERVER_ID_PARAM = "server"

###############################################################################
# MAIN
###############################################################################
def main(args):
    try:
        do_main(args)
    except MongoctlException,e:
        log_error(e)
        log_exception(e)
        exit(1)
    except Exception, e:
        log_exception(e)
        raise

###############################################################################
def do_main(args):
    header = """
-------------------------------------------------------------------------------------------
  __ _  ___  ___  ___ ____  ____/ /_/ /
 /  ' \/ _ \/ _ \/ _ `/ _ \/ __/ __/ / 
/_/_/_/\___/_//_/\_, /\___/\__/\__/_/  
                /___/ 
-------------------------------------------------------------------------------------------
   """

    # Parse options
    parser = get_mongoctl_cmd_parser()

    if len(args) < 1:
        print(header)
        parser.print_help()
        return

    # Parse the arguments and call the function of the selected cmd
    parsed_args = parser.parse_args(args)

    # turn on verbose if specified
    if namespace_get_property(parsed_args,"mongoctlVerbose"):
        turn_logging_verbose_on()

    # set interactive mode
    non_interactive = namespace_get_property(parsed_args,'noninteractive')
    non_interactive = False if non_interactive is None else non_interactive

    set_interactive_mode(not non_interactive)

    if not is_interactive_mode():
        log_verbose("Running with noninteractive mode")

    # set global prompt value
    yes_all = parsed_args.yesToEverything
    no_all = parsed_args.noToEverything

    if yes_all and no_all:
        raise MongoctlException("Cannot have --yes and --no at the same time. "
                                "Please choose either --yes or --no")
    elif yes_all:
        say_yes_to_everything()
    elif no_all:
        say_no_to_everything()

    # set conf root if specified
    if parsed_args.configRoot is not None:
        config._set_config_root(parsed_args.configRoot)
    elif os.getenv(CONF_ROOT_ENV_VAR) is not None:
        config._set_config_root(os.getenv(CONF_ROOT_ENV_VAR))

    # get the function to call from the parser framework
    command_function = parsed_args.func

    # parse global login if present
    username = namespace_get_property(parsed_args, "username")

    password = namespace_get_property(parsed_args, "password")
    server_id = namespace_get_property(parsed_args, SERVER_ID_PARAM)
    parse_global_login_user_arg(username, password, server_id)

    if server_id is not None:
        # check if assumeLocal was specified
        assume_local = namespace_get_property(parsed_args,"assumeLocal")
        if assume_local:
            objects.server.assume_local_server(server_id)
    # execute command
    log_info("")
    return command_function(parsed_args)

###############################################################################
########################                      #################################
########################  Commandline parsing #################################
########################                      #################################
###############################################################################


###############################################################################
# Mongoctl main parser
###############################################################################


###############################################################################
def get_mongoctl_cmd_parser():
    parser = dargparse.build_parser(MONGOCTL_PARSER_DEF)
    return parser


###############################################################################
########################                   ####################################
########################     BOOTSTRAP     ####################################
########################                   ####################################
###############################################################################

if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (SystemExit, KeyboardInterrupt) , e:
        if e.code == 0:
            pass
        else:
            raise
    except:
        traceback.print_exc()

########NEW FILE########
__FILENAME__ = mongoctl_command_config
#
# The MIT License
#
# Copyright (c) 2012 ObjectLabs Corporation
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

__author__ = 'abdul'

import version

MONGOCTL_PARSER_DEF = {
    "prog": "mongoctl",
    "usage": "Usage: mongoctl [<options>] <command> [<command-args>]",
    "description" : "A utility that simplifies the management of MongoDB servers and replica set clusters.",
    "args": [
        {
            "name": "mongoctlVerbose",
            "type" : "optional",
            "help": "make mongoctl more verbose",
            "cmd_arg": [
                "-v",
                "--verbose"
                ],
            "nargs": 0,
            "action": "store_true",
            "default": False
        },
        {
            "name": "noninteractive",
            "type" : "optional",
            "help": "bypass prompting for user interaction",
            "cmd_arg": [
                "-n",
                "--noninteractive"
                ],
            "nargs": 0,
            "action": "store_true",
            "default": False
        },

        {
            "name": "yesToEverything",
            "type" : "optional",
            "help": "auto yes to all yes/no prompts",
            "cmd_arg": [
                "--yes"
            ],
            "nargs": 0,
            "action": "store_true",
            "default": False
        },

        {
            "name": "noToEverything",
            "type" : "optional",
            "help": "auto no to all yes/no prompts",
            "cmd_arg": [
                "--no"
            ],
            "nargs": 0,
            "action": "store_true",
            "default": False
        },
            {
            "name": "configRoot",
            "type" : "optional",
            "help": "path to mongoctl config root; defaults to ~/.mongoctl",
            "cmd_arg": [
                "--config-root"
            ],
            "nargs": 1
        },

        {
            "name": "version",
            "type" : "optional",
            "cmd_arg":  "--version",
            "nargs": 0,
            "help": "print version",
            "action": "version",
            "version": "mongoctl %s" % version.MONGOCTL_VERSION
        }

    ],

    "child_groups": [
            {
            "name" :"adminCommands",
            "display": "Admin Commands"
        },
            {
            "name" :"clientCommands",
            "display": "Client Commands"
        },
            {
            "name" :"serverCommands",
            "display": "Server Commands"
        },

            {
            "name" :"clusterCommands",
            "display": "Cluster Commands"
        },
            {
            "name" :"miscCommands",
            "display": "Miscellaneous"
        },

        {
            "name" :"shardCommands",
            "display": "Sharding"
        }
    ],

    "children":[

        #### start ####
            {
            "prog": "start",
            "group": "serverCommands",
            #"usage" : generate default usage
            "shortDescription" : "start a server",
            "description" : "Starts a specific server.",
            "function": "mongoctl.commands.server.start.start_command",
            "args":[

                    {
                    "name": "server",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "SERVER_ID",
                    "help": "a valid server id"
                },

                    {
                    "name": "dryRun",
                    "type" : "optional",
                    "cmd_arg":  ["-n" , "--dry-run"],
                    "nargs": 0,
                    "help": "prints the mongod command to execute without "
                            "executing it",
                    "default": False
                },
                    {
                    "name": "assumeLocal",
                    "type" : "optional",
                    "cmd_arg": "--assume-local",
                    "nargs": 0,
                    "help": "Assumes that the server will be started on local"
                            " host. This will skip local address/dns check",
                    "default": False
                },
                    {
                    "name": "rsAdd",
                    "type" : "optional",
                    "cmd_arg": "--rs-add",
                    "nargs": 0,
                    "help": "Automatically add server to replicaset conf if "
                            "its not added yet",
                    "default": False
                },
                {
                    "name": "rsAddNoInit",
                    "type" : "optional",
                    "cmd_arg": "--rs-add-noinit",
                    "nargs": 0,
                    "help": "Automatically add server to an "
                            "initialized replicaset conf if "
                            "its not added yet",
                    "default": False
                },
                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                },

                # mongod supported options
                # confusing
                #                {
                #                    "name": "config",
                #                    "type" : "optional",
                #                    "cmd_arg":  ["-f", "--config"],
                #                    "nargs": 1,
                #                    "help": "configuration file specifying additional options"
                #                },

                    {
                    "name": "verbose",
                    "type" : "optional",
                    "cmd_arg":  ["-v", "--verbose"],
                    "nargs": 0,
                    "help": "be more verbose (include multiple times for more"
                            " verbosity e.g. -vvvvv)"
                },

                    {
                    "name": "quiet",
                    "type" : "optional",
                    "cmd_arg":  "--quiet",
                    "nargs": 0,
                    "help": "quieter output"
                },

                    {
                    "name": "port",
                    "type" : "optional",
                    "cmd_arg":  "--port",
                    "nargs": 1,
                    "help": "specify port number"
                },

                    {
                    "name": "bind_ip",
                    "type" : "optional",
                    "cmd_arg": "--bind_ip",
                    "nargs": 1,
                    "help": "comma separated list of ip addresses to listen "
                            "on- all local ips by default"
                },

                    {
                    "name": "maxConns",
                    "type" : "optional",
                    "cmd_arg":  "--maxConns",
                    "nargs": 1,
                    "help": "max number of simultaneous connections"
                },

                    {
                    "name": "objcheck",
                    "type" : "optional",
                    "cmd_arg":  "--objcheck",
                    "nargs": 0,
                    "help": "inspect client data for validity on receipt"
                },

                    {
                    "name": "logpath",
                    "type" : "optional",
                    "cmd_arg":  "--logpath",
                    "nargs": 1,
                    "help": "log file to send write to instead of stdout -"
                            " has to be a file, not directory. "
                            "mongoctl defaults that to dbpath/mongodb.log"
                },

                    {
                    "name": "logappend",
                    "type" : "optional",
                    "cmd_arg":  "--logappend",
                    "nargs": 1,
                    "help": "append to logpath instead of over-writing"
                },

                    {
                    "name": "pidfilepath",
                    "type" : "optional",
                    "cmd_arg":  "--pidfilepath",
                    "nargs": 1,
                    "help": "full path to pidfile (if not set,"
                            " no pidfile is created). "
                            "mongoctl defaults that to dbpath/pid.txt"
                },

                    {
                    "name": "keyFile",
                    "type" : "optional",
                    "cmd_arg":  "--keyFile",
                    "nargs": 1,
                    "help": "private key for cluster authentication "
                            "(only for replica sets)"
                },

                    {
                    "name": "nounixsocket",
                    "type" : "optional",
                    "cmd_arg":  "--nounixsocket",
                    "nargs": 0,
                    "help": "disable listening on unix sockets"
                },

                    {
                    "name": "unixSocketPrefix",
                    "type" : "optional",
                    "cmd_arg":  "--unixSocketPrefix",
                    "nargs": 1,
                    "help": "alternative directory for UNIX domain sockets "
                            "(defaults to /tmp)"
                },
                    {
                    "name": "auth",
                    "type" : "optional",
                    "cmd_arg":  "--auth",
                    "nargs": 0,
                    "help": "run with security"
                },

                    {
                    "name": "cpu",
                    "type" : "optional",
                    "cmd_arg":  "--cpu",
                    "nargs": 0,
                    "help": "periodically show cpu and iowait utilization"
                },

                    {
                    "name": "dbpath",
                    "type" : "optional",
                    "cmd_arg":  "--dbpath",
                    "nargs": 1,
                    "help": "directory for datafiles"
                },

                    {
                    "name": "diaglog",
                    "type" : "optional",
                    "cmd_arg":  "--diaglog",
                    "nargs": 1,
                    "help": "0=off 1=W 2=R 3=both 7=W+some reads"
                },

                    {
                    "name": "directoryperdb",
                    "type" : "optional",
                    "cmd_arg":  "--directoryperdb",
                    "nargs": 0,
                    "help": "each database will be stored in a"
                            " separate directory"
                },

                    {
                    "name": "journal",
                    "type" : "optional",
                    "cmd_arg":  "--journal",
                    "nargs": 0,
                    "help": "enable journaling"
                },

                    {
                    "name": "journalOptions",
                    "type" : "optional",
                    "cmd_arg":  "--journalOptions",
                    "nargs": 1,
                    "help": "journal diagnostic options"
                },

                    {
                    "name": "journalCommitInterval",
                    "type" : "optional",
                    "cmd_arg":  "--journalCommitInterval",
                    "nargs": 1,
                    "help": "how often to group/batch commit (ms)"
                },

                    {
                    "name": "ipv6",
                    "type" : "optional",
                    "cmd_arg":  "--ipv6",
                    "nargs": 0,
                    "help": "enable IPv6 support (disabled by default)"
                },

                    {
                    "name": "jsonp",
                    "type" : "optional",
                    "cmd_arg":  "--jsonp",
                    "nargs": 0,
                    "help": "allow JSONP access via http "
                            "(has security implications)"
                },

                    {
                    "name": "noauth",
                    "type" : "optional",
                    "cmd_arg":  "--noauth",
                    "nargs": 0,
                    "help": "run without security"
                },

                    {
                    "name": "nohttpinterface",
                    "type" : "optional",
                    "cmd_arg":  "--nohttpinterface",
                    "nargs": 0,
                    "help": "disable http interface"
                },

                    {
                    "name": "nojournal",
                    "type" : "optional",
                    "cmd_arg":  "--nojournal",
                    "nargs": 0,
                    "help": "disable journaling (journaling is on by default "
                            "for 64 bit)"
                },

                    {
                    "name": "noprealloc",
                    "type" : "optional",
                    "cmd_arg":  "--noprealloc",
                    "nargs": 0,
                    "help": "disable data file preallocation - "
                            "will often hurt performance"
                },

                    {
                    "name": "notablescan",
                    "type" : "optional",
                    "cmd_arg":  "--notablescan",
                    "nargs": 0,
                    "help": "do not allow table scans"
                },

                    {
                    "name": "nssize",
                    "type" : "optional",
                    "cmd_arg":  "--nssize",
                    "nargs": 1,
                    "help": ".ns file size (in MB) for new databases"
                },

                    {
                    "name": "profile",
                    "type" : "optional",
                    "cmd_arg":  "--profile",
                    "nargs": 1,
                    "help": "0=off 1=slow, 2=all"
                },

                    {
                    "name": "quota",
                    "type" : "optional",
                    "cmd_arg":  "--quota",
                    "nargs": 0,
                    "help": "limits each database to a certain number"
                            " of files (8 default)"
                },

                    {
                    "name": "quotaFiles",
                    "type" : "optional",
                    "cmd_arg":  "--quotaFiles",
                    "nargs": 1,
                    "help": "number of files allower per db, requires --quota"
                },

                    {
                    "name": "rest",
                    "type" : "optional",
                    "cmd_arg":  "--rest",
                    "nargs": 1,
                    "help": "turn on simple rest api"
                },

                    {
                    "name": "repair",
                    "type" : "optional",
                    "cmd_arg":  "--repair",
                    "nargs": 0,
                    "help": "run repair on all dbs"
                },

                    {
                    "name": "repairpath",
                    "type" : "optional",
                    "cmd_arg":  "--repairpath",
                    "nargs": 1,
                    "help": "root directory for repair files - defaults "
                            "to dbpath"
                },

                    {
                    "name": "slowms",
                    "type" : "optional",
                    "cmd_arg":  "--slowms",
                    "nargs": 1,
                    "help": "value of slow for profile and console log"
                },

                    {
                    "name": "smallfiles",
                    "type" : "optional",
                    "cmd_arg":  "--smallfiles",
                    "nargs": 0,
                    "help": "use a smaller default file size"
                },

                    {
                    "name": "syncdelay",
                    "type" : "optional",
                    "cmd_arg":  "--syncdelay",
                    "nargs": 1,
                    "help": "seconds between disk syncs "
                            "(0=never, but not recommended)"
                },

                    {
                    "name": "sysinfo",
                    "type" : "optional",
                    "cmd_arg":  "--sysinfo",
                    "nargs": 0,
                    "help": "print some diagnostic system information"
                },

                    {
                    "name": "upgrade",
                    "type" : "optional",
                    "cmd_arg":  "--upgrade",
                    "nargs": 0,
                    "help": "upgrade db if needed"
                },

                    {
                    "name": "fastsync",
                    "type" : "optional",
                    "cmd_arg":  "--fastsync",
                    "nargs": 0,
                    "help": "indicate that this instance is starting from "
                            "a dbpath snapshot of the repl peer"
                },

                    {
                    "name": "oplogSize",
                    "type" : "optional",
                    "cmd_arg":  "--oplogSize",
                    "nargs": 1,
                    "help": "size limit (in MB) for op log"
                },

                    {
                    "name": "master",
                    "type" : "optional",
                    "cmd_arg":  "--master",
                    "nargs": 0,
                    "help": "master mode"
                },

                    {
                    "name": "slave",
                    "type" : "optional",
                    "cmd_arg":  "--slave",
                    "nargs": 0,
                    "help": "slave mode"
                },

                    {
                    "name": "source",
                    "type" : "optional",
                    "cmd_arg":  "--source",
                    "nargs": 1,
                    "help": "when slave: specify master as <server:port>"
                },

                    {
                    "name": "only",
                    "type" : "optional",
                    "cmd_arg":  "--only",
                    "nargs": 1,
                    "help": "when slave: specify a single database"
                            " to replicate"
                },

                    {
                    "name": "slavedelay",
                    "type" : "optional",
                    "cmd_arg":  "--slavedelay",
                    "nargs": 1,
                    "help": "specify delay (in seconds) to be used when "
                            "applying master ops to slave"
                },

                    {
                    "name": "autoresync",
                    "type" : "optional",
                    "cmd_arg":  "--autoresync",
                    "nargs": 0,
                    "help": "automatically resync if slave data is stale"
                },

                    {
                    "name": "replSet",
                    "type" : "optional",
                    "cmd_arg":  "--replSet",
                    "nargs": 1,
                    "help": "arg is <setname>[/<optionalseedhostlist>]"
                },

                    {
                    "name": "configsvr",
                    "type" : "optional",
                    "cmd_arg":  "--configsvr",
                    "nargs": 0,
                    "help": "declare this is a config db of a cluster;"
                            " default port 27019; default dir /data/configdb"
                },

                    {
                    "name": "shardsvr",
                    "type" : "optional",
                    "cmd_arg":  "--shardsvr",
                    "nargs": 0,
                    "help": "declare this is a shard db of a cluster;"
                            " default port 27018"
                },

                    {
                    "name": "noMoveParanoia",
                    "type" : "optional",
                    "cmd_arg":  "--noMoveParanoia",
                    "nargs": 0,
                    "help": "turn off paranoid saving of data for moveChunk."
                            " this is on by default for now,"
                            " but default will switch"
                },

                    {
                    "name": "setParameter",
                    "type" : "optional",
                    "cmd_arg":  "--setParameter",
                    "nargs": 1,
                    "help": "Set a configurable parameter"
                }

                ]
        },
        #### stop ####
            {
            "prog": "stop",
            "group": "serverCommands",
            "shortDescription" : "stop a server",
            "description" : "Stops a specific server.",
            "function": "mongoctl.commands.server.stop.stop_command",
            "args":[
                    {   "name": "server",
                        "type" : "positional",
                        "nargs": 1,
                        "displayName": "SERVER_ID",
                        "help": "A valid server id"
                },
                    {   "name": "forceStop",
                        "type": "optional",
                        "cmd_arg": ["-f", "--force"],
                        "nargs": 0,
                        "help": "force stop if needed via kill",
                        "default": False
                },
                    {
                    "name": "assumeLocal",
                    "type" : "optional",
                    "cmd_arg": "--assume-local",
                    "nargs": 0,
                    "help": "Assumes that the server will be stopped on local"
                            " host. This will skip local address/dns check",
                    "default": False
                },
                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                }
            ]
        },
        #### restart ####
            {
            "prog": "restart",
            "group": "serverCommands",
            "shortDescription" : "restart a server",
            "description" : "Restarts a specific server.",
            "function": "mongoctl.commands.server.restart.restart_command",
            "args":[
                    {   "name": "server",
                        "type" : "positional",
                        "nargs": 1,
                        "displayName": "SERVER_ID",
                        "help": "A valid server id"
                },
                    {
                    "name": "assumeLocal",
                    "type" : "optional",
                    "cmd_arg": "--assume-local",
                    "nargs": 0,
                    "help": "Assumes that the server will be stopped on local"
                            " host. This will skip local address/dns check",
                    "default": False
                },

                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                }

            ]
        },
        #### status ####
            {
            "prog": "status",
            "group": "serverCommands",
            "shortDescription" : "retrieve status of server or a cluster",
            "description" : "Retrieves the status of a server or a cluster",
            "function": "mongoctl.commands.common.status.status_command",
            "args":[
                    {   "name": "id",
                        "type" : "positional",
                        "nargs": 1,
                        "displayName": "[SERVER OR CLUSTER ID]",
                        "help": "A valid server or cluster id"
                },
                    {   "name": "statusVerbose",
                        "type" : "optional",
                        "cmd_arg": ["-v", "--verbose"],
                        "nargs": 0,
                        "help": "include more information in status"
                },
                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                }
            ]
        },
        #### list-servers ####
            {
            "prog": "list-servers",
            "group": "serverCommands",
            "shortDescription" : "show list of configured servers",
            "description" : "Show list of configured servers.",
            "function": "mongoctl.commands.server.list_servers.list_servers_command"
        },
        #### show-server ####
            {
            "prog": "show-server",
            "group": "serverCommands",
            "shortDescription" : "show server's configuration",
            "description" : "Shows the configuration for a specific server.",
            "function": "mongoctl.commands.server.show.show_server_command" ,
            "args":[
                    {   "name": "server",
                        "type" : "positional",
                        "nargs": 1,
                        "displayName": "SERVER_ID",
                        "help": "A valid server id"
                }
            ]
        },
        #### connect ####
            {
            "prog": "connect",
            "group": "clientCommands",
            "shortDescription" : "open a mongo shell connection to a server",
            "description" : "Opens a mongo shell connection to the specified database. If a\n"
                            "cluster is specified command will connect to the primary server.\n\n"
                            "<db-address> can be one of:\n"
                            "   (a) a mongodb URI (e.g. mongodb://localhost:27017[/mydb])\n"
                            "   (b) <server-id>[/<db>]\n"
                            "   (c) <cluster-id>[/<db>]\n",
            "function": "mongoctl.commands.common.connect.connect_command",
            "args": [
                    {
                    "name": "dbAddress",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "<db-address>",
                    "help": "database addresses supported by mongoctl."
                            " Check docs for more details."
                },
                    {
                    "name": "jsFiles",
                    "type" : "positional",
                    "nargs": "*",
                    "displayName": "[file names (ending in .js)]",
                    "help": "file names: a list of files to run. files have to"
                            " end in .js and will exit after unless --shell"
                            " is specified"
                },
                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                },

                    {
                    "name": "shell",
                    "type" : "optional",
                    "help": "run the shell after executing files",
                    "cmd_arg": [
                        "--shell"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "norc",
                    "type" : "optional",
                    "help": 'will not run the ".mongorc.js" file on start up',
                    "cmd_arg": [
                        "--norc"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "quiet",
                    "type" : "optional",
                    "help": 'be less chatty',
                    "cmd_arg": [
                        "--quiet"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "eval",
                    "type" : "optional",
                    "help": 'evaluate javascript',
                    "cmd_arg": [
                        "--eval"
                    ],
                    "nargs": 1
                },

                    {
                    "name": "verbose",
                    "type" : "optional",
                    "help": 'increase verbosity',
                    "cmd_arg": [
                        "--verbose"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "ipv6",
                    "type" : "optional",
                    "help": 'enable IPv6 support (disabled by default)',
                    "cmd_arg": [
                        "--ipv6"
                    ],
                    "nargs": 0
                },



            ]
        },
        #### tail-log ####
            {
            "prog": "tail-log",
            "group": "serverCommands",
            "shortDescription" : "tails a server's log file",
            "description" : "Tails server's log file. Works only on local host",
            "function": "mongoctl.commands.server.tail_log.tail_log_command",
            "args": [
                    {
                    "name": "server",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "SERVER_ID",
                    "help": "a valid server id"
                },
                    {
                    "name": "assumeLocal",
                    "type" : "optional",
                    "cmd_arg": "--assume-local",
                    "nargs": 0,
                    "help": "Assumes that the server is running on local"
                            " host. This will skip local address/dns check",
                    "default": False
                }
            ]
        },

        #### dump ####
            {
            "prog": "dump",
            "group": "clientCommands",
            "shortDescription" : "Export MongoDB data to BSON files (using mongodump)",
            "description" : "Runs a mongodump  to the specified database address or dbpath. If a\n"
                            "cluster is specified command will run the dump against "
                            "the primary server.\n\n"
                            "<db-address> can be one of:\n"
                            "   (a) a mongodb URI (e.g. mongodb://localhost:27017[/mydb])\n"
                            "   (b) <server-id>[/<db>]\n"
                            "   (c) <cluster-id>[/<db>]\n",
            "function": "mongoctl.commands.common.dump.dump_command",
            "args": [
                    {
                    "name": "target",
                    "displayName": "TARGET",
                    "type" : "positional",
                    "nargs": 1,
                    "help": "database address or dbpath. Check docs for"
                            " more details."
                },
                    {
                    "name": "useBestSecondary",
                    "type" : "optional",
                    "help": "Only for clusters. Dump from the best secondary "
                            "(passive / least repl lag)",
                    "cmd_arg": [
                        "--use-best-secondary"
                    ],
                    "nargs": 0
                },
                #   {
                #    "name": "maxReplLag",
                #    "type" : "optional",
                #    "help": "Used only with --use-best-secondary. Select "
                #            "members whose repl lag is less than than "
                #            "specified max ",
                #    "cmd_arg": [
                #        "--max-repl-lag"
                #    ],
                #    "nargs": 1
                #},
                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                },

                    {
                    "name": "verbose",
                    "type" : "optional",
                    "help": 'increase verbosity',
                    "cmd_arg": [
                        "-v",
                        "--verbose"
                    ],
                    "nargs": 0
                },
                    {
                    "name": "directoryperdb",
                    "type" : "optional",
                    "help": "if dbpath specified, each db is in a separate directory",
                    "cmd_arg": [
                        "--directoryperdb"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "journal",
                    "type" : "optional",
                    "help": "enable journaling",
                    "cmd_arg": [
                        "--journal"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "collection",
                    "type" : "optional",
                    "displayName": "COLLECTION",
                    "help": "collection to use (some commands)",
                    "cmd_arg": [
                        "-c",
                        "--collection"
                    ],
                    "nargs": 1
                },

                    {
                    "name": "out",
                    "type" : "optional",
                    "displayName": "DIR",
                    "help": "output directory or '-' for stdout",
                    "cmd_arg": [
                        "-o",
                        "--out"
                    ],
                    "nargs": 1
                },

                    {
                    "name": "query",
                    "type" : "optional",
                    "displayName": "QUERY",
                    "help": "json query",
                    "cmd_arg": [
                        "-q",
                        "--query"
                    ],
                    "nargs": 1
                },

                    {
                    "name": "oplog",
                    "type" : "optional",
                    "help": " Use oplog for point-in-time snapshotting",
                    "cmd_arg": [
                        "--oplog"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "repair",
                    "type" : "optional",
                    "help": " try to recover a crashed database",
                    "cmd_arg": [
                        "--repair"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "forceTableScan",
                    "type" : "optional",
                    "help": " force a table scan (do not use $snapshot)",
                    "cmd_arg": [
                        "--forceTableScan"
                    ],
                    "nargs": 0
                },
                    {
                    "name": "ipv6",
                    "type" : "optional",
                    "cmd_arg":  "--ipv6",
                    "nargs": 0,
                    "help": "enable IPv6 support (disabled by default)"
                },
                    {
                    "name": "authenticationDatabase",
                    "type" : "optional",
                    "cmd_arg":  "--authenticationDatabase",
                    "nargs": 1,
                    "help": "user source (defaults to dbname). 2.4.x or greater only."
                },

                    {
                    "name": "dumpDbUsersAndRoles",
                    "type" : "optional",
                    "cmd_arg":  "--dumpDbUsersAndRoles",
                    "nargs": 0,
                    "help": "Dump user and role definitions for the given "
                            "database. 2.6.x or greater only."
                }

            ]
        },

        #### restore ####
            {
            "prog": "restore",
            "group": "clientCommands",
            "shortDescription" : "Restore MongoDB (using mongorestore)",
            "description" : "Runs a mongorestore from specified file or directory"
                            " to database address or dbpath. If a\n"
                            "cluster is specified command will restore against "
                            "the primary server.\n\n"
                            "<db-address> can be one of:\n"
                            "   (a) a mongodb URI (e.g. mongodb://localhost:27017[/mydb])\n"
                            "   (b) <server-id>[/<db>]\n"
                            "   (c) <cluster-id>[/<db>]\n",
            "function": "mongoctl.commands.common.restore.restore_command",
            "args": [
                    {
                    "name": "destination",
                    "displayName": "DESTINATION",
                    "type" : "positional",
                    "nargs": 1,
                    "help": "database address or dbpath. Check docs for"
                            " more details."
                },

                    {
                    "name": "source",
                    "displayName": "SOURCE",
                    "type" : "positional",
                    "nargs": 1,
                    "help": "directory or filename to restore from"
                },
                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                },

                    {
                    "name": "verbose",
                    "type" : "optional",
                    "help": 'increase verbosity',
                    "cmd_arg": [
                        "-v",
                        "--verbose"
                    ],
                    "nargs": 0
                },
                    {
                    "name": "directoryperdb",
                    "type" : "optional",
                    "help": "if dbpath specified, each db is in a separate directory",
                    "cmd_arg": [
                        "--directoryperdb"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "journal",
                    "type" : "optional",
                    "help": "enable journaling",
                    "cmd_arg": [
                        "--journal"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "collection",
                    "type" : "optional",
                    "displayName": "COLLECTION",
                    "help": " collection to use (some commands)",
                    "cmd_arg": [
                        "-c",
                        "--collection"
                    ],
                    "nargs": 1
                },


                    {
                    "name": "objcheck",
                    "type" : "optional",
                    "help": "validate object before inserting",
                    "cmd_arg": [
                        "--objectcheck"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "filter",
                    "type" : "optional",
                    "displayName": "FILTER",
                    "help": "filter to apply before inserting",
                    "cmd_arg": [
                        "--filter"
                    ],
                    "nargs": 1
                },

                    {
                    "name": "drop",
                    "type" : "optional",
                    "help": " drop each collection before import",
                    "cmd_arg": [
                        "--drop"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "oplogReplay",
                    "type" : "optional",
                    "help": "replay oplog for point-in-time restore",
                    "cmd_arg": [
                        "--oplogReplay"
                    ],
                    "nargs": 0
                },

                    {
                    "name": "keepIndexVersion",
                    "type" : "optional",
                    "help": " don't upgrade indexes to newest version",
                    "cmd_arg": [
                        "--keepIndexVersion"
                    ],
                    "nargs": 0
                },
                    {
                    "name": "ipv6",
                    "type" : "optional",
                    "cmd_arg":  "--ipv6",
                    "nargs": 0,
                    "help": "enable IPv6 support (disabled by default)"
                },

                {
                    "name": "authenticationDatabase",
                    "type" : "optional",
                    "cmd_arg":  "--authenticationDatabase",
                    "nargs": 1,
                    "help": "user source (defaults to dbname). 2.4.x or greater only."
                },

                {
                    "name": "restoreDbUsersAndRoles",
                    "type": "optional",
                    "cmd_arg":  "--restoreDbUsersAndRoles",
                    "nargs": 0,
                    "help": "Restore user and role definitions for the given "
                            "database. 2.6.x or greater only."
                }

            ]
        },
        #### resync-secondary ####
            {
            "prog": "resync-secondary",
            "group": "serverCommands",
            "shortDescription" : "Resyncs a secondary member",
            "description" : "Resyncs a secondary member",
            "function": "mongoctl.commands.server.resync_secondary.resync_secondary_command",
            "args": [
                    {
                    "name": "server",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "SERVER_ID",
                    "help": "a valid server id"
                },
                    {
                    "name": "assumeLocal",
                    "type" : "optional",
                    "cmd_arg": "--assume-local",
                    "nargs": 0,
                    "help": "Assumes that the server is running on local"
                            " host. This will skip local address/dns check",
                    "default": False
                },
                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                }
            ]
        },

        #### configure-cluster ####
            {
            "prog": "configure-cluster",
            "group": "clusterCommands",
            "shortDescription" : "initiate or reconfigure a cluster",
            "description" : "Initiaties or reconfigures a specific replica set cluster. "
                            "This command is \nused both to initiate the "
                            "cluster for the first time \nand to reconfigure "
                            "the cluster.",
            "function": "mongoctl.commands.cluster.configure.configure_cluster_command",
            "args": [
                    {
                    "name": "cluster",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "CLUSTER_ID",
                    "help": "A valid cluster id"
                },

                    {
                    "name": "dryRun",
                    "type" : "optional",
                    "cmd_arg":  ["-n" , "--dry-run"],
                    "nargs": 0,
                    "help": "prints configure cluster db command to execute "
                            "without executing it",
                    "default": False
                },

                    {
                    "name": "forcePrimaryServer",
                    "type" : "optional",
                    "displayName": "SERVER",
                    "cmd_arg":  [ "-f", "--force"],
                    "nargs": 1,
                    "help": "force member to become primary",
                    "default": None
                },

                    {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                    {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                }
            ]
        },

        #### list-clusters ####
            {
            "prog": "list-clusters",
            "group": "clusterCommands",
            "shortDescription" : "show list of configured clusters",
            "description" : "Show list of configured servers",
            "function": "mongoctl.commands.cluster.list_clusters.list_clusters_command"
        },

        #### show-cluster ####
            {
            "prog": "show-cluster",
            "group": "clusterCommands",
            "shortDescription" : "show cluster's configuration",
            "description" : "Shows specific cluster's configuration",
            "function": "mongoctl.commands.cluster.show.show_cluster_command",
            "args": [
                    {
                    "name": "cluster",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "CLUSTER_ID",
                    "help": "A valid cluster id"
                }
            ]
        },

        #### install ####
        # TODO: Remove and replace by install-mongodb
            {
            "prog": "install",
            "hidden": True,
            "group": "adminCommands",
            "shortDescription" : "install MongoDB",
            "description" : "install MongoDB",
            "function": "mongoctl.commands.misc.install.install_command",
            "args": [
                    {
                    "name": "version",
                    "type" : "positional",
                    "nargs": "?",
                    "displayName": "VERSION",
                    "help": "MongoDB version to install"
                },

                {
                    "name": "edition",
                    "type" : "optional",
                    "help": "edition (community (default) or enterprise)",
                    "cmd_arg": [
                        "--edition"
                    ],
                    "nargs": 1
                }
            ]
        },
        #### uninstall ####
        # TODO: Remove and replace by uninstall-mongodb
            {
            "prog": "uninstall",
            "hidden": True,
            "group": "adminCommands",
            "shortDescription" : "uninstall MongoDB",
            "description" : "uninstall MongoDB",
            "function": "mongoctl.commands.misc.install.uninstall_command",
            "args": [
                    {
                    "name": "version",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "VERSION",
                    "help": "MongoDB version to uninstall"
                }
            ]
        },
        #### install-mongodb ####
            {
            "prog": "install-mongodb",
            "group": "adminCommands",
            "shortDescription" : "install MongoDB",
            "description" : "install MongoDB",
            "function": "mongoctl.commands.misc.install.install_command",
            "args": [
                    {
                    "name": "version",
                    "type" : "positional",
                    "nargs": "?",
                    "displayName": "VERSION",
                    "help": "MongoDB version to install"
                },

                {
                    "name": "edition",
                    "type" : "optional",
                    "help": "edition (community (default) or enterprise)",
                    "cmd_arg": [
                        "--edition"
                    ],
                    "nargs": 1
                }
            ]
        },
        #### uninstall-mongodb ####
            {
            "prog": "uninstall-mongodb",
            "group": "adminCommands",
            "shortDescription" : "uninstall MongoDB",
            "description" : "uninstall MongoDB",
            "function": "mongoctl.commands.misc.install.uninstall_command",
            "args": [
                    {
                    "name": "version",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "VERSION",
                    "help": "MongoDB version to uninstall"
                } ,

                {
                    "name": "edition",
                    "type" : "optional",
                    "help": "edition (community (default) or enterprise)",
                    "cmd_arg": [
                        "--edition"
                    ],
                    "nargs": 1
                }
            ]
        },
        #### list-versions ####
            {
            "prog": "list-versions",
            "group": "adminCommands",
            "shortDescription" : "list all available MongoDB installations on"
                                 " this machine",
            "description" : "list all available MongoDB installations on"
                            " this machine",
            "function": "mongoctl.commands.misc.install.list_versions_command",
        },
        #### print-uri ####
        {
        "prog": "print-uri",
        "group": "miscCommands",
        "shortDescription" : "prints connection URI for a"
                             " server or cluster",
        "description" : "Prints MongoDB connection URI of the specified"
                        " server or clurter",
        "function": "mongoctl.commands.misc.print_uri.print_uri_command",
        "args": [
                {
                "name": "id",
                "type" : "positional",
                "nargs": 1,
                "displayName": "SERVER or CLUSTER ID",
                "help": "Server or cluster id"
            },
                {
                "name": "db",
                "type" : "optional",
                "help": "database name",
                "cmd_arg": [
                    "-d",
                    "--db"
                ],
                "nargs": 1
            }
        ]
        },

        {
            "prog": "add-shard",
            "group": "shardCommands",
            "shortDescription" : "Adds specified shard to sharded cluster",
            "description" : "Adds specified shard to sharded cluster",
            "function": "mongoctl.commands.sharding.sharding.add_shard_command",
            "args": [
                {
                    "name": "shardId",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "SHARD_ID",
                    "help": "A valid shard cluster id or shard server id"
                },

                {
                    "name": "dryRun",
                    "type" : "optional",
                    "cmd_arg":  ["-n" , "--dry-run"],
                    "nargs": 0,
                    "help": "prints configure cluster db command to execute "
                            "without executing it",
                    "default": False
                },

                {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                }
            ]
        },

        {
            "prog": "remove-shard",
            "group": "shardCommands",
            "shortDescription": "Removes shard from sharded cluster",
            "description": "Removes shard from sharded cluster",
            "function": "mongoctl.commands.sharding.sharding.remove_shard_command",
            "args": [
                {
                    "name": "shardId",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "SHARD_ID",
                    "help": "A valid shard cluster id or shard server id"
                },

                {
                    "name": "dryRun",
                    "type" : "optional",
                    "cmd_arg":  ["-n" , "--dry-run"],
                    "nargs": 0,
                    "help": "prints db command to execute "
                            "without executing it",
                    "default": False
                },

                {
                    "name": "unshardedDataDestination",
                    "displayName": "SHARD_ID",
                    "type" : "optional",
                    "cmd_arg":  ["--move-unsharded-data-to"],
                    "nargs": 1,
                    "help": "Moves unsharded to data to specified shard id",
                    "default": None
                },

                {
                    "name": "synchronized",
                    "type" : "optional",
                    "cmd_arg": ["--synchronized"],
                    "nargs": 0,
                    "help": "synchronized",
                    "default": False
                },

                {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                }
            ]
        },
        #### configure-cluster ####
        {
            "prog": "configure-shard-cluster",
            "group": "shardCommands",
            "shortDescription" : "configures a sharded cluster",
            "description" : "configures a sharded cluster",
            "function": "mongoctl.commands.sharding.sharding.configure_sharded_cluster_command",
            "args": [
                {
                    "name": "cluster",
                    "type" : "positional",
                    "nargs": 1,
                    "displayName": "CLUSTER_ID",
                    "help": "A valid cluster id"
                },

                {
                    "name": "dryRun",
                    "type" : "optional",
                    "cmd_arg":  ["-n" , "--dry-run"],
                    "nargs": 0,
                    "help": "prints configure cluster db command to execute "
                            "without executing it",
                    "default": False
                },

                {
                    "name": "username",
                    "type" : "optional",
                    "help": "admin username",
                    "cmd_arg": [
                        "-u"
                    ],
                    "nargs": 1
                },
                {
                    "name": "password",
                    "type" : "optional",
                    "help": "admin password",
                    "cmd_arg": [
                        "-p"
                    ],
                    "nargs": "?"
                }
            ]
        }


        ]

}


########NEW FILE########
__FILENAME__ = mongoctl_globals
__author__ = 'abdul'


DEFAULT_CONF_ROOT = "~/.mongoctl"

########NEW FILE########
__FILENAME__ = mongoctl_logging
__author__ = 'abdul'

import sys
import os
import traceback

import logging

import utils
import mongoctl_globals

from logging.handlers import TimedRotatingFileHandler

###############################################################################
LOG_DIR = "logs"

logger = None

# logger settings
_log_to_stdout = True
_logging_level = logging.INFO

VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")

###############################################################################
def get_logger():
    global logger, _logging_level

    if logger:
        return logger

    logger = logging.getLogger("MongoctlLogger")

    log_file_name="mongoctl.log"
    conf_dir = mongoctl_globals.DEFAULT_CONF_ROOT
    log_dir = utils.resolve_path(os.path.join(conf_dir, LOG_DIR))
    utils.ensure_dir(log_dir)


    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)8s | %(asctime)s | %(message)s")
    logfile = os.path.join(log_dir, log_file_name)
    fh = TimedRotatingFileHandler(logfile, backupCount=50, when="midnight")

    fh.setFormatter(formatter)
    fh.setLevel(logging.DEBUG)
    # add the handler to the root logger
    logging.getLogger().addHandler(fh)

    global _log_to_stdout
    if _log_to_stdout:
        sh = logging.StreamHandler(sys.stdout)
        std_formatter = logging.Formatter("%(message)s")
        sh.setFormatter(std_formatter)
        sh.setLevel(_logging_level)
        logging.getLogger().addHandler(sh)

    return logger

###############################################################################
def setup_logging(log_level=logging.INFO, log_to_stdout=True):
    global _log_to_stdout, _logging_level

    _log_to_stdout = log_to_stdout
    _logging_level = log_level

###############################################################################
def turn_logging_verbose_on():
    global _logging_level
    _logging_level = VERBOSE

###############################################################################
def log_info(msg):
    get_logger().info(msg)

###############################################################################
def log_error(msg):
    get_logger().error(msg)

###############################################################################
def log_warning(msg):
    get_logger().warning(msg)

###############################################################################
def log_verbose(msg):
    get_logger().log(VERBOSE, msg)

###############################################################################
def log_debug(msg):
    get_logger().debug(msg)

###############################################################################
def log_exception(exception):
    log_debug("EXCEPTION: %s" % exception)
    log_debug(traceback.format_exc())

###############################################################################
def stdout_log(msg):
    print msg

###############################################################################
def log_db_command(cmd):
    log_info( "Executing db command %s" % utils.document_pretty_string(cmd))

########NEW FILE########
__FILENAME__ = mongo_uri_tools
__author__ = 'abdul'

from pymongo import uri_parser, errors

###############################################################################
# mongo uri tool. Contains utility functions for dealing with mongo uris
###############################################################################

###############################################################################
# MongoUriWrapper
###############################################################################
class MongoUriWrapper:
    """
     A Mongo URI wrapper that makes it easy to deal with mongo uris:
     - Masks user/password on display (i.e. __str__()
    """
    ###########################################################################
    # Constructor
    ###########################################################################
    def __init__(self, uri_obj):
        self._uri_obj = uri_obj

    ###########################################################################
    @property
    def raw_uri(self):
        return self._get_uri(mask=False)

    ###########################################################################
    @property
    def member_raw_uri_list(self):
        return self._get_member_uri_list(mask=False)

    ###########################################################################
    @property
    def masked_uri(self):
        return self._get_uri(mask=True)

    ###########################################################################
    @property
    def member_masked_uri_list(self):
        return self._get_member_uri_list(mask=True)

    ###########################################################################
    @property
    def database(self):
        return self._uri_obj["database"]


    @database.setter
    def database(self, value):
        self._uri_obj["database"] = value

    ###########################################################################
    @property
    def node_list(self):
        return self._uri_obj["nodelist"]

    ###########################################################################
    @property
    def address(self):
        return self.addresses[0]

    ###########################################################################
    @property
    def addresses(self):
        addresses = []
        for node in self.node_list:
            address = "%s:%s" % (node[0], node[1])
            addresses.append(address)

        return addresses

    ###########################################################################
    @property
    def username(self):
        return self._uri_obj["username"]

    ###########################################################################
    @property
    def password(self):
        return self._uri_obj["password"]

    ###########################################################################
    def is_cluster_uri(self):
        return len(self.node_list) > 1

    ###########################################################################
    def __str__(self):
        return self.masked_uri

    ###########################################################################
    def _get_uri(self, mask=False):
        # build db string
        db_str = "/%s" % self.database if self.database else ""

        # build credentials string
        if self.username:
            if mask:
                creds = "*****:*****@"
            else:
                creds = "%s:%s@" % (self.username, self.password)
        else:
            creds = ""

        # build hosts string
        address_str = ",".join(self.addresses)
        return "mongodb://%s%s%s" % (creds, address_str, db_str)

    ###########################################################################
    def _get_member_uri_list(self, mask=False):
        # build db string
        db_str = "%s" % self.database if self.database else ""
        username = self.username
        password = "****" if mask else self.password

        # build credentials string
        if username:
            creds = "%s:%s@" % (username, password)
        else:
            creds = ""

        # build hosts string
        member_uris = []
        for node in self.node_list:
            address = "%s:%s" % (node[0], node[1])
            mem_uri = "mongodb://%s%s/%s" % (creds, address, db_str)
            member_uris.append(mem_uri)

        return member_uris

###############################################################################
def parse_mongo_uri(uri):
    try:
        uri_obj = uri_parser.parse_uri(uri)
        # validate uri
        nodes = uri_obj["nodelist"]
        for node in nodes:
            host = node[0]
            if not host:
                raise Exception("URI '%s' is missing a host." % uri)

        return MongoUriWrapper(uri_obj)
    except errors.ConfigurationError, e:
        raise Exception("Malformed URI '%s'. %s" % (uri, e))

    except Exception, e:
        raise Exception("Unable to parse mongo uri '%s'."
                        " Cause: %s" % (e, uri))

###############################################################################
def mask_mongo_uri(uri):
    uri_wrapper = parse_mongo_uri(uri)
    return uri_wrapper.masked_uri

###############################################################################
def is_mongo_uri(value):
    try:
        parse_mongo_uri(value)
        return True
    except Exception,e:
        return False

###############################################################################
def is_cluster_mongo_uri(mongo_uri):
    """
        Returns true if the specified mongo uri is a cluster connection
    """
    return len(parse_mongo_uri(mongo_uri).node_list) > 1



########NEW FILE########
__FILENAME__ = mongo_version
__author__ = 'abdul'

from verlib import NormalizedVersion, suggest_normalized_version
from errors import MongoctlException

# Version support stuff
MIN_SUPPORTED_VERSION = "1.8"


###############################################################################
# MongoEdition (enum)
###############################################################################

class MongoEdition():
    COMMUNITY = "community"
    ENTERPRISE = "enterprise"

###############################################################################
# VersionInfo class
# we had to inherit and override __str__ because the suggest_normalized_version
# method does not maintain the release candidate version properly
###############################################################################
class VersionInfo(NormalizedVersion):
    def __init__(self, version_number, edition=None):
        sugg_ver = suggest_normalized_version(version_number)
        super(VersionInfo,self).__init__(sugg_ver)
        self.version_number = version_number
        self.edition = edition or MongoEdition.COMMUNITY

    ###########################################################################
    def __str__(self):
        return "%s (%s)" % (self.version_number, self.edition)

    ###########################################################################
    def __eq__(self, other):
        return (other is not None and
                super(VersionInfo, self).__eq__(other) and
                self.edition == other.edition)

###############################################################################
def is_valid_version_info(version_info):
    return (is_valid_version(version_info.version_number) and
            version_info.edition in [MongoEdition.COMMUNITY,
                                     MongoEdition.ENTERPRISE])

###############################################################################
def is_valid_version(version_number):
    return suggest_normalized_version(version_number) is not None

###############################################################################
# returns true if version is greater or equal to 1.8
def is_supported_mongo_version(version_number):
    return (make_version_info(version_number)>=
            make_version_info(MIN_SUPPORTED_VERSION))

###############################################################################
def make_version_info(version_number, edition=None):
    if version_number is None:
        return None

    version_number = version_number.strip()
    version_number = version_number.replace("-pre-" , "-pre")
    version_info = VersionInfo(version_number, edition=edition)

    # validate version string
    if not is_valid_version_info(version_info):
        raise MongoctlException("Invalid version '%s." % version_info)
    else:
        return version_info


########NEW FILE########
__FILENAME__ = base
__author__ = 'abdul'

from mongoctl.utils import document_pretty_string
###############################################################################
# Document Wrapper Class
###############################################################################
class DocumentWrapper(object):

    ###########################################################################
    # Constructor
    ###########################################################################

    def __init__(self, document):
        self.__document__ = document

    ###########################################################################
    # Overridden Methods
    ###########################################################################
    def __str__(self):
        return document_pretty_string(self.__document__)

    ###########################################################################
    def get_document(self):
        return self.__document__

    ###########################################################################
    # Properties
    ###########################################################################
    def get_property(self, property_name):
        return self.__document__.get(property_name)

    ###########################################################################
    def set_property(self, name, value):
        self.__document__[name] = value

    ###########################################################################
    @property
    def id(self):
        return self.get_property('_id')

    @id.setter
    def id(self, value):
        self.set_property('_id', value)

########NEW FILE########
__FILENAME__ = cluster
__author__ = 'abdul'

from base import DocumentWrapper




###############################################################################
# Generic Cluster Class
###############################################################################
class Cluster(DocumentWrapper):

    ###########################################################################
    # Constructor and other init methods
    ###########################################################################
    def __init__(self, cluster_document):
        DocumentWrapper.__init__(self, cluster_document)
        self._members = self._resolve_members("members")

    ###########################################################################
    def _resolve_members(self, member_prop):
        member_documents = self.get_property(member_prop)
        members = []

        # if members are not set then return
        member_type = self.get_member_type()
        if member_documents:
            for mem_doc in member_documents:
                member = member_type(mem_doc)
                members.append(member)

        return members

    ###########################################################################
    def get_member_type(self):
        raise Exception("Should be implemented by subclasses")

    ###########################################################################
    # Properties
    ###########################################################################
    def get_description(self):
        return self.get_property("description")

    ###########################################################################
    def get_members(self):
        return self._members

    ###########################################################################
    def get_repl_key(self):
        return self.get_property("replKey")

    ###########################################################################
    def has_member_server(self, server):
        return self.get_member_for(server) is not None

    ###########################################################################
    def get_member_for(self, server):
        for member in self.get_members():
            if (member.get_server() and
                        member.get_server().id == server.id):
                return member

        return None

    ###########################################################################
    def get_status(self):
        """
            Needs to be overridden
        """
    ###########################################################################
    def get_default_server(self):
        """
            Needs to be overridden
        """

    ###########################################################################
    def get_mongo_uri_template(self, db=None):

        if not db:
            if self.get_repl_key():
                db = "[/<dbname>]"
            else:
                db = ""
        else:
            db = "/" + db

        server_uri_templates = []
        for member in self.get_members():
            server = member.get_server()
            if not server.is_arbiter_server():
                server_uri_templates.append(server.get_address_display())

        creds = "[<dbuser>:<dbpass>@]" if self.get_repl_key() else ""
        return ("mongodb://%s%s%s" % (creds, ",".join(server_uri_templates),
                                      db))

########NEW FILE########
__FILENAME__ = mongod
__author__ = 'abdul'



import server

from mongoctl.utils import resolve_path
from mongoctl.mongoctl_logging import log_verbose, log_debug, log_exception, \
    log_warning

from bson.son import SON
from mongoctl.errors import MongoctlException
from replicaset_cluster import ReplicaSetCluster, get_member_repl_lag
from sharded_cluster import ShardedCluster
###############################################################################
# CONSTANTS
###############################################################################

# This is mongodb's default dbpath
DEFAULT_DBPATH='/data/db'

LOCK_FILE_NAME = "mongod.lock"

###############################################################################
# MongodServer Class
###############################################################################

class MongodServer(server.Server):

    ###########################################################################
    # Constructor
    ###########################################################################
    def __init__(self, server_doc):
        super(MongodServer, self).__init__(server_doc)

    ###########################################################################
    # Properties
    ###########################################################################

    def get_db_path(self):
        dbpath = self.get_cmd_option("dbpath")
        if not dbpath:
            dbpath = super(MongodServer, self).get_server_home()
        if not dbpath:
            dbpath = DEFAULT_DBPATH

        return resolve_path(dbpath)

    ###########################################################################
    def get_server_home(self):
        """
            Override!
        :return:
        """
        home_dir = super(MongodServer, self).get_server_home()
        if not home_dir:
            home_dir = self.get_db_path()

        return home_dir

    ###########################################################################
    def export_cmd_options(self, options_override=None):
        """
            Override!
        :return:
        """
        cmd_options = super(MongodServer, self).export_cmd_options(
            options_override=options_override)

        # reset some props to exporting vals
        cmd_options['dbpath'] = self.get_db_path()

        if 'repairpath' in cmd_options:
            cmd_options['repairpath'] = resolve_path(cmd_options['repairpath'])

        # Add ReplicaSet args if a cluster is configured

        repl_cluster = self.get_replicaset_cluster()
        if repl_cluster is not None:
            if "replSet" not in cmd_options:
                cmd_options["replSet"] = repl_cluster.id

        # add configsvr as needed
        if self.is_config_server():
            cmd_options["configsvr"] = True

        # add shardsvr as needed
        if self.is_shard_server():
            cmd_options["shardsvr"] = True

        return cmd_options

    ###########################################################################
    def get_seed_users(self):
        """
            Override!
        :return:
        """
        seed_users = super(MongodServer, self).get_seed_users()
        # exempt database users for config servers
        if seed_users and self.is_config_server():
            for dbname in seed_users.keys():
                if dbname not in ["admin", "local", "config"]:
                    del seed_users[dbname]

        return seed_users

    ###########################################################################
    def get_lock_file_path(self):
        return self.get_default_file_path(LOCK_FILE_NAME)


    ###########################################################################
    def is_master(self):
        return self.get_cmd_option("master")

    ###########################################################################
    def is_slave(self):
        return self.get_cmd_option("slave")

    ###########################################################################
    def is_auth(self):
        if self.get_cmd_option("auth") or self.get_cmd_option("keyFile"):
            return True
        else:
            cluster = self.get_cluster()
            if cluster:
                return cluster.get_repl_key() is not None

    ###########################################################################
    def set_auth(self,auth):
        self.set_cmd_option("auth", auth)


    ###########################################################################
    def is_administrable(self):
        return not self.is_arbiter_server() and self.can_function()

    ###########################################################################
    def get_status(self, admin=False):

        # get status for super
        status = super(MongodServer, self).get_status(admin=admin)

        if "error" not in status and admin and not self.is_arbiter_server():
            rs_summary = self.get_rs_status_summary()
            if rs_summary:
                status["selfReplicaSetStatusSummary"] = rs_summary

        return status

    ###########################################################################
    def get_server_status_summary(self):
        server_status = self.db_command(SON([('serverStatus', 1)]), "admin")
        server_summary = {
            "host": server_status['host'],
            "connections": server_status['connections'],
            "version": server_status['version'],
            "uptime": server_status['uptime']
        }
        return server_summary

    ###########################################################################
    def get_rs_status_summary(self):
        if self.is_replicaset_member():
            member_rs_status = self.get_member_rs_status()
            if member_rs_status:
                return {
                    "name": member_rs_status['name'],
                    "stateStr": member_rs_status['stateStr']
                }

    ###########################################################################
    def is_arbiter_server(self):
        cluster = self.get_cluster()
        return (isinstance(cluster, ReplicaSetCluster) and
                cluster.get_member_for(self).is_arbiter())

    ###########################################################################
    def is_replicaset_member(self):
        cluster = self.get_cluster()
        return isinstance(cluster, ReplicaSetCluster)

    ###########################################################################
    def get_replicaset_cluster(self):
        cluster = self.get_cluster()
        if isinstance(cluster, ReplicaSetCluster):
            return cluster

    ###########################################################################
    def is_config_server(self):
        cluster = self.get_cluster()

        return ((isinstance(cluster, ShardedCluster) and
                 cluster.has_config_server(self)) or
                self.get_cmd_option("configsvr"))

    ###########################################################################
    def is_shard_server(self):
        cluster = self.get_cluster()
        if isinstance(cluster, ShardedCluster):
            return cluster.has_shard(self)
        elif isinstance(cluster, ReplicaSetCluster):
            return cluster.is_shard_member()

    ###########################################################################
    def command_needs_auth(self, dbname, cmd):
        # isMaster command does not need auth
        if "isMaster" in cmd or "ismaster" in cmd:
            return False
        if 'shutdown' in cmd and self.is_arbiter_server():
            return False

        # otherwise use default behavior
        return super(MongodServer, self).command_needs_auth(dbname, cmd)

    ###########################################################################
    def get_mongo_uri_template(self, db=None):
        if not db:
            if self.is_auth():
                db = "/[dbname]"
            else:
                db = ""
        else:
            db = "/" + db

        creds = "[dbuser]:[dbpass]@" if self.is_auth() else ""
        return "mongodb://%s%s%s" % (creds, self.get_address_display(), db)

    ###########################################################################
    def get_rs_config(self):
        try:
            return self.get_db('local')['system.replset'].find_one()
        except (Exception,RuntimeError), e:
            log_debug("Error whille trying to read rs config from "
                      "server '%s': %s" % (self.id, e))
            log_exception(e)
            if type(e) == MongoctlException:
                raise e
            else:
                log_verbose("Cannot get rs config from server '%s'. "
                            "cause: %s" % (self.id, e))
                return None

    ###########################################################################
    def get_rs_status(self):
        try:
            rs_status_cmd = SON([('replSetGetStatus', 1)])
            rs_status =  self.db_command(rs_status_cmd, 'admin')
            return rs_status
        except (Exception,RuntimeError), e:
            log_debug("Cannot get rs status from server '%s'. cause: %s" %
                        (self.id, e))
            log_exception(e)
            return None

    ###########################################################################
    def get_member_rs_status(self):
        rs_status =  self.get_rs_status()
        if rs_status:
            try:
                for member in rs_status['members']:
                    if 'self' in member and member['self']:
                        return member
            except (Exception,RuntimeError), e:
                log_debug("Cannot get member rs status from server '%s'."
                          " cause: %s" % (self.id, e))
                log_exception(e)

                return None

    ###########################################################################
    def is_primary(self):
        master_result = self.is_master_command()

        if master_result:
            return master_result.get("ismaster")

    ###########################################################################
    def is_secondary(self):
        master_result = self.is_master_command()

        if master_result:
            return master_result.get("secondary")

    ###########################################################################
    def is_master_command(self):
        try:
            if self.is_online():
                result = self.db_command({"isMaster" : 1}, "admin")
                return result

        except(Exception, RuntimeError),e:
            log_verbose("isMaster command failed on server '%s'. Cause %s" %
                        (self.id, e))

    ###########################################################################
    def is_reporting_incomplete_ismaster(self):
        is_master = self.is_master_command()
        if 'setName' not in is_master:
            if 'secondary' in is_master:
                log_warning("ismaster returning an incomplete result: %s"
                            % is_master)
                return True

        return False

    ###########################################################################
    def read_replicaset_name(self):
        master_result = self.is_master_command()
        if master_result:
            return "setName" in master_result and master_result["setName"]

    ###########################################################################
    def get_repl_lag(self, master_status):
        """
            Given two 'members' elements from rs.status(),
            return lag between their optimes (in secs).
        """
        member_status = self.get_member_rs_status()

        if not member_status:
            raise MongoctlException("Unable to determine replicaset status for"
                                    " member '%s'" %
                                    self.id)

        return get_member_repl_lag(member_status, master_status)



########NEW FILE########
__FILENAME__ = mongos
__author__ = 'abdul'

from server import Server

###############################################################################
# CONSTANTS
###############################################################################


###############################################################################
# MongosServer Class
###############################################################################

class MongosServer(Server):

    ###########################################################################
    # Constructor
    ###########################################################################
    def __init__(self, server_doc):
        super(MongosServer, self).__init__(server_doc)

    ###########################################################################
    def export_cmd_options(self, options_override=None):
        """
            Override!
        :return:
        """
        cmd_options = super(MongosServer, self).export_cmd_options(
            options_override=options_override)

        # Add configServers arg
        cluster = self.get_validate_cluster()
        config_addresses = ",".join(cluster.get_config_member_addresses())
        cmd_options["configdb"] = config_addresses

        return cmd_options
########NEW FILE########
__FILENAME__ = replicaset_cluster
__author__ = 'abdul'

import mongoctl.repository as repository

from cluster import Cluster
from mongoctl import users
from base import DocumentWrapper
from mongoctl.utils import *
from bson import DBRef

from mongoctl.config import get_cluster_member_alt_address_mapping
from mongoctl.mongoctl_logging import log_verbose, log_error, log_db_command

from mongoctl.prompt import prompt_confirm

###############################################################################
# ReplicaSet Cluster Member Class
###############################################################################

class ReplicaSetClusterMember(DocumentWrapper):

    ###########################################################################
    # Constructor
    ###########################################################################
    def __init__(self, member_doc):
        DocumentWrapper.__init__(self, member_doc)
        self._server = None

    ###########################################################################
    # Properties
    ###########################################################################

    def get_server(self):

        server_doc = self.get_property("server")
        host = self.get_property("host")

        if self._server is None:
            if server_doc is not None:
                if type(server_doc) is DBRef:
                    self._server = repository.lookup_server(server_doc.id)
            elif host is not None:
                self._server = repository.build_server_from_address(host)

        return self._server

    ###########################################################################
    def get_host(self):
        server = self.get_server()
        if server:
            return server.get_address()

    ###########################################################################
    def is_arbiter(self):
        return self.get_property("arbiterOnly") == True

    ###########################################################################
    def is_passive(self):
        return self.get_priority() == 0

    ###########################################################################
    def get_priority(self):
        return self.get_property("priority")

    ###########################################################################
    # Interface Methods
    ###########################################################################
    def get_member_type(self):
        return ReplicaSetClusterMember

    ###########################################################################
    def can_become_primary(self):
        return not self.is_arbiter() and self.get_priority() != 0

    ###########################################################################
    def get_member_repl_config(self):

        # create the member repl config with host

        member_conf = {"host": self.get_host()}

        # Add the rest of the properties configured in the document
        #  EXCEPT host/server

        ignore = ['host', 'server']

        for key,value in self.__document__.items():
            if key not in ignore :
                member_conf[key] = value

        self._apply_alt_address_mapping(member_conf)

        return member_conf

    ###########################################################################
    def _apply_alt_address_mapping(self, member_conf):

        # Not applicable to arbiters
        if self.is_arbiter():
            return

        tag_mapping = get_cluster_member_alt_address_mapping()
        if not tag_mapping:
            return

        tags = member_conf.get("tags", {})
        for tag_name, alt_address_prop in tag_mapping.items():
            alt_address = self.get_server().get_property(alt_address_prop)

            # set the alt address if it is different than host
            if alt_address and alt_address != member_conf['host']:
                tags[tag_name] = alt_address
            else:
                log_verbose("No alt address tag value created for alt address"
                            " mapping '%s=%s' for member \n%s" %
                            (tag_name, alt_address_prop, self))

        # set the tags property of the member config if there are any
        if tags:
            log_verbose("Member '%s' tags : %s" % (member_conf['host'], tags))
            member_conf['tags'] = tags

    ###########################################################################
    def read_rs_config(self):
        if self.is_valid():
            server = self.get_server()
            if server.can_function():
                return server.get_rs_config()
        return None

    ###########################################################################
    def is_valid(self):
        try:
            self.validate()
            return True
        except Exception, e:
            log_error("%s" % e)
            log_exception(e)
            return False

    ###########################################################################
    def validate(self):
        host_conf = self.get_property("host")
        server_conf = self.get_property("server")

        # ensure that 'server' or 'host' are configured

        if server_conf is None and host_conf is None:
            msg = ("Invalid member configuration:\n%s \n"
                   "Please set 'server' or 'host'." %
                   document_pretty_string(self.get_document()))
            raise MongoctlException(msg)

        # validate host if set
        if host_conf and not is_valid_member_address(host_conf):
            msg = ("Invalid 'host' value in member:\n%s \n"
                   "Please make sure 'host' is in the 'address:port' form" %
                   document_pretty_string(self.get_document()))
            raise MongoctlException(msg)

        # validate server if set
        server = self.get_server()
        if server is None:
            msg = ("Invalid 'server' value in member:\n%s \n"
                   "Please make sure 'server' is set or points to a "
                   "valid server." %
                   document_pretty_string(self.get_document()))
            raise MongoctlException(msg)
        repository.validate_server(server)
        if server.get_address() is None:
            raise MongoctlException("Invalid member configuration for server "
                                    "'%s'. address property is not set." %
                                    (server.id))

    ###########################################################################
    def validate_against_current_config(self, current_rs_conf):
        """
        Validates the member document against current rs conf
            1- If there is a member in current config with _id equals to my id
                then ensure hosts addresses resolve to the same host

            2- If there is a member in current config with host resolving to my
               host then ensure that if my id is et then it
               must equal member._id

        """

        # if rs is not configured yet then there is nothing to validate
        if not current_rs_conf:
            return

        my_host = self.get_host()
        current_member_confs = current_rs_conf['members']
        err = None
        for curr_mem_conf in current_member_confs:
            if (self.id and
                        self.id == curr_mem_conf['_id'] and
                    not is_same_address(my_host, curr_mem_conf['host'])):
                err = ("Member config is not consistent with current rs "
                       "config. \n%s\n. Both have the sam _id but addresses"
                       " '%s' and '%s' do not resolve to the same host." %
                       (document_pretty_string(curr_mem_conf),
                        my_host, curr_mem_conf['host'] ))

            elif (is_same_address(my_host, curr_mem_conf['host']) and
                      self.id and
                          self.id != curr_mem_conf['_id']):
                err = ("Member config is not consistent with current rs "
                       "config. \n%s\n. Both addresses"
                       " '%s' and '%s' resolve to the same host but _ids '%s'"
                       " and '%s' are not equal." %
                       (document_pretty_string(curr_mem_conf),
                        my_host, curr_mem_conf['host'],
                        self.id, curr_mem_conf['_id']))

        if err:
            raise MongoctlException("Invalid member configuration:\n%s \n%s" %
                                    (self, err))


    ###########################################################################
    def validate_against_other(self, other_member):
        err = None
        # validate _id uniqueness
        if self.id and self.id == other_member.id:
            err = ("Duplicate '_id' ('%s') found in a different member." %
                   self.id)

        # validate server uniqueness
        elif (self.get_property('server') and
                      self.get_server().id == other_member.get_server().id):
            err = ("Duplicate 'server' ('%s') found in a different member." %
                   self.get_server().id)
        else:

            # validate host uniqueness
            h1 = self.get_host()
            h2 = other_member.get_host()

            try:

                if is_same_address(h1, h2):
                    err = ("Duplicate 'host' found. Host in '%s' and "
                           "'%s' map to the same host." % (h1, h2))

            except Exception, e:
                log_exception(e)
                err = "%s" % e

        if err:
            raise MongoctlException("Invalid member configuration:\n%s \n%s" %
                                    (self, err))

###############################################################################
# ReplicaSet Cluster Class
###############################################################################
class ReplicaSetCluster(Cluster):

    ###########################################################################
    # Constructor and other init methods
    ###########################################################################
    def __init__(self, cluster_document):
        Cluster.__init__(self, cluster_document)
        self._members = self._resolve_members("members")

    ###########################################################################
    def _resolve_members(self, member_prop):
        member_documents = self.get_property(member_prop)
        members = []

        # if members are not set then return
        if member_documents:
            for mem_doc in member_documents:
                member = repository.new_replicaset_cluster_member(mem_doc)
                members.append(member)

        return members

    ###########################################################################
    def get_members_info(self):
        info = []
        for member in self.get_members():
            server = member.get_server()
            if server is not None:
                info.append(server.id)
            else:
                info.append("<Invalid Member>")

        return info

    ###########################################################################
    # Interface Methods
    ###########################################################################

    def get_default_server(self):
        return self.get_primary_server()

    ###########################################################################
    def get_primary_server(self):
        primary_member = self.get_primary_member()
        if primary_member:
            return primary_member.get_server()

    ###########################################################################
    def get_primary_member(self):
        for member in self.get_members():
            if member.get_server().is_primary():
                return member

        return None

    ###########################################################################
    def suggest_primary_member(self):
        for member in self.get_members():
            if(member.can_become_primary() and
                       member.get_server() is not None and
                   member.get_server().is_online_locally()):
                return member

    ###########################################################################
    def get_status(self):
        primary_server = self.get_primary_server()

        if not primary_server:
            raise MongoctlException("Unable to determine primary member for"
                                    " cluster '%s'" % self.id)

        master_status = primary_server.get_member_rs_status()
        primary_server_address = master_status['name']

        rs_status_members = primary_server.get_rs_status()['members']
        other_members = []
        for m in rs_status_members:
            if not m.get("self", False):
                address = m.get("name")
                member = {
                    "address": address,
                    "stateStr": m.get("stateStr")
                }
                if m.get("errmsg", None):
                    member['errmsg'] = m['errmsg']
                if m.get("stateStr", None) in ["STARTUP2", "SECONDARY",
                                               "RECOVERING"]:
                    # compute lag
                    lag_in_secs = get_member_repl_lag(m, master_status)
                    # compute lag description
                    hours, remainder = divmod(lag_in_secs, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if hours:
                        desc = ("%d hour(s) %d minute(s) %d second(s)" %
                                (hours, minutes, seconds))
                    elif minutes:
                        desc = ("%d minute(s) %d second(s)" %
                                (minutes, seconds))
                    else:
                        desc = "%d second(s)" % (seconds)

                    member['replLag'] = {
                        "value": lag_in_secs,
                        "description": desc
                    }
                other_members.append(member)
        return {
            "primary": {
                "address": primary_server_address,
                "stateStr": "PRIMARY",
                "serverStatusSummary":
                    primary_server.get_server_status_summary()
            },
            #"replSetConfig": primary_server.get_rs_config(),
            "otherMembers": other_members
        }

    ###########################################################################
    def get_dump_best_secondary(self, max_repl_lag=None):
        """
        Returns the best secondary member to be used for dumping
        best = passives with least lags, if no passives then least lag
        """
        secondary_lag_tuples = []

        primary_member = self.get_primary_member()
        if not primary_member:
            raise MongoctlException("Unable to determine primary member for"
                                    " cluster '%s'" % self.id)

        master_status = primary_member.get_server().get_member_rs_status()

        if not master_status:
            raise MongoctlException("Unable to determine replicaset status for"
                                    " primary member '%s'" %
                                    primary_member.get_server().id)

        for member in self.get_members():
            if member.get_server().is_secondary():
                repl_lag = member.get_server().get_repl_lag(master_status)
                if max_repl_lag and  repl_lag > max_repl_lag:
                    log_info("Excluding member '%s' because it's repl lag "
                             "(in seconds)%s is more than max %s. " %
                             (member.get_server().id,
                              repl_lag, max_repl_lag))
                    continue
                secondary_lag_tuples.append((member,repl_lag))

        def best_secondary_comp(x, y):
            x_mem, x_lag = x
            y_mem, y_lag = y
            if x_mem.is_passive():
                if y_mem.is_passive():
                    return x_lag - y_lag
                else:
                    return -1
            elif y_mem.is_passive():
                return 1
            else:
                return x_lag - y_lag

        if secondary_lag_tuples:
            secondary_lag_tuples.sort(best_secondary_comp)
            return secondary_lag_tuples[0][0]

    ###########################################################################
    def is_replicaset_initialized(self):
        """
        iterate on all members you get a member with a non-null
        read_replicaset_name()
        """

        # it's possible isMaster returns an "incomplete" result if we
        # query a replica set member while it's loading the replica set config
        # https://jira.mongodb.org/browse/SERVER-13458
        # let's try to detect this state before proceeding
        # seems like if the "secondary" field is present, but "setName" isn't,
        # it's a good indicator that we just need to wait a bit
        # add an uptime check in for good measure

        for member in self.get_members():
            if member.get_server().get_server_status_summary()['uptime'] < 2:
                log_verbose("The server just started, giving it a short 2 "
                            "second allowance to load a possible replica "
                            "set config...")
                time.sleep(2)

            server = member.get_server()
            if server.read_replicaset_name():
                return True
            elif server.is_reporting_incomplete_ismaster():

                def is_reporting_valid_ismaster():
                    return not server.is_reporting_incomplete_ismaster()

                wait_for(is_reporting_valid_ismaster, timeout=30, grace=False)

                # now try once more to get the replica set name
                if server.read_replicaset_name():
                    return True

        return False

    ###########################################################################
    def initialize_replicaset(self, suggested_primary_server=None):
        log_info("Initializing replica set cluster '%s' %s..." %
                 (self.id,
                  "" if suggested_primary_server is None else
                  "to contain only server '%s'" %
                  suggested_primary_server.id))

        ##### Determine primary server
        log_info("Determining which server should be primary...")
        primary_server = suggested_primary_server
        if primary_server is None:
            primary_member = self.suggest_primary_member()
            if primary_member is not None:
                primary_server = primary_member.get_server()

        if primary_server is None:
            raise MongoctlException("Unable to determine primary server."
                                    " At least one member server has"
                                    " to be online.")
        log_info("Selected server '%s' as primary." % primary_server.id)

        init_cmd = self.get_replicaset_init_all_db_command(
            suggested_primary_server)

        try:

            log_db_command(init_cmd)
            primary_server.timeout_maybe_db_command(init_cmd, "admin")

            # wait for replset to init
            def is_init():
                return self.is_replicaset_initialized()

            log_info("Will now wait for the replica set to initialize.")
            wait_for(is_init,timeout=60, sleep_duration=1)

            if self.is_replicaset_initialized():
                log_info("Successfully initiated replica set cluster '%s'!" %
                         self.id)
            else:
                msg = ("Timeout error: Initializing replicaset '%s' took "
                       "longer than expected. This does not necessarily"
                       " mean that it failed but it could have failed. " %
                       self.id)
                raise MongoctlException(msg)
                ## add the admin user after the set has been initiated
            ## Wait for the server to become primary though (at MongoDB's end)

            def is_primary_for_real():
                return primary_server.is_primary()

            log_info("Will now wait for the intended primary server to "
                     "become primary.")
            wait_for(is_primary_for_real,timeout=60, sleep_duration=1)

            if not is_primary_for_real():
                msg = ("Timeout error: Waiting for server '%s' to become "
                       "primary took longer than expected. "
                       "Please try again later." % primary_server.id)
                raise MongoctlException(msg)

            log_info("Server '%s' is primary now!" % primary_server.id)

            # setup cluster users
            users.setup_cluster_users(self, primary_server)

            log_info("New replica set configuration:\n%s" %
                     document_pretty_string(self.read_rs_config()))
            return True
        except Exception, e:
            log_exception(e)
            raise MongoctlException("Unable to initialize "
                                    "replica set cluster '%s'. Cause: %s" %
                                    (self.id,e) )

    ###########################################################################
    def configure_replicaset(self, add_server=None, force_primary_server=None):

        # Check if this is an init VS an update
        if not self.is_replicaset_initialized():
            self.initialize_replicaset()
            return

        primary_member = self.get_primary_member()

        # force server validation and setup
        if force_primary_server:
            force_primary_member = self.get_member_for(force_primary_server)
            # validate is cluster member
            if not force_primary_member:
                msg = ("Server '%s' is not a member of cluster '%s'" %
                       (force_primary_server.id, self.id))
                raise MongoctlException(msg)

            # validate is administrable
            if not force_primary_server.is_administrable():
                msg = ("Server '%s' is not running or has connection problems."
                       " For more details, Run 'mongoctl status %s'" %
                       (force_primary_server.id,
                        force_primary_server.id))
                raise MongoctlException(msg)

            if not force_primary_member.can_become_primary():
                msg = ("Server '%s' cannot become primary. Reconfiguration of"
                       " a replica set must be sent to a node that can become"
                       " primary" % force_primary_server.id)
                raise MongoctlException(msg)

            if primary_member:
                msg = ("Cluster '%s' currently has server '%s' as primary. "
                       "Proceed with force-reconfigure on server '%s'?" %
                       (self.id,
                        primary_member.get_server().id,
                        force_primary_server.id))
                if not prompt_confirm(msg):
                    return
            else:
                log_info("No primary server found for cluster '%s'" %
                         self.id)
        elif primary_member is None:
            raise MongoctlException("Unable to determine primary server"
                                    " for replica set cluster '%s'" %
                                    self.id)

        cmd_server = (force_primary_server if force_primary_server
                      else primary_member.get_server())

        log_info("Re-configuring replica set cluster '%s'..." % self.id)

        force = force_primary_server is not None
        rs_reconfig_cmd = \
            self.get_replicaset_reconfig_db_command(add_server=add_server,
                                                    force=force)
        desired_config = rs_reconfig_cmd['replSetReconfig']

        try:
            log_info("Executing the following command on server '%s':"
                     "\n%s" % (cmd_server.id,
                               document_pretty_string(rs_reconfig_cmd)))

            cmd_server.disconnecting_db_command(rs_reconfig_cmd, "admin")

            log_info("Re-configuration command for replica set cluster '%s'"
                     " issued successfully." % self.id)

            # Probably need to reconnect.  May not be primary any more.
            desired_cfg_version = desired_config['version']

            def got_the_memo(cur_cfg=None):
                current_config = cur_cfg or self.read_rs_config()
                # might've gotten None if nobody answers & tells us, so:
                current_cfg_version = (current_config['version']
                                       if current_config else 0)
                version_diff = (current_cfg_version - desired_cfg_version)
                return ((version_diff == 0) or
                        # force => mongo adds large random # to 'version'.
                        (force and version_diff >= 0))

            realized_config = self.read_rs_config()
            if not got_the_memo(realized_config):
                log_verbose("Really? Config version %s? "
                            "Let me double-check that ..." %
                            "unchanged" if realized_config else "unavailable")

                if not wait_for(got_the_memo, timeout=45, sleep_duration=5):
                    raise Exception("New config version not detected!")
                    # Finally! Resample.
                realized_config = self.read_rs_config()

            log_info("New replica set configuration:\n %s" %
                     document_pretty_string(realized_config))
            return True
        except Exception, e:
            log_exception(e)
            raise MongoctlException("Unable to reconfigure "
                                    "replica set cluster '%s'. Cause: %s " %
                                    (self.id,e) )

    ###########################################################################
    def add_member_to_replica(self, server):
        self.configure_replicaset(add_server=server)


    ###########################################################################
    def get_replicaset_reconfig_db_command(self, add_server=None, force=False):
        current_rs_conf = self.read_rs_config()
        new_config = self.make_replset_config(add_server=add_server,
                                              current_rs_conf=current_rs_conf)
        if current_rs_conf is not None:
            # update the rs config version
            new_config['version'] = current_rs_conf['version'] + 1

        log_info("Current replica set configuration:\n %s" %
                 document_pretty_string(current_rs_conf))

        return {"replSetReconfig": new_config, "force": force}

    ###########################################################################
    def get_replicaset_init_all_db_command(self, only_for_server=None):
        replset_config = \
            self.make_replset_config(only_for_server=only_for_server)

        return {"replSetInitiate": replset_config}

    ###########################################################################
    def is_member_configured_for(self, server):
        member = self.get_member_for(server)
        mem_conf = member.get_member_repl_config()
        rs_conf = self.read_rs_config()
        return (rs_conf is not None and
                self.match_member_id(mem_conf, rs_conf['members']) is not None)

    ###########################################################################
    def has_any_server_that(self, predicate):
        def server_predicate(member):
            server = member.get_server()
            return predicate(server) if server is not None else False

        return len(filter(server_predicate, self.get_members())) > 0

    ###########################################################################
    def get_all_members_configs(self):
        member_configs = []
        for member in self.get_members():
            member_configs.append(member.get_member_repl_config())

        return member_configs

    ###########################################################################
    def validate_members(self, current_rs_conf):

        members = self.get_members()
        length = len(members)
        for member in members:
            # basic validation
            member.validate()

        for i in range(0, length):
            member = members[i]
            # validate member against other members
            for j in range(i+1, length):
                member.validate_against_other(members[j])

            # validate members against current config
            member.validate_against_current_config(current_rs_conf)


    ###########################################################################
    def make_replset_config(self,
                            only_for_server=None,
                            add_server=None,
                            current_rs_conf=None):

        # validate members first
        self.validate_members(current_rs_conf)
        member_confs = None
        if add_server is not None:
            member = self.get_member_for(add_server)
            member_confs = []
            member_confs.extend(current_rs_conf['members'])
            member_confs.append(member.get_member_repl_config())
        elif only_for_server is not None:
            member = self.get_member_for(only_for_server)
            member_confs = [member.get_member_repl_config()]
        else:
            member_confs = self.get_all_members_configs()

        # populate member ids when needed
        self.populate_member_conf_ids(member_confs, current_rs_conf)

        return {"_id" : self.id,
                "members": member_confs}

    ###########################################################################
    def populate_member_conf_ids(self, member_confs, current_rs_conf=None):
        new_id = 0
        current_member_confs = None
        if current_rs_conf is not None:
            current_member_confs = current_rs_conf['members']
            new_id = self.max_member_id(current_member_confs) + 1

        for mem_conf in member_confs:
            if mem_conf.get('_id') is None :
                member_id = self.match_member_id(mem_conf,
                                                 current_member_confs)

                # if there is no match then use increment
                if member_id is None:
                    member_id = new_id
                    new_id = new_id + 1

                mem_conf['_id'] = member_id

    ###########################################################################
    def match_member_id(self, member_conf, current_member_confs):
        """
        Attempts to find an id for member_conf where fom current members confs
        there exists a element.
        Returns the id of an element of current confs
        WHERE member_conf.host and element.host are EQUAL or map to same host
        """
        if current_member_confs is None:
            return None

        for curr_mem_conf in current_member_confs:
            if is_same_address(member_conf['host'], curr_mem_conf['host']):
                return curr_mem_conf['_id']

        return None

    ###########################################################################
    def max_member_id(self, member_confs):
        max_id = 0
        for mem_conf in member_confs:
            if mem_conf['_id'] > max_id:
                max_id = mem_conf['_id']
        return max_id

    ###########################################################################
    def read_rs_config(self):

        # first attempt to read the conf from the primary server

        log_debug("Attempting to read rs conf for cluster %s" % self.id)
        log_debug("Locating primary server...")
        primary_member = self.get_primary_member()
        if primary_member:
            log_debug("Reading rs conf from primary server %s." %
                      primary_member.get_server().id)
            rs_conf = primary_member.read_rs_config()
            log_debug("RS CONF: %s" % document_pretty_string(rs_conf))
            return rs_conf

        log_debug("No primary server found. Iterate on all members "
                  "until an rs conf is found...")
        # iterate on all members until you get a non null rs-config
        # Read from arbiters only when needed so skip members until the end

        arb_members = []
        for member in self.get_members():
            if member.is_arbiter():
                arb_members.append(member)
                continue
            else:
                rs_conf = member.read_rs_config()
                if rs_conf is not None:
                    return rs_conf

        # No luck yet... iterate on arbiters
        for arb in arb_members:
            rs_conf = arb.read_rs_config()
            if rs_conf is not None:
                return rs_conf

    ###########################################################################
    def get_sharded_cluster(self):
        return repository.lookup_cluster_by_shard(self)

    ###########################################################################
    def is_shard_member(self):
        return self.get_sharded_cluster() is not None

###############################################################################
def get_member_repl_lag(member_status, master_status):

    lag_in_seconds = abs(timedelta_total_seconds(
        member_status['optimeDate'] -
        master_status['optimeDate']))

    return lag_in_seconds



########NEW FILE########
__FILENAME__ = server
__author__ = 'abdul'

import os

import mongoctl.repository as repository

from base import DocumentWrapper
from mongoctl.utils import resolve_path, document_pretty_string, is_host_local
from pymongo.errors import AutoReconnect
from mongoctl.mongoctl_logging import (
    log_verbose, log_error, log_warning, log_exception, log_debug
    )
from mongoctl.mongo_version import make_version_info

from mongoctl.config import get_default_users
from mongoctl.errors import MongoctlException
from mongoctl.prompt import read_username, read_password

from bson.son import SON

from pymongo.connection import Connection

import datetime

from mongoctl import config
from mongoctl import users

###############################################################################
# CONSTANTS
###############################################################################

# default pid file name
PID_FILE_NAME = "pid.txt"

LOG_FILE_NAME = "mongodb.log"

KEY_FILE_NAME = "keyFile"

# This is mongodb's default port
DEFAULT_PORT = 27017

# db connection timeout, 10 seconds
CONN_TIMEOUT = 10000


REPL_KEY_SUPPORTED_VERSION = '2.0.0'

EDITION_COMMUNITY = "community"
EDITION_ENTERPRISE = "enterprise"

###############################################################################
# Server Class
###############################################################################

class Server(DocumentWrapper):

    ###########################################################################
    # Constructor
    ###########################################################################
    def __init__(self, server_doc):
        DocumentWrapper.__init__(self, server_doc)
        self.__db_connection__ = None
        self.__seed_users__ = None
        self.__login_users__ = {}
        self.__mongo_version__ = None
        self._connection_address = None

    ###########################################################################
    # Properties
    ###########################################################################

    ###########################################################################
    def get_description(self):
        return self.get_property("description")

    ###########################################################################
    def set_description(self, desc):
        return self.set_property("description", desc)

    ###########################################################################
    def get_server_home(self):
        home_dir = self.get_property("serverHome")
        if home_dir:
            return resolve_path(home_dir)
        else:
            return None

    ###########################################################################
    def set_server_home(self, val):
        self.set_property("serverHome", val)

    ###########################################################################
    def get_pid_file_path(self):
        return self.get_server_file_path("pidfilepath", PID_FILE_NAME)

    ###########################################################################
    def get_log_file_path(self):
        return self.get_server_file_path("logpath", LOG_FILE_NAME)

    ###########################################################################
    def get_key_file(self):
        kf = self.get_cmd_option("keyFile")
        if kf:
            return resolve_path(kf)

    ###########################################################################
    def get_default_key_file_path(self):
        return self.get_server_file_path("keyFile", KEY_FILE_NAME)


    ###########################################################################
    def get_server_file_path(self, cmd_prop, default_file_name):
        file_path = self.get_cmd_option(cmd_prop)
        if file_path is not None:
            return resolve_path(file_path)
        else:
            return self.get_default_file_path(default_file_name)

    ###########################################################################
    def get_default_file_path(self, file_name):
        return self.get_server_home() + os.path.sep + file_name

    ###########################################################################
    def get_address(self):
        address = self.get_property("address")

        if address is not None:
            if address.find(":") > 0:
                return address
            else:
                return "%s:%s" % (address, self.get_port())
        else:
            return None

    ###########################################################################
    def get_address_display(self):
        display = self.get_address()
        if display is None:
            display = self.get_local_address()
        return display

    ###########################################################################
    def get_host_address(self):
        if self.get_address() is not None:
            return self.get_address().split(":")[0]
        else:
            return None

    ###########################################################################
    def get_connection_host_address(self):
        return self.get_connection_address().split(":")[0]

    ###########################################################################
    def set_address(self, address):
        self.set_property("address", address)

    ###########################################################################
    def get_local_address(self):
        return "localhost:%s" % self.get_port()

    ###########################################################################
    def get_port(self):
        port = self.get_cmd_option("port")
        if port is None:
            port = DEFAULT_PORT
        return port

    ###########################################################################
    def set_port(self, port):
        self.set_cmd_option("port", port)

    ###########################################################################
    def is_fork(self):
        fork = self.get_cmd_option("fork")
        return fork or fork is None

    ###########################################################################
    def get_mongo_version(self):
        """
        Gets mongo version of the server if it is running. Otherwise return
         version configured in mongoVersion property
        """
        if self.__mongo_version__:
            return self.__mongo_version__

        if self.is_online():
            mongo_version = self.get_db_connection().server_info()['version']
        else:
            mongo_version = self.get_property("mongoVersion")

        self.__mongo_version__ = mongo_version
        return self.__mongo_version__

    ###########################################################################
    def get_mongo_edition(self):
        return self.get_property("mongoEdition")

    ###########################################################################
    def get_mongo_version_info(self):
        version_number = self.get_mongo_version()
        if version_number is not None:
            return make_version_info(version_number,
                                     edition=self.get_mongo_edition())
        else:
            return None

    ###########################################################################
    def get_cmd_option(self, option_name):
        cmd_options = self.get_cmd_options()

        if cmd_options and cmd_options.has_key(option_name):
            return cmd_options[option_name]
        else:
            return None

    ###########################################################################
    def set_cmd_option(self, option_name, option_value):
        cmd_options = self.get_cmd_options()

        if cmd_options:
            cmd_options[option_name] = option_value

    ###########################################################################
    def get_cmd_options(self):
        return self.get_property('cmdOptions')

    ###########################################################################
    def set_cmd_options(self, cmd_options):
        return self.set_property('cmdOptions' , cmd_options)

    ###########################################################################
    def export_cmd_options(self, options_override=None):
        cmd_options =  self.get_cmd_options().copy()
        # reset some props to exporting vals
        cmd_options['pidfilepath'] = self.get_pid_file_path()

            # apply the options override
        if options_override is not None:
            for (option_name, option_val) in options_override.items():
                cmd_options[option_name] = option_val

        # set the logpath if forking..

        if (self.is_fork() or (options_override is not None and
                               options_override.get("fork"))):
            cmd_options['fork'] = True
            if "logpath" not in cmd_options:
                cmd_options["logpath"] = self.get_log_file_path()

        # Specify the keyFile arg if needed
        if self.needs_repl_key() and "keyFile" not in cmd_options:
            key_file_path = (self.get_key_file() or
                             self.get_default_key_file_path())
            cmd_options["keyFile"] = key_file_path
        return cmd_options

    ###########################################################################
    def get_seed_users(self):

        if self.__seed_users__ is None:
            seed_users = self.get_property('seedUsers')

            ## This hidden for internal user and should not be documented
            if not seed_users:
                seed_users = get_default_users()

            self.__seed_users__ = seed_users

        return self.__seed_users__

    ###########################################################################
    def get_login_user(self, dbname):
        login_user =  self.__login_users__.get(dbname)
        # if no login user found then check global login

        if not login_user:
            login_user = users.get_global_login_user(self, dbname)

        # if dbname is local and we cant find anything yet
        # THEN assume that local credentials == admin credentials
        if not login_user and dbname == "local":
            login_user = self.get_login_user("admin")

        return login_user

    ###########################################################################
    def lookup_password(self, dbname, username):
        # look in seed users
        db_seed_users = self.get_db_seed_users(dbname)
        if db_seed_users:
            user = filter(lambda user: user['username'] == username,
                        db_seed_users)
            if user and "password" in user[0]:
                return user[0]["password"]

    ###########################################################################
    def set_login_user(self, dbname, username, password):
        self.__login_users__[dbname] = {
            "username": username,
            "password": password
        }

    ###########################################################################
    def get_admin_users(self):
        return self.get_db_seed_users("admin")

    ###########################################################################
    def get_db_seed_users(self, dbname):
        return self.get_seed_users().get(dbname)

    ###########################################################################
    def get_cluster(self):
        return repository.lookup_cluster_by_server(self)

    ###########################################################################
    def get_validate_cluster(self):
        cluster = repository.lookup_cluster_by_server(self)
        if not cluster:
            raise MongoctlException("No cluster found for server '%s'" %
                                    self.id)
        repository.validate_cluster(cluster)
        return cluster

    ###########################################################################
    def is_cluster_member(self):
        return self.get_cluster() is not None

    ###########################################################################
    # DB Methods
    ###########################################################################

    def disconnecting_db_command(self, cmd, dbname):
        try:
            result = self.db_command(cmd, dbname)
            return result
        except AutoReconnect,e:
            log_verbose("This is an expected exception that happens after "
                        "disconnecting db commands: %s" % e)
        finally:
            self.__db_connection__ = None

    ###########################################################################
    def timeout_maybe_db_command(self, cmd, dbname):
        try:
            result = self.db_command(cmd, dbname)
            return result
        except Exception, e:
            log_exception(e)
            if "timed out" in str(e):
                log_warning("Command %s is taking a while to complete. "
                            "This is not necessarily bad. " %
                            document_pretty_string(cmd))
            else:
                raise
        finally:
            self.__db_connection__ = None

    ###########################################################################
    def db_command(self, cmd, dbname):

        need_auth = self.command_needs_auth(dbname, cmd)
        db = self.get_db(dbname, no_auth=not need_auth)
        return db.command(cmd)

    ###########################################################################
    def command_needs_auth(self, dbname, cmd):
        return self.needs_to_auth(dbname)

    ###########################################################################
    def get_db(self, dbname, no_auth=False, username=None, password=None,
               retry=True, never_auth_with_admin=False):

        conn = self.get_db_connection()
        db = conn[dbname]

        # If the DB doesn't need to be authenticated to (or at least yet)
        # then don't authenticate. this piece of code is important for the case
        # where you are connecting to the DB on local host where --auth is on
        # but there are no admin users yet
        if no_auth:
            return db

        if (not username and
                (not self.needs_to_auth(dbname))):
            return db

        if username:
            self.set_login_user(dbname, username, password)

        login_user = self.get_login_user(dbname)

        # if there is no login user for this database then use admin db unless
        # it was specified not to
        # ALSO use admin if this is 'local' db for mongodb >= 2.6.0
        if ((not never_auth_with_admin and
                not login_user and
                    dbname not in ["admin", "local"]) or
                (dbname == "local" and
                     not users.server_supports_local_users(self))):
            # if this passes then we are authed!
            admin_db = self.get_db("admin", retry=retry)
            return admin_db.connection[dbname]

        auth_success = self.authenticate_db(db, dbname, retry=retry)

        # If auth failed then give it a try by auth into admin db unless it
        # was specified not to
        if (not never_auth_with_admin and
                not auth_success
            and dbname != "admin"):
            admin_db = self.get_db("admin", retry=retry)
            return admin_db.connection[dbname]

        if auth_success:
            return db
        else:
            raise MongoctlException("Failed to authenticate to %s db" % dbname)

    ###########################################################################
    def authenticate_db(self, db, dbname, retry=True):
        """
        Returns True if we manage to auth to the given db, else False.
        """
        login_user = self.get_login_user(dbname)
        username = None
        password = None


        auth_success = False

        if login_user:
            username = login_user["username"]
            if "password" in login_user:
                password = login_user["password"]

        # have three attempts to authenticate
        no_tries = 0

        while not auth_success and no_tries < 3:
            if not username:
                username = read_username(dbname)
            if not password:
                password = self.lookup_password(dbname, username)
                if not password:
                    password = read_password("Enter password for user '%s\%s'"%
                                             (dbname, username))

            # if auth success then exit loop and memoize login
            auth_success = db.authenticate(username, password)
            if auth_success or not retry:
                break
            else:
                log_error("Invalid login!")
                username = None
                password = None

            no_tries += 1

        if auth_success:
            self.set_login_user(dbname, username, password)

        return auth_success

    ###########################################################################
    def get_working_login(self, database, username=None, password=None):
        """
            authenticate to the specified database starting with specified
            username/password (if present), try to return a successful login
            within 3 attempts
        """
        login_user = None


        #  this will authenticate and update login user
        self.get_db(database, username=username, password=password,
                    never_auth_with_admin=True)

        login_user = self.get_login_user(database)

        if login_user:
            username = login_user["username"]
            password = (login_user["password"] if "password" in login_user
                        else None)
        return username, password

    ###########################################################################
    def is_online(self):
        try:
            self.new_db_connection()
            return True
        except Exception, e:
            log_exception(e)
            return False

    ###########################################################################
    def can_function(self):
        status = self.get_status()
        if status['connection']:
            if 'error' not in status:
                return True
            else:
                log_verbose("Error while connecting to server '%s': %s " %
                            (self.id, status['error']))

    ###########################################################################
    def is_online_locally(self):
        return self.is_use_local() and self.is_online()

    ###########################################################################
    def is_use_local(self):
        return (self.get_address() is None or
                is_assumed_local_server(self.id)
                or self.is_local())

    ###########################################################################
    def is_local(self):
        try:
            server_host = self.get_host_address()
            return server_host is None or is_host_local(server_host)
        except Exception, e:
            log_exception(e)
            log_error("Unable to resolve address '%s' for server '%s'."
                      " Cause: %s" %
                      (self.get_host_address(), self.id, e))
        return False

    ###########################################################################
    def needs_to_auth(self, dbname):
        """
        Determines if the server needs to authenticate to the database.
        NOTE: we stopped depending on is_auth() since its only a configuration
        and may not be accurate
        """
        log_debug("Checking if server '%s' needs to auth on  db '%s'...." %
                  (self.id, dbname))
        try:
            conn = self.new_db_connection()
            db = conn[dbname]
            db.collection_names()
            result = False
        except (RuntimeError,Exception), e:
            log_exception(e)
            result = "authorized" in str(e)

        log_debug("needs_to_auth check for server '%s'  on db '%s' : %s" %
                  (self.id, dbname, result))
        return result

    ###########################################################################
    def get_status(self, admin=False):
        status = {}
        ## check if the server is online
        try:
            self.get_db_connection()
            status['connection'] = True

            # grab status summary if it was specified + if i am not an arbiter
            if admin:
                server_summary = self.get_server_status_summary()
                status["serverStatusSummary"] = server_summary

        except (RuntimeError, Exception), e:
            log_exception(e)
            self.sever_db_connection()   # better luck next time!
            status['connection'] = False
            status['error'] = "%s" % e
            if "timed out" in status['error']:
                status['timedOut'] = True
        return status

    ###########################################################################
    def get_server_status_summary(self):
        server_status = self.db_command(SON([('serverStatus', 1)]), "admin")
        server_summary = {
            "host": server_status['host'],
            "connections": server_status['connections'],
            "version": server_status['version']
        }
        return server_summary

    ###########################################################################
    def get_db_connection(self):
        if self.__db_connection__ is None:
            self.__db_connection__  = self.new_db_connection()
        return self.__db_connection__

    ###########################################################################
    def sever_db_connection(self):
        if self.__db_connection__ is not None:
            self.__db_connection__.close()
        self.__db_connection__ = None

    ###########################################################################
    def new_db_connection(self):
        return self.make_db_connection(self.get_connection_address())

    ###########################################################################
    def get_connection_address(self):

        if self._connection_address:
            return self._connection_address

        # try to get the first working connection address
        if (self.is_use_local() and
                self.has_connectivity_on(self.get_local_address())):
            self._connection_address = self.get_local_address()
        elif self.has_connectivity_on(self.get_address()):
            self._connection_address = self.get_address()

        # use old logic
        if not self._connection_address:
            if self.is_use_local():
                self._connection_address = self.get_local_address()
            else:
                self._connection_address = self.get_address()

        return self._connection_address

    ###########################################################################
    def make_db_connection(self, address):

        try:
            return Connection(address,
                              socketTimeoutMS=CONN_TIMEOUT,
                              connectTimeoutMS=CONN_TIMEOUT)
        except Exception, e:
            log_exception(e)
            error_msg = "Cannot connect to '%s'. Cause: %s" % \
                        (address, e)
            raise MongoctlException(error_msg,cause=e)

    ###########################################################################
    def has_connectivity_on(self, address):

        try:
            log_verbose("Checking if server '%s' is accessible on "
                        "address '%s'" % (self.id, address))
            self.make_db_connection(address)
            return True
        except Exception, e:
            log_exception(e)
            log_verbose("Check failed for server '%s' is accessible on "
                        "address '%s': %s" % (self.id, address, e))
            return False

    ###########################################################################
    def get_rs_config(self):
        try:
            return self.get_db('local')['system.replset'].find_one()
        except (Exception,RuntimeError), e:
            log_exception(e)
            if type(e) == MongoctlException:
                raise e
            else:
                log_verbose("Cannot get rs config from server '%s'. "
                            "cause: %s" % (self.id, e))
                return None

    ###########################################################################
    def validate_local_op(self, op):

        # If the server has been assumed to be local then skip validation
        if is_assumed_local_server(self.id):
            log_verbose("Skipping validation of server's '%s' address '%s' to be"
                        " local because --assume-local is on" %
                        (self.id, self.get_host_address()))
            return

        log_verbose("Validating server address: "
                    "Ensuring that server '%s' address '%s' is local on this "
                    "machine" % (self.id, self.get_host_address()))
        if not self.is_local():
            log_verbose("Server address validation failed.")
            raise MongoctlException("Cannot %s server '%s' on this machine "
                                    "because server's address '%s' does not appear "
                                    "to be local to this machine. Pass the "
                                    "--assume-local option if you are sure that "
                                    "this server should be running on this "
                                    "machine." % (op,
                                                  self.id,
                                                  self.get_host_address()))
        else:
            log_verbose("Server address validation passed. "
                        "Server '%s' address '%s' is local on this "
                        "machine !" % (self.id, self.get_host_address()))


    ###########################################################################
    def log_server_activity(self, activity):

        if is_logging_activity():
            log_record = {"op": activity,
                          "ts": datetime.datetime.utcnow(),
                          "serverDoc": self.get_document(),
                          "server": self.id,
                          "serverDisplayName": self.get_description()}
            log_verbose("Logging server activity \n%s" %
                        document_pretty_string(log_record))

            repository.get_activity_collection().insert(log_record)

    ###########################################################################
    def needs_repl_key(self):
        """
         We need a repl key if you are auth + a cluster member +
         version is None or >= 2.0.0
        """
        cluster = self.get_cluster()
        return (self.supports_repl_key() and
                cluster is not None and cluster.get_repl_key() is not None)

    ###########################################################################
    def supports_repl_key(self):
        """
         We need a repl key if you are auth + a cluster member +
         version is None or >= 2.0.0
        """
        version = self.get_mongo_version_info()
        return (version is None or
                version >= make_version_info(REPL_KEY_SUPPORTED_VERSION))

    ###########################################################################
    def get_pid(self):
        pid_file_path = self.get_pid_file_path()
        if os.path.exists(pid_file_path):
            pid_file = open(pid_file_path, 'r')
            pid = pid_file.readline().strip('\n')
            if pid and pid.isdigit():
                return int(pid)
            else:
                log_warning("Unable to determine pid for server '%s'. "
                            "Not a valid number in '%s"'' %
                            (self.id, pid_file_path))
        else:
            log_warning("Unable to determine pid for server '%s'. "
                        "pid file '%s' does not exist" %
                        (self.id, pid_file_path))

        return None

###############################################################################
def is_logging_activity():
    return (repository.consulting_db_repository() and
            config.get_mongoctl_config_val("logServerActivity" , False))

###############################################################################
__assumed_local_servers__ = []

def assume_local_server(server_id):
    global __assumed_local_servers__
    if server_id not in __assumed_local_servers__:
        __assumed_local_servers__.append(server_id)

###############################################################################
def is_assumed_local_server(server_id):
    global __assumed_local_servers__
    return server_id in __assumed_local_servers__

########NEW FILE########
__FILENAME__ = sharded_cluster
__author__ = 'abdul'

import mongoctl.repository as repository

from cluster import Cluster
from server import Server

from base import DocumentWrapper
from bson import DBRef

from mongoctl.mongoctl_logging import log_info
from mongoctl.utils import document_pretty_string

import time
###############################################################################
# ShardSet Cluster Class
###############################################################################
class ShardedCluster(Cluster):

    ###########################################################################
    # Constructor and other init methods
    ###########################################################################
    def __init__(self, cluster_document):
        Cluster.__init__(self, cluster_document)
        self._config_members = self._resolve_members("configServers")
        self._shards = self._resolve_shard_members()

    ###########################################################################
    def _resolve_shard_members(self):
        member_documents = self.get_property("shards")
        members = []

        # if members are not set then return
        if member_documents:
            for mem_doc in member_documents:
                member = ShardMember(mem_doc)
                members.append(member)

        return members

    ###########################################################################
    @property
    def config_members(self):
        return self._config_members

    ###########################################################################
    def has_config_server(self, server):
        for member in self.config_members:
            if member.get_server().id == server.id:
                return True

    ###########################################################################
    @property
    def shards(self):
        return self._shards

    ###########################################################################
    def has_shard(self, shard):
        return self.get_shard_member(shard) is not None

    ###########################################################################
    def get_shard_member(self, shard):
        for shard_member in self.shards:
            if ((isinstance(shard, Server) and
                 shard_member.get_server() and
                 shard_member.get_server().id == shard.id)
                or
                (isinstance(shard, Cluster) and
                 shard_member.get_cluster() and
                 shard_member.get_cluster().id == shard.id)):
                return shard_member

    ###########################################################################
    def get_shard_member_by_shard_id(self, shard_id):
        for shard_member in self.shards:
            if ((shard_member.get_server() and
                         shard_member.get_server().id == shard_id)
                or (shard_member.get_cluster() and
                            shard_member.get_cluster().id == shard_id)):
                return shard_member
    ###########################################################################
    def get_config_member_addresses(self):
        addresses = []
        for member in self.config_members:
            addresses.append(member.get_server().get_address())

        return addresses

    ###########################################################################
    def get_member_addresses(self):
        addresses = []
        for member in self.config_members:
            addresses.append(member.get_server().get_address())

        return addresses

    ###########################################################################
    def get_shard_member_address(self, shard_member):

        if shard_member.get_server():
            return shard_member.get_server().get_address()
        elif shard_member.get_cluster():
            cluster_member_addresses = []
            for cluster_member in shard_member.get_cluster().get_members():
                cluster_member_addresses.append(
                    cluster_member.get_server().get_address())
            return "%s/%s" % (shard_member.get_cluster().id,
                              ",".join(cluster_member_addresses))


    ###########################################################################
    def configure_sharded_cluster(self):
        sh_list = self.list_shards()
        if sh_list and sh_list.get("shards"):
            log_info("Shard cluster already configured. Will only be adding"
                     " new shards as needed...")

        for shard_member in self.shards:
            self.add_shard(shard_member.get_shard())

    ###########################################################################
    def add_shard(self, shard):
        log_info("Adding shard '%s' to ShardedCluster '%s' " % (shard.id, self.id))

        if self.is_shard_configured(shard):
            log_info("Shard '%s' already added! Nothing to do..." % shard.id)
            return

        mongos = self.get_any_online_mongos()
        shard_member = self.get_shard_member(shard)
        cmd = self.get_add_shard_command(shard_member)

        configured_shards = self.list_shards()
        log_info("Current configured shards: \n%s" %
                 document_pretty_string(configured_shards))


        log_info("Executing command \n%s\non mongos '%s'" %
                 (document_pretty_string(cmd), mongos.id))
        mongos.db_command(cmd, "admin")

        log_info("Shard '%s' added successfully!" % self.id)

    ###########################################################################
    def get_add_shard_command(self, shard_member):
        return {
            "addShard": self.get_shard_member_address(shard_member)
        }

    ###########################################################################
    def remove_shard(self, shard, unsharded_data_dest_id=None,
                     synchronized=False):
        log_info("Removing shard '%s' from ShardedCluster '%s' " %
                 (shard.id, self.id))

        configured_shards = self.list_shards()
        log_info("Current configured shards: \n%s" %
                 document_pretty_string(configured_shards))

        completed = False
        while not completed:
            result = self._do_remove_shard(shard, unsharded_data_dest_id)
            completed = synchronized and (result["state"] == "completed" or
                                          not self.is_shard_configured(shard))
            if not completed:
                time.sleep(2)

    ###########################################################################

    def _do_remove_shard(self, shard, unsharded_data_dest_id=None):
        cmd = self.get_validate_remove_shard_command(shard)
        mongos = self.get_any_online_mongos()

        log_info("Executing command \n%s\non mongos '%s'" %
                 (document_pretty_string(cmd), mongos.id))

        result = mongos.db_command(cmd, "admin")

        log_info("Command result: \n%s" % result)

        if "dbsToMove" in result and unsharded_data_dest_id:
            dest_shard_member = self.get_shard_member_by_shard_id(
                unsharded_data_dest_id)

            if not dest_shard_member:
                raise Exception("No such shard '%s' in ShardedCluster '%s' " %
                                (unsharded_data_dest_id, self.id))

            dest_shard = dest_shard_member.get_shard()
            self.move_dbs_primary(result["dbsToMove"], dest_shard)


        if result.get('state') == "completed":
            log_info("Shard '%s' removed successfully!" % self.id)

        return result

    ###########################################################################
    def get_validate_remove_shard_command(self, shard):
        if not self.is_shard_configured(shard):
            raise Exception("Bad remove shard attempt. Shard '%s' has not"
                            " been added yet" % shard.id)

        # TODO: re-enable this when  is_last_shard works properly
        # check if its last shard and raise error if so
        ##if self.is_last_shard(shard):
          ##  raise Exception("Bad remove shard attempt. Shard '%s' is the last"
            ##                " shard" % shard.id)
        shard_member = self.get_shard_member(shard)

        return {
            "removeShard": shard_member.get_shard_id()
        }

    ###########################################################################
    def get_remove_shard_command(self, shard):
        return {
            "removeShard": shard.id
        }

    ###########################################################################
    def list_shards(self):
        mongos = self.get_any_online_mongos()
        return mongos.db_command({"listShards": 1}, "admin")

    ###########################################################################
    def is_shard_configured(self, shard):
        shard_list = self.list_shards()
        if shard_list and shard_list.get("shards"):
            for sh in shard_list["shards"]:
                if shard.id == sh["_id"]:
                    return True

    ###########################################################################
    def is_last_shard(self, shard):
        # TODO: implement
        pass

    ###########################################################################
    def get_default_server(self):
        return self.get_any_online_mongos()

    ###########################################################################
    def get_any_online_mongos(self):
        for member in self.get_members():
            if member.get_server().is_online():
                return member.get_server()

        raise Exception("Unable to connect to a mongos")


    ###########################################################################
    def move_dbs_primary(self, db_names, dest_shard):
        log_info("Moving databases %s primary to shard '%s'" %
                 (db_names, dest_shard.id))
        mongos = self.get_any_online_mongos()

        for db_name in db_names:
            move_cmd = {
                "movePrimary": db_name,
                "to": dest_shard.id
            }
            log_info("Executing movePrimary command:\n%s\non mongos '%s'" %
                     (document_pretty_string(move_cmd), mongos.id))

            result = mongos.db_command(move_cmd, "admin")

            log_info("Move result: %s" % document_pretty_string(result))

    ###########################################################################
    def get_member_type(self):
        return ShardMember

###############################################################################
# ShardMember Class
###############################################################################
class ShardMember(DocumentWrapper):
    ###########################################################################
    # Constructor
    ###########################################################################
    def __init__(self, member_doc):
        DocumentWrapper.__init__(self, member_doc)
        self._server = None
        self._cluster = None

    ###########################################################################
    def get_server(self):
        server_doc = self.get_property("server")
        if not server_doc:
            return

        if self._server is None:
            if server_doc is not None:
                if type(server_doc) is DBRef:
                    self._server = repository.lookup_server(server_doc.id)

        return self._server

    ###########################################################################
    def get_cluster(self):
        cluster_doc = self.get_property("cluster")
        if not cluster_doc:
            return

        if self._cluster is None:
            if cluster_doc is not None:
                if type(cluster_doc) is DBRef:
                    self._cluster = repository.lookup_cluster(cluster_doc.id)

        return self._cluster

    ###########################################################################
    def get_shard_id(self):
        return self.get_shard().id

    ###########################################################################
    def get_shard(self):

        if self.get_server():
            return self.get_server()
        elif self.get_cluster():
            return self.get_cluster()


########NEW FILE########
__FILENAME__ = processes
__author__ = 'abdul'

import subprocess
###############################################################################
__child_subprocesses__ = []

def create_subprocess(command, **kwargs):
    child_process = subprocess.Popen(command, **kwargs)

    global __child_subprocesses__
    __child_subprocesses__.append(child_process)

    return child_process

###############################################################################
def communicate_to_child_process(child_pid):
    get_child_process(child_pid).communicate()

###############################################################################
def get_child_process(child_pid):
    global __child_subprocesses__
    for child_process in __child_subprocesses__:
        if child_process.pid == child_pid:
            return child_process

###############################################################################
def get_child_processes():
    global __child_subprocesses__
    return __child_subprocesses__
########NEW FILE########
__FILENAME__ = prompt
__author__ = 'abdul'

import sys
import getpass

from errors import MongoctlException
###############################################################################
# Global flags and their functions
###############################################################################
__interactive_mode__ = True

def set_interactive_mode(value):
    global __interactive_mode__
    __interactive_mode__ = value

###############################################################################
def is_interactive_mode():
    global __interactive_mode__
    return __interactive_mode__

###############################################################################
__say_yes_to_everything__ = False
__say_no_to_everything__ = False

###############################################################################
def say_yes_to_everything():
    global __say_yes_to_everything__
    __say_yes_to_everything__ = True

###############################################################################
def is_say_yes_to_everything():
    global __say_yes_to_everything__
    return __say_yes_to_everything__

###############################################################################
def say_no_to_everything():
    global __say_no_to_everything__
    __say_no_to_everything__ = True

###############################################################################
def is_say_no_to_everything():
    global __say_no_to_everything__
    return __say_no_to_everything__

###############################################################################
def is_interactive_mode():
    global __interactive_mode__
    return __interactive_mode__

###############################################################################
def read_input(message):
    # If we are running in a noninteractive mode then fail
    if not is_interactive_mode():
        msg = ("Error while trying to prompt you for '%s'. Prompting is not "
               "allowed when running with --noninteractive mode. Please pass"
               " enough arguments to bypass prompting or run without "
               "--noninteractive" % message)
        raise MongoctlException(msg)

    print >> sys.stderr, message,
    return raw_input()

###############################################################################
def read_username(dbname):
    # If we are running in a noninteractive mode then fail
    if not is_interactive_mode():
        msg = ("mongoctl needs username in order to proceed. Please pass the"
               " username using the -u option or run without --noninteractive")
        raise MongoctlException(msg)

    return read_input("Enter username for database '%s': " % dbname)

###############################################################################
def read_password(message=''):
    if not is_interactive_mode():
        msg = ("mongoctl needs password in order to proceed. Please pass the"
               " password using the -p option or run without --noninteractive")
        raise MongoctlException(msg)

    print >> sys.stderr, message
    return getpass.getpass()


###############################################################################
def prompt_execute_task(message, task_function):

    yes = prompt_confirm(message)
    if yes:
        return (True,task_function())
    else:
        return (False,None)

###############################################################################
def prompt_confirm(message):

    # return False if noninteractive or --no was specified
    if (not is_interactive_mode() or
            is_say_no_to_everything()):
        return False

    # return True if --yes was specified
    if is_say_yes_to_everything():
        return True

    valid_choices = {"yes":True,
                     "y":True,
                     "ye":True,
                     "no":False,
                     "n":False}

    while True:
        print >> sys.stderr, message + " [y/n] ",
        sys.stderr.flush()
        choice = raw_input().lower()
        if not valid_choices.has_key(choice):
            print >> sys.stderr, ("Please respond with 'yes' or 'no' "
                                  "(or 'y' or 'n').\n")
        elif valid_choices[choice]:
            return True
        else:
            return False

########NEW FILE########
__FILENAME__ = repository


__author__ = 'abdul'

import pymongo
import config

from bson import DBRef

from errors import MongoctlException
from mongoctl_logging import log_warning, log_verbose, log_info, log_exception
from mongo_uri_tools import parse_mongo_uri
from utils import (
    resolve_class, document_pretty_string, is_valid_member_address, listify
    )

from mongo_version import is_supported_mongo_version, is_valid_version
from mongo_uri_tools import is_cluster_mongo_uri, mask_mongo_uri

DEFAULT_SERVERS_FILE = "servers.config"

DEFAULT_CLUSTERS_FILE = "clusters.config"

DEFAULT_SERVERS_COLLECTION = "servers"

DEFAULT_CLUSTERS_COLLECTION = "clusters"

DEFAULT_ACTIVITY_COLLECTION = "logs.server-activity"


LOOKUP_TYPE_MEMBER = "members"
LOOKUP_TYPE_CONFIG_SVR = "configServers"
LOOKUP_TYPE_SHARDS = "shards"
LOOKUP_TYPE_ANY = [LOOKUP_TYPE_CONFIG_SVR, LOOKUP_TYPE_MEMBER,
                   LOOKUP_TYPE_SHARDS]

###############################################################################
# Global variable: mongoctl's mongodb object
__mongoctl_db__ = None

###############################################################################
def get_mongoctl_database():

    # if not using db then return
    if not has_db_repository():
        return

    global __mongoctl_db__

    if __mongoctl_db__ is not None:
        return __mongoctl_db__

    log_verbose("Connecting to mongoctl db...")
    try:

        (conn, dbname) = _db_repo_connect()

        __mongoctl_db__ = conn[dbname]
        return __mongoctl_db__
    except Exception, e:
        log_exception(e)
        __mongoctl_db__ = "OFFLINE"
        log_warning("\n*************\n"
                    "Will not be using database repository for configurations"
                    " at this time!"
                    "\nREASON: Could not establish a database"
                    " connection to mongoctl's database repository."
                    "\nCAUSE: %s."
                    "\n*************" % e)

###############################################################################
def has_db_repository():
    return config.get_database_repository_conf() is not None

###############################################################################
def has_file_repository():
    return config.get_file_repository_conf() is not None

###############################################################################
def consulting_db_repository():
    return has_db_repository() and is_db_repository_online()

###############################################################################
def is_db_repository_online():
    mongoctl_db = get_mongoctl_database()
    return mongoctl_db and mongoctl_db != "OFFLINE"

###############################################################################
def _db_repo_connect():
    db_conf = config.get_database_repository_conf()
    uri = db_conf["databaseURI"]
    conn = pymongo.Connection(uri)
    dbname = parse_mongo_uri(uri).database
    return conn, dbname


###############################################################################
def validate_repositories():
    if ((not has_file_repository()) and
            (not has_db_repository())):
        raise MongoctlException("Invalid 'mongoctl.config': No fileRepository"
                                " or databaseRepository configured. At least"
                                " one repository has to be configured.")

###############################################################################
# Server lookup functions
###############################################################################
def lookup_server(server_id):
    validate_repositories()

    server = None
    # lookup server from the db repo first
    if consulting_db_repository():
        server = db_lookup_server(server_id)

    # if server is not found then try from file repo
    if server is None and has_file_repository():
        server = config_lookup_server(server_id)


    return server

###############################################################################
def lookup_and_validate_server(server_id):
    server = lookup_server(server_id)
    if server is None:
        raise MongoctlException("Cannot find configuration for a server "
                                "with _id of '%s'." % server_id)

    validation_errors = validate_server(server)
    if len(validation_errors) > 0:
        raise MongoctlException(
            "Server '%s' configuration is not valid. Please fix errors below"
            " and try again.\n%s" % (server_id,"\n".join(validation_errors)))

    return server

###############################################################################
def db_lookup_server(server_id):
    server_collection = get_mongoctl_server_db_collection()
    server_doc = server_collection.find_one({"_id": server_id})

    if server_doc:
        return new_server(server_doc)
    else:
        return None

###############################################################################
## Looks up the server from config file
def config_lookup_server(server_id):
    servers = get_configured_servers()
    return servers.get(server_id)

###############################################################################
# returns all servers configured in both DB and config file
def lookup_all_servers():
    validate_repositories()

    all_servers = {}

    if consulting_db_repository():
        all_servers = db_lookup_all_servers()

    if has_file_repository():
        file_repo_servers = get_configured_servers()
        all_servers = dict(file_repo_servers.items() + all_servers.items())

    return all_servers.values()

###############################################################################
# returns servers saved in the db collection of servers
def db_lookup_all_servers():
    servers = get_mongoctl_server_db_collection()
    return new_servers_dict(servers.find())

###############################################################################
# Cluster lookup functions
###############################################################################
def lookup_and_validate_cluster(cluster_id):
    cluster = lookup_cluster(cluster_id)

    if cluster is None:
        raise MongoctlException("Unknown cluster: %s" % cluster_id)

    validate_cluster(cluster)

    return cluster

###############################################################################
# Lookup by cluster id
def lookup_cluster(cluster_id):
    validate_repositories()
    cluster = None
    # lookup cluster from the db repo first

    if consulting_db_repository():
        cluster = db_lookup_cluster(cluster_id)

    # if cluster is not found then try from file repo
    if cluster is None and has_file_repository():
        cluster = config_lookup_cluster(cluster_id)

    return cluster

###############################################################################
# Looks up the server from config file
def config_lookup_cluster(cluster_id):
    clusters = get_configured_clusters()
    return clusters.get(cluster_id)

###############################################################################
def db_lookup_cluster(cluster_id):
    cluster_collection = get_mongoctl_cluster_db_collection()
    cluster_doc = cluster_collection.find_one({"_id": cluster_id})

    if cluster_doc is not None:
        return new_cluster(cluster_doc)
    else:
        return None

###############################################################################
# returns all clusters configured in both DB and config file
def lookup_all_clusters():
    validate_repositories()
    all_clusters = {}

    if consulting_db_repository():
        all_clusters = db_lookup_all_clusters()

    if has_file_repository():
        all_clusters = dict(get_configured_clusters().items() +
                            all_clusters.items())

    return all_clusters.values()

###############################################################################
# returns a dictionary of (cluster_id, cluster) looked up from DB
def db_lookup_all_clusters():
    clusters = get_mongoctl_cluster_db_collection()
    return new_replicaset_clusters_dict(clusters.find())

###############################################################################
# Lookup by server id
def db_lookup_cluster_by_server(server, lookup_type=LOOKUP_TYPE_ANY):
    cluster_collection = get_mongoctl_cluster_db_collection()
    lookup_type = listify(lookup_type)
    type_query =[]
    for t in lookup_type:
        prop_query = {"%s.server.$id" % t: server.id}
        type_query.append(prop_query)

    query = {
        "$or": type_query
    }

    cluster_doc = cluster_collection.find_one(query)

    if cluster_doc is not None:
        return new_cluster(cluster_doc)
    else:
        return None


###############################################################################
# Lookup by server id
def db_lookup_cluster_by_shard(shard):
    cluster_collection = get_mongoctl_cluster_db_collection()

    query = {
        "shards.cluster.$id": shard.id
    }

    cluster_doc = cluster_collection.find_one(query)

    if cluster_doc is not None:
        return new_cluster(cluster_doc)
    else:
        return None



###############################################################################
def config_lookup_cluster_by_server(server, lookup_type=LOOKUP_TYPE_ANY):
    clusters = get_configured_clusters()
    lookup_type = listify(lookup_type)

    for t in lookup_type:
        result = None
        if t == LOOKUP_TYPE_MEMBER:
            result = filter(lambda c: c.has_member_server(server),
                            clusters.values())
        elif t == LOOKUP_TYPE_CONFIG_SVR:
            result = filter(lambda c: cluster_has_config_server(c, server),
                            clusters.values())
        elif t == LOOKUP_TYPE_SHARDS:
            result = filter(lambda c: cluster_has_shard(c, server),
                            clusters.values())
        if result:
            return result[0]

###############################################################################
def config_lookup_cluster_by_shard(shard):
    clusters = get_configured_clusters()

    result = filter(lambda c: cluster_has_shard(c, shard), clusters.values())
    if result:
        return result[0]

###############################################################################
def cluster_has_config_server(cluster, server):
    config_servers = cluster.get_property("configServers")
    if config_servers:
        for server_doc in config_servers:
            server_ref = server_doc["server"]
            if isinstance(server_ref, DBRef) and server_ref.id == server.id:
                return cluster

###############################################################################
def cluster_has_shard(cluster, shard):
    from objects.server import Server
    shards = cluster.get_property("shards")
    if shards:
        for shard_doc in shards:
            if isinstance(shard, Server):
                ref = shard_doc.get("server")
            else:
                ref = shard_doc.get("cluster")
            if isinstance(ref, DBRef) and ref.id == shard.id:
                return cluster

###############################################################################
# Global variable: lazy loaded map that holds servers read from config file
__configured_servers__ = None

###############################################################################
def get_configured_servers():

    global __configured_servers__

    if __configured_servers__ is None:
        __configured_servers__ = {}

        file_repo_conf = config.get_file_repository_conf()
        servers_path_or_url = file_repo_conf.get("servers",
                                                 DEFAULT_SERVERS_FILE)

        server_documents = config.read_config_json("servers",
                                                   servers_path_or_url)
        if not isinstance(server_documents, list):
            raise MongoctlException("Server list in '%s' must be an array" %
                                    servers_path_or_url)
        for document in server_documents:
            server = new_server(document)
            __configured_servers__[server.id] = server

    return __configured_servers__


###############################################################################
# Global variable: lazy loaded map that holds clusters read from config file
__configured_clusters__ = None

###############################################################################
def get_configured_clusters():

    global __configured_clusters__

    if __configured_clusters__ is None:
        __configured_clusters__ = {}

        file_repo_conf = config.get_file_repository_conf()
        clusters_path_or_url = file_repo_conf.get("clusters",
                                                  DEFAULT_CLUSTERS_FILE)

        cluster_documents = config.read_config_json("clusters",
                                                    clusters_path_or_url)
        if not isinstance(cluster_documents, list):
            raise MongoctlException("Cluster list in '%s' must be an array" %
                                    clusters_path_or_url)
        for document in cluster_documents:
            cluster = new_cluster(document)
            __configured_clusters__[cluster.id] = cluster

    return __configured_clusters__

###############################################################################
def validate_cluster(cluster):
    log_info("Validating cluster '%s'..." % cluster.id )

    errors = []

    if isinstance(cluster, replicaset_cluster_type()):
        errors.extend(validate_replicaset_cluster(cluster))
    elif isinstance(cluster, sharded_cluster_type()):
        errors.extend(validate_sharded_cluster(cluster))

    if len(errors) > 0:
        raise MongoctlException("Cluster %s configuration is not valid. "
                                "Please fix errors below and try again.\n%s" %
                                (cluster.id , "\n".join(errors)))

    return cluster

###############################################################################
def validate_replicaset_cluster(cluster):
    errors = []
    return errors

###############################################################################
def validate_sharded_cluster(cluster):
    errors = []
    if not cluster.config_members or len(cluster.config_members) not in [1,3]:
        errors.append("Need 1 or 3 configServers configured in your cluster")

    return errors

###############################################################################
def lookup_validate_cluster_by_server(server):
    cluster = lookup_cluster_by_server(server)

    if cluster is not None:
        validate_cluster(cluster)

    return cluster

###############################################################################
def lookup_cluster_by_server(server, lookup_type=LOOKUP_TYPE_ANY):
    validate_repositories()
    cluster = None

    ## Look for the cluster in db repo
    if consulting_db_repository():
        cluster = db_lookup_cluster_by_server(server, lookup_type=lookup_type)

    ## If nothing is found then look in file repo
    if cluster is None and has_file_repository():
        cluster = config_lookup_cluster_by_server(server,
                                                  lookup_type=lookup_type)


    return cluster


###############################################################################
def lookup_cluster_by_shard(shard):
    validate_repositories()
    cluster = None

    ## Look for the cluster in db repo
    if consulting_db_repository():
        cluster = db_lookup_cluster_by_shard(shard)

    ## If nothing is found then look in file repo
    if cluster is None and has_file_repository():
        cluster = config_lookup_cluster_by_shard(shard)

    return cluster

###############################################################################
def validate_server(server):
    errors = []

    version = server.get_mongo_version()
    # None versions are ok
    if version is not None:
        if not is_valid_version(version):
            errors.append("** Invalid mongoVersion value '%s'" % version)
        elif not is_supported_mongo_version(version):
            errors.append("** mongoVersion '%s' is not supported. Please refer"
                          " to mongoctl documentation for supported"
                          " versions." % version)
    return errors

###############################################################################
def get_mongoctl_server_db_collection():

    mongoctl_db = get_mongoctl_database()
    conf = config.get_database_repository_conf()

    server_collection_name = conf.get("servers", DEFAULT_SERVERS_COLLECTION)

    return mongoctl_db[server_collection_name]

###############################################################################
def get_mongoctl_cluster_db_collection():

    mongoctl_db = get_mongoctl_database()
    conf = config.get_database_repository_conf()
    cluster_collection_name = conf.get("clusters", DEFAULT_CLUSTERS_COLLECTION)

    return mongoctl_db[cluster_collection_name]

###############################################################################
def get_activity_collection():

    mongoctl_db = get_mongoctl_database()

    activity_coll_name = config.get_mongoctl_config_val(
        'activityCollectionName', DEFAULT_ACTIVITY_COLLECTION)

    return mongoctl_db[activity_coll_name]


###############################################################################
# Factory Functions
###############################################################################
def new_server(server_doc):
    _type = server_doc.get("_type")

    if _type is None or _type in SERVER_TYPE_MAP:
        clazz = resolve_class(SERVER_TYPE_MAP.get(_type,
                                                  MONGOD_SERVER_CLASS_NAME))
    else:
        raise MongoctlException("Unknown server _type '%s' for server:\n%s" %
                                (_type, document_pretty_string(server_doc)))

    return clazz(server_doc)

MONGOD_SERVER_CLASS_NAME = "mongoctl.objects.mongod.MongodServer"
MONGOS_ROUTER_CLASS_NAME = "mongoctl.objects.mongos.MongosServer"
SERVER_TYPE_MAP = {
    "Mongod": MONGOD_SERVER_CLASS_NAME,
    "ConfigMongod": MONGOD_SERVER_CLASS_NAME,
    "Mongos": MONGOS_ROUTER_CLASS_NAME,
    # === XXX deprecated XXX ===
    "mongod": MONGOD_SERVER_CLASS_NAME,  # XXX deprecated
    "mongos": MONGOS_ROUTER_CLASS_NAME,  # XXX deprecated
}


###############################################################################
def build_server_from_address(address):
    if not is_valid_member_address(address):
        return None

    port = int(address.split(":")[1])
    server_doc = {"_id": address,
                  "address": address,
                  "cmdOptions":{
                      "port": port
                  }}
    return new_server(server_doc)

###############################################################################
def build_server_from_uri(uri):
    uri_wrapper = parse_mongo_uri(uri)
    node = uri_wrapper.node_list[0]
    host = node[0]
    port = node[1]

    database = uri_wrapper.database or "admin"
    username = uri_wrapper.username
    password = uri_wrapper.password

    address = "%s:%s" % (host, port)
    server = build_server_from_address(address)

    # set login user if specified
    if username:
        server.set_login_user(database, username, password)

    return server

###############################################################################
def build_cluster_from_uri(uri):
    uri_wrapper = parse_mongo_uri(uri)
    database = uri_wrapper.database or "admin"
    username = uri_wrapper.username
    password = uri_wrapper.password

    nodes = uri_wrapper.node_list
    cluster_doc = {
        "_id": mask_mongo_uri(uri)
    }
    member_doc_list = []

    for node in nodes:
        host = node[0]
        port = node[1]
        member_doc = {
            "host": "%s:%s" % (host, port)
        }
        member_doc_list.append(member_doc)

    cluster_doc["members"] = member_doc_list

    cluster = new_cluster(cluster_doc)

    # set login user if specified
    if username:
        for member in cluster.get_members():
            member.get_server().set_login_user(database, username, password)

    return cluster

###############################################################################
def build_server_or_cluster_from_uri(uri):
    if is_cluster_mongo_uri(uri):
        return build_cluster_from_uri(uri)
    else:
        return build_server_from_uri(uri)

###############################################################################
def new_servers_dict(docs):
    d = {}
    map(lambda doc: d.update({doc['_id']: new_server(doc)}), docs)
    return d

###############################################################################
def new_cluster(cluster_doc):
    _type = cluster_doc.get("_type")

    if _type is None or _type == "ReplicaSetCluster":
        clazz = replicaset_cluster_type()
    elif _type == "ShardedCluster":
        clazz = sharded_cluster_type()
    else:
        raise MongoctlException("Unknown cluster _type '%s' for server:\n%s" %
                                (_type, document_pretty_string(cluster_doc)))
    return clazz(cluster_doc)

###############################################################################
def new_replicaset_clusters_dict(docs):
    d = {}
    map(lambda doc: d.update({doc['_id']: new_cluster(doc)}), docs)
    return d

###############################################################################
def new_replicaset_cluster_member(cluster_mem_doc):
    mem_type = "mongoctl.objects.replicaset_cluster.ReplicaSetClusterMember"
    clazz = resolve_class(mem_type)
    return clazz(cluster_mem_doc)

###############################################################################
def new_replicaset_cluster_member_list(docs_iteratable):
    return map(new_replicaset_cluster_member, docs_iteratable)

def replicaset_cluster_type():
    return resolve_class("mongoctl.objects.replicaset_cluster."
                         "ReplicaSetCluster")

def sharded_cluster_type():
    return resolve_class("mongoctl.objects.sharded_cluster.ShardedCluster")

########NEW FILE########
__FILENAME__ = auth_replicaset_test
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import time

from mongoctl.tests.test_base import MongoctlTestBase

class AuthReplicasetTest(MongoctlTestBase):

    def test_auth_replicaset(self):
        # assert that all servers are down
        self.assert_server_stopped("auth_arbiter_test_server")
        self.assert_server_stopped("auth_node1_test_server")
        self.assert_server_stopped("auth_node2_test_server")
        # start all servers and make sure they started...
        self.assert_start_server("auth_arbiter_test_server")
        self.assert_server_running("auth_arbiter_test_server")

        self.assert_start_server("auth_node1_test_server")
        self.assert_server_running("auth_node1_test_server")

        self.assert_start_server("auth_node2_test_server")
        self.assert_server_running("auth_node2_test_server")

        # Configure the cluster
        self.mongoctl_assert_cmd("configure-cluster AuthReplicasetTestCluster"
                                 " -u abdulito")

        print "Sleeping for 2 seconds..."
        # sleep for a couple of seconds
        time.sleep(2)
        # RE-Configure the cluster
        self.mongoctl_assert_cmd("configure-cluster AuthReplicasetTestCluster"
                                 " -u abdulito")

        print ("Sleeping for 15 seconds. Hopefully credentials would "
              "be replicated by then. If not then authentication will fail and"
              " passwords will be prompted and then the test will fail...")
        # sleep for a couple of seconds
        time.sleep(15)

        ## Stop all servers
        self.assert_stop_server("auth_arbiter_test_server")
        self.assert_server_stopped("auth_arbiter_test_server")

        self.assert_stop_server("auth_node1_test_server", force=True)
        self.assert_server_stopped("auth_node1_test_server")

        self.assert_stop_server("auth_node2_test_server", force=True)
        self.assert_server_stopped("auth_node2_test_server")

    ###########################################################################
    def get_my_test_servers(self):
        return ["auth_arbiter_test_server",
                "auth_node1_test_server",
                "auth_node2_test_server"]

# booty
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = basic_test
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import unittest

from mongoctl.tests.test_base import MongoctlTestBase

class BasicMongoctlTest(MongoctlTestBase):

    def test_start_stop_server(self):
        self.assert_server_stopped("simple_test_server")
        self.assert_start_server("simple_test_server")
        self.assert_server_running("simple_test_server")
        self.assert_stop_server("simple_test_server")
        self.assert_server_stopped("simple_test_server")

    ###########################################################################
    def test_restart_server(self):
        self.assert_server_stopped("simple_test_server")
        self.assert_restart_server("simple_test_server")
        self.assert_restart_server("simple_test_server")
        self.assert_restart_server("simple_test_server")
        self.assert_server_running("simple_test_server")
        self.assert_stop_server("simple_test_server")
        self.assert_server_stopped("simple_test_server")

    ###########################################################################
    def get_my_test_servers(self):
        return ["simple_test_server"]
# booty
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = install_test
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest

import os
import shutil
import mongoctl.config as config

from mongoctl.tests.test_base import MongoctlTestBase

TEMP_MONGO_INSTALL_DIR = "temp_mongo_installs_dir"
MONGO_INSTALL_DIR = config.get_mongodb_installs_dir()
class InstallTest(MongoctlTestBase):

###########################################################################
    def setUp(self):
        print ("setUp(): Temporarily setting mongoDBInstallationsDirectory=%s" %
               TEMP_MONGO_INSTALL_DIR)

        config.set_mongodb_installs_dir(TEMP_MONGO_INSTALL_DIR)
        super(InstallTest, self).setUp()

    ###########################################################################
    def tearDown(self):
        super(InstallTest, self).tearDown()
        if os.path.exists(TEMP_MONGO_INSTALL_DIR):
            print ("tearDown(): Deleting temp mongoDBInstallationsDirectory=%s" %
                   TEMP_MONGO_INSTALL_DIR)
            shutil.rmtree(TEMP_MONGO_INSTALL_DIR)

        print ("tearDown(): Resetting  mongoDBInstallationsDirectory back to"
               " '%s'" % MONGO_INSTALL_DIR)

        config.set_mongodb_installs_dir(MONGO_INSTALL_DIR)

    ###########################################################################
    def test_install(self):

        # install and list
        self.mongoctl_assert_cmd("list-versions")
        self.mongoctl_assert_cmd("install 2.0.3")
        self.mongoctl_assert_cmd("list-versions")
        self.mongoctl_assert_cmd("install 2.0.4")
        self.mongoctl_assert_cmd("list-versions")
        self.mongoctl_assert_cmd("install 2.0.5")
        self.mongoctl_assert_cmd("list-versions")

        # uninstall and list
        self.mongoctl_assert_cmd("uninstall 2.0.3")
        self.mongoctl_assert_cmd("list-versions")
        self.mongoctl_assert_cmd("uninstall 2.0.4")
        self.mongoctl_assert_cmd("list-versions")
        self.mongoctl_assert_cmd("uninstall 2.0.5")
        self.mongoctl_assert_cmd("list-versions")

    ###########################################################################
# booty
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = master_slave_test
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest

from mongoctl.tests.test_base import MongoctlTestBase

class MasterSlaveTest(MongoctlTestBase):

    def test_master_slave(self):
        # assert servers stopped
        self.assert_server_stopped("master_test_server")
        self.assert_server_stopped("slave_test_server")

        # start master
        self.assert_start_server("master_test_server")
        self.assert_server_running("master_test_server")

        # start slave
        self.assert_start_server("slave_test_server")
        self.assert_server_running("slave_test_server")

        # stop master
        self.assert_stop_server("master_test_server")
        self.assert_server_stopped("master_test_server")

        # stop slave
        self.assert_stop_server("slave_test_server")
        self.assert_server_stopped("slave_test_server")

    ###########################################################################
    def get_my_test_servers(self):
        return ["master_test_server",
                "slave_test_server"]
# booty
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = misc_test
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest

from mongoctl.tests.test_base import MongoctlTestBase

class MiscTest(MongoctlTestBase):

    def test_miscs(self):
        # list servers
        self.mongoctl_assert_cmd("list-servers")
        # list clusters
        self.mongoctl_assert_cmd("list-clusters")
        # show server
        self.mongoctl_assert_cmd("show-server master_test_server")
        # show cluster
        self.mongoctl_assert_cmd("show-cluster ReplicasetTestCluster")

# booty
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = replicaset_test
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
import time

from mongoctl.tests.test_base import MongoctlTestBase

class ReplicasetTest(MongoctlTestBase):

    def test_replicaset(self):
        # assert that all servers are down
        self.assert_server_stopped("arbiter_test_server")
        self.assert_server_stopped("node1_test_server")
        self.assert_server_stopped("node2_test_server")
        # start all servers and make sure they started...
        self.assert_start_server("arbiter_test_server")
        self.assert_server_running("arbiter_test_server")

        self.assert_start_server("node1_test_server")
        self.assert_server_running("node1_test_server")

        self.assert_start_server("node2_test_server")
        self.assert_server_running("node2_test_server")

        # Configure the cluster
        self.mongoctl_assert_cmd("configure-cluster ReplicasetTestCluster")

        print "Sleeping for 2 seconds..."
        # sleep for a couple of seconds
        time.sleep(2)
        # RE-Configure the cluster
        self.mongoctl_assert_cmd("configure-cluster ReplicasetTestCluster"
                                 " -u abdulito")

        print "Sleeping for 2 seconds..."
        # sleep for a couple of seconds
        time.sleep(2)

        # reconfigure with FORCE
        self.mongoctl_assert_cmd("configure-cluster ReplicasetTestCluster "
                                 "--force node2_test_server")

        print "Sleeping for 2 seconds..."
        # sleep for a couple of seconds
        time.sleep(2)

        ## Stop all servers
        self.assert_stop_server("arbiter_test_server")
        self.assert_server_stopped("arbiter_test_server")

        self.assert_stop_server("node1_test_server", force=True)
        self.assert_server_stopped("node1_test_server")

        self.assert_stop_server("node2_test_server", force=True)
        self.assert_server_stopped("node2_test_server")

    ###########################################################################
    def get_my_test_servers(self):
        return ["arbiter_test_server",
                "node1_test_server",
                "node2_test_server"]

# booty
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_base
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__author__ = 'abdul'

import unittest
import commands
import inspect
import os
import shutil
import mongoctl.mongoctl as mongoctl_main
from mongoctl.utils import is_pid_alive, kill_process
import traceback

###############################################################################
# Constants
###############################################################################
MONGOCTL_TEST_DBS_DIR_ENV = "MONGOCTL_TEST_DIR"

###############################################################################
# Base test class
###############################################################################
class MongoctlTestBase(unittest.TestCase):

    ###########################################################################
    def setUp(self):
        # set the test dir env
        test_dir = self.get_test_dbs_dir()
        os.environ[MONGOCTL_TEST_DBS_DIR_ENV] = test_dir
        # assure that the testing dir does not exist
        print "--- Creating test db directory %s " % test_dir
        if os.path.exists(test_dir):
            print ("Warning: %s already exists. Deleting and creating"
                   " again..." % test_dir)
            shutil.rmtree(test_dir)

        os.makedirs(test_dir)

        # cleanup pids before running
        self.cleanup_test_server_pids()

    ###########################################################################
    def tearDown(self):
        test_dir = self.get_test_dbs_dir()
        print "Tearing down: Cleaning up all used resources..."
        # delete the database dir when done
        self.cleanup_test_server_pids()

        print "--- Deleting the test db directory %s " % test_dir
        shutil.rmtree(test_dir)

    ###########################################################################
    def cleanup_test_server_pids(self):
        # delete the database dir when done
        print ("Ensuring all test servers processes are killed. "
              "Attempt to force kill all servers...")

        for server_id in self.get_my_test_servers():
            self.quiet_kill_test_server(server_id)

    ###########################################################################
    def quiet_kill_test_server(self, server_id):
        server_ps_output =  commands.getoutput("ps -o pid -o command -ae | "
                                               "grep %s" % server_id)

        pid_lines = server_ps_output.split("\n")

        for line in pid_lines:
            if line == '':
                continue
            pid = line.strip().split(" ")[0]
            if pid == '':
                continue
            pid = int(pid)
            if is_pid_alive(pid):
                print ("PID for server %s is still alive. Killing..." %
                       server_id)
                kill_process(pid, force=True)

    ###########################################################################
    # This should be overridden by inheritors
    def get_my_test_servers(self):
        return []

    ###########################################################################
    def assert_server_running(self, server_id):
        self.assert_server_status(server_id, is_running=True)

    ###########################################################################
    def assert_server_stopped(self, server_id):
        self.assert_server_status(server_id, is_running=False)

    ###########################################################################
    def assert_server_status(self, server_id, is_running):
        status=  self.mongoctl_assert_cmd("status %s -u abdulito" % server_id)
        self.assertEquals(status['connection'], is_running)

    ###########################################################################
    def assert_start_server(self, server_id):
        return self.mongoctl_assert_cmd("start %s -u abdulito" % server_id)

    ###########################################################################
    def assert_stop_server(self, server_id, force=False):

        args = ("--force %s" % server_id) if force else server_id
        return self.mongoctl_assert_cmd("stop %s -u abdulito" % args)

    ###########################################################################
    def assert_restart_server(self, server_id):
        return self.mongoctl_assert_cmd("restart %s -u abdulito" % server_id)

    ###########################################################################
    def mongoctl_assert_cmd(self, cmd, exit_code=0):
        return self.exec_assert_cmd(self.to_mongoctl_test_command(cmd))

    ###########################################################################
    def exec_assert_cmd(self, cmd, exit_code=0):
        print "++++++++++ Testing command : %s" % cmd

        try:
            return mongoctl_main.do_main(cmd.split(" ")[1:])
        except Exception, e:
            print("Error while executing test command '%s'. Cause: %s " %
                  (cmd, e))
            print "================= STACK TRACE ================"
            traceback.print_exc()
            print "Failing..."
            self.fail()

    ###########################################################################
    def quiet_exec_cmd(self, cmd, exit_code=0):
        print "Quiet Executing command : %s" % cmd

        try:
            return mongoctl_main.do_main(cmd.split(" ")[1:])
        except Exception, e:
            print("WARNING: failed to quiet execute command '%s'. Cause: %s " %
                  (cmd, e))

    ###########################################################################
    def to_mongoctl_test_command(self,cmd):
        return ("mongoctl -v --yes --config-root %s %s" %
                (self.get_testing_conf_root(), cmd))

    ###########################################################################
    def get_testing_conf_root(self):
        tests_pkg_path = os.path.dirname(
            inspect.getfile(inspect.currentframe()))
        return os.path.join(tests_pkg_path, "testing_conf")

    ###########################################################################
    def get_test_dbs_dir(self):
        return os.path.join(self.get_testing_conf_root(), "mongoctltest_dbs")
########NEW FILE########
__FILENAME__ = test_suite
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import unittest

from version_functions_test import VersionFunctionsTest
from basic_test import BasicMongoctlTest
from master_slave_test import MasterSlaveTest
from replicaset_test import ReplicasetTest
from misc_test import MiscTest
from auth_replicaset_test import AuthReplicasetTest

###############################################################################
all_suites = [
    unittest.TestLoader().loadTestsFromTestCase(VersionFunctionsTest),
    unittest.TestLoader().loadTestsFromTestCase(BasicMongoctlTest),
    unittest.TestLoader().loadTestsFromTestCase(MasterSlaveTest),
    unittest.TestLoader().loadTestsFromTestCase(ReplicasetTest),
    unittest.TestLoader().loadTestsFromTestCase(AuthReplicasetTest),
    unittest.TestLoader().loadTestsFromTestCase(MiscTest)
]
###############################################################################
# booty
###############################################################################
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(all_suites))



########NEW FILE########
__FILENAME__ = version_functions_test
# The MIT License

# Copyright (c) 2012 ObjectLabs Corporation

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
__author__ = 'aalkhatib'
import unittest
from mongoctl.mongo_version import make_version_info, is_valid_version

class VersionFunctionsTest(unittest.TestCase):
    def test_version_functions(self):
        self.assertTrue(make_version_info("1.2.0") < make_version_info("1.2.1"))
        self.assertFalse(make_version_info("1.2.0") < make_version_info("1.2.0"))
        self.assertFalse(make_version_info("1.2.0") < make_version_info("1.2.0C"))
        self.assertFalse(make_version_info("1.2.0-rc1") < make_version_info("1.2.0-rc0"))
        self.assertTrue(make_version_info("1.2.0-rc0") < make_version_info("1.2.0-rc1"))
        self.assertTrue(make_version_info("1.2.0-rc0") < make_version_info("1.2.0"))
        self.assertTrue(make_version_info("1.2.0-rc0") < make_version_info("1.2.1"))

        self.assertTrue(is_valid_version("1.0.1"))
        self.assertTrue(is_valid_version("0.1"))
        self.assertFalse(is_valid_version("1"))
        self.assertTrue(is_valid_version("0.1a"))
        self.assertTrue(is_valid_version("0.1c"))
        self.assertTrue(is_valid_version("1.8.9-rc0"))
        self.assertFalse(is_valid_version("a.1.2.3.4"))




########NEW FILE########
__FILENAME__ = users
__author__ = 'abdul'

import repository

from mongoctl_logging import log_info, log_verbose, log_warning, log_exception
from pymongo.errors import OperationFailure, AutoReconnect
from errors import MongoctlException
from prompt import read_password
import pymongo.auth
import mongo_version

###############################################################################
__global_login_user__ = {
    "serverId": None,
    "database": "admin",
    "username": None,
    "password": None
}


###############################################################################
def parse_global_login_user_arg(username, password, server_id):

    # if -u or --username  was not specified then nothing to do
    if not username:
        return

    global __global_login_user__
    __global_login_user__['serverId'] = server_id
    __global_login_user__['username'] = username
    __global_login_user__['password'] = password

###############################################################################
def get_global_login_user(server, dbname):
    global __global_login_user__

    # all server or exact server + db match
    if ((not __global_login_user__["serverId"] or
                 __global_login_user__["serverId"] == server.id) and
            __global_login_user__["username"] and
                __global_login_user__["database"] == dbname):
        return __global_login_user__

    # same cluster members and DB is not 'local'?
    if (__global_login_user__["serverId"] and
                __global_login_user__["database"] == dbname and
                dbname != "local"):
        global_login_server = repository.lookup_server(__global_login_user__["serverId"])
        global_login_cluster = global_login_server.get_replicaset_cluster()
        cluster = server.get_replicaset_cluster()
        if (global_login_cluster and cluster and
                    global_login_cluster.id == cluster.id):
            return __global_login_user__


###############################################################################
def setup_server_users(server):
    """
    Seeds all users returned by get_seed_users() IF there are no users seed yet
    i.e. system.users collection is empty
    """
    """if not should_seed_users(server):
        log_verbose("Not seeding users for server '%s'" % server.id)
        return"""

    log_info("Checking if there are any users that need to be added for "
             "server '%s'..." % server.id)

    seed_users = server.get_seed_users()

    count_new_users = 0

    # Note: If server member of a replica then don't setup admin
    # users because primary server will do that at replinit

    # Now create admin ones
    if not server.is_slave():
        count_new_users += setup_server_admin_users(server)

    for dbname, db_seed_users in seed_users.items():
        # create the admin ones last so we won't have an auth issue
        if dbname in ["admin", "local"]:
            continue
        count_new_users += setup_server_db_users(server, dbname, db_seed_users)


    if count_new_users > 0:
        log_info("Added %s users." % count_new_users)
    else:
        log_verbose("Did not add any new users.")

###############################################################################
def setup_cluster_users(cluster, primary_server):
    log_verbose("Setting up cluster '%s' users using primary server '%s'" %
                (cluster.id, primary_server.id))
    return setup_server_users(primary_server)

###############################################################################
def should_seed_users(server):
    log_verbose("See if we should seed users for server '%s'" %
                server.id)
    try:
        connection = server.get_db_connection()
        dbnames = connection.database_names()
        for dbname in dbnames:
            if connection[dbname]['system.users'].find_one():
                return False
        return True
    except Exception, e:
        log_exception(e)
        return False

###############################################################################
def should_seed_db_users(server, dbname):
    log_verbose("See if we should seed users for database '%s'" % dbname)
    try:
        connection = server.get_db_connection()
        if connection[dbname]['system.users'].find_one():
            return False
        else:
            return True
    except Exception, e:
        log_exception(e)
        return False

###############################################################################
def setup_db_users(server, db, db_users):
    count_new_users = 0
    for user in db_users :
        username = user['username']
        log_verbose("adding user '%s' to db '%s'" % (username, db.name))
        password = user.get('password')
        if not password:
            password = read_seed_password(db.name, username)

        _mongo_add_user(server, db, username, password)
        # if there is no login user for this db then set it to this new one
        db_login_user = server.get_login_user(db.name)
        if not db_login_user:
            server.set_login_user(db.name, username, password)
            # inc new users
        count_new_users += 1

    return count_new_users


###############################################################################
VERSION_2_6 = mongo_version.make_version_info("2.6.0")

###############################################################################
def server_supports_local_users(server):
    version = server.get_mongo_version_info()
    return version and version < VERSION_2_6

###############################################################################
def _mongo_add_user(server, db, username, password, read_only=False,
                    num_tries=1):
    try:
        db.add_user(username, password, read_only)
    except OperationFailure, ofe:
        # This is a workaround for PYTHON-407. i.e. catching a harmless
        # error that is raised after adding the first
        if "login" in str(ofe):
            pass
        else:
            raise
    except AutoReconnect, ar:
        log_exception(ar)
        if num_tries < 3:
            log_warning("_mongo_add_user: Caught a AutoReconnect error. %s " %
                        ar)
            # check if the user/pass was saved successfully
            if db.authenticate(username, password):
                log_info("_mongo_add_user: user was added successfully. "
                         "no need to retry")
            else:
                log_warning("_mongo_add_user: re-trying ...")
                _mongo_add_user(server, db, username, password,
                                read_only=read_only, num_tries=num_tries+1)
        else:
            raise


###############################################################################
def setup_server_db_users(server, dbname, db_users):
    log_verbose("Checking if there are any users that needs to be added for "
                "database '%s'..." % dbname)

    if not should_seed_db_users(server, dbname):
        log_verbose("Not seeding users for database '%s'" % dbname)
        return 0

    db = server.get_db(dbname)

    try:
        any_new_user_added = setup_db_users(server, db, db_users)
        if not any_new_user_added:
            log_verbose("No new users added for database '%s'" % dbname)
        return any_new_user_added
    except Exception, e:
        log_exception(e)
        raise MongoctlException(
            "Error while setting up users for '%s'" \
            " database on server '%s'."
            "\n Cause: %s" % (dbname, server.id, e))

###############################################################################
def prepend_global_admin_user(other_users, server):
    """
    When making lists of administrative users -- e.g., seeding a new server --
    it's useful to put the credentials supplied on the command line at the head
    of the queue.
    """
    cred0 = get_global_login_user(server, "admin")
    if cred0 and cred0["username"] and cred0["password"]:
        log_verbose("Seeding : CRED0 to the front of the line!")
        return [cred0] + other_users if other_users else [cred0]
    else:
        return other_users

###############################################################################
def setup_server_admin_users(server):

    if not should_seed_db_users(server, "admin"):
        log_verbose("Not seeding users for database 'admin'")
        return 0

    admin_users = server.get_admin_users()
    if server.is_auth():
        admin_users = prepend_global_admin_user(admin_users, server)

    if (admin_users is None or len(admin_users) < 1):
        log_verbose("No users configured for admin DB...")
        return 0

    log_verbose("Checking setup for admin users...")
    count_new_users = 0
    try:
        admin_db = server.get_db("admin")

        # potentially create the 1st admin user
        count_new_users += setup_db_users(server, admin_db, admin_users[0:1])

        # the 1st-time init case:
        # BEFORE adding 1st admin user, auth. is not possible --
        #       only localhost cxn gets a magic pass.
        # AFTER adding 1st admin user, authentication is required;
        #      so, to be sure we now have authenticated cxn, re-pull admin db:
        admin_db = server.get_db("admin")

        # create the rest of the users
        count_new_users += setup_db_users(server, admin_db, admin_users[1:])
        return count_new_users
    except Exception, e:
        log_exception(e)
        raise MongoctlException(
            "Error while setting up admin users on server '%s'."
            "\n Cause: %s" % (server.id, e))

###############################################################################
def setup_server_local_users(server):

    seed_local_users = False
    try:
        local_db = server.get_db("local", retry=False)
        if not local_db['system.users'].find_one():
            seed_local_users = True
    except Exception, e:
        log_exception(e)
        pass

    if not seed_local_users:
        log_verbose("Not seeding users for database 'local'")
        return 0

    try:
        local_users = server.get_db_seed_users("local")
        if server.is_auth():
            local_users = prepend_global_admin_user(local_users, server)

        if local_users:
            return setup_db_users(server, local_db, local_users)
        else:
            return 0
    except Exception, e:
        log_exception(e)
        raise MongoctlException(
            "Error while setting up local users on server '%s'."
            "\n Cause: %s" % (server.id, e))

###############################################################################
def read_seed_password(dbname, username):
    return read_password("Please create a password for user '%s' in DB '%s'" %
                         (username, dbname))

########NEW FILE########
__FILENAME__ = utils
__author__ = 'abdul'

import os
import subprocess
import pwd
import time
import socket

import urlparse
import json

from bson import json_util
from mongoctl_logging import *
from errors import MongoctlException


###############################################################################
def namespace_get_property(namespace, name):
    if hasattr(namespace, name):
        return getattr(namespace,name)

    return None

###############################################################################

def to_string(thing):
    return "" if thing is None else str(thing)

###############################################################################
def document_pretty_string(document):
    return json.dumps(document, indent=4, default=json_util.default)

###############################################################################
def listify(object):
    if isinstance(object, list):
        return object

    return [object]

###############################################################################
def is_url(value):
    scheme = urlparse.urlparse(value).scheme
    return  scheme is not None and scheme != ''


###############################################################################
def wait_for(predicate, timeout=None, sleep_duration=2, grace=True):
    start_time = now()
    must_retry = may_retry = not predicate()

    if must_retry and grace:
        # optimizing for predicates whose first invocations may be slooooooow
        log_verbose("GRACE: First eval finished in %d secs - resetting timer." %
                    (now() - start_time))
        start_time = now()

    while must_retry and may_retry:

        must_retry = not predicate()
        if must_retry:
            net_time = now() - start_time
            if timeout and net_time + sleep_duration > timeout:
                may_retry = False
            else:
                left = "[-%d sec] " % (timeout - net_time) if timeout else ""
                log_info("-- waiting %s--" % left)
                time.sleep(sleep_duration)

    return not must_retry

###############################################################################
def now():
    return time.time()

###############################################################################
# OS Functions
###############################################################################
def which(program):

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

###############################################################################
def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

###############################################################################
def ensure_dir(dir_path):
    """
    If DIR_PATH does not exist, makes it. Failing that, raises Exception.
    Returns True if dir already existed; False if it had to be made.
    """
    exists = dir_exists(dir_path)
    if not exists:
        try:
            os.makedirs(dir_path)
        except(Exception,RuntimeError), e:
            raise Exception("Unable to create directory %s. Cause %s" %
                            (dir_path, e))
    return exists

###############################################################################
def dir_exists(path):
    return os.path.exists(path) and os.path.isdir(path)

###############################################################################
def resolve_path(path):
    # handle file uris
    path = path.replace("file://", "")

    # expand vars
    path =  os.path.expandvars(custom_expanduser(path))
    # Turn relative paths to absolute
    try:
        path = os.path.abspath(path)
    except OSError, e:
        # handle the case where cwd does not exist
        if "No such file or directory" in str(e):
            pass
        else:
            raise

    return path

###############################################################################
def custom_expanduser(path):
    if path.startswith("~"):
        login = get_current_login()
        home_dir = os.path.expanduser( "~%s" % login)
        path = path.replace("~", home_dir, 1)

    return path

###############################################################################
def get_current_login():
    try:
        pwuid = pwd.getpwuid(os.geteuid())
        return pwuid.pw_name
    except Exception, e:
        raise Exception("Error while trying to get current os login. %s" % e)

###############################################################################
# sub-processing functions
###############################################################################
def call_command(command, bubble_exit_code=False):
    try:
        return subprocess.check_call(command)
    except subprocess.CalledProcessError, e:
        if bubble_exit_code:
            exit(e.returncode)
        else:
            raise e

###############################################################################
def execute_command(command):

    # Python 2.7+ : Use the new method because i think its better
    if  hasattr(subprocess, 'check_output'):
        return subprocess.check_output(command,stderr=subprocess.STDOUT)
    else: # Python 2.6 compatible, check_output is not available in 2.6
        return subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT).communicate()[0]

###############################################################################
def is_pid_alive(pid):

    try:
        os.kill(pid,0)
        return True
    except OSError:
        return False

###############################################################################
def kill_process(pid, force=False):
    signal = 9 if force else 1
    try:
        os.kill(pid, signal)
        return True
    except OSError:
        return False


###############################################################################
# HELPER functions
###############################################################################
def timedelta_total_seconds(td):
    """
    Equivalent python 2.7+ timedelta.total_seconds()
     This was added for python 2.6 compatibilty
    """
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6


###############################################################################
def is_valid_member_address(address):
    if address is None:
        return False
    host_port = address.split(":")

    return (len(host_port) == 2
            and host_port[0]
            and host_port[1]
            and str(host_port[1]).isdigit())


###############################################################################
# Network Utils Functions
###############################################################################

def is_host_local(host):
    if (host == "localhost" or
                host == "127.0.0.1"):
        return True

    return is_same_host(socket.gethostname(), host)

###############################################################################
def is_same_host(host1, host2):

    """
    Returns true if host1 == host2 OR map to the same host (using DNS)
    """

    if host1 == host2:
        return True
    else:
        ips1 = get_host_ips(host1)
        ips2 = get_host_ips(host2)
        return len(set(ips1) & set(ips2)) > 0

###############################################################################
def is_same_address(addr1, addr2):
    """
    Where the two addresses are in the host:port
    Returns true if ports are equals and hosts are the same using is_same_host
    """
    hostport1 = addr1.split(":")
    hostport2 = addr2.split(":")

    return (is_same_host(hostport1[0], hostport2[0]) and
            hostport1[1] == hostport2[1])
###############################################################################
def get_host_ips(host):
    try:

        ips = []
        addr_info = socket.getaddrinfo(host, None)
        for elem in addr_info:
            ip = elem[4]
            if ip not in ips:
                ips.append(ip)

        # TODO remove this temp hack that works around the case where
        # host X has more IPs than X.foo.com.
        if len(host.split(".")) == 3:
            try:
                ips.extend(get_host_ips(host.split(".")[0]))
            except Exception, ex:
                pass

        return ips
    except Exception, e:
        raise MongoctlException("Invalid host '%s'. Cause: %s" % (host, e))

###############################################################################
def timedelta_total_seconds(td):
    """
    Equivalent python 2.7+ timedelta.total_seconds()
     This was added for python 2.6 compatibilty
    """
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 1e6) / 1e6

###############################################################################
def resolve_class(kls):
    if kls == "dict":
        return dict

    try:
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__( module )
        for comp in parts[1:]:
            m = getattr(m, comp)
        return m
    except Exception, e:
        raise Exception("Cannot resolve class '%s'. Cause: %s" % (kls, e))
########NEW FILE########
__FILENAME__ = version
__author__ = 'abdul'


MONGOCTL_VERSION = '0.6.6.1'

########NEW FILE########
