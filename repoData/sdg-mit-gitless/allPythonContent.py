__FILENAME__ = commit_dialog
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Gitless's commit dialog."""


import itertools
import os
import subprocess

from gitless.core import repo as repo_lib
from gitless.core import sync as sync_lib

from . import pprint


_COMMIT_FILE = '.GL_COMMIT_EDIT_MSG'
_MERGE_MSG_FILE = 'MERGE_MSG'  # TODO(sperezde): refactor this.


def show(files):
  """Show the dialog.

  Args:
    files: files for pre-populating the dialog.

  Returns:
    A tuple (msg, files) with the commit msg and the files to commit.
  """
  if sync_lib.merge_in_progress():
    return _show_merge(files)
  elif sync_lib.rebase_in_progress():
    return _show_rebase(files)
  return _show(files)


def _show(files):
  """Show the dialog.

  Args:
    files: files for pre-populating the dialog.

  Returns:
    A tuple (msg, files) with the commit msg and the files to commit.
  """
  cf = open(_commit_file(), 'w')
  cf.write('\n')
  pprint.sep(p=cf.write)
  pprint.msg(
      'Please enter the commit message for your changes above. Lines starting '
      'with', p=cf.write)
  pprint.msg(
      '\'#\' will be ignored, and an empty message aborts the commit.',
      p=cf.write)
  pprint.blank(p=cf.write)
  pprint.msg('These are the files that will be commited:', p=cf.write)
  pprint.exp('You can add/remove files to this list', p=cf.write)
  for f in files:
    pprint.item(f, p=cf.write)
  pprint.sep(p=cf.write)
  cf.close()
  _launch_editor(cf.name)
  return _extract_info(5)


def _show_merge(files):
  """Show the dialog for a merge commit.

  Args:
    files: files that will be commited as part of the merge.

  Returns:
    A tuple (msg, files) with the commit msg and the files to commit.
  """
  cf = open(_commit_file(), 'w')
  merge_msg = open(_merge_msg_file(), 'r').read()
  cf.write(merge_msg)
  pprint.sep(p=cf.write)
  pprint.msg(
      'Please enter the commit message for your changes above. Lines starting '
      'with', p=cf.write)
  pprint.msg(
      '\'#\' will be ignored, and an empty message aborts the commit.',
      p=cf.write)
  pprint.blank(p=cf.write)
  pprint.msg(
      'These are the files that will be commited as part of the merge:',
      p=cf.write)
  pprint.exp(
      'You can add/remove files to this list, but you must commit resolved '
      'files', p=cf.write)
  for f in files:
    pprint.item(f, p=cf.write)
  pprint.sep(p=cf.write)
  cf.close()
  _launch_editor(cf.name)
  return _extract_info(5)


def _show_rebase(files):
  """Show the dialog for a rebase commit.

  Args:
    files: files that will be commited as part of the rebase.

  Returns:
    A tuple (msg, files) with the commit msg and the files to commit.
  """
  # TODO(sperezde): let the user enter a message.
  cf = open(_commit_file(), 'w')
  #cf.write('\n')
  pprint.sep(p=cf.write)
  pprint.msg(
      'The commit will have the original commit message.', p=cf.write)
  pprint.blank(p=cf.write)
  pprint.msg(
      'These are the files that will be commited as part of the rebase:',
      p=cf.write)
  pprint.exp(
      'You can add/remove files to this list, but you must commit resolved '
      'files', p=cf.write)
  for f in files:
    pprint.item(f, p=cf.write)
  pprint.sep(p=cf.write)
  cf.close()
  _launch_editor(cf.name)
  return _extract_info(4)


def _launch_editor(fp):
  editor = repo_lib.editor()
  if subprocess.call('{0} {1}'.format(editor, fp), shell=True) != 0:
    raise Exception('Call to editor {0} failed'.format(editor))


def _extract_info(exp_lines):
  """Extracts the commit msg and files to commit from the commit file.

  Args:
    exp_lines: the amount of lines between the separator and when the actual
    file list begins.

  Returns:
    A tuple (msg, files) where msg is the commit msg and files are the files to
    commit provided by the user in the editor.
  """
  cf = open(_commit_file(), 'r')
  sep = pprint.SEP + '\n'
  msg = ''
  l = cf.readline()
  while l != sep:
    msg += l
    l = cf.readline()
  # We reached the separator, this marks the end of the commit msg.
  # We exhaust the following lines so that we get to the file list.
  for _ in itertools.repeat(None, exp_lines):
    cf.readline()

  files = []
  l = cf.readline()
  while l != sep:
    files.append(l[1:].strip())
    l = cf.readline()

  # We reached the separator, this marks the end of the file list.
  return msg, files


def _commit_file():
  return os.path.join(repo_lib.gl_dir(), _COMMIT_FILE)


def _merge_msg_file():
  return os.path.join(repo_lib.gl_dir(), _MERGE_MSG_FILE)

########NEW FILE########
__FILENAME__ = file_cmd
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Helper module for gl_{track, untrack, resolve}."""


from . import pprint

from gitless.core import file as file_lib


VOWELS = ('a', 'e', 'i', 'o', 'u')


def parser(help_msg, subcmd):
  def f(subparsers):
    p = subparsers.add_parser(subcmd, help=help_msg)
    p.add_argument(
        'files', nargs='+', help='the file(s) to {0}'.format(subcmd))
    p.set_defaults(func=main(subcmd))
  return f


def main(subcmd):
  def f(args):
    success = True

    for fp in args.files:
      ret = getattr(file_lib, subcmd)(fp)
      if ret == file_lib.FILE_NOT_FOUND:
        pprint.err('Can\'t {0} a non-existent file: {1}'.format(subcmd, fp))
        success = False
      elif ret == file_lib.FILE_IS_DIR:
        pprint.dir_err_exp(fp, subcmd)
        success = False
      elif ret is file_lib.FILE_ALREADY_UNTRACKED:
        pprint.err('File {0} is already untracked'.format(fp))
        success = False
      elif ret is file_lib.FILE_ALREADY_TRACKED:
        pprint.err('File {0} is already tracked'.format(fp))
        success = False
      elif ret is file_lib.FILE_IS_IGNORED:
        pprint.err('File {0} is ignored. Nothing to {1}'.format(fp, subcmd))
        pprint.err_exp(
            'edit the .gitignore file to stop ignoring file {0}'.format(fp))
        success = False
      elif ret is file_lib.FILE_IN_CONFLICT:
        pprint.err('Can\'t {0} a file in conflict'.format(subcmd))
        success = False
      elif ret is file_lib.FILE_NOT_IN_CONFLICT:
        pprint.err('File {0} has no conflicts'.format(fp))
        success = False
      elif ret is file_lib.FILE_ALREADY_RESOLVED:
        pprint.err(
            'Nothing to resolve. File {0} was already marked as '
            'resolved'.format(fp))
        success = False
      elif ret is file_lib.SUCCESS:
        pprint.msg(
            'File {0} is now a{1} {2}{3}d file'.format(
                fp, 'n' if subcmd.startswith(VOWELS) else '', subcmd,
                '' if subcmd.endswith('e') else 'e'))
      else:
        raise Exception('Unexpected return code {0}'.format(ret))

    return success
  return f

########NEW FILE########
__FILENAME__ = gl
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl - Main Gitless's command. Dispatcher to the other cmds."""


import argparse
import traceback


from clint.textui import colored

from gitless.core import repo as repo_lib

from . import gl_track
from . import gl_untrack
from . import gl_status
from . import gl_diff
from . import gl_commit
from . import gl_branch
from . import gl_checkout
from . import gl_merge
from . import gl_rebase
from . import gl_remote
from . import gl_resolve
from . import gl_publish
from . import gl_init
from . import gl_history
from . import pprint


SUCCESS = 0
ERRORS_FOUND = 1
# 2 is used by argparse to indicate cmd syntax errors.
INTERNAL_ERROR = 3
NOT_IN_GL_REPO = 4

VERSION = '0.6.2'
URL = 'http://gitless.com'


colored.DISABLE_COLOR = not repo_lib.color_output()


