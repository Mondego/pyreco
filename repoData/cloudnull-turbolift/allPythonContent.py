__FILENAME__ = turbolift.local
#!/usr/bin/env python
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

import os
import sys

possible_topdir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                os.pardir, os.pardir))
if os.path.exists(os.path.join(possible_topdir, 'turbolift',
                  '__init__.py')):
    sys.path.insert(0, possible_topdir)

from turbolift import executable
executable.run_turbolift()

########NEW FILE########
__FILENAME__ = create_container
# =============================================================================
# Copyright [2014] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

import os


HOME = os.getenv('HOME')


# Set some default args
import turbolift
args = turbolift.ARGS = {
    'os_user': 'YOURUSERNAME',    # Username
    'os_apikey': 'YOURAPIKEY',    # API-Key
    'os_rax_auth': 'YOURREGION',  # RAX Region, must be UPPERCASE
    'error_retry': 5,             # Number of failure retries
    'quiet': True                 # Make the application not print stdout
}


# Load our Logger
from turbolift.logger import logger
log_method = logger.load_in(
    log_level='info',
    log_file='turbolift_library',
    log_location=HOME
)


# Load our constants
turbolift.load_constants(log_method, args)


# Authenticate against the swift API
from turbolift.authentication import authentication
authentication = authentication.authenticate()


# Package up the Payload
import turbolift.utils.http_utils as http
payload = http.prep_payload(
    auth=authentication,
    container=args.get('container'),
    source=args.get('source'),
    args=args
)


# Load all of our available cloud actions
from turbolift.clouderator import actions
cf_actions = actions.CloudActions(payload=payload)


# Create a Container if it does not already exist
# =============================================================================
kwargs = {
    'url': payload['url'],              # Defines the Upload URL
    'container': payload['c_name']      # Sets the container
}

# Create the container if needed
create_container = cf_actions.container_create(**kwargs)
print('Container Created: "%s"' % create_container)

########NEW FILE########
__FILENAME__ = delete_objects
# =============================================================================
# Copyright [2014] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

import os


HOME = os.getenv('HOME')


# Set some default args
import turbolift
args = turbolift.ARGS = {
    'os_user': 'YOURUSERNAME',    # Username
    'os_apikey': 'YOURAPIKEY',    # API-Key
    'os_rax_auth': 'YOURREGION',  # RAX Region, must be UPPERCASE
    'error_retry': 5,             # Number of failure retries
    'container': 'test9000',      # Name of the container
    'quiet': True,                # Make the application not print stdout
    'batch_size': 30000           # The number of jobs to do per cycle
}


# Load our Logger
from turbolift.logger import logger
log_method = logger.load_in(
    log_level='info',
    log_file='turbolift_library',
    log_location=HOME
)


# Load our constants
turbolift.load_constants(log_method, args)


# Authenticate against the swift API
from turbolift.authentication import authentication
authentication = authentication.authenticate()


# Package up the Payload
import turbolift.utils.http_utils as http
payload = http.prep_payload(
    auth=authentication,
    container=args.get('container'),
    source=args.get('source'),
    args=args
)


# Load all of our available cloud actions
from turbolift.clouderator import actions
cf_actions = actions.CloudActions(payload=payload)


# Delete file(s)
# =============================================================================
import turbolift.utils.multi_utils as multi

kwargs = {
    'url': payload['url'],              # Defines the Upload URL
    'container': payload['c_name']      # Sets the container
}

# Return a list of all objects that we will delete
objects, list_count, last_obj = cf_actions.object_lister(**kwargs)

# Get a list of all of the object names
object_names = [obj['name'] for obj in objects]

# Set the delete job
kwargs['cf_job'] = cf_actions.object_deleter

# Perform the upload job
multi.job_processer(
    num_jobs=list_count,
    objects=object_names,
    job_action=multi.doerator,
    concur=50,
    kwargs=kwargs
)

########NEW FILE########
__FILENAME__ = list_containers
# =============================================================================
# Copyright [2014] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

import os
import json


HOME = os.getenv('HOME')


# Set some default args
import turbolift
args = turbolift.ARGS = {
    'os_user': 'YOURUSERNAME',    # Username
    'os_apikey': 'YOURAPIKEY',    # API-Key
    'os_rax_auth': 'YOURREGION',  # RAX Region, must be UPPERCASE
    'error_retry': 5,             # Number of failure retries
    'quiet': True                 # Make the application not print stdout
}


# Load our Logger
from turbolift.logger import logger
log_method = logger.load_in(
    log_level='info',
    log_file='turbolift_library',
    log_location=HOME
)


# Load our constants
turbolift.load_constants(log_method, args)


# Authenticate against the swift API
from turbolift.authentication import authentication
authentication = authentication.authenticate()


# Package up the Payload
import turbolift.utils.http_utils as http
payload = http.prep_payload(
    auth=authentication,
    container=args.get('container'),
    source=args.get('source'),
    args=args
)


# Load all of our available cloud actions
from turbolift.clouderator import actions
cf_actions = actions.CloudActions(payload=payload)


# List Containers
# =============================================================================
kwargs = {
    'url': payload['url']
}
containers, list_count, last_container = cf_actions.container_lister(**kwargs)
print(json.dumps(containers, indent=2))
print('number of containers: [ %s ]' % list_count)
print('Last container in query: [ %s ]' % last_container)

########NEW FILE########
__FILENAME__ = list_objects
# =============================================================================
# Copyright [2014] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

import os
import json


HOME = os.getenv('HOME')


# Set some default args
import turbolift
args = turbolift.ARGS = {
    'os_user': 'YOURUSERNAME',    # Username
    'os_apikey': 'YOURAPIKEY',    # API-Key
    'os_rax_auth': 'YOURREGION',  # RAX Region, must be UPPERCASE
    'error_retry': 5,             # Number of failure retries
    'quiet': True,                # Make the application not print stdout
    'container': 'test9000'       # Name of the container
}


# Load our Logger
from turbolift.logger import logger
log_method = logger.load_in(
    log_level='info',
    log_file='turbolift_library',
    log_location=HOME
)


# Load our constants
turbolift.load_constants(log_method, args)


# Authenticate against the swift API
from turbolift.authentication import authentication
authentication = authentication.authenticate()


# Package up the Payload
import turbolift.utils.http_utils as http
payload = http.prep_payload(
    auth=authentication,
    container=args.get('container'),
    source=args.get('source'),
    args=args
)


# Load all of our available cloud actions
from turbolift.clouderator import actions
cf_actions = actions.CloudActions(payload=payload)


# List Objects
# =============================================================================
kwargs = {
    'url': payload['url'],              # Defines the Upload URL
    'container': payload['c_name']      # Sets the container
}

# Return a list of all objects that we will delete
objects, list_count, last_obj = cf_actions.object_lister(**kwargs)
print(json.dumps(objects, indent=2))
print('number of containers: [ %s ]' % list_count)
print('Last object in query: [ %s ]' % last_obj)

########NEW FILE########
__FILENAME__ = upload_files
# =============================================================================
# Copyright [2014] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import os

HOME = os.getenv('HOME')


# Set some default args
import turbolift
args = turbolift.ARGS = {
    'os_user': 'YOURUSERNAME',    # Username
    'os_apikey': 'YOURAPIKEY',    # API-Key
    'os_rax_auth': 'YOURREGION',  # RAX Region, must be UPPERCASE
    'error_retry': 5,             # Number of failure retries
    'source': '/tmp/files',       # local source for files to be uploaded
    'container': 'test9000',      # Name of the container
    'quiet': True,                # Make the application not print stdout
    'batch_size': 30000           # The number of jobs to do per cycle
}


# Load our Logger
from turbolift.logger import logger
log_method = logger.load_in(
    log_level='info',
    log_file='turbolift_library',
    log_location=HOME
)


# Load our constants
turbolift.load_constants(log_method, args)


# Authenticate against the swift API
from turbolift.authentication import authentication
authentication = authentication.authenticate()


# Package up the Payload
import turbolift.utils.http_utils as http
payload = http.prep_payload(
    auth=authentication,
    container=args.get('container'),
    source=args.get('source'),
    args=args
)


# Load all of our available cloud actions
from turbolift.clouderator import actions
cf_actions = actions.CloudActions(payload=payload)


# Upload file(s)
# =============================================================================
import turbolift.utils.multi_utils as multi
from turbolift import methods

f_indexed = methods.get_local_files()   # Index all of the local files
num_files = len(f_indexed)              # counts the indexed files

kwargs = {
    'url': payload['url'],              # Defines the Upload URL
    'container': payload['c_name'],     # Sets the container
    'source': payload['source'],        # Defines the local source to upload
    'cf_job': cf_actions.object_putter  # sets the job
}

# Perform the upload job
multi.job_processer(
    num_jobs=num_files,
    objects=f_indexed,
    job_action=multi.doerator,
    concur=25,
    kwargs=kwargs
)

########NEW FILE########
__FILENAME__ = archive
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================


def archive_actions(subparser, multi_source_args, container_args, regex):
    """Archive Arguments.

    :param subparser:
    :param multi_source_args:
    :param shared_args:
    :param cdn_args:
    """

    archaction = subparser.add_parser('archive',
                                      parents=[multi_source_args,
                                               container_args,
                                               regex],
                                      help=('Compress files or directories'
                                            ' into a single archive'))
    archaction.set_defaults(archive=True)
    archaction.add_argument('--tar-name',
                            metavar='<name>',
                            help='Name To Use for the Archive')
    archaction.add_argument('--no-cleanup',
                            action='store_true',
                            help=('Used to keep the compressed Archive.'
                                  ' The archive will be left in the Users'
                                  ' Home Folder'))
    archaction.add_argument('--verify',
                            action='store_true',
                            help=('Will open a created archive and verify'
                                  ' its contents. Used when needing to know'
                                  ' without a doubt that all the files that'
                                  ' were specified were compressed.'))

########NEW FILE########
__FILENAME__ = authgroup
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import os

from turbolift import info


def auth_group(parser):
    """Base Authentication Argument Set."""

    authgroup = parser.add_argument_group('Authentication',
                                          'Authentication against'
                                          ' the OpenStack API')

    a_keytype = authgroup.add_mutually_exclusive_group()
    a_keytype.add_argument('-a',
                           '--os-apikey',
                           metavar='[API_KEY]',
                           help='Defaults to env[OS_API_KEY]',
                           default=os.environ.get('OS_API_KEY', None))
    a_keytype.add_argument('-p',
                           '--os-password',
                           metavar='[PASSWORD]',
                           help='Defaults to env[OS_PASSWORD]',
                           default=os.environ.get('OS_PASSWORD', None))

    authgroup.add_argument('-u',
                           '--os-user',
                           metavar='[USERNAME]',
                           help='Defaults to env[OS_USERNAME]',
                           default=os.environ.get('OS_USERNAME', None))
    authgroup.add_argument('--os-tenant',
                           metavar='[TENANT]',
                           help='Defaults to env[OS_TENANT]',
                           default=os.environ.get('OS_TENANT', None))
    authgroup.add_argument('--os-token',
                           metavar='[TOKEN]',
                           help='Defaults to env[OS_TOKEN]',
                           default=os.environ.get('OS_TOKEN', None))

    a_regiontype = authgroup.add_mutually_exclusive_group()
    a_regiontype.add_argument('-r',
                              '--os-region',
                              metavar='[REGION]',
                              help='Defaults to env[OS_REGION_NAME]',
                              default=os.environ.get('OS_REGION_NAME', None))
    a_regiontype.add_argument('--os-rax-auth',
                              choices=info.__rax_regions__,
                              help=('Authentication Plugin for Rackspace Cloud'
                                    ' env[OS_RAX_AUTH]'),
                              default=os.getenv('OS_RAX_AUTH', None))
    a_regiontype.add_argument('--os-hp-auth',
                              choices=info.__hpc_regions__,
                              help=('Authentication Plugin for HP Cloud'
                                    ' env[OS_HP_AUTH]'),
                              default=os.getenv('OS_HP_AUTH', None))

    authgroup.add_argument('--os-auth-url',
                           metavar='[AUTH_URL]',
                           help='Defaults to env[OS_AUTH_URL]',
                           default=os.environ.get('OS_AUTH_URL', None))
    authgroup.add_argument('--os-version',
                           metavar='[VERSION_NUM]',
                           default=os.getenv('OS_VERSION', 'v2.0'),
                           help='env[OS_VERSION]')

########NEW FILE########
__FILENAME__ = clone
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================


def clone_actions(subparser, time_args):
    """Uploading Arguments.

    :param subparser:
    """

    # Provides for the stream Function.
    clone = subparser.add_parser(
        'clone',
        parents=[time_args],
        help='Clone Objects from one container to another.'
    )
    clone.set_defaults(clone=True)
    clone.add_argument('-sc',
                       '--source-container',
                       metavar='[CONTAINER]',
                       help='Target Container.',
                       required=True,
                       default=None)
    clone.add_argument('-tc',
                       '--target-container',
                       metavar='[CONTAINER]',
                       help='Target Container.',
                       required=True,
                       default=None)
    clone.add_argument('-tr',
                       '--target-region',
                       metavar='[REGION]',
                       help='Target Container.',
                       required=True,
                       default=None)
    clone.add_argument('--target-snet',
                       action='store_true',
                       help='Use Service Net to Stream the Objects.',
                       default=False)
    clone.add_argument('--clone-headers',
                       action='store_true',
                       help=('Query the source object for headers and restore'
                             ' them on the target.'),
                       default=False)
    clone.add_argument('--save-newer',
                       action='store_true',
                       help=('Check to see if the target "last_modified" time'
                             ' is newer than the source. If "True" upload is'
                             ' skipped.'),
                       default=False)
    clone.add_argument('--add-only',
                       action='store_true',
                       help=('Clone the object only if it doesn\'t exist in'
                             ' the target container.'),
                       default=False)

########NEW FILE########
__FILENAME__ = command
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================


def command_actions(subparser, source_args, container_args, cdn_args,
                    time_args, regex):
    """Uploading Arguments.

    :param subparser:
    :param source_args:
    :param container_args:
    :param cdn_args:
    """

    # Provides for the show Function.
    show = subparser.add_parser(
        'show',
        parents=[container_args],
        help='List Objects in a container.'
    )
    show.set_defaults(show=True)
    show_group = show.add_mutually_exclusive_group()
    show_group.add_argument('-o',
                            '--object',
                            metavar='[NAME]',
                            help='Target Object.',
                            default=None)
    show_group.add_argument('--cdn-info',
                            action='store_true',
                            help='Show Info on the Container for CDN',
                            default=None)

    # Provides for the list Function.
    lister = subparser.add_parser(
        'list',
        parents=[time_args, regex],
        help='List Objects in a container.'
    )
    lister.set_defaults(list=True)
    list_group = lister.add_mutually_exclusive_group(required=True)
    list_group.add_argument('-c',
                            '--container',
                            metavar='[CONTAINER]',
                            help='Target Container.',
                            default=None)
    list_group.add_argument('--all-containers',
                            action='store_true',
                            help='Target Container.',
                            default=None)
    lister.add_argument('--max-jobs',
                        metavar='[INT]',
                        default=None,
                        type=int,
                        help='Max number of processed on a single pass')
    lister.add_argument('--object-index',
                        metavar='[INT]',
                        help='Return the object from the index.',
                        type=int,
                        default=None)
    lister.add_argument('--filter',
                        metavar='[NAME]',
                        help='Filter returned list by name.',
                        default=None)

    # Provides for the list Function.
    updater = subparser.add_parser(
        'update',
        parents=[time_args, regex],
        help='Update Object headers from within a container.  This will'
             ' overwrite existing object headers with new ones as specified'
             ' on the command line.  See optional argment, "-OH"'
    )
    updater.set_defaults(update=True)
    update_group = updater.add_mutually_exclusive_group(required=True)
    update_group.add_argument('-c',
                              '--container',
                              metavar='[CONTAINER]',
                              help='Target Container.',
                              default=None)
    updater.add_argument('--max-jobs',
                         metavar='[INT]',
                         default=None,
                         type=int,
                         help='Max number of processed on a single pass')
    updater.add_argument('-o',
                         '--object',
                         metavar='[NAME]',
                         help='Target Object.',
                         default=None)
    updater.add_argument('--filter',
                         metavar='[NAME]',
                         help='Filter returned list by name.',
                         default=None)

    # Provides for the CDN Toggle Function.
    cdn_command = subparser.add_parser(
        'cdn-command',
        parents=[cdn_args],
        help='Run CDN Commands on a Container.'
    )
    cdn_command.set_defaults(cdn_command=True)
    cdn_command.add_argument('-c',
                             '--container',
                             metavar='[CONTAINER]',
                             help='Target Container.',
                             required=True,
                             default=None)

    cdn_command_group = cdn_command.add_mutually_exclusive_group(required=True)
    cdn_command_group.add_argument('--purge',
                                   metavar='[NAME]',
                                   help=('Purge a specific Object from the'
                                         ' CDN, This can be used multiple'
                                         ' times.'),
                                   default=[],
                                   action='append')
    cdn_command_group.add_argument('--enabled',
                                   action='store_true',
                                   default=None,
                                   help='Enable the CDN for a Container')
    cdn_command_group.add_argument('--disable',
                                   action='store_false',
                                   default=None,
                                   help='Disable the CDN for a Container')

