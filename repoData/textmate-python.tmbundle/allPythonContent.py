__FILENAME__ = pycheckmate
#!/usr/bin/env python
# encoding: utf-8
#
# PyCheckMate, a PyChecker output beautifier for TextMate.
# Copyright (c) Jay Soffian, 2005. <jay at soffian dot org>
# Inspired by Domenico Carbotta's PyMate.
#
# License: Artistic.
#
# Usage:
# - Out of the box, pycheckmate.py will perform only a basic syntax check
#   by attempting to compile the python code.
# - Install PyChecker or PyFlakes for more extensive checking. If both are
#   installed, PyChecker will be used.
# - TM_PYCHECKER may be set to control which checker is used. Set it to just
#   "pychecker", "pyflakes", "pep8", "flake8", or "pylint", or "frosted" to
#   locate these programs in the default python bin directory or to a full
#   path if the checker program is installed elsewhere.
# - If for some reason you want to use the built-in sytax check when either
#   pychecker or pyflakes are installed, you may set TM_PYCHECKER to
#   "builtin".

from __future__ import absolute_import, print_function

import os
import re
import sys
import traceback
from cgi import escape
from select import select

__version__ = "1.2"


if sys.version_info < (3, 0):
    from urllib import quote
else:
    from urllib.parse import quote

###
### Constants
###

PYCHECKER_URL = "http://pychecker.sourceforge.net/"
PYFLAKES_URL = "http://divmod.org/projects/pyflakes"
PYLINT_URL = "http://www.logilab.org/857"
PEP8_URL = "http://pypi.python.org/pypi/pep8"
FLAKE8_URL = "http://pypi.python.org/pypi/flake8/"

# patterns to match output of checker programs
PYCHECKER_RE = re.compile(r"^(.*?\.pyc?):(\d+):\s+(.*)$")

# careful editing these, they are format strings
TXMT_URL1_FORMAT = r"txmt://open?url=file://%s&line=%s"
TXMT_URL2_FORMAT = r"txmt://open?url=file://%s&line=%s&column=%s"
HTML_HEADER_FORMAT = r"""<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>PyCheckMate %s</title>
<style type="text/css">
<!--

body {
  background-color: #D8E2F1;
  margin: 0;
}

div#body {
  border-style: dotted;
  border-width: 1px 0;
  border-color: #666;
  margin: 10px 0;
  padding: 10px;
  background-color: #C9D9F0;
}

div#output{
  padding: 0;
  margin: 0;
  font-family: Monaco;
  font-size: 8pt;
}

strong.title { font-size: 11pt; }
span.stderr { color: red; }
p {margin: 0; padding: 2px 0; }

-->
</style>
</head>
<body>
<div id="body">
<p><strong class="title">%s</strong></p><br>
<div id="output">
"""

HTML_FOOTER = """</div>
</div>
</body>
</html>
"""

###
### Helper classes
###

class Error(Exception):
    pass

