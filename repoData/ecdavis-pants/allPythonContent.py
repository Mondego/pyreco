__FILENAME__ = pants_dig
#!/usr/bin/env python
###############################################################################
#
# Copyright 2011 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import optparse
import sys

from pants.util.dns import *

###############################################################################
# Main
###############################################################################

if __name__ == '__main__':
    usage = "usage: %prog [options] name [qtype]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--debug", dest="debug", action="store_true", default=False,
                help="Show extra messages.")
    parser.add_option("--servers", dest="list", action="store_true", default=False,
                help="List the discovered DNS servers.")
    parser.add_option("--hosts", dest="lh", action="store_true", default=False,
                help="List the entries loaded from the OS hosts file.")

    options, args = parser.parse_args()

    if options.debug:
        logging.getLogger('').setLevel(logging.DEBUG)
        logging.info('...')

    if options.list:
        print ''
        print 'Available DNS Servers'
        for i in list_dns_servers():
            print ' %s' % i

    if options.lh:
        print ''
        print 'Using: %s' % host_path

        print ''
        print 'Detected IPv4 Hosts'
        for k,v in hosts[A].iteritems():
            print ' %-40s A     %s' % (k, v)

        print ''
        print 'Detected IPv6 Hosts'
        for k,v in hosts[AAAA].iteritems():
            print ' %-40s AAAA  %s' % (k, v)

    if sys.platform == 'win32':
        timer = time.clock
    else:
        timer = time.time

    args = list(args)
    while args:
        host = args.pop(0)
        if args:
            qt = args.pop(0)
        else:
            qt = 'A'
        
        qtype = []
        for t in qt.split(','):
            t = t.upper()
            if t in QTYPES:
                t = QTYPES.index(t) + 1
            else:
                try:
                    t = int(t)
                except ValueError:
                    print 'Invalid QTYPE, %r.' % t
                    sys.exit(1)
            qtype.append(t)
        qtype = tuple(qtype)

        # Build a Message
        m = DNSMessage()
        
        for t in qtype:
            m.questions.append((host, t, IN))

        print ''

        # Query it.
        start = timer()
        status, data = sync.send_message(m)
        end = timer()

        if data and data.rcode != DNS_OK:
            status = data.rcode

        if qtype == A and host in hosts[A]:
            print "A record for %r in hosts: %s" % (host, hosts[A][host])
            print ""
        elif qtype == AAAA and host in hosts[AAAA]:
            print "AAAA record for %r in hosts: %s" % (host, hosts[AAAA][host])
            print ""

        if status == DNS_OK:
            print "Response: DNS_OK (%d)" % status
        elif status == DNS_TIMEOUT:
            print "Response: DNS_TIMEOUT (%d)" % status
        elif status == DNS_FORMATERROR:
            print "Response: DNS_FORMATERROR (%d)" % status
        elif status == DNS_SERVERFAILURE:
            print "Response: DNS_SERVERFAILURE (%d)" % status
        elif status == DNS_NAMEERROR:
            print "Response: DNS_NAMEERROR (%d)" % status
        elif status == DNS_NOTIMPLEMENTED:
            print "Response: DNS_NOTIMPLEMENTED (%d)" % status
        elif status == DNS_REFUSED:
            print "Response: DNS_REFUSED (%d)" % status
        else:
            print "Response: UNKNOWN (%d)" % status

        if not data:
            if status == DNS_OK:
                print "Empty response, but OK status? Something's wrong."
            else:
                print "Empty response."
            continue

        opcode = 'UNKNOWN (%d)' % data.opcode
        if data.opcode == OP_QUERY:
            opcode = 'QUERY'
        elif data.opcode == OP_IQUERY:
            opcode = 'IQUERY'
        elif data.opcode == OP_STATUS:
            opcode = 'STATUS'

        rcode = data.rcode
        if rcode == 0:
            rcode = 'OK'
        elif rcode == 1:
            rcode = 'Format Error'
        elif rcode == 2:
            rcode = 'Server Failure'
        elif rcode == 3:
            rcode = 'Name Error'
        elif rcode == 4:
            rcode = 'Not Implemented'
        elif rcode == 5:
            rcode = 'Refused'
        else:
            rcode = 'Unknown (%d)' % rcode

        flags = []
        if data.qr: flags.append('qr')
        if data.aa: flags.append('aa')
        if data.tc: flags.append('tc')
        if data.rd: flags.append('rd')
        if data.ra: flags.append('ra')

        print 'opcode: %s; rcode: %s; id: %d; flags: %s' % (opcode, rcode, data.id, ' '.join(flags))
        print 'queries: %d; answers: %d; authorities: %d; additional: %d' % (len(data.questions), len(data.answers), len(data.authrecords), len(data.additional))

        print ''
        print 'Question Section'
        for name, qtype, qclass in data.questions:
            if qtype < len(QTYPES):
                qtype = QTYPES[qtype-1]
            else:
                qtype = str(qtype)

            if qclass == IN:
                qclass = 'IN'
            else:
                qclass = str(qclass)

            print ' %-31s %-5s %s' % (name, qclass, qtype)

        for lbl,lst in (('Answer', data.answers), ('Authority', data.authrecords), ('Additional', data.additional)):
            if not lst:
                continue
            print ''
            print '%s Section' % lbl
            for name, atype, aclass, ttl, rdata in lst:
                if atype < len(QTYPES):
                    atype = QTYPES[atype-1]
                else:
                    atype = str(atype)

                if aclass == IN:
                    aclass = 'IN'
                else:
                    aclass = str(aclass)

                print ' %-22s %-8d %-5s %-8s %s' % (name, ttl, aclass, atype, ' '.join(str(x) for x in rdata))

        print ''
        print 'Query Time: %d msec' % int((end - start) * 1000)
        print 'Server: %s' % str(data.server)
        print 'Message Size: %d' % len(str(data))

    print ''
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Pants documentation build configuration file, created by
# sphinx-quickstart on Sat Apr 30 23:31:07 2011.
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
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx'
    ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Pants'
copyright = u'2011-2013, Pants Developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0.1'

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
exclude_patterns = ['_build', 'doc']

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

# Links to other projects using Sphinx so that we can reference them.
intersphinx_mapping = {
    'python': ('http://docs.python.org/2.7/', None),
    'pyside': ('http://srinikom.github.com/pyside-docs/', None),
    }


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ["_themes"]

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = "Pants"

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = "_static/logo.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = "_static/favicon.ico"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%B %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Pantsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Pants.tex', u'Pants Documentation',
   u'Christopher Davis', 'manual'),
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
    ('index', 'pants', u'Pants Documentation',
     [u'Pants Developers'], 1)
]

# Mockup PySide
try:
    import PySide
except ImportError:
    class Mock(object):
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            return Mock()

        @classmethod
        def __getattr__(self, name):
            if name in ('__file__', '__path__'):
                return '/dev/null'
            elif name[:2] != '__' and name[0] == name[0].upper():
                return type(name, (Mock,), {})
            else:
                return Mock()

    MOCK_MODULES = ['PySide', 'PySide.QtCore']
    for mod_name in MOCK_MODULES:
        sys.modules[mod_name] = Mock()

# Install a shiny __repr__ on the Engine.

from pants.engine import Engine
Engine.__repr__ = lambda s: "Engine.instance()"

########NEW FILE########
__FILENAME__ = echo
from pants import Engine, Server, Stream

class Echo(Stream):
    def on_read(self, data):
        self.write(data)

Server(Echo).listen(4040)
Engine.instance().start()

########NEW FILE########
__FILENAME__ = hello_web
from pants.web import Application

app = Application()

@app.route('/')
def hello(request):
    return "Hello, World!"

app.run()

########NEW FILE########
__FILENAME__ = tutorial1
from pants import Engine, Server, Stream

class Echo(Stream):
    def on_read(self, data):
        self.write(data)

server = Server(ConnectionClass=Echo)
server.listen(4040)
Engine.instance().start()

########NEW FILE########
__FILENAME__ = tutorial2
from pants import Engine, Server, Stream

class BlockEcho(Stream):
    def on_connect(self):
        self.read_delimiter = 8

    def on_read(self, block):
        self.write(block + '\r\n')

server = Server(ConnectionClass=BlockEcho)
server.listen(4040)
Engine.instance().start()

########NEW FILE########
__FILENAME__ = tutorial3
from pants import Engine, Server, Stream

class EchoLineToAll(Stream):
    def on_connect(self):
        self.read_delimiter = '\r\n'
        self.server.write_to_all("Connected: %s\r\n" % self.remote_address[0])

    def on_read(self, line):
        self.server.write_to_all("%s: %s\r\n" % (self.remote_address[0], line))

    def on_close(self):
        self.server.write_to_all("Disconnected: %s\r\n" % self.remote_address[0])

class EchoLineToAllServer(Server):
    ConnectionClass = EchoLineToAll

    def write_to_all(self, data):
        for channel in self.channels.itervalues():
            if channel.connected:
                channel.write(data)

EchoLineToAllServer().listen(4040)
Engine.instance().start()

########NEW FILE########
__FILENAME__ = irc
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import logging
import re

from pants.stream import Stream

###############################################################################
# Logging
###############################################################################

log = logging.getLogger(__name__)

###############################################################################
# Constants
###############################################################################

__all__ = ('BaseIRC','IRCClient')

COMMAND = re.compile(r"((?::.+? )?)(.+?) (.*)")
NETMASK = re.compile(
    r":(?:(?:([^!\s]+)!)?([^@\s]+)@)?([A-Za-z0-9-/:?`[_^{|}\\\]\.]+)")
ARGS    = re.compile(r"(?:^|(?<= ))(:.*|[^ ]+)")
CTCP    = re.compile(r"([\x00\n\r\x10])")
unCTCP  = re.compile(r"\x10([0nr\x10])")

CODECS  = ('utf-8','iso-8859-1','cp1252')
#])" # this is here to correct syntax highlighting in textmate... remove it!!!

###############################################################################
# BaseIRC Class
###############################################################################

class BaseIRC(Stream):
    """
    The IRC protocol, implemented over a Pants :class:`~pants.stream.Stream`.

    The goal with this is to create a lightweight IRC class that can serve as
    either a server or a client. As such, it doesn't implement a lot of logic
    in favor of providing a robust base.

    The BaseIRC class can receive and send IRC commands, and automatically
    respond to certain commands such as PING.

    This class extends :class:`~pants.stream.Stream`, and as such has the same
    :func:`~pants.stream.Stream.connect` and :func:`~pants.stream.Stream.listen`
    functions.
    """
    def __init__(self, encoding='utf-8', **kwargs):
        Stream.__init__(self, **kwargs)

        # Set our prefix to an empty string. This is prepended to all sent
        # commands, and useful for servers.
        self.prefix = ''
        self.encoding = encoding

        # Read lines at once.
        self.read_delimiter = '\n'

    ##### Public Event Handlers ###############################################

    def irc_close(self):
        """
        Placeholder.

        This method is called whenever the IRC instance becomes disconnected
        from the remote client or server.
        """
        pass

    def irc_command(self, command, args, nick, user, host):
        """
        Placeholder.

        This method is called whenever a command is received from the other
        side and successfully parsed as an IRC command.

        =========  ============
        Argument   Description
        =========  ============
        command    The received command.
        args       A list of the arguments following the command.
        nick       The nick of the user that sent the command, if applicable, or an empty string.
        user       The username of the user that sent the command, if applicable, or an empty string.
        host       The host of the user that sent the command, the host of the server that sent the command, or an empty string if no host was supplied.
        =========  ============
        """
        pass

    def irc_connect(self):
        """
        Placeholder.

        This method is called when the IRC instance has successfully connected
        to the remote client or server.
        """
        pass

    ##### I/O Methods #########################################################

    def message(self, destination, message, _ctcpQuote=True, _prefix=None):
        """
        Send a message to the given nick or channel.

        ============  ========  ============
        Argument      Default   Description
        ============  ========  ============
        destination             The nick or channel to send the message to.
        message                 The text of the message to be sent.
        _ctcpQuote    True      *Optional.* If True, the message text will be quoted for CTCP before being sent.
        _prefix       None      *Optional.* A string that, if provided, will be prepended to the command string before it's sent to the server.
        ============  ========  ============
        """
        if _ctcpQuote:
            message = ctcpQuote(message)

        self.send_command("PRIVMSG", destination, message, _prefix=_prefix)

    def notice(self, destination, message, _ctcpQuote=True, _prefix=None):
        """
        Send a NOTICE to the specified destination.

        ===========  ========  ============
        Argument     Default   Description
        ===========  ========  ============
        destination            The nick or channel to send the NOTICE to.
        message                The text of the NOTICE to be sent.
        _ctcpQuote   True      *Optional.* If True, the message text will be quoted for CTCP before being sent.
        _prefix      None      *Optional.* A string that, if provided, will be prepended to the command string before it's sent to the server.
        ===========  ========  ============
        """
        if _ctcpQuote:
            message = ctcpQuote(message)

        self.send_command("NOTICE", destination, message, _prefix=_prefix)

    def quit(self, reason=None, _prefix=None):
        """
        Send a QUIT message, with an optional reason.

        =========  ========  ============
        Argument   Default   Description
        =========  ========  ============
        reason     None      *Optional.* The reason for quitting that will be displayed to other users.
        _prefix    None      *Optional.* A string that, if provided, will be prepended to the command string before it's sent to the server.
        =========  ========  ============
        """
        if not reason:
            reason = "pants.contrib.irc -- http://www.pantsweb.org/"
        self.send_command("QUIT", reason, _prefix=_prefix)

    def send_command(self, command, *args, **kwargs):
        """
        Send a command to the remote endpoint.

        =========  ========  ============
        Argument   Default   Description
        =========  ========  ============
        command              The command to send.
        \*args                *Optional.* A list of arguments to send with the command.
        _prefix    None      *Optional.* A string that, if provided, will be prepended to the command string before it's sent to the server.
        =========  ========  ============
        """
        if args:
            args = list(args)
            for i in xrange(len(args)):
                arg = args[i]
                if not isinstance(arg, basestring):
                    args[i] = str(arg)

            if not args[-1].startswith(':'):
                args[-1] = ':%s' % args[-1]

            out = '%s %s\r\n' % (command, ' '.join(args))
        else:
            out = '%s\r\n' % command

        if '_prefix' in kwargs and kwargs['_prefix']:
            out = '%s %s' % (kwargs['_prefix'], out)
        elif self.prefix:
            out = '%s %s' % (self.prefix, out)

        # Send it.
        log.debug('\x1B[0;32m>> %s\x1B[0m' % out.rstrip())

        self.write(out.encode(self.encoding))

    ##### Internal Event Handlers #############################################

    def on_command(self, command, args, nick, user, host):
        """
        Placeholder.

        Performs any logic that has to be performed upon receiving a command,
        then calls irc_command.

        Arguments are identical to irc_command.
        """
        if hasattr(self, 'irc_command_%s' % command):
            getattr(self, 'irc_command_%s' % command)(
                command, args, nick, user, host)
        else:
            self.irc_command(command, args, nick, user, host)

    def on_connect(self):
        """
        Placeholder.

        Performs any logic that has to be performed at connect, then calls
        self.irc_connect.
        """
        self.irc_connect()

    def on_close(self):
        """
        Placeholder.

        Performs any logic that has to be performed at disconnect, then calls
        self.irc_close.
        """
        self.irc_close()

    def on_read(self, data):
        """
        Read the available data, parse the command, and call an event for it.
        """
        data = data.strip('\r\n')
        if not data:
            return

        log.debug('\x1B[0;31m<< %s\x1B[0m' % repr(data)[1:-1])

        # Decode it straight away.
        data = decode(data)

        try:
            prefix, command, raw = COMMAND.match(data).groups()
        except Exception:
            log.warning('Invalid IRC command %r.' % data)
            return

        if prefix:
            nick, user, host = NETMASK.match(prefix).groups()
            if not nick and not '.' in host:
                nick = host
                host = ''
        else:
            nick, user, host = '', '', ''

        args = ARGS.findall(raw)
        if args:
            if args[-1].startswith(':'):
                args[-1] = args[-1][1:]

        # If it's PING, handle it.
        if command == 'PING':
            self.send_command('PONG', *args)
            return

        # Handle the command.
        self.on_command(command, args, nick, user, host)

###############################################################################
# IRCClient Class & Channel Class
###############################################################################

class Channel(object):
    """
    An IRC channel's representation, for keeping track of users and the topic
    and stuff.
    """
    __slots__ = ('name', 'users','topic','topic_setter','topic_time')

    def __init__(self, name):
        self.name = name
        self.users = []
        self.topic = None
        self.topic_setter = None
        self.topic_time = 0

class IRCClient(BaseIRC):
    """
    An IRC client, written in Pants, based on :class:`~pants.contrib.irc.BaseIRC`.

    This implements rather more logic, and keeps track of what server it's
    connected to, its nick, and what channels it's in.
    """
    def __init__(self, encoding='utf-8', **kwargs):
        BaseIRC.__init__(self, encoding=encoding, **kwargs)

        # Internal State Stuff
        self._channels  = {}
        self._joining   = []

        self._nick      = None
        self._port      = 6667
        self._server    = None
        self._user      = None
        self._realname  = None

        # External Stuff
        self.password   = None

    ##### Properties ##########################################################

    @property
    def nick(self):
        """
        This instance's current nickname on the server it's connected to, or
        the nickname it will attempt to acquire when connecting.
        """
        return self._nick

    @nick.setter
    def nick(self, val):
        if not self.connected:
            self._nick = val
        else:
            self.send_command("NICK", val)

    @property
    def port(self):
        """
        The port this instance is connected to on the remote server, or the
        port it will attempt to connect to.
        """
        return self._port

    @port.setter
    def port(self, val):
        if self.connected or self.connecting:
            raise IOError('Cannot change while connected to server.')
        self._port = val

    @property
    def realname(self):
        """
        The real name this instance will report to the server when connecting.
        """
        return self._realname

    @realname.setter
    def realname(self, val):
        if self.connected or self.connecting:
            raise IOError('Cannot change while connected to server.')
        self._realname = val

    @property
    def server(self):
        """
        The server this instance is connected to, or will attempt to connect to.
        """
        return self._server

    @server.setter
    def server(self, val):
        if self.connected or self.connecting:
            raise IOError('Cannot change while connected to server.')
        self._server = val

    @property
    def user(self):
        """
        The user name this instance will report to the server when connecting.
        """
        return self._user

    @user.setter
    def user(self, val):
        if self.connected or self.connecting:
            raise IOError('Cannot change while connected to server.')
        self._user = val

    ##### General Methods #####################################################

    def channel(self, name):
        """
        Retrieve a Channel object for the channel ``name``, or None if we're
        not in that channel.
        """
        return self._channels.get(name, None)

    def connect(self, server=None, port=None):
        """
        Connect to the server.

        =========  ============
        Argument   Description
        =========  ============
        server     The host to connect to.
        port       The port to connect to on the remote server.
        =========  ============
        """
        if not self.connected and not self.connecting:
            if server:
                self._server = server
            if port:
                self._port = port


        Stream.connect(self, (self._server, self._port))

    ##### I/O Methods #########################################################

    def join(self, channel):
        """
        Join the specified channel.

        =========  ============
        Argument   Description
        =========  ============
        channel    The name of the channel to join.
        =========  ============
        """
        if channel in self._channels or channel in self._joining:
            return

        self._joining.append(channel)
        self.send_command("JOIN", channel)

    def part(self, channel, reason=None, force=False):
        """
        Leave the specified channel.

        =========  ========  ============
        Argument   Default   Description
        =========  ========  ============
        channel              The channel to leave.
        reason     None      *Optional.* The reason why.
        force      False     *Optional.* Don't ensure the client is actually *in* the named channel before sending ``PART``.
        =========  ========  ============
        """
        if not force and not channel in self._channels:
            return

        args = [channel]
        if reason:
            args.append(reason)

        self.send_command("PART", *args)

    ##### Public Event Handlers ###############################################

    def irc_ctcp(self, nick, message, user, host):
        """
        Placeholder.

        This method is called when the bot receives a CTCP message, which
        could, in theory, be anywhere in a PRIVMSG... annoyingly enough.

        =========  ============
        Argument   Description
        =========  ============
        nick       The nick of the user that sent the CTCP message, or an empty string if no nick is available.
        message    The full CTCP message.
        user       The username of the user that sent the CTCP message, or an empty string if no username is available.
        host       The host of the user that sent the CTCP message, or an empty string if no host is available.
        =========  ============
        """
        pass

    def irc_join(self, channel, nick, user, host):
        """
        Placeholder.

        This method is called when a user enters a channel. That also means
        that this function is called whenever this IRC client successfully
        joins a channel.

        =========  ============
        Argument   Description
        =========  ============
        channel    The channel a user has joined.
        nick       The nick of the user that joined the channel.
        user       The username of the user that joined the channel.
        host       The host of the user that joined the channel.
        =========  ============
        """
        pass

    def irc_message_channel(self, channel, message, nick, user, host):
        """
        Placeholder.

        This method is called when the client receives a message from a channel.

        =========  ============
        Argument   Description
        =========  ============
        channel    The channel the message was received in.
        message    The text of the message.
        nick       The nick of the user that sent the message.
        user       The username of the user that sent the message.
        host       The host of the user that sent the message.
        =========  ============
        """
        pass

    def irc_message_private(self, nick, message, user, host):
        """
        Placeholder.

        This method is called when the client receives a message from a user.

        =========  ============
        Argument   Description
        =========  ============
        nick       The nick of the user that sent the message.
        message    The text of the message.
        user       The username of the user that sent the message.
        host       The host of the user that sent the message.
        =========  ============
        """
        pass

    def irc_nick_changed(self, nick):
        """
        Placeholder.

        This method is called when the client's nick on the network is changed
        for any reason.

        =========  ============
        Argument   Description
        =========  ============
        nick       The client's new nick.
        =========  ============
        """
        pass

    def irc_part(self, channel, reason, nick, user, host):
        """
        Placeholder.

        This method is called when a leaves enters a channel. That also means
        that this function is called whenever this IRC client leaves a
        channel.

        =========  ============
        Argument   Description
        =========  ============
        channel    The channel that the user has left.
        reason     The provided reason message, or an empty string if there is no message.
        nick       The nick of the user that left the channel.
        user       The username of the user that left the channel.
        host       The host of the user that left the channel.
        =========  ============
        """
        pass

    def irc_topic_changed(self, channel, topic):
        """
        Placeholder.

        This method is called when the topic of a channel changes.

        =========  ============
        Argument   Description
        =========  ============
        channel    The channel which had its topic changed.
        topic      The channel's new topic.
        =========  ============
        """
        pass

    ##### IRC Command Handlers ################################################

    def irc_command_004(self, command, args, nick, user, host):
        """ 004 - Registered
            Syntax:
                004 server ver usermode chanmode

            The 004 command is sent once we've registered successfully with the
            server and can proceed to do normal IRC things.
        """
        # Check our nick.
        n = args[0]
        if n != self._nick:
            self._nick = n
            self.irc_nick_changed(n)

        self.irc_connect()

    def irc_command_332(self, command, args, nick, user, host):
        """ 332 - Channel Topic
            Syntax:
                332 channel :topic
        """
        chan, topic = args[-2:]
        if chan in self._channels:
            self._channels[chan].topic = topic

        self.irc_topic_changed(chan, topic)

    def irc_command_333(self, command, args, nick, user, host):
        """ 333 - Channel Topic (Extended)
            Syntax:
                333 channel nickname time
        """
        chan, nickname, time = args[-3:]
        if chan in self._channels:
            self._channels[chan].topic_setter = nickname
            try:
                self._channels[chan].topic_time = int(time)
            except ValueError:
                pass

    def irc_command_353(self, command, args, nick, user, host):
        """ 353 - Users in Channel
            Syntax:
                353 = channel: names
        """
        chan, names = args[-2:]
        if chan in self._channels:
            for name in names.split(' '):
                while name[0] in '@+':
                    name = name[1:]
                if not name in self._channels[chan].users:
                    self._channels[chan].users.append(name)

    def irc_command_JOIN(self, command, args, nick, user, host):
        """
        Received whenever a user, including ourself, joins a channel.
        """
        chan = args[0]

        if nick == self._nick:
            if chan in self._joining:
                self._joining.remove(chan)
            if not chan in self._channels:
                self._channels[chan] = Channel(chan)

        if chan in self._channels:
            name = nick
            while name[0] in '@+':
                name = name[1:]
            if not name in self._channels[chan].users:
                self._channels[chan].users.append(name)

        self.irc_join(chan, nick, user, host)

    def irc_command_PART(self, command, args, nick, user, host):
        """
        Received whenever a user, including ourself, leaves a channel.
        """
        chan = args[0]

        if nick == self._nick:
            if chan in self._joining:
                self._joining.remove(chan)
            if chan in self._channels:
                del self._channels[chan]

        if chan in self._channels:
            name = nick
            while name[0] in '@+':
                name = name[1:]
            if name in self._channels[chan].users:
                self._channels[chan].users.remove(name)

        if len(args) < 2:
            args.append('')

        self.irc_part(chan, args[1], nick, user, host)

    def irc_command_PRIVMSG(self, command, args, nick, user, host):
        """
        The PRIVMSG command is the heart of IRC communications. This method
        will call either irc_message_channel, or irc_message_private depending
        on the recipient of the privmsg.
        """
        msg = args[1]
        while msg:
            ind = msg.find('\x01')
            if ind == -1:
                ind = len(msg)

            if ind > 0:
                message = msg[:ind]
                msg = msg[ind:]

                if args[0] == self._nick:
                    self.irc_message_private(nick, message, user, host)
                else:
                    self.irc_message_channel(
                        args[0], message, nick, user, host)

            if msg:
                msg = msg[1:]
                ind = msg.find('\x01')
                if ind == -1:
                    continue

                message = msg[:ind]
                msg = msg[ind+1:]

                self.irc_ctcp(nick, message, user, host)

    ##### Internal Event Handlers #############################################

    def on_connect(self):
        """
        We're connected, so send the login stuff.
        """
        if self.password:
            self.send_command("PASS", self.password)

        self.send_command("NICK", self._nick or 'PantsIRC')

        # Our user and realname.
        self.send_command("USER",
            self._user or 'PantsIRC',
            0, '*',
            self._realname or 'pants.contrib.irc'
        )

        # And now, we wait. Don't raise irc_connect until we get a message
        # letting us know our connection was accepted.

    def on_close(self):
        """
        We've been disconnected.
        """
        self._channels  = {}
        self._joining   = []

        self.irc_close()

###############################################################################
# Helper Functions
###############################################################################

def ctcpQuote(message):
    """
    Low-level quote a message, adhering to the CTCP guidelines.
    """
    return CTCP.sub(_ctcpQuoter, message)

def _ctcpQuoter(match):
    m = match.group(1)
    if m == '\x00':
        return '\x100'
    elif m == '\n':
        return '\x10n'
    elif m == '\r':
        return '\x10r'
    elif m == '\x10':
        return '\x10\x10'
    else:
        return m

def ctcpUnquote(message):
    """
    Low-level unquote a message, adhering to the CTCP guidelines.
    """
    return unCTCP.sub(_ctcpUnquoter, message)

def _ctcpUnquoter(match):
    m = match.group(1)
    if m == '0':
        return '\x00'
    elif m == 'n':
        return '\n'
    elif m == 'r':
        return '\r'
    elif m == '\x10':
        return '\x10'
    else:
        return m

def decode(data):
    for codec in CODECS:
        try:
            return data.decode(codec)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', 'ignore')

########NEW FILE########
__FILENAME__ = qt
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

from pants.engine import Engine

try:
    from PySide.QtCore import QCoreApplication, QSocketNotifier, QTimer
except ImportError:
    from PyQt.QtCore import QCoreApplication, QSocketNotifier, QTimer

###############################################################################
# _Qt Class
###############################################################################

class _Qt(object):
    """
    A QSocketNotifier-based polling object.

    This caches events, waiting for the next call to poll, which should be
    called every loop by a QTimer.
    """
    def __init__(self):
        self._r = {}
        self._w = {}
        self._e = {}

        self._readable = set()
        self._writable = set()
        self._errored = set()

    def _read_event(self, fileno):
        self._readable.add(fileno)
        try:
            self._r[fileno].setEnabled(False)
        except KeyError:
            pass
        timer.setInterval(0)

    def _write_event(self, fileno):
        self._writable.add(fileno)
        try:
            self._w[fileno].setEnabled(False)
        except KeyError:
            pass
        timer.setInterval(0)

    def _error_event(self, fileno):
        self._errored.add(fileno)
        try:
            self._e[fileno].setEnabled(False)
        except KeyError:
            pass
        timer.setInterval(0)

    def add(self, fileno, events):
        if events & Engine.READ:
            self._r[fileno] = qs = QSocketNotifier(fileno,
                                        QSocketNotifier.Type.Read)
            qs.activated.connect(self._read_event)

        if events & Engine.WRITE:
            self._w[fileno] = qs = QSocketNotifier(fileno,
                                        QSocketNotifier.Type.Write)
            qs.activated.connect(self._write_event)

        if events & Engine.ERROR:
            self._e[fileno] = qs = QSocketNotifier(fileno,
                                        QSocketNotifier.Type.Exception)
            qs.activated.connect(self._error_event)

    def modify(self, fileno, events):
        if events & Engine.READ and not fileno in self._r:
            self._r[fileno] = qs = QSocketNotifier(fileno,
                                        QSocketNotifier.Type.Read)
            qs.activated.connect(self._read_event)

        elif not events & Engine.READ and fileno in self._r:
            self._r[fileno].setEnabled(False)
            del self._r[fileno]

        if events & Engine.WRITE and not fileno in self._w:
            self._w[fileno] = qs = QSocketNotifier(fileno,
                                        QSocketNotifier.Type.Write)
            qs.activated.connect(self._write_event)

        elif not events & Engine.WRITE and fileno in self._w:
            self._w[fileno].setEnabled(False)
            del self._w[fileno]

        if events & Engine.ERROR and not fileno in self._e:
            self._e[fileno] = qs = QSocketNotifier(fileno,
                                        QSocketNotifier.Type.Exception)
            qs.activated.connect(self._error_event)

        elif not events & Engine.ERROR and fileno in self._e:
            self._e[fileno].setEnabled(False)
            del self._e[fileno]

    def remove(self, fileno, events):
        if fileno in self._r:
            self._r[fileno].setEnabled(False)
            del self._r[fileno]
        if fileno in self._w:
            self._w[fileno].setEnabled(False)
            del self._w[fileno]
        if fileno in self._e:
            self._e[fileno].setEnabled(False)
            del self._e[fileno]

    def poll(self, timeout):
        events = {}

        for fileno in self._readable:
            events[fileno] = events.get(fileno, 0) | Engine.READ
            if fileno in self._r:
                self._r[fileno].setEnabled(True)

        for fileno in self._writable:
            events[fileno] = events.get(fileno, 0) | Engine.WRITE
            if fileno in self._w:
                self._w[fileno].setEnabled(True)

        for fileno in self._errored:
            events[fileno] = events.get(fileno, 0) | Engine.ERROR
            if fileno in self._e:
                self._e[fileno].setEnabled(True)

        self._readable.clear()
        self._writable.clear()
        self._errored.clear()

        return events

def do_poll():
    """
    Here, we run the Pants event loop. Then, we set the timer interval, either
    to the provided timeout, or for how long it would take to reach the
    earliest deferred event.
    """
    _engine.poll(0)

    if _engine._deferreds:
        timer.setInterval(min(1000 * (_engine._deferreds[0].end - _engine.latest_poll_time), _timeout))
    else:
        timer.setInterval(_timeout)

###############################################################################
# Installation Function
###############################################################################

timer = None
_timeout = 0.02
_engine = None

def install(app=None, timeout=0.02, engine=None):
    """
    Creates a :class:`~PySide.QtCore.QTimer` instance that will be triggered
    continuously to call :func:`Engine.poll() <pants.engine.Engine.poll>`,
    ensuring that Pants remains responsive.

    =========  ========  ============
    Argument   Default   Description
    =========  ========  ============
    app        None      *Optional.* The :class:`~PySide.QtCore.QCoreApplication` to attach to. If no application is provided, it will attempt to find an existing application in memory, or, failing that, create a new application instance.
    timeout    ``0.02``  *Optional.* The maximum time to wait, in seconds, before running :func:`Engine.poll() <pants.engine.Engine.poll>`.
    engine               *Optional.* The :class:`pants.engine.Engine` instance to use.
    =========  ========  ============
    """
    global timer
    global _timeout
    global _engine

    _engine = engine or Engine.instance()
    _engine._install_poller(_Qt())

    if app is None:
        app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])

    _timeout = timeout * 1000

    timer = QTimer(app)
    timer.timeout.connect(do_poll)
    timer.start(_timeout)

########NEW FILE########
__FILENAME__ = socks
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import socket
import struct

from pants.stream import Stream
import pants.util.dns


###############################################################################
# Constants
###############################################################################

SOCKS_VERSION = '\x05'


###############################################################################
# Exception Types
###############################################################################

class BadVersion(Exception):
    pass


class NoAuthenticationMethods(Exception):
    pass


class Unauthorized(Exception):
    pass


###############################################################################
# The Function
###############################################################################

def do_socks_handshake(self, addr, callback, error_callback=None, auth=None):
    """
    Perform a SOCKSv5 handshake, and call callback when it's completed. If
    authorization data is provided, we'll log onto the server too.

    ===============  ============
    Argument         Description
    ===============  ============
    addr             The address for the proxy server to connect to. This must be a tuple of ``(hostname, port)``.
    callback         A function to call when the handshake has completed.
    error_callback   *Optional.* A function to be called if the handshake has failed.
    auth             *Optional.* If provided, it must be a tuple of ``(username, password)``.
    ===============  ============
    """
    if not self.connected:
        raise RuntimeError("Tried to start SOCKS handshake on disconnected %r." % self)

    # Build our on_read.
    def on_read(data):
        if not self._socks_state:
            if data[0] != SOCKS_VERSION:
                if error_callback:
                    self._safely_call(error_callback,
                        BadVersion("Expected version 5, got %d." % ord(data[0])))
                self.close(False)
                return

            elif (auth and data[1] != '\x02') or (not auth and data[1] != '\x00'):
                if error_callback:
                    self._safely_call(error_callback,
                        NoAuthenticationMethods())
                self.close(False)
                return

            if auth:
                self.write("\x01%d%s%d%s" % (
                    len(auth[0]), auth[0], len(auth[1]), auth[1]))
                self._socks_state = 1

            else:
                self._socks_state = 1
                self.on_read("%s\x00" % SOCKS_VERSION)

        elif self._socks_state == 1:
            if data[0] != SOCKS_VERSION:
                if error_callback:
                    self._safely_call(error_callback,
                        BadVersion("Expected version 5, got %d." % ord(data[0])))
                self.close(False)
                return

            elif data[1] != '\x00':
                if error_callback:
                    self._safely_call(error_callback,
                        Unauthorized(data[1]))
                self.close(False)
                return

            self.write("%s\x01\x00\x03%s%s%s" % (
                SOCKS_VERSION,
                chr(len(addr[0])),
                addr[0],
                struct.pack('!H', addr[1])
                ))
            self._socks_state = 2
            self.read_delimiter = 4

        elif self._socks_state == 2:
            if data[0] != SOCKS_VERSION:
                if error_callback:
                    self._safely_call(error_callback,
                        BadVersion("Expected version 5, got %d." % ord(data[0])))
                self.close(False)
                return

            elif data[1] != '\x00':
                if error_callback:
                    self._safely_call(error_callback,
                        Exception(data[1]))
                self.close(False)
                return

            self._socks_state = 4
            if data[3] == '\x01':
                self._socks_fam = 1
                self.read_delimiter = 4
            elif data[3] == '\x03':
                self._socks_state = 3
                self.read_delimiter = 1
                self._socks_fam = 0
            elif data[3] == '\x04':
                self.read_delimiter = 16
                self._socks_fam = 2

            self._socks_port = struct.unpack("!H", data[-2:])

        elif self._socks_state == 3:
            if self.read_delimiter == 1:
                self._socks_state = 4
                self.read_delimiter = ord(data[0])

        elif self._socks_state == 4:
            if self._socks_fam == 1:
                data = socket.inet_ntop(socket.AF_INET, data)
            elif self._socks_fam == 2:
                try:
                    data = socket.inet_ntop(socket.AF_INET6, data)
                except (AttributeError, socket.error):
                    pass

            self.remote_address = (data, self._socks_port)

            # Cleanup!
            self.on_read = self._socks_read
            self.read_delimiter = self._socks_delim

            del self._socks_read
            del self._socks_delim
            del self._socks_port
            del self._socks_state
            del self._socks_fam

            self._safely_call(callback)

    # Start doing it!
    self._socks_state = 0
    self.write("%s\x01%s" % (
        SOCKS_VERSION, '\x02' if auth else '\x00'))

    self._socks_read = self.on_read
    self._socks_delim = self.read_delimiter
    self.on_read = on_read
    self.read_delimiter = 2

Stream.do_socks_handshake = do_socks_handshake

########NEW FILE########
__FILENAME__ = telnet
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import re
import struct

from pants import Stream, Server

try:
    from netstruct import NetStruct as _NetStruct
except ImportError:
    # Create the fake class because isinstance expects a class.
    class _NetStruct(object):
        def __init__(self, *a, **kw):
            raise NotImplementedError


###############################################################################
# Logging
###############################################################################

import logging
log = logging.getLogger(__name__)


###############################################################################
# Constants
###############################################################################

RegexType = type(re.compile(""))
Struct = struct.Struct

# Telnet commands
IAC  = chr(255)  # Interpret As Command
DONT = chr(254)  # Don't Perform
DO   = chr(253)  # Do Perform
WONT = chr(252)  # Won't Perform
WILL = chr(251)  # Will Perform
SB   = chr(250)  # Subnegotiation Begin
SE   = chr(240)  # Subnegotiation End

###############################################################################
# TelnetConnection Class
###############################################################################

class TelnetConnection(Stream):
    """
    A basic implementation of a Telnet connection.

    A TelnetConnection object is capable of identifying and extracting
    Telnet command sequences from incoming data. Upon identifying a
    Telnet command, option or subnegotiation, the connection will call a
    relevant placeholder method. This class should be subclassed to
    provide functionality for individual commands and options.
    """
    def __init__(self, **kwargs):
        Stream.__init__(self, **kwargs)

        # Initialize Stuff
        self._telnet_data = ""

    ##### Public Event Handlers ###############################################

    def on_command(self, command):
        """
        Placeholder. Called when the connection receives a telnet command,
        such as AYT (Are You There).

        =========  ============
        Argument   Description
        =========  ============
        command    The byte representing the telnet command.
        =========  ============
        """
        pass

    def on_option(self, command, option):
        """
        Placeholder. Called when the connection receives a telnet option
        negotiation sequence, such as IAC WILL ECHO.

        =========  ============
        Argument   Description
        =========  ============
        command    The byte representing the telnet command.
        option     The byte representing the telnet option being negotiated.
        =========  ============
        """
        pass

    def on_subnegotiation(self, option, data):
        """
        Placeholder. Called when the connection receives a subnegotiation
        sequence.

        =========  ============
        Argument   Description
        =========  ============
        option     The byte representing the telnet option for which subnegotiation data has been received.
        data       The received data.
        =========  ============
        """
        pass

    ##### Internal Telnet State Processing ####################################

    def _on_telnet_data(self, data):
        self._telnet_data += data

        while self._telnet_data:
            delimiter = self.read_delimiter

            if delimiter is None:
                data = self._telnet_data
                self._telnet_data = ''
                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, (int, long)):
                if len(self._telnet_data) < delimiter:
                    break
                data = self._telnet_data[:delimiter]
                self._telnet_data = self._telnet_data[delimiter:]
                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, basestring):
                mark = self._telnet_data.find(delimiter)
                if mark == -1:
                    break
                data = self._telnet_data[:mark]
                self._telnet_data = self._telnet_data[mark + len(delimiter):]
                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, Struct):
                # Weird. Why are you using Struct in telnet? Silly person.
                if len(self._telnet_data) < delimiter.size:
                    break
                data = self._telnet_data[:delimiter.size]
                self._telnet_data = self._telnet_data[delimiter.size:]

                try:
                    data = delimiter.unpack(data)
                except struct.error:
                    log.exception("Unable to unpack data on %r." % self)
                    self.close()
                    break

                self._safely_call(self.on_read, *data)

            elif isinstance(delimiter, _NetStruct):
                # Ditto for NetStruct.
                if not self._netstruct_iter:
                    # We need to get started.
                    self._netstruct_iter = delimiter.iter_unpack()
                    self._netstruct_needed = next(self._netstruct_iter)

                if len(self._telnet_data) < self._netstruct_needed:
                    break

                data = self._netstruct_iter.send(
                    self._telnet_data[:self._netstruct_needed])
                self._telnet_data = self._telnet_data[self._netstruct_needed:]

                if isinstance(data, (int,long)):
                    self._netstruct_needed = data
                    continue

                # Still here? Then we've got our object. Delete the NetStruct
                # state and send the data.
                self._netstruct_needed = None
                self._netstruct_iter = None

                self._safely_call(self.on_read, *data)

            elif isinstance(delimiter, RegexType):
                # Depending on regex_search, we could do this two ways.
                if self.regex_search:
                    match = delimiter.search(self._telnet_data)
                    if not match:
                        break

                    data = self._telnet_data[:match.start()]
                    self._telnet_data = self._telnet_data[match.end():]

                else:
                    data = delimiter.match(self._telnet_data)
                    if not data:
                        break
                    self._telnet_data = self._telnet_data[data.end():]

                self._safely_call(self.on_read, data)

            else:
                log.warning("Invalid read_delimiter on %r." % self)
                break

            if self._closed or not self.connected:
                break

    def _on_telnet_iac(self, data):
        if len(data) < 2:
            return False

        elif data[1] == IAC:
            # It's an escaped IAC byte. Send it to the data buffer.
            self._on_telnet_data(IAC)
            return data[2:]

        elif data[1] in '\xFB\xFC\xFD\xFE':
            if len(data) < 3:
                return False

            self._safely_call(self.on_option, data[1], data[2])
            return data[3:]

        elif data[1] == SB:
            seq = ''
            code = data[2:]
            data = data[3:]
            if not data:
                return False

            while data:
                loc = data.find(IAC)
                if loc == -1:
                    return False

                seq += data[:loc]

                if data[loc + 1] == SE:
                    # Match
                    data = data[loc+2:]
                    break

                elif data[loc + 1] == IAC:
                    # Escaped
                    seq += IAC
                    data = data[loc+2:]
                    continue

                # Unknown. Skip it.
                data = data[loc + 1:]
                if not data:
                    return False

            self._safely_call(self.on_subnegotiation, code, seq)

        # Still here? It must just be a command then. Send it on.
        self._safely_call(self.on_command, data[1])
        return data[2:]

    ##### Internal Processing Methods #########################################

    def _process_recv_buffer(self):
        """
        Completely replace the standard recv buffer processing with a custom
        function for optimal telnet performance.
        """
        while self._recv_buffer:
            loc = self._recv_buffer.find(IAC)

            if loc == -1:
                self._on_telnet_data(self._recv_buffer)
                self._recv_buffer = ''
                break

            elif loc > 0:
                self._on_telnet_data(self._recv_buffer[:loc])
                self._recv_buffer = self._recv_buffer[loc:]

            out = self._on_telnet_iac(self._recv_buffer)
            if out is False:
                break

            self._recv_buffer = out

###############################################################################
# TelnetServer Class
###############################################################################

class TelnetServer(Server):
    """
    A basic implementation of a Telnet server.
    """
    ConnectionClass = TelnetConnection

########NEW FILE########
__FILENAME__ = datagram
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
Low-level implementations of packet-oriented channels.
"""

###############################################################################
# Imports
###############################################################################

import re
import socket
import struct

from pants._channel import _Channel


###############################################################################
# Constants
###############################################################################

RegexType = type(re.compile(""))
Struct = struct.Struct

###############################################################################
# Logging
###############################################################################

import logging
log = logging.getLogger("pants")


###############################################################################
# Datagram Class
###############################################################################

class Datagram(_Channel):
    """
    A packet-oriented channel.

    ==================  ============
    Keyword Arguments   Description
    ==================  ============
    family              *Optional.* A supported socket family. By default, is :const:`socket.AF_INET`.
    socket              *Optional.* A pre-existing socket to wrap.
    ==================  ============
    """
    def __init__(self, **kwargs):
        if kwargs.setdefault("type", socket.SOCK_DGRAM) != socket.SOCK_DGRAM:
            raise TypeError("Cannot create a %s with a type other than "
                "SOCK_DGRAM." % self.__class__.__name__)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        kwargs['socket'] = sock

        _Channel.__init__(self, **kwargs)

        # Socket
        self.remote_address = None
        self.local_address = None

        # I/O attributes
        self.read_delimiter = None
        self.regex_search = True
        self._recv_buffer = {}
        self._recv_buffer_size_limit = 2 ** 16  # 64kb
        self._send_buffer = []

        # Channel state
        self.listening = False
        self._closing = False

    ##### Control Methods #####################################################

    def listen(self, addr):
        """
        Begin listening for packets sent to the channel.

        Returns the channel.

        ==========  ============
        Arguments   Description
        ==========  ============
        addr        The local address to listen for packets on.
        ==========  ============
        """
        if self.listening:
            raise RuntimeError("listen() called on listening %r." % self)

        if self._closed or self._closing:
            raise RuntimeError("listen() called on closed %r." % self)

        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass

        try:
            self._socket_bind(addr)
        except socket.error:
            self.close(flush=False)
            raise

        self.listening = True
        self._update_addr()

        return self

    def close(self, flush=True):
        """
        Close the channel.
        """
        # TODO Implement flushing functionality.
        if self._closed:
            return

        self.read_delimiter = None
        self._recv_buffer = {}
        self._send_buffer = []

        self.listening = False
        self._closing = False

        self._update_addr()

        _Channel.close(self)

    def end(self):
        """
        Close the channel after writing is finished.
        """
        # Integrate into Datagram.close and implement flushing.
        if self._closed or self._closing:
            return

        if not self._send_buffer:
            self.close(flush=False)
        else:
            self._closing = True

    ##### I/O Methods #########################################################

    def write(self, data, address=None, flush=False):
        """
        Write data to the channel.

        ==========  ============
        Arguments   Description
        ==========  ============
        data        A string of data to write to the channel.
        address     The remote address to write the data to.
        flush       If True, flush the internal write buffer.
        ==========  ============
        """
        if self._closed or self._closing:
            log.warning("Attempted to write to closed %r." % self)
            return

        if address is None:
            address = self.remote_address
            if address is None:
                log.warning("Attempted to write to %r with no remote "
                    "address." % self)
                return

        self._send_buffer.append((data, address))

        if flush:
            self._process_send_buffer()
        else:
            self._start_waiting_for_write_event()

    def flush(self):
        """
        Attempt to immediately write any internally buffered data to the
        channel.
        """
        if not self._send_buffer:
            return

        self._stop_waiting_for_write_event()
        self._process_send_buffer()

    ##### Private Methods #####################################################

    def _update_addr(self):
        """
        Update the channel's
        :attr:`~pants.datagram.Datagram.local_address` attribute.
        """
        if self.listening:
            self.local_address = self._socket.getsockname()
        else:
            self.local_address = None

    ##### Internal Event Handler Methods ######################################

    def _handle_read_event(self):
        """
        Handle a read event raised on the channel.
        """
        if self._closed:
            log.warning("Received read event for closed %r." % self)
            return

        if not self.listening:
            log.warning("Received read event for non-listening %r." % self)
            return

        while True:
            try:
                data, addr = self._socket_recvfrom()
            except socket.error:
                log.exception("Exception raised by recvfrom() on %r." % self)
                self.close(flush=False)
                return

            if not data:
                break

            self._recv_buffer[addr] = self._recv_buffer.get(addr, '') + data

            if len(self._recv_buffer[addr]) > self._recv_buffer_size_limit:
                e = DatagramBufferOverflow(
                        "Buffer length exceeded upper limit on %r." % self,
                        addr
                    )
                self._safely_call(self.on_overflow_error, e)
                return

        self._process_recv_buffer()

    def _handle_write_event(self):
        """
        Handle a write event raised on the channel.
        """
        if self._closed:
            log.warning("Received write event for closed %r." % self)
            return

        self._process_send_buffer()

    ##### Internal Processing Methods #########################################

    def _process_recv_buffer(self):
        """
        Process the :attr:`~pants.datagram.Datagram._recv_buffer`, passing
        chunks of data to :meth:`~pants.datagram.Datagram.on_read`.
        """
        for addr in self._recv_buffer.keys()[:]:
            buf = self._recv_buffer[addr]
            self.remote_address = addr

            while buf:
                delimiter = self.read_delimiter

                if delimiter is None:
                    self._safely_call(self.on_read, buf)
                    buf = ""

                elif isinstance(delimiter, (int, long)):
                    if len(buf) < delimiter:
                        break
                    data = buf[:delimiter]
                    buf = buf[delimiter:]
                    self._safely_call(self.on_read, data)

                elif isinstance(delimiter, basestring):
                    mark = buf.find(delimiter)
                    if mark == -1:
                        break
                    data = buf[:mark]
                    buf = buf[mark + len(delimiter):]
                    self._safely_call(self.on_read, data)

                elif isinstance(delimiter, Struct):
                    if len(buf) < delimiter.size:
                        break
                    data = buf[:delimiter.size]
                    buf = buf[delimiter.size:]

                    try:
                        data = delimiter.unpack(data)
                    except struct.error:
                        log.warning("Unable to unpack data on %r." % self)
                        break

                    self._safely_call(self.on_read, *data)

                elif isinstance(delimiter, RegexType):
                    # Depending on regex_search, we could do this two ways.
                    if self.regex_search:
                        match = delimiter.search(buf)
                        if not match:
                            break

                        data = buf[:match.start()]
                        buf = buf[match.end():]

                    else:
                        data = delimiter.match(buf)
                        if not data:
                            break

                        buf = buf[data.end():]

                    self._safely_call(self.on_read, data)

                else:
                    log.warning("Invalid read_delimiter on %r." % self)
                    break

                if self._closed:
                    break

            self.remote_address = None

            if buf:
                self._recv_buffer[addr] = buf
            else:
                del self._recv_buffer[addr]

            if self._closed:
                break

    def _process_send_buffer(self):
        """
        Process the :attr:`~pants.datagram.Datagram._send_buffer`,
        passing outgoing data to
        :meth:`~pants._channel._Channel._socket_sendto` and calling
        :meth:`~pants.datagram.Datagram.on_write` when sending has
        finished.
        """
        while self._send_buffer:
            data, addr = self._send_buffer.pop(0)

            while data:
                bytes_sent = self._socket_sendto(data, addr)
                self.listening = True
                self._update_addr()
                if bytes_sent == 0:
                    break
                data = data[bytes_sent:]

            if data:
                self._send_buffer.insert(0, (data, addr))
                break

        if not self._send_buffer:
            self._safely_call(self.on_write)

            if self._closing:
                self.close(flush=False)


###############################################################################
# DatagramBufferOverflow Exception
###############################################################################

class DatagramBufferOverflow(Exception):
    def __init__(self, errstr, addr):
        self.errstr = errstr
        self.addr = addr

    def __repr__(self):
        return self.errstr

########NEW FILE########
__FILENAME__ = engine
###############################################################################
#
# Copyright 2009 Facebook (see NOTICE.txt)
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
Asynchronous event processing and timer scheduling.

Pants applications are powered by instances of the
:class:`~pants.engine.Engine` class. An :class:`~pants.engine.Engine`
instance keeps track of active channels, continuously checks them for
new events and raises those events on the channel when they occur.
The :class:`~pants.engine.Engine` class also provides the timer
functionality which allows callable objects to be invoked after some
delay without blocking the process.

Engines
=======
Pants' engines are very simple to use. After you have finished
initializing your application, simply call
:meth:`~pants.engine.Engine.start` to enter the blocking event loop.
:meth:`~pants.engine.Engine.stop` may be called at any time to cause
a graceful exit from the event loop. If your application has a
pre-existing event loop you can call the
:meth:`~pants.engine.Engine.poll` method on each iteration of that loop
rather than using :meth:`~pants.engine.Engine.start` and
:meth:`~pants.engine.Engine.stop`. Ideally,
:meth:`~pants.engine.Engine.poll` should be called many times each
second to ensure that events are processed efficiently and timers
are executed on schedule.

The global engine instance is returned by the
:meth:`~pants.engine.Engine.instance()` classmethod. It is not required
that you use the global engine instance, but it is strongly recommended.
By default, new channels are automatically added to the global engine
when they are created. Channels can be added to a specific engine by
passing the engine instance as a keyword argument to the channel's
constructor. If a :class:`~pants.server.Server` is added to a
non-default engine, any connections it accepts will also be added to
that engine.

Timers
======
In addition to managing channels, Pants' engines can also schedule
timers. Timers are callable objects that get invoked at some point in
the future. Pants has four types of timers: callbacks, loops, deferreds
and cycles. Callbacks and loops are executed each time
:meth:`~pants.engine.Engine.poll` is called - callbacks are executed
once while loops are executed repeatedly. Deferreds and cycles are
executed after a delay specified in seconds - deferreds are executed
once while cycles are executed repeatedly.

:class:`~pants.engine.Engine` has methods for creating each of the four
types of timers: :meth:`~pants.engine.Engine.callback`,
:meth:`~pants.engine.Engine.loop`, :meth:`~pants.engine.Engine.defer`
and :meth:`~pants.engine.Engine.cycle`. Each of these methods is passed
a callable to execute as well as any number of positional and keyword
arguments::

    engine.callback(my_callable, 1, 2, foo='bar')

The timer methods all return a callable object which can be used to
cancel the execution of the timer::

    cancel_cycle = engine.cycle(10.0, my_callable)
    cancel_cycle()

Any object references passed to a timer method will be retained in
memory until the timer has finished executing or is cancelled. Be aware
of this when writing code, as it may cause unexpected behaviors should
you fail to take these references into account. Timers rely on their
engine for scheduling and execution. For best results, you should either
schedule timers while your engine is running or start your engine
immediately after scheduling your timers.

Pollers
=======
By default, Pants' engines support the :py:obj:`~select.epoll`,
:py:obj:`~select.kqueue` and :py:obj:`~select.select` polling methods.
The most appropriate polling method is selected based on the platform on
which Pants is running. Advanced users may wish to use a different
polling method. This can be done by defining a custom poller class and
passing an instance of it to the :class:`~pants.engine.Engine`
constructor. Interested users should review the source code for an
understanding of how these classes are defined and used.
"""

###############################################################################
# Imports
###############################################################################

import bisect
import errno
import functools
import select
import sys
import time


###############################################################################
# Logging
###############################################################################

import logging
log = logging.getLogger("pants")


###############################################################################
# Time
###############################################################################

# This hack is here because Windows' time() is too imprecise for our needs.
# See issue #40 for further details.
if sys.platform == "win32":
    _start_time = time.time()
    time.clock()  # Initialise the clock.
    current_time = lambda: round(_start_time + time.clock(), 2)
else:
    current_time = time.time


###############################################################################
# Engine Class
###############################################################################

class Engine(object):
    """
    The asynchronous engine class.

    An engine object is responsible for passing I/O events to active
    channels and running timers asynchronously. Depending on OS support,
    the engine will use either the :py:func:`~select.epoll()`,
    :py:func:`~select.kqueue()` or :py:func:`~select.select()` system
    call to detect events on active channels. It is possible to force
    the engine to use a particular polling method, but this is not
    recommended.

    Most applications will use the global engine object, which can be
    accessed using :meth:`~pants.engine.Engine.instance`, however it is
    also possible to create and use multiple instances of
    :class:`~pants.engine.Engine` in your application.

    An engine can either provide the main loop for your application
    (see :meth:`~pants.engine.Engine.start` and
    :meth:`~pants.engine.Engine.stop`), or its functionality can be
    integrated into a pre-existing main loop (see
    :meth:`~pants.engine.Engine.poll`).

    =========  =========================================================
    Argument   Description
    =========  =========================================================
    poller     *Optional.* A specific polling object for the engine to
               use.
    =========  =========================================================
    """
    # Socket events - these correspond to epoll() states.
    NONE = 0x00
    READ = 0x01
    WRITE = 0x04
    ERROR = 0x08
    HANGUP = 0x10 | 0x2000
    BASE_EVENTS = READ | ERROR | HANGUP
    ALL_EVENTS = BASE_EVENTS | WRITE

    def __init__(self, poller=None):
        self.latest_poll_time = current_time()

        self._shutdown = False
        self._running = False

        self._channels = {}
        self._poller = None
        self._install_poller(poller)

        self._callbacks = []
        self._deferreds = []

    @classmethod
    def instance(cls):
        """
        Returns the global engine object.
        """
        if not hasattr(cls, "_instance"):
            cls._instance = cls()

        return cls._instance

    ##### Engine Methods ######################################################

    def start(self, poll_timeout=0.2):
        """
        Start the engine.

        Initialises and continuously polls the engine until either
        :meth:`~pants.engine.Engine.stop` is called or an uncaught
        :obj:`Exception` is raised. :meth:`~pants.engine.Engine.start`
        should be called after your asynchronous application has been fully
        initialised. For applications with a pre-existing main loop, see
        :meth:`~pants.engine.Engine.poll`.

        =============  ===================================
        Argument       Description
        =============  ===================================
        poll_timeout   *Optional.* The timeout to pass to
                       :meth:`~pants.engine.Engine.poll`.
        =============  ===================================
        """
        if self._shutdown:
            self._shutdown = False
            return
        if self._running:
            return
        else:
            self._running = True

        log.info("Starting engine.")

        try:
            while not self._shutdown:
                self.poll(poll_timeout)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            log.exception("Uncaught exception in main loop.")
        finally:
            log.info("Stopping engine.")
            self._shutdown = False
            self._running = False

    def stop(self):
        """
        Stop the engine.

        If :meth:`~pants.engine.Engine.start` has been called, calling
        :meth:`~pants.engine.Engine.stop` will cause the engine to cease
        polling and shut down on the next iteration of the main loop.
        """
        if self._running:
            self._shutdown = True

    def poll(self, poll_timeout):
        """
        Poll the engine.

        Updates timers and processes I/O events on all active channels.
        If your application has a pre-existing main loop, call
        :meth:`~pants.engine.Engine.poll` on each iteration of that
        loop, otherwise, see :meth:`~pants.engine.Engine.start`.

        ============= ============
        Argument      Description
        ============= ============
        poll_timeout  The timeout to be passed to the polling object.
        ============= ============
        """
        self.latest_poll_time = current_time()

        callbacks, self._callbacks = self._callbacks[:], []

        for timer in callbacks:
            try:
                timer.function()
            except Exception:
                log.exception("Exception raised while executing timer.")

            if timer.requeue:
                self._callbacks.append(timer)

        while self._deferreds and self._deferreds[0].end <= self.latest_poll_time:
            timer = self._deferreds.pop(0)

            try:
                timer.function()
            except Exception:
                log.exception("Exception raised while executing timer.")

            if timer.requeue:
                timer.end = self.latest_poll_time + timer.delay
                bisect.insort(self._deferreds, timer)

        if self._shutdown:
            return

        if self._deferreds:
            timeout = self._deferreds[0].end - self.latest_poll_time
            if timeout > 0.0:
                poll_timeout = max(min(timeout, poll_timeout), 0.01)

        if not self._channels:
            time.sleep(poll_timeout)  # Don't burn CPU.
            return

        try:
            events = self._poller.poll(poll_timeout)
        except Exception as err:
            if err.args[0] == errno.EINTR:
                log.debug("Interrupted system call.")
                return
            else:
                raise

        for fileno, events in events.iteritems():
            channel = self._channels[fileno]
            try:
                channel._handle_events(events)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                log.exception("Error while handling events on %r." % channel)

    ##### Timer Methods #######################################################

    def callback(self, function, *args, **kwargs):
        """
        Schedule a callback.

        A callback is a function (or other callable) that is executed
        the next time :meth:`~pants.engine.Engine.poll` is called - in
        other words, on the next iteration of the main loop.

        Returns a callable which can be used to cancel the callback.

        =========  ============
        Argument   Description
        =========  ============
        function   The callable to be executed when the callback is run.
        args       The positional arguments to be passed to the callable.
        kwargs     The keyword arguments to be passed to the callable.
        =========  ============
        """
        callback = functools.partial(function, *args, **kwargs)
        timer = _Timer(self, callback, False)
        self._callbacks.append(timer)

        return timer

    def loop(self, function, *args, **kwargs):
        """
        Schedule a loop.

        A loop is a callback that is continuously rescheduled. It will
        be executed every time :meth:`~pants.engine.Engine.poll` is
        called - in other words, on each iteraton of the main loop.

        Returns a callable which can be used to cancel the loop.

        =========  ============
        Argument   Description
        =========  ============
        function   The callable to be executed when the loop is run.
        args       The positional arguments to be passed to the callable.
        kwargs     The keyword arguments to be passed to the callable.
        =========  ============
        """
        loop = functools.partial(function, *args, **kwargs)
        timer = _Timer(self, loop, True)
        self._callbacks.append(timer)

        return timer

    def defer(self, delay, function, *args, **kwargs):
        """
        Schedule a deferred.

        A deferred is a function (or other callable) that is executed
        after a certain amount of time has passed.

        Returns a callable which can be used to cancel the deferred.

        =========  =====================================================
        Argument   Description
        =========  =====================================================
        delay      The delay, in seconds, after which the deferred
                   should be run.
        function   The callable to be executed when the deferred is run.
        args       The positional arguments to be passed to the
                   callable.
        kwargs     The keyword arguments to be passed to the callable.
        =========  =====================================================
        """
        if delay <= 0:
            raise ValueError("Delay must be greater than 0 seconds.")

        deferred = functools.partial(function, *args, **kwargs)
        timer = _Timer(self, deferred, False, delay, self.latest_poll_time + delay)
        bisect.insort(self._deferreds, timer)

        return timer

    def cycle(self, interval, function, *args, **kwargs):
        """
        Schedule a cycle.

        A cycle is a deferred that is continuously rescheduled. It will
        be run at regular intervals.

        Returns a callable which can be used to cancel the cycle.

        =========  ============
        Argument   Description
        =========  ============
        interval   The interval, in seconds, at which the cycle should be run.
        function   The callable to be executed when the cycle is run.
        args       The positional arguments to be passed to the callable.
        kwargs     The keyword arguments to be passed to the callable.
        =========  ============
        """
        if interval <= 0:
            raise ValueError("Interval must be greater than 0 seconds.")

        cycle = functools.partial(function, *args, **kwargs)
        timer = _Timer(self, cycle, True, interval, self.latest_poll_time + interval)
        bisect.insort(self._deferreds, timer)

        return timer

    def _remove_timer(self, timer):
        """
        Remove a timer from the engine.

        =========  ============
        Argument   Description
        =========  ============
        timer      The timer to be removed.
        =========  ============
        """
        if timer.end is None:
            try:
                self._callbacks.remove(timer)
            except ValueError:
                pass  # Callback not present.
        else:
            try:
                self._deferreds.remove(timer)
            except ValueError:
                pass  # Callback not present.

    ##### Channel Methods #####################################################

    def add_channel(self, channel):
        """
        Add a channel to the engine.

        =========  ============
        Argument   Description
        =========  ============
        channel    The channel to be added.
        =========  ============
        """
        self._channels[channel.fileno] = channel
        self._poller.add(channel.fileno, channel._events)

    def modify_channel(self, channel):
        """
        Modify the state of a channel.

        =========  ============
        Argument   Description
        =========  ============
        channel    The channel to be modified.
        =========  ============
        """
        self._poller.modify(channel.fileno, channel._events)

    def remove_channel(self, channel):
        """
        Remove a channel from the engine.

        =========  ============
        Argument   Description
        =========  ============
        channel    The channel to be removed.
        =========  ============
        """
        self._channels.pop(channel.fileno, None)

        try:
            self._poller.remove(channel.fileno, channel._events)
        except (IOError, OSError):
            log.exception("Error while removing %r." % channel)

    ##### Poller Methods ######################################################

    def _install_poller(self, poller=None):
        """
        Install a poller on the engine.

        =========  ============
        Argument   Description
        =========  ============
        poller     The poller to be installed.
        =========  ============
        """
        if self._poller is not None:
            for fileno, channel in self._channels.iteritems():
                self._poller.remove(fileno, channel._events)

        if poller is not None:
            self._poller = poller
        elif hasattr(select, "epoll"):
            self._poller = _EPoll()
        elif hasattr(select, "kqueue"):
            self._poller = _KQueue()
        else:
            self._poller = _Select()

        for fileno, channel in self._channels.iteritems():
            self._poller.add(fileno, channel._events)


###############################################################################
# _EPoll Class
###############################################################################

class _EPoll(object):
    """
    An :py:func:`~select.epoll`-based poller.
    """
    def __init__(self):
        self._epoll = select.epoll()

    def add(self, fileno, events):
        self._epoll.register(fileno, events)

    def modify(self, fileno, events):
        self._epoll.modify(fileno, events)

    def remove(self, fileno, events):
        self._epoll.unregister(fileno)

    def poll(self, timeout):
        return dict(self._epoll.poll(timeout))


###############################################################################
# _KQueue Class
###############################################################################

class _KQueue(object):
    """
    A :py:func:`~select.kqueue`-based poller.
    """
    MAX_EVENTS = 1024

    def __init__(self):
        self._events = {}
        self._kqueue = select.kqueue()

    def add(self, fileno, events):
        self._events[fileno] = events
        self._control(fileno, events, select.KQ_EV_ADD)

    def modify(self, fileno, events):
        self.remove(fileno, self._events[fileno])
        self.add(fileno, events)

    def remove(self, fileno, events):
        self._control(fileno, events, select.KQ_EV_DELETE)
        self._events.pop(fileno, None)

    def poll(self, timeout):
        events = {}
        kqueue_events = self._kqueue.control(None, _KQueue.MAX_EVENTS, timeout)

        for event in kqueue_events:
            fileno = event.ident

            if event.filter == select.KQ_FILTER_READ:
                events[fileno] = events.get(fileno, 0) | Engine.READ
            if event.filter == select.KQ_FILTER_WRITE:
                events[fileno] = events.get(fileno, 0) | Engine.WRITE
            if event.flags & select.KQ_EV_ERROR:
                events[fileno] = events.get(fileno, 0) | Engine.ERROR
            if event.flags & select.KQ_EV_EOF:
                events[fileno] = events.get(fileno, 0) | Engine.HANGUP

        return events

    def _control(self, fileno, events, flags):
        if events & Engine.WRITE:
            event = select.kevent(fileno, filter=select.KQ_FILTER_WRITE,
                                  flags=flags)
            self._kqueue.control([event], 0)

        if events & Engine.READ:
            event = select.kevent(fileno, filter=select.KQ_FILTER_READ,
                                  flags=flags)
            self._kqueue.control([event], 0)


###############################################################################
# _Select Class
###############################################################################

class _Select(object):
    """
    A :py:func:`~select.select`-based poller.
    """
    def __init__(self):
        self._r = set()
        self._w = set()
        self._e = set()

    def add(self, fileno, events):
        if events & Engine.READ:
            self._r.add(fileno)
        if events & Engine.WRITE:
            self._w.add(fileno)
        if events & Engine.ERROR:
            self._e.add(fileno)

    def modify(self, fileno, events):
        self.remove(fileno, events)
        self.add(fileno, events)

    def remove(self, fileno, events):
        self._r.discard(fileno)
        self._w.discard(fileno)
        self._e.discard(fileno)

    def poll(self, timeout):
        # Note that select() won't raise "hangup" events. There's no way
        # around this and no way to determine whether a hangup or an
        # error occurred. C'est la vie.
        events = {}
        r, w, e, = select.select(self._r, self._w, self._e, timeout)

        for fileno in r:
            events[fileno] = events.get(fileno, 0) | Engine.READ
        for fileno in w:
            events[fileno] = events.get(fileno, 0) | Engine.WRITE
        for fileno in e:
            events[fileno] = events.get(fileno, 0) | Engine.ERROR

        return events


###############################################################################
# _Timer Class
###############################################################################

class _Timer(object):
    """
    A simple class for storing timer information.

    =========  ======================================================
    Argument   Description
    =========  ======================================================
    function   The callable to be executed when the timer is run.
    requeue    Whether the timer should be requeued after being run.
    delay      The time, in seconds, after which the timer should be
               run- or None, for a callback/loop.
    end        The time, in seconds since the epoch, after which the
               timer should be run - or None, for a callback/loop.
    =========  ======================================================
    """
    def __init__(self, engine, function, requeue, delay=None, end=None):
        self.engine = engine
        self.function = function
        self.requeue = requeue
        self.delay = delay
        self.end = end

    def __call__(self):
        self.cancel()

    def __cmp__(self, to):
        return cmp(self.end, to.end)

    def cancel(self):
        self.engine._remove_timer(self)

########NEW FILE########
__FILENAME__ = auth
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import base64

###############################################################################
# BaseAuth Class
###############################################################################

class AuthBase(object):
    def __call__(self, request):
        raise NotImplementedError("BaseAuth instances must be callable.")

def _basic_auth(username, password):
    return 'Basic ' + base64.b64encode('%s:%s' % (username, password))

###############################################################################
# Basic Authentication
###############################################################################

class BasicAuth(AuthBase):
    """ Basic HTTP authentication. """
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __call__(self, request):
        request.headers['Authorization'] = _basic_auth(self.username,
                                                       self.password)
        return request

class ProxyAuth(BasicAuth):
    """ Basic Proxy-Authorization """
    def __call__(self, request):
        request.headers['Proxy-Authorization'] = _basic_auth(self.username,
                                                             self.password)
        return request

###############################################################################
# Digest Authentication
###############################################################################

# TODO: Write Digest Authentication

########NEW FILE########
__FILENAME__ = client
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
``pants.http.client`` implements a basic asynchronous HTTP client on top of
Pants with an API modelled after that of the wonderful
`requests <http://www.python-requests.org/>`_ library. The client supports
keep-alive and SSL for connections, domain verification for SSL certificates,
basic WWW authentication, sessions with persistent cookies, automatic redirect
handling, automatic decompression of responses, connection timeouts, file
uploads, and saving large responses to temporary files to decrease
memory usage.

Logic is implemented using a series of request handlers.

Making Requests
===============

It's simple and easy to make requests, and it only requires that you have an
instance of :class:`HTTPClient` ready.

.. code-block:: python

    from pants.http import HTTPClient
    client = HTTPClient()

Like with `requests <http://www.python-requests.org/>`_, there are simple
methods for making requests with the different HTTP methods. For now, let's get
information for a bunch of Pants' commits on GitHub.

.. code-block:: python

    client.get("https://api.github.com/repos/ecdavis/pants/commits")

You'll notice that this is very similar to making a request with requests.
However, we do not get a response objects. Actually, calling
:meth:`HTTPClient.get` returns an instance of :class:`HTTPRequest` rather than
anything to do with a response, but we'll get to that later.

The Pants HTTP client is asynchronous, so to get your response, you need a
response handler. There are several ways to set one up, but the easiest way is
to pass it to your :class:`HTTPClient` during initialization.

.. code-block:: python

    def handle_response(response):
        if response.status_code != 200:
            print "There was a problem!"

    client = HTTPClient(handle_response)

``response`` in this situation is an instance of :class:`HTTPResponse`, and
it has an API modelled after the response objects that requests would give you.


Making *Useful* Requests
------------------------

Basic GET requests are nice, but you'll often want to send data to the server.
For query parameters you can use the optional *params* argument of the various
request methods, like so::

    data = {'since': '2013-11-01'}
    client.get("https://api.github.com/repos/ecdavis/pants/commits", params=data)

With that, you could eventually take your response and get the correct URL.

.. code-block:: python

    >>> response.url
    'https://api.github.com/repos/ecdavis/pants/commits?since=2013-11-01'

You can also post data to the server, either as a pre-made string, or as a
dictionary of values to be encoded.

.. code-block:: python

    client.post("http://httpbin.org/post", data="Hello World!")
    client.post("http://httpbin.org/post", data={"greeting": "Hello"})

By default, the ``Content-Type`` header will be set to
``application/x-www-form-urlencoded`` when you provide data for the request
body. If any files are present, it will instead default to
``multipart/form-data`` to transmit those. You can also manually set the
header when making your request.

You set files via the files parameter, which expects a dictionary of form field
names and file objects. You can also provide filenames if desired.

.. code-block:: python

    client.post("http://httpbin.org/post", files={'file': open("test.txt")})
    client.post("http://httpbin.org/post", files={'file': ("test.txt", open("test.txt"))})

You can, of course, use data and files together. Please note that, if you *do*
use them together, you'll need to supply data as a dictionary. Data strings are
not supported.

As many of you have probably noticed, this is *very* similar to using
`requests <http://www.python-requests.org/>`_. The Pants API was implemented
this way to make it easier to switch between the two libraries.


Reading Responses
=================

Making your request is only half the battle, of course. You have to read your
response when it comes in. And, for that, you start with the status code.

.. code-block:: python

    >>> response.status_code
    200
    >>> response.status_text
    'OK'
    >>> response.status
    '200 OK'

Unlike with requests, there is no ``raise_for_status()`` method available.
Raising a strange exception in an asynchronous framework that your code isn't
designed to catch just wouldn't work.


Headers
-------

HTTP headers are case-insensitive, and so the headers are stored in a special
case-insensitive dictionary made available as :attr:`HTTPResponse.headers`.

.. code-block:: python

    >>> response.headers
    HTTPHeaders({
        'Content-Length': 986,
        'Server': 'gunicorn/0.17.4',
        'Connection': 'keep-alive',
        'Date': 'Wed, 06 Nov 2013 05:58:53 GMT',
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
        })
    >>> response.headers['content-length']
    986

Nothing special here.


Cookies
-------

Cookies are a weak point of Pants' HTTP client at this time. Cookies are stored
in instances of :class:`Cookie.SimpleCookie`, which doesn't handle multiple
domains. Pants has logic to prevent sending cookies to the wrong domains, but
ideally it should move to using a better cookie storage structure in future
versions that handles multiple domains elegantly.

.. code-block:: python

    >>> response.cookies['cake']
    <Morsel: cake='lie'>
    >>> response.cookies['cake'].value
    'lie'

As you can see, Pants does not yet handle cookies as well as requests. Setting
cookies is a bit better.

.. code-block:: python

    client.get("http://httpbin.org/cookies", cookies={"cake": "lie"})


Redirects
---------

The HTTP client will follow redirects automatically. When this happens, the
redirecting responses are stored in the :attr:`HTTPResponse.history` list.

.. code-block:: python

    >>> response.history
    [<HTTPResponse [301 Moved Permanently] at 0x2C988F0>]

You can limit the number of times the HTTP client will automatically follow
redirects with the ``max_redirects`` argument.

.. code-block:: python

    client.get("http://github.com/", max_redirects=0)

By default, Pants will follow up to 10 redirects.


"""

###############################################################################
# Imports
###############################################################################

import codecs
import Cookie
import json
import os
import ssl
import tempfile
import urllib
import urlparse
import zlib

from datetime import datetime

from pants.stream import Stream
from pants.engine import Engine

from pants.http.auth import BasicAuth
from pants.http.utils import CRLF, date, DOUBLE_CRLF, encode_multipart, log, \
    read_headers, USER_AGENT

try:
    from backports.ssl_match_hostname import match_hostname, CertificateError
except ImportError:
    match_hostname = None
    class CertificateError(Exception):
        pass

###############################################################################
# Exports
###############################################################################

__all__ = (
    # Exceptions
    "HTTPClientException", "RequestTimedOut", "MalformedResponse",
    "RequestClosed",

    # Core Classes
    "HTTPClient", "Session", "HTTPResponse",
)

###############################################################################
# Constants
###############################################################################

CHUNK_SIZE = 2 ** 16
MAX_MEMORY_SIZE = 2 ** 20


###############################################################################
# Exceptions
###############################################################################

class HTTPClientException(Exception):
    """
    The base exception for all the exceptions used by the HTTP client, aside
    from :class:`CertificateError`.
    """
    pass


class RequestTimedOut(HTTPClientException):
    """ The exception returned when a connection times out. """
    pass


class MalformedResponse(HTTPClientException):
    """ The exception returned when the response is malformed in some way. """
    pass


class RequestClosed(HTTPClientException):
    """
    The exception returned when the connection closes before the entire
    request has been downloaded.
    """
    pass


###############################################################################
# Content Encoding
###############################################################################

CONTENT_ENCODING = {}

def encoding_gzip():
    return zlib.decompressobj(16 + zlib.MAX_WBITS)
CONTENT_ENCODING['gzip'] = encoding_gzip


def encoding_deflate():
    return zlib.decompressobj(-zlib.MAX_WBITS)
CONTENT_ENCODING['deflate'] = encoding_deflate


###############################################################################
# Cookie Loading
###############################################################################

def _get_cookies(request):
    """ Build a SimpleCookie with all the necessary cookies. """
    cookies = Cookie.SimpleCookie()
    if request.cookies:
        for key in request.cookies:
            cookies.load(request.cookies[key].output(None, ''))
    if request.cookies is not request.session.cookies:
        _load_cookies(cookies, request.session)
    elif request.session.parent:
        _load_cookies(cookies, request.session.parent)
    return cookies


def _load_cookies(cookies, session):
    if session.cookies:
        for key in session.cookies:
            if not key in cookies:
                cookies.load(session.cookies[key].output(None, ''))
    if session.parent:
        _load_cookies(cookies, session.parent)


###############################################################################
# Getting Hostname and Port on Python <2.7
###############################################################################

def _hostname(parts):
    # This code is borrowed from Python 2.7's argparse.
    netloc = parts.netloc.split('@')[-1]
    if '[' in netloc and ']' in netloc:
        return netloc.split(']')[0][1:].lower()
    elif ':' in netloc:
        return netloc.split(':')[0].lower()
    elif not netloc:
        return None
    else:
        return netloc.lower()


def _port(parts):
    # This code is borrowed from Python 2.7's argparse.
    netloc = parts.netloc.split('@')[-1].split(']')[-1]
    if ':' in netloc:
        port = netloc.split(':')[1]
        return int(port, 10)
    else:
        return None


###############################################################################
# _HTTPStream Class
###############################################################################

class _HTTPStream(Stream):
    """
    The _HTTPStream is a basic Pants client with an extra function for
    determining if it can connect to a given host without being destroyed and
    recreated. This is useful when dealing with proxies.

    It also automatically connects to the provided HTTPClient.
    """

    _host = None

    def __init__(self, client, *args, **kwargs):
        Stream.__init__(self, *args, **kwargs)
        self.client = client

        # This should be true when connected to certain proxies.
        self.need_full_url = False

    def can_fetch(self, host, is_secure):
        """
        Returns True if this stream can connect to the provided host (a string
        of ``"host:port"``) with HTTP (or HTTPS if is_secure is True), or
        False otherwise.
        """
        if not self.connected:
            return True
        if self.ssl_enabled != is_secure:
            return False

        if isinstance(self._host, basestring):
            if self._host != host:
                return False
        else:
            host, port = host.split(':')
            port = int(port)
            if host != self._host or port != self.remote_address[-1]:
                return False

        return True

    def connect(self, addr):
        if isinstance(addr, basestring):
            self._host = addr
        else:
            self._host = "%s:%d" % (addr[0], addr[-1])

        if self.connected:
            self._safely_call(self.on_connect)
        else:
            Stream.connect(self, addr)

    def on_connect(self):
        self.client._on_connect()

    def on_close(self):
        self.client._on_close()

    def on_connect_error(self, err):
        self.client._on_connect_error(err)

    def on_read_error(self, err):
        self.client._do_error(err)

    def on_overflow_error(self, err):
        self.client._do_error(err)


###############################################################################
# HTTPClient Class
###############################################################################

class HTTPClient(object):
    """
    An easy to use, asynchronous HTTP client implementing HTTP 1.1. All
    arguments passed to HTTPClient are used to initialize the default session.
    See :class:`Session` for more details. The following is a basic example of
    using an HTTPClient to fetch a remote resource::

        from pants.http import HTTPClient
        from pants.engine import Engine

        def response_handler(response):
            Engine.instance().stop()
            print response.content

        client = HTTPClient(response_handler)
        client.get("http://httpbin.org/ip")
        Engine.instance().start()

    Groups of requests can have their behavior customized with the use of
    sessions::

        from pants.http import HTTPClient
        from pants.engine import Engine

        def response_handler(response):
            Engine.instance().stop()
            print response.content

        def other_handler(response):
            print response.content

        client = HTTPClient(response_handler)
        client.get("http://httpbin.org/cookies")

        with client.session(cookies={'pie':'yummy'}):
            client.get("http://httpbin.org/cookies")

        Engine.instance().start()

    """

    def __init__(self, *args, **kwargs):
        """ Initialize the HTTPClient and start the first session. """

        # Figure out our engine.
        if 'engine' in kwargs:
            self.engine = kwargs.pop("engine")
        else:
            self.engine = Engine.instance()

        # Internal State
        self._stream = None
        self._processing = None
        self._requests = []
        self._sessions = []
        self._ssl_options = None
        self._reading_forever = False
        self._want_close = False
        self._no_process = False

        # Create the first Session
        ses = Session(self, *args, **kwargs)
        self._sessions.append(ses)


    ##### Public Event Handlers ###############################################

    def on_response(self, response):
        """
        Placeholder. Called when a complete response has been received.

        =========  ============
        Argument   Description
        =========  ============
        response   A :class:`HTTPResponse` instance with information about the received response.
        =========  ============
        """
        pass


    def on_headers(self, response):
        """
        Placeholder. Called when we've received headers for a request. You can
        abort a request at this time by returning False from this function. It
        *must* be False, and not simply a false-like value, such as an empty
        string.

        .. note::

            This function isn't called for HTTP ``HEAD`` requests.

        =========  ============
        Argument   Description
        =========  ============
        response   A :class:`HTTPResponse` instance with information about the received response.
        =========  ============
        """
        pass


    def on_progress(self, response, received, total):
        """
        Placeholder. Called when progress is made in downloading a response.

        =========  ============
        Argument   Description
        =========  ============
        response   A :class:`HTTPResponse` instance with information about the response.
        received   The number of bytes received thus far.
        total      The total number of bytes expected for the response. This will be ``0`` if we don't know how much to expect.
        =========  ============
        """
        pass


    def on_ssl_error(self, response, certificate, exception):
        """
        Placeholder. Called when the remote server's SSL certificate failed
        initial verification. If this method returns True, the certificate will
        be accepted, otherwise, the connection will be closed and
        :func:`on_error` will be called.

        ============  ============
        Argument      Description
        ============  ============
        response      A :class:`HTTPResponse` instance with information about the response. Notably, with the ``host`` to expect.
        certificate   A dictionary representing the certificate that wasn't automatically verified.
        exception     A CertificateError instance with information about the error that occurred.
        ============  ============
        """
        return False


    def on_error(self, response, exception):
        """
        Placeholder. Called when an error occurs.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   An Exception instance with information about the error that occurred.
        ==========  ============
        """
        pass


    ##### Session Generation ##################################################

    def session(self, *args, **kwargs):
        """ Create a new session. See :class:`Session` for details. """
        return Session(self, *args, **kwargs)


    ##### Request Making ######################################################

    def request(self, *args, **kwargs):
        """
        Begin a request. Missing parameters will be taken from the active
        session when available. See :func:`Session.request` for more details.
        """
        return self._sessions[-1].request(*args, **kwargs)


    def delete(self, url, **kwargs):
        """ Begin a DELETE request. See :func:`request` for more details. """
        return self.request("DELETE", url, **kwargs)


    def get(self, url, params=None, **kwargs):
        """ Begin a GET request. See :func:`request` for more details. """
        return self.request("GET", url, params=params, **kwargs)


    def head(self, url, params=None, **kwargs):
        """ Begin a HEAD request. See :func:`request` for more details. """
        return self.request("HEAD", url, params=params, **kwargs)


    def options(self, url, **kwargs):
        """ Begin an OPTIONS request. See :func:`request` for more details. """
        return self.request("OPTIONS", url, **kwargs)


    def patch(self, url, data=None, **kwargs):
        """ Begin a PATCH request. See :func:`request` for more details. """
        return self.request("PATCH", url, data=data, **kwargs)


    def post(self, url, data=None, files=None, **kwargs):
        """ Begin a POST request. See :func:`request` for more details. """
        return self.request("POST", url, data=data, files=files, **kwargs)


    def put(self, url, data=None, **kwargs):
        """ Begin a PUT request. See :func:`request` for more details. """
        return self.request("PUT", url, data=data, **kwargs)


    def trace(self, url, **kwargs):
        """ Begin a TRACE request. See :func:`request` for more details. """
        return self.request("TRACE", url, **kwargs)


    ##### Internals ###########################################################

    def _safely_call(self, thing_to_call, *args, **kwargs):
        """
        Safely execute a callable.

        The callable is wrapped in a try block and executed. If an
        exception is raised it is logged.

        ==============  ============
        Argument        Description
        ==============  ============
        thing_to_call   The callable to execute.
        *args           The positional arguments to be passed to the callable.
        **kwargs        The keyword arguments to be passed to the callable.
        ==============  ============
        """
        try:
            return thing_to_call(*args, **kwargs)
        except Exception:
            log.exception("Exception raised in callback on %r." % self)


    def _process(self):
        """ Send the first request on the stack. """
        if not self._requests:
            # Stop processing and close any connection since we've not got any
            # requests left.
            if self._stream:
                self._want_close = True
                self._no_process = True
                self._stream.close(False)
                self._stream = None
            self._processing = False
            return
        self._processing = True

        # Get the request.
        request = self._requests[0]

        # Make sure it has a response.
        if not request.response:
            HTTPResponse(request)

        # Handle authentication.
        if request.auth and not isinstance(request.auth, (list,tuple)):
            request = request.auth(request)

        # Now, determine what we should be connected to.
        port = _port(request.url)
        is_secure = request.url.scheme == 'https'
        if not port:
            port = 443 if is_secure else 80
        host = '%s:%d' % (_hostname(request.url), port)

        # If we have a stream, and it's not connected to that host, kill it
        # to make a new one.
        if self._stream:
            if not self._stream.connected:
                self._stream = None
            elif self._ssl_options != request.session.ssl_options or \
                    not self._stream.can_fetch(host, is_secure):
                log.debug("Closing unusable stream for %r." % self)
                self._want_close = True
                self._no_process = False
                self._stream.close(False)
                return

        # Set the timeout timer and log.
        log.debug("Sending HTTP request %r." % request)
        self._reset_timer()

        # Create a stream.
        if not self._stream:
            self._stream = _HTTPStream(self, engine=self.engine)

        # If we're secure, and the stream isn't, secure it.
        if is_secure and not self._stream.ssl_enabled:
            self._ssl_options = request.session.ssl_options
            self._stream.startSSL(self._ssl_options or {})

        # Connect the stream to await further orders.
        self._stream.connect((_hostname(request.url), port))


    def _timed_out(self, request):
        """ Called when a request times out. """
        if not request in self._requests:
            return

        log.debug("HTTP request %r timed out." % request)

        self._requests.remove(request)
        request.session.on_error(request.response, RequestTimedOut())

        # Now, close the connection, and keep processing.
        if self._stream:
            self._want_close = True
            self._no_process = True
            self._stream.close(False)
            self._stream = None
        self._process()


    def _reset_timer(self):
        if not self._requests:
            return
        request = self._requests[0]

        # Clear the existing timer.
        if request._timeout_timer:
            request._timeout_timer()

        request._timeout_timer = self.engine.defer(request.timeout,
                                                   self._timed_out, request)


    ##### Stream I/O Handlers #################################################

    def _on_connect(self):
        """ The Stream connected, so send the request. """
        if not self._requests:
            return
        request = self._requests[0]
        self._reset_timer()

        # Check our security.
        if request.url.scheme == 'https' and request.session.verify_ssl:
            # We care!
            cert = self._stream._socket.getpeercert()
            try:
                match_hostname(cert, _hostname(request.url))
            except CertificateError as err:
                if not self._safely_call(request.session.on_ssl_error,
                        request.response, cert, err):
                    self._do_error(err)
                    return

        # Write the request.
        if self._stream.need_full_url:
            path = "%s://%s%s" % (request.url.scheme, request.url.netloc,
                                  request.path)
        else:
            path = request.path

        self._stream.write("%s %s HTTP/1.1%s" % (request.method, path, CRLF))

        # Headers
        for key, val in request.headers.iteritems():
            self._stream.write("%s: %s%s" % (key, val, CRLF))

        # Cookies
        cookies = _get_cookies(request)
        if cookies:
            for key in cookies:
                morsel = cookies[key]
                if not request.path.startswith(morsel['path']) or \
                        not _hostname(request.url).lower().\
                        endswith(morsel['domain'].lower()) or \
                        morsel['secure'] and request.url.scheme != 'https':
                    continue
                self._stream.write(morsel.output(None, 'Cookie:') + CRLF)

        # And now, the body.
        self._stream.write(CRLF)
        if request.body:
            for item in request.body:
                if isinstance(item, basestring):
                    self._stream.write(item)
                else:
                    self._stream.write_file(item)

        # Now, we wait for a response.
        self._stream.on_read = self._read_headers
        self._stream.read_delimiter = DOUBLE_CRLF


    def _on_connect_error(self, err):
        """ The Stream had an exception. Pass it along. """
        if not self._requests:
            return

        # Pop off the request that had an error, and clear its timeout.
        request = self._requests.pop(0)
        if request._timeout_timer:
            request._timeout_timer()

        # Do the error method.
        self._safely_call(request.session.on_error, request.response, err)

        # Kill the stream.
        if self._stream:
            self._want_close = True
            self._no_process = True
            self._stream.close(False)
            self._stream = None

        # Keep processing, if needed.
        self._process()


    def _on_close(self):
        """
        If we weren't expecting the stream to close, it's an error, otherwise,
        just process our requests.
        """

        # Are we reading forever?
        if self._reading_forever:
            self._reading_forever = False
            # Right, clean up then.
            if self._requests:
                # Get the request.
                request = self._requests[0]
                response = request.response

                # Clean out the decoder.
                if response._decoder:
                    response._receive(response._decoder.flush())
                    response._receive(response._decoder.unused_data)
                    response._decoder = None

                # Now, go to _on_response.
                self._want_close = False
                self._no_process = False
                self._on_response()
                return

        elif not self._want_close:
            # If it's not an expected close, check for an active request and
            # error it.
            self._want_close = False
            if self._requests:
                request = self._requests[0]
                self._no_process = False
                self._do_error(RequestClosed("The server closed the "
                                             "connection."))
                return

        # Keep processing, if needed.
        self._stream = None
        if self._no_process:
            self._no_process = False
        else:
            self._process()


    def _do_error(self, err):
        """
        There was some kind of exception. Close the stream, report it, and then
        keep processing.
        """
        self._want_close = True
        self._no_process = True
        self._stream.close(False)
        self._stream = None
        if not self._requests:
            return

        # Pop off the request that had an error, and clear its timeout.
        request = self._requests.pop(0)
        if request._timeout_timer:
            request._timeout_timer()

        self._safely_call(request.session.on_error, request.response, err)

        # Keep processing, if needed.
        self._process()


    def _read_headers(self, data):
        """
        Read the headers of an HTTP response from the socket into the current
        HTTPResponse object, and prepare to read the body. Or, if necessary,
        follow a redirect.
        """
        if not self._requests:
            return
        request = self._requests[0]
        response = request.response
        self._reset_timer()

        ind = data.find(CRLF)
        if ind == -1:
            initial_line = data
            data = ''
        else:
            initial_line = data[:ind]
            data = data[ind+2:]
        try:
            http_version, status, status_text = initial_line.split(' ', 2)
            status = int(status)
            if not http_version.startswith('HTTP/'):
                self._do_error(MalformedResponse("Invalid HTTP protocol "
                                                 "version %r." % http_version))
                return
        except ValueError:
            self._do_error(MalformedResponse("Invalid status line."))
            return

        # Parse the headers.
        headers = read_headers(data) if data else {}

        # Store what we've got so far on the response.
        response.http_version = http_version
        response.status_code = status
        response.status_text = status_text
        response.headers = headers

        # Load any cookies.
        if 'Set-Cookie' in headers:
            if not response.cookies:
                request.cookies = Cookie.SimpleCookie()
                response.cookies = request.session.cookies = request.cookies

            cookies = headers['Set-Cookie']
            if not isinstance(cookies, list):
                cookies = [cookies]
            for val in cookies:
                val_jar = Cookie.SimpleCookie()
                val_jar.load(val)
                for key in val_jar:
                    morsel = val_jar[key]
                    if not morsel['domain']:
                        morsel['domain'] = _hostname(request.url)
                    response.cookies.load(morsel.output(None, ''))

        # Are we dealing with a HEAD request?
        if request.method == 'HEAD':
            # Just be done.
            self._on_response()
            return

        # Do the on_headers callback.
        continue_request = self._safely_call(request.session.on_headers,
                                             response)
        if continue_request is False:
            # Abort the connection now.
            self._requests.pop(0)
            self._want_close = True
            self._no_process = False
            self._stream.close(False)
            return

        # Is there a Content-Length header?
        if 'Content-Length' in headers:
            response.length = int(headers['Content-Length'])
            response.remaining = response.length

            # If there's no length, immediately we've got a response.
            if not response.remaining:
                self._on_response()
                return

            self._stream.on_read = self._read_body
            self._stream.read_delimiter = min(CHUNK_SIZE, response.remaining)

        # What about Transfer-Encoding?
        elif 'Transfer-Encoding' in headers:
            if headers['Transfer-Encoding'] != 'chunked':
                self._do_error(MalformedResponse(
                                "Unable to handle Transfer-Encoding %r." %
                                headers['Transfer-Encoding']))
                return

            response.length = 0
            self._stream.on_read = self._read_chunk_head
            self._stream.read_delimiter = CRLF

        # Is this not a persistent connection? If so, read the whole body.
        elif not response._keep_alive:
            response.length = 0
            response.remaining = 0
            self._reading_forever = True
            self._stream.on_read = self._read_forever

            # We have to have a read_delimiter of None, otherwise our data
            # gets deleted when the connection is closed.
            self._stream.read_delimiter = None

        # There must not be a body, so go ahead and be done.
        else:
            # We've got a response.
            self._on_response()
            return

        # Do we have any Content-Encoding?
        if 'Content-Encoding' in headers:
            encoding = headers['Content-Encoding']
            if not encoding in CONTENT_ENCODING:
                self._do_error(MalformedResponse(
                           "Unable to handle Content-Encoding %r." % encoding))
                return
            response._decoder = CONTENT_ENCODING[encoding]()


    def _on_response(self):
        """
        A response has been completed. Send it on through.
        """
        if not self._requests:
            return
        request = self._requests.pop(0)
        response = request.response

        # Do we have Connection: close?
        if not response._keep_alive:
            self._want_close = True
            self._no_process = True
            self._stream.close(False)
            self._stream = None

        # Clear the existing timer.
        if request._timeout_timer:
            request._timeout_timer()

        # Check for a status code handler.
        handler = getattr(response, 'handle_%d' % response.status_code, None)
        if handler:
            response = self._safely_call(handler, self)
            if not response:
                return

        self._safely_call(request.session.on_response, response)
        # Keep processing, if needed.
        self._process()


    ##### Length-Based Responses ##############################################

    def _read_forever(self, data):
        """
        Read until the connection closes.
        """
        if not self._requests:
            return
        request = self._requests[0]
        response = request.response
        self._reset_timer()

        # Make note of how many bytes we've received.
        response.length += len(data)

        # Decode the received data.
        if response._decoder:
            data = response._decoder.decompress(data)

        # Now, store that.
        response._receive(data)

        # Do a progress.
        self._safely_call(request.session.on_progress, response,
                          response.length, 0)


    def _read_body(self, data):
        """
        Add the data we received to the response body, doing any necessary
        decompression and character set nonsense.
        """
        if not self._requests:
            return
        request = self._requests[0]
        response = request.response
        self._reset_timer()

        # Make note of how many bytes we've received.
        response.remaining -= len(data)
        self._stream.read_delimiter = min(CHUNK_SIZE, response.remaining)
        finished = not response.remaining and not response.remaining is False

        # Decode the received data.
        if response._decoder:
            data = response._decoder.decompress(data)
            if finished:
                data += response._decoder.flush()
                data += response._decoder.unused_data
                response._decoder = None

        # Now, store that.
        response._receive(data)

        # Do a progress.
        self._safely_call(request.session.on_progress, response,
                          response.length-response.remaining, response.length)

        # Do a finished?
        if finished:
            self._on_response()


    ##### Chunked Responses ###################################################

    def _read_additional_headers(self, data):
        """ Read additional headers for the response. """
        if not self._requests:
            return
        request = self._requests[0]
        response = request.response
        self._reset_timer()

        # Build the additional headers data.
        if data:
            response._additional_headers += data + CRLF
            return

        # We're done, so parse those.
        headers = read_headers(response._additional_headers)
        del response._additional_headers

        # Extend the original headers.
        for key, val in headers.iteritems():
            if not key in response.headers:
                response.headers[key] = val
            else:
                if not isinstance(response.headers[key], list):
                    response.headers[key] = [response.headers[key]]
                if isinstance(val, (tuple,list)):
                    response.headers[key].extend(val)
                else:
                    response.headers[key].append(val)

        # Finally, we can handle it.
        self._on_response()


    def _read_chunk_head(self, data):
        """ Read a chunk header. """
        if not self._requests:
            return
        request = self._requests[0]
        response = request.response
        self._reset_timer()

        # Chop off any chunk extension data. We don't care about it.
        if ';' in data:
            data, ext = data.split(';', 1)

        # Get the length of the chunk.
        length = int(data.strip(), 16)

        if not length:
            # We're finished! Flush the decompressor if we have one, and move
            # on to the additional headers.
            if response._decoder:
                response._receive(response._decoder.flush())
                response._receive(response._decoder.unused_data)
                response._decoder = None

            self._stream.on_read = self._read_additional_headers
            response._additional_headers = ''
            self._stream.read_delimiter = CRLF

        else:
            # Read the new chunk.
            length += 2
            self._stream.on_read = self._read_chunk_body
            response.remaining = length
            self._stream.read_delimiter = min(CHUNK_SIZE, length)


    def _read_chunk_body(self, data):
        """ Read a chunk body. """
        if not self._requests:
            return
        request = self._requests[0]
        response = request.response
        self._reset_timer()

        # Make note of how many bytes we've received.
        bytes = len(data)
        response.remaining -= bytes
        response.length += bytes
        self._stream.read_delimiter = min(CHUNK_SIZE, response.remaining)

        # Pass the data through our decoder.
        data = data[:-2]
        if response._decoder:
            data = response._decoder.decompress(data)

        # Store this data.
        response._receive(data)

        # Do a progress event.
        self._safely_call(request.session.on_progress, response,
                          response.length, 0)

        # If we're finished with this chunk, read a new header.
        if not response.remaining:
            self._stream.on_read = self._read_chunk_head
            self._stream.read_delimiter = CRLF


###############################################################################
# Session Class
###############################################################################

class Session(object):
    """
    The Session class is the heart of the HTTP client, making it easy to share
    state between multiple requests, and enabling the use of ``with`` syntax.
    They're responsible for determining everything about a request before
    handing it back to :class:`HTTPClient` to be executed.

    ===============  ==========  ============
    Argument         Default     Description
    ===============  ==========  ============
    client                       The :class:`HTTPClient` instance this Session is associated with.
    on_response                  *Optional.* A callable that will handle any received responses, rather than the HTTPClient's own :func:`on_response` method.
    on_headers                   *Optional.* A callable for when response headers have been received.
    on_progress                  *Optional.* A callable for progress notifications.
    on_ssl_error                 *Optional.* A callable responsible for handling SSL verification errors, if ``verify_ssl`` is True.
    on_error                     *Optional.* A callable that will handle any errors that occur.
    timeout          ``30``      *Optional.* The time to wait, in seconds, of no activity to allow before timing out.
    max_redirects    ``10``      *Optional.* The maximum number of times to follow a server-issued redirect.
    keep_alive       ``True``    *Optional.* Whether or not a single connection will be reused for multiple requests.
    auth             ``None``    *Optional.* An instance of :class:`AuthBase` for authenticating requests to the server.
    headers          ``None``    *Optional.* A dictionary of default headers to send with requests.
    verify_ssl       ``False``   *Optional.* Whether or not to attempt to check the certificate of the remote secure server against its hostname.
    ssl_options      ``None``    *Optional.* Options to use when initializing SSL. See :func:`Stream.startSSL` for more.
    ===============  ==========  ============
    """

    def __init__(self, client, on_response=None, on_headers=None,
                 on_progress=None, on_ssl_error=None, on_error=None,
                 timeout=None, max_redirects=None, keep_alive=None, auth=None,
                 headers=None, cookies=None, verify_ssl=None,
                 ssl_options=None):
        """ Initialize the Session. """
        # Store the client and parent.
        if isinstance(client, Session):
            self.parent = parent = client
            self.client = client = self.parent.client
        else:
            self.client = client
            parent = client._sessions[-1] if client._sessions else None
            self.parent = parent

        # Setup our default settings.
        if on_response is None:
            on_response = parent.on_response if parent else client.on_response
        if on_headers is None:
            on_headers = parent.on_headers if parent else client.on_headers
        if on_progress is None:
            on_progress = parent.on_progress if parent else client.on_progress
        if on_ssl_error is None:
            if parent:
                on_ssl_error = parent.on_ssl_error
            else:
                on_ssl_error = client.on_ssl_error
        if on_error is None:
            on_error = parent.on_error if parent else client.on_error
        if timeout is None:
            timeout = parent.timeout if parent else 30
        if max_redirects is None:
            max_redirects = parent.max_redirects if parent else 10
        if keep_alive is None:
            keep_alive = parent.keep_alive if parent else True
        if auth is None:
            auth = parent.auth if parent else None
        if headers is None:
            headers = {}
            if parent and parent.headers:
                headers.update(parent.headers)
        if verify_ssl is None:
            verify_ssl = parent.verify_ssl if parent else False
        if ssl_options is None:
            ssl_options = parent.ssl_options if parent else None

        # Do some logic about SSL verification.
        if verify_ssl:
            if not ssl_options:
                # This logic comes from requests.
                loc = None
                if verify_ssl is not True:
                    loc = verify_ssl
                if not loc:
                    loc = os.environ.get('PANTS_CA_BUNDLE')
                if not loc:
                    loc = os.environ.get('CURL_CA_BUNDLE')
                if not loc:
                    try:
                        import certifi
                        loc = certifi.where()
                    except ImportError:
                        pass
                if not loc:
                    raise RuntimeError("Cannot find certificates for SSL "
                                       "verification.")
                ssl_options = {'ca_certs': loc, 'cert_reqs': ssl.CERT_REQUIRED}

            # Make sure we've got backports.ssl_match_hostname
            if not match_hostname:
                raise RuntimeError("Cannot verify SSL certificates without "
                                   "the package backports.ssl_match_hostname.")

        # Ensure the cookies are a cookiejar.
        if cookies is None:
            cookies = Cookie.SimpleCookie()
        elif isinstance(cookies, dict):
            cookies = Cookie.SimpleCookie(cookies)

        # Store our settings now.
        self.on_response = on_response
        self.on_headers = on_headers
        self.on_progress = on_progress
        self.on_ssl_error = on_ssl_error
        self.on_error = on_error
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.keep_alive = keep_alive
        self.auth = auth
        self.headers = headers
        self.cookies = cookies
        self.verify_ssl = verify_ssl
        self.ssl_options = ssl_options


    ##### Session Generation ##################################################

    def session(self, *args, **kwargs):
        """ Create a new session. See :class:`Session` for details. """
        return Session(self, *args, **kwargs)


    ##### Request Making ######################################################

    def request(self, method, url, params=None, data=None, headers=None,
                cookies=None, files=None, auth=None, timeout=None,
                max_redirects=None, keep_alive=None):
        """
        Begin a request.

        ==============  ============
        Argument        Description
        ==============  ============
        method          The HTTP method of the request.
        url             The URL to request.
        params          *Optional.* A dictionary or string of query parameters to add to the request.
        data            *Optional.* A dictionary or string of content to send in the request body.
        headers         *Optional.* A dictionary of headers to send with the request.
        cookies         *Optional.* A dictionary or CookieJar of cookies to send with the request.
        files           *Optional.* A dictionary of file-like objects to upload with the request.
        auth            *Optional.* An instance of :class:`AuthBase` to use to authenticate the request.
        timeout         *Optional.* The time to wait, in seconds, of no activity to allow before timing out.
        max_redirects   *Optional.* The maximum number of times to follow a server-issued redirect.
        keep_alive      *Optional.* Whether or not to reuse the connection for multiple requests.
        ==============  ============
        """
        method = str(method).upper()

        # Parse the URL.
        parts = urlparse.urlparse(url)
        if not parts.scheme in ("http", "https"):
            raise ValueError("HTTPClient unable to serve request with scheme "
                             "%r." % parts.scheme)

        # Get default values from the session if necessary
        if timeout is None:
            timeout = self.timeout
        if max_redirects is None:
            max_redirects = self.max_redirects
        if keep_alive is None:
            keep_alive = self.keep_alive
        if auth is None:
            auth = self.auth
        if cookies is None:
            cookies = self.cookies
        elif isinstance(cookies, dict):
            cookies = Cookie.SimpleCookie(cookies)

        # Build the headers.
        if not headers:
            headers = {}

        # Update with all the default headers.
        for key in self.headers:
            if not key in headers:
                headers[key] = self.headers[key]

        # Add an extra header or two.
        if not 'Accept-Encoding' in headers:
            headers['Accept-Encoding'] = 'deflate, gzip'

        if not 'Date' in headers:
            headers['Date'] = date(datetime.utcnow())

        if not 'Host' in headers:
            headers['Host'] = _hostname(parts)
            port = _port(parts)
            if port:
                headers['Host'] += ':%d' % port

        if not 'User-Agent' in headers:
            headers['User-Agent'] = USER_AGENT

        if not 'Connection' in headers and not keep_alive:
            headers['Connection'] = 'close'

        # Determine the Content-Type of the request body.
        if files:
            hdr = headers.get('Content-Type')
            if hdr and not hdr.startswith("multipart/form-data"):
                raise ValueError("Cannot transmit files with Content-Type "
                                 "%r." % hdr)
            elif not hdr:
                headers['Content-Type'] = 'multipart/form-data'
        elif not 'Content-Type' in headers and data:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'

        # Construct the actual request body. This is a mess.
        if 'Content-Type' in headers:
            hdr = headers['Content-Type']
            if isinstance(data, bytes):
                body = [data]
                length = len(data)
            elif hdr.startswith('multipart/form-data'):
                ind = hdr.find('boundary=')
                if ind != -1:
                    boundary = hdr[ind+9:]
                else:
                    boundary = None

                boundary, body = encode_multipart(data or {}, files, boundary)
                headers['Content-Type'] = 'multipart/form-data; boundary=%s' \
                                            % boundary
                length = 0
                for item in body:
                    if isinstance(item, basestring):
                        length += len(item)
                    else:
                        item.seek(0, 2)
                        length += item.tell()
            elif hdr == 'application/x-www-form-urlencoded':
                if isinstance(data, dict):
                    body = [urllib.urlencode(data or {}, True)]
                    length = len(body[0])
                elif not data:
                    body = []
                    length = 0
                else:
                    body = [data]
                    length = len(body[0])
            else:
                raise ValueError("Unknown Content-Type %r." % hdr)
            headers['Content-Length'] = length
        else:
            body = None

        # Deal with the request parameters and the URL fragment.
        path = parts.path or '/'
        if params:
            new_params = urlparse.parse_qs(parts.query)
            for key, value in params.iteritems():
                if not key in new_params:
                    new_params[key] = []
                if isinstance(value, (tuple,list)):
                    new_params[key].extend(value)
                else:
                    new_params[key].append(value)

            # Update the URL parts.
            parts = parts._replace(query=urllib.urlencode(new_params,True))

        if parts.query:
            path += '?%s' % parts.query
        if parts.fragment:
            path += '#%s' % parts.fragment

        # Build our request.
        request = HTTPRequest(self, method, path, parts, headers, cookies,
                                body, timeout, max_redirects, keep_alive, auth)

        # Now, send it back to the client.
        self.client._requests.append(request)
        if not self.client._processing:
            self.client._process()

        # Not sure what you'll do with this, but there you have it.
        return request


    def delete(self, url, **kwargs):
        """ Begin a DELETE request. See :func:`request` for more details. """
        return self.request("DELETE", url, **kwargs)


    def get(self, url, params=None, **kwargs):
        """ Begin a GET request. See :func:`request` for more details. """
        return self.request("GET", url, params=params, **kwargs)


    def head(self, url, params=None, **kwargs):
        """ Begin a HEAD request. See :func:`request` for more details. """
        return self.request("HEAD", url, params=params, **kwargs)


    def options(self, url, **kwargs):
        """ Begin an OPTIONS request. See :func:`request` for more details. """
        return self.request("OPTIONS", url, **kwargs)


    def patch(self, url, data=None, **kwargs):
        """ Begin a PATCH request. See :func:`request` for more details. """
        return self.request("PATCH", url, data=data, **kwargs)


    def post(self, url, data=None, files=None, **kwargs):
        """ Begin a POST request. See :func:`request` for more details. """
        return self.request("POST", url, data=data, files=files, **kwargs)


    def put(self, url, data=None, **kwargs):
        """ Begin a PUT request. See :func:`request` for more details. """
        return self.request("PUT", url, data=data, **kwargs)


    def trace(self, url, **kwargs):
        """ Begin a TRACE request. See :func:`request` for more details. """
        return self.request("TRACE", url, **kwargs)


    ##### Context #############################################################

    def __enter__(self):
        self.client._sessions.append(self)
        return self


    def __exit__(self, *args):
        self.client._sessions.pop()


###############################################################################
# HTTPRequest Class
###############################################################################

class HTTPRequest(object):
    """ A very basic structure for storing HTTP request information. """

    response = None
    _timeout_timer = None

    def __init__(self, session, method, path, url, headers, cookies, body,
                 timeout, max_redirects, keep_alive, auth):
        self.session = session
        self.method = method
        self.path = path
        self.url = url
        self.headers = headers
        self.cookies = cookies
        self.body = body
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.keep_alive = keep_alive
        self.auth = auth


    def __repr__(self):
        return '<%s ["%s://%s%s"] at 0x%X>' % (
            self.__class__.__name__,
            self.url.scheme,
            self.url.netloc,
            self.path,
            id(self)
            )


###############################################################################
# HTTPResponse Class
###############################################################################

class HTTPResponse(object):
    """
    The HTTPResponse class represents a single HTTPResponse, and has all the
    available information about a response, including the redirect history and
    the original HTTPRequest.
    """

    total = None
    remaining = None
    http_version = None
    status_code = None
    status_text = None
    cookies = None
    headers = None

    _body_file = None
    _decoder = None
    _encoding = None

    def __init__(self, request):
        """ Initialize from the provided request. """
        self.request = request
        self.history = []

        # Store stuff about us.
        self.method = request.method
        self.url = urlparse.urlunparse(request.url)
        self.path = request.path

        # Make sure we're the request's response.
        if self.request.response:
            self.history.extend(self.request.response.history)
            self.history.insert(0, self.request.response)
        self.request.response = self

        # Set cookies.
        self.cookies = self.request.session.cookies


    @property
    def status(self):
        """ The status code and status text as a string. """
        if not self.status_code:
            return None
        if not self.status_text:
            return str(self.status_code)
        return "%d %s" % (self.status_code, self.status_text)


    def __repr__(self):
        return "<%s [%s] at 0x%X>" % (
            self.__class__.__name__,
            self.status,
            id(self)
            )


    @property
    def _keep_alive(self):
        conn = self.headers.get('Connection', '').lower()
        if self.http_version == 'HTTP/1.0':
            return conn == 'keep-alive'
        return conn != 'close'

    ##### Body Management #####################################################

    @property
    def encoding(self):
        """
        This is the detected character encoding of the response. You can also
        set this to a specific character set to have :attr:`text` decoded
        properly.

        Pants will attempt to fill this value from the Content-Type response
        header. If no value was available, it will be ``None``.
        """
        if not self._encoding:
            # Time to play guess the encoding! We don't try that hard.
            cset = self.headers.get('Content-Type').partition('charset=')[-1]
            if not cset:
                cset = None
            self._encoding = cset
        return self._encoding

    @encoding.setter
    def encoding(self, val):
        # Use codecs.lookup to make sure it's a valid way to decode text.
        if val is not None:
            codecs.lookup(val)
        self._encoding = val


    @property
    def text(self):
        """
        The content of the response, after being decoded into unicode with
        :attr:`encoding`. Be careful when using this with large responses, as
        it will load the entire response into memory. ``None`` if no data has
        been received.

        If :attr:`encoding` is ``None``, this will default to ``UTF-8``.

        """
        raw = self.content
        if not raw:
            return raw

        encoding = self.encoding
        if not encoding:
            encoding = 'utf-8'

        return raw.decode(encoding)


    def json(self, **kwargs):
        """
        The content of the response, having been interpreted as JSON. This
        uses the value of :attr:`encoding` if possible. If :attr:`encoding`
        is not set, it will default to ``UTF-8``.

        Any provided keyword arguments will be passed to :func:`json.loads`.

        """
        if not 'encoding' in kwargs:
            kwargs['encoding'] = self.encoding

        raw = self.content
        if not raw:
            return raw

        return json.loads(raw, **kwargs)


    @property
    def file(self):
        """
        The content of the response as a :class:`tempfile.SpooledTemporaryFile`.
        Pants uses temporary files to decrease memory usage for
        large responses. ``None`` if no data has been received.
        """
        return self._body_file

    # requests compatibility
    raw = file
    stream = True


    @property
    def content(self):
        """
        The content of the response as a byte string. Be careful when using
        this with large responses, as it will load the entire response into
        memory. ``None`` if no data has been received.
        """
        if not self._body_file:
            return None
        f = self._body_file._file
        if hasattr(f, 'getvalue'):
            return f.getvalue()

        current_pos = f.tell()
        f.seek(0)
        out = f.read()
        f.seek(current_pos)
        return out


    def iter_content(self, chunk_size=1, decode_unicode=False):
        """
        Iterate over the content of the response. Using this, rather than
        :attr:`content` or :attr:`text` can prevent the loading of large
        responses into memory in their entirety.

        ===============  ========  ============
        Argument         Default   Description
        ===============  ========  ============
        chunk_size       ``1``     The number of bytes to read at once.
        decode_unicode   False     Whether or not to decode the bytes into unicode using the response's :attr:`encoding`.
        ===============  ========  ============
        """
        f = self._body_file
        if not f:
            return

        if decode_unicode:
            codec = self.encoding or 'utf-8'
            decoder = codecs.getincrementaldecoder(codec)(errors='replace')
        else:
            decoder = None

        pos = 0
        while True:
            f.seek(pos)
            data = f.read(chunk_size)

            pos += len(data)
            if decoder:
                data = decoder.decode(data)

            if not data:
                if decoder:
                    final = decoder.decode(b'', final=True)
                    if final:
                        yield final
                return

            yield data


    def iter_lines(self, chunk_size=512, decode_unicode=False):
        """
        Iterate over the content of the response, one line at a time. By
        using this rather than :attr:`content` or :attr:`text` you can
        prevent loading of the entire response into memory. The two arguments
        to this method are passed directly to :meth:`iter_content`.
        """
        # This method's implementation shamelessly copied from requests.
        pending = None
        for chunk in self.iter_content(chunk_size=chunk_size,
                                       decode_unicode=decode_unicode):
            if pending:
                chunk = pending + chunk

            lines = chunk.splitlines()
            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                pending = lines.pop()
            else:
                pending = None

            for line in lines:
                yield line

        if pending is not None:
            yield pending

    # Let people easily iterate over lines.
    __iter__ = iter_lines


    def _receive(self, data):
        if not self._body_file:
            self._init_body()
        self._body_file.write(data)


    def _init_body(self):
        self._body_file = tempfile.SpooledTemporaryFile(MAX_MEMORY_SIZE)


    ##### Status Code Handlers ################################################

    def handle_301(self, client):
        """ Handle the different redirect codes. """
        request = self.request
        if not request.max_redirects or not 'Location' in self.headers:
            return self

        # Get some useful things.
        status = self.status_code
        method = self.method
        body = request.body
        location = self.headers['Location']
        log.debug("Redirecting request %r to %r." % (request, location))

        # Update the request and send it again.
        try:
            # Update the URL.
            location = urlparse.urljoin(urlparse.urlunparse(request.url),
                                        location)
            parts = urlparse.urlparse(location)
            if not parts.scheme in ("http", "https"):
                raise MalformedResponse

            # Do special stuff for certain codes.
            if status == 301 and not method in ('GET', 'HEAD'):
                raise MalformedResponse
            elif status in (302, 303):
                method = 'GET'
                body = None

            host = _hostname(parts)
            port = _port(parts)
            if port:
                host += ':%d' % port

            # Update the request.
            request.url = parts
            request.path = parts.path or '/'
            request.method = method
            request.body = body
            request.headers['Host'] = host
            request.max_redirects -= 1

            # Make the new response, process it, and return.
            HTTPResponse(request)
            client._requests.insert(0, request)
            client._process()
            return
        except MalformedResponse:
            return self

    handle_302 = handle_303 = handle_307 = handle_301


    def handle_401(self, client):
        """ Handle authorization, if we know how. """
        request = self.request
        if not isinstance(request.auth, (list,tuple)) or \
                not 'WWW-Authenticate' in self.headers:
            return self

        auth_type, options = self.headers['WWW-Authenticate'].split(' ',1)
        if not auth_type.lower() in ('digest', 'basic'):
            return self

        # If it's basic, do that.
        if auth_type.lower() == 'basic':
            request.auth = BasicAuth(*request.auth)
        else:
            # TODO: Write Digest authentication.
            # request.auth = DigestAuth(*request.auth)
            return self

        # Now, resend.
        HTTPResponse(request)
        client._requests.insert(0, request)
        client._process()

########NEW FILE########
__FILENAME__ = server
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
``pants.http.server`` implements a lean HTTP server on top of Pants with
support for most of `HTTP/1.1 <http://www.w3.org/Protocols/rfc2616/rfc2616.html>`_,
including persistent connections. The HTTP server supports secure connections,
efficient transfer of files, and proxy headers. Utilizing the power of Pants,
it becomes easy to implement other protocols on top of HTTP such as
:mod:`WebSockets <pants.http.websocket>`.

The Server
==========

:class:`HTTPServer` is a subclass of :class:`pants.server.Server` that
implements the `HTTP/1.1 protocol <http://www.w3.org/Protocols/rfc2616/rfc2616.html>`_
via the class :class:`HTTPConnection`. Rather than specifying a custom
``ConnectionClass``, you implement your behavior with a ``request_handler``.
There will be more on request handlers below. For now, a brief example::

    from pants.http import HTTPServer
    from pants import Engine

    def my_handler(request):
        request.send_response("Hello World.")

    server = HTTPServer(my_handler)
    server.listen()
    Engine.instance().start()

In addition to specifying the request handler, there are a few other ways to
configure ``HTTPServer``.


Using HTTPServer Behind a Proxy
===============================

:class:`HTTPServer` has support for a few special HTTP headers that can be set
by proxy servers (notably ``X-Forwarded-For`` and ``X-Forwarded-Proto``) and it
can use ``X-Sendfile`` headers when sending files to allow the proxy server to
take care of static file transmission.

When creating your :class:`HTTPServer` instance, set ``xheaders`` to ``True``
to allow the server to automatically use the headers ``X-Real-IP``,
``X-Forwarded-For``, and ``X-Forwarded-Proto`` if they exist to set the
:class:`HTTPRequest`'s ``remote_ip`` and ``scheme``.

Sendfile is a bit more complex, with three separate variables for configuration.
To enable the ``X-Sendfile`` header, set ``sendfile`` to ``True`` when creating
your :class:`HTTPServer` instance. Alternatively, you may set it to a string to
have Pants use a string other than ``X-Sendfile`` for the header's name.

HTTPServer's ``sendfile_prefix`` allows you to set a prefix for the path written
to the ``X-Sendfile`` header. This is useful when using Pants behind nginx.

HTTPServer's ``file_root`` allows you to specify a root directory from which
static files should be located. This root path will be stripped from the file
paths before they're written to the ``X-Sendfile`` header. If ``file_root`` is
not set, the current working directory (as of the time :func:`HTTPRequest.send_file`
is called) will be used.

.. code-block:: python

    def my_handler(request):
        request.send_file('/srv/files/example.jpg')

    server = HTTPServer(my_handler, sendfile=True, sendfile_prefix='/_static/',
                        file_root='/srv/files')
    server.listen()

The above code would result in an HTTP response similar to:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: image/jpeg
    Content-Length: 0
    X-Sendfile: /_static/example.jpg

Your proxy server would then be required to detect the ``X-Sendfile`` header
in that response and insert the appropriate content and headers.

.. note::

    The sendfile API is quite rough at this point, and is most likely going to
    be changed in future versions. It is possible to manually set the
    appropriate headers to handle sending files yourself if you require more
    control over the process.


Request Handlers
================

A request handler is a callable Python object, typically either a function or a
class instance with a defined ``__call__`` method. Request handlers are passed
an instance of :class:`HTTPRequest` representing the current request.

HTTPRequest instances contain all of the information that was sent with an
incoming request. The instances also have numerous methods for building
responses.

.. note::

    It is *not* required to finish responding to a request within the
    request handler.

Please see the documentation for the :class:`HTTPRequest` class below for more
information on what you can do.
"""

###############################################################################
# Imports
###############################################################################

import base64
import Cookie
import json
import mimetypes
import os
import pprint
import sys

from datetime import datetime, timedelta
from urlparse import parse_qsl

if sys.platform == "win32":
    from time import clock as time
else:
    from time import time

from pants.stream import Stream
from pants.server import Server

from pants.http.utils import BadRequest, CRLF, date, DOUBLE_CRLF, \
    generate_signature, HTTP, HTTPHeaders, log, parse_multipart, read_headers, \
    SERVER, WHITESPACE, parse_date

###############################################################################
# Exports
###############################################################################

__all__ = (
    "HTTPConnection", "HTTPRequest", "HTTPServer"
)

###############################################################################
# HTTPConnection Class
###############################################################################

class HTTPConnection(Stream):
    """
    This class implements the HTTP protocol on top of Pants. It specifically
    processes incoming HTTP requests and constructs an instance of
    :class:`HTTPRequest` before passing that instance to the associated
    :class:`HTTPServer`'s request handler.

    Direct interaction with this class is typically unnecessary, only becoming
    useful when implementing another protocol on top of HTTP, such as
    :mod:`WebSockets <pants.http.websocket>` or performing some other action
    that requires direct control over the underlying socket.
    """
    def __init__(self, *args, **kwargs):
        Stream.__init__(self, *args, **kwargs)

        # Request State Storage
        self.current_request = None
        self._finished = False

        # Read the initial request.
        self._await_request()

    ##### I/O Methods #########################################################

    def finish(self):
        """
        This method should be called when the response to the current
        request has been completed, in preparation for either closing the
        connection or attempting to read a new request from the connection.

        This method is called automatically when you use the method
        :meth:`HTTPRequest.finish`.
        """
        self.flush()
        self._finished = True
        if not self._send_buffer:
            self._request_finished()

    ##### Public Event Handlers ###############################################

    def on_write(self):
        if self._finished:
            self._request_finished()

    def on_close(self):
        # Clear the on_read method to ensure that the connection is collected
        # immediately.
        del self.on_read

    ##### Internal Event Handlers #############################################

    def _await_request(self):
        """
        Sets the read handler and read delimiter to prepare to read an HTTP
        request from the socket.
        """
        self.on_read = self._read_header
        self.read_delimiter = DOUBLE_CRLF

    def _request_finished(self):
        """
        If keep-alive is supported, and the server configuration allows, then
        the connection will be prepared to read another request. Otherwise, the
        connection will be closed.
        """
        disconnect = True

        if self.server.keep_alive:
            headers = self.current_request.headers
            connection = headers.get('Connection','').lower()

            if self.current_request.protocol == 'HTTP/1.1':
                disconnect = connection == 'close'

            elif 'Content-Length' in headers or \
                    self.current_request.method in ('HEAD','GET'):
                disconnect = connection != 'keep-alive'

        self.current_request = None
        self._finished = False

        if disconnect:
            self.on_read = None
            self.close()
        else:
            self._await_request()

    def _read_header(self, data):
        """
        Read the headers of an HTTP request from the socket, and the request
        body if necessary, into a new HTTPRequest instance. Then, assuming that
        the headers are valid, call the server's request handler.
        """
        try:
            initial_line, _, data = data.partition(CRLF)

            try:
                method, url, protocol = WHITESPACE.split(initial_line) #.split(' ')
            except ValueError:
                raise BadRequest('Invalid HTTP request line.')

            if not protocol.startswith('HTTP/'):
                raise BadRequest('Invalid HTTP protocol version.',
                                 code='505 HTTP Version Not Supported')

            # Parse the headers.
            if data:
                headers = read_headers(data)
            else:
                headers = {}

            # If we're secure, we're HTTPs.
            if self.ssl_enabled:
                scheme = 'https'
            else:
                scheme = 'http'

            # Construct an HTTPRequest object.
            self.current_request = request = HTTPRequest(self,
                method, url, protocol, headers, scheme)

            # If we have a Content-Length header, read the request body.
            length = headers.get('Content-Length')
            if length:
                if not isinstance(length, int):
                    raise BadRequest(
                        'Provided Content-Length (%r) is invalid.' % length
                        )
                elif length > self.server.max_request:
                    raise BadRequest((
                        'Provided Content-Length (%d) larger than server '
                        'limit %d.'
                        ) % (length, self.server.max_request),
                        code='413 Request Entity Too Large')

                if headers.get('Expect','').lower() == '100-continue':
                    self.write("%s 100 (Continue)%s" % (
                        protocol, DOUBLE_CRLF))

                # Await a request body.
                self.on_read = self._read_request_body
                self.read_delimiter = length
                return

        except BadRequest as err:
            log.info('Bad request from %r: %s',
                self.remote_address, err)
            
            self.write('HTTP/1.1 %s%s' % (err.code, CRLF))
            if err.message:
                self.write('Content-Type: text/html%s' % CRLF)
                self.write('Content-Length: %d%s' % (len(err.message),
                                                     DOUBLE_CRLF))
                self.write(err.message)
            else:
                self.write(CRLF)
            self.close()
            return

        except Exception as err:
            log.info('Exception handling request from %r: %s',
                self.remote_address, err)

            self.write('HTTP/1.1 500 Internal Server Error%s' % CRLF)
            self.write('Content-Length: 0%s' % DOUBLE_CRLF)
            self.close()
            return

        try:
            # Call the request handler.
            self.server.request_handler(request)
        except Exception:
            log.exception('Error handling HTTP request.')
            if request._started:
                self.close(False)
            else:
                request.send_response("500 Internal Server Error", 500)
                self.close()

    def _read_request_body(self, data):
        """
        Read a request body from the socket, parse it, and then call the
        request handler for the current request.
        """
        request = self.current_request
        request.body = data

        try:
            content_type = request.headers.get('Content-Type', '')
            if request.method in ('POST','PUT'):
                if content_type.startswith('application/x-www-form-urlencoded'):
                    post = request.post
                    for key, val in parse_qsl(data, False):
                        if key in post:
                            if isinstance(post[key], list):
                                post[key].append(val)
                            else:
                                post[key] = [post[key], val]
                        else:
                            post[key] = val

                elif content_type.startswith('multipart/form-data'):
                    for field in content_type.split(';'):
                        key, _, value = field.strip().partition('=')
                        if key == 'boundary' and value:
                            parse_multipart(request, value, data)
                            break
                    else:
                        log.warning('Invalid multipart/form-data.')

        except BadRequest as err:
            log.info('Bad request from %r: %s',
                self.remote_address, err)

            request.send_response(err.message, err.code)
            self.close()
            return

        try:
            self.server.request_handler(request)
        except Exception:
            log.exception('Error handling HTTP request.')
            if request._started:
                self.close(False)
            else:
                request.send_response("500 Internal Server Error", 500)
                self.close()

###############################################################################
# HTTPRequest Class
###############################################################################

class HTTPRequest(object):
    """
    Instances of this class represent single HTTP requests that an
    :class:`HTTPServer` has received. Such instances contain all the
    information needed to respond to the request, as well as the functions used
    to build the appropriate response.

    HTTPRequest uses :class:`bytes` rather than :class:`str` unless otherwise
    stated, as network communications take place as bytes.
    """

    def __init__(self, connection, method, url, protocol, headers=None,
                 scheme='http'):
        self.body       = ''
        self.connection = connection
        self.method     = method
        self.url        = url
        self.protocol   = protocol
        self._started   = False

        if headers is None:
            self.headers = {}
        else:
            self.headers = headers

        # X-Headers
        if connection.server.xheaders:
            remote_ip = self.headers.get('X-Real-IP')
            if not remote_ip:
                remote_ip = self.headers.get('X-Forwarded-For')
                if not remote_ip:
                    remote_ip = connection.remote_address
                    if not isinstance(remote_ip, basestring):
                        remote_ip = remote_ip[0]
                else:
                    remote_ip = remote_ip.partition(',')[0].strip()

            self.remote_ip = remote_ip
            self.scheme = self.headers.get('X-Forwarded-Proto', scheme)
        else:
            self.remote_ip = connection.remote_address
            if not isinstance(self.remote_ip, basestring):
                self.remote_ip = self.remote_ip[0]
            self.scheme   = scheme

        # Calculated Variables
        self.host       = self.headers.get('Host', '127.0.0.1')

        # Timing Information
        self._start     = time()
        self._finish    = None

        # Request Variables
        self.post       = {}
        self.files      = {}

        # Split the URL into usable information.
        self._parse_url()

    def __repr__(self):
        attr = ('protocol','method','scheme','host','url','path','time')
        attr = u', '.join(u'%s=%r' % (k,getattr(self,k)) for k in attr)
        return u'%s(%s, headers=%r)' % (
            self.__class__.__name__, attr, self.headers)

    def __html__(self):
        attr = ('protocol','method','remote_ip','scheme','host','url','path',
                'time')
        attr = u'\n    '.join(u'%-8s = %r' % (k,getattr(self,k)) for k in attr)

        out = u'<pre>%s(\n    %s\n\n' % (self.__class__.__name__, attr)

        for i in ('headers','get','post'):
            thing = getattr(self, i)
            if thing:
                if isinstance(thing, HTTPHeaders):
                    thing = dict(thing.iteritems())
                out += u'    %-8s = {\n %s\n        }\n\n' % (
                    i, pprint.pformat(thing, 8)[1:-1])
            else:
                out += u'    %-8s = {}\n\n' % i

        if hasattr(self, '_cookies') and self.cookies:
            out += u'    cookies  = {\n'
            for k in self.cookies:
                out += u'        %r: %r\n' % (k, self.cookies[k].value)
            out += u'        }\n\n'
        else:
            out += u'    cookies  = {}\n\n'

        out += u'    files    = %s\n)</pre>' % \
            pprint.pformat(self.files.keys(), 0)
        return out

    ##### Properties ##########################################################

    @property
    def cookies(self):
        """
        An instance of :class:`Cookie.SimpleCookie` representing the cookies
        received with this request. Cookies being sent to the client with the
        response are stored in :attr:`cookies_out`.
        """
        try:
            return self._cookies
        except AttributeError:
            self._cookies = cookies = Cookie.SimpleCookie()
            if 'Cookie' in self.headers:
                raw = self.headers['Cookie']
                if isinstance(raw, list):
                    for i in raw:
                        cookies.load(i)
                else:
                    cookies.load(raw)
            return self._cookies

    @property
    def cookies_out(self):
        """
        An instance of :class:`Cookie.SimpleCookie` to populate with cookies
        that should be sent with the response.
        """
        try:
            return self._cookies_out
        except AttributeError:
            self._cookies_out = cookies = Cookie.SimpleCookie()
            return cookies

    @property
    def full_url(self):
        """
        The full url for this request. This is created by combining the
        :attr:`scheme`, :attr:`host`, and the :attr:`url`.
        """
        return '%s://%s%s' % (self.scheme, self.host, self.url)

    @property
    def is_secure(self):
        """
        Whether or not the request was received via HTTPS.
        """
        return self.scheme.lower() == 'https'

    @property
    def time(self):
        """
        The amount of time that has elapsed since the request was received. If
        the request has been finished already, this will be the total time that
        elapsed over the duration of the request.
        """
        if self._finish is None:
            return time() - self._start
        return self._finish - self._start

    ##### Secure Cookies ######################################################

    def set_secure_cookie(self, name, value, expires=30*86400, **kwargs):
        """
        Set a timestamp on a cookie and sign it, ensuring that it can't be
        altered by the client. To use this, the :class:`HTTPServer`
        *must* have a :attr:`~HTTPServer.cookie_secret` set.

        Cookies set with this function may be read with
        :meth:`get_secure_cookie`.

        If the provided value is a dictionary, list, or tuple the value will
        be serialized into JSON and encoded as UTF-8. Unicode strings will
        also be encoded as UTF-8. Byte strings will be passed as is. All other
        types will result in a :class:`TypeError`.

        =========  ===========  ============
        Argument   Default      Description
        =========  ===========  ============
        name                    The name of the cookie to set.
        value                   The value of the cookie.
        expires    ``2592000``  *Optional.* How long, in seconds, the cookie should last before expiring. The default value is equivalent to 30 days.
        =========  ===========  ============

        Additional arguments, such as ``path`` and ``secure`` may be set by
        providing them as keyword arguments. The ``HttpOnly`` attribute will
        be set by default on secure cookies..
        """
        if isinstance(value, (dict, list, tuple)):
            value = b"j" + json.dumps(value)
        elif isinstance(value, unicode):
            value = b"u" + value.encode("utf-8")
        elif not isinstance(value, str):
            raise TypeError("Invalid value for secure cookie: %r" % (value,))
        else:
            value = b"s" + value

        ts = str(int(time()))
        v = base64.b64encode(value)
        signature = generate_signature(
                        self.connection.server.cookie_secret, expires, ts, v)

        value = "%s|%d|%s|%s" % (value, expires, ts, signature)

        self.cookies_out[name] = value
        m = self.cookies_out[name]
        m['httponly'] = True

        if kwargs:
            for k, v in kwargs.iteritems():
                if k.lower() == 'httponly' and not v:
                    del m['httponly']
                else:
                    m[k] = v

        m['expires'] = expires

    def get_secure_cookie(self, name):
        """
        Return the signed cookie with the key ``name`` if it exists and has a
        valid signature. Otherwise, return None.
        """
        if not name in self.cookies:
            return None

        try:
            value, expires, ts, signature = self.cookies[name].value.rsplit('|', 3)
            expires = int(expires)
            ts = int(ts)
        except (AttributeError, ValueError):
            return None

        v = base64.b64encode(str(value))
        sig = generate_signature(self.connection.server.cookie_secret, expires, ts, v)

        if signature != sig or ts < time() - expires or ts > time() + expires:
            return None

        # Process value
        vtype = value[:1]
        if vtype == b"j":
            value = json.loads(value[1:])
        elif vtype == b"u":
            value = value[1:].decode("utf-8")
        else:
            value = value[1:]

        return value

    ##### I/O Methods #########################################################

    def finish(self):
        """
        This function should be called when the response has been completed,
        allowing the associated :class:`HTTPConnection` to
        either close the connection to the client or begin listening for a new
        request.

        Failing to call this function will drastically reduce the performance
        of the HTTP server, if it will work at all.
        """
        self._finish = time()
        self.connection.finish()

    def send(self, data):
        """
        Write data to the client.

        =========  ============
        Argument   Description
        =========  ============
        data       A string of data to be sent to the client.
        =========  ============
        """
        self._started = True
        self.connection.write(data)

    def send_cookies(self, keys=None, end_headers=False):
        """
        Write any cookies associated with the request to the client. If any
        keys are specified, only the cookies with the specified keys will be
        transmitted. Otherwise, all cookies in :attr:`cookies_out` will be
        written to the client.

        This function is usually called automatically by send_headers.

        ============  ========  ============
        Argument      Default   Description
        ============  ========  ============
        keys          None      *Optional.* A list of cookie names to send.
        end_headers   False     *Optional.* If this is set to True, a double CRLF sequence will be written at the end of the cookie headers, signifying the end of the HTTP headers segment and the beginning of the response.
        ============  ========  ============
        """
        self._started = True
        if keys is None:
            if hasattr(self, '_cookies_out'):
                out = self.cookies_out.output()
            else:
                out = ''
        else:
            out = []
            for k in keys:
                if not k in self.cookies_out:
                    continue
                out.append(self.cookies_out[k].output())
            out = CRLF.join(out)

        if not out.endswith(CRLF):
            out += CRLF

        if end_headers:
            self.connection.write('%s%s' % (out, CRLF))
        else:
            self.connection.write(out)

    def send_file(self, path, filename=None, guess_mime=True, headers=None):
        """
        Send a file to the client, given the path to that file. This method
        makes use of ``X-Sendfile``, if the :class:`~pants.http.server.HTTPServer`
        instance is configured to send X-Sendfile headers.

        If ``X-Sendfile`` is not available, Pants will make full use of caching
        headers, Ranges, and the `sendfile <http://www.kernel.org/doc/man-pages/online/pages/man2/sendfile.2.html>`_
        system call to improve file transfer performance. Additionally, if the
        client had made a ``HEAD`` request, the contents of the file will not
        be transferred.

        .. note::

            The request is finished automatically by this method.

        ===========  ========  ============
        Argument     Default   Description
        ===========  ========  ============
        path                   The path to the file to send. If this is a relative path, and the :class:`~pants.http.server.HTTPServer` instance has no root path for Sendfile set, the path will be assumed relative to the current working directory.
        filename     None      *Optional.* If this is set, the file will be sent as a download with the given filename as the default name to save it with.
        guess_mime   True      *Optional.* If this is set to True, Pants will attempt to set the ``Content-Type`` header based on the file extension.
        headers      None      *Optional.* A dictionary of HTTP headers to send with the file.
        ===========  ========  ============

        .. note::

            If you set a ``Content-Type`` header with the ``headers`` parameter,
            the mime type will not be used, even if ``guess_mime`` is True. The
            ``headers`` will also override any ``Content-Disposition`` header
            generated by the ``filename`` parameter.

        """
        self._started = True

        # The base path
        base = self.connection.server.file_root
        if not base:
            base = os.getcwd()

        # Now, the headers.
        if not headers:
            headers = {}

        # The Content-Disposition headers.
        if filename and not 'Content-Disposition' in headers:
            if not isinstance(filename, basestring):
                filename = str(filename)
            elif isinstance(filename, unicode):
                filename = filename.encode('utf8')

            headers['Content-Disposition'] = 'attachment; filename="%s"' % filename

        # The Content-Type header.
        if not 'Content-Type' in headers:
            if guess_mime:
                if not mimetypes.inited:
                    mimetypes.init()

                content_type = mimetypes.guess_type(path)[0]
                if not content_type:
                    content_type = 'application/octet-stream'

                headers['Content-Type'] = content_type

            else:
                headers['Content-Type'] = 'application/octet-stream'

        # If X-Sendfile is enabled, this becomes much easier.
        if self.connection.server.sendfile:
            # We don't want absolute paths, if we can help it.
            if os.path.isabs(path):
                rel = os.path.relpath(path, base)
                if not rel.startswith('..'):
                    path = rel

            # If we don't have an absolute path, append the prefix.
            if self.connection.server.sendfile_prefix and not os.path.isabs(path):
                path = os.path.join(self.connection.server.sendfile_prefix, path)

            if isinstance(self.connection.server.sendfile, basestring):
                headers[self.connection.server.sendfile] = path
            else:
                headers['X-Sendfile'] = path

            headers['Content-Length'] = 0

            # Now, pass it through and be done.
            self.send_status()
            self.send_headers(headers)
            self.finish()
            return

        # If we get here, then we have to handle sending the file ourself. This
        # gets a bit trickier. First, let's find the proper path.
        if not os.path.isabs(path):
            path = os.path.join(base, path)

        # Let's start with some information on the file.
        stat = os.stat(path)

        modified = datetime.fromtimestamp(stat.st_mtime)
        expires = datetime.utcnow() + timedelta(days=7)
        etag = '"%x-%x"' % (stat.st_size, int(stat.st_mtime))

        if not 'Last-Modified' in headers:
            headers['Last-Modified'] = date(modified)

        if not 'Expires' in headers:
            headers['Expires'] = date(expires)

        if not 'Cache-Control' in headers:
            headers['Cache-Control'] = 'max-age=604800'

        if not 'Accept-Ranges' in headers:
            headers['Accept-Ranges'] = 'bytes'

        if not 'ETag' in headers:
            headers['ETag'] = etag

        # Check request headers.
        not_modified = False

        if 'If-Modified-Since' in self.headers:
            try:
                since = parse_date(self.headers['If-Modified-Since'])
            except ValueError:
                since = None

            if since and since >= modified:
                not_modified = True

        if 'If-None-Match' in self.headers:
            values = self.headers['If-None-Match'].split(',')
            for val in values:
                val = val.strip()
                if val == '*' or etag == val:
                    not_modified = True
                    break

        # Send a 304 Not Modified, if possible.
        if not_modified:
            self.send_status(304)

            if 'Content-Length' in headers:
                del headers['Content-Length']

            if 'Content-Type' in headers:
                del headers['Content-Type']

            self.send_headers(headers)
            self.finish()
            return


        # Check for an If-Range header.
        if 'If-Range' in self.headers and 'Range' in self.headers:
            head = self.headers['If-Range']
            if head != etag:
                try:
                    match = parse_date(head) == modified
                except ValueError:
                    match = False

                if not match:
                    del self.headers['Range']

        # Open the file.
        if not os.access(path, os.R_OK):
            self.send_response('You do not have permission to access that file.', 403)
            return

        try:
            f = open(path, 'rb')
        except IOError:
            self.send_response('You do not have permission to access that file.', 403)
            return

        # If we have no Range header, just do things the easy way.
        if not 'Range' in self.headers:
            headers['Content-Length'] = stat.st_size

            self.send_status()
            self.send_headers(headers)

            if self.method != 'HEAD':
                self.connection.write_file(f)

            self.finish()
            return

        # Start parsing the Range header.
        length = stat.st_size
        start = length - 1
        end = 0

        try:
            if not self.headers['Range'].startswith('bytes='):
                raise ValueError

            for pair in self.headers['Range'][6:].split(','):
                pair = pair.strip()

                if pair.startswith('-'):
                    # Final x bytes.
                    val = int(pair[1:])
                    if val > length:
                        raise ValueError

                    end = length - 1

                    s = length - val
                    if s < start:
                        start = s

                elif pair.endswith('-'):
                    # Everything past x.
                    val = int(pair[:-1])
                    if val > length - 1:
                        raise ValueError

                    end = length - 1
                    if val < start:
                        start = val

                else:
                    s, e = map(int, pair.split('-'))
                    if start < 0 or start > end or end > length - 1:
                        raise ValueError

                    if s < start:
                        start = s

                    if e > end:
                        end = e

        except ValueError:
            # Any ValueErrors need to send a 416 error response.
            self.send_response('416 Requested Range Not Satisfiable', 416)
            return

        # Set the Content-Range header, and the Content-Length.
        total = 1 + (end - start)
        headers['Content-Range'] = 'bytes %d-%d/%d' % (start, end, length)
        headers['Content-Length'] = total

        # Now, send the response.
        self.send_status(206)
        self.send_headers(headers)

        if self.method != 'HEAD':
            if end == length - 1:
                total = 0

            self.connection.write_file(f, nbytes=total, offset=start)

        self.finish()


    def send_headers(self, headers, end_headers=True, cookies=True):
        """
        Write a dictionary of HTTP headers to the client.

        ============  ========  ============
        Argument      Default   Description
        ============  ========  ============
        headers                 A dictionary of HTTP headers.
        end_headers   True      *Optional.* If this is set to True, a double CRLF sequence will be written at the end of the cookie headers, signifying the end of the HTTP headers segment and the beginning of the response.
        cookies       True      *Optional.* If this is set to True, HTTP cookies will be sent along with the headers.
        ============  ========  ============
        """
        self._started = True
        out = []
        append = out.append
        if isinstance(headers, (tuple,list)):
            hv = headers
            headers = []
            for key, val in hv:
                headers.append(key.lower())
                append('%s: %s' % (key, val))
        else:
            hv = headers
            headers = []
            for key in hv:
                headers.append(key.lower())
                val = hv[key]
                if type(val) is list:
                    for v in val:
                        append('%s: %s' % (key, v))
                else:
                    append('%s: %s' % (key, val))

        if not 'date' in headers and self.protocol == 'HTTP/1.1':
            append('Date: %s' % date(datetime.utcnow()))

        if not 'server' in headers:
            append('Server: %s' % SERVER)

        if cookies and hasattr(self, '_cookies_out'):
            self.send_cookies()

        if end_headers:
            append(CRLF)
        else:
            append('')

        self.connection.write(CRLF.join(out))

    def send_response(self, content, code=200, content_type='text/plain'):
        """
        Write a very simple response, in one easy function. This function is
        for convenience, and allows you to send a basic response in one line.

        Basically, rather than::

            def request_handler(request):
                output = "Hello, World!"

                request.send_status(200)
                request.send_headers({
                    'Content-Type': 'text/plain',
                    'Content-Length': len(output)
                    })
                request.send(output)
                request.finish()

        You can simply::

            def request_handler(request):
                request.send_response("Hello, World!")

        =============  ===============  ============
        Argument       Default          Description
        =============  ===============  ============
        content                         A string of content to send to the client.
        code           ``200``          *Optional.* The HTTP status code to send to the client.
        content_type   ``text/plain``   *Optional.* The Content-Type header to send.
        =============  ===============  ============
        """
        self._started = True
        if not isinstance(content, str):
            content = str(content)

        self.send_status(code)
        self.send_headers({
            'Content-Type': content_type,
            'Content-Length': len(content)
            })
        self.send(content)
        self.finish()

    def send_status(self, code=200):
        """
        Write an HTTP status line (the very first line of any response) to the
        client, using the same HTTP protocol version as the request. If one is
        available, a human readable status message will be appended after the
        provided code.

        For example, ``request.send_status(404)`` would result in
        ``HTTP/1.1 404 Not Found`` being sent to the client, assuming of course
        that the request used HTTP protocol version ``HTTP/1.1``.

        =========  ========  ============
        Argument   Default   Description
        =========  ========  ============
        code       ``200``   *Optional.* The HTTP status code to send to the client.
        =========  ========  ============
        """
        self._started = True
        try:
            self.connection.write('%s %d %s%s' % (
                self.protocol, code, HTTP[code], CRLF))
        except KeyError:
            self.connection.write('%s %s%s' % (
                self.protocol, code, CRLF))

    write = send

    ##### Internal Event Handlers #############################################

    def _parse_url(self):
        # Do this ourselves because urlparse is too heavy.
        self.path, _, query = self.url.partition('?')
        self.query, _, self.fragment = query.partition('#')
        netloc = self.host.lower()

        # In-lined the hostname logic
        if '[' in netloc and ']' in netloc:
            self.hostname = netloc.split(']')[0][1:]
        elif ':' in netloc:
            self.hostname = netloc.split(':')[0]
        else:
            self.hostname = netloc

        self.get = get = {}
        if self.query:
            for key, val in parse_qsl(self.query, False):
                if key in get:
                    if isinstance(get[key], list):
                        get[key].append(val)
                    else:
                        get[key] = [get[key], val]
                else:
                    get[key] = val

###############################################################################
# HTTPServer Class
###############################################################################

class HTTPServer(Server):
    """
    An `HTTP <http://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_ server,
    extending the default :class:`~pants.server.Server` class.

    This class automatically uses the :class:`HTTPConnection` connection class.
    Rather than through specifying a connection class, its behavior is
    customized by providing a request handler function that is called whenever
    a valid request is received.

    A server's behavior is defined almost entirely by its request handler, and
    will not send any response by itself unless the received HTTP request is
    not valid or larger than the specified limit (which defaults to 10 MiB, or
    10,485,760 bytes).

    ================  ========  ============
    Argument          Default   Description
    ================  ========  ============
    request_handler             A callable that accepts a single argument. That argument is an instance of the :class:`HTTPRequest` class representing the current request.
    max_request       10 MiB    *Optional.* The maximum allowed length, in bytes, of an HTTP request body. This should be kept small, as the entire request body will be held in memory.
    keep_alive        True      *Optional.* Whether or not multiple requests are allowed over a single connection.
    cookie_secret     None      *Optional.* A string to use when signing secure cookies.
    xheaders          False     *Optional.* Whether or not to use ``X-Forwarded-For`` and ``X-Forwarded-Proto`` headers.
    sendfile          False     *Optional.* Whether or not to use ``X-Sendfile`` headers. If this is set to a string, that string will be used as the header name.
    sendfile_prefix   None      *Optional.* A string to prefix paths with for use in the ``X-Sendfile`` headers. Useful for nginx.
    file_root         None      *Optional.* The root path to send files from using :meth:`~pants.http.server.HTTPRequest.send_file`.
    ================  ========  ============
    """
    ConnectionClass = HTTPConnection

    def __init__(self, request_handler, max_request=10485760, keep_alive=True,
                    cookie_secret=None, xheaders=False, sendfile=False,
                    sendfile_prefix=None, file_root=None, **kwargs):
        Server.__init__(self, **kwargs)

        # Storage
        self.request_handler    = request_handler
        self.max_request        = max_request
        self.keep_alive         = keep_alive
        self.xheaders           = xheaders
        self.sendfile           = sendfile
        self.sendfile_prefix    = sendfile_prefix
        self.file_root          = os.path.abspath(file_root) if file_root else None

        self._cookie_secret     = cookie_secret

    @property
    def cookie_secret(self):
        if self._cookie_secret is None:
            self._cookie_secret = os.urandom(30)

        return self._cookie_secret

    @cookie_secret.setter
    def cookie_secret(self, val):
        self._cookie_secret = val

    def listen(self, address=None, backlog=1024, slave=True):
        """
        Begins listening for connections to the HTTP server.

        The given ``address`` is resolved, the server is bound to the address,
        and it then begins listening for connections. If an address isn't
        specified, the server will listen on either port 80 or port 443 by
        default. Port 443 is selected if SSL has been enabled prior to the
        call to listen, otherwise port 80 will be used.

        .. seealso::

            See :func:`pants.server.Server.listen` for more information on
            listening servers.
        """
        if address is None or isinstance(address, (list,tuple)) and \
                              len(address) > 1 and address[1] is None:
            if self.ssl_enabled:
                port = 443
            else:
                port = 80

            if address is None:
                address = port
            else:
                address = tuple(address[0] + (port,) + address[2:])

        return Server.listen(self, address=address, backlog=backlog,
                                slave=slave)

########NEW FILE########
__FILENAME__ = utils
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import hashlib
import hmac
import logging
import mimetypes
import re
import time

from datetime import datetime
from itertools import imap

from pants import __version__ as pants_version


###############################################################################
# Logging
###############################################################################

log = logging.getLogger("pants.http")


###############################################################################
# Constants
###############################################################################

WHITESPACE = re.compile(r"\s+")

SERVER      = 'HTTPants (pants/%s)' % pants_version
SERVER_URL  = 'http://www.pantspowered.org/'

USER_AGENT = "HTTPants/%s" % pants_version

# Formats for parse_date to use.
DATE_FORMATS = (
    "%a, %d %b %Y %H:%M:%S %Z",
    "%A, %d-%b-%y %H:%M:%S %Z",
    "%a %b %d %H:%M:%S %Y",
    )

COMMA_HEADERS = ('Accept', 'Accept-Charset', 'Accept-Encoding',
    'Accept-Language', 'Accept-Ranges', 'Allow', 'Cache-Control', 'Connection',
    'Content-Encoding', 'Content-Language', 'Expect', 'If-Match',
    'If-None-Match', 'Pragma', 'Proxy-Authenticate', 'TE', 'Trailer',
    'Transfer-Encoding', 'Upgrade', 'Vary', 'Via', 'Warning',
    'WWW-Authenticate')

STRANGE_HEADERS = {
    'a-im': 'A-IM',
    'c-pep': 'C-PEP',
    'c-pep-info': 'C-PEP-Info',
    'content-id': 'Content-ID',
    'content-md5': 'Content-MD5',
    'dasl': 'DASL',
    'dav': 'DAV',
    'dl-expansion-history': 'DL-Expansion-History',
    'differential-id': 'Differential-ID',
    'dnt': 'DNT',
    'ediint-features': 'EDIINT-Features',
    'etag': 'ETag',
    'getprofile': 'GetProfile',
    'im': 'IM',
    'message-id': 'Message-ID',
    'mime-version': 'MIME-Version',
    'p3p': 'P3P',
    'pep': 'PEP',
    'pics-label': 'PICS-Label',
    'profileobject': 'ProfileObject',
    'sec-websocket-accept': 'Sec-WebSocket-Accept',
    'sec-websocket-extensions': 'Sec-WebSocket-Extensions',
    'sec-websocket-key': 'Sec-WebSocket-Key',
    'sec-websocket-protocol': 'Sec-WebSocket-Protocol',
    'sec-websocket-version': 'Sec-WebSocket-Version',
    'setprofile': 'SetProfile',
    'slug': 'SLUG',
    'soapaction': 'SoapAction',
    'status-uri': 'Status-URI',
    'subok': 'SubOK',
    'tcn': 'TCN',
    'te': 'TE',
    'ua-color': 'UA-Color',
    'ua-media': 'UA-Media',
    'ua-pixels': 'UA-Pixels',
    'ua-resolution': 'UA-Resolution',
    'ua-windowpixels': 'UA-Windowpixels',
    'uri': 'URI',
    'vbr-info': 'VBR-Info',
    'www-authenticate': 'WWW-Authenticate',
    'x400-mts-identifier': 'X400-MTS-Identifier',
    'x-att-deviceid': 'X-ATT-DeviceId',
    'x-ua-compatible': 'X-UA-Compatible',
    'x-xss-protection': 'X-XSS-Protection',
}

CRLF = '\r\n'
DOUBLE_CRLF = CRLF + CRLF

HTTP = {
    101: 'Switching Protocols',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: 'No Longer Used',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Not Authorised',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    426: "Upgrade Required",
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported'
}

class BadRequest(Exception):
    def __init__(self, message, code='400 Bad Request'):
        Exception.__init__(self, message)
        self.code = code


###############################################################################
# Header Case Normalization
###############################################################################

class HeadingNormalizer(dict):
    def __missing__(self, key):
        ret = self[key] = "-".join(x.capitalize() for x in key.split("-"))
        return ret

_normalize_header = HeadingNormalizer(STRANGE_HEADERS).__getitem__

# Note: Do NOT correct the spelling 'referer'. It's meant to be that way.
for hdr in ('accept', 'accept-charset', 'accept-encoding', 'accept-language',
            'accept-datetime', 'authorization', 'cache-control', 'connection',
            'cookie', 'content-length', 'content-type', 'date', 'expect',
            'from', 'host', 'if-match', 'if-modified-since', 'if-none-match',
            'if-range', 'if-unmodified-since', 'max-forwards', 'pragma',
            'proxy-authorization', 'range', 'referer', 'upgrade', 'user-agent',
            'via', 'warning', 'x-requested-with', 'x-forwarded-for',
            'x-forwarded-proto', 'front-end-https', 'x-wap-profile',
            'proxy-connection', 'access-control-allow-origin', 'accept-ranges',
            'age', 'allow', 'content-encoding', 'content-language',
            'content-location', 'content-disposition', 'content-range',
            'expires', 'last-modified', 'link', 'location',
            'proxy-authenticate', 'refresh', 'retry-after', 'server',
            'set-cookie', 'strict-transport-security', 'trailer',
            'transfer-encoding', 'vary', 'x-frame-options',
            'x-content-type-options', 'x-powered-by'):
    _normalize_header(hdr)


###############################################################################
# HTTPHeaders Class
###############################################################################

class HTTPHeaders(object):
    """
    HTTPHeaders is a dict-like object that holds parsed HTTP headers, provides
    access to them in a case-insensitive way, and that normalizes the case of
    the headers upon iteration.
    """

    __slots__ = ('_data',)

    def __init__(self, data=None, _store=None):
        self._data = _store or {}
        if data:
            self.update(data)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, dict(self.iteritems()))

    def __len__(self):
        return len(self._data)

    def __eq__(self, other, _normalize_header=_normalize_header):
        if isinstance(other, HTTPHeaders):
            return self._data == other._data

        for k, v in self._data.iteritems():
            k = _normalize_header(k)
            if not (k in other) or not (other[k] == v):
                return 0
        return len(self._data) == len(other)

    def iteritems(self, _normalize_header=_normalize_header):
        for k, v in self._data.iteritems():
            yield _normalize_header(k), v

    def iterkeys(self):
        return imap(_normalize_header, self._data)

    __iter__ = iterkeys

    def itervalues(self):
        return self._data.itervalues()

    def items(self, _normalize_header=_normalize_header):
        return [(_normalize_header(k), v) for k,v in self._data.iteritems()]

    def keys(self, _normalize_header=_normalize_header):
        return [_normalize_header(k) for k in self._data]

    def values(self):
        return self._data.values()

    def update(self, iterable=None, **kwargs):
        if iterable:
            if hasattr(iterable, 'keys'):
                for k in iterable:
                    self[k] = iterable[k]
            else:
                for (k,v) in iterable:
                    self[k] = v

        for k,v in kwargs.iteritems():
            self[k] = v

    def __setitem__(self, key, value):
        self._data[key.lower()] = value

    def __delitem__(self, key):
        del self._data[key.lower()]

    def __contains__(self, key):
        return key.lower() in self._data

    has_key = __contains__

    def __getitem__(self, key):
        return self._data[key.lower()]

    def get(self, key, default=None):
        return self._data.get(key.lower(), default)

    def setdefault(self, key, default=None):
        return self._data.setdefault(key.lower(), default)

    def clear(self):
        self._data.clear()

    def copy(self):
        return self.__class__(_store=self._data.copy())

    def pop(self, key, *default):
        return self._data.pop(key, *default)

    def popitem(self):
        key, val = self._data.popitem()
        return _normalize_header(key), val


###############################################################################
# Support Functions
###############################################################################

def get_filename(file):
    name = getattr(file, 'name', None)
    if name and not (name.endswith('>') and name.startswith('<')):
        return name

def generate_signature(key, *parts):
    hash = hmac.new(key, digestmod=hashlib.sha1)
    for p in parts:
        hash.update(str(p))
    return hash.hexdigest()

def content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

def encode_multipart(vars, files=None, boundary=None):
    """
    Encode a set of variables and/or files into a ``multipart/form-data``
    request body, and returns a list of strings and files that can be sent to
    the server, along with the used boundary.

    =========  ============
    Argument   Description
    =========  ============
    vars       A dictionary of variables to encode.
    files      *Optional.* A dictionary of tuples of ``(filename, data)`` to encode.
    boundary   *Optional.* The boundary string to use when encoding, if for any reason the default string is unacceptable.
    =========  ============
    """

    if boundary is None:
        boundary = '-----pants-----PANTS-----pants$'

    out = []

    for k, v in vars.iteritems():
        out.append('--%s%sContent-Disposition: form-data; name="%s"%s%s%s' % (boundary, CRLF, k, DOUBLE_CRLF, v, CRLF))
    if files:
        for k, v in files.iteritems():
            if isinstance(v, (list,tuple)):
                fn, v = v
            else:
                fn = get_filename(v)
                if not fn:
                    fn = k

            out.append('--%s%sContent-Disposition: form-data; name="%s"; filename="%s"%sContent-Type: %s%sContent-Transfer-Encoding: binary%s' % (boundary, CRLF, k, fn, CRLF, content_type(fn), CRLF, DOUBLE_CRLF))
            out.append(v)
            out.append(CRLF)

    out.append('--%s--%s' % (boundary, CRLF))

    return boundary, out

def parse_multipart(request, boundary, data):
    """
    Parse a ``multipart/form-data`` request body and modify the request's
    ``post`` and ``files`` dictionaries as is appropriate.

    =========  ============
    Argument   Description
    =========  ============
    request    An :class:`HTTPRequest` instance that should be modified to include the parsed data.
    boundary   The ``multipart/form-data`` boundary to be used for splitting the data into parts.
    data       The data to be parsed.
    =========  ============
    """

    if boundary.startswith('"') and boundary.endswith('"'):
        boundary = boundary[1:-1]

    footer_length = len(boundary) + 4
    if data.endswith(CRLF):
        footer_length += 2

    parts = data[:-footer_length].split('--%s%s' % (boundary, CRLF))
    for part in parts:
        if not part:
            continue

        eoh = part.find(DOUBLE_CRLF)
        if eoh == -1:
            log.warning(
                'Missing part headers in multipart/form-data. Skipping.')
            continue

        headers = read_headers(part[:eoh])
        name_header = headers.get('Content-Disposition', '')
        if not name_header.startswith('form-data;') or not part.endswith(CRLF):
            log.warning('Invalid multipart/form-data part.')
            continue

        value = part[eoh+4:-2]
        name_values = {}
        for name_part in name_header[10:].split(';'):
            name, name_value = name_part.strip().split('=', 1)
            name_values[name] = name_value.strip('"').decode('utf-8')

        if not 'name' in name_values:
            log.warning('Missing name value in multipart/form-data part.')
            continue

        name = name_values['name']
        if 'filename' in name_values:
            content_type = headers.get('Content-Type', 'application/unknown')
            request.files.setdefault(name, []).append(dict(
                filename=name_values['filename'], body=value,
                content_type=content_type))
        else:
            request.post.setdefault(name, []).append(value)

def read_headers(data, target=None):
    """
    Read HTTP headers from the supplied data string and return a dictionary
    of those headers. If bad data is supplied, a :class:`BadRequest` exception
    will be raised.

    =========  ============
    Argument   Description
    =========  ============
    data       A data string containing HTTP headers.
    target     *Optional.* A dictionary in which to place the processed headers.
    =========  ============
    """
    if target is None:
        cast = True
        target = {}
    else:
        cast = False

    data = data.rstrip(CRLF)
    key = None

    if data:
        for line in data.split(CRLF):
            if not line:
                raise BadRequest('Illegal header line: %r' % line)
            if key and line[0] in ' \t':
                val = line.strip()
                mline = True
            else:
                mline = False
                try:
                    key, val = line.split(':', 1)
                except ValueError:
                    raise BadRequest('Illegal header line: %r' % line)

                key = key.strip().lower()
                val = val.strip()

                try:
                    val = int(val)
                except ValueError:
                    pass

            if key in target:
                if mline:
                    if isinstance(target[key], list):
                        if target[key]:
                            target[key][-1] += ' ' + val
                        else:
                            target[key].append(val)
                    else:
                        target[key] += ' ' + val
                elif key in COMMA_HEADERS:
                    target[key] = '%s, %s' % (target[key], val)
                elif isinstance(target[key], list):
                    target[key].append(val)
                else:
                    target[key] = [target[key], val]
                continue
            target[key] = val

    if cast:
        target = HTTPHeaders(_store=target)

    return target

def date(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

def parse_date(text):
    for fmt in DATE_FORMATS:
        try:
            return datetime(*time.strptime(text, fmt)[:6])
        except ValueError:
            continue
    raise ValueError("Unable to parse time data %r." % text)

########NEW FILE########
__FILENAME__ = websocket
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
``pants.http.websocket`` implements the WebSocket protocol, as described by
:rfc:`6455`, on top of the Pants HTTP server using an API similar to that
provided by :class:`pants.stream.Stream`.


Using WebSockets
================

To start working with WebSockets, you'll need to create a subclass of
:class:`WebSocket`. As with :class:`~pants.stream.Stream`, :class:`WebSocket`
instances are meant to contain the majority of your networking logic through
the definition of custom event handlers. Event handlers are methods that have
names beginning with ``on_`` that can be safely overridden within
your subclass.


Listening for Connections
-------------------------

:class:`WebSocket` is designed to be used as a request handler for the Pants
HTTP server, :class:`pants.http.server.HTTPServer`. As such, to begin listening
for WebSocket connections, you must create an instance of
:class:`~pants.http.server.HTTPServer` using your custom :class:`WebSocket`
subclass as its request handler.

.. code-block:: python

    from pants.http import HTTPServer, WebSocket
    from pants import Engine

    class EchoSocket(WebSocket):
        def on_read(self, data):
            self.write(data)

    HTTPServer(EchoSocket).listen(8080)
    Engine.instance().start()

If you need to host traditional requests from your HTTPServer instance, you may
invoke the WebSocket handler simply by creating an instance of your
:class:`WebSocket` subclass with the appropriate
:class:`pants.http.server.HTTPRequest` instance as its only argument:

.. code-block:: python

    from pants.http import HTTPServer, WebSocket
    from pants import Engine

    class EchoSocket(WebSocket):
        def on_read(self, data):
            self.write(data)

    def request_handler(request):
        if request.path == '/_ws':
            EchoSocket(request)
        else:
            request.send_response("Nothing to see here.")

    HTTPServer(request_handler).listen(8080)
    Engine.instance().start()


``WebSocket`` and ``Application``
---------------------------------

:class:`WebSocket` has support for :class:`pants.web.application.Application`
and can easily be used as a request handler for any route. Additionally,
variables captured from the URL by :class:`~pants.web.application.Application`
will be made accessible to the :meth:`WebSocket.on_connect` event handler. The
following example of a WebSocket echo server displays a customized welcome
message depending on the requested URL.

.. code-block:: python

    from pants.http import WebSocket
    from pants.web import Application

    app = Application()

    @app.route("/ws/<name>")
    class EchoSocket(WebSocket):
        def on_connect(self, name):
            self.write(u"Hello, {name}!".format(name=name))

        def on_read(self, data):
            self.write(data)

    app.run(8080)


WebSocket Security
==================

Secure Connections
------------------

:class:`WebSocket` relies upon the :class:`pants.http.server.HTTPServer`
instance serving it to provide SSL. This can be as easy as calling the server's
:meth:`~pants.http.server.HTTPServer.startSSL` method.

To determine whether or not the :class:`WebSocket` instance is using a
secure connection, you may use the :attr:`~WebSocket.is_secure` attribute.


Custom Handshakes
-----------------

You may implement custom logic during the WebSocket's handshake by overriding
the :meth:`WebSocket.on_handshake` event handler. The ``on_handshake`` handler
is called with a reference to the :class:`~pants.http.server.HTTPRequest`
instance the WebSocket handshake is happening upon as well as an empty
dictionary that may be used to set custom headers on the HTTP response.

``on_handshake`` is expected to return a True value if the request is alright.
Returning a False value will result in the generation of an error page. The
following example of a custom handshake requires a secret HTTP header in the
request, and that the connection is secured:

.. code-block:: python

    from pants.http import WebSocket

    class SecureSocket(WebSocket):
        def on_handshake(self, request, headers):
            return self.is_secure and 'X-Pizza' in request.headers

        def on_connect(self):
            self.write(u"Welcome to PizzaNet.")


Reading and Writing Data
========================

WebSockets are a bit different than normal :class:`~pants.stream.Stream`
instances, as a WebSocket can transmit both byte strings and unicode strings,
and data is encapsulated into formatted messages with definite lengths. Because
of this, reading from one can be slightly different.

Mostly, however, the :attr:`~WebSocket.read_delimiter` works in exactly the
same way as that of :class:`pants.stream.Stream`.

Unicode Strings and Byte Strings
--------------------------------

:class:`WebSocket` strictly enforces the difference between byte strings and
unicode strings. As such, the connection will be closed with a protocol error
if any of the following happen:

    1.  The string types of the :attr:`~WebSocket.read_delimiter` and the
        buffer differ.

    2.  There is an existing string still in the buffer when the client sends
        another string of a different type.

    3.  The :attr:`~WebSocket.read_delimiter` is currently a struct and the
        buffer does not contain a byte string.

Of those conditions, the most likely to occur is the first. Take the following
code:

.. code-block:: python

    from pants.http import WebSocket, HTTPServer
    from pants import Engine

    def process(text):
        return text.decode('rot13')

    class LineOriented(WebSocket):
        def on_connect(self):
            self.read_delimiter = "\\n"

        def on_read(self, line):
            self.write(process(line))

    HTTPServer(LineOriented).listen(8080)
    Engine.instance().start()

And, on the client:

.. code-block:: html

    <!DOCTYPE html>
    <textarea id="editor"></textarea><br>
    <input type="submit" value="Send">
    <script>
        var ws = new WebSocket("ws://localhost:8080/"),
            input = document.querySelector('#editor'),
            button = document.querySelector('input');

        ws.onmessage = function(e) {
            alert("Got back: " + e.data);
        }

        button.addEventListener("click", function() {
            ws.send(input.value + "\\n");
        });
    </script>

On Python 2.x, the read delimiter will be a byte string. The WebSocket will
expect to receive a byte string. However, the simple JavaScript shown above
sends *unicode* strings. That simple service would fail immediately
on Python 2.

To avoid the problem, be sure to use the string type you really want for your
read delimiters. For the above, that's as simple as setting the read
delimiter with:

.. code-block:: python

    self.read_delimiter = u"\\n"


WebSocket Messages
------------------

In addition to the standard types of :attr:`~WebSocket.read_delimiter`,
:class:`WebSocket` instances support the use of a special value called
:attr:`EntireMessage`. When using ``EntireMessage``, full messages will
be sent to your :attr:`~WebSocket.on_read` event handler, as framed by
the remote end-point.

``EntireMessage`` is the default :attr:`~WebSocket.read_delimiter` for
WebSocket instances, and it makes it dead simple to write simple services.

The following example implements a simple RPC system over WebSockets:

.. code-block:: python

    import json

    from pants.http.server import HTTPServer
    from pants.http.websocket import WebSocket, FRAME_TEXT
    from pants import Engine

    class RPCSocket(WebSocket):
        methods = {}

        @classmethod
        def method(cls, name):
            ''' Add a method to the RPC. '''
            def decorator(method):
                cls.methods[name] = method
                return method
            return decorator

        def json(self, **data):
            ''' Send a JSON object to the remote end-point. '''
            # JSON outputs UTF-8 encoded text by default, so use the frame
            # argument to let WebSocket know it should be sent as text to the
            # remote end-point, rather than as binary data.
            self.write(json.dumps(data), frame=FRAME_TEXT)

        def on_read(self, data):
            # Attempt to decode a JSON message.
            try:
                data = json.loads(data)
            except ValueError:
                self.json(ok=False, result="can't decode JSON")
                return

            # Lookup the desired method. Return an error if it doesn't exist.
            method = data['method']
            if not method in self.methods:
                self.json(ok=False, result="no such method")
                return

            method = self.methods[method]
            args = data.get("args", tuple())
            kwargs = data.get("kwargs", dict())
            ok = True

            # Try running the method, and capture the result. If it errors, set
            # the result to the error string and ok to False.
            try:
                result = method(*args, **kwargs)
            except Exception as ex:
                ok = False
                result = str(ex)

            self.json(ok=ok, result=result)


    @RPCSocket.method("rot13")
    def rot13(string):
        return string.decode("rot13")

    HTTPServer(RPCSocket).listen(8080)
    Engine.instance().start()

As you can see, it never even *uses* :attr:`~WebSocket.read_delimiter`. The
client simply sends JSON messages, with code such as:

.. code-block:: javascript

    my_websocket.send(JSON.stringify({method: "rot13", args: ["test"]}));

This behavior is completely reliable, even when the client is sending
fragmented messages.

"""

###############################################################################
# Imports
###############################################################################

import base64
import hashlib
import re
import struct
import sys

if sys.platform == "win32":
    from time import clock as time
else:
    from time import time

from pants.stream import StreamBufferOverflow
from pants.http.utils import log

try:
    from netstruct import NetStruct as _NetStruct
except ImportError:
    # Create the fake class because isinstance expects a class.
    class _NetStruct(object):
        def __init__(self, *a, **kw):
            raise NotImplementedError


###############################################################################
# Constants
###############################################################################

CLOSE_REASONS = {
    1000: 'Normal Closure',
    1001: 'Endpoint Going Away',
    1002: 'Protocol Error',
    1003: 'Unacceptable Data Type',
    1005: 'No Status Code',
    1006: 'Abnormal Close',
    1007: 'Invalid UTF-8 Data',
    1008: 'Message Violates Policy',
    1009: 'Message Too Big',
    1010: 'Extensions Not Present',
    1011: 'Unexpected Condition Prevented Fulfillment',
    1015: 'TLS Handshake Error'
}

# Handshake Key
WEBSOCKET_KEY = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# Supported WebSocket Versions
WEBSOCKET_VERSIONS = (13, 8, 0)

# Frame Opcodes
FRAME_CONTINUATION = 0
FRAME_TEXT = 1
FRAME_BINARY = 2
FRAME_CLOSE = 8
FRAME_PING = 9
FRAME_PONG = 10

# Special read_delimiter Value
EntireMessage = object()

# Regex Stuff
RegexType = type(re.compile(""))
Struct = struct.Struct

# Structs
STRUCT_H = Struct("!H")
STRUCT_Q = Struct("!Q")


###############################################################################
# WebSocket Class
###############################################################################

class WebSocket(object):
    """
    An implementation of `WebSockets <http://en.wikipedia.org/wiki/WebSockets>`_
    on top of the Pants HTTP server using an API similar to that of
    :class:`pants.stream.Stream`.

    A :class:`WebSocket` instance represents a WebSocket connection to a
    remote client. In the future, WebSocket will be modified to support acting
    as a client in addition to acting as a server.

    When using WebSockets you write logic as you could for
    :class:`~pants.stream.Stream`, using the same :attr:`read_delimiter` and
    event handlers, while the WebSocket implementation handles the initial
    negotiation and all data framing for you.

    =========  ============
    Argument   Description
    =========  ============
    request    The :class:`~pants.http.server.HTTPRequest` to begin negotiating a WebSocket connection over.
    =========  ============
    """

    protocols = None
    allow_old_handshake = False

    def __init__(self, request, *arguments):
        # Store the request and play nicely with web.
        self._connection = request.connection
        self.engine = self._connection.engine
        request.auto_finish = False
        self._arguments = arguments

        # Base State
        self.fileno = self._connection.fileno
        self._remote_address = None
        self._local_address = None
        self._pings = {}
        self._last_ping = 0

        # I/O attributes
        self._read_delimiter = EntireMessage
        self._recv_buffer_size_limit = self._buffer_size

        self._recv_buffer = ""
        self._read_buffer = None
        self._rb_type = None
        self._frag_frame = None

        self.connected = False
        self._closed = False

        # Copy the HTTPRequest's security state.
        self.is_secure = request.is_secure

        # First up, make sure we're dealing with an actual WebSocket request.
        # If we aren't, return a simple 426 Upgrade Required page.
        fail = False
        headers = {}

        if not request.headers.get('Connection','').lower() == 'upgrade' and \
                not request.headers.get('Upgrade','').lower() == 'websocket':
            fail = True

        # It's a WebSocket. Rejoice. Make sure the handshake information is
        # all acceptable.
        elif not self._safely_call(self.on_handshake, request, headers):
            fail = True

        # Determine which version of WebSockets we're dealing with.
        if 'Sec-WebSocket-Version' in request.headers:
            # New WebSockets. Handshake.
            if not 'Sec-WebSocket-Key' in request.headers:
                fail = True
            else:

                accept = base64.b64encode(hashlib.sha1(
                    request.headers['Sec-WebSocket-Key'] + WEBSOCKET_KEY
                    ).digest())

                headers['Upgrade'] = 'websocket'
                headers['Connection'] = 'Upgrade'
                headers['Sec-WebSocket-Accept'] = accept

                self.version = int(request.headers['Sec-WebSocket-Version'])

                if self.version not in WEBSOCKET_VERSIONS:
                    headers['Sec-WebSocket-Version'] = False
                    fail = True

        elif not self.allow_old_handshake:
            # No old WebSockets allowed.
            fail = True

        else:
            # Old WebSockets. Wut?
            self.version = 0
            self._headers = headers
            self._request = request

            self._connection.on_read = self._finish_handshake
            self._connection.on_close = self._con_close
            self._connection.on_write = self._con_write
            self._connection.read_delimiter = 8
            return

        if fail:
            if 'Sec-WebSocket-Version' in headers:
                request.send_status(400)
                request.send_headers({
                    'Content-Type': 'text/plain',
                    'Content-Length': 15,
                    'Sec-WebSocket-Version': ', '.join(str(x) for x in
                                                        WEBSOCKET_VERSIONS)
                })
                request.send('400 Bad Request')
            else:
                request.send_status(426)
                headers = {
                    'Content-Type': 'text/plain',
                    'Content-Length': '20',
                    'Sec-WebSocket-Version': ', '.join(str(x) for x in
                        WEBSOCKET_VERSIONS)
                    }
                request.send_headers(headers)
                request.send("426 Upgrade Required")
            request.finish()
            return

        # Still here? No fail! Send the handshake response, hook up event
        # handlers, and call on_connect.
        request.send_status(101)
        request.send_headers(headers)

        self._connection.on_read = self._con_read
        self._connection.on_close = self._con_close
        self._connection.on_write = self._con_write
        self._connection.read_delimiter = None

        self.connected = True
        self._safely_call(self.on_connect, *self._arguments)
        del self._arguments


    def _finish_handshake(self, key3):
        self._connection.read_delimiter = None
        request = self._request
        headers = self._headers
        del self._headers
        del self._request

        scheme = 'wss' if self.is_secure else 'ws'

        request.send_status(101)
        headers.update({
            'Upgrade': 'WebSocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Origin': request.headers['Origin'],
            'Sec-WebSocket-Location': '%s://%s%s' % (
                scheme, request.host, request.url)
            })
        request.send_headers(headers)

        try:
            request.send(challenge_response(
                request.headers, key3))
        except ValueError:
            log.warning("Malformed WebSocket challenge to %r." % self)
            self.close(False)
            return

        # Move on.
        self._expect_frame = True

        # Finish up.
        self.connected = True
        self._connection.on_read = self._con_old_read
        self._safely_call(self.on_connect, *self._arguments)
        del self._arguments


    ##### Properties ##########################################################

    @property
    def remote_address(self):
        """
        The remote address to which the WebSocket is connected.

        By default, this will be the value of ``socket.getpeername`` or
        None. It is possible for user code to override the default
        behaviour and set the value of the property manually. In order
        to return the property to its default behaviour, user code then
        has to delete the value. Example::

            # default behaviour
            channel.remote_address = custom_value
            # channel.remote_address will return custom_value now
            del channel.remote_address
            # default behaviour
        """
        if self._remote_address is not None:
            return self._remote_address
        elif self._connection:
            return self._connection.remote_address
        else:
            return None


    @remote_address.setter
    def remote_address(self, val):
        self._remote_address = val


    @remote_address.deleter
    def remote_address(self):
        self._remote_address = None


    @property
    def local_address(self):
        """
        The address of the WebSocket on the local machine.

        By default, this will be the value of ``socket.getsockname`` or
        None. It is possible for user code to override the default
        behaviour and set the value of the property manually. In order
        to return the property to its default behaviour, user code then
        has to delete the value. Example::

            # default behaviour
            channel.local_address = custom_value
            # channel.local_address will return custom_value now
            del channel.local_address
            # default behaviour
        """
        if self._local_address is not None:
            return self._local_address
        elif self._connection:
            return self._connection.local_address
        else:
            return None


    @local_address.setter
    def local_address(self, val):
        self._local_address = val


    @local_address.deleter
    def local_address(self):
        self._local_address = None


    @property
    def read_delimiter(self):
        """
        The magical read delimiter which determines how incoming data is
        buffered by the WebSocket.

        As data is read from the socket, it is buffered internally by
        the WebSocket before being passed to the :meth:`on_read` callback. The
        value of the read delimiter determines when the data is passed to the
        callback. Valid values are ``None``, a string, an integer/long,
        a compiled regular expression, an instance of :class:`struct.Struct`,
        an instance of :class:`netstruct.NetStruct`, or the
        :attr:`~pants.http.websocket.EntireMessage` object.

        When the read delimiter is the ``EntireMessage`` object, entire
        WebSocket messages will be passed to :meth:`on_read` immediately once
        they have been received in their entirety. This is the default behavior
        for :class:`WebSocket` instances.

        When the read delimiter is ``None``, data will be passed to
        :meth:`on_read` immediately after it has been received.

        When the read delimiter is a byte string or unicode string, data will
        be buffered internally until that string is encountered in the incoming
        data. All data up to but excluding the read delimiter is then passed
        to :meth:`on_read`. The segment matching the read delimiter itself is
        discarded from the buffer.

        .. note::

            When using strings as your read delimiter, you must be careful to
            use unicode strings if you wish to send and receive strings to a
            remote JavaScript client.

        When the read delimiter is an integer or a long, it is treated
        as the number of bytes to read before passing the data to
        :meth:`on_read`.

        When the read delimiter is an instance of :class:`struct.Struct`, the
        Struct's ``size`` is fully buffered and the data is unpacked before the
        unpacked data is sent to :meth:`on_read`. Unlike other types of read
        delimiters, this can result in more than one argument being sent to the
        :meth:`on_read` event handler, as in the following example::

            import struct
            from pants.http import WebSocket

            class Example(WebSocket):
                def on_connect(self):
                    self.read_delimiter = struct.Struct("!ILH")

                def on_read(self, packet_type, length, id):
                    pass

        You must send binary data from the client when using structs as your
        read delimiter. If Pants receives a unicode string while a struct
        read delimiter is set, it will close the connection with a protocol
        error. This holds true for the :class:`~netstruct.Netstruct`
        delimiters as well.

        When the read delimiter is an instance of :class:`netstruct.NetStruct`,
        the NetStruct's :attr:`~netstruct.NetStruct.minimum_size` is buffered
        and unpacked with the NetStruct, and additional data is buffered as
        necessary until the NetStruct can be completely unpacked. Once ready,
        the data will be passed to :meth:`on_read`. Using Struct and NetStruct
        are *very* similar.

        When the read delimiter is a compiled regular expression
        (:class:`re.RegexObject`), there are two possible behaviors that you
        may switch between by setting the value of :attr:`regex_search`. If
        :attr:`regex_search` is True, as is the default, the delimiter's
        :meth:`~re.RegexObject.search` method is used and, if a match is found,
        the string before that match is passed to :meth:`on_read`. The segment
        that was matched by the regular expression will be discarded.

        If :attr:`regex_search` is False, the delimiter's
        :meth:`~re.RegexObject.match` method is used instead and, if a match
        is found, the match object itself will be passed to :meth:`on_read`,
        giving you access to the capture groups. Again, the segment that was
        matched by the regular expression will be discarded from the buffer.

        Attempting to set the read delimiter to any other value will
        raise a :exc:`TypeError`.

        The effective use of the read delimiter can greatly simplify the
        implementation of certain protocols.
        """
        return self._read_delimiter


    @read_delimiter.setter
    def read_delimiter(self, value):
        if value is None or isinstance(value, basestring) or\
           isinstance(value, RegexType):
            self._read_delimiter = value
            self._recv_buffer_size_limit = self._buffer_size

        elif isinstance(value, (int, long)):
            self._read_delimiter = value
            self._recv_buffer_size_limit = max(self._buffer_size, value)

        elif isinstance(value, Struct):
            self._read_delimiter = value
            self._recv_buffer_size_limit = max(self._buffer_size, value.size)

        elif isinstance(value, _NetStruct):
            self._read_delimiter = value
            self._recv_buffer_size_limit = max(self._buffer_size,
                                               value.minimum_size)

        elif value is EntireMessage:
            self._read_delimiter = value
            self._recv_buffer_size_limit = self._buffer_size

        else:
            raise TypeError("Attempted to set read_delimiter to a value with an invalid type.")

        # Reset NetStruct state when we change the read delimiter.
        self._netstruct_iter = None
        self._netstruct_needed = None


    # Setting these at the class level makes them easy to override on a
    # per-class basis.
    regex_search = True
    _buffer_size = 2 ** 16  # 64kb


    @property
    def buffer_size(self):
        """
        The maximum size, in bytes, of the internal buffer used for
        incoming data.

        When buffering data it is important to ensure that inordinate
        amounts of memory are not used. Setting the buffer size to a
        sensible value can prevent coding errors or malicious use from
        causing your application to consume increasingly large amounts
        of memory. By default, a maximum of 64kb of data will be stored.

        The buffer size is mainly relevant when using a string value for
        the :attr:`read_delimiter`. Because you cannot guarantee that the
        string will appear, having an upper limit on the size of the data
        is appropriate.

        If the read delimiter is set to a number larger than the buffer
        size, the buffer size will be increased to accommodate the read
        delimiter.

        When the internal buffer's size exceeds the maximum allowed, the
        :meth:`on_overflow_error` callback will be invoked.

        Attempting to set the buffer size to anything other than an
        integer or long will raise a :exc:`TypeError`.
        """
        return self._buffer_size


    @buffer_size.setter
    def buffer_size(self, value):
        if not isinstance(value, (long, int)):
            raise TypeError("buffer_size must be an int or a long")
        self._buffer_size = value
        if isinstance(self._read_delimiter, (int, long)):
            self._recv_buffer_size_limit = max(value, self._read_delimiter)
        elif isinstance(self._read_delimiter, Struct):
            self._recv_buffer_size_limit = max(value,
                self._read_delimiter.size)
        elif isinstance(self._read_delimiter, _NetStruct):
            self._recv_buffer_size_limit = max(value,
                self._read_delimiter.minimum_size)
        else:
            self._recv_buffer_size_limit = value


    ##### Control Methods #####################################################

    def close(self, flush=True, reason=1000, message=None):
        """
        Close the WebSocket connection. If flush is True, wait for any remaining
        data to be sent and send a close frame before closing the connection.

        =========  ==========  ============
        Argument   Default     Description
        =========  ==========  ============
        flush      ``True``    *Optional.* If False, closes the connection immediately, without ensuring all buffered data is sent.
        reason     ``1000``    *Optional.* The reason the socket is closing, as defined at :rfc:`6455#section-7.4`.
        message    ``None``    *Optional.* A message string to send with the reason code, rather than the default.
        =========  ==========  ============
        """
        if self._connection is None or self._closed:
            return

        self.read_delimiter = None
        self._read_buffer = None
        self._rb_type = None
        self._recv_buffer = ""
        self._closed = True

        if flush:
            if not self.version:
                self._connection.close(True)
            else:
                # Look up the reason.
                if not message:
                    message = CLOSE_REASONS.get(reason, 'Unknown Close')
                reason = STRUCT_H.pack(reason) + message

                self.write(reason, frame=FRAME_CLOSE)
                self._connection.close(True)
                self.connected = False
                self._connection = None
            return

        self.connected = False

        if self._connection and self._connection.connected:
            self._connection.close(False)
            self._connection = None


    ##### Public Event Handlers ###############################################

    def on_read(self, data):
        """
        Placeholder. Called when data is read from the WebSocket.

        =========  ============
        Argument   Description
        =========  ============
        data       A chunk of data received from the socket. Binary data will be provided as a byte string, and text data will be provided as a unicode string.
        =========  ============
        """
        pass


    def on_write(self):
        """
        Placeholder. Called after the WebSocket has finished writing data.
        """
        pass


    def on_connect(self, *arguments):
        """
        Placeholder. Called after the WebSocket has connected to a client and
        completed its handshake. Any additional arguments passed to the
        :class:`WebSocket` instance's constructor will be passed to this
        method when it is invoked, making it easy to use :class:`WebSocket`
        together with the URL variables captured by
        :class:`pants.web.application.Application`, as shown in the
        following example::

            from pants.web import Application
            from pants.http import WebSocket

            app = Application()
            @app.route("/ws/<int:id>")
            class MyConnection(WebSocket):
                def on_connect(self, id):
                    pass
        """
        pass


    def on_close(self):
        """
        Placeholder. Called after the WebSocket has finished closing.
        """
        pass


    def on_handshake(self, request, headers):
        """
        Placeholder. Called during the initial handshake, making it possible to
        validate the request with custom logic, such as Origin checking and
        other forms of authentication.

        If this function returns a False value, the handshake will be stopped
        and an error will be sent to the client.

        =========  ============
        Argument   Description
        =========  ============
        request    The :class:`pants.http.server.HTTPRequest` being upgraded to a WebSocket.
        headers    An empty dict. Any values set here will be sent as headers when accepting (or rejecting) the connection.
        =========  ============
        """
        return True


    def on_pong(self, data):
        """
        Placeholder. Called when a PONG control frame is received from the
        remote end-point in response to an earlier ping.

        When used together with the :meth:`ping` method, ``on_pong`` may be
        used to measure the connection's round-trip time. See :meth:`ping` for
        more information.

        =========  ============
        Argument   Description
        =========  ============
        data       Either the RTT expressed as seconds, or an arbitrary byte string that served as the PONG frame's payload.
        =========  ============
        """
        pass


    def on_overflow_error(self, exception):
        """
        Placeholder. Called when an internal buffer on the WebSocket has
        exceeded its size limit.

        By default, logs the exception and closes the WebSocket.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        self.close(reason=1009)


    ##### I/O Methods #########################################################

    def ping(self, data=None):
        """
        Write a ping frame to the WebSocket. You may, optionally, provide a
        byte string of data to be used as the ping's payload. When the
        end-point returns a PONG, and the :meth:`on_pong` method is called,
        that byte string will be provided to ``on_pong``. Otherwise, ``on_pong``
        will be called with the elapsed time.

        =========  ============
        Argument   Description
        =========  ============
        data       *Optional.* A byte string of data to be sent as the ping's payload.
        =========  ============
        """
        if data is None:
            self._last_ping += 1
            data = str(self._last_ping)
            self._pings[data] = time()

        self.write(data, FRAME_PING)


    def write(self, data, frame=None, flush=False):
        """
        Write data to the WebSocket.

        Data will not be written immediately, but will be buffered internally
        until it can be sent without blocking the process.

        Calling :meth:`write` on a closed or disconnected WebSocket will raise
        a :exc:`RuntimeError`.

        If data is a unicode string, the data will be sent to the remote
        end-point as text using the frame opcode for text. If data is a byte
        string, the data will be sent to the remote end-point as binary data
        using the frame opcode for binary data. If you manually specify a frame
        opcode, the provided data *must* be a byte string.

        An appropriate header for the data will be generated by this method,
        using the length of the data and the frame opcode.

        ==========  ============================================================
        Arguments   Description
        ==========  ============================================================
        data        A string of data to write to the WebSocket. Unicode will be
                    converted automatically.
        frame       *Optional.* The frame opcode for this message.
        flush       *Optional.* If True, flush the internal write buffer. See
                    :meth:`pants.stream.Stream.flush` for details.
        ==========  ============================================================
        """
        if self._connection is None:
            raise RuntimeError("write() called on closed %r" % self)

        if not self.connected:
            raise RuntimeError("write() called on disconnected %r." % self)

        if frame is None:
            if isinstance(data, unicode):
                frame = FRAME_TEXT
                data = data.encode('utf-8')
            elif isinstance(data, bytes):
                frame = FRAME_BINARY
            else:
                raise TypeError("data must be unicode or bytes")

        elif frame == FRAME_TEXT:
            if isinstance(data, unicode):
                data = data.encode('utf-8')
            elif not isinstance(data, bytes):
                raise TypeError("data must be bytes or unicode for FRAME_TEXT.")

        elif not isinstance(data, bytes):
            raise TypeError("data must be bytes for frames other "
                            "than FRAME_TEXT.")

        if self.version == 0:
            if frame != FRAME_TEXT:
                raise TypeError("Attempted to send non-unicode data across "
                                "outdated WebSocket protocol.")

            self._connection.write(b"\x00" + data + b"\xFF", flush=flush)
            return

        header = chr(0x80 | frame)
        plen = len(data)
        if plen > 65535:
            header += b"\x7F" + STRUCT_Q.pack(plen)
        elif plen > 125:
            header += b"\x7E" + STRUCT_H.pack(plen)
        else:
            header += chr(plen)

        self._connection.write(header + data, flush=flush)


    def write_file(self, sfile, nbytes=0, offset=0, flush=False):
        """
        Write a file to the WebSocket.

        This method sends an entire file as one huge binary frame, so be
        careful with how you use it.

        Calling :meth:`write_file()` on a closed or disconnected WebSocket will
        raise a :exc:`RuntimeError`.

        ==========  ====================================================
        Arguments   Description
        ==========  ====================================================
        sfile       A file object to write to the WebSocket.
        nbytes      *Optional.* The number of bytes of the file to
                    write. If 0, all bytes will be written.
        offset      *Optional.* The number of bytes to offset writing
                    by.
        flush       *Optional.* If True, flush the internal write
                    buffer. See :meth:`~pants.stream.Stream.flush` for
                    details.
        ==========  ====================================================
        """
        if not self._connection:
            raise RuntimeError("write_file() called on closed %r." % self)
        elif not self.connected:
            raise RuntimeError("write_file() called on disconnected %r." % self)
        elif not self.version:
            raise TypeError("Attempted to send non-unicode data across "
                            "outdated WebSocket protocol.")

        # Determine the length we're sending.
        current_pos = sfile.tell()
        sfile.seek(0, 2)
        size = sfile.tell()
        sfile.seek(current_pos)

        if offset > size:
            raise ValueError("offset outsize of file size.")
        elif offset:
            size -= offset

        if nbytes == 0:
            nbytes = size
        elif nbytes < size:
            size = nbytes

        header = b"\x82"
        if size > 65535:
            header += b"\x7F" + STRUCT_Q.pack(size)
        elif size > 125:
            header += b"\x7E" + STRUCT_H.pack(size)
        else:
            header += chr(size)

        self._connection.write(header)
        self._connection.write_file(sfile, nbytes, offset, flush)


    def write_packed(self, *data, **kwargs):
        """
        Write packed binary data to the WebSocket.

        Calling :meth:`write_packed` on a closed or disconnected WebSocket will
        raise a :exc:`RuntimeError`.

        If the current :attr:`read_delimiter` is an instance of
        :class:`struct.Struct` or :class:`netstruct.NetStruct` the format
        will be read from that Struct, otherwise you will need to provide
        a ``format``.

        ==========  ====================================================
        Argument    Description
        ==========  ====================================================
        \*data      Any number of values to be passed through
                    :mod:`struct` and written to the remote host.
        format      *Optional.* A formatting string to pack the
                    provided data with. If one isn't provided, the read
                    delimiter will be used.
        flush       *Optional.* If True, flush the internal write
                    buffer. See :meth:`~pants.stream.Stream.flush` for
                    details.
        ==========  ====================================================
        """
        frame = kwargs.get("frame", FRAME_BINARY)

        if not self._connection:
            raise RuntimeError("write_packed() called on closed %r." % self)
        elif not self.connected:
            raise RuntimeError("write_packed() called on disconnected %r."
                               % self)
        elif not self.version and frame != FRAME_TEXT:
            raise TypeError("Attempted to send non-unicode data across "
                            "outdated WebSocket protocol.")

        format = kwargs.get("format", None)
        flush = kwargs.get("flush", False)

        if format:
            self.write(struct.pack(format, *data), frame=frame, flush=flush)

        elif not isinstance(self._read_delimiter, (Struct, _NetStruct)):
            raise ValueError("No format is available for writing packed data.")

        else:
            self.write(self._read_delimiter.pack(*data), frame=frame, flush=flush)


    ##### Internal Methods ####################################################

    def _safely_call(self, thing_to_call, *args, **kwargs):
        """
        Safely execute a callable.

        The callable is wrapped in a try block and executed. If an
        exception is raised it is logged.

        ==============  ============
        Argument        Description
        ==============  ============
        thing_to_call   The callable to execute.
        *args           The positional arguments to be passed to the callable.
        **kwargs        The keyword arguments to be passed to the callable.
        ==============  ============
        """
        try:
            return thing_to_call(*args, **kwargs)
        except Exception:
            log.exception("Exception raised on %r." % self)


    ##### Internal Event Handler Methods ######################################

    def _con_old_read(self, data):
        """
        Process incoming data, the old way.
        """
        self._recv_buffer += data

        while len(self._recv_buffer) >= 2:
            if self._expect_frame:
                self._expect_frame = False
                self._frame = ord(self._recv_buffer[0])
                self._recv_buffer = self._recv_buffer[1:]

                if self._frame & 0x80 == 0x80:
                    log.error("Unsupported frame type for old-style WebSockets %02X on %r." %
                        (self._frame, self))
                    self.close(False)
                    return

            # Simple Frame.
            ind = self._recv_buffer.find('\xFF')
            if ind == -1:
                if len(self._recv_buffer) > self._recv_buffer_size_limit:
                    # TODO: Callback for handling this event?
                    self.close(reason=1009)
                return

            # Read the data.
            try:
                data = self._recv_buffer[:ind].decode('utf-8')
            except UnicodeDecodeError:
                self.close(reason=1007)
                return

            if not self._read_buffer:
                self._read_buffer = data
                self._rb_type = type(self._read_buffer)
            else:
                self._read_buffer += data

            self._recv_buffer = self._recv_buffer[ind+1:]
            self._expect_frame = True

            # Act on the data.
            self._process_read_buffer()


    def _con_read(self, data):
        """
        Process incoming data.
        """
        self._recv_buffer += data

        while len(self._recv_buffer) >= 2:
            byte1 = ord(self._recv_buffer[0])
            final = 0x80 & byte1
            rsv1 = 0x40 & byte1
            rsv2 = 0x20 & byte1
            rsv3 = 0x10 & byte1
            opcode = 0x0F & byte1

            byte2 = ord(self._recv_buffer[1])
            mask = 0x80 & byte2
            length = 0x7F & byte2

            if length == 126:
                if len(self._recv_buffer) < 4:
                    return
                length = STRUCT_H.unpack(self._recv_buffer[2:4])
                headlen = 4

            elif length == 127:
                if len(self._recv_buffer) < 10:
                    return
                length = STRUCT_Q.unpack(self._recv_buffer[2:10])
                headlen = 10

            else:
                headlen = 2

            if mask:
                if len(self._recv_buffer) < headlen + 4:
                    return
                mask = [ord(x) for x in self._recv_buffer[headlen:headlen+4]]
                headlen += 4

            total_size = headlen + length
            if len(self._recv_buffer) < total_size:
                if len(self._recv_buffer) > self._recv_buffer_size_limit:
                    # TODO: Callback for handling this event?
                    self.close(reason=1009)
                return

            # Got a full message!
            data = self._recv_buffer[headlen:total_size]
            self._recv_buffer = self._recv_buffer[total_size:]

            if mask:
                new_data = ""
                for i in xrange(len(data)):
                    new_data += chr(ord(data[i]) ^ mask[i % 4])
                data = new_data
                del new_data

            # Control Frame Nonsense!
            if opcode == FRAME_CLOSE:
                if data:
                    reason = STRUCT_H.unpack(data[:2])[0]
                    message = data[2:]
                else:
                    reason = 1000
                    message = None

                self.close(True, reason, message)
                return

            elif opcode == FRAME_PING:
                if self.connected:
                    self.write(data, frame=FRAME_PONG)

            elif opcode == FRAME_PONG:
                sent = self._pings.pop(data, None)
                if sent:
                    data = time() - sent

                self._safely_call(self.on_pong, data)
                return

            elif opcode == FRAME_CONTINUATION:
                if not self._frag_frame:
                    self.close(reason=1002)
                    return

                opcode = self._frag_frame
                self._frag_frame = None

            if opcode == FRAME_TEXT:
                try:
                    data = data.decode('utf-8')
                except UnicodeDecodeError:
                    self.close(reason=1007)
                    return

            if not self._read_buffer:
                self._read_buffer = data
                self._rb_type = type(data)
            elif not isinstance(data, self._rb_type):
                # TODO: Improve wrong string type handling with event handler.
                log.error("Received string type not matching buffer on %r." % self)
                self.close(reason=1002)
                return
            else:
                self._read_buffer += data

            if not final:
                if not opcode in (FRAME_BINARY, FRAME_TEXT):
                    log.error("Received fragment control frame on %r." % self)
                    self.close(reason=1002)
                    return

                self._frag_frame = opcode
                if self._read_delimiter is EntireMessage:
                    return

            self._process_read_buffer()

            if self._read_buffer and len(self._read_buffer) > self._recv_buffer_size_limit:
                e = StreamBufferOverflow("Buffer length exceeded upper limit "
                                         "on %r." % self)
                self._safely_call(self.on_overflow_error, e)
                return


    def _con_close(self):
        """
        Close the WebSocket.
        """
        if hasattr(self, '_request'):
            del self._request
        if hasattr(self, '_headers'):
            del self._headers

        self.connected = False
        self._closed = True
        self._safely_call(self.on_close)
        self._connection = None


    def _con_write(self):
        if self.connected:
            self._safely_call(self.on_write)


    ##### Internal Processing Methods #########################################

    def _process_read_buffer(self):
        """
        Process the read_buffer. This is only used when the ReadDelimiter isn't
        EntireMessage.
        """
        while self._read_buffer:
            delimiter = self._read_delimiter

            if delimiter is None or delimiter is EntireMessage:
                data = self._read_buffer
                self._read_buffer = None
                self._rb_type = None
                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, (int, long)):
                size = len(self._read_buffer)
                if size < delimiter:
                    break
                elif size == delimiter:
                    data = self._read_buffer
                    self._read_buffer = None
                    self._rb_type = None
                else:
                    data = self._read_buffer[:delimiter]
                    self._read_buffer = self._read_buffer[delimiter:]

                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, (bytes, unicode)):
                if not isinstance(delimiter, self._rb_type):
                    log.error("buffer string type doesn't match read_delimiter "
                              "on %r." % self)
                    self.close(reason=1002)
                    break

                mark = self._read_buffer.find(delimiter)
                if mark == -1:
                    break
                else:
                    data = self._read_buffer[:mark]
                    self._read_buffer = self._read_buffer[mark + len(delimiter):]
                    if not self._read_buffer:
                        self._read_buffer = None
                        self._rb_type = None

                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, Struct):
                if self._rb_type is not bytes:
                    log.error("buffer is not bytes for struct read_delimiter "
                              "on %r." % self)
                    self.close(reason=1002)
                    break

                size = len(self._read_buffer)
                if size < delimiter.size:
                    break
                elif size == delimiter.size:
                    data = self._read_buffer
                    self._read_buffer = None
                    self._rb_type = None
                else:
                    data = self._read_buffer[:delimiter.size]
                    self._read_buffer = self._read_buffer[delimiter.size:]

                # Safely unpack it. This should *probably* never error.
                try:
                    data = delimiter.unpack(data)
                except struct.error:
                    log.exception("Unable to unpack data on %r." % self)
                    self.close(reason=1002)
                    break

                # Unlike most on_read calls, this one sends every variable of
                # the parsed data as its own argument.
                self._safely_call(self.on_read, *data)

            elif isinstance(delimiter, _NetStruct):
                if self._rb_type is not bytes:
                    log.error("buffer is not bytes for struct read_delimiter "
                              "on %r." % self)
                    self.close(reason=1002)
                    break

                if not self._netstruct_iter:
                    # We need to get started.
                    self._netstruct_iter = delimiter.iter_unpack()
                    self._netstruct_needed = next(self._netstruct_iter)

                size = len(self._read_buffer)
                if size < self._netstruct_needed:
                    break
                elif size == self._netstruct_needed:
                    data = self._read_buffer
                    self._read_buffer = None
                    self._rb_type = None
                else:
                    data = self._read_buffer[:self._netstruct_needed]
                    self._read_buffer = self._read_buffer[self._netstruct_needed:]

                data = self._netstruct_iter.send(data)
                if isinstance(data, (int, long)):
                    self._netstruct_needed = data
                    continue

                # Still here? Then we've got an object. Delete the NetStruct
                # state and send the data.
                self._netstruct_needed = None
                self._netstruct_iter = None

                self._safely_call(self.on_read, *data)

            elif isinstance(delimiter, RegexType):
                if not isinstance(delimiter.pattern, self._rb_type):
                    log.error("buffer string type does not match "
                              "read_delimiter on %r." % self)
                    self.close(reason=1002)
                    break

                # Depending on regex_search, we could do this two ways.
                if self.regex_search:
                    match = delimiter.search(self._read_buffer)
                    if not match:
                        break

                    data = self._read_buffer[:match.start()]
                    self._read_buffer = self._read_buffer[match.end():]
                    if not self._read_buffer:
                        self._read_buffer = None
                        self._rb_type = None

                else:
                    # Require the match to be at the beginning.
                    data = delimiter.match(self._read_buffer)
                    if not data:
                        break

                    self._read_buffer = self._read_buffer[data.end():]
                    if not self._read_buffer:
                        self._read_buffer = None
                        self._rb_type = None

                # Send either the string or the match object.
                self._safely_call(self.on_read, data)

            else:
                log.warning("Invalid read_delimiter on %r." % self)
                break

            if self._connection is None or not self.connected:
                break


###############################################################################
# Support Functions
###############################################################################

def challenge_response(headers, key3):
    """
    Calculate the response for a WebSocket security challenge and return it.
    """
    resp = hashlib.md5()

    for key in (headers.get('Sec-WebSocket-Key1'),
                headers.get('Sec-WebSocket-Key2')):
        n = ''
        s = 0
        for c in key:
            if c.isdigit(): n += c
            elif c == ' ': s += 1
        n = int(n)

        if n > 4294967295 or s == 0 or n % s != 0:
            raise ValueError("The provided keys aren't valid.")
        n /= s

        resp.update(
            chr(n >> 24 & 0xFF) +
            chr(n >> 16 & 0xFF) +
            chr(n >> 8  & 0xFF) +
            chr(n       & 0xFF)
        )

    resp.update(key3)
    return resp.digest()

########NEW FILE########
__FILENAME__ = server
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
Streaming (TCP) server implementation.

Servers are one of the two main types of channels in Pants - the other
being :mod:`streams <pants.stream>`. Servers listen for connections to
your application, accept those connections and allow you to handle them
easily. Pants servers support SSL and IPv6.

Servers
=======
Writing Servers
---------------
You have two choices when writing a server application: either use
Pants' default :class:`~pants.server.Server` class without modification
or subclass :class:`~pants.server.Server` in order to implement custom
behaviour.

Pants' default :class:`~pants.server.Server` class will wrap every new
connection in an instance of a connection class which you provide (see
below). In most cases, this provides you with sufficient freedom to
implement your application logic and has the added benefit of
simplicity. To use the default server, simply instantiate 
:class:`~pants.server.Server` and pass your connection class to the
constructor.

If you need to implement custom server behaviour, you can subclass
:class:`~pants.server.Server` and define your connection class as a
class attribute::

    class MyServer(pants.Server):
        ConnectionClass = MyConnectionClass

It is recommended that you use the default :class:`~pants.server.Server`
class where possible and try to implement your application logic in your
connection class.

Connection Classes
------------------
A connection class is a subclass of :class:`~pants.stream.Stream` which
a server will use to wrap each incoming connection. Every time a new
connection is made to the server, a new instance of your connection
class will be created to handle it. You can override the various event
handler methods of :class:`~pants.stream.Stream` to implement your
application's logic.

Running Servers
---------------
Having defined your connection class and instantiated your server, you
can start it listening for new connections with the
:meth:`~pants.server.Server.listen` method. This will bind the server
to your chosen address and once the :mod:`~pants.engine` is started,
the server will begin accepting new connections. Once the server has
started listening for connections it can be stopped using the
:meth:`~pants.server.Server.close` method. When
:meth:`~pants.server.Server.close` is called, the default server 
implementation will close any connections that were made to it which are
still open.

SSL
===
Pants servers have SSL support. If you want to start an SSL-enabled
server, call the :meth:`~pants.server.Server.startSSL` method before
calling the :meth:`~pants.server.Server.listen` method. When you call
:meth:`~pants.server.Server.startSSL` you must provide a dictionary of
SSL options as detailed in the method documentation. It is also
possible to pass the SSL options dictionary directly to the
:class:`~pants.server.Server` constructor in order to enable SSL.
Here is an example of how you might start an SSL-enabled server::

    server = pants.Server(MyConnectionClass)
    server.startSSL({
        'certfile': '/home/user/certfile.pem',
        'keyfile': '/home/user/keyfile.pem'
        })
    server.listen(('', 8080))

If you are writing an SSL-enabled application you should read the
entirety of Python's :mod:`ssl` documentation. Pants does not override
any of Python's SSL defaults unless clearly stated in this documentation.
"""

###############################################################################
# Imports
###############################################################################

import socket
import ssl
import weakref

from pants._channel import _Channel, HAS_IPV6, sock_type
from pants.stream import Stream


###############################################################################
# Logging
###############################################################################

import logging
log = logging.getLogger("pants")


###############################################################################
# Server Class
###############################################################################

class Server(_Channel):
    """
    A stream-oriented server channel.

    A :class:`~pants.server.Server` instance represents a local server
    capable of listening for connections from remote hosts over a
    connection-oriented protocol such as TCP/IP.

    =================  ================================================
    Keyword Argument   Description
    =================  ================================================
    engine             *Optional.* The engine to which the channel
                       should be added. Defaults to the global engine.
    socket             *Optional.* A pre-existing socket to wrap. This
                       can be a regular :py:obj:`~socket.socket` or an
                       :py:obj:`~ssl.SSLSocket`. If a socket is not
                       provided, a new socket will be created for the
                       channel when required.
    ssl_options        *Optional.* If provided,
                       :meth:`~pants.server.Server.startSSL` will be
                       called with these options once the server is
                       ready. By default, SSL will not be enabled.
    =================  ================================================
    """
    ConnectionClass = Stream

    def __init__(self, ConnectionClass=None, **kwargs):
        sock = kwargs.get("socket", None)
        if sock and sock_type(sock) != socket.SOCK_STREAM:
            raise TypeError("Cannot create a %s with a socket type other than SOCK_STREAM."
                    % self.__class__.__name__)

        _Channel.__init__(self, **kwargs)

        # Socket
        self._remote_address = None
        self._local_address = None

        self._slave = None

        # Channel state
        self.listening = False

        # SSL state
        self.ssl_enabled = False
        self._ssl_options = None
        if kwargs.get("ssl_options", None) is not None:
            self.startSSL(kwargs["ssl_options"])

        # Connection class
        if ConnectionClass is not None:
            self.ConnectionClass = ConnectionClass
        self.channels = weakref.WeakValueDictionary()

    ##### Properties ##########################################################

    @property
    def remote_address(self):
        """
        """
        return self._remote_address or self._socket.getpeername()

    @remote_address.setter
    def remote_address(self, val):
        self._remote_address = val

    @property
    def local_address(self):
        """
        """
        return self._local_address or self._socket.getsockname()

    @local_address.setter
    def local_address(self, val):
        self._local_address = val

    ##### Control Methods #####################################################

    def startSSL(self, ssl_options={}):
        """
        Enable SSL on the channel.

        Enabling SSL on a server channel will cause any new connections
        accepted by the server to be automatically wrapped in an SSL
        context before being passed to
        :meth:`~pants.server.Server.on_accept`. If an error occurs while
        a new connection is being wrapped,
        :meth:`~pants.server.Server.on_ssl_wrap_error` is called.

        SSL is enabled immediately. Typically, this method is called
        before :meth:`~pants.server.Server.listen`. If it is called
        afterwards, any connections made in the meantime will not have
        been wrapped in SSL contexts.

        The SSL options argument will be passed through to each
        invocation of :func:`ssl.wrap_socket` as keyword arguments - see
        the :mod:`ssl` documentation for further information. You will
        typically want to provide the ``keyfile``, ``certfile`` and
        ``ca_certs`` options. The ``do_handshake_on_connect`` option
        **must** be ``False`` and the ``server_side`` option **must** be
        true, or a :exc:`ValueError` will be raised.

        Attempting to enable SSL on a closed channel or a channel that
        already has SSL enabled on it will raise a :exc:`RuntimeError`.

        Returns the channel.

        ============ ===================================================
        Arguments    Description
        ============ ===================================================
        ssl_options  *Optional.* Keyword arguments to pass to
                     :func:`ssl.wrap_socket`.
        ============ ===================================================
        """
        if self.ssl_enabled:
            raise RuntimeError("startSSL() called on SSL-enabled %r." % self)

        if self._closed:
            raise RuntimeError("startSSL() called on closed %r." % self)

        if ssl_options.setdefault("server_side", True) is not True:
            raise ValueError("SSL option 'server_side' must be True.")

        if ssl_options.setdefault("do_handshake_on_connect", False) is not False:
            raise ValueError("SSL option 'do_handshake_on_connect' must be False.")

        self.ssl_enabled = True
        self._ssl_options = ssl_options

        return self

    def listen(self, address, backlog=1024, slave=True):
        """
        Begin listening for connections made to the channel.

        The given ``address`` is resolved, the channel is bound to the
        address and then begins listening for connections. Once the
        channel has begun listening,
        :meth:`~pants.server.Server.on_listen` will be called.

        Addresses can be represented in a number of different ways. A
        single string is treated as a UNIX address. A single integer is
        treated as a port and converted to a 2-tuple of the form
        ``('', port)``. A 2-tuple is treated as an IPv4 address and a
        4-tuple is treated as an IPv6 address. See the :mod:`socket`
        documentation for further information on socket addresses.

        If no socket exists on the channel, one will be created with a
        socket family appropriate for the given address.

        An error will occur if the given address is not of a valid
        format or of an inappropriate format for the socket (e.g. if an
        IP address is given to a UNIX socket).

        Calling :meth:`listen()` on a closed channel or a channel that
        is already listening will raise a :exc:`RuntimeError`.

        Returns the channel.

        ===============  ================================================
        Arguments        Description
        ===============  ================================================
        address          The local address to listen for connections on.
        backlog          *Optional.* The maximum size of the
                         connection queue.
        slave            *Optional.* If True, this will cause a
                         Server listening on IPv6 INADDR_ANY to
                         create a slave Server that listens on the
                         IPv4 INADDR_ANY.
        ===============  ================================================
        """
        if self.listening:
            raise RuntimeError("listen() called on active %r." % self)

        if self._closed:
            raise RuntimeError("listen() called on closed %r." % self)

        address, family, resolved = self._format_address(address)
        if not family:
            raise ValueError("Unable to determine address family from "
                             "address: %s" % repr(address))

        self._do_listen(address, family, backlog, slave)

        return self

    def close(self):
        """
        Close the channel.

        The channel will be closed immediately and will cease to accept
        new connections. Any connections accepted by this channel will
        remain open and will need to be closed separately. If this
        channel has an IPv4 slave (see
        :meth:`~pants.server.Server.listen`) it will be closed.

        Once closed, a channel cannot be re-opened.
        """
        if self._closed:
            return

        self.listening = False

        self.ssl_enabled = False

        if self._slave:
            self._slave.close()

        self._safely_call(self.on_close)

        self._remote_address = None
        self._local_address = None

        _Channel.close(self)

    ##### Public Event Handlers ###############################################

    def on_accept(self, socket, addr):
        """
        Called after the channel has accepted a new connection.

        Create a new instance of
        :attr:`~pants.server.Server.ConnectionClass` to wrap the socket
        and add it to the server.

        =========  ============
        Argument   Description
        =========  ============
        sock       The newly connected socket object.
        addr       The new socket's address.
        =========  ============
        """
        connection = self.ConnectionClass(engine=self.engine, socket=socket)
        connection.server = self
        self.channels[connection.fileno] = connection
        connection._handle_connect_event()

    def on_close(self):
        """
        Called after the channel has finished closing.

        Close all active connections to the server.
        """
        for channel in self.channels.values():
            channel.close(flush=False)

    ##### Public Error Handlers ###############################################

    def on_ssl_wrap_error(self, sock, addr, exception):
        """
        Placeholder. Called when an error occurs while wrapping a new
        connection with an SSL context.

        By default, logs the exception and closes the new connection.

        ==========  ============
        Argument    Description
        ==========  ============
        sock        The newly connected socket object.
        addr        The new socket's address.
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        try:
            sock.close()
        except socket.error:
            pass

    ##### Internal Methods ####################################################

    def _do_listen(self, addr, family, backlog, slave):
        """
        A callback method to be used with
        :meth:`~pants._channel._Channel._resolve_addr` - either listens
        immediately or notifies the user of an error.

        =========  =====================================================
        Argument   Description
        =========  =====================================================
        backlog    The maximum size of the connection queue.
        slave      If True, this will cause a Server listening on
                   IPv6 INADDR_ANY to create a slave Server that
                   listens on the IPv4 INADDR_ANY.
        addr       The address to listen on or None if address
                   resolution failed.
        family     The detected socket family or None if address
                   resolution failed.
        error      *Optional.* Error information or None if no error
                   occurred.
        =========  =====================================================
        """
        if self._socket:
            if self._socket.family != family:
                self.engine.remove_channel(self)
                self._socket_close()
                self._closed = False

        sock = socket.socket(family, socket.SOCK_STREAM)
        self._socket_set(sock)
        self.engine.add_channel(self)

        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass

        if hasattr(socket, "IPPROTO_IPV6") and hasattr(socket, "IPV6_V6ONLY")\
                and family == socket.AF_INET6:
            self._socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            slave = False

        try:
            self._socket_bind(addr)
            self._socket_listen(backlog)
        except socket.error as err:
            self.close()
            raise

        self.listening = True
        self._safely_call(self.on_listen)

        if slave and not isinstance(addr, str) and addr[0] == '' and HAS_IPV6:
            # Silently fail if we can't make a slave.
            try:
                self._slave = _SlaveServer(self.engine, self, addr, backlog)
            except Exception:
                self._slave = None

    ##### Internal Event Handler Methods ######################################

    def _handle_read_event(self):
        """
        Handle a read event raised on the channel.
        """
        while True:
            try:
                sock, addr = self._socket_accept()
            except socket.error:
                log.exception("Exception raised by accept() on %r." % self)
                try:
                    sock.close()
                except socket.error:
                    pass
                return

            if sock is None:
                return

            if self.ssl_enabled:
                try:
                    sock.setblocking(False)
                    sock = ssl.wrap_socket(sock, **self._ssl_options)
                except ssl.SSLError as e:
                    self._safely_call(self.on_ssl_wrap_error, sock, addr, e)
                    continue

            self._safely_call(self.on_accept, sock, addr)

    def _handle_write_event(self):
        """
        Handle a write event raised on the channel.
        """
        log.warning("Received write event for %r." % self)


###############################################################################
# _SlaveServer Class
###############################################################################

class _SlaveServer(Server):
    """
    A slave for a StreamServer to allow listening on multiple address
    families.
    """
    def __init__(self, engine, server, addr, backlog):
        Server.__init__(self, engine=engine)
        self.server = server

        # Now, listen our way.
        if server._socket.family == socket.AF_INET6:
            family = socket.AF_INET
        else:
            family = socket.AF_INET6

        sock = socket.socket(family, socket.SOCK_STREAM)
        self._socket_set(sock)
        self.engine.add_channel(self)

        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass

        try:
            self._socket_bind(addr)
            self._socket_listen(backlog)
        except socket.error as err:
            self.close()
            raise

        self._remote_address = None
        self._local_address = None

        self.listening = True

        self.on_accept = self.server.on_accept

    def on_close(self):
        if self.server._slave == self:
            self.server._slave = None

########NEW FILE########
__FILENAME__ = stream
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
Streaming (TCP) connection implementation.

Streams are one of the two main types of channels in Pants - the other
being :mod:`servers <pants.server>`. Streams represent connections
between two endpoints. They may be used for both client and server
applications.

Streams
=======
To write a Pants application you will first need to subclass
:class:`~pants.stream.Stream`. Your :class:`~pants.stream.Stream`
subclass will contain the majority of your networking code in the form
of event handlers. Event handlers are methods beginning with ``on_`` and
can be safely overridden by your subclass.

Connecting
----------
Before a :class:`~pants.stream.Stream` instance can be used, it must
first be connected to a remote host. If you are writing a server
application, all new :class:`~pants.stream.Stream` instance created by
your :class:`~pants.server.Server` will be connected. Once they are
created by the :class:`~pants.server.Server`,
:meth:`~pants.stream.Stream.on_connect` will be called and your
:class:`~pants.engine.Engine` will begin dispatching events to your
:class:`~pants.stream.Stream` instance.

If you are writing a client application, you must first instantiate your
:class:`~pants.stream.Stream` subclass and then use the
:meth:`~pants.stream.Stream.connect` method to connect the channel to a
remote host. Once the connection has been successfully established, the
:meth:`~pants.stream.Stream.on_connect` event handler will be called and
your :class:`~pants.stream.Stream` instance will start receiving events.
Bear in mind that the connection will not be established until the
:class:`~pants.engine.Engine` is running. As such, a common pattern when
writing client applications with Pants is to call
:meth:`~pants.stream.Stream.connect`, start the engine and then put all
other initialization code in :meth:`~pants.stream.Stream.on_connect`.

Writing Data
------------
Once your :class:`~pants.stream.Stream` instance is connected to a
remote host, you can begin to write data to the channel. Use
:meth:`~pants.stream.Stream.write` to write string data to the channel,
:meth:`~pants.stream.Stream.write_file` to efficiently write data from
an open file and :meth:`~pants.stream.Stream.write_packed` to write
packed binary data. As you call these methods, Pants internally buffers
your outgoing data. Once the buffer is completely empty,
:meth:`~pants.stream.Stream.on_write` will be called. Be aware that if
you continuously write data to your :class:`~pants.stream.Stream` that
:meth:`~pants.stream.Stream.on_write` may not be called very frequently.
If you wish to bypass the internal buffering and attempt to write your
data immediately you can use the ``flush`` options present in the three
write methods or call the :meth:`~pants.stream.Stream.flush` method
yourself. This can help to improve your application's responsiveness but
calling it excessively can reduce overall performance. Generally
speaking, it is useful when you know with certainty that you have
finished writing one discrete chunk of data (i.e. an HTTP response).

Reading Data
------------
A connected :class:`~pants.stream.Stream` instance will automatically
receive all incoming data from the remote host. By default, all incoming
data is immediately passed to the :meth:`~pants.stream.Stream.on_read`
event handler for your code to process. The
:attr:`~pants.stream.Stream.read_delimiter` attribute can be used to
control this behaviour by causing Pants to buffer incoming data
internally, only forwarding it to :meth:`~pants.stream.Stream.on_read`
when a particular condition is met. If the condition is never met, the
internal buffer will eventually exceed the allowed
:attr:`~pants.stream.Stream.buffer_size` and the
:meth:`~pants.stream.Stream.on_overflow_error` handler method will be
called. :attr:`~pants.stream.Stream.read_delimiter` is extremely
powerful when used effectively.

Closing
-------
To close a :class:`~pants.stream.Stream` instance, simply call the
:meth:`~pants.stream.Stream.close` method. Once a stream has been closed
it should not be reused.

Handling Errors
---------------
Despite best efforts, errors will occasionally occur in asynchronous
code. Pants handles these errors by passing the resulting exception
object to one of a number of error handler methods. They are:
:meth:`~pants.stream.Stream.on_connect_error`,
:meth:`~pants.stream.Stream.on_overflow_error` and
:meth:`~pants.stream.Stream.on_error`. Additionally, 
:meth:`~pants.stream.Stream.on_ssl_handshake_error` and
:meth:`~pants.stream.Stream.on_ssl_error` exist to handle SSL-specific
errors.

SSL
===
Pants streams have SSL support. If you are writing a server application,
use :meth:`Server.startSSL <pants.server.Server.startSSL>` to enable SSL
on your server. Each :class:`~pants.stream.Stream` created by your
server from that point forward will be SSL-enabled. If you are writing a
client application, call
:meth:`Stream.startSSL <pants.stream.Stream.startSSL>` before calling
:meth:`~pants.stream.Stream.connect`. Alternatively, you can pass a
dictionary of SSL options to the :class:`~pants.stream.Stream`
constructor which will then enable SSL on the instance. When SSL is
enabled on a :class:`~pants.stream.Stream`, an SSL handshake occurs
between the local and remote ends of the connection. Once the SSL
handshake is complete, :meth:`~pants.stream.Stream.on_ssl_handshake`
will be called. If it fails,
:meth:`~pants.stream.Stream.on_ssl_handshake_error` will be called.

If you are writing an SSL-enabled application you should read the
entirety of Python's :mod:`ssl` documentation. Pants does not override
any of Python's SSL defaults unless clearly stated in this documentation.
"""

###############################################################################
# Imports
###############################################################################

import errno
import functools
import os
import re
import socket
import ssl
import struct

from pants._channel import _Channel, HAS_IPV6, sock_type
from pants.engine import Engine


try:
    from netstruct import NetStruct as _NetStruct
except ImportError:
    # Create the fake class because isinstance expects a class.
    class _NetStruct(object):
        def __init__(self, *a, **kw):
            raise NotImplementedError


###############################################################################
# Constants
###############################################################################

RegexType = type(re.compile(""))
Struct = struct.Struct


###############################################################################
# Logging
###############################################################################

import logging
log = logging.getLogger("pants")


###############################################################################
# Stream Class
###############################################################################

class Stream(_Channel):
    """
    The stream-oriented connection channel.

    A :class:`~pants.stream.Stream` instance represents either a local
    connection to a remote server or a remote connection to a local
    server over a streaming, connection-oriented protocol such as TCP.

    =================  ================================================
    Keyword Argument   Description
    =================  ================================================
    engine             *Optional.* The engine to which the channel
                       should be added. Defaults to the global engine.
    socket             *Optional.* A pre-existing socket to wrap. This
                       can be a regular :py:obj:`~socket.socket` or an
                       :py:obj:`~ssl.SSLSocket`. If a socket is not
                       provided, a new socket will be created for the
                       channel when required.
    ssl_options        *Optional.* If provided,
                       :meth:`~pants.stream.Stream.startSSL` will be
                       called with these options once the stream is
                       ready. By default, SSL will not be enabled.
    =================  ================================================
    """
    SEND_STRING = 0
    SEND_FILE = 1
    SEND_SSL_HANDSHAKE = 2

    def __init__(self, **kwargs):
        sock = kwargs.get("socket", None)
        if sock and sock_type(sock) != socket.SOCK_STREAM:
            raise TypeError("Cannot create a %s with a socket type other than SOCK_STREAM."
                    % self.__class__.__name__)

        _Channel.__init__(self, **kwargs)

        # Socket
        self._remote_address = None
        self._local_address = None

        # I/O attributes
        self._read_delimiter = None
        self._recv_buffer = ""
        self._recv_buffer_size_limit = self._buffer_size
        self._send_buffer = []

        # Channel state
        self.connected = False
        self.connecting = False
        self._closing = False

        # SSL state
        self.ssl_enabled = False
        self._ssl_enabling = False
        self._ssl_socket_wrapped = False
        self._ssl_handshake_done = False
        self._ssl_call_on_connect = False
        if isinstance(kwargs.get("socket", None), ssl.SSLSocket):
            self._ssl_socket_wrapped = True
            self.startSSL()
        elif kwargs.get("ssl_options", None) is not None:
            self.startSSL(kwargs["ssl_options"])

    ##### Properties ##########################################################

    @property
    def remote_address(self):
        """
        The remote address to which the channel is connected.

        By default, this will be the value of ``socket.getpeername`` or
        None. It is possible for user code to override the default
        behaviour and set the value of the property manually. In order
        to return the property to its default behaviour, user code then
        has to delete the value. Example::

            # default behaviour
            channel.remote_address = custom_value
            # channel.remote_address will return custom_value now
            del channel.remote_address
            # default behaviour
        """
        if self._remote_address is not None:
            return self._remote_address
        elif self._socket:
            try:
                return self._socket.getpeername()
            except socket.error:
                return None
        else:
            return None

    @remote_address.setter
    def remote_address(self, val):
        self._remote_address = val

    @remote_address.deleter
    def remote_address(self):
        self._remote_address = None

    @property
    def local_address(self):
        """
        The address of the channel on the local machine.

        By default, this will be the value of ``socket.getsockname`` or
        None. It is possible for user code to override the default
        behaviour and set the value of the property manually. In order
        to return the property to its default behaviour, user code then
        has to delete the value. Example::

            # default behaviour
            channel.local_address = custom_value
            # channel.local_address will return custom_value now
            del channel.local_address
            # default behaviour
        """
        if self._local_address is not None:
            return self._local_address
        elif self._socket:
            try:
                return self._socket.getsockname()
            except socket.error:
                return None
        else:
            return None

    @local_address.setter
    def local_address(self, val):
        self._local_address = val

    @local_address.deleter
    def local_address(self):
        self._local_address = None

    @property
    def read_delimiter(self):
        """
        The magical read delimiter which determines how incoming data is
        buffered by the stream.

        As data is read from the socket, it is buffered internally by
        the stream before being passed to the :meth:`on_read` callback. The
        value of the read delimiter determines when the data is passed to the
        callback. Valid values are ``None``, a byte string, an integer/long,
        a compiled regular expression, an instance of :class:`struct.Struct`,
        or an instance of :class:`netstruct.NetStruct`.

        When the read delimiter is ``None``, data will be passed to
        :meth:`on_read` immediately after it is read from the socket. This is
        the default behaviour.

        When the read delimiter is a byte string, data will be buffered
        internally until that string is encountered in the incoming
        data. All data up to but excluding the read delimiter is then
        passed to :meth:`on_read`. The segment matching the read delimiter
        itself is discarded from the buffer.

        When the read delimiter is an integer or a long, it is treated
        as the number of bytes to read before passing the data to
        :meth:`on_read`.

        When the read delimiter is a :class:`struct.Struct` instance, the
        Struct's ``size`` is fully buffered and the data is unpacked using the
        Struct before its sent to :meth:`on_read`. Unlike other types of read
        delimiters, this can result in more than one argument being passed to
        :meth:`on_read`, as in the following example::

            import struct
            from pants import Stream

            class Example(Stream):
                def on_connect(self):
                    self.read_delimiter = struct.Struct("!LLH")

                def on_read(self, packet_type, length, id):
                    pass

        When the read delimiter is an instance of :class:`netstruct.NetStruct`,
        the NetStruct's :attr:`~netstruct.NetStruct.minimum_size` is buffered
        and unpacked with the NetStruct, and additional data is buffered as
        necessary until the NetStruct can be completely unpacked. Once ready,
        the data will be passed to :meth:`on_read`. Using Struct and NetStruct
        are *very* similar.

        When the read delimiter is a compiled regular expression
        (:class:`re.RegexObject`), there are two possible behaviors that you
        may switch between by setting the value of :attr:`regex_search`. If
        :attr:`regex_search` is True, as is the default, the delimiter's
        :meth:`~re.RegexObject.search` method is used and, if a match is found,
        the string before that match is passed to :meth:`on_read`. The segment
        that was matched by the regular expression will be discarded.

        If :attr:`regex_search` is False, the delimiter's
        :meth:`~re.RegexObject.match` method is used instead and, if a match
        is found, the match object itself will be passed to :meth:`on_read`,
        giving you access to the capture groups. Again, the segment that was
        matched by the regular expression will be discarded from the buffer.

        Attempting to set the read delimiter to any other value will
        raise a :exc:`TypeError`.

        The effective use of the read delimiter can greatly simplify the
        implementation of certain protocols.
        """
        return self._read_delimiter

    @read_delimiter.setter
    def read_delimiter(self, value):
        if value is None or isinstance(value, basestring) or \
                isinstance(value, RegexType):
            self._read_delimiter = value
            self._recv_buffer_size_limit = self._buffer_size

        elif isinstance(value, (int, long)):
            self._read_delimiter = value
            self._recv_buffer_size_limit = max(self._buffer_size, value)

        elif isinstance(value, Struct):
            self._read_delimiter = value
            self._recv_buffer_size_limit = max(self._buffer_size, value.size)

        elif isinstance(value, _NetStruct):
            self._read_delimiter = value
            self._recv_buffer_size_limit = max(self._buffer_size,
                                               value.minimum_size)

        else:
            raise TypeError("Attempted to set read_delimiter to a value with an invalid type.")

        # Reset NetStruct state when we change the read delimiter.
        self._netstruct_iter = None
        self._netstruct_needed = None

    # Setting these at the class level makes them easy to override on a
    # per-class basis.
    regex_search = True
    _buffer_size = 2 ** 16  # 64kb

    @property
    def buffer_size(self):
        """
        The maximum size, in bytes, of the internal buffer used for
        incoming data.

        When buffering data it is important to ensure that inordinate
        amounts of memory are not used. Setting the buffer size to a
        sensible value can prevent coding errors or malicious use from
        causing your application to consume increasingly large amounts
        of memory. By default, a maximum of 64kb of data will be stored.

        The buffer size is mainly relevant when using a string value for
        the :attr:`~pants.stream.Stream.read_delimiter`. Because you
        cannot guarantee that the string will appear, having an upper
        limit on the size of the data is appropriate.

        If the read delimiter is set to a number larger than the buffer
        size, the buffer size will be increased to accommodate the read
        delimiter.

        When the internal buffer's size exceeds the maximum allowed, the
        :meth:`~pants.stream.Stream.on_overflow_error` callback will be
        invoked.

        Attempting to set the buffer size to anything other than an
        integer or long will raise a :exc:`TypeError`.
        """
        return self._buffer_size

    @buffer_size.setter
    def buffer_size(self, value):
        if not isinstance(value, (long, int)):
            raise TypeError("buffer_size must be an int or a long")
        self._buffer_size = value
        if isinstance(self._read_delimiter, (int, long)):
            self._recv_buffer_size_limit = max(value, self._read_delimiter)
        elif isinstance(self._read_delimiter, Struct):
            self._recv_buffer_size_limit = max(value,
                                               self._read_delimiter.size)
        elif isinstance(self._read_delimiter, _NetStruct):
            self._recv_buffer_size_limit = max(value,
                                            self._read_delimiter.minimum_size)
        else:
            self._recv_buffer_size_limit = value

    ##### Control Methods #####################################################

    def startSSL(self, ssl_options={}):
        """
        Enable SSL on the channel and perform a handshake at the next
        opportunity.

        SSL is only enabled on a channel once all currently pending data
        has been written. If a problem occurs at this stage,
        :meth:`~pants.stream.Stream.on_ssl_error` is called. Once SSL
        has been enabled, the SSL handshake begins - this typically
        takes some time and may fail, in which case
        :meth:`~pants.stream.Stream.on_ssl_handshake_error` will be
        called. When the handshake is successfully completed,
        :meth:`~pants.stream.Stream.on_ssl_handshake` is called and the
        channel is secure.

        Typically, this method is called before
        :meth:`~pants.stream.Stream.connect`. In this case,
        :meth:`~pants.stream.Stream.on_ssl_handshake` will be called
        before :meth:`~pants.stream.Stream.on_connect`. If
        :meth:`~pants.stream.Stream.startSSL` is called after
        :meth:`~pants.stream.Stream.connect`, the reverse is true.

        It is possible, although unusual, to start SSL on a channel that
        is already connected and active. In this case, as noted above,
        SSL will only be enabled and the handshake performed after all
        currently pending data has been written.

        The SSL options argument will be passed through to
        :func:`ssl.wrap_socket` as keyword arguments - see the
        :mod:`ssl` documentation for further information. You will
        typically want to provide the ``keyfile``, ``certfile`` and
        ``ca_certs`` options. The ``do_handshake_on_connect`` option
        **must** be ``False``, or a :exc:`ValueError` will be raised.

        Attempting to enable SSL on a closed channel or a channel that
        already has SSL enabled on it will raise a :exc:`RuntimeError`.

        Returns the channel.

        ============ ===================================================
        Arguments    Description
        ============ ===================================================
        ssl_options  *Optional.* Keyword arguments to pass to
                     :func:`ssl.wrap_socket`.
        ============ ===================================================
        """
        if self.ssl_enabled or self._ssl_enabling:
            raise RuntimeError("startSSL() called on SSL-enabled %r" % self)

        if self._closed or self._closing:
            raise RuntimeError("startSSL() called on closed %r" % self)

        if ssl_options.setdefault("do_handshake_on_connect", False) is not False:
            raise ValueError("SSL option 'do_handshake_on_connect' must be False.")

        self._ssl_enabling = True
        self._send_buffer.append((Stream.SEND_SSL_HANDSHAKE, ssl_options))

        if self.connected:
            self._process_send_buffer()

        return self

    def connect(self, address):
        """
        Connect the channel to a remote socket.

        The given ``address`` is resolved and used by the channel to
        connect to the remote server. If an error occurs at any stage in
        this process, :meth:`~pants.stream.Stream.on_connect_error` is
        called. When a connection is successfully established,
        :meth:`~pants.stream.Stream.on_connect` is called.

        Addresses can be represented in a number of different ways. A
        single string is treated as a UNIX address. A single integer is
        treated as a port and converted to a 2-tuple of the form
        ``('', port)``. A 2-tuple is treated as an IPv4 address and a
        4-tuple is treated as an IPv6 address. See the :mod:`socket`
        documentation for further information on socket addresses.

        If no socket exists on the channel, one will be created with a
        socket family appropriate for the given address.

        An error will occur during the connection if the given address
        is not of a valid format or of an inappropriate format for the
        socket (e.g. if an IP address is given to a UNIX socket).

        Calling :meth:`connect()` on a closed channel or a channel that
        is already connected will raise a :exc:`RuntimeError`.

        Returns the channel.

        ===============  ===============================================
        Arguments        Description
        ===============  ===============================================
        address          The remote address to connect to.
        ===============  ===============================================
        """
        if self.connected or self.connecting:
            raise RuntimeError("connect() called on active %r." % self)

        if self._closed or self._closing:
            raise RuntimeError("connect() called on closed %r." % self)

        self.connecting = True

        address, family, resolved = self._format_address(address)

        if resolved:
            self._do_connect(address, family)
        else:
            try:
                result = socket.getaddrinfo(address[0], address[1], family)
            except socket.error as err:
                self.close(flush=False)
                e = StreamConnectError(err.errno, err.strerror)
                self._safely_call(self.on_connect_error, e)
                return self

            # We only care about the first result.
            result = result[0]
            self._do_connect(result[-1], result[0])

        return self

    def close(self, flush=True):
        """
        Close the channel.
        """
        if self._closed:
            return

        if flush and self._send_buffer:
            self._closing = True
            return

        self.read_delimiter = None
        self._recv_buffer = ""
        self._send_buffer = []

        self.connected = False
        self.connecting = False

        self.ssl_enabled = False
        self._ssl_enabling = False
        self._ssl_socket_wrapped = False
        self._ssl_handshake_done = False
        self._ssl_call_on_connect = False

        self._safely_call(self.on_close)

        self._remote_address = None
        self._local_address = None

        _Channel.close(self)

        self._closing = False

    ##### I/O Methods #########################################################

    def write(self, data, flush=False):
        """
        Write data to the channel.

        Data will not be written immediately, but will be buffered
        internally until it can be sent without blocking the process.

        Calling :meth:`write()` on a closed or disconnected channel will
        raise a :exc:`RuntimeError`.

        ==========  ===================================================
        Arguments   Description
        ==========  ===================================================
        data        A string of data to write to the channel.
        flush       *Optional.* If True, flush the internal write
                    buffer. See :meth:`~pants.stream.Stream.flush` for
                    details.
        ==========  ===================================================
        """
        if self._closed or self._closing:
            raise RuntimeError("write() called on closed %r." % self)

        if not self.connected:
            raise RuntimeError("write() called on disconnected %r." % self)

        if self._send_buffer and self._send_buffer[-1][0] == Stream.SEND_STRING:
            data_type, existing_data = self._send_buffer.pop(-1)
            data = existing_data + data

        self._send_buffer.append((Stream.SEND_STRING, data))

        if flush:
            self._process_send_buffer()
        else:
            self._start_waiting_for_write_event()

    def write_file(self, sfile, nbytes=0, offset=0, flush=False):
        """
        Write a file to the channel.

        The file will not be written immediately, but will be buffered
        internally until it can be sent without blocking the process.

        Calling :meth:`write_file()` on a closed or disconnected channel
        will raise a :exc:`RuntimeError`.

        ==========  ====================================================
        Arguments   Description
        ==========  ====================================================
        sfile       A file object to write to the channel.
        nbytes      *Optional.* The number of bytes of the file to
                    write. If 0, all bytes will be written.
        offset      *Optional.* The number of bytes to offset writing
                    by.
        flush       *Optional.* If True, flush the internal write
                    buffer. See :meth:`~pants.stream.Stream.flush` for
                    details.
        ==========  ====================================================
        """
        if self._closed or self._closing:
            raise RuntimeError("write_file() called on closed %r." % self)

        if not self.connected:
            raise RuntimeError("write_file() called on disconnected %r." % self)

        self._send_buffer.append((Stream.SEND_FILE, (sfile, offset, nbytes)))

        if flush:
            self._process_send_buffer()
        else:
            self._start_waiting_for_write_event()

    def write_packed(self, *data, **kwargs):
        """
        Write packed binary data to the channel.

        If the current :attr:`read_delimiter` is an instance of
        :class:`struct.Struct` or :class:`netstruct.NetStruct` the format will
        be read from that Struct, otherwise you will need to
        provide a ``format``.

        ==========  ====================================================
        Argument    Description
        ==========  ====================================================
        \*data      Any number of values to be passed through
                    :mod:`struct` and written to the remote host.
        flush       *Optional.* If True, flush the internal write
                    buffer. See :meth:`~pants.stream.Stream.flush`
                    for details.
        format      *Optional.* A formatting string to pack the
                    provided data with. If one isn't provided, the read
                    delimiter will be used.
        ==========  ====================================================
        """
        format = kwargs.get("format")
        if format:
            self.write(struct.pack(format, *data), kwargs.get("flush", False))
        elif not isinstance(self._read_delimiter, (Struct, _NetStruct)):
            raise ValueError("No format is available for writing packed data.")
        else:
            self.write(self._read_delimiter.pack(*data),
                       kwargs.get("flush", False))

    def flush(self):
        """
        Attempt to immediately write any internally buffered data to the
        channel without waiting for a write event.

        This method can be fairly expensive to call and should be used
        sparingly.

        Calling :meth:`flush()` on a closed or disconnected channel will
        raise a :exc:`RuntimeError`.
        """
        if self._closed or self._closing:
            raise RuntimeError("flush() called on closed %r." % self)

        if not self.connected:
            raise RuntimeError("flush() called on disconnected %r." % self)

        if not self._send_buffer:
            return

        self._stop_waiting_for_write_event()
        self._process_send_buffer()

    ##### Public Event Handlers ###############################################

    def on_ssl_handshake(self):
        """
        Placeholder. Called after the channel has finished its SSL
        handshake.
        """
        pass

    ##### Public Error Handlers ###############################################

    def on_ssl_handshake_error(self, exception):
        """
        Placeholder. Called when an error occurs during the SSL
        handshake.

        By default, logs the exception and closes the channel.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        self.close(flush=False)

    def on_ssl_error(self, exception):
        """
        Placeholder. Called when an error occurs in the underlying SSL
        implementation.

        By default, logs the exception and closes the channel.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        self.close(flush=False)

    ##### Internal Methods ####################################################

    def _do_connect(self, address, family, error=None):
        """
        A callback method to be used with
        :meth:`~pants._channel._Channel._resolve_addr` - either connects
        immediately or notifies the user of an error.

        =========  =====================================================
        Argument   Description
        =========  =====================================================
        address    The address to connect to or None if address
                   resolution failed.
        family     The detected socket family or None if address
                   resolution failed.
        error      *Optional.* Error information or None if no error
                   occurred.
        =========  =====================================================
        """
        if not address:
            self.connecting = False
            e = StreamConnectError(*error)
            self._safely_call(self.on_connect_error, e)
            return

        if self._socket:
            if self._socket.family != family:
                self.engine.remove_channel(self)
                self._socket_close()
                self._closed = False

        sock = socket.socket(family, socket.SOCK_STREAM)
        self._socket_set(sock)
        self.engine.add_channel(self)

        try:
            connected = self._socket_connect(address)
        except socket.error as err:
            self.close(flush=False)
            e = StreamConnectError(err.errno, err.strerror)
            self._safely_call(self.on_connect_error, e)
            return

        if connected:
            self._handle_connect_event()

    ##### Internal Event Handler Methods ######################################

    def _handle_read_event(self):
        """
        Handle a read event raised on the channel.
        """
        if self.ssl_enabled and not self._ssl_handshake_done:
            self._ssl_do_handshake()
            return

        while True:
            try:
                data = self._socket_recv()
            except socket.error as err:
                self._safely_call(self.on_read_error, err)
                return

            if not data:
                break
            else:
                self._recv_buffer += data

                if len(self._recv_buffer) > self._recv_buffer_size_limit:
                    # Try processing the buffer to reduce its length.
                    self._process_recv_buffer()

                    # If the buffer's still too long, overflow error.
                    if len(self._recv_buffer) > self._recv_buffer_size_limit:
                        e = StreamBufferOverflow("Buffer length exceeded upper limit on %r." % self)
                        self._safely_call(self.on_overflow_error, e)
                        return

        self._process_recv_buffer()

        # This block was moved out of the above loop to address issue #41.
        if data is None:
            self.close(flush=False)

    def _handle_write_event(self):
        """
        Handle a write event raised on the channel.
        """
        if self.ssl_enabled and not self._ssl_handshake_done:
            self._ssl_do_handshake()
            return

        if not self.connected:
            self._handle_connect_event()

        if not self._send_buffer:
            return

        self._process_send_buffer()

    def _handle_error_event(self):
        """
        Handle an error event raised on the channel.
        """
        if self.connecting:
            # That's no moon...
            self._handle_connect_event()
        else:
            _Channel._handle_error_event(self)

    def _handle_connect_event(self):
        """
        Handle a connect event raised on the channel.
        """
        self.connecting = False
        err, errstr = self._get_socket_error()
        if err == 0:
            self.connected = True
            if self._ssl_enabling:
                self._ssl_call_on_connect = True
                self._process_send_buffer()
            else:
                self._safely_call(self.on_connect)
        else:
            # ... it's a space station!
            e = StreamConnectError(err, errstr)
            self._safely_call(self.on_connect_error, e)

    ##### Internal Processing Methods #########################################

    def _process_recv_buffer(self):
        """
        Process the :attr:`~pants.stream.Stream._recv_buffer`, passing
        chunks of data to :meth:`~pants.stream.Stream.on_read`.
        """
        while self._recv_buffer:
            delimiter = self.read_delimiter

            if delimiter is None:
                data = self._recv_buffer
                self._recv_buffer = ""
                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, (int, long)):
                if len(self._recv_buffer) < delimiter:
                    break
                data = self._recv_buffer[:delimiter]
                self._recv_buffer = self._recv_buffer[delimiter:]
                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, basestring):
                mark = self._recv_buffer.find(delimiter)
                if mark == -1:
                    break
                data = self._recv_buffer[:mark]
                self._recv_buffer = self._recv_buffer[mark + len(delimiter):]
                self._safely_call(self.on_read, data)

            elif isinstance(delimiter, Struct):
                if len(self._recv_buffer) < delimiter.size:
                    break
                data = self._recv_buffer[:delimiter.size]
                self._recv_buffer = self._recv_buffer[delimiter.size:]

                # Safely unpack it. This should *probably* never error.
                try:
                    data = delimiter.unpack(data)
                except struct.error:
                    log.exception("Unable to unpack data on %r." % self)
                    self.close()
                    break

                # Unlike most on_read calls, this one sends every variable of
                # the parsed data as its own argument.
                self._safely_call(self.on_read, *data)

            elif isinstance(delimiter, _NetStruct):
                if not self._netstruct_iter:
                    # We need to get started.
                    self._netstruct_iter = delimiter.iter_unpack()
                    self._netstruct_needed = next(self._netstruct_iter)

                if len(self._recv_buffer) < self._netstruct_needed:
                    break

                data = self._netstruct_iter.send(
                    self._recv_buffer[:self._netstruct_needed])
                self._recv_buffer = self._recv_buffer[self._netstruct_needed:]

                if isinstance(data, (int,long)):
                    self._netstruct_needed = data
                    continue

                # Still here? Then we've got our object. Delete the NetStruct
                # state and send the data.
                self._netstruct_needed = None
                self._netstruct_iter = None

                self._safely_call(self.on_read, *data)

            elif isinstance(delimiter, RegexType):
                # Depending on regex_search, we could do this two ways.
                if self.regex_search:
                    match = delimiter.search(self._recv_buffer)
                    if not match:
                        break

                    data = self._recv_buffer[:match.start()]
                    self._recv_buffer = self._recv_buffer[match.end():]

                else:
                    # Require the match to be at the beginning.
                    data = delimiter.match(self._recv_buffer)
                    if not data:
                        break

                    self._recv_buffer = self._recv_buffer[data.end():]

                # Send either the string or the match object.
                self._safely_call(self.on_read, data)

            else:
                # The safeguards in the read delimiter property should
                # prevent this from happening unless people start
                # getting too crafty for their own good.
                err = InvalidReadDelimiterError("Invalid read delimiter on %r." % self)
                self._safely_call(self.on_error, err)
                break

            if self._closed or not self.connected:
                break

    def _process_send_buffer(self):
        """
        Process the :attr:`~pants.stream.Stream._send_buffer`, passing
        outgoing data to :meth:`~pants._channel._Channel._socket_send`
        or :meth:`~pants._channel._Channel._socket_sendfile` and calling
        :meth:`~pants.stream.Stream.on_write` when sending has finished.
        """
        while self._send_buffer:
            data_type, data = self._send_buffer.pop(0)

            if data_type == Stream.SEND_STRING:
                bytes_sent = self._process_send_string(data)
            elif data_type == Stream.SEND_FILE:
                bytes_sent = self._process_send_file(*data)
            elif data_type == Stream.SEND_SSL_HANDSHAKE:
                bytes_sent = self._process_send_ssl_handshake(data)

            if bytes_sent == 0:
                break

        if not self._closed and not self._send_buffer:
            self._safely_call(self.on_write)

            if self._closing:
                self.close(flush=False)

    def _process_send_string(self, data):
        """
        Send data from a string to the remote socket.
        """
        try:
            bytes_sent = self._socket_send(data)
        except socket.error as err:
            self._safely_call(self.on_write_error, err)
            return 0

        if len(data) > bytes_sent:
            self._send_buffer.insert(0, (Stream.SEND_STRING, data[bytes_sent:]))

        return bytes_sent

    def _process_send_file(self, sfile, offset, nbytes):
        """
        Send data from a file to the remote socket.
        """
        try:
            bytes_sent = self._socket_sendfile(sfile, offset, nbytes)
        except socket.error as err:
            self._safely_call(self.on_write_error, err)
            return 0

        offset += bytes_sent

        if nbytes > 0:
            if nbytes - bytes_sent > 0:
                nbytes -= bytes_sent
            else:
                # Reached the end of the segment.
                return bytes_sent

        # TODO This is awful. Find a better way.
        if os.fstat(sfile.fileno()).st_size - offset <= 0:
            # Reached the end of the file.
            return bytes_sent

        self._send_buffer.insert(0, (Stream.SEND_FILE, (sfile, offset, nbytes)))

        return bytes_sent

    def _process_send_ssl_handshake(self, ssl_options):
        """
        Enable SSL and begin the handshake.
        """
        self._ssl_enabling = False

        if not self._ssl_socket_wrapped:
            try:
                self._socket = ssl.wrap_socket(self._socket, **ssl_options)
            except ssl.SSLError as err:
                self._ssl_enabling = True
                self._safely_call(self.on_ssl_error, err)
                return 0
            else:
                self._ssl_socket_wrapped = True

        self.ssl_enabled = True

        try:
            bytes_sent = self._ssl_do_handshake()
        except Exception as err:
            self._safely_call(self.on_ssl_handshake_error, err)
            return 0

        # Unlike strings and files, the SSL handshake is not re-added to
        # the queue. This is because the stream's state has been
        # modified and the handshake will continue until it's complete.
        return bytes_sent

    ##### SSL Implementation ##################################################

    def _socket_recv(self):
        """
        Receive data from the socket.

        Returns a string of data read from the socket. The data is None if
        the socket has been closed.

        Overrides :meth:`pants._channel._Channel._socket_recv` to handle
        SSL-specific behaviour.
        """
        try:
            return _Channel._socket_recv(self)
        except ssl.SSLError as err:
            if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                return ''
            else:
                raise

    def _socket_send(self, data):
        """
        Send data to the socket.

        Returns the number of bytes that were sent to the socket.

        Overrides :meth:`pants._channel._Channel._socket_send` to handle
        SSL-specific behaviour.

        =========  ============
        Argument   Description
        =========  ============
        data       The string of data to send.
        =========  ============
        """
        try:
            bytes_sent = _Channel._socket_send(self, data)
        except ssl.SSLError as err:
            if err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self._start_waiting_for_write_event()
                return 0
            else:
                raise

        # SSLSocket.send() can return 0 rather than raise an exception
        # if it needs a write event.
        if self.ssl_enabled and bytes_sent == 0:
            self._start_waiting_for_write_event()
        return bytes_sent

    def _socket_sendfile(self, sfile, offset, nbytes):
        """
        Send data from a file to a remote socket.

        Returns the number of bytes that were sent to the socket.

        Overrides :meth:`pants._channel._Channel._socket_sendfile` to
        handle SSL-specific behaviour.

        =========  ============
        Argument   Description
        =========  ============
        sfile      The file to send.
        offset     The number of bytes to offset writing by.
        nbytes     The number of bytes of the file to write. If 0, all bytes will be written.
        =========  ============
        """
        return _Channel._socket_sendfile(self, sfile, offset, nbytes, self.ssl_enabled)

    def _ssl_do_handshake(self):
        """
        Perform an asynchronous SSL handshake.
        """
        try:
            self._socket.do_handshake()
        except ssl.SSLError as err:
            if err.args[0] == ssl.SSL_ERROR_WANT_READ:
                return 0
            elif err.args[0] == ssl.SSL_ERROR_WANT_WRITE:
                self._start_waiting_for_write_event()
                return 0
            elif err.args[0] in (ssl.SSL_ERROR_EOF, ssl.SSL_ERROR_ZERO_RETURN):
                self.close(flush=False)
                return 0
            elif err.args[0] == ssl.SSL_ERROR_SSL:
                self._safely_call(self.on_ssl_handshake_error, err)
                return 0
            else:
                raise
        except socket.error as err:
            if err.args[0] in (errno.ECONNRESET, errno.EPIPE):
                self.close(flush=False)
                return 0
            else:
                raise
        else:
            self._ssl_handshake_done = True
            self._safely_call(self.on_ssl_handshake)
            if self._ssl_call_on_connect:
                self._safely_call(self.on_connect)
            return None


###############################################################################
# Exceptions
###############################################################################

class StreamBufferOverflow(Exception):
    """
    Raised when a stream's internal buffer has exceeded its maximum
    allowed size.
    """
    pass

class StreamConnectError(Exception):
    """
    Raised when an error has occurred during an attempt to connect a
    stream to a remote host.
    """
    pass

class InvalidReadDelimiterError(Exception):
    """
    Raised when a channel tries to process incoming data with an
    invalid read delimiter.
    """
    pass

########NEW FILE########
__FILENAME__ = test_channel
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import errno
import socket
import sys
import unittest

from mock import MagicMock

from pants.engine import Engine
from pants._channel import _Channel, HAS_UNIX, HAS_IPV6, InvalidAddressFormatError
import pants._channel

class TestChannelConstructorArguments(unittest.TestCase):
    def test_channel_constructor_no_args(self):
        channel = _Channel()
        self.assertTrue(channel.engine is Engine.instance())
        self.assertTrue(channel._socket is None)

    def test_channel_constructor_socket_arg(self):
        sock = socket.socket()
        channel = _Channel(socket=sock)
        self.assertTrue(channel._socket is sock)

    def test_channel_constructor_engine_arg(self):
        engine = Engine()
        channel = _Channel(engine=engine)
        self.assertTrue(channel.engine is engine)

class TestChannelEngineInteraction(unittest.TestCase):
    def test_channel_gets_added_to_engine(self):
        engine = Engine()
        engine.add_channel = MagicMock()
        channel = _Channel(socket=socket.socket(), engine=engine)
        engine.add_channel.assert_called_once_with(channel)
        channel.close()

    def test_channel_gets_removed_from_engine(self):
        engine = Engine()
        engine.remove_channel = MagicMock()
        channel = _Channel(socket=socket.socket(), engine=engine)
        channel.close()
        engine.remove_channel.assert_called_once_with(channel)

class TestChannelFileno(unittest.TestCase):
    def test_channel_fileno_with_no_socket(self):
        channel = _Channel()
        self.assertTrue(channel.fileno is None)

    def test_channel_fileno_with_socket(self):
        sock = socket.socket()
        channel = _Channel(socket=sock)
        self.assertTrue(channel.fileno == sock.fileno())

class TestChannelClose(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()

    def test_channel_close_does_not_raise_an_exception_with_no_socket(self):
        try:
            self.channel.close()
        except TypeError:
            self.fail("Attempted to remove a socketless channel from the engine.")

    def test_channel_close_does_not_call_on_close(self):
        self.channel.on_close = MagicMock()
        self.channel.close()
        self.assertRaises(AssertionError, self.channel.on_close.assert_any_call)

class TestChannelSocketSet(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()

    def test_socket_set_with_acceptable_socket(self):
        sock = MagicMock()
        sock.family = socket.AF_INET
        sock.type = socket.SOCK_STREAM
        sock.setblocking = MagicMock()
        self.channel._socket_set(sock)
        self.assertTrue(self.channel._socket is sock)
        sock.setblocking.assert_called_once_with(False)

    def test_socket_set_with_preexisting_socket(self):
        self.channel._socket = MagicMock()
        self.assertRaises(RuntimeError, self.channel._socket_set, None)

    def test_socket_set_with_unsupported_family(self):
        sock = MagicMock()
        sock.family = 9001
        self.assertRaises(ValueError, self.channel._socket_set, sock)

    def test_socket_set_with_unsupported_type(self):
        sock = MagicMock()
        sock.family = socket.AF_INET
        sock.type = 9001
        self.assertRaises(ValueError, self.channel._socket_set, sock)

class TestChannelSocketConnect(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.channel._socket = self.sock

    def test_connect_ex_returns_success(self):
        self.sock.connect_ex = MagicMock(return_value=0)
        self.assertTrue(self.channel._socket_connect(None))

    def test_connect_ex_returns_EISCONN(self):
        self.sock.connect_ex = MagicMock(return_value=errno.EISCONN)
        self.assertTrue(self.channel._socket_connect(None))

    def test_connect_ex_returns_EAGAIN(self):
        self.sock.connect_ex = MagicMock(return_value=errno.EAGAIN)
        self.assertFalse(self.channel._socket_connect(None))

    def test_connect_ex_returns_EWOULDBLOCK(self):
        self.sock.connect_ex = MagicMock(return_value=errno.EWOULDBLOCK)
        self.assertFalse(self.channel._socket_connect(None))

    def test_connect_ex_returns_EINPROGRESS(self):
        self.sock.connect_ex = MagicMock(return_value=errno.EINPROGRESS)
        self.assertFalse(self.channel._socket_connect(None))

    def test_connect_ex_returns_EALREADY(self):
        self.sock.connect_ex = MagicMock(return_value=errno.EALREADY)
        self.assertFalse(self.channel._socket_connect(None))

    def test_connect_ex_returns_unknown(self):
        self.sock.connect_ex = MagicMock(return_value=-1)
        self.assertRaises(socket.error, self.channel._socket_connect, None)

    def test_connect_ex_raises_unknown(self):
        self.sock.connect_ex = MagicMock(side_effect=Exception)
        self.assertRaises(Exception, self.channel._socket_connect, None)

    def test_reraises_unknown_socket_error(self):
        self.sock.connect_ex = MagicMock(side_effect=socket.error(-1))
        self.assertRaises(socket.error, self.channel._socket_connect, None)

class TestChannelSocketBind(unittest.TestCase):
    def test_bind_is_called(self):
        channel = _Channel()
        channel._socket = MagicMock()
        channel._socket.bind = MagicMock()
        channel._socket_bind(None)
        channel._socket.bind.assert_called_once_with(None)

class TestChannelSocketListen(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.sock.listen = MagicMock()
        self.channel._socket = self.sock

    def test_listen_is_called(self):
        self.channel._socket_listen(1)
        self.sock.listen.assert_called_once_with(1)

    @unittest.skipUnless(sys.platform.startswith("win"), "Windows-specific functionality.")
    def test_listen_backlog_is_corrected_on_windows(self):
        self.channel._socket_listen(socket.SOMAXCONN+1)
        self.sock.listen.assert_called_once_with(socket.SOMAXCONN)
    
    @unittest.skipIf(sys.platform.startswith("win"), "Non-Windows-specific functionality.")
    def test_listen_backlog_is_not_corrected_on_other_platforms(self):
        self.channel._socket_listen(socket.SOMAXCONN+1)
        self.sock.listen.assert_called_once_with(socket.SOMAXCONN+1)

class TestChannelSocketClose(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.channel._socket = self.sock

    def test_socket_close(self):
        self.channel._socket_close()
        self.assertTrue(self.channel._socket is None)
        self.assertTrue(self.channel._closed)

    def test_shutdown_is_called(self):
        shutdown = MagicMock()
        self.sock.shutdown = shutdown
        self.channel._socket_close()
        shutdown.assert_called_once_with(socket.SHUT_RDWR)

    def test_close_is_called(self):
        close = MagicMock()
        self.sock.close = close
        self.channel._socket_close()
        close.assert_called_once_with()

    def test_socket_error_is_raised(self):
        socket_error_raiser = MagicMock(side_effect=socket.error)
        self.sock.shutdown = socket_error_raiser
        try:
            self.channel._socket_close()
        except socket.error:
            self.fail("socket.error was not caught.")

class TestChannelSocketAccept(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.channel._socket = self.sock

    def test_socket_accept(self):
        self.sock.accept = MagicMock(return_value=(1, 2, 3))
        self.assertEqual(self.channel._socket_accept(), (1, 2, 3))

    def test_accept_raises_EAGAIN(self):
        self.sock.accept = MagicMock(side_effect=socket.error(errno.EAGAIN))
        self.assertEqual(self.channel._socket_accept(), (None, None))

    def test_accept_raises_EWOULDBLOCK(self):
        self.sock.accept = MagicMock(side_effect=socket.error(errno.EWOULDBLOCK))
        self.assertEqual(self.channel._socket_accept(), (None, None))

    def test_accept_raises_unknown(self):
        self.sock.accept = MagicMock(side_effect=socket.error(-1))
        self.assertRaises(socket.error, self.channel._socket_accept)

class TestChannelSocketRecv(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.channel._socket = self.sock

    def test_socket_recv(self):
        chunk = "foo"
        self.sock.recv = MagicMock(return_value=chunk)
        result = self.channel._socket_recv()
        self.assertEqual(result, chunk)
        self.sock.recv.assert_called_once_with(self.channel._recv_amount)

    def test_recv_returns_no_data(self):
        chunk = ""
        self.sock.recv = MagicMock(return_value=chunk)
        result = self.channel._socket_recv()
        self.assertEqual(result, None)

    def test_recv_raises_EAGAIN(self):
        self.sock.recv = MagicMock(side_effect=socket.error(errno.EAGAIN))
        result = self.channel._socket_recv()
        self.assertEqual(result, "")

    def test_recv_raises_EWOULDBLOCK(self):
        self.sock.recv = MagicMock(side_effect=socket.error(errno.EWOULDBLOCK))
        result = self.channel._socket_recv()
        self.assertEqual(result, "")

    def test_recv_raises_ECONNRESET(self):
        self.sock.recv = MagicMock(side_effect=socket.error(errno.ECONNRESET))
        result = self.channel._socket_recv()
        self.assertEqual(result, None)

    def test_recv_raises_unknown(self):
        self.sock.recv = MagicMock(side_effect=socket.error(-1))
        self.assertRaises(socket.error, self.channel._socket_recv)

class TestChannelSocketRecvFrom(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.channel._socket = self.sock

    def test_socket_recvfrom(self):
        chunk = ("foo", None)
        self.sock.recvfrom = MagicMock(return_value=chunk)
        result = self.channel._socket_recvfrom()
        self.assertEqual(result, chunk)
        self.sock.recvfrom.assert_called_once_with(self.channel._recv_amount)

    def test_recvfrom_returns_no_data(self):
        chunk = ("", None)
        self.sock.recvfrom = MagicMock(return_value=chunk)
        result = self.channel._socket_recvfrom()
        self.assertEqual(result, (None, None))

    def test_recvfrom_raises_EAGAIN(self):
        self.sock.recvfrom = MagicMock(side_effect=socket.error(errno.EAGAIN))
        result = self.channel._socket_recvfrom()
        self.assertEqual(result, ("", None))

    def test_recvfrom_raises_EWOULDBLOCK(self):
        self.sock.recvfrom = MagicMock(side_effect=socket.error(errno.EWOULDBLOCK))
        result = self.channel._socket_recvfrom()
        self.assertEqual(result, ("", None))

    def test_recvfrom_raises_ECONNRESET(self):
        self.sock.recvfrom = MagicMock(side_effect=socket.error(errno.ECONNRESET))
        result = self.channel._socket_recvfrom()
        self.assertEqual(result, ("", None))

    def test_recvfrom_raises_unknown(self):
        self.sock.recvfrom = MagicMock(side_effect=socket.error(-1))
        self.assertRaises(socket.error, self.channel._socket_recvfrom)

class TestChannelSocketSend(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.channel._socket = self.sock

    def test_socket_send(self):
        chunk = "foo"
        self.sock.send = MagicMock(return_value=len(chunk))
        self.assertEqual(self.channel._socket_send(chunk), len(chunk))
        self.sock.send.assert_called_once_with(chunk)

    def test_send_raises_EAGAIN(self):
        self.sock.send = MagicMock(side_effect=socket.error(errno.EAGAIN))
        self.channel._start_waiting_for_write_event = MagicMock()
        result = self.channel._socket_send(None)
        self.assertEqual(result, 0)
        self.channel._start_waiting_for_write_event.assert_called_once_with()

    def test_send_raises_EWOULDBLOCK(self):
        self.sock.send = MagicMock(side_effect=socket.error(errno.EWOULDBLOCK))
        self.channel._start_waiting_for_write_event = MagicMock()
        result = self.channel._socket_send(None)
        self.assertEqual(result, 0)
        self.channel._start_waiting_for_write_event.assert_called_once_with()

    def test_send_raises_EPIPE(self):
        self.sock.send = MagicMock(side_effect=Exception(errno.EPIPE))
        self.channel.close = MagicMock()
        result = self.channel._socket_send(None)
        self.assertEqual(result, 0)
        self.channel.close.assert_called_once_with(flush=False)

    def test_send_raises_unknown(self):
        self.sock.send = MagicMock(side_effect=Exception(-1))
        self.assertRaises(Exception, self.channel._socket_send)

class TestChannelSocketSendTo(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.channel._socket = self.sock

    def test_socket_sendto(self):
        chunk = "foo"
        args = (chunk, None, None)
        self.sock.sendto = MagicMock(return_value=len(chunk))
        self.assertEqual(self.channel._socket_sendto(*args), len(chunk))
        self.sock.sendto.assert_called_once_with(*args)

    def test_sendto_raises_EAGAIN(self):
        self.sock.send = MagicMock(side_effect=socket.error(errno.EAGAIN))
        self.channel._start_waiting_for_write_event = MagicMock()
        result = self.channel._socket_send(None)
        self.assertEqual(result, 0)
        self.channel._start_waiting_for_write_event.assert_called_once_with()

    def test_sendto_raises_EWOULDBLOCK(self):
        self.sock.send = MagicMock(side_effect=socket.error(errno.EWOULDBLOCK))
        self.channel._start_waiting_for_write_event = MagicMock()
        result = self.channel._socket_send(None)
        self.assertEqual(result, 0)
        self.channel._start_waiting_for_write_event.assert_called_once_with()

    def test_sendto_raises_EPIPE(self):
        self.sock.send = MagicMock(side_effect=Exception(errno.EPIPE))
        self.channel.close = MagicMock()
        result = self.channel._socket_send(None)
        self.assertEqual(result, 0)
        self.channel.close.assert_called_once_with(flush=False)

    def test_sendto_raises_unknown(self):
        self.sock.send = MagicMock(side_effect=Exception(-1))
        self.assertRaises(Exception, self.channel._socket_send)

class TestChannelSocketSendfile(unittest.TestCase):
    def setUp(self):
        self._sendfile = pants._channel.sendfile
        self.channel = _Channel()

    def tearDown(self):
        pants._channel.sendfile = self._sendfile

    def test_socket_sendfile(self):
        chunk = "foo"
        args = (chunk, None, None, False)
        pants._channel.sendfile = MagicMock(return_value=len(chunk))
        self.assertEqual(self.channel._socket_sendfile(*args), len(chunk))
        pants._channel.sendfile.assert_called_once_with(chunk, self.channel, None, None, False)

    def test_sendfile_raises_EAGAIN(self):
        chunk = "foo"
        args = (chunk, None, None, False)
        err = socket.error(errno.EAGAIN)
        err.nbytes = 0 # See issue #43
        pants._channel.sendfile = MagicMock(side_effect=err)
        self.channel._start_waiting_for_write_event = MagicMock()
        result = self.channel._socket_sendfile(*args)
        self.assertEqual(result, 0)
        self.channel._start_waiting_for_write_event.assert_called_once_with()

    def test_sendfile_raises_EWOULDBLOCK(self):
        chunk = "foo"
        args = (chunk, None, None, False)
        err = socket.error(errno.EWOULDBLOCK)
        err.nbytes = 0 # See issue #43
        pants._channel.sendfile = MagicMock(side_effect=err)
        self.channel._start_waiting_for_write_event = MagicMock()
        result = self.channel._socket_sendfile(*args)
        self.assertEqual(result, 0)
        self.channel._start_waiting_for_write_event.assert_called_once_with()

    def test_sendfile_raises_EPIPE(self):
        chunk = "foo"
        args = (chunk, None, None, False)
        pants._channel.sendfile = MagicMock(side_effect=Exception(errno.EPIPE))
        self.channel.close = MagicMock()
        result = self.channel._socket_sendfile(*args)
        self.assertEqual(result, 0)
        self.channel.close.assert_called_once_with(flush=False)

    def test_sendfile_raises_unknown(self):
        pants._channel.sendfile = MagicMock(side_effect=Exception((-1,)))
        self.assertRaises(Exception, self.channel._socket_sendfile)

class TestChannelStartWaitingForWriteEvent(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()

    def test_when_write_needs_to_be_added(self):
        self.channel._events = Engine.NONE
        self.channel.engine.modify_channel = MagicMock()
        self.channel._start_waiting_for_write_event()
        self.assertEqual(self.channel._events, Engine.WRITE)
        self.channel.engine.modify_channel.assert_called_once_with(self.channel)

    def test_when_write_doesnt_need_to_be_added(self):
        self.channel._events = Engine.WRITE
        self.channel.engine.modify_channel = MagicMock()
        self.channel._start_waiting_for_write_event()
        self.assertEqual(self.channel._events, Engine.WRITE)
        self.assertRaises(AssertionError, self.channel.engine.modify_channel.assert_called_once_with)

class TestChannelStopWaitingForWriteEvent(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()

    def test_when_write_needs_to_be_removed(self):
        self.channel._events = Engine.WRITE
        self.channel.engine.modify_channel = MagicMock()
        self.channel._stop_waiting_for_write_event()
        self.assertEqual(self.channel._events, Engine.NONE)
        self.channel.engine.modify_channel.assert_called_once_with(self.channel)

    def test_when_write_doesnt_need_to_be_removed(self):
        self.channel._events = Engine.NONE
        self.channel.engine.modify_channel = MagicMock()
        self.channel._stop_waiting_for_write_event()
        self.assertEqual(self.channel._events, Engine.NONE)
        self.assertRaises(AssertionError, self.channel.engine.modify_channel.assert_called_once_with)

class TestChannelSafelyCall(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()

    def test_with_no_error(self):
        args = (1, 2, 3)
        kwargs = {"foo": "bar"}
        thing_to_call = MagicMock()
        self.channel._safely_call(thing_to_call, *args, **kwargs)
        thing_to_call.assert_called_once_with(*args, **kwargs)

    def test_with_an_error(self):
        args = (1, 2, 3)
        kwargs = {"foo": "bar"}
        thing_to_call = MagicMock(side_effect=Exception())
        self.channel._safely_call(thing_to_call, *args, **kwargs)
        thing_to_call.assert_called_once_with(*args, **kwargs)

class TestChannelGetSocketError(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.sock = MagicMock()
        self.channel._socket = self.sock

    def test_with_no_error(self):
        self.sock.getsockopt = MagicMock(return_value=0)
        err, errstr = self.channel._get_socket_error()
        self.sock.getsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_ERROR)
        self.assertEqual(err, 0)
        self.assertEqual(errstr, "")

    def test_with_an_error(self):
        self.sock.getsockopt = MagicMock(return_value=errno.EAGAIN)
        err, errstr = self.channel._get_socket_error()
        self.sock.getsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_ERROR)
        self.assertEqual(err, errno.EAGAIN)
        self.assertNotEqual(errstr, "")

class TestChannelFormatAddress(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()

    @unittest.skipUnless(HAS_UNIX, "Requires support for UNIX sockets.")
    def test_with_unix_address(self):
        path = "/home/example/socket"
        address, family, resolved = self.channel._format_address(path)
        self.assertEqual(address, path)
        self.assertEqual(family, socket.AF_UNIX)
        self.assertEqual(resolved, True)

    @unittest.skipIf(HAS_UNIX, "Requires no support for UNIX sockets.")
    def test_when_unix_address_is_invalid(self):
        path = "/home/example/socket"
        self.assertRaises(InvalidAddressFormatError, self.channel._format_address, path)

    def test_with_port_number(self):
        port = 8080
        address, family, resolved = self.channel._format_address(port)
        self.assertEqual(address, ("", port))
        self.assertEqual(family, socket.AF_INET)
        self.assertEqual(resolved, True)

    def test_inaddr_any(self):
        addr = ('', 80)
        address, family, resolved = self.channel._format_address(addr)
        self.assertEqual(address, addr)
        self.assertEqual(family, socket.AF_INET)
        self.assertEqual(resolved, True)

    def test_inaddr6_any(self):
        addr = ('', 80, 1, 2)
        address, family, resolved = self.channel._format_address(addr)
        self.assertEqual(address, addr)
        self.assertEqual(family, socket.AF_INET6)
        self.assertEqual(resolved, True)

    def test_broadcast(self):
        addr = ('<broadcast>', 80)
        address, family, resolved = self.channel._format_address(addr)
        self.assertEqual(address, addr)
        self.assertEqual(family, socket.AF_INET)
        self.assertEqual(resolved, True)

    def test_broadcast6(self):
        addr = ('<broadcast>', 80, 1, 2)
        address, family, resolved = self.channel._format_address(addr)
        self.assertEqual(address, addr)
        self.assertEqual(family, socket.AF_INET6)
        self.assertEqual(resolved, True)

    def test_with_invalid_ipv4_address(self):
        addr = (1, 2)
        self.assertRaises(InvalidAddressFormatError, self.channel._format_address, addr)

    def test_with_ipv4_address(self):
        addr = ('8.8.8.8', 2)
        address, family, resolved = self.channel._format_address(addr)
        self.assertEqual(address, ('8.8.8.8', 2))
        self.assertEqual(family, socket.AF_INET)
        self.assertEqual(resolved, True)

    @unittest.skipUnless(HAS_IPV6, "Requires support for IPv6 sockets.")
    def test_with_invalid_ipv6_address(self):
        addr = (1, 2, 3, 4)

    @unittest.skipUnless(HAS_IPV6, "Requires support for IPv6 sockets.")
    def test_with_ipv6_address(self):
        addr = ('::1', 2, 3, 4)
        address, family, resolved = self.channel._format_address(addr)
        self.assertEqual(address, addr)
        self.assertEqual(family, socket.AF_INET6)
        self.assertEqual(resolved, True)

    @unittest.skipIf(HAS_IPV6, "Requires no support for IPv6 sockets.")
    def test_when_ipv6_address_is_invalid(self):
        addr = (1, 2, 3, 4)
        self.assertRaises(InvalidAddressFormatError, self.channel._format_address, addr)

    def test_with_invalid_addresses(self):
        self.assertRaises(InvalidAddressFormatError, self.channel._format_address, None)
        self.assertRaises(InvalidAddressFormatError, self.channel._format_address, (1, 2, 3))

@unittest.skip("Not yet implemented.")
class TestChannelResolveAddress(unittest.TestCase):
    @unittest.skipUnless(HAS_UNIX, "Requires support for UNIX sockets.")
    def test_resolve_unix_address(self):
        self.fail("Not yet implemented.")

    def test_resolve_ipv4_address(self):
        self.fail("Not yet implemented.")

    @unittest.skipUnless(HAS_IPV6, "Requires support for IPv6 sockets.")
    def test_resolve_inet6_address(self):
        self.fail("Not yet implemented.")

class TestChannelHandleEvents(unittest.TestCase):
    def setUp(self):
        self.channel = _Channel()
        self.channel._handle_read_event = MagicMock()
        self.channel._handle_write_event = MagicMock()
        self.channel._handle_error_event = MagicMock()
        self.channel._handle_hangup_event = MagicMock()

    def test_new_events_modify_engine(self):
        self.channel.engine.modify_channel = MagicMock()

        def add_events():
            self._events = Engine.ALL_EVENTS
        
        self.channel._handle_read_event = add_events
        self.channel._events = Engine.NONE
        self.channel._handle_events(Engine.READ)
        self.channel.engine.modify_channel.assert_called_once_with(self.channel)

    def test_when_channel_is_closed(self):
        self.channel._closed = True
        self.channel._handle_events(Engine.READ)
        self.assertRaises(AssertionError, self.channel._handle_read_event.assert_called_once_with)

    def test_with_no_events(self):
        self.channel._handle_events(Engine.NONE)
        self.assertRaises(AssertionError, self.channel._handle_read_event.assert_called_once_with)
        self.assertRaises(AssertionError, self.channel._handle_write_event.assert_called_once_with)
        self.assertRaises(AssertionError, self.channel._handle_error_event.assert_called_once_with)
        self.assertRaises(AssertionError, self.channel._handle_hangup_event.assert_called_once_with)

    def test_with_all_events(self):
        self.channel._handle_events(Engine.ALL_EVENTS)
        self.channel._handle_read_event.assert_called_once_with()
        self.channel._handle_write_event.assert_called_once_with()
        self.channel._handle_error_event.assert_called_once_with()
        self.channel._handle_hangup_event.assert_called_once_with()

    def test_with_abrupt_close(self):
        self.channel._handle_error_event = MagicMock(side_effect=self.channel.close)
        self.channel._handle_events(Engine.ALL_EVENTS)
        self.channel._handle_read_event.assert_called_once_with()
        self.channel._handle_write_event.assert_called_once_with()
        self.channel._handle_error_event.assert_called_once_with()
        self.assertRaises(AssertionError, self.channel._handle_hangup_event.assert_called_once_with)

########NEW FILE########
__FILENAME__ = test_echo
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import socket
import unittest

import pants

from pants.test._pants_util import *

class Echo(pants.Stream):
    def on_read(self, data):
        self.write(data)

class TestEcho(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(ConnectionClass=Echo).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def test_echo_with_one_client(self):
        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', 4040))
        request = repr(sock)
        sock.send(request)
        response = sock.recv(1024)
        self.assertEqual(response, request)
        sock.close()

    def test_echo_with_two_sequential_clients(self):
        sock1 = socket.socket()
        sock1.settimeout(1.0)
        sock1.connect(('127.0.0.1', 4040))
        request1 = repr(sock1)
        sock1.send(request1)
        response1 = sock1.recv(1024)
        self.assertEqual(response1, request1)
        sock1.close()

        sock2 = socket.socket()
        sock2.settimeout(1.0)
        sock2.connect(('127.0.0.1', 4040))
        request2 = repr(sock2)
        sock2.send(request2)
        response2 = sock2.recv(1024)
        self.assertEqual(response2, request2)
        sock2.close()

    def test_echo_with_two_concurrent_clients(self):
        sock1 = socket.socket()
        sock1.settimeout(1.0)
        sock2 = socket.socket()
        sock2.settimeout(1.0)
        sock1.connect(('127.0.0.1', 4040))
        sock2.connect(('127.0.0.1', 4040))
        request1 = repr(sock1)
        request2 = repr(sock2)
        sock1.send(request1)
        sock2.send(request2)
        response1 = sock1.recv(1024)
        response2 = sock2.recv(1024)
        self.assertEqual(response1, request1)
        self.assertEqual(response2, request2)
        sock1.close()
        sock2.close()

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

########NEW FILE########
__FILENAME__ = test_echo_to_all
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import socket
import unittest

import pants

from pants.test._pants_util import *

class EchoToAll(pants.Stream):
    def on_read(self, data):
        for channel in self.server.channels.itervalues():
            channel.write(data)

class TestEchoToAll(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(ConnectionClass=EchoToAll).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def test_echo_to_all_with_one_client(self):
        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', 4040))
        request = repr(sock)
        sock.send(request)
        response = sock.recv(1024)
        self.assertEqual(response, request)
        sock.close()

    def test_echo_to_all_with_two_sequential_clients(self):
        sock1 = socket.socket()
        sock1.settimeout(1.0)
        sock1.connect(('127.0.0.1', 4040))
        request1 = repr(sock1)
        sock1.send(request1)
        response1 = sock1.recv(1024)
        self.assertEqual(response1, request1)
        sock1.close()

        sock2 = socket.socket()
        sock2.settimeout(1.0)
        sock2.connect(('127.0.0.1', 4040))
        request2 = repr(sock2)
        sock2.send(request2)
        response2 = sock2.recv(1024)
        self.assertEqual(response2, request2)
        sock2.close()

    def test_echo_to_all_with_two_concurrent_clients(self):
        sock1 = socket.socket()
        sock1.settimeout(1.0)
        sock2 = socket.socket()
        sock2.settimeout(1.0)
        sock1.connect(('127.0.0.1', 4040))
        sock2.connect(('127.0.0.1', 4040))
        request1 = repr(sock1)
        sock1.send(request1)
        response1_1 = sock1.recv(1024)
        response1_2 = sock2.recv(1024)
        request2 = repr(sock2)
        sock2.send(request2)
        response2_1 = sock1.recv(1024)
        response2_2 = sock2.recv(1024)
        self.assertEqual(response1_1, request1)
        self.assertEqual(response1_2, request1)
        self.assertEqual(response2_1, request2)
        self.assertEqual(response2_2, request2)
        sock1.close()
        sock2.close()

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

########NEW FILE########
__FILENAME__ = test_engine
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import errno
import select
import time
import unittest

from mock import call, MagicMock

from pants.engine import Engine, _EPoll, _KQueue, _Select, _Timer

class TestEngine(unittest.TestCase):
    def test_engine_global_instance(self):
        engine1 = Engine.instance()
        engine2 = Engine.instance()

        self.assertTrue(engine1 is engine2)

    def test_engine_local_instances(self):
        engine1 = Engine()
        engine2 = Engine()

        self.assertFalse(engine1 is engine2)

class TestEngineStart(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()

    def test_when_shutdown_is_true(self):
        self.engine._shutdown = True
        self.engine.start()
        self.assertFalse(self.engine._shutdown)

    def test_when_shutdown_is_false_and_running_is_true(self):
        self.engine._shutdown = False
        self.engine._running = True
        self.engine.start()
        self.assertFalse(self.engine._shutdown)
        self.assertTrue(self.engine._running)

    def test_when_engine_is_stopped_normally(self):
        def poll(engine):
            self.engine.stop()

        self.engine.poll = poll
        self.engine.start()
        self.assertFalse(self.engine._shutdown)
        self.assertFalse(self.engine._running)

    def test_when_poll_raises_systemexit(self):
        def poll(engine):
            raise SystemExit

        self.engine.poll = poll
        self.assertRaises(SystemExit, self.engine.start)
        self.assertFalse(self.engine._shutdown)
        self.assertFalse(self.engine._running)

    def test_when_poll_raises_exception(self):
        def poll(engine):
            raise Exception

        self.engine.poll = poll
        self.engine.start()
        self.assertFalse(self.engine._shutdown)
        self.assertFalse(self.engine._running)

class TestEngineStop(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()

    def test_when_running(self):
        self.engine._shutdown = False
        self.engine._running = True
        self.engine.stop()
        self.assertTrue(self.engine._shutdown)

    def test_when_not_running(self):
        self.engine._shutdown = False
        self.engine._running = False
        self.engine.stop()
        self.assertFalse(self.engine._shutdown)

class TestEnginePoll(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()

    def test_poll_updates_time(self):
        current_time = self.engine.latest_poll_time
        time.sleep(0.02)
        self.engine.poll(0.02)
        self.assertTrue(self.engine.latest_poll_time > current_time)

    def test_poll_executes_callbacks(self):
        callback = MagicMock()
        callback.function = MagicMock()
        callback.requeue = False
        self.engine._callbacks.append(callback)
        self.engine.poll(0.02)
        callback.function.assert_called_once_with()
        self.assertTrue(len(self.engine._callbacks) == 0)

    def test_callback_exception_doesnt_break_poll(self):
        callback = MagicMock()
        callback.function = MagicMock(side_effect=Exception)
        callback.requeue = False
        self.engine._callbacks.append(callback)
        try:
            self.engine.poll(0.02)
        except Exception:
            self.fail("Exception in callback function was not caught.")

    def test_keyboardinterrupt_during_callback_processing_is_raised(self):
        callback = MagicMock()
        callback.function = MagicMock(side_effect=KeyboardInterrupt)
        callback.requeue = False
        self.engine._callbacks.append(callback)
        self.assertRaises(KeyboardInterrupt, self.engine.poll, 0.02)

    def test_systemexit_during_callback_processing_is_raised(self):
        callback = MagicMock()
        callback.function = MagicMock(side_effect=SystemExit)
        callback.requeue = False
        self.engine._callbacks.append(callback)
        self.assertRaises(SystemExit, self.engine.poll, 0.02)

    def test_poll_requeues_loops(self):
        loop = MagicMock()
        loop.function = MagicMock()
        loop.requeue = True
        self.engine._callbacks.append(loop)
        self.engine.poll(0.02)
        self.assertTrue(loop in self.engine._callbacks)

    def test_poll_executes_deferreds(self):
        defer = MagicMock()
        defer.function = MagicMock()
        defer.requeue = False
        defer.end = self.engine.latest_poll_time - 1
        self.engine._deferreds.append(defer)
        self.engine.poll(0.02)
        defer.function.assert_called_once_with()

    def test_deferred_exception_doesnt_break_poll(self):
        defer = MagicMock()
        defer.function = MagicMock()
        defer.requeue = False
        defer.end = self.engine.latest_poll_time - 1
        self.engine._deferreds.append(defer)
        try:
            self.engine.poll(0.02)
        except Exception:
            self.fail("Exception in deferred was not caught.")

    def test_keyboardinterrupt_during_deferred_processing_is_raised(self):
        defer = MagicMock()
        defer.function = MagicMock(side_effect=KeyboardInterrupt)
        defer.requeue = False
        defer.end = self.engine.latest_poll_time - 1
        self.engine._deferreds.append(defer)
        self.assertRaises(KeyboardInterrupt, self.engine.poll, 0.02)

    def test_systemexit_during_deferred_processing_is_raised(self):
        defer = MagicMock()
        defer.function = MagicMock(side_effect=SystemExit)
        defer.requeue = False
        defer.end = self.engine.latest_poll_time - 1
        self.engine._deferreds.append(defer)
        self.assertRaises(SystemExit, self.engine.poll, 0.02)

    def test_poll_requeues_deferreds(self):
        cycle = MagicMock()
        cycle.function = MagicMock()
        cycle.requeue = True
        cycle.end = self.engine.latest_poll_time - 1
        cycle.delay = 10
        self.engine._deferreds.append(cycle)
        self.engine.poll(0.02)
        self.assertTrue(cycle in self.engine._deferreds)

    def test_poll_returns_if_timer_shuts_down_engine(self):
        # Pretty ugly way of testing this, to be honest.
        self.engine._poller.poll = MagicMock()
        self.engine._channels = {1: None}
        self.engine.callback(self.engine.stop)
        self.engine.poll(0.02)
        self.assertRaises(AssertionError, self.engine._poller.poll.assert_called_once_with)

    def test_poll_sleeps_for_poll_timeout(self):
        before = time.time()
        self.engine.poll(0.225)
        after = time.time()
        # It's never exactly the timeout length, but it gets very close.
        self.assertTrue((after - before) > 0.22)

    def test_poll_sleeps_until_next_deferred(self):
        defer = MagicMock()
        defer.function = MagicMock()
        defer.requeue = False
        self.engine._deferreds.append(defer)
        before = time.time()
        defer.end = before + 0.225
        self.engine.poll(1)
        after = time.time()
        # Again, never going to be exact.
        self.assertTrue((after - before) < 0.25)

    def test_poller_successful(self):
        self.engine._channels = {1: None}
        self.engine._poller.poll = MagicMock()
        self.engine.poll(0.02)
        self.engine._poller.poll.assert_called_once_with(0.02)

    def test_poller_raises_EINTR(self):
        self.engine._channels = {1: None}
        self.engine._poller.poll = MagicMock(side_effect=Exception(errno.EINTR))
        try:
            self.engine.poll(0.02)
        except Exception as err:
            if err.args[0] == errno.EINTR:
                self.fail("EINTR during polling was not caught.")

    def test_poller_raises_unknown(self):
        self.engine._channels = {1: None}
        self.engine._poller.poll = MagicMock(side_effect=Exception)
        self.assertRaises(Exception, self.engine.poll, 0.02)

    def test_poll_processes_events(self):
        channel = MagicMock()
        channel._handle_events = MagicMock()
        self.engine._channels = {1: channel}
        self.engine._poller.poll = MagicMock(return_value={1:Engine.ALL_EVENTS})
        self.engine.poll(0.02)
        channel._handle_events.assert_called_once_with(Engine.ALL_EVENTS)

    def test_event_processing_error_doesnt_break_poll(self):
        channel = MagicMock()
        channel._handle_events = MagicMock(side_effect=Exception)
        self.engine._channels = {1: channel}
        self.engine._poller.poll = MagicMock(return_value={1:Engine.ALL_EVENTS})
        try:
            self.engine.poll(0.02)
        except Exception:
            self.fail("Exception raised during event processing was not caught.")

    def test_keyboardinterrupt_during_event_processing_is_raised(self):
        channel = MagicMock()
        channel._handle_events = MagicMock(side_effect=KeyboardInterrupt)
        self.engine._channels = {1: channel}
        self.engine._poller.poll = MagicMock(return_value={1:Engine.ALL_EVENTS})
        self.assertRaises(KeyboardInterrupt, self.engine.poll, 0.02)

    def test_systemexit_during_event_processing_is_raised(self):
        channel = MagicMock()
        channel._handle_events = MagicMock(side_effect=SystemExit)
        self.engine._channels = {1: channel}
        self.engine._poller.poll = MagicMock(return_value={1:Engine.ALL_EVENTS})
        self.assertRaises(SystemExit, self.engine.poll, 0.02)

class TestEngineTimers(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()

    def test_callback_added(self):
        timer = self.engine.callback(MagicMock())
        self.assertTrue(timer in self.engine._callbacks)

    def test_loop_added(self):
        timer = self.engine.loop(MagicMock())
        self.assertTrue(timer in self.engine._callbacks)

    def test_deferred_added(self):
        timer = self.engine.defer(10, MagicMock())
        self.assertTrue(timer in self.engine._deferreds)

    def test_deferred_with_zero_delay(self):
        self.assertRaises(ValueError, self.engine.defer, 0, MagicMock())

    def test_deferred_with_negative_delay(self):
        self.assertRaises(ValueError, self.engine.defer, -1, MagicMock())

    def test_cycle_added(self):
        timer = self.engine.cycle(10, MagicMock())
        self.assertTrue(timer in self.engine._deferreds)

    def test_cycle_with_zero_delay(self):
        self.assertRaises(ValueError, self.engine.cycle, 0, MagicMock())

    def test_cycle_with_negative_delay(self):
        self.assertRaises(ValueError, self.engine.cycle, -1, MagicMock())

    def test_remove_timer_with_no_end(self):
        timer = self.engine.callback(MagicMock())
        self.engine._remove_timer(timer)

    def test_remove_nonexistent_timer_with_no_end(self):
        timer = MagicMock()
        timer.end = None
        self.engine._remove_timer(timer)

    def test_remove_timer_with_end(self):
        timer = self.engine.defer(10, MagicMock())
        self.engine._remove_timer(timer)

    def test_remove_nonexistent_timer_with_end(self):
        timer = MagicMock()
        timer.end = 1
        self.engine._remove_timer(timer)

class TestEngineAddChannel(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()
        self.poller = MagicMock()
        self.poller.add = MagicMock()
        self.engine._poller = self.poller
        self.channel = MagicMock()
        self.channel.fileno = "foo"
        self.channel._events = "bar"

    def test_channel_is_added_to_engine(self):
        self.engine.add_channel(self.channel)
        self.assertTrue(self.channel.fileno in self.engine._channels)
        self.assertEqual(self.engine._channels[self.channel.fileno], self.channel)

    def test_channel_is_added_to_poller(self):
        self.engine.add_channel(self.channel)
        self.poller.add.assert_called_once_with(self.channel.fileno, self.channel._events)

class TestEngineModifyChannel(unittest.TestCase):
    def test_channel_is_modified_on_poller(self):
        engine = Engine()
        channel = MagicMock()
        channel.fileno = "foo"
        channel._events = "bar"
        engine._poller.modify = MagicMock()
        engine.modify_channel(channel)
        engine._poller.modify.assert_called_once_with(channel.fileno, channel._events)

class TestEngineRemoveChannel(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()
        self.poller = MagicMock()
        self.poller.remove = MagicMock()
        self.engine._poller = self.poller
        self.channel = MagicMock()
        self.channel.fileno = "foo"
        self.channel._events = "bar"
        self.engine._channels[self.channel.fileno] = self.channel

    def test_channel_is_removed_from_engine(self):
        self.engine.remove_channel(self.channel)
        self.assertFalse(self.channel.fileno in self.engine._channels)

    def test_channel_is_removed_from_poller(self):
        self.engine.remove_channel(self.channel)
        self.poller.remove.assert_called_once_with(self.channel.fileno, self.channel._events)

    def test_removing_channel_from_poller_raises_IOError(self):
        self.poller.remove = MagicMock(side_effect=IOError())
        self.engine.remove_channel(self.channel)
        self.poller.remove.assert_called_once_with(self.channel.fileno, self.channel._events)

    def test_removing_channel_from_poller_raises_OSError(self):
        self.poller.remove = MagicMock(side_effect=OSError())
        self.engine.remove_channel(self.channel)
        self.poller.remove.assert_called_once_with(self.channel.fileno, self.channel._events)

    def test_removing_channel_from_poller_raises_unknown(self):
        self.poller.remove = MagicMock(side_effect=Exception())
        self.assertRaises(Exception, self.engine.remove_channel, self.channel)
        self.poller.remove.assert_called_once_with(self.channel.fileno, self.channel._events)

class TestEngineInstallPoller(unittest.TestCase):
    def setUp(self):
        self.engine = Engine()

    def test_custom_poller(self):
        poller = MagicMock()
        self.engine._poller = None
        self.engine._channels = {}
        self.engine._install_poller(poller)
        self.assertTrue(self.engine._poller is poller)

    @unittest.skip("Not yet implemented.")
    def test_custom_poller_with_existing_channels(self):
        self.fail("Not yet implemented.")

    @unittest.skip("Not yet implemented.")
    def test_custom_poller_with_existing_channels_and_poller(self):
        self.fail("Not yet implemented.")

    @unittest.skip("Not yet implemented.")
    @unittest.skipUnless(hasattr(select, "epoll"), "epoll-specific functionality.")
    def test_defaulting_to_epoll(self):
        self.fail("Not yet implemented.")

    @unittest.skip("Not yet implemented.")
    @unittest.skipIf(hasattr(select, "epoll"), "kqueue-specific functionality.")
    @unittest.skipUnless(hasattr(select, "kqueue"), "kqueue-specific functionality.")
    def test_defaulting_to_kqueue(self):
        self.fail("Not yet implemented.")

    @unittest.skip("Not yet implemented.")
    @unittest.skipIf(hasattr(select, "epoll"), "select-specific functionality.")
    @unittest.skipIf(hasattr(select, "kqueue"), "select-specific functionality.")
    def test_defaulting_to_select(self):
        self.fail("Not yet implemented.")

@unittest.skipUnless(hasattr(select, "epoll"), "epoll-specific functionality.")
class TestEpoll(unittest.TestCase):
    def setUp(self):
        self.poller = _EPoll()
        self.epoll = MagicMock()
        self.epoll.register = MagicMock()
        self.epoll.modify = MagicMock()
        self.epoll.unregister = MagicMock()
        self.epoll.poll = MagicMock()
        self.poller._epoll = self.epoll
        self.fileno = "foo"
        self.events = "bar"

    def test_epoll_add(self):
        self.poller.add(self.fileno, self.events)
        self.epoll.register.assert_called_once_with(self.fileno, self.events)

    def test_epoll_modify(self):
        self.poller.modify(self.fileno, self.events)
        self.epoll.modify.assert_called_once_with(self.fileno, self.events)

    def test_epoll_remove(self):
        self.poller.remove(self.fileno, self.events)
        self.epoll.unregister.assert_called_once_with(self.fileno)

    def test_epoll_poll(self):
        timeout = 10
        ret = self.poller.poll(timeout)
        self.assertTrue(isinstance(ret, dict))
        self.epoll.poll.assert_called_once_with(timeout)

@unittest.skip("Not yet implemented.")
@unittest.skipUnless(hasattr(select, "kqueue"), "kqueue-specific functionality.")
class TestKQueue(unittest.TestCase):
    pass

class TestSelect(unittest.TestCase):
    def setUp(self):
        self.poller = _Select()
        self.fileno = "foo"
        # Beware: here be monkey-patching.
        self.real_select = select.select
        self.fake_select = MagicMock(return_value=([], [], []))
        select.select = self.fake_select

    def tearDown(self):
        select.select = self.real_select

    def test_select_add_all_events(self):
        self.poller.add(self.fileno, Engine.ALL_EVENTS)
        self.assertTrue(self.fileno in self.poller._r)
        self.assertTrue(self.fileno in self.poller._w)
        self.assertTrue(self.fileno in self.poller._e)

    def test_select_add_no_events(self):
        self.poller.add(self.fileno, Engine.NONE)
        self.assertFalse(self.fileno in self.poller._r)
        self.assertFalse(self.fileno in self.poller._w)
        self.assertFalse(self.fileno in self.poller._e)

    def test_select_add_one_event(self):
        self.poller.add(self.fileno, Engine.WRITE)
        self.assertFalse(self.fileno in self.poller._r)
        self.assertTrue(self.fileno in self.poller._w)
        self.assertFalse(self.fileno in self.poller._e)

    def test_select_add_doesnt_erase_previous_events(self):
        self.poller.add(self.fileno, Engine.READ)
        self.assertTrue(self.fileno in self.poller._r)
        self.assertFalse(self.fileno in self.poller._w)
        self.assertFalse(self.fileno in self.poller._e)
        self.poller.add(self.fileno, Engine.WRITE)
        self.assertTrue(self.fileno in self.poller._r)
        self.assertTrue(self.fileno in self.poller._w)
        self.assertFalse(self.fileno in self.poller._e)

    def test_select_modify(self):
        self.poller.remove = MagicMock()
        self.poller.add = MagicMock()
        self.poller.modify(self.fileno, Engine.ALL_EVENTS)
        self.poller.remove.assert_called_once_with(self.fileno, Engine.ALL_EVENTS)
        self.poller.add.assert_called_once_with(self.fileno, Engine.ALL_EVENTS)

    def test_select_remove(self):
        self.poller.add(self.fileno, Engine.ALL_EVENTS)
        # Remember, remove completely deregisters the fileno, it doesn't
        # remove individual events.
        self.poller.remove(self.fileno, Engine.NONE)
        self.assertFalse(self.fileno in self.poller._r)
        self.assertFalse(self.fileno in self.poller._w)
        self.assertFalse(self.fileno in self.poller._e)

    def test_select_poll(self):
        timeout = 10
        args = (self.poller._r, self.poller._w, self.poller._e, timeout)
        ret = self.poller.poll(timeout)
        self.assertTrue(isinstance(ret, dict))
        self.fake_select.assert_called_once_with(*args)

class TestTimer(unittest.TestCase):
    def test_calling_timer_calls_cancel(self):
        timer = _Timer(None, None, None)
        timer.cancel = MagicMock()
        timer()
        timer.cancel.assert_called_once_with()

    def test_comparing_two_timers_compares_end(self):
        timer1 = _Timer(None, None, None, end=1)
        timer2 = _Timer(None, None, None, end=2)
        self.assertTrue(timer2 > timer1)
        self.assertTrue(timer1 < timer2)

    def test_cancelling_timer_calls_engine_remove_timer(self):
        engine = Engine()
        engine._remove_timer = MagicMock()
        timer = _Timer(engine, None, None)
        timer.cancel()
        engine._remove_timer.assert_called_once_with(timer)

########NEW FILE########
__FILENAME__ = test_read_delimiter
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import json
import re
import socket
import struct
import unittest

import pants

from pants.test._pants_util import *

try:
    import netstruct
except ImportError:
    netstruct = None

class LineOriented(pants.Stream):
    def on_connect(self):
        self.read_delimiter = '\r\n'

    def on_read(self, data):
        self.write(data * 2)

class TestReadDelimiterString(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(ConnectionClass=LineOriented).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def test_read_delimiter_string(self):
        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', 4040))
        request = "line1\r\nline2\r\n"
        sock.send(request)
        response = sock.recv(1024)
        sock.close()
        self.assertEqual(response, "line1line1line2line2")

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

class StructOriented(pants.Stream):
    def on_connect(self):
        self.read_delimiter = struct.Struct("!2H")

    def on_read(self, val1, val2):
        self.write(str(val1 * val2))

class TestReadDelimiterStruct(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(StructOriented).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

    def test_read_delimiter_struct(self):
        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', 4040))
        sock.send(struct.pack("!2H", 42, 81))
        response = sock.recv(1024)
        sock.close()
        self.assertEqual(int(response), 42*81)

class NetStructOriented(pants.Stream):
    def on_connect(self):
        self.read_delimiter = netstruct.NetStruct("ih$5b")

    def on_read(self, *data):
        self.write(json.dumps(data))

@unittest.skipIf(netstruct is None, "netstruct library not installed")
class TestReadDelimiterNetStruct(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(NetStructOriented).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

    def test_read_delimiter_netstruct(self):
        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', 4040))
        print sock.send("\x00\x00\x05\x12\x00\x07default\x00\x00\x01\x00\x08")
        response = sock.recv(1024)
        sock.close()
        self.assertEqual(
            json.loads(response),
            [1298, 'default', 0, 0, 1, 0, 8]
        )

class RegexOriented(pants.Stream):
    def on_connect(self):
        self.read_delimiter = re.compile(r"\s\s+")

    def on_read(self, data):
        self.write(data)

class TestReadDelimiterRegex(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(RegexOriented).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

    def test_read_delimiter_regex(self):
        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', 4040))
        sock.send("This is  a test.  ")
        response = sock.recv(1024)
        sock.close()
        self.assertEqual(response, "This isa test.")

class ChunkOriented(pants.Stream):
    def on_connect(self):
        self.read_delimiter = 4

    def on_read(self, data):
        self.write(data * 2)

class TestReadDelimiterChunk(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(ConnectionClass=ChunkOriented).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def test_read_delimiter_number(self):
        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', 4040))
        request = ('1' * 4) + ('2' * 4)
        sock.send(request)
        response = sock.recv(1024)
        sock.close()
        self.assertEqual(response, ('1' * 8) + ('2' * 8))

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

########NEW FILE########
__FILENAME__ = test_sendfile
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import os
import socket
import unittest

import pants

from pants.test._pants_util import *

class FileSender(pants.Stream):
    def on_connect(self):
        with open(os.path.dirname(__file__) + "/data.txt", 'r') as test_file:
            # The file is flushed here to get around an awkward issue
            # that was only happening with the unit test. sendfile() was
            # blocking for some strange reason.
            self.write_file(test_file, flush=True)

class TestSendfile(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(ConnectionClass=FileSender).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def test_sendfile(self):
        with open(os.path.dirname(__file__) + "/data.txt", 'r') as test_file:
            expected_data = ''.join(test_file.readlines())

        sock = socket.socket()
        sock.settimeout(1.0)
        sock.connect(('127.0.0.1', 4040))
        actual_data = sock.recv(1024)
        self.assertEqual(actual_data, expected_data)
        sock.close()

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

########NEW FILE########
__FILENAME__ = test_simple_client
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import os
import socket
import unittest

import pants

from pants.test._pants_util import *

class GoogleClient(pants.Stream):
    def __init__(self, **kwargs):
        pants.Stream.__init__(self, **kwargs)

        self.on_connect_called = False
        self.on_read_called = False
        self.on_close_called = False

    def on_connect(self):
        self.on_connect_called = True
        self.read_delimiter = '\r\n\r\n'
        self.write("HEAD / HTTP/1.1\r\n\r\n")

    def on_read(self, data):
        self.on_read_called = True
        self.close()

    def on_close(self):
        self.on_close_called = True
        self.engine.stop()

class TestSimpleClient(PantsTestCase):
    def setUp(self):
        self.client = GoogleClient()
        PantsTestCase.setUp(self)

    def test_simple_client(self):
        self.client.connect(('google.com', 80))
        self._engine_thread.join(5.0) # Give it plenty of time to talk to Google.
        self.assertTrue(self.client.on_connect_called)
        self.assertTrue(self.client.on_read_called)
        self.assertTrue(self.client.on_close_called)

    @unittest.skip("pants.util.dns is currently disabled")
    def test_simple_client_with_pants_resolve(self):
        # Switched to httpbin.org from google.come because the lack of IPv6
        # routing was making it fail with Google.
        self.client.connect(('httpbin.org', 80), native_resolve=False)
        self._engine_thread.join(5.0) # Give it plenty of time to talk to httpbin.
        self.assertTrue(self.client.on_connect_called)
        self.assertTrue(self.client.on_read_called)
        self.assertTrue(self.client.on_close_called)

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.client.close()

########NEW FILE########
__FILENAME__ = test_ssl
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import os
import socket
import ssl
import unittest

import pants

from pants.test._pants_util import *

CERT_PATH = os.path.dirname(__file__) + '/cert.pem'
CERT_EXISTS = os.path.exists(CERT_PATH)
SSL_OPTIONS = {
    'server_side': True,
    'certfile': CERT_PATH,
    'keyfile': CERT_PATH
    }

class GoogleClient(pants.Stream):
    def __init__(self, **kwargs):
        pants.Stream.__init__(self, **kwargs)

        self.on_ssl_handshake_called = False
        self.on_connect_called = False
        self.on_read_called = False
        self.on_close_called = False

    def on_ssl_handshake(self):
        self.on_ssl_handshake_called = True

    def on_connect(self):
        self.on_connect_called = True
        self.read_delimiter = '\r\n\r\n'
        self.write("HEAD / HTTP/1.1\r\n\r\n")

    def on_read(self, data):
        self.on_read_called = True
        self.close()

    def on_close(self):
        self.on_close_called = True
        self.engine.stop()

class TestSSLClient(PantsTestCase):
    def setUp(self):
        self.client = GoogleClient(ssl_options={}).connect(('google.com', 443))
        PantsTestCase.setUp(self)

    def test_ssl_client(self):
        self._engine_thread.join(5.0) # Give it plenty of time to talk to Google.
        self.assertTrue(self.client.on_ssl_handshake_called)
        self.assertTrue(self.client.on_connect_called)
        self.assertTrue(self.client.on_read_called)
        self.assertTrue(self.client.on_close_called)

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.client.close()

class Echo(pants.Stream):
    def on_read(self, data):
        self.write(data)

@unittest.skipIf(not CERT_EXISTS, "no SSL certificate present in unit test directory")
class TestSSLServer(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(ConnectionClass=Echo, ssl_options=SSL_OPTIONS).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def test_ssl_server(self):
        sock = socket.socket()
        sock.settimeout(1.0)
        ssl_sock = ssl.wrap_socket(sock)
        ssl_sock.connect(('127.0.0.1', 4040))
        request = repr(ssl_sock)
        ssl_sock.send(request)
        response = ssl_sock.recv(1024)
        self.assertEqual(response, request)
        ssl_sock.close()

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

class FileSender(pants.Stream):
    def on_connect(self):
        with open(os.path.dirname(__file__) + "/data.txt", 'r') as test_file:
            # The file is flushed here to get around an awkward issue
            # that was only happening with the unit test. sendfile() was
            # blocking for some strange reason.
            self.write_file(test_file, flush=True)

@unittest.skipIf(not CERT_EXISTS, "no SSL certificate present in unit test directory")
class TestSSLSendfile(PantsTestCase):
    def setUp(self):
        self.server = pants.Server(ConnectionClass=FileSender, ssl_options=SSL_OPTIONS).listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self)

    def test_sendfile(self):
        with open(os.path.dirname(__file__) + "/data.txt", 'r') as test_file:
            expected_data = ''.join(test_file.readlines())

        sock = socket.socket()
        sock.settimeout(1.0)
        ssl_sock = ssl.wrap_socket(sock)
        ssl_sock.connect(('127.0.0.1', 4040))
        actual_data = ssl_sock.recv(1024)
        self.assertEqual(actual_data, expected_data)
        ssl_sock.close()

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

########NEW FILE########
__FILENAME__ = test_stream

import socket
import unittest

from mock import call, MagicMock

from pants.stream import Stream

class TestStream(unittest.TestCase):
    def test_stream_constructor_with_invalid_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.assertRaises(TypeError, Stream, socket=sock)
        sock.close()

    def test_stream_set_read_delimiter_invalid_value(self):
        # not a great test, given that the error needs to be raised
        # with any non-valid type, not just with a list
        stream = Stream()
        passed = False
        try:
            stream.read_delimiter = []
        except TypeError:
            passed = True
        self.assertTrue(passed)

    def test_stream_handle_read_event_processes_recv_buffer_before_closing(self):
        # to ensure we don't reintroduce issue #41
        stream = Stream()
        stream._socket_recv = MagicMock(return_value=None)

        manager = MagicMock()
        stream._process_recv_buffer = manager._process_recv_buffer
        stream.close = manager.close

        stream._handle_read_event()

        expected_calls = [call._process_recv_buffer(), call.close(flush=False)]
        self.assertTrue(manager.mock_calls == expected_calls)

########NEW FILE########
__FILENAME__ = test_timers
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import sys
import time
import unittest

from mock import MagicMock, call

from pants.engine import Engine

class TestTimers(unittest.TestCase):
    def setUp(self):
        self.times_called = []
        self.engine = Engine()

    def timer(self):
        self.times_called.append(self.engine.latest_poll_time)

    def test_callback(self):
        timer = MagicMock()
        self.engine.callback(timer)
        self.engine.poll(0.01)
        self.engine.poll(0.01)
        self.engine.poll(0.01)
        timer.assert_called_once_with()

    def test_callback_cancel(self):
        timer = MagicMock()
        cancel_callback = self.engine.callback(timer)
        cancel_callback()
        self.engine.poll(0.01)
        self.engine.poll(0.01)
        self.engine.poll(0.01)
        self.assertRaises(AssertionError, timer.assert_called_with)

    def test_loop(self):
        timer = MagicMock()
        self.engine.loop(timer)
        self.engine.poll(0.01)
        self.engine.poll(0.01)
        self.engine.poll(0.01)
        timer.assert_has_calls([call() for _ in range(3)])

    def test_loop_cancel(self):
        timer = MagicMock()
        cancel_loop = self.engine.loop(timer)
        self.engine.poll(0.01)
        self.engine.poll(0.01)
        timer.assert_has_calls([call() for _ in range(2)])
        cancel_loop()
        self.engine.poll(0.01)
        timer.assert_has_calls([call() for _ in range(2)])

    def test_defer(self):
        self.engine.poll(0.01)
        timer = MagicMock(side_effect=self.timer)
        expected_time = self.engine.latest_poll_time + 0.01
        self.engine.defer(0.01, timer)
        self.engine.poll(0.2)
        self.engine.poll(0.2)
        self.engine.poll(0.2)
        timer.assert_called_once_with()
        self.assertLess(abs(expected_time - self.times_called[0]), 0.01)

    def test_defer_cancel(self):
        timer = MagicMock()
        cancel_defer = self.engine.defer(0.01, timer)
        cancel_defer()
        self.engine.poll(0.2)
        self.engine.poll(0.2)
        self.engine.poll(0.2)
        self.assertRaises(AssertionError, timer.assert_called_with)

    def test_cycle(self):
        self.engine.poll(0.01)
        timer = MagicMock(side_effect=self.timer)
        expected_times = [
            self.engine.latest_poll_time + 0.01,
            self.engine.latest_poll_time + 0.02,
            self.engine.latest_poll_time + 0.03
            ]
        self.engine.cycle(0.01, timer)
        self.engine.poll(0.2)
        self.engine.poll(0.2)
        self.engine.poll(0.2)
        if sys.platform == "win32": self.engine.poll(0.02)  # See issue #40
        timer.assert_has_calls([call() for _ in range(3)])
        for i in range(3):
            self.assertLess(abs(expected_times[i] - self.times_called[i]), 0.01)

    def test_cycle_cancel(self):
        self.engine.poll(0.01)
        timer = MagicMock(side_effect=self.timer)
        expected_times = [
            self.engine.latest_poll_time + 0.01,
            self.engine.latest_poll_time + 0.02
            ]
        cancel_cycle = self.engine.cycle(0.01, timer)
        self.engine.poll(0.2)
        self.engine.poll(0.2)
        if sys.platform == "win32": self.engine.poll(0.02)  # See issue #40
        timer.assert_has_calls([call() for _ in range(2)])
        cancel_cycle()
        self.engine.poll(0.2)
        timer.assert_has_calls([call() for _ in range(2)])
        for i in range(2):
            self.assertLess(abs(expected_times[i] - self.times_called[i]), 0.01)

########NEW FILE########
__FILENAME__ = test_http_client
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import unittest
import json

from pants.http import HTTPClient
from pants.engine import Engine

from pants.test._pants_util import *

###############################################################################
# SSL Verification Check
###############################################################################

try:
    HTTPClient(verify_ssl=True)
    VERIFY_SSL = True
except RuntimeError:
    VERIFY_SSL = False

###############################################################################
# The Test Case Base
###############################################################################

class HTTPTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = Engine.instance()
        self.client = HTTPClient(self.on_response, self.on_headers, self.on_progress, self.on_ssl_error, self.on_error, engine=self.engine)

    def start(self, timeout=5.0):
        self._timeout = self.engine.defer(timeout, self.timeout)
        self.engine.start()

        self.assertTrue(self.got_response)
        self.assertTrue(self.response_valid)

    def timeout(self):
        self.stop()
        raise AssertionError("Timed out.")

    def stop(self):
        self._timeout()
        del self._timeout
        self.engine.stop()

    def tearDown(self):
        if self.client._stream:
            self.client._want_close = True
            self.client._no_process = True
            self.client._stream.close()
            self.client._stream = None
        del self.client
        del self.engine

    got_response = False
    response_valid = True

    def on_response(self, response):
        self.stop()
        self.got_response = True

    def on_headers(self, response):
        pass

    def on_progress(self, response, received, total):
        pass

    def on_ssl_error(self, response, cert, error):
        pass

    def on_error(self, response, error):
        pass

###############################################################################
# The Cases
###############################################################################

class GetTest(HTTPTestCase):
    def on_response(self, response):
        self.got_response = True
        self.stop()

    def test_get(self):
        self.client.get("http://httpbin.org/ip", {"foo": "bar"})
        self.start()


class PostTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

        data = response.json
        if not data["form"]["foo"] == "bar":
            self.response_valid = False

    def test_post(self):
        self.client.post("http://httpbin.org/post", {"foo": "bar"})
        self.start()

    def test_multipart(self):
        self.got_response = False
        self.response_valid = True

        self.client.post("http://httpbin.org/post", {"foo": "bar"},
                         {"file": ("test.py", "whee")})
        self.start()


class HostChangeTest(HTTPTestCase):

    resp_count = 0

    def on_response(self, response):
        self.resp_count += 1
        if self.resp_count < 2:
            return

        self.stop()
        self.got_response = True

    def test_cookie(self):
        self.client.get("http://www.google.com/")
        self.client.get("http://httpbin.org/ip")
        self.start()


class TimeoutTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.response_valid = False

    def on_error(self, response, error):
        self.stop()
        self.got_response = True

    def test_timeout(self):
        with self.client.session(timeout=1) as ses:
            ses.get("http://httpbin.org/delay/3")
        self.start()


class BadHostTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()

    def on_error(self, response, error):
        self.got_response = True
        self.stop()

    def test_bad_host(self):
        self.client.get("http://www.python.rog/")
        self.start()



class BadPortTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()

    def on_error(self, response, error):
        self.got_response = True
        self.stop()

    def test_bad_port(self):
        self.client.get("http://httpbin.org:65432/")
        self.start()


class GzippedTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

        data = response.json
        if not data["gzipped"] and \
                response.headers['Content-Encoding'] == 'gzip':
            self.response_valid = False

    def test_gzipped(self):
        self.client.get("http://httpbin.org/gzip")
        self.start()


class TeapotTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

        if not response.status_code == 418:
            self.response_valid = False

    def test_teapot(self):
        self.client.get("http://httpbin.org/status/418")
        self.start()


class RedirectTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

        if not len(response.history) == 3 or not response.path == "/get":
            self.response_valid = False

    def test_redirect(self):
        self.client.get("http://httpbin.org/redirect/3")
        self.start()


class RedirectLimitTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

        if not (len(response.history) == 10 and response.status_code == 302):
            self.response_valid = False

    def test_limit(self):
        self.client.get("http://httpbin.org/redirect/12")
        self.start(10)


class RedirectRelativeTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

        if not response.path == "/get":
            self.response_valid = False

    def test_relative(self):
        self.client.get("http://httpbin.org/relative-redirect/3")
        self.start()


class CookieTest(HTTPTestCase):

    resp_count = 0

    def on_response(self, response):
        self.resp_count += 1
        if self.resp_count < 2:
            return

        self.stop()
        self.got_response = True

        if not response.cookies["foo"].value == "bar":
            self.response_valid = False

    def test_cookie(self):
        self.client.get("http://httpbin.org/cookies/set/foo/bar")
        self.client.get("http://httpbin.org/cookies")
        self.start()


class AuthTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

        if not response.status_code == 401:
            self.response_valid = False

    def test_auth(self):
        self.client.get("http://httpbin.org/basic-auth/user/passwd")
        self.start()


class DoAuthTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

        if not response.status_code == 200:
            self.response_valid = False

    def test_do_auth(self):
        with self.client.session(auth=("user", "passwd")) as ses:
            ses.get("http://httpbin.org/basic-auth/user/passwd")
        self.start()


class HTTPSTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

    def test_https(self):
        self.client.get("https://httpbin.org/ip")
        self.start()


@unittest.skipIf(not VERIFY_SSL, "Unable to verify SSL certificates without CA bundle. Install certifi and backports.ssl_match_hostname.")
class BadCertTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()

    def on_ssl_error(self, response, cert, error):
        self.stop()
        self.got_response = True

    def test_bad(self):
        with self.client.session(verify_ssl=True) as ses:
            ses.get("https://www.httpbin.org/ip")
        self.start()


@unittest.skipIf(not VERIFY_SSL, "Unable to verify SSL certificates without CA bundle. Install certifi and backports.ssl_match_hostname.")
class SSLOverrideTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

    def on_ssl_error(self, response, cert, error):
        return True

    def test_override(self):
        with self.client.session(verify_ssl=True) as ses:
            ses.get("https://www.httpbin.org/ip")
        self.start()


class ProgressTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()

    def on_progress(self, response, received, total):
        self.got_response = True

    def test_progress(self):
        self.client.get("http://httpbin.org/get")
        self.start()


class ForceURLEncodedTest(HTTPTestCase):
    def on_response(self, response):
        self.stop()
        self.got_response = True

    def test_force_urlencoded(self):
        self.client.post("http://httpbin.org/post",
                headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.start()

########NEW FILE########
__FILENAME__ = test_http_server
# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import json
try:
    import requests
except ImportError:
    requests = None

from pants.http import HTTPServer
from pants.engine import Engine

from pants.test._pants_util import *

###############################################################################
# The Test Case Base
###############################################################################

class HTTPTestCase(PantsTestCase):
    def request_handler(self, request):
        raise NotImplementedError

    def setUp(self):
        engine = Engine.instance()
        self.server = HTTPServer(self.request_handler, engine=engine)
        self.server.listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self, engine)

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

###############################################################################
# The Cases
###############################################################################

@unittest.skipIf(requests is None, "requests library not installed")
class BasicTest(HTTPTestCase):
    def request_handler(self, request):
        request.send_response("Hello, World!")

    def test_basic(self):
        response = requests.get("http://127.0.0.1:4040/", timeout=0.5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "Hello, World!")

@unittest.skipIf(requests is None, "requests library not installed")
class ExceptionTest(HTTPTestCase):
    def request_handler(self, request):
        print pie

    def test_exception(self):
        response = requests.get("http://127.0.0.1:4040/", timeout=0.5)
        self.assertEqual(response.status_code, 500)

@unittest.skipIf(requests is None, "requests library not installed")
class CookieTest(HTTPTestCase):
    def request_handler(self, request):
        for key in request.cookies:
            val = request.cookies[key].value
            request.cookies_out[val] = key

        request.send_response("Hello, Cookies!")

    def test_cookies(self):
        response = requests.get("http://127.0.0.1:4040/",
                                cookies={"foo": "bar"}, timeout=0.5)
        self.assertEqual(response.cookies["bar"], "foo")

@unittest.skipIf(requests is None, "requests library not installed")
class SecureCookieTest(HTTPTestCase):
    def request_handler(self, request):
        request.set_secure_cookie("foo", "bar")
        request.set_secure_cookie("baz", u"こんにちは！")
        request.set_secure_cookie("what", [True, False, None])
        request.set_secure_cookie("pizza", "tasty", secure=True)
        request.send_response("Hello, Cookies!")

    def other_handler(self, request):
        if request.get_secure_cookie("foo") == "bar" and \
                request.get_secure_cookie("baz") == u"こんにちは！" and \
                request.get_secure_cookie("what") == [True, False, None] and \
                not request.get_secure_cookie("pizza"):
            request.send_response("Okay.")
        else:
            request.send_response("Bad.", 400)

    def test_cookies(self):
        response = requests.get("http://127.0.0.1:4040/", timeout=0.5)
        self.assertEqual(response.status_code, 200)

        self.server.request_handler = self.other_handler

        response = requests.get("http://127.0.0.1:4040/", cookies=response.cookies)
        self.assertEqual(response.status_code, 200)

@unittest.skipIf(requests is None, "requests library not installed")
class ResponseBody(HTTPTestCase):
    def request_handler(self, request):
        data = json.loads(request.body)
        request.send_response(json.dumps(list(reversed(data))))

    def test_body(self):
        response = requests.post("http://127.0.0.1:4040/", json.dumps(range(50)), timeout=0.5)
        data = json.loads(response.text)
        self.assertListEqual(data, range(49, -1, -1))

########NEW FILE########
__FILENAME__ = test_http_utils
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import os
import unittest

from pants.http.utils import *

###############################################################################
# Test HTTP Utilities
###############################################################################

class HTTPHeadersTest(unittest.TestCase):
    def test_headers(self):
        data = HTTPHeaders()
        data['Content-Type'] = 'text/plain'
        
        self.assertEqual(data['content-type'], data['Content-Type'])
        self.assertTrue('CONTENT-TYPE' in data)
        
        del data['CoNtEnT-tYpE']

        self.assertFalse('Content-Type' in data)
        self.assertTrue(data.get('Content-Type') is None)

class FunctionTests(unittest.TestCase):
    def test_get_filename(self):
        with open(__file__) as f:
            self.assertEqual(os.path.basename(get_filename(f)),
                os.path.basename(__file__))

    def test_generate_signature(self):
        self.assertEqual(
            generate_signature("whee", "one", "two", "three"),
            "7d767d29a065e3445184b6d8369bcea03a50fdd8"
        )

    def test_content_type(self):
        self.assertEqual(content_type("test.txt"), "text/plain")

    def test_read_headers(self):
        # read_headers is fussy now about line breaks.
        headers = read_headers(CRLF.join("""Content-Type: text/plain; charset=UTF-8
Content-Length: 12
Content-Encoding: gzip
Server: HTTPants/some-ver
Other-Header: Blah
Set-Cookie: fish=true;
Set-Cookie: pie=blah""".splitlines()))

        self.assertEqual(headers["content-length"], headers["Content-Length"])
        self.assertEqual(int(headers["content-length"]), 12)
        self.assertEqual(len(headers["set-cookie"]), 2)

    def test_bad_headers(self):
        with self.assertRaises(BadRequest):
            read_headers(CRLF.join("""Test: fish

Cake: free""".splitlines()))

########NEW FILE########
__FILENAME__ = log
###############################################################################
#
# Copyright 2011 Chris Davis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import logging


###############################################################################
# Logging Configuration
###############################################################################

if __debug__:
    LEVEL = logging.DEBUG
else:
    LEVEL = logging.DEBUG

logging.basicConfig(
    level=LEVEL,
    filename="pants.log",
    format="[%(asctime)-19s] %(name)-5s : %(levelname)-7s (%(module)s::%(funcName)s:%(lineno)d): %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S"
    )


###############################################################################
# Initialisation
###############################################################################

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(name)-5s : %(levelname)-7s %(message)s")
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

########NEW FILE########
__FILENAME__ = test_web_application
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
Tests for pants.web.Application.
"""

###############################################################################
# Imports
###############################################################################

try:
    import requests
except ImportError:
    requests = None

from mock import MagicMock

from pants.http import HTTPServer, HTTPRequest
from pants.engine import Engine
from pants.web import Application, url_for, error, abort, redirect

from pants.test._pants_util import *

###############################################################################
# Helper
###############################################################################

class RequestContext(object):
    def __init__(self, app, url='/', method='GET', protocol='HTTP/1.1',
                 headers=None, scheme='http', remote_address=("127.0.0.1", 99)):

        connection = MagicMock()
        connection.server = MagicMock()
        connection.server.xheaders = False
        connection.server.cookie_secret = "1234567890"
        connection.remote_address = remote_address

        connection.write = MagicMock()
        connection.finish = MagicMock()

        self.request = HTTPRequest(connection, method, url, protocol, headers, scheme)
        self.request.auto_finish = True

        self.app = app

        self.stack = []

        with self:
            self.result = self.app.route_request(self.request)

    def __enter__(self):
        self.stack.append((Application.current_app, self.app.request))
        Application.current_app = self.app
        self.app.request = self.request

    def __exit__(self, exc_type, exc_val, exc_tb):
        Application.current_app, self.app.request = self.stack.pop()


###############################################################################
# The Test Case Base
###############################################################################

@unittest.skipIf(requests is None, "requests is not installed")
class AppTestCase(PantsTestCase):
    def init_app(self, app):
        raise NotImplementedError

    def setUp(self):
        self.app = Application()
        self.init_app(self.app)

        engine = Engine.instance()
        self.server = HTTPServer(self.app, engine=engine)
        self.server.listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self, engine)

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

###############################################################################
# url_for
###############################################################################

class TestUrlFor(AppTestCase):
    def init_app(self, app):
        @app.route("/")
        def index(request):
            return url_for('index')

        @app.route("/external")
        def external(request):
            return url_for('index', _external=True)

        @app.route("test.example.com/")
        def other_domain(request):
            return None

        @app.route("/domain")
        def domain(request):
            return url_for('other_domain')

        @app.route("/scheme")
        def scheme(request):
            return url_for('index', _scheme="ws")

        @app.route("/same_scheme")
        def same_scheme(request):
            return url_for('index', _scheme='http')

        @app.route("/bad")
        def bad(request):
            return url_for('bad_test')

        @app.route("/args/<var>/")
        def args(request, var):
            pass


    def test_basic(self):
        for url in ("/", "/external", "/test/pants"):
            with RequestContext(self.app, url):
                self.assertEqual(url_for('index'), '/')

        with RequestContext(self.app, headers={'Host': 'test.example.com'}):
            self.assertEqual(url_for('other_domain'), '/')

        with RequestContext(self.app):
            self.assertEqual(url_for('other_domain'), 'http://test.example.com/')

    def test_external(self):
        with RequestContext(self.app):
            self.assertEqual(
                url_for('index', _external=True),
                'http://127.0.0.1/'
            )

            self.assertEqual(
                url_for('other_domain'), 'http://test.example.com/'
            )

        with RequestContext(self.app, headers={'Host': 'www.example.com'}):
            self.assertEqual(
                url_for('scheme', _external=True),
                'http://www.example.com/scheme'
            )

        with RequestContext(self.app, headers={'Host': 'blah:1234'}):
            self.assertEqual(
                url_for('bad', _external=True),
                'http://blah:1234/bad'
            )

    def test_arguments(self):
        with RequestContext(self.app):
            self.assertEqual(url_for('index', test=True), '/?test=True')
            self.assertEqual(url_for('args', 'pie'), '/args/pie/')
            self.assertEqual(url_for('args', var='pie'), '/args/pie/')
            self.assertEqual(
                url_for('args', 'pie', test=True),
                '/args/pie/?test=True'
            )
            with self.assertRaises(ValueError):
                url_for('index', 32, 84)

    def test_domain(self):
        response = requests.get("http://127.0.0.1:4040/domain", timeout=0.5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "http://test.example.com/")

    def test_scheme(self):
        response = requests.get("http://127.0.0.1:4040/scheme", timeout=0.5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "ws://127.0.0.1:4040/")

    def test_same_scheme(self):
        response = requests.get("http://127.0.0.1:4040/same_scheme", timeout=0.5)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "/")

    def test_bad(self):
        response = requests.get("http://127.0.0.1:4040/bad", timeout=0.5)
        self.assertEqual(response.status_code, 500)

    def test_context(self):
        with self.assertRaises(RuntimeError):
            url_for('index')

########NEW FILE########
__FILENAME__ = test_wsgi
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
Note: These tests were adapted from https://github.com/jonashaag/WSGITest
"""

###############################################################################
# Imports
###############################################################################

try:
    import requests
except ImportError:
    requests = None

import pprint

from pants.http import HTTPServer
from pants.web import WSGIConnector

from pants.test._pants_util import *

###############################################################################
# The Test Case Base
###############################################################################

@unittest.skipIf(requests is None, "requests library not installed")
class WSGITestCase(PantsTestCase):
    def application(self, env, start_response):
        raise NotImplementedError

    def setUp(self):
        engine = Engine.instance()
        self.server = HTTPServer(WSGIConnector(self.application, debug=True), engine=engine)
        self.server.listen(('127.0.0.1', 4040))
        PantsTestCase.setUp(self, engine)

    def tearDown(self):
        PantsTestCase.tearDown(self)
        self.server.close()

class WSGIBodyTest(WSGITestCase):
    body = None
    headers = None
    status = None

    def request(self):
        return requests.get("http://127.0.0.1:4040/", timeout=0.5)

    def test_thing(self):
        response = self.request()

        if self.body is not None:
            self.assertEqual(response.text, self.body)

        if self.status is not None:
            self.assertEqual(response.status_code, self.status)

        if self.headers is not None:
            for k,v in self.headers:
                self.assertEqual(response.headers[k], v)

class WSGIServerTest(WSGITestCase):
    def setUp(self):
        WSGITestCase.setUp(self)
        self.passed = True

    def logic(self, env, start_response):
        pass

    def application(self, env, start_response):
        try:
            self.logic(env, start_response)
        except AssertionError as err:
            print err
            print ""
            self.passed = False

        if not self.passed:
            pprint.pprint(env)

        start_response('200 OK', [])
        return []

    def request(self):
        requests.get("http://127.0.0.1:4040/", timeout=0.5)

    def test_thing(self):
        self.request()
        self.assertTrue(self.passed)

###############################################################################
# The Cases
###############################################################################

class EmptyHeader(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 OK', [])
        return ['hello']

    status = 200
    body = "hello"


class ContentLength(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 OK', [('Content-Length', 5)])
        return ['hello']

    status = 200
    body = "hello"


class TooFewArguments(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 OK')
        return []

    status = 500


class TooManyArguments(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 OK', [], 42, 38)
        return []

    status = 500


class WrongType(WSGIBodyTest):
    def application(self, env, start_response):
        start_response(object(), [])
        return ['hello']

    status = 500


class WrongType2(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 OK', object())
        return ['hello']

    status = 500


class WrongReturnType(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 OK', [])
        return object()

    status = 500


class MultiStart(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 OK', [])
        start_response('200 OK', [])
        return ['hello']

    status = 500


###############################################################################
# Server Tests
###############################################################################

class TestGET(WSGIServerTest):
    def logic(self, env, start_response):
        self.assertEqual(env['REQUEST_METHOD'], 'GET')


class TestPOST(WSGIServerTest):
    def logic(self, env, start_response):
        self.assertEqual(env['REQUEST_METHOD'], 'POST')
        self.assertEqual(env['CONTENT_LENGTH'], 12)
        self.assertEqual(env['wsgi.input'].read(), 'Hello World!')

    def request(self):
        requests.post("http://127.0.0.1:4040/", data="Hello World!", timeout=0.5)


class TestQS(WSGIServerTest):
    def logic(self, env, start_response):
        self.assertIn(env['QUERY_STRING'], ('foo=bar&x=y', 'x=y&foo=bar'))

    def request(self):
        requests.get("http://127.0.0.1:4040/", params={'foo':'bar', 'x':'y'}, timeout=0.5)


class TestQSEmpty(WSGIServerTest):
    def logic(self, env, start_response):
        self.assertEqual(env['QUERY_STRING'], '')


class TestHeaderVars(WSGIServerTest):
    def logic(self, env, start_response):
        self.assertDictContainsSubset({
            'HTTP_X_HELLO_IAM_A_HEADER': '42,42',
            'HTTP_HEADER_TWICE': [1, 2],
            'HTTP_IGNORETHECASE_PLEAS_E': 'hello world!',
            'HTTP_MULTILINE_VALUE': 'foo 42 bar and \\r\\n so on'
        }, env)

    def request(self):
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 4040))
        sock.sendall("\r\n".join([
            "GET /foo HTTP/1.1",
            "x-hello-iam-a-header: 42,42",
            "header-twice: 1",
            "IgNoREtheCAsE_pLeas-E: hello world!",
            "header-twice: 2",
            "multiline-value: foo 42",
            "\tbar and \\r\\n\t",
            "\tso",
            " on",
            ]) + "\r\n\r\n")

        sock.settimeout(0.5)
        try:
            sock.recv(4096)
            sock.close()
        except Exception:
            pass


class TestWSGIVars(WSGIServerTest):
    def logic(self, env, start_response):
        self.assertIsInstance(env['wsgi.version'], tuple)
        self.assertEqual(len(env['wsgi.version']), 2)
        self.assertEqual(env['wsgi.url_scheme'][:4], 'http')
        self.assertIsInstance(env['wsgi.multithread'], bool)
        self.assertIsInstance(env['wsgi.multiprocess'], bool)
        self.assertIsInstance(env['wsgi.run_once'], bool)


class TestPostBody(WSGIServerTest):
    def logic(self, env, start_response):
        inp = env['wsgi.input']
        ae = self.assertEqual

        ae(inp.read(1), 'H')
        ae(inp.readline(), 'ello\n')

        for line in inp:
            ae(line, 'World,\r\n')
            break

        ae(inp.read(4), '\twha')
        ae(inp.readlines(), ["t's\r\n", '\r\n', '\n', 'up?'])
        ae(inp.read(123), '')

    def request(self):
        requests.post('http://127.0.0.1:4040/', data="Hello\nWorld,\r\n\twhat's\r\n\r\n\nup?", timeout=0.5)


###############################################################################
# Body Tests
###############################################################################

class TestEmptyChunks(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 ok', [])
        yield 'he'
        yield ''
        yield 'llo'

    body = 'hello'


class TestEmptyChunks2(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 ok', [])
        return ['', '', 'hello']

    body = 'hello'


class TestError(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 ok', [])
        yield 'foo'
        spicy_pies # NameError
        yield 'bar'

    body = 'foo'


class TestStartResponseInThing(WSGIBodyTest):
    def application(self, env, start_response):
        x = False
        for item in ('hello ', 'wor', 'ld!'):
            if not x:
                x = True
                start_response('321 blah', [('Content-Length', '12')])
            yield item

    status = 321
    body = 'hello world!'
    headers = [('Content-Length', '12')]


class TestCustomIterable(WSGIBodyTest):
    def application(self, env, start_response):
        start_response('200 ok', [])
        class foo(object):
            def __iter__(self):
                for char in 'thisisacustomstringfromacustomiterable':
                    yield char
        return foo()

    body = 'thisisacustomstringfromacustomiterable'



########NEW FILE########
__FILENAME__ = _pants_util
###############################################################################
#
# Copyright 2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

import threading
import unittest

from pants.engine import Engine

class PantsTestCase(unittest.TestCase):
    _engine_thread = None

    def setUp(self, engine=None):
        if not engine:
            engine = Engine.instance()
        self._engine = engine
        self._engine_thread = threading.Thread(target=self._engine.start)
        self._engine_thread.start()

    def tearDown(self):
        self._engine.stop()
        if self._engine_thread:
            self._engine_thread.join(1.0)

########NEW FILE########
__FILENAME__ = dns
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
Implementation of the DNS protocol for use in Pants.
"""

###############################################################################
# Imports
###############################################################################

import collections
import itertools
import os
import random
import socket
import struct
import sys
import time

from pants.engine import Engine
from pants.stream import Stream
from pants.datagram import Datagram

###############################################################################
# Logging
###############################################################################

import logging
log = logging.getLogger(__name__)

###############################################################################
# Constants
###############################################################################

# Return Values
DNS_TIMEOUT = -1
DNS_OK = 0
DNS_FORMATERROR = 1
DNS_SERVERFAILURE = 2
DNS_NAMEERROR = 3
DNS_NOTIMPLEMENTED = 4
DNS_REFUSED = 5

# DNS Listening Port
DNS_PORT = 53

# Query Types
(A, NS, MD, MF, CNAME, SOA, MB, MG, MR, NULL, WKS, PTR, HINFO, MINFO, MX, TXT,
 RP, AFSDB, X25, ISDN, RT, NSAP, NSAP_PTR, SIG, KEY, PX, GPOS, AAAA, LOC, NXT,
 EID, NIMLOC, SRV, ATMA, NAPTR, KX, CERT, A6, DNAME, SINK, OPT, APL, DS, SSHFP,
 IPSECKEY, RRSIG, NSEC, DNSKEY, DHCID, NSEC3, NSEC3PARAM) = range(1,52)

QTYPES = "A, NS, MD, MF, CNAME, SOA, MB, MG, MR, NULL, WKS, PTR, HINFO, MINFO, MX, TXT, RP, AFSDB, X25, ISDN, RT, NSAP, NSAP_PTR, SIG, KEY, PX, GPOS, AAAA, LOC, NXT, EID, NIMLOC, SRV, ATMA, NAPTR, KX, CERT, A6, DNAME, SINK, OPT, APL, DS, SSHFP, IPSECKEY, RRSIG, NSEC, DNSKEY, DHCID, NSEC3, NSEC3PARAM".split(', ')

# OPCODEs
OP_QUERY = 0
OP_IQUERY = 1
OP_STATUS = 2

# Query Classes
IN = 1

# Default Servers
DEFAULT_SERVERS = [
    '127.0.0.1',
    '8.8.8.8'
    ]

# Internal Exception
class TooShortError(ValueError):
    pass

# RDATA Declarations
RDATA_TYPES = {
    A: (('address', 'ipv4'), ),
    NS: 'name',
    MD: 'name',
    MF: 'name',
    CNAME: 'name',
    SOA: (('mname', 'name'), ('rname', 'name'), ('serial|refresh|retry|expire|minimum', '!LlllL')),
    MB: 'name',
    MG: 'name',
    MR: 'name',
    NULL: 'str',
    WKS: (('address', 'ipv4'), ('protocol', '!B'), ('map', 'str')),
    PTR: 'name',
    HINFO: (('cpu', 'lstr'), ('os', 'lstr')),
    MINFO: (('rmailbx', 'name'), ('emailbx', 'name')),
    MX: (('preference', '!H'), ('name', 'name')),
    TXT: 'strs',
    RP: (('mbox', 'name'), ('txt', 'name')),

    AAAA: (('address', 'ipv6'), ),

    SRV: (('priority|weight|port', '!3H'), ('target', 'name')),

    DNAME: 'name',

    DNSKEY: (('flags|protocol|algorithm', '!H2B'), ('key', 'str')),
    }

RDATA_TUPLES = {}

for k,v in RDATA_TYPES.iteritems():
    # Get the Name.
    nm = '%s_Record' % QTYPES[k-1]

    if v == 'strs':
        continue

    elif v == 'str':
        RDATA_TUPLES[k] = collections.namedtuple(nm, ['value'])
        continue

    elif v == 'name':
        RDATA_TUPLES[k] = collections.namedtuple(nm, ['name'])
        continue

    keys = []
    for fn, ft in v:
        if '|' in fn:
            keys.extend(fn.split('|'))
        else:
            keys.append(fn)

    RDATA_TUPLES[k] = collections.namedtuple(nm, keys)

###############################################################################
# OS-Specific DNS Server Listing and hosts Code
###############################################################################

if os.name == 'nt':
    from ctypes import c_int, c_void_p, POINTER, windll, wintypes, \
                       create_string_buffer, c_char, c_char_p, c_size_t

    DWORD = wintypes.DWORD
    LPCWSTR = wintypes.LPCWSTR
    DNS_CONFIG_DNS_SERVER_LIST = 6

    DnsQueryConfig = windll.dnsapi.DnsQueryConfig
    DnsQueryConfig.argtypes = [
        c_int,              # __in      DNS_CONFIG_TYPE Config,
        DWORD,              # __in      DWORD Flag,
        LPCWSTR,            # __in_opt  PCWSTR pwsAdapterName,
        c_void_p,           # __in_opt  PVOID pReserved,
        POINTER(c_char),    # __out     PVOID pBuffer,
        POINTER(DWORD),     # __inout   PDWORD pBufferLength
    ]

    def list_dns_servers():
        # First, figure out how much data we need.
        needed = DWORD(0)

        result = DnsQueryConfig(DNS_CONFIG_DNS_SERVER_LIST,
                                0, None, None, None, needed)

        if result == 0:
            if needed.value == 0:
                # No results, apparently.
                return DEFAULT_SERVERS[:]
            else:
                result = 234

        if result != 234:
            raise Exception("Unexpected result calling DnsQueryConfig, %d." % result)

        # Now, call it.
        buf = create_string_buffer(needed.value)

        result = DnsQueryConfig(DNS_CONFIG_DNS_SERVER_LIST,
                                0, None, None, buf, needed)

        if result == 234:
            # Set the number of IPs to the space we have.
            ips = (needed.value - 4) / 4
        else:
            # Some kind of magic.
            ips = struct.unpack('I',buf[0:4])[0]

        # Do crazy stuff.
        out = []
        for i in xrange(ips):
            start = (i+1) * 4
            out.append(socket.inet_ntoa(buf[start:start+4]))

        out.extend(DEFAULT_SERVERS)
        return out

    # Additional Functions
    if not hasattr(socket, 'inet_pton') and hasattr(windll, 'ws2_32') and hasattr(windll.ws2_32, 'inet_pton'):
        _inet_pton = windll.ws2_32.inet_pton
        _inet_pton.argtypes = [
            c_int,              # __in  INT Family,
            c_char_p,           # __in  PCTSTR pszAddrString,
            POINTER(c_char),    # __out PVOID pAddrBuf
            ]

        def inet_pton(address_family, ip_string):
            """
            Convert an IP address from its family-specific string format to a
            packed, binary format. inet_pton() is useful when a library or
            network protocol calls for an object of type ``struct in_addr`` or
            ``struct in6_addr``.

            ===============  ============
            Argument         Description
            ===============  ============
            address_family   Supported values are ``socket.AF_INET`` and ``socket.AF_INET6``.
            ip_string        The IP address to pack.
            ===============  ============
            """
            if not address_family in (socket.AF_INET, socket.AF_INET6):
                raise socket.error(97, os.strerror(97))

            if address_family == socket.AF_INET:
                bytes = 5
            else:
                bytes = 17

            buf = create_string_buffer(bytes)

            result = _inet_pton(address_family, ip_string, buf)
            if result == 0:
                raise socket.error("illegal IP address string passed to inet_pton")
            elif result != 1:
                raise socket.error("unknown error calling inet_pton")

            return buf.raw[:bytes-1]

        socket.inet_pton = inet_pton

    if not hasattr(socket, 'inet_ntop') and hasattr(windll, 'ws2_32') and hasattr(windll.ws2_32, 'inet_ntop'):
        _inet_ntop = windll.ws2_32.inet_ntop
        _inet_ntop.argtypes = [
            c_int,              # __in  INT Family,
            POINTER(c_char),    # __in  PVOID pAddr,
            c_char_p,           # __out PTSTR pStringBuf,
            c_size_t,           # __in  size_t StringBufSize
            ]

        def inet_ntop(address_family, packed_ip):
            """
            Convert a packed IP address (a string of some number of characters)
            to its standard, family-specific string representation (for
            example, ``'7.10.0.5`` or ``5aef:2b::8``). inet_ntop() is useful
            when a library or network protocol returns an object of type
            ``struct in_addr`` or ``struct in6_addr``.

            ===============  ============
            Argument         Description
            ===============  ============
            address_family   Supported values are ``socket.AF_INET`` and ``socket.AF_INET6``.
            packed_ip        The IP address to unpack.
            ===============  ============
            """
            if not address_family in (socket.AF_INET, socket.AF_INET6):
                raise socket.error(97, os.strerror(97))

            if address_family == socket.AF_INET:
                bytes = 17
            else:
                bytes = 47

            buf = create_string_buffer(bytes)

            result = _inet_ntop(address_family, packed_ip, buf, bytes)
            if not result:
                raise socket.error("unknown error calling inet_ntop")

            return buf.value

        socket.inet_ntop = inet_ntop

    host_path = os.path.join(os.path.expandvars("%SystemRoot%"), "system32", "drivers", "etc", "hosts")

else:
    # *nix is way easier. Parse resolve.conf.
    def list_dns_servers():
        out = []
        try:
            with open('/etc/resolv.conf','r') as f:
                for l in f.readlines():
                    if l.startswith('nameserver '):
                        out.append(l[11:].strip())
        except IOError:
            pass

        out.extend(DEFAULT_SERVERS)
        return out

    host_path = "/etc/hosts"

###############################################################################
# Hosts
###############################################################################

hosts = {A: {}, AAAA: {}}
host_m = None
host_time = None

def load_hosts():
    global host_m
    global host_time

    host_time = time.time()

    try:
        stat = os.stat(host_path)
        if hosts and host_m is not None:
            if host_m == (stat.st_mtime, stat.st_size):
                return

        hosts[A].clear()
        hosts[AAAA].clear()

        with open(host_path, 'r') as f:
            for l in f.readlines():
                l = l.strip().split(None, 1)
                if len(l) < 2 or l[0].startswith('#') or not all(l):
                    continue
                ip = l[0].strip()
                host = [x.strip() for x in l[1].split()]

                try:
                    socket.inet_aton(ip)

                    for h in host:
                        hosts[A][h] = ip

                except socket.error:
                    if hasattr(socket, 'inet_pton'):
                        try:
                            socket.inet_pton(socket.AF_INET6, ip)

                            for h in host:
                                hosts[AAAA][h] = ip

                        except socket.error:
                            continue

        host_m = (stat.st_mtime, stat.st_size)
    except (OSError, ValueError):
        pass

    if not 'localhost' in hosts[A]:
        hosts[A]['localhost'] = '127.0.0.1'

    if not 'localhost' in hosts[AAAA]:
        hosts[AAAA]['localhost'] = '::1'

load_hosts()

###############################################################################
# DNSMessage Class
###############################################################################

class DNSMessage(object):
    """
    This class stores all the information used in a DNS message, and can either
    generate valid messages to be sent to a server or read messages from a
    server.

    To convert an instance of DNSMessage into a byte string for sending to the
    server, simply use str() on it. To read a message from the server into an
    instance of DNSMessage, use DNSMessage.from_string().
    """
    __slots__ = ('id','qr','opcode','aa','tc','rd','ra','rcode','server',
                'questions','answers','authrecords','additional')

    def __init__(self, id=None, qr=False, opcode=OP_QUERY, aa=False, tc=False,
                    rd=True, ra=True, rcode=DNS_OK):

        self.id = id
        self.qr = qr
        self.opcode = opcode
        self.aa = aa
        self.tc = tc
        self.rd = rd
        self.ra = ra
        self.rcode = rcode

        self.server = None

        self.questions = []
        self.answers = []
        self.authrecords = []
        self.additional = []

    def __str__(self):
        return self.to_string()

    def to_string(self, limit=None):
        """
        Render the DNSMessage as a string of bytes that can be sent to a DNS
        server. If a *limit* is specified and the length of the string exceeds
        that limit, the truncated byte will automatically be set to True.

        =========  ========  ============
        Argument   Default   Description
        =========  ========  ============
        limit      None      *Optional.* The maximum size of the message to generate, in bytes.
        =========  ========  ============
        """
        out = ""

        ## Body

        for q in self.questions:
            qname, qtype, qclass = q

            for part in qname.split('.'):
                out += chr(len(part)) + part

            out += '\x00' + struct.pack('!2H', qtype, qclass)

        for q in itertools.chain(self.answers, self.authrecords, self.additional):
            name, typ, clss, ttl, rdata = q

            for part in name.split('.'):
                out += chr(len(part)) + part

            out += '\x00%s%s' % (
                struct.pack('!2HIH', typ, clss, ttl, len(rdata)),
                rdata
                )

        ## Header

        if limit:
            tc = len(out) + 12 > limit
            out = out[:(limit-12)]
        else:
            tc = self.tc

        byte3 = (self.qr << 7) | (self.opcode << 3) | (self.aa << 2) | \
                (tc << 1) | self.rd

        byte4 = (self.ra << 7) | self.rcode

        hdr = struct.pack('!H2B4H', self.id, byte3, byte4, len(self.questions),
                len(self.answers), len(self.authrecords), len(self.additional))

        return hdr + out

    @classmethod
    def from_string(cls, data):
        """
        Create a DNSMessage instance containing the provided data in a usable
        format.

        =========  ============
        Argument   Description
        =========  ============
        data       The data to parse into a DNSMessage instance.
        =========  ============
        """
        if len(data) < 12:
            raise TooShortError

        self = cls()

        full_data = data

        self.id, byte3, byte4, qdcount, ancount, nscount, arcount = \
            struct.unpack('!H2B4H', data[:12])

        self.qr = bool(byte3 >> 7)
        self.opcode = (byte3 & 120) >> 3
        self.aa = bool((byte3 & 4) >> 2)
        self.tc = bool((byte3 & 2) >> 1)
        self.rd = bool(byte3 & 1)

        self.ra = bool(byte4 >> 7)
        self.rcode = byte4 & 15

        data = data[12:]

        try:
            for i in xrange(qdcount):
                qname, qtype, qclass, bytes = readQuery(data, full_data)
                data = data[bytes:]
                self.questions.append((qname, qtype, qclass))

            for i in xrange(ancount):
                name, typ, clss, ttl, rdata, bytes = readAnswer(data, full_data)
                data = data[bytes:]
                self.answers.append((name, typ, clss, ttl, rdata))

            for i in xrange(nscount):
                name, typ, clss, ttl, rdata, bytes = readAnswer(data, full_data)
                data = data[bytes:]
                self.authrecords.append((name, typ, clss, ttl, rdata))

            for i in xrange(arcount):
                name, typ, clss, ttl, rdata, bytes = readAnswer(data, full_data)
                data = data[bytes:]
                self.additional.append((name, typ, clss, ttl, rdata))

        except TooShortError:
            if not self.tc:
                raise

        return self

###############################################################################
# Message Reading Functions
###############################################################################

def readName(data, full_data=None):
    """
    Read a QNAME from the bytes of a DNS message.
    """
    if not data:
        raise TooShortError

    orig = len(data)

    name = None
    while True:
        if not data:
            raise TooShortError

        l = ord(data[0])

        if full_data and l & 0xC0 == 0xC0:
            offset, = struct.unpack('!H', data[:2])
            offset ^= 0xC000

            if name:
                name += '.%s' % readName(full_data[offset:], full_data)[0]
            else:
                name = readName(full_data[offset:], full_data)[0]
            data = data[2:]
            break

        elif l == 0:
            data = data[1:]
            break

        if len(data) < 1 + l:
            raise TooShortError

        if name:
            name += '.%s' % data[1:l+1]
        else:
            name = data[1:l+1]
        data = data[1+l:]

    return name, orig - len(data)

def readAnswer(data, full_data):
    """
    Read an answer (or similarly formatted record) from a DNS message.
    """
    if not data:
        raise TooShortError

    orig = len(data)

    name, bytes = readName(data, full_data)
    data = data[bytes:]

    if len(data) < 10:
        raise TooShortError

    typ, clss, ttl, rdlength = struct.unpack('!2HIH', data[:10])
    data = data[10:]

    if not data or len(data) < rdlength:
        raise TooShortError

    rdata = readRDATA(data[:rdlength], full_data, typ)
    data = data[rdlength:]

    return name, typ, clss, ttl, rdata, orig - len(data)

def readQuery(data, full_data):
    """
    Read a query from a DNS message.
    """
    if not data:
        raise TooShortError

    orig = len(data)

    qname, bytes = readName(data, full_data)
    data = data[bytes:]

    if len(data) < 4:
        raise TooShortError

    qtype, qclass = struct.unpack('!2H', data[:4])

    return qname, qtype, qclass, (orig - len(data)) + 4

def readRDATA(data, full_data, qtype):
    """
    Read RDATA for a given QTYPE into an easy-to-use namedtuple.
    """
    if not qtype in RDATA_TYPES:
        return data

    format = RDATA_TYPES[qtype]

    # Special cast for TXT.
    if format == 'strs':
        values = []
        while data:
            l = ord(data[0])
            values.append(data[1:1+l:])
            data = data[1+l:]
        return tuple(values)

    tup = RDATA_TUPLES[qtype]

    if format == 'name':
        return tup(readName(data, full_data)[0])

    values = []
    for fn, ft in format:
        if ft == 'ipv4':
            values.append(socket.inet_ntoa(data[:4]))
            data = data[4:]

        elif ft == 'ipv6':
            if hasattr(socket, 'inet_ntop'):
                values.append(socket.inet_ntop(socket.AF_INET6, data[:16]))
            else:
                values.append(data[:16])
            data = data[16:]

        elif ft == 'lstr':
            l = ord(data[0])
            values.append(data[1:1+l])
            data = data[1+l:]

        elif ft == 'name':
            v, bytes = readName(data, full_data)
            data = data[bytes:]
            values.append(v)

        elif ft == 'str':
            values.append(data)
            data = ''

        else:
            sz = struct.calcsize(ft)
            values.extend(struct.unpack(ft, data[:sz]))
            data = data[sz:]

    return tup(*values)

###############################################################################
# _DNSStream Class
###############################################################################

class _DNSStream(Stream):
    """
    A subclass of Stream that makes things way easier inside Resolver.
    """
    def __init__(self, resolver, id, **kwargs):
        Stream.__init__(self, **kwargs)
        self.resolver = resolver
        self.id = id

        self.response = ''

    def on_connect(self):
        if not self.id in self.resolver._messages:
            if self.id in self.resolver._tcp:
                del self.resolver._tcp[self.id]
            self.close()
            return

        message = str(self.resolver._messages[self.id][1])
        self._wait_for_write_event = True
        self.write(message)

    def on_read(self, data):
        if not self.id in self.resolver._messages:
            if self.id in self.resolver._tcp:
                del self.resolver._tcp[self.id]
            self.close()
            return

        self.response += data

        try:
            m = DNSMessage.from_string(self.response)
        except TooShortError:
            return

        if self.remote_address and isinstance(self.remote_address, tuple):
            m.server = '%s:%d' % self.remote_address

        if self.id in self.resolver._tcp:
            del self.resolver._tcp[self.id]
        self.close()

        self.resolver.receive_message(m)

###############################################################################
# Resolver Class
###############################################################################

class Resolver(object):
    """
    The Resolver class generates DNS messages, sends them to remote servers,
    and processes any responses. The bulk of the heavy lifting is done in
    DNSMessage and the RDATA handling functions, however.

    =========  ============
    Argument   Description
    =========  ============
    servers    *Optional.* A list of DNS servers to query. If a list isn't provided, Pants will attempt to retrieve a list of servers from the OS, falling back to a list of default servers if none are available.
    engine     *Optional.* The :class:`pants.engine.Engine` instance to use.
    =========  ============
    """
    def __init__(self, servers=None, engine=None):
        self.servers = servers or list_dns_servers()
        self.engine = engine or Engine.instance()

        # Internal State
        self._messages = {}
        self._cache = {}
        self._queries = {}
        self._tcp = {}
        self._udp = None
        self._last_id = -1

    def _safely_call(self, callback, *args, **kwargs):
        try:
            callback(*args, **kwargs)
        except Exception:
            log.exception('Error calling callback for DNS result.')

    def _error(self, message, err=DNS_TIMEOUT):
        if not message in self._messages:
            return

        if message in self._tcp:
            try:
                self._tcp[message].close()
            except Exception:
                pass
            del self._tcp[message]

        callback, message, df_timeout, media, data = self._messages[message]
        del self._messages[message.id]

        try:
            df_timeout.cancel()
        except Exception:
            pass

        if err == DNS_TIMEOUT and data:
            self._safely_call(callback, DNS_OK, data)
        else:
            self._safely_call(callback, err, None)

    def _init_udp(self):
        """
        Create a new Datagram instance and listen on a socket.
        """
        self._udp = Datagram(engine=self.engine)
        self._udp.on_read = self.receive_message

        start = port = random.randrange(10005, 65535)
        while True:
            try:
                self._udp.listen(('',port))
                break
            except Exception:
                port += 1
                if port > 65535:
                    port = 10000
                if port == start:
                    raise Exception("Can't listen on any port.")

    def send_message(self, message, callback=None, timeout=10, media=None):
        """
        Send an instance of DNSMessage to a DNS server, and call the provided
        callback when a response is received, or if the action times out.

        =========  ========  ============
        Argument   Default   Description
        =========  ========  ============
        message              The :class:`DNSMessage` instance to send to the server.
        callback   None      *Optional.* The function to call once the response has been received or the attempt has timed out.
        timeout    10        *Optional.* How long, in seconds, to wait before timing out.
        media      None      *Optional.* Whether to use UDP or TCP. UDP is used by default.
        =========  ========  ============
        """
        while message.id is None or message.id in self._messages:
            self._last_id += 1
            if self._last_id > 65535:
                self._last_id = 0
            message.id = self._last_id

        # Timeout in timeout seconds.
        df_timeout = self.engine.defer(timeout, self._error, message.id)

        # Send the Message
        msg = str(message)
        if media is None:
            media = 'udp'
            #if len(msg) > 512:
            #    media = 'tcp'
            #else:
            #    media = 'udp'

        # Store Info
        self._messages[message.id] = callback, message, df_timeout, media, None

        if media == 'udp':
            if self._udp is None:
                self._init_udp()
            try:
                self._udp.write(msg, (self.servers[0], DNS_PORT))
            except Exception:
                # Pants gummed up. Try again.
                self._next_server(message.id)

            self.engine.defer(0.5, self._next_server, message.id)

        else:
            tcp = self._tcp[message.id] = _DNSStream(self, message.id)
            tcp.connect((self.servers[0], DNS_PORT))

    def _next_server(self, id):
        if not id in self._messages or id in self._tcp:
            return

        # Cycle the list.
        self.servers.append(self.servers.pop(0))

        msg = str(self._messages[id][1])
        try:
            self._udp.write(msg, (self.servers[0], DNS_PORT))
        except Exception:
            try:
                self._udp.close()
            except Exception:
                pass
            del self._udp
            self._init_udp()
            self._udp.write(msg, (self.servers[0], DNS_PORT))

    def receive_message(self, data):
        if not isinstance(data, DNSMessage):
            try:
                data = DNSMessage.from_string(data)
            except TooShortError:
                if len(data) < 2:
                    return

                id = struct.unpack("!H", data[:2])
                if not id in self._messages:
                    return

                self._error(id, err=DNS_FORMATERROR)
                return

        if not data.id in self._messages:
            return

        callback, message, df_timeout, media, _ = self._messages[data.id]

        #if data.tc and media == 'udp':
        #    self._messages[data.id] = callback, message, df_timeout, 'tcp', data
        #    tcp = self._tcp[data.id] = _DNSStream(self, message.id)
        #    tcp.connect((self.servers[0], DNS_PORT))
        #    return

        if not data.server:
            if self._udp and isinstance(self._udp.remote_address, tuple):
                data.server = '%s:%d' % self._udp.remote_address
            else:
                data.server = '%s:%d' % (self.servers[0], DNS_PORT)

        try:
            df_timeout.cancel()
        except Exception:
            pass

        del self._messages[data.id]
        self._safely_call(callback, DNS_OK, data)

    def query(self, name, qtype=A, qclass=IN, callback=None, timeout=10, allow_cache=True, allow_hosts=True):
        """
        Make a DNS request of the given QTYPE for the given name.

        ============  ========  ============
        Argument      Default   Description
        ============  ========  ============
        name                    The name to query.
        qtype         A         *Optional.* The QTYPE to query.
        qclass        IN        *Optional.* The QCLASS to query.
        callback      None      *Optional.* The function to call when a response for the query has been received, or when the request has timed out.
        timeout       10        *Optional.* The time, in seconds, to wait before timing out.
        allow_cache   True      *Optional.* Whether or not to use the cache. If you expect to be performing thousands of requests, you may want to disable the cache to avoid excess memory usage.
        allow_hosts   True      *Optional.* Whether or not to use any records gathered from the OS hosts file.
        ============  ========  ============
        """
        if not isinstance(qtype, (list,tuple)):
            qtype = (qtype, )

        if allow_hosts:
            if host_time + 30 < time.time():
                load_hosts()

            cname = None
            if name in self._cache and CNAME in self._cache[name]:
                cname = self._cache[name][CNAME]

            result = []

            if AAAA in qtype and name in hosts[AAAA]:
                result.append(hosts[AAAA][name])

            if A in qtype and name in hosts[A]:
                result.append(hosts[A][name])

            if result:
                if callback:
                    self._safely_call(callback, DNS_OK, cname, None, tuple(result))
                return

        if allow_cache and name in self._cache:
            cname = self._cache[name].get(CNAME, None)

            tm = time.time()
            result = []
            min_ttl = sys.maxint

            for t in qtype:
                death, ttl, rdata = self._cache[name][(t, qclass)]
                if death < tm:
                    del self._cache[name][(t, qclass)]
                    continue

                min_ttl = min(ttl, min_ttl)
                if rdata:
                    result.extend(rdata)

            if callback:
                self._safely_call(callback, DNS_OK, cname, min_ttl,
                                    tuple(result))
            return

        # Build a message and add our question.
        m = DNSMessage()

        m.questions.append((name, qtype[0], qclass))

        # Make the function for handling our response.
        def handle_response(status, data):
            cname = None
            # TTL is 30 by default, so answers with no records we want will be
            # repeated, but not too often.
            ttl = sys.maxint

            if not data:
                self._safely_call(callback, status, None, None, None)
                return

            rdata = {}
            final_rdata = []
            for (aname, atype, aclass, attl, ardata) in data.answers:
                if atype == CNAME:
                    cname = ardata[0]

                if atype in qtype and aclass == qclass:
                    ttl = min(attl, ttl)
                    if len(ardata) == 1:
                        rdata.setdefault(atype, []).append(ardata[0])
                        final_rdata.append(ardata[0])
                    else:
                        rdata.setdefault(atype, []).append(ardata)
                        final_rdata.append(ardata)
            final_rdata = tuple(final_rdata)
            ttl = min(30, ttl)

            if allow_cache:
                if not name in self._cache:
                    self._cache[name] = {}
                    if cname:
                        self._cache[name][CNAME] = cname
                    for t in qtype:
                        self._cache[name][(t, qclass)] = time.time() + ttl, ttl, rdata.get(t, [])

            if data.rcode != DNS_OK:
                status = data.rcode

            self._safely_call(callback, status, cname, ttl, final_rdata)

        # Send it, so we get an ID.
        self.send_message(m, handle_response)

resolver = Resolver()

###############################################################################
# Helper Functions
###############################################################################

query = resolver.query
send_message = resolver.send_message

def gethostbyaddr(ip_address, callback, timeout=10):
    """
    Returns a tuple ``(hostname, aliaslist, ipaddrlist)``, functioning similarly
    to :func:`socket.gethostbyaddr`. When the information is available, it will
    be passed to callback. If the attempt fails, the callback will be called
    with None instead.

    ===========  ========  ============
    Argument     Default   Description
    ===========  ========  ============
    ip_address             The IP address to look up information on.
    callback               The function to call when a result is available.
    timeout      10        *Optional.* How long, in seconds, to wait before timing out.
    ===========  ========  ============
    """
    is_ipv6 = False
    if hasattr(socket, 'inet_pton'):
        try:
            addr = socket.inet_pton(socket.AF_INET6, ip_address)
            is_ipv6 = True
        except socket.error:
            try:
                addr = socket.inet_pton(socket.AF_INET, ip_address)
            except socket.error:
                raise ValueError("%r is not a valid IP address." % ip_address)
    else:
        try:
            addr = socket.inet_aton(ip_address)
        except socket.error:
            is_ipv6 = True

    if is_ipv6:
        if not hasattr(socket, 'inet_pton'):
            raise ImportError("socket lacks inet_pton.")
        addr = socket.inet_pton(socket.AF_INET6, ip_address)

        name = ''.join('%02x' % ord(c) for c in addr)
        name = '.'.join(reversed(name)) + '.ip6.arpa'

    else:
        name = '.'.join(reversed(ip_address.split('.'))) + '.in-addr.arpa'


    def handle_response(status, cname, ttl, rdata):
        if status != DNS_OK:
            res = None
        else:
            if not rdata:
                res = None
            else:
                res = rdata[0], [name] + list(rdata[1:]), [ip_address]

        try:
            callback(res)
        except Exception:
            log.exception('Error calling callback for gethostbyaddr.')

    resolver.query(name, qtype=PTR, callback=handle_response, timeout=timeout)

def gethostbyname(hostname, callback, timeout=10):
    """
    Translate a host name to an IPv4 address, functioning similarly to
    :func:`socket.gethostbyname`. When the information becomes available, it
    will be passed to callback. If the underlying query fails, the callback
    will be called with None instead.

    =========  ========  ============
    Argument   Default   Description
    =========  ========  ============
    hostname             The hostname to look up information on.
    callback             The function to call when a result is available.
    timeout    10        *Optional.* How long, in seconds, to wait before timing out.
    =========  ========  ============
    """
    def handle_response(status, cname, ttl, rdata):
        if status != DNS_OK or not rdata:
            res = None
        else:
            res = rdata[0]

        try:
            callback(res)
        except Exception:
            log.exception('Error calling callback for gethostbyname.')

    resolver.query(hostname, qtype=A, callback=handle_response, timeout=timeout)

def gethostbyname_ex(hostname, callback, timeout=10):
    """
    Translate a host name to an IPv4 address, functioning similarly to
    :func:`socket.gethostbyname_ex` and return a tuple
    ``(hostname, aliaslist, ipaddrlist)``. When the information becomes
    available, it will be passed to callback. If the underlying query fails,
    the callback will be called with None instead.

    =========  ========  ============
    Argument   Default   Description
    =========  ========  ============
    hostname             The hostname to look up information on.
    callback             The function to call when a result is available.
    timeout    10        *Optional.* How long, in seconds, to wait before timing out.
    =========  ========  ============
    """
    def handle_response(status, cname, ttl, rdata):
        if status != DNS_OK or not rdata:
            res = None
        else:
            if cname != hostname:
                res = cname, [hostname], list(rdata)
            else:
                res = cname, [], list(rdata)

        try:
            callback(res)
        except Exception:
            log.exception('Error calling callback for gethostbyname_ex.')

    resolver.query(hostname, qtype=A, callback=handle_response, timeout=timeout)

###############################################################################
# Synchronous Support
###############################################################################

class Synchroniser(object):
    __slots__ = ('_parent',)

    def __init__(self, parent):
        self._parent = parent

    def __getattr__(self, key):
        if key.startswith('_'):
            return object.__getattribute__(self, key)

        func = self._parent[key]

        if not callable(func):
            raise ValueError("%r isn't callable." % key)

        def doer(*a, **kw):
            if Engine.instance()._running:
                raise RuntimeError("synchronous calls cannot be made while Pants is already running.")

            data = []

            def callback(*a,**kw):
                if kw:
                    if a:
                        a = a + (kw, )
                    else:
                        a = kw

                if isinstance(a, tuple) and len(a) == 1:
                    a = a[0]

                data.append(a)
                Engine.instance().stop()

            kw['callback'] = callback
            func(*a, **kw)
            Engine.instance().start()
            return data[0]

        doer.__name__ = func.__name__

        return doer

sync = synchronous = Synchroniser(globals())

########NEW FILE########
__FILENAME__ = sendfile
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
Various implementations of the platform-dependant sendfile() system
call.
"""

###############################################################################
# Imports
###############################################################################

import os
import socket
import sys

import ctypes
import ctypes.util


###############################################################################
# Constants
###############################################################################

SENDFILE_PLATFORMS = ("linux2", "darwin", "freebsd", "dragonfly")
SENDFILE_AMOUNT = 2 ** 16


###############################################################################
# Implementations
###############################################################################

def sendfile_fallback(sfile, channel, offset, nbytes, fallback):
    """
    Fallback implementation of ``sendfile()``.

    This is not a true implementation of the ``sendfile()`` system call,
    but rather a fallback option written in Python. It has the same
    ultimate effect, but is far slower than a native implementation.
    This function is only used as a last resort.

    =========  ============
    Argument   Description
    =========  ============
    sfile      The file to send.
    channel    The channel to write to.
    offset     The number of bytes to offset writing by.
    nbytes     The number of bytes of the file to write. If 0, all bytes will be written.
    fallback   If True, the pure-Python sendfile function will be used.
    =========  ============
    """
    # TODO Implement a better solution for the "send all bytes" argument.
    if nbytes == 0:
        to_read = SENDFILE_AMOUNT
    else:
        to_read = min(nbytes, SENDFILE_AMOUNT)

    sfile.seek(offset)
    data = sfile.read(to_read)

    if len(data) == 0:
        return 0

    return channel._socket_send(data)

def sendfile_linux(sfile, channel, offset, nbytes, fallback):
    """
    Linux 2.x implementation of ``sendfile()``.

    =========  ============
    Argument   Description
    =========  ============
    sfile      The file to send.
    channel    The channel to write to.
    offset     The number of bytes to offset writing by.
    nbytes     The number of bytes of the file to write. If 0, all bytes will be written.
    fallback   If True, the pure-Python sendfile function will be used.
    =========  ============
    """
    if fallback:
        return sendfile_fallback(sfile, channel, offset, nbytes, fallback)

    # TODO Linux doesn't support an argument of 0 for nbytes. Implement
    #      a better solution.
    if nbytes == 0:
        nbytes = SENDFILE_AMOUNT

    _offset = ctypes.c_uint64(offset)

    result = _sendfile(channel.fileno, sfile.fileno(), _offset, nbytes)

    if result == -1:
        e = ctypes.get_errno()
        err =  socket.error(e, os.strerror(e))
        err.nbytes = 0 # See issue #43
        raise err

    return result

def sendfile_darwin(sfile, channel, offset, nbytes, fallback):
    """
    Darwin implementation of ``sendfile()``.

    =========  ============
    Argument   Description
    =========  ============
    sfile      The file to send.
    channel    The channel to write to.
    offset     The number of bytes to offset writing by.
    nbytes     The number of bytes of the file to write. If 0, all bytes will be written.
    fallback   If True, the pure-Python sendfile function will be used.
    =========  ============
    """
    if fallback:
        return sendfile_fallback(sfile, channel, offset, nbytes, fallback)

    _nbytes = ctypes.c_uint64(nbytes)

    result = _sendfile(sfile.fileno(), channel.fileno, offset, _nbytes,
                       None, 0)

    if result == -1:
        e = ctypes.get_errno()
        err = socket.error(e, os.strerror(e))
        err.nbytes = _nbytes.value # See issue #43
        raise err

    return _nbytes.value

def sendfile_bsd(sfile, channel, offset, nbytes, fallback):
    """
    FreeBSD/Dragonfly implementation of ``sendfile()``.

    =========  ============
    Argument   Description
    =========  ============
    sfile      The file to send.
    channel    The channel to write to.
    offset     The number of bytes to offset writing by.
    nbytes     The number of bytes of the file to write. If 0, all bytes will be written.
    fallback   If True, the pure-Python sendfile function will be used.
    =========  ============
    """
    if fallback:
        return sendfile_fallback(sfile, channel, offset, nbytes, fallback)

    _nbytes = ctypes.c_uint64()

    result = _sendfile(sfile.fileno(), channel.fileno, offset, nbytes,
                       None, _nbytes, 0)

    if result == -1:
        e = ctypes.get_errno()
        err = socket.error(e, os.strerror(e))
        err.nbytes = _nbytes.value # See issue #43
        raise err

    return _nbytes.value


###############################################################################
# Sendfile
###############################################################################

_sendfile = None
if sys.version_info >= (2, 6) and sys.platform in SENDFILE_PLATFORMS:
    _libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    if hasattr(_libc, "sendfile"):
        _sendfile = _libc.sendfile

sendfile = None
if _sendfile is None:
    sendfile = sendfile_fallback

elif sys.platform == "linux2":
    _sendfile.argtypes = (
            ctypes.c_int,  # socket
            ctypes.c_int,  # file
            ctypes.POINTER(ctypes.c_uint64), #  offset
            ctypes.c_size_t  # len
            )

    sendfile = sendfile_linux

elif sys.platform == "darwin":
    _sendfile.argtypes = (
            ctypes.c_int,  # file
            ctypes.c_int,  # socket
            ctypes.c_uint64, # offset
            ctypes.POINTER(ctypes.c_uint64),  # len
            ctypes.c_voidp,  # header/trailer
            ctypes.c_int  # flags
            )

    sendfile = sendfile_darwin

elif sys.platform in ("freebsd", "dragonfly"):
    _sendfile.argtypes = (
            ctypes.c_int,  # file
            ctypes.c_int,  # socket
            ctypes.c_uint64,  # offset
            ctypes.c_uint64,  # len
            ctypes.c_voidp,  # header/trailer
            ctypes.POINTER(ctypes.c_uint64),  # bytes sent
            ctypes.c_int  # flags
            )

    sendfile = sendfile_bsd

########NEW FILE########
__FILENAME__ = application
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
``pants.web.application`` implements a minimalistic framework for building
websites on top of Pants.

The :class:`~pants.web.application.Application` class features a powerful,
easy to use request routing system and an API similar to that of the popular
`Flask <http://flask.pocoo.org/>`_ project.

.. note::

    Application does not provide out of the box support for sessions or
    templates, and it is not compatible with WSGI middleware as it is not
    implemented via WSGI.


Applications
============

Instances of the :class:`Application` class are callable and act as request
handlers for the :class:`pants.http.server.HTTPServer` class. As such, to
implement a server you just have to create an
:class:`~pants.http.server.HTTPServer` instance using your application.

.. code-block:: python

    from pants.http import HTTPServer
    from pants.web import Application

    app = Application()

    HTTPServer(app).listen(8080)

Alternatively, you may call the Application's :func:`~Application.run` method,
which creates an instance of HTTPServer for you and starts Pants' global
:mod:`~pants.engine`.

The main features of an Application are its powerful request routing table and
its output handling.

.. _app-routing:

Routing
=======

When registering new request handlers with an :class:`Application` instance,
you are required to provide a specially formatted rule. These rules allow you
to capture variables from URLs on top of merely routing requests, making it
easy to create attractive URLs bereft of unfriendly query strings.

Rules in their simplest form will match a static string.

.. code-block:: python

    @app.route("/")
    def index(request):
        return "Index Page"

    @app.route("/welcome")
    def welcome(request):
        return "Hello, Programmer!"

Such an Application would have two pages, and not be exceptionally useful by
any definition. Adding a simple variable makes things much more interesting.

.. code-block:: python

    @app.route("/welcome/<name>")
    def welcome(request, name):
        return "Hello, %s!" % name

Variables are created using inequality signs, as demonstrated above, and allow
you to capture data directly from a URL. By default, a variable accepts any
character except a slash (``/``) and returns the entire captured string as an
argument to your request handler.

It is possible to change this behavior by naming a :class:`Converter` within
the variable definition using the format ``<converter:name>`` where
``converter`` is the name of the converter to use. It is not case-sensitive.
For example, the ``int`` converter:

.. code-block:: python

    @app.route("/user/<int:id>")
    def user(request, id):
        return session.query(User).filter_by(id=id).first().username

In the above example, the ``id`` is automatically converted to an integer by
the framework. The converter also serves to limit the URLs that will match a
rule. Variables using the ``int`` converter will only match numbers.

Finally, you may provide default values for variables:

.. code-block:: python

    @app.route("/page/<path:slug=welcome>")

Default values are used if there is no string to capture for the variable in
question, and are processed via the converter's :meth:`~Converter.decode`
method each time the rule is matched.

When using default values, they allow you to omit the entirety of the URL
following the point at which they are used. As such, if you have a rule such
as ``/page/<int:id=2>/other``, the URL ``/page/`` will match it.


Domains
-------

The route rule strings are very similar to those used by the popular Flask
framework. However, in addition to that behavior, the Application allows you
to match and extract variables from the domain the page was requested from.

.. code-block:: python

    @app.route("<username>.my-site.com/blog/<int:year>/<slug>")

To use domains, simply place the domain before the first slash in the
route rule.


Rule Variable Converters
========================

Converters are all subclasses of :class:`Converter` that have been registered
with Pants using the :func:`register_converter` decorator.

A Converter has three uses:

1. Generating a regular expression snippet that will match only valid input for
   the variable in question.
2. Processing the captured string into useful data for the Application.
3. Encoding values into URL-friendly strings for inclusion into URLs generated
   via the :func:`url_for` method.

Converters can accept configuration information from rules using a basic
format.

.. code-block:: python

    @app.route("/page/<regex('(\d{3}-\d{4})'):number>")

    @app.route("/user/<id(digits=4 min=200):id>")

Configuration must be provided within parenthesis, with separate values
separated by simple spaces. Strings may be enclosed within quotation marks if
they need to contain spaces.

The values ``true``, ``false``, and ``none`` are converted to the appropriate
Python values before being passed to the Converter's configuration method and it
also attempts to convert values into integers or floats if possible. Use
quotation marks to avoid this behavior if required.

Arguments may be passed by order or by key, and are passed to the Converter's
:func:`~Converter.configure` method from the constructor
via: ``self.configure(*args, **kwargs)``

Several basic converters have been included by default to make things easier.

Any
---

The ``any`` converter will allow you to match one string from a list of possible
strings.

.. code-block:: python

    @app.route("/<any(call text im):action>/<int:id>")

Using the above rule, you can match URLs starting with ``/call/``, ``/text/``,
or ``/im/`` (and followed, of course, by an integer named id).


DomainPart
----------

DomainPart is a special converter used when matching sections of a domain name
that will not match a period (``.``) but that otherwise works identically to the
default String converter.

You do not have to specify the DomainPart converter. It will be used
automatically in place of String for any variable capture within the domain name
portion of the rule.


Float
-----

The ``float`` converter will match a negation, the digits 0 through 9, and a
single period. It automatically converts the captured string into a
floating point number.

=========  ========  ============
Argument   Default   Description
=========  ========  ============
min        None      The minimum value to allow.
max        None      The maximum value to allow.
=========  ========  ============

Values outside of the range defined by ``min`` and ``max`` will result in an
error and *not* merely the rule not matching the URL.


Integer
-------

The ``int`` (or ``integer``) converter will match a negation and the digits
0 through 9, automatically converting the captured string into an integer.

=========  ========  ============
Argument   Default   Description
=========  ========  ============
digits     None      The exact number of digits to match with this variable.
min        None      The minimum value to allow.
max        None      The maximum value to allow.
=========  ========  ============

As with the Float converter, values outside of the range defined by ``min`` and
``max`` will result in an error and *not* merely the rule not matching the URL.


Path
----

The ``path`` converter will match any character at all and merely returns the
captured string. This is useful as a catch all for placing on the end of URLs.


Regex
-----

The ``regex`` converter allows you to specify an arbitrary regular expression
snippet for inclusion into the rule's final expression.

=========  ========  ============
Argument   Default   Description
=========  ========  ============
match                A regular expression snippet for inclusion into the rule's final expression.
namegen    None      The string format to use when building a URL for this variable with :func:`~pants.web.application.url_for`.
=========  ========  ============

.. code-block:: python

    @app.route("/call/<regex('(\d{3}-\d{4})'):number>")

The above variable would match strings such as ``555-1234``.


String
------

The ``string`` converter is the default converter used when none is specified,
and it matches any character except for a slash (``/``), allowing it to easily
capture individual URL segments.

=========  ========  ============
Argument   Default   Description
=========  ========  ============
min        None      The minimum length of the string to capture.
max        None      The maximum length of the string to capture.
length     None      An easy way to set both ``min`` and ``max`` at once.
=========  ========  ============

.. note::

    Setting ``length`` overrides any value of ``min`` and ``max``.


Writing a Variable Converter
============================

To create your own variable converters, you must create subclasses of
:class:`Converter` and register it with Pants using the
decorator :func:`register_converter`.

The simplest way to use converters is as a way to store common regular
expressions that you use to match segments of a URL. If, for example, you need
to match basic phone numbers, you could use:

.. code-block:: python

    @app.route("/tel/<regex('(\d{3})-(\d{4})'):number>")

Placing the expression in the route isn't clean, however, and it can be a pain
to update--particularly if you use the same expression across many different
routes.

A better alternative is to use a custom converter:

.. code-block:: python

    from pants.web import Converter, register_converter

    @register_converter
    class Telephone(Converter):
        regex = r"(\d{3})-(\d{4})"

After doing that, your rule becomes as easy as ``/tel/<telephone:number>``. Of
course, you could stop there, and deal with the resulting tuple of two strings
within your request handler.

However, the main goal of converters is to *convert* your data. Let's store our
phone number in a :class:`collections.namedtuple`. While we're at it, we'll
switch to a slightly more complex regular expression that can capture area codes
and extensions as well.

.. code-block:: python

    from collections import namedtuple
    from pants.web import Converter, register_converter

    PhoneNumber = namedtuple('PhoneNumber', ['npa','nxx','subscriber', 'ext'])

    @register_converter
    class Telephone(Converter):
        regex = r"(?:1[ -]*)?(?:\(? *([2-9][0-9]{2}) *\)?[ -]*)?([2-9](?:1[02-9]|[02-9][0-9]))[ -]*(\d{4})(?:[ -]*e?xt?[ -]*(\d+))?"

        def decode(self, request, *values):
            return PhoneNumber(*(int(x) if x else None for x in values))

Now we're getting somewhere. Using our existing rule, now we can make a request
for the URL ``/tel/555-234-5678x115`` and our request handler will receive the
variable ``PhoneNumber(npa=555, nxx=234, subscriber=5678, ext=115)``.

Lastly, we need a way to convert our nice ``PhoneNumber`` instances into
something we can place in a URL, for use with the :func:`url_for` function:

.. code-block:: python

    @register_converter
    class Telephone(Converter):

        ...

        def encode(self, request, value):
            out = '%03d-%03d-%04d' % (value.npa, value.nxx, value.subscriber)
            if value.ext:
                out += '-ext%d' % value.ext
            return out

Now, we can use ``url_for('route', PhoneNumber(npa=555, nxx=234, subscriber=5678, ext=115))``
and get a nice and readable ``/tel/555-234-5678-ext115`` back (assuming the rule
for ``route`` is ``/tel/<telephone:number>``).


Output Handling
===============

Sending output from a request handler is as easy as returning a value from the
function. Strings work well:

.. code-block:: python

    @app.route("/")
    def index(request):
        return "Hello, World!"

The example above would result in a ``200 OK`` response with the headers
``Content-Type: text/plain`` and ``Content-Length: 13``.


Response Body
-------------

If the returned string begins with ``<!DOCTYPE`` or ``<html`` it will be
assumed that the ``Content-Type`` should be ``text/html`` if a content type is
not provided.

If a unicode string is returned, rather than a byte string, it will be encoded
automatically using the encoding specified in the ``Content-Type`` header. If
that header is missing, or does not contain an encoding, the document will be
encoded in ``UTF-8`` by default and the content type header will be updated.

Dictionaries, lists, and tuples will be automatically converted into
`JSON <http://en.wikipedia.org/wiki/JSON>`_ and the ``Content-Type`` header
will be set to ``application/json``, making it easy to send JSON to clients.

If any other object is returned, the Application will attempt to cast it into
a byte string using ``str(object)``. To provide custom behavior, an object may
be given a ``to_html`` method, which will be called rather than ``str()``. If
``to_html`` is used, the ``Content-Type`` will be assumed to be ``text/html``.


Status and Headers
------------------

Of course, in any web application it is useful to be able to return custom
status codes and HTTP headers. To do so from an Application's request handlers,
simply return a tuple of ``(body, status)`` or ``(body, status, headers)``.

If provided, ``status`` must be an integer or a byte string. All valid HTTP
response codes may be sent simply by using their numbers.

If provided, ``headers`` must be either a dictionary, or a list of tuples
containing key/value pairs (``[(heading, value), ...]``).

You may also use an instance of :class:`pants.web.application.Response` rather
than a simple body or tuple.

The following example returns a page with the status code ``404 Not Found``:

.. code-block:: python

    @app.route("/nowhere/")
    def nowhere(request):
        return "This does not exist.", 404


"""

###############################################################################
# Imports
###############################################################################

import re
import traceback
import urllib

from datetime import datetime

from pants.http.server import HTTPServer
from pants.http.utils import HTTP, HTTPHeaders

from pants.web.utils import decode, ERROR_PAGE, HAIKUS, HTTP_MESSAGES, \
    HTTPException, HTTPTransparentRedirect, log, NO_BODY_CODES, CONSOLE_JS

try:
    import simplejson as json
except ImportError:
    import json


###############################################################################
# Constants
###############################################################################

__all__ = (
    "Converter", "register_converter",  # Converter Functions
    "Response", "Module", "Application", "HTTPServer",  # Core Classes

    "abort", "all_or_404", "error", "redirect", "url_for"  # Helper Functions
)

RULE_PARSER = re.compile(r"<(?:([a-zA-Z_][a-zA-Z0-9_]+)(?:\(((?:\"[^\"]+\"|[^:>)]*)+)\))?:)?([a-zA-Z_][a-zA-Z0-9_]+)(?:=([^>]*))?>([^<]*)")
OPTIONS_PARSER = re.compile(r"""(?:(\w+)=)?(None|True|False|\d+\.\d+|\d+\.|\d+|"[^"]*?"|'[^']*?'|\w+)""", re.IGNORECASE)

# Unique object for URL building.
NoValue = object()


###############################################################################
# JSONEncoder Class
###############################################################################

class JSONEncoder(json.JSONEncoder):
    """
    This subclass of JSONEncoder adds support for serializing datetime objects.
    """
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


###############################################################################
# Context Manager
###############################################################################

class RequestContext(object):
    __slots__ = ('application', 'request', 'stack')

    def __init__(self, application=None, request=None):
        self.application = application or Application.current_app
        self.request = request or self.application.request
        self.stack = []

    def __enter__(self):
        self.stack.append((Application.current_app, self.application.request))

        Application.current_app = ca = self.application
        ca.request = self.request

        return ca

    def __exit__(self, exc_type, exc_val, exc_tb):
        Application.current_app, self.application.request = self.stack.pop()


###############################################################################
# Converter Class
###############################################################################

class Converter(object):
    """
    The Converter class is the base class for all the different value
    converters usable in routing rules.
    """

    regex = "([^/]+)"

    def __init__(self, options, default):
        # Handle the options.
        self.default = default
        args, kwargs = [], {}
        if options:
            for key, val in OPTIONS_PARSER.findall(options):
                if val.lower() == 'none':
                    val = None
                elif val.lower() == 'true':
                    val = True
                elif val.lower() == 'false':
                    val = False
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass

                if isinstance(val, basestring):
                    val = val
                    if (val[0] == '"' and val[-1] == '"') or \
                            (val[0] == "'" and val[-1] == "'"):
                        val = val[1:-1]

                if key:
                    kwargs[key] = val
                else:
                    args.append(val)

        # Now, configure it with those settings.
        #noinspection PyArgumentList
        self.configure(*args, **kwargs)

        # Count our capture groups.
        self._regex = re.compile("^%s$" % self.regex)
        self.capture_groups = self._regex.groups

    def __repr__(self):
        out = ""
        if self.default:
            out += " default=" + repr(self.default)
        if hasattr(self, 'regex'):
            out += ' regex=' + repr(self.regex)
        return "<Converter[%s]%s>" % (self.__class__.__name__, out)

    def __call__(self, request, *values):
        if not any(values):
            m = self._regex.match(self.default)
            if not m:
                raise HttpException('Invalid default value for converter: %s', self.default)
            values = m.groups()
        return self.decode(request, *values)

    def configure(self):
        """
        The method receives configuration data parsed from the rule creating
        this Converter instance as positional and keyword arguments.

        You must build a regular expression for matching acceptable input within
        this function, and save it as the instance's ``regex`` attribute. You
        may use more than one capture group.
        """
        pass

    def decode(self, request, *values):
        """
        This method receives captured strings from URLs and must process the
        strings and return variables usable within request handlers.

        If the converter's regular expression has multiple capture groups, it
        will receive multiple arguments.

        .. note::

            Use :func:`abort` or raise an :class:`HTTPException` from this
            method if you wish to display an error page. Any other uncaught
            exceptions will result in a ``400 Bad Request`` page.

        """
        return values[0] if len(values) == 1 else values

    def encode(self, request, value):
        """
        This method encodes a value into a URL-friendly string for inclusion
        into URLs generated with :func:`url_for`.
        """
        return str(value)


###############################################################################
# Built-In Converters
###############################################################################

CONVERTER_TYPES = {}

def register_converter(name=None, klass=None):
    """
    Register a converter with the given name. If a name is not provided, the
    class name will be converted to lowercase and used instead.
    """
    try:
        if issubclass(name, Converter):
            name, klass = None, name
    except TypeError:
        pass

    def decorator(klass):
        _name = name if name else klass.__name__.lower()
        CONVERTER_TYPES[_name] = klass
        return klass

    if klass:
        return decorator(klass)
    return decorator


@register_converter
class Regex(Converter):
    def configure(self, match, namegen=None):
        self.regex = match
        if namegen is not None:
            self.namegen = namegen

    def encode(self, request, value):
        if hasattr(self, 'namegen'):
            return namegen.format(value)
        return str(value)


@register_converter
class Any(Converter):
    def configure(self, *choices):
        self.regex = "(%s)" % '|'.join(re.escape(x) for x in choices)

        if self.default is not None:
            dl = self.default.lower()
            for choice in choices:
                if choice.lower() == dl:
                    self.default = choice
                    break
            else:
                raise ValueError("Default value %r is not a valid "
                                 "choice." % self.default)


@register_converter
class DomainPart(Converter):
    def configure(self, min=None, max=None, length=None):
        if length is not None:
            min, max = length, length

        if min is None and max is None:
            self.regex = "([^/.]+)"
        elif min == max:
            self.regex = "([^/.]{%d})" % min
        elif max is None:
            self.regex = "([^/.]{%d,})" % min
        else:
            self.regex = "([^/.]{%d,%d})" % (min, max)


@register_converter
class Float(Converter):
    def configure(self, min=None, max=None):
        # Depending on the value of min, allow it to match a negation.
        if min is None or min < 0:
            self.regex = "(-?\d+(?:\.\d+)?)"
        else:
            self.regex = "(\d+(?:\.\d+)?)"

        self.min = min
        self.max = max

    def decode(self, request, value):
        value = float(value)
        if (self.min is not None and value < self.min) or\
           (self.max is not None and value > self.max):
            raise ValueError("Value %d is out of range." % value)
        return value


@register_converter('int')
@register_converter
class Integer(Converter):
    def configure(self, digits=None, min=None, max=None):
        # Build the correct regex for the length.
        minus = "-?" if min is None or min < 0 else ""
        if digits:
            self.regex = "(%s\d{%d})" % (minus, digits)
        else:
            self.regex = "(%s\d+)" % minus

        self.min = min
        self.max = max
        self.digits = digits

    def decode(self, request, value):
        value = int(value)
        if (self.min is not None and value < self.min) or\
           (self.max is not None and value > self.max):
            raise ValueError("Value %d is out of range." % value)
        return value

    def encode(self, request, value):
        if self.digits:
            minus = '-' if value < 0 else ''
            return ('%s%%0%dd' % (minus, self.digits)) % abs(value)

        else:
            return str(value)


@register_converter
class Path(Converter):
    regex = "(.+?)"


@register_converter
class String(Converter):
    def configure(self, min=None, max=None, length=None):
        if length is not None:
            min, max = length, length

        if min is None and max is None:
            self.regex = "([^/]+)"
        elif min == max:
            self.regex = "([^/]{%d})" % min
        elif max is None:
            self.regex = "([^/]{%d,})" % min
        else:
            self.regex = "([^/]{%d,%d})" % (min, max)


###############################################################################
# Response Class
###############################################################################

class Response(object):
    """
    The Response object is entirely optional, and provides a convenient way to
    glue the body, status code, and HTTP headers into one object to return from
    your routes.

    =========  ==================  ============
    Argument   Default             Description
    =========  ==================  ============
    body       ``None``            *Optional.* The response body to send back to the client.
    status     ``200``             *Optional.* The HTTP status code of the response.
    headers    ``HTTPHeaders()``   *Optional.* HTTP headers to send with the response.
    =========  ==================  ============
    """

    def __init__(self, body=None, status=None, headers=None):
        self.body = body or ""
        self.status = status or 200
        self.headers = headers or HTTPHeaders()

    def __repr__(self):
        return '<Response[%r] at 0x%08X>' % (self.status, id(self))


###############################################################################
# Module Class
###############################################################################

class Module(object):
    """
    A Module is, essentially, a group of rules for an Application. Rules grouped
    into a Module can be created without any access to the final Application
    instance, making it simple to split a website into multiple Python modules
    to be imported in the module that creates and runs the application.
    """

    def __init__(self, name=None):
        # Internal Stuff
        self._modules = {}
        self._routes = {}
        self._parents = set()

        # External Stuff
        self.name = name

        self.hooks = {
            'request_started': [],
            'request_finished': [],
            'request_teardown': []
            }

    def __repr__(self):
        return "<Module(%r) at 0x%08X>" % (self.name, id(self))

    ##### Module Connection ###################################################

    def add(self, rule, module):
        """
        Add a Module to this Module under the given rule. All rules within the
        sub-module will be accessible to this Module, with their rules prefixed
        by the rule provided here.

        For example::

            module_one = Module()

            @module_one.route("/fish")
            def fish(request):
                return "This is fish."

            module_two = Module()

            module_two.add("/pie", module_one)

        Given that code, the request handler ``fish`` would be available from
        the Module ``module_two`` with the rules ``/pie/fish``.
        """
        if isinstance(module, Application):
            raise TypeError("Applications cannot be added as modules.")

        # Register this module with the child module.
        module._parents.add(self)

        if not '/' in rule:
            rule = '/' + rule
        self._modules[rule] = module

        # Now, recalculate.
        self._recalculate_routes()

    def _recalculate_routes(self, processed=tuple()):
        if self in processed:
            raise RuntimeError("Cyclic inheritance: %s" %
                               ", ".join(repr(x) for x in processed))

        for parent in self._parents:
            parent._recalculate_routes(processed=processed + (self,))


    ##### Hook Decorators #####################################################

    def request_started(self, func):
        """
        Register a method to be executed immediately after a request has been
        successfully routed and before the request handler is executed.

        .. note::

            Hooks, including ``request_started``, are not executed if there is
            no matching rule to handle the request.

        This can be used for the initialization of sessions, a database
        connection, or other details. However, it is not always the best choice.
        If you wish to modify *all* requests, or manipulate the URL before
        routing occurs, you should wrap the Application in another method,
        rather than using a ``request_started`` hook. As an example of the
        difference:

        .. code-block:: python

            from pants.web import Application
            from pants.http import HTTPServer
            from pants import Engine

            from my_site import sessions, module

            app = Application()

            # The Hook
            @app.request_started
            def handle(request):
                logging.info('Request matched route: %s' % request.route_name)

            # The Wrapper
            def wrapper(request):
                request.session = sessions.get(request.get_secure_cookie('session_id'))
                app(request)

            # Add rules from another module.
            app.add('/', module)

            HTTPServer(wrapper).listen()
            Engine.instance().start()

        """
        self.hooks['request_started'].append(func)
        self._recalculate_routes()
        return func

    def request_finished(self, func):
        """
        Register a method to be executed immediately after the request handler
        and before the output is processed and send to the client.

        This can be used to transform the output of request handlers.

        .. note::

            These hooks are not run if there is no matching rule for a request,
            if there is an exception while running the request handler, or if
            the request is not set to have its output processed by the
            Application by setting ``request.auto_finish`` to ``False``.
        """
        self.hooks['request_finished'].append(func)
        self._recalculate_routes()
        return func

    def request_teardown(self, func):
        """
        Register a method to be executed after the output of a request handler
        has been processed and has begun being transmitted to the client. At
        this point, the request is not going to be used again and can be cleaned
        up.

        .. note::

            These hooks will always run if there was a matching rule, even if
            the request handler or other hooks have exceptions, to prevent any
            potential memory leaks from requests that aren't torn down properly.
        """
        self.hooks['request_teardown'].append(func)
        self._recalculate_routes()
        return func


    ##### Route Management Decorators #########################################

    def basic_route(self, rule, name=None, methods=('GET', 'HEAD'),
                    headers=None, content_type=None, func=None):
        """
        The basic_route decorator registers a route with the Module without
        holding your hand about it.

        It functions similarly to the :func:`Module.route` decorator, but it
        doesn't wrap the function with any argument processing code. Instead,
        the function is given only the request object, and through it access to
        the regular expression match.

        Example Usage::

            @app.basic_route("/char/<char>")
            def my_route(request):
                char, = request.match.groups()
                return "The character is %s!" % char

        That is essentially equivalent to::

            @app.route("/char/<char>")
            def my_route(request, char):
                return "The character is %s!" % char

        .. note::

            Output is still handled the way it is with a normal route, so you
            can return strings and dictionaries as usual.

        =============  ============
        Argument       Description
        =============  ============
        rule           The route rule to match for a request to go to the decorated function. See :func:`Module.route` for more information.
        name           *Optional.* The name of the decorated function, for use with the :func:`url_for` helper function.
        methods        *Optional.* A list of HTTP methods to allow for this request handler. By default, only ``GET`` and ``HEAD`` requests are allowed, and all others will result in a ``405 Method Not Allowed`` error.
        headers        *Optional.* A dictionary of HTTP headers to always send with the response from this request handler. Any headers set within the request handler will override these headers.
        content_type   *Optional.* The HTTP Content-Type header to send with the response from this request handler. A Content-Type header set within the request handler will override this.
        func           *Optional.* The function for this view. Specifying the function bypasses the usual decorator-like behavior of this function.
        =============  ============
        """
        if not '/' in rule:
            rule = '/' + rule

        def decorator(func):
            if not callable(func):
                raise ValueError("Request handler must be callable.")

            if name is None:
                if hasattr(func, "__name__"):
                    _name = func.__name__
                elif hasattr(func, "__class__"):
                    _name = func.__class__.__name__
                else:
                    raise ValueError("Cannot find name for rule. Please "
                                     "specify name manually.")
            else:
                _name = name

            # Get the rule table for this rule.
            rule_table = self._routes.setdefault(rule, {})
            if isinstance(rule_table, Module):
                raise ValueError("The rule %r is claimed by a Module." % rule)

            # Now, for each method, store the data.
            for method in methods:
                rule_table[method] = (func, _name, False, False, headers,
                                      content_type)

            # Recalculate routes and return.
            self._recalculate_routes()
            return func

        if func:
            return decorator(func)
        return decorator

    def route(self, rule, name=None, methods=('GET','HEAD'), auto404=False,
              headers=None, content_type=None, func=None):
        """
        The route decorator is used to register a new route with the Module
        instance. Example::

            @app.route("/")
            def hello_world(request):
                return "Hiya, Everyone!"

        .. seealso::

            See :ref:`app-routing` for more information on writing rules.

        =============  ============
        Argument       Description
        =============  ============
        rule           The route rule to be matched for the decorated function to be used for handling a request.
        name           *Optional.* The name of the decorated function, for use with the :func:`url_for` helper function.
        methods        *Optional.* A list of HTTP methods to allow for this request handler. By default, only ``GET`` and ``HEAD`` requests are allowed, and all others will result in a ``405 Method Not Allowed`` error.
        auto404        *Optional.* If this is set to True, all response handler arguments will be checked for truthiness (True, non-empty strings, etc.) and, if any fail, a ``404 Not Found`` page will be rendered automatically.
        headers        *Optional.* A dictionary of HTTP headers to always send with the response from this request handler. Any headers set within the request handler will override these headers.
        content_type   *Optional.* The HTTP Content-Type header to send with the response from this request handler. A Content-Type header set within the request handler will override this.
        func           *Optional.* The function for this view. Specifying the function bypasses the usual decorator-like behavior of this function.
        =============  ============
        """
        if not '/' in rule:
            rule = '/' + rule

        def decorator(func):
            if not callable(func):
                raise ValueError("Request handler must be callable.")

            if name is None:
                if hasattr(func, "__name__"):
                    _name = func.__name__
                elif hasattr(func, "__class__"):
                    _name = func.__class__.__name__
                else:
                    raise ValueError("Cannot find name for rule. Please "
                                     "specify name manually.")
            else:
                _name = name

            # Get the rule table for this rule.
            rule_table = self._routes.setdefault(rule, {})
            if isinstance(rule_table, Module):
                raise ValueError("The rule %r is claimed by a Module." % rule)

            # Now, for each method, store the data.
            for method in methods:
                rule_table[method] = (func, _name, True, auto404, headers, content_type)

            # Recalculate and return.
            self._recalculate_routes()
            return func

        if func:
            return decorator(func)
        return decorator


###############################################################################
# Application Class
###############################################################################

class Application(Module):
    """
    The Application class builds upon the :class:`Module` class and acts as a
    request handler for the :class:`~pants.http.server.HTTPServer`, with request
    routing, error handling, and a degree of convenience that makes sending
    output easier.

    Instances of Application are callable, and should be used as a HTTPServer's
    request handler.

    =========  ================================================================
    Argument   Description
    =========  ================================================================
    debug      *Optional.* If this is set to True, the automatically generated
               ``500 Internal Server Error`` pages will display additional
               debugging information.
    =========  ================================================================
    """
    current_app = None
    request = None

    def __init__(self, name=None, debug=False, fix_end_slash=False):
        super(Application, self).__init__(name)

        # Internal Stuff
        self._route_table = {}
        self._route_list = []
        self._name_table = {}

        # External Stuff
        self.json_encoder = JSONEncoder
        self.debug = debug
        self.fix_end_slash = fix_end_slash

    def run(self, address=None, ssl_options=None, engine=None):
        """
        This function exists for convenience, and when called creates a
        :class:`~pants.http.server.HTTPServer` instance with its request
        handler set to this application instance, calls
        :func:`~pants.http.server.HTTPServer.listen` on that HTTPServer, and
        finally, starts the Pants engine to process requests.

        ============  ============
        Argument      Description
        ============  ============
        address       *Optional.* The address to listen on. If this isn't specified, it will default to ``('', 80)``.
        ssl_options   *Optional.* A dictionary of SSL options for the server. See :meth:`pants.server.Server.startSSL` for more information.
        engine        *Optional.* The :class:`pants.engine.Engine` instance to use.
        ============  ============
        """
        if not engine:
            from pants.engine import Engine
            engine = Engine.instance()

        HTTPServer(self, ssl_options=ssl_options, engine=engine).listen(address)
        engine.start()

    ##### Error Handlers ######################################################

    def handle_404(self, request, err):
        if isinstance(err, HTTPException):
            return error(err.message, 404, request=request)
        return error(404, request=request)

    def handle_500(self, request, err):
        log.exception("Error handling HTTP request: %s %s" %
                      (request.method, request.url))
        if not self.debug:
            return error(500, request=request)

        # See if we can highlight the traceback.
        tb = getattr(request, '_tb', None) or traceback.format_exc()

        # Try to highlight the traceback.
        if hasattr(self, 'highlight_traceback'):
            try:
                tb = self.highlight_traceback(request, err, tb)
                if not u"<pre>" in tb:
                    tb = u"<pre>%s</pre>" % tb
            except Exception as err:
                log.exception("Error in highlight_traceback for %r." % self)
                tb = u"<pre>%s</pre>" % tb
        else:
            tb = u"<pre>%s</pre>" % tb

        response = u"\n".join([
            u"<h2>Traceback</h2>", tb,
            #u'<div id="console"><script type="text/javascript">%s</script></div>' % CONSOLE_JS,
            u"<h2>Route</h2>",
            u"<pre>route name   = %r" % getattr(request, "route_name", None),
            u"match groups = %r" % (request.match.groups() if request.match else None,),
            (u"match values = %r</pre>" % request._converted_match) if hasattr(request, '_converted_match') else u"</pre>",
            u"<h2>HTTP Request</h2>",
            request.__html__()
        ])

        return error(response, 500, request=request)

    ##### Routing Table Builder ###############################################

    def _recalculate_routes(self, processed=None, path=None, module=None,
                            nameprefix="", hooks=None):
        """
        This function does the heavy lifting of building the routing table, and
        it's called every time a route is updated. Fortunately, that generally
        only happens when the application is being created.
        """
        if path is None:
            # Initialize our storage variables.
            self._route_list = []
            self._route_table = {}
            self._name_table = {}

        # Get the unprocessed route table.
        routes = module._routes if module else self._routes
        modules = module._modules if module else self._modules
        mod_hooks = module.hooks if module else self.hooks

        # Update the name prefix.
        name = module.name if module else self.name
        if name:
            nameprefix = nameprefix + "." + name if nameprefix else name

        # Update the hooks system.
        if hooks:
            new_hooks = {}
            for k, v in hooks.iteritems():
                new_hooks[k] = v[:]
            hooks = new_hooks
        else:
            hooks = {}

        for k,v in mod_hooks.iteritems():
            if k in hooks:
                hooks[k].extend(v)
            else:
                hooks[k] = v[:]

        # Iterate through modules first, so our own rules are more important.
        for rule, mod in modules.iteritems():
            self._recalculate_routes(None, rule, mod, nameprefix, hooks)

        # Iterate through the unprocessed route table.
        for rule, table in routes.iteritems():
            # If path is set, and this isn't an absolute rule, merge the rule
            # with the path.
            if path and (rule[0] == "/" or not "/" in rule):
                if path[-1] == "/":
                    if rule[0] == "/":
                        rule = path + rule[1:]
                    else:
                        rule = path + rule
                else:
                    if rule[0] == "/":
                        rule = path + rule
                    else:
                        rule = path + "/" + rule

            # Parse the rule string.
            regex, converters, names, namegen, domain, rpath = \
                _rule_to_regex(rule)
            dkey, rkey = rule.split("/", 1)

            # Get the domain table.
            if not dkey in self._route_table:
                dt = self._route_table[dkey] = {}
                dl = dt[None] = [domain, dkey, []]
                self._route_list.append(dl)
            else:
                dt = self._route_table[dkey]
                dl = dt[None]

            # Determine if this is a new rule for the given domain.
            if not rkey in dt:
                rt = dt[rkey] = {}
                rl = rt[None] = [rpath, re.compile(regex), rkey, None, {},
                                 names, namegen, converters]
                dl[2].append(rl)
            else:
                rt = dt[rkey]
                rl = rt[None]

            # Get the method table
            method_table = rl[4]

            # Iterate through all the methods this rule provides.
            for method, (func, name, advanced, auto404, headers, content_type) \
                    in table.iteritems():
                method = method.upper()
                if method == 'GET' or rl[3] is None:
                    if nameprefix:
                        name = nameprefix + '.' + name
                    rl[3] = name
                if advanced:
                    for mthd in method_table:
                        if getattr(method_table[mthd], "wrapped_func", None) \
                                is func:
                            method_table[method] = method_table[mthd], \
                                                   headers, content_type
                            break
                    else:
                        method_table[method] = _get_runner(func, converters,
                                                            auto404), headers, \
                                                            content_type, hooks
                else:
                    method_table[method] = func, headers, content_type, hooks

            # Update the name table.
            self._name_table[rl[3]] = rl

        if path is None:
            # Sort everything.

            # Sort the domains first by the length of the domain key, in reverse
            # order; followed by the number of colons in the domain key, in
            # reverse order; and finally by the domain key alphabetically.
            self._route_list.sort(key=lambda x: (-len(x[1]), -(x[1].count(':')),
                                                 x[1]))

            # Sort the same way for each rule in each domain, but using the rule
            # key rather than the domain key.
            for domain, dkey, rl in self._route_list:
                rl.sort(key=lambda x: (-len(x[2]), -(x[2].count(':')), x[2]))

    ##### The Request Handler #################################################

    def __call__(self, request):
        """
        This function is called when a new request is received, and uses the
        method :meth:`Application.route_request` to select and execute the
        proper request handler, and then the method
        :meth:`Application.parse_output` to process the handler's output.
        """
        Application.current_app = self
        self.request = request

        try:
            request.auto_finish = True
            result = self.route_request(request)
            if request.auto_finish:
                self.parse_output(result)

        except Exception as err:
            # This should hopefully never happen, but it *could*.
            try:
                body, status, headers = self.handle_500(request, err)
            except Exception:
                # There's an error with our handle_500.
                log.exception("There was a problem handling a request, "
                              "and a problem running Application.handle_500 "
                              "for %r." % self)
                body, status, headers = error(500, request=request)

                # If an exception happens at *this* point, it's destined. Just
                # show the ugly page.

            if not 'Content-Length' in headers:
                headers['Content-Length'] = len(body)

            request.send_status(status)
            request.send_headers(headers)
            request.write(body)
            request.finish()

        finally:
            if hasattr(request, '_hooks'):
                hks = request._hooks.get('request_teardown')
                if hks:
                    for hf in hks:
                        try:
                            hf(request)
                        except Exception as err:
                            # Log the exception, but continue.
                            log.exception("There was a problem handling a "
                                          "request teardown hook for: %r",
                                            request)

            if hasattr(request, '_converted_match'):
                del request._converted_match

            Application.current_app = None
            self.request = None

    def route_request(self, request):
        """
        Determine which request handler to use for the given request, execute
        that handler, and return its output.
        """
        domain = request.hostname
        path = urllib.unquote_plus(request.path)
        matcher = domain + path
        method = request.method.upper()
        available_methods = set()

        request._rule_headers = None
        request._rule_content_type = None

        for dmn, dkey, rules in self._route_list:
            # Do basic domain matching.
            if ':' in dmn:
                if not request.host.lower().endswith(dmn):
                    continue
            elif not domain.endswith(dmn):
                continue

            # Iterate through the available rules, trying for a match.
            for rule, regex, rkey, name, method_table, names, namegen, \
                    converters in rules:
                if not path.startswith(rule):
                    continue
                match = regex.match(matcher)
                if match is None:
                    continue

                # We have a match. Check for a valid method.
                if not method in method_table:
                    available_methods.update(method_table.keys())
                    continue

                # It's a match. Run the method and return the result.
                request.route_name = name
                request.match = match

                try:
                    func, headers, content_type, hooks = method_table[method]
                    request._rule_headers = headers
                    request._rule_content_type = content_type
                    request._hooks = hooks

                    hks = hooks.get('request_started')
                    if hks:
                        for hf in hks:
                            hf(request)

                    output = func(request)

                    if request.auto_finish:
                        hks = hooks.get('request_finished')
                        if hks:
                            # Make sure the request_finished handler always gets
                            # an instance of Response. This way, it's always
                            # possible for it to be changed without taking
                            # return values.
                            if not isinstance(output, Response):
                                if isinstance(output, tuple):
                                    out = Response(*output)
                                else:
                                    out = Response(output)

                            for hf in hks:
                                hf(request, output)

                    return output

                except HTTPException as err:
                    request._rule_headers = None
                    request._rule_content_type = None

                    err_handler = getattr(self, "handle_%d" % err.status, None)
                    if err_handler:
                        return err_handler(request, err)
                    else:
                        return error(err.message, err.status, err.headers,
                                     request=request)
                except HTTPTransparentRedirect as err:
                    request._rule_headers = None
                    request._rule_content_type = None

                    request.url = err.url
                    request._parse_url()
                    return self.route_request(request)
                except Exception as err:
                    request._rule_headers = None
                    request._rule_content_type = None

                    return self.handle_500(request, err)

        if available_methods:
            if request.method == 'OPTIONS':
                return '', 200, {'Allow': ', '.join(available_methods)}
            else:
                return error(
                    "The method %s is not allowed for %r." % (method, path),
                    405, {'Allow': ', '.join(available_methods)}
                )

        elif self.fix_end_slash:
            # If there are no matching routes, and the path doesn't end with a
            # slash, try adding the slash.
            if not path[-1] == "/":
                path += "/"
                matcher += "/"
                for dmn, dkey, rules in self._route_list:
                    if ':' in dmn:
                        if not request.host.lower().endswith(dmn):
                            continue
                    elif not domain.endswith(dmn):
                        continue

                    for rule, regex, rkey, name, method_table, names, namegen, \
                            converters in rules:
                        if not path.startswith(rule):
                            continue
                        if regex.match(matcher):
                            if request.query:
                                return redirect("%s?%s" %
                                                (path, request.query))
                            else:
                                return redirect(path)

        return self.handle_404(request, None)

    def parse_output(self, result):
        """ Process the output of :meth:`Application.route_request`. """
        request = self.request

        if not request.auto_finish or request._finish is not None:
            return

        status = None

        if isinstance(result, Response):
            body = result.body
            status = result.status
            headers = result.headers

        elif isinstance(result, tuple):
            if len(result) == 3:
                body, status, headers = result
            else:
                body, status = result
                headers = HTTPHeaders()
                
        else:
            body = result
            headers = HTTPHeaders()

        # If we don't have a body, use a 204.
        if status is None:
            if body is None:
                status = 204
            else:
                status = 200

        # Use the rule headers stuff.
        if request._rule_headers:
            if isinstance(request._rule_headers, HTTPHeaders):
                rule_headers = request._rule_headers.copy()
            else:
                rule_headers = HTTPHeaders(request._rule_headers)

            if isinstance(headers, HTTPHeaders):
                rule_headers._data.update(headers._data)
            else:
                rule_headers.update(headers)

            headers = rule_headers

        # Determine if we're sending a body.
        send_body = request.method.upper() != 'HEAD' and status not in NO_BODY_CODES

        # Convert the body to something that we can send.
        if send_body:
            # Use the rule content-type.
            if request._rule_content_type and not 'Content-Type' in headers:
                headers['Content-Type'] = request._rule_content_type

            try:
                body = body.to_html()
                if not 'Content-Type' in headers:
                    headers['Content-Type'] = 'text/html'
            except AttributeError:
                pass

            # Set a Content-Type header if there isn't one already.
            if not 'Content-Type' in headers:
                if isinstance(body, basestring) and body[:5].lower() in \
                        ('<html', '<!doc'):
                    headers['Content-Type'] = 'text/html'
                elif isinstance(body, (tuple, list, dict)):
                    headers['Content-Type'] = 'application/json'
                else:
                    headers['Content-Type'] = 'text/plain'

            if isinstance(body, unicode):
                encoding = headers['Content-Type']
                if 'charset=' in encoding:
                    before, sep, enc = encoding.partition('charset=')
                else:
                    before = encoding
                    sep = '; charset='
                    enc = 'UTF-8'

                body = body.encode(enc)
                headers['Content-Type'] = before + sep + enc

            elif isinstance(body, (tuple, list, dict)):
                try:
                    body = json.dumps(body, cls=self.json_encoder)
                except Exception as err:
                    body, status, headers = self.handle_500(request, err)
                    body = body.encode('utf-8')
                    headers['Content-Type'] = 'text/html; charset=UTF-8'

            elif body is None:
                body = ''

            elif not isinstance(body, str):
                body = str(body)

            # More headers!
            if not 'Content-Length' in headers:
                headers['Content-Length'] = len(body)

        else:
            # We're not allowed to send the body, so strip out any headers about
            # the content of the body.
            if 'Content-Length' in headers:
                del headers['Content-Length']

            if 'Content-Type' in headers:
                del headers['Content-Type']

            if 'Transfer-Encoding' in headers:
                del headers['Transfer-Encoding']

        # Send the response.
        request.send_status(status)
        request.send_headers(headers)

        if send_body:
            request.write(body)

        request.finish()


###############################################################################
# Private Helper Functions
###############################################################################

def _get_runner(func, converters, auto404):
    def view_runner(request):
        request.__func_module = func.__module__
        match = request.match

        if not converters:
            return func(request)

        try:
            # We have to get a bit fancy here, since a single converter can take
            # multiple values.
            i = 0
            out = []
            values = match.groups()

            for converter in converters:
                groups = converter.capture_groups
                out.append(converter(request, *values[i:i+groups]))
                i += groups

            request._converted_match = out

        except HTTPException as err:
            raise err
        except Exception as err:
            raise HTTPException(400, str(err))

        if auto404:
            all_or_404(*out)

        return func(request, *out)

    view_runner.wrapped_func = func
    return view_runner


def _rule_to_regex(rule):
    """
    Parse a rule and return a regular expression, as well as converters for
    value conversion and default values.
    """
    regex, converters, names, namegen, domain, path = "", [], [], "", "", ""

    # Make sure we have at least one /.
    if not '/' in rule:
        rule = '/' + rule

    in_domain = True

    # Handle the beginning of the string.
    if rule[0] == '.':
        regex += '[^./]+?'
    elif rule[0] == '/':
        regex += '[^/]+?'

    # Find the first <.
    ind = rule.find("<")
    if ind == -1 or RULE_PARSER.match(rule[ind:]) is None:
        if '/' in rule:
            domain, _, path = rule.partition('/')
            path = '/' + path
            regex += re.escape(domain) + "(?::\d+)?" + re.escape(path) + "$"
        else:
            regex += re.escape(rule) + "$"

        # There are no variables to match. Tough luck.
        return "^" + regex, tuple(), tuple(), rule, domain, path
    elif ind > 0:
        text = rule[:ind]
        rule = rule[ind:]

        if '/' in text:
            in_domain = False
            domain, _, path = text.partition('/')
            path = '/' + path
            regex += re.escape(domain) + "(?::\d+)?" + re.escape(path)
        else:
            regex += re.escape(text)
        namegen += text

    has_default = 0

    # Iterate through the matches.
    for match in RULE_PARSER.finditer(rule):
        converter, options, name, default, text = match.groups()
        names.append(name)

        if default is not None:
            has_default += 1
            if not in_domain:
                regex += "(?:"

        # If we're still in the domain, use a special converter that doesn't
        # match the period.
        if converter:
            converter = converter.lower()

        if converter == 'str':
            converter = 'string'
        if in_domain and (not converter or converter == 'string'):
            converter = 'domainpart'
        elif not in_domain and (not converter or converter == 'domainpart'):
            converter = 'string'

        converter = converter.strip()
        if not converter in CONVERTER_TYPES:
            raise ValueError("No such converter %r." % converter)

        # Make the converter.
        converter = CONVERTER_TYPES[converter](options, default)
        converters.append(converter)

        regex += converter.regex
        namegen += '%s' + text

        if in_domain and '/' in text:
            in_domain = False
            domain, _, path = text.partition('/')
            path = '/' + path
            regex += re.escape(domain) + "(?::\d+)?" + re.escape(path)

            if default:
                regex += ")?"

            while has_default > 0:
                regex = "(?:" + regex
                has_default -= 1
        else:
            regex += re.escape(text)
            if default and in_domain:
                regex += ")?"

    while has_default > 0:
        regex += ")?"
        has_default -= 1

    return "^" + regex + "$", tuple(converters), tuple(names), \
           namegen, domain, path


###############################################################################
# Public Helper Functions
###############################################################################

def abort(status=404, message=None, headers=None):
    """
    Raise a :class:`~pants.contrib.web.HTTPException` to display an error page.
    """
    raise HTTPException(status, message, headers)


def all_or_404(*args):
    """
    If any of the provided arguments aren't truthy, raise a ``404 Not Found``
    exception. This is automatically called for you if you set ``auto404=True``
    when using the route decorator.
    """
    all(args) or abort()


def error(message=None, status=None, headers=None, request=None, debug=None):
    """
    Return a very simple error page, defaulting to a ``404 Not Found`` error if
    no status code is supplied. Usually, you'll want to call :func:`abort` in
    your code, rather than error(). Usage::

        return error(404)
        return error("Some message.", 404)
        return error("Blah blah blah.", 403, {'Some-Header': 'Fish'})
    """
    if request is None:
        request = Application.current_app.request

    if status is None:
        if isinstance(message, (int, long)):
            status, message = message, None
        else:
            status = 404

    status_text = None
    if isinstance(status, basestring):
        status, _, status_text = status.partition(' ')
        status = int(status)
    if not status_text:
        status_text = HTTP.get(status, "Unknown Error")

    if not headers:
        headers = {}

    if message is None:
        message = HTTP_MESSAGES.get(status, u"An unknown error has occurred.")
        values = request.__dict__.copy()
        values['url'] = decode(urllib.unquote(values['url']))
        message = message.format(**values)

    if status in HAIKUS:
        haiku = u'<div class="haiku">%s</div>' % HAIKUS[status]
    else:
        haiku = u""

    if not message[0] == u"<":
        message = u"<p>%s</p>" % message

    if debug is None:
        debug = Application.current_app and Application.current_app.debug

    if debug:
        debug = u"%0.3f ms" % (1000 * request.time)
    else:
        debug = u""

    result = ERROR_PAGE.safe_substitute(
        status=status,
        status_text=status_text,
        status_text_nbsp=status_text.replace(u" ", u"&nbsp;"),
        haiku=haiku,
        content=message,
        scheme=request.scheme,
        host=request.host,
        debug=debug
    )

    return result, status, headers


def redirect(url, status=302, request=None):
    """
    Construct a ``302 Found`` response to instruct the client's browser to
    redirect its request to a different URL. Other codes may be returned by
    specifying a status.

    =========  ========  ============
    Argument   Default   Description
    =========  ========  ============
    url                  The URL to redirect the client's browser to.
    status     ``302``   *Optional.* The status code to send with the response.
    =========  ========  ============
    """
    if isinstance(url, unicode):
        url = url.encode('utf-8')

    return error(
        'The document you have requested is located at <a href="%s">%s</a>.' % (
            url, url), status, {'Location': url}, request=request)

def url_for(name, *values, **kw_values):
    """
    Generates a URL for the route with the given name. You may give either an
    absolute name for the route or use a period to match names relative to the
    current route. Multiple periods may be used to traverse up the name tree.

    Passed arguments will be used to construct the URL. Any unknown keyword
    arguments will be appended to the URL as query arguments. Additionally,
    there are several special keyword arguments to customize
    ``url_for``'s behavior.

    ==========  ========  ============
    Argument    Default   Description
    ==========  ========  ============
    _anchor     None      *Optional.* An anchor string to be appended to the URL.
    _doseq      True      *Optional.* The value to pass to :func:`urllib.urlencode`'s ``doseq`` parameter for building the query string.
    _external   False     *Optional.* Whether or not a URL is meant for external use. External URLs never have their host portion removed.
    _scheme     None      *Optional.* The scheme of the link to generate. By default, this is set to the scheme of the current request.
    ==========  ========  ============
    """

    if '_request' in kw_values:
        request = kw_values.pop('_request')
    else:
        app = Application.current_app
        if not app or not app.request:
            raise RuntimeError("Called url_for outside of a request.")
        request = app.request

    # Handle periods, which are for moving up the module table.
    if name[0] == '.':
        # Count and remove the periods.
        count = len(name)
        name = name.lstrip('.')
        count = count - len(name)

        # Now, build a list of route names, and pop one item off for every
        # period we've counted.
        mod_name = request.route_name.split('.')
        if count >= len(mod_name):
            del mod_name[:]
        else:
            del mod_name[len(mod_name) - count:]

        mod_name.append(name)
        name = '.'.join(mod_name)

    if not name in app._name_table:
        raise KeyError("Cannot find request handler with name %r." % name)

    rule_table = app._name_table[name]
    names, namegen, converters = rule_table[-3:]

    data = []
    values = list(values)

    for i in xrange(len(names)):
        name = names[i]

        if name in kw_values:
            val = kw_values.pop(name)
        elif values:
            val = values.pop(0)
        elif converters[i].default is not None:
            val = NoValue
        else:
            raise ValueError("Missing required value %r." % name)

        # Process the data.
        if val is NoValue:
            data.append(converters[i].default)
        else:
            data.append(converters[i].encode(request, val))

    # If we still have values, we were given too many.
    if values:
        raise ValueError("Too many values to unpack.")

    # Generate the string.
    out = namegen % tuple(data)

    dmn, sep, pth = out.partition("/")
    out = dmn + sep + urllib.quote(pth)

    if '_external' in kw_values:
        if kw_values['_external'] and out[0] == '/':
            out = request.host + out
        elif not kw_values['_external'] and out[0] != '/':
            _, _, out = out.partition('/')
            out = '/' + out
        del kw_values['_external']
    else:
        if not ":" in out and out.lower().startswith(request.hostname.lower()):
            out = out[len(request.hostname):]
        elif out.lower().startswith(request.host.lower()):
            out = out[len(request.host):]

    if '_scheme' in kw_values:
        if not out[0] == "/":
            out = "%s://%s" % (kw_values['_scheme'], out)
        elif request.scheme.lower() != kw_values['_scheme'].lower():
            out = "%s://%s%s" % (kw_values['_scheme'], request.host, out)
        del kw_values['_scheme']
    else:
        if not out[0] == "/":
            out = '%s://%s' % (request.scheme, out)

    # Remove the anchor before adding query string variables.
    anchor = kw_values.pop('_anchor', None)

    # Build the query
    if kw_values:
        out += '?%s' % urllib.urlencode(kw_values, doseq=kw_values.pop('_doseq', True))

    if anchor:
        out += '#' + anchor

    return out

########NEW FILE########
__FILENAME__ = asynchronous
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
This is the asynchronous request helper for the Application system, utilizing
generator coroutines for optimal performance and ease of development.
"""

# Warning: This whole file is pretty much weird magic.

import json
import traceback
import weakref

from functools import wraps
from types import GeneratorType

from pants.http.utils import HTTPHeaders

from pants.web.application import Application, error, Response, RequestContext
from pants.web.utils import HTTPException, HTTPTransparentRedirect, log


###############################################################################
# Constants
###############################################################################

Again = object()
Waiting = object()
Finished = object()


###############################################################################
# Storage
###############################################################################

receivers = {}


###############################################################################
# Exceptions
###############################################################################

class TimeoutError(Exception):
    """
    Instances of TimeoutError are raised into an asynchronous request handler
    when an :func:`async.wait` or :func:`async.receive` timeout.
    """
    pass


class RequestClosed(Exception):
    """
    An instance of RequestClosed is raised into an asynchronous request handler
    when the connection for the request is closed.
    """
    pass


###############################################################################
# Basic Asynchronous Requests
###############################################################################

def async(func):
    """
    The ``@async`` decorator is used in conjunction with
    :class:`pants.web.Application` to create asynchronous request handlers using
    generators. This is useful for performing database lookups and doing other
    I/O bound tasks without blocking the server. The following example performs
    a simple database lookup with a `fork <https://github.com/stendec/asyncmongo>`_
    of `asyncmongo <https://github.com/bitly/asyncmongo>`_ that adds support for
    Pants. It then uses `jinja2 <http://jinja.pocoo.org/>`_ templates to render
    the response.

    .. code-block:: python

        from pants.web import Application, async

        import jinja2
        import asyncmongo

        database_options = {
            'host': '127.0.0.1',
            'port': 27017,
            'dbname': 'test',
        }

        db = asyncmongo.Client(pool_id='web', backend='pants', **database_options)

        app = Application()
        env = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))

        index_template = env.get_template("index.html")

        @app.route("/")
        @async
        def index(request):
            results = yield async.run(db.news.find, {'published': True})
            yield index_template.render(data=results)

        app.run()

    Additionally, the @async decorator also allows for the easy implementation
    of server-sent events, including support for the ``text/event-stream``
    Content-Type used by HTML5 ```EventSource
    <http://dev.w3.org/html5/eventsource/>`_``.

    .. seealso::

        :func:`async.stream`, :func:`async.event_stream`
    """

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # Set a bit of state for the request.
        request._writer = _async_finish
        _init(request)

        # Create the generator.
        try:
            request._gen = gen = func(request, *args, **kwargs)
        except Exception:
            _cleanup(request)
            raise

        # If we've not got a generator, return the output.
        if not isinstance(gen, GeneratorType):
            _cleanup(request)
            return gen

        # Set a flag on the request so Application won't finish processing it.
        request.auto_finish = False

        # Now let's run the generator for the first time. No input yet, for
        # obvious reasons.
        _do(request, None)

    return wrapper


def _async_finish(request, output):
    """
    Write the provided output to the request and finish the request.
    """
    if request._started:
        request.connection.close(False)
        _cleanup(request)
        return

    # Do things App style.
    with request._context as app:
        request.auto_finish = True

        try:
            if output is Finished:
                raise RuntimeError("Reached StopIteration in asynchronous "
                                   "request handler.")

            app.parse_output(output)
        except Exception as err:
            if request._started:
                request.connection.close(False)
                _cleanup(request)
                return

            request._tb = traceback.format_exc()

            try:
                body, status, headers = app.handle_500(request, err)

            except Exception:
                log.exception("There was a problem handling an asynchronous "
                              "request, and a problem running "
                              "Application.handle_500 for %r." % app)
                body, status, headers = error(500, request=request)

            request.send_status(status)
            if not 'Content-Length' in headers:
                headers['Content-Length'] = len(body)
            request.send_headers(headers)
            request.write(body)
            request.finish()

    # Finish cleanup.
    _cleanup(request)


###############################################################################
# Asynchronous Streams
###############################################################################

def stream(func):
    """
    The ``@async.stream`` decorator is used to create asynchronous request
    handlers using generators. This can be used to begin writing a portion of
    the response to the client before the entire response can be generated.

    The very first yielded output is processed for a status code and headers
    using the same logic that :class:`~pants.web.Application` uses for its
    standard route functions.

    Subsequently yielded values are *not* processed, so returning a status code
    and/or headers in that situation will result in undesired output. You may
    return an instance of :class:`pants.web.Response` *or* the bare value to
    write out.

    The following is, though not particularly useful, an example::

        @app.route("/")
        @async.stream
        def index(request):
            yield None, 200, {'X-Pizza': 'Yum'}
            yield "This is an example.\n"
            yield "It isn't particularly useful.\n"

            yield ("This will be treated as a list and serialized with "
                   "JSON because you can't set the status code or provide "
                   "additional headers after the response has started."), 401

    """

    @wraps(func)
    def wrapped(request, *args, **kwargs):
        # Set a bit of state for the request.
        request._writer = _stream_output
        _init(request)

        # Create the generator.
        try:
            request._gen = gen = func(request, *args, **kwargs)
        except Exception:
            _cleanup(request)
            raise

        # If we've not got a generator, return the output.
        if not isinstance(gen, GeneratorType):
            _cleanup(request)
            return gen

        # Set a flag on the request so Application won't finish processing it.
        request.auto_finish = False

        # Now let's run the generator for the first time. No input yet, for
        # obvious reasons.
        _do(request, None)

    return wrapped

async.stream = stream


def _stream_output(request, output):
    """
    Write the provided chunk of data to the stream. This will automatically
    encode the output as Transfer-Encoding: chunked if necessary.
    """
    if request._started:
        if not output or output is Finished:
            # We're finished.
            if request._chunked:
                request.write("0\r\n\r\n\r\n")

            request.finish()
            _cleanup(request)
            return

        # Go ahead and cast the body and send it.
        if isinstance(output, Response):
            output = output.body

        try:
            output = _cast(request, output)
        except Exception:
            log.exception("Error casting output for asynchronous stream.")
            request.connection.close(False)
            _cleanup(request)
            return

        if request._chunked:
            request.write("%x\r\n%s\r\n" % (len(output), output))

        return Again


    # Assume that the first message has status and a header.
    if isinstance(output, Response):
        output, status, headers = output.body, output.status, output.headers
    elif isinstance(output, tuple):
        if len(output) == 3:
            output, status, headers = output
        else:
            output, status = output
            headers = HTTPHeaders()
    else:
        status = 200
        headers = HTTPHeaders()

    # Use the rule headers stuff.
    if request._rule_headers:
        if isinstance(request._rule_headers, HTTPHeaders):
            rule_headers = request._rule_headers.copy()
        else:
            rule_headers = HTTPHeaders(request._rule_headers)

        if isinstance(headers, HTTPHeaders):
            rule_headers._data.update(headers._data)
        else:
            rule_headers.update(headers)

        headers = rule_headers

    if request._rule_content_type and not 'Content-Type' in headers:
        headers['Content-Type'] = request._rule_content_type

    # Check for a character encoding.
    content_type = headers.get('Content-Type', '')
    if 'charset=' in content_type:
        request._charset = content_type.split('charset=',1)[1].strip()

    # Check the body to guess a Content-Type.
    if not 'Content-Type' in headers:
        if hasattr(output, "to_html") or (isinstance(output, basestring) and
                output[:5].lower() in ('<html', '<!doc')):
            headers['Content-Type'] = 'text/html; charset=%s' % request._charset
        elif isinstance(output, (tuple, list, dict)):
            headers['Content-Type'] = 'application/json'
        else:
            headers['Content-Type'] = 'text/plain; charset=%s' % request._charset

    # Finally, cast the body.
    errored = False
    if output is not None:
        try:
            output = _cast(request, output)
        except Exception as err:
            errored = True
            with request._context as app:
                try:
                    output, status, headers = app.handle_500(request, err)
                except Exception:
                    output, status, headers = error(500, request=request)

            if not 'Content-Length' in headers:
                headers['Content-Length'] = len(output)

    # Make sure the client has some way of determining the length.
    if not 'Content-Length' in headers and not 'Transfer-Encoding' in headers:
        headers['Transfer-Encoding'] = 'chunked'
        request._chunked = True

    # Now, send it all out.
    request.send_status(status)
    request.send_headers(headers)

    if request.method.upper() == 'HEAD':
        request.finish()
        _cleanup(request)
        return

    if output is not None:
        if request._chunked:
            request.write("%x\r\n%s\r\n" % (len(output), output))
        else:
            request.write(output)

    if errored:
        request.finish()
        _cleanup(request)
        return

    return Again


###############################################################################
# Event Stream
###############################################################################

def event_stream(func):
    """
    The ``@async.event_stream`` decorator allows you to easily push server-sent
    events from Pants to your web clients using the new HTML5 `EventSource
    <http://dev.w3.org/html5/eventsource/>`_ API. Example::

        from pants.web import Application, async, TimeoutError

        @app.route("/events")
        @async.event_stream
        def events(request):
            try:
                message = yield async.receive("events", 10)
            except TimeoutError:
                yield None
            else:
                yield message

        # Elsewhere...

        async.send("events", "Something happened!")

    When you yield a value, there are a few ways it can be processed.

    1.  If the value is empty, None, etc. a single comment line will be sent to
        the client to keep the connection alive.

    2.  If the value is a tuple, it will be separated into ``(output, headers)``
        and the provided message headers will be prepended to the output before
        it's sent to the client.

    3.  Any other values for the output will result in normal output processing
        before the output is sent to the client as a message.

    .. note::

        ``@async.event_stream`` automatically formats output messages, handling
        line breaks for you.

    """

    @wraps(func)
    def wrapped(request, *args, **kwargs):
        # Set a bit of state for the request.
        request._writer = _event_stream_output
        _init(request)
        request._chunked = True

        # Create the generator.
        try:
            request._gen = gen = func(request, *args, **kwargs)
        except Exception:
            _cleanup(request)
            raise

        # If we've not got a generator, return the output.
        if not isinstance(gen, GeneratorType):
            _cleanup(request)
            return gen

        # Set a flag on the request so Application won't finish processing it.
        request.auto_finish = False

        # Now let's run the generator for the first time. No input yet, for
        # obvious reasons.
        _do(request, None)

    return wrapped

async.event_stream = event_stream


def _event_stream_output(request, output):
    """
    Write a text/event-stream message to the client. If no data has been sent
    yet, it writes a 200 OK response code and a Content-Type header.
    """
    if not request._started:
        request.send_status()
        request.send_headers({'Content-Type': 'text/event-stream'})

    if output is Finished:
        # We're finished.
        request.connection.close()
        _cleanup(request)
        return

    if isinstance(output, tuple):
        output, headers = output
    else:
        headers = {}

    if not output and not headers:
        # Send a simple comment line for keep-alive.
        request.write(":\r\n")
        return Again

    if output is None:
        output = ""
    else:
        # Cast the output into something usable.
        output = _cast(request, output)

    # Split up output, adding "data:" field names, and then prepend the
    # provided headers, if there are any.
    output = "\r\n".join("data: %s" % x for x in output.splitlines())
    for key, value in headers.iteritems():
        output = "%s: %s\r\n%s" % (key, _cast(request, value), output)

    # Write it out, with an extra blank line so that the client will read
    # the message.
    request.write("%s\r\n\r\n" % output)
    return Again


###############################################################################
# Asynchronous _Sleeper
###############################################################################

class _Sleeper(tuple):
    def __repr__(self):
        return "_Sleeper(%r)" % self[0]


def sleep(time):
    """
    Sleep for *time* seconds, doing nothing else during that period.
    """
    return _Sleeper((time,))

async.sleep = sleep


###############################################################################
# Asynchronous Caller
###############################################################################

def run(function, *args, **kwargs):
    """
    Run *function* with the provided *args* and *kwargs*.

    This works for any function that supports the ``callback`` keyword argument
    by inserting a callback object into the keyword arguments before calling
    the function.

    If you need to asynchronously call a function that *doesn't* use
    ``callback``, please use :func:`async.callback`.

    Here is a brief example using an `asyncmongo
    <https://github.com/bitly/asyncmongo>`_ Client named ``db``::

        @app.route("/count")
        @async
        def count(request):
            results = yield async.run(db.news.find, {'published': True})
            yield len(results)

    .. note::

        ``async.run`` does *not* process keyword arguments passed to the
        callback. If you require the keyword arguments, you must use
        :func:`async.callback` manually.

    Calling ``async.run`` returns the instance of
    :class:`pants.web.Callback` used. Yielding that instance will
    wait until the callback is triggered and return the value passed to
    the callback.
    """

    # Create a callback and set the callback keyword argument.
    kwargs['callback'] = cb = Callback()

    # Ignore the return value.
    function(*args, **kwargs)

    # Return the callback.
    return cb

async.run = run


class Callback(object):
    """
    Return an instance of :class:`pants.web.Callback` that can be used as a
    callback with other asynchronous code to capture output and return it to
    an asynchronous request handler.

    Yielding an instance of Callback will wait until the callback has been
    triggered, and then return values that were sent to the callback so that
    they may be used by the asynchronous request handler.

    It's easy::

        @app.route("/")
        @async
        def index(request):
            callback = async.callback()
            do_something_crazy(request, on_complete=callback)

            result = yield callback
            if not result:
                abort(403)

            yield result

    """

    __slots__ = ("request", "use_kwargs")

    def __init__(self, use_kwargs=False):
        # Store this callback.
        self.use_kwargs = use_kwargs
        self.request = request = Application.current_app.request
        request._callbacks[self] = Waiting
        request._unhandled.append(self)

    def __call__(self, *args, **kwargs):
        request = self.request
        if hasattr(request, "_callbacks"):
            if self.use_kwargs:
                args = (args, kwargs)
            elif len(args) == 1:
                args = args[0]

            request._callbacks[self] = args

            # Now, see if we're finished waiting.
            _check_waiting(request, self)

async.callback = Callback


###############################################################################
# Waiting
###############################################################################

class _WaitList(list):
    timeout = None


def wait(timeout=None):
    """
    Wait for all asynchronous callbacks to return, and return a list of those
    values. If a *timeout* is provide, wait up to that many seconds for the
    callbacks to return before raising a TimeoutError containing a list of
    the results that *did* complete.
    """
    request = Application.current_app.request
    top, request._unhandled = _WaitList(request._unhandled), []

    top.timeout = timeout
    return top

async.wait = wait


def _wait_timeout(request):
    """
    Handle a timed-out async.wait().
    """
    if not hasattr(request, "_in_do"):
        # Don't deal with requests that were closed. Just don't.
        return

    # Get the item off the top of the waiting stack, and make sure it's
    # something we can work with.
    if not request._waiting or not isinstance(request._waiting[-1], _WaitList):
        return

    # Build the input list.
    input = []
    for key in request._waiting.pop():
        value = request._callbacks.pop(key)
        input.append(value if value is not Waiting else None)

    # Now, pass it along to _do. Note the as_exception=True.
    _do(request, TimeoutError(input), as_exception=True)


def _check_waiting(request, trigger=None):
    """
    Check the waiting list for the provided request to determine if we should
    be taking action. If we should, pop the top item from the waiting list and
    send the input we've gathered into _do.
    """

    if not hasattr(request, "_in_do"):
        # If this happens, the request was *probably* closed. There's nothing
        # to do, so just get out of here.
        return

    # Get the item off the top of the waiting stack, and make sure it's
    # something we can work with.
    top = request._waiting[-1] if request._waiting else None

    if not isinstance(top, (_WaitList, Callback)):
        return

    # If a trigger was provided, check to see if the top *is* that trigger. If
    # this is the case, we can just return the result for that specific item.
    if top is trigger:
        # It is. We can pop off the top and send the input now.
        request._waiting.pop()
        _do(request, request._callbacks.pop(trigger))
        return

    # If we're still here, then we've got a list of callbacks to wait on. If
    # any of those are still Waiting, we're not done yet, so return early.
    if any(request._callbacks[key] is Waiting for key in top):
        return

    # Check the _WaitList's timeout, and clear it if we find one.
    if callable(top.timeout):
        top.timeout()

    # We're finished, so build the list and send it on to _do.
    input = [request._callbacks.pop(key) for key in request._waiting.pop()]
    _do(request, input)


###############################################################################
# Message Sending
###############################################################################

class _Receiver(tuple):
    timeout = None
    ref = None


def send(key, *args):
    """
    Send a message with the provided ``*args`` to all asynchronous requests
    listening for *key*.
    """

    # Get the list of requests listening for key. If there aren't any, return.
    recv = receivers.pop(key, None)
    if not recv:
        return

    # If we only have one argument, pop it out of its tuple.
    if len(args) == 1:
        args = args[0]

    # Now, for each listening request, make sure it's still alive before
    # sending the arguments its way.
    for ref in recv:
        request = ref()
        if not request:
            continue

        # Check for the _in_do attribute, to make sure the request is still
        # working asynchronously.
        if not hasattr(request, "_in_do"):
            continue

        # Get the top of the request's wait list and make sure it's what
        # we expect.
        if not request._waiting or not isinstance(request._waiting[-1], _Receiver):
            continue

        # Pop the top item off the wait list and clear any timeout.
        top = request._waiting.pop()
        if callable(top.timeout):
            top.timeout()

        # Now, send the message.
        _do(request, args)

async.send = send


def receive(key, timeout=None):
    """
    Listen for messages with the key *key*. If *timeout* is specified, wait
    up to that many seconds before raising a TimeoutError.
    """
    out = _Receiver((key, timeout))
    return out

async.receive = receive


def _receive_timeout(request):
    if not hasattr(request, "_in_do"):
        return

    # Make sure the top of the wait list is a _Receiver.
    if not request._waiting or not isinstance(request._waiting[-1], _Receiver):
        return

    # Remove this request from the receivers list so we don't get any
    # unexpected input later on.
    top = request._waiting.pop()

    if top[0] in receivers and top.ref in receivers[top[0]]:
        receivers[top[0]].remove(top.ref)

    # Now, send along a TimeoutError.
    _do(request, TimeoutError(), as_exception=True)


###############################################################################
# Asynchronous Internals
###############################################################################

def _init(request):
    """
    Set a bit of state for the request.
    """
    request._in_do = False
    request._chunked = False
    request._charset = "utf-8"
    request._tb = None
    request._callbacks = {}
    request._waiting = []
    request._unhandled = []

    # Create a RequestContext.
    request._context = RequestContext()


def _cast(request, output):
    """
    Convert an output object into something we can send over a connection.
    """
    if hasattr(output, "to_html"):
        output = output.to_html()

    if isinstance(output, (tuple, list, dict)):
        with request._context as app:
            return json.dumps(output, cls=app.json_encoder)

    elif isinstance(output, unicode):
        return output.encode(request._charset)

    elif not isinstance(output, str):
        with request._context:
            return str(output)

    return output


def _cleanup(request):
    """
    Delete the context manager and everything else.
    """

    del request._in_do
    del request._chunked
    del request._charset
    del request._unhandled

    del request._context

    try:
        del request._gen
    except AttributeError:
        del request._callbacks
        del request._waiting
        return

    # Cleanup any timers.
    for item in request._waiting:
        timer = getattr(item, "timeout", None)
        if timer and callable(timer):
            try:
                timer()
            except Exception:
                # Who knows what could happen here.
                pass

    # Asynchronous Internals
    request._callbacks.clear()
    del request._callbacks
    del request._waiting


def _do(request, input, as_exception=False):
    """
    Send the provided input to the asynchronous request handler for *request*.
    If ``as_exception`` is truthy, throw it into the generator as an exception,
    otherwise it's just sent.
    """
    if request._in_do:
        # Let's not enter some bizarre stack recursion that can cause all sorts
        # of badness today, shall we? Put off the next _do till the next
        # engine cycle.
        request.connection.engine.callback(_do, request, input, as_exception)
        return

    try:
        request._in_do = True

        while True:
            errored = False

            with request._context as app:
                # Make sure we're connected.
                if not request.connection.connected:
                    try:
                        # Bubble up an error so the user's code can do something
                        # about this.
                        request._gen.throw(RequestClosed())
                    except RequestClosed:
                        # Don't react at all to our own exception.
                        pass
                    except Exception:
                        # Just log any other exception. The request is already
                        # closed, so there's not a lot *else* to do.
                        log.exception("Error while cleaning up closed "
                                      "asynchronous request: %s %s" %
                                      (request.method, request.url))
                    finally:
                        _cleanup(request)
                        return

                try:
                    if as_exception:
                        output = request._gen.throw(input)
                    else:
                        output = request._gen.send(input)

                except StopIteration:
                    # We've run out of content. Setting output to Finished
                    # tells the output handler to close up and go home.
                    output = Finished

                except HTTPException as err:
                    if request._started:
                        log.exception("Error while handling asynchronous "
                                      "request: %s %s" % (request.method,
                                                          request.url))
                        request.connection.close(False)
                        _cleanup(request)
                        return

                    errored = True
                    request._tb = traceback.format_exc()

                    err_handler = getattr(app, "handle_%d" % err.status, None)
                    if err_handler:
                        output = err_handler(request, err)
                    else:
                        output = error(err.message, err.status, err.headers,
                            request=request)

                except HTTPTransparentRedirect as err:
                    if request._started:
                        log.exception("HTTPTransparentRedirect sent to already "
                                      "started request: %s %s" %
                                      (request.method, request.url))
                        request.connection.close(False)
                        _cleanup(request)
                        return

                    errored = True
                    output = err
                    request._tb = traceback.format_exc()

                except Exception as err:
                    if request._started:
                        log.exception("Error while handling asynchronous "
                                      "request: %s %s" % (request.method,
                                                          request.url))
                        request.connection.close(False)
                        _cleanup(request)
                        return

                    errored = True
                    request._tb = traceback.format_exc()

                    try:
                        output = app.handle_500(request, err)
                    except Exception:
                        # There's an error with the handle_500 function.
                        log.exception("There was a problem handling a request, and a "
                                      "problem running Application.handle_500 for %r."
                                        % app)

                        output = error(500, request=request)

            # Did we error?
            if errored:
                # Clear the rule data, because errors don't care about it.
                request._rule_content_type = None
                request._rule_headers = None

                _async_finish(request, output)
                return

            # Returning a list of Callback instances is the only way to control
            # exactly what you're waiting for.
            if not isinstance(output, _WaitList) and \
                    isinstance(output, (tuple, list)) and \
                    all(isinstance(x, Callback) for x in output):
                output = _WaitList(output)

            # Now that we're out of the request context, let's see what we've got to
            # work with.
            if isinstance(output, _Sleeper):
                # Just sleep.
                request.connection.engine.defer(output[0], _do, request, None)

            elif isinstance(output, Callback):
                # Shove the callback onto its own waiting list.
                request._unhandled.remove(output)
                request._waiting.append(output)

            elif isinstance(output, _WaitList):
                # Push the WaitList onto the waiting list.
                if output.timeout:
                    output.timeout = request.connection.engine.defer(output.timeout, _wait_timeout, request)
                request._waiting.append(output)

            elif isinstance(output, _Receiver):
                # Push the Receiver onto the waiting list.
                if output[1]:
                    output.timeout = request.connection.engine.defer(output[1], _receive_timeout, request)

                output.ref = ref = weakref.ref(request)
                receivers.setdefault(output[0], []).append(ref)
                request._waiting.append(output)

            else:
                # We've received some content, so write it out.
                if request._writer(request, output) is Again:
                    input = None
                    as_exception = False
                    continue

            # We *have* to continue if we don't want to break.
            break

    finally:
        if hasattr(request, "_in_do"):
            request._in_do = False

########NEW FILE########
__FILENAME__ = fileserver
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
``pants.web.fileserver`` implements a basic static file server for use with a
:class:`~pants.http.server.HTTPServer` or
:class:`~pants.web.application.Application`. It makes use of the appropriate
HTTP headers and the ``sendfile`` system call, as well as the ``X-Sendfile``
header to improve transfer performance.

Serving Static Files
====================

The ``pants.web.fileserver`` module can be invoked directly using the *-m*
switch of the interpreter to serve files in a similar way to the standard
library's :mod:`SimpleHTTPServer`. However, it performs much more efficiently
than ``SimpleHTTPServer`` for this task.

.. code-block:: bash

    $ python -m pants.web.fileserver

When doing this, you may use additional arguments to specify which address the
server should bind to, as well as which filenames should serve as directory
indices. By default, only ``index.html`` and ``index.htm`` are served
as indices.

"""

###############################################################################
# Imports
###############################################################################

import mimetypes
import os
import re
import sys
import time
import urllib

from datetime import datetime, timedelta

from pants.http.utils import date, SERVER

from pants.web.application import abort, Application, redirect
from pants.web.utils import DATE_FORMATS, decode, DIRECTORY_ENTRY, \
    DIRECTORY_PAGE, HTTPException


__all__ = (
    "FileServer",  # Core Classes
)

###############################################################################
# Cross Platform Hidden File Detection
###############################################################################

def _is_hidden(file, path):
    return file.startswith(u'.')

if os.name == 'nt':
    try:
        import win32api, win32con
    except ImportError:
        win32api = None
        win32con = None

    if win32api:
        def _is_hidden(file, path):
            if file.startswith(u'.'):
                return True
            file = os.path.join(path, file)
            try:
                if win32api.GetFileAttributes(file) & win32con.FILE_ATTRIBUTE_HIDDEN:
                    return True
            except Exception:
                return True
            return False


###############################################################################
# FileServer Class
###############################################################################

class FileServer(object):
    """
    The FileServer is a request handling class that, as it sounds, serves files
    to the client using :meth:`pants.http.server.HTTPRequest.send_file`. As
    such, it supports caching headers, as well as ``X-Sendfile`` if the
    :class:`~pants.http.server.HTTPServer` instance is configured to use the
    Sendfile header. FileServer is also able to take advantage of the
    ``sendfile`` system call to improve performance when ``X-Sendfile`` is not
    in use.

    ==========  ==============================  ============
    Argument    Default                         Description
    ==========  ==============================  ============
    path                                        The path to serve.
    blacklist   ``.py`` and ``.pyc`` files      *Optional.* A list of regular expressions to test filenames against. If a given file matches any of the provided patterns, it will not be downloadable and instead return a ``403 Unauthorized`` error.
    default     ``index.html``, ``index.htm``   *Optional.* A list of default files to be displayed rather than a directory listing if they exist.
    ==========  ==============================  ============

    Using it is simple. It only requires a single argument: the path to serve
    files from. You can also supply a list of default files to check to serve
    rather than a file listing.

    When used with an Application, the FileServer is not created in the usual
    way with the route decorator, but rather with a method of the FileServer
    itself. Example::

        FileServer("/tmp/path").attach(app)

    If you wish to listen on a path other than ``/static/``, you can also use
    that when attaching::

        FileServer("/tmp/path").attach(app, "/files/")
    """
    def __init__(self, path, blacklist=(re.compile('.*\.py[co]?$'), ),
            defaults=('index.html', 'index.htm')):
        # Make sure our path is unicode.
        if not isinstance(path, unicode):
            path = decode(path)

        self.path = os.path.normpath(os.path.realpath(path))
        self.defaults = defaults

        # Build the blacklist.
        self.blacklist = []
        for bl in blacklist:
            if isinstance(bl, str):
                bl = re.compile(bl)
            self.blacklist.append(bl)

    def attach(self, app, path='/static/'):
        """
        Attach this FileServer to an :class:`~pants.web.application.Application`,
        bypassing the usual route decorator to ensure the rule is configured as
        FileServer expects.

        =========  ===============  ============
        Argument   Default          Description
        =========  ===============  ============
        app                         The :class:`~pants.contrib.web.Application` instance to attach to.
        rule       ``'/static/'``   *Optional.* The path to serve requests from.
        =========  ===============  ============
        """
        if not path.endswith("/"):
            path += '/'
        app.basic_route(path + '<regex("(.*)"):path>', func=self)

    def check_blacklist(self, path):
        """
        Check the given path to make sure it isn't blacklisted. If it is
        blacklisted, then raise an :class:`~pants.contrib.web.HTTPException`
        via :func:`~pants.contrib.web.abort`.

        =========  ============
        Argument   Description
        =========  ============
        path       The path to check against the blacklist.
        =========  ============
        """
        for bl in self.blacklist:
            if isinstance(bl, unicode):
                if bl in path:
                    abort(403)
            elif bl.match(path):
                abort(403)

    def __call__(self, request):
        """
        Serve a request.
        """

        try:
            path = request.match.groups()[-1]
            if path is None:
                path = urllib.unquote_plus(request.path)
        except (AttributeError, IndexError):
            path = urllib.unquote_plus(request.path)

        # Convert the path to unicode.
        path = decode(path)

        # Strip off a starting quote.
        if path.startswith('/') or path.startswith('\\'):
            path = path[1:]

        # Normalize the path.
        full_path = os.path.normpath(os.path.join(self.path, path))

        # Validate the request.
        if not full_path.startswith(self.path):
            abort(403)
        elif not os.path.exists(full_path):
            abort()
        elif not os.access(full_path, os.R_OK):
            abort(403)

        # Is this a directory?
        if os.path.isdir(full_path):
            # Check defaults.
            for f in self.defaults:
                full = os.path.join(full_path, f)
                if os.path.exists(full):
                    request.path = urllib.quote(full.encode('utf8'))
                    if hasattr(request, 'match'):
                        del request.match
                    return self.__call__(request)

            # Guess not. List it.
            if hasattr(request, 'match'):
                return self.list_directory(request, path)
            else:
                body, status, headers = self.list_directory(request, path)
                if isinstance(body, unicode):
                    body = body.encode('utf-8')
                headers['Content-Length'] = len(body)
                request.send_status(status)
                request.send_headers(headers)
                request.send(body)
                request.finish()
                return

        # Blacklist Checking.
        self.check_blacklist(full_path)

        # Let's send the file.
        request.auto_finish = False
        request.send_file(full_path)


    def list_directory(self, request, path):
        """
        Generate a directory listing and return it.
        """

        # Normalize the path.
        full_path = os.path.normpath(os.path.join(self.path, path))

        # Get the URL, which is just request.path decoded.
        url = decode(urllib.unquote(request.path))
        if not url.startswith(u'/'):
            url = u'/%s' % url
        if not url.endswith(u'/'):
            return redirect(u'%s/' % url)

        go_up = u''
        if url.strip(u'/'):
            go_up = u'<p><a href="..">Up to Higher Directory</a></p>'

        files = []
        dirs = []

        try:
            contents = os.listdir(full_path)
        except OSError:
            abort(403)

        for p in sorted(contents, key=unicode.lower):
            if _is_hidden(p, full_path):
                continue

            full = os.path.join(full_path, p)
            try:
                fp = full
                if os.path.isdir(full):
                    fp += '/'
                self.check_blacklist(fp)
            except HTTPException:
                continue

            stat = os.stat(full)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime(
                u'%Y-%m-%d %I:%M:%S %p'
                )

            if os.path.isdir(full):
                cls = u'folder'
                link = u'%s/' % p
                size = u'<span class="faint">Directory</span>'
                obj = dirs

            elif os.path.isfile(full):
                cls = 'document'
                ext = p[p.rfind('.')+1:]
                if ext in ('jpg','jpeg','png','gif','bmp'):
                    cls = 'image'
                elif ext in ('zip','gz','tar','7z','tgz'):
                    cls = 'zip'
                elif ext in ('mp3','mpa','wma','wav','flac','mid','midi','raw',
                        'mod','xm','aac','m4a','ogg','aiff','au','voc','m3u',
                        'pls','asx'):
                    cls = 'audio'
                elif ext in ('mpg','mpeg','mkv','mp4','wmv','avi','mov'):
                    cls = 'video'
                link = p
                size = _human_readable_size(stat.st_size)
                obj = files

            else:
                continue

            obj.append(DIRECTORY_ENTRY.safe_substitute(
                        cls=cls,
                        url=url + link,
                        name=p,
                        size=size,
                        modified=mtime
                        ))

        if files or dirs:
            files = u''.join(dirs) + u''.join(files)
        else:
            files = (u'<tr><td colspan="3" class="noborder">'
                     u'<div class="footer center">'
                     u'This directory is empty.</div></td></tr>')

        if Application.current_app and Application.current_app.debug:
            rtime = u'%0.3f ms' % (1000 * request.time)
        else:
            rtime = u''

        output = DIRECTORY_PAGE.safe_substitute(
                    path=url,
                    go_up=go_up,
                    host=request.host,
                    scheme=request.scheme,
                    content=''.join(files),
                    debug=rtime
                    )

        return output, 200, {'Content-Type': 'text/html; charset=UTF-8'}


###############################################################################
# Private Helper Functions
###############################################################################

_abbreviations = (
    (1<<50L, u' PB'),
    (1<<40L, u' TB'),
    (1<<30L, u' GB'),
    (1<<20L, u' MB'),
    (1<<10L, u' KB'),
    (1, u' B')
)

def _human_readable_size(size, precision=2):
    """ Convert a size to a human readable filesize. """
    if not size:
        return u'0 B'

    for f,s in _abbreviations:
        if size >= f:
            break

    ip, dp = str(size/float(f)).split('.')
    if int(dp[:precision]):
        return  u'%s.%s%s' % (ip, dp[:precision], s)
    return u'%s%s' % (ip, s)


###############################################################################
# Run as Module Support
###############################################################################

if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser(usage="%prog [options] [path]")

    parser.add_option("-b", "--bind", metavar="ADDRESS", dest="address",
        default="8000", help="Bind the server to PORT, INTERFACE:PORT, or unix:PATH")
    parser.add_option("-i", "--index", metavar="FILE", dest="indices",
        action="append", default=[], help="Serve files named FILE if available rather than a directory listing.")

    options, args = parser.parse_args()
    args = ''.join(args)

    # First, get the directory.
    path = os.path.realpath(args)
    if not os.path.exists(path) or not os.path.isdir(path):
        print "The provided path %r is not a directory or does not exist." % path
        sys.exit(1)

    # Parse the address.
    if ':' in options.address:
        address = options.address.split(":", 1)
        if address[0].lower() == "unix":
            address = address[1]
        else:
            address[1] = int(address[1])
    else:
        address = int(options.address)

    # Fix up the indices list.
    indices = options.indices
    if not indices:
        indices.extend(['index.html', 'index.htm'])

    # Create the server now.
    app = Application()
    FileServer(path, [], indices).attach(app, '/')
    print "Serving HTTP with Pants on: %s" % repr(address)

    try:
        app.run(address)
    except (KeyboardInterrupt, SystemExit):
        pass

########NEW FILE########
__FILENAME__ = utils
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################

###############################################################################
# Imports
###############################################################################

import base64
import logging
import re
import string
import sys

from pants.http.utils import HTTP, SERVER, SERVER_URL


try:
    from pkg_resources import resource_string
except ImportError:
    def resource_string(*args):
        raise IOError("pkg_resources not available.")

###############################################################################
# Logging
###############################################################################

log = logging.getLogger("pants.web")

###############################################################################
# Constants
###############################################################################

HAIKUS = {
    400: u'Something you entered<br>'
         u'transcended parameters.<br>'
         u'So much is unknown.',

    401: u'To access this page,<br>'
         u'one must know oneself; but then:<br>'
         u'inform the server.',

    403: u'Unfortunately,<br>'
         u'permissions insufficient.<br>'
         u'This, you cannot see.',

    404: u'You step in the stream,<br>'
         u'But the water has moved on.<br>'
         u'This page is not here.',

    410: u'A file that big?<br>'
         u'It might be very useful.<br>'
         u'But now it is Gone.',

    413: u'Out of memory.<br>'
         u'We wish to hold the whole sky,<br>'
         u'But we never will.',

    418: u'You requested coffee,<br>'
         u'it is neither short nor stout.<br>'
         u'I am a teapot.',

    500: u'Chaos reigns within.<br>'
         u'Reflect, repent, and reboot.<br>'
         u'Order shall return.'
}

if sys.platform.startswith('win'):
    HAIKUS[500] = (u'Yesterday it worked.<br>'
        u'Today, it is not working.<br>'
        u'Windows is like that.')

HTTP_MESSAGES = {
    401: u'You must sign in to access this page.',
    403: u'You do not have permission to view this page.',
    404: u'The page at <code>{url}</code> cannot be found.',
    500: u'The server encountered an internal error and cannot display '
         u'this page.'
}

# Formats for parse_date to use.
DATE_FORMATS = (
    "%a, %d %b %Y %H:%M:%S %Z",
    "%A, %d-%b-%y %H:%M:%S %Z",
    "%a %b %d %H:%M:%S %Y",
    )

# HTTP status codes that should not send response bodies.
NO_BODY_CODES = (204, 205, 304)


###############################################################################
# Resources
###############################################################################

# The Console JS
try:
    CONSOLE_JS = resource_string("pants.web", "data/console.js")
except IOError:
    # This message is commented out because the console JS isn't actually
    # *used* yet in the code, and can be safely ignored.
    # log.debug("Unable to load pants.web console JS from %r." % DATA_DIR)
    CONSOLE_JS = ""

# The Main CSS
try:
    MAIN_CSS = resource_string("pants.web", "data/main.css")
except IOError:
    log.debug("Unable to load pants.web main CSS.")
    MAIN_CSS = ""

# The Directory CSS
try:
    DIRECTORY_CSS = resource_string("pants.web", "data/directory.css")
except IOError:
    log.debug("Unable to load pants.web directory CSS.")
    DIRECTORY_CSS = ""

# The Images
IMAGES = {}
for name in ('audio', 'document', 'folder', 'image', 'video', 'zip'):
    try:
        IMAGES[name] = base64.b64encode(resource_string("pants.web",
                                                        "data/%s.png" % name))
    except IOError:
        log.debug("Unable to load pants.web icon %r." % name)

# Insert the images.
DIRECTORY_CSS = string.Template(DIRECTORY_CSS).safe_substitute(**IMAGES)

# The Main Template
try:
    PAGE = resource_string("pants.web", "data/main.html")
except IOError:
    log.debug("Unable to load pants.web page template.")
    PAGE = u"""<!DOCTYPE html>
<title>$title</title>
$content
<hr>
<address><a href="$server_url">$server</a> at
<a href="$scheme://$host">$scheme://$host</a></address>"""

# Fill up the template a bit.
PAGE = string.Template(PAGE).safe_substitute(
                                css=MAIN_CSS,
                                server_url=SERVER_URL,
                                server=SERVER)

PAGE = re.compile(">\s+<", flags=re.DOTALL).sub("><", PAGE)
PAGE = string.Template(PAGE)

# The Directory Template
try:
    DIRECTORY_PAGE = PAGE.safe_substitute(
                            title="Index of $path",
                            content=resource_string("pants.web",
                                                    "data/directory.html"),
                            extra_css=DIRECTORY_CSS
                            )
except IOError:
    DIRECTORY_PAGE = PAGE.safe_substitute(
                            title="Index of $path",
                            content="""<h1>Index of $path</h1>
$go_up
<table><thead><tr><th>Name</th><th>Size</th><th>Last Modified</th></tr></thead>
$content
</table>""",
                            extra_css=DIRECTORY_CSS
                            )

DIRECTORY_PAGE = string.Template(DIRECTORY_PAGE)

# Directory Entry Template
try:
    DIRECTORY_ENTRY = resource_string("pants.web", "data/entry.html")
except IOError:
    DIRECTORY_ENTRY = '<tr><td><a class="icon $cls" href="$url">$name</a>' + \
                      '</td><td>$size</td><td>$modified</td></tr>'

DIRECTORY_ENTRY = string.Template(DIRECTORY_ENTRY)

# The Error Template
try:
    ERROR_PAGE = PAGE.safe_substitute(
                        title="$status $status_text",
                        content=resource_string("pants.web", "data/error.html"),
                        extra_css=u'')
except IOError:
    log.warning("Unable to load pants.web error template.")
    ERROR_PAGE = PAGE.safe_substitute(
                        title="$status $status_text",
                        extra_css=u'',
                        content=u"""<h1>$status $status_text</h1>
$content""")

ERROR_PAGE = string.Template(ERROR_PAGE)


###############################################################################
# Special Exceptions
###############################################################################

class HTTPException(Exception):
    """
    Raising an instance of HTTPException will cause the Application to render
    an error page out to the client with the given
    `HTTP status code <http://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_,
    message, and any provided headers.

    This is, generally, preferable to allowing an exception of a different
    type to bubble up to the Application, which would result in a
    ``500 Internal Server Error`` page.

    The :func:`abort` helper function makes it easy to raise instances of
    this exception.

    =========  ============
    Argument   Description
    =========  ============
    status     *Optional.* The `HTTP status code <http://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_ to generate an error page for. If this isn't specified, a ``404 Not Found`` page will be generated.
    message    *Optional.* A text message to display on the error page.
    headers    *Optional.* A dict of extra HTTP headers to return with the rendered page.
    =========  ============
    """
    def __init__(self, status=404, message=None, headers=None):
        super(HTTPException, self).__init__(status, message, headers)

    def __str__(self):
        return "%d %s [message=%r, headers=%r]" % \
            (self.status, HTTP.get(self.status, ''), self.args[1], self.args[2])

    def __repr__(self):
        return "HTTPException(status=%r, message=%r, headers=%r)" % self.args

    @property
    def status(self):
        return self.args[0]

    @property
    def message(self):
        return self.args[1]

    @property
    def headers(self):
        return self.args[2]


class HTTPTransparentRedirect(Exception):
    """
    Raising an instance of HTTPTransparentRedirect will cause the Application
    to silently redirect a request to a new URL.
    """
    def __init__(self, url):
        super(HTTPTransparentRedirect, self).__init__(url)

    def __str__(self):
        return "url=%r" % self.args[0]

    def __repr__(self):
        return "%s(url=%r)" % (self.__class__.__name__, self.args[0])

    @property
    def url(self):
        return self.args[0]


###############################################################################
# Private Helper Functions
###############################################################################

_encodings = ('utf-8','iso-8859-1','cp1252','latin1')
def decode(text):
    for enc in _encodings:
        try:
            return text.decode(enc)
        except UnicodeDecodeError:
            continue
    else:
        return text.decode('utf-8','ignore')

########NEW FILE########
__FILENAME__ = wsgi
###############################################################################
#
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
``pants.web.wsgi`` implements a WSGI compatibility class that lets you run
WSGI applications using the Pants :class:`~pants.http.server.HTTPServer`.

Currently, this module uses the :pep:`333` standard. Future releases will add
support for :pep:`3333`, as well as the ability to host a Pants
:class:`~pants.web.application.Application` from a standard WSGI server.
"""

###############################################################################
# Imports
###############################################################################

import cStringIO
import sys
import traceback

from pants.web.application import error
from pants.web.utils import log, SERVER

###############################################################################
# WSGIConnector Class
###############################################################################

class WSGIConnector(object):
    """
    This class functions as a request handler for the Pants
    :class:`~pants.http.server.HTTPServer` that wraps WSGI applications to
    allow them to work correctly.

    Class instances are callable, and when called with a
    :class:`~pants.http.server.HTTPRequest` instance, they construct a WSGI
    environment and invoke the application.

    .. code-block:: python

        from pants import Engine
        from pants.http import HTTPServer
        from pants.web import WSGIConnector

        def hello_app(environ, start_response):
            start_response("200 OK", {"Content-Type": "text/plain"})
            return ["Hello, World!"]

        connector = WSGIConnector(hello_app)
        HTTPServer(connector).listen()
        Engine.instance().start()

    ``WSGIConnector`` supports sending responses with
    ``Transfer-Encoding: chunked`` and will do so automatically when the WSGI
    application's response does not contain information about the response's
    length.

    ============  ============
    Argument      Description
    ============  ============
    application   The WSGI application that will handle incoming requests.
    debug         *Optional.* Whether or not to display tracebacks and additional debugging information for a request within ``500 Internal Server Error`` pages.
    ============  ============
    """
    def __init__(self, application, debug=False):
        self.app = application
        self.debug = debug

    def attach(self, application, rule, methods=('HEAD','GET','POST','PUT')):
        """
        Attach the WSGIConnector to an instance of
        :class:`~pants.web.application.Application` at the given
        :ref:`route <app-routing>`.

        You may use route variables to strip information out of a URL. In the
        event that variables exist, they will be made available within the WSGI
        environment under the key `wsgiorg.routing_args <http://wsgi.readthedocs.org/en/latest/specifications/routing_args.html>`_

        .. warning::

            When using WSGIConnector within an Application, WSGIConnector
            expects the final variable in the rule to capture the remainder of
            the URL, and it treats the last variable as containing the value
            for the ``PATH_INFO`` variable in the WSGI environment. This method
            adds such a variable automatically. However, if you add the
            WSGIConnector manually you will have to be prepared.

        ============  ============
        Argument      Description
        ============  ============
        application   The :class:`~pants.web.Application` to attach to.
        rule          The path to serve requests from.
        methods       *Optional.* The HTTP methods to accept.
        ============  ============
        """
        if not rule.endswith('/'):
            rule += '/'

        application.route(rule + '<regex("(.*)"):path>', methods=methods, func=self)

    def __call__(self, request, *args):
        """
        Handle the given request.
        """
        # Make sure this plays nice with Web.
        request.auto_finish = False

        request._headers = None
        request._head_status = None
        request._chunk_it = False

        def write(data):
            if not request._started:
                # Before the first output, send the headers.
                # But before that, figure out if we've got a set length.
                for k,v in request._headers:
                    if k.lower() == 'content-length' or k.lower() == 'transfer-encoding':
                        break
                else:
                    request._headers.append(('Transfer-Encoding', 'chunked'))
                    request._chunk_it = True

                request.send_status(request._head_status)
                request.send_headers(request._headers)

            if request._chunk_it:
                request.write("%x\r\n%s\r\n" % (len(data), data))
            else:
                request.write(data)

        def start_response(status, head, exc_info=None):
            if exc_info:
                try:
                    if request._started:
                        raise exc_info[0], exc_info[1], exc_info[2]
                finally:
                    exc_info = None

            elif request._head_status is not None:
                raise RuntimeError("Headers already set.")

            if not isinstance(status, (int, str)):
                raise ValueError("status must be a string or int")
            if not isinstance(head, list):
                if isinstance(head, dict):
                    head = [(k,v) for k,v in head.iteritems()]
                else:
                    try:
                        head = list(head)
                    except ValueError:
                        raise ValueError("headers must be a list")

            request._head_status = status
            request._headers = head
            return write

        # Check for extra arguments that would mean we're being used
        # within Application.
        if hasattr(request, '_converted_match'):
            path = request._converted_match[-1]
            routing_args = request._converted_match[:-1]
        else:
            path = request.path
            if hasattr(request, 'match'):
                routing_args = request.match.groups()
            else:
                routing_args = None

        # Build an environment for the WSGI application.
        environ = {
            'REQUEST_METHOD'    : request.method,
            'SCRIPT_NAME'       : '',
            'PATH_INFO'         : path,
            'QUERY_STRING'      : request.query,
            'SERVER_NAME'       : request.headers.get('Host','127.0.0.1'),
            'SERVER_PROTOCOL'   : request.protocol,
            'SERVER_SOFTWARE'   : SERVER,
            'REMOTE_ADDR'       : request.remote_ip,
            'GATEWAY_INTERFACE' : 'WSGI/1.0',
            'wsgi.version'      : (1,0),
            'wsgi.url_scheme'   : request.scheme,
            'wsgi.input'        : cStringIO.StringIO(request.body),
            'wsgi.errors'       : sys.stderr,
            'wsgi.multithread'  : False,
            'wsgi.multiprocess' : False,
            'wsgi.run_once'     : False
        }

        if isinstance(request.connection.server.local_address, tuple):
            environ['SERVER_PORT'] = request.connection.server.local_address[1]

        if routing_args:
            environ['wsgiorg.routing_args'] = (routing_args, {})

        if 'Content-Type' in request.headers:
            environ['CONTENT_TYPE'] = request.headers['Content-Type']
        if 'Content-Length' in request.headers:
            environ['CONTENT_LENGTH'] = request.headers['Content-Length']

        for k,v in request.headers._data.iteritems():
            environ['HTTP_%s' % k.replace('-','_').upper()] = v

        # Run the WSGI Application.
        try:
            result = self.app(environ, start_response)

            if result:
                try:
                    if isinstance(result, str):
                        write(result)
                    else:
                        for data in result:
                            if data:
                                write(data)
                finally:
                    try:
                        if hasattr(result, 'close'):
                            result.close()
                    except Exception:
                        log.warning("Exception running result.close() for: "
                                    "%s %s", request.method, request.path,
                            exc_info=True)
                    result = None

        except Exception:
            log.exception('Exception running WSGI application for: %s %s',
                request.method, request.path)

            # If we've started, bad stuff.
            if request._started:
                # We can't recover, so close the connection.
                if request._chunk_it:
                    request.write("0\r\n\r\n\r\n")
                request.connection.close(True)
                return

            # Use the default behavior if we're not debugging.
            if not self.debug:
                raise

            resp = u''.join([
                u"<h2>Traceback</h2>\n",
                u"<pre>%s</pre>\n" % traceback.format_exc(),
                u"<h2>HTTP Request</h2>\n",
                request.__html__(),
                ])
            body, status, headers = error(resp, 500, request=request,
                debug=True)

            request.send_status(500)

            if not 'Content-Length' in headers:
                headers['Content-Length'] = len(body)

            request.send_headers(headers)
            request.write(body)
            request.finish()
            return

        # Finish up here.
        if not request._started:
            write('')
        if request._chunk_it:
            request.write("0\r\n\r\n\r\n")

        request.finish()

########NEW FILE########
__FILENAME__ = _channel
###############################################################################
#
# Copyright 2009 Facebook (see NOTICE.txt)
# Copyright 2011-2012 Pants Developers (see AUTHORS.txt)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
"""
The low-level channel class. Provides a non-blocking socket wrapper for
use as a base for higher-level classes. Intended for internal use only.
"""

###############################################################################
# Imports
###############################################################################

import errno
import os
import socket
import sys
import time

from pants.engine import Engine
from pants.util.sendfile import sendfile

dns = None


###############################################################################
# Logging
###############################################################################

import logging
log = logging.getLogger("pants")


###############################################################################
# Constants
###############################################################################

SUPPORTED_FAMILIES = [socket.AF_INET]
HAS_UNIX = False
try:
    SUPPORTED_FAMILIES.append(socket.AF_UNIX)
except AttributeError:
    # Unix sockets not supported.
    pass
else:
    HAS_UNIX = True

HAS_IPV6 = False
if socket.has_ipv6:
    # IPv6 must be enabled on Windows XP before it can be used, but
    # socket.has_ipv6 will be True regardless. Check that we can
    # actually create an IPv6 socket.
    try:
        socket.socket(socket.AF_INET6)
    except socket.error:
        pass
    else:
        HAS_IPV6 = True
        SUPPORTED_FAMILIES.append(socket.AF_INET6)

SUPPORTED_FAMILIES = tuple(SUPPORTED_FAMILIES)
SUPPORTED_TYPES = (socket.SOCK_STREAM, socket.SOCK_DGRAM)

if sys.platform == "win32":
    FAMILY_ERROR = (10047, "WSAEAFNOSUPPORT")
    NAME_ERROR = (11001, "WSAHOST_NOT_FOUND")
else:
    FAMILY_ERROR = (97, "Address family not supported by protocol")
    NAME_ERROR = (-2, "Name or service not known")


###############################################################################
# Functions
###############################################################################

# os.strerror() is buggy on Windows, so we have to look up the error
# string manually.
if sys.platform == "win32":
    def strerror(err):
        if err in socket.errorTab:
            errstr = socket.errorTab[err]
        elif err in errno.errorcode:
            errstr = errno.errorcode[err]
        else:
            errstr = os.strerror(err)
            if errstr == "Unknown error":
                errstr += ": %d" % err
        return errstr
else:
    strerror = os.strerror

def sock_type(sock):
    """
    We can thank Linux for this abomination of a function.
    
    As of Linux 2.6.27, bits 11-32 of the socket type are flags. This
    change was made with a complete lack of consideration for the fact
    that socket types are not flags, but are in fact "symbolic
    constants" represented on all major operating systems by sequential
    numbers. It is impossible to distinguish between some types (i.e.
    SOCK_STREAM and SOCK_RAW) using a simple bitwise AND, as one would
    expect from a flag value.
    
    To get around this, we treat the first 9 bits as the "real" type.
    """
    return sock.type & 1023


###############################################################################
# _Channel Class
###############################################################################

class _Channel(object):
    """
    A simple socket wrapper class.

    _Channel wraps most common socket methods to make them "safe", more
    consistent in their return values and easier to use in non-blocking
    code. This class is for internal use -- it does not function as-is
    and must be subclassed. Subclasses should override
    :meth:`~pants._channel._Channel._handle_read_event` and
    :meth:`~pants._channel._Channel._handle_write_event` to implement
    basic event-handling behaviour. Subclasses may also override
    :meth:`~pants._channel._Channel._handle_error_event` and
    :meth:`~pants._channel._Channel._handle_hangup_event` to implement
    custom error-handling behaviour. Subclasses should also ensure that
    they call the relevant on_* event handler placeholders at the
    appropriate times.

    =================  ================================================
    Keyword Argument   Description
    =================  ================================================
    engine             *Optional.* The engine to which the channel
                       should be added. Defaults to the global engine.
    socket             *Optional.* A pre-existing socket to wrap.
                       Defaults to a newly-created socket.
    =================  ================================================
    """
    def __init__(self, **kwargs):
        self.engine = kwargs.get("engine", Engine.instance())

        # Socket
        self._socket = None
        self._closed = False
        sock = kwargs.get("socket", None)
        if sock:
            self._socket_set(sock)

        # I/O attributes
        self._recv_amount = 4096

        # Internal state
        self._events = Engine.ALL_EVENTS
        if self._socket:
            self.engine.add_channel(self)

    def __repr__(self):
        return "%s #%r (%s)" % (self.__class__.__name__, self.fileno,
                object.__repr__(self))

    ##### Properties ##########################################################

    @property
    def fileno(self):
        """
        The fileno associated with the socket that this channel wraps,
        or None if the channel does not have a socket.
        """
        return None if not self._socket else self._socket.fileno()

    ##### Control Methods #####################################################

    def close(self, flush=True):
        """
        Close the channel.

        This method does not call the on_close() event handler -
        subclasses are responsible for that functionality.

        =========  =====================================================
        Argument   Description
        =========  =====================================================
        flush      If True, the channel will try to flush any
                   internally buffered data before actually closing.
                   :class:`~pants._channel._Channel` does not do any
                   internal buffering itself, but its subclasses may.
        =========  =====================================================
        """
        if self._closed:
            return

        if self._socket is not None:
            self.engine.remove_channel(self)
            self._socket_close()
        else:
            self._closed = True
        self._events = Engine.ALL_EVENTS

    ##### Public Event Handlers ###############################################

    def on_read(self, data):
        """
        Placeholder. Called when data is read from the channel.

        =========  ============
        Argument   Description
        =========  ============
        data       A chunk of data received from the socket.
        =========  ============
        """
        pass

    def on_write(self):
        """
        Placeholder. Called after the channel has finished writing data.
        """
        pass

    def on_connect(self):
        """
        Placeholder. Called after the channel has connected to a remote
        socket.
        """
        pass

    def on_listen(self):
        """
        Placeholder. Called when the channel begins listening for new
        connections or packets.
        """
        pass

    def on_accept(self, sock, addr):
        """
        Placeholder. Called after the channel has accepted a new
        connection.

        =========  ============
        Argument   Description
        =========  ============
        sock       The newly connected socket object.
        addr       The new socket's address.
        =========  ============
        """
        pass

    def on_close(self):
        """
        Placeholder. Called after the channel has finished closing.
        """
        pass

    ##### Public Error Handlers ###############################################

    def on_connect_error(self, exception):
        """
        Placeholder. Called when the channel has failed to connect to a
        remote socket.

        By default, logs the exception and closes the channel.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        self.close(flush=False)

    def on_read_error(self, exception):
        """
        Placeholder. Called when the channel has failed to read data
        from a remote socket.

        By default, logs the exception and closes the channel.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        self.close(flush=False)

    def on_write_error(self, exception):
        """
        Placeholder. Called when the channel has failed to write data to
        a remote socket.

        By default, logs the exception and closes the channel.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        self.close(flush=False)

    def on_overflow_error(self, exception):
        """
        Placeholder. Called when an internal buffer on the channel has
        exceeded its size limit.

        By default, logs the exception and closes the channel.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        self.close(flush=False)

    def on_error(self, exception):
        """
        Placeholder. Generic error handler for exceptions raised on the
        channel. Called when an error occurs and no specific
        error-handling callback exists.

        By default, logs the exception and closes the channel.

        ==========  ============
        Argument    Description
        ==========  ============
        exception   The exception that was raised.
        ==========  ============
        """
        log.exception(exception)
        self.close(flush=False)

    ##### Socket Method Wrappers ##############################################

    def _socket_set(self, sock):
        """
        Set the channel's current socket and update channel details.

        =========  ============
        Argument   Description
        =========  ============
        sock       A socket for this channel to wrap.
        =========  ============
        """
        if self._socket is not None:
            raise RuntimeError("Cannot replace existing socket.")
        if sock.family not in SUPPORTED_FAMILIES:
            raise ValueError("Unsupported socket family.")
        if sock_type(sock) not in SUPPORTED_TYPES:
            raise ValueError("Unsupported socket type.")

        sock.setblocking(False)
        self._socket = sock

    def _socket_connect(self, addr):
        """
        Connect the socket to a remote socket at the given address.

        Returns True if the connection was completed immediately, False
        otherwise.

        =========  ============
        Argument   Description
        =========  ============
        addr       The remote address to connect to.
        =========  ============
        """
        try:
            result = self._socket.connect_ex(addr)
        except socket.error as err:
            result = err.args[0]

        # None can be returned by an SSLSocket when it times out, rather
        # than EAGAIN. See issue #42 for more information.
        if result is None:
            result = errno.EAGAIN

        if result == 0 or result == errno.EISCONN:
            return True

        if result in (errno.EAGAIN, errno.EWOULDBLOCK,
                errno.EINPROGRESS, errno.EALREADY):
            self._start_waiting_for_write_event()
            return False

        raise socket.error(result, strerror(result))

    def _socket_bind(self, addr):
        """
        Bind the socket to the given address.

        =========  ============
        Argument   Description
        =========  ============
        addr       The local address to bind to.
        =========  ============
        """
        self._socket.bind(addr)

    def _socket_listen(self, backlog):
        """
        Begin listening for connections made to the socket.

        =========  ============
        Argument   Description
        =========  ============
        backlog    The size of the connection queue.
        =========  ============
        """
        if sys.platform == "win32" and backlog > socket.SOMAXCONN:
            log.warning("Setting backlog to SOMAXCONN on %r." % self)
            backlog = socket.SOMAXCONN

        self._socket.listen(backlog)

    def _socket_close(self):
        """
        Close the socket.
        """
        try:
            if self._socket:
                self._socket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        finally:
            if self._socket:
                self._socket.close()
            self._socket = None
            self._closed = True

    def _socket_accept(self):
        """
        Accept a new connection to the socket.

        Returns a 2-tuple containing the new socket and its remote
        address. The 2-tuple is (None, None) if no connection was
        accepted.
        """
        try:
            return self._socket.accept()
        except socket.error as err:
            if err.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                return None, None
            else:
                raise

    def _socket_recv(self):
        """
        Receive data from the socket.

        Returns a string of data read from the socket. The data is None if
        the socket has been closed.
        """
        try:
            data = self._socket.recv(self._recv_amount)
        except socket.error as err:
            if err.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                return ''
            elif err.args[0] == errno.ECONNRESET:
                return None
            else:
                raise

        if not data:
            return None
        else:
            return data

    def _socket_recvfrom(self):
        """
        Receive data from the socket.

        Returns a 2-tuple containing a string of data read from the socket
        and the address of the sender. The data is None if reading failed.
        The data and address are None if no data was received.
        """
        try:
            data, addr = self._socket.recvfrom(self._recv_amount)
        except socket.error as err:
            if err.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK,
                    errno.ECONNRESET):
                return '', None
            else:
                raise

        if not data:
            return None, None
        else:
            return data, addr

    def _socket_send(self, data):
        """
        Send data to the socket.

        Returns the number of bytes that were sent to the socket.

        =========  ============
        Argument   Description
        =========  ============
        data       The string of data to send.
        =========  ============
        """
        # TODO Find out if socket.send() can return 0 rather than raise
        # an exception if it needs a write event.
        try:
            return self._socket.send(data)
        except Exception as err:
            if err.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                self._start_waiting_for_write_event()
                return 0
            elif err.args[0] == errno.EPIPE:
                self.close(flush=False)
                return 0
            else:
                raise

    def _socket_sendto(self, data, addr, flags=0):
        """
        Send data to a remote socket.

        Returns the number of bytes that were sent to the socket.

        =========  ============
        Argument   Description
        =========  ============
        data       The string of data to send.
        addr       The remote address to send to.
        flags      *Optional.* Flags to pass to the sendto call.
        =========  ============
        """
        try:
            return self._socket.sendto(data, flags, addr)
        except Exception as err:
            if err.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                self._start_waiting_for_write_event()
                return 0
            elif err.args[0] == errno.EPIPE:
                self.close(flush=False)
                return 0
            else:
                raise

    def _socket_sendfile(self, sfile, offset, nbytes, fallback=False):
        """
        Send data from a file to a remote socket.

        Returns the number of bytes that were sent to the socket.

        =========  ====================================================
        Argument   Description
        =========  ====================================================
        sfile      The file to send.
        offset     The number of bytes to offset writing by.
        nbytes     The number of bytes of the file to write. If 0, all
                   bytes will be written.
        fallback   If True, the pure-Python sendfile function will be
                   used.
        =========  ====================================================
        """
        try:
            return sendfile(sfile, self, offset, nbytes, fallback)
        except Exception as err:
            if err.args[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                self._start_waiting_for_write_event()
                return err.nbytes # See issue #43
            elif err.args[0] == errno.EPIPE:
                self.close(flush=False)
                return 0
            else:
                raise

    ##### Internal Methods ####################################################

    def _start_waiting_for_write_event(self):
        """
        Start waiting for a write event on the channel, update the
        engine if necessary.
        """
        if self._events != self._events | Engine.WRITE:
            self._events = self._events | Engine.WRITE
            self.engine.modify_channel(self)

    def _stop_waiting_for_write_event(self):
        """
        Stop waiting for a write event on the channel, update the engine
        if necessary.
        """
        if self._events == self._events | Engine.WRITE:
            self._events = self._events & (self._events ^ Engine.WRITE)
            self.engine.modify_channel(self)

    def _safely_call(self, thing_to_call, *args, **kwargs):
        """
        Safely execute a callable.

        The callable is wrapped in a try block and executed. If an
        exception is raised it is logged.

        If no exception is raised, returns the value returned by
        :func:`thing_to_call`.

        ==============  ============
        Argument        Description
        ==============  ============
        thing_to_call   The callable to execute.
        *args           The positional arguments to be passed to the callable.
        **kwargs        The keyword arguments to be passed to the callable.
        ==============  ============
        """
        try:
            return thing_to_call(*args, **kwargs)
        except Exception:
            log.exception("Exception raised in callback on %r." % self)

    def _get_socket_error(self):
        """
        Get the most recent error that occured on the socket.

        Returns a 2-tuple containing the error code and the error message.
        """
        err = self._socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        errstr = ""

        if err != 0:
            errstr = strerror(err)

        return err, errstr

    def _format_address(self, address):
        """
        Given an address, returns the address family and - if
        necessary - properly formats the address. Also determines if the
        address is a hostname that must be resolved.

        A string is treated as an AF_UNIX address. An integer or long is
        converted to a 2-tuple of the form ('', number). A 4-tuple is
        treated as an AF_INET6 address.

        If the first part of the address tuple is an empty string, it will be
        interpreted as INADDR_ANY given a 2-tuple or IN6ADDR_ANY_INIT, the
        IPv6 equivalent, given a 4-tuple.

        If a 2-tuple uses an IP address, the family will be set properly,
        otherwise the returned family will be ``0`` and the resolved value
        will be False.

        The following table demonstrates how _format_address will react to
        different inputs.

        =================================  ================================
        Address                            ``(address, family, resolved)``
        =================================  ================================
        ``None``                           **raises exception**
        ``'/myserver'``                    ``('/myserver', socket.AF_UNIX, True)``
        ``80``                             ``(('', 80), socket.AF_INET, True)``
        ``('www.google.com', 80)``         ``(('www.google.com', 80), 0, False)``
        ``('', 80, 0, 0)``                 ``(('', 80, 0, 0), socket.AF_INET6, True)``
        ``('www.google.com', 80, 0, 0)``   ``(('www.google.com', 80, 0, 0), socket.AF_INET6, False)``
        ``('2001:4860::1014', 80)``        ``(('2001:4860::1014', 80, 0, 0), socket.AF_INET6, True)``
        ``('8.8.8.8', 53)``                ``(('8.8.8.8', 53), socket.AF_INET, True)``
        =================================  ================================

        Will raise an InvalidAddressFormatError if the given address is
        from an unknown or unsupported family.

        ========= ============
        Argument  Description
        ========= ============
        address   The address to format.
        ========= ============
        """
        if isinstance(address, basestring):
            if HAS_UNIX:
                return address, socket.AF_UNIX, True
            raise InvalidAddressFormatError("AF_UNIX not supported.")

        elif isinstance(address, (int, long)):
            return ('', address), socket.AF_INET, True

        elif not isinstance(address, (tuple, list)) or \
                not len(address) in (2,4) or \
                not isinstance(address[0], basestring):
            raise InvalidAddressFormatError("Invalid address: %s" %
                                            repr(address))

        # Deal with IPv6 right now.
        if not HAS_IPV6 and len(address) == 4:
            raise InvalidAddressFormatError("AF_INET6 not supported.")

        # Deal with INADDR_ANY and <broadcast>
        if address[0] in ('', '<broadcast>'):
            if len(address) == 4:
                return address, socket.AF_INET6, True
            else:
                return address, socket.AF_INET, True

        # If the address is a 4-tuple, require IPv6 from getaddrinfo.
        family = socket.AF_INET6 if len(address) == 4 else 0

        # Now, run getaddrinfo.
        try:
            result = socket.getaddrinfo(address[0], address[1], family, 0, 0,
                                        socket.AI_NUMERICHOST)
        except socket.error:
            # It isn't an IP address.
            if len(address) == 4:
                return address, socket.AF_INET6, False
            else:
                return address, 0, False

        # We've got an IP address. Conveniently, getaddrinfo gives us a family.
        # We only care about the first result.
        result = result[0]
        family = result[0]

        if family == socket.AF_INET6:
            if not HAS_IPV6:
                raise InvalidAddressFormatError("AF_INET6 not supported.")

            # Keep the flow control and scope id from our address.
            address = result[-1][:2] + address[2:]
        else:
            address = result[-1]

        # Now, get the family from the first position and address from the last.
        return address, family, True

    def _resolve_address(self, address, callback):
        """
        Use Pants' DNS client to asynchronously resolve the given
        address.

        ========= ===================================================
        Argument  Description
        ========= ===================================================
        address   The address to resolve.
        callback  A callable taking two mandatory arguments and one
                  optional argument. The arguments are: the resolved
                  address, the socket family and error information,
                  respectively.
        ========= ===================================================
        """
        raise NotImplementedError("pants.util.dns is currently disabled")

        # This is here to prevent an import-loop. pants.util.dns depends
        # on pants._channel. Unfortunate, but necessary.
        global dns
        if dns is None:
            from pants.util import dns

        def dns_callback(status, cname, ttl, rdata):
            if status != dns.DNS_OK:
                # DNS errored. Assume it's a bad hostname.
                callback(None, None, NAME_ERROR)
                return

            for addr in rdata:
                family = socket.AF_INET6 if ':' in addr else 0
                try:
                    result = socket.getaddrinfo(addr, address[1], family, 0, 0, socket.AI_NUMERICHOST)
                except socket.error:
                    continue

                # It's a valid host.
                result = result[0]
                callback(result[-1], result[0])
                return

            # We didn't get any valid address.
            callback(None, None, NAME_ERROR)

        # Only query records that we can use.
        if not HAS_IPV6:
            qtype = dns.A
        elif len(address) == 4:
            qtype = dns.AAAA
        else:
            qtype = (dns.AAAA, dns.A)

        dns.query(address[0], qtype, callback=dns_callback)

    ##### Internal Event Handler Methods ######################################

    def _handle_events(self, events):
        """
        Handle events raised on the channel.

        =========  ============
        Argument   Description
        =========  ============
        events     The events in the form of an integer.
        =========  ============
        """
        if self._closed:
            log.warning("Received events for closed %r." % self)
            return

        previous_events = self._events
        self._events = Engine.BASE_EVENTS

        if events & Engine.READ:
            self._handle_read_event()
            if self._closed:
                return

        if events & Engine.WRITE:
            self._handle_write_event()
            if self._closed:
                return

        if events & Engine.ERROR:
            self._handle_error_event()
            if self._closed:
                return

        if events & Engine.HANGUP:
            self._handle_hangup_event()
            if self._closed:
                return

        if self._events != previous_events:
            self.engine.modify_channel(self)

    def _handle_read_event(self):
        """
        Handle a read event raised on the channel.

        Not implemented in :class:`~pants._channel._Channel`.
        """
        raise NotImplementedError

    def _handle_write_event(self):
        """
        Handle a write event raised on the channel.

        Not implemented in :class:`~pants._channel._Channel`.
        """
        raise NotImplementedError

    def _handle_error_event(self):
        """
        Handle an error event raised on the channel.

        By default, logs the error and closes the channel.
        """
        err, errstr = self._get_socket_error()
        if err != 0:
            log.error("Socket error on %r: %s (%d)" % (self, errstr, err))
            self.close(flush=False)

    def _handle_hangup_event(self):
        """
        Handle a hangup event raised on the channel.

        By default, logs the hangup and closes the channel.
        """
        log.debug("Hang up on %r." % self)
        self.close(flush=False)


###############################################################################
# Exceptions
###############################################################################

class InvalidAddressFormatError(Exception):
    """
    Raised when an invalid address format is provided to a channel.
    """
    pass

########NEW FILE########