########NEW FILE########
__FILENAME__ = delete
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================


def delete_actions(subparser, del_args, container_args, regex):
    delaction = subparser.add_parser('delete',
                                     parents=[del_args, container_args, regex],
                                     help=('Deletes everything in a given'
                                           ' container Including the'
                                           ' container.'))
    delaction.set_defaults(delete=True)

########NEW FILE########
__FILENAME__ = download
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================


def download_actions(subparser, source_args, container_args, time_args, regex):
    """Download Actions.

    :param subparser:
    :param source_args:
    :param shared_args:
    """

    download = subparser.add_parser('download',
                                    parents=[source_args,
                                             container_args,
                                             time_args,
                                             regex],
                                    help=('Downloads everything from a'
                                          ' given container creating a'
                                          ' target Directory if it does'
                                          ' not exist'))
    download.set_defaults(download=True)
    download.add_argument('--index-from',
                          metavar='[NAME]',
                          default=None,
                          type=str,
                          help='file Path to begin the download from')
    download.add_argument('--max-jobs',
                          metavar='[INT]',
                          default=None,
                          type=int,
                          help='Max number of processed on a single pass')
    download.add_argument('--sync',
                          action='store_true',
                          help=('Looks at local file vs Remote File and if a'
                                ' difference is detected the file is'
                                ' uploaded.'),
                          default=None)
    download.add_argument('--restore-perms',
                          action='store_true',
                          help=('If The object has permissions saved as'
                                ' metadata restore those permissions on the'
                                ' local object'),
                          default=None)
    dwfilter = download.add_mutually_exclusive_group()
    dwfilter.add_argument('-o',
                          '--object',
                          metavar='[NAME]',
                          default=[],
                          action='append',
                          help=('Name of a specific Object that you want'
                                ' to Download.'))
    dwfilter.add_argument('-d',
                          '--dir',
                          metavar='[NAME]',
                          default=None,
                          type=str,
                          help=('Name of a directory path that you want'
                                ' to Download.'))

########NEW FILE########
__FILENAME__ = headers
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

BASE_HEADERS = [
    "Connection=Keep-alive",
    "User-Agent=turbolift"
]


def header_args(parser):
    """Add in Optional Header Arguments."""

    headers = parser.add_argument_group('Header Options',
                                        'Headers are Parsed as KEY=VALUE'
                                        ' arguments. This is useful when'
                                        ' setting a custom header when'
                                        ' using a CDN URL or other HTTP'
                                        ' action which may rely on Headers.'
                                        ' Here are the default headers')
    headers.add_argument('-BH', '--base-headers',
                         metavar='[K=V]',
                         default=BASE_HEADERS,
                         action='append',
                         help=('These are the basic headers used for'
                               ' all Turbolift operations. Anything'
                               ' added here will modify ALL Turbolift'
                               ' Operations which leverage the API.'))
    headers.add_argument('-OH', '--object-headers',
                         metavar='[K=V]',
                         default=[],
                         action='append',
                         help=('These Headers only effect Objects'
                               ' (files).'))
    headers.add_argument('-CH', '--container-headers',
                         metavar='[K=V]',
                         default=[],
                         action='append',
                         help='These headers only effect Containers')

########NEW FILE########
__FILENAME__ = optionals
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import os


def optional_args(parser):
    """Add in all optional Arguments."""

    optionals = parser.add_argument_group('Additional Options',
                                          'Things you might want to'
                                          ' add to your operation')
    optionals.add_argument('-P',
                           '--preserve-path',
                           action='store_true',
                           help=('This will preserve the full path to a file'
                                 ' when uploaded to a container.'))
    optionals.add_argument('-I',
                           '--internal',
                           action='store_true',
                           help='Use Service Network',
                           default=os.getenv('TURBO_INTERNAL', None))
    optionals.add_argument('--error-retry',
                           metavar='[ATTEMPTS]',
                           type=int,
                           default=os.getenv('TURBO_ERROR_RETRY', 5),
                           help=('This option sets the number of attempts'
                                 ' %(prog)s will attempt an operation'
                                 ' before quiting. The default is 5. This'
                                 ' is useful if you have a spotty'
                                 ' network or ISP.'))
    optionals.add_argument('--cc',
                           metavar='[CONCURRENCY]',
                           type=int,
                           help='Upload Concurrency',
                           default=os.getenv('TURBO_CONCURRENCY', 50))
    optionals.add_argument('--service-type',
                           type=str,
                           default='cloudFiles',
                           help='Service Type for Use in object storage.'),
    optionals.add_argument('--colorized',
                           action='store_true',
                           help='Colored output, effects logs and STDOUT.')
    optionals.add_argument('--log-location',
                           type=str,
                           default=os.getenv('TURBO_LOGS', os.getenv('HOME')),
                           help=('Change the log location, Default is Home.'
                                 'The DEFAULT is the users HOME Dir.'))
    optionals.add_argument('--log-file',
                           type=str,
                           default=os.getenv('TURBO_LOGFILE', 'turbolift.log'),
                           help=('Change the log file'
                                 ' Log File is %(default)s.'))
    optionals.add_argument('--quiet',
                           action='store_true',
                           help='Make %(prog)s Shut the hell up',
                           default=os.getenv('TURBO_QUIET', None))
    optionals.add_argument('--verbose',
                           action='store_true',
                           help='Be verbose While Uploading',
                           default=os.getenv('TURBO_VERBOSE', None))
    optionals.add_argument('--debug',
                           action='store_true',
                           help='Turn up verbosity to over 9000',
                           default=os.getenv('TURBO_DEBUG', None))
    optionals.add_argument('--batch-size',
                           metavar='[INT]',
                           type=int,
                           help=('The number of files to process per job.'
                                 ' Default is %(default)sK'),
                           default=30000)

########NEW FILE########
__FILENAME__ = tsync
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================


def tsync_actions(subparser, source_args, container_args):
    """Tsync Arguments.

    :param source_args:
    :param shared_args:
    :param cdn_args:
    :param subparser:
    """

    tsync = subparser.add_parser(
        'tsync',
        parents=[source_args, container_args],
        help='Deprecated, Please use "upload --sync" instead'
    )
    tsync.set_defaults(tsync=True)

########NEW FILE########
__FILENAME__ = upload
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================


def upload_actions(subparser, source_args, container_args, time_args, regex):
    """Uploading Arguments.

    :param subparser:
    :param source_args:
    :param shared_args:
    :param cdn_args:
    """

    upload = subparser.add_parser(
        'upload',
        parents=[source_args, container_args, time_args, regex],
        help='Upload files to SWIFT, -CloudFiles-'
    )
    upload.set_defaults(upload=True)
    upload.add_argument('--exclude',
                        action='append',
                        help='Exclude a pattern when uploading',
                        default=[])
    upload.add_argument('--sync',
                        action='store_true',
                        help=('Looks at local file vs Remote File and if a '
                              'difference is detected the file is uploaded.'),
                        default=False)
    upload.add_argument('--delete-remote',
                        action='store_true',
                        help=('Compare the REMOTE container and LOCAL file'
                              ' system and if the REMOTE container has objects'
                              ' NOT found in the LOCAL File System, DELETE THE'
                              ' REMOTE OBJECTS.'),
                        default=False)
    upload.add_argument('--save-perms',
                        action='store_true',
                        help=('Save the UID, GID, and MODE, of a file as meta'
                              ' data on the object.'),
                        default=False)
    upload.add_argument('-d',
                        '--dir',
                        metavar='[NAME]',
                        default=None,
                        type=str,
                        help=('Name of a directory path that you want'
                              ' to Upload to.'))
########NEW FILE########
__FILENAME__ = authentication
"""Perform Openstack Authentication."""

import json
import traceback

import turbolift as turbo
import turbolift.utils.auth_utils as auth
import turbolift.utils.http_utils as http
import turbolift.utils.report_utils as report

from turbolift import LOG


def authenticate():
    """Authentication For Openstack API.

    Pulls the full Openstack Service Catalog Credentials are the Users API
    Username and Key/Password "osauth" has a Built in Rackspace Method for
    Authentication

    Set a DC Endpoint and Authentication URL for the OpenStack environment
    """

    # Setup the request variables
    url = auth.parse_region()
    a_url = http.parse_url(url=url, auth=True)
    auth_json = auth.parse_reqtype()

    # remove the prefix for the Authentication URL if Found
    LOG.debug('POST == REQUEST DICT > JSON DUMP %s', auth_json)
    auth_json_req = json.dumps(auth_json)
    headers = {'Content-Type': 'application/json'}

    # Send Request
    try:
        auth_resp = http.post_request(
            url=a_url, headers=headers, body=auth_json_req
        )
        if auth_resp.status_code >= 300:
            raise SystemExit(
                'Authentication Failure, %s %s' % (auth_resp.status_code,
                                                   auth_resp.reason)
            )
    except ValueError as exp:
        LOG.error('Authentication Failure %s\n%s', exp, traceback.format_exc())
        raise turbo.SystemProblem('JSON Decode Failure. ERROR: %s' % exp)
    else:
        LOG.debug('POST Authentication Response %s', auth_resp.json())
        auth_info = auth.parse_auth_response(auth_resp.json())
        token, tenant, user, inet, enet, cnet, acfep = auth_info
        report.reporter(
            msg=('API Access Granted. TenantID: %s Username: %s'
                 % (tenant, user)),
            prt=False,
            log=True
        )
        return token, tenant, user, inet, enet, cnet, a_url, acfep


def get_new_token():
    """Authenticate and return only a new token.

    :return token:
    """

    return authenticate()[0]

########NEW FILE########
__FILENAME__ = actions
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift as turbo
import turbolift.clouderator as cloud
import turbolift.methods as meth
import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.report_utils as report

from turbolift.authentication.authentication import get_new_token

from turbolift import ARGS


