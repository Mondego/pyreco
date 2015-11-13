__FILENAME__ = constants
REGIONS_ID = 'rubocop_remark_regions'
SETTINGS_FILE = 'RuboCop.sublime-settings'

########NEW FILE########
__FILENAME__ = file_tools
# Sublime RuboCop plugin
#
# Author: Patrick Derichs (patderichs@gmail.com)
# License: MIT (http://opensource.org/licenses/MIT)

import os
import pipes

class FileTools(object):
  """Simple file operations"""
  @staticmethod
  def is_executable(path):
    return os.path.isfile(path) and os.access(path, os.X_OK)

  @staticmethod
  def quote(path):
    # TODO: Use shlex.quote as soon as a newer python version is available.
    return pipes.quote(path)

  @staticmethod
  def is_ruby_file(path):
    name, ext = os.path.splitext(path)
    if ext == '.rb': 
      return True
    return False

########NEW FILE########
__FILENAME__ = rubocop_command
# Sublime RuboCop plugin
#
# Author: Patrick Derichs (patderichs@gmail.com)
# License: MIT (http://opensource.org/licenses/MIT)

import sublime_plugin
import sublime
import os
import tempfile

if sublime.version() >= '3000':
  from RuboCop.file_tools import FileTools
  from RuboCop.rubocop_runner import RubocopRunner
  from RuboCop.constants import *
  from RuboCop.rubocop_listener import RubocopEventListener
else:
  from file_tools import FileTools
  from rubocop_runner import RubocopRunner
  from constants import *
  from rubocop_listener import RubocopEventListener

# Base class for all RuboCop commands
class RubocopCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    self.load_config()

  def load_config(self):
    s = sublime.load_settings(SETTINGS_FILE)
    use_rvm = s.get('check_for_rvm')
    use_rbenv = s.get('check_for_rbenv')
    self.rubocop_command = s.get('rubocop_command')
    rvm_auto_ruby_path = s.get('rvm_auto_ruby_path')
    rbenv_path = s.get('rbenv_path')

    self.runner = RubocopRunner(use_rbenv, use_rvm, self.rubocop_command, rvm_auto_ruby_path, rbenv_path)
    self.rubocop_command = self.runner.command_string() + ' {options} {path}'

  def used_options(self):
    return ''

  def command_with_options(self):
    return self.rubocop_command.replace('{options}', self.used_options())

  def run_rubocop_on(self, path, file_list=False):
    if not path:
      return

    if not file_list:
      # Single item to check.
      quoted_file_path = FileTools.quote(path)
      working_dir = os.path.dirname(quoted_file_path)
    else:
      # Multiple files to check.
      working_dir = '.'
      quoted_file_path = ''
      for file in path:
        quoted_file_path += FileTools.quote(file) + ' '

    cop_command = self.command_with_options()
    rubocop_cmd = cop_command.replace('{path}', quoted_file_path)

    self.run_shell_command(rubocop_cmd, working_dir)

  def run_shell_command(self, command, working_dir='.'):
    if not command:
      return

    self.view.window().run_command('exec', {
      'cmd': [command],
      'shell': True,
      'working_dir': working_dir,
      'file_regex': r"^([^:]+):([0-9]*)",
    })

# --------- General rubocop commands -------------

# Toggles mark_issues_in_view setting
class RubocopPauseToggleCommand(RubocopCommand):
  def run(self, edit):
    super(RubocopPauseToggleCommand, self).run(edit)
    self.pause()

  def pause(self):
    s = sublime.load_settings(SETTINGS_FILE)
    mark_issues_in_view = s.get('mark_issues_in_view')
    s.set('mark_issues_in_view', not mark_issues_in_view)
    sublime.save_settings(SETTINGS_FILE)
    RubocopEventListener.instance().update_marks()