def main():
  parser = argparse.ArgumentParser(
      description=(
          'Gitless: a version control system built on top of Git. More info, '
          'downloads and documentation available at {0}'.format(URL)),
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument(
      '--version', action='version', version=(
         'GL Version: {0}\nYou can check if there\'s a new version of Gitless '
         'available by visiting {1}'.format(VERSION, URL)))
  subparsers = parser.add_subparsers(dest='subcmd_name')

  sub_cmds = [
      gl_track, gl_untrack, gl_status, gl_diff, gl_commit, gl_branch,
      gl_checkout, gl_merge, gl_resolve, gl_rebase, gl_remote, gl_publish,
      gl_init, gl_history]
  for sub_cmd in sub_cmds:
    sub_cmd.parser(subparsers)

  args = parser.parse_args()
  if args.subcmd_name != 'init' and not repo_lib.gl_dir():
    pprint.err(
        'You are not in a Gitless repository. To make this directory a '
        'repository do gl init. For cloning existing repositories do gl init '
        'repo.')
    return NOT_IN_GL_REPO

  try:
    return SUCCESS if args.func(args) else ERRORS_FOUND
  except KeyboardInterrupt:
    # The user pressed Crl-c.
    # Disable pylint's superflous-parens warning (they are not superflous
    # in this case -- python 2/3 compatibility).
    # pylint: disable=C0325
    print('\n')
    pprint.msg('Keyboard interrupt detected, operation aborted')
    return SUCCESS
  except:
    pprint.err(
        'Oops...something went wrong (recall that Gitless is in beta). If you '
        'want to help, report the bug at {0}/community.html and include the '
        'following information:\n\n{1}\n\n{2}'.format(
            URL, VERSION, traceback.format_exc()))
    return INTERNAL_ERROR

########NEW FILE########
__FILENAME__ = gl_branch
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl branch - Create, edit, delete or switch branches."""


from clint.textui import colored

from gitless.core import branch as branch_lib
from gitless.core import sync as sync_lib

from . import pprint


def parser(subparsers):
  """Adds the branch parser to the given subparsers object."""
  branch_parser = subparsers.add_parser(
      'branch', help='list, create, edit, delete or switch branches')
  branch_parser.add_argument(
      'branch', nargs='?',
      help='switch to branch (will be created if it doesn\'t exist yet)')
  branch_parser.add_argument(
      'divergent_point', nargs='?',
      help='the commit from where to \'branch out\' (only relevant if a new '
      'branch is created; defaults to HEAD)', default='HEAD')
  branch_parser.add_argument(
      '-d', '--delete', nargs='+', help='delete branch(es)', dest='delete_b')
  branch_parser.add_argument(
      '-su', '--set-upstream', help='set the upstream branch',
      dest='upstream_b')
  branch_parser.add_argument(
      '-uu', '--unset-upstream', help='unset the upstream branch',
      action='store_true')
  branch_parser.set_defaults(func=main)


def main(args):
  ret = True
  if args.branch:
    b_st = branch_lib.status(args.branch)
    if b_st and b_st.is_current:
      pprint.err(
          'You are already in branch {0}. No need to switch.'.format(
              colored.green(args.branch)))
      pprint.err_exp('to list existing branches do gl branch')
      return False

    if sync_lib.rebase_in_progress():
      pprint.err(
          'You can\'t switch branches when a rebase is in progress (yet '
          '-- this will be implemented in the future)')
      return False
    elif sync_lib.merge_in_progress():
      pprint.err(
          'You can\'t switch branches when merge is in progress (yet '
          '-- this will be implemented in the future)')
      return False

    if not b_st and not _do_create(args.branch, args.divergent_point):
      return False

    branch_lib.switch(args.branch)
    pprint.msg('Switched to branch {0}'.format(colored.green(args.branch)))
  elif args.delete_b:
    ret = _do_delete(args.delete_b)
  elif args.upstream_b:
    ret = _do_set_upstream(args.upstream_b)
  elif args.unset_upstream:
    ret = _do_unset_upstream()
  else:
    _do_list()

  return ret


def _do_create(branch_name, divergent_point):
  errors_found = False

  ret = branch_lib.create(branch_name, dp=divergent_point)
  if ret == branch_lib.INVALID_NAME:
    pprint.err('Invalid branch name')
    errors_found = True
  elif ret == branch_lib.INVALID_DP:
    pprint.msg('Invalid divergent point {0}'.format(divergent_point))
    errors_found = True
  elif ret == branch_lib.SUCCESS:
    pprint.msg('Created new branch {0}'.format(branch_name))
  else:
    raise Exception('Unrecognized ret code {0}'.format(ret))
  return not errors_found


def _do_list():
  pprint.msg('List of branches:')
  pprint.exp('do gl branch <b> to create or switch to branch b')
  pprint.exp('do gl branch -d <b> to delete branch b')
  pprint.exp(
      'do gl branch -su <upstream> to set an upstream for the current branch')
  pprint.exp('* = current branch')
  pprint.blank()
  for name, is_current, upstream, upstream_exists in branch_lib.status_all():
    current_str = '*' if is_current else ' '
    upstream_str = ''
    if upstream:
      np_str = ' --not present in remote yet' if not upstream_exists else ''
      upstream_str = '(upstream is {0}{1})'.format(upstream, np_str)
    color = colored.green if is_current else colored.yellow
    pprint.item('{0} {1} {2}'.format(current_str, color(name), upstream_str))


def _do_delete(delete_b):
  errors_found = False

  for b in delete_b:
    b_st = branch_lib.status(b)
    cb = colored.green(b)
    if not b_st:
      pprint.err('Can\'t remove non-existent branch {0}'.format(cb))
      pprint.err_exp('do gl branch to list existing branches')
      errors_found = True
    elif b_st and b_st.is_current:
      pprint.err('Can\'t remove current branch {0}'.format(cb))
      pprint.err_exp(
          'do gl branch <b> to create or switch to another branch b and then '
          'gl branch -d {0} to remove branch {0}'.format(cb))
      errors_found = True
    elif not pprint.conf_dialog('Branch {0} will be removed'.format(cb)):
      pprint.msg('Aborted: removal of branch {0}'.format(cb))
    else:
      branch_lib.delete(b)
      pprint.msg('Branch {0} removed successfully'.format(cb))

  return not errors_found


def _do_set_upstream(upstream):
  if '/' not in upstream:
    pprint.err(
        'Invalid upstream branch. It must be in the format remote/branch')
    return True

  ret = branch_lib.set_upstream(upstream)

  errors_found = False
  upstream_remote, upstream_branch = upstream.split('/')
  if ret is branch_lib.REMOTE_NOT_FOUND:
    pprint.err('Remote {0} not found'.format(upstream_remote))
    pprint.err_exp('do gl remote to list all existing remotes')
    pprint.err_exp(
        'do gl remote {0} <r_url> to add a new remote {0} mapping to '
        'r_url'.format(upstream_remote))
    errors_found = True
  elif ret is branch_lib.SUCCESS:
    pprint.msg(
        'Current branch {0} set to track {1}/{2}'.format(
            colored.green(branch_lib.current()), upstream_remote,
            upstream_branch))

  return not errors_found


def _do_unset_upstream():
  ret = branch_lib.unset_upstream()

  errors_found = False
  if ret is branch_lib.UPSTREAM_NOT_SET:
    pprint.err('Current branch has no upstream set')
    pprint.err_exp(
        'do gl branch to list all existing branches -- if a branch has an '
        'upstream set it will be shown')
    pprint.err_exp(
      'do gl branch -su <upstream> to set an upstream for the current branch')
    errors_found = True
  elif ret is branch_lib.SUCCESS:
    pprint.msg('Upstream unset for current branch')

  return not errors_found

########NEW FILE########
__FILENAME__ = gl_checkout
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl checkout - Checkout committed versions of files."""


from gitless.core import file as file_lib

from . import pprint


def parser(subparsers):
  """Adds the checkout parser to the given subparsers object."""
  checkout_parser = subparsers.add_parser(
      'checkout', help='checkout committed versions of files')
  checkout_parser.add_argument(
      '-cp', '--commit_point', help=(
          'the commit point to checkout the files at. Defaults to HEAD.'),
      dest='cp', default='HEAD')
  checkout_parser.add_argument(
      'files', nargs='+', help='the file(s) to checkout')
  checkout_parser.set_defaults(func=main)


def main(args):
  success = True

  for fp in args.files:
    if not _checkout_file(fp, args.cp):
      success = False

  return success


def _checkout_file(fp, cp):
  """Checkout file fp at commit point cp.

  Will output to screen if some error is encountered.

  Returns:
    True if the file was checkouted successfully or False if some error was
    encountered.
  """
  conf_msg = (
      'You have uncomitted changes in {0} that could be overwritten by the '
      'checkout'.format(fp))
  f = file_lib.status(fp)
  if f and f.type == file_lib.TRACKED and f.modified and not pprint.conf_dialog(
      conf_msg):
    pprint.err('Checkout aborted')
    return False

  ret, _ = file_lib.checkout(fp, cp)
  if ret == file_lib.FILE_NOT_FOUND_AT_CP:
    pprint.err('Checkout aborted')
    pprint.err('There\'s no file {0} at {1}'.format(fp, cp))
    return False
  elif ret == file_lib.FILE_IS_DIR:
    pprint.dir_err_exp(fp, 'checkout')
    return False
  elif ret == file_lib.SUCCESS:
    pprint.msg(
        'File {0} checked out sucessfully to its state at {1}'.format(fp, cp))
    return True
  else:
    raise Exception('Unrecognized ret code {0}'.format(ret))

########NEW FILE########
__FILENAME__ = gl_commit
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl commit - Record changes in the local repository."""


from gitless.core import file as file_lib
from gitless.core import sync as sync_lib

from . import commit_dialog
from . import pprint


def parser(subparsers):
  """Adds the commit parser to the given subparsers object."""
  commit_parser = subparsers.add_parser(
      'commit', help='record changes in the local repository')
  commit_parser.add_argument(
      'only_files', nargs='*',
      help='only the files listed as arguments will be committed (files could '
           'be tracked or untracked files)')
  commit_parser.add_argument(
      '-exc', '--exclude', nargs='+',
      help=('files listed as arguments will be excluded from the commit (files '
            'must be tracked files)'),
      dest='exc_files')
  commit_parser.add_argument(
      '-inc', '--include', nargs='+',
      help=('files listed as arguments will be included to the commit (files '
            'must be untracked files)'),
      dest='inc_files')
  commit_parser.add_argument(
      '-p', '--partial', help='do a partial commit', action='store_true')
  commit_parser.add_argument(
      '-sc', '--skip-checks', help='skip pre-commit check', action='store_true',
      default=False, dest='sc')
  commit_parser.add_argument(
      '-m', '--message', help='Commit message', dest='m')
  commit_parser.set_defaults(func=main)


def main(args):
  # TODO(sperezde): re-think this worflow a bit.

  only_files = frozenset(args.only_files)
  exc_files = frozenset(args.exc_files) if args.exc_files else []
  inc_files = frozenset(args.inc_files) if args.inc_files else []

  if not _valid_input(only_files, exc_files, inc_files):
    return False

  commit_files = _compute_fs(only_files, exc_files, inc_files)

  if not commit_files:
    pprint.err('Commit aborted')
    pprint.err('No files to commit')
    pprint.err_exp('use gl track <f> if you want to track changes to file f')
    return False

  msg = args.m
  if not msg:
    # Show the commit dialog.
    msg, commit_files = commit_dialog.show(commit_files)
    if not msg.strip() and not sync_lib.rebase_in_progress():
      pprint.err('Commit aborted')
      pprint.err('No commit message provided')
      return False
    if not commit_files:
      pprint.err('Commit aborted')
      pprint.err('No files to commit')
      pprint.err_exp('use gl track <f> if you want to track changes to file f')
      return False
    if not _valid_input(commit_files, [], []):
      return False

  _auto_track(commit_files)
  commit = sync_lib.commit if not args.partial else _do_partial_commit
  ret, out = commit(commit_files, msg, skip_checks=args.sc)
  if not ret:
    pprint.msg('Commit aborted')
    return True
  if ret == sync_lib.SUCCESS:
    if out:
      pprint.msg(out)
  elif ret == sync_lib.PRE_COMMIT_FAILED:
    pprint.err('Commit aborted')
    pprint.err('The pre-commit check failed:')
    pprint.err_exp('fix the problems and run gl commit again')
    pprint.err_exp(
        'alternatively, you can skip the pre-commit checks with the '
        '--skip-checks flag')
    pprint.err_blank()
    pprint.err(out)
  elif ret == sync_lib.UNRESOLVED_CONFLICTS:
    pprint.err('Commit aborted')
    pprint.err('You have unresolved conflicts:')
    pprint.err_exp(
        'use gl resolve <f> to mark file f as resolved once you fixed the '
        'conflicts')
    for f in out:
      pprint.err_item(f.fp)
    return False
  elif ret == sync_lib.RESOLVED_FILES_NOT_IN_COMMIT:
    pprint.err('Commit aborted')
    pprint.err('You have resolved files that were not included in the commit:')
    pprint.err_exp('these must be part of the commit')
    for f in out:
      pprint.err_item(f.fp)
    return False
  else:
    raise Exception('Unexpected return code {0}'.format(ret))

  return True


def _valid_input(only_files, exc_files, inc_files):
  """Validates user input.

  This function will print to stdout in case user-provided values are invalid
  (and return False).

  Args:
    only_files: user-provided list of filenames to be committed only.
    exc_files: list of filenames to be excluded from commit.
    inc_files: list of filenames to be included to the commit.

  Returns:
    True if the input is valid, False if otherwise.
  """
  if only_files and (exc_files or inc_files):
    pprint.err('Commit aborted')
    pprint.err(
        'You provided a list of filenames to be committed only but also '
        'provided a list of files to be excluded or included.')
    return False

  ret = True
  err = []
  for fp in only_files:
    f = file_lib.status(fp)
    if not f:
      err.append('File {0} doesn\'t exist'.format(fp))
      ret = False
    elif f.type == file_lib.TRACKED and not f.modified:
      err.append(
          'File {0} is a tracked file but has no modifications'.format(fp))
      ret = False

  for fp in exc_files:
    f = file_lib.status(fp)
    # We check that the files to be excluded are existing tracked files.
    if not f:
      err.append('File {0} doesn\'t exist'.format(fp))
      ret = False
    elif f.type != file_lib.TRACKED:
      err.append(
          'File {0}, listed to be excluded from commit, is not a tracked '
          'file'.format(fp))
      ret = False
    elif f.type == file_lib.TRACKED and not f.modified:
      err.append(
          'File {0}, listed to be excluded from commit, is a tracked file but '
          'has no modifications'.format(fp))
      ret = False
    elif f.resolved:
      err.append('You can\'t exclude a file that has been resolved')
      ret = False

  for fp in inc_files:
    f = file_lib.status(fp)
    # We check that the files to be included are existing untracked files.
    if not f:
      err.append('File {0} doesn\'t exist'.format(fp))
      ret = False
    elif f.type != file_lib.UNTRACKED:
      err.append(
          'File {0}, listed to be included in the commit, is not a untracked '
          'file'.format(fp))
      ret = False

  if not ret:
    # Some error occured.
    pprint.err('Commit aborted')
    for e in err:
      pprint.err(e)

  return ret


def _compute_fs(only_files, exc_files, inc_files):
  """Compute the final fileset to commit.

  Args:
    only_files: list of filenames to be committed only.
    exc_files: list of filenames to be excluded from commit.
    inc_files: list of filenames to be included to the commit.

  Returns:
    A list of filenames to be committed.
  """
  if only_files:
    ret = only_files
  else:
    # Tracked modified files.
    ret = frozenset(
        f.fp for f in file_lib.status_all() if f.type == file_lib.TRACKED and
        f.modified)
    # TODO(sperezde): the following is a mega-hack, do it right.
    from gitpylib import common
    ret = ret.difference(common.real_case(exc_f) for exc_f in exc_files)
    ret = ret.union(common.real_case(inc_f) for inc_f in inc_files)

  return ret


def _auto_track(files):
  """Tracks those untracked files in the list."""
  for fp in files:
    f = file_lib.status(fp)
    if not f:
      raise Exception('Expected {0} to exist, but it doesn\'t'.format(fp))
    if f.type == file_lib.UNTRACKED:
      file_lib.track(f.fp)


def _do_partial_commit(files, msg, skip_checks=False):
  pprint.msg('Entering partial commit mode')
  pprint.exp(
      'you can always input "a" or "abort" or "q" or "quit" to abort the '
      'commit')
  pc = sync_lib.partial_commit(files)
  for chunked_fp in pc:
    print('\n')
    pprint.msg('Looking at file "{0}"'.format(chunked_fp.fp))
    for chunk in chunked_fp:
      while True:
        pprint.diff(*chunk.diff)
        print('\n')
        pprint.msg('Do you want to include this chunk in the commit?')
        pprint.exp('input "y" or "yes" to include this chunk in the commit')
        pprint.exp('input "n" or "no" to include this chunk in the commit')
        pprint.exp(
            'input "a" or "abort" or "q" or "quit" to abort the commit')
        user_input = pprint.get_user_input()
        if user_input in ['y', 'yes']:
          chunk.include()
          break
        elif user_input in ['n', 'no']:
          break
        elif user_input in ['a', 'abort', 'q', 'quit']:
          return None, None
        else:
          pprint.msg(
              'Unrecognized input "{0}", please try again'.format(user_input))
  return pc.commit(msg, skip_checks=skip_checks)

########NEW FILE########
__FILENAME__ = gl_diff
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl diff - Show changes in files."""


import os
import subprocess
import tempfile

from gitless.core import file as file_lib

from . import pprint


def parser(subparsers):
  """Adds the diff parser to the given subparsers object."""
  diff_parser = subparsers.add_parser(
      'diff', help='show changes in files')
  diff_parser.add_argument(
      'files', nargs='*', help='the files to diff')
  diff_parser.set_defaults(func=main)


def main(args):
  if not args.files:
    # Tracked modified files.
    files = [
        f.fp for f in file_lib.status_all() if f.type == file_lib.TRACKED
        and f.modified]
    if not files:
      pprint.msg(
          'Nothing to diff (there are no tracked files with modifications).')
      return True
  else:
    files = args.files

  success = True
  for fp in files:
    ret, (out, padding, additions, deletions) = file_lib.diff(fp)

    if ret == file_lib.FILE_NOT_FOUND:
      pprint.err('Can\'t diff a non-existent file: {0}'.format(fp))
      success = False
    elif ret == file_lib.FILE_IS_UNTRACKED:
      pprint.err(
          'You tried to diff untracked file {0}. It\'s probably a mistake. If '
          'you really care about changes in this file you should start '
          'tracking changes to it with gl track {1}'.format(fp, fp))
      success = False
    elif ret == file_lib.FILE_IS_IGNORED:
      pprint.err(
          'You tried to diff ignored file {0}. It\'s probably a mistake. If '
          'you really care about changes in this file you should stop ignoring '
          'it by editing the .gigignore file'.format(fp))
      success = False
    elif ret == file_lib.FILE_IS_DIR:
      pprint.dir_err_exp(fp, 'diff')
      success = False
    elif ret == file_lib.SUCCESS:
      if not out:
        pprint.msg(
            'The working version of file {0} is the same as its last '
            'committed version. No diffs to output'.format(fp))
        continue

      with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
        pprint.msg(
            'Diff of file {0} with its last committed version'.format(fp),
            p=tf.write)
        put_s = lambda num: '' if num == 1 else 's'
        pprint.msg(
            '{0} line{1} added'.format(additions, put_s(additions)), p=tf.write)
        pprint.msg(
            '{0} line{1} removed'.format(deletions, put_s(deletions)),
            p=tf.write)
        pprint.diff(out, padding, p=tf.write)

      subprocess.call('less -r -f {0}'.format(tf.name), shell=True)
      os.remove(tf.name)
    else:
      raise Exception('Unrecognized ret code {0}'.format(ret))

  return success

########NEW FILE########
__FILENAME__ = gl_history
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl history - Show commit history."""


import os
import subprocess
import tempfile

from clint.textui import colored, indent, puts

from gitless.core import repo as repo_lib

from . import pprint


def parser(subparsers):
  """Adds the history parser to the given subparsers object."""
  history_parser = subparsers.add_parser(
      'history', help='show commit history')
  history_parser.add_argument(
      '-v', '--verbose', help='be verbose, will output the diffs of the commit',
      action='store_true')
  history_parser.set_defaults(func=main)


def main(args):
  with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
    for ci in repo_lib.history(include_diffs=args.verbose):
      puts(colored.yellow('Commit Id: {0}'.format(ci.id)), stream=tf.write)
      puts(colored.yellow(
        'Author:    {0} <{1}>'.format(ci.author.name, ci.author.email)),
        stream=tf.write)
      puts(colored.yellow(
        'Date:      {0} ({1})'.format(ci.author.date, ci.author.date_relative)),
        stream=tf.write)
      puts(stream=tf.write)
      with indent(4):
        for l in ci.msg.splitlines():
          puts(l, stream=tf.write)
      puts(stream=tf.write)
      puts(stream=tf.write)
      for diff in ci.diffs:
        puts(
            colored.cyan('Diff of file {0}'.format(diff.fp_before)),
            stream=tf.write)
        if diff.fp_before != diff.fp_after:
          puts(colored.cyan(
              ' (renamed to {0})'.format(diff.fp_after)), stream=tf.write)
        puts(stream=tf.write)
        puts(stream=tf.write)
        pprint.diff(*diff.diff, p=tf.write)
        puts(stream=tf.write)
        puts(stream=tf.write)
      puts(stream=tf.write)
  subprocess.call('less -r -f {0}'.format(tf.name), shell=True)
  os.remove(tf.name)
  return True

########NEW FILE########
__FILENAME__ = gl_init
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl init - Create an empty repo or make a clone."""


import os

from gitless.core import init as init_lib

from . import pprint


def parser(subparsers):
  """Adds the init parser to the given subparsers object."""
  init_parser = subparsers.add_parser(
      'init',
      help=(
          'create an empty Gitless\'s repository or create one from an '
          'existing remote repository.'))
  init_parser.add_argument(
      'repo', nargs='?',
      help=(
          'an optional remote repo address from where to read to create the'
          'local repo.'))
  init_parser.set_defaults(func=main)


def main(args):
  ret = init_lib.init_from(args.repo) if args.repo else init_lib.init_cwd()

  if ret == init_lib.REPO_UNREACHABLE:
    pprint.err(
        'Couldn\'t reach remote repository \'{0}\' to init from'.format(
            args.repo))
    pprint.err_exp('make sure you are connected to the internet')
    pprint.err_exp(
        'make sure you have the necessary permissions to access {0}'.format(
            args.repo))
    return False
  if ret is init_lib.NOTHING_TO_INIT:
    pprint.err('Nothing to init, this directory is already a Gitless\'s repo')
    return False
  elif ret is init_lib.SUCCESS:
    pprint.msg('Local repo created in \'{0}\''.format(os.getcwd()))
    if args.repo:
      pprint.msg('Initialized from remote \'{0}\''.format(args.repo))
    return True
  else:
    raise Exception('Unexpected return code {0}'.format(ret))

########NEW FILE########
__FILENAME__ = gl_merge
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl merge - Merge the divergent changes of one branch onto another."""


from gitless.core import branch as branch_lib
from gitless.core import sync as sync_lib

from . import pprint


def parser(subparsers):
  """Adds the merge parser to the given subparsers object."""
  merge_parser = subparsers.add_parser(
      'merge', help='merge the divergent changes of one branch onto another')
  group = merge_parser.add_mutually_exclusive_group()
  group.add_argument(
      'src', nargs='?', help='the source branch to read changes from')
  group.add_argument(
      '-a', '--abort', help='abort the merge in progress', action='store_true')
  merge_parser.set_defaults(func=main)


def main(args):
  if args.abort:
    if sync_lib.abort_merge() is sync_lib.MERGE_NOT_IN_PROGRESS:
      pprint.err('No merge in progress, nothing to abort')
      pprint.err_exp(
          'To merge divergent changes of branch b onto the current branch do gl'
          ' merge <b>')
      return False
    pprint.msg('Merge aborted successfully')
    return True

  if not args.src:
    # We use the upstream branch, if any.
    current = branch_lib.current()
    b_st = branch_lib.status(current)
    if b_st.upstream is None:
      pprint.err(
          'No src branch specified and the current branch has no upstream '
          'branch set')
      return False

    if not b_st.upstream_exists:
      pprint.err(
          'Current branch has an upstream set but it hasn\'t been published '
          'yet')
      return False

    # If we reached this point, it is safe to use the upstream branch to get
    # changes from.
    args.src = b_st.upstream
    pprint.msg(
        'No src branch specified, defaulted to getting changes from upstream '
        'branch {0}'.format(args.src))

  ret, out = sync_lib.merge(args.src)
  if ret is sync_lib.SRC_NOT_FOUND:
    pprint.err('Branch {0} not found'.format(args.src))
    pprint.err_exp('do gl branch to list all existing branches')
    return False
  elif ret is sync_lib.SRC_IS_CURRENT_BRANCH:
    pprint.err('Branch {0} is the current branch'.format(args.src))
    pprint.err_exp(
        'to merge branch {0} onto another branch b, do gl branch b, and gl '
        'merge {0} from there'.format(args.src))
    return False
  elif ret is sync_lib.REMOTE_NOT_FOUND:
    pprint.err('The remote of {0} doesn\'t exist'.format(args.src))
    pprint.err_exp('to list available remotes do gl remote show')
    pprint.err_exp(
        'to add a new remote use gl remote add remote_name remote_url')
    return False
  elif ret is sync_lib.REMOTE_UNREACHABLE:
    pprint.err('Can\'t reach the remote')
    pprint.err_exp('make sure that you are still connected to the internet')
    pprint.err_exp('make sure you still have permissions to access the remote')
    return False
  elif ret is sync_lib.REMOTE_BRANCH_NOT_FOUND:
    pprint.err('The branch doesn\'t exist in the remote')
    return False
  elif ret is sync_lib.NOTHING_TO_MERGE:
    pprint.err(
        'No divergent changes to merge from {0}'.format(args.src))
    return False
  elif ret is sync_lib.LOCAL_CHANGES_WOULD_BE_LOST:
    pprint.err(
        'Merge was aborted because your local changes to the following files '
        'would be overwritten by merge:')
    pprint.err_exp('use gl commit to commit your changes')
    pprint.err_exp(
        'use gl checkout HEAD f to discard changes to tracked file f')
    for fp in out:
      pprint.err_item(fp)

    return False
  elif ret is sync_lib.CONFLICT:
    pprint.err(
        'Merge was aborted becase there are conflicts you need to resolve')
    pprint.err_exp(
        'use gl status to look at the files in conflict')
    pprint.err_exp(
        'use gl merge --abort to go back to the state before the merge')
    pprint.err_exp('use gl resolve <f> to mark file f as resolved')
    pprint.err_exp(
        'once you solved all conflicts do gl commit to complete the merge')
    return False
  elif ret is sync_lib.SUCCESS:
    pprint.msg('Merged succeeded')

  return True

########NEW FILE########
__FILENAME__ = gl_publish
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl publish - Publish commits upstream."""


from gitless.core import sync as sync_lib

from . import pprint


def parser(subparsers):
  """Adds the publish parser to the given subparsers object."""
  push_parser = subparsers.add_parser(
      'publish', help='publish commits upstream')
  push_parser.set_defaults(func=main)


def main(_):
  ret, out = sync_lib.publish()
  success = True

  if ret == sync_lib.SUCCESS:
    # Disable pylint's superflous-parens warning (they are not superflous
    # in this case -- python 2/3 compatibility).
    # pylint: disable=C0325
    print(out)
  elif ret == sync_lib.UPSTREAM_NOT_SET:
    pprint.err('Current branch has no upstream set')
    pprint.err_exp(
        'to set an upstream branch do gl branch --set-upstream '
        'remote/remote_branch')
    success = False
  elif ret == sync_lib.NOTHING_TO_PUSH:
    pprint.err('No commits to publish')
    success = False
  elif ret == sync_lib.PUSH_FAIL:
    pprint.err(
        'Publish failed, there are conflicting changes you need to converge')
    pprint.err_exp('use gl rebase or gl merge to converge the upstream changes')
    success = False
  else:
    raise Exception('Unrecognized ret code {0}'.format(ret))

  return success

########NEW FILE########
__FILENAME__ = gl_rebase
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl rebase - Rebase one branch onto another."""


from gitless.core import branch as branch_lib
from gitless.core import sync as sync_lib

from . import pprint


def parser(subparsers):
  """Adds the rebase parser to the given subparsers object."""
  rebase_parser = subparsers.add_parser(
      'rebase',
      help=(
          'converge divergent changes of two branches by rebasing one onto '
          'another'))
  group = rebase_parser.add_mutually_exclusive_group()
  group.add_argument(
      'src', nargs='?', help='the source branch to use as a base for rebasing')
  group.add_argument(
      '-a', '--abort', help='abort the rebase in progress', action='store_true')
  group.add_argument(
      '-s', '--skip',
      help='skip the current commit and continue with the next one',
      action='store_true')

  rebase_parser.set_defaults(func=main)


def main(args):
  if args.abort:
    if sync_lib.abort_rebase() is sync_lib.REBASE_NOT_IN_PROGRESS:
      pprint.err('No rebase in progress, nothing to abort')
      pprint.err_exp(
          'To converge divergent changes of the current branch and branch b by '
          'rebasing the current branch out of b do gl rebase <b>')
      return False
    pprint.msg('Rebase aborted')
    return True

  if args.skip:
    if sync_lib.skip_rebase_commit() is sync_lib.REBASE_NOT_IN_PROGRESS:
      pprint.err('No rebase in progress, nothing to skip')
      pprint.err_exp(
          'To converge divergent changes of the current branch and branch b by '
          'rebasing the current branch out of b do gl rebase <b>')
      return False

    pprint.msg('Rebase commit skipped')
    return True

  if not args.src:
    # We use the upstream branch, if any.
    current = branch_lib.current()
    b_st = branch_lib.status(current)
    if b_st.upstream is None:
      pprint.err(
          'No src branch specified and the current branch has no upstream '
          'branch set')
      return False

    if not b_st.upstream_exists:
      pprint.err(
          'Current branch has an upstream set but it hasn\'t been published '
          'yet')
      return False

    # If we reached this point, it is safe to use the upstream branch to get
    # changes from.
    args.src = b_st.upstream
    pprint.msg(
        'No src branch specified, defaulted to getting changes from upstream '
        'branch {0}'.format(args.src))

  if sync_lib.rebase_in_progress():
    pprint.err('You are already in the middle of a rebase')
    pprint.err_exp('use gl rebase --abort to abort the current rebase')
    return False

  ret, _ = sync_lib.rebase(args.src)
  if ret is sync_lib.SRC_NOT_FOUND:
    pprint.err('Branch {0} not found'.format(args.src))
    pprint.err_exp('do gl branch to list all existing branches')
    return False
  elif ret is sync_lib.SRC_IS_CURRENT_BRANCH:
    pprint.err('Branch {0} is the current branch'.format(args.src))
    pprint.err_exp(
        'to rebase branch {0} onto another branch b, do gl branch b, and gl '
        'rebase {0} from there'.format(args.src))
    return False
  elif ret is sync_lib.REMOTE_NOT_FOUND:
    pprint.err('The remote of {0} doesn\'t exist'.format(args.src))
    pprint.err_exp('to list available remotes do gl remote show')
    pprint.err_exp(
        'to add a new remote use gl remote add remote_name remote_url')
    return False
  elif ret is sync_lib.REMOTE_UNREACHABLE:
    pprint.err('Can\'t reach the remote')
    pprint.err_exp('make sure that you are still connected to the internet')
    pprint.err_exp('make sure you still have permissions to access the remote')
    return False
  elif ret is sync_lib.REMOTE_BRANCH_NOT_FOUND:
    pprint.err('The branch doesn\'t exist in the remote')
    return False
  elif ret is sync_lib.CONFLICT:
    pprint.err('There are conflicts you need to resolve')
    pprint.err_exp('use gl status to look at the files in conflict')
    pprint.err_exp(
        'edit the files in conflict and do gl resolve <f> to mark file f as '
        'resolved')
    pprint.err_exp(
        'once all conflicts have been resolved do gl commit to commit the '
        'changes and continue rebasing')
    pprint.err_blank()
    # pprint.err('Files in conflict:')
    # for f in out:
    #  pprint.err_item(f)
    return False
  elif ret is sync_lib.NOTHING_TO_REBASE:
    pprint.err(
        'No divergent changes to rebase from {0}'.format(args.src))
  elif ret is sync_lib.LOCAL_CHANGES_WOULD_BE_LOST:
    pprint.err(
        'Rebase was aborted because you have uncommited local changes')
    pprint.err_exp('use gl commit to commit your changes')
    return False
  elif ret is sync_lib.SUCCESS:
    pprint.msg('Rebase succeded')
    return True
  else:
    raise Exception('Unexpected ret code {0}'.format(ret))

########NEW FILE########
__FILENAME__ = gl_remote
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl remote - {Add, remove, get info of} remotes."""


from gitless.core import remote as remote_lib

from . import pprint


def parser(subparsers):
  """Adds the remote parser to the given subparsers object."""
  remote_parser = subparsers.add_parser(
      'remote', help='list, create or delete remotes')

  remote_parser.add_argument(
      'remote_name', nargs='?', help='the name of the remote')
  remote_parser.add_argument(
      'remote_url', nargs='?',
      help='the url of the remote. Only relevant when adding a new remote')
  remote_parser.add_argument(
      '-d', '--delete', nargs='+', help='delete remote(es)', dest='delete_r')
  # TODO(sperezde): do this.
#  remote_parser.add_argument(
#      '-v', '--verbose',
#      help='be verbose, will output more info when listing remotes',
#      action='store_true')

  remote_parser.set_defaults(func=main)


def main(args):
  if args.remote_name:
    return _do_add(args)
  elif args.delete_r:
    return _do_delete(args.delete_r)
  else:
    _do_list()
    return True


def _do_add(args):
  rn = args.remote_name
  ru = args.remote_url
  ret = remote_lib.add(rn, ru)
  success = True

  if ret == remote_lib.REMOTE_ALREADY_SET:
    pprint.err('There\'s already a remote set with that name')
    pprint.err_exp('to list existing remotes do gl remote')
    pprint.err_exp(
        'if you want to change the url for remote %s do gl remote -d %s, and '
        'then gl remote %s new_url' % (rn, rn, rn))
    success = False
  elif ret == remote_lib.REMOTE_UNREACHABLE:
    pprint.err('Couldn\'t reach {0} to create {1}'.format(ru, rn))
    pprint.err_exp('make sure that you are connected to the internet')
    pprint.err_exp(
        'make sure that you have permissions to access the remote')
    success = False
  elif ret == remote_lib.INVALID_NAME:
    pprint.err(
        'Invalid remote name {0}, remote names can\'t have \'/\''.format(ru))
    success = False
  elif ret == remote_lib.SUCCESS:
    pprint.msg('Remote {0} mapping to {1} created successfully'.format(rn, ru))
    pprint.exp('to list existing remotes do gl remote')
    pprint.exp('to remove {0} do gl remote -d {1}'.format(rn, rn))
  else:
    raise Exception('Unrecognized ret code %s' % ret)

  return success


def _do_list():
  pprint.msg('List of remotes:')
  pprint.exp('do gl remote <r> <r_url> to add a new remote r mapping to r_url')
  pprint.exp('do gl remote -d <r> to delete remote r')
  remotes = remote_lib.info_all()
  pprint.blank()
  if not remotes:
    pprint.item('There are no remotes to list')
  else:
    for rn in remotes:
      mapping = ' (maps to {0})'.format(rn.upstream)
      if rn.downstream != rn.upstream:
        mapping = ' (maps to {0} downstream, {1} upstream)'.format(
            rn.downstream, rn.upstream)
      pprint.item(rn.name, opt_text=mapping)
  return True


#def _print_remote(rn, verbose):
#  success = True
#  pprint.item(rn)
#  if verbose:
#    ret, info = remote_lib.info(rn)
#    if ret == remote_lib.REMOTE_UNREACHABLE:
#      pprint.item_info(
#          'Couldn\'t reach remote %s to get more info abou it' % rn)
#      pprint.item_info(
#           'make sure that you are still connected to the internet')
#      pprint.item_info(
#          'make sure that you still have permissions to access the remote')
#      success = False
#    elif ret == remote_lib.SUCCESS:
#      pprint.item_info(info)
#    else:
#      raise Exception('Unrecognized ret code %s' % ret)
#  return success


def _do_delete(delete_r):
  errors_found = False

  for r in delete_r:
    ret = remote_lib.rm(r)
    if ret == remote_lib.REMOTE_NOT_FOUND:
      pprint.err('Remote %s not found' % r)
      errors_found = True
    elif ret == remote_lib.SUCCESS:
      pprint.msg('Remote %s removed successfully' % r)
    else:
      raise Exception('Unrecognized ret code %s' % ret)

  return not errors_found

########NEW FILE########
__FILENAME__ = gl_resolve
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl resolve - Mark a file with conflicts as resolved."""


from . import file_cmd


parser = file_cmd.parser('mark files with conflicts as resolved', 'resolve')

########NEW FILE########
__FILENAME__ = gl_status
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl status - Show the status of files in the repo."""


from clint.textui import colored

from gitless.core import branch as branch_lib
from gitless.core import file as file_lib
from gitless.core import repo as repo_lib
from gitless.core import sync as sync_lib

from . import pprint


def parser(subparsers):
  """Adds the status parser to the given subparsers object."""
  status_parser = subparsers.add_parser(
      'status', help='show status of the repo')
  status_parser.set_defaults(func=main)


def main(_):
  curr_b = branch_lib.current()
  repo_dir = '/' + repo_lib.cwd()
  if not curr_b:
    pprint.msg('Repo-directory {0}'.format(colored.green(repo_dir)))
  else:
    pprint.msg(
      'On branch {0}, repo-directory {1}'.format(
          colored.green(curr_b), colored.green(repo_dir)))

  in_merge = sync_lib.merge_in_progress()
  in_rebase = sync_lib.rebase_in_progress()
  if in_merge:
    pprint.blank()
    _print_conflict_exp('merge')
  elif in_rebase:
    pprint.blank()
    _print_conflict_exp('rebase')

  tracked_mod_list = []
  untracked_list = []
  for f in file_lib.status_all(include_tracked_unmodified_fps=False):
    if f.type == file_lib.TRACKED and f.modified:
      tracked_mod_list.append(f)
    elif f.type == file_lib.UNTRACKED:
      untracked_list.append(f)
  pprint.blank()
  tracked_mod_list.sort(key=lambda f: f.fp)
  _print_tracked_mod_files(tracked_mod_list)
  pprint.blank()
  pprint.blank()
  untracked_list.sort(key=lambda f: f.fp)
  _print_untracked_files(untracked_list)
  return True


def _print_tracked_mod_files(tracked_mod_list):
  pprint.msg('Tracked files with modifications:')
  pprint.exp('these will be automatically considered for commit')
  pprint.exp(
      'use gl untrack <f> if you don\'t want to track changes to file f')
  pprint.exp(
      'if file f was committed before, use gl checkout <f> to discard '
      'local changes')
  pprint.blank()
  if not tracked_mod_list:
    pprint.item('There are no tracked files with modifications to list')
  else:
    for f in tracked_mod_list:
      exp = ''
      color = colored.yellow
      # TODO(sperezde): sometimes files don't appear here if they were resolved.
      if not f.exists_in_lr:
        exp = ' (new file)'
        color = colored.green
      elif not f.exists_in_wd:
        exp = ' (deleted)'
        color = colored.red
      elif f.in_conflict:
        exp = ' (with conflicts)'
        color = colored.cyan
      elif f.resolved:
        exp = ' (conflicts resolved)'
      pprint.item(color(f.fp), opt_text=exp)


def _print_untracked_files(untracked_list):
  pprint.msg('Untracked files:')
  pprint.exp('these won\'t be considered for commit')
  pprint.exp('use gl track <f> if you want to track changes to file f')
  pprint.blank()
  if not untracked_list:
    pprint.item('There are no untracked files to list')
  else:
    for f in untracked_list:
      s = ''
      color = colored.blue
      if f.exists_in_lr:
        color = colored.magenta
        if f.exists_in_wd:
          s = ' (exists in local repo)'
        else:
          s = ' (exists in local repo but not in working directory)'
      pprint.item(color(f.fp), opt_text=s)


def _print_conflict_exp(t):
  pprint.msg(
      'You are in the middle of a {0}; all conflicts must be resolved before '
      'commiting'.format(t))
  pprint.exp(
      'use gl {0} --abort to go back to the state before the {0}'.format(t))
  pprint.exp('use gl resolve <f> to mark file f as resolved')
  pprint.exp('once you solved all conflicts do gl commit to continue')
  pprint.blank()

########NEW FILE########
__FILENAME__ = gl_track
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl track - Start tracking changes to files."""


from . import file_cmd


parser = file_cmd.parser('start tracking changes to files', 'track')

########NEW FILE########
__FILENAME__ = gl_untrack
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""gl untrack - Stop tracking changes to files."""


from . import file_cmd


parser = file_cmd.parser('stop tracking changes to files', 'untrack')

########NEW FILE########
__FILENAME__ = pprint
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Module for pretty printing Gitless output."""


from clint.textui import puts

import re
import sys

from gitless.core import file as file_lib


SEP = (
    '##########################################################################'
    '######')

# Stdout.

def blank(p=sys.stdout.write):
  puts('#', stream=p)


def msg(text, p=sys.stdout.write):
  puts('# {0}'.format(text), stream=p)


def exp(text, p=sys.stdout.write):
  puts('#   ({0})'.format(text), stream=p)


def item(i, opt_text='', p=sys.stdout.write):
  puts('#     {0}{1}'.format(i, opt_text), stream=p)


def sep(p=sys.stdout.write):
  puts(SEP, stream=p)


# Err.

def err(text):
  msg(text, p=sys.stderr.write)


def err_exp(text):
  exp(text, p=sys.stderr.write)


def err_blank():
  blank(p=sys.stderr.write)


def err_item(i, opt_text='', p=sys.stderr.write):
  item(i, opt_text, p=sys.stderr.write)


# Misc.

def conf_dialog(text):
  """Gets confirmation from the user.

  Prints a confirmation message to stdout with the given text and waits for
  user confirmation.

  Args:
    text: the text to include in the confirmation.

  Returns:
    True if the user confirmed she wanted to continue or False if otherwise.
  """
  msg('{0}. Do you wish to continue? (y/N)'.format(text))
  user_input = get_user_input()
  return user_input and user_input[0].lower() == 'y'


def get_user_input(text='> '):
  """Python 2/3 compatible way of getting user input."""
  global input
  try:
    # Disable pylint's redefined-builtin warning and undefined-variable
    # (raw_input is undefined in python 3) error.
    # pylint: disable=W0622
    # pylint: disable=E0602
    input = raw_input
  except NameError:
    pass
  return input(text)


def dir_err_exp(fp, subcmd):
  """Prints the dir error exp to stderr."""
  err('{0} is a directory. Can\'t {1} a directory'.format(fp, subcmd))


def diff(processed_diff, max_line_digits, p=sys.stdout.write):
  """Uses line-by-line diff information to format lines nicely.

  Args:
    processed_diff: a list of LineData objects.
    max_line_digits: largest number of digits in a line number (for padding).
    p: a writer function (defaults to sys.stdout.write).

  Returns:
    a list of strings making up the formatted diff output.
  """

  def is_unchanged(status):
    """Check if a diff status code does not correspond to + or -.

    Args:
      status: status code of a line.

    Returns:
      True if status is file_lib.DIFF_SAME or file_lib.DIFF_INFO.
    """
    return status == file_lib.DIFF_SAME or status == file_lib.DIFF_INFO

  processed = []
  for index, line_data in enumerate(processed_diff):
    # check if line is a single line diff (do diff within line if so).
    # condition: The current line was ADDED to the file AND
    # the line after is non-existent or unchanged AND
    # the line before was removed from the file AND
    # the line two before is non-existent or unchanged.
    # In other words: bold if only one line was changed in this area.
    if (line_data.status == file_lib.DIFF_ADDED and
       (index == len(processed_diff) - 1 or
           is_unchanged(processed_diff[index + 1].status)) and
       (index - 1 >= 0 and
           processed_diff[index - 1].status == file_lib.DIFF_MINUS) and
       (index - 2 < 0 or is_unchanged(processed_diff[index - 2].status))):
      interest = _highlight(
          processed_diff[index - 1].line[1:], line_data.line[1:])
      if interest:
        # show changed line with bolded diff in both red and green.
        starts, ends = interest
        # first bold negative diff.
        processed[-1] = _format_line(
            processed_diff[index - 1], max_line_digits,
            bold_delim=(starts[0], ends[0]))
        processed += [_format_line(
            line_data, max_line_digits, bold_delim=(starts[1], ends[1]))]
      else:
        processed += [_format_line(line_data, max_line_digits)]
    else:
      processed += [_format_line(line_data, max_line_digits)]
  # TODO: print as we process.
  return p('\n'.join(processed) + '\n')


def _format_line(line_data, max_line_digits, bold_delim=None):
  """Format a standard diff line.

  Args:
    line_data: a namedtuple with the line info to be formatted.
    max_line_digits: maximum number of digits in a line number (for padding).
    bold_delim: optional arg indicate where to start/end bolding.

  Returns:
    a colored version of the diff line using ANSI control characters.
  """
  # Color constants.
  GREEN = '\033[32m'
  GREEN_BOLD = '\033[1;32m'
  RED = '\033[31m'
  RED_BOLD = '\033[1;31m'
  CLEAR = '\033[0m'

  line = line_data.line
  formatted = ''

  if line_data.status == file_lib.DIFF_SAME:
    formatted = (
        str(line_data.old_line_number).ljust(max_line_digits) +
        str(line_data.new_line_number).ljust(max_line_digits) + line)
  elif line_data.status == file_lib.DIFF_ADDED:
    formatted = (
        ' ' * max_line_digits + GREEN +
        str(line_data.new_line_number).ljust(max_line_digits))
    if not bold_delim:
      formatted += line
    else:
      bold_start, bold_end = bold_delim
      formatted += (
          line[:bold_start] + GREEN_BOLD + line[bold_start:bold_end] + CLEAR +
          GREEN + line[bold_end:])
  elif line_data.status == file_lib.DIFF_MINUS:
    formatted = (
        RED + str(line_data.old_line_number).ljust(max_line_digits) +
        ' ' * max_line_digits)
    if not bold_delim:
      formatted += line
    else:
      bold_start, bold_end = bold_delim
      formatted += (
          line[:bold_start] + RED_BOLD + line[bold_start:bold_end] +
          CLEAR + RED + line[bold_end:])
  elif line_data.status == file_lib.DIFF_INFO:
    formatted = CLEAR + '\n' + line

  return formatted + CLEAR


def _highlight(line1, line2):
  """Returns the sections that should be bolded in the given lines.

  Args:
    line1: a line from a diff output without the first status character.
    line2: see line1

  Returns:
    two tuples. The first tuple indicates the starts of where to bold
    and the second tuple indicated the ends.
   """
  start1 = start2 = 0
  match = re.search(r'\S', line1)  # ignore leading whitespace.
  if match:
    start1 = match.start()
  match = re.search(r'\S', line2)
  if match:
    start2 = match.start()
  length = min(len(line1), len(line2)) - 1
  bold_start1 = start1
  bold_start2 = start2
  while (bold_start1 <= length and bold_start2 <= length and
         line1[bold_start1] == line2[bold_start2]):
    bold_start1 += 1
    bold_start2 += 1
  match = re.search(r'\s*$', line1)  # ignore trailing whitespace.
  bold_end1 = match.start() - 1
  match = re.search(r'\s*$', line2)
  bold_end2 = match.start() - 1
  while (bold_end1 >= bold_start1 and bold_end2 >= bold_start2 and
         line1[bold_end1] == line2[bold_end2]):
    bold_end1 -= 1
    bold_end2 -= 1
  if bold_start1 - start1 > 0 or len(line1) - 1 - bold_end1 > 0:
    return (bold_start1 + 1, bold_start2 + 1), (bold_end1 + 2, bold_end2 + 2)
  return None

########NEW FILE########
__FILENAME__ = branch
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Gitless's branching lib."""


import collections
import os
import re

from gitpylib import branch as git_branch
from gitpylib import common as git_common
from gitpylib import file as git_file
from gitpylib import stash as git_stash
from gitpylib import status as git_status

from . import remote as remote_lib
from . import repo as repo_lib


BranchStatus = collections.namedtuple(
    'BranchStatus', ['name', 'is_current', 'upstream', 'upstream_exists'])

# Ret codes of methods.
SUCCESS = 1
REMOTE_NOT_FOUND = 2
INVALID_NAME = 3
BRANCH_ALREADY_EXISTS = 4
NONEXISTENT_BRANCH = 5
BRANCH_IS_CURRENT = 6
INVALID_DP = 7
UPSTREAM_NOT_SET = 8


def create(name, dp='HEAD'):
  """Creates a new branch with the given name.

  Args:
    name: the name of the branch to create.
    dp: divergent point. The commit from where to 'branch out.' (Defaults to
      HEAD.)

  Returns:
    INVALID_NAME, BRANCH_ALREADY_EXISTS, SUCCESS.
  """
  if not name.strip() or '/' in name or '_' in name:
    # Branches can't have a '/' so that we don't confuse them with remote
    # branches that can be specified in the form remote/branch.
    # Also, they can't have a '_' so that it doesn't conflict with our way of
    # naming internal files.
    return INVALID_NAME
  ret = git_branch.create(name, sp=dp)
  if ret == git_branch.INVALID_NAME:
    return INVALID_NAME
  elif ret == git_branch.BRANCH_ALREADY_EXISTS:
    return BRANCH_ALREADY_EXISTS
  elif ret == git_branch.SUCCESS:
    return SUCCESS
  elif ret == git_branch.INVALID_SP:
    return INVALID_DP
  else:
    raise Exception('Unrecognized ret code {0}'.format(ret))


def delete(name):
  """Deletes the branch with the given name.

  Args:
    name: the name of the branch to delete.

  Returns:
    NONEXISTENT_BRANCH or SUCCESS.
  """
  ret = git_branch.force_delete(name)
  if ret == git_branch.NONEXISTENT_BRANCH:
    return NONEXISTENT_BRANCH
  elif ret == SUCCESS:
    # We also cleanup any stash left.
    git_stash.drop(_stash_msg(name))
    return SUCCESS
  else:
    raise Exception('Unrecognized ret code {0}'.format(ret))


def set_upstream(upstream):
  """Sets the upstream branch of the current branch.

  Args:
    upstream: the upstream branch in the form remote/branch.

  Returns:
    REMOTE_NOT_FOUND or SUCCESS.
  """
  upstream_remote, upstream_branch = upstream.split('/')
  if not remote_lib.is_set(upstream_remote):
    return REMOTE_NOT_FOUND

  current_b = current()
  ret = git_branch.set_upstream(current_b, upstream)
  uf = _upstream_file(current_b, upstream_remote, upstream_branch)
  if os.path.exists(uf):
    os.remove(uf)
  if ret == git_branch.UNFETCHED_OBJECT:
    # We work around this, it could be the case that the user is trying to push
    # a new branch to the remote or it could be that the branch exists but it
    # hasn't been fetched yet.
    # TODO(sperezde): fix the fetch case.
    open(uf, 'a').close()
  return SUCCESS


def unset_upstream():
  """Unsets the upstream branch of the current branch."""
  current_b_name = current()
  current_b = status(current_b_name)
  ret = UPSTREAM_NOT_SET
  if current_b.upstream:
    ret = SUCCESS
    if current_b.upstream_exists:
      git_branch.unset_upstream(current_b_name)
    else:
      uf = _upstream_file(current_b_name, *current_b.upstream.split('/'))
      os.remove(uf)
  return ret


def switch(name):
  """Switches to the branch with the given name.

  Args:
    name: the name of the destination branch.

  Returns:
    BRANCH_IS_CURRENT or SUCCESS.
  """
  gl_dir = repo_lib.gl_dir()
  current_b = _current(gl_dir=gl_dir)
  if name == current_b:
    return BRANCH_IS_CURRENT
  # Stash doesn't save assumed unchanged files, so we save which files are
  # marked as assumed unchanged and unmark them. And when switching back we
  # look at this info and re-mark them.
  _unmark_au_files(current_b)
  git_stash.all(_stash_msg(current_b))
  git_branch.checkout(name)
  git_stash.pop(_stash_msg(name))
  _remark_au_files(name, gl_dir=gl_dir)
  return SUCCESS


def current():
  """Get the name of the current branch."""
  return _current()


def status(name):
  """Get the status of the branch with the given name.

  Args:
    name: the name of the branch to status.

  Returns:
    a named tuple (exists, is_current, upstream, upstream_exists) where exists,
    is_current and upstream_exists are boolean values and upstream is a string
    representing its upstream branch (in the form 'remote_name/remote_branch')
    or None if it has no upstream set.
  """
  exists, is_current, upstream = git_branch.status(name)
  if not exists:
    return None
  upstream_exists = True
  if not upstream:
    # We have to check if the branch has an unpushed upstream.
    upstream = _unpushed_upstream(name)
    upstream_exists = False

  return BranchStatus(name, is_current, upstream, upstream_exists)


def status_all():
  """Get the status of all existing branches.

  Returns:
    named tuples of the form (name, is_current, upstream, upstream_exists).
    upstream is in the format 'remote_name/remote_branch'.
  """
  rebase_in_progress = _rebase_in_progress()
  if rebase_in_progress:
    current_b = _rebase_branch()

  ret = []
  for name, is_current, upstream in git_branch.status_all():
    if name == '(no branch)':
      continue

    if rebase_in_progress and name == current_b:
      is_current = current_b

    upstream_exists = True
    if not upstream:
      # We check if the branch has an unpushed upstream
      upstream = _unpushed_upstream(name)
      upstream_exists = False

    ret.append(BranchStatus(name, is_current, upstream, upstream_exists))

  return ret


# Private methods.


def _current(gl_dir=None):
  """Get the name of the current branch.

  Args:
    gl_dir: the gl dir (optional arg for speeding up things).
  """
  gl_dir = repo_lib.gl_dir() if not gl_dir else gl_dir
  if _rebase_in_progress(gl_dir=gl_dir):
    # While in a rebase, Git actually moves to a "no-branch" status.
    # In Gitless, the user is in the branch being re-based.
    return _rebase_branch(gl_dir=gl_dir)
  return git_branch.current()


def _stash_msg(name):
  """Computes the stash msg to use for stashing changes in branch name."""
  return '---gl-{0}---'.format(name)


def _unpushed_upstream(name):
  """Returns the unpushed upstream or None."""
  for f in os.listdir(repo_lib.gl_dir()):
    result = re.match(r'GL_UPSTREAM_{0}_(\w+)_(\w+)'.format(name), f)
    if result:
      return '/'.join([result.group(1), result.group(2)])
  return None


def _upstream_file(branch, upstream_remote, upstream_branch):
  upstream_fn = 'GL_UPSTREAM_{0}_{1}_{2}'.format(
      branch, upstream_remote, upstream_branch)
  return os.path.join(repo_lib.gl_dir(), upstream_fn)


def _unmark_au_files(branch):
  """Saves the path of files marked as assumed unchanged and unmarks them.

  To re-mark all files again use _remark_au_files(branch).

  Args:
    branch: the info will be stored under this branch name.
  """
  assumed_unchanged_fps = git_status.au_files()
  if not assumed_unchanged_fps:
    return

  gl_dir = repo_lib.gl_dir()
  repo_dir = git_common.repo_dir()
  with open(os.path.join(gl_dir, 'GL_AU_{0}'.format(branch)), 'w') as f:
    for fp in assumed_unchanged_fps:
      f.write(fp + '\n')
      git_file.not_assume_unchanged(os.path.join(repo_dir, fp))


def _remark_au_files(branch, gl_dir=None):
  """Re-marks files as assumed unchanged.

  Args:
    branch: the branch name under which the info is stored.
    gl_dir: the gl dir (optional arg for speeding up things).
  """
  gl_dir = repo_lib.gl_dir() if not gl_dir else gl_dir
  au_info_fp = os.path.join(gl_dir, 'GL_AU_{0}'.format(branch))
  if not os.path.exists(au_info_fp):
    return

  repo_dir = git_common.repo_dir()
  with open(au_info_fp, 'r') as f:
    for fp in f:
      fp = fp.strip()
      git_file.assume_unchanged(os.path.join(repo_dir, fp))

  os.remove(au_info_fp)


# Temporal hack until we refactor the sync module.
def _rebase_in_progress(gl_dir=None):
  return os.path.exists(_rebase_file(gl_dir=gl_dir))


def _rebase_branch(gl_dir=None):
  """Gets the name of the current branch being rebased."""
  rf = open(_rebase_file(gl_dir=gl_dir), 'r')
  return rf.readline().strip()


def _rebase_file(gl_dir=None):
  gl_dir = repo_lib.gl_dir() if not gl_dir else gl_dir
  return os.path.join(gl_dir, 'GL_REBASE')

########NEW FILE########
__FILENAME__ = file
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Gitless's file lib."""


import collections
import os

from gitpylib import common as git_common
from gitpylib import file as git_file
from gitpylib import status as git_status

from . import repo as repo_lib
from . import branch as branch_lib


# Ret codes of methods.
SUCCESS = 1
FILE_NOT_FOUND = 2
FILE_ALREADY_TRACKED = 3
FILE_ALREADY_UNTRACKED = 4
FILE_IS_UNTRACKED = 5
FILE_NOT_FOUND_AT_CP = 6
FILE_IN_CONFLICT = 7
FILE_IS_IGNORED = 8
FILE_NOT_IN_CONFLICT = 9
FILE_ALREADY_RESOLVED = 10
FILE_IS_DIR = 11

# Possible Gitless's file types.
TRACKED = 12
UNTRACKED = 13
IGNORED = 14

# Possible diff output lines.
DIFF_INFO = git_file.DIFF_INFO  # line carrying diff info for new hunk.
DIFF_SAME = git_file.DIFF_SAME  # line that git diff includes for context.
DIFF_ADDED = git_file.DIFF_ADDED
DIFF_MINUS = git_file.DIFF_MINUS


def track(fp):
  """Start tracking changes to fp.

  Args:
    fp: the file path of the file to track.

  Returns:
    FILE_NOT_FOUND, FILE_IS_DIR, FILE_ALREADY_TRACKED, FILE_IN_CONFLICT,
    FILE_IS_IGNORED or SUCCESS.
  """
  if os.path.isdir(fp):
    return FILE_IS_DIR
  gl_st, git_s = _status(fp)
  if not gl_st:
    return FILE_NOT_FOUND
  elif gl_st.type == TRACKED:
    return FILE_ALREADY_TRACKED
  elif gl_st.type == IGNORED:
    return FILE_IS_IGNORED

  # If we reached this point we know that the file to track is a untracked
  # file. This means that in the Git world, the file could be either:
  #   (i)  a new file for Git => add the file.
  #   (ii) an assumed unchanged file => unmark it.
  if git_s == git_status.UNTRACKED:
    # Case (i).
    git_file.stage(fp)
  elif (git_s == git_status.ASSUME_UNCHANGED or
        git_s == git_status.DELETED_ASSUME_UNCHANGED):
    # Case (ii).
    git_file.not_assume_unchanged(fp)
  else:
    raise Exception('File {0} in unkown status {1}'.format(fp, git_s))

  return SUCCESS


def untrack(fp):
  """Stop tracking changes to fp.

  Args:
    fp: the file path of the file to untrack.

  Returns:
    FILE_NOT_FOUND, FILE_IS_DIR, FILE_ALREADY_UNTRACKED, FILE_IN_CONFLICT,
    FILE_IS_IGNORED or SUCCESS.
  """
  if os.path.isdir(fp):
    return FILE_IS_DIR
  gl_st, git_s = _status(fp)
  if not gl_st:
    return FILE_NOT_FOUND
  elif gl_st.type == IGNORED:
    return FILE_IS_IGNORED
  elif gl_st.type == UNTRACKED:
    return FILE_ALREADY_UNTRACKED

  # If we reached this point we know that the file to untrack is a tracked
  # file. This means that in the Git world, the file could be either:
  #   (i)  a new file for Git that is staged (the user executed gl track on a
  #        uncomitted file) => reset changes;
  #   (ii) the file is a previously committed file => mark it as assumed
  #        unchanged.
  if git_s == git_status.STAGED:
    # Case (i).
    git_file.unstage(fp)
  elif (git_s == git_status.TRACKED_UNMODIFIED or
        git_s == git_status.TRACKED_MODIFIED or
        git_s == git_status.DELETED):
    # Case (ii).
    git_file.assume_unchanged(fp)
  elif git_s == git_status.IN_CONFLICT:
    return FILE_IN_CONFLICT
  else:
    raise Exception('File {0} in unkown status {1}'.format(fp, git_s))

  return SUCCESS


def diff(fp):
  """Compute the diff of the given file with its last committed version.

  Args:
    fp: the file path of the file to diff.

  Returns:
    a pair (result, out) where result is one of FILE_NOT_FOUND,
    FILE_IS_UNTRACKED, FILE_IS_DIR or SUCCESS and out is the output of the diff
    command in a machine-friendly way: it's a tuple of the form
    (list of namedtuples with fields 'line', 'status', 'old_line_number',
     'new_line_number', line number padding, additions, deletions).
  """
  nil_out = (None, None, None, None)
  if os.path.isdir(fp):
    return (FILE_IS_DIR, nil_out)
  gl_st, git_s = _status(fp)
  if not gl_st:
    return (FILE_NOT_FOUND, nil_out)
  elif gl_st.type == UNTRACKED:
    return (FILE_IS_UNTRACKED, nil_out)
  elif gl_st.type == IGNORED:
    return (FILE_IS_IGNORED, nil_out)

  do_staged_diff = False
  if git_s == git_status.STAGED:
    do_staged_diff = True
  elif (git_s == git_status.ADDED_MODIFIED or
        git_s == git_status.MODIFIED_MODIFIED):
    git_file.stage(fp)
    do_staged_diff = True

  # Don't include the `git diff` header.
  return (SUCCESS, git_file.diff(fp, staged=do_staged_diff)[:-1])


def checkout(fp, cp='HEAD'):
  """Checkouts file fp at cp.

  Args:
    fp: the filepath to checkout.
    cp: the commit point at which to checkout the file (defaults to HEAD).

  Returns:
    a pair (status, out) where status is one of FILE_IS_DIR,
    FILE_NOT_FOUND_AT_CP or SUCCESS and out is the content of fp at cp.
  """
  if os.path.isdir(fp):
    return (FILE_IS_DIR, None)
  # "show" expects the full path with respect to the repo root.
  rel_fp = os.path.join(repo_lib.cwd(), fp)[1:]
  ret, out = git_file.show(rel_fp, cp)

  if ret == git_file.FILE_NOT_FOUND_AT_CP:
    return (FILE_NOT_FOUND_AT_CP, None)

  s = git_status.of_file(fp)
  unstaged = False
  if s == git_status.STAGED:
    git_file.unstage(fp)
    unstaged = True

  with open(fp, 'w') as dst:
    dst.write(out)

  if unstaged:
    git_file.stage(fp)

  return (SUCCESS, out)


def status(fp):
  """Gets the status of fp.

  Args:
    fp: the file to status.

  Returns:
    None (if the file wasn't found) or a named tuple (fp, type, exists_in_lr,
    exists_in_wd, modified, in_conflict, resolved) where fp is a file path, type
    is one of TRACKED, UNTRACKED or IGNORED and all the remaining fields are
    booleans. The modified field is True if the working version of the file
    differs from its committed version. (If there's no committed version,
    modified is set to True.)
  """
  return _status(fp)[0]


def status_all(include_tracked_unmodified_fps=True):
  """Gets the status of all files relative to the cwd.

  Args:
    include_tracked_unmodified_fps: if True, files that are tracked but
      unmodified will be also reported. Setting it to False improves performance
      significantly if the repo is big. (Defaults to True.)

  Returns:
    a list of named tuples (fp, type, exists_in_lr, exists_in_wd, modified,
    in_conflict, resolved) where fp is a file path, type is one of TRACKED,
    UNTRACKED or IGNORED and all the remaining fields are booleans. The
    modified field is True if the working version of the file differs from its
    committed version. (If there's no committed version, modified is set to
    True.)
  """
  for (s, fp) in git_status.of_repo(
      include_tracked_unmodified_fps=include_tracked_unmodified_fps):
    f_st = _build_f_st(s, fp)
    if f_st:
      yield f_st


def resolve(fp):
  """Marks the given file in conflict as resolved.

  Args:
    fp: the file to mark as resolved.

  Returns:
    FILE_NOT_FOUND, FILE_NOT_IN_CONFLICT, FILE_ALREADY_RESOLVED or SUCCESS.
  """
  if os.path.isdir(fp):
    return FILE_IS_DIR
  f_st = status(fp)
  if not f_st:
    return FILE_NOT_FOUND
  if f_st.resolved:
    return FILE_ALREADY_RESOLVED
  if not f_st.in_conflict:
    return FILE_NOT_IN_CONFLICT

  # We don't use Git to keep track of resolved files, but just to make it feel
  # like doing a resolve in Gitless is similar to doing a resolve in Git
  # (i.e., add) we stage the file.
  git_file.stage(fp)
  # We add a file in the Gitless directory to be able to tell when a file has
  # been marked as resolved.
  # TODO(sperezde): might be easier to just find a way to tell if the file is
  # in the index.
  open(_resolved_file(fp), 'w').close()
  return SUCCESS


def internal_resolved_cleanup():
  for f in os.listdir(repo_lib.gl_dir()):
    if f.startswith('GL_RESOLVED'):
      os.remove(os.path.join(repo_lib.gl_dir(), f))
      #print 'removed %s' % f


# Private methods.


def _status(fp):
  """Get the status of the given fp.

  Returns:
    a tuple (gl_status, git_status) where gl_status is a FileStatus namedtuple
    representing the status of the file (or None if the file doesn't exist) and
    git_status is one of git's possible status for the file.
  """
  git_s = git_status.of_file(fp)
  if git_s == git_status.FILE_NOT_FOUND:
    return (None, git_s)
  gl_s = _build_f_st(git_s, fp)
  if not gl_s:
    return (None, git_s)
  return (gl_s, git_s)


# This namedtuple is only used in _build_f_st, but putting it as a module var
# instead of inside the function significantly improves performance (makes a
# difference when the repo is big).
FileStatus = collections.namedtuple(
    'FileStatus', [
        'fp', 'type', 'exists_in_lr', 'exists_in_wd', 'modified',
        'in_conflict', 'resolved'])


def _build_f_st(s, fp):
  # TODO(sperezde): refactor this.
  # Temporarily disable pylint's too-many-branches warning.
  # pylint: disable=R0912
  ret = None
  if s == git_status.UNTRACKED:
    ret = FileStatus(fp, UNTRACKED, False, True, True, False, False)
  elif s == git_status.TRACKED_UNMODIFIED:
    ret = FileStatus(fp, TRACKED, True, True, False, False, False)
  elif s == git_status.TRACKED_MODIFIED:
    ret = FileStatus(fp, TRACKED, True, True, True, False, False)
  elif s == git_status.STAGED:
    # A file could have been "gl track"ed and later ignored by adding a matching
    # pattern in a .gitignore file. We consider this kind of file to still be a
    # tracked file. This is consistent with the idea that tracked files can't
    # be ignored.
    # TODO(sperezde): address the following rough edge: the user could untrack
    # a tracked file (one that was not committed before) and if it's matched by
    # a .gitignore file it will be ignored. The same thing won't happen if an
    # already committed file is untracked (due to how Gitless keeps track of
    # these kind of files).

    # Staged files don't exist in the lr for Gitless.
    ret = FileStatus(fp, TRACKED, False, True, True, False, False)
  elif s == git_status.ASSUME_UNCHANGED:
    # TODO(sperezde): detect whether it is modified or not?
    ret = FileStatus(fp, UNTRACKED, True, True, True, False, False)
  elif s == git_status.DELETED:
    ret = FileStatus(fp, TRACKED, True, False, True, False, False)
  elif s == git_status.DELETED_STAGED:
    # This can only happen if the user did a rm of a new file. The file doesn't
    # exist as far as Gitless is concerned.
    git_file.unstage(fp)
    ret = None
  elif s == git_status.DELETED_ASSUME_UNCHANGED:
    ret = None
  elif s == git_status.IN_CONFLICT:
    wr = _was_resolved(fp)
    ret = FileStatus(fp, TRACKED, True, True, True, not wr, wr)
  elif s == git_status.IGNORED:
    ret = FileStatus(fp, IGNORED, False, True, True, True, False)
  elif s == git_status.MODIFIED_MODIFIED:
    # The file was marked as resolved and then modified. To Gitless, this is
    # just a regular tracked file.
    ret = FileStatus(fp, TRACKED, True, True, True, False, True)
  elif s == git_status.ADDED_MODIFIED:
    # The file is a new file that was added and then modified. This can only
    # happen if the user gl tracks a file and then modifies it.
    ret = FileStatus(fp, TRACKED, False, True, True, False, False)
  else:
    raise Exception('Unrecognized status {0}'.format(s))
  return ret


def _was_resolved(fp):
  """Returns True if the given file had conflicts and was marked as resolved."""
  return os.path.exists(_resolved_file(fp))


def _resolved_file(fp):
  fp = os.path.relpath(os.path.abspath(fp), git_common.repo_dir())
  fp = fp.replace(os.path.sep, '-')  # this hack will do the trick for now.
  return os.path.join(
      repo_lib.gl_dir(), 'GL_RESOLVED_{0}_{1}'.format(branch_lib.current(), fp))

########NEW FILE########
__FILENAME__ = init
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Gitless's init lib."""


from . import branch as branch_lib
from . import repo as repo_lib

from gitpylib import repo as git_repo
from gitpylib import remote as git_remote


# Ret codes of methods.
SUCCESS = 1
NOTHING_TO_INIT = 2
REPO_UNREACHABLE = 3


def init_from(remote_repo):
  """Clones the remote_repo into the cwd."""
  if repo_lib.gl_dir():
    return NOTHING_TO_INIT
  if not git_repo.clone(remote_repo):
    return REPO_UNREACHABLE
  # We get all remote branches as well and create local equivalents.
  for remote_branch in git_remote.branches('origin'):
    if remote_branch == 'master':
      continue
    s = branch_lib.create(remote_branch, 'origin/{0}'.format(remote_branch))
    if s != SUCCESS:
      raise Exception(
          'Unexpected status code {0} when creating local branch {1}'.format(
              s, remote_branch))
  return SUCCESS


def init_cwd():
  """Makes the cwd a Gitless's repository."""
  if repo_lib.gl_dir():
    return NOTHING_TO_INIT
  git_repo.init()
  return SUCCESS

########NEW FILE########
__FILENAME__ = remote
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Gitless's remote lib."""


import collections

from gitpylib import remote as git_remote


# Ret codes of functions.
SUCCESS = 1
REMOTE_NOT_FOUND = 2
REMOTE_ALREADY_SET = 3
REMOTE_NOT_FOUND = 4
REMOTE_UNREACHABLE = 5
INVALID_NAME = 6


def add(remote_name, remote_url):
  """Add a remote.

  Args:
    remote_name: the name of the remote.
    remote_url: the url of the remote

  Returns:
    REMOTE_ALREADY_SET, REMOTE_UNREACHABLE or SUCCESS.
  """
  if '/' in remote_name:
    return INVALID_NAME
  if is_set(remote_name):
    return REMOTE_ALREADY_SET
  s = git_remote.add(remote_name, remote_url)
  if s == git_remote.REMOTE_UNREACHABLE:
    return REMOTE_UNREACHABLE
  elif s == git_remote.SUCCESS:
    return SUCCESS
  else:
    raise Exception('Unrecognized ret code {0}'.format(s))


def info(remote_name):
  ret, remote_info = git_remote.show(remote_name)
  if ret == git_remote.REMOTE_NOT_FOUND:
    return (REMOTE_NOT_FOUND, None)
  elif ret == git_remote.REMOTE_UNREACHABLE:
    return (REMOTE_UNREACHABLE, None)
  elif ret == git_remote.SUCCESS:
    return (SUCCESS, remote_info)


RemoteInfo = collections.namedtuple(
    'RemoteInfo', ['name', 'downstream', 'upstream'])


def info_all():
  for ri in git_remote.show_all_v():
    yield RemoteInfo(ri.name, ri.fetch, ri.push)


def rm(remote_name):
  if not is_set(remote_name):
    return REMOTE_NOT_FOUND
  git_remote.rm(remote_name)
  return SUCCESS


def is_set(remote_name):
  return remote_name in git_remote.show_all()

########NEW FILE########
__FILENAME__ = repo
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Gitless's repo lib."""


import os

from gitpylib import common as git_common
from gitpylib import config as git_config
from gitpylib import log as git_log


def cwd():
  """Gets the Gitless's cwd."""
  dr = os.path.dirname(gl_dir())
  cwd = os.getcwd()
  return '/' if dr == cwd else cwd[len(dr):]


def gl_dir():
  """Gets the path to the gl directory.

  Returns:
    the absolute path to the gl directory or None if the current working
    directory is not a Gitless repository.
  """
  # We use the same .git directory.
  return git_common.git_dir()


def editor():
  """Returns the editor set up by the user (defaults to Vim)."""
  ret = git_config.get('core.editor')
  if ret:
    return ret
  # We check the $EDITOR variable.
  ret = os.environ['EDITOR'] if 'EDITOR' in os.environ else None
  if ret:
    return ret
  # We default to Vim.
  return 'vim'


def color_output():
  ret = git_config.get('color.ui')
  if ret and ret.lower() in ['true', 'always']:
    return True
  return False


def history(include_diffs=False):
  return git_log.log(include_diffs=include_diffs)

########NEW FILE########
__FILENAME__ = sync
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Gitless's sync lib."""


import itertools
import os

from gitpylib import apply as git_apply
from gitpylib import file as git_file
from gitpylib import hook as git_hook
from gitpylib import status as git_status
from gitpylib import sync as git_sync
from gitpylib import remote as git_remote

from . import branch as branch_lib
from . import file as file_lib
from . import remote as remote_lib
from . import repo as repo_lib


# Ret codes of methods.
SUCCESS = 1
LOCAL_CHANGES_WOULD_BE_LOST = 2
SRC_NOT_FOUND = 3
SRC_IS_CURRENT_BRANCH = 4
NOTHING_TO_MERGE = 5
FILE_NOT_FOUND = 6
MERGE_NOT_IN_PROGRESS = 8
CONFLICT = 9
REBASE_NOT_IN_PROGRESS = 10
NOTHING_TO_REBASE = 11
UPSTREAM_NOT_SET = 12
NOTHING_TO_PUSH = 13
REMOTE_NOT_FOUND = 14
REMOTE_UNREACHABLE = 15
REMOTE_BRANCH_NOT_FOUND = 16
PUSH_FAIL = 17
UNRESOLVED_CONFLICTS = 19
RESOLVED_FILES_NOT_IN_COMMIT = 20
PRE_COMMIT_FAILED = 21


def merge(src):
  """Merges changes in the src branch into the current branch.

  Args:
    src: the source branch to pick up changes from.
  """
  is_remote_b = _is_remote_branch(src)
  is_valid, error = (
      _valid_remote_branch(src)
      if is_remote_b else _valid_branch(src))
  if not is_valid:
    return (error, None)

  if is_remote_b:
    remote, remote_b = _parse_from_remote_branch(src)
    ret, out = git_sync.pull_merge(remote, remote_b)
  else:
    ret, out = git_sync.merge(src)

  if ret == git_sync.SUCCESS:
    return (SUCCESS, out)
  elif ret == git_sync.CONFLICT:
    return (CONFLICT, out)
  elif ret == git_sync.LOCAL_CHANGES_WOULD_BE_LOST:
    return (LOCAL_CHANGES_WOULD_BE_LOST, out)
  elif ret == git_sync.NOTHING_TO_MERGE:
    return (NOTHING_TO_MERGE, out)
  raise Exception('Unexpected ret code {0}'.format(ret))


def merge_in_progress():
  return git_sync.merge_in_progress()


def abort_merge():
  if not merge_in_progress():
    return MERGE_NOT_IN_PROGRESS
  git_sync.abort_merge()
  file_lib.internal_resolved_cleanup()
  return SUCCESS


def rebase(new_base):
  is_remote_b = _is_remote_branch(new_base)
  is_valid, error = (
      _valid_remote_branch(new_base)
      if is_remote_b else _valid_branch(new_base))
  if not is_valid:
    return (error, None)

  current = branch_lib.current()
  if is_remote_b:
    remote, remote_b = _parse_from_remote_branch(new_base)
    ret, out = git_sync.pull_rebase(remote, remote_b)
  else:
    ret, out = git_sync.rebase(new_base)
  if ret == git_sync.SUCCESS:
    return (SUCCESS, out)
  elif ret == git_sync.LOCAL_CHANGES_WOULD_BE_LOST:
    return (LOCAL_CHANGES_WOULD_BE_LOST, out)
  elif ret == git_sync.CONFLICT:
    # We write a file to note the current branch being rebased and the new base.
    _write_rebase_file(current, new_base)
    return (CONFLICT, out)
  elif ret == git_sync.NOTHING_TO_REBASE:
    return (NOTHING_TO_REBASE, out)
  raise Exception('Unexpected ret code {0}'.format(ret))


def rebase_in_progress():
  return os.path.exists(os.path.join(repo_lib.gl_dir(), 'GL_REBASE'))


def abort_rebase():
  if not rebase_in_progress():
    return REBASE_NOT_IN_PROGRESS
  git_sync.abort_rebase()
  conclude_rebase()
  return SUCCESS


def rebase_info():
  """Gets the name of the current branch being rebased and the new base."""
  rf = open(_rebase_file(), 'r')
  current = rf.readline().strip()
  new_base = rf.readline().strip()
  return (current, new_base)


def skip_rebase_commit():
  if not rebase_in_progress():
    return REBASE_NOT_IN_PROGRESS
  s = git_sync.skip_rebase_commit()
  if s[0] == git_sync.SUCCESS:
    conclude_rebase()
    return (SUCCESS, s[1])
  elif s[0] == git_sync.CONFLICT:
    return (SUCCESS, s[1])
  else:
    raise Exception('Unexpected ret code {0}'.format(s[0]))


def conclude_rebase():
  file_lib.internal_resolved_cleanup()
  os.remove(_rebase_file())


def publish():
  """Publish local commits to the upstream branch."""
  current_b = branch_lib.current()
  b_st = branch_lib.status(current_b)
  if not b_st.upstream:
    return (UPSTREAM_NOT_SET, None)
  ret, out = git_sync.push(current_b, *b_st.upstream.split('/'))
  if ret == git_sync.SUCCESS:
    if not b_st.upstream_exists:
      # After the push the upstream exists. So we set it.
      branch_lib.set_upstream(b_st.upstream)
    return (SUCCESS, out)
  elif ret == git_sync.NOTHING_TO_PUSH:
    return (NOTHING_TO_PUSH, None)
  elif ret == git_sync.PUSH_FAIL:
    return (PUSH_FAIL, None)
  else:
    raise Exception('Unexpected ret code {0}'.format(ret))


def partial_commit(files):
  return PartialCommit(files)

class PartialCommit(object):

  def __init__(self, files):
    self.__files = files
    self.__pf = open(os.path.join(repo_lib.gl_dir(), 'GL_PARTIAL_CI'), 'w+')

  def __iter__(self):
    for fp in self.__files:
      yield self.ChunkedFile(fp, self.__pf)

  def commit(self, msg, skip_checks=False):
    def has_staged_version(fp):
      return git_status.of_file(fp) in [
          git_status.STAGED, git_status.MODIFIED_MODIFIED,
          git_status.ADDED_MODIFIED]

    self.__pf.close()
    git_apply.on_index(self.__pf.name)
    for fp in self.__files:
      if not has_staged_version(fp):
        # Partial commit includes all changes to file.
        git_file.stage(fp)
    out = git_sync.commit(
        None, msg, skip_checks=skip_checks, include_staged_files=True)
    return SUCCESS, out

  class ChunkedFile(object):

    def __init__(self, fp, pf):
      self.fp = fp
      self.__pf = pf
      self.__diff, self.__padding, _, _, self.__diff_header = git_file.diff(fp)
      if not self.__diff:
        raise Exception('There\'s nothing to (partially) commit')
      self.__diff_len = len(self.__diff)
      self.__header_printed = False
      self.__curr_index = 0
      self.__curr_chunk = None

    def __iter__(self):
      return self

    # Py 2/3 compatibility.
    def __next__(self):
      return self.next()

    def next(self):
      if self.__curr_index >= self.__diff_len:
        raise StopIteration
      self.__curr_chunk = [self.__diff[self.__curr_index]]
      self.__curr_chunk.extend(
          itertools.takewhile(
            lambda ld: ld.status != git_file.DIFF_INFO,
            itertools.islice(self.__diff, self.__curr_index + 1, None)))
      self.__curr_index += len(self.__curr_chunk)
      return self

    @property
    def diff(self):
      return self.__curr_chunk, self.__padding

    def include(self):
      if not self.__header_printed:
        self.__pf.write('\n'.join(self.__diff_header) + '\n')
      for line, _, _, _ in self.__curr_chunk:
        self.__pf.write(line + '\n')


def commit(files, msg, skip_checks=False):
  """Record changes in the local repository.

  Args:
    files: the files to commit.
    msg: the commit message.
    skip_checks: True if the pre-commit checks should be skipped (defaults to
      False).

  Returns:
    a pair (status, out) where status can be:
    - UNRESOLVED_CONFLICTS -> out is the list of unresolved files.
    - PRE_COMMIT_FAILED -> out is the output from the pre-commit hook.
    - SUCCESS -> out is the output of the commit command.
  """
  in_rebase = rebase_in_progress()
  in_merge = merge_in_progress()
  if in_rebase or in_merge:
    # If we are doing a merge then we can't do a partial commit (Git won't let
    # us do it). We can do commit -i which will stage all the files but we need
    # to watch out for not commiting new Gitless's tracked files that are not in
    # the list.
    # To do this, we temporarily unstage these files and then re-stage them
    # after the commit.
    # TODO(sperezde): actually implement what the comment above says ;)
    # TODO(sperezde): also need to do something with deletions?
    unresolved = []
    resolved = []
    for f in file_lib.status_all():
      if f.in_conflict:
        unresolved.append(f)
      elif f.resolved:
        resolved.append(f)

    if unresolved:
      return (UNRESOLVED_CONFLICTS, unresolved)
    # We know that there are no pending conflicts to be resolved.
    # Let's check that all resolved files are in the commit.
    resolved_not_in_ci = [f for f in resolved if f.fp not in files]
    if resolved_not_in_ci:
      return (RESOLVED_FILES_NOT_IN_COMMIT, resolved_not_in_ci)

    # print 'commiting files %s' % files
    out = None
    if in_rebase:
      # TODO(sperezde): save the message to use it later.
      for f in files:
        git_file.stage(f)
      file_lib.internal_resolved_cleanup()
      if not skip_checks:
        pc = git_hook.pre_commit()
        if not pc.ok:
          return (PRE_COMMIT_FAILED, pc.err)
      s = git_sync.rebase_continue()
      if s[0] == SUCCESS:
        conclude_rebase()
        return (SUCCESS, s[1])
      elif s[0] == CONFLICT:
        # TODO(sperezde): the next apply could actually result in another
        # conflict.
        return (SUCCESS, s[1])
      else:
        raise Exception('Unexpected ret code {0}'.format(s[0]))

    # It's a merge.
    if not skip_checks:
      pc = git_hook.pre_commit()
      if not pc.ok:
        return (PRE_COMMIT_FAILED, pc.err)
    out = git_sync.commit(
        files, msg, skip_checks=True, include_staged_files=True)
    file_lib.internal_resolved_cleanup()
    return (SUCCESS, out)

  # It's a regular commit.
  if not skip_checks:
    pc = git_hook.pre_commit()
    if not pc.ok:
      return (PRE_COMMIT_FAILED, pc.err)
  return (SUCCESS, git_sync.commit(files, msg, skip_checks=True))


# Private methods.


def _write_rebase_file(current, new_base):
  with open(_rebase_file(), 'w') as rf:
    rf.write(current + '\n')
    rf.write(new_base + '\n')


def _rebase_file():
  return os.path.join(repo_lib.gl_dir(), 'GL_REBASE')


def _valid_branch(b):
  b_st = branch_lib.status(b)
  if not b_st:
    return (False, SRC_NOT_FOUND)
  if b_st and b_st.is_current:
    return (False, SRC_IS_CURRENT_BRANCH)
  return (True, None)


def _valid_remote_branch(b):
  remote_n, remote_b = b.split('/')
  if not remote_lib.is_set(remote_n):
    return (False, REMOTE_NOT_FOUND)

  # We know the remote exists, let's see if the branch exists.
  exists, err = git_remote.head_exist(remote_n, remote_b)
  if not exists:
    if err == git_remote.REMOTE_UNREACHABLE:
      ret_err = REMOTE_UNREACHABLE
    else:
      ret_err = REMOTE_BRANCH_NOT_FOUND
    return (False, ret_err)

  return (True, None)


def _is_remote_branch(b):
  return '/' in b


def _parse_from_remote_branch(b):
  return b.split('/')

########NEW FILE########
__FILENAME__ = common
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Common methods used in unit tests."""


from functools import wraps
import os

import gitless.core.file as file_lib
import gitless.tests.utils as utils_lib


class TestCore(utils_lib.TestBase):
  """Base class for core tests."""

  def setUp(self):
    super(TestCore, self).setUp('gl-core-test')
    utils_lib.git_call('init')
    utils_lib.set_test_config()


def stub(module, fake):
  """Stub the given module with the given fake.

  Each symbol in the module is overrwritten with its matching symbol
  in the fake.

  Args:
    module: the module to stub.
    fake: an instance of a class or dict used for stubbing.
  """
  return Stubber(module, fake)


class Stubber(object):

  def __init__(self, module, fake):
    self.__module = module
    self.__backup = {}
    if not isinstance(fake, dict):
      # We dictionarize (-- is that even a word?) the object.
      fake = dict(
          (n, getattr(fake, n)) for n in dir(fake) if not n.startswith('__'))

    for k, v in fake.items():
      try:
        self.__backup[k] = getattr(module, k)
      except AttributeError:
        pass
      setattr(module, k, v)

  def __enter__(self):
    pass

  def __exit__(self, t, value, traceback):
    for k, v in self.__backup.items():
      setattr(self.__module, k, v)


def assert_contents_unchanged(*fps):
  """Decorator that fails the test if the contents of the file fp changed.

  The method decorated should be a unit test.

  Usage:
    @common.assert_contents_unchanged('f1')
    def test_method_that_shouldnt_modify_f1(self):
      # do something here.
      # assert something here.

  Args:
    fps: the filepath(s) to assert.
  """
  return __assert_decorator('Contents', utils_lib.read_file, *fps)


def assert_status_unchanged(*fps):
  """Decorator that fails the test if the status of fp changed.

  The method decorated should be a unit test.

  Usage:
    @common.assert_status_unchanged('f1')
    def test_method_that_shouldnt_modify_f1_status(self):
      # do something here.
      # assert something here.

  Args:
    fps: the filepath(s) to assert.
  """
  return __assert_decorator('Status', file_lib.status, *fps)


def assert_no_side_effects(*fps):
  """Decorator that fails the test if the contents or status of fp changed.

  The method decorated should be a unit test.

  Usage:
    @common.assert_no_side_effects('f1')
    def test_method_that_shouldnt_affect_f1(self):
      # do something here.
      # assert something here.

  It is a shorthand of:
    @common.assert_status_unchanged('f1')
    @common.assert_contents_unchanged('f1')
    def test_method_that_shouldnt_affect_f1(self):
      # do something here.
      # assert something here.

  Args:
    fps: the filepath(s) to assert.
  """
  def decorator(f):
    @assert_contents_unchanged(*fps)
    @assert_status_unchanged(*fps)
    @wraps(f)
    def wrapper(*args, **kwargs):
      f(*args, **kwargs)
    return wrapper
  return decorator


# Private functions.


def __assert_decorator(msg, prop, *fps):
  def decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
      self = args[0]
      # We save up the cwd to chdir to it after the test has run so that the
      # the given fps still "work" even if the test changed the cwd.
      cwd_before = os.getcwd()
      before_list = [prop(fp) for fp in fps]
      f(*args, **kwargs)
      os.chdir(cwd_before)
      after_list = [prop(fp) for fp in fps]
      for fp, before, after in zip(fps, before_list, after_list):
        self.assertEqual(
            before, after,
            '{0} of file "{1}" changed: from "{2}" to "{3}"'.format(
                msg, fp, before, after))
    return wrapper
  return decorator

########NEW FILE########
__FILENAME__ = stubs
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Stubs."""


from gitpylib import remote as git_remote


class RemoteLib(object):

  SUCCESS = git_remote.SUCCESS
  REMOTE_NOT_FOUND = git_remote.REMOTE_NOT_FOUND

  def __init__(self):
    self.remotes = {}

  def add(self, remote_name, remote_url):
    self.remotes[remote_name] = remote_url
    return self.SUCCESS

  def show(self, remote_name):
    if remote_name not in self.remotes:
      return (self.REMOTE_NOT_FOUND, None)
    return (self.SUCCESS, 'info about {0}'.format(remote_name))

  def show_all(self):
    return list(self.remotes.keys())

  def show_all_v(self):
    ret = []
    for rn, ru in self.remotes.items():
      ret.append(git_remote.RemoteInfo(rn, ru, ru))
    return ret

  def rm(self, remote_name):
    del self.remotes[remote_name]

########NEW FILE########
__FILENAME__ = test_branch
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Unit tests for branch module."""


import os
import unittest

import gitless.core.file as file_lib
import gitless.core.branch as branch_lib
import gitless.core.remote as remote_lib
import gitless.tests.utils as utils_lib

from . import common
from . import stubs


TRACKED_FP = 'f1'
TRACKED_FP_CONTENTS_1 = 'f1-1'
TRACKED_FP_CONTENTS_2 = 'f1-2'
UNTRACKED_FP = 'f2'
UNTRACKED_FP_CONTENTS = 'f2'
IGNORED_FP = 'f3'
BRANCH = 'b1'


class TestBranch(common.TestCore):
  """Base class for branch tests."""

  def setUp(self):
    super(TestBranch, self).setUp()

    # Build up an interesting mock repo.
    utils_lib.write_file(TRACKED_FP, contents=TRACKED_FP_CONTENTS_1)
    utils_lib.git_call('add "{0}"'.format(TRACKED_FP))
    utils_lib.git_call('commit -m"1" "{0}"'.format(TRACKED_FP))
    utils_lib.write_file(TRACKED_FP, contents=TRACKED_FP_CONTENTS_2)
    utils_lib.git_call('commit -m"2" "{0}"'.format(TRACKED_FP))
    utils_lib.write_file(UNTRACKED_FP, contents=UNTRACKED_FP_CONTENTS)
    utils_lib.write_file('.gitignore', contents='{0}'.format(IGNORED_FP))
    utils_lib.write_file(IGNORED_FP)
    utils_lib.git_call('branch "{0}"'.format(BRANCH))


class TestCreate(TestBranch):

  def test_create_invalid_name(self):
    self.assertEqual(branch_lib.INVALID_NAME, branch_lib.create('evil/branch'))
    self.assertEqual(branch_lib.INVALID_NAME, branch_lib.create('evil_branch'))
    self.assertEqual(branch_lib.INVALID_NAME, branch_lib.create(''))
    self.assertEqual(branch_lib.INVALID_NAME, branch_lib.create('\t'))
    self.assertEqual(branch_lib.INVALID_NAME, branch_lib.create('   '))

  def test_create_existent_name(self):
    self.assertEqual(branch_lib.SUCCESS, branch_lib.create('branch1'))
    self.assertEqual(
        branch_lib.BRANCH_ALREADY_EXISTS, branch_lib.create('branch1'))

  def test_create(self):
    self.assertEqual(branch_lib.SUCCESS, branch_lib.create('branch1'))
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch('branch1'))
    self.assertTrue(os.path.exists(TRACKED_FP))
    self.assertEqual(TRACKED_FP_CONTENTS_2, utils_lib.read_file(TRACKED_FP))
    self.assertFalse(os.path.exists(UNTRACKED_FP))
    self.assertFalse(os.path.exists(IGNORED_FP))
    self.assertFalse(os.path.exists('.gitignore'))

  def test_create_from_prev_commit(self):
    self.assertEqual(
        branch_lib.SUCCESS, branch_lib.create('branch1', dp='HEAD^'))
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch('branch1'))
    self.assertTrue(os.path.exists(TRACKED_FP))
    self.assertEqual(TRACKED_FP_CONTENTS_1, utils_lib.read_file(TRACKED_FP))
    self.assertFalse(os.path.exists(UNTRACKED_FP))
    self.assertFalse(os.path.exists(IGNORED_FP))
    self.assertFalse(os.path.exists('.gitignore'))


class TestDelete(TestBranch):

  def test_delete_nonexistent_branch(self):
    self.assertEqual(
        branch_lib.NONEXISTENT_BRANCH, branch_lib.delete('nonexistent'))

  def test_delete(self):
    self.assertEqual(
        branch_lib.SUCCESS, branch_lib.delete(BRANCH))


class TestSwitch(TestBranch):

  def test_switch_contents_still_there_untrack_tracked(self):
    file_lib.untrack(TRACKED_FP)
    utils_lib.write_file(TRACKED_FP, contents='contents')
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    self.assertEqual(TRACKED_FP_CONTENTS_2, utils_lib.read_file(TRACKED_FP))
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch('master'))
    self.assertEqual('contents', utils_lib.read_file(TRACKED_FP))

  def test_switch_contents_still_there_untracked(self):
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    utils_lib.write_file(UNTRACKED_FP, contents='contents')
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch('master'))
    self.assertEqual(UNTRACKED_FP_CONTENTS, utils_lib.read_file(UNTRACKED_FP))
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    self.assertEqual('contents', utils_lib.read_file(UNTRACKED_FP))

  def test_switch_contents_still_there_ignored(self):
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    utils_lib.write_file(IGNORED_FP, contents='contents')
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch('master'))
    self.assertEqual(IGNORED_FP, utils_lib.read_file(IGNORED_FP))
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    self.assertEqual('contents', utils_lib.read_file(IGNORED_FP))

  def test_switch_contents_still_there_tracked_commit(self):
    utils_lib.write_file(TRACKED_FP, contents='commit')
    utils_lib.git_call('commit -m\'comment\' {0}'.format(TRACKED_FP))
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    self.assertEqual(TRACKED_FP_CONTENTS_2, utils_lib.read_file(TRACKED_FP))
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch('master'))
    self.assertEqual('commit', utils_lib.read_file(TRACKED_FP))

  def test_switch_file_classification_is_mantained(self):
    file_lib.untrack(TRACKED_FP)
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.TRACKED, st.type)
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch('master'))
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.UNTRACKED, st.type)

  def test_switch_with_hidden_files(self):
    hf = '.file'
    utils_lib.write_file(hf)
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    utils_lib.write_file(hf, contents='contents')
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch('master'))
    self.assertEqual(hf, utils_lib.read_file(hf))
    self.assertEqual(branch_lib.SUCCESS, branch_lib.switch(BRANCH))
    self.assertEqual('contents', utils_lib.read_file(hf))


class TestUpstream(TestBranch):

  REMOTE_NAME = 'remote'
  REMOTE_URL = 'url'

  def setUp(self):
    super(TestUpstream, self).setUp()
    common.stub(remote_lib.git_remote, stubs.RemoteLib())
    remote_lib.add(self.REMOTE_NAME, self.REMOTE_URL)

  def test_set_upstream_no_remote(self):
    self.assertEqual(
        branch_lib.REMOTE_NOT_FOUND, branch_lib.set_upstream('r/b'))

  def test_set_upstream(self):
    self.assertEqual(
        branch_lib.SUCCESS,
        branch_lib.set_upstream(self.REMOTE_NAME + '/branch'))

  def test_unset_upstream_no_upstream(self):
    self.assertEqual(
        branch_lib.UPSTREAM_NOT_SET, branch_lib.unset_upstream())

  def test_unset_upstream(self):
    remote_branch = self.REMOTE_NAME + '/branch'
    with common.stub(
        branch_lib.git_branch,
        {'status': lambda b: (True, True, remote_branch),
         'set_upstream': lambda un, ub: branch_lib.git_branch.SUCCESS,
         'unset_upstream': lambda b: branch_lib.git_branch.SUCCESS}):
      branch_lib.set_upstream(remote_branch)
      self.assertEqual(branch_lib.SUCCESS, branch_lib.unset_upstream())



if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_file
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Unit tests for file module."""


import os
import unittest

import gitless.core.file as file_lib
import gitless.tests.utils as utils_lib

from . import common


TRACKED_FP = 'f1'
TRACKED_FP_CONTENTS_1 = 'f1-1\n'
TRACKED_FP_CONTENTS_2 = 'f1-2\n'
TRACKED_FP_WITH_SPACE = 'f1 space'
UNTRACKED_FP = 'f2'
UNTRACKED_FP_WITH_SPACE = 'f2 space'
IGNORED_FP = 'f3'
IGNORED_FP_WITH_SPACE = 'f3 space'
NONEXISTENT_FP = 'nonexistent'
NONEXISTENT_FP_WITH_SPACE = 'nonexistent space'
DIR = 'dir'
UNTRACKED_DIR_FP = os.path.join(DIR, 'f1')
UNTRACKED_DIR_FP_WITH_SPACE = os.path.join(DIR, 'f1 space')
TRACKED_DIR_FP = os.path.join(DIR, 'f2')
TRACKED_DIR_FP_WITH_SPACE = os.path.join(DIR, 'f2 space')
DIR_DIR = os.path.join(DIR, DIR)
UNTRACKED_DIR_DIR_FP = os.path.join(DIR_DIR, 'f1')
UNTRACKED_DIR_DIR_FP_WITH_SPACE = os.path.join(DIR_DIR, 'f1 space')
TRACKED_DIR_DIR_FP = os.path.join(DIR_DIR, 'f2')
TRACKED_DIR_DIR_FP_WITH_SPACE = os.path.join(DIR_DIR, 'f2 space')
ALL_FPS_IN_WD = [
    TRACKED_FP, TRACKED_FP_WITH_SPACE, UNTRACKED_FP, UNTRACKED_FP_WITH_SPACE,
    IGNORED_FP, IGNORED_FP_WITH_SPACE, UNTRACKED_DIR_FP,
    UNTRACKED_DIR_FP_WITH_SPACE, TRACKED_DIR_FP, TRACKED_DIR_FP_WITH_SPACE,
    UNTRACKED_DIR_DIR_FP, UNTRACKED_DIR_DIR_FP_WITH_SPACE, TRACKED_DIR_DIR_FP,
    TRACKED_DIR_DIR_FP_WITH_SPACE, '.gitignore']
ALL_DIR_FPS_IN_WD = [
    TRACKED_DIR_FP, TRACKED_DIR_FP_WITH_SPACE, UNTRACKED_DIR_FP,
    UNTRACKED_DIR_FP_WITH_SPACE, TRACKED_DIR_DIR_FP,
    TRACKED_DIR_DIR_FP_WITH_SPACE, UNTRACKED_DIR_DIR_FP,
    UNTRACKED_DIR_DIR_FP_WITH_SPACE]


class TestFile(common.TestCore):
  """Base class for file tests."""

  def setUp(self):
    super(TestFile, self).setUp()

    # Build up an interesting mock repo.
    utils_lib.write_file(TRACKED_FP, contents=TRACKED_FP_CONTENTS_1)
    utils_lib.write_file(TRACKED_FP_WITH_SPACE, contents=TRACKED_FP_CONTENTS_1)
    utils_lib.write_file(TRACKED_DIR_FP, contents=TRACKED_FP_CONTENTS_1)
    utils_lib.write_file(
        TRACKED_DIR_FP_WITH_SPACE, contents=TRACKED_FP_CONTENTS_1)
    utils_lib.write_file(TRACKED_DIR_DIR_FP, contents=TRACKED_FP_CONTENTS_1)
    utils_lib.write_file(
        TRACKED_DIR_DIR_FP_WITH_SPACE, contents=TRACKED_FP_CONTENTS_1)
    utils_lib.git_call(
        'add "{0}" "{1}" "{2}" "{3}" "{4}" "{5}"'.format(
          TRACKED_FP, TRACKED_FP_WITH_SPACE,
          TRACKED_DIR_FP, TRACKED_DIR_FP_WITH_SPACE,
          TRACKED_DIR_DIR_FP, TRACKED_DIR_DIR_FP_WITH_SPACE))
    utils_lib.git_call(
        'commit -m"1" "{0}" "{1}" "{2}" "{3}" "{4}" "{5}"'.format(
          TRACKED_FP, TRACKED_FP_WITH_SPACE,
          TRACKED_DIR_FP, TRACKED_DIR_FP_WITH_SPACE,
          TRACKED_DIR_DIR_FP, TRACKED_DIR_DIR_FP_WITH_SPACE))
    utils_lib.write_file(TRACKED_FP, contents=TRACKED_FP_CONTENTS_2)
    utils_lib.write_file(TRACKED_FP_WITH_SPACE, contents=TRACKED_FP_CONTENTS_2)
    utils_lib.write_file(TRACKED_DIR_FP, contents=TRACKED_FP_CONTENTS_2)
    utils_lib.write_file(
        TRACKED_DIR_FP_WITH_SPACE, contents=TRACKED_FP_CONTENTS_2)
    utils_lib.write_file(TRACKED_DIR_DIR_FP, contents=TRACKED_FP_CONTENTS_2)
    utils_lib.write_file(
        TRACKED_DIR_DIR_FP_WITH_SPACE, contents=TRACKED_FP_CONTENTS_2)
    utils_lib.git_call(
        'commit -m"2" "{0}" "{1}" "{2}" "{3}" "{4}" "{5}"'.format(
          TRACKED_FP, TRACKED_FP_WITH_SPACE,
          TRACKED_DIR_FP, TRACKED_DIR_FP_WITH_SPACE,
          TRACKED_DIR_DIR_FP, TRACKED_DIR_DIR_FP_WITH_SPACE))
    utils_lib.write_file(UNTRACKED_FP)
    utils_lib.write_file(UNTRACKED_FP_WITH_SPACE)
    utils_lib.write_file(UNTRACKED_DIR_FP)
    utils_lib.write_file(UNTRACKED_DIR_FP_WITH_SPACE)
    utils_lib.write_file(UNTRACKED_DIR_DIR_FP)
    utils_lib.write_file(UNTRACKED_DIR_DIR_FP_WITH_SPACE)
    utils_lib.write_file(
        '.gitignore', contents='{0}\n{1}'.format(
            IGNORED_FP, IGNORED_FP_WITH_SPACE))
    utils_lib.write_file(IGNORED_FP)
    utils_lib.write_file(IGNORED_FP_WITH_SPACE)


class TestTrackFile(TestFile):

  def test_track_dir(self):
    self.assertEqual(file_lib.FILE_IS_DIR, file_lib.track(DIR))

  @common.assert_contents_unchanged(UNTRACKED_FP)
  def test_track_untracked_fp(self):
    self.__assert_track_fp(UNTRACKED_FP)

  @common.assert_contents_unchanged(UNTRACKED_FP_WITH_SPACE)
  def test_track_untracked_fp_with_space(self):
    self.__assert_track_fp(UNTRACKED_FP_WITH_SPACE)

  @common.assert_contents_unchanged(UNTRACKED_DIR_FP)
  def test_track_untracked_dir_fp(self):
    self.__assert_track_fp(UNTRACKED_DIR_FP)

  @common.assert_contents_unchanged(UNTRACKED_DIR_FP_WITH_SPACE)
  def test_track_untracked_dir_fp_with_space(self):
    self.__assert_track_fp(UNTRACKED_DIR_FP_WITH_SPACE)

  @common.assert_contents_unchanged(UNTRACKED_DIR_DIR_FP)
  def test_track_untracked_dir_dir_fp(self):
    self.__assert_track_fp(UNTRACKED_DIR_DIR_FP)

  @common.assert_contents_unchanged(UNTRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_track_untracked_dir_dir_fp_with_space(self):
    self.__assert_track_fp(UNTRACKED_DIR_DIR_FP_WITH_SPACE)

  @common.assert_contents_unchanged(
      UNTRACKED_DIR_FP, UNTRACKED_DIR_FP_WITH_SPACE, UNTRACKED_DIR_DIR_FP,
      UNTRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_track_untracked_relative(self):
    os.chdir(DIR)
    self.__assert_track_fp(os.path.relpath(UNTRACKED_DIR_FP, DIR))
    self.__assert_track_fp(os.path.relpath(UNTRACKED_DIR_FP_WITH_SPACE, DIR))
    os.chdir(DIR)
    self.__assert_track_fp(os.path.relpath(UNTRACKED_DIR_DIR_FP, DIR_DIR))
    self.__assert_track_fp(
        os.path.relpath(UNTRACKED_DIR_DIR_FP_WITH_SPACE, DIR_DIR))

  def __assert_track_fp(self, fp):
    t = file_lib.track(fp)
    self.assertEqual(
        file_lib.SUCCESS, t,
        'Track of fp "{0}" failed: expected {1}, got {2}'.format(
            fp, file_lib.SUCCESS, t))
    st = file_lib.status(fp)
    self.assertTrue(st)
    self.assertEqual(
        file_lib.TRACKED, st.type,
        'Track of fp "{0}" failed: expected status.type={1}, got '
        'status.type={2}'.format(fp, file_lib.TRACKED, st.type))

  @common.assert_no_side_effects(TRACKED_FP)
  def test_track_tracked_fp(self):
    self.assertEqual(file_lib.FILE_ALREADY_TRACKED, file_lib.track(TRACKED_FP))

  @common.assert_no_side_effects(TRACKED_FP_WITH_SPACE)
  def test_track_tracked_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED, file_lib.track(TRACKED_FP_WITH_SPACE))

  @common.assert_no_side_effects(TRACKED_DIR_FP)
  def test_track_tracked_dir_fp(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED, file_lib.track(TRACKED_DIR_FP))

  @common.assert_no_side_effects(TRACKED_DIR_FP_WITH_SPACE)
  def test_track_tracked_dir_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED,
        file_lib.track(TRACKED_DIR_FP_WITH_SPACE))

  @common.assert_contents_unchanged(TRACKED_DIR_DIR_FP)
  def test_track_tracked_dir_dir_fp(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED,
        file_lib.track(TRACKED_DIR_DIR_FP))

  @common.assert_contents_unchanged(TRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_track_tracked_dir_dir_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED,
        file_lib.track(TRACKED_DIR_DIR_FP_WITH_SPACE))

  @common.assert_contents_unchanged(
      TRACKED_DIR_FP, TRACKED_DIR_FP_WITH_SPACE, TRACKED_DIR_DIR_FP,
      TRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_track_tracked_relative(self):
    os.chdir(DIR)
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED,
        file_lib.track(os.path.relpath(TRACKED_DIR_FP, DIR)))
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED,
        file_lib.track(os.path.relpath(TRACKED_DIR_FP_WITH_SPACE, DIR)))
    os.chdir(DIR)
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED,
        file_lib.track(os.path.relpath(TRACKED_DIR_DIR_FP, DIR_DIR)))
    self.assertEqual(
        file_lib.FILE_ALREADY_TRACKED,
        file_lib.track(os.path.relpath(TRACKED_DIR_DIR_FP_WITH_SPACE, DIR_DIR)))

  def test_track_nonexistent_fp(self):
    self.assertEqual(file_lib.FILE_NOT_FOUND, file_lib.track(NONEXISTENT_FP))

  def test_track_nonexistent_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_NOT_FOUND, file_lib.track(NONEXISTENT_FP_WITH_SPACE))

  @common.assert_no_side_effects(IGNORED_FP)
  def test_track_ignored(self):
    self.assertEqual(file_lib.FILE_IS_IGNORED, file_lib.track(IGNORED_FP))

  @common.assert_no_side_effects(IGNORED_FP_WITH_SPACE)
  def test_track_ignored_with_space(self):
    self.assertEqual(
        file_lib.FILE_IS_IGNORED, file_lib.track(IGNORED_FP_WITH_SPACE))


