__FILENAME__ = ensime_client
import os, sys, stat, time, datetime, re
import functools, socket, threading
import sublime_plugin, sublime
import sexp
from string import strip
from sexp import key,sym
import ensime_notes
import traceback
import Queue

class EnsimeMessageHandler:

  def on_data(self, data):
    pass

  def on_disconnect(self, reason):
    pass

class EnsimeServerClient:

  def __init__(self, project_root, handler):
    self.project_root = project_root
    self.connected = False
    self.handler = handler
    self._lock = threading.RLock()
    self._connect_lock = threading.RLock()
    self._receiver = None

  def port(self):
    return int(open(self.project_root + "/.ensime_port").read()) 

  def receive_loop(self):
    while self.connected:
      try:
        res = self.client.recv(4096)
        print "RECV: " + unicode(res, "utf-8")
        if res:
          len_str = res[:6]
          msglen = int(len_str, 16) + 6
          msg = res[6:msglen]
          nxt = strip(res[msglen:])
          while len(nxt) > 0 or len(msg) > 0:
            form = sexp.read(msg)
            sublime.set_timeout(functools.partial(self.handler.on_data, form), 0)
            if len(nxt) > 0:
              msglen = int(nxt[:6], 16) + 6
              msg = nxt[6:msglen]
              nxt = strip(nxt[msglen:])
            else: 
              msg = ""
              msglen = ""
        else:
          self.set_connected(False)
      except Exception as e:
        print "*****    ERROR     *****"
        print e
        self.handler.on_disconnect("server")
        self.set_connected(False)

  def set_connected(self, val):
    self._lock.acquire()
    try:
      self.connected = val
    finally:
      self._lock.release()

  def start_receiving(self):
    t = threading.Thread(name = "ensime-client-" + str(self.port()), target = self.receive_loop)
    t.setDaemon(True)
    t.start()
    self._receiver = t

  def connect(self):
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.connect(("127.0.0.1", self.port()))
      self.client = s
      self.set_connected(True)
      self.start_receiving()
      return s
    except socket.error as e:
      # set sublime error status
      self.set_connected(False)
      sublime.error_message("Can't connect to ensime server:  " + e.args[1])
    finally:
      self._connect_lock.release()

  def send(self, request):
    try:
      if not self.connected:
        self.connect()
      self.client.send(request)
    except:
      self.handler.disconnect("server")
      self.set_connected(False)

  def sync_send(self, request, msg_id): 
    self._connect_lock.acquire()
    try:
      s = socket.socket()
      s.connect(("127.0.0.1", self.port()))
      try:
        s.send(request)
        result = ""
        keep_going = True
        nxt = ""
        while keep_going: 
          res = nxt + s.recv(4096)
          msglen = int(res[:6], 16) + 6
          msg = res[6:msglen]
          if (len(msg) + 6) == msglen:
            nxt = strip(res[msglen:])
            while len(nxt) > 0 or len(msg) > 0:
              if len(nxt) > 0:
                sublime.set_timeout(functools.partial(self.handler.on_data, sexp.read(msg)), 0)
                msglen = int(nxt[:6], 16) + 6
                msg = nxt[6:msglen]
                nxt = strip(nxt[msglen:])
              else: 
                nxt = ""
                break
            result = sexp.read(msg)
            keep_going = result == None or msg_id != result[-1]
            if keep_going:
              sublime.set_timeout(functools.partial(self.handler.on_data, result), 0)
          else:
            nxt = res 
            
        return result
      except Exception as error:
        print error
      finally:
        if s: 
          s.close() 
    except Exception as error:
      print error
    finally:
      self._connect_lock.release()

  def close(self):
    self._connect_lock.acquire()
    try:
      if self.client:
        self.client.close()
      self.connect = False
    finally:
      self._connect_lock.release()    