class CloudActions(object):
    def __init__(self, payload):
        self.payload = payload

    def resp_exception(self, resp):
        """If we encounter an exception in our upload.

        we will look at how we can attempt to resolve the exception.

        :param resp:
        """

        # Check to make sure we have all the bits needed
        if not hasattr(resp, 'status_code'):
            raise turbo.SystemProblem('No Status to check.')
        elif resp is None:
            raise turbo.SystemProblem('No response information.')
        elif resp.status_code == 401:
            report.reporter(
                msg=('Turbolift experienced an Authentication issue.'
                     ' STATUS %s REASON %s REQUEST %s. Turbolift will retry'
                     % (resp.status_code, resp.reason, resp.request)),
                lvl='warn',
                log=True,
                prt=False
            )

            # This was done in this manor due to how manager dicts are proxied
            # related : http://bugs.python.org/issue6766
            headers = self.payload['headers']
            headers['X-Auth-Token'] = get_new_token()
            self.payload['headers'] = headers

            raise turbo.AuthenticationProblem(
                'Attempting to resolve the Authentication issue.'
            )
        elif resp.status_code == 404:
            report.reporter(
                msg=('Not found STATUS: %s, REASON: %s, MESSAGE: %s'
                     % (resp.status_code, resp.reason, resp.request)),
                prt=False,
                lvl='debug'
            )
        elif resp.status_code == 413:
            _di = resp.headers
            basic.stupid_hack(wait=_di.get('retry_after', 10))
            raise turbo.SystemProblem(
                'The System encountered an API limitation and will'
                ' continue in "%s" Seconds' % _di.get('retry_after')
            )
        elif resp.status_code == 502:
            raise turbo.SystemProblem('Failure making Connection')
        elif resp.status_code == 503:
            basic.stupid_hack(wait=10)
            raise turbo.SystemProblem('SWIFT-API FAILURE')
        elif resp.status_code == 504:
            basic.stupid_hack(wait=10)
            raise turbo.SystemProblem('Gateway Time-out')
        elif resp.status_code >= 300:
            raise turbo.SystemProblem(
                'SWIFT-API FAILURE -> REASON %s REQUEST %s' % (resp.reason,
                                                               resp.request)
            )
        else:
            report.reporter(
                msg=('MESSAGE %s %s %s' % (resp.status_code,
                                           resp.reason,
                                           resp.request)),
                prt=False,
                lvl='debug'
            )

    def _checker(self, url, rpath, lpath, fheaders, skip):
        """Check to see if a local file and a target file are different.

        :param url:
        :param rpath:
        :param lpath:
        :param retry:
        :param fheaders:
        :return True|False:
        """

        if skip is True:
            return True
        elif ARGS.get('sync'):
            resp = self._header_getter(url=url,
                                       rpath=rpath,
                                       fheaders=fheaders)
            if resp.status_code == 404:
                return True
            elif cloud.md5_checker(resp=resp, local_f=lpath) is True:
                return True
            else:
                return False
        else:
            return True

    def _downloader(self, url, rpath, fheaders, lfile, source,
                    skip=False):
        """Download a specified object in the container.

        :param url:
        :param rpath:
        :param fheaders:
        :param lfile:
        :param skip:
        """

        resp = None

        if source is None:
            local_f = lfile
        else:
            local_f = basic.jpath(root=source, inode=lfile)

        if self._checker(url, rpath, local_f, fheaders, skip) is True:
            report.reporter(
                msg='Downloading remote %s to local file %s' % (rpath, lfile),
                prt=False,
                lvl='debug',
            )

            # Perform Object GET
            resp = http.get_request(
                url=url, rpath=rpath, headers=fheaders, stream=True
            )
            self.resp_exception(resp=resp)
            local_f = basic.collision_rename(file_name=local_f)

            # Open our source file and write it
            with open(local_f, 'wb') as f_name:
                for chunk in resp.iter_content(chunk_size=2048):
                    if chunk:
                        f_name.write(chunk)
                        f_name.flush()
            resp.close()

        if ARGS.get('restore_perms') is not None:
            # Make a connection
            if resp is None:
                resp = self._header_getter(
                    url=url, rpath=rpath, fheaders=fheaders
                )

            all_headers = resp.headers

            if all(['x-object-meta-group' in all_headers,
                    'x-object-meta-owner' in all_headers,
                    'x-object-meta-perms' in all_headers]):
                basic.restor_perms(local_file=local_f, headers=all_headers)
            else:
                report.reporter(
                    msg=('No Permissions were restored, because none were'
                         ' saved on the object "%s"' % rpath),
                    lvl='warn',
                    log=True
                )

    def _deleter(self, url, rpath, fheaders):
        """Delete a specified object in the container.

        :param url:
        :param rpath:
        :param fheaders:
        """

        # perform Object Delete
        resp = http.delete_request(url=url, headers=fheaders, rpath=rpath)
        self.resp_exception(resp=resp)

        report.reporter(
            msg=('OBJECT %s MESSAGE %s %s %s'
                 % (rpath, resp.status_code, resp.reason, resp.request)),
            prt=False,
            lvl='debug'
        )

    def _putter(self, url, fpath, rpath, fheaders, skip=False):
        """Place  object into the container.

        :param url:
        :param fpath:
        :param rpath:
        :param fheaders:
        """

        if self._checker(url, rpath, fpath, fheaders, skip) is True:
            report.reporter(
                msg='OBJECT ORIGIN %s RPATH %s' % (fpath, rpath),
                prt=False,
                lvl='debug'
            )

            if basic.file_exists(fpath) is False:
                return None
            else:
                with open(fpath, 'rb') as f_open:
                    resp = http.put_request(
                        url=url, rpath=rpath, body=f_open, headers=fheaders
                    )
                    self.resp_exception(resp=resp)

    def _list_getter(self, url, filepath, fheaders, last_obj=None):
        """Get a list of all objects in a container.

        :param url:
        :param filepath:
        :param fheaders:
        :return list:
        """

        def _marker_type(base, last):
            """Set and return the marker.

            :param base:
            :param last:
            :return str:
            """

            if last is None:
                return base
            else:
                return _last_marker(f_path=base, l_obj=last)

        def _last_marker(f_path, l_obj):
            """Set Marker.

            :param f_path:
            :param l_obj:
            :return str:
            """

            return '%s&marker=%s' % (f_path, http.quoter(url=l_obj))

        def _obj_index(b_path, m_path):
            f_list = []
            l_obj = None

            while True:
                resp = http.get_request(
                    url=url, rpath=m_path, headers=fheaders
                )
                self.resp_exception(resp=resp)
                return_list = resp.json()

                for obj in return_list:
                    time_offset = ARGS.get('time_offset')
                    if time_offset is not None:
                        # Get the last_modified data from the Object.
                        if cloud.time_delta(lmobj=time_offset) is True:
                            f_list.append(obj)
                    else:
                        f_list.append(obj)

                last_obj_in_list = f_list[-1].get('name')
                if ARGS.get('max_jobs', ARGS.get('object_index')) is not None:
                    max_jobs = ARGS.get('max_jobs', ARGS.get('object_index'))
                    if max_jobs <= len(f_list):
                        return f_list[:max_jobs]
                    elif l_obj is last_obj_in_list:
                        return f_list
                    else:
                        l_obj = last_obj_in_list
                        m_path = _marker_type(
                            base=b_path, last=last_obj_in_list
                        )
                else:
                    if l_obj is last_obj_in_list:
                        return f_list
                    else:
                        l_obj = last_obj_in_list
                        m_path = _marker_type(
                            base=b_path, last=last_obj_in_list
                        )

        # Quote the file path.
        base_path = marked_path = (
            '%s/?limit=10000&format=json' % basic.ustr(filepath)
        )
        if last_obj is not None:
            marked_path = _last_marker(
                f_path=base_path,
                l_obj=http.quoter(url=last_obj)
            )

        for retry in basic.retryloop(attempts=ARGS.get('error_retry'),
                                     obj='Object List Creation'):
            with meth.operation(retry, obj='%s %s' % (fheaders, filepath)):
                file_list = _obj_index(base_path, marked_path)
                final_list = basic.unique_list_dicts(
                    dlist=file_list, key='name'
                )
                list_count = len(final_list)
                report.reporter(
                    msg='INFO: %d object(s) found' % len(final_list),
                    log=True
                )
                if 'name' in file_list[-1]:
                    return final_list, list_count, file_list[-1]['name']
                else:
                    return final_list, list_count, file_list[-1]

    def _header_getter(self, url, rpath, fheaders):
        """perfrom HEAD request on a specified object in the container.

        :param url:
        :param rpath:
        :param fheaders:
        """

        # perform Object HEAD request
        resp = http.head_request(url=url, headers=fheaders, rpath=rpath)
        self.resp_exception(resp=resp)
        return resp

    def _header_poster(self, url, rpath, fheaders):
        """POST Headers on a specified object in the container.

        :param url:
        :param rpath:
        :param fheaders:
        """

        # perform Object POST request for header update.
        resp = http.post_request(url=url, rpath=rpath, headers=fheaders)
        self.resp_exception(resp=resp)

        report.reporter(
            msg='STATUS: %s MESSAGE: %s REASON: %s' % (resp.status_code,
                                                       resp.request,
                                                       resp.reason),
            prt=False,
            lvl='debug'
        )

        return resp.headers

    def detail_show(self, url):
        """Return Details on an object or container."""

        rty_count = ARGS.get('error_retry')
        for retry in basic.retryloop(attempts=rty_count,
                                     delay=5,
                                     obj=ARGS.get('container')):
            if ARGS.get('object') is not None:
                rpath = http.quoter(url=url.path,
                                    cont=ARGS.get('container'),
                                    ufile=ARGS.get('object'))
            else:
                rpath = http.quoter(url=url.path,
                                    cont=ARGS.get('container'))
            fheaders = self.payload['headers']
            with meth.operation(retry, obj='%s %s' % (fheaders, rpath)):
                return self._header_getter(url=url,
                                           rpath=rpath,
                                           fheaders=fheaders)

    def container_create(self, url, container):
        """Create a container if it is not Found.

        :param url:
        :param container:
        """

        rty_count = ARGS.get('error_retry')
        for retry in basic.retryloop(attempts=rty_count,
                                     delay=5,
                                     obj=container):

            rpath = http.quoter(url=url.path,
                                cont=container)

            fheaders = self.payload['headers']
            with meth.operation(retry, obj='%s %s' % (fheaders, rpath)):
                resp = self._header_getter(url=url,
                                           rpath=rpath,
                                           fheaders=fheaders)

                # Check that the status was a good one
                if resp.status_code == 404:
                    report.reporter(msg='Creating Container => %s' % container)
                    http.put_request(url=url, rpath=rpath, headers=fheaders)
                    self.resp_exception(resp=resp)
                    report.reporter(msg='Container "%s" Created' % container)
                    return True
                else:
                    report.reporter(msg='Container "%s" Found' % container)
                    return False

    def container_cdn_command(self, url, container, sfile=None):
        """Command your CDN enabled Container.

        :param url:
        :param container:
        """

        rty_count = ARGS.get('error_retry')
        for retry in basic.retryloop(attempts=rty_count, delay=2, obj=sfile):
            cheaders = self.payload['headers']
            if sfile is not None:
                rpath = http.quoter(url=url.path,
                                    cont=container,
                                    ufile=sfile)
                # perform CDN Object DELETE
                adddata = '%s %s' % (cheaders, container)
                with meth.operation(retry, obj=adddata):
                    resp = http.delete_request(
                        url=url, rpath=rpath, headers=cheaders
                    )
                    self.resp_exception(resp=resp)
            else:
                rpath = http.quoter(url=url.path,
                                    cont=container)
                http.cdn_toggle(headers=cheaders)

                # perform CDN Enable PUT
                adddata = '%s %s' % (cheaders, container)
                with meth.operation(retry, obj=adddata):
                    resp = http.put_request(
                        url=url, rpath=rpath, headers=cheaders
                    )
                    self.resp_exception(resp=resp)

            report.reporter(
                msg='OBJECT %s MESSAGE %s %s %s' % (rpath,
                                                    resp.status_code,
                                                    resp.reason,
                                                    resp.request),
                prt=False,
                lvl='debug'
            )

    def container_deleter(self, url, container):
        """Delete all objects in a container.

        :param url:
        :param container:
        """

        for retry in basic.retryloop(attempts=ARGS.get('error_retry'),
                                     delay=2,
                                     obj=container):
            fheaders = self.payload['headers']
            rpath = http.quoter(url=url.path, cont=container)
            with meth.operation(retry, obj='%s %s' % (fheaders, container)):
                # Perform delete.
                self._deleter(url=url,
                              rpath=rpath,
                              fheaders=fheaders)

    def container_lister(self, url, last_obj=None):
        """Builds a long list of objects found in a container.

        NOTE: This could be millions of Objects.

        :param url:
        :return None | list:
        """

        for retry in basic.retryloop(attempts=ARGS.get('error_retry'),
                                     obj='Container List'):

            fheaders = self.payload['headers']
            fpath = http.quoter(url=url.path)
            with meth.operation(retry, obj='%s %s' % (fheaders, fpath)):
                resp = self._header_getter(url=url,
                                           rpath=fpath,
                                           fheaders=fheaders)

                head_check = resp.headers
                container_count = head_check.get('x-account-container-count')
                if container_count:
                    container_count = int(container_count)
                    if not container_count > 0:
                        return None
                else:
                    return None

                # Set the number of loops that we are going to do
                return self._list_getter(url=url,
                                         filepath=fpath,
                                         fheaders=fheaders,
                                         last_obj=last_obj)

    def object_updater(self, url, container, u_file):
        """Update an existing object in a swift container.

        This method will place new headers on an existing object.

        :param url:
        :param container:
        :param u_file:
        """

        for retry in basic.retryloop(attempts=ARGS.get('error_retry'),
                                     delay=2,
                                     obj=u_file):

            # HTML Encode the path for the file
            rpath = http.quoter(url=url.path,
                                cont=container,
                                ufile=u_file)

            fheaders = self.payload['headers']
            if ARGS.get('object_headers') is not None:
                fheaders.update(ARGS.get('object_headers'))
            if ARGS.get('save_perms') is not None:
                fheaders.update(basic.stat_file(local_file=u_file))

            with meth.operation(retry, obj='%s %s' % (fheaders, u_file)):
                self._header_poster(url=url,
                                    rpath=rpath,
                                    fheaders=fheaders)

    def object_putter(self, url, container, source, u_file):
        """This is the Sync method which uploads files to the swift repository

        if they are not already found. If a file "name" is found locally and
        in the swift repository an MD5 comparison is done between the two
        files. If the MD5 is miss-matched the local file is uploaded to the
        repository. If custom meta data is specified, and the object exists the
        method will put the metadata onto the object.

        :param url:
        :param container:
        :param source:
        :param u_file:
        """

        for retry in basic.retryloop(attempts=ARGS.get('error_retry'),
                                     delay=2,
                                     obj=u_file):

            # Open connection and perform operation

            # Get the path ready for action
            sfile = basic.get_sfile(ufile=u_file, source=source)

            if ARGS.get('dir'):
                container = '%s/%s' % (container, ARGS['dir'].strip('/'))

            rpath = http.quoter(url=url.path,
                                cont=container,
                                ufile=sfile)

            fheaders = self.payload['headers']

            if ARGS.get('object_headers') is not None:
                fheaders.update(ARGS.get('object_headers'))
            if ARGS.get('save_perms') is not None:
                fheaders.update(basic.stat_file(local_file=u_file))

            with meth.operation(retry, obj='%s %s' % (fheaders, u_file)):
                self._putter(url=url,
                             fpath=u_file,
                             rpath=rpath,
                             fheaders=fheaders)

    def object_deleter(self, url, container, u_file):
        """Deletes an objects in a container.

        :param url:
        :param container:
        :param u_file:
        """
        rty_count = ARGS.get('error_retry')
        for retry in basic.retryloop(attempts=rty_count, delay=2, obj=u_file):
            fheaders = self.payload['headers']
            rpath = http.quoter(url=url.path,
                                cont=container,
                                ufile=u_file)

                # Make a connection
            with meth.operation(retry, obj='%s %s' % (fheaders, rpath)):
                resp = self._header_getter(url=url,
                                           rpath=rpath,
                                           fheaders=fheaders)
                if not resp.status_code == 404:
                    # Perform delete.
                    self._deleter(url=url,
                                  rpath=rpath,
                                  fheaders=fheaders)

    def object_downloader(self, url, container, source, u_file):
        """Download an Object from a Container.

        :param url:
        :param container:
        :param u_file:
        """

        rty_count = ARGS.get('error_retry')
        for retry in basic.retryloop(attempts=rty_count, delay=2, obj=u_file):
            fheaders = self.payload['headers']
            rpath = http.quoter(url=url.path,
                                cont=container,
                                ufile=u_file)
            with meth.operation(retry, obj='%s %s' % (fheaders, u_file)):
                self._downloader(url=url,
                                 rpath=rpath,
                                 fheaders=fheaders,
                                 lfile=u_file,
                                 source=source)

    def object_lister(self, url, container, object_count=None, last_obj=None):
        """Builds a long list of objects found in a container.

        NOTE: This could be millions of Objects.

        :param url:
        :param container:
        :param object_count:
        :param last_obj:
        :return None | list:
        """

        for retry in basic.retryloop(attempts=ARGS.get('error_retry'),
                                     obj='Object List'):
            fheaders = self.payload['headers']
            fpath = http.quoter(url=url.path,
                                cont=container)
            with meth.operation(retry, obj='%s %s' % (fheaders, fpath)):
                resp = self._header_getter(url=url,
                                           rpath=fpath,
                                           fheaders=fheaders)
                if resp.status_code == 404:
                    report.reporter(
                        msg='Not found. %s | %s' % (resp.status_code,
                                                    resp.request)
                    )
                    return None, None, None
                else:
                    if object_count is None:
                        object_count = resp.headers.get(
                            'x-container-object-count'
                        )
                        if object_count:
                            object_count = int(object_count)
                            if not object_count > 0:
                                return None, None, None
                        else:
                            return None, None, None

                    # Set the number of loops that we are going to do
                    return self._list_getter(url=url,
                                             filepath=fpath,
                                             fheaders=fheaders,
                                             last_obj=last_obj)

    def object_syncer(self, surl, turl, scontainer, tcontainer, u_file):
        """Download an Object from one Container and the upload it to a target.

        :param surl:
        :param turl:
        :param scontainer:
        :param tcontainer:
        :param u_file:
        """

        def _cleanup():
            """Ensure that our temp file is removed."""
            if locals().get('tfile') is not None:
                basic.remove_file(tfile)

        def _time_difference(obj_resp, obj):
            if ARGS.get('save_newer') is True:
                # Get the source object last modified time.
                compare_time = obj_resp.header.get('last_modified')
                if compare_time is None:
                    return True
                elif cloud.time_delta(compare_time=compare_time,
                                      lmobj=obj['last_modified']) is True:
                    return False
                else:
                    return True
            else:
                return True

        def _compare(obj_resp, obj):
            if obj_resp.status_code == 404:
                report.reporter(
                    msg='Target Object %s not found' % obj['name'],
                    prt=False
                )
                return True
            elif ARGS.get('add_only'):
                report.reporter(
                    msg='Target Object %s already exists' % obj['name'],
                    prt=True
                )
                return False
            elif obj_resp.headers.get('etag') != obj['hash']:
                report.reporter(
                    msg=('Checksum Mismatch on Target Object %s'
                         % u_file['name']),
                    prt=False,
                    lvl='debug'
                )
                return _time_difference(obj_resp, obj)
            else:
                return False

        fheaders = self.payload['headers']
        for retry in basic.retryloop(attempts=ARGS.get('error_retry'),
                                     delay=5,
                                     obj=u_file['name']):
            # Open connection and perform operation
            spath = http.quoter(url=surl.path,
                                cont=scontainer,
                                ufile=u_file['name'])
            tpath = http.quoter(url=turl.path,
                                cont=tcontainer,
                                ufile=u_file['name'])

            with meth.operation(retry, obj='%s %s' % (fheaders, tpath)):
                resp = self._header_getter(url=turl,
                                           rpath=tpath,
                                           fheaders=fheaders)

                # If object comparison is True GET then PUT object
                if _compare(resp, u_file) is not True:
                    return None
            try:
                # Open Connection for source Download
                with meth.operation(retry, obj='%s %s' % (fheaders, spath)):
                    # make a temp file.
                    tfile = basic.create_tmp()

                    # Make a connection
                    resp = self._header_getter(url=surl,
                                               rpath=spath,
                                               fheaders=fheaders)
                    sheaders = resp.headers
                    self._downloader(
                        url=surl,
                        rpath=spath,
                        fheaders=fheaders,
                        lfile=tfile,
                        source=None,
                        skip=True
                    )

                for _retry in basic.retryloop(attempts=ARGS.get('error_retry'),
                                              delay=5,
                                              obj=u_file):
                    # open connection for target upload.
                    adddata = '%s %s' % (fheaders, u_file)
                    with meth.operation(_retry, obj=adddata, cleanup=_cleanup):
                        resp = self._header_getter(url=turl,
                                                   rpath=tpath,
                                                   fheaders=fheaders)
                        self.resp_exception(resp=resp)
                        # PUT remote object
                        self._putter(url=turl,
                                     fpath=tfile,
                                     rpath=tpath,
                                     fheaders=fheaders,
                                     skip=True)

                        # let the system rest for 1 seconds.
                        basic.stupid_hack(wait=1)

                        # With the source headers POST new headers on target
                        if ARGS.get('clone_headers') is True:
                            theaders = resp.headers
                            for key in sheaders.keys():
                                if key not in theaders:
                                    fheaders.update({key: sheaders[key]})
                            # Force the SOURCE content Type on the Target.
                            fheaders.update(
                                {'content-type': sheaders.get('content-type')}
                            )
                            self._header_poster(
                                url=turl,
                                rpath=tpath,
                                fheaders=fheaders
                            )
            finally:
                _cleanup()

########NEW FILE########
__FILENAME__ = executable
#!/usr/bin/env python
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import sys

import turbolift as turbo
from turbolift import arguments
from turbolift import load_constants
from turbolift.logger import logger