class TestUntrackFile(TestFile):

  def test_untrack_dir(self):
    self.assertEqual(file_lib.FILE_IS_DIR, file_lib.untrack(DIR))

  @common.assert_contents_unchanged(TRACKED_FP)
  def test_untrack_tracked_fp(self):
    self.__assert_untrack_fp(TRACKED_FP)

  @common.assert_contents_unchanged(TRACKED_FP_WITH_SPACE)
  def test_untrack_tracked_fp_space(self):
    self.__assert_untrack_fp(TRACKED_FP_WITH_SPACE)

  @common.assert_contents_unchanged(TRACKED_DIR_FP)
  def test_untrack_tracked_dir_fp(self):
    self.__assert_untrack_fp(TRACKED_DIR_FP)

  @common.assert_contents_unchanged(TRACKED_DIR_FP_WITH_SPACE)
  def test_untrack_tracked_dir_fp_with_space(self):
    self.__assert_untrack_fp(TRACKED_DIR_FP_WITH_SPACE)

  @common.assert_contents_unchanged(TRACKED_DIR_DIR_FP)
  def test_untrack_tracked_dir_dir_fp(self):
    self.__assert_untrack_fp(TRACKED_DIR_DIR_FP)

  @common.assert_contents_unchanged(TRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_untrack_tracked_dir_dir_fp_with_space(self):
    self.__assert_untrack_fp(TRACKED_DIR_DIR_FP_WITH_SPACE)

  @common.assert_contents_unchanged(
      TRACKED_DIR_FP, TRACKED_DIR_FP_WITH_SPACE, TRACKED_DIR_DIR_FP,
      TRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_untrack_tracked_relative(self):
    os.chdir(DIR)
    self.__assert_untrack_fp(os.path.relpath(TRACKED_DIR_FP, DIR))
    self.__assert_untrack_fp(os.path.relpath(TRACKED_DIR_FP_WITH_SPACE, DIR))
    os.chdir(DIR)
    self.__assert_untrack_fp(os.path.relpath(TRACKED_DIR_DIR_FP, DIR_DIR))
    self.__assert_untrack_fp(
        os.path.relpath(TRACKED_DIR_DIR_FP_WITH_SPACE, DIR_DIR))

  def __assert_untrack_fp(self, fp):
    t = file_lib.untrack(fp)
    self.assertEqual(
        file_lib.SUCCESS, t,
        'Untrack of fp "{0}" failed: expected {1}, got {2}'.format(
            fp, file_lib.SUCCESS, t))
    st = file_lib.status(fp)
    self.assertTrue(st)
    self.assertEqual(
        file_lib.UNTRACKED, st.type,
        'Untrack of fp "{0}" failed: expected status.type={1}, got '
        'status.type={2}'.format(fp, file_lib.UNTRACKED, st.type))

  @common.assert_no_side_effects(UNTRACKED_FP)
  def test_untrack_untracked_fp(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED, file_lib.untrack(UNTRACKED_FP))

  @common.assert_no_side_effects(UNTRACKED_FP_WITH_SPACE)
  def test_untrack_untracked_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED,
        file_lib.untrack(UNTRACKED_FP_WITH_SPACE))

  @common.assert_no_side_effects(UNTRACKED_DIR_FP)
  def test_untrack_untracked_dir_fp(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED, file_lib.untrack(UNTRACKED_DIR_FP))

  @common.assert_no_side_effects(UNTRACKED_DIR_FP_WITH_SPACE)
  def test_untrack_untracked_dir_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED,
        file_lib.untrack(UNTRACKED_DIR_FP_WITH_SPACE))

  @common.assert_no_side_effects(UNTRACKED_DIR_DIR_FP)
  def test_untrack_untracked_dir_dir_fp(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED, file_lib.untrack(UNTRACKED_DIR_DIR_FP))

  @common.assert_no_side_effects(UNTRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_untrack_untracked_dir_dir_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED,
        file_lib.untrack(UNTRACKED_DIR_DIR_FP_WITH_SPACE))

  @common.assert_contents_unchanged(
      UNTRACKED_DIR_FP, UNTRACKED_DIR_FP_WITH_SPACE, UNTRACKED_DIR_DIR_FP,
      UNTRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_untrack_untracked_relative(self):
    os.chdir(DIR)
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED,
        file_lib.untrack(os.path.relpath(UNTRACKED_DIR_FP, DIR)))
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED,
        file_lib.untrack(os.path.relpath(UNTRACKED_DIR_FP_WITH_SPACE, DIR)))
    os.chdir(DIR)
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED,
        file_lib.untrack(os.path.relpath(UNTRACKED_DIR_DIR_FP, DIR_DIR)))
    self.assertEqual(
        file_lib.FILE_ALREADY_UNTRACKED,
        file_lib.untrack(
            os.path.relpath(UNTRACKED_DIR_DIR_FP_WITH_SPACE, DIR_DIR)))

  def test_untrack_nonexistent_fp(self):
    self.assertEqual(file_lib.FILE_NOT_FOUND, file_lib.untrack(NONEXISTENT_FP))

  def test_untrack_nonexistent_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_NOT_FOUND, file_lib.untrack(NONEXISTENT_FP_WITH_SPACE))

  @common.assert_no_side_effects(IGNORED_FP)
  def test_untrack_ignored(self):
    self.assertEqual(file_lib.FILE_IS_IGNORED, file_lib.untrack(IGNORED_FP))

  @common.assert_no_side_effects(IGNORED_FP_WITH_SPACE)
  def test_untrack_ignored_with_space(self):
    self.assertEqual(
        file_lib.FILE_IS_IGNORED, file_lib.untrack(IGNORED_FP_WITH_SPACE))


