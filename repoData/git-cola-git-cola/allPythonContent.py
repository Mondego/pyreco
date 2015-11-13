__FILENAME__ = app
# Copyright (C) 2009, 2010, 2011, 2012, 2013
# David Aguilar <davvid@gmail.com>
"""Provides the main() routine and ColaApplicaiton"""
from __future__ import division, absolute_import, unicode_literals

import argparse
import glob
import os
import signal
import sys

# Make homebrew work by default
if sys.platform == 'darwin':
    from distutils import sysconfig
    python_version = sysconfig.get_python_version()
    homebrew_mods = '/usr/local/lib/python%s/site-packages' % python_version
    if os.path.isdir(homebrew_mods):
        sys.path.append(homebrew_mods)

import sip
sip.setapi('QString', 1)
sip.setapi('QDate', 1)
sip.setapi('QDateTime', 1)
sip.setapi('QTextStream', 1)
sip.setapi('QTime', 1)
sip.setapi('QUrl', 1)
sip.setapi('QVariant', 1)

try:
    from PyQt4 import QtGui
    from PyQt4 import QtCore
    from PyQt4.QtCore import SIGNAL
except ImportError:
    sys.stderr.write('Sorry, you do not seem to have PyQt4 installed.\n')
    sys.stderr.write('Please install it before using git-cola.\n')
    sys.stderr.write('e.g.: sudo apt-get install python-qt4\n')
    sys.exit(-1)

# Import cola modules
from cola import cmds
from cola import core
from cola import compat
from cola import git
from cola import inotify
from cola import i18n
from cola import qtcompat
from cola import qtutils
from cola import resources
from cola import utils
from cola import version
from cola.compat import ustr
from cola.decorators import memoize
from cola.interaction import Interaction
from cola.models import main
from cola.widgets import cfgactions
from cola.widgets import startup
from cola.settings import Session


def setup_environment():
    # Allow Ctrl-C to exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Session management wants an absolute path when restarting
    sys.argv[0] = core.abspath(sys.argv[0])

    # Spoof an X11 display for SSH
    os.environ.setdefault('DISPLAY', ':0')

    if not core.getenv('SHELL', ''):
        for shell in ('/bin/zsh', '/bin/bash', '/bin/sh'):
            if os.path.exists(shell):
                compat.setenv('SHELL', shell)
                break

    # Setup the path so that git finds us when we run 'git cola'
    path_entries = core.getenv('PATH', '').split(os.pathsep)
    bindir = os.path.dirname(core.abspath(__file__))
    path_entries.insert(0, bindir)
    path = os.pathsep.join(path_entries)
    compat.setenv('PATH', path)

    # We don't ever want a pager
    compat.setenv('GIT_PAGER', '')

    # Setup *SSH_ASKPASS
    git_askpass = core.getenv('GIT_ASKPASS')
    ssh_askpass = core.getenv('SSH_ASKPASS')
    if git_askpass:
        askpass = git_askpass
    elif ssh_askpass:
        askpass = ssh_askpass
    elif sys.platform == 'darwin':
        askpass = resources.share('bin', 'ssh-askpass-darwin')
    else:
        askpass = resources.share('bin', 'ssh-askpass')

    compat.setenv('GIT_ASKPASS', askpass)
    compat.setenv('SSH_ASKPASS', askpass)

    # --- >8 --- >8 ---
    # Git v1.7.10 Release Notes
    # =========================
    #
    # Compatibility Notes
    # -------------------
    #
    #  * From this release on, the "git merge" command in an interactive
    #   session will start an editor when it automatically resolves the
    #   merge for the user to explain the resulting commit, just like the
    #   "git commit" command does when it wasn't given a commit message.
    #
    #   If you have a script that runs "git merge" and keeps its standard
    #   input and output attached to the user's terminal, and if you do not
    #   want the user to explain the resulting merge commits, you can
    #   export GIT_MERGE_AUTOEDIT environment variable set to "no", like
    #   this:
    #
    #        #!/bin/sh
    #        GIT_MERGE_AUTOEDIT=no
    #        export GIT_MERGE_AUTOEDIT
    #
    #   to disable this behavior (if you want your users to explain their
    #   merge commits, you do not have to do anything).  Alternatively, you
    #   can give the "--no-edit" option to individual invocations of the
    #   "git merge" command if you know everybody who uses your script has
    #   Git v1.7.8 or newer.
    # --- >8 --- >8 ---
    # Longer-term: Use `git merge --no-commit` so that we always
    # have a chance to explain our merges.
    compat.setenv('GIT_MERGE_AUTOEDIT', 'no')


# style note: we use camelCase here since we're masquerading a Qt class
class ColaApplication(object):
    """The main cola application

    ColaApplication handles i18n of user-visible data
    """

    def __init__(self, argv, locale=None, gui=True, git_path=None):
        cfgactions.install()
        i18n.install(locale)
        qtcompat.install()
        qtutils.install()

        # Call _update_files when inotify detects changes
        inotify.observer(_update_files)

        # Add the default style dir so that we find our icons
        icon_dir = resources.icon_dir()
        qtcompat.add_search_path(os.path.basename(icon_dir), icon_dir)

        if gui:
            self._app = instance(tuple(argv), git_path)
            self._app.setWindowIcon(qtutils.git_icon())
        else:
            self._app = QtCore.QCoreApplication(argv)

        self._app.setStyleSheet("""
            QMainWindow::separator {
                width: 3px;
                height: 3px;
            }
            QMainWindow::separator:hover {
                background: white;
            }
            """)

    def activeWindow(self):
        """Wrap activeWindow()"""
        return self._app.activeWindow()

    def desktop(self):
        return self._app.desktop()

    def exec_(self):
        """Wrap exec_()"""
        return self._app.exec_()

    def set_view(self, view):
        if hasattr(self._app, 'view'):
            self._app.view = view


@memoize
def instance(argv, git_path=None):
    return ColaQApplication(list(argv), git_path)


class ColaQApplication(QtGui.QApplication):

    def __init__(self, argv, git_path=None):
        QtGui.QApplication.__init__(self, argv)
        self.git_path = git_path
        self.view = None ## injected by application_start()

    def commitData(self, session_mgr):
        """Save session data"""
        if self.view is None:
            return
        sid = ustr(session_mgr.sessionId())
        skey = ustr(session_mgr.sessionKey())
        session_id = '%s_%s' % (sid, skey)
        session = Session(session_id,
                          repo=os.getcwdu(), git_path=self.git_path)
        self.view.save_state(settings=session)


def process_args(args):
    if args.version:
        # Accept 'git cola --version' or 'git cola version'
        version.print_version()
        sys.exit(0)

    # Handle session management
    restore_session(args)

    if args.git_path:
        # Adds git to the PATH.  This is needed on Windows.
        path_entries = core.getenv('PATH', '').split(os.pathsep)
        path_entries.insert(0, os.path.dirname(core.decode(args.git_path)))
        compat.setenv('PATH', os.pathsep.join(path_entries))

    # Bail out if --repo is not a directory
    repo = core.decode(args.repo)
    if repo.startswith('file:'):
        repo = repo[len('file:'):]
    repo = core.realpath(repo)
    if not core.isdir(repo):
        sys.stderr.write("fatal: '%s' is not a directory.  "
                         'Consider supplying -r <path>.\n' % repo)
        sys.exit(-1)

    # We do everything relative to the repo root
    os.chdir(args.repo)
    return repo


def restore_session(args):
    # args.settings is provided when restoring from a session.
    args.settings = None
    if args.session is None:
        return
    session = Session(args.session)
    if session.load():
        args.settings = session
        args.repo = session.repo
        args.git_path = session.git_path


def application_init(args, update=False):
    """Parses the command-line arguments and starts git-cola
    """
    # Ensure that we're working in a valid git repository.
    # If not, try to find one.  When found, chdir there.
    setup_environment()
    process_args(args)

    app = new_application(args)
    model = new_model(app, args.repo, prompt=args.prompt)
    if update:
        model.update_status()
    return ApplicationContext(args, app, model)


def application_start(context, view):
    """Show the GUI and start the main event loop"""
    # Store the view for session management
    context.app.set_view(view)

    # Make sure that we start out on top
    view.show()
    view.raise_()

    # Scan for the first time
    task = _start_update_thread(context.model)

    # Start the inotify thread
    inotify.start()

    msg_timer = QtCore.QTimer()
    msg_timer.setSingleShot(True)
    msg_timer.connect(msg_timer, SIGNAL('timeout()'), _send_msg)
    msg_timer.start(0)

    # Start the event loop
    result = context.app.exec_()

    # All done, cleanup
    inotify.stop()
    QtCore.QThreadPool.globalInstance().waitForDone()
    del task

    pattern = utils.tmp_file_pattern()
    for filename in glob.glob(pattern):
        os.unlink(filename)

    return result


def add_common_arguments(parser):
    # We also accept 'git cola version'
    parser.add_argument('--version', default=False, action='store_true',
                        help='print version number')

    # Specifies a git repository to open
    parser.add_argument('-r', '--repo', metavar='<repo>', default=os.getcwd(),
                        help='open the specified git repository')

    # Specifies that we should prompt for a repository at startup
    parser.add_argument('--prompt', action='store_true', default=False,
                        help='prompt for a repository')

    # Used on Windows for adding 'git' to the path
    parser.add_argument('-g', '--git-path', metavar='<path>', default=None,
                        help='use the specified git executable')

    # Resume an X Session Management session
    parser.add_argument('-session', metavar='<session>', default=None,
                        help=argparse.SUPPRESS)


def new_application(args):
    # Initialize the app
    return ColaApplication(sys.argv, git_path=args.git_path)


def new_model(app, repo, prompt=False):
    model = main.model()
    valid = model.set_worktree(repo) and not prompt
    while not valid:
        startup_dlg = startup.StartupDialog(app.activeWindow())
        gitdir = startup_dlg.find_git_repo()
        if not gitdir:
            sys.exit(-1)
        valid = model.set_worktree(gitdir)

    # Finally, go to the root of the git repo
    os.chdir(model.git.worktree())
    return model


def _start_update_thread(model):
    """Update the model in the background

    git-cola should startup as quickly as possible.

    """
    class UpdateTask(QtCore.QRunnable):
        def run(self):
            model.update_status(update_index=True)

    # Hold onto a reference to prevent PyQt from dereferencing
    task = UpdateTask()
    QtCore.QThreadPool.globalInstance().start(task)

    return task


def _send_msg():
    if git.GIT_COLA_TRACE == 'trace':
        msg = ('info: Trace enabled.  '
               'Many of commands reported with "trace" use git\'s stable '
               '"plumbing" API and are not intended for typical '
               'day-to-day use.  Here be dragons')
        Interaction.log(msg)


def _update_files():
    # Respond to inotify updates
    cmds.do(cmds.Refresh)


class ApplicationContext(object):

    def __init__(self, args, app, model):
        self.args = args
        self.app = app
        self.model = model

########NEW FILE########
__FILENAME__ = cmds
from __future__ import division, absolute_import, unicode_literals

import os
import sys
from fnmatch import fnmatch
from io import StringIO

from cola import compat
from cola import core
from cola import gitcfg
from cola import gitcmds
from cola import inotify
from cola import utils
from cola import difftool
from cola import resources
from cola.diffparse import DiffParser
from cola.git import STDOUT
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.models import prefs
from cola.models import selection

_config = gitcfg.instance()


class UsageError(Exception):
    """Exception class for usage errors."""
    def __init__(self, title, message):
        Exception.__init__(self, message)
        self.title = title
        self.msg = message


class BaseCommand(object):
    """Base class for all commands; provides the command pattern"""

    DISABLED = False

    def __init__(self):
        self.undoable = False

    def is_undoable(self):
        """Can this be undone?"""
        return self.undoable

    @staticmethod
    def name():
        return 'Unknown'

    def do(self):
        raise NotImplementedError('%s.do() is unimplemented' % self.__class__.__name__)

    def undo(self):
        raise NotImplementedError('%s.undo() is unimplemented' % self.__class__.__name__)


class Command(BaseCommand):
    """Base class for commands that modify the main model"""

    def __init__(self):
        """Initialize the command and stash away values for use in do()"""
        # These are commonly used so let's make it easier to write new commands.
        BaseCommand.__init__(self)
        self.model = main.model()

        self.old_diff_text = self.model.diff_text
        self.old_filename = self.model.filename
        self.old_mode = self.model.mode

        self.new_diff_text = self.old_diff_text
        self.new_filename = self.old_filename
        self.new_mode = self.old_mode

    def do(self):
        """Perform the operation."""
        self.model.set_filename(self.new_filename)
        self.model.set_mode(self.new_mode)
        self.model.set_diff_text(self.new_diff_text)

    def undo(self):
        """Undo the operation."""
        self.model.set_diff_text(self.old_diff_text)
        self.model.set_filename(self.old_filename)
        self.model.set_mode(self.old_mode)


class AmendMode(Command):
    """Try to amend a commit."""

    SHORTCUT = 'Ctrl+M'

    LAST_MESSAGE = None

    @staticmethod
    def name():
        return N_('Amend')

    def __init__(self, amend):
        Command.__init__(self)
        self.undoable = True
        self.skip = False
        self.amending = amend
        self.old_commitmsg = self.model.commitmsg
        self.old_mode = self.model.mode

        if self.amending:
            self.new_mode = self.model.mode_amend
            self.new_commitmsg = self.model.prev_commitmsg()
            AmendMode.LAST_MESSAGE = self.model.commitmsg
            return
        # else, amend unchecked, regular commit
        self.new_mode = self.model.mode_none
        self.new_diff_text = ''
        self.new_commitmsg = self.model.commitmsg
        # If we're going back into new-commit-mode then search the
        # undo stack for a previous amend-commit-mode and grab the
        # commit message at that point in time.
        if AmendMode.LAST_MESSAGE is not None:
            self.new_commitmsg = AmendMode.LAST_MESSAGE
            AmendMode.LAST_MESSAGE = None

    def do(self):
        """Leave/enter amend mode."""
        """Attempt to enter amend mode.  Do not allow this when merging."""
        if self.amending:
            if self.model.is_merging:
                self.skip = True
                self.model.set_mode(self.old_mode)
                Interaction.information(
                        N_('Cannot Amend'),
                        N_('You are in the middle of a merge.\n'
                           'Cannot amend while merging.'))
                return
        self.skip = False
        Command.do(self)
        self.model.set_commitmsg(self.new_commitmsg)
        self.model.update_file_status()

    def undo(self):
        if self.skip:
            return
        self.model.set_commitmsg(self.old_commitmsg)
        Command.undo(self)
        self.model.update_file_status()


class ApplyDiffSelection(Command):

    def __init__(self, staged, selected, offset, selection_text,
                 apply_to_worktree):
        Command.__init__(self)
        self.staged = staged
        self.selected = selected
        self.offset = offset
        self.selection_text = selection_text
        self.apply_to_worktree = apply_to_worktree

    def do(self):
        # The normal worktree vs index scenario
        parser = DiffParser(self.model,
                            filename=self.model.filename,
                            cached=self.staged,
                            reverse=self.apply_to_worktree)
        status, out, err = \
        parser.process_diff_selection(self.selected,
                                      self.offset,
                                      self.selection_text,
                                      apply_to_worktree=self.apply_to_worktree)
        Interaction.log_status(status, out, err)
        self.model.update_file_status(update_index=True)


class ApplyPatches(Command):

    def __init__(self, patches):
        Command.__init__(self)
        self.patches = patches

    def do(self):
        diff_text = ''
        num_patches = len(self.patches)
        orig_head = self.model.git.rev_parse('HEAD')[STDOUT]

        for idx, patch in enumerate(self.patches):
            status, out, err = self.model.git.am(patch)
            # Log the git-am command
            Interaction.log_status(status, out, err)

            if num_patches > 1:
                diff = self.model.git.diff('HEAD^!', stat=True)[STDOUT]
                diff_text += (N_('PATCH %(current)d/%(count)d') %
                              dict(current=idx+1, count=num_patches))
                diff_text += ' - %s:\n%s\n\n' % (os.path.basename(patch), diff)

        diff_text += N_('Summary:') + '\n'
        diff_text += self.model.git.diff(orig_head, stat=True)[STDOUT]

        # Display a diffstat
        self.model.set_diff_text(diff_text)
        self.model.update_file_status()

        basenames = '\n'.join([os.path.basename(p) for p in self.patches])
        Interaction.information(
                N_('Patch(es) Applied'),
                (N_('%d patch(es) applied.') + '\n\n%s') %
                    (len(self.patches), basenames))


class Archive(BaseCommand):

    def __init__(self, ref, fmt, prefix, filename):
        BaseCommand.__init__(self)
        self.ref = ref
        self.fmt = fmt
        self.prefix = prefix
        self.filename = filename

    def do(self):
        fp = core.xopen(self.filename, 'wb')
        cmd = ['git', 'archive', '--format='+self.fmt]
        if self.fmt in ('tgz', 'tar.gz'):
            cmd.append('-9')
        if self.prefix:
            cmd.append('--prefix=' + self.prefix)
        cmd.append(self.ref)
        proc = core.start_command(cmd, stdout=fp)
        out, err = proc.communicate()
        fp.close()
        status = proc.returncode
        Interaction.log_status(status, out or '', err or '')


class Checkout(Command):
    """
    A command object for git-checkout.

    'argv' is handed off directly to git.

    """

    def __init__(self, argv, checkout_branch=False):
        Command.__init__(self)
        self.argv = argv
        self.checkout_branch = checkout_branch
        self.new_diff_text = ''

    def do(self):
        status, out, err = self.model.git.checkout(*self.argv)
        Interaction.log_status(status, out, err)
        if self.checkout_branch:
            self.model.update_status()
        else:
            self.model.update_file_status()


class CheckoutBranch(Checkout):
    """Checkout a branch."""

    def __init__(self, branch):
        args = [branch]
        Checkout.__init__(self, args, checkout_branch=True)


class CherryPick(Command):
    """Cherry pick commits into the current branch."""

    def __init__(self, commits):
        Command.__init__(self)
        self.commits = commits

    def do(self):
        self.model.cherry_pick_list(self.commits)
        self.model.update_file_status()


class ResetMode(Command):
    """Reset the mode and clear the model's diff text."""

    def __init__(self):
        Command.__init__(self)
        self.new_mode = self.model.mode_none
        self.new_diff_text = ''

    def do(self):
        Command.do(self)
        self.model.update_file_status()


class RevertUnstagedEdits(Command):

    SHORTCUT = 'Ctrl+U'

    def do(self):
        if not self.model.undoable():
            return
        s = selection.selection()
        if s.staged:
            items_to_undo = s.staged
        else:
            items_to_undo = s.modified
        if items_to_undo:
            if not Interaction.confirm(N_('Revert Unstaged Changes?'),
                                   N_('This operation drops unstaged changes.\n'
                                      'These changes cannot be recovered.'),
                                   N_('Revert the unstaged changes?'),
                                   N_('Revert Unstaged Changes'),
                                   default=True,
                                   icon=resources.icon('undo.svg')):
                return
            args = []
            if not s.staged and self.model.amending():
                args.append(self.model.head)
            do(Checkout, args + ['--'] + items_to_undo)
        else:
            msg = N_('No files selected for checkout from HEAD.')
            Interaction.log(msg)


class Commit(ResetMode):
    """Attempt to create a new commit."""

    SHORTCUT = 'Ctrl+Return'

    def __init__(self, amend, msg):
        ResetMode.__init__(self)
        self.amend = amend
        self.msg = msg
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = ''

    def do(self):
        tmpfile = utils.tmp_filename('commit-message')
        status, out, err = self.model.commit_with_msg(self.msg, tmpfile,
                                                      amend=self.amend)
        if status == 0:
            ResetMode.do(self)
            self.model.set_commitmsg(self.new_commitmsg)
            msg = N_('Created commit: %s') % out
        else:
            msg = N_('Commit failed: %s') % out
        Interaction.log_status(status, msg, err)

        return status, out, err


class Ignore(Command):
    """Add files to .gitignore"""

    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = filenames

    def do(self):
        if not self.filenames:
            return
        new_additions = '\n'.join(self.filenames) + '\n'
        for_status = new_additions
        if core.exists('.gitignore'):
            current_list = core.read('.gitignore')
            new_additions = current_list.rstrip() + '\n' + new_additions
        core.write('.gitignore', new_additions)
        Interaction.log_status(0, 'Added to .gitignore:\n%s' % for_status, '')
        self.model.update_file_status()


class Delete(Command):
    """Delete files."""

    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = filenames
        # We could git-hash-object stuff and provide undo-ability
        # as an option.  Heh.
    def do(self):
        rescan = False
        for filename in self.filenames:
            if filename:
                try:
                    os.remove(filename)
                    rescan=True
                except:
                    Interaction.information(
                            N_('Error'),
                            N_('Deleting "%s" failed') % filename)
        if rescan:
            self.model.update_file_status()


class DeleteBranch(Command):
    """Delete a git branch."""

    def __init__(self, branch):
        Command.__init__(self)
        self.branch = branch

    def do(self):
        status, out, err = self.model.delete_branch(self.branch)
        Interaction.log_status(status, out, err)


class DeleteRemoteBranch(Command):
    """Delete a remote git branch."""

    def __init__(self, remote, branch):
        Command.__init__(self)
        self.remote = remote
        self.branch = branch

    def do(self):
        status, out, err = self.model.git.push(self.remote, self.branch,
                                               delete=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()

        if status == 0:
            Interaction.information(
                N_('Remote Branch Deleted'),
                N_('"%(branch)s" has been deleted from "%(remote)s".')
                    % dict(branch=self.branch, remote=self.remote))
        else:
            command = 'git push'
            message = (N_('"%(command)s" returned exit status %(status)d') %
                        dict(command=command, status=status))

            Interaction.critical(N_('Error Deleting Remote Branch'),
                                 message, out + err)



class Diff(Command):
    """Perform a diff and set the model's current text."""

    def __init__(self, filenames, cached=False):
        Command.__init__(self)
        # Guard against the list of files being empty
        if not filenames:
            return
        opts = {}
        if cached:
            opts['ref'] = self.model.head
        self.new_filename = filenames[0]
        self.old_filename = self.model.filename
        self.new_mode = self.model.mode_worktree
        self.new_diff_text = gitcmds.diff_helper(filename=self.new_filename,
                                                 cached=cached, **opts)


class Diffstat(Command):
    """Perform a diffstat and set the model's diff text."""

    def __init__(self):
        Command.__init__(self)
        diff = self.model.git.diff(self.model.head,
                                   unified=_config.get('diff.context', 3),
                                   no_ext_diff=True,
                                   no_color=True,
                                   M=True,
                                   stat=True)[STDOUT]
        self.new_diff_text = diff
        self.new_mode = self.model.mode_worktree


class DiffStaged(Diff):
    """Perform a staged diff on a file."""

    def __init__(self, filenames):
        Diff.__init__(self, filenames, cached=True)
        self.new_mode = self.model.mode_index


class DiffStagedSummary(Command):

    def __init__(self):
        Command.__init__(self)
        diff = self.model.git.diff(self.model.head,
                                   cached=True,
                                   no_color=True,
                                   no_ext_diff=True,
                                   patch_with_stat=True,
                                   M=True)[STDOUT]
        self.new_diff_text = diff
        self.new_mode = self.model.mode_index


class Difftool(Command):
    """Run git-difftool limited by path."""

    def __init__(self, staged, filenames):
        Command.__init__(self)
        self.staged = staged
        self.filenames = filenames

    def do(self):
        difftool.launch_with_head(self.filenames,
                                  self.staged, self.model.head)


class Edit(Command):
    """Edit a file using the configured gui.editor."""
    SHORTCUT = 'Ctrl+E'

    @staticmethod
    def name():
        return N_('Edit')

    def __init__(self, filenames, line_number=None):
        Command.__init__(self)
        self.filenames = filenames
        self.line_number = line_number

    def do(self):
        if not self.filenames:
            return
        filename = self.filenames[0]
        if not core.exists(filename):
            return
        editor = prefs.editor()
        opts = []

        if self.line_number is None:
            opts = self.filenames
        else:
            # Single-file w/ line-numbers (likely from grep)
            editor_opts = {
                    '*vim*': ['+'+self.line_number, filename],
                    '*emacs*': ['+'+self.line_number, filename],
                    '*textpad*': ['%s(%s,0)' % (filename, self.line_number)],
                    '*notepad++*': ['-n'+self.line_number, filename],
            }

            opts = self.filenames
            for pattern, opt in editor_opts.items():
                if fnmatch(editor, pattern):
                    opts = opt
                    break

        try:
            core.fork(utils.shell_split(editor) + opts)
        except Exception as e:
            message = (N_('Cannot exec "%s": please configure your editor') %
                       editor)
            Interaction.critical(N_('Error Editing File'),
                                 message, str(e))


class FormatPatch(Command):
    """Output a patch series given all revisions and a selected subset."""

    def __init__(self, to_export, revs):
        Command.__init__(self)
        self.to_export = to_export
        self.revs = revs

    def do(self):
        status, out, err = gitcmds.format_patchsets(self.to_export, self.revs)
        Interaction.log_status(status, out, err)


class LaunchDifftool(BaseCommand):

    SHORTCUT = 'Ctrl+D'

    @staticmethod
    def name():
        return N_('Launch Diff Tool')

    def __init__(self):
        BaseCommand.__init__(self)

    def do(self):
        s = selection.selection()
        if s.unmerged:
            paths = s.unmerged
            if utils.is_win32():
                core.fork(['git', 'mergetool', '--no-prompt', '--'] + paths)
            else:
                core.fork(['xterm', '-e',
                           'git', 'mergetool', '--no-prompt', '--'] + paths)
        else:
            difftool.run()


class LaunchTerminal(BaseCommand):

    SHORTCUT = 'Ctrl+t'

    @staticmethod
    def name():
        return N_('Launch Terminal')

    def __init__(self, path):
        BaseCommand.__init__(self)
        self.path = path

    def do(self):
        cmd = _config.get('cola.terminal', 'xterm -e $SHELL')
        cmd = os.path.expandvars(cmd)
        argv = utils.shell_split(cmd)
        core.fork(argv, cwd=self.path)


class LaunchEditor(Edit):
    SHORTCUT = 'Ctrl+E'

    @staticmethod
    def name():
        return N_('Launch Editor')

    def __init__(self):
        s = selection.selection()
        allfiles = s.staged + s.unmerged + s.modified + s.untracked
        Edit.__init__(self, allfiles)


class LoadCommitMessageFromFile(Command):
    """Loads a commit message from a path."""

    def __init__(self, path):
        Command.__init__(self)
        self.undoable = True
        self.path = path
        self.old_commitmsg = self.model.commitmsg
        self.old_directory = self.model.directory

    def do(self):
        path = self.path
        if not path or not core.isfile(path):
            raise UsageError(N_('Error: Cannot find commit template'),
                             N_('%s: No such file or directory.') % path)
        self.model.set_directory(os.path.dirname(path))
        self.model.set_commitmsg(core.read(path))

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)
        self.model.set_directory(self.old_directory)


class LoadCommitMessageFromTemplate(LoadCommitMessageFromFile):
    """Loads the commit message template specified by commit.template."""

    def __init__(self):
        template = _config.get('commit.template')
        LoadCommitMessageFromFile.__init__(self, template)

    def do(self):
        if self.path is None:
            raise UsageError(
                    N_('Error: Unconfigured commit template'),
                    N_('A commit template has not been configured.\n'
                       'Use "git config" to define "commit.template"\n'
                       'so that it points to a commit template.'))
        return LoadCommitMessageFromFile.do(self)



class LoadCommitMessageFromSHA1(Command):
    """Load a previous commit message"""

    def __init__(self, sha1, prefix=''):
        Command.__init__(self)
        self.sha1 = sha1
        self.old_commitmsg = self.model.commitmsg
        self.new_commitmsg = prefix + self.model.prev_commitmsg(sha1)
        self.undoable = True

    def do(self):
        self.model.set_commitmsg(self.new_commitmsg)

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)


class LoadFixupMessage(LoadCommitMessageFromSHA1):
    """Load a fixup message"""

    def __init__(self, sha1):
        LoadCommitMessageFromSHA1.__init__(self, sha1, prefix='fixup! ')


class Merge(Command):
    def __init__(self, revision, no_commit, squash):
        Command.__init__(self)
        self.revision = revision
        self.no_commit = no_commit
        self.squash = squash

    def do(self):
        squash = self.squash
        revision = self.revision
        no_commit = self.no_commit
        msg = gitcmds.merge_message(revision)

        status, out, err = self.model.git.merge('-m', msg,
                                                revision,
                                                no_commit=no_commit,
                                                squash=squash)

        Interaction.log_status(status, out, err)
        self.model.update_status()


class OpenDefaultApp(BaseCommand):
    """Open a file using the OS default."""
    SHORTCUT = 'Space'

    @staticmethod
    def name():
        return N_('Open Using Default Application')

    def __init__(self, filenames):
        BaseCommand.__init__(self)
        if utils.is_darwin():
            launcher = 'open'
        else:
            launcher = 'xdg-open'
        self.launcher = launcher
        self.filenames = filenames

    def do(self):
        if not self.filenames:
            return
        core.fork([self.launcher] + self.filenames)


class OpenParentDir(OpenDefaultApp):
    """Open parent directories using the OS default."""
    SHORTCUT = 'Shift+Space'

    @staticmethod
    def name():
        return N_('Open Parent Directory')

    def __init__(self, filenames):
        OpenDefaultApp.__init__(self, filenames)

    def do(self):
        if not self.filenames:
            return
        dirs = list(set(map(os.path.dirname, self.filenames)))
        core.fork([self.launcher] + dirs)


class OpenNewRepo(Command):
    """Launches git-cola on a repo."""

    def __init__(self, repo_path):
        Command.__init__(self)
        self.repo_path = repo_path

    def do(self):
        self.model.set_directory(self.repo_path)
        core.fork([sys.executable, sys.argv[0], '--repo', self.repo_path])


class OpenRepo(Command):
    def __init__(self, repo_path):
        Command.__init__(self)
        self.repo_path = repo_path

    def do(self):
        git = self.model.git
        old_worktree = git.worktree()
        if not self.model.set_worktree(self.repo_path):
            self.model.set_worktree(old_worktree)
            return
        new_worktree = git.worktree()
        core.chdir(new_worktree)
        self.model.set_directory(self.repo_path)
        _config.reset()
        inotify.stop()
        inotify.start()
        self.model.update_status()


class Clone(Command):
    """Clones a repository and optionally spawns a new cola session."""

    def __init__(self, url, new_directory, spawn=True):
        Command.__init__(self)
        self.url = url
        self.new_directory = new_directory
        self.spawn = spawn

    def do(self):
        status, out, err = self.model.git.clone(self.url, self.new_directory)
        if status != 0:
            Interaction.information(
                    N_('Error: could not clone "%s"') % self.url,
                    (N_('git clone returned exit code %s') % status) +
                    ((out+err) and ('\n\n' + out + err) or ''))
            return False
        if self.spawn:
            core.fork([sys.executable, sys.argv[0],
                       '--repo', self.new_directory])
        return True


class GitXBaseContext(object):

    def __init__(self, **kwargs):
        self.extras = kwargs

    def __enter__(self):
        compat.setenv('GIT_SEQUENCE_EDITOR',
                      resources.share('bin', 'git-xbase'))
        for var, value in self.extras.items():
            compat.setenv(var, value)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        compat.unsetenv('GIT_SEQUENCE_EDITOR')
        for var in self.extras:
            compat.unsetenv(var)


class Rebase(Command):

    def __init__(self, branch, capture_output=True):
        Command.__init__(self)
        self.branch = branch
        self.capture_output = capture_output

    def do(self):
        branch = self.branch
        if not branch:
            return
        status = 1
        out = ''
        err = ''
        extra = {}
        if self.capture_output:
            extra['_stderr'] = None
            extra['_stdout'] = None
        with GitXBaseContext(
                GIT_EDITOR=prefs.editor(),
                GIT_XBASE_TITLE=N_('Rebase onto %s') % branch,
                GIT_XBASE_ACTION=N_('Rebase')):
            status, out, err = self.model.git.rebase(branch,
                                                     interactive=True,
                                                     autosquash=True,
                                                     **extra)
        Interaction.log_status(status, out, err)
        self.model.update_status()
        return status, out, err


class RebaseEditTodo(Command):

    def do(self):
        with GitXBaseContext(
                GIT_XBASE_TITLE=N_('Edit Rebase'),
                GIT_XBASE_ACTION=N_('Save')):
            status, out, err = self.model.git.rebase(edit_todo=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()


class RebaseContinue(Command):

    def do(self):
        status, out, err = self.model.git.rebase('--continue')
        Interaction.log_status(status, out, err)
        self.model.update_status()


class RebaseSkip(Command):

    def do(self):
        status, out, err = self.model.git.rebase(skip=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()


class RebaseAbort(Command):

    def do(self):
        status, out, err = self.model.git.rebase(abort=True)
        Interaction.log_status(status, out, err)
        self.model.update_status()


class Rescan(Command):
    """Rescan for changes"""

    def do(self):
        self.model.update_status()


class Refresh(Command):
    """Update refs and refresh the index"""

    SHORTCUT = 'Ctrl+R'

    @staticmethod
    def name():
        return N_('Refresh')

    def do(self):
        self.model.update_status(update_index=True)


class RunConfigAction(Command):
    """Run a user-configured action, typically from the "Tools" menu"""

    def __init__(self, action_name):
        Command.__init__(self)
        self.action_name = action_name
        self.model = main.model()

    def do(self):
        for env in ('FILENAME', 'REVISION', 'ARGS'):
            try:
                compat.unsetenv(env)
            except KeyError:
                pass
        rev = None
        args = None
        opts = _config.get_guitool_opts(self.action_name)
        cmd = opts.get('cmd')
        if 'title' not in opts:
            opts['title'] = cmd

        if 'prompt' not in opts or opts.get('prompt') is True:
            prompt = N_('Run "%s"?') % cmd
            opts['prompt'] = prompt

        if opts.get('needsfile'):
            filename = selection.filename()
            if not filename:
                Interaction.information(
                        N_('Please select a file'),
                        N_('"%s" requires a selected file.') % cmd)
                return False
            compat.setenv('FILENAME', filename)

        if opts.get('revprompt') or opts.get('argprompt'):
            while True:
                ok = Interaction.confirm_config_action(cmd, opts)
                if not ok:
                    return False
                rev = opts.get('revision')
                args = opts.get('args')
                if opts.get('revprompt') and not rev:
                    title = N_('Invalid Revision')
                    msg = N_('The revision expression cannot be empty.')
                    Interaction.critical(title, msg)
                    continue
                break

        elif opts.get('confirm'):
            title = os.path.expandvars(opts.get('title'))
            prompt = os.path.expandvars(opts.get('prompt'))
            if Interaction.question(title, prompt):
                return
        if rev:
            compat.setenv('REVISION', rev)
        if args:
            compat.setenv('ARGS', args)
        title = os.path.expandvars(cmd)
        Interaction.log(N_('Running command: %s') % title)
        cmd = ['sh', '-c', cmd]

        if opts.get('noconsole'):
            status, out, err = core.run_command(cmd)
        else:
            status, out, err = Interaction.run_command(title, cmd)

        Interaction.log_status(status,
                               out and (N_('Output: %s') % out) or '',
                               err and (N_('Errors: %s') % err) or '')

        if not opts.get('norescan'):
            self.model.update_status()
        return status


class SetDiffText(Command):

    def __init__(self, text):
        Command.__init__(self)
        self.undoable = True
        self.new_diff_text = text


class ShowUntracked(Command):
    """Show an untracked file."""

    def __init__(self, filenames):
        Command.__init__(self)
        self.filenames = filenames
        self.new_mode = self.model.mode_untracked
        self.new_diff_text = ''
        if filenames:
            self.new_diff_text = self.diff_text_for(filenames[0])

    def diff_text_for(self, filename):
        size = _config.get('cola.readsize', 1024 * 2)
        try:
            result = core.read(filename, size=size)
        except:
            result = ''

        if len(result) == size:
            result += '...'
        return result


class SignOff(Command):
    SHORTCUT = 'Ctrl+I'

    @staticmethod
    def name():
        return N_('Sign Off')

    def __init__(self):
        Command.__init__(self)
        self.undoable = True
        self.old_commitmsg = self.model.commitmsg

    def do(self):
        signoff = self.signoff()
        if signoff in self.model.commitmsg:
            return
        self.model.set_commitmsg(self.model.commitmsg + '\n' + signoff)

    def undo(self):
        self.model.set_commitmsg(self.old_commitmsg)

    def signoff(self):
        try:
            import pwd
            user = pwd.getpwuid(os.getuid()).pw_name
        except ImportError:
            user = os.getenv('USER', N_('unknown'))

        name = _config.get('user.name', user)
        email = _config.get('user.email', '%s@%s' % (user, core.node()))
        return '\nSigned-off-by: %s <%s>' % (name, email)


class Stage(Command):
    """Stage a set of paths."""
    SHORTCUT = 'Ctrl+S'

    @staticmethod
    def name():
        return N_('Stage')

    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        msg = N_('Staging: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        # Prevent external updates while we are staging files.
        # We update file stats at the end of this operation
        # so there's no harm in ignoring updates from other threads
        # (e.g. inotify).
        with CommandDisabled(UpdateFileStatus):
            self.model.stage_paths(self.paths)


class StageModified(Stage):
    """Stage all modified files."""

    SHORTCUT = 'Ctrl+S'

    @staticmethod
    def name():
        return N_('Stage Modified')

    def __init__(self):
        Stage.__init__(self, None)
        self.paths = self.model.modified


class StageUnmerged(Stage):
    """Stage all modified files."""

    SHORTCUT = 'Ctrl+S'

    @staticmethod
    def name():
        return N_('Stage Unmerged')

    def __init__(self):
        Stage.__init__(self, None)
        self.paths = self.model.unmerged


class StageUntracked(Stage):
    """Stage all untracked files."""

    SHORTCUT = 'Ctrl+S'

    @staticmethod
    def name():
        return N_('Stage Untracked')

    def __init__(self):
        Stage.__init__(self, None)
        self.paths = self.model.untracked


class Tag(Command):
    """Create a tag object."""

    def __init__(self, name, revision, sign=False, message=''):
        Command.__init__(self)
        self._name = name
        self._message = message
        self._revision = revision
        self._sign = sign

    def do(self):
        log_msg = (N_('Tagging "%(revision)s" as "%(name)s"') %
                   dict(revision=self._revision, name=self._name))
        opts = {}
        if self._message:
            opts['F'] = utils.tmp_filename('tag-message')
            core.write(opts['F'], self._message)

        if self._sign:
            log_msg += ' (%s)' % N_('GPG-signed')
            opts['s'] = True
            status, output, err = self.model.git.tag(self._name,
                                                     self._revision, **opts)
        else:
            opts['a'] = bool(self._message)
            status, output, err = self.model.git.tag(self._name,
                                                     self._revision, **opts)
        if 'F' in opts:
            os.unlink(opts['F'])

        if output:
            log_msg += '\n' + (N_('Output: %s') % output)

        Interaction.log_status(status, log_msg, err)
        if status == 0:
            self.model.update_status()


class Unstage(Command):
    """Unstage a set of paths."""

    SHORTCUT = 'Ctrl+S'

    @staticmethod
    def name():
        return N_('Unstage')

    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        msg = N_('Unstaging: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        with CommandDisabled(UpdateFileStatus):
            self.model.unstage_paths(self.paths)


class UnstageAll(Command):
    """Unstage all files; resets the index."""

    def do(self):
        self.model.unstage_all()


class UnstageSelected(Unstage):
    """Unstage selected files."""

    def __init__(self):
        Unstage.__init__(self, selection.selection_model().staged)


class Untrack(Command):
    """Unstage a set of paths."""

    def __init__(self, paths):
        Command.__init__(self)
        self.paths = paths

    def do(self):
        msg = N_('Untracking: %s') % (', '.join(self.paths))
        Interaction.log(msg)
        with CommandDisabled(UpdateFileStatus):
            status, out, err = self.model.untrack_paths(self.paths)
        Interaction.log_status(status, out, err)


class UntrackedSummary(Command):
    """List possible .gitignore rules as the diff text."""

    def __init__(self):
        Command.__init__(self)
        untracked = self.model.untracked
        suffix = len(untracked) > 1 and 's' or ''
        io = StringIO()
        io.write('# %s untracked file%s\n' % (len(untracked), suffix))
        if untracked:
            io.write('# possible .gitignore rule%s:\n' % suffix)
            for u in untracked:
                io.write('/'+u+'\n')
        self.new_diff_text = io.getvalue()
        self.new_mode = self.model.mode_untracked


class UpdateFileStatus(Command):
    """Rescans for changes."""

    def do(self):
        self.model.update_file_status()


class VisualizeAll(Command):
    """Visualize all branches."""

    def do(self):
        browser = utils.shell_split(prefs.history_browser())
        launch_history_browser(browser + ['--all'])


class VisualizeCurrent(Command):
    """Visualize all branches."""

    def do(self):
        browser = utils.shell_split(prefs.history_browser())
        launch_history_browser(browser + [self.model.currentbranch])


class VisualizePaths(Command):
    """Path-limited visualization."""

    def __init__(self, paths):
        Command.__init__(self)
        browser = utils.shell_split(prefs.history_browser())
        if paths:
            self.argv = browser + paths
        else:
            self.argv = browser

    def do(self):
        launch_history_browser(self.argv)


class VisualizeRevision(Command):
    """Visualize a specific revision."""

    def __init__(self, revision, paths=None):
        Command.__init__(self)
        self.revision = revision
        self.paths = paths

    def do(self):
        argv = utils.shell_split(prefs.history_browser())
        if self.revision:
            argv.append(self.revision)
        if self.paths:
            argv.append('--')
            argv.extend(self.paths)
        launch_history_browser(argv)


def launch_history_browser(argv):
    try:
        core.fork(argv)
    except Exception as e:
        _, details = utils.format_exception(e)
        title = N_('Error Launching History Browser')
        msg = (N_('Cannot exec "%s": please configure a history browser') %
               ' '.join(argv))
        Interaction.critical(title, message=msg, details=details)


def run(cls, *args, **opts):
    """
    Returns a callback that runs a command

    If the caller of run() provides args or opts then those are
    used instead of the ones provided by the invoker of the callback.

    """
    def runner(*local_args, **local_opts):
        if args or opts:
            do(cls, *args, **opts)
        else:
            do(cls, *local_args, **local_opts)

    return runner


class CommandDisabled(object):

    """Context manager to temporarily disable a command from running"""
    def __init__(self, cmdclass):
        self.cmdclass = cmdclass

    def __enter__(self):
        self.cmdclass.DISABLED = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cmdclass.DISABLED = False


def do(cls, *args, **opts):
    """Run a command in-place"""
    return do_cmd(cls(*args, **opts))


def do_cmd(cmd):
    if hasattr(cmd, 'DISABLED') and cmd.DISABLED:
        return None
    try:
        return cmd.do()
    except Exception as e:
        msg, details = utils.format_exception(e)
        Interaction.critical(N_('Error'), message=msg, details=details)
        return None

########NEW FILE########
__FILENAME__ = compat
import os
import sys


PY3 = sys.version_info[0] >= 3

try:
    ustr = unicode
except NameError:
    # Python 3
    ustr = str

try:
    unichr = unichr
except NameError:
    # Python 3
    unichr = chr

try:
    # Python 3
    from urllib import parse
    urllib = parse
except ImportError:
    import urllib

def setenv(key, value):
    """Compatibility wrapper for setting environment variables

    Why?  win32 requires putenv().  UNIX only requires os.environ.

    """
    os.environ[key] = value
    os.putenv(key, value)


def unsetenv(key):
    """Compatibility wrapper for unsetting environment variables"""
    try:
        del os.environ[key]
    except:
        pass
    if hasattr(os, 'unsetenv'):
        os.unsetenv(key)

########NEW FILE########
__FILENAME__ = core
"""This module provides core functions for handling unicode and UNIX quirks

The @interruptable functions retry when system calls are interrupted,
e.g. when python raises an IOError or OSError with errno == EINTR.

"""
from __future__ import division, absolute_import, unicode_literals

import os
import sys
import itertools
import platform
import subprocess

from cola.decorators import interruptable
from cola.compat import ustr
from cola.compat import PY3

# Some files are not in UTF-8; some other aren't in any codification.
# Remember that GIT doesn't care about encodings (saves binary data)
_encoding_tests = [
    'utf-8',
    'iso-8859-15',
    'windows1252',
    'ascii',
    # <-- add encodings here
]

def decode(enc, encoding=None):
    """decode(encoded_string) returns an unencoded unicode string
    """
    if enc is None or type(enc) is ustr:
        return enc

    if encoding is None:
        encoding_tests = _encoding_tests
    else:
        encoding_tests = itertools.chain([encoding], _encoding_tests)

    for encoding in encoding_tests:
        try:
            return enc.decode(encoding)
        except:
            pass
    # this shouldn't ever happen... FIXME
    return ustr(enc)


def encode(string, encoding=None):
    """encode(unencoded_string) returns a string encoded in utf-8
    """
    if type(string) is not ustr:
        return string
    return string.encode(encoding or 'utf-8', 'replace')


def read(filename, size=-1, encoding=None):
    """Read filename and return contents"""
    with xopen(filename, 'r') as fh:
        return fread(fh, size=size, encoding=encoding)


def write(path, contents, encoding=None):
    """Writes a unicode string to a file"""
    with xopen(path, 'wb') as fh:
        return fwrite(fh, contents, encoding=encoding)


@interruptable
def fread(fh, size=-1, encoding=None):
    """Read from a filehandle and retry when interrupted"""
    return decode(fh.read(size), encoding=encoding)


@interruptable
def fwrite(fh, content, encoding=None):
    """Write to a filehandle and retry when interrupted"""
    return fh.write(encode(content, encoding=encoding))


@interruptable
def wait(proc):
    """Wait on a subprocess and retry when interrupted"""
    return proc.wait()


@interruptable
def readline(fh, encoding=None):
    return decode(fh.readline(), encoding=encoding)


@interruptable
def start_command(cmd, cwd=None, add_env=None,
                  universal_newlines=False,
                  stdin=subprocess.PIPE,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
                  **extra):
    """Start the given command, and return a subprocess object.

    This provides a simpler interface to the subprocess module.

    """
    env = None
    if add_env is not None:
        env = os.environ.copy()
        env.update(add_env)
    if PY3:
        # Python3 on windows always goes through list2cmdline() internally inside
        # of subprocess.py so we must provide unicode strings here otherwise
        # Python3 breaks when bytes are provided.
        #
        # Additionally, the preferred usage on Python3 is to pass unicode
        # strings to subprocess.  Python will automatically encode into the
        # default encoding (utf-8) when it gets unicode strings.
        cmd = [decode(c) for c in cmd]
    else:
        cmd = [encode(c) for c in cmd]
    return subprocess.Popen(cmd, bufsize=1, stdin=stdin, stdout=stdout,
                            stderr=stderr, cwd=cwd, env=env,
                            universal_newlines=universal_newlines, **extra)


@interruptable
def communicate(proc):
    return proc.communicate()


def run_command(cmd, encoding=None, *args, **kwargs):
    """Run the given command to completion, and return its results.

    This provides a simpler interface to the subprocess module.
    The results are formatted as a 3-tuple: (exit_code, output, errors)
    The other arguments are passed on to start_command().

    """
    process = start_command(cmd, *args, **kwargs)
    (output, errors) = communicate(process)
    output = decode(output, encoding=encoding)
    errors = decode(errors, encoding=encoding)
    exit_code = process.returncode
    return (exit_code, output, errors)


@interruptable
def _fork_posix(args, cwd=None):
    """Launch a process in the background."""
    encoded_args = [encode(arg) for arg in args]
    return subprocess.Popen(encoded_args, cwd=cwd).pid


def _fork_win32(args, cwd=None):
    """Launch a background process using crazy win32 voodoo."""
    # This is probably wrong, but it works.  Windows.. wow.
    if args[0] == 'git-dag':
        # win32 can't exec python scripts
        args = [sys.executable] + args
    args[0] = _win32_find_exe(args[0])

    if PY3:
        # see comment in start_command()
        argv = [decode(arg) for arg in args]
    else:
        argv = [encode(arg) for arg in args]
    DETACHED_PROCESS = 0x00000008 # Amazing!
    return subprocess.Popen(argv, cwd=cwd, creationflags=DETACHED_PROCESS).pid


def _win32_find_exe(exe):
    """Find the actual file for a Windows executable.

    This function goes through the same process that the Windows shell uses to
    locate an executable, taking into account the PATH and PATHEXT environment
    variables.  This allows us to avoid passing shell=True to subprocess.Popen.

    For reference, see:
    http://technet.microsoft.com/en-us/library/cc723564.aspx#XSLTsection127121120120
    """
    # try the argument itself
    candidates = [exe]
    # if argument does not have an extension, also try it with each of the
    # extensions specified in PATHEXT
    if not '.' in exe:
        candidates.extend(exe + ext
                for ext in getenv('PATHEXT', '').split(os.pathsep)
                if ext.startswith('.'))
    # search the current directory first
    for candidate in candidates:
        if exists(candidate):
            return candidate
    # if the argument does not include a path separator, search each of the
    # directories on the PATH
    if not os.path.dirname(exe):
        for path in getenv('PATH').split(os.pathsep):
            if path:
                for candidate in candidates:
                    full_path = os.path.join(path, candidate)
                    if exists(full_path):
                        return full_path
    # not found, punt and return the argument unchanged
    return exe


# Portability wrappers
if sys.platform == 'win32' or sys.platform == 'cygwin':
    fork = _fork_win32
else:
    fork = _fork_posix


def wrap(action, fn, decorator=None):
    """Wrap arguments with `action`, optionally decorate the result"""
    if decorator is None:
        decorator = lambda x: x
    def wrapped(*args, **kwargs):
        return decorator(fn(action(*args, **kwargs)))
    return wrapped


def decorate(decorator, fn):
    """Decorate the result of `fn` with `action`"""
    def decorated(*args, **kwargs):
        return decorator(fn(*args, **kwargs))
    return decorated


def exists(path, encoding=None):
    return os.path.exists(encode(path), encoding=encoding)


def getenv(name, default=None):
    return decode(os.getenv(name, default))


def xopen(path, mode='r', encoding=None):
    return open(encode(path, encoding=encoding), mode)


def stdout(msg):
    msg = msg + '\n'
    if not PY3:
        msg = encode(msg, sys.stdout.encoding)
    sys.stdout.write(msg)


def stderr(msg):
    msg = msg + '\n'
    if not PY3:
        msg = encode(msg, sys.stderr.encoding)
    sys.stderr.write(msg)


@interruptable
def node():
    return platform.node()


abspath = wrap(encode, os.path.abspath, decorator=decode)
chdir = wrap(encode, os.chdir)
exists = wrap(encode, os.path.exists)
expanduser = wrap(encode, os.path.expanduser, decorator=decode)
getcwd = decorate(decode, os.getcwd)
isdir = wrap(encode, os.path.isdir)
isfile = wrap(encode, os.path.isfile)
islink = wrap(encode, os.path.islink)
makedirs = wrap(encode, os.makedirs)
try:
    readlink = wrap(encode, os.readlink, decorator=decode)
except AttributeError:
    readlink = lambda p: p
realpath = wrap(encode, os.path.realpath, decorator=decode)
stat = wrap(encode, os.stat)
unlink = wrap(encode, os.unlink)
walk = wrap(encode, os.walk)

########NEW FILE########
__FILENAME__ = decorators
from __future__ import division, absolute_import, unicode_literals

__all__ = ('decorator', 'memoize', 'interruptable')

import errno


def decorator(caller, func=None):
    """
    Create a new decorator

    decorator(caller) converts a caller function into a decorator;
    decorator(caller, func) decorates a function using a caller.

    """
    if func is None:
        # return a decorator
        def _decorator(f, *args, **opts):
            def _caller(*args, **opts):
                return caller(f, *args, **opts)
            return _caller
        return _decorator
    else:
        # return a decorated function
        def _decorated(*args, **opts):
            return caller(func, *args, **opts)
        return _decorated


def memoize(func):
    """
    A decorator for memoizing function calls

    http://en.wikipedia.org/wiki/Memoization

    """
    func.cache = {}
    return decorator(_memoize, func)


def _memoize(func, *args, **opts):
    """Implements memoized cache lookups"""
    if opts: # frozenset is used to ensure hashability
        key = args, frozenset(opts.items())
    else:
        key = args
    cache = func.cache # attribute added by memoize
    try:
        result = cache[key]
    except KeyError:
        result = cache[key] = func(*args, **opts)
    return result


@decorator
def interruptable(func, *args, **opts):
    """Handle interruptable system calls

    OSX and others are known to interrupt system calls

        http://en.wikipedia.org/wiki/PCLSRing
        http://en.wikipedia.org/wiki/Unix_philosophy#Worse_is_better

    The @interruptable decorator handles this situation

    """
    while True:
        try:
            result = func(*args, **opts)
        except IOError as e:
            if e.errno == errno.EINTR:
                continue
            raise e
        except OSError as e:
            if e.errno in (errno.EINTR, errno.EINVAL):
                continue
            raise e
        else:
            break
    return result

########NEW FILE########
__FILENAME__ = diffparse
from __future__ import division, absolute_import, unicode_literals

import os
import re

from cola import core
from cola import gitcmds
from cola import gitcfg
from cola import utils


class Range(object):

    def __init__(self, begin, end):
        self.begin = self._parse(begin)
        self.end = self._parse(end)

    def _parse(self, range_str):
        if ',' in range_str:
            begin, end = range_str.split(',')
            return [int(begin), int(end)]
        else:
            return [int(range_str), int(range_str)]

    def make(self):
        return '@@ -%s +%s @@' % (self._span(self.begin), self._span(self.end))

    def set_begin_count(self, count):
        self._set_count(self.begin, count)

    def set_end_count(self, count):
        self._set_count(self.end, count)

    def _set_count(self, which, count):
        if count != which[1]:
            which[1] = count
            if count == 1 and which[0] == 0:
                # the file would be empty in the diff, but we're only
                # partially applying it, and thus it's not a +0,0 diff
                # anymore.
                which[0] = 1

    def _span(self, seq):
        a = seq[0]
        b = seq[1]
        if a == b and a == 1:
            return '%d' % a
        else:
            return '%d,%d' % (a, b)


class DiffSource(object):
    def get(self, head, amending, filename, cached, reverse):
        return gitcmds.diff_helper(head=head,
                                   amending=amending,
                                   filename=filename,
                                   with_diff_header=True,
                                   cached=cached,
                                   reverse=reverse)


class DiffParser(object):

    """Handles parsing diff for use by the interactive index editor."""

    HEADER_RE = re.compile(r'^@@ -([0-9,]+) \+([0-9,]+) @@.*')

    def __init__(self, model, filename='',
                 cached=True, reverse=False,
                 diff_source=None):

        self._idx = -1
        self._diffs = []
        self._diff_spans = []
        self._diff_offsets = []
        self._ranges = []

        self.config = gitcfg.instance()
        self.head = model.head
        self.amending = model.amending()
        self.start = None
        self.end = None
        self.offset = None
        self.diff_sel = []
        self.selected = []
        self.filename = filename
        self.diff_source = diff_source or DiffSource()

        (header, diff) = self.diff_source.get(self.head, self.amending,
                                              filename, cached,
                                              cached or reverse)
        self.model = model
        self.diff = diff
        self.header = header
        self.parse_diff(diff)

        # Always index into the non-reversed diff
        self.fwd_header, self.fwd_diff = \
                self.diff_source.get(self.head,
                                     self.amending,
                                     filename,
                                     cached, False)

    def write_diff(self,filename,which,selected=False,noop=False):
        """Writes a new diff corresponding to the user's selection."""
        if not noop and which < len(self.diff_sel):
            diff = self.diff_sel[which]
            encoding = self.config.file_encoding(self.filename)
            core.write(filename, self.header + '\n' + diff + '\n',
                       encoding=encoding)
            return True
        else:
            return False

    def ranges(self):
        """Return the diff header ranges"""
        return self._ranges

    def diffs(self):
        """Returns the list of diffs."""
        return self._diffs

    def diff_subset(self, diff, start, end):
        """Processes the diffs and returns a selected subset from that diff.
        """
        adds = 0
        deletes = 0
        existing = 0
        newdiff = []
        local_offset = 0
        offset = self._diff_spans[diff][0]

        ADD = '+'
        DEL = '-'
        NOP = ' '

        for line in self._diffs[diff]:
            line_start = offset + local_offset
            local_offset += len(line) + 1 #\n
            line_end = offset + local_offset
            # |line1 |line2 |line3 |
            #   |--selection--|
            #   '-start       '-end

            # selection has head of diff (line3)
            has_head = start <= line_start and end > line_start and end <= line_end
            # selection has all of diff (line2)
            has_all = start <= line_start and end >= line_end
            # selection has tail of diff (line1)
            has_tail = start >= line_start and start < line_end - 1

            action = line[0:1]
            if has_head or has_all or has_tail:
                newdiff.append(line)
                if action == ADD:
                    adds += 1
                elif action == DEL:
                    deletes += 1
                elif action == NOP:
                    existing += 1
            else:
                # Don't add new lines unless selected
                if action == ADD:
                    continue
                elif action == DEL:
                    # Don't remove lines unless selected
                    newdiff.append(' ' + line[1:])
                    existing += 1
                elif action == NOP:
                    newdiff.append(line)
                    existing += 1
                else:
                    newdiff.append(line)

        diff_range = self._ranges[diff]
        begin_count = existing + deletes
        end_count = existing + adds

        diff_range.set_begin_count(begin_count)
        diff_range.set_end_count(end_count)
        newdiff[0] = diff_range.make()

        return (self.header + '\n' + '\n'.join(newdiff) + '\n')

    def spans(self):
        """Returns the line spans of each hunk."""
        return self._diff_spans

    def offsets(self):
        """Returns the offsets."""
        return self._diff_offsets

    def set_diff_to_offset(self, offset):
        """Sets the diff selection to be the hunk at a particular offset."""
        self.offset = offset
        self.diff_sel, self.selected = self.diff_for_offset(offset)

    def set_diffs_to_range(self, start, end):
        """Sets the diff selection to be a range of hunks."""
        self.start = start
        self.end = end
        self.diff_sel, self.selected = self.diffs_for_range(start,end)

    def diff_for_offset(self, offset):
        """Returns the hunks for a particular offset."""
        for idx, diff_offset in enumerate(self._diff_offsets):
            if offset < diff_offset:
                return (['\n'.join(self._diffs[idx])], [idx])
        return ([],[])

    def diffs_for_range(self, start, end):
        """Returns the hunks for a selected range."""
        diffs = []
        indices = []
        for idx, span in enumerate(self._diff_spans):
            has_end_of_diff = start >= span[0] and start < span[1]
            has_all_of_diff = start <= span[0] and end >= span[1]
            has_head_of_diff = end >= span[0] and end <= span[1]

            selected_diff =(has_end_of_diff
                    or has_all_of_diff
                    or has_head_of_diff)
            if selected_diff:
                diff = '\n'.join(self._diffs[idx])
                diffs.append(diff)
                indices.append(idx)
        return diffs, indices

    def parse_diff(self, diff):
        """Parses a diff and extracts headers, offsets, hunks, etc.
        """
        total_offset = 0
        self._idx = -1

        for line in diff.split('\n'):
            match = self.HEADER_RE.match(line)
            if match:
                self._ranges.append(Range(match.group(1), match.group(2)))
                self._diffs.append([line])

                line_len = len(line) + 1 #\n
                self._diff_spans.append([total_offset,
                                         total_offset + line_len])
                total_offset += line_len
                self._diff_offsets.append(total_offset)
                self._idx += 1
                continue

            if self._idx < 0:
                errmsg = 'Malformed diff?: %s' % diff
                raise AssertionError(errmsg)

            line_len = len(line) + 1
            total_offset += line_len

            self._diffs[self._idx].append(line)
            self._diff_spans[-1][-1] += line_len
            self._diff_offsets[self._idx] += line_len

    def process_diff_selection(self, selected, offset, selection,
                               apply_to_worktree=False):
        """Processes a diff selection and applies changes to git."""
        if selection:
            # qt destroys \r\n and makes it \n with no way of going back.
            # boo!  we work around that here.
            # I think this was win32-specific.  We might want to do
            # this on win32 only (TODO verify)
            if selection not in self.fwd_diff:
                special_selection = selection.replace('\n', '\r\n')
                if special_selection in self.fwd_diff:
                    selection = special_selection
                else:
                    return 0, '', ''
            start = self.fwd_diff.index(selection)
            end = start + len(selection)
            self.set_diffs_to_range(start, end)
        else:
            self.set_diff_to_offset(offset)
            selected = False

        output = ''
        error = ''
        status = 0
        # Process diff selection only
        if selected:
            encoding = self.config.file_encoding(self.filename)
            for idx in self.selected:
                contents = self.diff_subset(idx, start, end)
                if not contents:
                    continue
                tmpfile = utils.tmp_filename('selection')
                core.write(tmpfile, contents, encoding=encoding)
                if apply_to_worktree:
                    stat, out, err = self.model.apply_diff_to_worktree(tmpfile)
                    output += out
                    error += err
                    status = max(status, stat)
                else:
                    stat, out, err = self.model.apply_diff(tmpfile)
                    output += out
                    error += err
                    status = max(status, stat)
                os.unlink(tmpfile)
        # Process a complete hunk
        else:
            for idx, diff in enumerate(self.diff_sel):
                tmpfile = utils.tmp_filename('patch%02d' % idx)
                if not self.write_diff(tmpfile,idx):
                    continue
                if apply_to_worktree:
                    stat, out, err = self.model.apply_diff_to_worktree(tmpfile)
                    output += out
                    error += err
                    status = max(status, stat)
                else:
                    stat, out, err = self.model.apply_diff(tmpfile)
                    output += out
                    error += err
                    status = max(status, stat)
                os.unlink(tmpfile)
        return status, output, error

########NEW FILE########
__FILENAME__ = difftool
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import utils
from cola import qtutils
from cola import gitcmds
from cola.i18n import N_
from cola.models import main
from cola.models import selection
from cola.widgets import completion
from cola.widgets import defs
from cola.widgets import standard
from cola.compat import ustr


def run():
    files = selection.selected_group()
    if not files:
        return
    s = selection.selection()
    model = main.model()
    launch_with_head(files, bool(s.staged), model.head)


def launch_with_head(filenames, staged, head):
    args = []
    if staged:
        args.append('--cached')
    if head != 'HEAD':
        args.append(head)
    args.append('--')
    args.extend(filenames)
    launch(args)


def launch(args):
    """Launches 'git difftool' with args"""
    difftool_args = ['git', 'difftool', '--no-prompt']
    difftool_args.extend(args)
    core.fork(difftool_args)


def diff_commits(parent, a, b):
    dlg = FileDiffDialog(parent, a=a, b=b)
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtGui.QDialog.Accepted


def diff_expression(parent, expr,
                    create_widget=False, hide_expr=False):
    dlg = FileDiffDialog(parent, expr=expr, hide_expr=hide_expr)
    if create_widget:
        return dlg
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtGui.QDialog.Accepted


class FileDiffDialog(QtGui.QDialog):

    def __init__(self, parent, a=None, b=None, expr=None, title=None,
                 hide_expr=False):
        QtGui.QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)

        self.a = a
        self.b = b
        self.expr = expr

        if title is None:
            title = N_('git-cola diff')

        self.setWindowTitle(title)
        self.setWindowModality(QtCore.Qt.WindowModal)

        self._expr = completion.GitRefLineEdit(parent=self)
        if expr is not None:
            self._expr.setText(expr)

        if expr is None or hide_expr:
            self._expr.hide()

        self._tree = standard.TreeWidget(self)
        self._tree.setSelectionMode(self._tree.ExtendedSelection)
        self._tree.setHeaderHidden(True)

        self._diff_btn = QtGui.QPushButton(N_('Compare'))
        self._diff_btn.setIcon(qtutils.ok_icon())
        self._diff_btn.setEnabled(False)

        self._close_btn = QtGui.QPushButton(N_('Close'))
        self._close_btn.setIcon(qtutils.close_icon())

        self._button_layt = QtGui.QHBoxLayout()
        self._button_layt.setMargin(0)
        self._button_layt.addStretch()
        self._button_layt.addWidget(self._diff_btn)
        self._button_layt.addWidget(self._close_btn)

        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(defs.margin)
        self._layt.setSpacing(defs.spacing)

        self._layt.addWidget(self._expr)
        self._layt.addWidget(self._tree)
        self._layt.addLayout(self._button_layt)
        self.setLayout(self._layt)

        self.connect(self._tree, SIGNAL('itemSelectionChanged()'),
                     self._tree_selection_changed)

        self.connect(self._tree,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self._tree_double_clicked)

        self.connect(self._expr, SIGNAL('textChanged(QString)'),
                     self.text_changed)

        self.connect(self._expr, SIGNAL('returnPressed()'),
                     self.refresh)

        qtutils.connect_button(self._diff_btn, self.diff)
        qtutils.connect_button(self._close_btn, self.close)
        qtutils.add_close_action(self)

        self.resize(720, 420)
        self.refresh()

    def text_changed(self, txt):
        self.expr = ustr(txt)
        self.refresh()

    def refresh(self):
        if self.expr is not None:
            self.diff_arg = utils.shell_split(self.expr)
        elif self.b is None:
            self.diff_arg = [self.a]
        else:
            self.diff_arg = [self.a, self.b]
        self.refresh_filenames()

    def refresh_filenames(self):
        self._tree.clear()

        if self.a and self.b is None:
            filenames = gitcmds.diff_index_filenames(self.a)
        else:
            filenames = gitcmds.diff(self.diff_arg)
        if not filenames:
            return

        icon = qtutils.file_icon()
        items = []
        for filename in filenames:
            item = QtGui.QTreeWidgetItem()
            item.setIcon(0, icon)
            item.setText(0, filename)
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(filename))
            items.append(item)
        self._tree.addTopLevelItems(items)

    def _tree_selection_changed(self):
        self._diff_btn.setEnabled(bool(self._tree.selectedItems()))

    def _tree_double_clicked(self, item, column):
        path = item.data(0, QtCore.Qt.UserRole).toPyObject()
        launch(self.diff_arg + ['--', ustr(path)])

    def diff(self):
        items = self._tree.selectedItems()
        if not items:
            return
        paths = [i.data(0, QtCore.Qt.UserRole).toPyObject() for i in items]
        for path in paths:
            launch(self.diff_arg + ['--', ustr(path)])

########NEW FILE########
__FILENAME__ = git
from __future__ import division, absolute_import, unicode_literals

import functools
import errno
import os
import sys
import subprocess
import threading
from os.path import join

from cola import core
from cola.decorators import memoize
from cola.interaction import Interaction


INDEX_LOCK = threading.Lock()
GIT_COLA_TRACE = core.getenv('GIT_COLA_TRACE', '')
STATUS = 0
STDOUT = 1
STDERR = 2


def dashify(s):
    return s.replace('_', '-')


def is_git_dir(d):
    """From git's setup.c:is_git_directory()."""
    if (core.isdir(d) and core.isdir(join(d, 'objects')) and
            core.isdir(join(d, 'refs'))):
        headref = join(d, 'HEAD')
        return (core.isfile(headref) or
                (core.islink(headref) and
                    core.readlink(headref).startswith('refs')))

    return is_git_file(d)


def is_git_file(f):
    return core.isfile(f) and '.git' == os.path.basename(f)


def is_git_worktree(d):
    return is_git_dir(join(d, '.git'))


def read_git_file(path):
    if path is None:
        return None
    if is_git_file(path):
        data = core.read(path).strip()
        if data.startswith('gitdir: '):
            return data[len('gitdir: '):]
    return None


class Git(object):
    """
    The Git class manages communication with the Git binary
    """
    def __init__(self):
        self._git_cwd = None #: The working directory used by execute()
        self._worktree = None
        self._git_file_path = None
        self.set_worktree(core.getcwd())

    def set_worktree(self, path):
        self._git_dir = core.decode(path)
        self._git_file_path = None
        self._worktree = None
        return self.worktree()

    def worktree(self):
        if self._worktree:
            return self._worktree
        self.git_dir()
        if self._git_dir:
            curdir = self._git_dir
        else:
            curdir = core.getcwd()

        if is_git_dir(join(curdir, '.git')):
            return curdir

        # Handle bare repositories
        if (len(os.path.basename(curdir)) > 4
                and curdir.endswith('.git')):
            return curdir
        if 'GIT_WORK_TREE' in os.environ:
            self._worktree = core.getenv('GIT_WORK_TREE')
        if not self._worktree or not core.isdir(self._worktree):
            if self._git_dir:
                gitparent = join(core.abspath(self._git_dir), '..')
                self._worktree = core.abspath(gitparent)
                self.set_cwd(self._worktree)
        return self._worktree

    def is_valid(self):
        return self._git_dir and is_git_dir(self._git_dir)

    def git_path(self, *paths):
        if self._git_file_path is None:
            return join(self.git_dir(), *paths)
        else:
            return join(self._git_file_path, *paths)

    def git_dir(self):
        if self.is_valid():
            return self._git_dir
        if 'GIT_DIR' in os.environ:
            self._git_dir = core.getenv('GIT_DIR')
        if self._git_dir:
            curpath = core.abspath(self._git_dir)
        else:
            curpath = core.abspath(core.getcwd())
        # Search for a .git directory
        while curpath:
            if is_git_dir(curpath):
                self._git_dir = curpath
                break
            gitpath = join(curpath, '.git')
            if is_git_dir(gitpath):
                self._git_dir = gitpath
                break
            curpath, dummy = os.path.split(curpath)
            if not dummy:
                break
        self._git_file_path = read_git_file(self._git_dir)
        return self._git_dir

    def set_cwd(self, path):
        """Sets the current directory."""
        self._git_cwd = path

    def __getattr__(self, name):
        git_cmd = functools.partial(self.git, name)
        setattr(self, name, git_cmd)
        return git_cmd

    @staticmethod
    def execute(command,
                _cwd=None,
                _decode=True,
                _encoding=None,
                _raw=False,
                _stdin=None,
                _stderr=subprocess.PIPE,
                _stdout=subprocess.PIPE):
        """
        Execute a command and returns its output

        :param command: argument list to execute.
        :param _cwd: working directory, defaults to the current directory.
        :param _decode: whether to decode output, defaults to True.
        :param _encoding: default encoding, defaults to None (utf-8).
        :param _raw: do not strip trailing whitespace.
        :param _stdin: optional stdin filehandle.
        :returns (status, out, err): exit status, stdout, stderr

        """
        # Allow the user to have the command executed in their working dir.
        if not _cwd:
            _cwd = core.getcwd()

        extra = {}
        if sys.platform == 'win32':
            # If git-cola is invoked on Windows using "start pythonw git-cola",
            # a console window will briefly flash on the screen each time
            # git-cola invokes git, which is very annoying.  The code below
            # prevents this by ensuring that any window will be hidden.
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags = subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            extra['startupinfo'] = startupinfo

        # Start the process
        # Guard against thread-unsafe .git/index.lock files
        INDEX_LOCK.acquire()
        status, out, err = core.run_command(command,
                                            cwd=_cwd,
                                            encoding=_encoding,
                                            stdin=_stdin, stdout=_stdout, stderr=_stderr,
                                            **extra)
        # Let the next thread in
        INDEX_LOCK.release()
        if not _raw and out is not None:
            out = out.rstrip('\n')

        cola_trace = GIT_COLA_TRACE
        if cola_trace == 'trace':
            msg = 'trace: ' + subprocess.list2cmdline(command)
            Interaction.log_status(status, msg, '')
        elif cola_trace == 'full':
            if out or err:
                core.stderr("%s -> %d: '%s' '%s'" %
                            (' '.join(command), status, out, err))
            else:
                core.stderr("%s -> %d" % (' '.join(command), status))
        elif cola_trace:
            core.stderr(' '.join(command))

        # Allow access to the command's status code
        return (status, out, err)

    def transform_kwargs(self, **kwargs):
        """Transform kwargs into git command line options"""
        args = []
        for k, v in kwargs.items():
            if len(k) == 1:
                if v is True:
                    args.append("-%s" % k)
                elif type(v) is not bool:
                    args.append("-%s%s" % (k, v))
            else:
                if v is True:
                    args.append("--%s" % dashify(k))
                elif type(v) is not bool:
                    args.append("--%s=%s" % (dashify(k), v))
        return args

    def git(self, cmd, *args, **kwargs):
        # Handle optional arguments prior to calling transform_kwargs
        # otherwise they'll end up in args, which is bad.
        _kwargs = dict(_cwd=self._git_cwd)
        execute_kwargs = ('_cwd', '_decode', '_encoding',
                '_stdin', '_stdout', '_stderr', '_raw')
        for kwarg in execute_kwargs:
            if kwarg in kwargs:
                _kwargs[kwarg] = kwargs.pop(kwarg)

        # Prepare the argument list
        opt_args = self.transform_kwargs(**kwargs)
        call = ['git', dashify(cmd)] + opt_args
        call.extend(args)
        try:
            return self.execute(call, **_kwargs)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e
            core.stderr("ERROR: Unable to execute 'git'.\n"
                        "Ensure that 'git' is in your $PATH, or specify the "
                        "path to 'git' using the --git-path argument.")
            sys.exit(1)


@memoize
def instance():
    """Return the Git singleton"""
    return Git()


git = instance()
"""
Git command singleton

>>> from cola.git import git
>>> from cola.git import STDOUT
>>> 'git' == git.version()[STDOUT][:3].lower()
True

"""

########NEW FILE########
__FILENAME__ = gitcfg
from __future__ import division, absolute_import, unicode_literals

import copy
import fnmatch
from os.path import join

from cola import core
from cola import git
from cola import observable
from cola.decorators import memoize
from cola.git import STDOUT
from cola.compat import ustr

@memoize
def instance():
    """Return a static GitConfig instance."""
    return GitConfig()

_USER_CONFIG = core.expanduser(join('~', '.gitconfig'))
_USER_XDG_CONFIG = core.expanduser(
        join(core.getenv('XDG_CONFIG_HOME', join('~', '.config')),
             'git', 'config'))

def _stat_info():
    # Try /etc/gitconfig as a fallback for the system config
    paths = (('system', '/etc/gitconfig'),
             ('user', _USER_XDG_CONFIG),
             ('user', _USER_CONFIG),
             ('repo', git.instance().git_path('config')))
    statinfo = []
    for category, path in paths:
        try:
            statinfo.append((category, path, core.stat(path).st_mtime))
        except OSError:
            continue
    return statinfo


def _cache_key():
    # Try /etc/gitconfig as a fallback for the system config
    paths = ('/etc/gitconfig',
             _USER_XDG_CONFIG,
             _USER_CONFIG,
             git.instance().git_path('config'))
    mtimes = []
    for path in paths:
        try:
            mtimes.append(core.stat(path).st_mtime)
        except OSError:
            continue
    return mtimes


class GitConfig(observable.Observable):
    """Encapsulate access to git-config values."""

    message_user_config_changed = 'user_config_changed'
    message_repo_config_changed = 'repo_config_changed'

    def __init__(self):
        observable.Observable.__init__(self)
        self.git = git.instance()
        self._map = {}
        self._system = {}
        self._user = {}
        self._repo = {}
        self._all = {}
        self._cache_key = None
        self._configs = []
        self._config_files = {}
        self._value_cache = {}
        self._attr_cache = {}
        self._find_config_files()

    def reset(self):
        self._map.clear()
        self._system.clear()
        self._user.clear()
        self._repo.clear()
        self._all.clear()
        self._cache_key = None
        self._configs = []
        self._config_files.clear()
        self._value_cache = {}
        self._attr_cache = {}
        self._find_config_files()

    def user(self):
        return copy.deepcopy(self._user)

    def repo(self):
        return copy.deepcopy(self._repo)

    def all(self):
        return copy.deepcopy(self._all)

    def _find_config_files(self):
        """
        Classify git config files into 'system', 'user', and 'repo'.

        Populates self._configs with a list of the files in
        reverse-precedence order.  self._config_files is populated with
        {category: path} where category is one of 'system', 'user', or 'repo'.

        """
        # Try the git config in git's installation prefix
        statinfo = _stat_info()
        self._configs = map(lambda x: x[1], statinfo)
        self._config_files = {}
        for (cat, path, mtime) in statinfo:
            self._config_files[cat] = path

    def update(self):
        """Read config values from git."""
        if self._cached():
            return
        self._read_configs()

    def _cached(self):
        """
        Return True when the cache matches.

        Updates the cache and returns False when the cache does not match.

        """
        cache_key = _cache_key()
        if self._cache_key is None or cache_key != self._cache_key:
            self._cache_key = cache_key
            return False
        return True

    def _read_configs(self):
        """Read git config value into the system, user and repo dicts."""
        self._map.clear()
        self._system.clear()
        self._user.clear()
        self._repo.clear()
        self._all.clear()

        if 'system' in self._config_files:
            self._system.update(
                    self.read_config(self._config_files['system']))

        if 'user' in self._config_files:
            self._user.update(
                    self.read_config(self._config_files['user']))

        if 'repo' in self._config_files:
            self._repo.update(
                    self.read_config(self._config_files['repo']))

        for dct in (self._system, self._user, self._repo):
            self._all.update(dct)

    def read_config(self, path):
        """Return git config data from a path as a dictionary."""
        dest = {}
        args = ('--null', '--file', path, '--list')
        config_lines = self.git.config(*args)[STDOUT].split('\0')
        for line in config_lines:
            try:
                k, v = line.split('\n', 1)
            except ValueError:
                # the user has an invalid entry in their git config
                if not line:
                    continue
                k = line
                v = 'true'

            if v in ('true', 'yes'):
                v = True
            elif v in ('false', 'no'):
                v = False
            else:
                try:
                    v = int(v)
                except ValueError:
                    pass
            self._map[k.lower()] = k
            dest[k] = v
        return dest

    def _get(self, src, key, default):
        self.update()
        try:
            return src[key]
        except KeyError:
            pass
        key = self._map.get(key.lower(), key)
        try:
            return src[key]
        except KeyError:
            return src.get(key.lower(), default)

    def get(self, key, default=None):
        """Return the string value for a config key."""
        return self._get(self._all, key, default)

    def get_user(self, key, default=None):
        return self._get(self._user, key, default)

    def get_repo(self, key, default=None):
        return self._get(self._repo, key, default)

    def python_to_git(self, value):
        if type(value) is bool:
            if value:
                return 'true'
            else:
                return 'false'
        if type(value) is int:
            return ustr(value)
        return value

    def set_user(self, key, value):
        msg = self.message_user_config_changed
        self.git.config('--global', key, self.python_to_git(value))
        self.update()
        self.notify_observers(msg, key, value)

    def set_repo(self, key, value):
        msg = self.message_repo_config_changed
        self.git.config(key, self.python_to_git(value))
        self.update()
        self.notify_observers(msg, key, value)

    def find(self, pat):
        pat = pat.lower()
        match = fnmatch.fnmatch
        result = {}
        self.update()
        for key, val in self._all.items():
            if match(key, pat):
                result[key] = val
        return result

    def get_cached(self, key, default=None):
        cache = self._value_cache
        try:
            value = cache[key]
        except KeyError:
            value = cache[key] = self.get(key, default=default)
        return value

    def gui_encoding(self):
        return self.get_cached('gui.encoding', default='utf-8')

    def is_per_file_attrs_enabled(self):
        return self.get_cached('cola.fileattributes', default=False)

    def file_encoding(self, path):
        if not self.is_per_file_attrs_enabled():
            return None
        cache = self._attr_cache
        try:
            value = cache[path]
        except KeyError:
            value = cache[path] = self._file_encoding(path)
        return value

    def _file_encoding(self, path):
        """Return the file encoding for a path"""
        status, out, err = self.git.check_attr('encoding', '--', path)
        if status != 0:
            return None
        header = '%s: encoding: ' % path
        if out.startswith(header):
            encoding = out[len(header):].strip()
            if (encoding != 'unspecified' and
                    encoding != 'unset' and
                    encoding != 'set'):
                return encoding
        return None

    guitool_opts = ('cmd', 'needsfile', 'noconsole', 'norescan', 'confirm',
                    'argprompt', 'revprompt', 'revunmerged', 'title', 'prompt')

    def get_guitool_opts(self, name):
        """Return the guitool.<name> namespace as a dict"""
        keyprefix = 'guitool.' + name + '.'
        opts = {}
        for cfg in self.guitool_opts:
            value = self.get(keyprefix + cfg)
            if value is None:
                continue
            opts[cfg] = value
        return opts

    def get_guitool_names(self):
        guitools = self.find('guitool.*.cmd')
        prefix = len('guitool.')
        suffix = len('.cmd')
        return sorted([name[prefix:-suffix]
                        for (name, cmd) in guitools.items()])

########NEW FILE########
__FILENAME__ = gitcmds
"""Provides commands and queries for Git."""
from __future__ import division, absolute_import, unicode_literals

import re
from io import StringIO

from cola import core
from cola import gitcfg
from cola import utils
from cola import version
from cola.git import git
from cola.git import STDOUT
from cola.i18n import N_

config = gitcfg.instance()


class InvalidRepositoryError(Exception):
    pass


def default_remote(config=None):
    """Return the remote tracked by the current branch."""
    if config is None:
        config = gitcfg.instance()
    return config.get('branch.%s.remote' % current_branch())


def diff_index_filenames(ref):
    """Return a of filenames that have been modified relative to the index"""
    out = git.diff_index(ref, name_only=True, z=True)[STDOUT]
    return _parse_diff_filenames(out)


def diff_filenames(*args):
    """Return a list of filenames that have been modified"""
    out = git.diff_tree(name_only=True, no_commit_id=True, r=True, z=True,
                        *args)[STDOUT]
    return _parse_diff_filenames(out)


def diff(args):
    """Return a list of filenames for the given diff arguments

    :param args: list of arguments to pass to "git diff --name-only"

    """
    out = git.diff(name_only=True, z=True, *args)[STDOUT]
    return _parse_diff_filenames(out)


def _parse_diff_filenames(out):
    if out:
        return out[:-1].split('\0')
    else:
        return []


def all_files():
    """Return the names of all files in the repository"""
    out = git.ls_files(z=True)[STDOUT]
    if out:
        return out[:-1].split('\0')
    else:
        return []


class _current_branch:
    """Cache for current_branch()"""
    key = None
    value = None


def clear_cache():
    _current_branch.key = None


def current_branch():
    """Return the current branch"""
    head = git.git_path('HEAD')
    try:
        key = core.stat(head).st_mtime
        if _current_branch.key == key:
            return _current_branch.value
    except OSError:
        pass
    status, data, err = git.rev_parse('HEAD', symbolic_full_name=True)
    if status != 0:
        # git init -- read .git/HEAD.  We could do this unconditionally...
        data = _read_git_head(head)

    for refs_prefix in ('refs/heads/', 'refs/remotes/', 'refs/tags/'):
        if data.startswith(refs_prefix):
            value = data[len(refs_prefix):]
            _current_branch.key = key
            _current_branch.value = value
            return value
    # Detached head
    return data


def _read_git_head(head, default='master', git=git):
    """Pure-python .git/HEAD reader"""
    # Legacy .git/HEAD symlinks
    if core.islink(head):
        refs_heads = core.realpath(git.git_path('refs', 'heads'))
        path = core.abspath(head).replace('\\', '/')
        if path.startswith(refs_heads + '/'):
            return path[len(refs_heads)+1:]

    # Common .git/HEAD "ref: refs/heads/master" file
    elif core.isfile(head):
        data = core.read(head).rstrip()
        ref_prefix = 'ref: '
        if data.startswith(ref_prefix):
            return data[len(ref_prefix):]
        # Detached head
        return data

    return default


def branch_list(remote=False):
    """
    Return a list of local or remote branches

    This explicitly removes HEAD from the list of remote branches.

    """
    if remote:
        return for_each_ref_basename('refs/remotes')
    else:
        return for_each_ref_basename('refs/heads')


def for_each_ref_basename(refs, git=git):
    """Return refs starting with 'refs'."""
    out = git.for_each_ref(refs, format='%(refname)')[STDOUT]
    output = out.splitlines()
    non_heads = filter(lambda x: not x.endswith('/HEAD'), output)
    return list(map(lambda x: x[len(refs) + 1:], non_heads))


def all_refs(split=False, git=git):
    """Return a tuple of (local branches, remote branches, tags)."""
    local_branches = []
    remote_branches = []
    tags = []
    triple = lambda x, y: (x, len(x) + 1, y)
    query = (triple('refs/tags', tags),
             triple('refs/heads', local_branches),
             triple('refs/remotes', remote_branches))
    out = git.for_each_ref(format='%(refname)')[STDOUT]
    for ref in out.splitlines():
        for prefix, prefix_len, dst in query:
            if ref.startswith(prefix) and not ref.endswith('/HEAD'):
                dst.append(ref[prefix_len:])
                continue
    if split:
        return local_branches, remote_branches, tags
    else:
        return local_branches + remote_branches + tags


def tracked_branch(branch=None, config=None):
    """Return the remote branch associated with 'branch'."""
    if config is None:
        config = gitcfg.instance()
    if branch is None:
        branch = current_branch()
    if branch is None:
        return None
    remote = config.get('branch.%s.remote' % branch)
    if not remote:
        return None
    merge_ref = config.get('branch.%s.merge' % branch)
    if not merge_ref:
        return None
    refs_heads = 'refs/heads/'
    if merge_ref.startswith(refs_heads):
        return remote + '/' + merge_ref[len(refs_heads):]
    return None


def untracked_files(git=git):
    """Returns a sorted list of untracked files."""
    out = git.ls_files(z=True, others=True, exclude_standard=True)[STDOUT]
    if out:
        return out[:-1].split('\0')
    return []


def tag_list():
    """Return a list of tags."""
    return list(reversed(for_each_ref_basename('refs/tags')))


def log(git, *args, **kwargs):
    return git.log(no_color=True, no_ext_diff=True, *args, **kwargs)[STDOUT]


def commit_diff(sha1, git=git):
    return log(git, '-1', sha1, '--') + '\n\n' + sha1_diff(git, sha1)


_diff_overrides = {}
def update_diff_overrides(space_at_eol, space_change,
                          all_space, function_context):
    _diff_overrides['ignore_space_at_eol'] = space_at_eol
    _diff_overrides['ignore_space_change'] = space_change
    _diff_overrides['ignore_all_space'] = all_space
    _diff_overrides['function_context'] = function_context


def common_diff_opts(config=config):
    submodule = version.check('diff-submodule', version.git_version())
    opts = {
        'patience': True,
        'submodule': submodule,
        'no_color': True,
        'no_ext_diff': True,
        'unified': config.get('gui.diffcontext', 3),
        '_raw': True,
    }
    opts.update(_diff_overrides)
    return opts


def sha1_diff(git, sha1, filename=None):
    if filename is None:
        return git.diff(sha1+'^!', **common_diff_opts())[STDOUT]
    else:
        return git.diff(sha1+'^!', filename, **common_diff_opts())[STDOUT]


def diff_info(sha1, git=git, filename=None):
    decoded = log(git, '-1', sha1, '--', pretty='format:%b').strip()
    if decoded:
        decoded += '\n\n'
    return decoded + sha1_diff(git, sha1, filename=filename)


def diff_helper(commit=None,
                ref=None,
                endref=None,
                filename=None,
                cached=True,
                head=None,
                amending=False,
                with_diff_header=False,
                suppress_header=True,
                reverse=False,
                git=git):
    "Invokes git diff on a filepath."
    if commit:
        ref, endref = commit+'^', commit
    argv = []
    if ref and endref:
        argv.append('%s..%s' % (ref, endref))
    elif ref:
        for r in utils.shell_split(ref.strip()):
            argv.append(r)
    elif head and amending and cached:
        argv.append(head)

    encoding = None
    if filename:
        argv.append('--')
        if type(filename) is list:
            argv.extend(filename)
        else:
            argv.append(filename)
            encoding = config.file_encoding(filename)

    if filename is not None:
        deleted = cached and not core.exists(filename)
    else:
        deleted = False

    status, out, err = git.diff(R=reverse, M=True, cached=cached,
                                _encoding=encoding,
                                *argv,
                                **common_diff_opts())
    if status != 0:
        # git init
        if with_diff_header:
            return ('', '')
        else:
            return ''

    return extract_diff_header(status, deleted,
                               with_diff_header, suppress_header, out)


def extract_diff_header(status, deleted,
                        with_diff_header, suppress_header, diffoutput):
    headers = []

    if diffoutput.startswith('Submodule'):
        if with_diff_header:
            return ('', diffoutput)
        else:
            return diffoutput

    start = False
    del_tag = 'deleted file mode '
    output = StringIO()

    diff = diffoutput.split('\n')
    for line in diff:
        if not start and '@@' == line[:2] and '@@' in line[2:]:
            start = True
        if start or (deleted and del_tag in line):
            output.write(line + '\n')
        else:
            if with_diff_header:
                headers.append(line)
            elif not suppress_header:
                output.write(line + '\n')

    result = output.getvalue()
    output.close()

    if with_diff_header:
        return('\n'.join(headers), result)
    else:
        return result


def format_patchsets(to_export, revs, output='patches'):
    """
    Group contiguous revision selection into patchsets

    Exists to handle multi-selection.
    Multiple disparate ranges in the revision selection
    are grouped into continuous lists.

    """

    outs = []
    errs = []

    cur_rev = to_export[0]
    cur_master_idx = revs.index(cur_rev)

    patches_to_export = [[cur_rev]]
    patchset_idx = 0

    # Group the patches into continuous sets
    for idx, rev in enumerate(to_export[1:]):
        # Limit the search to the current neighborhood for efficiency
        master_idx = revs[cur_master_idx:].index(rev)
        master_idx += cur_master_idx
        if master_idx == cur_master_idx + 1:
            patches_to_export[ patchset_idx ].append(rev)
            cur_master_idx += 1
            continue
        else:
            patches_to_export.append([ rev ])
            cur_master_idx = master_idx
            patchset_idx += 1

    # Export each patchsets
    status = 0
    for patchset in patches_to_export:
        stat, out, err = export_patchset(patchset[0],
                                         patchset[-1],
                                         output='patches',
                                         n=len(patchset) > 1,
                                         thread=True,
                                         patch_with_stat=True)
        outs.append(out)
        if err:
            errs.append(err)
        status = max(stat, status)
    return (status, '\n'.join(outs), '\n'.join(errs))


def export_patchset(start, end, output='patches', **kwargs):
    """Export patches from start^ to end."""
    return git.format_patch('-o', output, start + '^..' + end, **kwargs)


def unstage_paths(args, head='HEAD'):
    status, out, err = git.reset(head, '--', *set(args))
    if status == 128:
        # handle git init: we have to use 'git rm --cached'
        # detect this condition by checking if the file is still staged
        return untrack_paths(args, head=head)
    else:
        return (status, out, err)


def untrack_paths(args, head='HEAD'):
    if not args:
        return (-1, N_('Nothing to do'), '')
    return git.update_index('--', force_remove=True, *set(args))


def worktree_state(head='HEAD'):
    """Return a tuple of files in various states of being

    Can be staged, unstaged, untracked, unmerged, or changed
    upstream.

    """
    state = worktree_state_dict(head=head)
    return(state.get('staged', []),
           state.get('modified', []),
           state.get('unmerged', []),
           state.get('untracked', []),
           state.get('upstream_changed', []))


def worktree_state_dict(head='HEAD', update_index=False, display_untracked=True):
    """Return a dict of files in various states of being

    :rtype: dict, keys are staged, unstaged, untracked, unmerged,
            changed_upstream, and submodule.

    """
    if update_index:
        git.update_index(refresh=True)

    staged, unmerged, staged_submods = diff_index(head)
    modified, modified_submods = diff_worktree()
    untracked = display_untracked and untracked_files() or []

    # Remove unmerged paths from the modified list
    unmerged_set = set(unmerged)
    modified_set = set(modified)
    modified_unmerged = modified_set.intersection(unmerged_set)
    for path in modified_unmerged:
        modified.remove(path)

    # All submodules
    submodules = staged_submods.union(modified_submods)

    # Only include the submodule in the staged list once it has
    # been staged.  Otherwise, we'll see the submodule as being
    # both modified and staged.
    modified_submods = modified_submods.difference(staged_submods)

    # Add submodules to the staged and unstaged lists
    staged.extend(list(staged_submods))
    modified.extend(list(modified_submods))

    # Look for upstream modified files if this is a tracking branch
    upstream_changed = diff_upstream(head)

    # Keep stuff sorted
    staged.sort()
    modified.sort()
    unmerged.sort()
    untracked.sort()
    upstream_changed.sort()

    return {'staged': staged,
            'modified': modified,
            'unmerged': unmerged,
            'untracked': untracked,
            'upstream_changed': upstream_changed,
            'submodules': submodules}


def diff_index(head, cached=True):
    submodules = set()
    staged = []
    unmerged = []

    status, out, err = git.diff_index(head, '--', cached=cached, z=True)
    if status != 0:
        # handle git init
        return all_files(), unmerged, submodules

    while out:
        rest, out = out.split('\0', 1)
        name, out = out.split('\0', 1)
        status = rest[-1]
        if '160000' in rest[1:14]:
            submodules.add(name)
        elif status  in 'DAMT':
            staged.append(name)
        elif status == 'U':
            unmerged.append(name)

    return staged, unmerged, submodules


def diff_worktree():
    modified = []
    submodules = set()

    status, out, err = git.diff_files(z=True)
    if status != 0:
        # handle git init
        out = git.ls_files(modified=True, z=True)[STDOUT]
        if out:
            modified = out[:-1].split('\0')
        return modified, submodules

    while out:
        rest, out = out.split('\0', 1)
        name, out = out.split('\0', 1)
        status = rest[-1]
        if '160000' in rest[1:14]:
            submodules.add(name)
        elif status in 'DAMT':
            modified.append(name)

    return modified, submodules


def diff_upstream(head):
    tracked = tracked_branch()
    if not tracked:
        return []
    base = merge_base(head, tracked)
    return diff_filenames(base, tracked)


def _branch_status(branch):
    """
    Returns a tuple of staged, unstaged, untracked, and unmerged files

    This shows only the changes that were introduced in branch

    """
    staged = diff_filenames(branch)
    return {'staged': staged,
            'upstream_changed': staged}


def merge_base(head, ref):
    """Given `ref`, return $(git merge-base ref HEAD)..ref."""
    return git.merge_base(head, ref)[STDOUT]


def merge_base_parent(branch):
    tracked = tracked_branch(branch=branch)
    if tracked:
        return tracked
    return 'HEAD'


def parse_ls_tree(rev):
    """Return a list of(mode, type, sha1, path) tuples."""
    output = []
    lines = git.ls_tree(rev, r=True)[STDOUT].splitlines()
    regex = re.compile(r'^(\d+)\W(\w+)\W(\w+)[ \t]+(.*)$')
    for line in lines:
        match = regex.match(line)
        if match:
            mode = match.group(1)
            objtype = match.group(2)
            sha1 = match.group(3)
            filename = match.group(4)
            output.append((mode, objtype, sha1, filename,) )
    return output


# A regex for matching the output of git(log|rev-list) --pretty=oneline
REV_LIST_REGEX = re.compile(r'^([0-9a-f]{40}) (.*)$')

def parse_rev_list(raw_revs):
    """Parse `git log --pretty=online` output into (SHA-1, summary) pairs."""
    revs = []
    for line in raw_revs.splitlines():
        match = REV_LIST_REGEX.match(line)
        if match:
            rev_id = match.group(1)
            summary = match.group(2)
            revs.append((rev_id, summary,))
    return revs


def log_helper(all=False, extra_args=None):
    """Return parallel arrays containing the SHA-1s and summaries."""
    revs = []
    summaries = []
    args = []
    if extra_args:
        args = extra_args
    output = log(git, pretty='oneline', all=all, *args)
    for line in output.splitlines():
        match = REV_LIST_REGEX.match(line)
        if match:
            revs.append(match.group(1))
            summaries.append(match.group(2))
    return (revs, summaries)


def rev_list_range(start, end):
    """Return a (SHA-1, summary) pairs between start and end."""
    revrange = '%s..%s' % (start, end)
    out = git.rev_list(revrange, pretty='oneline')[STDOUT]
    return parse_rev_list(out)


def commit_message_path():
    """Return the path to .git/GIT_COLA_MSG"""
    path = git.git_path("GIT_COLA_MSG")
    if core.exists(path):
        return path
    return None


def merge_message_path():
    """Return the path to .git/MERGE_MSG or .git/SQUASH_MSG."""
    for basename in ('MERGE_MSG', 'SQUASH_MSG'):
        path = git.git_path(basename)
        if core.exists(path):
            return path
    return None


def abort_merge():
    """Abort a merge by reading the tree at HEAD."""
    # Reset the worktree
    git.read_tree('HEAD', reset=True, u=True, v=True)
    # remove MERGE_HEAD
    merge_head = git.git_path('MERGE_HEAD')
    if core.exists(merge_head):
        core.unlink(merge_head)
    # remove MERGE_MESSAGE, etc.
    merge_msg_path = merge_message_path()
    while merge_msg_path:
        core.unlink(merge_msg_path)
        merge_msg_path = merge_message_path()


def merge_message(revision):
    """Return a merge message for FETCH_HEAD."""
    fetch_head = git.git_path('FETCH_HEAD')
    if core.exists(fetch_head):
        return git.fmt_merge_msg('--file', fetch_head)[STDOUT]
    return "Merge branch '%s'" % revision

########NEW FILE########
__FILENAME__ = gravatar
from __future__ import division, absolute_import, unicode_literals

import time

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtNetwork
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import resources
from cola import core
from cola.compat import ustr, urllib
import hashlib


class Gravatar(object):
    @staticmethod
    def url_for_email(email, imgsize):
        email_hash = hashlib.md5(core.encode(email)).hexdigest()
        default_url = b'http://git-cola.github.io/images/git-64x64.jpg'
        encoded_url = urllib.quote(default_url, b'')
        query = '?s=%d&d=%s' % (imgsize, encoded_url)
        url = 'http://gravatar.com/avatar/' + email_hash + query
        return url


class GravatarLabel(QtGui.QLabel):
    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)

        self.email = None
        self.response = None
        self.timeout = 0
        self.imgsize = 48
        self.pixmaps = {}

        self.network = QtNetwork.QNetworkAccessManager()
        self.connect(self.network,
                     SIGNAL('finished(QNetworkReply*)'),
                     self.network_finished)

    def set_email(self, email):
        if email in self.pixmaps:
            self.setPixmap(self.pixmaps[email])
            return
        if (self.timeout > 0 and
                (int(time.time()) - self.timeout) < (5 * 60)):
            self.set_pixmap_from_response()
            return
        if email == self.email and self.response is not None:
            self.set_pixmap_from_response()
            return
        self.email = email
        self.request(email)

    def request(self, email):
        url = Gravatar.url_for_email(email, self.imgsize)
        self.network.get(QtNetwork.QNetworkRequest(QtCore.QUrl(url)))

    def default_pixmap_as_bytes(self):
        xres = self.imgsize
        pixmap = QtGui.QPixmap(resources.icon('git.svg'))
        pixmap = pixmap.scaledToHeight(xres, Qt.SmoothTransformation)
        byte_array = QtCore.QByteArray()
        buf = QtCore.QBuffer(byte_array)
        buf.open(QtCore.QIODevice.WriteOnly)
        pixmap.save(buf, 'PNG')
        buf.close()
        return byte_array

    def network_finished(self, reply):
        email = self.email

        header = QtCore.QByteArray('Location')
        raw_header = reply.rawHeader(header)
        if raw_header:
            location = ustr(QtCore.QString(raw_header)).strip()
            request_location = ustr(
                    Gravatar.url_for_email(self.email, self.imgsize))
            relocated = location != request_location
        else:
            relocated = False

        if reply.error() == QtNetwork.QNetworkReply.NoError:
            if relocated:
                # We could do get_url(urllib.unquote(location)) to
                # download the default image.
                # Save bandwidth by using a pixmap.
                self.response = self.default_pixmap_as_bytes()
            else:
                self.response = reply.readAll()
            self.timeout = 0
        else:
            self.response = self.default_pixmap_as_bytes()
            self.timeout = int(time.time())

        pixmap = self.set_pixmap_from_response()

        # If the email has not changed (e.g. no other requests)
        # then we know that this pixmap corresponds to this specific
        # email address.  We can't blindly trust self.email else
        # we may add cache entries for thee wrong email address.
        url = Gravatar.url_for_email(email, self.imgsize)
        if url == ustr(reply.url().toString()):
            self.pixmaps[email] = pixmap

    def set_pixmap_from_response(self):
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(self.response)
        self.setPixmap(pixmap)
        return pixmap

########NEW FILE########
__FILENAME__ = guicmds
from __future__ import division, absolute_import, unicode_literals

import os
import re

from PyQt4 import QtGui

from cola import cmds
from cola import core
from cola import difftool
from cola import gitcmds
from cola import qtutils
from cola.git import git
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.widgets import completion
from cola.widgets.browse import BrowseDialog
from cola.widgets.selectcommits import select_commits
from cola.compat import ustr


def delete_branch():
    """Launch the 'Delete Branch' dialog."""
    branch = choose_branch(N_('Delete Branch'), N_('Delete'))
    if not branch:
        return
    cmds.do(cmds.DeleteBranch, branch)


def delete_remote_branch():
    """Launch the 'Delete Remote Branch' dialog."""
    branch = choose_remote_branch(N_('Delete Remote Branch'), N_('Delete'))
    if not branch:
        return
    rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
    match = rgx.match(branch)
    if match:
        remote = match.group('remote')
        branch = match.group('branch')
        cmds.do(cmds.DeleteRemoteBranch, remote, branch)


def browse_current():
    """Launch the 'Browse Current Branch' dialog."""
    branch = gitcmds.current_branch()
    BrowseDialog.browse(branch)


def browse_other():
    """Prompt for a branch and inspect content at that point in time."""
    # Prompt for a branch to browse
    branch = choose_ref(N_('Browse Commits...'), N_('Browse'))
    if not branch:
        return
    BrowseDialog.browse(branch)


def checkout_branch():
    """Launch the 'Checkout Branch' dialog."""
    branch = choose_branch(N_('Checkout Branch'), N_('Checkout'))
    if not branch:
        return
    cmds.do(cmds.CheckoutBranch, branch)


def cherry_pick():
    """Launch the 'Cherry-Pick' dialog."""
    revs, summaries = gitcmds.log_helper(all=True)
    commits = select_commits(N_('Cherry-Pick Commit'),
                             revs, summaries, multiselect=False)
    if not commits:
        return
    cmds.do(cmds.CherryPick, commits)


def new_repo():
    """Prompt for a new directory and create a new Git repository

    :returns str: repository path or None if no repository was created.

    """
    dlg = QtGui.QFileDialog()
    dlg.setFileMode(QtGui.QFileDialog.Directory)
    dlg.setOption(QtGui.QFileDialog.ShowDirsOnly)
    dlg.show()
    dlg.raise_()
    if dlg.exec_() != QtGui.QFileDialog.Accepted:
        return None
    paths = dlg.selectedFiles()
    if not paths:
        return None
    path = ustr(paths[0])
    if not path:
        return None
    # Avoid needlessly calling `git init`.
    if git.is_git_dir(path):
        # We could prompt here and confirm that they really didn't
        # mean to open an existing repository, but I think
        # treating it like an "Open" is a sensible DWIM answer.
        return path

    status, out, err = core.run_command(['git', 'init', path])
    if status == 0:
        return path
    else:
        title = N_('Error Creating Repository')
        msg = (N_('"%(command)s" returned exit status %(status)d') %
               dict(command='git init %s' % path, status=status))
        details = N_('Output:\n%s') % out
        if err:
            details += '\n\n'
            details += N_('Errors: %s') % err
        qtutils.critical(title, msg, details)
        return None


def open_new_repo():
    dirname = new_repo()
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, dirname)


def clone_repo(spawn=True):
    """
    Present GUI controls for cloning a repository

    A new cola session is invoked when 'spawn' is True.

    """
    url, ok = qtutils.prompt(N_('Path or URL to clone (Env. $VARS okay)'))
    url = os.path.expandvars(url)
    if not ok or not url:
        return None
    try:
        # Pick a suitable basename by parsing the URL
        newurl = url.replace('\\', '/').rstrip('/')
        default = newurl.rsplit('/', 1)[-1]
        if default == '.git':
            # The end of the URL is /.git, so assume it's a file path
            default = os.path.basename(os.path.dirname(newurl))
        if default.endswith('.git'):
            # The URL points to a bare repo
            default = default[:-4]
        if url == '.':
            # The URL is the current repo
            default = os.path.basename(core.getcwd())
        if not default:
            raise
    except:
        Interaction.information(
                N_('Error Cloning'),
                N_('Could not parse Git URL: "%s"') % url)
        Interaction.log(N_('Could not parse Git URL: "%s"') % url)
        return None

    # Prompt the user for a directory to use as the parent directory
    msg = N_('Select a parent directory for the new clone')
    dirname = qtutils.opendir_dialog(msg, main.model().getcwd())
    if not dirname:
        return None
    count = 1
    destdir = os.path.join(dirname, default)
    olddestdir = destdir
    if core.exists(destdir):
        # An existing path can be specified
        msg = (N_('"%s" already exists, cola will create a new directory') %
               destdir)
        Interaction.information('Directory Exists', msg)

    # Make sure the new destdir doesn't exist
    while core.exists(destdir):
        destdir = olddestdir + str(count)
        count += 1
    if cmds.do(cmds.Clone, url, destdir, spawn=spawn):
        return destdir
    return None


def export_patches():
    """Run 'git format-patch' on a list of commits."""
    revs, summaries = gitcmds.log_helper()
    to_export = select_commits(N_('Export Patches'), revs, summaries)
    if not to_export:
        return
    cmds.do(cmds.FormatPatch, reversed(to_export), reversed(revs))


def diff_expression():
    """Diff using an arbitrary expression."""
    tracked = gitcmds.tracked_branch()
    current = gitcmds.current_branch()
    if tracked and current:
        ref = tracked + '..' + current
    else:
        ref = 'origin/master..'
    difftool.diff_expression(qtutils.active_window(), ref)


def open_repo():
    dirname = qtutils.opendir_dialog(N_('Open Git Repository...'),
                                     main.model().getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, dirname)


def open_repo_in_new_window():
    """Spawn a new cola session."""
    dirname = qtutils.opendir_dialog(N_('Open Git Repository...'),
                                     main.model().getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenNewRepo, dirname)


def load_commitmsg():
    """Load a commit message from a file."""
    filename = qtutils.open_file(N_('Load Commit Message'),
                                 directory=main.model().getcwd())
    if filename:
        cmds.do(cmds.LoadCommitMessageFromFile, filename)


def choose_from_dialog(get, title, button_text, default):
    parent = qtutils.active_window()
    return get(title, button_text, parent, default=default)


def choose_ref(title, button_text, default=None):
    return choose_from_dialog(completion.GitRefDialog.get,
                              title, button_text, default)


def choose_branch(title, button_text, default=None):
    return choose_from_dialog(completion.GitBranchDialog.get,
                              title, button_text, default)


def choose_remote_branch(title, button_text, default=None):
    return choose_from_dialog(completion.GitRemoteBranchDialog.get,
                              title, button_text, default)


def review_branch():
    """Diff against an arbitrary revision, branch, tag, etc."""
    branch = choose_ref(N_('Select Branch to Review'), N_('Review'))
    if not branch:
        return
    merge_base = gitcmds.merge_base_parent(branch)
    difftool.diff_commits(qtutils.active_window(), merge_base, branch)

########NEW FILE########
__FILENAME__ = i18n
"""i18n and l10n support for git-cola"""
from __future__ import division, absolute_import, unicode_literals

import gettext as _gettext
import os
import sys

from cola import compat
from cola import core
from cola import resources

_null_translation = _gettext.NullTranslations()
# Python 3 compat
if not hasattr(_null_translation, 'ugettext'):
    _null_translation.ugettext = _null_translation.gettext
    _null_translation.ungettext = _null_translation.ngettext
_translation = _null_translation


def gettext(s):
    txt = _translation.ugettext(s)
    if txt[-6:-4] == '@@': # handle @@verb / @@noun
        txt = txt[:-6]
    return txt


def ngettext(s, p, n):
    return _translation.ungettext(s, p, n)


def N_(s):
    return gettext(s)


def install(locale):
    global _translation
    if sys.platform == 'win32':
        _check_win32_locale()
    if locale:
        compat.setenv('LANGUAGE', locale)
        compat.setenv('LANG', locale)
        compat.setenv('LC_MESSAGES', locale)
    _install_custom_language()
    _gettext.textdomain('messages')
    _translation = _gettext.translation('git-cola',
                                        localedir=_get_locale_dir(),
                                        fallback=True)
    # Python 3 compat
    if not hasattr(_translation, 'ugettext'):
        _translation.ugettext = _translation.gettext
        _translation.ungettext = _translation.ngettext

def uninstall():
    global _translation
    _translation = _null_translation


def _get_locale_dir():
    return resources.prefix('share', 'locale')


def _install_custom_language():
    """Allow a custom language to be set in ~/.config/git-cola/language"""
    lang_file = resources.config_home('language')
    if not core.exists(lang_file):
        return
    try:
        lang = core.read(lang_file).strip()
    except:
        return
    if lang:
        compat.setenv('LANGUAGE', lang)


def _check_win32_locale():
    for i in ('LANGUAGE','LC_ALL','LC_MESSAGES','LANG'):
        if os.environ.get(i):
            break
    else:
        lang = None
        import locale
        try:
            import ctypes
        except ImportError:
            # use only user's default locale
            lang = locale.getdefaultlocale()[0]
        else:
            # using ctypes to determine all locales
            lcid_user = ctypes.windll.kernel32.GetUserDefaultLCID()
            lcid_system = ctypes.windll.kernel32.GetSystemDefaultLCID()
            if lcid_user != lcid_system:
                lcid = [lcid_user, lcid_system]
            else:
                lcid = [lcid_user]
            lang = [locale.windows_locale.get(i) for i in lcid]
            lang = ':'.join([i for i in lang if i])
        # set lang code for gettext
        if lang:
            compat.setenv('LANGUAGE', lang)

########NEW FILE########
__FILENAME__ = inotify
# Copyright (c) 2008 David Aguilar
"""Provides an inotify plugin for Linux and other systems with pyinotify"""
from __future__ import division, absolute_import, unicode_literals

import os
from threading import Timer
from threading import Lock

try:
    import pyinotify
    from pyinotify import ProcessEvent
    from pyinotify import WatchManager
    from pyinotify import Notifier
    from pyinotify import EventsCodes
    AVAILABLE = True
except ImportError:
    ProcessEvent = object
    AVAILABLE = False

from cola import utils
if utils.is_win32():
    try:
        import win32file
        import win32con
        import pywintypes
        import win32event
        AVAILABLE = True
    except ImportError:
        ProcessEvent = object
        AVAILABLE = False

from PyQt4 import QtCore

from cola import gitcfg
from cola import core
from cola.git import STDOUT
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main


_thread = None
_observers = []


def observer(fn):
    _observers.append(fn)


def start():
    global _thread

    cfg = gitcfg.instance()
    if not cfg.get('cola.inotify', True):
        msg = N_('inotify is disabled because "cola.inotify" is false')
        Interaction.log(msg)
        return

    if not AVAILABLE:
        if utils.is_win32():
            msg = N_('file notification: disabled\n'
                     'Note: install pywin32 to enable.\n')
        elif utils.is_linux():
            msg = N_('inotify: disabled\n'
                     'Note: install python-pyinotify to enable inotify.\n')
        else:
            return

        if utils.is_debian():
            msg += N_('On Debian systems '
                      'try: sudo aptitude install python-pyinotify')
        Interaction.log(msg)
        return

    # Start the notification thread
    _thread = GitNotifier()
    _thread.start()
    if utils.is_win32():
        msg = N_('File notification enabled.')
    else:
        msg = N_('inotify enabled.')
    Interaction.log(msg)


def stop():
    if not has_inotify():
        return
    _thread.stop(True)
    _thread.wait()


def has_inotify():
    """Return True if pyinotify is available."""
    return AVAILABLE and _thread and _thread.isRunning()


class Handler():
    """Queues filesystem events for broadcast"""

    def __init__(self):
        """Create an event handler"""
        ## Timer used to prevent notification floods
        self._timer = None
        ## Lock to protect files and timer from threading issues
        self._lock = Lock()

    def broadcast(self):
        """Broadcasts a list of all files touched since last broadcast"""
        with self._lock:
            for observer in _observers:
                observer()
            self._timer = None

    def handle(self, path):
        """Queues up filesystem events for broadcast"""
        with self._lock:
            if self._timer is None:
                self._timer = Timer(0.888, self.broadcast)
                self._timer.start()


class FileSysEvent(ProcessEvent):
    """Generated by GitNotifier in response to inotify events"""

    def __init__(self):
        """Maintain event state"""
        ProcessEvent.__init__(self)
        ## Takes care of Queueing events for broadcast
        self._handler = Handler()

    def process_default(self, event):
        """Queues up inotify events for broadcast"""
        if not event.name:
            return
        path = os.path.relpath(os.path.join(event.path, event.name))
        self._handler.handle(path)


class GitNotifier(QtCore.QThread):
    """Polls inotify for changes and generates FileSysEvents"""

    def __init__(self, timeout=333):
        """Set up the pyinotify thread"""
        QtCore.QThread.__init__(self)
        ## Git command object
        self._git = main.model().git
        ## pyinotify timeout
        self._timeout = timeout
        ## Path to monitor
        self._path = self._git.worktree()
        ## Signals thread termination
        self._running = True
        ## Directories to watching
        self._dirs_seen = set()
        ## The inotify watch manager instantiated in run()
        self._wmgr = None
        ## Events to capture
        if utils.is_linux():
            self._mask = (EventsCodes.ALL_FLAGS['IN_ATTRIB'] |
                          EventsCodes.ALL_FLAGS['IN_CLOSE_WRITE'] |
                          EventsCodes.ALL_FLAGS['IN_CREATE'] |
                          EventsCodes.ALL_FLAGS['IN_DELETE'] |
                          EventsCodes.ALL_FLAGS['IN_MODIFY'] |
                          EventsCodes.ALL_FLAGS['IN_MOVED_TO'])

    def stop(self, stopped):
        """Tells the GitNotifier to stop"""
        self._timeout = 0
        self._running = not stopped

    def _watch_directory(self, directory):
        """Set up a directory for monitoring by inotify"""
        if self._wmgr is None:
            return
        directory = core.realpath(directory)
        if directory in self._dirs_seen:
            return
        self._dirs_seen.add(directory)
        if core.exists(directory):
            self._wmgr.add_watch(directory, self._mask)

    def _is_pyinotify_08x(self):
        """Is this pyinotify 0.8.x?

        The pyinotify API changed between 0.7.x and 0.8.x.
        This allows us to maintain backwards compatibility.
        """
        if hasattr(pyinotify, '__version__'):
            if pyinotify.__version__[:3] == '0.8':
                return True
        return False

    def run(self):
        """Create the inotify WatchManager and generate FileSysEvents"""

        if utils.is_win32():
            self.run_win32()
            return

        # Only capture events that git cares about
        self._wmgr = WatchManager()
        if self._is_pyinotify_08x():
            notifier = Notifier(self._wmgr, FileSysEvent(),
                                timeout=self._timeout)
        else:
            notifier = Notifier(self._wmgr, FileSysEvent())

        self._watch_directory(self._path)

        # Register files/directories known to git
        for filename in self._git.ls_files()[STDOUT].splitlines():
            filename = core.realpath(filename)
            directory = os.path.dirname(filename)
            self._watch_directory(directory)

        # self._running signals app termination.  The timeout is a tradeoff
        # between fast notification response and waiting too long to exit.
        while self._running:
            if self._is_pyinotify_08x():
                check = notifier.check_events()
            else:
                check = notifier.check_events(timeout=self._timeout)
            if not self._running:
                break
            if check:
                notifier.read_events()
                notifier.process_events()
        notifier.stop()

    def run_win32(self):
        """Generate notifications using pywin32"""

        hdir = win32file.CreateFile(
                self._path,
                0x0001,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_BACKUP_SEMANTICS |
                win32con.FILE_FLAG_OVERLAPPED,
                None)

        flags = (win32con.FILE_NOTIFY_CHANGE_FILE_NAME |
                 win32con.FILE_NOTIFY_CHANGE_DIR_NAME |
                 win32con.FILE_NOTIFY_CHANGE_ATTRIBUTES |
                 win32con.FILE_NOTIFY_CHANGE_SIZE |
                 win32con.FILE_NOTIFY_CHANGE_LAST_WRITE |
                 win32con.FILE_NOTIFY_CHANGE_SECURITY)

        buf = win32file.AllocateReadBuffer(8192)
        overlapped = pywintypes.OVERLAPPED()
        overlapped.hEvent = win32event.CreateEvent(None, 0, 0, None)

        handler = Handler()
        while self._running:
            win32file.ReadDirectoryChangesW(hdir, buf, True, flags, overlapped)

            rc = win32event.WaitForSingleObject(overlapped.hEvent,
                                                self._timeout)
            if rc != win32event.WAIT_OBJECT_0:
                continue
            nbytes = win32file.GetOverlappedResult(hdir, overlapped, True)
            if not nbytes:
                continue
            results = win32file.FILE_NOTIFY_INFORMATION(buf, nbytes)
            for action, path in results:
                if not self._running:
                    break
                path = path.replace('\\', '/')
                if (not path.startswith('.git/') and
                        '/.git/' not in path and os.path.isfile(path)):
                    handler.handle(path)

########NEW FILE########
__FILENAME__ = interaction
from __future__ import division, absolute_import, unicode_literals

import os
import subprocess
from cola import core
from cola.i18n import N_


class Interaction(object):
    """Prompts the user and answers questions"""

    VERBOSE = bool(os.getenv('GIT_COLA_VERBOSE'))

    @staticmethod
    def information(title,
                    message=None, details=None, informative_text=None):
        if message is None:
            message = title
        scope = {}
        scope['title'] = title
        scope['title_dashes'] = '-' * len(title)
        scope['message'] = message
        scope['details'] = details and '\n'+details or ''
        scope['informative_text'] = (informative_text and
                '\n'+informative_text or '')
        print("""
%(title)s
%(title_dashes)s
%(message)s%(details)s%(informative_text)s""" % scope)

    @classmethod
    def critical(cls, title, message=None, details=None):
        """Show a warning with the provided title and message."""
        cls.information(title, message=message, details=details)

    @classmethod
    def confirm(cls, title, text, informative_text, ok_text,
                icon=None, default=True):

        cls.information(title, message=text,
                        informative_text=informative_text)
        if default:
            prompt = '%s? [Y/n]:' % ok_text
        else:
            prompt = '%s? [y/N]: ' % ok_text
        answer = raw_input(prompt)
        if answer == '':
            return default
        return answer.lower().startswith('y')

    @classmethod
    def question(cls, title, message, default=True):
        return cls.confirm(title, message, '',
                           ok_text=N_('Continue'), default=default)

    @classmethod
    def run_command(cls, title, cmd):
        cls.log('$ ' + subprocess.list2cmdline(cmd))
        status, out, err = core.run_command(cmd)
        cls.log_status(status, out, err)

    @classmethod
    def confirm_config_action(cls, name, opts):
        return cls.confirm(N_('Run %s?') % name,
                           N_('Run the "%s" command?') % name,
                           '',
                           ok_text=N_('Run'))

    @classmethod
    def log_status(cls, status, out, err=None):
        msg = (
           (out and ((N_('Output: %s') % out) + '\n') or '') +
           (err and ((N_('Errors: %s') % err) + '\n') or '') +
           N_('Exit code: %s') % status
        )
        cls.log(msg)

    @classmethod
    def log(cls, message):
        if cls.VERBOSE:
            core.stdout(message)

########NEW FILE########
__FILENAME__ = browse
from __future__ import division, absolute_import, unicode_literals

import time

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import gitcfg
from cola import core
from cola import utils
from cola import qtutils
from cola import version
from cola import resources
from cola.git import STDOUT
from cola.i18n import N_
from cola.models import main


# Custom event type for GitRepoInfoEvents
INFO_EVENT_TYPE = QtCore.QEvent.User + 42


class Columns(object):
    """Defines columns in the worktree browser"""

    NAME = 'Name'
    STATUS = 'Status'
    AGE = 'Age'
    MESSAGE = 'Message'
    AUTHOR = 'Author'
    ALL = (NAME, STATUS, AGE, MESSAGE, AUTHOR)

    @classmethod
    def text(cls, column):
        if column == cls.NAME:
            return N_('Name')
        elif column == cls.STATUS:
            return N_('Status')
        elif column == cls.AGE:
            return N_('Age')
        elif column == cls.MESSAGE:
            return N_('Message')
        elif column == cls.AUTHOR:
            return N_('Author')
        else:
            raise NotImplementedError('Mapping required for "%s"' % column)


class GitRepoModel(QtGui.QStandardItemModel):
    """Provides an interface into a git repository for browsing purposes."""
    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self._interesting_paths = self._get_paths()
        self._known_paths = set()

        self.connect(self, SIGNAL('updated'), self._updated_callback)
        model = main.model()
        model.add_observer(model.message_updated, self._model_updated)
        self._dir_rows = {}
        self.setColumnCount(len(Columns.ALL))
        for idx, header in enumerate(Columns.ALL):
            text = Columns.text(header)
            self.setHeaderData(idx, Qt.Horizontal, QtCore.QVariant(text))

        self._direntries = {'': self.invisibleRootItem()}
        self._initialize()

    def _create_column(self, col, path):
        """Creates a StandardItem for use in a treeview cell."""
        # GitRepoNameItem is the only one that returns a custom type(),
        # so we use to infer selections.
        if col == Columns.NAME:
            return GitRepoNameItem(path)
        return GitRepoItem(col, path)

    def _create_row(self, path):
        """Return a list of items representing a row."""
        return [self._create_column(c, path) for c in Columns.ALL]

    def _add_file(self, parent, path, insert=False):
        """Add a file entry to the model."""

        # Create model items
        row_items = self._create_row(path)

        # Use a standard file icon for the name field
        row_items[0].setIcon(qtutils.file_icon())

        if not insert:
            # Add file paths at the end of the list
            parent.appendRow(row_items)
            self.entry(path).update_name()
            self._known_paths.add(path)
            return
        # Entries exist so try to find an a good insertion point
        done = False
        for idx in range(parent.rowCount()):
            child = parent.child(idx, 0)
            if child.rowCount() > 0:
                continue
            if path < child.path:
                parent.insertRow(idx, row_items)
                done = True
                break

        # No adequate place found so simply append
        if not done:
            parent.appendRow(row_items)
        self.entry(path).update_name()
        self._known_paths.add(path)

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""

        # Create model items
        row_items = self._create_row(path)

        # Use a standard directory icon
        row_items[0].setIcon(qtutils.dir_icon())

        # Insert directories before file paths
        # TODO: have self._dir_rows's keys based on something less flaky than
        # QStandardItem instances.
        row = self._dir_rows.setdefault(id(parent), 0)
        parent.insertRow(row, row_items)
        self._dir_rows[id(parent)] += 1

        # Update the 'name' column for this entry
        self.entry(path).update_name()
        self._known_paths.add(path)

        return row_items[0]

    def path_is_interesting(self, path):
        """Return True if path has a status."""
        return path in self._interesting_paths

    def _get_paths(self):
        """Return paths of interest; e.g. paths with a status."""
        model = main.model()
        paths = set(model.staged + model.unstaged)
        return utils.add_parents(paths)

    def _model_updated(self):
        """Observes model changes and updates paths accordingly."""
        self.emit(SIGNAL('updated'))

    def _updated_callback(self):
        old_paths = self._interesting_paths
        new_paths = self._get_paths()
        for path in new_paths.union(old_paths):
            if path not in self._known_paths:
                continue
            self.entry(path).update()

        self._interesting_paths = new_paths

    def _initialize(self):
        """Iterate over the cola model and create GitRepoItems."""
        for path in main.model().everything():
            self.add_file(path)

    def add_file(self, path, insert=False):
        """Add a file to the model."""
        dirname = utils.dirname(path)
        if dirname in self._direntries:
            parent = self._direntries[dirname]
        else:
            parent = self._create_dir_entry(dirname, self._direntries)
            self._direntries[dirname] = parent
        self._add_file(parent, path, insert=insert)

    def _create_dir_entry(self, dirname, direntries):
        """
        Create a directory entry for the model.

        This ensures that directories are always listed before files.

        """
        entries = dirname.split('/')
        curdir = []
        parent = self.invisibleRootItem()
        curdir_append = curdir.append
        self_add_directory = self.add_directory
        for entry in entries:
            curdir_append(entry)
            path = '/'.join(curdir)
            if path in direntries:
                parent = direntries[path]
            else:
                grandparent = parent
                parent = self_add_directory(grandparent, path)
                direntries[path] = parent
        return parent

    def entry(self, path):
        """Return the GitRepoEntry for a path."""
        return GitRepoEntryManager.entry(path)


class GitRepoEntryManager(object):
    """
    Provides access to static instances of GitRepoEntry and model data.
    """
    static_entries = {}

    @classmethod
    def entry(cls, path, _static_entries=static_entries):
        """Return a static instance of a GitRepoEntry."""
        try:
            e = _static_entries[path]
        except KeyError:
            e = _static_entries[path] = GitRepoEntry(path)
        return e


class TaskRunner(object):
    """Manages QRunnable task instances to avoid python's garbage collector

    When PyQt stops referencing a QRunnable instance Python cleans it up
    which leads to segfaults, e.g. the dreaded "C++ object has gone away".

    This class keeps track of tasks and cleans up references to them as they
    complete.

    """
    singleton = None

    @classmethod
    def instance(cls):
        if cls.singleton is None:
            cls.singleton = TaskRunner()
        return cls.singleton

    def __init__(self):
        self.tasks = set()
        self.threadpool = QtCore.QThreadPool.globalInstance()
        self.notifier = QtCore.QObject()
        self.notifier.connect(self.notifier, SIGNAL('task_done'), self.task_done)

    def run(self, task):
        self.tasks.add(task)
        self.threadpool.start(task)

    def task_done(self, task):
        if task in self.tasks:
            self.tasks.remove(task)

    def cleanup_task(self, task):
        self.notifier.emit(SIGNAL('task_done'), task)


class GitRepoEntry(QtCore.QObject):
    """
    Provides asynchronous lookup of repository data for a path.

    Emits signal names matching those defined in Columns.

    """
    def __init__(self, path):
        QtCore.QObject.__init__(self)
        self.path = path

    def update_name(self):
        """Emits a signal corresponding to the entry's name."""
        # 'name' is cheap to calculate so simply emit a signal
        self.emit(SIGNAL(Columns.NAME), utils.basename(self.path))
        if '/' not in self.path:
            self.update()

    def update(self):
        """Starts a GitRepoInfoTask to calculate info for entries."""
        # GitRepoInfoTask handles expensive lookups
        task = GitRepoInfoTask(self.path)
        TaskRunner.instance().run(task)

    def event(self, e):
        """Receive GitRepoInfoEvents and emit corresponding Qt signals."""
        if e.type() == INFO_EVENT_TYPE:
            e.accept()
            self.emit(SIGNAL(e.signal), *e.data)
            return True
        return QtCore.QObject.event(self, e)


# Support older versions of PyQt
if version.check('pyqt_qrunnable', QtCore.PYQT_VERSION_STR):
    QRunnable = QtCore.QRunnable
else:
    class QRunnable(object):
        pass

class GitRepoInfoTask(QRunnable):
    """Handles expensive git lookups for a path."""
    def __init__(self, path):
        QRunnable.__init__(self)
        self.path = path
        self._cfg = gitcfg.instance()
        self._data = {}

    def data(self, key):
        """
        Return git data for a path.

        Supported keys are 'date', 'message', and 'author'

        """
        if not self._data:
            log_line = main.model().git.log('-1', '--', self.path,
                                            M=True,
                                            all=False,
                                            no_color=True,
                                            pretty='format:%ar%x01%s%x01%an'
                                            )[STDOUT]
            if log_line:
                log_line = log_line
                date, message, author = log_line.split(chr(0x01), 2)
                self._data['date'] = date
                self._data['message'] = message
                self._data['author'] = author
            else:
                self._data['date'] = self.date()
                self._data['message'] = '-'
                self._data['author'] = self._cfg.get('user.name', 'unknown')
        return self._data[key]

    def name(self):
        """Calculate the name for an entry."""
        return utils.basename(self.path)

    def date(self):
        """
        Returns a relative date for a file path.

        This is typically used for new entries that do not have
        'git log' information.

        """
        try:
            st = core.stat(self.path)
        except:
            return N_('%d minutes ago') % 0
        elapsed = time.time() - st.st_mtime
        minutes = int(elapsed / 60)
        if minutes < 60:
            return N_('%d minutes ago') % minutes
        hours = int(elapsed / 60 / 60)
        if hours < 24:
            return N_('%d hours ago') % hours
        return N_('%d days ago') % int(elapsed / 60 / 60 / 24)

    def status(self):
        """Return the status for the entry's path."""

        model = main.model()
        unmerged = utils.add_parents(set(model.unmerged))
        modified = utils.add_parents(set(model.modified))
        staged = utils.add_parents(set(model.staged))
        untracked = utils.add_parents(set(model.untracked))
        upstream_changed = utils.add_parents(set(model.upstream_changed))

        if self.path in unmerged:
            return (resources.icon('modified.png'), N_('Unmerged'))
        if self.path in modified and self.path in staged:
            return (resources.icon('partial.png'), N_('Partially Staged'))
        if self.path in modified:
            return (resources.icon('modified.png'), N_('Modified'))
        if self.path in staged:
            return (resources.icon('staged.png'), N_('Staged'))
        if self.path in upstream_changed:
            return (resources.icon('upstream.png'), N_('Changed Upstream'))
        if self.path in untracked:
            return (None, '?')
        return (None, '')

    def run(self):
        """Perform expensive lookups and post corresponding events."""
        app = QtGui.QApplication.instance()
        entry = GitRepoEntryManager.entry(self.path)
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.MESSAGE, self.data('message')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.AGE, self.data('date')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.AUTHOR, self.data('author')))
        app.postEvent(entry,
                GitRepoInfoEvent(Columns.STATUS, self.status()))

        TaskRunner.instance().cleanup_task(self)


class GitRepoInfoEvent(QtCore.QEvent):
    """Transport mechanism for communicating from a GitRepoInfoTask."""
    def __init__(self, signal, *data):
        QtCore.QEvent.__init__(self, QtCore.QEvent.User + 1)
        self.signal = signal
        self.data = data

    def type(self):
        return INFO_EVENT_TYPE


class GitRepoItem(QtGui.QStandardItem):
    """
    Represents a cell in a treeview.

    Many GitRepoItems map to a single repository path.
    Each GitRepoItem manages a different cell in the tree view.
    One is created for each column -- Name, Status, Age, etc.

    """
    def __init__(self, column, path):
        QtGui.QStandardItem.__init__(self)
        self.setEditable(False)
        self.setDragEnabled(False)
        entry = GitRepoEntryManager.entry(path)
        if column == Columns.STATUS:
            QtCore.QObject.connect(entry, SIGNAL(column), self.set_status)
        else:
            QtCore.QObject.connect(entry, SIGNAL(column), self.setText)

    def set_status(self, data):
        icon, txt = data
        if icon:
            self.setIcon(QtGui.QIcon(icon))
        else:
            self.setIcon(QtGui.QIcon())
        self.setText(txt)


class GitRepoNameItem(GitRepoItem):
    """Subclass GitRepoItem to provide a custom type()."""
    TYPE = QtGui.QStandardItem.UserType + 1

    def __init__(self, path):
        GitRepoItem.__init__(self, Columns.NAME, path)
        self.path = path

    def type(self):
        """
        Indicate that this item is of a special user-defined type.

        'name' is the only column that registers a user-defined type.
        This is done to allow filtering out other columns when determining
        which paths are selected.

        """
        return GitRepoNameItem.TYPE

########NEW FILE########
__FILENAME__ = dag
from __future__ import division, absolute_import, unicode_literals

import subprocess

from cola import core
from cola import utils
from cola.git import git
from cola.observable import Observable

# put summary at the end b/c it can contain
# any number of funky characters, including the separator
logfmt = 'format:%H%x01%P%x01%d%x01%an%x01%ad%x01%ae%x01%s'
logsep = chr(0x01)


class CommitFactory(object):
    root_generation = 0
    commits = {}

    @classmethod
    def reset(cls):
        cls.commits.clear()
        cls.root_generation = 0

    @classmethod
    def new(cls, sha1=None, log_entry=None):
        if not sha1 and log_entry:
            sha1 = log_entry[:40]
        try:
            commit = cls.commits[sha1]
            if log_entry and not commit.parsed:
                commit.parse(log_entry)
            cls.root_generation = max(commit.generation,
                                      cls.root_generation)
        except KeyError:
            commit = Commit(sha1=sha1,
                            log_entry=log_entry)
            if not log_entry:
                cls.root_generation += 1
                commit.generation = max(commit.generation,
                                        cls.root_generation)
            cls.commits[sha1] = commit
        return commit


class DAG(Observable):
    ref_updated = 'ref_updated'
    count_updated = 'count_updated'

    def __init__(self, ref, count):
        Observable.__init__(self)
        self.ref = ref
        self.count = count
        self.overrides = {}

    def set_ref(self, ref):
        changed = ref != self.ref
        if changed:
            self.ref = ref
            self.notify_observers(self.ref_updated)
        return changed

    def set_count(self, count):
        changed = count != self.count
        if changed:
            self.count = count
            self.notify_observers(self.count_updated)
        return changed

    def set_arguments(self, args):
        if args is None:
            return
        if self.set_count(args.count):
            self.overrides['count'] = args.count

        if hasattr(args, 'args') and args.args:
            ref = subprocess.list2cmdline(map(core.decode, args.args))
            if self.set_ref(ref):
                self.overrides['ref'] = ref

    def overridden(self, opt):
        return opt in self.overrides

    def paths(self):
        all_refs = utils.shell_split(self.ref)
        if '--' in all_refs:
            all_refs = all_refs[all_refs.index('--'):]

        return [p for p in all_refs if p and core.exists(p)]


class Commit(object):
    root_generation = 0

    __slots__ = ('sha1',
                 'summary',
                 'parents',
                 'children',
                 'tags',
                 'author',
                 'authdate',
                 'email',
                 'generation',
                 'parsed')
    def __init__(self, sha1=None, log_entry=None):
        self.sha1 = sha1
        self.summary = None
        self.parents = []
        self.children = []
        self.tags = set()
        self.email = None
        self.author = None
        self.authdate = None
        self.parsed = False
        self.generation = CommitFactory.root_generation
        if log_entry:
            self.parse(log_entry)

    def parse(self, log_entry, sep=logsep):
        self.sha1 = log_entry[:40]
        (parents, tags, author, authdate, email, summary) = \
                log_entry[41:].split(sep, 6)

        self.summary = summary and summary or ''
        self.author = author and author or ''
        self.authdate = authdate or ''
        self.email = email and email or ''

        if parents:
            generation = None
            for parent_sha1 in parents.split(' '):
                parent = CommitFactory.new(sha1=parent_sha1)
                parent.children.append(self)
                if generation is None:
                    generation = parent.generation+1
                self.parents.append(parent)
                generation = max(parent.generation+1, generation)
            self.generation = generation

        if tags:
            for tag in tags[2:-1].split(', '):
                if tag.startswith('tag: '):
                    tag = tag[5:] # tag: refs/
                elif tag.startswith('refs/remotes/'):
                    tag = tag[13:] # refs/remotes/
                elif tag.startswith('refs/heads/'):
                    tag = tag[11:] # refs/heads/
                if tag.endswith('/HEAD'):
                    continue
                self.tags.add(tag)

        self.parsed = True
        return self

    def __str__(self):
        return self.sha1

    def __repr__(self):
        return ("{\n"
                "  sha1: " + self.sha1 + "\n"
                "  summary: " + self.summary + "\n"
                "  author: " + self.author + "\n"
                "  authdate: " + self.authdate + "\n"
                "  parents: [" + ', '.join([p.sha1 for p in self.parents]) + "]\n"
                "  tags: [" + ', '.join(self.tags) + "]\n"
                "}")

    def is_fork(self):
        ''' Returns True if the node is a fork'''
        return len(self.children) > 1

    def is_merge(self):
        ''' Returns True if the node is a fork'''
        return len(self.parents) > 1


class RepoReader(object):

    def __init__(self, dag, git=git):
        self.dag = dag
        self.git = git
        self._proc = None
        self._objects = {}
        self._cmd = ['git', 'log',
                     '--topo-order',
                     '--reverse',
                     '--pretty='+logfmt]
        self._cached = False
        """Indicates that all data has been read"""
        self._idx = -1
        """Index into the cached commits"""
        self._topo_list = []
        """List of commits objects in topological order"""

    cached = property(lambda self: self._cached)
    """Return True when no commits remain to be read"""


    def __len__(self):
        return len(self._topo_list)

    def reset(self):
        CommitFactory.reset()
        if self._proc:
            self._topo_list = []
            self._proc.kill()
        self._proc = None
        self._cached = False

    def __iter__(self):
        if self._cached:
            return self
        self.reset()
        return self

    def next(self):
        if self._cached:
            try:
                self._idx += 1
                return self._topo_list[self._idx]
            except IndexError:
                self._idx = -1
                raise StopIteration

        if self._proc is None:
            ref_args = utils.shell_split(self.dag.ref)
            cmd = self._cmd + ['-%d' % self.dag.count] + ref_args
            self._proc = core.start_command(cmd)
            self._topo_list = []

        log_entry = core.readline(self._proc.stdout).rstrip()
        if not log_entry:
            self._cached = True
            self._proc.wait()
            self._proc = None
            raise StopIteration

        sha1 = log_entry[:40]
        try:
            return self._objects[sha1]
        except KeyError:
            c = CommitFactory.new(log_entry=log_entry)
            self._objects[c.sha1] = c
            self._topo_list.append(c)
            return c

    __next__ = next # for Python 3

    def __getitem__(self, sha1):
        return self._objects[sha1]

    def items(self):
        return self._objects.items()

########NEW FILE########
__FILENAME__ = main
# Copyright (c) 2008 David Aguilar
"""This module provides the central cola model.
"""
from __future__ import division, absolute_import, unicode_literals

import os
import copy

from cola import core
from cola import git
from cola import gitcfg
from cola import gitcmds
from cola.git import STDOUT
from cola.observable import Observable
from cola.decorators import memoize
from cola.models.selection import selection_model
from cola.models import prefs
from cola.compat import ustr


# Static GitConfig instance
_config = gitcfg.instance()


@memoize
def model():
    """Returns the main model singleton"""
    return MainModel()


class MainModel(Observable):
    """Provides a friendly wrapper for doing common git operations."""

    # Observable messages
    message_about_to_update = 'about_to_update'
    message_commit_message_changed = 'commit_message_changed'
    message_diff_text_changed = 'diff_text_changed'
    message_directory_changed = 'directory_changed'
    message_filename_changed = 'filename_changed'
    message_mode_about_to_change = 'mode_about_to_change'
    message_mode_changed = 'mode_changed'
    message_updated = 'updated'

    # States
    mode_none = 'none' # Default: nothing's happened, do nothing
    mode_worktree = 'worktree' # Comparing index to worktree
    mode_untracked = 'untracked' # Dealing with an untracked file
    mode_index = 'index' # Comparing index to last commit
    mode_amend = 'amend' # Amending a commit

    # Modes where we can checkout files from the $head
    modes_undoable = set((mode_amend, mode_index, mode_worktree))

    # Modes where we can partially stage files
    modes_stageable = set((mode_amend, mode_worktree, mode_untracked))

    # Modes where we can partially unstage files
    modes_unstageable = set((mode_amend, mode_index))

    unstaged = property(lambda self: self.modified + self.unmerged + self.untracked)
    """An aggregate of the modified, unmerged, and untracked file lists."""

    def __init__(self, cwd=None):
        """Reads git repository settings and sets several methods
        so that they refer to the git module.  This object
        encapsulates cola's interaction with git."""
        Observable.__init__(self)

        # Initialize the git command object
        self.git = git.instance()

        self.head = 'HEAD'
        self.diff_text = ''
        self.mode = self.mode_none
        self.filename = None
        self.is_merging = False
        self.is_rebasing = False
        self.currentbranch = ''
        self.directory = ''
        self.project = ''
        self.remotes = []

        self.commitmsg = ''
        self.modified = []
        self.staged = []
        self.untracked = []
        self.unmerged = []
        self.upstream_changed = []
        self.submodules = set()

        self.local_branches = []
        self.remote_branches = []
        self.tags = []
        if cwd:
            self.set_worktree(cwd)

    def unstageable(self):
        return self.mode in self.modes_unstageable

    def amending(self):
        return self.mode == self.mode_amend

    def undoable(self):
        """Whether we can checkout files from the $head."""
        return self.mode in self.modes_undoable

    def stageable(self):
        """Whether staging should be allowed."""
        return self.mode in self.modes_stageable

    def all_branches(self):
        return (self.local_branches + self.remote_branches)

    def set_worktree(self, worktree):
        self.git.set_worktree(worktree)
        is_valid = self.git.is_valid()
        if is_valid:
            self.project = os.path.basename(self.git.worktree())
        return is_valid

    def set_commitmsg(self, msg):
        self.commitmsg = msg
        self.notify_observers(self.message_commit_message_changed, msg)

    def save_commitmsg(self, msg):
        path = self.git.git_path('GIT_COLA_MSG')
        try:
            core.write(path, msg)
        except:
            pass

    def set_diff_text(self, txt):
        self.diff_text = txt
        self.notify_observers(self.message_diff_text_changed, txt)

    def set_directory(self, path):
        self.directory = path
        self.notify_observers(self.message_directory_changed, path)

    def set_filename(self, filename):
        self.filename = filename
        self.notify_observers(self.message_filename_changed, filename)

    def set_mode(self, mode):
        if self.amending():
            if mode != self.mode_none:
                return
        if self.is_merging and mode == self.mode_amend:
            mode = self.mode
        if mode == self.mode_amend:
            head = 'HEAD^'
        else:
            head = 'HEAD'
        self.notify_observers(self.message_mode_about_to_change, mode)
        self.head = head
        self.mode = mode
        self.notify_observers(self.message_mode_changed, mode)

    def apply_diff(self, filename):
        return self.git.apply(filename, index=True, cached=True)

    def apply_diff_to_worktree(self, filename):
        return self.git.apply(filename)

    def prev_commitmsg(self, *args):
        """Queries git for the latest commit message."""
        return self.git.log('-1', no_color=True, pretty='format:%s%n%n%b',
                            *args)[STDOUT]

    def update_file_status(self, update_index=False):
        self.notify_observers(self.message_about_to_update)
        self._update_files(update_index=update_index)
        self.notify_observers(self.message_updated)

    def update_status(self, update_index=False):
        # Give observers a chance to respond
        self.notify_observers(self.message_about_to_update)
        self._update_merge_rebase_status()
        self._update_files(update_index=update_index)
        self._update_refs()
        self._update_branches_and_tags()
        self._update_branch_heads()
        self.notify_observers(self.message_updated)

    def _update_files(self, update_index=False):
        display_untracked = prefs.display_untracked()
        state = gitcmds.worktree_state_dict(head=self.head,
                                            update_index=update_index,
                                            display_untracked=display_untracked)
        self.staged = state.get('staged', [])
        self.modified = state.get('modified', [])
        self.unmerged = state.get('unmerged', [])
        self.untracked = state.get('untracked', [])
        self.submodules = state.get('submodules', set())
        self.upstream_changed = state.get('upstream_changed', [])

        sel = selection_model()
        if self.is_empty():
            sel.reset()
        else:
            sel.update(self)
        if selection_model().is_empty():
            self.set_diff_text('')

    def is_empty(self):
        return not(bool(self.staged or self.modified or
                        self.unmerged or self.untracked))

    def _update_refs(self):
        self.remotes = self.git.remote()[STDOUT].splitlines()

    def _update_branch_heads(self):
        # Set these early since they are used to calculate 'upstream_changed'.
        self.currentbranch = gitcmds.current_branch()

    def _update_branches_and_tags(self):
        local_branches, remote_branches, tags = gitcmds.all_refs(split=True)
        self.local_branches = local_branches
        self.remote_branches = remote_branches
        self.tags = tags

    def _update_merge_rebase_status(self):
        self.is_merging = core.exists(self.git.git_path('MERGE_HEAD'))
        self.is_rebasing = core.exists(self.git.git_path('rebase-merge'))
        if self.is_merging and self.mode == self.mode_amend:
            self.set_mode(self.mode_none)

    def delete_branch(self, branch):
        return self.git.branch(branch, D=True)

    def _sliced_op(self, input_items, map_fn):
        """Slice input_items and call map_fn over every slice

        This exists because of "errno: Argument list too long"

        """
        # This comment appeared near the top of include/linux/binfmts.h
        # in the Linux source tree:
        #
        # /*
        #  * MAX_ARG_PAGES defines the number of pages allocated for arguments
        #  * and envelope for the new program. 32 should suffice, this gives
        #  * a maximum env+arg of 128kB w/4KB pages!
        #  */
        # #define MAX_ARG_PAGES 32
        #
        # 'size' is a heuristic to keep things highly performant by minimizing
        # the number of slices.  If we wanted it to run as few commands as
        # possible we could call "getconf ARG_MAX" and make a better guess,
        # but it's probably not worth the complexity (and the extra call to
        # getconf that we can't do on Windows anyways).
        #
        # In my testing, getconf ARG_MAX on Mac OS X Mountain Lion reported
        # 262144 and Debian/Linux-x86_64 reported 2097152.
        #
        # The hard-coded max_arg_len value is safely below both of these
        # real-world values.

        max_arg_len = 32 * 4 * 1024
        avg_filename_len = 300
        size = max_arg_len // avg_filename_len

        status = 0
        outs = []
        errs = []

        items = copy.copy(input_items)
        while items:
            stat, out, err = map_fn(items[:size])
            status = max(stat, status)
            outs.append(out)
            errs.append(err)
            items = items[size:]

        return (status, '\n'.join(outs), '\n'.join(errs))

    def _sliced_add(self, input_items):
        lambda_fn = lambda x: self.git.add('--', force=True, verbose=True, *x)
        return self._sliced_op(input_items, lambda_fn)

    def stage_modified(self):
        status, out, err = self._sliced_add(self.modified)
        self.update_file_status()
        return (status, out, err)

    def stage_untracked(self):
        status, out, err = self._sliced_add(self.untracked)
        self.update_file_status()
        return (status, out, err)

    def reset(self, *items):
        lambda_fn = lambda x: self.git.reset('--', *x)
        status, out, err = self._sliced_op(items, lambda_fn)
        self.update_file_status()
        return (status, out, err)

    def unstage_all(self):
        """Unstage all files, even while amending"""
        status, out, err = self.git.reset(self.head, '--', '.')
        self.update_file_status()
        return (status, out, err)

    def stage_all(self):
        status, out, err = self.git.add(v=True, u=True)
        self.update_file_status()
        return (status, out, err)

    def config_set(self, key, value, local=True):
        # git config category.key value
        strval = ustr(value)
        if type(value) is bool:
            # git uses "true" and "false"
            strval = strval.lower()
        if local:
            argv = [key, strval]
        else:
            argv = ['--global', key, strval]
        return self.git.config(*argv)

    def config_dict(self, local=True):
        """parses the lines from git config --list into a dictionary"""

        kwargs = {
            'list': True,
            'global': not local, # global is a python keyword
        }
        config_lines = self.git.config(**kwargs)[STDOUT].splitlines()
        newdict = {}
        for line in config_lines:
            try:
                k, v = line.split('=', 1)
            except:
                # value-less entry in .gitconfig
                continue
            k = k.replace('.','_') # git -> model
            if v == 'true' or v == 'false':
                v = bool(eval(v.title()))
            try:
                v = int(eval(v))
            except:
                pass
            newdict[k]=v
        return newdict

    def commit_with_msg(self, msg, tmpfile, amend=False):
        """Creates a git commit."""

        if not msg.endswith('\n'):
            msg += '\n'

        # Create the commit message file
        core.write(tmpfile, msg)

        # Run 'git commit'
        status, out, err = self.git.commit(F=tmpfile, v=True, amend=amend)
        core.unlink(tmpfile)
        return (status, out, err)

    def remote_url(self, name, action):
        if action == 'push':
            url = self.git.config('remote.%s.pushurl' % name,
                                  get=True)[STDOUT]
            if url:
                return url
        return self.git.config('remote.%s.url' % name, get=True)[STDOUT]

    def remote_args(self, remote,
                    local_branch='',
                    remote_branch='',
                    ffwd=True,
                    tags=False,
                    rebase=False,
                    push=False):
        # Swap the branches in push mode (reverse of fetch)
        if push:
            tmp = local_branch
            local_branch = remote_branch
            remote_branch = tmp
        if ffwd:
            branch_arg = '%s:%s' % (remote_branch, local_branch)
        else:
            branch_arg = '+%s:%s' % (remote_branch, local_branch)
        args = [remote]
        if local_branch and remote_branch:
            args.append(branch_arg)
        elif local_branch:
            args.append(local_branch)
        elif remote_branch:
            args.append(remote_branch)
        kwargs = {
            'verbose': True,
            'tags': tags,
            'rebase': rebase,
        }
        return (args, kwargs)

    def run_remote_action(self, action, remote, push=False, **kwargs):
        args, kwargs = self.remote_args(remote, push=push, **kwargs)
        return action(*args, **kwargs)

    def fetch(self, remote, **opts):
        return self.run_remote_action(self.git.fetch, remote, **opts)

    def push(self, remote, **opts):
        return self.run_remote_action(self.git.push, remote, push=True, **opts)

    def pull(self, remote, **opts):
        return self.run_remote_action(self.git.pull, remote, push=True, **opts)

    def create_branch(self, name, base, track=False, force=False):
        """Create a branch named 'name' from revision 'base'

        Pass track=True to create a local tracking branch.
        """
        return self.git.branch(name, base, track=track, force=force)

    def cherry_pick_list(self, revs, **kwargs):
        """Cherry-picks each revision into the current branch.
        Returns a list of command output strings (1 per cherry pick)"""
        if not revs:
            return []
        outs = []
        errs = []
        status = 0
        for rev in revs:
            stat, out, err = self.git.cherry_pick(rev)
            status = max(stat, status)
            outs.append(out)
            errs.append(err)
        return (status, '\n'.join(outs), '\n'.join(errs))

    def pad(self, pstr, num=22):
        topad = num-len(pstr)
        if topad > 0:
            return pstr + ' '*topad
        else:
            return pstr

    def is_commit_published(self):
        head = self.git.rev_parse('HEAD')[STDOUT]
        return bool(self.git.branch(r=True, contains=head)[STDOUT])

    def everything(self):
        """Returns a sorted list of all files, including untracked files."""
        ls_files = self.git.ls_files(z=True,
                                     cached=True,
                                     others=True,
                                     exclude_standard=True)[STDOUT]
        return sorted([f for f in ls_files.split('\0') if f])

    def stage_paths(self, paths):
        """Stages add/removals to git."""
        if not paths:
            self.stage_all()
            return

        add = []
        remove = []

        for path in set(paths):
            if core.exists(path):
                add.append(path)
            else:
                remove.append(path)

        self.notify_observers(self.message_about_to_update)

        # `git add -u` doesn't work on untracked files
        if add:
            self._sliced_add(add)

        # If a path doesn't exist then that means it should be removed
        # from the index.   We use `git add -u` for that.
        if remove:
            while remove:
                self.git.add('--', u=True, *remove[:42])
                remove = remove[42:]

        self._update_files()
        self.notify_observers(self.message_updated)

    def unstage_paths(self, paths):
        if not paths:
            self.unstage_all()
            return
        gitcmds.unstage_paths(paths, head=self.head)
        self.update_file_status()

    def untrack_paths(self, paths):
        status, out, err = gitcmds.untrack_paths(paths, head=self.head)
        self.update_file_status()
        return status, out, err

    def getcwd(self):
        """If we've chosen a directory then use it, otherwise os.getcwd()."""
        if self.directory:
            return self.directory
        return core.getcwd()

########NEW FILE########
__FILENAME__ = prefs
from __future__ import division, absolute_import, unicode_literals

from cola import gitcfg
from cola import observable


FONTDIFF = 'cola.fontdiff'
DIFFCONTEXT = 'gui.diffcontext'
DIFFTOOL = 'diff.tool'
DISPLAY_UNTRACKED = 'gui.displayuntracked'
EDITOR = 'gui.editor'
LINEBREAK = 'cola.linebreak'
TABWIDTH = 'cola.tabwidth'
TEXTWIDTH = 'cola.textwidth'
HISTORY_BROWSER = 'gui.historybrowser'
MERGE_SUMMARY = 'merge.summary'
MERGE_DIFFSTAT = 'merge.diffstat'
MERGE_KEEPBACKUP = 'merge.keepbackup'
MERGE_VERBOSITY = 'merge.verbosity'
MERGETOOL = 'merge.tool'
SAVEWINDOWSETTINGS = 'cola.savewindowsettings'
USER_EMAIL = 'user.email'
USER_NAME = 'user.name'



def config():
    return gitcfg.instance()


def display_untracked():
    return config().get(DISPLAY_UNTRACKED, True)


def editor():
    app = config().get(EDITOR, 'gvim')
    return {'vim': 'gvim -f'}.get(app, app)


def history_browser():
    return config().get(HISTORY_BROWSER, 'gitk')


def linebreak():
    return config().get(LINEBREAK, True)


def tabwidth():
    return config().get(TABWIDTH, 8)


def textwidth():
    return config().get(TEXTWIDTH, 72)



class PreferencesModel(observable.Observable):
    message_config_updated = 'config_updated'

    def __init__(self):
        observable.Observable.__init__(self)
        self.config = gitcfg.instance()

    def set_config(self, source, config, value):
        if source == 'repo':
            self.config.set_repo(config, value)
        else:
            self.config.set_user(config, value)
        message = self.message_config_updated
        self.notify_observers(message, source, config, value)

    def get_config(self, source, config):
        if source == 'repo':
            return self.config.get_repo(config)
        else:
            return self.config.get(config)


class SetConfig(object):

    def __init__(self, model, source, config, value):
        self.source = source
        self.config = config
        self.value = value
        self.old_value = None
        self.model = model

    def is_undoable(self):
        return True

    def do(self):
        self.old_value = self.model.get_config(self.source, self.config)
        self.model.set_config(self.source, self.config, self.value)

    def undo(self):
        if self.old_value is None:
            return
        self.model.set_config(self.source, self.config, self.old_value)

########NEW FILE########
__FILENAME__ = selection
"""Provides a selection model to handle selection."""
from __future__ import division, absolute_import, unicode_literals

import collections

from cola.observable import Observable
from cola.decorators import memoize

State = collections.namedtuple('State', 'staged unmerged modified untracked')


@memoize
def selection_model():
    """Provides access to a static SelectionModel instance."""
    return SelectionModel()


def selection():
    """Return the current selection."""
    return selection_model().selection()


def single_selection():
    """Scan across staged, modified, etc. and return a single item."""
    return selection_model().single_selection()


def selected_group():
    return selection_model().group()


def filename():
    return selection_model().filename()


def pick(s):
    if s.staged:
        files = s.staged
    elif s.unmerged:
        files = s.unmerged
    elif s.modified:
        files = s.modified
    elif s.untracked:
        files = s.untracked
    else:
        files = []
    return files


def _filter(a, b):
    b_set = set(b)
    a_copy = list(a)
    last = len(a_copy) - 1
    for idx, i in enumerate(reversed(a)):
        if i not in b_set:
            a.pop(last - idx)


class SelectionModel(Observable):
    """Provides information about selected file paths."""
    # Notification message sent out when selection changes
    message_selection_changed = 'selection_changed'

    # These properties wrap the individual selection items
    # to provide higher-level pseudo-selections.
    unstaged = property(lambda self: self.unmerged +
                                     self.modified +
                                     self.untracked)

    def __init__(self):
        Observable.__init__(self)
        self.staged = []
        self.unmerged = []
        self.modified = []
        self.untracked = []

    def reset(self):
        self.staged = []
        self.unmerged = []
        self.modified = []
        self.untracked = []

    def is_empty(self):
        return not(bool(self.staged or self.unmerged or
                        self.modified or self.untracked))

    def set_selection(self, s):
        """Set the new selection."""
        self.staged = s.staged
        self.unmerged = s.unmerged
        self.modified = s.modified
        self.untracked = s.untracked
        self.notify_observers(self.message_selection_changed)

    def update(self, other):
        _filter(self.staged, other.staged)
        _filter(self.unmerged, other.unmerged)
        _filter(self.modified, other.modified)
        _filter(self.untracked, other.untracked)
        self.notify_observers(self.message_selection_changed)

    def selection(self):
        return State(self.staged, self.unmerged,
                     self.modified, self.untracked)

    def single_selection(self):
        st = None
        m = None
        um = None
        ut = None
        if self.staged:
            st = self.staged[0]
        elif self.modified:
            m = self.modified[0]
        elif self.unmerged:
            um = self.unmerged[0]
        elif self.untracked:
            ut = self.untracked[0]
        return State(st, um, m, ut)

    def filename(self):
        paths = [p for p in self.single_selection() if p is not None]
        if paths:
            return paths[0]
        else:
            return None

    def group(self):
        """A list of selected files in various states of being"""
        return pick(self.selection())

########NEW FILE########
__FILENAME__ = stash
from __future__ import division, absolute_import, unicode_literals

from cola import observable
from cola.git import git
from cola.git import STDOUT
from cola.interaction import Interaction
from cola.models import main


class StashModel(observable.Observable):
    def __init__(self):
        observable.Observable.__init__(self)

    def stash_list(self):
        return git.stash('list')[STDOUT].splitlines()

    def has_stashable_changes(self):
        model = main.model()
        return bool(model.modified + model.staged)

    def stash_info(self, revids=False, names=False):
        """Parses "git stash list" and returns a list of stashes."""
        stashes = self.stash_list()
        revids = [s[:s.index(':')] for s in stashes]
        names = [s.split(': ', 2)[-1] for s in stashes]

        return stashes, revids, names

    def stash_diff(self, rev):
        diffstat = git.stash('show', rev)[STDOUT]
        diff = git.stash('show', '-p', rev)[STDOUT]
        return diffstat + '\n\n' + diff


class ApplyStash(object):
    def __init__(self, selection, index):
        self.selection = selection
        self.index = index

    def is_undoable(self):
        return False

    def do(self):
        if self.index:
            args = ['apply', '--index', self.selection]
        else:
            args = ['apply', self.selection]
        status, out, err = git.stash(*args)
        Interaction.log_status(status, out, err)


class DropStash(object):
    def __init__(self, stash_sha1):
        self.stash_sha1 = stash_sha1

    def is_undoable(self):
        return False

    def do(self):
        status, out, err = git.stash('drop', self.stash_sha1)
        Interaction.log_status(status, out, err)


class SaveStash(object):

    def __init__(self, stash_name, keep_index):
        self.stash_name = stash_name
        self.keep_index = keep_index

    def is_undoable(self):
        return False

    def do(self):
        if self.keep_index:
            args = ['save', '--keep-index', self.stash_name]
        else:
            args = ['save', self.stash_name]
        status, out, err = git.stash(*args)
        Interaction.log_status(status, out, err)

########NEW FILE########
__FILENAME__ = observable
# Copyright (c) 2008 David Aguilar
"""This module provides the Observable class"""
from __future__ import division, absolute_import, unicode_literals

class Observable(object):
    """Handles subject/observer notifications."""
    def __init__(self):
        self.notification_enabled = True
        self.observers = {}

    def add_observer(self, message, observer):
        """Add an observer for a specific message."""
        observers = self.observers.setdefault(message, set())
        observers.add(observer)

    def remove_observer(self, observer):
        """Remove an observer."""
        for message, observers in self.observers.items():
            if observer in observers:
                observers.remove(observer)

    def notify_observers(self, message, *args, **opts):
        """Pythonic signals and slots."""
        if not self.notification_enabled:
            return
        observers = self.observers.get(message, ())
        for method in observers:
            method(*args, **opts)

########NEW FILE########
__FILENAME__ = qtcompat
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore

def install():
    if not hasattr(QtGui.QHBoxLayout, 'setContentsMargins'):
        QtGui.QHBoxLayout.setContentsMargins = lambda *args: True

    if not hasattr(QtGui.QVBoxLayout, 'setContentsMargins'):
        QtGui.QVBoxLayout.setContentsMargins = lambda *args: True

    if not hasattr(QtGui.QKeySequence, 'Preferences'):
        QtGui.QKeySequence.Preferences = 'Ctrl+O'

    if not hasattr(QtGui.QGraphicsItem, 'mapRectToScene'):
        QtGui.QGraphicsItem.mapRectToScene = _map_rect_to_scene

    if not hasattr(QtCore.QCoreApplication, 'setStyleSheet'):
        QtCore.QCoreApplication.setStyleSheet = lambda *args: None


def add_search_path(prefix, path):
    if hasattr(QtCore.QDir, 'addSearchPath'):
        QtCore.QDir.addSearchPath(prefix, path)

def set_common_dock_options(window):
    if not hasattr(window, 'setDockOptions'):
        return
    nested = QtGui.QMainWindow.AllowNestedDocks
    tabbed = QtGui.QMainWindow.AllowTabbedDocks
    animated = QtGui.QMainWindow.AnimatedDocks
    window.setDockOptions(nested | tabbed | animated)


def _map_rect_to_scene(self, rect):
    """Only available in newer PyQt4 versions"""
    return self.sceneTransform().mapRect(rect)

########NEW FILE########
__FILENAME__ = qtutils
# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous Qt utility functions.
"""
from __future__ import division, absolute_import, unicode_literals

import os
import re

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import gitcfg
from cola import utils
from cola import resources
from cola.decorators import memoize
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models.prefs import FONTDIFF
from cola.widgets import defs
from cola.compat import ustr


def connect_action(action, fn):
    action.connect(action, SIGNAL('triggered()'), fn)


def connect_action_bool(action, fn):
    action.connect(action, SIGNAL('triggered(bool)'), fn)


def connect_button(button, fn):
    button.connect(button, SIGNAL('clicked()'), fn)


def connect_toggle(toggle, fn):
    toggle.connect(toggle, SIGNAL('toggled(bool)'), fn)


def active_window():
    return QtGui.QApplication.activeWindow()


def prompt(msg, title=None, text=''):
    """Presents the user with an input widget and returns the input."""
    if title is None:
        title = msg
    result = QtGui.QInputDialog.getText(active_window(), msg, title,
                                        QtGui.QLineEdit.Normal, text)
    return (ustr(result[0]), result[1])


def create_listwidget_item(text, filename):
    """Creates a QListWidgetItem with text and the icon at filename."""
    item = QtGui.QListWidgetItem()
    item.setIcon(QtGui.QIcon(filename))
    item.setText(text)
    return item


class TreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, text, filename, exists):
        QtGui.QTreeWidgetItem.__init__(self)
        self.exists = exists
        self.setIcon(0, cached_icon_from_path(filename))
        self.setText(0, text)


def create_treewidget_item(text, filename, exists=True):
    """Creates a QTreeWidgetItem with text and the icon at filename."""
    return TreeWidgetItem(text, filename, exists)


@memoize
def cached_icon_from_path(filename):
    return QtGui.QIcon(filename)


def confirm(title, text, informative_text, ok_text,
            icon=None, default=True):
    """Confirm that an action should take place"""
    if icon is None:
        icon = ok_icon()
    elif icon and isinstance(icon, ustr):
        icon = QtGui.QIcon(icon)
    msgbox = QtGui.QMessageBox(active_window())
    msgbox.setWindowModality(Qt.WindowModal)
    msgbox.setWindowTitle(title)
    msgbox.setText(text)
    msgbox.setInformativeText(informative_text)
    ok = msgbox.addButton(ok_text, QtGui.QMessageBox.ActionRole)
    ok.setIcon(icon)
    cancel = msgbox.addButton(QtGui.QMessageBox.Cancel)
    if default:
        msgbox.setDefaultButton(ok)
    else:
        msgbox.setDefaultButton(cancel)
    msgbox.exec_()
    return msgbox.clickedButton() == ok


class ResizeableMessageBox(QtGui.QMessageBox):

    def __init__(self, parent):
        QtGui.QMessageBox.__init__(self, parent)
        self.setMouseTracking(True)
        self.setSizeGripEnabled(True)

    def event(self, event):
        res = QtGui.QMessageBox.event(self, event)
        event_type = event.type()
        if (event_type == QtCore.QEvent.MouseMove or
                event_type == QtCore.QEvent.MouseButtonPress):
            maxi = QtCore.QSize(1024*4, 1024*4)
            self.setMaximumSize(maxi)
            text = self.findChild(QtGui.QTextEdit)
            if text is not None:
                expand = QtGui.QSizePolicy.Expanding
                text.setSizePolicy(QtGui.QSizePolicy(expand, expand))
                text.setMaximumSize(maxi)
        return res


def critical(title, message=None, details=None):
    """Show a warning with the provided title and message."""
    if message is None:
        message = title
    mbox = ResizeableMessageBox(active_window())
    mbox.setWindowTitle(title)
    mbox.setTextFormat(Qt.PlainText)
    mbox.setText(message)
    mbox.setIcon(QtGui.QMessageBox.Critical)
    mbox.setStandardButtons(QtGui.QMessageBox.Close)
    mbox.setDefaultButton(QtGui.QMessageBox.Close)
    if details:
        mbox.setDetailedText(details)
    mbox.exec_()


def information(title, message=None, details=None, informative_text=None):
    """Show information with the provided title and message."""
    if message is None:
        message = title
    mbox = QtGui.QMessageBox(active_window())
    mbox.setStandardButtons(QtGui.QMessageBox.Close)
    mbox.setDefaultButton(QtGui.QMessageBox.Close)
    mbox.setWindowTitle(title)
    mbox.setWindowModality(Qt.WindowModal)
    mbox.setTextFormat(Qt.PlainText)
    mbox.setText(message)
    if informative_text:
        mbox.setInformativeText(informative_text)
    if details:
        mbox.setDetailedText(details)
    # Render git.svg into a 1-inch wide pixmap
    pixmap = QtGui.QPixmap(resources.icon('git.svg'))
    xres = pixmap.physicalDpiX()
    pixmap = pixmap.scaledToHeight(xres, Qt.SmoothTransformation)
    mbox.setIconPixmap(pixmap)
    mbox.exec_()


def question(title, msg, default=True):
    """Launches a QMessageBox question with the provided title and message.
    Passing "default=False" will make "No" the default choice."""
    yes = QtGui.QMessageBox.Yes
    no = QtGui.QMessageBox.No
    buttons = yes | no
    if default:
        default = yes
    else:
        default = no
    result = (QtGui.QMessageBox
                   .question(active_window(), title, msg, buttons, default))
    return result == QtGui.QMessageBox.Yes


def selected_treeitem(tree_widget):
    """Returns a(id_number, is_selected) for a QTreeWidget."""
    id_number = None
    selected = False
    item = tree_widget.currentItem()
    if item:
        id_number = item.data(0, Qt.UserRole).toInt()[0]
        selected = True
    return(id_number, selected)


def selected_row(list_widget):
    """Returns a(row_number, is_selected) tuple for a QListWidget."""
    items = list_widget.selectedItems()
    if not items:
        return (-1, False)
    item = items[0]
    return (list_widget.row(item), True)


def selection_list(listwidget, items):
    """Returns an array of model items that correspond to
    the selected QListWidget indices."""
    selected = []
    itemcount = listwidget.count()
    widgetitems = [ listwidget.item(idx) for idx in range(itemcount) ]

    for item, widgetitem in zip(items, widgetitems):
        if widgetitem.isSelected():
            selected.append(item)
    return selected


def tree_selection(treeitem, items):
    """Returns model items that correspond to selected widget indices"""
    itemcount = treeitem.childCount()
    widgetitems = [treeitem.child(idx) for idx in range(itemcount)]
    selected = []
    for item, widgetitem in zip(items[:len(widgetitems)], widgetitems):
        if widgetitem.isSelected():
            selected.append(item)

    return selected


def tree_selection_items(item):
    """Returns selected widget items"""
    count = item.childCount()
    childitems = [item.child(idx) for idx in range(count)]
    selected = []
    for child in childitems:
        if child.isSelected():
            selected.append(child)

    return selected


def selected_item(list_widget, items):
    """Returns the selected item in a QListWidget."""
    widget_items = list_widget.selectedItems()
    if not widget_items:
        return None
    widget_item = widget_items[0]
    row = list_widget.row(widget_item)
    if row < len(items):
        return items[row]
    else:
        return None


def selected_items(list_widget, items):
    """Returns the selected item in a QListWidget."""
    selection = []
    widget_items = list_widget.selectedItems()
    if not widget_items:
        return selection
    for widget_item in widget_items:
        row = list_widget.row(widget_item)
        if row < len(items):
            selection.append(items[row])
    return selection


def open_file(title, directory=None):
    """Creates an Open File dialog and returns a filename."""
    return ustr(QtGui.QFileDialog
                        .getOpenFileName(active_window(), title, directory))


def open_files(title, directory=None, filter=None):
    """Creates an Open File dialog and returns a list of filenames."""
    return (QtGui.QFileDialog
            .getOpenFileNames(active_window(), title, directory, filter))


def opendir_dialog(title, path):
    """Prompts for a directory path"""

    flags = (QtGui.QFileDialog.ShowDirsOnly |
             QtGui.QFileDialog.DontResolveSymlinks)
    return ustr(QtGui.QFileDialog
                        .getExistingDirectory(active_window(),
                                              title, path, flags))


def save_as(filename, title='Save As...'):
    """Creates a Save File dialog and returns a filename."""
    return ustr(QtGui.QFileDialog
                        .getSaveFileName(active_window(), title, filename))


def icon(basename):
    """Given a basename returns a QIcon from the corresponding cola icon."""
    return QtGui.QIcon(resources.icon(basename))


def set_clipboard(text):
    """Sets the copy/paste buffer to text."""
    if not text:
        return
    clipboard = QtGui.QApplication.instance().clipboard()
    clipboard.setText(text, QtGui.QClipboard.Clipboard)
    clipboard.setText(text, QtGui.QClipboard.Selection)


def add_action_bool(widget, text, fn, checked, *shortcuts):
    action = _add_action(widget, text, fn, connect_action_bool, *shortcuts)
    action.setCheckable(True)
    action.setChecked(checked)
    return action


def add_action(widget, text, fn, *shortcuts):
    return _add_action(widget, text, fn, connect_action, *shortcuts)


def _add_action(widget, text, fn, connect, *shortcuts):
    action = QtGui.QAction(text, widget)
    connect(action, fn)
    if shortcuts:
        action.setShortcuts(shortcuts)
        action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        widget.addAction(action)
    return action

def set_selected_item(widget, idx):
    """Sets a the currently selected item to the item at index idx."""
    if type(widget) is QtGui.QTreeWidget:
        item = widget.topLevelItem(idx)
        if item:
            widget.setItemSelected(item, True)
            widget.setCurrentItem(item)


def add_items(widget, items):
    """Adds items to a widget."""
    for item in items:
        widget.addItem(item)


def set_items(widget, items):
    """Clear the existing widget contents and set the new items."""
    widget.clear()
    add_items(widget, items)


def icon_file(filename, staged=False, untracked=False):
    """Returns a file path representing a corresponding file path."""
    exists = True
    if staged:
        exists = core.exists(filename)
        if exists:
            ifile = resources.icon('staged-item.png')
        else:
            ifile = resources.icon('removed.png')
    elif untracked:
        ifile = resources.icon('untracked.png')
    else:
        (ifile, exists) = utils.file_icon(filename)
    return (ifile, exists)


def icon_for_file(filename, staged=False, untracked=False):
    """Returns a QIcon for a particular file path."""
    ifile = icon_file(filename, staged=staged, untracked=untracked)
    return icon(ifile)


def create_treeitem(filename, staged=False, untracked=False, check=True):
    """Given a filename, return a QListWidgetItem suitable
    for adding to a QListWidget.  "staged" and "untracked"
    controls whether to use the appropriate icons."""
    if check:
        (ifile, exists) = icon_file(filename,
                                    staged=staged, untracked=untracked)
    else:
        exists = True
        ifile = resources.icon('staged.png')
    return create_treewidget_item(filename, ifile, exists=exists)


def update_file_icons(widget, items, staged=True,
                      untracked=False, offset=0):
    """Populate a QListWidget with custom icon items."""
    for idx, model_item in enumerate(items):
        item = widget.item(idx+offset)
        if item:
            item.setIcon(icon_for_file(model_item, staged, untracked))

@memoize
def cached_icon(key):
    """Maintain a cache of standard icons and return cache entries."""
    style = QtGui.QApplication.instance().style()
    return style.standardIcon(key)


def dir_icon():
    """Return a standard icon for a directory."""
    return cached_icon(QtGui.QStyle.SP_DirIcon)


def file_icon():
    """Return a standard icon for a file."""
    return cached_icon(QtGui.QStyle.SP_FileIcon)


def apply_icon():
    """Return a standard Apply icon"""
    return cached_icon(QtGui.QStyle.SP_DialogApplyButton)


def new_icon():
    return cached_icon(QtGui.QStyle.SP_FileDialogNewFolder)


def save_icon():
    """Return a standard Save icon"""
    return cached_icon(QtGui.QStyle.SP_DialogSaveButton)


def ok_icon():
    """Return a standard Ok icon"""
    return cached_icon(QtGui.QStyle.SP_DialogOkButton)


def open_icon():
    """Return a standard open directory icon"""
    return cached_icon(QtGui.QStyle.SP_DirOpenIcon)


def help_icon():
    """Return a standard open directory icon"""
    return cached_icon(QtGui.QStyle.SP_DialogHelpButton)


def add_icon():
    return icon('add.svg')


def remove_icon():
    return icon('remove.svg')


def open_file_icon():
    return icon('open.svg')


def options_icon():
    """Return a standard open directory icon"""
    return icon('options.svg')


def dir_close_icon():
    """Return a standard closed directory icon"""
    return cached_icon(QtGui.QStyle.SP_DirClosedIcon)


def titlebar_close_icon():
    """Return a dock widget close icon"""
    return cached_icon(QtGui.QStyle.SP_TitleBarCloseButton)


def titlebar_normal_icon():
    """Return a dock widget close icon"""
    return cached_icon(QtGui.QStyle.SP_TitleBarNormalButton)


def git_icon():
    return icon('git.svg')


def reload_icon():
    """Returna  standard Refresh icon"""
    return cached_icon(QtGui.QStyle.SP_BrowserReload)


def discard_icon():
    """Return a standard Discard icon"""
    return cached_icon(QtGui.QStyle.SP_DialogDiscardButton)


def close_icon():
    """Return a standard Close icon"""
    return cached_icon(QtGui.QStyle.SP_DialogCloseButton)


def add_close_action(widget):
    """Adds close action and shortcuts to a widget."""
    return add_action(widget, N_('Close...'),
                      widget.close, QtGui.QKeySequence.Close, 'Ctrl+Q')


def center_on_screen(widget):
    """Move widget to the center of the default screen"""
    desktop = QtGui.QApplication.instance().desktop()
    rect = desktop.screenGeometry(QtGui.QCursor().pos())
    cy = rect.height()//2
    cx = rect.width()//2
    widget.move(cx - widget.width()//2, cy - widget.height()//2)


@memoize
def theme_icon(name):
    """Grab an icon from the current theme with a fallback

    Support older versions of Qt by catching AttributeError and
    falling back to our default icons.

    """
    try:
        base, ext = os.path.splitext(name)
        qicon = QtGui.QIcon.fromTheme(base)
        if not qicon.isNull():
            return qicon
    except AttributeError:
        pass
    return icon(name)


def default_monospace_font():
    font = QtGui.QFont()
    family = 'Monospace'
    if utils.is_darwin():
        family = 'Monaco'
    font.setFamily(family)
    return font


def diff_font_str():
    font_str = gitcfg.instance().get(FONTDIFF)
    if font_str is None:
        font = default_monospace_font()
        font_str = ustr(font.toString())
    return font_str


def diff_font():
    font_str = diff_font_str()
    font = QtGui.QFont()
    font.fromString(font_str)
    return font


def create_button(text='', layout=None, tooltip=None, icon=None):
    """Create a button, set its title, and add it to the parent."""
    button = QtGui.QPushButton()
    button.setCursor(Qt.PointingHandCursor)
    if text:
        button.setText(text)
    if icon:
        button.setIcon(icon)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if layout is not None:
        layout.addWidget(button)
    return button


def create_action_button(tooltip=None, icon=None):
    button = QtGui.QPushButton()
    button.setFixedSize(QtCore.QSize(16, 16))
    button.setCursor(Qt.PointingHandCursor)
    button.setFlat(True)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if icon is not None:
        pixmap = icon.pixmap(QtCore.QSize(16, 16))
        button.setIcon(QtGui.QIcon(pixmap))
    return button


def hide_button_menu_indicator(button):
    cls = type(button)
    name = cls.__name__
    stylesheet = """
        %(name)s::menu-indicator {
            image: none;
        }
    """
    if name == 'QPushButton':
        stylesheet += """
            %(name)s {
                border-style: none;
            }
        """
    button.setStyleSheet(stylesheet % {'name': name})


class DockTitleBarWidget(QtGui.QWidget):

    def __init__(self, parent, title, stretch=True):
        QtGui.QWidget.__init__(self, parent)
        self.label = label = QtGui.QLabel()
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        label.setText(title)

        self.setCursor(Qt.OpenHandCursor)

        self.close_button = create_action_button(
                tooltip=N_('Close'), icon=titlebar_close_icon())

        self.toggle_button = create_action_button(
                tooltip=N_('Detach'), icon=titlebar_normal_icon())

        self.corner_layout = QtGui.QHBoxLayout()
        self.corner_layout.setMargin(defs.no_margin)
        self.corner_layout.setSpacing(defs.spacing)

        self.main_layout = QtGui.QHBoxLayout()
        self.main_layout.setMargin(defs.small_margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addWidget(label)
        self.main_layout.addSpacing(defs.spacing)
        if stretch:
            self.main_layout.addStretch()
        self.main_layout.addLayout(self.corner_layout)
        self.main_layout.addSpacing(defs.spacing)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.close_button)

        self.setLayout(self.main_layout)

        connect_button(self.toggle_button, self.toggle_floating)
        connect_button(self.close_button, self.toggle_visibility)

    def toggle_floating(self):
        self.parent().setFloating(not self.parent().isFloating())
        self.update_tooltips()

    def toggle_visibility(self):
        self.parent().toggleViewAction().trigger()

    def set_title(self, title):
        self.label.setText(title)

    def add_corner_widget(self, widget):
        self.corner_layout.addWidget(widget)

    def update_tooltips(self):
        if self.parent().isFloating():
            tooltip = N_('Attach')
        else:
            tooltip = N_('Detach')
        self.toggle_button.setToolTip(tooltip)


def create_dock(title, parent, stretch=True):
    """Create a dock widget and set it up accordingly."""
    dock = QtGui.QDockWidget(parent)
    dock.setWindowTitle(title)
    dock.setObjectName(title)
    titlebar = DockTitleBarWidget(dock, title, stretch=stretch)
    dock.setTitleBarWidget(titlebar)
    if hasattr(parent, 'dockwidgets'):
        parent.dockwidgets.append(dock)
    return dock


def create_menu(title, parent):
    """Create a menu and set its title."""
    qmenu = QtGui.QMenu(parent)
    qmenu.setTitle(title)
    return qmenu


def create_toolbutton(text=None, layout=None, tooltip=None, icon=None):
    button = QtGui.QToolButton()
    button.setAutoRaise(True)
    button.setAutoFillBackground(True)
    button.setCursor(Qt.PointingHandCursor)
    if icon is not None:
        button.setIcon(icon)
    if text is not None:
        button.setText(text)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if tooltip is not None:
        button.setToolTip(tooltip)
    if layout is not None:
        layout.addWidget(button)
    return button


# Syntax highlighting

def TERMINAL(pattern):
    """
    Denotes that a pattern is the final pattern that should
    be matched.  If this pattern matches no other formats
    will be applied, even if they would have matched.
    """
    return '__TERMINAL__:%s' % pattern

# Cache the results of re.compile so that we don't keep
# rebuilding the same regexes whenever stylesheets change
_RGX_CACHE = {}

def rgba(r, g, b, a=255):
    c = QtGui.QColor()
    c.setRgb(r, g, b)
    c.setAlpha(a)
    return c

default_colors = {
    'color_text':           rgba(0x00, 0x00, 0x00),
    'color_add':            rgba(0xcd, 0xff, 0xe0),
    'color_remove':         rgba(0xff, 0xd0, 0xd0),
    'color_header':         rgba(0xbb, 0xbb, 0xbb),
}


class GenericSyntaxHighligher(QtGui.QSyntaxHighlighter):
    def __init__(self, doc, *args, **kwargs):
        QtGui.QSyntaxHighlighter.__init__(self, doc)
        for attr, val in default_colors.items():
            setattr(self, attr, val)
        self._rules = []
        self.enabled = True
        self.generate_rules()

    def generate_rules(self):
        pass

    def set_enabled(self, enabled):
        self.enabled = enabled

    def create_rules(self, *rules):
        if len(rules) % 2:
            raise Exception('create_rules requires an even '
                            'number of arguments.')
        for idx, rule in enumerate(rules):
            if idx % 2:
                continue
            formats = rules[idx+1]
            terminal = rule.startswith(TERMINAL(''))
            if terminal:
                rule = rule[len(TERMINAL('')):]
            try:
                regex = _RGX_CACHE[rule]
            except KeyError:
                regex = _RGX_CACHE[rule] = re.compile(rule)
            self._rules.append((regex, formats, terminal,))

    def formats(self, line):
        matched = []
        for regex, fmts, terminal in self._rules:
            match = regex.match(line)
            if not match:
                continue
            matched.append([match, fmts])
            if terminal:
                return matched
        return matched

    def mkformat(self, fg=None, bg=None, bold=False):
        fmt = QtGui.QTextCharFormat()
        if fg:
            fmt.setForeground(fg)
        if bg:
            fmt.setBackground(bg)
        if bold:
            fmt.setFontWeight(QtGui.QFont.Bold)
        return fmt

    def highlightBlock(self, qstr):
        if not self.enabled:
            return
        ascii = ustr(qstr)
        if not ascii:
            return
        formats = self.formats(ascii)
        if not formats:
            return
        for match, fmts in formats:
            start = match.start()
            groups = match.groups()

            # No groups in the regex, assume this is a single rule
            # that spans the entire line
            if not groups:
                self.setFormat(0, len(ascii), fmts)
                continue

            # Groups exist, rule is a tuple corresponding to group
            for grpidx, group in enumerate(groups):
                # allow empty matches
                if not group:
                    continue
                # allow None as a no-op format
                length = len(group)
                if fmts[grpidx]:
                    self.setFormat(start, start+length,
                            fmts[grpidx])
                start += length

    def set_colors(self, colordict):
        for attr, val in colordict.items():
            setattr(self, attr, val)


class DiffSyntaxHighlighter(GenericSyntaxHighligher):
    """Implements the diff syntax highlighting

    This class is used by widgets that display diffs.

    """
    def __init__(self, doc, whitespace=True):
        self.whitespace = whitespace
        GenericSyntaxHighligher.__init__(self, doc)

    def generate_rules(self):
        diff_head = self.mkformat(fg=self.color_header)
        diff_head_bold = self.mkformat(fg=self.color_header, bold=True)

        diff_add = self.mkformat(fg=self.color_text, bg=self.color_add)
        diff_remove = self.mkformat(fg=self.color_text, bg=self.color_remove)

        if self.whitespace:
            bad_ws = self.mkformat(fg=Qt.black, bg=Qt.red)

        # We specify the whitespace rule last so that it is
        # applied after the diff addition/removal rules.
        # The rules for the header
        diff_old_rgx = TERMINAL(r'^--- ')
        diff_new_rgx = TERMINAL(r'^\+\+\+ ')
        diff_ctx_rgx = TERMINAL(r'^@@ ')

        diff_hd1_rgx = TERMINAL(r'^diff --git a/.*b/.*')
        diff_hd2_rgx = TERMINAL(r'^index \S+\.\.\S+')
        diff_hd3_rgx = TERMINAL(r'^new file mode')
        diff_hd4_rgx = TERMINAL(r'^deleted file mode')
        diff_add_rgx = TERMINAL(r'^\+')
        diff_rmv_rgx = TERMINAL(r'^-')
        diff_bar_rgx = TERMINAL(r'^([ ]+.*)(\|[ ]+\d+[ ]+[+-]+)$')
        diff_sts_rgx = (r'(.+\|.+?)(\d+)(.+?)([\+]*?)([-]*?)$')
        diff_sum_rgx = (r'(\s+\d+ files changed[^\d]*)'
                        r'(:?\d+ insertions[^\d]*)'
                        r'(:?\d+ deletions.*)$')

        self.create_rules(diff_old_rgx,     diff_head,
                          diff_new_rgx,     diff_head,
                          diff_ctx_rgx,     diff_head_bold,
                          diff_bar_rgx,     (diff_head_bold, diff_head),
                          diff_hd1_rgx,     diff_head,
                          diff_hd2_rgx,     diff_head,
                          diff_hd3_rgx,     diff_head,
                          diff_hd4_rgx,     diff_head,
                          diff_add_rgx,     diff_add,
                          diff_rmv_rgx,     diff_remove,
                          diff_sts_rgx,     (None, diff_head,
                                             None, diff_head,
                                             diff_head),
                          diff_sum_rgx,     (diff_head,
                                             diff_head,
                                             diff_head))
        if self.whitespace:
            self.create_rules(r'(..*?)(\s+)$', (None, bad_ws))


def install():
    Interaction.critical = staticmethod(critical)
    Interaction.confirm = staticmethod(confirm)
    Interaction.question = staticmethod(question)
    Interaction.information = staticmethod(information)

########NEW FILE########
__FILENAME__ = resources
"""Provides the prefix() function for finding cola resources"""
from __future__ import division, absolute_import, unicode_literals

import os
import webbrowser
from os.path import dirname

from cola import core


_modpath = core.abspath(__file__)
if os.path.join('share', 'git-cola', 'lib') in _modpath:
    # this is the release tree
    # __file__ = '$prefix/share/git-cola/lib/cola/__file__.py'
    _lib_dir = dirname(dirname(_modpath))
    _prefix = dirname(dirname(dirname(_lib_dir)))
else:
    # this is the source tree
    # __file__ = '$prefix/cola/__file__.py'
    _prefix = dirname(dirname(_modpath))


def prefix(*args):
    """Return a path relative to cola's installation prefix"""
    return os.path.join(_prefix, *args)


def doc(*args):
    """Return a path relative to cola's /usr/share/doc/ directory"""
    return os.path.join(_prefix, 'share', 'doc', 'git-cola', *args)


def html_docs():
    """Return the path to the cola html documentation."""
    # index.html only exists after the install-docs target is run,
    # so fallback to git-cola.rst.
    htmldocs = doc('html', 'index.html')
    if core.exists(htmldocs):
        return htmldocs
    return doc('git-cola.rst')


def show_html_docs():
    url = html_docs()
    webbrowser.open_new_tab('file://' + url)

def share(*args):
    """Return a path relative to cola's /usr/share/ directory"""
    return prefix('share', 'git-cola', *args)


def icon(basename):
    """Return the full path to an icon file given a basename."""
    return 'icons:'+basename


def icon_dir():
    """Return the path to the style dir within the cola install tree."""
    return share('icons')


def config_home(*args):
    config = core.getenv('XDG_CONFIG_HOME',
                         os.path.join(core.expanduser('~'), '.config'))
    return os.path.join(config, 'git-cola', *args)

########NEW FILE########
__FILENAME__ = settings
# Copyright (c) 2008 David Aguilar
"""This handles saving complex settings such as bookmarks, etc.
"""
from __future__ import division, absolute_import, unicode_literals

import os
import sys

from cola import core
from cola import git
from cola import resources
import json


def mkdict(obj):
    if type(obj) is dict:
        return obj
    else:
        return {}


def mklist(obj):
    if type(obj) is list:
        return obj
    else:
        return []


def read_json(path):
    try:
        with core.xopen(path, 'rt') as fp:
            return mkdict(json.load(fp))
    except: # bad path or json
        return {}


def write_json(values, path):
    try:
        parent = os.path.dirname(path)
        if not core.isdir(parent):
            core.makedirs(parent)
        with core.xopen(path, 'wt') as fp:
            json.dump(values, fp, indent=4)
    except:
        sys.stderr.write('git-cola: error writing "%s"\n' % path)


class Settings(object):
    _file = resources.config_home('settings')
    bookmarks = property(lambda self: mklist(self.values['bookmarks']))
    gui_state = property(lambda self: mkdict(self.values['gui_state']))
    recent = property(lambda self: mklist(self.values['recent']))

    def __init__(self, verify=git.is_git_worktree):
        """Load existing settings if they exist"""
        self.values = {
                'bookmarks': [],
                'gui_state': {},
                'recent': [],
        }
        self.verify = verify

    def remove_missing(self):
        missing_bookmarks = []
        missing_recent = []

        for bookmark in self.bookmarks:
            if not self.verify(bookmark):
                missing_bookmarks.append(bookmark)

        for bookmark in missing_bookmarks:
            try:
                self.bookmarks.remove(bookmark)
            except:
                pass

        for recent in self.recent:
            if not self.verify(recent):
                missing_recent.append(recent)

        for recent in missing_recent:
            try:
                self.recent.remove(recent)
            except:
                pass

    def add_bookmark(self, bookmark):
        """Adds a bookmark to the saved settings"""
        if bookmark not in self.bookmarks:
            self.bookmarks.append(bookmark)

    def remove_bookmark(self, bookmark):
        """Removes a bookmark from the saved settings"""
        if bookmark in self.bookmarks:
            self.bookmarks.remove(bookmark)

    def add_recent(self, entry):
        if entry in self.recent:
            self.recent.remove(entry)
        self.recent.insert(0, entry)
        if len(self.recent) > 8:
            self.recent.pop()

    def path(self):
        return self._file

    def save(self):
        write_json(self.values, self.path())

    def load(self):
        self.values.update(self.asdict())
        self.remove_missing()

    def asdict(self):
        path = self.path()
        if core.exists(path):
            return read_json(path)
        # We couldn't find ~/.config/git-cola, try ~/.cola
        values = {}
        path = os.path.join(core.expanduser('~'), '.cola')
        if core.exists(path):
            json_values = read_json(path)
            # Keep only the entries we care about
            for key in self.values:
                try:
                    values[key] = json_values[key]
                except KeyError:
                    pass
        return values

    def reload_recent(self):
        values = self.asdict()
        self.values['recent'] = mklist(values.get('recent', []))

    def save_gui_state(self, gui):
        """Saves settings for a cola view"""
        name = gui.name()
        self.gui_state[name] = mkdict(gui.export_state())
        self.save()

    def get_gui_state(self, gui):
        """Returns the saved state for a gui"""
        try:
            state = mkdict(self.gui_state[gui.name()])
        except KeyError:
            state = self.gui_state[gui.name()] = {}
        return state


class Session(Settings):
    """Store per-session settings"""

    _sessions_dir = resources.config_home('sessions')

    git_path = property(lambda self: self.values['git_path'])
    repo = property(lambda self: self.values['repo'])

    def __init__(self, session_id, repo=None, git_path=None):
        Settings.__init__(self)
        self.session_id = session_id
        self.values.update({
                'git_path': git_path,
                'repo': repo,
        })

    def path(self):
        return os.path.join(self._sessions_dir, self.session_id)

    def load(self):
        path = self.path()
        if core.exists(path):
            self.values.update(read_json(path))
            try:
                os.unlink(path)
            except:
                pass
            return True
        return False

########NEW FILE########
__FILENAME__ = textwrap
"""Text wrapping and filling.
"""
from __future__ import division, absolute_import, unicode_literals

# Copyright (C) 1999-2001 Gregory P. Ward.
# Copyright (C) 2002, 2003 Python Software Foundation.
# Copyright (C) 2013, David Aguilar
# Written by Greg Ward <gward@python.net>
# Simplified for git-cola by David Aguilar <davvid@gmail.com>

import re

from cola.compat import ustr


class TextWrapper(object):
    """
    Object for wrapping/filling text.  The public interface consists of
    the wrap() and fill() methods; the other methods are just there for
    subclasses to override in order to tweak the default behaviour.
    If you want to completely replace the main wrapping algorithm,
    you'll probably have to override _wrap_chunks().

    Several instance attributes control various aspects of wrapping:
      width (default: 70)
        The preferred width of wrapped lines.
      tabwidth (default: 8)
        The width of a tab used when calculating line length.
      break_on_hyphens (default: true)
        Allow breaking hyphenated words. If true, wrapping will occur
        preferably on whitespaces and right after hyphens part of
        compound words.
      drop_whitespace (default: true)
        Drop leading and trailing whitespace from lines.
    """

    # This funky little regex is just the trick for splitting
    # text up into word-wrappable chunks.  E.g.
    #   "Hello there -- you goof-ball, use the -b option!"
    # splits into
    #   Hello/ /there/ /--/ /you/ /goof-/ball,/ /use/ /the/ /-b/ /option!
    # (after stripping out empty strings).
    wordsep_re = re.compile(
        r'(\s+|'                                  # any whitespace
        r'[^\s\w]*\w+[^0-9\W]-(?=\w+[^0-9\W])|'   # hyphenated words
        r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w))')   # em-dash

    # This less funky little regex just split on recognized spaces. E.g.
    #   "Hello there -- you goof-ball, use the -b option!"
    # splits into
    #   Hello/ /there/ /--/ /you/ /goof-ball,/ /use/ /the/ /-b/ /option!/
    wordsep_simple_re = re.compile(r'(\s+)')

    def __init__(self,
                 width=70,
                 tabwidth=8,
                 break_on_hyphens=True,
                 drop_whitespace=True):
        self.width = width
        self.tabwidth = tabwidth
        self.break_on_hyphens = break_on_hyphens
        self.drop_whitespace = drop_whitespace

        # recompile the regexes for Unicode mode -- done in this clumsy way for
        # backwards compatibility because it's rather common to monkey-patch
        # the TextWrapper class' wordsep_re attribute.
        self.wordsep_re_uni = re.compile(self.wordsep_re.pattern, re.U)
        self.wordsep_simple_re_uni = re.compile(
            self.wordsep_simple_re.pattern, re.U)

    def _split(self, text):
        """_split(text : string) -> [string]

        Split the text to wrap into indivisible chunks.  Chunks are
        not quite the same as words; see _wrap_chunks() for full
        details.  As an example, the text
          Look, goof-ball -- use the -b option!
        breaks into the following chunks:
          'Look,', ' ', 'goof-', 'ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', 'option!'
        if break_on_hyphens is True, or in:
          'Look,', ' ', 'goof-ball', ' ', '--', ' ',
          'use', ' ', 'the', ' ', '-b', ' ', option!'
        otherwise.
        """
        if isinstance(text, ustr):
            if self.break_on_hyphens:
                pat = self.wordsep_re_uni
            else:
                pat = self.wordsep_simple_re_uni
        else:
            if self.break_on_hyphens:
                pat = self.wordsep_re
            else:
                pat = self.wordsep_simple_re
        chunks = pat.split(text)
        chunks = list(filter(None, chunks))  # remove empty chunks
        return chunks

    def _wrap_chunks(self, chunks):
        """_wrap_chunks(chunks : [string]) -> [string]

        Wrap a sequence of text chunks and return a list of lines of length
        'self.width' or less.  Some lines may be longer than this.  Chunks
        correspond roughly to words and the whitespace between them: each
        chunk is indivisible, but a line break can come between any two
        chunks.  Chunks should not have internal whitespace; ie. a chunk is
        either all whitespace or a "word".  Whitespace chunks will be removed
        from the beginning and end of lines, but apart from that whitespace is
        preserved.
        """
        lines = []

        # Arrange in reverse order so items can be efficiently popped
        # from a stack of chucks.
        chunks = list(reversed(chunks))

        while chunks:

            # Start the list of chunks that will make up the current line.
            # cur_len is just the length of all the chunks in cur_line.
            cur_line = []
            cur_len = 0

            # Maximum width for this line.
            width = self.width

            # First chunk on line is a space -- drop it, unless this
            # is the very beginning of the text (ie. no lines started yet).
            if self.drop_whitespace and chunks[-1] == ' ' and lines:
                chunks.pop()

            while chunks:
                l = self.chunklen(chunks[-1])

                # Can at least squeeze this chunk onto the current line.
                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l
                # Nope, this line is full.
                else:
                    break

            # The current line is full, and the next chunk is too big to
            # fit on *any* line (not just this one).
            if chunks and self.chunklen(chunks[-1]) > width:
                if not cur_line:
                    cur_line.append(chunks.pop())

            # If the last chunk on this line is all a space, drop it.
            if self.drop_whitespace and cur_line and cur_line[-1] == ' ':
                cur_line.pop()

            # Avoid whitespace at the beginining of the line.
            if (self.drop_whitespace and cur_line and
                    cur_line[0] in (' ', '  ')):
                cur_line.pop(0)

            # Convert current line back to a string and store it in list
            # of all lines (return value).
            if cur_line:
                lines.append(''.join(cur_line))

        return lines

    def chunklen(self, word):
        """Return length of a word taking tabs into account

        >>> w = TextWrapper(tabwidth=8)
        >>> w.chunklen("\\t\\t\\t\\tX")
        33

        """
        return len(word.replace('\t', '')) + word.count('\t') * self.tabwidth


    # -- Public interface ----------------------------------------------

    def wrap(self, text):
        """wrap(text : string) -> [string]

        Reformat the single paragraph in 'text' so it fits in lines of
        no more than 'self.width' columns, and return a list of wrapped
        lines.  Tabs in 'text' are expanded with string.expandtabs(),
        and all other whitespace characters (including newline) are
        converted to space.
        """
        chunks = self._split(text)
        return self._wrap_chunks(chunks)

    def fill(self, text):
        """fill(text : string) -> string

        Reformat the single paragraph in 'text' to fit in lines of no
        more than 'self.width' columns, and return a new string
        containing the entire wrapped paragraph.
        """
        return "\n".join(self.wrap(text))


def word_wrap(text, tabwidth, limit):
    r"""Wrap long lines to the specified limit

    >>> text = 'a bb ccc dddd\neeeee'
    >>> word_wrap(text, 8, 2)
    u'a\nbb\nccc\ndddd\neeeee'

    >>> word_wrap(text, 8, 4)
    u'a bb\nccc\ndddd\neeeee'

    >>> text = 'a bb ccc dddd\n\teeeee'
    >>> word_wrap(text, 8, 4)
    u'a bb\nccc\ndddd\n\t\neeeee'

    """

    lines = []

    # Acked-by:, Signed-off-by:, Helped-by:, etc.
    special_tag_rgx = re.compile(
            r'^('
            r'Acked-by|'
            r"Ack'd-by|"
            r'Based-on-patch-by|'
            r'Cheered-on-by|'
            r'Co-authored-by|'
            r'Comments-by|'
            r'Confirmed-by|'
            r'Contributions-by|'
            r'Debugged-by|'
            r'Discovered-by|'
            r'Explained-by|'
            r'Backtraced-by|'
            r'Helped-by|'
            r'Liked-by|'
            r'Improved-by|'
            r'Inspired-by|'
            r'Initial-patch-by|'
            r'Noticed-by|'
            r'Original-patch-by|'
            r'Originally-by|'
            r'Mentored-by|'
            r'Patch-by|'
            r'Proposed-by|'
            r'Reported-by|'
            r'Requested-by|'
            r'Reviewed-by|'
            r'Signed-off-by|'
            r'Signed-Off-by|'
            r'Spotted-by|'
            r'Suggested-by|'
            r'Tested-by|'
            r'Tested-on-([a-zA-Z-_]+)-by|'
            r'With-suggestions-by'
            r'):')

    w = TextWrapper(width=limit,
                    tabwidth=tabwidth,
                    break_on_hyphens=True,
                    drop_whitespace=True)

    for line in text.split('\n'):
        if special_tag_rgx.match(line):
            lines.append(line)
        else:
            lines.append(w.fill(line))

    return '\n'.join(lines)

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2008 David Aguilar
"""This module provides miscellaneous utility functions."""
from __future__ import division, absolute_import, unicode_literals

import mimetypes
import os
import random
import re
import shlex
import sys
import time
import traceback

from cola import core
from cola import resources
import hashlib

random.seed(hash(time.time()))


KNOWN_FILE_MIME_TYPES = {
    'text':      'script.png',
    'image':     'image.png',
    'python':    'script.png',
    'ruby':      'script.png',
    'shell':     'script.png',
    'perl':      'script.png',
    'octet':     'binary.png',
}

KNOWN_FILE_EXTENSION = {
    '.java':    'script.png',
    '.groovy':  'script.png',
    '.cpp':     'script.png',
    '.c':       'script.png',
    '.h':       'script.png',
    '.cxx':     'script.png',
}


def add_parents(path_entry_set):
    """Iterate over each item in the set and add its parent directories."""
    for path in list(path_entry_set):
        while '//' in path:
            path = path.replace('//', '/')
        if path not in path_entry_set:
            path_entry_set.add(path)
        if '/' in path:
            parent_dir = dirname(path)
            while parent_dir and parent_dir not in path_entry_set:
                path_entry_set.add(parent_dir)
                parent_dir = dirname(parent_dir)
    return path_entry_set


def ident_file_type(filename, exists):
    """Returns an icon based on the contents of filename."""
    if exists:
        filemimetype = mimetypes.guess_type(filename)
        if filemimetype[0] != None:
            for filetype, iconname in KNOWN_FILE_MIME_TYPES.items():
                if filetype in filemimetype[0].lower():
                    return iconname
        filename = filename.lower()
        for fileext, iconname in KNOWN_FILE_EXTENSION.items():
            if filename.endswith(fileext):
                return iconname
        return 'generic.png'
    else:
        return 'removed.png'
    # Fallback for modified files of an unknown type
    return 'generic.png'


def file_icon(filename):
    """
    Returns the full path to an icon file corresponding to
    filename"s contents.
    """
    exists = core.exists(filename)
    return (resources.icon(ident_file_type(filename, exists)), exists)


def format_exception(e):
    exc_type, exc_value, exc_tb = sys.exc_info()
    details = traceback.format_exception(exc_type, exc_value, exc_tb)
    details = '\n'.join(details)
    if hasattr(e, 'msg'):
        msg = e.msg
    else:
        msg = str(e)
    return (msg, details)


def sublist(a,b):
    """Subtracts list b from list a and returns the resulting list."""
    # conceptually, c = a - b
    c = []
    for item in a:
        if item not in b:
            c.append(item)
    return c


__grep_cache = {}
def grep(pattern, items, squash=True):
    """Greps a list for items that match a pattern and return a list of
    matching items.  If only one item matches, return just that item.
    """
    isdict = type(items) is dict
    if pattern in __grep_cache:
        regex = __grep_cache[pattern]
    else:
        regex = __grep_cache[pattern] = re.compile(pattern)
    matched = []
    matchdict = {}
    for item in items:
        match = regex.match(item)
        if not match:
            continue
        groups = match.groups()
        if not groups:
            subitems = match.group(0)
        else:
            if len(groups) == 1:
                subitems = groups[0]
            else:
                subitems = list(groups)
        if isdict:
            matchdict[item] = items[item]
        else:
            matched.append(subitems)

    if isdict:
        return matchdict
    else:
        if squash and len(matched) == 1:
            return matched[0]
        else:
            return matched


def basename(path):
    """
    An os.path.basename() implementation that always uses '/'

    Avoid os.path.basename because git's output always
    uses '/' regardless of platform.

    """
    return path.rsplit('/', 1)[-1]


def strip_one(path):
    """Strip one level of directory

    >>> strip_one('/usr/bin/git')
    u'bin/git'

    >>> strip_one('local/bin/git')
    u'bin/git'

    >>> strip_one('bin/git')
    u'git'

    >>> strip_one('git')
    u'git'

    """
    return path.strip('/').split('/', 1)[-1]


def dirname(path):
    """
    An os.path.dirname() implementation that always uses '/'

    Avoid os.path.dirname because git's output always
    uses '/' regardless of platform.

    """
    while '//' in path:
        path = path.replace('//', '/')
    path_dirname = path.rsplit('/', 1)[0]
    if path_dirname == path:
        return ''
    return path.rsplit('/', 1)[0]


def strip_prefix(prefix, string):
    """Return string, without the prefix. Blow up if string doesn't
    start with prefix."""
    assert string.startswith(prefix)
    return string[len(prefix):]


def sanitize(s):
    """Removes shell metacharacters from a string."""
    for c in """ \t!@#$%^&*()\\;,<>"'[]{}~|""":
        s = s.replace(c, '_')
    return s


def tablength(word, tabwidth):
    """Return length of a word taking tabs into account

    >>> tablength("\\t\\t\\t\\tX", 8)
    33

    """
    return len(word.replace('\t', '')) + word.count('\t') * tabwidth


def _shell_split(s):
    """Split string apart into utf-8 encoded words using shell syntax"""
    try:
        return shlex.split(core.encode(s))
    except ValueError:
        return [core.encode(s)]


if sys.version_info[0] == 3:
    # In Python 3, we don't need the encode/decode dance
    shell_split = shlex.split
else:
    def shell_split(s):
        """Returns a unicode list instead of encoded strings"""
        return [core.decode(arg) for arg in _shell_split(s)]


def tmp_dir():
    # Allow TMPDIR/TMP with a fallback to /tmp
    return core.getenv('TMP', core.getenv('TMPDIR', '/tmp'))


def tmp_file_pattern():
    return os.path.join(tmp_dir(), 'git-cola-%s-.*' % os.getpid())


def tmp_filename(prefix):
    randstr = ''.join([chr(random.randint(ord('a'), ord('z')))
                        for i in range(7)])
    prefix = prefix.replace('/', '-').replace('\\', '-')
    basename = 'git-cola-%s-%s-%s' % (os.getpid(), randstr, prefix)
    return os.path.join(tmp_dir(), basename)


def is_linux():
    """Is this a linux machine?"""
    return sys.platform.startswith('linux')


def is_debian():
    """Is it debian?"""
    return os.path.exists('/usr/bin/apt-get')


def is_darwin():
    """Return True on OSX."""
    return sys.platform == 'darwin'


def is_win32():
    """Return True on win32"""
    return sys.platform == 'win32' or sys.platform == 'cygwin'


def checksum(path):
    """Return a cheap md5 hexdigest for a path."""
    md5 = hashlib.new('md5')
    md5.update(open(path, 'rb').read())
    return md5.hexdigest()

########NEW FILE########
__FILENAME__ = version
# Copyright (c) David Aguilar
"""Provide git-cola's version number"""
from __future__ import division, absolute_import, unicode_literals

import os
import sys

if __name__ == '__main__':
    srcdir = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(1, srcdir)

from cola.git import git
from cola.git import STDOUT
from cola.decorators import memoize
from cola._version import VERSION

# minimum version requirements
_versions = {
    # git-diff learned --patience in 1.6.2
    # git-mergetool learned --no-prompt in 1.6.2
    # git-difftool moved out of contrib in git 1.6.3
    'git': '1.6.3',
    'python': '2.6',
    'pyqt': '4.4',
    'pyqt_qrunnable': '4.4',
    'diff-submodule': '1.6.6',
}


def get(key):
    """Returns an entry from the known versions table"""
    return _versions.get(key)


def version():
    """Returns the current version"""
    return VERSION


@memoize
def check_version(min_ver, ver):
    """Check whether ver is greater or equal to min_ver
    """
    min_ver_list = version_to_list(min_ver)
    ver_list = version_to_list(ver)
    return min_ver_list <= ver_list


@memoize
def check(key, ver):
    """Checks if a version is greater than the known version for <what>"""
    return check_version(get(key), ver)


def version_to_list(version):
    """Convert a version string to a list of numbers or strings
    """
    ver_list = []
    for p in version.split('.'):
        try:
            n = int(p)
        except ValueError:
            n = p
        ver_list.append(n)
    return ver_list


@memoize
def git_version_str():
    """Returns the current GIT version"""
    return git.version()[STDOUT].strip()

@memoize
def git_version():
    """Returns the current GIT version"""
    parts = git_version_str().split()
    if parts and len(parts) >= 3:
        return parts[2]
    else:
        # minimum supported version
        return '1.6.3'


def print_version(brief=False):
    if brief:
        print('%s' % version())
    else:
        print('cola version %s' % version())


if __name__ == '__main__':
    print(version())

########NEW FILE########
__FILENAME__ = about
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4.QtCore import Qt


from cola import core
from cola import resources
from cola import qtutils
from cola import version
from cola.i18n import N_
from cola.widgets import defs
from cola.widgets.text import MonoTextView

def launch_about_dialog():
    """Launches the Help -> About dialog"""
    view = AboutView(qtutils.active_window())
    view.set_version(version.version())
    view.show()


COPYRIGHT = """git-cola: The highly caffeinated git GUI v$VERSION

Copyright (C) 2007-2014, David Aguilar and contributors

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License
version 2 as published by the Free Software Foundation.

This program is distributed in the hope that it will
be useful, but WITHOUT ANY WARRANTY; without even the
implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the
GNU General Public License along with this program.
If not, see http://www.gnu.org/licenses/.

"""

class AboutView(QtGui.QDialog):
    """Provides the git-cola 'About' dialog.
    """
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle(N_('About git-cola'))
        self.setWindowModality(Qt.WindowModal)

        self.label = QtGui.QLabel()
        self.pixmap = QtGui.QPixmap('icons:logo-top.png')
        #self.label.setStyleSheet('QWidget {background: #000; }')
        self.label.setPixmap(self.pixmap)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignTop)

        palette = self.label.palette()
        palette.setColor(QtGui.QPalette.Window, Qt.black)
        self.label.setAutoFillBackground(True)
        self.label.setPalette(palette)

        self.text = MonoTextView(self)
        self.text.setReadOnly(True)
        self.text.setPlainText(COPYRIGHT)

        self.close_button = QtGui.QPushButton()
        self.close_button.setText(N_('Close'))
        self.close_button.setDefault(True)

        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.close_button)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(0)
        self.main_layout.setSpacing(defs.spacing)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.text)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)

        self.resize(666, 420)

        qtutils.connect_button(self.close_button, self.accept)

    def set_version(self, version):
        """Sets the version field in the 'about' dialog"""
        self.text.setPlainText(self.text.toPlainText().replace('$VERSION', version))


def show_shortcuts():
    try:
        from PyQt4 import QtWebKit
    except ImportError:
        # redhat disabled QtWebKit in their qt build but don't punish the
        # users
        qtutils.critical(N_('This PyQt4 does not include QtWebKit.\n'
                            'The keyboard shortcuts feature is unavailable.'))
        return

    try:
        html = show_shortcuts.html
    except AttributeError:
        hotkeys = resources.doc(N_('hotkeys.html'))
        html = show_shortcuts.html = core.read(hotkeys)

    try:
        widget = show_shortcuts.widget
    except AttributeError:
        parent = qtutils.active_window()
        widget = show_shortcuts.widget = QtGui.QDialog(parent)
        widget.setWindowModality(Qt.WindowModal)

        web = QtWebKit.QWebView(parent)
        web.setHtml(html)

        layout = QtGui.QHBoxLayout()
        layout.setMargin(0)
        layout.setSpacing(0)
        layout.addWidget(web)

        widget.setWindowTitle(N_('Shortcuts'))
        widget.setLayout(layout)
        widget.resize(800, min(parent.height(), 600))

        qtutils.add_action(widget, N_('Close'), widget.accept,
                           Qt.Key_Question,
                           Qt.Key_Enter,
                           Qt.Key_Return)
    widget.show()
    return widget

########NEW FILE########
__FILENAME__ = action
"""The "Actions" widget"""
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui

from cola import cmds
from cola.i18n import N_
from cola.models.selection import selection_model
from cola.widgets import defs
from cola.widgets import remote
from cola.widgets import stash
from cola.qtutils import create_button
from cola.qtutils import connect_button


class QFlowLayoutWidget(QtGui.QWidget):

    _horizontal = QtGui.QBoxLayout.LeftToRight
    _vertical = QtGui.QBoxLayout.TopToBottom

    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        self._direction = self._vertical
        self._layout = layout = QtGui.QBoxLayout(self._direction)
        layout.setSpacing(defs.spacing)
        layout.setMargin(defs.margin)
        self.setLayout(layout)
        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Minimum)
        self.setSizePolicy(policy)
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.aspect_ratio = 0.8

    def resizeEvent(self, event):
        size = event.size()
        if size.width() * self.aspect_ratio < size.height():
            dxn = self._vertical
        else:
            dxn = self._horizontal

        if dxn != self._direction:
            self._direction = dxn
            self.layout().setDirection(dxn)


class ActionButtons(QFlowLayoutWidget):
    def __init__(self, parent=None):
        QFlowLayoutWidget.__init__(self, parent)
        layout = self.layout()
        self.stage_button = create_button(text=N_('Stage'), layout=layout)
        self.unstage_button = create_button(text=N_('Unstage'), layout=layout)
        self.refresh_button = create_button(text=N_('Refresh'), layout=layout)
        self.fetch_button = create_button(text=N_('Fetch...'), layout=layout)
        self.push_button = create_button(text=N_('Push...'), layout=layout)
        self.pull_button = create_button(text=N_('Pull...'), layout=layout)
        self.stash_button = create_button(text=N_('Stash...'), layout=layout)
        self.aspect_ratio = 0.4
        layout.addStretch()
        self.setMinimumHeight(30)

        # Add callbacks
        connect_button(self.refresh_button, cmds.run(cmds.Refresh))
        connect_button(self.fetch_button, remote.fetch)
        connect_button(self.push_button, remote.push)
        connect_button(self.pull_button, remote.pull)
        connect_button(self.stash_button, stash.stash)
        connect_button(self.stage_button, self.stage)
        connect_button(self.unstage_button, self.unstage)

    def stage(self):
        """Stage selected files, or all files if no selection exists."""
        paths = selection_model().unstaged
        if not paths:
            cmds.do(cmds.StageModified)
        else:
            cmds.do(cmds.Stage, paths)

    def unstage(self):
        """Unstage selected files, or all files if no selection exists."""
        paths = selection_model().staged
        if not paths:
            cmds.do(cmds.UnstageAll)
        else:
            cmds.do(cmds.Unstage, paths)

########NEW FILE########
__FILENAME__ = archive
from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import qtutils
from cola.git import git
from cola.git import STDOUT
from cola.i18n import N_
from cola.widgets import defs
from cola.compat import ustr


class ExpandableGroupBox(QtGui.QGroupBox):
    def __init__(self, parent=None):
        QtGui.QGroupBox.__init__(self, parent)
        self.setFlat(True)
        self.expanded = True
        self.click_pos = None
        self.arrow_icon_size = 16

    def set_expanded(self, expanded):
        if expanded == self.expanded:
            self.emit(SIGNAL('expanded(bool)'), expanded)
            return
        self.expanded = expanded
        for widget in self.findChildren(QtGui.QWidget):
            widget.setHidden(not expanded)
        self.emit(SIGNAL('expanded(bool)'), expanded)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            option = QtGui.QStyleOptionGroupBox()
            self.initStyleOption(option)
            icon_size = self.arrow_icon_size
            button_area = QtCore.QRect(0, 0, icon_size, icon_size)
            offset = self.arrow_icon_size + defs.spacing
            adjusted = option.rect.adjusted(0, 0, -offset, 0)
            top_left = adjusted.topLeft()
            button_area.moveTopLeft(QtCore.QPoint(top_left))
            self.click_pos = event.pos()
        QtGui.QGroupBox.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        if (event.button() == Qt.LeftButton and
            self.click_pos == event.pos()):
            self.set_expanded(not self.expanded)
        QtGui.QGroupBox.mouseReleaseEvent(self, event)

    def paintEvent(self, event):
        painter = QtGui.QStylePainter(self)
        option = QtGui.QStyleOptionGroupBox()
        self.initStyleOption(option)
        painter.save()
        painter.translate(self.arrow_icon_size + defs.spacing, 0)
        painter.drawText(option.rect, Qt.AlignLeft, self.title())
        painter.restore()

        style = QtGui.QStyle
        point = option.rect.adjusted(0, -4, 0, 0).topLeft()
        icon_size = self.arrow_icon_size
        option.rect = QtCore.QRect(point.x(), point.y(), icon_size, icon_size)
        if self.expanded:
            painter.drawPrimitive(style.PE_IndicatorArrowDown, option)
        else:
            painter.drawPrimitive(style.PE_IndicatorArrowRight, option)



class GitArchiveDialog(QtGui.QDialog):

    @staticmethod
    def save_hashed_objects(ref, shortref, parent=None):
        dlg = GitArchiveDialog(ref, shortref, parent)
        if dlg.exec_() != dlg.Accepted:
            return None
        return dlg

    def __init__(self, ref, shortref=None, parent=None):
        QtGui.QDialog.__init__(self, parent)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # input
        self.ref = ref
        if shortref is None:
            shortref = ref

        # outputs
        self.fmt = None

        filename = '%s-%s' % (os.path.basename(os.getcwd()), shortref)
        self.prefix = filename + '/'
        self.filename = filename

        # widgets
        self.setWindowTitle(N_('Save Archive'))

        self.filetext = QtGui.QLineEdit()
        self.filetext.setText(self.filename)

        self.browse = QtGui.QToolButton()
        self.browse.setAutoRaise(True)
        style = self.style()
        self.browse.setIcon(style.standardIcon(QtGui.QStyle.SP_DirIcon))

        self.format_strings = (
                git.archive('--list')[STDOUT].rstrip().splitlines())
        self.format_combo = QtGui.QComboBox()
        self.format_combo.setEditable(False)
        self.format_combo.addItems(self.format_strings)

        self.cancel = QtGui.QPushButton()
        self.cancel.setText(N_('Cancel'))

        self.save = QtGui.QPushButton()
        self.save.setText(N_('Save'))
        self.save.setDefault(True)

        self.prefix_label = QtGui.QLabel()
        self.prefix_label.setText(N_('Prefix'))
        self.prefix_text = QtGui.QLineEdit()
        self.prefix_text.setText(self.prefix)

        self.prefix_group = ExpandableGroupBox()
        self.prefix_group.setTitle(N_('Advanced'))

        # layouts
        self.filelayt = QtGui.QHBoxLayout()
        self.filelayt.setMargin(0)
        self.filelayt.setSpacing(defs.spacing)
        self.filelayt.addWidget(self.browse)
        self.filelayt.addWidget(self.filetext)
        self.filelayt.addWidget(self.format_combo)

        self.prefixlayt = QtGui.QHBoxLayout()
        self.prefixlayt.setMargin(defs.margin)
        self.prefixlayt.setSpacing(defs.spacing)
        self.prefixlayt.addWidget(self.prefix_label)
        self.prefixlayt.addWidget(self.prefix_text)
        self.prefix_group.setLayout(self.prefixlayt)
        self.prefix_group.set_expanded(False)

        self.btnlayt = QtGui.QHBoxLayout()
        self.btnlayt.setMargin(0)
        self.btnlayt.setSpacing(defs.spacing)
        self.btnlayt.addStretch()
        self.btnlayt.addWidget(self.cancel)
        self.btnlayt.addWidget(self.save)

        self.mainlayt = QtGui.QVBoxLayout()
        self.mainlayt.setMargin(defs.margin)
        self.mainlayt.setSpacing(0)
        self.mainlayt.addLayout(self.filelayt)
        self.mainlayt.addWidget(self.prefix_group)
        self.mainlayt.addStretch()
        self.mainlayt.addLayout(self.btnlayt)
        self.setLayout(self.mainlayt)
        self.resize(555, 0)

        # initial setup; done before connecting to avoid
        # signal/slot side-effects
        if 'tar.gz' in self.format_strings:
            idx = self.format_strings.index('tar.gz')
        elif 'zip' in self.format_strings:
            idx = self.format_strings.index('zip')
        else:
            idx = 0
        self.format_combo.setCurrentIndex(idx)
        self.update_filetext_for_format(idx)

        # connections
        self.connect(self.filetext, SIGNAL('textChanged(QString)'),
                     self.filetext_changed)

        self.connect(self.prefix_text, SIGNAL('textChanged(QString)'),
                     self.prefix_text_changed)

        self.connect(self.format_combo, SIGNAL('currentIndexChanged(int)'),
                     self.update_filetext_for_format)

        self.connect(self.prefix_group, SIGNAL('expanded(bool)'),
                     self.prefix_group_expanded)

        self.connect(self, SIGNAL('accepted()'), self.archive_saved)

        qtutils.connect_button(self.browse, self.choose_filename)
        qtutils.connect_button(self.cancel, self.reject)
        qtutils.connect_button(self.save, self.save_archive)

    def archive_saved(self):
        cmds.do(cmds.Archive, self.ref, self.fmt, self.prefix, self.filename)
        qtutils.information(N_('File Saved'),
                            N_('File saved to "%s"') % self.filename)

    def save_archive(self):
        filename = self.filename
        if not filename:
            return
        if core.exists(filename):
            title = N_('Overwrite File?')
            msg = N_('The file "%s" exists and will be overwritten.') % filename
            info_txt = N_('Overwrite "%s"?') % filename
            ok_txt = N_('Overwrite')
            icon = qtutils.save_icon()
            if not qtutils.confirm(title, msg, info_txt, ok_txt,
                                   default=False, icon=icon):
                return
        self.accept()

    def choose_filename(self):
        filename = qtutils.save_as(self.filename)
        if not filename:
            return
        self.filetext.setText(filename)
        self.update_filetext_for_format(self.format_combo.currentIndex())

    def filetext_changed(self, qstr):
        self.filename = ustr(qstr)
        self.save.setEnabled(bool(self.filename))
        prefix = self.strip_exts(os.path.basename(self.filename)) + '/'
        self.prefix_text.setText(prefix)

    def prefix_text_changed(self, qstr):
        self.prefix = ustr(qstr)

    def strip_exts(self, text):
        for format_string in self.format_strings:
            ext = '.'+format_string
            if text.endswith(ext):
                return text[:-len(ext)]
        return text

    def update_filetext_for_format(self, idx):
        self.fmt = self.format_strings[idx]
        text = self.strip_exts(ustr(self.filetext.text()))
        self.filename = '%s.%s' % (text, self.fmt)
        self.filetext.setText(self.filename)
        self.filetext.setFocus()
        if '/' in text:
            start = text.rindex('/') + 1
        else:
            start = 0
        self.filetext.setSelection(start, len(text) - start)

    def prefix_group_expanded(self, expanded):
        if expanded:
            self.prefix_text.setFocus()
        else:
            self.filetext.setFocus()

########NEW FILE########
__FILENAME__ = bookmarks
"""Provides widgets related to bookmarks"""
from __future__ import division, absolute_import, unicode_literals

import os
import sys

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL


from cola import cmds
from cola import core
from cola import qtutils
from cola.i18n import N_
from cola.settings import Settings
from cola.widgets import defs
from cola.widgets import standard


def manage_bookmarks():
    dlg = BookmarksDialog(qtutils.active_window())
    dlg.show()
    dlg.exec_()
    return dlg


class BookmarksDialog(standard.Dialog):
    def __init__(self, parent):
        standard.Dialog.__init__(self, parent=parent)
        self.settings = Settings()
        self.settings.load()

        self.resize(494, 238)
        self.setWindowTitle(N_('Bookmarks'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
        self.layt = QtGui.QVBoxLayout(self)
        self.layt.setMargin(defs.margin)
        self.layt.setSpacing(defs.spacing)

        self.bookmarks = QtGui.QListWidget(self)
        self.bookmarks.setAlternatingRowColors(True)
        self.bookmarks.setSelectionMode(QtGui.QAbstractItemView
                                             .ExtendedSelection)

        self.layt.addWidget(self.bookmarks)
        self.button_layout = QtGui.QHBoxLayout()

        self.open_button = qtutils.create_button(text=N_('Open'),
                icon=qtutils.open_icon())
        self.open_button.setEnabled(False)
        self.button_layout.addWidget(self.open_button)

        self.add_button = qtutils.create_button(text=N_('Add'),
                icon=qtutils.add_icon())
        self.button_layout.addWidget(self.add_button)

        self.delete_button = QtGui.QPushButton(self)
        self.delete_button.setText(N_('Delete'))
        self.delete_button.setIcon(qtutils.discard_icon())
        self.delete_button.setEnabled(False)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addStretch()

        self.save_button = QtGui.QPushButton(self)
        self.save_button.setText(N_('Save'))
        self.save_button.setIcon(qtutils.save_icon())
        self.save_button.setEnabled(False)
        self.button_layout.addWidget(self.save_button)

        self.close_button = QtGui.QPushButton(self)
        self.close_button.setText(N_('Close'))
        self.button_layout.addWidget(self.close_button)

        self.layt.addLayout(self.button_layout)

        self.connect(self.bookmarks, SIGNAL('itemSelectionChanged()'),
                     self.item_selection_changed)

        qtutils.connect_button(self.open_button, self.open_repo)
        qtutils.connect_button(self.add_button, self.add)
        qtutils.connect_button(self.delete_button, self.delete)
        qtutils.connect_button(self.save_button, self.save)
        qtutils.connect_button(self.close_button, self.accept)

        self.update_bookmarks()

    def update_bookmarks(self):
        self.bookmarks.clear()
        self.bookmarks.addItems(self.settings.bookmarks)

    def selection(self):
        return qtutils.selection_list(self.bookmarks, self.settings.bookmarks)

    def item_selection_changed(self):
        has_selection = bool(self.selection())
        self.open_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def save(self):
        """Saves the bookmarks settings and exits"""
        self.settings.save()
        self.save_button.setEnabled(False)

    def add(self):
        path, ok = qtutils.prompt(N_('Path to git repository'),
                                  title=N_('Enter Git Repository'),
                                  text=core.getcwd())
        if not ok:
            return
        self.settings.bookmarks.append(path)
        self.update_bookmarks()
        self.save()

    def open_repo(self):
        """Opens a new git-cola session on a bookmark"""
        for repo in self.selection():
            core.fork([sys.executable, sys.argv[0], '--repo', repo])

    def delete(self):
        """Removes a bookmark from the bookmarks list"""
        selection = self.selection()
        if not selection:
            return
        for repo in selection:
            self.settings.remove_bookmark(repo)
        self.update_bookmarks()
        self.save_button.setEnabled(True)


class BookmarksWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.tree = BookmarksTreeWidget(parent=self)
        self.open_button = qtutils.create_action_button(
                tooltip=N_('Open'), icon=qtutils.open_icon())
        self.open_button.setEnabled(False)

        self.edit_button = qtutils.create_action_button(
                tooltip=N_('Bookmarks...'), icon=qtutils.add_icon())

        qtutils.connect_button(self.open_button, self.tree.open_repo)
        qtutils.connect_button(self.edit_button, self.manage_bookmarks)

        self.connect(self.tree, SIGNAL('itemSelectionChanged()'),
                     self._tree_selection_changed)

        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.setMargin(defs.no_margin)
        self.button_layout.setSpacing(defs.spacing)
        self.button_layout.addWidget(self.open_button)
        self.button_layout.addWidget(self.edit_button)

        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(defs.no_margin)
        self.layout.setSpacing(defs.spacing)
        self.layout.addWidget(self.tree)
        self.setLayout(self.layout)

        self.corner_widget = QtGui.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)
        self.setFocusProxy(self.tree)

    def _tree_selection_changed(self):
        enabled = bool(self.tree.selected_item())
        self.open_button.setEnabled(enabled)

    def manage_bookmarks(self):
        manage_bookmarks()
        self.refresh()

    def refresh(self):
        self.tree.refresh()


class BookmarksTreeWidget(standard.TreeWidget):

    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)

        self.open_action = qtutils.add_action(self,
                N_('Open'), self.open_repo, QtGui.QKeySequence.Open)
        self.open_action.setEnabled(False)

        self.open_new_action = qtutils.add_action(self,
                N_('Open in New Window'), self.open_new_repo,
                QtGui.QKeySequence.New)
        self.open_new_action.setEnabled(False)

        self.open_default_action = qtutils.add_action(self,
                cmds.OpenDefaultApp.name(), self.open_default,
                cmds.OpenDefaultApp.SHORTCUT)
        self.open_default_action.setEnabled(False)

        self.launch_editor_action = qtutils.add_action(self,
                cmds.Edit.name(), self.launch_editor,
                cmds.Edit.SHORTCUT)
        self.launch_editor_action.setEnabled(False)

        self.launch_terminal_action = qtutils.add_action(self,
                cmds.LaunchTerminal.name(), self.launch_terminal,
                cmds.LaunchTerminal.SHORTCUT)
        self.launch_terminal_action.setEnabled(False)

        self.copy_action = qtutils.add_action(self,
                N_('Copy'), self.copy, QtGui.QKeySequence.Copy)
        self.copy_action.setEnabled(False)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self._tree_selection_changed)

        self.connect(self, SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self._tree_double_clicked)

        self.refresh()

    def refresh(self):
        self.clear()
        settings = Settings()
        settings.load()
        items = []
        icon = qtutils.dir_icon()
        recents = set(settings.recent)
        for path in settings.recent:
            item = BookmarksTreeWidgetItem(path, icon)
            items.append(item)
        for path in settings.bookmarks:
            if path in recents: # avoid duplicates
                continue
            item = BookmarksTreeWidgetItem(path, icon)
            items.append(item)
        self.addTopLevelItems(items)

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)
        menu.addAction(self.open_action)
        menu.addAction(self.open_new_action)
        menu.addAction(self.open_default_action)
        menu.addSeparator()
        menu.addAction(self.copy_action)
        menu.addAction(self.launch_editor_action)
        menu.addAction(self.launch_terminal_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def copy(self):
        item = self.selected_item()
        if not item:
            return
        qtutils.set_clipboard(item.path)

    def open_default(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.OpenDefaultApp, [item.path])

    def open_repo(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.OpenRepo, item.path)

    def open_new_repo(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.OpenNewRepo, item.path)

    def launch_editor(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.Edit, [item.path])

    def launch_terminal(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.LaunchTerminal, item.path)

    def _tree_selection_changed(self):
        enabled = bool(self.selected_item())
        self.open_action.setEnabled(enabled)
        self.open_new_action.setEnabled(enabled)
        self.copy_action.setEnabled(enabled)
        self.launch_editor_action.setEnabled(enabled)
        self.launch_terminal_action.setEnabled(enabled)
        self.open_default_action.setEnabled(enabled)

    def _tree_double_clicked(self, item, column):
        cmds.do(cmds.OpenRepo, item.path)


class BookmarksTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, path, icon):
        QtGui.QTreeWidgetItem.__init__(self)
        self.path = path
        self.setIcon(0, icon)
        self.setText(0, os.path.basename(path))
        self.setToolTip(0, path)

########NEW FILE########
__FILENAME__ = browse
from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import difftool
from cola import gitcmds
from cola import utils
from cola import qtutils
from cola.cmds import BaseCommand
from cola.git import git
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.models.browse import GitRepoModel
from cola.models.browse import GitRepoEntryManager
from cola.models.browse import GitRepoNameItem
from cola.models.selection import State
from cola.models.selection import selection_model
from cola.widgets import defs
from cola.widgets import standard
from cola.widgets.selectcommits import select_commits
from cola.compat import ustr


def worktree_browser_widget(parent, update=True):
    """Return a widget for immediate use."""
    view = Browser(parent, update=update)
    view.tree.setModel(GitRepoModel(view.tree))
    view.ctl = BrowserController(view.tree)
    return view


def worktree_browser(update=True):
    """Launch a new worktree browser session."""
    view = worktree_browser_widget(None, update=update)
    view.show()
    return view


class Browser(standard.Widget):
    def __init__(self, parent, update=True):
        standard.Widget.__init__(self, parent)
        self.tree = RepoTreeView(self)
        self.mainlayout = QtGui.QHBoxLayout()
        self.setLayout(self.mainlayout)
        self.mainlayout.setMargin(0)
        self.mainlayout.setSpacing(defs.spacing)
        self.mainlayout.addWidget(self.tree)
        self.resize(720, 420)

        self.connect(self, SIGNAL('updated'), self._updated_callback)
        self.model = main.model()
        self.model.add_observer(self.model.message_updated, self.model_updated)
        qtutils.add_close_action(self)
        if update:
            self.model_updated()

    # Read-only mode property
    mode = property(lambda self: self.model.mode)

    def model_updated(self):
        """Update the title with the current branch and directory name."""
        self.emit(SIGNAL('updated'))

    def _updated_callback(self):
        branch = self.model.currentbranch
        curdir = os.getcwd()
        msg = N_('Repository: %s') % curdir
        msg += '\n'
        msg += N_('Branch: %s') % branch
        self.setToolTip(msg)

        title = N_('%s: %s - Browse') % (self.model.project, branch)
        if self.mode == self.model.mode_amend:
            title += ' (%s)' % N_('Amending')
        self.setWindowTitle(title)


class RepoTreeView(standard.TreeView):
    """Provides a filesystem-like view of a git repository."""

    def __init__(self, parent):
        standard.TreeView.__init__(self, parent)

        self.setRootIsDecorated(True)
        self.setSortingEnabled(False)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        # Observe model updates
        model = main.model()
        model.add_observer(model.message_updated, self.update_actions)

        # The non-Qt cola application model
        self.connect(self, SIGNAL('expanded(QModelIndex)'), self.size_columns)
        self.connect(self, SIGNAL('collapsed(QModelIndex)'), self.size_columns)

        # Sync selection before the key press event changes the model index
        self.connect(self, SIGNAL('indexAboutToChange()'), self.sync_selection)

        self.action_history =\
                self._create_action(
                        N_('View History...'),
                        N_('View history for selected path(s).'),
                        self.view_history,
                        'Shift+Ctrl+H')
        self.action_stage =\
                self._create_action(N_('Stage Selected'),
                                    N_('Stage selected path(s) for commit.'),
                                    self.stage_selected,
                                    cmds.Stage.SHORTCUT)
        self.action_unstage =\
                self._create_action(
                        N_('Unstage Selected'),
                        N_('Remove selected path(s) from the staging area.'),
                        self.unstage_selected,
                        'Ctrl+U')

        self.action_untrack =\
                self._create_action(N_('Untrack Selected'),
                                    N_('Stop tracking path(s)'),
                                    self.untrack_selected)

        self.action_difftool =\
                self._create_action(cmds.LaunchDifftool.name(),
                                    N_('Launch git-difftool on the current path.'),
                                    cmds.run(cmds.LaunchDifftool),
                                    cmds.LaunchDifftool.SHORTCUT)
        self.action_difftool_predecessor =\
                self._create_action(N_('Diff Against Predecessor...'),
                                    N_('Launch git-difftool against previous versions.'),
                                    self.difftool_predecessor,
                                    'Shift+Ctrl+D')
        self.action_revert =\
                self._create_action(N_('Revert Uncommitted Changes...'),
                                    N_('Revert changes to selected path(s).'),
                                    self.revert,
                                    'Ctrl+Z')
        self.action_editor =\
                self._create_action(cmds.LaunchEditor.name(),
                                    N_('Edit selected path(s).'),
                                    cmds.run(cmds.LaunchEditor),
                                    cmds.LaunchDifftool.SHORTCUT)

    def size_columns(self):
        """Set the column widths."""
        self.resizeColumnToContents(0)

    def update_actions(self):
        """Enable/disable actions."""
        selection = self.selected_paths()
        selected = bool(selection)
        staged = bool(self.selected_staged_paths(selection=selection))
        modified = bool(self.selected_modified_paths(selection=selection))
        unstaged = bool(self.selected_unstaged_paths(selection=selection))
        tracked = bool(self.selected_tracked_paths())

        self.action_history.setEnabled(selected)
        self.action_stage.setEnabled(unstaged)
        self.action_unstage.setEnabled(staged)
        self.action_untrack.setEnabled(tracked)
        self.action_difftool.setEnabled(staged or modified)
        self.action_difftool_predecessor.setEnabled(tracked)
        self.action_revert.setEnabled(tracked)

    def contextMenuEvent(self, event):
        """Create a context menu."""
        self.update_actions()
        menu = QtGui.QMenu(self)
        menu.addAction(self.action_editor)
        menu.addAction(self.action_stage)
        menu.addAction(self.action_unstage)
        menu.addSeparator()
        menu.addAction(self.action_history)
        menu.addAction(self.action_difftool)
        menu.addAction(self.action_difftool_predecessor)
        menu.addSeparator()
        menu.addAction(self.action_revert)
        menu.addAction(self.action_untrack)
        menu.exec_(self.mapToGlobal(event.pos()))

    def mousePressEvent(self, event):
        """Synchronize the selection on mouse-press."""
        result = QtGui.QTreeView.mousePressEvent(self, event)
        self.sync_selection()
        return result

    def sync_selection(self):
        """Push selection into the selection model."""
        staged = []
        unmerged = []
        modified = []
        untracked = []
        state = State(staged, unmerged, modified, untracked)

        paths = self.selected_paths()
        model = main.model()
        model_staged = utils.add_parents(set(model.staged))
        model_modified = utils.add_parents(set(model.modified))
        model_unmerged = utils.add_parents(set(model.unmerged))
        model_untracked = utils.add_parents(set(model.untracked))

        for path in paths:
            if path in model_unmerged:
                unmerged.append(path)
            elif path in model_untracked:
                untracked.append(path)
            elif path in model_staged:
                staged.append(path)
            elif path in model_modified:
                modified.append(path)
            else:
                staged.append(path)
        # Push the new selection into the model.
        selection_model().set_selection(state)
        return paths

    def selectionChanged(self, old_selection, new_selection):
        """Override selectionChanged to update available actions."""
        result = QtGui.QTreeView.selectionChanged(self, old_selection, new_selection)
        self.update_actions()
        paths = self.sync_selection()

        if paths and self.model().path_is_interesting(paths[0]):
            cached = paths[0] in main.model().staged
            cmds.do(cmds.Diff, paths, cached)
        return result

    def setModel(self, model):
        """Set the concrete QAbstractItemModel instance."""
        QtGui.QTreeView.setModel(self, model)
        self.size_columns()

    def item_from_index(self, model_index):
        """Return the name item corresponding to the model index."""
        index = model_index.sibling(model_index.row(), 0)
        return self.model().itemFromIndex(index)

    def selected_paths(self):
        """Return the selected paths."""
        items = map(self.model().itemFromIndex, self.selectedIndexes())
        return [i.path for i in items
                    if i.type() == GitRepoNameItem.TYPE]

    def selected_staged_paths(self, selection=None):
        """Return selected staged paths."""
        if not selection:
            selection = self.selected_paths()
        staged = utils.add_parents(set(main.model().staged))
        return [p for p in selection if p in staged]

    def selected_modified_paths(self, selection=None):
        """Return selected modified paths."""
        if not selection:
            selection = self.selected_paths()
        model = main.model()
        modified = utils.add_parents(set(model.modified))
        return [p for p in selection if p in modified]

    def selected_unstaged_paths(self, selection=None):
        """Return selected unstaged paths."""
        if not selection:
            selection = self.selected_paths()
        model = main.model()
        modified = utils.add_parents(set(model.modified))
        untracked = utils.add_parents(set(model.untracked))
        unstaged = modified.union(untracked)
        return [p for p in selection if p in unstaged]

    def selected_tracked_paths(self, selection=None):
        """Return selected tracked paths."""
        if not selection:
            selection = self.selected_paths()
        model = main.model()
        staged = set(self.selected_staged_paths())
        modified = set(self.selected_modified_paths())
        untracked = utils.add_parents(set(model.untracked))
        tracked = staged.union(modified)
        return [p for p in selection
                if p not in untracked or p in tracked]

    def _create_action(self, name, tooltip, slot, shortcut=None):
        """Create an action with a shortcut, tooltip, and callback slot."""
        action = QtGui.QAction(name, self)
        action.setStatusTip(tooltip)
        if shortcut is not None:
            if hasattr(Qt, 'WidgetWithChildrenShortcut'):
                action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            action.setShortcut(shortcut)
        self.addAction(action)
        qtutils.connect_action(action, slot)
        return action

    def view_history(self):
        """Signal that we should view history for paths."""
        self.emit(SIGNAL('history(QStringList)'), self.selected_paths())

    def stage_selected(self):
        """Signal that we should stage selected paths."""
        cmds.do(cmds.Stage, self.selected_unstaged_paths())

    def unstage_selected(self):
        """Signal that we should stage selected paths."""
        cmds.do(cmds.Unstage, self.selected_staged_paths())

    def untrack_selected(self):
        """untrack selected paths."""
        cmds.do(cmds.Untrack, self.selected_tracked_paths())

    def difftool_predecessor(self):
        """Diff paths against previous versions."""
        paths = self.selected_tracked_paths()
        self.emit(SIGNAL('difftool_predecessor'), paths)

    def revert(self):
        """Signal that we should revert changes to a path."""
        if not qtutils.confirm(N_('Revert Uncommitted Changes?'),
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               N_('Revert Uncommitted Changes'),
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        paths = self.selected_tracked_paths()
        cmds.do(cmds.Checkout, ['HEAD', '--'] + paths)

    def current_path(self):
        """Return the path for the current item."""
        index = self.currentIndex()
        if not index.isValid():
            return None
        return self.item_from_index(index).path


class BrowserController(QtCore.QObject):
    def __init__(self, view=None):
        QtCore.QObject.__init__(self, view)
        self.model = main.model()
        self.view = view
        self.updated = set()
        self.connect(view, SIGNAL('history(QStringList)'),
                     self.view_history)
        self.connect(view, SIGNAL('expanded(QModelIndex)'),
                     self.query_model)
        self.connect(view, SIGNAL('difftool_predecessor'),
                     self.difftool_predecessor)

    def view_history(self, entries):
        """Launch the configured history browser path-limited to entries."""
        entries = map(ustr, entries)
        cmds.do(cmds.VisualizePaths, entries)

    def query_model(self, model_index):
        """Update information about a directory as it is expanded."""
        item = self.view.item_from_index(model_index)
        path = item.path
        if path in self.updated:
            return
        self.updated.add(path)
        GitRepoEntryManager.entry(path).update()
        entry = GitRepoEntryManager.entry
        for row in range(item.rowCount()):
            path = item.child(row, 0).path
            entry(path).update()

    def difftool_predecessor(self, paths):
        """Prompt for an older commit and launch difftool against it."""
        args = ['--'] + paths
        revs, summaries = gitcmds.log_helper(all=False, extra_args=args)
        commits = select_commits(N_('Select Previous Version'),
                                 revs, summaries, multiselect=False)
        if not commits:
            return
        commit = commits[0]
        difftool.launch([commit, '--'] + paths)


class BrowseModel(object):
    def __init__(self, ref):
        self.ref = ref
        self.relpath = None
        self.filename = None


class SaveBlob(BaseCommand):
    def __init__(self, model):
        BaseCommand.__init__(self)
        self.model = model

    def do(self):
        model = self.model
        cmd = ['git', 'show', '%s:%s' % (model.ref, model.relpath)]
        with core.xopen(model.filename, 'wb') as fp:
            proc = core.start_command(cmd, stdout=fp)
            out, err = proc.communicate()

        status = proc.returncode
        msg = (N_('Saved "%(filename)s" from "%(ref)s" to "%(destination)s"') %
               dict(filename=model.relpath,
                    ref=model.ref,
                    destination=model.filename))
        Interaction.log_status(status, msg, '')

        Interaction.information(
                N_('File Saved'),
                N_('File saved to "%s"') % model.filename)



class BrowseDialog(QtGui.QDialog):

    @staticmethod
    def browse(ref):
        parent = qtutils.active_window()
        model = BrowseModel(ref)
        dlg = BrowseDialog(model, parent=parent)
        dlg_model = GitTreeModel(ref, dlg)
        dlg.setModel(dlg_model)
        dlg.setWindowTitle(N_('Browsing %s') % model.ref)
        if hasattr(parent, 'width'):
            dlg.resize(parent.width()*3//4, 333)
        else:
            dlg.resize(420, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return dlg

    @staticmethod
    def select_file(ref):
        parent = qtutils.active_window()
        model = BrowseModel(ref)
        dlg = BrowseDialog(model, select_file=True, parent=parent)
        dlg_model = GitTreeModel(ref, dlg)
        dlg.setModel(dlg_model)
        dlg.setWindowTitle(N_('Select file from "%s"') % model.ref)
        dlg.resize(parent.width()*3//4, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return model.filename

    @staticmethod
    def select_file_from_list(file_list, title=N_('Select File')):
        parent = qtutils.active_window()
        model = BrowseModel(None)
        dlg = BrowseDialog(model, select_file=True, parent=parent)
        dlg_model = GitFileTreeModel(dlg)
        dlg_model.add_files(file_list)
        dlg.setModel(dlg_model)
        dlg.expandAll()
        dlg.setWindowTitle(title)
        dlg.resize(parent.width()*3//4, 333)
        dlg.show()
        dlg.raise_()
        if dlg.exec_() != dlg.Accepted:
            return None
        return model.filename

    def __init__(self, model, select_file=False, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        # updated for use by commands
        self.model = model

        # widgets
        self.tree = GitTreeWidget(parent=self)
        self.close = QtGui.QPushButton(N_('Close'))
        self.save = QtGui.QPushButton(select_file and N_('Select') or N_('Save'))
        self.save.setDefault(True)
        self.save.setEnabled(False)

        # layouts
        self.btnlayt = QtGui.QHBoxLayout()
        self.btnlayt.addStretch()
        self.btnlayt.addWidget(self.close)
        self.btnlayt.addWidget(self.save)

        self.layt = QtGui.QVBoxLayout()
        self.layt.setMargin(defs.margin)
        self.layt.setSpacing(defs.spacing)
        self.layt.addWidget(self.tree)
        self.layt.addLayout(self.btnlayt)
        self.setLayout(self.layt)

        # connections
        if select_file:
            self.connect(self.tree, SIGNAL('path_chosen'), self.path_chosen)
        else:
            self.connect(self.tree, SIGNAL('path_chosen'), self.save_path)

        self.connect(self.tree, SIGNAL('selectionChanged()'),
                     self.selection_changed)

        qtutils.connect_button(self.close, self.reject)
        qtutils.connect_button(self.save, self.save_blob)

    def expandAll(self):
        self.tree.expandAll()

    def setModel(self, model):
        self.tree.setModel(model)

    def path_chosen(self, path, close=True):
        """Update the model from the view"""
        model = self.model
        model.relpath = path
        model.filename = path
        if close:
            self.accept()

    def save_path(self, path):
        """Choose an output filename based on the selected path"""
        self.path_chosen(path, close=False)
        model = self.model
        filename = qtutils.save_as(model.filename)
        if not filename:
            return
        model.filename = filename
        cmds.do(SaveBlob, model)
        self.accept()

    def save_blob(self):
        """Save the currently selected file"""
        filenames = self.tree.selected_files()
        if not filenames:
            return
        self.path_chosen(filenames[0], close=True)

    def selection_changed(self):
        """Update actions based on the current selection"""
        filenames = self.tree.selected_files()
        self.save.setEnabled(bool(filenames))


class GitTreeWidget(standard.TreeView):
    def __init__(self, parent=None):
        standard.TreeView.__init__(self, parent)
        self.setHeaderHidden(True)

        self.connect(self, SIGNAL('doubleClicked(const QModelIndex &)'),
                     self.double_clicked)

    def double_clicked(self, index):
        item = self.model().itemFromIndex(index)
        if item is None:
            return
        if item.is_dir:
            return
        self.emit(SIGNAL('path_chosen'), item.path)

    def selected_files(self):
        items = map(self.model().itemFromIndex, self.selectedIndexes())
        return [i.path for i in items if not i.is_dir]

    def selectionChanged(self, old_selection, new_selection):
        QtGui.QTreeView.selectionChanged(self, old_selection, new_selection)
        self.emit(SIGNAL('selectionChanged()'))

    def select_first_file(self):
        """Select the first filename in the tree"""
        model = self.model()
        idx = self.indexAt(QtCore.QPoint(0, 0))
        item = model.itemFromIndex(idx)
        while idx and idx.isValid() and item and item.is_dir:
            idx = self.indexBelow(idx)
            item = model.itemFromIndex(idx)

        if idx and idx.isValid() and item:
            self.setCurrentIndex(idx)


class GitFileTreeModel(QtGui.QStandardItemModel):
    """Presents a list of file paths as a hierarchical tree."""
    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.dir_entries = {'': self.invisibleRootItem()}
        self.dir_rows = {}

    def clear(self):
        QtGui.QStandardItemModel.clear(self)
        self.dir_rows = {}
        self.dir_entries = {'': self.invisibleRootItem()}

    def add_files(self, files):
        """Add a list of files"""
        add_file = self.add_file
        for f in files:
            add_file(f)

    def add_file(self, path):
        """Add a file to the model."""
        dirname = utils.dirname(path)
        dir_entries = self.dir_entries
        try:
            parent = dir_entries[dirname]
        except KeyError:
            parent = dir_entries[dirname] = self.create_dir_entry(dirname)

        row_items = self.create_row(path, False)
        parent.appendRow(row_items)

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""
        # Create model items
        row_items = self.create_row(path, True)

        # Insert directories before file paths
        try:
            row = self.dir_rows[parent]
        except KeyError:
            row = self.dir_rows[parent] = 0

        parent.insertRow(row, row_items)
        self.dir_rows[parent] += 1
        self.dir_entries[path] = row_items[0]

        return row_items[0]

    def create_row(self, path, is_dir):
        """Return a list of items representing a row."""
        return [GitTreeItem(path, is_dir)]

    def create_dir_entry(self, dirname):
        """
        Create a directory entry for the model.

        This ensures that directories are always listed before files.

        """
        entries = dirname.split('/')
        curdir = []
        parent = self.invisibleRootItem()
        curdir_append = curdir.append
        self_add_directory = self.add_directory
        dir_entries = self.dir_entries
        for entry in entries:
            curdir_append(entry)
            path = '/'.join(curdir)
            try:
                parent = dir_entries[path]
            except KeyError:
                grandparent = parent
                parent = self_add_directory(grandparent, path)
                dir_entries[path] = parent
        return parent


class GitTreeModel(GitFileTreeModel):
    def __init__(self, ref, parent):
        GitFileTreeModel.__init__(self, parent)
        self.ref = ref
        self._initialize()

    def _initialize(self):
        """Iterate over git-ls-tree and create GitTreeItems."""
        status, out, err = git.ls_tree('--full-tree', '-r', '-t', '-z',
                                       self.ref)
        if status != 0:
            Interaction.log_status(status, out, err)
            return

        if not out:
            return

        for line in out[:-1].split('\0'):
            # .....6 ...4 ......................................40
            # 040000 tree c127cde9a0c644a3a8fef449a244f47d5272dfa6	relative
            # 100644 blob 139e42bf4acaa4927ec9be1ec55a252b97d3f1e2	relative/path
            objtype = line[7]
            relpath = line[6 + 1 + 4 + 1 + 40 + 1:]
            if objtype == 't':
                parent = self.dir_entries[utils.dirname(relpath)]
                self.add_directory(parent, relpath)
            elif objtype == 'b':
                self.add_file(relpath)


class GitTreeItem(QtGui.QStandardItem):
    """
    Represents a cell in a treeview.

    Many GitRepoItems could map to a single repository path,
    but this tree only has a single column.
    Each GitRepoItem manages a different cell in the tree view.

    """
    def __init__(self, path, is_dir):
        QtGui.QStandardItem.__init__(self)
        self.is_dir = is_dir
        self.path = path
        self.setEditable(False)
        self.setDragEnabled(False)
        self.setText(utils.basename(path))
        if is_dir:
            self.setIcon(qtutils.dir_icon())
        else:
            self.setIcon(qtutils.file_icon())

########NEW FILE########
__FILENAME__ = cfgactions
from __future__ import division, absolute_import, unicode_literals

import os
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import gitcfg
from cola import gitcmds
from cola import qtutils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.qtutils import create_button
from cola.widgets import defs
from cola.widgets import completion
from cola.widgets import standard
from cola.compat import ustr


def install():
    Interaction.run_command = staticmethod(run_command)
    Interaction.confirm_config_action = staticmethod(confirm_config_action)


def get_config_actions():
    cfg = gitcfg.instance()
    return cfg.get_guitool_names()


def confirm_config_action(name, opts):
    dlg = ActionDialog(qtutils.active_window(), name, opts)
    dlg.show()
    if dlg.exec_() != QtGui.QDialog.Accepted:
        return False
    rev = ustr(dlg.revision())
    if rev:
        opts['revision'] = rev
    args = ustr(dlg.args())
    if args:
        opts['args'] = args
    return True


def run_command(title, command):
    """Show a command widget"""
    view = GitCommandWidget(title, qtutils.active_window())
    view.set_command(command)
    view.show()
    view.raise_()
    view.run()
    view.exec_()
    return (view.exitstatus, view.out, view.err)


class GitCommandWidget(standard.Dialog):
    """Nice TextView that reads the output of a command syncronously"""
    # Keep us in scope otherwise PyQt kills the widget
    def __init__(self, title, parent=None):
        standard.Dialog.__init__(self, parent)
        self.setWindowTitle(title)
        if parent is not None:
            self.setWindowModality(Qt.ApplicationModal)

        # Construct the process
        self.proc = QtCore.QProcess(self)
        self.exitstatus = 0
        self.out = ''
        self.err = ''

        self._layout = QtGui.QVBoxLayout(self)
        self._layout.setContentsMargins(3, 3, 3, 3)

        # Create the text browser
        self.output_text = QtGui.QTextBrowser(self)
        self.output_text.setAcceptDrops(False)
        self.output_text.setTabChangesFocus(True)
        self.output_text.setUndoRedoEnabled(False)
        self.output_text.setReadOnly(True)
        self.output_text.setAcceptRichText(False)

        self._layout.addWidget(self.output_text)

        # Create abort / close buttons
        self.button_abort = QtGui.QPushButton(self)
        self.button_abort.setText(N_('Abort'))
        self.button_close = QtGui.QPushButton(self)
        self.button_close.setText(N_('Close'))

        # Put them in a horizontal layout at the bottom.
        self.button_box = QtGui.QDialogButtonBox(self)
        self.button_box.addButton(self.button_abort, QtGui.QDialogButtonBox.RejectRole)
        self.button_box.addButton(self.button_close, QtGui.QDialogButtonBox.AcceptRole)
        self._layout.addWidget(self.button_box)

        # Connect the signals to the process
        self.connect(self.proc, SIGNAL('readyReadStandardOutput()'),
                self.read_stdout)
        self.connect(self.proc, SIGNAL('readyReadStandardError()'),
                self.read_stderr)
        self.connect(self.proc, SIGNAL('finished(int)'), self.finishProc)
        self.connect(self.proc, SIGNAL('stateChanged(QProcess::ProcessState)'), self.stateChanged)

        # Start with abort disabled - will be enabled when the process is run.
        self.button_abort.setEnabled(False)

        qtutils.connect_button(self.button_abort, self.abortProc)
        qtutils.connect_button(self.button_close, self.close)
        self.resize(720, 420)

    def set_command(self, command):
        self.command = command

    def run(self):
        """Runs the process"""
        self.proc.start(self.command[0], QtCore.QStringList(self.command[1:]))

    def read_stdout(self):
        rawbytes = self.proc.readAllStandardOutput()
        data = ''
        for b in rawbytes:
            data += b
        text = core.decode(data)
        self.out += text
        self.append_text(text)

    def read_stderr(self):
        rawbytes = self.proc.readAllStandardError()
        data = ''
        for b in rawbytes:
            data += b
        text = core.decode(data)
        self.err += text
        self.append_text(text)

    def append_text(self, text):
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(text)
        cursor.movePosition(cursor.End)
        self.output_text.setTextCursor(cursor)

    def abortProc(self):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # Terminate seems to do nothing in windows
            self.proc.terminate()
            # Kill the process.
            QtCore.QTimer.singleShot(1000, self.proc, QtCore.SLOT('kill()'))

    def closeEvent(self, event):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            # The process is still running, make sure we really want to abort.
            title = N_('Abort Action')
            msg = N_('An action is still running.\n'
                     'Terminating it could result in data loss.')
            info_text = N_('Abort the action?')
            ok_text = N_('Abort Action')
            if qtutils.confirm(title, msg, info_text, ok_text,
                               default=False, icon=qtutils.discard_icon()):
                self.abortProc()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

        return standard.Dialog.closeEvent(self, event)

    def stateChanged(self, newstate):
        # State of process has changed - change the abort button state.
        if newstate == QtCore.QProcess.NotRunning:
            self.button_abort.setEnabled(False)
        else:
            self.button_abort.setEnabled(True)

    def finishProc(self, status ):
        self.exitstatus = status


class ActionDialog(standard.Dialog):
    def __init__(self, parent, name, opts):
        standard.Dialog.__init__(self, parent)
        self.name = name
        self.opts = opts

        self.setWindowModality(Qt.ApplicationModal)

        self.layt = QtGui.QVBoxLayout()
        self.layt.setMargin(defs.margin)
        self.layt.setSpacing(defs.spacing)
        self.setLayout(self.layt)

        title = opts.get('title')
        if title:
            self.setWindowTitle(os.path.expandvars(title))

        self.prompt = QtGui.QLabel()

        prompt = opts.get('prompt')
        if prompt:
            self.prompt.setText(os.path.expandvars(prompt))
        self.layt.addWidget(self.prompt)


        self.argslabel = QtGui.QLabel()
        if 'argprompt' not in opts or opts.get('argprompt') is True:
            argprompt = N_('Arguments')
        else:
            argprompt = opts.get('argprompt')

        self.argslabel.setText(argprompt)

        self.argstxt = QtGui.QLineEdit()
        self.argslayt = QtGui.QHBoxLayout()
        self.argslayt.addWidget(self.argslabel)
        self.argslayt.addWidget(self.argstxt)
        self.layt.addLayout(self.argslayt)

        if not self.opts.get('argprompt'):
            self.argslabel.setMinimumSize(1, 1)
            self.argstxt.setMinimumSize(1, 1)
            self.argstxt.hide()
            self.argslabel.hide()

        revs = (
            (N_('Local Branch'), gitcmds.branch_list(remote=False)),
            (N_('Tracking Branch'), gitcmds.branch_list(remote=True)),
            (N_('Tag'), gitcmds.tag_list()),
        )

        if 'revprompt' not in opts or opts.get('revprompt') is True:
            revprompt = N_('Revision')
        else:
            revprompt = opts.get('revprompt')
        self.revselect = RevisionSelector(self, revs)
        self.revselect.set_revision_label(revprompt)
        self.layt.addWidget(self.revselect)

        if not opts.get('revprompt'):
            self.revselect.hide()

        # Close/Run buttons
        self.btnlayt = QtGui.QHBoxLayout()
        self.btnlayt.addStretch()
        self.closebtn = create_button(text=N_('Close'), layout=self.btnlayt)
        self.runbtn = create_button(text=N_('Run'), layout=self.btnlayt)
        self.runbtn.setDefault(True)
        self.layt.addLayout(self.btnlayt)

        # Widen the dialog by default
        self.resize(666, self.height())

        qtutils.connect_button(self.closebtn, self.reject)
        qtutils.connect_button(self.runbtn, self.accept)

    def revision(self):
        return self.revselect.revision()

    def args(self):
        return self.argstxt.text()


class RevisionSelector(QtGui.QWidget):
    def __init__(self, parent, revs):
        QtGui.QWidget.__init__(self, parent)

        self._revs = revs
        self._revdict = dict(revs)

        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(0)
        self.setLayout(self._layt)

        self._rev_layt = QtGui.QHBoxLayout()
        self._rev_layt.setMargin(0)

        self._rev_label = QtGui.QLabel()
        self._rev_layt.addWidget(self._rev_label)

        self._revision = completion.GitRefLineEdit()
        self._rev_layt.addWidget(self._revision)

        self._layt.addLayout(self._rev_layt)

        self._radio_layt = QtGui.QHBoxLayout()
        self._radio_btns = {}

        # Create the radio buttons
        for label, rev_list in self._revs:
            radio = QtGui.QRadioButton()
            radio.setText(label)
            radio.setObjectName(label)
            qtutils.connect_button(radio, self._set_revision_list)
            self._radio_layt.addWidget(radio)
            self._radio_btns[label] = radio

        self._radio_layt.addStretch()

        self._layt.addLayout(self._radio_layt)

        self._rev_list = QtGui.QListWidget()
        self._layt.addWidget(self._rev_list)

        label, rev_list = self._revs[0]
        self._radio_btns[label].setChecked(True)
        qtutils.set_items(self._rev_list, rev_list)

        self.connect(self._rev_list, SIGNAL('itemSelectionChanged()'),
                     self._rev_list_selection_changed)

    def revision(self):
        return self._revision.text()

    def set_revision_label(self, txt):
        self._rev_label.setText(txt)

    def _set_revision_list(self):
        sender = ustr(self.sender().objectName())
        revs = self._revdict[sender]
        qtutils.set_items(self._rev_list, revs)

    def _rev_list_selection_changed(self):
        items = self._rev_list.selectedItems()
        if not items:
            return
        self._revision.setText(items[0].text())

########NEW FILE########
__FILENAME__ = combodlg
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.widgets import standard
from cola.compat import ustr


class ComboDialog(standard.Dialog):
    """A dialog for choosing branches."""

    def __init__(self, parent=None, title='', items=None):
        standard.Dialog.__init__(self, parent=parent)

        self.setWindowTitle(title)
        self.resize(400, 73)
        self._main_layt = QtGui.QVBoxLayout(self)

        # Exposed
        self.items_widget = QtGui.QComboBox(self)
        self.items_widget.setEditable(True)

        self._main_layt.addWidget(self.items_widget)

        self.button_box = QtGui.QDialogButtonBox(self)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtGui.QDialogButtonBox.Ok |
                                           QtGui.QDialogButtonBox.Cancel)

        self._main_layt.addWidget(self.button_box)
        self.setTabOrder(self.items_widget, self.button_box)

        if items:
            self.items_widget.addItems(items)

        self.connect(self.button_box, SIGNAL('accepted()'), self.accept)
        self.connect(self.button_box, SIGNAL('rejected()'), self.reject)

    def idx(self):
        return self.items_widget.currentIndex()

    def value(self):
        return ustr(self.items_widget.currentText())

    def selected(self):
        """Present the dialog and return the chosen item."""
        geom = QtGui.QApplication.instance().desktop().screenGeometry()
        width = geom.width()
        height = geom.height()
        if self.parent():
            x = self.parent().x() + self.parent().width()//2 - self.width()//2
            y = self.parent().y() + self.parent().height()//3 - self.height()//2
            self.move(x, y)
        self.show()
        if self.exec_() == QtGui.QDialog.Accepted:
            return self.value()
        else:
            return None


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    combo = ComboDialog()
    combo.show()
    sys.exit(app.exec_())


########NEW FILE########
__FILENAME__ = commitmsg
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import gitcmds
from cola import gitcfg
from cola import textwrap
from cola.cmds import Interaction
from cola.gitcmds import commit_message_path
from cola.i18n import N_
from cola.models.dag import DAG
from cola.models.dag import RepoReader
from cola.models.prefs import tabwidth
from cola.models.prefs import textwidth
from cola.models.prefs import linebreak
from cola.qtutils import add_action
from cola.qtutils import confirm
from cola.qtutils import connect_action_bool
from cola.qtutils import connect_button
from cola.qtutils import create_toolbutton
from cola.qtutils import diff_font
from cola.qtutils import hide_button_menu_indicator
from cola.qtutils import options_icon
from cola.qtutils import save_icon
from cola.widgets import defs
from cola.widgets.selectcommits import select_commits
from cola.widgets.spellcheck import SpellCheckTextEdit
from cola.widgets.text import HintedLineEdit
from cola.compat import ustr


class CommitMessageEditor(QtGui.QWidget):
    def __init__(self, model, parent):
        QtGui.QWidget.__init__(self, parent)

        self.model = model
        self.notifying = False
        self.spellcheck_initialized = False

        self._linebreak = None
        self._textwidth = None
        self._tabwidth = None

        # Actions
        self.signoff_action = add_action(self, cmds.SignOff.name(),
                                         cmds.run(cmds.SignOff),
                                         cmds.SignOff.SHORTCUT)
        self.signoff_action.setToolTip(N_('Sign off on this commit'))

        self.commit_action = add_action(self,
                                        N_('Commit@@verb'),
                                        self.commit,
                                        cmds.Commit.SHORTCUT)
        self.commit_action.setToolTip(N_('Commit staged changes'))

        # Widgets
        self.summary = CommitSummaryLineEdit()
        self.summary.extra_actions.append(self.signoff_action)
        self.summary.extra_actions.append(self.commit_action)

        self.description = CommitMessageTextEdit()
        self.description.extra_actions.append(self.signoff_action)
        self.description.extra_actions.append(self.commit_action)

        commit_button_tooltip = N_('Commit staged changes\n'
                                   'Shortcut: Ctrl+Enter')
        self.commit_button = create_toolbutton(text=N_('Commit@@verb'),
                                               tooltip=commit_button_tooltip,
                                               icon=save_icon())

        self.actions_menu = QtGui.QMenu()
        self.actions_button = create_toolbutton(icon=options_icon(),
                                                tooltip=N_('Actions...'))
        self.actions_button.setMenu(self.actions_menu)
        self.actions_button.setPopupMode(QtGui.QToolButton.InstantPopup)
        hide_button_menu_indicator(self.actions_button)

        self.actions_menu.addAction(self.signoff_action)
        self.actions_menu.addAction(self.commit_action)
        self.actions_menu.addSeparator()

        # Amend checkbox
        self.amend_action = self.actions_menu.addAction(
                N_('Amend Last Commit'))
        self.amend_action.setCheckable(True)
        self.amend_action.setShortcut(cmds.AmendMode.SHORTCUT)
        self.amend_action.setShortcutContext(Qt.ApplicationShortcut)

        # Spell checker
        self.check_spelling_action = self.actions_menu.addAction(
                N_('Check Spelling'))
        self.check_spelling_action.setCheckable(True)
        self.check_spelling_action.setChecked(False)

        # Line wrapping
        self.autowrap_action = self.actions_menu.addAction(
                N_('Auto-Wrap Lines'))
        self.autowrap_action.setCheckable(True)
        self.autowrap_action.setChecked(linebreak())

        # Commit message
        self.actions_menu.addSeparator()
        self.load_commitmsg_menu = self.actions_menu.addMenu(
                N_('Load Previous Commit Message'))
        self.connect(self.load_commitmsg_menu, SIGNAL('aboutToShow()'),
                     self.build_commitmsg_menu)

        self.fixup_commit_menu = self.actions_menu.addMenu(
                N_('Fixup Previous Commit'))
        self.connect(self.fixup_commit_menu, SIGNAL('aboutToShow()'),
                     self.build_fixup_menu)

        self.toplayout = QtGui.QHBoxLayout()
        self.toplayout.setMargin(0)
        self.toplayout.setSpacing(defs.spacing)
        self.toplayout.addWidget(self.actions_button)
        self.toplayout.addWidget(self.summary)
        self.toplayout.addWidget(self.commit_button)

        self.mainlayout = QtGui.QVBoxLayout()
        self.mainlayout.setMargin(defs.margin)
        self.mainlayout.setSpacing(defs.spacing)
        self.mainlayout.addLayout(self.toplayout)
        self.mainlayout.addWidget(self.description)
        self.setLayout(self.mainlayout)

        connect_button(self.commit_button, self.commit)

        # Broadcast the amend mode
        connect_action_bool(self.amend_action, cmds.run(cmds.AmendMode))
        connect_action_bool(self.check_spelling_action,
                            self.toggle_check_spelling)

        # Handle the one-off autowrapping
        connect_action_bool(self.autowrap_action, self.set_linebreak)

        add_action(self.summary, N_('Move Down'), self.focus_description,
                Qt.Key_Down, Qt.Key_Return, Qt.Key_Enter)

        self.model.add_observer(self.model.message_commit_message_changed,
                                self.set_commit_message)

        self.connect(self.summary, SIGNAL('cursorPosition(int,int)'),
                     self.emit_position)

        self.connect(self.description, SIGNAL('cursorPosition(int,int)'),
                     # description starts at line 2
                     lambda row, col: self.emit_position(row + 2, col))

        # Keep model informed of changes
        self.connect(self.summary, SIGNAL('textChanged(QString)'),
                     self.commit_summary_changed)

        self.connect(self.description, SIGNAL('textChanged()'),
                     self.commit_message_changed)

        self.connect(self.description, SIGNAL('leave()'),
                     self.focus_summary)

        self.setFont(diff_font())

        self.summary.enable_hint(True)
        self.description.enable_hint(True)

        self.commit_button.setEnabled(False)
        self.commit_action.setEnabled(False)

        self.setFocusProxy(self.summary)

        self.set_tabwidth(tabwidth())
        self.set_textwidth(textwidth())
        self.set_linebreak(linebreak())

        # Loading message
        commit_msg = ''
        commit_msg_path = commit_message_path()
        if commit_msg_path:
            commit_msg = core.read(commit_msg_path)
        self.set_commit_message(commit_msg)

        # Allow tab to jump from the summary to the description
        self.setTabOrder(self.summary, self.description)

    def set_initial_size(self):
        self.setMaximumHeight(133)
        QtCore.QTimer.singleShot(1, self.restore_size)

    def restore_size(self):
        self.setMaximumHeight(2 ** 13)

    def focus_summary(self):
        self.summary.setFocus()

    def focus_description(self):
        self.description.setFocus()

    def commit_message(self, raw=True):
        """Return the commit message as a unicode string"""
        summary = self.summary.value()
        if raw:
            description = self.description.value()
        else:
            description = self.formatted_description()
        if summary and description:
            return summary + '\n\n' + description
        elif summary:
            return summary
        elif description:
            return '\n\n' + description
        else:
            return ''

    def formatted_description(self):
        text = self.description.value()
        if not self._linebreak:
            return text
        return textwrap.word_wrap(text, self._tabwidth, self._textwidth)

    def commit_summary_changed(self, value):
        """Respond to changes to the `summary` field

        Newlines can enter the `summary` field when pasting, which is
        undesirable.  Break the pasted value apart into the separate
        (summary, description) values and move the description over to the
        "extended description" field.

        """
        value = ustr(value)
        if '\n' in value:
            summary, description = value.split('\n', 1)
            description = description.lstrip('\n')
            cur_description = self.description.value()
            if cur_description:
                description = description + '\n' + cur_description
            # this callback is triggered by changing `summary`
            # so disable signals for `summary` only.
            self.summary.blockSignals(True)
            self.summary.set_value(summary)
            self.summary.blockSignals(False)
            self.description.set_value(description)
        self.commit_message_changed()

    def commit_message_changed(self, value=None):
        """Update the model when values change"""
        self.notifying = True
        message = self.commit_message()
        self.model.set_commitmsg(message)
        self.refresh_palettes()
        self.notifying = False
        self.update_actions()

    def update_actions(self):
        commit_enabled = bool(self.summary.value())
        self.commit_button.setEnabled(commit_enabled)
        self.commit_action.setEnabled(commit_enabled)

    def refresh_palettes(self):
        """Update the color palette for the hint text"""
        self.summary.refresh_palette()
        self.description.refresh_palette()

    def set_commit_message(self, message):
        """Set the commit message to match the observed model"""
        if self.notifying:
            # Calling self.model.set_commitmsg(message) causes us to
            # loop around so break the loop
            return

        # Parse the "summary" and "description" fields
        umsg = ustr(message)
        lines = umsg.splitlines()

        num_lines = len(lines)

        if num_lines == 0:
            # Message is empty
            summary = ''
            description = ''

        elif num_lines == 1:
            # Message has a summary only
            summary = lines[0]
            description = ''

        elif num_lines == 2:
            # Message has two lines; this is not a common case
            summary = lines[0]
            description = lines[1]

        else:
            # Summary and several description lines
            summary = lines[0]
            if lines[1]:
                # We usually skip this line but check just in case
                description_lines = lines[1:]
            else:
                description_lines = lines[2:]
            description = '\n'.join(description_lines)

        focus_summary = not summary
        focus_description = not description

        # Update summary
        if not summary and not self.summary.hasFocus():
            summary = self.summary.hint()

        blocksignals = self.summary.blockSignals(True)
        self.summary.setText(summary)
        self.summary.setCursorPosition(0)
        self.summary.blockSignals(blocksignals)

        # Update description
        if not description and not self.description.hasFocus():
            description = self.description.hint()

        blocksignals = self.description.blockSignals(True)
        self.description.setPlainText(description)
        self.description.blockSignals(blocksignals)

        # Update text color
        self.refresh_palettes()

        # Focus the empty summary or description
        if focus_summary:
            self.summary.setFocus()
            self.summary.emit_position()
        elif focus_description:
            self.description.setFocus()
            self.description.emit_position()
        else:
            self.summary.emit_position()

        self.update_actions()

    def set_tabwidth(self, width):
        self._tabwidth = width
        self.description.set_tabwidth(width)

    def set_textwidth(self, width):
        self._textwidth = width
        self.description.set_textwidth(width)

    def set_linebreak(self, brk):
        self._linebreak = brk
        self.description.set_linebreak(brk)
        blocksignals = self.autowrap_action.blockSignals(True)
        self.autowrap_action.setChecked(brk)
        self.autowrap_action.blockSignals(blocksignals)

    def setFont(self, font):
        """Pass the setFont() calls down to the text widgets"""
        self.summary.setFont(font)
        self.description.setFont(font)

    def set_mode(self, mode):
        can_amend = not self.model.is_merging
        checked = (mode == self.model.mode_amend)
        blocksignals = self.amend_action.blockSignals(True)
        self.amend_action.setEnabled(can_amend)
        self.amend_action.setChecked(checked)
        self.amend_action.blockSignals(blocksignals)

    def emit_position(self, row, col):
        self.emit(SIGNAL('cursorPosition(int,int)'), row, col)

    def commit(self):
        """Attempt to create a commit from the index and commit message."""
        if not bool(self.summary.value()):
            # Describe a good commit message
            error_msg = N_(''
                'Please supply a commit message.\n\n'
                'A good commit message has the following format:\n\n'
                '- First line: Describe in one sentence what you did.\n'
                '- Second line: Blank\n'
                '- Remaining lines: Describe why this change is good.\n')
            Interaction.log(error_msg)
            Interaction.information(N_('Missing Commit Message'), error_msg)
            return

        msg = self.commit_message(raw=False)

        if not self.model.staged:
            error_msg = N_(''
                'No changes to commit.\n\n'
                'You must stage at least 1 file before you can commit.')
            if self.model.modified:
                informative_text = N_('Would you like to stage and '
                                      'commit all modified files?')
                if not confirm(N_('Stage and commit?'),
                               error_msg,
                               informative_text,
                               N_('Stage and Commit'),
                               default=True,
                               icon=save_icon()):
                    return
            else:
                Interaction.information(N_('Nothing to commit'), error_msg)
                return
            cmds.do(cmds.StageModified)

        # Warn that amending published commits is generally bad
        amend = self.amend_action.isChecked()
        if (amend and self.model.is_commit_published() and
            not confirm(N_('Rewrite Published Commit?'),
                        N_('This commit has already been published.\n'
                           'This operation will rewrite published history.\n'
                           'You probably don\'t want to do this.'),
                        N_('Amend the published commit?'),
                        N_('Amend Commit'),
                        default=False, icon=save_icon())):
            return
        status, out, err = cmds.do(cmds.Commit, amend, msg)
        if status != 0:
            Interaction.critical(N_('Commit failed'),
                                 N_('"git commit" returned exit code %s') %
                                    (status,),
                                 out + err)

    def build_fixup_menu(self):
        self.build_commits_menu(cmds.LoadFixupMessage,
                                self.fixup_commit_menu,
                                self.choose_fixup_commit,
                                prefix='fixup! ')

    def build_commitmsg_menu(self):
        self.build_commits_menu(cmds.LoadCommitMessageFromSHA1,
                                self.load_commitmsg_menu,
                                self.choose_commit_message)

    def build_commits_menu(self, cmd, menu, chooser, prefix=''):
        dag = DAG('HEAD', 6)
        commits = RepoReader(dag)

        menu_commits = []
        for idx, c in enumerate(commits):
            menu_commits.insert(0, c)
            if idx > 5:
                continue

        menu.clear()
        for c in menu_commits:
            menu.addAction(prefix + c.summary, cmds.run(cmd, c.sha1))

        if len(commits) == 6:
            menu.addSeparator()
            menu.addAction(N_('More...'), chooser)


    def choose_commit(self, cmd):
        revs, summaries = gitcmds.log_helper()
        sha1s = select_commits(N_('Select Commit'), revs, summaries,
                               multiselect=False)
        if not sha1s:
            return
        sha1 = sha1s[0]
        cmds.do(cmd, sha1)

    def choose_commit_message(self):
        self.choose_commit(cmds.LoadCommitMessageFromSHA1)

    def choose_fixup_commit(self):
        self.choose_commit(cmds.LoadFixupMessage)

    def toggle_check_spelling(self, enabled):
        spellcheck = self.description.spellcheck

        if enabled and not self.spellcheck_initialized:
            # Add our name to the dictionary
            self.spellcheck_initialized = True
            cfg = gitcfg.instance()
            user_name = cfg.get('user.name')
            if user_name:
                for part in user_name.split():
                    spellcheck.add_word(part)

            # Add our email address to the dictionary
            user_email = cfg.get('user.email')
            if user_email:
                for part in user_email.split('@'):
                    for elt in part.split('.'):
                        spellcheck.add_word(elt)

            # git jargon
            spellcheck.add_word('Acked')
            spellcheck.add_word('Signed')
            spellcheck.add_word('Closes')
            spellcheck.add_word('Fixes')

        self.description.highlighter.enable(enabled)


class CommitSummaryLineEdit(HintedLineEdit):
    def __init__(self, parent=None):
        hint = N_('Commit summary')
        HintedLineEdit.__init__(self, hint, parent)
        self.extra_actions = []

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        if self.extra_actions:
            menu.addSeparator()
        for action in self.extra_actions:
            menu.addAction(action)
        menu.exec_(self.mapToGlobal(event.pos()))


class CommitMessageTextEdit(SpellCheckTextEdit):

    def __init__(self, parent=None):
        hint = N_('Extended description...')
        SpellCheckTextEdit.__init__(self, hint, parent)
        self.extra_actions = []

        self.action_emit_leave = add_action(self,
                'Shift Tab', self.emit_leave, 'Shift+tab')

    def contextMenuEvent(self, event):
        menu, spell_menu = self.context_menu()
        if self.extra_actions:
            menu.addSeparator()
        for action in self.extra_actions:
            menu.addAction(action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            position = cursor.position()
            if position == 0:
                # The cursor is at the beginning of the line.
                # If we have selection then simply reset the cursor.
                # Otherwise, emit a signal so that the parent can
                # change focus.
                if cursor.hasSelection():
                    cursor.setPosition(0)
                    self.setTextCursor(cursor)
                else:
                    self.emit_leave()
                event.accept()
                return
            text_before = ustr(self.toPlainText())[:position]
            lines_before = text_before.count('\n')
            if lines_before == 0:
                # If we're on the first line, but not at the
                # beginning, then move the cursor to the beginning
                # of the line.
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.setPosition(0, mode)
                self.setTextCursor(cursor)
                event.accept()
                return
        elif event.key() == Qt.Key_Down:
            cursor = self.textCursor()
            position = cursor.position()
            all_text = ustr(self.toPlainText())
            text_after = all_text[position:]
            lines_after = text_after.count('\n')
            if lines_after == 0:
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.setPosition(len(all_text), mode)
                self.setTextCursor(cursor)
                event.accept()
                return
        SpellCheckTextEdit.keyPressEvent(self, event)

    def emit_leave(self):
        self.emit(SIGNAL('leave()'))

    def setFont(self, font):
        SpellCheckTextEdit.setFont(self, font)
        fm = self.fontMetrics()
        self.setMinimumSize(QtCore.QSize(1, fm.height() * 2))

########NEW FILE########
__FILENAME__ = compare
"""Provides dialogs for comparing branches and commits."""
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola import difftool
from cola import gitcmds
from cola.i18n import N_
from cola.qtutils import connect_button
from cola.widgets import defs
from cola.widgets import standard
from cola.compat import ustr


class FileItem(QtGui.QTreeWidgetItem):
    def __init__(self, path, icon):
        QtGui.QTreeWidgetItem.__init__(self, [path])
        self.path = path
        self.setIcon(0, icon)


def compare_branches():
    """Launches a dialog for comparing a pair of branches"""
    view = CompareBranchesDialog(qtutils.active_window())
    view.show()
    return view


class CompareBranchesDialog(standard.Dialog):


    def __init__(self, parent):
        standard.Dialog.__init__(self, parent=parent)

        self.BRANCH_POINT = N_('*** Branch Point ***')
        self.SANDBOX = N_('*** Sandbox ***')
        self.LOCAL = N_('Local')

        self.remote_branches = gitcmds.branch_list(remote=True)
        self.local_branches = gitcmds.branch_list(remote=False)

        self.setWindowTitle(N_('Branch Diff Viewer'))
        self.resize(658, 350)

        self.main_layt = QtGui.QVBoxLayout(self)
        self.main_layt.setMargin(defs.margin)
        self.main_layt.setSpacing(defs.spacing)

        self.splitter = QtGui.QSplitter(self)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(defs.handle_width)

        self.top_widget = QtGui.QWidget(self.splitter)

        self.top_grid_layt = QtGui.QGridLayout(self.top_widget)
        self.top_grid_layt.setMargin(0)
        self.top_grid_layt.setSpacing(defs.spacing)

        self.left_combo = QtGui.QComboBox(self.top_widget)
        self.left_combo.addItem(N_('Local'))
        self.left_combo.addItem(N_('Remote'))
        self.left_combo.setCurrentIndex(0)
        self.top_grid_layt.addWidget(self.left_combo, 0, 0, 1, 1)

        self.right_combo = QtGui.QComboBox(self.top_widget)
        self.right_combo.addItem(N_('Local'))
        self.right_combo.addItem(N_('Remote'))
        self.right_combo.setCurrentIndex(1)
        self.top_grid_layt.addWidget(self.right_combo, 0, 1, 1, 1)

        self.left_list = QtGui.QListWidget(self.top_widget)
        self.top_grid_layt.addWidget(self.left_list, 1, 0, 1, 1)

        self.right_list = QtGui.QListWidget(self.top_widget)
        self.top_grid_layt.addWidget(self.right_list, 1, 1, 1, 1)

        self.bottom_widget = QtGui.QWidget(self.splitter)
        self.bottom_grid_layt = QtGui.QGridLayout(self.bottom_widget)
        self.bottom_grid_layt.setMargin(0)
        self.bottom_grid_layt.setSpacing(defs.button_spacing)

        self.button_spacer = QtGui.QSpacerItem(1, 1,
                                                QtGui.QSizePolicy.Expanding,
                                                QtGui.QSizePolicy.Minimum)
        self.bottom_grid_layt.addItem(self.button_spacer, 1, 1, 1, 1)

        self.button_compare = QtGui.QPushButton(self.bottom_widget)
        self.button_compare.setText(N_('Compare'))
        self.bottom_grid_layt.addWidget(self.button_compare, 1, 2, 1, 1)

        self.button_close = QtGui.QPushButton(self.bottom_widget)
        self.button_close.setText(N_('Close'))
        self.bottom_grid_layt.addWidget(self.button_close, 1, 3, 1, 1)

        self.diff_files = standard.TreeWidget(self.bottom_widget)
        self.diff_files.headerItem().setText(0, N_('File Differences'))

        self.bottom_grid_layt.addWidget(self.diff_files, 0, 0, 1, 4)
        self.main_layt.addWidget(self.splitter)

        connect_button(self.button_close, self.accept)
        connect_button(self.button_compare, self.compare)

        self.connect(self.diff_files,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self.compare)

        self.connect(self.left_combo,
                     SIGNAL('currentIndexChanged(int)'),
                     lambda x: self.update_combo_boxes(left=True))

        self.connect(self.right_combo,
                     SIGNAL('currentIndexChanged(int)'),
                     lambda x: self.update_combo_boxes(left=False))

        self.connect(self.left_list,
                     SIGNAL('itemSelectionChanged()'), self.update_diff_files)

        self.connect(self.right_list,
                     SIGNAL('itemSelectionChanged()'), self.update_diff_files)

        self.update_combo_boxes(left=True)
        self.update_combo_boxes(left=False)

        # Pre-select the 0th elements
        item = self.left_list.item(0)
        if item:
            self.left_list.setCurrentItem(item)
            self.left_list.setItemSelected(item, True)

        item = self.right_list.item(0)
        if item:
            self.right_list.setCurrentItem(item)
            self.right_list.setItemSelected(item, True)

    def selection(self):
        left_item = self.left_list.currentItem()
        if left_item and left_item.isSelected():
            left_item = ustr(left_item.text())
        else:
            left_item = None
        right_item = self.right_list.currentItem()
        if right_item and right_item.isSelected():
            right_item = ustr(right_item.text())
        else:
            right_item = None
        return (left_item, right_item)


    def update_diff_files(self, *rest):
        """Updates the list of files whenever the selection changes"""
        # Left and Right refer to the comparison pair (l,r)
        left_item, right_item = self.selection()
        if (not left_item or not right_item or
                left_item == right_item):
            self.set_diff_files([])
            return
        left_item = self.remote_ref(left_item)
        right_item = self.remote_ref(right_item)

        # If any of the selection includes sandbox then we
        # generate the same diff, regardless.  This means we don't
        # support reverse diffs against sandbox aka worktree.
        if self.SANDBOX in (left_item, right_item):
            self.use_sandbox = True
            if left_item == self.SANDBOX:
                self.diff_arg = (right_item,)
            else:
                self.diff_arg = (left_item,)
        else:
            self.diff_arg = (left_item, right_item)
            self.use_sandbox = False

        # start and end as in 'git diff start end'
        self.start = left_item
        self.end = right_item

        if len(self.diff_arg) == 1:
            files = gitcmds.diff_index_filenames(self.diff_arg[0])
        else:
            files = gitcmds.diff_filenames(*self.diff_arg)

        self.set_diff_files(files)

    def set_diff_files(self, files):
        mk = FileItem
        icon = qtutils.icon('script.png')
        self.diff_files.clear()
        self.diff_files.addTopLevelItems([mk(f, icon) for f in files])

    def remote_ref(self, branch):
        """Returns the remote ref for 'git diff [local] [remote]'
        """
        if branch == self.BRANCH_POINT:
            # Compare against the branch point so find the merge-base
            branch = gitcmds.current_branch()
            tracked_branch = gitcmds.tracked_branch()
            if tracked_branch:
                return gitcmds.merge_base(branch, tracked_branch)
            else:
                remote_branches = gitcmds.branch_list(remote=True)
                remote_branch = 'origin/%s' % branch
                if remote_branch in remote_branches:
                    return gitcmds.merge_base(branch, remote_branch)

                elif 'origin/master' in remote_branches:
                    return gitcmds.merge_base(branch, 'origin/master')
                else:
                    return 'HEAD'
        else:
            # Compare against the remote branch
            return branch


    def update_combo_boxes(self, left=False):
        """Update listwidgets from the combobox selection

        Update either the left or right listwidgets
        to reflect the available items.
        """
        if left:
            which = ustr(self.left_combo.currentText())
            widget = self.left_list
        else:
            which = ustr(self.right_combo.currentText())
            widget = self.right_list
        if not which:
            return
        # If we're looking at "local" stuff then provide the
        # sandbox as a valid choice.  If we're looking at
        # "remote" stuff then also include the branch point.
        if which == self.LOCAL:
            new_list = ([self.SANDBOX]+ self.local_branches)
        else:
            new_list = ([self.BRANCH_POINT] + self.remote_branches)

        widget.clear()
        widget.addItems(new_list)
        if new_list:
            item = widget.item(0)
            widget.setCurrentItem(item)
            widget.setItemSelected(item, True)

    def compare(self, *args):
        """Shows the diff for a specific file
        """
        tree_widget = self.diff_files
        item = tree_widget.currentItem()
        if item and item.isSelected():
            self.compare_file(item.path)

    def compare_file(self, filename):
        """Initiates the difftool session"""
        if self.use_sandbox:
            arg = self.diff_arg
        else:
            arg = (self.start, self.end)
        difftool.launch(arg + ('--', filename))

########NEW FILE########
__FILENAME__ = completion
from __future__ import division, absolute_import, unicode_literals

import re
import subprocess

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola.i18n import N_
from cola import qtutils
from cola import utils
from cola.models import main
from cola.widgets import defs
from cola.compat import ustr


class CompletionLineEdit(QtGui.QLineEdit):

    def __init__(self, model, parent=None):
        QtGui.QLineEdit.__init__(self, parent)

        self.setFont(qtutils.diff_font())
        # used to hide the completion popup after a drag-select
        self._drag = 0

        self._keys_to_ignore = set([Qt.Key_Enter, Qt.Key_Return,
                                    Qt.Key_Escape])

        completion_model = model(self)
        completer = Completer(completion_model, self)
        completer.setWidget(self)
        self._completer = completer

        self._delegate = HighlightDelegate(self)
        self.connect(self, SIGNAL('textChanged(QString)'),
                     self._text_changed)

        completer.popup().setItemDelegate(self._delegate)
        self.connect(self._completer, SIGNAL('activated(QString)'),
                     self._complete)

    def refresh(self):
        return self._completer.model().update()

    def popup(self):
        return self._completer.popup()

    def value(self):
        return ustr(self.text())

    def _is_case_sensitive(self, text):
        return bool([char for char in text if char.isupper()])

    def _text_changed(self, text):
        text = self._last_word()
        self._do_text_changed(text)

    def _do_text_changed(self, text):
        case_sensitive = self._is_case_sensitive(text)
        if case_sensitive:
            self._completer.setCaseSensitivity(Qt.CaseSensitive)
        else:
            self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._delegate.set_highlight_text(text, case_sensitive)
        self._completer.set_match_text(text, case_sensitive)

    def update_matches(self):
        text = self._last_word()
        case_sensitive = self._is_case_sensitive(text)
        self._completer.model().update_matches(case_sensitive)

    def _complete(self, completion):
        """
        This is the event handler for the QCompleter.activated(QString) signal,
        it is called when the user selects an item in the completer popup.
        """
        completion = ustr(completion)
        if not completion:
            self._do_text_changed('')
            return
        words = self._words()
        if words and not self._ends_with_whitespace():
            words.pop()

        words.append(completion)
        text = subprocess.list2cmdline(words)
        self.setText(text)
        self.emit(SIGNAL('changed()'))
        self._do_text_changed('')

    def _words(self):
        return utils.shell_split(ustr(self.text()))

    def _ends_with_whitespace(self):
        text = ustr(self.text())
        return text.rstrip() != text

    def _last_word(self):
        if self._ends_with_whitespace():
            return ''
        words = self._words()
        if not words:
            return ustr(self.text())
        if not words[-1]:
            return ''
        return words[-1]

    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if (event.key() == Qt.Key_Tab and
                    self.popup().isVisible()):
                event.ignore()
                return True
            if (event.key() in (Qt.Key_Return, Qt.Key_Enter) and
                    not self.popup().isVisible()):
                self.emit(SIGNAL('returnPressed()'))
                event.accept()
                return True
        if event.type() == QtCore.QEvent.Hide:
            self.close_popup()
        return QtGui.QLineEdit.event(self, event)

    def do_completion(self):
        self._completer.popup().setCurrentIndex(
                self._completer.model().index(0,0))
        self._completer.complete()

    def keyPressEvent(self, event):
        if self._completer.popup().isVisible():
            if event.key() in self._keys_to_ignore:
                event.ignore()
                self._complete(self._last_word())
                return

        elif (event.key() == Qt.Key_Down and
              self._completer.completionCount() > 0):
            event.accept()
            self.do_completion()
            return

        QtGui.QLineEdit.keyPressEvent(self, event)

        prefix = self._last_word()
        if prefix != ustr(self._completer.completionPrefix()):
            self._update_popup_items(prefix)

        if len(event.text()) > 0 and len(prefix) > 0:
            self._completer.complete()

    #: _drag: 0 - unclicked, 1 - clicked, 2 - dragged
    def mousePressEvent(self, event):
        self._drag = 1
        return QtGui.QLineEdit.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self._drag == 1:
            self._drag = 2
        return QtGui.QLineEdit.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self._drag != 2 and event.button() != Qt.RightButton:
            self.do_completion()
        self._drag = 0
        return QtGui.QLineEdit.mouseReleaseEvent(self, event)

    def close_popup(self):
        if self.popup().isVisible():
            self.popup().close()

    def _update_popup_items(self, prefix):
        """
        Filters the completer's popup items to only show items
        with the given prefix.
        """
        self._completer.setCompletionPrefix(prefix)
        self._completer.popup().setCurrentIndex(
                self._completer.model().index(0,0))

    def __del__(self):
        self.dispose()

    def dispose(self):
        self._completer.dispose()


class GatherCompletionsThread(QtCore.QThread):
    def __init__(self, model):
        QtCore.QThread.__init__(self)
        self.model = model
        self.case_sensitive = False

    def run(self):
        text = None
        # Loop when the matched text changes between the start and end time.
        # This happens when gather_matches() takes too long and the
        # model's matched_text changes in-between.
        while text != self.model.matched_text:
            text = self.model.matched_text
            items = self.model.gather_matches(self.case_sensitive)

        if text is not None:
            self.emit(SIGNAL('items_gathered'), items)


class HighlightDelegate(QtGui.QStyledItemDelegate):
    """A delegate used for auto-completion to give formatted completion"""
    def __init__(self, parent=None): # model, parent=None):
        QtGui.QStyledItemDelegate.__init__(self, parent)
        self.highlight_text = ''
        self.case_sensitive = False

        self.doc = QtGui.QTextDocument()
        try:
            self.doc.setDocumentMargin(0)
        except: # older PyQt4
            pass

    def set_highlight_text(self, text, case_sensitive):
        """Sets the text that will be made bold in the term name when displayed"""
        self.highlight_text = text
        self.case_sensitive = case_sensitive

    def paint(self, painter, option, index):
        """Overloaded Qt method for custom painting of a model index"""
        if not self.highlight_text:
            return QtGui.QStyledItemDelegate.paint(self, painter, option, index)

        text = ustr(index.data().toPyObject())
        if self.case_sensitive:
            html = text.replace(self.highlight_text,
                                '<strong>%s</strong>' % self.highlight_text)
        else:
            match = re.match(r'(.*)(%s)(.*)' % re.escape(self.highlight_text),
                             text, re.IGNORECASE)
            if match:
                start = match.group(1) or ''
                middle = match.group(2) or ''
                end = match.group(3) or ''
                html = (start + ('<strong>%s</strong>' % middle) + end)
            else:
                html = text
        self.doc.setHtml(html)

        # Painting item without text, Text Document will paint the text
        optionV4 = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(optionV4, index)
        optionV4.text = QtCore.QString()

        style = QtGui.QApplication.style()
        style.drawControl(QtGui.QStyle.CE_ItemViewItem, optionV4, painter)
        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        # Highlighting text if item is selected
        if (optionV4.state & QtGui.QStyle.State_Selected):
            color = optionV4.palette.color(QtGui.QPalette.Active,
                                           QtGui.QPalette.HighlightedText)
            ctx.palette.setColor(QtGui.QPalette.Text, color)

        # translate the painter to where the text is drawn
        rect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, optionV4)
        painter.save()

        start = rect.topLeft() + QtCore.QPoint(3, 0)
        painter.translate(start)

        # tell the text document to draw the html for us
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()


class CompletionModel(QtGui.QStandardItemModel):

    def __init__(self, parent):
        QtGui.QStandardItemModel.__init__(self, parent)
        self.matched_text = ''
        self.case_sensitive = False

        self.update_thread = GatherCompletionsThread(self)
        self.connect(self.update_thread, SIGNAL('items_gathered'),
                     self.apply_matches)

    def lower_completion_key(self, x):
        return x.replace('.','').lower()

    def completion_key(self, x):
        return x.replace('.','')

    def update(self):
        case_sensitive = self.update_thread.case_sensitive
        self.update_matches(case_sensitive)

    def set_match_text(self, matched_text, case_sensitive):
        self.matched_text = matched_text
        self.update_matches(case_sensitive)

    def update_matches(self, case_sensitive):
        self.case_sensitive = case_sensitive
        self.update_thread.case_sensitive = case_sensitive
        if not self.update_thread.isRunning():
            self.update_thread.start()

    def gather_matches(self, case_sensitive):
        return ((), (), set())

    def apply_matches(self, match_tuple):
        self.match_tuple = match_tuple
        matched_refs, matched_paths, dirs = match_tuple
        QStandardItem = QtGui.QStandardItem
        file_icon = qtutils.file_icon()
        dir_icon = qtutils.dir_icon()
        git_icon = qtutils.git_icon()

        matched_text = self.matched_text
        items = []
        for ref in matched_refs:
            item = QStandardItem()
            item.setText(ref)
            item.setIcon(git_icon)
            items.append(item)

        if matched_paths and (not matched_text or matched_text in '--'):
            item = QStandardItem()
            item.setText('--')
            item.setIcon(file_icon)
            items.append(item)

        for match in matched_paths:
            item = QStandardItem()
            item.setText(match)
            if match in dirs:
                item.setIcon(dir_icon)
            else:
                item.setIcon(file_icon)
            items.append(item)

        self.clear()
        self.invisibleRootItem().appendRows(items)


class Completer(QtGui.QCompleter):

    def __init__(self, model, parent):
        QtGui.QCompleter.__init__(self, parent)
        self._model = model
        self.setCompletionMode(QtGui.QCompleter.UnfilteredPopupCompletion)
        self.setCaseSensitivity(Qt.CaseInsensitive)

        self.connect(model, SIGNAL('update()'), self.update)
        self.setModel(model)

    def update(self):
        self._model.update()

    def dispose(self):
        self._model.dispose()

    def set_match_text(self, matched_text, case_sensitive):
        self._model.set_match_text(matched_text, case_sensitive)


class GitCompletionModel(CompletionModel):

    def __init__(self, parent):
        CompletionModel.__init__(self, parent)
        self.main_model = model = main.model()
        msg = model.message_updated
        model.add_observer(msg, self.emit_update)

    def gather_matches(self, case_sensitive):
        if case_sensitive:
            transform = lambda x: x
            keyfunc = self.completion_key
        else:
            transform = lambda x: x.lower()
            keyfunc = self.lower_completion_key

        matched_text = self.matched_text
        if matched_text:
            matched_refs = [r for r in self.matches()
                            if transform(matched_text) in transform(r)]
            # if we match nothing, still offer to complete something
            if not matched_refs:
                matched_refs = self.matches()
        else:
            matched_refs = self.matches()

        matched_refs.sort(key=keyfunc)
        return (matched_refs, (), set())

    def emit_update(self):
        self.emit(SIGNAL('update()'))

    def matches(self):
        return []

    def dispose(self):
        self.main_model.remove_observer(self.emit_update)


class GitRefCompletionModel(GitCompletionModel):
    """Completer for branches and tags"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.local_branches + model.remote_branches + model.tags


class GitBranchCompletionModel(GitCompletionModel):
    """Completer for remote branches"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.local_branches


class GitRemoteBranchCompletionModel(GitCompletionModel):
    """Completer for remote branches"""

    def __init__(self, parent):
        GitCompletionModel.__init__(self, parent)

    def matches(self):
        model = self.main_model
        return model.remote_branches


class GitLogCompletionModel(GitRefCompletionModel):
    """Completer for arguments suitable for git-log like commands"""

    def __init__(self, parent):
        GitRefCompletionModel.__init__(self, parent)

    def gather_matches(self, case_sensitive):
        (matched_refs, dummy_paths, dummy_dirs) =\
                GitRefCompletionModel.gather_matches(self, case_sensitive)

        file_list = self.main_model.everything()
        files = set(file_list)
        files_and_dirs = utils.add_parents(set(files))

        if case_sensitive:
            transform = lambda x: x
            keyfunc = self.completion_key
        else:
            transform = lambda x: x.lower()
            keyfunc = self.lower_completion_key

        dirs = files_and_dirs.difference(files)
        matched_text = self.matched_text
        if matched_text:
            matched_paths = [f for f in files_and_dirs
                             if transform(matched_text) in transform(f)]
        else:
            matched_paths = list(files_and_dirs)

        matched_paths.sort(key=keyfunc)

        return (matched_refs, matched_paths, dirs)


def bind_lineedit(model):
    """Create a line edit bound against a specific model"""

    class BoundLineEdit(CompletionLineEdit):

        def __init__(self, parent=None):
            CompletionLineEdit.__init__(self, model, parent)

    return BoundLineEdit

# Concrete classes
GitLogLineEdit = bind_lineedit(GitLogCompletionModel)
GitRefLineEdit = bind_lineedit(GitRefCompletionModel)
GitBranchLineEdit = bind_lineedit(GitBranchCompletionModel)
GitRemoteBranchLineEdit = bind_lineedit(GitRemoteBranchCompletionModel)


class GitDialog(QtGui.QDialog):

    def __init__(self, lineedit, title, button_text, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(333)

        self.label = QtGui.QLabel()
        self.label.setText(title)

        self.lineedit = lineedit(self)
        self.setFocusProxy(self.lineedit)

        self.ok_button = QtGui.QPushButton()
        self.ok_button.setText(button_text)
        self.ok_button.setIcon(qtutils.apply_icon())

        self.close_button = QtGui.QPushButton()
        self.close_button.setText(N_('Close'))

        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.setMargin(defs.no_margin)
        self.button_layout.setSpacing(defs.button_spacing)
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.close_button)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.spacing)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.lineedit)
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.ok_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        self.connect(self.lineedit, SIGNAL('textChanged(const QString&)'),
                     self.text_changed)
        self.connect(self.lineedit, SIGNAL('returnPressed()'), self.accept)

        self.setWindowModality(Qt.WindowModal)
        self.ok_button.setEnabled(False)

    def text(self):
        return ustr(self.lineedit.text())

    def text_changed(self, txt):
        self.ok_button.setEnabled(bool(self.text()))

    def set_text(self, ref):
        self.lineedit.setText(ref)

    @classmethod
    def get(cls, title, button_text, parent, default=None):
        dlg = cls(title, button_text, parent)
        if default:
            dlg.set_text(default)

        dlg.show()
        dlg.raise_()

        def show_popup():
            x = dlg.lineedit.x()
            y = dlg.lineedit.y() + dlg.lineedit.height()
            point = QtCore.QPoint(x, y)
            mapped = dlg.mapToGlobal(point)
            dlg.lineedit.popup().move(mapped.x(), mapped.y())
            dlg.lineedit.popup().show()
            dlg.lineedit.refresh()

        QtCore.QTimer().singleShot(0, show_popup)

        if dlg.exec_() == cls.Accepted:
            return dlg.text()
        else:
            return None


class GitRefDialog(GitDialog):

    def __init__(self, title, button_text, parent):
        GitDialog.__init__(self, GitRefLineEdit,
                           title, button_text, parent)


class GitBranchDialog(GitDialog):

    def __init__(self, title, button_text, parent):
        GitDialog.__init__(self, GitBranchLineEdit,
                           title, button_text, parent)


class GitRemoteBranchDialog(GitDialog):

    def __init__(self, title, button_text, parent):
        GitDialog.__init__(self, GitRemoteBranchLineEdit,
                           title, button_text, parent)

########NEW FILE########
__FILENAME__ = createbranch
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.widgets import defs
from cola.widgets import completion
from cola.widgets.standard import Dialog
from cola.compat import ustr


def create_new_branch(revision=''):
    """Launches a dialog for creating a new branch"""
    model = main.MainModel()
    model.update_status()
    view = CreateBranchDialog(model, qtutils.active_window())
    if revision:
        view.set_revision(revision)
    view.show()
    return view


class CreateOpts(object):
    def __init__(self, model):
        self.model = model
        self.reset = False
        self.track = False
        self.fetch = True
        self.checkout = True
        self.revision = 'HEAD'
        self.branch = ''


class CreateThread(QtCore.QThread):
    def __init__(self, opts, parent):
        QtCore.QThread.__init__(self, parent)
        self.opts = opts

    def run(self):
        branch = self.opts.branch
        revision = self.opts.revision
        reset = self.opts.reset
        checkout = self.opts.checkout
        track = self.opts.track
        model = self.opts.model
        results = []
        status = 0

        if track and '/' in revision:
            remote = revision.split('/', 1)[0]
            status, out, err = model.git.fetch(remote)
            self.emit(SIGNAL('command'), status, out, err)
            results.append(('fetch', status, out, err))

        if status == 0:
            status, out, err = model.create_branch(branch, revision,
                                                   force=reset,
                                                   track=track)
            self.emit(SIGNAL('command'), status, out, err)

        results.append(('branch', status, out, err))
        if status == 0 and checkout:
            status, out, err = model.git.checkout(branch)
            self.emit(SIGNAL('command'), status, out, err)
            results.append(('checkout', status, out, err))

        main.model().update_status()
        self.emit(SIGNAL('done'), results)


class CreateBranchDialog(Dialog):
    """A dialog for creating branches."""

    def __init__(self, model, parent=None):
        Dialog.__init__(self, parent=parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Create Branch'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.model = model
        self.opts = CreateOpts(model)
        self.thread = CreateThread(self.opts, self)

        self.progress = QtGui.QProgressDialog(self)
        self.progress.setRange(0, 0)
        self.progress.setCancelButton(None)
        self.progress.setWindowTitle(N_('Create Branch'))
        self.progress.setWindowModality(Qt.WindowModal)

        self.branch_name_label = QtGui.QLabel()
        self.branch_name_label.setText(N_('Branch Name'))

        self.branch_name = QtGui.QLineEdit()

        self.rev_label = QtGui.QLabel()
        self.rev_label.setText(N_('Starting Revision'))

        self.revision = completion.GitRefLineEdit()
        current = gitcmds.current_branch()
        if current:
            self.revision.setText(current)

        self.local_radio = QtGui.QRadioButton()
        self.local_radio.setText(N_('Local branch'))
        self.local_radio.setChecked(True)

        self.remote_radio = QtGui.QRadioButton()
        self.remote_radio.setText(N_('Tracking branch'))

        self.tag_radio = QtGui.QRadioButton()
        self.tag_radio.setText(N_('Tag'))

        self.branch_list = QtGui.QListWidget()

        self.update_existing_label = QtGui.QLabel()
        self.update_existing_label.setText(N_('Update Existing Branch:'))

        self.no_update_radio = QtGui.QRadioButton()
        self.no_update_radio.setText(N_('No'))

        self.ffwd_only_radio = QtGui.QRadioButton()
        self.ffwd_only_radio.setText(N_('Fast Forward Only'))
        self.ffwd_only_radio.setChecked(True)

        self.reset_radio = QtGui.QRadioButton()
        self.reset_radio.setText(N_('Reset'))

        self.options_bottom_layout = QtGui.QHBoxLayout()
        self.options_checkbox_layout = QtGui.QVBoxLayout()

        self.fetch_checkbox = QtGui.QCheckBox()
        self.fetch_checkbox.setText(N_('Fetch Tracking Branch'))
        self.fetch_checkbox.setChecked(True)
        self.options_checkbox_layout.addWidget(self.fetch_checkbox)

        self.checkout_checkbox = QtGui.QCheckBox()
        self.checkout_checkbox.setText(N_('Checkout After Creation'))
        self.checkout_checkbox.setChecked(True)
        self.options_checkbox_layout.addWidget(self.checkout_checkbox)

        self.options_bottom_layout.addLayout(self.options_checkbox_layout)
        self.options_bottom_layout.addStretch()

        self.create_button = qtutils.create_button(text=N_('Create Branch'),
                                                   icon=qtutils.git_icon())
        self.create_button.setDefault(True)

        self.close_button = qtutils.create_button(text=N_('Close'))

        self.branch_name_layout = QtGui.QHBoxLayout()
        self.branch_name_layout.addWidget(self.branch_name_label)
        self.branch_name_layout.addWidget(self.branch_name)

        self.rev_start_radiobtn_layout = QtGui.QHBoxLayout()
        self.rev_start_radiobtn_layout.addWidget(self.local_radio)
        self.rev_start_radiobtn_layout.addWidget(self.remote_radio)
        self.rev_start_radiobtn_layout.addWidget(self.tag_radio)
        self.rev_start_radiobtn_layout.addStretch()

        self.rev_start_textinput_layout = QtGui.QHBoxLayout()
        self.rev_start_textinput_layout.setMargin(0)
        self.rev_start_textinput_layout.setSpacing(defs.spacing)
        self.rev_start_textinput_layout.addWidget(self.rev_label)
        self.rev_start_textinput_layout.addWidget(self.revision)

        self.rev_start_group = QtGui.QGroupBox()
        self.rev_start_group.setTitle(N_('Starting Revision'))

        self.rev_start_layout = QtGui.QVBoxLayout(self.rev_start_group)
        self.rev_start_layout.setMargin(defs.margin)
        self.rev_start_layout.setSpacing(defs.spacing)
        self.rev_start_layout.addLayout(self.rev_start_radiobtn_layout)
        self.rev_start_layout.addWidget(self.branch_list)
        self.rev_start_layout.addLayout(self.rev_start_textinput_layout)

        self.options_radio_layout = QtGui.QHBoxLayout()
        self.options_radio_layout.addWidget(self.update_existing_label)
        self.options_radio_layout.addWidget(self.no_update_radio)
        self.options_radio_layout.addWidget(self.ffwd_only_radio)
        self.options_radio_layout.addWidget(self.reset_radio)

        self.option_group = QtGui.QGroupBox()
        self.option_group.setTitle(N_('Options'))

        self.options_grp_layout = QtGui.QVBoxLayout(self.option_group)
        self.options_grp_layout.setMargin(defs.margin)
        self.options_grp_layout.setSpacing(defs.spacing)
        self.options_grp_layout.addLayout(self.options_radio_layout)
        self.options_grp_layout.addLayout(self.options_bottom_layout)

        self.buttons_layout = QtGui.QHBoxLayout()
        self.buttons_layout.setMargin(defs.margin)
        self.buttons_layout.setSpacing(defs.spacing)
        self.buttons_layout.addWidget(self.create_button)
        self.buttons_layout.addWidget(self.close_button)

        self.options_section_layout = QtGui.QHBoxLayout()
        self.options_section_layout.setMargin(defs.margin)
        self.options_section_layout.setSpacing(defs.spacing)
        self.options_section_layout.addWidget(self.option_group)
        self.options_section_layout.addLayout(self.buttons_layout)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addLayout(self.branch_name_layout)
        self.main_layout.addWidget(self.rev_start_group)
        self.main_layout.addLayout(self.options_section_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.close_button, self.reject)
        qtutils.connect_button(self.create_button, self.create_branch)
        qtutils.connect_button(self.local_radio, self.display_model)
        qtutils.connect_button(self.remote_radio, self.display_model)
        qtutils.connect_button(self.tag_radio, self.display_model)

        self.connect(self.branch_list, SIGNAL('itemSelectionChanged()'),
                     self.branch_item_changed)

        self.connect(self.thread, SIGNAL('command'), self.thread_command)
        self.connect(self.thread, SIGNAL('done'), self.thread_done)

        self.resize(555, 333)
        self.display_model()

    def set_revision(self, revision):
        self.revision.setText(revision)

    def getopts(self):
        self.opts.revision = self.revision.value()
        self.opts.branch = ustr(self.branch_name.text())
        self.opts.checkout = self.checkout_checkbox.isChecked()
        self.opts.reset = self.reset_radio.isChecked()
        self.opts.fetch = self.fetch_checkbox.isChecked()
        self.opts.track = self.remote_radio.isChecked()

    def create_branch(self):
        """Creates a branch; called by the "Create Branch" button"""
        self.getopts()
        revision = self.opts.revision
        branch = self.opts.branch
        no_update = self.no_update_radio.isChecked()
        ffwd_only = self.ffwd_only_radio.isChecked()
        existing_branches = gitcmds.branch_list()
        check_branch = False

        if not branch or not revision:
            qtutils.critical(N_('Missing Data'),
                             N_('Please provide both a branch '
                                'name and revision expression.'))
            return
        if branch in existing_branches:
            if no_update:
                msg = N_('Branch "%s" already exists.') % branch
                qtutils.critical(N_('Branch Exists'), msg)
                return
            # Whether we should prompt the user for lost commits
            commits = gitcmds.rev_list_range(revision, branch)
            check_branch = bool(commits)

        if check_branch:
            msg = (N_('Resetting "%(branch)s" to "%(revision)s" '
                      'will lose commits.') %
                   dict(branch=branch, revision=revision))
            if ffwd_only:
                qtutils.critical(N_('Branch Exists'), msg)
                return
            lines = [msg]
            for idx, commit in enumerate(commits):
                subject = commit[1][0:min(len(commit[1]),16)]
                if len(subject) < len(commit[1]):
                    subject += '...'
                lines.append('\t' + commit[0][:8]
                        +'\t' + subject)
                if idx >= 5:
                    skip = len(commits) - 5
                    lines.append('\t(%s)' % (N_('%d skipped') % skip))
                    break
            line = N_('Recovering lost commits may not be easy.')
            lines.append(line)
            if not qtutils.confirm(N_('Reset Branch?'),
                                   '\n'.join(lines),
                                   (N_('Reset "%(branch)s" to "%(revision)s"?') %
                                    dict(branch=branch, revision=revision)),
                                   N_('Reset Branch'),
                                   default=False,
                                   icon=qtutils.icon('undo.svg')):
                return
        self.setEnabled(False)
        self.progress.setEnabled(True)
        QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)

        # Show a nice progress bar
        self.progress.setLabelText(N_('Updating...'))
        self.progress.show()
        self.thread.start()

    def thread_command(self, status, out, err):
        Interaction.log_status(status, out, err)

    def thread_done(self, results):
        self.setEnabled(True)
        self.progress.close()
        QtGui.QApplication.restoreOverrideCursor()

        for (cmd, status, out, err) in results:
            if status != 0:
                Interaction.critical(
                        N_('Error Creating Branch'),
                        (N_('"%(command)s" returned exit status "%(status)d"') %
                         dict(command='git '+cmd, status=status)))
                return

        self.accept()

    def branch_item_changed(self, *rest):
        """This callback is called when the branch selection changes"""
        # When the branch selection changes then we should update
        # the "Revision Expression" accordingly.
        qlist = self.branch_list
        (row, selected) = qtutils.selected_row(qlist)
        if not selected:
            return
        # Update the model with the selection
        sources = self.branch_sources()
        rev = sources[row]
        self.revision.setText(rev)

        # Set the branch field if we're branching from a remote branch.
        if not self.remote_radio.isChecked():
            return
        branch = utils.basename(rev)
        if branch == 'HEAD':
            return
        # Signal that we've clicked on a remote branch
        self.branch_name.setText(branch)

    def display_model(self):
        """Sets the branch list to the available branches
        """
        branches = self.branch_sources()
        qtutils.set_items(self.branch_list, branches)

    def branch_sources(self):
        """Get the list of items for populating the branch root list.
        """
        if self.local_radio.isChecked():
            return self.model.local_branches
        elif self.remote_radio.isChecked():
            return self.model.remote_branches
        elif self.tag_radio.isChecked():
            return self.model.tags

########NEW FILE########
__FILENAME__ = createtag
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt

from cola import cmds
from cola import qtutils
from cola.i18n import N_
from cola.qtutils import connect_button
from cola.qtutils import critical
from cola.qtutils import information
from cola.widgets import completion
from cola.widgets import standard
from cola.widgets import text


def new_create_tag(name='', ref='', sign=False, parent=None):
    """Entry point for external callers."""
    opts = TagOptions(name, ref, sign)
    view = CreateTag(opts, parent=parent)
    return view


def create_tag(name='', ref='', sign=False):
    """Entry point for external callers."""
    view = new_create_tag(name=name, ref=ref, sign=sign,
                          parent=qtutils.active_window())
    view.show()
    view.raise_()
    return view



class TagOptions(object):
    """Simple data container for the CreateTag dialog."""

    def __init__(self, name, ref, sign):
        self.name = name or ''
        self.ref = ref or 'HEAD'
        self.sign = sign


class CreateTag(standard.Dialog):

    def __init__(self, opts, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Create Tag'))
        if parent is not None:
            self.setWindowModality(QtCore.Qt.WindowModal)

        self.opts = opts

        self.main_layt = QtGui.QVBoxLayout(self)
        self.main_layt.setContentsMargins(6, 12, 6, 6)

        # Form layout for inputs
        self.input_form_layt = QtGui.QFormLayout()
        self.input_form_layt.setFieldGrowthPolicy(QtGui.QFormLayout.ExpandingFieldsGrow)

        # Tag label
        self.tag_name_label = QtGui.QLabel(self)
        self.tag_name_label.setText(N_('Name'))
        self.input_form_layt.setWidget(0, QtGui.QFormLayout.LabelRole,
                                       self.tag_name_label)

        self.tag_name = text.HintedLineEdit(N_('vX.Y.Z'), self)
        self.tag_name.set_value(opts.name)
        self.tag_name.setToolTip(N_('Specifies the tag name'))
        self.input_form_layt.setWidget(0, QtGui.QFormLayout.FieldRole,
                                       self.tag_name)

        # Sign Tag
        self.sign_label = QtGui.QLabel(self)
        self.sign_label.setText(N_('Sign Tag'))
        self.input_form_layt.setWidget(1, QtGui.QFormLayout.LabelRole,
                                       self.sign_label)

        self.sign_tag = QtGui.QCheckBox(self)
        self.sign_tag.setChecked(opts.sign)
        self.sign_tag.setToolTip(N_('Whether to sign the tag (git tag -s)'))
        self.input_form_layt.setWidget(1, QtGui.QFormLayout.FieldRole,
                                       self.sign_tag)
        self.main_layt.addLayout(self.input_form_layt)

        # Tag message
        self.tag_msg_label = QtGui.QLabel(self)
        self.tag_msg_label.setText(N_('Message'))
        self.input_form_layt.setWidget(2, QtGui.QFormLayout.LabelRole,
                                       self.tag_msg_label)

        self.tag_msg = text.HintedTextEdit(N_('Tag message...'), self)
        self.tag_msg.setToolTip(N_('Specifies the tag message'))
        self.tag_msg.enable_hint(True)
        self.input_form_layt.setWidget(2, QtGui.QFormLayout.FieldRole,
                                       self.tag_msg)
        # Revision
        self.rev_label = QtGui.QLabel(self)
        self.rev_label.setText(N_('Revision'))
        self.input_form_layt.setWidget(3, QtGui.QFormLayout.LabelRole,
                                       self.rev_label)

        self.revision = completion.GitRefLineEdit()
        self.revision.setText(self.opts.ref)
        self.revision.setToolTip(N_('Specifies the SHA-1 to tag'))
        self.input_form_layt.setWidget(3, QtGui.QFormLayout.FieldRole,
                                       self.revision)

        # Buttons
        self.button_hbox_layt = QtGui.QHBoxLayout()
        self.button_hbox_layt.addStretch()

        self.create_button = qtutils.create_button(text=N_('Create Tag'),
                                                   icon=qtutils.git_icon())
        self.button_hbox_layt.addWidget(self.create_button)
        self.main_layt.addLayout(self.button_hbox_layt)

        self.close_button = qtutils.create_button(text=N_('Close'))
        self.button_hbox_layt.addWidget(self.close_button)

        connect_button(self.close_button, self.accept)
        connect_button(self.create_button, self.create_tag)

        self.resize(506, 295)

    def create_tag(self):
        """Verifies inputs and emits a notifier tag message."""

        revision = self.revision.value()
        tag_name = self.tag_name.value()
        tag_msg = self.tag_msg.value()
        sign_tag = self.sign_tag.isChecked()

        if not revision:
            critical(N_('Missing Revision'),
                     N_('Please specify a revision to tag.'))
            return
        elif not tag_name:
            critical(N_('Missing Name'),
                     N_('Please specify a name for the new tag.'))
            return
        elif (sign_tag and not tag_msg and
                not qtutils.confirm(N_('Missing Tag Message'),
                                    N_('Tag-signing was requested but the tag '
                                       'message is empty.'),
                                    N_('An unsigned, lightweight tag will be '
                                       'created instead.\n'
                                       'Create an unsigned tag?'),
                                    N_('Create Unsigned Tag'),
                                    default=False,
                                    icon=qtutils.save_icon())):
            return

        cmds.do(cmds.Tag, tag_name, revision,
                sign=sign_tag, message=tag_msg)
        information(N_('Tag Created'),
                    N_('Created a new tag named "%s"') % tag_name,
                    details=tag_msg or None)
        self.accept()

########NEW FILE########
__FILENAME__ = dag
from __future__ import division, absolute_import, unicode_literals

import collections
import math
import sys

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtCore import QPointF
from PyQt4.QtCore import QRectF

from cola import cmds
from cola import difftool
from cola import observable
from cola import qtutils
from cola.i18n import N_
from cola.models.dag import DAG
from cola.models.dag import RepoReader
from cola.widgets import completion
from cola.widgets import defs
from cola.widgets.createbranch import create_new_branch
from cola.widgets.createtag import create_tag
from cola.widgets.archive import GitArchiveDialog
from cola.widgets.browse import BrowseDialog
from cola.widgets.standard import MainWindow
from cola.widgets.standard import TreeWidget
from cola.widgets.diff import COMMITS_SELECTED
from cola.widgets.diff import DiffWidget
from cola.widgets.filelist import FileWidget
from cola.compat import ustr


def git_dag(model, args=None, settings=None):
    """Return a pre-populated git DAG widget."""
    branch = model.currentbranch
    # disambiguate between branch names and filenames by using '--'
    branch_doubledash = branch and (branch + ' --') or ''
    dag = DAG(branch_doubledash, 1000)
    dag.set_arguments(args)

    view = GitDAG(model, dag, settings=settings)
    if dag.ref:
        view.display()
    return view


class ViewerMixin(object):
    """Implementations must provide selected_items()"""

    def __init__(self):
        self.selected = None
        self.clicked = None
        self.menu_actions = self.context_menu_actions()

    def selected_item(self):
        """Return the currently selected item"""
        selected_items = self.selected_items()
        if not selected_items:
            return None
        return selected_items[0]

    def selected_sha1(self):
        item = self.selected_item()
        if item is None:
            return None
        return item.commit.sha1

    def diff_selected_this(self):
        clicked_sha1 = self.clicked.sha1
        selected_sha1 = self.selected.sha1
        self.emit(SIGNAL('diff_commits'), selected_sha1, clicked_sha1)

    def diff_this_selected(self):
        clicked_sha1 = self.clicked.sha1
        selected_sha1 = self.selected.sha1
        self.emit(SIGNAL('diff_commits'), clicked_sha1, selected_sha1)

    def cherry_pick(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        cmds.do(cmds.CherryPick, [sha1])

    def copy_to_clipboard(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        qtutils.set_clipboard(sha1)

    def create_branch(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        create_new_branch(revision=sha1)

    def create_tag(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        create_tag(ref=sha1)

    def create_tarball(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        short_sha1 = sha1[:7]
        GitArchiveDialog.save_hashed_objects(sha1, short_sha1, self)

    def save_blob_dialog(self):
        sha1 = self.selected_sha1()
        if sha1 is None:
            return
        return BrowseDialog.browse(sha1)

    def context_menu_actions(self):
        return {
        'diff_this_selected':
            qtutils.add_action(self, N_('Diff this -> selected'),
                               self.diff_this_selected),
        'diff_selected_this':
            qtutils.add_action(self, N_('Diff selected -> this'),
                               self.diff_selected_this),
        'create_branch':
            qtutils.add_action(self, N_('Create Branch'),
                               self.create_branch),
        'create_patch':
            qtutils.add_action(self, N_('Create Patch'),
                               self.create_patch),
        'create_tag':
            qtutils.add_action(self, N_('Create Tag'),
                               self.create_tag),
        'create_tarball':
            qtutils.add_action(self, N_('Save As Tarball/Zip...'),
                               self.create_tarball),
        'cherry_pick':
            qtutils.add_action(self, N_('Cherry Pick'),
                               self.cherry_pick),
        'save_blob':
            qtutils.add_action(self, N_('Grab File...'),
                               self.save_blob_dialog),
        'copy':
            qtutils.add_action(self, N_('Copy SHA-1'),
                               self.copy_to_clipboard,
                               QtGui.QKeySequence.Copy),
        }

    def update_menu_actions(self, event):
        selected_items = self.selected_items()
        item = self.itemAt(event.pos())
        if item is None:
            self.clicked = commit = None
        else:
            self.clicked = commit = item.commit

        has_single_selection = len(selected_items) == 1
        has_selection = bool(selected_items)
        can_diff = bool(commit and has_single_selection and
                        commit is not selected_items[0].commit)

        if can_diff:
            self.selected = selected_items[0].commit
        else:
            self.selected = None

        self.menu_actions['diff_this_selected'].setEnabled(can_diff)
        self.menu_actions['diff_selected_this'].setEnabled(can_diff)

        self.menu_actions['create_branch'].setEnabled(has_single_selection)
        self.menu_actions['create_tag'].setEnabled(has_single_selection)

        self.menu_actions['cherry_pick'].setEnabled(has_single_selection)
        self.menu_actions['create_patch'].setEnabled(has_selection)
        self.menu_actions['create_tarball'].setEnabled(has_single_selection)

        self.menu_actions['save_blob'].setEnabled(has_single_selection)
        self.menu_actions['copy'].setEnabled(has_single_selection)

    def context_menu_event(self, event):
        self.update_menu_actions(event)
        menu = QtGui.QMenu(self)
        menu.addAction(self.menu_actions['diff_this_selected'])
        menu.addAction(self.menu_actions['diff_selected_this'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['create_branch'])
        menu.addAction(self.menu_actions['create_tag'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['cherry_pick'])
        menu.addAction(self.menu_actions['create_patch'])
        menu.addAction(self.menu_actions['create_tarball'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['save_blob'])
        menu.addAction(self.menu_actions['copy'])
        menu.exec_(self.mapToGlobal(event.pos()))


class CommitTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, commit, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(0, commit.summary)
        self.setText(1, commit.author)
        self.setText(2, commit.authdate)


class CommitTreeWidget(ViewerMixin, TreeWidget):

    def __init__(self, notifier, parent):
        TreeWidget.__init__(self, parent)
        ViewerMixin.__init__(self)

        self.setSelectionMode(self.ContiguousSelection)
        self.setHeaderLabels([N_('Summary'), N_('Author'), N_('Date, Time')])

        self.sha1map = {}
        self.notifier = notifier
        self.selecting = False
        self.commits = []

        self.action_up = qtutils.add_action(self, N_('Go Up'), self.go_up,
                                            Qt.Key_K)

        self.action_down = qtutils.add_action(self, N_('Go Down'), self.go_down,
                                              Qt.Key_J)

        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)

    # ViewerMixin
    def go_up(self):
        self.goto(self.itemAbove)

    def go_down(self):
        self.goto(self.itemBelow)

    def goto(self, finder):
        items = self.selected_items()
        item = items and items[0] or None
        if item is None:
            return
        found = finder(item)
        if found:
            self.select([found.commit.sha1], block_signals=False)

    def set_selecting(self, selecting):
        self.selecting = selecting

    def selection_changed(self):
        items = self.selected_items()
        if not items:
            return
        self.set_selecting(True)
        self.notifier.notify_observers(COMMITS_SELECTED,
                                       [i.commit for i in items])
        self.set_selecting(False)

    def commits_selected(self, commits):
        if self.selecting:
            return
        self.select([commit.sha1 for commit in commits])

    def select(self, sha1s, block_signals=True):
        self.clearSelection()
        for sha1 in sha1s:
            try:
                item = self.sha1map[sha1]
            except KeyError:
                continue
            block = self.blockSignals(block_signals)
            self.scrollToItem(item)
            item.setSelected(True)
            self.blockSignals(block)

    def adjust_columns(self):
        width = self.width()-20
        zero = width*2//3
        onetwo = width//6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)

    def clear(self):
        QtGui.QTreeWidget.clear(self)
        self.sha1map.clear()
        self.commits = []

    def add_commits(self, commits):
        self.commits.extend(commits)
        items = []
        for c in reversed(commits):
            item = CommitTreeWidgetItem(c)
            items.append(item)
            self.sha1map[c.sha1] = item
            for tag in c.tags:
                self.sha1map[tag] = item
        self.insertTopLevelItems(0, items)

    def create_patch(self):
        items = self.selectedItems()
        if not items:
            return
        sha1s = [item.commit.sha1 for item in reversed(items)]
        all_sha1s = [c.sha1 for c in self.commits]
        cmds.do(cmds.FormatPatch, sha1s, all_sha1s)

    # Qt overrides
    def contextMenuEvent(self, event):
        self.context_menu_event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            event.accept()
            return
        QtGui.QTreeWidget.mousePressEvent(self, event)


class GitDAG(MainWindow):
    """The git-dag widget."""

    def __init__(self, model, dag, parent=None, settings=None):
        MainWindow.__init__(self, parent)

        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setMinimumSize(420, 420)

        # change when widgets are added/removed
        self.widget_version = 1
        self.model = model
        self.dag = dag
        self.settings = settings

        self.commits = {}
        self.commit_list = []

        self.old_count = None
        self.old_ref = None
        self.thread = ReaderThread(dag, self)

        self.revtext = completion.GitLogLineEdit()

        self.maxresults = QtGui.QSpinBox()
        self.maxresults.setMinimum(1)
        self.maxresults.setMaximum(99999)
        self.maxresults.setPrefix('')
        self.maxresults.setSuffix('')

        self.zoom_out = qtutils.create_action_button(
                tooltip=N_('Zoom Out'),
                icon=qtutils.theme_icon('zoom-out.png'))

        self.zoom_in = qtutils.create_action_button(
                tooltip=N_('Zoom In'),
                icon=qtutils.theme_icon('zoom-in.png'))

        self.zoom_to_fit = qtutils.create_action_button(
                tooltip=N_('Zoom to Fit'),
                icon=qtutils.theme_icon('zoom-fit-best.png'))

        self.notifier = notifier = observable.Observable()
        self.notifier.refs_updated = refs_updated = 'refs_updated'
        self.notifier.add_observer(refs_updated, self.display)

        self.treewidget = CommitTreeWidget(notifier, self)
        self.diffwidget = DiffWidget(notifier, self)
        self.filewidget = FileWidget(notifier, self)
        self.graphview = GraphView(notifier, self)

        self.controls_layout = QtGui.QHBoxLayout()
        self.controls_layout.setMargin(defs.no_margin)
        self.controls_layout.setSpacing(defs.spacing)
        self.controls_layout.addWidget(self.revtext)
        self.controls_layout.addWidget(self.maxresults)

        self.controls_widget = QtGui.QWidget()
        self.controls_widget.setLayout(self.controls_layout)

        self.log_dock = qtutils.create_dock(N_('Log'), self, stretch=False)
        self.log_dock.setWidget(self.treewidget)
        log_dock_titlebar = self.log_dock.titleBarWidget()
        log_dock_titlebar.add_corner_widget(self.controls_widget)

        self.file_dock = qtutils.create_dock(N_('Files'), self)
        self.file_dock.setWidget(self.filewidget)

        self.diff_dock = qtutils.create_dock(N_('Diff'), self)
        self.diff_dock.setWidget(self.diffwidget)

        self.graph_controls_layout = QtGui.QHBoxLayout()
        self.graph_controls_layout.setMargin(defs.no_margin)
        self.graph_controls_layout.setSpacing(defs.button_spacing)
        self.graph_controls_layout.addWidget(self.zoom_out)
        self.graph_controls_layout.addWidget(self.zoom_in)
        self.graph_controls_layout.addWidget(self.zoom_to_fit)

        self.graph_controls_widget = QtGui.QWidget()
        self.graph_controls_widget.setLayout(self.graph_controls_layout)

        self.graphview_dock = qtutils.create_dock(N_('Graph'), self)
        self.graphview_dock.setWidget(self.graphview)
        graph_titlebar = self.graphview_dock.titleBarWidget()
        graph_titlebar.add_corner_widget(self.graph_controls_widget)

        self.lock_layout_action = qtutils.add_action_bool(self,
                N_('Lock Layout'), self.set_lock_layout, False)

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # View Menu
        self.view_menu = qtutils.create_menu(N_('View'), self.menubar)
        self.view_menu.addAction(self.log_dock.toggleViewAction())
        self.view_menu.addAction(self.graphview_dock.toggleViewAction())
        self.view_menu.addAction(self.diff_dock.toggleViewAction())
        self.view_menu.addAction(self.file_dock.toggleViewAction())
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.lock_layout_action)

        self.menubar.addAction(self.view_menu.menuAction())
        self.setMenuBar(self.menubar)

        left = Qt.LeftDockWidgetArea
        right = Qt.RightDockWidgetArea
        bottom = Qt.BottomDockWidgetArea
        self.addDockWidget(left, self.log_dock)
        self.addDockWidget(right, self.graphview_dock)
        self.addDockWidget(right, self.file_dock)
        self.addDockWidget(bottom, self.diff_dock)

        # Update fields affected by model
        self.revtext.setText(dag.ref)
        self.maxresults.setValue(dag.count)
        self.update_window_title()

        # Also re-loads dag.* from the saved state
        if not self.restore_state(settings=settings):
            self.resize_to_desktop()

        qtutils.connect_button(self.zoom_out, self.graphview.zoom_out)
        qtutils.connect_button(self.zoom_in, self.graphview.zoom_in)
        qtutils.connect_button(self.zoom_to_fit,
                               self.graphview.zoom_to_fit)

        self.thread.connect(self.thread, self.thread.commits_ready,
                            self.add_commits)

        self.thread.connect(self.thread, self.thread.done,
                            self.thread_done)

        self.connect(self.treewidget, SIGNAL('diff_commits'),
                     self.diff_commits)

        self.connect(self.graphview, SIGNAL('diff_commits'),
                     self.diff_commits)

        self.connect(self.maxresults, SIGNAL('editingFinished()'),
                     self.display)

        self.connect(self.revtext, SIGNAL('changed()'),
                     self.display)

        self.connect(self.revtext, SIGNAL('textChanged(QString)'),
                     self.text_changed)

        self.connect(self.revtext, SIGNAL('returnPressed()'),
                     self.display)

        # The model is updated in another thread so use
        # signals/slots to bring control back to the main GUI thread
        self.model.add_observer(self.model.message_updated,
                                self.emit_model_updated)

        self.connect(self, SIGNAL('model_updated'),
                     self.model_updated)

        qtutils.add_action(self, 'Focus search field',
                           lambda: self.revtext.setFocus(), 'Ctrl+l')

        qtutils.add_close_action(self)

    def text_changed(self, txt):
        self.dag.ref = ustr(txt)
        self.update_window_title()

    def update_window_title(self):
        project = self.model.project
        if self.dag.ref:
            self.setWindowTitle(N_('%s: %s - DAG') % (project, self.dag.ref))
        else:
            self.setWindowTitle(project + N_(' - DAG'))

    def export_state(self):
        state = MainWindow.export_state(self)
        state['count'] = self.dag.count
        return state

    def apply_state(self, state):
        result = MainWindow.apply_state(self, state)
        try:
            count = state['count']
            if self.dag.overridden('count'):
                count = self.dag.count
        except:
            count = self.dag.count
            result = False
        self.dag.set_count(count)
        self.lock_layout_action.setChecked(state.get('lock_layout', False))
        return result

    def emit_model_updated(self):
        self.emit(SIGNAL('model_updated'))

    def model_updated(self):
        if self.dag.ref:
            self.revtext.update_matches()
            return
        if not self.model.currentbranch:
            return
        self.revtext.setText(self.model.currentbranch + ' --')
        self.display()

    def display(self):
        new_ref = ustr(self.revtext.text())
        if not new_ref:
            return
        new_count = self.maxresults.value()
        old_ref = self.old_ref
        old_count = self.old_count
        if old_ref == new_ref and old_count == new_count:
            return

        self.old_ref = new_ref
        self.old_count = new_count

        self.thread.stop()
        self.clear()
        self.dag.set_ref(new_ref)
        self.dag.set_count(self.maxresults.value())
        self.thread.start()

    def show(self):
        MainWindow.show(self)
        self.treewidget.adjust_columns()

    def clear(self):
        self.graphview.clear()
        self.treewidget.clear()
        self.commits.clear()
        self.commit_list = []

    def add_commits(self, commits):
        self.commit_list.extend(commits)
        # Keep track of commits
        for commit_obj in commits:
            self.commits[commit_obj.sha1] = commit_obj
            for tag in commit_obj.tags:
                self.commits[tag] = commit_obj
        self.graphview.add_commits(commits)
        self.treewidget.add_commits(commits)

    def thread_done(self):
        self.graphview.setFocus()
        try:
            commit_obj = self.commit_list[-1]
        except IndexError:
            return
        self.notifier.notify_observers(COMMITS_SELECTED, [commit_obj])
        self.graphview.update_scene_rect()
        self.graphview.set_initial_view()

    def resize_to_desktop(self):
        desktop = QtGui.QApplication.instance().desktop()
        width = desktop.width()
        height = desktop.height()
        self.resize(width, height)

    def diff_commits(self, a, b):
        paths = self.dag.paths()
        if paths:
            difftool.launch([a, b, '--'] + paths)
        else:
            difftool.diff_commits(self, a, b)

    # Qt overrides
    def closeEvent(self, event):
        self.revtext.close_popup()
        self.thread.stop()
        MainWindow.closeEvent(self, event)

    def resizeEvent(self, e):
        MainWindow.resizeEvent(self, e)
        self.treewidget.adjust_columns()


class ReaderThread(QtCore.QThread):
    commits_ready = SIGNAL('commits_ready')
    done = SIGNAL('done')

    def __init__(self, dag, parent):
        QtCore.QThread.__init__(self, parent)
        self.dag = dag
        self._abort = False
        self._stop = False
        self._mutex = QtCore.QMutex()
        self._condition = QtCore.QWaitCondition()

    def run(self):
        repo = RepoReader(self.dag)
        repo.reset()
        commits = []
        for c in repo:
            self._mutex.lock()
            if self._stop:
                self._condition.wait(self._mutex)
            self._mutex.unlock()
            if self._abort:
                repo.reset()
                return
            commits.append(c)
            if len(commits) >= 512:
                self.emit(self.commits_ready, commits)
                commits = []

        if commits:
            self.emit(self.commits_ready, commits)
        self.emit(self.done)

    def start(self):
        self._abort = False
        self._stop = False
        QtCore.QThread.start(self)

    def pause(self):
        self._mutex.lock()
        self._stop = True
        self._mutex.unlock()

    def resume(self):
        self._mutex.lock()
        self._stop = False
        self._mutex.unlock()
        self._condition.wakeOne()

    def stop(self):
        self._abort = True
        self.wait()


class Cache(object):
    pass


class Edge(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 1

    def __init__(self, source, dest):

        QtGui.QGraphicsItem.__init__(self)

        self.setAcceptedMouseButtons(Qt.NoButton)
        self.source = source
        self.dest = dest
        self.commit = source.commit
        self.setZValue(-2)

        dest_pt = Commit.item_bbox.center()

        self.source_pt = self.mapFromItem(self.source, dest_pt)
        self.dest_pt = self.mapFromItem(self.dest, dest_pt)
        self.line = QtCore.QLineF(self.source_pt, self.dest_pt)

        width = self.dest_pt.x() - self.source_pt.x()
        height = self.dest_pt.y() - self.source_pt.y()
        rect = QtCore.QRectF(self.source_pt, QtCore.QSizeF(width, height))
        self.bound = rect.normalized()

        # Choose a new color for new branch edges
        if self.source.x() < self.dest.x():
            color = EdgeColor.next()
            line = Qt.SolidLine
        elif self.source.x() != self.dest.x():
            color = EdgeColor.current()
            line = Qt.SolidLine
        else:
            color = EdgeColor.current()
            line = Qt.SolidLine

        self.pen = QtGui.QPen(color, 4.0, line, Qt.SquareCap, Qt.RoundJoin)

    # Qt overrides
    def type(self):
        return self.item_type

    def boundingRect(self):
        return self.bound

    def paint(self, painter, option, widget):

        arc_rect = 10
        connector_length = 5

        painter.setPen(self.pen)
        path = QtGui.QPainterPath()

        if self.source.x() == self.dest.x():
            path.moveTo(self.source.x(), self.source.y())
            path.lineTo(self.dest.x(), self.dest.y())
            painter.drawPath(path)

        else:

            #Define points starting from source
            point1 = QPointF(self.source.x(), self.source.y())
            point2 = QPointF(point1.x(), point1.y() - connector_length)
            point3 = QPointF(point2.x() + arc_rect, point2.y() - arc_rect)

            #Define points starting from dest
            point4 = QPointF(self.dest.x(), self.dest.y())
            point5 = QPointF(point4.x(),point3.y() - arc_rect)
            point6 = QPointF(point5.x() - arc_rect, point5.y() + arc_rect)

            start_angle_arc1 = 180
            span_angle_arc1 = 90
            start_angle_arc2 = 90
            span_angle_arc2 = -90

            # If the dest is at the left of the source, then we
            # need to reverse some values
            if self.source.x() > self.dest.x():
                point5 = QPointF(point4.x(), point4.y() + connector_length)
                point6 = QPointF(point5.x() + arc_rect, point5.y() + arc_rect)
                point3 = QPointF(self.source.x() - arc_rect, point6.y())
                point2 = QPointF(self.source.x(), point3.y() + arc_rect)

                span_angle_arc1 = 90

            path.moveTo(point1)
            path.lineTo(point2)
            path.arcTo(QRectF(point2, point3),
                       start_angle_arc1, span_angle_arc1)
            path.lineTo(point6)
            path.arcTo(QRectF(point6, point5),
                       start_angle_arc2, span_angle_arc2)
            path.lineTo(point4)
            painter.drawPath(path)


class EdgeColor(object):
    """An edge color factory"""

    current_color_index = 0
    colors = [
                QtGui.QColor(Qt.red),
                QtGui.QColor(Qt.green),
                QtGui.QColor(Qt.blue),
                QtGui.QColor(Qt.black),
                QtGui.QColor(Qt.darkRed),
                QtGui.QColor(Qt.darkGreen),
                QtGui.QColor(Qt.darkBlue),
                QtGui.QColor(Qt.cyan),
                QtGui.QColor(Qt.magenta),
                # Orange; Qt.yellow is too low-contrast
                qtutils.rgba(0xff, 0x66, 0x00),
                QtGui.QColor(Qt.gray),
                QtGui.QColor(Qt.darkCyan),
                QtGui.QColor(Qt.darkMagenta),
                QtGui.QColor(Qt.darkYellow),
                QtGui.QColor(Qt.darkGray),
             ]

    @classmethod
    def next(cls):
        cls.current_color_index += 1
        cls.current_color_index %= len(cls.colors)
        color = cls.colors[cls.current_color_index]
        color.setAlpha(128)
        return color

    @classmethod
    def current(cls):
        return cls.colors[cls.current_color_index]


class Commit(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 2
    commit_radius = 12.0
    merge_radius = 18.0

    item_shape = QtGui.QPainterPath()
    item_shape.addRect(commit_radius/-2.0,
                       commit_radius/-2.0,
                       commit_radius, commit_radius)
    item_bbox = item_shape.boundingRect()

    inner_rect = QtGui.QPainterPath()
    inner_rect.addRect(commit_radius/-2.0 + 2.0,
                       commit_radius/-2.0 + 2.0,
                       commit_radius - 4.0,
                       commit_radius - 4.0)
    inner_rect = inner_rect.boundingRect()

    commit_color = QtGui.QColor(Qt.white)
    outline_color = commit_color.darker()
    merge_color = QtGui.QColor(Qt.lightGray)

    commit_selected_color = QtGui.QColor(Qt.green)
    selected_outline_color = commit_selected_color.darker()

    commit_pen = QtGui.QPen()
    commit_pen.setWidth(1.0)
    commit_pen.setColor(outline_color)

    def __init__(self, commit,
                 notifier,
                 selectable=QtGui.QGraphicsItem.ItemIsSelectable,
                 cursor=Qt.PointingHandCursor,
                 xpos=commit_radius/2.0 + 1.0,
                 cached_commit_color=commit_color,
                 cached_merge_color=merge_color):

        QtGui.QGraphicsItem.__init__(self)

        self.commit = commit
        self.notifier = notifier

        self.setZValue(0)
        self.setFlag(selectable)
        self.setCursor(cursor)
        self.setToolTip(commit.sha1[:7] + ': ' + commit.summary)

        if commit.tags:
            self.label = label = Label(commit)
            label.setParentItem(self)
            label.setPos(xpos, -self.commit_radius/2.0)
        else:
            self.label = None

        if len(commit.parents) > 1:
            self.brush = cached_merge_color
        else:
            self.brush = cached_commit_color

        self.pressed = False
        self.dragged = False

    def blockSignals(self, blocked):
        self.notifier.notification_enabled = not blocked

    def itemChange(self, change, value):
        if change == QtGui.QGraphicsItem.ItemSelectedHasChanged:
            # Broadcast selection to other widgets
            selected_items = self.scene().selectedItems()
            commits = [item.commit for item in selected_items]
            self.scene().parent().set_selecting(True)
            self.notifier.notify_observers(COMMITS_SELECTED, commits)
            self.scene().parent().set_selecting(False)

            # Cache the pen for use in paint()
            if value.toPyObject():
                self.brush = self.commit_selected_color
                color = self.selected_outline_color
            else:
                if len(self.commit.parents) > 1:
                    self.brush = self.merge_color
                else:
                    self.brush = self.commit_color
                color = self.outline_color
            commit_pen = QtGui.QPen()
            commit_pen.setWidth(1.0)
            commit_pen.setColor(color)
            self.commit_pen = commit_pen

        return QtGui.QGraphicsItem.itemChange(self, change, value)

    def type(self):
        return self.item_type

    def boundingRect(self, rect=item_bbox):
        return rect

    def shape(self):
        return self.item_shape

    def paint(self, painter, option, widget,
              inner=inner_rect,
              cache=Cache):

        # Do not draw outside the exposed rect
        painter.setClipRect(option.exposedRect)

        # Draw ellipse
        painter.setPen(self.commit_pen)
        painter.setBrush(self.brush)
        painter.drawEllipse(inner)


    def mousePressEvent(self, event):
        QtGui.QGraphicsItem.mousePressEvent(self, event)
        self.pressed = True
        self.selected = self.isSelected()

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtGui.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QtGui.QGraphicsItem.mouseReleaseEvent(self, event)
        if (not self.dragged and
                self.selected and
                event.button() == Qt.LeftButton):
            return
        self.pressed = False
        self.dragged = False


class Label(QtGui.QGraphicsItem):
    item_type = QtGui.QGraphicsItem.UserType + 3

    width = 72
    height = 18

    item_shape = QtGui.QPainterPath()
    item_shape.addRect(0, 0, width, height)
    item_bbox = item_shape.boundingRect()

    text_options = QtGui.QTextOption()
    text_options.setAlignment(Qt.AlignCenter)
    text_options.setAlignment(Qt.AlignVCenter)

    def __init__(self, commit,
                 other_color=QtGui.QColor(Qt.white),
                 head_color=QtGui.QColor(Qt.green)):
        QtGui.QGraphicsItem.__init__(self)
        self.setZValue(-1)

        # Starts with enough space for two tags. Any more and the commit
        # needs to be taller to accomodate.
        self.commit = commit

        if 'HEAD' in commit.tags:
            self.color = head_color
        else:
            self.color = other_color

        self.color.setAlpha(180)
        self.pen = QtGui.QPen()
        self.pen.setColor(self.color.darker())
        self.pen.setWidth(1.0)

    def type(self):
        return self.item_type

    def boundingRect(self, rect=item_bbox):
        return rect

    def shape(self):
        return self.item_shape

    def paint(self, painter, option, widget,
              text_opts=text_options,
              black=Qt.black,
              cache=Cache):
        try:
            font = cache.label_font
        except AttributeError:
            font = cache.label_font = QtGui.QApplication.font()
            font.setPointSize(6)


        # Draw tags
        painter.setBrush(self.color)
        painter.setPen(self.pen)
        painter.setFont(font)

        current_width = 0

        for tag in self.commit.tags:
            text_rect = painter.boundingRect(
                    QRectF(current_width, 0, 0, 0), Qt.TextSingleLine, tag)
            box_rect = text_rect.adjusted(-1, -1, 1, 1)
            painter.drawRoundedRect(box_rect, 2, 2)
            painter.drawText(text_rect, Qt.TextSingleLine, tag)
            current_width += text_rect.width() + 5


class GraphView(ViewerMixin, QtGui.QGraphicsView):

    x_max = 0
    y_min = 0

    x_adjust = Commit.commit_radius*4/3
    y_adjust = Commit.commit_radius*4/3

    x_off = 18
    y_off = 24

    def __init__(self, notifier, parent):
        QtGui.QGraphicsView.__init__(self, parent)
        ViewerMixin.__init__(self)

        highlight = self.palette().color(QtGui.QPalette.Highlight)
        Commit.commit_selected_color = highlight
        Commit.selected_outline_color = highlight.darker()

        self.selection_list = []
        self.notifier = notifier
        self.commits = []
        self.items = {}
        self.saved_matrix = QtGui.QMatrix(self.matrix())

        self.x_offsets = collections.defaultdict(int)

        self.is_panning = False
        self.pressed = False
        self.selecting = False
        self.last_mouse = [0, 0]
        self.zoom = 2
        self.setDragMode(self.RubberBandDrag)

        scene = QtGui.QGraphicsScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        self.setScene(scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setViewportUpdateMode(self.BoundingRectViewportUpdate)
        self.setCacheMode(QtGui.QGraphicsView.CacheBackground)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setBackgroundBrush(QtGui.QColor(Qt.white))

        qtutils.add_action(self, N_('Zoom In'),
                           self.zoom_in, Qt.Key_Plus, Qt.Key_Equal)

        qtutils.add_action(self, N_('Zoom Out'),
                           self.zoom_out, Qt.Key_Minus)

        qtutils.add_action(self, N_('Zoom to Fit'),
                           self.zoom_to_fit, Qt.Key_F)

        qtutils.add_action(self, N_('Select Parent'),
                           self.select_parent, 'Shift+J')

        qtutils.add_action(self, N_('Select Oldest Parent'),
                           self.select_oldest_parent, Qt.Key_J)

        qtutils.add_action(self, N_('Select Child'),
                           self.select_child, 'Shift+K')

        qtutils.add_action(self, N_('Select Newest Child'),
                           self.select_newest_child, Qt.Key_K)

        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)

    def clear(self):
        self.scene().clear()
        self.selection_list = []
        self.items.clear()
        self.x_offsets.clear()
        self.x_max = 0
        self.y_min = 0
        self.commits = []

    # ViewerMixin interface
    def selected_items(self):
        """Return the currently selected items"""
        return self.scene().selectedItems()

    def zoom_in(self):
        self.scale_view(1.5)

    def zoom_out(self):
        self.scale_view(1.0/1.5)

    def commits_selected(self, commits):
        if self.selecting:
            return
        self.select([commit.sha1 for commit in commits])

    def select(self, sha1s):
        """Select the item for the SHA-1"""
        self.scene().clearSelection()
        for sha1 in sha1s:
            try:
                item = self.items[sha1]
            except KeyError:
                continue
            item.blockSignals(True)
            item.setSelected(True)
            item.blockSignals(False)
            item_rect = item.sceneTransform().mapRect(item.boundingRect())
            self.ensureVisible(item_rect)

    def get_item_by_generation(self, commits, criteria_fn):
        """Return the item for the commit matching criteria"""
        if not commits:
            return None
        generation = None
        for commit in commits:
            if (generation is None or
                    criteria_fn(generation, commit.generation)):
                sha1 = commit.sha1
                generation = commit.generation
        try:
            return self.items[sha1]
        except KeyError:
            return None

    def oldest_item(self, commits):
        """Return the item for the commit with the oldest generation number"""
        return self.get_item_by_generation(commits, lambda a, b: a > b)

    def newest_item(self, commits):
        """Return the item for the commit with the newest generation number"""
        return self.get_item_by_generation(commits, lambda a, b: a < b)

    def create_patch(self):
        items = self.selected_items()
        if not items:
            return
        selected_commits = self.sort_by_generation([n.commit for n in items])
        sha1s = [c.sha1 for c in selected_commits]
        all_sha1s = [c.sha1 for c in self.commits]
        cmds.do(cmds.FormatPatch, sha1s, all_sha1s)

    def select_parent(self):
        """Select the parent with the newest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self.newest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        self.ensureVisible(
                parent_item.mapRectToScene(parent_item.boundingRect()))

    def select_oldest_parent(self):
        """Select the parent with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self.oldest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        scene_rect = parent_item.mapRectToScene(parent_item.boundingRect())
        self.ensureVisible(scene_rect)

    def select_child(self):
        """Select the child with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        child_item = self.oldest_item(selected_item.commit.children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        scene_rect = child_item.mapRectToScene(child_item.boundingRect())
        self.ensureVisible(scene_rect)

    def select_newest_child(self):
        """Select the Nth child with the newest generation number (N > 1)"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        if len(selected_item.commit.children) > 1:
            children = selected_item.commit.children[1:]
        else:
            children = selected_item.commit.children
        child_item = self.newest_item(children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        scene_rect = child_item.mapRectToScene(child_item.boundingRect())
        self.ensureVisible(scene_rect)

    def set_initial_view(self):
        self_commits = self.commits
        self_items = self.items

        commits = self_commits[-2:]
        items = [self_items[c.sha1] for c in commits]
        self.fit_view_to_items(items)

    def zoom_to_fit(self):
        """Fit selected items into the viewport"""

        items = self.selected_items()
        self.fit_view_to_items(items)

    def fit_view_to_items(self, items):
        if not items:
            rect = self.scene().itemsBoundingRect()
        else:
            maxint = 9223372036854775807
            x_min = maxint
            y_min = maxint
            x_max = -maxint
            ymax = -maxint
            for item in items:
                pos = item.pos()
                item_rect = item.boundingRect()
                x_off = item_rect.width()
                y_off = item_rect.height()
                x_min = min(x_min, pos.x())
                y_min = min(y_min, pos.y()-y_off)
                x_max = max(x_max, pos.x()+x_off)
                ymax = max(ymax, pos.y())
            rect = QtCore.QRectF(x_min, y_min, x_max-x_min, ymax-y_min)
        x_adjust = GraphView.x_adjust
        y_adjust = GraphView.y_adjust
        rect.setX(rect.x() - x_adjust)
        rect.setY(rect.y() - y_adjust)
        rect.setHeight(rect.height() + y_adjust*2)
        rect.setWidth(rect.width() + x_adjust*2)
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.scene().invalidate()

    def save_selection(self, event):
        if event.button() != Qt.LeftButton:
            return
        elif Qt.ShiftModifier != event.modifiers():
            return
        self.selection_list = self.selected_items()

    def restore_selection(self, event):
        if Qt.ShiftModifier != event.modifiers():
            return
        for item in self.selection_list:
            item.setSelected(True)

    def handle_event(self, event_handler, event):
        self.update()
        self.save_selection(event)
        event_handler(self, event)
        self.restore_selection(event)

    def set_selecting(self, selecting):
        self.selecting = selecting

    def pan(self, event):
        pos = event.pos()
        dx = pos.x() - self.mouse_start[0]
        dy = pos.y() - self.mouse_start[1]

        if dx == 0 and dy == 0:
            return

        rect = QtCore.QRect(0, 0, abs(dx), abs(dy))
        delta = self.mapToScene(rect).boundingRect()

        tx = delta.width()
        if dx < 0.0:
            tx = -tx

        ty = delta.height()
        if dy < 0.0:
            ty = -ty

        matrix = QtGui.QMatrix(self.saved_matrix).translate(tx, ty)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def wheel_zoom(self, event):
        """Handle mouse wheel zooming."""
        zoom = math.pow(2.0, event.delta()/512.0)
        factor = (self.matrix()
                        .scale(zoom, zoom)
                        .mapRect(QtCore.QRectF(0.0, 0.0, 1.0, 1.0))
                        .width())
        if factor < 0.014 or factor > 42.0:
            return
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.zoom = zoom
        self.scale(zoom, zoom)

    def wheel_pan(self, event):
        """Handle mouse wheel panning."""

        if event.delta() < 0:
            s = -133.0
        else:
            s = 133.0
        pan_rect = QtCore.QRectF(0.0, 0.0, 1.0, 1.0)
        factor = 1.0/self.matrix().mapRect(pan_rect).width()

        if event.orientation() == Qt.Vertical:
            matrix = self.matrix().translate(0, s*factor)
        else:
            matrix = self.matrix().translate(s*factor, 0)
        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.setMatrix(matrix)

    def scale_view(self, scale):
        factor = (self.matrix().scale(scale, scale)
                               .mapRect(QtCore.QRectF(0, 0, 1, 1))
                               .width())
        if factor < 0.07 or factor > 100.0:
            return
        self.zoom = scale

        adjust_scrollbars = True
        scrollbar = self.verticalScrollBar()
        if scrollbar:
            value = scrollbar.value()
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            distance = value - min_
            nonzero_range = range_ > 0.1
            if nonzero_range:
                scrolloffset = distance/range_
            else:
                adjust_scrollbars = False

        self.setTransformationAnchor(QtGui.QGraphicsView.NoAnchor)
        self.scale(scale, scale)

        scrollbar = self.verticalScrollBar()
        if scrollbar and adjust_scrollbars:
            min_ = scrollbar.minimum()
            max_ = scrollbar.maximum()
            range_ = max_ - min_
            value = min_ + int(float(range_) * scrolloffset)
            scrollbar.setValue(value)

    def add_commits(self, commits):
        """Traverse commits and add them to the view."""
        self.commits.extend(commits)
        scene = self.scene()
        for commit in commits:
            item = Commit(commit, self.notifier)
            self.items[commit.sha1] = item
            for ref in commit.tags:
                self.items[ref] = item
            scene.addItem(item)

        self.layout_commits(commits)
        self.link(commits)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            try:
                commit_item = self.items[commit.sha1]
            except KeyError:
                # TODO - Handle truncated history viewing
                continue
            for parent in reversed(commit.parents):
                try:
                    parent_item = self.items[parent.sha1]
                except KeyError:
                    # TODO - Handle truncated history viewing
                    continue
                edge = Edge(parent_item, commit_item)
                scene.addItem(edge)

    def layout_commits(self, nodes):
        positions = self.position_nodes(nodes)
        for sha1, (x, y) in positions.items():
            item = self.items[sha1]
            item.setPos(x, y)

    def position_nodes(self, nodes):
        positions = {}

        x_max = self.x_max
        y_min = self.y_min
        x_off = self.x_off
        y_off = self.y_off
        x_offsets = self.x_offsets

        for node in nodes:
            generation = node.generation
            sha1 = node.sha1

            if node.is_fork():
                # This is a fan-out so sweep over child generations and
                # shift them to the right to avoid overlapping edges
                child_gens = [c.generation for c in node.children]
                maxgen = max(child_gens)
                for g in range(generation + 1, maxgen):
                    x_offsets[g] += x_off

            if len(node.parents) == 1:
                # Align nodes relative to their parents
                parent_gen = node.parents[0].generation
                parent_off = x_offsets[parent_gen]
                x_offsets[generation] = max(parent_off-x_off,
                                            x_offsets[generation])

            cur_xoff = x_offsets[generation]
            next_xoff = cur_xoff
            next_xoff += x_off
            x_offsets[generation] = next_xoff

            x_pos = cur_xoff
            y_pos = -generation * y_off

            y_pos = min(y_pos, y_min - y_off)

            #y_pos = y_off
            positions[sha1] = (x_pos, y_pos)

            x_max = max(x_max, x_pos)
            y_min = y_pos

        self.x_max = x_max
        self.y_min = y_min

        return positions

    def update_scene_rect(self):
        y_min = self.y_min
        x_max = self.x_max
        self.scene().setSceneRect(-GraphView.x_adjust,
                                  y_min-GraphView.y_adjust,
                                  x_max + GraphView.x_adjust,
                                  abs(y_min) + GraphView.y_adjust)

    def sort_by_generation(self, commits):
        if len(commits) < 2:
            return commits
        commits.sort(key=lambda x: x.generation)
        return commits

    # Qt overrides
    def contextMenuEvent(self, event):
        self.context_menu_event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MidButton:
            pos = event.pos()
            self.mouse_start = [pos.x(), pos.y()]
            self.saved_matrix = QtGui.QMatrix(self.matrix())
            self.is_panning = True
            return
        if event.button() == Qt.RightButton:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.pressed = True
        self.handle_event(QtGui.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self.is_panning:
            self.pan(event)
            return
        self.last_mouse[0] = pos.x()
        self.last_mouse[1] = pos.y()
        self.handle_event(QtGui.QGraphicsView.mouseMoveEvent, event)

    def mouseReleaseEvent(self, event):
        self.pressed = False
        if event.button() == Qt.MidButton:
            self.is_panning = False
            return
        self.handle_event(QtGui.QGraphicsView.mouseReleaseEvent, event)
        self.selection_list = []

    def wheelEvent(self, event):
        """Handle Qt mouse wheel events."""
        if event.modifiers() == Qt.ControlModifier:
            self.wheel_zoom(event)
        else:
            self.wheel_pan(event)

########NEW FILE########
__FILENAME__ = defs
no_margin = 0
small_margin = 2
margin = 4
no_spacing = 0
spacing = 4
handle_width = 4
button_spacing = 12

########NEW FILE########
__FILENAME__ = diff
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, SIGNAL

from cola import cmds
from cola import core
from cola import gitcmds
from cola import gravatar
from cola import qtutils
from cola.cmds import run
from cola.i18n import N_
from cola.models import main
from cola.models import selection
from cola.qtutils import add_action
from cola.qtutils import create_action_button
from cola.qtutils import create_menu
from cola.qtutils import DiffSyntaxHighlighter
from cola.qtutils import options_icon
from cola.widgets import defs
from cola.widgets.text import MonoTextView
from cola.compat import ustr


COMMITS_SELECTED = 'COMMITS_SELECTED'
FILES_SELECTED = 'FILES_SELECTED'


class DiffTextEdit(MonoTextView):
    def __init__(self, parent, whitespace=True):

        MonoTextView.__init__(self, parent)
        # Diff/patch syntax highlighter
        self.highlighter = DiffSyntaxHighlighter(self.document(),
                                                 whitespace=whitespace)


class DiffEditor(DiffTextEdit):

    def __init__(self, parent):
        DiffTextEdit.__init__(self, parent)
        self.model = model = main.model()

        # "Diff Options" tool menu
        self.diff_ignore_space_at_eol_action = add_action(self,
                N_('Ignore changes in whitespace at EOL'),
                self._update_diff_opts)
        self.diff_ignore_space_at_eol_action.setCheckable(True)

        self.diff_ignore_space_change_action = add_action(self,
                N_('Ignore changes in amount of whitespace'),
                self._update_diff_opts)
        self.diff_ignore_space_change_action.setCheckable(True)

        self.diff_ignore_all_space_action = add_action(self,
                N_('Ignore all whitespace'),
                self._update_diff_opts)
        self.diff_ignore_all_space_action.setCheckable(True)

        self.diff_function_context_action = add_action(self,
                N_('Show whole surrounding functions of changes'),
                self._update_diff_opts)
        self.diff_function_context_action.setCheckable(True)

        self.diffopts_button = create_action_button(
                tooltip=N_('Diff Options'), icon=options_icon())
        self.diffopts_menu = create_menu(N_('Diff Options'),
                                         self.diffopts_button)

        self.diffopts_menu.addAction(self.diff_ignore_space_at_eol_action)
        self.diffopts_menu.addAction(self.diff_ignore_space_change_action)
        self.diffopts_menu.addAction(self.diff_ignore_all_space_action)
        self.diffopts_menu.addAction(self.diff_function_context_action)
        self.diffopts_button.setMenu(self.diffopts_menu)
        qtutils.hide_button_menu_indicator(self.diffopts_button)

        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.diffopts_button)

        self.action_process_section = qtutils.add_action(self,
                N_('Process Section'),
                self.apply_section, Qt.Key_H)
        self.action_process_selection = qtutils.add_action(self,
                N_('Process Selection'),
                self.apply_selection, Qt.Key_S)

        self.launch_editor = qtutils.add_action(self,
                cmds.LaunchEditor.name(), run(cmds.LaunchEditor),
                cmds.LaunchEditor.SHORTCUT,
                'Return', 'Enter')
        self.launch_editor.setIcon(qtutils.options_icon())

        self.launch_difftool = qtutils.add_action(self,
                cmds.LaunchDifftool.name(), run(cmds.LaunchDifftool),
                cmds.LaunchDifftool.SHORTCUT)
        self.launch_difftool.setIcon(qtutils.icon('git.svg'))

        self.action_stage_selection = qtutils.add_action(self,
                N_('Stage &Selected Lines'),
                self.stage_selection)
        self.action_stage_selection.setIcon(qtutils.icon('add.svg'))
        self.action_stage_selection.setShortcut(Qt.Key_S)

        self.action_revert_selection = qtutils.add_action(self,
                N_('Revert Selected Lines...'),
                self.revert_selection)
        self.action_revert_selection.setIcon(qtutils.icon('undo.svg'))

        self.action_unstage_selection = qtutils.add_action(self,
                N_('Unstage &Selected Lines'),
                self.unstage_selection)
        self.action_unstage_selection.setIcon(qtutils.icon('remove.svg'))
        self.action_unstage_selection.setShortcut(Qt.Key_S)

        self.action_apply_selection = qtutils.add_action(self,
                N_('Apply Diff Selection to Work Tree'),
                self.stage_selection)
        self.action_apply_selection.setIcon(qtutils.apply_icon())

        model.add_observer(model.message_diff_text_changed, self._emit_text)

        self.connect(self, SIGNAL('copyAvailable(bool)'),
                     self.enable_selection_actions)

        self.connect(self, SIGNAL('set_text'), self.setPlainText)

    def _emit_text(self, text):
        self.emit(SIGNAL('set_text'), text)

    def _update_diff_opts(self):
        space_at_eol = self.diff_ignore_space_at_eol_action.isChecked()
        space_change = self.diff_ignore_space_change_action.isChecked()
        all_space = self.diff_ignore_all_space_action.isChecked()
        function_context = self.diff_function_context_action.isChecked()

        gitcmds.update_diff_overrides(space_at_eol,
                                      space_change,
                                      all_space,
                                      function_context)
        self.emit(SIGNAL('diff_options_updated()'))

    # Qt overrides
    def contextMenuEvent(self, event):
        """Create the context menu for the diff display."""
        menu = QtGui.QMenu(self)
        s = selection.selection()
        filename = selection.filename()

        if self.model.stageable():
            if s.modified and s.modified[0] in main.model().submodules:
                action = menu.addAction(qtutils.icon('add.svg'),
                                        cmds.Stage.name(),
                                        cmds.run(cmds.Stage, s.modified))
                action.setShortcut(cmds.Stage.SHORTCUT)
                menu.addAction(qtutils.git_icon(),
                               N_('Launch git-cola'),
                               cmds.run(cmds.OpenRepo,
                                        core.abspath(s.modified[0])))
            elif s.modified:
                action = menu.addAction(qtutils.icon('add.svg'),
                                        N_('Stage Section'),
                                        self.stage_section)
                action.setShortcut(Qt.Key_H)
                menu.addAction(self.action_stage_selection)
                menu.addSeparator()
                menu.addAction(qtutils.icon('undo.svg'),
                               N_('Revert Section...'),
                               self.revert_section)
                menu.addAction(self.action_revert_selection)

        if self.model.unstageable():
            if s.staged and s.staged[0] in main.model().submodules:
                action = menu.addAction(qtutils.icon('remove.svg'),
                                        cmds.Unstage.name(),
                                        cmds.do(cmds.Unstage, s.staged))
                action.setShortcut(cmds.Unstage.SHORTCUT)
                menu.addAction(qtutils.git_icon(),
                               N_('Launch git-cola'),
                               cmds.do(cmds.OpenRepo,
                                       core.abspath(s.staged[0])))
            elif s.staged:
                action = menu.addAction(qtutils.icon('remove.svg'),
                                        N_('Unstage Section'),
                                        self.unstage_section)
                action.setShortcut(Qt.Key_H)
                menu.addAction(self.action_unstage_selection)

        if self.model.stageable() or self.model.unstageable():
            # Do not show the "edit" action when the file does not exist.
            # Untracked files exist by definition.
            if filename and core.exists(filename):
                menu.addSeparator()
                menu.addAction(self.launch_editor)

            # Removed files can still be diffed.
            menu.addAction(self.launch_difftool)

        menu.addSeparator()
        action = menu.addAction(qtutils.icon('edit-copy.svg'),
                                N_('Copy'), self.copy)
        action.setShortcut(QtGui.QKeySequence.Copy)

        action = menu.addAction(qtutils.icon('edit-select-all.svg'),
                                N_('Select All'), self.selectAll)
        action.setShortcut(QtGui.QKeySequence.SelectAll)
        menu.exec_(self.mapToGlobal(event.pos()))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            # Intercept the Control modifier to not resize the text
            # when doing control+mousewheel
            event.accept()
            event = QtGui.QWheelEvent(event.pos(), event.delta(),
                                      Qt.NoButton,
                                      Qt.NoModifier,
                                      event.orientation())

        return DiffTextEdit.wheelEvent(self, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Intercept right-click to move the cursor to the current position.
            # setTextCursor() clears the selection so this is only done when
            # nothing is selected.
            _, selection_text = self.offset_and_selection()
            if not selection_text:
                cursor = self.cursorForPosition(event.pos())
                self.setTextCursor(cursor)

        return DiffTextEdit.mousePressEvent(self, event)

    def setPlainText(self, text):
        """setPlainText(str) while retaining scrollbar positions"""
        mode = self.model.mode
        highlight = (mode != self.model.mode_none and
                     mode != self.model.mode_untracked)
        self.highlighter.set_enabled(highlight)

        scrollbar = self.verticalScrollBar()
        if scrollbar:
            scrollvalue = scrollbar.value()
        else:
            scrollvalue = None

        if text is None:
            return

        offset, selection_text = self.offset_and_selection()
        old_text = ustr(self.toPlainText())

        DiffTextEdit.setPlainText(self, text)

        # If the old selection exists in the new text then
        # re-select it.
        if selection_text and selection_text in text:
            idx = text.index(selection_text)
            cursor = self.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx + len(selection_text),
                               QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)

        # Otherwise, if the text is identical and there
        # is no selection then restore the cursor position.
        elif text == old_text:
            cursor = self.textCursor()
            cursor.setPosition(offset)
            self.setTextCursor(cursor)

        if scrollbar and scrollvalue is not None:
            scrollbar.setValue(scrollvalue)

    def offset_and_selection(self):
        cursor = self.textCursor()
        offset = cursor.position()
        selection_text = ustr(cursor.selection().toPlainText())
        return offset, selection_text

    # Mutators
    def enable_selection_actions(self, enabled):
        self.action_apply_selection.setEnabled(enabled)
        self.action_revert_selection.setEnabled(enabled)
        self.action_unstage_selection.setEnabled(enabled)
        self.action_stage_selection.setEnabled(enabled)

    def apply_section(self):
        s = selection.single_selection()
        if self.model.stageable() and s.modified:
            self.stage_section()
        elif self.model.unstageable():
            self.unstage_section()

    def apply_selection(self):
        s = selection.single_selection()
        if self.model.stageable() and s.modified:
            self.stage_selection()
        elif self.model.unstageable():
            self.unstage_selection()

    def stage_section(self):
        """Stage a specific section."""
        self.process_diff_selection(staged=False)

    def stage_selection(self):
        """Stage selected lines."""
        self.process_diff_selection(staged=False, selected=True)

    def unstage_section(self, cached=True):
        """Unstage a section."""
        self.process_diff_selection(staged=True)

    def unstage_selection(self):
        """Unstage selected lines."""
        self.process_diff_selection(staged=True, selected=True)

    def revert_section(self):
        """Destructively remove a section from a worktree file."""
        if not qtutils.confirm(N_('Revert Section?'),
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               N_('Revert Section'),
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True)

    def revert_selection(self):
        """Destructively check out content for the selected file from $head."""
        if not qtutils.confirm(N_('Revert Selected Lines?'),
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               N_('Revert Selected Lines'),
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True, selected=True)

    def process_diff_selection(self, selected=False,
                               staged=True, apply_to_worktree=False,
                               reverse=False):
        """Implement un/staging of selected lines or sections."""
        if selection.selection_model().is_empty():
            return
        offset, selection_text = self.offset_and_selection()
        cmds.do(cmds.ApplyDiffSelection,
                staged, selected, offset, selection_text, apply_to_worktree)



class DiffWidget(QtGui.QWidget):

    def __init__(self, notifier, parent):
        QtGui.QWidget.__init__(self, parent)

        author_font = QtGui.QFont(self.font())
        author_font.setPointSize(int(author_font.pointSize() * 1.1))

        summary_font = QtGui.QFont(author_font)
        summary_font.setWeight(QtGui.QFont.Bold)

        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Minimum)

        self.gravatar_label = gravatar.GravatarLabel()

        self.author_label = TextLabel()
        self.author_label.setTextFormat(Qt.RichText)
        self.author_label.setFont(author_font)
        self.author_label.setSizePolicy(policy)
        self.author_label.setAlignment(Qt.AlignBottom)
        self.author_label.elide()

        self.summary_label = TextLabel()
        self.summary_label.setTextFormat(Qt.PlainText)
        self.summary_label.setFont(summary_font)
        self.summary_label.setSizePolicy(policy)
        self.summary_label.setAlignment(Qt.AlignTop)
        self.summary_label.elide()

        self.sha1_label = TextLabel()
        self.sha1_label.setTextFormat(Qt.PlainText)
        self.sha1_label.setSizePolicy(policy)
        self.sha1_label.setAlignment(Qt.AlignTop)
        self.sha1_label.elide()

        self.diff = DiffTextEdit(self, whitespace=False)
        self.tasks = set()
        self.reflector = QtCore.QObject(self)

        self.info_layout = QtGui.QVBoxLayout()
        self.info_layout.setMargin(defs.no_margin)
        self.info_layout.setSpacing(defs.no_spacing)
        self.info_layout.addWidget(self.author_label)
        self.info_layout.addWidget(self.summary_label)
        self.info_layout.addWidget(self.sha1_label)

        self.logo_layout = QtGui.QHBoxLayout()
        self.logo_layout.setContentsMargins(defs.margin, 0, defs.margin, 0)
        self.logo_layout.setSpacing(defs.button_spacing)
        self.logo_layout.addWidget(self.gravatar_label)
        self.logo_layout.addLayout(self.info_layout)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.no_margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addLayout(self.logo_layout)
        self.main_layout.addWidget(self.diff)
        self.setLayout(self.main_layout)

        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)
        notifier.add_observer(FILES_SELECTED, self.files_selected)
        self.connect(self.reflector, SIGNAL('diff'), self.diff.setText)
        self.connect(self.reflector, SIGNAL('task_done'), self.task_done)

    def task_done(self, task):
        try:
            self.tasks.remove(task)
        except:
            pass

    def set_diff_sha1(self, sha1, filename=None):
        self.diff.setText('+++ ' + N_('Loading...'))
        task = DiffInfoTask(sha1, self.reflector, filename=filename)
        self.tasks.add(task)
        QtCore.QThreadPool.globalInstance().start(task)

    def commits_selected(self, commits):
        if len(commits) != 1:
            return
        commit = commits[0]
        self.sha1 = commit.sha1

        email = commit.email or ''
        summary = commit.summary or ''
        author = commit.author or ''

        template_args = {
                'author': author,
                'email': email,
                'summary': summary
        }

        author_text = ("""%(author)s &lt;"""
                       """<a href="mailto:%(email)s">"""
                       """%(email)s</a>&gt;"""
                       % template_args)

        author_template = '%(author)s <%(email)s>' % template_args
        self.author_label.set_template(author_text, author_template)
        self.summary_label.set_text(summary)
        self.sha1_label.set_text(self.sha1)

        self.set_diff_sha1(self.sha1)
        self.gravatar_label.set_email(email)

    def files_selected(self, filenames):
        if not filenames:
            return
        self.set_diff_sha1(self.sha1, filenames[0])


class TextLabel(QtGui.QLabel):

    def __init__(self, parent=None):
        QtGui.QLabel.__init__(self, parent)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse |
                                     Qt.LinksAccessibleByMouse)
        self._display = ''
        self._template = ''
        self._text = ''
        self._elide = False
        self._metrics = QtGui.QFontMetrics(self.font())
        self.setOpenExternalLinks(True)

    def elide(self):
        self._elide = True

    def set_text(self, text):
        self.set_template(text, text)

    def set_template(self, text, template):
        self._display = text
        self._text = text
        self._template = template
        self.update_text(self.width())
        self.setText(self._display)

    def update_text(self, width):
        self._display = self._text
        if not self._elide:
            return
        text = self._metrics.elidedText(self._template,
                                        Qt.ElideRight, width-2)
        if ustr(text) != self._template:
            self._display = text

    # Qt overrides
    def setFont(self, font):
        self._metrics = QtGui.QFontMetrics(font)
        QtGui.QLabel.setFont(self, font)

    def resizeEvent(self, event):
        if self._elide:
            self.update_text(event.size().width())
            block = self.blockSignals(True)
            self.setText(self._display)
            self.blockSignals(block)
        QtGui.QLabel.resizeEvent(self, event)


class DiffInfoTask(QtCore.QRunnable):

    def __init__(self, sha1, reflector, filename=None):
        QtCore.QRunnable.__init__(self)
        self.sha1 = sha1
        self.reflector = reflector
        self.filename = filename

    def run(self):
        diff = gitcmds.diff_info(self.sha1, filename=self.filename)
        self.reflector.emit(SIGNAL('diff'), diff)

########NEW FILE########
__FILENAME__ = editremotes
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola.git import git
from cola.git import STDOUT
from cola.i18n import N_
from cola.models import main
from cola.widgets import defs
from cola.widgets import text
from cola.compat import ustr


def remote_editor():
    view= new_remote_editor(parent=qtutils.active_window())
    view.show()
    view.raise_()
    return view


def new_remote_editor(parent=None):
    return RemoteEditor(parent=parent)


class RemoteEditor(QtGui.QDialog):
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle(N_('Edit Remotes'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.default_hint = N_(''
            'Add and remove remote repositories using the \n'
            'Add(+) and Delete(-) buttons on the left-hand side.\n'
            '\n'
            'Remotes can be renamed by selecting one from the list\n'
            'and pressing "enter", or by double-clicking.')

        self.remote_list = []
        self.remotes = QtGui.QListWidget()
        self.remotes.setToolTip(N_(
            'Remote git repositories - double-click to rename'))

        self.info = text.HintedTextView(self.default_hint, self)
        font = self.info.font()
        metrics = QtGui.QFontMetrics(font)
        width = metrics.width('_' * 72)
        height = metrics.height() * 13
        self.info.setMinimumWidth(width)
        self.info.setMinimumHeight(height)
        self.info_thread = RemoteInfoThread(self)

        self.add_btn = QtGui.QToolButton()
        self.add_btn.setIcon(qtutils.add_icon())
        self.add_btn.setToolTip(N_('Add new remote git repository'))

        self.refresh_btn = QtGui.QToolButton()
        self.refresh_btn.setIcon(qtutils.reload_icon())
        self.refresh_btn.setToolTip(N_('Refresh'))

        self.delete_btn = QtGui.QToolButton()
        self.delete_btn.setIcon(qtutils.remove_icon())
        self.delete_btn.setToolTip(N_('Delete remote'))

        self.close_btn = QtGui.QPushButton(N_('Close'))

        self._top_layout = QtGui.QSplitter()
        self._top_layout.setOrientation(Qt.Horizontal)
        self._top_layout.setHandleWidth(defs.handle_width)
        self._top_layout.addWidget(self.remotes)
        self._top_layout.addWidget(self.info)
        width = self._top_layout.width()
        self._top_layout.setSizes([width//4, width*3//4])

        self._button_layout = QtGui.QHBoxLayout()
        self._button_layout.addWidget(self.add_btn)
        self._button_layout.addWidget(self.delete_btn)
        self._button_layout.addWidget(self.refresh_btn)
        self._button_layout.addStretch()
        self._button_layout.addWidget(self.close_btn)

        self._layout = QtGui.QVBoxLayout()
        self._layout.setMargin(defs.margin)
        self._layout.setSpacing(defs.spacing)
        self._layout.addWidget(self._top_layout)
        self._layout.addLayout(self._button_layout)
        self.setLayout(self._layout)

        self.refresh()

        qtutils.connect_button(self.add_btn, self.add)
        qtutils.connect_button(self.delete_btn, self.delete)
        qtutils.connect_button(self.refresh_btn, self.refresh)
        qtutils.connect_button(self.close_btn, self.close)

        self.connect(self.info_thread, SIGNAL('info'),
                     self.info.set_value)

        self.connect(self.remotes,
                     SIGNAL('itemChanged(QListWidgetItem*)'),
                     self.remote_renamed)

        self.connect(self.remotes, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)

    def refresh(self):
        remotes = git.remote()[STDOUT].splitlines()
        self.remotes.clear()
        self.remotes.addItems(remotes)
        self.remote_list = remotes
        self.info.set_hint(self.default_hint)
        self.info.enable_hint(True)
        for idx, r in enumerate(remotes):
            item = self.remotes.item(idx)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

    def add(self):
        widget = AddRemoteWidget(self)
        if not widget.add_remote():
            return
        name = widget.name.value()
        url = widget.url.value()
        status, out, err = git.remote('add', name, url)
        if status != 0:
            qtutils.critical(N_('Error creating remote "%s"') % name,
                             out + err)
        self.refresh()

    def delete(self):
        remote = qtutils.selected_item(self.remotes, self.remote_list)
        if remote is None:
            return

        title = N_('Delete Remote')
        question = N_('Delete remote?')
        info = N_('Delete remote "%s"') % remote
        ok_btn = N_('Delete')
        if not qtutils.confirm(title, question, info, ok_btn):
            return

        status, out, err = git.remote('rm', remote)
        if status != 0:
            qtutils.critical(N_('Error deleting remote "%s"') % remote,
                             out + err)
        main.model().update_status()
        self.refresh()

    def remote_renamed(self, item):
        idx = self.remotes.row(item)
        if idx < 0:
            return
        if idx >= len(self.remote_list):
            return

        old_name = self.remote_list[idx]
        new_name = ustr(item.text())
        if new_name == old_name:
            return
        if not new_name:
            item.setText(old_name)
            return

        title = N_('Rename Remote')
        question = N_('Rename remote?')
        info = (N_('Rename remote "%(current)s" to "%(new)s"?') %
                dict(current=old_name, new=new_name))
        ok_btn = N_('Rename')

        if qtutils.confirm(title, question, info, ok_btn):
            status, out, err = git.remote('rename', old_name, new_name)
            if status == 0:
                self.remote_list[idx] = new_name
        else:
            item.setText(old_name)

    def selection_changed(self):
        remote = qtutils.selected_item(self.remotes, self.remote_list)
        if remote is None:
            return
        self.info.set_hint(N_('Gathering info for "%s"...') % remote)
        self.info.enable_hint(True)

        self.info_thread.remote = remote
        self.info_thread.start()


class RemoteInfoThread(QtCore.QThread):
    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.remote = None

    def run(self):
        remote = self.remote
        if remote is None:
            return
        status, out, err = git.remote('show', remote)
        # This call takes a long time and we may have selected a
        # different remote...
        if remote == self.remote:
            self.emit(SIGNAL('info'), out + err)
        else:
            self.run()


class AddRemoteWidget(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowModality(Qt.WindowModal)

        self.add_btn = QtGui.QPushButton(N_('Add Remote'))
        self.add_btn.setIcon(qtutils.apply_icon())

        self.cancel_btn = QtGui.QPushButton(N_('Cancel'))

        def lineedit(hint):
            widget = text.HintedLineEdit(hint)
            widget.enable_hint(True)
            metrics = QtGui.QFontMetrics(widget.font())
            widget.setMinimumWidth(metrics.width('_' * 32))
            return widget

        self.setWindowTitle(N_('Add remote'))
        self.name = lineedit(N_('Name for the new remote'))
        self.url = lineedit('git://git.example.com/repo.git')

        self._form = QtGui.QFormLayout()
        self._form.setMargin(defs.margin)
        self._form.setSpacing(defs.spacing)
        self._form.addRow(N_('Name'), self.name)
        self._form.addRow(N_('URL'), self.url)

        self._btn_layout = QtGui.QHBoxLayout()
        self._btn_layout.setMargin(0)
        self._btn_layout.setSpacing(defs.button_spacing)
        self._btn_layout.addStretch()
        self._btn_layout.addWidget(self.add_btn)
        self._btn_layout.addWidget(self.cancel_btn)

        self._layout = QtGui.QVBoxLayout()
        self._layout.setMargin(defs.margin)
        self._layout.setSpacing(defs.margin)
        self._layout.addLayout(self._form)
        self._layout.addLayout(self._btn_layout)
        self.setLayout(self._layout)

        self.connect(self.name, SIGNAL('textChanged(QString)'),
                     self.validate)

        self.connect(self.url, SIGNAL('textChanged(QString)'),
                     self.validate)

        self.add_btn.setEnabled(False)

        qtutils.connect_button(self.add_btn, self.accept)
        qtutils.connect_button(self.cancel_btn, self.reject)

    def validate(self, dummy_text):
        name = self.name.value()
        url = self.url.value()
        self.add_btn.setEnabled(bool(name) and bool(url))

    def add_remote(self):
        self.show()
        self.raise_()
        return self.exec_() == QtGui.QDialog.Accepted

########NEW FILE########
__FILENAME__ = filelist
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.i18n import N_
from cola.git import git
from cola.widgets.standard import TreeWidget
from cola.widgets.diff import COMMITS_SELECTED
from cola.widgets.diff import FILES_SELECTED


class FileWidget(TreeWidget):

    def __init__(self, notifier, parent):
        TreeWidget.__init__(self, parent)
        self.notifier = notifier
        self.setHeaderLabels([N_('Filename'), N_('Additions'), N_('Deletions')])
        notifier.add_observer(COMMITS_SELECTED, self.commits_selected)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.selection_changed)

    def selection_changed(self):
        items = self.selected_items()
        self.notifier.notify_observers(FILES_SELECTED,
                                       [i.file_name for i in items])

    def commits_selected(self, commits):
        if not commits:
            return
        commit = commits[0]
        sha1 = commit.sha1
        status, out, err = git.show(sha1,
                                    numstat=True, oneline=True, no_renames=True)
        if status == 0:
            paths = [f for f in out.splitlines() if f]
            if paths:
                paths = paths[1:]
        else:
            paths = []
        self.list_files(paths)

    def list_files(self, files_log):
        self.clear()
        if not files_log:
            return
        files = []
        for f in files_log:
            item = FileTreeWidgetItem(f)
            files.append(item)
        self.insertTopLevelItems(0, files)

    def adjust_columns(self):
        width = self.width()-20
        zero = width*2//3
        onetwo = width//6
        self.setColumnWidth(0, zero)
        self.setColumnWidth(1, onetwo)
        self.setColumnWidth(2, onetwo)

    def show(self):
        self.adjust_columns()

    def resizeEvent(self, e):
        self.adjust_columns()


class FileTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, file_log, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)
        texts = file_log.split('\t')
        self.file_name = texts[2]
        self.setText(0, self.file_name) # file name
        self.setText(1, texts[0]) # addition
        self.setText(2, texts[1]) # deletion

########NEW FILE########
__FILENAME__ = grep
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import utils
from cola import qtutils
from cola.cmds import do
from cola.git import git
from cola.i18n import N_
from cola.qtutils import diff_font
from cola.widgets import defs
from cola.widgets.standard import Dialog
from cola.widgets.text import HintedTextView, HintedLineEdit
from cola.compat import ustr


def grep():
    """Prompt and use 'git grep' to find the content."""
    widget = new_grep(parent=qtutils.active_window())
    widget.show()
    widget.raise_()
    return widget


def new_grep(text=None, parent=None):
    widget = Grep(parent=parent)
    if text:
        widget.search_for(text)
    return widget


def goto_grep(line):
    """Called when Search -> Grep's right-click 'goto' action."""
    filename, line_number, contents = line.split(':', 2)
    do(cmds.Edit, [filename], line_number=line_number)


class GrepThread(QtCore.QThread):

    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.query = None
        self.shell = False
        self.regexp_mode = '--basic-regexp'

    def run(self):
        if self.query is None:
            return
        query = self.query
        if self.shell:
            args = utils.shell_split(query)
        else:
            args = [query]
        status, out, err = git.grep(self.regexp_mode, n=True, *args)
        if query == self.query:
            self.emit(SIGNAL('result'), status, out, err)
        else:
            self.run()


class Grep(Dialog):

    def __init__(self, parent=None):
        Dialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Search'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.input_label = QtGui.QLabel('git grep')
        self.input_label.setFont(diff_font())

        self.input_txt = HintedLineEdit(N_('command-line arguments'), self)
        self.input_txt.enable_hint(True)

        self.regexp_combo = combo = QtGui.QComboBox()
        combo.setToolTip(N_('Choose the "git grep" regular expression mode'))
        items = [N_('Basic Regexp'), N_('Extended Regexp'), N_('Fixed String')]
        combo.addItems(items)
        combo.setCurrentIndex(0)
        combo.setEditable(False)
        combo.setItemData(0,
                N_('Search using a POSIX basic regular expression'),
                Qt.ToolTipRole)
        combo.setItemData(1,
                N_('Search using a POSIX extended regular expression'),
                Qt.ToolTipRole)
        combo.setItemData(2,
                N_('Search for a fixed string'),
                Qt.ToolTipRole)
        combo.setItemData(0, '--basic-regexp', Qt.UserRole)
        combo.setItemData(1, '--extended-regexp', Qt.UserRole)
        combo.setItemData(2, '--fixed-strings', Qt.UserRole)

        self.result_txt = GrepTextView(N_('grep result...'), self)
        self.result_txt.enable_hint(True)

        self.edit_button = QtGui.QPushButton(N_('Edit'))
        self.edit_button.setIcon(qtutils.open_file_icon())
        self.edit_button.setEnabled(False)
        self.edit_button.setShortcut(cmds.Edit.SHORTCUT)

        self.refresh_button = QtGui.QPushButton(N_('Refresh'))
        self.refresh_button.setIcon(qtutils.reload_icon())
        self.refresh_button.setShortcut(QtGui.QKeySequence.Refresh)

        self.shell_checkbox = QtGui.QCheckBox(N_('Shell arguments'))
        self.shell_checkbox.setToolTip(
                N_('Parse arguments using a shell.\n'
                   'Queries with spaces will require "double quotes".'))
        self.shell_checkbox.setChecked(False)

        self.close_button = QtGui.QPushButton(N_('Close'))

        self.input_layout = QtGui.QHBoxLayout()
        self.input_layout.setMargin(0)
        self.input_layout.setSpacing(defs.button_spacing)

        self.bottom_layout = QtGui.QHBoxLayout()
        self.bottom_layout.setMargin(0)
        self.bottom_layout.setSpacing(defs.button_spacing)

        self.mainlayout = QtGui.QVBoxLayout()
        self.mainlayout.setMargin(defs.margin)
        self.mainlayout.setSpacing(defs.spacing)

        self.input_layout.addWidget(self.input_label)
        self.input_layout.addWidget(self.input_txt)
        self.input_layout.addWidget(self.regexp_combo)

        self.bottom_layout.addWidget(self.edit_button)
        self.bottom_layout.addWidget(self.refresh_button)
        self.bottom_layout.addWidget(self.shell_checkbox)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.close_button)

        self.mainlayout.addLayout(self.input_layout)
        self.mainlayout.addWidget(self.result_txt)
        self.mainlayout.addLayout(self.bottom_layout)
        self.setLayout(self.mainlayout)

        self.grep_thread = GrepThread(self)

        self.connect(self.grep_thread, SIGNAL('result'),
                     self.process_result)

        self.connect(self.input_txt, SIGNAL('textChanged(QString)'),
                     lambda s: self.search())

        self.connect(self.regexp_combo, SIGNAL('currentIndexChanged(int)'),
                     lambda x: self.search())

        self.connect(self.result_txt, SIGNAL('leave()'),
                     lambda: self.input_txt.setFocus())

        qtutils.add_action(self.input_txt, 'FocusResults',
                           lambda: self.result_txt.setFocus(),
                           Qt.Key_Down, Qt.Key_Enter, Qt.Key_Return)
        qtutils.add_action(self, 'FocusSearch',
                           lambda: self.input_txt.setFocus(),
                           'Ctrl+l')
        qtutils.connect_button(self.edit_button, self.edit)
        qtutils.connect_button(self.refresh_button, self.search)
        qtutils.connect_toggle(self.shell_checkbox, lambda x: self.search())
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        if not self.restore_state():
            self.resize(666, 420)

    def done(self, exit_code):
        self.save_state()
        return Dialog.done(self, exit_code)

    def regexp_mode(self):
        idx = self.regexp_combo.currentIndex()
        data = self.regexp_combo.itemData(idx, Qt.UserRole).toPyObject()
        return ustr(data)

    def search(self):
        self.edit_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        query = self.input_txt.value()
        if len(query) < 2:
            self.result_txt.set_value('')
            return
        self.grep_thread.query = query
        self.grep_thread.shell = self.shell_checkbox.isChecked()
        self.grep_thread.regexp_mode = self.regexp_mode()
        self.grep_thread.start()

    def search_for(self, txt):
        self.input_txt.set_value(txt)
        self.search()

    def text_scroll(self):
        scrollbar = self.result_txt.verticalScrollBar()
        if scrollbar:
            return scrollbar.value()
        return None

    def set_text_scroll(self, scroll):
        scrollbar = self.result_txt.verticalScrollBar()
        if scrollbar and scroll is not None:
            scrollbar.setValue(scroll)

    def text_offset(self):
        return self.result_txt.textCursor().position()

    def set_text_offset(self, offset):
        cursor = self.result_txt.textCursor()
        cursor.setPosition(offset)
        self.result_txt.setTextCursor(cursor)

    def process_result(self, status, out, err):

        if status == 0:
            value = out + err
        elif out + err:
            value = 'git grep: ' + out + err
        else:
            value = ''

        # save scrollbar and text cursor
        scroll = self.text_scroll()
        offset = min(len(value), self.text_offset())

        self.result_txt.set_value(value)
        # restore
        self.set_text_scroll(scroll)
        self.set_text_offset(offset)

        self.edit_button.setEnabled(status == 0)
        self.refresh_button.setEnabled(status == 0)

    def edit(self):
        goto_grep(self.result_txt.selected_line()),


class GrepTextView(HintedTextView):

    def __init__(self, hint, parent):
        HintedTextView.__init__(self, hint, parent)
        self.goto_action = qtutils.add_action(self, 'Launch Editor', self.edit)
        self.goto_action.setShortcut(cmds.Edit.SHORTCUT)

        qtutils.add_action(self, 'Up',
                lambda: self.move(QtGui.QTextCursor.Up),
                Qt.Key_K)

        qtutils.add_action(self, 'Down',
                lambda: self.move(QtGui.QTextCursor.Down),
                Qt.Key_J)

        qtutils.add_action(self, 'Left',
                lambda: self.move(QtGui.QTextCursor.Left),
                Qt.Key_H)

        qtutils.add_action(self, 'Right',
                lambda: self.move(QtGui.QTextCursor.Right),
                Qt.Key_L)

        qtutils.add_action(self, 'StartOfLine',
                lambda: self.move(QtGui.QTextCursor.StartOfLine),
                Qt.Key_0)

        qtutils.add_action(self, 'EndOfLine',
                lambda: self.move(QtGui.QTextCursor.EndOfLine),
                Qt.Key_Dollar)

        qtutils.add_action(self, 'WordLeft',
                lambda: self.move(QtGui.QTextCursor.WordLeft),
                Qt.Key_B)

        qtutils.add_action(self, 'WordRight',
                lambda: self.move(QtGui.QTextCursor.WordRight),
                Qt.Key_W)

        qtutils.add_action(self, 'PageUp',
                lambda: self.page(-self.height()//2),
                'Shift+Space')

        qtutils.add_action(self, 'PageDown',
                lambda: self.page(self.height()//2),
                Qt.Key_Space)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        menu.addSeparator()
        menu.addAction(self.goto_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def edit(self):
        goto_grep(self.selected_line())

    def page(self, offset):
        rect = self.cursorRect()
        x = rect.x()
        y = rect.y() + offset
        new_cursor = self.cursorForPosition(QtCore.QPoint(x, y))
        if new_cursor is not None:
            self.set_text_cursor(new_cursor)

    def set_text_cursor(self, cursor):
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.viewport().update()

    def move(self, direction):
        cursor = self.textCursor()
        if cursor.movePosition(direction):
            self.set_text_cursor(cursor)

    def paintEvent(self, event):
        HintedTextView.paintEvent(self, event)
        if self.hasFocus():
            # Qt doesn't redraw the cursor when using movePosition().
            # So.. draw our own cursor.
            rect = self.cursorRect()
            painter = QtGui.QPainter(self.viewport())
            painter.fillRect(rect, Qt.SolidPattern)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            position = cursor.position()
            if position == 0 and not cursor.hasSelection():
                # The cursor is at the beginning of the line.
                # If we have selection then simply reset the cursor.
                # Otherwise, emit a signal so that the parent can
                # change focus.
                self.emit(SIGNAL('leave()'))
        return HintedTextView.keyPressEvent(self, event)

########NEW FILE########
__FILENAME__ = highlighter
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore, QtGui

from cola.compat import ustr

have_pygments = True
try:
    from pygments.styles import get_style_by_name
    from pygments import lex
    from pygments.util import ClassNotFound
    from pygments.lexers import get_lexer_for_filename
except ImportError:
    have_pygments = False

def highlight_document(edit, filename):
    doc = edit.document()

    if not have_pygments:
        return

    try:
        lexer = get_lexer_for_filename(filename, stripnl=False)
    except ClassNotFound:
        return

    style = get_style_by_name("default")

    font = doc.defaultFont()
    base_format = QtGui.QTextCharFormat()
    base_format.setFont(font)
    token_formats = {}

    window = edit.window()
    if hasattr(window, "processEvents"):
        processEvents = window.processEvents
    else:
        processEvents = QtCore.QCoreApplication.processEvents

    def get_token_format(token):
        if token in token_formats:
            return token_formats[token]

        if token.parent:
            parent_format = get_token_format(token.parent)
        else:
            parent_format = base_format

        format = QtGui.QTextCharFormat(parent_format)
        font = format.font()
        if style.styles_token(token):
            tstyle = style.style_for_token(token)
            if tstyle['color']:
                format.setForeground (QtGui.QColor("#"+tstyle['color']))
            if tstyle['bold']: font.setWeight(QtGui.QFont.Bold)
            if tstyle['italic']: font.setItalic (True)
            if tstyle['underline']: format.setFontUnderline(True)
            if tstyle['bgcolor']: format.setBackground (QtGui.QColor("#"+tstyle['bgcolor']))
            # No way to set this for a QTextCharFormat
            #if tstyle['border']: format.
        token_formats[token] = format
        return format

    text = ustr(doc.toPlainText())

    block_count = 0
    block = doc.firstBlock()
    assert(isinstance(block, QtGui.QTextBlock))
    block_pos = 0
    block_len = block.length()
    block_formats = []

    for token, ttext in lex(text, lexer):
        format_len = len(ttext)
        format = get_token_format(token)
        while format_len > 0:
            format_range = QtGui.QTextLayout.FormatRange()
            format_range.start = block_pos
            format_range.length = min(format_len, block_len)
            format_range.format = format
            block_formats.append(format_range)
            block_len -= format_range.length
            format_len -= format_range.length
            block_pos += format_range.length
            if block_len == 0:
                block.layout().setAdditionalFormats(block_formats)
                doc.markContentsDirty(block.position(), block.length())
                block = block.next()
                block_pos = 0
                block_len = block.length()
                block_formats = []

                block_count += 1
                if block_count % 100 == 0:
                    processEvents()


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)

    python = QtGui.QPlainTextEdit()
    f = open(__file__, 'r')
    python.setPlainText(f.read())
    f.close()

    python.setWindowTitle('python')
    python.show()
    highlight_document(python, __file__)

    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = log
from __future__ import division, absolute_import, unicode_literals

import time

from PyQt4 import QtGui

from cola.i18n import N_
from cola.widgets.text import MonoTextView


class LogWidget(QtGui.QWidget):
    """A simple dialog to display command logs."""
    def __init__(self, parent=None, output=None):
        QtGui.QWidget.__init__(self, parent)

        self._layout = QtGui.QVBoxLayout(self)
        self._layout.setMargin(0)

        self.output_text = MonoTextView(self)
        self._layout.addWidget(self.output_text)
        if output:
            self.set_output(output)

    def clear(self):
        self.output_text.clear()

    def set_output(self, output):
        self.output_text.setText(output)

    def log_status(self, status, out, err=None):
        msg = out
        if err:
            msg += '\n' + err
        if status != 0:
            msg += '\n'
            msg += N_('exit code %s') % status
        self.log(msg)

    def log(self, msg):
        if not msg:
            return
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        text = self.output_text
        cursor.insertText(time.asctime() + '\n')
        for line in msg.splitlines():
            cursor.insertText(line + '\n')
        cursor.insertText('\n')
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)

########NEW FILE########
__FILENAME__ = main
"""This view provides the main git-cola user interface.
"""
from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import gitcmds
from cola import guicmds
from cola import gitcfg
from cola import qtutils
from cola import resources
from cola import utils
from cola import version
from cola.compat import unichr
from cola.git import git
from cola.git import STDOUT
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import prefs
from cola.qtutils import add_action
from cola.qtutils import add_action_bool
from cola.qtutils import connect_action
from cola.qtutils import connect_action_bool
from cola.qtutils import create_dock
from cola.qtutils import create_menu
from cola.settings import Settings
from cola.widgets import action
from cola.widgets import cfgactions
from cola.widgets import editremotes
from cola.widgets import merge
from cola.widgets import remote
from cola.widgets.about import launch_about_dialog
from cola.widgets.about import show_shortcuts
from cola.widgets.archive import GitArchiveDialog
from cola.widgets.bookmarks import manage_bookmarks
from cola.widgets.bookmarks import BookmarksWidget
from cola.widgets.browse import worktree_browser
from cola.widgets.browse import worktree_browser_widget
from cola.widgets.commitmsg import CommitMessageEditor
from cola.widgets.compare import compare_branches
from cola.widgets.createtag import create_tag
from cola.widgets.createbranch import create_new_branch
from cola.widgets.dag import git_dag
from cola.widgets.diff import DiffEditor
from cola.widgets.grep import grep
from cola.widgets.log import LogWidget
from cola.widgets.patch import apply_patches
from cola.widgets.prefs import preferences
from cola.widgets.recent import browse_recent_files
from cola.widgets.status import StatusWidget
from cola.widgets.search import search
from cola.widgets.standard import MainWindow
from cola.widgets.stash import stash


class MainView(MainWindow):

    def __init__(self, model, parent=None, settings=None):
        MainWindow.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)

        # Default size; this is thrown out when save/restore is used
        self.model = model
        self.settings = settings
        self.prefs_model = prefs_model = prefs.PreferencesModel()

        # The widget version is used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self.widget_version = 2

        # Keeps track of merge messages we've seen
        self.merge_message_hash = ''

        cfg = gitcfg.instance()
        self.browser_dockable = (cfg.get('cola.browserdockable') or
                                 cfg.get('cola.classicdockable'))
        if self.browser_dockable:
            self.browserdockwidget = create_dock(N_('Browser'), self)
            self.browserwidget = worktree_browser_widget(self)
            self.browserdockwidget.setWidget(self.browserwidget)

        # "Actions" widget
        self.actionsdockwidget = create_dock(N_('Actions'), self)
        self.actionsdockwidgetcontents = action.ActionButtons(self)
        self.actionsdockwidget.setWidget(self.actionsdockwidgetcontents)
        self.actionsdockwidget.toggleViewAction().setChecked(False)
        self.actionsdockwidget.hide()

        # "Repository Status" widget
        self.statuswidget = StatusWidget(self)
        self.statusdockwidget = create_dock(N_('Status'), self)
        self.statusdockwidget.setWidget(self.statuswidget)

        # "Switch Repository" widget
        self.bookmarksdockwidget = create_dock(N_('Bookmarks'), self)
        self.bookmarkswidget = BookmarksWidget(parent=self.bookmarksdockwidget)
        self.bookmarksdockwidget.setWidget(self.bookmarkswidget)

        # "Commit Message Editor" widget
        self.position_label = QtGui.QLabel()
        font = qtutils.default_monospace_font()
        font.setPointSize(int(font.pointSize() * 0.8))
        self.position_label.setFont(font)

        # make the position label fixed size to avoid layout issues
        fm = self.position_label.fontMetrics()
        width = fm.width('999:999')
        height = self.position_label.sizeHint().height()
        self.position_label.setFixedSize(width, height)

        self.commitdockwidget = create_dock(N_('Commit'), self)
        titlebar = self.commitdockwidget.titleBarWidget()
        titlebar.add_corner_widget(self.position_label)

        self.commitmsgeditor = CommitMessageEditor(model, self)
        self.commitdockwidget.setWidget(self.commitmsgeditor)

        # "Console" widget
        self.logwidget = LogWidget()
        self.logdockwidget = create_dock(N_('Console'), self)
        self.logdockwidget.setWidget(self.logwidget)
        self.logdockwidget.toggleViewAction().setChecked(False)
        self.logdockwidget.hide()

        # "Diff Viewer" widget
        self.diffdockwidget = create_dock(N_('Diff'), self)
        self.diffeditor = DiffEditor(self.diffdockwidget)
        self.diffdockwidget.setWidget(self.diffeditor)

        # All Actions
        self.unstage_all_action = add_action(self,
                N_('Unstage All'), cmds.run(cmds.UnstageAll))
        self.unstage_all_action.setIcon(qtutils.icon('remove.svg'))

        self.unstage_selected_action = add_action(self,
                N_('Unstage From Commit'), cmds.run(cmds.UnstageSelected))
        self.unstage_selected_action.setIcon(qtutils.icon('remove.svg'))

        self.show_diffstat_action = add_action(self,
                N_('Diffstat'), cmds.run(cmds.Diffstat), 'Alt+D')

        self.stage_modified_action = add_action(self,
                N_('Stage Changed Files To Commit'),
                cmds.run(cmds.StageModified), 'Alt+A')
        self.stage_modified_action.setIcon(qtutils.icon('add.svg'))

        self.stage_untracked_action = add_action(self,
                N_('Stage All Untracked'),
                cmds.run(cmds.StageUntracked), 'Alt+U')
        self.stage_untracked_action.setIcon(qtutils.icon('add.svg'))

        self.apply_patches_action = add_action(self,
                N_('Apply Patches...'), apply_patches)

        self.export_patches_action = add_action(self,
                N_('Export Patches...'), guicmds.export_patches, 'Alt+E')

        self.new_repository_action = add_action(self,
                N_('New Repository...'), guicmds.open_new_repo)
        self.new_repository_action.setIcon(qtutils.new_icon())

        self.preferences_action = add_action(self,
                N_('Preferences'), self.preferences,
                QtGui.QKeySequence.Preferences, 'Ctrl+O')

        self.edit_remotes_action = add_action(self,
                N_('Edit Remotes...'), lambda: editremotes.remote_editor().exec_())
        self.rescan_action = add_action(self,
                cmds.Refresh.name(),
                cmds.run(cmds.Refresh),
                cmds.Refresh.SHORTCUT)
        self.rescan_action.setIcon(qtutils.reload_icon())

        self.browse_recently_modified_action = add_action(self,
                N_('Recently Modified Files...'),
                browse_recent_files, 'Shift+Ctrl+E')

        self.cherry_pick_action = add_action(self,
                N_('Cherry-Pick...'),
                guicmds.cherry_pick, 'Ctrl+P')

        self.load_commitmsg_action = add_action(self,
                N_('Load Commit Message...'), guicmds.load_commitmsg)

        self.save_tarball_action = add_action(self,
                N_('Save As Tarball/Zip...'), self.save_archive)

        self.quit_action = add_action(self,
                N_('Quit'), self.close, 'Ctrl+Q')
        self.manage_bookmarks_action = add_action(self,
                N_('Bookmarks...'), self.manage_bookmarks)
        self.grep_action = add_action(self,
                N_('Grep'), grep, 'Ctrl+G')
        self.merge_local_action = add_action(self,
                N_('Merge...'), merge.local_merge)

        self.merge_abort_action = add_action(self,
                N_('Abort Merge...'), merge.abort_merge)

        self.fetch_action = add_action(self,
                N_('Fetch...'), remote.fetch)
        self.push_action = add_action(self,
                N_('Push...'), remote.push)
        self.pull_action = add_action(self,
                N_('Pull...'), remote.pull)

        self.open_repo_action = add_action(self,
                N_('Open...'), guicmds.open_repo)
        self.open_repo_action.setIcon(qtutils.open_icon())

        self.open_repo_new_action = add_action(self,
                N_('Open in New Window...'), guicmds.open_repo_in_new_window)
        self.open_repo_new_action.setIcon(qtutils.open_icon())

        self.stash_action = add_action(self,
                N_('Stash...'), stash, 'Alt+Shift+S')

        self.clone_repo_action = add_action(self,
                N_('Clone...'), guicmds.clone_repo)
        self.clone_repo_action.setIcon(qtutils.git_icon())

        self.help_docs_action = add_action(self,
                N_('Documentation'), resources.show_html_docs,
                QtGui.QKeySequence.HelpContents)

        self.help_shortcuts_action = add_action(self,
                N_('Keyboard Shortcuts'),
                show_shortcuts,
                QtCore.Qt.Key_Question)

        self.visualize_current_action = add_action(self,
                N_('Visualize Current Branch...'),
                cmds.run(cmds.VisualizeCurrent))
        self.visualize_all_action = add_action(self,
                N_('Visualize All Branches...'),
                cmds.run(cmds.VisualizeAll))
        self.search_commits_action = add_action(self,
                N_('Search...'), search)
        self.browse_branch_action = add_action(self,
                N_('Browse Current Branch...'), guicmds.browse_current)
        self.browse_other_branch_action = add_action(self,
                N_('Browse Other Branch...'), guicmds.browse_other)
        self.load_commitmsg_template_action = add_action(self,
                N_('Get Commit Message Template'),
                cmds.run(cmds.LoadCommitMessageFromTemplate))
        self.help_about_action = add_action(self,
                N_('About'), launch_about_dialog)

        self.diff_expression_action = add_action(self,
                N_('Expression...'), guicmds.diff_expression)
        self.branch_compare_action = add_action(self,
                N_('Branches...'), compare_branches)

        self.create_tag_action = add_action(self,
                N_('Create Tag...'), create_tag)

        self.create_branch_action = add_action(self,
                N_('Create...'), create_new_branch, 'Ctrl+B')

        self.delete_branch_action = add_action(self,
                N_('Delete...'), guicmds.delete_branch)

        self.delete_remote_branch_action = add_action(self,
                N_('Delete Remote Branch...'), guicmds.delete_remote_branch)

        self.checkout_branch_action = add_action(self,
                N_('Checkout...'), guicmds.checkout_branch, 'Alt+B')
        self.branch_review_action = add_action(self,
                N_('Review...'), guicmds.review_branch)

        self.browse_action = add_action(self,
                N_('Browser...'), worktree_browser)
        self.browse_action.setIcon(qtutils.git_icon())

        self.dag_action = add_action(self, N_('DAG...'), self.git_dag)
        self.dag_action.setIcon(qtutils.git_icon())

        self.rebase_start_action = add_action(self,
                N_('Start Interactive Rebase...'), self.rebase_start)

        self.rebase_edit_todo_action = add_action(self,
                N_('Edit...'), self.rebase_edit_todo)

        self.rebase_continue_action = add_action(self,
                N_('Continue'), self.rebase_continue)

        self.rebase_skip_action = add_action(self,
                N_('Skip Current Patch'), self.rebase_skip)

        self.rebase_abort_action = add_action(self,
                N_('Abort'), self.rebase_abort)

        # Relayed actions
        status_tree = self.statusdockwidget.widget().tree
        self.addAction(status_tree.revert_unstaged_edits_action)
        if not self.browser_dockable:
            # These shortcuts conflict with those from the
            # 'Browser' widget so don't register them when
            # the browser is a dockable tool.
            self.addAction(status_tree.up)
            self.addAction(status_tree.down)
            self.addAction(status_tree.process_selection)

        self.lock_layout_action = add_action_bool(self,
                N_('Lock Layout'), self.set_lock_layout, False)

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # File Menu
        self.file_menu = create_menu(N_('File'), self.menubar)
        self.open_recent_menu = self.file_menu.addMenu(N_('Open Recent'))
        self.open_recent_menu.setIcon(qtutils.open_icon())
        self.file_menu.addAction(self.open_repo_action)
        self.file_menu.addAction(self.open_repo_new_action)
        self.file_menu.addAction(self.clone_repo_action)
        self.file_menu.addAction(self.new_repository_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.rescan_action)
        self.file_menu.addAction(self.edit_remotes_action)
        self.file_menu.addAction(self.browse_recently_modified_action)
        self.file_menu.addAction(self.manage_bookmarks_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.load_commitmsg_action)
        self.file_menu.addAction(self.load_commitmsg_template_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.apply_patches_action)
        self.file_menu.addAction(self.export_patches_action)
        self.file_menu.addAction(self.save_tarball_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.preferences_action)
        self.file_menu.addAction(self.quit_action)
        self.menubar.addAction(self.file_menu.menuAction())

        # Actions menu
        self.actions_menu = create_menu(N_('Actions'), self.menubar)
        self.actions_menu.addAction(self.fetch_action)
        self.actions_menu.addAction(self.push_action)
        self.actions_menu.addAction(self.pull_action)
        self.actions_menu.addAction(self.stash_action)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.create_tag_action)
        self.actions_menu.addAction(self.cherry_pick_action)
        self.actions_menu.addAction(self.merge_local_action)
        self.actions_menu.addAction(self.merge_abort_action)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.grep_action)
        self.actions_menu.addAction(self.search_commits_action)
        self.menubar.addAction(self.actions_menu.menuAction())

        # Index Menu
        self.commit_menu = create_menu(N_('Index'), self.menubar)
        self.commit_menu.setTitle(N_('Index'))
        self.commit_menu.addAction(self.stage_modified_action)
        self.commit_menu.addAction(self.stage_untracked_action)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.unstage_all_action)
        self.commit_menu.addAction(self.unstage_selected_action)
        self.menubar.addAction(self.commit_menu.menuAction())

        # Diff Menu
        self.diff_menu = create_menu(N_('Diff'), self.menubar)
        self.diff_menu.addAction(self.diff_expression_action)
        self.diff_menu.addAction(self.branch_compare_action)
        self.diff_menu.addSeparator()
        self.diff_menu.addAction(self.show_diffstat_action)
        self.menubar.addAction(self.diff_menu.menuAction())

        # Branch Menu
        self.branch_menu = create_menu(N_('Branch'), self.menubar)
        self.branch_menu.addAction(self.branch_review_action)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.create_branch_action)
        self.branch_menu.addAction(self.checkout_branch_action)
        self.branch_menu.addAction(self.delete_branch_action)
        self.branch_menu.addAction(self.delete_remote_branch_action)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.browse_branch_action)
        self.branch_menu.addAction(self.browse_other_branch_action)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.visualize_current_action)
        self.branch_menu.addAction(self.visualize_all_action)
        self.menubar.addAction(self.branch_menu.menuAction())

        # Rebase menu
        self.rebase_menu = create_menu(N_('Rebase'), self.actions_menu)
        self.rebase_menu.addAction(self.rebase_start_action)
        self.rebase_menu.addAction(self.rebase_edit_todo_action)
        self.rebase_menu.addSeparator()
        self.rebase_menu.addAction(self.rebase_continue_action)
        self.rebase_menu.addAction(self.rebase_skip_action)
        self.rebase_menu.addSeparator()
        self.rebase_menu.addAction(self.rebase_abort_action)
        self.menubar.addAction(self.rebase_menu.menuAction())

        # View Menu
        self.view_menu = create_menu(N_('View'), self.menubar)
        self.view_menu.addAction(self.browse_action)
        self.view_menu.addAction(self.dag_action)
        self.view_menu.addSeparator()
        if self.browser_dockable:
            self.view_menu.addAction(self.browserdockwidget.toggleViewAction())

        self.setup_dockwidget_view_menu()
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.lock_layout_action)
        self.menubar.addAction(self.view_menu.menuAction())

        # Help Menu
        self.help_menu = create_menu(N_('Help'), self.menubar)
        self.help_menu.addAction(self.help_docs_action)
        self.help_menu.addAction(self.help_shortcuts_action)
        self.help_menu.addAction(self.help_about_action)
        self.menubar.addAction(self.help_menu.menuAction())

        # Set main menu
        self.setMenuBar(self.menubar)

        # Arrange dock widgets
        left = Qt.LeftDockWidgetArea
        right = Qt.RightDockWidgetArea
        bottom = Qt.BottomDockWidgetArea

        self.addDockWidget(left, self.commitdockwidget)
        if self.browser_dockable:
            self.addDockWidget(left, self.browserdockwidget)
            self.tabifyDockWidget(self.browserdockwidget, self.commitdockwidget)
        self.addDockWidget(left, self.diffdockwidget)
        self.addDockWidget(right, self.statusdockwidget)
        self.addDockWidget(right, self.bookmarksdockwidget)
        self.addDockWidget(bottom, self.actionsdockwidget)
        self.addDockWidget(bottom, self.logdockwidget)
        self.tabifyDockWidget(self.actionsdockwidget, self.logdockwidget)


        # Listen for model notifications
        model.add_observer(model.message_updated, self._update)
        model.add_observer(model.message_mode_changed, lambda x: self._update())

        prefs_model.add_observer(prefs_model.message_config_updated,
                                 self._config_updated)

        # Set a default value
        self.show_cursor_position(1, 0)

        self.connect(self.open_recent_menu, SIGNAL('aboutToShow()'),
                     self.build_recent_menu)

        self.connect(self.commitmsgeditor, SIGNAL('cursorPosition(int,int)'),
                     self.show_cursor_position)

        self.connect(self.diffeditor, SIGNAL('diff_options_updated()'),
                     self.statuswidget.refresh)

        self.connect(self, SIGNAL('update'), self._update_callback)
        self.connect(self, SIGNAL('install_config_actions'),
                     self._install_config_actions)

        # Install .git-config-defined actions
        self._config_task = None
        self.install_config_actions()

        # Restore saved settings
        if not self.restore_state(settings=settings):
            self.resize(987, 610)
            self.set_initial_size()

        self.statusdockwidget.widget().setFocus()

        # Route command output here
        Interaction.log_status = self.logwidget.log_status
        Interaction.log = self.logwidget.log
        Interaction.log(version.git_version_str() + '\n' +
                        N_('git cola version %s') % version.version())

    def set_initial_size(self):
        self.statuswidget.set_initial_size()
        self.commitmsgeditor.set_initial_size()

    # Qt overrides
    def closeEvent(self, event):
        """Save state in the settings manager."""
        commit_msg = self.commitmsgeditor.commit_message(raw=True)
        self.model.save_commitmsg(commit_msg)
        MainWindow.closeEvent(self, event)

    def build_recent_menu(self):
        settings = Settings()
        settings.load()
        recent = settings.recent
        cmd = cmds.OpenRepo
        menu = self.open_recent_menu
        menu.clear()
        for r in recent:
            name = os.path.basename(r)
            directory = os.path.dirname(r)
            text = '%s %s %s' % (name, unichr(0x2192), directory)
            menu.addAction(text, cmds.run(cmd, r))

    # Accessors
    mode = property(lambda self: self.model.mode)

    def _config_updated(self, source, config, value):
        if config == prefs.FONTDIFF:
            # The diff font
            font = QtGui.QFont()
            if not font.fromString(value):
                return
            self.logwidget.setFont(font)
            self.diffeditor.setFont(font)
            self.commitmsgeditor.setFont(font)

        elif config == prefs.TABWIDTH:
            # variable-tab-width setting
            self.diffeditor.set_tabwidth(value)
            self.commitmsgeditor.set_tabwidth(value)

        elif config == prefs.LINEBREAK:
            # enables automatic line breaks
            self.commitmsgeditor.set_linebreak(value)

        elif config == prefs.TEXTWIDTH:
            # text width used for line wrapping
            self.commitmsgeditor.set_textwidth(value)

    def install_config_actions(self):
        """Install .gitconfig-defined actions"""
        self._config_task = self._start_config_actions_task()

    def _start_config_actions_task(self):
        """Do the expensive "get_config_actions()" call in the background"""
        class ConfigActionsTask(QtCore.QRunnable):
            def __init__(self, sender):
                QtCore.QRunnable.__init__(self)
                self._sender = sender
            def run(self):
                names = cfgactions.get_config_actions()
                self._sender.emit(SIGNAL('install_config_actions'), names)

        task = ConfigActionsTask(self)
        QtCore.QThreadPool.globalInstance().start(task)
        return task

    def _install_config_actions(self, names):
        """Install .gitconfig-defined actions"""
        if not names:
            return
        menu = self.actions_menu
        menu.addSeparator()
        for name in names:
            menu.addAction(name, cmds.run(cmds.RunConfigAction, name))

    def _update(self):
        self.emit(SIGNAL('update'))

    def _update_callback(self):
        """Update the title with the current branch and directory name."""
        alerts = []
        branch = self.model.currentbranch
        curdir = core.getcwd()
        is_merging = self.model.is_merging
        is_rebasing = self.model.is_rebasing

        msg = N_('Repository: %s') % curdir
        msg += '\n'
        msg += N_('Branch: %s') % branch

        if is_rebasing:
            msg += '\n\n'
            msg += N_('This repository is currently being rebased.\n'
                      'Resolve conflicts, commit changes, and run:\n'
                      '    Rebase > Continue')
            alerts.append(N_('Rebasing'))

        elif is_merging:
            msg += '\n\n'
            msg += N_('This repository is in the middle of a merge.\n'
                      'Resolve conflicts and commit changes.')
            alerts.append(N_('Merging'))

        if self.mode == self.model.mode_amend:
            alerts.append(N_('Amending'))

        l = unichr(0xab)
        r = unichr(0xbb)
        title = ('%s: %s %s%s' % (
                    self.model.project,
                    branch,
                    alerts and ((r+' %s '+l+' ') % ', '.join(alerts)) or '',
                    self.model.git.worktree()))

        self.setWindowTitle(title)
        self.commitdockwidget.setToolTip(msg)
        self.commitmsgeditor.set_mode(self.mode)
        self.update_actions()

        if not self.model.amending():
            # Check if there's a message file in .git/
            merge_msg_path = gitcmds.merge_message_path()
            if merge_msg_path is None:
                return
            merge_msg_hash = utils.checksum(merge_msg_path)
            if merge_msg_hash == self.merge_message_hash:
                return
            self.merge_message_hash = merge_msg_hash
            cmds.do(cmds.LoadCommitMessageFromFile, merge_msg_path)

    def update_actions(self):
        is_rebasing = self.model.is_rebasing
        can_rebase = not is_rebasing
        self.rebase_start_action.setEnabled(can_rebase)
        self.rebase_edit_todo_action.setEnabled(is_rebasing)
        self.rebase_continue_action.setEnabled(is_rebasing)
        self.rebase_skip_action.setEnabled(is_rebasing)
        self.rebase_abort_action.setEnabled(is_rebasing)

    def apply_state(self, state):
        """Imports data for save/restore"""
        result = MainWindow.apply_state(self, state)
        self.lock_layout_action.setChecked(state.get('lock_layout', False))
        return result

    def setup_dockwidget_view_menu(self):
        # Hotkeys for toggling the dock widgets
        if utils.is_darwin():
            optkey = 'Meta'
        else:
            optkey = 'Ctrl'
        dockwidgets = (
            (optkey + '+0', self.logdockwidget),
            (optkey + '+1', self.commitdockwidget),
            (optkey + '+2', self.statusdockwidget),
            (optkey + '+3', self.diffdockwidget),
            (optkey + '+4', self.actionsdockwidget),
            (optkey + '+5', self.bookmarksdockwidget),
        )
        for shortcut, dockwidget in dockwidgets:
            # Associate the action with the shortcut
            toggleview = dockwidget.toggleViewAction()
            toggleview.setShortcut('Shift+' + shortcut)
            self.view_menu.addAction(toggleview)
            def showdock(show, dockwidget=dockwidget):
                if show:
                    dockwidget.raise_()
                    dockwidget.widget().setFocus()
                else:
                    self.setFocus()
            self.addAction(toggleview)
            connect_action_bool(toggleview, showdock)

            # Create a new shortcut Shift+<shortcut> that gives focus
            toggleview = QtGui.QAction(self)
            toggleview.setShortcut(shortcut)
            def focusdock(dockwidget=dockwidget, showdock=showdock):
                if dockwidget.toggleViewAction().isChecked():
                    showdock(True)
                else:
                    dockwidget.toggleViewAction().trigger()
            self.addAction(toggleview)
            connect_action(toggleview, focusdock)

    def preferences(self):
        return preferences(model=self.prefs_model, parent=self)

    def git_dag(self):
        view = git_dag(self.model)
        view.show()
        view.raise_()

    def save_archive(self):
        ref = git.rev_parse('HEAD')[STDOUT]
        shortref = ref[:7]
        GitArchiveDialog.save_hashed_objects(ref, shortref, self)

    def show_cursor_position(self, rows, cols):
        display = '&nbsp;%02d:%02d&nbsp;' % (rows, cols)
        if cols > 78:
            display = ('<span style="color: white; '
                       '             background-color: red;"'
                       '>%s</span>' % display)
        elif cols > 72:
            display = ('<span style="color: black; '
                       '             background-color: orange;"'
                       '>%s</span>' % display)
        elif cols > 64:
            display = ('<span style="color: black; '
                       '             background-color: yellow;"'
                       '>%s</span>' % display)
        else:
            display = ('<span style="color: grey;">%s</span>' % display)

        self.position_label.setText(display)

    def manage_bookmarks(self):
        manage_bookmarks()
        self.bookmarkswidget.refresh()

    def rebase_start(self):
        branch = guicmds.choose_ref(N_('Select New Upstream'),
                                    N_('Interactive Rebase'))
        if not branch:
            return None
        self.model.is_rebasing = True
        self._update_callback()
        cmds.do(cmds.Rebase, branch)

    def rebase_edit_todo(self):
        cmds.do(cmds.RebaseEditTodo)

    def rebase_continue(self):
        cmds.do(cmds.RebaseContinue)

    def rebase_skip(self):
        cmds.do(cmds.RebaseSkip)

    def rebase_abort(self):
        cmds.do(cmds.RebaseAbort)

########NEW FILE########
__FILENAME__ = merge
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import gitcmds
from cola import qtutils
from cola.i18n import N_
from cola.models import main
from cola.widgets import completion
from cola.widgets import defs
from cola.compat import ustr


def local_merge():
    """Provides a dialog for merging branches"""
    model = main.model()
    view = MergeView(model, qtutils.active_window())
    view.show()
    view.raise_()
    return view


def abort_merge():
    """Prompts before aborting a merge in progress
    """
    title = N_('Abort Merge...')
    txt = N_('Aborting the current merge will cause '
             '*ALL* uncommitted changes to be lost.\n'
             'Recovering uncommitted changes is not possible.')
    info_txt = N_('Aborting the current merge?')
    ok_txt = N_('Abort Merge')
    if qtutils.confirm(title, txt, info_txt, ok_txt,
                       default=False, icon=qtutils.icon('undo.svg')):
        gitcmds.abort_merge()


class MergeView(QtGui.QDialog):
    """Provides a dialog for merging branches."""

    def __init__(self, model, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.model = model
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
        self.setAttribute(Qt.WA_MacMetalStyle)

        # Widgets
        self.title_label = QtGui.QLabel()
        self.revision_label = QtGui.QLabel()
        self.revision_label.setText(N_('Revision To Merge'))

        self.revision = completion.GitRefLineEdit()

        self.radio_local = QtGui.QRadioButton()
        self.radio_local.setText(N_('Local Branch'))
        self.radio_local.setChecked(True)
        self.radio_remote = QtGui.QRadioButton()
        self.radio_remote.setText(N_('Tracking Branch'))
        self.radio_tag = QtGui.QRadioButton()
        self.radio_tag.setText(N_('Tag'))

        self.revisions = QtGui.QListWidget()
        self.revisions.setAlternatingRowColors(True)

        self.button_viz = QtGui.QPushButton(self)
        self.button_viz.setText(N_('Visualize'))

        self.checkbox_squash = QtGui.QCheckBox(self)
        self.checkbox_squash.setText(N_('Squash'))

        self.checkbox_commit = QtGui.QCheckBox(self)
        self.checkbox_commit.setText(N_('Commit'))
        self.checkbox_commit.setChecked(True)
        self.checkbox_commit_state = True

        self.button_cancel = QtGui.QPushButton(self)
        self.button_cancel.setText(N_('Cancel'))

        self.button_merge = QtGui.QPushButton(self)
        self.button_merge.setText(N_('Merge'))

        # Layouts
        self.revlayt = QtGui.QHBoxLayout()
        self.revlayt.addWidget(self.revision_label)
        self.revlayt.addWidget(self.revision)
        self.revlayt.addStretch()
        self.revlayt.addWidget(self.title_label)

        self.radiolayt = QtGui.QHBoxLayout()
        self.radiolayt.addWidget(self.radio_local)
        self.radiolayt.addWidget(self.radio_remote)
        self.radiolayt.addWidget(self.radio_tag)

        self.buttonlayt = QtGui.QHBoxLayout()
        self.buttonlayt.setSpacing(defs.button_spacing)
        self.buttonlayt.addWidget(self.button_viz)
        self.buttonlayt.addStretch()
        self.buttonlayt.addWidget(self.checkbox_squash)
        self.buttonlayt.addWidget(self.checkbox_commit)
        self.buttonlayt.addWidget(self.button_cancel)
        self.buttonlayt.addWidget(self.button_merge)

        self.mainlayt = QtGui.QVBoxLayout()
        self.mainlayt.setMargin(defs.margin)
        self.mainlayt.setSpacing(defs.spacing)
        self.mainlayt.addLayout(self.radiolayt)
        self.mainlayt.addWidget(self.revisions)
        self.mainlayt.addLayout(self.revlayt)
        self.mainlayt.addLayout(self.buttonlayt)
        self.setLayout(self.mainlayt)

        self.revision.setFocus()

        # Signal/slot connections
        self.connect(self.revision, SIGNAL('textChanged(QString)'),
                     self.update_title)

        self.connect(self.revisions, SIGNAL('itemSelectionChanged()'),
                     self.revision_selected)

        qtutils.connect_button(self.button_cancel, self.reject)
        qtutils.connect_button(self.checkbox_squash, self.toggle_squash)
        qtutils.connect_button(self.radio_local, self.update_revisions)
        qtutils.connect_button(self.radio_remote, self.update_revisions)
        qtutils.connect_button(self.radio_tag, self.update_revisions)
        qtutils.connect_button(self.button_merge, self.merge_revision)
        qtutils.connect_button(self.button_viz, self.viz_revision)

        # Observer messages
        model.add_observer(model.message_updated, self.update_all)
        self.update_all()
        self.resize(700, 400)

    def update_all(self):
        """Set the branch name for the window title and label."""
        self.update_title()
        self.update_revisions()

    def update_title(self, dummy_txt=None):
        branch = self.model.currentbranch
        revision = ustr(self.revision.text())
        if revision:
            txt = (N_('Merge "%(revision)s" into "%(branch)s"') %
                   dict(revision=revision, branch=branch))
        else:
            txt = N_('Merge into "%s"') % branch
        self.title_label.setText(txt)
        self.setWindowTitle(txt)

    def toggle_squash(self):
        """Toggles the commit checkbox based on the squash checkbox."""
        if self.checkbox_squash.isChecked():
            self.checkbox_commit_state =\
                self.checkbox_commit.checkState()
            self.checkbox_commit.setCheckState(Qt.Unchecked)
            self.checkbox_commit.setDisabled(True)
        else:
            self.checkbox_commit.setDisabled(False)
            oldstate = self.checkbox_commit_state
            self.checkbox_commit.setCheckState(oldstate)

    def update_revisions(self):
        """Update the revision list whenever a radio button is clicked"""
        self.revisions.clear()
        self.revisions.addItems(self.current_revisions())

    def revision_selected(self):
        """Update the revision field when a list item is selected"""
        revlist = self.current_revisions()
        widget = self.revisions
        row, selected = qtutils.selected_row(widget)
        if selected and row < len(revlist):
            revision = revlist[row]
            self.revision.setText(revision)

    def current_revisions(self):
        """Retrieve candidate items to merge"""
        if self.radio_local.isChecked():
            return self.model.local_branches
        elif self.radio_remote.isChecked():
            return self.model.remote_branches
        elif self.radio_tag.isChecked():
            return self.model.tags
        return []

    def viz_revision(self):
        """Launch a gitk-like viewer on the selection revision"""
        revision = ustr(self.revision.text())
        if not revision:
            qtutils.information(N_('No Revision Specified'),
                                N_('You must specify a revision to view.'))
            return
        cmds.do(cmds.VisualizeRevision, revision)

    def merge_revision(self):
        """Merge the selected revision/branch"""
        revision = ustr(self.revision.text())
        if not revision:
            qtutils.information(N_('No Revision Specified'),
                                N_('You must specify a revision to merge.'))
            return

        do_commit = self.checkbox_commit.isChecked()
        squash = self.checkbox_squash.isChecked()
        cmds.do(cmds.Merge, revision, not(do_commit), squash)
        self.accept()

########NEW FILE########
__FILENAME__ = patch
from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt

from cola import core
from cola import cmds
from cola import qtutils
from cola.i18n import N_
from cola.widgets import defs
from cola.widgets.standard import Dialog
from cola.widgets.standard import DraggableTreeWidget
from cola.compat import ustr


def apply_patches():
    parent = qtutils.active_window()
    dlg = new_apply_patches(parent=parent)
    dlg.show()
    dlg.raise_()
    return dlg


def new_apply_patches(patches=None, parent=None):
    dlg = ApplyPatches(parent=parent)
    if patches:
        dlg.add_paths(patches)
    return dlg


def get_patches_from_paths(paths):
    paths = [core.decode(p) for p in paths]
    patches = [p for p in paths
                if core.isfile(p) and (
                    p.endswith('.patch') or p.endswith('.mbox'))]
    dirs = [p for p in paths if core.isdir(p)]
    dirs.sort()
    for d in dirs:
        patches.extend(get_patches_from_dir(d))
    return patches


def get_patches_from_mimedata(mimedata):
    urls = mimedata.urls()
    if not urls:
        return []
    paths = map(lambda x: ustr(x.path()), urls)
    return get_patches_from_paths(paths)


def get_patches_from_dir(path):
    """Find patches in a subdirectory"""
    patches = []
    for root, subdirs, files in core.walk(path):
        for name in [f for f in files if f.endswith('.patch')]:
            patches.append(core.decode(os.path.join(root, name)))
    return patches


class ApplyPatches(Dialog):

    def __init__(self, parent=None):
        super(ApplyPatches, self).__init__(parent=parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Apply Patches'))
        self.setAcceptDrops(True)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.curdir = os.getcwd()
        self.inner_drag = False

        self.usage = QtGui.QLabel()
        self.usage.setText(N_("""
            <p>
                Drag and drop or use the <strong>Add</strong> button to add
                patches to the list
            </p>
            """))

        self.tree = PatchTreeWidget(parent=self)
        self.tree.setHeaderHidden(True)

        self.add_button = qtutils.create_toolbutton(
                text=N_('Add'), icon=qtutils.add_icon(),
                tooltip=N_('Add patches (+)'))

        self.remove_button = qtutils.create_toolbutton(
                text=N_('Remove'), icon=qtutils.remove_icon(),
                tooltip=N_('Remove selected (Delete)'))

        self.apply_button = qtutils.create_button(
                text=N_('Apply'), icon=qtutils.apply_icon())

        self.close_button = qtutils.create_button(
                text=N_('Close'), icon=qtutils.close_icon())

        self.add_action = qtutils.add_action(self,
                N_('Add'), self.add_files,
                Qt.Key_Plus)

        self.remove_action = qtutils.add_action(self,
                N_('Remove'), self.tree.remove_selected,
                QtGui.QKeySequence.Delete, Qt.Key_Backspace,
                Qt.Key_Minus)

        layout = QtGui.QVBoxLayout()
        layout.setMargin(defs.margin)
        layout.setSpacing(defs.spacing)

        top = QtGui.QHBoxLayout()
        top.setMargin(defs.no_margin)
        top.setSpacing(defs.button_spacing)
        top.addWidget(self.add_button)
        top.addWidget(self.remove_button)
        top.addStretch()
        top.addWidget(self.usage)

        bottom = QtGui.QHBoxLayout()
        bottom.setMargin(defs.no_margin)
        bottom.setSpacing(defs.button_spacing)
        bottom.addWidget(self.apply_button)
        bottom.addStretch()
        bottom.addWidget(self.close_button)

        layout.addLayout(top)
        layout.addWidget(self.tree)
        layout.addLayout(bottom)
        self.setLayout(layout)

        qtutils.connect_button(self.add_button, self.add_files)
        qtutils.connect_button(self.remove_button, self.tree.remove_selected)
        qtutils.connect_button(self.apply_button, self.apply_patches)
        qtutils.connect_button(self.close_button, self.close)

        if not self.restore_state():
            self.resize(666, 420)

    def apply_patches(self):
        items = self.tree.items()
        if not items:
            return
        patches = [ustr(i.data(0, Qt.UserRole).toPyObject()) for i in items]
        cmds.do(cmds.ApplyPatches, patches)
        self.accept()

    def add_files(self):
        files = qtutils.open_files(N_('Select patch file(s)...'),
                                   directory=self.curdir,
                                   filter='Patches (*.patch *.mbox)')
        if not files:
            return
        files = [ustr(f) for f in files]
        self.curdir = os.path.dirname(files[0])
        self.add_paths([os.path.relpath(f) for f in files])

    def dragEnterEvent(self, event):
        """Accepts drops if the mimedata contains patches"""
        super(ApplyPatches, self).dragEnterEvent(event)
        patches = get_patches_from_mimedata(event.mimeData())
        if patches:
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Add dropped patches"""
        event.accept()
        patches = get_patches_from_mimedata(event.mimeData())
        if not patches:
            return
        self.add_paths(patches)

    def add_paths(self, paths):
        self.tree.add_paths(paths)


class PatchTreeWidget(DraggableTreeWidget):

    def __init__(self, parent=None):
        super(PatchTreeWidget, self).__init__(parent=parent)

    def add_paths(self, paths):
        patches = get_patches_from_paths(paths)
        if not patches:
            return
        items = []
        icon = qtutils.file_icon()
        for patch in patches:
            item = QtGui.QTreeWidgetItem()
            flags = item.flags() & ~Qt.ItemIsDropEnabled
            item.setFlags(flags)
            item.setIcon(0, icon)
            item.setText(0, os.path.basename(patch))
            item.setData(0, Qt.UserRole, QtCore.QVariant(patch))
            item.setToolTip(0, patch)
            items.append(item)
        self.addTopLevelItems(items)

    def remove_selected(self):
        idxs = self.selectedIndexes()
        rows = [idx.row() for idx in idxs]
        for row in reversed(sorted(rows)):
            self.invisibleRootItem().takeChild(row)

########NEW FILE########
__FILENAME__ = prefs
from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import qtutils
from cola import gitcfg
from cola.i18n import N_
from cola.models import prefs
from cola.models.prefs import PreferencesModel
from cola.models.prefs import SetConfig
from cola.models.prefs import FONTDIFF
from cola.qtutils import diff_font
from cola.widgets import defs
from cola.widgets import standard
from cola.compat import ustr


def preferences(model=None, parent=None):
    if model is None:
        model = PreferencesModel()
    view = PreferencesView(model, parent=parent)
    view.show()
    view.raise_()
    return view


class FormWidget(QtGui.QWidget):
    def __init__(self, model, parent, source='user'):
        QtGui.QWidget.__init__(self, parent)
        self.model = model
        self.config_to_widget = {}
        self.widget_to_config = {}
        self.source = source
        self.config = gitcfg.instance()
        self.defaults = {}
        self.setLayout(QtGui.QFormLayout())

    def add_row(self, label, widget):
        self.layout().addRow(label, widget)

    def set_config(self, config_dict):
        self.config_to_widget.update(config_dict)
        for config, (widget, default) in config_dict.items():
            self.widget_to_config[config] = widget
            self.defaults[config] = default
            self.connect_widget_to_config(widget, config)

    def connect_widget_to_config(self, widget, config):
        if isinstance(widget, QtGui.QSpinBox):
            widget.connect(widget, SIGNAL('valueChanged(int)'),
                           self._int_config_changed(config))

        elif isinstance(widget, QtGui.QCheckBox):
            widget.connect(widget, SIGNAL('toggled(bool)'),
                           self._bool_config_changed(config))

        elif isinstance(widget, QtGui.QLineEdit):
            widget.connect(widget, SIGNAL('editingFinished()'),
                           self._text_config_changed(config))
            widget.connect(widget, SIGNAL('returnPressed()'),
                           self._text_config_changed(config))

    def _int_config_changed(self, config):
        def runner(value):
            cmds.do(SetConfig, self.model, self.source, config, value)
        return runner

    def _bool_config_changed(self, config):
        def runner(value):
            cmds.do(SetConfig, self.model, self.source, config, value)
        return runner

    def _text_config_changed(self, config):
        def runner():
            value = ustr(self.sender().text())
            cmds.do(SetConfig, self.model, self.source, config, value)
        return runner

    def update_from_config(self):
        if self.source == 'user':
            getter = self.config.get_user
        else:
            getter = self.config.get

        for config, widget in self.widget_to_config.items():
            value = getter(config)
            if value is None:
                value = self.defaults[config]
            self.set_widget_value(widget, value)

    def set_widget_value(self, widget, value):
        widget.blockSignals(True)
        if isinstance(widget, QtGui.QSpinBox):
            widget.setValue(value)
        elif isinstance(widget, QtGui.QLineEdit):
            widget.setText(value)
        elif isinstance(widget, QtGui.QCheckBox):
            widget.setChecked(value)
        widget.blockSignals(False)


class RepoFormWidget(FormWidget):
    def __init__(self, model, parent, source):
        FormWidget.__init__(self, model, parent, source=source)

        self.name = QtGui.QLineEdit()
        self.email = QtGui.QLineEdit()
        self.merge_verbosity = QtGui.QSpinBox()
        self.merge_verbosity.setMinimum(0)
        self.merge_verbosity.setMaximum(5)
        self.merge_verbosity.setProperty('value', QtCore.QVariant(5))

        self.diff_context = QtGui.QSpinBox()
        self.diff_context.setMinimum(2)
        self.diff_context.setMaximum(99)
        self.diff_context.setProperty('value', QtCore.QVariant(5))

        self.merge_summary = QtGui.QCheckBox()
        self.merge_summary.setChecked(True)

        self.merge_diffstat = QtGui.QCheckBox()
        self.merge_diffstat.setChecked(True)

        self.display_untracked = QtGui.QCheckBox()
        self.display_untracked.setChecked(True)

        self.add_row(N_('User Name'), self.name)
        self.add_row(N_('Email Address'), self.email)
        self.add_row(N_('Merge Verbosity'), self.merge_verbosity)
        self.add_row(N_('Number of Diff Context Lines'), self.diff_context)
        self.add_row(N_('Summarize Merge Commits'), self.merge_summary)
        self.add_row(N_('Show Diffstat After Merge'), self.merge_diffstat)
        self.add_row(N_('Display Untracked Files'), self.display_untracked)

        self.set_config({
            prefs.DIFFCONTEXT: (self.diff_context, 5),
            prefs.DISPLAY_UNTRACKED: (self.display_untracked, True),
            prefs.USER_NAME: (self.name, ''),
            prefs.USER_EMAIL: (self.email, ''),
            prefs.MERGE_DIFFSTAT: (self.merge_diffstat, True),
            prefs.MERGE_SUMMARY: (self.merge_summary, True),
            prefs.MERGE_VERBOSITY: (self.merge_verbosity, 5),
        })


class SettingsFormWidget(FormWidget):
    def __init__(self, model, parent):
        FormWidget.__init__(self, model, parent)

        self.fixed_font = QtGui.QFontComboBox()
        self.fixed_font.setFontFilters(QtGui.QFontComboBox.MonospacedFonts)

        self.font_size = QtGui.QSpinBox()
        self.font_size.setMinimum(8)
        self.font_size.setProperty('value', QtCore.QVariant(12))
        self._font_str = None

        self.tabwidth = QtGui.QSpinBox()
        self.tabwidth.setWrapping(True)
        self.tabwidth.setMaximum(42)

        self.textwidth = QtGui.QSpinBox()
        self.textwidth.setWrapping(True)
        self.textwidth.setMaximum(150)

        self.linebreak = QtGui.QCheckBox()
        self.editor = QtGui.QLineEdit()
        self.historybrowser = QtGui.QLineEdit()
        self.difftool = QtGui.QLineEdit()
        self.mergetool = QtGui.QLineEdit()
        self.keep_merge_backups = QtGui.QCheckBox()
        self.save_gui_settings = QtGui.QCheckBox()

        self.add_row(N_('Fixed-Width Font'), self.fixed_font)
        self.add_row(N_('Font Size'), self.font_size)
        self.add_row(N_('Tab Width'), self.tabwidth)
        self.add_row(N_('Text Width'), self.textwidth)
        self.add_row(N_('Auto-Wrap Lines'), self.linebreak)
        self.add_row(N_('Editor'), self.editor)
        self.add_row(N_('History Browser'), self.historybrowser)
        self.add_row(N_('Diff Tool'), self.difftool)
        self.add_row(N_('Merge Tool'), self.mergetool)
        self.add_row(N_('Keep *.orig Merge Backups'), self.keep_merge_backups)
        self.add_row(N_('Save GUI Settings'), self.save_gui_settings)

        self.set_config({
            prefs.SAVEWINDOWSETTINGS: (self.save_gui_settings, True),
            prefs.TABWIDTH: (self.tabwidth, 8),
            prefs.TEXTWIDTH: (self.textwidth, 72),
            prefs.LINEBREAK: (self.linebreak, True),
            prefs.DIFFTOOL: (self.difftool, 'xxdiff'),
            prefs.EDITOR: (self.editor, os.getenv('VISUAL', 'gvim')),
            prefs.HISTORY_BROWSER: (self.historybrowser, 'gitk'),
            prefs.MERGE_KEEPBACKUP: (self.keep_merge_backups, True),
            prefs.MERGETOOL: (self.mergetool, 'xxdiff'),
        })

        self.connect(self.fixed_font, SIGNAL('currentFontChanged(const QFont &)'),
                     self.current_font_changed)

        self.connect(self.font_size, SIGNAL('valueChanged(int)'),
                     self.font_size_changed)

    def update_from_config(self):
        FormWidget.update_from_config(self)

        block = self.fixed_font.blockSignals(True)
        font = diff_font()
        self.fixed_font.setCurrentFont(font)
        self.fixed_font.blockSignals(block)

        block = self.font_size.blockSignals(True)
        font_size = font.pointSize()
        self.font_size.setValue(font_size)
        self.font_size.blockSignals(block)

    def font_size_changed(self, size):
        font = self.fixed_font.currentFont()
        font.setPointSize(size)
        cmds.do(SetConfig, self.model,
                'user', FONTDIFF, ustr(font.toString()))

    def current_font_changed(self, font):
        cmds.do(SetConfig, self.model,
                'user', FONTDIFF, ustr(font.toString()))


class PreferencesView(standard.Dialog):

    def __init__(self, model, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.setWindowTitle(N_('Preferences'))
        if parent is not None:
            self.setWindowModality(QtCore.Qt.WindowModal)

        self.resize(600, 360)

        self._tabbar = QtGui.QTabBar()
        self._tabbar.setDrawBase(False)
        self._tabbar.addTab(N_('All Repositories'))
        self._tabbar.addTab(N_('Current Repository'))
        self._tabbar.addTab(N_('Settings'))

        self._user_form = RepoFormWidget(model, self, source='user')
        self._repo_form = RepoFormWidget(model, self, source='repo')
        self._options_form = SettingsFormWidget(model, self)

        self._stackedwidget = QtGui.QStackedWidget()
        self._stackedwidget.addWidget(self._user_form)
        self._stackedwidget.addWidget(self._repo_form)
        self._stackedwidget.addWidget(self._options_form)

        self.close_button = QtGui.QPushButton(self)
        self.close_button.setText(N_('Close'))
        self.close_button.setIcon(qtutils.close_icon())

        self._button_layt = QtGui.QHBoxLayout()
        self._button_layt.setMargin(0)
        self._button_layt.setSpacing(defs.spacing)
        self._button_layt.addStretch()
        self._button_layt.addWidget(self.close_button)

        self._layt = QtGui.QVBoxLayout()
        self._layt.setMargin(defs.margin)
        self._layt.setSpacing(defs.spacing)
        self._layt.addWidget(self._tabbar)
        self._layt.addWidget(self._stackedwidget)
        self._layt.addLayout(self._button_layt)
        self.setLayout(self._layt)

        self.connect(self._tabbar, SIGNAL('currentChanged(int)'),
                     self._stackedwidget.setCurrentIndex)

        self.connect(self._stackedwidget, SIGNAL('currentChanged(int)'),
                     self.update_widget)

        qtutils.connect_button(self.close_button, self.accept)
        qtutils.add_close_action(self)

        self.update_widget(0)

    def update_widget(self, idx):
        widget = self._stackedwidget.widget(idx)
        widget.update_from_config()

########NEW FILE########
__FILENAME__ = recent
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import gitcmds
from cola import qtutils
from cola.i18n import N_
from cola.widgets import defs
from cola.widgets import standard
from cola.widgets.browse import GitTreeWidget
from cola.widgets.browse import GitFileTreeModel


def browse_recent_files():
    parent = qtutils.active_window()
    dialog = RecentFileDialog(parent)
    dialog.resize(parent.width(), min(parent.height(), 420))
    dialog.show()


class UpdateFileListThread(QtCore.QThread):
    def __init__(self, count):
        QtCore.QThread.__init__(self)
        self.count = count

    def run(self):
        ref = 'HEAD~%d' % self.count
        filenames = gitcmds.diff_index_filenames(ref)
        self.emit(SIGNAL('filenames'), filenames)


class RecentFileDialog(standard.Dialog):
    def __init__(self, parent):
        standard.Dialog.__init__(self, parent)
        self.setWindowTitle(N_('Recently Modified Files'))
        self.setWindowModality(Qt.WindowModal)

        count = 8
        self.update_thread = UpdateFileListThread(count)

        self.count = QtGui.QSpinBox()
        self.count.setMinimum(0)
        self.count.setMaximum(10000)
        self.count.setValue(count)
        self.count.setSuffix(N_(' commits ago'))

        self.count_label = QtGui.QLabel()
        self.count_label.setText(N_('Showing changes since'))

        self.refresh_button = QtGui.QPushButton()
        self.refresh_button.setText(N_('Refresh'))
        self.refresh_button.setIcon(qtutils.reload_icon())
        self.refresh_button.setEnabled(False)

        self.tree = GitTreeWidget(parent=self)
        self.tree_model = GitFileTreeModel(self)
        self.tree.setModel(self.tree_model)

        self.expand_button = QtGui.QPushButton()
        self.expand_button.setText(N_('Expand'))
        self.expand_button.setIcon(qtutils.open_icon())

        self.collapse_button = QtGui.QPushButton()
        self.collapse_button.setText(N_('Collapse'))
        self.collapse_button.setIcon(qtutils.dir_close_icon())

        self.edit_button = QtGui.QPushButton()
        self.edit_button.setText(N_('Edit'))
        self.edit_button.setIcon(qtutils.apply_icon())
        self.edit_button.setDefault(True)
        self.edit_button.setEnabled(False)

        self.close_button = QtGui.QPushButton()
        self.close_button.setText(N_('Close'))

        toplayout = QtGui.QHBoxLayout()
        toplayout.setMargin(0)
        toplayout.setSpacing(defs.spacing)
        toplayout.addWidget(self.count_label)
        toplayout.addWidget(self.count)
        toplayout.addStretch()
        toplayout.addWidget(self.refresh_button)

        btnlayout = QtGui.QHBoxLayout()
        btnlayout.setMargin(0)
        btnlayout.setSpacing(defs.spacing)
        btnlayout.addWidget(self.expand_button)
        btnlayout.addWidget(self.collapse_button)
        btnlayout.addStretch()
        btnlayout.addWidget(self.edit_button)
        btnlayout.addWidget(self.close_button)

        layout = QtGui.QVBoxLayout()
        layout.setMargin(defs.margin)
        layout.setSpacing(defs.spacing)
        layout.addLayout(toplayout)
        layout.addWidget(self.tree)
        layout.addLayout(btnlayout)
        self.setLayout(layout)

        self.connect(self.tree, SIGNAL('selectionChanged()'),
                     self.selection_changed)

        self.connect(self.tree, SIGNAL('path_chosen'), self.edit_file)

        self.connect(self.count, SIGNAL('valueChanged(int)'),
                     self.count_changed)

        self.connect(self.count, SIGNAL('editingFinished()'), self.refresh)

        self.connect(self.update_thread, SIGNAL('filenames'),
                     self.set_filenames)

        qtutils.connect_button(self.refresh_button, self.refresh)
        qtutils.connect_button(self.expand_button, self.tree.expandAll)
        qtutils.connect_button(self.collapse_button, self.tree.collapseAll)
        qtutils.connect_button(self.close_button, self.accept)
        qtutils.connect_button(self.edit_button, self.edit_selected)

        qtutils.add_action(self, N_('Refresh'), self.refresh, 'Ctrl+R')

        self.update_thread.start()

    def edit_selected(self):
        filenames = self.tree.selected_files()
        if not filenames:
            return
        self.edit_files(filenames)

    def edit_files(self, filenames):
        cmds.do(cmds.Edit, filenames)

    def edit_file(self, filename):
        self.edit_files([filename])

    def refresh(self):
        self.refresh_button.setEnabled(False)
        self.count.setEnabled(False)
        self.tree_model.clear()
        self.tree.setEnabled(False)

        self.update_thread.count = self.count.value()
        self.update_thread.start()

    def count_changed(self, value):
        self.refresh_button.setEnabled(True)

    def selection_changed(self):
        """Update actions based on the current selection"""
        filenames = self.tree.selected_files()
        self.edit_button.setEnabled(bool(filenames))

    def set_filenames(self, filenames):
        self.count.setEnabled(True)
        self.tree.setEnabled(True)
        self.tree_model.clear()
        self.tree_model.add_files(filenames)
        self.tree.expandAll()
        self.tree.select_first_file()
        self.tree.setFocus()

########NEW FILE########
__FILENAME__ = remote
from __future__ import division, absolute_import, unicode_literals

import fnmatch
import time

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.qtutils import connect_button
from cola.widgets import defs
from cola.widgets import standard
from cola.compat import ustr

FETCH = 'Fetch'
PUSH = 'Push'
PULL = 'Pull'


def fetch():
    return run(Fetch)


def push():
    return run(Push)


def pull():
    return run(Pull)


def run(RemoteDialog):
    """Launches fetch/push/pull dialogs."""
    # Copy global stuff over to speedup startup
    model = main.MainModel()
    global_model = main.model()
    model.currentbranch = global_model.currentbranch
    model.local_branches = global_model.local_branches
    model.remote_branches = global_model.remote_branches
    model.tags = global_model.tags
    model.remotes = global_model.remotes
    parent = qtutils.active_window()
    view = RemoteDialog(model, parent=parent)
    view.show()
    return view


def combine(result, existing):
    if existing is None:
        return result

    if type(existing) is tuple:
        if len(existing) == 3:
            return (max(existing[0], result[0]),
                    combine(existing[1], result[1]),
                    combine(existing[2], result[2]))
        else:
            raise AssertionError('combine() with length %d' % len(existing))
    else:
        if existing and result:
            return existing + '\n\n' + result
        elif existing:
            return existing
        else:
            return result


class ActionTask(QtCore.QRunnable):

    def __init__(self, sender, model_action, remote, kwargs):
        QtCore.QRunnable.__init__(self)
        self.sender = sender
        self.model_action = model_action
        self.remote = remote
        self.kwargs = kwargs

    def run(self):
        """Runs the model action and captures the result"""
        status, out, err = self.model_action(self.remote, **self.kwargs)
        self.sender.emit(SIGNAL('action_completed'), self, status, out, err)


class ProgressAnimationThread(QtCore.QThread):

    def __init__(self, txt, parent, timeout=0.25):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        self.txt = txt
        self.timeout = timeout
        self.symbols = [
            '..   ',
            '...  ',
            '.... ',
            '.....',
            '.... ',
            '...  '
        ]
        self.idx = -1

    def next(self):
        self.idx = (self.idx + 1) % len(self.symbols)
        return self.txt + self.symbols[self.idx]

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.emit(SIGNAL('str'), self.next())
            time.sleep(self.timeout)


class RemoteActionDialog(standard.Dialog):

    def __init__(self, model, action, parent=None):
        """Customizes the dialog based on the remote action
        """
        standard.Dialog.__init__(self, parent=parent)
        self.model = model
        self.action = action
        self.tasks = []
        self.filtered_remote_branches = []
        self.selected_remotes = []

        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_(action))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.progress = QtGui.QProgressDialog(self)
        self.progress.setFont(qtutils.diff_font())
        self.progress.setRange(0, 0)
        self.progress.setCancelButton(None)
        self.progress.setWindowTitle(action)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setLabelText(N_('Updating') + '..   ')
        self.progress_thread = ProgressAnimationThread(N_('Updating'), self)

        self.local_label = QtGui.QLabel()
        self.local_label.setText(N_('Local Branch'))

        self.local_branch = QtGui.QLineEdit()
        self.local_branches = QtGui.QListWidget()
        self.local_branches.addItems(self.model.local_branches)

        self.remote_label = QtGui.QLabel()
        self.remote_label.setText(N_('Remote'))

        self.remote_name = QtGui.QLineEdit()
        self.remotes = QtGui.QListWidget()
        if action == PUSH:
            self.remotes.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.remotes.addItems(self.model.remotes)

        self.remote_branch_label = QtGui.QLabel()
        self.remote_branch_label.setText(N_('Remote Branch'))

        self.remote_branch = QtGui.QLineEdit()
        self.remote_branches = QtGui.QListWidget()
        self.remote_branches.addItems(self.model.remote_branches)

        self.ffwd_only_checkbox = QtGui.QCheckBox()
        self.ffwd_only_checkbox.setText(N_('Fast Forward Only '))
        self.ffwd_only_checkbox.setChecked(True)

        self.tags_checkbox = QtGui.QCheckBox()
        self.tags_checkbox.setText(N_('Include tags '))

        self.rebase_checkbox = QtGui.QCheckBox()
        self.rebase_checkbox.setText(N_('Rebase '))

        self.action_button = QtGui.QPushButton()
        self.action_button.setText(N_(action))
        self.action_button.setIcon(qtutils.ok_icon())

        self.close_button = QtGui.QPushButton()
        self.close_button.setText(N_('Close'))
        self.close_button.setIcon(qtutils.close_icon())

        self.local_branch_layout = QtGui.QHBoxLayout()
        self.local_branch_layout.addWidget(self.local_label)
        self.local_branch_layout.addWidget(self.local_branch)

        self.remote_branch_layout = QtGui.QHBoxLayout()
        self.remote_branch_layout.addWidget(self.remote_label)
        self.remote_branch_layout.addWidget(self.remote_name)

        self.remote_branches_layout = QtGui.QHBoxLayout()
        self.remote_branches_layout.addWidget(self.remote_branch_label)
        self.remote_branches_layout.addWidget(self.remote_branch)

        self.options_layout = QtGui.QHBoxLayout()
        self.options_layout.setSpacing(defs.button_spacing)
        self.options_layout.addStretch()
        self.options_layout.addWidget(self.ffwd_only_checkbox)
        self.options_layout.addWidget(self.tags_checkbox)
        self.options_layout.addWidget(self.rebase_checkbox)
        self.options_layout.addWidget(self.action_button)
        self.options_layout.addWidget(self.close_button)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addLayout(self.remote_branch_layout)
        self.main_layout.addWidget(self.remotes)
        if action == PUSH:
            self.main_layout.addLayout(self.local_branch_layout)
            self.main_layout.addWidget(self.local_branches)
            self.main_layout.addLayout(self.remote_branches_layout)
            self.main_layout.addWidget(self.remote_branches)
        else: # fetch and pull
            self.main_layout.addLayout(self.remote_branches_layout)
            self.main_layout.addWidget(self.remote_branches)
            self.main_layout.addLayout(self.local_branch_layout)
            self.main_layout.addWidget(self.local_branches)
        self.main_layout.addLayout(self.options_layout)
        self.setLayout(self.main_layout)

        remotes = self.model.remotes
        if 'origin' in remotes:
            idx = remotes.index('origin')
            if self.select_remote(idx):
                self.remote_name.setText('origin')
        else:
            if self.select_first_remote():
                self.remote_name.setText(remotes[0])

        # Trim the remote list to just the default remote
        self.update_remotes()
        self.set_field_defaults()

        # Setup signals and slots
        self.connect(self.remotes, SIGNAL('itemSelectionChanged()'),
                     self.update_remotes)

        self.connect(self.local_branches, SIGNAL('itemSelectionChanged()'),
                     self.update_local_branches)

        self.connect(self.remote_branches, SIGNAL('itemSelectionChanged()'),
                     self.update_remote_branches)

        connect_button(self.action_button, self.action_callback)
        connect_button(self.close_button, self.close)

        qtutils.add_action(self, N_('Close'),
                      self.close, QtGui.QKeySequence.Close, 'Esc')

        self.connect(self, SIGNAL('action_completed'), self.action_completed)
        self.connect(self.progress_thread, SIGNAL('str'), self.update_progress)

        if action == PULL:
            self.tags_checkbox.hide()
            self.ffwd_only_checkbox.hide()
            self.local_label.hide()
            self.local_branch.hide()
            self.local_branches.hide()
            self.remote_branch.setFocus()
        else:
            self.rebase_checkbox.hide()

        if not self.restore_state():
            self.resize(666, 420)

        self.remote_name.setFocus()

    def set_rebase(self, value):
        self.rebase_checkbox.setChecked(value)

    def set_field_defaults(self):
        # Default to "git fetch origin master"
        action = self.action
        if action == FETCH or action == PULL:
            self.local_branch.setText('')
            self.remote_branch.setText('')
            return

        # Select the current branch by default for push
        if action == PUSH:
            branch = self.model.currentbranch
            try:
                idx = self.model.local_branches.index(branch)
            except ValueError:
                return
            if self.select_local_branch(idx):
                self.set_local_branch(branch)
            self.set_remote_branch('')

    def set_remote_name(self, remote_name):
        self.remote_name.setText(remote_name)
        if remote_name:
            self.remote_name.selectAll()

    def set_local_branch(self, branch):
        self.local_branch.setText(branch)
        if branch:
            self.local_branch.selectAll()

    def set_remote_branch(self, branch):
        self.remote_branch.setText(branch)
        if branch:
            self.remote_branch.selectAll()

    def set_remote_branches(self, branches):
        self.remote_branches.clear()
        self.remote_branches.addItems(branches)
        self.filtered_remote_branches = branches

    def select_first_remote(self):
        """Selects the first remote in the list view"""
        return self.select_remote(0)

    def select_remote(self, idx):
        """Selects a remote by index"""
        item = self.remotes.item(idx)
        if item:
            self.remotes.setItemSelected(item, True)
            self.remotes.setCurrentItem(item)
            self.set_remote_name(ustr(item.text()))
            return True
        else:
            return False

    def select_local_branch(self, idx):
        """Selects a local branch by index in the list view"""
        item = self.local_branches.item(idx)
        if not item:
            return False
        self.local_branches.setItemSelected(item, True)
        self.local_branches.setCurrentItem(item)
        self.local_branch.setText(item.text())
        return True

    def display_remotes(self, widget):
        """Display the available remotes in a listwidget"""
        displayed = []
        for remote_name in self.model.remotes:
            url = self.model.remote_url(remote_name, self.action)
            display = ('%s\t(%s)'
                       % (remote_name, N_('URL: %s') % url))
            displayed.append(display)
        qtutils.set_items(widget,displayed)

    def update_remotes(self, *rest):
        """Update the remote name when a remote from the list is selected"""
        widget = self.remotes
        remotes = self.model.remotes
        selection = qtutils.selected_item(widget, remotes)
        if not selection:
            self.selected_remotes = []
            return
        self.set_remote_name(selection)
        self.selected_remotes = qtutils.selected_items(self.remotes,
                                                       self.model.remotes)

        all_branches = gitcmds.branch_list(remote=True)
        branches = []
        patterns = []
        for remote in self.selected_remotes:
            pat = remote + '/*'
            patterns.append(pat)

        for branch in all_branches:
            for pat in patterns:
                if fnmatch.fnmatch(branch, pat):
                    branches.append(branch)
                    break
        if branches:
            self.set_remote_branches(branches)
        else:
            self.set_remote_branches(all_branches)
        self.set_remote_branch('')

    def update_local_branches(self,*rest):
        """Update the local/remote branch names when a branch is selected"""
        branches = self.model.local_branches
        widget = self.local_branches
        selection = qtutils.selected_item(widget, branches)
        if not selection:
            return
        self.set_local_branch(selection)
        self.set_remote_branch(selection)

    def update_remote_branches(self,*rest):
        """Update the remote branch name when a branch is selected"""
        widget = self.remote_branches
        branches = self.filtered_remote_branches
        selection = qtutils.selected_item(widget, branches)
        if not selection:
            return
        branch = utils.strip_one(selection)
        if branch == 'HEAD':
            return
        self.set_remote_branch(branch)

    def common_args(self):
        """Returns git arguments common to fetch/push/pulll"""
        remote_name = ustr(self.remote_name.text())
        local_branch = ustr(self.local_branch.text())
        remote_branch = ustr(self.remote_branch.text())

        ffwd_only = self.ffwd_only_checkbox.isChecked()
        rebase = self.rebase_checkbox.isChecked()
        tags = self.tags_checkbox.isChecked()

        return (remote_name,
                {
                    'local_branch': local_branch,
                    'remote_branch': remote_branch,
                    'ffwd': ffwd_only,
                    'rebase': rebase,
                    'tags': tags,
                })

    # Actions

    def action_callback(self):
        action = self.action
        if action == FETCH:
            model_action = self.model.fetch
        elif action == PUSH:
            model_action = self.push_to_all
        else: # if action == PULL:
            model_action = self.model.pull

        remote_name = ustr(self.remote_name.text())
        if not remote_name:
            errmsg = N_('No repository selected.')
            Interaction.log(errmsg)
            return
        remote, kwargs = self.common_args()
        self.selected_remotes = qtutils.selected_items(self.remotes,
                                                       self.model.remotes)

        # Check if we're about to create a new branch and warn.
        remote_branch = ustr(self.remote_branch.text())
        local_branch = ustr(self.local_branch.text())

        if action == PUSH and not remote_branch:
            branch = local_branch
            candidate = '%s/%s' % (remote, branch)
            if candidate not in self.model.remote_branches:
                title = N_('Push')
                args = dict(branch=branch, remote=remote)
                msg = N_('Branch "%(branch)s" does not exist in "%(remote)s".\n'
                         'A new remote branch will be published.') % args
                info_txt= N_('Create a new remote branch?')
                ok_text = N_('Create Remote Branch')
                if not qtutils.confirm(title, msg, info_txt, ok_text,
                                       default=False,
                                       icon=qtutils.git_icon()):
                    return

        if not self.ffwd_only_checkbox.isChecked():
            if action == FETCH:
                title = N_('Force Fetch?')
                msg = N_('Non-fast-forward fetch overwrites local history!')
                info_txt = N_('Force fetching from %s?') % remote
                ok_text = N_('Force Fetch')
            elif action == PUSH:
                title = N_('Force Push?')
                msg = N_('Non-fast-forward push overwrites published '
                         'history!\n(Did you pull first?)')
                info_txt = N_('Force push to %s?') % remote
                ok_text = N_('Force Push')
            else: # pull: shouldn't happen since the controls are hidden
                msg = "You probably don't want to do this.\n\tContinue?"
                return

            if not qtutils.confirm(title, msg, info_txt, ok_text,
                                   default=False,
                                   icon=qtutils.discard_icon()):
                return

        # Disable the GUI by default
        self.action_button.setEnabled(False)
        self.close_button.setEnabled(False)
        QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)

        # Show a nice progress bar
        self.progress.show()
        self.progress_thread.start()

        # Use a thread to update in the background
        task = ActionTask(self, model_action, remote, kwargs)
        self.tasks.append(task)
        QtCore.QThreadPool.globalInstance().start(task)

    def update_progress(self, txt):
        self.progress.setLabelText(txt)

    def push_to_all(self, dummy_remote, *args, **kwargs):
        selected_remotes = self.selected_remotes
        all_results = None
        for remote in selected_remotes:
            result = self.model.push(remote, *args, **kwargs)
            all_results = combine(result, all_results)
        return all_results

    def action_completed(self, task, status, out, err):
        # Grab the results of the action and finish up
        self.action_button.setEnabled(True)
        self.close_button.setEnabled(True)
        QtGui.QApplication.restoreOverrideCursor()

        self.progress_thread.stop()
        self.progress_thread.wait()
        self.progress.close()
        if task in self.tasks:
            self.tasks.remove(task)

        already_up_to_date = N_('Already up-to-date.')

        if not out: # git fetch --tags --verbose doesn't print anything...
            out = already_up_to_date

        command = 'git %s' % self.action.lower()
        message = (N_('"%(command)s" returned exit status %(status)d') %
                   dict(command=command, status=status))
        details = ''
        if out:
            details = out
        if err:
            details += '\n\n' + err

        log_message = message
        if details:
            log_message += '\n\n' + details
        Interaction.log(log_message)

        if status == 0:
            self.accept()
            return

        if self.action == PUSH:
            message += '\n\n'
            message += N_('Have you rebased/pulled lately?')

        Interaction.critical(self.windowTitle(),
                             message=message, details=details)


# Use distinct classes so that each saves its own set of preferences
class Fetch(RemoteActionDialog):
    def __init__(self, model, parent=None):
        RemoteActionDialog.__init__(self, model, FETCH, parent=parent)


class Push(RemoteActionDialog):
    def __init__(self, model, parent=None):
        RemoteActionDialog.__init__(self, model, PUSH, parent=parent)


class Pull(RemoteActionDialog):
    def __init__(self, model, parent=None):
        RemoteActionDialog.__init__(self, model, PULL, parent=parent)

    def apply_state(self, state):
        result = RemoteActionDialog.apply_state(self, state)
        try:
            rebase = state['rebase']
        except KeyError:
            result = False
        else:
            self.rebase_checkbox.setChecked(rebase)
        return result

    def export_state(self):
        state = RemoteActionDialog.export_state(self)
        state['rebase'] = self.rebase_checkbox.isChecked()
        return state

    def done(self, exit_code):
        self.save_state()
        return RemoteActionDialog.done(self, exit_code)

########NEW FILE########
__FILENAME__ = search
"""A widget for searching git commits"""
from __future__ import division, absolute_import, unicode_literals

import os
import time
import subprocess

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import utils
from cola import qtutils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.git import git
from cola.git import STDOUT
from cola.qtutils import connect_button
from cola.qtutils import create_toolbutton
from cola.qtutils import dir_icon
from cola.widgets import defs
from cola.widgets import standard
from cola.widgets.diff import DiffTextEdit
from cola.compat import ustr


def mkdate(timespec):
    return '%04d-%02d-%02d' % time.localtime(timespec)[:3]


class SearchOptions(object):
    def __init__(self):
        self.query = ''
        self.max_count = 500
        self.start_date = ''
        self.end_date = ''


class SearchWidget(standard.Dialog):
    def __init__(self, parent):
        standard.Dialog.__init__(self, parent)
        self.setAttribute(QtCore.Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Search'))

        self.mode_combo = QtGui.QComboBox()
        self.browse_button = create_toolbutton(icon=dir_icon(),
                                               tooltip=N_('Browse...'))
        self.query = QtGui.QLineEdit()

        self.start_date = QtGui.QDateEdit()
        self.start_date.setCurrentSection(QtGui.QDateTimeEdit.YearSection)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat(N_('yyyy-MM-dd'))

        self.end_date = QtGui.QDateEdit()
        self.end_date.setCurrentSection(QtGui.QDateTimeEdit.YearSection)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat(N_('yyyy-MM-dd'))

        self.search_button = QtGui.QPushButton()
        self.search_button.setText(N_('Search'))
        self.search_button.setDefault(True)

        self.max_count = QtGui.QSpinBox()
        self.max_count.setMinimum(5)
        self.max_count.setMaximum(9995)
        self.max_count.setSingleStep(5)
        self.max_count.setValue(500)

        self.commit_list = QtGui.QListWidget()
        self.commit_list.setMinimumSize(QtCore.QSize(1, 1))
        self.commit_list.setAlternatingRowColors(True)
        self.commit_list.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

        self.commit_text = DiffTextEdit(self, whitespace=False)

        self.button_export = QtGui.QPushButton()
        self.button_export.setText(N_('Export Patches'))

        self.button_cherrypick = QtGui.QPushButton()
        self.button_cherrypick.setText(N_('Cherry Pick'))

        self.button_close = QtGui.QPushButton()
        self.button_close.setText(N_('Close'))

        self.top_layout = QtGui.QHBoxLayout()
        self.top_layout.setMargin(0)
        self.top_layout.setSpacing(defs.button_spacing)

        self.top_layout.addWidget(self.query)
        self.top_layout.addWidget(self.start_date)
        self.top_layout.addWidget(self.end_date)
        self.top_layout.addWidget(self.browse_button)
        self.top_layout.addWidget(self.search_button)
        self.top_layout.addStretch()
        self.top_layout.addWidget(self.mode_combo)
        self.top_layout.addWidget(self.max_count)

        self.splitter = QtGui.QSplitter()
        self.splitter.setHandleWidth(defs.handle_width)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.addWidget(self.commit_list)
        self.splitter.addWidget(self.commit_text)

        self.bottom_layout = QtGui.QHBoxLayout()
        self.bottom_layout.setMargin(0)
        self.bottom_layout.setSpacing(defs.spacing)
        self.bottom_layout.addWidget(self.button_export)
        self.bottom_layout.addWidget(self.button_cherrypick)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.button_close)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addWidget(self.splitter)
        self.main_layout.addLayout(self.bottom_layout)
        self.setLayout(self.main_layout)

        if self.parent():
            self.resize(self.parent().width(), self.parent().height())
        else:
            self.resize(720, 500)


def search():
    """Return a callback to handle various search actions."""
    return search_commits(qtutils.active_window())


class SearchEngine(object):
    def __init__(self, model):
        self.model = model

    def rev_args(self):
        max_count = self.model.max_count
        return {
            'no_color': True,
            'max-count': max_count,
            'pretty': 'format:%H %aN - %s - %ar',
        }

    def common_args(self):
        return (self.model.query, self.rev_args())

    def search(self):
        if not self.validate():
            return
        return self.results()

    def validate(self):
        return len(self.model.query) > 1

    def revisions(self, *args, **kwargs):
        revlist = git.log(*args, **kwargs)[STDOUT]
        return gitcmds.parse_rev_list(revlist)

    def results(self):
        pass

class RevisionSearch(SearchEngine):
    def results(self):
        query, opts = self.common_args()
        args = utils.shell_split(query)
        return self.revisions(all=True, *args, **opts)


class PathSearch(SearchEngine):
    def results(self):
        query, args = self.common_args()
        paths = ['--'] + utils.shell_split(query)
        return self.revisions(all=True, *paths, **args)


class MessageSearch(SearchEngine):
    def results(self):
        query, kwargs = self.common_args()
        return self.revisions(all=True, grep=query, **kwargs)


class AuthorSearch(SearchEngine):
    def results(self):
        query, kwargs = self.common_args()
        return self.revisions(all=True, author=query, **kwargs)


class CommitterSearch(SearchEngine):
    def results(self):
        query, kwargs = self.common_args()
        return self.revisions(all=True, committer=query, **kwargs)


class DiffSearch(SearchEngine):
    def results(self):
        query, kwargs = self.common_args()
        return gitcmds.parse_rev_list(
            git.log('-S'+query, all=True, **kwargs)[STDOUT])


class DateRangeSearch(SearchEngine):
    def validate(self):
        return self.model.start_date < self.model.end_date

    def results(self):
        kwargs = self.rev_args()
        start_date = self.model.start_date
        end_date = self.model.end_date
        return self.revisions(date='iso',
                              all=True,
                              after=start_date,
                              before=end_date,
                              **kwargs)


class Search(SearchWidget):

    def __init__(self, model, parent):
        SearchWidget.__init__(self, parent)
        self.model = model

        self.EXPR = N_('Search by Expression')
        self.PATH = N_('Search by Path')
        self.MESSAGE = N_('Search Commit Messages')
        self.DIFF = N_('Search Diffs')
        self.AUTHOR = N_('Search Authors')
        self.COMMITTER = N_('Search Committers')
        self.DATE_RANGE = N_('Search Date Range')

        # Each search type is handled by a distinct SearchEngine subclass
        self.engines = {
            self.EXPR: RevisionSearch,
            self.PATH: PathSearch,
            self.MESSAGE: MessageSearch,
            self.DIFF: DiffSearch,
            self.AUTHOR: AuthorSearch,
            self.COMMITTER: CommitterSearch,
            self.DATE_RANGE: DateRangeSearch,
        }

        self.modes = (self.EXPR, self.PATH, self.DATE_RANGE,
                      self.DIFF, self.MESSAGE, self.AUTHOR, self.COMMITTER)
        self.mode_combo.addItems(self.modes)

        connect_button(self.search_button, self.search_callback)
        connect_button(self.browse_button, self.browse_callback)
        connect_button(self.button_export, self.export_patch)
        connect_button(self.button_cherrypick, self.cherry_pick)
        connect_button(self.button_close, self.accept)

        self.connect(self.mode_combo, SIGNAL('currentIndexChanged(int)'),
                     self.mode_index_changed)

        self.connect(self.commit_list,
                     SIGNAL('itemSelectionChanged()'),
                     self.display)

        self.set_start_date(mkdate(time.time()-(87640*31)))
        self.set_end_date(mkdate(time.time()+87640))
        self.set_mode(self.EXPR)

        self.query.setFocus()

    def mode_index_changed(self, idx):
        mode = self.mode()
        self.update_shown_widgets(mode)
        if mode == self.PATH:
            self.browse_callback()

    def set_commit_list(self, commits):
        widget = self.commit_list
        widget.clear()
        widget.addItems(commits)

    def set_start_date(self, datestr):
        self.set_date(self.start_date, datestr)

    def set_end_date(self, datestr):
        self.set_date(self.end_date, datestr)

    def set_date(self, widget, datestr):
        fmt = QtCore.Qt.ISODate
        date = QtCore.QDate.fromString(datestr, fmt)
        if date:
            widget.setDate(date)

    def set_mode(self, mode):
        idx = self.modes.index(mode)
        self.mode_combo.setCurrentIndex(idx)
        self.update_shown_widgets(mode)

    def update_shown_widgets(self, mode):
        date_shown = mode == self.DATE_RANGE
        browse_shown = mode == self.PATH
        self.query.setVisible(not date_shown)
        self.browse_button.setVisible(browse_shown)
        self.start_date.setVisible(date_shown)
        self.end_date.setVisible(date_shown)

    def mode(self):
        return str(self.mode_combo.currentText())

    def search_callback(self, *args):
        engineclass = self.engines[self.mode()]
        self.model.query = ustr(self.query.text())
        self.model.max_count = self.max_count.value()

        fmt = QtCore.Qt.ISODate
        self.model.start_date = str(self.start_date.date().toString(fmt))
        self.model.end_date = str(self.end_date.date().toString(fmt))

        self.results = engineclass(self.model).search()
        if self.results:
            self.display_results()
        else:
            self.commit_list.clear()
            self.commit_text.setText('')

    def browse_callback(self):
        paths = QtGui.QFileDialog.getOpenFileNames(self,
                                                   N_('Choose Path(s)'))
        if not paths:
            return
        filepaths = []
        lenprefix = len(os.getcwd()) + 1
        for path in map(lambda x: ustr(x), paths):
            if not path.startswith(os.getcwd()):
                continue
            filepaths.append(path[lenprefix:])
        query = subprocess.list2cmdline(filepaths)
        self.query.setText(query)
        if query:
            self.search_callback()

    def display_results(self):
        commit_list = map(lambda x: x[1], self.results)
        self.set_commit_list(commit_list)

    def display(self, *args):
        widget = self.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            self.commit_text.setText('')
            return
        revision = self.results[row][0]
        qtutils.set_clipboard(revision)
        diff = gitcmds.commit_diff(revision)
        self.commit_text.setText(diff)

    def export_patch(self):
        widget = self.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        Interaction.log_status(*gitcmds.export_patchset(revision, revision))

    def cherry_pick(self):
        widget = self.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        Interaction.log_status(*git.cherry_pick(revision))

def search_commits(parent):
    opts = SearchOptions()
    widget = Search(opts, parent)
    widget.show()
    return widget



if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    search = Search()
    search.show()
    sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = selectcommits
"""A GUI for selecting commits"""
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import qtutils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.widgets import defs
from cola.widgets.diff import DiffTextEdit


def select_commits(title, revs, summaries, multiselect=True):
    """Use the SelectCommitsDialog to select commits from a list."""
    model = Model(revs, summaries)
    parent = qtutils.active_window()
    dialog = SelectCommitsDialog(model, parent, title, multiselect=multiselect)
    return dialog.select_commits()


class Model(object):
    def __init__(self, revs, summaries):
        self.revisions = revs
        self.summaries = summaries

    def revision_sha1(self, idx):
        return self.revisions[idx]


class SelectCommitsDialog(QtGui.QDialog):
    def __init__(self, model,
                 parent=None, title=None, multiselect=True, syntax=True):
        QtGui.QDialog.__init__(self, parent)
        self.model = model
        if title:
            self.setWindowTitle(title)

        self.commit_list = QtGui.QListWidget()
        if multiselect:
            mode = QtGui.QAbstractItemView.ExtendedSelection
        else:
            mode = QtGui.QAbstractItemView.SingleSelection
        self.commit_list.setSelectionMode(mode)
        self.commit_list.setAlternatingRowColors(True)

        self.commit_text = DiffTextEdit(self, whitespace=False)

        self.label = QtGui.QLabel()
        self.label.setText(N_('Revision Expression:'))
        self.revision = QtGui.QLineEdit()
        self.revision.setReadOnly(True)

        self.select_button = QtGui.QPushButton(N_('Select'))
        self.select_button.setIcon(qtutils.apply_icon())
        self.select_button.setEnabled(False)
        self.select_button.setDefault(True)

        self.close_button = QtGui.QPushButton(N_('Close'))

        # Make the list widget slighty larger
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(defs.handle_width)
        self.splitter.setSizes([100, 150])
        self.splitter.addWidget(self.commit_list)
        self.splitter.addWidget(self.commit_text)

        self.input_layout = QtGui.QHBoxLayout()
        self.input_layout.setMargin(0)
        self.input_layout.setSpacing(defs.spacing)
        self.input_layout.addWidget(self.label)
        self.input_layout.addWidget(self.revision)
        self.input_layout.addWidget(self.select_button)
        self.input_layout.addWidget(self.close_button)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.margin)
        self.main_layout.addWidget(self.splitter)
        self.main_layout.addLayout(self.input_layout)
        self.setLayout(self.main_layout)

        self.connect(self.commit_list,
                     SIGNAL('itemSelectionChanged()'), self.commit_sha1_selected)

        qtutils.connect_button(self.select_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        #self.setTabOrder(self.commit_list, self.commit_text)
        #self.setTabOrder(self.commit_text, self.revision)
        #self.setTabOrder(self.revision, self.select_button)
        #self.setTabOrder(self.select_button, self.close_button)
        #self.setTabOrder(self.close_button, self.commit_list)

        self.resize(700, 420)

    def select_commits(self):
        summaries = self.model.summaries
        if not summaries:
            msg = N_('No commits exist in this branch.')
            Interaction.log(msg)
            return []
        qtutils.set_items(self.commit_list, summaries)
        self.show()
        if self.exec_() != QtGui.QDialog.Accepted:
            return []
        revs = self.model.revisions
        return qtutils.selection_list(self.commit_list, revs)

    def commit_sha1_selected(self):
        row, selected = qtutils.selected_row(self.commit_list)
        self.select_button.setEnabled(selected)
        if not selected:
            self.commit_text.setText('')
            self.revision.setText('')
            return
        # Get the sha1 and put it in the revision line
        sha1 = self.model.revision_sha1(row)
        self.revision.setText(sha1)
        self.revision.selectAll()

        # Display the sha1's commit
        commit_diff = gitcmds.commit_diff(sha1)
        self.commit_text.setText(commit_diff)

########NEW FILE########
__FILENAME__ = spellcheck
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

__copyright__ = """
2012, Peter Norvig (http://norvig.com/spell-correct.html)
2013, David Aguilar <davvid@gmail.com>
"""

import collections
import re
import sys

from PyQt4.Qt import QAction
from PyQt4.Qt import QApplication
from PyQt4.Qt import QEvent
from PyQt4.Qt import QMenu
from PyQt4.Qt import QMouseEvent
from PyQt4.Qt import QSyntaxHighlighter
from PyQt4.Qt import QTextCharFormat
from PyQt4.Qt import QTextCursor
from PyQt4.Qt import Qt
from PyQt4.QtCore import SIGNAL

from cola.i18n import N_
from cola.widgets.text import HintedTextEdit
from cola.compat import ustr


alphabet = 'abcdefghijklmnopqrstuvwxyz'


def train(features, model):
    for f in features:
        model[f] += 1
    return model


def edits1(word):
    splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes    = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b)>1]
    replaces   = [a + c + b[1:] for a, b in splits for c in alphabet if b]
    inserts    = [a + c + b     for a, b in splits for c in alphabet]
    return set(deletes + transposes + replaces + inserts)


def known_edits2(word, words):
    return set(e2 for e1 in edits1(word)
                  for e2 in edits1(e1) if e2 in words)

def known(word, words):
    return set(w for w in word if w in words)


def suggest(word, words):
    candidates = (known([word], words) or
                  known(edits1(word), words) or
                  known_edits2(word, words) or [word])
    return candidates


def correct(word, words):
    candidates = suggest(word, words)
    return max(candidates, key=words.get)


class NorvigSpellCheck(object):
    def __init__(self):
        self.words = collections.defaultdict(lambda: 1)
        self.extra_words = set()
        self.initialized = False

    def init(self):
        if self.initialized:
            return
        self.initialized = True
        train(self.read(), self.words)
        train(self.extra_words, self.words)

    def add_word(self, word):
        self.extra_words.add(word)

    def suggest(self, word):
        self.init()
        return suggest(word, self.words)

    def check(self, word):
        self.init()
        return word.replace('.', '') in self.words

    def read(self):
        for (path, title) in (('/usr/share/dict/words', True),
                              ('/usr/share/dict/propernames', False)):
            try:
                with open(path, 'r') as f:
                    for word in f:
                        yield word.rstrip()
                        if title:
                            yield word.rstrip().title()
            except IOError:
                pass
        raise StopIteration


class SpellCheckTextEdit(HintedTextEdit):

    def __init__(self, hint, parent=None):
        HintedTextEdit.__init__(self, hint, parent)

        # Default dictionary based on the current locale.
        self.spellcheck = NorvigSpellCheck()
        self.highlighter = Highlighter(self.document(), self.spellcheck)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Rewrite the mouse event to a left button event so the cursor is
            # moved to the location of the pointer.
            event = QMouseEvent(QEvent.MouseButtonPress,
                                event.pos(),
                                Qt.LeftButton,
                                Qt.LeftButton,
                                Qt.NoModifier)
        HintedTextEdit.mousePressEvent(self, event)

    def context_menu(self):
        popup_menu = HintedTextEdit.createStandardContextMenu(self)

        # Select the word under the cursor.
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        self.setTextCursor(cursor)

        # Check if the selected word is misspelled and offer spelling
        # suggestions if it is.
        spell_menu = None
        if self.textCursor().hasSelection():
            text = ustr(self.textCursor().selectedText())
            if not self.spellcheck.check(text):
                spell_menu = QMenu(N_('Spelling Suggestions'))
                for word in self.spellcheck.suggest(text):
                    action = SpellAction(word, spell_menu)
                    self.connect(action, SIGNAL('correct'), self.correct)
                    spell_menu.addAction(action)
                # Only add the spelling suggests to the menu if there are
                # suggestions.
                if len(spell_menu.actions()) > 0:
                    popup_menu.addSeparator()
                    popup_menu.addMenu(spell_menu)

        return popup_menu, spell_menu

    def contextMenuEvent(self, event):
        popup_menu, _spell_menu = self.context_menu()
        popup_menu.exec_(self.mapToGlobal(event.pos()))

    def correct(self, word):
        """Replaces the selected text with word."""
        cursor = self.textCursor()
        cursor.beginEditBlock()

        cursor.removeSelectedText()
        cursor.insertText(word)

        cursor.endEditBlock()


class Highlighter(QSyntaxHighlighter):

    WORDS = r"(?iu)[\w']+"

    def __init__(self, doc, spellcheck):
        QSyntaxHighlighter.__init__(self, doc)
        self.spellcheck = spellcheck
        self.enabled = False

    def enable(self, enabled):
        self.enabled = enabled
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.enabled:
            return
        text = ustr(text)
        fmt = QTextCharFormat()
        fmt.setUnderlineColor(Qt.red)
        fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)

        for word_object in re.finditer(self.WORDS, text):
            if not self.spellcheck.check(word_object.group()):
                self.setFormat(word_object.start(),
                    word_object.end() - word_object.start(), fmt)


class SpellAction(QAction):
    """QAction that returns the text in a signal.
    """

    def __init__(self, *args):
        QAction.__init__(self, *args)
        self.connect(self, SIGNAL('triggered()'), self.correct)

    def correct(self):
        self.emit(SIGNAL('correct'), ustr(self.text()))


def main(args=sys.argv):
    app = QApplication(args)

    widget = SpellCheckTextEdit('Type here')
    widget.show()
    widget.raise_()

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())

########NEW FILE########
__FILENAME__ = standard
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDockWidget

from cola import core
from cola import gitcfg
from cola import qtcompat
from cola.settings import Settings


class WidgetMixin(object):
    """Mix-in for common utilities and serialization of widget state"""

    def __init__(self, QtClass):
        self.QtClass = QtClass
        self._apply_state_applied = False

    def show(self):
        """Automatically centers dialogs"""
        if not self._apply_state_applied and self.parent() is not None:
            left = self.parent().x()
            width = self.parent().width()
            center_x = left + width//2

            x = center_x - self.width()//2
            y = self.parent().y()

            self.move(x, y)
        # Call the base Qt show()
        return self.QtClass.show(self)

    def name(self):
        """Returns the name of the view class"""
        return self.__class__.__name__.lower()

    def save_state(self, settings=None):
        if settings is None:
            settings = Settings()
            settings.load()
        if gitcfg.instance().get('cola.savewindowsettings', True):
            settings.save_gui_state(self)

    def restore_state(self, settings=None):
        if settings is None:
            settings = Settings()
            settings.load()
        state = settings.get_gui_state(self)
        return bool(state) and self.apply_state(state)

    def apply_state(self, state):
        """Imports data for view save/restore"""
        result = True
        try:
            self.resize(state['width'], state['height'])
        except:
            result = False
        try:
            self.move(state['x'], state['y'])
        except:
            result = False
        try:
            if state['maximized']:
                self.showMaximized()
        except:
            result = False
        self._apply_state_applied = result
        return result

    def export_state(self):
        """Exports data for view save/restore"""
        state = self.windowState()
        maximized = bool(state & Qt.WindowMaximized)
        return {
            'x': self.x(),
            'y': self.y(),
            'width': self.width(),
            'height': self.height(),
            'maximized': maximized,
        }

    def closeEvent(self, event):
        settings = Settings()
        settings.load()
        settings.add_recent(core.getcwd())
        self.save_state(settings=settings)
        self.QtClass.closeEvent(self, event)


class MainWindowMixin(WidgetMixin):

    def __init__(self, QtClass):
        WidgetMixin.__init__(self, QtClass)
        # Dockwidget options
        self.dockwidgets = []
        self.lock_layout = False
        self.widget_version = 0
        qtcompat.set_common_dock_options(self)

    def export_state(self):
        """Exports data for save/restore"""
        state = WidgetMixin.export_state(self)
        windowstate = self.saveState(self.widget_version)
        state['lock_layout'] = self.lock_layout
        state['windowstate'] = windowstate.toBase64().data().decode('ascii')
        return state

    def apply_state(self, state):
        result = WidgetMixin.apply_state(self, state)
        windowstate = state.get('windowstate', None)
        if windowstate is None:
            result = False
        else:
            result = self.restoreState(QtCore.QByteArray.fromBase64(str(windowstate)),
                                       self.widget_version) and result
        self.lock_layout = state.get('lock_layout', self.lock_layout)
        self.update_dockwidget_lock_state()
        self.update_dockwidget_tooltips()
        return result

    def set_lock_layout(self, lock_layout):
        self.lock_layout = lock_layout
        self.update_dockwidget_lock_state()

    def update_dockwidget_lock_state(self):
        if self.lock_layout:
            features = (QDockWidget.DockWidgetClosable |
                        QDockWidget.DockWidgetFloatable)
        else:
            features = (QDockWidget.DockWidgetClosable |
                        QDockWidget.DockWidgetFloatable |
                        QDockWidget.DockWidgetMovable)
        for widget in self.dockwidgets:
            widget.titleBarWidget().update_tooltips()
            widget.setFeatures(features)

    def update_dockwidget_tooltips(self):
        for widget in self.dockwidgets:
            widget.titleBarWidget().update_tooltips()


class TreeMixin(object):

    def __init__(self, QtClass):
        self.QtClass = QtClass
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setAnimated(True)
        self.setRootIsDecorated(False)

    def keyPressEvent(self, event):
        """
        Make LeftArrow to work on non-directories.

        When LeftArrow is pressed on a file entry or an unexpanded
        directory, then move the current index to the parent directory.

        This simplifies navigation using the keyboard.
        For power-users, we support Vim keybindings ;-P

        """
        # Check whether the item is expanded before calling the base class
        # keyPressEvent otherwise we end up collapsing and changing the
        # current index in one shot, which we don't want to do.
        index = self.currentIndex()
        was_expanded = self.isExpanded(index)
        was_collapsed = not was_expanded

        # Vim keybindings...
        # Rewrite the event before marshalling to QTreeView.event()
        key = event.key()

        # Remap 'H' to 'Left'
        if key == Qt.Key_H:
            event = QtGui.QKeyEvent(event.type(),
                                    Qt.Key_Left,
                                    event.modifiers())
        # Remap 'J' to 'Down'
        elif key == Qt.Key_J:
            event = QtGui.QKeyEvent(event.type(),
                                    Qt.Key_Down,
                                    event.modifiers())
        # Remap 'K' to 'Up'
        elif key == Qt.Key_K:
            event = QtGui.QKeyEvent(event.type(),
                                    Qt.Key_Up,
                                    event.modifiers())
        # Remap 'L' to 'Right'
        elif key == Qt.Key_L:
            event = QtGui.QKeyEvent(event.type(),
                                    Qt.Key_Right,
                                    event.modifiers())

        # Re-read the event key to take the remappings into account
        key = event.key()
        result = self.QtClass.keyPressEvent(self, event)

        # Let others hook in here before we change the indexes
        self.emit(SIGNAL('indexAboutToChange()'))

        # Automatically select the first entry when expanding a directory
        if (key == Qt.Key_Right and was_collapsed and
                self.isExpanded(index)):
            index = self.moveCursor(self.MoveDown, event.modifiers())
            self.setCurrentIndex(index)

        # Process non-root entries with valid parents only.
        elif key == Qt.Key_Left and index.parent().isValid():

            # File entries have rowCount() == 0
            if self.model().itemFromIndex(index).rowCount() == 0:
                self.setCurrentIndex(index.parent())

            # Otherwise, do this for collapsed directories only
            elif was_collapsed:
                self.setCurrentIndex(index.parent())

        # If it's a movement key ensure we have a selection
        elif key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_Right, Qt.Key_Down):
            # Try to select the first item if the model index is invalid
            item = self.selected_item()
            if item is None or not index.isValid():
                index = self.model().index(0, 0, QtCore.QModelIndex())
                if index.isValid():
                    self.setCurrentIndex(index)

        return result

    def items(self):
        root = self.invisibleRootItem()
        child = root.child
        count = root.childCount()
        return [child(i) for i in range(count)]

    def selected_items(self):
        """Return all selected items"""
        if hasattr(self, 'selectedItems'):
            return self.selectedItems()
        else:
            item_from_index = self.model().itemFromIndex
            return [item_from_index(i) for i in self.selectedIndexes()]

    def selected_item(self):
        """Return the first selected item"""
        selected_items = self.selected_items()
        if not selected_items:
            return None
        return selected_items[0]


class DraggableTreeMixin(TreeMixin):
    """A tree widget with internal drag+drop reordering of rows"""

    def __init__(self, QtClass):
        super(DraggableTreeMixin, self).__init__(QtClass)
        self.setAcceptDrops(True)
        self.setSelectionMode(self.SingleSelection)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.setSortingEnabled(False)
        self._inner_drag = False

    def dragEnterEvent(self, event):
        """Accept internal drags only"""
        self.QtClass.dragEnterEvent(self, event)
        self._inner_drag = event.source() == self
        if self._inner_drag:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.QtClass.dragLeaveEvent(self, event)
        if self._inner_drag:
            event.accept()
        else:
            event.ignore()
        self._inner_drag = False

    def dropEvent(self, event):
        """Re-select selected items after an internal move"""
        if not self._inner_drag:
            event.ignore()
            return
        clicked_items = self.selected_items()
        event.setDropAction(Qt.MoveAction)
        self.QtClass.dropEvent(self, event)

        if clicked_items:
            self.clearSelection()
            for item in clicked_items:
                self.setItemSelected(item, True)
        self._inner_drag = False
        event.accept() # must be called after dropEvent()

    def mousePressEvent(self, event):
        """Clear the selection when a mouse click hits no item"""
        clicked_item = self.itemAt(event.pos())
        if clicked_item is None:
            self.clearSelection()
        return self.QtClass.mousePressEvent(self, event)


class Widget(WidgetMixin, QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, QtGui.QWidget)


class Dialog(WidgetMixin, QtGui.QDialog):

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        WidgetMixin.__init__(self, QtGui.QDialog)


class MainWindow(MainWindowMixin, QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        MainWindowMixin.__init__(self, QtGui.QMainWindow)


class TreeView(TreeMixin, QtGui.QTreeView):

    def __init__(self, parent=None):
        QtGui.QTreeView.__init__(self, parent)
        TreeMixin.__init__(self, QtGui.QTreeView)


class TreeWidget(TreeMixin, QtGui.QTreeWidget):

    def __init__(self, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        TreeMixin.__init__(self, QtGui.QTreeWidget)


class DraggableTreeWidget(DraggableTreeMixin, QtGui.QTreeWidget):

    def __init__(self, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        DraggableTreeMixin.__init__(self, QtGui.QTreeWidget)

########NEW FILE########
__FILENAME__ = startup
"""
Provides the git-cola startup dialog

The startup dialog is presented when no repositories can be
found at startup.

"""
from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import guicmds
from cola import qtutils
from cola.compat import ustr
from cola.i18n import N_
from cola.settings import Settings
from cola.widgets import defs


class StartupDialog(QtGui.QDialog):
    """Provides a GUI to Open or Clone a git repository."""

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(N_('git-cola'))
        self._gitdir = None

        self._layt = QtGui.QHBoxLayout()
        self._layt.setMargin(defs.margin)
        self._layt.setSpacing(defs.spacing)

        self._new_btn = QtGui.QPushButton(N_('New...'))
        self._new_btn.setIcon(qtutils.new_icon())

        self._open_btn = QtGui.QPushButton(N_('Open...'))
        self._open_btn.setIcon(qtutils.open_icon())

        self._clone_btn = QtGui.QPushButton(N_('Clone...'))
        self._clone_btn.setIcon(qtutils.git_icon())

        self._close_btn = QtGui.QPushButton(N_('Close'))

        self._layt.addWidget(self._open_btn)
        self._layt.addWidget(self._clone_btn)
        self._layt.addWidget(self._new_btn)
        self._layt.addStretch()
        self._layt.addWidget(self._close_btn)

        settings = Settings()
        settings.load()

        self._vlayt = QtGui.QVBoxLayout()
        self._vlayt.setMargin(defs.margin)
        self._vlayt.setSpacing(defs.margin)

        self._bookmark_label = QtGui.QLabel(N_('Select Repository...'))
        self._bookmark_label.setAlignment(Qt.AlignCenter)

        self._bookmark_model = QtGui.QStandardItemModel()

        item = QtGui.QStandardItem(N_('Select manually...'))
        item.setEditable(False)
        self._bookmark_model.appendRow(item)

        added = set()
        all_repos = settings.bookmarks + settings.recent

        for repo in all_repos:
            if repo in added:
                continue
            added.add(repo)
            item = QtGui.QStandardItem(repo)
            item.setEditable(False)
            self._bookmark_model.appendRow(item)

        selection_mode = QtGui.QAbstractItemView.SingleSelection

        self._bookmark_list = QtGui.QListView()
        self._bookmark_list.setSelectionMode(selection_mode)
        self._bookmark_list.setAlternatingRowColors(True)
        self._bookmark_list.setModel(self._bookmark_model)

        if not all_repos:
            self._bookmark_label.setMinimumHeight(1)
            self._bookmark_list.setMinimumHeight(1)
            self._bookmark_label.hide()
            self._bookmark_list.hide()

        self._vlayt.addWidget(self._bookmark_label)
        self._vlayt.addWidget(self._bookmark_list)
        self._vlayt.addLayout(self._layt)

        self.setLayout(self._vlayt)

        qtutils.connect_button(self._open_btn, self._open)
        qtutils.connect_button(self._clone_btn, self._clone)
        qtutils.connect_button(self._new_btn, self._new)
        qtutils.connect_button(self._close_btn, self.reject)

        self.connect(self._bookmark_list,
                     SIGNAL('activated(const QModelIndex &)'),
                     self._open_bookmark)


    def find_git_repo(self):
        """
        Return a path to a git repository

        This is the entry point for external callers.
        This method finds a git repository by allowing the
        user to browse to one on the filesystem or by creating
        a new one with git-clone.

        """
        self.show()
        self.raise_()
        if self.exec_() == QtGui.QDialog.Accepted:
            return self._gitdir
        return None

    def _open(self):
        self._gitdir = self._get_selected_bookmark()
        if not self._gitdir:
            self._gitdir = qtutils.opendir_dialog(N_('Open Git Repository...'),
                                                  os.getcwd())
        if self._gitdir:
            self.accept()

    def _clone(self):
        gitdir = guicmds.clone_repo(spawn=False)
        if gitdir:
            self._gitdir = gitdir
            self.accept()

    def _new(self):
        gitdir = guicmds.new_repo()
        if gitdir:
            self._gitdir = gitdir
            self.accept()

    def _open_bookmark(self, index):
        if(index.row() == 0):
            self._open()
        else:
            self._gitdir = ustr(self._bookmark_model.data(index).toString())
            if self._gitdir:
                self.accept()

    def _get_selected_bookmark(self):
        selected = self._bookmark_list.selectedIndexes()
        if(len(selected) > 0 and selected[0].row() != 0):
            return ustr(self._bookmark_model.data(selected[0]).toString())
        return None

########NEW FILE########
__FILENAME__ = stash
"""Provides the StashView dialog."""
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.models.stash import StashModel
from cola.models.stash import ApplyStash
from cola.models.stash import SaveStash
from cola.models.stash import DropStash
from cola.widgets import defs
from cola.widgets.diff import DiffTextEdit
from cola.widgets.standard import Dialog


def stash():
    """Launches a stash dialog using the provided model + view
    """
    model = StashModel()
    view = StashView(model, qtutils.active_window())
    view.show()
    view.raise_()
    return view


class StashView(Dialog):
    def __init__(self, model, parent=None):
        Dialog.__init__(self, parent=parent)
        self.model = model
        self.stashes = []
        self.revids = []
        self.names = []

        self.setWindowTitle(N_('Stash'))
        self.setAttribute(QtCore.Qt.WA_MacMetalStyle)
        if parent is not None:
            self.setWindowModality(QtCore.Qt.WindowModal)
            self.resize(parent.width(), 420)
        else:
            self.resize(700, 420)

        self.stash_list = QtGui.QListWidget(self)
        self.stash_text = DiffTextEdit(self)

        self.button_apply =\
            self.toolbutton(N_('Apply'),
                            N_('Apply the selected stash'),
                            qtutils.apply_icon())
        self.button_save =\
            self.toolbutton(N_('Save'),
                            N_('Save modified state to new stash'),
                            qtutils.save_icon())
        self.button_drop = \
            self.toolbutton(N_('Drop'),
                            N_('Drop the selected stash'),
                            qtutils.discard_icon())
        self.button_close = \
            self.pushbutton(N_('Close'),
                            N_('Close'), qtutils.close_icon())

        self.keep_index = QtGui.QCheckBox(self)
        self.keep_index.setText(N_('Keep Index'))
        self.keep_index.setChecked(True)

        # Arrange layouts
        self.main_layt = QtGui.QVBoxLayout()
        self.main_layt.setMargin(defs.margin)
        self.main_layt.setSpacing(defs.spacing)

        self.btn_layt = QtGui.QHBoxLayout()
        self.btn_layt.setMargin(0)
        self.btn_layt.setSpacing(defs.spacing)

        self.splitter = QtGui.QSplitter()
        self.splitter.setHandleWidth(defs.handle_width)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.insertWidget(0, self.stash_list)
        self.splitter.insertWidget(1, self.stash_text)

        self.btn_layt.addWidget(self.button_save)
        self.btn_layt.addWidget(self.button_apply)
        self.btn_layt.addWidget(self.button_drop)
        self.btn_layt.addWidget(self.keep_index)
        self.btn_layt.addStretch()
        self.btn_layt.addWidget(self.button_close)

        self.main_layt.addWidget(self.splitter)
        self.main_layt.addLayout(self.btn_layt)
        self.setLayout(self.main_layt)

        self.splitter.setSizes([self.width()//3, self.width()*2//3])

        self.update_from_model()
        self.update_actions()

        self.setTabOrder(self.button_save, self.button_apply)
        self.setTabOrder(self.button_apply, self.button_drop)
        self.setTabOrder(self.button_drop, self.keep_index)
        self.setTabOrder(self.keep_index, self.button_close)

        self.connect(self.stash_list, SIGNAL('itemSelectionChanged()'),
                     self.item_selected)

        qtutils.connect_button(self.button_apply, self.stash_apply)
        qtutils.connect_button(self.button_save, self.stash_save)
        qtutils.connect_button(self.button_drop, self.stash_drop)
        qtutils.connect_button(self.button_close, self.close)

    def close(self):
        self.accept()
        cmds.do(cmds.Rescan)

    def toolbutton(self, text, tooltip, icon):
        return qtutils.create_toolbutton(text=text, tooltip=tooltip, icon=icon)

    def pushbutton(self, text, tooltip, icon):
        btn = QtGui.QPushButton(self)
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.setIcon(icon)
        return btn

    def selected_stash(self):
        """Returns the stash name of the currently selected stash
        """
        list_widget = self.stash_list
        stash_list = self.revids
        return qtutils.selected_item(list_widget, stash_list)

    def selected_name(self):
        list_widget = self.stash_list
        stash_list = self.names
        return qtutils.selected_item(list_widget, stash_list)

    def item_selected(self):
        """Shows the current stash in the main view."""
        self.update_actions()
        selection = self.selected_stash()
        if not selection:
            return
        diff_text = self.model.stash_diff(selection)
        self.stash_text.setPlainText(diff_text)

    def update_actions(self):
        has_changes = self.model.has_stashable_changes()
        has_stash = bool(self.selected_stash())
        self.button_save.setEnabled(has_changes)
        self.button_apply.setEnabled(has_stash)
        self.button_drop.setEnabled(has_stash)

    def update_from_model(self):
        """Initiates git queries on the model and updates the view
        """
        stashes, revids, names = self.model.stash_info()
        self.stashes = stashes
        self.revids = revids
        self.names = names

        self.stash_list.clear()
        self.stash_list.addItems(self.stashes)

    def stash_apply(self):
        """Applies the currently selected stash
        """
        selection = self.selected_stash()
        if not selection:
            return
        index = self.keep_index.isChecked()
        cmds.do(ApplyStash, selection, index)
        self.accept()
        cmds.do(cmds.Rescan)

    def stash_save(self):
        """Saves the worktree in a stash

        This prompts the user for a stash name and creates
        a git stash named accordingly.

        """
        stash_name, ok = qtutils.prompt(N_('Save Stash'),
                                        N_('Enter a name for the stash'))
        if not ok or not stash_name:
            return
        # Sanitize the stash name
        stash_name = utils.sanitize(stash_name)
        if stash_name in self.names:
            qtutils.critical(N_('Error: Stash exists'),
                             N_('A stash named "%s" already exists') % stash_name)
            return

        keep_index = self.keep_index.isChecked()
        cmds.do(SaveStash, stash_name, keep_index)
        self.accept()
        cmds.do(cmds.Rescan)

    def stash_drop(self):
        """Drops the currently selected stash
        """
        selection = self.selected_stash()
        name = self.selected_name()
        if not selection:
            return
        if not qtutils.confirm(N_('Drop Stash?'),
                               N_('Recovering a dropped stash is not possible.'),
                               N_('Drop the "%s" stash?') % name,
                               N_('Drop Stash'),
                               default=True,
                               icon=qtutils.discard_icon()):
            return
        cmds.do(DropStash, selection)
        self.update_from_model()
        self.stash_text.setPlainText('')

########NEW FILE########
__FILENAME__ = status
from __future__ import division, absolute_import, unicode_literals

import os
import subprocess
import itertools

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.models import selection


class StatusWidget(QtGui.QWidget):
    """
    Provides a git-status-like repository widget.

    This widget observes the main model and broadcasts
    Qt signals.

    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.layout = QtGui.QVBoxLayout(self)
        self.setLayout(self.layout)

        self.tree = StatusTreeWidget(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def set_initial_size(self):
        self.setMaximumWidth(222)
        QtCore.QTimer.singleShot(1, self.restore_size)

    def restore_size(self):
        self.setMaximumWidth(2 ** 13)

    def refresh(self):
        self.tree.show_selection()


class StatusTreeWidget(QtGui.QTreeWidget):
    # Item categories
    idx_header = -1
    idx_staged = 0
    idx_unmerged = 1
    idx_modified = 2
    idx_untracked = 3
    idx_end = 4

    # Read-only access to the mode state
    mode = property(lambda self: self.m.mode)

    def __init__(self, parent):
        QtGui.QTreeWidget.__init__(self, parent)

        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.headerItem().setHidden(True)
        self.setAllColumnsShowFocus(True)
        self.setSortingEnabled(False)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setRootIsDecorated(False)
        self.setIndentation(0)

        self.add_item(N_('Staged'), hide=True)
        self.add_item(N_('Unmerged'), hide=True)
        self.add_item(N_('Modified'), hide=True)
        self.add_item(N_('Untracked'), hide=True)

        # Used to restore the selection
        self.old_scroll = None
        self.old_selection = None
        self.old_contents = None
        self.old_current_item = None
        self.expanded_items = set()

        self.process_selection = qtutils.add_action(self,
                N_('Stage / Unstage'), self._process_selection,
                cmds.Stage.SHORTCUT)

        self.revert_unstaged_edits_action = qtutils.add_action(self,
                N_('Revert Unstaged Edits...'),
                cmds.run(cmds.RevertUnstagedEdits),
                cmds.RevertUnstagedEdits.SHORTCUT)
        self.revert_unstaged_edits_action.setIcon(qtutils.icon('undo.svg'))

        self.launch_difftool = qtutils.add_action(self,
                cmds.LaunchDifftool.name(),
                cmds.run(cmds.LaunchDifftool),
                cmds.LaunchDifftool.SHORTCUT)
        self.launch_difftool.setIcon(qtutils.icon('git.svg'))

        self.launch_editor = qtutils.add_action(self,
                cmds.LaunchEditor.name(),
                cmds.run(cmds.LaunchEditor),
                cmds.LaunchEditor.SHORTCUT,
                'Return', 'Enter')
        self.launch_editor.setIcon(qtutils.options_icon())

        if not utils.is_win32():
            self.open_using_default_app = qtutils.add_action(self,
                    cmds.OpenDefaultApp.name(),
                    self._open_using_default_app,
                    cmds.OpenDefaultApp.SHORTCUT)
            self.open_using_default_app.setIcon(qtutils.file_icon())

            self.open_parent_dir = qtutils.add_action(self,
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir,
                    cmds.OpenParentDir.SHORTCUT)
            self.open_parent_dir.setIcon(qtutils.open_file_icon())

        self.up = qtutils.add_action(self, N_('Move Up'), self.move_up,
                                     Qt.Key_K)

        self.down = qtutils.add_action(self, N_('Move Down'), self.move_down,
                                       Qt.Key_J)

        self.copy_path_action = qtutils.add_action(self,
                N_('Copy Path to Clipboard'),
                self.copy_path, QtGui.QKeySequence.Copy)
        self.copy_path_action.setIcon(qtutils.theme_icon('edit-copy.svg'))

        self.connect(self, SIGNAL('about_to_update'), self._about_to_update)
        self.connect(self, SIGNAL('updated'), self._updated)

        self.m = main.model()
        self.m.add_observer(self.m.message_about_to_update,
                            self.about_to_update)
        self.m.add_observer(self.m.message_updated, self.updated)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.show_selection)

        self.connect(self, SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self.double_clicked)

        self.connect(self, SIGNAL('itemCollapsed(QTreeWidgetItem*)'),
                     lambda x: self.update_column_widths())

        self.connect(self, SIGNAL('itemExpanded(QTreeWidgetItem*)'),
                     lambda x: self.update_column_widths())

    def add_item(self, txt, hide=False):
        """Create a new top-level item in the status tree."""
        # TODO no icon
        font = self.font()
        font.setBold(True)

        item = QtGui.QTreeWidgetItem(self)
        item.setFont(0, font)
        item.setText(0, txt)
        if hide:
            self.setItemHidden(item, True)

    def restore_selection(self):
        if not self.old_selection or not self.old_contents:
            return
        old_c = self.old_contents
        old_s = self.old_selection
        new_c = self.contents()

        def mkselect(lst, widget_getter):
            def select(item, current=False):
                idx = lst.index(item)
                widget = widget_getter(idx)
                if current:
                    self.setCurrentItem(widget)
                self.setItemSelected(widget, True)
            return select

        select_staged = mkselect(new_c.staged, self.staged_item)
        select_unmerged = mkselect(new_c.unmerged, self.unmerged_item)
        select_modified = mkselect(new_c.modified, self.modified_item)
        select_untracked = mkselect(new_c.untracked, self.untracked_item)

        saved_selection = [
        (set(new_c.staged), old_c.staged, set(old_s.staged),
            select_staged),

        (set(new_c.unmerged), old_c.unmerged, set(old_s.unmerged),
            select_unmerged),

        (set(new_c.modified), old_c.modified, set(old_s.modified),
            select_modified),

        (set(new_c.untracked), old_c.untracked, set(old_s.untracked),
            select_untracked),
        ]

        # Restore the current item
        if self.old_current_item:
            category, idx = self.old_current_item
            if category == self.idx_header:
                item = self.invisibleRootItem().child(idx)
                if item is not None:
                    self.setCurrentItem(item)
                    self.setItemSelected(item, True)
                return
            # Reselect the current item
            selection_info = saved_selection[category]
            new = selection_info[0]
            old = selection_info[1]
            reselect = selection_info[3]
            try:
                item = old[idx]
            except:
                return
            if item in new:
                reselect(item, current=True)

        # Restore selection
        # When reselecting we only care that the items are selected;
        # we do not need to rerun the callbacks which were triggered
        # above.  Block signals to skip the callbacks.
        self.blockSignals(True)
        for (new, old, sel, reselect) in saved_selection:
            for item in sel:
                if item in new:
                    reselect(item, current=False)
        self.blockSignals(False)

        for (new, old, sel, reselect) in saved_selection:
            # When modified is staged, select the next modified item
            # When unmerged is staged, select the next unmerged item
            # When unstaging, select the next staged item
            # When staging untracked files, select the next untracked item
            if len(new) >= len(old):
                # The list did not shrink so it is not one of these cases.
                continue
            for item in sel:
                # The item still exists so ignore it
                if item in new or item not in old:
                    continue
                # The item no longer exists in this list so search for
                # its nearest neighbors and select them instead.
                idx = old.index(item)
                for j in itertools.chain(old[idx+1:], reversed(old[:idx])):
                    if j in new:
                        reselect(j, current=True)
                        return

    def restore_scrollbar(self):
        vscroll = self.verticalScrollBar()
        if vscroll and self.old_scroll is not None:
            vscroll.setValue(self.old_scroll)
            self.old_scroll = None

    def staged_item(self, itemidx):
        return self._subtree_item(self.idx_staged, itemidx)

    def modified_item(self, itemidx):
        return self._subtree_item(self.idx_modified, itemidx)

    def unmerged_item(self, itemidx):
        return self._subtree_item(self.idx_unmerged, itemidx)

    def untracked_item(self, itemidx):
        return self._subtree_item(self.idx_untracked, itemidx)

    def unstaged_item(self, itemidx):
        # is it modified?
        item = self.topLevelItem(self.idx_modified)
        count = item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # is it unmerged?
        item = self.topLevelItem(self.idx_unmerged)
        count += item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # is it untracked?
        item = self.topLevelItem(self.idx_untracked)
        count += item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # Nope..
        return None

    def _subtree_item(self, idx, itemidx):
        parent = self.topLevelItem(idx)
        return parent.child(itemidx)

    def about_to_update(self):
        self.emit(SIGNAL('about_to_update'))

    def _about_to_update(self):
        self.save_selection()
        self.save_scrollbar()

    def save_scrollbar(self):
        vscroll = self.verticalScrollBar()
        if vscroll:
            self.old_scroll = vscroll.value()
        else:
            self.old_scroll = None

    def current_item(self):
        s = self.selected_indexes()
        if not s:
            return None
        current = self.currentItem()
        if not current:
            return None
        idx = self.indexFromItem(current, 0)
        if idx.parent().isValid():
            parent_idx = idx.parent()
            entry = (parent_idx.row(), idx.row())
        else:
            entry = (self.idx_header, idx.row())
        return entry

    def save_selection(self):
        self.old_contents = self.contents()
        self.old_selection = self.selection()
        self.old_current_item = self.current_item()

    def updated(self):
        """Update display from model data."""
        self.emit(SIGNAL('updated'))

    def _updated(self):
        self.set_staged(self.m.staged)
        self.set_modified(self.m.modified)
        self.set_unmerged(self.m.unmerged)
        self.set_untracked(self.m.untracked)
        self.restore_selection()
        self.restore_scrollbar()
        self.update_column_widths()
        self.update_actions()

    def update_actions(self, selected=None):
        if selected is None:
            selected = selection.selection()
        can_revert_unstaged_edits = bool(selected.staged or selected.modified)
        self.revert_unstaged_edits_action.setEnabled(can_revert_unstaged_edits)

    def set_staged(self, items):
        """Adds items to the 'Staged' subtree."""
        self._set_subtree(items, self.idx_staged, staged=True,
                          check=not self.m.amending())

    def set_modified(self, items):
        """Adds items to the 'Modified' subtree."""
        self._set_subtree(items, self.idx_modified)

    def set_unmerged(self, items):
        """Adds items to the 'Unmerged' subtree."""
        self._set_subtree(items, self.idx_unmerged)

    def set_untracked(self, items):
        """Adds items to the 'Untracked' subtree."""
        self._set_subtree(items, self.idx_untracked)

    def _set_subtree(self, items, idx,
                     staged=False,
                     untracked=False,
                     check=True):
        """Add a list of items to a treewidget item."""
        self.blockSignals(True)
        parent = self.topLevelItem(idx)
        if items:
            self.setItemHidden(parent, False)
        else:
            self.setItemHidden(parent, True)

        # sip v4.14.7 and below leak memory in parent.takeChildren()
        # so we use this backwards-compatible construct instead
        while parent.takeChild(0) is not None:
            pass

        for item in items:
            treeitem = qtutils.create_treeitem(item,
                                               staged=staged,
                                               check=check,
                                               untracked=untracked)
            parent.addChild(treeitem)
        self.expand_items(idx, items)
        self.blockSignals(False)

    def update_column_widths(self):
        self.resizeColumnToContents(0)

    def expand_items(self, idx, items):
        """Expand the top-level category "folder" once and only once."""
        # Don't do this if items is empty; this makes it so that we
        # don't add the top-level index into the expanded_items set
        # until an item appears in a particular category.
        if not items:
            return
        # Only run this once; we don't want to re-expand items that
        # we've clicked on to re-collapse on updated().
        if idx in self.expanded_items:
            return
        self.expanded_items.add(idx)
        item = self.topLevelItem(idx)
        if item:
            self.expandItem(item)

    def contextMenuEvent(self, event):
        """Create context menus for the repo status tree."""
        menu = self.create_context_menu()
        menu.exec_(self.mapToGlobal(event.pos()))

    def create_context_menu(self):
        """Set up the status menu for the repo status tree."""
        s = self.selection()
        menu = QtGui.QMenu(self)

        selected_indexes = self.selected_indexes()
        if selected_indexes:
            category, idx = selected_indexes[0]
            # A header item e.g. 'Staged', 'Modified', etc.
            if category == self.idx_header:
                return self._create_header_context_menu(menu, idx)

        if s.staged:
            return self._create_staged_context_menu(menu, s)

        elif s.unmerged:
            return self._create_unmerged_context_menu(menu, s)
        else:
            return self._create_unstaged_context_menu(menu, s)

    def _create_header_context_menu(self, menu, idx):
        if idx == self.idx_staged:
            menu.addAction(qtutils.icon('remove.svg'),
                           N_('Unstage All'),
                           cmds.run(cmds.UnstageAll))
            return menu
        elif idx == self.idx_unmerged:
            action = menu.addAction(qtutils.icon('add.svg'),
                                    cmds.StageUnmerged.name(),
                                    cmds.run(cmds.StageUnmerged))
            action.setShortcut(cmds.StageUnmerged.SHORTCUT)
            return menu
        elif idx == self.idx_modified:
            action = menu.addAction(qtutils.icon('add.svg'),
                                    cmds.StageModified.name(),
                                    cmds.run(cmds.StageModified))
            action.setShortcut(cmds.StageModified.SHORTCUT)
            return menu

        elif idx == self.idx_untracked:
            action = menu.addAction(qtutils.icon('add.svg'),
                                    cmds.StageUntracked.name(),
                                    cmds.run(cmds.StageUntracked))
            action.setShortcut(cmds.StageUntracked.SHORTCUT)
            return menu

    def _create_staged_context_menu(self, menu, s):
        if s.staged[0] in self.m.submodules:
            return self._create_staged_submodule_context_menu(menu, s)

        if self.m.unstageable():
            action = menu.addAction(qtutils.icon('remove.svg'),
                                    N_('Unstage Selected'),
                                    cmds.run(cmds.Unstage, self.staged()))
            action.setShortcut(cmds.Unstage.SHORTCUT)

        # Do all of the selected items exist?
        staged_items = self.staged_items()
        all_exist = all([i.exists for i in staged_items])

        if all_exist:
            menu.addAction(self.launch_editor)
            menu.addAction(self.launch_difftool)

        if all_exist and not utils.is_win32():
            menu.addSeparator()
            action = menu.addAction(qtutils.file_icon(),
                    cmds.OpenDefaultApp.name(),
                    cmds.run(cmds.OpenDefaultApp, self.staged()))
            action.setShortcut(cmds.OpenDefaultApp.SHORTCUT)

            action = menu.addAction(qtutils.open_file_icon(),
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir)
            action.setShortcut(cmds.OpenParentDir.SHORTCUT)

        if self.m.undoable():
            menu.addSeparator()
            menu.addAction(self.revert_unstaged_edits_action)
            menu.addAction(qtutils.icon('undo.svg'),
                           N_('Revert Uncommited Edits...'),
                           lambda: self._revert_uncommitted_edits(
                                        self.staged()))
        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu

    def _create_staged_submodule_context_menu(self, menu, s):
        menu.addAction(qtutils.git_icon(),
                       N_('Launch git-cola'),
                       cmds.run(cmds.OpenRepo,
                                core.abspath(s.staged[0])))

        menu.addAction(self.launch_editor)
        menu.addSeparator()

        action = menu.addAction(qtutils.icon('remove.svg'),
                                N_('Unstage Selected'),
                                cmds.run(cmds.Unstage, self.staged()))
        action.setShortcut(cmds.Unstage.SHORTCUT)
        menu.addSeparator()

        menu.addAction(self.copy_path_action)
        return menu

    def _create_unmerged_context_menu(self, menu, s):
        menu.addAction(self.launch_difftool)

        action = menu.addAction(qtutils.icon('add.svg'),
                                N_('Stage Selected'),
                                cmds.run(cmds.Stage, self.unstaged()))
        action.setShortcut(cmds.Stage.SHORTCUT)
        menu.addSeparator()
        menu.addAction(self.launch_editor)

        if not utils.is_win32():
            menu.addSeparator()
            action = menu.addAction(qtutils.file_icon(),
                    cmds.OpenDefaultApp.name(),
                    cmds.run(cmds.OpenDefaultApp, self.unmerged()))
            action.setShortcut(cmds.OpenDefaultApp.SHORTCUT)

            action = menu.addAction(qtutils.open_file_icon(),
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir)
            action.setShortcut(cmds.OpenParentDir.SHORTCUT)

        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu

    def _create_unstaged_context_menu(self, menu, s):
        modified_submodule = (s.modified and
                              s.modified[0] in self.m.submodules)
        if modified_submodule:
            return self._create_modified_submodule_context_menu(menu, s)

        if self.m.stageable():
            action = menu.addAction(qtutils.icon('add.svg'),
                                    N_('Stage Selected'),
                                    cmds.run(cmds.Stage, self.unstaged()))
            action.setShortcut(cmds.Stage.SHORTCUT)

        # Do all of the selected items exist?
        unstaged_items = self.unstaged_items()
        all_exist = all([i.exists for i in unstaged_items])

        if all_exist and self.unstaged():
            menu.addAction(self.launch_editor)

        if all_exist and s.modified and self.m.stageable():
            menu.addAction(self.launch_difftool)

        if s.modified and self.m.stageable():
            if self.m.undoable():
                menu.addSeparator()
                menu.addAction(self.revert_unstaged_edits_action)
                menu.addAction(qtutils.icon('undo.svg'),
                               N_('Revert Uncommited Edits...'),
                               lambda: self._revert_uncommitted_edits(
                                            self.modified()))

        if all_exist and self.unstaged() and not utils.is_win32():
            menu.addSeparator()
            action = menu.addAction(qtutils.file_icon(),
                    cmds.OpenDefaultApp.name(),
                    cmds.run(cmds.OpenDefaultApp, self.unstaged()))
            action.setShortcut(cmds.OpenDefaultApp.SHORTCUT)

            action = menu.addAction(qtutils.open_file_icon(),
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir)
            action.setShortcut(cmds.OpenParentDir.SHORTCUT)

        if all_exist and s.untracked:
            menu.addSeparator()
            menu.addAction(qtutils.discard_icon(),
                           N_('Delete File(s)...'), self._delete_files)
            menu.addSeparator()
            menu.addAction(qtutils.icon('edit-clear.svg'),
                           N_('Add to .gitignore'),
                           cmds.run(cmds.Ignore,
                                map(lambda x: '/' + x, self.untracked())))
        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu

    def _create_modified_submodule_context_menu(self, menu, s):
        menu.addAction(qtutils.git_icon(),
                       N_('Launch git-cola'),
                       cmds.run(cmds.OpenRepo, core.abspath(s.modified[0])))

        menu.addAction(self.launch_editor)

        if self.m.stageable():
            menu.addSeparator()
            action = menu.addAction(qtutils.icon('add.svg'),
                                    N_('Stage Selected'),
                                    cmds.run(cmds.Stage, self.unstaged()))
            action.setShortcut(cmds.Stage.SHORTCUT)

        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu


    def _delete_files(self):
        files = self.untracked()
        count = len(files)
        if count == 0:
            return

        title = N_('Delete Files?')
        msg = N_('The following files will be deleted:') + '\n\n'

        fileinfo = subprocess.list2cmdline(files)
        if len(fileinfo) > 2048:
            fileinfo = fileinfo[:2048].rstrip() + '...'
        msg += fileinfo

        info_txt = N_('Delete %d file(s)?') % count
        ok_txt = N_('Delete Files')

        if qtutils.confirm(title, msg, info_txt, ok_txt,
                           default=True,
                           icon=qtutils.discard_icon()):
            cmds.do(cmds.Delete, files)

    def _revert_uncommitted_edits(self, items_to_undo):
        if items_to_undo:
            if not qtutils.confirm(
                    N_('Revert Uncommitted Changes?'),
                    N_('This operation drops uncommitted changes.\n'
                       'These changes cannot be recovered.'),
                    N_('Revert the uncommitted changes?'),
                    N_('Revert Uncommitted Changes'),
                    default=True,
                    icon=qtutils.icon('undo.svg')):
                return
            cmds.do(cmds.Checkout, [self.m.head, '--'] + items_to_undo)
        else:
            msg = N_('No files selected for checkout from HEAD.')
            Interaction.log(msg)

    def single_selection(self):
        """Scan across staged, modified, etc. and return a single item."""
        st = None
        um = None
        m = None
        ut = None

        s = self.selection()
        if s.staged:
            st = s.staged[0]
        elif s.modified:
            m = s.modified[0]
        elif s.unmerged:
            um = s.unmerged[0]
        elif s.untracked:
            ut = s.untracked[0]

        return selection.State(st, um, m, ut)

    def selected_indexes(self):
        """Returns a list of (category, row) representing the tree selection."""
        selected = self.selectedIndexes()
        result = []
        for idx in selected:
            if idx.parent().isValid():
                parent_idx = idx.parent()
                entry = (parent_idx.row(), idx.row())
            else:
                entry = (self.idx_header, idx.row())
            result.append(entry)
        return result

    def selection(self):
        """Return the current selection in the repo status tree."""
        return selection.State(self.staged(), self.unmerged(),
                               self.modified(), self.untracked())

    def contents(self):
        return selection.State(self.m.staged, self.m.unmerged,
                               self.m.modified, self.m.untracked)

    def all_files(self):
        c = self.contents()
        return c.staged + c.unmerged + c.modified + c.untracked

    def selected_group(self):
        """A list of selected files in various states of being"""
        return selection.pick(self.selection())

    def selected_idx(self):
        c = self.contents()
        s = self.single_selection()
        offset = 0
        for content, selection in zip(c, s):
            if len(content) == 0:
                continue
            if selection is not None:
                return offset + content.index(selection)
            offset += len(content)
        return None

    def select_by_index(self, idx):
        c = self.contents()
        to_try = [
            (c.staged, self.idx_staged),
            (c.unmerged, self.idx_unmerged),
            (c.modified, self.idx_modified),
            (c.untracked, self.idx_untracked),
        ]
        for content, toplevel_idx in to_try:
            if len(content) == 0:
                continue
            if idx < len(content):
                parent = self.topLevelItem(toplevel_idx)
                item = parent.child(idx)
                self.select_item(item)
                return
            idx -= len(content)

    def select_item(self, item):
        self.scrollToItem(item)
        self.setCurrentItem(item)
        self.setItemSelected(item, True)

    def staged(self):
        return self._subtree_selection(self.idx_staged, self.m.staged)

    def unstaged(self):
        return self.unmerged() + self.modified() + self.untracked()

    def modified(self):
        return self._subtree_selection(self.idx_modified, self.m.modified)

    def unmerged(self):
        return self._subtree_selection(self.idx_unmerged, self.m.unmerged)

    def untracked(self):
        return self._subtree_selection(self.idx_untracked, self.m.untracked)

    def staged_items(self):
        return self._subtree_selection_items(self.idx_staged)

    def unstaged_items(self):
        return (self.unmerged_items() + self.modified_items() +
                self.untracked_items())

    def modified_items(self):
        return self._subtree_selection_items(self.idx_modified)

    def unmerged_items(self):
        return self._subtree_selection_items(self.idx_unmerged)

    def untracked_items(self):
        return self._subtree_selection_items(self.idx_untracked)

    def _subtree_selection(self, idx, items):
        item = self.topLevelItem(idx)
        return qtutils.tree_selection(item, items)

    def _subtree_selection_items(self, idx):
        item = self.topLevelItem(idx)
        return qtutils.tree_selection_items(item)

    def double_clicked(self, item, idx):
        """Called when an item is double-clicked in the repo status tree."""
        self._process_selection()

    def _process_selection(self):
        s = self.selection()
        if s.staged:
            cmds.do(cmds.Unstage, s.staged)

        unstaged = []
        if s.unmerged:
            unstaged.extend(s.unmerged)
        if s.modified:
            unstaged.extend(s.modified)
        if s.untracked:
            unstaged.extend(s.untracked)
        if unstaged:
            cmds.do(cmds.Stage, unstaged)

    def _open_using_default_app(self):
        cmds.do(cmds.OpenDefaultApp, self.selected_group())

    def _open_parent_dir(self):
        cmds.do(cmds.OpenParentDir, self.selected_group())

    def show_selection(self):
        """Show the selected item."""
        # Sync the selection model
        selected = self.selection()
        selection.selection_model().set_selection(selected)
        self.update_actions(selected=selected)

        selected_indexes = self.selected_indexes()
        if not selected_indexes:
            if self.m.amending():
                cmds.do(cmds.SetDiffText, '')
            else:
                cmds.do(cmds.ResetMode)
            return
        category, idx = selected_indexes[0]
        # A header item e.g. 'Staged', 'Modified', etc.
        if category == self.idx_header:
            cls = {
                self.idx_staged: cmds.DiffStagedSummary,
                self.idx_modified: cmds.Diffstat,
                # TODO implement UnmergedSummary
                #self.idx_unmerged: cmds.UnmergedSummary,
                self.idx_untracked: cmds.UntrackedSummary,
            }.get(idx, cmds.Diffstat)
            cmds.do(cls)
        # A staged file
        elif category == self.idx_staged:
            cmds.do(cmds.DiffStaged, self.staged())

        # A modified file
        elif category == self.idx_modified:
            cmds.do(cmds.Diff, self.modified())

        elif category == self.idx_unmerged:
            cmds.do(cmds.Diff, self.unmerged())

        elif category == self.idx_untracked:
            cmds.do(cmds.ShowUntracked, self.unstaged())

    def move_up(self):
        idx = self.selected_idx()
        all_files = self.all_files()
        if idx is None:
            selected_indexes = self.selected_indexes()
            if selected_indexes:
                category, toplevel_idx = selected_indexes[0]
                if category == self.idx_header:
                    item = self.itemAbove(self.topLevelItem(toplevel_idx))
                    if item is not None:
                        self.select_item(item)
                        return
            if all_files:
                self.select_by_index(len(all_files) - 1)
            return
        if idx - 1 >= 0:
            self.select_by_index(idx - 1)
        else:
            self.select_by_index(len(all_files) - 1)

    def move_down(self):
        idx = self.selected_idx()
        all_files = self.all_files()
        if idx is None:
            selected_indexes = self.selected_indexes()
            if selected_indexes:
                category, toplevel_idx = selected_indexes[0]
                if category == self.idx_header:
                    item = self.itemBelow(self.topLevelItem(toplevel_idx))
                    if item is not None:
                        self.select_item(item)
                        return
            if all_files:
                self.select_by_index(0)
            return
        if idx + 1 < len(all_files):
            self.select_by_index(idx + 1)
        else:
            self.select_by_index(0)

    def copy_path(self):
        """Copy a selected path to the clipboard"""
        filename = selection.selection_model().filename()
        if filename is not None:
            curdir = os.getcwdu()
            qtutils.set_clipboard(os.path.join(curdir, filename))

########NEW FILE########
__FILENAME__ = text
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, SIGNAL

from cola.models.prefs import tabwidth
from cola.qtutils import diff_font
from cola.compat import ustr


class MonoTextEdit(QtGui.QTextEdit):

    def __init__(self, parent):
        QtGui.QTextEdit.__init__(self, parent)
        self._tabwidth = 8
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setFont(diff_font())
        self.set_tabwidth(tabwidth())
        self.setCursorWidth(2)

    def tabwidth(self):
        return self._tabwidth

    def set_tabwidth(self, width):
        self._tabwidth = width
        font = self.font()
        fm = QtGui.QFontMetrics(font)
        pixels = fm.width('M' * width)
        self.setTabStopWidth(pixels)

    def set_textwidth(self, width):
        font = self.font()
        fm = QtGui.QFontMetrics(font)
        pixels = fm.width('M' * (width + 1)) + 1
        self.setLineWrapColumnOrWidth(pixels)

    def set_linebreak(self, brk):
        if brk:
            wrapmode = QtGui.QTextEdit.FixedPixelWidth
        else:
            wrapmode = QtGui.QTextEdit.NoWrap
        self.setLineWrapMode(wrapmode)

    def selected_line(self):
        cursor = self.textCursor()
        offset = cursor.position()
        contents = ustr(self.toPlainText())
        while (offset >= 1
                and contents[offset-1]
                and contents[offset-1] != '\n'):
            offset -= 1
        data = contents[offset:]
        if '\n' in data:
            line, rest = data.split('\n', 1)
        else:
            line = data
        return line

    def mousePressEvent(self, event):
        # Move the text cursor so that the right-click events operate
        # on the current position, not the last left-clicked position.
        if event.button() == Qt.RightButton:
            if not self.textCursor().hasSelection():
                self.setTextCursor(self.cursorForPosition(event.pos()))
        QtGui.QTextEdit.mousePressEvent(self, event)


class MonoTextView(MonoTextEdit):

    def __init__(self, parent):
        MonoTextEdit.__init__(self, parent)
        self.setAcceptDrops(False)
        self.setTabChangesFocus(True)
        self.setUndoRedoEnabled(False)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard |
                                     Qt.TextSelectableByMouse)


class HintedTextWidgetEventFilter(QtCore.QObject):

    def __init__(self, parent):
        QtCore.QObject.__init__(self, parent)
        self.widget = parent

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.FocusIn:
            self.widget.emit_position()
            if self.widget.is_hint():
                self.widget.enable_hint(False)

        elif event.type() == QtCore.QEvent.FocusOut:
            if not bool(self.widget.value()):
                self.widget.enable_hint(True)

        return False


class HintedTextWidgetMixin(object):

    def __init__(self, hint):
        self._hint = hint
        self._event_filter = HintedTextWidgetEventFilter(self)
        self.installEventFilter(self._event_filter)

        # Palette for normal text
        self.default_palette = QtGui.QPalette(self.palette())

        # Palette used for the placeholder text
        self.hint_palette = pal = QtGui.QPalette(self.palette())
        color = self.hint_palette.text().color()
        color.setAlpha(128)
        pal.setColor(QtGui.QPalette.Active, QtGui.QPalette.Text, color)
        pal.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Text, color)

    def emit_position(self):
        pass

    def reset_cursor(self):
        pass

    def set_hint(self, hint):
        is_hint = self.is_hint()
        self._hint = hint
        if is_hint:
            self.enable_hint(True)

    def hint(self):
        return self._hint

    def is_hint(self):
        return self.strip() == self._hint

    def value(self):
        text = self.strip()
        if text == self._hint:
            return ''
        else:
            return text

    def strip(self):
        return self.as_unicode().strip()

    def enable_hint(self, hint):
        blocksignals = self.blockSignals(True)
        if hint:
            self.set_value(self.hint())
        else:
            self.clear()
        self.reset_cursor()
        self.blockSignals(blocksignals)
        self.enable_hint_palette(hint)

    def enable_hint_palette(self, hint):
        if hint:
            self.setPalette(self.hint_palette)
        else:
            self.setPalette(self.default_palette)

    def refresh_palette(self):
        self.enable_hint_palette(self.is_hint())


class HintedTextEditMixin(HintedTextWidgetMixin):

    def __init__(self, hint):
        HintedTextWidgetMixin.__init__(self, hint)
        self.connect(self, SIGNAL('cursorPositionChanged()'),
                     self.emit_position)

    def as_unicode(self):
        return ustr(self.toPlainText())

    def set_value(self, value):
        self.setPlainText(value)
        self.refresh_palette()

    def emit_position(self):
        cursor = self.textCursor()
        position = cursor.position()
        txt = self.as_unicode()
        before = txt[:position]
        row = before.count('\n')
        line = before.split('\n')[row]
        col = cursor.columnNumber()
        if hasattr(self, 'tabwidth'):
            col += line[:col].count('\t') * (self.tabwidth() - 1)
        self.emit(SIGNAL('cursorPosition(int,int)'), row+1, col)


class HintedTextEdit(MonoTextEdit, HintedTextEditMixin):

    def __init__(self, hint, parent=None):
        MonoTextEdit.__init__(self, parent)
        HintedTextEditMixin.__init__(self, hint)


# The read-only variant.
class HintedTextView(MonoTextView, HintedTextEditMixin):

    def __init__(self, hint, parent=None):
        MonoTextView.__init__(self, parent)
        HintedTextEditMixin.__init__(self, hint)


class HintedLineEdit(QtGui.QLineEdit, HintedTextWidgetMixin):

    def __init__(self, hint, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        HintedTextWidgetMixin.__init__(self, hint)

        self.setFont(diff_font())
        self.connect(self,
                     SIGNAL('cursorPositionChanged(int,int)'),
                     lambda x, y: self.emit_position())

    def emit_position(self):
        cols = self.cursorPosition()
        self.emit(SIGNAL('cursorPosition(int,int)'), 1, cols)

    def set_value(self, value):
        self.setText(value)
        self.refresh_palette()

    def as_unicode(self):
        return ustr(self.text())

    def reset_cursor(self):
        self.setCursorPosition(0)

########NEW FILE########
__FILENAME__ = _version
# The current git-cola version
VERSION = '2.0.3'

########NEW FILE########
__FILENAME__ = build_mo
"""build_mo command for setup.py"""

from distutils import log
from distutils.command.build import build
from distutils.core import Command
from distutils.dep_util import newer
from distutils.spawn import find_executable
import os
import re


class build_mo(Command):
    """Subcommand of build command: build_mo"""

    description = 'compile po files to mo files'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('build-dir=', 'd', 'Directory to build locale files'),
                    ('output-base=', 'o', 'mo-files base name'),
                    ('source-dir=', None, 'Directory with sources po files'),
                    ('force', 'f', 'Force creation of mo files'),
                    ('lang=', None, 'Comma-separated list of languages '
                                    'to process')]

    boolean_options = ['force']

    def initialize_options(self):
        self.build_dir = None
        self.output_base = None
        self.source_dir = None
        self.force = None
        self.lang = None

    def finalize_options(self):
        self.set_undefined_options('build', ('force', 'force'))
        self.prj_name = self.distribution.get_name()
        if self.build_dir is None:
            self.build_dir = os.path.join('share', 'locale')
        if not self.output_base:
            self.output_base = self.prj_name or 'messages'
        if self.source_dir is None:
            self.source_dir = 'po'
        if self.lang is None:
            if self.prj_name:
                re_po = re.compile(r'^(?:%s-)?([a-zA-Z_]+)\.po$' % self.prj_name)
            else:
                re_po = re.compile(r'^([a-zA-Z_]+)\.po$')
            self.lang = []
            for i in os.listdir(self.source_dir):
                mo = re_po.match(i)
                if mo:
                    self.lang.append(mo.group(1))
        else:
            self.lang = [i.strip() for i in self.lang.split(',') if i.strip()]

    def run(self):
        """Run msgfmt for each language"""
        if not self.lang:
            return

        if find_executable('msgfmt') is None:
            log.warn("GNU gettext msgfmt utility not found!")
            log.warn("Skip compiling po files.")
            return

        if 'en' in self.lang:
            if find_executable('msginit') is None:
                log.warn("GNU gettext msginit utility not found!")
                log.warn("Skip creating English PO file.")
            else:
                log.info('Creating English PO file...')
                pot = (self.prj_name or 'messages') + '.pot'
                if self.prj_name:
                    en_po = '%s-en.po' % self.prj_name
                else:
                    en_po = 'en.po'
                self.spawn(['msginit',
                    '--no-translator',
                    '-l', 'en',
                    '-i', os.path.join(self.source_dir, pot),
                    '-o', os.path.join(self.source_dir, en_po),
                    ])

        basename = self.output_base
        if not basename.endswith('.mo'):
            basename += '.mo'

        po_prefix = ''
        if self.prj_name:
            po_prefix = self.prj_name + '-'
        for lang in self.lang:
            po = os.path.join(self.source_dir, lang + '.po')
            if not os.path.isfile(po):
                po = os.path.join(self.source_dir, po_prefix + lang + '.po')
            dir_ = os.path.join(self.build_dir, lang, 'LC_MESSAGES')
            self.mkpath(dir_)
            mo = os.path.join(dir_, basename)
            if self.force or newer(po, mo):
                log.info('Compile: %s -> %s' % (po, mo))
                self.spawn(['msgfmt', '-o', mo, po])


build.sub_commands.insert(0, ('build_mo', None))

########NEW FILE########
__FILENAME__ = build_pot
"""build_pot command for setup.py"""

import os
import glob
from distutils import log
from distutils.core import Command
from distutils.errors import DistutilsOptionError


class build_pot(Command):
    """Distutils command build_pot"""

    description = 'extract strings from python sources for translation'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('build-dir=', 'd', 'Directory to put POT file'),
                    ('output=', 'o', 'POT filename'),
                    ('lang=', None, 'Comma-separated list of languages '
                                    'to update po-files'),
                    ('no-lang', 'N', "Don't update po-files"),
                    ('english', 'E', 'Regenerate English PO file'),
                   ]
    boolean_options = ['no-lang', 'english']

    def initialize_options(self):
        self.build_dir = None
        self.output = None
        self.lang = None
        self.no_lang = False
        self.english = False

    def finalize_options(self):
        if self.build_dir is None:
            self.build_dir = 'po'
        if not self.output:
            self.output = (self.distribution.get_name() or 'messages')+'.pot'
        if self.lang is not None:
            self.lang = [i.strip() for i in self.lang.split(',') if i.strip()]
        if self.lang and self.no_lang:
            raise DistutilsOptionError("You can't use options "
                "--lang=XXX and --no-lang in the same time.")

    def _force_LF(self, src, dst=None):
        f = open(src, 'rU')
        try:
            content = f.read()
        finally:
            f.close()
        if dst is None:
            dst = src
        f = open(dst, 'wb')
        try:
            f.write(content)
        finally:
            f.close()

    def run(self):
        """Run xgettext for project sources"""
        # project name based on `name` argument in setup() call
        prj_name = self.distribution.get_name()
        # output file
        if self.build_dir != '.':
            fullname = os.path.join(self.build_dir, self.output)
        else:
            fullname = self.output
        log.info('Generate POT file: ' + fullname)
        if not os.path.isdir(self.build_dir):
            log.info('Make directory: ' + self.build_dir)
            os.makedirs(self.build_dir)
        self.spawn(['xgettext',
                    '--keyword=N_',
                    '-p', self.build_dir,
                    '-o', self.output] +
                    glob.glob('cola/*.py') +
                    glob.glob('cola/*/*.py'))
        self._force_LF(fullname)
        # regenerate english PO
        if self.english:
            log.info('Regenerating English PO file...')
            if prj_name:
                en_po = prj_name + '-' + 'en.po'
            else:
                en_po = 'en.po'
            self.spawn(['msginit',
                '--no-translator',
                '-l', 'en',
                '-i', os.path.join(self.build_dir, self.output),
                '-o', os.path.join(self.build_dir, en_po),
                ])
        # search and update all po-files
        if self.no_lang:
            return
        for po in glob.glob(os.path.join(self.build_dir,'*.po')):
            if self.lang is not None:
                po_lang = os.path.splitext(os.path.basename(po))[0]
                if prj_name and po_lang.startswith(prj_name+'-'):
                    po_lang = po_lang[5:]
                if po_lang not in self.lang:
                    continue
            new_po = po + ".new"
            cmd = "msgmerge %s %s -o %s" % (po, fullname, new_po)
            self.spawn(cmd.split())
            # force LF line-endings
            log.info("%s --> %s" % (new_po, po))
            self._force_LF(new_po, po)
            os.unlink(new_po)

########NEW FILE########
__FILENAME__ = sphinxtogithub
#! /usr/bin/env python
from __future__ import print_function

from optparse import OptionParser
import warnings
import os
import sys
import shutil


class DirHelper(object):

    def __init__(self, is_dir, list_dir, walk, rmtree):

        self.is_dir = is_dir
        self.list_dir = list_dir
        self.walk = walk
        self.rmtree = rmtree

class FileSystemHelper(object):

    def __init__(self, open_, path_join, move, exists):

        self.open_ = open_
        self.path_join = path_join
        self.move = move
        self.exists = exists

class Replacer(object):
    "Encapsulates a simple text replace"

    def __init__(self, from_, to):

        self.from_ = from_
        self.to = to

    def process(self, text):

        return text.replace( self.from_, self.to )

class FileHandler(object):
    "Applies a series of replacements the contents of a file inplace"

    def __init__(self, name, replacers, opener):

        self.name = name
        self.replacers = replacers
        self.opener = opener

    def process(self):

        text = self.opener(self.name).read()

        for replacer in self.replacers:
            text = replacer.process( text )

        self.opener(self.name, "w").write(text)

class Remover(object):

    def __init__(self, exists, remove):
        self.exists = exists
        self.remove = remove

    def __call__(self, name):

        if self.exists(name):
            self.remove(name)

class ForceRename(object):

    def __init__(self, renamer, remove):

        self.renamer = renamer
        self.remove = remove

    def __call__(self, from_, to):

        self.remove(to)
        self.renamer(from_, to)

class VerboseRename(object):

    def __init__(self, renamer, stream):

        self.renamer = renamer
        self.stream = stream

    def __call__(self, from_, to):

        self.stream.write(
                "Renaming directory '%s' -> '%s'\n"
                    % (os.path.basename(from_), os.path.basename(to))
                )

        self.renamer(from_, to)


class DirectoryHandler(object):
    "Encapsulates renaming a directory by removing its first character"

    def __init__(self, name, root, renamer):

        self.name = name
        self.new_name = name[1:]
        self.root = root + os.sep
        self.renamer = renamer

    def path(self):
        
        return os.path.join(self.root, self.name)

    def relative_path(self, directory, filename):

        path = directory.replace(self.root, "", 1)
        return os.path.join(path, filename)

    def new_relative_path(self, directory, filename):

        path = self.relative_path(directory, filename)
        return path.replace(self.name, self.new_name, 1)

    def process(self):

        from_ = os.path.join(self.root, self.name)
        to = os.path.join(self.root, self.new_name)
        self.renamer(from_, to)


class HandlerFactory(object):

    def create_file_handler(self, name, replacers, opener):

        return FileHandler(name, replacers, opener)

    def create_dir_handler(self, name, root, renamer):

        return DirectoryHandler(name, root, renamer)


class OperationsFactory(object):

    def create_force_rename(self, renamer, remover):

        return ForceRename(renamer, remover)

    def create_verbose_rename(self, renamer, stream):

        return VerboseRename(renamer, stream)

    def create_replacer(self, from_, to):

        return Replacer(from_, to)

    def create_remover(self, exists, remove):

        return Remover(exists, remove)


class Layout(object):
    """
    Applies a set of operations which result in the layout
    of a directory changing
    """

    def __init__(self, directory_handlers, file_handlers):

        self.directory_handlers = directory_handlers
        self.file_handlers = file_handlers

    def process(self):

        for handler in self.file_handlers:
            handler.process()

        for handler in self.directory_handlers:
            handler.process()


class NullLayout(object):
    """
    Layout class that does nothing when asked to process
    """
    def process(self):
        pass

class LayoutFactory(object):
    "Creates a layout object"

    def __init__(self, operations_factory, handler_factory, file_helper, dir_helper, verbose, stream, force):

        self.operations_factory = operations_factory
        self.handler_factory = handler_factory

        self.file_helper = file_helper
        self.dir_helper = dir_helper

        self.verbose = verbose
        self.output_stream = stream
        self.force = force

    def create_layout(self, path):
        path = str(path)
        contents = self.dir_helper.list_dir(path)

        renamer = self.file_helper.move

        if self.force:
            remove = self.operations_factory.create_remover(self.file_helper.exists, self.dir_helper.rmtree)
            renamer = self.operations_factory.create_force_rename(renamer, remove) 

        if self.verbose:
            renamer = self.operations_factory.create_verbose_rename(renamer, self.output_stream) 

        # Build list of directories to process
        directories = [d for d in contents if self.is_underscore_dir(path, d)]
        underscore_directories = [
                self.handler_factory.create_dir_handler(d, path, renamer)
                    for d in directories
                ]

        if not underscore_directories:
            if self.verbose:
                self.output_stream.write(
                        "No top level directories starting with an underscore "
                        "were found in '%s'\n" % path
                        )
            return NullLayout()

        # Build list of files that are in those directories
        replacers = []
        for handler in underscore_directories:
            for directory, dirs, files in self.dir_helper.walk(handler.path()):
                for f in files:
                    replacers.append(
                            self.operations_factory.create_replacer(
                                handler.relative_path(directory, f),
                                handler.new_relative_path(directory, f)
                                )
                            )

        # Build list of handlers to process all files
        filelist = []
        for root, dirs, files in self.dir_helper.walk(path):
            for f in files:
                if f.endswith(".html"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                replacers,
                                self.file_helper.open_)
                            )
                if f.endswith(".js"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                [self.operations_factory.create_replacer("'_sources/'", "'sources/'")],
                                self.file_helper.open_
                                )
                            )

        return Layout(underscore_directories, filelist)

    def is_underscore_dir(self, path, directory):

        return (self.dir_helper.is_dir(self.file_helper.path_join(path, directory))
            and directory.startswith("_"))



def sphinx_extension(app, exception):
    "Wrapped up as a Sphinx Extension"

    if not app.builder.name in ("html", "dirhtml"):
        return

    if not app.config.sphinx_to_github:
        if app.config.sphinx_to_github_verbose:
            print("Sphinx-to-github: Disabled, doing nothing.")
        return

    if exception:
        if app.config.sphinx_to_github_verbose:
            print("Sphinx-to-github: Exception raised in main build, doing nothing.")
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            app.config.sphinx_to_github_verbose,
            sys.stdout,
            force=True
            )

    layout = layout_factory.create_layout(app.outdir)
    layout.process()


def setup(app):
    "Setup function for Sphinx Extension"

    if (not hasattr(app, 'add_config_value') or
        not hasattr(app, 'connect')):
        warnings.warn('Could not call add_config_value() in sphinxtogithub')
        return
    app.add_config_value("sphinx_to_github", True, '')
    app.add_config_value("sphinx_to_github_verbose", True, '')
    app.connect("build-finished", sphinx_extension)


def main(args):

    usage = "usage: %prog [options] <html directory>"
    parser = OptionParser(usage=usage)
    parser.add_option("-v","--verbose", action="store_true",
            dest="verbose", default=False, help="Provides verbose output")
    opts, args = parser.parse_args(args)

    try:
        path = args[0]
    except IndexError:
        sys.stderr.write(
                "Error - Expecting path to html directory:"
                "sphinx-to-github <path>\n"
                )
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            opts.verbose,
            sys.stdout,
            force=False
            )

    layout = layout_factory.create_layout(path)
    layout.process()
    


if __name__ == "__main__":
    main(sys.argv[1:])




########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# git-cola documentation build configuration file, created by
# sphinx-quickstart on Sat Apr 18 22:49:53 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# Add the cola source directory to sys.path
docdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
srcdir = os.path.dirname(os.path.dirname(docdir))
extrasdir = os.path.join(srcdir, 'extras')

sys.path.insert(1, extrasdir)

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.intersphinx',
              'sphinx.ext.todo',
              'sphinx.ext.coverage',
              'sphinxtogithub']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'git-cola'
copyright = '2007-2014, David Aguilar and contributors'
authors = 'David Aguilar and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
versionfile = os.path.join(srcdir, 'cola', '_version.py')
scope = {}
with open(versionfile) as f:
    exec(f.read(), scope)
# The short X.Y version.
version = scope['VERSION']
# The full version, including alpha/beta/rc tags.
release = version

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'haiku'

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'git-coladoc'

# -- Options for manual pages output ---
man_pages = [
  ('git-cola', 'git-cola', 'The highly caffeinated Git GUI',
   authors, '1'),
  ('git-dag', 'git-dag', 'The sleek and powerful Git history browser',
   authors, '1'),
]


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'git-cola.tex', u'git-cola Documentation',
   u'David Aguilar and contributors', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = browse_model_test
"""Covers interfaces used by the classic view."""
from __future__ import unicode_literals

import os

import helper
from cola import gitcmds
from cola.models.main import MainModel


class ClassicModelTestCase(helper.GitRepositoryTestCase):
    """Tests interfaces used by the classic view."""

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self, commit=False)
        self.model = MainModel(cwd=os.getcwd())

    def test_everything(self):
        """Test the MainModel.everything() method."""
        self.shell('touch other-file')
        everything = self.model.everything()

        self.assertTrue('A' in everything)
        self.assertTrue('B' in everything)
        self.assertTrue('other-file' in everything)

    def test_stage_paths_untracked(self):
        """Test stage_paths() with an untracked file."""
        self.shell("""
            mkdir -p foo/bar &&
            touch foo/bar/baz
        """)
        self.model.stage_paths(['foo'])

        self.assertTrue('foo/bar/baz' in self.model.staged)
        self.assertTrue('foo/bar/baz' not in self.model.modified)
        self.assertTrue('foo/bar/baz' not in self.model.untracked)

    def test_unstage_paths(self):
        """Test a simple usage of unstage_paths()."""
        self.shell("""
            git commit -m'initial commit' > /dev/null
            echo change > A &&
            git add A
        """)
        gitcmds.unstage_paths(['A'])
        self.model.update_status()

        self.assertTrue('A' not in self.model.staged)
        self.assertTrue('A' in self.model.modified)

    def test_unstage_paths_init(self):
        """Test unstage_paths() on the root commit."""
        gitcmds.unstage_paths(['A'])
        self.model.update_status()

        self.assertTrue('A' not in self.model.staged)
        self.assertTrue('A' in self.model.untracked)

    def test_unstage_paths_subdir(self):
        """Test unstage_paths() in a subdirectory."""
        self.shell("git commit -m'initial commit' > /dev/null")
        self.shell("""
            mkdir -p foo/bar &&
            touch foo/bar/baz &&
            git add foo/bar/baz
        """)
        gitcmds.unstage_paths(['foo'])
        self.model.update_status()

        self.assertTrue('foo/bar/baz' in self.model.untracked)
        self.assertTrue('foo/bar/baz' not in self.model.staged)

########NEW FILE########
__FILENAME__ = core_test
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
import unittest

import helper

from cola import core


class CoreColaUnicodeTestCase(unittest.TestCase):
    """Tests the cola.core module's unicode handling
    """

    def test_core_decode(self):
        """Test the core.decode function
        """
        filename = helper.fixture('unicode.txt')
        expect = core.decode(core.encode('unicøde'))
        actual = core.read(filename).strip()
        self.assertEqual(expect, actual)

    def test_core_encode(self):
        """Test the core.encode function
        """
        filename = helper.fixture('unicode.txt')
        expect = core.encode('unicøde')
        actual = core.encode(core.read(filename).strip())
        self.assertEqual(expect, actual)

    def test_decode_None(self):
        """Ensure that decode(None) returns None"""
        expect = None
        actual = core.decode(None)
        self.assertEqual(expect, actual)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = diffparse_test
from __future__ import unicode_literals
import os
import unittest

from cola import core
from cola import gitcmds
from cola import diffparse
from cola.diffparse import DiffParser

import helper


class DiffParseModel(object):
    def __init__(self):
        self.last_worktree_diff = None
        self.last_diff = None
        self.head = 'HEAD'
        self.amend = False

    def amending(self):
        return self.amend

    def apply_diff_to_worktree(self, path):
        if os.path.exists(path):
            self.last_worktree_diff = core.read(path)

    def apply_diff(self, path):
        if os.path.exists(path):
            self.last_diff = core.read(path)


class DiffSource(object):
    def __init__(self, fwd, reverse):
        self.fwd = core.read(fwd)
        self.reverse = core.read(reverse)

    def get(self, head, amending, filename, cached, reverse):
        if reverse:
            return self.parse(self.reverse)
        else:
            return self.parse(self.fwd)

    def parse(self, diffoutput):
        return gitcmds.extract_diff_header(
                status=0, deleted=False,
                with_diff_header=True, suppress_header=False,
                diffoutput=diffoutput)


class DiffParseTestCase(unittest.TestCase):
    def setUp(self):
        self.model = DiffParseModel()

    def test_diff(self):
        fwd = helper.fixture('diff.txt')
        reverse = helper.fixture('diff-reverse.txt')
        source = DiffSource(fwd, reverse)
        model = DiffParseModel()
        parser = DiffParser(model, filename='',
                            cached=False, reverse=False,
                            diff_source=source)

        self.assertEqual(parser.offsets(),
                [916, 1798, 2550])
        self.assertEqual(parser.spans(),
                [[0, 916], [916, 1798], [1798, 2550]])

        diffs = parser.diffs()
        self.assertEqual(len(diffs), 3)

        self.assertEqual(len(diffs[0]), 23)
        self.assertEqual(diffs[0][0],
                '@@ -6,10 +6,21 @@ from cola import gitcmds')
        self.assertEqual(diffs[0][1],
                ' from cola import gitcfg')
        self.assertEqual(diffs[0][2],
                ' ')
        self.assertEqual(diffs[0][3],
                ' ')
        self.assertEqual(diffs[0][4],
                '+class DiffSource(object):')

        self.assertEqual(len(diffs[1]), 18)
        self.assertEqual(diffs[1][0],
                '@@ -29,13 +40,11 @@ class DiffParser(object):')
        self.assertEqual(diffs[1][1],
                '         self.diff_sel = []')
        self.assertEqual(diffs[1][2],
                '         self.selected = []')
        self.assertEqual(diffs[1][3],
                '         self.filename = filename')
        self.assertEqual(diffs[1][4],
                '+        self.diff_source = diff_source or DiffSource()')

        self.assertEqual(len(diffs[2]), 18)
        self.assertEqual(diffs[2][0],
                '@@ -43,11 +52,10 @@ class DiffParser(object):')

    def test_diff_at_start(self):
        fwd = helper.fixture('diff-start.txt')
        reverse = helper.fixture('diff-start-reverse.txt')

        source = DiffSource(fwd, reverse)
        model = DiffParseModel()
        parser = DiffParser(model, filename='',
                            cached=False, reverse=False,
                            diff_source=source)

        self.assertEqual(parser.diffs()[0][0], '@@ -1 +1,4 @@')
        self.assertEqual(parser.offsets(), [30])
        self.assertEqual(parser.spans(), [[0, 30]])
        self.assertEqual(parser.diffs_for_range(0, 10),
                         (['@@ -1 +1,4 @@\n bar\n+a\n+b\n+c\n\n'],
                          [0]))
        self.assertEqual(parser.ranges()[0].begin, [1, 1])
        self.assertEqual(parser.ranges()[0].end, [1, 4])
        self.assertEqual(parser.ranges()[0].make(), '@@ -1 +1,4 @@')

    def test_diff_at_end(self):
        fwd = helper.fixture('diff-end.txt')
        reverse = helper.fixture('diff-end-reverse.txt')

        source = DiffSource(fwd, reverse)
        model = DiffParseModel()
        parser = DiffParser(model, filename='',
                            cached=False, reverse=False,
                            diff_source=source)

        self.assertEqual(parser.diffs()[0][0], '@@ -1,39 +1 @@')
        self.assertEqual(parser.offsets(), [1114])
        self.assertEqual(parser.spans(), [[0, 1114]])
        self.assertEqual(parser.ranges()[0].begin, [1, 39])
        self.assertEqual(parser.ranges()[0].end, [1, 1])
        self.assertEqual(parser.ranges()[0].make(), '@@ -1,39 +1 @@')

    def test_diff_that_empties_file(self):
        fwd = helper.fixture('diff-empty.txt')
        reverse = helper.fixture('diff-empty-reverse.txt')

        source = DiffSource(fwd, reverse)
        model = DiffParseModel()
        parser = DiffParser(model, filename='',
                            cached=False, reverse=False,
                            diff_source=source)

        self.assertEqual(parser.diffs()[0][0], '@@ -1,2 +0,0 @@')
        self.assertEqual(parser.offsets(), [33])
        self.assertEqual(parser.spans(), [[0, 33]])
        self.assertEqual(parser.diffs_for_range(0, 1),
                         (['@@ -1,2 +0,0 @@\n-first\n-second\n\n'],
                          [0]))

        self.assertEqual(parser.ranges()[0].begin, [1, 2])
        self.assertEqual(parser.ranges()[0].end, [0, 0])
        self.assertEqual(parser.ranges()[0].make(), '@@ -1,2 +0,0 @@')


class RangeTestCase(unittest.TestCase):

    def test_empty_becomes_non_empty(self):
        r = diffparse.Range('1,2', '0,0')
        self.assertEqual(r.begin, [1,2])
        self.assertEqual(r.end, [0, 0])
        self.assertEqual(r.make(), '@@ -1,2 +0,0 @@')

        r.set_end_count(1)
        self.assertEqual(r.end, [1, 1])
        self.assertEqual(r.make(), '@@ -1,2 +1 @@')

    def test_single_line(self):
        r = diffparse.Range('1', '1,2')
        self.assertEqual(r.begin, [1, 1])
        self.assertEqual(r.end, [1, 2])
        self.assertEqual(r.make(), '@@ -1 +1,2 @@')
        r.set_end_count(1)
        self.assertEqual(r.make(), '@@ -1 +1 @@')


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = gitcfg_test
from __future__ import unicode_literals

import unittest

import helper
from cola import gitcfg


class GitConfigTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""
    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.config = gitcfg.instance()

    def test_string(self):
        """Test string values in get()."""
        self.shell('git config test.value test')
        self.assertEqual(self.config.get('test.value'), 'test')

    def test_int(self):
        """Test int values in get()."""
        self.shell('git config test.int 42')
        self.assertEqual(self.config.get('test.int'), 42)

    def test_true(self):
        """Test bool values in get()."""
        self.shell('git config test.bool true')
        self.assertEqual(self.config.get('test.bool'), True)

    def test_false(self):
        self.shell('git config test.bool false')
        self.assertEqual(self.config.get('test.bool'), False)

    def test_yes(self):
        self.shell('git config test.bool yes')
        self.assertEqual(self.config.get('test.bool'), True)

    def test_no(self):
        self.shell('git config test.bool false')
        self.assertEqual(self.config.get('test.bool'), False)

    def test_bool_no_value(self):
        self.shell('printf "[test]\n" >> .git/config')
        self.shell('printf "\tbool\n" >> .git/config')
        self.assertEqual(self.config.get('test.bool'), True)

    def test_empty_value(self):
        self.shell('printf "[test]\n" >> .git/config')
        self.shell('printf "\tvalue = \n" >> .git/config')
        self.assertEqual(self.config.get('test.value'), '')

    def test_default(self):
        """Test default values in get()."""
        self.assertEqual(self.config.get('does.not.exist'), None)
        self.assertEqual(self.config.get('does.not.exist', default=42), 42)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = gitcmds_test
from __future__ import unicode_literals

import os
import time
import unittest

import helper
from cola import gitcmds
from cola import gitcfg


class GitCmdsTestCase(helper.GitRepositoryTestCase):
    """Tests the cola.gitcmds module."""
    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.config = gitcfg.GitConfig()

    def test_currentbranch(self):
        """Test current_branch()."""
        self.assertEqual(gitcmds.current_branch(), 'master')

    def test_branch_list_local(self):
        """Test branch_list(remote=False)."""
        self.assertEqual(gitcmds.branch_list(remote=False), ['master'])

    def test_branch_list_remote(self):
        """Test branch_list(remote=False)."""
        self.assertEqual(gitcmds.branch_list(remote=True), [])
        self.shell("""
            git remote add origin . &&
            git fetch origin > /dev/null 2>&1
        """)
        self.assertEqual(gitcmds.branch_list(remote=True), ['origin/master'])
        self.shell('git remote rm origin')
        self.assertEqual(gitcmds.branch_list(remote=True), [])

    def test_default_remote(self):
        """Test default_remote()."""
        self.assertEqual(gitcmds.default_remote(config=self.config), None)
        self.shell('git config branch.master.remote test')
        self.config.reset()
        self.assertEqual(gitcmds.default_remote(config=self.config), 'test')

    def test_tracked_branch(self):
        """Test tracked_branch()."""
        self.assertEqual(gitcmds.tracked_branch(config=self.config), None)
        self.shell("""
            git config branch.master.remote test &&
            git config branch.master.merge refs/heads/master
        """)
        self.config.reset()
        self.assertEqual(gitcmds.tracked_branch(config=self.config),
                         'test/master')

    def test_tracked_branch_other(self):
        """Test tracked_branch('other')."""
        self.assertEqual(gitcmds.tracked_branch('other', config=self.config),
                         None)
        self.shell("""
            git config branch.other.remote test &&
            git config branch.other.merge refs/heads/other/branch
        """)
        self.config.reset()
        self.assertEqual(gitcmds.tracked_branch('other', config=self.config),
                         'test/other/branch')

    def test_untracked_files(self):
        """Test untracked_files()."""
        self.shell('touch C D E')
        self.assertEqual(gitcmds.untracked_files(), ['C', 'D', 'E'])

    def test_tag_list(self):
        """Test tag_list()."""
        self.shell('git tag a && git tag b && git tag c')
        self.assertEqual(gitcmds.tag_list(), ['c', 'b', 'a'])

    def test_merge_message_path(self):
        """Test merge_message_path()."""
        self.shell('touch .git/SQUASH_MSG')
        self.assertEqual(gitcmds.merge_message_path(),
                         os.path.abspath('.git/SQUASH_MSG'))
        self.shell('touch .git/MERGE_MSG')
        self.assertEqual(gitcmds.merge_message_path(),
                         os.path.abspath('.git/MERGE_MSG'))
        os.unlink(gitcmds.merge_message_path())
        self.assertEqual(gitcmds.merge_message_path(),
                         os.path.abspath('.git/SQUASH_MSG'))
        os.unlink(gitcmds.merge_message_path())
        self.assertEqual(gitcmds.merge_message_path(), None)

    def test_all_refs(self):
        self.shell("""
            git branch a &&
            git branch b &&
            git branch c &&
            git tag d &&
            git tag e &&
            git tag f &&
            git remote add origin . &&
            git fetch origin > /dev/null 2>&1
        """)
        refs = gitcmds.all_refs()
        self.assertEqual(refs,
                         ['a', 'b', 'c', 'master',
                          'origin/a', 'origin/b', 'origin/c', 'origin/master',
                          'd', 'e', 'f'])

    def test_all_refs_split(self):
        self.shell("""
            git branch a &&
            git branch b &&
            git branch c &&
            git tag d &&
            git tag e &&
            git tag f &&
            git remote add origin . &&
            git fetch origin > /dev/null 2>&1
        """)
        local, remote, tags = gitcmds.all_refs(split=True)
        self.assertEqual(local, ['a', 'b', 'c', 'master'])
        self.assertEqual(remote, ['origin/a', 'origin/b', 'origin/c', 'origin/master'])
        self.assertEqual(tags, ['d', 'e', 'f'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = gitops_test
#!/usr/bin/env python
"""Tests basic git operations: commit, log, config"""
from __future__ import unicode_literals

import os
import unittest

import helper
from cola.models.main import MainModel

class ColaBasicGitTestCase(helper.GitRepositoryTestCase):

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self, commit=False)

    def test_git_commit(self):
        """Test running 'git commit' via cola.git"""
        self.shell("""
            echo A > A
            echo B > B
            git add A B
            """)

        model = MainModel(cwd=os.getcwd())
        model.git.commit(m='commit test')
        log = helper.pipe('git log --pretty=oneline | wc -l')

        self.assertEqual(log.strip(), '1')

    def test_git_config(self):
        """Test cola.git.config()"""
        self.shell('git config section.key value')
        model = MainModel(cwd=os.getcwd())
        value = model.git.config('section.key', get=True)

        self.assertEqual(value, (0, 'value', ''))

        #  Test config_set
        model.config_set('section.bool', True)
        value = model.git.config('section.bool', get=True)

        self.assertEqual(value, (0, 'true', ''))
        model.config_set('section.bool', False)

        # Test config_dict
        config_dict = model.config_dict(local=True)

        self.assertEqual(config_dict['section_key'], 'value')
        self.assertEqual(config_dict['section_bool'], False)

        # Test config_dict --global
        global_dict = model.config_dict(local=False)

        self.assertEqual(type(global_dict), dict)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = git_test
#!/usr/bin/env python
"""Tests various operations using the cola.git module
"""
from __future__ import unicode_literals

import time
import signal
import unittest

from cola import git
from cola.git import STDOUT


class GitCommandTest(unittest.TestCase):
    """Runs tests using a git.Git instance"""

    def setUp(self):
        """Creates a git.Git instance for later use"""
        self.git = git.Git()

    def test_version(self):
        """Test running 'git version'"""
        version = self.git.version()[STDOUT]
        self.failUnless(version.startswith('git version'))

    def test_tag(self):
        """Test running 'git tag'"""
        tags = self.git.tag()[STDOUT].splitlines()
        self.failUnless( 'v1.0.0' in tags )

    def test_show(self):
        """Test running 'git show'"""
        sha = '1b9742bda5d26a4f250fa64657f66ed20624a084'
        contents = self.git.show(sha)[STDOUT].splitlines()
        self.failUnless(contents[0] == '/build')

    def test_stdout(self):
        """Test overflowing the stdout buffer"""
        # Write to stdout only
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)
        self.assertEqual(len(err), 0)

    def test_stderr(self):
        """Test that stderr is seen"""
        # Write to stderr and capture it
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 0)
        self.assertEqual(len(err), 1024 * 16 + 1)

    def test_stdout_and_stderr(self):
        """Test ignoring stderr when stdout+stderr are provided (v2)"""
        # Write to stdout and stderr but only capture stdout
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stdout.write(s);'
                'sys.stderr.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(len(out), 1024 * 16 + 1)
        self.assertEqual(len(err), 1024 * 16 + 1)

    def test_it_doesnt_deadlock(self):
        """Test that we don't deadlock with both stderr and stdout"""
        # 16k+1 bytes to exhaust any output buffers
        code = ('import sys;'
                's = "\\0" * (1024 * 16 + 1);'
                'sys.stderr.write(s);'
                'sys.stdout.write(s);')
        status, out, err = git.Git.execute(['python', '-c', code], _raw=True)
        self.assertEqual(status, 0)
        self.assertEqual(out, '\0' * (1024 * 16 + 1))
        self.assertEqual(err, '\0' * (1024 * 16 + 1))

    def test_it_handles_interrupted_syscalls(self):
        """Test that we handle interrupted system calls"""
        # send ourselves a signal that causes EINTR
        prev_handler = signal.signal(signal.SIGALRM, lambda x, y: 1)
        signal.alarm(1)
        time.sleep(0.1)
        status, out, err = git.Git.execute(['sleep', '1'])
        self.assertEqual(status, 0)

        signal.signal(signal.SIGALRM, prev_handler)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = gravatar_test
#!/usr/bin/env python
from __future__ import unicode_literals

import unittest
from cola import gravatar


class GravatarTestCase(unittest.TestCase):

    def test_url_for_email_(self):
        email = 'email@example.com'
        expect='http://gravatar.com/avatar/5658ffccee7f0ebfda2b226238b1eb6e?s=64&d=http%3A%2F%2Fgit-cola.github.io%2Fimages%2Fgit-64x64.jpg'
        actual = gravatar.Gravatar.url_for_email(email, 64)
        self.assertEqual(expect, actual)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = helper
from __future__ import unicode_literals

import os
import shutil
import unittest
import tempfile

from cola import core
from cola import git
from cola import gitcfg
from cola import gitcmds


def tmp_path(*paths):
    """Returns a path relative to the test/tmp directory"""
    return os.path.join(os.path.dirname(__file__), 'tmp', *paths)


def fixture(*paths):
    return os.path.join(os.path.dirname(__file__), 'fixtures', *paths)


def shell(cmd):
    return os.system(cmd)


def pipe(cmd):
    p = os.popen(cmd)
    out = core.fread(p).strip()
    p.close()
    return out


class TmpPathTestCase(unittest.TestCase):
    def setUp(self):
        self._testdir = tempfile.mkdtemp('_cola_test')
        os.chdir(self._testdir)

    def tearDown(self):
        """Remove the test directory and return to the tmp root."""
        path = self._testdir
        os.chdir(tmp_path())
        shutil.rmtree(path)

    def shell(self, cmd):
        result = shell(cmd)
        self.failIf(result != 0)

    def test_path(self, *paths):
        return os.path.join(self._testdir, *paths)


class GitRepositoryTestCase(TmpPathTestCase):
    """Tests that operate on temporary git repositories."""
    def setUp(self, commit=True):
        TmpPathTestCase.setUp(self)
        self.initialize_repo()
        if commit:
            self.commit_files()
        git.instance().set_worktree(core.getcwd())
        gitcfg.instance().reset()
        gitcmds.clear_cache()

    def initialize_repo(self):
        self.shell("""
            git init > /dev/null &&
            touch A B &&
            git add A B
        """)

    def commit_files(self):
        self.shell('git commit -m"Initial commit" > /dev/null')

########NEW FILE########
__FILENAME__ = i18n_test
# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import sip
sip.setapi('QString', 1)

import unittest

from PyQt4 import QtCore

from cola import i18n
from cola.i18n import N_
from cola.compat import unichr


class ColaI18nTestCase(unittest.TestCase):
    """Test cases for the ColaApplication class"""

    def tearDown(self):
        i18n.uninstall()

    def test_translates_noun(self):
        """Test that strings with @@noun are translated
        """
        i18n.install('ja_JP')
        expect = (unichr(0x30b3) + unichr(0x30df) +
                  unichr(0x30c3) + unichr(0x30c8))
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_verb(self):
        """Test that strings with @@verb are translated
        """
        i18n.install('de_DE')
        expect = 'Version aufnehmen'
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_english_noun(self):
        """Test that English strings with @@noun are properly handled
        """
        i18n.install('en_US.UTF-8')
        expect = 'Commit'
        actual = N_('Commit@@noun')
        self.assertEqual(expect, actual)

    def test_translates_english_verb(self):
        """Test that English strings with @@verb are properly handled
        """
        i18n.install('en_US.UTF-8')
        expect = 'Commit'
        actual = N_('Commit@@verb')
        self.assertEqual(expect, actual)

    def test_translates_random_english(self):
        """Test that random English strings are passed through as-is
        """
        i18n.install('en_US.UTF-8')
        expect = 'Random'
        actual = N_('Random')
        self.assertEqual(expect, actual)

    def test_guards_against_qstring(self):
        """Test that random QString is passed through as-is
        """
        i18n.install('en_US.UTF-8')
        expect = 'Random'
        actual = i18n.gettext(QtCore.QString('Random'))
        self.assertEqual(expect, actual)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = main_model_test
from __future__ import unicode_literals

import os
import unittest

import helper
from cola.models.main import MainModel


class MainModelTestCase(helper.GitRepositoryTestCase):
    """Tests the MainModel class."""

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self)
        self.model = MainModel(cwd=os.getcwd())

    def test_project(self):
        """Test the 'project' attribute."""
        project = os.path.basename(self.test_path())
        self.assertEqual(self.model.project, project)

    def test_local_branches(self):
        """Test the 'local_branches' attribute."""
        self.model.update_status()
        self.assertEqual(self.model.local_branches, ['master'])

    def test_remote_branches(self):
        """Test the 'remote_branches' attribute."""
        self.model.update_status()
        self.assertEqual(self.model.remote_branches, [])

        self.shell("""
                git remote add origin .
                git fetch origin > /dev/null 2>&1
        """)
        self.model.update_status()
        self.assertEqual(self.model.remote_branches, ['origin/master'])

    def test_modified(self):
        """Test the 'modified' attribute."""
        self.shell('echo change > A')
        self.model.update_status()
        self.assertEqual(self.model.modified, ['A'])

    def test_unstaged(self):
        """Test the 'unstaged' attribute."""
        self.shell('echo change > A')
        self.shell('echo C > C')
        self.model.update_status()
        self.assertEqual(self.model.unstaged, ['A', 'C'])

    def test_untracked(self):
        """Test the 'untracked' attribute."""
        self.shell('echo C > C')
        self.model.update_status()
        self.assertEqual(self.model.untracked, ['C'])

    def test_remotes(self):
        """Test the 'remote' attribute."""
        self.shell('git remote add origin .')
        self.model.update_status()
        self.assertEqual(self.model.remotes, ['origin'])

    def test_currentbranch(self):
        """Test the 'currentbranch' attribute."""
        self.shell('git checkout -b test > /dev/null 2>&1')
        self.model.update_status()
        self.assertEqual(self.model.currentbranch, 'test')

    def test_tags(self):
        """Test the 'tags' attribute."""
        self.shell('git tag test')
        self.model.update_status()
        self.assertEqual(self.model.tags, ['test'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = settings_test
from __future__ import unicode_literals

import unittest
import os

import helper
from cola.settings import Settings


class SettingsTestCase(unittest.TestCase):
    """Tests the cola.settings module"""
    def setUp(self):
        Settings._file = self._file = helper.tmp_path('settings')
        self.settings = self.new_settings()

    def tearDown(self):
        if os.path.exists(self._file):
            os.remove(self._file)

    def new_settings(self, **kwargs):
        settings = Settings(**kwargs)
        settings.load()
        return settings

    def test_gui_save_restore(self):
        """Test saving and restoring gui state"""
        settings = self.new_settings()
        settings.gui_state['test-gui'] = {'foo':'bar'}
        settings.save()

        settings = self.new_settings()
        state = settings.gui_state.get('test-gui', {})
        self.assertTrue('foo' in state)
        self.assertEqual(state['foo'], 'bar')

    def test_bookmarks_save_restore(self):
        """Test the bookmark save/restore feature"""

        # We automatically purge missing entries so we mock-out
        # git.is_git_worktree() so that this bookmark is kept.

        bookmark = '/tmp/python/thinks/this/exists'

        def mock_verify(path):
            return path == bookmark

        settings = self.new_settings()
        settings.add_bookmark(bookmark)
        settings.save()

        settings = self.new_settings(verify=mock_verify)

        bookmarks = settings.bookmarks
        self.assertEqual(len(settings.bookmarks), 1)
        self.assertTrue(bookmark in bookmarks)

        settings.remove_bookmark(bookmark)
        bookmarks = settings.bookmarks
        self.assertEqual(len(bookmarks), 0)
        self.assertFalse(bookmark in bookmarks)

    def test_bookmarks_removes_missing_entries(self):
        """Test that missing entries are removed after a reload"""
        bookmark = '/tmp/this/does/not/exist'
        settings = self.new_settings()
        settings.add_bookmark(bookmark)
        settings.save()

        settings = self.new_settings()
        bookmarks = settings.bookmarks
        self.assertEqual(len(settings.bookmarks), 0)
        self.assertFalse(bookmark in bookmarks)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = textwrap_test
#!/usr/bin/env python
from __future__ import unicode_literals

import unittest
from cola import textwrap


class WordWrapTestCase(unittest.TestCase):
    def setUp(self):
        self.tabwidth = 8
        self.limit = None

    def wrap(self, text):
        return textwrap.word_wrap(text, self.tabwidth, self.limit)

    def test_word_wrap(self):
        self.limit = 16
        text = """
12345678901 3 56 8 01 3 5 7

1 3 5"""
        expect = """
12345678901 3 56
8 01 3 5 7

1 3 5"""
        self.assertEqual(expect, self.wrap(text))

    def test_word_wrap_dashes(self):
        self.limit = 4
        text = '123-5'
        expect = '123-5'
        self.assertEqual(expect, self.wrap(text))

    def test_word_wrap_double_dashes(self):
        self.limit = 4
        text = '12--5'
        expect = '12--\n5'
        self.assertEqual(expect, self.wrap(text))

    def test_word_wrap_many_lines(self):
        self.limit = 2
        text = """
aa


bb cc dd"""
        expect = """
aa


bb
cc
dd"""
        self.assertEqual(expect, self.wrap(text))

    def test_word_python_code(self):
        self.limit = 78
        text = """
if True:
    print "hello world"
else:
    print "hello world"

"""
        self.assertEqual(text, self.wrap(text))

    def test_word_wrap_spaces(self):
        self.limit = 2
        text = ' ' * 6
        self.assertEqual(' ' * 6, self.wrap(text))

    def test_word_wrap_special_tag(self):
        self.limit = 2
        text = """
This test is so meta, even this sentence

With-special-tag: Avoids word-wrap
"""

        expect = """
This
test
is
so
meta,
even
this
sentence

With-special-tag: Avoids word-wrap
"""

        self.assertEqual(self.wrap(text), expect)

    def test_word_wrap_space_at_start_of_wrap(self):
        inputs = """0 1 2 3 4 5 6 7 8 9  0 1 2 3 4 5 6 7 8 """
        expect = """0 1 2 3 4 5 6 7 8 9\n0 1 2 3 4 5 6 7 8"""
        self.limit = 20
        actual = self.wrap(inputs)
        self.assertEqual(expect, actual)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils_test
#!/usr/bin/env python
from __future__ import unicode_literals

import unittest

from cola import utils

class ColaUtilsTestCase(unittest.TestCase):
    """Tests the cola.utils module."""

    def test_basename(self):
        """Test the utils.basename function."""
        self.assertEqual(utils.basename('bar'), 'bar')
        self.assertEqual(utils.basename('/bar'), 'bar')
        self.assertEqual(utils.basename('/bar '), 'bar ')
        self.assertEqual(utils.basename('foo/bar'), 'bar')
        self.assertEqual(utils.basename('/foo/bar'), 'bar')
        self.assertEqual(utils.basename('foo/foo/bar'), 'bar')
        self.assertEqual(utils.basename('/foo/foo/bar'), 'bar')
        self.assertEqual(utils.basename('/foo/foo//bar'), 'bar')
        self.assertEqual(utils.basename('////foo //foo//bar'), 'bar')

    def test_dirname(self):
        """Test the utils.dirname function."""
        self.assertEqual(utils.dirname('bar'), '')
        self.assertEqual(utils.dirname('/bar'), '')
        self.assertEqual(utils.dirname('//bar'), '')
        self.assertEqual(utils.dirname('///bar'), '')
        self.assertEqual(utils.dirname('foo/bar'), 'foo')
        self.assertEqual(utils.dirname('foo//bar'), 'foo')
        self.assertEqual(utils.dirname('foo /bar'), 'foo ')
        self.assertEqual(utils.dirname('/foo//bar'), '/foo')
        self.assertEqual(utils.dirname('/foo /bar'), '/foo ')
        self.assertEqual(utils.dirname('//foo//bar'), '/foo')
        self.assertEqual(utils.dirname('///foo///bar'), '/foo')

    def test_add_parents(self):
        """Test the utils.add_parents() function."""
        path_set = set(['foo///bar///baz'])
        utils.add_parents(path_set)

        self.assertTrue('foo/bar/baz' in path_set)
        self.assertTrue('foo/bar' in path_set)
        self.assertTrue('foo' in path_set)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
