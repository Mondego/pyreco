__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id: bootstrap.py 102545 2009-08-06 14:49:47Z chrisw $
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser()
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=True,
                   help="Use Disribute rather than Setuptools.")

options, args = parser.parse_args()

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse(requirement)).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse(requirement)).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = base
class MissingRemote(Exception):

    """
    Raise when a remote by name is not found.

    """
    pass


class MissingMasterBranch(Exception):

    """
    Raise when the "master" branch cannot be located.

    """
    pass


class BaseOperation(object):

    """
    Base class for all Git-related operations.

    """
    def __init__(self, repo, remote_name='origin', master_branch='master'):
        self.repo = repo
        self.remote_name = remote_name
        self.master_branch = master_branch

    def _filtered_remotes(self, origin, skip=[]):
        """
        Returns a list of remote refs, skipping ones you don't need.

        If ``skip`` is empty, it will default to ``['HEAD',
        self.master_branch]``.
        """
        if not skip:
            skip = ['HEAD', self.master_branch]

        refs = [i for i in origin.refs if not i.remote_head in skip]

        return refs

    def _master_ref(self, origin):
        """
        Finds the master ref object that matches master branch.
        """
        for ref in origin.refs:
            if ref.remote_head == self.master_branch:
                return ref

        raise MissingMasterBranch(
            'Could not find ref for {0}'.format(self.master_branch))

    @property
    def _origin(self):
        """
        Gets the remote that references origin by name self.origin_name.
        """
        origin = None

        for remote in self.repo.remotes:
            if remote.name == self.remote_name:
                origin = remote

        if not origin:
            raise MissingRemote('Could not find the remote named {0}'.format(
                self.remote_name))

        return origin

########NEW FILE########
__FILENAME__ = cli
import sys
from os import getcwd
from argparse import ArgumentParser
from textwrap import dedent

from git import Repo, InvalidGitRepositoryError

from gitsweep.inspector import Inspector
from gitsweep.deleter import Deleter


