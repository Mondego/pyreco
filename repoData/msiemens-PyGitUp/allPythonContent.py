__FILENAME__ = gitup
# coding=utf-8
"""
git up -- like 'git pull', but polite

Usage: git up [-h | --version | --quiet]

Options:
  -h            Show this screen.
  --version     Show version (and if there is a newer version).
  --quiet       Be quiet, only print error messages.


Why use git-up? `git pull` has two problems:
  - It merges upstream changes by default, when it's really more polite to
    rebase over them, unless your collaborators enjoy a commit graph that
    looks like bedhead.
  - It only updates the branch you're currently on, which means git push
    will shout at you for being behind on branches you don't particularly
    care about right now.
(from the original git-up https://github.com/aanand/git-up/)


For configuration options, please see
https://github.com/msiemens/PyGitUp#readme or <path-to-PyGitUp>/README.rst.


Python port of https://github.com/aanand/git-up/
Project Author: Markus Siemens <markus@m-siemens.de>
Project URL: https://github.com/msiemens/PyGitUp
"""

from __future__ import print_function

__all__ = ['GitUp']

###############################################################################
# IMPORTS and LIBRARIES SETUP
###############################################################################

# Python libs
import sys
import os
import re
import platform
import json
import urllib2
import subprocess
from cStringIO import StringIO
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

# 3rd party libs
try:
    #noinspection PyUnresolvedReferences
    import pkg_resources as pkg
except ImportError:
    NO_DISTRIBUTE = True
else:
    NO_DISTRIBUTE = False

import colorama
from docopt import docopt
from git import Repo, GitCmdObjectDB
from termcolor import colored

# PyGitUp libs
from PyGitUp.utils import execute, uniq, find
from PyGitUp.git_wrapper import GitWrapper, GitError

###############################################################################
# Setup of 3rd party libs
###############################################################################

colorama.init(autoreset=True)


###############################################################################
# Setup constants
###############################################################################

PYPI_URL = 'https://pypi.python.org/pypi/git-up/json'


###############################################################################
# GitUp
###############################################################################

