__FILENAME__ = about
#
# Sublime Text plugin to support Corona Editor
#
# Copyright (c) 2013 Corona Labs Inc. A mobile development software company. All rights reserved.
#
# MIT License - see https://raw.github.com/coronalabs/CoronaSDK-SublimeText/master/LICENSE

import sublime
import sublime_plugin
import os.path
import json
import datetime

try:
  from . import _corona_utils  # P3
except:
  import _corona_utils  # P2

"""
# This is run by ST3 after the plugins have loaded (and the ST API is ready for calls)
def plugin_loaded():
  corona_utils.Init()

# This fakes the above functionality on ST2.
# It's important that this is called from a module that isn't imported by any other modules or
# the code gets run multiple times in ST2
if corona_utils.SUBLIME_VERSION < 3000:
  corona_utils.Init()
"""


class AboutCoronaEditorCommand(sublime_plugin.WindowCommand):
  _about_info = None
  _dev_about_info = '{"url": "https://www.coronalabs.com/", "version": "<development>", "description": "Corona Editor is the official Corona SDK plugin for Sublime Text"}'

  def run(self):
    self.load_json("package-metadata.json")
    sublime_info = "[Sublime Text " + sublime.version() + "/" + sublime.channel() + "/" + sublime.platform() + "/" + sublime.arch() + "]"
    canary_file = os.path.join(_corona_utils.PACKAGE_DIR, "about.py") if _corona_utils.SUBLIME_VERSION < 3000 else _corona_utils.PLUGIN_PATH
    install_info = "Installed: " + str(datetime.datetime.fromtimestamp(os.path.getmtime(canary_file)))
    about_mesg = "Corona Editor for Sublime Text\n\nVersion: " + self._about_info['version'] + "\n\n" + install_info + "\n\n" + self._about_info['description'] + "\n\n" + sublime_info
    print("about: " + about_mesg.replace("\n\n", " | "))
    sublime.message_dialog(about_mesg)

  # If we're running ST2, load JSON from file
  # else, load JSON from member of package
  def load_json(self, filename):
    if (_corona_utils.SUBLIME_VERSION < 3000):
      file_path = os.path.join(_corona_utils.PACKAGE_DIR, filename)
      try:
        json_data = open(file_path)
        self._about_info = json.load(json_data)
      except:
        self._about_info = json.loads(self._dev_about_info)
      else:
        json_data.close()

    else:  # we're on ST3

      try:
        self._about_info = json.loads(sublime.load_resource(_corona_utils.ST_PACKAGE_PATH + filename))
      except:
        self._about_info = json.loads(self._dev_about_info)

    # pprint(self._about_info)
    # print("About: " + str(self._about_info))

########NEW FILE########
__FILENAME__ = completions
#
# Sublime Text plugin to support Corona Editor
#
# Copyright (c) 2013 Corona Labs Inc. A mobile development software company. All rights reserved.
#
# MIT License - see https://raw.github.com/coronalabs/CoronaSDK-SublimeText/master/LICENSE

import sublime
import sublime_plugin
import os
import re
import json

try:
  from . import _corona_utils  # P3
except:
  import _corona_utils  # P2

# We expose the completions to the snippets code
CoronaCompletions = None


#
# Utility functions
#
def is_lua_file(view):
  # Fairly rigorous test for being a Corona Lua file
  # Note this means users have to set new files to the right syntax to get completions
  return view.match_selector(view.sel()[0].a, "source.lua.corona")


# determine if 'obj' is a string in both Python 2.x and 3.x
def is_string_instance(obj):
  try:
    return isinstance(obj, basestring)
  except NameError:
    return isinstance(obj, str)

class FuzzyMatcher():

  def __init__(self):
    self.prefix_match_tweak = 20
    self.regex1 = ''
    self.regex2 = ''

  def setPattern(self, pattern):
    self.regex1 = re.compile('.*?'.join(map(re.escape, list(pattern))))  # look for characters in pattern in order
    self.regex2 = re.compile('\\b'+re.escape(pattern))  # look for exact prefixes matching pattern

  def score(self, string):
    match = self.regex1.search(string)
    tweak = self.regex2.search(string)
    if match is None:
      return 0
    else:
      return (100.0 / ((1 + match.start()) * (match.end() - match.start() + 1))) + (self.prefix_match_tweak if tweak is not None else 0)


#
# CoronaLabs Class
#
class CoronaLabs:
  _completions = []
  _fuzzyMatcher = None
  _fuzzyPrefix = None
  _findWhiteSpace = re.compile("([^,])\s")

  def __init__(self):
    global CoronaCompletions
    CoronaCompletions = self

  # Called by the snippets module to make sure completions are loaded
  def initialize(self):
    self.load_completions(_corona_utils.GetSetting("corona_sdk_use_docset", "public"))

  # If we're running ST2, load completions from file
  # else, load completions from member of package
  def load_completions(self, docset):
    # Only load once
    if (len(self._completions) == 0):
      source = docset if docset in ['public', 'legacy', 'daily'] else 'public'
      source = "corona.completions-" + source
      if (_corona_utils.SUBLIME_VERSION < 3000):
        comp_path = os.path.join(_corona_utils.PACKAGE_DIR, source)
        json_data = open(comp_path)
        self._completions = json.load(json_data)
        json_data.close()

      else:

        self._completions = json.loads(sublime.load_resource(_corona_utils.ST_PACKAGE_PATH + source))

      # print(self._completions)
      print("Corona Editor: loaded {0} completions from {1}".format(len(self._completions['completions']), source))

  def setupFuzzyMatch(self, prefix):
    self._fuzzyMatcher = FuzzyMatcher()
    self._fuzzyMatcher.setPattern(prefix)
    self._fuzzyPrefix = prefix

  def fuzzyMatchString(self, s, use_fuzzy_completion):
    if use_fuzzy_completion:
      threshold = 5
      score = self._fuzzyMatcher.score(s)
      if score > threshold:
        # print('s: ', s, '; score: ', score)
        return True
      else:
        return False
    else:
      if s.startswith(self._fuzzyPrefix):
        return True
      else:
        return False

  # extract completions which match prefix
  # Completions are problematic because Sublime uses the "word_separators" preference to decide where tokens
  # begin and end which, by default, means that periods are not completed properly.  One options is to remove
  # periods from "word_separators" and this works well except that it breaks intra line cursor movement with Alt-arrow.
  # So we jump through some hoops to accommodate periods in the completion process:
  #  * determine the "completion target" ourselves based on the view instead of using the provided prefix
  #  * if there's a period in the "completion target", return only the part following the period in the completions

  def find_completions(self, view, prefix):
    self.load_completions(_corona_utils.GetSetting("corona_sdk_use_docset", "public"))
    use_fuzzy_completion = _corona_utils.GetSetting("corona_sdk_use_fuzzy_completion", True)
    strip_white_space = _corona_utils.GetSetting("corona_completions_strip_white_space", False)

    completion_target = self.current_word(view)

    # Because we adjust the prefix to make completions with periods in them work better we may need to
    # trim the part before the period from the returned string (or it will appear to be doubled). Note
    # this only happens for "dict" completions, not "string" completions.
    trim_result = completion_target.endswith(".")

    # print('completion_target: ', completion_target, "; trim_result: ", trim_result, "; corona_sdk_complete_periods: ", _corona_utils.GetSetting("corona_sdk_complete_periods", True) )

    self.setupFuzzyMatch(completion_target)

    # Sample:
    #   { "trigger": "audio.stopWithDelay()", "contents": "audio.stopWithDelay( ${1:duration}, ${2:[, options ]} )"},
    #   "audio.totalChannels ",

    # This is horrible on a variety of levels but is brought upon us by the fact that
    # ST completion files contain an array that is a mixture of strings and dicts
    comps = []
    for c in self._completions['completions']:
      trigger = ""
      contents = ""
      if isinstance(c, dict):
        if self.fuzzyMatchString(c['trigger'], use_fuzzy_completion):
          trigger = c['trigger']
          contents = c['contents'] if not trim_result else c['contents'].partition('.')[2]
      elif is_string_instance(c):
        if self.fuzzyMatchString(c, use_fuzzy_completion):
          trigger = c
          contents = c

      if trigger is not "":
        if strip_white_space and contents is not "":
           contents = self._findWhiteSpace.sub("\\1", contents)
        comps.append((trigger, contents))

    # print("comps: ", comps)
    # print("extract_completions: ", view.extract_completions(completion_target))

    # Add textual completions from the document
    for c in view.extract_completions(completion_target):
      comps.append((c, c))

    # Reorganize into a list
    comps = list(set(comps))
    comps.sort()

    return comps

  def current_word(self, view):
    s = view.sel()[0]

    # Expand selection to current "word"
    start = s.a
    end = s.b

    view_size = view.size()
    terminator = ['\t', ' ', '\"', '\'', ':', '=', '-', '+', '*', '/', '^', ',']

    while (start > 0
            and not view.substr(start - 1) in terminator
            and view.classify(start) & sublime.CLASS_LINE_START == 0):
        start -= 1

    while (end < view_size
            and not view.substr(end) in terminator
            and view.classify(end) & sublime.CLASS_LINE_END == 0):
        end += 1

    return view.substr(sublime.Region(start, end))


