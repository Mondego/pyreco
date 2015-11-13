__FILENAME__ = command
import os

from twiggy import log
from lockfile import LockTimeout
from lockfile.pidlockfile import PIDLockFile

from taskw.warrior import TaskWarriorBase

from bugwarrior.config import get_taskrc_path, load_config
from bugwarrior.services import aggregate_issues
from bugwarrior.db import synchronize


def pull():
    try:
        # Load our config file
        config = load_config()

        tw_config = TaskWarriorBase.load_config(get_taskrc_path(config))
        lockfile_path = os.path.join(
            os.path.expanduser(
                tw_config['data']['location']
            ),
            'bugwarrior.lockfile'
        )

        lockfile = PIDLockFile(lockfile_path)
        lockfile.acquire(timeout=10)
        try:
            # Get all the issues.  This can take a while.
            issue_generator = aggregate_issues(config)

            # Stuff them in the taskwarrior db as necessary
            synchronize(issue_generator, config)
        finally:
            lockfile.release()
    except LockTimeout:
        log.name('command').critical(
            'Your taskrc repository is currently locked. '
            'Remove the file at %s if you are sure no other '
            'bugwarrior processes are currently running.' % (
                lockfile_path
            )
        )
    except:
        log.name('command').trace('error').critical('oh noes')

########NEW FILE########
__FILENAME__ = config
import codecs
from ConfigParser import ConfigParser
import optparse
import os
import subprocess
import sys

import six
import twiggy
from twiggy import log
from twiggy.levels import name2level


def asbool(some_value):
    """ Cast config values to boolean. """
    return six.text_type(some_value).lower() in [
        'y', 'yes', 't', 'true', '1', 'on'
    ]


def get_service_password(service, username, oracle=None, interactive=False):
    """
    Retrieve the sensitive password for a service by:

      * retrieving password from a secure store (@oracle:use_keyring, default)
      * asking the password from the user (@oracle:ask_password, interactive)
      * executing a command and use the output as password
        (@oracle:eval:<command>)

    Note that the keyring may or may not be locked
    which requires that the user provides a password (interactive mode).

    :param service:     Service name, may be key into secure store (as string).
    :param username:    Username for the service (as string).
    :param oracle:      Hint which password oracle strategy to use.
    :return: Retrieved password (as string)

    .. seealso::
        https://bitbucket.org/kang/python-keyring-lib
    """
    import getpass
    import keyring

    password = None
    if not oracle or oracle == "@oracle:use_keyring":
        password = keyring.get_password(service, username)
        if interactive and password is None:
            # -- LEARNING MODE: Password is not stored in keyring yet.
            oracle = "@oracle:ask_password"
            password = get_service_password(service, username,
                                            oracle, interactive=True)
            if password:
                keyring.set_password(service, username, password)
    elif interactive and oracle == "@oracle:ask_password":
        prompt = "%s password: " % service
        password = getpass.getpass(prompt)
    elif oracle.startswith('@oracle:eval:'):
        command = oracle[13:]
        p = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        password = p.stdout.read()[:-1]

    if password is None:
        die("MISSING PASSWORD: oracle='%s', interactive=%s for service=%s" %
            (oracle, interactive, service))
    return password


def load_example_rc():
    fname = os.path.join(
        os.path.dirname(__file__),
        '../docs/source/configuration.rst'
    )
    with open(fname, 'r') as f:
        readme = f.read()
    example = readme.split('.. example')[1][4:]
    return example

error_template = """
*************************************************
* There was a problem with your ~/.bugwarriorrc *
*   {msg}
* Here's an example template to help:           *
*************************************************
{example}"""


def die(msg):
    log.options(suppress_newlines=False).critical(
        error_template,
        msg=msg,
        example=load_example_rc(),
    )
    sys.exit(1)


def parse_args():
    p = optparse.OptionParser()
    p.add_option('-f', '--config', default='~/.bugwarriorrc')
    p.add_option('-i', '--interactive', action='store_true', default=False)
    return p.parse_args()


def validate_config(config):
    if not config.has_section('general'):
        die("No [general] section found.")

    twiggy.quickSetup(
        name2level(config.get('general', 'log.level')),
        config.get('general', 'log.file')
    )

    if not config.has_option('general', 'targets'):
        die("No targets= item in [general] found.")

    targets = config.get('general', 'targets')
    targets = [t.strip() for t in targets.split(",")]

    for target in targets:
        if target not in config.sections():
            die("No [%s] section found." % target)

    # Validate each target one by one.
    for target in targets:
        service = config.get(target, 'service')
        if not service:
            die("No 'service' in [%s]" % target)

        if service not in SERVICES:
            die("'%s' in [%s] is not a valid service." % (service, target))

        # Call the service-specific validator
        SERVICES[service].validate_config(config, target)


def load_config():
    opts, args = parse_args()

    config = ConfigParser({'log.level': "DEBUG", 'log.file': None})
    config.readfp(
        codecs.open(
            os.path.expanduser(opts.config),
            "r",
            "utf-8",
        )
    )
    config.interactive = opts.interactive
    validate_config(config)

    return config


def get_taskrc_path(conf):
    path = '~/.taskrc'
    if conf.has_option('general', 'taskrc'):
        path = conf.get('general', 'taskrc')
    return os.path.normpath(
        os.path.expanduser(path)
    )


# This needs to be imported here and not above to avoid a circular-import.
from bugwarrior.services import SERVICES

########NEW FILE########
__FILENAME__ = db
from ConfigParser import NoOptionError
import os
import re
import subprocess

import requests
import dogpile.cache
import six
from twiggy import log
from taskw import TaskWarriorShellout
from taskw.exceptions import TaskwarriorError

from bugwarrior.config import asbool, get_taskrc_path
from bugwarrior.notifications import send_notification


MARKUP = "(bw)"


DOGPILE_CACHE_PATH = os.path.expanduser('~/.cache/dagd.dbm')
if not os.path.isdir(os.path.dirname(DOGPILE_CACHE_PATH)):
    os.mkdirs(os.path.dirname(DOGPILE_CACHE_PATH))
CACHE_REGION = dogpile.cache.make_region().configure(
    "dogpile.cache.dbm",
    arguments=dict(filename=DOGPILE_CACHE_PATH),
)


# Sentinel value used for aborting processing of tasks
ABORT_PROCESSING = 2