class EnsimeClient(EnsimeMessageHandler):

  def __init__(self, settings, window, project_root):
    def ignore(d): 
      None      

    def clear_notes(lang):
      self.note_map = {}
      for v in self.window.views():
        v.run_command("ensime_notes", 
                      {"lang": lang, 
                       "action": "clear"})

    def add_notes(lang, data):
      m = sexp.sexp_to_key_map(data)
      new_notes = [sexp.sexp_to_key_map(form) for form in m[":notes"]]

      for note in new_notes:
        key = os.path.realpath(str(note[":file"]))
        view_notes = self.note_map.get(key) or []
        view_notes.append(note)
        self.note_map[key] = view_notes

      for v in self.window.views():
        key = os.path.realpath(str(v.file_name()))
        notes = self.note_map.get(key) or []
        v.run_command(
          "ensime_notes",
          { "lang": lang, "action": 
            "add", "value": notes })

    # maps filenames to lists of notes
    self.note_map = {}

    self.settings = settings
    self.project_root = project_root
    self._ready = False
    self._readyLock = threading.RLock()
    self.window = window
    self.output_view = self.window.get_output_panel("ensime_messages")
    self.message_handlers = dict()
    self.procedure_handlers = dict()
    self._counter = 0
    self._procedure_counter = 0
    self._counterLock = threading.RLock()
    self.client = EnsimeServerClient(project_root, self)
    self._reply_handlers = {
      ":ok": lambda d: self.message_handlers[d[-1]](d),
      ":abort": lambda d: sublime.status_message(d[-1]),
      ":error": lambda d: sublime.error_message(d[-1])
    }
    self._server_message_handlers = {
      ":clear-all-scala-notes": lambda d: clear_notes("scala"),
      ":clear-all-java-notes": lambda d: clear_notes("java"),
      ":scala-notes": lambda d: add_notes("scala", d),
      ":java-notes": lambda d: add_notes("java", d),
      ":compiler-ready": 
      lambda d: self.window.run_command("random_words_of_encouragement"),
      ":full-typecheck-finished": ignore,
      ":indexer-ready": ignore,
      ":background-message": sublime.status_message
    }
      
  def ready(self):
    return self._ready

  def set_ready(self):
    self._readyLock.acquire()
    try:
      self._ready = True
      return self.ready()
    finally:
      self._readyLock.release()

  def set_not_ready(self):
    self._readyLock.acquire()
    try:
      self._ready = False
      return self.ready()
    finally:
      self._readyLock.release()

  def remove_handler(self, handler_id):
    del self.message_handlers[handler_id]

  def on_data(self, data):
    print "on_data: " + str(data)
    self.feedback(str(data))
    # match a message with a registered response handler.
    # if the message has no registered handler check if it's a 
    # background message.
    if data[0] == key(":return"):
      th = self._reply_handlers

      # if data[0][0][0][1:] == "procedure-id" and self.procedure_handlers.has_key(data[0][0][1]):
      #   self.procedure_handlers[data[0][0][1]](data)
      #   del self.proceure_handlers[data[0][0][1]]

      if self.message_handlers.has_key(data[-1]):
        reply_type = str(data[1][0])
        th[reply_type](data)
      else:
        print "Unhandled message: " + str(data)
    else:
        self.handle_server_message(data)

  def handle_server_message(self, data):
    print "handle_server_message: " + str(data)
    handled = self._server_message_handlers
    try:
      key = str(data[0])
      if handled.has_key(key):
        handled[key](data[-1])
      else:
        print "Received a message from the server:"
        print str(data)
    except Exception as e:
      print "Error when handling server message: " + str(data)
      traceback.print_exc(file=sys.stdout)

  def next_message_id(self):
    self._counterLock.acquire()
    try:
      self._counter += 1
      return self._counter
    finally:
      self._counterLock.release()

  def next_procedure_id(self):
    self._counterLock.acquire()
    try:
      self._procedure_counter += 1
      return self._procedure_counter
    finally:
      self._counterLock.release()

  def feedback(self, msg):
    self.window.run_command("ensime_update_messages_view", { 'msg': msg })

  def on_disconnect(self, reason = "client"):
    self._counterLock.acquire()
    try:
      self._counter = 0
      self._procedure_counter = 0
    finally:
      self._counterLock.release()
      
    if reason == "server":
      sublime.error_message("The ensime server was disconnected, you might want to restart it.")

  def project_file(self): 
    if self.ready:
      return os.path.join(self.project_root, ".ensime")
    else:
      return None

  def project_config(self):
    try:
      src = open(self.project_file()).read() if self.project_file() else "()"
      conf = sexp.read(src)
      return conf
    except StandardError:
      return []
    
  
  def prepend_length(self, data): 
    return "%06x" % len(data) + data

  def format(self, data, count = None):
    if count:
      return [key(":swank-rpc"), data, count]
    else:
      return [key(":swank-rpc"), data]

  
  def req(self, to_send, on_complete = None, msg_id = None): 
    msgcnt = msg_id
    if msg_id == None:
      msgcnt = self.next_message_id()
      
    if self.ready() and not self.client.connected:
      self.client.connect()

    msg = None
    if on_complete != None:
      self.message_handlers[msgcnt] = on_complete
      msg = self.format(to_send, msgcnt)
    else:
      msg = self.format(to_send)

    msg_str = sexp.to_string(msg)

    print "SEND: " + msg_str

    sublime.set_timeout(functools.partial(self.feedback, msg_str), 0)
    self.client.send(self.prepend_length(msg_str))

  def sync_req(self, to_send):
    msgcnt = self.next_message_id()
    msg_str = sexp.to_string(self.format(to_send, msgcnt))
    print "SEND: " + msg_str
    return self.client.sync_send(self.prepend_length(msg_str), msgcnt)
    

  def disconnect(self):
    self._counterLock.acquire()
    try:
      self._counter = 0
      self._procedure_counter = 0
    finally:
      self._counterLock.release()
    self.client.close()

  def handshake(self, on_complete): 
    self.req([sym("swank:connection-info")], on_complete)

  def __initialize_project(self, conf, subproj_name, on_complete):
    conf = conf + [key(":root-dir"), self.project_root]
    conf = conf + [key(":active-subproject"), subproj_name]
    self.req([sym("swank:init-project"), conf], on_complete)

  def initialize_project(self, on_complete):
    conf = self.project_config()
    m = sexp.sexp_to_key_map(conf)
    subprojects = [sexp.sexp_to_key_map(p) for p in m[":subprojects"]]
    names = [p[":name"] for p in subprojects]
    if len(names) > 1:
      self.window.show_quick_panel(
        names, lambda i: self.__initialize_project(conf,names[i],on_complete))
    elif len(names) == 1:
      self.__initialize_project(conf,names[0],on_complete)
    else:
      self.__initialize_project(conf,"NA",on_complete)

  def format_source(self, file_path, on_complete):
    self.req([sym("swank:format-source"),[file_path]], on_complete)

  def type_check_all(self, on_complete):
    self.req([sym("swank:typecheck-all")], on_complete)

  def type_check_file(self, file_path, on_complete):
    self.req([sym("swank:typecheck-file"), file_path], on_complete)

  def organize_imports(self, file_path, on_complete):
    self.req([sym("swank:perform-refactor"),
              self.next_procedure_id(),
              sym("organizeImports"), 
              [sym("file"),file_path], 
              True], on_complete)
  
  def perform_organize(self, previous_id, msg_id, on_complete):
    self.req([sym("swank:exec-refactor"),
              int(previous_id), 
              sym("organizeImports")], 
             on_complete, int(msg_id))

  def inspect_type_at_point(self, file_path, position, on_complete):
    self.req([sym("swank:type-at-point"),
              file_path,
              int(position)], 
             on_complete)
  
  def complete_member(self, file_path, position):
    return self.sync_req([sym("swank:completions"), file_path, position, 0])

