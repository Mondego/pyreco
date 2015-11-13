__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# repoze.atemplate documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# The contents of this file are pickled, so don't put values in the
# namespace that aren't pickleable (module imports are okay, they're
# removed automatically).
#
# All configuration values have a default value; values that are commented
# out serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the
# directory is relative to the documentation root, use os.path.abspath to
# make it absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))


# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [ 'sphinx.ext.autodoc', 'sphinx.ext.todo' ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'pyrad'
copyright = u'2002-2009 Wichert Akkerman, 2009 Kristoffer Gronlund'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.2'
# The full version, including alpha/beta/rc tags.
release = '1.2'

# There are two options for replacing |today|: either, you set today to
# some non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be
# searched for source files.
#exclude_dirs = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'repoze.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as
# html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
html_logo = '.static/logo.png'

# The name of an image file (within the static path) to use as favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or
# 32x32 pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css".
html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

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

# If true, the reST sources are included in the HTML build as
# _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages
# will contain a <link> tag referring to it.  The value of this option must
# be the base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'euphoriecontent'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, document class [howto/manual]).
latex_documents = [
  ('index', 'euphoriecontent.tex', 'euphorie.content Documentation',
   'Simplon', 'manual'),
]

# The name of an image file (relative to this directory) to place at the
# top of the title page.
latex_logo = '.static/logo.png'

# For "manual" documents, if this is true, then toplevel headings are
# parts, not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


# Options for extras
# ------------------
todo_include_todos = True


########NEW FILE########
__FILENAME__ = acct
#!/usr/bin/python

import random, socket, sys
import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary

def SendPacket(srv, req):
    try:
        srv.SendPacket(req)
    except pyrad.client.Timeout:
        print "RADIUS server does not reply"
        sys.exit(1)
    except socket.error, error:
        print "Network error: " + error[1]
        sys.exit(1)

srv=Client(server="localhost",
           secret="Kah3choteereethiejeimaeziecumi",
           dict=Dictionary("dictionary"))

req=srv.CreateAcctPacket(User_Name="wichert")

req["NAS-IP-Address"]="192.168.1.10"
req["NAS-Port"]=0
req["NAS-Identifier"]="trillian"
req["Called-Station-Id"]="00-04-5F-00-0F-D1"
req["Calling-Station-Id"]="00-01-24-80-B3-9C"
req["Framed-IP-Address"]="10.0.0.100"

print "Sending accounting start packet"
req["Acct-Status-Type"]="Start"
SendPacket(srv, req)

print "Sending accounting stop packet"
req["Acct-Status-Type"]="Stop"
req["Acct-Input-Octets"] = random.randrange(2**10, 2**30)
req["Acct-Output-Octets"] = random.randrange(2**10, 2**30)
req["Acct-Session-Time"] = random.randrange(120, 3600)
req["Acct-Terminate-Cause"] = random.choice(["User-Request", "Idle-Timeout"])
SendPacket(srv, req)


########NEW FILE########
__FILENAME__ = auth
#!/usr/bin/python

import socket, sys
import pyrad.packet
from pyrad.client import Client
from pyrad.dictionary import Dictionary

srv=Client(server="localhost",
           secret="Kah3choteereethiejeimaeziecumi",
           dict=Dictionary("dictionary"))

req=srv.CreateAuthPacket(code=pyrad.packet.AccessRequest,
                         User_Name="wichert")

req["NAS-IP-Address"]     = "192.168.1.10"
req["NAS-Port"]           = 0
req["Service-Type"]       = "Login-User"
req["NAS-Identifier"]     = "trillian"
req["Called-Station-Id"]  = "00-04-5F-00-0F-D1"
req["Calling-Station-Id"] = "00-01-24-80-B3-9C"
req["Framed-IP-Address"]  = "10.0.0.100"

try:
    print "Sending authentication request"
    reply=srv.SendPacket(req)
except pyrad.client.Timeout:
    print "RADIUS server does not reply"
    sys.exit(1)
except socket.error, error:
    print "Network error: " + error[1]
    sys.exit(1)

if reply.code==pyrad.packet.AccessAccept:
    print "Access accepted"
else:
    print "Access denied"

print "Attributes returned by server:"
for i in reply.keys():
    print "%s: %s" % (i, reply[i])


########NEW FILE########
__FILENAME__ = server
#!/usr/bin/python

from pyrad import dictionary, packet, server

class FakeServer(server.Server):
    def _HandleAuthPacket(self, pkt):
        server.Server._HandleAuthPacket(self, pkt)

        print "Received an authentication request"
        print "Attributes: "
        for attr in pkt.keys():
            print "%s: %s" % (attr, pkt[attr])
        print

        reply=self.CreateReplyPacket(pkt)
        reply.code=packet.AccessAccept
        self.SendReplyPacket(pkt.fd, reply)

    def _HandleAcctPacket(self, pkt):
        server.Server._HandleAcctPacket(self, pkt)

        print "Received an accounting request"
        print "Attributes: "
        for attr in pkt.keys():
            print "%s: %s" % (attr, pkt[attr])
        print

        reply=self.CreateReplyPacket(pkt)
        self.SendReplyPacket(pkt.fd, reply)


srv=FakeServer(dict=dictionary.Dictionary("dictionary"))
srv.hosts["127.0.0.1"]=server.RemoteHost("127.0.0.1",
                                         "Kah3choteereethiejeimaeziecumi",
                                         "localhost")
srv.BindToAddress("")
srv.Run()

########NEW FILE########
__FILENAME__ = bidict
# bidict.py
#
# Bidirectional map


class BiDict:
    def __init__(self):
        self.forward = {}
        self.backward = {}

    def Add(self, one, two):
        self.forward[one] = two
        self.backward[two] = one

    def __len__(self):
        return len(self.forward)

    def __getitem__(self, key):
        return self.GetForward(key)

    def __delitem__(self, key):
        if key in self.forward:
            del self.backward[self.forward[key]]
            del self.forward[key]
        else:
            del self.forward[self.backward[key]]
            del self.backward[key]

    def GetForward(self, key):
        return self.forward[key]

    def HasForward(self, key):
        return key in self.forward

    def GetBackward(self, key):
        return self.backward[key]

    def HasBackward(self, key):
        return key in self.backward

########NEW FILE########
__FILENAME__ = client
# client.py
#
# Copyright 2002-2007 Wichert Akkerman <wichert@wiggy.net>

__docformat__ = "epytext en"

import select
import socket
import time
import six
from pyrad import host
from pyrad import packet


class Timeout(Exception):
    """Simple exception class which is raised when a timeout occurs
    while waiting for a RADIUS server to respond."""


class Client(host.Host):
    """Basic RADIUS client.
    This class implements a basic RADIUS client. It can send requests
    to a RADIUS server, taking care of timeouts and retries, and
    validate its replies.

    :ivar retries: number of times to retry sending a RADIUS request
    :type retries: integer
    :ivar timeout: number of seconds to wait for an answer
    :type timeout: integer
    """
    def __init__(self, server, authport=1812, acctport=1813,
            secret=six.b(''), dict=None):

        """Constructor.

        :param   server: hostname or IP address of RADIUS server
        :type    server: string
        :param authport: port to use for authentication packets
        :type  authport: integer
        :param acctport: port to use for accounting packets
        :type  acctport: integer
        :param   secret: RADIUS secret
        :type    secret: string
        :param     dict: RADIUS dictionary
        :type      dict: pyrad.dictionary.Dictionary
        """
        host.Host.__init__(self, authport, acctport, dict)

        self.server = server
        self.secret = secret
        self._socket = None
        self.retries = 3
        self.timeout = 5

    def bind(self, addr):
        """Bind socket to an address.
        Binding the socket used for communicating to an address can be
        usefull when working on a machine with multiple addresses.

        :param addr: network address (hostname or IP) and port to bind to
        :type  addr: host,port tuple
        """
        self._CloseSocket()
        self._SocketOpen()
        self._socket.bind(addr)

    def _SocketOpen(self):
        if not self._socket:
            self._socket = socket.socket(socket.AF_INET,
                                       socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET,
                                    socket.SO_REUSEADDR, 1)

    def _CloseSocket(self):
        if self._socket:
            self._socket.close()
            self._socket = None

    def CreateAuthPacket(self, **args):
        """Create a new RADIUS packet.
        This utility function creates a new RADIUS packet which can
        be used to communicate with the RADIUS server this client
        talks to. This is initializing the new packet with the
        dictionary and secret used for the client.

        :return: a new empty packet instance
        :rtype:  pyrad.packet.Packet
        """
        return host.Host.CreateAuthPacket(self, secret=self.secret, **args)

    def CreateAcctPacket(self, **args):
        """Create a new RADIUS packet.
        This utility function creates a new RADIUS packet which can
        be used to communicate with the RADIUS server this client
        talks to. This is initializing the new packet with the
        dictionary and secret used for the client.

        :return: a new empty packet instance
        :rtype:  pyrad.packet.Packet
        """
        return host.Host.CreateAcctPacket(self, secret=self.secret, **args)

    def _SendPacket(self, pkt, port):
        """Send a packet to a RADIUS server.

        :param pkt:  the packet to send
        :type pkt:   pyrad.packet.Packet
        :param port: UDP port to send packet to
        :type port:  integer
        :return:     the reply packet received
        :rtype:      pyrad.packet.Packet
        :raise Timeout: RADIUS server does not reply
        """
        self._SocketOpen()

        for attempt in range(self.retries):
            if attempt and pkt.code == packet.AccountingRequest:
                if "Acct-Delay-Time" in pkt:
                    pkt["Acct-Delay-Time"] = \
                            pkt["Acct-Delay-Time"][0] + self.timeout
                else:
                    pkt["Acct-Delay-Time"] = self.timeout
            self._socket.sendto(pkt.RequestPacket(), (self.server, port))

            now = time.time()
            waitto = now + self.timeout

            while now < waitto:
                ready = select.select([self._socket], [], [],
                                    (waitto - now))

                if ready[0]:
                    rawreply = self._socket.recv(4096)
                else:
                    now = time.time()
                    continue

                try:
                    reply = pkt.CreateReply(packet=rawreply)
                    if pkt.VerifyReply(reply, rawreply):
                        return reply
                except packet.PacketError:
                    pass

                now = time.time()

        raise Timeout

    def SendPacket(self, pkt):
        """Send a packet to a RADIUS server.

        :param pkt: the packet to send
        :type pkt:  pyrad.packet.Packet
        :return:    the reply packet received
        :rtype:     pyrad.packet.Packet
        :raise Timeout: RADIUS server does not reply
        """
        if isinstance(pkt, packet.AuthPacket):
            return self._SendPacket(pkt, self.authport)
        else:
            return self._SendPacket(pkt, self.acctport)

########NEW FILE########
__FILENAME__ = curved
# curved.py
#
# Copyright 2002 Wichert Akkerman <wichert@wiggy.net>

"""Twisted integration code
"""

__docformat__ = 'epytext en'

from twisted.internet import protocol
from twisted.internet import reactor
from twisted.python import log
import sys
from pyrad import dictionary
from pyrad import host
from pyrad import packet


class PacketError(Exception):
    """Exception class for bogus packets

    PacketError exceptions are only used inside the Server class to
    abort processing of a packet.
    """


class RADIUS(host.Host, protocol.DatagramProtocol):
    def __init__(self, hosts={}, dict=dictionary.Dictionary()):
        host.Host.__init__(self, dict=dict)
        self.hosts = hosts

    def processPacket(self, pkt):
        pass

    def createPacket(self, **kwargs):
        raise NotImplementedError('Attempted to use a pure base class')

    def datagramReceived(self, datagram, (host, port)):
        try:
            pkt = self.CreatePacket(packet=datagram)
        except packet.PacketError as err:
            log.msg('Dropping invalid packet: ' + str(err))
            return

        if host not in self.hosts:
            log.msg('Dropping packet from unknown host ' + host)
            return

        pkt.source = (host, port)
        try:
            self.processPacket(pkt)
        except PacketError as err:
            log.msg('Dropping packet from %s: %s' % (host, str(err)))


class RADIUSAccess(RADIUS):
    def createPacket(self, **kwargs):
        self.CreateAuthPacket(**kwargs)

    def processPacket(self, pkt):
        if pkt.code != packet.AccessRequest:
            raise PacketError(
                    'non-AccessRequest packet on authentication socket')


class RADIUSAccounting(RADIUS):
    def createPacket(self, **kwargs):
        self.CreateAcctPacket(**kwargs)

    def processPacket(self, pkt):
        if pkt.code != packet.AccountingRequest:
            raise PacketError(
                    'non-AccountingRequest packet on authentication socket')


if __name__ == '__main__':
    log.startLogging(sys.stdout, 0)
    reactor.listenUDP(1812, RADIUSAccess())
    reactor.listenUDP(1813, RADIUSAccounting())
    reactor.run()

########NEW FILE########
__FILENAME__ = dictfile
# dictfile.py
#
# Copyright 2009 Kristoffer Gronlund <kristoffer.gronlund@purplescout.se>

""" Dictionary File

Implements an iterable file format that handles the
RADIUS $INCLUDE directives behind the scene.
"""

import os
import six


class _Node(object):
    """Dictionary file node

    A single dictionary file.
    """
    __slots__ = ('name', 'lines', 'current', 'length', 'dir')

    def __init__(self, fd, name, parentdir):
        self.lines = fd.readlines()
        self.length = len(self.lines)
        self.current = 0
        self.name = os.path.basename(name)
        path = os.path.dirname(name)
        if os.path.isabs(path):
            self.dir = path
        else:
            self.dir = os.path.join(parentdir, path)

    def Next(self):
        if self.current >= self.length:
            return None
        self.current += 1
        return self.lines[self.current - 1]


