__FILENAME__ = bootstrap
# -*- coding: utf-8 -*-

"""
legit.bootstrap
~~~~~~~~~~~~~~~

This module boostraps the Legit runtime.
"""


import ConfigParser


import clint.textui.colored
from clint import resources
from clint.textui import colored



from .settings import settings



resources.init('kennethreitz', 'legit')

try:
    config_file = resources.user.open('config.ini', 'r')
except IOError:
    resources.user.write('config.ini', '')
    config_file = resources.user.open('config.ini', 'r')


# Load existing configuration.
config = ConfigParser.ConfigParser()
config.readfp(config_file)



# Populate if needed.
if not config.has_section('legit'):
    config.add_section('legit')


modified = False

# Set defaults if they are missing.
# Add everything to settings object.
for (k, v, _) in settings.config_defaults:
    if not config.has_option('legit', k):
        modified = True
        config.set('legit', k, v)
        setattr(settings, k, v)
    else:
        val = config.get('legit', k)

        # Map boolean strings.
        if val.lower() in ('true', '1', 'yep', 'sure'):
            val = True
        elif val.lower() in ('false', '0', 'nope', 'nadda', 'nah'):
            val = False

        setattr(settings, k, val)

if modified:
    config_file = resources.user.open('config.ini', 'w')
    config.write(config_file)


if settings.disable_colors:
    clint.textui.colored.DISABLE_COLOR = True

########NEW FILE########
__FILENAME__ = cli
# -*- coding: utf-8 -*-

"""
legit.cli
~~~~~~~~~

This module provides the CLI interface to legit.
"""

import os
import sys
from subprocess import call
from time import sleep

import clint.resources
from clint import Args
from clint.eng import join as eng_join
from clint.textui import colored, puts, columns

from .core import __version__
from .settings import settings
from .helpers import is_lin, is_osx, is_win
from .scm import *

args = Args()

def black(s):
    if settings.allow_black_foreground:
        return colored.black(s)
    else:
        return s.encode('utf-8')

# --------
# Dispatch
# --------

def main():
    """Primary Legit command dispatch."""

    command = Command.lookup(args.get(0))
    if command:
        arg = args.get(0)
        args.remove(arg)

        command.__call__(args)
        sys.exit()

    elif args.contains(('-h', '--help')):
        display_help()
        sys.exit(1)

    elif args.contains(('-v', '--version')):
        display_version()
        sys.exit(1)

    else:
        if settings.git_transparency:
            # Send everything to git
            git_args = list(sys.argv)
            if settings.git_transparency is True:
                settings.git_transparency = os.environ.get("GIT_PYTHON_GIT_EXECUTABLE", 'git')

            git_args[0] = settings.git_transparency

            sys.exit(call(' '.join(git_args), shell=True))

        else:
            show_error(colored.red('Unknown command {0}'.format(args.get(0))))
            display_info()
            sys.exit(1)


def show_error(msg):
    sys.stdout.flush()
    sys.stderr.write(msg + '\n')


# -------
# Helpers
# -------

def status_log(func, message, *args, **kwargs):
    """Executes a callable with a header message."""

    print message
    log = func(*args, **kwargs)

    if log:
        out = []

        for line in log.split('\n'):
            if not line.startswith('#'):
                out.append(line)
        print black('\n'.join(out))


def switch_to(branch):
    """Runs the cmd_switch command with given branch arg."""

    switch_args = args.copy
    switch_args._args = [branch]

    return cmd_switch(switch_args)

def fuzzy_match_branch(branch):
    if not branch: return False

    all_branches = get_branch_names()
    if branch in all_branches:
        return branch

    def branch_fuzzy_match(b): return b.startswith(branch)
    possible_branches = filter(branch_fuzzy_match, all_branches)

    if len(possible_branches) == 1:
        return possible_branches[0]

    return False

# --------
# Commands
# --------

def cmd_switch(args):
    """Legit Switch command."""

    from_branch = repo.head.ref.name
    to_branch = args.get(0)
    to_branch = fuzzy_match_branch(to_branch)

    if not to_branch:
        print 'Please specify a branch to switch to:'
        display_available_branches()
        sys.exit()

    if repo.is_dirty():
        status_log(stash_it, 'Saving local changes.')

    status_log(checkout_branch, 'Switching to {0}.'.format(
        colored.yellow(to_branch)), to_branch)

    if unstash_index(branch=from_branch):
        status_log(unstash_it, 'Restoring local changes.', branch=from_branch)