class MyPopen(object):
    """Modifed version of standard popen2.Popen class that does what I need.

    Runs command with stdin redirected from /dev/null and monitors its stdout
    and stderr. Each time poll() is called a tuple of (stdout, stderr) is
    returned where stdout and stderr are lists of zero or more lines of output
    from the command. status() should be called before calling poll() and if
    it returns other than -1 then the child has terminated and poll() will
    return no additional output. At that point drain() should be called to
    return the last bit of output.

    As a simplication, readlines() can be called until it returns (None, None)
    """

    try:
        MAXFD = os.sysconf('SC_OPEN_MAX')
    except (AttributeError, ValueError):
        MAXFD = 256

    def __init__(self, cmd):
        stdout_r, stdout_w = os.pipe()
        stderr_r, stderr_w = os.pipe()
        self._status = -1
        self._drained = 0
        self._pid = os.fork()
        if self._pid == 0:
            # child
            devnull = open("/dev/null")
            os.dup2(devnull.fileno(), 0)
            os.dup2(stdout_w, 1)
            os.dup2(stderr_w, 2)
            devnull.close()
            self._run_child(cmd)
        else:
            # parent
            os.close(stdout_w)
            os.close(stderr_w)
            self._stdout = stdout_r
            self._stderr = stderr_r
            self._stdout_buf = ""
            self._stderr_buf = ""

    def _run_child(self, cmd):
        if isinstance(cmd, basestring):
            cmd = ['/bin/sh', '-c', cmd]
        for i in range(3, self.MAXFD):
            try:
                os.close(i)
            except OSError:
                pass
        try:
            os.execvp(cmd[0], cmd)
        finally:
            os._exit(1)

    def status(self):
        """Returns exit status of child or -1 if still running."""
        if self._status < 0:
            try:
                pid, this_status = os.waitpid(self._pid, os.WNOHANG)
                if pid == self._pid:
                    self._status = this_status
            except os.error:
                pass
        return self._status

    def poll(self, timeout=None):
        """Returns (stdout, stderr) from child."""
        bufs = {self._stdout:self._stdout_buf, self._stderr:self._stderr_buf}
        fds, dummy, dummy = select(bufs.keys(), [], [], timeout)
        for fd in fds:
            bufs[fd] += os.read(fd, 4096)
        self._stdout_buf = ""
        self._stderr_buf = ""
        stdout_lines = bufs[self._stdout].splitlines()
        stderr_lines = bufs[self._stderr].splitlines()
        if stdout_lines and not bufs[self._stdout].endswith("\n"):
            self._stdout_buf = stdout_lines.pop()
        if stderr_lines and not bufs[self._stderr].endswith("\n"):
            self._stderr_buf = stderr_lines.pop()
        return (stdout_lines, stderr_lines)

    def drain(self):
        stdout, stderr = [self._stdout_buf], [self._stderr_buf]
        while 1:
            data = os.read(self._stdout, 4096)
            if not data:
                break
            stdout.append(data)
        while 1:
            data = os.read(self._stderr, 4096)
            if not data:
                break
            stderr.append(data)
        self._stdout_buf = ""
        self._stderr_buf = ""
        self._drained = 1
        stdout_lines = ''.join(stdout).splitlines()
        stderr_lines = ''.join(stderr).splitlines()
        return (stdout_lines, stderr_lines)

    def readlines(self):
        if self._drained:
            return None, None
        elif self.status() == -1:
            return self.poll()
        else:
            return self.drain()

    def close(self):
        os.close(self._stdout)
        os.close(self._stderr)

###
### Program code
###

def check_syntax(script_path):
    f = open(script_path, 'r')
    source = ''.join(f.readlines()+["\n"])
    f.close()
    try:
        print("Syntax Errors...<br><br>")
        compile(source, script_path, "exec")
        print("None<br>")
    except SyntaxError as e:
        href = TXMT_URL2_FORMAT % (quote(script_path), e.lineno, e.offset)
        print('<a href="%s">%s:%s</a> %s' % (href,
                                             escape(os.path.basename(script_path)),
                                             e.lineno, e.msg))
    except:
        for line in apply(traceback.format_exception, sys.exc_info()):
            stripped = line.lstrip()
            pad = "&nbsp;" * (len(line) - len(stripped))
            line = escape(stripped.rstrip())
            print('<span class="stderr">%s%s</span><br>' % (pad, line))