class DictFile(object):
    """Dictionary file class

    An iterable file type that handles $INCLUDE
    directives internally.
    """
    __slots__ = ('stack')

    def __init__(self, fil):
        """
        @param fil: a dictionary file to parse
        @type fil: string or file
        """
        self.stack = []
        self.__ReadNode(fil)

    def __ReadNode(self, fil):
        node = None
        parentdir = self.__CurDir()
        if isinstance(fil, six.string_types):
            fname = None
            if os.path.isabs(fil):
                fname = fil
            else:
                fname = os.path.join(parentdir, fil)
            fd = open(fname, "rt")
            node = _Node(fd, fil, parentdir)
            fd.close()
        else:
            node = _Node(fil, '', parentdir)
        self.stack.append(node)

    def __CurDir(self):
        if self.stack:
            return self.stack[-1].dir
        else:
            return os.path.realpath(os.curdir)

    def __GetInclude(self, line):
        line = line.split("#", 1)[0].strip()
        tokens = line.split()
        if tokens and tokens[0].upper() == '$INCLUDE':
            return " ".join(tokens[1:])
        else:
            return None

    def Line(self):
        """Returns line number of current file
        """
        if self.stack:
            return self.stack[-1].current
        else:
            return -1

    def File(self):
        """Returns name of current file
        """
        if self.stack:
            return self.stack[-1].name
        else:
            return ''

    def __iter__(self):
        return self

    def __next__(self):
        while self.stack:
            line = self.stack[-1].Next()
            if line == None:
                self.stack.pop()
            else:
                inc = self.__GetInclude(line)
                if inc:
                    self.__ReadNode(inc)
                else:
                    return line
        raise StopIteration
    next = __next__  # BBB for python <3

########NEW FILE########
__FILENAME__ = dictionary
# dictionary.py
#
# Copyright 2002,2005,2007 Wichert Akkerman <wichert@wiggy.net>

"""
RADIUS uses dictionaries to define the attributes that can
be used in packets. The Dictionary class stores the attribute
definitions from one or more dictionary files.

Dictionary files are textfiles with one command per line.
Comments are specified by starting with a # character, and empty
lines are ignored.

The commands supported are::

  ATTRIBUTE <attribute> <code> <type> [<vendor>]
  specify an attribute and its type

  VALUE <attribute> <valuename> <value>
  specify a value attribute

  VENDOR <name> <id>
  specify a vendor ID

  BEGIN-VENDOR <vendorname>
  begin definition of vendor attributes

  END-VENDOR <vendorname>
  end definition of vendor attributes


The datatypes currently supported are:

=======   ======================
type      description
=======   ======================
string    ASCII string
ipaddr    IPv4 address
integer   32 bits signed number
date      32 bits UNIX timestamp
octets    arbitrary binary data
=======   ======================

These datatypes are parsed but not supported:

+------------+----------------------------------------------+
| type       | description                                  |
+============+==============================================+
| abinary    | ASCII encoded binary data                    |
+------------+----------------------------------------------+
| ifid       | 8 octets in network byte order               |
+------------+----------------------------------------------+
| ipv6addr   | 16 octets in network byte order              |
+------------+----------------------------------------------+
| ipv6prefix | 18 octets in network byte order              |
+------------+----------------------------------------------+
| ether      | 6 octets of hh:hh:hh:hh:hh:hh                |
|            | where 'h' is hex digits, upper or lowercase. |
+------------+----------------------------------------------+

"""

__docformat__ = 'epytext en'

from pyrad import bidict
from pyrad import tools
from pyrad import dictfile
from copy import copy

DATATYPES = frozenset(['string', 'ipaddr', 'integer', 'date',
                       'octets', 'abinary', 'ipv6addr',
                       'ipv6prefix', 'ifid', 'ether'])


class ParseError(Exception):
    """Dictionary parser exceptions.

    :ivar msg:        Error message
    :type msg:        string
    :ivar linenumber: Line number on which the error occured
    :type linenumber: integer
    """

    def __init__(self, msg=None, **data):
        self.msg = msg
        self.file = data.get('file', '')
        self.line = data.get('line', -1)

    def __str__(self):
        str = ''
        if self.file:
            str += self.file
        if self.line > -1:
            str += '(%d)' % self.line
        if self.file or self.line > -1:
            str += ': '
        str += 'Parse error'
        if self.msg:
            str += ': %s' % self.msg

        return str


class Attribute:
    def __init__(self, name, code, datatype, vendor='', values={},
            encrypt=0, has_tag=False):
        if datatype not in DATATYPES:
            raise ValueError('Invalid data type')
        self.name = name
        self.code = code
        self.type = datatype
        self.vendor = vendor
        self.encrypt = encrypt
        self.has_tag = has_tag
        self.values = bidict.BiDict()
        for (key, value) in values.items():
            self.values.Add(key, value)


class Dictionary(object):
    """RADIUS dictionary class.
    This class stores all information about vendors, attributes and their
    values as defined in RADIUS dictionary files.

    :ivar vendors:    bidict mapping vendor name to vendor code
    :type vendors:    bidict
    :ivar attrindex:  bidict mapping
    :type attrindex:  bidict
    :ivar attributes: bidict mapping attribute name to attribute class
    :type attributes: bidict
    """

    def __init__(self, dict=None, *dicts):
        """
        :param dict:  path of dictionary file or file-like object to read
        :type dict:   string or file
        :param dicts: list of dictionaries
        :type dicts:  sequence of strings or files
        """
        self.vendors = bidict.BiDict()
        self.vendors.Add('', 0)
        self.attrindex = bidict.BiDict()
        self.attributes = {}
        self.defer_parse = []

        if dict:
            self.ReadDictionary(dict)

        for i in dicts:
            self.ReadDictionary(i)

    def __len__(self):
        return len(self.attributes)

    def __getitem__(self, key):
        return self.attributes[key]

    def __contains__(self, key):
        return key in self.attributes

    has_key = __contains__

    def __ParseAttribute(self, state, tokens):
        if not len(tokens) in [4, 5]:
            raise ParseError(
                'Incorrect number of tokens for attribute definition',
                name=state['file'],
                line=state['line'])

        vendor = state['vendor']
        has_tag = False
        encrypt = 0
        if len(tokens) >= 5:
            def keyval(o):
                kv = o.split('=')
                if len(kv) == 2:
                    return (kv[0], kv[1])
                else:
                    return (kv[0], None)
            options = [keyval(o) for o in tokens[4].split(',')]
            for (key, val) in options:
                if key == 'has_tag':
                    has_tag = True
                elif key == 'encrypt':
                    if val not in ['1', '2', '3']:
                        raise ParseError(
                                'Illegal attribute encryption: %s' % val,
                                file=state['file'],
                                line=state['line'])
                    encrypt = int(val)

            if (not has_tag) and encrypt == 0:
                vendor = tokens[4]
                if not self.vendors.HasForward(vendor):
                    raise ParseError('Unknown vendor ' + vendor,
                                     file=state['file'],
                                     line=state['line'])

        (attribute, code, datatype) = tokens[1:4]
        code = int(code, 0)
        if not datatype in DATATYPES:
            raise ParseError('Illegal type: ' + datatype,
                             file=state['file'],
                             line=state['line'])

        if vendor:
            key = (self.vendors.GetForward(vendor), code)
        else:
            key = code

        self.attrindex.Add(attribute, key)
        self.attributes[attribute] = Attribute(attribute, code, datatype,
                vendor, encrypt=encrypt, has_tag=has_tag)

    def __ParseValue(self, state, tokens, defer):
        if len(tokens) != 4:
            raise ParseError('Incorrect number of tokens for value definition',
                             file=state['file'],
                             line=state['line'])

        (attr, key, value) = tokens[1:]

        try:
            adef = self.attributes[attr]
        except KeyError:
            if defer:
                self.defer_parse.append((copy(state), copy(tokens)))
                return
            raise ParseError('Value defined for unknown attribute ' + attr,
                             file=state['file'],
                             line=state['line'])

        if adef.type == 'integer':
            value = int(value, 0)
        value = tools.EncodeAttr(adef.type, value)
        self.attributes[attr].values.Add(key, value)

    def __ParseVendor(self, state, tokens):
        if len(tokens) not in [3, 4]:
            raise ParseError(
                    'Incorrect number of tokens for vendor definition',
                    file=state['file'],
                    line=state['line'])

        # Parse format specification, but do
        # nothing about it for now
        if len(tokens) == 4:
            fmt = tokens[3].split('=')
            if fmt[0] != 'format':
                raise ParseError(
                        "Unknown option '%s' for vendor definition" % (fmt[0]),
                        file=state['file'],
                        line=state['line'])
            try:
                (t, l) = tuple(int(a) for a in fmt[1].split(','))
                if t not in [1, 2, 4] or l not in [0, 1, 2]:
                    raise ParseError(
                        'Unknown vendor format specification %s' % (fmt[1]),
                        file=state['file'],
                        line=state['line'])
            except ValueError:
                raise ParseError(
                        'Syntax error in vendor specification',
                        file=state['file'],
                        line=state['line'])

        (vendorname, vendor) = tokens[1:3]
        self.vendors.Add(vendorname, int(vendor, 0))

    def __ParseBeginVendor(self, state, tokens):
        if len(tokens) != 2:
            raise ParseError(
                    'Incorrect number of tokens for begin-vendor statement',
                    file=state['file'],
                    line=state['line'])

        vendor = tokens[1]

        if not self.vendors.HasForward(vendor):
            raise ParseError(
                    'Unknown vendor %s in begin-vendor statement' % vendor,
                    file=state['file'],
                    line=state['line'])

        state['vendor'] = vendor

    def __ParseEndVendor(self, state, tokens):
        if len(tokens) != 2:
            raise ParseError(
                'Incorrect number of tokens for end-vendor statement',
                file=state['file'],
                line=state['line'])

        vendor = tokens[1]

        if state['vendor'] != vendor:
            raise ParseError(
                    'Ending non-open vendor' + vendor,
                    file=state['file'],
                    line=state['line'])
        state['vendor'] = ''

    def ReadDictionary(self, file):
        """Parse a dictionary file.
        Reads a RADIUS dictionary file and merges its contents into the
        class instance.

        :param file: Name of dictionary file to parse or a file-like object
        :type file:  string or file-like object
        """

        fil = dictfile.DictFile(file)

        state = {}
        state['vendor'] = ''

        self.defer_parse = []
        for line in fil:
            state['file'] = fil.File()
            state['line'] = fil.Line()
            line = line.split('#', 1)[0].strip()

            tokens = line.split()
            if not tokens:
                continue

            key = tokens[0].upper()
            if key == 'ATTRIBUTE':
                self.__ParseAttribute(state, tokens)
            elif key == 'VALUE':
                self.__ParseValue(state, tokens, True)
            elif key == 'VENDOR':
                self.__ParseVendor(state, tokens)
            elif key == 'BEGIN-VENDOR':
                self.__ParseBeginVendor(state, tokens)
            elif key == 'END-VENDOR':
                self.__ParseEndVendor(state, tokens)

        for state, tokens in self.defer_parse:
            key = tokens[0].upper()
            if key == 'VALUE':
                self.__ParseValue(state, tokens, False)
        self.defer_parse = []

########NEW FILE########
__FILENAME__ = host
# host.py
#
# Copyright 2003,2007 Wichert Akkerman <wichert@wiggy.net>

from pyrad import packet


class Host:
    """Generic RADIUS capable host.

    :ivar     dict: RADIUS dictionary
    :type     dict: pyrad.dictionary.Dictionary
    :ivar authport: port to listen on for authentication packets
    :type authport: integer
    :ivar acctport: port to listen on for accounting packets
    :type acctport: integer
    """
    def __init__(self, authport=1812, acctport=1813, dict=None):
        """Constructor

        :param authport: port to listen on for authentication packets
        :type  authport: integer
        :param acctport: port to listen on for accounting packets
        :type  acctport: integer
        :param     dict: RADIUS dictionary
        :type      dict: pyrad.dictionary.Dictionary
        """
        self.dict = dict
        self.authport = authport
        self.acctport = acctport

    def CreatePacket(self, **args):
        """Create a new RADIUS packet.
        This utility function creates a new RADIUS authentication
        packet which can be used to communicate with the RADIUS server
        this client talks to. This is initializing the new packet with
        the dictionary and secret used for the client.

        :return: a new empty packet instance
        :rtype:  pyrad.packet.Packet
        """
        return packet.Packet(dict=self.dict, **args)

    def CreateAuthPacket(self, **args):
        """Create a new authentication RADIUS packet.
        This utility function creates a new RADIUS authentication
        packet which can be used to communicate with the RADIUS server
        this client talks to. This is initializing the new packet with
        the dictionary and secret used for the client.

        :return: a new empty packet instance
        :rtype:  pyrad.packet.AuthPacket
        """
        return packet.AuthPacket(dict=self.dict, **args)

    def CreateAcctPacket(self, **args):
        """Create a new accounting RADIUS packet.
        This utility function creates a new accouting RADIUS packet
        which can be used to communicate with the RADIUS server this
        client talks to. This is initializing the new packet with the
        dictionary and secret used for the client.

        :return: a new empty packet instance
        :rtype:  pyrad.packet.AcctPacket
        """
        return packet.AcctPacket(dict=self.dict, **args)

    def SendPacket(self, fd, pkt):
        """Send a packet.

        :param fd: socket to send packet with
        :type  fd: socket class instance
        :param pkt: packet to send
        :type  pkt: Packet class instance
        """
        fd.sendto(pkt.Packet(), pkt.source)

    def SendReplyPacket(self, fd, pkt):
        """Send a packet.

        :param fd: socket to send packet with
        :type  fd: socket class instance
        :param pkt: packet to send
        :type  pkt: Packet class instance
        """
        fd.sendto(pkt.ReplyPacket(), pkt.source)

########NEW FILE########
__FILENAME__ = packet
# packet.py
#
# Copyright 2002-2005,2007 Wichert Akkerman <wichert@wiggy.net>
#
# A RADIUS packet as defined in RFC 2138


import struct
import random
try:
    import hashlib
    md5_constructor = hashlib.md5
except ImportError:
    # BBB for python 2.4
    import md5
    md5_constructor = md5.new
import six
from pyrad import tools

# Packet codes
AccessRequest = 1
AccessAccept = 2
AccessReject = 3
AccountingRequest = 4
AccountingResponse = 5
AccessChallenge = 11
StatusServer = 12
StatusClient = 13
DisconnectRequest = 40
DisconnectACK = 41
DisconnectNAK = 42
CoARequest = 43
CoAACK = 44
CoANAK = 45

