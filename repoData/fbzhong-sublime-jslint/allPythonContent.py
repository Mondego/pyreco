__FILENAME__ = asyncprocess
import os
import thread
import subprocess
import functools
import time
import sublime

class AsyncProcess(object):
  def __init__(self, cmd, listener):
    self.cmd = cmd
    self.listener = listener
    #print "DEBUG_EXEC: " + str(self.cmd)
    self.proc = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if self.proc.stdout:
      thread.start_new_thread(self.read_stdout, ())

    if self.proc.stderr:
      thread.start_new_thread(self.read_stderr, ())

    thread.start_new_thread(self.poll, ())

  def poll(self):
    while True:
      if self.proc.poll() != None:
        sublime.set_timeout(functools.partial(self.listener.proc_terminated, self.proc), 0)
        break
      time.sleep(0.1)

  def read_stdout(self):
    while True:
      data = os.read(self.proc.stdout.fileno(), 2**15)
      if data != "":
        sublime.set_timeout(functools.partial(self.listener.append_data, self.proc, data), 0)
      else:
        self.proc.stdout.close()
        self.listener.is_running = False
        break

  def read_stderr(self):
    while True:
      data = os.read(self.proc.stderr.fileno(), 2**15)
      if data != "":
        sublime.set_timeout(functools.partial(self.listener.append_data, self.proc, data), 0)
      else:
        self.proc.stderr.close()
        self.listener.is_running = False
        break

########NEW FILE########
__FILENAME__ = jslint
import os
import re
import sublime
import sublime_plugin
from statusprocess import *
from asyncprocess import *

RESULT_VIEW_NAME = 'jslint_result_view'
SETTINGS_FILE = "sublime-jslint.sublime-settings"

class ShowJslintResultCommand(sublime_plugin.WindowCommand):
  """show jslint result"""
  def run(self):
    self.window.run_command("show_panel", {"panel": "output."+RESULT_VIEW_NAME})

class JslintCommand(sublime_plugin.WindowCommand):
  def run(self):
    s = sublime.load_settings(SETTINGS_FILE)

    file_path = self.window.active_view().file_name()
    file_name = os.path.basename(file_path)

    self.debug = s.get('debug', False)
    self.buffered_data = ''
    self.file_path = file_path
    self.file_name = file_name
    self.is_running = True
    self.tests_panel_showed = False
    self.ignored_error_count = 0
    self.ignore_errors = s.get('ignore_errors', [])
    self.use_node_jslint = s.get('use_node_jslint', False)

    self.init_tests_panel()

    if (self.use_node_jslint):
      cmd = 'jslint ' + s.get('node_jslint_options', '') + ' "' + file_path + '"'
    else:
      if len(s.get('jslint_jar', '')) > 0:
        jslint_jar = s.get('jslint_jar')
      else:
        jslint_jar = sublime.packages_path() + '/sublime-jslint/jslint4java-2.0.5-SNAPSHOT.jar'
      cmd = 'java -jar "' + jslint_jar + '" ' + s.get('jslint_options', '') + ' "' + file_path + '"'

    if self.debug:
      print "DEBUG: " + str(cmd)

    AsyncProcess(cmd, self)
    StatusProcess('Starting JSLint for file ' + file_name, self)

    JsLintEventListener.disabled = True

  def init_tests_panel(self):
    if not hasattr(self, 'output_view'):
      self.output_view = self.window.get_output_panel(RESULT_VIEW_NAME)
      self.output_view.set_name(RESULT_VIEW_NAME)
    self.clear_test_view()
    self.output_view.settings().set("file_path", self.file_path)

  def show_tests_panel(self):
    if self.tests_panel_showed:
      return
    self.window.run_command("show_panel", {"panel": "output."+RESULT_VIEW_NAME})
    self.tests_panel_showed = True

  def clear_test_view(self):
    self.output_view.set_read_only(False)
    edit = self.output_view.begin_edit()
    self.output_view.erase(edit, sublime.Region(0, self.output_view.size()))
    self.output_view.end_edit(edit)
    self.output_view.set_read_only(True)

  def append_data(self, proc, data, end=False):
    self.buffered_data = self.buffered_data + data.decode("utf-8")
    data = self.buffered_data.replace(self.file_path, self.file_name).replace('\r\n', '\n').replace('\r', '\n')

    if end == False:
      rsep_pos = data.rfind('\n')
      if rsep_pos == -1:
        # not found full line.
        return
      self.buffered_data = data[rsep_pos+1:]
      data = data[:rsep_pos+1]

    # ignore error.
    text = data
    if (len(self.ignore_errors) > 0) and (not self.use_node_jslint):
      text = ''
      for line in data.split('\n'):
        if len(line) == 0:
          continue
        ignored = False
        for rule in self.ignore_errors:
          if re.search(rule, line):
            ignored = True
            self.ignored_error_count += 1
            if self.debug:
              print "text match line "
              print "rule = " + rule
              print "line = " + line
              print "---------"
            break
        if ignored == False:
          text += line + '\n'


    self.show_tests_panel()
    selection_was_at_end = (len(self.output_view.sel()) == 1 and self.output_view.sel()[0] == sublime.Region(self.output_view.size()))
    self.output_view.set_read_only(False)
    edit = self.output_view.begin_edit()
    self.output_view.insert(edit, self.output_view.size(), text)

    if end and not self.use_node_jslint:
      text = '\njslint: ignored ' + str(self.ignored_error_count) + ' errors.\n'
      self.output_view.insert(edit, self.output_view.size(), text)

    # if selection_was_at_end:
    #   self.output_view.show(self.output_view.size())
    self.output_view.end_edit(edit)
    self.output_view.set_read_only(True)

    # if end:
    #   self.output_view.run_command("goto_line", {"line": 1})

  def update_status(self, msg, progress):
    sublime.status_message(msg + " " + progress)

  def proc_terminated(self, proc):
    if proc.returncode == 0:
      msg = self.file_name + ' lint free!'
    else:
      msg = ''
    self.append_data(proc, msg, True)

    JsLintEventListener.disabled = False