class CoronaLabsCollector(CoronaLabs, sublime_plugin.EventListener):

  def __init__(self):
    self.periods_set = {}


  # Optionally trigger a "build" when a .lua file is saved.  This is best
  # done by setting the "Relaunch Simulator when project is modified" setting
  # in the Simulator itself but is provided here for cases where that option
  # doesn't work
  def on_post_save(self, view):
    if is_lua_file(view):
      auto_build = _corona_utils.GetSetting("corona_sdk_auto_build", False)
      if auto_build:
        print("Corona Editor: auto build triggered")
        view.window().run_command("build")


  # When a Lua file is loaded and the "use_periods_in_completion" user preference is set,
  # add period to "auto_complete_triggers" if it's not already there.
  def on_load(self, view):
    use_corona_sdk_completion = _corona_utils.GetSetting("corona_sdk_completion", True)
    if use_corona_sdk_completion and is_lua_file(view):
      use_periods_in_completion = _corona_utils.GetSetting("corona_sdk_complete_periods", True)

      # Completion behavior is improved if periods are included in the completion process
      if use_periods_in_completion:
        # If "auto_complete_triggers" for periods is not set for this buffer, set it
        auto_complete_triggers = view.settings().get("auto_complete_triggers")
        self.periods_set[view.file_name()] = False
        for act in auto_complete_triggers:
          if "source.lua" in act["selector"] and "." in act["characters"]:
            self.periods_set[view.file_name()] = True
            break
        if not self.periods_set.get(view.file_name(), False):
          auto_complete_triggers.append({ "selector": "source.lua", "characters": "." })
          view.settings().set("auto_complete_triggers", auto_complete_triggers)
          self.periods_set[view.file_name()] = True
    print("on_load view: ", view.file_name(), "periods_set" if self.periods_set.get(view.file_name(), False) else "not set")


  # When a Lua file is closed and we added a period to "auto_complete_triggers", remove it
  def on_close(self, view):
    print("on_close view: ", view.file_name(), "periods_set" if self.periods_set.get(view.file_name(), False) else "not set" )
    if view.file_name() is not None and self.periods_set.get(view.file_name(), False):
      auto_complete_triggers = view.settings().get("auto_complete_triggers")
      if { "selector": "source.lua", "characters": "." } in auto_complete_triggers:
        auto_complete_triggers.remove({ "selector": "source.lua", "characters": "." })
        self.periods_set[view.file_name()] = False


  def on_query_completions(self, view, prefix, locations):
    use_corona_sdk_completion = _corona_utils.GetSetting("corona_sdk_completion", True)
    print("on_query_completions: ",  use_corona_sdk_completion, view.match_selector(locations[0], "source.lua.corona - entity"))
    if use_corona_sdk_completion and view.match_selector(locations[0], "source.lua.corona - entity"):
      comps = self.find_completions(view, prefix)
      flags = 0  # sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS
      return (comps, flags)
    else:
      return []

########NEW FILE########
__FILENAME__ = corona_docs
#
# Sublime Text plugin to support Corona SDK
#
# Copyright (c) 2013 Corona Labs Inc. A mobile development software company. All rights reserved.
#
# MIT License - see https://raw.github.com/coronalabs/CoronaSDK-SublimeText/master/LICENSE
#

import sublime
import sublime_plugin
import webbrowser
import string
import re
import urllib

try:
  from . import _corona_utils  # P3
except:
  import _corona_utils  # P2

SEARCH_URL = "http://www.google.com/cse?cx=009283852522218786394%3Ag40gqt2m6rq&ie=UTF-8&q={search_term}&sa=Search#gsc.tab=0&gsc.q={search_term}&gsc.page=1"

# Note "lfs", "socket", "sqlite3" are omitted because we don't have complete docs for those
LIBRARY_APIS = (
  "ads", "analytics", "audio", "credits", "crypto", "display", "easing",
  "facebook", "gameNetwork", "global", "graphics", "io", "json", "licensing",
  "math", "media", "native", "network", "os", "package", "physics", "sprite",
  "store", "storyboard", "string", "system", "table", "timer", "transition", "widget")


# Python version independent UrlEncode
def UrlEncode(s):
  try:
    return urllib.parse.quote_plus(s)
  except AttributeError:
    return urllib.quote_plus(s)


class CoronaDocsCommand(sublime_plugin.TextCommand):
  def is_visible(self):
    s = self.view.sel()[0]
    return self.view.match_selector(s.a, "source.lua - entity")

  def run(self, edit):
    s = self.view.sel()[0]

    # Expand selection to current "word"
    start = s.a
    end = s.b

    view_size = self.view.size()
    terminator = ['\t', ' ', '\"', '\'', '(', '=']

    while (start > 0
            and not self.view.substr(start - 1) in terminator
            and self.view.classify(start) & sublime.CLASS_LINE_START == 0):
        start -= 1

    while (end < view_size
            and not self.view.substr(end) in terminator
            and self.view.classify(end) & sublime.CLASS_LINE_END == 0):
        end += 1

    # Note if the current point is on a Lua keyword (according to
    # the .tmLanguage definition)
    isLuaKeyword = self.view.match_selector(start,
                                            "keyword.control.lua, support.function.lua, support.function.library.lua")

    use_docset = _corona_utils.GetSetting("corona_sdk_use_docset", "public")
    if use_docset in ['legacy', 'daily']:
      docset = use_docset + "/"
    else:
      docset = ""

    # Convert "word" under cursor to Corona Docs link, or a Lua docs link
    page = self.view.substr(sublime.Region(start, end))
    page = page.strip(string.punctuation)

    # Look for an embedded period which, if the class name is one of ours,
    # indicates we should look it up in the "library" section of the docs
    # (unless the class member doesn't start with a lowercase letter in which
    # case it's a constant and we'll have to just default to searching for it)
    if page is None or page == "":
      # Nothing is selected, take them to API home
      docUrl = "http://docs.coronalabs.com/" + docset + "api/index.html"
    elif (re.search("\w+\.[a-z]", page) is not None and
       page.partition(".")[0] in LIBRARY_APIS):
      page = page.replace(".", "/")
      docUrl = "http://docs.coronalabs.com/" + docset + "api/library/" + page + ".html"
    elif isLuaKeyword:
      # Unfortunately, there's no search on the Lua docs site so we need to guess at
      # an anchor (if it's not there, you go to the top of the page)
      docUrl = "http://www.lua.org/manual/5.1/manual.html#pdf-" + page
    else:
      # We don't know what we're on, send them to the Corona Docs search page
      page = UrlEncode(page)
      docUrl = SEARCH_URL.format(search_term=page)

    # print("docURL : " + docUrl)

    webbrowser.open_new_tab(docUrl)

########NEW FILE########
__FILENAME__ = debugger
#
# Sublime Text plugin to support Corona Editor
#
# Copyright (c) 2013 Corona Labs Inc. A mobile development software company. All rights reserved.
#
# MIT License - see https://raw.github.com/coronalabs/CoronaSDK-SublimeText/master/LICENSE

import sublime
import sublime_plugin
import os
import re
import threading
import subprocess
import datetime
import sys
import socket
import traceback

try:
  import queue  # P3
  coronaQueue = queue
except:
  import Queue  # P2
  coronaQueue = Queue

subProcOutputQ = None
debuggerCmdQ = None

try:
  from . import _corona_utils  # P3