class URLShortener(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(URLShortener, cls).__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    @CACHE_REGION.cache_on_arguments()
    def shorten(self, url):
        if not url:
            return ''
        base = 'http://da.gd/s'
        return requests.get(base, params=dict(url=url)).text.strip()


class NotFound(Exception):
    pass


class MultipleMatches(Exception):
    pass


def normalize_description(issue_description):
    return issue_description[:issue_description.index(' .. http')]


def get_normalized_annotation(annotation):
    return re.sub(
        r'[\W_]',
        '',
        six.text_type(annotation)
    )


def sanitize(string):
    """ Sanitize a string for logging with twiggy.

    It is obnoxious that we have to do this ourselves, but twiggy doesn't like
    strings with non-ascii characters or with curly braces in them.
    """
    if not isinstance(string, six.string_types):
        return string
    return six.text_type(string.replace('{', '{{').replace('}', '}}'))


def get_annotation_hamming_distance(left, right):
    left = get_normalized_annotation(left)
    right = get_normalized_annotation(right)
    if len(left) > len(right):
        left = left[0:len(right)]
    elif len(right) > len(left):
        right = right[0:len(left)]
    return hamdist(left, right)


def hamdist(str1, str2):
    """Count the # of differences between equal length strings str1 and str2"""
    diffs = 0
    for ch1, ch2 in zip(str1, str2):
        if ch1 != ch2:
            diffs += 1
    return diffs


def get_managed_task_uuids(tw, key_list, legacy_matching):
    expected_task_ids = set([])
    for keys in key_list.values():
        tasks = tw.filter_tasks({
            'and': [('%s.not' % key, '') for key in keys],
            'or': [
                ('status', 'pending'),
                ('status', 'waiting'),
            ],
        })
        expected_task_ids = expected_task_ids | set([
            task['uuid'] for task in tasks
        ])

    if legacy_matching:
        starts_with_markup = tw.filter_tasks({
            'description.startswith': MARKUP,
            'or': [
                ('status', 'pending'),
                ('status', 'waiting'),
            ],
        })
        expected_task_ids = expected_task_ids | set([
            task['uuid'] for task in starts_with_markup
        ])

    return expected_task_ids


def find_local_uuid(tw, keys, issue, legacy_matching=True):
    """ For a given issue issue, find its local UUID.

    Assembles a list of task IDs existing in taskwarrior
    matching the supplied issue (`issue`) on the combination of any
    set of supplied unique identifiers (`keys`) or, optionally,
    the task's description field (should `legacy_matching` be `True`).

    :params:
    * `tw`: An instance of `taskw.TaskWarriorShellout`
    * `keys`: A list of lists of keys to use for uniquely identifying
      an issue.  To clarify the "list of lists" behavior, assume that
      there are two services, one having a single primary key field
      -- 'serviceAid' -- and another having a pair of fields composing
      its primary key -- 'serviceBproject' and 'serviceBnumber' --, the
      incoming data for this field would be::

        [
            ['serviceAid'],
            ['serviceBproject', 'serviceBnumber'],
        ]

    * `issue`: A instance of a subclass of `bugwarrior.services.Issue`.
    * `legacy_matching`: By default, this is enabled, and it allows
      the matching algorithm to -- in addition to searching by stored
      issue keys -- search using the task's description for a match.

    :returns:
    * A single string UUID.

    :raises:
    * `bugwarrior.db.MultipleMatches`: if multiple matches were found.
    * `bugwarrior.db.NotFound`: if an issue was not found.

    """
    if not issue['description']:
        raise ValueError('Issue %s has no description.' % issue)

    possibilities = set([])

    if legacy_matching:
        legacy_description = issue.get_default_description().rsplit('..', 1)[0]
        results = tw.filter_tasks({
            'description.startswith': legacy_description,
            'or': [
                ('status', 'pending'),
                ('status', 'waiting'),
            ],
        })
        possibilities = possibilities | set([
            task['uuid'] for task in results
        ])

    for service, key_list in six.iteritems(keys):
        if any([key in issue for key in key_list]):
            results = tw.filter_tasks({
                'and': [(key, issue[key]) for key in key_list],
                'or': [
                    ('status', 'pending'),
                    ('status', 'waiting'),
                ],
            })
            possibilities = possibilities | set([
                task['uuid'] for task in results
            ])

    if len(possibilities) == 1:
        return possibilities.pop()

    if len(possibilities) > 1:
        raise MultipleMatches(
            "Issue %s matched multiple IDs: %s" % (
                issue['description'],
                possibilities
            )
        )

    raise NotFound(
        "No issue was found matching %s" % issue
    )


def merge_left(field, local_task, remote_issue, hamming=False):
    """ Merge array field from the remote_issue into local_task

    * Local 'left' entries are preserved without modification
    * Remote 'left' are appended to task if not present in local.

    :param `field`: Task field to merge.
    :param `local_task`: `taskw.task.Task` object into which to merge
        remote changes.
    :param `remote_issue`: `dict` instance from which to merge into
        local task.
    :param `hamming`: (default `False`) If `True`, compare entries by
        truncating to maximum length, and comparing hamming distances.
        Useful generally only for annotations.

    """

    # Ensure that empty defaults are present
    local_field = local_task.get(field, [])
    remote_field = remote_issue.get(field, [])

    # We need to make sure an array exists for this field because
    # we will be appending to it in a moment.
    if field not in local_task:
        local_task[field] = []

    # If a remote does not appear in local, add it to the local task
    new_count = 0
    for remote in remote_field:
        found = False
        for local in local_field:
            if (
                # For annotations, they don't have to match *exactly*.
                (
                    hamming
                    and get_annotation_hamming_distance(remote, local) == 0
                )
                # But for everything else, they should.
                or (
                    remote == local
                )
            ):
                found = True
                break
        if not found:
            log.name('db').debug(
                "%s not found in %r" % (remote, local_field)
            )
            local_task[field].append(remote)
            new_count += 1
    if new_count > 0:
        log.name('db').debug(
            'Added %s new values to %s (total: %s)' % (
                new_count,
                field,
                len(local_task[field]),
            )
        )


def run_hooks(conf, name):
    if conf.has_option('hooks', name):
        pre_import = [
            t.strip() for t in conf.get('hooks', name).split(',')
        ]
        if pre_import is not None:
            for hook in pre_import:
                exit_code = subprocess.call(hook, shell=True)
                if exit_code is not 0:
                    msg = 'Non-zero exit code %d on hook %s' % (
                        exit_code, hook
                    )
                    log.name('hooks:%s' % name).error(msg)
                    raise RuntimeError(msg)


def synchronize(issue_generator, conf):
    def _bool_option(section, option, default):
        try:
            return section in conf.sections() and \
                asbool(conf.get(section, option, default))
        except NoOptionError:
            return default

    targets = [t.strip() for t in conf.get('general', 'targets').split(',')]
    services = set([conf.get(target, 'service') for target in targets])
    key_list = build_key_list(services)
    uda_list = build_uda_config_overrides(services)

    if uda_list:
        log.name('bugwarrior').info(
            'Service-defined UDAs (you can optionally add these to your '
            '~/.taskrc for use in reports):'
        )
        for uda in convert_override_args_to_taskrc_settings(uda_list):
            log.name('bugwarrior').info(uda)

    static_fields = static_fields_default = ['priority']
    if conf.has_option('general', 'static_fields'):
        static_fields = conf.get('general', 'static_fields').split(',')

    # Before running CRUD operations, call the pre_import hook(s).
    run_hooks(conf, 'pre_import')

    notify = _bool_option('notifications', 'notifications', 'False')

    tw = TaskWarriorShellout(
        config_filename=get_taskrc_path(conf),
        config_overrides=uda_list,
        marshal=True,
    )

    legacy_matching = _bool_option('general', 'legacy_matching', 'True')

    issue_updates = {
        'new': [],
        'existing': [],
        'changed': [],
        'closed': get_managed_task_uuids(tw, key_list, legacy_matching),
    }

    for issue in issue_generator:
        if isinstance(issue, tuple) and issue[0] == ABORT_PROCESSING:
            raise RuntimeError(issue[1])
        try:
            existing_uuid = find_local_uuid(
                tw, key_list, issue, legacy_matching=legacy_matching
            )
            issue_dict = dict(issue)
            _, task = tw.get_task(uuid=existing_uuid)

            # Drop static fields from the upstream issue.  We don't want to
            # overwrite local changes to fields we declare static.
            for field in static_fields:
                del issue_dict[field]

            # Merge annotations & tags from online into our task object
            merge_left('annotations', task, issue_dict, hamming=True)
            merge_left('tags', task, issue_dict)

            issue_dict.pop('annotations', None)
            issue_dict.pop('tags', None)

            task.update(issue_dict)

            if task.get_changes(keep=True):
                issue_updates['changed'].append(task)
            else:
                issue_updates['existing'].append(task)

            if existing_uuid in issue_updates['closed']:
                issue_updates['closed'].remove(existing_uuid)

        except MultipleMatches as e:
            log.name('db').error("Multiple matches: {0}", six.text_type(e))
            log.name('db').trace(e)
        except NotFound:
            issue_updates['new'].append(dict(issue))

    # Add new issues
    log.name('db').info("Adding {0} tasks", len(issue_updates['new']))
    for issue in issue_updates['new']:
        log.name('db').info(
            "Adding task {0}",
            issue['description'].encode("utf-8")
        )
        if notify:
            send_notification(issue, 'Created', conf)

        try:
            tw.task_add(**issue)
        except TaskwarriorError as e:
            log.name('db').trace(e)

    log.name('db').info("Updating {0} tasks", len(issue_updates['changed']))
    for issue in issue_updates['changed']:
        changes = '; '.join([
            '{field}: {f} -> {t}'.format(
                field=field,
                f=repr(ch[0]),
                t=repr(ch[1])
            )
            for field, ch in six.iteritems(issue.get_changes(keep=True))
        ])
        log.name('db').info(
            "Updating task {0}; {1}",
            issue['description'].encode("utf-8"),
            changes,
        )
        try:
            tw.task_update(issue)
        except TaskwarriorError as e:
            log.name('db').trace(e)

    log.name('db').info("Closing {0} tasks", len(issue_updates['closed']))
    for issue in issue_updates['closed']:
        _, task_info = tw.get_task(uuid=issue)
        log.name('db').info(
            "Completing task {0} {1}",
            task_info['uuid'],
            task_info['description'],
        )
        if notify:
            send_notification(task_info, 'Completed', conf)

        try:
            tw.task_done(uuid=issue)
        except TaskwarriorError as e:
            log.name('db').trace(e)

    # Send notifications
    if notify:
        send_notification(
            dict(
                description="New: %d, Changed: %d, Completed: %d" % (
                    len(issue_updates['new']),
                    len(issue_updates['changed']),
                    len(issue_updates['closed'])
                )
            ),
            'bw_finished',
            conf,
        )


def build_key_list(targets):
    from bugwarrior.services import SERVICES

    keys = {}
    for target in targets:
        keys[target] = SERVICES[target].ISSUE_CLASS.UNIQUE_KEY
    return keys


def build_uda_config_overrides(targets):
    """ Returns a list of UDAs defined by given targets

    For all targets in `targets`, build a dictionary of configuration overrides
    representing the UDAs defined by the passed-in services (`targets`).

    Given a hypothetical situation in which you have two services, the first
    of which defining a UDA named 'serviceAid' ("Service A ID", string) and
    a second service defining two UDAs named 'serviceBproject'
    ("Service B Project", string) and 'serviceBnumber'
    ("Service B Number", numeric), this would return the following structure::

        {
            'uda': {
                'serviceAid': {
                    'label': 'Service A ID',
                    'type': 'string',
                },
                'serviceBproject': {
                    'label': 'Service B Project',
                    'type': 'string',
                },
                'serviceBnumber': {
                    'label': 'Service B Number',
                    'type': 'numeric',
                }
            }
        }

    """

    from bugwarrior.services import SERVICES

    targets_udas = {}
    for target in targets:
        targets_udas.update(SERVICES[target].ISSUE_CLASS.UDAS)
    return {
        'uda': targets_udas
    }


def convert_override_args_to_taskrc_settings(config, prefix=''):
    args = []
    for k, v in six.iteritems(config):
        if isinstance(v, dict):
            args.extend(
                convert_override_args_to_taskrc_settings(
                    v,
                    prefix='.'.join([
                        prefix,
                        k,
                    ]) if prefix else k
                )
            )
        else:
            v = six.text_type(v)
            left = (prefix + '.' if prefix else '') + k
            args.append('='.join([left, v]))
    return args

########NEW FILE########
__FILENAME__ = notifications
import datetime
import os
import urllib

from bugwarrior.config import asbool


cache_dir = os.path.expanduser("~/.cache/bugwarrior")
logo_path = cache_dir + "/logo.png"
logo_url = "https://upload.wikimedia.org/wikipedia/" + \
    "en/5/59/Taskwarrior_logo.png"


def _cache_logo():
    if os.path.exists(logo_path):
        return

    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)

    urllib.urlretrieve(logo_url, logo_path)


def _get_metadata(issue):
    due = ''
    tags = ''
    priority = ''
    metadata = ''
    project = ''
    if 'project' in issue:
        project = "Project: " + issue['project']
    # if 'due' in issue:
    #     due = "Due: " + datetime.datetime.fromtimestamp(
    #         int(issue['due'])).strftime('%Y-%m-%d')
    if 'tags' in issue:
        tags = "Tags: " + ', '.join(issue['tags'])
    if 'priority' in issue:
        priority = "Priority: " + issue['priority']
    if project != '':
        metadata += "\n" + project
    if priority != '':
        metadata += "\n" + priority
    if due != '':
        metadata += "\n" + due
    if tags != '':
        metadata += "\n" + tags
    return metadata


def send_notification(issue, op, conf):
    notify_backend = conf.get('notifications', 'backend')

    # Notifications for growlnotify on Mac OS X
    if notify_backend == 'growlnotify':
        import gntp.notifier
        growl = gntp.notifier.GrowlNotifier(
            applicationName="Bugwarrior",
            notifications=["New Updates", "New Messages"],
            defaultNotifications=["New Messages"],
        )
        growl.register()
        if op == 'bw_finished':
            growl.notify(
                noteType="New Messages",
                title="Bugwarrior",
                description="Finished querying for new issues.\n%s" %
                issue['description'],
                sticky=asbool(conf.get(
                    'notifications', 'finished_querying_sticky', 'True')),
                icon="https://upload.wikimedia.org/wikipedia/"
                "en/5/59/Taskwarrior_logo.png",
                priority=1,
            )
            return
        message = "%s task: %s" % (op, issue['description'].encode("utf-8"))
        metadata = _get_metadata(issue)
        if metadata is not None:
            message += metadata
        growl.notify(
            noteType="New Messages",
            title="Bugwarrior",
            description=message,
            sticky=asbool(conf.get(
                'notifications', 'task_crud_sticky', 'True')),
            icon="https://upload.wikimedia.org/wikipedia/"
            "en/5/59/Taskwarrior_logo.png",
            priority=1,
        )
        return
    elif notify_backend == 'pynotify':
        _cache_logo()

        import pynotify
        pynotify.init("bugwarrior")

        if op == 'bw finished':
            message = "Finished querying for new issues.\n%s" %\
                issue['description']
        else:
            message = "%s task: %s" % (
                op, issue['description'].encode("utf-8"))
            metadata = _get_metadata(issue)
            if metadata is not None:
                message += metadata

        pynotify.Notification("Bugwarrior", message, logo_path).show()
    elif notify_backend == 'gobject':
        _cache_logo()

        from gi.repository import Notify
        Notify.init("bugwarrior")

        if op == 'bw finished':
            message = "Finished querying for new issues.\n%s" %\
                issue['description']
        else:
            message = "%s task: %s" % (
                op, issue['description'].encode("utf-8"))
            metadata = _get_metadata(issue)
            if metadata is not None:
                message += metadata

        Notify.Notification.new("Bugwarrior", message, logo_path).show()

########NEW FILE########
__FILENAME__ = activecollab
import re

import pypandoc
from twiggy import log
from pyac.library import activeCollab
from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die


class ActiveCollabClient(object):
    def __init__(self, url, key, user_id):
        self.url = url
        self.key = key
        self.user_id = int(user_id)
        self.activecollabtivecollab = activeCollab(
            key=key,
            url=url,
            user_id=user_id
        )