class GitUp(object):
    """ Conainter class for GitUp methods """

    default_settings = {
        'bundler.check': False,
        'bundler.autoinstall': False,
        'bundler.local': False,
        'bundler.rbenv': False,
        'fetch.prune': True,
        'fetch.all': False,
        'rebase.arguments': None,
        'rebase.auto': True,
        'rebase.log-hook': None,
        'updates.check': True
    }

    def __init__(self, testing=False, sparse=False):
        # Sparse init: config only
        if sparse:
            self.git = GitWrapper(None)

            # Load configuration
            self.settings = self.default_settings.copy()
            self.load_config()
            return

        # Testing: redirect stderr to stdout
        self.testing = testing
        if testing:
            self.stderr = sys.stdout  # Quiet testing
        else:
            self.stderr = sys.stderr

        self.states = []

        # Check, if we're in a git repo
        try:
            self.repo = Repo(execute('git rev-parse --show-toplevel'),
                             odbt=GitCmdObjectDB)
        except IndexError:
            exc = GitError("We don't seem to be in a git repository.")
            self.print_error(exc)

            raise exc

        # Check for branch tracking informatino
        if not any(b.tracking_branch() for b in self.repo.branches):
            exc = GitError("Can\'t update your repo because it doesn\'t has "
                           "any branches with tracking information.")
            self.print_error(exc)

            raise exc

        self.git = GitWrapper(self.repo)

        # target_map: map local branch names to remote tracking branches
        self.target_map = dict()

        for branch in self.repo.branches:
            target = branch.tracking_branch()

            if target:
                if target.name.startswith('./'):
                    # Tracking branch is in local repo
                    target.is_local = True
                else:
                    target.is_local = False

                self.target_map[branch.name] = target

        # branches: all local branches with tracking information
        self.branches = [b for b in self.repo.branches if b.tracking_branch()]
        self.branches.sort(key=lambda br: br.name)

        # remotes: all remotes that are associated with local branches
        self.remotes = uniq(
            # name = '<remote>/<branch>' -> '<remote>'
            [r.name.split('/', 2)[0]
             for r in list(self.target_map.values())]
        )

        # change_count: Number of unstaged changes
        self.change_count = len(
            self.git.status(porcelain=True, untracked_files='no').split('\n')
        )

        # Load configuration
        self.settings = self.default_settings.copy()
        self.load_config()

    def run(self):
        """ Run all the git-up stuff. """
        try:
            self.fetch()

            with self.git.stash():
                with self.returning_to_current_branch():
                    self.rebase_all_branches()

            if self.with_bundler():
                self.check_bundler()

        except GitError as error:
            self.print_error(error)

            # Used for test cases
            if self.testing:
                raise
            else:
                sys.exit(1)

    def rebase_all_branches(self):
        """ Rebase all branches, if possible. """
        col_width = max(len(b.name) for b in self.branches) + 1

        for branch in self.branches:
            target = self.target_map[branch.name]

            # Print branch name
            if branch.name == self.repo.active_branch.name:
                attrs = ['bold']
            else:
                attrs = []
            print(colored(branch.name.ljust(col_width), attrs=attrs),
                  end=' ')

            # Check, if target branch exists
            try:
                if target.name.startswith('./'):
                    # Check, if local branch exists
                    self.git.rev_parse(target.name[2:])

                else:
                    # Check, if remote branch exists
                    _ = target.commit

            except (ValueError, GitError):
                # Remote branch doesn't exist!
                print(colored('error: remote branch doesn\'t exist', 'red'))
                self.states.append('remote branch doesn\'t exist')

                continue

            # Get tracking branch
            if target.is_local:
                target = find(self.repo.branches,
                              lambda b: b.name == target.name[2:])

            # Check status and act appropriately
            if target.commit.hexsha == branch.commit.hexsha:
                print(colored('up to date', 'green'))
                self.states.append('up to date')

                continue  # Do not do anything

            base = self.git.merge_base(branch.name, target.name)

            if base == target.commit.hexsha:
                print(colored('ahead of upstream', 'cyan'))
                self.states.append('ahead')

                continue  # Do not do anything

            if base == branch.commit.hexsha:
                print(colored('fast-forwarding...', 'yellow'))
                self.states.append('fast-forwarding')

            elif not self.settings['rebase.auto']:
                print(colored('diverged', 'red'))
                self.states.append('diverged')

                continue  # Do not do anything
            else:
                print(colored('rebasing', 'yellow'))
                self.states.append('rebasing')

            self.log(branch, target)
            self.git.checkout(branch.name)
            self.git.rebase(target)

    def fetch(self):
        """
        Fetch the recent refs from the remotes.

        Unless git-up.fetch.all is set to true, all remotes with
        locally existent branches will be fetched.
        """
        fetch_kwargs = {'multiple': True}
        fetch_args = []

        if self.is_prune():
            fetch_kwargs['prune'] = True

        if self.settings['fetch.all']:
            fetch_kwargs['all'] = True
        else:
            fetch_args.append(self.remotes)

            if fetch_args[-1] == ['.']:
                # Only local target branches, `git fetch --multiple` will fail
                return

        try:
            self.git.fetch(tostdout=True, *fetch_args, **fetch_kwargs)
        except GitError as error:
            error.message = "`git fetch` failed"
            raise error

    def log(self, branch, remote):
        """ Call a log-command, if set by git-up.fetch.all. """
        log_hook = self.settings['rebase.log-hook']

        if log_hook:
            if platform.system() == 'Windows':
                # Running a string in CMD from Python is not that easy on
                # Windows. Running 'cmd /C log_hook' produces problems when
                # using multiple statements or things like 'echo'. Therefore,
                # we write the string to a bat file and execute it.

                # In addition, we replace occurences of $1 with %1 and so forth
                # in case the user is used to Bash or sh.
                # If there are occurences of %something, we'll replace it with
                # %%something. This is the case when running something like
                # 'git log --pretty=format:"%Cred%h..."'.
                # Also, we replace a semicolon with a newline, because if you
                # start with 'echo' on Windows, it will simply echo the
                # semicolon and the commands behind instead of echoing and then
                # running other commands

                # Prepare log_hook
                log_hook = re.sub(r'\$(\d+)', r'%\1', log_hook)
                log_hook = re.sub(r'%(?!\d)', '%%', log_hook)
                log_hook = re.sub(r'; ?', r'\n', log_hook)

                # Write log_hook to an temporary file and get it's path
                with NamedTemporaryFile(
                        prefix='PyGitUp.', suffix='.bat', delete=False
                ) as bat_file:
                    # Don't echo all commands
                    bat_file.file.write('@echo off\n')
                    # Run log_hook
                    bat_file.file.write(log_hook)

                # Run bat_file
                state = subprocess.call(
                    [bat_file.name, branch.name, remote.name]
                )

                # Clean up file
                os.remove(bat_file.name)
            else:
                # Run log_hook via 'shell -c'
                state = subprocess.call(
                    [log_hook, 'git-up', branch.name, remote.name],
                    shell=True
                )

            if self.testing:
                assert state == 0, 'log_hook returned != 0'

    def version_info(self):
        """ Tell, what version we're running at and if it's up to date. """

        # Retrive and show local version info
        package = pkg.get_distribution('git-up')
        local_version_str = package.version
        local_version = package.parsed_version

        print('GitUp version is: ' + colored('v' + local_version_str, 'green'))

        if not self.settings['updates.check']:
            return

        # Check for updates
        print('Checking for updates...', end='')

        try:
            # Get version information from the PyPI JSON API
            details = json.load(urllib2.urlopen(PYPI_URL))
            online_version = details['info']['version']
        except (urllib2.HTTPError, urllib2.URLError, ValueError):
            recent = True  # To not disturb the user with HTTP/parsing errors
        else:
            recent = local_version >= pkg.parse_version(online_version)

        if not recent:
            #noinspection PyUnboundLocalVariable
            print(
                '\rRecent version is: '
                + colored('v' + online_version, color='yellow', attrs=['bold'])
            )
            print('Run \'pip install -U git-up\' to get the update.')
        else:
            # Clear the update line
            sys.stdout.write('\r' + ' ' * 80 + '\n')

    ###########################################################################
    # Helpers
    ###########################################################################

    @contextmanager
    def returning_to_current_branch(self):
        """ A contextmanager returning to the current branch. """
        if self.repo.head.is_detached:
            raise GitError("You're not currently on a branch. I'm exiting"
                           " in case you're in the middle of something.")

        branch_name = self.repo.active_branch.name

        yield

        if (
                self.repo.head.is_detached  # Only on Travis CI,
                # we get a detached head after doing our rebase *confused*.
                # Running self.repo.active_branch would fail.
            or
                not self.repo.active_branch.name == branch_name
        ):
            print(colored('returning to {0}'.format(branch_name), 'magenta'))
            self.git.checkout(branch_name)

    def load_config(self):
        """
        Load the configuration from git config.
        """
        for key in self.settings:
            value = self.config(key)
            # Parse true/false
            if value == '' or value is None:
                continue  # Not set by user, go on
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value:
                pass  # A user-defined string, store the value later

            self.settings[key] = value

    def config(self, key):
        """ Get a git-up-specific config value. """
        return self.git.config('git-up.{0}'.format(key))

    def is_prune(self):
        """
        Return True, if `git fetch --prune` is allowed.

        Because of possible incompatibilities, this requires special
        treatment.
        """
        required_version = "1.6.6"
        config_value = self.settings['fetch.prune']

        if self.git.is_version_min(required_version):
            return config_value is not False
        else:
            if config_value == 'true':
                print(colored(
                    "Warning: fetch.prune is set to 'true' but your git"
                    "version doesn't seem to support it ({0} < {1})."
                    "Defaulting to 'false'.".format(self.git.version,
                                                    required_version),
                    'yellow'
                ))

    ###########################################################################
    # Gemfile Checking
    ###########################################################################

    def with_bundler(self):
        """
        Check, if bundler check is requested.

        Check, if the user wants us to check for new gems and return True in
        this case.
        :rtype : bool
        """
        def gemfile_exists():
            """
            Check, if a Gemfile exists in the current repo.
            """
            return os.path.exists('Gemfile')

        if 'GIT_UP_BUNDLER_CHECK' in os.environ:
            print(colored(
                '''The GIT_UP_BUNDLER_CHECK environment variable is deprecated.
You can now tell git-up to check (or not check) for missing
gems on a per-project basis using git's config system. To
set it globally, run this command anywhere:

git config --global git-up.bundler.check true

To set it within a project, run this command inside that
project's directory:

git config git-up.bundler.check true

Replace 'true' with 'false' to disable checking.''', 'yellow'))

        if self.settings['bundler.check']:
            return gemfile_exists()

        if ('GIT_UP_BUNDLER_CHECK' in os.environ
                and os.environ['GIT_UP_BUNDLER_CHECK'] == 'true'):
            return gemfile_exists()

        return False

    def check_bundler(self):
        """
        Run the bundler check.
        """
        def get_config(name):
            return name if self.config('bundler.' + name) else ''

        from pkg_resources import Requirement, resource_filename
        relative_path = os.path.join('PyGitUp', 'check-bundler.rb')
        bundler_script = resource_filename(Requirement.parse('git-up'),
                                           relative_path)
        assert os.path.exists(bundler_script), 'check-bundler.rb doesn\'t ' \
                                               'exist!'

        return_value = subprocess.call(
            ['ruby', bundler_script, get_config('autoinstall'),
             get_config('local'), get_config('rbenv')]
        )

        if self.testing:
            assert return_value == 0, 'Errors while executing check-bundler.rb'

    def print_error(self, error):
        """
        Print more information about an error.

        :type error: GitError
        """
        print(colored(error.message, 'red'), file=self.stderr)

        if error.stdout or error.stderr:
            print(file=self.stderr)
            print("Here's what git said:", file=self.stderr)
            print(file=self.stderr)

            if error.stdout:
                print(error.stdout, file=self.stderr)
            if error.stderr:
                print(error.stderr, file=self.stderr)

        if error.details:
            print(file=self.stderr)
            print("Here's what we know:", file=self.stderr)
            print(str(error.details), file=self.stderr)
            print(file=self.stderr)

