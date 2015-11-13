__FILENAME__ = Envim
# Envim.py
#
# Copyright 2012 Jeanluc Chasseriau <jeanluc@lo.cx>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TODO:
# - update QuickFixList only when received FullTypecheck done
# - test if Analyzer is ready before use TypecheckFile / TypecheckAll

import logging
from EnvimTools import *
from EnvimOutputs import *
from VimHelpers import *
from Helper import *

from SwankProtocol import *

from Responses import *
from Events import *

log = logging.getLogger('envim')

@SimpleSingleton
class Envim:

  @CatchAndLogException
  def __init__(self):
    self.pauseAfter = 0
    self.currentCompletions = self.beginCompletions

  def setPauseAfter(self, pauseAfter):
    self.pauseAfter = pauseAfter

  @CatchAndLogException
  def sendToEnsimeClient(self, data):
    if self.pauseAfter <= 0:
      vim.eval("g:envim.ensimeClientCtx.write('"+data+"')")
    else:
      vim.eval("g:envim.ensimeClientCtx.writeAndPause('"+data+"', %d)" % (self.pauseAfter))
      self.pauseAfter = 0

  @CatchAndLogException
  def connectionAndProjectInit(self):
    SwankRpc().connectionInfo()(ConnectionInfoHandler())

  @CatchAndLogException
  def shutdownServer(self):
    echo("Shuting down Ensime server")
    SwankRpc().shutdownServer()(ShutdownServerHandler())
    State().initialized = False

  @CatchAndLogException
  def typecheckFile(self):
    if not checkCompilerReady(): return

    vim.command("update")

    # @todo: ensure that file is in source-roots
    filename = getCurrentFilename()
    if filename == None:
      echoe("Unknown current filename")
    else:
      SwankRpc().typecheckFile(filename)(TypecheckFileHandler())

  @CatchAndLogException
  def typecheckAll(self):
    if not checkCompilerReady(): return

    vim.command("update")

    SwankRpc().typecheckAll()(TypecheckAllHandler())

  @CatchAndLogException
  def symbolAtPoint(self):
    if not checkCompilerReady(): return

    filename = getCurrentFilename()
    if filename == None:
      echoe("Unknown current filename")
    else:
      #saveFile()
      offset = getCurrentOffset()
      SwankRpc().symbolAtPoint(filename, offset)(SymbolAtPointHandler())

  @CatchAndLogException
  def usesOfSymbolAtPoint(self):
    if not checkCompilerReady(): return

    filename = getCurrentFilename()
    if filename == None:
      echoe("Unknown current filename")
    else:
      offset = getCurrentOffset()
      SwankRpc().usesOfSymbolAtPoint(filename, offset)(UsesOfSymbolAtPointHandler())

  @CatchAndLogException
  def formatSource(self):
    if not checkCompilerReady(): return

    # @todo: ensure that file is in source-roots
    filename = getCurrentFilename()
    if filename == None:
      echoe("Unknown current filename")
    else:
      vim.command("update")
      SwankRpc().formatSource([filename])(FormatSourceHandler())
      echo("Please wait while formating...")

  @CatchAndLogException
  def onCursorMoved(self):
    PreviewOutput().close()

  @CatchAndLogException
  def onWinLeave(self):
    pass

  @CatchAndLogException
  def onTabLeave(self):
    PreviewOutput().close()

  @CatchAndLogException
  def completions(self, findstart, base):
    log.debug("Envim.completions: findstart: %d %s base: %s", findstart, str(findstart.__class__), base)

    self.currentCompletions(findstart, base)

  @CatchAndLogException
  def beginCompletions(self, findstart, base):
    log.debug("Envim.beginCompletions:")

    if findstart == 1:

      cmds = [
        "let pos = col('.') -1",
        "let line = getline('.')",
        "let bc = strpart(line,0,pos)",
        "let match_text = matchstr(bc, '\zs[^ \t#().[\]{}\''\";: ]*$')",
        "let completion_result = len(bc)-len(match_text)"
      ]

      vim.command("\n".join(cmds))

      OmniOutput().setStart(int(vim.eval("completion_result")))

    else:
      vim.command("update")

      filename = getCurrentFilename()
      if filename == None:
        echoe("Unknown current filename")
      else:
        offset = getCurrentOffset()

        self.setPauseAfter(1)
        SwankRpc().completions(filename, offset, 0, False)(CompletionsHandler())

      vim.command("let completion_result = []")

      OmniOutput().setBase(base)

      self.currentCompletions = self.showCompletions

    log.debug("Envim.beginCompletions: completion_result: %s", vim.eval("completion_result"))

  @CatchAndLogException
  def showCompletions(self, findstart, base):
    log.debug("Envim.showCompletions:")
    vim.command("let g:envim.showCompletions = 1")

    if findstart == 1:
      vim.command("let completion_result = %d" % (OmniOutput().getStart()))

    else:
      results = OmniOutput().getFormatedResults()
      vim.command("let completion_result = %s" % (results))

      self.currentCompletions = self.beginCompletions

    log.debug("Envim.showCompletions: completion_result: %s", vim.eval("completion_result"))