# Use cryptographic-safe random generator as provided by the OS.
random_generator = random.SystemRandom()

# Current ID
CurrentID = random_generator.randrange(1, 255)


class PacketError(Exception):
    pass


class Packet(dict):
    """Packet acts like a standard python map to provide simple access
    to the RADIUS attributes. Since RADIUS allows for repeated
    attributes the value will always be a sequence. pyrad makes sure
    to preserve the ordering when encoding and decoding packets.

    There are two ways to use the map intereface: if attribute
    names are used pyrad take care of en-/decoding data. If
    the attribute type number (or a vendor ID/attribute type
    tuple for vendor attributes) is used you work with the
    raw data.

    Normally you will not use this class directly, but one of the
    :obj:`AuthPacket` or :obj:`AcctPacket` classes.
    """

    def __init__(self, code=0, id=None, secret=six.b(''), authenticator=None,
            **attributes):
        """Constructor

        :param dict:   RADIUS dictionary
        :type dict:    pyrad.dictionary.Dictionary class
        :param secret: secret needed to communicate with a RADIUS server
        :type secret:  string
        :param id:     packet identifaction number
        :type id:      integer (8 bits)
        :param code:   packet type code
        :type code:    integer (8bits)
        :param packet: raw packet to decode
        :type packet:  string
        """
        dict.__init__(self)
        self.code = code
        if id is not None:
            self.id = id
        else:
            self.id = CreateID()
        if not isinstance(secret, six.binary_type):
            raise TypeError('secret must be a binary string')
        self.secret = secret
        if authenticator is not None and \
                not isinstance(authenticator, six.binary_type):
                    raise TypeError('authenticator must be a binary string')
        self.authenticator = authenticator

        if 'dict' in attributes:
            self.dict = attributes['dict']

        if 'packet' in attributes:
            self.DecodePacket(attributes['packet'])

        for (key, value) in attributes.items():
            if key in ['dict', 'fd', 'packet']:
                continue
            key = key.replace('_', '-')
            self.AddAttribute(key, value)

    def CreateReply(self, **attributes):
        """Create a new packet as a reply to this one. This method
        makes sure the authenticator and secret are copied over
        to the new instance.
        """
        return Packet(id=self.id, secret=self.secret,
                      authenticator=self.authenticator, dict=self.dict,
                      **attributes)

    def _DecodeValue(self, attr, value):
        if attr.values.HasBackward(value):
            return attr.values.GetBackward(value)
        else:
            return tools.DecodeAttr(attr.type, value)

    def _EncodeValue(self, attr, value):
        if attr.values.HasForward(value):
            return attr.values.GetForward(value)
        else:
            return tools.EncodeAttr(attr.type, value)

    def _EncodeKeyValues(self, key, values):
        if not isinstance(key, str):
            return (key, values)

        attr = self.dict.attributes[key]
        if attr.vendor:
            key = (self.dict.vendors.GetForward(attr.vendor), attr.code)
        else:
            key = attr.code

        return (key, [self._EncodeValue(attr, v) for v in values])

    def _EncodeKey(self, key):
        if not isinstance(key, str):
            return key

        attr = self.dict.attributes[key]
        if attr.vendor:
            return (self.dict.vendors.GetForward(attr.vendor), attr.code)
        else:
            return attr.code

    def _DecodeKey(self, key):
        """Turn a key into a string if possible"""

        if self.dict.attrindex.HasBackward(key):
            return self.dict.attrindex.GetBackward(key)
        return key

    def AddAttribute(self, key, value):
        """Add an attribute to the packet.

        :param key:   attribute name or identification
        :type key:    string, attribute code or (vendor code, attribute code)
                      tuple
        :param value: value
        :type value:  depends on type of attribute
        """
        (key, value) = self._EncodeKeyValues(key, [value])
        value = value[0]

        self.setdefault(key, []).append(value)

    def __getitem__(self, key):
        if not isinstance(key, six.string_types):
            return dict.__getitem__(self, key)

        values = dict.__getitem__(self, self._EncodeKey(key))
        attr = self.dict.attributes[key]
        res = []
        for v in values:
            res.append(self._DecodeValue(attr, v))
        return res

    def __contains__(self, key):
        try:
            return dict.__contains__(self, self._EncodeKey(key))
        except KeyError:
            return False

    has_key = __contains__

    def __delitem__(self, key):
        dict.__delitem__(self, self._EncodeKey(key))

    def __setitem__(self, key, item):
        if isinstance(key, six.string_types):
            (key, item) = self._EncodeKeyValues(key, [item])
            dict.__setitem__(self, key, item)
        else:
            assert isinstance(item, list)
            dict.__setitem__(self, key, item)

    def keys(self):
        return [self._DecodeKey(key) for key in dict.keys(self)]

    @staticmethod
    def CreateAuthenticator():
        """Create a packet autenticator. All RADIUS packets contain a sixteen
        byte authenticator which is used to authenticate replies from the
        RADIUS server and in the password hiding algorithm. This function
        returns a suitable random string that can be used as an authenticator.

        :return: valid packet authenticator
        :rtype: binary string
        """

        data = []
        for i in range(16):
            data.append(random_generator.randrange(0, 256))
        if six.PY3:
            return bytes(data)
        else:
            return ''.join(chr(b) for b in data)

    def CreateID(self):
        """Create a packet ID.  All RADIUS requests have a ID which is used to
        identify a request. This is used to detect retries and replay attacks.
        This function returns a suitable random number that can be used as ID.

        :return: ID number
        :rtype:  integer

        """
        return random_generator.randrange(0, 256)

    def ReplyPacket(self):
        """Create a ready-to-transmit authentication reply packet.
        Returns a RADIUS packet which can be directly transmitted
        to a RADIUS server. This differs with Packet() in how
        the authenticator is calculated.

        :return: raw packet
        :rtype:  string
        """
        assert(self.authenticator)
        assert(self.secret is not None)

        attr = self._PktEncodeAttributes()
        header = struct.pack('!BBH', self.code, self.id, (20 + len(attr)))

        authenticator = md5_constructor(header[0:4] + self.authenticator
                              + attr + self.secret).digest()
        return header + authenticator + attr

    def VerifyReply(self, reply, rawreply=None):
        if reply.id != self.id:
            return False

        if rawreply is None:
            rawreply = reply.ReplyPacket()

        hash = md5_constructor(rawreply[0:4] + self.authenticator +
                     rawreply[20:] + self.secret).digest()

        if hash != rawreply[4:20]:
            return False
        return True

    def _PktEncodeAttribute(self, key, value):
        if isinstance(key, tuple):
            value = struct.pack('!L', key[0]) + \
                self._PktEncodeAttribute(key[1], value)
            key = 26

        return struct.pack('!BB', key, (len(value) + 2)) + value

    def _PktEncodeAttributes(self):
        result = six.b('')
        for (code, datalst) in self.items():
            for data in datalst:
                result += self._PktEncodeAttribute(code, data)

        return result

    def _PktDecodeVendorAttribute(self, data):
        # Check if this packet is long enough to be in the
        # RFC2865 recommended form
        if len(data) < 6:
            return (26, data)

        (vendor, type, length) = struct.unpack('!LBB', data[:6])[0:3]
        # Another sanity check
        if len(data) != length + 4:
            return (26, data)

        return ((vendor, type), data[6:])

    def DecodePacket(self, packet):
        """Initialize the object from raw packet data.  Decode a packet as
        received from the network and decode it.

        :param packet: raw packet
        :type packet:  string"""

        try:
            (self.code, self.id, length, self.authenticator) = \
                    struct.unpack('!BBH16s', packet[0:20])
        except struct.error:
            raise PacketError('Packet header is corrupt')
        if len(packet) != length:
            raise PacketError('Packet has invalid length')
        if length > 8192:
            raise PacketError('Packet length is too long (%d)' % length)

        self.clear()

        packet = packet[20:]
        while packet:
            try:
                (key, attrlen) = struct.unpack('!BB', packet[0:2])
            except struct.error:
                raise PacketError('Attribute header is corrupt')

            if attrlen < 2:
                raise PacketError(
                        'Attribute length is too small (%d)' % attrlen)

            value = packet[2:attrlen]
            if key == 26:
                (key, value) = self._PktDecodeVendorAttribute(value)

            self.setdefault(key, []).append(value)
            packet = packet[attrlen:]


class AuthPacket(Packet):
    def __init__(self, code=AccessRequest, id=None, secret=six.b(''),
            authenticator=None, **attributes):
        """Constructor

        :param code:   packet type code
        :type code:    integer (8bits)
        :param id:     packet identifaction number
        :type id:      integer (8 bits)
        :param secret: secret needed to communicate with a RADIUS server
        :type secret:  string

        :param dict:   RADIUS dictionary
        :type dict:    pyrad.dictionary.Dictionary class

        :param packet: raw packet to decode
        :type packet:  string
        """
        Packet.__init__(self, code, id, secret, authenticator, **attributes)

    def CreateReply(self, **attributes):
        """Create a new packet as a reply to this one. This method
        makes sure the authenticator and secret are copied over
        to the new instance.
        """
        return AuthPacket(AccessAccept, self.id,
            self.secret, self.authenticator, dict=self.dict,
            **attributes)

    def RequestPacket(self):
        """Create a ready-to-transmit authentication request packet.
        Return a RADIUS packet which can be directly transmitted
        to a RADIUS server.

        :return: raw packet
        :rtype:  string
        """
        attr = self._PktEncodeAttributes()

        if self.authenticator is None:
            self.authenticator = self.CreateAuthenticator()

        if self.id is None:
            self.id = self.CreateID()

        header = struct.pack('!BBH16s', self.code, self.id,
            (20 + len(attr)), self.authenticator)

        return header + attr

    def PwDecrypt(self, password):
        """Unobfuscate a RADIUS password. RADIUS hides passwords in packets by
        using an algorithm based on the MD5 hash of the packet authenticator
        and RADIUS secret. This function reverses the obfuscation process.

        :param password: obfuscated form of password
        :type password:  binary string
        :return:         plaintext password
        :rtype:          unicode string
        """
        buf = password
        pw = six.b('')

        last = self.authenticator
        while buf:
            hash = md5_constructor(self.secret + last).digest()
            if six.PY3:
                for i in range(16):
                    pw += bytes((hash[i] ^ buf[i],))
            else:
                for i in range(16):
                    pw += chr(ord(hash[i]) ^ ord(buf[i]))

            (last, buf) = (buf[:16], buf[16:])

        while pw.endswith(six.b('\x00')):
            pw = pw[:-1]

        return pw.decode('utf-8')

    def PwCrypt(self, password):
        """Obfuscate password.
        RADIUS hides passwords in packets by using an algorithm
        based on the MD5 hash of the packet authenticator and RADIUS
        secret. If no authenticator has been set before calling PwCrypt
        one is created automatically. Changing the authenticator after
        setting a password that has been encrypted using this function
        will not work.

        :param password: plaintext password
        :type password:  unicode stringn
        :return:         obfuscated version of the password
        :rtype:          binary string
        """
        if self.authenticator is None:
            self.authenticator = self.CreateAuthenticator()

        if isinstance(password, six.text_type):
            password = password.encode('utf-8')

        buf = password
        if len(password) % 16 != 0:
            buf += six.b('\x00') * (16 - (len(password) % 16))

        hash = md5_constructor(self.secret + self.authenticator).digest()
        result = six.b('')

        last = self.authenticator
        while buf:
            hash = md5_constructor(self.secret + last).digest()
            if six.PY3:
                for i in range(16):
                    result += bytes((hash[i] ^ buf[i],))
            else:
                for i in range(16):
                    result += chr(ord(hash[i]) ^ ord(buf[i]))

            last = result[-16:]
            buf = buf[16:]

        return result


class AcctPacket(Packet):
    """RADIUS accounting packets. This class is a specialization
    of the generic :obj:`Packet` class for accounting packets.
    """

    def __init__(self, code=AccountingRequest, id=None, secret=six.b(''),
            authenticator=None, **attributes):
        """Constructor

        :param dict:   RADIUS dictionary
        :type dict:    pyrad.dictionary.Dictionary class
        :param secret: secret needed to communicate with a RADIUS server
        :type secret:  string
        :param id:     packet identifaction number
        :type id:      integer (8 bits)
        :param code:   packet type code
        :type code:    integer (8bits)
        :param packet: raw packet to decode
        :type packet:  string
        """
        Packet.__init__(self, code, id, secret, authenticator, **attributes)
        if 'packet' in attributes:
            self.raw_packet = attributes['packet']

    def CreateReply(self, **attributes):
        """Create a new packet as a reply to this one. This method
        makes sure the authenticator and secret are copied over
        to the new instance.
        """
        return AcctPacket(AccountingResponse, self.id,
            self.secret, self.authenticator, dict=self.dict,
            **attributes)

    def VerifyAcctRequest(self):
        """Verify request authenticator.

        :return: True if verification failed else False
        :rtype: boolean
        """
        assert(self.raw_packet)
        hash = md5_constructor(self.raw_packet[0:4] + 16 * six.b('\x00') +
                self.raw_packet[20:] + self.secret).digest()
        return hash == self.authenticator

    def RequestPacket(self):
        """Create a ready-to-transmit authentication request packet.
        Return a RADIUS packet which can be directly transmitted
        to a RADIUS server.

        :return: raw packet
        :rtype:  string
        """

        attr = self._PktEncodeAttributes()

        if self.id is None:
            self.id = self.CreateID()

        header = struct.pack('!BBH', self.code, self.id, (20 + len(attr)))
        self.authenticator = md5_constructor(header[0:4] + 16 * six.b('\x00') + attr
            + self.secret).digest()
        return header + self.authenticator + attr


def CreateID():
    """Generate a packet ID.

    :return: packet ID
    :rtype:  8 bit integer
    """
    global CurrentID

    CurrentID = (CurrentID + 1) % 256
    return CurrentID