def find_checker_program():
    checkers = ["pychecker", "pyflakes", "pylint", "pep8", "flake8", "frosted"]
    tm_pychecker = os.getenv("TM_PYCHECKER")

    opts = filter(None, os.getenv('TM_PYCHECKER_OPTIONS', '').split())

    if tm_pychecker == "builtin":
        return ('', None, "Syntax check only")

    if tm_pychecker is not None:
        checkers.insert(0, tm_pychecker)

    for checker in checkers:
        basename = os.path.split(checker)[1]
        if checker == basename:
            # look for checker in same bin directory as python (might be
            # symlinked)
            bindir = os.path.split(sys.executable)[0]
            checker = os.path.join(bindir, basename)
            if not os.path.isfile(checker):
                # look where python is installed
                checker = os.path.join(sys.prefix, "bin", basename)
            if not os.path.isfile(checker):
                # search the PATH
                p = os.popen("/usr/bin/which '%s'" % basename)
                checker = p.readline().strip()
                p.close()

        if not os.path.isfile(checker):
            continue

        if basename == "pychecker":
            p = os.popen('"%s" -V 2>/dev/null' % (checker))
            version = p.readline().strip()
            status = p.close()
            if status is None and version:
                version = "PyChecker %s" % version
                return (checker, opts, version)

        elif basename == "pylint":
            p = os.popen('"%s" --version 2>/dev/null' % (checker))
            version = p.readline().strip()
            status = p.close()
            if status is None and version:
                version = re.sub('^pylint\s*', '', version)
                version = re.sub(',$', '', version)
                version = "Pylint %s" % version
                opts += ('--output-format=parseable',)
                return (checker, opts, version)

        elif basename == "pyflakes":
            # pyflakes doesn't have a version string embedded anywhere,
            # so run it against itself to make sure it's functional
            p = os.popen('"%s" "%s" 2>&1 >/dev/null' % (checker, checker))
            output = p.readlines()
            status = p.close()
            if status is None and not output:
                return (checker, opts, "PyFlakes")

        elif basename == "pep8":
            p = os.popen('"%s" --version 2>/dev/null' % (checker))
            version = p.readline().strip()
            status = p.close()
            if status is None and version:
                version = "PEP 8 %s" % version
                global PYCHECKER_RE
                PYCHECKER_RE = re.compile(r"^(.*?\.pyc?):(\d+):(?:\d+:)?\s+(.*)$")
                return (checker, opts, version)

        elif basename == "flake8":
            p = os.popen('"%s" --version 2>/dev/null' % (checker))
            version = p.readline().strip()
            status = p.close()
            if status is None and version:
                version = "flake8 %s" % version
                PYCHECKER_RE = re.compile(r"^(.*?\.pyc?):(\d+):(?:\d+:)?\s+(.*)$")
                return (checker, opts, version)

    return ('', None, "Syntax check only")

def run_checker_program(checker_bin, checker_opts, script_path):
    basepath = os.getenv("TM_PROJECT_DIRECTORY")
    cmd = []
    cmd.append(checker_bin)
    if checker_opts:
        cmd.extend(checker_opts)
    cmd.append(script_path)
    p = MyPopen(cmd)
    while 1:
        stdout, stderr = p.readlines()
        if stdout is None:
            break
        for line in stdout:
            line = line.rstrip()
            match = PYCHECKER_RE.search(line)
            if match:
                filename, lineno, msg = match.groups()
                href = TXMT_URL1_FORMAT % (quote(os.path.abspath(filename)),
                                           lineno)
                if basepath is not None and filename.startswith(basepath):
                    filename = filename[len(basepath)+1:]
                # naive linewrapping, but it seems to work well-enough
                if len(filename) + len(msg) > 80:
                    add_br = "<br>&nbsp;&nbsp;"
                else:
                    add_br = " "
                line = '<a href="%s">%s:%s</a>%s%s' % (
                       href, escape(filename), lineno, add_br,
                       escape(msg))
            else:
                line = escape(line)
            print("%s<br>" % line)
        for line in stderr:
            # strip whitespace off front and replace with &nbsp; so that
            # we can allow the browser to wrap long lines but we don't lose
            # leading indentation otherwise.
            stripped = line.lstrip()
            pad = "&nbsp;" * (len(line) - len(stripped))
            line = escape(stripped.rstrip())
            print('<span class="stderr">%s%s</span><br>' % (pad, line))
    print("<br>Exit status: %s" % p.status())
    p.close()

def main(script_path):
    checker_bin, checker_opts, checker_ver = find_checker_program()
    version_string = "PyCheckMate %s &ndash; %s" % (__version__, checker_ver)
    warning_string = ""
    if not checker_bin:
        href_format = \
            "<a href=\"javascript:TextMate.system('open %s', null)\">%s</a>"
        pychecker_url = href_format % (PYCHECKER_URL, "PyChecker")
        pyflakes_url  = href_format % (PYFLAKES_URL, "PyFlakes")
        pylint_url  = href_format % (PYLINT_URL, "Pylint")
        pep8_url = href_format % (PEP8_URL, "PEP 8")
        flake8_url = href_format % (FLAKE8_URL, "flake8")
        warning_string = \
            "<p>Please install %s, %s, %s, %s or %s for more extensive code checking." \
            "</p><br>" % (pychecker_url, pyflakes_url, pylint_url, pep8_url, flake8_url)

    basepath = os.getenv("TM_PROJECT_DIRECTORY")
    if basepath:
        project_dir = os.path.basename(basepath)
        script_name = os.path.basename(script_path)
        title = "%s &mdash; %s" % (escape(script_name), escape(project_dir))
    else:
        title = escape(script_path)

    print(HTML_HEADER_FORMAT % (title, version_string))
    if warning_string:
        print(warning_string)
    if checker_bin:
        run_checker_program(checker_bin, checker_opts, script_path)
    else:
        check_syntax(script_path)
    print(HTML_FOOTER)
    return 0