class CommandLine(object):

    """
    Main interface to the command-line for running git-sweep.

    """
    parser = ArgumentParser(
        description='Clean up your Git remote branches.',
        usage='git-sweep <action> [-h]',
        )

    _sub_parsers = parser.add_subparsers(title='action',
        description='Preview changes or perform clean up')

    _origin_kwargs = {
        'help': 'The name of the remote you wish to clean up',
        'dest': 'origin',
        'default': 'origin'}

    _master_kwargs = {
        'help': 'The name of what you consider the master branch',
        'dest': 'master',
        'default': 'master'}

    _skip_kwargs = {
        'help': 'Comma-separated list of branches to skip',
        'dest': 'skips',
        'default': ''}

    _no_fetch_kwargs = {
        'help': 'Do not fetch from the remote',
        'dest': 'fetch',
        'action': 'store_false',
        'default': True}

    _preview_usage = dedent('''
        git-sweep preview [-h] [--nofetch] [--skip SKIPS]
                              [--master MASTER] [--origin ORIGIN]
        '''.strip())

    _preview = _sub_parsers.add_parser('preview',
        help='Preview the branches that will be deleted',
        usage=_preview_usage)
    _preview.add_argument('--origin', **_origin_kwargs)
    _preview.add_argument('--master', **_master_kwargs)
    _preview.add_argument('--nofetch', **_no_fetch_kwargs)
    _preview.add_argument('--skip', **_skip_kwargs)
    _preview.set_defaults(action='preview')

    _cleanup_usage = dedent('''
        git-sweep cleanup [-h] [--nofetch] [--skip SKIPS] [--force]
                              [--master MASTER] [--origin ORIGIN]
        '''.strip())

    _cleanup = _sub_parsers.add_parser('cleanup',
        help='Delete merged branches from the remote',
        usage=_cleanup_usage)
    _cleanup.add_argument('--force', action='store_true', default=False,
        dest='force', help='Do not ask, cleanup immediately')
    _cleanup.add_argument('--origin', **_origin_kwargs)
    _cleanup.add_argument('--master', **_master_kwargs)
    _cleanup.add_argument('--nofetch', **_no_fetch_kwargs)
    _cleanup.add_argument('--skip', **_skip_kwargs)
    _cleanup.set_defaults(action='cleanup')

    def __init__(self, args):
        self.args = args[1:]

    def run(self):
        """
        Runs git-sweep.
        """
        try:
            if not self.args:
                self.parser.print_help()
                sys.exit(1)

            self._sweep()

            sys.exit(0)
        except InvalidGitRepositoryError:
            sys.stdout.write('This is not a Git repository\n')
        except Exception as e:
            sys.stdout.write(str(e) + '\n')

        sys.exit(1)

    def _sweep(self):
        """
        Runs git-sweep.
        """
        args = self.parser.parse_args(self.args)

        dry_run = True if args.action == 'preview' else False
        fetch = args.fetch
        skips = [i.strip() for i in args.skips.split(',')]

        # Is this a Git repository?
        repo = Repo(getcwd())

        remote_name = args.origin

        # Fetch from the remote so that we have the latest commits
        if fetch:
            for remote in repo.remotes:
                if remote.name == remote_name:
                    sys.stdout.write('Fetching from the remote\n')
                    remote.fetch()

        master_branch = args.master

        # Find branches that could be merged
        inspector = Inspector(repo, remote_name=remote_name,
            master_branch=master_branch)
        ok_to_delete = inspector.merged_refs(skip=skips)

        if ok_to_delete:
            sys.stdout.write(
                'These branches have been merged into {0}:\n\n'.format(
                    master_branch))
        else:
            sys.stdout.write('No remote branches are available for '
                'cleaning up\n')

        for ref in ok_to_delete:
            sys.stdout.write('  {0}\n'.format(ref.remote_head))

        if not dry_run:
            deleter = Deleter(repo, remote_name=remote_name,
                master_branch=master_branch)

            if not args.force:
                sys.stdout.write('\nDelete these branches? (y/n) ')
                answer = raw_input()
            if args.force or answer.lower().startswith('y'):
                sys.stdout.write('\n')
                for ref in ok_to_delete:
                    sys.stdout.write('  deleting {0}'.format(ref.remote_head))
                    deleter.remove_remote_refs([ref])
                    sys.stdout.write(' (done)\n')

                sys.stdout.write('\nAll done!\n')
                sys.stdout.write('\nTell everyone to run `git fetch --prune` '
                    'to sync with this remote.\n')
                sys.stdout.write('(you don\'t have to, yours is synced)\n')
            else:
                sys.stdout.write('\nOK, aborting.\n')
        elif ok_to_delete:
            # Replace the first argument with cleanup
            sysv_copy = self.args[:]
            sysv_copy[0] = 'cleanup'
            command = 'git-sweep {0}'.format(' '.join(sysv_copy))

            sys.stdout.write(
                '\nTo delete them, run again with `{0}`\n'.format(command))

########NEW FILE########
__FILENAME__ = deleter
from .base import BaseOperation


class Deleter(BaseOperation):

    """
    Removes remote branches from the remote.

    """
    def remove_remote_refs(self, refs):
        """
        Removes the remote refs from the remote.

        ``refs`` should be a lit of ``git.RemoteRefs`` objects.
        """
        origin = self._origin

        pushes = []
        for ref in refs:
            pushes.append(origin.push(':{0}'.format(ref.remote_head)))

        return pushes

########NEW FILE########
__FILENAME__ = entrypoints
def main():
    """
    Command-line interface.
    """
    import sys

    from gitsweep.cli import CommandLine

    CommandLine(sys.argv).run()


def test():
    """
    Run git-sweep's test suite.
    """
    import nose

    import sys

    nose.main(argv=['nose'] + sys.argv[1:])

########NEW FILE########
__FILENAME__ = inspector
from git import Git

from .base import BaseOperation


class Inspector(BaseOperation):

    """
    Used to introspect a Git repository.

    """
    def merged_refs(self, skip=[]):
        """
        Returns a list of remote refs that have been merged into the master
        branch.

        The "master" branch may have a different name than master. The value of
        ``self.master_name`` is used to determine what this name is.
        """
        origin = self._origin

        master = self._master_ref(origin)
        refs = self._filtered_remotes(
            origin, skip=['HEAD', self.master_branch] + skip)
        merged = []

        for ref in refs:
            upstream = '{origin}/{master}'.format(
                origin=origin.name, master=master.remote_head)
            head = '{origin}/{branch}'.format(
                origin=origin.name, branch=ref.remote_head)
            cmd = Git(self.repo.working_dir)
            # Drop to the git binary to do this, it's just easier to work with
            # at this level.
            (retcode, stdout, stderr) = cmd.execute(
                ['git', 'cherry', upstream, head],
                with_extended_output=True, with_exceptions=False)
            if retcode == 0 and not stdout:
                # This means there are no commits in the branch that are not
                # also in the master branch. This is ready to be deleted.
                merged.append(ref)

        return merged