########NEW FILE########
__FILENAME__ = ensime_commands
import os, sys, stat, random, getpass
import ensime_environment
from ensime_server import EnsimeOnly
import functools, socket, threading
import sublime_plugin, sublime


def save_view(view):
  if view == None or view.file_name == None:
    return
  content = view.substr(sublime.Region(0, view.size()))
  with open(view.file_name(), 'wb') as f:
    f.write(content.encode("UTF-8"))
                
class EnsimeReformatSourceCommand(sublime_plugin.TextCommand, EnsimeOnly):

  def handle_reply(self, data):
    self.view.run_command('revert')
    self.view.set_status("ensime", "Formatting done!")
    ensime_environment.ensime_env.client().remove_handler(data[-1])

  def run(self, edit):
    #ensure_ensime_environment.ensime_env()
    vw = self.view
    if vw.is_dirty():
      vw.run_command("save")
    ensime_environment.ensime_env.client().format_source(vw.file_name(), self.handle_reply)

class RandomWordsOfEncouragementCommand(sublime_plugin.WindowCommand, EnsimeOnly):

  def run(self):
    if not hasattr(self, "phrases"):
      self.phrases = [
        "Let the hacking commence!",
        "Hacks and glory await!",
        "Hack and be merry!",
        "May the source be with you!",
        "Death to null!",
        "Find closure!",
        "May the _ be with you.",
        "CanBuildFrom[List[Dream], Reality, List[Reality]]"
      ]  
    msgidx = random.randint(0, len(self.phrases) - 1)
    msg = self.phrases[msgidx]
    sublime.status_message(msg + " This could be the start of a beautiful program, " + 
      getpass.getuser().capitalize()  + ".")

class EnsimeTypeCheckAllCommand(sublime_plugin.WindowCommand, EnsimeOnly):

  def handle_reply(self, data):
    print "got reply for type check all:"
    print data
    ensime_environment.ensime_env.client().remove_handler(data[-1])

  def run(self):
    ensime_environment.ensime_env.client().type_check_all(self.handle_reply)

class EnsimeTypeCheckFileCommand(sublime_plugin.TextCommand, EnsimeOnly):

  def handle_reply(self, data):
    print "got reply for type check file:"
    print data

  def run(self, edit):
    vw = self.view
    fname = vw.file_name()
    if fname:
      if vw.is_dirty():
        vw.run_command("save")

      repl = self.handle_reply
      cl = ensime_environment.ensime_env.client()
      if not cl is None:
        cl.type_check_file(fname, repl)

class EnsimeOrganizeImportsCommand(sublime_plugin.TextCommand, EnsimeOnly):

  def handle_reply(self, edit, data):
    if data[1][1][5] == "success":
      ov = self.view.window().new_file()

      ov.set_syntax_file(self.view.settings().get('syntax'))
      ov.set_scratch(True)

      prelude = "/*\n   Confirm that you want to make this change.\n   Hitting enter with a string of yes is to confirm any other string or esc cancels.\n*/\n\n\n"
      start = data[1][1][7][0][5]
      end = data[1][1][7][0][7]
      new_cntnt = data[1][1][7][0][3]

      prev = self.view.substr(sublime.Region(0, start))

      on_done = functools.partial(self.on_done, data[1][1][1], data[-1], ov)
 
      new_cntnt = new_cntnt.replace('\r\n', '\n').replace('\r', '\n')
 
      cl = ensime_environment.ensime_env.client()
      cl.window.show_quick_panel(["Accept changes", "Reject changes"], on_done)
 
      ov.set_read_only(False)
      edt = ov.begin_edit()
      ov.insert(edt, 0, prelude + prev + new_cntnt)
      ov.end_edit(edt)
      ov.set_read_only(True)

  def on_done(self, procedure_id, msg_id, output, answer):
    if answer == 0:
      self.view.run_command("ensime_accept_imports", { "procedure_id": procedure_id, "msg_id": msg_id })
      self.close_output_view(output)
    else:
      ensime_environment.ensime_env.client().remove_handler(msg_id)
      self.close_output_view(output)

  def close_output_view(self, output):
    # ov = self.views[output]
    ov = output
    ensime_environment.ensime_env.client().window.focus_view(ov)
    ensime_environment.ensime_env.client().window.run_command("close")

  def run(self, edit):
    #ensure_ensime_environment.ensime_env()
    fname = self.view.file_name()
    if fname:
      ensime_environment.ensime_env.client().organize_imports(fname, lambda data: self.handle_reply(edit, data))

