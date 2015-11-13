__FILENAME__ = color
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

import pager
from git_config import GitConfig

COLORS = {None     :-1,
          'normal' :-1,
          'black'  : 0,
          'red'    : 1,
          'green'  : 2,
          'yellow' : 3,
          'blue'   : 4,
          'magenta': 5,
          'cyan'   : 6,
          'white'  : 7}

ATTRS = {None     :-1,
         'bold'   : 1,
         'dim'    : 2,
         'ul'     : 4,
         'blink'  : 5,
         'reverse': 7}

RESET = "\033[m"

def is_color(s): return s in COLORS
def is_attr(s):  return s in ATTRS

def _Color(fg = None, bg = None, attr = None):
    fg = COLORS[fg]
    bg = COLORS[bg]
    attr = ATTRS[attr]

    if attr >= 0 or fg >= 0 or bg >= 0:
      need_sep = False
      code = "\033["

      if attr >= 0:
        code += chr(ord('0') + attr)
        need_sep = True

      if fg >= 0:
        if need_sep:
          code += ';'
        need_sep = True

        if fg < 8:
          code += '3%c' % (ord('0') + fg)
        else:
          code += '38;5;%d' % fg

      if bg >= 0:
        if need_sep:
          code += ';'
        need_sep = True

        if bg < 8:
          code += '4%c' % (ord('0') + bg)
        else:
          code += '48;5;%d' % bg
      code += 'm'
    else:
      code = ''
    return code


class Coloring(object):
  def __init__(self, config, type):
    self._section = 'color.%s' % type
    self._config = config
    self._out = sys.stdout

    on = self._config.GetString(self._section)
    if on is None:
      on = self._config.GetString('color.ui')

    if on == 'auto':
      if pager.active or os.isatty(1):
        self._on = True
      else:
        self._on = False
    elif on in ('true', 'always'):
      self._on = True
    else:
      self._on = False

  def redirect(self, out):
    self._out = out

  @property
  def is_on(self):
    return self._on

  def write(self, fmt, *args):
    self._out.write(fmt % args)

  def flush(self):
    self._out.flush()

  def nl(self):
    self._out.write('\n')

  def printer(self, opt=None, fg=None, bg=None, attr=None):
    s = self
    c = self.colorer(opt, fg, bg, attr)
    def f(fmt, *args):
      s._out.write(c(fmt, *args))
    return f

  def colorer(self, opt=None, fg=None, bg=None, attr=None):
    if self._on:
      c = self._parse(opt, fg, bg, attr)
      def f(fmt, *args):
        str = fmt % args
        return ''.join([c, str, RESET])
      return f
    else:
      def f(fmt, *args):
        return fmt % args
      return f

  def _parse(self, opt, fg, bg, attr):
    if not opt:
      return _Color(fg, bg, attr)

    v = self._config.GetString('%s.%s' % (self._section, opt))
    if v is None:
      return _Color(fg, bg, attr)

    v = v.strip().lower()
    if v == "reset":
      return RESET
    elif v == '':
      return _Color(fg, bg, attr)

    have_fg = False
    for a in v.split(' '):
      if is_color(a):
        if have_fg: bg = a
        else:       fg = a
      elif is_attr(a):
        attr = a

    return _Color(fg, bg, attr)

########NEW FILE########
__FILENAME__ = command
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import optparse
import sys

import manifest_loader

from error import NoSuchProjectError

class Command(object):
  """Base class for any command line action in repo.
  """

  common = False
  _optparse = None

  def WantPager(self, opt):
    return False

  @property
  def OptionParser(self):
    if self._optparse is None:
      try:
        me = 'repo %s' % self.NAME
        usage = self.helpUsage.strip().replace('%prog', me)
      except AttributeError:
        usage = 'repo %s' % self.NAME
      self._optparse = optparse.OptionParser(usage = usage)
      self._Options(self._optparse)
    return self._optparse

  def _Options(self, p):
    """Initialize the option parser.
    """

  def Usage(self):
    """Display usage and terminate.
    """
    self.OptionParser.print_usage()
    sys.exit(1)

  def Execute(self, opt, args):
    """Perform the action, after option parsing is complete.
    """
    raise NotImplementedError
 
  @property
  def manifest(self):
    return self.GetManifest()

  def GetManifest(self, reparse=False, type=None):
    return manifest_loader.GetManifest(self.repodir,
                                       reparse=reparse,
                                       type=type)

  def GetProjects(self, args, missing_ok=False):
    """A list of projects that match the arguments.
    """
    all = self.manifest.projects

    mp = self.manifest.manifestProject
    if mp.relpath == '.':
      all = dict(all)
      all[mp.name] = mp

    result = []

    if not args:
      for project in all.values():
        if missing_ok or project.Exists:
          result.append(project)
    else:
      by_path = None

      for arg in args:
        project = all.get(arg)

        if not project:
          path = os.path.abspath(arg).replace('\\', '/')

          if not by_path:
            by_path = dict()
            for p in all.values():
              by_path[p.worktree] = p

          try:
            project = by_path[path]
          except KeyError:
            oldpath = None
            while path \
              and path != oldpath \
              and path != self.manifest.topdir:
              try:
                project = by_path[path]
                break
              except KeyError:
                oldpath = path
                path = os.path.dirname(path)

        if not project:
          raise NoSuchProjectError(arg)
        if not missing_ok and not project.Exists:
          raise NoSuchProjectError(arg)

        result.append(project)

    def _getpath(x):
      return x.relpath
    result.sort(key=_getpath)
    return result

class InteractiveCommand(Command):
  """Command which requires user interaction on the tty and
     must not run within a pager, even if the user asks to.
  """
  def WantPager(self, opt):
    return False

class PagedCommand(Command):
  """Command which defaults to output in a pager, as its
     display tends to be larger than one screen full.
  """
  def WantPager(self, opt):
    return True

class MirrorSafeCommand(object):
  """Command permits itself to run within a mirror,
     and does not require a working directory.
  """

########NEW FILE########
__FILENAME__ = editor
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import sys
import subprocess
import tempfile

from error import EditorError

class Editor(object):
  """Manages the user's preferred text editor."""

  _editor = None
  globalConfig = None

  @classmethod
  def _GetEditor(cls):
    if cls._editor is None:
      cls._editor = cls._SelectEditor()
    return cls._editor

  @classmethod
  def _SelectEditor(cls):
    e = os.getenv('GIT_EDITOR')
    if e:
      return e

    if cls.globalConfig:
      e = cls.globalConfig.GetString('core.editor')
      if e:
        return e

    e = os.getenv('VISUAL')
    if e:
      return e

    e = os.getenv('EDITOR')
    if e:
      return e

    if os.getenv('TERM') == 'dumb':
      print >>sys.stderr,\
"""No editor specified in GIT_EDITOR, core.editor, VISUAL or EDITOR.
Tried to fall back to vi but terminal is dumb.  Please configure at
least one of these before using this command."""
      sys.exit(1)

    return 'vi'

  @classmethod
  def EditString(cls, data):
    """Opens an editor to edit the given content.

       Args:
         data        : the text to edit
  
      Returns:
        new value of edited text; None if editing did not succeed
    """
    editor = cls._GetEditor()
    if editor == ':':
      return data

    fd, path = tempfile.mkstemp()
    try:
      os.write(fd, data)
      os.close(fd)
      fd = None

      if re.compile("^.*[$ \t'].*$").match(editor):
        args = [editor + ' "$@"', 'sh']
        shell = True
      else:
        args = [editor]
        shell = False
      args.append(path)

      try:
        rc = subprocess.Popen(args, shell=shell).wait()
      except OSError, e:
        raise EditorError('editor failed, %s: %s %s'
          % (str(e), editor, path))
      if rc != 0:
        raise EditorError('editor failed with exit status %d: %s %s'
          % (rc, editor, path))

      fd2 = open(path)
      try:
        return fd2.read()
      finally:
        fd2.close()
    finally:
      if fd:
        os.close(fd)
      os.remove(path)

########NEW FILE########
__FILENAME__ = error
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class ManifestParseError(Exception):
  """Failed to parse the manifest file.
  """

class ManifestInvalidRevisionError(Exception):
  """The revision value in a project is incorrect.
  """

class EditorError(Exception):
  """Unspecified error from the user's text editor.
  """
  def __init__(self, reason):
    self.reason = reason

  def __str__(self):
    return self.reason

class GitError(Exception):
  """Unspecified internal error from git.
  """
  def __init__(self, command):
    self.command = command

  def __str__(self):
    return self.command

class ImportError(Exception):
  """An import from a non-Git format cannot be performed.
  """
  def __init__(self, reason):
    self.reason = reason

  def __str__(self):
    return self.reason

class UploadError(Exception):
  """A bundle upload to Gerrit did not succeed.
  """
  def __init__(self, reason):
    self.reason = reason

  def __str__(self):
    return self.reason

class NoSuchProjectError(Exception):
  """A specified project does not exist in the work tree.
  """
  def __init__(self, name=None):
    self.name = name

  def __str__(self):
    if self.Name is None:
      return 'in current directory'
    return self.name

class RepoChangedException(Exception):
  """Thrown if 'repo sync' results in repo updating its internal
     repo or manifest repositories.  In this special case we must
     use exec to re-execute repo with the new code and manifest.
  """
  def __init__(self, extra_args=[]):
    self.extra_args = extra_args

########NEW FILE########
__FILENAME__ = git_command
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import subprocess
import tempfile
from signal import SIGTERM
from error import GitError
from trace import REPO_TRACE, IsTrace, Trace

GIT = 'git'
MIN_GIT_VERSION = (1, 5, 4)
GIT_DIR = 'GIT_DIR'

LAST_GITDIR = None
LAST_CWD = None

_ssh_proxy_path = None
_ssh_sock_path = None
_ssh_clients = []

def ssh_sock(create=True):
  global _ssh_sock_path
  if _ssh_sock_path is None:
    if not create:
      return None
    dir = '/tmp'
    if not os.path.exists(dir):
      dir = tempfile.gettempdir()
    _ssh_sock_path = os.path.join(
      tempfile.mkdtemp('', 'ssh-', dir),
      'master-%r@%h:%p')
  return _ssh_sock_path

def _ssh_proxy():
  global _ssh_proxy_path
  if _ssh_proxy_path is None:
    _ssh_proxy_path = os.path.join(
      os.path.dirname(__file__),
      'git_ssh')
  return _ssh_proxy_path

def _add_ssh_client(p):
  _ssh_clients.append(p)

def _remove_ssh_client(p):
  try:
    _ssh_clients.remove(p)
  except ValueError:
    pass

def terminate_ssh_clients():
  global _ssh_clients
  for p in _ssh_clients:
    try:
      os.kill(p.pid, SIGTERM)
      p.wait()
    except OSError:
      pass
  _ssh_clients = []

class _GitCall(object):
  def version(self):
    p = GitCommand(None, ['--version'], capture_stdout=True)
    if p.Wait() == 0:
      return p.stdout
    return None

  def __getattr__(self, name):
    name = name.replace('_','-')
    def fun(*cmdv):
      command = [name]
      command.extend(cmdv)
      return GitCommand(None, command).Wait() == 0
    return fun
git = _GitCall()

_git_version = None

def git_require(min_version, fail=False):
  global _git_version

  if _git_version is None:
    ver_str = git.version()
    if ver_str.startswith('git version '):
      _git_version = tuple(
        map(lambda x: int(x),
          ver_str[len('git version '):].strip().split('.')[0:3]
        ))
    else:
      print >>sys.stderr, 'fatal: "%s" unsupported' % ver_str
      sys.exit(1)

  if min_version <= _git_version:
    return True
  if fail:
    need = '.'.join(map(lambda x: str(x), min_version))
    print >>sys.stderr, 'fatal: git %s or later required' % need
    sys.exit(1)
  return False

def _setenv(env, name, value):
  env[name] = value.encode()

class GitCommand(object):
  def __init__(self,
               project,
               cmdv,
               bare = False,
               provide_stdin = False,
               capture_stdout = False,
               capture_stderr = False,
               disable_editor = False,
               ssh_proxy = False,
               cwd = None,
               gitdir = None):
    env = os.environ.copy()

    for e in [REPO_TRACE,
              GIT_DIR,
              'GIT_ALTERNATE_OBJECT_DIRECTORIES',
              'GIT_OBJECT_DIRECTORY',
              'GIT_WORK_TREE',
              'GIT_GRAFT_FILE',
              'GIT_INDEX_FILE']:
      if e in env:
        del env[e]

    if disable_editor:
      _setenv(env, 'GIT_EDITOR', ':')
    if ssh_proxy:
      _setenv(env, 'REPO_SSH_SOCK', ssh_sock())
      _setenv(env, 'GIT_SSH', _ssh_proxy())

    if project:
      if not cwd:
        cwd = project.worktree
      if not gitdir:
        gitdir = project.gitdir

    command = [GIT]
    if bare:
      if gitdir:
        _setenv(env, GIT_DIR, gitdir)
      cwd = None
    command.extend(cmdv)

    if provide_stdin:
      stdin = subprocess.PIPE
    else:
      stdin = None

    if capture_stdout:
      stdout = subprocess.PIPE
    else:
      stdout = None

    if capture_stderr:
      stderr = subprocess.PIPE
    else:
      stderr = None

    if IsTrace():
      global LAST_CWD
      global LAST_GITDIR

      dbg = ''

      if cwd and LAST_CWD != cwd:
        if LAST_GITDIR or LAST_CWD:
          dbg += '\n'
        dbg += ': cd %s\n' % cwd
        LAST_CWD = cwd

      if GIT_DIR in env and LAST_GITDIR != env[GIT_DIR]:
        if LAST_GITDIR or LAST_CWD:
          dbg += '\n'
        dbg += ': export GIT_DIR=%s\n' % env[GIT_DIR]
        LAST_GITDIR = env[GIT_DIR]

      dbg += ': '
      dbg += ' '.join(command)
      if stdin == subprocess.PIPE:
        dbg += ' 0<|'
      if stdout == subprocess.PIPE:
        dbg += ' 1>|'
      if stderr == subprocess.PIPE:
        dbg += ' 2>|'
      Trace('%s', dbg)

    try:
      p = subprocess.Popen(command,
                           cwd = cwd,
                           env = env,
                           stdin = stdin,
                           stdout = stdout,
                           stderr = stderr)
    except Exception, e:
      raise GitError('%s: %s' % (command[1], e))

    if ssh_proxy:
      _add_ssh_client(p)

    self.process = p
    self.stdin = p.stdin

  def Wait(self):
    p = self.process

    if p.stdin:
      p.stdin.close()
      self.stdin = None

    if p.stdout:
      self.stdout = p.stdout.read()
      p.stdout.close()
    else:
      p.stdout = None

    if p.stderr:
      self.stderr = p.stderr.read()
      p.stderr.close()
    else:
      p.stderr = None

    try:
      rc = p.wait()
    finally:
      _remove_ssh_client(p)
    return rc

########NEW FILE########
__FILENAME__ = git_config
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cPickle
import os
import re
import subprocess
import sys
try:
  import threading as _threading
except ImportError:
  import dummy_threading as _threading
import time
import urllib2

from signal import SIGTERM
from urllib2 import urlopen, HTTPError
from error import GitError, UploadError
from trace import Trace

from git_command import GitCommand
from git_command import ssh_sock
from git_command import terminate_ssh_clients

R_HEADS = 'refs/heads/'
R_TAGS  = 'refs/tags/'
ID_RE = re.compile('^[0-9a-f]{40}$')

REVIEW_CACHE = dict()

def IsId(rev):
  return ID_RE.match(rev)

def _key(name):
  parts = name.split('.')
  if len(parts) < 2:
    return name.lower()
  parts[ 0] = parts[ 0].lower()
  parts[-1] = parts[-1].lower()
  return '.'.join(parts)

class GitConfig(object):
  _ForUser = None

  @classmethod
  def ForUser(cls):
    if cls._ForUser is None:
      cls._ForUser = cls(file = os.path.expanduser('~/.gitconfig'))
    return cls._ForUser

  @classmethod
  def ForRepository(cls, gitdir, defaults=None):
    return cls(file = os.path.join(gitdir, 'config'),
               defaults = defaults)

  def __init__(self, file, defaults=None, pickleFile=None):
    self.file = file
    self.defaults = defaults
    self._cache_dict = None
    self._section_dict = None
    self._remotes = {}
    self._branches = {}

    if pickleFile is None:
      self._pickle = os.path.join(
        os.path.dirname(self.file),
        '.repopickle_' + os.path.basename(self.file))
    else:
      self._pickle = pickleFile

  def ClearCache(self):
    if os.path.exists(self._pickle):
      os.remove(self._pickle)
    self._cache_dict = None
    self._section_dict = None
    self._remotes = {}
    self._branches = {}

  def Has(self, name, include_defaults = True):
    """Return true if this configuration file has the key.
    """
    if _key(name) in self._cache:
      return True
    if include_defaults and self.defaults:
      return self.defaults.Has(name, include_defaults = True)
    return False

  def GetBoolean(self, name):
    """Returns a boolean from the configuration file.
       None : The value was not defined, or is not a boolean.
       True : The value was set to true or yes.
       False: The value was set to false or no.
    """
    v = self.GetString(name)
    if v is None:
      return None
    v = v.lower()
    if v in ('true', 'yes'):
      return True
    if v in ('false', 'no'):
      return False
    return None

  def GetString(self, name, all=False):
    """Get the first value for a key, or None if it is not defined.

       This configuration file is used first, if the key is not
       defined or all = True then the defaults are also searched.
    """
    try:
      v = self._cache[_key(name)]
    except KeyError:
      if self.defaults:
        return self.defaults.GetString(name, all = all)
      v = []

    if not all:
      if v:
        return v[0]
      return None

    r = []
    r.extend(v)
    if self.defaults:
      r.extend(self.defaults.GetString(name, all = True))
    return r

  def SetString(self, name, value):
    """Set the value(s) for a key.
       Only this configuration file is modified.

       The supplied value should be either a string,
       or a list of strings (to store multiple values).
    """
    key = _key(name)

    try:
      old = self._cache[key]
    except KeyError:
      old = []

    if value is None:
      if old:
        del self._cache[key]
        self._do('--unset-all', name)

    elif isinstance(value, list):
      if len(value) == 0:
        self.SetString(name, None)

      elif len(value) == 1:
        self.SetString(name, value[0])

      elif old != value:
        self._cache[key] = list(value)
        self._do('--replace-all', name, value[0])
        for i in xrange(1, len(value)):
          self._do('--add', name, value[i])

    elif len(old) != 1 or old[0] != value:
      self._cache[key] = [value]
      self._do('--replace-all', name, value)

  def GetRemote(self, name):
    """Get the remote.$name.* configuration values as an object.
    """
    try:
      r = self._remotes[name]
    except KeyError:
      r = Remote(self, name)
      self._remotes[r.name] = r
    return r

  def GetBranch(self, name):
    """Get the branch.$name.* configuration values as an object.
    """
    try:
      b = self._branches[name]
    except KeyError:
      b = Branch(self, name)
      self._branches[b.name] = b
    return b

  def GetSubSections(self, section):
    """List all subsection names matching $section.*.*
    """
    return self._sections.get(section, set())

  def HasSection(self, section, subsection = ''):
    """Does at least one key in section.subsection exist?
    """
    try:
      return subsection in self._sections[section]
    except KeyError:
      return False

  @property
  def _sections(self):
    d = self._section_dict
    if d is None:
      d = {}
      for name in self._cache.keys():
        p = name.split('.')
        if 2 == len(p):
          section = p[0]
          subsect = ''
        else:
          section = p[0]
          subsect = '.'.join(p[1:-1])
        if section not in d:
          d[section] = set()
        d[section].add(subsect)
        self._section_dict = d
    return d

  @property
  def _cache(self):
    if self._cache_dict is None:
      self._cache_dict = self._Read()
    return self._cache_dict

  def _Read(self):
    d = self._ReadPickle()
    if d is None:
      d = self._ReadGit()
      self._SavePickle(d)
    return d

  def _ReadPickle(self):
    try:
      if os.path.getmtime(self._pickle) \
      <= os.path.getmtime(self.file):
        os.remove(self._pickle)
        return None
    except OSError:
      return None
    try:
      Trace(': unpickle %s', self.file)
      fd = open(self._pickle, 'rb')
      try:
        return cPickle.load(fd)
      finally:
        fd.close()
    except EOFError:
      os.remove(self._pickle)
      return None
    except IOError:
      os.remove(self._pickle)
      return None
    except cPickle.PickleError:
      os.remove(self._pickle)
      return None

  def _SavePickle(self, cache):
    try:
      fd = open(self._pickle, 'wb')
      try:
        cPickle.dump(cache, fd, cPickle.HIGHEST_PROTOCOL)
      finally:
        fd.close()
    except IOError:
      if os.path.exists(self._pickle):
        os.remove(self._pickle)
    except cPickle.PickleError:
      if os.path.exists(self._pickle):
        os.remove(self._pickle)

  def _ReadGit(self):
    """
    Read configuration data from git.

    This internal method populates the GitConfig cache.

    """
    c = {}
    d = self._do('--null', '--list')
    if d is None:
      return c
    for line in d.rstrip('\0').split('\0'):
      if '\n' in line:
          key, val = line.split('\n', 1)
      else:
          key = line
          val = None

      if key in c:
        c[key].append(val)
      else:
        c[key] = [val]

    return c

  def _do(self, *args):
    command = ['config', '--file', self.file]
    command.extend(args)

    p = GitCommand(None,
                   command,
                   capture_stdout = True,
                   capture_stderr = True)
    if p.Wait() == 0:
      return p.stdout
    else:
      GitError('git config %s: %s' % (str(args), p.stderr))


class RefSpec(object):
  """A Git refspec line, split into its components:

      forced:  True if the line starts with '+'
      src:     Left side of the line
      dst:     Right side of the line
  """

  @classmethod
  def FromString(cls, rs):
    lhs, rhs = rs.split(':', 2)
    if lhs.startswith('+'):
      lhs = lhs[1:]
      forced = True
    else:
      forced = False
    return cls(forced, lhs, rhs)

  def __init__(self, forced, lhs, rhs):
    self.forced = forced
    self.src = lhs
    self.dst = rhs

  def SourceMatches(self, rev):
    if self.src:
      if rev == self.src:
        return True
      if self.src.endswith('/*') and rev.startswith(self.src[:-1]):
        return True
    return False

  def DestMatches(self, ref):
    if self.dst:
      if ref == self.dst:
        return True
      if self.dst.endswith('/*') and ref.startswith(self.dst[:-1]):
        return True
    return False

  def MapSource(self, rev):
    if self.src.endswith('/*'):
      return self.dst[:-1] + rev[len(self.src) - 1:]
    return self.dst

  def __str__(self):
    s = ''
    if self.forced:
      s += '+'
    if self.src:
      s += self.src
    if self.dst:
      s += ':'
      s += self.dst
    return s


_master_processes = []
_master_keys = set()
_ssh_master = True
_master_keys_lock = None

def init_ssh():
  """Should be called once at the start of repo to init ssh master handling.

  At the moment, all we do is to create our lock.
  """
  global _master_keys_lock
  assert _master_keys_lock is None, "Should only call init_ssh once"
  _master_keys_lock = _threading.Lock()