if __name__ == "__main__":
    if len(sys.argv) == 2:
        sys.exit(main(sys.argv[1]))
    else:
        print("Usage: %s <file.py>" % sys.argv[0], file=sys.stderr)
        sys.exit(1)

########NEW FILE########
__FILENAME__ = browse_pydocs
#!/usr/bin/env python
# kumar.mcmillan at gmail

import os
import sys
import pydoc
import time
from urllib2 import urlopen, URLError
from traceback import format_exc

PORT=9877
URL='http://localhost:%d/' % PORT
UID='pydoc_server_%d' % PORT
OUT_LOG = file('/tmp/%s.log' % UID, 'a+')
ERR_LOG = file('/tmp/%s_error.log' % UID, 'a+', 0)

def browse_docs():
    cmd = 'open %s' % URL
    if os.system(cmd) is not 0:
        raise OSError("failed: %s" % cmd)

def is_serving():
    try:
        urlopen(URL)
        return True
    except URLError:
        return False

def start_serv():
    # Redirect standard file descriptors.
    dev_null = file('/dev/null', 'r')
    sys.stdout.flush()
    sys.stderr.flush()
    
    os.dup2(OUT_LOG.fileno(), sys.stdout.fileno())
    os.dup2(ERR_LOG.fileno(), sys.stderr.fileno())
    os.dup2(dev_null.fileno(), sys.stdin.fileno())
    
    pydoc.serve(PORT)

def info():
    def dd(term, d):
        return '<dt>%s</dt><dd>%s</dd>' % (term, d)
        
    return """
<style type="text/css">
body { color: #fff; }
h2, dt { padding: 1em 0.3em 0.3em 0.3em; }
h2 { background: #7799ee; }
dl { margin: 0; }
dt { text-align: right; width: 5em; background: #ee77aa; float: left; }
dd { background: #ffc8d8; padding-top: 1em; }
dd a { margin-left: 0.5em; }
h2, dd { margin-bottom: 3px; }
dd:after {
    content: "."; 
    display: block; 
    height: 0; 
    clear: both; 
    visibility: hidden;
}
</style>

<h2>Pydoc Server</h2>
<dl>
%s
</dl>""" % "\n".join([
    dd('url', '<a href="%(url)s">%(url)s</a>' % {'url':URL}),
    dd('log', '<a href="file://%(url)s">%(url)s</a>' % {'url':OUT_LOG.name}),
    dd('error log', '<a href="file://%(url)s">%(url)s</a>' % {'url':ERR_LOG.name})])

def wait_for_server(finished):
    timeout, interval, elapsed = 10,1,0
    while not is_serving():
        time.sleep(interval)
        elapsed = elapsed + interval
        if elapsed >= timeout:
            raise RuntimeError('timed out waiting for server!')
    finished()

def main():
    def onserve():
        print info()
        browse_docs()
        
    try:
        if is_serving(): 
            onserve()
            sys.exit(0)
        
        # daemonize with the magical two forks, lifted from:
        # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012
        try:
            pid = os.fork()
            if pid > 0:
                wait_for_server(onserve)
                sys.exit(0)
        except OSError, e: 
            print >>sys.stderr, "fork #1 failed: %s" % (e) 
            raise
    
        os.chdir('/')
        os.setsid()
        os.umask(0)
    
        try:
            pid = os.fork()
            if pid > 0:
                # this is the server's pid
                sys.exit(0)
        except OSError, e: 
            print >>sys.stderr, "fork #2 failed: %s" % (e)
            raise
    
        start_serv()
    except SystemExit, e:
        # don't want this printing a <pre> tag in the TM thread
        raise
    except:
        ERR_LOG.write(format_exc())
        print "<pre>" # so we can read the traceback in the TM thread :)
        raise

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = cleanup_whitespace
#!/usr/bin/env python