def cmd_resync(args):
    """Stashes unstaged changes, 
    Fetches upstream data from master branch,
    Auto-Merge/Rebase from master branch 
    Performs smart pull+merge, 
    Pushes local commits up, and Unstashes changes.
    Defaults to current branch.
    """
    if args.get(0):
        upstream = fuzzy_match_branch(args.get(0))
        if upstream:
            is_external = True
            original_branch = repo.head.ref.name
        else:
            print "{0} doesn't exist. Use a branch that does.".format(
                colored.yellow(args.get(0)))
            sys.exit(1)
    else:
        upstream = "master"
    original_branch = repo.head.ref.name
    if repo.is_dirty():
        status_log(stash_it, 'Saving local changes.', sync=True)
    switch_to(upstream)
    status_log(smart_pull, 'Pulling commits from the server.')
    switch_to(original_branch)
    status_log(smart_merge, 'Grafting commits from {0}.'.format(
        colored.yellow(upstream)), upstream, allow_rebase=False)
    if unstash_index(sync=True):
        status_log(unstash_it, 'Restoring local changes.', sync=True)
    status_log(smart_pull, 'Pulling commits from the server.')
    status_log(push, 'Pushing commits to the server.', original_branch)

def cmd_sync(args):
    """Stashes unstaged changes, Fetches remote data, Performs smart
    pull+merge, Pushes local commits up, and Unstashes changes.

    Defaults to current branch.
    """

    if args.get(0):
        # Optional branch specifier.
        branch = fuzzy_match_branch(args.get(0))
        if branch:
            is_external = True
            original_branch = repo.head.ref.name
        else:
            print "{0} doesn't exist. Use a branch that does.".format(
                colored.yellow(args.get(0)))
            sys.exit(1)
    else:
        # Sync current branch.
        branch = repo.head.ref.name
        is_external = False

    if branch in get_branch_names(local=False):

        if is_external:
            switch_to(branch)

        if repo.is_dirty():
            status_log(stash_it, 'Saving local changes.', sync=True)

        status_log(smart_pull, 'Pulling commits from the server.')
        status_log(push, 'Pushing commits to the server.', branch)

        if unstash_index(sync=True):
            status_log(unstash_it, 'Restoring local changes.', sync=True)

        if is_external:
            switch_to(original_branch)

    else:
        print '{0} has not been published yet.'.format(
            colored.yellow(branch))
        sys.exit(1)


def cmd_sprout(args):
    """Creates a new branch of given name from given branch.
    Defaults to current branch.
    """

    off_branch = args.get(0)
    new_branch = args.get(1)

    if new_branch is None:
        new_branch = off_branch
        off_branch = repo.head.ref.name
    else:
        off_branch = fuzzy_match_branch(off_branch)

    if not off_branch:
        print 'Please specify branch to sprout:'
        display_available_branches()
        sys.exit()

    branch_names = get_branch_names()

    if off_branch not in branch_names:
        print "{0} doesn't exist. Use a branch that does.".format(
            colored.yellow(off_branch))
        sys.exit(1)

    if new_branch in branch_names:
        print "{0} already exists. Use a unique name.".format(
            colored.yellow(new_branch))
        sys.exit(1)


    if repo.is_dirty():
        status_log(stash_it, 'Saving local changes.')

    status_log(sprout_branch, 'Branching {0} to {1}.'.format(
        colored.yellow(off_branch), colored.yellow(new_branch)),
        off_branch, new_branch)


def cmd_graft(args):
    """Merges an unpublished branch into the given branch, then deletes it."""

    branch = fuzzy_match_branch(args.get(0))
    into_branch = args.get(1)

    if not branch:
        print 'Please specify a branch to graft:'
        display_available_branches()
        sys.exit()

    if not into_branch:
        into_branch = repo.head.ref.name
    else:
        into_branch = fuzzy_match_branch(into_branch)

    branch_names = get_branch_names(local=True, remote_branches=False)
    remote_branch_names = get_branch_names(local=False, remote_branches=True)

    if branch not in branch_names:
        print "{0} doesn't exist. Use a branch that does.".format(
            colored.yellow(branch))
        sys.exit(1)

    if branch in remote_branch_names:
        print "{0} is published. To graft it, unpublish it first.".format(
            colored.yellow(branch))
        sys.exit(1)

    if into_branch not in branch_names:
        print "{0} doesn't exist. Use a branch that does.".format(
            colored.yellow(into_branch))
        sys.exit(1)

    # Go to new branch.
    switch_to(into_branch)

    status_log(graft_branch, 'Grafting {0} into {1}.'.format(
        colored.yellow(branch), colored.yellow(into_branch)), branch)