class ActiveCollabIssue(Issue):
    BODY = 'acbody'
    NAME = 'acname'
    PERMALINK = 'acpermalink'
    TASK_ID = 'actaskid'
    FOREIGN_ID = 'acid'
    PROJECT_ID = 'acprojectid'
    PROJECT_NAME = 'acprojectname'
    TYPE = 'actype'
    CREATED_ON = 'accreatedon'
    CREATED_BY_NAME = 'accreatedbyname'
    ESTIMATED_TIME = 'acestimatedtime'
    TRACKED_TIME = 'actrackedtime'
    MILESTONE = 'acmilestone'
    LABEL = 'aclabel'

    UDAS = {
        BODY: {
            'type': 'string',
            'label': 'ActiveCollab Body'
        },
        NAME: {
            'type': 'string',
            'label': 'ActiveCollab Name'
        },
        PERMALINK: {
            'type': 'string',
            'label': 'ActiveCollab Permalink'
        },
        TASK_ID: {
            'type': 'numeric',
            'label': 'ActiveCollab Task ID'
        },
        FOREIGN_ID: {
            'type': 'numeric',
            'label': 'ActiveCollab ID',
        },
        PROJECT_ID: {
            'type': 'numeric',
            'label': 'ActiveCollab Project ID'
        },
        PROJECT_NAME: {
            'type': 'string',
            'label': 'ActiveCollab Project Name'
        },
        TYPE: {
            'type': 'string',
            'label': 'ActiveCollab Task Type'
        },
        CREATED_ON: {
            'type': 'date',
            'label': 'ActiveCollab Created On'
        },
        CREATED_BY_NAME: {
            'type': 'string',
            'label': 'ActiveCollab Created By'
        },
        ESTIMATED_TIME: {
            'type': 'numeric',
            'label': 'ActiveCollab Estimated Time'
        },
        TRACKED_TIME: {
            'type': 'numeric',
            'label': 'ActiveCollab Tracked Time'
        },
        MILESTONE: {
            'type': 'string',
            'label': 'ActiveCollab Milestone'
        },
        LABEL: {
            'type': 'string',
            'label': 'ActiveCollab Label'
        }
    }
    UNIQUE_KEY = (FOREIGN_ID, )

    def to_taskwarrior(self):
        record = {
            'project': re.sub(r'\W+', '-', self.record['project']).lower(),
            'priority': self.get_priority(),
            'annotations': self.extra.get('annotations', []),
            self.NAME: self.record.get('name', ''),
            self.BODY: pypandoc.convert(self.record.get('body'),
                                        'md', format='html').rstrip(),
            self.PERMALINK: self.record['permalink'],
            self.TASK_ID: int(self.record.get('task_id')),
            self.PROJECT_NAME: self.record['project'],
            self.PROJECT_ID: int(self.record['project_id']),
            self.FOREIGN_ID: int(self.record['id']),
            self.TYPE: self.record.get('type', 'subtask').lower(),
            self.CREATED_BY_NAME: self.record['created_by_name'],
            self.MILESTONE: self.record['milestone'],
            self.ESTIMATED_TIME: self.record.get('estimated_time', 0),
            self.TRACKED_TIME: self.record.get('tracked_time', 0),
            self.LABEL: self.record.get('label'),
        }

        if self.TYPE == 'subtask':
            # Store the parent task ID for subtasks
            record['actaskid'] = int(self.record['task_id'])

        if isinstance(self.record.get('due_on'), dict):
            record['due'] = self.parse_date(
                self.record.get('due_on')['formatted_date']
            )

        if isinstance(self.record.get('created_on'), dict):
            record[self.CREATED_ON] = self.parse_date(
                self.record.get('created_on')['formatted_date']
            )
        return record

    def get_annotations(self):
        return self.extra.get('annotations', [])

    def get_priority(self):
        value = self.record.get('priority')
        if value > 0:
            return 'H'
        elif value < 0:
            return 'L'
        else:
            return 'M'

    def get_default_description(self):
        return self.build_default_description(
            title=(
                self.record.get('name')
                if self.record.get('name')
                else self.record.get('body')
            ),
            url=self.get_processed_url(self.record['permalink']),
            number=self.record['id'],
            cls=self.record.get('type', 'subtask').lower(),
        )


class ActiveCollabService(IssueService):
    ISSUE_CLASS = ActiveCollabIssue
    CONFIG_PREFIX = 'activecollab'

    def __init__(self, *args, **kw):
        super(ActiveCollabService, self).__init__(*args, **kw)

        self.url = self.config_get('url').rstrip('/')
        self.key = self.config_get('key')
        self.user_id = int(self.config_get('user_id'))
        self.client = ActiveCollabClient(
            self.url, self.key, self.user_id
        )
        self.activecollab = activeCollab(url=self.url, key=self.key,
                                         user_id=self.user_id)

    @classmethod
    def validate_config(cls, config, target):
        for k in (
            'activecollab.url', 'activecollab.key', 'activecollab.user_id'
        ):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def _comments(self, issue):
        comments = self.activecollab.get_comments(
            issue['project_id'],
            issue['task_id']
        )
        comments_formatted = []
        if comments is not None:
            for comment in comments:
                comments_formatted.append(
                    dict(user=comment['created_by']['display_name'],
                         body=comment['body']))
        return comments_formatted

    def get_owner(self, issue):
        if issue['assignee_id']:
            return issue['assignee_id']

    def annotations(self, issue):
        if 'type' not in issue:
            # Subtask
            return []
        comments = self._comments(issue)
        if comments is None:
            return []
        return self.build_annotations(
            (
                c['user'],
                pypandoc.convert(c['body'], 'md', format='html').rstrip()
            ) for c in comments
        )

    def issues(self):
        data = self.activecollab.get_my_tasks()
        label_data = self.activecollab.get_assignment_labels()
        labels = dict()
        for item in label_data:
            labels[item['id']] = re.sub(r'\W+', '_', item['name'])
        task_count = 0
        issues = []
        for key, record in data.iteritems():
            for task_id, task in record['assignments'].iteritems():
                task_count = task_count + 1
                # Add tasks
                if task['assignee_id'] == self.user_id:
                    task['label'] = labels.get(task['label_id'])
                    issues.append(task)
                if 'subtasks' in task:
                    for subtask_id, subtask in task['subtasks'].iteritems():
                        # Add subtasks
                        task_count = task_count + 1
                        if subtask['assignee_id'] is self.user_id:
                            # Add some data from the parent task
                            subtask['label'] = labels.get(subtask['label_id'])
                            subtask['project_id'] = task['project_id']
                            subtask['project'] = task['project']
                            subtask['task_id'] = task['task_id']
                            subtask['milestone'] = task['milestone']
                            issues.append(subtask)
        log.name(self.target).debug(" Found {0} total", task_count)
        log.name(self.target).debug(" Pruned down to {0}", len(issues))
        for issue in issues:
            extra = {
                'annotations': self.annotations(issue)
            }
            yield self.get_issue_for_record(issue, extra)

########NEW FILE########
__FILENAME__ = activecollab2
import itertools
import json
import time
import urllib2

import six
from twiggy import log

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die


class ActiveCollab2Client(object):
    def __init__(self, url, key, user_id, projects):
        self.url = url
        self.key = key
        self.user_id = user_id
        self.projects = projects

    def get_task_dict(self, project, key, task):
        assigned_task = {
            'project': project
        }
        if task[u'type'] == 'Ticket':
            # Load Ticket data
            # @todo Implement threading here.
            ticket_data = self.call_api(
                "/projects/" + six.text_type(task[u'project_id']) +
                "/tickets/" + six.text_type(task[u'ticket_id']))
            assignees = ticket_data[u'assignees']

            for k, v in enumerate(assignees):
                if (
                    (v[u'is_owner'] is True)
                    and (v[u'user_id'] == int(self.user_id))
                ):
                    assigned_task.update(ticket_data)
                    return assigned_task
        elif task[u'type'] == 'Task':
            # Load Task data
            assigned_task.update(task)
            return assigned_task

    def get_issue_generator(self, user_id, project_id, project_name):
        """
        Approach:

        1. Get user ID from .bugwarriorrc file
        2. Get list of tickets from /user-tasks for a given project
        3. For each ticket/task returned from #2, get ticket/task info and
           check if logged-in user is primary (look at `is_owner` and
           `user_id`)
        """

        user_tasks_data = self.call_api(
            "/projects/" + six.text_type(project_id) + "/user-tasks")

        for key, task in enumerate(user_tasks_data):

            assigned_task = self.get_task_dict(project_id, key, task)

            if assigned_task:
                log.name(self.target).debug(
                    " Adding '" + assigned_task['description'] +
                    "' to task list.")
                yield assigned_task

    def call_api(self, uri, get=None):
        url = self.url.rstrip("/") + "?token=" + self.key + \
            "&path_info=" + uri + "&format=json"
        req = urllib2.Request(url)
        res = urllib2.urlopen(req)

        return json.loads(res.read())


class ActiveCollab2Issue(Issue):
    BODY = 'ac2body'
    NAME = 'ac2name'
    PERMALINK = 'ac2permalink'
    TICKET_ID = 'ac2ticketid'
    PROJECT_ID = 'ac2projectid'
    TYPE = 'ac2type'
    CREATED_ON = 'ac2createdon'
    CREATED_BY_ID = 'ac2createdbyid'

    UDAS = {
        BODY: {
            'type': 'string',
            'label': 'ActiveCollab2 Body'
        },
        NAME: {
            'type': 'string',
            'label': 'ActiveCollab2 Name'
        },
        PERMALINK: {
            'type': 'string',
            'label': 'ActiveCollab2 Permalink'
        },
        TICKET_ID: {
            'type': 'string',
            'label': 'ActiveCollab2 Ticket ID'
        },
        PROJECT_ID: {
            'type': 'string',
            'label': 'ActiveCollab2 Project ID'
        },
        TYPE: {
            'type': 'string',
            'label': 'ActiveCollab2 Task Type'
        },
        CREATED_ON: {
            'type': 'date',
            'label': 'ActiveCollab2 Created On'
        },
        CREATED_BY_ID: {
            'type': 'string',
            'label': 'ActiveCollab2 Created By'
        },
    }
    UNIQUE_KEY = (PERMALINK, )

    PRIORITY_MAP = {
        -2: 'L',
        -1: 'L',
        0: 'M',
        1: 'H',
        2: 'H',
    }

    def to_taskwarrior(self):
        record = {
            'project': self.record['project'],
            'priority': self.get_priority(),
            'due': self.parse_date(self.record.get('due_on')),

            self.PERMALINK: self.record['permalink'],
            self.TICKET_ID: self.record['ticket_id'],
            self.PROJECT_ID: self.record['project_id'],
            self.TYPE: self.record['type'],
            self.CREATED_ON: self.parse_date(self.record.get('created_on')),
            self.CREATED_BY_ID: self.record['created_by_id'],
            self.BODY: self.record.get('body'),
            self.NAME: self.record.get('name'),
        }
        return record

    def get_default_description(self):
        return self.build_default_description(
            title=(
                self.record['name']
                if self.record['name']
                else self.record['body']
            ),
            url=self.get_processed_url(self.record['permalink']),
            number=self.record['ticket_id'],
            cls=self.record['type'].lower(),
        )


class ActiveCollab2Service(IssueService):
    ISSUE_CLASS = ActiveCollab2Issue
    CONFIG_PREFIX = 'activecollab2'

    def __init__(self, *args, **kw):
        super(ActiveCollab2Service, self).__init__(*args, **kw)

        self.url = self.config_get('url').rstrip('/')
        self.key = self.config_get('key')
        self.user_id = self.config_get('user_id')
        projects_raw = self.config_get('projects')

        projects_list = projects_raw.split(',')
        projects = []
        for k, v in enumerate(projects_list):
            project_data = v.strip().split(":")
            project = dict([(project_data[0], project_data[1])])
            projects.append(project)

        self.projects = projects

        self.client = ActiveCollab2Client(
            self.url, self.key, self.user_id, self.projects
        )

    @classmethod
    def validate_config(cls, config, target):
        for k in (
            'activecollab2.url',
            'activecollab2.key',
            'activecollab2.projects',
            'activecollab2.user_id'
        ):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        super(ActiveCollab2Service, cls).validate_config(config, target)

    def issues(self):
        # Loop through each project
        start = time.time()
        issue_generators = []
        projects = self.projects
        for project in projects:
            for project_id, project_name in project.iteritems():
                log.name(self.target).debug(
                    " Getting tasks for #" + project_id +
                    " " + project_name + '"')
                issue_generators.append(
                    self.client.get_issue_generator(
                        self.user_id, project_id, project_name
                    )
                )

        log.name(self.target).debug(
            " Elapsed Time: %s" % (time.time() - start))

        for record in itertools.chain(*issue_generators):
            yield self.get_issue_for_record(record)

########NEW FILE########
__FILENAME__ = bitbucket
import requests
from twiggy import log

from bugwarrior.services import IssueService, Issue
from bugwarrior.config import die, get_service_password