import sys
import re

def cleanup_whitespace(filename = None):
   re_blanks = re.compile(r"^\s*$")
   re_indent = re.compile(r"^[ \t]*")
   
   if filename is None:
      lines = sys.stdin.readlines()
   else:
      f = open(filename)
      lines = f.readlines()
      f.close()
   
   for linenum in xrange(len(lines)-1):
      this_line = lines[linenum]
      if re_blanks.search(this_line):
         # search forward for next non-blank line and get its indent
         replacement = None
         for next_line in lines[linenum+1:]:
            match = re_indent.search(next_line)
            if match:
               replacement = match.group(0) + "\n"
               break
         if replacement is None: continue
      else:
         replacement = this_line.rstrip() + "\n"
      if this_line != replacement:
         lines[linenum] = replacement
   
   if filename is None:
      sys.stdout.writelines(lines)
   else:
      f = open(filename, "w")
      f.writelines(lines)
      f.close()

if __name__ == "__main__":
   if len(sys.argv) == 2 and sys.argv[1] != "-":
      cleanup_whitespace(sys.argv[1])
   else:
      cleanup_whitespace()
########NEW FILE########
__FILENAME__ = docmate
# -*- coding: UTF-8 -*-

import re
import sys
from os import system, path, mkdir, environ as env
import cPickle
import urllib2
import inspect
from urlparse import urljoin as _urljoin
import time

# make sure Support/lib is on the path
support_lib = path.join(env["TM_SUPPORT_PATH"], "lib")
if support_lib not in sys.path:
    sys.path.insert(0, support_lib)

import tm_helpers

if "TM_PYTHONDOCS" in env:
    PYTHONDOCS = env["TM_PYTHONDOCS"]
else:
    PYTHONDOCS = "http://docs.python.org"

TIMEOUT = 5 * 60
_PYDOC_PORT = 7400
_PYDOC_URL = "http://localhost:%i/"

prefdir = path.join(env["HOME"], "Library/Preferences/com.macromates.textmate.python")
if not path.exists(prefdir):
    mkdir(prefdir)
hitcount_path = path.join(prefdir, 'docmate_url_hitcount')

def urljoin(base, *fragments):
    for f in fragments:
        base = _urljoin(base, f, allow_fragments=True)
    return base

def accessible(url):
    """ True if the url is accessible. """
    try:
        urllib2.urlopen(url)
        return True
    except urllib2.URLError:
        return False

def pydoc_url():
    """ Return a URL to pydoc for the python returned by tm_helpers.env_python(). """
    python, version = tm_helpers.env_python()
    port = _PYDOC_PORT + version
    url = _PYDOC_URL % port
    return url, port

def launch_pydoc_server():
    server = path.join(env["TM_BUNDLE_SUPPORT"], "DocMate/pydoc_server.py")
    python, version = tm_helpers.env_python()
    url, port = pydoc_url()
    if not accessible(url):
        # launch pydoc.
        system('/usr/bin/nohup %s %s %i %i\
                    1>> /tmp/pydoc.log 2>> /tmp/pydoc.log &' \
                    % (python, tm_helpers.sh_escape(server), port, TIMEOUT))
    return url

def library_docs(word):
    # build a list of matching library docs
    paths = []
    try:
        f = open(path.join(env["TM_BUNDLE_SUPPORT"], 'DocMate/lib.index'))
        index = cPickle.load(f)
    finally:
        f.close()
    word_re = re.compile(r"\b(%s)\b" % re.sub('[^a-zA-Z0-9_\. ]+', '', word))
    matching_keys = [key for key in index if word_re.search(key)]
    for key in matching_keys:
        for desc, url in index[key]:
            paths.append((desc, urljoin(PYTHONDOCS, "lib/", url)))
    return paths

def local_docs(word):
    import pydoc
    try:
        obj, name = pydoc.resolve(word)
    except ImportError:
        return None
    desc = pydoc.describe(obj)
    return [(desc, urljoin(pydoc_url()[0], "%s.html" % word))]

########NEW FILE########
__FILENAME__ = pydoc_server
import os
import time
import pydoc
import new

