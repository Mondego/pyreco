__FILENAME__ = check_ruby_syntax
import sublime, sublime_plugin
import subprocess
import re

class CheckRubySyntax(sublime_plugin.TextCommand):
  def run(self, edit):
    file_name = self.view.file_name()

    check_syntax_command = subprocess.Popen(["ruby","-wc",file_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = check_syntax_command.communicate()

    if re.match(r"Syntax OK", out):
      sublime.message_dialog("Syntax OK")
    else:
      sublime.message_dialog(out)

########NEW FILE########
__FILENAME__ = close_other_tabs
import sublime, sublime_plugin

class CloseOtherTabs(sublime_plugin.TextCommand):
  def run(self, edit):
    window = self.view.window()
    group_index, view_index = window.get_view_index(self.view)
    window.run_command("close_others_by_index", { "group": group_index, "index": view_index})

########NEW FILE########
__FILENAME__ = coffeescript
import sublime, sublime_plugin, subprocess, os


# Run the `coffee` command synchronously, sending `input` on stdin.
def coffee(extra_args, input):
    command = ['coffee', '--stdio']
    command.extend(extra_args)

    try:
        process = subprocess.Popen(command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        stdin, stdout = process.communicate(input)
        exit_code = process.wait()

        return exit_code, stdin, stdout

    except OSError as (errno, strerror):
        if errno == 2:
            path = os.environ['PATH']
            message = "`coffee` couldn't be found on your $PATH:\n" + path
            return -1, None, message
        else:
            raise


# Base class for CoffeeScript commands
class CoffeeCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        syntax_filename = os.path.basename(self.view.settings().get('syntax'))
        return syntax_filename == 'CoffeeScript.tmLanguage'

    def _show_in_panel(self, output):
        window = self.view.window()
        v = window.get_output_panel('coffee_output')
        edit = v.begin_edit()
        v.insert(edit, 0, output)
        v.end_edit(edit)

        window.run_command("show_panel", {"panel": "output.coffee_output"})


# Compile the selected CoffeeScript and display it in a new window.  If no code
# is selected, compile the entire file.
class CompileAndDisplayJs(CoffeeCommand):
    def run(self, edit):
        window = self.view.window()

        for region in self.view.sel():
            if region.empty():
                region = sublime.Region(0, self.view.size())

            code = self.view.substr(region)

            exit_code, compiled_code, error = coffee(
                ['--compile', '--bare'], code)

            if exit_code == 0:
                v = window.new_file()
                v.set_name("Compiled JavaScript")
                v.set_scratch(True)
                v.set_syntax_file('Packages/JavaScript/JavaScript.tmLanguage')

                edit = v.begin_edit()
                v.insert(edit, 0, compiled_code)
                v.end_edit(edit)

            else:
                self._show_in_panel(error)
                return


# Run the selected CoffeeScript and display the results in the output panel.  If
# no code is selected, run the entire file.
class RunCoffeeScript(CoffeeCommand):
    def run(self, edit):
        window = self.view.window()

        for region in self.view.sel():
            if region.empty():
                region = sublime.Region(0, self.view.size())

            code = self.view.substr(region)

            exit_code, output, error = coffee([], code)

            if exit_code == 0:
                self._show_in_panel(output)
            else:
                self._show_in_panel(error)
                return

########NEW FILE########
__FILENAME__ = copy_path_to_clipboard
import sublime, sublime_plugin
import os

class CopyPathToClipboard(sublime_plugin.TextCommand):
  def run(self, edit):
    line_number, column = self.view.rowcol(self.view.sel()[0].begin())
    line_number += 1
    sublime.set_clipboard(self.view.file_name() + ":" + str(line_number))

########NEW FILE########
__FILENAME__ = open_coffee_file
import sublime
import sublime_plugin
import os
import re

class OpenCoffeeTwinCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.views = []
    window = self.window
    current_file_path = self.window.active_view().file_name()

    if current_file_path.find("/spec/") > 0:
      twin_path = self.app_twin_path(current_file_path)
    else:
      twin_path = self.spec_twin_path(current_file_path)

    if os.path.exists(twin_path) :
      window.open_file(twin_path)
    else :
      if sublime.ok_cancel_dialog("Create file: "+twin_path, "Yeah, fuck it"):
        open(twin_path,"w").close()
        window.open_file(twin_path)
      else:
        sublime.status_message("Could not find " + twin_path)

  def app_twin_path(self, spec_path):
    file_path = re.search(r'scripts(/.*)', spec_path).group(1).replace("_spec.coffee", ".coffee")
    return self.find_app_directory() + file_path

  def find_app_directory(self):
    return self.find_directory([
      "/content/javascripts",
      "/app/assets/javascripts",
      "/app/coffeescripts"
    ])

  def spec_twin_path(self, app_path):
    file_path = re.search(r'scripts(/.*)', app_path).group(1).replace(".coffee", "_spec.coffee")
    return self.find_spec_directory() + file_path

  def find_spec_directory(self):
    return self.find_directory([
      "/spec/coffeescripts",
      "/spec/javascripts",
      "/spec/assets/javascripts"
    ])

  def find_directory(self, candidates):
    root_path = self.window.folders()[0]

    for candidate in candidates:
      print root_path + candidate
      if os.path.exists(root_path + candidate):
        return root_path + candidate

    raise Exception("Unable to find coffeescripts path in " + ','.join(map(str, candidates)))


########NEW FILE########
__FILENAME__ = open_javascript_file
import sublime
import sublime_plugin
import os
import re

class OpenJavascriptTwinCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.views = []
    window = self.window
    current_file_path = self.window.active_view().file_name()

    if current_file_path.find("/spec/") > 0:
      twin_path = self.app_twin_path(current_file_path)
    else:
      twin_path = self.spec_twin_path(current_file_path)

    if os.path.exists(twin_path) :
      window.open_file(twin_path)
    else :
      if sublime.ok_cancel_dialog("Create file: "+twin_path, "Yeah, fuck it"):
        open(twin_path,"w").close()
        window.open_file(twin_path)
      else:
        sublime.status_message("Could not find " + twin_path)

  def app_twin_path(self, spec_path):
    file_path = re.search(r'scripts(/.*)', spec_path).group(1).replace(".spec.js", ".js")
    return self.find_app_directory() + file_path

  def find_app_directory(self):
    return self.find_directory([
      "/app/assets/javascripts",
      "/app/javascripts"
    ])

  def spec_twin_path(self, app_path):
    file_path = re.search(r'scripts(/.*)', app_path).group(1).replace(".js", ".spec.js")
    return self.find_spec_directory() + file_path

  def find_spec_directory(self):
    return self.find_directory([
      "/spec/javascripts",
      "/spec/assets/javascripts"
    ])

  def find_directory(self, candidates):
    root_path = self.window.folders()[0]

    for candidate in candidates:
      print root_path + candidate
      if os.path.exists(root_path + candidate):
        return root_path + candidate

    raise Exception("Unable to find javascripts path in " + ','.join(map(str, candidates)))


########NEW FILE########
__FILENAME__ = rspec
import sublime
import sublime_plugin
import os, errno
import re

def get_twin_path(path):
  spec_file = path.find("/spec/") >= 0

  if spec_file:
    if path.find("/lib/") > 0:
      return path.replace("/spec/lib/","/lib/").replace("_spec.rb", ".rb")
    else:
      return path.replace("/spec/","/app/").replace("_spec.rb", ".rb")
  else:
    if path.find("/lib/") > 0:
      return path.replace("/lib/", "/spec/lib/").replace(".rb", "_spec.rb")
    else:
      return path.replace("/app/", "/spec/").replace(".rb", "_spec.rb")

class OpenRspecFileCommand(sublime_plugin.WindowCommand):
  def run(self):
    self.views = []
    window = self.window
    current_file_path = self.window.active_view().file_name()

    twin_path = get_twin_path(current_file_path)

    if os.path.exists(twin_path):
      view = window.open_file(twin_path)
    else:
      matches = self.find_twin_candidates(current_file_path)
      matches.append("Create "+twin_path)

      def process_selection(choice):
        if( choice == matches.__len__() - 1):
          self.create_new_file(twin_path)
        elif( choice == -1):
          print "Cancelled dialog"
          # do nothing
        else:
          window.open_file(matches[choice])
      window.show_quick_panel(matches, process_selection)

  def create_new_file(self, path):
    window = self.window
    path_parts = path.split("/")
    dirname = "/".join(path_parts[0:-1])
    basename = path_parts[-1]

    try:
        os.makedirs(dirname)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise

    twin_file = open(path, "w")

    constant_name = self.camelize(basename.replace(".rb", "").replace("_spec", ""))

    if basename.find("_spec") > 0:
      twin_file.write("class " + constant_name + "\nend")
    else:
      twin_file.write("require \"spec_helper\"\n\ndescribe " + constant_name + " do\nend")
    twin_file.close()

    print(path)

    view = window.open_file(twin_file)
    self.views.append(view)


  def find_twin_candidates(self, file_path):
    is_spec = file_path.find("/spec/") > 0

    base_name = re.search(r"\/(\w+)\.(\w+)$", file_path).group(1)
    base_name = re.sub('_spec', '', base_name)

    if is_spec:
      matcher = re.compile("[/\\\\]" + base_name + "\.rb$")
    else:
      matcher = re.compile("[/\\\\]" + base_name + "_spec\.rb$")

    window = self.window
    candidates = []
    for root, dirs, files in os.walk(window.folders()[0]):
      for f in files:
        if re.search(r"\.rb$", f):
          cur_file = os.path.join(root, f)
          if matcher.search(cur_file):
            candidates.append(cur_file)

    return candidates

  def camelize(self, string):
    return re.sub(r"(?:^|_)(.)", lambda x: x.group(0)[-1].upper(), string)


class RunTests(sublime_plugin.TextCommand):
  def run(self, edit, scope):
    last_run = sublime.load_settings("Rspec.last-run")

    if scope == "last":
      self.run_spec(last_run.get("root_path"), last_run.get("path"))
    else:
      path = self.find_path(scope)
      root_path = re.sub("\/spec\/.*", "", path)
      self.run_spec(root_path, path)

      last_run.set("path", path)
      last_run.set("root_path", root_path)
      sublime.save_settings("Rspec.last-run")

  def find_path(self, scope):
    path = self.view.file_name()

    if path.find("/spec/") < 0:
      twin_path = get_twin_path(path)
      if os.path.exists(twin_path):
        path = twin_path
      else:
        return sublime.error_message("You're not in a spec, bro.")

    if scope == "line":
      line_number, column = self.view.rowcol(self.view.sel()[0].begin())
      line_number += 1
      path += ":" + str(line_number)

    return path

  def run_spec(self, root_path, path):
    self.run_in_terminal('cd ' + root_path)
    self.run_in_terminal('bundle exec rspec ' + path)

  def run_in_terminal(self, command):
    osascript_command = 'osascript '
    osascript_command += '"' + sublime.packages_path() + '/User/run_command.applescript"'
    osascript_command += ' "' + command + '"'
    osascript_command += ' "Ruby Tests"'
    os.system(osascript_command)

########NEW FILE########
__FILENAME__ = steady_cursor
# NOTE: this does not work as is since trim_trailing_white_space runs afterwards
# for now, you can just add this logic to trim_trailing_white_space.py in Default
import sublime, sublime_plugin

class SteadyCursor(sublime_plugin.EventListener):
  def on_pre_save(self, view):
    if self.should_reindent(view):
      view.run_command("reindent")

  # reindent if the cursor is chilling on a non-terminal empty line
  def should_reindent(self, view):
    cursor = view.sel()[0]
    return view.sel().__len__() == 1 and view.line(cursor).empty() and cursor.end() != view.size()

########NEW FILE########