class BitbucketIssue(Issue):
    TITLE = 'bitbuckettitle'
    URL = 'bitbucketurl'
    FOREIGN_ID = 'bitbucketid'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Bitbucket Title',
        },
        URL: {
            'type': 'string',
            'label': 'Bitbucket URL',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Bitbucket Issue ID',
        }
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'trivial': 'L',
        'minor': 'L',
        'major': 'M',
        'critical': 'H',
        'blocker': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'priority': self.get_priority(),
            'annotations': self.extra['annotations'],

            self.URL: self.extra['url'],
            self.FOREIGN_ID: self.record['local_id'],
            self.TITLE: self.record['title'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['local_id'],
            cls='issue'
        )


class BitbucketService(IssueService):
    ISSUE_CLASS = BitbucketIssue
    CONFIG_PREFIX = 'bitbucket'

    BASE_API = 'https://api.bitbucket.org/1.0'
    BASE_URL = 'http://bitbucket.org/'

    def __init__(self, *args, **kw):
        super(BitbucketService, self).__init__(*args, **kw)

        self.auth = None
        if self.config_get_default('login'):
            login = self.config_get('login')
            password = self.config_get_default('password')
            if not password or password.startswith('@oracle:'):
                username = self.config_get('username')
                service = "bitbucket://%s@bitbucket.org/%s" % (login, username)
                password = get_service_password(
                    service, login, oracle=password,
                    interactive=self.config.interactive)

            self.auth = (login, password)

    def get_data(self, url):
        response = requests.get(self.BASE_API + url, auth=self.auth)

        # And.. if we didn't get good results, just bail.
        if response.status_code != 200:
            raise IOError(
                "Non-200 status code %r; %r; %r" % (
                    response.status_code, url, response.text,
                )
            )
        if callable(response.json):
            # Newer python-requests
            return response.json()
        else:
            # Older python-requests
            return response.json

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'bitbucket.username'):
            die("[%s] has no 'username'" % target)

        IssueService.validate_config(config, target)

    def pull(self, tag):
        response = self.get_data('/repositories/%s/issues/' % tag)
        return [(tag, issue) for issue in response['issues']]

    def get_annotations(self, tag, issue):
        response = self.get_data(
            '/repositories/%s/issues/%i/comments' % (tag, issue['local_id'])
        )
        return self.build_annotations(
            (
                comment['author_info']['username'],
                comment['content'],
            ) for comment in response
        )

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('responsible', {}).get('username', None)

    def issues(self):
        user = self.config.get(self.target, 'bitbucket.username')
        response = self.get_data('/users/' + user + '/')
        repos = [
            repo.get('slug') for repo in response.get('repositories')
            if repo.get('has_issues')
        ]

        issues = sum([self.pull(user + "/" + repo) for repo in repos], [])
        log.name(self.target).debug(" Found {0} total.", len(issues))

        closed = ['resolved', 'duplicate', 'wontfix', 'invalid']
        not_resolved = lambda tup: tup[1]['status'] not in closed
        issues = filter(not_resolved, issues)
        issues = filter(self.include, issues)
        log.name(self.target).debug(" Pruned down to {0}", len(issues))

        for tag, issue in issues:
            extras = {
                'project': tag.split('/')[1],
                'url': self.BASE_URL + '/'.join(
                    issue['resource_uri'].split('/')[3:]
                ).replace('issues', 'issue'),
                'annotations': self.get_annotations(tag, issue)
            }
            yield self.get_issue_for_record(issue, extras)

########NEW FILE########
__FILENAME__ = bz
import bugzilla
from twiggy import log

import six

from bugwarrior.config import die, asbool, get_service_password
from bugwarrior.services import IssueService, Issue


class BugzillaIssue(Issue):
    URL = 'bugzillaurl'
    SUMMARY = 'bugzillasummary'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Bugzilla URL',
        },
        SUMMARY: {
            'type': 'string',
            'label': 'Bugzilla Summary',
        }
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'unspecified': 'M',
        'low': 'L',
        'medium': 'M',
        'high': 'H',
        'urgent': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.record['component'],
            'priority': self.get_priority(),
            'annotations': self.extra.get('annotations', []),

            self.URL: self.extra['url'],
            self.SUMMARY: self.record['summary'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['summary'],
            url=self.get_processed_url(self.extra['url']),
            number=self.record['id'],
            cls='issue',
        )


class BugzillaService(IssueService):
    ISSUE_CLASS = BugzillaIssue
    CONFIG_PREFIX = 'bugzilla'

    OPEN_STATUSES = [
        'NEW',
        'ASSIGNED',
        'NEEDINFO',
        'ON_DEV',
        'MODIFIED',
        'POST',
        'REOPENED',
        'ON_QA',
        'FAILS_QA',
        'PASSES_QA',
    ]
    COLUMN_LIST = [
        'id',
        'summary',
        'priority',
        'component',
        'longdescs',
    ]

    def __init__(self, *args, **kw):
        super(BugzillaService, self).__init__(*args, **kw)
        self.base_uri = self.config_get('base_uri')
        self.username = self.config_get('username')
        self.password = self.config_get('password')

        # So more modern bugzilla's require that we specify
        # query_format=advanced along with the xmlrpc request.
        # https://bugzilla.redhat.com/show_bug.cgi?id=825370
        # ...but older bugzilla's don't know anything about that argument.
        # Here we make it possible for the user to specify whether they want
        # to pass that argument or not.
        self.advanced = asbool(self.config_get_default('advanced', 'no'))

        if not self.password or self.password.startswith("@oracle:"):
            service = "bugzilla://%s@%s" % (self.username, self.base_uri)
            self.password = get_service_password(
                service, self.username, oracle=self.password,
                interactive=self.config.interactive
            )

        url = 'https://%s/xmlrpc.cgi' % self.base_uri
        self.bz = bugzilla.Bugzilla(url=url)
        self.bz.login(self.username, self.password)

    @classmethod
    def validate_config(cls, config, target):
        req = ['bugzilla.username', 'bugzilla.password', 'bugzilla.base_uri']
        for option in req:
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        super(BugzillaService, cls).validate_config(config, target)

    def get_owner(self, issue):
        # NotImplemented, but we should never get called since .include() isn't
        # used by this IssueService.
        raise NotImplementedError

    def annotations(self, tag, issue):
        if 'comments' in issue:
            comments = issue.get('comments', [])
            return self.build_annotations(
                (
                    c['author'].split('@')[0],
                    c['text'],
                ) for c in comments
            )
        else:
            # Backwards compatibility (old python-bugzilla/bugzilla instances)
            # This block handles a million different contingencies that have to
            # do with different version of python-bugzilla and different
            # version of bugzilla itself.  :(
            comments = issue.get('longdescs', [])

            def _parse_author(obj):
                if isinstance(obj, dict):
                    return obj['login_name'].split('@')[0]
                else:
                    return obj

            def _parse_body(obj):
                return obj.get('text', obj.get('body'))

            return self.build_annotations(
                (
                    _parse_author(c['author']),
                    _parse_body(c)
                ) for c in issue['longdescs']
            )

    def issues(self):
        email = self.username
        # TODO -- doing something with blockedby would be nice.

        query = dict(
            column_list=self.COLUMN_LIST,
            bug_status=self.OPEN_STATUSES,
            email1=email,
            emailreporter1=1,
            emailcc1=1,
            emailassigned_to1=1,
            emailqa_contact1=1,
            emailtype1="substring",
        )

        if self.advanced:
            # Required for new bugzilla
            # https://bugzilla.redhat.com/show_bug.cgi?id=825370
            query['query_format'] = 'advanced'

        bugs = self.bz.query(query)

        # Convert to dicts
        bugs = [
            dict(
                ((col, getattr(bug, col)) for col in self.COLUMN_LIST)
            ) for bug in bugs
        ]

        issues = [(self.target, bug) for bug in bugs]
        log.name(self.target).debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        base_url = "https://%s/show_bug.cgi?id=" % (self.base_uri)
        for tag, issue in issues:
            extra = {
                'url': base_url + six.text_type(issue['id']),
                'annotations': self.annotations(tag, issue),
            }
            yield self.get_issue_for_record(issue, extra)

########NEW FILE########
__FILENAME__ = github
import re
import six

from jinja2 import Template
from twiggy import log

from bugwarrior.config import asbool, die, get_service_password
from bugwarrior.services import IssueService, Issue

from . import githubutils


class GithubIssue(Issue):
    TITLE = 'githubtitle'
    BODY = 'githubbody'
    CREATED_AT = 'githubcreatedon'
    UPDATED_AT = 'githubupdatedat'
    MILESTONE = 'githubmilestone'
    URL = 'githuburl'
    TYPE = 'githubtype'
    NUMBER = 'githubnumber'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Github Title',
        },
        BODY: {
            'type': 'string',
            'label': 'Github Body',
        },
        CREATED_AT: {
            'type': 'date',
            'label': 'Github Created',
        },
        UPDATED_AT: {
            'type': 'date',
            'label': 'Github Updated',
        },
        MILESTONE: {
            'type': 'numeric',
            'label': 'Github Milestone',
        },
        URL: {
            'type': 'string',
            'label': 'Github URL',
        },
        TYPE: {
            'type': 'string',
            'label': 'Github Type',
        },
        NUMBER: {
            'type': 'numeric',
            'label': 'Github Issue/PR #',
        },
    }
    UNIQUE_KEY = (URL, TYPE,)

    def to_taskwarrior(self):
        milestone = self.record['milestone']
        if milestone:
            milestone = milestone['id']

        body = self.record['body']
        if body:
            body = body.replace('\r\n', '\n')

        return {
            'project': self.extra['project'],
            'priority': self.origin['default_priority'],
            'annotations': self.extra.get('annotations', []),
            'tags': self.get_tags(),

            self.URL: self.record['html_url'],
            self.TYPE: self.extra['type'],
            self.TITLE: self.record['title'],
            self.BODY: body,
            self.MILESTONE: milestone,
            self.NUMBER: self.record['number'],
            self.CREATED_AT: self.parse_date(self.record['created_at']),
            self.UPDATED_AT: self.parse_date(self.record['updated_at'])
        }

    def get_tags(self):
        tags = []

        if not self.origin['import_labels_as_tags']:
            return tags

        context = self.record.copy()
        label_template = Template(self.origin['label_template'])

        for label_dict in self.record.get('labels', []):
            context.update({
                'label': label_dict['name']
            })
            tags.append(
                label_template.render(context)
            )

        return tags

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.record['html_url']),
            number=self.record['number'],
            cls=self.extra['type'],
        )