########NEW FILE########
__FILENAME__ = EnvimOutputs
# EnvimOutputs.py
#
# Copyright 2012 Jeanluc Chasseriau <jeanluc@lo.cx>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import types
import logging
from VimHelpers import *
from Helper import *

@SimpleSingleton
class ServerOutput(VimBufferHelper):

  def __init__(self):
    VimBufferHelper.__init__(self)
    self.bufferId = 0
    self.filename = "ENSIME_SERVER_OUTPUT"
    self.filters = [] # [ (regex, function, execOnce), ... ]
    self.prefix = "Ensime: "

  # Private

  def _updateBuffer(self, id, f):
    vim.command("call setbufvar(%d, '&modifiable', 1)" % (id))
    f()
    vim.command("call setbufvar(%d, '&modifiable', 0)" % (id))

  def _setDiscret(self):
    options = self.discretBufferOptions()
    self.setBufferOptions(self.bufferId, options)

  # Public

  @CatchAndLogException
  def setupBuffer(self):
    vim.command("badd %s" % (self.filename))
    self.bufferId = int(vim.eval("bufnr('%s')" % (self.filename)))

    log.debug("ServerOutput.setupBuffer: bufferId: %d", self.bufferId)

    options = self.hiddenBufferOptions()
    options.extend([
      ('modifiable', "1")
    ])

    extraCmds = [
      "sbuffer %d" % (self.bufferId),
      "autocmd * %s norm! G$" % (self.filename)
    ]
    
    self.setBufferOptions(self.bufferId, options, extraCmds)

  @CatchAndLogException
  def onServerOutput(self, data):
    def realOnServerOutput(data):
      doAppend = lambda: vim.buffers[self.bufferId-1].append(self.prefix + data)

      #self._updateBuffer(self.bufferId, doAppend)
      doAppend()

      for filter in self.filters:
        regex, fct, execOnce = filter
        if regex.match(data) != None:
          fct(data)
          if execOnce:
            self.filters.remove(filter)
  
    # set discret the first time
    # TODO: rework... discret is not set...
    self._setDiscret()
    self.onServerOutput = realOnServerOutput

    realOnServerOutput(data)

  @CatchAndLogException
  def addFilter(self, regex, fct, execOnce=True):
    self.filters.append( (re.compile(regex), fct, execOnce) )

  @CatchAndLogException
  def showServerOutput(self):
    vim.command("sbuffer %d" % (self.bufferId))
    vim.command("wincmd p")

@SimpleSingleton
class PreviewOutput(VimBufferHelper):
  def __init__(self):
    VimBufferHelper.__init__(self)
    self.bufferId = 0
    self.filename = "ENSIME_PREVIEW"
    self.isOpen = False

  # Private

  # Public

  @CatchAndLogException
  def clear(self):
    log.debug("PreviewOutput.clear: bufferId: %d", self.bufferId)
    id = self.bufferId - 1
    vim.buffers[id][:] = None

  @CatchAndLogException
  def setupBuffer(self):
    vim.command("badd %s" % (self.filename))
    self.bufferId = int(vim.eval("bufnr('%s')" % (self.filename)))

    log.debug("PreviewOutput.setupBuffer: bufferId: %d", self.bufferId)

    options = self.hiddenBufferOptions()
    options.extend([
      ('modifiable', "1")
    ])

    extraCmds = [
      "set previewheight=2",
    ]

    self.setBufferOptions(self.bufferId, options, extraCmds)

  @CatchAndLogException
  def set(self, lines=[]):
    def enc(s): return s.encode('ascii', 'replace')

    if isinstance(lines, types.StringType) or isinstance(lines, types.UnicodeType):
      lines = [enc(lines)]
    elif isinstance(lines, types.ListType):
      lines = [enc(l) for l in lines]
    else: log.error("PreviewOutput.set: lines is not of List neither String type")

    # note: show preview edit before updating it, and then redraw
    # this avoid vim to modify the source file header while setting the content
    # why? and how? haven't been solved yet
    cmds = [
      "pc",
      "pedit %s" % (self.filename),
    ]
    vim.command("\n".join(cmds))

    self.clear()

    id = self.bufferId - 1
    vim.buffers[id][:] = lines

    options = self.discretBufferOptions()
    options.extend([
      ('statusline', "'%='")
    ])

    cmds = [
      "redraw"
    ]

    self.setBufferOptions(self.bufferId, options, cmds)

    self.isOpen = True

  @CatchAndLogException
  def close(self):
    if self.isOpen:
      vim.command("pc")
      self.isOpen = False