########NEW FILE########
__FILENAME__ = proxy
# proxy.py
#
# Copyright 2005,2007 Wichert Akkerman <wichert@wiggy.net>
#
# A RADIUS proxy as defined in RFC 2138

from pyrad.server import ServerPacketError
from pyrad.server import Server
from pyrad import packet
import select
import socket


class Proxy(Server):
    """Base class for RADIUS proxies.
    This class extends tha RADIUS server class with the capability to
    handle communication with other RADIUS servers as well.

    :ivar _proxyfd: network socket used to communicate with other servers
    :type _proxyfd: socket class instance
    """

    def _PrepareSockets(self):
        Server._PrepareSockets(self)
        self._proxyfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._fdmap[self._proxyfd.fileno()] = self._proxyfd
        self._poll.register(self._proxyfd.fileno(),
                (select.POLLIN | select.POLLPRI | select.POLLERR))

    def _HandleProxyPacket(self, pkt):
        """Process a packet received on the reply socket.
        If this packet should be dropped instead of processed a
        :obj:`ServerPacketError` exception should be raised. The main loop
        will drop the packet and log the reason.

        :param pkt: packet to process
        :type  pkt: Packet class instance
        """
        if pkt.source[0] not in self.hosts:
            raise ServerPacketError('Received packet from unknown host')
        pkt.secret = self.hosts[pkt.source[0]].secret

        if pkt.code not in [packet.AccessAccept, packet.AccessReject,
                packet.AccountingResponse]:
            raise ServerPacketError('Received non-response on proxy socket')

    def _ProcessInput(self, fd):
        """Process available data.
        If this packet should be dropped instead of processed a
        `ServerPacketError` exception should be raised. The main loop
        will drop the packet and log the reason.

        This function calls either :obj:`HandleAuthPacket`,
        :obj:`HandleAcctPacket` or :obj:`_HandleProxyPacket` depending on
        which socket is being processed.

        :param  fd: socket to read packet from
        :type   fd: socket class instance
        :param pkt: packet to process
        :type  pkt: Packet class instance
        """
        if fd.fileno() == self._proxyfd.fileno():
            pkt = self._GrabPacket(
                lambda data, s=self: s.CreatePacket(packet=data), fd)
            self._HandleProxyPacket(pkt)
        else:
            Server._ProcessInput(self, fd)

########NEW FILE########
__FILENAME__ = server
# server.py
#
# Copyright 2003-2004,2007 Wichert Akkerman <wichert@wiggy.net>

import select
import socket
from pyrad import host
from pyrad import packet
import logging


logger = logging.getLogger('pyrad')


class RemoteHost:
    """Remote RADIUS capable host we can talk to.
    """

    def __init__(self, address, secret, name, authport=1812, acctport=1813):
        """Constructor.

        :param   address: IP address
        :type    address: string
        :param    secret: RADIUS secret
        :type     secret: string
        :param      name: short name (used for logging only)
        :type       name: string
        :param  authport: port used for authentication packets
        :type   authport: integer
        :param  acctport: port used for accounting packets
        :type   acctport: integer
        """
        self.address = address
        self.secret = secret
        self.authport = authport
        self.acctport = acctport
        self.name = name


class ServerPacketError(Exception):
    """Exception class for bogus packets.
    ServerPacketError exceptions are only used inside the Server class to
    abort processing of a packet.
    """


class Server(host.Host):
    """Basic RADIUS server.
    This class implements the basics of a RADIUS server. It takes care
    of the details of receiving and decoding requests; processing of
    the requests should be done by overloading the appropriate methods
    in derived classes.

    :ivar  hosts: hosts who are allowed to talk to us
    :type  hosts: dictionary of Host class instances
    :ivar  _poll: poll object for network sockets
    :type  _poll: select.poll class instance
    :ivar _fdmap: map of filedescriptors to network sockets
    :type _fdmap: dictionary
    :cvar MaxPacketSize: maximum size of a RADIUS packet
    :type MaxPacketSize: integer
    """

    MaxPacketSize = 8192

    def __init__(self, addresses=[], authport=1812, acctport=1813, hosts=None,
            dict=None):
        """Constructor.

        :param addresses: IP addresses to listen on
        :type  addresses: sequence of strings
        :param  authport: port to listen on for authentication packets
        :type   authport: integer
        :param  acctport: port to listen on for accounting packets
        :type   acctport: integer
        :param     hosts: hosts who we can talk to
        :type      hosts: dictionary mapping IP to RemoteHost class instances
        :param      dict: RADIUS dictionary to use
        :type       dict: Dictionary class instance
        """
        host.Host.__init__(self, authport, acctport, dict)
        if hosts is None:
            self.hosts = {}
        else:
            self.hosts = hosts

        self.authfds = []
        self.acctfds = []

        for addr in addresses:
            self.BindToAddress(addr)

    def BindToAddress(self, addr):
        """Add an address to listen to.
        An empty string indicated you want to listen on all addresses.

        :param addr: IP address to listen on
        :type  addr: string
        """
        authfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        authfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        authfd.bind((addr, self.authport))

        acctfd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        acctfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        acctfd.bind((addr, self.acctport))

        self.authfds.append(authfd)
        self.acctfds.append(acctfd)

    def HandleAuthPacket(self, pkt):
        """Authentication packet handler.
        This is an empty function that is called when a valid
        authentication packet has been received. It can be overriden in
        derived classes to add custom behaviour.

        :param pkt: packet to process
        :type  pkt: Packet class instance
        """

    def HandleAcctPacket(self, pkt):
        """Accounting packet handler.
        This is an empty function that is called when a valid
        accounting packet has been received. It can be overriden in
        derived classes to add custom behaviour.

        :param pkt: packet to process
        :type  pkt: Packet class instance
        """

    def _HandleAuthPacket(self, pkt):
        """Process a packet received on the authentication port.
        If this packet should be dropped instead of processed a
        ServerPacketError exception should be raised. The main loop will
        drop the packet and log the reason.

        :param pkt: packet to process
        :type  pkt: Packet class instance
        """
        if pkt.source[0] not in self.hosts:
            raise ServerPacketError('Received packet from unknown host')

        pkt.secret = self.hosts[pkt.source[0]].secret
        if pkt.code != packet.AccessRequest:
            raise ServerPacketError(
                'Received non-authentication packet on authentication port')
        self.HandleAuthPacket(pkt)

    def _HandleAcctPacket(self, pkt):
        """Process a packet received on the accounting port.
        If this packet should be dropped instead of processed a
        ServerPacketError exception should be raised. The main loop will
        drop the packet and log the reason.

        :param pkt: packet to process
        :type  pkt: Packet class instance
        """
        if pkt.source[0] not in self.hosts:
            raise ServerPacketError('Received packet from unknown host')

        pkt.secret = self.hosts[pkt.source[0]].secret
        if not pkt.code in [packet.AccountingRequest,
                packet.AccountingResponse]:
            raise ServerPacketError(
                    'Received non-accounting packet on accounting port')
        self.HandleAcctPacket(pkt)

    def _GrabPacket(self, pktgen, fd):
        """Read a packet from a network connection.
        This method assumes there is data waiting for to be read.

        :param fd: socket to read packet from
        :type  fd: socket class instance
        :return: RADIUS packet
        :rtype:  Packet class instance
        """
        (data, source) = fd.recvfrom(self.MaxPacketSize)
        pkt = pktgen(data)
        pkt.source = source
        pkt.fd = fd
        return pkt

    def _PrepareSockets(self):
        """Prepare all sockets to receive packets.
        """
        for fd in self.authfds + self.acctfds:
            self._fdmap[fd.fileno()] = fd
            self._poll.register(fd.fileno(),
                    select.POLLIN | select.POLLPRI | select.POLLERR)
        self._realauthfds = list(map(lambda x: x.fileno(), self.authfds))
        self._realacctfds = list(map(lambda x: x.fileno(), self.acctfds))

    def CreateReplyPacket(self, pkt, **attributes):
        """Create a reply packet.
        Create a new packet which can be returned as a reply to a received
        packet.

        :param pkt:   original packet
        :type pkt:    Packet instance
        """
        reply = pkt.CreateReply(**attributes)
        reply.source = pkt.source
        return reply

    def _ProcessInput(self, fd):
        """Process available data.
        If this packet should be dropped instead of processed a
        PacketError exception should be raised. The main loop will
        drop the packet and log the reason.

        This function calls either HandleAuthPacket() or
        HandleAcctPacket() depending on which socket is being
        processed.

        :param  fd: socket to read packet from
        :type   fd: socket class instance
        """
        if fd.fileno() in self._realauthfds:
            pkt = self._GrabPacket(lambda data, s=self:
                    s.CreateAuthPacket(packet=data), fd)
            self._HandleAuthPacket(pkt)
        else:
            pkt = self._GrabPacket(lambda data, s=self:
                    s.CreateAcctPacket(packet=data), fd)
            self._HandleAcctPacket(pkt)

    def Run(self):
        """Main loop.
        This method is the main loop for a RADIUS server. It waits
        for packets to arrive via the network and calls other methods
        to process them.
        """
        self._poll = select.poll()
        self._fdmap = {}
        self._PrepareSockets()

        while 1:
            for (fd, event) in self._poll.poll():
                if event == select.POLLIN:
                    try:
                        fdo = self._fdmap[fd]
                        self._ProcessInput(fdo)
                    except ServerPacketError as err:
                        logger.info('Dropping packet: ' + str(err))
                    except packet.PacketError as err:
                        logger.info('Received a broken packet: ' + str(err))
                else:
                    logger.error('Unexpected event in server main loop')

########NEW FILE########
__FILENAME__ = mock
import fcntl
import os
from pyrad.packet import PacketError


class MockPacket:
    reply = object()

    def __init__(self, code, verify=False, error=False):
        self.code = code
        self.data = {}
        self.verify = verify
        self.error = error

    def CreateReply(self, packet=None):
        if self.error:
            raise PacketError
        return self.reply

    def VerifyReply(self, reply, rawreply):
        return self.verify

    def RequestPacket(self):
        return "request packet"

    def __contains__(self, key):
        return key in self.data
    has_key = __contains__

    def __setitem__(self, key, value):
        self.data[key] = [value]

    def __getitem__(self, key):
        return self.data[key]


class MockSocket:
    def __init__(self, domain, type, data=None):
        self.domain = domain
        self.type = type
        self.closed = False
        self.options = []
        self.address = None
        self.output = []

        if data is not None:
            (self.read_end, self.write_end) = os.pipe()
            fcntl.fcntl(self.write_end, fcntl.F_SETFL, os.O_NONBLOCK)
            os.write(self.write_end, data)
            self.data = data
        else:
            self.read_end = 1
            self.write_end = None

    def fileno(self):
        return self.read_end

    def bind(self, address):
        self.address = address

    def recv(self, buffer):
        return self.data[:buffer]

    def sendto(self, data, target):
        self.output.append((data, target))

    def setsockopt(self, level, opt, value):
        self.options.append((level, opt, value))

    def close(self):
        self.closed = True


class MockFinished(Exception):
    pass


class MockPoll:
    results = []

    def __init__(self):
        self.registry = []

    def register(self, fd, options):
        self.registry.append((fd, options))

    def poll(self):
        for result in self.results:
            yield result
        raise MockFinished


def origkey(klass):
    return "_originals_" + klass.__name__


def MockClassMethod(klass, name, myfunc=None):
    def func(self, *args, **kwargs):
        if not hasattr(self, "called"):
            self.called = []
        self.called.append((name, args, kwargs))

    key = origkey(klass)
    if not hasattr(klass, key):
        setattr(klass, key, {})
    getattr(klass, key)[name] = getattr(klass, name)
    if myfunc is None:
        setattr(klass, name, func)
    else:
        setattr(klass, name, myfunc)


def UnmockClassMethods(klass):
    key = origkey(klass)
    if not hasattr(klass, key):
        return
    for (name, func) in getattr(klass, key).items():
        setattr(klass, name, func)

    delattr(klass, key)


class MockFd:
    data = object()
    source = object()

    def __init__(self, fd=0):
        self.fd = fd

    def fileno(self):
        return self.fd

    def recvfrom(self, size):
        self.size = size
        return (self.data, self.source)

########NEW FILE########
__FILENAME__ = testBidict
import operator
import unittest
from pyrad.bidict import BiDict


class BiDictTests(unittest.TestCase):
    def setUp(self):
        self.bidict = BiDict()

    def testStartEmpty(self):
        self.assertEqual(len(self.bidict), 0)
        self.assertEqual(len(self.bidict.forward), 0)
        self.assertEqual(len(self.bidict.backward), 0)

    def testLength(self):
        self.assertEqual(len(self.bidict), 0)
        self.bidict.Add("from", "to")
        self.assertEqual(len(self.bidict), 1)
        del self.bidict["from"]
        self.assertEqual(len(self.bidict), 0)

    def testDeletion(self):
        self.assertRaises(KeyError, operator.delitem, self.bidict, "missing")
        self.bidict.Add("missing", "present")
        del self.bidict["missing"]

    def testBackwardDeletion(self):
        self.assertRaises(KeyError, operator.delitem, self.bidict, "missing")
        self.bidict.Add("missing", "present")
        del self.bidict["present"]
        self.assertEqual(self.bidict.HasForward("missing"), False)

    def testForwardAccess(self):
        self.bidict.Add("shake", "vanilla")
        self.bidict.Add("pie", "custard")
        self.assertEqual(self.bidict.HasForward("shake"), True)
        self.assertEqual(self.bidict.GetForward("shake"), "vanilla")
        self.assertEqual(self.bidict.HasForward("pie"), True)
        self.assertEqual(self.bidict.GetForward("pie"), "custard")
        self.assertEqual(self.bidict.HasForward("missing"), False)
        self.assertRaises(KeyError, self.bidict.GetForward, "missing")

    def testBackwardAccess(self):
        self.bidict.Add("shake", "vanilla")
        self.bidict.Add("pie", "custard")
        self.assertEqual(self.bidict.HasBackward("vanilla"), True)
        self.assertEqual(self.bidict.GetBackward("vanilla"), "shake")
        self.assertEqual(self.bidict.HasBackward("missing"), False)
        self.assertRaises(KeyError, self.bidict.GetBackward, "missing")

    def testItemAccessor(self):
        self.bidict.Add("shake", "vanilla")
        self.bidict.Add("pie", "custard")
        self.assertRaises(KeyError, operator.getitem, self.bidict, "missing")
        self.assertEquals(self.bidict["shake"], "vanilla")
        self.assertEquals(self.bidict["pie"], "custard")