###############################################################################


def run():
    arguments = docopt(__doc__, ['up'] + sys.argv[1:])
    if arguments['--version']:
        if NO_DISTRIBUTE:
            print(colored('Please install \'git-up\' via pip in order to '
                          'get version information.', 'yellow'))
        else:
            GitUp(sparse=True).version_info()
    else:
        if arguments['--quiet']:
            sys.stdout = StringIO()

        try:
            gitup = GitUp()
        except GitError:
            sys.exit(1)  # Error in constructor
        else:
            gitup.run()

if __name__ == '__main__':
    run()

########NEW FILE########
__FILENAME__ = git_wrapper
# coding=utf-8
"""
A wrapper extending GitPython's repo.git.

This wrapper class provides support for stdout messages in Git Exceptions
and (nearly) realtime stdout output. In addition, some methods of the
original repo.git are shadowed by custom methods providing functionality
needed for `git up`.
"""

from __future__ import print_function

__all__ = ['GitWrapper', 'GitError']

###############################################################################
# IMPORTS
###############################################################################

# Python libs
import sys
import re
import subprocess
import platform
from contextlib import contextmanager

# 3rd party libs
from termcolor import colored  # Assume, colorama is already initialized
from git import GitCommandError, CheckoutError as OrigCheckoutError, Git