except:
  import _corona_utils  # P2


# determine if 'obj' is a string in both Python 2.x and 3.x
def is_string_instance(obj):
  try:
    return isinstance(obj, basestring)
  except NameError:
    return isinstance(obj, str)


debugFP = None


def debug(s):
  global debugFP
  try:
    if not os.path.isdir(_corona_utils.PACKAGE_USER_DIR):
      os.makedirs(_corona_utils.PACKAGE_USER_DIR)
    debugFP = open(os.path.normpath(os.path.join(_corona_utils.PACKAGE_USER_DIR, "debug.log")), "w", 1)
  except:
    pass

  # <CoronaDebuggerThread(Thread-5, started 4583960576)>
  thread_id = re.sub(r'.*\(([^,]*),.*', r'\1', str(threading.current_thread()))
  log_line = str(datetime.datetime.now()) + " (" + str(thread_id) + "): " + str(s)
  if debugFP:
    debugFP.write(log_line + "\n")
  print(log_line)


def debug_with_stacktrace(s):
  debug(s)
  for line in traceback.format_list(traceback.extract_stack()):
    debug("    "+line.strip())

HOST = ''    # Symbolic name meaning all available interfaces
PORT = 8171  # Arbitrary non-privileged port, matches Simulator

coronaDbg = None
coronaDbgThread = None
coronaBreakpointsSettings = None
coronaBreakpoints = {}