########NEW FILE########
__FILENAME__ = testClient
import socket
import unittest
import six
from pyrad.client import Client
from pyrad.client import Timeout
from pyrad.packet import AuthPacket
from pyrad.packet import AcctPacket
from pyrad.packet import AccessRequest
from pyrad.packet import AccountingRequest
from pyrad.tests.mock import MockPacket
from pyrad.tests.mock import MockSocket

BIND_IP = "127.0.0.1"
BIND_PORT = 53535


class ConstructionTests(unittest.TestCase):
    def setUp(self):
        self.server = object()

    def testSimpleConstruction(self):
        client = Client(self.server)
        self.failUnless(client.server is self.server)
        self.assertEqual(client.authport, 1812)
        self.assertEqual(client.acctport, 1813)
        self.assertEqual(client.secret, six.b(''))
        self.assertEqual(client.retries, 3)
        self.assertEqual(client.timeout, 5)
        self.failUnless(client.dict is None)

    def testParameterOrder(self):
        marker = object()
        client = Client(self.server, 123, 456, "secret", marker)
        self.failUnless(client.server is self.server)
        self.assertEqual(client.authport, 123)
        self.assertEqual(client.acctport, 456)
        self.assertEqual(client.secret, "secret")
        self.failUnless(client.dict is marker)

    def testNamedParameters(self):
        marker = object()
        client = Client(server=self.server, authport=123, acctport=456,
                      secret="secret", dict=marker)
        self.failUnless(client.server is self.server)
        self.assertEqual(client.authport, 123)
        self.assertEqual(client.acctport, 456)
        self.assertEqual(client.secret, "secret")
        self.failUnless(client.dict is marker)


class SocketTests(unittest.TestCase):
    def setUp(self):
        self.server = object()
        self.client = Client(self.server)
        self.orgsocket = socket.socket
        socket.socket = MockSocket

    def tearDown(self):
        socket.socket = self.orgsocket

    def testReopen(self):
        self.client._SocketOpen()
        sock = self.client._socket
        self.client._SocketOpen()
        self.failUnless(sock is self.client._socket)

    def testBind(self):
        self.client.bind((BIND_IP, BIND_PORT))
        self.assertEqual(self.client._socket.address, (BIND_IP, BIND_PORT))
        self.assertEqual(self.client._socket.options,
                [(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)])

    def testBindClosesSocket(self):
        s = MockSocket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client._socket = s
        self.client.bind((BIND_IP, BIND_PORT))
        self.assertEqual(s.closed, True)

    def testSendPacket(self):
        def MockSend(self, pkt, port):
            self._mock_pkt = pkt
            self._mock_port = port

        _SendPacket = Client._SendPacket
        Client._SendPacket = MockSend

        self.client.SendPacket(AuthPacket())
        self.assertEqual(self.client._mock_port, self.client.authport)

        self.client.SendPacket(AcctPacket())
        self.assertEqual(self.client._mock_port, self.client.acctport)

        Client._SendPacket = _SendPacket

    def testNoRetries(self):
        self.client.retries = 0
        self.assertRaises(Timeout, self.client._SendPacket, None, None)

    def testSingleRetry(self):
        self.client.retries = 1
        self.client.timeout = 0
        packet = MockPacket(AccessRequest)
        self.assertRaises(Timeout, self.client._SendPacket, packet, 432)
        self.assertEqual(self.client._socket.output,
                [("request packet", (self.server, 432))])

    def testDoubleRetry(self):
        self.client.retries = 2
        self.client.timeout = 0
        packet = MockPacket(AccessRequest)
        self.assertRaises(Timeout, self.client._SendPacket, packet, 432)
        self.assertEqual(self.client._socket.output,
                [("request packet", (self.server, 432)),
                 ("request packet", (self.server, 432))])

    def testAuthDelay(self):
        self.client.retries = 2
        self.client.timeout = 1
        packet = MockPacket(AccessRequest)
        self.assertRaises(Timeout, self.client._SendPacket, packet, 432)
        self.failIf("Acct-Delay-Time" in packet)

    def testSingleAccountDelay(self):
        self.client.retries = 2
        self.client.timeout = 1
        packet = MockPacket(AccountingRequest)
        self.assertRaises(Timeout, self.client._SendPacket, packet, 432)
        self.assertEqual(packet["Acct-Delay-Time"], [1])

    def testDoubleAccountDelay(self):
        self.client.retries = 3
        self.client.timeout = 1
        packet = MockPacket(AccountingRequest)
        self.assertRaises(Timeout, self.client._SendPacket, packet, 432)
        self.assertEqual(packet["Acct-Delay-Time"], [2])

    def testIgnorePacketError(self):
        self.client.retries = 1
        self.client.timeout = 1
        self.client._socket = MockSocket(1, 2, six.b("valid reply"))
        packet = MockPacket(AccountingRequest, verify=True, error=True)
        self.assertRaises(Timeout, self.client._SendPacket, packet, 432)

    def testValidReply(self):
        self.client.retries = 1
        self.client.timeout = 1
        self.client._socket = MockSocket(1, 2, six.b("valid reply"))
        packet = MockPacket(AccountingRequest, verify=True)
        reply = self.client._SendPacket(packet, 432)
        self.failUnless(reply is packet.reply)

    def testInvalidReply(self):
        self.client.retries = 1
        self.client.timeout = 1
        self.client._socket = MockSocket(1, 2, six.b("invalid reply"))
        packet = MockPacket(AccountingRequest, verify=False)
        self.assertRaises(Timeout, self.client._SendPacket, packet, 432)


class OtherTests(unittest.TestCase):
    def setUp(self):
        self.server = object()
        self.client = Client(self.server, secret=six.b('zeer geheim'))

    def testCreateAuthPacket(self):
        packet = self.client.CreateAuthPacket(id=15)
        self.failUnless(isinstance(packet, AuthPacket))
        self.failUnless(packet.dict is self.client.dict)
        self.assertEqual(packet.id, 15)
        self.assertEqual(packet.secret, six.b('zeer geheim'))

    def testCreateAcctPacket(self):
        packet = self.client.CreateAcctPacket(id=15)
        self.failUnless(isinstance(packet, AcctPacket))
        self.failUnless(packet.dict is self.client.dict)
        self.assertEqual(packet.id, 15)
        self.assertEqual(packet.secret, six.b('zeer geheim'))

########NEW FILE########
__FILENAME__ = testDictionary
import unittest
import operator
import os
from six import StringIO
from pyrad.tests import home
from pyrad.dictionary import Attribute
from pyrad.dictionary import Dictionary
from pyrad.dictionary import ParseError
from pyrad.tools import DecodeAttr
from pyrad.dictfile import DictFile


class AttributeTests(unittest.TestCase):
    def testInvalidDataType(self):
        self.assertRaises(ValueError, Attribute, 'name', 'code', 'datatype')

    def testConstructionParameters(self):
        attr = Attribute('name', 'code', 'integer', 'vendor')
        self.assertEqual(attr.name, 'name')
        self.assertEqual(attr.code, 'code')
        self.assertEqual(attr.type, 'integer')
        self.assertEqual(attr.vendor, 'vendor')
        self.assertEqual(len(attr.values), 0)

    def testNamedConstructionParameters(self):
        attr = Attribute(name='name', code='code', datatype='integer',
                vendor='vendor')
        self.assertEqual(attr.name, 'name')
        self.assertEqual(attr.code, 'code')
        self.assertEqual(attr.type, 'integer')
        self.assertEqual(attr.vendor, 'vendor')
        self.assertEqual(len(attr.values), 0)

    def testValues(self):
        attr = Attribute('name', 'code', 'integer', 'vendor',
                dict(pie='custard', shake='vanilla'))
        self.assertEqual(len(attr.values), 2)
        self.assertEqual(attr.values['shake'], 'vanilla')


class DictionaryInterfaceTests(unittest.TestCase):
    def testEmptyDictionary(self):
        dict = Dictionary()
        self.assertEqual(len(dict), 0)

    def testContainment(self):
        dict = Dictionary()
        self.assertEqual('test' in dict, False)
        self.assertEqual(dict.has_key('test'), False)
        dict.attributes['test'] = 'dummy'
        self.assertEqual('test' in dict, True)
        self.assertEqual(dict.has_key('test'), True)

    def testReadonlyContainer(self):
        import six
        dict = Dictionary()
        self.assertRaises(TypeError,
                operator.setitem, dict, 'test', 'dummy')
        self.assertRaises(AttributeError,
                operator.attrgetter('clear'), dict)
        self.assertRaises(AttributeError,
                operator.attrgetter('update'), dict)


class DictionaryParsingTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(home, 'tests', 'data')
        self.dict = Dictionary(os.path.join(self.path, 'simple'))

    def testParseEmptyDictionary(self):
        dict = Dictionary(StringIO(''))
        self.assertEqual(len(dict), 0)

    def testParseMultipleDictionaries(self):
        dict = Dictionary(StringIO(''))
        self.assertEqual(len(dict), 0)
        one = StringIO('ATTRIBUTE Test-First 1 string')
        two = StringIO('ATTRIBUTE Test-Second 2 string')
        dict = Dictionary(StringIO(''), one, two)
        self.assertEqual(len(dict), 2)

    def testParseSimpleDictionary(self):
        self.assertEqual(len(self.dict), 8)
        values = [
                ('Test-String', 1, 'string'),
                ('Test-Octets', 2, 'octets'),
                ('Test-Integer', 3, 'integer'),
                ('Test-Ip-Address', 4, 'ipaddr'),
                ('Test-Ipv6-Address', 5, 'ipv6addr'),
                ('Test-If-Id', 6, 'ifid'),
                ('Test-Date', 7, 'date'),
                ('Test-Abinary', 8, 'abinary'),
                ]

        for (attr, code, type) in values:
            attr = self.dict[attr]
            self.assertEqual(attr.code, code)
            self.assertEqual(attr.type, type)

    def testAttributeTooFewColumnsError(self):
        try:
            self.dict.ReadDictionary(
                    StringIO('ATTRIBUTE Oops-Too-Few-Columns'))
        except ParseError as e:
            self.assertEqual('attribute' in str(e), True)
        else:
            self.fail()

    def testAttributeUnknownTypeError(self):
        try:
            self.dict.ReadDictionary(StringIO('ATTRIBUTE Test-Type 1 dummy'))
        except ParseError as e:
            self.assertEqual('dummy' in str(e), True)
        else:
            self.fail()

    def testAttributeUnknownVendorError(self):
        try:
            self.dict.ReadDictionary(StringIO('ATTRIBUTE Test-Type 1 Simplon'))
        except ParseError as e:
            self.assertEqual('Simplon' in str(e), True)
        else:
            self.fail()

    def testAttributeOptions(self):
        self.dict.ReadDictionary(StringIO(
            'ATTRIBUTE Option-Type 1 string has_tag,encrypt=1'))
        self.assertEqual(self.dict['Option-Type'].has_tag, True)
        self.assertEqual(self.dict['Option-Type'].encrypt, 1)

    def testAttributeEncryptionError(self):
        try:
            self.dict.ReadDictionary(StringIO(
                'ATTRIBUTE Test-Type 1 string encrypt=4'))
        except ParseError as e:
            self.assertEqual('encrypt' in str(e), True)
        else:
            self.fail()

    def testValueTooFewColumnsError(self):
        try:
            self.dict.ReadDictionary(StringIO('VALUE Oops-Too-Few-Columns'))
        except ParseError as e:
            self.assertEqual('value' in str(e), True)
        else:
            self.fail()

    def testValueForUnknownAttributeError(self):
        try:
            self.dict.ReadDictionary(StringIO(
                'VALUE Test-Attribute Test-Text 1'))
        except ParseError as e:
            self.assertEqual('unknown attribute' in str(e), True)
        else:
            self.fail()

    def testIntegerValueParsing(self):
        self.assertEqual(len(self.dict['Test-Integer'].values), 0)
        self.dict.ReadDictionary(StringIO('VALUE Test-Integer Value-Six 5'))
        self.assertEqual(len(self.dict['Test-Integer'].values), 1)
        self.assertEqual(
                DecodeAttr('integer',
                    self.dict['Test-Integer'].values['Value-Six']),
                5)

    def testStringValueParsing(self):
        self.assertEqual(len(self.dict['Test-String'].values), 0)
        self.dict.ReadDictionary(StringIO(
            'VALUE Test-String Value-Custard custardpie'))
        self.assertEqual(len(self.dict['Test-String'].values), 1)
        self.assertEqual(
                DecodeAttr('string',
                    self.dict['Test-String'].values['Value-Custard']),
                'custardpie')

    def testVenderTooFewColumnsError(self):
        try:
            self.dict.ReadDictionary(StringIO('VENDOR Simplon'))
        except ParseError as e:
            self.assertEqual('vendor' in str(e), True)
        else:
            self.fail()

    def testVendorParsing(self):
        self.assertRaises(ParseError, self.dict.ReadDictionary,
                StringIO('ATTRIBUTE Test-Type 1 integer Simplon'))
        self.dict.ReadDictionary(StringIO('VENDOR Simplon 42'))
        self.assertEqual(self.dict.vendors['Simplon'], 42)
        self.dict.ReadDictionary(StringIO(
                        'ATTRIBUTE Test-Type 1 integer Simplon'))
        self.assertEquals(self.dict.attrindex['Test-Type'], (42, 1))

    def testVendorOptionError(self):
        self.assertRaises(ParseError, self.dict.ReadDictionary,
                StringIO('ATTRIBUTE Test-Type 1 integer Simplon'))
        try:
            self.dict.ReadDictionary(StringIO('VENDOR Simplon 42 badoption'))
        except ParseError as e:
            self.assertEqual('option' in str(e), True)
        else:
            self.fail()

    def testVendorFormatError(self):
        self.assertRaises(ParseError, self.dict.ReadDictionary,
                StringIO('ATTRIBUTE Test-Type 1 integer Simplon'))
        try:
            self.dict.ReadDictionary(StringIO(
                'VENDOR Simplon 42 format=5,4'))
        except ParseError as e:
            self.assertEqual('format' in str(e), True)
        else:
            self.fail()

    def testVendorFormatSyntaxError(self):
        self.assertRaises(ParseError, self.dict.ReadDictionary,
                StringIO('ATTRIBUTE Test-Type 1 integer Simplon'))
        try:
            self.dict.ReadDictionary(StringIO(
                'VENDOR Simplon 42 format=a,1'))
        except ParseError as e:
            self.assertEqual('Syntax' in str(e), True)
        else:
            self.fail()

    def testBeginVendorTooFewColumns(self):
        try:
            self.dict.ReadDictionary(StringIO('BEGIN-VENDOR'))
        except ParseError as e:
            self.assertEqual('begin-vendor' in str(e), True)
        else:
            self.fail()

    def testBeginVendorUnknownVendor(self):
        try:
            self.dict.ReadDictionary(StringIO('BEGIN-VENDOR Simplon'))
        except ParseError as e:
            self.assertEqual('Simplon' in str(e), True)
        else:
            self.fail()

    def testBeginVendorParsing(self):
        self.dict.ReadDictionary(StringIO(
                        'VENDOR Simplon 42\n'
                        'BEGIN-VENDOR Simplon\n'
                        'ATTRIBUTE Test-Type 1 integer'))
        self.assertEquals(self.dict.attrindex['Test-Type'], (42, 1))

    def testEndVendorUnknownVendor(self):
        try:
            self.dict.ReadDictionary(StringIO('END-VENDOR'))
        except ParseError as e:
            self.assertEqual('end-vendor' in str(e), True)
        else:
            self.fail()

    def testEndVendorUnbalanced(self):
        try:
            self.dict.ReadDictionary(StringIO(
                            'VENDOR Simplon 42\n'
                            'BEGIN-VENDOR Simplon\n'
                            'END-VENDOR Oops\n'))
        except ParseError as e:
            self.assertEqual('Oops' in str(e), True)
        else:
            self.fail()

    def testEndVendorParsing(self):
        self.dict.ReadDictionary(StringIO(
                        'VENDOR Simplon 42\n'
                        'BEGIN-VENDOR Simplon\n'
                        'END-VENDOR Simplon\n'
                        'ATTRIBUTE Test-Type 1 integer'))
        self.assertEquals(self.dict.attrindex['Test-Type'], 1)

    def testInclude(self):
        try:
            self.dict.ReadDictionary(StringIO(
                    '$INCLUDE this_file_does_not_exist\n'
                    'VENDOR Simplon 42\n'
                    'BEGIN-VENDOR Simplon\n'
                    'END-VENDOR Simplon\n'
                    'ATTRIBUTE Test-Type 1 integer'))
        except IOError as e:
            self.assertEqual('this_file_does_not_exist' in str(e), True)
        else:
            self.fail()

    def testDictFilePostParse(self):
        f = DictFile(StringIO(
                'VENDOR Simplon 42\n'))
        for _ in f:
            pass
        self.assertEquals(f.File(), '')
        self.assertEquals(f.Line(), -1)

    def testDictFileParseError(self):
        tmpdict = Dictionary()
        try:
            tmpdict.ReadDictionary(os.path.join(self.path, 'dictfiletest'))
        except ParseError as e:
            self.assertEquals('dictfiletest' in str(e), True)
        else:
            self.fail()