def cmd_publish(args):
    """Pushes an unpublished branch to a remote repository."""

    branch = fuzzy_match_branch(args.get(0))

    if not branch:
        branch = repo.head.ref.name
        display_available_branches()
        print "Branch {0} not found, using current branch {1}".format(colored.red(args.get(0)),colored.yellow(branch))

    branch_names = get_branch_names(local=False)

    if branch in branch_names:
        print "{0} is already published. Use a branch that isn't.".format(
            colored.yellow(branch))
        sys.exit(1)

    status_log(publish_branch, 'Publishing {0}.'.format(
        colored.yellow(branch)), branch)



def cmd_unpublish(args):
    """Removes a published branch from the remote repository."""

    branch = fuzzy_match_branch(args.get(0))

    if not branch:
        print 'Please specify a branch to unpublish:'
        display_available_branches()
        sys.exit()

    branch_names = get_branch_names(local=False)

    if branch not in branch_names:
        print "{0} isn't published. Use a branch that is.".format(
            colored.yellow(branch))
        sys.exit(1)

    status_log(unpublish_branch, 'Unpublishing {0}.'.format(
        colored.yellow(branch)), branch)


def cmd_harvest(args):
    """Syncs a branch with given branch. Defaults to current."""

    from_branch = fuzzy_match_branch(args.get(0))
    to_branch = fuzzy_match_branch(args.get(1))

    if not from_branch:
        print 'Please specify a branch to harvest commits from:'
        display_available_branches()
        sys.exit()

    if to_branch:
        original_branch = repo.head.ref.name
        is_external = True
    else:
        is_external = False

    branch_names = get_branch_names(local=True, remote_branches=False)

    if from_branch not in branch_names:
        print "{0} isn't an available branch. Use a branch that is.".format(
            colored.yellow(from_branch))
        sys.exit(1)

    if is_external:
        switch_to(to_branch)

    if repo.is_dirty():
        status_log(stash_it, 'Saving local changes.')

    status_log(smart_merge, 'Grafting commits from {0}.'.format(
        colored.yellow(from_branch)), from_branch, allow_rebase=False)

    if is_external:
        switch_to(original_branch)

    if unstash_index():
        status_log(unstash_it, 'Restoring local changes.')


#

def cmd_branches(args):
    """Displays available branches."""

    display_available_branches()


def cmd_settings(args):
    """Opens legit settings in editor."""

    path = clint.resources.user.open('config.ini').name


    print 'Legit Settings:\n'

    for (option, _, description) in settings.config_defaults:
        print columns([colored.yellow(option), 25], [description, None])


    print '\nSee {0} for more details.'.format(settings.config_url)

    sleep(0.35)

    if is_osx:
        editor = os.environ.get('EDITOR') or os.environ.get('VISUAL') or 'open'
        os.system("{0} '{1}'".format(editor, path))
    elif is_lin:
        editor = os.environ.get('EDITOR') or os.environ.get('VISUAL') or 'pico'
        os.system("{0} '{1}'".format(editor, path))
    elif is_win:
        os.system("'{0}'".format(path))
    else:
        print "Edit '{0}' to manage Legit settings.\n".format(path)

    sys.exit()


def cmd_install(args):
    """Installs legit git aliases."""

    aliases = [
        'branches',
        'graft',
        'harvest',
        'publish',
        'unpublish',
        'sprout',
        'sync',
        'switch',
        'resync',
    ]

    print 'The following git aliases have been installed:\n'

    for alias in aliases:
        cmd = '!legit ' + alias
        os.system('git config --global --replace-all alias.{0} "{1}"'.format(alias, cmd))
        print columns(['', 1], [colored.yellow('git ' + alias), 20], [cmd, None])

    sys.exit()


def cmd_help(args):
    """Display help for individual commands."""
    command = args.get(0)
    help(command)

# -----
# Views
# -----

def help(command):
    if command == None:
        command = 'help'

    cmd = Command.lookup(command)
    usage = cmd.usage or ''
    help = cmd.help or ''
    help_text = '%s\n\n%s' % (usage, help)
    print help_text