# Calling autocorrect on the current file
class RubocopAutoCorrectCommand(RubocopCommand):
  def run(self, edit):
    super(RubocopAutoCorrectCommand, self).run(edit)

    cancel_op = self.warning_msg()
    if cancel_op:
      return

    view = self.view
    path = view.file_name()
    quoted_file_path = FileTools.quote(path)

    if view.is_read_only():
      sublime.message_dialog('RuboCop: Unable to run auto correction on a read only buffer.')
      return

    # Inform user about unsaved contents of current buffer
    if view.is_dirty():
      warn_msg = 'RuboCop: The curent buffer is modified. Save the file and continue?'
      cancel_op = not sublime.ok_cancel_dialog(warn_msg)

    if cancel_op:
      return
    else:
      view.run_command('save')

    RubocopEventListener.instance().clear_marks(view)

    # Copy the current file to a temp file
    content = view.substr(sublime.Region(0, view.size()))
    f = tempfile.NamedTemporaryFile()

    try:
      self.write_to_file(f, content, view)
      f.flush()

      # Create path for possible config file in the source directory
      quoted_file_path = FileTools.quote(path)
      config_opt = '-c ' + os.path.dirname(quoted_file_path) + '/.rubocop.yml'
      print(config_opt)

      # Run rubocop with auto-correction on temp file
      self.runner.run(f.name, '-a ' + config_opt)

      # Read contents of file
      f.seek(0)
      content = self.read_from_file(f, view)

      # Overwrite buffer contents
      rgn = sublime.Region(0, view.size())
      view.replace(edit, rgn, content)
    finally:
      # TempFile will be deleted here
      f.close()

    sublime.status_message('RuboCop: Auto correction done.')

  def warning_msg(self):
    cancel_op = False
    s = sublime.load_settings(SETTINGS_FILE)
    show_warning = s.get('show_auto_correct_warning')
    if show_warning:
      cancel_op = not sublime.ok_cancel_dialog("""
Attention! You are about to run auto correction on the current file. 

The contents of the current buffer will be overwritten by RuboCop. Afterwards, you need to save these changes manually.

Do you want to continue?

(You can disable this message in the settings.)
      """)

    return cancel_op

  def write_to_file(self, f, content, view):
    if sublime.version() < '3000':
      f.write(content)
      return
    f.write(bytes(content, view.encoding()))

  def read_from_file(self, f, view):
    if sublime.version() < '3000':
      return f.read()
    return f.read().decode(view.encoding())

# Runs a check on the currently opened file.
class RubocopCheckSingleFileCommand(RubocopCommand):
  def run(self, edit):
    super(RubocopCheckSingleFileCommand, self).run(edit)
    file_path = self.view.file_name()
    self.run_rubocop_on(file_path)

# Runs a check on the currently opened project.
class RubocopCheckProjectCommand(RubocopCommand):
  def run(self, edit):
    super(RubocopCheckProjectCommand, self).run(edit)
    folders = self.view.window().folders()
    if len(folders) > 0:
      self.run_rubocop_on(folders[0])
    else:
      sublime.status_message('RuboCop: No project folder available.')

# Runs a check on the folder of the current file.
class RubocopCheckFileFolderCommand(RubocopCommand):
  def run(self, edit):
    super(RubocopCheckFileFolderCommand, self).run(edit)
    file_path = self.view.file_name()
    project_folder = os.path.dirname(file_path)
    self.run_rubocop_on(project_folder)

# Runs a check on all open files.
class RubocopCheckOpenFilesCommand(RubocopCommand):
  def run(self, edit):
    super(RubocopCheckOpenFilesCommand, self).run(edit)
    files = self.open_ruby_files()
    if len(files) > 0:
      self.run_rubocop_on(files, True)
    else:
      sublime.status_message('RuboCop: There are no Ruby files to check.')

  def open_ruby_files(self):
    files = []
    views = self.view.window().views()
    for vw in views:
      file_path = vw.file_name()
      if FileTools.is_ruby_file(file_path):
        files.append(file_path)
    return files


# --------- Lint Cops -------------

# Runs a check on the current file (only using lint cops)
class RubocopCheckCurrentFileOnlyWithLintCopsCommand(RubocopCheckSingleFileCommand):
  def used_options(self):
    return '-l'

# Runs a check on the current project (only using lint cops)
class RubocopCheckProjectOnlyWithLintCopsCommand(RubocopCheckProjectCommand):
  def used_options(self):
    return '-l'

# Runs a check on the current project (only using lint cops)
class RubocopCheckFileFolderOnlyWithLintCopsCommand(RubocopCheckFileFolderCommand):
  def used_options(self):
    return '-l'

# Runs a check on all open files (only using lint cops)
class RubocopCheckOpenFilesOnlyWithLintCopsCommand(RubocopCheckOpenFilesCommand):
  def used_options(self):
    return '-l'

# --------- Rails Cops -------------

# Runs a check on the current file (Rails)
class RubocopCheckCurrentFileRailsCommand(RubocopCheckSingleFileCommand):
  def used_options(self):
    return '-R'

# Runs a check on the current project (Rails)
class RubocopCheckProjectRailsCommand(RubocopCheckProjectCommand):
  def used_options(self):
    return '-R'

# Runs a check on the current project (Rails)
class RubocopCheckFileFolderRailsCommand(RubocopCheckFileFolderCommand):
  def used_options(self):
    return '-R'

# Runs a check on all open files (Rails)
class RubocopCheckOpenFilesRailsCommand(RubocopCheckOpenFilesCommand):
  def used_options(self):
    return '-R'

########NEW FILE########
__FILENAME__ = rubocop_listener
# Sublime RuboCop plugin
#
# Author: Patrick Derichs (patderichs@gmail.com)
# License: MIT (http://opensource.org/licenses/MIT)

import sublime
import sublime_plugin
import locale
import re
import os