@SimpleSingleton
class OmniOutput:
  def __init__(self):
    self.start = 0
    self.base = ''
    self.results = [] # list of dicts

  def setBase(self, base):
    self.base = base

  def getBase(self):
    return self.base

  def setStart(self, start):
    self.start = start

  def getStart(self):
    return self.start

  def setResults(self, results):
    self.results = results

  def getFormatedResults(self):
    s = listOfDictToString(self.results)
    self.results = []
    return s

  def showCompletions(self):
    vim.command("call feedkeys(\"\<c-x>\<c-o>\")")

  def pauseMessages(self):
    vim.command("call abeans#pauseMessages()")

  def continueMessages(self):
    vim.command("call abeans#continueMessages()")

@SimpleSingleton
class QuickFixOutput:
  def __init__(self):
    pass

  def open(self):
    cmds = ["copen", "setlocal nonu", "setlocal nocursorline", "redraw"]
    vimCommands(cmds)
    self.isOpen = True

  def close(self):
    cmds = ["cclose", "redraw"]
    vimCommands(cmds)
    self.isOpen = False

  def clear(self):
    self.set([])

  def set(self, qflist):
    o = listOfDictToString(qflist)

    cmds = [ 
      "call setqflist(%s)" % (o),
    ]
    vimCommands(cmds)


########NEW FILE########
__FILENAME__ = EnvimTools
# EnvimTools.py
#
# Copyright 2012 Jeanluc Chasseriau <jeanluc@lo.cx>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from VimHelpers import *
from Helper import *

log = logging.getLogger('envim')

@SimpleSingleton
class State(object):
  def __init__(self):
    self.initialized = False
    self.indexerReady = False
    self.compilerReady = False
    self.fullTypecheckFinished = False
    self.scalaNotes = []
    self.javaNotes = []

# TODO: Transform checkInitialized() and checkCompilerReady() in to decorator?
def checkInitialized():
  if not State().initialized:
    echoe("Project is not initialized. Ensure you have a .ensime project file and start using `:Envim`.")
    return False
  return True

def checkCompilerReady():
  if not checkInitialized(): return False
  if not State().compilerReady:
    echoe("Compiler is not ready yet.")
    return False
  return True


########NEW FILE########
__FILENAME__ = Events
# Events.py
#
# Copyright 2012 Jeanluc Chasseriau <jeanluc@lo.cx>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from EnvimTools import *
from EnvimOutputs import *
from VimHelpers import *

log = logging.getLogger('envim')

@SwankEventBackgroundMessage
def backgroundMessage(code, details):
  s = codeDetailsString(code, details)
  log.info('Background message: '+s)
  echo(s)

@SwankEventReaderError
def readerError(code, details):
  s = codeDetailsString(code, details)
  log.error('Reader error: '+s)
  echo(s)

@SwankEventCompilerReady
def compilerReady():
  State().compilerReady = True
  echo("Compiler ready")

@SwankEventIndexerReady
def indexerReady():
  State().indexerReady = True
  echo("Indexer ready")

@SwankEventFullTypecheckFinished
def fullTypecheckFinished():
  echo("Full typecheck finished")

  qflist = notesToQuickFixList(State().scalaNotes)
  QuickFixOutput().set(qflist)
  QuickFixOutput().open()

@SwankEventScalaNotes
def scalaNotes(notes):
  # notes.is_full True|False
  # notes.notes = []

  if notes.is_full:
    log.debug("scalaNotes: Full scala notes list, clear previous list")
  else:
    log.debug("scalaNotes: Partial scala notes list")

    # here we prepend existing notes
    notes.notes.reverse()
    State().scalaNotes.reverse()
    notes.notes.extend(State().scalaNotes)
    notes.notes.reverse()

  State().scalaNotes = notes.notes

  echo("Typechecking in progress...")