########NEW FILE########
__FILENAME__ = test
from gitsweep.entrypoints import test

__test__ = False

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = testcases
import sys
from os import chdir, getcwd
from os.path import join, basename
from tempfile import mkdtemp
from unittest import TestCase
from uuid import uuid4 as uuid
from shutil import rmtree
from shlex import split
from contextlib import contextmanager, nested
from textwrap import dedent

from mock import patch
from git import Repo
from git.cmd import Git

from gitsweep.inspector import Inspector
from gitsweep.deleter import Deleter
from gitsweep.cli import CommandLine


@contextmanager
def cwd_bounce(dir):
    """
    Temporarily changes to a directory and changes back in the end.

    Where ``dir`` is the directory you wish to change to. When the context
    manager exits it will change back to the original working directory.

    Context manager will yield the original working directory and make that
    available to the context manager's assignment target.
    """
    original_dir = getcwd()

    try:
        chdir(dir)

        yield original_dir
    finally:
        chdir(original_dir)


class GitSweepTestCase(TestCase):

    """
    Sets up a Git repository and provides some command to manipulate it.

    """
    def setUp(self):
        """
        Sets up the Git repository for testing.

        The following will be available after :py:method`setUp()` runs.

        self.repodir
            The absolute filename of the Git repository

        self.repo
            A ``git.Repo`` object for self.repodir

        This will create the root commit in the test repository automaticall.
        """
        super(GitSweepTestCase, self).setUp()

        repodir = mkdtemp()

        self.repodir = repodir
        self.repo = Repo.init(repodir)

        rootcommit_filename = join(repodir, 'rootcommit')

        with open(rootcommit_filename, 'w') as fh:
            fh.write('')

        self.repo.index.add([basename(rootcommit_filename)])
        self.repo.index.commit('Root commit')

        # Cache the remote per test
        self._remote = None

        # Keep track of cloned repositories that track self.repo
        self._clone_dirs = []

    def tearDown(self):
        """
        Remove any created repositories.
        """
        rmtree(self.repodir)

        for clone in self._clone_dirs:
            rmtree(clone)

    def assertResults(self, expected, actual):
        """
        Assert that output matches expected argument.
        """
        expected = dedent(expected).strip()

        actual = actual.strip()

        self.assertEqual(expected, actual)

    def command(self, command):
        """
        Runs the Git command in self.repo
        """
        args = split(command)

        cmd = Git(self.repodir)

        cmd.execute(args)

    @property
    def remote(self):
        """
        Clones the test case's repository and tracks it as a remote.

        Returns a ``git.Repo`` object.
        """
        if not self._remote:
            clonedir = mkdtemp()
            self._clone_dirs.append(clonedir)

            self._remote = Repo.clone(self.repo, clonedir)

        # Update in case the remote has changed
        self._remote.remotes[0].pull()
        return self._remote

    def graph(self):
        """
        Prints a graph of the git log.

        This is used for testing and debugging only.
        """
        sys.stdout.write(Git(self.repodir).execute(
            ['git', 'log', '--graph', '--oneline']))

    def make_commit(self):
        """
        Makes a random commit in the current branch.
        """
        fragment = uuid().hex[:8]
        filename = join(self.repodir, fragment)
        with open(filename, 'w') as fh:
            fh.write(uuid().hex)

        self.repo.index.add([basename(filename)])
        self.repo.index.commit('Adding {0}'.format(basename(filename)))


