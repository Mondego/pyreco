__FILENAME__ = commands
import os
import sys
import logging
import shutil

from baboon.baboon.monitor import Monitor
from baboon.baboon.transport import WatchTransport
from baboon.baboon.initializor import MetadirController
from baboon.baboon.transport import RegisterTransport, AdminTransport
from baboon.baboon.fmt import cinput, confirm_cinput, cwarn, csuccess, cerr
from baboon.baboon.notifier import Notifier

from baboon.baboon.config import check_user, check_server, check_project
from baboon.baboon.config import check_config, config, dump, SCMS
from baboon.common.logger import logger
from baboon.common.utils import exec_cmd
from baboon.common.errors.baboon_exception import BaboonException
from baboon.common.errors.baboon_exception import CommandException

logger = logging.getLogger(__name__)


def command(fn):
    def wrapped():
        try:
            return fn()
        except (BaboonException, CommandException) as err:
            cerr(err)
        except KeyboardInterrupt as err:
            print "Bye !"

    return wrapped


def start():
    """ Starts baboon client !
    """

    # Ensure the validity of the configuration file.
    check_config(add_mandatory_server_fields=['streamer', 'max_stanza_size'])

    # If notification is configured, start the notifier.
    try:
        notif_cmd = config['notification']['cmd']
        Notifier(notif_cmd)
    except:
        pass

    metadirs = []
    monitor = None
    transport = None

    try:
        transport = _start_transport()
        monitor = _start_monitor()
        metadirs = _start_metadirs(monitor.handler.exclude)

        # Wait until the transport is disconnected before exiting Baboon.
        _wait_disconnect(transport)
    except BaboonException as err:
        logger.error(err)
    except KeyboardInterrupt:
        pass
    finally:
        _start_close(monitor, transport, metadirs)
        logger.info("Bye !")


@command
def register():
    """ Ask mandatory information and register the new user.
    """

    transport = None
    try:
        username = _get_username()
        passwd = _get_passwd()

        print("\nRegistration in progress...")

        # RegisterTransport uses the config attributes to register.
        config['user'] = {
            'jid': username,
            'passwd': passwd
        }

        # Registration...
        transport = RegisterTransport(callback=_on_register_finished)
        transport.open(block=True)
    finally:
        # Disconnect the transport if necessary.
        if transport and transport.connected.is_set():
            transport.close()
            transport.disconnected.wait(10)


@command
def projects():
    """ Lists all users in a project.
    """

    check_config()

    project = config['parser'].get('project')
    subs_by_project = []

    with AdminTransport(logger_enabled=False) as transport:
        # Get all subscriptions
        subscriptions = _projects_specific(transport, project) if project \
            else _projects_all(transport)

        # Display the subscriptions in a good format.
        _projects_print_users(subscriptions)