class EnsimeAcceptImportsCommand(sublime_plugin.TextCommand, EnsimeOnly): 

  def handle_reply(self, edit, data):
    self.view.run_command("revert")
    ensime_environment.ensime_env.client().remove_handler(data[-1])

  def run(self, edit, procedure_id, msg_id):
    ensime_environment.ensime_env.client().perform_organize(
      procedure_id, msg_id, lambda data: self.handle_reply(edit, data))

########NEW FILE########
__FILENAME__ = ensime_completions
import os, sys, stat, random, getpass
import ensime_environment
from ensime_server import EnsimeOnly
import functools, socket, threading
import sublime_plugin, sublime
import sexp
from sexp import key,sym

class EnsimeCompletion:

  def __init__(self, name, signature, type_id, is_callable = False, to_insert = None):
    self.name = name
    self.signature = signature
    self.is_callable = is_callable
    self.type_id = type_id
    self.to_insert = to_insert

def ensime_completion(p):
    return EnsimeCompletion(
      p[":name"], 
      p[":type-sig"], 
      p[":type-id"], 
      bool(p[":is-callable"]) if ":is-callable" in p else False,
      p[":to-insert"] if ":to-insert" in p else None)


class EnsimeCompletionsListener(sublime_plugin.EventListener): 
 
  def on_query_completions(self, view, prefix, locations):
    if not view.match_selector(locations[0], "source.scala") and not view.match_selector(locations[0], "source.java"):
      return []
    env = ensime_environment.ensime_env
    if not env.use_auto_complete:
      return []
    data = env.client().complete_member(view.file_name(), locations[0])
    if data is None: 
      return [] 
    friend = sexp.sexp_to_key_map(data[1][1])
    comps = friend[":completions"] if ":completions" in friend else []
    comp_list = [ensime_completion(sexp.sexp_to_key_map(p)) for p in friend[":completions"]]
    
    return ([(p.name + "\t" + p.signature, p.name) for p in comp_list], sublime.INHIBIT_EXPLICIT_COMPLETIONS | sublime.INHIBIT_WORD_COMPLETIONS)
  

########NEW FILE########
__FILENAME__ = ensime_environment
import threading 
import sublime

class EnsimeEnvironment:

  def __init__(self):
    self.settings = sublime.load_settings("Ensime.sublime-settings")
    self._clientLock = threading.RLock()
    self._client = None

  def set_client(self, client):
    self._clientLock.acquire()
    try:
      self._client = client
      return self._client
    finally:
      self._clientLock.release()

  def client(self):
    return self._client


ensime_env = EnsimeEnvironment()


########NEW FILE########
__FILENAME__ = ensime_notes
import os, sys, stat, functools
import sublime, sublime_plugin
from ensime_server import EnsimeOnly
import ensime_environment
import sexp

ensime_env = ensime_environment.ensime_env

class LangNote:

  def __init__(self, lang, msg, fname, severity, start, end, line, col):
    self.lang = lang
    self.message = msg
    self.file_name = fname
    self.severity = severity
    self.start = start
    self.end = end
    self.line = line
    self.col = col

def lang_note(lang, m):
  return LangNote(
    lang, 
    m[":msg"],
    m[":file"],
    m[":severity"],
    m[":beg"],
    m[":end"],
    m[":line"],
    m[":col"])

def erase_error_highlights(view):
  view.erase_regions("ensime-error")
  view.erase_regions("ensime-error-underline")
  
def highlight_errors(view, notes):
  if notes is None:
    print "There were no notes?"
    return
  print "higlighting errors"
  errors = [view.full_line(note.start) for note in notes]
  underlines = []
  for note in notes:
    underlines += [sublime.Region(int(pos)) for pos in range(note.start, note.end)]
  view.add_regions(
    "ensime-error-underline",
    underlines,
    "invalid.illegal",
    sublime.DRAW_EMPTY_AS_OVERWRITE)
  view.add_regions(
    "ensime-error", 
    errors, 
    "invalid.illegal", 
    "cross",
    sublime.DRAW_OUTLINED)

view_notes = {}

class EnsimeNotes(sublime_plugin.TextCommand, EnsimeOnly):

  def run(self, edit, action = "add", lang = "scala", value=None):

    if not hasattr(self, "notes"):
      self.notes = []

    if action == "add":
      new_notes = [lang_note(lang, m) for m in value]
      self.notes.extend(new_notes)
      highlight_errors(self.view, self.notes)

    elif action == "clear":
      self.notes = []
      erase_error_highlights(self.view)

    elif action == "display":
      nn = self.notes
      vw = self.view
      vpos = vw.line(vw.sel()[0].begin()).begin()
      if len(nn) > 0 and len([a for a in nn if self.view.line(int(a.start)).begin() == vpos]) > 0:
        msgs = [note.message for note in self.notes]
        self.view.set_status("ensime-typer", "; ".join(set(msgs)))
      else:
        self.view.erase_status("ensime-typer")
        #sublime.set_timeout(functools.partial(self.view.run_command, "ensime_inspect_type_at_point", self.view.id()), 200)