def display_available_branches():
    """Displays available branches."""

    branches = get_branches()

    if not branches:
        print colored.red('No branches available')
        return

    branch_col = len(max([b.name for b in branches], key=len)) + 1

    for branch in branches:

        try:
            branch_is_selected = (branch.name == repo.head.ref.name)
        except TypeError:
            branch_is_selected = False

        marker = '*' if branch_is_selected else ' '
        color = colored.green if branch_is_selected else colored.yellow
        pub = '(published)' if branch.is_published else '(unpublished)'

        print columns(
            [colored.red(marker), 2],
            [color(branch.name), branch_col],
            [black(pub), 14]
        )


def display_info():
    """Displays Legit informatics."""

    puts('{0}. {1}\n'.format(
        colored.red('legit'),
        black(u'A Kenneth Reitz Project™')
    ))

    puts('Usage: {0}'.format(colored.blue('legit <command>')))
    puts('Commands:\n')
    for command in Command.all_commands():
        usage = command.usage or command.name
        help = command.help or ''
        puts('{0:40} {1}'.format(
                colored.green(usage),
                first_sentence(help)))


def first_sentence(s):
    pos = s.find('. ')
    if pos < 0:
        pos = len(s) - 1
    return s[:pos + 1]


def display_help():
    """Displays Legit help."""

    display_info()


def display_version():
    """Displays Legit version/release."""


    puts('{0} v{1}'.format(
        colored.yellow('legit'),
        __version__
    ))


def handle_abort(aborted):
    print colored.red('Error:'), aborted.message
    print black(str(aborted.log))
    print 'Unfortunately, there was a merge conflict. It has to be merged manually.'
    sys.exit(1)


settings.abort_handler = handle_abort


class Command(object):
    COMMANDS = {}
    SHORT_MAP = {}

    @classmethod
    def register(klass, command):
        klass.COMMANDS[command.name] = command
        if command.short:
            for short in command.short:
                klass.SHORT_MAP[short] = command

    @classmethod
    def lookup(klass, name):
        if name in klass.SHORT_MAP:
            return klass.SHORT_MAP[name]
        if name in klass.COMMANDS:
            return klass.COMMANDS[name]
        else:
            return None

    @classmethod
    def all_commands(klass):
        return sorted(klass.COMMANDS.values(),
                      key=lambda cmd: cmd.name)

    def __init__(self, name=None, short=None, fn=None, usage=None, help=None):
        self.name = name
        self.short = short
        self.fn = fn
        self.usage = usage
        self.help = help

    def __call__(self, *args, **kw_args):
        return self.fn(*args, **kw_args)


def def_cmd(name=None, short=None, fn=None, usage=None, help=None):
    command = Command(name=name, short=short, fn=fn, usage=usage, help=help)
    Command.register(command)


def_cmd(
    name='branches',
    fn=cmd_branches,
    usage='branches',
    help='Get a nice pretty list of branches.')

def_cmd(
    name='graft',
    short=['gr'],
    fn=cmd_graft,
    usage='graft <branch> <into-branch>',
    help=('Merges specified branch into the second branch, and removes it. '
          'You can only graft unpublished branches.'))

def_cmd(
    name='harvest',
    short=['ha', 'hv', 'har'],
    usage='harvest [<branch>] <into-branch>',
    help=('Auto-Merge/Rebase of specified branch changes into the second '
          'branch.'),
    fn=cmd_harvest)

def_cmd(
    name='help',
    short=['h'],
    fn=cmd_help,
    usage='help <command>',
    help='Display help for legit command.')

def_cmd(
    name='install',
    fn=cmd_install,
    usage='install',
    help='Installs legit git aliases.')

def_cmd(
    name='publish',
    short=['pub'],
    fn=cmd_publish,
    usage='publish <branch>',
    help='Publishes specified branch to the remote.')

def_cmd(
    name='settings',
    fn=cmd_settings,
    usage='settings',
    help='Opens legit settings in a text editor.')

def_cmd(
    name='sprout',
    short=['sp'],
    fn=cmd_sprout,
    usage='sprout [<branch>] <new-branch>',
    help=('Creates a new branch off of the specified branch. Defaults to '
          'current branch. Switches to it immediately.'))

def_cmd(
    name='switch',
    short=['sw'],
    fn=cmd_switch,
    usage='switch <branch>',
    help=('Switches to specified branch. Automatically stashes and unstashes '
          'any changes.'))

def_cmd(
    name='sync',
    short=['sy'],
    fn=cmd_sync,
    usage='sync <branch>',
    help=('Syncronizes the given branch. Defaults to current branch. Stash, '
          'Fetch, Auto-Merge/Rebase, Push, and Unstash.'))