class TestCheckoutFile(TestFile):

  def test_checkout_dir(self):
    self.assertEqual(file_lib.FILE_IS_DIR, file_lib.checkout(DIR)[0])

  @common.assert_no_side_effects(TRACKED_FP)
  def test_checkout_fp_at_head(self):
    self.__assert_checkout_fp_at_head(TRACKED_FP)

  @common.assert_no_side_effects(TRACKED_FP_WITH_SPACE)
  def test_checkout_fp_with_space_at_head(self):
    self.__assert_checkout_fp_at_head(TRACKED_FP_WITH_SPACE)

  @common.assert_no_side_effects(TRACKED_DIR_FP)
  def test_checkout_dir_fp_at_head(self):
    self.__assert_checkout_fp_at_head(TRACKED_DIR_FP)

  @common.assert_no_side_effects(TRACKED_DIR_FP_WITH_SPACE)
  def test_checkout_dir_fp_with_space_at_head(self):
    self.__assert_checkout_fp_at_head(TRACKED_DIR_FP_WITH_SPACE)

  @common.assert_no_side_effects(TRACKED_DIR_DIR_FP)
  def test_checkout_dir_dir_fp_at_head(self):
    self.__assert_checkout_fp_at_head(TRACKED_DIR_DIR_FP)

  @common.assert_no_side_effects(TRACKED_DIR_DIR_FP_WITH_SPACE)
  def test_checkout_dir_dir_fp_with_space_at_head(self):
    self.__assert_checkout_fp_at_head(TRACKED_DIR_DIR_FP_WITH_SPACE)

  def test_checkout_fp_at_cp_other_than_head(self):
    self.__assert_checkout_cp_other_than_head(TRACKED_FP)

  def test_checkout_fp_with_space_at_cp_other_than_head(self):
    self.__assert_checkout_cp_other_than_head(TRACKED_FP_WITH_SPACE)

  def test_checkout_dir_fp_at_cp_other_than_head(self):
    self.__assert_checkout_cp_other_than_head(TRACKED_DIR_FP)

  def test_checkout_dir_fp_with_space_at_cp_other_than_head(self):
    self.__assert_checkout_cp_other_than_head(TRACKED_DIR_FP_WITH_SPACE)

  def test_checkout_dir_dir_fp_at_cp_other_than_head(self):
    self.__assert_checkout_cp_other_than_head(TRACKED_DIR_DIR_FP)

  def test_checkout_dir_dir_fp_with_space_at_cp_other_than_head(self):
    self.__assert_checkout_cp_other_than_head(TRACKED_DIR_DIR_FP_WITH_SPACE)

  @common.assert_no_side_effects(UNTRACKED_FP)
  def test_checkout_uncommited_fp(self):
    self.assertEqual(
        file_lib.FILE_NOT_FOUND_AT_CP, file_lib.checkout(UNTRACKED_FP)[0])

  @common.assert_no_side_effects(UNTRACKED_FP_WITH_SPACE)
  def test_checkout_uncommited_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_NOT_FOUND_AT_CP,
        file_lib.checkout(UNTRACKED_FP_WITH_SPACE)[0])

  def test_checkout_nonexistent_fp(self):
    self.assertEqual(
        file_lib.FILE_NOT_FOUND_AT_CP, file_lib.checkout(NONEXISTENT_FP)[0])

  def test_checkout_nonexistent_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_NOT_FOUND_AT_CP,
        file_lib.checkout(NONEXISTENT_FP_WITH_SPACE)[0])

  def test_checkout_relative(self):
    os.chdir(DIR)
    self.__assert_checkout_fp_at_head(os.path.relpath(TRACKED_DIR_FP, DIR))
    self.__assert_checkout_fp_at_head(
        os.path.relpath(TRACKED_DIR_FP_WITH_SPACE, DIR))
    os.chdir(DIR)
    self.__assert_checkout_fp_at_head(
        os.path.relpath(TRACKED_DIR_DIR_FP, DIR_DIR))
    self.__assert_checkout_fp_at_head(
        os.path.relpath(TRACKED_DIR_DIR_FP_WITH_SPACE, DIR_DIR))

  def __assert_checkout_fp_at_head(self, fp):
    contents = utils_lib.read_file(fp)
    utils_lib.write_file(fp, contents='contents')
    self.assertEqual(file_lib.SUCCESS, file_lib.checkout(fp)[0])
    self.assertEqual(contents, utils_lib.read_file(fp))

  def __assert_checkout_cp_other_than_head(self, fp):
    utils_lib.write_file(fp, contents='contents')
    self.assertEqual(file_lib.SUCCESS, file_lib.checkout(fp, 'HEAD^1')[0])
    self.assertEqual(TRACKED_FP_CONTENTS_1, utils_lib.read_file(fp))