class CoronaDebuggerThread(threading.Thread):

  def __init__(self, projectDir, completionCallback, threadID=1):
    threading.Thread.__init__(self)
    self.threadID = threadID
    self.projectDir = projectDir
    self.completionCallback = completionCallback
    self.debugger_running = False
    self.conn = None
    self.socket = None
    self.recvFP = None
    self.sendFP = None

  def stop(self):
    # debug_with_stacktrace("CoronaDebuggerThread: stop")
    self.debugger_running = False

  def isRunning(self):
    # debug("CoronaDebuggerThread: isRunning (" + str(self.debugger_running) + ")")
    return self.debugger_running

  def setup(self):

    self.debugger_running = True
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    debug('Socket created')

    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    debug('Socket options set')

    try:
      self.socket.bind((HOST, PORT))
    except socket.error as msg:
      debug('Bind: ' + str(msg))
      sublime.error_message("Cannot connect to Corona Simulator (" + str(msg) + ")\n\nPerhaps there is another debugger running.\n\nTry restarting Sublime Text and stopping any Simulators.")
      return False
    else:
      debug('Socket bind complete')

    self.socket.listen(1)
    debug('Socket now listening')

    return True

  def initPUTComms(self):
    if _corona_utils.SUBLIME_VERSION < 3000:
      self.recvFP = self.conn.makefile('r', 1)
      self.sendFP = self.conn.makefile('w', 1)
    else:
      self.recvFP = self.conn.makefile(mode='rb', buffering=0, newline='\n')
      self.sendFP = self.conn.makefile(mode='wb', buffering=0, newline='\n')

  def closePUTComms(self):
    if self.sendFP is not None:
      self.sendFP.close()
      self.sendFP = None
    if self.recvFP is not None:
      self.recvFP.close()
      self.recvFP = None

  def writeToPUT(self, s):
    try:
      return self.sendFP.write(str.encode(s, 'utf-8'))
    except TypeError:
      return self.sendFP.write(s)

  def readFromPUT(self, n=None):
    try:
      if n is not None:
        result = self.recvFP.read(n)
      else:
        result = self.recvFP.readline()
    except Exception as e:
      debug("readFromPUT: " + str(e))
    else:
      return result.decode('utf-8')

  def run(self):

    # wait to accept a connection - set a short timeout so we can be interrupted if plans change
    self.socket.settimeout(1)
    debug("Socket about to accept")
    while self.socket is not None:
      try:
        self.conn, addr = self.socket.accept()
        self.conn.settimeout(None)  # Revert to no timeout once things are established
      except socket.error as msg:
        debug('Accept: ' + str(msg))
      else:
        debug('Socket accepted')
        break

    if self.socket is None:
      return

    # display client information
    debug('Connected with ' + addr[0] + ':' + str(addr[1]))

    self.initPUTComms()

    self.writeToPUT("STEP\n")

    data = self.readFromPUT()  # response like '200 OK'
    debug('data: ' + str(data))

    bpResponse = self.readFromPUT()  # response like '202 Paused main.lua 3\n'
    debug('bpResponse: ' + bpResponse)

    bpMatches = re.search(r'^202 Paused\s+([^\s]+)\s+(\d+)$', bpResponse.strip())

    # Handle the response to the STEP command we just issued to start the PUT
    if bpMatches is not None:
      filename = bpMatches.group(1)
      line = bpMatches.group(2)

      if filename != "main.lua":  # we get a pause in "init.lua" if there's a syntax error in main.lua
        debugger_status("Error running main.lua")
        on_main_thread(lambda: sublime.error_message("There was an error running main.lua.\n\nCheck Console for error messages."))
        # self.writeToPUT("RUN\n") # this leaves the Simulator is a deterministic state
      else:
        debugger_status("Paused at line {0} of {1}".format(line, filename))
        on_main_thread(lambda: self.showSublimeContext(os.path.join(self.projectDir, filename), int(line)))
    else:
      errMatches = re.search(r'^401 Error in Execution (\d+)$', bpResponse.strip())
      if errMatches is not None:
        size = errMatches.group(1)
        console_output("Error in remote application: ")
        console_output(self.readFromPUT(size))
      else:
        on_main_thread(lambda: sublime.error_message("Unexpected response from Simulator:\n\n" + str(bpResponse) + "\n\nCheck Console for error messages."))

    # Restore any breakpoint we have saved (breakpoints can only be set when
    # we are running the debugger though we allow the user to think they are
    # setting breakpoints before it's started)
    on_main_thread(lambda: self.restore_breakpoints())

    self.doCommand('backtrace')
    self.doCommand('locals')

    while self.debugger_running:
      cmd = debuggerCmdQ.get()
      self.performCommand(cmd)
      debuggerCmdQ.task_done()

    # clean up on PUT termination
    on_main_thread(lambda: self.completionCallback(self.threadID))

    debug('CoronaDebuggerThread: ends')

  def restore_breakpoints(self):
    global coronaBreakpointsSettings
    if coronaBreakpointsSettings is None:
      coronaBreakpointsSettings = sublime.load_settings(_corona_utils.PACKAGE_NAME + ".breakpoints")
    if coronaBreakpointsSettings is not None:
      debug("coronaBreakpointsSettings: "+str(coronaBreakpointsSettings))
      if coronaBreakpointsSettings.get('breakpoints') is not None:
        # Restore previously set breakpoints(use a local rather than "coronaBreakpoints"
        # so we don't toggle any existing ones off again)
        breakpoints = coronaBreakpointsSettings.get('breakpoints')
        debug("breakpoints: "+str(breakpoints))
        for filename in breakpoints:
          for view in sublime.active_window().views():
            debug("view.name: " + str(view.file_name()) + "; filename: " + filename)
            if view.file_name() == filename:
              breakpoints[filename] = sorted(set(breakpoints[filename]))  # sort and unique
              for line in breakpoints[filename]:
                sublime.active_window().run_command("corona_debugger", {"cmd": "setb", "arg_filename": filename, "arg_lineno": line, "arg_toggle": False})

  def getBreakpointParameters(self, cmdLine):
    cmd = ""
    filename = ""
    linenum = 0

    bpMatches = re.search(r'^(\w+)\s+(.+?)\s+(\d+)$', cmdLine)
    if bpMatches is not None:
      cmd = bpMatches.group(1)
      filename = bpMatches.group(2)
      linenum = bpMatches.group(3)
    else:
      debugger_status("Could not parse breakpoint expression: " + cmdLine)

    return cmd, filename, linenum

  def getParameters(self, cmdLine):
    cmd = ""
    parameter = ""

    cmdMatches = re.search(r'^(\w+)\s*(.*)$', cmdLine)
    if cmdMatches is not None:
      cmd = cmdMatches.group(1)
      parameter = cmdMatches.group(2)
    else:
      debugger_status("Could not parse command: " + cmdLine)

    return cmd, parameter

  def getAck(self, cmd):
    ack = None
    try:
      self.writeToPUT(cmd.upper() + "\n")
      ack = self.readFromPUT().strip()
    except Exception as e:
      debug("Exception reading network: "+str(e))
    else:
      debug("getAck: " + ack)
      if ack != "200 OK":
        debug("*** Sent '{0}' got unexpected '{1}'".format(cmd, ack))

    return ack

  def doCommand(self, cmd):
    debuggerCmdQ.put(cmd, 1)

  def performCommand(self, cmd):
    try:
      verb = cmd.partition(" ")[0].lower()
      if verb in ["run", "step", "over"]:
        self.doContinue(cmd)
      elif verb in ["backtrace", "locals"]:
        self.doGetData(cmd)
      elif verb in ["setb", "delb"]:
        self.doSetBreakpoint(cmd)
      elif verb in ["dump"]:
        self.doDump(cmd)
      elif verb in ["exit"]:
        self.doExit(cmd)
      elif verb in ["frame"]:
        debugger_status("Command '" + verb + "' not implemented")
      else:
        debugger_status("Unhandled command: {0}".format(cmd))
    except Exception as e:
      debug("Exception performing command: "+str(e))
      type_, value_, traceback_ = sys.exc_info()
      for line in traceback.format_tb(traceback_):
        debug("    "+line.strip())

  def doDump(self, cmd):
    cmdtype, variable_name = self.getParameters(cmd)
    debug("doDump: "+cmdtype+" "+variable_name)
    if variable_name:
      # Note the space after "return" matters
      self.writeToPUT("EXEC return (" + variable_name + ")\n")
      dmpResponse = self.readFromPUT().strip()
      debug("dmpResponse: " + dmpResponse)
      dataMatches = re.search(r'^(\d+)[^0-9]*(\d+)$', dmpResponse)
      if dataMatches is not None:
        status = dataMatches.group(1)
        length = int(dataMatches.group(2))
        if status == "200":
          if length == 0:
            debugger_status("No "+cmd)
          else:
            dataStr = ""
            while len(dataStr) < length:
              dataStr += self.readFromPUT(int(length - len(dataStr)))

            dataStr = variable_name + " = " + dataStr
            debug('dmpData: ' + dataStr)
            sublime.message_dialog(dataStr)
      else:
        debugger_status("Error getting variable value: " + dmpResponse)
    else:
      debugger_status("Usage: DUMP variable")

  def doSetBreakpoint(self, cmd):
    global coronaBreakpoints
    cmdtype, filename, linenum = self.getBreakpointParameters(cmd)
    if filename and linenum:
      self.writeToPUT(cmdtype.upper() + " " + filename + " " + linenum + "\n")
      bpResponse = self.readFromPUT().strip()
      debug("bpResponse: " + bpResponse)
      if bpResponse == "200 OK":
        action = "set" if cmdtype.upper() == "SETB" else "removed"
        debugger_status("Breakpoint {2} at {0}:{1}".format(filename, linenum, action))
      else:
        debugger_status("Error setting breakpoint: " + bpResponse)
    else:
      debugger_status("Usage: [SETB|DELB] filename linenum")

  def doExit(self, cmd):
    debug("CoronaDebugger: doExit")
    try:
      # self.closePUTComms()
      if self.conn is not None:
        # debug("doExit: conn.close")
        self.conn.close()
        self.conn = None
      if self.socket is not None:
        # debug("doExit: socket.close")
        # self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        self.socket = None
    except Exception as e:
      debug("Exception closing down coprocess: "+str(e))
      exc_type, exc_obj, exc_tb = sys.exc_info()
      fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
      print(exc_type, fname, exc_tb.tb_lineno)

  def doGetData(self, cmd):
    # backtrace and locals overload the 200 response with a length so we need
    # to send them manually rather than use getAck()
    self.writeToPUT(cmd.upper() + "\n")
    dataResponse = self.readFromPUT().strip()
    debug("dataResponse: " + dataResponse)
    dataMatches = re.search(r'^(\d+)[^0-9]*(\d+)$', dataResponse)
    if dataMatches is not None:
      status = dataMatches.group(1)
      length = int(dataMatches.group(2))
      if status == "200":
        if length == 0:
          debugger_status("No "+cmd)
        else:
          dataStr = ""
          while len(dataStr) < length:
            dataStr += self.readFromPUT(int(length - len(dataStr)))
          if cmd == 'backtrace':
            # Tidy up backtrace
            if dataStr.find('platform/resources/init.lua:') != -1 or dataStr.find('?:0') != -1:
              # Stopped in internal code
              dataStr = re.sub(r' at .*platform/resources/init\.lua:[0-9]*', ' at <internal location>', dataStr)
              dataStr = re.sub(r' at \?:0', ' at <internal location>', dataStr)
            # Elide the project directory from any frames that contain it
            # debug("projectDir: " + self.projectDir + os.path.sep)
            dataStr = re.sub("(?i)" + re.escape(self.projectDir + os.path.sep), '', dataStr)
            stack_output(cmd.title() + ":\n" + dataStr)
          else:
            variables_output(cmd.title() + ":\n" + dataStr)
      else:
        debugger_status("Error response from '" + cmd + "' (" + dataResponse + ")")
    else:
      debugger_status("Unparsable response from '" + cmd + "' (" + dataResponse + ")")

  def activateViewWithFile(self, filename, line):
    debug("activateViewWithFile: "+str(filename) + ":" + str(line))
    window = sublime.active_window()
    for view in window.views():
      if view.name() == filename:
        window.focus_view(view)
        break

    if window.active_view().file_name() != filename:
      # didn't find an existing view, open a new one
      filename = filename + ":" + str(line)
      view = window.open_file(filename, sublime.ENCODED_POSITION)
      window.focus_view(view)

  def showSublimeContext(self, filename, line):
    debug("showSublimeContext: "+str(filename) + " : " + str(line))
    window = sublime.active_window()
    if window:
      window.focus_group(0)
      view = window.active_view()
      # debug("showSublimeContext: view: " + str(view) + "; size: " + str(view.size()))
      # testing that "view" is not None is insufficient here
      if view is not None and view.size() >= 0:
        if view.file_name() != filename:
          self.activateViewWithFile(filename, line)

        window.run_command("goto_line", {"line": line})
        # view might have changed
        view = window.active_view()
        mark = [view.line(view.text_point(line - 1, 0))]
        view.erase_regions("current_line")  # removes it if we change files
        view.add_regions("current_line", mark, "current_line", "dot", sublime.DRAW_OUTLINED)  # sublime.HIDDEN | sublime.PERSISTENT)
      else:
        debug("No current view")

  # Handle category of commands that move the execution pointer ("run", "step", "over")
  def doContinue(self, cmd):
    if cmd == "run":
      stack_output("Running ...")
      variables_output("Running ...")
      debugger_status("Running ...")
      on_main_thread(lambda: sublime.active_window().active_view().erase_regions("current_line"))  # we wont be back to erase the current line marker so do it here

    self.getAck(cmd)
    response = self.readFromPUT()
    if response is None or response == "":
      debugger_status("Program finished")
      self.debugger_running = False
      return

    statusMatches = re.search(r'^(\d+)', response.strip())
    status = statusMatches.group(0)
    debug("Status: " + status)
    if status == "202":
      bpMatches = re.search(r'^202 (\w+)\s+([^\s]+)\s+(\d+)$', response)
      if bpMatches is not None:
        label = bpMatches.group(1)
        filename = bpMatches.group(2)
        line = bpMatches.group(3)
        if label == "Error":
          label = "Runtime script error"
        if filename and line:
          if filename == "=?" or filename == "init.lua" or filename == "shell.lua":
            debugger_status(label + " at internal location")
          else:
            debugger_status(label + " at line " + line + " of " + filename)
            on_main_thread(lambda: self.showSublimeContext(os.path.join(self.projectDir, filename), int(line)))
        else:
          debugger_status(label + " response: " + response)
      else:
        debugger_status("Unexpected 202 response: " + response)
    elif status == "203":
      bpwMatches = re.search(r'^203 Paused\s+([^\s]+)\s+(\d+)\s+(\d+)$', response)
      if bpwMatches is not None:
        file = bpwMatches.group(1)
        line = bpwMatches.group(2)
        watchIndex = bpwMatches.group(3)
        if file and line and watchIndex:
          print(_corona_utils.PACKAGE_NAME + ": watches not implemented")
          # debugger_status("Paused at file " + file + " line " + line + " (watch expression " + watchIndex + ": [" + watches[watchIndex] + "])")
      else:
        debugger_status("Unexpected 203 response: " + response)
    elif status == "401":
      errMatches = re.search(r'^401 Error in Execution (\d+)$', response)
      if errMatches:
        size = errMatches.group(1)
        if size:
          console_output("Error in remote application: ")
          console_output(self.readFromPUT(int(size)))

  def doRun(self):
    self.doContinue("RUN")

  def doStep(self):
    self.doContinue("STEP")