########NEW FILE########
__FILENAME__ = testHost
import unittest
from pyrad.host import Host
from pyrad.packet import Packet
from pyrad.packet import AuthPacket
from pyrad.packet import AcctPacket


class ConstructionTests(unittest.TestCase):
    def testSimpleConstruction(self):
        host = Host()
        self.assertEqual(host.authport, 1812)
        self.assertEqual(host.acctport, 1813)

    def testParameterOrder(self):
        host = Host(123, 456, 789)
        self.assertEqual(host.authport, 123)
        self.assertEqual(host.acctport, 456)
        self.assertEqual(host.dict, 789)

    def testNamedParameters(self):
        host = Host(authport=123, acctport=456, dict=789)
        self.assertEqual(host.authport, 123)
        self.assertEqual(host.acctport, 456)
        self.assertEqual(host.dict, 789)


class PacketCreationTests(unittest.TestCase):
    def setUp(self):
        self.host = Host()

    def testCreatePacket(self):
        packet = self.host.CreatePacket(id=15)
        self.failUnless(isinstance(packet, Packet))
        self.failUnless(packet.dict is self.host.dict)
        self.assertEqual(packet.id, 15)

    def testCreateAuthPacket(self):
        packet = self.host.CreateAuthPacket(id=15)
        self.failUnless(isinstance(packet, AuthPacket))
        self.failUnless(packet.dict is self.host.dict)
        self.assertEqual(packet.id, 15)

    def testCreateAcctPacket(self):
        packet = self.host.CreateAcctPacket(id=15)
        self.failUnless(isinstance(packet, AcctPacket))
        self.failUnless(packet.dict is self.host.dict)
        self.assertEqual(packet.id, 15)


class MockPacket:
    packet = object()
    replypacket = object()
    source = object()

    def Packet(self):
        return self.packet

    def ReplyPacket(self):
        return self.replypacket


class MockFd:
    data = None
    target = None

    def sendto(self, data, target):
        self.data = data
        self.target = target


class PacketSendTest(unittest.TestCase):
    def setUp(self):
        self.host = Host()
        self.fd = MockFd()
        self.packet = MockPacket()

    def testSendPacket(self):
        self.host.SendPacket(self.fd, self.packet)
        self.failUnless(self.fd.data is self.packet.packet)
        self.failUnless(self.fd.target is self.packet.source)

    def testSendReplyPacket(self):
        self.host.SendReplyPacket(self.fd, self.packet)
        self.failUnless(self.fd.data is self.packet.replypacket)
        self.failUnless(self.fd.target is self.packet.source)

########NEW FILE########
__FILENAME__ = testPacket
import os
import unittest
import six
from pyrad import packet
from pyrad.tests import home
from pyrad.dictionary import Dictionary


class UtilityTests(unittest.TestCase):
    def testGenerateID(self):
        id = packet.CreateID()
        self.failUnless(isinstance(id, int))
        newid = packet.CreateID()
        self.assertNotEqual(id, newid)


class PacketConstructionTests(unittest.TestCase):
    klass = packet.Packet

    def setUp(self):
        self.path = os.path.join(home, 'tests', 'data')
        self.dict = Dictionary(os.path.join(self.path, 'simple'))

    def testBasicConstructor(self):
        pkt = self.klass()
        self.failUnless(isinstance(pkt.code, int))
        self.failUnless(isinstance(pkt.id, int))
        self.failUnless(isinstance(pkt.secret, six.binary_type))

    def testNamedConstructor(self):
        pkt = self.klass(code=26, id=38, secret=six.b('secret'),
                authenticator=six.b('authenticator'),
                dict='fakedict')
        self.assertEqual(pkt.code, 26)
        self.assertEqual(pkt.id, 38)
        self.assertEqual(pkt.secret, six.b('secret'))
        self.assertEqual(pkt.authenticator, six.b('authenticator'))
        self.assertEqual(pkt.dict, 'fakedict')

    def testConstructWithDictionary(self):
        pkt = self.klass(dict=self.dict)
        self.failUnless(pkt.dict is self.dict)

    def testConstructorIgnoredParameters(self):
        marker = []
        pkt = self.klass(fd=marker)
        self.failIf(getattr(pkt, 'fd', None) is marker)

    def testSecretMustBeBytestring(self):
        self.assertRaises(TypeError, self.klass, secret=six.u('secret'))

    def testConstructorWithAttributes(self):
        pkt = self.klass(dict=self.dict, Test_String='this works')
        self.assertEqual(pkt['Test-String'], ['this works'])


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(home, 'tests', 'data')
        self.dict = Dictionary(os.path.join(self.path, 'full'))
        self.packet = packet.Packet(id=0, secret=six.b('secret'),
                authenticator=six.b('01234567890ABCDEF'), dict=self.dict)

    def testCreateReply(self):
        reply = self.packet.CreateReply(Test_Integer=10)
        self.assertEqual(reply.id, self.packet.id)
        self.assertEqual(reply.secret, self.packet.secret)
        self.assertEqual(reply.authenticator, self.packet.authenticator)
        self.assertEqual(reply['Test-Integer'], [10])

    def testAttributeAccess(self):
        self.packet['Test-Integer'] = 10
        self.assertEqual(self.packet['Test-Integer'], [10])
        self.assertEqual(self.packet[3], [six.b('\x00\x00\x00\x0a')])

        self.packet['Test-String'] = 'dummy'
        self.assertEqual(self.packet['Test-String'], ['dummy'])
        self.assertEqual(self.packet[1], [six.b('dummy')])

    def testAttributeValueAccess(self):
        self.packet['Test-Integer'] = 'Three'
        self.assertEqual(self.packet['Test-Integer'], ['Three'])
        self.assertEqual(self.packet[3], [six.b('\x00\x00\x00\x03')])

    def testVendorAttributeAccess(self):
        self.packet['Simplon-Number'] = 10
        self.assertEqual(self.packet['Simplon-Number'], [10])
        self.assertEqual(self.packet[(16, 1)], [six.b('\x00\x00\x00\x0a')])

        self.packet['Simplon-Number'] = 'Four'
        self.assertEqual(self.packet['Simplon-Number'], ['Four'])
        self.assertEqual(self.packet[(16, 1)], [six.b('\x00\x00\x00\x04')])

    def testRawAttributeAccess(self):
        marker = [six.b('')]
        self.packet[1] = marker
        self.failUnless(self.packet[1] is marker)
        self.packet[(16, 1)] = marker
        self.failUnless(self.packet[(16, 1)] is marker)

    def testHasKey(self):
        self.assertEqual(self.packet.has_key('Test-String'), False)
        self.assertEqual('Test-String' in self.packet, False)
        self.packet['Test-String'] = 'dummy'
        self.assertEqual(self.packet.has_key('Test-String'), True)
        self.assertEqual(self.packet.has_key(1), True)
        self.assertEqual(1 in self.packet, True)

    def testHasKeyWithUnknownKey(self):
        self.assertEqual(self.packet.has_key('Unknown-Attribute'), False)
        self.assertEqual('Unknown-Attribute' in self.packet, False)

    def testDelItem(self):
        self.packet['Test-String'] = 'dummy'
        del self.packet['Test-String']
        self.assertEqual(self.packet.has_key('Test-String'), False)
        self.packet['Test-String'] = 'dummy'
        del self.packet[1]
        self.assertEqual(self.packet.has_key('Test-String'), False)

    def testKeys(self):
        self.assertEqual(self.packet.keys(), [])
        self.packet['Test-String'] = 'dummy'
        self.assertEqual(self.packet.keys(), ['Test-String'])
        self.packet['Test-Integer'] = 10
        self.assertEqual(self.packet.keys(), ['Test-String', 'Test-Integer'])
        dict.__setitem__(self.packet, 12345, None)
        self.assertEqual(self.packet.keys(),
                        ['Test-String', 'Test-Integer', 12345])

    def testCreateAuthenticator(self):
        a = packet.Packet.CreateAuthenticator()
        self.failUnless(isinstance(a, six.binary_type))
        self.assertEqual(len(a), 16)

        b = packet.Packet.CreateAuthenticator()
        self.assertNotEqual(a, b)

    def testGenerateID(self):
        id = self.packet.CreateID()
        self.failUnless(isinstance(id, int))
        newid = self.packet.CreateID()
        self.assertNotEqual(id, newid)

    def testReplyPacket(self):
        reply = self.packet.ReplyPacket()
        self.assertEqual(reply,
                six.b('\x00\x00\x00\x14\xb0\x5e\x4b\xfb\xcc\x1c'
                      '\x8c\x8e\xc4\x72\xac\xea\x87\x45\x63\xa7'))

    def testVerifyReply(self):
        reply = self.packet.CreateReply()
        self.assertEqual(self.packet.VerifyReply(reply), True)

        reply.id += 1
        self.assertEqual(self.packet.VerifyReply(reply), False)
        reply.id = self.packet.id

        reply.secret = six.b('different')
        self.assertEqual(self.packet.VerifyReply(reply), False)
        reply.secret = self.packet.secret

        reply.authenticator = six.b('X') * 16
        self.assertEqual(self.packet.VerifyReply(reply), False)
        reply.authenticator = self.packet.authenticator

    def testPktEncodeAttribute(self):
        encode = self.packet._PktEncodeAttribute

        # Encode a normal attribute
        self.assertEqual(
                encode(1, six.b('value')),
                six.b('\x01\x07value'))
        # Encode a vendor attribute
        self.assertEqual(
                encode((1, 2), six.b('value')),
                six.b('\x1a\x0d\x00\x00\x00\x01\x02\x07value'))

    def testPktEncodeAttributes(self):
        self.packet[1] = [six.b('value')]
        self.assertEqual(self.packet._PktEncodeAttributes(),
                six.b('\x01\x07value'))

        self.packet.clear()
        self.packet[(1, 2)] = [six.b('value')]
        self.assertEqual(self.packet._PktEncodeAttributes(),
                six.b('\x1a\x0d\x00\x00\x00\x01\x02\x07value'))

        self.packet.clear()
        self.packet[1] = [six.b('one'), six.b('two'), six.b('three')]
        self.assertEqual(self.packet._PktEncodeAttributes(),
                six.b('\x01\x05one\x01\x05two\x01\x07three'))

        self.packet.clear()
        self.packet[1] = [six.b('value')]
        self.packet[(1, 2)] = [six.b('value')]
        self.assertEqual(
                self.packet._PktEncodeAttributes(),
                six.b('\x1a\x0d\x00\x00\x00\x01\x02\x07value\x01\x07value'))

    def testPktDecodeVendorAttribute(self):
        decode = self.packet._PktDecodeVendorAttribute

        # Non-RFC2865 recommended form
        self.assertEqual(decode(six.b('')), (26, six.b('')))
        self.assertEqual(decode(six.b('12345')), (26, six.b('12345')))

        # Almost RFC2865 recommended form: bad length value
        self.assertEqual(
                decode(six.b('\x00\x00\x00\x01\x02\x06value')),
                (26, six.b('\x00\x00\x00\x01\x02\x06value')))

        # Proper RFC2865 recommended form
        self.assertEqual(
                decode(six.b('\x00\x00\x00\x01\x02\x07value')),
                ((1, 2), six.b('value')))

    def testDecodePacketWithEmptyPacket(self):
        try:
            self.packet.DecodePacket(six.b(''))
        except packet.PacketError as e:
            self.failUnless('header is corrupt' in str(e))
        else:
            self.fail()

    def testDecodePacketWithInvalidLength(self):
        try:
            self.packet.DecodePacket(six.b('\x00\x00\x00\x001234567890123456'))
        except packet.PacketError as e:
            self.failUnless('invalid length' in str(e))
        else:
            self.fail()

    def testDecodePacketWithTooBigPacket(self):
        try:
            self.packet.DecodePacket(six.b('\x00\x00\x24\x00') + (0x2400 - 4) * six.b('X'))
        except packet.PacketError as e:
            self.failUnless('too long' in str(e))
        else:
            self.fail()

    def testDecodePacketWithPartialAttributes(self):
        try:
            self.packet.DecodePacket(
                    six.b('\x01\x02\x00\x151234567890123456\x00'))
        except packet.PacketError as e:
            self.failUnless('header is corrupt' in str(e))
        else:
            self.fail()

    def testDecodePacketWithoutAttributes(self):
        self.packet.DecodePacket(six.b('\x01\x02\x00\x141234567890123456'))
        self.assertEqual(self.packet.code, 1)
        self.assertEqual(self.packet.id, 2)
        self.assertEqual(self.packet.authenticator, six.b('1234567890123456'))
        self.assertEqual(self.packet.keys(), [])

    def testDecodePacketWithBadAttribute(self):
        try:
            self.packet.DecodePacket(
                    six.b('\x01\x02\x00\x161234567890123456\x00\x01'))
        except packet.PacketError as e:
            self.failUnless('too small' in str(e))
        else:
            self.fail()

    def testDecodePacketWithEmptyAttribute(self):
        self.packet.DecodePacket(
                six.b('\x01\x02\x00\x161234567890123456\x00\x02'))
        self.assertEqual(self.packet[0], [six.b('')])

    def testDecodePacketWithAttribute(self):
        self.packet.DecodePacket(
            six.b('\x01\x02\x00\x1b1234567890123456\x00\x07value'))
        self.assertEqual(self.packet[0], [six.b('value')])

    def testDecodePacketWithMultiValuedAttribute(self):
        self.packet.DecodePacket(
            six.b('\x01\x02\x00\x1e1234567890123456\x00\x05one\x00\x05two'))
        self.assertEqual(self.packet[0], [six.b('one'), six.b('two')])

    def testDecodePacketWithTwoAttributes(self):
        self.packet.DecodePacket(
            six.b('\x01\x02\x00\x1e1234567890123456\x00\x05one\x01\x05two'))
        self.assertEqual(self.packet[0], [six.b('one')])
        self.assertEqual(self.packet[1], [six.b('two')])

    def testDecodePacketWithVendorAttribute(self):
        self.packet.DecodePacket(
                six.b('\x01\x02\x00\x1b1234567890123456\x1a\x07value'))
        self.assertEqual(self.packet[26], [six.b('value')])

    def testEncodeKeyValues(self):
        self.assertEqual(self.packet._EncodeKeyValues(1, '1234'), (1, '1234'))

    def testEncodeKey(self):
        self.assertEqual(self.packet._EncodeKey(1), 1)

    def testAddAttribute(self):
        self.packet.AddAttribute(1, 1)
        self.assertEqual(dict.__getitem__(self.packet, 1), [1])
        self.packet.AddAttribute(1, 1)
        self.assertEqual(dict.__getitem__(self.packet, 1), [1, 1])


