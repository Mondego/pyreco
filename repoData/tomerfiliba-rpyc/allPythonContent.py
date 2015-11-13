__FILENAME__ = rpycd
#!/usr/bin/env python
from __future__ import with_statement
import daemon
import lockfile
import sys
import signal
from rpyc.utils.server import ThreadedServer, ForkingServer
from rpyc.core.service import SlaveService
from rpyc.lib import setup_logger
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

server = None

def start():
    global server
    
    conf = ConfigParser()
    conf.read('rpycd.conf')
    
    mode = conf.get("rpycd", "mode").lower()
    if mode == "threaded":
        factory = ThreadedServer
    elif mode == "forking":
        factory = ForkingServer
    else:
        raise ValueError("Invalid mode %r" % (mode,))
    
    setup_logger(conf.getboolean("rpycd", "quiet"), conf.get("rpycd", "logfile"))
    
    server = factory(SlaveService, hostname = conf.get("rpycd", "host"), 
        port = conf.getint("rpycd", "port"), reuse_addr = True)
    server.start()

def reload(*args):
    server.close()
    start()

def stop(*args):
    server.close()
    sys.exit()


if __name__ == "__main__":
    with daemon.DaemonContext(
            pidfile = lockfile.FileLock('/var/run/rpydc.pid'),
            signal_map = {signal.SIGTERM: stop, signal.SIGHUP: reload}):
        start()


########NEW FILE########
__FILENAME__ = rpyc_classic
#!/usr/bin/env python
"""
classic rpyc server (threaded, forking or std) running a SlaveService
usage:
    rpyc_classic.py                         # default settings
    rpyc_classic.py -m forking -p 12345     # custom settings

    # ssl-authenticated server (keyfile and certfile are required)
    rpyc_classic.py --ssl-keyfile keyfile.pem --ssl-certfile certfile.pem --ssl-cafile cafile.pem
"""
import sys
import os
import rpyc
from plumbum import cli
from rpyc.utils.server import ThreadedServer, ForkingServer, OneShotServer
from rpyc.utils.classic import DEFAULT_SERVER_PORT, DEFAULT_SERVER_SSL_PORT
from rpyc.utils.registry import REGISTRY_PORT
from rpyc.utils.registry import UDPRegistryClient, TCPRegistryClient
from rpyc.utils.authenticators import SSLAuthenticator
from rpyc.lib import setup_logger
from rpyc.core import SlaveService


class ClassicServer(cli.Application):
    mode = cli.SwitchAttr(["-m", "--mode"], cli.Set("threaded", "forking", "stdio", "oneshot"),
        default = "threaded", help = "The serving mode (threaded, forking, or 'stdio' for "
        "inetd, etc.)")
    
    port = cli.SwitchAttr(["-p", "--port"], cli.Range(0, 65535), default = None, 
        help="The TCP listener port (default = %s, default for SSL = %s)" % 
            (DEFAULT_SERVER_PORT, DEFAULT_SERVER_SSL_PORT), group = "Socket Options")
    host = cli.SwitchAttr(["--host"], str, default = "", help = "The host to bind to. "
        "The default is INADDR_ANY", group = "Socket Options")
    ipv6 = cli.Flag(["--ipv6"], help = "Enable IPv6", group = "Socket Options")
    
    logfile = cli.SwitchAttr("--logfile", str, default = None, help="Specify the log file to use; "
        "the default is stderr", group = "Logging")
    quiet = cli.Flag(["-q", "--quiet"], help = "Quiet mode (only errors will be logged)", 
        group = "Logging")
    
    ssl_keyfile = cli.SwitchAttr("--ssl-keyfile", cli.ExistingFile,
        help = "The keyfile to use for SSL. Required for SSL", group = "SSL", 
        requires = ["--ssl-certfile"])
    ssl_certfile = cli.SwitchAttr("--ssl-certfile", cli.ExistingFile,
        help = "The certificate file to use for SSL. Required for SSL", group = "SSL",
        requires = ["--ssl-keyfile"])
    ssl_cafile = cli.SwitchAttr("--ssl-cafile", cli.ExistingFile,
        help = "The certificate authority chain file to use for SSL. Optional; enables client-side " 
        "authentication", group = "SSL", requires = ["--ssl-keyfile"])
    
    auto_register = cli.Flag("--register", help = "Asks the server to attempt registering with "
        "a registry server. By default, the server will not attempt to register", 
        group = "Registry")
    registry_type = cli.SwitchAttr("--registry-type", cli.Set("UDP", "TCP"), 
        default = "UDP", help="Specify a UDP or TCP registry", group = "Registry")
    registry_port = cli.SwitchAttr("--registry-port", cli.Range(0, 65535), default=REGISTRY_PORT, 
        help = "The registry's UDP/TCP port", group = "Registry")
    registry_host = cli.SwitchAttr("--registry-host", str, default = None,
        help = "The registry host machine. For UDP, the default is 255.255.255.255; "
        "for TCP, a value is required", group = "Registry")

    def main(self):
        if self.registry_type == "UDP":
            if self.registry_host is None:
                self.registry_host = "255.255.255.255"
            self.registrar = UDPRegistryClient(ip = self.registry_host, port = self.registry_port)
        else:
            if self.registry_host is None:
                raise ValueError("With TCP registry, you must specify --registry-host")
            self.registrar = TCPRegistryClient(ip = self.registry_host, port = self.registry_port)

        if self.ssl_keyfile:
            self.authenticator = SSLAuthenticator(self.ssl_keyfile, self.ssl_certfile, 
                self.ssl_cafile)
            default_port = DEFAULT_SERVER_SSL_PORT
        else:
            self.authenticator = None
            default_port = DEFAULT_SERVER_PORT
        if self.port is None:
            self.port = default_port

        setup_logger(self.quiet, self.logfile)
    
        if self.mode == "threaded":
            self._serve_mode(ThreadedServer)
        elif self.mode == "forking":
            self._serve_mode(ForkingServer)
        elif self.mode == "oneshot":
            self._serve_oneshot()
        elif self.mode == "stdio":
            self._serve_stdio()
    
    def _serve_mode(self, factory):
        t = factory(SlaveService, hostname = self.host, port = self.port, 
            reuse_addr = True, ipv6 = self.ipv6, authenticator = self.authenticator, 
            registrar = self.registrar, auto_register = self.auto_register)
        t.start()

    def _serve_oneshot(self):
        t = OneShotServer(SlaveService, hostname = self.host, port = self.port, 
            reuse_addr = True, ipv6 = self.ipv6, authenticator = self.authenticator, 
            registrar = self.registrar, auto_register = self.auto_register)
        sys.stdout.write("rpyc-oneshot\n")
        sys.stdout.write("%s\t%s\n" % (t.host, t.port))
        sys.stdout.flush()
        t.start()

    def _serve_stdio(self):
        origstdin = sys.stdin
        origstdout = sys.stdout
        sys.stdin = open(os.devnull, "r")
        sys.stdout = open(os.devnull, "w")
        sys.stderr = open(os.devnull, "w")
        conn = rpyc.classic.connect_pipes(origstdin, origstdout)
        try:
            try:
                conn.serve_all()
            except KeyboardInterrupt:
                print( "User interrupt!" )
        finally:
            conn.close()


if __name__ == "__main__":
    ClassicServer.run()


########NEW FILE########
__FILENAME__ = rpyc_registry
#!/usr/bin/env python
"""
The registry server listens to broadcasts on UDP port 18812, answering to
discovery queries by clients and registering keepalives from all running
servers. In order for clients to use discovery, a registry service must
be running somewhere on their local network.
"""
from plumbum import cli
from rpyc.utils.registry import REGISTRY_PORT, DEFAULT_PRUNING_TIMEOUT
from rpyc.utils.registry import UDPRegistryServer, TCPRegistryServer
from rpyc.lib import setup_logger


class RegistryServer(cli.Application):
    mode = cli.SwitchAttr(["-m", "--mode"], cli.Set("UDP", "TCP"), default = "UDP",
        help = "Serving mode")
    
    ipv6 = cli.Flag(["-6", "--ipv6"], help="use ipv6 instead of ipv4")

    port = cli.SwitchAttr(["-p", "--port"], cli.Range(0, 65535), default = REGISTRY_PORT, 
        help = "The UDP/TCP listener port")
    
    logfile = cli.SwitchAttr(["--logfile"], str, default = None, 
        help = "The log file to use; the default is stderr")
    
    quiet = cli.SwitchAttr(["-q", "--quiet"], help = "Quiet mode (only errors are logged)")
    
    pruning_timeout = cli.SwitchAttr(["-t", "--timeout"], int, 
        default = DEFAULT_PRUNING_TIMEOUT, help = "Set a custom pruning timeout (in seconds)")

    def main(self):
        if self.mode == "UDP":
            server = UDPRegistryServer(host = '::' if self.ipv6 else '0.0.0.0', port = self.port, 
                pruning_timeout = self.pruning_timeout)
        elif self.mode == "TCP":
            server = TCPRegistryServer(port = self.port, pruning_timeout = self.pruning_timeout)
        setup_logger(self.quiet, self.logfile)
        server.start()


if __name__ == "__main__":
    RegistryServer.run()


########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python
from __future__ import print_function
from plumbum import local, cli
from plumbum.utils import delete
from rpyc.version import version_string

class Build(cli.Application):
    publish = cli.Flag("--publish")
    
    def main(self):
        delete("build", "dist", "MANIFEST", local.cwd // "*.egg-info")

        # generate zip, tar.gz, and win32 installer
        if self.publish:
            print("registering...")
            local.python("setup.py", "register")
            print("uploading zip and tar.gz")
            local.python("setup.py", "sdist", "--formats=zip,gztar", "upload")
            print("uploading win installer")
            local.python("setup.py", "bdist_wininst", "--plat-name=win32", "upload")
    
            # upload to sourceforge
            print("uploading to sourceforge")
            dst = "gangesmaster,rpyc@frs.sourceforge.net:/home/frs/project/r/rp/rpyc/main/%s/" % (version_string,)
            local["rsync"]("-rv", "dist/", dst)
        else:
            local.python("setup.py", "sdist", "--formats=zip,gztar")
            local.python("setup.py", "bdist_wininst", "--plat-name=win32")
    
        delete("build", local.cwd // "*.egg-info")
        print("Built", [f.basename for f in local.cwd / "dist"])

if __name__ == "__main__":
    Build.run()


########NEW FILE########
__FILENAME__ = server
from __future__ import with_statement
from rpyc import Service, async
from rpyc.utils.server import ThreadedServer
from threading import RLock


USERS_DB = {
    "foo" : "bar",
    "spam" : "bacon",
    "eggs" : "viking",
}
broadcast_lock = RLock()
tokens = set()


class UserToken(object):
    def __init__(self, name, callback):
        self.name = name
        self.stale = False
        self.callback = callback
        self.broadcast("* Hello %s *" % (self.name,))
        tokens.add(self)

    def exposed_say(self, message):
        if self.stale:
            raise ValueError("User token is stale")
        self.broadcast("[%s] %s" % (self.name, message))

    def exposed_logout(self):
        if self.stale:
            return
        self.stale = True
        self.callback = None
        tokens.discard(self)
        self.broadcast("* Goodbye %s *" % (self.name,))

    def broadcast(self, text):
        global tokens
        stale = set()
        with broadcast_lock:
            for tok in tokens:
                try:
                    tok.callback(text)
                except:
                    stale.add(tok)
            tokens -= stale


class ChatService(Service):
    def on_connect(self):
        self.token = None

    def on_disconnect(self):
        if self.token:
            self.token.exposed_logout()

    def exposed_login(self, username, password, callback):
        if self.token and not self.token.stale:
            raise ValueError("already logged in")
        if username in USERS_DB and password == USERS_DB[username]:
            self.token = UserToken(username, async(callback))
            return self.token
        else:
            raise ValueError("wrong username or password")


if __name__ == "__main__":
    t = ThreadedServer(ChatService, port = 19912)
    t.start()


########NEW FILE########
__FILENAME__ = client
import rpyc
import time
import os


filename = "/tmp/floop.bloop"
if os.path.exists(filename):
    os.remove(filename)

f = open(filename, "w")
conn = rpyc.connect("localhost", 18871)
bgsrv = rpyc.BgServingThread(conn)  # create a bg thread to process incoming events

def on_file_changed(oldstat, newstat):
    print( "file changed")
    print( "    old stat: %s" % (oldstat,))
    print( "    new stat: %s" % (newstat,))

mon = conn.root.FileMonitor(filename, on_file_changed) # create a filemon

print( "wait a little for the filemon to have a look at the original file")
time.sleep(2)

print( "change file size")
f.write("shmoop") # change size
f.flush()
time.sleep(2)

print( "change size again")
f.write("groop") # change size
f.flush()
time.sleep(2)

mon.stop()
bgsrv.stop()
conn.close()


########NEW FILE########
__FILENAME__ = server
import rpyc
import os
import time
from threading import Thread

class FileMonitorService(rpyc.Service):
    class exposed_FileMonitor(object):
        def __init__(self, filename, callback, interval = 1):
            self.filename = filename
            self.interval = interval
            self.last_stat = None
            self.callback = rpyc.async(callback)   # make the callback async
            self.active = True
            self.thread = Thread(target = self.work)
            self.thread.start()
        def exposed_stop(self):
            self.active = False
            self.thread.join()
        def work(self):
            while self.active:
                stat = os.stat(self.filename)
                if self.last_stat is not None and self.last_stat != stat:
                    self.callback(self.last_stat, stat)
                self.last_stat = stat
                time.sleep(self.interval)


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    ThreadedServer(FileMonitorService, port = 18871).start()


########NEW FILE########
__FILENAME__ = mount.rpycfs
# requires fuse bindings for python
import fuse


class RPyCFS(fuse.Fuse):
    def __init__(self, conn, mountpoint):
        self.conn = conn
        fuse.Fuse.__init__(self, mountpoint)


########NEW FILE########
__FILENAME__ = rpycfsd



########NEW FILE########
__FILENAME__ = service
import rpyc


class RemoteFSService(rpyc.Service):
    def open(self, filename, mode = "r"):
        pass
    def listdir(self, path):
        pass
    def mkdir(self, path):
        pass
    def stat(self, path):
        pass
    def rmdir(self, path):
        pass


########NEW FILE########
__FILENAME__ = splits
import sys
import rpyc
from plumbum import SshMachine
from rpyc.utils.zerodeploy import DeployedServer
from rpyc.utils.splitbrain import splitbrain

mach = SshMachine("192.168.1.117")

print sys.platform

with DeployedServer(mach) as dep:
    conn = dep.classic_connect()
    print conn.modules.sys.platform
    
    try:
        import posix
    except ImportError as ex:
        print ex
    
    with splitbrain(conn):
        import posix
        print posix.stat("/boot")

    print posix




########NEW FILE########
__FILENAME__ = client
import rpyc


c = rpyc.connect_by_service("TIME")
print( "server's time is", c.root.get_time())


########NEW FILE########
__FILENAME__ = server
from rpyc.utils.server import ThreadedServer
from time_service import TimeService


if __name__ == "__main__":
    s = ThreadedServer(TimeService)
    s.start()


########NEW FILE########
__FILENAME__ = time_service
import time
from rpyc import Service


class TimeService(Service):
    def exposed_get_utc(self):
        return time.time()

    def exposed_get_time(self):
        return time.ctime()


########NEW FILE########
__FILENAME__ = safegtk
"""
this class exposes only the gtk constants and some of the "safe" classes.
we don't want the server to open pop-ups on the client, so we won't expose
Window() et al.
"""
import pygtk
pygtk.require('2.0')
import gtk


safe_gtk_classes = set([
    "Box", "VBox", "HBox", "Frame", "Entry", "Button", "ScrolledWindow",
    "TextView", "Label",
])

class SafeGTK(object):
    for _name in dir(gtk):
        if _name in safe_gtk_classes or _name.isupper():
            exec "exposed_%s = gtk.%s" % (_name, _name)
    del _name

SafeGTK = SafeGTK()


########NEW FILE########
__FILENAME__ = server
import rpyc
from rpyc.utils.server import ThreadedServer
import time
import threading


class Web8Service(rpyc.Service):
    def exposed_get_page(self, gtk, content, page):
        self.gtk = gtk
        self.content = content
        page = page.replace(" ", "_").lower()
        pagefunc = getattr(self, "page_%s" % (page,), None)
        if pagefunc:
            pagefunc()
        else:
            lbl1 = self.gtk.Label("Page %r does not exist" % (page,))
            lbl1.show()
            self.content.pack_start(lbl1)

    def page_main(self):
        counter = [0]

        lbl1 = self.gtk.Label("Hello mate, this is the main page")
        lbl1.show()
        self.content.pack_start(lbl1)

        def on_btn1_clicked(src):
            counter[0] += 1
            lbl2.set_text("You have clicked the button %d times" % (counter[0],))

        btn1 = self.gtk.Button("Add 1")
        btn1.connect("clicked", on_btn1_clicked)
        btn1.show()
        self.content.pack_start(btn1)

        lbl2 = self.gtk.Label("You have clicked the button 0 times")
        lbl2.show()
        self.content.pack_start(lbl2)

        def on_btn2_clicked(src):
            self._conn.root.navigate("/hello_world")

        btn2 = self.gtk.Button("Go to the 'hello world' page")
        btn2.connect("clicked", on_btn2_clicked)
        btn2.show()
        self.content.pack_start(btn2)

        active = [False]

        def bg_timer_thread():
            while active[0]:
                rpyc.async(lbl3.set_text)("Server time is: %s" % (time.ctime(),))
                time.sleep(1)

        bg_thread = [None]

        def on_btn3_clicked(src):
            if btn3.get_label() == "Start timer":
                bg_thread[0] = threading.Thread(target = bg_timer_thread)
                active[0] = True
                bg_thread[0].start()
                btn3.set_label("Stop timer")
            else:
                active[0] = False
                bg_thread[0].join()
                btn3.set_label("Start timer")

        btn3 = self.gtk.Button("Start timer")
        btn3.connect("clicked", on_btn3_clicked)
        btn3.show()
        self.content.pack_start(btn3)

        lbl3 = self.gtk.Label("Server time is: ?")
        lbl3.show()
        self.content.pack_start(lbl3)

    def page_hello_world(self):
        lbl = self.gtk.Label("Hello world!")
        lbl.show()
        self.content.pack_start(lbl)




if __name__ == "__main__":
    t = ThreadedServer(Web8Service, port = 18833)
    t.start()


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# RPyC documentation build configuration file, created by
# sphinx-quickstart on Sat May 28 10:06:21 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'RPyC'
copyright = u'%d, Tomer Filiba, licensed under Attribution-ShareAlike 3.0' % (time.gmtime().tm_year,)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
from rpyc.version import version_string, release_date
version = version_string
# The full version, including alpha/beta/rc tags.
release = version_string + "/" + release_date

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

autodoc_member_order = "bysource"


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'agogo'
html_theme = 'haiku'
#html_theme_path = ["_themes"]


# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {"full_logo" : True}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = "%s v%s Docs" % (project, version)
#html_title = project
html_title = "RPyC"

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "_static/banner.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = "rpyc3-logo-tiny.ico"

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
html_domain_indices = False

# If false, no index is generated.
html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'RPyCdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'RPyC.tex', u'RPyC Documentation',
   u'Tomer Filiba', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'rpyc', u'RPyC Documentation',
     [u'Tomer Filiba'], 1)
]

########NEW FILE########
__FILENAME__ = issue14
import rpyc
import os
from contextlib import contextmanager

class Number(object):
    def __init__(self,number):
        self.number=number

def f(number):
    print( number.number)


@contextmanager
def ASYNC(func):
    wrapper = rpyc.async(func)
    yield wrapper

if __name__ == "__main__":
    conn = rpyc.classic.connect("localhost")
    conn.modules.sys.path.append(os.path.dirname(__file__))

    mod = conn.modules["issue14"]
    n = Number(999)
    #f = rpyc.async(mod.f)(n)
    #print( f )
    #print( f.value )

    f2 = rpyc.async(mod.f)
    res = f2(n)
    print res.value
    
    with ASYNC(mod.f) as f2:
        res = f2(n)
        print res.value



########NEW FILE########
__FILENAME__ = issue26
import rpyc

class AService(rpyc.Service):
    class exposed_A(object):
        @classmethod
        def exposed_foo(cls, a, b):
            return 17 * a + b

if __name__ == "__main__":
    with rpyc.connect_thread(remote_service = AService) as conn:
        print( conn.root.A.foo(1, 2))


########NEW FILE########
__FILENAME__ = issue32
import rpyc
import time

c = rpyc.classic.connect("localhost")
t = rpyc.BgServingThread(c)

start = time.time()
for i in range(100):
    c.execute("newObj = %d" % (i))
stop = time.time()
print "added %d simple objects one by one, %f seconds" % (100, stop - start)

t.stop()


########NEW FILE########
__FILENAME__ = nonrpyc_client
import socket
import ssl

for i in range(5000):
    if i % 100 == 0:
        print i
    sock = socket.socket()
    sock.connect(("localhost", 13388))
    sock2 = ssl.wrap_socket(sock, server_side = False, keyfile = 'cert.key', 
        certfile = 'cert.crt', cert_reqs = ssl.CERT_NONE, ca_certs = None, 
        ssl_version = ssl.PROTOCOL_TLSv1)
    
    for text in ["hello world", "foobar", "spam and eggs"]:
        sock2.send(text)
        data = sock2.recv(1000)
        assert data == text
    #sock.close()


########NEW FILE########
__FILENAME__ = nonrpyc_server
import socket
import select
import ssl
import threading
import time

files = [open("/tmp/rpyc-test-%d" % (i,), "w") for i in range(1000)]
sockets = [socket.socket() for i in range(100)]

listener = socket.socket()
assert listener.fileno() > 1024

listener.bind(("localhost", 13388))
listener.listen(10)

def handle_sock(s):
    s2 = ssl.wrap_socket(s, server_side = True, keyfile = 'cert.key', certfile = 'cert.crt', 
        cert_reqs = ssl.CERT_NONE, ca_certs = None, ssl_version = ssl.PROTOCOL_TLSv1)
    select.select([s2], [], [], 1)
    for i in range(3):
        data = s2.recv(1000)
        s2.send(data)
    time.sleep(1)
    #s2.close()

while True:
    s, _ = listener.accept()
    assert s.fileno() > 1024
    t = threading.Thread(target = handle_sock, args = (s,))
    t.start()




########NEW FILE########
__FILENAME__ = rpyc_client
import rpyc

#
# with explicit closing
#
for i in range(5000):
    #if i % 100 == 0:
    #    print i
    c = rpyc.ssl_connect("localhost", 13388, keyfile = "cert.key", certfile = "cert.crt")
    print i, c.fileno()
    #c = rpyc.connect("localhost", 13388)
    assert c.root.foo() == 18
    c.close()

print
print "finished (1/2)"

#
# without explicit closing
#
for i in range(5000):
    if i % 100 == 0:
        print i
    c = rpyc.ssl_connect("localhost", 13388, keyfile = "cert.key", certfile = "cert.crt")
    #c = rpyc.connect("localhost", 13388)
    assert c.root.foo() == 18
    #c.close()

print
print "finished (2/2)"


########NEW FILE########
__FILENAME__ = rpyc_server
import rpyc


class MyService(rpyc.Service):
    def exposed_foo(self):
        return 18



if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    from rpyc.utils.authenticators import SSLAuthenticator
    server = ThreadedServer(MyService, port = 13388, 
        authenticator = SSLAuthenticator("cert.key", "cert.crt"),
    )
    server.start()

########NEW FILE########
__FILENAME__ = issue63_client
import rpyc
import time

count = 0

def callbackFunc(x):
    global count
    count += 1
    print x, time.time()

if __name__ == "__main__":
    conn = rpyc.connect("localhost", 12000)
    #rpyc.BgServingThread.SERVE_INTERVAL = 0.01
    rpyc.BgServingThread.SLEEP_INTERVAL = 0.0001
    bgsrv = rpyc.BgServingThread(conn)

    test = conn.root.RemoteCallbackTest(callbackFunc)
    print test
    test.start()
    print "doing other things while the callback is being called"
    while count < 100:
        time.sleep(0.1)
    print "done"



########NEW FILE########
__FILENAME__ = issue63_server
import threading
import rpyc


def run_something(callback):
    for i in range(100):
        callback(i)

class MyService(rpyc.Service):
    def on_connect(self):
        print "hi", self._conn._config["endpoints"][1]
    def on_disconnect(self):
        print "bye", self._conn._config["endpoints"][1]
    
    class exposed_RemoteCallbackTest(object):
        def __init__(self, callback):
            self.callback = callback
        def start(self):
            thd = threading.Thread(target = run_something, args = (self.callback,))
            thd.start()


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer
    myServerObj = ThreadedServer(MyService, port=12000, protocol_config={"allow_public_attrs":True})
    myServerObj.start()


########NEW FILE########
__FILENAME__ = issue8_client
import rpyc 

conn = rpyc.connect ("localhost", 18861) 

store = conn.root.store 
Order = conn.root.Order 
estrella_levante = conn.root.estrella_levante #beer supplier 
client = conn.root.client 
Product = conn.root.Product 

def show_reserved_products (product):  #callback 
    print 'You have reserved %s' %  product 

#Product.reserveds is the py-notify signal that is thrown when you 
# output a product from thee store 
conn.root.connect (Product.reserveds, show_reserved_products) 

p = store.output ('quinto', estrella_levante) #store.output gives me a Product object
print "@@", type(p), p
order = Order (client) 
order.add_product (p)      #  <---------- this is the interesting moment 
                           #  we pass as argument a Product object 

conn.close ()


########NEW FILE########
__FILENAME__ = issue8_server
#server: please, pay attention at line 'print type(product)' inside 
#Order in method add_product 
#we will see Order and not Product class 
#------------------------------------- 
from itertools import count 
from datetime import datetime 
from notify.all import * 
import rpyc 

class Supplier(object): 
    def __init__(self, name): 
        self.name = name 

    def __repr__(self): 
        return 'Supplier: %s' % self.name 

class Product(object): 
    reserveds = Signal() #when a product is set reserved, we throw this signal 
    exposed_reserveds = reserveds 

    def __init__(self, name, supplier, id): 
        self.name = name 
        self.supplier = supplier 
        self.id = id 
        self.reserved = 'N' 

    def set_reserved (self): 
        self.reserved = 'Y' 
        Product.reserveds(self)  #notify the observers 

    def __repr__(self): 
        return '<Product: %s, %s, Id: %s>' % (self.name, self.supplier, self.id) 

class Store(object): 
    def __init__(self, name): 
        self.name = name 
        self._products = [] 

    def input (self, product): 
        self._products.append(product) 

    def output (self, product_name, supplier): 
        for i, p in enumerate(self._products): 
            if p.name == product_name and p.supplier == supplier: 
                ret = self._products.pop(i) 
                ret.set_reserved() 
                return ret 
        raise Exception('There is no: %s, %s' % (product_name, supplier)) 

    exposed_output = output 

    def __repr__(self): 
        ret = 'Store: %s\n' % self.name 
        for p in self._products: 
            ret += '%s\n' % p 
        return ret 

class Client(object): 
    def __init__(self, name): 
        self.name = name 

    def __repr__(self): 
        return 'Client: %s' % self.name 

class Order(object): 
    new_id = count() 

    def __init__(self, client): 
        self.id = Order.new_id.next() 
        self.client = client 
        self.products = [] 
        self.datetime = datetime.now() 

    def add_product(self, product): 
        print type(product)        #  <--------- look at the output: it is not Product but Order class
        print "!!", product 
        self.products.append(product) 

    exposed_add_product = add_product 

    def __repr__(self): 
        ret = ['<Order: %d, %s, Date: %s>' % (self.id, self.client, 
                         self.datetime.strftime('%d-%m-%Y %H:%M'))] 
        for p in self.products: 
            ret.append('\t%s' % p) 
        return '\n'.join(ret) 

#creating some objects 

estrella_levante = Supplier('Estrella Levante') 
store = Store('Trastienda') 
client = Client('Miguel Angel') 

for i in range(5): 
    store.input(Product('quinto', estrella_levante, '#%d' % i)) 
    store.input(Product('tercio', estrella_levante, '#%d' % i)) 

class MyService(rpyc.Service): 
    exposed_store = store 
    exposed_Order = Order 
    exposed_estrella_levante = estrella_levante 
    exposed_client = client 
    exposed_Product = Product 

    def __init__(self, *args): 
        rpyc.Service.__init__(self, *args) 
        self.signal_handler = []        #when registering signal of py-notify with the handler 

    def on_disconnect(self): 
        for s, h in self.signal_handler: 
            s.disconnect(h) 

    # we register py-notify signal with the handler this way, so when 
    # closing we disconnect every connection 
    def exposed_connect(self, signal, handler): 
        handler =  rpyc.async(handler) 
        self.signal_handler.append((signal, handler)) 
        signal.connect(handler) 

    def exposed_disconnect(self, signal, handler): 
        handler =  rpyc.async(handler) # py-notify disconnects passing 
                                       # as argument the handler object, as we connected 
        try: 
            self.signal_handler.remove((signal, handler)) 
            signal.disconnect(handler) 
        except: 
            pass 