if sublime.version() >= '3000':
  from RuboCop.file_tools import FileTools
  from RuboCop.rubocop_runner import RubocopRunner
  from RuboCop.constants import *
else:
  from file_tools import FileTools
  from rubocop_runner import RubocopRunner
  from constants import *

# Event listener to provide on the fly checks when saving a ruby file.
class RubocopEventListener(sublime_plugin.EventListener):
  listener_instance = None

  def __init__(self):
    super(RubocopEventListener, self).__init__()
    self.file_remark_dict = {}
    RubocopEventListener.listener_instance = self
    if sublime.version() >= '3000':
      sublime.set_timeout_async(self.update_marks, 2)

  @classmethod
  def instance(cls):
    return cls.listener_instance

  def get_current_file_dict(self, view):
    if not (view.file_name() in self.file_remark_dict.keys()):
      return None

    return self.file_remark_dict[view.file_name()]

  def clear_marks(self, view):
    dct = self.get_current_file_dict(view)
    if dct:
      dct.clear()
    view.erase_regions(REGIONS_ID)

  def update_marks(self):
    for wnd in sublime.windows():
      for vw in wnd.views():
        self.do_in_file_check(vw)

  def line_no_of_cop_result(self, file_name, result):
    res = result.decode(locale.getpreferredencoding())
    reg_result = re.search(r"^([^:]+):([0-9]*):.*:(.*)", res)
    if reg_result:
      return reg_result.group(2), reg_result.group(3).strip()
    return None, None

  def set_marks_by_results(self, view, cop_results):
    lines = []
    path = view.file_name()
    base_file = os.path.basename(path)
    view_dict = self.get_current_file_dict(view)
    if not view_dict:
      view_dict = {}
      self.file_remark_dict[path] = view_dict
    for result in cop_results:
      line_no, message = self.line_no_of_cop_result(base_file, result)
      if line_no:
        ln = int(line_no) - 1
        view_dict[ln] = message
        line = view.line(view.text_point(ln, 0))
        lines.append(sublime.Region(line.begin(), line.end()))
    view.add_regions(REGIONS_ID, lines, 'invalid', 'circle')

  def run_rubocop(self, path):
    s = sublime.load_settings(SETTINGS_FILE)
    use_rvm = s.get('check_for_rvm')
    use_rbenv = s.get('check_for_rbenv')
    cmd = s.get('rubocop_command')
    rvm_path = s.get('rvm_auto_ruby_path')
    rbenv_path = s.get('rbenv_path')
    runner = RubocopRunner(use_rbenv, use_rvm, cmd, rvm_path, rbenv_path)
    output = runner.run(path, '--format emacs').splitlines()
    return output

  def mark_issues(self, view, mark):
    self.clear_marks(view)
    if mark:
      results = self.run_rubocop(view.file_name())
      self.set_marks_by_results(view, results)

  def do_in_file_check(self, view):
    if not FileTools.is_ruby_file(view.file_name()):
      return
    mark = sublime.load_settings(SETTINGS_FILE).get('mark_issues_in_view')
    self.mark_issues(view, mark)

  def on_post_save(self, view):
    if sublime.version() >= '3000':
      # To improve performance, we use the async method within ST3
      return

    self.do_in_file_check(view)

  def on_post_save_async(self, view):
    self.do_in_file_check(view)

  def on_load_async(self, view):
    self.do_in_file_check(view)

  def on_selection_modified(self, view):
    curr_sel = view.sel()
    if curr_sel:
      view_dict = self.get_current_file_dict(view)
      if not view_dict:
        return
      first_sel = curr_sel[0]
      row, col = view.rowcol(first_sel.begin())
      if row in view_dict.keys():
        sublime.status_message('RuboCop: {0}'.format(view_dict[row]))
      else:
        sublime.status_message('')

########NEW FILE########
__FILENAME__ = rubocop_runner
# Sublime RuboCop plugin
#
# Initial Author: Patrick Derichs (patderichs@gmail.com)
# License: MIT (http://opensource.org/licenses/MIT)

import os
import subprocess

RVM_DEFAULT_PATH = '~/.rvm/bin/rvm-auto-ruby'
RBENV_DEFAULT_PATH = '~/.rbenv/bin/rbenv'