def run_turbolift():
    """This is the run section of the application Turbolift."""

    if len(sys.argv) <= 1:
        arguments.get_help()
        raise SystemExit('Give me something to do and I will do it')
    else:
        args = arguments.get_args()
        log = logger.load_in(log_level=args.get('log_level', 'info'),
                             log_file=args.get('log_file'),
                             log_location=args.get('log_location', '/var/log'))
        log.debug('set arguments %s', args)
        load_constants(log_method=log, args=args)
        try:
            from turbolift import worker
            worker.start_work()
        except KeyboardInterrupt:
            turbo.emergency_kill(reclaim=True)
        finally:
            if args.get('quiet') is not True:
                print('All Done!')
            log.info('Job Finished.')


if __name__ == "__main__":
    run_turbolift()

########NEW FILE########
__FILENAME__ = info
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

__author__ = "Kevin Carter"
__contact__ = "Kevin Carter"
__email__ = "kevin@cloudnull.com"
__copyright__ = "2014 All Rights Reserved"
__license__ = "GPLv3+"
__date__ = "2014-03-15"
__version__ = "2.1.0"
__status__ = "Production"
__appname__ = "turbolift"
__description__ = 'OpenStack Swift -Cloud Files- Uploader'
__url__ = 'https://github.com/cloudnull/turbolift.git'

# Service Information
__rax_regions__ = ['dfw', 'ord', 'iad', 'lon', 'syd', 'hkg']
__hpc_regions__ = ['region-b.geo-1', 'region-a.geo-1']
__srv_types__ = ['cloudFiles', 'objectServer', 'Object Storage']
__cdn_types__ = ['cloudFilesCDN', 'CDN']

# The Version Of the Application
__VN__ = '%s' % __version__

# The Version and Information for the application
VINFO = ('Turbolift %(version)s, '
         'developed by %(author)s, '
         'Licenced Under %(license)s, '
         'FYI : %(copyright)s' % {'version': __version__,
                                  'author': __author__,
                                  'license': __license__,
                                  'copyright': __copyright__})

########NEW FILE########
__FILENAME__ = logger
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import logging
import logging.handlers as lhs
import os

import turbolift as tbl
from turbolift import info


class Logging(object):
    """Setup Application Logging."""

    def __init__(self, log_level, log_file=None):
        self.log_level = log_level
        self.log_file = log_file

    def logger_setup(self):
        """Setup logging for your application."""

        logger = logging.getLogger(str(info.__appname__.upper()))

        avail_level = {'DEBUG': logging.DEBUG,
                       'INFO': logging.INFO,
                       'CRITICAL': logging.CRITICAL,
                       'WARN': logging.WARN,
                       'ERROR': logging.ERROR}

        _log_level = self.log_level.upper()
        if _log_level in avail_level:
            lvl = avail_level[_log_level]
            logger.setLevel(lvl)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s:%(levelname)s ==> %(message)s"
            )
        else:
            raise tbl.NoLogLevelSet(
                'I died because you did not set a known log level'
            )

        if self.log_file:
            handler = lhs.RotatingFileHandler(self.log_file,
                                              maxBytes=150000000,
                                              backupCount=5)
        else:
            handler = logging.StreamHandler()

        handler.setLevel(lvl)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger


def return_logfile(filename, log_location):
    """Return a path for logging file.

    :param filename: name of the file for log storage.

    IF "/var/log/" does not exist, or you dont have write permissions to
    "/var/log/" the log file will be in your working directory
    Check for ROOT user if not log to working directory
    """

    if os.path.isfile(filename):
        return filename
    else:
        logname = str(filename)
        logfile = os.path.join(log_location, logname)
        return logfile


def load_in(log_location, log_file, log_level='info',):
    """Load in the log handler.

    If output is not None, systen will use the default
    Log facility.
    """

    _log_file = return_logfile(filename=log_file, log_location=log_location)
    log = Logging(log_level=log_level, log_file=_log_file)
    output = log.logger_setup()
    return output

########NEW FILE########
__FILENAME__ = archive
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import os

import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions
from turbolift import methods


class Archive(object):
    """Setup and run the archive Method."""

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    def start(self):
        """This is the archive method.

        Uses archive (TAR) feature to compress files and then upload the
        TAR Ball to a specified container.
        """

        # Index Local Files for Upload
        f_indexed = methods.get_local_files()

        if ARGS.get('pattern_match'):
            f_indexed = basic.match_filter(
                idx_list=f_indexed, pattern=ARGS['pattern_match']
            )

        num_files = len(f_indexed)
        report.reporter(msg='MESSAGE: "%s" Files have been found.' % num_files)

        # Package up the Payload
        payload = http.prep_payload(
            auth=self.auth,
            container=ARGS.get('container', basic.rand_string()),
            source=None,
            args=ARGS
        )

        report.reporter(
            msg='PAYLOAD\t: "%s"' % payload,
            log=True,
            lvl='debug',
            prt=False
        )

        # Set the actions class up
        self.go = actions.CloudActions(payload=payload)
        self.go.container_create(
            url=payload['url'], container=payload['c_name']
        )
        self.action = getattr(self.go, 'object_putter')

        with multi.spinner():
            # Compression Job
            wfile = methods.compress_files(file_list=f_indexed)
            source, name = os.path.split(wfile)
            report.reporter(msg='MESSAGE: "%s" is being uploaded.' % name)

            # Perform the upload
            self.action(url=payload['url'],
                        container=payload['c_name'],
                        source=source,
                        u_file=wfile)

            # Remove the archive unless instructed not too.
            if ARGS.get('no_cleanup') is None:
                basic.remove_file(wfile)

########NEW FILE########
__FILENAME__ = cdn_command
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions


class CdnCommand(object):
    """Setup and run the archive Method."""

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    def start(self):
        """This is the archive method.

        Uses archive (TAR) feature to compress files and then upload the
        TAR Ball to a specified container.
        """

        report.reporter(
            msg='Toggling CDN on Container %s.' % ARGS.get('container')
        )

        # Package up the Payload
        payload = http.prep_payload(
            auth=self.auth,
            container=ARGS.get('container', basic.rand_string()),
            source=None,
            args=ARGS
        )

        report.reporter(
            msg='PAYLOAD\t: "%s"' % payload,
            log=True,
            lvl='debug',
            prt=False
        )

        # Set the actions class up
        self.go = actions.CloudActions(payload=payload)

        with multi.spinner():
            if ARGS.get('purge'):
                for obj in ARGS.get('purge'):
                    # Perform the purge
                    self.go.container_cdn_command(url=payload['cnet'],
                                                  container=payload['c_name'],
                                                  sfile=obj)
            else:
                self.go.container_cdn_command(url=payload['cnet'],
                                              container=payload['c_name'])

########NEW FILE########
__FILENAME__ = clone
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift as turbo
import turbolift.utils.auth_utils as auth
import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions


class Clone(object):
    """Setup and run the stream Method.

    The method will create a list of objects in a "Source" container, then
    check to see if the object exists in the target container. If it exists
    a comparison will be made between the source and target MD5 and if a
    difference is found the source object will overwrite the target. If the
    target object simply does not exists, the object will be placed in the
    target container.
    """

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    def start(self):
        """Clone onjects from one container to another.

        NOTE: This method was intended for use with inter-datacenter cloning of
        objects.
        """

        # Package up the Payload
        payload = http.prep_payload(
            auth=self.auth,
            container=ARGS.get('source_container'),
            source=None,
            args=ARGS
        )

        # Prep action class
        self.go = actions.CloudActions(payload=payload)

        # Ensure we have a target region.
        target_region = ARGS.get('target_region')
        if target_region is None:
            raise turbo.NoSource('No target Region was specified.')
        else:
            target_region = target_region.upper()

        # check for a target type URL
        if ARGS.get('target_snet') is True:
            target_type = 'internalURL'
        else:
            target_type = 'publicURL'

        # Format the target URL
        target_url = auth.get_surl(
            region=target_region, cf_list=payload['acfep'], lookup=target_type
        )
        if target_url is None:
            raise turbo.NoSource('No url was found from the target region')
        else:
            payload['turl'] = target_url

        # Ensure we have a target Container.
        target_container = ARGS.get('target_container')
        if target_container is None:
            raise turbo.NoSource('No target Container was specified.')
        else:
            payload['tc_name'] = target_container

        # Check if the source and target containers exist. If not Create them.
        # Source Container.
        self.go.container_create(url=payload['url'],
                                 container=payload['c_name'])
        # Target Container.
        self.go.container_create(url=target_url,
                                 container=target_container)

        report.reporter(msg='Getting Object list from the Source.')
        with multi.spinner():
            # Get a list of Objects from the Source/Target container.
            objects, list_count, last_obj = self.go.object_lister(
                url=payload['url'],
                container=payload['c_name']
            )

            if ARGS.get('pattern_match'):
                objects = basic.match_filter(
                    idx_list=objects,
                    pattern=ARGS['pattern_match'],
                    dict_type=True
                )

        if objects is None:
            raise turbo.NoSource('The source container is empty.')

        # Get the number of objects and set Concurrency
        num_files = len(objects)
        concurrency = multi.set_concurrency(args=ARGS,
                                            file_count=num_files)

        report.reporter(msg='Beginning Sync Operation.')
        kwargs = {'surl': payload['url'],
                  'turl': payload['turl'],
                  'scontainer': payload['c_name'],
                  'tcontainer': payload['tc_name'],
                  'cf_job': getattr(self.go, 'object_syncer')}

        multi.job_processer(
            num_jobs=num_files,
            objects=objects,
            job_action=multi.doerator,
            concur=concurrency,
            kwargs=kwargs
        )

########NEW FILE########
__FILENAME__ = delete
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions


class Delete(object):
    """Setup and run the list Method."""

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    def start(self):
        """Retrieve a long list of all files in a container."""

        def _deleterator(payload):
            """Multipass Object Delete."""

            report.reporter(msg='Getting file list')
            with multi.spinner():
                # Get all objects in a Container
                objects, list_count, last_obj = self.action(
                    url=payload['url'],
                    container=payload['c_name']
                )

                if ARGS.get('pattern_match'):
                    objects = basic.match_filter(
                        idx_list=objects,
                        pattern=ARGS['pattern_match'],
                        dict_type=True
                    )

                # Count the number of objects returned.
                if objects is False:
                    report.reporter(msg='No Container found.')
                    return
                elif objects is not None:
                    # Load the queue
                    obj_list = [obj['name'] for obj in objects]
                    num_files = len(obj_list)
                    if num_files < 1:
                        report.reporter(msg='No Objects found.')
                        return
                else:
                    report.reporter(msg='Nothing found.')
                    return

                # Get The rate of concurrency
                concurrency = multi.set_concurrency(args=ARGS,
                                                    file_count=num_files)

                if ARGS.get('object'):
                    obj_names = ARGS.get('object')
                    obj_list = [obj for obj in obj_list if obj in obj_names]
                    if not obj_list:
                        return 'Nothing Found to Delete.'
                    num_files = len(obj_list)
                report.reporter(
                    msg=('Performing Object Delete for "%s" object(s)...'
                         % num_files)
                )
                kwargs = {'url': payload['url'],
                          'container': payload['c_name'],
                          'cf_job': getattr(self.go, 'object_deleter')}
            multi.job_processer(
                num_jobs=num_files,
                objects=obj_list,
                job_action=multi.doerator,
                concur=concurrency,
                kwargs=kwargs
            )
            _deleterator(payload=payload)

        # Package up the Payload
        payload = http.prep_payload(
            auth=self.auth,
            container=ARGS.get('container'),
            source=None,
            args=ARGS
        )
        report.reporter(
            msg='PAYLOAD\t: "%s"' % payload,
            log=True,
            lvl='debug',
            prt=False
        )

        self.go = actions.CloudActions(payload=payload)
        self.action = getattr(self.go, 'object_lister')

        report.reporter(
            msg='Accessing API for list of Objects in %s' % payload['c_name'],
            log=True,
            lvl='info',
            prt=True
        )

        # Delete the objects and report when done.
        _deleterator(payload=payload)

        sup_args = [ARGS.get('object'), ARGS.get('pattern_match')]
        if ARGS.get('save_container') is None and not any(sup_args):
            report.reporter(msg='Performing Container Delete.')
            with multi.spinner():
                self.go.container_deleter(url=payload['url'],
                                          container=payload['c_name'])

########NEW FILE########
__FILENAME__ = download
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions
from turbolift import LOG


class Download(object):
    """Setup and run the list Method."""

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    def start(self):
        """Retrieve a long list of all files in a container."""

        # Package up the Payload
        payload = http.prep_payload(
            auth=self.auth,
            container=ARGS.get('container'),
            source=ARGS.get('source'),
            args=ARGS
        )
        self.go = actions.CloudActions(payload=payload)
        self.action = getattr(self.go, 'object_lister')

        LOG.info('Attempting Download of Remote path %s', payload['c_name'])

        if ARGS.get('verbose'):
            LOG.info(
                'Accessing API for a list of Objects in %s', payload['c_name']
            )

        report.reporter(
            msg='PAYLOAD\t: "%s"' % payload,
            log=True,
            lvl='debug',
            prt=False
        )

        report.reporter(msg='getting file list')
        with multi.spinner():
            # Get all objects in a Container
            objects, list_count, last_obj = self.action(
                url=payload['url'],
                container=payload['c_name'],
                last_obj=ARGS.get('index_from')
            )

            if ARGS.get('pattern_match'):
                objects = basic.match_filter(
                    idx_list=objects,
                    pattern=ARGS['pattern_match'],
                    dict_type=True
                )

            # Count the number of objects returned.
            if objects is False:
                report.reporter(msg='No Container found.')
                return
            elif objects is not None:
                num_files = len(objects)
                if num_files < 1:
                    report.reporter(msg='No Objects found.')
                    return
            else:
                report.reporter(msg='No Objects found.')
                return

            # Get The rate of concurrency
            concurrency = multi.set_concurrency(args=ARGS,
                                                file_count=num_files)
            # Load the queue
            obj_list = [obj['name'] for obj in objects if obj.get('name')]

        report.reporter(msg='Building Directory Structure.')
        with multi.spinner():
            if ARGS.get('object'):
                obj_names = ARGS.get('object')
                obj_list = [obj for obj in obj_list if obj in obj_names]
                num_files = len(obj_list)
            elif ARGS.get('dir'):
                objpath = ARGS.get('dir')
                obj_list = [obj for obj in obj_list if obj.startswith(objpath)]
                num_files = len(obj_list)

            # from objects found set a unique list of directories
            unique_dirs = basic.set_unique_dirs(object_list=obj_list,
                                                root_dir=payload['source'])
            for udir in unique_dirs:
                basic.mkdir_p(path=udir)

        kwargs = {'url': payload['url'],
                  'container': payload['c_name'],
                  'source': payload['source'],
                  'cf_job': getattr(self.go, 'object_downloader')}

        report.reporter(msg='Performing Object Download.')
        multi.job_processer(
            num_jobs=num_files,
            objects=obj_list,
            job_action=multi.doerator,
            concur=concurrency,
            kwargs=kwargs
        )
        if ARGS.get('max_jobs') is not None:
            report.reporter(
                msg=('This is the last object downloaded. [ %s ]'
                     % last_obj),
                log=True
            )

########NEW FILE########
__FILENAME__ = list
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions


class List(object):
    """Setup and run the list Method."""

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    def start(self):
        """Return a list of objects from the API for a container."""

        def _check_list(list_object):
            if list_object:
                return list_object
            else:
                return None, None, None

        def _list(payload, go, last_obj):
            """Retrieve a long list of all files in a container.

            :return final_list, list_count, last_obj:
            """

            if ARGS.get('all_containers') is None:
                return _check_list(
                    list_object=go.object_lister(
                        url=payload['url'],
                        container=payload['c_name'],
                        last_obj=last_obj
                    )
                )
            else:
                return _check_list(
                    list_object=go.container_lister(
                        url=payload['url'],
                        last_obj=last_obj
                    )
                )

        # Package up the Payload
        payload = http.prep_payload(
            auth=self.auth,
            container=ARGS.get('container'),
            source=None,
            args=ARGS
        )

        # Prep Actions.
        self.go = actions.CloudActions(payload=payload)

        report.reporter(
            msg='API Access for a list of Objects in %s' % payload['c_name'],
            log=True
        )
        report.reporter(
            msg='PAYLOAD\t: "%s"' % payload,
            log=True,
            lvl='debug',
            prt=False
        )

        last_obj = None
        with multi.spinner():
            objects, list_count, last_obj = _list(payload=payload,
                                                  go=self.go,
                                                  last_obj=last_obj)
            if 'pattern_match' in ARGS:
                objects = basic.match_filter(
                    idx_list=objects,
                    pattern=ARGS['pattern_match'],
                    dict_type=True
                )

            if ARGS.get('filter') is not None:
                objects = [obj for obj in objects
                           if ARGS.get('filter') in obj.get('name')]

        # Count the number of objects returned.
        if objects is False:
            report.reporter(msg='Nothing found.')
        elif ARGS.get('object_index'):
            report.reporter(msg=report.print_horiz_table([{'name': last_obj}]))
        elif objects is not None:
            num_files = len(objects)
            if num_files < 1:
                report.reporter(msg='Nothing found.')
            else:
                return_objects = []
                for obj in objects:
                    for item in ['hash', 'last_modified', 'content_type']:
                        if item in obj:
                            obj.pop(item)
                    return_objects.append(obj)
                report.reporter(msg=report.print_horiz_table(return_objects))
                report.reporter(msg='I found "%d" Item(s).' % num_files)
        else:
            report.reporter(msg='Nothing found.')