# PyGitUp libs
from PyGitUp.utils import find


###############################################################################
# GitWrapper
###############################################################################

class GitWrapper(object):
    """
    A wrapper for repo.git providing better stdout handling + better exeptions.

    It is preferred to repo.git because it doesn't print to stdout
    in real time. In addition, this wrapper provides better error
    handling (it provides stdout messages inside the exception, too).
    """

    def __init__(self, repo):
        if repo:
            #: :type: git.Repo
            self.repo = repo
            #: :type: git.Git
            self.git = self.repo.git
        else:
            #: :type: git.Git
            self.git = Git()

    def __del__(self):
        # Is the following true?

        # GitPython runs persistent git processes in  the working directory.
        # Therefore, when we use 'git up' in something like a test environment,
        # this might cause troubles because of the open file handlers (like
        # trying to remove the directory right after the test has finished).
        # 'clear_cache' kills the processes...

        if platform.system() == 'Windows':
            pass
            # ... or rather "should kill", because but somehow it recently
            # started to not kill cat_file_header out of the blue (I even
            # tried running old code, but the once working code failed).
            # Thus, we kill it  manually here.
            if self.git.cat_file_header is not None:
                subprocess.call(("TASKKILL /F /T /PID {0} 2>nul 1>nul".format(
                    str(self.git.cat_file_header.proc.pid)
                )), shell=True)
            if self.git.cat_file_all is not None:
                subprocess.call(("TASKKILL /F /T /PID {0} 2>nul 1>nul".format(
                    str(self.git.cat_file_all.proc.pid)
                )), shell=True)

        self.git.clear_cache()

    def run(self, name, *args, **kwargs):
        """ Run a git command specified by name and args/kwargs. """

        tostdout = kwargs.pop('tostdout', False)
        stdout = ''

        # Execute command
        cmd = getattr(self.git, name)(as_process=True, *args, **kwargs)

        # Capture output
        while True:
            output = cmd.stdout.read(1)

            # Print to stdout
            if tostdout:
                sys.stdout.write(output)
                sys.stdout.flush()

            stdout += output

            if output == "":
                break

        # Wait for the process to quit
        try:
            cmd.wait()
        except GitCommandError as error:
            # Add more meta-information to errors
            message = "'{0}' returned exit status {1}".format(
                ' '.join(str(c) for c in error.command),
                error.status
            )

            raise GitError(message, stderr=error.stderr, stdout=stdout)

        return stdout.strip()

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.run(name, *args, **kwargs)

    ###########################################################################
    # Overwrite some methods and add new ones
    ###########################################################################

    @contextmanager
    def stash(self):
        """
        A stashing contextmanager.
        It  stashes all changes inside and unstashed when done.
        """
        stashed = False

        if self.repo.is_dirty():
            if self.change_count > 1:
                message = 'stashing {0} changes'
            else:
                message = 'stashing {0} change'
            print(colored(
                message.format(self.change_count),
                'magenta'
            ))
            self.git.stash()
            stashed = True

        yield

        if stashed:
            print(colored('unstashing', 'magenta'))
            try:
                self.run('stash', 'pop')
            except GitError as e:
                raise UnstashError(stderr=e.stderr, stdout=e.stdout)

    def checkout(self, branch_name):
        """ Checkout a branch by name. """
        try:
            find(
                self.repo.branches, lambda b: b.name == branch_name
            ).checkout()
        except OrigCheckoutError as e:
            raise CheckoutError(branch_name, details=e)

    def rebase(self, target_branch):
        """ Rebase to target branch. """
        current_branch = self.repo.active_branch

        arguments = (
            ([self.config('git-up.rebase.arguments')] or []) +
            [target_branch.name]
        )
        try:
            self.run('rebase', *arguments)
        except GitError as e:
            raise RebaseError(current_branch.name, target_branch.name,
                              **e.__dict__)

    def config(self, key):
        """ Return `git config key` output or None. """
        try:
            return self.git.config(key)
        except GitCommandError:
            return None

    @property
    def change_count(self):
        """ The number of changes in the working directory. """
        return len(
            self.git.status(porcelain=True, untracked_files='no').split(
                '\n')
        )

    @property
    def version(self):
        """
        Return git's version as a list of numbers.

        The original repo.git.version_info has problems with tome types of
        git version strings.
        """
        return re.search(r'\d+(\.\d+)+', self.git.version()).group(0)

    def is_version_min(self, required_version):
        """ Does git's version match the requirements? """
        return self.version.split('.') >= required_version.split('.')