@command
def create():
    """ Create a new project with the project argument name.
    """

    check_server()
    check_user()

    project = config['parser']['project']
    path = config['parser']['path']
    project_scm = _check_scm(path)

    _check_project(project)
    config['projects'][project] = {
        'path': path,
        'scm': project_scm,
        'enable': 1
    }

    print("Creation in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.create_project(project)
        if not _on_action_finished(ret_status, msg):
            return

    dump()

    # Do an init() if the git-url can be guessed.
    git_url = _get_git_url(path)
    if git_url:
        config['parser']['git-url'] = git_url
        init()


@command
def delete():
    """ Delete the project with the project argument name.
    """

    check_config()

    project = config['parser']['project']
    print("Deletion in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.delete_project(project)
        _on_action_finished(ret_status, msg)

    project_path = _get_project_path(project)
    _delete_metadir(project, project_path)
    del config['projects'][project]
    dump()


@command
def join():
    """ Join the project with the project argument name.
    """

    check_server()
    check_user()

    project = config['parser']['project']
    path = config['parser']['path']
    project_scm = _check_scm(path)

    _check_project(project)
    config['projects'][project] = {
        'path': path,
        'scm': project_scm,
        'enable': 1
    }

    print("Join in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.join_project(project)
        if not _on_action_finished(ret_status, msg):
            return

    dump()


@command
def unjoin():
    """ Unjoin the project with the project argument name.
    """

    check_config()

    project = config['parser']['project']
    print("Unjoin in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.unjoin_project(project)
        _on_action_finished(ret_status, msg)

    project_path = _get_project_path(project)
    _delete_metadir(project, project_path)
    del config['projects'][project]
    dump()


@command
def accept():
    """ Accept the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = _get_username()

    print("Acceptation in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.accept_pending(project, username)
        _on_action_finished(ret_status, msg)


@command
def reject():
    """ Reject the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = _get_username()

    print("Rejection in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.reject(project, username)
        _on_action_finished(ret_status, msg)


@command
def kick():
    """ Kick the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = _get_username()

    print("Kick in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.kick(project, username)
        _on_action_finished(ret_status, msg)


@command
def init():
    """ Initialialize a new project.
    """

    check_config()

    project = config['parser']['project']
    project_path = _get_project_path(project)
    url = config['parser']['git-url']

    print("Initialize the project %s..." % project)
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.first_git_init(project, url)

        metadir_controller = MetadirController(project, project_path)
        metadir_controller.init_index()
        metadir_controller.create_baboon_index()
        metadir_controller.index.close()

        if not _on_action_finished(ret_status, msg):
            _delete_metadir(project, project_path)


def _start_transport():
    """ Builds and returns a new connected WatchTransport.
    """

    transport = WatchTransport()
    transport.open()
    transport.connected.wait()

    return transport


def _start_monitor():
    """ Builds and returns a new watched Monitor.
    """

    monitor = Monitor()
    monitor.watch()

    return monitor


def _start_metadirs(exclude=None):
    """ Builds and returns all metadirs. exclude is the exclude_method
    optionally needed by the MetadirController constructor.
    """

    metadirs = []
    for project, project_attrs in config['projects'].iteritems():
        # For each project, verify if the .baboon metadir is valid and
        # take some decisions about needed actions on the repository.
        metadir = MetadirController(project, project_attrs['path'], exclude)
        metadirs.append(metadir)
        metadir.go()

    return metadirs


def _start_close(monitor, transport, metadirs):
    """ Clears the monitor, transport and list of metadir before finishing the
    start command.
    """

    logger.info("Closing baboon...")

    # Close each metadir shelve index.
    for metadir in metadirs:
        metadir.index.close()

    # Close the transport and the monitor. If one of them is not
    # started, the close() method has no effect.
    if monitor:
        monitor.close()
    if transport:
        transport.close()
        transport.disconnected.wait(10)


def _wait_disconnect(transport, timeout=5):
    """ Polls the state of the transport's connection each `timeout` seconds.
    Exits when the transport is disconnected.
    """

    while not transport.disconnected.is_set():
        transport.disconnected.wait(timeout)


def _get_username():
    """ Returns the username by getting it from the config or asking it from
    stdin.
    """

    username = config['parser'].get('username')
    if not username:
        validations = [('^\w+$', 'Username can only contains alphanumeric and '
                        'underscore characters')]
        username = cinput('Username: ', validations=validations)

    # Transform the username to a JID.
    username += '@%s' % config['parser']['hostname']

    return username


def _get_passwd():
    """ Returns the password by getting it from stdin.
    """

    validations = [('^\w{6,}$', 'The password must be at least 6 characters '
                    'long.')]
    return confirm_cinput('Password: ', validations=validations, secret=True,
                          possible_err='The password must match !')


def _projects_specific(transport, project):
    """ Lists all users in a specific project. The transport must be connected.
    """

    project_users = transport.get_project_users(project) or []
    return [(project, project_users)]


def _projects_all(transport):
    """ Lists all users in a all projects. The transport must be connected.
    """

    subscriptions = []
    for project in config['projects']:
        subscriptions += _projects_specific(transport, project)

    return subscriptions


def _projects_print_users(subs_by_project):
    """ Prints the subs_by_project list of tuples.
    """

    for project, subs in subs_by_project:
        print("[%s]" % project)
        for sub in subs:
            print(" %s" % sub['jid'])


def _check_project(project_name):
    """ Checks if the project is not already defined in the configuration file.
    If so, raise a CommandException.
    """

    project = config['projects'].get(project_name)
    if project:
        if project.get('enable') == '0':
            raise CommandException(409, "The project is already defined in "
                                   "your configuration file, but it's "
                                   "disabled.")

        raise CommandException(409, "The project is already defined in your "
                               "configuration file.")


def _check_scm(path):
    """ Checks if the SCM in the path directory is supported. If not, raise a
    CommandException.
    """

    # Ensure the path exists.
    if not os.path.exists(path):
        raise CommandException(404, "The project's path does not exist on "
                               "your system.")

    # Ensure the path is a directory.
    if not os.path.isdir(path):
        raise CommandException(500, "The project's path is not a directory.")

    # Ensure the scm in the path directory exists and is supported.
    scm = _get_scm(path)
    if not scm:
        raise CommandException(500, "The project isn't managed by a supported "
                               "source code manager.")

    return scm


def _get_project_path(project_name):
    """ Returns the project path of the project_name. Raised a CommandException
    if cannot be retrieved.
    """

    try:
        project_path = config['projects'][project_name]['path']
        return project_path
    except KeyError:
        raise CommandException(404, "The project path cannot be found in your "
                               "configuration file.")


def _get_git_url(path):
    """ Try to auto-detect the git origin url in the path dir. If found, return
    it.
    """

    ret_code, output, _ = exec_cmd('git config --get remote.origin.url', path)
    return output if ret_code == 0 else None


def _delete_metadir(project_name, project_path):
    """ Delete the metadir on the project_path. Raised a CommandException on
    error.
    """

    try:
        MetadirController(project_name, project_path).delete()
    except EnvironmentError:
        raise CommandException(500, "Cannot delete the metadir directory.")


def _on_register_finished(ret_status, msg, fatal=False):
    """ Callback for the registration.
    """

    _on_action_finished(ret_status, msg, fatal=fatal)
    # Dump the configuration file if there's no error.
    if ret_status == 200:
        dump()


def _on_action_finished(ret_status, msg, fatal=False):
    if ret_status >= 200 and ret_status < 300:
        csuccess(msg)
        return True
    else:
        # Print the error message.
        cerr(msg)
        return False


def _get_scm(path):
    """ Explores the path of the directory and returns the SCM used (one None).
    """

    for scm in SCMS:
        if os.path.isdir(os.path.join(path, '.%s' % scm)):
            return scm

########NEW FILE########
__FILENAME__ = config
import os
import shutil
import sys
import argparse
import logging
import logging.config

if sys.version_info < (3, 0):
    from ConfigParser import RawConfigParser, MissingSectionHeaderError
else:
    from configparser import RawConfigParser, MissingSectionHeaderError

from baboon.baboon.fmt import cerr, cwarn, csuccess
from baboon.baboon.dictconf import LOGGING, PARSER
from baboon.common.config import get_config_args, get_config_file
from baboon.common.config import init_config_log
from baboon.common.errors.baboon_exception import ConfigException

SCMS = ('git',)


def check_server(add_mandatory_fields=[]):
    """ Checks the server section in the config dict. The add_mandatory_fields
    list allows to add more mandatory fields.
    """

    mandatory_keys = set(['master', 'pubsub'] + add_mandatory_fields)
    _check_config_section('server', mandatory_keys)


def check_user(add_mandatory_fields=[]):
    """ Checks the user section in the config dict. The add_mandatory_fields
    list allows to add more mandatory fields.
    """

    mandatory_keys = set(['jid', 'passwd'] + add_mandatory_fields)
    _check_config_section('user', mandatory_keys)


def check_project(add_mandatory_fields=[]):
    """ Checks if there's at least one configured project. The
    add_mandatory_fields list allows to add more mandatory fields to validate
    all configured projects.
    """

    mandatory_keys = set(['path', 'scm', 'enable'] + add_mandatory_fields)
    projects = config.get('projects', {})

    # Ensure there's at least one project.
    if not len(projects):
        raise ConfigException("No project configured.")

    # For all projects, ensure all mandatory fields are present.
    mandatory_keys = set(['path', 'scm', 'enable'] + add_mandatory_fields)
    for project in projects:
        _check_config_section(project, mandatory_keys, prefix='projects')


def check_config(add_mandatory_server_fields=[], add_mandatory_user_fields=[],
                 add_mandatory_project_fields=[]):
    """ Checks all the mandatory fields in all sections.
    """

    check_server(add_mandatory_fields=add_mandatory_server_fields)
    check_user(add_mandatory_fields=add_mandatory_user_fields)
    check_project(add_mandatory_fields=add_mandatory_project_fields)


def dump():
    """ Dumps the config dict to the user's configuration file ~/.baboonrc. If
    the file already exists, it's copied to ~/.baboonrc.old and the original
    file is overwritten.
    """

    # Don't dump the config if the --nosave arg is present.
    if config['parser'].get('nosave', False):
        return

    baboonrc_path = os.path.expanduser('~/.baboonrc')
    # Override the default baboonrc_path if the --config arg is present.
    if config['parser'].get('configpath'):
        baboonrc_path = config['parser']['configpath']

    try:
        # Dump the config file.
        with open(baboonrc_path, 'w') as fd:
            print >>fd, get_dumped_user()
            print >>fd, get_dumped_server()
            print >>fd, get_dumped_notification()
            print >>fd, get_dumped_projects()
            print >>fd, get_dumped_example_project()

            csuccess("The new configuration file is written in %s\n" %
                     baboonrc_path)
    except EnvironmentError as err:
        cerr("Cannot dump the configuration. Cause:\n%s" % err)


def get_dumped_server():
    """ Returns a dumped representation of the server section.
    """

    return '\n'.join(_get_dumped_section('server')) + '\n'


def get_dumped_user():
    """ Returns a dumped representation of the user section.
    """

    return '\n'.join(_get_dumped_section('user')) + '\n'


def get_dumped_notification():
    """ Returns a dumped representation of the notification section.
    """

    return '\n'.join(_get_dumped_section('notification')) + '\n'


def get_dumped_projects():
    """ Returns a dumped representation of the projects section.
    """

    content = []
    for project, opts in config['projects'].iteritems():
        dumped_section = _get_dumped_section(project, prefix='projects')
        content.append('\n'.join(dumped_section) + '\n')

    return '\n'.join(content)


def get_dumped_example_project():
    """ Returns a dumped representation of project configuration example.
    """

    return """# Example of project definition.
#[awesome_project] \t# The project name on the baboon server.
#path = /pathto/project # The project path of your system.
#scm = git \t\t# The source code manager you use for this project.
#enable = 1 \t\t# You want baboon to actually watch this project.
"""


def get_baboon_config():
    """ Returns the baboon full dict configuration.
    """

    arg_attrs = get_config_args(PARSER)
    file_attrs = get_config_file(arg_attrs, 'baboonrc')
    init_config_log(arg_attrs, LOGGING)

    config = {
        'parser': arg_attrs,
        'projects': {}
    }

    # The known section tuple contains the list of sections to put directly
    # as a root key in the config dict. Other sections will be interpreted as a
    # project and placed into the 'projects' key.
    known_section = ('server', 'user', 'notification')
    for key in file_attrs:
        if key in known_section:
            config[key] = file_attrs[key]
        else:
            # It's a project, add the attributes to the projects key.
            config['projects'][key] = file_attrs[key]

    # If a hostname has been defined in the command line, we need to override
    # all fields that depend on it.
    depend_hostnames = {}
    if 'server' in config:
        depend_hostnames['server'] = ['pubsub', 'streamer', 'master']
    if 'user' in config:
        depend_hostnames['user'] = ['jid']

    # Search and replace default hostname by hostname defined from the command
    # line.
    for section, fields in depend_hostnames.iteritems():
        for field in fields:
            try:
                cur_value = config[section][field]
                config[section][field] = cur_value.replace(
                    'baboon-project.org', config['parser']['hostname'])
            except KeyError:
                # Just pass the keyerror exception. If it's a mandatory field,
                # the error will be raised correctly later.
                pass

    return config


def _check_config_section(section, mandatory_keys, prefix=None):

    # If the prefix is provided, use the config['prefix'] src dict instead of
    # directly the src config. Useful for projects sections.
    src = config[prefix] if prefix else config

    # Ensure the section exists.
    if section not in src:
        raise ConfigException("'%s' section is missing." % section)

    try:
        # Ensure all mandatory keys exist with a non-empty value. If not,
        # raised a appropriate message exception.
        for key, value in [(x, src[section][x]) for x in mandatory_keys]:
            if not value:
                raise ConfigException("Value of the '%s' field cannot be "
                                      "empty." % key)
    except KeyError as err:
        raise ConfigException("'%s' field required in the '%s' section " %
                              (err.message, section))


def _get_dumped_section(section, prefix=None):

    try:
        src = config[prefix] if prefix else config

        content = ['[%s]' % section]
        for option, value in src['%s' % section].iteritems():
            content.append('%s = %s' % (option, value))

        return content
    except KeyError:
        # Ignore all the section content if a KeyError exception is raised.
        return ''


config = get_baboon_config()

########NEW FILE########
__FILENAME__ = dictconf
import sys
import logging

from baboon.common.config import get_log_path, get_null_handler


PARSER = {
    'description': 'detect merge conflicts in realtime.',
    'args': [{
        'args': ('-v', '--verbose'),
        'kwargs': {
            'help': 'increase the verbosity.',
            'action': 'store_const',
            'dest': 'loglevel',
            'const': logging.DEBUG,
            'default': logging.INFO
        }
    }, {
        'args': ('--hostname',),
        'kwargs': {
            'help': 'override the default baboon-project.org hostname.',
            'dest': 'hostname',
            'default': 'baboon-project.org'
        }
    }, {
        'args': ('--config', ),
        'kwargs': {
            'help': 'override the default location of the configuration file.',
            'dest': 'configpath'
        }
    }],
    'subparsers': [
        {
            'name': 'register',
            'help': 'create an account.',
            'args': [{
                'args': ('username',),
                'kwargs': {
                    'help': 'your username.',
                    'nargs': '?'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to override the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'projects',
            'help': 'list all users in a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.',
                    'nargs': '?'
                }
            }, {
                'args': ('-a', '--all'),
                'kwargs': {
                    'help': 'display all information.',
                    'action': 'store_true'
                }
            }]
        }, {
            'name': 'create',
            'help': 'create a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('path',),
                'kwargs': {
                    'help': 'the project path on the filesystem.',
                    'action': 'store'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to dump the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'delete',
            'help': 'delete a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to dump the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'join',
            'help': 'join a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('path',),
                'kwargs': {
                    'help': 'the project path on the filesystem.',
                    'action': 'store'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to dump the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'unjoin',
            'help': 'unjoin a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to dump the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'accept',
            'help': 'accept a user to join a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('username',),
                'kwargs': {
                    'help': 'the username to accept.'
                }
            }]
        }, {
            'name': 'reject',
            'help': 'reject a user to join a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('username',),
                'kwargs': {
                    'help': 'the username to reject.'
                }
            }]
        }, {
            'name': 'kick',
            'help': 'kick a user from a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('username',),
                'kwargs': {
                    'help': 'the username to kick.'
                }
            }]
        }, {
            'name': 'init',
            'help': 'initialize a new project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('git-url',),
                'kwargs': {
                    'help': 'the remote git url to fetch the project.'
                }
            }]
        }, {
            'name': 'start',
            'help': 'start Baboon !',
            'args': [{
                'args': ('--no-init',),
                'kwargs': {
                    'help': 'avoid to execute the startup sync.',
                    'dest': 'init',
                    'default': False,
                    'action': 'store_true'
                }
            }]
        }
    ]
}


LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(message)s',
            'datefmt': '%Y/%m/%d %H:%M:%S'

        },
        'simple': {
            'format': '%(message)s'
        },
    },
    'handlers': {
        'rootfile': {
            'level': 'DEBUG',
            'class': get_null_handler(),
            'formatter': 'verbose'
        },
        'sleekxmppfile': {
            'class': get_null_handler(),
            'level': 'DEBUG',
            'formatter': 'verbose'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'baboon.common.loghandler.ConsoleUnixColoredHandler',
            'formatter': 'verbose',
            'stream': 'ext://sys.stdout',
        }
    },
    'loggers': {
        'baboon': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'sleekxmpp': {
            'handlers': ['sleekxmppfile'],
            'level': 'DEBUG',
        },
        'root': {
            'handlers': ['rootfile'],
            'level': 'DEBUG',
        },
    }
}

########NEW FILE########
__FILENAME__ = fmt
from re import match
from getpass import getpass
from termcolor import colored, cprint
from baboon.common.errors.baboon_exception import CommandException


# Fix Python 2.x. input
try:
    input = raw_input
except:
    pass


def cerr(msg):
    """ Displays the formatted msg with an error style.
    """

    cprint(msg, 'red', attrs=['bold'])


def csuccess(msg):
    """ Displays the formatted msg with a success style.
    """

    cprint(msg, 'green', attrs=['bold'])


def cwarn(msg):
    """
    """

    cprint(msg, 'yellow', attrs=['bold'])


def cblabla(msg):
    """
    """

    cprint(msg, attrs=['bold'])


def cinput(prompt, validations=[], secret=False):
    """ Retrieves the user input with a formatted prompt. Return the value when
    the value entered by the user matches all validations. The validations is a
    list of tuple. The first element of the tuple is the regexp, the second is
    the error message when the input does not match the regexp.
    """

    # The future return value.
    ret = None

    # Iterate until input matches all validations.
    while True:
        valid = True

        # Get the user input and put it into ret.
        colored_prompt = colored(prompt, attrs=['bold'])
        ret = getpass(prompt=colored_prompt) if secret else \
            input(colored_prompt)

        # Iterates over validations...
        for validation, possible_err in validations:
            if not match(validation, ret):
                # The input is not valid. Print an error message and set the
                # valid flag to False to avoid to exit the while True loop.
                cerr(possible_err)
                valid = False

        # Exit the loop if the valid flag is True.
        if valid:
            break

    return ret


def cinput_yes_no(prompt):
    ret = input(colored(prompt + ' (y/n) ', attrs=['bold']))
    return ret.lower() in ('true', 'y', 'yes')


def confirm_cinput(prompt, validations=[], possible_err="", secret=False):

    ret = cinput(prompt, secret=secret)

    # Iterates over validations...
    for validation, err in validations:
        if not match(validation, ret):
            raise CommandException(500, err)

    confirm_ret = cinput('Confirm %s' % prompt.lower(), secret=secret)

    if ret == confirm_ret:
        return ret
    else:
        # The values are not the same.
        raise CommandException(500, possible_err)

########NEW FILE########
__FILENAME__ = initializor
import os
import shutil
import time
import shelve

from os.path import join, relpath, getmtime, exists

from baboon.baboon.config import config
from baboon.common.file import FileEvent
from baboon.common.eventbus import eventbus
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


@logger
class MetadirController(object):

    METADIR = '.baboon'
    GIT_INDEX = 'index'

    def __init__(self, project, project_path, exclude_method=None):
        """
        """

        self.project = project
        self.project_path = project_path
        self.metadir_path = join(self.project_path, MetadirController.METADIR)
        self.exclude_method = exclude_method

        eventbus.register('rsync-finished-success', self._on_rsync_finished)

    def go(self):
        """
        """

        # Verify (and create if necessary) if baboon metadir exists.
        already_exists = exists(self.metadir_path)

        if already_exists:
            # Initializes the shelve index.
            self.init_index()

            # Startup initialization.
            self._startup_init()
        else:
            raise BaboonException("The project %s is not yet initialized. "
                                  "Please, run `baboon init %s <git-url>`." %
                                  (self.project, self.project))

    def init_index(self):
        if not exists(self.metadir_path):
            os.makedirs(self.metadir_path)

        self.index = shelve.open(join(self.metadir_path,
                                      MetadirController.GIT_INDEX),
                                 writeback=True)

    def create_baboon_index(self):
        """
        """

        if not exists(self.metadir_path):
            os.makedirs(self.metadir_path)

        cur_timestamp = time.time()

        for root, _, files in os.walk(self.project_path):
            for name in files:
                fullpath = join(root, name)
                rel_path = relpath(fullpath, self.project_path)

                self.index[rel_path] = cur_timestamp

    def _on_rsync_finished(self, project, files):
        """ When a rsync is finished, update the index dict.
        """

        # First, we need to verify if the event is for this current
        # initializor! If so, it means the project is the same than
        # self.project.
        if not project == self.project:
            return

        cur_timestamp = time.time()

        try:
            for f in files:
                if f.event_type == FileEvent.MOVE:
                    del self.index[f.src_path]
                    self.index[f.dest_path] = cur_timestamp
                elif f.event_type == FileEvent.DELETE:
                    del self.index[f.src_path]
                else:
                    self.index[f.src_path] = cur_timestamp

            # TODO: Verify if it's not a performance issue (maybe on big
            # project).
            self.index.sync()
        except ValueError:
            # If the index shelve is already closed, a ValueError is raised.
            # In this case, the last rsync will not be persisted on disk. Not
            # dramatical.
            pass

    def _startup_init(self):
        """
        """

        cur_files = []

        self.logger.info("[%s] startup initialization..." % self.project)
        for root, _, files in os.walk(self.project_path):
            for name in files:
                fullpath = join(root, name)
                rel_path = relpath(fullpath, self.project_path)

                # Add the current file to the cur_files list.
                cur_files.append(rel_path)

                # Get the last modification timestamp of the current file.
                cur_timestamp = getmtime(fullpath)

                # Get the last rsync timestamp of the current file.
                register_timestamp = self.index.get(rel_path)

                # If the file is not excluded...
                if not self.exclude_method or not \
                        self.exclude_method(rel_path):
                    # Verify if it's a new file...
                    if register_timestamp is None:
                        self.logger.info("Need to create: %s" % rel_path)
                        FileEvent(self.project, FileEvent.CREATE,
                                  rel_path).register()
                    elif (register_timestamp and cur_timestamp >
                          register_timestamp):
                        self.logger.info("Need to sync: %s" % rel_path)
                        FileEvent(self.project, FileEvent.MODIF,
                                  rel_path).register()

        # Verify if there's no file deleted since the last time.
        for del_file in [x for x in self.index.keys() if x not in cur_files]:
            self.logger.info("Need to delete: %s" % del_file)
            FileEvent(self.project, FileEvent.DELETE, del_file).register()

        self.logger.info("[%s] ready !" % self.project)

    def delete(self):
        """ Deletes the metadir from the project.
        """

        if os.path.exists(self.metadir_path):
            shutil.rmtree(self.metadir_path)

########NEW FILE########
__FILENAME__ = main
import os
import sys
import logging

from baboon.common.errors.baboon_exception import ConfigException

# The config can raise a ConfigException if there's a problem.
try:
    from baboon.baboon.config import config
    from baboon.baboon.config import check_server, check_user, check_project
except ConfigException as err:
    # An error as occured while loading the global baboon configuration. So,
    # there's no logger correctly configured. Load a basic logger to print the
    # error message.

    logging.basicConfig(format='%(message)s')
    logger = logging.getLogger(__name__)
    logger.error(err)

    sys.exit(1)

from baboon.baboon import commands
from baboon.baboon.plugins import *
from baboon.common.logger import logger

logger = logging.getLogger(__name__)


def main():
    """ The entry point of the Baboon client.
    """

    try:
        # Call the correct method according to the current arg subparser.
        getattr(commands, config['parser']['which'])()
    except (ConfigException, KeyError) as err:
        logger.error(err)
        sys.exit(1)

########NEW FILE########
__FILENAME__ = monitor
import os
import tarfile
import tempfile

from os.path import join, exists
from time import sleep
from threading import Thread, Lock
from abc import ABCMeta, abstractmethod, abstractproperty

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from baboon.baboon.config import config
from baboon.common.file import FileEvent, pending
from baboon.common.eventbus import eventbus
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException

lock = Lock()


@logger
class EventHandler(FileSystemEventHandler):
    """ An abstract class that extends watchdog FileSystemEventHandler in
    order to describe the behavior when a file is
    added/modified/deleted. The behavior is dependend of the SCM to
    detect exclude patterns (e.g. .git for git, .hg for hg, etc.)
    """

    __metaclass__ = ABCMeta

    def __init__(self, project_path):

        super(EventHandler, self).__init__()
        self.project_path = project_path

    @abstractproperty
    def scm_name(self):
        """ The name of the scm. This name will be used in the baboonrc
        configuration file in order to retrieve and instanciate the correct
        class.
        """

        return

    @abstractmethod
    def exclude(self, path):
        '''Returns True when file matches an exclude pattern specified in the
        scm specific monitor plugin.
        '''
        return

    def on_created(self, event):
        self.logger.debug('CREATED event %s' % event.src_path)

        with lock:
            project = self._get_project(event.src_path)
            rel_path = self._verify_exclude(event, event.src_path)
            if rel_path:
                FileEvent(project, FileEvent.CREATE, rel_path).register()

    def on_moved(self, event):
        self.logger.debug('MOVED event from %s to %s' % (event.src_path,
                                                         event.dest_path))

        with lock:
            project = self._get_project(event.src_path)
            src_rel_path = self._verify_exclude(event, event.src_path)
            dest_rel_path = self._verify_exclude(event, event.dest_path)

            if src_rel_path:
                FileEvent(project, FileEvent.DELETE, src_rel_path).register()

            if dest_rel_path:
                FileEvent(project, FileEvent.MODIF, dest_rel_path).register()

    def on_modified(self, event):
        """ Triggered when a file is modified in the watched project.
        @param event: the watchdog event
        @raise BaboonException: if cannot retrieve the relative project path
        """

        self.logger.debug('MODIFIED event %s' % event.src_path)

        with lock:
            project = self._get_project(event.src_path)
            rel_path = self._verify_exclude(event, event.src_path)
            if rel_path:
                # Here, we are sure that the rel_path is a file. The check is
                # done if the _verify_exclude method.

                # If the file was a file and is now a directory, we need to
                # delete absolutely the file. Otherwise, the server will not
                # create the directory (OSError).
                if os.path.isdir(event.src_path):
                    self.logger.debug('The file %s is now a directory.' %
                                      rel_path)

                FileEvent(project, FileEvent.MODIF, rel_path).register()

    def on_deleted(self, event):
        """ Trigered when a file is deleted in the watched project.
        """

        self.logger.debug('DELETED event %s' % event.src_path)

        with lock:
            project = self._get_project(event.src_path)
            rel_path = self._verify_exclude(event, event.src_path)
            if rel_path:
                FileEvent(project, FileEvent.DELETE, rel_path).register()

    def _verify_exclude(self, event, fullpath):
        """ Verifies if the full path correspond to an exclude file. Returns
        the relative path of the file if the file is not excluded. Returns None
        if the file need to be ignored.  """

        # Use the event is_directory attribute instead of
        # os.path.isdir. Suppose a file 'foo' is deleted and a
        # directory named 'foo' is created. The on_deleted is
        # triggered after the file is deleted and maybe after the
        # directory is created too. So if we do a os.path.isdir, the
        # return value will be True. We want False.
        if event.is_directory:
            return None

        rel_path = os.path.relpath(fullpath, self.project_path)
        if self.exclude(rel_path):
            self.logger.debug("Ignore the file: %s" % rel_path)
            return

        return rel_path

    def _get_project(self, fullpath):
        """ Get the name of the project of the fullpath file.
        """

        for project, project_conf in config['projects'].iteritems():
            path = os.path.expanduser(project_conf['path'])
            if path == self.project_path:
                return project


@logger
class Dancer(Thread):
    """ A thread that wakes up every <sleeptime> secs and starts a
    rsync + merge verification if pending set() is not empty.
    """

    def __init__(self, sleeptime=1):
        """ Initializes the thread.
        """

        Thread.__init__(self, name='Dancer')

        self.sleeptime = sleeptime
        self.stop = False

    def run(self):
        """ Runs the thread.
        """

        while not self.stop:
            # Sleeps during sleeptime secs.
            sleep(self.sleeptime)

            with lock:
                for project, files in pending.iteritems():
                    try:
                        eventbus.fire('new-rsync', project=project,
                                      files=files)

                    except BaboonException as e:
                        self.logger.error(e)

                # Clears the pending dict.
                pending.clear()

    def close(self):
        """ Sets the stop flag to True.
        """

        self.stop = True


@logger
class Monitor(object):
    def __init__(self):
        """ Watches file change events (creation, modification) in the
        watched project.
        """

        from baboon.baboon.plugins.git.monitor_git import EventHandlerGit

        self.dancer = Dancer(sleeptime=1)

        # All monitor will be stored in this dict. The key is the project name,
        # the value is the monitor instance.
        self.monitors = {}

        try:
            # Avoid to use iteritems (python 2.x) or items (python 3.x) in
            # order to support both versions.
            for project in sorted(config['projects']):
                project_attrs = config['projects'][project]
                project_path = os.path.expanduser(project_attrs['path'])
                self.handler = EventHandlerGit(project_path)

                monitor = Observer()
                monitor.schedule(self.handler, project_path, recursive=True)

                self.monitors[project_path] = monitor
        except OSError as err:
            self.logger.error(err)
            raise BaboonException(err)

    def watch(self):
        """ Starts to watch the watched project
        """

        # Start all monitor instance.
        for project, monitor in self.monitors.iteritems():
            monitor.start()
            self.logger.debug("Started to monitor the %s directory" % project)

        self.dancer.start()

    def startup_rsync(self, project, project_path):
        """
        """

        # Get the timestamp of the last rsync.
        register_timestamp = os.path.getmtime(join(project_path,
                                                   '.baboon-timestamp'))

        for root, _, files in os.walk(project_path):
            for name in files:
                fullpath = join(root, name)
                rel_path = os.path.relpath(fullpath, project_path)

                # Get the timestamp of the current file
                cur_timestamp = os.path.getmtime(fullpath)

                # Register a FileEvent.MODIF if the file is not excluded
                # and the file is more recent than the last rsync.
                if not self.handler.exclude(rel_path) and \
                        cur_timestamp > register_timestamp:

                    FileEvent(project, FileEvent.MODIF, rel_path).register()

    def close(self):
        """ Stops the monitoring on the watched project
        """

        # Stop all monitor instance.
        for project, monitor in self.monitors.iteritems():
            monitor.stop()
            monitor.join()

        self.dancer.close()
        self.dancer.join()

########NEW FILE########
__FILENAME__ = notifier
from baboon.common.eventbus import eventbus
from baboon.common.utils import exec_cmd
from baboon.common.logger import logger


@logger
class Notifier(object):
    """ This class listens on the event bus and run notification command from
    the configuration file when a notification is sent.
    """

    def __init__(self, notif_cmd):

        self.notif_cmd = notif_cmd
        eventbus.register('conflict-result', self._on_message)

        self.logger.debug("Notifier loaded with command: %s" % self.notif_cmd)

    def _on_message(self, message):

        exec_cmd(self.notif_cmd %(message))

########NEW FILE########
__FILENAME__ = monitor_git
import os
import sys
import re
import fnmatch

if sys.version_info < (2, 7):
    # Python < 2.7 doesn't have the cmp_to_key function.
    from baboon.common.utils import cmp_to_key
else:
    from functools import cmp_to_key

from baboon.baboon.monitor import EventHandler
from baboon.common.errors.baboon_exception import BaboonException


class EventHandlerGit(EventHandler):
    def __init__(self, project_path):
        super(EventHandlerGit, self).__init__(project_path)

        # My ignore file name is...
        self.gitignore_path = os.path.join(project_path, '.gitignore')

        # Lists of compiled RegExp objects
        self.include_regexps = []
        self.exclude_regexps = []

        # Update those lists
        self._populate_gitignore_items()

    @property
    def scm_name(self):
        return 'git'

    def exclude(self, rel_path):
        # First, check if the modified file is the gitignore file. If it's the
        # case, update include/exclude paths lists.
        if rel_path == self.gitignore_path:
            self._populate_gitignore_items()

        # Return True only if rel_path matches an exclude pattern AND does NOT
        # match an include pattern. Else, return False
        if (self._match_excl_regexp(rel_path) and
                not self._match_incl_regexp(rel_path)):

            return True

        return False

    def on_modified(self, event):
        """
        """

        rel_path = os.path.relpath(event.src_path, self.project_path)
        if rel_path == '.gitignore':
            # Reparse the gitignore.
            self._populate_gitignore_items()

        super(EventHandlerGit, self).on_modified(event)

    def _populate_gitignore_items(self):
        """ This method populates include and exclude lists with
        compiled regexps objects.
        """

        # Reset the include_regexps and exclude_regexps.
        self.include_regexps = []
        self.exclude_regexps = [re.compile('.*\.git/.*\.lock'),
                                re.compile('.*\.baboon-timestamp'),
                                re.compile('.*baboon.*')]

        # If there's a .gitignore file in the watched directory.
        if os.path.exists(self.gitignore_path):
            # Parse the gitignore.
            ignores = self._parse_gitignore()
            if ignores is not None:
                # Populate the regexps list with the ignores result.
                self.include_regexps += [re.compile(x) for x in ignores[0]]
                self.exclude_regexps += [re.compile(x) for x in ignores[1]]

    def _match_excl_regexp(self, rel_path):
        """ Returns True if rel_path matches any item in
        exclude_regexp list.
        """

        for regexp in self.exclude_regexps:
            if regexp.search(rel_path) is not None:
                self.logger.debug("The path %s matches the ignore regexp"
                                  " %s." % (rel_path, regexp.pattern))
                return True

        return False

    def _match_incl_regexp(self, rel_path):
        """ Returns True if rel_path matches any item in
        include_regexp list.
        """

        for neg_regexp in self.include_regexps:
            if neg_regexp.search(rel_path) is not None:
                self.logger.debug("The same path %s matches the include"
                                  " regexp %s." % (rel_path,
                                                   neg_regexp.pattern))
                return True

        return False

    def _parse_gitignore(self):
        """ Parses the .gitignore file in the repository.
        Returns a tuple with:
        1st elem: negative regexps (regexps to not match)
        2nd elem: regexps
        """
        gitignore_path = os.path.join(self.project_path, '.gitignore')
        lines = []  # contains each line of the .gitignore file
        results = []  # contains the result regexp patterns
        neg_results = []  # contains the result negative regexp patterns

        try:
            with open(gitignore_path, 'r') as f:
                lines = f.readlines()
        except IOError as err:
            raise BaboonException(format(err))

        # Sort the line in order to have inverse pattern first
        lines = sorted(lines, key=cmp_to_key(self._gitline_comparator))

        # For each git pattern, convert it to regexp pattern
        for line in lines:
            regexp = self._gitline_to_regexp(line)
            if regexp is not None:
                if not line.startswith('!'):
                    results.append(regexp)
                else:
                    neg_results.append(regexp)

        return neg_results, results

    def _gitline_comparator(self, a, b):
        """ Compares a and b. I want to have pattern started with '!'
        firstly
        """
        if a.startswith('!'):
            return -1
        elif b.startswith('!'):
            return 1
        else:
            return a == b

    def _gitline_to_regexp(self, line):
        """ Convert the unix pattern (line) to a regex pattern
        """
        negation = False  # if True, inverse the pattern

        # Remove the dirty characters like spaces at the beginning
        # or at the end, carriage returns, etc.
        line = line.strip()

        # A blank line matches no files, so it can serve as a
        # separator for readability.
        if line == '':
            return

        # A line starting with # serves as a comment.
        if line.startswith('#'):
            return

        # An optional prefix !  which negates the pattern; any
        # matching file excluded by a previous pattern will become
        # included again. If a negated pattern matches, this will
        # override
        if line.startswith('!'):
            line = line[1:]
            negation = True

        # If the pattern does not contain a slash /, git treats it
        # as a shell glob pattern and checks for a match against
        # the pathname relative to the location of the .gitignore
        # file (relative to the toplevel of the work tree if not
        # from a .gitignore file).

        # Otherwise, git treats the pattern as a shell glob
        # suitable for consumption by fnmatch(3) with the
        # FNM_PATHNAME flag: wildcards in the pattern will not
        # match a / in the pathname. For example,
        # "Documentation/*.html" matches "Documentation/git.html"
        # but not "Documentation/ppc/ppc.html" or
        # "tools/perf/Documentation/perf.html".
        regex = fnmatch.translate(line)
        regex = regex.replace('\\Z(?ms)', '')

        if not negation:
            regex = '.*%s.*' % regex

        return regex

########NEW FILE########
__FILENAME__ = transport
import os
import sys
import pickle
import struct
import uuid
import time

from threading import Event

from sleekxmpp import ClientXMPP
from sleekxmpp.jid import JID
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream.tostring import tostring
from sleekxmpp.exceptions import IqError
from sleekxmpp.plugins.xep_0060.stanza.pubsub_event import EventItem

from baboon.baboon.monitor import FileEvent
from baboon.baboon.config import config
from baboon.common import proxy_socket
from baboon.common.eventbus import eventbus
from baboon.common.logger import logger
from baboon.common import pyrsync
from baboon.common.stanza import rsync
from baboon.common.errors.baboon_exception import BaboonException


@logger
class CommonTransport(ClientXMPP):

    def __init__(self):
        """ Initializes the CommonTranport with the XEP-0060 support.
        """

        ClientXMPP.__init__(self, config['user']['jid'], config['user'][
            'passwd'])

        self.connected = Event()
        self.disconnected = Event()
        self.rsync_running = Event()
        self.rsync_finished = Event()
        self.wait_close = False
        self.failed_auth = False

        # Register and configure pubsub plugin.
        self.register_plugin('xep_0060')
        self.register_handler(Callback('Pubsub event', StanzaPath(
            'message/pubsub_event'), self._pubsub_event))

        # Shortcut to access to the xep_0060 plugin.
        self.pubsub = self.plugin["xep_0060"]

        # Register and configure data form plugin.
        self.register_plugin('xep_0004')

        # Shortcuts to access to the xep_0004 plugin.
        self.form = self.plugin['xep_0004']

        # Shortcuts to access to the config server information
        self.pubsub_addr = config['server']['pubsub']
        self.server_addr = config['server']['master']

        # Register events
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('failed_auth', self._on_failed_auth)
        self.add_event_handler('stream_error', self.stream_err)
        self.add_event_handler('message', self.message)
        self.add_event_handler('message_form', self.message_form)
        self.add_event_handler('message_xform', self.message_form)
        self.register_handler(Callback('RsyncFinished Handler',
                                       StanzaPath('iq@type=set/rsyncfinished'),
                                       self._handle_rsync_finished))

        eventbus.register('new-rsync', self._on_new_rsync)

    def __enter__(self):
        """ Adds the support of with statement with all CommonTransport
        classes. A new XMPP connection is instantiated and returned when the
        connection is established.
        """

        # Open a new connection.
        self.open()

        # Wait until the connection is established. Raise a BaboonException if
        # there's an authentication error.
        while not self.connected.is_set():
            if self.failed_auth:
                raise BaboonException("Authentication failed.")
            self.connected.wait(1)

        # Return the instance itself.
        return self

    def __exit__(self, type, value, traceback):
        """ Disconnects the transport at the end of the with statement.
        """

        self.close()

    def open(self, block=False):
        """ Connects to the XMPP server.
        """

        self.logger.debug("Connecting to XMPP...")
        self.use_ipv6 = False
        if self.connect(use_ssl=False, use_tls=False):
            self.logger.debug("Connected to XMPP")
            self.disconnected.clear()
            self.process(block=block)
        else:
            self.logger.error("Unable to connect.")

    def stream_err(self, iq):
        """ Called when a StreamError is received.
        """

        self.logger.error(iq['text'])

    def  _on_failed_auth(self, event):
        """ Called when authentication failed.
        """

        self.logger.error("Authentication failed.")
        eventbus.fire('failed-auth')
        self.failed_auth = True
        self.close()

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        self.connected.set()
        self.logger.debug('Connected')

    def close(self):
        """ Closes the XMPP connection.
        """

        self.connected.clear()
        self.logger.debug('Closing the XMPP connection...')
        self.disconnect(wait=True)
        self.disconnected.set()
        self.logger.debug('XMPP connection closed.')

    def _pubsub_event(self, msg):
        """ Called when a pubsub event is received.
        """

        if msg['type'] in ('normal', 'headline'):
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])

            items = msg['pubsub_event']['items']['substanzas']
            for item in items:
                notif_msg = ""
                if isinstance(item, EventItem):
                    self.logger.info(item['payload'].get('status'))
                    notif_msg += item['payload'].get('status')

                    for err_f in item['payload']:
                        if err_f.text:
                            err = "> %s" % err_f.text
                            self.logger.warning(err)
                            notif_msg = "%s\n%s" % (notif_msg, err)
                    if item['payload'].get('type') == 'error':
                        eventbus.fire('conflict-result', notif_msg)
        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])

    def _on_new_rsync(self, project, files, **kwargs):
        """ Called when a new rsync needs to be started.
        """

        self.connected.wait()

        self.rsync(project, files=files)
        eventbus.fire('rsync-finished-success', project, files)

    def _handle_rsync_finished(self, iq):
        """ Called when a rsync is finished.
        """

        # Retrieve the project context.
        node = iq['rsyncfinished']['node']

        # Reply to the iq.
        self.logger.debug("[%s] Sync finished." % node)
        iq.reply().send()

        # Set the rsync flags.
        self.rsync_running.clear()
        self.rsync_finished.set()

        # It's time to verify if there's a conflict or not.
        if not self.wait_close:
            self.merge_verification(node)

    def message_form(self, form):
        self.logger.debug("Received a form message: %s" % form)
        try:
            expected_type = \
                'http://jabber.org/protocol/pubsub#subscribe_authorization'
            if expected_type in form['form']['fields']['FORM_TYPE']['value']:
                node = form['form']['fields']['pubsub#node']['value']
                jid = form['form']['fields']['pubsub#subscriber_jid']['value']
                user = JID(jid).user

                self.logger.info(">> %s wants to join the %s project ! <<" % (user, node))
                self.logger.info(" $ baboon accept %s %s" % (node, user))
                self.logger.info(" $ baboon reject %s %s" % (node, user))
        except KeyError:
            pass

    def message(self, msg):
        self.logger.info("Received: %s" % msg)

    def rsync_error(self, msg):
        """ On rsync error.
        """

        self.logger.error(msg)

        # Set the rsync flags.
        self.rsync_running.clear()
        self.rsync_finished.set()


@logger
class WatchTransport(CommonTransport):
    """ The transport has the responsability to communicate via HTTP
    with the baboon server and to subscribe with XMPP 0060 with the
    Baboon XMPP server.
    """

    def __init__(self):
        """ WatchTransport initializes all SleekXMPP stuff like plugins,
        events and more.
        """

        super(WatchTransport, self).__init__()

        # Shortcuts to access to the config server information
        self.streamer_addr = config['server']['streamer']

        self.register_plugin('xep_0050')  # Ad-hoc command
        self.register_plugin('xep_0065')  # Socks5 Bytestreams

        self.add_event_handler('socks_connected', self._on_socks_connected)

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        # Shortcut to access to the xep_0050 plugin.
        self.adhoc = self.plugin["xep_0050"]

        # Shortcut to access to the xep_0065 plugin.
        self.streamer = self.plugin["xep_0065"]

        # Negotiates the bytestream
        try:
            streamhost_used = self.streamer.handshake(self.server_addr,
                                                      self.streamer_addr)
        except IqError as e:
            self.logger.error("Cannot established the proxy_socket connection. "
                              "Exiting...")
            # If the socks5 bytestream can't be established, disconnect the
            # XMPP connection clearly.
            self.close()
            return

        # Registers the SID to retrieve later to send/recv data to the
        # good proxy_socket stored in self.streamer.proxy_threads dict.
        self.sid = streamhost_used['socks']['sid']

    def _on_socks_connected(self, event):
        """
        """

        proxy_sock = self.streamer.get_socket(self.sid)
        proxy_listener = proxy_socket.listen(self.sid, proxy_sock,
                                             self._on_socks5_data)

        self.logger.debug("Connected.")
        self.connected.set()

        # Retrieve the list of pending users.
        for project in config['projects']:
            self._get_pending_users(project)

    def close(self):
        """ Closes the XMPP connection.
        """

        # Wait until all syncs are finished.
        self.wait_close = True
        if self.rsync_running.is_set():
            self.logger.info("A sync task is currently running...")
            self.rsync_finished.wait()
            self.logger.info("Ok, all syncs are now finished.")

        # Close the proxy proxy_socket.
        if hasattr(self, 'streamer') and self.streamer:
            self.streamer.close()

        # Disconnect...
        super(WatchTransport, self).close()

    def rsync(self, project, files=None):
        """ Starts a rsync transaction, rsync and stop the
        transaction.

        Raises a BaboonException if there's a problem.
        """

        # Verify if the connection is established. Otherwise, wait...
        if not self.connected.is_set():
            self.connected.wait()

        # Set the rsync flags.
        self.rsync_running.set()
        self.rsync_finished.clear()

        #TODO: make this an int while checking config file
        max_stanza_size = int(config['server']['max_stanza_size'])

        # Build first stanza
        iq = self._build_iq(project, files)

        try:
            # Get the size of the stanza
            to_xml = tostring(iq.xml)
            size = sys.getsizeof(to_xml)

            # If it's bigger than the max_stanza_size, split it !
            if size >= max_stanza_size:
                iqs = self._split_iq(size, project, files)
                self.logger.warning('The xml stanza has been split %s stanzas.'
                                    % len(iqs))
            else:
                # Else the original iq will be the only element to send
                iqs = [iq]

            # Send elements in list
            for iq in iqs:
                iq.send()
                self.logger.debug('Sent (%d/%d)!' %
                                  (iqs.index(iq) + 1, len(iqs)))

        except IqError as e:
            self.rsync_error(e.iq['error']['text'])
        except Exception as e:
            self.rsync_error(e)

    def _build_iq(self, project, files):
        """Build a single rsync stanza.
        """
        iq = self.Iq(sto=self.server_addr, stype='set')

        # Generate a new rsync ID.
        iq['rsync']['sid'] = self.sid
        iq['rsync']['rid'] = str(uuid.uuid4())
        iq['rsync']['node'] = project

        for f in files:
            if f.event_type == FileEvent.MODIF:
                iq['rsync'].add_file(f.src_path)
            elif f.event_type == FileEvent.CREATE:
                iq['rsync'].add_create_file(f.src_path)
            elif f.event_type == FileEvent.DELETE:
                iq['rsync'].add_delete_file(f.src_path)

        return iq

    def _split_iq(self, size, project, files):
        """Splits a stanza into multiple stanzas whith size < max_stanza_size.
        Returns a list a stanzas
        """

        iqs = []

        # We don't need the exact result of the division. Let's add 1 to
        # overcome "round" issues. How many chunks do we need ?
        chunk_num = size / int(config['server']['max_stanza_size']) + 1

        # How many files per chunk then ?
        step = len(files) / chunk_num

        # Get the splitted files list
        chunks = list(self._get_chunks(files, step))

        # Build a stanza for each of them
        for chunk in chunks:
            iqs.append(self._build_iq(project, chunk))

        return iqs

    def _get_chunks(self, files, step):
        """ Generate the chunks from the files list.
        """
        for i in xrange(0, len(files), step):
            yield files[i:i + step]

    def _on_socks5_data(self, sid, data, **kwargs):
        """ Called when receiving data over the socks5 proxy_socket (xep
        0065).
        """

        deltas = []  # The list of delta.

        # Sets the future proxy_socket response dict.
        ret = {'from': self.boundjid.bare}

        # Gets the current project.
        ret['node'] = data['node']

        # Gets the RID.
        ret['rid'] = data['rid']

        # Gets the list of hashes.
        all_hashes = data['hashes']

        for elem in all_hashes:
            # 'elem' is a tuple. The first element is the relative
            # path to the current file. The second is the server-side
            # hashes associated to this path.
            relpath = elem[0]
            hashes = elem[1]

            # TODO: Handle the possible AttributeError.
            project_path = config['projects'][data['node']]['path']
            project_path = os.path.expanduser(project_path)

            fullpath = os.path.join(project_path, relpath)
            if os.path.exists(fullpath) and os.path.isfile(fullpath):
                # Computes the local delta of the current file.
                patchedfile = open(fullpath, 'rb')
                delta = pyrsync.rsyncdelta(patchedfile, hashes,
                                           blocksize=8192)
                delta = (relpath, delta)

                # Appends the result to the list of delta.
                deltas.append(delta)
            else:
                # TODO: Handle this error ?
                pass

        # Adds the list of deltas in the response dict.
        ret['delta'] = deltas

        # Sends the result over the proxy_socket.
        self.streamer.send(sid, proxy_socket.pack(ret))

    def merge_verification(self, project):
        """ Sends an IQ to verify if there's a conflict or not.
        """

        iq = self.Iq(sto=self.server_addr, stype='set')
        iq['merge']['node'] = project

        try:
            iq.send()
        except IqError as e:
            self.logger.error(e.iq['error']['text'])

    def _get_pending_users(self, node):
        """ Build and send the message to get the list of pending users on the
        node.
        """

        # Build the IQ.
        iq = self.Iq(sto=self.pubsub_addr, stype='set')
        iq['command']['action'] = 'execute'
        iq['command']['sessionid'] = 'pubsub-get-pending:20031021T150901Z-600'
        iq['command']['node'] = 'http://jabber.org/protocol/pubsub#get-pending'
        iq['command']['form'].add_field(var='pubsub#node', value=node)

        # Send the IQ to the pubsub server !
        try:
            iq.send()
        except IqError:
            pass


@logger
class AdminTransport(CommonTransport):

    def __init__(self, logger_enabled=True):

        super(AdminTransport, self).__init__()
        self.logger.disabled = not logger_enabled

    def create_project(self, project):
        """ Creates a node on the XMPP server with the name project. Sets also
        the correct subscriptions and affiliations.
        """

        try:
            # Update the default configuration to have 'Authorize' node access
            # model.
            node_config = self.pubsub.get_node_config(self.pubsub_addr)
            node_config_form = node_config['pubsub_owner']['default']['config']
            node_config_form.field['pubsub#access_model'].set_value(
                'authorize')
            node_config_form.field['pubsub#notify_delete'].set_value(True)

            # Create the node (name == project).
            self.pubsub.create_node(self.pubsub_addr, project,
                                    config=node_config_form)

            # The owner must subscribe to the node to receive the alerts.
            self.pubsub.modify_subscriptions(self.pubsub_addr, project,
                                             [(config['user']['jid'],
                                               'subscribed')])

            # The admin must have the owner affiliation to publish alerts
            # into the node.
            self.pubsub.modify_affiliations(self.pubsub_addr, project,
                                            [(self.server_addr, 'owner')])

            return (200, 'The project %s is successfuly created.' % project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong during the creation of the project " \
                "%s." % project

            if status_code == 409:
                msg = 'The project %s already exists.' % project

            return (status_code, msg)

    def delete_project(self, project):

        try:
            self.pubsub.delete_node(self.pubsub_addr, project)
            return (200, 'The project %s is successfuly deleted.' % project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong during the deletion of the project " \
                "%s." % project

            if status_code == 403:
                msg = 'You are not authorized to delete %s project.' % project
            elif status_code == 404:
                msg = 'The project %s does not exist.' % project

            return (status_code, msg)

    def join_project(self, project):
        try:
            # TODO: Before the subscription, we need to verify if the user is
            # not already subscribed in order to have a correct message.
            # Otherwise, the status code is 202. Strange behavior.
            ret_iq = self.pubsub.subscribe(self.pubsub_addr, project)
            status = ret_iq['pubsub']['subscription']['subscription']

            if status == 'pending':
                return (202, "Invitation sent. You need to wait until the "
                        "owner accepts your invitation.")
            elif status == 'subscribed':
                return (200, "You are now a contributor of the %s project." %
                        project)
            else:
                return (500, "Something went wrong. Cannot join the %s "
                        "project." % project)

        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong. Cannot join the %s project." % project

            if status_code == 404:
                msg = "The %s project does not exist." % project

            return (status_code, msg)

    def unjoin_project(self, project):

        try:
            self.pubsub.unsubscribe(self.pubsub_addr, project)
            return (200, "Successfully unjoin the %s project." % project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong. Cannot unjoin the %s project." \
                  % project

            if status_code == 401:
                msg = "You are not a contributor of the %s project." % project
            elif status_code == 404:
                msg = "The %s project does not exist." % project

            return (status_code, msg)

    def get_project_users(self, project):
        try:
            ret = self.pubsub.get_node_subscriptions(self.pubsub_addr, project)
            return ret['pubsub_owner']['subscriptions']
        except IqError:
            # TODO: Handle this error.
            pass

    def accept_pending(self, project, user):
        self._allow_pending(project, user, 'true')
        return (200, "%s is now successfuly subscribed on %s." % (user,
                                                                  project))

    def reject(self, project, user):
        self._allow_pending(project, user, 'false')
        return (200, "%s is now successfuly rejected on %s." % (user,
                                                                project))

    def kick(self, project, user):

        subscriptions = [(user, 'none')]
        try:
            self.pubsub.modify_subscriptions(self.pubsub_addr, project,
                                             subscriptions=subscriptions)
            return (200, "%s is now successfuly kicked from %s." % (user,
                                                                    project))
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong."

            if status_code == 403:
                msg = "You don't have the permission to do this."
            elif status_code == 404:
                msg = "The %s project does not exist." % project

            return (status_code, msg)

    def first_git_init(self, project, url):

        iq = self.Iq(sto=self.server_addr, stype='set')
        iq['git-init']['node'] = project
        iq['git-init']['url'] = url

        try:
            iq.send(timeout=240)
            return (200, "The project %s is now correctly initialized." %
                    project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong."

            if status_code == 503:
                msg = e.iq['error']['text']

            return (status_code, msg)

    def _allow_pending(self, project, user, allow):
        """ Build and send the message to accept/reject the user on the node
        project depending on allow boolean.
        """

        # Build the data form.
        payload = self.form.make_form(ftype='submit')
        payload.add_field(var='FORM_TYPE', ftype='hidden',
                          value='http://jabber.org/protocol/pubsub'
                          '#subscribe_authorization')
        payload.add_field(var='pubsub#subid', value='ididid')
        payload.add_field(var='pubsub#node', value=project)
        payload.add_field(var='pubsub#subscriber_jid', value=user)
        payload.add_field(var='pubsub#allow', value=allow)

        # Build the message.
        message = self.make_message(self.pubsub_addr)
        message.appendxml(payload.xml)

        # Send the message to the pubsub server !
        message.send()


class RegisterTransport(CommonTransport):

    def __init__(self, callback=None):

        super(RegisterTransport, self).__init__()

        self.callback = callback

        self.register_plugin('xep_0077')  # In-band Registration
        self.add_event_handler('register', self.register)

    def register(self, iq):
        """ Handler for the register event.
        """

        resp = self.Iq()
        resp['type'] = 'set'
        resp['register']['username'] = self.boundjid.user
        resp['register']['password'] = self.password

        try:
            resp.send(now=True)

            if self.callback:
                self.callback(200, 'You are now registered as %s.' %
                              config['user']['jid'])
        except IqError as e:
            if self.callback:
                status_code = int(e.iq['error']['code'])
                msg = "Something went wrong during the registration."

                if status_code == 409:
                    msg = "This username is already use. Please choose " \
                          "another one."
                elif status_code == 500:
                    # Often, registration limit exception.
                    msg = e.iq['error']['text']

                self.callback(status_code, msg, fatal=True)

        self.close()

########NEW FILE########
__FILENAME__ = config
import argparse
import logging
import logging.config

from baboon.common.config import get_config_args, get_config_file
from baboon.common.config import init_config_log
from dictconf import LOGGING, PARSER


def get_baboond_config():
    """ Returns the baboond full dict configuration.
    """

    arg_attrs = get_config_args(PARSER)
    file_attrs = get_config_file(arg_attrs, 'baboondrc')
    init_config_log(arg_attrs, LOGGING)

    config = {}
    config.update(arg_attrs)
    config.update(file_attrs)

    return config


config = get_baboond_config()

########NEW FILE########
__FILENAME__ = dictconf
import sys
import logging

from baboon.common.config import get_log_path, get_null_handler


PARSER = {
    'description': 'detect merge conflicts in realtime.',
    'args': [{
        'args': ('-v', '--verbose'),
        'kwargs': {
            'help': 'increase the verbosity.',
            'action': 'store_const',
            'dest': 'loglevel',
            'const': logging.DEBUG,
            'default': logging.INFO
        }
    }],
    'subparsers': []
}

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(asctime)-20s%(levelname)-18s %(message)s'
            ' (%(threadName)s/%(funcName)s:%(lineno)s)',
            'datefmt': '%Y/%m/%d %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'rootfile': {
            'level': 'DEBUG',
            'class': get_null_handler(),
            'formatter': 'verbose',
        },
        'sleekxmppfile': {
            'level': 'DEBUG',
            'class': get_null_handler(),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'baboon.common.loghandler.ConsoleUnixColoredHandler',
            'formatter': 'verbose',
            'stream': 'ext://sys.stdout',
        }
    },
    'loggers': {
        'baboon': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'sleekxmpp': {
            'handlers': ['sleekxmppfile'],
            'level': 'DEBUG',
        },
        'root': {
            'handlers': ['rootfile'],
            'level': 'DEBUG',
        },
    }
}

########NEW FILE########
__FILENAME__ = dispatcher
from executor import Executor

from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


@logger
class Dispatcher(object):
    """ This class has the responsability to dispatch tasks to the good
    executor thread according to the project name.
    """

    def __init__(self):
        """
        """

        # Keys -> project name, Values -> The associated executor thread.
        self.executors = {}

    def put(self, project_name, task):
        """ Put the task to the executor thread associated to the project name.
        If the thread does not exist, it will be created.
        """

        # Get the executor thread associated to the project name.
        executor = self.executors.get(project_name)
        if not executor:
            # The thread does not exist yet. Create a new one.
            executor = Executor()

            # Associate this new thread to the project_name.
            self.executors[project_name] = executor

            # Start the thread.
            executor.start()

        # Put the task to the good executor thread.
        executor.tasks.put(task)

    def close(self):
        """ Stop all executor threads.
        """

        from baboon.baboond.task import EndTask

        for executor in self.executors.values():
            executor.tasks.put(EndTask())
            executor.join()


dispatcher = Dispatcher()

########NEW FILE########
__FILENAME__ = executor
import sys

from threading import Thread

if sys.version_info < (3, 0):
    from Queue import PriorityQueue
else:
    from queue import PriorityQueue

from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


@logger
class Executor(Thread):
    """ This class applies the baboonsrv workflow task by task.
    """

    def __init__(self):
        """ Initialize the executor thread. Executor has only ONE
        thread because all the task MUST BE executed one after
        another.
        """

        Thread.__init__(self)

        # A priority queue to store all tasks. The priority is important in
        # order to have an endtask with high priority. When someone puts an
        # EndTask into this queue, the next task will be that and all other
        # tasks will be ignored.
        self.tasks = PriorityQueue()

    def run(self):
        """ Consume on the tasks queue and run each task until an
        endtask.
        """
        from baboon.baboond.task import EndTask

        # The endtask is a flag to indicate if it's the end of life of
        # the server or not.
        endtask = False

        # While the endtask is False, continue to consume on the
        # queue.
        while not endtask:
            # Take the next task...
            task = self.tasks.get()

            # Verify that it's not a EndTask.
            endtask = type(task) == EndTask

            # Run it !
            try:
                self.logger.debug('Running a new task...')
                task.run()
            except BaboonException as err:
                self.logger.error(err)

            # Mark the task finished
            self.logger.debug('A task has been finished...')
            self.tasks.task_done()
            self.logger.debug('Remaining task(s): %s' % self.tasks.qsize())

        self.logger.debug('The executor thread is now finished.')

########NEW FILE########
__FILENAME__ = main
from baboon.baboond.transport import transport
from baboon.baboond.dispatcher import dispatcher
from baboon.common.eventbus import eventbus


def main():
    """ Initializes baboond.
    """

    try:
        while not transport.disconnected.is_set():
            transport.disconnected.wait(5)
    except KeyboardInterrupt:
        dispatcher.close()
        transport.close()

########NEW FILE########
__FILENAME__ = task
import os
import errno
import stat
import threading
import shutil
import tempfile
import uuid
import re

from sleekxmpp.jid import JID

from baboon.baboond.dispatcher import dispatcher
from baboon.baboond.transport import transport
from baboon.baboond.config import config
from baboon.common import pyrsync, proxy_socket
from baboon.common.utils import exec_cmd
from baboon.common.eventbus import eventbus
from baboon.common.file import FileEvent
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


def create_missing_dirs(fullpath, isfile=True):
    """ Creates all missing parent directories of the fullpath.
    """

    if isfile:
        fullpath = os.path.dirname(fullpath)

    try:
        # Creates all the parent directories.
        os.makedirs(fullpath)
    except OSError:
        pass


class Task(object):
    """ The base class for all kind of tasks.
    """

    def __init__(self, priority):
        """ Store the priority in order to compare tasks and order
        them.
        """
        self.priority = priority

    def __cmp__(self, other):
        """ The comparison is based on the priority.
        """
        return cmp(self.priority, other.priority)

    def run(self):
        """ This task cannot be run.
        """
        raise NotImplementedError("This run method must be implemented in a "
                                  " task subclass.")


@logger
class EndTask(Task):
    """ A high priority task to exit BaboonSrv.
    """

    def __init__(self):
        """ Initializes the EndTask.
        """

        # The priority is 1. It means that it's the higher possible priority
        # for baboonsrv.
        super(EndTask, self).__init__(1)

    def run(self):
        """ Shutdowns Baboond.
        """

        # Closes the transport
        transport.close()
        self.logger.info('Bye !')


class AlertTask(Task):
    """ A high priority task to alert baboon client the state of the merge.
    """

    def __init__(self, project_name, jid, dest_jid,
                 merge_conflict=False, conflict_files=[]):
        """ Initialize the AlertTask. By default, there's no merge
        conflict.
        """

        # The priority is 2. It means that it's the higher possible
        # priority for baboonsrv except the EndTask.
        super(AlertTask, self).__init__(2)

        self.project_name = project_name
        self.username = JID(jid).user
        self.dest_username = JID(dest_jid).user
        self.merge_conflict = merge_conflict
        self.conflict_files = conflict_files

    def run(self):
        """ Build the appropriate message and publish it to the node.
        """

        conflict_msg = '[%s] Conflict detected between %s and %s.' % (
            self.project_name, self.username, self.dest_username)
        good_msg = '[%s] No conflict detected between %s and %s.' % (
            self.project_name, self.username, self.dest_username)
        msg = conflict_msg if self.merge_conflict else good_msg

        transport.alert(self.project_name, msg, self.conflict_files,
                        merge_conflict=self.merge_conflict)


@logger
class GitInitTask(Task):
    """ The first git initialization task. In other words, the first git clone.
    """

    def __init__(self, project, url, jid):
        """ Initializes the GitInitTask.
        """

        super(GitInitTask, self).__init__(4)

        # Generate the current GitInitTask unique baboon id
        self.bid = uuid.uuid4()

        self.project = project
        self.url = url
        self.jid = jid
        self.project_cwd = os.path.join(config['server']['working_dir'],
                                        self.project)
        self.user_cwd = os.path.join(self.project_cwd, self.jid)

    def run(self):
        self.logger.debug('A new git init task has been started.')

        # If the project directory already exists, delete it.
        if os.path.exists(self.user_cwd):
            shutil.rmtree(self.user_cwd)

        create_missing_dirs(self.project_cwd, isfile=False)
        ret_code, output, _ = exec_cmd('git clone %s %s' % (
            self.url, self.jid), self.project_cwd)
        if not ret_code:
            self.logger.debug('Git init task finished.')
            eventbus.fire('git-init-success', self.bid)
        else:
            eventbus.fire('git-init-failure', self.bid,
                          "Cannot initialize the git repository.")


@logger
class RsyncTask(Task):
    """ A rsync task to sync the baboon client repository with
    relative repository server-side.
    """

    def __init__(self, sid, rid, sfrom, project, project_path, files):

        super(RsyncTask, self).__init__(4)

        self.sid = sid
        self.rid = rid
        self.jid = JID(sfrom)
        self.project = project
        self.project_path = project_path
        self.files = files

        self.modif_files = []
        self.create_files = []
        self.mov_files = []
        self.del_files = []

        # Declare a thread Event to wait until the rsync is completely
        # finished.
        self.rsync_finished = threading.Event()

    def run(self):

        self.logger.debug('RsyncTask %s started' % self.sid)

        # Lock the repository with a .baboon.lock file.
        lock_file = os.path.join(self.project_path, '.baboon.lock')
        create_missing_dirs(lock_file)
        open(lock_file, 'w').close()

        for f in self.files:
            # Verify if the file can be written in the self.project_path.
            path_valid = self._verify_paths(f)
            if not path_valid:
                self.logger.error("The file path cannot be written in %s." %
                                  self.project)
                eventbus.fire('rsync-finished-failure', rid=self.rid)
                return

            if f.event_type == FileEvent.CREATE:
                self.logger.debug('[%s] - Need to create %s.' %
                                 (self.project_path, f.src_path))
                self._create_file(f.src_path)
            elif f.event_type == FileEvent.MODIF:
                self.logger.debug('[%s] - Need to sync %s.' %
                                 (self.project_path, f.src_path))
                new_hash = self._get_hash(f.src_path)
                self._send_hash(new_hash)
            elif f.event_type == FileEvent.DELETE:
                self.logger.debug('[%s] - Need to delete %s.' %
                                 (self.project_path, f.src_path))
                self._delete_file(f.src_path)
            elif f.event_type == FileEvent.MOVE:
                self.logger.debug('[%s] - Need to move %s to %s.' %
                                 (self.project_path, f.src_path, f.dest_path))
                self._move_file(f.src_path, f.dest_path)

        # Remove the .baboon.lock file.
        os.remove(lock_file)

        # Fire the rsync-finished-success event.
        eventbus.fire('rsync-finished-success', rid=self.rid)

        self.logger.debug('Rsync task %s finished', self.sid)

    def _verify_paths(self, file_event):
        """ Verifies if the file_event paths can be written in the
        project_path.
        """

        valid = self._verify_path(file_event.src_path)
        if valid and file_event.dest_path:
            valid = self._verify_path(file_event.dest_path)

        return valid

    def _verify_path(self, f):
        """ Verifies if the f path can be written in the project_path.
        """

        joined = os.path.join(self.project_path, f)
        if self.project_path not in os.path.abspath(joined):
            return False

        return True

    def _create_file(self, f):
        """ Create the file f.
        """

        fullpath = os.path.join(self.project_path, f)
        create_missing_dirs(fullpath)
        open(fullpath, 'w').close()

    def _move_file(self, src, dest):
        """ Move the src path to the dest path.
        """

        src_fullpath = os.path.join(self.project_path, src)
        dest_fullpath = os.path.join(self.project_path, dest)

        shutil.move(src_fullpath, dest_fullpath)
        self.logger.debug("Moving %s to %s done." % (src_fullpath,
                                                     dest_fullpath))

    def _delete_file(self, f):
        """ Delete the file f from the project path.
        """

        fullpath = os.path.join(self.project_path, f)

        # Verifies if the current file exists on the filesystem
        # before delete it. For example, it can be already deleted
        # by a recursive deleted parent directory (with
        # shutil.rmtree below).
        if os.path.exists(fullpath):
            try:
                if os.path.isfile(fullpath):
                    # Remove the file.
                    os.remove(fullpath)

                    # Delete recursively all parent directories of
                    # the fullpath is they are empty.
                    self._clean_directory(self.project_path,
                                          os.path.dirname(fullpath))

                elif os.path.isdir(f):
                    shutil.rmtree(f)
                    self.logger.info('Directory recursively deleted: %s' % f)
            except OSError:
                # There's no problem if the file/dir does not
                # exists.
                pass

    def _get_hash(self, f):
        """ Computes the hash of the file f.
        """

        fullpath = os.path.join(self.project_path, f)

        # If the file has no write permission, set it.
        self._add_perm(fullpath, stat.S_IWUSR)

        # Verifies if all parent directories of the fullpath is created.
        create_missing_dirs(fullpath)

        # If the file does not exist, create it
        if not os.path.exists(fullpath):
            open(fullpath, 'w+b').close()

        if os.path.isfile(fullpath):
            # Computes the block checksums and add the result to the
            # all_hashes list.
            with open(fullpath, 'rb') as unpatched:
                return (f, pyrsync.blockchecksums(unpatched, blocksize=8192))

    def _send_hash(self, h):
        """ Sends over the transport streamer the hash h.
        """

        # Sets the future proxy_socket response dict.
        payload = {
            'sid': self.sid,
            'rid': self.rid,
            'node': self.project,
            'hashes': [h],
        }

        # Gets the proxy_socket associated to the SID and send the payload.
        proxy_sock = transport.streamer.get_socket(self.sid)
        proxy_sock.sendall(proxy_socket.pack(payload))

        # Wait until the rsync is finished.
        # TODO: It takes sometimes more than 240 sec (i.e. git pack files)
        self.rsync_finished.wait(240)

        if not self.rsync_finished.is_set():
            self.logger.error('Timeout on rsync detected !')

        # Reset the rsync_finished Event.
        self.rsync_finished.clear()

    def _get_hashes(self):
        """ Computes the delta hashes for each file in the files list
        and return the future rsync payload to send.
        """

        # Sets the future proxy_socket response dict.
        ret = {
            'sid': self.sid,
            'rid': self.rid
        }

        # A list of hashes.
        all_hashes = []

        for relpath in self.files:
            fullpath = os.path.join(self.project_path, relpath)

            # If the file has no write permission, set it.
            self._add_perm(fullpath, stat.S_IWUSR)

            # Verifies if all parent directories of the fullpath is
            # created.
            create_missing_dirs(fullpath)

            # If the file does not exist, create it
            if not os.path.exists(fullpath):
                open(fullpath, 'w+b').close()

            if os.path.isfile(fullpath):
                # Computes the block checksums and add the result to the
                # all_hashes list.
                with open(fullpath, 'rb') as unpatched:
                    hashes = pyrsync.blockchecksums(unpatched)
                    data = (relpath, hashes)
                    all_hashes.append(data)

        # Adds the hashes list in the ret dict.
        ret['hashes'] = all_hashes

        return ret

    def _add_perm(self, fullpath, perm):
        """ Add the permission (the list of available permissions is
        in the Python stat module) to the fullpath. If the fullpath
        does not exists, do nothing.
        """

        if os.path.exists(fullpath) and not os.access(fullpath, os.W_OK):
            cur_perm = stat.S_IMODE(os.stat(fullpath).st_mode)
            os.chmod(fullpath, cur_perm | stat.S_IWUSR)

    def _clean_directory(self, basepath, destpath):
        """ Deletes all empty directories from the destpath to
        basepath.
        """

        cur_dir = destpath
        while not cur_dir == basepath:
            try:
                os.rmdir(cur_dir)
                cur_dir = os.path.dirname(cur_dir)
            except OSError as e:
                if e.errno == errno.ENOTEMPTY:
                    # The directory is not empty. Return now.
                    return


@logger
class MergeTask(Task):
    """ A task to test if there's a conflict or not.
    """

    def __init__(self, project_name, username):
        """ Initialize the MergeTask.

        The project_name initializes the current working directory.

        The username is the user directory inside the project_name
        that indicates which user start the task.
        """

        # The priority is greater than EndTask and RsyncTask in order
        # to have a lower priority.
        super(MergeTask, self).__init__(5)

        # See the __init__ documentation.
        self.project_name = project_name
        self.username = username

        # Set the project cwd.
        self.project_cwd = os.path.join(config['server']['working_dir'],
                                        self.project_name)

        # Raise an error if the project cwd does not exist.
        if not os.path.exists(self.project_cwd):
            raise BaboonException('Cannot find the project on the server.'
                                  ' Are you sure %s is a correct project name'
                                  ' ?' % self.project_name)

        # Set the master user cwd.
        self.master_cwd = os.path.join(self.project_cwd, self.username)

        # Raise an error if the project cwd does not exist.
        if not os.path.exists(self.master_cwd):
            raise BaboonException('Cannot find the master user on the %s'
                                  ' project.' % self.project_name)

        # If the project cwd is mark as corrupted, stop this task.
        if os.path.exists(os.path.join(self.master_cwd, '.lock')):
            # The path exists -> the master_cwd is corrupted.
            raise BaboonException('The %s is corrupted. The merge task is'
                                  ' cancelled.' % self.master_cwd)

    def run(self):
        """ Test if there's a merge conflict or not.
        """

        # Verify if the repository of the master user is not locked.
        lock_file = os.path.join(self.master_cwd, '.baboon.lock')
        if os.path.exists(lock_file):
            self.logger.error("The %s directory is locked. Can't start a merge"
                              "task." % self.master_cwd)
            return

        self.logger.debug('Merge task %s started' % self.master_cwd)

        merge_threads = []

        # All users
        for user in self._get_user_dirs():
            try:
                # Create a thread by user to merge with the master
                # user repository.
                merge_thread = threading.Thread(target=self._user_side,
                                                args=(user, ))
                merge_thread.start()
                merge_threads.append(merge_thread)
            except BaboonException as e:
                self.logger.error(e)

        # Wait all merge threads are finished.
        for thread in merge_threads:
            thread.join()

        self.logger.debug('Merge task %s finished' % self.master_cwd)

    def _user_side(self, user):

        user_cwd = os.path.join(self.project_cwd, user)

        # If the user cwd is locked, stop the process.
        if os.path.exists(os.path.join(user_cwd, '.baboon.lock')):
            # The path exists -> the user_cwd is locke.
            self.logger.error('The %s is locked. Ignore it' % user_cwd)
            return

        # Add the master_cwd remote.
        exec_cmd('git remote add %s %s' % (self.username, self.master_cwd),
                 user_cwd)

        # Fetch the master_cwd repository.
        exec_cmd('git fetch %s' % self.username, user_cwd)

        # Get the current user branch
        _, out_branch, _ = exec_cmd('git symbolic-ref -q HEAD',
                                    self.master_cwd)

        # out_branch looks like something like :
        # refs/head/master\n. Parse it to only retrieve the branch
        # name.
        cur_branch = os.path.basename(out_branch).rstrip('\r\n')

        # Get the merge-base hash commit between the master user and the
        # current user.
        mergebase_hash = exec_cmd('git merge-base -a HEAD %s/%s' %
                                  (self.username, cur_branch),
                                  user_cwd)[1].rstrip('\r\n')

        # Get the diff between the master_cwd and the mergebase_hash.
        _, diff, _ = exec_cmd('git diff --binary --full-index %s' %
                              mergebase_hash, self.master_cwd)

        # Set the return code of the merge task to 0 by default. It means
        # there's no conflict.
        ret = 0

        # The future result string of the `git apply --check` command.
        patch_output = ""

        # If the diff is not empty, check if it can be applied in the user_cwd.
        # Otherwise, it means that there's no change, so there's no possible
        # conflict.
        if diff:
            # Create a temp file.
            tmpfile = tempfile.NamedTemporaryFile()
            try:
                # Write the diff into a temp file.
                tmpfile.write(diff)
                # After writing, rewind the file handle using seek() in order
                # to read the data back from it.
                tmpfile.seek(0)

                # Check if the diff can be applied in the master user.
                ret, patch_output, _ = exec_cmd('git apply --check %s' %
                                                tmpfile.name, user_cwd)
            finally:
                # Automatically delete the temp file.
                tmpfile.close()

        # Build the *args for the _alert method.
        alert_args = (self.project_name, self.username, user)

        # Build the **kwargs for the _alert method if there's no
        # conflict.
        alert_kwargs = {'merge_conflict': False, }

        if ret:
            # Build the **kwargs for the _alert method if there's a
            # merge conflict.x
            alert_kwargs = {
                'merge_conflict': True,
                'conflict_files': self._get_conflict_files(patch_output)
            }

        # Call the _alert method with alert_args tuple as *args
        # argument and alert_kwargs dict as **kwargs.
        self._alert(*alert_args, **alert_kwargs)

    def _get_conflict_files(self, patch_output):
        """ Parses the patch_output string and returns a readable list of
        conflict files.
        """

        conflict_files = []
        for i, line in enumerate(patch_output.split('\n')):
            if not i % 2:
                conflict_files.append(line)

        return conflict_files

    def _alert(self, project_name, username, dest_username,
               merge_conflict=False, conflict_files=[]):
        """ Creates a alert task to warn to the user the state of the
        merge.
        """

        dispatcher.put(project_name, AlertTask(project_name, username,
                                               dest_username, merge_conflict,
                                               conflict_files=conflict_files))

    def _get_user_dirs(self):
        """ A generator that returns the next user directory in the
        self.project_cwd.
        """

        for folder_name in os.listdir(self.project_cwd):
            folder_fullpath = os.path.join(self.project_cwd, folder_name)
            if folder_fullpath != self.master_cwd and \
                    os.path.isdir(folder_fullpath):
                yield folder_name

########NEW FILE########
__FILENAME__ = transport
import os
import shutil
import subprocess
import struct
import tempfile
import pickle

from threading import Event
from os.path import join

from sleekxmpp import ClientXMPP
from sleekxmpp.jid import JID
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath

from baboon.baboond.dispatcher import dispatcher
from baboon.baboond.config import config
from baboon.common import proxy_socket
from baboon.common.stanza.rsync import MergeStatus
from baboon.common.eventbus import eventbus
from baboon.common.logger import logger
from baboon.common import pyrsync


@logger
class Transport(ClientXMPP):
    """ The transport has the responsability to communicate with the
    sleekxmpp library via XMPP protocol.
    """

    def __init__(self):

        ClientXMPP.__init__(self, config['user']['jid'], config['user'][
            'passwd'])

        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0065')  # Socks5 Bytestreams
        self.pubsub_addr = config['server']['pubsub']
        self.working_dir = config['server']['working_dir']

        # Some shortcuts
        self.pubsub = self.plugin['xep_0060']
        self.streamer = self.plugin['xep_0065']

        self.disconnected = Event()
        self.pending_rsyncs = {}   # {SID => RsyncTask}
        self.pending_git_init_tasks = {}  # {BID => GitInitTask}

        # Bind all handlers to corresponding events.
        self._bind()

        # Start the XMPP connection.
        self.use_ipv6 = False
        if self.connect(use_ssl=False, use_tls=False):
            self.disconnected.clear()
            self.process()

    def close(self):
        """ Disconnect from the XMPP server.
        """

        self.streamer.close()
        self.disconnect(wait=True)
        self.disconnected.set()
        self.logger.info("Disconnected from the XMPP server.")

    def alert(self, node, msg, files=[], merge_conflict=False):
        """ Build a MergeStatus stanza and publish it to the pubsub node.
        """

        # Build the MergeStatus stanza.
        status_msg = MergeStatus()
        status_msg['node'] = node
        status_msg['status'] = msg
        status_msg['type'] = 'error' if merge_conflict else 'ok'
        status_msg.set_files(files)

        try:
            result = self.pubsub.publish(self.pubsub_addr, node,
                                         payload=status_msg)
            self.logger.debug("Published a msg to the node: %s" % node)
        except:
            self.logger.debug("Could not publish to: %s" % node)

    def _bind(self):
        """ Registers needed handlers.
        """

        self.add_event_handler('session_start', self._on_session_start)
        self.add_event_handler('failed_auth', self._on_failed_auth)
        self.add_event_handler('socks_connected', self._on_socks_connected)

        self.register_handler(Callback('First Git Init Handler',
                                       StanzaPath('iq@type=set/git-init'),
                                       self._on_git_init_stanza))

        self.register_handler(Callback('RsyncStart Handler',
                                       StanzaPath('iq@type=set/rsync'),
                                       self._on_rsync_stanza))

        self.register_handler(Callback('MergeVerification Handler',
                                       StanzaPath('iq@type=set/merge'),
                                       self._on_merge_stanza))

        eventbus.register('rsync-finished-success', self._on_rsync_success)
        eventbus.register('rsync-finished-failure', self._on_rsync_failure)
        eventbus.register('git-init-success', self._on_git_init_success)
        eventbus.register('git-init-failure', self._on_git_init_failure)

    def _on_session_start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        self.logger.info("Connected to the XMPP server.")

    def _on_failed_auth(self, event):
        """ Called when authentication failed.
        """

        self.logger.error("Authentication failed.")
        eventbus.fire('failed-auth')
        self.close()

    def _on_socks_connected(self, sid):
        """ Called when the Socks5 bytestream plugin is connected.
        """

        proxy_sock = self.streamer.get_socket(sid)
        proxy_listener = proxy_socket.listen(sid, proxy_sock,
                                             self._on_socks5_data)
        self.logger.debug("Socks5 connected.")

    def _on_git_init_stanza(self, iq):
        """ Called when a GitInit stanza is received. This handler creates a
        new GitInitTask if permissions are good.
        """

        self.logger.info("Received a git init stanza.")

        # Get the useful data.
        node = iq['git-init']['node']
        url = iq['git-init']['url']
        sfrom = iq['from'].bare

        # Ensure permissions.
        is_subscribed = self._verify_subscription(iq, sfrom, node)
        if not is_subscribed:
            eventbus.fire("rsync-finished-failure")
            return

        # Create a new GitInitTask
        from baboon.baboond.task import GitInitTask
        git_init_task = GitInitTask(node, url, sfrom)

        # Register the BaboonId of this GitInitTask in the
        # self.pending_git_init_tasks dict.
        self.pending_git_init_tasks[git_init_task.bid] = iq

        # Add the GitInitTask to the list of tasks to execute.
        dispatcher.put(node, git_init_task)

    def _on_rsync_stanza(self, iq):
        """ Called when a Rsync stanza is received. This handler creates a
        new RsyncTask if permissions are good.
        """

        self.logger.info('Received a rsync stanza.')

        # Get the useful data.
        node = iq['rsync']['node']
        sid = iq['rsync']['sid']
        rid = iq['rsync']['rid']
        files = iq['rsync']['files']
        sfrom = iq['from']
        project_path = join(self.working_dir, node, sfrom.bare)

        # Verify if the user is a subscriber/owner of the node.
        is_subscribed = self._verify_subscription(iq, sfrom.bare, node)
        if not is_subscribed:
            eventbus.fire('rsync-finished-failure', rid=rid)
            return

        # The future reply iq.
        reply = iq.reply()

        # Create the new RsyncTask.
        from task import RsyncTask
        rsync_task = RsyncTask(sid, rid, sfrom, node, project_path, files)
        dispatcher.put(node, rsync_task)

        # Register the current rsync_task in the pending_rsyncs dict.
        self.pending_rsyncs[rid] = rsync_task

        # Reply to the IQ
        reply['rsync']
        reply.send()

    def _on_merge_stanza(self, iq):
        """ Called when a MergeVerification stanza is received. This handler
        creates a new MergeTask if permissions are good.
        """

        # Get the useful data.
        sfrom = iq['from'].bare
        node = iq['merge']['node']
        project_path = join(self.working_dir, node, sfrom)

        # Verify if the user is a subscriber/owner of the node.
        is_subscribed = self._verify_subscription(iq, sfrom, node)
        if not is_subscribed:
            eventbus.fire("rsync-finished-failure")
            return

        # Verify if the server-side project is a git repository.
        is_git_repo = self._verify_git_repository(iq, node, project_path)
        if not is_git_repo:
            return

        # The future reply iq.
        reply = iq.reply()

        # Prepare the merge verification with this data.
        from task import MergeTask
        dispatcher.put(node, MergeTask(node, sfrom))

        # Reply to the request.
        reply.send()

    def _on_socks5_data(self, sid, data, **kwargs):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        self.logger.debug("Received data over socks5 socket.")

        # Get the useful data.
        node = data['node']
        rid = data['rid']
        sfrom = JID(data['from'])
        deltas = data['delta']
        project_path = join(self.working_dir, node, sfrom.bare)

        # Patch files with corresponding deltas.
        for relpath, delta in deltas:
            self._patch_file(join(project_path, relpath), delta)

        cur_rsync_task = self.pending_rsyncs.get(rid)
        if cur_rsync_task:
            cur_rsync_task.rsync_finished.set()
        else:
            self.logger.error('Rsync task %s not found.' % rid)
            # TODO: Handle this error.

    def _on_git_init_success(self, bid):
        """ Called when a git init task has been terminated successfuly.
        """

        # Retrieve the IQ associated to this BaboonId and send the response.
        iq = self.pending_git_init_tasks[bid]
        if not iq:
            self.logger.error("IQ associated with the %s BID not found." % bid)

        # Send the reply iq.
        iq.reply().send()

        # Remove the entry in the pending dict.
        del self.pending_git_init_tasks[bid]

    def _on_git_init_failure(self, bid, error):
        """ Called when a git init task has been terminated with an error.
        """

        # Display the error message.
        self.logger.error(error)

        # Retrieve the IQ associated to this BaboonId and send the response.
        iq = self.pending_git_init_tasks[bid]
        if not iq:
            self.logger.error("IQ associated with the %s BID not found." % bid)
            return

        # Send the reply error iq.
        reply = iq.reply().error()
        reply['error']['code'] = '409'
        reply['error']['type'] = 'cancel'
        reply['error']['condition'] = 'conflict'
        reply['error']['text'] = error
        reply.send()

        # Remove the entry in the pending dict.
        del self.pending_git_init_tasks[bid]

    def _on_rsync_success(self, rid, *args, **kwargs):
        """ Called when a rsync task has been terminated successfuly.
        """
        cur_rsync_task = self.pending_rsyncs.get(rid)
        if cur_rsync_task:
            self.logger.debug("RsyncTask %s finished." % rid)
            iq = self.Iq(sto=cur_rsync_task.jid, stype='set')
            iq['rsyncfinished']['node'] = cur_rsync_task.project
            iq.send(block=False)
        else:
            self.logger.error("Could not find a rsync task with RID: %s" % rid)

    def _on_rsync_failure(self, *args, **kwargs):
        """ Called when a rsync task has been terminated with an error.
        """

        rid = kwargs.get('rid')
        if rid is None:
            return

        cur_rsync_task = self.pending_rsyncs.get(rid)
        if cur_rsync_task:
            self.logger.debug("RsyncTask %s finished with an error." % rid)

            # TODO: Add a status (success/error) to the rsyncfinished iq.
            iq = self.Iq(sto=cur_rsync_task.jid, stype='set')
            iq['rsyncfinished']['node'] = cur_rsync_task.project
            iq.send(block=False)

    def _verify_subscription(self, iq, jid, node):
        """ Verify if the bare jid is a subscriber/owner on the node.
        """

        try:
            ret = self.pubsub.get_node_subscriptions(self.pubsub_addr, node)
            subscriptions = ret['pubsub_owner']['subscriptions']

            for subscription in subscriptions:
                if jid == subscription['jid']:
                    return True
        except Exception as e:
            pass

        err_msg = "you are not a contributor on %s." % node
        self._send_forbidden_error(iq.reply(), err_msg)

        return False

    def _verify_git_repository(self, iq, node, path):
        """
        """

        proc = subprocess.Popen('git status', stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, shell=True,
                                cwd=path)
        output, errorss = proc.communicate()

        if not proc.returncode:
            return True
        else:
            err_msg = ("The repository %s seems to be corrupted. Please, "
                       " (re)run the init command." % node)
            self._send_forbidden_error(iq.reply(), err_msg)

            return False

    def _patch_file(self, fullpath, delta):
        """ Patch the fullpath file with the delta.
        """

        # Open the unpatched file with the cursor at the beginning.
        unpatched = open(fullpath, 'rb')
        unpatched.seek(0)

        # Save the new file in a temporary file. Avoid to delete the file
        # when it's closed.
        save_fd = tempfile.NamedTemporaryFile(delete=False)

        # Patch the file with the delta.
        pyrsync.patchstream(unpatched, save_fd, delta)

        # Close the file (data are flushed).
        save_fd.close()

        # Rename the temporary file to the good file path.
        shutil.move(save_fd.name, fullpath)

    def _send_forbidden_error(self, iq, err_msg):
        """ Send an error iq with the err_msg as text.
        """
        iq.error()
        iq['error']['code'] = '503'
        iq['error']['type'] = 'auth'
        iq['error']['condition'] = 'forbidden'
        iq['error']['text'] = err_msg
        iq.send()


transport = Transport()

########NEW FILE########
__FILENAME__ = config
import os
import sys
import argparse

from logging import Handler
from os.path import join, dirname, abspath, expanduser, exists, isfile, isdir
from baboon.common.errors.baboon_exception import ConfigException

if sys.version_info < (2, 7):
    from baboon.common.thirdparty.dictconfig import dictConfig
else:
    from logging.config import dictConfig

if sys.version_info < (3, 0):
    from ConfigParser import RawConfigParser, Error as ConfigParserError
else:
    from configparser import RawConfigParser, Error as ConfigParserError


class NullHandler(Handler):
    """ Reimplemented the NullHandler logger for Python < 2.7.
    """

    def emit(self, record):
        pass


def get_null_handler():
    """ Return the module path of the NullHandler. Useful for Python < 2.7.
    """

    # NullHandler does not exist before Python 2.7
    null_handler_mod = 'logging.NullHandler'
    try:
        from logging import NullHandler
    except ImportError:
        null_handler_mod = 'baboon.common.config.NullHandler'

    return null_handler_mod


def get_config_path(arg_attrs, config_name):
    """ Gets the configuration path with the priority order:
    1) config command line argument
    2) <project_path>/conf/baboonrc
    3) ~/.baboonrc
    4) /etc/baboon/baboonrc
    5) environment variable : BABOONRC
    Otherwise : return None

    arg_attrs is the parser argument attributes.
    config_name is the name of the configuration file.
    """

    # Verify if the config path is specified in the command line.
    config_path = arg_attrs.get('configpath')
    if config_path:
        return config_path

    mod_path = _get_module_path()
    sys_path = ['%s/baboon/conf/%s' % (x, config_name) for x in sys.path]
    curdir_path = '%s/conf/%s' % (mod_path, config_name)
    user_path = '%s/.%s' % (expanduser('~'), config_name)
    etc_path = '/etc/baboon/%s' % config_name

    # Verify if one of the config paths (etc, user, curdir, syspath) exist.
    for loc in [etc_path, user_path, curdir_path] + sys_path:
        if isfile(loc):
            return loc

    # Otherwise, return the env BABOONRC variable or None.
    return os.environ.get("BABOONRC")


def get_config_file(arg_attrs, config_name):
    """ Returns the dict corresponding to the configuration file.
    """

    filename = get_config_path(arg_attrs, config_name)
    if not filename:
        raise ConfigException("Failed to retrieve the configuration filepath.")

    try:
        parser = RawConfigParser()
        parser.read(filename)

        file_attrs = {}
        for section in parser.sections():
            file_attrs[section] = dict(parser.items(section))

        return file_attrs
    except ConfigParserError:
        raise ConfigException("Failed to parse the configuration file: %s " %
                              filename)


def init_config_log(arg_attrs, logconf):
    """ Configures the logger level setted in the logging args
    """

    # Configure the logger with the dict logconf.
    logconf['loggers']['baboon']['level'] = arg_attrs['loglevel']
    dictConfig(logconf)


def get_config_args(parser_dict):
    """ Builds and returns the argument parser.
    """

    # Create the new global parser.
    parser = argparse.ArgumentParser(description=parser_dict['description'])

    # Add arguments to the global parser.
    for arg in parser_dict['args']:
        parser.add_argument(*arg['args'], **arg['kwargs'])

    # Iterates over all subparsers.
    if parser_dict['subparsers']:
        subparsers = parser.add_subparsers()
    for item in parser_dict['subparsers']:
        # Add the new subparser.
        subparser = subparsers.add_parser(item['name'], help=item['help'])
        subparser.set_defaults(which=item['name'])

        # Add arguments to the subparser.
        for arg in item['args']:
            subparser.add_argument(*arg['args'], **arg['kwargs'])

    args = parser.parse_args()

    # Ensure the path is an abspath.
    if hasattr(args, 'path') and args.path:
        args.path = abspath(expanduser(args.path))

    # Return a dict, not a Namespace.
    return args.__dict__


def get_log_path():
    """ Returns the correct log directory path.
    """

    # The log directory to use if there's a problem.
    fallback_logdir = expanduser('~/')

    if os.name == 'posix':
        try:
            var_log = '/var/log/baboon'
            if not os.path.exists(var_log):
                os.makedirs(var_log)
            return var_log if os.path.isdir(var_log) else fallback_logdir
        except EnvironmentError:
            pass

    return fallback_logdir


def _get_module_path():
    return dirname(dirname(abspath(__file__)))

########NEW FILE########
__FILENAME__ = baboon_exception


class CommandException(Exception):

    def __init__(self, status_code, msg=None):
        super(CommandException, self).__init__(msg)
        self.status_code = status_code


class BaboonException(Exception):
    pass


class ForbiddenException(BaboonException):
    pass


class ConfigException(BaboonException):
    pass

########NEW FILE########
__FILENAME__ = eventbus


class EventBus(object):
    """
    """

    def __init__(self):

        # The dict that associate a key (the event) and a callback.
        self._handlers = {}

        # A list of callbacks that will be removed after the first call.
        self._oneshot_callbacks = set()

    def register(self, key, callback):
        if not self._handlers.get(key):
            self._handlers[key] = set()

        self._handlers[key].add(callback)

    def register_once(self, key, callback):
        """ Associates the key to the callback. The callback will be
        automatically unregister after the call.
        """
        self.register(key, callback)
        self._oneshot_callbacks.add(callback)

    def unregister(self, key, callback):
        try:
            filter(lambda x: x is not callback, self._handlers[key])
            filter(lambda x: x is not callback, self._oneshot_callbacks)
        except KeyError:
            pass

    def fire(self, key, *args, **kwargs):
        try:
            for callback in self._handlers[key]:
                callback(*args, **kwargs)
                self.unregister(key, callback)

        except KeyError:
            pass

eventbus = EventBus()

########NEW FILE########
__FILENAME__ = file

pending = {}


class FileEvent(object):
    """ Describes a file event. Avoid to use watchdog event to have relpaths
    instead of fullpaths. In addition, if watchdog is replaced by another
    library, the rest of the code will not need to change.
    """

    CREATE = 0
    MODIF = 1
    MOVE = 2
    DELETE = 3

    def __init__(self, project, event_type, src_path, dest_path=None):
        """
        """

        self.project = project
        self.event_type = event_type
        self.src_path = src_path
        self.dest_path = dest_path

    def register(self):

        if not pending.get(self.project):
            pending[self.project] = []

        if hash(self) not in [hash(x) for x in pending[self.project]]:
            pending[self.project].append(self)

    def __hash__(self):
        return (hash(self.project) ^
                hash(self.event_type) ^
                hash(self.src_path) ^
                hash(self.dest_path))

########NEW FILE########
__FILENAME__ = logger
import logging


def logger(cls):
    """ Adds a logger class attribute to the class 'cls'.
    By default, the logger is based on the name class.

    @param cls: the class will contains the new logger
    attribute
    """
    setattr(cls, 'logger',
            logging.getLogger('baboon.%s' % cls.__name__))
    return cls

########NEW FILE########
__FILENAME__ = loghandler
import copy
import logging


class ConsoleUnixColoredHandler(logging.StreamHandler):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    COLORS = {
        'FATAL': RED,
        'ERROR': RED,
        'WARNING': YELLOW,
        'INFO': GREEN,
        'DEBUG': CYAN,
    }

    def emit(self, r):
        # Need to make a actual copy of the record to prevent altering
        # the message for other loggers.
        record = copy.copy(r)
        levelname = record.levelname

        # Configures the current colors to use.
        color = self.COLORS[record.levelname]

        # Colories the levelname of each log message
        record.levelname = self._get_fg_color(color) + str(levelname) + \
            self._reset()
        logging.StreamHandler.emit(self, record)

    def _get_fg_color(self, color):
        return '\x1B[1;3%sm' % color

    def _reset(self):
        return '\x1B[1;%sm' % self.BLACK

########NEW FILE########
__FILENAME__ = proxy_socket
import sys
import logging
import pickle
import struct
import socket
import threading
import select


from baboon.common.logger import logger

logger = logging.getLogger(__name__)


def listen(sid, sock, callback):
    """ Starts listening on the socket associated to the SID for data. When
    data is receveid, call the callback.
    """

    thread = threading.Thread(target=_run, args=(sid, sock, callback))
    thread.start()


def _run(sid, sock, callback):
    """ A thread to listen data on the sock. This thread calls the callback
    when data is received.
    """

    socket_open = True
    while socket_open:
        ins = []
        try:
            # Wait any read available data on socket. Timeout
            # after 5 secs.
            ins, out, err = select.select([sock, ], [], [], 5)
        except socket.error as (errno, err):
            # 9 means the socket is closed. It can be normal. Otherwise,
            # log the error.
            if errno != 9:
                logger.debug('Socket is closed: %s' % err)
            break
        except Exception as e:
            logger.debug(e)
            break

        for s in ins:
            data = _recv_size(sock)
            if not data:
                socket_open = False
            else:
                unpacked_data = unpack(data)
                if unpacked_data:
                    callback(sid, unpacked_data)


def _recv_size(sock):
    """ Read data on the socket and return it.
    """

    total_len = 0
    total_data = []
    size = sys.maxint
    size_data = sock_data = ''
    recv_size = 8192

    while total_len < size:
        sock_data = sock.recv(recv_size)
        if not sock_data:
            return ''.join(total_data)

        if not total_data:
            if len(sock_data) > 4:
                size_data += sock_data
                size = struct.unpack('>i', size_data[:4])[0]
                recv_size = size
                if recv_size > 524288:
                    recv_size = 524288
                total_data.append(size_data[4:])
            else:
                size_data += sock_data
        else:
            total_data.append(sock_data)
        total_len = sum([len(i) for i in total_data])
    return ''.join(total_data)


def pack(data):
    """ Packs the data.
    """

    # The data format is: `len_data`+`data`. Useful to receive all the data
    # at once (avoid splitted data) thanks to the recv_size method.
    data = pickle.dumps(data)
    return struct.pack('>i', len(data)) + data


def unpack(data):
    """ Unpacks the data. On error, log an error message and returns None.
    """

    try:
        return pickle.loads(data)
    except Exception as err:
        logger.error(err)

########NEW FILE########
__FILENAME__ = pyrsync
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
This is a pure Python implementation of the [rsync algorithm] [TM96].

Updated to use SHA256 hashing (instead of the standard implementation
which uses outdated MD5 hashes), and packages for disutils
distribution by Isis Lovecruft, <isis@patternsinthevoid.net>. The
majority of the code is blatantly stolen from Eric Pruitt's code
as posted on [ActiveState] [1].

[1]: https://code.activestate.com/recipes/577518-rsync-algorithm/

[TM96]: Andrew Tridgell and Paul Mackerras. The rsync algorithm.
Technical Report TR-CS-96-05, Canberra 0200 ACT, Australia, 1996.
http://samba.anu.edu.au/rsync/.

### Example Use Case: ###

    # On the system containing the file that needs to be patched
    >>> unpatched = open("unpatched.file", "rb")
    >>> hashes = blockchecksums(unpatched)

    # On the remote system after having received `hashes`
    >>> patchedfile = open("patched.file", "rb")
    >>> delta = rsyncdelta(patchedfile, hashes)

    # System with the unpatched file after receiving `delta`
    >>> unpatched.seek(0)
    >>> save_to = open("locally-patched.file", "wb")
    >>> patchstream(unpatched, save_to, delta)
"""