def_cmd(
    name='resync',
    short=['rs'],
    fn=cmd_resync,
    usage='sync <branch>',
    help=('Syncronizes the given branch. Defaults to current branch. Stash, '
          'Fetch, Auto-Merge/Rebase, Push, and Unstash.'))

def_cmd(
    name='unpublish',
    short=['unp'],
    fn=cmd_unpublish,
    usage='unpublish <branch>',
    help='Removes specified branch from the remote.')

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

"""
legit.core
~~~~~~~~~~

This module provides the basic functionality of legit.
"""

import bootstrap
del bootstrap

__version__ = '0.1.1'
__author__ = 'Kenneth Reitz'
__license__ = 'BSD'


########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-

"""
legit.helpers
~~~~~~~~~~~~~

Various Python helpers.
"""


import os
import platform

_platform = platform.system().lower()

is_osx = (_platform == 'darwin')
is_win = (_platform == 'windows')
is_lin = (_platform == 'linux')

########NEW FILE########
__FILENAME__ = scm
# -*- coding: utf-8 -*-

"""
legit.scm
~~~~~~~~~

This module provides the main interface to Git.
"""

import os
import sys
import subprocess
from collections import namedtuple
from exceptions import ValueError
from operator import attrgetter

from git import Repo
from git.exc import GitCommandError

from .settings import settings


LEGIT_TEMPLATE = 'Legit: stashing before {0}.'

git = os.environ.get("GIT_PYTHON_GIT_EXECUTABLE", 'git')

Branch = namedtuple('Branch', ['name', 'is_published'])


class Aborted(object):

    def __init__(self):
        self.message = None
        self.log = None


def abort(message, log=None):

    a = Aborted()
    a.message = message
    a.log = log

    settings.abort_handler(a)

def repo_check(require_remote=False):
    if repo is None:
        print 'Not a git repository.'
        sys.exit(128)

    # TODO: no remote fail
    if not repo.remotes and require_remote:
        print 'No git remotes configured. Please add one.'
        sys.exit(128)

    # TODO: You're in a merge state.



def stash_it(sync=False):
    repo_check()
    msg = 'syncing branch' if sync else 'switching branches'

    return repo.git.execute([git,
        'stash', 'save', '--include-untracked',
        LEGIT_TEMPLATE.format(msg)])


def unstash_index(sync=False, branch=None):
    """Returns an unstash index if one is available."""

    repo_check()

    stash_list = repo.git.execute([git,
        'stash', 'list'])

    if branch is None:
        branch = repo.head.ref.name

    for stash in stash_list.splitlines():

        verb = 'syncing' if sync else 'switching'

        if (
            (('Legit' in stash) and
                ('On {0}:'.format(branch) in stash) and
                (verb in stash))
            or (('GitHub' in stash) and
                ('On {0}:'.format(branch) in stash) and
                (verb in stash))
        ):
            return stash[7]

def unstash_it(sync=False, branch=None):
    """Unstashes changes from current branch for branch sync."""

    repo_check()

    stash_index = unstash_index(sync=sync, branch=branch)

    if stash_index is not None:
        return repo.git.execute([git,
            'stash', 'pop', 'stash@{{{0}}}'.format(stash_index)])


def fetch():

    repo_check()

    return repo.git.execute([git, 'fetch', remote.name])


def smart_pull():
    'git log --merges origin/master..master'

    repo_check()

    branch = repo.head.ref.name

    fetch()

    return smart_merge('{0}/{1}'.format(remote.name, branch))


def smart_merge(branch, allow_rebase=True):

    repo_check()

    from_branch = repo.head.ref.name

    merges = repo.git.execute([git,
        'log', '--merges', '{0}..{1}'.format(branch, from_branch)])

    if allow_rebase:
        verb = 'merge' if merges.count('commit') else 'rebase'
    else:
        verb = 'merge'

    try:
        return repo.git.execute([git, verb, branch])
    except GitCommandError, why:
        log = repo.git.execute([git,'merge', '--abort'])
        abort('Merge failed. Reverting.', log=why)



def push(branch=None):

    repo_check()

    if branch is None:
        return repo.git.execute([git, 'push'])
    else:
        return repo.git.execute([git, 'push', remote.name, branch])


def checkout_branch(branch):
    """Checks out given branch."""

    repo_check()

    return repo.git.execute([git, 'checkout', branch])


def sprout_branch(off_branch, branch):
    """Checks out given branch."""

    repo_check()

    return repo.git.execute([git, 'checkout', off_branch, '-b', branch])