def run_check(view):
    view.checked = True
    view.run_command("ensime_type_check_file")

class BackgroundTypeChecker(sublime_plugin.EventListener):


  def _is_valid_file(self, view):
    return bool(not view.file_name() is None and view.file_name().endswith(("scala","java")))

  def on_load(self, view):
    if self._is_valid_file(view):
      run_check(view)

  def on_post_save(self, view):
    if self._is_valid_file(view):
      run_check(view)

  def on_selection_modified(self, view):
    if self._is_valid_file(view):
      view.run_command("ensime_notes", { "action": "display" })



class EnsimeInspectTypeAtPoint(sublime_plugin.TextCommand, EnsimeOnly):

  def handle_reply(self, data):
    d = data[1][1]
    if d[1] != "<notype>":
      self.view.set_status("ensime-typer", "(" + str(d[7]) + ") " + d[5])
    else:
      self.view.erase_status("ensime-typer")

  def run(self, edit):
    if self.view.file_name():
      cl = ensime_environment.ensime_env.client()
      if not cl is None:
        cl.inspect_type_at_point(self.view.file_name(), self.view.sel()[0].begin(), self.handle_reply)




########NEW FILE########
__FILENAME__ = ensime_server
import os, sys, stat, time, datetime, re, random
from ensime_client import *
import ensime_environment
import functools, socket, threading
import sublime_plugin, sublime
import thread
import logging
import subprocess
import sexp
from sexp import key,sym

class ProcessListener(object):
  def on_data(self, proc, data):
    pass

  def on_finished(self, proc):
    pass

class AsyncProcess(object):
  def __init__(self, arg_list, listener, cwd = None):

    # ensure the subprocess is always killed when the editor exits
    # import atexit
    # atexit.register(self.kill)

    self.listener = listener
    self.killed = False

    # Hide the console window on Windows
    startupinfo = None
    if os.name == "nt":
      startupinfo = subprocess.STARTUPINFO()
      startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    proc_env = os.environ.copy()

    self.proc = subprocess.Popen(arg_list, stdout=subprocess.PIPE,
      stderr=subprocess.PIPE, startupinfo=startupinfo, env=proc_env, cwd = cwd)

    if self.proc.stdout:
      thread.start_new_thread(self.read_stdout, ())

    if self.proc.stderr:
      thread.start_new_thread(self.read_stderr, ())

  def kill(self):
    if not self.killed:
      self.killed = True
      self.proc.kill()
      self.listener = None

  def poll(self):
    return self.proc.poll() == None

  def read_stdout(self):
    while True:
      data = os.read(self.proc.stdout.fileno(), 2**15)

      if data != "":
        if self.listener:
          self.listener.on_data(self, data)
      else:
        self.proc.stdout.close()
        if self.listener:
          self.listener.on_finished(self)
        break

  def read_stderr(self):
    while True:
      data = os.read(self.proc.stderr.fileno(), 2**15)

      if data != "":
        if self.listener:
          self.listener.on_data(self, data)
      else:
        self.proc.stderr.close()
        break

# if this doesn't work well enough as it's a bit hacky use the chardet egg to drive this home.
guess_list = ["us-ascii", "utf-8", "utf-16", "utf-7", "iso-8859-1", "iso-8859-2", "windows-1250", "windows-1252"]
def decode_string(data):
  for best_enc in guess_list:
    try:
      unicode(data, best_enc, "strict")
    except:
      pass
    else:
      break
  return unicode(data, best_enc)

class ScalaOnly:
  def is_enabled(self):
    return (bool(self.window and self.window.active_view().file_name() != "" and
    self._is_scala(self.window.active_view().file_name())))

  def _is_scala(self, file_name):
    _, fname = os.path.split(file_name)
    return fname.lower().endswith(".scala")

class EnsimeOnly:
  def ensime_project_file(self):
    prj_files = [(f + "/.ensime") for f in self.window.folders() if os.path.exists(f + "/.ensime")]
    if len(prj_files) > 0:
      return prj_files[0]
    else:
      #sublime.error_message("There are no open folders. Please open a folder containing a .ensime file.")
      return None

  def is_enabled(self, kill = False):
    return bool(ensime_environment.ensime_env.client()) and ensime_environment.ensime_env.client.ready() and bool(self.ensime_project_file())