def serve_until_quit(self):
    import select
    self.quit = False
    while not self.quit:
        rd, wr, ex = select.select([self.socket.fileno()], [], [], 1)
        if rd:
            self.last_request = time.time()
            self.handle_request()

server = None
def serve(port, timeout=0):
    global started, server
    started = 0
    import threading
    def ready(s):
        global started, server
        server = s
        # monkey-patch the serve_until_quit method.
        server.last_request = time.time()
        server.serve_until_quit = new.instancemethod(serve_until_quit, server, server.__class__)
        started = time.time()
    def quit(event=None):
        global server
        server.quit = 1
    threading.Thread(target=pydoc.serve, args=(port, ready)).start()
    while not started:
        time.sleep(0.1)
    while time.time() < server.last_request + timeout:
        time.sleep(timeout)
    quit()

if __name__ == '__main__':
    import sys
    serve(int(sys.argv[1]), int(sys.argv[2]))

########NEW FILE########
__FILENAME__ = sitecustomize
# coding: utf-8
"""
tmhooks.py for PyMate.

This file monkey-patches sys.excepthook to intercept any unhandled
exceptions, format the exception in fancy html, and write them to
a file handle (for instance, sys.stderr).

Also, sys.stdout and sys.stder are wrapped in a utf-8 codec writer.

"""

import sys, os

# remove TM_BUNDLE_SUPPORT from the path.
if os.environ['TM_BUNDLE_SUPPORT'] in sys.path:
  sys.path.remove(os.environ['TM_BUNDLE_SUPPORT'])

# now import local sitecustomize
try:
  import sitecustomize
  if sys.version_info[0] >= 3:
    from imp import reload
  reload(sitecustomize)
except ImportError: pass

import codecs

from os import environ, path, fdopen, popen
from traceback import extract_tb
from cgi import escape
from urllib import quote

# add utf-8 support to stdout/stderr
sys.stdout = codecs.getwriter('utf-8')(sys.stdout);
sys.stderr = codecs.getwriter('utf-8')(sys.stderr);

def tm_excepthook(e_type, e, tb):
    """
    Catch unhandled exceptions, and write the traceback in pretty HTML
    to the file descriptor given by $TM_ERROR_FD.
    """
    # get the file descriptor.
    error_fd = int(str(environ['TM_ERROR_FD']))
    io = fdopen(error_fd, 'wb', 0)
    io.write("<div id='exception_report' class='framed'>\n")
    if isinstance(e_type, str):
        io.write("<p id='exception'><strong>String Exception:</strong> %s</p>\n" % escape(e_type))
    elif e_type is SyntaxError:
        # if this is a SyntaxError, then tb == None
        filename, line_number, offset, text = e.filename, e.lineno, e.offset, e.text
        url, display_name = '', 'untitled'
        if not offset: offset = 0
        io.write("<pre>%s\n%s</pre>\n" % (escape(e.text).rstrip(), "&nbsp;" * (offset-1) + "↑"))
        io.write("<blockquote><table border='0' cellspacing='0' cellpadding='0'>\n")
        if filename and path.exists(filename):
            url = "&url=file://%s" % quote(filename)
            display_name = path.basename(filename)
        if filename == '<string>': # exception in exec'd string.
            display_name = 'exec'
        io.write("<tr><td><a class='near' href='txmt://open?line=%i&column=%i%s'>" %
                                                    (line_number, offset, url))
        io.write("line %i, column %i" % (line_number, offset))
        io.write("</a></td>\n<td>&nbsp;in <strong>%s</strong></td></tr>\n" %
                                            (escape(display_name)))
        io.write("</table></blockquote></div>")
    else:
        message = ""
        if e.args:
            # For some reason the loop below works, but using either of the lines below
            # doesn't
            # message = ", ".join([str(arg) for arg in e.args])
            # message = ", ".join([unicode(arg) for arg in e.args])
            message = repr(e.args[0])
            if len(e.args) > 1:
                for arg in e.args[1:]:
                    message += ", %s" % repr(arg)
        if isinstance(message, unicode):
            io.write("<p id='exception'><strong>%s:</strong> %s</p>\n" %
                                    (e_type.__name__, escape(message).encode("utf-8")))
        else:
            io.write("<p id='exception'><strong>%s:</strong> %s</p>\n" %
                                    (e_type.__name__, escape(message)))
    if tb: # now we write out the stack trace if we have a traceback
        io.write("<blockquote><table border='0' cellspacing='0' cellpadding='0'>\n")
        for trace in extract_tb(tb):
            filename, line_number, function_name, text = trace
            url, display_name = '', 'untitled'
            if filename and path.exists(filename):
                url = "&url=file://%s" % quote(path.abspath(filename))
                display_name = path.basename(filename)
            io.write("<tr><td><a class='near' href='txmt://open?line=%i%s'>" %
                                                            (line_number, url))
            if filename == '<string>': # exception in exec'd string.
                display_name = 'exec'
            if function_name and function_name != "?":
                if function_name == '<module>':
                    io.write("<em>module body</em>")
                else:
                    io.write("function %s" % escape(function_name))
            else:
                io.write('<em>at file root</em>')
            io.write("</a> in <strong>%s</strong> at line %i</td></tr>\n" %
                                                (escape(display_name).encode("utf-8"), line_number))
            io.write("<tr><td><pre class=\"snippet\">%s</pre></tr></td>" % text)
        io.write("</table></blockquote></div>")
    if e_type is UnicodeDecodeError:
        io.write("<p id='warning'><strong>Warning:</strong> It seems that you are trying to print a plain string containing unicode characters.\
            In many contexts, setting the script encoding to UTF-8 and using plain strings with non-ASCII will work,\
            but it is fragile. See also <a href='http://macromates.com/ticket/show?ticket_id=502C2FDD'>this ticket.</a><p />\
            <p id='warning'>You can fix this by changing the string to a unicode string using the 'u' prefix (e.g. u\"foobar\").</p>")
    io.flush()