########NEW FILE########
__FILENAME__ = show
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions


class Show(object):
    """Setup and run the list Method."""

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    def start(self):
        """Retrieve a long list of all files in a container."""

        # Package up the Payload
        payload = http.prep_payload(
            auth=self.auth,
            container=None,
            source=None,
            args=ARGS
        )

        # Prep Actions.
        self.go = actions.CloudActions(payload=payload)

        report.reporter(
            msg='PAYLOAD\t: "%s"' % payload,
            log=True,
            lvl='debug',
            prt=False
        )

        with multi.spinner():
            if ARGS.get('cdn_info'):
                url = payload['cnet']
            else:
                url = payload['url']
            message = self.go.detail_show(url=url)

        try:
            if message.status_code != 404:
                report.reporter(msg='Object Found...')
                report.reporter(
                    msg=report.print_virt_table(dict(message.headers))
                )
            else:
                report.reporter(msg='Nothing Found...')
        except ValueError as exp:
            report.reporter(
                msg=('Non-hashable Type, Likley Item is not found.'
                     ' Additional Data: %s' % exp)
            )

########NEW FILE########
__FILENAME__ = update
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions


class Update(object):
    """Setup and run the list Method."""

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    def start(self):
        """Return a list of objects from the API for a container."""

        def _check_list(list_object):
            if list_object:
                return list_object
            else:
                return None, None, None

        def _list(l_payload, go, l_last_obj):
            """Retrieve a long list of all files in a container.

            :return final_list, list_count, last_obj:
            """
            # object_lister(url, container, object_count=None, last_obj=None)
            return _check_list(
                list_object=go.object_lister(
                    url=l_payload['url'],
                    container=l_payload['c_name'],
                    last_obj=l_last_obj
                )
            )

        # Package up the Payload
        payload = http.prep_payload(
            auth=self.auth,
            container=ARGS.get('container'),
            source=None,
            args=ARGS
        )

        # Prep Actions.
        self.go = actions.CloudActions(payload=payload)

        report.reporter(
            msg='API Access for a list of Objects in %s' % payload['c_name'],
            log=True
        )
        report.reporter(
            msg='PAYLOAD\t: "%s"' % payload,
            log=True,
            lvl='debug',
            prt=False
        )

        last_obj = None
        with multi.spinner():
            objects, list_count, last_obj = _list(
                l_payload=payload, go=self.go, l_last_obj=last_obj
            )
            if 'pattern_match' in ARGS:
                objects = basic.match_filter(
                    idx_list=objects,
                    pattern=ARGS['pattern_match'],
                    dict_type=True
                )

            if ARGS.get('filter') is not None:
                objects = [obj for obj in objects
                           if ARGS.get('filter') in obj.get('name')]

        # Count the number of objects returned.
        if objects is False:
            report.reporter(msg='Nothing found.')
        elif len(objects) < 1:
            report.reporter(msg='Nothing found.')
        elif ARGS.get('object'):
            self.go.object_updater(
                url=payload['url'],
                container=payload['c_name'],
                u_file=last_obj
            )
        elif objects is not None:
            kwargs = {
                'url': payload['url'],
                'container': payload['c_name'],
                'cf_job': getattr(self.go, 'object_updater'),
            }

            object_names = [i['name'] for i in objects]
            num_files = len(object_names)
            concurrency = multi.set_concurrency(
                args=ARGS, file_count=num_files
            )
            multi.job_processer(
                num_jobs=num_files,
                objects=object_names,
                job_action=multi.doerator,
                concur=concurrency,
                kwargs=kwargs
            )
        else:
            report.reporter(msg='Nothing found.')

########NEW FILE########
__FILENAME__ = upload
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import turbolift.utils.basic_utils as basic
import turbolift.utils.http_utils as http
import turbolift.utils.multi_utils as multi
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift.clouderator import actions
from turbolift import methods


class Upload(object):
    """Setup and run the upload Method."""

    def __init__(self, auth):
        self.auth = auth
        self.go = None
        self.action = None

    @staticmethod
    def _index_local_files():
        """Index Local Files for Upload."""
        with multi.spinner():
            file_index = methods.get_local_files()

        if ARGS.get('pattern_match'):
            return basic.match_filter(
                idx_list=file_index,
                pattern=ARGS['pattern_match']
            )
        else:
            return file_index

    def start(self):
        """This is the upload method.

        Uses file_upload is to simply upload all files and folders to a
        specified container.
        """

        f_indexed = self._index_local_files()
        num_files = len(f_indexed)

        # Get The rate of concurrency
        concurrency = multi.set_concurrency(args=ARGS, file_count=num_files)

        # Package up the Payload
        payload = multi.manager_dict(
            http.prep_payload(
                auth=self.auth,
                container=ARGS.get('container', basic.rand_string()),
                source=basic.get_local_source(),
                args=ARGS
            )
        )
        report.reporter(msg='MESSAGE : "%s" Files found.' % num_files)
        report.reporter(msg='PAYLOAD : "%s"' % payload, prt=False, lvl='debug')

        # Set the actions class up
        self.go = actions.CloudActions(payload=payload)

        kwargs = {'url': payload['url'], 'container': payload['c_name']}
        # get that the container exists if not create it.
        self.go.container_create(**kwargs)
        kwargs['source'] = payload['source']
        kwargs['cf_job'] = getattr(self.go, 'object_putter')

        multi.job_processer(
            num_jobs=num_files,
            objects=f_indexed,
            job_action=multi.doerator,
            concur=concurrency,
            kwargs=kwargs
        )

        if ARGS.get('delete_remote') is True:
            self.remote_delete(payload=payload)

    def remote_delete(self, payload):
        """If Remote Delete was True run.

        NOTE: Remote delete will delete ALL Objects in a remote container
        which differ from the objects in the SOURCED LOCAL FILESYSTEM.

        IE: If this option is used, on one directory and then another directory
        and the files were different any difference would be deleted and based
        on the index information found in LOCAL FILE SYSTEM on the LAST
        command run.

        :param payload: ``dict``
        """

        report.reporter(msg='Getting file list for REMOTE DELETE')
        objects = self.go.object_lister(
            url=payload['url'], container=payload['c_name']
        )

        source = payload['source']
        obj_names = [
            basic.jpath(root=source, inode=obj.get('name'))
            for obj in objects[0]
        ]

        # From the remote system see if we have differences in the local system
        f_indexed = self._index_local_files()
        diff_check = multi.ReturnDiff()
        objects = diff_check.difference(target=f_indexed, source=obj_names)

        if objects:
            # Set Basic Data for file delete.
            num_files = len(objects)
            report.reporter(
                msg=('MESSAGE: "%d" Files have been found to be removed'
                     ' from the REMOTE CONTAINER.' % num_files)
            )
            concurrency = multi.set_concurrency(
                args=ARGS, file_count=num_files
            )
            # Delete the difference in Files.
            report.reporter(msg='Performing REMOTE DELETE')

            del_objects = [
                basic.get_sfile(ufile=obj, source=payload['source'])
                for obj in objects if obj is not None
            ]

            kwargs = {
                'url': payload['url'],
                'container': payload['c_name'],
                'cf_job': getattr(self.go, 'object_deleter')
            }

            multi.job_processer(
                num_jobs=num_files,
                objects=del_objects,
                job_action=multi.doerator,
                concur=concurrency,
                kwargs=kwargs
            )
        else:
            report.reporter(
                msg='No Difference between REMOTE and LOCAL Directories.'
            )

########NEW FILE########
__FILENAME__ = test_argument
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================

import inspect
import sys
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import mock

from turbolift import arguments


class ArguementsTests(unittest.TestCase):
    """Test all of the arguments."""

    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, obj, cls, msg=None):
            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (obj, cls)
                self.fail(self._formatMessage(msg, standardMsg))

    def setUp(self):
        self.args = arguments.args_setup()
        self.command = sys.argv[0]
        self.arg_dict = {'os_user': 'TEST-USER',
                         'container': 'TEST-CONTAINER'}

    def auth_rax_args(self):
        auth_dict = {
            'os_password': 'TEST-PASSWORD',
            'os_rax_auth': 'TEST-REGION'
        }
        auth_dict.update(self.arg_dict)
        return auth_dict

    def auth_hp_args(self):
        auth_dict = {
            'os_apikey': 'TEST-KEY',
            'os_hp_auth': 'TEST-REGION'
        }
        auth_dict.update(self.arg_dict)
        return auth_dict

    def auth_basic_args(self):
        auth_dict = {
            'os_password': 'TEST-KEY',
            'os_region': 'TEST-REGION',
            'os_auth_url': 'https://test.url'
        }
        auth_dict.update(self.arg_dict)
        return auth_dict

    def check_auth_types(self):
        methods = inspect.getmembers(
            object=self,
            predicate=inspect.ismethod
        )
        for name, method in methods:
            if name.startswith('auth'):
                args = method()
                self.assertIsInstance(args, dict)

                parsed_args = arguments.understand_args(set_args=args)
                self.args.set_defaults(**parsed_args)

    def test_understanding_failure_no_apikey_or_password(self):
        base_dict = {
            'os_user': 'TEST-USER',
            'os_auth_url': 'https://test.url',
            'os_region': 'TEST-REGION',
        }
        self.assertRaises(
            SystemExit,
            arguments.understand_args,
            base_dict
        )

    def test_understanding_failure_no_user(self):
        base_dict = {
            'os_password': 'TEST-KEY',
            'os_auth_url': 'https://test.url',
            'os_region': 'TEST-REGION'
        }
        self.assertRaises(
            SystemExit,
            arguments.understand_args,
            base_dict
        )

    def test_understanding_region_upper(self):
        base_dict = {
            'os_user': 'TEST-USER',
            'os_password': 'TEST-KEY',
            'os_auth_url': 'https://test.url',
            'os_region': 'lower-region'
        }
        understood = arguments.understand_args(set_args=base_dict)
        self.assertEqual(
            first=understood['os_region'],
            second=base_dict['os_region'].upper()
        )

    def test_understanding_rax_auth_upper(self):
        base_dict = {
            'os_user': 'TEST-USER',
            'os_password': 'TEST-KEY',
            'os_auth_url': 'https://test.url',
            'os_rax_auth': 'lower-region'
        }
        understood = arguments.understand_args(set_args=base_dict)
        self.assertEqual(
            first=understood['os_rax_auth'],
            second=base_dict['os_rax_auth'].upper()
        )

    def test_method_archive(self):
        base = [self.command,
                'archive',
                '--source',
                'TEST-SOURCE',
                '--container',
                'TEST-CONTAINER']

        with mock.patch('sys.argv', base):
            self.check_auth_types()

    def test_method_delete(self):
        base = [self.command,
                'delete',
                '--container',
                'TEST-CONTAINER']

        with mock.patch('sys.argv', base):
            self.check_auth_types()

    def test_method_download(self):
        base = [self.command,
                'download',
                '--source',
                'TEST-SOURCE',
                '--container',
                'TEST-CONTAINER']

        with mock.patch('sys.argv', base):
            self.check_auth_types()

    def test_method_upload(self):
        base = [self.command,
                'upload',
                '--source',
                'TEST-SOURCE',
                '--container',
                'TEST-CONTAINER']

        with mock.patch('sys.argv', base):
            self.check_auth_types()

    def test_method_show(self):
        base = [self.command,
                'show',
                '--container',
                'TEST-CONTAINER']

        with mock.patch('sys.argv', base):
            self.check_auth_types()

    def test_method_list(self):
        base = [self.command,
                'list',
                '--container',
                'TEST-CONTAINER']

        with mock.patch('sys.argv', base):
            self.check_auth_types()

    def test_method_cdn_command(self):
        base = [self.command,
                'cdn-command',
                '--container',
                'TEST-CONTAINER',
                '--enabled']

        with mock.patch('sys.argv', base):
            self.check_auth_types()

    def test_method_clone(self):
        base = [self.command,
                'clone',
                '--source-container',
                'TEST-SOURCE',
                '--target-container',
                'TEST-CONTAINER',
                '--target-region',
                'TEST-TARGET-REGION']

        with mock.patch('sys.argv', base):
            self.check_auth_types()

########NEW FILE########
__FILENAME__ = test_auth_utils
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import json
import httplib
import unittest

import mock

import turbolift

from turbolift.authentication import authentication
from turbolift import tests
from turbolift.utils import auth_utils


FAKE_200_OK = tests.FakeHttpResponse(
    status=200,
    reason='OK',
    headers=[('Foo', 'Bar')],
    body=json.dumps({'message': 'connection response'})
)

FAKE_300_FAILURE = tests.FakeHttpResponse(
    status=300,
    reason='UNAUTHORIZED',
    headers=[('Foo', 'Bar')],
    body=json.dumps({'message': 'connection response'})
)