class InspectorTestCase(TestCase):

    """
    Creates an Inspector object for testing.

    """
    def setUp(self):
        super(InspectorTestCase, self).setUp()

        self._inspector = None

    @property
    def inspector(self):
        """
        Return and optionally create an Inspector from self.remote.
        """
        if not self._inspector:
            self._inspector = Inspector(self.remote)

        return self._inspector

    def merged_refs(self, refobjs=False):
        """
        Get a list of branch names from merged refs from self.inspector.

        By default, it returns a list of branch names. You can return the
        actual ``git.RemoteRef`` objects by passing ``refobjs=True``.
        """
        refs = self.inspector.merged_refs()

        if refobjs:
            return refs

        return [i.remote_head for i in refs]


class DeleterTestCase(TestCase):

    """
    Creates a Deleter object for testing.

    """
    def setUp(self):
        super(DeleterTestCase, self).setUp()

        self._deleter = None

    @property
    def deleter(self):
        """
        Return and optionally create a Deleter from self.remote.
        """
        if not self._deleter:
            self._deleter = Deleter(self.remote)

        return self._deleter


class CommandTestCase(GitSweepTestCase, InspectorTestCase, DeleterTestCase):

    """
    Used to test the command-line interface.

    """
    def setUp(self):
        super(CommandTestCase, self).setUp()

        self._commandline = None
        self._original_dir = getcwd()

        # Change the working directory to our clone
        chdir(self.remote.working_dir)

    def tearDown(self):
        """
        Change back to the original directory.
        """
        chdir(self._original_dir)

    @property
    def cli(self):
        """
        Return and optionally create a CommandLine object.
        """
        if not self._commandline:
            self._commandline = CommandLine([])

        return self._commandline

    def gscommand(self, command):
        """
        Runs the command with the given args.
        """
        args = split(command)

        self.cli.args = args[1:]

        patches = (
            patch.object(sys, 'stdout'),
            patch.object(sys, 'stderr'))

        with nested(*patches):
            stdout = sys.stdout
            stderr = sys.stderr
            try:
                self.cli.run()
            except SystemExit as se:
                pass

        stdout = ''.join([i[0][0] for i in stdout.write.call_args_list])
        stderr = ''.join([i[0][0] for i in stderr.write.call_args_list])

        return (se.code, stdout, stderr)

########NEW FILE########
__FILENAME__ = test_cli
from mock import patch

from gitsweep.tests.testcases import CommandTestCase