###############################################################################
# GitError + subclasses
###############################################################################

class GitError(GitCommandError):
    """
    Extension of the GitCommandError class.

    New:
    - stdout
    - details: a 'nested' exception with more details
    """

    def __init__(self, message=None, stderr=None, stdout=None, details=None):
        super(GitError, self).__init__(None, None, stderr)
        self.stdout = stdout
        self.details = details
        self.message = message

    def __str__(self):
        return self.message


class UnstashError(GitError):
    """
    Error while unstashing
    """
    def __init__(self, **kwargs):
        kwargs.pop('message', None)
        GitError.__init__(self, 'Unstash failed!', **kwargs)


class CheckoutError(GitError):
    """
    Error during checkout
    """
    def __init__(self, branch_name, **kwargs):
        kwargs.pop('message', None)
        GitError.__init__(self, 'Failed to checkout ' + branch_name,
                          **kwargs)


class RebaseError(GitError):
    """
    Error during rebase command
    """
    def __init__(self, current_branch, target_branch, **kwargs):
        # Remove kwargs we won't pass to GitError
        kwargs.pop('message', None)
        kwargs.pop('command', None)
        kwargs.pop('status', None)

        message = "Failed to rebase {1} onto {0}".format(
            current_branch, target_branch
        )
        GitError.__init__(self, message, **kwargs)

########NEW FILE########
__FILENAME__ = utils
# coding=utf-8
"""
Some simple, generic usefull methods.
"""

import os


def find(seq, test):
    """ Return first item in sequence where test(item) == True """
    for item in seq:
        if test(item):
            return item


def uniq(seq):
    """ Return a copy of seq without duplicates. """
    seen = set()
    return [x for x in seq if str(x) not in seen and not seen.add(str(x))]


def execute(cmd):
    """ Execute a command and return it's output. """
    return os.popen(cmd).readlines()[0].strip()

########NEW FILE########
__FILENAME__ = test_ahead_of_upstream
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, write_file, init_master

test_name = 'ahead-of-upstream'
testfile_name = 'file'

repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Modify file in our repo
    repo_path_file = join(path, testfile_name)
    write_file(repo_path_file, 'line 1\nline 2\ncounter: 2')
    repo.index.add([repo_path_file])
    repo.index.commit(test_name)


def test_ahead_of_upstream():
    """ Run 'git up' with result: ahead of upstream """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'ahead')

########NEW FILE########
__FILENAME__ = test_bundler
# System imports
import os
import platform
import subprocess
from os.path import join

# 3rd party libs
from nose.plugins.skip import SkipTest
from git import *

# PyGitup imports
from tests import basepath, write_file, init_master

test_name = 'bundler'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Add Gemfile
    gemfile = join(master_path, 'Gemfile')
    write_file(gemfile, "source 'https://rubygems.org'\ngem 'colored'")
    master.index.add([gemfile])
    master.index.commit(test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)
    repo.git.config('git-up.bundler.check', 'true')

    assert repo.working_dir == path


def test_bundler():
    """ Run bundler integration """
    shell = True if platform.system() == 'Windows' else False

    if os.environ.get('TRAVIS', False):
        raise SkipTest('Skip this test on Travis CI :(')

    # Helper methods
    def is_installed(prog):
        dev_null = open(os.devnull, 'wb')
        return_value = subprocess.call([prog, '--version'], shell=shell,
                                       stdout=dev_null, stderr=dev_null)
        return return_value == 0

    def get_output(cmd):
        return subprocess.check_output(cmd, shell=shell)

    # Check for ruby and bundler
    if not (is_installed('ruby') and is_installed('gem')
            and 'bundler' in get_output(['gem', 'list'])):

        # Ruby not installed, skip test
        raise SkipTest('Ruby not installed, skipped Bundler integration test')

    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

########NEW FILE########
__FILENAME__ = test_checkout_error
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from PyGitUp.git_wrapper import CheckoutError
from tests import basepath, init_master, testfile_name, wip, write_file

test_name = 'checkout_error'
second_branch = test_name + '.2'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Create second branch and add test_file.1 to index
    write_file(join(path, testfile_name + '.1'), 'contents :)')
    repo.index.add([testfile_name + '.1'])

    # Checkout first branch and add same file but untracked
    repo.git.checkout(test_name)
    write_file(join(path, testfile_name), 'content')


@wip
@raises(CheckoutError)
def test_checkout_error():
    """ Run 'git up' with checkout errors """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

########NEW FILE########
__FILENAME__ = test_detached
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master, update_file
from PyGitUp.git_wrapper import GitError

test_name = 'detached'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Modify file in master
    update_file(master, test_name)

    # Modify file in our repo
    update_file(repo, test_name)
    update_file(repo, test_name)

    # Check out parent commit
    repo.git.checkout('HEAD~')


@raises(GitError)
def test_detached():
    """ Run 'git up' with detached head """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

########NEW FILE########
__FILENAME__ = test_diverged
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master, update_file

test_name = 'diverged'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Set git-up.rebase.auto to false
    repo.git.config('git-up.rebase.auto', 'false')

    # Modify file in master
    update_file(master, test_name)

    # Modify file in our repo
    update_file(repo, test_name)


def test_diverged():
    """ Run 'git up' with result: diverged """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'diverged')

########NEW FILE########
__FILENAME__ = test_fast_forwarded
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master, update_file

test_name = 'fast-forwarded'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Modify file in master
    update_file(master, test_name)


def test_fast_forwarded():
    """ Run 'git up' with result: fast-forwarding """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'fast-forwarding')

########NEW FILE########
__FILENAME__ = test_fetchall
# System imports
import os
import contextlib
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master

test_name = 'fetch-all'
repo_path = join(basepath, test_name + os.sep)


@contextlib.contextmanager
def capture():
    import sys
    from cStringIO import StringIO
    oldout, olderr = sys.stdout, sys.stderr
    out = None
    try:
        out = [StringIO(), StringIO()]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        if out:
            out[0] = out[0].getvalue()
            out[1] = out[1].getvalue()


def setup():
    master_path, master = init_master(test_name)
    master_path2, master2 = init_master(test_name + '2')

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Configure git up
    repo.git.config('git-up.fetch.all', 'true')

    # Add second master repo to remotes
    repo.git.remote('add', test_name, master_path2)


def test_fetchall():
    """ Run 'git up' with fetch.all """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)

    with capture() as [stdout, _]:
        gitup.run()

    stdout = stdout.getvalue()

    assert_true('origin' in stdout)
    assert_true(test_name in stdout)