class GithubService(IssueService):
    ISSUE_CLASS = GithubIssue
    CONFIG_PREFIX = 'github'

    def __init__(self, *args, **kw):
        super(GithubService, self).__init__(*args, **kw)

        login = self.config_get('login')
        password = self.config_get_default('password')
        if not password or password.startswith('@oracle:'):
            username = self.config_get('username')
            service = "github://%s@github.com/%s" % (login, username)
            password = get_service_password(
                service, login, oracle=password,
                interactive=self.config.interactive
            )
        self.auth = (login, password)

        self.exclude_repos = []
        if self.config_get_default('exclude_repos', None):
            self.exclude_repos = [
                item.strip() for item in
                self.config_get('exclude_repos').strip().split(',')
            ]

        self.include_repos = []
        if self.config_get_default('include_repos', None):
            self.include_repos = [
                item.strip() for item in
                self.config_get('include_repos').strip().split(',')
            ]

        self.import_labels_as_tags = self.config_get_default(
            'import_labels_as_tags', default=False, to_type=asbool
        )
        self.label_template = self.config_get_default(
            'label_template', default='{{label}}', to_type=six.text_type
        )

    def get_service_metadata(self):
        return {
            'import_labels_as_tags': self.import_labels_as_tags,
            'label_template': self.label_template,
        }

    def get_owned_repo_issues(self, tag):
        """ Grab all the issues """
        issues = {}
        for issue in githubutils.get_issues(*tag.split('/'), auth=self.auth):
            issues[issue['url']] = (tag, issue)
        return issues

    def get_directly_assigned_issues(self):
        project_matcher = re.compile(
            r'.*/repos/(?P<owner>[^/]+)/(?P<project>[^/]+)/.*'
        )
        issues = {}
        for issue in githubutils.get_directly_assigned_issues(auth=self.auth):
            match_dict = project_matcher.match(issue['url']).groupdict()
            issues[issue['url']] = (
                '{owner}/{project}'.format(
                    **match_dict
                ),
                issue
            )
        return issues

    def _comments(self, tag, number):
        user, repo = tag.split('/')
        return githubutils.get_comments(user, repo, number, auth=self.auth)

    def annotations(self, tag, issue):
        comments = self._comments(tag, issue['number'])
        return self.build_annotations(
            (
                c['user']['login'],
                c['body'],
            ) for c in comments
        )

    def _reqs(self, tag):
        """ Grab all the pull requests """
        return [
            (tag, i) for i in
            githubutils.get_pulls(*tag.split('/'), auth=self.auth)
        ]

    def get_owner(self, issue):
        if issue[1]['assignee']:
            return issue[1]['assignee']['login']

    def _filter_repos_base(self, repo):
        if self.exclude_repos:
            if repo['name'] in self.exclude_repos:
                return False

        if self.include_repos:
            if repo['name'] in self.include_repos:
                return True
            else:
                return False

        return True

    def filter_repos_for_prs(self, repo):
        if repo['forks'] < 1:
            return False
        else:
            return self._filter_repos_base(repo)

    def filter_repos_for_issues(self, repo):
        if not (repo['has_issues'] and repo['open_issues_count'] > 0):
            return False
        else:
            return self._filter_repos_base(repo)

    def issues(self):
        user = self.config.get(self.target, 'github.username')

        all_repos = githubutils.get_repos(username=user, auth=self.auth)
        assert(type(all_repos) == list)
        repos = filter(self.filter_repos_for_issues, all_repos)

        issues = {}
        for repo in repos:
            issues.update(
                self.get_owned_repo_issues(user + "/" + repo['name'])
            )
        issues.update(self.get_directly_assigned_issues())
        log.name(self.target).debug(" Found {0} total.", len(issues))
        issues = filter(self.include, issues.values())
        log.name(self.target).debug(" Pruned down to {0}", len(issues))

        # Next, get all the pull requests (and don't prune)
        repos = filter(self.filter_repos_for_prs, all_repos)
        requests = sum([self._reqs(user + "/" + r['name']) for r in repos], [])

        # For pull requests, github lists an 'issue' and a 'pull request' with
        # the same id and the same URL.  So, if we find any pull requests,
        # let's strip those out of the "issues" list so that we don't have
        # unnecessary duplicates.
        request_urls = [r[1]['html_url'] for r in requests]
        issues = [i for i in issues if not i[1]['html_url'] in request_urls]

        for tag, issue in issues:
            extra = {
                'project': tag.split('/')[1],
                'type': 'issue',
                'annotations': self.annotations(tag, issue)
            }
            yield self.get_issue_for_record(issue, extra)

        for tag, request in requests:
            extra = {
                'project': tag.split('/')[1],
                'type': 'pull_request',
                'annotations': self.annotations(tag, request)
            }
            yield self.get_issue_for_record(request, extra)

    @classmethod
    def validate_config(cls, config, target):
        if not config.has_option(target, 'github.login'):
            die("[%s] has no 'github.login'" % target)

        if not config.has_option(target, 'github.password'):
            die("[%s] has no 'github.password'" % target)

        if not config.has_option(target, 'github.username'):
            die("[%s] has no 'github.username'" % target)

        super(GithubService, cls).validate_config(config, target)

########NEW FILE########
__FILENAME__ = githubutils
""" Tools for querying github.

I tried using pygithub3, but it really sucks.
"""

import requests


def _link_field_to_dict(field):
    """ Utility for ripping apart github's Link header field.
    It's kind of ugly.
    """

    if not field:
        return dict()

    return dict([
        (
            part.split('; ')[1][5:-1],
            part.split('; ')[0][1:-1],
        ) for part in field.split(', ')
    ])


def get_repos(username, auth):
    """ username should be a string
    auth should be a tuple of username and password.

    item can be one of "repos" or "orgs"
    """

    tmpl = "https://api.github.com/users/{username}/repos?per_page=100"
    url = tmpl.format(username=username)
    return _getter(url, auth)


def get_issues(username, repo, auth):
    """ username and repo should be strings
    auth should be a tuple of username and password.
    """

    tmpl = "https://api.github.com/repos/{username}/{repo}/issues?per_page=100"
    url = tmpl.format(username=username, repo=repo)
    return _getter(url, auth)


def get_directly_assigned_issues(auth):
    """ Returns all issues assigned to authenticated user.

    This will return all issues assigned to the authenticated user
    regardless of whether the user owns the repositories in which the
    issues exist.

    """
    url = "https://api.github.com/user/issues?per_page=100"
    return _getter(url, auth)


def get_comments(username, repo, number, auth):
    tmpl = "https://api.github.com/repos/{username}/{repo}/issues/" + \
        "{number}/comments?per_page=100"
    url = tmpl.format(username=username, repo=repo, number=number)
    return _getter(url, auth)


def get_pulls(username, repo, auth):
    """ username and repo should be strings
    auth should be a tuple of username and password.
    """

    tmpl = "https://api.github.com/repos/{username}/{repo}/pulls?per_page=100"
    url = tmpl.format(username=username, repo=repo)
    return _getter(url, auth)


def _getter(url, auth):
    """ Pagination utility.  Obnoxious. """

    results = []
    link = dict(next=url)
    while 'next' in link:
        response = requests.get(link['next'], auth=auth)

        # And.. if we didn't get good results, just bail.
        if response.status_code != 200:
            raise IOError(
                "Non-200 status code %r; %r; %r" % (
                    response.status_code, url, response.json))

        if callable(response.json):
            # Newer python-requests
            results += response.json()
        else:
            # Older python-requests
            results += response.json

        link = _link_field_to_dict(response.headers.get('link', None))

    return results

if __name__ == '__main__':
    # Little test.
    import getpass
    username = raw_input("GitHub Username: ")
    password = getpass.getpass()

    results = get_all(username, (username, password))
    print len(results), "repos found."

########NEW FILE########
__FILENAME__ = jira
from __future__ import absolute_import

from jinja2 import Template
from jira.client import JIRA
import six

from bugwarrior.config import asbool, die, get_service_password
from bugwarrior.services import IssueService, Issue


class JiraIssue(Issue):
    SUMMARY = 'jirasummary'
    URL = 'jiraurl'
    FOREIGN_ID = 'jiraid'
    DESCRIPTION = 'jiradescription'

    UDAS = {
        SUMMARY: {
            'type': 'string',
            'label': 'Jira Summary'
        },
        URL: {
            'type': 'string',
            'label': 'Jira URL',
        },
        DESCRIPTION: {
            'type': 'string',
            'label': 'Jira Description',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Jira Issue ID'
        }
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'Trivial': 'L',
        'Minor': 'L',
        'Major': 'M',
        'Critical': 'H',
        'Blocker': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),
            'annotations': self.get_annotations(),
            'tags': self.get_tags(),

            self.URL: self.get_url(),
            self.FOREIGN_ID: self.record['key'],
            self.DESCRIPTION: self.record.get('fields', {}).get('description'),
            self.SUMMARY: self.get_summary(),
        }

    def get_tags(self):
        tags = []

        if not self.origin['import_labels_as_tags']:
            return tags

        context = self.record.copy()
        label_template = Template(self.origin['label_template'])

        for label in self.record.get('fields', {}).get('labels', []):
            context.update({
                'label': label
            })
            tags.append(
                label_template.render(context)
            )

        return tags

    def get_annotations(self):
        return self.extra.get('annotations', [])

    def get_project(self):
        return self.record['key'].rsplit('-', 1)[0]

    def get_number(self):
        return self.record['key'].rsplit('-', 1)[1]

    def get_url(self):
        return self.origin['url'] + '/browse/' + self.record['key']

    def get_summary(self):
        if self.extra.get('jira_version') == 4:
            return self.record['fields']['summary']['value']
        return self.record['fields']['summary']

    def get_priority(self):
        value = self.record['fields'].get('priority')
        if isinstance(value, dict):
            value = value.get('name')
        elif value:
            value = str(value)

        return self.PRIORITY_MAP.get(value, self.origin['default_priority'])

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_summary(),
            url=self.get_processed_url(self.get_url()),
            number=self.get_number(),
            cls='issue',
        )


class JiraService(IssueService):
    ISSUE_CLASS = JiraIssue
    CONFIG_PREFIX = 'jira'

    def __init__(self, *args, **kw):
        super(JiraService, self).__init__(*args, **kw)
        self.username = self.config_get('username')
        self.url = self.config_get('base_uri')
        password = self.config_get('password')
        if not password or password.startswith("@oracle:"):
            service = "jira://%s@%s" % (self.username, self.url)
            password = get_service_password(
                service, self.username,
                oracle=password,
                interactive=self.config.interactive
            )

        default_query = 'assignee=' + self.username + \
            ' AND status != closed and status != resolved'
        self.query = self.config_get_default('query', default_query)
        self.jira = JIRA(
            options={
                'server': self.config_get('base_uri'),
                'rest_api_version': 'latest',
            },
            basic_auth=(self.username, password)
        )
        self.import_labels_as_tags = self.config_get_default(
            'import_labels_as_tags', default=False, to_type=asbool
        )
        self.label_template = self.config_get_default(
            'label_template', default='{{label}}', to_type=six.text_type
        )

    def get_service_metadata(self):
        return {
            'url': self.url,
            'import_labels_as_tags': self.import_labels_as_tags,
            'label_template': self.label_template,
        }

    @classmethod
    def validate_config(cls, config, target):
        for option in ('jira.username', 'jira.password', 'jira.base_uri'):
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        IssueService.validate_config(config, target)

    def annotations(self, issue):
        comments = self.jira.comments(issue)

        if not comments:
            return []
        else:
            return self.build_annotations(
                (
                    comment.author.name,
                    comment.body
                ) for comment in comments
            )

    def issues(self):
        cases = self.jira.search_issues(self.query, maxResults=-1)

        jira_version = 5
        if self.config.has_option(self.target, 'jira.version'):
            jira_version = self.config.getint(self.target, 'jira.version')

        for case in cases:
            extra = {
                'jira_version': jira_version,
            }
            if jira_version > 4:
                extra.update({
                    'annotations': self.annotations(case.key)
                })
            yield self.get_issue_for_record(case.raw, extra)

########NEW FILE########
__FILENAME__ = mplan
from __future__ import absolute_import

import megaplan
from twiggy import log

from bugwarrior.config import die, get_service_password
from bugwarrior.services import IssueService, Issue


class MegaplanIssue(Issue):
    URL = 'megaplanurl'
    FOREIGN_ID = 'megaplanid'
    TITLE = 'megaplantitle'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Megaplan Title',
        },
        URL: {
            'type': 'string',
            'label': 'Megaplan URL',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Megaplan Issue ID'
        }
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),

            self.FOREIGN_ID: self.record['Id'],
            self.URL: self.get_issue_url(),
            self.TITLE: self.get_issue_title(),
        }

    def get_project(self):
        return self.origin['project_name']

    def get_default_description(self):
        return self.build_default_description(
            title=self.get_issue_title(),
            url=self.get_processed_url(self.get_issue_url()),
            number=self.record['Id'],
            cls='issue',
        )

    def get_issue_url(self):
        return "https://%s/task/%d/card/" % (
            self.origin['hostname'], self.record["Id"]
        )

    def get_issue_title(self):
        parts = self.record["Name"].split("|")
        return parts[-1].strip()

    def get_issue_id(self):
        if self.record["Id"] > 1000000:
            return self.record["Id"] - 1000000
        return self.record["Id"]