if __name__ == "__main__": 
    from rpyc.utils.server import ThreadedServer 
    t = ThreadedServer(MyService, port = 18861) 
    t.start()


########NEW FILE########
__FILENAME__ = issue8_test
import rpyc
import gc

c = rpyc.classic.connect("localhost")
c.execute("""class Foo(object):
    def __init__(self, name):
        self.name = name
    def __del__(self):
        print "%s deleted" % (self.name,)
""")

f1 = c.namespace["Foo"]("f1")
f2 = c.namespace["Foo"]("f2")
f3 = c.namespace["Foo"]("f3")

del f1
del f2
gc.collect()

raw_input()
c.close()


########NEW FILE########
__FILENAME__ = nested_exceptions
import rpyc
c=rpyc.classic.connect_thread()
c.execute("import rpyc; c2=rpyc.classic.connect_thread()")
c.namespace["c2"].execute("1/0")


########NEW FILE########
__FILENAME__ = split33
import rpyc
from rpyc.utils.splitbrain import splitbrain, localbrain
import traceback
import sys


c = rpyc.classic.connect("localhost")
import os
pid1 = os.getpid()

with open("tmp.txt", "w") as f:
    f.write("foobar")

with splitbrain(c):
    pid2 = os.getpid()
    assert pid1 != pid2
    import email
    print (email)
    import os as os2
    pid3 = os2.getpid()
    assert pid2 == pid3
    
    assert not os.path.exists("tmp.txt")
    
    with localbrain():
        with open("tmp.txt", "r") as f:
            assert f.read() == "foobar"
        pid4 = os.getpid()
        assert pid4 == pid1
    
    try:
        open("tmp.txt", "r")
    except IOError as ex:
        #print(type(ex), repr(ex))
        with localbrain():
            x = ("".join(traceback.format_exception(*sys.exc_info())))
            print(len(x))
    else:
        assert False, "expected an IOError"

pid5 = os.getpid()
assert pid5 == pid1

print ("done")

########NEW FILE########
__FILENAME__ = async
import time


class AsyncResultTimeout(Exception):
    """an exception that represents an :class:`AsyncResult` that has timed out"""
    pass

class AsyncResult(object):
    """*AsyncResult* represents a computation that occurs in the background and
    will eventually have a result. Use the :attr:`value` property to access the 
    result (which will block if the result has not yet arrived).
    """
    __slots__ = ["_conn", "_is_ready", "_is_exc", "_callbacks", "_obj", "_ttl"]
    def __init__(self, conn):
        self._conn = conn
        self._is_ready = False
        self._is_exc = None
        self._obj = None
        self._callbacks = []
        self._ttl = None
    def __repr__(self):
        if self._is_ready:
            state = "ready"
        elif self._is_exc:
            state = "error"
        elif self.expired:
            state = "expired"
        else:
            state = "pending"
        return "<AsyncResult object (%s) at 0x%08x>" % (state, id(self))
    
    def __call__(self, is_exc, obj):
        if self.expired:
            return
        self._is_exc = is_exc
        self._obj = obj
        self._is_ready = True
        for cb in self._callbacks:
            cb(self)
        del self._callbacks[:]

    def wait(self):
        """Waits for the result to arrive. If the AsyncResult object has an
        expiry set, and the result did not arrive within that timeout,
        an :class:`AsyncResultTimeout` exception is raised"""
        if self._is_ready:
            return
        if self._ttl is None:
            while not self._is_ready:
                self._conn.serve()
        else:
            while True:
                timeout = self._ttl - time.time()
                self._conn.poll(timeout = max(timeout, 0))
                if self._is_ready:
                    break
                if timeout <= 0:
                    raise AsyncResultTimeout("result expired")
    
    def add_callback(self, func):
        """Adds a callback to be invoked when the result arrives. The callback 
        function takes a single argument, which is the current AsyncResult
        (``self``). If the result has already arrived, the function is invoked
        immediately.
        
        :param func: the callback function to add
        """
        if self._is_ready:
            func(self)
        else:
            self._callbacks.append(func)
    def set_expiry(self, timeout):
        """Sets the expiry time (in seconds, relative to now) or ``None`` for
        unlimited time
        
        :param timeout: the expiry time in seconds or ``None``
        """
        if timeout is None:
            self._ttl = None
        else:
            self._ttl = time.time() + timeout

    @property
    def ready(self):
        """Indicates whether the result has arrived"""
        if self.expired:
            return False
        if not self._is_ready:
            self._conn.poll_all()
        return self._is_ready
    @property
    def error(self):
        """Indicates whether the returned result is an exception"""
        if self.ready:
            return self._is_exc
        return False
    @property
    def expired(self):
        """Indicates whether the AsyncResult has expired"""
        if self._is_ready or self._ttl is None:
            return False
        else:
            return time.time() > self._ttl

    @property
    def value(self):
        """Returns the result of the operation. If the result has not yet
        arrived, accessing this property will wait for it. If the result does
        not arrive before the expiry time elapses, :class:`AsyncResultTimeout` 
        is raised. If the returned result is an exception, it will be raised 
        here. Otherwise, the result is returned directly.
        """
        self.wait()
        if self._is_exc:
            raise self._obj
        else:
            return self._obj


########NEW FILE########
__FILENAME__ = brine
"""
**Brine** is a simple, fast and secure object serializer for **immutable** objects.
The following types are supported: ``int``, ``long``, ``bool``, ``str``, ``float``,
``unicode``, ``bytes``, ``slice``, ``complex``, ``tuple`` (of simple types), 
``forzenset`` (of simple types) as well as the following singletons: ``None``, 
``NotImplemented``, and ``Ellipsis``.

Example::

    >>> x = ("he", 7, u"llo", 8, (), 900, None, True, Ellipsis, 18.2, 18.2j + 13,
    ... slice(1,2,3), frozenset([5,6,7]), NotImplemented)
    >>> dumpable(x)
    True
    >>> y = dump(x)
    >>> y.encode("hex")
    '140e0b686557080c6c6c6f580216033930300003061840323333333333331b402a000000000000403233333333333319125152531a1255565705'
    >>> z = load(y)
    >>> x == z
    True
"""
from rpyc.lib.compat import Struct, BytesIO, is_py3k, BYTES_LITERAL


# singletons
TAG_NONE = BYTES_LITERAL("\x00")
TAG_EMPTY_STR = BYTES_LITERAL("\x01")
TAG_EMPTY_TUPLE = BYTES_LITERAL("\x02")
TAG_TRUE = BYTES_LITERAL("\x03")
TAG_FALSE = BYTES_LITERAL("\x04")
TAG_NOT_IMPLEMENTED = BYTES_LITERAL("\x05")
TAG_ELLIPSIS = BYTES_LITERAL("\x06")
# types
TAG_UNICODE = BYTES_LITERAL("\x08")
TAG_LONG = BYTES_LITERAL("\x09")
TAG_STR1 = BYTES_LITERAL("\x0a")
TAG_STR2 = BYTES_LITERAL("\x0b")
TAG_STR3 = BYTES_LITERAL("\x0c")
TAG_STR4 = BYTES_LITERAL("\x0d")
TAG_STR_L1 = BYTES_LITERAL("\x0e")
TAG_STR_L4 = BYTES_LITERAL("\x0f")
TAG_TUP1 = BYTES_LITERAL("\x10")
TAG_TUP2 = BYTES_LITERAL("\x11")
TAG_TUP3 = BYTES_LITERAL("\x12")
TAG_TUP4 = BYTES_LITERAL("\x13")
TAG_TUP_L1 = BYTES_LITERAL("\x14")
TAG_TUP_L4 = BYTES_LITERAL("\x15")
TAG_INT_L1 = BYTES_LITERAL("\x16")
TAG_INT_L4 = BYTES_LITERAL("\x17")
TAG_FLOAT = BYTES_LITERAL("\x18")
TAG_SLICE = BYTES_LITERAL("\x19")
TAG_FSET = BYTES_LITERAL("\x1a")
TAG_COMPLEX = BYTES_LITERAL("\x1b")
if is_py3k:
    IMM_INTS = dict((i, bytes([i + 0x50])) for i in range(-0x30, 0xa0))
else:
    IMM_INTS = dict((i, chr(i + 0x50)) for i in range(-0x30, 0xa0))

I1 = Struct("!B")
I4 = Struct("!L")
F8 = Struct("!d")
C16 = Struct("!dd")

_dump_registry = {}
_load_registry = {}
IMM_INTS_LOADER = dict((v, k) for k, v in IMM_INTS.items())

def register(coll, key):
    def deco(func):
        coll[key] = func
        return func
    return deco

#===============================================================================
# dumping
#===============================================================================
@register(_dump_registry, type(None))
def _dump_none(obj, stream):
    stream.append(TAG_NONE)

@register(_dump_registry, type(NotImplemented))
def _dump_notimplemeted(obj, stream):
    stream.append(TAG_NOT_IMPLEMENTED)

@register(_dump_registry, type(Ellipsis))
def _dump_ellipsis(obj, stream):
    stream.append(TAG_ELLIPSIS)

@register(_dump_registry, bool)
def _dump_bool(obj, stream):
    if obj:
        stream.append(TAG_TRUE)
    else:
        stream.append(TAG_FALSE)

@register(_dump_registry, slice)
def _dump_slice(obj, stream):
    stream.append(TAG_SLICE)
    _dump((obj.start, obj.stop, obj.step), stream)

@register(_dump_registry, frozenset)
def _dump_frozenset(obj, stream):
    stream.append(TAG_FSET)
    _dump(tuple(obj), stream)

@register(_dump_registry, int)
def _dump_int(obj, stream):
    if obj in IMM_INTS:
        stream.append(IMM_INTS[obj])
    else:
        obj = BYTES_LITERAL(str(obj))
        l = len(obj)
        if l < 256:
            stream.append(TAG_INT_L1 + I1.pack(l) + obj)
        else:
            stream.append(TAG_INT_L4 + I4.pack(l) + obj)

@register(_dump_registry, float)
def _dump_float(obj, stream):
    stream.append(TAG_FLOAT + F8.pack(obj))

@register(_dump_registry, complex)
def _dump_complex(obj, stream):
    stream.append(TAG_COMPLEX + C16.pack(obj.real, obj.imag))

if is_py3k:
    @register(_dump_registry, bytes)
    def _dump_bytes(obj, stream):
        l = len(obj)
        if l == 0:
            stream.append(TAG_EMPTY_STR)
        elif l == 1:
            stream.append(TAG_STR1 + obj)
        elif l == 2:
            stream.append(TAG_STR2 + obj)
        elif l == 3:
            stream.append(TAG_STR3 + obj)
        elif l == 4:
            stream.append(TAG_STR4 + obj)
        elif l < 256:
            stream.append(TAG_STR_L1 + I1.pack(l) + obj)
        else:
            stream.append(TAG_STR_L4 + I4.pack(l) + obj)

    @register(_dump_registry, str)
    def _dump_str(obj, stream):
        stream.append(TAG_UNICODE)
        _dump_bytes(obj.encode("utf8"), stream)
else:
    @register(_dump_registry, str)
    def _dump_str(obj, stream):
        l = len(obj)
        if l == 0:
            stream.append(TAG_EMPTY_STR)
        elif l == 1:
            stream.append(TAG_STR1 + obj)
        elif l == 2:
            stream.append(TAG_STR2 + obj)
        elif l == 3:
            stream.append(TAG_STR3 + obj)
        elif l == 4:
            stream.append(TAG_STR4 + obj)
        elif l < 256:
            stream.append(TAG_STR_L1 + I1.pack(l) + obj)
        else:
            stream.append(TAG_STR_L4 + I4.pack(l) + obj)

    @register(_dump_registry, unicode)
    def _dump_unicode(obj, stream):
        stream.append(TAG_UNICODE)
        _dump_str(obj.encode("utf8"), stream)

    @register(_dump_registry, long)
    def _dump_long(obj, stream):
        stream.append(TAG_LONG)
        _dump_int(obj, stream)


@register(_dump_registry, tuple)
def _dump_tuple(obj, stream):
    l = len(obj)
    if l == 0:
        stream.append(TAG_EMPTY_TUPLE)
    elif l == 1:
        stream.append(TAG_TUP1)
    elif l == 2:
        stream.append(TAG_TUP2)
    elif l == 3:
        stream.append(TAG_TUP3)
    elif l == 4:
        stream.append(TAG_TUP4)
    elif l < 256:
        stream.append(TAG_TUP_L1 + I1.pack(l))
    else:
        stream.append(TAG_TUP_L4 + I4.pack(l))
    for item in obj:
        _dump(item, stream)

def _undumpable(obj, stream):
    raise TypeError("cannot dump %r" % (obj,))

def _dump(obj, stream):
    _dump_registry.get(type(obj), _undumpable)(obj, stream)

#===============================================================================
# loading
#===============================================================================
@register(_load_registry, TAG_NONE)
def _load_none(stream):
    return None
@register(_load_registry, TAG_NOT_IMPLEMENTED)
def _load_nonimp(stream):
    return NotImplemented
@register(_load_registry, TAG_ELLIPSIS)
def _load_elipsis(stream):
    return Ellipsis
@register(_load_registry, TAG_TRUE)
def _load_true(stream):
    return True
@register(_load_registry, TAG_FALSE)
def _load_false(stream):
    return False
@register(_load_registry, TAG_EMPTY_TUPLE)
def _load_empty_tuple(stream):
    return ()

if is_py3k:
    @register(_load_registry, TAG_EMPTY_STR)
    def _load_empty_str(stream):
        return BYTES_LITERAL("")
else:
    @register(_load_registry, TAG_EMPTY_STR)
    def _load_empty_str(stream):
        return ""

if is_py3k:
    @register(_load_registry, TAG_LONG)
    def _load_long(stream):
        obj = _load(stream)
        return int(obj)
else:
    @register(_load_registry, TAG_LONG)
    def _load_long(stream):
        obj = _load(stream)
        return long(obj)

@register(_load_registry, TAG_FLOAT)
def _load_float(stream):
    return F8.unpack(stream.read(8))[0]
@register(_load_registry, TAG_COMPLEX)
def _load_complex(stream):
    real, imag = C16.unpack(stream.read(16))
    return complex(real, imag)

@register(_load_registry, TAG_STR1)
def _load_str1(stream):
    return stream.read(1)
@register(_load_registry, TAG_STR2)
def _load_str2(stream):
    return stream.read(2)
@register(_load_registry, TAG_STR3)
def _load_str3(stream):
    return stream.read(3)
@register(_load_registry, TAG_STR4)
def _load_str4(stream):
    return stream.read(4)
@register(_load_registry, TAG_STR_L1)
def _load_str_l1(stream):
    l, = I1.unpack(stream.read(1))
    return stream.read(l)
@register(_load_registry, TAG_STR_L4)
def _load_str_l4(stream):
    l, = I4.unpack(stream.read(4))
    return stream.read(l)

@register(_load_registry, TAG_UNICODE)
def _load_unicode(stream):
    obj = _load(stream)
    return obj.decode("utf-8")

@register(_load_registry, TAG_TUP1)
def _load_tup1(stream):
    return (_load(stream),)
@register(_load_registry, TAG_TUP2)
def _load_tup2(stream):
    return (_load(stream), _load(stream))
@register(_load_registry, TAG_TUP3)
def _load_tup3(stream):
    return (_load(stream), _load(stream), _load(stream))
@register(_load_registry, TAG_TUP4)
def _load_tup4(stream):
    return (_load(stream), _load(stream), _load(stream), _load(stream))
@register(_load_registry, TAG_TUP_L1)
def _load_tup_l1(stream):
    l, = I1.unpack(stream.read(1))
    return tuple(_load(stream) for i in range(l))

if is_py3k:
    @register(_load_registry, TAG_TUP_L4)
    def _load_tup_l4(stream):
        l, = I4.unpack(stream.read(4))
        return tuple(_load(stream) for i in range(l))
else:
    @register(_load_registry, TAG_TUP_L4)
    def _load_tup_l4(stream):
        l, = I4.unpack(stream.read(4))
        return tuple(_load(stream) for i in xrange(l))

@register(_load_registry, TAG_SLICE)
def _load_slice(stream):
    start, stop, step = _load(stream)
    return slice(start, stop, step)
@register(_load_registry, TAG_FSET)
def _load_frozenset(stream):
    return frozenset(_load(stream))

@register(_load_registry, TAG_INT_L1)
def _load_int_l1(stream):
    l, = I1.unpack(stream.read(1))
    return int(stream.read(l))
@register(_load_registry, TAG_INT_L4)
def _load_int_l4(stream):
    l, = I4.unpack(stream.read(4))
    return int(stream.read(l))

def _load(stream):
    tag = stream.read(1)
    if tag in IMM_INTS_LOADER:
        return IMM_INTS_LOADER[tag]
    return _load_registry.get(tag)(stream)

#===============================================================================
# API
#===============================================================================
def dump(obj):
    """Converts (dumps) the given object to a byte-string representation
    
    :param obj: any :func:`dumpable` object
    
    :returns: a byte-string representation of the object
    """
    stream = []
    _dump(obj, stream)
    return BYTES_LITERAL("").join(stream)

def load(data):
    """Recreates (loads) an object from its byte-string representation
    
    :param data: the byte-string representation of an object
    
    :returns: the dumped object
    """
    stream = BytesIO(data)
    return _load(stream)

if is_py3k:
    simple_types = frozenset([type(None), int, bool, float, bytes, str, complex, 
        type(NotImplemented), type(Ellipsis)])
else:
    simple_types = frozenset([type(None), int, long, bool, float, str, unicode, complex, 
        type(NotImplemented), type(Ellipsis)])

def dumpable(obj):
    """Indicates whether the given object is *dumpable* by brine
    
    :returns: ``True`` if the object is dumpable (e.g., :func:`dump` would succeed),
              ``False`` otherwise
    """
    if type(obj) in simple_types:
        return True
    if type(obj) in (tuple, frozenset):
        return all(dumpable(item) for item in obj)
    if type(obj) is slice:
        return dumpable(obj.start) and dumpable(obj.stop) and dumpable(obj.step)
    return False


if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = channel
"""
*Channel* is an abstraction layer over streams that works with *packets of data*,
rather than an endless stream of bytes, and adds support for compression.
"""
from rpyc.lib import safe_import
from rpyc.lib.compat import Struct, BYTES_LITERAL
zlib = safe_import("zlib")

# * 64 bit length field?
# * separate \n into a FlushingChannel subclass?
# * add thread safety as a subclass?

class Channel(object):
    """Channel implementation.
    
    Note: In order to avoid problems with all sorts of line-buffered transports, 
    we deliberately add ``\\n`` at the end of each frame.
    """
    
    COMPRESSION_THRESHOLD = 3000
    COMPRESSION_LEVEL = 1
    FRAME_HEADER = Struct("!LB")
    FLUSHER = BYTES_LITERAL("\n") # cause any line-buffered layers below us to flush
    __slots__ = ["stream", "compress"]

    def __init__(self, stream, compress = True):
        self.stream = stream
        if not zlib:
            compress = False
        self.compress = compress
    def close(self):
        """closes the channel and underlying stream"""
        self.stream.close()
    @property
    def closed(self):
        """indicates whether the underlying stream has been closed"""
        return self.stream.closed
    def fileno(self):
        """returns the file descriptor of the underlying stream"""
        return self.stream.fileno()
    def poll(self, timeout):
        """polls the underlying steam for data, waiting up to *timeout* seconds"""
        return self.stream.poll(timeout)
    def recv(self):
        """Receives the next packet (or *frame*) from the underlying stream.
        This method will block until the packet has been read completely
        
        :returns: string of data
        """
        header = self.stream.read(self.FRAME_HEADER.size)
        length, compressed = self.FRAME_HEADER.unpack(header)
        data = self.stream.read(length + len(self.FLUSHER))[:-len(self.FLUSHER)]
        if compressed:
            data = zlib.decompress(data)
        return data
    def send(self, data):
        """Sends the given string of data as a packet over the underlying 
        stream. Blocks until the packet has been sent.
        
        :param data: the byte string to send as a packet
        """
        if self.compress and len(data) > self.COMPRESSION_THRESHOLD:
            compressed = 1
            data = zlib.compress(data, self.COMPRESSION_LEVEL)
        else:
            compressed = 0
        header = self.FRAME_HEADER.pack(len(data), compressed)
        buf = header + data + self.FLUSHER
        self.stream.write(buf)


########NEW FILE########
__FILENAME__ = consts
"""
Constants used by the protocol
"""

# messages
MSG_REQUEST      = 1
MSG_REPLY        = 2
MSG_EXCEPTION    = 3

# boxing
LABEL_VALUE      = 1
LABEL_TUPLE      = 2
LABEL_LOCAL_REF  = 3
LABEL_REMOTE_REF = 4

# action handlers
HANDLE_PING        = 1
HANDLE_CLOSE       = 2
HANDLE_GETROOT     = 3
HANDLE_GETATTR     = 4
HANDLE_DELATTR     = 5
HANDLE_SETATTR     = 6
HANDLE_CALL        = 7
HANDLE_CALLATTR    = 8
HANDLE_REPR        = 9
HANDLE_STR         = 10
HANDLE_CMP         = 11
HANDLE_HASH        = 12
HANDLE_DIR         = 13
HANDLE_PICKLE      = 14
HANDLE_DEL         = 15
HANDLE_INSPECT     = 16
HANDLE_BUFFITER    = 17
HANDLE_OLDSLICING  = 18

# optimized exceptions
EXC_STOP_ITERATION = 1

# DEBUG
#for k in globals().keys():
#    globals()[k] = k


########NEW FILE########
__FILENAME__ = netref
"""
**NetRef**: a transparent *network reference*. This module contains quite a lot
of *magic*, so beware.
"""
import sys
import inspect
import types
from rpyc.lib.compat import pickle, is_py3k, maxint
from rpyc.core import consts


_local_netref_attrs = frozenset([
    '____conn__', '____oid__', '__class__', '__cmp__', '__del__', '__delattr__',
    '__dir__', '__doc__', '__getattr__', '__getattribute__', '__hash__',
    '__init__', '__metaclass__', '__module__', '__new__', '__reduce__',
    '__reduce_ex__', '__repr__', '__setattr__', '__slots__', '__str__',
    '__weakref__', '__dict__', '__members__', '__methods__',
])
"""the set of attributes that are local to the netref object"""

_builtin_types = [
    type, object, bool, complex, dict, float, int, list, slice, str, tuple, set, 
    frozenset, Exception, type(None), types.BuiltinFunctionType, types.GeneratorType,
    types.MethodType, types.CodeType, types.FrameType, types.TracebackType, 
    types.ModuleType, types.FunctionType,

    type(int.__add__),      # wrapper_descriptor
    type((1).__add__),      # method-wrapper
    type(iter([])),         # listiterator
    type(iter(())),         # tupleiterator
    type(iter(set())),      # setiterator
]
"""a list of types considered built-in (shared between connections)"""

try:
    BaseException
except NameError:
    pass
else:
    _builtin_types.append(BaseException)

if is_py3k:
    _builtin_types.extend([
        bytes, bytearray, type(iter(range(10))), memoryview,
    ])
else:
    _builtin_types.extend([
        basestring, unicode, long, xrange, type(iter(xrange(10))), file,
        types.InstanceType, types.ClassType, types.DictProxyType,
    ])

_normalized_builtin_types = dict(((t.__name__, t.__module__), t)
    for t in _builtin_types)

def syncreq(proxy, handler, *args):
    """Performs a synchronous request on the given proxy object.
    Not intended to be invoked directly.
    
    :param proxy: the proxy on which to issue the request
    :param handler: the request handler (one of the ``HANDLE_XXX`` members of 
                    ``rpyc.protocol.consts``)
    :param args: arguments to the handler
    
    :raises: any exception raised by the operation will be raised
    :returns: the result of the operation
    """
    conn = object.__getattribute__(proxy, "____conn__")()
    if not conn:
        raise ReferenceError('weakly-referenced object no longer exists')
    oid = object.__getattribute__(proxy, "____oid__")
    return conn.sync_request(handler, oid, *args)

def asyncreq(proxy, handler, *args):
    """Performs an asynchronous request on the given proxy object.
    Not intended to be invoked directly.

    :param proxy: the proxy on which to issue the request
    :param handler: the request handler (one of the ``HANDLE_XXX`` members of 
                    ``rpyc.protocol.consts``)
    :param args: arguments to the handler
    
    :returns: an :class:`AsyncResult <rpyc.core.async.AsyncResult>` representing
              the operation
    """
    conn = object.__getattribute__(proxy, "____conn__")()
    if not conn:
        raise ReferenceError('weakly-referenced object no longer exists')
    oid = object.__getattribute__(proxy, "____oid__")
    return conn.async_request(handler, oid, *args)

class NetrefMetaclass(type):
    """A *metaclass* used to customize the ``__repr__`` of ``netref`` classes.
    It is quite useless, but it makes debugging and interactive programming 
    easier"""
    
    __slots__ = ()
    def __repr__(self):
        if self.__module__:
            return "<netref class '%s.%s'>" % (self.__module__, self.__name__)
        else:
            return "<netref class '%s'>" % (self.__name__,)

class BaseNetref(object):
    """The base netref class, from which all netref classes derive. Some netref
    classes are "pre-generated" and cached upon importing this module (those 
    defined in the :data:`_builtin_types`), and they are shared between all 
    connections. 
    
    The rest of the netref classes are created by :meth:`rpyc.core.protocl.Connection._unbox`,
    and are private to the connection.
    
    Do not use this class directly; use :func:`class_factory` instead.
    
    :param conn: the :class:`rpyc.core.protocol.Connection` instance
    :param oid: the unique object ID of the remote object
    """
    # this is okay with py3k -- see below
    __metaclass__ = NetrefMetaclass
    __slots__ = ["____conn__", "____oid__", "__weakref__"]
    def __init__(self, conn, oid):
        self.____conn__ = conn
        self.____oid__ = oid
    def __del__(self):
        try:
            asyncreq(self, consts.HANDLE_DEL)
        except Exception:
            # raised in a destructor, most likely on program termination,
            # when the connection might have already been closed.
            # it's safe to ignore all exceptions here
            pass

    def __getattribute__(self, name):
        if name in _local_netref_attrs:
            if name == "__class__":
                cls = object.__getattribute__(self, "__class__")
                if cls is None:
                    cls = self.__getattr__("__class__")
                return cls
            elif name == "__doc__":
                return self.__getattr__("__doc__")
            elif name == "__members__":                       # for Python < 2.6
                return self.__dir__()
            else:
                return object.__getattribute__(self, name)
        elif name == "__call__":                          # IronPython issue #10
            return object.__getattribute__(self, "__call__")
        else:
            return syncreq(self, consts.HANDLE_GETATTR, name)
    def __getattr__(self, name):
        return syncreq(self, consts.HANDLE_GETATTR, name)
    def __delattr__(self, name):
        if name in _local_netref_attrs:
            object.__delattr__(self, name)
        else:
            syncreq(self, consts.HANDLE_DELATTR, name)
    def __setattr__(self, name, value):
        if name in _local_netref_attrs:
            object.__setattr__(self, name, value)
        else:
            syncreq(self, consts.HANDLE_SETATTR, name, value)
    def __dir__(self):
        return list(syncreq(self, consts.HANDLE_DIR))

    # support for metaclasses
    def __hash__(self):
        return syncreq(self, consts.HANDLE_HASH)
    def __cmp__(self, other):
        return syncreq(self, consts.HANDLE_CMP, other)
    def __repr__(self):
        return syncreq(self, consts.HANDLE_REPR)
    def __str__(self):
        return syncreq(self, consts.HANDLE_STR)
    
    # support for pickling netrefs
    def __reduce_ex__(self, proto):
        return pickle.loads, (syncreq(self, consts.HANDLE_PICKLE, proto),)

if not isinstance(BaseNetref, NetrefMetaclass):
    # python 2 and 3 compatible metaclass...
    ns = dict(BaseNetref.__dict__)
    for slot in BaseNetref.__slots__:
        ns.pop(slot)
    BaseNetref = NetrefMetaclass(BaseNetref.__name__, BaseNetref.__bases__, ns) 


def _make_method(name, doc):
    """creates a method with the given name and docstring that invokes
    :func:`syncreq` on its `self` argument"""
    
    slicers = {"__getslice__" : "__getitem__", "__delslice__" : "__delitem__", "__setslice__" : "__setitem__"}
    
    name = str(name)                                      # IronPython issue #10
    if name == "__call__":
        def __call__(_self, *args, **kwargs):
            kwargs = tuple(kwargs.items())
            return syncreq(_self, consts.HANDLE_CALL, args, kwargs)
        __call__.__doc__ = doc
        return __call__
    elif name in slicers:                                 # 32/64 bit issue #41
        def method(self, start, stop, *args):
            if stop == maxint:
                stop = None
            return syncreq(self, consts.HANDLE_OLDSLICING, slicers[name], name, start, stop, args)
        method.__name__ = name
        method.__doc__ = doc
        return method
    else:
        def method(_self, *args, **kwargs):
            kwargs = tuple(kwargs.items())
            return syncreq(_self, consts.HANDLE_CALLATTR, name, args, kwargs)
        method.__name__ = name
        method.__doc__ = doc
        return method