class TestStatus(TestFile):

  def test_status_all(self):
    st_all = file_lib.status_all()
    seen = []
    for fp, f_type, exists_in_lr, exists_in_wd, modified, _, _ in st_all:
      if (fp == TRACKED_FP or fp == TRACKED_FP_WITH_SPACE or
          fp == TRACKED_DIR_FP or fp == TRACKED_DIR_FP_WITH_SPACE or
          fp == TRACKED_DIR_DIR_FP or fp == TRACKED_DIR_DIR_FP_WITH_SPACE):
        self.__assert_type(fp, file_lib.TRACKED, f_type)
        self.__assert_field(fp, 'exists_in_lr', True, exists_in_lr)
        self.__assert_field(fp, 'modified', False, modified)
      elif (fp == UNTRACKED_FP or fp == UNTRACKED_FP_WITH_SPACE or
            fp == UNTRACKED_DIR_FP or fp == UNTRACKED_DIR_FP_WITH_SPACE or
            fp == UNTRACKED_DIR_DIR_FP or
            fp == UNTRACKED_DIR_DIR_FP_WITH_SPACE):
        self.__assert_type(fp, file_lib.UNTRACKED, f_type)
        self.__assert_field(fp, 'exists_in_lr', False, exists_in_lr)
        self.__assert_field(fp, 'modified', True, modified)
      elif fp == IGNORED_FP or fp == IGNORED_FP_WITH_SPACE:
        self.__assert_type(fp, file_lib.IGNORED, f_type)
        self.__assert_field(fp, 'exists_in_lr', False, exists_in_lr)
        self.__assert_field(fp, 'modified', True, modified)
      elif fp == '.gitignore':
        self.__assert_type(fp, file_lib.UNTRACKED, f_type)
        self.__assert_field(fp, 'exists_in_lr', False, exists_in_lr)
        self.__assert_field(fp, 'modified', True, modified)
      else:
        self.fail('Unexpected fp {0}'.format(fp))
      self.__assert_field(fp, 'exists_in_wd', True, exists_in_wd)
      seen.append(fp)
    self.assertItemsEqual(seen, ALL_FPS_IN_WD)

  def test_status_equivalence(self):
    self.assertItemsEqual(
        file_lib.status_all(), [file_lib.status(fp) for fp in ALL_FPS_IN_WD])

  def test_status_nonexistent_fp(self):
    self.assertFalse(file_lib.status(NONEXISTENT_FP))

  def test_status_nonexistent_fp_with_space(self):
    self.assertFalse(file_lib.status(NONEXISTENT_FP_WITH_SPACE))

  def test_status_modify(self):
    utils_lib.write_file(TRACKED_FP, contents='contents')
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertTrue(st.modified)
    utils_lib.write_file(TRACKED_FP, contents=TRACKED_FP_CONTENTS_2)
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertFalse(st.modified)

  def test_status_rm(self):
    os.remove(TRACKED_FP)
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.TRACKED, st.type)
    self.assertTrue(st.modified)
    self.assertTrue(st.exists_in_lr)
    self.assertFalse(st.exists_in_wd)

    utils_lib.write_file(TRACKED_FP, contents=TRACKED_FP_CONTENTS_2)
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.TRACKED, st.type)
    self.assertFalse(st.modified)
    self.assertTrue(st.exists_in_lr)
    self.assertTrue(st.exists_in_wd)

  def test_status_track_rm(self):
    file_lib.track(UNTRACKED_FP)
    st = file_lib.status(UNTRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.TRACKED, st.type)
    self.assertTrue(st.modified)

    os.remove(UNTRACKED_FP)
    self.assertFalse(file_lib.status(UNTRACKED_FP))

  def test_status_track_untrack(self):
    file_lib.track(UNTRACKED_FP)
    st = file_lib.status(UNTRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.TRACKED, st.type)
    self.assertTrue(st.modified)

    file_lib.untrack(UNTRACKED_FP)
    st = file_lib.status(UNTRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.UNTRACKED, st.type)
    self.assertTrue(st.modified)

  def test_status_unignore(self):
    utils_lib.write_file('.gitignore', contents='')
    st = file_lib.status(IGNORED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.UNTRACKED, st.type)
    st = file_lib.status(IGNORED_FP_WITH_SPACE)
    self.assertTrue(st)
    self.assertEqual(file_lib.UNTRACKED, st.type)

  def test_status_ignore(self):
    contents = utils_lib.read_file('.gitignore') + '\n' + TRACKED_FP
    utils_lib.write_file('.gitignore', contents=contents)
    # Tracked files can't be ignored.
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.TRACKED, st.type)

  def test_status_untrack_tracked_modify(self):
    file_lib.untrack(TRACKED_FP)
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.UNTRACKED, st.type)
    # self.assertFalse(st.modified)

    utils_lib.write_file(TRACKED_FP, contents='contents')
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.UNTRACKED, st.type)
    self.assertTrue(st.modified)

  def test_status_untrack_tracked_rm(self):
    file_lib.untrack(TRACKED_FP)
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.assertEqual(file_lib.UNTRACKED, st.type)

    os.remove(TRACKED_FP)
    self.assertFalse(file_lib.status(TRACKED_FP))

  def test_status_all_relative(self):
    rel_to_dir = lambda fp: os.path.relpath(fp, DIR)

    os.chdir(DIR)

    st_all = file_lib.status_all()
    seen = []
    for fp, f_type, exists_in_lr, exists_in_wd, modified, _, _ in st_all:
      if (fp == rel_to_dir(TRACKED_DIR_FP) or
          fp == rel_to_dir(TRACKED_DIR_FP_WITH_SPACE) or
          fp == rel_to_dir(TRACKED_DIR_DIR_FP) or
          fp == rel_to_dir(TRACKED_DIR_DIR_FP_WITH_SPACE)):
        self.__assert_type(fp, file_lib.TRACKED, f_type)
        self.__assert_field(fp, 'exists_in_lr', True, exists_in_lr)
        self.__assert_field(fp, 'modified', False, modified)
      elif (fp == rel_to_dir(UNTRACKED_DIR_FP) or
            fp == rel_to_dir(UNTRACKED_DIR_FP_WITH_SPACE) or
            fp == rel_to_dir(UNTRACKED_DIR_DIR_FP) or
            fp == rel_to_dir(UNTRACKED_DIR_DIR_FP_WITH_SPACE)):
        self.__assert_type(fp, file_lib.UNTRACKED, f_type)
        self.__assert_field(fp, 'exists_in_lr', False, exists_in_lr)
        self.__assert_field(fp, 'modified', True, modified)
      else:
        self.fail('Unexpected fp {0}'.format(fp))
      self.__assert_field(fp, 'exists_in_wd', True, exists_in_wd)
      seen.append(fp)
    self.assertItemsEqual(seen, [rel_to_dir(fp) for fp in ALL_DIR_FPS_IN_WD])

  def test_status_ignore_tracked(self):
    """Assert that ignoring a tracked file has no effect."""
    utils_lib.append_to_file('.gitignore', contents='\n' + TRACKED_FP + '\n')
    st = file_lib.status(TRACKED_FP)
    self.assertTrue(st)
    self.__assert_type(TRACKED_FP, file_lib.TRACKED, st.type)

  def test_status_ignore_untracked(self):
    """Assert that ignoring a untracked file makes it ignored."""
    utils_lib.append_to_file('.gitignore', contents='\n' + UNTRACKED_FP + '\n')
    st = file_lib.status(UNTRACKED_FP)
    self.assertTrue(st)
    self.__assert_type(UNTRACKED_FP, file_lib.IGNORED, st.type)

  # TODO(sperezde): this test exposes a rough edge that we haven't fixed yet.
  # Uncomment the test once it's fixed.
  #def test_status_ignore_untracked_tracked(self):
  #  file_lib.untrack(TRACKED_FP)
  #  utils_lib.append_to_file('.gitignore', contents='\n' + TRACKED_FP + '\n')
  #  self.__assert_type(
  #      TRACKED_FP, file_lib.IGNORED, file_lib.status(TRACKED_FP).type)

  def __assert_type(self, fp, expected, got):
    self.assertEqual(
        expected, got,
        'Incorrect type for {0}: expected {1}, got {2}'.format(
            fp, expected, got))

  def __assert_field(self, fp, field, expected, got):
    self.assertEqual(
        expected, got,
        'Incorrect status for {0}: expected {1}={2}, got {3}={4}'.format(
            fp, field, expected, field, got))