########NEW FILE########
__FILENAME__ = test_fetch_fail
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from PyGitUp.git_wrapper import GitError
from tests import basepath, init_master, update_file

test_name = 'test-fail'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Set remote
    repo.git.remote('set-url', 'origin', 'does-not-exist')

    # Modify file in master
    update_file(master, test_name)


@raises(GitError)
def test_fetch_fail():
    """ Run 'git up' with a non-existent remote """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

########NEW FILE########
__FILENAME__ = test_local_tracking
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *

# PyGitup imports
from tests import basepath, init_master, update_file

test_name = 'local_tracking'
repo_path = join(basepath, test_name + os.sep)


def _read_file(path):
    with open(path) as f:
        return f.read()


def setup():
    global repo_path
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Create branch with local tracking
    master.git.checkout(b=test_name + '_b', t=True)
    repo_path = master_path

    # Modify tracking branch
    master.git.checkout(test_name)
    update_file(master)


def test_local_tracking():
    """ Run 'git up' with a local tracking branch """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'fast-forwarding')

########NEW FILE########
__FILENAME__ = test_log_hook
# System imports
import os
import platform
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master, update_file

test_name = 'log-hook'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Set git-up.rebase.log-hook
    if platform.system() == 'Windows':
        repo.git.config(
            'git-up.rebase.log-hook',
            'IF [%1]==[] exit 1; '  # Note: this whole string is one line
            'IF [%2]==[] exit 1; '  # and will be split by 'git up' to
            'git log -n 1 $1 > nul; '   # multiple lines.
            'git log -n 1 $2 > nul;'
        )
    else:
        repo.git.config(
            'git-up.rebase.log-hook',
            'if [ -z "$1" -a -z "$2" ]; then exit 1; fi;'
            'git log -n 1 "$1" &> /dev/null; '
            'git log -n 1 "$2" &> /dev/null;'
        )

    # Modify file in master
    update_file(master, test_name)


def test_log_hook():
    """ Run 'git up' with log-hook"""
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'fast-forwarding')

########NEW FILE########
__FILENAME__ = test_not_on_a_git_repo
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *

# PyGitup imports
from tests import basepath
from PyGitUp.git_wrapper import GitError

test_name = 'not-on-a-repo'
repo_path = join(basepath, test_name + os.sep)


def setup():
    os.makedirs(repo_path, 0700)


@raises(GitError)
def test_not_a_git_repo():
    """ Run 'git up' being not on a git repo """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    GitUp(testing=True)

########NEW FILE########
__FILENAME__ = test_no_remotes
# System imports
import os

# 3rd party libs
from nose.tools import *

# PyGitup imports
from tests import init_master
from PyGitUp.git_wrapper import GitError

test_name = 'no_remotes'


def setup():
    global master_path
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)


@raises(GitError)
def test_no_remotes():
    """ Run 'git up' w/o remotes """
    os.chdir(master_path)

    from PyGitUp.gitup import GitUp
    GitUp(testing=True)

########NEW FILE########
__FILENAME__ = test_rebase_arguments
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, write_file, init_master, update_file, testfile_name
from PyGitUp.git_wrapper import RebaseError

test_name = 'rebase-arguments'
repo_path = join(basepath, test_name + os.sep)


def _read_file(path):
    with open(path) as f:
        return f.read()


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Modify file in master
    master_file = update_file(master, test_name)

    # Modify file in our repo
    contents = _read_file(master_file)
    contents = contents.replace('line 1', 'line x')
    repo_file = join(path, testfile_name)

    write_file(repo_file, contents)
    repo.index.add([repo_file])
    repo.index.commit(test_name)

    # Set git-up.rebase.arguments to '--abort', what results in an
    # invalid cmd and thus git returning an error, that we look for.
    repo.git.config('git-up.rebase.arguments', '--abort')


@raises(RebaseError)
def test_rebase_arguments():
    """ Run 'git up' with rebasing.arguments """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'rebasing')

########NEW FILE########
__FILENAME__ = test_rebase_error
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from PyGitUp.git_wrapper import GitError
from tests import basepath, write_file, init_master, update_file, testfile_name

test_name = 'rebase_error'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Modify file in master
    update_file(master, test_name)

    # Modify file in our repo
    contents = 'completely changed!'
    repo_file = join(path, testfile_name)

    write_file(repo_file, contents)
    repo.index.add([repo_file])
    repo.index.commit(test_name)

    # Modify file in master
    update_file(master, test_name)