class RubocopRunner(object):
  """This class takes care of the rubocop location and its execution"""
  def __init__(self, use_rbenv, use_rvm, custom_rubocop_cmd, rvm_auto_ruby_path=None, rbenv_path=None):
    self.use_rvm = use_rvm
    self.use_rbenv = use_rbenv
    self.custom_rubocop_cmd = custom_rubocop_cmd

    if rvm_auto_ruby_path is None:
      self.rvm_auto_ruby_path = RVM_DEFAULT_PATH
    else:
      self.rvm_auto_ruby_path = rvm_auto_ruby_path

    if rbenv_path is None:
      self.rbenv_path = RBENV_DEFAULT_PATH
    else:
      self.rbenv_path = rbenv_path

  def load_cmd_prefix(self):
    self.cmd_prefix = ''
    if not self.load_rvm():
      self.load_rbenv()

  def load_rvm(self):
    if self.use_rvm:
      rvm_cmd = os.path.expanduser(self.rvm_auto_ruby_path)
      self.cmd_prefix = rvm_cmd + ' -S'
      return True
    return False

  def load_rbenv(self):
    if self.use_rbenv:
      rbenv_cmd = os.path.expanduser(self.rbenv_path)
      self.cmd_prefix = rbenv_cmd + ' exec'
      return True
    return False

  def run(self, path, options=''):
    call_list = self.command_list()
    call_list.extend(options.split())
    call_list.extend(path.split())

    p = subprocess.Popen(call_list,
      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    return out

  def command_list(self):
    if not self.custom_rubocop_cmd or self.custom_rubocop_cmd is '':
      self.load_cmd_prefix()
      cmd = self.cmd_prefix + ' rubocop'
    else:
      cmd = self.custom_rubocop_cmd

    return cmd.split()

  def command_string(self):
    return ' '.join(self.command_list())

########NEW FILE########
__FILENAME__ = rubocop_runner_tests
# These are some unit tests for rubocop_runner (one of the main
# actors of that plugin). They are commented out since ST is 
# parsing that file on startup and it causes a lot of warnings
# in the ST console. I will comment that in as soon as we got
# a better location for that file or make ST ignore it.

# import unittest

# from rubocop_runner import RubocopRunner

# RVM_PATH = '/.rvm/bin/rvm-auto-ruby'
# RBENV_PATH = '/.rbenv/bin/rbenv'

# class RuboCopRunnerTests(unittest.TestCase):
#   def test_init_with_rbenv(self):
#     runner = RubocopRunner(True, False, 'abc')
#     self.assertTrue(runner.use_rbenv)
#     self.assertFalse(runner.use_rvm)
#     self.assertEqual(runner.custom_rubocop_cmd, 'abc')

#   def test_init_with_rvm(self):
#     runner = RubocopRunner(False, True, 'xyz')
#     self.assertFalse(runner.use_rbenv)
#     self.assertTrue(runner.use_rvm)
#     self.assertEqual(runner.custom_rubocop_cmd, 'xyz')

#   def test_load_cmd_prefix_rbenv(self):
#     runner = RubocopRunner(True, False, 'xyz')
#     prefix = runner.load_cmd_prefix()
#     self.assertTrue(runner.cmd_prefix.endswith(RBENV_PATH + ' exec'))

#   def test_load_cmd_prefix_rvm(self):
#     runner = RubocopRunner(False, True, 'xyz')
#     prefix = runner.load_cmd_prefix()
#     self.assertTrue(runner.cmd_prefix.endswith(RVM_PATH + ' -S'))

#   def test_load_cmd_prefix_no_prefix(self):
#     runner = RubocopRunner(False, False, '')
#     prefix = runner.load_cmd_prefix()
#     self.assertEqual(runner.cmd_prefix, '')

#   def test_load_rvm_use_rvm(self):
#     runner = RubocopRunner(False, True, '')
#     self.assertTrue(runner.load_rvm())

#   def test_load_rvm_not_using_rvm(self):
#     runner = RubocopRunner(True, False, '')
#     self.assertFalse(runner.load_rvm())

#   def test_load_rbenv_use_rbenv(self):
#     runner = RubocopRunner(True, False, '')
#     self.assertTrue(runner.load_rbenv())

#   def test_load_rbenv_not_using_rbenv(self):
#     runner = RubocopRunner(False, True, '')
#     self.assertFalse(runner.load_rbenv())

#   def test_command_list_rvm(self):
#     runner = RubocopRunner(False, True, '')
#     lst = runner.command_list()
#     self.assertEqual(len(lst), 3)
#     self.assertTrue(lst[0].endswith(RVM_PATH))
#     self.assertEqual(lst[1], '-S')
#     self.assertEqual(lst[2], 'rubocop')

#   def test_command_list_rbenv(self):
#     runner = RubocopRunner(True, False, '')
#     lst = runner.command_list()
#     self.assertEqual(len(lst), 3)
#     self.assertTrue(lst[0].endswith(RBENV_PATH))
#     self.assertEqual(lst[1], 'exec')
#     self.assertEqual(lst[2], 'rubocop')

#   def test_command_list_custom(self):
#     runner = RubocopRunner(False, False, '666')
#     self.assertEqual(runner.command_list(), ['666'])
    
#   # TODO: Test run method

# def main():
#   unittest.main()

# if __name__ == '__main__':
#   main()

########NEW FILE########