class TestDiff(TestFile):

  # TODO(sperezde): add DIR, DIR_DIR, relative tests to diff.

  def test_diff_dir(self):
    self.assertEqual(file_lib.FILE_IS_DIR, file_lib.diff(DIR)[0])

  @common.assert_no_side_effects(UNTRACKED_FP)
  def test_diff_untracked_fp(self):
    self.assertEqual(file_lib.FILE_IS_UNTRACKED, file_lib.diff(UNTRACKED_FP)[0])

  @common.assert_no_side_effects(UNTRACKED_FP_WITH_SPACE)
  def test_diff_untracked_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_IS_UNTRACKED, file_lib.diff(UNTRACKED_FP_WITH_SPACE)[0])

  @common.assert_no_side_effects(IGNORED_FP)
  def test_diff_ignored_fp(self):
    self.assertEqual(file_lib.FILE_IS_IGNORED, file_lib.diff(IGNORED_FP)[0])

  @common.assert_no_side_effects(IGNORED_FP_WITH_SPACE)
  def test_diff_ignored_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_IS_IGNORED, file_lib.diff(IGNORED_FP_WITH_SPACE)[0])

  def test_diff_nonexistent_fp(self):
    self.assertEqual(file_lib.FILE_NOT_FOUND, file_lib.diff(NONEXISTENT_FP)[0])

  def test_diff_nonexistent_fp_with_space(self):
    self.assertEqual(
        file_lib.FILE_NOT_FOUND, file_lib.diff(NONEXISTENT_FP_WITH_SPACE)[0])

  @common.assert_no_side_effects(TRACKED_FP)
  def test_empty_diff(self):
    ret, (out, _, _, _) = file_lib.diff(TRACKED_FP)
    self.assertEqual(file_lib.SUCCESS, ret)
    self.assertEqual([], out)

  def test_diff_basic(self):
    utils_lib.write_file(TRACKED_FP, contents='new contents')
    ret, (out, _, additions, removals) = file_lib.diff(TRACKED_FP)

    self.assertEqual(1, additions)
    self.assertEqual(1, removals)

    self.assertEqual(file_lib.SUCCESS, ret)
    self.assertEqual(3, len(out))
    # [:-1] removes the '\n'.
    self.assertEqual('-' + TRACKED_FP_CONTENTS_2[:-1], out[1].line)
    self.assertEqual(file_lib.DIFF_MINUS, out[1].status)
    self.assertEqual(1, out[1].old_line_number)
    self.assertEqual(None, out[1].new_line_number)

    self.assertEqual('+new contents', out[2].line)
    self.assertEqual(file_lib.DIFF_ADDED, out[2].status)
    self.assertEqual(None, out[2].old_line_number)
    self.assertEqual(1, out[2].new_line_number)

  def test_diff_append(self):
    utils_lib.append_to_file(TRACKED_FP, contents='new contents')
    ret, (out, _, additions, removals) = file_lib.diff(TRACKED_FP)

    self.assertEqual(1, additions)
    self.assertEqual(0, removals)

    self.assertEqual(file_lib.SUCCESS, ret)
    self.assertEqual(3, len(out))
    # [:-1] removes the '\n'.
    self.assertEqual(' ' + TRACKED_FP_CONTENTS_2[:-1], out[1].line)
    self.assertEqual(file_lib.DIFF_SAME, out[1].status)
    self.assertEqual(1, out[1].old_line_number)
    self.assertEqual(1, out[1].new_line_number)

    self.assertEqual('+new contents', out[2].line)
    self.assertEqual(file_lib.DIFF_ADDED, out[2].status)
    self.assertEqual(None, out[2].old_line_number)
    self.assertEqual(2, out[2].new_line_number)

  def test_diff_new_fp(self):
    fp = 'new'
    utils_lib.write_file(fp, contents=fp + '\n')
    file_lib.track(fp)
    ret, (out, _, additions, removals) = file_lib.diff(fp)

    self.assertEqual(1, additions)
    self.assertEqual(0, removals)

    self.assertEqual(file_lib.SUCCESS, ret)
    self.assertEqual(2, len(out))
    self.assertEqual('+' + fp, out[1].line)
    self.assertEqual(file_lib.DIFF_ADDED, out[1].status)
    self.assertEqual(None, out[1].old_line_number)
    self.assertEqual(1, out[1].new_line_number)

    # Now let's add some change to the file and check that diff notices it.
    utils_lib.append_to_file(fp, contents='new line')
    ret, (out, _, additions, removals) = file_lib.diff(fp)

    self.assertEqual(2, additions)
    self.assertEqual(0, removals)

    self.assertEqual(file_lib.SUCCESS, ret)

    self.assertEqual(3, len(out))
    self.assertEqual('+' + fp, out[1].line)
    self.assertEqual(file_lib.DIFF_ADDED, out[1].status)
    self.assertEqual(None, out[1].old_line_number)
    self.assertEqual(1, out[1].new_line_number)

    self.assertEqual('+new line', out[2].line)
    self.assertEqual(file_lib.DIFF_ADDED, out[2].status)
    self.assertEqual(None, out[2].old_line_number)
    self.assertEqual(2, out[2].new_line_number)