sys.excepthook = tm_excepthook

########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python
# encoding: utf-8
"""
${TM_NEW_FILE_BASENAME}.py

Created by ${TM_FULLNAME} on ${TM_DATE}.
Copyright (c) ${TM_YEAR} ${TM_ORGANIZATION_NAME}. All rights reserved.
"""

import sys
import os
import unittest


class ${TM_NEW_FILE_BASENAME}:
	def __init__(self):
		pass


class ${TM_NEW_FILE_BASENAME}Tests(unittest.TestCase):
	def setUp(self):
		pass


if __name__ == '__main__':
	unittest.main()
########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python
# encoding: utf-8
"""
${TM_NEW_FILE_BASENAME}.py

Created by ${TM_FULLNAME} on ${TM_DATE}.
Copyright (c) ${TM_YEAR} ${TM_ORGANIZATION_NAME}. All rights reserved.
"""

import sys
import os


def main():
	pass


if __name__ == '__main__':
	main()


########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python
# encoding: utf-8
"""
${TM_NEW_FILE_BASENAME}.py

Created by ${TM_FULLNAME} on ${TM_DATE}.
Copyright (c) ${TM_YEAR} ${TM_ORGANIZATION_NAME}. All rights reserved.
"""

import sys
import getopt


help_message = '''
The help message goes here.
'''


class Usage(Exception):
	def __init__(self, msg):
		self.msg = msg


def main(argv=None):
	if argv is None:
		argv = sys.argv
	try:
		try:
			opts, args = getopt.getopt(argv[1:], "ho:v", ["help", "output="])
		except getopt.error, msg:
			raise Usage(msg)
	
		# option processing
		for option, value in opts:
			if option == "-v":
				verbose = True
			if option in ("-h", "--help"):
				raise Usage(help_message)
			if option in ("-o", "--output"):
				output = value
	
	except Usage, err:
		print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
		print >> sys.stderr, "\t for help use --help"
		return 2


if __name__ == "__main__":
	sys.exit(main())

########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python
# encoding: utf-8
"""
${TM_NEW_FILE_BASENAME}.py

Created by ${TM_FULLNAME} on ${TM_DATE}.
Copyright (c) ${TM_YEAR} ${TM_ORGANIZATION_NAME}. All rights reserved.
"""

import unittest


class ${TM_NEW_FILE_BASENAME}(unittest.TestCase):
	def setUp(self):
		pass

    
if __name__ == '__main__':
	unittest.main()
########NEW FILE########