class CoronaDebuggerListener(sublime_plugin.EventListener):
  def on_post_save(self, view):
    debug("CoronaDebuggerListener:on_post_save: " + view.file_name())
    if (coronaDbg is not None and coronaDbg.isRunning()) and view.file_name().endswith(".lua"):
      if sublime.ok_cancel_dialog(view.file_name() + " has changed.  Do you want to restart the Debugger?", "Restart"):
        sublime.set_timeout(lambda: sublime.active_window().run_command("corona_debugger", {"cmd": "restart"}), 0)


class CoronaDebuggerCommand(sublime_plugin.WindowCommand):

  view = None

  def is_enabled(self):
    view = self.window.active_view()
    if view is not None:
      s = view.sel()[0]
      return view.match_selector(s.a, "source.lua - entity")
    else:
      return False

  def run(self, cmd=None, arg_filename=None, arg_lineno=None, arg_toggle=True):
    debug("CoronaDebuggerCommand: " + cmd)
    global coronaDbg
    self.view = self.window.active_view()

    if self.view is None:
      sublime.error_message("Cannot find an active view.  You may need to restart Sublime Text.")
      return

    # if we aren't started yet and a step is asked for, do a start
    if (coronaDbg is None or not coronaDbg.isRunning()) and cmd in ['run', 'step', 'over']:
      cmd = "start"

    if cmd == "start":
      if _corona_utils.GetSetting("corona_sdk_debug", False):
        # Show Sublime Console
        self.window.run_command("show_panel", {"panel": "console"})
        # sublime.log_commands(True)

      if coronaDbg is not None:
        debug("Cleaning up debugger thread")
        coronaDbg.join()
        coronaDbg = None

      self.saved_layout = self.window.get_layout()

      # Figure out where the PUT and the Simulator are
      filename = self.window.active_view().file_name()
      if filename is None or not filename.endswith(".lua"):
        filename = None
        # No current .lua file, see if we have one open
        for view in self.window.views():
          if view.file_name() and view.file_name().endswith(".lua"):
            if filename is None or not filename.endswith("main.lua"):  # prefer a 'main.lua' if there is one
              filename = view.file_name()

      if filename is None:
        sublime.error_message("Can't find an open '.lua' file to determine the location of 'main.lua'")
        return
      mainlua = _corona_utils.ResolveMainLua(filename)
      if mainlua is None:
        sublime.error_message("Can't locate 'main.lua' for this project (try opening it in an editor tab)")
        return
      self.window.open_file(mainlua)  # make sure main.lua is open as that's the first place we'll stop
      projectDir = os.path.dirname(mainlua)
      if not projectDir:
        sublime.error_message("Cannot find 'main.lua' for '"+self.view.file_name()+"'.  This does not look like a Corona SDK app")
        return

      dbg_path, dbg_flags = _corona_utils.GetSimulatorCmd(mainlua, True)
      dbg_cmd = [dbg_path]
      dbg_cmd += dbg_flags
      dbg_cmd.append(mainlua)
      debug("debugger cmd: " + str(dbg_cmd))

      global subProcOutputQ, debuggerCmdQ
      subProcOutputQ = coronaQueue.Queue()
      debuggerCmdQ = coronaQueue.Queue()

      coronaDbg = CoronaDebuggerThread(projectDir, self.debuggerFinished)
      if coronaDbg.setup():
        if self.window.num_groups() == 1:
          self.initializeWindowPanes()
        else:
          # Clear the existing windows
          variables_output(' ')
          stack_output(' ')
        self.window.focus_group(0)
        RunSubprocess(dbg_cmd, self.window)
        coronaDbg.start()

    elif cmd == "restart":
      if coronaDbg is not None:
        self.window.run_command("corona_debugger", {"cmd": "exit"})
      sublime.set_timeout(lambda: self.window.run_command("corona_debugger", {"cmd": "start"}), 0)

    elif cmd == "exit":
      StopSubprocess()
      coronaDbg.doCommand(cmd)
      coronaDbg.stop()
      coronaDbg.join()
      coronaDbg = None
    elif cmd in ["run", "step", "over"]:
      coronaDbg.doCommand(cmd)
      coronaDbg.doCommand('backtrace')
      coronaDbg.doCommand('locals')
    elif cmd == "dump":
      self.dumpVariable()
    elif cmd == "setb":
      # toggle a breakpoint at the current cursor position
      if arg_filename is None:
        filename = self.view.file_name()
        (lineno, col) = self.view.rowcol(self.view.sel()[0].begin())
        lineno += 1
      else:
        filename = arg_filename
        lineno = int(arg_lineno)

      if self.toggle_breakpoint(filename, lineno, arg_toggle):
        cmd = "setb"
      else:
        cmd = "delb"

      cmd += " " + '"' + filename + '"'
      cmd += " " + str(lineno)
      debug("setb: " + cmd)

      if coronaDbg is not None:
        coronaDbg.doCommand(cmd)

    else:
      print("CoronaDebuggerCommand: Unrecognized command: " + cmd)

  def debuggerFinished(self, threadId):
    debug("debuggerFinished: threadId: " + str(threadId))
    self.closeWindowPanes()
    # self.window.run_command("corona_debugger", {"cmd": "exit"})

  def dumpVariable(self):
    # If something's selected use that, otherwise prompt the user for a variable name
    selection = self.view.sel()[0]
    if selection:
      selected_word = self.view.substr(self.view.word(selection))
      if selected_word and selected_word != "":
        self.doDumpVariable(selected_word)
    else:
      self.window.show_input_panel("Variable name or expression:", "", self.doDumpVariable, None, None)

  def doDumpVariable(self, variable_name):
      if coronaDbg is not None:
        coronaDbg.doCommand("dump " + variable_name)
      else:
        sublime.error_message("Corona Debugger is not running")

  def toggle_breakpoint(self, filename, lineno, toggle=True):
    global coronaBreakpointsSettings
    global coronaBreakpoints
    result = True

    if coronaBreakpointsSettings is None:
      coronaBreakpointsSettings = sublime.load_settings(_corona_utils.PACKAGE_NAME + ".breakpoints")

    bpId = self.new_breakpoint_id(filename, lineno)
    debug("bpId: " + bpId)
    if filename not in coronaBreakpoints:
      coronaBreakpoints[filename] = []
    if lineno in coronaBreakpoints[filename] and toggle:
      # we're unsetting the breakpoint
      debug("toggle_breakpoint: unsetting breakpoint")
      coronaBreakpoints[filename].remove(lineno)
      view = self.view_for_file(filename)
      if view is not None:
        view.erase_regions(bpId)
      result = False
    else:
      debug("toggle_breakpoint: setting breakpoint")
      if lineno not in coronaBreakpoints[filename]:
        coronaBreakpoints[filename].append(int(lineno))
      view = self.view_for_file(filename)
      if view is not None:
        mark = [view.line(view.text_point(lineno - 1, 0))]
        if _corona_utils.SUBLIME_VERSION < 3000:
          # Path for icons is "Packages/Theme - Default/"
          view.add_regions(bpId, mark, "breakpoint", "../"+_corona_utils.PACKAGE_NAME+"/CoronaBP", sublime.HIDDEN)
        else:
          view.add_regions(bpId, mark, "breakpoint", "Packages/"+_corona_utils.PACKAGE_NAME+"/CoronaBP.png", sublime.HIDDEN)
      result = True

    # Save the breakpoints for posterity
    debug("coronaBreakpoints: " + str(coronaBreakpoints))
    coronaBreakpointsSettings.set("breakpoints", coronaBreakpoints)
    sublime.save_settings(_corona_utils.PACKAGE_NAME + ".breakpoints")

    return result

  def view_for_file(self, filename):
    for view in sublime.active_window().views():
      if view.file_name() == filename:
        return view
    return None

  def new_breakpoint_id(self, filename, lineno):
    return filename + str(lineno)

  def initializeWindowPanes(self):
    self.window.set_layout({"cols":[0,0.6,1],"rows":[0,0.5,0.7,1],"cells":[[0,0,2,1],[0,1,2,2],[0,2,1,3],[1,2,2,3]]})

    self.window_panes = [{'group': 0, 'tag': 'code', 'title': ''},
                         {'group': 1, 'tag': 'console', 'title': 'Console'},
                         {'group': 2, 'tag': 'variables', 'title': 'Variables'},
                         {'group': 3, 'tag': 'stack', 'title': 'Lua Stack'}]

    for w in self.window_panes:
      views = self.window.views_in_group(w['group'])
      if len(views) is 0:
        view = self.window.new_file()
        view.set_name(w['title'])
        view.settings().set('word_wrap', False)
        view.set_read_only(True)
        view.set_scratch(True)
        view.run_command("toggle_setting", {"setting": "line_numbers"})
        self.window.set_view_index(view, w['group'], 0)
        # outputToPane(w['title'], "this is " + w['title'])

  def closeWindowPanes(self):
    if self.window.num_groups() > 1:
      for view in self.window.views():
        group, index = self.window.get_view_index(view)
        if group > 0:
          debug("Closing: " + view.name())
          self.window.focus_view(view)
          self.window.run_command("close_file")
      # print("saved_layout: " + str(self.saved_layout))
      self.window.run_command("set_layout", {"cells": [[0, 0, 1, 1]], "cols": [0.0, 1.0], "rows": [0.0, 1.0]})
      self.view.erase_regions("current_line")