FP_IN_CONFLICT = 'f_conflict'
DIR_FP_IN_CONFLICT = os.path.join(DIR, FP_IN_CONFLICT)


class TestResolveFile(TestFile):

  def setUp(self):
    super(TestResolveFile, self).setUp()

    # Generate a conflict.
    utils_lib.git_call('checkout -b branch')
    utils_lib.write_file(FP_IN_CONFLICT, contents='branch')
    utils_lib.write_file(DIR_FP_IN_CONFLICT, contents='branch')
    utils_lib.git_call(
        'add "{0}" "{1}"'.format(FP_IN_CONFLICT, DIR_FP_IN_CONFLICT))
    utils_lib.git_call(
        'commit -m"branch" "{0}" "{1}"'.format(
            FP_IN_CONFLICT, DIR_FP_IN_CONFLICT))
    utils_lib.git_call('checkout master')
    utils_lib.write_file(FP_IN_CONFLICT, contents='master')
    utils_lib.write_file(DIR_FP_IN_CONFLICT, contents='master')
    utils_lib.git_call(
        'add "{0}" "{1}"'.format(FP_IN_CONFLICT, DIR_FP_IN_CONFLICT))
    utils_lib.git_call(
        'commit -m"master" "{0}" "{1}"'.format(
            FP_IN_CONFLICT, DIR_FP_IN_CONFLICT))
    utils_lib.git_call('merge branch', expected_ret_code=1)

  def test_resolve_dir(self):
    self.assertEqual(file_lib.FILE_IS_DIR, file_lib.resolve(DIR))

  @common.assert_no_side_effects(TRACKED_FP)
  def test_resolve_fp_with_no_conflicts(self):
    self.assertEqual(
        file_lib.FILE_NOT_IN_CONFLICT, file_lib.resolve(TRACKED_FP))

  def test_resolve_fp_with_conflicts(self):
    self.__assert_resolve_fp(FP_IN_CONFLICT)

  def test_resolve_dir_fp_with_conflicts(self):
    self.__assert_resolve_fp(DIR_FP_IN_CONFLICT)

  def test_resolve_relative(self):
    self.__assert_resolve_fp(DIR_FP_IN_CONFLICT)
    os.chdir(DIR)
    rel_fp = os.path.relpath(DIR_FP_IN_CONFLICT, DIR)
    st = file_lib.status(rel_fp)
    self.assertTrue(st)
    self.assertTrue(st.resolved)
    self.assertEqual(file_lib.FILE_ALREADY_RESOLVED, file_lib.resolve(rel_fp))

  @common.assert_contents_unchanged(FP_IN_CONFLICT)
  def __assert_resolve_fp(self, fp):
    self.assertEqual(file_lib.SUCCESS, file_lib.resolve(fp))
    st = file_lib.status(fp)
    self.assertTrue(st)
    self.assertTrue(st.resolved)


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_remote
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Unit tests for remote module."""


import unittest

from . import common
from . import stubs

import gitless.core.remote as remote_lib



class TestRemote(common.TestCore):
  """Base class for remote tests."""

  def setUp(self):
    super(TestRemote, self).setUp()
    # Re-stub the module with a fresh RemoteLib instance.
    # This keeps unit tests independent between each other.
    common.stub(remote_lib.git_remote, stubs.RemoteLib())


class TestAdd(TestRemote):

  def test_add_new(self):
    self.assertEqual(remote_lib.SUCCESS, remote_lib.add('remote', 'url'))

  def test_add_existing(self):
    remote_lib.add('remote', 'url')
    self.assertEqual(
        remote_lib.REMOTE_ALREADY_SET, remote_lib.add('remote', 'url2'))

  def test_add_invalid_name(self):
    self.assertEqual(remote_lib.INVALID_NAME, remote_lib.add('rem/ote', 'url'))


class TestInfo(TestRemote):

  def test_info_nonexistent(self):
    self.assertEqual(
        remote_lib.REMOTE_NOT_FOUND, remote_lib.info('nonexistent_remote')[0])

  def test_info(self):
    remote_lib.add('remote', 'url')
    self.assertEqual(remote_lib.SUCCESS, remote_lib.info('remote')[0])


class TestInfoAll(TestRemote):

  def test_info_all(self):
    remote_lib.add('remote1', 'url1')
    remote_lib.add('remote2', 'url2')
    self.assertItemsEqual(
        [remote_lib.RemoteInfo('remote1', 'url1', 'url1'),
         remote_lib.RemoteInfo('remote2', 'url2', 'url2')],
        remote_lib.info_all())


class TestRm(TestRemote):

  def test_rm(self):
    remote_lib.add('remote', 'url')
    self.assertEqual(remote_lib.SUCCESS, remote_lib.rm('remote'))

  def test_rm_nonexistent(self):
    self.assertEqual(remote_lib.REMOTE_NOT_FOUND, remote_lib.rm('remote'))
    remote_lib.add('remote', 'url')
    remote_lib.rm('remote')
    self.assertEqual(remote_lib.REMOTE_NOT_FOUND, remote_lib.rm('remote'))


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_sync
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""Unit tests for sync module."""