class MegaplanService(IssueService):
    ISSUE_CLASS = MegaplanIssue
    CONFIG_PREFIX = 'megaplan'

    def __init__(self, *args, **kw):
        super(MegaplanService, self).__init__(*args, **kw)

        self.hostname = self.config_get('hostname')
        _login = self.config_get('login')
        _password = self.config_get('password')
        if not _password or _password.startswith("@oracle:"):
            service = "megaplan://%s@%s" % (_login, self.hostname)
            _password = get_service_password(
                service, _login, oracle=_password,
                interactive=self.config.interactive
            )

        self.client = megaplan.Client(self.hostname)
        self.client.authenticate(_login, _password)

        self.project_name = self.config_get_default(
            'project_name', self.hostname
        )

    def get_service_metadata(self):
        return {
            'project_name': self.project_name,
            'hostname': self.hostname,
        }

    @classmethod
    def validate_config(cls, config, target):
        for k in ('megaplan.login', 'megaplan.password', 'megaplan.hostname'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def issues(self):
        issues = self.client.get_actual_tasks()
        log.name(self.target).debug(" Found {0} total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)

########NEW FILE########
__FILENAME__ = phab
import six
from twiggy import log

from bugwarrior.services import IssueService, Issue

# This comes from PyPI
import phabricator


class PhabricatorIssue(Issue):
    TITLE = 'phabricatortitle'
    URL = 'phabricatorurl'
    TYPE = 'phabricatortype'
    OBJECT_NAME = 'phabricatorid'

    UDAS = {
        TITLE: {
            'type': 'string',
            'label': 'Phabricator Title',
        },
        URL: {
            'type': 'string',
            'label': 'Phabricator URL',
        },
        TYPE: {
            'type': 'string',
            'label': 'Phabricator Type',
        },
        OBJECT_NAME: {
            'type': 'string',
            'label': 'Phabricator Object',
        },
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'priority': self.origin['default_priority'],
            'annotations': self.extra.get('annotations', []),

            self.URL: self.record['uri'],
            self.TYPE: self.extra['type'],
            self.TITLE: self.record['title'],
            self.OBJECT_NAME: self.record['uri'].split('/')[-1],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.record['uri']),
            number=self.record['uri'].split('/')[-1],
            cls=self.extra['type'],
        )


class PhabricatorService(IssueService):
    ISSUE_CLASS = PhabricatorIssue
    CONFIG_PREFIX = 'phabricator'

    def __init__(self, *args, **kw):
        super(PhabricatorService, self).__init__(*args, **kw)
        # These reads in login credentials from ~/.arcrc
        self.api = phabricator.Phabricator()

    def issues(self):

        # TODO -- get a list of these from the api
        projects = {}

        issues = self.api.maniphest.query(status='status-open')
        issues = list(issues.iteritems())

        log.name(self.target).info("Found %i issues" % len(issues))

        for phid, issue in issues:
            project = self.target  # a sensible default
            try:
                project = projects.get(issue['projectPHIDs'][0], project)
            except IndexError:
                pass

            extra = {
                'project': project,
                'type': 'issue',
                #'annotations': self.annotations(phid, issue)
            }
            yield self.get_issue_for_record(issue, extra)

        diffs = self.api.differential.query(status='status-open')
        diffs = list(diffs)

        log.name(self.target).info("Found %i differentials" % len(diffs))

        for diff in list(diffs):
            project = self.target  # a sensible default
            try:
                project = projects.get(issue['projectPHIDs'][0], project)
            except IndexError:
                pass

            extra = {
                'project': project,
                'type': 'pull_request',
                #'annotations': self.annotations(phid, issue)
            }
            yield self.get_issue_for_record(diff, extra)

########NEW FILE########
__FILENAME__ = redmine
import urllib
import urllib2
import json

import six
from twiggy import log

from bugwarrior.config import die
from bugwarrior.services import Issue, IssueService


class RedMineClient(object):
    def __init__(self, url, key):
        self.url = url
        self.key = key

    def find_issues(self, user_id=None):
        args = {}
        if user_id is not None:
            args["assigned_to_id"] = user_id
        return self.call_api("/issues.json", args)["issues"]

    def call_api(self, uri, get=None):
        url = self.url.rstrip("/") + uri

        if get:
            url += "?" + urllib.urlencode(get)

        req = urllib2.Request(url)
        req.add_header("X-Redmine-API-Key", self.key)

        res = urllib2.urlopen(req)

        return json.loads(res.read())


class RedMineIssue(Issue):
    URL = 'redmineurl'
    SUBJECT = 'redminesubject'
    ID = 'redmineid'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Redmine URL',
        },
        SUBJECT: {
            'type': 'string',
            'label': 'Redmine Subject',
        },
        ID: {
            'type': 'string',
            'label': 'Redmine ID',
        },
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.get_project_name(),
            'priority': self.get_priority(),

            self.URL: self.get_issue_url(),
            self.SUBJECT: self.record['subject'],
            self.ID: self.record['id']
        }

    def get_issue_url(self):
        return (
            self.origin['url'] + "/issues/" + six.text_type(self.record["id"])
        )

    def get_project_name(self):
        if self.origin['project_name']:
            return self.origin['project_name']
        return self.record["project"]["name"]

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['subject'],
            url=self.get_processed_url(self.record['url']),
            number=self.record['id'],
            cls='issue',
        )