def inspect_methods(obj):
    """introspects the given (local) object, returning a list of all of its
    methods (going up the MRO).
    
    :param obj: any local (not proxy) python object
    
    :returns: a list of ``(method name, docstring)`` tuples of all the methods
              of the given object
    """
    methods = {}
    attrs = {}
    if isinstance(obj, type):
        # don't forget the darn metaclass
        mros = list(reversed(type(obj).__mro__)) + list(reversed(obj.__mro__))
    else:
        mros = reversed(type(obj).__mro__)
    for basecls in mros:
        attrs.update(basecls.__dict__)
    for name, attr in attrs.items():
        if name not in _local_netref_attrs and hasattr(attr, "__call__"):
            methods[name] = inspect.getdoc(attr)
    return methods.items()

def class_factory(clsname, modname, methods):
    """Creates a netref class proxying the given class
    
    :param clsname: the class's name
    :param modname: the class's module name
    :param methods: a list of ``(method name, docstring)`` tuples, of the methods
                    that the class defines
    
    :returns: a netref class
    """
    clsname = str(clsname)                                # IronPython issue #10
    modname = str(modname)                                # IronPython issue #10
    ns = {"__slots__" : ()}
    for name, doc in methods:
        name = str(name)                                  # IronPython issue #10
        if name not in _local_netref_attrs:
            ns[name] = _make_method(name, doc)
    ns["__module__"] = modname
    if modname in sys.modules and hasattr(sys.modules[modname], clsname):
        ns["__class__"] = getattr(sys.modules[modname], clsname)
    elif (clsname, modname) in _normalized_builtin_types:
        ns["__class__"] = _normalized_builtin_types[clsname, modname]
    else:
        # to be resolved by the instance
        ns["__class__"] = None
    return type(clsname, (BaseNetref,), ns)

builtin_classes_cache = {}
"""The cache of built-in netref classes (each of the types listed in 
:data:`_builtin_types`). These are shared between all RPyC connections"""

# init the builtin_classes_cache
for cls in _builtin_types:
    builtin_classes_cache[cls.__name__, cls.__module__] = class_factory(
        cls.__name__, cls.__module__, inspect_methods(cls))


########NEW FILE########
__FILENAME__ = protocol
"""
The RPyC protocol
"""
import sys
import weakref
import itertools
import socket
import time

from threading import Lock
from rpyc.lib.compat import pickle, next, is_py3k, maxint, select_error
from rpyc.lib.colls import WeakValueDict, RefCountingColl
from rpyc.core import consts, brine, vinegar, netref
from rpyc.core.async import AsyncResult

class PingError(Exception):
    """The exception raised should :func:`Connection.ping` fail"""
    pass

DEFAULT_CONFIG = dict(
    # ATTRIBUTES
    allow_safe_attrs = True,
    allow_exposed_attrs = True,
    allow_public_attrs = False,
    allow_all_attrs = False,
    safe_attrs = set(['__abs__', '__add__', '__and__', '__bool__', '__cmp__', '__contains__',
        '__delitem__', '__delslice__', '__div__', '__divmod__', '__doc__',
        '__eq__', '__float__', '__floordiv__', '__ge__', '__getitem__',
        '__getslice__', '__gt__', '__hash__', '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__ifloordiv__', '__ilshift__', '__imod__', '__imul__',
        '__index__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__',
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__',
        '__long__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__',
        '__neg__', '__new__', '__nonzero__', '__oct__', '__or__', '__pos__',
        '__pow__', '__radd__', '__rand__', '__rdiv__', '__rdivmod__', '__repr__',
        '__rfloordiv__', '__rlshift__', '__rmod__', '__rmul__', '__ror__',
        '__rpow__', '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__',
        '__rxor__', '__setitem__', '__setslice__', '__str__', '__sub__',
        '__truediv__', '__xor__', 'next', '__length_hint__', '__enter__',
        '__exit__', '__next__',]),
    exposed_prefix = "exposed_",
    allow_getattr = True,
    allow_setattr = False,
    allow_delattr = False,
    # EXCEPTIONS
    include_local_traceback = True,
    instantiate_custom_exceptions = False,
    import_custom_exceptions = False,
    instantiate_oldstyle_exceptions = False, # which don't derive from Exception
    propagate_SystemExit_locally = False, # whether to propagate SystemExit locally or to the other party
    propagate_KeyboardInterrupt_locally = True,  # whether to propagate KeyboardInterrupt locally or to the other party
    log_exceptions = True,
    # MISC
    allow_pickle = False,
    connid = None,
    credentials = None,
    endpoints = None,
    logger = None,
)
"""
The default configuration dictionary of the protocol. You can override these parameters
by passing a different configuration dict to the :class:`Connection` class.

.. note::
   You only need to override the parameters you want to change. There's no need
   to repeat parameters whose values remain unchanged.

=======================================  ================  =====================================================
Parameter                                Default value     Description
=======================================  ================  =====================================================
``allow_safe_attrs``                     ``True``          Whether to allow the use of *safe* attributes
                                                           (only those listed as ``safe_attrs``)
``allow_exposed_attrs``                  ``True``          Whether to allow exposed attributes
                                                           (attributes that start with the ``exposed_prefix``)
``allow_public_attrs``                   ``False``         Whether to allow public attributes
                                                           (attributes that don't start with ``_``)
``allow_all_attrs``                      ``False``         Whether to allow all attributes (including private)
``safe_attrs``                           ``set([...])``    The set of attributes considered safe
``exposed_prefix``                       ``"exposed_"``    The prefix of exposed attributes
``allow_getattr``                        ``True``          Whether to allow getting of attributes (``getattr``)
``allow_setattr``                        ``False``         Whether to allow setting of attributes (``setattr``)
``allow_delattr``                        ``False``         Whether to allow deletion of attributes (``delattr``)
``allow_pickle``                         ``False``         Whether to allow the use of ``pickle``

``include_local_traceback``              ``True``          Whether to include the local traceback
                                                           in the remote exception
``instantiate_custom_exceptions``        ``False``         Whether to allow instantiation of
                                                           custom exceptions (not the built in ones)
``import_custom_exceptions``             ``False``         Whether to allow importing of
                                                           exceptions from not-yet-imported modules
``instantiate_oldstyle_exceptions``      ``False``         Whether to allow instantiation of exceptions
                                                           which don't derive from ``Exception``. This
                                                           is not applicable for Python 3 and later.
``propagate_SystemExit_locally``         ``False``         Whether to propagate ``SystemExit``
                                                           locally (kill the server) or to the other
                                                           party (kill the client)
``propagate_KeyboardInterrupt_locally``  ``False``         Whether to propagate ``KeyboardInterrupt``
                                                           locally (kill the server) or to the other
                                                           party (kill the client)
``logger``                               ``None``          The logger instance to use to log exceptions
                                                           (before they are sent to the other party)
                                                           and other events. If ``None``, no logging takes place.

``connid``                               ``None``          **Runtime**: the RPyC connection ID (used
                                                           mainly for debugging purposes)
``credentials``                          ``None``          **Runtime**: the credentails object that was returned
                                                           by the server's :ref:`authenticator <api-authenticators>`
                                                           or ``None``
``endpoints``                            ``None``          **Runtime**: The connection's endpoints. This is a tuple
                                                           made of the local socket endpoint (``getsockname``) and the
                                                           remote one (``getpeername``). This is set by the server
                                                           upon accepting a connection; client side connections
                                                           do no have this configuration option set.
=======================================  ================  =====================================================
"""


_connection_id_generator = itertools.count(1)

class Connection(object):
    """The RPyC *connection* (AKA *protocol*).
    
    :param service: the :class:`Service <rpyc.core.service.Service>` to expose
    :param channel: the :class:`Channel <rpyc.core.channel.Channel>` over which messages are passed
    :param config: the connection's configuration dict (overriding parameters 
                   from the :data:`default configuration <DEFAULT_CONFIG>`)
    :param _lazy: whether or not to initialize the service with the creation of
                  the connection. Default is True. If set to False, you will 
                  need to call :func:`_init_service` manually later
    """
    def __init__(self, service, channel, config = {}, _lazy = False):
        self._closed = True
        self._config = DEFAULT_CONFIG.copy()
        self._config.update(config)
        if self._config["connid"] is None:
            self._config["connid"] = "conn%d" % (next(_connection_id_generator),)

        self._channel = channel
        self._seqcounter = itertools.count()
        self._recvlock = Lock()
        self._sendlock = Lock()
        self._sync_replies = {}
        self._async_callbacks = {}
        self._local_objects = RefCountingColl()
        self._last_traceback = None
        self._proxy_cache = WeakValueDict()
        self._netref_classes_cache = {}
        self._remote_root = None
        self._local_root = service(weakref.proxy(self))
        if not _lazy:
            self._init_service()
        self._closed = False
    def _init_service(self):
        self._local_root.on_connect()

    def __del__(self):
        self.close()
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def __repr__(self):
        a, b = object.__repr__(self).split(" object ")
        return "%s %r object %s" % (a, self._config["connid"], b)

    #
    # IO
    #
    def _cleanup(self, _anyway = True):
        if self._closed and not _anyway:
            return
        self._closed = True
        self._channel.close()
        self._local_root.on_disconnect()
        self._sync_replies.clear()
        self._async_callbacks.clear()
        self._local_objects.clear()
        self._proxy_cache.clear()
        self._netref_classes_cache.clear()
        self._last_traceback = None
        self._remote_root = None
        self._local_root = None
        #self._seqcounter = None
        #self._config.clear()
    
    def close(self, _catchall = True):
        """closes the connection, releasing all held resources"""
        if self._closed:
            return
        self._closed = True
        try:
            self._async_request(consts.HANDLE_CLOSE)
        except EOFError:
            pass
        except Exception:
            if not _catchall:
                raise
        finally:
            self._cleanup(_anyway = True)

    @property
    def closed(self):
        """Indicates whether the connection has been closed or not"""
        return self._closed
    def fileno(self):
        """Returns the connectin's underlying file descriptor"""
        return self._channel.fileno()

    def ping(self, data = None, timeout = 3):
        """       
        Asserts that the other party is functioning properly, by making sure
        the *data* is echoed back before the *timeout* expires
        
        :param data: the data to send (leave ``None`` for the default buffer)
        :param timeout: the maximal time to wait for echo
        
        :raises: :class:`PingError` if the echoed data does not match
        """
        if data is None:
            data = "abcdefghijklmnopqrstuvwxyz" * 20
        res = self.async_request(consts.HANDLE_PING, data, timeout = timeout)
        if res.value != data:
            raise PingError("echo mismatches sent data")

    def _send(self, msg, seq, args):
        data = brine.dump((msg, seq, args))
        self._sendlock.acquire()
        try:
            self._channel.send(data)
        finally:
            self._sendlock.release()
    def _send_request(self, handler, args):
        seq = next(self._seqcounter)
        self._send(consts.MSG_REQUEST, seq, (handler, self._box(args)))
        return seq
    def _send_reply(self, seq, obj):
        self._send(consts.MSG_REPLY, seq, self._box(obj))
    def _send_exception(self, seq, exctype, excval, exctb):
        exc = vinegar.dump(exctype, excval, exctb,
            include_local_traceback = self._config["include_local_traceback"])
        self._send(consts.MSG_EXCEPTION, seq, exc)

    #
    # boxing
    #
    def _box(self, obj):
        """store a local object in such a way that it could be recreated on
        the remote party either by-value or by-reference"""
        if brine.dumpable(obj):
            return consts.LABEL_VALUE, obj
        if type(obj) is tuple:
            return consts.LABEL_TUPLE, tuple(self._box(item) for item in obj)
        elif isinstance(obj, netref.BaseNetref) and obj.____conn__() is self:
            return consts.LABEL_LOCAL_REF, obj.____oid__
        else:
            self._local_objects.add(obj)
            try:
                cls = obj.__class__
            except Exception:
                # see issue #16
                cls = type(obj)
            if not isinstance(cls, type):
                cls = type(obj)
            return consts.LABEL_REMOTE_REF, (id(obj), cls.__name__, cls.__module__)

    def _unbox(self, package):
        """recreate a local object representation of the remote object: if the
        object is passed by value, just return it; if the object is passed by
        reference, create a netref to it"""
        label, value = package
        if label == consts.LABEL_VALUE:
            return value
        if label == consts.LABEL_TUPLE:
            return tuple(self._unbox(item) for item in value)
        if label == consts.LABEL_LOCAL_REF:
            return self._local_objects[value]
        if label == consts.LABEL_REMOTE_REF:
            oid, clsname, modname = value
            if oid in self._proxy_cache:
                return self._proxy_cache[oid]
            proxy = self._netref_factory(oid, clsname, modname)
            self._proxy_cache[oid] = proxy
            return proxy
        raise ValueError("invalid label %r" % (label,))

    def _netref_factory(self, oid, clsname, modname):
        typeinfo = (clsname, modname)
        if typeinfo in self._netref_classes_cache:
            cls = self._netref_classes_cache[typeinfo]
        elif typeinfo in netref.builtin_classes_cache:
            cls = netref.builtin_classes_cache[typeinfo]
        else:
            info = self.sync_request(consts.HANDLE_INSPECT, oid)
            cls = netref.class_factory(clsname, modname, info)
            self._netref_classes_cache[typeinfo] = cls
        return cls(weakref.ref(self), oid)

    #
    # dispatching
    #
    def _dispatch_request(self, seq, raw_args):
        try:
            handler, args = raw_args
            args = self._unbox(args)
            res = self._HANDLERS[handler](self, *args)
        except:
            # need to catch old style exceptions too
            t, v, tb = sys.exc_info()
            self._last_traceback = tb
            if self._config["logger"] and t is not StopIteration:
                self._config["logger"].debug("Exception caught", exc_info=True)
            if t is SystemExit and self._config["propagate_SystemExit_locally"]:
                raise
            if t is KeyboardInterrupt and self._config["propagate_KeyboardInterrupt_locally"]:
                raise
            self._send_exception(seq, t, v, tb)
        else:
            self._send_reply(seq, res)

    def _dispatch_reply(self, seq, raw):
        obj = self._unbox(raw)
        if seq in self._async_callbacks:
            self._async_callbacks.pop(seq)(False, obj)
        else:
            self._sync_replies[seq] = (False, obj)

    def _dispatch_exception(self, seq, raw):
        obj = vinegar.load(raw,
            import_custom_exceptions = self._config["import_custom_exceptions"],
            instantiate_custom_exceptions = self._config["instantiate_custom_exceptions"],
            instantiate_oldstyle_exceptions = self._config["instantiate_oldstyle_exceptions"])
        if seq in self._async_callbacks:
            self._async_callbacks.pop(seq)(True, obj)
        else:
            self._sync_replies[seq] = (True, obj)

    #
    # serving
    #
    def _recv(self, timeout, wait_for_lock):
        if not self._recvlock.acquire(wait_for_lock):
            return None
        try:
            if self._channel.poll(timeout):
                data = self._channel.recv()
            else:
                data = None
        except EOFError:
            self.close()
            raise
        finally:
            self._recvlock.release()
        return data

    def _dispatch(self, data):
        msg, seq, args = brine.load(data)
        if msg == consts.MSG_REQUEST:
            self._dispatch_request(seq, args)
        elif msg == consts.MSG_REPLY:
            self._dispatch_reply(seq, args)
        elif msg == consts.MSG_EXCEPTION:
            self._dispatch_exception(seq, args)
        else:
            raise ValueError("invalid message type: %r" % (msg,))

    def poll(self, timeout = 0):
        """Serves a single transaction, should one arrives in the given
        interval. Note that handling a request/reply may trigger nested
        requests, which are all part of a single transaction.

        :returns: ``True`` if a transaction was served, ``False`` otherwise"""
        data = self._recv(timeout, wait_for_lock = False)
        if not data:
            return False
        self._dispatch(data)
        return True

    def serve(self, timeout = 1):
        """Serves a single request or reply that arrives within the given
        time frame (default is 1 sec). Note that the dispatching of a request
        might trigger multiple (nested) requests, thus this function may be
        reentrant. 
        
        :returns: ``True`` if a request or reply were received, ``False``
                  otherwise.
        """
        data = self._recv(timeout, wait_for_lock = True)
        if not data:
            return False
        self._dispatch(data)
        return True

    def serve_all(self):
        """Serves all requests and replies for as long as the connection is 
        alive."""
        try:
            while True:
                self.serve(0.1)
        except (socket.error, select_error, IOError):
            if not self.closed:
                raise
        except EOFError:
            pass
        finally:
            self.close()

    def poll_all(self, timeout = 0):
        """Serves all requests and replies that arrive within the given interval.
        
        :returns: ``True`` if at least a single transaction was served, ``False`` otherwise
        """
        at_least_once = False
        t0 = time.time()
        duration = timeout
        try:
            while True:
                if self.poll(duration):
                    at_least_once = True
                if timeout is not None:
                    duration = t0 + timeout - time.time()
                    if duration < 0:
                        break
        except EOFError:
            pass
        return at_least_once

    #
    # requests
    #
    def sync_request(self, handler, *args):
        """Sends a synchronous request (waits for the reply to arrive)
        
        :raises: any exception that the requets may be generated
        :returns: the result of the request
        """
        seq = self._send_request(handler, args)
        while seq not in self._sync_replies:
            self.serve(0.1)
        isexc, obj = self._sync_replies.pop(seq)
        if isexc:
            raise obj
        else:
            return obj

    def _async_request(self, handler, args = (), callback = (lambda a, b: None)):
        seq = self._send_request(handler, args)
        self._async_callbacks[seq] = callback
    def async_request(self, handler, *args, **kwargs):
        """Send an asynchronous request (does not wait for it to finish)
        
        :returns: an :class:`rpyc.core.async.AsyncResult` object, which will
                  eventually hold the result (or exception)
        """
        timeout = kwargs.pop("timeout", None)
        if kwargs:
            raise TypeError("got unexpected keyword argument(s) %s" % (list(kwargs.keys()),))
        res = AsyncResult(weakref.proxy(self))
        self._async_request(handler, args, res)
        if timeout is not None:
            res.set_expiry(timeout)
        return res

    @property
    def root(self):
        """Fetches the root object (service) of the other party"""
        if self._remote_root is None:
            self._remote_root = self.sync_request(consts.HANDLE_GETROOT)
        return self._remote_root

    #
    # attribute access
    #
    def _check_attr(self, obj, name):
        if self._config["allow_exposed_attrs"]:
            if name.startswith(self._config["exposed_prefix"]):
                name2 = name
            else:
                name2 = self._config["exposed_prefix"] + name
            if hasattr(obj, name2):
                return name2
        if self._config["allow_all_attrs"]:
            return name
        if self._config["allow_safe_attrs"] and name in self._config["safe_attrs"]:
            return name
        if self._config["allow_public_attrs"] and not name.startswith("_"):
            return name
        return False

    def _access_attr(self, oid, name, args, overrider, param, default):
        if is_py3k:
            if type(name) is bytes:
                name = str(name, "utf8")
            elif type(name) is not str:
                raise TypeError("name must be a string")
        else:
            if type(name) not in (str, unicode):
                raise TypeError("name must be a string")
            name = str(name) # IronPython issue #10 + py3k issue
        obj = self._local_objects[oid]
        accessor = getattr(type(obj), overrider, None)
        if accessor is None:
            name2 = self._check_attr(obj, name)
            if not self._config[param] or not name2:
                raise AttributeError("cannot access %r" % (name,))
            accessor = default
            name = name2
        return accessor(obj, name, *args)

    #
    # request handlers
    #
    def _handle_ping(self, data):
        return data
    def _handle_close(self):
        self._cleanup()
    def _handle_getroot(self):
        return self._local_root
    def _handle_del(self, oid):
        self._local_objects.decref(oid)
    def _handle_repr(self, oid):
        return repr(self._local_objects[oid])
    def _handle_str(self, oid):
        return str(self._local_objects[oid])
    def _handle_cmp(self, oid, other):
        # cmp() might enter recursive resonance... yet another workaround
        #return cmp(self._local_objects[oid], other)
        obj = self._local_objects[oid]
        try:
            return type(obj).__cmp__(obj, other)
        except (AttributeError, TypeError):
            return NotImplemented
    def _handle_hash(self, oid):
        return hash(self._local_objects[oid])
    def _handle_call(self, oid, args, kwargs=()):
        return self._local_objects[oid](*args, **dict(kwargs))
    def _handle_dir(self, oid):
        return tuple(dir(self._local_objects[oid]))
    def _handle_inspect(self, oid):
        return tuple(netref.inspect_methods(self._local_objects[oid]))
    def _handle_getattr(self, oid, name):
        return self._access_attr(oid, name, (), "_rpyc_getattr", "allow_getattr", getattr)
    def _handle_delattr(self, oid, name):
        return self._access_attr(oid, name, (), "_rpyc_delattr", "allow_delattr", delattr)
    def _handle_setattr(self, oid, name, value):
        return self._access_attr(oid, name, (value,), "_rpyc_setattr", "allow_setattr", setattr)
    def _handle_callattr(self, oid, name, args, kwargs):
        return self._handle_getattr(oid, name)(*args, **dict(kwargs))
    def _handle_pickle(self, oid, proto):
        if not self._config["allow_pickle"]:
            raise ValueError("pickling is disabled")
        return pickle.dumps(self._local_objects[oid], proto)
    def _handle_buffiter(self, oid, count):
        items = []
        obj = self._local_objects[oid]
        i = 0
        try:
            while i < count:
                items.append(next(obj))
                i += 1
        except StopIteration:
            pass
        return tuple(items)
    def _handle_oldslicing(self, oid, attempt, fallback, start, stop, args):
        try:
            # first try __xxxitem__
            getitem = self._handle_getattr(oid, attempt)
            return getitem(slice(start, stop), *args)
        except Exception:
            # fallback to __xxxslice__. see issue #41
            if stop is None:
                stop = maxint
            getslice = self._handle_getattr(oid, fallback)
            return getslice(start, stop, *args)

    # collect handlers
    _HANDLERS = {}
    for name, obj in dict(locals()).items():
        if name.startswith("_handle_"):
            name2 = "HANDLE_" + name[8:].upper()
            if hasattr(consts, name2):
                _HANDLERS[getattr(consts, name2)] = obj
            else:
                raise NameError("no constant defined for %r", name)
    del name, name2, obj


########NEW FILE########
__FILENAME__ = reactor
import os
import select    
import threading


class SelectReactor(object):
    TIMEOUT = 0.5 if os.name == "nt" else None
    def __init__(self):
        self._active = False
        self._readfds = set()
    def register_read(self, fileobj):
        self._readfds.append(fileobj)
    def run(self):
        self._active = True
        while self._active:
            rlist, _, _ = select.select(self._readfds, (), (), self.TIMEOUT)
            for fileobj in rlist:
                data = fileobj.recv(16000)
                if not data:
                    fileobj.close()
                    self._readfds.discard(fileobj)


_reactor = SelectReactor()

def _reactor_thread():
    pass


_thd = None
def start_reactor():
    global _thd
    if _thd is None:
        raise ValueError("already started")
    _thd = threading.Thread("rpyc reactor thread", target = _reactor_thread)
    _thd.setDaemon(True)
    _thd.start()



########NEW FILE########
__FILENAME__ = service
"""
Services are the heart of RPyC: each side of the connection exposes a *service*,
which define the capabilities available to the other side. 

Note that the services by both parties need not be symmetric, e.g., one side may 
exposed *service A*, while the other may expose *service B*. As long as the two
can interoperate, you're good to go.
"""
from rpyc.lib.compat import execute, is_py3k


class Service(object):
    """The service base-class. Derive from this class to implement custom RPyC
    services:
    
    * The name of the class implementing the ``Foo`` service should match the
      pattern ``FooService`` (suffixed by the word 'Service') ::
      
          class FooService(Service):
              pass
          
          FooService.get_service_name() # 'FOO'
          FooService.get_service_aliases() # ['FOO']
    
    * To supply a different name or aliases, use the ``ALIASES`` class attribute ::
    
          class Foobar(Service):
              ALIASES = ["foo", "bar", "lalaland"]
          
          Foobar.get_service_name() # 'FOO'
          Foobar.get_service_aliases() # ['FOO', 'BAR', 'LALALAND']
    
    * Override :func:`on_connect` to perform custom initialization
    
    * Override :func:`on_disconnect` to perform custom finalization
    
    * To add exposed methods or attributes, simply define them normally,
      but prefix their name by ``exposed_``, e.g. ::
    
          class FooService(Service):
              def exposed_add(self, x, y):
                  return x + y
    
    * All other names (not prefixed by ``exposed_``) are local (not accessible
      to the other party)
    
    .. note::
       You can override ``_rpyc_getattr``, ``_rpyc_setattr`` and ``_rpyc_delattr``
       to change attribute lookup -- but beware of possible **security implications!**
    """
    __slots__ = ["_conn"]
    ALIASES = ()

    def __init__(self, conn):
        self._conn = conn
    def on_connect(self):
        """called when the connection is established"""
        pass
    def on_disconnect(self):
        """called when the connection had already terminated for cleanup
        (must not perform any IO on the connection)"""
        pass

    def _rpyc_getattr(self, name):
        if name.startswith("exposed_"):
            name = name
        else:
            name = "exposed_" + name
        return getattr(self, name)
    def _rpyc_delattr(self, name):
        raise AttributeError("access denied")
    def _rpyc_setattr(self, name, value):
        raise AttributeError("access denied")

    @classmethod
    def get_service_aliases(cls):
        """returns a list of the aliases of this service"""
        if cls.ALIASES:
            return tuple(str(n).upper() for n in cls.ALIASES)
        name = cls.__name__.upper()
        if name.endswith("SERVICE"):
            name = name[:-7]
        return (name,)
    @classmethod
    def get_service_name(cls):
        """returns the canonical name of the service (which is its first 
        alias)"""
        return cls.get_service_aliases()[0]

    exposed_get_service_aliases = get_service_aliases
    exposed_get_service_name = get_service_name


class VoidService(Service):
    """void service - an do-nothing service"""
    __slots__ = ()


class ModuleNamespace(object):
    """used by the :class:`SlaveService` to implement the magical 
    'module namespace'"""
    
    __slots__ = ["__getmodule", "__cache", "__weakref__"]
    def __init__(self, getmodule):
        self.__getmodule = getmodule
        self.__cache = {}
    def __contains__(self, name):
        try:
            self[name]
        except ImportError:
            return False
        else:
            return True
    def __getitem__(self, name):
        if type(name) is tuple:
            name = ".".join(name)
        if name not in self.__cache:
            self.__cache[name] = self.__getmodule(name)
        return self.__cache[name]
    def __getattr__(self, name):
        return self[name]

class SlaveService(Service):
    """The SlaveService allows the other side to perform arbitrary imports and
    execution arbitrary code on the server. This is provided for compatibility 
    with the classic RPyC (2.6) modus operandi.
    
    This service is very useful in local, secure networks, but it exposes
    a **major security risk** otherwise."""
    __slots__ = ["exposed_namespace"]

    def on_connect(self):
        self.exposed_namespace = {}
        self._conn._config.update(dict(
            allow_all_attrs = True,
            allow_pickle = True,
            allow_getattr = True,
            allow_setattr = True,
            allow_delattr = True,
            import_custom_exceptions = True,
            instantiate_custom_exceptions = True,
            instantiate_oldstyle_exceptions = True,
        ))
        # shortcuts
        self._conn.modules = ModuleNamespace(self._conn.root.getmodule)
        self._conn.eval = self._conn.root.eval
        self._conn.execute = self._conn.root.execute
        self._conn.namespace = self._conn.root.namespace
        if is_py3k:
            self._conn.builtin = self._conn.modules.builtins
        else:
            self._conn.builtin = self._conn.modules.__builtin__
        self._conn.builtins = self._conn.builtin

    def exposed_execute(self, text):
        """execute arbitrary code (using ``exec``)"""
        execute(text, self.exposed_namespace)
    def exposed_eval(self, text):
        """evaluate arbitrary code (using ``eval``)"""
        return eval(text, self.exposed_namespace)
    def exposed_getmodule(self, name):
        """imports an arbitrary module"""
        return __import__(name, None, None, "*")
    def exposed_getconn(self):
        """returns the local connection instance to the other side"""
        return self._conn