class TestAuthenticate(unittest.TestCase):
    """Test Auth Utils Methods."""

    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, obj, cls, msg=None):
            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (obj, cls)
                self.fail(self._formatMessage(msg, standardMsg))

    def setUp(self):
        self.srv_cat_json = {
            u"access": {
                u"token": {
                    u"id": u"TEST-ID",
                },
                u"serviceCatalog": [
                    {
                        u"endpoints": [
                            {
                                u"region": u"TEST-REGION",
                                u"tenantId": u"TEST-TENANT-ID",
                                u"publicURL": u"https://TEST.url"
                            }
                        ],
                        u"name": u"cloudFiles"
                    },
                    {
                        u"endpoints": [
                            {
                                u"region": u"TEST-REGION",
                                u"tenantId": u"TEST-TENANT-ID",
                                u"publicURL": u"https://TEST-CDN.url"
                            }
                        ],
                        u"name": u"cloudFilesCDN"
                    }
                ],
                u"user": {
                    u"name": u"TEST-USER"
                }
            }
        }

    def endpoints(self, name):
        access = self.srv_cat_json.get('access')
        scat = access.get('serviceCatalog')

        for srv in scat:
            if srv.get('name') == name:
                return srv.get('endpoints')
        else:
            self.fail()

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_reqtype_token(self, mock_log):
        args = {
            'os_user': 'TEST-USER',
            'os_token': 'TEST-TOKEN'
        }
        expected_return = {
            'auth': {
                'token': {
                    'id': 'TEST-TOKEN'
                }
            }
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            ab = auth_utils.parse_reqtype()
            self.assertEqual(ab, expected_return)
            self.assertTrue(mock_log.debug.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_reqtype_password(self, mock_log):
        args = {
            'os_user': 'TEST-USER',
            'os_password': 'TEST-PASSWORD'
        }
        expected_return = {
            'auth': {
                'passwordCredentials': {
                    'username': 'TEST-USER',
                    'password': 'TEST-PASSWORD'
                }
            }
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            ab = auth_utils.parse_reqtype()
            self.assertEqual(ab, expected_return)
            self.assertTrue(mock_log.debug.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_reqtype_apikey(self, mock_log):
        args = {
            'os_user': 'TEST-USER',
            'os_apikey': 'TEST-APIKEY'
        }
        expected_return = {
            'auth': {
                'RAX-KSKEY:apiKeyCredentials': {
                    'username': 'TEST-USER',
                    'apiKey': 'TEST-APIKEY'
                }
            }
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            ab = auth_utils.parse_reqtype()
            self.assertEqual(ab, expected_return)
            self.assertTrue(mock_log.debug.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_reqtype_failure(self, mock_log):
        args = {
            'os_user': 'TEST-USER'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            self.assertRaises(AttributeError, auth_utils.parse_reqtype)
            self.assertTrue(mock_log.error.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_reqtype_token_with_tenant(self, mock_log):
        args = {
            'os_user': 'TEST-USER',
            'os_token': 'TEST-TOKEN',
            'os_tenant': 'TEST-TENANT'
        }
        expected_return = {
            'auth': {
                'token': {
                    'id': 'TEST-TOKEN'
                },
                'tenantName': 'TEST-TENANT'
            }
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            ab = auth_utils.parse_reqtype()
            self.assertEqual(ab, expected_return)
            self.assertTrue(mock_log.debug.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_reqtype_password_with_tenant(self, mock_log):
        args = {
            'os_user': 'TEST-USER',
            'os_password': 'TEST-PASSWORD',
            'os_tenant': 'TEST-TENANT'
        }
        expected_return = {
            'auth': {
                'passwordCredentials': {
                    'username': 'TEST-USER',
                    'password': 'TEST-PASSWORD'
                },
                'tenantName': 'TEST-TENANT'
            }
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            ab = auth_utils.parse_reqtype()
            self.assertEqual(ab, expected_return)
            self.assertTrue(mock_log.debug.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_reqtype_apikey_with_tenant(self, mock_log):
        args = {
            'os_user': 'TEST-USER',
            'os_apikey': 'TEST-APIKEY',
            'os_tenant': 'TEST-TENANT'
        }
        expected_return = {
            'auth': {
                'RAX-KSKEY:apiKeyCredentials': {
                    'username': 'TEST-USER',
                    'apiKey': 'TEST-APIKEY'
                },
                'tenantName': 'TEST-TENANT'
            }
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            ab = auth_utils.parse_reqtype()
            self.assertEqual(ab, expected_return)
            self.assertTrue(mock_log.debug.called)

    def test_get_surl(self):
        cf_return = self.endpoints(name='cloudFiles')
        parsed_url = auth_utils.get_surl(
            region='TEST-REGION', cf_list=cf_return, lookup='publicURL'
        )
        self.assertEqual(parsed_url.scheme, 'https')
        self.assertEqual(parsed_url.netloc, 'TEST.url')

    def test_get_surl_cdn(self):
        cf_return = self.endpoints(name='cloudFilesCDN')
        parsed_url = auth_utils.get_surl(
            region='TEST-REGION', cf_list=cf_return, lookup='publicURL'
        )
        self.assertEqual(parsed_url.scheme, 'https')
        self.assertEqual(parsed_url.netloc, 'TEST-CDN.url')

    def test_get_surl_bad_lookup(self):
        cf_return = self.endpoints(name='cloudFiles')
        parsed_url = auth_utils.get_surl(
            region='TEST-REGION', cf_list=cf_return, lookup='NotThisURL'
        )
        self.assertEqual(parsed_url, None)

    def test_get_surl_not_region_found(self):
        cf_return = self.endpoints(name='cloudFiles')
        kwargs = {
            'region': 'NotThisRegion',
            'cf_list': cf_return,
            'lookup': 'publicURL'
        }
        self.assertRaises(
            turbolift.SystemProblem, auth_utils.get_surl, **kwargs
        )

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_auth_response_tenant_with_rax_auth(self, mock_log):
        args = {
            'os_rax_auth': 'TEST-REGION'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            srv_cat = self.srv_cat_json.copy()
            srv_cat['access']['token']['tenant'] = {u'name': u'TEST-TENANT'}
            par = auth_utils.parse_auth_response(auth_response=srv_cat)
            self.assertIsInstance(par, tuple)
            self.assertEqual(par[0], 'TEST-ID')
            self.assertEqual(par[1], 'TEST-TENANT')
            self.assertEqual(par[2], 'TEST-USER')
            self.assertEqual(par[3], None)
            self.assertEqual(par[4].scheme, 'https')
            self.assertEqual(par[4].netloc, 'TEST.url')
            self.assertEqual(par[5].scheme, 'https')
            self.assertEqual(par[5].netloc, 'TEST-CDN.url')
            self.assertIsInstance(par[6], list)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_auth_response_with_rax_auth(self, mock_log):
        args = {
            'os_rax_auth': 'TEST-REGION'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            srv_cat = self.srv_cat_json.copy()
            par = auth_utils.parse_auth_response(auth_response=srv_cat)
            self.assertIsInstance(par, tuple)
            self.assertEqual(par[0], 'TEST-ID')
            self.assertEqual(par[1], None)
            self.assertEqual(par[2], 'TEST-USER')
            self.assertEqual(par[3], None)
            self.assertEqual(par[4].scheme, 'https')
            self.assertEqual(par[4].netloc, 'TEST.url')
            self.assertEqual(par[5].scheme, 'https')
            self.assertEqual(par[5].netloc, 'TEST-CDN.url')
            self.assertIsInstance(par[6], list)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_auth_response_with_hp_auth(self, mock_log):
        args = {
            'os_hp_auth': 'TEST-REGION',
            'os_tenant': 'TEST-TENANT'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            srv_cat = self.srv_cat_json.copy()
            par = auth_utils.parse_auth_response(auth_response=srv_cat)
            self.assertIsInstance(par, tuple)
            self.assertEqual(par[0], 'TEST-ID')
            self.assertEqual(par[1], None)
            self.assertEqual(par[2], 'TEST-USER')
            self.assertEqual(par[3], None)
            self.assertEqual(par[4].scheme, 'https')
            self.assertEqual(par[4].netloc, 'TEST.url')
            self.assertEqual(par[5].scheme, 'https')
            self.assertEqual(par[5].netloc, 'TEST-CDN.url')
            self.assertIsInstance(par[6], list)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_auth_response_with_region_auth(self, mock_log):
        args = {
            'os_region': 'TEST-REGION',
            'os_tenant': 'TEST-TENANT'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            srv_cat = self.srv_cat_json.copy()
            par = auth_utils.parse_auth_response(auth_response=srv_cat)
            self.assertIsInstance(par, tuple)
            self.assertEqual(par[0], 'TEST-ID')
            self.assertEqual(par[1], None)
            self.assertEqual(par[2], 'TEST-USER')
            self.assertEqual(par[3], None)
            self.assertEqual(par[4].scheme, 'https')
            self.assertEqual(par[4].netloc, 'TEST.url')
            self.assertEqual(par[5].scheme, 'https')
            self.assertEqual(par[5].netloc, 'TEST-CDN.url')
            self.assertIsInstance(par[6], list)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_auth_response_with_hp_auth_failure(self, mock_log):
        args = {
            'os_hp_auth': 'TEST-REGION',
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            srv_cat = self.srv_cat_json.copy()
            self.assertRaises(
                turbolift.NoTenantIdFound,
                auth_utils.parse_auth_response,
                srv_cat
            )

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_auth_response_failure(self, mock_log):
        srv_cat = self.srv_cat_json.copy()
        srv_cat['access'].pop('user')

        self.assertRaises(
            turbolift.NoTenantIdFound,
            auth_utils.parse_auth_response,
            srv_cat
        )
        self.assertTrue(mock_log.error.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    def test_parse_auth_response_no_region_failure(self, mock_log):
        args = {
            'os_tenant': 'TEST-TENANT'
        }
        srv_cat = self.srv_cat_json.copy()
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            self.assertRaises(
                turbolift.SystemProblem,
                auth_utils.parse_auth_response,
                srv_cat
            )

    @mock.patch('turbolift.utils.auth_utils.LOG')
    @mock.patch('turbolift.utils.auth_utils.info.__srv_types__', ['NotFound'])
    @mock.patch('turbolift.utils.auth_utils.info.__cdn_types__', ['NotFound'])
    def test_parse_auth_response_no_cloudfiles_endpoints(self, mock_log):
        args = {
            'os_region': 'TEST-REGION',
            'os_tenant': 'TEST-TENANT'
        }
        srv_cat = self.srv_cat_json.copy()
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            self.assertRaises(
                turbolift.SystemProblem,
                auth_utils.parse_auth_response,
                srv_cat
            )

    def test_parse_region_rax_auth_us(self):
        args = {
            'os_rax_auth': 'ORD'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            url = auth_utils.parse_region()
            self.assertEqual(
                url, 'https://identity.api.rackspacecloud.com/v2.0/tokens'
            )

    def test_parse_region_rax_auth_lon_with_auth_url(self):
        args = {
            'os_rax_auth': 'ORD',
            'os_auth_url': 'https://TEST.url'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            url = auth_utils.parse_region()
            self.assertEqual(
                url, 'https://TEST.url'
            )

    def test_parse_region_rax_auth_lon(self):
        args = {
            'os_rax_auth': 'LON'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            url = auth_utils.parse_region()
            self.assertEqual(
                url, 'https://lon.identity.api.rackspacecloud.com/v2.0/tokens'
            )

    def test_parse_region_rax_auth_us_with_auth_url(self):
        args = {
            'os_rax_auth': 'ORD',
            'os_auth_url': 'https://TEST.url'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            url = auth_utils.parse_region()
            self.assertEqual(
                url, 'https://TEST.url'
            )

    def test_parse_region_rax_auth_failure(self):
        args = {
            'os_rax_auth': 'TEST-REGION'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            self.assertRaises(
                turbolift.SystemProblem, auth_utils.parse_region
            )

    def test_parse_region_hp_auth(self):
        args = {
            'os_hp_auth': 'region-b.geo-1'
        }
        au = 'https://region-b.geo-1.identity.hpcloudsvc.com:35357/v2.0/tokens'
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            url = auth_utils.parse_region()
            self.assertEqual(
                url, au
            )

    def test_parse_region_hp_auth_with_auth_url(self):
        args = {
            'os_hp_auth': 'region-b.geo-1',
            'os_auth_url': 'https://TEST.url'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            url = auth_utils.parse_region()
            self.assertEqual(
                url, 'https://TEST.url'
            )

    def test_parse_region_hp_auth_failure(self):
        args = {
            'os_hp_auth': 'TEST-REGION'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            self.assertRaises(
                turbolift.SystemProblem, auth_utils.parse_region
            )

    def test_parse_region_with_auth_url(self):
        args = {
            'os_auth_url': 'https://TEST.url'
        }
        with mock.patch('turbolift.utils.auth_utils.ARGS', args):
            url = auth_utils.parse_region()
            self.assertEqual(
                url, 'https://TEST.url'
            )

    def test_parse_region_auth_failure(self):
        with mock.patch('turbolift.utils.auth_utils.ARGS', {}):
            self.assertRaises(
                    turbolift.SystemProblem, auth_utils.parse_region
            )

    @mock.patch('turbolift.utils.auth_utils.LOG')
    @mock.patch('turbolift.utils.auth_utils.http.open_connection')
    def test_request_process(self, mock_conn, mock_log):

        _mock = mock.Mock()
        _mock.getresponse.side_effect = [FAKE_200_OK]
        mock_conn.return_value = _mock

        parsed_url = tests.ParseResult
        post = {
            "auth": {
                'passwordCredentials': {
                    "username": "TEST-USER",
                    "password": "TEST-ID"
                }
            }
        }

        post_request = (
            'POST',
            '/v2.0/tokens',
            str(post),
            {'Content-Type': 'application/json'}
        )

        resp = auth_utils.request_process(
            aurl=parsed_url, req=post_request
        )
        self.assertEqual(resp, '{"message": "connection response"}')
        self.assertTrue(mock_log.debug.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    @mock.patch('turbolift.utils.auth_utils.http.open_connection')
    def test_request_process_bad_status(self, mock_conn, mock_log):

        _mock = mock.Mock()
        _mock.getresponse.side_effect = [FAKE_300_FAILURE]
        mock_conn.return_value = _mock

        parsed_url = tests.ParseResult
        post = {
            "auth": {
                'passwordCredentials': {
                    "username": "TEST-USER",
                    "password": "TEST-ID"
                }
            }
        }

        post_request = (
            'POST',
            '/v2.0/tokens',
            str(post),
            {'Content-Type': 'application/json'}
        )

        kwargs = {
            'aurl': parsed_url,
            'req': post_request
        }

        self.assertRaises(
            httplib.HTTPException,
            auth_utils.request_process,
            **kwargs
        )
        self.assertTrue(mock_log.error.called)

    @mock.patch('turbolift.utils.auth_utils.LOG')
    @mock.patch('turbolift.utils.auth_utils.http.open_connection')
    def test_request_process_exception(self, mock_conn, mock_log):

        _mock = mock.Mock()
        _mock.getresponse.side_effect = Exception('Died')
        mock_conn.return_value = _mock

        parsed_url = tests.ParseResult
        post = {
            "auth": {
                'passwordCredentials': {
                    "username": "TEST-USER",
                    "password": "TEST-ID"
                }
            }
        }

        post_request = (
            'POST',
            '/v2.0/tokens',
            str(post),
            {'Content-Type': 'application/json'}
        )

        kwargs = {
            'aurl': parsed_url,
            'req': post_request
        }

        self.assertRaises(
            AttributeError,
            auth_utils.request_process,
            **kwargs
        )
        self.assertTrue(mock_log.error.called)

########NEW FILE########
__FILENAME__ = test_basic_utils
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import datetime
import os
import tempfile
import unittest

import mock

import turbolift
from turbolift.utils import basic_utils


class TestAuthenticate(unittest.TestCase):
    """Test Basic Utils Methods."""

    def setUp(self):
        pass

    if not hasattr(unittest.TestCase, 'assertIsInstance'):
        def assertIsInstance(self, obj, cls, msg=None):
            if not isinstance(obj, cls):
                standardMsg = '%s is not an instance of %r' % (obj, cls)
                self.fail(self._formatMessage(msg, standardMsg))

    def test_time_stamp(self):
        fmt, date, date_delta, now = basic_utils.time_stamp()
        self.assertEqual('%Y-%m-%dT%H:%M:%S.%f', fmt)
        self.assertIsInstance(date, type)
        self.assertIsInstance(date_delta, type)
        self.assertIsInstance(now, datetime.datetime)

    def test_json_encode(self):
        json_dict = '{"key": "value"}'
        self.assertIsInstance(basic_utils.json_encode(read=json_dict), dict)

    def test_unique_list_dicts(self):
        dict_list = [
            {'key': 'value'},
            {'key': 'value'}
        ]
        return_list = basic_utils.unique_list_dicts(dlist=dict_list, key='key')
        self.assertEqual(len(return_list), 1)

    def test_dict_pop_none(self):
        dict_with_none = {
            'key': 'value',
            'test': None
        }
        return_dict = basic_utils.dict_pop_none(dictionary=dict_with_none)
        if 'test' in return_dict:
            self.fail(
                'None Value not removed from dictionary'
            )

    def test_keys2dict(self):
        list_of_strings = ['test=value']
        return_dict = basic_utils.keys2dict(chl=list_of_strings)
        self.assertIsInstance(return_dict, dict)

    def test_keys2dict_with_none_value(self):
        list_of_strings = None
        return_dict = basic_utils.keys2dict(chl=list_of_strings)
        self.assertEqual(return_dict, None)

    def test_jpath(self):
        return_path = basic_utils.jpath(root='/test', inode='path/of/test')
        self.assertEqual(return_path, '/test/path/of/test')

    def test_rand_string(self):
        return_str1 = basic_utils.rand_string()
        return_str2 = basic_utils.rand_string()
        self.assertIsInstance(return_str1, str)
        self.assertIsInstance(return_str2, str)
        self.assertNotEqual(return_str1, return_str2)

    def test_create_tmp(self):
        return_file = basic_utils.create_tmp()
        if not os.path.exists(return_file):
            self.fail('No File was found when creating a temp file')
        else:
            try:
                os.remove(return_file)
            except OSError:
                pass

    def test_remove_file(self):
        return_file = tempfile.mkstemp()[1]
        basic_utils.remove_file(filename=return_file)
        if os.path.exists(return_file):
            self.fail('Failed to remove File')

    def test_file_exists(self):
        return_file = tempfile.mkstemp()[1]
        self.assertEqual(
            basic_utils.file_exists(filename=return_file), True
        )
        try:
            os.remove(return_file)
        except OSError:
            pass
        else:
            self.assertEqual(
                basic_utils.file_exists(filename=return_file), False
            )

    @mock.patch('turbolift.utils.basic_utils.turbo.ARGS', {'batch_size': 1})
    @mock.patch('turbolift.utils.basic_utils.report.reporter')
    def test_batcher(self, mock_reporter):
        return_batch_size = basic_utils.batcher(1)
        self.assertEqual(return_batch_size, 1)
        self.assertTrue(mock_reporter.called)

    @mock.patch('turbolift.utils.basic_utils.turbo.ARGS', {'batch_size': 1})
    @mock.patch('turbolift.utils.basic_utils.report.reporter')
    def test_batcher_with_more_files(self, mock_reporter):
        return_batch_size = basic_utils.batcher(2)
        self.assertEqual(return_batch_size, 1)
        self.assertTrue(mock_reporter.called)

    def test_collision(self):
        self.assertEqual(basic_utils.collision_rename('test'), 'test')

    def test_collision_rename_directory(self):
        dir_name = tempfile.mkdtemp()
        dir_rename = basic_utils.collision_rename(dir_name)
        self.assertEqual('%s.renamed' % dir_name, dir_rename)
        os.removedirs(dir_name)

    def test_mkdir_p(self):
        dir_name = tempfile.mkdtemp()
        if not os.path.exists(dir_name):
            self.fail('Failed to create base directory')
        else:
            long_dir_name = os.path.join(dir_name, 'test/path')
            basic_utils.mkdir_p(long_dir_name)
            if not os.path.exists(long_dir_name):
                self.fail('Failed to create recursive directories.')

    def test_mkdir_p_failure(self):
        os = mock.Mock(side_effect=OSError('TEST EXCEPTION'))
        with mock.patch('turbolift.utils.basic_utils.os.makedirs', os):
            self.assertRaises(
                turbolift.DirectoryFailure, basic_utils.mkdir_p, 'test'
            )

    def test_set_unique_dirs(self):
        fake_object_list = [
            'testone/1',
            'testone/1',
            'testtwo/2',
            'testtwo/2',
            'testthree/3'
        ]
        return_object_list = basic_utils.set_unique_dirs(
            object_list=fake_object_list, root_dir='/test/dir/'
        )
        self.assertNotEqual(len(fake_object_list), len(return_object_list))

    def test_get_sfile_with_preserver_path(self):
        args = {'preserve_path': True}
        with mock.patch('turbolift.utils.basic_utils.turbo.ARGS', args):
            obj = basic_utils.get_sfile(ufile='object1', source='test/dir')
            self.assertEqual(obj, 'test/dir/object1')

    @mock.patch('turbolift.utils.basic_utils.turbo.ARGS', {})
    def test_get_sfile_isfile(self):
        os = mock.Mock().return_value(True)
        with mock.patch('turbolift.utils.basic_utils.os.path.isfile', os):
            obj = basic_utils.get_sfile(ufile='object1', source='test/dir')
            self.assertEqual(obj, 'dir')

    @mock.patch('turbolift.utils.basic_utils.turbo.ARGS', {})
    def test_get_sfile_dot_source(self):
        def fake_cwd():
            return '/some/dir'

        with mock.patch('turbolift.utils.basic_utils.os.getcwd', fake_cwd):
            obj = basic_utils.get_sfile(ufile='object1', source='.')
            self.assertEqual(obj, '/some/dir')

    @mock.patch('turbolift.utils.basic_utils.turbo.ARGS', {})
    def test_get_sfile_dot_source(self):
        obj = basic_utils.get_sfile(ufile='/test/object1', source='/test')
        self.assertEqual(obj, 'object1')

    def test_real_full_path_relitive_path(self):
        os.environ['HOME'] = '/home/test'
        obj = basic_utils.real_full_path(object='~/test/dir')
        self.assertEqual(obj, '/home/test/test/dir')

    def test_real_full_path(self):
        obj = basic_utils.real_full_path(object='/test/dir')
        self.assertEqual(obj, '/test/dir')

    # def test_get_local_source(self):
    #     self.fail('no test made yet')
    #
    # def test_ustr(self):
    #     self.fail('no test made yet')
    #
    # def test_retryloop(self):
    #     self.fail('no test made yet')
    #
    # def test_restor_perms(self):
    #     self.fail('no test made yet')
    #
    # def test_stat_file(self):
    #     self.fail('no test made yet')
    #
    # def test_stupid_hack(self):
    #     self.fail('no test made yet')
    #
    # def test_match_filter(self):
    #     self.fail('no test made yet')

########NEW FILE########
__FILENAME__ = auth_utils
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import traceback

import turbolift as turbo
import turbolift.utils.http_utils as http

from turbolift import ARGS
from turbolift import info
from turbolift import LOG


def parse_reqtype():
    """Setup our Authentication POST.

    username and setup are only used in APIKEY/PASSWORD Authentication
    """

    setup = {'username': ARGS.get('os_user')}
    if ARGS.get('os_token') is not None:
        auth_body = {'auth': {'token': {'id': ARGS.get('os_token')}}}
    elif ARGS.get('os_password') is not None:
        prefix = 'passwordCredentials'
        setup['password'] = ARGS.get('os_password')
        auth_body = {'auth': {prefix: setup}}
    elif ARGS.get('os_apikey') is not None:
        prefix = 'RAX-KSKEY:apiKeyCredentials'
        setup['apiKey'] = ARGS.get('os_apikey')
        auth_body = {'auth': {prefix: setup}}
    else:
        LOG.error(traceback.format_exc())
        raise AttributeError('No Password, APIKey, or Token Specified')

    if ARGS.get('os_tenant'):
        auth_body['auth']['tenantName'] = ARGS.get('os_tenant')

    LOG.debug('AUTH Request Type > %s', auth_body)
    return auth_body


def get_surl(region, cf_list, lookup):
    """Lookup a service URL.

    :param region:
    :param cf_list:
    :param lookup:
    :return net:
    """

    for srv in cf_list:
        region_get = srv.get('region')
        lookup_get = srv.get(lookup)
        if any([region in region_get, region.lower() in region_get]):
            if lookup_get is None:
                return None
            else:
                return http.parse_url(url=lookup_get)
    else:
        raise turbo.SystemProblem(
            'Region "%s" was not found in your Service Catalog.' % region
        )


def parse_auth_response(auth_response):
    """Parse the auth response and return the tenant, token, and username.

    :param auth_response: the full object returned from an auth call
    :returns: tuple (token, tenant, username, internalurl, externalurl, cdnurl)
    """

    def _service_ep(scat, types_list):
        for srv in scat:
            if srv.get('name') in types_list:
                index_id = types_list.index(srv.get('name'))
                index = types_list[index_id]
                if srv.get('name') == index:
                    return srv.get('endpoints')
        else:
            return None

    access = auth_response.get('access')
    token = access.get('token').get('id')

    if 'tenant' in access.get('token'):
        tenant = access.get('token').get('tenant').get('name')
        user = access.get('user').get('name')
    elif 'user' in access:
        tenant = None
        user = access.get('user').get('name')
    else:
        LOG.error('No Token Found to Parse.\nHere is the DATA: %s\n%s',
                  auth_response, traceback.format_exc())
        raise turbo.NoTenantIdFound('When attempting to grab the '
                                    'tenant or user nothing was found.')

    if ARGS.get('os_rax_auth') is not None:
        region = ARGS.get('os_rax_auth')
    elif ARGS.get('os_hp_auth') is not None:
        if ARGS.get('os_tenant') is None:
            raise turbo.NoTenantIdFound(
                'You need to have a tenant set to use HP Cloud'
            )
        region = ARGS.get('os_hp_auth')
    elif ARGS.get('os_region') is not None:
        region = ARGS.get('os_region')
    else:
        raise turbo.SystemProblem('No Region Set')

    scat = access.pop('serviceCatalog')

    cfl = _service_ep(scat, info.__srv_types__)
    cdn = _service_ep(scat, info.__cdn_types__)

    if cfl is not None:
        inet = get_surl(region=region, cf_list=cfl, lookup='internalURL')
        enet = get_surl(region=region, cf_list=cfl, lookup='publicURL')
    else:
        need_tenant = ' Maybe you need to specify "os-tenant"?'
        gen_message = ('No Service Endpoints were found for use with Swift.'
                       ' If you have Swift available to you,'
                       ' Check Your Credentials and/or Swift\'s availability'
                       ' using Token Auth.')
        if ARGS.get('os_tenant') is None:
            gen_message += need_tenant
        raise turbo.SystemProblem(gen_message)

    if cdn is not None:
        cnet = get_surl(region=region, cf_list=cdn, lookup='publicURL')
    else:
        cnet = None

    return token, tenant, user, inet, enet, cnet, cfl


def parse_region():
    """Pull region/auth url information from context."""

    if ARGS.get('os_rax_auth'):
        region = ARGS.get('os_rax_auth')
        auth_url = 'identity.api.rackspacecloud.com/v2.0/tokens'
        if region is 'LON':
            return ARGS.get('os_auth_url', 'https://lon.%s' % auth_url)
        elif region.lower() in info.__rax_regions__:
            return ARGS.get('os_auth_url', 'https://%s' % auth_url)
        else:
            raise turbo.SystemProblem('No Known RAX Region Was Specified')
    elif ARGS.get('os_hp_auth'):
        region = ARGS.get('os_hp_auth')
        auth_url = 'https://%s.identity.hpcloudsvc.com:35357/v2.0/tokens'
        if region.lower() in info.__hpc_regions__:
            return ARGS.get('os_auth_url', auth_url % region)
        else:
            raise turbo.SystemProblem('No Known HP Region Was Specified')
    elif ARGS.get('os_auth_url'):
        return ARGS.get('os_auth_url')
    else:
        raise turbo.SystemProblem(
            'You Are required to specify an Auth URL, Region or Plugin'
        )

########NEW FILE########
__FILENAME__ = basic_utils
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import datetime
import errno
import grp
import json
import os
import pwd
import random
import re
import string
import tempfile
import time

import turbolift as turbo
import turbolift.utils.report_utils as report


def time_stamp():
    """Setup time functions

    :return (fmt, date, date_delta, now):
    """

    # Time constants
    fmt = '%Y-%m-%dT%H:%M:%S.%f'
    date = datetime.datetime
    date_delta = datetime.timedelta
    now = datetime.datetime.utcnow()

    return fmt, date, date_delta, now


def json_encode(read):
    """Return a json encoded object.

    :param read:
    :return:
    """

    return json.loads(read)


def unique_list_dicts(dlist, key):
    """Return a list of dictionaries which have sorted for only unique entries.

    :param dlist:
    :param key:
    :return list:
    """

    return dict((val[key], val) for val in dlist).values()


def dict_pop_none(dictionary):
    """Parse all keys in a dictionary for Values that are None.

    :param dictionary: all parsed arguments
    :returns dict: all arguments which are not None.
    """

    return dict([(key, value) for key, value in dictionary.iteritems()
                 if value is not None if value is not False])


def keys2dict(chl):
    """Take a list of strings and turn it into dictionary.

    :param chl:
    :return {}|None:
    """

    if chl:
        return dict([_kv.split('=') for _kv in chl])
    else:
        return None


def jpath(root, inode):
    """Return joined directory / path

    :param root:
    :param inode:
    :return "root/inode":
    """

    return os.path.join(root, inode)


def rand_string(length=15):
    """Generate a Random string."""

    chr_set = string.ascii_uppercase
    output = ''

    for _ in range(length):
        output += random.choice(chr_set)
    return output


def create_tmp():
    """Create a tmp file.

    :return str:
    """

    return tempfile.mkstemp()[1]


def remove_file(filename):
    """Remove a file if its found.

    :param filename:
    """

    if file_exists(filename):
        try:
            os.remove(filename)
        except OSError:
            pass


def file_exists(filename):
    """Return True|False if a File Exists.

    :param filename:
    :return True|False:
    """

    return os.path.exists(filename)


def batcher(num_files):
    """Check the batch size and return it.

    :param num_files:
    :return int:
    """

    batch_size = turbo.ARGS.get('batch_size')
    report.reporter(
        msg='Job process MAX Batch Size is "%s"' % batch_size,
        lvl='debug',
        log=True,
        prt=False
    )
    ops = num_files / batch_size + 1
    report.reporter(
        msg='This will take "%s" operations to complete.' % ops,
        lvl='warn',
        log=True,
        prt=True
    )
    return batch_size


def collision_rename(file_name):
    """Rename file on Collision.

    If the file name is a directory and already exists rename the file to
    %s.renamed, else return the file_name

    :param file_name:
    :return file_name:
    """
    if os.path.isdir(file_name):
        return '%s.renamed' % file_name
    else:
        return file_name


def mkdir_p(path):
    """'mkdir -p' in Python

    Original Code came from :
    stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
    :param path:
    """

    try:
        if not os.path.isdir(path):
            os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise turbo.DirectoryFailure(
                'The path provided, "%s", is either occupied and can\'t be'
                ' used as a directory or the permissions will not allow you to'
                ' write to this location.' % path
            )


def set_unique_dirs(object_list, root_dir):
    """From an object list create a list of unique directories.

    :param object_list:
    :param root_dir:
    """

    unique_dirs = []
    for obj in object_list:
        full_path = jpath(root=root_dir, inode=obj.lstrip(os.sep))
        dir_path = full_path.split(
            os.path.basename(full_path)
        )[0].rstrip(os.sep)
        unique_dirs.append(dir_path)
    return set(unique_dirs)


def get_sfile(ufile, source):
    """Return the source file

    :param ufile:
    :param source:
    :return file_name:
    """

    if turbo.ARGS.get('preserve_path'):
        return os.path.join(source, ufile).lstrip(os.sep)
    if os.path.isfile(source):
        return os.path.basename(source)
    elif source is '.':
        return os.getcwd()
    else:
        try:
            base, sfile = ufile.split(source)
            return os.sep.join(sfile.split(os.sep)[1:])
        except ValueError:
            report.reporter(
                msg='ValueError Error when unpacking - %s %s' % (ufile, source)
            )
            return None


def real_full_path(object):
    """Return a string with the real full path of an object.

    :param object:
    :return str:
    """

    return os.path.realpath(
        os.path.expanduser(
            object
        )
    )


def get_local_source():
    """Understand the Local Source and return it.

    :param turbo.ARGS:
    :return source:
    """

    local_path = real_full_path(turbo.ARGS.get('source'))
    if os.path.isdir(local_path):
        return local_path.rstrip(os.sep)
    else:
        return os.path.split(local_path)[0].rstrip(os.sep)


def ustr(obj):
    """If an Object is unicode convert it.

    :param object:
    :return:
    """
    if obj is not None and isinstance(obj, unicode):
        return str(obj.encode('utf8'))
    else:
        return obj


def retryloop(attempts, timeout=None, delay=None, backoff=1, obj=None):
    """Enter the amount of retries you want to perform.

    The timeout allows the application to quit on "X".
    delay allows the loop to wait on fail. Useful for making REST calls.

    ACTIVE STATE retry loop
    http://code.activestate.com/recipes/578163-retry-loop/

    Example:
        Function for retring an action.
        for retry in retryloop(attempts=10, timeout=30, delay=1, backoff=1):
            something
            if somecondition:
                retry()

    :param attempts:
    :param timeout:
    :param delay:
    :param backoff:
    """

    starttime = time.time()
    success = set()
    for _ in range(attempts):
        success.add(True)
        yield success.clear
        if success:
            return
        duration = time.time() - starttime
        if timeout is not None and duration > timeout:
            break
        if delay:
            time.sleep(delay)
            delay = delay * backoff
    report.reporter(
        msg=('RetryError: FAILED TO PROCESS "%s" after "%s" Attempts'
             % (obj, attempts)),
        lvl='critical',
        log=True
    )


def restor_perms(local_file, headers):
    """Restore Permissions, UID, GID from metadata.

    :param local_file:
    :param headers:
    """

    # Restore Permissions.
    os.chmod(
        local_file,
        int(headers['x-object-meta-perms'], 8)
    )

    # Lookup user and group name and restore them.
    os.chown(
        local_file,
        pwd.getpwnam(headers['x-object-meta-owner']).pw_uid,
        grp.getgrnam(headers['x-object-meta-group']).gr_gid
    )


def stat_file(local_file):
    """Stat a file and return the Permissions, UID, GID.

    :param local_file:
    :return dict:
    """

    obj = os.stat(local_file)
    return {'X-Object-Meta-perms': oct(obj.st_mode)[-4:],
            'X-Object-Meta-owner': pwd.getpwuid(obj.st_uid).pw_name,
            'X-Object-Meta-group': grp.getgrgid(obj.st_gid).gr_name}


def stupid_hack(most=10, wait=None):
    """Return a random time between 1 - 10 Seconds."""

    # Stupid Hack For Public Cloud so it is not overwhelmed with API requests.
    if wait is not None:
        time.sleep(wait)
    else:
        time.sleep(random.randrange(1, most))


def match_filter(idx_list, pattern, dict_type=False, dict_key='name'):
    """Match items in indexed files.

    :param idx_list:
    :return list
    """

    if idx_list:
        if dict_type is False:
            return [obj for obj in idx_list
                    if re.search(pattern, obj)]
        elif dict_type is True:
            return [obj for obj in idx_list
                    if re.search(pattern, obj.get(dict_key))]
    else:
        return idx_list

########NEW FILE########
__FILENAME__ = http_utils
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import httplib
import traceback
import urllib
import urlparse

import requests

import turbolift.utils.basic_utils as basic
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift import LOG


# Enable Debug Mode if its set
if ARGS is not None and ARGS.get('debug'):
    httplib.HTTPConnection.debuglevel = 1


def set_headers(headers):
    """Set the headers used in the Cloud Files Request.

    :return headers:
    """

    # Set the headers if some custom ones were specified
    if ARGS.get('base_headers'):
        headers.update(ARGS.get('base_headers'))

    return headers


def container_headers(headers):
    """Return updated Container Headers."""

    return headers.update(ARGS.get('container_headers'))


def parse_url(url, auth=False):
    """Return a clean URL. Remove the prefix for the Auth URL if Found.

    :param url:
    :return aurl:
    """

    if all([auth is True, 'tokens' not in url]):
            url = urlparse.urljoin(url, 'tokens')

    if url.startswith(('http', 'https', '//')):
        if url.startswith('//'):
            return urlparse.urlparse(url, scheme='http')
        else:
            return urlparse.urlparse(url)
    else:
        return urlparse.urlparse('http://%s' % url)


def prep_payload(auth, container, source, args):
    """Create payload dictionary.

    :param auth:
    :param container:
    :param source:
    :return (dict, dict): payload and headers
    """

    if container is not None and '/' in container:
        raise SystemExit(
            report.reporter(
                msg='Containers may not have a "/" in them.',
                lvl='error'
            )
        )

    # Unpack the values from Authentication
    token, tenant, user, inet, enet, cnet, aurl, acfep = auth

    # Get the headers ready
    headers = set_headers({'X-Auth-Token': token})

    if args.get('internal'):
        url = inet
    else:
        url = enet

    # Set the upload Payload
    return {'c_name': container,
            'source': source,
            'tenant': tenant,
            'headers': headers,
            'user': user,
            'cnet': cnet,
            'aurl': aurl,
            'url': url,
            'acfep': acfep}


def quoter(url, cont=None, ufile=None):
    """Return a Quoted URL.

    :param url:
    :param cont:
    :param ufile:
    :return:
    """

    url = basic.ustr(obj=url)
    if cont is not None:
        cont = basic.ustr(obj=cont)
    if ufile is not None:
        ufile = basic.ustr(obj=ufile)

    if ufile is not None and cont is not None:
        return urllib.quote(
            '%s/%s/%s' % (url, cont, ufile)
        )
    elif cont is not None:
        return urllib.quote(
            '%s/%s' % (url, cont)
        )
    else:
        return urllib.quote(
            '%s' % url
        )


def cdn_toggle(headers):
    """Set headers to Enable or Disable the CDN."""

    enable_or_disable = ARGS.get('enabled', ARGS.get('disable', False))
    return headers.update({'X-CDN-Enabled': enable_or_disable,
                           'X-TTL': ARGS.get('cdn_ttl'),
                           'X-Log-Retention': ARGS.get('cdn_logs')})


def post_request(url, headers, body=None, rpath=None):
    """Perform HTTP(s) POST request based on Provided Params.

    :param url:
    :param rpath:
    :param headers:
    :param body:
    :return resp:
    """

    try:
        if rpath is not None:
            _url = urlparse.urljoin(urlparse.urlunparse(url), rpath)
        else:
            _url = urlparse.urlunparse(url)

        kwargs = {'timeout': ARGS.get('timeout', 60)}
        resp = requests.post(_url, data=body, headers=headers, **kwargs)
    except Exception as exp:
        LOG.error('Not able to perform Request ERROR: %s', exp)
        raise AttributeError("Failure to perform Authentication %s ERROR:\n%s"
                             % (exp, traceback.format_exc()))
    else:
        return resp


def head_request(url, headers, rpath):
    try:
        _url = urlparse.urljoin(urlparse.urlunparse(url), rpath)

        kwargs = {'timeout': ARGS.get('timeout')}
        resp = requests.head(_url, headers=headers, **kwargs)
        report.reporter(
            msg='INFO: %s %s %s' % (resp.status_code,
                                    resp.reason,
                                    resp.request),
            prt=False
        )
    except Exception as exp:
        report.reporter(
            'Not able to perform Request ERROR: %s' % exp,
            lvl='error',
            log=True
        )
    else:
        return resp


def put_request(url, headers, rpath, body=None):
    try:
        _url = urlparse.urljoin(urlparse.urlunparse(url), rpath)

        kwargs = {'timeout': ARGS.get('timeout')}
        resp = requests.put(_url, data=body, headers=headers, **kwargs)
        report.reporter(
            msg='INFO: %s %s %s' % (resp.status_code,
                                    resp.reason,
                                    resp.request),
            prt=False
        )
    except Exception as exp:
        LOG.error('Not able to perform Request ERROR: %s', exp)
    else:
        return resp


def delete_request(url, headers, rpath):
    try:
        _url = urlparse.urljoin(urlparse.urlunparse(url), rpath)

        kwargs = {'timeout': ARGS.get('timeout')}
        resp = requests.delete(_url, headers=headers, **kwargs)
        report.reporter(
            msg='INFO: %s %s %s' % (resp.status_code,
                                    resp.reason,
                                    resp.request),
            prt=False
        )
    except Exception as exp:
        LOG.error('Not able to perform Request ERROR: %s', exp)
    else:
        return resp


def get_request(url, headers, rpath, stream=False):
    try:
        _url = urlparse.urljoin(urlparse.urlunparse(url), rpath)

        kwargs = {'timeout': ARGS.get('timeout')}
        resp = requests.get(_url, headers=headers, stream=stream, **kwargs)
        report.reporter(
            msg='INFO: %s %s %s' % (resp.status_code,
                                    resp.reason,
                                    resp.request),
            prt=False
        )
    except Exception as exp:
        LOG.error('Not able to perform Request ERROR: %s', exp)
    else:
        return resp

########NEW FILE########
__FILENAME__ = multi_utils
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import contextlib
import multiprocessing
import Queue
import sys
import time

import turbolift as turbo
import turbolift.utils.basic_utils as basic
import turbolift.utils.report_utils as report

from turbolift import ARGS
from turbolift import methods


class IndicatorThread(object):
    """Creates a visual indicator while normally performing actions."""

    def __init__(self, work_q=None, system=True):
        """System Operations Available on Load.

        :param work_q:
        :param system:
        """

        self.work_q = work_q
        self.system = system

    def indicator(self):
        """Produce the spinner."""

        with methods.operation(retry=turbo.emergency_kill):
            while self.system:
                busy_chars = ['|', '/', '-', '\\']
                for _cr in busy_chars:
                    # Fixes Errors with OS X due to no sem_getvalue support
                    if self.work_q is not None:
                        if not sys.platform.startswith('darwin'):
                            size = self.work_q.qsize()
                            if size > 0:
                                _qz = 'Number of Jobs in Queue = %s ' % size
                            else:
                                _qz = 'Waiting for in-process Jobs to finish '
                        else:
                            _qz = 'Waiting for in-process Jobs to finish. '
                    else:
                        _qz = 'Please Wait... '
                    sys.stdout.write('\rProcessing - [ %(spin)s ] - %(qsize)s'
                                     % {"qsize": _qz, "spin": _cr})
                    sys.stdout.flush()
                    time.sleep(.1)
                    self.system = self.system

    def indicator_thread(self):
        """indicate that we are performing work in a thread."""

        job = multiprocessing.Process(target=self.indicator)
        job.start()
        return job


def manager_dict(dictionary):
    """Create and return a Manger Dictionary.

    :param dictionary:
    :return dict:
    """

    manager = multiprocessing.Manager()
    return manager.dict(dictionary)


def basic_queue(iters=None):
    """Uses a manager Queue, from multiprocessing.

    All jobs will be added to the queue for processing.
    :param iters:
    """

    worker_q = multiprocessing.Queue()
    if iters is not None:
        for _dt in iters:
            worker_q.put(_dt)
    return worker_q


def get_from_q(queue):
    """Returns the file or a sentinel value.

    :param queue:
    :return item|None:
    """

    try:
        wfile = queue.get(timeout=5)
    except Queue.Empty:
        return None
    else:
        if isinstance(wfile, str):
            return wfile.strip()
        else:
            return wfile


def worker_proc(job_action, concurrency, queue, kwargs, opt):
    """Requires the job_action and num_jobs variables for functionality.

    :param job_action: What function will be used
    :param concurrency: The number of jobs that will be processed
    :param queue: The Queue
    :param t_args: Optional

    All threads produced by the worker are limited by the number of concurrency
    specified by the user. The Threads are all made active prior to them
    processing jobs.
    """

    arguments = []
    for item in [queue, opt, kwargs]:
        if item is not None:
            arguments.append(item)

    jobs = [multiprocessing.Process(target=job_action,
                                    args=tuple(arguments))
            for _ in xrange(concurrency)]

    report.reporter(
        msg='Thread Starting Cycle',
        lvl='info',
        log=True,
        prt=True
    )
    join_jobs = []
    for _job in jobs:
        join_jobs.append(_job)
        basic.stupid_hack(wait=.01)
        _job.daemon = True
        _job.start()

    for job in join_jobs:
        job.join()


class ReturnDiff(object):
    def __init__(self):
        """Compare the target list to the source list and return the diff."""

        self.target = None
        self.opt = None

    def _checker(self, work_q, payload):
        """Check if an object is in the target, if so append to manager list.

        :param work_q:
        :param payload:
        """

        while True:
            sobj = get_from_q(work_q)
            if sobj is None:
                break
            elif sobj not in self.target:
                if self.opt is not None:
                    self.opt(sobj)
                else:
                    payload.append(sobj)

    def difference(self, target, source, opt=None):
        """Process the diff.

        :param target:
        :param source:
        :param opt: THIS IS AN OPTIONAL FUNCTION...
                    ... which the difference "result" will run.
        :return list:
        """

        # Load the target into the class
        self.target = target
        if opt is not None:
            self.opt = opt

        manager = multiprocessing.Manager()
        proxy_list = manager.list()

        # Get The rate of concurrency
        num_files = len(source)
        concurrency = multiprocessing.cpu_count() * 32
        if concurrency > 128:
            concurrency = 128

        job_processer(
            num_jobs=num_files,
            objects=source,
            job_action=self._checker,
            concur=concurrency,
            opt=proxy_list
        )

        return list(proxy_list)


def job_processer(num_jobs, objects, job_action, concur, kwargs=None,
                  opt=None):
    """Process all jobs in batches.

    :param num_jobs:
    :param objects:
    :param job_action:
    :param concur:
    :param payload:
    """

    count = 0
    batch_size = basic.batcher(num_files=num_jobs)
    while objects:
        count += 1
        report.reporter(msg='Job Count %s' % count)
        work = [
            objects.pop(objects.index(obj)) for obj in objects[0:batch_size]
        ]
        work_q = basic_queue(work)
        with spinner(work_q=work_q):
            worker_proc(
                job_action=job_action,
                concurrency=concur,
                queue=work_q,
                opt=opt,
                kwargs=kwargs
            )
            basic.stupid_hack(wait=.2)
        work_q.close()


def set_concurrency(args, file_count):
    """Concurrency is a user specified variable when the arguments parsed.

    :param args:

    However if the number of things Turbo lift has to do is less than the
    desired concurency, then turbolift will lower the concurency rate to
    the number of operations.
    """

    def verbose(ccr):
        report.reporter(
            msg='MESSAGE: We are creating %s Processes' % ccr,
            prt=False
        )
        return ccr

    _cc = args.get('cc')

    if _cc > file_count:
        report.reporter(
            msg=('MESSAGE: There are less things to do than the number of'
                 ' concurrent processes specified by either an override'
                 ' or the system defaults. I am leveling the number of'
                 ' concurrent processes to the number of jobs to perform.'),
            lvl='warn'
        )
        return verbose(ccr=file_count)
    else:
        return verbose(ccr=_cc)


def doerator(work_q, kwargs):
    """Do Jobs until done.

    :param work_q:
    :param job:
    """
    job = kwargs.pop('cf_job')
    while True:
        # Get the file that we want to work with
        wfile = get_from_q(queue=work_q)

        # If Work is None return None
        if wfile is None:
            break
        try:
            # Do the job that was provided
            kwargs['u_file'] = wfile
            job(**kwargs)
        except EOFError:
            turbo.emergency_kill()
        except KeyboardInterrupt:
            turbo.emergency_kill(reclaim=True)


@contextlib.contextmanager
def spinner(work_q=None):
    """Show a fancy spinner while we have work running.

    :param work_q:
    :return:
    """
    itd = None
    if any([ARGS.get('verbose') is True, ARGS.get('quiet') is True]):
        yield
    else:
        set_itd = IndicatorThread(work_q=work_q)
        try:
            itd = set_itd.indicator_thread()
            yield
        finally:
            if itd is not None:
                itd.terminate()

########NEW FILE########
__FILENAME__ = report_utils
# =============================================================================
# Copyright [2013] [kevin]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
import prettytable

import turbolift as turbo


def print_horiz_table(data):
    """Print a horizontal pretty table from data."""

    table = prettytable.PrettyTable(dict(data[0]).keys())

    for info in data:
        table.add_row(dict(info).values())
    for tbl in table.align.keys():
        table.align[tbl] = 'l'
    return table


def print_virt_table(data):
    """Print a vertical pretty table from data."""

    table = prettytable.PrettyTable()
    table.add_column('Keys', data.keys())
    table.add_column('Values', data.values())
    for tbl in table.align.keys():
        table.align[tbl] = 'l'
    return table


def reporter(msg, prt=True, lvl='info', log=False, color=False):
    """Print Messages and Log it.

    :param msg:
    :param prt:
    :param lvl:
    """

    # Print a Message
    if prt is True or turbo.ARGS.get('verbose') is True:
        if lvl is 'error':
            if turbo.ARGS.get('colorized') is True:
                msg = bcolors(msg, lvl)
            print(msg)
        else:
            if turbo.ARGS.get('quiet') is None:
                if turbo.ARGS.get('colorized') is True:
                    msg = bcolors(msg, lvl)
                print(msg)

    # Log message
    if any([turbo.ARGS.get('verbose') is True,
            lvl in ['debug', 'warn', 'error'],
            log is True]):
        logger = getattr(turbo.LOG, lvl)
        if turbo.ARGS.get('colorized'):
            logger(bcolors(msg, lvl))
        else:
            logger(msg)


def bcolors(msg, color):
    """return a colorizes string.

    :param msg:
    :param color:
    :return str:
    """

    # Available Colors
    colors = {'debug': '\033[94m',
              'info': '\033[92m',
              'warn': '\033[93m',
              'error': '\033[91m',
              'critical': '\033[95m',
              'ENDC': '\033[0m'}

    if color in colors:
        return '%s%s%s' % (colors[color], msg, colors['ENDC'])
    else:
        raise turbo.SystemProblem('"%s" was not a known color.' % color)

########NEW FILE########
__FILENAME__ = worker
# =============================================================================
# Copyright [2013] [Kevin Carter]
# License Information :
# This software has no warranty, it is provided 'as is'. It is your
# responsibility to validate the behavior of the routines and its accuracy
# using the code provided. Consult the GNU General Public license for further
# details (see GNU General Public License).
# http://www.gnu.org/licenses/gpl.html
# =============================================================================
from turbolift import ARGS


def start_work():
    """Begin Work."""

    def get_method(method, name):
        """Import what is required to run the System."""

        to_import = '%s.%s' % (method.__name__, name)
        return __import__(to_import, fromlist="None")

    def get_actions(module, name):
        """Get all available actions from an imported method.

        :param module:
        :param name:
        :return method attributes:
        """

        return getattr(module, name)

    # Low imports for load in module.
    import pkgutil

    # Low imports for load in module.
    import turbolift as turbo
    from turbolift.authentication import authentication as auth
    from turbolift import methods as met

    try:
        for mod, name, package in pkgutil.iter_modules(met.__path__):
            if ARGS.get(name) is not None:
                titled_name = name.title().replace('_', '')
                method = get_method(method=met, name=name)
                actions = get_actions(module=method, name=titled_name)
                actions(auth=auth.authenticate()).start()
                break
        else:
            raise turbo.SystemProblem('No Method set for processing')
    except KeyboardInterrupt:
        turbo.emergency_kill(reclaim=True)

########NEW FILE########