class EnsimeServerCommand(sublime_plugin.WindowCommand, 
                          ProcessListener, ScalaOnly, EnsimeOnly):

  def ensime_project_root(self):
    prj_dirs = [f for f in self.window.folders() if os.path.exists(f + "/.ensime")]
    if len(prj_dirs) > 0:
      return prj_dirs[0]
    else:
      return None

  def is_started(self):
    return hasattr(self, 'proc') and self.proc and self.proc.poll()

  def is_enabled(self, **kwargs):
    start, kill, show_output = (kwargs.get("start", False), 
                                kwargs.get("kill", False), 
                                kwargs.get("show_output", False))
    return (((kill or show_output) and self.is_started()) or 
            (start and bool(self.ensime_project_file())))
                
  def show_output_window(self, show_output = False):
    if show_output:
      self.window.run_command("show_panel", {"panel": "output.ensime_server"})

  def ensime_command(self): 
    if os.name == 'nt':
      return "bin\\server.bat"
    else: 
      return "bin/server"

  def default_ensime_install_path(self):
    if os.name == 'nt':
      return "Ensime\\server"
    else: 
      return "Ensime/server"    


  def run(self, encoding = "utf-8", env = {}, 
          start = False, quiet = True, kill = False, 
          show_output = True):
    print "Running: " + self.__class__.__name__
    self.show_output = show_output
    if not hasattr(self, 'settings'):
      self.settings = sublime.load_settings("Ensime.sublime-settings")

    server_dir = self.settings.get("ensime_server_path", self.default_ensime_install_path())
    server_path = server_dir if server_dir.startswith("/") else os.path.join(sublime.packages_path(), server_dir)

    if kill:
      ensime_environment.ensime_env.client().sync_req([sym("swank:shutdown-server")])
      ensime_environment.ensime_env.client().disconnect()
      if self.proc:
        self.proc.kill()
        self.proc = None
        self.append_data(None, "[Cancelled]")
      return
    else:
      if self.is_started():
        self.show_output_window(show_output)
        if start and not self.quiet:
          print "Ensime server is already running!"
        return

    if not hasattr(self, 'output_view'):
      self.output_view = self.window.get_output_panel("ensime_server")

    self.quiet = quiet

    self.proc = None
    if not self.quiet:
      print "Starting Ensime Server."

    if show_output:
      self.show_output_window(show_output)

    # Change to the working dir, rather than spawning the process with it,
    # so that emitted working dir relative path names make sense
    if self.ensime_project_root() and self.ensime_project_root() != "":
      os.chdir(self.ensime_project_root())

    err_type = OSError
    if os.name == "nt":
      err_type = WindowsError

    try:
      self.show_output = show_output
      if start:
        cl = EnsimeClient(
          ensime_environment.ensime_env.settings, 
          self.window, self.ensime_project_root())
        sublime.set_timeout(
          functools.partial(ensime_environment.ensime_env.set_client, cl), 0)
        vw = self.window.active_view()
        self.proc = AsyncProcess([server_path + '/' + self.ensime_command(),
				  self.ensime_project_root() + "/.ensime_port"],
				  self,
				  server_path)
    except err_type as e:
      print str(e)
      self.append_data(None, str(e) + '\n')

  def perform_handshake(self):
    self.window.run_command("ensime_handshake")


  def append_data(self, proc, data):
    if proc != self.proc:
      # a second call to exec has been made before the first one
      # finished, ignore it instead of intermingling the output.
      if proc:
        proc.kill()
      return

    str_data = str(data).replace("\r\n", "\n").replace("\r", "\n")

    if not ensime_environment.ensime_env.client().ready() and re.search("Wrote port", str_data):
      ensime_environment.ensime_env.client().set_ready()
      self.perform_handshake()

    selection_was_at_end = (len(self.output_view.sel()) == 1
      and self.output_view.sel()[0]
        == sublime.Region(self.output_view.size()))
    self.output_view.set_read_only(False)
    edit = self.output_view.begin_edit()
    self.output_view.insert(edit, self.output_view.size(), str_data)
    if selection_was_at_end:
      self.output_view.show(self.output_view.size())
    self.output_view.end_edit(edit)
    self.output_view.set_read_only(True)

  def finish(self, proc):
    if proc != self.proc:
      return

    # Set the selection to the start, so that next_result will work as expected
    edit = self.output_view.begin_edit()
    self.output_view.sel().clear()
    self.output_view.sel().add(sublime.Region(0))
    self.output_view.end_edit(edit)

  def on_data(self, proc, data):
    sublime.set_timeout(functools.partial(self.append_data, proc, data), 0)

  def on_finished(self, proc):
    sublime.set_timeout(functools.partial(self.finish, proc), 0)


class EnsimeUpdateMessagesView(sublime_plugin.WindowCommand, EnsimeOnly):
  def run(self, msg):
    if msg != None:
      ov = ensime_environment.ensime_env.client().output_view
      msg = msg.replace("\r\n", "\n").replace("\r", "\n")

      selection_was_at_end = (len(ov.sel()) == 1
        and ov.sel()[0]
            == sublime.Region(ov.size()))
      ov.set_read_only(False)
      edit = ov.begin_edit()
      ov.insert(edit, ov.size(), str(msg) + "\n")
      if selection_was_at_end:
          ov.show(ov.size())
      ov.end_edit(edit)
      ov.set_read_only(True)

class CreateEnsimeClientCommand(sublime_plugin.WindowCommand, EnsimeOnly):

  def run(self):
    cl = EnsimeClient(self.window, u"/Users/ivan/projects/scapulet")
    cl.set_ready()
    self.window.run_command("ensime_handshake")

class EnsimeShowMessageViewCommand(sublime_plugin.WindowCommand, EnsimeOnly):

  def run(self):
    self.window.run_command("show_panel", {"panel": "output.ensime_messages"})