def debugger_status(msg):
  debug("debugger_status: " + msg)
  sublime.set_timeout(lambda: sublime.status_message(msg), 0)


def on_main_thread(callee):
  sublime.set_timeout(callee, 0)


def console_output(text):
  if subProcOutputQ is not None:
    # if the line doesn't end with a newline, add one
    if text[-1] != "\n":
      text += "\n"
    # Remove cruft from Simulator output
    text = re.sub(r'Corona Simulator\[\d+:\d+\] ', '', text, 1)
    subProcOutputQ.put(text, 1)
    sublime.set_timeout(lambda: outputToPane('Console', None, False), 0)


def variables_output(text):
  if subProcOutputQ is not None:
    # if the line doesn't end with a newline, add one
    if text[-1] != "\n":
      text += "\n"
    subProcOutputQ.put(text, 1)
    sublime.set_timeout(lambda: outputToPane('Variables', None, True), 0)


def stack_output(text):
  if subProcOutputQ is not None:
    # if the line doesn't end with a newline, add one
    if text[-1] != "\n":
      text += "\n"
    subProcOutputQ.put(text, 1)
    sublime.set_timeout(lambda: outputToPane('Lua Stack', None, True), 0)


def outputToPane(name, text, erase=True):
  queueing = False
  if text is None:
    text = subProcOutputQ.get()
    queueing = True
  # debug("outputToPane: name: " + name + "text: " + text)
  window = sublime.active_window()
  for view in window.views():
    if view.name() == name:
      view.set_read_only(False)
      if _corona_utils.SUBLIME_VERSION < 3000:
        edit = view.begin_edit()
        # print("name: ", name, "size: ", view.size())
        if erase:
          view.erase(edit, sublime.Region(0, view.size()))
          view.insert(edit, 0, text)
        else:
          view.insert(edit, view.size(), text)
        view.end_edit(edit)
      else:  # It's ST3
        if erase:
          view.run_command("select_all")
          view.run_command("right_delete")
        view.run_command('append', {'characters': text})

      view.set_read_only(True)
      # view.set_viewport_position((0, view.size())) # scroll to the end
      view.show(view.size(), True)  # scroll to the end, works better on Windows
  if queueing:
    subProcOutputQ.task_done()