def graft_branch(branch):
    """Merges branch into current branch, and deletes it."""

    repo_check()

    log = []

    try:
        msg = repo.git.execute([git, 'merge', '--no-ff', branch])
        log.append(msg)
    except GitCommandError, why:
        log = repo.git.execute([git,'merge', '--abort'])
        abort('Merge failed. Reverting.', log='{0}\n{1}'.format(why, log))


    out = repo.git.execute([git, 'branch', '-D', branch])
    log.append(out)
    return '\n'.join(log)


def unpublish_branch(branch):
    """Unpublishes given branch."""

    repo_check()

    return repo.git.execute([git,
        'push', remote.name, ':{0}'.format(branch)])


def publish_branch(branch):
    """Publishes given branch."""

    repo_check()

    return repo.git.execute([git,
        'push', '-u', remote.name, branch])


def get_repo():
    """Returns the current Repo, based on path."""

    work_path = subprocess.Popen([git, 'rev-parse', '--show-toplevel'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()[0].rstrip('\n')

    if work_path:
        return Repo(work_path)
    else:
        return None


def get_remote():

    repo_check(require_remote=True)

    reader = repo.config_reader()

    # If there is no legit section return the default remote.
    if not reader.has_section('legit'):
        return repo.remotes[0]

    # If there is no remote option in the legit section return the default.
    if not any('legit' in s and 'remote' in s for s in reader.sections()):
        return repo.remotes[0]

    remote_name = reader.get('legit', 'remote')
    if not remote_name in [r.name for r in repo.remotes]:
        raise ValueError('Remote "{0}" does not exist! Please update your git '
                         'configuration.'.format(remote_name))

    return repo.remote(remote_name)


def get_branches(local=True, remote_branches=True):
    """Returns a list of local and remote branches."""

    repo_check()

    # print local
    branches = []

    if remote_branches:

        # Remote refs.
        try:
            for b in remote.refs:
                name = '/'.join(b.name.split('/')[1:])

                if name not in settings.forbidden_branches:
                    branches.append(Branch(name, True))
        except (IndexError, AssertionError):
            pass

    if local:

        # Local refs.
        for b in [h.name for h in repo.heads]:

            if b not in [br.name for br in branches] or not remote_branches:
                if b not in settings.forbidden_branches:
                    branches.append(Branch(b, False))


    return sorted(branches, key=attrgetter('name'))


def get_branch_names(local=True, remote_branches=True):

    repo_check()

    branches = get_branches(local=local, remote_branches=remote_branches)

    return [b.name for b in branches]


repo = get_repo()
remote = get_remote()

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

"""
legit.config
~~~~~~~~~~~~~~~~~~

This module provides the Legit settings feature set.

"""


class Settings(object):
    _singleton = {}

    # attributes with defaults
    __attrs__ = tuple()

    def __init__(self, **kwargs):
        super(Settings, self).__init__()

        self.__dict__ = self._singleton


    def __call__(self, *args, **kwargs):
        # new instance of class to call
        r = self.__class__()

        # cache previous settings for __exit__
        r.__cache = self.__dict__.copy()
        map(self.__cache.setdefault, self.__attrs__)

        # set new settings
        self.__dict__.update(*args, **kwargs)

        return r


    def __enter__(self):
        pass


    def __exit__(self, *args):

        # restore cached copy
        self.__dict__.update(self.__cache.copy())
        del self.__cache


    def __getattribute__(self, key):
        if key in object.__getattribute__(self, '__attrs__'):
            try:
                return object.__getattribute__(self, key)
            except AttributeError:
                return None
        return object.__getattribute__(self, key)

settings = Settings()

settings.config_defaults = (
    ('check_for_updates', True,
        'Are update checks allowed? Defaults to True.'),

    ('allow_black_foreground', True,
        'Is the epic black foreground color allowed? Defaults to True.'),

    ('git_transparency', False,
        'Send unknown commands to Git? Defaults to False.'),

    ('disable_colors', False,
        'Y U NO FUN? Defaults to False.'),

    ('last_update_check', None,
        'Date of the last update check.'))


settings.config_url = 'http://git-legit.org/config'
settings.update_url = 'https://api.github.com/repos/kennethreitz/legit/tags'
settings.forbidden_branches = ['HEAD',]
########NEW FILE########
__FILENAME__ = legit
# -*- coding: utf-8 -*-

from legit.cli import main
if __name__ == '__main__':
    main()
########NEW FILE########