class TestHelpMenu(CommandTestCase):

    """
    Command-line tool can show the help menu.

    """
    def test_help(self):
        """
        If no arguments are given the help menu is displayed.
        """
        (retcode, stdout, stderr) = self.gscommand('git-sweep -h')

        self.assertResults('''
            usage: git-sweep <action> [-h]

            Clean up your Git remote branches.

            optional arguments:
              -h, --help         show this help message and exit

            action:
              Preview changes or perform clean up

              {preview,cleanup}
                preview          Preview the branches that will be deleted
                cleanup          Delete merged branches from the remote
            ''', stdout)

    def test_fetch(self):
        """
        Will fetch if told not to.
        """
        (retcode, stdout, stderr) = self.gscommand('git-sweep preview')

        self.assertResults('''
            Fetching from the remote
            No remote branches are available for cleaning up
            ''', stdout)

    def test_no_fetch(self):
        """
        Will not fetch if told not to.
        """
        (retcode, stdout, stderr) = self.gscommand(
            'git-sweep preview --nofetch')

        self.assertResults('''
            No remote branches are available for cleaning up
            ''', stdout)

    def test_will_preview(self):
        """
        Will preview the proposed deletes.
        """
        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')
            self.make_commit()
            self.command('git merge branch{0}'.format(i))

        (retcode, stdout, stderr) = self.gscommand('git-sweep preview')

        self.assertResults('''
            Fetching from the remote
            These branches have been merged into master:

              branch1
              branch2
              branch3
              branch4
              branch5

            To delete them, run again with `git-sweep cleanup`
            ''', stdout)

    def test_will_preserve_arguments(self):
        """
        The recommended cleanup command contains the same arguments given.
        """
        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')
            self.make_commit()
            self.command('git merge branch{0}'.format(i))

        preview = 'git-sweep preview --master=master --origin=origin'
        cleanup = 'git-sweep cleanup --master=master --origin=origin'

        (retcode, stdout, stderr) = self.gscommand(preview)

        self.assertResults('''
            Fetching from the remote
            These branches have been merged into master:

              branch1
              branch2
              branch3
              branch4
              branch5

            To delete them, run again with `{0}`
            '''.format(cleanup), stdout)

    def test_will_preview_none_found(self):
        """
        Will preview the proposed deletes.
        """
        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')

        (retcode, stdout, stderr) = self.gscommand('git-sweep preview')

        self.assertResults('''
            Fetching from the remote
            No remote branches are available for cleaning up
            ''', stdout)

    def test_will_cleanup(self):
        """
        Will preview the proposed deletes.
        """
        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')
            self.make_commit()
            self.command('git merge branch{0}'.format(i))

        with patch('gitsweep.cli.raw_input', create=True) as ri:
            ri.return_value = 'y'
            (retcode, stdout, stderr) = self.gscommand('git-sweep cleanup')

        self.assertResults('''
            Fetching from the remote
            These branches have been merged into master:

              branch1
              branch2
              branch3
              branch4
              branch5

            Delete these branches? (y/n) 
              deleting branch1 (done)
              deleting branch2 (done)
              deleting branch3 (done)
              deleting branch4 (done)
              deleting branch5 (done)

            All done!

            Tell everyone to run `git fetch --prune` to sync with this remote.
            (you don't have to, yours is synced)
            ''', stdout)

    def test_will_abort_cleanup(self):
        """
        Will preview the proposed deletes.
        """
        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')
            self.make_commit()
            self.command('git merge branch{0}'.format(i))

        with patch('gitsweep.cli.raw_input', create=True) as ri:
            ri.return_value = 'n'
            (retcode, stdout, stderr) = self.gscommand('git-sweep cleanup')

        self.assertResults('''
            Fetching from the remote
            These branches have been merged into master:

              branch1
              branch2
              branch3
              branch4
              branch5

            Delete these branches? (y/n) 
            OK, aborting.
            ''', stdout)

    def test_will_skip_certain_branches(self):
        """
        Can be forced to skip certain branches.
        """
        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')
            self.make_commit()
            self.command('git merge branch{0}'.format(i))

        (retcode, stdout, stderr) = self.gscommand(
            'git-sweep preview --skip=branch1,branch2')

        cleanup = 'git-sweep cleanup --skip=branch1,branch2'

        self.assertResults('''
            Fetching from the remote
            These branches have been merged into master:

              branch3
              branch4
              branch5

            To delete them, run again with `{0}`
            '''.format(cleanup), stdout)

    def test_will_force_clean(self):
        """
        Will cleanup immediately if forced.
        """
        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')
            self.make_commit()
            self.command('git merge branch{0}'.format(i))

        (retcode, stdout, stderr) = self.gscommand('git-sweep cleanup --force')

        self.assertResults('''
            Fetching from the remote
            These branches have been merged into master:

              branch1
              branch2
              branch3
              branch4
              branch5

              deleting branch1 (done)
              deleting branch2 (done)
              deleting branch3 (done)
              deleting branch4 (done)
              deleting branch5 (done)

            All done!

            Tell everyone to run `git fetch --prune` to sync with this remote.
            (you don't have to, yours is synced)
            ''', stdout)

########NEW FILE########
__FILENAME__ = test_deleter
from gitsweep.tests.testcases import (GitSweepTestCase, InspectorTestCase,
    DeleterTestCase)


class TestDeleter(GitSweepTestCase, InspectorTestCase, DeleterTestCase):

    """
    Can delete remote refs from a remote.

    """
    def setUp(self):
        super(TestDeleter, self).setUp()

        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')
            self.make_commit()
            self.command('git merge branch{0}'.format(i))

    def test_will_delete_merged_from_clone(self):
        """
        Given a list of refs, will delete them from cloned repo.

        This test looks at our cloned repository, the one which is setup to
        track the remote and makes sure that the changes occur on it as
        expected.
        """
        clone = self.remote.remotes[0]

        # Grab all the remote branches
        before = [i.remote_head for i in clone.refs]
        # We should have 5 branches plus HEAD and master
        self.assertEqual(7, len(before))

        # Delete from the remote through the clone
        pushes = self.deleter.remove_remote_refs(
            self.merged_refs(refobjs=True))

        # Make sure it removed the expected number
        self.assertEqual(5, len(pushes))

        # Grab all the remote branches again
        after = [i.remote_head for i in clone.refs]
        after.sort()

        # We should be down to 2, HEAD and master
        self.assertEqual(['HEAD', 'master'], after)

    def test_will_delete_merged_on_remote(self):
        """
        With the list of refs, will delete these from the remote.

        This test makes assertion against the remote, not the clone repository.
        We are testing to see if the interactions in the cloned repo are pushed
        through to the remote.

        Note that accessing the repository directly does not include the
        symbolic reference of HEAD.
        """
        remote = self.repo

        # Get a list of branches on this remote
        before = [i.name for i in remote.refs]
        # Should be 5 branches + master
        self.assertEqual(6, len(before))

        # Delete through the clone which pushes to this remote
        pushes = self.deleter.remove_remote_refs(
            self.merged_refs(refobjs=True))

        # Make sure it removed the expected number
        self.assertEqual(5, len(pushes))

        # Grab again
        after = [i.name for i in remote.refs]
        # Should be down to just master
        self.assertEqual(['master'], after)