class CoronaSubprocessThread(threading.Thread):

  def __init__(self, cmd, completionCallback=None, window=None, threadID=1):
    threading.Thread.__init__(self)
    self.threadID = threadID
    self.cmd = cmd
    self.completionCallback = completionCallback
    self.window = window
    self.proc = None

  def terminate(self):
    if self.proc.poll() is None:
      self.proc.terminate()

  def run(self):
    debug("Running: " + str(self.cmd))
    if sublime.platform() == "windows":
      closeFDs = False
    else:
      closeFDs = True

    self.proc = subprocess.Popen(self.cmd, bufsize=0, close_fds=closeFDs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    while self.proc.poll() is None:
        try:
          data = self.proc.stdout.readline().decode('UTF-8')
          # this isn't the same as "print()": sys.stdout.write(data)
          # print("Read: " + data)
          console_output(data)
        except IndexError as e:
          break  # we get this when the child process has terminated
        except Exception as e:
          console_output("Exception reading from coprocess: "+str(e))

    on_main_thread(lambda: self.completionCallback(self.threadID, self.window))

    debug("CoronaSubprocessThread: ends (proc.poll(): " + str(self.proc.poll()) + ")")


def CompleteSubprocess(threadID, window):
  debug("CompleteSubprocess: called (" + str(threadID) + ")")
  # debug("CompleteSubprocess: window " + str(window))
  # window.run_command("corona_debugger", {"cmd": "stop"})


def RunSubprocess(cmd, window):
  global coronaDbgThread
  coronaDbgThread = CoronaSubprocessThread(cmd, CompleteSubprocess, window)
  coronaDbgThread.start()


def StopSubprocess():
  global coronaDbgThread
  debug("StopSubprocess: " + str(coronaDbgThread))
  if coronaDbgThread is not None and coronaDbgThread.is_alive():
    coronaDbgThread.terminate()
    coronaDbgThread.join()

########NEW FILE########
__FILENAME__ = mk_sublime_completions
#!/usr/bin/python
#
# Sublime Text plugin to support Corona SDK
#
# Copyright (c) 2013 Corona Labs Inc. A mobile development software company. All rights reserved.
#
# MIT License - see https://raw.github.com/coronalabs/CoronaSDK-SublimeText/master/LICENSE
#

import re
import string
import json
import sys

preamble = """
{
    "scope": "source.lua",

      "completions":
        [
"""

postamble = """
    ]
}
"""

if len(sys.argv) != 2:
  print("Usage: "+ sys.argv[0] + " <raw-completions>")
  sys.exit(1)

fh = open(sys.argv[1])

print(preamble)
output = ""

for line in fh.readlines():
  typeDesc = "unknown"
  line = line.strip()
  # print(line)
  if line.find(':') != -1:
    # We have a type member, since we can't know what the object is called,
    # complete from the semi-colon only
    line = line.partition(':')[2]

  if line.find("\t") != -1:
    # We have a type description after a tab
    typeDesc = line.partition("\t")[2]
    line = line.partition("\t")[0]

  if output != "":
    output += ",\n"

  argListMatch = re.search("\((.*)\)", line)

  if argListMatch != None:
    argsString = argListMatch.groups()[0]
    funcName = line.replace("("+argsString+")", "")
    funcName = funcName.strip()
    args = re.findall("(\[.*?\]|[^\[,]*)", argsString)
    # print("   funcName", funcName)
    # print("   argsString", argsString)
    # print("   args", args)
    argCount = 1
    stCompArgs = ""
    for arg in args:
      arg = arg.strip()
      if arg == "":
        continue
      arg = json.dumps(arg)[1:-1] # escape JSON and remove surrounding quotes
      # if the arg is not optional and includes a comma, add a comma
      if not arg.startswith("[,"):
        stCompArgs += ","
      stCompArgs += " ${"+str(argCount)+":"+arg+"}"
      argCount += 1
    stCompArgs = stCompArgs.lstrip(",");
    # print("stCompArgs: ", stCompArgs)
    output += "{{ \"trigger\": \"{0}()\\t{2}\", \"contents\": \"{0}({1} )\"}}".format(funcName, stCompArgs, typeDesc)
  else:
    output += "{{ \"trigger\": \"{0}\\t{1}\", \"contents\": \"{0}\"}}".format(line, typeDesc)

print(output)
print(postamble)

########NEW FILE########
__FILENAME__ = run_project
#
# Sublime Text plugin to support Corona Editor
#
# Copyright (c) 2013 Corona Labs Inc. A mobile development software company. All rights reserved.
#
# MIT License - see https://raw.github.com/coronalabs/CoronaSDK-SublimeText/master/LICENSE

import sublime
import sublime_plugin

try:
  from . import _corona_utils  # P3
except:
  import _corona_utils  # P2


class ToggleBuildPanelCommand(sublime_plugin.WindowCommand):

  def __init__(self, window):
    self.window = window
    self.output_panel = None

  def run(self):
    # The output panel content is cleared anytime "get_output_panel()" is called
    # so we minimize how often we do that
    if self.output_panel is None:
      self.output_panel = self.window.get_output_panel("exec")
    if self.output_panel.window():
      self.window.run_command("hide_panel", {"panel": "output.exec"})
    else:
      self.window.run_command("show_panel", {"panel": "output.exec"})

  def description(self):
    if self.output_panel is None:
      self.output_panel = self.window.get_output_panel("exec")
    if self.output_panel.window():
      return "Hide Build Panel"
    else:
      return "Show Build Panel"


class RunProjectCommand(sublime_plugin.WindowCommand):

  # find a main.lua file to start the Simulator with or failing that, any open Lua
  # file we can use as a place to start looking for a main.lua
  def findLuaFile(self):
    filename = self.window.active_view().file_name()
    if filename is None or not filename.endswith(".lua"):
      filename = None
      # No current .lua file, see if we have one open
      for view in self.window.views():
        if view.file_name() and view.file_name().endswith(".lua"):
          filename = view.file_name()
    return filename

  def is_enabled(self):
    return self.findLuaFile() is not None

  def run(self):
    cmd = []

    filename = self.findLuaFile()

    if filename is None:
      sublime.error_message("Can't find an open '.lua' file to determine the location of 'main.lua'")
      return
    mainlua = _corona_utils.ResolveMainLua(filename)
    if mainlua is None:
      sublime.error_message("Can't locate 'main.lua' for this project (try opening it in an editor tab)")
      return

    simulator_path, simulator_flags = _corona_utils.GetSimulatorCmd(mainlua)

    cmd = [simulator_path]
    cmd += simulator_flags
    cmd.append(mainlua)

    print(_corona_utils.PACKAGE_NAME + ": Running: " + str(cmd))

    # Save our changes before we run
    self.window.run_command("save")

    self.window.run_command('exec', {'cmd': cmd})

########NEW FILE########
__FILENAME__ = snippets
#
# Sublime Text plugin to support Corona Editor
#
# Copyright (c) 2013 Corona Labs Inc. A mobile development software company. All rights reserved.
#
# MIT License - see https://raw.github.com/coronalabs/CoronaSDK-SublimeText/master/LICENSE

import sublime
import sublime_plugin
import os.path
import json
import threading
import re
import zipfile
import tempfile
from xml.dom import minidom

try:
  from . import completions  # P3
except:
  import completions  # P2

try:
  from . import _corona_utils  # P3
except:
  import _corona_utils  # P2


def XMLGetText(nodelist):
  parts = []
  for node in nodelist:
    if node.nodeType == node.TEXT_NODE:
      parts.append(node.data)
  return ''.join(parts)


def UnZIPToDir(zipFilePath, destDir):
  zfile = zipfile.ZipFile(zipFilePath)
  for name in zfile.namelist():
    (dirName, fileName) = os.path.split(name)
    if fileName == '':
      # directory
      newDir = os.path.join(destDir, dirName)
      if not os.path.exists(newDir):
        os.makedirs(newDir)
    else:
      # file
      path = os.path.join(destDir, name)
      # print("Unzip: " + path)
      fd = open(path, 'wb')
      fd.write(zfile.read(name))
      fd.close()
  zfile.close()


class CoronaSnippetFolderIndexer(threading.Thread):
  _initialized = False
  _snippets_dir = None

  def __init__(self):
    threading.Thread.__init__(self)

  def run(self):

    # Wait for _corona_utils initialization to complete
    # print("Waiting for InitializedEvent...")
    _corona_utils.InitializedEvent.wait()

    self._snippets_dir = os.path.join(_corona_utils.PACKAGE_USER_DIR, "Snippets")

    if not os.path.exists(self._snippets_dir):
      os.makedirs(self._snippets_dir)
      print(_corona_utils.PACKAGE_NAME + ": Extracting snippets ...")
      try:
        # In ST3 our ZIP file is not on the filesystem, it's in our package so we have to extract
        # it and unzip from there (to work on Windows the temp file must be closed before it can
        # be reopened to be unzipped)
        zip_bytes = sublime.load_binary_resource(_corona_utils.ST_PACKAGE_PATH + "snippets.zip")
        with tempfile.NamedTemporaryFile(suffix = ".zip", delete=False) as tempzip:
          tempzip.write(zip_bytes)
          tempzip.close()
          UnZIPToDir(tempzip.name, self._snippets_dir)
          os.remove(tempzip.name)
      except:
        # We're on ST2 and the ZIP file is just a file in our package directory
        UnZIPToDir(os.path.join(_corona_utils.PACKAGE_DIR, "snippets.zip"), self._snippets_dir)

    snippetMenuArray = []
    snippetJSON = ""

    if os.path.isdir(self._snippets_dir):
      snippetMenuArray = self.addDirectory(self._snippets_dir)
      snippetJSON = json.dumps(snippetMenuArray, indent=4, separators=(',', ': '))

    if snippetJSON == "":
      print(_corona_utils.PACKAGE_NAME + ": Failed to build Snippets menu")
      return

    # Put our menu into the Main.sublime-menu.template file
    menus = ""
    if _corona_utils.SUBLIME_VERSION < 3000:
      with open(os.path.join(_corona_utils.PACKAGE_DIR, "Main.sublime-menu.template"), "r") as fd:
          menus = fd.read()
    else:
      menus = sublime.load_resource(_corona_utils.ST_PACKAGE_PATH + "Main.sublime-menu.template")

    if menus == "":
      print(_corona_utils.PACKAGE_NAME + ": Failed to create Snippets menu")
      return

    menus = menus.replace("$corona_snippets", snippetJSON)

    if not os.path.exists(_corona_utils.PACKAGE_DIR):
      os.makedirs(_corona_utils.PACKAGE_DIR)
    if _corona_utils.SUBLIME_VERSION < 3000:
      with open(os.path.join(_corona_utils.PACKAGE_DIR, "Main.sublime-menu"), "w") as fd:
          fd.write("// Generated file - do not edit - modify 'Main.sublime-menu.template' instead\n")
          fd.write(menus)
    else:  # ST3/P3
      with open(os.path.join(_corona_utils.PACKAGE_DIR, "Main.sublime-menu"), "w", encoding='utf-8') as fd:
          fd.write("// Generated file - do not edit - modify 'Main.sublime-menu.template' instead\n")
          fd.write(menus)

  def addDirectory(self, path):
    jsonArray = []
    pathnames = os.listdir(path)
    for pathname in pathnames:
      if pathname.startswith(".") or pathname == "README.md":
        continue
      realpath = os.path.join(path, pathname)
      # _corona_utils.debug("realpath: " + realpath)
      if os.path.isdir(realpath):
        jsonArray.append({"caption": pathname, "children": self.addDirectory(realpath)})
      else:
        # Parse XML snippet file to get the "Description"
        if realpath.endswith(".sublime-snippet"):
          # _corona_utils.debug("Parsing: " + realpath)
          try:
            xmldoc = minidom.parse(realpath)
          except:
            print(_corona_utils.PACKAGE_NAME + ": Invalid XML in " + realpath)
          else:
            desc = XMLGetText(xmldoc.getElementsByTagName('description')[0].childNodes)
            if desc is None:
              desc = path
        else:
          desc = pathname

        jsonArray.append({"caption": desc, "command": "corona_snippet", "args": {"file": realpath}})

    return jsonArray


# This is run automatically after the plugin has loaded in ST3
def plugin_loaded():
  # Index the "snippets" directory in the background
  indexer = CoronaSnippetFolderIndexer()
  indexer.start()

# We need to run it manually in ST2
if _corona_utils.SUBLIME_VERSION < 3000:
  plugin_loaded()


class CoronaSnippetCommand(sublime_plugin.TextCommand):
  _comps = None

  def run(self, edit, **args):

    if 'name' in args:
      trigger = args['name']
    else:
      trigger = args['file']

    if self._comps is None:
      completions.CoronaCompletions.initialize()
      self._comps = completions.CoronaCompletions._completions

    # print("CoronaSnippetCommand:")
    # print(str(self._comps))
    # print(str(len(self._comps['completions'])) + " completions available")

    # print("trigger: " + trigger)
    if trigger.endswith(".sublime-snippet"):
      # The command wants names in the form: "Packages/User/Snippets/foo.sublime-snippet" so we
      # need to remove everything in the path before "Packages" and convert backslashes to slashes
      # (TODO: note that this wont work for a user called "Packages")
      trigger = re.sub(r'.*Packages', "Packages", trigger, 1)
      trigger = trigger.replace('\\', '/')
      print("modified trigger: " + trigger)
      self.view.run_command("insert_snippet", {"name": trigger})
    else:
      # Find a completion keyed by the contents of the snippet file
      with open(trigger, "r") as fd:
        lookup = fd.read().strip()

      key = [key for key, item in enumerate(self._comps['completions']) if item['trigger'].lower().startswith(lookup.lower())]
      if key is not None and len(key) != 0:
        self.view.run_command("insert_snippet", {"contents": self._comps['completions'][key[0]]['contents']})
      else:
        self.view.run_command('insert', {'characters': lookup})

########NEW FILE########
__FILENAME__ = _corona_utils
#
# Sublime Text plugin to support Corona Editor
#
# Copyright (c) 2013 Corona Labs Inc. A mobile development software company. All rights reserved.
#
# MIT License - see https://raw.github.com/coronalabs/CoronaSDK-SublimeText/master/LICENSE

# Note: the leading underscore on the name of this module forces Sublime Text to load it first which
# prevents it being loaded more than once (once when it's first imported, e.g. by about.py, and then
# again when it comes up in the load order)

import sublime
import os
import re
import threading

SUBLIME_VERSION = "not set"
PLUGIN_PATH = "not set"
PACKAGE_NAME = "not set"
PACKAGE_DIR = "not set"
PACKAGE_USER_DIR = "not set"
ST_PACKAGE_PATH = "not set"

# In Sublime Text 3 most APIs are unavailable until a module level function is called (fortunately
# sublime.version() is available so we can correctly fake things in Sublime Text 2; see about.py)
SUBLIME_VERSION = 3000 if sublime.version() == '' else int(sublime.version())


def debug(*args):
  for arg in args:
    print("Corona Editor: " + str(arg))


InitializedEvent = threading.Event()


def Init():
  global SUBLIME_VERSION
  global PLUGIN_PATH
  global PACKAGE_NAME
  global PACKAGE_DIR
  global PACKAGE_USER_DIR
  global ST_PACKAGE_PATH

  PLUGIN_PATH = os.path.dirname(os.path.realpath(__file__))
  if PLUGIN_PATH.lower().endswith('coronasdk-sublimetext'):
    if SUBLIME_VERSION < 3000:
      PLUGIN_PATH = os.path.expanduser('~/Library/Application Support/Sublime Text 2/Packages/Corona Editor')
    else:
      PLUGIN_PATH = os.path.expanduser('~/Library/Application Support/Sublime Text 3/Packages/Corona Editor')
  debug("PLUGIN_PATH: " + PLUGIN_PATH)

  PACKAGE_NAME = os.path.basename(PLUGIN_PATH) if SUBLIME_VERSION < 3000 else os.path.basename(PLUGIN_PATH).replace(".sublime-package", "")
  debug("PACKAGE_NAME: " + PACKAGE_NAME)

  # This is the actual package dir on ST2 and the "unpacked" package dir on ST3 ("~/Library/Application Support/Sublime Text 2/Packages")
  PACKAGE_DIR = os.path.join(sublime.packages_path(), PACKAGE_NAME)
  debug("PACKAGE_DIR: " + PACKAGE_DIR)

  # This is the user dir on ST
  PACKAGE_USER_DIR = os.path.join(sublime.packages_path(), 'User', PACKAGE_NAME)
  debug("PACKAGE_USER_DIR: " + PACKAGE_USER_DIR)

  # This is the faux path used by various Sublime Text functions ("Packages/CoronaSDK/")
  ST_PACKAGE_PATH = "Packages/" + PACKAGE_NAME + "/"
  debug("ST_PACKAGE_PATH: " + ST_PACKAGE_PATH)

  # This allows other threads to wait until this code has run
  InitializedEvent.set()


# This is run by ST3 after the plugins have loaded (and the ST API is ready for calls)
def plugin_loaded():
  Init()

# This fakes the above functionality on ST2
if SUBLIME_VERSION < 3000:
  Init()


# Return the path to the Simulator for the current project and platform
# First we look in any build.settings file in the project, then we look
# for a user preference, then we pick a platform appropriate default
def GetSimulatorCmd(mainlua=None, debug=False):
  platform = sublime.platform()
  arch = sublime.arch()
  view = sublime.active_window().active_view()

  simulator_path = ""
  simulator_flags = []

  if mainlua is not None:
    simulator_path = GetSimulatorPathFromBuildSettings(mainlua)
    if simulator_path is None:
      simulator_path = GetSetting("corona_sdk_simulator_path", None)

  if platform == "osx":
    if simulator_path is None:
      simulator_path = "/Applications/CoronaSDK/Corona Simulator.app"
    if simulator_path.endswith(".app"):
      simulator_path += "/Contents/MacOS/Corona Simulator"
    simulator_flags = ["-singleton", "1"]
    if debug:
      simulator_flags.append("-debug")
      simulator_flags.append("1")
      simulator_flags.append("-project")
  elif platform == 'windows':
    if simulator_path is None:
      if arch == "x64":
        simulator_path = "C:\\Program Files (x86)\\Corona Labs\\Corona SDK\\Corona Simulator.exe"
      else:
        simulator_path = "C:\\Program Files\\Corona Labs\\Corona SDK\\Corona Simulator.exe"
    simulator_flags = ["/singleton", "/no-console"]
    if debug:
      simulator_flags.append("/debug")

  # Can we find an executable file at the path
  if not os.path.isfile(simulator_path) or not os.access(simulator_path, os.X_OK):
    sublime.error_message("Cannot find executable Corona Simulator at path '{0}'\n\nYou can set the user preference 'corona_sdk_simulator_path' to the location of the Simulator.".format(simulator_path))
    return None, None

  return simulator_path, simulator_flags


# Given a path to a main.lua file, see if there's a "corona_sdk_simulator_path" setting in
# the corresponding build.settings file
def GetSimulatorPathFromBuildSettings(mainlua):
  simulator_path = None
  project_path = os.path.dirname(mainlua)
  build_settings = os.path.join(project_path, "build.settings")
  bs_contents = None
  if os.path.isfile(build_settings):
    try:
      with open(build_settings, "r") as bs_fd:
        bs_contents = bs_fd.read()
    except IOError:
      pass  # we don't care if the file doesn't exist

  if bs_contents is not None:
    # Remove comments
    bs_contents = re.sub(r'--.*', '', bs_contents)
    # Note we can't use a Python r'' string here because we then can't escape the single quotes
    bs_matches = re.findall('corona_sdk_simulator_path\s*=\s*["\'](.*)["\']', bs_contents)
    if bs_matches is not None and len(bs_matches) > 0:
      # Last one wins
      simulator_path = bs_matches[-1]
      debug("GetSimulatorPathFromBuildSettings: simulator_path '"+str(simulator_path)+"'")

  return simulator_path


# Given an existing file path or directory, find the likely "main.lua" for this project
def ResolveMainLua(path):
  # debug("ResolveMainLua: path: "+str(path))
  path = os.path.abspath(path)
  if not os.path.isdir(path):
    path = os.path.dirname(path)

  mainlua = os.path.join(path, "main.lua")
  if mainlua == "/main.lua" or mainlua == "\\main.lua":
    return None
  elif os.path.isfile(mainlua):
    return mainlua
  else:
    return ResolveMainLua(os.path.join(path, ".."))

def GetSetting(key,default=None):
  # repeated calls to load_settings return same object without further disk reads
  s = sublime.load_settings('Corona Editor.sublime-settings')
  print("GetSetting: ", key, s.get(key, default))
  return s.get(key, default)


########NEW FILE########