class AuthPacketConstructionTests(PacketConstructionTests):
    klass = packet.AuthPacket

    def testConstructorDefaults(self):
        pkt = self.klass()
        self.assertEqual(pkt.code, packet.AccessRequest)


class AuthPacketTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(home, 'tests', 'data')
        self.dict = Dictionary(os.path.join(self.path, 'full'))
        self.packet = packet.AuthPacket(id=0, secret=six.b('secret'),
                authenticator=six.b('01234567890ABCDEF'), dict=self.dict)

    def testCreateReply(self):
        reply = self.packet.CreateReply(Test_Integer=10)
        self.assertEqual(reply.code, packet.AccessAccept)
        self.assertEqual(reply.id, self.packet.id)
        self.assertEqual(reply.secret, self.packet.secret)
        self.assertEqual(reply.authenticator, self.packet.authenticator)
        self.assertEqual(reply['Test-Integer'], [10])

    def testRequestPacket(self):
        self.assertEqual(self.packet.RequestPacket(),
                six.b('\x01\x00\x00\x1401234567890ABCDE'))

    def testRequestPacketCreatesAuthenticator(self):
        self.packet.authenticator = None
        self.packet.RequestPacket()
        self.failUnless(self.packet.authenticator is not None)

    def testRequestPacketCreatesID(self):
        self.packet.id = None
        self.packet.RequestPacket()
        self.failUnless(self.packet.id is not None)

    def testPwCryptEmptyPassword(self):
        self.assertEqual(self.packet.PwCrypt(''), six.b(''))

    def testPwCryptPassword(self):
        self.assertEqual(self.packet.PwCrypt('Simplon'),
                six.b('\xd3U;\xb23\r\x11\xba\x07\xe3\xa8*\xa8x\x14\x01'))

    def testPwCryptSetsAuthenticator(self):
        self.packet.authenticator = None
        self.packet.PwCrypt(six.u(''))
        self.failUnless(self.packet.authenticator is not None)

    def testPwDecryptEmptyPassword(self):
        self.assertEqual(self.packet.PwDecrypt(six.b('')), six.u(''))

    def testPwDecryptPassword(self):
        self.assertEqual(self.packet.PwDecrypt(
                six.b('\xd3U;\xb23\r\x11\xba\x07\xe3\xa8*\xa8x\x14\x01')),
                six.u('Simplon'))


class AcctPacketConstructionTests(PacketConstructionTests):
    klass = packet.AcctPacket

    def testConstructorDefaults(self):
        pkt = self.klass()
        self.assertEqual(pkt.code, packet.AccountingRequest)

    def testConstructorRawPacket(self):
        raw = six.b('\x00\x00\x00\x14\xb0\x5e\x4b\xfb\xcc\x1c' \
                    '\x8c\x8e\xc4\x72\xac\xea\x87\x45\x63\xa7')
        pkt = self.klass(packet=raw)
        self.assertEqual(pkt.raw_packet, raw)


class AcctPacketTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(home, 'tests', 'data')
        self.dict = Dictionary(os.path.join(self.path, 'full'))
        self.packet = packet.AcctPacket(id=0, secret=six.b('secret'),
                authenticator=six.b('01234567890ABCDEF'), dict=self.dict)

    def testCreateReply(self):
        reply = self.packet.CreateReply(Test_Integer=10)
        self.assertEqual(reply.code, packet.AccountingResponse)
        self.assertEqual(reply.id, self.packet.id)
        self.assertEqual(reply.secret, self.packet.secret)
        self.assertEqual(reply.authenticator, self.packet.authenticator)
        self.assertEqual(reply['Test-Integer'], [10])

    def testVerifyAcctRequest(self):
        rawpacket = self.packet.RequestPacket()
        pkt = packet.AcctPacket(secret=six.b('secret'), packet=rawpacket)
        self.assertEqual(pkt.VerifyAcctRequest(), True)

        pkt.secret = six.b('different')
        self.assertEqual(pkt.VerifyAcctRequest(), False)
        pkt.secret = six.b('secret')

        pkt.raw_packet = six.b('X') + pkt.raw_packet[1:]
        self.assertEqual(pkt.VerifyAcctRequest(), False)

    def testRequestPacket(self):
        self.assertEqual(self.packet.RequestPacket(),
            six.b('\x04\x00\x00\x14\x95\xdf\x90\xccbn\xfb\x15G!\x13\xea\xfa>6\x0f'))

    def testRequestPacketSetsId(self):
        self.packet.id = None
        self.packet.RequestPacket()
        self.failUnless(self.packet.id is not None)

########NEW FILE########
__FILENAME__ = testProxy
import select
import socket
import unittest
from pyrad.proxy import Proxy
from pyrad.packet import AccessAccept
from pyrad.packet import AccessRequest
from pyrad.server import ServerPacketError
from pyrad.server import Server
from pyrad.tests.mock import MockFd
from pyrad.tests.mock import MockPoll
from pyrad.tests.mock import MockSocket
from pyrad.tests.mock import MockClassMethod
from pyrad.tests.mock import UnmockClassMethods


class TrivialObject:
    """dummy object"""


class SocketTests(unittest.TestCase):
    def setUp(self):
        self.orgsocket = socket.socket
        socket.socket = MockSocket
        self.proxy = Proxy()
        self.proxy._fdmap = {}

    def tearDown(self):
        socket.socket = self.orgsocket

    def testProxyFd(self):
        self.proxy._poll = MockPoll()
        self.proxy._PrepareSockets()
        self.failUnless(isinstance(self.proxy._proxyfd, MockSocket))
        self.assertEqual(list(self.proxy._fdmap.keys()), [1])
        self.assertEqual(self.proxy._poll.registry,
                [(1, select.POLLIN | select.POLLPRI | select.POLLERR)])


class ProxyPacketHandlingTests(unittest.TestCase):
    def setUp(self):
        self.proxy = Proxy()
        self.proxy.hosts['host'] = TrivialObject()
        self.proxy.hosts['host'].secret = 'supersecret'
        self.packet = TrivialObject()
        self.packet.code = AccessAccept
        self.packet.source = ('host', 'port')

    def testHandleProxyPacketUnknownHost(self):
        self.packet.source = ('stranger', 'port')
        try:
            self.proxy._HandleProxyPacket(self.packet)
        except ServerPacketError as e:
            self.failUnless('unknown host' in str(e))
        else:
            self.fail()

    def testHandleProxyPacketSetsSecret(self):
        self.proxy._HandleProxyPacket(self.packet)
        self.assertEqual(self.packet.secret, 'supersecret')

    def testHandleProxyPacketHandlesWrongPacket(self):
        self.packet.code = AccessRequest
        try:
            self.proxy._HandleProxyPacket(self.packet)
        except ServerPacketError as e:
            self.failUnless('non-response' in str(e))
        else:
            self.fail()


class OtherTests(unittest.TestCase):
    def setUp(self):
        self.proxy = Proxy()
        self.proxy._proxyfd = MockFd()

    def tearDown(self):
        UnmockClassMethods(Proxy)
        UnmockClassMethods(Server)

    def testProcessInputNonProxyPort(self):
        fd = MockFd(fd=111)
        MockClassMethod(Server, '_ProcessInput')
        self.proxy._ProcessInput(fd)
        self.assertEqual(self.proxy.called,
                [('_ProcessInput', (fd,), {})])

    def testProcessInput(self):
        MockClassMethod(Proxy, '_GrabPacket')
        MockClassMethod(Proxy, '_HandleProxyPacket')
        self.proxy._ProcessInput(self.proxy._proxyfd)
        self.assertEqual([x[0] for x in self.proxy.called],
                ['_GrabPacket', '_HandleProxyPacket'])


if not hasattr(select, 'poll'):
    del SocketTests

########NEW FILE########
__FILENAME__ = testServer
import select
import socket
import unittest
from pyrad.packet import PacketError
from pyrad.server import RemoteHost
from pyrad.server import Server
from pyrad.server import ServerPacketError
from pyrad.tests.mock import MockFinished
from pyrad.tests.mock import MockFd
from pyrad.tests.mock import MockPoll
from pyrad.tests.mock import MockSocket
from pyrad.tests.mock import MockClassMethod
from pyrad.tests.mock import UnmockClassMethods
from pyrad.packet import AccessRequest
from pyrad.packet import AccountingRequest


class TrivialObject:
    """dummy objec"""


class RemoteHostTests(unittest.TestCase):
    def testSimpleConstruction(self):
        host = RemoteHost('address', 'secret', 'name', 'authport', 'acctport')
        self.assertEqual(host.address, 'address')
        self.assertEqual(host.secret, 'secret')
        self.assertEqual(host.name, 'name')
        self.assertEqual(host.authport, 'authport')
        self.assertEqual(host.acctport, 'acctport')

    def testNamedConstruction(self):
        host = RemoteHost(address='address', secret='secret', name='name',
               authport='authport', acctport='acctport')
        self.assertEqual(host.address, 'address')
        self.assertEqual(host.secret, 'secret')
        self.assertEqual(host.name, 'name')
        self.assertEqual(host.authport, 'authport')
        self.assertEqual(host.acctport, 'acctport')


class ServerConstructiontests(unittest.TestCase):
    def testSimpleConstruction(self):
        server = Server()
        self.assertEqual(server.authfds, [])
        self.assertEqual(server.acctfds, [])
        self.assertEqual(server.authport, 1812)
        self.assertEqual(server.acctport, 1813)
        self.assertEqual(server.hosts, {})

    def testParameterOrder(self):
        server = Server([], 'authport', 'acctport', 'hosts', 'dict')
        self.assertEqual(server.authfds, [])
        self.assertEqual(server.acctfds, [])
        self.assertEqual(server.authport, 'authport')
        self.assertEqual(server.acctport, 'acctport')
        self.assertEqual(server.dict, 'dict')

    def testBindDuringConstruction(self):
        def BindToAddress(self, addr):
            self.bound.append(addr)
        bta = Server.BindToAddress
        Server.BindToAddress = BindToAddress

        Server.bound = []
        server = Server(['one', 'two', 'three'])
        self.assertEqual(server.bound, ['one', 'two', 'three'])
        del Server.bound

        Server.BindToAddress = bta