@SwankEventClearAllScalaNotes
def clearAllScalaNotes():
  log.debug("clearAllScalaNotes: Clear all Scala notes")

  QuickFixOutput().clear()

  State().scalaNotes = []

@SwankEventJavaNotes
def javaNotes():
  log.debug("javaNotes: TODO: Implement Java notes")
  echoe("Java notes: TODO to implement")

@SwankEventClearAllJavaNotes
def clearAllJavaNotes():
  log.debug("clearAllJavaNotes: TODO: Implement clear Java notes")



########NEW FILE########
__FILENAME__ = Responses
# Responses.py
#
# Copyright 2012 Jeanluc Chasseriau <jeanluc@lo.cx>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from EnvimOutputs import *
from EnvimTools import *
from VimHelpers import *
from Helper import SimpleSingleton

log = logging.getLogger('envim')

# TODO: printing error using echoe()) in Handlers raise an error in abeans#processInput() without displaying the error

@SimpleSingleton
class ConnectionInfoHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("ConnectionInfo abort: "+codeDetailsString(code, details))

  def response(self, r):
    spid = ""
    if (r.pid): spid = str(r.pid)

    echo("server: "+r.implementation.name+" ("+r.version+") "+spid)

    configFile = getEnsimeConfigFile()
    if configFile == None:
      return

    config = ensimeConfigToPython(configFile)
    if config == None:
      return

    SwankRpc().projectInit(config)(InitProjectHandler())

@SimpleSingleton
class InitProjectHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("InitProject abort: "+codeDetailsString(code, details))

  def response(self, r):
    echo("Initializing project: "+str(r.project_name))

    for src in r.source_roots:
      log.debug("project source roots: "+src)

    State().initialized = True

@SimpleSingleton
class ShutdownServerHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("ShutdownServer abort: "+codeDetailsString(code, details))

  def response(self, r):
    echo("Ensime server is now off")

@SimpleSingleton
class TypecheckFileHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("TypecheckFile abort: "+codeDetailsString(code, details))

  def response(self, r):
    if r: echo("Typechecking in progress...")
    else: echoe("Typecheck file error")

    State().scalaNotes = []

@SimpleSingleton
class TypecheckAllHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("TypecheckAll abort: "+codeDetailsString(code, details))

  def response(self, r):
    if r: echo("Typechecking in progress...")
    else: echoe("Typecheck all error")

    State().scalaNotes = []

@SimpleSingleton
class SymbolAtPointHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("SymbolAtPoint abort: "+codeDetailsString(code, details))

  def response(self, symbolInfo):
    if not symbolInfo:
      #echo("No symbol here")
      PreviewOutput().set(["No symbol here"])
      return

    # Example:
    # Result for a val:
    # (:return (:ok (:name "toto" :type (:name "String" :type-id 1 :full-name "java.lang.String" :decl-as class) :decl-pos (:file "/Users/jeanluc/Source/vim/test_vim_ensime/src/main/scala/HelloWorld.scala" :offset 64) :owner-type-id 2)) 47)

    # Result for a method:
    #(:return (:ok (:name "println" :type (:name "(x: Any)Unit" :type-id 2 :arrow-type t :result-type (:name "Unit" :type-id 3 :full-name "scala.Unit" :decl-as class) :param-sections ((:params (("x" (:name "Any" :type-id 1 :full-name "scala.Any" :decl-as class)))))) :is-callable t :owner-type-id 4)) 45)

    # Fields may be defined depending on the type we are accessing

    out = symbolInfo.name + ' : ' + symbolInfo.type.name

    decl_as = ''
    if hasattr(symbolInfo.type, 'decl_as'):
      decl_as = symbolInfo.type.decl_as

    full_name = ''
    if hasattr(symbolInfo.type, 'full_name'):
      full_name = symbolInfo.type.full_name

    if decl_as != '' or full_name != '':
      out += ' (' + decl_as + ' ' + full_name + ')'

    log.debug("SymbolAtPointHandler.response: %s", out)

    #echo(out)
    PreviewOutput().set([out])

@SimpleSingleton
class UsesOfSymbolAtPointHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("SymbolAtPoint abort: "+codeDetailsString(code, details))

  def response(self, rangePosList):
    if not rangePosList:
      echo("Symbol not used")
      qflist = []
    else:
      qflist = rangePosToQuickFixList(rangePosList)

    QuickFixOutput().set(qflist)
    QuickFixOutput().open()