import itertools

import gitless.core.file as file_lib
import gitless.core.repo as repo_lib
import gitless.core.sync as sync_lib
import gitless.tests.utils as utils_lib

from . import common


TRACKED_FP = 't_fp'
UNTRACKED_FP = 'u_fp'


class TestPartialCommit(common.TestCore):

  def setUp(self):
    super(TestPartialCommit, self).setUp()
    _setup_fp(TRACKED_FP)
    utils_lib.write_file(UNTRACKED_FP)

  def test_chunking(self):
    chunked_fp_count = 0
    chunk_count = 0
    pc = sync_lib.partial_commit([TRACKED_FP])
    all_chunks = ['chunk1', 'chunk2']
    for chunked_file in pc:
      chunked_fp_count += 1
      for chunk in chunked_file:
        chunk_count += 1
        curr_chunk = 'chunk' + str(chunk_count)
        self.__assert_expected_chunk(
            curr_chunk,
            filter(lambda c: c != curr_chunk, all_chunks),
            _textify_diff(chunk.diff[0]))
    self.assertEqual(1, chunked_fp_count)
    self.assertEqual(2, chunk_count)

  def test_one_chunk_commit(self):
    pc = sync_lib.partial_commit([TRACKED_FP])
    for chunked_file in pc:
      for chunk in chunked_file:
        chunk.include()
        break
    pc.commit('msg')
    ci = repo_lib.history(include_diffs=True)[0]
    self.assertEqual(1, len(ci.diffs))
    self.assertEqual(TRACKED_FP, ci.diffs[0].fp_before)
    self.assertTrue('chunk1' in _textify_diff(ci.diffs[0].diff[0]))
    self.assertFalse('chunk2' in _textify_diff(ci.diffs[0].diff[0]))

  def test_all_chunks_commit(self):
    pc = sync_lib.partial_commit([TRACKED_FP])
    for chunked_file in pc:
      for chunk in chunked_file:
        chunk.include()
    pc.commit('msg')
    ci = repo_lib.history(include_diffs=True)[0]
    self.assertEqual(1, len(ci.diffs))
    self.assertEqual(TRACKED_FP, ci.diffs[0].fp_before)
    self.assertTrue('chunk1' in _textify_diff(ci.diffs[0].diff[0]))
    self.assertTrue('chunk2' in _textify_diff(ci.diffs[0].diff[0]))

  def test_basic_multiple_files(self):
    TRACKED_FP_2 = 't_fp2'
    _setup_fp(TRACKED_FP_2)
    pc = sync_lib.partial_commit([TRACKED_FP, TRACKED_FP_2])
    # Just the first chunk of each file.
    for chunked_file in pc:
      for chunk in chunked_file:
        chunk.include()
        break
    pc.commit('msg')
    ci = repo_lib.history(include_diffs=True)[0]
    self.assertEqual(2, len(ci.diffs))
    self.assertEqual(TRACKED_FP, ci.diffs[0].fp_before)
    self.assertEqual(TRACKED_FP_2, ci.diffs[1].fp_before)
    t_fp_diff = _textify_diff(ci.diffs[0].diff[0])
    t_fp_2_diff = _textify_diff(ci.diffs[1].diff[0])
    self.assertTrue(_chunk_i(TRACKED_FP, 1) in t_fp_diff)
    self.assertFalse(_chunk_i(TRACKED_FP, 2) in t_fp_diff)
    self.assertTrue(_chunk_i(TRACKED_FP_2, 1) in t_fp_2_diff)
    self.assertFalse(_chunk_i(TRACKED_FP_2, 2) in t_fp_2_diff)

  def __assert_expected_chunk(self, expected_chunk, other_chunks, out):
    self.assertTrue(
        expected_chunk in out,
        msg='{0} not found in output'.format(expected_chunk))
    for other_chunk in other_chunks:
      self.assertFalse(
          other_chunk in out, msg='{0} found in output'.format(other_chunk))


def _textify_diff(diff):
  return '\n'.join([ld.line for ld in diff])


def _chunk_i(fp, i):
  return '{0}-chunk{1}'.format(fp, i)


def _setup_fp(fp):
  utils_lib.write_file(fp, contents=_chunk('contents'))
  file_lib.track(fp)
  sync_lib.commit([fp], 'msg')
  new_contents = (
      _chunk(_chunk_i(fp, 1)) + utils_lib.read_file(fp) +
      _chunk(_chunk_i(fp, 2)))
  utils_lib.write_file(fp, contents=new_contents)


def _chunk(content_id):
  CHUNK_SIZE = 10
  contents = ''
  for _ in itertools.repeat(None, CHUNK_SIZE):
    contents += '{0}\n'.format(content_id)
  return contents

########NEW FILE########
__FILENAME__ = test_e2e
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL v2.

"""End-to-end test."""


import logging
import time
import unittest

import gitless.tests.utils as utils_lib


class TestEndToEnd(utils_lib.TestBase):

  def setUp(self):
    super(TestEndToEnd, self).setUp('gl-e2e-test')
    utils_lib.gl_expect_success('init')
    utils_lib.set_test_config()


# TODO(sperezde): add dialog related tests.
# TODO(sperezde): add checkout related tests.


class TestBasic(TestEndToEnd):

  def test_basic_functionality(self):
    utils_lib.write_file('file1', 'Contents of file1')
    # Track.
    utils_lib.gl_expect_success('track file1')
    utils_lib.gl_expect_error('track file1')  # file1 is already tracked.
    utils_lib.gl_expect_error('track non-existent')
    # Untrack.
    utils_lib.gl_expect_success('untrack file1')
    utils_lib.gl_expect_success('untrack file1')  # file1 is already untracked.
    utils_lib.gl_expect_error('untrack non-existent')
    # Commit.
    utils_lib.gl_expect_success('commit -m"file1 commit"')
    utils_lib.gl_expect_error('commit -m"nothing to commit"')
    # History.
    if 'file1 commit' not in utils_lib.gl_expect_success('history')[0]:
      self.fail('Commit didn\'t appear in history')
    # Branch.
    # Make some changes in file1 and branch out.
    utils_lib.write_file('file1', 'New contents of file1')
    utils_lib.gl_expect_success('branch branch1')
    if 'New' in utils_lib.read_file('file1'):
      self.fail('Branch not independent!')
    # Switch back to master branch, check that contents are the same as before.
    utils_lib.gl_expect_success('branch master')
    if 'New' not in utils_lib.read_file('file1'):
      self.fail('Branch not independent!')
    out, _ = utils_lib.gl_expect_success('branch')
    if '* master' not in out:
      self.fail('Branch status output wrong')
    if 'branch1' not in out:
      self.fail('Branch status output wrong')

    utils_lib.gl_expect_success('branch branch1')
    utils_lib.gl_expect_success('branch branch2')
    utils_lib.gl_expect_success('branch branch-conflict1')
    utils_lib.gl_expect_success('branch branch-conflict2')
    utils_lib.gl_expect_success('branch master')
    utils_lib.gl_expect_success('commit -m"New contents commit"')

    # Rebase.
    utils_lib.gl_expect_success('branch branch1')
    utils_lib.gl_expect_error('rebase')  # no upstream set.
    utils_lib.gl_expect_success('rebase master')
    if 'file1 commit' not in utils_lib.gl_expect_success('history')[0]:
      self.fail()

    # Merge.
    utils_lib.gl_expect_success('branch branch2')
    utils_lib.gl_expect_error('merge')  # no upstream set.
    utils_lib.gl_expect_success('merge master')
    if 'file1 commit' not in utils_lib.gl_expect_success('history')[0]:
      self.fail()

    # Conflicting rebase.
    utils_lib.gl_expect_success('branch branch-conflict1')
    utils_lib.write_file('file1', 'Conflicting changes to file1')
    utils_lib.gl_expect_success('commit -m"changes in branch-conflict1"')
    if 'conflict' not in utils_lib.gl_expect_error('rebase master')[1]:
      self.fail()
    if 'file1 (with conflicts)' not in utils_lib.gl_expect_success('status')[0]:
      self.fail()

    # Try aborting.
    utils_lib.gl_expect_success('rebase --abort')
    if 'file1' in utils_lib.gl_expect_success('status')[0]:
      self.fail()

    # Ok, now let's fix the conflicts.
    if 'conflict' not in utils_lib.gl_expect_error('rebase master')[1]:
      self.fail()
    if 'file1 (with conflicts)' not in utils_lib.gl_expect_success('status')[0]:
      self.fail()

    utils_lib.write_file('file1', 'Fixed conflicts!')
    utils_lib.gl_expect_error('commit -m"shouldn\'t work (resolve not called)"')
    utils_lib.gl_expect_error('resolve nonexistentfile')
    utils_lib.gl_expect_success('resolve file1')
    utils_lib.gl_expect_success('commit -m"fixed conflicts"')


class TestCommit(TestEndToEnd):

  TRACKED_FP = 'file1'
  UNTRACKED_FP = 'file2'
  FPS = [TRACKED_FP, UNTRACKED_FP]

  def setUp(self):
    super(TestCommit, self).setUp()
    utils_lib.write_file(self.TRACKED_FP)
    utils_lib.write_file(self.UNTRACKED_FP)
    utils_lib.gl_expect_success('track {0}'.format(self.TRACKED_FP))

  # Happy paths.
  def test_commit(self):
    utils_lib.gl_expect_success('commit -m"msg"')
    self.__assert_commit(self.TRACKED_FP)

  def test_commit_only(self):
    utils_lib.gl_expect_success('commit -m"msg" {0}'.format(self.TRACKED_FP))
    self.__assert_commit(self.TRACKED_FP)

  def test_commit_only_untrack(self):
    utils_lib.gl_expect_success('commit -m"msg" {0}'.format(self.UNTRACKED_FP))
    self.__assert_commit(self.UNTRACKED_FP)

  def test_commit_inc(self):
    utils_lib.gl_expect_success(
        'commit -m"msg" -inc {0}'.format(self.UNTRACKED_FP))
    self.__assert_commit(self.TRACKED_FP, self.UNTRACKED_FP)

  def test_commit_exc_inc(self):
    utils_lib.gl_expect_success(
        'commit -m"msg" -inc {0} -exc {1}'.format(
            self.UNTRACKED_FP, self.TRACKED_FP))
    self.__assert_commit(self.UNTRACKED_FP)

  # Error paths.
  def test_commit_no_files(self):
    utils_lib.gl_expect_error('commit -m"msg" -exc {0}'.format(self.TRACKED_FP))
    utils_lib.gl_expect_error('commit -m"msg" nonexistentfp')
    utils_lib.gl_expect_error('commit -m"msg" -exc nonexistentfp')
    utils_lib.gl_expect_error('commit -m"msg" -inc nonexistentfp')

  def test_commit_dir(self):
    utils_lib.write_file('dir/f')
    utils_lib.gl_expect_error('commit -m"msg" dir')

  def __assert_commit(self, *expected_committed):
    st = utils_lib.gl_expect_success('status')[0]
    h = utils_lib.gl_expect_success('history -v')[0]
    for fp in expected_committed:
      if fp in st or fp not in h:
        self.fail('{0} was apparently not committed!'.format(fp))
    expected_not_committed = [
        fp for fp in self.FPS if fp not in expected_committed]
    for fp in expected_not_committed:
      if fp not in st or fp in h:
        self.fail('{0} was apparently committed!'.format(fp))


class TestBranch(TestEndToEnd):

  BRANCH_1 = 'branch1'
  BRANCH_2 = 'branch2'

  def setUp(self):
    super(TestBranch, self).setUp()
    utils_lib.write_file('f')
    utils_lib.gl_expect_success('commit f -msg"commit"')

  def test_create(self):
    utils_lib.gl_expect_success('branch {0}'.format(self.BRANCH_1))
    utils_lib.gl_expect_error('branch {0}'.format(self.BRANCH_1))
    utils_lib.gl_expect_error('branch evil_named_branch')
    if self.BRANCH_1 not in utils_lib.gl_expect_success('branch')[0]:
      self.fail()

  def test_remove(self):
    utils_lib.gl_expect_success('branch {0}'.format(self.BRANCH_1))
    utils_lib.gl_expect_error('branch -d {0}'.format(self.BRANCH_1))
    utils_lib.gl_expect_success('branch {0}'.format(self.BRANCH_2))
    utils_lib.gl_expect_success(
        'branch -d {0}'.format(self.BRANCH_1), pre_cmd='echo "n"')
    utils_lib.gl_expect_success(
        'branch -d {0}'.format(self.BRANCH_1), pre_cmd='echo "y"')
    if self.BRANCH_1 in utils_lib.gl_expect_success('branch')[0]:
      self.fail()


class TestDiff(TestEndToEnd):

  TRACKED_FP = 't_fp'
  UNTRACKED_FP = 'u_fp'

  def setUp(self):
    super(TestDiff, self).setUp()
    utils_lib.write_file(self.TRACKED_FP)
    utils_lib.gl_expect_success(
        'commit {0} -msg"commit"'.format(self.TRACKED_FP))
    utils_lib.write_file(self.UNTRACKED_FP)

  def test_empty_diff(self):
    if 'Nothing to diff' not in utils_lib.gl_expect_success('diff')[0]:
      self.fail()

  def test_diff_nonexistent_fp(self):
    _, err = utils_lib.gl_expect_error('diff {0}'.format('file'))
    if 'non-existent' not in err:
      self.fail()

  def test_basic_diff(self):
    utils_lib.write_file(self.TRACKED_FP, contents='contents')
    out1 = utils_lib.gl_expect_success('diff')[0]
    if '+contents' not in out1:
      self.fail()
    out2 = utils_lib.gl_expect_success('diff {0}'.format(self.TRACKED_FP))[0]
    if '+contents' not in out2:
      self.fail()
    self.assertEqual(out1, out2)


# TODO(sperezde): add more performance tests to check that we're not dropping
# the ball: We should try to keep Gitless's performance reasonably close to
# Git's.
class TestPerformance(TestEndToEnd):

  FPS_QTY = 10000

  def setUp(self):
    super(TestPerformance, self).setUp()
    for i in range(0, self.FPS_QTY):
      fp = 'f' + str(i)
      utils_lib.write_file(fp, fp)

  def test_status_performance(self):
    """Assert that gl status is not too slow."""

    def assert_status_performance():
      # The test fails if gl status takes more than 100 times
      # the time git status took.
      MAX_TOLERANCE = 100

      t = time.time()
      utils_lib.gl_call('status')
      gl_t = time.time() - t

      t = time.time()
      utils_lib.git_call('status')
      git_t = time.time() - t

      self.assertTrue(
          gl_t < git_t*MAX_TOLERANCE,
          msg='gl_t {0}, git_t {1}'.format(gl_t, git_t))

    # All files are untracked.
    assert_status_performance()
    # Track all files, repeat.
    logging.info('Doing a massive git add, this might take a while')
    utils_lib.git_call('add .')
    logging.info('Done')
    assert_status_performance()

  def test_branch_switch_performance(self):
    """Assert that switching branches is not too slow."""
    MAX_TOLERANCE = 100

    # Temporary hack until we get stuff working smoothly when the repo has no
    # commits.
    utils_lib.gl_call('commit -m"commit" f1')

    t = time.time()
    utils_lib.gl_call('branch develop')
    gl_t = time.time() - t

    # go back to previous state.
    utils_lib.gl_call('branch master')

    # do the same for git.
    t = time.time()
    utils_lib.git_call('branch gitdev')
    utils_lib.git_call('stash save --all')
    utils_lib.git_call('checkout gitdev')
    git_t = time.time() - t

    self.assertTrue(
        gl_t < git_t*MAX_TOLERANCE,
        msg='gl_t {0}, git_t {1}'.format(gl_t, git_t))


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = utils
# Gitless - a version control system built on top of Git.
# Licensed under GNU GPL, version 2.

"""Utility library for tests."""


import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class TestBase(unittest.TestCase):

  def setUp(self, prefix_for_tmp_repo):
    """Creates temporary dir and cds to it."""
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    self.path = tempfile.mkdtemp(prefix=prefix_for_tmp_repo)
    logging.debug('Created temporary directory {0}'.format(self.path))
    os.chdir(self.path)

  def tearDown(self):
    """Removes the temporary dir."""
    shutil.rmtree(self.path)
    logging.debug('Removed dir {0}'.format(self.path))

  # Python 2/3 compatibility.
  def assertItemsEqual(self, actual, expected, msg=None):
    try:
      return super(TestBase, self).assertItemsEqual(actual, expected, msg=msg)
    except AttributeError:
      try:
        return super(TestBase, self).assertCountEqual(actual, expected, msg=msg)
      except AttributeError:
        return self.assertEqual(sorted(actual), sorted(expected), msg=msg)


def write_file(fp, contents=None):
  _x_file('w', fp, contents=contents)


def append_to_file(fp, contents=None):
  _x_file('a', fp, contents=contents)


def read_file(fp):
  f = open(fp, 'r')
  ret = f.read()
  f.close()
  return ret


def gl_call(cmd, expected_ret_code=0, pre_cmd=None):
  return _call('gl', cmd, expected_ret_code=expected_ret_code, pre_cmd=pre_cmd)


def git_call(cmd, expected_ret_code=0):
  return _call('git', cmd, expected_ret_code=expected_ret_code)


def gl_expect_success(cmd, pre_cmd=None):
  return gl_call(cmd, pre_cmd=pre_cmd)


def gl_expect_error(cmd, pre_cmd=None):
  return gl_call(cmd, expected_ret_code=1, pre_cmd=pre_cmd)


def set_test_config():
  git_call('config user.name \"test\"')
  git_call('config user.email \"test@test.com\"')


# Private functions.


def _x_file(x, fp, contents=None):
  if not contents:
    contents = fp
  dirs, _ = os.path.split(fp)
  if dirs and not os.path.exists(dirs):
    os.makedirs(dirs)
  f = open(fp, x)
  f.write(contents)
  f.close()


def _call(cmd, subcmd, expected_ret_code=0, pre_cmd=None):
  logging.debug('Calling {0} {1}'.format(cmd, subcmd))
  if pre_cmd:
    pre_cmd = pre_cmd + '|'
  else:
    pre_cmd = ''
  p = subprocess.Popen(
      '{0} {1} {2}'.format(pre_cmd, cmd, subcmd), stdout=subprocess.PIPE,
      stderr=subprocess.PIPE, shell=True)
  out, err = p.communicate()
  # Python 2/3 compatibility.
  if sys.version > "3":
    # Disable pylint's no-member error. 'str' has no 'decode' member in
    # python 3.
    # pylint: disable=E1101
    out = out.decode('utf-8')
    err = err.decode('utf-8')
  logging.debug('Out is \n{0}'.format(out))
  if err:
    logging.debug('Err is \n{0}'.format(err))
  if p.returncode != expected_ret_code:
    raise Exception(
        'Obtained ret code {0} doesn\'t match the expected {1}.\nOut of the '
        'cmd was:\n{2}\nErr of the cmd was:\n{3}\n'.format(
            p.returncode, expected_ret_code, out, err))
  return out, err

########NEW FILE########