import collections
import hashlib

if not(hasattr(__builtins__, "bytes")) or str is bytes:
    # Python 2.x compatibility
    def bytes(var, *args):
        try:
            return ''.join(map(chr, var))
        except TypeError:
            return map(ord, var)

__all__ = ["rollingchecksum", "weakchecksum", "patchstream", "rsyncdelta",
           "blockchecksums"]


def rsyncdelta(datastream, remotesignatures, blocksize=4096):
    """
    Generates a binary patch when supplied with the weak and strong
    hashes from an unpatched target and a readable stream for the
    up-to-date data. The blocksize must be the same as the value
    used to generate remotesignatures.
    """
    remote_weak, remote_strong = remotesignatures

    match = True
    matchblock = -1
    deltaqueue = collections.deque()

    while True:
        if match and datastream is not None:
            # Whenever there is a match or the loop is running for the first
            # time, populate the window using weakchecksum instead of rolling
            # through every single byte which takes at least twice as long.
            window = collections.deque(bytes(datastream.read(blocksize)))
            checksum, a, b = weakchecksum(window)

        try:
            # If there are two identical weak checksums in a file, and the
            # matching strong hash does not occur at the first match, it will
            # be missed and the data sent over. May fix eventually, but this
            # problem arises very rarely.
            matchblock = remote_weak.index(checksum, matchblock + 1)
            stronghash = hashlib.sha256(bytes(window)).hexdigest()
            matchblock = remote_strong.index(stronghash, matchblock)

            match = True
            deltaqueue.append(matchblock)

            if datastream.closed:
                break
            continue

        except ValueError:
            # The weakchecksum did not match
            match = False
            try:
                if datastream:
                    # Get the next byte and affix to the window
                    newbyte = ord(datastream.read(1))
                    window.append(newbyte)
            except TypeError:
                # No more data from the file; the window will slowly shrink.
                # newbyte needs to be zero from here on to keep the checksum
                # correct.
                newbyte = 0
                tailsize = datastream.tell() % blocksize
                datastream = None

            if datastream is None and len(window) <= tailsize:
                # The likelihood that any blocks will match after this is
                # nearly nil so call it quits.
                deltaqueue.append(window)
                break

            # Yank off the extra byte and calculate the new window checksum
            oldbyte = window.popleft()
            checksum, a, b = rollingchecksum(oldbyte, newbyte, a, b, blocksize)

            # Add the old byte the file delta. This is data that was not found
            # inside of a matching block so it needs to be sent to the target.
            try:
                deltaqueue[-1].append(oldbyte)
            except (AttributeError, IndexError):
                deltaqueue.append([oldbyte])

    # Return a delta that starts with the blocksize and converts all iterables
    # to bytes.
    deltastructure = [blocksize]
    for element in deltaqueue:
        if isinstance(element, int):
            deltastructure.append(element)
        elif element:
            deltastructure.append(bytes(element))

    return deltastructure