@SimpleSingleton
class CompletionsHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("Completions abort: "+codeDetailsString(code, details))

  def response(self, completions):
    if not completions or not completions.has('completions'):
      echo("Empty completions")
      OmniOutput().continueMessages()
      return

    reBase = None
    if OmniOutput().getBase() != '':
      reBase = re.compile("^%s.*" % (OmniOutput().getBase()))

    isCallableToVim = {True: 'f', False: 'v'}

    log.debug("CompletionsHandler.response:")

    out = [{'word':completions.prefix}]
    for comp in completions.completions:
      if reBase != None and reBase.match(comp.name) == None: continue
      d = {}
      d['word'] = comp.name
      d['info'] = comp.type_sig
      if comp.has('is_callable'):
        d['kind'] = isCallableToVim[comp.is_callable]

      out.append(d)

    out = sorted(out, key=lambda d: d['word'])

    OmniOutput().setResults(out)

    OmniOutput().showCompletions()

@SimpleSingleton
class FormatSourceHandler(SwankCallHandler):

  def abort(self, code, details):
    echoe("FormatSource abort: "+codeDetailsString(code, details))

  def response(self, r):
    if not r:
      echoe("FormatSource file error")
      return

    cmds = [
      "call feedkeys('<cr>')",
      # @todo: we use feedkeys() in order to avoid loosing the syntax colors, simply 'e' should be enough (cf. #9)
      "call feedkeys(':e')"
    ]
    vimCommands(cmds)

    echo("FormatSource done")


########NEW FILE########
__FILENAME__ = test
import Helper

Logger().setOutput("exception.log")

@CatchAndLogException
def main():
    Logger().debug("Hello world!")

if __name__ == "__main__":
    u = 1/0
    main()

########NEW FILE########
__FILENAME__ = VimHelpers
# VimHelpers.py
#
# Copyright 2012 Jeanluc Chasseriau <jeanluc@lo.cx>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import mmap
import types
import vim
import logging
from SExpression import *
from SwankProtocol import *

log = logging.getLogger('envim')

class VimBufferHelper:
  def __init__(self):
    pass

  def hiddenBufferOptions(self):
    return [
      ('buftype', "'nofile'"),
      ('bufhidden', "'hide'"),
      ('swapfile', "0"),
      ('buflisted', "0"),
      ('lazyredraw', "0")
    ]

  def discretBufferOptions(self):
    return [
      ('cursorline', "0"),
      ('nu', "0")
    ]

  def setBufferOptions(self, id, options, extraCmds=[]):
    cmds = ["call setbufvar(%d, '&%s', %s)" % (id, opt, value) for opt, value in options]
    cmds.extend(extraCmds)
    c = "\n".join(cmds)
    #log.debug("VimBufferHelper.setBufferOptions: %s", c)
    vim.command(c)

#
# Vim Helpers functions
#

# execute a list of commands
def vimCommands(listCmds):
  vim.command("\n".join(listCmds))

# normal echo (in vim command line)
def echo(s):
  log.info(s)
  vim.command("echo('"+s+"')")

# error echo (highlighted in vim command line)
def echoe(s):
  log.error(s)
  vim.command("echoe('"+s+"')")

# debug echo (as provided by Decho addon: open a new window)
def decho(s):
  log.debug(s)
  vim.command("Decho('"+s+"')")

def getCurrentOffset():
  return int(vim.eval('line2byte(line("."))+col(".")'))-1

def getCurrentFilename():
  filename = vim.eval("expand('%')")
  if filename != None:
    # TODO: check if this is still correct after :lcd path
    filename = os.getcwd() + '/' + filename
  return filename

def getBeforeAndAfterCursor():
  col = int(vim.eval("col('.')"))
  line = vim.eval("line('.')")
  before = line[:col]
  after = line[col:]
  return (before, after)

def listOfDictToString(li):
  o = '['

  nlist = len(li)
  for de in li:
    nlist -= 1

    o += '{'
    ndict = len(de.keys())
    for k in de.keys():
      ndict -= 1

      o += "'"+k+"'" + ':'
      if isinstance(de[k], types.StringType) or isinstance(de[k], types.UnicodeType):
        # TODO: the value may be utf-8 which does not appear to be handled in vim's omnicompletion
        # check if there is a way and if we can avoid this 'replace'
        value = de[k].encode('ascii', 'replace')
        o += '"' + value.replace('"', '\\"') + '"'
      else:
        o += str(de[k])

      if ndict > 0: o += ','

    o += '}'
    if nlist > 0: o += ','

  o += ']'
  return o