########NEW FILE########
__FILENAME__ = stream
"""
An abstraction layer over OS-dependent file-like objects, that provides a 
consistent view of a *duplex byte stream*.
"""
import sys
import os
import socket
import time
import errno
from rpyc.lib import safe_import
from rpyc.lib.compat import select, select_error, BYTES_LITERAL, get_exc_errno, maxint
win32file = safe_import("win32file")
win32pipe = safe_import("win32pipe")
msvcrt = safe_import("msvcrt")
ssl = safe_import("ssl")


retry_errnos = (errno.EAGAIN, errno.EWOULDBLOCK)


class Stream(object):
    """Base Stream"""
    
    __slots__ = ()
    def close(self):
        """closes the stream, releasing any system resources associated with it"""
        raise NotImplementedError()
    @property
    def closed(self):
        """tests whether the stream is closed or not"""
        raise NotImplementedError()
    def fileno(self):
        """returns the stream's file descriptor"""
        raise NotImplementedError()
    def poll(self, timeout):
        """indicates whether the stream has data to read (within *timeout* 
        seconds)"""
        try:
            while True:
                try:
                    rl, _, _ = select([self], [], [], timeout)
                except select_error as ex:
                    if ex[0] == errno.EINTR:
                        continue
                    else:
                        raise
                else:
                    break
        except ValueError as ex:
            # i get this some times: "ValueError: file descriptor cannot be a negative integer (-1)"
            # let's translate it to select.error
            raise select_error(str(ex))
        return bool(rl)
    def read(self, count):
        """reads **exactly** *count* bytes, or raise EOFError
        
        :param count: the number of bytes to read
        
        :returns: read data
        """
        raise NotImplementedError()
    def write(self, data):
        """writes the entire *data*, or raise EOFError
        
        :param data: a string of binary data
        """
        raise NotImplementedError()


class ClosedFile(object):
    """Represents a closed file object (singleton)"""
    __slots__ = ()
    def __getattr__(self, name):
        if name.startswith("__"): # issue 71
            raise AttributeError("stream has been closed")
        raise EOFError("stream has been closed")
    def close(self):
        pass
    @property
    def closed(self):
        return True
    def fileno(self):
        raise EOFError("stream has been closed")
ClosedFile = ClosedFile()


class SocketStream(Stream):
    """A stream over a socket"""
    
    __slots__ = ("sock",)
    MAX_IO_CHUNK = 8000
    def __init__(self, sock):
        self.sock = sock

    @classmethod
    def _connect(cls, host, port, family = socket.AF_INET, socktype = socket.SOCK_STREAM,
            proto = 0, timeout = 3, nodelay = False, keepalive = False):
        family, socktype, proto, _, sockaddr = socket.getaddrinfo(host, port, family, 
            socktype, proto)[0]
        s = socket.socket(family, socktype, proto)
        s.settimeout(timeout)
        s.connect(sockaddr)
        if nodelay:
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if keepalive:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Linux specific: after 10 idle minutes, start sending keepalives every 5 minutes. 
            # Drop connection after 10 failed keepalives
            if hasattr(socket, "TCP_KEEPIDLE") and hasattr(socket, "TCP_KEEPINTVL") and hasattr(socket, "TCP_KEEPCNT"):
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10 * 60)
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5 * 60)
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 10)    
        return s
    
    @classmethod
    def connect(cls, host, port, **kwargs):
        """factory method that creates a ``SocketStream`` over a socket connected
        to *host* and *port*
        
        :param host: the host name
        :param port: the TCP port
        :param kwargs: additional keyword arguments: ``family``, ``socktype``,
                       ``proto``, ``timeout``, ``nodelay``, passed directly to 
                       the ``socket`` constructor, or ``ipv6``.
        :param ipv6: if True, creates an IPv6 socket (``AF_INET6``); otherwise
                     an IPv4 (``AF_INET``) socket is created
        
        :returns: a :class:`SocketStream`
        """
        if kwargs.pop("ipv6", False):
            kwargs["family"] = socket.AF_INET6
        return cls(cls._connect(host, port, **kwargs))

    @classmethod
    def ssl_connect(cls, host, port, ssl_kwargs, **kwargs):
        """factory method that creates a ``SocketStream`` over an SSL-wrapped 
        socket, connected to *host* and *port* with the given credentials.
        
        :param host: the host name
        :param port: the TCP port
        :param ssl_kwargs: a dictionary of keyword arguments to be passed 
                           directly to ``ssl.wrap_socket``
        :param kwargs: additional keyword arguments: ``family``, ``socktype``,
                       ``proto``, ``timeout``, ``nodelay``, passed directly to 
                       the ``socket`` constructor, or ``ipv6``.
        :param ipv6: if True, creates an IPv6 socket (``AF_INET6``); otherwise
                     an IPv4 (``AF_INET``) socket is created
        
        :returns: a :class:`SocketStream`
        """
        if kwargs.pop("ipv6", False):
            kwargs["family"] = socket.AF_INET6
        s = cls._connect(host, port, **kwargs)
        s2 = ssl.wrap_socket(s, **ssl_kwargs)
        return cls(s2)
    
    @property
    def closed(self):
        return self.sock is ClosedFile
    def close(self):
        if not self.closed:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
        self.sock.close()
        self.sock = ClosedFile
    def fileno(self):
        try:
            return self.sock.fileno()
        except socket.error:
            self.close()
            ex = sys.exc_info()[1]
            if get_exc_errno(ex) == errno.EBADF:
                raise EOFError()
            else:
                raise
    
    def read(self, count):
        data = []
        while count > 0:
            try:
                buf = self.sock.recv(min(self.MAX_IO_CHUNK, count))
            except socket.timeout:
                continue
            except socket.error:
                ex = sys.exc_info()[1]
                if get_exc_errno(ex) in retry_errnos:
                    # windows just has to be a bitch
                    continue
                self.close()
                raise EOFError(ex)
            if not buf:
                self.close()
                raise EOFError("connection closed by peer")
            data.append(buf)
            count -= len(buf)
        return BYTES_LITERAL("").join(data)
    def write(self, data):
        try:
            while data:
                count = self.sock.send(data[:self.MAX_IO_CHUNK])
                data = data[count:]
        except socket.error:
            ex = sys.exc_info()[1]
            self.close()
            raise EOFError(ex)

class TunneledSocketStream(SocketStream):
    """A socket stream over an SSH tunnel (terminates the tunnel when the connection closes)"""
    
    __slots__ = ("tun",)
    def __init__(self, sock):
        self.sock = sock
        self.tun = None
    def close(self):
        SocketStream.close(self)
        if self.tun:
            self.tun.close()

class PipeStream(Stream):
    """A stream over two simplex pipes (one used to input, another for output)"""
    
    __slots__ = ("incoming", "outgoing")
    MAX_IO_CHUNK = 32000
    def __init__(self, incoming, outgoing):
        outgoing.flush()
        self.incoming = incoming
        self.outgoing = outgoing
    @classmethod
    def from_std(cls):
        """factory method that creates a PipeStream over the standard pipes 
        (``stdin`` and ``stdout``)
        
        :returns: a :class:`PipeStream` instance
        """
        return cls(sys.stdin, sys.stdout)
    @classmethod
    def create_pair(cls):
        """factory method that creates two pairs of anonymous pipes, and 
        creates two PipeStreams over them. Useful for ``fork()``.
        
        :returns: a tuple of two :class:`PipeStream` instances
        """
        r1, w1 = os.pipe()
        r2, w2 = os.pipe()
        side1 = cls(os.fdopen(r1, "rb"), os.fdopen(w2, "wb"))
        side2 = cls(os.fdopen(r2, "rb"), os.fdopen(w1, "wb"))
        return side1, side2
    @property
    def closed(self):
        return self.incoming is ClosedFile
    def close(self):
        self.incoming.close()
        self.outgoing.close()
        self.incoming = ClosedFile
        self.outgoing = ClosedFile
    def fileno(self):
        return self.incoming.fileno()
    def read(self, count):
        data = []
        try:
            while count > 0:
                buf = os.read(self.incoming.fileno(), min(self.MAX_IO_CHUNK, count))
                if not buf:
                    raise EOFError("connection closed by peer")
                data.append(buf)
                count -= len(buf)
        except EOFError:
            self.close()
            raise
        except EnvironmentError:
            ex = sys.exc_info()[1]
            self.close()
            raise EOFError(ex)
        return BYTES_LITERAL("").join(data)
    def write(self, data):
        try:
            while data:
                chunk = data[:self.MAX_IO_CHUNK]
                written = os.write(self.outgoing.fileno(), chunk)
                data = data[written:]
        except EnvironmentError:
            ex = sys.exc_info()[1]
            self.close()
            raise EOFError(ex)


class Win32PipeStream(Stream):
    """A stream over two simplex pipes (one used to input, another for output).
    This is an implementation for Windows pipes (which suck)"""
    
    __slots__ = ("incoming", "outgoing", "_fileno", "_keepalive")
    PIPE_BUFFER_SIZE = 130000
    MAX_IO_CHUNK = 32000

    def __init__(self, incoming, outgoing):
        self._keepalive = (incoming, outgoing)
        if hasattr(incoming, "fileno"):
            self._fileno = incoming.fileno()
            incoming = msvcrt.get_osfhandle(incoming.fileno())
        if hasattr(outgoing, "fileno"):
            outgoing = msvcrt.get_osfhandle(outgoing.fileno())
        self.incoming = incoming
        self.outgoing = outgoing
    @classmethod
    def from_std(cls):
        return cls(sys.stdin, sys.stdout)
    @classmethod
    def create_pair(cls):
        r1, w1 = win32pipe.CreatePipe(None, cls.PIPE_BUFFER_SIZE)
        r2, w2 = win32pipe.CreatePipe(None, cls.PIPE_BUFFER_SIZE)
        return cls(r1, w2), cls(r2, w1)

    def fileno(self):
        return self._fileno
    @property
    def closed(self):
        return self.incoming is ClosedFile
    def close(self):
        if self.closed:
            return
        try:
            win32file.CloseHandle(self.incoming)
        except Exception:
            pass
        self.incoming = ClosedFile
        try:
            win32file.CloseHandle(self.outgoing)
        except Exception:
            pass
        self.outgoing = ClosedFile
    def read(self, count):
        try:
            data = []
            while count > 0:
                dummy, buf = win32file.ReadFile(self.incoming, int(min(self.MAX_IO_CHUNK, count)))
                count -= len(buf)
                data.append(buf)
        except TypeError:
            ex = sys.exc_info()[1]
            if not self.closed:
                raise
            raise EOFError(ex)
        except win32file.error:
            ex = sys.exc_info()[1]
            self.close()
            raise EOFError(ex)
        return BYTES_LITERAL("").join(data)
    def write(self, data):
        try:
            while data:
                dummy, count = win32file.WriteFile(self.outgoing, data[:self.MAX_IO_CHUNK])
                data = data[count:]
        except TypeError:
            ex = sys.exc_info()[1]
            if not self.closed:
                raise
            raise EOFError(ex)
        except win32file.error:
            ex = sys.exc_info()[1]
            self.close()
            raise EOFError(ex)

    def poll(self, timeout, interval = 0.1):
        """a poor man's version of select()"""
        if timeout is None:
            timeout = maxint
        length = 0
        tmax = time.time() + timeout
        try:
            while length == 0:
                length = win32pipe.PeekNamedPipe(self.incoming, 0)[1]
                if time.time() >= tmax:
                    break
                time.sleep(interval)
        except TypeError:
            ex = sys.exc_info()[1]
            if not self.closed:
                raise
            raise EOFError(ex)
        return length != 0