class JsLintEventListener(sublime_plugin.EventListener):
  """jslint event"""
  disabled = False
  def __init__(self):
    self.previous_resion = None
    self.file_view = None

  def on_post_save(self, view):
    s = sublime.load_settings(SETTINGS_FILE)
    if s.get('run_on_save', False) == False:
      return

    if view.file_name().endswith('.js') == False:
      return

    # run jslint.
    sublime.active_window().run_command("jslint")

  def on_deactivated(self, view):
    if view.name() != RESULT_VIEW_NAME:
      return
    self.previous_resion = None

    if self.file_view:
      self.file_view.erase_regions(RESULT_VIEW_NAME)

  def on_selection_modified(self, view):
    if JsLintEventListener.disabled:
      return
    if view.name() != RESULT_VIEW_NAME:
      return
    region = view.line(view.sel()[0])
    s = sublime.load_settings(SETTINGS_FILE)

    # make sure call once.
    if self.previous_resion == region:
      return
    self.previous_resion = region

    # extract line from jslint result.
    if (s.get('use_node_jslint', False)):
      pattern_position = "\\/\\/ Line (\d+), Pos (\d+)$"
      text = view.substr(region)
      text = re.findall(pattern_position, text)
      if len(text) > 0:
        line = int(text[0][0])
        col = int(text[0][1])
    else:
      text = view.substr(region).split(':')
      if len(text) < 4 or text[0] != 'jslint' or re.match('\d+', text[2]) == None or re.match('\d+', text[3]) == None:
          return
      line = int(text[2])
      col = int(text[3])

    # hightligh view line.
    view.add_regions(RESULT_VIEW_NAME, [region], "comment")

    # find the file view.
    file_path = view.settings().get('file_path')
    window = sublime.active_window()
    file_view = None
    for v in window.views():
      if v.file_name() == file_path:
        file_view = v
        break
    if file_view == None:
      return

    self.file_view = file_view
    window.focus_view(file_view)
    file_view.run_command("goto_line", {"line": line})
    file_region = file_view.line(file_view.sel()[0])

    # highlight file_view line
    file_view.add_regions(RESULT_VIEW_NAME, [file_region], "string")



########NEW FILE########
__FILENAME__ = statusprocess
import thread
import functools
import time
import sublime

class StatusProcess(object):
  def __init__(self, msg, listener):
    self.msg = msg
    self.listener = listener
    thread.start_new_thread(self.run_thread, ())

  def run_thread(self):
    progress = ""
    while True:
      if self.listener.is_running:
        if len(progress) >= 10:
          progress = ""
        progress += "."
        sublime.set_timeout(functools.partial(self.listener.update_status, self.msg, progress), 0)
        time.sleep(0.1)
      else:
        break

########NEW FILE########