@raises(GitError)
def test_rebase_error():
    """ Run 'git up' with a failing rebase """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

########NEW FILE########
__FILENAME__ = test_rebasing
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, write_file, init_master, update_file, testfile_name

test_name = 'rebasing'
repo_path = join(basepath, test_name + os.sep)


def _read_file(path):
    with open(path) as f:
        return f.read()


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Modify file in master
    master_file = update_file(master, test_name)

    # Modify file in our repo
    contents = _read_file(master_file)
    contents = contents.replace('line 1', 'line x')
    repo_file = join(path, testfile_name)

    write_file(repo_file, contents)
    repo.index.add([repo_file])
    repo.index.commit(test_name)


def test_rebasing():
    """ Run 'git up' with result: rebasing """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'rebasing')

########NEW FILE########
__FILENAME__ = test_remote_branch_deleted
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master

test_name = 'remote-branch-deleted'
new_branch_name = test_name + '.2'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Create new branch
    master.git.checkout(b=new_branch_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Checkout new branch in cloned repo
    repo.git.checkout(new_branch_name, 'origin/' + new_branch_name, b=True)

    # Remove branch from master again
    master.git.checkout(test_name)
    master.git.branch(new_branch_name, d=True)


def test_remote_branch_deleted():
    """ Run 'git up' with remotely deleted branch """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 2)
    assert_equal(gitup.states[1], 'remote branch doesn\'t exist')

########NEW FILE########
__FILENAME__ = test_returning_to_branch
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master, update_file

test_name = 'returning-to-branch'
new_branch_name = test_name + '.2'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Create a new branch in repo
    repo.git.checkout(b=new_branch_name)

    # Modify file in master
    update_file(master, test_name)


def test_returning_to_branch():
    """ Run 'git up': return to branch """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'fast-forwarding')
    assert_equal(gitup.repo.head.ref.name, new_branch_name)

########NEW FILE########
__FILENAME__ = test_tracking
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master, update_file

test_name = 'tracking'
repo_path = join(basepath, test_name + os.sep)


def _read_file(path):
    with open(path) as f:
        return f.read()


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    # Rename test repo branch
    repo.git.branch(test_name + '_renamed', m=True)

    assert repo.working_dir == path

    # Modify file in master
    update_file(master, test_name)


def test_tracking():
    """ Run 'git up' with a local tracking branch """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'fast-forwarding')

########NEW FILE########
__FILENAME__ = test_unstash_error
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from PyGitUp.git_wrapper import GitError
from tests import basepath, write_file, init_master, testfile_name

test_name = 'unstash_error'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Modify file in master
    master_path_file = join(master_path, testfile_name)
    write_file(master_path_file, 'contents')
    master.index.add([master_path_file])
    master.index.commit(test_name)

    # Modify file in repo
    path_file = join(path, testfile_name)
    os.unlink(path_file)


@raises(GitError)
def test_unstash_error():
    """ Run 'git up' with an unclean unstash """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

########NEW FILE########
__FILENAME__ = test_up_to_date
# System imports
import os
from os.path import join

# 3rd party libs
from nose.tools import *
from git import *

# PyGitup imports
from tests import basepath, init_master, update_file

test_name = 'up-to-date'
repo_path = join(basepath, test_name + os.sep)


def setup():
    master_path, master = init_master(test_name)

    # Prepare master repo
    master.git.checkout(b=test_name)

    # Clone to test repo
    path = join(basepath, test_name)

    master.clone(path, b=test_name)
    repo = Repo(path, odbt=GitCmdObjectDB)

    assert repo.working_dir == path

    # Modify file in master
    update_file(master, test_name)

    # Update repo
    repo.remotes.origin.pull()


def test_up_to_date():
    """ Run 'git up' with result: up to date """
    os.chdir(repo_path)

    from PyGitUp.gitup import GitUp
    gitup = GitUp(testing=True)
    gitup.run()

    assert_equal(len(gitup.states), 1)
    assert_equal(gitup.states[0], 'up to date')

########NEW FILE########
__FILENAME__ = test_utils
from nose.tools import *

from PyGitUp import utils


def test_find():
    assert_equal(utils.find([1, 2, 3], lambda i: i == 3), 3)
    assert_equal(utils.find([1, 2, 3], lambda i: i == 4), None)


def test_uniq():
    assert_equal(utils.uniq([1, 1, 1, 2, 3]), [1, 2, 3])
    assert_equal(utils.uniq([1]), [1])
    assert_equal(utils.uniq([]), [])

########NEW FILE########