def _open_ssh(host, port=None):
  global _ssh_master

  # Acquire the lock.  This is needed to prevent opening multiple masters for
  # the same host when we're running "repo sync -jN" (for N > 1) _and_ the
  # manifest <remote fetch="ssh://xyz"> specifies a different host from the
  # one that was passed to repo init.
  _master_keys_lock.acquire()
  try:

    # Check to see whether we already think that the master is running; if we
    # think it's already running, return right away.
    if port is not None:
      key = '%s:%s' % (host, port)
    else:
      key = host

    if key in _master_keys:
      return True

    if not _ssh_master \
    or 'GIT_SSH' in os.environ \
    or sys.platform in ('win32', 'cygwin'):
      # failed earlier, or cygwin ssh can't do this
      #
      return False

    # We will make two calls to ssh; this is the common part of both calls.
    command_base = ['ssh',
                     '-o','ControlPath %s' % ssh_sock(),
                     host]
    if port is not None:
      command_base[1:1] = ['-p',str(port)]

    # Since the key wasn't in _master_keys, we think that master isn't running.
    # ...but before actually starting a master, we'll double-check.  This can
    # be important because we can't tell that that 'git@myhost.com' is the same
    # as 'myhost.com' where "User git" is setup in the user's ~/.ssh/config file.
    check_command = command_base + ['-O','check']
    try:
      Trace(': %s', ' '.join(check_command))
      check_process = subprocess.Popen(check_command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
      check_process.communicate() # read output, but ignore it...
      isnt_running = check_process.wait()

      if not isnt_running:
        # Our double-check found that the master _was_ infact running.  Add to
        # the list of keys.
        _master_keys.add(key)
        return True
    except Exception:
      # Ignore excpetions.  We we will fall back to the normal command and print
      # to the log there.
      pass

    command = command_base[:1] + \
              ['-M', '-N'] + \
              command_base[1:]
    try:
      Trace(': %s', ' '.join(command))
      p = subprocess.Popen(command)
    except Exception, e:
      _ssh_master = False
      print >>sys.stderr, \
        '\nwarn: cannot enable ssh control master for %s:%s\n%s' \
        % (host,port, str(e))
      return False

    _master_processes.append(p)
    _master_keys.add(key)
    time.sleep(1)
    return True
  finally:
    _master_keys_lock.release()

def close_ssh():
  global _master_keys_lock

  terminate_ssh_clients()

  for p in _master_processes:
    try:
      os.kill(p.pid, SIGTERM)
      p.wait()
    except OSError:
      pass
  del _master_processes[:]
  _master_keys.clear()

  d = ssh_sock(create=False)
  if d:
    try:
      os.rmdir(os.path.dirname(d))
    except OSError:
      pass

  # We're done with the lock, so we can delete it.
  _master_keys_lock = None

URI_SCP = re.compile(r'^([^@:]*@?[^:/]{1,}):')
URI_ALL = re.compile(r'^([a-z][a-z+]*)://([^@/]*@?[^/]*)/')

def _preconnect(url):
  m = URI_ALL.match(url)
  if m:
    scheme = m.group(1)
    host = m.group(2)
    if ':' in host:
      host, port = host.split(':')
    else:
      port = None
    if scheme in ('ssh', 'git+ssh', 'ssh+git'):
      return _open_ssh(host, port)
    return False

  m = URI_SCP.match(url)
  if m:
    host = m.group(1)
    return _open_ssh(host)

  return False

class Remote(object):
  """Configuration options related to a remote.
  """
  def __init__(self, config, name):
    self._config = config
    self.name = name
    self.url = self._Get('url')
    self.review = self._Get('review')
    self.projectname = self._Get('projectname')
    self.fetch = map(lambda x: RefSpec.FromString(x),
                     self._Get('fetch', all=True))
    self._review_protocol = None

  def _InsteadOf(self):
    globCfg = GitConfig.ForUser()
    urlList = globCfg.GetSubSections('url')
    longest = ""
    longestUrl = ""

    for url in urlList:
      key = "url." + url + ".insteadOf"
      insteadOfList = globCfg.GetString(key, all=True)

      for insteadOf in insteadOfList:
        if self.url.startswith(insteadOf) \
        and len(insteadOf) > len(longest):
          longest = insteadOf
          longestUrl = url

    if len(longest) == 0:
      return self.url

    return self.url.replace(longest, longestUrl, 1)

  def PreConnectFetch(self):
    connectionUrl = self._InsteadOf()
    return _preconnect(connectionUrl)

  @property
  def ReviewProtocol(self):
    if self._review_protocol is None:
      if self.review is None:
        return None

      u = self.review
      if not u.startswith('http:') and not u.startswith('https:'):
        u = 'http://%s' % u
      if u.endswith('/Gerrit'):
        u = u[:len(u) - len('/Gerrit')]
      if not u.endswith('/ssh_info'):
        if not u.endswith('/'):
          u += '/'
        u += 'ssh_info'

      if u in REVIEW_CACHE:
        info = REVIEW_CACHE[u]
        self._review_protocol = info[0]
        self._review_host = info[1]
        self._review_port = info[2]
      else:
        try:
          info = urlopen(u).read()
          if info == 'NOT_AVAILABLE':
            raise UploadError('%s: SSH disabled' % self.review)
          if '<' in info:
            # Assume the server gave us some sort of HTML
            # response back, like maybe a login page.
            #
            raise UploadError('%s: Cannot parse response' % u)

          self._review_protocol = 'ssh'
          self._review_host = info.split(" ")[0]
          self._review_port = info.split(" ")[1]
        except urllib2.URLError, e:
          raise UploadError('%s: %s' % (self.review, e.reason[1]))
        except HTTPError, e:
          if e.code == 404:
            self._review_protocol = 'http-post'
            self._review_host = None
            self._review_port = None
          else:
            raise UploadError('Upload over ssh unavailable')

        REVIEW_CACHE[u] = (
          self._review_protocol,
          self._review_host,
          self._review_port)
    return self._review_protocol

  def SshReviewUrl(self, userEmail):
    if self.ReviewProtocol != 'ssh':
      return None
    username = self._config.GetString('review.%s.username' % self.review)
    if username is None:
      username = userEmail.split("@")[0]
    return 'ssh://%s@%s:%s/%s' % (
      username,
      self._review_host,
      self._review_port,
      self.projectname)

  def ToLocal(self, rev):
    """Convert a remote revision string to something we have locally.
    """
    if IsId(rev):
      return rev
    if rev.startswith(R_TAGS):
      return rev

    if not rev.startswith('refs/'):
      rev = R_HEADS + rev

    for spec in self.fetch:
      if spec.SourceMatches(rev):
        return spec.MapSource(rev)
    raise GitError('remote %s does not have %s' % (self.name, rev))

  def WritesTo(self, ref):
    """True if the remote stores to the tracking ref.
    """
    for spec in self.fetch:
      if spec.DestMatches(ref):
        return True
    return False

  def ResetFetch(self, mirror=False):
    """Set the fetch refspec to its default value.
    """
    if mirror:
      dst = 'refs/heads/*'
    else:
      dst = 'refs/remotes/%s/*' % self.name
    self.fetch = [RefSpec(True, 'refs/heads/*', dst)]

  def Save(self):
    """Save this remote to the configuration.
    """
    self._Set('url', self.url)
    self._Set('review', self.review)
    self._Set('projectname', self.projectname)
    self._Set('fetch', map(lambda x: str(x), self.fetch))

  def _Set(self, key, value):
    key = 'remote.%s.%s' % (self.name, key)
    return self._config.SetString(key, value)

  def _Get(self, key, all=False):
    key = 'remote.%s.%s' % (self.name, key)
    return self._config.GetString(key, all = all)


class Branch(object):
  """Configuration options related to a single branch.
  """
  def __init__(self, config, name):
    self._config = config
    self.name = name
    self.merge = self._Get('merge')

    r = self._Get('remote')
    if r:
      self.remote = self._config.GetRemote(r)
    else:
      self.remote = None

  @property
  def LocalMerge(self):
    """Convert the merge spec to a local name.
    """
    if self.remote and self.merge:
      return self.remote.ToLocal(self.merge)
    return None

  def Save(self):
    """Save this branch back into the configuration.
    """
    if self._config.HasSection('branch', self.name):
      if self.remote:
        self._Set('remote', self.remote.name)
      else:
        self._Set('remote', None)
      self._Set('merge', self.merge)

    else:
      fd = open(self._config.file, 'ab')
      try:
        fd.write('[branch "%s"]\n' % self.name)
        if self.remote:
          fd.write('\tremote = %s\n' % self.remote.name)
        if self.merge:
          fd.write('\tmerge = %s\n' % self.merge)
      finally:
        fd.close()

  def _Set(self, key, value):
    key = 'branch.%s.%s' % (self.name, key)
    return self._config.SetString(key, value)

  def _Get(self, key, all=False):
    key = 'branch.%s.%s' % (self.name, key)
    return self._config.GetString(key, all = all)

########NEW FILE########
__FILENAME__ = git_refs
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from trace import Trace

HEAD    = 'HEAD'
R_HEADS = 'refs/heads/'
R_TAGS  = 'refs/tags/'
R_PUB   = 'refs/published/'


class GitRefs(object):
  def __init__(self, gitdir):
    self._gitdir = gitdir
    self._phyref = None
    self._symref = None
    self._mtime = {}

  @property
  def all(self):
    self._EnsureLoaded()
    return self._phyref

  def get(self, name):
    try:
      return self.all[name]
    except KeyError:
      return ''

  def deleted(self, name):
    if self._phyref is not None:
      if name in self._phyref:
        del self._phyref[name]

      if name in self._symref:
        del self._symref[name]

      if name in self._mtime:
        del self._mtime[name]

  def symref(self, name):
    try:
      self._EnsureLoaded()
      return self._symref[name]
    except KeyError:
      return ''

  def _EnsureLoaded(self):
    if self._phyref is None or self._NeedUpdate():
      self._LoadAll()

  def _NeedUpdate(self):
    Trace(': scan refs %s', self._gitdir)

    for name, mtime in self._mtime.iteritems():
      try:
        if mtime != os.path.getmtime(os.path.join(self._gitdir, name)):
          return True
      except OSError:
        return True
    return False

  def _LoadAll(self):
    Trace(': load refs %s', self._gitdir)

    self._phyref = {}
    self._symref = {}
    self._mtime = {}

    self._ReadPackedRefs()
    self._ReadLoose('refs/')
    self._ReadLoose1(os.path.join(self._gitdir, HEAD), HEAD)

    scan = self._symref
    attempts = 0
    while scan and attempts < 5:
      scan_next = {}
      for name, dest in scan.iteritems():
        if dest in self._phyref:
          self._phyref[name] = self._phyref[dest]
        else:
          scan_next[name] = dest
      scan = scan_next
      attempts += 1

  def _ReadPackedRefs(self):
    path = os.path.join(self._gitdir, 'packed-refs')
    try:
      fd = open(path, 'rb')
      mtime = os.path.getmtime(path)
    except IOError:
      return
    except OSError:
      return
    try:
      for line in fd:
        if line[0] == '#':
          continue
        if line[0] == '^':
          continue

        line = line[:-1]
        p = line.split(' ')
        id = p[0]
        name = p[1]

        self._phyref[name] = id
    finally:
      fd.close()
    self._mtime['packed-refs'] = mtime

  def _ReadLoose(self, prefix):
    base = os.path.join(self._gitdir, prefix)
    for name in os.listdir(base):
      p = os.path.join(base, name)
      if os.path.isdir(p):
        self._mtime[prefix] = os.path.getmtime(base)
        self._ReadLoose(prefix + name + '/')
      elif name.endswith('.lock'):
        pass
      else:
        self._ReadLoose1(p, prefix + name)

  def _ReadLoose1(self, path, name):
    try:
      fd = open(path, 'rb')
      mtime = os.path.getmtime(path)
    except OSError:
      return
    except IOError:
      return
    try:
      id = fd.readline()
    finally:
      fd.close()

    if not id:
      return
    id = id[:-1]

    if id.startswith('ref: '):
      self._symref[name] = id[5:]
    else:
      self._phyref[name] = id
    self._mtime[name] = mtime

########NEW FILE########
__FILENAME__ = main
#!/bin/sh
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

magic='--calling-python-from-/bin/sh--'
"""exec" python -E "$0" "$@" """#$magic"
if __name__ == '__main__':
  import sys
  if sys.argv[-1] == '#%s' % magic:
    del sys.argv[-1]
del magic

import optparse
import os
import re
import sys

from trace import SetTrace
from git_config import init_ssh, close_ssh
from command import InteractiveCommand
from command import MirrorSafeCommand
from command import PagedCommand
from error import ManifestInvalidRevisionError
from error import NoSuchProjectError
from error import RepoChangedException
from pager import RunPager

from subcmds import all as all_commands

global_options = optparse.OptionParser(
                 usage="repo [-p|--paginate|--no-pager] COMMAND [ARGS]"
                 )
global_options.add_option('-p', '--paginate',
                          dest='pager', action='store_true',
                          help='display command output in the pager')
global_options.add_option('--no-pager',
                          dest='no_pager', action='store_true',
                          help='disable the pager')
global_options.add_option('--trace',
                          dest='trace', action='store_true',
                          help='trace git command execution')
global_options.add_option('--version',
                          dest='show_version', action='store_true',
                          help='display this version of repo')

class _Repo(object):
  def __init__(self, repodir):
    self.repodir = repodir
    self.commands = all_commands
    # add 'branch' as an alias for 'branches'
    all_commands['branch'] = all_commands['branches']

  def _Run(self, argv):
    name = None
    glob = []

    for i in xrange(0, len(argv)):
      if not argv[i].startswith('-'):
        name = argv[i]
        if i > 0:
          glob = argv[:i]
        argv = argv[i + 1:]
        break
    if not name:
      glob = argv
      name = 'help'
      argv = []
    gopts, gargs = global_options.parse_args(glob)

    if gopts.trace:
      SetTrace()
    if gopts.show_version:
      if name == 'help':
        name = 'version'
      else:
        print >>sys.stderr, 'fatal: invalid usage of --version'
        sys.exit(1)

    try:
      cmd = self.commands[name]
    except KeyError:
      print >>sys.stderr,\
            "repo: '%s' is not a repo command.  See 'repo help'."\
            % name
      sys.exit(1)

    cmd.repodir = self.repodir

    if not isinstance(cmd, MirrorSafeCommand) and cmd.manifest.IsMirror:
      print >>sys.stderr, \
            "fatal: '%s' requires a working directory"\
            % name
      sys.exit(1)

    copts, cargs = cmd.OptionParser.parse_args(argv)

    if not gopts.no_pager and not isinstance(cmd, InteractiveCommand):
      config = cmd.manifest.globalConfig
      if gopts.pager:
        use_pager = True
      else:
        use_pager = config.GetBoolean('pager.%s' % name)
        if use_pager is None:
          use_pager = cmd.WantPager(copts)
      if use_pager:
        RunPager(config)

    try:
      cmd.Execute(copts, cargs)
    except ManifestInvalidRevisionError, e:
      print >>sys.stderr, 'error: %s' % str(e)
      sys.exit(1)
    except NoSuchProjectError, e:
      if e.name:
        print >>sys.stderr, 'error: project %s not found' % e.name
      else:
        print >>sys.stderr, 'error: no project in current directory'
      sys.exit(1)

def _MyWrapperPath():
  return os.path.join(os.path.dirname(__file__), 'repo')

def _CurrentWrapperVersion():
  VERSION = None
  pat = re.compile(r'^VERSION *=')
  fd = open(_MyWrapperPath())
  for line in fd:
    if pat.match(line):
      fd.close()
      exec line
      return VERSION
  raise NameError, 'No VERSION in repo script'

def _CheckWrapperVersion(ver, repo_path):
  if not repo_path:
    repo_path = '~/bin/repo'

  if not ver:
     print >>sys.stderr, 'no --wrapper-version argument'
     sys.exit(1)

  exp = _CurrentWrapperVersion()
  ver = tuple(map(lambda x: int(x), ver.split('.')))
  if len(ver) == 1:
    ver = (0, ver[0])

  if exp[0] > ver[0] or ver < (0, 4):
    exp_str = '.'.join(map(lambda x: str(x), exp))
    print >>sys.stderr, """
!!! A new repo command (%5s) is available.    !!!
!!! You must upgrade before you can continue:   !!!

    cp %s %s
""" % (exp_str, _MyWrapperPath(), repo_path)
    sys.exit(1)

  if exp > ver:
    exp_str = '.'.join(map(lambda x: str(x), exp))
    print >>sys.stderr, """
... A new repo command (%5s) is available.
... You should upgrade soon:

    cp %s %s
""" % (exp_str, _MyWrapperPath(), repo_path)

def _CheckRepoDir(dir):
  if not dir:
     print >>sys.stderr, 'no --repo-dir argument'
     sys.exit(1)

def _PruneOptions(argv, opt):
  i = 0
  while i < len(argv):
    a = argv[i]
    if a == '--':
      break
    if a.startswith('--'):
      eq = a.find('=')
      if eq > 0:
        a = a[0:eq]
    if not opt.has_option(a):
      del argv[i]
      continue
    i += 1

def _Main(argv):
  opt = optparse.OptionParser(usage="repo wrapperinfo -- ...")
  opt.add_option("--repo-dir", dest="repodir",
                 help="path to .repo/")
  opt.add_option("--wrapper-version", dest="wrapper_version",
                 help="version of the wrapper script")
  opt.add_option("--wrapper-path", dest="wrapper_path",
                 help="location of the wrapper script")
  _PruneOptions(argv, opt)
  opt, argv = opt.parse_args(argv)

  _CheckWrapperVersion(opt.wrapper_version, opt.wrapper_path)
  _CheckRepoDir(opt.repodir)

  repo = _Repo(opt.repodir)
  try:
    try:
      init_ssh()
      repo._Run(argv)
    finally:
      close_ssh()
  except KeyboardInterrupt:
    sys.exit(1)
  except RepoChangedException, rce:
    # If repo changed, re-exec ourselves.
    #
    argv = list(sys.argv)
    argv.extend(rce.extra_args)
    try:
      os.execv(__file__, argv)
    except OSError, e:
      print >>sys.stderr, 'fatal: cannot restart repo after upgrade'
      print >>sys.stderr, 'fatal: %s' % e
      sys.exit(128)

if __name__ == '__main__':
  _Main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = manifest
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from error import ManifestParseError
from editor import Editor
from git_config import GitConfig
from project import MetaProject

class Manifest(object):
  """any manifest format"""

  def __init__(self, repodir):
    self.repodir = os.path.abspath(repodir)
    self.topdir = os.path.dirname(self.repodir)
    self.globalConfig = GitConfig.ForUser()
    Editor.globalConfig = self.globalConfig

    self.repoProject = MetaProject(self, 'repo',
      gitdir   = os.path.join(repodir, 'repo/.git'),
      worktree = os.path.join(repodir, 'repo'))

  @property
  def IsMirror(self):
    return self.manifestProject.config.GetBoolean('repo.mirror')

  @property
  def projects(self):
    return {}

  @property
  def notice(self):
    return None

  @property
  def manifest_server(self):
    return None

  def InitBranch(self):
    pass

  def SetMRefs(self, project):
    pass

  def Upgrade_Local(self, old):
    raise ManifestParseError, 'unsupported upgrade path'

########NEW FILE########
__FILENAME__ = manifest_loader
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from manifest_submodule import SubmoduleManifest
from manifest_xml import XmlManifest

def ParseManifest(repodir, type=None):
  if type:
    return type(repodir)
  if SubmoduleManifest.Is(repodir):
    return SubmoduleManifest(repodir)
  return XmlManifest(repodir)

_manifest = None

def GetManifest(repodir, reparse=False, type=None):
  global _manifest
  if _manifest is None \
  or reparse \
  or (type and _manifest.__class__ != type):
    _manifest = ParseManifest(repodir, type=type)
  return _manifest

########NEW FILE########
__FILENAME__ = manifest_submodule
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import shutil

from error import GitError
from error import ManifestParseError
from git_command import GitCommand
from git_config import GitConfig
from git_config import IsId
from manifest import Manifest
from progress import Progress
from project import RemoteSpec
from project import Project
from project import MetaProject
from project import R_HEADS
from project import HEAD
from project import _lwrite

import manifest_xml

GITLINK = '160000'

def _rmdir(dir, top):
  while dir != top:
    try:
      os.rmdir(dir)
    except OSError:
      break
    dir = os.path.dirname(dir)

def _rmref(gitdir, ref):
  os.remove(os.path.join(gitdir, ref))
  log = os.path.join(gitdir, 'logs', ref)
  if os.path.exists(log):
    os.remove(log)
    _rmdir(os.path.dirname(log), gitdir)

def _has_gitmodules(d):
  return os.path.exists(os.path.join(d, '.gitmodules'))

class SubmoduleManifest(Manifest):
  """manifest from .gitmodules file"""

  @classmethod
  def Is(cls, repodir):
    return _has_gitmodules(os.path.dirname(repodir)) \
        or _has_gitmodules(os.path.join(repodir, 'manifest')) \
        or _has_gitmodules(os.path.join(repodir, 'manifests'))

  @classmethod
  def IsBare(cls, p):
    try:
      p.bare_git.cat_file('-e', '%s:.gitmodules' % p.GetRevisionId())
    except GitError:
      return False
    return True

  def __init__(self, repodir):
    Manifest.__init__(self, repodir)

    gitdir = os.path.join(repodir, 'manifest.git')
    config = GitConfig.ForRepository(gitdir = gitdir)

    if config.GetBoolean('repo.mirror'):
      worktree = os.path.join(repodir, 'manifest')
      relpath = None
    else:
      worktree = self.topdir
      relpath  = '.'

    self.manifestProject = MetaProject(self, '__manifest__',
      gitdir   = gitdir,
      worktree = worktree,
      relpath  = relpath)
    self._modules = GitConfig(os.path.join(worktree, '.gitmodules'),
                              pickleFile = os.path.join(
                                repodir, '.repopickle_gitmodules'
                              ))
    self._review = GitConfig(os.path.join(worktree, '.review'),
                             pickleFile = os.path.join(
                               repodir, '.repopickle_review'
                             ))
    self._Unload()

  @property
  def projects(self):
    self._Load()
    return self._projects

  @property
  def notice(self):
    return self._modules.GetString('repo.notice')

  def InitBranch(self):
    m = self.manifestProject
    if m.CurrentBranch is None:
      b = m.revisionExpr
      if b.startswith(R_HEADS):
        b = b[len(R_HEADS):]
      return m.StartBranch(b)
    return True

  def SetMRefs(self, project):
    if project.revisionId is None:
      # Special project, e.g. the manifest or repo executable.
      #
      return

    ref = 'refs/remotes/m'
    cur = project.bare_ref.get(ref)
    exp = project.revisionId
    if cur != exp:
      msg = 'manifest set to %s' % exp
      project.bare_git.UpdateRef(ref, exp, message = msg, detach = True)

    ref = 'refs/remotes/m-revision'
    cur = project.bare_ref.symref(ref)
    exp = project.revisionExpr
    if exp is None:
      if cur:
        _rmref(project.gitdir, ref)
    elif cur != exp:
      remote = project.GetRemote(project.remote.name)
      dst = remote.ToLocal(exp)
      msg = 'manifest set to %s (%s)' % (exp, dst)
      project.bare_git.symbolic_ref('-m', msg, ref, dst)

  def Upgrade_Local(self, old):
    if isinstance(old, manifest_xml.XmlManifest):
      self.FromXml_Local_1(old, checkout=True)
      self.FromXml_Local_2(old)
    else:
      raise ManifestParseError, 'cannot upgrade manifest'

  def FromXml_Local_1(self, old, checkout):
    os.rename(old.manifestProject.gitdir,
              os.path.join(old.repodir, 'manifest.git'))

    oldmp = old.manifestProject
    oldBranch = oldmp.CurrentBranch
    b = oldmp.GetBranch(oldBranch).merge
    if not b:
      raise ManifestParseError, 'cannot upgrade manifest'
    if b.startswith(R_HEADS):
      b = b[len(R_HEADS):]

    newmp = self.manifestProject
    self._CleanOldMRefs(newmp)
    if oldBranch != b:
      newmp.bare_git.branch('-m', oldBranch, b)
      newmp.config.ClearCache()

    old_remote = newmp.GetBranch(b).remote.name
    act_remote = self._GuessRemoteName(old)
    if old_remote != act_remote:
      newmp.bare_git.remote('rename', old_remote, act_remote)
      newmp.config.ClearCache()
    newmp.remote.name = act_remote
    print >>sys.stderr, "Assuming remote named '%s'" % act_remote

    if checkout:
      for p in old.projects.values():
        for c in p.copyfiles:
          if os.path.exists(c.abs_dest):
            os.remove(c.abs_dest)
      newmp._InitWorkTree()
    else:
      newmp._LinkWorkTree()

    _lwrite(os.path.join(newmp.worktree,'.git',HEAD),
            'ref: refs/heads/%s\n' % b)

  def _GuessRemoteName(self, old):
    used = {}
    for p in old.projects.values():
      n = p.remote.name
      used[n] = used.get(n, 0) + 1

    remote_name = 'origin'
    remote_used = 0
    for n in used.keys():
      if remote_used < used[n]:
        remote_used = used[n]
        remote_name = n
    return remote_name

  def FromXml_Local_2(self, old):
    shutil.rmtree(old.manifestProject.worktree)
    os.remove(old._manifestFile)

    my_remote = self._Remote().name
    new_base = os.path.join(self.repodir, 'projects')
    old_base = os.path.join(self.repodir, 'projects.old')
    os.rename(new_base, old_base)
    os.makedirs(new_base)

    info = []
    pm = Progress('Converting projects', len(self.projects))
    for p in self.projects.values():
      pm.update()

      old_p = old.projects.get(p.name)
      old_gitdir = os.path.join(old_base, '%s.git' % p.relpath)
      if not os.path.isdir(old_gitdir):
        continue

      parent = os.path.dirname(p.gitdir)
      if not os.path.isdir(parent):
        os.makedirs(parent)
      os.rename(old_gitdir, p.gitdir)
      _rmdir(os.path.dirname(old_gitdir), self.repodir)

      if not os.path.isdir(p.worktree):
        os.makedirs(p.worktree)

      if os.path.isdir(os.path.join(p.worktree, '.git')):
        p._LinkWorkTree(relink=True)

      self._CleanOldMRefs(p)
      if old_p and old_p.remote.name != my_remote:
        info.append("%s/: renamed remote '%s' to '%s'" \
                    % (p.relpath, old_p.remote.name, my_remote))
        p.bare_git.remote('rename', old_p.remote.name, my_remote)
        p.config.ClearCache()

      self.SetMRefs(p)
    pm.end()
    for i in info:
      print >>sys.stderr, i

  def _CleanOldMRefs(self, p):
    all_refs = p._allrefs
    for ref in all_refs.keys():
      if ref.startswith(manifest_xml.R_M):
        if p.bare_ref.symref(ref) != '':
          _rmref(p.gitdir, ref)
        else:
          p.bare_git.DeleteRef(ref, all_refs[ref])

  def FromXml_Definition(self, old):
    """Convert another manifest representation to this one.
    """
    mp = self.manifestProject
    gm = self._modules
    gr = self._review

    fd = open(os.path.join(mp.worktree, '.gitignore'), 'ab')
    fd.write('/.repo\n')
    fd.close()

    sort_projects = list(old.projects.keys())
    sort_projects.sort()

    b = mp.GetBranch(mp.CurrentBranch).merge
    if b.startswith(R_HEADS):
      b = b[len(R_HEADS):]

    if old.notice:
      gm.SetString('repo.notice', old.notice)

    info = []
    pm = Progress('Converting manifest', len(sort_projects))
    for p in sort_projects:
      pm.update()
      p = old.projects[p]

      gm.SetString('submodule.%s.path' % p.name, p.relpath)
      gm.SetString('submodule.%s.url' % p.name, p.remote.url)

      if gr.GetString('review.url') is None:
        gr.SetString('review.url', p.remote.review)
      elif gr.GetString('review.url') != p.remote.review:
        gr.SetString('review.%s.url' % p.name, p.remote.review)

      r = p.revisionExpr
      if r and not IsId(r):
        if r.startswith(R_HEADS):
          r = r[len(R_HEADS):]
        if r == b:
          r = '.'
        gm.SetString('submodule.%s.revision' % p.name, r)

      for c in p.copyfiles:
        info.append('Moved %s out of %s' % (c.src, p.relpath))
        c._Copy()
        p.work_git.rm(c.src)
        mp.work_git.add(c.dest)

      self.SetRevisionId(p.relpath, p.GetRevisionId())
    mp.work_git.add('.gitignore', '.gitmodules', '.review')
    pm.end()
    for i in info:
      print >>sys.stderr, i

  def _Unload(self):
    self._loaded = False
    self._projects = {}
    self._revisionIds = None
    self.branch = None

  def _Load(self):
    if not self._loaded:
      f = os.path.join(self.repodir, manifest_xml.LOCAL_MANIFEST_NAME)
      if os.path.exists(f):
        print >>sys.stderr, 'warning: ignoring %s' % f

      m = self.manifestProject
      b = m.CurrentBranch
      if not b:
        raise ManifestParseError, 'manifest cannot be on detached HEAD'
      b = m.GetBranch(b).merge
      if b.startswith(R_HEADS):
        b = b[len(R_HEADS):]
      self.branch = b
      m.remote.name = self._Remote().name

      self._ParseModules()

      if self.IsMirror:
        self._AddMetaProjectMirror(self.repoProject)
        self._AddMetaProjectMirror(self.manifestProject)

      self._loaded = True

  def _ParseModules(self):
    byPath = dict()
    for name in self._modules.GetSubSections('submodule'):
      p = self._ParseProject(name)
      if self._projects.get(p.name):
        raise ManifestParseError, 'duplicate project "%s"' % p.name
      if byPath.get(p.relpath):
        raise ManifestParseError, 'duplicate path "%s"' % p.relpath
      self._projects[p.name] = p
      byPath[p.relpath] = p

    for relpath in self._allRevisionIds.keys():
      if relpath not in byPath:
        raise ManifestParseError, \
          'project "%s" not in .gitmodules' \
          % relpath

  def _Remote(self):
    m = self.manifestProject
    b = m.GetBranch(m.CurrentBranch)
    return b.remote

  def _ResolveUrl(self, url):
    if url.startswith('./') or url.startswith('../'):
      base = self._Remote().url
      try:
        base = base[:base.rindex('/')+1]
      except ValueError:
        base = base[:base.rindex(':')+1]
      if url.startswith('./'):
        url = url[2:]
      while '/' in base and url.startswith('../'):
        base = base[:base.rindex('/')+1]
        url = url[3:]
      return base + url
    return url

  def _GetRevisionId(self, path):
    return self._allRevisionIds.get(path)

  @property
  def _allRevisionIds(self):
    if self._revisionIds is None:
      a = dict()
      p = GitCommand(self.manifestProject,
                     ['ls-files','-z','--stage'],
                     capture_stdout = True)
      for line in p.process.stdout.read().split('\0')[:-1]:
        l_info, l_path = line.split('\t', 2)
        l_mode, l_id, l_stage = l_info.split(' ', 2)
        if l_mode == GITLINK and l_stage == '0':
          a[l_path] = l_id
      p.Wait()
      self._revisionIds = a
    return self._revisionIds

  def SetRevisionId(self, path, id):
    self.manifestProject.work_git.update_index(
      '--add','--cacheinfo', GITLINK, id, path)

  def _ParseProject(self, name):
    gm = self._modules
    gr = self._review

    path = gm.GetString('submodule.%s.path' % name)
    if not path:
      path = name

    revId = self._GetRevisionId(path)
    if not revId:
      raise ManifestParseError(
        'submodule "%s" has no revision at "%s"' \
        % (name, path))

    url = gm.GetString('submodule.%s.url' % name)
    if not url:
      url = name
    url = self._ResolveUrl(url)

    review = gr.GetString('review.%s.url' % name)
    if not review:
      review = gr.GetString('review.url')
    if not review:
      review = self._Remote().review

    remote = RemoteSpec(self._Remote().name, url, review)
    revExpr = gm.GetString('submodule.%s.revision' % name)
    if revExpr == '.':
      revExpr = self.branch

    if self.IsMirror:
      relpath = None
      worktree = None
      gitdir = os.path.join(self.topdir, '%s.git' % name)
    else:
      worktree = os.path.join(self.topdir, path)
      gitdir = os.path.join(self.repodir, 'projects/%s.git' % name)

    return Project(manifest = self,
                   name = name,
                   remote = remote,
                   gitdir = gitdir,
                   worktree = worktree,
                   relpath = path,
                   revisionExpr = revExpr,
                   revisionId = revId)

  def _AddMetaProjectMirror(self, m):
    m_url = m.GetRemote(m.remote.name).url
    if m_url.endswith('/.git'):
      raise ManifestParseError, 'refusing to mirror %s' % m_url

    name = self._GuessMetaName(m_url)
    if name.endswith('.git'):
      name = name[:-4]

    if name not in self._projects:
      m.PreSync()
      gitdir = os.path.join(self.topdir, '%s.git' % name)
      project = Project(manifest = self,
                        name = name,
                        remote = RemoteSpec(self._Remote().name, m_url),
                        gitdir = gitdir,
                        worktree = None,
                        relpath = None,
                        revisionExpr = m.revisionExpr,
                        revisionId = None)
      self._projects[project.name] = project

  def _GuessMetaName(self, m_url):
    parts = m_url.split('/')
    name = parts[-1]
    parts = parts[0:-1]
    s = len(parts) - 1
    while s > 0:
      l = '/'.join(parts[0:s]) + '/'
      r = '/'.join(parts[s:]) + '/'
      for p in self._projects.values():
        if p.name.startswith(r) and p.remote.url.startswith(l):
          return r + name
      s -= 1
    return m_url[m_url.rindex('/') + 1:]

########NEW FILE########
__FILENAME__ = manifest_xml
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import xml.dom.minidom

from git_config import GitConfig
from git_config import IsId
from manifest import Manifest
from project import RemoteSpec
from project import Project
from project import MetaProject
from project import R_HEADS
from project import HEAD
from error import ManifestParseError

MANIFEST_FILE_NAME = 'manifest.xml'
LOCAL_MANIFEST_NAME = 'local_manifest.xml'
R_M = 'refs/remotes/m/'

class _Default(object):
  """Project defaults within the manifest."""

  revisionExpr = None
  remote = None

class _XmlRemote(object):
  def __init__(self,
               name,
               fetch=None,
               review=None):
    self.name = name
    self.fetchUrl = fetch
    self.reviewUrl = review

  def ToRemoteSpec(self, projectName):
    url = self.fetchUrl
    while url.endswith('/'):
      url = url[:-1]
    url += '/%s.git' % projectName
    return RemoteSpec(self.name, url, self.reviewUrl)

class XmlManifest(Manifest):
  """manages the repo configuration file"""

  def __init__(self, repodir):
    Manifest.__init__(self, repodir)

    self._manifestFile = os.path.join(repodir, MANIFEST_FILE_NAME)
    self.manifestProject = MetaProject(self, 'manifests',
      gitdir   = os.path.join(repodir, 'manifests.git'),
      worktree = os.path.join(repodir, 'manifests'))

    self._Unload()

  def Override(self, name):
    """Use a different manifest, just for the current instantiation.
    """
    path = os.path.join(self.manifestProject.worktree, name)
    if not os.path.isfile(path):
      raise ManifestParseError('manifest %s not found' % name)

    old = self._manifestFile
    try:
      self._manifestFile = path
      self._Unload()
      self._Load()
    finally:
      self._manifestFile = old

  def Link(self, name):
    """Update the repo metadata to use a different manifest.
    """
    self.Override(name)

    try:
      if os.path.exists(self._manifestFile):
        os.remove(self._manifestFile)
      os.symlink('manifests/%s' % name, self._manifestFile)
    except OSError, e:
      raise ManifestParseError('cannot link manifest %s' % name)

  def _RemoteToXml(self, r, doc, root):
    e = doc.createElement('remote')
    root.appendChild(e)
    e.setAttribute('name', r.name)
    e.setAttribute('fetch', r.fetchUrl)
    if r.reviewUrl is not None:
      e.setAttribute('review', r.reviewUrl)

  def Save(self, fd, peg_rev=False):
    """Write the current manifest out to the given file descriptor.
    """
    doc = xml.dom.minidom.Document()
    root = doc.createElement('manifest')
    doc.appendChild(root)

    # Save out the notice.  There's a little bit of work here to give it the
    # right whitespace, which assumes that the notice is automatically indented
    # by 4 by minidom.
    if self.notice:
      notice_element = root.appendChild(doc.createElement('notice'))
      notice_lines = self.notice.splitlines()
      indented_notice = ('\n'.join(" "*4 + line for line in notice_lines))[4:]
      notice_element.appendChild(doc.createTextNode(indented_notice))

    d = self.default
    sort_remotes = list(self.remotes.keys())
    sort_remotes.sort()

    for r in sort_remotes:
      self._RemoteToXml(self.remotes[r], doc, root)
    if self.remotes:
      root.appendChild(doc.createTextNode(''))

    have_default = False
    e = doc.createElement('default')
    if d.remote:
      have_default = True
      e.setAttribute('remote', d.remote.name)
    if d.revisionExpr:
      have_default = True
      e.setAttribute('revision', d.revisionExpr)
    if have_default:
      root.appendChild(e)
      root.appendChild(doc.createTextNode(''))

    if self._manifest_server:
      e = doc.createElement('manifest-server')
      e.setAttribute('url', self._manifest_server)
      root.appendChild(e)
      root.appendChild(doc.createTextNode(''))

    sort_projects = list(self.projects.keys())
    sort_projects.sort()

    for p in sort_projects:
      p = self.projects[p]
      e = doc.createElement('project')
      root.appendChild(e)
      e.setAttribute('name', p.name)
      if p.relpath != p.name:
        e.setAttribute('path', p.relpath)
      if not d.remote or p.remote.name != d.remote.name:
        e.setAttribute('remote', p.remote.name)
      if peg_rev:
        if self.IsMirror:
          e.setAttribute('revision',
                         p.bare_git.rev_parse(p.revisionExpr + '^0'))
        else:
          e.setAttribute('revision',
                         p.work_git.rev_parse(HEAD + '^0'))
      elif not d.revisionExpr or p.revisionExpr != d.revisionExpr:
        e.setAttribute('revision', p.revisionExpr)

      for c in p.copyfiles:
        ce = doc.createElement('copyfile')
        ce.setAttribute('src', c.src)
        ce.setAttribute('dest', c.dest)
        e.appendChild(ce)

    doc.writexml(fd, '', '  ', '\n', 'UTF-8')

  @property
  def projects(self):
    self._Load()
    return self._projects

  @property
  def remotes(self):
    self._Load()
    return self._remotes

  @property
  def default(self):
    self._Load()
    return self._default

  @property
  def notice(self):
    self._Load()
    return self._notice

  @property
  def manifest_server(self):
    self._Load()
    return self._manifest_server

  def InitBranch(self):
    m = self.manifestProject
    if m.CurrentBranch is None:
      return m.StartBranch('default')
    return True

  def SetMRefs(self, project):
    if self.branch:
      project._InitAnyMRef(R_M + self.branch)

  def _Unload(self):
    self._loaded = False
    self._projects = {}
    self._remotes = {}
    self._default = None
    self._notice = None
    self.branch = None
    self._manifest_server = None

  def _Load(self):
    if not self._loaded:
      m = self.manifestProject
      b = m.GetBranch(m.CurrentBranch)
      if b.remote and b.remote.name:
        m.remote.name = b.remote.name
      b = b.merge
      if b is not None and b.startswith(R_HEADS):
        b = b[len(R_HEADS):]
      self.branch = b

      self._ParseManifest(True)

      local = os.path.join(self.repodir, LOCAL_MANIFEST_NAME)
      if os.path.exists(local):
        try:
          real = self._manifestFile
          self._manifestFile = local
          self._ParseManifest(False)
        finally:
          self._manifestFile = real

      if self.IsMirror:
        self._AddMetaProjectMirror(self.repoProject)
        self._AddMetaProjectMirror(self.manifestProject)

      self._loaded = True

  def _ParseManifest(self, is_root_file):
    root = xml.dom.minidom.parse(self._manifestFile)
    if not root or not root.childNodes:
      raise ManifestParseError, \
            "no root node in %s" % \
            self._manifestFile

    config = root.childNodes[0]
    if config.nodeName != 'manifest':
      raise ManifestParseError, \
            "no <manifest> in %s" % \
            self._manifestFile

    for node in config.childNodes:
      if node.nodeName == 'remove-project':
        name = self._reqatt(node, 'name')
        try:
          del self._projects[name]
        except KeyError:
          raise ManifestParseError, \
                'project %s not found' % \
                (name)

    for node in config.childNodes:
      if node.nodeName == 'remote':
        remote = self._ParseRemote(node)
        if self._remotes.get(remote.name):
          raise ManifestParseError, \
                'duplicate remote %s in %s' % \
                (remote.name, self._manifestFile)
        self._remotes[remote.name] = remote

    for node in config.childNodes:
      if node.nodeName == 'default':
        if self._default is not None:
          raise ManifestParseError, \
                'duplicate default in %s' % \
                (self._manifestFile)
        self._default = self._ParseDefault(node)
    if self._default is None:
      self._default = _Default()

    for node in config.childNodes:
      if node.nodeName == 'notice':
        if self._notice is not None:
          raise ManifestParseError, \
                'duplicate notice in %s' % \
                (self.manifestFile)
        self._notice = self._ParseNotice(node)

    for node in config.childNodes:
      if node.nodeName == 'manifest-server':
        url = self._reqatt(node, 'url')
        if self._manifest_server is not None:
            raise ManifestParseError, \
                'duplicate manifest-server in %s' % \
                (self.manifestFile)
        self._manifest_server = url

    for node in config.childNodes:
      if node.nodeName == 'project':
        project = self._ParseProject(node)
        if self._projects.get(project.name):
          raise ManifestParseError, \
                'duplicate project %s in %s' % \
                (project.name, self._manifestFile)
        self._projects[project.name] = project

  def _AddMetaProjectMirror(self, m):
    name = None
    m_url = m.GetRemote(m.remote.name).url
    if m_url.endswith('/.git'):
      raise ManifestParseError, 'refusing to mirror %s' % m_url

    if self._default and self._default.remote:
      url = self._default.remote.fetchUrl
      if not url.endswith('/'):
        url += '/'
      if m_url.startswith(url):
        remote = self._default.remote
        name = m_url[len(url):]

    if name is None:
      s = m_url.rindex('/') + 1
      remote = _XmlRemote('origin', m_url[:s])
      name = m_url[s:]

    if name.endswith('.git'):
      name = name[:-4]

    if name not in self._projects:
      m.PreSync()
      gitdir = os.path.join(self.topdir, '%s.git' % name)
      project = Project(manifest = self,
                        name = name,
                        remote = remote.ToRemoteSpec(name),
                        gitdir = gitdir,
                        worktree = None,
                        relpath = None,
                        revisionExpr = m.revisionExpr,
                        revisionId = None)
      self._projects[project.name] = project

  def _ParseRemote(self, node):
    """
    reads a <remote> element from the manifest file
    """
    name = self._reqatt(node, 'name')
    fetch = self._reqatt(node, 'fetch')
    review = node.getAttribute('review')
    if review == '':
      review = None
    return _XmlRemote(name, fetch, review)

  def _ParseDefault(self, node):
    """
    reads a <default> element from the manifest file
    """
    d = _Default()
    d.remote = self._get_remote(node)
    d.revisionExpr = node.getAttribute('revision')
    if d.revisionExpr == '':
      d.revisionExpr = None
    return d

  def _ParseNotice(self, node):
    """
    reads a <notice> element from the manifest file

    The <notice> element is distinct from other tags in the XML in that the
    data is conveyed between the start and end tag (it's not an empty-element
    tag).

    The white space (carriage returns, indentation) for the notice element is
    relevant and is parsed in a way that is based on how python docstrings work.
    In fact, the code is remarkably similar to here:
      http://www.python.org/dev/peps/pep-0257/
    """
    # Get the data out of the node...
    notice = node.childNodes[0].data

    # Figure out minimum indentation, skipping the first line (the same line
    # as the <notice> tag)...
    minIndent = sys.maxint
    lines = notice.splitlines()
    for line in lines[1:]:
      lstrippedLine = line.lstrip()
      if lstrippedLine:
        indent = len(line) - len(lstrippedLine)
        minIndent = min(indent, minIndent)

    # Strip leading / trailing blank lines and also indentation.
    cleanLines = [lines[0].strip()]
    for line in lines[1:]:
      cleanLines.append(line[minIndent:].rstrip())

    # Clear completely blank lines from front and back...
    while cleanLines and not cleanLines[0]:
      del cleanLines[0]
    while cleanLines and not cleanLines[-1]:
      del cleanLines[-1]

    return '\n'.join(cleanLines)

  def _ParseProject(self, node):
    """
    reads a <project> element from the manifest file
    """
    name = self._reqatt(node, 'name')

    remote = self._get_remote(node)
    if remote is None:
      remote = self._default.remote
    if remote is None:
      raise ManifestParseError, \
            "no remote for project %s within %s" % \
            (name, self._manifestFile)

    revisionExpr = node.getAttribute('revision')
    if not revisionExpr:
      revisionExpr = self._default.revisionExpr
    if not revisionExpr:
      raise ManifestParseError, \
            "no revision for project %s within %s" % \
            (name, self._manifestFile)

    path = node.getAttribute('path')
    if not path:
      path = name
    if path.startswith('/'):
      raise ManifestParseError, \
            "project %s path cannot be absolute in %s" % \
            (name, self._manifestFile)

    if self.IsMirror:
      relpath = None
      worktree = None
      gitdir = os.path.join(self.topdir, '%s.git' % name)
    else:
      worktree = os.path.join(self.topdir, path).replace('\\', '/')
      gitdir = os.path.join(self.repodir, 'projects/%s.git' % path)

    project = Project(manifest = self,
                      name = name,
                      remote = remote.ToRemoteSpec(name),
                      gitdir = gitdir,
                      worktree = worktree,
                      relpath = path,
                      revisionExpr = revisionExpr,
                      revisionId = None)

    for n in node.childNodes:
      if n.nodeName == 'copyfile':
        self._ParseCopyFile(project, n)

    return project

  def _ParseCopyFile(self, project, node):
    src = self._reqatt(node, 'src')
    dest = self._reqatt(node, 'dest')
    if not self.IsMirror:
      # src is project relative;
      # dest is relative to the top of the tree
      project.AddCopyFile(src, dest, os.path.join(self.topdir, dest))

  def _get_remote(self, node):
    name = node.getAttribute('remote')
    if not name:
      return None

    v = self._remotes.get(name)
    if not v:
      raise ManifestParseError, \
            "remote %s not defined in %s" % \
            (name, self._manifestFile)
    return v

  def _reqatt(self, node, attname):
    """
    reads a required attribute from the node.
    """
    v = node.getAttribute(attname)
    if not v:
      raise ManifestParseError, \
            "no %s in <%s> within %s" % \
            (attname, node.nodeName, self._manifestFile)
    return v

########NEW FILE########
__FILENAME__ = pager
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import select
import sys

active = False

def RunPager(globalConfig):
  global active

  if not os.isatty(0) or not os.isatty(1):
    return
  pager = _SelectPager(globalConfig)
  if pager == '' or pager == 'cat':
    return

  # This process turns into the pager; a child it forks will
  # do the real processing and output back to the pager. This
  # is necessary to keep the pager in control of the tty.
  #
  try:
    r, w = os.pipe()
    pid = os.fork()
    if not pid:
      os.dup2(w, 1)
      os.dup2(w, 2)
      os.close(r)
      os.close(w)
      active = True
      return

    os.dup2(r, 0)
    os.close(r)
    os.close(w)

    _BecomePager(pager)
  except Exception:
    print >>sys.stderr, "fatal: cannot start pager '%s'" % pager
    os.exit(255)

def _SelectPager(globalConfig):
  try:
    return os.environ['GIT_PAGER']
  except KeyError:
    pass

  pager = globalConfig.GetString('core.pager')
  if pager:
    return pager

  try:
    return os.environ['PAGER']
  except KeyError:
    pass

  return 'less'

def _BecomePager(pager):
  # Delaying execution of the pager until we have output
  # ready works around a long-standing bug in popularly
  # available versions of 'less', a better 'more'.
  #
  a, b, c = select.select([0], [], [0])

  os.environ['LESS'] = 'FRSX'

  try:
    os.execvp(pager, [pager])
  except OSError, e:
    os.execv('/bin/sh', ['sh', '-c', pager])

########NEW FILE########
__FILENAME__ = progress
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from time import time
from trace import IsTrace

_NOT_TTY = not os.isatty(2)

class Progress(object):
  def __init__(self, title, total=0):
    self._title = title
    self._total = total
    self._done = 0
    self._lastp = -1
    self._start = time()
    self._show = False

  def update(self, inc=1):
    self._done += inc

    if _NOT_TTY or IsTrace():
      return

    if not self._show:
      if 0.5 <= time() - self._start:
        self._show = True
      else:
        return

    if self._total <= 0:
      sys.stderr.write('\r%s: %d, ' % (
        self._title,
        self._done))
      sys.stderr.flush()
    else:
      p = (100 * self._done) / self._total

      if self._lastp != p:
        self._lastp = p
        sys.stderr.write('\r%s: %3d%% (%d/%d)  ' % (
          self._title,
          p,
          self._done,
          self._total))
        sys.stderr.flush()

  def end(self):
    if _NOT_TTY or IsTrace() or not self._show:
      return

    if self._total <= 0:
      sys.stderr.write('\r%s: %d, done.  \n' % (
        self._title,
        self._done))
      sys.stderr.flush()
    else:
      p = (100 * self._done) / self._total
      sys.stderr.write('\r%s: %3d%% (%d/%d), done.  \n' % (
        self._title,
        p,
        self._done,
        self._total))
      sys.stderr.flush()

########NEW FILE########
__FILENAME__ = project
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import errno
import filecmp
import os
import re
import shutil
import stat
import sys
import urllib2

from color import Coloring
from git_command import GitCommand
from git_config import GitConfig, IsId
from error import GitError, ImportError, UploadError
from error import ManifestInvalidRevisionError

from git_refs import GitRefs, HEAD, R_HEADS, R_TAGS, R_PUB

def _lwrite(path, content):
  lock = '%s.lock' % path

  fd = open(lock, 'wb')
  try:
    fd.write(content)
  finally:
    fd.close()

  try:
    os.rename(lock, path)
  except OSError:
    os.remove(lock)
    raise

def _error(fmt, *args):
  msg = fmt % args
  print >>sys.stderr, 'error: %s' % msg

def not_rev(r):
  return '^' + r

def sq(r):
  return "'" + r.replace("'", "'\''") + "'"

hook_list = None
def repo_hooks():
  global hook_list
  if hook_list is None:
    d = os.path.abspath(os.path.dirname(__file__))
    d = os.path.join(d , 'hooks')
    hook_list = map(lambda x: os.path.join(d, x), os.listdir(d))
  return hook_list

def relpath(dst, src):
  src = os.path.dirname(src)
  top = os.path.commonprefix([dst, src])
  if top.endswith('/'):
    top = top[:-1]
  else:
    top = os.path.dirname(top)

  tmp = src
  rel = ''
  while top != tmp:
    rel += '../'
    tmp = os.path.dirname(tmp)
  return rel + dst[len(top) + 1:]


class DownloadedChange(object):
  _commit_cache = None

  def __init__(self, project, base, change_id, ps_id, commit):
    self.project = project
    self.base = base
    self.change_id = change_id
    self.ps_id = ps_id
    self.commit = commit

  @property
  def commits(self):
    if self._commit_cache is None:
      self._commit_cache = self.project.bare_git.rev_list(
        '--abbrev=8',
        '--abbrev-commit',
        '--pretty=oneline',
        '--reverse',
        '--date-order',
        not_rev(self.base),
        self.commit,
        '--')
    return self._commit_cache


class ReviewableBranch(object):
  _commit_cache = None

  def __init__(self, project, branch, base):
    self.project = project
    self.branch = branch
    self.base = base

  @property
  def name(self):
    return self.branch.name

  @property
  def commits(self):
    if self._commit_cache is None:
      self._commit_cache = self.project.bare_git.rev_list(
        '--abbrev=8',
        '--abbrev-commit',
        '--pretty=oneline',
        '--reverse',
        '--date-order',
        not_rev(self.base),
        R_HEADS + self.name,
        '--')
    return self._commit_cache

  @property
  def unabbrev_commits(self):
    r = dict()
    for commit in self.project.bare_git.rev_list(
        not_rev(self.base),
        R_HEADS + self.name,
        '--'):
      r[commit[0:8]] = commit
    return r

  @property
  def date(self):
    return self.project.bare_git.log(
      '--pretty=format:%cd',
      '-n', '1',
      R_HEADS + self.name,
      '--')

  def UploadForReview(self, people, auto_topic=False):
    self.project.UploadForReview(self.name,
                                 people,
                                 auto_topic=auto_topic)

  def GetPublishedRefs(self):
    refs = {}
    output = self.project.bare_git.ls_remote(
      self.branch.remote.SshReviewUrl(self.project.UserEmail),
      'refs/changes/*')
    for line in output.split('\n'):
      try:
        (sha, ref) = line.split()
        refs[sha] = ref
      except ValueError:
        pass

    return refs

class StatusColoring(Coloring):
  def __init__(self, config):
    Coloring.__init__(self, config, 'status')
    self.project   = self.printer('header',    attr = 'bold')
    self.branch    = self.printer('header',    attr = 'bold')
    self.nobranch  = self.printer('nobranch',  fg = 'red')
    self.important = self.printer('important', fg = 'red')

    self.added     = self.printer('added',     fg = 'green')
    self.changed   = self.printer('changed',   fg = 'red')
    self.untracked = self.printer('untracked', fg = 'red')


class DiffColoring(Coloring):
  def __init__(self, config):
    Coloring.__init__(self, config, 'diff')
    self.project   = self.printer('header',    attr = 'bold')


class _CopyFile:
  def __init__(self, src, dest, abssrc, absdest):
    self.src = src
    self.dest = dest
    self.abs_src = abssrc
    self.abs_dest = absdest

  def _Copy(self):
    src = self.abs_src
    dest = self.abs_dest
    # copy file if it does not exist or is out of date
    if not os.path.exists(dest) or not filecmp.cmp(src, dest):
      try:
        # remove existing file first, since it might be read-only
        if os.path.exists(dest):
          os.remove(dest)
        else:
          dir = os.path.dirname(dest)
          if not os.path.isdir(dir):
            os.makedirs(dir)
        shutil.copy(src, dest)
        # make the file read-only
        mode = os.stat(dest)[stat.ST_MODE]
        mode = mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
        os.chmod(dest, mode)
      except IOError:
        _error('Cannot copy file %s to %s', src, dest)

class RemoteSpec(object):
  def __init__(self,
               name,
               url = None,
               review = None):
    self.name = name
    self.url = url
    self.review = review

class Project(object):
  def __init__(self,
               manifest,
               name,
               remote,
               gitdir,
               worktree,
               relpath,
               revisionExpr,
               revisionId):
    self.manifest = manifest
    self.name = name
    self.remote = remote
    self.gitdir = gitdir.replace('\\', '/')
    if worktree:
      self.worktree = worktree.replace('\\', '/')
    else:
      self.worktree = None
    self.relpath = relpath
    self.revisionExpr = revisionExpr

    if   revisionId is None \
     and revisionExpr \
     and IsId(revisionExpr):
      self.revisionId = revisionExpr
    else:
      self.revisionId = revisionId

    self.snapshots = {}
    self.copyfiles = []
    self.config = GitConfig.ForRepository(
                    gitdir = self.gitdir,
                    defaults =  self.manifest.globalConfig)

    if self.worktree:
      self.work_git = self._GitGetByExec(self, bare=False)
    else:
      self.work_git = None
    self.bare_git = self._GitGetByExec(self, bare=True)
    self.bare_ref = GitRefs(gitdir)

  @property
  def Exists(self):
    return os.path.isdir(self.gitdir)

  @property
  def CurrentBranch(self):
    """Obtain the name of the currently checked out branch.
       The branch name omits the 'refs/heads/' prefix.
       None is returned if the project is on a detached HEAD.
    """
    b = self.work_git.GetHead()
    if b.startswith(R_HEADS):
      return b[len(R_HEADS):]
    return None

  def IsRebaseInProgress(self):
    w = self.worktree
    g = os.path.join(w, '.git')
    return os.path.exists(os.path.join(g, 'rebase-apply')) \
        or os.path.exists(os.path.join(g, 'rebase-merge')) \
        or os.path.exists(os.path.join(w, '.dotest'))

  def IsDirty(self, consider_untracked=True):
    """Is the working directory modified in some way?
    """
    self.work_git.update_index('-q',
                               '--unmerged',
                               '--ignore-missing',
                               '--refresh')
    if self.work_git.DiffZ('diff-index','-M','--cached',HEAD):
      return True
    if self.work_git.DiffZ('diff-files'):
      return True
    if consider_untracked and self.work_git.LsOthers():
      return True
    return False

  _userident_name = None
  _userident_email = None

  @property
  def UserName(self):
    """Obtain the user's personal name.
    """
    if self._userident_name is None:
      self._LoadUserIdentity()
    return self._userident_name

  @property
  def UserEmail(self):
    """Obtain the user's email address.  This is very likely
       to be their Gerrit login.
    """
    if self._userident_email is None:
      self._LoadUserIdentity()
    return self._userident_email

  def _LoadUserIdentity(self):
      u = self.bare_git.var('GIT_COMMITTER_IDENT')
      m = re.compile("^(.*) <([^>]*)> ").match(u)
      if m:
        self._userident_name = m.group(1)
        self._userident_email = m.group(2)
      else:
        self._userident_name = ''
        self._userident_email = ''

  def GetRemote(self, name):
    """Get the configuration for a single remote.
    """
    return self.config.GetRemote(name)

  def GetBranch(self, name):
    """Get the configuration for a single branch.
    """
    return self.config.GetBranch(name)

  def GetBranches(self):
    """Get all existing local branches.
    """
    current = self.CurrentBranch
    all = self._allrefs
    heads = {}
    pubd = {}

    for name, id in all.iteritems():
      if name.startswith(R_HEADS):
        name = name[len(R_HEADS):]
        b = self.GetBranch(name)
        b.current = name == current
        b.published = None
        b.revision = id
        heads[name] = b

    for name, id in all.iteritems():
      if name.startswith(R_PUB):
        name = name[len(R_PUB):]
        b = heads.get(name)
        if b:
          b.published = id

    return heads


## Status Display ##

  def HasChanges(self):
    """Returns true if there are uncommitted changes.
    """
    self.work_git.update_index('-q',
                               '--unmerged',
                               '--ignore-missing',
                               '--refresh')
    if self.IsRebaseInProgress():
      return True

    if self.work_git.DiffZ('diff-index', '--cached', HEAD):
      return True

    if self.work_git.DiffZ('diff-files'):
      return True

    if self.work_git.LsOthers():
      return True

    return False

  def PrintWorkTreeStatus(self):
    """Prints the status of the repository to stdout.
    """
    if not os.path.isdir(self.worktree):
      print ''
      print 'project %s/' % self.relpath
      print '  missing (run "repo sync")'
      return

    self.work_git.update_index('-q',
                               '--unmerged',
                               '--ignore-missing',
                               '--refresh')
    rb = self.IsRebaseInProgress()
    di = self.work_git.DiffZ('diff-index', '-M', '--cached', HEAD)
    df = self.work_git.DiffZ('diff-files')
    do = self.work_git.LsOthers()
    if not rb and not di and not df and not do:
      return 'CLEAN'

    out = StatusColoring(self.config)
    out.project('project %-40s', self.relpath + '/')

    branch = self.CurrentBranch
    if branch is None:
      out.nobranch('(*** NO BRANCH ***)')
    else:
      out.branch('branch %s', branch)
    out.nl()

    if rb:
      out.important('prior sync failed; rebase still in progress')
      out.nl()

    paths = list()
    paths.extend(di.keys())
    paths.extend(df.keys())
    paths.extend(do)

    paths = list(set(paths))
    paths.sort()

    for p in paths:
      try: i = di[p]
      except KeyError: i = None

      try: f = df[p]
      except KeyError: f = None

      if i: i_status = i.status.upper()
      else: i_status = '-'

      if f: f_status = f.status.lower()
      else: f_status = '-'

      if i and i.src_path:
        line = ' %s%s\t%s => %s (%s%%)' % (i_status, f_status,
                                        i.src_path, p, i.level)
      else:
        line = ' %s%s\t%s' % (i_status, f_status, p)

      if i and not f:
        out.added('%s', line)
      elif (i and f) or (not i and f):
        out.changed('%s', line)
      elif not i and not f:
        out.untracked('%s', line)
      else:
        out.write('%s', line)
      out.nl()
    return 'DIRTY'

  def PrintWorkTreeDiff(self):
    """Prints the status of the repository to stdout.
    """
    out = DiffColoring(self.config)
    cmd = ['diff']
    if out.is_on:
      cmd.append('--color')
    cmd.append(HEAD)
    cmd.append('--')
    p = GitCommand(self,
                   cmd,
                   capture_stdout = True,
                   capture_stderr = True)
    has_diff = False
    for line in p.process.stdout:
      if not has_diff:
        out.nl()
        out.project('project %s/' % self.relpath)
        out.nl()
        has_diff = True
      print line[:-1]
    p.Wait()


## Publish / Upload ##

  def WasPublished(self, branch, all=None):
    """Was the branch published (uploaded) for code review?
       If so, returns the SHA-1 hash of the last published
       state for the branch.
    """
    key = R_PUB + branch
    if all is None:
      try:
        return self.bare_git.rev_parse(key)
      except GitError:
        return None
    else:
      try:
        return all[key]
      except KeyError:
        return None

  def CleanPublishedCache(self, all=None):
    """Prunes any stale published refs.
    """
    if all is None:
      all = self._allrefs
    heads = set()
    canrm = {}
    for name, id in all.iteritems():
      if name.startswith(R_HEADS):
        heads.add(name)
      elif name.startswith(R_PUB):
        canrm[name] = id

    for name, id in canrm.iteritems():
      n = name[len(R_PUB):]
      if R_HEADS + n not in heads:
        self.bare_git.DeleteRef(name, id)

  def GetUploadableBranches(self):
    """List any branches which can be uploaded for review.
    """
    heads = {}
    pubed = {}

    for name, id in self._allrefs.iteritems():
      if name.startswith(R_HEADS):
        heads[name[len(R_HEADS):]] = id
      elif name.startswith(R_PUB):
        pubed[name[len(R_PUB):]] = id

    ready = []
    for branch, id in heads.iteritems():
      if branch in pubed and pubed[branch] == id:
        continue

      rb = self.GetUploadableBranch(branch)
      if rb:
        ready.append(rb)
    return ready

  def GetUploadableBranch(self, branch_name):
    """Get a single uploadable branch, or None.
    """
    branch = self.GetBranch(branch_name)
    base = branch.LocalMerge
    if branch.LocalMerge:
      rb = ReviewableBranch(self, branch, base)
      if rb.commits:
        return rb
    return None

  def UploadForReview(self, branch=None,
                      people=([],[]),
                      auto_topic=False):
    """Uploads the named branch for code review.
    """
    if branch is None:
      branch = self.CurrentBranch
    if branch is None:
      raise GitError('not currently on a branch')

    branch = self.GetBranch(branch)
    if not branch.LocalMerge:
      raise GitError('branch %s does not track a remote' % branch.name)
    if not branch.remote.review:
      raise GitError('remote %s has no review url' % branch.remote.name)

    dest_branch = branch.merge
    if not dest_branch.startswith(R_HEADS):
      dest_branch = R_HEADS + dest_branch

    if not branch.remote.projectname:
      branch.remote.projectname = self.name
      branch.remote.Save()

    if branch.remote.ReviewProtocol == 'ssh':
      if dest_branch.startswith(R_HEADS):
        dest_branch = dest_branch[len(R_HEADS):]

      rp = ['gerrit receive-pack']
      for e in people[0]:
        rp.append('--reviewer=%s' % sq(e))
      for e in people[1]:
        rp.append('--cc=%s' % sq(e))

      ref_spec = '%s:refs/for/%s' % (R_HEADS + branch.name, dest_branch)
      if auto_topic:
        ref_spec = ref_spec + '/' + branch.name

      cmd = ['push']
      cmd.append('--receive-pack=%s' % " ".join(rp))
      cmd.append(branch.remote.SshReviewUrl(self.UserEmail))
      cmd.append(ref_spec)

      if GitCommand(self, cmd, bare = True).Wait() != 0:
        raise UploadError('Upload failed')

    else:
        raise UploadError('Unsupported protocol %s' \
          % branch.remote.review)

    msg = "posted to %s for %s" % (branch.remote.review, dest_branch)
    self.bare_git.UpdateRef(R_PUB + branch.name,
                            R_HEADS + branch.name,
                            message = msg)


## Sync ##

  def Sync_NetworkHalf(self, quiet=False):
    """Perform only the network IO portion of the sync process.
       Local working directory/branch state is not affected.
    """
    is_new = not self.Exists
    if is_new:
      if not quiet:
        print >>sys.stderr
        print >>sys.stderr, 'Initializing project %s ...' % self.name
      self._InitGitDir()

    self._InitRemote()
    if not self._RemoteFetch(initial=is_new, quiet=quiet):
      return False

    #Check that the requested ref was found after fetch
    #
    try:
      self.GetRevisionId()
    except ManifestInvalidRevisionError:
      # if the ref is a tag. We can try fetching
      # the tag manually as a last resort
      #
      rev = self.revisionExpr
      if rev.startswith(R_TAGS):
        self._RemoteFetch(None, rev[len(R_TAGS):], quiet=quiet)

    if self.worktree:
      self.manifest.SetMRefs(self)
    else:
      self._InitMirrorHead()
      try:
        os.remove(os.path.join(self.gitdir, 'FETCH_HEAD'))
      except OSError:
        pass
    return True

  def PostRepoUpgrade(self):
    self._InitHooks()

  def _CopyFiles(self):
    for file in self.copyfiles:
      file._Copy()

  def GetRevisionId(self, all=None):
    if self.revisionId:
      return self.revisionId

    rem = self.GetRemote(self.remote.name)
    rev = rem.ToLocal(self.revisionExpr)

    if all is not None and rev in all:
      return all[rev]

    try:
      return self.bare_git.rev_parse('--verify', '%s^0' % rev)
    except GitError:
      raise ManifestInvalidRevisionError(
        'revision %s in %s not found' % (self.revisionExpr,
                                         self.name))

  def Sync_LocalHalf(self, syncbuf):
    """Perform only the local IO portion of the sync process.
       Network access is not required.
    """
    self._InitWorkTree()
    all = self.bare_ref.all
    self.CleanPublishedCache(all)

    revid = self.GetRevisionId(all)
    head = self.work_git.GetHead()
    if head.startswith(R_HEADS):
      branch = head[len(R_HEADS):]
      try:
        head = all[head]
      except KeyError:
        head = None
    else:
      branch = None

    if branch is None or syncbuf.detach_head:
      # Currently on a detached HEAD.  The user is assumed to
      # not have any local modifications worth worrying about.
      #
      if self.IsRebaseInProgress():
        syncbuf.fail(self, _PriorSyncFailedError())
        return

      if head == revid:
        # No changes; don't do anything further.
        #
        return

      lost = self._revlist(not_rev(revid), HEAD)
      if lost:
        syncbuf.info(self, "discarding %d commits", len(lost))
      try:
        self._Checkout(revid, quiet=True)
      except GitError, e:
        syncbuf.fail(self, e)
        return
      self._CopyFiles()
      return

    if head == revid:
      # No changes; don't do anything further.
      #
      return

    branch = self.GetBranch(branch)

    if not branch.LocalMerge:
      # The current branch has no tracking configuration.
      # Jump off it to a deatched HEAD.
      #
      syncbuf.info(self,
                   "leaving %s; does not track upstream",
                   branch.name)
      try:
        self._Checkout(revid, quiet=True)
      except GitError, e:
        syncbuf.fail(self, e)
        return
      self._CopyFiles()
      return

    upstream_gain = self._revlist(not_rev(HEAD), revid)
    pub = self.WasPublished(branch.name, all)
    if pub:
      not_merged = self._revlist(not_rev(revid), pub)
      if not_merged:
        if upstream_gain:
          # The user has published this branch and some of those
          # commits are not yet merged upstream.  We do not want
          # to rewrite the published commits so we punt.
          #
          syncbuf.fail(self,
                       "branch %s is published (but not merged) and is now %d commits behind"
                       % (branch.name, len(upstream_gain)))
        return
      elif pub == head:
        # All published commits are merged, and thus we are a
        # strict subset.  We can fast-forward safely.
        #
        def _doff():
          self._FastForward(revid)
          self._CopyFiles()
        syncbuf.later1(self, _doff)
        return

    # Examine the local commits not in the remote.  Find the
    # last one attributed to this user, if any.
    #
    local_changes = self._revlist(not_rev(revid), HEAD, format='%H %ce')
    last_mine = None
    cnt_mine = 0
    for commit in local_changes:
      commit_id, committer_email = commit.split(' ', 1)
      if committer_email == self.UserEmail:
        last_mine = commit_id
        cnt_mine += 1

    if not upstream_gain and cnt_mine == len(local_changes):
      return

    if self.IsDirty(consider_untracked=False):
      syncbuf.fail(self, _DirtyError())
      return

    # If the upstream switched on us, warn the user.
    #
    if branch.merge != self.revisionExpr:
      if branch.merge and self.revisionExpr:
        syncbuf.info(self,
                     'manifest switched %s...%s',
                     branch.merge,
                     self.revisionExpr)
      elif branch.merge:
        syncbuf.info(self,
                     'manifest no longer tracks %s',
                     branch.merge)

    if cnt_mine < len(local_changes):
      # Upstream rebased.  Not everything in HEAD
      # was created by this user.
      #
      syncbuf.info(self,
                   "discarding %d commits removed from upstream",
                   len(local_changes) - cnt_mine)

    branch.remote = self.GetRemote(self.remote.name)
    branch.merge = self.revisionExpr
    branch.Save()

    if cnt_mine > 0:
      def _dorebase():
        self._Rebase(upstream = '%s^1' % last_mine, onto = revid)
        self._CopyFiles()
      syncbuf.later2(self, _dorebase)
    elif local_changes:
      try:
        self._ResetHard(revid)
        self._CopyFiles()
      except GitError, e:
        syncbuf.fail(self, e)
        return
    else:
      def _doff():
        self._FastForward(revid)
        self._CopyFiles()
      syncbuf.later1(self, _doff)

  def AddCopyFile(self, src, dest, absdest):
    # dest should already be an absolute path, but src is project relative
    # make src an absolute path
    abssrc = os.path.join(self.worktree, src)
    self.copyfiles.append(_CopyFile(src, dest, abssrc, absdest))

  def DownloadPatchSet(self, change_id, patch_id):
    """Download a single patch set of a single change to FETCH_HEAD.
    """
    remote = self.GetRemote(self.remote.name)

    cmd = ['fetch', remote.name]
    cmd.append('refs/changes/%2.2d/%d/%d' \
               % (change_id % 100, change_id, patch_id))
    cmd.extend(map(lambda x: str(x), remote.fetch))
    if GitCommand(self, cmd, bare=True).Wait() != 0:
      return None
    return DownloadedChange(self,
                            self.GetRevisionId(),
                            change_id,
                            patch_id,
                            self.bare_git.rev_parse('FETCH_HEAD'))


## Branch Management ##

  def StartBranch(self, name):
    """Create a new branch off the manifest's revision.
    """
    head = self.work_git.GetHead()
    if head == (R_HEADS + name):
      return True

    all = self.bare_ref.all
    if (R_HEADS + name) in all:
      return GitCommand(self,
                        ['checkout', name, '--'],
                        capture_stdout = True,
                        capture_stderr = True).Wait() == 0

    branch = self.GetBranch(name)
    branch.remote = self.GetRemote(self.remote.name)
    branch.merge = self.revisionExpr
    revid = self.GetRevisionId(all)

    if head.startswith(R_HEADS):
      try:
        head = all[head]
      except KeyError:
        head = None

    if revid and head and revid == head:
      ref = os.path.join(self.gitdir, R_HEADS + name)
      try:
        os.makedirs(os.path.dirname(ref))
      except OSError:
        pass
      _lwrite(ref, '%s\n' % revid)
      _lwrite(os.path.join(self.worktree, '.git', HEAD),
              'ref: %s%s\n' % (R_HEADS, name))
      branch.Save()
      return True

    if GitCommand(self,
                  ['checkout', '-b', branch.name, revid],
                  capture_stdout = True,
                  capture_stderr = True).Wait() == 0:
      branch.Save()
      return True
    return False

  def CheckoutBranch(self, name):
    """Checkout a local topic branch.
    """
    rev = R_HEADS + name
    head = self.work_git.GetHead()
    if head == rev:
      # Already on the branch
      #
      return True

    all = self.bare_ref.all
    try:
      revid = all[rev]
    except KeyError:
      # Branch does not exist in this project
      #
      return False

    if head.startswith(R_HEADS):
      try:
        head = all[head]
      except KeyError:
        head = None

    if head == revid:
      # Same revision; just update HEAD to point to the new
      # target branch, but otherwise take no other action.
      #
      _lwrite(os.path.join(self.worktree, '.git', HEAD),
              'ref: %s%s\n' % (R_HEADS, name))
      return True

    return GitCommand(self,
                      ['checkout', name, '--'],
                      capture_stdout = True,
                      capture_stderr = True).Wait() == 0

  def AbandonBranch(self, name):
    """Destroy a local topic branch.
    """
    rev = R_HEADS + name
    all = self.bare_ref.all
    if rev not in all:
      # Doesn't exist; assume already abandoned.
      #
      return True

    head = self.work_git.GetHead()
    if head == rev:
      # We can't destroy the branch while we are sitting
      # on it.  Switch to a detached HEAD.
      #
      head = all[head]

      revid = self.GetRevisionId(all)
      if head == revid:
        _lwrite(os.path.join(self.worktree, '.git', HEAD),
                '%s\n' % revid)
      else:
        self._Checkout(revid, quiet=True)

    return GitCommand(self,
                      ['branch', '-D', name],
                      capture_stdout = True,
                      capture_stderr = True).Wait() == 0

  def PruneHeads(self):
    """Prune any topic branches already merged into upstream.
    """
    cb = self.CurrentBranch
    kill = []
    left = self._allrefs
    for name in left.keys():
      if name.startswith(R_HEADS):
        name = name[len(R_HEADS):]
        if cb is None or name != cb:
          kill.append(name)

    rev = self.GetRevisionId(left)
    if cb is not None \
       and not self._revlist(HEAD + '...' + rev) \
       and not self.IsDirty(consider_untracked = False):
      self.work_git.DetachHead(HEAD)
      kill.append(cb)

    if kill:
      old = self.bare_git.GetHead()
      if old is None:
        old = 'refs/heads/please_never_use_this_as_a_branch_name'

      try:
        self.bare_git.DetachHead(rev)

        b = ['branch', '-d']
        b.extend(kill)
        b = GitCommand(self, b, bare=True,
                       capture_stdout=True,
                       capture_stderr=True)
        b.Wait()
      finally:
        self.bare_git.SetHead(old)
        left = self._allrefs

      for branch in kill:
        if (R_HEADS + branch) not in left:
          self.CleanPublishedCache()
          break

    if cb and cb not in kill:
      kill.append(cb)
    kill.sort()

    kept = []
    for branch in kill:
      if (R_HEADS + branch) in left:
        branch = self.GetBranch(branch)
        base = branch.LocalMerge
        if not base:
          base = rev
        kept.append(ReviewableBranch(self, branch, base))
    return kept


## Direct Git Commands ##

  def _RemoteFetch(self, name=None, tag=None,
                   initial=False,
                   quiet=False):
    if not name:
      name = self.remote.name

    ssh_proxy = False
    if self.GetRemote(name).PreConnectFetch():
      ssh_proxy = True

    if initial:
      alt = os.path.join(self.gitdir, 'objects/info/alternates')
      try:
        fd = open(alt, 'rb')
        try:
          ref_dir = fd.readline()
          if ref_dir and ref_dir.endswith('\n'):
            ref_dir = ref_dir[:-1]
        finally:
          fd.close()
      except IOError, e:
        ref_dir = None

      if ref_dir and 'objects' == os.path.basename(ref_dir):
        ref_dir = os.path.dirname(ref_dir)
        packed_refs = os.path.join(self.gitdir, 'packed-refs')
        remote = self.GetRemote(name)

        all = self.bare_ref.all
        ids = set(all.values())
        tmp = set()

        for r, id in GitRefs(ref_dir).all.iteritems():
          if r not in all:
            if r.startswith(R_TAGS) or remote.WritesTo(r):
              all[r] = id
              ids.add(id)
              continue

          if id in ids:
            continue

          r = 'refs/_alt/%s' % id
          all[r] = id
          ids.add(id)
          tmp.add(r)

        ref_names = list(all.keys())
        ref_names.sort()

        tmp_packed = ''
        old_packed = ''

        for r in ref_names:
          line = '%s %s\n' % (all[r], r)
          tmp_packed += line
          if r not in tmp:
            old_packed += line

        _lwrite(packed_refs, tmp_packed)

      else:
        ref_dir = None

    cmd = ['fetch']
    if quiet:
      cmd.append('--quiet')
    if not self.worktree:
      cmd.append('--update-head-ok')
    cmd.append(name)
    if tag is not None:
      cmd.append('tag')
      cmd.append(tag)

    ok = GitCommand(self,
                    cmd,
                    bare = True,
                    ssh_proxy = ssh_proxy).Wait() == 0

    if initial:
      if ref_dir:
        if old_packed != '':
          _lwrite(packed_refs, old_packed)
        else:
          os.remove(packed_refs)
      self.bare_git.pack_refs('--all', '--prune')

    return ok

  def _Checkout(self, rev, quiet=False):
    cmd = ['checkout']
    if quiet:
      cmd.append('-q')
    cmd.append(rev)
    cmd.append('--')
    if GitCommand(self, cmd).Wait() != 0:
      if self._allrefs:
        raise GitError('%s checkout %s ' % (self.name, rev))

  def _ResetHard(self, rev, quiet=True):
    cmd = ['reset', '--hard']
    if quiet:
      cmd.append('-q')
    cmd.append(rev)
    if GitCommand(self, cmd).Wait() != 0:
      raise GitError('%s reset --hard %s ' % (self.name, rev))

  def _Rebase(self, upstream, onto = None):
    cmd = ['rebase']
    if onto is not None:
      cmd.extend(['--onto', onto])
    cmd.append(upstream)
    if GitCommand(self, cmd).Wait() != 0:
      raise GitError('%s rebase %s ' % (self.name, upstream))

  def _FastForward(self, head):
    cmd = ['merge', head]
    if GitCommand(self, cmd).Wait() != 0:
      raise GitError('%s merge %s ' % (self.name, head))

  def _InitGitDir(self):
    if not os.path.exists(self.gitdir):
      os.makedirs(self.gitdir)
      self.bare_git.init()

      mp = self.manifest.manifestProject
      ref_dir = mp.config.GetString('repo.reference')

      if ref_dir:
        mirror_git = os.path.join(ref_dir, self.name + '.git')
        repo_git = os.path.join(ref_dir, '.repo', 'projects',
                                self.relpath + '.git')

        if os.path.exists(mirror_git):
          ref_dir = mirror_git

        elif os.path.exists(repo_git):
          ref_dir = repo_git

        else:
          ref_dir = None

        if ref_dir:
          _lwrite(os.path.join(self.gitdir, 'objects/info/alternates'),
                  os.path.join(ref_dir, 'objects') + '\n')

      if self.manifest.IsMirror:
        self.config.SetString('core.bare', 'true')
      else:
        self.config.SetString('core.bare', None)

      hooks = self._gitdir_path('hooks')
      try:
        to_rm = os.listdir(hooks)
      except OSError:
        to_rm = []
      for old_hook in to_rm:
        os.remove(os.path.join(hooks, old_hook))
      self._InitHooks()

      m = self.manifest.manifestProject.config
      for key in ['user.name', 'user.email']:
        if m.Has(key, include_defaults = False):
          self.config.SetString(key, m.GetString(key))

  def _InitHooks(self):
    hooks = self._gitdir_path('hooks')
    if not os.path.exists(hooks):
      os.makedirs(hooks)
    for stock_hook in repo_hooks():
      name = os.path.basename(stock_hook)

      if name in ('commit-msg') and not self.remote.review:
        # Don't install a Gerrit Code Review hook if this
        # project does not appear to use it for reviews.
        #
        continue

      dst = os.path.join(hooks, name)
      if os.path.islink(dst):
        continue
      if os.path.exists(dst):
        if filecmp.cmp(stock_hook, dst, shallow=False):
          os.remove(dst)
        else:
          _error("%s: Not replacing %s hook", self.relpath, name)
          continue
      try:
        os.symlink(relpath(stock_hook, dst), dst)
      except OSError, e:
        if e.errno == errno.EPERM:
          raise GitError('filesystem must support symlinks')
        else:
          raise

  def _InitRemote(self):
    if self.remote.url:
      remote = self.GetRemote(self.remote.name)
      remote.url = self.remote.url
      remote.review = self.remote.review
      remote.projectname = self.name

      if self.worktree:
        remote.ResetFetch(mirror=False)
      else:
        remote.ResetFetch(mirror=True)
      remote.Save()

  def _InitMirrorHead(self):
    self._InitAnyMRef(HEAD)

  def _InitAnyMRef(self, ref):
    cur = self.bare_ref.symref(ref)

    if self.revisionId:
      if cur != '' or self.bare_ref.get(ref) != self.revisionId:
        msg = 'manifest set to %s' % self.revisionId
        dst = self.revisionId + '^0'
        self.bare_git.UpdateRef(ref, dst, message = msg, detach = True)
    else:
      remote = self.GetRemote(self.remote.name)
      dst = remote.ToLocal(self.revisionExpr)
      if cur != dst:
        msg = 'manifest set to %s' % self.revisionExpr
        self.bare_git.symbolic_ref('-m', msg, ref, dst)

  def _LinkWorkTree(self, relink=False):
    dotgit = os.path.join(self.worktree, '.git')
    if not relink:
      os.makedirs(dotgit)

    for name in ['config',
                 'description',
                 'hooks',
                 'info',
                 'logs',
                 'objects',
                 'packed-refs',
                 'refs',
                 'rr-cache',
                 'svn']:
      try:
        src = os.path.join(self.gitdir, name)
        dst = os.path.join(dotgit, name)
        if relink:
          os.remove(dst)
        if os.path.islink(dst) or not os.path.exists(dst):
          os.symlink(relpath(src, dst), dst)
        else:
          raise GitError('cannot overwrite a local work tree')
      except OSError, e:
        if e.errno == errno.EPERM:
          raise GitError('filesystem must support symlinks')
        else:
          raise

  def _InitWorkTree(self):
    dotgit = os.path.join(self.worktree, '.git')
    if not os.path.exists(dotgit):
      self._LinkWorkTree()

      _lwrite(os.path.join(dotgit, HEAD), '%s\n' % self.GetRevisionId())

      cmd = ['read-tree', '--reset', '-u']
      cmd.append('-v')
      cmd.append(HEAD)
      if GitCommand(self, cmd).Wait() != 0:
        raise GitError("cannot initialize work tree")
      self._CopyFiles()

  def _gitdir_path(self, path):
    return os.path.join(self.gitdir, path)

  def _revlist(self, *args, **kw):
    a = []
    a.extend(args)
    a.append('--')
    return self.work_git.rev_list(*a, **kw)

  @property
  def _allrefs(self):
    return self.bare_ref.all

  class _GitGetByExec(object):
    def __init__(self, project, bare):
      self._project = project
      self._bare = bare

    def LsOthers(self):
      p = GitCommand(self._project,
                     ['ls-files',
                      '-z',
                      '--others',
                      '--exclude-standard'],
                     bare = False,
                     capture_stdout = True,
                     capture_stderr = True)
      if p.Wait() == 0:
        out = p.stdout
        if out:
          return out[:-1].split("\0")
      return []

    def DiffZ(self, name, *args):
      cmd = [name]
      cmd.append('-z')
      cmd.extend(args)
      p = GitCommand(self._project,
                     cmd,
                     bare = False,
                     capture_stdout = True,
                     capture_stderr = True)
      try:
        out = p.process.stdout.read()
        r = {}
        if out:
          out = iter(out[:-1].split('\0'))
          while out:
            try:
              info = out.next()
              path = out.next()
            except StopIteration:
              break

            class _Info(object):
              def __init__(self, path, omode, nmode, oid, nid, state):
                self.path = path
                self.src_path = None
                self.old_mode = omode
                self.new_mode = nmode
                self.old_id = oid
                self.new_id = nid

                if len(state) == 1:
                  self.status = state
                  self.level = None
                else:
                  self.status = state[:1]
                  self.level = state[1:]
                  while self.level.startswith('0'):
                    self.level = self.level[1:]

            info = info[1:].split(' ')
            info =_Info(path, *info)
            if info.status in ('R', 'C'):
              info.src_path = info.path
              info.path = out.next()
            r[info.path] = info
        return r
      finally:
        p.Wait()

    def GetHead(self):
      if self._bare:
        path = os.path.join(self._project.gitdir, HEAD)
      else:
        path = os.path.join(self._project.worktree, '.git', HEAD)
      fd = open(path, 'rb')
      try:
        line = fd.read()
      finally:
        fd.close()
      if line.startswith('ref: '):
        return line[5:-1]
      return line[:-1]

    def SetHead(self, ref, message=None):
      cmdv = []
      if message is not None:
        cmdv.extend(['-m', message])
      cmdv.append(HEAD)
      cmdv.append(ref)
      self.symbolic_ref(*cmdv)

    def DetachHead(self, new, message=None):
      cmdv = ['--no-deref']
      if message is not None:
        cmdv.extend(['-m', message])
      cmdv.append(HEAD)
      cmdv.append(new)
      self.update_ref(*cmdv)

    def UpdateRef(self, name, new, old=None,
                  message=None,
                  detach=False):
      cmdv = []
      if message is not None:
        cmdv.extend(['-m', message])
      if detach:
        cmdv.append('--no-deref')
      cmdv.append(name)
      cmdv.append(new)
      if old is not None:
        cmdv.append(old)
      self.update_ref(*cmdv)

    def DeleteRef(self, name, old=None):
      if not old:
        old = self.rev_parse(name)
      self.update_ref('-d', name, old)
      self._project.bare_ref.deleted(name)

    def rev_list(self, *args, **kw):
      if 'format' in kw:
        cmdv = ['log', '--pretty=format:%s' % kw['format']]
      else:
        cmdv = ['rev-list']
      cmdv.extend(args)
      p = GitCommand(self._project,
                     cmdv,
                     bare = self._bare,
                     capture_stdout = True,
                     capture_stderr = True)
      r = []
      for line in p.process.stdout:
        if line[-1] == '\n':
          line = line[:-1]
        r.append(line)
      if p.Wait() != 0:
        raise GitError('%s rev-list %s: %s' % (
                       self._project.name,
                       str(args),
                       p.stderr))
      return r

    def __getattr__(self, name):
      name = name.replace('_', '-')
      def runner(*args):
        cmdv = [name]
        cmdv.extend(args)
        p = GitCommand(self._project,
                       cmdv,
                       bare = self._bare,
                       capture_stdout = True,
                       capture_stderr = True)
        if p.Wait() != 0:
          raise GitError('%s %s: %s' % (
                         self._project.name,
                         name,
                         p.stderr))
        r = p.stdout
        if r.endswith('\n') and r.index('\n') == len(r) - 1:
          return r[:-1]
        return r
      return runner


class _PriorSyncFailedError(Exception):
  def __str__(self):
    return 'prior sync failed; rebase still in progress'

class _DirtyError(Exception):
  def __str__(self):
    return 'contains uncommitted changes'

class _InfoMessage(object):
  def __init__(self, project, text):
    self.project = project
    self.text = text

  def Print(self, syncbuf):
    syncbuf.out.info('%s/: %s', self.project.relpath, self.text)
    syncbuf.out.nl()

class _Failure(object):
  def __init__(self, project, why):
    self.project = project
    self.why = why

  def Print(self, syncbuf):
    syncbuf.out.fail('error: %s/: %s',
                     self.project.relpath,
                     str(self.why))
    syncbuf.out.nl()

class _Later(object):
  def __init__(self, project, action):
    self.project = project
    self.action = action

  def Run(self, syncbuf):
    out = syncbuf.out
    out.project('project %s/', self.project.relpath)
    out.nl()
    try:
      self.action()
      out.nl()
      return True
    except GitError, e:
      out.nl()
      return False

class _SyncColoring(Coloring):
  def __init__(self, config):
    Coloring.__init__(self, config, 'reposync')
    self.project   = self.printer('header', attr = 'bold')
    self.info      = self.printer('info')
    self.fail      = self.printer('fail', fg='red')

class SyncBuffer(object):
  def __init__(self, config, detach_head=False):
    self._messages = []
    self._failures = []
    self._later_queue1 = []
    self._later_queue2 = []

    self.out = _SyncColoring(config)
    self.out.redirect(sys.stderr)

    self.detach_head = detach_head
    self.clean = True

  def info(self, project, fmt, *args):
    self._messages.append(_InfoMessage(project, fmt % args))

  def fail(self, project, err=None):
    self._failures.append(_Failure(project, err))
    self.clean = False

  def later1(self, project, what):
    self._later_queue1.append(_Later(project, what))

  def later2(self, project, what):
    self._later_queue2.append(_Later(project, what))

  def Finish(self):
    self._PrintMessages()
    self._RunLater()
    self._PrintMessages()
    return self.clean

  def _RunLater(self):
    for q in ['_later_queue1', '_later_queue2']:
      if not self._RunQueue(q):
        return

  def _RunQueue(self, queue):
    for m in getattr(self, queue):
      if not m.Run(self):
        self.clean = False
        return False
    setattr(self, queue, [])
    return True

  def _PrintMessages(self):
    for m in self._messages:
      m.Print(self)
    for m in self._failures:
      m.Print(self)

    self._messages = []
    self._failures = []


class MetaProject(Project):
  """A special project housed under .repo.
  """
  def __init__(self, manifest, name, gitdir, worktree, relpath=None):
    repodir = manifest.repodir
    if relpath is None:
      relpath = '.repo/%s' % name
    Project.__init__(self,
                     manifest = manifest,
                     name = name,
                     gitdir = gitdir,
                     worktree = worktree,
                     remote = RemoteSpec('origin'),
                     relpath = relpath,
                     revisionExpr = 'refs/heads/master',
                     revisionId = None)

  def PreSync(self):
    if self.Exists:
      cb = self.CurrentBranch
      if cb:
        cb = self.GetBranch(cb)
        if cb.merge:
          self.revisionExpr = cb.merge
          self.revisionId = None
        if cb.remote and cb.remote.name:
          self.remote.name = cb.remote.name

  @property
  def LastFetch(self):
    try:
      fh = os.path.join(self.gitdir, 'FETCH_HEAD')
      return os.path.getmtime(fh)
    except OSError:
      return 0

  @property
  def HasChanges(self):
    """Has the remote received new commits not yet checked out?
    """
    if not self.remote or not self.revisionExpr:
      return False

    all = self.bare_ref.all
    revid = self.GetRevisionId(all)
    head = self.work_git.GetHead()
    if head.startswith(R_HEADS):
      try:
        head = all[head]
      except KeyError:
        head = None

    if revid == head:
      return False
    elif self._revlist(not_rev(HEAD), revid):
      return True
    return False

########NEW FILE########
__FILENAME__ = abandon
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from command import Command
from git_command import git
from progress import Progress

class Abandon(Command):
  common = True
  helpSummary = "Permanently abandon a development branch"
  helpUsage = """
%prog <branchname> [<project>...]

This subcommand permanently abandons a development branch by
deleting it (and all its history) from your local repository.

It is equivalent to "git branch -D <branchname>".
"""

  def Execute(self, opt, args):
    if not args:
      self.Usage()

    nb = args[0]
    if not git.check_ref_format('heads/%s' % nb):
      print >>sys.stderr, "error: '%s' is not a valid name" % nb
      sys.exit(1)

    nb = args[0]
    err = []
    all = self.GetProjects(args[1:])

    pm = Progress('Abandon %s' % nb, len(all))
    for project in all:
      pm.update()
      if not project.AbandonBranch(nb):
        err.append(project)
    pm.end()

    if err:
      if len(err) == len(all):
        print >>sys.stderr, 'error: no project has branch %s' % nb
      else:
        for p in err:
          print >>sys.stderr,\
            "error: %s/: cannot abandon %s" \
            % (p.relpath, nb)
      sys.exit(1)

########NEW FILE########
__FILENAME__ = branches
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from color import Coloring
from command import Command

class BranchColoring(Coloring):
  def __init__(self, config):
    Coloring.__init__(self, config, 'branch')
    self.current = self.printer('current', fg='green')
    self.local   = self.printer('local')
    self.notinproject = self.printer('notinproject', fg='red')

class BranchInfo(object):
  def __init__(self, name):
    self.name = name
    self.current = 0
    self.published = 0
    self.published_equal = 0
    self.projects = []

  def add(self, b):
    if b.current:
      self.current += 1
    if b.published:
      self.published += 1
    if b.revision == b.published:
      self.published_equal += 1
    self.projects.append(b)

  @property
  def IsCurrent(self):
    return self.current > 0

  @property
  def IsPublished(self):
    return self.published > 0

  @property
  def IsPublishedEqual(self):
    return self.published_equal == len(self.projects)


class Branches(Command):
  common = True
  helpSummary = "View current topic branches"
  helpUsage = """
%prog [<project>...]

Summarizes the currently available topic branches.

Branch Display
--------------

The branch display output by this command is organized into four
columns of information; for example:

 *P nocolor                   | in repo
    repo2                     |

The first column contains a * if the branch is the currently
checked out branch in any of the specified projects, or a blank
if no project has the branch checked out.

The second column contains either blank, p or P, depending upon
the upload status of the branch.

 (blank): branch not yet published by repo upload
       P: all commits were published by repo upload
       p: only some commits were published by repo upload

The third column contains the branch name.

The fourth column (after the | separator) lists the projects that
the branch appears in, or does not appear in.  If no project list
is shown, then the branch appears in all projects.

"""

  def Execute(self, opt, args):
    projects = self.GetProjects(args)
    out = BranchColoring(self.manifest.manifestProject.config)
    all = {}
    project_cnt = len(projects)

    for project in projects:
      for name, b in project.GetBranches().iteritems():
        b.project = project
        if name not in all:
          all[name] = BranchInfo(name)
        all[name].add(b)

    names = all.keys()
    names.sort()

    if not names:
      print >>sys.stderr, '   (no branches)'
      return

    width = 25
    for name in names:
      if width < len(name):
        width = len(name)

    for name in names:
      i = all[name]
      in_cnt = len(i.projects)

      if i.IsCurrent:
        current = '*'
        hdr = out.current
      else:
        current = ' '
        hdr = out.local

      if i.IsPublishedEqual:
        published = 'P'
      elif i.IsPublished:
        published = 'p'
      else:
        published = ' '

      hdr('%c%c %-*s' % (current, published, width, name))
      out.write(' |')

      if in_cnt < project_cnt:
        fmt = out.write
        paths = []
        if in_cnt < project_cnt - in_cnt: 
          type = 'in'
          for b in i.projects:
            paths.append(b.project.relpath)
        else:
          fmt = out.notinproject
          type = 'not in'
          have = set()
          for b in i.projects:
            have.add(b.project)
          for p in projects:
            if not p in have:
              paths.append(p.relpath)

        s = ' %s %s' % (type, ', '.join(paths))
        if width + 7 + len(s) < 80:
          fmt(s)
        else:
          fmt(' %s:' % type)
          for p in paths:
            out.nl()
            fmt(width*' ' + '          %s' % p)
      else:
        out.write(' in all projects')
      out.nl()

########NEW FILE########
__FILENAME__ = checkout
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from command import Command
from progress import Progress

class Checkout(Command):
  common = True
  helpSummary = "Checkout a branch for development"
  helpUsage = """
%prog <branchname> [<project>...]
"""
  helpDescription = """
The '%prog' command checks out an existing branch that was previously
created by 'repo start'.

The command is equivalent to:

  repo forall [<project>...] -c git checkout <branchname>
"""

  def Execute(self, opt, args):
    if not args:
      self.Usage()

    nb = args[0]
    err = []
    all = self.GetProjects(args[1:])

    pm = Progress('Checkout %s' % nb, len(all))
    for project in all:
      pm.update()
      if not project.CheckoutBranch(nb):
        err.append(project)
    pm.end()

    if err:
      if len(err) == len(all):
        print >>sys.stderr, 'error: no project has branch %s' % nb
      else:
        for p in err:
          print >>sys.stderr,\
            "error: %s/: cannot checkout %s" \
            % (p.relpath, nb)
      sys.exit(1)

########NEW FILE########
__FILENAME__ = diff
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from command import PagedCommand

class Diff(PagedCommand):
  common = True
  helpSummary = "Show changes between commit and working tree"
  helpUsage = """
%prog [<project>...]
"""

  def Execute(self, opt, args):
    for project in self.GetProjects(args):
      project.PrintWorkTreeDiff()

########NEW FILE########
__FILENAME__ = download
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import sys

from command import Command

CHANGE_RE = re.compile(r'^([1-9][0-9]*)(?:[/\.-]([1-9][0-9]*))?$')

class Download(Command):
  common = True
  helpSummary = "Download and checkout a change"
  helpUsage = """
%prog {project change[/patchset]}...
"""
  helpDescription = """
The '%prog' command downloads a change from the review system and
makes it available in your project's local working directory.
"""

  def _Options(self, p):
    pass

  def _ParseChangeIds(self, args):
    if not args:
      self.Usage()

    to_get = []
    project = None

    for a in args:
      m = CHANGE_RE.match(a)
      if m:
        if not project:
          self.Usage()
        chg_id = int(m.group(1))
        if m.group(2):
          ps_id = int(m.group(2))
        else:
          ps_id = 1
        to_get.append((project, chg_id, ps_id))
      else:
        project = self.GetProjects([a])[0]
    return to_get

  def Execute(self, opt, args):
    for project, change_id, ps_id in self._ParseChangeIds(args):
      dl = project.DownloadPatchSet(change_id, ps_id)
      if not dl:
        print >>sys.stderr, \
          '[%s] change %d/%d not found' \
          % (project.name, change_id, ps_id)
        sys.exit(1)

      if not dl.commits:
        print >>sys.stderr, \
          '[%s] change %d/%d has already been merged' \
          % (project.name, change_id, ps_id)
        continue

      if len(dl.commits) > 1:
        print >>sys.stderr, \
          '[%s] %d/%d depends on %d unmerged changes:' \
          % (project.name, change_id, ps_id, len(dl.commits))
        for c in dl.commits:
          print >>sys.stderr, '  %s' % (c)
      project._Checkout(dl.commit)

########NEW FILE########
__FILENAME__ = forall
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import fcntl
import re
import os
import select
import sys
import subprocess

from color import Coloring
from command import Command, MirrorSafeCommand

_CAN_COLOR = [
  'branch',
  'diff',
  'grep',
  'log',
]

class ForallColoring(Coloring):
  def __init__(self, config):
    Coloring.__init__(self, config, 'forall')
    self.project = self.printer('project', attr='bold')


class Forall(Command, MirrorSafeCommand):
  common = False
  helpSummary = "Run a shell command in each project"
  helpUsage = """
%prog [<project>...] -c <command> [<arg>...]
"""
  helpDescription = """
Executes the same shell command in each project.

Output Formatting
-----------------

The -p option causes '%prog' to bind pipes to the command's stdin,
stdout and stderr streams, and pipe all output into a continuous
stream that is displayed in a single pager session.  Project headings
are inserted before the output of each command is displayed.  If the
command produces no output in a project, no heading is displayed.

The formatting convention used by -p is very suitable for some
types of searching, e.g. `repo forall -p -c git log -SFoo` will
print all commits that add or remove references to Foo.

The -v option causes '%prog' to display stderr messages if a
command produces output only on stderr.  Normally the -p option
causes command output to be suppressed until the command produces
at least one byte of output on stdout.

Environment
-----------

pwd is the project's working directory.  If the current client is
a mirror client, then pwd is the Git repository.

REPO_PROJECT is set to the unique name of the project.

REPO_PATH is the path relative the the root of the client.

REPO_REMOTE is the name of the remote system from the manifest.

REPO_LREV is the name of the revision from the manifest, translated
to a local tracking branch.  If you need to pass the manifest
revision to a locally executed git command, use REPO_LREV.

REPO_RREV is the name of the revision from the manifest, exactly
as written in the manifest.

shell positional arguments ($1, $2, .., $#) are set to any arguments
following <command>.

Unless -p is used, stdin, stdout, stderr are inherited from the
terminal and are not redirected.
"""

  def _Options(self, p):
    def cmd(option, opt_str, value, parser):
      setattr(parser.values, option.dest, list(parser.rargs))
      while parser.rargs:
        del parser.rargs[0]
    p.add_option('-c', '--command',
                 help='Command (and arguments) to execute',
                 dest='command',
                 action='callback',
                 callback=cmd)

    g = p.add_option_group('Output')
    g.add_option('-p',
                 dest='project_header', action='store_true',
                 help='Show project headers before output')
    g.add_option('-v', '--verbose',
                 dest='verbose', action='store_true',
                 help='Show command error messages')

  def WantPager(self, opt):
    return opt.project_header

  def Execute(self, opt, args):
    if not opt.command:
      self.Usage()

    cmd = [opt.command[0]]

    shell = True
    if re.compile(r'^[a-z0-9A-Z_/\.-]+$').match(cmd[0]):
      shell = False

    if shell:
      cmd.append(cmd[0])
    cmd.extend(opt.command[1:])

    if  opt.project_header \
    and not shell \
    and cmd[0] == 'git':
      # If this is a direct git command that can enable colorized
      # output and the user prefers coloring, add --color into the
      # command line because we are going to wrap the command into
      # a pipe and git won't know coloring should activate.
      #
      for cn in cmd[1:]:
        if not cn.startswith('-'):
          break
      if cn in _CAN_COLOR:
        class ColorCmd(Coloring):
          def __init__(self, config, cmd):
            Coloring.__init__(self, config, cmd)
        if ColorCmd(self.manifest.manifestProject.config, cn).is_on:
          cmd.insert(cmd.index(cn) + 1, '--color')

    mirror = self.manifest.IsMirror
    out = ForallColoring(self.manifest.manifestProject.config)
    out.redirect(sys.stdout)

    rc = 0
    first = True

    for project in self.GetProjects(args):
      env = os.environ.copy()
      def setenv(name, val):
        if val is None:
          val = ''
        env[name] = val.encode()

      setenv('REPO_PROJECT', project.name)
      setenv('REPO_PATH', project.relpath)
      setenv('REPO_REMOTE', project.remote.name)
      setenv('REPO_LREV', project.GetRevisionId())
      setenv('REPO_RREV', project.revisionExpr)

      if mirror:
        setenv('GIT_DIR', project.gitdir)
        cwd = project.gitdir
      else:
        cwd = project.worktree

      if not os.path.exists(cwd):
        if (opt.project_header and opt.verbose) \
        or not opt.project_header:
          print >>sys.stderr, 'skipping %s/' % project.relpath
        continue

      if opt.project_header:
        stdin = subprocess.PIPE
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
      else:
        stdin = None
        stdout = None
        stderr = None

      p = subprocess.Popen(cmd,
                           cwd = cwd,
                           shell = shell,
                           env = env,
                           stdin = stdin,
                           stdout = stdout,
                           stderr = stderr)

      if opt.project_header:
        class sfd(object):
          def __init__(self, fd, dest):
            self.fd = fd
            self.dest = dest
          def fileno(self):
            return self.fd.fileno()

        empty = True
        didout = False
        errbuf = ''

        p.stdin.close()
        s_in = [sfd(p.stdout, sys.stdout),
                sfd(p.stderr, sys.stderr)]

        for s in s_in:
          flags = fcntl.fcntl(s.fd, fcntl.F_GETFL)
          fcntl.fcntl(s.fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        while s_in:
          in_ready, out_ready, err_ready = select.select(s_in, [], [])
          for s in in_ready:
            buf = s.fd.read(4096)
            if not buf:
              s.fd.close()
              s_in.remove(s)
              continue

            if not opt.verbose:
              if s.fd == p.stdout:
                didout = True
              else:
                errbuf += buf
                continue

            if empty:
              if first:
                first = False
              else:
                out.nl()
              out.project('project %s/', project.relpath)
              out.nl()
              out.flush()
              if errbuf:
                sys.stderr.write(errbuf)
                sys.stderr.flush()
                errbuf = ''
              empty = False

            s.dest.write(buf)
            s.dest.flush()

      r = p.wait()
      if r != 0 and r != rc:
        rc = r
    if rc != 0:
      sys.exit(rc)

########NEW FILE########
__FILENAME__ = grep
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from optparse import SUPPRESS_HELP
from color import Coloring
from command import PagedCommand
from git_command import git_require, GitCommand

class GrepColoring(Coloring):
  def __init__(self, config):
    Coloring.__init__(self, config, 'grep')
    self.project = self.printer('project', attr='bold')

class Grep(PagedCommand):
  common = True
  helpSummary = "Print lines matching a pattern"
  helpUsage = """
%prog {pattern | -e pattern} [<project>...]
"""
  helpDescription = """
Search for the specified patterns in all project files.

Boolean Options
---------------

The following options can appear as often as necessary to express
the pattern to locate:

 -e PATTERN
 --and, --or, --not, -(, -)

Further, the -r/--revision option may be specified multiple times
in order to scan multiple trees.  If the same file matches in more
than one tree, only the first result is reported, prefixed by the
revision name it was found under.

Examples
-------

Look for a line that has '#define' and either 'MAX_PATH or 'PATH_MAX':

  repo grep -e '#define' --and -\( -e MAX_PATH -e PATH_MAX \)

Look for a line that has 'NODE' or 'Unexpected' in files that
contain a line that matches both expressions:

  repo grep --all-match -e NODE -e Unexpected

"""

  def _Options(self, p):
    def carry(option,
              opt_str,
              value,
              parser):
      pt = getattr(parser.values, 'cmd_argv', None)
      if pt is None:
        pt = []
        setattr(parser.values, 'cmd_argv', pt)

      if opt_str == '-(':
        pt.append('(')
      elif opt_str == '-)':
        pt.append(')')
      else:
        pt.append(opt_str)

      if value is not None:
        pt.append(value)

    g = p.add_option_group('Sources')
    g.add_option('--cached',
                 action='callback', callback=carry,
                 help='Search the index, instead of the work tree')
    g.add_option('-r','--revision',
                 dest='revision', action='append', metavar='TREEish',
                 help='Search TREEish, instead of the work tree')

    g = p.add_option_group('Pattern')
    g.add_option('-e',
                 action='callback', callback=carry,
                 metavar='PATTERN', type='str',
                 help='Pattern to search for')
    g.add_option('-i', '--ignore-case',
                 action='callback', callback=carry,
                 help='Ignore case differences')
    g.add_option('-a','--text',
                 action='callback', callback=carry,
                 help="Process binary files as if they were text")
    g.add_option('-I',
                 action='callback', callback=carry,
                 help="Don't match the pattern in binary files")
    g.add_option('-w', '--word-regexp',
                 action='callback', callback=carry,
                 help='Match the pattern only at word boundaries')
    g.add_option('-v', '--invert-match',
                 action='callback', callback=carry,
                 help='Select non-matching lines')
    g.add_option('-G', '--basic-regexp',
                 action='callback', callback=carry,
                 help='Use POSIX basic regexp for patterns (default)')
    g.add_option('-E', '--extended-regexp',
                 action='callback', callback=carry,
                 help='Use POSIX extended regexp for patterns')
    g.add_option('-F', '--fixed-strings',
                 action='callback', callback=carry,
                 help='Use fixed strings (not regexp) for pattern')

    g = p.add_option_group('Pattern Grouping')
    g.add_option('--all-match',
                 action='callback', callback=carry,
                 help='Limit match to lines that have all patterns')
    g.add_option('--and', '--or', '--not',
                 action='callback', callback=carry,
                 help='Boolean operators to combine patterns')
    g.add_option('-(','-)',
                 action='callback', callback=carry,
                 help='Boolean operator grouping')

    g = p.add_option_group('Output')
    g.add_option('-n',
                 action='callback', callback=carry,
                 help='Prefix the line number to matching lines')
    g.add_option('-C',
                 action='callback', callback=carry,
                 metavar='CONTEXT', type='str',
                 help='Show CONTEXT lines around match')
    g.add_option('-B',
                 action='callback', callback=carry,
                 metavar='CONTEXT', type='str',
                 help='Show CONTEXT lines before match')
    g.add_option('-A',
                 action='callback', callback=carry,
                 metavar='CONTEXT', type='str',
                 help='Show CONTEXT lines after match')
    g.add_option('-l','--name-only','--files-with-matches',
                 action='callback', callback=carry,
                 help='Show only file names containing matching lines')
    g.add_option('-L','--files-without-match',
                 action='callback', callback=carry,
                 help='Show only file names not containing matching lines')


  def Execute(self, opt, args):
    out = GrepColoring(self.manifest.manifestProject.config)

    cmd_argv = ['grep']
    if out.is_on and git_require((1,6,3)):
      cmd_argv.append('--color')
    cmd_argv.extend(getattr(opt,'cmd_argv',[]))

    if '-e' not in cmd_argv:
      if not args:
        self.Usage()
      cmd_argv.append('-e')
      cmd_argv.append(args[0])
      args = args[1:]

    projects = self.GetProjects(args)

    full_name = False
    if len(projects) > 1:
      cmd_argv.append('--full-name')
      full_name = True

    have_rev = False
    if opt.revision:
      if '--cached' in cmd_argv:
        print >>sys.stderr,\
          'fatal: cannot combine --cached and --revision'
        sys.exit(1)
      have_rev = True
      cmd_argv.extend(opt.revision)
    cmd_argv.append('--')

    bad_rev = False
    have_match = False

    for project in projects:
      p = GitCommand(project,
                     cmd_argv,
                     bare = False,
                     capture_stdout = True,
                     capture_stderr = True)
      if p.Wait() != 0:
        # no results
        #
        if p.stderr:
          if have_rev and 'fatal: ambiguous argument' in p.stderr:
            bad_rev = True
          else:
            out.project('--- project %s ---' % project.relpath)
            out.nl()
            out.write("%s", p.stderr)
            out.nl()
        continue
      have_match = True

      # We cut the last element, to avoid a blank line.
      #
      r = p.stdout.split('\n')
      r = r[0:-1]

      if have_rev and full_name:
        for line in r:
          rev, line = line.split(':', 1)
          out.write("%s", rev)
          out.write(':')
          out.project(project.relpath)
          out.write('/')
          out.write("%s", line)
          out.nl()
      elif full_name:
        for line in r:
          out.project(project.relpath)
          out.write('/')
          out.write("%s", line)
          out.nl()
      else:
        for line in r:
          print line

    if have_match:
      sys.exit(0)
    elif have_rev and bad_rev:
      for r in opt.revision:
        print >>sys.stderr, "error: can't search revision %s" % r
      sys.exit(1)
    else:
      sys.exit(1)

########NEW FILE########
__FILENAME__ = help
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import sys
from formatter import AbstractFormatter, DumbWriter

from color import Coloring
from command import PagedCommand, MirrorSafeCommand

class Help(PagedCommand, MirrorSafeCommand):
  common = False
  helpSummary = "Display detailed help on a command"
  helpUsage = """
%prog [--all|command]
"""
  helpDescription = """
Displays detailed usage information about a command.
"""

  def _PrintAllCommands(self):
    print 'usage: repo COMMAND [ARGS]'
    print """
The complete list of recognized repo commands are:
"""
    commandNames = self.commands.keys()
    commandNames.sort()

    maxlen = 0
    for name in commandNames:
      maxlen = max(maxlen, len(name))
    fmt = '  %%-%ds  %%s' % maxlen

    for name in commandNames:
      command = self.commands[name]
      try:
        summary = command.helpSummary.strip()
      except AttributeError:
        summary = ''
      print fmt % (name, summary)
    print """
See 'repo help <command>' for more information on a specific command.
"""

  def _PrintCommonCommands(self):
    print 'usage: repo COMMAND [ARGS]'
    print """
The most commonly used repo commands are:
"""
    commandNames = [name 
                    for name in self.commands.keys()
                    if self.commands[name].common]
    commandNames.sort()

    maxlen = 0
    for name in commandNames:
      maxlen = max(maxlen, len(name))
    fmt = '  %%-%ds  %%s' % maxlen

    for name in commandNames:
      command = self.commands[name]
      try:
        summary = command.helpSummary.strip()
      except AttributeError:
        summary = ''
      print fmt % (name, summary)
    print """
See 'repo help <command>' for more information on a specific command.
See 'repo help --all' for a complete list of recognized commands.
"""

  def _PrintCommandHelp(self, cmd):
    class _Out(Coloring):
      def __init__(self, gc):
        Coloring.__init__(self, gc, 'help')
        self.heading = self.printer('heading', attr='bold')

        self.wrap = AbstractFormatter(DumbWriter())

      def _PrintSection(self, heading, bodyAttr):
        try:
          body = getattr(cmd, bodyAttr)
        except AttributeError:
          return
        if body == '' or body is None:
          return

        self.nl()

        self.heading('%s', heading)
        self.nl()

        self.heading('%s', ''.ljust(len(heading), '-'))
        self.nl()

        me = 'repo %s' % cmd.NAME
        body = body.strip()
        body = body.replace('%prog', me)

        asciidoc_hdr = re.compile(r'^\n?([^\n]{1,})\n([=~-]{2,})$')
        for para in body.split("\n\n"):
          if para.startswith(' '):
            self.write('%s', para)
            self.nl()
            self.nl()
            continue

          m = asciidoc_hdr.match(para)
          if m:
            title = m.group(1)
            type = m.group(2)
            if type[0] in ('=', '-'):
              p = self.heading
            else:
              def _p(fmt, *args):
                self.write('  ')
                self.heading(fmt, *args)
              p = _p

            p('%s', title)
            self.nl()
            p('%s', ''.ljust(len(title),type[0]))
            self.nl()
            continue

          self.wrap.add_flowing_data(para)
          self.wrap.end_paragraph(1)
        self.wrap.end_paragraph(0)

    out = _Out(self.manifest.globalConfig)
    out._PrintSection('Summary', 'helpSummary')
    cmd.OptionParser.print_help()
    out._PrintSection('Description', 'helpDescription')

  def _Options(self, p):
    p.add_option('-a', '--all',
                 dest='show_all', action='store_true',
                 help='show the complete list of commands')

  def Execute(self, opt, args):
    if len(args) == 0:
      if opt.show_all:
        self._PrintAllCommands()
      else:
        self._PrintCommonCommands()

    elif len(args) == 1:
      name = args[0]

      try:
        cmd = self.commands[name]
      except KeyError:
        print >>sys.stderr, "repo: '%s' is not a repo command." % name
        sys.exit(1)

      cmd.repodir = self.repodir
      self._PrintCommandHelp(cmd)

    else:
      self._PrintCommandHelp(self)

########NEW FILE########
__FILENAME__ = init
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from color import Coloring
from command import InteractiveCommand, MirrorSafeCommand
from error import ManifestParseError
from project import SyncBuffer
from git_command import git_require, MIN_GIT_VERSION
from manifest_submodule import SubmoduleManifest
from manifest_xml import XmlManifest
from subcmds.sync import _ReloadManifest

class Init(InteractiveCommand, MirrorSafeCommand):
  common = True
  helpSummary = "Initialize repo in the current directory"
  helpUsage = """
%prog [options]
"""
  helpDescription = """
The '%prog' command is run once to install and initialize repo.
The latest repo source code and manifest collection is downloaded
from the server and is installed in the .repo/ directory in the
current working directory.

The optional -b argument can be used to select the manifest branch
to checkout and use.  If no branch is specified, master is assumed.

The optional -m argument can be used to specify an alternate manifest
to be used. If no manifest is specified, the manifest default.xml
will be used.

The --reference option can be used to point to a directory that
has the content of a --mirror sync. This will make the working
directory use as much data as possible from the local reference
directory when fetching from the server. This will make the sync
go a lot faster by reducing data traffic on the network.


Switching Manifest Branches
---------------------------

To switch to another manifest branch, `repo init -b otherbranch`
may be used in an existing client.  However, as this only updates the
manifest, a subsequent `repo sync` (or `repo sync -d`) is necessary
to update the working directory files.
"""

  def _Options(self, p):
    # Logging
    g = p.add_option_group('Logging options')
    g.add_option('-q', '--quiet',
                 dest="quiet", action="store_true", default=False,
                 help="be quiet")

    # Manifest
    g = p.add_option_group('Manifest options')
    g.add_option('-u', '--manifest-url',
                 dest='manifest_url',
                 help='manifest repository location', metavar='URL')
    g.add_option('-b', '--manifest-branch',
                 dest='manifest_branch',
                 help='manifest branch or revision', metavar='REVISION')
    g.add_option('-o', '--origin',
                 dest='manifest_origin',
                 help="use REMOTE instead of 'origin' to track upstream",
                 metavar='REMOTE')
    if isinstance(self.manifest, XmlManifest) \
    or not self.manifest.manifestProject.Exists:
      g.add_option('-m', '--manifest-name',
                   dest='manifest_name', default='default.xml',
                   help='initial manifest file', metavar='NAME.xml')
    g.add_option('--mirror',
                 dest='mirror', action='store_true',
                 help='mirror the forrest')
    g.add_option('--reference',
                 dest='reference',
                 help='location of mirror directory', metavar='DIR')

    # Tool
    g = p.add_option_group('repo Version options')
    g.add_option('--repo-url',
                 dest='repo_url',
                 help='repo repository location', metavar='URL')
    g.add_option('--repo-branch',
                 dest='repo_branch',
                 help='repo branch or revision', metavar='REVISION')
    g.add_option('--no-repo-verify',
                 dest='no_repo_verify', action='store_true',
                 help='do not verify repo source code')

  def _ApplyOptions(self, opt, is_new):
    m = self.manifest.manifestProject

    if is_new:
      if opt.manifest_origin:
        m.remote.name = opt.manifest_origin

      if opt.manifest_branch:
        m.revisionExpr = opt.manifest_branch
      else:
        m.revisionExpr = 'refs/heads/master'
    else:
      if opt.manifest_origin:
        print >>sys.stderr, 'fatal: cannot change origin name'
        sys.exit(1)

      if opt.manifest_branch:
        m.revisionExpr = opt.manifest_branch
      else:
        m.PreSync()

  def _SyncManifest(self, opt):
    m = self.manifest.manifestProject
    is_new = not m.Exists

    if is_new:
      if not opt.manifest_url:
        print >>sys.stderr, 'fatal: manifest url (-u) is required.'
        sys.exit(1)

      if not opt.quiet:
        print >>sys.stderr, 'Getting manifest ...'
        print >>sys.stderr, '   from %s' % opt.manifest_url
      m._InitGitDir()

    self._ApplyOptions(opt, is_new)
    if opt.manifest_url:
      r = m.GetRemote(m.remote.name)
      r.url = opt.manifest_url
      r.ResetFetch()
      r.Save()

    if opt.reference:
      m.config.SetString('repo.reference', opt.reference)

    if opt.mirror:
      if is_new:
        m.config.SetString('repo.mirror', 'true')
        m.config.ClearCache()
      else:
        print >>sys.stderr, 'fatal: --mirror not supported on existing client'
        sys.exit(1)

    if not m.Sync_NetworkHalf():
      r = m.GetRemote(m.remote.name)
      print >>sys.stderr, 'fatal: cannot obtain manifest %s' % r.url
      sys.exit(1)

    if is_new and SubmoduleManifest.IsBare(m):
      new = self.GetManifest(reparse=True, type=SubmoduleManifest)
      if m.gitdir != new.manifestProject.gitdir:
        os.rename(m.gitdir, new.manifestProject.gitdir)
        new = self.GetManifest(reparse=True, type=SubmoduleManifest)
      m = new.manifestProject
      self._ApplyOptions(opt, is_new)

    if not is_new:
      # Force the manifest to load if it exists, the old graph
      # may be needed inside of _ReloadManifest().
      #
      self.manifest.projects

    syncbuf = SyncBuffer(m.config)
    m.Sync_LocalHalf(syncbuf)
    syncbuf.Finish()

    if isinstance(self.manifest, XmlManifest):
      self._LinkManifest(opt.manifest_name)
    _ReloadManifest(self)

    self._ApplyOptions(opt, is_new)

    if not self.manifest.InitBranch():
      print >>sys.stderr, 'fatal: cannot create branch in manifest'
      sys.exit(1)

  def _LinkManifest(self, name):
    if not name:
      print >>sys.stderr, 'fatal: manifest name (-m) is required.'
      sys.exit(1)

    try:
      self.manifest.Link(name)
    except ManifestParseError, e:
      print >>sys.stderr, "fatal: manifest '%s' not available" % name
      print >>sys.stderr, 'fatal: %s' % str(e)
      sys.exit(1)

  def _Prompt(self, prompt, value):
    mp = self.manifest.manifestProject

    sys.stdout.write('%-10s [%s]: ' % (prompt, value))
    a = sys.stdin.readline().strip()
    if a == '':
      return value
    return a

  def _ConfigureUser(self):
    mp = self.manifest.manifestProject

    while True:
      print ''
      name  = self._Prompt('Your Name', mp.UserName)
      email = self._Prompt('Your Email', mp.UserEmail)

      print ''
      print 'Your identity is: %s <%s>' % (name, email)
      sys.stdout.write('is this correct [y/n]? ')
      a = sys.stdin.readline().strip()
      if a in ('yes', 'y', 't', 'true'):
        break

    if name != mp.UserName:
      mp.config.SetString('user.name', name)
    if email != mp.UserEmail:
      mp.config.SetString('user.email', email)

  def _HasColorSet(self, gc):
    for n in ['ui', 'diff', 'status']:
      if gc.Has('color.%s' % n):
        return True
    return False

  def _ConfigureColor(self):
    gc = self.manifest.globalConfig
    if self._HasColorSet(gc):
      return

    class _Test(Coloring):
      def __init__(self):
        Coloring.__init__(self, gc, 'test color display')
        self._on = True
    out = _Test()

    print ''
    print "Testing colorized output (for 'repo diff', 'repo status'):"

    for c in ['black','red','green','yellow','blue','magenta','cyan']:
      out.write(' ')
      out.printer(fg=c)(' %-6s ', c)
    out.write(' ')
    out.printer(fg='white', bg='black')(' %s ' % 'white')
    out.nl()

    for c in ['bold','dim','ul','reverse']:
      out.write(' ')
      out.printer(fg='black', attr=c)(' %-6s ', c)
    out.nl()

    sys.stdout.write('Enable color display in this user account (y/n)? ')
    a = sys.stdin.readline().strip().lower()
    if a in ('y', 'yes', 't', 'true', 'on'):
      gc.SetString('color.ui', 'auto')

  def Execute(self, opt, args):
    git_require(MIN_GIT_VERSION, fail=True)
    self._SyncManifest(opt)

    if os.isatty(0) and os.isatty(1) and not self.manifest.IsMirror:
      self._ConfigureUser()
      self._ConfigureColor()

    if self.manifest.IsMirror:
      type = 'mirror '
    else:
      type = ''

    print ''
    print 'repo %sinitialized in %s' % (type, self.manifest.topdir)

########NEW FILE########
__FILENAME__ = manifest
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from command import PagedCommand
from manifest_submodule import SubmoduleManifest
from manifest_xml import XmlManifest

def _doc(name):
  r = os.path.dirname(__file__)
  r = os.path.dirname(r)
  fd = open(os.path.join(r, 'docs', name))
  try:
    return fd.read()
  finally:
    fd.close()

class Manifest(PagedCommand):
  common = False
  helpSummary = "Manifest inspection utility"
  helpUsage = """
%prog [options]
"""
  _xmlHelp = """

With the -o option, exports the current manifest for inspection.
The manifest and (if present) local_manifest.xml are combined
together to produce a single manifest file.  This file can be stored
in a Git repository for use during future 'repo init' invocations.

"""

  @property
  def helpDescription(self):
    help = ''
    if isinstance(self.manifest, XmlManifest):
      help += self._xmlHelp + '\n' + _doc('manifest_xml.txt')
    if isinstance(self.manifest, SubmoduleManifest):
      help += _doc('manifest_submodule.txt')
    return help

  def _Options(self, p):
    if isinstance(self.manifest, XmlManifest):
      p.add_option('--upgrade',
                   dest='upgrade', action='store_true',
                   help='Upgrade XML manifest to submodule')
      p.add_option('-r', '--revision-as-HEAD',
                   dest='peg_rev', action='store_true',
                   help='Save revisions as current HEAD')
      p.add_option('-o', '--output-file',
                   dest='output_file',
                   help='File to save the manifest to',
                   metavar='-|NAME.xml')

  def WantPager(self, opt):
    if isinstance(self.manifest, XmlManifest) and opt.upgrade:
      return False
    return True

  def _Output(self, opt):
    if opt.output_file == '-':
      fd = sys.stdout
    else:
      fd = open(opt.output_file, 'w')
    self.manifest.Save(fd,
                       peg_rev = opt.peg_rev)
    fd.close()
    if opt.output_file != '-':
      print >>sys.stderr, 'Saved manifest to %s' % opt.output_file

  def _Upgrade(self):
    old = self.manifest

    if isinstance(old, SubmoduleManifest):
      print >>sys.stderr, 'error: already upgraded'
      sys.exit(1)

    old._Load()
    for p in old.projects.values():
      if not os.path.exists(p.gitdir) \
      or not os.path.exists(p.worktree):
        print >>sys.stderr, 'fatal: project "%s" missing' % p.relpath
        sys.exit(1)

    new = SubmoduleManifest(old.repodir)
    new.FromXml_Local_1(old, checkout=False)
    new.FromXml_Definition(old)
    new.FromXml_Local_2(old)
    print >>sys.stderr, 'upgraded manifest; commit result manually'

  def Execute(self, opt, args):
    if args:
      self.Usage()

    if isinstance(self.manifest, XmlManifest):
      if opt.upgrade:
        self._Upgrade()
        return

      if opt.output_file is not None:
        self._Output(opt)
        return

    print >>sys.stderr, 'error: no operation to perform'
    print >>sys.stderr, 'error: see repo help manifest'
    sys.exit(1)

########NEW FILE########
__FILENAME__ = prune
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from color import Coloring
from command import PagedCommand

class Prune(PagedCommand):
  common = True
  helpSummary = "Prune (delete) already merged topics"
  helpUsage = """
%prog [<project>...]
"""

  def Execute(self, opt, args):
    all = []
    for project in self.GetProjects(args):
      all.extend(project.PruneHeads())

    if not all:
      return

    class Report(Coloring):
      def __init__(self, config):
        Coloring.__init__(self, config, 'status')
        self.project = self.printer('header', attr='bold')

    out = Report(all[0].project.config)
    out.project('Pending Branches')
    out.nl()

    project = None

    for branch in all:
      if project != branch.project:
        project = branch.project
        out.nl()
        out.project('project %s/' % project.relpath)
        out.nl()

      commits = branch.commits
      date = branch.date
      print '%s %-33s (%2d commit%s, %s)' % (
            branch.name == project.CurrentBranch and '*' or ' ',
            branch.name,
            len(commits),
            len(commits) != 1 and 's' or ' ',
            date)

########NEW FILE########
__FILENAME__ = rebase
#
# Copyright (C) 2010 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from command import Command
from git_command import GitCommand
from git_refs import GitRefs, HEAD, R_HEADS, R_TAGS, R_PUB
from error import GitError

class Rebase(Command):
  common = True
  helpSummary = "Rebase local branches on upstream branch"
  helpUsage = """
%prog {[<project>...] | -i <project>...}
"""
  helpDescription = """
'%prog' uses git rebase to move local changes in the current topic branch to
the HEAD of the upstream history, useful when you have made commits in a topic
branch but need to incorporate new upstream changes "underneath" them.
"""

  def _Options(self, p):
    p.add_option('-i', '--interactive',
                dest="interactive", action="store_true",
                help="interactive rebase (single project only)")

    p.add_option('-f', '--force-rebase',
                 dest='force_rebase', action='store_true',
                 help='Pass --force-rebase to git rebase')
    p.add_option('--no-ff',
                 dest='no_ff', action='store_true',
                 help='Pass --no-ff to git rebase')
    p.add_option('-q', '--quiet',
                 dest='quiet', action='store_true',
                 help='Pass --quiet to git rebase')
    p.add_option('--autosquash',
                 dest='autosquash', action='store_true',
                 help='Pass --autosquash to git rebase')
    p.add_option('--whitespace',
                 dest='whitespace', action='store', metavar='WS',
                 help='Pass --whitespace to git rebase')

  def Execute(self, opt, args):
    all = self.GetProjects(args)
    one_project = len(all) == 1

    if opt.interactive and not one_project:
      print >>sys.stderr, 'error: interactive rebase not supported with multiple projects'
      return -1

    for project in all:
      cb = project.CurrentBranch
      if not cb:
        if one_project:
          print >>sys.stderr, "error: project %s has a detatched HEAD" % project.relpath
          return -1
        # ignore branches with detatched HEADs
        continue

      upbranch = project.GetBranch(cb)
      if not upbranch.LocalMerge:
        if one_project:
          print >>sys.stderr, "error: project %s does not track any remote branches" % project.relpath
          return -1
        # ignore branches without remotes
        continue

      args = ["rebase"]

      if opt.whitespace:
        args.append('--whitespace=%s' % opt.whitespace)

      if opt.quiet:
        args.append('--quiet')

      if opt.force_rebase:
        args.append('--force-rebase')

      if opt.no_ff:
        args.append('--no-ff')

      if opt.autosquash:
        args.append('--autosquash')

      if opt.interactive:
        args.append("-i")

      args.append(upbranch.LocalMerge)

      print >>sys.stderr, '# %s: rebasing %s -> %s' % \
        (project.relpath, cb, upbranch.LocalMerge)

      if GitCommand(project, args).Wait() != 0:
        return -1

########NEW FILE########
__FILENAME__ = selfupdate
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from optparse import SUPPRESS_HELP
import sys

from command import Command, MirrorSafeCommand
from subcmds.sync import _PostRepoUpgrade
from subcmds.sync import _PostRepoFetch

class Selfupdate(Command, MirrorSafeCommand):
  common = False
  helpSummary = "Update repo to the latest version"
  helpUsage = """
%prog
"""
  helpDescription = """
The '%prog' command upgrades repo to the latest version, if a
newer version is available.

Normally this is done automatically by 'repo sync' and does not
need to be performed by an end-user.
"""

  def _Options(self, p):
    g = p.add_option_group('repo Version options')
    g.add_option('--no-repo-verify',
                 dest='no_repo_verify', action='store_true',
                 help='do not verify repo source code')
    g.add_option('--repo-upgraded',
                 dest='repo_upgraded', action='store_true',
                 help=SUPPRESS_HELP)

  def Execute(self, opt, args):
    rp = self.manifest.repoProject
    rp.PreSync()

    if opt.repo_upgraded:
      _PostRepoUpgrade(self.manifest)

    else:
      if not rp.Sync_NetworkHalf():
        print >>sys.stderr, "error: can't update repo"
        sys.exit(1)

      rp.bare_git.gc('--auto')
      _PostRepoFetch(rp,
                     no_repo_verify = opt.no_repo_verify,
                     verbose = True)

########NEW FILE########
__FILENAME__ = smartsync
#
# Copyright (C) 2010 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sync import Sync

class Smartsync(Sync):
  common = True
  helpSummary = "Update working tree to the latest known good revision"
  helpUsage = """
%prog [<project>...]
"""
  helpDescription = """
The '%prog' command is a shortcut for sync -s.
"""

  def _Options(self, p):
    Sync._Options(self, p, show_smart=False)

  def Execute(self, opt, args):
    opt.smart_sync = True
    Sync.Execute(self, opt, args)

########NEW FILE########
__FILENAME__ = stage
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from color import Coloring
from command import InteractiveCommand
from git_command import GitCommand

class _ProjectList(Coloring):
  def __init__(self, gc):
    Coloring.__init__(self, gc, 'interactive')
    self.prompt = self.printer('prompt', fg='blue', attr='bold')
    self.header = self.printer('header', attr='bold')
    self.help = self.printer('help', fg='red', attr='bold')

class Stage(InteractiveCommand):
  common = True
  helpSummary = "Stage file(s) for commit"
  helpUsage = """
%prog -i [<project>...]
"""
  helpDescription = """
The '%prog' command stages files to prepare the next commit.
"""

  def _Options(self, p):
    p.add_option('-i', '--interactive',
                 dest='interactive', action='store_true',
                 help='use interactive staging')

  def Execute(self, opt, args):
    if opt.interactive:
      self._Interactive(opt, args)
    else:
      self.Usage()

  def _Interactive(self, opt, args):
    all = filter(lambda x: x.IsDirty(), self.GetProjects(args))
    if not all:
      print >>sys.stderr,'no projects have uncommitted modifications'
      return

    out = _ProjectList(self.manifest.manifestProject.config)
    while True:
      out.header('        %s', 'project')
      out.nl()

      for i in xrange(0, len(all)):
        p = all[i]
        out.write('%3d:    %s', i + 1, p.relpath + '/')
        out.nl()
      out.nl()

      out.write('%3d: (', 0)
      out.prompt('q')
      out.write('uit)')
      out.nl()

      out.prompt('project> ')
      try:
        a = sys.stdin.readline()
      except KeyboardInterrupt:
        out.nl()
        break
      if a == '':
        out.nl()
        break

      a = a.strip()
      if a.lower() in ('q', 'quit', 'exit'):
        break
      if not a:
        continue

      try:
        a_index = int(a)
      except ValueError:
        a_index = None

      if a_index is not None:
        if a_index == 0:
          break
        if 0 < a_index and a_index <= len(all):
          _AddI(all[a_index - 1])
          continue

      p = filter(lambda x: x.name == a or x.relpath == a, all)
      if len(p) == 1:
        _AddI(p[0])
        continue
    print 'Bye.'

def _AddI(project):
  p = GitCommand(project, ['add', '--interactive'], bare=False)
  p.Wait()

########NEW FILE########
__FILENAME__ = start
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from command import Command
from git_command import git
from progress import Progress

class Start(Command):
  common = True
  helpSummary = "Start a new branch for development"
  helpUsage = """
%prog <newbranchname> [--all | <project>...]
"""
  helpDescription = """
'%prog' begins a new branch of development, starting from the
revision specified in the manifest.
"""

  def _Options(self, p):
    p.add_option('--all',
                 dest='all', action='store_true',
                 help='begin branch in all projects')

  def Execute(self, opt, args):
    if not args:
      self.Usage()

    nb = args[0]
    if not git.check_ref_format('heads/%s' % nb):
      print >>sys.stderr, "error: '%s' is not a valid name" % nb
      sys.exit(1)

    err = []
    projects = []
    if not opt.all:
      projects = args[1:]
      if len(projects) < 1:
        print >>sys.stderr, "error: at least one project must be specified"
        sys.exit(1)

    all = self.GetProjects(projects)

    pm = Progress('Starting %s' % nb, len(all))
    for project in all:
      pm.update()
      if not project.StartBranch(nb):
        err.append(project)
    pm.end()

    if err:
      for p in err:
        print >>sys.stderr,\
          "error: %s/: cannot start %s" \
          % (p.relpath, nb)
      sys.exit(1)

########NEW FILE########
__FILENAME__ = status
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from command import PagedCommand

class Status(PagedCommand):
  common = True
  helpSummary = "Show the working tree status"
  helpUsage = """
%prog [<project>...]
"""
  helpDescription = """
'%prog' compares the working tree to the staging area (aka index),
and the most recent commit on this branch (HEAD), in each project
specified.  A summary is displayed, one line per file where there
is a difference between these three states.

Status Display
--------------

The status display is organized into three columns of information,
for example if the file 'subcmds/status.py' is modified in the
project 'repo' on branch 'devwork':

  project repo/                                   branch devwork
   -m     subcmds/status.py

The first column explains how the staging area (index) differs from
the last commit (HEAD).  Its values are always displayed in upper
case and have the following meanings:

 -:  no difference
 A:  added         (not in HEAD,     in index                     )
 M:  modified      (    in HEAD,     in index, different content  )
 D:  deleted       (    in HEAD, not in index                     )
 R:  renamed       (not in HEAD,     in index, path changed       )
 C:  copied        (not in HEAD,     in index, copied from another)
 T:  mode changed  (    in HEAD,     in index, same content       )
 U:  unmerged; conflict resolution required

The second column explains how the working directory differs from
the index.  Its values are always displayed in lower case and have
the following meanings:

 -:  new / unknown (not in index,     in work tree                )
 m:  modified      (    in index,     in work tree, modified      )
 d:  deleted       (    in index, not in work tree                )

"""

  def Execute(self, opt, args):
    all = self.GetProjects(args)
    clean = 0

    on = {}
    for project in all:
      cb = project.CurrentBranch
      if cb:
        if cb not in on:
          on[cb] = []
        on[cb].append(project)

    branch_names = list(on.keys())
    branch_names.sort()
    for cb in branch_names:
      print '# on branch %s' % cb

    for project in all:
      state = project.PrintWorkTreeStatus()
      if state == 'CLEAN':
        clean += 1
    if len(all) == clean:
      print 'nothing to commit (working directory clean)'

########NEW FILE########
__FILENAME__ = sync
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from optparse import SUPPRESS_HELP
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import xmlrpclib

try:
  import threading as _threading
except ImportError:
  import dummy_threading as _threading

from git_command import GIT
from git_refs import R_HEADS
from project import HEAD
from project import Project
from project import RemoteSpec
from command import Command, MirrorSafeCommand
from error import RepoChangedException, GitError
from project import R_HEADS
from project import SyncBuffer
from progress import Progress

class Sync(Command, MirrorSafeCommand):
  jobs = 1
  common = True
  helpSummary = "Update working tree to the latest revision"
  helpUsage = """
%prog [<project>...]
"""
  helpDescription = """
The '%prog' command synchronizes local project directories
with the remote repositories specified in the manifest.  If a local
project does not yet exist, it will clone a new local directory from
the remote repository and set up tracking branches as specified in
the manifest.  If the local project already exists, '%prog'
will update the remote branches and rebase any new local changes
on top of the new remote changes.

'%prog' will synchronize all projects listed at the command
line.  Projects can be specified either by name, or by a relative
or absolute path to the project's local directory. If no projects
are specified, '%prog' will synchronize all projects listed in
the manifest.

The -d/--detach option can be used to switch specified projects
back to the manifest revision.  This option is especially helpful
if the project is currently on a topic branch, but the manifest
revision is temporarily needed.

The -s/--smart-sync option can be used to sync to a known good
build as specified by the manifest-server element in the current
manifest.

The -f/--force-broken option can be used to proceed with syncing
other projects if a project sync fails.

SSH Connections
---------------

If at least one project remote URL uses an SSH connection (ssh://,
git+ssh://, or user@host:path syntax) repo will automatically
enable the SSH ControlMaster option when connecting to that host.
This feature permits other projects in the same '%prog' session to
reuse the same SSH tunnel, saving connection setup overheads.

To disable this behavior on UNIX platforms, set the GIT_SSH
environment variable to 'ssh'.  For example:

  export GIT_SSH=ssh
  %prog

Compatibility
~~~~~~~~~~~~~

This feature is automatically disabled on Windows, due to the lack
of UNIX domain socket support.

This feature is not compatible with url.insteadof rewrites in the
user's ~/.gitconfig.  '%prog' is currently not able to perform the
rewrite early enough to establish the ControlMaster tunnel.

If the remote SSH daemon is Gerrit Code Review, version 2.0.10 or
later is required to fix a server side protocol bug.

"""

  def _Options(self, p, show_smart=True):
    p.add_option('-f', '--force-broken',
                 dest='force_broken', action='store_true',
                 help="continue sync even if a project fails to sync")
    p.add_option('-l','--local-only',
                 dest='local_only', action='store_true',
                 help="only update working tree, don't fetch")
    p.add_option('-n','--network-only',
                 dest='network_only', action='store_true',
                 help="fetch only, don't update working tree")
    p.add_option('-d','--detach',
                 dest='detach_head', action='store_true',
                 help='detach projects back to manifest revision')
    p.add_option('-q','--quiet',
                 dest='quiet', action='store_true',
                 help='be more quiet')
    p.add_option('-j','--jobs',
                 dest='jobs', action='store', type='int',
                 help="number of projects to fetch simultaneously")
    if show_smart:
      p.add_option('-s', '--smart-sync',
                   dest='smart_sync', action='store_true',
                   help='smart sync using manifest from a known good build')

    g = p.add_option_group('repo Version options')
    g.add_option('--no-repo-verify',
                 dest='no_repo_verify', action='store_true',
                 help='do not verify repo source code')
    g.add_option('--repo-upgraded',
                 dest='repo_upgraded', action='store_true',
                 help=SUPPRESS_HELP)

  def _FetchHelper(self, opt, project, lock, fetched, pm, sem):
      if not project.Sync_NetworkHalf(quiet=opt.quiet):
        print >>sys.stderr, 'error: Cannot fetch %s' % project.name
        if opt.force_broken:
          print >>sys.stderr, 'warn: --force-broken, continuing to sync'
        else:
          sem.release()
          sys.exit(1)

      lock.acquire()
      fetched.add(project.gitdir)
      pm.update()
      lock.release()
      sem.release()

  def _Fetch(self, projects, opt):
    fetched = set()
    pm = Progress('Fetching projects', len(projects))

    if self.jobs == 1:
      for project in projects:
        pm.update()
        if project.Sync_NetworkHalf(quiet=opt.quiet):
          fetched.add(project.gitdir)
        else:
          print >>sys.stderr, 'error: Cannot fetch %s' % project.name
          if opt.force_broken:
            print >>sys.stderr, 'warn: --force-broken, continuing to sync'
          else:
            sys.exit(1)
    else:
      threads = set()
      lock = _threading.Lock()
      sem = _threading.Semaphore(self.jobs)
      for project in projects:
        sem.acquire()
        t = _threading.Thread(target = self._FetchHelper,
                              args = (opt,
                                      project,
                                      lock,
                                      fetched,
                                      pm,
                                      sem))
        threads.add(t)
        t.start()

      for t in threads:
        t.join()

    pm.end()
    for project in projects:
      project.bare_git.gc('--auto')
    return fetched

  def UpdateProjectList(self):
    new_project_paths = []
    for project in self.manifest.projects.values():
      if project.relpath:
        new_project_paths.append(project.relpath)
    file_name = 'project.list'
    file_path = os.path.join(self.manifest.repodir, file_name)
    old_project_paths = []

    if os.path.exists(file_path):
      fd = open(file_path, 'r')
      try:
        old_project_paths = fd.read().split('\n')
      finally:
        fd.close()
      for path in old_project_paths:
        if not path:
          continue
        if path not in new_project_paths:
          """If the path has already been deleted, we don't need to do it
          """
          if os.path.exists(self.manifest.topdir + '/' + path):
              project = Project(
                             manifest = self.manifest,
                             name = path,
                             remote = RemoteSpec('origin'),
                             gitdir = os.path.join(self.manifest.topdir,
                                                   path, '.git'),
                             worktree = os.path.join(self.manifest.topdir, path),
                             relpath = path,
                             revisionExpr = 'HEAD',
                             revisionId = None)

              if project.IsDirty():
                print >>sys.stderr, 'error: Cannot remove project "%s": \
uncommitted changes are present' % project.relpath
                print >>sys.stderr, '       commit changes, then run sync again'
                return -1
              else:
                print >>sys.stderr, 'Deleting obsolete path %s' % project.worktree
                shutil.rmtree(project.worktree)
                # Try deleting parent subdirs if they are empty
                dir = os.path.dirname(project.worktree)
                while dir != self.manifest.topdir:
                  try:
                    os.rmdir(dir)
                  except OSError:
                    break
                  dir = os.path.dirname(dir)

    new_project_paths.sort()
    fd = open(file_path, 'w')
    try:
      fd.write('\n'.join(new_project_paths))
      fd.write('\n')
    finally:
      fd.close()
    return 0

  def Execute(self, opt, args):
    if opt.jobs:
      self.jobs = opt.jobs
    if opt.network_only and opt.detach_head:
      print >>sys.stderr, 'error: cannot combine -n and -d'
      sys.exit(1)
    if opt.network_only and opt.local_only:
      print >>sys.stderr, 'error: cannot combine -n and -l'
      sys.exit(1)

    if opt.smart_sync:
      if not self.manifest.manifest_server:
        print >>sys.stderr, \
            'error: cannot smart sync: no manifest server defined in manifest'
        sys.exit(1)
      try:
        server = xmlrpclib.Server(self.manifest.manifest_server)
        p = self.manifest.manifestProject
        b = p.GetBranch(p.CurrentBranch)
        branch = b.merge
        if branch.startswith(R_HEADS):
          branch = branch[len(R_HEADS):]

        env = os.environ.copy()
        if (env.has_key('TARGET_PRODUCT') and
            env.has_key('TARGET_BUILD_VARIANT')):
          target = '%s-%s' % (env['TARGET_PRODUCT'],
                              env['TARGET_BUILD_VARIANT'])
          [success, manifest_str] = server.GetApprovedManifest(branch, target)
        else:
          [success, manifest_str] = server.GetApprovedManifest(branch)

        if success:
          manifest_name = "smart_sync_override.xml"
          manifest_path = os.path.join(self.manifest.manifestProject.worktree,
                                       manifest_name)
          try:
            f = open(manifest_path, 'w')
            try:
              f.write(manifest_str)
            finally:
              f.close()
          except IOError:
            print >>sys.stderr, 'error: cannot write manifest to %s' % \
                manifest_path
            sys.exit(1)
          self.manifest.Override(manifest_name)
        else:
          print >>sys.stderr, 'error: %s' % manifest_str
          sys.exit(1)
      except socket.error:
        print >>sys.stderr, 'error: cannot connect to manifest server %s' % (
            self.manifest.manifest_server)
        sys.exit(1)

    rp = self.manifest.repoProject
    rp.PreSync()

    mp = self.manifest.manifestProject
    mp.PreSync()

    if opt.repo_upgraded:
      _PostRepoUpgrade(self.manifest)

    if not opt.local_only:
      mp.Sync_NetworkHalf(quiet=opt.quiet)

    if mp.HasChanges:
      syncbuf = SyncBuffer(mp.config)
      mp.Sync_LocalHalf(syncbuf)
      if not syncbuf.Finish():
        sys.exit(1)
      self.manifest._Unload()
    all = self.GetProjects(args, missing_ok=True)

    if not opt.local_only:
      to_fetch = []
      now = time.time()
      if (24 * 60 * 60) <= (now - rp.LastFetch):
        to_fetch.append(rp)
      to_fetch.extend(all)

      fetched = self._Fetch(to_fetch, opt)
      _PostRepoFetch(rp, opt.no_repo_verify)
      if opt.network_only:
        # bail out now; the rest touches the working tree
        return

      if mp.HasChanges:
        syncbuf = SyncBuffer(mp.config)
        mp.Sync_LocalHalf(syncbuf)
        if not syncbuf.Finish():
          sys.exit(1)
        _ReloadManifest(self)
        mp = self.manifest.manifestProject

        all = self.GetProjects(args, missing_ok=True)
        missing = []
        for project in all:
          if project.gitdir not in fetched:
            missing.append(project)
        self._Fetch(missing, opt)

    if self.manifest.IsMirror:
      # bail out now, we have no working tree
      return

    if self.UpdateProjectList():
      sys.exit(1)

    syncbuf = SyncBuffer(mp.config,
                         detach_head = opt.detach_head)
    pm = Progress('Syncing work tree', len(all))
    for project in all:
      pm.update()
      if project.worktree:
        project.Sync_LocalHalf(syncbuf)
    pm.end()
    print >>sys.stderr
    if not syncbuf.Finish():
      sys.exit(1)

def _ReloadManifest(cmd):
  old = cmd.manifest
  new = cmd.GetManifest(reparse=True)

  if old.__class__ != new.__class__:
    print >>sys.stderr, 'NOTICE: manifest format has changed  ***'
    new.Upgrade_Local(old)
  else:
    if new.notice:
      print new.notice

def _PostRepoUpgrade(manifest):
  for project in manifest.projects.values():
    if project.Exists:
      project.PostRepoUpgrade()

def _PostRepoFetch(rp, no_repo_verify=False, verbose=False):
  if rp.HasChanges:
    print >>sys.stderr, 'info: A new version of repo is available'
    print >>sys.stderr, ''
    if no_repo_verify or _VerifyTag(rp):
      syncbuf = SyncBuffer(rp.config)
      rp.Sync_LocalHalf(syncbuf)
      if not syncbuf.Finish():
        sys.exit(1)
      print >>sys.stderr, 'info: Restarting repo with latest version'
      raise RepoChangedException(['--repo-upgraded'])
    else:
      print >>sys.stderr, 'warning: Skipped upgrade to unverified version'
  else:
    if verbose:
      print >>sys.stderr, 'repo version %s is current' % rp.work_git.describe(HEAD)

def _VerifyTag(project):
  gpg_dir = os.path.expanduser('~/.repoconfig/gnupg')
  if not os.path.exists(gpg_dir):
    print >>sys.stderr,\
"""warning: GnuPG was not available during last "repo init"
warning: Cannot automatically authenticate repo."""
    return True

  try:
    cur = project.bare_git.describe(project.GetRevisionId())
  except GitError:
    cur = None

  if not cur \
     or re.compile(r'^.*-[0-9]{1,}-g[0-9a-f]{1,}$').match(cur):
    rev = project.revisionExpr
    if rev.startswith(R_HEADS):
      rev = rev[len(R_HEADS):]

    print >>sys.stderr
    print >>sys.stderr,\
      "warning: project '%s' branch '%s' is not signed" \
      % (project.name, rev)
    return False

  env = os.environ.copy()
  env['GIT_DIR'] = project.gitdir.encode()
  env['GNUPGHOME'] = gpg_dir.encode()

  cmd = [GIT, 'tag', '-v', cur]
  proc = subprocess.Popen(cmd,
                          stdout = subprocess.PIPE,
                          stderr = subprocess.PIPE,
                          env = env)
  out = proc.stdout.read()
  proc.stdout.close()

  err = proc.stderr.read()
  proc.stderr.close()

  if proc.wait() != 0:
    print >>sys.stderr
    print >>sys.stderr, out
    print >>sys.stderr, err
    print >>sys.stderr
    return False
  return True

########NEW FILE########
__FILENAME__ = upload
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import re
import sys

from command import InteractiveCommand
from editor import Editor
from error import UploadError

UNUSUAL_COMMIT_THRESHOLD = 5

def _ConfirmManyUploads(multiple_branches=False):
  if multiple_branches:
    print "ATTENTION: One or more branches has an unusually high number of commits."
  else:
    print "ATTENTION: You are uploading an unusually high number of commits."
  print "YOU PROBABLY DO NOT MEAN TO DO THIS. (Did you rebase across branches?)"
  answer = raw_input("If you are sure you intend to do this, type 'yes': ").strip()
  return answer == "yes"

def _die(fmt, *args):
  msg = fmt % args
  print >>sys.stderr, 'error: %s' % msg
  sys.exit(1)

def _SplitEmails(values):
  result = []
  for str in values:
    result.extend([s.strip() for s in str.split(',')])
  return result

class Upload(InteractiveCommand):
  common = True
  helpSummary = "Upload changes for code review"
  helpUsage="""
%prog [--re --cc] [<project>]...
"""
  helpDescription = """
The '%prog' command is used to send changes to the Gerrit Code
Review system.  It searches for topic branches in local projects
that have not yet been published for review.  If multiple topic
branches are found, '%prog' opens an editor to allow the user to
select which branches to upload.

'%prog' searches for uploadable changes in all projects listed at
the command line.  Projects can be specified either by name, or by
a relative or absolute path to the project's local directory. If no
projects are specified, '%prog' will search for uploadable changes
in all projects listed in the manifest.

If the --reviewers or --cc options are passed, those emails are
added to the respective list of users, and emails are sent to any
new users.  Users passed as --reviewers must already be registered
with the code review system, or the upload will fail.

Configuration
-------------

review.URL.autoupload:

To disable the "Upload ... (y/n)?" prompt, you can set a per-project
or global Git configuration option.  If review.URL.autoupload is set
to "true" then repo will assume you always answer "y" at the prompt,
and will not prompt you further.  If it is set to "false" then repo
will assume you always answer "n", and will abort.

review.URL.autocopy:

To automatically copy a user or mailing list to all uploaded reviews,
you can set a per-project or global Git option to do so. Specifically,
review.URL.autocopy can be set to a comma separated list of reviewers
who you always want copied on all uploads with a non-empty --re
argument.

review.URL.username:

Override the username used to connect to Gerrit Code Review.
By default the local part of the email address is used.

The URL must match the review URL listed in the manifest XML file,
or in the .git/config within the project.  For example:

  [remote "origin"]
    url = git://git.example.com/project.git
    review = http://review.example.com/

  [review "http://review.example.com/"]
    autoupload = true
    autocopy = johndoe@company.com,my-team-alias@company.com

References
----------

Gerrit Code Review:  http://code.google.com/p/gerrit/

"""

  def _Options(self, p):
    p.add_option('-t',
                 dest='auto_topic', action='store_true',
                 help='Send local branch name to Gerrit Code Review')
    p.add_option('--re', '--reviewers',
                 type='string',  action='append', dest='reviewers',
                 help='Request reviews from these people.')
    p.add_option('--cc',
                 type='string',  action='append', dest='cc',
                 help='Also send email to these email addresses.')

  def _SingleBranch(self, opt, branch, people):
    project = branch.project
    name = branch.name
    remote = project.GetBranch(name).remote

    key = 'review.%s.autoupload' % remote.review
    answer = project.config.GetBoolean(key)

    if answer is False:
      _die("upload blocked by %s = false" % key)

    if answer is None:
      date = branch.date
      list = branch.commits

      print 'Upload project %s/:' % project.relpath
      print '  branch %s (%2d commit%s, %s):' % (
                    name,
                    len(list),
                    len(list) != 1 and 's' or '',
                    date)
      for commit in list:
        print '         %s' % commit

      sys.stdout.write('to %s (y/n)? ' % remote.review)
      answer = sys.stdin.readline().strip()
      answer = answer in ('y', 'Y', 'yes', '1', 'true', 't')

    if answer:
      if len(branch.commits) > UNUSUAL_COMMIT_THRESHOLD:
        answer = _ConfirmManyUploads()

    if answer:
      self._UploadAndReport(opt, [branch], people)
    else:
      _die("upload aborted by user")

  def _MultipleBranches(self, opt, pending, people):
    projects = {}
    branches = {}

    script = []
    script.append('# Uncomment the branches to upload:')
    for project, avail in pending:
      script.append('#')
      script.append('# project %s/:' % project.relpath)

      b = {}
      for branch in avail:
        name = branch.name
        date = branch.date
        list = branch.commits

        if b:
          script.append('#')
        script.append('#  branch %s (%2d commit%s, %s):' % (
                      name,
                      len(list),
                      len(list) != 1 and 's' or '',
                      date))
        for commit in list:
          script.append('#         %s' % commit)
        b[name] = branch

      projects[project.relpath] = project
      branches[project.name] = b
    script.append('')

    script = Editor.EditString("\n".join(script)).split("\n")

    project_re = re.compile(r'^#?\s*project\s*([^\s]+)/:$')
    branch_re = re.compile(r'^\s*branch\s*([^\s(]+)\s*\(.*')

    project = None
    todo = []

    for line in script:
      m = project_re.match(line)
      if m:
        name = m.group(1)
        project = projects.get(name)
        if not project:
          _die('project %s not available for upload', name)
        continue

      m = branch_re.match(line)
      if m:
        name = m.group(1)
        if not project:
          _die('project for branch %s not in script', name)
        branch = branches[project.name].get(name)
        if not branch:
          _die('branch %s not in %s', name, project.relpath)
        todo.append(branch)
    if not todo:
      _die("nothing uncommented for upload")

    many_commits = False
    for branch in todo:
      if len(branch.commits) > UNUSUAL_COMMIT_THRESHOLD:
        many_commits = True
        break
    if many_commits:
      if not _ConfirmManyUploads(multiple_branches=True):
        _die("upload aborted by user")

    self._UploadAndReport(opt, todo, people)

  def _AppendAutoCcList(self, branch, people):
    """
    Appends the list of users in the CC list in the git project's config if a
    non-empty reviewer list was found.
    """

    name = branch.name
    project = branch.project
    key = 'review.%s.autocopy' % project.GetBranch(name).remote.review
    raw_list = project.config.GetString(key)
    if not raw_list is None and len(people[0]) > 0:
      people[1].extend([entry.strip() for entry in raw_list.split(',')])

  def _FindGerritChange(self, branch):
    last_pub = branch.project.WasPublished(branch.name)
    if last_pub is None:
      return ""

    refs = branch.GetPublishedRefs()
    try:
      # refs/changes/XYZ/N --> XYZ
      return refs.get(last_pub).split('/')[-2]
    except:
      return ""

  def _UploadAndReport(self, opt, todo, original_people):
    have_errors = False
    for branch in todo:
      try:
        people = copy.deepcopy(original_people)
        self._AppendAutoCcList(branch, people)

        # Check if there are local changes that may have been forgotten
        if branch.project.HasChanges():
            key = 'review.%s.autoupload' % branch.project.remote.review
            answer = branch.project.config.GetBoolean(key)

            # if they want to auto upload, let's not ask because it could be automated
            if answer is None:
                sys.stdout.write('Uncommitted changes in ' + branch.project.name + ' (did you forget to amend?). Continue uploading? (y/n) ')
                a = sys.stdin.readline().strip().lower()
                if a not in ('y', 'yes', 't', 'true', 'on'):
                    print >>sys.stderr, "skipping upload"
                    branch.uploaded = False
                    branch.error = 'User aborted'
                    continue

        branch.UploadForReview(people, auto_topic=opt.auto_topic)
        branch.uploaded = True
      except UploadError, e:
        branch.error = e
        branch.uploaded = False
        have_errors = True

    print >>sys.stderr, ''
    print >>sys.stderr, '----------------------------------------------------------------------'

    if have_errors:
      for branch in todo:
        if not branch.uploaded:
          if len(str(branch.error)) <= 30:
            fmt = ' (%s)'
          else:
            fmt = '\n       (%s)'
          print >>sys.stderr, ('[FAILED] %-15s %-15s' + fmt) % (
                 branch.project.relpath + '/', \
                 branch.name, \
                 str(branch.error))
      print >>sys.stderr, ''

    for branch in todo:
        if branch.uploaded:
          print >>sys.stderr, '[OK    ] %-15s %s' % (
                 branch.project.relpath + '/',
                 branch.name)

    if have_errors:
      sys.exit(1)

  def Execute(self, opt, args):
    project_list = self.GetProjects(args)
    pending = []
    reviewers = []
    cc = []

    if opt.reviewers:
      reviewers = _SplitEmails(opt.reviewers)
    if opt.cc:
      cc = _SplitEmails(opt.cc)
    people = (reviewers,cc)

    for project in project_list:
      avail = project.GetUploadableBranches()
      if avail:
        pending.append((project, avail))

    if not pending:
      print >>sys.stdout, "no branches ready for upload"
    elif len(pending) == 1 and len(pending[0][1]) == 1:
      self._SingleBranch(opt, pending[0][1][0], people)
    else:
      self._MultipleBranches(opt, pending, people)

########NEW FILE########
__FILENAME__ = version
#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from command import Command, MirrorSafeCommand
from git_command import git
from project import HEAD

class Version(Command, MirrorSafeCommand):
  common = False
  helpSummary = "Display the version of repo"
  helpUsage = """
%prog
"""

  def Execute(self, opt, args):
    rp = self.manifest.repoProject
    rem = rp.GetRemote(rp.remote.name)

    print 'repo version %s' % rp.work_git.describe(HEAD)
    print '       (from %s)' % rem.url
    print git.version().strip()
    print 'Python %s' % sys.version

########NEW FILE########
__FILENAME__ = test_git_config
import os
import unittest

import git_config

def fixture(*paths):
    """Return a path relative to test/fixtures.
    """
    return os.path.join(os.path.dirname(__file__), 'fixtures', *paths)

class GitConfigUnitTest(unittest.TestCase):
    """Tests the GitConfig class.
    """
    def setUp(self):
        """Create a GitConfig object using the test.gitconfig fixture.
        """
        config_fixture = fixture('test.gitconfig')
        self.config = git_config.GitConfig(config_fixture)

    def test_GetString_with_empty_config_values(self):
        """
        Test config entries with no value.

        [section]
            empty

        """
        val = self.config.GetString('section.empty')
        self.assertEqual(val, None)

    def test_GetString_with_true_value(self):
        """
        Test config entries with a string value.

        [section]
            nonempty = true

        """
        val = self.config.GetString('section.nonempty')
        self.assertEqual(val, 'true')

    def test_GetString_from_missing_file(self):
        """
        Test missing config file
        """
        config_fixture = fixture('not.present.gitconfig')
        config = git_config.GitConfig(config_fixture)
        val = config.GetString('empty')
        self.assertEqual(val, None)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = trace
#
# Copyright (C) 2008 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
REPO_TRACE = 'REPO_TRACE'

try:
  _TRACE = os.environ[REPO_TRACE] == '1'
except KeyError:
  _TRACE = False

def IsTrace():
  return _TRACE

def SetTrace():
  global _TRACE
  _TRACE = True

def Trace(fmt, *args):
  if IsTrace():
    print >>sys.stderr, fmt % args

########NEW FILE########