class SocketTests(unittest.TestCase):
    def setUp(self):
        self.orgsocket = socket.socket
        socket.socket = MockSocket
        self.server = Server()

    def tearDown(self):
        socket.socket = self.orgsocket

    def testBind(self):
        self.server.BindToAddress('192.168.13.13')
        self.assertEqual(len(self.server.authfds), 1)
        self.assertEqual(self.server.authfds[0].address,
                ('192.168.13.13', 1812))

        self.assertEqual(len(self.server.acctfds), 1)
        self.assertEqual(self.server.acctfds[0].address,
                ('192.168.13.13', 1813))

    def testGrabPacket(self):
        def gen(data):
            res = TrivialObject()
            res.data = data
            return res

        fd = MockFd()
        fd.source = object()
        pkt = self.server._GrabPacket(gen, fd)
        self.failUnless(isinstance(pkt, TrivialObject))
        self.failUnless(pkt.fd is fd)
        self.failUnless(pkt.source is fd.source)
        self.failUnless(pkt.data is fd.data)

    def testPrepareSocketNoFds(self):
        self.server._poll = MockPoll()
        self.server._PrepareSockets()

        self.assertEqual(self.server._poll.registry, [])
        self.assertEqual(self.server._realauthfds, [])
        self.assertEqual(self.server._realacctfds, [])

    def testPrepareSocketAuthFds(self):
        self.server._poll = MockPoll()
        self.server._fdmap = {}
        self.server.authfds = [MockFd(12), MockFd(14)]
        self.server._PrepareSockets()

        self.assertEqual(list(self.server._fdmap.keys()), [12, 14])
        self.assertEqual(self.server._poll.registry,
                [(12, select.POLLIN | select.POLLPRI | select.POLLERR),
                 (14, select.POLLIN | select.POLLPRI | select.POLLERR)])

    def testPrepareSocketAcctFds(self):
        self.server._poll = MockPoll()
        self.server._fdmap = {}
        self.server.acctfds = [MockFd(12), MockFd(14)]
        self.server._PrepareSockets()

        self.assertEqual(list(self.server._fdmap.keys()), [12, 14])
        self.assertEqual(self.server._poll.registry,
                [(12, select.POLLIN | select.POLLPRI | select.POLLERR),
                 (14, select.POLLIN | select.POLLPRI | select.POLLERR)])


class AuthPacketHandlingTests(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.server.hosts['host'] = TrivialObject()
        self.server.hosts['host'].secret = 'supersecret'
        self.packet = TrivialObject()
        self.packet.code = AccessRequest
        self.packet.source = ('host', 'port')

    def testHandleAuthPacketUnknownHost(self):
        self.packet.source = ('stranger', 'port')
        try:
            self.server._HandleAuthPacket(self.packet)
        except ServerPacketError as e:
            self.failUnless('unknown host' in str(e))
        else:
            self.fail()

    def testHandleAuthPacketWrongPort(self):
        self.packet.code = AccountingRequest
        try:
            self.server._HandleAuthPacket(self.packet)
        except ServerPacketError as e:
            self.failUnless('port' in str(e))
        else:
            self.fail()

    def testHandleAuthPacket(self):
        def HandleAuthPacket(self, pkt):
            self.handled = pkt
        hap = Server.HandleAuthPacket
        Server.HandleAuthPacket = HandleAuthPacket

        self.server._HandleAuthPacket(self.packet)
        self.failUnless(self.server.handled is self.packet)

        Server.HandleAuthPacket = hap


class AcctPacketHandlingTests(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.server.hosts['host'] = TrivialObject()
        self.server.hosts['host'].secret = 'supersecret'
        self.packet = TrivialObject()
        self.packet.code = AccountingRequest
        self.packet.source = ('host', 'port')

    def testHandleAcctPacketUnknownHost(self):
        self.packet.source = ('stranger', 'port')
        try:
            self.server._HandleAcctPacket(self.packet)
        except ServerPacketError as e:
            self.failUnless('unknown host' in str(e))
        else:
            self.fail()

    def testHandleAcctPacketWrongPort(self):
        self.packet.code = AccessRequest
        try:
            self.server._HandleAcctPacket(self.packet)
        except ServerPacketError as e:
            self.failUnless('port' in str(e))
        else:
            self.fail()

    def testHandleAcctPacket(self):
        def HandleAcctPacket(self, pkt):
            self.handled = pkt
        hap = Server.HandleAcctPacket
        Server.HandleAcctPacket = HandleAcctPacket

        self.server._HandleAcctPacket(self.packet)
        self.failUnless(self.server.handled is self.packet)

        Server.HandleAcctPacket = hap


class OtherTests(unittest.TestCase):
    def setUp(self):
        self.server = Server()

    def tearDown(self):
        UnmockClassMethods(Server)

    def testCreateReplyPacket(self):
        class TrivialPacket:
            source = object()

            def CreateReply(self, **kw):
                reply = TrivialObject()
                reply.kw = kw
                return reply

        reply = self.server.CreateReplyPacket(TrivialPacket(),
                one='one', two='two')
        self.failUnless(isinstance(reply, TrivialObject))
        self.failUnless(reply.source is TrivialPacket.source)
        self.assertEqual(reply.kw, dict(one='one', two='two'))

    def testAuthProcessInput(self):
        fd = MockFd(1)
        self.server._realauthfds = [1]
        MockClassMethod(Server, '_GrabPacket')
        MockClassMethod(Server, '_HandleAuthPacket')

        self.server._ProcessInput(fd)
        self.assertEqual([x[0] for x in self.server.called],
                ['_GrabPacket', '_HandleAuthPacket'])
        self.assertEqual(self.server.called[0][1][1], fd)

    def testAcctProcessInput(self):
        fd = MockFd(1)
        self.server._realauthfds = []
        self.server._realacctfds = [1]
        MockClassMethod(Server, '_GrabPacket')
        MockClassMethod(Server, '_HandleAcctPacket')

        self.server._ProcessInput(fd)
        self.assertEqual([x[0] for x in self.server.called],
                ['_GrabPacket', '_HandleAcctPacket'])
        self.assertEqual(self.server.called[0][1][1], fd)


class ServerRunTests(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.origpoll = select.poll
        select.poll = MockPoll

    def tearDown(self):
        MockPoll.results = []
        select.poll = self.origpoll
        UnmockClassMethods(Server)

    def testRunInitializes(self):
        MockClassMethod(Server, '_PrepareSockets')
        self.assertRaises(MockFinished, self.server.Run)
        self.assertEqual(self.server.called, [('_PrepareSockets', (), {})])
        self.failUnless(isinstance(self.server._fdmap, dict))
        self.failUnless(isinstance(self.server._poll, MockPoll))

    def testRunIgnoresPollErrors(self):
        self.server.authfds = [MockFd()]
        MockPoll.results = [(0, select.POLLERR)]
        self.assertRaises(MockFinished, self.server.Run)

    def testRunIgnoresServerPacketErrors(self):
        def RaisePacketError(self, fd):
            raise ServerPacketError
        MockClassMethod(Server, '_ProcessInput', RaisePacketError)
        self.server.authfds = [MockFd()]
        MockPoll.results = [(0, select.POLLIN)]
        self.assertRaises(MockFinished, self.server.Run)

    def testRunIgnoresPacketErrors(self):
        def RaisePacketError(self, fd):
            raise PacketError
        MockClassMethod(Server, '_ProcessInput', RaisePacketError)
        self.server.authfds = [MockFd()]
        MockPoll.results = [(0, select.POLLIN)]
        self.assertRaises(MockFinished, self.server.Run)

    def testRunRunsProcessInput(self):
        MockClassMethod(Server, '_ProcessInput')
        self.server.authfds = fd = [MockFd()]
        MockPoll.results = [(0, select.POLLIN)]
        self.assertRaises(MockFinished, self.server.Run)
        self.assertEqual(self.server.called, [('_ProcessInput', (fd[0],), {})])

if not hasattr(select, 'poll'):
    del SocketTests
    del ServerRunTests

########NEW FILE########
__FILENAME__ = testTools
import unittest
import six
from pyrad import tools


class EncodingTests(unittest.TestCase):
    def testStringEncoding(self):
        self.assertRaises(ValueError, tools.EncodeString, 'x' * 254)
        self.assertEqual(
                tools.EncodeString('1234567890'),
                six.b('1234567890'))

    def testInvalidStringEncodingRaisesTypeError(self):
        self.assertRaises(TypeError, tools.EncodeString, 1)

    def testAddressEncoding(self):
        self.assertRaises(ValueError, tools.EncodeAddress, '123')
        self.assertEqual(
                tools.EncodeAddress('192.168.0.255'),
                six.b('\xc0\xa8\x00\xff'))

    def testInvalidAddressEncodingRaisesTypeError(self):
        self.assertRaises(TypeError, tools.EncodeAddress, 1)

    def testIntegerEncoding(self):
        self.assertEqual(tools.EncodeInteger(0x01020304),
                six.b('\x01\x02\x03\x04'))

    def testUnsignedIntegerEncoding(self):
        self.assertEqual(tools.EncodeInteger(0xFFFFFFFF),
                six.b('\xff\xff\xff\xff'))

    def testInvalidIntegerEncodingRaisesTypeError(self):
        self.assertRaises(TypeError, tools.EncodeInteger, '1')

    def testDateEncoding(self):
        self.assertEqual(tools.EncodeDate(0x01020304),
                six.b('\x01\x02\x03\x04'))

    def testInvalidDataEncodingRaisesTypeError(self):
        self.assertRaises(TypeError, tools.EncodeDate, '1')

    def testStringDecoding(self):
        self.assertEqual(
                tools.DecodeString(six.b('1234567890')),
                '1234567890')

    def testAddressDecoding(self):
        self.assertEqual(
                tools.DecodeAddress(six.b('\xc0\xa8\x00\xff')),
                '192.168.0.255')

    def testIntegerDecoding(self):
        self.assertEqual(
                tools.DecodeInteger(six.b('\x01\x02\x03\x04')),
                0x01020304)

    def testDateDecoding(self):
        self.assertEqual(
                tools.DecodeDate(six.b('\x01\x02\x03\x04')),
                0x01020304)

    def testUnknownTypeEncoding(self):
        self.assertRaises(ValueError, tools.EncodeAttr, 'unknown', None)

    def testUnknownTypeDecoding(self):
        self.assertRaises(ValueError, tools.DecodeAttr, 'unknown', None)

    def testEncodeFunction(self):
        self.assertEqual(
                tools.EncodeAttr('string', six.u('string')),
                six.b('string'))
        self.assertEqual(
                tools.EncodeAttr('octets', six.b('string')),
                six.b('string'))
        self.assertEqual(
                tools.EncodeAttr('ipaddr', '192.168.0.255'),
                six.b('\xc0\xa8\x00\xff'))
        self.assertEqual(
                tools.EncodeAttr('integer', 0x01020304),
                six.b('\x01\x02\x03\x04'))
        self.assertEqual(
                tools.EncodeAttr('date', 0x01020304),
                six.b('\x01\x02\x03\x04'))

    def testDecodeFunction(self):
        self.assertEqual(
                tools.DecodeAttr('string', six.b('string')),
                six.u('string'))
        self.assertEqual(
                tools.EncodeAttr('octets', six.b('string')),
                six.b('string'))
        self.assertEqual(
                tools.DecodeAttr('ipaddr', six.b('\xc0\xa8\x00\xff')),
                '192.168.0.255')
        self.assertEqual(
                tools.DecodeAttr('integer', six.b('\x01\x02\x03\x04')),
                0x01020304)
        self.assertEqual(
                tools.DecodeAttr('date', six.b('\x01\x02\x03\x04')),
                0x01020304)

########NEW FILE########
__FILENAME__ = tools
# tools.py
#
# Utility functions
import struct
import six


def EncodeString(str):
    if len(str) > 253:
        raise ValueError('Can only encode strings of <= 253 characters')
    if isinstance(str, six.text_type):
        return str.encode('utf-8')
    else:
        return str


def EncodeOctets(str):
    if len(str) > 253:
        raise ValueError('Can only encode strings of <= 253 characters')
    return str


def EncodeAddress(addr):
    if not isinstance(addr, six.string_types):
        raise TypeError('Address has to be a string')
    (a, b, c, d) = map(int, addr.split('.'))
    return struct.pack('BBBB', a, b, c, d)


def EncodeInteger(num):
    if not isinstance(num, six.integer_types):
        raise TypeError('Can not encode non-integer as integer')
    return struct.pack('!I', num)


def EncodeDate(num):
    if not isinstance(num, int):
        raise TypeError('Can not encode non-integer as date')
    return struct.pack('!I', num)


def DecodeString(str):
    return str.decode('utf-8')


def DecodeOctets(str):
    return str


def DecodeAddress(addr):
    return '.'.join(map(str, struct.unpack('BBBB', addr)))


def DecodeInteger(num):
    return (struct.unpack('!I', num))[0]


def DecodeDate(num):
    return (struct.unpack('!I', num))[0]


def EncodeAttr(datatype, value):
    if datatype == 'string':
        return EncodeString(value)
    elif datatype == 'octets':
        return EncodeOctets(value)
    elif datatype == 'ipaddr':
        return EncodeAddress(value)
    elif datatype == 'integer':
        return EncodeInteger(value)
    elif datatype == 'date':
        return EncodeDate(value)
    else:
        raise ValueError('Unknown attribute type %s' % datatype)


def DecodeAttr(datatype, value):
    if datatype == 'string':
        return DecodeString(value)
    elif datatype == 'octets':
        return DecodeOctets(value)
    elif datatype == 'ipaddr':
        return DecodeAddress(value)
    elif datatype == 'integer':
        return DecodeInteger(value)
    elif datatype == 'date':
        return DecodeDate(value)
    else:
        raise ValueError('Unknown attribute type %s' % datatype)

########NEW FILE########