def saveFile():
  vim.command("w")

def editAtOffset(filename, offset):
  vim.command("call feedkeys(':e fnameescape("+filename+") |goto "+offset+" |syn on")

#
# Misc tools
#

def codeDetailsString(code, detail):
  return ProtocolConst.toStr(code)+'('+str(code)+') : '+detail

def getEnsimeConfigFile():
  def lookAround(path):
    if path == '/':
      echoe("Ensime configuration file (.ensime) could not be found")
      return None
    configFile = path + '/' + '.ensime'
    if os.path.isfile(configFile): return configFile
    else: return lookAround(os.path.dirname(path))

  configFile = lookAround(os.getcwd())
  log.debug("getEnsimeConfigFile: .ensime configuration file: %s", configFile)

  return configFile

def ensimeConfigToPython(filename):
  try: f = file(filename)
  except:
    log.error("ensimeConfigToPython: unable to open ensime config file ("+filename+")")
    return None
 
  outlist = []

  lines = f.readlines()

  for line in lines:
    line = line.strip()
    
    if line.startswith(';;'): continue

    comment = line.find(';;')
    if comment > 0:
      line = line[:comment].strip()

    if not len(line): continue

    outlist.append(line)

  out = ' '.join(outlist)

  log.debug("ensimeConfigToPython: reading conf:")
  log.debug(out)

  try:
    sexp = SExpParser().parse(out)
    py = sexp.toPy()
  except:
    err = "Error while parsing .ensime configuration file"
    echo(err)
    log.exception(err)
    return None

  # TODO: this is ABSOLUTELY NOT CLEAN:
  # I am unable to make ensime works with .ensime as generated by sbt
  # If we remove the 'subprojects' from it, it works...
  # Why???
  try:
    if py.has('subprojects'):
      py = py.subprojects[0]
  except:
    log.exception("Detected .ensime as generated by sbt ensime generate. Unable to take out subprojects.")

  if not py.has('root_dir'):
    setattr(py, 'root_dir', os.getcwd())

  log.debug("ensimeConfigToPython: python object:")
  log.debug(py.debugString())

  return py

def notesToQuickFixList(notes):
  # quick fix list format:
  # list = [ { 'filename': xxx, 'lnum': xxx, 'col': xxx, 'text': xxx, 'type': E/W
  # Note: maybe we can highlight the file segment (thx to notes.beg and notes.end)

  vimseverity = {'error':'E', 'warn':'W', 'info':'I'}

  qflist = []
  nr = 1

  for note in notes:
    entry = {
      'filename': note.file,
      'lnum': note.line,
      'col': note.col,
      'vcol': 1,
      'text': note.msg,
      'type': vimseverity[note.severity],
      'nr': nr
    }
    qflist.append(entry)
    nr += 1

    debugs = '['+note.severity+'] '+os.path.basename(note.file)+' l.'+str(note.line)+' c.'+str(note.col)
    debugs += ' : '+note.msg

    log.debug(debugs)

  return qflist

# NOTE: this is quite ugly and inefficient: find how vim can help here
def offsetToLineCol(filename, offset):
  try:
    f = open(filename, 'r+')
    buf = mmap.mmap(f.fileno(), 0)
    f.close()
  except Exception as detail:
    log.error("offsetToLineCol: unable to open file ("+filename+") : "+str(detail))
    return None

  found = False
  lastPos = buf.tell()
  lineno = 1
  col = 0
  line = ""

  while not found:
    line = buf.readline()
    pos = buf.tell()

    if pos < offset:
      lineno += 1
      lastPos = pos
    else:
      col = offset - lastPos
      found = True

  buf.close()

  if found:
    return (line, lineno, col)

  log.debug("offsetToLineCol: line and column not found for "+filename+":"+str(offset))
  return None

def rangePosToQuickFixList(rangePosList):

  qflist = []
  nr = 1

  for pos in rangePosList:
    r = offsetToLineCol(pos.file, pos.offset)
    if r == None:
      continue
    
    (line, lineNo, colNo) = r

    entry = {
      'filename': pos.file,
      'lnum': lineNo,
      'col': colNo,
      'text': line,
      'vcol': 1,
      'type': 'I',
      'nr': nr
    }
    qflist.append(entry)
    nr += 1

  return qflist



########NEW FILE########