def blockchecksums(instream, blocksize=4096):
    """
    Returns a list of weak and strong hashes for each block of the
    defined size for the given data stream.
    """
    weakhashes = list()
    stronghashes = list()
    read = instream.read(blocksize)

    while read:
        weakhashes.append(weakchecksum(bytes(read))[0])
        stronghashes.append(hashlib.sha256(read).hexdigest())
        read = instream.read(blocksize)

    return weakhashes, stronghashes


def patchstream(instream, outstream, delta):
    """
    Patches instream using the supplied delta and write the resultantant
    data to outstream.
    """
    blocksize = delta[0]

    for element in delta[1:]:
        if isinstance(element, int) and blocksize:
            instream.seek(element * blocksize)
            element = instream.read(blocksize)
        outstream.write(element)


def rollingchecksum(removed, new, a, b, blocksize=4096):
    """
    Generates a new weak checksum when supplied with the internal state
    of the checksum calculation for the previous window, the removed
    byte, and the added byte.
    """
    a -= removed - new
    b -= removed * blocksize - a
    return (b << 16) | a, a, b


def weakchecksum(data):
    """
    Generates a weak checksum from an iterable set of bytes.
    """
    a = b = 0
    l = len(data)
    for i in range(l):
        a += data[i]
        b += (l - i) * data[i]

    return (b << 16) | a, a, b