class EnsimeHandshakeCommand(sublime_plugin.WindowCommand, EnsimeOnly):

  def handle_init_reply(self, init_info):
    sublime.status_message("Ensime ready!")

  def handle_reply(self, server_info):
    if server_info[1][0] == key(":ok"):
      sublime.status_message("Initializing... ")
      ensime_environment.ensime_env.client().initialize_project(self.handle_init_reply)
    else:
      sublime.error_message("There was problem initializing ensime, msgno: " + 
                            str(server_info[2]) + ".")

  def run(self):
    if (ensime_environment.ensime_env.client().ready()):
      ensime_environment.ensime_env.client().handshake(self.handle_reply)


########NEW FILE########
__FILENAME__ = sexp
import re

class Keyword:
  def __init__(self, s):
    self.val = s
  def __repr__(self):
    return self.val
  def __eq__(self, k):
    return type(k) == type(self) and self.val == k.val

class Symbol:
  def __init__(self, s):
    self.val = s
  def __repr__(self):
    return self.val
  def __eq__(self, k):
    return type(k) == type(self) and self.val == k.val

def sexp_to_key_map(sexp):
    key_type = type(key(":key"))
    result = {}
    for i in xrange(0, len(sexp), 2):
        k,val = sexp[i],sexp[i+1]
        if type(k) == key_type:
            result[str(k)] = val
    return result

def key(s):
  return Keyword(s)

def sym(s):
  return Symbol(s)

def read(s):
  "Read a Scheme expression from a string."
  return read_form(s)[0]

def read_form(str):
  "Read a form."
  if len(str) == 0:
    raise SyntaxError('unexpected EOF while reading form')
  ch = str[0]
  if ch.isspace():
    raise SyntaxError('unexpected whitespace while reading form')
  elif ch == '(':
    return read_list(str)
  elif ch == '"':
    return read_string(str)
  elif ch == ':':
    return read_keyword(str)
  elif ch.isdigit() or ch == "-":
    return read_int(str)
  elif ch.isalpha():
    return read_symbol(str)
  else:
    raise SyntaxError('unexpected character in read_form: ' + ch)

def read_list(str):
  "Read a list from a string."
  if len(str) == 0:
    raise SyntaxError('unexpected EOF while reading list')
  if str[0] != '(':
    raise SyntaxError('expected ( as first char of list')      
  str = str[1:]
  lst = []
  while(len(str) > 0):
    ch = str[0]
    if ch.isspace():
      str = str[1:]
      continue
    elif ch == ')':
      return (lst,str[1:])
    else:
      val,remain = read_form(str)
      lst.append(val)
      str = remain
  raise SyntaxError('EOF while reading list')

def read_string(str):
  "Read a string."
  if len(str) == 0:
    raise SyntaxError('unexpected EOF while reading string')
  if str[0] != '"':
    raise SyntaxError('expected ( as first char of string')      
  str = str[1:]
  s = ""
  escaped = False
  while(len(str) > 0):
    ch = str[0]
    if ch == '"' and not escaped:
      return (s.replace("\\\\", "\\"),str[1:])
    elif escaped:
      escaped = False
    elif ch == "\\":
      escaped = True
    s = s + ch
    str = str[1:]
  raise SyntaxError('EOF while reading string')


def read_keyword(str):
  "Read a keyword."
  if len(str) == 0:
    raise SyntaxError('unexpected EOF while reading keyword')
  if str[0] != ':':
    raise SyntaxError('expected : as first char of keyword')      
  str = str[1:]
  s = ""
  while(len(str) > 0):
    ch = str[0]
    if not (ch.isalpha() or ch.isdigit() or ch == '-'):
      return (Keyword(":" + s),str)
    else:
      s = s + ch
      str = str[1:]

  if len(s) > 1:
    return (Keyword(":" + s),str)
  else:
    raise SyntaxError('EOF while reading keyword')


def read_symbol(str):
  "Read a symbol."
  if len(str) == 0:
    raise SyntaxError('unexpected EOF while reading symbol')
  if not str[0].isalpha():
    raise SyntaxError('expected alpha char as first char of symbol')
  s = ""
  while(len(str) > 0):
    ch = str[0]
    if not (ch.isalpha() or ch.isdigit() or ch == '-' or ch == ":"):
      if s == "t":
        return (True,str)
      elif s == "nil":
        return (False,str)
      else:
        return (Symbol(s),str)
    else:
      s = s + ch
      str = str[1:]

  if len(s) > 0:
    return (Symbol(s),str)
  else:
    raise SyntaxError('EOF while reading symbol')


def read_int(str):
  "Read an integer."
  if len(str) == 0:
    raise SyntaxError('unexpected EOF while reading int')
  s = ""
  while(len(str) > 0):
    ch = str[0]
    if not (ch.isdigit() or ch == '-'):
      return (int(s),str)
    else:
      s = s + ch
      str = str[1:]

  if len(s) > 0:
    return (int(s),str)
  else:
    raise SyntaxError('EOF while reading int')


def to_string(exp):
  "Convert a Python object back into a Lisp-readable string."
  return '('+' '.join(map(to_string, exp))+')' if type(exp) == type([]) else atom_to_str(exp)