########NEW FILE########
__FILENAME__ = test_inspector
from gitsweep.tests.testcases import GitSweepTestCase, InspectorTestCase


class TestInspector(GitSweepTestCase, InspectorTestCase):

    """
    Inspector can find merged branches and present them for cleaning.

    """
    def test_no_branches(self):
        """
        If only the master branch is present, nothing to clean.
        """
        self.assertEqual([], self.inspector.merged_refs())

    def test_filtered_refs(self):
        """
        Will filter references and not return HEAD and master.
        """
        for i in range(1, 4):
            self.command('git checkout -b branch{0}'.format(i))
            self.command('git checkout master')

        refs = self.inspector._filtered_remotes(
            self.inspector.repo.remotes[0])

        self.assertEqual(['branch1', 'branch2', 'branch3'],
            [i.remote_head for i in refs])

    def test_one_branch_no_commits(self):
        """
        There is one branch on the remote that is the same as master.
        """
        self.command('git checkout -b branch1')
        self.command('git checkout master')

        # Since this is the same as master, it should show up as merged
        self.assertEqual(['branch1'], self.merged_refs())

    def test_one_branch_one_commit(self):
        """
        A commit has been made in the branch so it's not safe to remove.
        """
        self.command('git checkout -b branch1')

        self.make_commit()

        self.command('git checkout master')

        # Since there is a commit in branch1, it's not safe to remove it
        self.assertEqual([], self.merged_refs())

    def test_one_merged_branch(self):
        """
        If a branch has been merged, it's safe to delete it.
        """
        self.command('git checkout -b branch1')

        self.make_commit()

        self.command('git checkout master')

        self.command('git merge branch1')

        self.assertEqual(['branch1'], self.merged_refs())

    def test_commit_in_master(self):
        """
        Commits in master not in the branch do not block it for deletion.
        """
        self.command('git checkout -b branch1')

        self.make_commit()

        self.command('git checkout master')

        self.make_commit()

        self.command('git merge branch1')

        self.assertEqual(['branch1'], self.merged_refs())

    def test_large_set_of_changes(self):
        r"""
        A long list of changes is properly marked for deletion.

        The branch history for this will look like this:

        ::

            |\
            | * 08d07e1 Adding 4e510716
            * | 056abb2 Adding a0dfc9fb
            |/
            *   9d77626 Merge branch 'branch4'
            |\
            | * 956b3f9 Adding e16ec279
            * | d11315e Adding 9571d55d
            |/
            *   f100932 Merge branch 'branch3'
            |\
            | * c641899 Adding 9b33164f
            * | 17c1e35 Adding b56c43be
            |/
            *   c83c8d3 Merge branch 'branch2'
            |\
            | * bead4e5 Adding 31a13fa4
            * | 5a88ec3 Adding b6a45f21
            |/
            *   f34643d Merge branch 'branch1'
            |\
            | * 8e110c4 Adding 11948eb5
            * | 4c94394 Adding db29f4aa
            |/
        """
        for i in range(1, 6):
            self.command('git checkout -b branch{0}'.format(i))
            self.make_commit()
            self.command('git checkout master')
            self.make_commit()
            self.command('git merge branch{0}'.format(i))

        self.assertEqual(
            ['branch1', 'branch2', 'branch3', 'branch4', 'branch5'],
            self.merged_refs())

########NEW FILE########