class RedMineService(IssueService):
    ISSUE_CLASS = RedMineIssue
    CONFIG_PREFIX = 'redmine'

    def __init__(self, *args, **kw):
        super(RedMineService, self).__init__(*args, **kw)

        self.url = self.config_get('url').rstrip("/")
        self.key = self.config_get('key')
        self.user_id = self.config_get('user_id')

        self.client = RedMineClient(self.url, self.key)

        self.project_name = self.config_get_default('project_name')

    def get_service_metadata(self):
        return {
            'project_name': self.project_name,
            'url': self.url,
        }

    @classmethod
    def validate_config(cls, config, target):
        for k in ('redmine.url', 'redmine.key', 'redmine.user_id'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def issues(self):
        issues = self.client.find_issues(self.user_id)
        log.name(self.target).debug(" Found {0} total.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)

########NEW FILE########
__FILENAME__ = teamlab
import json
import urllib
import urllib2

import six
from twiggy import log

from bugwarrior.config import die, get_service_password
from bugwarrior.services import Issue, IssueService


class TeamLabClient(object):
    def __init__(self, hostname, verbose=False):
        self.hostname = hostname
        self.verbose = verbose
        self.token = None

    def authenticate(self, login, password):
        resp = self.call_api("/api/1.0/authentication.json", post={
            "userName": six.text_type(login),
            "password": six.text_type(password),
        })

        self.token = six.text_type(resp["token"])

    def get_task_list(self):
        resp = self.call_api("/api/1.0/project/task/@self.json")
        return resp

    def call_api(self, uri, post=None, get=None):
        uri = "http://" + self.hostname + uri

        if post is None:
            data = None
        else:
            data = urllib.urlencode(post)

        if get is not None:
            uri += "?" + urllib.urlencode(get)

        req = urllib2.Request(uri, data)
        if self.token is not None:
            req.add_header("Authorization", self.token)
        req.add_header("Accept", "application/json")

        res = urllib2.urlopen(req)
        if res.getcode() >= 400:
            raise Exception("Error accessing the API: %s" % res.read())

        response = res.read()

        return json.loads(response)["response"]


class TeamLabIssue(Issue):
    URL = 'teamlaburl'
    FOREIGN_ID = 'teamlabid'
    TITLE = 'teamlabtitle'
    PROJECTOWNER_ID = 'teamlabprojectownerid'

    UDAS = {
        URL: {
            'type': 'string',
            'label': 'Teamlab URL',
        },
        FOREIGN_ID: {
            'type': 'string',
            'label': 'Teamlab ID',
        },
        TITLE: {
            'type': 'string',
            'label': 'Teamlab Title',
        },
        PROJECTOWNER_ID: {
            'type': 'string',
            'label': 'Teamlab ProjectOwner ID',
        }
    }
    UNIQUE_KEY = (URL, )

    def to_taskwarrior(self):
        return {
            'project': self.get_project(),
            'priority': self.get_priority(),

            self.TITLE: self.record['title'],
            self.FOREIGN_ID: self.record['id'],
            self.URL: self.get_issue_url(),
            self.PROJECTOWNER_ID: self.record['projectOwner']['id'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['title'],
            url=self.get_processed_url(self.get_issue_url()),
            number=self.record['id'],
            cls='issue',
        )

    def get_project(self):
        return self.origin['project_name']

    def get_issue_url(self):
        return "http://%s/products/projects/tasks.aspx?prjID=%d&id=%d" % (
            self.origin['hostname'],
            self.record["projectOwner"]["id"],
            self.record["id"]
        )

    def get_priority(self):
        if self.record.get("priority") == 1:
            return "H"
        return self.origin['default_priority']


class TeamLabService(IssueService):
    ISSUE_CLASS = TeamLabIssue
    CONFIG_PREFIX = 'teamlab'

    def __init__(self, *args, **kw):
        super(TeamLabService, self).__init__(*args, **kw)

        self.hostname = self.config_get('hostname')
        _login = self.config_get('login')
        _password = self.config_get('password')
        if not _password or _password.startswith("@oracle:"):
            service = "teamlab://%s@%s" % (_login, self.hostname)
            _password = get_service_password(
                service, _login, oracle=_password,
                interactive=self.config.interactive
            )

        self.client = TeamLabClient(self.hostname)
        self.client.authenticate(_login, _password)

        self.project_name = self.config_get_default(
            'project_name', self.hostname
        )

    def get_service_metadata(self):
        return {
            'hostname': self.hostname,
            'project_name': self.project_name,
        }

    @classmethod
    def validate_config(cls, config, target):
        for k in ('teamlab.login', 'teamlab.password', 'teamlab.hostname'):
            if not config.has_option(target, k):
                die("[%s] has no '%s'" % (target, k))

        IssueService.validate_config(config, target)

    def issues(self):
        issues = self.client.get_task_list()
        log.name(self.target).debug(
            " Remote has {0} total issues.", len(issues))

        # Filter out closed tasks.
        issues = filter(lambda i: i["status"] == 1, issues)
        log.name(self.target).debug(
            " Remote has {0} active issues.", len(issues))

        for issue in issues:
            yield self.get_issue_for_record(issue)

########NEW FILE########
__FILENAME__ = trac
import offtrac
from twiggy import log

from bugwarrior.config import die, get_service_password
from bugwarrior.services import Issue, IssueService


class TracIssue(Issue):
    SUMMARY = 'tracsummary'
    URL = 'tracurl'
    NUMBER = 'tracnumber'

    UDAS = {
        SUMMARY: {
            'type': 'string',
            'label': 'Trac Summary',
        },
        URL: {
            'type': 'string',
            'label': 'Trac URL',
        },
        NUMBER: {
            'type': 'numeric',
            'label': 'Trac Number',
        },
    }
    UNIQUE_KEY = (URL, )

    PRIORITY_MAP = {
        'trivial': 'L',
        'minor': 'L',
        'major': 'M',
        'critical': 'H',
        'blocker': 'H',
    }

    def to_taskwarrior(self):
        return {
            'project': self.extra['project'],
            'priority': self.get_priority(),
            'annotations': self.extra['annotations'],

            self.URL: self.record['url'],
            self.SUMMARY: self.record['summary'],
            self.NUMBER: self.record['number'],
        }

    def get_default_description(self):
        return self.build_default_description(
            title=self.record['summary'],
            url=self.get_processed_url(self.record['url']),
            number=self.record['number'],
            cls='issue'
        )

    def get_priority(self):
        return self.PRIORITY_MAP.get(
            self.record.get('priority'),
            self.origin['default_priority']
        )


class TracService(IssueService):
    ISSUE_CLASS = TracIssue
    CONFIG_PREFIX = 'trac'

    def __init__(self, *args, **kw):
        super(TracService, self).__init__(*args, **kw)
        base_uri = self.config_get('base_uri')
        username = self.config_get('username')
        password = self.config_get('password')
        if not password or password.startswith('@oracle:'):
            service = "https://%s@%s/" % (username, base_uri)
            password = get_service_password(
                service, username, oracle=password,
                interactive=self.config.interactive
            )

        uri = 'https://%s:%s@%s/login/xmlrpc' % (username, password, base_uri)
        self.trac = offtrac.TracServer(uri)

    @classmethod
    def validate_config(cls, config, target):
        for option in ['trac.username', 'trac.password', 'trac.base_uri']:
            if not config.has_option(target, option):
                die("[%s] has no '%s'" % (target, option))

        IssueService.validate_config(config, target)

    def annotations(self, tag, issue):
        annotations = []
        changelog = self.trac.server.ticket.changeLog(issue['number'])
        for time, author, field, oldvalue, newvalue, permament in changelog:
            if field == 'comment':
                annotations.append((author, newvalue, ))

        return self.build_annotations(annotations)

    def get_owner(self, issue):
        tag, issue = issue
        return issue.get('owner', None) or None

    def issues(self):
        base_url = "https://" + self.config.get(self.target, 'trac.base_uri')
        tickets = self.trac.query_tickets('status!=closed&max=0')
        tickets = map(self.trac.get_ticket, tickets)
        issues = [(self.target, ticket[3]) for ticket in tickets]
        log.name(self.target).debug(" Found {0} total.", len(issues))

        # Build a url for each issue
        for i in range(len(issues)):
            issues[i][1]['url'] = "%s/ticket/%i" % (base_url, tickets[i][0])
            issues[i][1]['number'] = tickets[i][0]

        issues = filter(self.include, issues)
        log.name(self.target).debug(" Pruned down to {0}", len(issues))

        for project, issue in issues:
            extra = {
                'annotations': self.annotations(project, issue),
                'project': project,
            }
            yield self.get_issue_for_record(issue, extra)

########NEW FILE########
__FILENAME__ = generate_service_template
import inspect
import os
import sys

from jinja2 import Template

from bugwarrior.services import Issue


def make_table(grid):
    """ Make a RST-compatible table

    From http://stackoverflow.com/a/12539081

    """
    cell_width = 2 + max(
        reduce(
            lambda x, y: x+y, [[len(item) for item in row] for row in grid], []
        )
    )
    num_cols = len(grid[0])
    rst = table_div(num_cols, cell_width, 0)
    header_flag = 1
    for row in grid:
        rst = rst + '| ' + '| '.join(
            [normalize_cell(x, cell_width-1) for x in row]
        ) + '|\n'
        rst = rst + table_div(num_cols, cell_width, header_flag)
        header_flag = 0
    return rst


def table_div(num_cols, col_width, header_flag):
    if header_flag == 1:
        return num_cols*('+' + (col_width)*'=') + '+\n'
    else:
        return num_cols*('+' + (col_width)*'-') + '+\n'


def normalize_cell(string, length):
    return string + ((length - len(string)) * ' ')


def import_by_path(name):
    m = __import__(name)
    for n in name.split(".")[1:]:
        m = getattr(m, n)
    return m


def row_comparator(left_row, right_row):
    left = left_row[0]
    right = right_row[0]
    if left > right:
        return 1
    elif right > left or left == 'Field Name':
        return -1
    return 0


TYPE_NAME_MAP = {
    'date': 'Date & Time',
    'numeric': 'Numeric',
    'string': 'Text (string)',
    'duration': 'Duration'
}


if __name__ == '__main__':
    service = sys.argv[1]
    module = import_by_path(
        'bugwarrior.services.{service}'.format(service=service)
    )
    rows = []
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, Issue):
            for field_name, details in obj.UDAS.items():
                rows.append(
                    [
                        '``%s``' % field_name,
                        ' '.join(details['label'].split(' ')[1:]),
                        TYPE_NAME_MAP.get(
                            details['type'],
                            '``%s``' % details['type'],
                        ),
                    ]
                )

    rows = sorted(rows, cmp=row_comparator)
    rows.insert(0, ['Field Name', 'Description', 'Type'])

    filename = os.path.join(os.path.dirname(__file__), 'service_template.html')
    with open(filename) as template:
        rendered = Template(template.read()).render({
            'service_name_humane': service.title(),
            'service_name': service,
            'uda_table': make_table(rows)
        })

    print rendered

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bugwarrior documentation build configuration file, created by
# sphinx-quickstart on Wed Apr 16 15:09:22 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bugwarrior'
copyright = u'2014, Ralph Bean'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.8.0'
# The full version, including alpha/beta/rc tags.
release = '0.8.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Bugwarriordoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'Bugwarrior.tex', u'Bugwarrior Documentation',
   u'Ralph Bean', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bugwarrior', u'Bugwarrior Documentation',
     [u'Ralph Bean'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Bugwarrior', u'Bugwarrior Documentation',
   u'Ralph Bean', 'Bugwarrior', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = base
import mock
import unittest2


class ServiceTest(unittest2.TestCase):
    GENERAL_CONFIG = {
        'annotation_length': 100,
        'description_length': 100,
    }
    SERVICE_CONFIG = {
    }

    def get_mock_service(
        self, service, section='unspecified',
        config_overrides=None, general_overrides=None
    ):
        options = {
            'general': self.GENERAL_CONFIG.copy(),
            section: self.SERVICE_CONFIG.copy(),
        }
        if config_overrides:
            options[section].update(config_overrides)
        if general_overrides:
            options['general'].update(general_overrides)

        def has_option(section, name):
            try:
                return options[section][name]
            except KeyError:
                return False

        def get_option(section, name):
            return options[section][name]

        def get_int(section, name):
            return int(get_option(section, name))

        config = mock.Mock()
        config.has_option = mock.Mock(side_effect=has_option)
        config.get = mock.Mock(side_effect=get_option)
        config.getint = mock.Mock(side_effect=get_int)

        service = service(config, section)

        return service

########NEW FILE########
__FILENAME__ = test_activecollab
import datetime
import mock
import pypandoc
import pytz

from bugwarrior.services.activecollab import (
    ActiveCollabService
)

from .base import ServiceTest


class TestActiveCollabIssue(ServiceTest):
    SERVICE_CONFIG = {
        'activecollab.url': 'hello',
        'activecollab.key': 'howdy',
        'activecollab.user_id': '2',
        'activecollab.projects': '1:one, 2:two'
    }

    def setUp(self):
        self.maxDiff = None
        with mock.patch(
            'pyac.library.activeCollab.call_api'
        ):
            self.service = self.get_mock_service(ActiveCollabService)

    def test_to_taskwarrior(self):
        arbitrary_due_on = (
            datetime.datetime.now() - datetime.timedelta(hours=1)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_created_on = (
            datetime.datetime.now() - datetime.timedelta(hours=2)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_extra = {
            'annotations': ['an annotation'],
        }
        arbitrary_issue = {
            'priority': 0,
            'project': 'something',
            'due_on': {
                'formatted_date': arbitrary_due_on.isoformat(),
            },
            'permalink': 'http://wherever/',
            'task_id': 10,
            'project_name': 'something',
            'project_id': 10,
            'id': 30,
            'type': 'issue',
            'created_on': {
                'formatted_date': arbitrary_created_on.isoformat(),
            },
            'created_by_name': 'Tester',
            'body': pypandoc.convert('<p>Ticket Body</p>', 'md',
                                     format='html').rstrip(),
            'name': 'Anonymous',
            'milestone': 'Sprint 1',
            'estimated_time': 1,
            'tracked_time': 10,
            'label': 'ON_HOLD',
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue, arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_issue['project'],
            'due': arbitrary_due_on,
            'priority': 'M',
            'annotations': arbitrary_extra['annotations'],
            issue.PERMALINK: arbitrary_issue['permalink'],
            issue.PROJECT_ID: arbitrary_issue['project_id'],
            issue.PROJECT_NAME: arbitrary_issue['project_name'],
            issue.TYPE: arbitrary_issue['type'],
            issue.CREATED_ON: arbitrary_created_on,
            issue.CREATED_BY_NAME: arbitrary_issue['created_by_name'],
            issue.BODY: arbitrary_issue['body'],
            issue.NAME: arbitrary_issue['name'],
            issue.FOREIGN_ID: arbitrary_issue['id'],
            issue.TASK_ID: arbitrary_issue['task_id'],
            issue.ESTIMATED_TIME: arbitrary_issue['estimated_time'],
            issue.TRACKED_TIME: arbitrary_issue['tracked_time'],
            issue.MILESTONE: arbitrary_issue['milestone'],
            issue.LABEL: arbitrary_issue['label'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_activecollab2
import datetime

import pytz

from bugwarrior.services.activecollab2 import ActiveCollab2Service

from .base import ServiceTest


class TestActiveCollab2Issue(ServiceTest):
    SERVICE_CONFIG = {
        'activecollab2.url': 'hello',
        'activecollab2.key': 'howdy',
        'activecollab2.user_id': 'hola',
        'activecollab2.projects': '1:one, 2:two'
    }

    def setUp(self):
        self.service = self.get_mock_service(ActiveCollab2Service)

    def test_to_taskwarrior(self):
        arbitrary_due_on = (
            datetime.datetime.now() - datetime.timedelta(hours=1)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_created_on = (
            datetime.datetime.now() - datetime.timedelta(hours=2)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_issue = {
            'project': 'something',
            'priority': 2,
            'due_on': arbitrary_due_on.isoformat(),
            'permalink': 'http://wherever/',
            'ticket_id': 10,
            'project_id': 20,
            'type': 'issue',
            'created_on': arbitrary_created_on.isoformat(),
            'created_by_id': '10',
            'body': 'Ticket Body',
            'name': 'Anonymous',
        }

        issue = self.service.get_issue_for_record(arbitrary_issue)

        expected_output = {
            'project': arbitrary_issue['project'],
            'priority': issue.PRIORITY_MAP[arbitrary_issue['priority']],
            'due': arbitrary_due_on,

            issue.PERMALINK: arbitrary_issue['permalink'],
            issue.TICKET_ID: arbitrary_issue['ticket_id'],
            issue.PROJECT_ID: arbitrary_issue['project_id'],
            issue.TYPE: arbitrary_issue['type'],
            issue.CREATED_ON: arbitrary_created_on,
            issue.CREATED_BY_ID: arbitrary_issue['created_by_id'],
            issue.BODY: arbitrary_issue['body'],
            issue.NAME: arbitrary_issue['name'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_bitbucket
from bugwarrior.services.bitbucket import BitbucketService

from .base import ServiceTest


class TestBitbucketIssue(ServiceTest):
    SERVICE_CONFIG = {
        'bitbucket.login': 'something',
        'bitbucket.password': 'something else',
    }

    def setUp(self):
        self.service = self.get_mock_service(BitbucketService)

    def test_to_taskwarrior(self):
        arbitrary_issue = {
            'priority': 'trivial',
            'local_id': '100',
            'title': 'Some Title',
        }
        arbitrary_extra = {
            'url': 'http://hello-there.com/',
            'project': 'Something',
            'annotations': [
                'One',
            ]
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue, arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_extra['project'],
            'priority': issue.PRIORITY_MAP[arbitrary_issue['priority']],
            'annotations': arbitrary_extra['annotations'],

            issue.URL: arbitrary_extra['url'],
            issue.FOREIGN_ID: arbitrary_issue['local_id'],
            issue.TITLE: arbitrary_issue['title'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_bugzilla
import mock

from bugwarrior.services.bz import BugzillaService

from .base import ServiceTest


class TestBugzillaService(ServiceTest):
    SERVICE_CONFIG = {
        'bugzilla.base_uri': 'http://one.com/',
        'bugzilla.username': 'hello',
        'bugzilla.password': 'there',
    }

    def setUp(self):
        with mock.patch('bugzilla.Bugzilla'):
            self.service = self.get_mock_service(BugzillaService)

    def test_to_taskwarrior(self):
        arbitrary_record = {
            'component': 'Something',
            'priority': 'urgent',
            'summary': 'This is the issue summary'
        }
        arbitrary_extra = {
            'url': 'http://path/to/issue/',
            'annotations': [
                'Two',
            ],
        }

        issue = self.service.get_issue_for_record(
            arbitrary_record,
            arbitrary_extra,
        )

        expected_output = {
            'project': arbitrary_record['component'],
            'priority': issue.PRIORITY_MAP[arbitrary_record['priority']],
            'annotations': arbitrary_extra['annotations'],

            issue.URL: arbitrary_extra['url'],
            issue.SUMMARY: arbitrary_record['summary'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_db
import unittest2

import taskw.task
from bugwarrior.db import merge_left


class DBTest(unittest2.TestCase):
    def setUp(self):
        self.issue_dict = {'annotations': ['testing']}

    def test_merge_left_with_dict(self):
        task = {}
        merge_left('annotations', task, self.issue_dict)
        self.assertEquals(task, self.issue_dict)

    def test_merge_left_with_taskw(self):
        task = taskw.task.Task({})
        merge_left('annotations', task, self.issue_dict)
        self.assertEquals(task, self.issue_dict)

########NEW FILE########
__FILENAME__ = test_github
import datetime

import pytz

from bugwarrior.services.github import GithubService

from .base import ServiceTest


class TestGithubIssue(ServiceTest):
    SERVICE_CONFIG = {
        'github.login': 'arbitrary_login',
        'github.password': 'arbitrary_password',
        'github.username': 'arbitrary_username',
    }

    def setUp(self):
        self.service = self.get_mock_service(GithubService)

    def test_to_taskwarrior(self):
        arbitrary_created = (
            datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        ).replace(tzinfo=pytz.UTC)
        arbitrary_updated = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        arbitrary_issue = {
            'title': 'Hallo',
            'html_url': 'http://whanot.com/',
            'number': 10,
            'body': 'Something',
            'milestone': {'id': 'alpha'},
            'created_at': arbitrary_created.isoformat(),
            'updated_at': arbitrary_updated.isoformat(),
        }
        arbitrary_extra = {
            'project': 'one',
            'type': 'issue',
            'annotations': [],
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue,
            arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_extra['project'],
            'priority': self.service.default_priority,
            'annotations': [],
            'tags': [],

            issue.URL: arbitrary_issue['html_url'],
            issue.TYPE: arbitrary_extra['type'],
            issue.TITLE: arbitrary_issue['title'],
            issue.NUMBER: arbitrary_issue['number'],
            issue.UPDATED_AT: arbitrary_updated,
            issue.CREATED_AT: arbitrary_created,
            issue.BODY: arbitrary_issue['body'],
            issue.MILESTONE: arbitrary_issue['milestone']['id'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_jira
import mock

from bugwarrior.services.jira import JiraService

from .base import ServiceTest


class TestJiraIssue(ServiceTest):
    SERVICE_CONFIG = {
        'jira.username': 'one',
        'jira.base_uri': 'two',
        'jira.password': 'three',
    }

    def setUp(self):
        with mock.patch('jira.client.JIRA._get_json'):
            self.service = self.get_mock_service(JiraService)

    def test_to_taskwarrior(self):
        arbitrary_project = 'DONUT'
        arbitrary_id = '10'
        arbitrary_url = 'http://one'
        arbitrary_summary = 'lkjaldsfjaldf'
        arbitrary_record = {
            'fields': {
                'priority': 'Blocker',
                'summary': arbitrary_summary,
            },
            'key': '%s-%s' % (arbitrary_project, arbitrary_id, ),
        }
        arbitrary_extra = {
            'jira_version': 5,
            'annotations': ['an annotation'],
        }

        issue = self.service.get_issue_for_record(
            arbitrary_record, arbitrary_extra
        )

        expected_output = {
            'project': arbitrary_project,
            'priority': (
                issue.PRIORITY_MAP[arbitrary_record['fields']['priority']]
            ),
            'annotations': arbitrary_extra['annotations'],
            'tags': [],

            issue.URL: arbitrary_url,
            issue.FOREIGN_ID: arbitrary_record['key'],
            issue.SUMMARY: arbitrary_summary,
            issue.DESCRIPTION: None,
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_megaplan
import mock

from bugwarrior.services.mplan import MegaplanService

from .base import ServiceTest


class TestMegaplanIssue(ServiceTest):
    SERVICE_CONFIG = {
        'megaplan.hostname': 'something',
        'megaplan.login': 'something_else',
        'megaplan.password': 'aljlkj',
    }

    def setUp(self):
        with mock.patch('megaplan.Client'):
            self.service = self.get_mock_service(MegaplanService)

    def test_to_taskwarrior(self):
        arbitrary_project = 'one'
        arbitrary_url = 'http://one.com/'
        name_parts = ['one', 'two', 'three']
        arbitrary_issue = {
            'Id': 10,
            'Name': '|'.join(name_parts)
        }

        issue = self.service.get_issue_for_record(arbitrary_issue)

        expected_output = {
            'project': arbitrary_project,
            'priority': self.service.default_priority,

            issue.FOREIGN_ID: arbitrary_issue['Id'],
            issue.URL: arbitrary_url,
            issue.TITLE: name_parts[-1]
        }

        def get_url(*args):
            return arbitrary_url

        def get_project(*args):
            return arbitrary_project

        with mock.patch.multiple(
            issue, get_project=mock.DEFAULT, get_issue_url=mock.DEFAULT
        ) as mocked:
            mocked['get_project'].side_effect = get_project
            mocked['get_issue_url'].side_effect = get_url
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_redmine
import mock

from bugwarrior.services.redmine import RedMineService

from .base import ServiceTest


class TestRedmineIssue(ServiceTest):
    SERVICE_CONFIG = {
        'redmine.url': 'something',
        'redmine.key': 'something_else',
        'redmine.user_id': '10834u0234',
    }

    def setUp(self):
        self.service = self.get_mock_service(RedMineService)

    def test_to_taskwarrior(self):
        arbitrary_url = 'http://lkjlj.com'
        arbitrary_issue = {
            'project': {
                'name': 'Something',
            },
            'subject': 'The Subject',
            'id': 'The ID',
        }

        issue = self.service.get_issue_for_record(arbitrary_issue)

        expected_output = {
            'project': arbitrary_issue['project']['name'],
            'priority': self.service.default_priority,

            issue.URL: arbitrary_url,
            issue.SUBJECT: arbitrary_issue['subject'],
            issue.ID: arbitrary_issue['id'],
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_teamlab
import mock

from bugwarrior.services.teamlab import TeamLabService

from .base import ServiceTest


class TestTeamlabIssue(ServiceTest):
    SERVICE_CONFIG = {
        'teamlab.hostname': 'something',
        'teamlab.login': 'alkjdsf',
        'teamlab.password': 'lkjklj',
        'teamlab.project_name': 'abcdef',
    }

    def setUp(self):
        with mock.patch(
            'bugwarrior.services.teamlab.TeamLabClient.authenticate'
        ):
            self.service = self.get_mock_service(TeamLabService)

    def test_to_taskwarrior(self):
        arbitrary_url = 'http://galkjsdflkj.com/'
        arbitrary_issue = {
            'title': 'Hello',
            'id': 10,
            'projectOwner': {
                'id': 140,
            }
        }

        issue = self.service.get_issue_for_record(arbitrary_issue)

        expected_output = {
            'project': self.SERVICE_CONFIG['teamlab.project_name'],
            'priority': self.service.default_priority,
            issue.TITLE: arbitrary_issue['title'],
            issue.FOREIGN_ID: arbitrary_issue['id'],
            issue.URL: arbitrary_url,
            issue.PROJECTOWNER_ID: arbitrary_issue['projectOwner']['id']
        }

        def get_url(*args):
            return arbitrary_url

        with mock.patch.object(issue, 'get_issue_url', side_effect=get_url):
            actual_output = issue.to_taskwarrior()

        self.assertEqual(actual_output, expected_output)

########NEW FILE########
__FILENAME__ = test_templates
import mock

from bugwarrior.services import Issue

from .base import ServiceTest


class TestTemplates(ServiceTest):
    def setUp(self):
        self.arbitrary_default_description = 'Construct Library on Terminus'
        self.arbitrary_issue = {
            'project': 'end_of_empire',
            'priority': 'H',
        }

    def get_issue(
        self, templates=None, issue=None, description=None, add_tags=None
    ):
        templates = {} if templates is None else templates
        origin = {
            'annotation_length': 100,  # Arbitrary
            'default_priority': 'H',  # Arbitrary
            'description_length': 100,  # Arbitrary
            'templates': templates,
            'shorten': False,  # Arbitrary
            'add_tags': add_tags if add_tags else [],
        }

        issue = Issue({}, origin)
        issue.to_taskwarrior = lambda: (
            self.arbitrary_issue if description is None else description
        )
        issue.get_default_description = lambda: (
            self.arbitrary_default_description
            if description is None else description
        )
        return issue

    def test_default_taskwarrior_record(self):
        issue = self.get_issue({})

        record = issue.get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update({
            'description': self.arbitrary_default_description,
            'tags': [],
        })

        self.assertEqual(record, expected_record)

    def test_override_description(self):
        description_template = "{{ priority }} - {{ description }}"

        issue = self.get_issue({
            'description': description_template
        })

        record = issue.get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update({
            'description': '%s - %s' % (
                self.arbitrary_issue['priority'],
                self.arbitrary_default_description,
            ),
            'tags': [],
        })

        self.assertEqual(record, expected_record)

    def test_override_project(self):
        project_template = "wat_{{ project|upper }}"

        issue = self.get_issue({
            'project': project_template
        })

        record = issue.get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update({
            'description': self.arbitrary_default_description,
            'project': 'wat_%s' % self.arbitrary_issue['project'].upper(),
            'tags': [],
        })

        self.assertEqual(record, expected_record)

    def test_tag_templates(self):
        issue = self.get_issue(add_tags=['one', '{{ project }}'])

        record = issue.get_taskwarrior_record()
        expected_record = self.arbitrary_issue.copy()
        expected_record.update({
            'description': self.arbitrary_default_description,
            'tags': ['one', self.arbitrary_issue['project']]
        })

        self.assertEqual(record, expected_record)

########NEW FILE########
__FILENAME__ = test_trac
from bugwarrior.services.trac import TracService

from .base import ServiceTest


class TestTracIssue(ServiceTest):
    SERVICE_CONFIG = {
        'trac.base_uri': 'http://ljlkajsdfl.com',
        'trac.username': 'something',
        'trac.password': 'somepwd',
    }

    def setUp(self):
        self.service = self.get_mock_service(TracService)

    def test_to_taskwarrior(self):
        arbitrary_issue = {
            'url': 'http://some/url.com/',
            'summary': 'Some Summary',
            'number': 204,
            'priority': 'critical',
        }
        arbitrary_extra = {
            'annotations': [
                'alpha',
                'beta',
            ],
            'project': 'some project',
        }

        issue = self.service.get_issue_for_record(
            arbitrary_issue,
            arbitrary_extra,
        )

        expected_output = {
            'project': arbitrary_extra['project'],
            'priority': issue.PRIORITY_MAP[arbitrary_issue['priority']],
            'annotations': arbitrary_extra['annotations'],
            issue.URL: arbitrary_issue['url'],
            issue.SUMMARY: arbitrary_issue['summary'],
            issue.NUMBER: arbitrary_issue['number'],
        }
        actual_output = issue.to_taskwarrior()

        self.assertEquals(actual_output, expected_output)

########NEW FILE########
