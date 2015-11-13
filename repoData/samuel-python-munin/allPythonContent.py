__FILENAME__ = munin-node
#!/usr/bin/env python

import os
import socket
import SocketServer
import sys
import threading
import time
from subprocess import Popen, PIPE

PLUGIN_PATH = "/etc/munin/plugins"

def parse_args():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-p", "--pluginpath", dest="plugin_path",
                      help="path to plugins", default=PLUGIN_PATH)
    (options, args) = parser.parse_args()
    return options, args


def execute_plugin(path, cmd=""):
    args = [path]
    if cmd:
        args.append(cmd)
    p = Popen(args, stdout=PIPE)
    output = p.communicate()[0]
    return output

if os.name == 'posix':
    def become_daemon(our_home_dir='.', out_log='/dev/null',
                      err_log='/dev/null', umask=022):
        "Robustly turn into a UNIX daemon, running in our_home_dir."
        # First fork
        try:
            if os.fork() > 0:
                sys.exit(0)     # kill off parent
        except OSError, e:
            sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror))
            sys.exit(1)
        os.setsid()
        os.chdir(our_home_dir)
        os.umask(umask)

        # Second fork
        try:
            if os.fork() > 0:
                os._exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror))
            os._exit(1)

        si = open('/dev/null', 'r')
        so = open(out_log, 'a+', 0)
        se = open(err_log, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        # Set custom file descriptors so that they get proper buffering.
        sys.stdout, sys.stderr = so, se
else:
    def become_daemon(our_home_dir='.', out_log=None, err_log=None, umask=022):
        """
        If we're not running under a POSIX system, just simulate the daemon
        mode by doing redirections and directory changing.
        """
        os.chdir(our_home_dir)
        os.umask(umask)
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()
        if err_log:
            sys.stderr = open(err_log, 'a', 0)
        else:
            sys.stderr = NullDevice()
        if out_log:
            sys.stdout = open(out_log, 'a', 0)
        else:
            sys.stdout = NullDevice()

    class NullDevice:
        "A writeable object that writes to nowhere -- like /dev/null."
        def write(self, s):
            pass

class MuninRequestHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        plugins = []
        for x in os.listdir(self.server.options.plugin_path):
            if x.startswith('.'):
                continue
            fullpath = os.path.join(self.server.options.plugin_path, x)
            if not os.path.isfile(fullpath):
                continue
            plugins.append(x)
            
        node_name = socket.gethostname().split('.')[0]
        self.wfile.write("# munin node at %s\n" % node_name)
        while True:
            line = self.rfile.readline()
            if not line:
                break
            line = line.strip()

            cmd = line.split(' ', 1)
            plugin = (len(cmd) > 1) and cmd[1] or None

            if cmd[0] == "list":
                self.wfile.write("%s\n" % " ".join(plugins))
            elif cmd[0] == "nodes":
                self.wfile.write("nodes\n%s\n.\n" % (node_name))
            elif cmd[0] == "version":
                self.wfile.write("munins node on chatter1 version: 1.2.6\n")
            elif cmd[0] in ("fetch", "config"):
                if plugin not in plugins:
                    self.wfile.write("# Unknown service\n.\n")
                    continue
                c = (cmd[0] == "config") and "config" or ""
                out = execute_plugin(os.path.join(self.server.options.plugin_path, plugin), c)
                self.wfile.write(out)
                if out and out[-1] != "\n":
                    self.wfile.write("\n")
                self.wfile.write(".\n")
            elif cmd[0] == "quit":
                break
            else:
                self.wfile.write("# Unknown command. Try list, nodes, config, fetch, version or quit\n")


class MuninServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 4949
    if sys.version_info[:3] >= (2, 6, 0):
        server = MuninServer((HOST, PORT), MuninRequestHandler, bind_and_activate=False)
        server.allow_reuse_address = True
        server.server_bind()
        server.server_activate()
    else:
        server = MuninServer((HOST, PORT), MuninRequestHandler)
    ip, port = server.server_address
    options, args = parse_args()
    options.plugin_path = os.path.abspath(options.plugin_path)
    server.options = options

    become_daemon()
    server.serve_forever()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# python-munin documentation build configuration file, created by
# sphinx-quickstart on Mon Jul 27 14:30:15 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo']
try:
    from github.tools import sphinx
except ImportError:
    pass
else:
    extensions.append('github.tools.sphinx')

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'python-munin'
copyright = u'2009, Samuel Stauffer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.4'
# The full version, including alpha/beta/rc tags.
release = '1.4'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = [] # ['_static']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'python-munindoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'python-munin.tex', u'python-munin Documentation',
   u'Samuel Stauffer', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = cassandra
from __future__ import division

import os
import re
import socket
import time
from subprocess import Popen, PIPE

from munin import MuninPlugin

space_re = re.compile(r"\s+")

class MuninCassandraPlugin(MuninPlugin):
    category = "Cassandra"

    def __init__(self, *args, **kwargs):
        super(MuninCassandraPlugin, self).__init__(*args, **kwargs)
        self.nodetool_path = os.environ["NODETOOL_PATH"]
        self.host = socket.gethostname()
        self.keyspaces = [x for x in os.environ.get('CASSANDRA_KEYSPACE', '').split(',') if x]

    def execute_nodetool(self, cmd):
        p = Popen([self.nodetool_path, "-host", self.host, cmd], stdout=PIPE)
        output = p.communicate()[0]
        return output

    def parse_cfstats(self, text):
        text = text.strip().split('\n')
        cfstats = {}
        cf = None
        for line in text:
            line = line.strip()
            if not line or line.startswith('-'):
                continue

            name, value = line.strip().split(': ', 1)
            if name == "Keyspace":
                ks = {'cf': {}}
                cf = None
                cfstats[value] = ks
            elif name == "Column Family":
                cf = {}
                ks['cf'][value] = cf
            elif cf is None:
                ks[name] = value
            else:
                cf[name] = value
        return cfstats

    def cfstats(self):
        return self.parse_cfstats(self.execute_nodetool("cfstats"))

    def cinfo(self):
        text = self.execute_nodetool("info")
        lines = text.strip().split('\n')
        token = lines[0]
        info = {}
        for l in lines[1:]:
            name, value = l.split(':')
            info[name.strip()] = value.strip()
        l_num, l_units = info['Load'].split(' ', 1)
        l_num = float(l_num)
        if l_units == "KB":
            scale = 1024
        elif l_units == "MB":
            scale = 1024*1024
        elif l_units == "GB":
            scale = 1024*1024*1024
        elif l_units == "TB":
            scale = 1024*1024*1024*1024
        info['Load'] = int(l_num * scale)
        info['token'] = token
        return info

    def tpstats(self):
        out = self.execute_nodetool("tpstats")
        tpstats = {}
        for line in out.strip().split('\n')[1:]:
            name, active, pending, completed = space_re.split(line)
            tpstats[name] = dict(active=int(active), pending=int(pending), completed=int(completed))
        return tpstats

########NEW FILE########
__FILENAME__ = ddwrt

# https://192.168.1.10/Info.live.htm

import os
import re
import urllib2
from munin import MuninPlugin

class DDWrtPlugin(MuninPlugin):
    category = "Wireless"

    def __init__(self):
        super(DDWrtPlugin, self).__init__()
        self.root_url = os.environ.get('DDWRT_URL') or "http://192.168.1.1"
        self.url = self.root_url + "/Info.live.htm"

    def get_info(self):
        res = urllib2.urlopen(self.url)
        text = res.read()
        return dict(
            x[1:-1].split('::')
            for x in text.split('\n')
        )

########NEW FILE########
__FILENAME__ = gearman
#!/usr/bin/env python

import os
import re
import socket
from munin import MuninPlugin

worker_re = re.compile(r'^(?P<fd>\d+) (?P<ip>[\d\.]+) (?P<client_id>[^\s]+) :\s?(?P<abilities>.*)$')

class MuninGearmanPlugin(MuninPlugin):
    category = "Gearman"

    def __init__(self):
        super(MuninGearmanPlugin, self).__init__()
        addr = os.environ.get('GM_SERVER') or "127.0.0.1"
        port = int(addr.split(':')[-1]) if ':' in addr else 4730
        host = addr.split(':')[0]
        self.addr = (host, port)
        self._sock = None

    def connect(self):
        if not self._sock:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect(self.addr)
        return self._sock

    def disconnect(self):
        if self._sock:
            self._sock.close()

    def get_workers(self):
        sock = self.connect()
        sock.send("workers\n")
        buf = ""
        while ".\n" not in buf:
            buf += sock.recv(8192)

        info = []
        for l in buf.split('\n'):
            if l.strip() == '.':
                break
            m = worker_re.match(l)
            i = m.groupdict()
            i['abilities'] = [x for x in i['abilities'].split(' ') if x]
            info.append(i)
        return info

    def get_status(self):
        sock = self.connect()
        sock.send("status\n")
        buf = ""
        while ".\n" not in buf:
            buf += sock.recv(8192)

        info = {}
        for l in buf.split('\n'):
            l = l.strip()
            if l == '.':
                break
            counts = l.split('\t')
            info[counts[0]] = dict(
                total = int(counts[1]),
                running = int(counts[2]),
                workers = int(counts[3]),
            )
        return info

########NEW FILE########
__FILENAME__ = memcached
#!/usr/bin/env python

import os
import socket
from munin import MuninPlugin

class MuninMemcachedPlugin(MuninPlugin):
    category = "Memcached"

    def autoconf(self):
        try:
            self.get_stats()
        except socket.error:
            return False
        return True

    def get_stats(self):
        host = os.environ.get('MEMCACHED_HOST') or '127.0.0.1'
        port = int(os.environ.get('MEMCACHED_PORT') or '11211')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.send("stats\n")
        buf = ""
        while 'END\r\n' not in buf:
            buf += s.recv(1024)
        stats = (x.split(' ', 2) for x in buf.split('\r\n'))
        stats = dict((x[1], x[2]) for x in stats if x[0] == 'STAT')
        s.close()
        return stats

    def execute(self):
        stats = self.get_stats()
        values = {}
        for k, v in self.fields:
            try:
                value = stats[k]
            except KeyError:
                value = "U"
            values[k] = value
        return values

########NEW FILE########
__FILENAME__ = mongodb
#!/usr/bin/env python

import os
import sys
from munin import MuninPlugin

class MuninMongoDBPlugin(MuninPlugin):
    dbname_in_args = False
    category = "MongoDB"

    def __init__(self):
        super(MuninMongoDBPlugin, self).__init__()

        self.dbname = None
        if self.dbname_in_args:
            self.dbname = sys.argv[0].rsplit('_', 1)[-1]
        if not self.dbname:
            self.dbname = os.environ.get('MONGODB_DATABASE')

        host = os.environ.get('MONGODB_SERVER') or 'localhost'
        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        else:
            port = 27017
        self.server = (host, port)

    @property
    def connection(self):
        if not hasattr(self, '_connection'):
            import pymongo
            self._connection = pymongo.Connection(self.server[0], self.server[1], slave_okay=True)
        return self._connection

    @property
    def db(self):
        if not hasattr(self, '_db'):
            self._db = getattr(self.connection, self.dbname)
        return self._db

    def autoconf(self):
        return bool(self.connection)

########NEW FILE########
__FILENAME__ = mysql

import os, sys, re
from ConfigParser import SafeConfigParser
from munin import MuninPlugin

class MuninMySQLPlugin(MuninPlugin):
    dbname_in_args = False
    category = "MySQL"

    def __init__(self):
        super(MuninMySQLPlugin, self).__init__()

        self.dbname = ((sys.argv[0].rsplit('_', 1)[-1] if self.dbname_in_args else None)
            or os.environ.get('DATABASE') or self.default_table)

        self.conninfo = dict(
            user = "root",
            host = "localhost",
        )

        cnfpath = ""

        m = re.findall(r"--defaults-file=([^\s]+)", os.environ.get("mysqlopts") or "")
        if m:
            cnfpath = m[0]

        if not cnfpath:
            m = re.findall(r"mysql_read_default_file=([^\s;:]+)", os.environ.get("mysqlconnection") or "")
            if m:
                cnfpath = m[0]

        if cnfpath:
            cnf = SafeConfigParser()
            cnf.read([cnfpath])
            for section in ["client", "munin"]:
                if not cnf.has_section(section):
                    continue
                for connkey, opt in [("user", "user"), ("passwd", "password"), ("host", "host"), ("port", "port")]:
                    if cnf.has_option(section, opt):
                        self.conninfo[connkey] = cnf.get(section, opt)

        for k in ('user', 'passwd', 'host', 'port'):
            # Use lowercase because that's what the existing mysql plugins do
            v = os.environ.get(k)
            if v:
                self.conninfo[k] = v

    def connection(self):
        if not hasattr(self, '_connection'):
            import MySQLdb
            self._connection = MySQLdb.connect(**self.conninfo)
        return self._connection

    def cursor(self):
        return self.connection().cursor()

    def autoconf(self):
        return bool(self.connection())

########NEW FILE########
__FILENAME__ = nginx
#!/usr/bin/env python

import os
import re
import urllib
from munin import MuninPlugin

class MuninNginxPlugin(MuninPlugin):
    category = "Nginx"

    status_re = re.compile(
        r"Active connections:\s+(?P<active>\d+)\s+"
        r"server accepts handled requests\s+"
        r"(?P<accepted>\d+)\s+(?P<handled>\d+)\s+(?P<requests>\d+)\s+"
        r"Reading: (?P<reading>\d+) Writing: (?P<writing>\d+) Waiting: (?P<waiting>\d+)")

    def __init__(self):
        super(MuninNginxPlugin, self).__init__()
        self.url = os.environ.get('NX_STATUS_URL') or "http://localhost/nginx_status"

    def autoconf(self):
        return bool(self.get_status())

    def get_status(self):
        return self.status_re.search(urllib.urlopen(self.url).read()).groupdict()

########NEW FILE########
__FILENAME__ = pgbouncer
import sys
from munin.postgres import MuninPostgresPlugin

class MuninPgBouncerPlugin(MuninPostgresPlugin):
    dbname_in_args = False
    default_table = "pgbouncer"
    category = "PgBouncer"

    def __init__(self, *args, **kwargs):
        super(MuninPgBouncerPlugin, self).__init__(*args, **kwargs)
        self.dbwatched = sys.argv[0].rsplit('_', 1)[-1]

    def connection(self):
        if not hasattr(self, '_connection'):
            import psycopg2
            self._connection = psycopg2.connect(self.dsn)
            self._connection.set_isolation_level(0)
        return self._connection

    def execute(self):
        cursor = self.cursor()
        cursor.execute(self.command)
        columns = [column[0] for column in cursor.description]

        totals = dict.fromkeys((field[0] for field in self.fields), 0)
        for row in cursor:
            row_dict = dict(zip(columns, row))
            if row_dict['database'] in (self.dbwatched, self.dbwatched + '\x00'):
                for field in self.fields:
                    totals[field[0]] += row_dict[field[0]]

        return dict((field[0], totals[field[0]]) for field in self.fields)


########NEW FILE########
__FILENAME__ = postgres

import os, sys
from munin import MuninPlugin

class MuninPostgresPlugin(MuninPlugin):
    dbname_in_args = False
    category = "PostgreSQL"
    default_table = "template1"

    def __init__(self):
        super(MuninPostgresPlugin, self).__init__()

        self.dbname = ((sys.argv[0].rsplit('_', 1)[-1] if self.dbname_in_args else None)
            or os.environ.get('PGDATABASE') or self.default_table)
        dsn = ["dbname='%s'" % self.dbname]
        for k in ('user', 'password', 'host', 'port'):
            v = os.environ.get('DB%s' % k.upper())
            if v:
                dsn.append("db%s='%s'" % (k, v))
        self.dsn = ' '.join(dsn)

    def connection(self):
        if not hasattr(self, '_connection'):
            import psycopg2
            self._connection = psycopg2.connect(self.dsn)
        return self._connection

    def cursor(self):
        return self.connection().cursor()

    def autoconf(self):
        return bool(self.connection())

    def tables(self):
        if not hasattr(self, '_tables'):
            c = self.cursor()
            c.execute(
                "SELECT c.relname FROM pg_catalog.pg_class c"
                " LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace"
                " WHERE c.relkind IN ('r','')"
                "  AND n.nspname NOT IN ('pg_catalog', 'pg_toast')"
                "  AND pg_catalog.pg_table_is_visible(c.oid)")
            self._tables = [r[0] for r in c.fetchall()]
        return self._tables

########NEW FILE########
__FILENAME__ = redis
#!/usr/bin/env python

import os
import socket
from munin import MuninPlugin

class MuninRedisPlugin(MuninPlugin):
    category = "Redis"

    def autoconf(self):
        try:
            self.get_info()
        except socket.error:
            return False
        return True

    def get_info(self):
        host = os.environ.get('REDIS_HOST') or '127.0.0.1'
        port = int(os.environ.get('REDIS_PORT') or '6379')
        if host.startswith('/'):
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(host)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
        s.send("*1\r\n$4\r\ninfo\r\n")
        buf = ""
        while '\r\n' not in buf:
            buf += s.recv(1024)
        l, buf = buf.split('\r\n', 1)
        if l[0] != "$":
            s.close()
            raise Exception("Protocol error")
        remaining = int(l[1:]) - len(buf)
        if remaining > 0:
            buf += s.recv(remaining)
        s.close()
        return dict(x.split(':', 1) for x in buf.split('\r\n') if ':' in x)

    def execute(self):
        stats = self.get_info()
        values = {}
        for k, v in self.fields:
            try:
                value = stats[k]
            except KeyError:
                value = "U"
            values[k] = value
        return values

########NEW FILE########
__FILENAME__ = riak
#!/usr/bin/env python

try:
    import json
except ImportError:
    import simplejson as json
import os
import sys
import urllib2
from munin import MuninPlugin

class MuninRiakPlugin(MuninPlugin):
    category = "Riak"

    def __init__(self):
        super(MuninRiakPlugin, self).__init__()

        host = os.environ.get('RIAK_HOST') or 'localhost'
        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        else:
            port = 8098
        self.host = "%s:%s" % (host, port)

    def get_status(self):
        res = urllib2.urlopen("http://%s/stats" % (self.host))
        return json.loads(res.read())

########NEW FILE########