class NamedPipeStream(Win32PipeStream):
    """A stream over two named pipes (one used to input, another for output).
    Windows implementation."""
    
    NAMED_PIPE_PREFIX = r'\\.\pipe\rpyc_'
    PIPE_IO_TIMEOUT = 3
    CONNECT_TIMEOUT = 3
    __slots__ = ("is_server_side",)

    def __init__(self, handle, is_server_side):
        Win32PipeStream.__init__(self, handle, handle)
        self.is_server_side = is_server_side
    @classmethod
    def from_std(cls):
        raise NotImplementedError()
    @classmethod
    def create_pair(cls):
        raise NotImplementedError()

    @classmethod
    def create_server(cls, pipename, connect = True):
        """factory method that creates a server-side ``NamedPipeStream``, over 
        a newly-created *named pipe* of the given name.
        
        :param pipename: the name of the pipe. It will be considered absolute if
                         it starts with ``\\\\.``; otherwise ``\\\\.\\pipe\\rpyc``
                         will be prepended.
        :param connect: whether to connect on creation or not
        
        :returns: a :class:`NamedPipeStream` instance
        """
        if not pipename.startswith("\\\\."):
            pipename = cls.NAMED_PIPE_PREFIX + pipename
        handle = win32pipe.CreateNamedPipe(
            pipename,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
            1,
            cls.PIPE_BUFFER_SIZE,
            cls.PIPE_BUFFER_SIZE,
            cls.PIPE_IO_TIMEOUT * 1000,
            None
        )
        inst = cls(handle, True)
        if connect:
            inst.connect_server()
        return inst

    def connect_server(self):
        """connects the server side of an unconnected named pipe (blocks 
        until a connection arrives)"""
        if not self.is_server_side:
            raise ValueError("this must be the server side")
        win32pipe.ConnectNamedPipe(self.incoming, None)

    @classmethod
    def create_client(cls, pipename):
        """factory method that creates a client-side ``NamedPipeStream``, over 
        a newly-created *named pipe* of the given name.
        
        :param pipename: the name of the pipe. It will be considered absolute if
                         it starts with ``\\\\.``; otherwise ``\\\\.\\pipe\\rpyc``
                         will be prepended.
        
        :returns: a :class:`NamedPipeStream` instance
        """
        if not pipename.startswith("\\\\."):
            pipename = cls.NAMED_PIPE_PREFIX + pipename
        handle = win32file.CreateFile(
            pipename,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        return cls(handle, False)

    def close(self):
        if self.closed:
            return
        if self.is_server_side:
            win32file.FlushFileBuffers(self.outgoing)
            win32pipe.DisconnectNamedPipe(self.outgoing)
        Win32PipeStream.close(self)


if sys.platform == "win32":
    PipeStream = Win32PipeStream


########NEW FILE########
__FILENAME__ = vinegar
"""
**Vinegar** ("when things go sour") is a safe serializer for exceptions.
The :data`configuration parameters <rpyc.core.protocol.DEFAULT_CONFIG>` control
its mode of operation, for instance, whether to allow *old-style* exceptions 
(that do not derive from ``Exception``), whether to allow the :func:`load` to
import custom modules (imposes a security risk), etc. 

Note that by changing the configuration parameters, this module can be made 
non-secure. Keep this in mind.
"""
import sys
import traceback
try:
    import exceptions as exceptions_module
except ImportError:
    import builtins as exceptions_module
try:
    from types import InstanceType, ClassType
except ImportError:
    ClassType = type

from rpyc.core import brine
from rpyc.core import consts
from rpyc.lib.compat import is_py3k


try:
    BaseException
except NameError:
    # python 2.4 compatible
    BaseException = Exception

def dump(typ, val, tb, include_local_traceback):
    """Dumps the given exceptions info, as returned by ``sys.exc_info()``
    
    :param typ: the exception's type (class)
    :param val: the exceptions' value (instance)
    :param tb: the exception's traceback (a ``traceback`` object)
    :param include_local_traceback: whether or not to include the local traceback
                                    in the dumped info. This may expose the other
                                    side to implementation details (code) and 
                                    package structure, and may theoretically impose
                                    a security risk.
    
    :returns: A tuple of ``((module name, exception name), arguments, attributes, 
              traceback text)``. This tuple can be safely passed to 
              :func:`brine.dump <rpyc.core.brine.dump>`
    """
    if typ is StopIteration:
        return consts.EXC_STOP_ITERATION # optimization
    if type(typ) is str:
        return typ

    if include_local_traceback:
        tbtext = "".join(traceback.format_exception(typ, val, tb))
    else:
        tbtext = "<traceback denied>"
    attrs = []
    args = []
    ignored_attrs = frozenset(["_remote_tb", "with_traceback"])
    for name in dir(val):
        if name == "args":
            for a in val.args:
                if brine.dumpable(a):
                    args.append(a)
                else:
                    args.append(repr(a))
        elif name.startswith("_") or name in ignored_attrs:
            continue
        else:
            try:
                attrval = getattr(val, name)
            except AttributeError:
                # skip this attr. see issue #108
                continue
            if not brine.dumpable(attrval):
                attrval = repr(attrval)
            attrs.append((name, attrval))
    return (typ.__module__, typ.__name__), tuple(args), tuple(attrs), tbtext

def load(val, import_custom_exceptions, instantiate_custom_exceptions, instantiate_oldstyle_exceptions):
    """
    Loads a dumped exception (the tuple returned by :func:`dump`) info a 
    throwable exception object. If the exception cannot be instantiated for any
    reason (i.e., the security parameters do not allow it, or the exception 
    class simply doesn't exist on the local machine), a :class:`GenericException`
    instance will be returned instead, containing all of the original exception's
    details.
    
    :param val: the dumped exception
    :param import_custom_exceptions: whether to allow this function to import custom modules 
                                     (imposes a security risk)
    :param instantiate_custom_exceptions: whether to allow this function to instantiate "custom 
                                          exceptions" (i.e., not one of the built-in exceptions,
                                          such as ``ValueError``, ``OSError``, etc.)
    :param instantiate_oldstyle_exceptions: whether to allow this function to instantiate exception 
                                            classes that do not derive from ``BaseException``.
                                            This is required to support old-style exceptions. 
                                            Not applicable for Python 3 and above.
    
    :returns: A throwable exception object
    """
    if val == consts.EXC_STOP_ITERATION:
        return StopIteration # optimization
    if type(val) is str:
        return val # deprecated string exceptions

    (modname, clsname), args, attrs, tbtext = val
    if import_custom_exceptions and modname not in sys.modules:
        try:
            __import__(modname, None, None, "*")
        except Exception:
            pass
    
    if instantiate_custom_exceptions:
        if modname in sys.modules:
            cls = getattr(sys.modules[modname], clsname, None)
        else:
            cls = None
    elif modname == exceptions_module.__name__:
        cls = getattr(exceptions_module, clsname, None)
    else:
        cls = None

    if is_py3k:
        if not isinstance(cls, type) or not issubclass(cls, BaseException):
            cls = None
    else:
        if not isinstance(cls, (type, ClassType)):
            cls = None
        elif issubclass(cls, ClassType) and not instantiate_oldstyle_exceptions:
            cls = None
        elif not issubclass(cls, BaseException):
            cls = None

    if cls is None:
        fullname = "%s.%s" % (modname, clsname)
        if fullname not in _generic_exceptions_cache:
            fakemodule = {"__module__" : "%s/%s" % (__name__, modname)}
            if isinstance(GenericException, ClassType):
                _generic_exceptions_cache[fullname] = ClassType(fullname, (GenericException,), fakemodule)
            else:
                _generic_exceptions_cache[fullname] = type(fullname, (GenericException,), fakemodule)
        cls = _generic_exceptions_cache[fullname]

    cls = _get_exception_class(cls)
    
    # support old-style exception classes
    if ClassType is not type and isinstance(cls, ClassType):
        exc = InstanceType(cls)
    else:
        exc = cls.__new__(cls)

    exc.args = args
    for name, attrval in attrs:
        setattr(exc, name, attrval)
    exc._remote_tb = tbtext
    return exc


class GenericException(Exception):
    """A 'generic exception' that is raised when the exception the gotten from
    the other party cannot be instantiated locally"""
    pass

_generic_exceptions_cache = {}
_exception_classes_cache = {}

def _get_exception_class(cls):
    if cls in _exception_classes_cache:
        return _exception_classes_cache[cls]

    # subclass the exception class' to provide a version of __str__ that supports _remote_tb
    class Derived(cls):
        def __str__(self):
            try:
                text = cls.__str__(self)
            except Exception:
                text = "<Unprintable exception>"
            if hasattr(self, "_remote_tb"):
                text += "\n\n========= Remote Traceback (%d) =========\n%s" % (
                    self._remote_tb.count("\n\n========= Remote Traceback") + 1, self._remote_tb)
            return text
        def __repr__(self):
            return str(self)
    
    Derived.__name__ = cls.__name__
    Derived.__module__ = cls.__module__
    _exception_classes_cache[cls] = Derived
    return Derived


########NEW FILE########
__FILENAME__ = retunnel
import socket
import random
import time
from Queue import Queue, Empty as QueueEmpty
from rpyc.core.stream import Stream, TunneledSocketStream, ClosedFile


COOKIE_LENGTH = 8

class ReconnectingTunnelStream(Stream):
    RETRIES = 5

    def __init__(self, remote_machine, destination_port, retries = RETRIES):
        self.remote_machine = remote_machine
        self.destination_port = destination_port
        self.retries = retries
        self.cookie = "".join(chr(random.randint(0, 255)) for _ in range(COOKIE_LENGTH))
        self.stream = None

    def close(self):
        if self.stream is not None and not self.closed:
            self.stream.close()
        self.stream = ClosedFile

    @property
    def closed(self):
        return self.stream is ClosedFile

    def fileno(self):
        return self._safeio(lambda stream: stream.fileno())

    def _reconnect(self):
        # choose random local_port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("localhost", 0))
        local_port = s.getsockname()[1]
        s.close()
        # create a tunnel from local_port:destination_port and connect it
        tun = self.remote_machine.tunnel(local_port, self.destination_port)
        stream = TunneledSocketStream.connect("localhost", local_port)
        stream.write(self.cookie)
        stream.tun = tun
        # print "ReconnectingTunnelStream._reconnect: established a tunnel from localhost:%r to %s:%r" % (
        #    local_port, self.remote_machine, self.destination_port)
        return stream

    def _safeio(self, callback):
        if self.closed:
            raise ValueError("I/O operation on closed file")
        for i in range(self.retries):
            try:
                if not self.stream:
                    self.stream = self._reconnect()
                return callback(self.stream)
            except (EOFError, IOError, OSError, socket.error):
                if i >= self.retries - 1:
                    raise
                if self.stream:
                    self.stream.close()
                self.stream = None
                time.sleep(0.5)

    def write(self, data):
        # print "ReconnectingTunnelStream.write(%r)" % (len(data),)
        return self._safeio(lambda stream: stream.write(data))

    def read(self, count):
        # print "ReconnectingTunnelStream.read(%r)" % (count,)
        return self._safeio(lambda stream: stream.read(count))


class MultiplexingListener(object):
    REACCEPT_TIMEOUT = 10
    RETRIES = 5

    def __init__(self, reaccept_timeout = REACCEPT_TIMEOUT, retries = RETRIES):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.reaccept_timeout = reaccept_timeout
        self.retries = retries
        self.client_map = {}

    def close(self):
        self.listener.close()
        self.listener = ClosedFile
    def fileno(self):
        return self.listener.getfileno()
    def getsockname(self):
        return self.listener.getsockname()
    def listen(self, backlog):
        self.listener.listen(backlog)
    def bind(self, addrinfo):
        self.listener.bind(addrinfo)
    def settimeout(self, timeout):
        self.listener.settimeout(timeout)
    def setsockopt(self, level, option, value):
        return self.listener.setsockopt(level, option, value)
    def shutdown(self, mode):
        self.listener.shutdown(mode)

    def accept(self):
        while True:
            # print "MultiplexingListener.accept"
            sock, addrinfo = self.listener.accept()
            cookie = sock.recv(COOKIE_LENGTH)
            # print "MultiplexingListener.accept: got cookie %r" % (cookie,)

            if cookie not in self.client_map:
                self.client_map[cookie] = Queue(1)
                self.client_map[cookie].put(sock)
                # print "MultiplexingListener.accept: new, map=%r" % (self.client_map,)

                resock = ReconnectingSocket(self, cookie, self.retries)
                return resock, addrinfo
            else:
                self.client_map[cookie].put(sock)
                # print "MultiplexingListener.accept: old, map=%r" % (self.client_map,)

    def reaccept(self, cookie):
        # print "MultiplexingListener.reaccept: %r" % (cookie,)
        try:
            return self.client_map[cookie].get(self.reaccept_timeout)
        except QueueEmpty:
            raise EOFError("Client did not reconnect within the timeout")


class ReconnectingSocket(object):
    def __init__(self, listener, cookie, retries):
        self.listener = listener
        self.cookie = cookie
        self.sock = None
        self.retries = retries
        self.blocking_mode = None
    
    def close(self):
        if self.sock:
            self.sock.close()
        self.sock = ClosedFile

    def fileno(self):
        return self._safeio(lambda sock: sock.fileno())
    def getsockname(self):
        return self._safeio(lambda sock: sock.getsockname())
    def getpeername(self):
        return self._safeio(lambda sock: sock.getpeername())
    def shutdown(self, mode):
        if self.sock:
            self.sock.shutdown(mode)

    def setblocking(self, mode):
        self.blocking_mode = mode
        if self.sock:
            self.sock.setblocking(mode)

    def _safeio(self, callback):
        for i in range(self.retries):
            if self.sock is None:
                self.sock = self.listener.reaccept(self.cookie)
                if self.blocking_mode is not None:
                    self.sock.setblocking(self.blocking_mode)

            try:
                return callback(self.sock)
            except (EOFError, IOError, OSError, socket.error):
                if i >= self.retries - 1:
                    raise
                if self.sock:
                    self.sock.close()
                self.sock = None

    def recv(self, count):
        # print "ReconnectingSocket.recv(%r)" % (count,)
        return self._safeio(lambda sock: sock.recv(count))

    def send(self, data):
        # print "ReconnectingSocket.send(%r)" % (len(data),)
        return self._safeio(lambda sock: sock.send(data))










########NEW FILE########
__FILENAME__ = splitbrain
"""
The Magnificent Splitbrain
.. versionadded:: 3.3

"""
import sys
import atexit
import threading
from contextlib import contextmanager
import functools
import gc
try:
    import __builtin__ as builtins
except ImportError:
    import builtins # python 3+
from types import ModuleType

router = threading.local()

routed_modules = set(["os", "os.path", "platform", "ntpath", "posixpath", "zipimport", "genericpath", 
    "posix", "nt", "signal", "time", "sysconfig", "_locale", "locale", "socket", "_socket", "ssl", "_ssl",
    "struct", "_struct", "_symtable", "errno", "fcntl", "grp", "pwd", "select", "spwd", "syslog", "thread", 
    "_io", "io", "subprocess", "_subprocess", "datetime", "mmap", "msvcrt", "pdb", "bdb", "glob", "fnmatch",
    #"_frozen_importlib", "imp", "exceptions"
    ])

class RoutedModule(ModuleType):
    def __init__(self, realmod):
        ModuleType.__init__(self, realmod.__name__, getattr(realmod, "__doc__", None))
        object.__setattr__(self, "__realmod__", realmod)
        object.__setattr__(self, "__file__", getattr(realmod, "__file__", None))
    def __repr__(self):
        if self.__file__:
            return "<module %r from %r>" % (self.__name__, self.__file__)
        else:
            return "<module %r (built-in)>" % (self.__name__,)
    def __dir__(self):
        return dir(self.__currmod__)
    def __getattribute__(self, name):
        if name == "__realmod__":
            return object.__getattribute__(self, "__realmod__")
        elif name == "__name__":
            return object.__getattribute__(self, "__name__")
        elif name == "__currmod__":
            modname = object.__getattribute__(self, "__name__")
            if hasattr(router, "conn"):
                return router.conn.modules[modname]
            else:
                return object.__getattribute__(self, "__realmod__")
        else:
            return getattr(self.__currmod__, name)
    def __delattr__(self, name, val):
        return setattr(self.__currmod__, name, val)
    def __setattr__(self, name, val):
        return setattr(self.__currmod__, name, val)

routed_sys_attrs = set(["byteorder", "platform", "getfilesystemencoding", "getdefaultencoding", "settrace",
    "setprofile", "setrecursionlimit", "getprofile", "getrecursionlimit", "getsizeof", "gettrace", 
    "exc_clear", "exc_info", "exc_type", "last_type", "last_value", "last_traceback",
    ])

class RoutedSysModule(ModuleType):
    def __init__(self):
        ModuleType.__init__(self, "sys", sys.__doc__)
    def __dir__(self):
        return dir(sys)
    def __getattribute__(self, name):
        if name in routed_sys_attrs and hasattr(router, "conn"):
            return getattr(router.conn.modules["sys"], name)
        else:
            return getattr(sys, name)
    def __setattr__(self, name, value):
        if name in routed_sys_attrs and hasattr(router, "conn"):
            setattr(router.conn.modules["sys"], name, value)
        else:
            setattr(sys, name, value)

rsys = RoutedSysModule()

class RemoteModule(ModuleType):
    def __init__(self, realmod):
        ModuleType.__init__(self, realmod.__name__, getattr(realmod, "__doc__", None))
        object.__setattr__(self, "__file__", getattr(realmod, "__file__", None))
    def __repr__(self):
        try:
            self.__currmod__
        except (AttributeError, ImportError):
            return "<module %r (stale)>" % (self.__name__,)
        if self.__file__:
            return "<module %r from %r>" % (self.__name__, self.__file__)
        else:
            return "<module %r (built-in)>" % (self.__name__,)
    def __dir__(self):
        return dir(self.__currmod__)

    def __getattribute__(self, name):
        if name == "__name__":
            return object.__getattribute__(self, "__name__")
        elif name == "__currmod__":
            modname = object.__getattribute__(self, "__name__")
            if not hasattr(router, "conn"):
                raise AttributeError("Module %r is not available in this context" % (modname,))
            mod = router.conn.modules._ModuleNamespace__cache.get(modname)
            if not mod:
                raise AttributeError("Module %r is not available in this context" % (modname,))
            return mod
        else:
            return getattr(self.__currmod__, name)
    def __delattr__(self, name, val):
        return setattr(self.__currmod__, name, val)
    def __setattr__(self, name, val):
        return setattr(self.__currmod__, name, val)


_orig_import = builtins.__import__

def _importer(modname, *args, **kwargs):
    if not hasattr(router, "conn"):
        return _orig_import(modname, *args, **kwargs)
    existing = sys.modules.get(modname, None)
    if type(existing) is RoutedModule:
        return existing
    
    mod = router.conn.modules[modname]
    if existing and type(existing) is RemoteModule:
        return existing
    rmod = RemoteModule(mod)
    sys.modules[modname] = rmod
    return rmod

_enabled = False
_prev_builtins = {}

def enable_splitbrain():
    """Enables (activates) the Splitbrain machinery; must be called before entering 
    ``splitbrain`` or ``localbrain`` contexts"""
    global _enabled
    if _enabled:
        return
    sys.modules["sys"] = rsys
    for modname in routed_modules:
        try:
            realmod = _orig_import(modname, [], [], "*")
        except ImportError:
            continue
        rmod = RoutedModule(realmod)
        sys.modules[modname] = rmod
        for ref in gc.get_referrers(realmod):
            if not isinstance(ref, dict) or "__name__" not in ref or ref.get("__file__") is None:
                continue
            n = ref["__name__"]
            if n in routed_modules or n.startswith("rpyc") or n.startswith("importlib") or n.startswith("imp"):
                continue
            for k, v in ref.items():
                if v is realmod:
                    #print ("## %s.%s = %s" % (ref["__name__"], ref[k], modname))
                    ref[k] = rmod

    builtins.__import__ = _importer
    for funcname in ["open", "execfile", "file"]:
        if not hasattr(builtins, funcname):
            continue
        def mkfunc(funcname, origfunc):
            @functools.wraps(getattr(builtins, funcname))
            def tlbuiltin(*args, **kwargs):
                if hasattr(router, "conn"):
                    func = getattr(router.conn.builtins, funcname)
                else:
                    func = origfunc
                return func(*args, **kwargs)
            return tlbuiltin
        origfunc = getattr(builtins, funcname)
        _prev_builtins[funcname] = origfunc
        setattr(builtins, funcname, mkfunc(funcname, origfunc))
    
    _enabled = True

def disable_splitbrain():
    """Disables (deactivates) the Splitbrain machinery"""
    global _enabled
    if not _enabled:
        return
    _enabled = False
    for funcname, origfunc in _prev_builtins.items():
        setattr(builtins, funcname, origfunc)
    for modname, mod in sys.modules.items():
        if isinstance(mod, RoutedModule):
            sys.modules[modname] = mod.__realmod__
            for ref in gc.get_referrers(mod):
                if isinstance(ref, dict) and "__name__" in ref and ref.get("__file__") is not None:
                    for k, v in ref.items():
                        if v is mod:
                            ref[k] = mod.__realmod__
    sys.modules["sys"] = sys
    builtins.__import__ = _orig_import

atexit.register(disable_splitbrain)

@contextmanager
def splitbrain(conn):
    """Enter a splitbrain context in which imports take place over the given RPyC connection (expected to 
    be a SlaveService). You can enter this context only after calling ``enable()``"""
    if not _enabled:
        enable_splitbrain()
        #raise ValueError("Splitbrain not enabled")
    prev_conn = getattr(router, "conn", None)
    prev_modules = sys.modules.copy()
    router.conn = conn
    prev_stdin = conn.modules.sys.stdin
    prev_stdout = conn.modules.sys.stdout
    prev_stderr = conn.modules.sys.stderr
    conn.modules["sys"].stdin = sys.stdin
    conn.modules["sys"].stdout = sys.stdout
    conn.modules["sys"].stderr = sys.stderr
    try:
        yield
    finally:
        conn.modules["sys"].stdin = prev_stdin
        conn.modules["sys"].stdout = prev_stdout
        conn.modules["sys"].stderr = prev_stderr
        sys.modules.clear()
        sys.modules.update(prev_modules)
        router.conn = prev_conn
        if not router.conn:
            del router.conn

@contextmanager
def localbrain():
    """Return to operate on the local machine. You can enter this context only after calling ``enable()``"""
    if not _enabled:
        raise ValueError("Splitbrain not enabled")
    prev_conn = getattr(router, "conn", None)
    prev_modules = sys.modules.copy()
    if hasattr(router, "conn"):
        del router.conn
    try:
        yield
    finally:
        sys.modules.clear()
        sys.modules.update(prev_modules)
        router.conn = prev_conn
        if not router.conn:
            del router.conn





########NEW FILE########
__FILENAME__ = colls
from __future__ import with_statement
import weakref
from threading import Lock

class WeakValueDict(object):
    """a light-weight version of weakref.WeakValueDictionary"""
    __slots__ = ("_dict",)
    def __init__(self):
        self._dict = {}
    def __repr__(self):
        return repr(self._dict)
    def __iter__(self):
        return self.iterkeys()
    def __len__(self):
        return len(self._dict)
    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True
    def get(self, key, default = None):
        try:
            return self[key]
        except KeyError:
            return default
    def __getitem__(self, key):
        obj = self._dict[key]()
        if obj is None:
            raise KeyError(key)
        return obj
    def __setitem__(self, key, value):
        def remover(wr, _dict = self._dict, key = key):
            _dict.pop(key, None)
        self._dict[key] = weakref.ref(value, remover)
    def __delitem__(self, key):
        del self._dict[key]
    def iterkeys(self):
        return self._dict.keys()
    def keys(self):
        return self._dict.keys()
    def itervalues(self):
        for k in self:
            yield self[k]
    def values(self):
        return list(self.itervalues())
    def iteritems(self):
        for k in self:
            yield k, self[k]
    def items(self):
        return list(self.iteritems())
    def clear(self):
        self._dict.clear()

class RefCountingColl(object):
    """a set-like object that implements refcounting on its contained objects"""
    __slots__ = ("_lock", "_dict")
    def __init__(self):
        self._lock = Lock()
        self._dict = {}
    def __repr__(self):
        return repr(self._dict)
    def add(self, obj):
        with self._lock:
            key = id(obj)
            slot = self._dict.get(key, None)
            if slot is None:
                slot = [obj, 0]
            else:
                slot[1] += 1
            self._dict[key] = slot
    def clear(self):
        with self._lock:
            self._dict.clear()
    def decref(self, key):
        with self._lock:
            slot = self._dict[key]
            if slot[1] < 1:
                del self._dict[key]
            else:
                slot[1] -= 1
                self._dict[key] = slot
    def __getitem__(self, key):
        with self._lock:
            return self._dict[key][0]


########NEW FILE########
__FILENAME__ = compat
"""
compatibility module for various versions of python (2.4/3+/jython)
and various platforms (posix/windows)
"""
import sys
import time

is_py3k = (sys.version_info[0] >= 3)

if is_py3k:
    exec("execute = exec")
    def BYTES_LITERAL(text):
        return bytes(text, "utf8")
    maxint = sys.maxsize
else:
    exec("""def execute(code, globals = None, locals = None):
                exec code in globals, locals""")
    def BYTES_LITERAL(text):
        return text
    maxint = sys.maxint

try:
    from struct import Struct #@UnusedImport
except ImportError:
    import struct
    class Struct(object):
        __slots__ = ["format", "size"]
        def __init__(self, format):
            self.format = format
            self.size = struct.calcsize(format)
        def pack(self, *args):
            return struct.pack(self.format, *args)
        def unpack(self, data):
            return struct.unpack(self.format, data)

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO #@UnusedImport

try:
    next = next
except NameError:
    def next(iterator):
        return iterator.next()

try:
    import cPickle as pickle
except ImportError:
    import pickle #@UnusedImport

try:
    callable = callable
except NameError:
    def callable(obj):
        return hasattr(obj, "__call__")

try:
    import select as select_module
except ImportError:
    select_module = None
    def select(*args):
        raise ImportError("select not supported on this platform")
else:
    # jython
    if hasattr(select_module, 'cpython_compatible_select'):
        from select import cpython_compatible_select as select
    else:
        from select import select

def get_exc_errno(exc):
    if hasattr(exc, "errno"):
        return exc.errno
    else:
        return exc[0]

if select_module:
    select_error = select_module.error
else:
    select_error = IOError

if hasattr(select_module, "poll"):
    class PollingPoll(object):
        def __init__(self):
            self._poll = select_module.poll()
        def register(self, fd, mode):
            flags = 0
            if "r" in mode:
                flags |= select_module.POLLIN | select_module.POLLPRI
            if "w" in mode:
                flags |= select_module.POLLOUT
            if "e" in mode:
                flags |= select_module.POLLERR
            if "h" in mode:
                # POLLRDHUP is a linux only extension, not know to python, but nevertheless
                # used and thus needed in the flags
                POLLRDHUP = 0x2000
                flags |= select_module.POLLHUP | select_module.POLLNVAL | POLLRDHUP
            self._poll.register(fd, flags)
        modify = register
        def unregister(self, fd):
            self._poll.unregister(fd)
        def poll(self, timeout = None):
            events = self._poll.poll(timeout)
            processed = []
            for fd, evt in events:
                mask = ""
                if evt & (select_module.POLLIN | select_module.POLLPRI):
                    mask += "r"
                if evt & select_module.POLLOUT:
                    mask += "w"
                if evt & select_module.POLLERR:
                    mask += "e"
                if evt & select_module.POLLHUP:
                    mask += "h"
                if evt & select_module.POLLNVAL:
                    mask += "n"
                processed.append((fd, mask))
            return processed
    
    poll = PollingPoll
else:
    class SelectingPoll(object):
        def __init__(self):
            self.rlist = set()
            self.wlist = set()
        def register(self, fd, mode):
            if "r" in mode:
                self.rlist.add(fd)
            if "w" in mode:
                self.wlist.add(fd)
        modify = register
        def unregister(self, fd):
            self.rlist.discard(fd)
            self.wlist.discard(fd)
        def poll(self, timeout = None):
            if not self.rlist and not self.wlist:
                time.sleep(timeout)
                return []  # need to return an empty array in this case
            else:
                rl, wl, _ = select(self.rlist, self.wlist, (), timeout)
                return [(fd, "r") for fd in rl] + [(fd, "w") for fd in wl]
    
    poll = SelectingPoll



########NEW FILE########
__FILENAME__ = authenticators
"""
An *authenticator* is basically a callable object that takes a socket and
"authenticates" it in some way. Upon success, it must return a tuple containing 
a **socket-like** object and its **credentials** (any object), or raise an 
:class:`AuthenticationError` upon failure. The credentials are any object you wish to
associate with the authentication, and it's stored in the connection's 
:data:`configuration dict <rpyc.core.protocol.DEFAULT_CONFIG>` under the key "credentials".

There are no constraints on what the authenticators, for instance::

    def magic_word_authenticator(sock):
        if sock.recv(5) != "Ma6ik":
            raise AuthenticationError("wrong magic word")
        return sock, None

RPyC comes bundled with an authenticator for ``SSL`` (using certificates). 
This authenticator, for instance, both verifies the peer's identity and wraps the 
socket with an encrypted transport (which replaces the original socket).

Authenticators are used by :class:`servers <rpyc.utils.server.Server>` to 
validate an incoming connection. Using them is pretty trivial ::

    s = ThreadedServer(...., authenticator = magic_word_authenticator)
    s.start()
"""
import sys
from rpyc.lib import safe_import
ssl = safe_import("ssl")

class AuthenticationError(Exception):
    """raised to signal a failed authentication attempt"""
    pass


class SSLAuthenticator(object):
    """An implementation of the authenticator protocol for ``SSL``. The given
    socket is wrapped by ``ssl.wrap_socket`` and is validated based on 
    certificates
    
    :param keyfile: the server's key file
    :param certfile: the server's certificate file
    :param ca_certs: the server's certificate authority file
    :param cert_reqs: the certificate requirements. By default, if ``ca_cert`` is
                      specified, the requirement is set to ``CERT_REQUIRED``; 
                      otherwise it is set to ``CERT_NONE``
    :param ciphers: the list of ciphers to use, or ``None``, if you do not wish
                    to restrict the available ciphers. New in Python 2.7/3.2
    :param ssl_version: the SSL version to use
    
    Refer to `ssl.wrap_socket <http://docs.python.org/dev/library/ssl.html#ssl.wrap_socket>`_
    for more info.
    """
    
    def __init__(self, keyfile, certfile, ca_certs = None, cert_reqs = None, 
            ssl_version = None, ciphers = None):
        self.keyfile = keyfile
        self.certfile = certfile
        self.ca_certs = ca_certs
        self.ciphers = ciphers
        if cert_reqs is None:
            if ca_certs:
                self.cert_reqs = ssl.CERT_REQUIRED
            else:
                self.cert_reqs = ssl.CERT_NONE
        else:
            self.cert_reqs = cert_reqs
        if ssl_version is None:
            self.ssl_version = ssl.PROTOCOL_TLSv1
        else:
            self.ssl_version = ssl_version

    def __call__(self, sock):
        kwargs = dict(keyfile = self.keyfile, certfile = self.certfile,
            server_side = True, ca_certs = self.ca_certs, cert_reqs = self.cert_reqs,
            ssl_version = self.ssl_version)
        if self.ciphers is not None:
            kwargs["ciphers"] = self.ciphers
        try:
            sock2 = ssl.wrap_socket(sock, **kwargs)
        except ssl.SSLError:
            ex = sys.exc_info()[1]
            raise AuthenticationError(str(ex))
        return sock2, sock2.getpeercert()




########NEW FILE########
__FILENAME__ = classic
from __future__ import with_statement
import sys
import os
import inspect
from rpyc.lib.compat import pickle, execute, is_py3k
from rpyc import SlaveService
from rpyc.utils import factory
from rpyc.core.service import ModuleNamespace
from contextlib import contextmanager


DEFAULT_SERVER_PORT = 18812
DEFAULT_SERVER_SSL_PORT = 18821


#===============================================================================
# connecting
#===============================================================================
def connect_channel(channel):
    """
    Creates an RPyC connection over the given ``channel``
    
    :param channel: the :class:`rpyc.core.channel.Channel` instance
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    return factory.connect_channel(channel, SlaveService)

def connect_stream(stream):
    """
    Creates an RPyC connection over the given stream

    :param channel: the :class:`rpyc.core.stream.Stream` instance
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    return factory.connect_stream(stream, SlaveService)

def connect_stdpipes():
    """
    Creates an RPyC connection over the standard pipes (``stdin`` and ``stdout``)
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    return factory.connect_stdpipes(SlaveService)

def connect_pipes(input, output):
    """
    Creates an RPyC connection over two pipes
    
    :param input: the input pipe
    :param output: the output pipe
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    return factory.connect_pipes(input, output, SlaveService)

def connect(host, port = DEFAULT_SERVER_PORT, ipv6 = False, keepalive = False):
    """
    Creates a socket connection to the given host and port.
    
    :param host: the host to connect to
    :param port: the TCP port
    :param ipv6: whether to create an IPv6 socket or IPv4
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    return factory.connect(host, port, SlaveService, ipv6 = ipv6, keepalive = keepalive)

def ssl_connect(host, port = DEFAULT_SERVER_SSL_PORT, keyfile = None,
        certfile = None, ca_certs = None, cert_reqs = None, ssl_version = None, 
        ciphers = None, ipv6 = False):
    """Creates a secure (``SSL``) socket connection to the given host and port,
    authenticating with the given certfile and CA file.
    
    :param host: the host to connect to
    :param port: the TCP port to use
    :param ipv6: whether to create an IPv6 socket or an IPv4 one
    
    The following arguments are passed directly to 
    `ssl.wrap_socket <http://docs.python.org/dev/library/ssl.html#ssl.wrap_socket>`_:
    
    :param keyfile: see ``ssl.wrap_socket``. May be ``None``
    :param certfile: see ``ssl.wrap_socket``. May be ``None``
    :param ca_certs: see ``ssl.wrap_socket``. May be ``None``
    :param cert_reqs: see ``ssl.wrap_socket``. By default, if ``ca_cert`` is specified,
                      the requirement is set to ``CERT_REQUIRED``; otherwise it is 
                      set to ``CERT_NONE``
    :param ssl_version: see ``ssl.wrap_socket``. The default is ``PROTOCOL_TLSv1``
    :param ciphers: see ``ssl.wrap_socket``. May be ``None``. New in Python 2.7/3.2

    :returns: an RPyC connection exposing ``SlaveService``

    .. _wrap_socket: 
    """
    return factory.ssl_connect(host, port, keyfile = keyfile, certfile = certfile,
        ssl_version = ssl_version, ca_certs = ca_certs, service = SlaveService,
        ipv6 = ipv6)

def ssh_connect(remote_machine, remote_port):
    """Connects to the remote server over an SSH tunnel. See 
    :func:`rpyc.utils.factory.ssh_connect` for more info.
    
    :param remote_machine: the :class:`plumbum.remote.RemoteMachine` instance
    :param remote_port: the remote TCP port
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    return factory.ssh_connect(remote_machine, remote_port, SlaveService)

def connect_subproc(server_file = None):
    """Runs an RPyC classic server as a subprocess and returns an RPyC
    connection to it over stdio
    
    :param server_file: The full path to the server script (``rpyc_classic.py``). 
                        If not given, ``which rpyc_classic.py`` will be attempted.
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    if server_file is None:
        server_file = os.popen("which rpyc_classic.py").read().strip()
        if not server_file:
            raise ValueError("server_file not given and could not be inferred")
    return factory.connect_subproc([sys.executable, "-u", server_file, "-q", "-m", "stdio"],
        SlaveService)

def connect_thread():
    """
    Starts a SlaveService on a thread and connects to it. Useful for testing 
    purposes. See :func:`rpyc.utils.factory.connect_thread`
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    return factory.connect_thread(SlaveService, remote_service = SlaveService)

def connect_multiprocess(args = {}):
    """
    Starts a SlaveService on a multiprocess process and connects to it.
    Useful for testing purposes and running multicore code thats uses shared
    memory. See :func:`rpyc.utils.factory.connect_multiprocess`
    
    :returns: an RPyC connection exposing ``SlaveService``
    """
    return factory.connect_multiprocess(SlaveService, remote_service = SlaveService, args=args)


#===============================================================================
# remoting utilities
#===============================================================================

def upload(conn, localpath, remotepath, filter = None, ignore_invalid = False, chunk_size = 16000):
    """uploads a file or a directory to the given remote path
    
    :param localpath: the local file or directory
    :param remotepath: the remote path
    :param filter: a predicate that accepts the filename and determines whether
                   it should be uploaded; None means any file
    :param chunk_size: the IO chunk size
    """
    if os.path.isdir(localpath):
        upload_dir(conn, localpath, remotepath, filter, chunk_size)
    elif os.path.isfile(localpath):
        upload_file(conn, localpath, remotepath, chunk_size)
    else:
        if not ignore_invalid:
            raise ValueError("cannot upload %r" % (localpath,))

def upload_file(conn, localpath, remotepath, chunk_size = 16000):
    lf = open(localpath, "rb")
    rf = conn.builtin.open(remotepath, "wb")
    while True:
        buf = lf.read(chunk_size)
        if not buf:
            break
        rf.write(buf)
    lf.close()
    rf.close()

def upload_dir(conn, localpath, remotepath, filter = None, chunk_size = 16000):
    if not conn.modules.os.path.isdir(remotepath):
        conn.modules.os.makedirs(remotepath)
    for fn in os.listdir(localpath):
        if not filter or filter(fn):
            lfn = os.path.join(localpath, fn)
            rfn = conn.modules.os.path.join(remotepath, fn)
            upload(conn, lfn, rfn, filter = filter, ignore_invalid = True, chunk_size = chunk_size)

def download(conn, remotepath, localpath, filter = None, ignore_invalid = False, chunk_size = 16000):
    """
    download a file or a directory to the given remote path
    
    :param localpath: the local file or directory
    :param remotepath: the remote path
    :param filter: a predicate that accepts the filename and determines whether
                   it should be downloaded; None means any file
    :param chunk_size: the IO chunk size
    """
    if conn.modules.os.path.isdir(remotepath):
        download_dir(conn, remotepath, localpath, filter)
    elif conn.modules.os.path.isfile(remotepath):
        download_file(conn, remotepath, localpath, chunk_size)
    else:
        if not ignore_invalid:
            raise ValueError("cannot download %r" % (remotepath,))

def download_file(conn, remotepath, localpath, chunk_size = 16000):
    rf = conn.builtin.open(remotepath, "rb")
    lf = open(localpath, "wb")
    while True:
        buf = rf.read(chunk_size)
        if not buf:
            break
        lf.write(buf)
    lf.close()
    rf.close()

def download_dir(conn, remotepath, localpath, filter = None, chunk_size = 16000):
    if not os.path.isdir(localpath):
        os.makedirs(localpath)
    for fn in conn.modules.os.listdir(remotepath):
        if not filter or filter(fn):
            rfn = conn.modules.os.path.join(remotepath, fn)
            lfn = os.path.join(localpath, fn)
            download(conn, rfn, lfn, filter = filter, ignore_invalid = True)

def upload_package(conn, module, remotepath = None, chunk_size = 16000):
    """
    uploads a module or a package to the remote party
    
    :param conn: the RPyC connection to use
    :param module: the local module/package object to upload
    :param remotepath: the remote path (if ``None``, will default to the 
                       remote system's python library (as reported by 
                       ``distutils``)
    :param chunk_size: the IO chunk size
    
    .. note:: ``upload_module`` is just an alias to ``upload_package``
    
    example::
    
       import foo.bar
       ...
       rpyc.classic.upload_package(conn, foo.bar)
    
    """
    if remotepath is None:
        site = conn.modules["distutils.sysconfig"].get_python_lib()
        remotepath = conn.modules.os.path.join(site, module.__name__)
    localpath = os.path.dirname(os.path.abspath(inspect.getsourcefile(module)))
    upload(conn, localpath, remotepath, chunk_size = chunk_size)

upload_module = upload_package

def obtain(proxy):
    """obtains (copies) a remote object from a proxy object. the object is 
    ``pickled`` on the remote side and ``unpickled`` locally, thus moved 
    **by value**. changes made to the local object will not reflect remotely.
        
    :param proxy: an RPyC proxy object
    
    .. note:: the remote object to must be ``pickle``-able

    :returns: a copy of the remote object
    """
    return pickle.loads(pickle.dumps(proxy))

def deliver(conn, localobj):
    """delivers (recreates) a local object on the other party. the object is
    ``pickled`` locally and ``unpickled`` on the remote side, thus moved
    **by value**. changes made to the remote object will not reflect locally.
    
    :param conn: the RPyC connection
    :param localobj: the local object to deliver
    
    .. note:: the object must be ``picklable``
    
    :returns: a proxy to the remote object
    """
    return conn.modules["rpyc.lib.compat"].pickle.loads(pickle.dumps(localobj))

@contextmanager
def redirected_stdio(conn):
    r"""
    Redirects the other party's ``stdin``, ``stdout`` and ``stderr`` to 
    those of the local party, so remote IO will occur locally.

    Example usage::
    
        with redirected_stdio(conn):
            conn.modules.sys.stdout.write("hello\n")   # will be printed locally
    
    """
    orig_stdin = conn.modules.sys.stdin
    orig_stdout = conn.modules.sys.stdout
    orig_stderr = conn.modules.sys.stderr
    try:
        conn.modules.sys.stdin = sys.stdin
        conn.modules.sys.stdout = sys.stdout
        conn.modules.sys.stderr = sys.stderr
        yield
    finally:
        conn.modules.sys.stdin = orig_stdin
        conn.modules.sys.stdout = orig_stdout
        conn.modules.sys.stderr = orig_stderr

def pm(conn):
    """same as ``pdb.pm()`` but on a remote exception
    
    :param conn: the RPyC connection
    """
    #pdb.post_mortem(conn.root.getconn()._last_traceback)
    with redirected_stdio(conn):
        conn.modules.pdb.post_mortem(conn.root.getconn()._last_traceback)

def interact(conn, namespace = None):
    """remote interactive interpreter
    
    :param conn: the RPyC connection
    :param namespace: the namespace to use (a ``dict``)
    """
    if namespace is None:
        namespace = {}
    namespace["conn"] = conn
    with redirected_stdio(conn):
        conn.execute("""def _rinteract(ns):
            import code
            code.interact(local = dict(ns))""")
        conn.namespace["_rinteract"](namespace)

class MockClassicConnection(object):
    """Mock classic RPyC connection object. Useful when you want the same code to run remotely or locally.
    
    """
    def __init__(self):
        self._conn = None
        self.namespace = {}
        self.modules = ModuleNamespace(self.getmodule)
        if is_py3k:
            self.builtin = self.modules.builtins
        else:
            self.builtin = self.modules.__builtin__
        self.builtins = self.builtin

    def execute(self, text):
        execute(text, self.namespace)
    def eval(self, text):
        return eval(text, self.namespace)
    def getmodule(self, name):
        return __import__(name, None, None, "*")
    def getconn(self):
        return None

def teleport_function(conn, func):
    """
    "Teleports" a function (including nested functions/closures) over the RPyC connection.
    The function is passed in bytecode form and reconstructed on the other side.

    The function cannot have non-brinable defaults (e.g., ``def f(x, y=[8]):``,
    since a ``list`` isn't brinable), or make use of non-builtin globals (like modules).
    You can overcome the second restriction by moving the necessary imports into the
    function body, e.g. ::

        def f(x, y):
            import os
            return (os.getpid() + y) * x

    :param conn: the RPyC connection
    :param func: the function object to be delivered to the other party
    """
    from rpyc.utils.teleportation import export_function
    exported = export_function(func)
    return conn.modules["rpyc.utils.teleportation"].import_function(exported)





########NEW FILE########
__FILENAME__ = factory
"""
RPyC connection factories: ease the creation of a connection for the common 
cases)
"""
import socket

import threading
try:
    from thread import interrupt_main
except ImportError:
    try:
        from _thread import interrupt_main
    except ImportError:
        # assume jython (#83)
        from java.lang import System
        interrupt_main = System.exit

from rpyc import Connection, Channel, SocketStream, TunneledSocketStream, PipeStream, VoidService
from rpyc.utils.registry import UDPRegistryClient
from rpyc.lib import safe_import
ssl = safe_import("ssl")


class DiscoveryError(Exception):
    pass


#------------------------------------------------------------------------------
# API
#------------------------------------------------------------------------------
def connect_channel(channel, service = VoidService, config = {}):
    """creates a connection over a given channel
    
    :param channel: the channel to use
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict

    :returns: an RPyC connection
    """
    return Connection(service, channel, config = config)

def connect_stream(stream, service = VoidService, config = {}):
    """creates a connection over a given stream

    :param stream: the stream to use
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict
    
    :returns: an RPyC connection
    """
    return connect_channel(Channel(stream), service = service, config = config)

def connect_pipes(input, output, service = VoidService, config = {}):
    """
    creates a connection over the given input/output pipes
    
    :param input: the input pipe
    :param output: the output pipe
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict
    
    :returns: an RPyC connection
    """
    return connect_stream(PipeStream(input, output), service = service, config = config)

def connect_stdpipes(service = VoidService, config = {}):
    """
    creates a connection over the standard input/output pipes
    
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict
    
    :returns: an RPyC connection
    """
    return connect_stream(PipeStream.from_std(), service = service, config = config)

def connect(host, port, service = VoidService, config = {}, ipv6 = False, keepalive = False):
    """
    creates a socket-connection to the given host and port
    
    :param host: the hostname to connect to
    :param port: the TCP port to use
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict
    :param ipv6: whether to use IPv6 or not

    :returns: an RPyC connection
    """
    s = SocketStream.connect(host, port, ipv6 = ipv6, keepalive = keepalive)
    return connect_stream(s, service, config)

def ssl_connect(host, port, keyfile = None, certfile = None, ca_certs = None,
        cert_reqs = None, ssl_version = None, ciphers = None,
        service = VoidService, config = {}, ipv6 = False, keepalive = False):
    """
    creates an SSL-wrapped connection to the given host (encrypted and
    authenticated).
    
    :param host: the hostname to connect to
    :param port: the TCP port to use
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict
    :param ipv6: whether to create an IPv6 socket or an IPv4 one
    
    The following arguments are passed directly to 
    `ssl.wrap_socket <http://docs.python.org/dev/library/ssl.html#ssl.wrap_socket>`_:
    
    :param keyfile: see ``ssl.wrap_socket``. May be ``None``
    :param certfile: see ``ssl.wrap_socket``. May be ``None``
    :param ca_certs: see ``ssl.wrap_socket``. May be ``None``
    :param cert_reqs: see ``ssl.wrap_socket``. By default, if ``ca_cert`` is specified,
                      the requirement is set to ``CERT_REQUIRED``; otherwise it is 
                      set to ``CERT_NONE``
    :param ssl_version: see ``ssl.wrap_socket``. The default is ``PROTOCOL_TLSv1``
    :param ciphers: see ``ssl.wrap_socket``. May be ``None``. New in Python 2.7/3.2

    :returns: an RPyC connection
    """
    ssl_kwargs = {"server_side" : False}
    if keyfile is not None:
        ssl_kwargs["keyfile"] = keyfile
    if certfile is not None:
        ssl_kwargs["certfile"] = certfile
    if ca_certs is not None:
        ssl_kwargs["ca_certs"] = ca_certs
        ssl_kwargs["cert_reqs"] = ssl.CERT_REQUIRED
    if cert_reqs is not None:
        ssl_kwargs["cert_reqs"] = cert_reqs
    if ssl_version is None:
        ssl_kwargs["ssl_version"] = ssl.PROTOCOL_TLSv1
    else:
        ssl_kwargs["ssl_version"] = ssl_version
    if ciphers is not None:
        ssl_kwargs["ciphers"] = ciphers
    s = SocketStream.ssl_connect(host, port, ssl_kwargs, ipv6 = ipv6, keepalive = keepalive)
    return connect_stream(s, service, config)

def _get_free_port():
    """attempts to find a free port"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("localhost", 0))
    _, port = s.getsockname()
    s.close()
    return port

def ssh_connect(remote_machine, remote_port, service = VoidService, config = {}):
    """
    Connects to an RPyC server over an SSH tunnel (created by plumbum).
    See `Plumbum tunneling <http://plumbum.readthedocs.org/en/latest/remote.html#tunneling>`_ 
    for further details.
    
    :param remote_machine: an :class:`plumbum.remote.RemoteMachine` instance
    :param remote_port: the port of the remote server
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict

    :returns: an RPyC connection
    """
    loc_port = _get_free_port()
    tun = remote_machine.tunnel(loc_port, remote_port)
    stream = TunneledSocketStream.connect("localhost", loc_port)
    stream.tun = tun
    return Connection(service, Channel(stream), config = config)

def discover(service_name, host = None, registrar = None, timeout = 2):
    """
    discovers hosts running the given service
    
    :param service_name: the service to look for
    :param host: limit the discovery to the given host only (None means any host)
    :param registrar: use this registry client to discover services. if None,
                      use the default UDPRegistryClient with the default settings.
    :param timeout: the number of seconds to wait for a reply from the registry
                    if no hosts are found, raises DiscoveryError
    
    :raises: ``DiscoveryError`` if no server is found
    :returns: a list of (ip, port) pairs
    """
    if registrar is None:
        registrar = UDPRegistryClient(timeout = timeout)
    addrs = registrar.discover(service_name)
    if not addrs:
        raise DiscoveryError("no servers exposing %r were found" % (service_name,))
    if host:
        ips = socket.gethostbyname_ex(host)[2]
        addrs = [(h, p) for h, p in addrs if h in ips]
    if not addrs:
        raise DiscoveryError("no servers exposing %r were found on %r" % (service_name, host))
    return addrs

def connect_by_service(service_name, host = None, service = VoidService, config = {}):
    """create a connection to an arbitrary server that exposes the requested service
    
    :param service_name: the service to discover
    :param host: limit discovery to the given host only (None means any host)
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict

    :raises: ``DiscoveryError`` if no server is found
    :returns: an RPyC connection
    """
    host, port = discover(service_name, host = host)[0]
    return connect(host, port, service, config = config)

def connect_subproc(args, service = VoidService, config = {}):
    """runs an rpyc server on a child process that and connects to it over
    the stdio pipes. uses the subprocess module.
    
    :param args: the args to Popen, e.g., ["python", "-u", "myfile.py"]
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict
    """
    from subprocess import Popen, PIPE
    proc = Popen(args, stdin = PIPE, stdout = PIPE)
    conn = connect_pipes(proc.stdout, proc.stdin, service = service, config = config)
    conn.proc = proc # just so you can have control over the processs
    return conn

def connect_thread(service = VoidService, config = {}, remote_service = VoidService, remote_config = {}):
    """starts an rpyc server on a new thread, bound to an arbitrary port, 
    and connects to it over a socket.
    
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict
    :param server_service: the remote service to expose (of the server; defaults to Void)
    :param server_config: remote configuration dict (of the server)
    """
    listener = socket.socket()
    listener.bind(("localhost", 0))
    listener.listen(1)

    def server(listener = listener):
        client = listener.accept()[0]
        listener.close()
        conn = connect_stream(SocketStream(client), service = remote_service,
            config = remote_config)
        try:
            conn.serve_all()
        except KeyboardInterrupt:
            interrupt_main()

    t = threading.Thread(target = server)
    t.setDaemon(True)
    t.start()
    host, port = listener.getsockname()
    return connect(host, port, service = service, config = config)

def connect_multiprocess(service = VoidService, config = {}, remote_service = VoidService, remote_config = {}, args={}):
    """starts an rpyc server on a new process, bound to an arbitrary port, 
    and connects to it over a socket. Basically a copy of connect_thread().
    However if args is used and if these are shared memory then changes
    will be bi-directional. That is we now have access to shared memmory.
    
    :param service: the local service to expose (defaults to Void)
    :param config: configuration dict
    :param server_service: the remote service to expose (of the server; defaults to Void)
    :param server_config: remote configuration dict (of the server)
    :param args: dict of local vars to pass to new connection, form {'name':var}
    
    Contributed by *@tvanzyl*
    """
    from multiprocessing import Process
    
    listener = socket.socket()
    listener.bind(("localhost", 0))
    listener.listen(1)
    
    def server(listener=listener, args=args):
        client = listener.accept()[0]
        listener.close()
        conn = connect_stream(SocketStream(client), service = remote_service, config = remote_config)        
        try:
            for k in args:
                conn._local_root.exposed_namespace[k] = args[k]
            conn.serve_all()
        except KeyboardInterrupt:
            interrupt_main()
    
    t = Process(target = server)
    t.start()
    host, port = listener.getsockname()
    return connect(host, port, service = service, config = config)



########NEW FILE########
__FILENAME__ = helpers
"""
Helpers and wrappers for common RPyC tasks
"""
import time
import threading
from rpyc.lib.colls import WeakValueDict
from rpyc.lib.compat import callable
from rpyc.core.consts import HANDLE_BUFFITER, HANDLE_CALL
from rpyc.core.netref import syncreq, asyncreq


def buffiter(obj, chunk = 10, max_chunk = 1000, factor = 2):
    """Buffered iterator - reads the remote iterator in chunks starting with
    *chunk*, multiplying the chunk size by *factor* every time, as an 
    exponential-backoff, up to a chunk of *max_chunk* size.
    
    ``buffiter`` is very useful for tight loops, where you fetch an element 
    from the other side with every iterator. Instead of being limited by the 
    network's latency after every iteration, ``buffiter`` fetches a "chunk" 
    of elements every time, reducing the amount of network I/Os.
    
    :param obj: An iterable object (supports ``iter()``)
    :param chunk: the initial chunk size
    :param max_chunk: the maximal chunk size
    :param factor: the factor by which to multiply the chunk size after every 
                   iterator (up to *max_chunk*). Must be >= 1.
    
    :returns: an iterator
    
    Example::
        
        cursor = db.get_cursor()
        for id, name, dob in buffiter(cursor.select("Id", "Name", "DoB")):
            print id, name, dob
    """
    if factor < 1:
        raise ValueError("factor must be >= 1, got %r" % (factor,))
    it = iter(obj)
    count = chunk
    while True:
        items = syncreq(it, HANDLE_BUFFITER, count)
        count = min(count * factor, max_chunk)
        if not items:
            break
        for elem in items:
            yield elem

def restricted(obj, attrs, wattrs = None):
    """Returns a 'restricted' version of an object, i.e., allowing access only to a subset of its
    attributes. This is useful when returning a "broad" or "dangerous" object, where you don't 
    want the other party to have access to all of its attributes.
    
    .. versionadded:: 3.2
    
    :param obj: any object
    :param attrs: the set of attributes exposed for reading (``getattr``) or writing (``setattr``).
                  The same set will serve both for reading and writing, unless wattrs is explicitly
                  given.
    :param wattrs: the set of attributes exposed for writing (``setattr``). If ``None``, 
                   ``wattrs`` will default to ``attrs``. To disable setting attributes completely,
                   set to an empty tuple ``()``.
    :returns: a restricted view of the object
    
    Example::
    
        class MyService(rpyc.Service):
            def exposed_open(self, filename):
                f = open(filename, "r")
                return rpyc.restricted(f, {"read", "close"})   # disallow access to `seek` or `write`
    
    """
    if wattrs is None:
        wattrs = attrs
    class Restricted(object):
        def _rpyc_getattr(self, name):
            if name not in attrs:
                raise AttributeError(name)
            return getattr(obj, name)
        __getattr__ = _rpyc_getattr
        def _rpyc_setattr(self, name, value):
            if name not in wattrs:
                raise AttributeError(name)
            setattr(obj, name, value)
        __setattr__ = _rpyc_setattr
    return Restricted()

class _Async(object):
    """Creates an async proxy wrapper over an existing proxy. Async proxies
    are cached. Invoking an async proxy will return an AsyncResult instead of
    blocking"""

    __slots__ = ("proxy", "__weakref__")
    def __init__(self, proxy):
        self.proxy = proxy
    def __call__(self, *args, **kwargs):
        return asyncreq(self.proxy, HANDLE_CALL, args, tuple(kwargs.items()))
    def __repr__(self):
        return "async(%r)" % (self.proxy,)

_async_proxies_cache = WeakValueDict()
def async(proxy):
    """
    Returns an asynchronous "version" of the given proxy. Invoking the returned
    proxy will not block; instead it will return an 
    :class:`rpyc.core.async.AsyncResult` object that you can test for completion
    
    :param proxy: any **callable** RPyC proxy
    
    :returns: the proxy, wrapped by an asynchronous wrapper
    
    Example::
    
        async_sleep = rpyc.async(conn.modules.time.sleep)
        res = async_sleep(5)
    
    .. _async_note:
    
    .. note:: 
       In order to avoid overloading the GC, the returned asynchronous wrapper is 
       cached as a weak reference. Therefore, do not use::
           
           rpyc.async(foo)(5)
       
       Always store the returned asynchronous wrapper in a variable, e.g. ::
       
           a_foo = rpyc.async(foo)
           a_foo(5)
    """
    pid = id(proxy)
    if pid in _async_proxies_cache:
        return _async_proxies_cache[pid]
    if not hasattr(proxy, "____conn__") or not hasattr(proxy, "____oid__"):
        raise TypeError("'proxy' must be a Netref: %r", (proxy,))
    if not callable(proxy):
        raise TypeError("'proxy' must be callable: %r" % (proxy,))
    caller = _Async(proxy)
    _async_proxies_cache[id(caller)] = _async_proxies_cache[pid] = caller
    return caller

async.__doc__ = _Async.__doc__

class timed(object):
    """Creates a timed asynchronous proxy. Invoking the timed proxy will
    run in the background and will raise an :class:`rpyc.core.async.AsyncResultTimeout` 
    exception if the computation does not terminate within the given time frame
    
    :param proxy: any **callable** RPyC proxy
    :param timeout: the maximal number of seconds to allow the operation to run
    
    :returns: a ``timed`` wrapped proxy
    
    Example::
    
        t_sleep = rpyc.timed(conn.modules.time.sleep, 6) # allow up to 6 seconds
        t_sleep(4) # okay
        t_sleep(8) # will time out and raise AsyncResultTimeout
    """

    __slots__ = ("__weakref__", "proxy", "timeout")
    def __init__(self, proxy, timeout):
        self.proxy = async(proxy)
        self.timeout = timeout
    def __call__(self, *args, **kwargs):
        res = self.proxy(*args, **kwargs)
        res.set_expiry(self.timeout)
        return res
    def __repr__(self):
        return "timed(%r, %r)" % (self.proxy.proxy, self.timeout)

class BgServingThread(object):
    """Runs an RPyC server in the background to serve all requests and replies
    that arrive on the given RPyC connection. The thread is started upon the
    the instantiation of the ``BgServingThread`` object; you can use the 
    :meth:`stop` method to stop the server thread
    
    Example::
    
        conn = rpyc.connect(...)
        bg_server = BgServingThread(conn)
        ...
        bg_server.stop()
        
    .. note:: 
       For a more detailed explanation of asynchronous operation and the role of the 
       ``BgServingThread``, see :ref:`tut5`
    
    """
    # these numbers are magical...
    SERVE_INTERVAL = 0.0
    SLEEP_INTERVAL = 0.1

    def __init__(self, conn):
        self._conn = conn
        self._thread = threading.Thread(target = self._bg_server)
        self._thread.setDaemon(True)
        self._active = True
        self._thread.start()
    def __del__(self):
        if self._active:
            self.stop()
    def _bg_server(self):
        try:
            while self._active:
                self._conn.serve(self.SERVE_INTERVAL)
                time.sleep(self.SLEEP_INTERVAL) # to reduce contention
        except Exception:
            if self._active:
                raise
    def stop(self):
        """stop the server thread. once stopped, it cannot be resumed. you will
        have to create a new BgServingThread object later."""
        assert self._active
        self._active = False
        self._thread.join()
        self._conn = None


########NEW FILE########
__FILENAME__ = registry
"""
RPyC **registry server** implementation. The registry is much like 
`Avahi <http://en.wikipedia.org/wiki/Avahi_(software)>`_ or 
`Bonjour <http://en.wikipedia.org/wiki/Bonjour_(software)>`_, but tailored to
the needs of RPyC. Also, neither of them supports (or supported) Windows,
and Bonjour has a restrictive license. Moreover, they are too "powerful" for 
what RPyC needed and required too complex a setup.

If anyone wants to implement the RPyC registry using Avahi, Bonjour, or any 
other zeroconf implementation -- I'll be happy to include them. 

Refer to :file:`rpyc/scripts/rpyc_registry.py` for more info.
"""
import sys
import socket
import time
import logging
from rpyc.core import brine


DEFAULT_PRUNING_TIMEOUT = 4 * 60
MAX_DGRAM_SIZE          = 1500
REGISTRY_PORT           = 18811


#------------------------------------------------------------------------------
# servers
#------------------------------------------------------------------------------

class RegistryServer(object):
    """Base registry server"""
    
    def __init__(self, listenersock, pruning_timeout = None, logger = None):
        self.sock = listenersock
        self.port = self.sock.getsockname()[1]
        self.active = False
        self.services = {}
        if pruning_timeout is None:
            pruning_timeout = DEFAULT_PRUNING_TIMEOUT
        self.pruning_timeout = pruning_timeout
        if logger is None:
            logger = self._get_logger()
        self.logger = logger

    def _get_logger(self):
        raise NotImplementedError()

    def on_service_added(self, name, addrinfo):
        """called when a new service joins the registry (but not on keepalives).
        override this to add custom logic"""

    def on_service_removed(self, name, addrinfo):
        """called when a service unregisters or is pruned.
        override this to add custom logic"""

    def _add_service(self, name, addrinfo):
        """updates the service's keep-alive time stamp"""
        if name not in self.services:
            self.services[name] = {}
        is_new = addrinfo not in self.services[name]
        self.services[name][addrinfo] = time.time()
        if is_new:
            try:
                self.on_service_added(name, addrinfo)
            except Exception:
                self.logger.exception('error executing service add callback')

    def _remove_service(self, name, addrinfo):
        """removes a single server of the given service"""
        self.services[name].pop(addrinfo, None)
        if not self.services[name]:
            del self.services[name]
        try:
            self.on_service_removed(name, addrinfo)
        except Exception:
            self.logger.exception('error executing service remove callback')

    def cmd_query(self, host, name):
        """implementation of the ``query`` command"""
        name = name.upper()
        self.logger.debug("querying for %r", name)
        if name not in self.services:
            self.logger.debug("no such service")
            return ()

        oldest = time.time() - self.pruning_timeout
        all_servers = sorted(self.services[name].items(), key = lambda x: x[1])
        servers = []
        for addrinfo, t in all_servers:
            if t < oldest:
                self.logger.debug("discarding stale %s:%s", *addrinfo)
                self._remove_service(name, addrinfo)
            else:
                servers.append(addrinfo)

        self.logger.debug("replying with %r", servers)
        return tuple(servers)

    def cmd_register(self, host, names, port):
        """implementation of the ``register`` command"""
        self.logger.debug("registering %s:%s as %s", host, port, ", ".join(names))
        for name in names:
            self._add_service(name.upper(), (host, port))
        return "OK"

    def cmd_unregister(self, host, port):
        """implementation of the ``unregister`` command"""
        self.logger.debug("unregistering %s:%s", host, port)
        for name in self.services.keys():
            self._remove_service(name, (host, port))
        return "OK"

    def _recv(self):
        raise NotImplementedError()

    def _send(self, data, addrinfo):
        raise NotImplementedError()

    def _work(self):
        while self.active:
            try:
                data, addrinfo = self._recv()
            except (socket.error, socket.timeout):
                continue
            try:
                magic, cmd, args = brine.load(data)
            except Exception:
                continue
            if magic != "RPYC":
                self.logger.warn("invalid magic: %r", magic)
                continue
            cmdfunc = getattr(self, "cmd_%s" % (cmd.lower(),), None)
            if not cmdfunc:
                self.logger.warn("unknown command: %r", cmd)
                continue

            try:
                reply = cmdfunc(addrinfo[0], *args)
            except Exception:
                self.logger.exception('error executing function')
            else:
                self._send(brine.dump(reply), addrinfo)

    def start(self):
        """Starts the registry server (blocks)"""
        if self.active:
            raise ValueError("server is already running")
        if self.sock is None:
            raise ValueError("object disposed")
        self.logger.debug("server started on %s:%s", *self.sock.getsockname()[:2])
        try:
            self.active = True
            self._work()
        except KeyboardInterrupt:
            self.logger.warn("User interrupt!")
        finally:
            self.active = False
            self.logger.debug("server closed")
            self.sock.close()
            self.sock = None

    def close(self):
        """Closes (terminates) the registry server"""
        if not self.active:
            raise ValueError("server is not running")
        self.logger.debug("stopping server...")
        self.active = False

class UDPRegistryServer(RegistryServer):
    """UDP-based registry server. The server listens to UDP broadcasts and
    answers them. Useful in local networks, were broadcasts are allowed"""
    
    TIMEOUT = 1.0
    
    def __init__(self, host = "0.0.0.0", port = REGISTRY_PORT, pruning_timeout = None, logger = None):
        family, socktype, proto, _, sockaddr = socket.getaddrinfo(host, port, 0, 
            socket.SOCK_DGRAM)[0]
        sock = socket.socket(family, socktype, proto)
        sock.bind(sockaddr)
        sock.settimeout(self.TIMEOUT)
        RegistryServer.__init__(self, sock, pruning_timeout = pruning_timeout,
            logger = logger)

    def _get_logger(self):
        return logging.getLogger("REGSRV/UDP/%d" % (self.port,))

    def _recv(self):
        return self.sock.recvfrom(MAX_DGRAM_SIZE)

    def _send(self, data, addrinfo):
        try:
            self.sock.sendto(data, addrinfo)
        except (socket.error, socket.timeout):
            pass

class TCPRegistryServer(RegistryServer):
    """TCP-based registry server. The server listens to a certain TCP port and
    answers requests. Useful when you need to cross routers in the network, since
    they block UDP broadcasts"""

    TIMEOUT = 3.0
    
    def __init__(self, host = "0.0.0.0", port = REGISTRY_PORT, pruning_timeout = None, 
            logger = None, reuse_addr = True):

        family, socktype, proto, _, sockaddr = socket.getaddrinfo(host, port, 0, 
            socket.SOCK_STREAM)[0]
        sock = socket.socket(family, socktype, proto)
        if reuse_addr and sys.platform != "win32":
            # warning: reuseaddr is not what you expect on windows!
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(sockaddr)
        sock.listen(10)
        sock.settimeout(self.TIMEOUT)
        RegistryServer.__init__(self, sock, pruning_timeout = pruning_timeout,
            logger = logger)
        self._connected_sockets = {}

    def _get_logger(self):
        return logging.getLogger("REGSRV/TCP/%d" % (self.port,))

    def _recv(self):
        sock2, _ = self.sock.accept()
        addrinfo = sock2.getpeername()
        data = sock2.recv(MAX_DGRAM_SIZE)
        self._connected_sockets[addrinfo] = sock2
        return data, addrinfo

    def _send(self, data, addrinfo):
        sock2 = self._connected_sockets.pop(addrinfo)
        try:
            sock2.send(data)
        except (socket.error, socket.timeout):
            pass
        finally:
            sock2.close()

#------------------------------------------------------------------------------
# clients (registrars)
#------------------------------------------------------------------------------
class RegistryClient(object):
    """Base registry client. Also known as **registrar**"""
    
    REREGISTER_INTERVAL = 60

    def __init__(self, ip, port, timeout, logger = None):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        if logger is None:
            logger = self._get_logger()
        self.logger = logger

    def _get_logger(self):
        raise NotImplementedError()

    def discover(self, name):
        """Sends a query for the specified service name.
        
        :param name: the service name (or one of its aliases)
        
        :returns: a list of ``(host, port)`` tuples
        """
        raise NotImplementedError()

    def register(self, aliases, port):
        """Registers the given service aliases with the given TCP port. This 
        API is intended to be called only by an RPyC server.
        
        :param aliases: the :class:`service's <rpyc.core.service.Service>` aliases
        :param port: the listening TCP port of the server
        """
        raise NotImplementedError()

    def unregister(self, port):
        """Unregisters the given RPyC server. This API is intended to be called
        only by an RPyC server.
        
        :param port: the listening TCP port of the RPyC server to unregister
        """
        raise NotImplementedError()

class UDPRegistryClient(RegistryClient):
    """UDP-based registry clients. By default, it sends UDP broadcasts (requires 
    special user privileges on certain OS's) and collects the replies. You can 
    also specify the IP address to send to.
    
    Example::
    
        registrar = UDPRegistryClient()
        list_of_servers = registrar.discover("foo")

    .. note::
       Consider using :func:`rpyc.utils.factory.discover` instead
    """
    
    def __init__(self, ip = "255.255.255.255", port = REGISTRY_PORT, timeout = 2,
            bcast = None, logger = None, ipv6 = False):
        RegistryClient.__init__(self, ip = ip, port = port, timeout = timeout,
            logger = logger)
        
        if ipv6:
            self.sock_family = socket.AF_INET6
            self.bcast = False
        else:
            self.sock_family = socket.AF_INET
            if bcast is None:
                bcast = "255" in ip.split(".")
            self.bcast = bcast

    def _get_logger(self):
        return logging.getLogger('REGCLNT/UDP')

    def discover(self, name):
        sock = socket.socket(self.sock_family, socket.SOCK_DGRAM)

        try:
            if self.bcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
            data = brine.dump(("RPYC", "QUERY", (name,)))
            sock.sendto(data, (self.ip, self.port))
            sock.settimeout(self.timeout)

            try:
                data, _ = sock.recvfrom(MAX_DGRAM_SIZE)
            except (socket.error, socket.timeout):
                servers = ()
            else:
                servers = brine.load(data)
        finally:
            sock.close()
        return servers

    def register(self, aliases, port, interface = ""):
        self.logger.info("registering on %s:%s", self.ip, self.port)
        sock = socket.socket(self.sock_family, socket.SOCK_DGRAM)
        sock.bind((interface, 0))
        try:
            if self.bcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
            data = brine.dump(("RPYC", "REGISTER", (aliases, port)))
            sock.sendto(data, (self.ip, self.port))
    
            tmax = time.time() + self.timeout
            while time.time() < tmax:
                sock.settimeout(tmax - time.time())
                try:
                    data, address = sock.recvfrom(MAX_DGRAM_SIZE)
                    rip, rport = address[:2]
                except socket.timeout:
                    self.logger.warn("no registry acknowledged")
                    return False
                if rport != self.port:
                    continue
                try:
                    reply = brine.load(data)
                except Exception:
                    continue
                if reply == "OK":
                    self.logger.info("registry %s:%s acknowledged", rip, rport)
                    return True
            else:
                self.logger.warn("no registry acknowledged")
                return False
        finally:
            sock.close()

    def unregister(self, port):
        self.logger.info("unregistering from %s:%s", self.ip, self.port)
        sock = socket.socket(self.sock_family, socket.SOCK_DGRAM)
        try:
            if self.bcast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
            data = brine.dump(("RPYC", "UNREGISTER", (port,)))
            sock.sendto(data, (self.ip, self.port))
        finally:
            sock.close()


class TCPRegistryClient(RegistryClient):
    """TCP-based registry client. You must specify the host (registry server)
    to connect to.  
    
    Example::
    
        registrar = TCPRegistryClient("localhost")
        list_of_servers = registrar.discover("foo")
    
    .. note::
       Consider using :func:`rpyc.utils.factory.discover` instead
    """
    
    def __init__(self, ip, port = REGISTRY_PORT, timeout = 2, logger = None):
        RegistryClient.__init__(self, ip = ip, port = port, timeout = timeout,
            logger = logger)

    def _get_logger(self):
        return logging.getLogger('REGCLNT/TCP')

    def discover(self, name):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            data = brine.dump(("RPYC", "QUERY", (name,)))
            sock.connect((self.ip, self.port))
            sock.send(data)
            
            try:
                data = sock.recv(MAX_DGRAM_SIZE)
            except (socket.error, socket.timeout):
                servers = ()
            else:
                servers = brine.load(data)
        finally:
            sock.close()
        return servers

    def register(self, aliases, port, interface = ""):
        self.logger.info("registering on %s:%s", self.ip, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((interface, 0))
        sock.settimeout(self.timeout)
        data = brine.dump(("RPYC", "REGISTER", (aliases, port)))

        try:
            try:
                sock.connect((self.ip, self.port))
                sock.send(data)
            except (socket.error, socket.timeout):
                self.logger.warn("could not connect to registry")
                return False
            try:
                data = sock.recv(MAX_DGRAM_SIZE)
            except socket.timeout:
                self.logger.warn("registry did not acknowledge")
                return False
            try:
                reply = brine.load(data)
            except Exception:
                self.logger.warn("received corrupted data from registry")
                return False
            if reply == "OK":
                self.logger.info("registry %s:%s acknowledged", self.ip, self.port)

            return True
        finally:
            sock.close()

    def unregister(self, port):
        self.logger.info("unregistering from %s:%s", self.ip, self.port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            data = brine.dump(("RPYC", "UNREGISTER", (port,)))
            try:
                sock.connect((self.ip, self.port))
                sock.send(data)
            except (socket.error, socket.timeout):
                self.logger.warn("could not connect to registry")
        finally:
            sock.close()


########NEW FILE########
__FILENAME__ = server
"""
rpyc plug-in server (threaded or forking)
"""
import sys
import os
import socket
import time
import threading
import errno
import logging
try:
    import Queue
except ImportError:
    import queue as Queue
from rpyc.core import SocketStream, Channel, Connection
from rpyc.utils.registry import UDPRegistryClient
from rpyc.utils.authenticators import AuthenticationError
from rpyc.lib import safe_import
from rpyc.lib.compat import poll, get_exc_errno
signal = safe_import("signal")



class Server(object):
    """Base server implementation
    
    :param service: the :class:`service <service.Service>` to expose
    :param hostname: the host to bind to. Default is IPADDR_ANY, but you may 
                     want to restrict it only to ``localhost`` in some setups
    :param ipv6: whether to create an IPv6 or IPv4 socket. The default is IPv4
    :param port: the TCP port to bind to
    :param backlog: the socket's backlog (passed to ``listen()``)
    :param reuse_addr: whether or not to create the socket with the ``SO_REUSEADDR`` option set. 
    :param authenticator: the :ref:`api-authenticators` to use. If ``None``, no authentication 
                          is performed.
    :param registrar: the :class:`registrar <rpyc.utils.registry.RegistryClient>` to use. 
                          If ``None``, a default :class:`rpyc.utils.registry.UDPRegistryClient`
                          will be used
    :param auto_register: whether or not to register using the *registrar*. By default, the 
                          server will attempt to register only if a registrar was explicitly given. 
    :param protocol_config: the :data:`configuration dictionary <rpyc.core.protocol.DEFAULT_CONFIG>` 
                            that is passed to the RPyC connection
    :param logger: the ``logger`` to use (of the built-in ``logging`` module). If ``None``, a 
                   default logger will be created.
    :param listener_timeout: the timeout of the listener socket; set to ``None`` to disable (e.g.
                             on embedded platforms with limited battery)
    """
    
    def __init__(self, service, hostname = "", ipv6 = False, port = 0, 
            backlog = 10, reuse_addr = True, authenticator = None, registrar = None,
            auto_register = None, protocol_config = {}, logger = None, listener_timeout = 0.5):
        self.active = False
        self._closed = False
        self.service = service
        self.authenticator = authenticator
        self.backlog = backlog
        if auto_register is None:
            self.auto_register = bool(registrar)
        else:
            self.auto_register = auto_register
        self.protocol_config = protocol_config
        self.clients = set()

        if ipv6:
            if hostname == "localhost" and sys.platform != "win32":
                # on windows, you should bind to localhost even for ipv6
                hostname = "localhost6"
            self.listener = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        else:
            self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        if reuse_addr and sys.platform != "win32":
            # warning: reuseaddr is not what you'd expect on windows!
            # it allows you to bind an already bound port, resulting in "unexpected behavior"
            # (quoting MSDN)
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.listener.bind((hostname, port))
        self.listener.settimeout(listener_timeout)

        # hack for IPv6 (the tuple can be longer than 2)
        sockname = self.listener.getsockname()
        self.host, self.port = sockname[0], sockname[1]

        if logger is None:
            logger = logging.getLogger("%s/%d" % (self.service.get_service_name(), self.port))
        self.logger = logger
        if "logger" not in self.protocol_config:
            self.protocol_config["logger"] = self.logger
        if registrar is None:
            registrar = UDPRegistryClient(logger = self.logger)
        self.registrar = registrar

    def close(self):
        """Closes (terminates) the server and all of its clients. If applicable, 
        also unregisters from the registry server"""
        if self._closed:
            return
        self._closed = True
        self.active = False
        if self.auto_register:
            try:
                self.registrar.unregister(self.port)
            except Exception:
                self.logger.exception("error unregistering services")
        try:
            self.listener.shutdown(socket.SHUT_RDWR)
        except (EnvironmentError, socket.error):
            pass
        self.listener.close()
        self.logger.info("listener closed")
        for c in set(self.clients):
            try:
                c.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            c.close()
        self.clients.clear()

    def fileno(self):
        """returns the listener socket's file descriptor"""
        return self.listener.fileno()

    def accept(self):
        """accepts an incoming socket connection (blocking)"""
        while self.active:
            try:
                sock, addrinfo = self.listener.accept()
            except socket.timeout:
                pass
            except socket.error:
                ex = sys.exc_info()[1]
                if get_exc_errno(ex) == errno.EINTR:
                    pass
                else:
                    raise EOFError()
            else:
                break

        if not self.active:
            return

        sock.setblocking(True)
        self.logger.info("accepted %s:%s", addrinfo[0], addrinfo[1])
        self.clients.add(sock)
        self._accept_method(sock)

    def _accept_method(self, sock):
        """this method should start a thread, fork a child process, or
        anything else in order to serve the client. once the mechanism has
        been created, it should invoke _authenticate_and_serve_client with
        `sock` as the argument"""
        raise NotImplementedError

    def _authenticate_and_serve_client(self, sock):
        try:
            if self.authenticator:
                addrinfo = sock.getpeername()
                h = addrinfo[0]
                p = addrinfo[1]
                try:
                    sock2, credentials = self.authenticator(sock)
                except AuthenticationError:
                    self.logger.info("[%s]:%s failed to authenticate, rejecting connection", h, p)
                    return
                else:
                    self.logger.info("[%s]:%s authenticated successfully", h, p)
            else:
                credentials = None
                sock2 = sock
            try:
                self._serve_client(sock2, credentials)
            except Exception:
                self.logger.exception("client connection terminated abruptly")
                raise
        finally:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            sock.close()
            self.clients.discard(sock)

    def _serve_client(self, sock, credentials):
        addrinfo = sock.getpeername()
        h = addrinfo[0]
        p = addrinfo[1]
        if credentials:
            self.logger.info("welcome [%s]:%s (%r)", h, p, credentials)
        else:
            self.logger.info("welcome [%s]:%s", h, p)
        try:
            config = dict(self.protocol_config, credentials = credentials, 
                endpoints = (sock.getsockname(), addrinfo), logger = self.logger)
            conn = Connection(self.service, Channel(SocketStream(sock)),
                config = config, _lazy = True)
            conn._init_service()
            conn.serve_all()
        finally:
            self.logger.info("goodbye [%s]:%s", h, p)

    def _bg_register(self):
        interval = self.registrar.REREGISTER_INTERVAL
        self.logger.info("started background auto-register thread "
            "(interval = %s)", interval)
        tnext = 0
        try:
            while self.active:
                t = time.time()
                if t >= tnext:
                    did_register = False
                    aliases = self.service.get_service_aliases()
                    try:
                        did_register = self.registrar.register(aliases, self.port, interface = self.host)
                    except Exception:
                        self.logger.exception("error registering services")

                    # If registration worked out, retry to register again after
                    # interval time. Otherwise, try to register soon again.
                    if did_register:
                        tnext = t + interval
                    else:
                        self.logger.info("registering services did not work - retry")

                time.sleep(1)
        finally:
            if not self._closed:
                self.logger.info("background auto-register thread finished")

    def start(self):
        """Starts the server (blocking). Use :meth:`close` to stop"""
        self.listener.listen(self.backlog)
        self.logger.info("server started on [%s]:%s", self.host, self.port)
        self.active = True
        if self.auto_register:
            t = threading.Thread(target = self._bg_register)
            t.setDaemon(True)
            t.start()
        try:
            while self.active:
                self.accept()
        except EOFError:
            pass # server closed by another thread
        except KeyboardInterrupt:
            print("")
            self.logger.warn("keyboard interrupt!")
        finally:
            self.logger.info("server has terminated")
            self.close()


class OneShotServer(Server):
    """
    A server that handles a single connection (blockingly), and terminates after that
    
    Parameters: see :class:`Server`
    """
    def _accept_method(self, sock):
        try:
            self._authenticate_and_serve_client(sock)
        finally:
            self.close()

class ThreadedServer(Server):
    """
    A server that spawns a thread for each connection. Works on any platform
    that supports threads.
    
    Parameters: see :class:`Server`
    """
    def _accept_method(self, sock):
        t = threading.Thread(target = self._authenticate_and_serve_client, args = (sock,))
        t.setDaemon(True)
        t.start()


class ThreadPoolServer(Server):
    """This server is threaded like the ThreadedServer but reuses threads so that
    recreation is not necessary for each request. The pool of threads has a fixed
    size that can be set with the 'nbThreads' argument. The default size is 20.
    The server dispatches request to threads by batch, that is a given thread may process
    up to request_batch_size requests from the same connection in one go, before it goes to
    the next connection with pending requests. By default, self.request_batch_size
    is set to 10 and it can be overwritten in the constructor arguments.
    
    Contributed by *@sponce*

    Parameters: see :class:`Server`
    """

    def __init__(self, *args, **kwargs):
        '''Initializes a ThreadPoolServer. In particular, instantiate the thread pool.'''
        # get the number of threads in the pool
        nbthreads = 20
        if 'nbThreads' in kwargs:
            nbthreads = kwargs['nbThreads']
            del kwargs['nbThreads']
        # get the request batch size
        self.request_batch_size = 10
        if 'requestBatchSize' in kwargs:
            self.request_batch_size = kwargs['requestBatchSize']
            del kwargs['requestBatchSize']
        # init the parent
        Server.__init__(self, *args, **kwargs)
        # a queue of connections having somethign to process
        self._active_connection_queue = Queue.Queue()
        # declare the pool as already active
        self.active = True
        # setup the thread pool for handling requests
        self.workers = []
        for _ in range(nbthreads):
            t = threading.Thread(target = self._serve_clients)
            t.setName('ThreadPoolWorker')
            t.daemon = True
            t.start()
            self.workers.append(t)
        # a polling object to be used be the polling thread
        self.poll_object = poll()
        # a dictionary fd -> connection
        self.fd_to_conn = {}
        # setup a thread for polling inactive connections
        self.polling_thread = threading.Thread(target = self._poll_inactive_clients)
        self.polling_thread.setName('PollingThread')
        self.polling_thread.setDaemon(True)
        self.polling_thread.start()

    def close(self):
        '''closes a ThreadPoolServer. In particular, joins the thread pool.'''
        # close parent server
        Server.close(self)
        # stop producer thread
        self.polling_thread.join()
        # cleanup thread pool : first fill the pool with None fds so that all threads exit
        # the blocking get on the queue of active connections. Then join the threads
        for _ in range(len(self.workers)):
            self._active_connection_queue.put(None)
        for w in self.workers:
            w.join()

    def _remove_from_inactive_connection(self, fd):
        '''removes a connection from the set of inactive ones'''
        # unregister the connection in the polling object
        try:
            self.poll_object.unregister(fd)
        except KeyError:
            # the connection has already been unregistered
            pass

    def _drop_connection(self, fd):
        '''removes a connection by closing it and removing it from internal structs'''
        # cleanup fd_to_conn dictionnary
        try:
            conn = self.fd_to_conn[fd]
            del self.fd_to_conn[fd]
        except KeyError:
            # the active connection has already been removed
            pass
        # close connection
        conn.close()

    def _add_inactive_connection(self, fd):
        '''adds a connection to the set of inactive ones'''
        self.poll_object.register(fd, "reh")

    def _handle_poll_result(self, connlist):
        '''adds a connection to the set of inactive ones'''
        for fd, evt in connlist:
            try:
                # remove connection from the inactive ones
                self._remove_from_inactive_connection(fd)
                # Is it an error ?
                if "e" in evt or "n" in evt or "h" in evt:
                    # it was an error, connection was closed. Do the same on our side
                    self._drop_connection(fd)
                else:
                    # connection has data, let's add it to the active queue
                    self._active_connection_queue.put(fd)
            except KeyError:
                # the connection has already been dropped. Give up
                pass

    def _poll_inactive_clients(self):
        '''Main method run by the polling thread of the thread pool.
        Check whether inactive clients have become active'''
        while self.active:
            try:
                # the actual poll, with a timeout of 1s so that we can exit in case
                # we re not active anymore
                active_clients = self.poll_object.poll(1)
                # for each client that became active, put them in the active queue
                self._handle_poll_result(active_clients)
            except Exception:
                ex = sys.exc_info()[1]
                # "Caught exception in Worker thread" message
                self.logger.warning("failed to poll clients, caught exception : %s", str(ex))
                # wait a bit so that we do not loop too fast in case of error
                time.sleep(0.2)

    def _serve_requests(self, fd):
        '''Serves requests from the given connection and puts it back to the appropriate queue'''
        # serve a maximum of RequestBatchSize requests for this connection
        for _ in range(self.request_batch_size):
            try:
                if not self.fd_to_conn[fd].poll(): # note that poll serves the request
                    # we could not find a request, so we put this connection back to the inactive set
                    self._add_inactive_connection(fd)
                    return
            except EOFError:
                # the connection has been closed by the remote end. Close it on our side and return
                self._drop_connection(fd)
                return
            except Exception:
                # put back the connection to active queue in doubt and raise the exception to the upper level
                self._active_connection_queue.put(fd)
                raise
        # we've processed the maximum number of requests. Put back the connection in the active queue
        self._active_connection_queue.put(fd)

    def _serve_clients(self):
        '''Main method run by the processing threads of the thread pool.
        Loops forever, handling requests read from the connections present in the active_queue'''
        while self.active:
            try:
                # note that we do not use a timeout here. This is because the implementation of
                # the timeout version performs badly. So we block forever, and exit by filling
                # the queue with None fds
                fd = self._active_connection_queue.get(True)
                # fd may be None (case where we want to exit the blocking get to close the service)
                if fd:
                    # serve the requests of this connection
                    self._serve_requests(fd)
            except Queue.Empty:
                # we've timed out, let's just retry. We only use the timeout so that this
                # thread can stop even if there is nothing in the queue
                pass
            except Exception:
                ex = sys.exc_info()[1]
                # "Caught exception in Worker thread" message
                self.logger.warning("failed to serve client, caught exception : %s", str(ex))
                # wait a bit so that we do not loop too fast in case of error
                time.sleep(0.2)

    def _authenticate_and_build_connection(self, sock):
        '''Authenticate a client and if it succees, wraps the socket in a connection object.
        Note that this code is cut and paste from the rpyc internals and may have to be
        changed if rpyc evolves'''
        # authenticate
        if self.authenticator:
            h, p = sock.getpeername()
            try:
                sock, credentials = self.authenticator(sock)
            except AuthenticationError:
                self.logger.info("%s:%s failed to authenticate, rejecting connection", h, p)
                return None
        else:
            credentials = None
        # build a connection
        h, p = sock.getpeername()
        config = dict(self.protocol_config, credentials=credentials, connid="%s:%d"%(h, p))
        return Connection(self.service, Channel(SocketStream(sock)), config=config)

    def _accept_method(self, sock):
        '''Implementation of the accept method : only pushes the work to the internal queue.
        In case the queue is full, raises an AsynResultTimeout error'''
        try:
            # authenticate and build connection object
            conn = self._authenticate_and_build_connection(sock)
            # put the connection in the active queue
            if conn:
                fd = conn.fileno()
                self.fd_to_conn[fd] = conn
                self._add_inactive_connection(fd)
                self.clients.clear()
        except Exception:
            ex = sys.exc_info()[1]
            self.logger.warning("failed to serve client, caught exception : %s", str(ex))


class ForkingServer(Server):
    """
    A server that forks a child process for each connection. Available on 
    POSIX compatible systems only.
    
    Parameters: see :class:`Server`
    """
    
    def __init__(self, *args, **kwargs):
        if not signal:
            raise OSError("ForkingServer not supported on this platform")
        Server.__init__(self, *args, **kwargs)
        # setup sigchld handler
        self._prevhandler = signal.signal(signal.SIGCHLD, self._handle_sigchld)

    def close(self):
        Server.close(self)
        signal.signal(signal.SIGCHLD, self._prevhandler)

    @classmethod
    def _handle_sigchld(cls, signum, unused):
        try:
            while True:
                pid, dummy = os.waitpid(-1, os.WNOHANG)
                if pid <= 0:
                    break
        except OSError:
            pass
        # re-register signal handler (see man signal(2), under Portability)
        signal.signal(signal.SIGCHLD, cls._handle_sigchld)

    def _accept_method(self, sock):
        pid = os.fork()
        if pid == 0:
            # child
            try:
                self.logger.debug("child process created")
                signal.signal(signal.SIGCHLD, self._prevhandler)
                #76: call signal.siginterrupt(False) in forked child
                signal.siginterrupt(signal.SIGCHLD, False)
                self.listener.close()
                self.clients.clear()
                self._authenticate_and_serve_client(sock)
            except:
                self.logger.exception("child process terminated abnormally")
            else:
                self.logger.debug("child process terminated")
            finally:
                self.logger.debug("child terminated")
                os._exit(0)
        else:
            # parent
            sock.close()


########NEW FILE########
__FILENAME__ = teleportation
import opcode
try:
    import __builtin__
except ImportError:
    import builtins as __builtin__
from rpyc.lib.compat import is_py3k
from types import CodeType, FunctionType
from rpyc.core import brine

CODEOBJ_MAGIC = "MAg1c J0hNNzo0hn ZqhuBP17LQk8"


def decode_codeobj(codeobj):
    # adapted from dis.dis
    extended_arg = 0
    if is_py3k:
        codestr = codeobj.co_code
    else:
        codestr = [ord(ch) for ch in codeobj.co_code]
    free = None
    i = 0
    while i < len(codestr):
        op = codestr[i]
        opname = opcode.opname[op]
        i += 1
        argval = None
        if op >= opcode.HAVE_ARGUMENT:
            oparg = codestr[i] + codestr[i + 1] * 256 + extended_arg
            i += 2
            extended_arg = 0
            if op == opcode.EXTENDED_ARG:
                extended_arg = oparg * 65536
                continue
            
            if op in opcode.hasconst:
                argval = codeobj.co_consts[oparg]
            elif op in opcode.hasname:
                argval = codeobj.co_names[oparg]
            elif op in opcode.hasjrel:
                argval = i + oparg
            elif op in opcode.haslocal:
                argval = codeobj.co_varnames[oparg]
            elif op in opcode.hascompare:
                argval = opcode.cmp_op[oparg]
            elif op in opcode.hasfree:
                if free is None:
                    free = codeobj.co_cellvars + codeobj.co_freevars
                argval = free[oparg]

        yield (opname, argval)

def _export_codeobj(cobj):
    consts2 = []
    for const in cobj.co_consts:
        if brine.dumpable(const):
            consts2.append(const)
        elif isinstance(const, CodeType):
            consts2.append(_export_codeobj(const))
        else:
            raise TypeError("Cannot export a function with non-brinable constants: %r" % (const,))

    for op, arg in decode_codeobj(cobj):
        if op in ("LOAD_GLOBAL", "STORE_GLOBAL", "DELETE_GLOBAL"):
            if arg not in __builtin__.__dict__:
                raise TypeError("Cannot export a function with non-builtin globals: %r" % (arg,))

    if is_py3k:
        exported = (cobj.co_argcount, cobj.co_kwonlyargcount, cobj.co_nlocals, cobj.co_stacksize, cobj.co_flags,
            cobj.co_code, tuple(consts2), cobj.co_names, cobj.co_varnames, cobj.co_filename,
            cobj.co_name, cobj.co_firstlineno, cobj.co_lnotab, cobj.co_freevars, cobj.co_cellvars)
    else:
        exported = (cobj.co_argcount, cobj.co_nlocals, cobj.co_stacksize, cobj.co_flags,
            cobj.co_code, tuple(consts2), cobj.co_names, cobj.co_varnames, cobj.co_filename,
            cobj.co_name, cobj.co_firstlineno, cobj.co_lnotab, cobj.co_freevars, cobj.co_cellvars)

    assert brine.dumpable(exported)
    return (CODEOBJ_MAGIC, exported)

def export_function(func):
    if is_py3k:
        func_closure = func.__closure__
        func_code = func.__code__
        func_defaults = func.__defaults__
    else:
        func_closure = func.func_closure
        func_code = func.func_code
        func_defaults = func.func_defaults
    
    if func_closure:
        raise TypeError("Cannot export a function closure")
    if not brine.dumpable(func_defaults):
        raise TypeError("Cannot export a function with non-brinable defaults (func_defaults)")
    
    return func.__name__, func.__module__, func_defaults, _export_codeobj(func_code)[1]

def _import_codetup(codetup):
    if is_py3k:
        (argcnt, kwargcnt, nloc, stk, flg, codestr, consts, names, varnames, filename, name,
            firstlineno, lnotab, freevars, cellvars) = codetup
    else:
        (argcnt, nloc, stk, flg, codestr, consts, names, varnames, filename, name,
            firstlineno, lnotab, freevars, cellvars) = codetup

    consts2 = []
    for const in consts:
        if isinstance(const, tuple) and len(const) == 2 and const[0] == CODEOBJ_MAGIC:
            consts2.append(_import_codetup(const[1]))
        else:
            consts2.append(const)
    
    if is_py3k:
        return CodeType(argcnt, kwargcnt, nloc, stk, flg, codestr, tuple(consts2), names, varnames, filename, name,
            firstlineno, lnotab, freevars, cellvars)
    else:
        return CodeType(argcnt, nloc, stk, flg, codestr, tuple(consts2), names, varnames, filename, name,
            firstlineno, lnotab, freevars, cellvars)

def import_function(functup):
    name, modname, defaults, codetup = functup
    mod = __import__(modname, None, None, "*")
    codeobj = _import_codetup(codetup)
    return FunctionType(codeobj, mod.__dict__, name, defaults)



########NEW FILE########
__FILENAME__ = zerodeploy
"""
.. versionadded:: 3.3

Requires [plumbum](http://plumbum.readthedocs.org/)
"""
from __future__ import with_statement
import sys
import rpyc
import socket
from rpyc.lib.compat import BYTES_LITERAL
from rpyc.core.service import VoidService
from rpyc.core.stream import SocketStream
try:
    from plumbum import local, ProcessExecutionError, CommandNotFound
    from plumbum.path import copy
except ImportError:
    import inspect
    if any("sphinx" in line[1] or "docutils" in line[1] or "autodoc" in line[1] for line in inspect.stack()):
        # let the sphinx docs be built without requiring plumbum installed
        pass
    else:
        raise


SERVER_SCRIPT = r"""\
import sys
import os
import atexit
import shutil
from threading import Thread

here = os.path.dirname(__file__)
os.chdir(here)

def rmdir():
    shutil.rmtree(here, ignore_errors = True)
atexit.register(rmdir)

try:
    for dirpath, _, filenames in os.walk(here):
        for fn in filenames:
            if fn == "__pycache__" or (fn.endswith(".pyc") and os.path.exists(fn[:-1])):
                os.remove(os.path.join(dirpath, fn))
except Exception:
    pass

sys.path.insert(0, here)
from $MODULE$ import $SERVER$ as ServerCls
from rpyc import SlaveService

logger = None
$EXTRA_SETUP$

t = ServerCls(SlaveService, hostname = "localhost", port = 0, reuse_addr = True, logger = logger)
thd = Thread(target = t.start)
thd.setDaemon(True)
thd.start()

sys.stdout.write("%s\n" % (t.port,))
sys.stdout.flush()

try:
    sys.stdin.read()
finally:
    t.close()
    thd.join(2)
"""

class DeployedServer(object):
    """
    Sets up a temporary, short-lived RPyC deployment on the given remote machine. It will: 
    
    1. Create a temporary directory on the remote machine and copy RPyC's code 
       from the local machine to the remote temporary directory.
    2. Start an RPyC server on the remote machine, binding to an arbitrary TCP port,
       allowing only in-bound connections (``localhost`` connections). The server reports the 
       chosen port over ``stdout``.
    3. An SSH tunnel is created from an arbitrary local port (on the local host), to the remote 
       machine's chosen port. This tunnel is authenticated and encrypted.
    4. You get a ``DeployedServer`` object that can be used to connect to the newly-spawned server.
    5. When the deployment is closed, the SSH tunnel is torn down, the remote server terminates 
       and the temporary directory is deleted.
    
    :param remote_machine: a plumbum ``SshMachine`` or ``ParamikoMachine`` instance, representing 
                           an SSH connection to the desired remote machine
    :param server_class: the server to create (e.g., ``"ThreadedServer"``, ``"ForkingServer"``)
    :param extra_setup: any extra code to add to the script
    """
    
    def __init__(self, remote_machine, server_class = "rpyc.utils.server.ThreadedServer", extra_setup = "", python_executable=None):
        self.proc = None
        self.tun = None
        self.remote_machine = remote_machine
        self._tmpdir_ctx = None
        
        rpyc_root = local.path(rpyc.__file__).up()
        self._tmpdir_ctx = remote_machine.tempdir()
        tmp = self._tmpdir_ctx.__enter__()
        copy(rpyc_root, tmp / "rpyc")
        
        script = (tmp / "deployed-rpyc.py")
        modname, clsname = server_class.rsplit(".", 1)
        script.write(SERVER_SCRIPT.replace("$MODULE$", modname).replace("$SERVER$", clsname).replace("$EXTRA_SETUP$", extra_setup))
        if python_executable:
            cmd = remote_machine[python_executable]
        else:
            major = sys.version_info[0]
            minor = sys.version_info[1]
            cmd = None
            for opt in ["python%s.%s" % (major, minor), "python%s" % (major,)]:
                try:
                    cmd = remote_machine[opt]
                except CommandNotFound:
                    pass
                else:
                    break
            if not cmd:
                cmd = remote_machine.python
        
        self.proc = cmd.popen(script, new_session = True)
        
        line = ""
        try:
            line = self.proc.stdout.readline()
            self.remote_port = int(line.strip())
        except Exception:
            try:
                self.proc.terminate()
            except Exception:
                pass
            stdout, stderr = self.proc.communicate()
            raise ProcessExecutionError(self.proc.argv, self.proc.returncode, BYTES_LITERAL(line) + stdout, stderr)
        
        if hasattr(remote_machine, "connect_sock"):
            # Paramiko: use connect_sock() instead of tunnels
            self.local_port = None
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("localhost", 0))
            self.local_port = s.getsockname()[1]
            s.close()
            self.tun = remote_machine.tunnel(self.local_port, self.remote_port)

    def __del__(self):
        self.close()
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()

    def close(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            self.proc = None
        if self.tun is not None:
            try:
                self.tun.close()
            except Exception:
                pass
            self.tun = None
        if self._tmpdir_ctx is not None:
            try:
                self._tmpdir_ctx.__exit__(None, None, None)
            except Exception:
                pass
            self._tmpdir_ctx = None
    
    def connect(self, service = VoidService, config = {}):
        """Same as :func:`connect <rpyc.utils.factory.connect>`, but with the ``host`` and ``port`` 
        parameters fixed"""
        if self.local_port is None:
            # ParamikoMachine
            stream = SocketStream(self.remote_machine.connect_sock(self.remote_port))
            return rpyc.connect_stream(stream, service = service, config = config)
        else:
            return rpyc.connect("localhost", self.local_port, service = service, config = config)
    
    def classic_connect(self):
        """Same as :func:`classic.connect <rpyc.utils.classic.connect>`, but with the ``host`` and 
        ``port`` parameters fixed"""
        if self.local_port is None:
            # ParamikoMachine
            stream = SocketStream(self.remote_machine.connect_sock(self.remote_port))
            return rpyc.classic.connect_stream(stream)
        else:
            return rpyc.classic.connect("localhost", self.local_port)


class MultiServerDeployment(object):
    """
    An 'aggregate' server deployment to multiple SSH machine. It deploys RPyC to each machine
    separately, but lets you manage them as a single deployment.
    """
    def __init__(self, remote_machines, server_class = "ThreadedServer"):
        self.remote_machines = remote_machines
        # build the list incrementally, so we can clean it up if we have an exception
        self.servers = [DeployedServer(mach, server_class) for mach in remote_machines]
    
    def __del__(self):
        self.close()
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def __iter__(self):
        return iter(self.servers)
    def __len__(self):
        return len(self.servers)
    def __getitem__(self, index):
        return self.servers[index]
    
    def close(self):
        while self.servers:
            s = self.servers.pop(0)
            s.close()
    
    def connect_all(self, service = VoidService, config = {}):
        """connects to all deployed servers; returns a list of connections (order guaranteed)"""
        return [s.connect(service, config) for s in self.servers]
    def classic_connect_all(self):
        """connects to all deployed servers using classic_connect; returns a list of connections (order guaranteed)"""
        return [s.classic_connect() for s in self.servers]




########NEW FILE########
__FILENAME__ = version
version = (3, 3, 0)
version_string = "3.3.0"
release_date = "2013.07.01"


########NEW FILE########
__FILENAME__ = test_async
import time
import unittest
import rpyc

class TestAsync(unittest.TestCase):
    def setUp(self):
        self.conn = rpyc.classic.connect_thread()
        self.a_sleep = rpyc.async(self.conn.modules.time.sleep)
        self.a_int = rpyc.async(self.conn.builtin.int)

    def tearDown(self):
        self.conn.close()
    
    def test_asyncresult_api(self):
        res = self.a_sleep(2)
        self.assertFalse(res.ready)
        res.wait()
        self.assertTrue(res.ready)
        self.assertFalse(res.expired)
        self.assertFalse(res.error)
        self.assertEqual(res.value, None)

    def test_asyncresult_expiry(self):
        res = self.a_sleep(5)
        res.set_expiry(4)
        t0 = time.time()
        self.assertRaises(rpyc.AsyncResultTimeout, res.wait)
        dt = time.time() - t0
        #print( "timed out after %s" % (dt,) )
        self.assertTrue(dt >= 3.5, str(dt))
        self.assertTrue(dt <= 4.5, str(dt))

    def test_asyncresult_callbacks(self):
        res = self.a_sleep(2)
        visited = []

        def f(res):
            assert res.ready
            assert not res.error
            visited.append("f")

        def g(res):
            visited.append("g")

        res.add_callback(f)
        res.add_callback(g)
        res.wait()
        self.assertEqual(set(visited), set(["f", "g"]))
        
    def test_timed(self):
        timed_sleep = rpyc.timed(self.conn.modules.time.sleep, 5)
        res = timed_sleep(3)
        res.value
        res = timed_sleep(7)
        self.assertRaises(rpyc.AsyncResultTimeout, lambda: res.value)

    def test_exceptions(self):
        res = self.a_int("foo")
        res.wait()
        self.assertTrue(res.error)
        self.assertRaises(ValueError, lambda: res.value)

if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = test_attributes
import rpyc
import unittest


class Properties(object):
    def __init__(self):
        self._x = 0

    @property
    def counter(self):
        self._x += 1
        return self._x

    @property
    def dont_touch_me(self):
        # reconstruct bug reported by Andrew Stromnov
        # http://groups.google.com/group/rpyc/msg/aa6110259481f194
        1/0


class TestAttributes(unittest.TestCase):
    def setUp(self):
        self.conn = rpyc.classic.connect_thread()

    def tearDown(self):
        self.conn.close()

    def test_properties(self):
        p = self.conn.modules["test_attributes"].Properties()
        print( p.counter )                # 1
        print( p.counter )                # 2
        print( p.counter )                # 3
        self.assertEqual(p.counter, 4)    # 4


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_attr_access
import rpyc
import unittest
import time
from rpyc.utils.server import ThreadedServer
from threading import Thread


class MyClass(object):
    def foo(self):
        return "foo"
    def bar(self):
        return "bar"
    def spam(self):
        return "spam"

class YourClass(object):
    def lala(self):
        return MyClass()
    def baba(self):
        return "baba"
    def gaga(self):
        return "gaga"

try:
    long
except NameError:
    long = int
    unicode = str

try:
    bytes
except NameError:
    bytes = str

class Protector(object):
    def __init__(self, safetypes = (int, list, bool, tuple, str, float, long, unicode, bytes)):
        self._safetypes = set(safetypes)
        self._typereg = {}
    def register(self, typ, attrs):
        self._typereg[typ] = frozenset(attrs)
    def wrap(self, obj):
        class Restrictor(object):
            def __call__(_, *args, **kwargs):
                return self.wrap(obj(*args, **kwargs))
            def _rpyc_getattr(_, name):
                if type(obj) not in self._safetypes:
                    attrs = self._typereg.get(type(obj), ())
                    if name not in attrs:
                        raise AttributeError(name)
                obj2 = getattr(obj, name)
                return self.wrap(obj2)
            __getattr__ = _rpyc_getattr
        return Restrictor()

class MyService(rpyc.Service):
    def exposed_get_one(self):
        return rpyc.restricted(MyClass(), ["foo", "bar"])
    
    def exposed_get_two(self):
        protector = Protector()
        protector.register(MyClass, ["foo", "spam"])
        protector.register(YourClass, ["lala", "baba"])
        return protector.wrap(YourClass())

class TestRestricted(unittest.TestCase):
    def setUp(self):
        self.server = ThreadedServer(MyService, port = 0)
        self.thd = Thread(target = self.server.start)
        self.thd.start()
        time.sleep(1)
        self.conn = rpyc.connect("localhost", self.server.port)

    def tearDown(self):
        self.conn.close()
        self.server.close()
        self.thd.join()

    def test_restricted(self):
        obj = self.conn.root.get_one()
        self.assertEqual(obj.foo(), "foo")
        self.assertEqual(obj.bar(), "bar")
        self.assertRaises(AttributeError, lambda: obj.spam)

#    def test_type_protector(self):
#        obj = self.conn.root.get_two()
#        assert obj.baba() == "baba"
#        try:
#            obj.gaga()
#        except AttributeError:
#            pass
#        else:
#            assert False, "expected an attribute error!"
#        obj2 = obj.lala()
#        assert obj2.foo() == "foo"
#        assert obj2.spam() == "spam"
#        try:
#            obj.bar()
#        except AttributeError:
#            pass
#        else:
#            assert False, "expected an attribute error!"
#        


if __name__ == "__main__":
    unittest.main()





########NEW FILE########
__FILENAME__ = test_brine
from rpyc.core import brine
from rpyc.lib.compat import is_py3k
import unittest


class BrineTest(unittest.TestCase):
    def test_brine_2(self):
        if is_py3k:
            exec('''x = (b"he", 7, "llo", 8, (), 900, None, True, Ellipsis, 18.2, 18.2j + 13,
                 slice(1, 2, 3), frozenset([5, 6, 7]), NotImplemented, (1,2))''', globals())
        else:
            exec('''x = ("he", 7, u"llo", 8, (), 900, None, True, Ellipsis, 18.2, 18.2j + 13,
                 slice(1, 2, 3), frozenset([5, 6, 7]), NotImplemented, (1,2))''')
        self.assertTrue(brine.dumpable(x))
        y = brine.dump(x)
        z = brine.load(y)
        self.assertEqual(x, z)


if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = test_classic
import os
import rpyc
import unittest


class ClassicMode(unittest.TestCase):
    def setUp(self):
        self.conn = rpyc.classic.connect_thread()
    
    def tearDown(self):
        self.conn.close()
        self.conn = None
    
    def test_piped_server(self):
        # this causes the following lines to be printed to stderr on Windows:
        #
        # close failed in file object destructor:
        #     IOError: [Errno 9] Bad file descriptor
        # close failed in file object destructor:
        #     IOError: [Errno 9] Bad file descriptor
        #
        # this is because the pipe objects that hold the child process' stdin
        # and stdout were disowned by Win32PipeStream (it forcefully takes
        # ownership of the file handles). so when the low-level pipe objects
        # are gc'ed, they cry that their fd is already closed. this is all
        # considered harmless, but there's no way to disable that message
        # to stderr
        server_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "rpyc_classic.py")
        conn = rpyc.classic.connect_subproc(server_file)
        conn.modules.sys.path.append("xxx")
        self.assertEqual(conn.modules.sys.path.pop(-1), "xxx")
        conn.close()
        self.assertEqual(conn.proc.wait(), 0)

    def test_buffiter(self):
        bi = rpyc.buffiter(self.conn.builtin.range(10000))
        self.assertEqual(list(bi), list(range(10000)))

    def test_classic(self):
        print( self.conn.modules.sys )
        print( self.conn.modules["xml.dom.minidom"].parseString("<a/>") )
        self.conn.execute("x = 5")
        self.assertEqual(self.conn.namespace["x"], 5)
        self.assertEqual(self.conn.eval("1+x"), 6)

    def test_isinstance(self):
        x = self.conn.builtin.list((1,2,3,4))
        print( x )
        print( type(x) )
        print( x.__class__ )
        self.assertTrue(isinstance(x, list))
        self.assertTrue(isinstance(x, rpyc.BaseNetref))
    
    def test_mock_connection(self):
        from rpyc.utils.classic import MockClassicConnection
        import sys
        import xml.dom.minidom
        conn = MockClassicConnection()
        self.assertTrue(conn.modules.sys is sys)
        self.assertTrue(conn.modules["xml.dom.minidom"].Element is xml.dom.minidom.Element)
        self.assertTrue(conn.builtin.open is open)
        self.assertEqual(conn.eval("2+3"), 5)


if __name__ == "__main__":
    unittest.main()



########NEW FILE########
__FILENAME__ = test_context_managers
from __future__ import with_statement
import rpyc
import unittest

from contextlib import contextmanager

on_context_enter = False
on_context_exit = False

class MyService(rpyc.Service):
    @contextmanager
    def exposed_context(self, y):
        global on_context_enter, on_context_exit
        on_context_enter = True
        try:
            yield 17 + y
        finally:
            on_context_exit = True


class TestContextManagers(unittest.TestCase):
    def setUp(self):
        self.conn = rpyc.connect_thread(remote_service=MyService)

    def tearDown(self):
        self.conn.close()
    
    def test_context(self):
        with self.conn.root.context(3) as x:
            print( "entering test" )
            self.assertTrue(on_context_enter)
            self.assertFalse(on_context_exit)
            print( "got past context enter" )
            self.assertEqual(x, 20)
            print( "got past x=20" )
        self.assertTrue(on_context_exit)
        print( "got past on_context_exit" )


if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = test_custom_service
import math
import time

import rpyc
import unittest

on_connect_called = False
on_disconnect_called = False

class MyMeta(type):
    def spam(self):
        return self.__name__ * 5

class MyClass(object):
    __metaclass__ = MyMeta

if not isinstance(MyMeta, MyMeta):
    # python 3 compatibility
    MyClass = MyMeta(MyClass.__name__, MyClass.__bases__, dict(MyClass.__dict__))

class MyService(rpyc.Service):
    def on_connect(self):
        global on_connect_called
        on_connect_called = True

    def on_disconnect(self):
        global on_disconnect_called
        on_disconnect_called = True

    def exposed_distance(self, p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        return math.sqrt((x2-x1)**2 + (y2-y1)**2)

    def exposed_getlist(self):
        return [1, 2, 3]

    def foobar(self):
        assert False

    def exposed_getmeta(self):
        return MyClass()


class TestCustomService(unittest.TestCase):
    config = {}

    def setUp(self):
        global on_connect_called
        self.conn = rpyc.connect_thread(remote_service=MyService)
        self.conn.root # this will block until the service is initialized,
        # so we can be sure on_connect_called is True by that time
        self.assertTrue(on_connect_called)
        on_connect_called = False

    def tearDown(self):
        global on_disconnect_called
        self.conn.close()
        time.sleep(0.5) # this will wait a little, making sure
        # on_disconnect_called is already True
        self.assertTrue(on_disconnect_called)
        on_disconnect_called = False

    def test_aliases(self):
        print( "service name: %s" % (self.conn.root.get_service_name(),) )

    def test_distance(self):
        assert self.conn.root.distance((2,7), (5,11)) == 5

    def test_attributes(self):
        self.conn.root.distance
        self.conn.root.exposed_distance
        self.conn.root.getlist
        self.conn.root.exposed_getlist
        # this is not an exposed attribute:
        self.assertRaises(AttributeError, lambda: self.conn.root.foobar()) 

    def test_safeattrs(self):
        x = self.conn.root.getlist()
        #self.require(x == [1, 2, 3]) -- can't compare remote objects, sorry
        #self.require(x * 2 == [1, 2, 3, 1, 2, 3])
        self.assertEqual([y*2 for y in x], [2, 4, 6])

    def test_metaclasses(self):
        x = self.conn.root.getmeta()
        print( x )


if __name__ == "__main__":
    unittest.main()



########NEW FILE########
__FILENAME__ = test_deploy
from __future__ import with_statement 
import unittest
import sys
from plumbum import SshMachine
from rpyc.utils.zerodeploy import DeployedServer


class TestDeploy(unittest.TestCase):
    def test_deploy(self):
        rem = SshMachine("localhost")
        SshMachine.python = rem[sys.executable]
        with DeployedServer(rem) as dep:
            conn = dep.classic_connect()
            print (conn.modules.sys)
            func = conn.modules.os.getcwd
            print (func())
        
        try:
            func()
        except EOFError:
            pass
        else:
            self.fail("expected an EOFError")
    
    def test_deploy_paramiko(self):
        try:
            import paramiko     # @UnusedImport
        except Exception:
            self.skipTest("Paramiko is not available")
        from plumbum.machines.paramiko_machine import ParamikoMachine
        
        rem = ParamikoMachine("localhost", missing_host_policy = paramiko.AutoAddPolicy())
        with DeployedServer(rem) as dep:
            conn = dep.classic_connect()
            print (conn.modules.sys)
            func = conn.modules.os.getcwd
            print (func())

        try:
            func()
        except EOFError:
            pass
        else:
            self.fail("expected an EOFError")


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_ipv6
import rpyc
import threading
import socket
import unittest
import time
from rpyc.utils.server import ThreadedServer
from rpyc import SlaveService
from nose import SkipTest

if not getattr(socket, "has_ipv6", False):
    raise SkipTest("requires IPv6")


class Test_IPv6(unittest.TestCase):
    def setUp(self):
        self.server = ThreadedServer(SlaveService, port = 0, ipv6 = True)
        self.server.logger.quiet = True
        self.thd = threading.Thread(target = self.server.start)
        self.thd.start()
        time.sleep(1)

    def tearDown(self):
        self.server.close()
        self.thd.join()

    def test_ipv6_conenction(self):
        c = rpyc.classic.connect("::1", port = self.server.port, ipv6 = True)
        print( repr(c) )
        print( c.modules.sys )
        print( c.modules["xml.dom.minidom"].parseString("<a/>") )
        c.execute("x = 5")
        self.assertEqual(c.namespace["x"], 5)
        self.assertEqual(c.eval("1+x"), 6)
        c.close()


if __name__ == "__main__":
    unittest.main()




########NEW FILE########
__FILENAME__ = test_refcount
import rpyc
import gc
import unittest


class TestRefcount(unittest.TestCase):
    def setUp(self):
        self.conn = rpyc.classic.connect_thread()

    def tearDown(self):
        self.conn.close()

    def test_refcount(self):
        self.conn.execute("""
deleted_objects = []

class DummyObject(object):
    def __init__(self, name):
        self.name = name
    def __del__(self):
        deleted_objects.append(self.name)""")
        rDummyObject = self.conn.namespace["DummyObject"]
        d1 = rDummyObject("d1")
        d2 = rDummyObject("d2")
        d3 = rDummyObject("d3")
        d4 = rDummyObject("d4") #@UnusedVariable
        d2_copy = d2
        del d1
        del d3
        gc.collect()
        self.assertEqual(set(self.conn.namespace["deleted_objects"]), set(["d1", "d3"]))
        del d2
        gc.collect()
        self.assertEqual(set(self.conn.namespace["deleted_objects"]), set(["d1", "d3"]))
        del d2_copy
        gc.collect()
        self.assertEqual(set(self.conn.namespace["deleted_objects"]), set(["d1", "d2", "d3"]))


if __name__ == "__main__":
    unittest.main()




########NEW FILE########
__FILENAME__ = test_registry
import time
import unittest

from threading import Thread
from rpyc.utils.registry import TCPRegistryServer, TCPRegistryClient
from rpyc.utils.registry import UDPRegistryServer, UDPRegistryClient


PRUNING_TIMEOUT = 5


class BaseRegistryTest(object):
    def _get_server(self):
        raise NotImplementedError

    def _get_client(self):
        raise NotImplementedError

    def setUp(self):
        self.server = self._get_server()
        self.server.logger.quiet = True
        self.server_thread = Thread(target=self.server.start)
        self.server_thread.setDaemon(True)
        self.server_thread.start()
        time.sleep(0.1)

    def tearDown(self):
        self.server.close()
        self.server_thread.join()

    def test_api(self):
        c = self._get_client()
        c.logger.quiet = True
        c.register(("FOO",), 12345)
        c.register(("FOO",), 45678)
        res = c.discover("FOO")
        expected = (12345, 45678)
        self.assertEqual(set(p for _, p in res), set(expected))
        c.unregister(12345)
        res = c.discover("FOO")
        expected = (45678,)
        self.assertEqual(set(p for _, p in res), set(expected))

    def test_pruning(self):
        c = self._get_client()
        c.logger.quiet = True
        c.register(("BAR",), 17171)
        
        time.sleep(1)
        res = c.discover("BAR")
        self.assertEqual(set(p for _, p in res), set((17171,)))

        time.sleep(PRUNING_TIMEOUT)
        res = c.discover("BAR")
        self.assertEqual(res, ())


class TestTcpRegistry(BaseRegistryTest, unittest.TestCase):
    def _get_server(self):
        return TCPRegistryServer(pruning_timeout=PRUNING_TIMEOUT)

    def _get_client(self):
        return TCPRegistryClient("localhost")

class TestUdpRegistry(BaseRegistryTest, unittest.TestCase):
    def _get_server(self):
        return UDPRegistryServer(pruning_timeout=PRUNING_TIMEOUT)

    def _get_client(self):
        return UDPRegistryClient()


if __name__ == "__main__":
    unittest.main()



########NEW FILE########
__FILENAME__ = test_remoting
import os
import tempfile
import shutil
import unittest
from nose import SkipTest
import rpyc


class Test_Remoting(unittest.TestCase):
    def setUp(self):
        self.conn = rpyc.classic.connect_thread()

    def tearDown(self):
        self.conn.close()

    def test_files(self):
        base = tempfile.mkdtemp()
        base1 = os.path.join(base, "1")
        base2 = os.path.join(base, "2")
        base3 = os.path.join(base, "3")
        os.mkdir(base1)
        for i in range(10):
            f = open(os.path.join(base1, "foofoo%d" % (i,)), "w")
            f.close()
        os.mkdir(os.path.join(base1, "somedir1"))

        rpyc.classic.upload(self.conn, base1, base2)
        self.assertEqual(os.listdir(base1), os.listdir(base2))

        rpyc.classic.download(self.conn, base2, base3)
        self.assertEqual(os.listdir(base2), os.listdir(base3))

        shutil.rmtree(base)

    def test_distribution(self):
        raise SkipTest("TODO: upload a package and a module")

    def test_interactive(self):
        raise SkipTest("Need to be manually")
        print( "type Ctrl+D to exit (Ctrl+Z on Windows)" )
        rpyc.classic.interact(self.conn)

    def test_post_mortem(self):
        raise SkipTest("Need to be manually")
        try:
            self.conn.modules.sys.path[100000]
        except IndexError:
            print( "type 'q' to exit" )
            rpyc.classic.pm(self.conn)
            raise
        else:
            self.fail("expected an exception")

    def test_migration(self):
        l = rpyc.classic.obtain(self.conn.modules.sys.path)
        self.assertTrue(type(l) is list)
        rl = rpyc.classic.deliver(self.conn, l)
        self.assertTrue(isinstance(rl, rpyc.BaseNetref))


if __name__ == "__main__":
    unittest.main()




########NEW FILE########
__FILENAME__ = test_splitbrain
from __future__ import with_statement
import subprocess
import sys
import os
import rpyc
import unittest
import tempfile
import shutil
import traceback
from rpyc.experimental.splitbrain import splitbrain, localbrain, enable_splitbrain, disable_splitbrain


if not hasattr(unittest.TestCase, "assertIn"):
    unittest.TestCase.assertIn = lambda self, member, container, msg = None: self.assertTrue(member in container, msg)
if not hasattr(unittest.TestCase, "assertNotIn"):
    unittest.TestCase.assertNotIn = lambda self, member, container, msg = None: self.assertFalse(member in container, msg)

def b(st):
    if sys.version_info[0] >= 3:
        return bytes(st, "latin-1")
    else:
        return st

class SplitbrainTest(unittest.TestCase):
    def setUp(self):
        enable_splitbrain()
        server_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "rpyc_classic.py")
        self.proc = subprocess.Popen([sys.executable, server_file, "--mode=oneshot", "--host=localhost", "-p0"],
            stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        line = self.proc.stdout.readline().strip()
        if not line:
            print (self.proc.stderr.read())
            self.fail("server failed to start")
        self.assertEqual(line, b("rpyc-oneshot"), "server failed to start")
        host, port = self.proc.stdout.readline().strip().split(b("\t"))
        self.conn = rpyc.classic.connect(host, int(port))

    def tearDown(self):
        self.conn.close()
        disable_splitbrain()

    def test(self):
        here = os.getcwd()
        mypid = os.getpid()
        with open("split-test.txt", "w") as f:
            f.write("foobar")
        with splitbrain(self.conn):
            try:
                path = tempfile.mkdtemp()

                import email

                self.assertNotIn("stale", repr(email))

                os.chdir(path)
                hispid = os.getpid()
                self.assertNotEqual(mypid, hispid)
                here2 = os.getcwd()
                self.assertNotEqual(here, here2)
                self.assertFalse(os.path.exists("split-test.txt"))
                with open("split-test.txt", "w") as f:
                    f.write("spam")

                with localbrain():
                    self.assertEqual(os.getpid(), mypid)
                    with open("split-test.txt", "r") as f:
                        self.assertEqual(f.read(), "foobar")

                try:
                    def f():
                        g()
                    def g():
                        h()
                    def h():
                        open("crap.txt", "r")
                    f()
                except IOError:
                    with localbrain():
                        tbtext = "".join(traceback.format_exception(*sys.exc_info()))
                    # pdb.post_mortem(sys.exc_info()[2])
                    self.assertIn("f()", tbtext)
                    self.assertIn("g()", tbtext)
                    self.assertIn("h()", tbtext)
                else:
                    self.fail("This should have raised a IOError")

            finally:
                # we must move away from the tempdir to delete it (at least on windows)
                os.chdir("/")
                shutil.rmtree(path)

        self.assertIn("stale", repr(email))

        self.assertEqual(os.getpid(), mypid)
        self.assertEqual(os.getcwd(), here)

        os.remove("split-test.txt")



if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = test_ssh
import rpyc
import time
import threading
import sys
import os
import unittest
from rpyc.utils.server import ThreadedServer
from rpyc import SlaveService
from plumbum import SshMachine


class Test_Ssh(unittest.TestCase):
    def setUp(self):
        if sys.platform == "win32":
            self.server = None
            os.environ["HOME"] = os.path.expanduser("~")
            self.remote_machine = SshMachine("localhost")
        else:
            # assume "ssh localhost" is configured to run without asking for password 
            self.server = ThreadedServer(SlaveService, hostname = "localhost", 
                ipv6 = False, port = 18888, auto_register=False)
            t = threading.Thread(target=self.server.start)
            t.setDaemon(True)
            t.start()
            time.sleep(0.5)
            self.remote_machine = SshMachine("localhost")

    def tearDown(self):
        if self.server:
            self.server.close()

    def test_simple(self):
        conn = rpyc.classic.ssh_connect(self.remote_machine, 18888)
        print( "server's pid =", conn.modules.os.getpid())
        conn.modules.sys.stdout.write("hello over ssh\n")
        conn.modules.sys.stdout.flush()

    def test_connect(self):
        conn2 = rpyc.ssh_connect(self.remote_machine, 18888, service=SlaveService)
        conn2.modules.sys.stdout.write("hello through rpyc.ssh_connect()\n")
        conn2.modules.sys.stdout.flush()

if __name__ == "__main__":
    unittest.main()



########NEW FILE########
__FILENAME__ = test_ssl
import rpyc
import os
import threading
import unittest
import time
from rpyc.utils.authenticators import SSLAuthenticator
from rpyc.utils.server import ThreadedServer
from rpyc import SlaveService
from nose import SkipTest

try:
    import ssl #@UnusedImport
except ImportError:
    raise SkipTest("requires ssl")


class Test_SSL(unittest.TestCase):
    '''
    created key like that
    http://www.akadia.com/services/ssh_test_certificate.html

    openssl req -newkey rsa:1024 -nodes -keyout mycert.pem -out mycert.pem
    '''

    def setUp(self):
        self.key = os.path.join( os.path.dirname(__file__) , "server.key")
        self.cert =  os.path.join( os.path.dirname(__file__) , "server.crt")
        print( self.cert, self.key )

        authenticator = SSLAuthenticator(self.key, self.cert)
        self.server = ThreadedServer(SlaveService, port = 18812,
            auto_register=False, authenticator = authenticator)
        self.server.logger.quiet = False
        t = threading.Thread(target=self.server.start)
        t.start()
        time.sleep(1)

    def tearDown(self):
        self.server.close()

    def test_ssl_conenction(self):
        c = rpyc.classic.ssl_connect("localhost", port = 18812,
            keyfile=self.key, certfile=self.cert)
        print( repr(c) )
        print( c.modules.sys )
        print( c.modules["xml.dom.minidom"].parseString("<a/>") )
        c.execute("x = 5")
        self.assertEqual(c.namespace["x"], 5)
        self.assertEqual(c.eval("1+x"), 6)
        c.close()

if __name__ == "__main__":
    unittest.main()


########NEW FILE########
__FILENAME__ = test_teleportation
from __future__ import with_statement
import subprocess
import sys
import os
import rpyc
import unittest
from rpyc.utils.teleportation import export_function, import_function
from rpyc.utils.classic import teleport_function


def b(st):
    if sys.version_info[0] >= 3:
        return bytes(st, "latin-1")
    else:
        return st

def f(a):
    def g(b):
        return a + int(b)
    return g

def h(a):
    import os
    return a * os.getpid()


class TeleportationTest(unittest.TestCase):
    def setUp(self):
        server_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "rpyc_classic.py")
        self.proc = subprocess.Popen([sys.executable, server_file, "--mode=oneshot", "--host=localhost", "-p0"],
            stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        line = self.proc.stdout.readline().strip()
        if not line:
            print (self.proc.stderr.read())
            self.fail("server failed to start")
        self.assertEqual(line, b("rpyc-oneshot"), "server failed to start")
        host, port = self.proc.stdout.readline().strip().split(b("\t"))
        self.conn = rpyc.classic.connect(host, int(port))

    def tearDown(self):
        self.conn.close()

    def test(self):
        exp = export_function(f)
        f2 = import_function(exp)
        self.assertEqual(f(6)(7), f2(6)(7))

        # HACK: needed so the other side could import us (for globals)
        mod = self.conn.modules.types.ModuleType(__name__)
        self.conn.modules.sys.modules[__name__] = mod
        mod.__builtins__ = self.conn.builtins

        h2 = teleport_function(self.conn, h)
        self.assertNotEqual(h(7), h2(7))



if __name__ == "__main__":
    unittest.main()




########NEW FILE########
__FILENAME__ = test_threaded_server
import rpyc
import time
from rpyc.utils.server import ThreadedServer
from rpyc import SlaveService
import threading
import unittest


class Test_ThreadedServer(unittest.TestCase):
    def setUp(self):
        self.server = ThreadedServer(SlaveService, port=18878, auto_register=False)
        self.server.logger.quiet = False
        t = threading.Thread(target=self.server.start)
        t.start()
        time.sleep(0.5)

    def tearDown(self):
        self.server.close()

    def test_conenction(self):
        c = rpyc.classic.connect("localhost", port=18878)
        print( c.modules.sys )
        print( c.modules["xml.dom.minidom"].parseString("<a/>") )
        c.execute("x = 5")
        self.assertEqual(c.namespace["x"], 5)
        self.assertEqual(c.eval("1+x"), 6)
        c.close()


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_threads
#!/usr/bin/env python
import threading
import time
import unittest
import rpyc

class MyService(rpyc.Service):
    class exposed_Invoker(object):
        def __init__(self, callback, interval):
            self.callback = rpyc.async(callback)
            self.interval = interval
            self.active = True
            self.thread = threading.Thread(target=self.work)
            self.thread.setDaemon(True)
            self.thread.start()

        def exposed_stop(self):
            self.active = False
            self.thread.join()

        def work(self):
            while self.active:
                self.callback(time.time())
                time.sleep(self.interval)

    def exposed_foo(self, x):
        time.sleep(2)
        return x * 17

class Test_Multithreaded(unittest.TestCase):
    def setUp(self):
        self.conn = rpyc.connect_thread(remote_service=MyService)
        self.bgserver = rpyc.BgServingThread(self.conn)

    def tearDown(self):
        self.bgserver.stop()
        self.conn.close()

    def test_invoker(self):
        counter = [0]
        def callback(x):
            counter[0] += 1
            print( "callback %s" % (x,) )
        invoker = self.conn.root.Invoker(callback, 1)
        # 3 * 2sec = 6 sec = ~6 calls to callback
        for i in range(3):
            print( "foo%s = %s" % (i, self.conn.root.foo(i)) )
        invoker.stop()
        print( "callback called %s times" % (counter[0],) )
        self.assertTrue(counter[0] >= 5)


if __name__ == "__main__":
    unittest.main()




########NEW FILE########
__FILENAME__ = test_win32pipes
import sys
import time
import unittest
from threading import Thread

from nose import SkipTest
if sys.platform != "win32":
    raise SkipTest("Requires windows")

import rpyc
from rpyc.core.stream import PipeStream, NamedPipeStream
from rpyc.lib.compat import BYTES_LITERAL


class Test_Pipes(unittest.TestCase):
    def test_basic_io(self):
        p1, p2 = PipeStream.create_pair()
        p1.write(BYTES_LITERAL("hello"))
        assert p2.poll(0)
        assert p2.read(5) == BYTES_LITERAL("hello")
        assert not p2.poll(0)
        p2.write(BYTES_LITERAL("world"))
        assert p1.poll(0)
        assert p1.read(5) == BYTES_LITERAL("world")
        assert not p1.poll(0)
        p1.close()
        p2.close()

    def test_rpyc(self):
        p1, p2 = PipeStream.create_pair()
        client = rpyc.connect_stream(p1)
        server = rpyc.connect_stream(p2)
        server_thread = Thread(target=server.serve_all)
        server_thread.start()
        assert client.root.get_service_name() == "VOID"
        t = rpyc.BgServingThread(client)
        assert server.root.get_service_name() == "VOID"
        t.stop()
        client.close()
        server.close()
        server_thread.join()


class Test_NamedPipe(object):
    def setUp(self):
        self.pipe_server_thread = Thread(target=self.pipe_server)
        self.pipe_server_thread.start()
        time.sleep(1) # make sure server is accepting already
        self.np_client = NamedPipeStream.create_client("floop")
        self.client = rpyc.connect_stream(self.np_client)

    def tearDown(self):
        self.client.close()
        self.server.close()
        self.pipe_server_thread.join()

    def pipe_server(self):
        self.np_server = NamedPipeStream.create_server("floop")
        self.server = rpyc.connect_stream(self.np_server)
        self.server.serve_all()

    def test_rpyc(self):
        assert self.client.root.get_service_name() == "VOID"
        t = rpyc.BgServingThread(self.client)
        assert self.server.root.get_service_name() == "VOID"
        t.stop()


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