def atom_to_str(exp):
  if exp and (type(exp) == type(True)):
    return "t"
  elif (not exp) and (type(exp) == type(False)):
    return "nil"
  elif type(exp) == type("") or type(exp) == type(u""):
    return "\"" + exp.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
  else:
    return str(exp)

def repl(prompt='lis.py> '):
  "A prompt-read-eval-print loop."
  while True:
    val = eval(parse(raw_input(prompt)))
    if val is not None: print to_string(val)


if __name__ == "__main__":
  print(str(read("nil")))
  print(str(read("(\"a b c\")")))
  print(str(read("(a b c)")))
  print(str(read("(:notes (:notes ((:file \"/Users/aemon/projects/cutey_ape/googleclient/experimental/qt_ape/src/apeoutlinemodel.cpp\" :line 37 :col 100 :beg nil :end nil :severity error :msg \"expected ')'\"))))")))
  print(str(read("-4342323")))
  print(str(read(":dude")))
  print(str(read("ape")))
  print(str(read("((((((nil))))))")))
  print(str(read("\"hello \\face\"")))
  print(str(read("\"hello \\fa\\\"ce\"")))
  print(str(read("(:swank-rpc (swank:connection-info) 1)")))

########NEW FILE########
__FILENAME__ = sexpr_parser
# $ProjectHeader: sexprmodule 0.2.1 Wed, 05 Apr 2000 23:33:53 -0600 nas $
# originally from: http://arctrix.com/nas/python/ 
# modified to understand \-escaped quotes instead of "" escaping  - pj 20060809
# IPC: taken from http://code.google.com/p/mhi/source/browse/sexpr.py  11 Jul 2011
import string
import StringIO
from StringIO import StringIO
# tokens
[T_EOF, T_ERROR, T_SYMBOL, T_STRING, 
 T_INTEGER, T_FLOAT, T_OPEN, T_CLOSE] = range(8)
# states
[S_START, S_SYMBOL, S_STRING, S_NUMBER] = range(4)

SexprError = 'SexprError'

def parse(expr): 
  return SexprParser(StringIO(expr)).parse()

class SexprParser:
  def __init__(self, input):
    self.line_no = 1
    self.input = input
    self.char = None

  def getc(self):
    if self.char is None:
      c = self.input.read(1)
      if c == '\n':
        self.line_no = self.line_no + 1
      return c
    else:
      t = self.char
      self.char = None
      return t

  def ungetc(self, c):
    self.char = c
    
  def convert_number(self, token):
    try:
      i = string.atoi(token)
      return (T_INTEGER, i)
    except ValueError:
      try:
        f = string.atof(token)
        return (T_FLOAT, f)
      except ValueError:
        return (T_ERROR, '%d: invalid number "%s"' % (self.line_no, token))

  def get_token(self):
    token = []
    state = S_START
    while 1:
      c = self.getc()
      if state == S_START:
        # EOF
        if not c:
          return (T_EOF, None)
        # whitespace
        elif c in ' \t\n':
          continue
        # comments
        elif c == ';':
          while c and (c != '\n'):
            c = self.getc()
        elif c == '(':
          return (T_OPEN, None)
        elif c == ')':
          return (T_CLOSE, None)
        elif c == '"':
          state = S_STRING
        elif c in '-0123456789.':
          state = S_NUMBER
          token.append(c)
        else:
          state = S_SYMBOL
          token.append(c)
      elif state == S_SYMBOL:
        if not c:
          return (T_SYMBOL, string.join(token, ''))
        if c in ' \t\n;()':
          self.ungetc(c)
          return (T_SYMBOL, string.join(token, ''))
        else:
          token.append(c)
      elif state == S_STRING:
        if not c:
          return (T_ERROR, '%d: unexpected EOF inside string' % self.line_no)
        elif c == '\\':
          c = self.getc()
          if c == '"':
            token.append('"')
          else:
            self.ungetc(c)
            token.append('\\')
        elif c == '"':
          return (T_STRING, string.join(token, ''))
        else:
          token.append(c)
      elif state == S_NUMBER:
        if not c:
          return self.convert_number(string.join(token, ''))
        if c in ' \t\n;()':
          self.ungetc(c)
          return self.convert_number(string.join(token, ''))
        elif c in '0123456789.eE-':
          token.append(c)
        else:
          return (T_ERROR, '%d: invalid character "%s" while reading integer' 
                    % (self.line_no, c))

  def parse(self, t=None):
    if not t:
      (t, v) = self.get_token()
    if t == T_OPEN:
      l = []
      while 1:
        (t, v) = self.get_token()
        if t == T_CLOSE:
          return l
        elif t == T_OPEN:
          v = self.parse(t)
          if v == None:
            raise SexprError, '%d: unexpected EOF' % self.line_no
        elif t == T_ERROR:
          raise SexprError, v
        elif t == T_EOF:
          raise SexprError, '%d: EOF while inside list' % self.line_no
        l.append(v)
    elif t == T_CLOSE:
      raise SexprError, '%d: unexpected )' % self.line_no
    elif t == T_EOF:
      return None
    elif t == T_ERROR:
      raise SexprError, v
    else:
      return v

if __name__ == '__main__':
  import sys
  #import profile
  p = SexprParser(sys.stdin)
  #profile.run('p.parse()')
  while 1:
    e = p.parse()
    print e
    if not e:
      break

########NEW FILE########