########NEW FILE########
__FILENAME__ = rsync
from sleekxmpp.xmlstream import register_stanza_plugin, ElementBase, ET
from sleekxmpp import Iq

from baboon.common.file import FileEvent


class GitInit(ElementBase):
    name = 'git-init'
    namespace = 'baboon'
    plugin_attrib = 'git-init'
    interfaces = set(('node', 'url',))


class Rsync(ElementBase):
    name = 'rsync'
    namespace = 'baboon'
    plugin_attrib = 'rsync'
    interfaces = set(('sid', 'rid', 'node', 'files', 'create_files',
                      'move_files', 'delete_files'))
    sub_interfaces = set(('files', 'create_files', 'move_files',
                          'delete_files'))

    def get_files(self):

        files = []

        for element in self.xml.getchildren():
            tag_name = element.tag.split('}', 1)[-1]
            file_event_type = None

            if tag_name == 'file':
                file_event_type = FileEvent.MODIF
            elif tag_name == 'create_file':
                file_event_type = FileEvent.CREATE
            elif tag_name == 'move_file':
                file_event_type = FileEvent.MOVE
            elif tag_name == 'delete_file':
                file_event_type = FileEvent.DELETE

            file_event = FileEvent(self['node'], file_event_type, element.text)
            files.append(file_event)

        return files

    def add_file(self, f):
        file_xml = ET.Element('{%s}file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_files(self, files):
        for f in files:
            self.add_file(f)

    def add_create_file(self, f):
        file_xml = ET.Element('{%s}create_file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_create_files(self, files):
        for f in files:
            self.add_create_file(f)

    def add_delete_file(self, f):
        file_xml = ET.Element('{%s}delete_file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_delete_files(self, files):
        for f in files:
            self.add_delete_file(f)

    def add_move_file(self, f):
        file_xml = ET.Element('{%s}move_file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_move_files(self, files):
        for f in files:
            self.add_move_file(f)


class RsyncFinished(ElementBase):
    name = 'rsyncfinished'
    namespace = 'baboon'
    interfaces = set(('node', ))
    plugin_attrib = 'rsyncfinished'


class MergeVerification(ElementBase):
    name = 'merge_verification'
    namespace = 'baboon'
    interfaces = set(('node', ))
    plugin_attrib = 'merge'


class MergeStatus(ElementBase):
    name = 'merge_status'
    namespace = 'baboon'
    interfaces = set(('node', 'status', 'files', 'type'))
    subinterfaces = set(('files',))
    plugin_attrib = 'merge_status'

    def get_files(self):
        return [element.text for element in self.xml.getchildren()]

    def add_file(self, f):
        file_xml = ET.Element('{%s}file' % self.namespace)
        file_xml.text = f
        self.xml.append(file_xml)

    def set_files(self, files):
        for f in files:
            self.add_file(f)

register_stanza_plugin(Iq, GitInit)
register_stanza_plugin(Iq, Rsync)
register_stanza_plugin(Iq, RsyncFinished)
register_stanza_plugin(Iq, MergeVerification)
register_stanza_plugin(Iq, MergeStatus)

########NEW FILE########
__FILENAME__ = dictconfig
# Copyright 2009-2010 by Vinay Sajip. All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted,
# provided that the above copyright notice appear in all copies and that
# both that copyright notice and this permission notice appear in
# supporting documentation, and that the name of Vinay Sajip
# not be used in advertising or publicity pertaining to distribution
# of the software without specific, written prior permission.
# VINAY SAJIP DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING
# ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# VINAY SAJIP BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR
# ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER
# IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import logging.handlers
import re
import sys
import types

IDENTIFIER = re.compile('^[a-z_][a-z0-9_]*$', re.I)


def valid_ident(s):
    m = IDENTIFIER.match(s)
    if not m:
        raise ValueError('Not a valid Python identifier: %r' % s)
    return True

#
# This function is defined in logging only in recent versions of Python
#
try:
    from logging import _checkLevel
except ImportError:
    def _checkLevel(level):
        if isinstance(level, int):
            rv = level
        elif str(level) == level:
            if level not in logging._levelNames:
                raise ValueError('Unknown level: %r' % level)
            rv = logging._levelNames[level]
        else:
            raise TypeError('Level not an integer or a '
                            'valid string: %r' % level)
        return rv

# The ConvertingXXX classes are wrappers around standard Python containers,
# and they serve to convert any suitable values in the container. The
# conversion converts base dicts, lists and tuples to their wrapped
# equivalents, whereas strings which match a conversion format are converted
# appropriately.
#
# Each wrapper should have a configurator attribute holding the actual
# configurator to use for conversion.


class ConvertingDict(dict):
    """A converting dictionary wrapper."""

    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    def get(self, key, default=None):
        value = dict.get(self, key, default)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    def pop(self, key, default=None):
        value = dict.pop(self, key, default)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result


class ConvertingList(list):
    """A converting list wrapper."""
    def __getitem__(self, key):
        value = list.__getitem__(self, key)
        result = self.configurator.convert(value)
        #If the converted value is different, save for next time
        if value is not result:
            self[key] = result
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result

    def pop(self, idx=-1):
        value = list.pop(self, idx)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
        return result


class ConvertingTuple(tuple):
    """A converting tuple wrapper."""
    def __getitem__(self, key):
        value = tuple.__getitem__(self, key)
        result = self.configurator.convert(value)
        if value is not result:
            if type(result) in (ConvertingDict, ConvertingList,
                                ConvertingTuple):
                result.parent = self
                result.key = key
        return result


class BaseConfigurator(object):
    """
    The configurator base class which defines some useful defaults.
    """

    CONVERT_PATTERN = re.compile(r'^(?P<prefix>[a-z]+)://(?P<suffix>.*)$')

    WORD_PATTERN = re.compile(r'^\s*(\w+)\s*')
    DOT_PATTERN = re.compile(r'^\.\s*(\w+)\s*')
    INDEX_PATTERN = re.compile(r'^\[\s*(\w+)\s*\]\s*')
    DIGIT_PATTERN = re.compile(r'^\d+$')

    value_converters = {
        'ext': 'ext_convert',
        'cfg': 'cfg_convert',
    }

    # We might want to use a different one, e.g. importlib
    importer = __import__

    def __init__(self, config):
        self.config = ConvertingDict(config)
        self.config.configurator = self

    def resolve(self, s):
        """
        Resolve strings to objects using standard import and attribute
        syntax.
        """
        name = s.split('.')
        used = name.pop(0)
        try:
            found = self.importer(used)
            for frag in name:
                used += '.' + frag
                try:
                    found = getattr(found, frag)
                except AttributeError:
                    self.importer(used)
                    found = getattr(found, frag)
            return found
        except ImportError:
            e, tb = sys.exc_info()[1:]
            v = ValueError('Cannot resolve %r: %s' % (s, e))
            v.__cause__, v.__traceback__ = e, tb
            raise v

    def ext_convert(self, value):
        """Default converter for the ext:// protocol."""
        return self.resolve(value)

    def cfg_convert(self, value):
        """Default converter for the cfg:// protocol."""
        rest = value
        m = self.WORD_PATTERN.match(rest)
        if m is None:
            raise ValueError("Unable to convert %r" % value)
        else:
            rest = rest[m.end():]
            d = self.config[m.groups()[0]]
            #print d, rest
            while rest:
                m = self.DOT_PATTERN.match(rest)
                if m:
                    d = d[m.groups()[0]]
                else:
                    m = self.INDEX_PATTERN.match(rest)
                    if m:
                        idx = m.groups()[0]
                        if not self.DIGIT_PATTERN.match(idx):
                            d = d[idx]
                        else:
                            try:
                                # try as number first (mostlikely)
                                n = int(idx)
                                d = d[n]
                            except TypeError:
                                d = d[idx]
                if m:
                    rest = rest[m.end():]
                else:
                    raise ValueError('Unable to convert '
                                     '%r at %r' % (value, rest))
        #rest should be empty
        return d

    def convert(self, value):
        """
        Convert values to an appropriate type. dicts, lists and tuples are
        replaced by their converting alternatives. Strings are checked to
        see if they have a conversion format and are converted if they do.
        """
        if not isinstance(value, ConvertingDict) and isinstance(value, dict):
            value = ConvertingDict(value)
            value.configurator = self
        elif not isinstance(value, ConvertingList) and isinstance(value, list):
            value = ConvertingList(value)
            value.configurator = self
        elif not isinstance(value, ConvertingTuple) and \
                isinstance(value, tuple):
            value = ConvertingTuple(value)
            value.configurator = self
        elif isinstance(value, basestring):  # str for py3k
            m = self.CONVERT_PATTERN.match(value)
            if m:
                d = m.groupdict()
                prefix = d['prefix']
                converter = self.value_converters.get(prefix, None)
                if converter:
                    suffix = d['suffix']
                    converter = getattr(self, converter)
                    value = converter(suffix)
        return value

    def configure_custom(self, config):
        """Configure an object with a user-supplied factory."""
        c = config.pop('()')
        if not hasattr(c, '__call__') and hasattr(types, 'ClassType') and \
                type(c) != types.ClassType:
            c = self.resolve(c)
        props = config.pop('.', None)
        # Check for valid identifiers
        kwargs = dict([(k, config[k]) for k in config if valid_ident(k)])
        result = c(**kwargs)
        if props:
            for name, value in props.items():
                setattr(result, name, value)
        return result

    def as_tuple(self, value):
        """Utility function which converts lists to tuples."""
        if isinstance(value, list):
            value = tuple(value)
        return value


class DictConfigurator(BaseConfigurator):
    """
    Configure logging using a dictionary-like object to describe the
    configuration.
    """

    def configure(self):
        """Do the configuration."""

        config = self.config
        if 'version' not in config:
            raise ValueError("dictionary doesn't specify a version")
        if config['version'] != 1:
            raise ValueError("Unsupported version: %s" % config['version'])
        incremental = config.pop('incremental', False)
        EMPTY_DICT = {}
        logging._acquireLock()
        try:
            if incremental:
                handlers = config.get('handlers', EMPTY_DICT)
                # incremental handler config only if handler name
                # ties in to logging._handlers (Python 2.7)
                if sys.version_info[:2] == (2, 7):
                    for name in handlers:
                        if name not in logging._handlers:
                            raise ValueError('No handler found with '
                                             'name %r' % name)
                        else:
                            try:
                                handler = logging._handlers[name]
                                handler_config = handlers[name]
                                level = handler_config.get('level', None)
                                if level:
                                    handler.setLevel(_checkLevel(level))
                            except StandardError, e:
                                raise ValueError('Unable to configure handler '
                                                 '%r: %s' % (name, e))
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    try:
                        self.configure_logger(name, loggers[name], True)
                    except StandardError, e:
                        raise ValueError('Unable to configure logger '
                                         '%r: %s' % (name, e))
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root, True)
                    except StandardError, e:
                        raise ValueError('Unable to configure root '
                                         'logger: %s' % e)
            else:
                disable_existing = config.pop('disable_existing_loggers', True)

                logging._handlers.clear()
                del logging._handlerList[:]

                # Do formatters first - they don't refer to anything else
                formatters = config.get('formatters', EMPTY_DICT)
                for name in formatters:
                    try:
                        formatters[name] = self.configure_formatter(
                            formatters[name])
                    except StandardError, e:
                        raise ValueError('Unable to configure '
                                         'formatter %r: %s' % (name, e))
                # Next, do filters - they don't refer to anything else, either
                filters = config.get('filters', EMPTY_DICT)
                for name in filters:
                    try:
                        filters[name] = self.configure_filter(filters[name])
                    except StandardError, e:
                        raise ValueError('Unable to configure '
                                         'filter %r: %s' % (name, e))

                # Next, do handlers - they refer to formatters and filters
                # As handlers can refer to other handlers, sort the keys
                # to allow a deterministic order of configuration
                handlers = config.get('handlers', EMPTY_DICT)
                for name in sorted(handlers):
                    try:
                        handler = self.configure_handler(handlers[name])
                        handler.name = name
                        handlers[name] = handler
                    except StandardError, e:
                        raise ValueError('Unable to configure handler '
                                         '%r: %s' % (name, e))
                # Next, do loggers - they refer to handlers and filters

                #we don't want to lose the existing loggers,
                #since other threads may have pointers to them.
                #existing is set to contain all existing loggers,
                #and as we go through the new configuration we
                #remove any which are configured. At the end,
                #what's left in existing is the set of loggers
                #which were in the previous configuration but
                #which are not in the new configuration.
                root = logging.root
                existing = root.manager.loggerDict.keys()
                #The list needs to be sorted so that we can
                #avoid disabling child loggers of explicitly
                #named loggers. With a sorted list it is easier
                #to find the child loggers.
                existing.sort()
                #We'll keep the list of existing loggers
                #which are children of named loggers here...
                child_loggers = []
                #now set up the new ones...
                loggers = config.get('loggers', EMPTY_DICT)
                for name in loggers:
                    if name in existing:
                        i = existing.index(name)
                        prefixed = name + "."
                        pflen = len(prefixed)
                        num_existing = len(existing)
                        i = i + 1  # look at the entry after name
                        while (i < num_existing) and\
                              (existing[i][:pflen] == prefixed):
                            child_loggers.append(existing[i])
                            i = i + 1
                        existing.remove(name)
                    try:
                        self.configure_logger(name, loggers[name])
                    except StandardError, e:
                        raise ValueError('Unable to configure logger '
                                         '%r: %s' % (name, e))

                #Disable any old loggers. There's no point deleting
                #them as other threads may continue to hold references
                #and by disabling them, you stop them doing any logging.
                #However, don't disable children of named loggers, as that's
                #probably not what was intended by the user.
                for log in existing:
                    logger = root.manager.loggerDict[log]
                    if log in child_loggers:
                        logger.level = logging.NOTSET
                        logger.handlers = []
                        logger.propagate = True
                    elif disable_existing:
                        logger.disabled = True

                # And finally, do the root logger
                root = config.get('root', None)
                if root:
                    try:
                        self.configure_root(root)
                    except StandardError, e:
                        raise ValueError('Unable to configure root '
                                         'logger: %s' % e)
        finally:
            logging._releaseLock()

    def configure_formatter(self, config):
        """Configure a formatter from a dictionary."""
        if '()' in config:
            factory = config['()']  # for use in exception handler
            try:
                result = self.configure_custom(config)
            except TypeError, te:
                if "'format'" not in str(te):
                    raise
                #Name of parameter changed from fmt to format.
                #Retry with old name.
                #This is so that code can be used with older Python versions
                #(e.g. by Django)
                config['fmt'] = config.pop('format')
                config['()'] = factory
                result = self.configure_custom(config)
        else:
            fmt = config.get('format', None)
            dfmt = config.get('datefmt', None)
            result = logging.Formatter(fmt, dfmt)
        return result

    def configure_filter(self, config):
        """Configure a filter from a dictionary."""
        if '()' in config:
            result = self.configure_custom(config)
        else:
            name = config.get('name', '')
            result = logging.Filter(name)
        return result

    def add_filters(self, filterer, filters):
        """Add filters to a filterer from a list of names."""
        for f in filters:
            try:
                filterer.addFilter(self.config['filters'][f])
            except StandardError, e:
                raise ValueError('Unable to add filter %r: %s' % (f, e))

    def configure_handler(self, config):
        """Configure a handler from a dictionary."""
        formatter = config.pop('formatter', None)
        if formatter:
            try:
                formatter = self.config['formatters'][formatter]
            except StandardError, e:
                raise ValueError('Unable to set formatter '
                                 '%r: %s' % (formatter, e))
        level = config.pop('level', None)
        filters = config.pop('filters', None)
        if '()' in config:
            c = config.pop('()')
            if not hasattr(c, '__call__') and hasattr(types, 'ClassType') and \
                    type(c) != types.ClassType:
                c = self.resolve(c)
            factory = c
        else:
            klass = self.resolve(config.pop('class'))
            #Special case for handler which refers to another handler
            if issubclass(klass, logging.handlers.MemoryHandler) and \
                    'target' in config:
                try:
                    config['target'] = self.config['handlers'][config[
                        'target']]
                except StandardError, e:
                    raise ValueError('Unable to set target handler '
                                     '%r: %s' % (config['target'], e))
            elif issubclass(klass, logging.handlers.SMTPHandler) and \
                    'mailhost' in config:
                config['mailhost'] = self.as_tuple(config['mailhost'])
            elif issubclass(klass, logging.handlers.SysLogHandler) and \
                    'address' in config:
                config['address'] = self.as_tuple(config['address'])
            factory = klass
        kwargs = dict([(k, config[k]) for k in config if valid_ident(k)])
        try:
            result = factory(**kwargs)
        except TypeError, te:
            if "'stream'" not in str(te):
                raise
            #The argument name changed from strm to stream
            #Retry with old name.
            #This is so that code can be used with older Python versions
            #(e.g. by Django)
            kwargs['strm'] = kwargs.pop('stream')
            result = factory(**kwargs)
        if formatter:
            result.setFormatter(formatter)
        if level is not None:
            result.setLevel(_checkLevel(level))
        if filters:
            self.add_filters(result, filters)
        return result

    def add_handlers(self, logger, handlers):
        """Add handlers to a logger from a list of names."""
        for h in handlers:
            try:
                logger.addHandler(self.config['handlers'][h])
            except StandardError, e:
                raise ValueError('Unable to add handler %r: %s' % (h, e))

    def common_logger_config(self, logger, config, incremental=False):
        """
        Perform configuration which is common to root and non-root loggers.
        """
        level = config.get('level', None)
        if level is not None:
            logger.setLevel(_checkLevel(level))
        if not incremental:
            #Remove any existing handlers
            for h in logger.handlers[:]:
                logger.removeHandler(h)
            handlers = config.get('handlers', None)
            if handlers:
                self.add_handlers(logger, handlers)
            filters = config.get('filters', None)
            if filters:
                self.add_filters(logger, filters)

    def configure_logger(self, name, config, incremental=False):
        """Configure a non-root logger from a dictionary."""
        logger = logging.getLogger(name)
        self.common_logger_config(logger, config, incremental)
        propagate = config.get('propagate', None)
        if propagate is not None:
            logger.propagate = propagate

    def configure_root(self, config, incremental=False):
        """Configure a root logger from a dictionary."""
        root = logging.getLogger()
        self.common_logger_config(root, config, incremental)


dictConfigClass = DictConfigurator


def dictConfig(config):
    """Configure logging using a dictionary."""
    dictConfigClass(config).configure()

########NEW FILE########
__FILENAME__ = utils
import subprocess


def cmp_to_key(mycmp):
    """ Converts a cmp= function into a key= function.
    """

    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0

        def __hash__(self):
            raise TypeError('hash not implemented')

    return K


def exec_cmd(cmd, cwd=None):
    """ Execute the cmd command in a subprocess.
    """

    # Create the process and run it.
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, shell=True, cwd=cwd)
    output, errors = proc.communicate()

    return (proc.returncode, output, errors)

########NEW FILE########
