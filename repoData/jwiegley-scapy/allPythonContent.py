__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Scapy documentation build configuration file, created by
# sphinx-quickstart on Mon Sep  8 19:37:39 2008.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# The contents of this file are pickled, so don't put values in the namespace
# that aren't pickleable (module imports are okay, they're removed automatically).
#
# All configuration values have a default value; values that are commented out
# serve to show the default value.

import sys, os

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use os.path.abspath to make it
# absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'Scapy'
copyright = '2008, 2009 Philippe Biondi and the Scapy community'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '2.1.1'
# The full version, including alpha/beta/rc tags.
release = '2.1.1-dev'

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directories, that shouldn't be searched
# for source files.
#exclude_dirs = []

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


# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
html_style = 'default.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
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
html_use_modindex = False

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Scapydoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
latex_paper_size = 'a4'

# The font size ('10pt', '11pt' or '12pt').
latex_font_size = '11pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, document class [howto/manual]).
latex_documents = [
  ('index', 'Scapy.tex', 'Scapy Documentation',
   'Philippe Biondi and the Scapy community', 'manual'),
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
latex_use_modindex = False

########NEW FILE########
__FILENAME__ = all
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Aggregate top level objects from all Scapy modules.
"""

from base_classes import *
from config import *
from dadict import *
from data import *
from error import *
from themes import *
from arch import *

from plist import *
from fields import *
from packet import *
from asn1fields import *
from asn1packet import *

from utils import *
from route import *
if conf.ipv6_enabled:
    from utils6 import *
    from route6 import *
from sendrecv import *
from supersocket import *
from volatile import *
from as_resolvers import *

from ansmachine import *
from automaton import *
from autorun import *

from main import *

from layers.all import *

from asn1.asn1 import *
from asn1.ber import *
from asn1.mib import *

from crypto import *

########NEW FILE########
__FILENAME__ = ansmachine
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Answering machines.
"""

########################
## Answering machines ##
########################

from sendrecv import send,sendp,sniff
from config import conf
from error import log_interactive

class ReferenceAM(type):
    def __new__(cls, name, bases, dct):
        o = super(ReferenceAM, cls).__new__(cls, name, bases, dct)
        if o.function_name:
            globals()[o.function_name] = lambda o=o,*args,**kargs: o(*args,**kargs)()
        return o


class AnsweringMachine(object):
    __metaclass__ = ReferenceAM
    function_name = ""
    filter = None
    sniff_options = { "store":0 }
    sniff_options_list = [ "store", "iface", "count", "promisc", "filter", "type", "prn", "stop_filter" ]
    send_options = { "verbose":0 }
    send_options_list = ["iface", "inter", "loop", "verbose"]
    send_function = staticmethod(send)
    
    
    def __init__(self, **kargs):
        self.mode = 0
        if self.filter:
            kargs.setdefault("filter",self.filter)
        kargs.setdefault("prn", self.reply)
        self.optam1 = {}
        self.optam2 = {}
        self.optam0 = {}
        doptsend,doptsniff = self.parse_all_options(1, kargs)
        self.defoptsend = self.send_options.copy()
        self.defoptsend.update(doptsend)
        self.defoptsniff = self.sniff_options.copy()
        self.defoptsniff.update(doptsniff)
        self.optsend,self.optsniff = [{},{}]

    def __getattr__(self, attr):
        for d in [self.optam2, self.optam1]:
            if attr in d:
                return d[attr]
        raise AttributeError,attr
                
    def __setattr__(self, attr, val):
        mode = self.__dict__.get("mode",0)
        if mode == 0:
            self.__dict__[attr] = val
        else:
            [self.optam1, self.optam2][mode-1][attr] = val

    def parse_options(self):
        pass

    def parse_all_options(self, mode, kargs):
        sniffopt = {}
        sendopt = {}
        for k in kargs.keys():            
            if k in self.sniff_options_list:
                sniffopt[k] = kargs[k]
            if k in self.send_options_list:
                sendopt[k] = kargs[k]
            if k in self.sniff_options_list+self.send_options_list:
                del(kargs[k])
        if mode != 2 or kargs:
            if mode == 1:
                self.optam0 = kargs
            elif mode == 2 and kargs:
                k = self.optam0.copy()
                k.update(kargs)
                self.parse_options(**k)
                kargs = k 
            omode = self.__dict__.get("mode",0)
            self.__dict__["mode"] = mode
            self.parse_options(**kargs)
            self.__dict__["mode"] = omode
        return sendopt,sniffopt

    def is_request(self, req):
        return 1

    def make_reply(self, req):
        return req

    def send_reply(self, reply):
        self.send_function(reply, **self.optsend)

    def print_reply(self, req, reply):
        print "%s ==> %s" % (req.summary(),reply.summary())

    def reply(self, pkt):
        if not self.is_request(pkt):
            return
        reply = self.make_reply(pkt)
        self.send_reply(reply)
        if conf.verb >= 0:
            self.print_reply(pkt, reply)

    def run(self, *args, **kargs):
        log_interactive.warning("run() method deprecated. The intance is now callable")
        self(*args,**kargs)

    def __call__(self, *args, **kargs):
        optsend,optsniff = self.parse_all_options(2,kargs)
        self.optsend=self.defoptsend.copy()
        self.optsend.update(optsend)
        self.optsniff=self.defoptsniff.copy()
        self.optsniff.update(optsniff)

        try:
            self.sniff()
        except KeyboardInterrupt:
            print "Interrupted by user"
        
    def sniff(self):
        sniff(**self.optsniff)


########NEW FILE########
__FILENAME__ = bsd
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Support for BSD-like operating systems such as FreeBSD, OpenBSD and Mac OS X.
"""

LOOPBACK_NAME="lo0"

from unix import *

########NEW FILE########
__FILENAME__ = linux
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Linux specific functions.
"""

from __future__ import with_statement
import sys,os,struct,socket,time
from select import select
from fcntl import ioctl
import scapy.utils
import scapy.utils6
from scapy.config import conf
from scapy.data import *
from scapy.supersocket import SuperSocket
import scapy.arch
from scapy.error import warning



# From bits/ioctls.h
SIOCGIFHWADDR  = 0x8927          # Get hardware address    
SIOCGIFADDR    = 0x8915          # get PA address          
SIOCGIFNETMASK = 0x891b          # get network PA mask     
SIOCGIFNAME    = 0x8910          # get iface name          
SIOCSIFLINK    = 0x8911          # set iface channel       
SIOCGIFCONF    = 0x8912          # get iface list          
SIOCGIFFLAGS   = 0x8913          # get flags               
SIOCSIFFLAGS   = 0x8914          # set flags               
SIOCGIFINDEX   = 0x8933          # name -> if_index mapping
SIOCGIFCOUNT   = 0x8938          # get number of devices
SIOCGSTAMP     = 0x8906          # get packet timestamp (as a timeval)

# From if.h
IFF_UP = 0x1               # Interface is up.
IFF_BROADCAST = 0x2        # Broadcast address valid.
IFF_DEBUG = 0x4            # Turn on debugging.
IFF_LOOPBACK = 0x8         # Is a loopback net.
IFF_POINTOPOINT = 0x10     # Interface is point-to-point link.
IFF_NOTRAILERS = 0x20      # Avoid use of trailers.
IFF_RUNNING = 0x40         # Resources allocated.
IFF_NOARP = 0x80           # No address resolution protocol.
IFF_PROMISC = 0x100        # Receive all packets.

# From netpacket/packet.h
PACKET_ADD_MEMBERSHIP  = 1
PACKET_DROP_MEMBERSHIP = 2
PACKET_RECV_OUTPUT     = 3
PACKET_RX_RING         = 5
PACKET_STATISTICS      = 6
PACKET_MR_MULTICAST    = 0
PACKET_MR_PROMISC      = 1
PACKET_MR_ALLMULTI     = 2

# From bits/socket.h
SOL_PACKET = 263
# From asm/socket.h
SO_ATTACH_FILTER = 26
SOL_SOCKET = 1

# From net/route.h
RTF_UP = 0x0001  # Route usable
RTF_REJECT = 0x0200



LOOPBACK_NAME="lo"

with os.popen("tcpdump -V 2> /dev/null") as _f:
    if _f.close() >> 8 == 0x7f:
        log_loading.warning("Failed to execute tcpdump. Check it is installed and in the PATH")
        TCPDUMP=0
    else:
        TCPDUMP=1
del(_f)
    

def get_if_raw_hwaddr(iff):
    return struct.unpack("16xh6s8x",get_if(iff,SIOCGIFHWADDR))

def get_if_raw_addr(iff):
    try:
        return get_if(iff, SIOCGIFADDR)[20:24]
    except IOError:
        return "\0\0\0\0"


def get_if_list():
    f=open("/proc/net/dev","r")
    lst = []
    f.readline()
    f.readline()
    for l in f:
        lst.append(l.split(":")[0].strip())
    return lst
def get_working_if():
    for i in get_if_list():
        if i == LOOPBACK_NAME:                
            continue
        ifflags = struct.unpack("16xH14x",get_if(i,SIOCGIFFLAGS))[0]
        if ifflags & IFF_UP:
            return i
    return LOOPBACK_NAME
def attach_filter(s, filter):
    # XXX We generate the filter on the interface conf.iface 
    # because tcpdump open the "any" interface and ppp interfaces
    # in cooked mode. As we use them in raw mode, the filter will not
    # work... one solution could be to use "any" interface and translate
    # the filter from cooked mode to raw mode
    # mode
    if not TCPDUMP:
        return
    try:
        f = os.popen("%s -i %s -ddd -s 1600 '%s'" % (conf.prog.tcpdump,conf.iface,filter))
    except OSError,msg:
        log_interactive.warning("Failed to execute tcpdump: (%s)")
        return
    lines = f.readlines()
    if f.close():
        raise Scapy_Exception("Filter parse error")
    nb = int(lines[0])
    bpf = ""
    for l in lines[1:]:
        bpf += struct.pack("HBBI",*map(long,l.split()))

    # XXX. Argl! We need to give the kernel a pointer on the BPF,
    # python object header seems to be 20 bytes. 36 bytes for x86 64bits arch.
    if scapy.arch.X86_64:
        bpfh = struct.pack("HL", nb, id(bpf)+36)
    else:
        bpfh = struct.pack("HI", nb, id(bpf)+20)  
    s.setsockopt(SOL_SOCKET, SO_ATTACH_FILTER, bpfh)

def set_promisc(s,iff,val=1):
    mreq = struct.pack("IHH8s", get_if_index(iff), PACKET_MR_PROMISC, 0, "")
    if val:
        cmd = PACKET_ADD_MEMBERSHIP
    else:
        cmd = PACKET_DROP_MEMBERSHIP
    s.setsockopt(SOL_PACKET, cmd, mreq)



def read_routes():
    f=open("/proc/net/route","r")
    routes = []
    s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ifreq = ioctl(s, SIOCGIFADDR,struct.pack("16s16x",LOOPBACK_NAME))
    addrfamily = struct.unpack("h",ifreq[16:18])[0]
    if addrfamily == socket.AF_INET:
        ifreq2 = ioctl(s, SIOCGIFNETMASK,struct.pack("16s16x",LOOPBACK_NAME))
        msk = socket.ntohl(struct.unpack("I",ifreq2[20:24])[0])
        dst = socket.ntohl(struct.unpack("I",ifreq[20:24])[0]) & msk
        ifaddr = scapy.utils.inet_ntoa(ifreq[20:24])
        routes.append((dst, msk, "0.0.0.0", LOOPBACK_NAME, ifaddr))
    else:
        warning("Interface lo: unkown address family (%i)"% addrfamily)

    for l in f.readlines()[1:]:
        iff,dst,gw,flags,x,x,x,msk,x,x,x = l.split()
        flags = int(flags,16)
        if flags & RTF_UP == 0:
            continue
        if flags & RTF_REJECT:
            continue
        try:
            ifreq = ioctl(s, SIOCGIFADDR,struct.pack("16s16x",iff))
        except IOError: # interface is present in routing tables but does not have any assigned IP
            ifaddr="0.0.0.0"
        else:
            addrfamily = struct.unpack("h",ifreq[16:18])[0]
            if addrfamily == socket.AF_INET:
                ifaddr = scapy.utils.inet_ntoa(ifreq[20:24])
            else:
                warning("Interface %s: unkown address family (%i)"%(iff, addrfamily))
                continue
        routes.append((socket.htonl(long(dst,16))&0xffffffffL,
                       socket.htonl(long(msk,16))&0xffffffffL,
                       scapy.utils.inet_ntoa(struct.pack("I",long(gw,16))),
                       iff, ifaddr))
    
    f.close()
    return routes

############
### IPv6 ###
############

def in6_getifaddr():
    """
    Returns a list of 3-tuples of the form (addr, scope, iface) where
    'addr' is the address of scope 'scope' associated to the interface
    'ifcace'.

    This is the list of all addresses of all interfaces available on
    the system.
    """
    ret = []
    try:
        f = open("/proc/net/if_inet6","r")
    except IOError, err:    
        return ret
    l = f.readlines()
    for i in l:
        # addr, index, plen, scope, flags, ifname
        tmp = i.split()
        addr = struct.unpack('4s4s4s4s4s4s4s4s', tmp[0])
        addr = scapy.utils6.in6_ptop(':'.join(addr))
        ret.append((addr, int(tmp[3], 16), tmp[5])) # (addr, scope, iface)
    return ret

def read_routes6():
    try:
        f = open("/proc/net/ipv6_route","r")
    except IOError, err:
        return []
    # 1. destination network
    # 2. destination prefix length
    # 3. source network displayed
    # 4. source prefix length
    # 5. next hop
    # 6. metric
    # 7. reference counter (?!?)
    # 8. use counter (?!?)
    # 9. flags
    # 10. device name
    routes = []
    def proc2r(p):
        ret = struct.unpack('4s4s4s4s4s4s4s4s', p)
        ret = ':'.join(ret)
        return scapy.utils6.in6_ptop(ret)
    
    lifaddr = in6_getifaddr() 
    for l in f.readlines():
        d,dp,s,sp,nh,m,rc,us,fl,dev = l.split()
        fl = int(fl, 16)

        if fl & RTF_UP == 0:
            continue
        if fl & RTF_REJECT:
            continue

        d = proc2r(d) ; dp = int(dp, 16)
        s = proc2r(s) ; sp = int(sp, 16)
        nh = proc2r(nh)

        cset = [] # candidate set (possible source addresses)
        if dev == LOOPBACK_NAME:
            if d == '::':
                continue
            cset = ['::1']
        else:
            devaddrs = filter(lambda x: x[2] == dev, lifaddr)
            cset = scapy.utils6.construct_source_candidate_set(d, dp, devaddrs, LOOPBACK_NAME)
        
        if len(cset) != 0:
            routes.append((d, dp, nh, dev, cset))
    f.close()
    return routes   




def get_if(iff,cmd):
    s=socket.socket()
    ifreq = ioctl(s, cmd, struct.pack("16s16x",iff))
    s.close()
    return ifreq


def get_if_index(iff):
    return int(struct.unpack("I",get_if(iff, SIOCGIFINDEX)[16:20])[0])

if os.uname()[4] == 'x86_64':
    def get_last_packet_timestamp(sock):
        ts = ioctl(sock, SIOCGSTAMP, "1234567890123456")
        s,us = struct.unpack("QQ",ts)
        return s+us/1000000.0
else:
    def get_last_packet_timestamp(sock):
        ts = ioctl(sock, SIOCGSTAMP, "12345678")
        s,us = struct.unpack("II",ts)
        return s+us/1000000.0


def _flush_fd(fd):
    if type(fd) is not int:
        fd = fd.fileno()
    while 1:
        r,w,e = select([fd],[],[],0)
        if r:
            os.read(fd,MTU)
        else:
            break





class L3PacketSocket(SuperSocket):
    desc = "read/write packets at layer 3 using Linux PF_PACKET sockets"
    def __init__(self, type = ETH_P_ALL, filter=None, promisc=None, iface=None, nofilter=0):
        self.type = type
        self.ins = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(type))
        self.ins.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 0)
        _flush_fd(self.ins)
        if iface:
            self.ins.bind((iface, type))
        if not nofilter:
            if conf.except_filter:
                if filter:
                    filter = "(%s) and not (%s)" % (filter, conf.except_filter)
                else:
                    filter = "not (%s)" % conf.except_filter
            if filter is not None:
                attach_filter(self.ins, filter)
        self.ins.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**30)
        self.outs = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(type))
        self.outs.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2**30)
        if promisc is None:
            promisc = conf.promisc
        self.promisc = promisc
        if self.promisc:
            if iface is None:
                self.iff = get_if_list()
            else:
                if iface.__class__ is list:
                    self.iff = iface
                else:
                    self.iff = [iface]
            for i in self.iff:
                set_promisc(self.ins, i)
    def close(self):
        if self.closed:
            return
        self.closed=1
        if self.promisc:
            for i in self.iff:
                set_promisc(self.ins, i, 0)
        SuperSocket.close(self)
    def recv(self, x=MTU):
        pkt, sa_ll = self.ins.recvfrom(x)
        if sa_ll[2] == socket.PACKET_OUTGOING:
            return None
        if sa_ll[3] in conf.l2types:
            cls = conf.l2types[sa_ll[3]]
            lvl = 2
        elif sa_ll[1] in conf.l3types:
            cls = conf.l3types[sa_ll[1]]
            lvl = 3
        else:
            cls = conf.default_l2
            warning("Unable to guess type (interface=%s protocol=%#x family=%i). Using %s" % (sa_ll[0],sa_ll[1],sa_ll[3],cls.name))
            lvl = 2

        try:
            pkt = cls(pkt)
        except KeyboardInterrupt:
            raise
        except:
            if conf.debug_dissector:
                raise
            pkt = conf.raw_layer(pkt)
        if lvl == 2:
            pkt = pkt.payload
            
        if pkt is not None:
            pkt.time = get_last_packet_timestamp(self.ins)
        return pkt
    
    def send(self, x):
        iff,a,gw  = x.route()
        if iff is None:
            iff = conf.iface
        sdto = (iff, self.type)
        self.outs.bind(sdto)
        sn = self.outs.getsockname()
        ll = lambda x:x
        if type(x) in conf.l3types:
            sdto = (iff, conf.l3types[type(x)])
        if sn[3] in conf.l2types:
            ll = lambda x:conf.l2types[sn[3]]()/x
        try:
            sx = str(ll(x))
            x.sent_time = time.time()
            self.outs.sendto(sx, sdto)
        except socket.error,msg:
            x.sent_time = time.time()  # bad approximation
            if conf.auto_fragment and msg[0] == 90:
                for p in x.fragment():
                    self.outs.sendto(str(ll(p)), sdto)
            else:
                raise
                    



class L2Socket(SuperSocket):
    desc = "read/write packets at layer 2 using Linux PF_PACKET sockets"
    def __init__(self, iface = None, type = ETH_P_ALL, filter=None, nofilter=0):
        if iface is None:
            iface = conf.iface
        self.ins = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(type))
        self.ins.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 0)
        _flush_fd(self.ins)
        if not nofilter: 
            if conf.except_filter:
                if filter:
                    filter = "(%s) and not (%s)" % (filter, conf.except_filter)
                else:
                    filter = "not (%s)" % conf.except_filter
            if filter is not None:
                attach_filter(self.ins, filter)
        self.ins.bind((iface, type))
        self.ins.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**30)
        self.outs = self.ins
        self.outs.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2**30)
        sa_ll = self.outs.getsockname()
        if sa_ll[3] in conf.l2types:
            self.LL = conf.l2types[sa_ll[3]]
        elif sa_ll[1] in conf.l3types:
            self.LL = conf.l3types[sa_ll[1]]
        else:
            self.LL = conf.default_l2
            warning("Unable to guess type (interface=%s protocol=%#x family=%i). Using %s" % (sa_ll[0],sa_ll[1],sa_ll[3],self.LL.name))
            
    def recv(self, x=MTU):
        pkt, sa_ll = self.ins.recvfrom(x)
        if sa_ll[2] == socket.PACKET_OUTGOING:
            return None
        try:
            q = self.LL(pkt)
        except KeyboardInterrupt:
            raise
        except:
            if conf.debug_dissector:
                raise
            q = conf.raw_layer(pkt)
        q.time = get_last_packet_timestamp(self.ins)
        return q


class L2ListenSocket(SuperSocket):
    desc = "read packets at layer 2 using Linux PF_PACKET sockets"
    def __init__(self, iface = None, type = ETH_P_ALL, promisc=None, filter=None, nofilter=0):
        self.type = type
        self.outs = None
        self.ins = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(type))
        self.ins.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 0)
        _flush_fd(self.ins)
        if iface is not None:
            self.ins.bind((iface, type))
        if not nofilter:
            if conf.except_filter:
                if filter:
                    filter = "(%s) and not (%s)" % (filter, conf.except_filter)
                else:
                    filter = "not (%s)" % conf.except_filter
            if filter is not None:
                attach_filter(self.ins, filter)
        if promisc is None:
            promisc = conf.sniff_promisc
        self.promisc = promisc
        if iface is None:
            self.iff = get_if_list()
        else:
            if iface.__class__ is list:
                self.iff = iface
            else:
                self.iff = [iface]
        if self.promisc:
            for i in self.iff:
                set_promisc(self.ins, i)
        self.ins.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**30)
    def close(self):
        if self.promisc:
            for i in self.iff:
                set_promisc(self.ins, i, 0)
        SuperSocket.close(self)

    def recv(self, x):
        pkt, sa_ll = self.ins.recvfrom(x)
        if sa_ll[3] in conf.l2types :
            cls = conf.l2types[sa_ll[3]]
        elif sa_ll[1] in conf.l3types:
            cls = conf.l3types[sa_ll[1]]
        else:
            cls = conf.default_l2
            warning("Unable to guess type (interface=%s protocol=%#x family=%i). Using %s" % (sa_ll[0],sa_ll[1],sa_ll[3],cls.name))

        try:
            pkt = cls(pkt)
        except KeyboardInterrupt:
            raise
        except:
            if conf.debug_dissector:
                raise
            pkt = conf.raw_layer(pkt)
        pkt.time = get_last_packet_timestamp(self.ins)
        return pkt
    
    def send(self, x):
        raise Scapy_Exception("Can't send anything with L2ListenSocket")


conf.L3socket = L3PacketSocket
conf.L2socket = L2Socket
conf.L2listen = L2ListenSocket

conf.iface = get_working_if()

########NEW FILE########
__FILENAME__ = pcapdnet
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Packet sending and receiving with libdnet and libpcap/WinPcap.
"""

import time,struct,sys
if not sys.platform.startswith("win"):
    from fcntl import ioctl
from scapy.data import *
from scapy.config import conf
from scapy.utils import warning
from scapy.supersocket import SuperSocket
from scapy.error import Scapy_Exception
import scapy.arch



if conf.use_pcap:    



    try:
        import pcap
    except ImportError,e:
        try:
            import pcapy as pcap
        except ImportError,e2:
            if conf.interactive:
                log_loading.error("Unable to import pcap module: %s/%s" % (e,e2))
                conf.use_pcap = False
            else:
                raise
    if conf.use_pcap:
        
        # From BSD net/bpf.h
        #BIOCIMMEDIATE=0x80044270
        BIOCIMMEDIATE=-2147204496

        if hasattr(pcap,"pcap"): # python-pypcap
            class _PcapWrapper_pypcap:
                def __init__(self, device, snaplen, promisc, to_ms):
                    try:
                        self.pcap = pcap.pcap(device, snaplen, promisc, immediate=1, timeout_ms=to_ms)
                    except TypeError:
                        # Older pypcap versions do not support the timeout_ms argument
                        self.pcap = pcap.pcap(device, snaplen, promisc, immediate=1)                    
                def __getattr__(self, attr):
                    return getattr(self.pcap, attr)
            open_pcap = lambda *args,**kargs: _PcapWrapper_pypcap(*args,**kargs)
        elif hasattr(pcap,"pcapObject"): # python-libpcap
            class _PcapWrapper_libpcap:
                def __init__(self, *args, **kargs):
                    self.pcap = pcap.pcapObject()
                    self.pcap.open_live(*args, **kargs)
                def setfilter(self, filter):
                    self.pcap.setfilter(filter, 0, 0)
                def next(self):
                    c = self.pcap.next()
                    if c is None:
                        return
                    l,pkt,ts = c 
                    return ts,pkt
                def __getattr__(self, attr):
                    return getattr(self.pcap, attr)
            open_pcap = lambda *args,**kargs: _PcapWrapper_libpcap(*args,**kargs)
        elif hasattr(pcap,"open_live"): # python-pcapy
            class _PcapWrapper_pcapy:
                def __init__(self, *args, **kargs):
                    self.pcap = pcap.open_live(*args, **kargs)
                def next(self):
                    try:
                        c = self.pcap.next()
                    except pcap.PcapError:
                        return None
                    else:
                        h,p = c
                        s,us = h.getts()
                        return (s+0.000001*us), p
                def fileno(self):
                    warning("fileno: pcapy API does not permit to get capure file descriptor. Bugs ahead! Press Enter to trigger packet reading")
                    return 0
                def __getattr__(self, attr):
                    return getattr(self.pcap, attr)
            open_pcap = lambda *args,**kargs: _PcapWrapper_pcapy(*args,**kargs)

        
        class PcapTimeoutElapsed(Scapy_Exception):
            pass
    
        class L2pcapListenSocket(SuperSocket):
            desc = "read packets at layer 2 using libpcap"
            def __init__(self, iface = None, type = ETH_P_ALL, promisc=None, filter=None):
                self.type = type
                self.outs = None
                self.iface = iface
                if iface is None:
                    iface = conf.iface
                if promisc is None:
                    promisc = conf.sniff_promisc
                self.promisc = promisc
                self.ins = open_pcap(iface, 1600, self.promisc, 100)
                try:
                    ioctl(self.ins.fileno(),BIOCIMMEDIATE,struct.pack("I",1))
                except:
                    pass
                if type == ETH_P_ALL: # Do not apply any filter if Ethernet type is given
                    if conf.except_filter:
                        if filter:
                            filter = "(%s) and not (%s)" % (filter, conf.except_filter)
                        else:
                            filter = "not (%s)" % conf.except_filter
                    if filter:
                        self.ins.setfilter(filter)
        
            def close(self):
                del(self.ins)
                
            def recv(self, x=MTU):
                ll = self.ins.datalink()
                if ll in conf.l2types:
                    cls = conf.l2types[ll]
                else:
                    cls = conf.default_l2
                    warning("Unable to guess datalink type (interface=%s linktype=%i). Using %s" % (self.iface, ll, cls.name))
        
                pkt = None
                while pkt is None:
                    pkt = self.ins.next()
                    if pkt is not None:
                        ts,pkt = pkt
                    if scapy.arch.WINDOWS and pkt is None:
                        raise PcapTimeoutElapsed
                
                try:
                    pkt = cls(pkt)
                except KeyboardInterrupt:
                    raise
                except:
                    if conf.debug_dissector:
                        raise
                    pkt = conf.raw_layer(pkt)
                pkt.time = ts
                return pkt
        
            def send(self, x):
                raise Scapy_Exception("Can't send anything with L2pcapListenSocket")
        
    
        conf.L2listen = L2pcapListenSocket

        
    

if conf.use_dnet:
    try:
        import dnet
    except ImportError,e:
        if conf.interactive:
            log_loading.error("Unable to import dnet module: %s" % e)
            conf.use_dnet = False
            def get_if_raw_hwaddr(iff):
                "dummy"
                return (0,"\0\0\0\0\0\0")
            def get_if_raw_addr(iff):
                "dummy"
                return "\0\0\0\0"
            def get_if_list():
                "dummy"
                return []
        else:
            raise
    else:
        def get_if_raw_hwaddr(iff):
            if iff == scapy.arch.LOOPBACK_NAME:
                return (772, '\x00'*6)
            try:
                l = dnet.intf().get(iff)
                l = l["link_addr"]
            except:
                raise Scapy_Exception("Error in attempting to get hw address for interface [%s]" % iff)
            return l.type,l.data
        def get_if_raw_addr(ifname):
            i = dnet.intf()
            return i.get(ifname)["addr"].data
        def get_if_list():
            return [i.get("name", None) for i in dnet.intf()]
    
    
if conf.use_pcap and conf.use_dnet:
    class L3dnetSocket(SuperSocket):
        desc = "read/write packets at layer 3 using libdnet and libpcap"
        def __init__(self, type = ETH_P_ALL, filter=None, promisc=None, iface=None, nofilter=0):
            self.iflist = {}
            self.intf = dnet.intf()
            if iface is None:
                iface = conf.iface
            self.iface = iface
            self.ins = open_pcap(iface, 1600, 0, 100)
            try:
                ioctl(self.ins.fileno(),BIOCIMMEDIATE,struct.pack("I",1))
            except:
                pass
            if nofilter:
                if type != ETH_P_ALL:  # PF_PACKET stuff. Need to emulate this for pcap
                    filter = "ether proto %i" % type
                else:
                    filter = None
            else:
                if conf.except_filter:
                    if filter:
                        filter = "(%s) and not (%s)" % (filter, conf.except_filter)
                    else:
                        filter = "not (%s)" % conf.except_filter
                if type != ETH_P_ALL:  # PF_PACKET stuff. Need to emulate this for pcap
                    if filter:
                        filter = "(ether proto %i) and (%s)" % (type,filter)
                    else:
                        filter = "ether proto %i" % type
            if filter:
                self.ins.setfilter(filter)
        def send(self, x):
            iff,a,gw  = x.route()
            if iff is None:
                iff = conf.iface
            ifs,cls = self.iflist.get(iff,(None,None))
            if ifs is None:
                iftype = self.intf.get(iff)["type"]
                if iftype == dnet.INTF_TYPE_ETH:
                    try:
                        cls = conf.l2types[1]
                    except KeyError:
                        warning("Unable to find Ethernet class. Using nothing")
                    ifs = dnet.eth(iff)
                else:
                    ifs = dnet.ip()
                self.iflist[iff] = ifs,cls
            if cls is None:
                sx = str(x)
            else:
                sx = str(cls()/x)
            x.sent_time = time.time()
            ifs.send(sx)
        def recv(self,x=MTU):
            ll = self.ins.datalink()
            if ll in conf.l2types:
                cls = conf.l2types[ll]
            else:
                cls = conf.default_l2
                warning("Unable to guess datalink type (interface=%s linktype=%i). Using %s" % (self.iface, ll, cls.name))
    
            pkt = self.ins.next()
            if pkt is not None:
                ts,pkt = pkt
            if pkt is None:
                return
    
            try:
                pkt = cls(pkt)
            except KeyboardInterrupt:
                raise
            except:
                if conf.debug_dissector:
                    raise
                pkt = conf.raw_layer(pkt)
            pkt.time = ts
            return pkt.payload
    
        def nonblock_recv(self):
            self.ins.setnonblock(1)
            p = self.recv()
            self.ins.setnonblock(0)
            return p
    
        def close(self):
            if hasattr(self, "ins"):
                del(self.ins)
            if hasattr(self, "outs"):
                del(self.outs)
    
    class L2dnetSocket(SuperSocket):
        desc = "read/write packets at layer 2 using libdnet and libpcap"
        def __init__(self, iface = None, type = ETH_P_ALL, filter=None, nofilter=0):
            if iface is None:
                iface = conf.iface
            self.iface = iface
            self.ins = open_pcap(iface, 1600, 0, 100)
            try:
                ioctl(self.ins.fileno(),BIOCIMMEDIATE,struct.pack("I",1))
            except:
                pass
            if nofilter:
                if type != ETH_P_ALL:  # PF_PACKET stuff. Need to emulate this for pcap
                    filter = "ether proto %i" % type
                else:
                    filter = None
            else:
                if conf.except_filter:
                    if filter:
                        filter = "(%s) and not (%s)" % (filter, conf.except_filter)
                    else:
                        filter = "not (%s)" % conf.except_filter
                if type != ETH_P_ALL:  # PF_PACKET stuff. Need to emulate this for pcap
                    if filter:
                        filter = "(ether proto %i) and (%s)" % (type,filter)
                    else:
                        filter = "ether proto %i" % type
            if filter:
                self.ins.setfilter(filter)
            self.outs = dnet.eth(iface)
        def recv(self,x=MTU):
            ll = self.ins.datalink()
            if ll in conf.l2types:
                cls = conf.l2types[ll]
            else:
                cls = conf.default_l2
                warning("Unable to guess datalink type (interface=%s linktype=%i). Using %s" % (self.iface, ll, cls.name))
    
            pkt = self.ins.next()
            if pkt is not None:
                ts,pkt = pkt
            if pkt is None:
                return
            
            try:
                pkt = cls(pkt)
            except KeyboardInterrupt:
                raise
            except:
                if conf.debug_dissector:
                    raise
                pkt = conf.raw_layer(pkt)
            pkt.time = ts
            return pkt
    
        def nonblock_recv(self):
            self.ins.setnonblock(1)
            p = self.recv(MTU)
            self.ins.setnonblock(0)
            return p
    
        def close(self):
            if hasattr(self, "ins"):
                del(self.ins)
            if hasattr(self, "outs"):
                del(self.outs)

    conf.L3socket=L3dnetSocket
    conf.L2socket=L2dnetSocket

        
    

########NEW FILE########
__FILENAME__ = solaris
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Customization for the Solaris operation system.
"""

# IPPROTO_GRE is missing on Solaris
import socket
socket.IPPROTO_GRE = 47

LOOPBACK_NAME="lo0"

from unix import *

########NEW FILE########
__FILENAME__ = unix
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Common customizations for all Unix-like operating systems other than Linux
"""

import sys,os,struct,socket,time
from fcntl import ioctl
from scapy.error import warning
import scapy.config
import scapy.utils
import scapy.utils6
import scapy.arch

scapy.config.conf.use_pcap = 1
scapy.config.conf.use_dnet = 1
from pcapdnet import *


    


##################
## Routes stuff ##
##################


def read_routes():
    if scapy.arch.SOLARIS:
        f=os.popen("netstat -rvn") # -f inet
    elif scapy.arch.FREEBSD:
        f=os.popen("netstat -rnW") # -W to handle long interface names
    else:
        f=os.popen("netstat -rn") # -f inet
    ok = 0
    mtu_present = False
    prio_present = False
    routes = []
    pending_if = []
    for l in f.readlines():
        if not l:
            break
        l = l.strip()
        if l.find("----") >= 0: # a separation line
            continue
        if not ok:
            if l.find("Destination") >= 0:
                ok = 1
                mtu_present = l.find("Mtu") >= 0
                prio_present = l.find("Prio") >= 0
            continue
        if not l:
            break
        if scapy.arch.SOLARIS:
            lspl = l.split()
            if len(lspl) == 10:
                dest,mask,gw,netif,mxfrg,rtt,ref,flg = lspl[:8]
            else: # missing interface
                dest,mask,gw,mxfrg,rtt,ref,flg = lspl[:7]
                netif=None
        else:
            rt = l.split()
            dest,gw,flg = rt[:3]
            netif = rt[5+mtu_present+prio_present]
        if flg.find("Lc") >= 0:
            continue                
        if dest == "default":
            dest = 0L
            netmask = 0L
        else:
            if scapy.arch.SOLARIS:
                netmask = scapy.utils.atol(mask)
            elif "/" in dest:
                dest,netmask = dest.split("/")
                netmask = scapy.utils.itom(int(netmask))
            else:
                netmask = scapy.utils.itom((dest.count(".") + 1) * 8)
            dest += ".0"*(3-dest.count("."))
            dest = scapy.utils.atol(dest)
        if not "G" in flg:
            gw = '0.0.0.0'
        if netif is not None:
            ifaddr = scapy.arch.get_if_addr(netif)
            routes.append((dest,netmask,gw,netif,ifaddr))
        else:
            pending_if.append((dest,netmask,gw))
    f.close()

    # On Solaris, netstat does not provide output interfaces for some routes
    # We need to parse completely the routing table to route their gw and
    # know their output interface
    for dest,netmask,gw in pending_if:
        gw_l = scapy.utils.atol(gw)
        max_rtmask,gw_if,gw_if_addr, = 0,None,None
        for rtdst,rtmask,_,rtif,rtaddr in routes[:]:
            if gw_l & rtmask == rtdst:
                if rtmask >= max_rtmask:
                    max_rtmask = rtmask
                    gw_if = rtif
                    gw_if_addr = rtaddr
        if gw_if:
            routes.append((dest,netmask,gw,gw_if,gw_if_addr))
        else:
            warning("Did not find output interface to reach gateway %s" % gw)
            
    return routes

############
### IPv6 ###
############

def in6_getifaddr():
    """
    Returns a list of 3-tuples of the form (addr, scope, iface) where
    'addr' is the address of scope 'scope' associated to the interface
    'ifcace'.

    This is the list of all addresses of all interfaces available on
    the system.
    """

    ret = []
    i = dnet.intf()
    for int in i:
        ifname = int['name']
        v6 = []
        if int.has_key('alias_addrs'):
            v6 = int['alias_addrs']
        for a in v6:
            if a.type != dnet.ADDR_TYPE_IP6:
                continue

            xx = str(a).split('/')[0]
            addr = scapy.utils6.in6_ptop(xx)

            scope = scapy.utils6.in6_getscope(addr)

            ret.append((xx, scope, ifname))
    return ret

def read_routes6():
    f = os.popen("netstat -rn -f inet6")
    ok = False
    mtu_present = False
    prio_present = False
    routes = []
    lifaddr = in6_getifaddr()
    for l in f.readlines():
        if not l:
            break
        l = l.strip()
        if not ok:
            if l.find("Destination") >= 0:
                ok = 1
                mtu_present = l.find("Mtu") >= 0
                prio_present = l.find("Prio") >= 0
            continue
        # gv 12/12/06: under debugging      
        if scapy.arch.NETBSD or scapy.arch.OPENBSD:
            lspl = l.split()
            d,nh,fl = lspl[:3]
            dev = lspl[5+mtu_present+prio_present]
        else:       # FREEBSD or DARWIN 
            d,nh,fl,dev = l.split()[:4]
        if filter(lambda x: x[2] == dev, lifaddr) == []:
            continue
        if 'L' in fl: # drop MAC addresses
            continue

        if 'link' in nh:
            nh = '::'

        cset = [] # candidate set (possible source addresses)
        dp = 128
        if d == 'default':
            d = '::'
            dp = 0
        if '/' in d:
            d,dp = d.split("/")
            dp = int(dp)
        if '%' in d:
            d,dev = d.split('%')
        if '%' in nh:
            nh,dev = nh.split('%')
        if scapy.arch.LOOPBACK_NAME in dev:
            cset = ['::1']
            nh = '::'
        else:
            devaddrs = filter(lambda x: x[2] == dev, lifaddr)
            cset = scapy.utils6.construct_source_candidate_set(d, dp, devaddrs, scapy.arch.LOOPBACK_NAME)

        if len(cset) != 0:
            routes.append((d, dp, nh, dev, cset))

    f.close()
    return routes


            




########NEW FILE########
__FILENAME__ = asn1
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
ASN.1 (Abstract Syntax Notation One)
"""

import random
from scapy.config import conf
from scapy.error import Scapy_Exception,warning
from scapy.volatile import RandField
from scapy.utils import Enum_metaclass, EnumElement

class RandASN1Object(RandField):
    def __init__(self, objlist=None):
        if objlist is None:
            objlist = map(lambda x:x._asn1_obj,
                          filter(lambda x:hasattr(x,"_asn1_obj"), ASN1_Class_UNIVERSAL.__rdict__.values()))
        self.objlist = objlist
        self.chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    def _fix(self, n=0):
        o = random.choice(self.objlist)
        if issubclass(o, ASN1_INTEGER):
            return o(int(random.gauss(0,1000)))
        elif issubclass(o, ASN1_IPADDRESS):
            z = RandIP()._fix()
            return o(z)
        elif issubclass(o, ASN1_STRING):
            z = int(random.expovariate(0.05)+1)
            return o("".join([random.choice(self.chars) for i in range(z)]))
        elif issubclass(o, ASN1_SEQUENCE) and (n < 10):
            z = int(random.expovariate(0.08)+1)
            return o(map(lambda x:x._fix(n+1), [self.__class__(objlist=self.objlist)]*z))
        return ASN1_INTEGER(int(random.gauss(0,1000)))


##############
#### ASN1 ####
##############

class ASN1_Error(Scapy_Exception):
    pass

class ASN1_Encoding_Error(ASN1_Error):
    pass

class ASN1_Decoding_Error(ASN1_Error):
    pass

class ASN1_BadTag_Decoding_Error(ASN1_Decoding_Error):
    pass



class ASN1Codec(EnumElement):
    def register_stem(cls, stem):
        cls._stem = stem
    def dec(cls, s, context=None):
        return cls._stem.dec(s, context=context)
    def safedec(cls, s, context=None):
        return cls._stem.safedec(s, context=context)
    def get_stem(cls):
        return cls.stem
    

class ASN1_Codecs_metaclass(Enum_metaclass):
    element_class = ASN1Codec

class ASN1_Codecs:
    __metaclass__ = ASN1_Codecs_metaclass
    BER = 1
    DER = 2
    PER = 3
    CER = 4
    LWER = 5
    BACnet = 6
    OER = 7
    SER = 8
    XER = 9

class ASN1Tag(EnumElement):
    def __init__(self, key, value, context=None, codec=None):
        EnumElement.__init__(self, key, value)
        self._context = context
        if codec == None:
            codec = {}
        self._codec = codec
    def clone(self): # /!\ not a real deep copy. self.codec is shared
        return self.__class__(self._key, self._value, self._context, self._codec)
    def register_asn1_object(self, asn1obj):
        self._asn1_obj = asn1obj
    def asn1_object(self, val):
        if hasattr(self,"_asn1_obj"):
            return self._asn1_obj(val)
        raise ASN1_Error("%r does not have any assigned ASN1 object" % self)
    def register(self, codecnum, codec):
        self._codec[codecnum] = codec
    def get_codec(self, codec):
        try:
            c = self._codec[codec]
        except KeyError,msg:
            raise ASN1_Error("Codec %r not found for tag %r" % (codec, self))
        return c

class ASN1_Class_metaclass(Enum_metaclass):
    element_class = ASN1Tag
    def __new__(cls, name, bases, dct): # XXX factorise a bit with Enum_metaclass.__new__()
        for b in bases:
            for k,v in b.__dict__.iteritems():
                if k not in dct and isinstance(v,ASN1Tag):
                    dct[k] = v.clone()

        rdict = {}
        for k,v in dct.iteritems():
            if type(v) is int:
                v = ASN1Tag(k,v) 
                dct[k] = v
                rdict[v] = v
            elif isinstance(v, ASN1Tag):
                rdict[v] = v
        dct["__rdict__"] = rdict

        cls = type.__new__(cls, name, bases, dct)
        for v in cls.__dict__.values():
            if isinstance(v, ASN1Tag): 
                v.context = cls # overwrite ASN1Tag contexts, even cloned ones
        return cls
            

class ASN1_Class:
    __metaclass__ = ASN1_Class_metaclass

class ASN1_Class_UNIVERSAL(ASN1_Class):
    name = "UNIVERSAL"
    ERROR = -3
    RAW = -2
    NONE = -1
    ANY = 0
    BOOLEAN = 1
    INTEGER = 2
    BIT_STRING = 3
    STRING = 4
    NULL = 5
    OID = 6
    OBJECT_DESCRIPTOR = 7
    EXTERNAL = 8
    REAL = 9
    ENUMERATED = 10
    EMBEDDED_PDF = 11
    UTF8_STRING = 12
    RELATIVE_OID = 13
    SEQUENCE = 0x30#XXX 16 ??
    SET = 0x31 #XXX 17 ??
    NUMERIC_STRING = 18
    PRINTABLE_STRING = 19
    T61_STRING = 20
    VIDEOTEX_STRING = 21
    IA5_STRING = 22
    UTC_TIME = 23
    GENERALIZED_TIME = 24
    GRAPHIC_STRING = 25
    ISO646_STRING = 26
    GENERAL_STRING = 27
    UNIVERSAL_STRING = 28
    CHAR_STRING = 29
    BMP_STRING = 30
    IPADDRESS = 0x40
    COUNTER32 = 0x41
    GAUGE32 = 0x42
    TIME_TICKS = 0x43
    SEP = 0x80

class ASN1_Object_metaclass(type):
    def __new__(cls, name, bases, dct):
        c = super(ASN1_Object_metaclass, cls).__new__(cls, name, bases, dct)
        try:
            c.tag.register_asn1_object(c)
        except:
            warning("Error registering %r for %r" % (c.tag, c.codec))
        return c


class ASN1_Object:
    __metaclass__ = ASN1_Object_metaclass
    tag = ASN1_Class_UNIVERSAL.ANY
    def __init__(self, val):
        self.val = val
    def enc(self, codec):
        return self.tag.get_codec(codec).enc(self.val)
    def __repr__(self):
        return "<%s[%r]>" % (self.__dict__.get("name", self.__class__.__name__), self.val)
    def __str__(self):
        return self.enc(conf.ASN1_default_codec)
    def strshow(self, lvl=0):
        return ("  "*lvl)+repr(self)+"\n"
    def show(self, lvl=0):
        print self.strshow(lvl)
    def __eq__(self, other):
        return self.val == other
    def __cmp__(self, other):
        return cmp(self.val, other)

class ASN1_DECODING_ERROR(ASN1_Object):
    tag = ASN1_Class_UNIVERSAL.ERROR
    def __init__(self, val, exc=None):
        ASN1_Object.__init__(self, val)
        self.exc = exc
    def __repr__(self):
        return "<%s[%r]{{%s}}>" % (self.__dict__.get("name", self.__class__.__name__),
                                   self.val, self.exc.args[0])
    def enc(self, codec):
        if isinstance(self.val, ASN1_Object):
            return self.val.enc(codec)
        return self.val

class ASN1_force(ASN1_Object):
    tag = ASN1_Class_UNIVERSAL.RAW
    def enc(self, codec):
        if isinstance(self.val, ASN1_Object):
            return self.val.enc(codec)
        return self.val

class ASN1_BADTAG(ASN1_force):
    pass

class ASN1_INTEGER(ASN1_Object):
    tag = ASN1_Class_UNIVERSAL.INTEGER

class ASN1_STRING(ASN1_Object):
    tag = ASN1_Class_UNIVERSAL.STRING

class ASN1_BIT_STRING(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.BIT_STRING

class ASN1_PRINTABLE_STRING(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.PRINTABLE_STRING

class ASN1_T61_STRING(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.T61_STRING

class ASN1_IA5_STRING(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.IA5_STRING

class ASN1_NUMERIC_STRING(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.NUMERIC_STRING

class ASN1_VIDEOTEX_STRING(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.VIDEOTEX_STRING

class ASN1_IPADDRESS(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.IPADDRESS

class ASN1_UTC_TIME(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.UTC_TIME

class ASN1_GENERALIZED_TIME(ASN1_STRING):
    tag = ASN1_Class_UNIVERSAL.GENERALIZED_TIME

class ASN1_TIME_TICKS(ASN1_INTEGER):
    tag = ASN1_Class_UNIVERSAL.TIME_TICKS

class ASN1_BOOLEAN(ASN1_INTEGER):
    tag = ASN1_Class_UNIVERSAL.BOOLEAN

class ASN1_ENUMERATED(ASN1_INTEGER):
    tag = ASN1_Class_UNIVERSAL.ENUMERATED
    
class ASN1_NULL(ASN1_INTEGER):
    tag = ASN1_Class_UNIVERSAL.NULL

class ASN1_SEP(ASN1_NULL):
    tag = ASN1_Class_UNIVERSAL.SEP

class ASN1_GAUGE32(ASN1_INTEGER):
    tag = ASN1_Class_UNIVERSAL.GAUGE32
    
class ASN1_COUNTER32(ASN1_INTEGER):
    tag = ASN1_Class_UNIVERSAL.COUNTER32
    
class ASN1_SEQUENCE(ASN1_Object):
    tag = ASN1_Class_UNIVERSAL.SEQUENCE
    def strshow(self, lvl=0):
        s = ("  "*lvl)+("# %s:" % self.__class__.__name__)+"\n"
        for o in self.val:
            s += o.strshow(lvl=lvl+1)
        return s
    
class ASN1_SET(ASN1_SEQUENCE):
    tag = ASN1_Class_UNIVERSAL.SET
    
class ASN1_OID(ASN1_Object):
    tag = ASN1_Class_UNIVERSAL.OID
    def __init__(self, val):
        val = conf.mib._oid(val)
        ASN1_Object.__init__(self, val)
    def __repr__(self):
        return "<%s[%r]>" % (self.__dict__.get("name", self.__class__.__name__), conf.mib._oidname(self.val))
    def __oidname__(self):
        return '%s'%conf.mib._oidname(self.val)
    


conf.ASN1_default_codec = ASN1_Codecs.BER

########NEW FILE########
__FILENAME__ = ber
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Basic Encoding Rules (BER) for ASN.1
"""

from scapy.error import warning
from scapy.utils import inet_aton,inet_ntoa
from asn1 import ASN1_Decoding_Error,ASN1_Encoding_Error,ASN1_BadTag_Decoding_Error,ASN1_Codecs,ASN1_Class_UNIVERSAL,ASN1_Error,ASN1_DECODING_ERROR,ASN1_BADTAG

##################
## BER encoding ##
##################



#####[ BER tools ]#####


class BER_Exception(Exception):
    pass

class BER_Encoding_Error(ASN1_Encoding_Error):
    def __init__(self, msg, encoded=None, remaining=None):
        Exception.__init__(self, msg)
        self.remaining = remaining
        self.encoded = encoded
    def __str__(self):
        s = Exception.__str__(self)
        if isinstance(self.encoded, BERcodec_Object):
            s+="\n### Already encoded ###\n%s" % self.encoded.strshow()
        else:
            s+="\n### Already encoded ###\n%r" % self.encoded
        s+="\n### Remaining ###\n%r" % self.remaining
        return s

class BER_Decoding_Error(ASN1_Decoding_Error):
    def __init__(self, msg, decoded=None, remaining=None):
        Exception.__init__(self, msg)
        self.remaining = remaining
        self.decoded = decoded
    def __str__(self):
        s = Exception.__str__(self)
        if isinstance(self.decoded, BERcodec_Object):
            s+="\n### Already decoded ###\n%s" % self.decoded.strshow()
        else:
            s+="\n### Already decoded ###\n%r" % self.decoded
        s+="\n### Remaining ###\n%r" % self.remaining
        return s

class BER_BadTag_Decoding_Error(BER_Decoding_Error, ASN1_BadTag_Decoding_Error):
    pass

def BER_len_enc(l, size=0):
        if l <= 127 and size==0:
            return chr(l)
        s = ""
        while l or size>0:
            s = chr(l&0xff)+s
            l >>= 8L
            size -= 1
        if len(s) > 127:
            raise BER_Exception("BER_len_enc: Length too long (%i) to be encoded [%r]" % (len(s),s))
        return chr(len(s)|0x80)+s
def BER_len_dec(s):
        l = ord(s[0])
        if not l & 0x80:
            return l,s[1:]
        l &= 0x7f
        if len(s) <= l:
            raise BER_Decoding_Error("BER_len_dec: Got %i bytes while expecting %i" % (len(s)-1, l),remaining=s)
        ll = 0L
        for c in s[1:l+1]:
            ll <<= 8L
            ll |= ord(c)
        return ll,s[l+1:]
        
def BER_num_enc(l, size=1):
        x=[]
        while l or size>0:
            x.insert(0, l & 0x7f)
            if len(x) > 1:
                x[0] |= 0x80
            l >>= 7
            size -= 1
        return "".join([chr(k) for k in x])
def BER_num_dec(s):
        x = 0
        for i in range(len(s)):
            c = ord(s[i])
            x <<= 7
            x |= c&0x7f
            if not c&0x80:
                break
        if c&0x80:
            raise BER_Decoding_Error("BER_num_dec: unfinished number description", remaining=s)
        return x, s[i+1:]

#####[ BER classes ]#####

class BERcodec_metaclass(type):
    def __new__(cls, name, bases, dct):
        c = super(BERcodec_metaclass, cls).__new__(cls, name, bases, dct)
        try:
            c.tag.register(c.codec, c)
        except:
            warning("Error registering %r for %r" % (c.tag, c.codec))
        return c


class BERcodec_Object:
    __metaclass__ = BERcodec_metaclass
    codec = ASN1_Codecs.BER
    tag = ASN1_Class_UNIVERSAL.ANY

    @classmethod
    def asn1_object(cls, val):
        return cls.tag.asn1_object(val)

    @classmethod
    def check_string(cls, s):
        if not s:
            raise BER_Decoding_Error("%s: Got empty object while expecting tag %r" %
                                     (cls.__name__,cls.tag), remaining=s)        
    @classmethod
    def check_type(cls, s):
        cls.check_string(s)
        if cls.tag != ord(s[0]):
            raise BER_BadTag_Decoding_Error("%s: Got tag [%i/%#x] while expecting %r" %
                                            (cls.__name__, ord(s[0]), ord(s[0]),cls.tag), remaining=s)
        return s[1:]
    @classmethod
    def check_type_get_len(cls, s):
        s2 = cls.check_type(s)
        if not s2:
            raise BER_Decoding_Error("%s: No bytes while expecting a length" %
                                     cls.__name__, remaining=s)
        return BER_len_dec(s2)
    @classmethod
    def check_type_check_len(cls, s):
        l,s3 = cls.check_type_get_len(s)
        if len(s3) < l:
            raise BER_Decoding_Error("%s: Got %i bytes while expecting %i" %
                                     (cls.__name__, len(s3), l), remaining=s)
        return l,s3[:l],s3[l:]

    @classmethod
    def do_dec(cls, s, context=None, safe=False):
        if context is None:
            context = cls.tag.context
        cls.check_string(s)
        p = ord(s[0])
        if p not in context:
            t = s
            if len(t) > 18:
                t = t[:15]+"..."
            raise BER_Decoding_Error("Unknown prefix [%02x] for [%r]" % (p,t), remaining=s)
        codec = context[p].get_codec(ASN1_Codecs.BER)
        return codec.dec(s,context,safe)

    @classmethod
    def dec(cls, s, context=None, safe=False):
        if not safe:
            return cls.do_dec(s, context, safe)
        try:
            return cls.do_dec(s, context, safe)
        except BER_BadTag_Decoding_Error,e:
            o,remain = BERcodec_Object.dec(e.remaining, context, safe)
            return ASN1_BADTAG(o),remain
        except BER_Decoding_Error, e:
            return ASN1_DECODING_ERROR(s, exc=e),""
        except ASN1_Error, e:
            return ASN1_DECODING_ERROR(s, exc=e),""

    @classmethod
    def safedec(cls, s, context=None):
        return cls.dec(s, context, safe=True)


    @classmethod
    def enc(cls, s):
        if type(s) is str:
            return BERcodec_STRING.enc(s)
        else:
            return BERcodec_INTEGER.enc(int(s))

            

ASN1_Codecs.BER.register_stem(BERcodec_Object)


class BERcodec_INTEGER(BERcodec_Object):
    tag = ASN1_Class_UNIVERSAL.INTEGER
    @classmethod
    def enc(cls, i):
        s = []
        while 1:
            s.append(i&0xff)
            if -127 <= i < 0:
                break
            if 128 <= i <= 255:
                s.append(0)
            i >>= 8
            if not i:
                break
        s = map(chr, s)
        s.append(BER_len_enc(len(s)))
        s.append(chr(cls.tag))
        s.reverse()
        return "".join(s)
    @classmethod
    def do_dec(cls, s, context=None, safe=False):
        l,s,t = cls.check_type_check_len(s)
        x = 0L
        if s:
            if ord(s[0])&0x80: # negative int
                x = -1L
            for c in s:
                x <<= 8
                x |= ord(c)
        return cls.asn1_object(x),t
    

class BERcodec_BOOLEAN(BERcodec_INTEGER):
    tag = ASN1_Class_UNIVERSAL.BOOLEAN

class BERcodec_ENUMERATED(BERcodec_INTEGER):
    tag = ASN1_Class_UNIVERSAL.ENUMERATED

class BERcodec_NULL(BERcodec_INTEGER):
    tag = ASN1_Class_UNIVERSAL.NULL
    @classmethod
    def enc(cls, i):
        if i == 0:
            return chr(cls.tag)+"\0"
        else:
            return BERcodec_INTEGER.enc(i)

class BERcodec_SEP(BERcodec_NULL):
    tag = ASN1_Class_UNIVERSAL.SEP

class BERcodec_STRING(BERcodec_Object):
    tag = ASN1_Class_UNIVERSAL.STRING
    @classmethod
    def enc(cls,s):
        return chr(cls.tag)+BER_len_enc(len(s))+s
    @classmethod
    def do_dec(cls, s, context=None, safe=False):
        l,s,t = cls.check_type_check_len(s)
        return cls.tag.asn1_object(s),t

class BERcodec_BIT_STRING(BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.BIT_STRING

class BERcodec_PRINTABLE_STRING(BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.PRINTABLE_STRING

class BERcodec_T61_STRING (BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.T61_STRING

class BERcodec_IA5_STRING(BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.IA5_STRING

class BERcodec_NUMERIC_STRING(BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.NUMERIC_STRING

class BERcodec_VIDEOTEX_STRING(BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.VIDEOTEX_STRING

class BERcodec_IPADDRESS(BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.IPADDRESS
    
    @classmethod
    def enc(cls, ipaddr_ascii):
        try:
            s = inet_aton(ipaddr_ascii)
        except Exception:
            raise BER_Encoding_Error("IPv4 address could not be encoded") 
        return chr(cls.tag)+BER_len_enc(len(s))+s
    
    @classmethod
    def do_dec(cls, s, context=None, safe=False):
        l,s,t = cls.check_type_check_len(s)
        try:
            ipaddr_ascii = inet_ntoa(s)
        except Exception:
            raise BER_Decoding_Error("IP address could not be decoded", decoded=obj)
        return cls.asn1_object(ipaddr_ascii), t

class BERcodec_UTC_TIME(BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.UTC_TIME

class BERcodec_GENERALIZED_TIME(BERcodec_STRING):
    tag = ASN1_Class_UNIVERSAL.GENERALIZED_TIME

class BERcodec_TIME_TICKS(BERcodec_INTEGER):
    tag = ASN1_Class_UNIVERSAL.TIME_TICKS

class BERcodec_GAUGE32(BERcodec_INTEGER):
    tag = ASN1_Class_UNIVERSAL.GAUGE32

class BERcodec_COUNTER32(BERcodec_INTEGER):
    tag = ASN1_Class_UNIVERSAL.COUNTER32

class BERcodec_SEQUENCE(BERcodec_Object):
    tag = ASN1_Class_UNIVERSAL.SEQUENCE
    @classmethod
    def enc(cls, l):
        if type(l) is not str:
            l = "".join(map(lambda x: x.enc(cls.codec), l))
        return chr(cls.tag)+BER_len_enc(len(l))+l
    @classmethod
    def do_dec(cls, s, context=None, safe=False):
        if context is None:
            context = cls.tag.context
        l,st = cls.check_type_get_len(s) # we may have len(s) < l
        s,t = st[:l],st[l:]
        obj = []
        while s:
            try:
                o,s = BERcodec_Object.dec(s, context, safe)
            except BER_Decoding_Error, err:
                err.remaining += t
                if err.decoded is not None:
                    obj.append(err.decoded)
                err.decoded = obj
                raise 
            obj.append(o)
        if len(st) < l:
            raise BER_Decoding_Error("Not enough bytes to decode sequence", decoded=obj)
        return cls.asn1_object(obj),t

class BERcodec_SET(BERcodec_SEQUENCE):
    tag = ASN1_Class_UNIVERSAL.SET


class BERcodec_OID(BERcodec_Object):
    tag = ASN1_Class_UNIVERSAL.OID

    @classmethod
    def enc(cls, oid):
        lst = [int(x) for x in oid.strip(".").split(".")]
        if len(lst) >= 2:
            lst[1] += 40*lst[0]
            del(lst[0])
        s = "".join([BER_num_enc(k) for k in lst])
        return chr(cls.tag)+BER_len_enc(len(s))+s
    @classmethod
    def do_dec(cls, s, context=None, safe=False):
        l,s,t = cls.check_type_check_len(s)
        lst = []
        while s:
            l,s = BER_num_dec(s)
            lst.append(l)
        if (len(lst) > 0):
            lst.insert(0,lst[0]/40)
            lst[1] %= 40
        return cls.asn1_object(".".join([str(k) for k in lst])), t



########NEW FILE########
__FILENAME__ = mib
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Management Information Base (MIB) parsing
"""

import re
from glob import glob
from scapy.dadict import DADict,fixname
from scapy.config import conf
from scapy.utils import do_graph

#################
## MIB parsing ##
#################

_mib_re_integer = re.compile("^[0-9]+$")
_mib_re_both = re.compile("^([a-zA-Z_][a-zA-Z0-9_-]*)\(([0-9]+)\)$")
_mib_re_oiddecl = re.compile("$\s*([a-zA-Z0-9_-]+)\s+OBJECT([^:\{\}]|\{[^:]+\})+::=\s*\{([^\}]+)\}",re.M)
_mib_re_strings = re.compile('"[^"]*"')
_mib_re_comments = re.compile('--.*(\r|\n)')

class MIBDict(DADict):
    def _findroot(self, x):
        if x.startswith("."):
            x = x[1:]
        if not x.endswith("."):
            x += "."
        max=0
        root="."
        for k in self.keys():
            if x.startswith(self[k]+"."):
                if max < len(self[k]):
                    max = len(self[k])
                    root = k
        return root, x[max:-1]
    def _oidname(self, x):
        root,remainder = self._findroot(x)
        return root+remainder
    def _oid(self, x):
        xl = x.strip(".").split(".")
        p = len(xl)-1
        while p >= 0 and _mib_re_integer.match(xl[p]):
            p -= 1
        if p != 0 or xl[p] not in self:
            return x
        xl[p] = self[xl[p]] 
        return ".".join(xl[p:])
    def _make_graph(self, other_keys=[], **kargs):
        nodes = [(k,self[k]) for k in self.keys()]
        oids = [self[k] for k in self.keys()]
        for k in other_keys:
            if k not in oids:
                nodes.append(self.oidname(k),k)
        s = 'digraph "mib" {\n\trankdir=LR;\n\n'
        for k,o in nodes:
            s += '\t"%s" [ label="%s"  ];\n' % (o,k)
        s += "\n"
        for k,o in nodes:
            parent,remainder = self._findroot(o[:-1])
            remainder = remainder[1:]+o[-1]
            if parent != ".":
                parent = self[parent]
            s += '\t"%s" -> "%s" [label="%s"];\n' % (parent, o,remainder)
        s += "}\n"
        do_graph(s, **kargs)
    def __len__(self):
        return len(self.keys())


def mib_register(ident, value, the_mib, unresolved):
    if ident in the_mib or ident in unresolved:
        return ident in the_mib
    resval = []
    not_resolved = 0
    for v in value:
        if _mib_re_integer.match(v):
            resval.append(v)
        else:
            v = fixname(v)
            if v not in the_mib:
                not_resolved = 1
            if v in the_mib:
                v = the_mib[v]
            elif v in unresolved:
                v = unresolved[v]
            if type(v) is list:
                resval += v
            else:
                resval.append(v)
    if not_resolved:
        unresolved[ident] = resval
        return False
    else:
        the_mib[ident] = resval
        keys = unresolved.keys()
        i = 0
        while i < len(keys):
            k = keys[i]
            if mib_register(k,unresolved[k], the_mib, {}):
                del(unresolved[k])
                del(keys[i])
                i = 0
            else:
                i += 1
                    
        return True


def load_mib(filenames):
    the_mib = {'iso': ['1']}
    unresolved = {}
    for k in conf.mib.keys():
        mib_register(k, conf.mib[k].split("."), the_mib, unresolved)

    if type(filenames) is str:
        filenames = [filenames]
    for fnames in filenames:
        for fname in glob(fnames):
            f = open(fname)
            text = f.read()
            cleantext = " ".join(_mib_re_strings.split(" ".join(_mib_re_comments.split(text))))
            for m in _mib_re_oiddecl.finditer(cleantext):
                gr = m.groups()
                ident,oid = gr[0],gr[-1]
                ident=fixname(ident)
                oid = oid.split()
                for i in range(len(oid)):
                    m = _mib_re_both.match(oid[i])
                    if m:
                        oid[i] = m.groups()[1]
                mib_register(ident, oid, the_mib, unresolved)

    newmib = MIBDict(_name="MIB")
    for k,o in the_mib.iteritems():
        newmib[k]=".".join(o)
    for k,o in unresolved.iteritems():
        newmib[k]=".".join(o)

    conf.mib=newmib



conf.mib = MIBDict(_name="MIB")

########NEW FILE########
__FILENAME__ = asn1fields
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Classes that implement ASN.1 data structures.
"""

from asn1.asn1 import *
from asn1.ber import *
from volatile import *
from base_classes import BasePacket


#####################
#### ASN1 Fields ####
#####################

class ASN1F_badsequence(Exception):
    pass

class ASN1F_element:
    pass

class ASN1F_optionnal(ASN1F_element):
    def __init__(self, field):
        self._field=field
    def __getattr__(self, attr):
        return getattr(self._field,attr)
    def dissect(self,pkt,s):
        try:
            return self._field.dissect(pkt,s)
        except ASN1F_badsequence:
            self._field.set_val(pkt,None)
            return s
        except BER_Decoding_Error:
            self._field.set_val(pkt,None)
            return s
    def build(self, pkt):
        if self._field.is_empty(pkt):
            return ""
        return self._field.build(pkt)

class ASN1F_field(ASN1F_element):
    holds_packets=0
    islist=0

    ASN1_tag = ASN1_Class_UNIVERSAL.ANY
    context=ASN1_Class_UNIVERSAL
    
    def __init__(self, name, default, context=None):
        if context is not None:
            self.context = context
        self.name = name
        self.default = default

    def i2repr(self, pkt, x):
        return repr(x)
    def i2h(self, pkt, x):
        return x
    def any2i(self, pkt, x):
        return x
    def m2i(self, pkt, x):
        return self.ASN1_tag.get_codec(pkt.ASN1_codec).safedec(x, context=self.context)
    def i2m(self, pkt, x):
        if x is None:
            x = 0
        if isinstance(x, ASN1_Object):
            if ( self.ASN1_tag == ASN1_Class_UNIVERSAL.ANY
                 or x.tag == ASN1_Class_UNIVERSAL.RAW
                 or x.tag == ASN1_Class_UNIVERSAL.ERROR
                 or self.ASN1_tag == x.tag ):
                return x.enc(pkt.ASN1_codec)
            else:
                raise ASN1_Error("Encoding Error: got %r instead of an %r for field [%s]" % (x, self.ASN1_tag, self.name))
        return self.ASN1_tag.get_codec(pkt.ASN1_codec).enc(x)

    def do_copy(self, x):
        if hasattr(x, "copy"):
            return x.copy()
        if type(x) is list:
            x = x[:]
            for i in xrange(len(x)):
                if isinstance(x[i], BasePacket):
                    x[i] = x[i].copy()
        return x

    def build(self, pkt):
        return self.i2m(pkt, getattr(pkt, self.name))

    def set_val(self, pkt, val):
        setattr(pkt, self.name, val)
    def is_empty(self, pkt):
        return getattr(pkt,self.name) is None
    
    def dissect(self, pkt, s):
        v,s = self.m2i(pkt, s)
        self.set_val(pkt, v)
        return s

    def get_fields_list(self):
        return [self]

    def __hash__(self):
        return hash(self.name)
    def __str__(self):
        return self.name
    def __eq__(self, other):
        return self.name == other
    def __repr__(self):
        return self.name
    def randval(self):
        return RandInt()


class ASN1F_INTEGER(ASN1F_field):
    ASN1_tag= ASN1_Class_UNIVERSAL.INTEGER
    def randval(self):
        return RandNum(-2**64, 2**64-1)

class ASN1F_BOOLEAN(ASN1F_field):
    ASN1_tag= ASN1_Class_UNIVERSAL.BOOLEAN
    def randval(self):
        return RandChoice(True,False)

class ASN1F_NULL(ASN1F_INTEGER):
    ASN1_tag= ASN1_Class_UNIVERSAL.NULL

class ASN1F_SEP(ASN1F_NULL):
    ASN1_tag= ASN1_Class_UNIVERSAL.SEP

class ASN1F_enum_INTEGER(ASN1F_INTEGER):
    def __init__(self, name, default, enum):
        ASN1F_INTEGER.__init__(self, name, default)
        i2s = self.i2s = {}
        s2i = self.s2i = {}
        if type(enum) is list:
            keys = xrange(len(enum))
        else:
            keys = enum.keys()
        if filter(lambda x: type(x) is str, keys):
            i2s,s2i = s2i,i2s
        for k in keys:
            i2s[k] = enum[k]
            s2i[enum[k]] = k
    def any2i_one(self, pkt, x):
        if type(x) is str:
            x = self.s2i[x]
        return x
    def i2repr_one(self, pkt, x):
        return self.i2s.get(x, repr(x))
    
    def any2i(self, pkt, x):
        if type(x) is list:
            return map(lambda z,pkt=pkt:self.any2i_one(pkt,z), x)
        else:
            return self.any2i_one(pkt,x)        
    def i2repr(self, pkt, x):
        if type(x) is list:
            return map(lambda z,pkt=pkt:self.i2repr_one(pkt,z), x)
        else:
            return self.i2repr_one(pkt,x)

class ASN1F_ENUMERATED(ASN1F_enum_INTEGER):
    ASN1_tag = ASN1_Class_UNIVERSAL.ENUMERATED

class ASN1F_STRING(ASN1F_field):
    ASN1_tag = ASN1_Class_UNIVERSAL.STRING
    def randval(self):
        return RandString(RandNum(0, 1000))

class ASN1F_PRINTABLE_STRING(ASN1F_STRING):
    ASN1_tag = ASN1_Class_UNIVERSAL.PRINTABLE_STRING

class ASN1F_BIT_STRING(ASN1F_STRING):
    ASN1_tag = ASN1_Class_UNIVERSAL.BIT_STRING
    
class ASN1F_IPADDRESS(ASN1F_STRING):
    ASN1_tag = ASN1_Class_UNIVERSAL.IPADDRESS    

class ASN1F_TIME_TICKS(ASN1F_INTEGER):
    ASN1_tag = ASN1_Class_UNIVERSAL.TIME_TICKS

class ASN1F_UTC_TIME(ASN1F_STRING):
    ASN1_tag = ASN1_Class_UNIVERSAL.UTC_TIME

class ASN1F_GENERALIZED_TIME(ASN1F_STRING):
    ASN1_tag = ASN1_Class_UNIVERSAL.GENERALIZED_TIME

class ASN1F_OID(ASN1F_field):
    ASN1_tag = ASN1_Class_UNIVERSAL.OID
    def randval(self):
        return RandOID()

class ASN1F_SEQUENCE(ASN1F_field):
    ASN1_tag = ASN1_Class_UNIVERSAL.SEQUENCE
    def __init__(self, *seq, **kargs):
        if "ASN1_tag" in kargs:
            self.ASN1_tag = kargs["ASN1_tag"]
        self.seq = seq
    def __repr__(self):
        return "<%s%r>" % (self.__class__.__name__,self.seq,)
    def set_val(self, pkt, val):
        for f in self.seq:
            f.set_val(pkt,val)
    def is_empty(self, pkt):
        for f in self.seq:
            if not f.is_empty(pkt):
                return False
        return True
    def get_fields_list(self):
        return reduce(lambda x,y: x+y.get_fields_list(), self.seq, [])
    def build(self, pkt):
        s = reduce(lambda x,y: x+y.build(pkt), self.seq, "")
        return self.i2m(pkt, s)
    def dissect(self, pkt, s):
        codec = self.ASN1_tag.get_codec(pkt.ASN1_codec)
        try:
            i,s,remain = codec.check_type_check_len(s)
            for obj in self.seq:
                s = obj.dissect(pkt,s)
            if s:
                warning("Too many bytes to decode sequence: [%r]" % s) # XXX not reversible!
            return remain
        except ASN1_Error,e:
            raise ASN1F_badsequence(e)

class ASN1F_SET(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_UNIVERSAL.SET

class ASN1F_SEQUENCE_OF(ASN1F_SEQUENCE):
    holds_packets = 1
    islist = 1
    def __init__(self, name, default, asn1pkt, ASN1_tag=0x30):
        self.asn1pkt = asn1pkt
        self.tag = chr(ASN1_tag)
        self.name = name
        self.default = default
    def i2repr(self, pkt, i):
        if i is None:
            return []
        return i
    def get_fields_list(self):
        return [self]
    def set_val(self, pkt, val):
        ASN1F_field.set_val(self, pkt, val)
    def is_empty(self, pkt):
        return ASN1F_field.is_empty(self, pkt)
    def build(self, pkt):
        val = getattr(pkt, self.name)
        if isinstance(val, ASN1_Object) and val.tag == ASN1_Class_UNIVERSAL.RAW:
            s = val
        elif val is None:
            s = ""
        else:
            s = "".join(map(str, val ))
        return self.i2m(pkt, s)
    def dissect(self, pkt, s):
        codec = self.ASN1_tag.get_codec(pkt.ASN1_codec)
        i,s1,remain = codec.check_type_check_len(s)
        lst = []
        while s1:
            try:
                p = self.asn1pkt(s1)
            except ASN1F_badsequence,e:
                lst.append(packet.Raw(s1))
                break
            lst.append(p)
            if packet.Raw in p:
                s1 = p[packet.Raw].load
                del(p[packet.Raw].underlayer.payload)
            else:
                break
        self.set_val(pkt, lst)
        return remain
    def randval(self):
        return fuzz(self.asn1pkt())
    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__,self.name)

class ASN1F_PACKET(ASN1F_field):
    holds_packets = 1
    def __init__(self, name, default, cls):
        ASN1F_field.__init__(self, name, default)
        self.cls = cls
    def i2m(self, pkt, x):
        if x is None:
            x = ""
        return str(x)
    def extract_packet(self, cls, x):
        try:
            c = cls(x)
        except ASN1F_badsequence:
            c = packet.Raw(x)
        cpad = c.getlayer(packet.Padding)
        x = ""
        if cpad is not None:
            x = cpad.load
            del(cpad.underlayer.payload)
        return c,x
    def m2i(self, pkt, x):
        return self.extract_packet(self.cls, x)


class ASN1F_CHOICE(ASN1F_PACKET):
    ASN1_tag = ASN1_Class_UNIVERSAL.NONE
    def __init__(self, name, default, *args):
        self.name=name
        self.choice = {}
        for p in args:
            self.choice[p.ASN1_root.ASN1_tag] = p
#        self.context=context
        self.default=default
    def m2i(self, pkt, x):
        if len(x) == 0:
            return packet.Raw(),""
            raise ASN1_Error("ASN1F_CHOICE: got empty string")
        if ord(x[0]) not in self.choice:
            return packet.Raw(x),"" # XXX return RawASN1 packet ? Raise error 
            raise ASN1_Error("Decoding Error: choice [%i] not found in %r" % (ord(x[0]), self.choice.keys()))

        z = ASN1F_PACKET.extract_packet(self, self.choice[ord(x[0])], x)
        return z
    def randval(self):
        return RandChoice(*map(lambda x:fuzz(x()), self.choice.values()))
            
    
# This import must come in last to avoid problems with cyclic dependencies
import packet

########NEW FILE########
__FILENAME__ = asn1packet
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Packet holding data in Abstract Syntax Notation (ASN.1).
"""

from packet import *

class ASN1_Packet(Packet):
    ASN1_root = None
    ASN1_codec = None    
    def init_fields(self):
        flist = self.ASN1_root.get_fields_list()
        self.do_init_fields(flist)
        self.fields_desc = flist    
    def self_build(self):
        return self.ASN1_root.build(self)    
    def do_dissect(self, x):
        return self.ASN1_root.dissect(self, x)
        


########NEW FILE########
__FILENAME__ = as_resolvers
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Resolve Autonomous Systems (AS).
"""


import socket
from config import conf

class AS_resolver:
    server = None
    options = "-k" 
    def __init__(self, server=None, port=43, options=None):
        if server is not None:
            self.server = server
        self.port = port
        if options is not None:
            self.options = options
        
    def _start(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.server,self.port))
        if self.options:
            self.s.send(self.options+"\n")
            self.s.recv(8192)
    def _stop(self):
        self.s.close()
        
    def _parse_whois(self, txt):
        asn,desc = None,""
        for l in txt.splitlines():
            if not asn and l.startswith("origin:"):
                asn = l[7:].strip()
            if l.startswith("descr:"):
                if desc:
                    desc += r"\n"
                desc += l[6:].strip()
            if asn is not None and desc:
                break
        return asn,desc.strip()

    def _resolve_one(self, ip):
        self.s.send("%s\n" % ip)
        x = ""
        while not ("%" in x  or "source" in x):
            x += self.s.recv(8192)
        asn, desc = self._parse_whois(x)
        return ip,asn,desc
    def resolve(self, *ips):
        self._start()
        ret = []
        for ip in ips:
            ip,asn,desc = self._resolve_one(ip)
            if asn is not None:
                ret.append((ip,asn,desc))
        self._stop()
        return ret

class AS_resolver_riswhois(AS_resolver):
    server = "riswhois.ripe.net"
    options = "-k -M -1"


class AS_resolver_radb(AS_resolver):
    server = "whois.ra.net"
    options = "-k -M"
    

class AS_resolver_cymru(AS_resolver):
    server = "whois.cymru.com"
    options = None
    def resolve(self, *ips):
        ASNlist = []
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.server,self.port))
        s.send("begin\r\n"+"\r\n".join(ips)+"\r\nend\r\n")
        r = ""
        while 1:
            l = s.recv(8192)
            if l == "":
                break
            r += l
        s.close()
        for l in r.splitlines()[1:]:
            if "|" not in l:
                continue
            asn,ip,desc = map(str.strip, l.split("|"))
            if asn == "NA":
                continue
            asn = int(asn)
            ASNlist.append((ip,asn,desc))
        return ASNlist

class AS_resolver_multi(AS_resolver):
    resolvers_list = ( AS_resolver_cymru(),AS_resolver_riswhois(),AS_resolver_radb() )
    def __init__(self, *reslist):
        if reslist:
            self.resolvers_list = reslist
    def resolve(self, *ips):
        todo = ips
        ret = []
        for ASres in self.resolvers_list:
            res = ASres.resolve(*todo)
            resolved = [ ip for ip,asn,desc in res ]
            todo = [ ip for ip in todo if ip not in resolved ]
            ret += res
        return ret


conf.AS_resolver = AS_resolver_multi()

########NEW FILE########
__FILENAME__ = automaton
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Automata with states, transitions and actions.
"""

from __future__ import with_statement
import types,itertools,time,os,sys,socket
from select import select
from collections import deque
import thread
from config import conf
from utils import do_graph
from error import log_interactive
from plist import PacketList
from data import MTU
from supersocket import SuperSocket

class ObjectPipe:
    def __init__(self):
        self.rd,self.wr = os.pipe()
        self.queue = deque()
    def fileno(self):
        return self.rd
    def send(self, obj):
        self.queue.append(obj)
        os.write(self.wr,"X")
    def recv(self, n=0):
        os.read(self.rd,1)
        return self.queue.popleft()


class Message:
    def __init__(self, **args):
        self.__dict__.update(args)
    def __repr__(self):
        return "<Message %s>" % " ".join("%s=%r"%(k,v)
                                         for (k,v) in self.__dict__.iteritems()
                                         if not k.startswith("_"))

class _instance_state:
    def __init__(self, instance):
        self.im_self = instance.im_self
        self.im_func = instance.im_func
        self.im_class = instance.im_class
    def __getattr__(self, attr):
        return getattr(self.im_func, attr)

    def __call__(self, *args, **kargs):
        return self.im_func(self.im_self, *args, **kargs)
    def breaks(self):
        return self.im_self.add_breakpoints(self.im_func)
    def intercepts(self):
        return self.im_self.add_interception_points(self.im_func)
    def unbreaks(self):
        return self.im_self.remove_breakpoints(self.im_func)
    def unintercepts(self):
        return self.im_self.remove_interception_points(self.im_func)
        

##############
## Automata ##
##############

class ATMT:
    STATE = "State"
    ACTION = "Action"
    CONDITION = "Condition"
    RECV = "Receive condition"
    TIMEOUT = "Timeout condition"
    IOEVENT = "I/O event"

    class NewStateRequested(Exception):
        def __init__(self, state_func, automaton, *args, **kargs):
            self.func = state_func
            self.state = state_func.atmt_state
            self.initial = state_func.atmt_initial
            self.error = state_func.atmt_error
            self.final = state_func.atmt_final
            Exception.__init__(self, "Request state [%s]" % self.state)
            self.automaton = automaton
            self.args = args
            self.kargs = kargs
            self.action_parameters() # init action parameters
        def action_parameters(self, *args, **kargs):
            self.action_args = args
            self.action_kargs = kargs
            return self
        def run(self):
            return self.func(self.automaton, *self.args, **self.kargs)
        def __repr__(self):
            return "NewStateRequested(%s)" % self.state

    @staticmethod
    def state(initial=0,final=0,error=0):
        def deco(f,initial=initial, final=final):
            f.atmt_type = ATMT.STATE
            f.atmt_state = f.func_name
            f.atmt_initial = initial
            f.atmt_final = final
            f.atmt_error = error
            def state_wrapper(self, *args, **kargs):
                return ATMT.NewStateRequested(f, self, *args, **kargs)

            state_wrapper.func_name = "%s_wrapper" % f.func_name
            state_wrapper.atmt_type = ATMT.STATE
            state_wrapper.atmt_state = f.func_name
            state_wrapper.atmt_initial = initial
            state_wrapper.atmt_final = final
            state_wrapper.atmt_error = error
            state_wrapper.atmt_origfunc = f
            return state_wrapper
        return deco
    @staticmethod
    def action(cond, prio=0):
        def deco(f,cond=cond):
            if not hasattr(f,"atmt_type"):
                f.atmt_cond = {}
            f.atmt_type = ATMT.ACTION
            f.atmt_cond[cond.atmt_condname] = prio
            return f
        return deco
    @staticmethod
    def condition(state, prio=0):
        def deco(f, state=state):
            f.atmt_type = ATMT.CONDITION
            f.atmt_state = state.atmt_state
            f.atmt_condname = f.func_name
            f.atmt_prio = prio
            return f
        return deco
    @staticmethod
    def receive_condition(state, prio=0):
        def deco(f, state=state):
            f.atmt_type = ATMT.RECV
            f.atmt_state = state.atmt_state
            f.atmt_condname = f.func_name
            f.atmt_prio = prio
            return f
        return deco
    @staticmethod
    def ioevent(state, name, prio=0, as_supersocket=None):
        def deco(f, state=state):
            f.atmt_type = ATMT.IOEVENT
            f.atmt_state = state.atmt_state
            f.atmt_condname = f.func_name
            f.atmt_ioname = name
            f.atmt_prio = prio
            f.atmt_as_supersocket = as_supersocket
            return f
        return deco
    @staticmethod
    def timeout(state, timeout):
        def deco(f, state=state, timeout=timeout):
            f.atmt_type = ATMT.TIMEOUT
            f.atmt_state = state.atmt_state
            f.atmt_timeout = timeout
            f.atmt_condname = f.func_name
            return f
        return deco

class _ATMT_Command:
    RUN = "RUN"
    NEXT = "NEXT"
    FREEZE = "FREEZE"
    STOP = "STOP"
    END = "END"
    EXCEPTION = "EXCEPTION"
    SINGLESTEP = "SINGLESTEP"
    BREAKPOINT = "BREAKPOINT"
    INTERCEPT = "INTERCEPT"
    ACCEPT = "ACCEPT"
    REPLACE = "REPLACE"
    REJECT = "REJECT"

class _ATMT_supersocket(SuperSocket):
    def __init__(self, name, ioevent, automaton, proto, args, kargs):
        self.name = name
        self.ioevent = ioevent
        self.proto = proto
        self.spa,self.spb = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)
        kargs["external_fd"] = {ioevent:self.spb}
        self.atmt = automaton(*args, **kargs)
        self.atmt.runbg()
    def fileno(self):
        return self.spa.fileno()
    def send(self, s):
        if type(s) is not str:
            s = str(s)
        return self.spa.send(s)
    def recv(self, n=MTU):
        r = self.spa.recv(n)
        if self.proto is not None:
            r = self.proto(r)
        return r
    def close(self):
        pass

class _ATMT_to_supersocket:
    def __init__(self, name, ioevent, automaton):
        self.name = name
        self.ioevent = ioevent
        self.automaton = automaton
    def __call__(self, proto, *args, **kargs):
        return _ATMT_supersocket(self.name, self.ioevent, self.automaton, proto, args, kargs)

class Automaton_metaclass(type):
    def __new__(cls, name, bases, dct):
        cls = super(Automaton_metaclass, cls).__new__(cls, name, bases, dct)
        cls.states={}
        cls.state = None
        cls.recv_conditions={}
        cls.conditions={}
        cls.ioevents={}
        cls.timeout={}
        cls.actions={}
        cls.initial_states=[]
        cls.ionames = []
        cls.iosupersockets = []

        members = {}
        classes = [cls]
        while classes:
            c = classes.pop(0) # order is important to avoid breaking method overloading
            classes += list(c.__bases__)
            for k,v in c.__dict__.iteritems():
                if k not in members:
                    members[k] = v

        decorated = [v for v in members.itervalues()
                     if type(v) is types.FunctionType and hasattr(v, "atmt_type")]
        
        for m in decorated:
            if m.atmt_type == ATMT.STATE:
                s = m.atmt_state
                cls.states[s] = m
                cls.recv_conditions[s]=[]
                cls.ioevents[s]=[]
                cls.conditions[s]=[]
                cls.timeout[s]=[]
                if m.atmt_initial:
                    cls.initial_states.append(m)
            elif m.atmt_type in [ATMT.CONDITION, ATMT.RECV, ATMT.TIMEOUT, ATMT.IOEVENT]:
                cls.actions[m.atmt_condname] = []
    
        for m in decorated:
            if m.atmt_type == ATMT.CONDITION:
                cls.conditions[m.atmt_state].append(m)
            elif m.atmt_type == ATMT.RECV:
                cls.recv_conditions[m.atmt_state].append(m)
            elif m.atmt_type == ATMT.IOEVENT:
                cls.ioevents[m.atmt_state].append(m)
                cls.ionames.append(m.atmt_ioname)
                if m.atmt_as_supersocket is not None:
                    cls.iosupersockets.append(m)
            elif m.atmt_type == ATMT.TIMEOUT:
                cls.timeout[m.atmt_state].append((m.atmt_timeout, m))
            elif m.atmt_type == ATMT.ACTION:
                for c in m.atmt_cond:
                    cls.actions[c].append(m)
            

        for v in cls.timeout.itervalues():
            v.sort(lambda (t1,f1),(t2,f2): cmp(t1,t2))
            v.append((None, None))
        for v in itertools.chain(cls.conditions.itervalues(),
                                 cls.recv_conditions.itervalues(),
                                 cls.ioevents.itervalues()):
            v.sort(lambda c1,c2: cmp(c1.atmt_prio,c2.atmt_prio))
        for condname,actlst in cls.actions.iteritems():
            actlst.sort(lambda c1,c2: cmp(c1.atmt_cond[condname], c2.atmt_cond[condname]))

        for ioev in cls.iosupersockets:
            setattr(cls, ioev.atmt_as_supersocket, _ATMT_to_supersocket(ioev.atmt_as_supersocket, ioev.atmt_ioname, cls))

        return cls

    def graph(self, **kargs):
        s = 'digraph "%s" {\n'  % self.__class__.__name__
        
        se = "" # Keep initial nodes at the begining for better rendering
        for st in self.states.itervalues():
            if st.atmt_initial:
                se = ('\t"%s" [ style=filled, fillcolor=blue, shape=box, root=true];\n' % st.atmt_state)+se
            elif st.atmt_final:
                se += '\t"%s" [ style=filled, fillcolor=green, shape=octagon ];\n' % st.atmt_state
            elif st.atmt_error:
                se += '\t"%s" [ style=filled, fillcolor=red, shape=octagon ];\n' % st.atmt_state
        s += se

        for st in self.states.values():
            for n in st.atmt_origfunc.func_code.co_names+st.atmt_origfunc.func_code.co_consts:
                if n in self.states:
                    s += '\t"%s" -> "%s" [ color=green ];\n' % (st.atmt_state,n)
            

        for c,k,v in ([("purple",k,v) for k,v in self.conditions.items()]+
                      [("red",k,v) for k,v in self.recv_conditions.items()]+
                      [("orange",k,v) for k,v in self.ioevents.items()]):
            for f in v:
                for n in f.func_code.co_names+f.func_code.co_consts:
                    if n in self.states:
                        l = f.atmt_condname
                        for x in self.actions[f.atmt_condname]:
                            l += "\\l>[%s]" % x.func_name
                        s += '\t"%s" -> "%s" [label="%s", color=%s];\n' % (k,n,l,c)
        for k,v in self.timeout.iteritems():
            for t,f in v:
                if f is None:
                    continue
                for n in f.func_code.co_names+f.func_code.co_consts:
                    if n in self.states:
                        l = "%s/%.1fs" % (f.atmt_condname,t)                        
                        for x in self.actions[f.atmt_condname]:
                            l += "\\l>[%s]" % x.func_name
                        s += '\t"%s" -> "%s" [label="%s",color=blue];\n' % (k,n,l)
        s += "}\n"
        return do_graph(s, **kargs)
        


class Automaton:
    __metaclass__ = Automaton_metaclass

    ## Methods to overload
    def parse_args(self, debug=0, store=1, **kargs):
        self.debug_level=debug
        self.socket_kargs = kargs
        self.store_packets = store        

    def master_filter(self, pkt):
        return True

    def my_send(self, pkt):
        self.send_sock.send(pkt)


    ## Utility classes and exceptions
    class _IO_fdwrapper:
        def __init__(self,rd,wr):
            if rd is not None and type(rd) is not int:
                rd = rd.fileno()
            if wr is not None and type(wr) is not int:
                wr = wr.fileno()
            self.rd = rd
            self.wr = wr
        def fileno(self):
            return self.rd
        def read(self, n=65535):
            return os.read(self.rd, n)
        def write(self, msg):
            return os.write(self.wr,msg)
        def recv(self, n=65535):
            return self.read(n)        
        def send(self, msg):
            return self.write(msg)

    class _IO_mixer:
        def __init__(self,rd,wr):
            self.rd = rd
            self.wr = wr
        def fileno(self):
            if type(self.rd) is int:
                return self.rd
            return self.rd.fileno()
        def recv(self, n=None):
            return self.rd.recv(n)
        def read(self, n=None):
            return self.rd.recv(n)        
        def send(self, msg):
            return self.wr.send(msg)
        def write(self, msg):
            return self.wr.send(msg)


    class AutomatonException(Exception):
        def __init__(self, msg, state=None, result=None):
            Exception.__init__(self, msg)
            self.state = state
            self.result = result

    class AutomatonError(AutomatonException):
        pass
    class ErrorState(AutomatonException):
        pass
    class Stuck(AutomatonException):
        pass
    class AutomatonStopped(AutomatonException):
        pass
    
    class Breakpoint(AutomatonStopped):
        pass
    class Singlestep(AutomatonStopped):
        pass
    class InterceptionPoint(AutomatonStopped):
        def __init__(self, msg, state=None, result=None, packet=None):
            Automaton.AutomatonStopped.__init__(self, msg, state=state, result=result)
            self.packet = packet

    class CommandMessage(AutomatonException):
        pass


    ## Services
    def debug(self, lvl, msg):
        if self.debug_level >= lvl:
            log_interactive.debug(msg)            

    def send(self, pkt):
        if self.state.state in self.interception_points:
            self.debug(3,"INTERCEPT: packet intercepted: %s" % pkt.summary())
            self.intercepted_packet = pkt
            cmd = Message(type = _ATMT_Command.INTERCEPT, state=self.state, pkt=pkt)
            self.cmdout.send(cmd)
            cmd = self.cmdin.recv()
            self.intercepted_packet = None
            if cmd.type == _ATMT_Command.REJECT:
                self.debug(3,"INTERCEPT: packet rejected")
                return
            elif cmd.type == _ATMT_Command.REPLACE:
                pkt = cmd.pkt
                self.debug(3,"INTERCEPT: packet replaced by: %s" % pkt.summary())
            elif cmd.type == _ATMT_Command.ACCEPT:
                self.debug(3,"INTERCEPT: packet accepted")
            else:
                raise self.AutomatonError("INTERCEPT: unkown verdict: %r" % cmd.type)
        self.my_send(pkt)
        self.debug(3,"SENT : %s" % pkt.summary())
        self.packets.append(pkt.copy())


    ## Internals
    def __init__(self, *args, **kargs):
        external_fd = kargs.pop("external_fd",{})
        self.send_sock_class = kargs.pop("ll", conf.L3socket)
        self.started = thread.allocate_lock()
        self.threadid = None
        self.breakpointed = None
        self.breakpoints = set()
        self.interception_points = set()
        self.intercepted_packet = None
        self.debug_level=0
        self.init_args=args
        self.init_kargs=kargs
        self.io = type.__new__(type, "IOnamespace",(),{})
        self.oi = type.__new__(type, "IOnamespace",(),{})
        self.cmdin = ObjectPipe()
        self.cmdout = ObjectPipe()
        self.ioin = {}
        self.ioout = {}
        for n in self.ionames:
            extfd = external_fd.get(n)
            if type(extfd) is not tuple:
                extfd = (extfd,extfd)
            ioin,ioout = extfd                
            if ioin is None:
                ioin = ObjectPipe()
            elif type(ioin) is not types.InstanceType:
                ioin = self._IO_fdwrapper(ioin,None)
            if ioout is None:
                ioout = ObjectPipe()
            elif type(ioout) is not types.InstanceType:
                ioout = self._IO_fdwrapper(None,ioout)

            self.ioin[n] = ioin
            self.ioout[n] = ioout 
            ioin.ioname = n
            ioout.ioname = n
            setattr(self.io, n, self._IO_mixer(ioout,ioin))
            setattr(self.oi, n, self._IO_mixer(ioin,ioout))

        for stname in self.states:
            setattr(self, stname, 
                    _instance_state(getattr(self, stname)))
        
        self.parse_args(*args, **kargs)

        self.start()

    def __iter__(self):
        return self        

    def __del__(self):
        self.stop()

    def _run_condition(self, cond, *args, **kargs):
        try:
            self.debug(5, "Trying %s [%s]" % (cond.atmt_type, cond.atmt_condname))
            cond(self,*args, **kargs)
        except ATMT.NewStateRequested, state_req:
            self.debug(2, "%s [%s] taken to state [%s]" % (cond.atmt_type, cond.atmt_condname, state_req.state))
            if cond.atmt_type == ATMT.RECV:
                self.packets.append(args[0])
            for action in self.actions[cond.atmt_condname]:
                self.debug(2, "   + Running action [%s]" % action.func_name)
                action(self, *state_req.action_args, **state_req.action_kargs)
            raise
        except Exception,e:
            self.debug(2, "%s [%s] raised exception [%s]" % (cond.atmt_type, cond.atmt_condname, e))
            raise
        else:
            self.debug(2, "%s [%s] not taken" % (cond.atmt_type, cond.atmt_condname))

    def _do_start(self, *args, **kargs):
        
        thread.start_new_thread(self._do_control, args, kargs)


    def _do_control(self, *args, **kargs):
        with self.started:
            self.threadid = thread.get_ident()

            # Update default parameters
            a = args+self.init_args[len(args):]
            k = self.init_kargs.copy()
            k.update(kargs)
            self.parse_args(*a,**k)
    
            # Start the automaton
            self.state=self.initial_states[0](self)
            self.send_sock = self.send_sock_class()
            self.listen_sock = conf.L2listen(**self.socket_kargs)
            self.packets = PacketList(name="session[%s]"%self.__class__.__name__)

            singlestep = True
            iterator = self._do_iter()
            self.debug(3, "Starting control thread [tid=%i]" % self.threadid)
            try:
                while True:
                    c = self.cmdin.recv()
                    self.debug(5, "Received command %s" % c.type)
                    if c.type == _ATMT_Command.RUN:
                        singlestep = False
                    elif c.type == _ATMT_Command.NEXT:
                        singlestep = True
                    elif c.type == _ATMT_Command.FREEZE:
                        continue
                    elif c.type == _ATMT_Command.STOP:
                        break
                    while True:
                        state = iterator.next()
                        if isinstance(state, self.CommandMessage):
                            break
                        elif isinstance(state, self.Breakpoint):
                            c = Message(type=_ATMT_Command.BREAKPOINT,state=state)
                            self.cmdout.send(c)
                            break
                        if singlestep:
                            c = Message(type=_ATMT_Command.SINGLESTEP,state=state)
                            self.cmdout.send(c)
                            break
            except StopIteration,e:
                c = Message(type=_ATMT_Command.END, result=e.args[0])
                self.cmdout.send(c)
            except Exception,e:
                self.debug(3, "Transfering exception [%s] from tid=%i"% (e,self.threadid))
                m = Message(type = _ATMT_Command.EXCEPTION, exception=e, exc_info=sys.exc_info())
                self.cmdout.send(m)        
            self.debug(3, "Stopping control thread (tid=%i)"%self.threadid)
            self.threadid = None
    
    def _do_iter(self):
        while True:
            try:
                self.debug(1, "## state=[%s]" % self.state.state)
    
                # Entering a new state. First, call new state function
                if self.state.state in self.breakpoints and self.state.state != self.breakpointed: 
                    self.breakpointed = self.state.state
                    yield self.Breakpoint("breakpoint triggered on state %s" % self.state.state,
                                          state = self.state.state)
                self.breakpointed = None
                state_output = self.state.run()
                if self.state.error:
                    raise self.ErrorState("Reached %s: [%r]" % (self.state.state, state_output), 
                                          result=state_output, state=self.state.state)
                if self.state.final:
                    raise StopIteration(state_output)
    
                if state_output is None:
                    state_output = ()
                elif type(state_output) is not list:
                    state_output = state_output,
                
                # Then check immediate conditions
                for cond in self.conditions[self.state.state]:
                    self._run_condition(cond, *state_output)
    
                # If still there and no conditions left, we are stuck!
                if ( len(self.recv_conditions[self.state.state]) == 0 and
                     len(self.ioevents[self.state.state]) == 0 and
                     len(self.timeout[self.state.state]) == 1 ):
                    raise self.Stuck("stuck in [%s]" % self.state.state,
                                     state=self.state.state, result=state_output)
    
                # Finally listen and pay attention to timeouts
                expirations = iter(self.timeout[self.state.state])
                next_timeout,timeout_func = expirations.next()
                t0 = time.time()
                
                fds = [self.cmdin]
                if len(self.recv_conditions[self.state.state]) > 0:
                    fds.append(self.listen_sock)
                for ioev in self.ioevents[self.state.state]:
                    fds.append(self.ioin[ioev.atmt_ioname])
                while 1:
                    t = time.time()-t0
                    if next_timeout is not None:
                        if next_timeout <= t:
                            self._run_condition(timeout_func, *state_output)
                            next_timeout,timeout_func = expirations.next()
                    if next_timeout is None:
                        remain = None
                    else:
                        remain = next_timeout-t
    
                    self.debug(5, "Select on %r" % fds)
                    r,_,_ = select(fds,[],[],remain)
                    self.debug(5, "Selected %r" % r)
                    for fd in r:
                        self.debug(5, "Looking at %r" % fd)
                        if fd == self.cmdin:
                            yield self.CommandMessage("Received command message")
                        elif fd == self.listen_sock:
                            pkt = self.listen_sock.recv(MTU)
                            if pkt is not None:
                                if self.master_filter(pkt):
                                    self.debug(3, "RECVD: %s" % pkt.summary())
                                    for rcvcond in self.recv_conditions[self.state.state]:
                                        self._run_condition(rcvcond, pkt, *state_output)
                                else:
                                    self.debug(4, "FILTR: %s" % pkt.summary())
                        else:
                            self.debug(3, "IOEVENT on %s" % fd.ioname)
                            for ioevt in self.ioevents[self.state.state]:
                                if ioevt.atmt_ioname == fd.ioname:
                                    self._run_condition(ioevt, fd, *state_output)
    
            except ATMT.NewStateRequested,state_req:
                self.debug(2, "switching from [%s] to [%s]" % (self.state.state,state_req.state))
                self.state = state_req
                yield state_req

    ## Public API
    def add_interception_points(self, *ipts):
        for ipt in ipts:
            if hasattr(ipt,"atmt_state"):
                ipt = ipt.atmt_state
            self.interception_points.add(ipt)
        
    def remove_interception_points(self, *ipts):
        for ipt in ipts:
            if hasattr(ipt,"atmt_state"):
                ipt = ipt.atmt_state
            self.interception_points.discard(ipt)

    def add_breakpoints(self, *bps):
        for bp in bps:
            if hasattr(bp,"atmt_state"):
                bp = bp.atmt_state
            self.breakpoints.add(bp)

    def remove_breakpoints(self, *bps):
        for bp in bps:
            if hasattr(bp,"atmt_state"):
                bp = bp.atmt_state
            self.breakpoints.discard(bp)

    def start(self, *args, **kargs):
        if not self.started.locked():
            self._do_start(*args, **kargs)
        
    def run(self, resume=None, wait=True):
        if resume is None:
            resume = Message(type = _ATMT_Command.RUN)
        self.cmdin.send(resume)
        if wait:
            try:
                c = self.cmdout.recv()
            except KeyboardInterrupt:
                self.cmdin.send(Message(type = _ATMT_Command.FREEZE))
                return
            if c.type == _ATMT_Command.END:
                return c.result
            elif c.type == _ATMT_Command.INTERCEPT:
                raise self.InterceptionPoint("packet intercepted", state=c.state.state, packet=c.pkt)
            elif c.type == _ATMT_Command.SINGLESTEP:
                raise self.Singlestep("singlestep state=[%s]"%c.state.state, state=c.state.state)
            elif c.type == _ATMT_Command.BREAKPOINT:
                raise self.Breakpoint("breakpoint triggered on state [%s]"%c.state.state, state=c.state.state)
            elif c.type == _ATMT_Command.EXCEPTION:
                raise c.exc_info[0],c.exc_info[1],c.exc_info[2]

    def runbg(self, resume=None, wait=False):
        self.run(resume, wait)

    def next(self):
        return self.run(resume = Message(type=_ATMT_Command.NEXT))

    def stop(self):
        self.cmdin.send(Message(type=_ATMT_Command.STOP))
        with self.started:
            # Flush command pipes
            while True:
                r,_,_ = select([self.cmdin, self.cmdout],[],[],0)
                if not r:
                    break
                for fd in r:
                    fd.recv()
                
    def restart(self, *args, **kargs):
        self.stop()
        self.start(*args, **kargs)

    def accept_packet(self, pkt=None, wait=False):
        rsm = Message()
        if pkt is None:
            rsm.type = _ATMT_Command.ACCEPT
        else:
            rsm.type = _ATMT_Command.REPLACE
            rsm.pkt = pkt
        return self.run(resume=rsm, wait=wait)

    def reject_packet(self, wait=False):
        rsm = Message(type = _ATMT_Command.REJECT)
        return self.run(resume=rsm, wait=wait)

    


########NEW FILE########
__FILENAME__ = autorun
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Run commands when the Scapy interpreter starts.
"""

import code,sys
from config import conf
from themes import *
from error import Scapy_Exception
from utils import tex_escape


#########################
##### Autorun stuff #####
#########################

class StopAutorun(Scapy_Exception):
    code_run = ""

class ScapyAutorunInterpreter(code.InteractiveInterpreter):
    def __init__(self, *args, **kargs):
        code.InteractiveInterpreter.__init__(self, *args, **kargs)
        self.error = 0
    def showsyntaxerror(self, *args, **kargs):
        self.error = 1
        return code.InteractiveInterpreter.showsyntaxerror(self, *args, **kargs)
    def showtraceback(self, *args, **kargs):
        self.error = 1
        exc_type, exc_value, exc_tb = sys.exc_info()
        if isinstance(exc_value, StopAutorun):
            raise exc_value
        return code.InteractiveInterpreter.showtraceback(self, *args, **kargs)


def autorun_commands(cmds,my_globals=None,verb=0):
    sv = conf.verb
    import __builtin__
    try:
        try:
            if my_globals is None:
                my_globals = __import__("scapy.all").all.__dict__
            conf.verb = verb
            interp = ScapyAutorunInterpreter(my_globals)
            cmd = ""
            cmds = cmds.splitlines()
            cmds.append("") # ensure we finish multiline commands
            cmds.reverse()
            __builtin__.__dict__["_"] = None
            while 1:
                if cmd:
                    sys.stderr.write(sys.__dict__.get("ps2","... "))
                else:
                    sys.stderr.write(str(sys.__dict__.get("ps1",ColorPrompt())))
                    
                l = cmds.pop()
                print l
                cmd += "\n"+l
                if interp.runsource(cmd):
                    continue
                if interp.error:
                    return 0
                cmd = ""
                if len(cmds) <= 1:
                    break
        except SystemExit:
            pass
    finally:
        conf.verb = sv
    return _

def autorun_get_interactive_session(cmds, **kargs):
    class StringWriter:
        def __init__(self):
            self.s = ""
        def write(self, x):
            self.s += x
            
    sw = StringWriter()
    sstdout,sstderr = sys.stdout,sys.stderr
    try:
        try:
            sys.stdout = sys.stderr = sw
            res = autorun_commands(cmds, **kargs)
        except StopAutorun,e:
            e.code_run = sw.s
            raise
    finally:
        sys.stdout,sys.stderr = sstdout,sstderr
    return sw.s,res

def autorun_get_text_interactive_session(cmds, **kargs):
    ct = conf.color_theme
    try:
        conf.color_theme = NoTheme()
        s,res = autorun_get_interactive_session(cmds, **kargs)
    finally:
        conf.color_theme = ct
    return s,res

def autorun_get_ansi_interactive_session(cmds, **kargs):
    ct = conf.color_theme
    try:
        conf.color_theme = DefaultTheme()
        s,res = autorun_get_interactive_session(cmds, **kargs)
    finally:
        conf.color_theme = ct
    return s,res

def autorun_get_html_interactive_session(cmds, **kargs):
    ct = conf.color_theme
    to_html = lambda s: s.replace("<","&lt;").replace(">","&gt;").replace("#[#","<").replace("#]#",">")
    try:
        try:
            conf.color_theme = HTMLTheme2()
            s,res = autorun_get_interactive_session(cmds, **kargs)
        except StopAutorun,e:
            e.code_run = to_html(e.code_run)
            raise
    finally:
        conf.color_theme = ct
    
    return to_html(s),res

def autorun_get_latex_interactive_session(cmds, **kargs):
    ct = conf.color_theme
    to_latex = lambda s: tex_escape(s).replace("@[@","{").replace("@]@","}").replace("@`@","\\")
    try:
        try:
            conf.color_theme = LatexTheme2()
            s,res = autorun_get_interactive_session(cmds, **kargs)
        except StopAutorun,e:
            e.code_run = to_latex(e.code_run)
            raise
    finally:
        conf.color_theme = ct
    return to_latex(s),res



########NEW FILE########
__FILENAME__ = base_classes
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Generators and packet meta classes.
"""

###############
## Generators ##
################

import re,random,socket
import config
import error

class Gen(object):
    def __iter__(self):
        return iter([])
    
class SetGen(Gen):
    def __init__(self, set, _iterpacket=1):
        self._iterpacket=_iterpacket
        if type(set) is list:
            self.set = set
        elif isinstance(set, BasePacketList):
            self.set = list(set)
        else:
            self.set = [set]
    def transf(self, element):
        return element
    def __iter__(self):
        for i in self.set:
            if (type(i) is tuple) and (len(i) == 2) and type(i[0]) is int and type(i[1]) is int:
                if  (i[0] <= i[1]):
                    j=i[0]
                    while j <= i[1]:
                        yield j
                        j += 1
            elif isinstance(i, Gen) and (self._iterpacket or not isinstance(i,BasePacket)):
                for j in i:
                    yield j
            else:
                yield i
    def __repr__(self):
        return "<SetGen %s>" % self.set.__repr__()

class Net(Gen):
    """Generate a list of IPs from a network address or a name"""
    name = "ip"
    ipaddress = re.compile(r"^(\*|[0-2]?[0-9]?[0-9](-[0-2]?[0-9]?[0-9])?)\.(\*|[0-2]?[0-9]?[0-9](-[0-2]?[0-9]?[0-9])?)\.(\*|[0-2]?[0-9]?[0-9](-[0-2]?[0-9]?[0-9])?)\.(\*|[0-2]?[0-9]?[0-9](-[0-2]?[0-9]?[0-9])?)(/[0-3]?[0-9])?$")

    @staticmethod
    def _parse_digit(a,netmask):
        netmask = min(8,max(netmask,0))
        if a == "*":
            a = (0,256)
        elif a.find("-") >= 0:
            x,y = map(int,a.split("-"))
            if x > y:
                y = x
            a = (x &  (0xffL<<netmask) , max(y, (x | (0xffL>>(8-netmask))))+1)
        else:
            a = (int(a) & (0xffL<<netmask),(int(a) | (0xffL>>(8-netmask)))+1)
        return a

    @classmethod
    def _parse_net(cls, net):
        tmp=net.split('/')+["32"]
        if not cls.ipaddress.match(net):
            tmp[0]=socket.gethostbyname(tmp[0])
        netmask = int(tmp[1])
        return map(lambda x,y: cls._parse_digit(x,y), tmp[0].split("."), map(lambda x,nm=netmask: x-nm, (8,16,24,32))),netmask

    def __init__(self, net):
        self.repr=net
        self.parsed,self.netmask = self._parse_net(net)


                                                                                               
    def __iter__(self):
        for d in xrange(*self.parsed[3]):
            for c in xrange(*self.parsed[2]):
                for b in xrange(*self.parsed[1]):
                    for a in xrange(*self.parsed[0]):
                        yield "%i.%i.%i.%i" % (a,b,c,d)
    def choice(self):
        ip = []
        for v in self.parsed:
            ip.append(str(random.randint(v[0],v[1]-1)))
        return ".".join(ip) 
                          
    def __repr__(self):
        return "Net(%r)" % self.repr
    def __eq__(self, other):
        if hasattr(other, "parsed"):
            p2 = other.parsed
        else:
            p2,nm2 = self._parse_net(other)
        return self.parsed == p2
    def __contains__(self, other):
        if hasattr(other, "parsed"):
            p2 = other.parsed
        else:
            p2,nm2 = self._parse_net(other)
        for (a1,b1),(a2,b2) in zip(self.parsed,p2):
            if a1 > a2 or b1 < b2:
                return False
        return True
    def __rcontains__(self, other):        
        return self in self.__class__(other)
        

class OID(Gen):
    name = "OID"
    def __init__(self, oid):
        self.oid = oid        
        self.cmpt = []
        fmt = []        
        for i in oid.split("."):
            if "-" in i:
                fmt.append("%i")
                self.cmpt.append(tuple(map(int, i.split("-"))))
            else:
                fmt.append(i)
        self.fmt = ".".join(fmt)
    def __repr__(self):
        return "OID(%r)" % self.oid
    def __iter__(self):        
        ii = [k[0] for k in self.cmpt]
        while 1:
            yield self.fmt % tuple(ii)
            i = 0
            while 1:
                if i >= len(ii):
                    raise StopIteration
                if ii[i] < self.cmpt[i][1]:
                    ii[i]+=1
                    break
                else:
                    ii[i] = self.cmpt[i][0]
                i += 1


 
######################################
## Packet abstract and base classes ##
######################################

class Packet_metaclass(type):
    def __new__(cls, name, bases, dct):
        if "fields_desc" in dct: # perform resolution of references to other packets
            current_fld = dct["fields_desc"]
            resolved_fld = []
            for f in current_fld:
                if isinstance(f, Packet_metaclass): # reference to another fields_desc
                    for f2 in f.fields_desc:
                        resolved_fld.append(f2)
                else:
                    resolved_fld.append(f)
        else: # look for a field_desc in parent classes
            resolved_fld = None
            for b in bases:
                if hasattr(b,"fields_desc"):
                    resolved_fld = b.fields_desc
                    break

        if resolved_fld: # perform default value replacements
            final_fld = []
            for f in resolved_fld:
                if f.name in dct:
                    f = f.copy()
                    f.default = dct[f.name]
                    del(dct[f.name])
                final_fld.append(f)

            dct["fields_desc"] = final_fld

        newcls = super(Packet_metaclass, cls).__new__(cls, name, bases, dct)
        if hasattr(newcls,"register_variant"):
            newcls.register_variant()
        for f in newcls.fields_desc:                
            f.register_owner(newcls)
        config.conf.layers.register(newcls)
        return newcls

    def __getattr__(self, attr):
        for k in self.fields_desc:
            if k.name == attr:
                return k
        raise AttributeError(attr)

    def __call__(cls, *args, **kargs):
        if "dispatch_hook" in cls.__dict__:
            cls =  cls.dispatch_hook(*args, **kargs)
        i = cls.__new__(cls, cls.__name__, cls.__bases__, cls.__dict__)
        i.__init__(*args, **kargs)
        return i


class NewDefaultValues(Packet_metaclass):
    """NewDefaultValues is deprecated (not needed anymore)
    
    remove this:
        __metaclass__ = NewDefaultValues
    and it should still work.
    """    
    def __new__(cls, name, bases, dct):
        from error import log_loading
        import traceback
        try:
            for tb in traceback.extract_stack()+[("??",-1,None,"")]:
                f,l,_,line = tb
                if line.startswith("class"):
                    break
        except:
            f,l="??",-1
            raise
        log_loading.warning("Deprecated (no more needed) use of NewDefaultValues  (%s l. %i)." % (f,l))
        
        return super(NewDefaultValues, cls).__new__(cls, name, bases, dct)

class BasePacket(Gen):
    pass


#############################
## Packet list base classe ##
#############################

class BasePacketList:
    pass




########NEW FILE########
__FILENAME__ = config
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Implementation for of the configuration object.
"""

import os,time,socket,sys
from data import *
import base_classes
import themes
from error import log_scapy

############
## Config ##
############

class ConfClass(object):
    def configure(self, cnf):
        self.__dict__ = cnf.__dict__.copy()
    def __repr__(self):
        return str(self)
    def __str__(self):
        s=""
        keys = self.__class__.__dict__.copy()
        keys.update(self.__dict__)
        keys = keys.keys()
        keys.sort()
        for i in keys:
            if i[0] != "_":
                r = repr(getattr(self, i))
                r = " ".join(r.split())
                wlen = 76-max(len(i),10)
                if len(r) > wlen:
                    r = r[:wlen-3]+"..."
                s += "%-10s = %s\n" % (i, r)
        return s[:-1]

class Interceptor(object):
    def __init__(self, name, default, hook, args=None, kargs=None):
        self.name = name
        self.intname = "_intercepted_%s" % name
        self.default=default
        self.hook = hook
        self.args = args if args is not None else []
        self.kargs = kargs if kargs is not None else {}
    def __get__(self, obj, typ=None):
        if not hasattr(obj, self.intname):
            setattr(obj, self.intname, self.default)
        return getattr(obj, self.intname)
    def __set__(self, obj, val):
        setattr(obj, self.intname, val)
        self.hook(self.name, val, *self.args, **self.kargs)

    
class ProgPath(ConfClass):
    pdfreader = "acroread"
    psreader = "gv"
    dot = "dot"
    display = "display"
    tcpdump = "tcpdump"
    tcpreplay = "tcpreplay"
    hexedit = "hexer"
    wireshark = "wireshark"


class ConfigFieldList:
    def __init__(self):
        self.fields = set()
        self.layers = set()
    @staticmethod
    def _is_field(f):
        return hasattr(f, "owners")
    def _recalc_layer_list(self):
        self.layers = set([owner for f in self.fields for owner in f.owners])
    def add(self, *flds):
        self.fields |= set([f for f in flds if self._is_field(f)])
        self._recalc_layer_list()
    def remove(self, *flds):
        self.fields -= set(flds)
        self._recalc_layer_list()
    def __contains__(self, elt):
        if isinstance(elt, base_classes.Packet_metaclass):
            return elt in self.layers
        return elt in self.fields
    def __repr__(self):
        return "<%s [%s]>" %  (self.__class__.__name__," ".join(str(x) for x in self.fields))

class Emphasize(ConfigFieldList):
    pass

class Resolve(ConfigFieldList):
    pass
    

class Num2Layer:
    def __init__(self):
        self.num2layer = {}
        self.layer2num = {}
        
    def register(self, num, layer):
        self.register_num2layer(num, layer)
        self.register_layer2num(num, layer)
        
    def register_num2layer(self, num, layer):
        self.num2layer[num] = layer
    def register_layer2num(self, num, layer):
        self.layer2num[layer] = num

    def __getitem__(self, item):
        if isinstance(item, base_classes.Packet_metaclass):
            return self.layer2num[item]
        return self.num2layer[item]
    def __contains__(self, item):
        if isinstance(item, base_classes.Packet_metaclass):
            return item in self.layer2num
        return item in self.num2layer
    def get(self, item, default=None):
        if item in self:
            return self[item]
        return default
    
    def __repr__(self):
        lst = []
        for num,layer in self.num2layer.iteritems():
            if layer in self.layer2num and self.layer2num[layer] == num:
                dir = "<->"
            else:
                dir = " ->"
            lst.append((num,"%#6x %s %-20s (%s)" % (num,dir,layer.__name__,layer.name)))
        for layer,num in self.layer2num.iteritems():
            if num not in self.num2layer or self.num2layer[num] != layer:
                lst.append((num,"%#6x <-  %-20s (%s)" % (num,layer.__name__,layer.name)))
        lst.sort()
        return "\n".join(y for x,y in lst)
            

class LayersList(list):
    def __repr__(self):
        s=[]
        for l in self:
            s.append("%-20s: %s" % (l.__name__,l.name))
        return "\n".join(s)
    def register(self, layer):
        self.append(layer)

class CommandsList(list):
    def __repr__(self):
        s=[]
        for l in sorted(self,key=lambda x:x.__name__):
            if l.__doc__:
                doc = l.__doc__.split("\n")[0]
            else:
                doc = "--"
            s.append("%-20s: %s" % (l.__name__,doc))
        return "\n".join(s)
    def register(self, cmd):
        self.append(cmd)
        return cmd # return cmd so that method can be used as a decorator

def lsc():
    print repr(conf.commands)

class CacheInstance(dict):
    def __init__(self, name="noname", timeout=None):
        self.timeout = timeout
        self.name = name
        self._timetable = {}
    def __getitem__(self, item):
        val = dict.__getitem__(self,item)
        if self.timeout is not None:
            t = self._timetable[item]
            if time.time()-t > self.timeout:
                raise KeyError(item)
        return val
    def get(self, item, default=None):
        # overloading this method is needed to force the dict to go through
        # the timetable check
        try:
            return self[item]
        except KeyError:
            return default
    def __setitem__(self, item, v):
        self._timetable[item] = time.time()
        dict.__setitem__(self, item,v)
    def update(self, other):
        dict.update(self, other)
        self._timetable.update(other._timetable)
    def iteritems(self):
        if self.timeout is None:
            return dict.iteritems(self)
        t0=time.time()
        return ((k,v) for (k,v) in dict.iteritems(self) if t0-self._timetable[k] < self.timeout) 
    def iterkeys(self):
        if self.timeout is None:
            return dict.iterkeys(self)
        t0=time.time()
        return (k for k in dict.iterkeys(self) if t0-self._timetable[k] < self.timeout)
    def __iter__(self):
        return self.iterkeys()
    def itervalues(self):
        if self.timeout is None:
            return dict.itervalues(self)
        t0=time.time()
        return (v for (k,v) in dict.iteritems(self) if t0-self._timetable[k] < self.timeout)
    def items(self):
        if self.timeout is None:
            return dict.items(self)
        t0=time.time()
        return [(k,v) for (k,v) in dict.iteritems(self) if t0-self._timetable[k] < self.timeout]
    def keys(self):
        if self.timeout is None:
            return dict.keys(self)
        t0=time.time()
        return [k for k in dict.iterkeys(self) if t0-self._timetable[k] < self.timeout]
    def values(self):
        if self.timeout is None:
            return dict.values(self)
        t0=time.time()
        return [v for (k,v) in dict.iteritems(self) if t0-self._timetable[k] < self.timeout]
    def __len__(self):
        if self.timeout is None:
            return dict.__len__(self)
        return len(self.keys())
    def summary(self):
        return "%s: %i valid items. Timeout=%rs" % (self.name, len(self), self.timeout)
    def __repr__(self):
        s = []
        if self:
            mk = max(len(k) for k in self.iterkeys())
            fmt = "%%-%is %%s" % (mk+1)
            for item in self.iteritems():
                s.append(fmt % item)
        return "\n".join(s)
            
            


class NetCache:
    def __init__(self):
        self._caches_list = []


    def add_cache(self, cache):
        self._caches_list.append(cache)
        setattr(self,cache.name,cache)
    def new_cache(self, name, timeout=None):
        c = CacheInstance(name=name, timeout=timeout)
        self.add_cache(c)
    def __delattr__(self, attr):
        raise AttributeError("Cannot delete attributes")
    def update(self, other):
        for co in other._caches_list:
            if hasattr(self, co.name):
                getattr(self,co.name).update(co)
            else:
                self.add_cache(co.copy())
    def flush(self):
        for c in self._caches_list:
            c.flush()
    def __repr__(self):
        return "\n".join(c.summary() for c in self._caches_list)
        

class LogLevel(object):
    def __get__(self, obj, otype):
        return obj._logLevel
    def __set__(self,obj,val):
        log_scapy.setLevel(val)
        obj._logLevel = val
        


def _prompt_changer(attr,val):
    prompt = conf.prompt
    try:
        ct = val
        if isinstance(ct, AnsiColorTheme) and ct.prompt(""):
            ## ^A and ^B delimit invisible caracters for readline to count right.
            ## And we need ct.prompt() to do change something or else ^A and ^B will be
            ## displayed
             prompt = "\001%s\002" % ct.prompt("\002"+prompt+"\001")
        else:
            prompt = ct.prompt(prompt)
    except:
        pass
    sys.ps1 = prompt

class Conf(ConfClass):
    """This object contains the configuration of scapy.
session  : filename where the session will be saved
interactive_shell : If set to "ipython", use IPython as shell. Default: Python 
stealth  : if 1, prevents any unwanted packet to go out (ARP, DNS, ...)
checkIPID: if 0, doesn't check that IPID matches between IP sent and ICMP IP citation received
           if 1, checks that they either are equal or byte swapped equals (bug in some IP stacks)
           if 2, strictly checks that they are equals
checkIPsrc: if 1, checks IP src in IP and ICMP IP citation match (bug in some NAT stacks)
check_TCPerror_seqack: if 1, also check that TCP seq and ack match the ones in ICMP citation
iff      : selects the default output interface for srp() and sendp(). default:"eth0")
verb     : level of verbosity, from 0 (almost mute) to 3 (verbose)
promisc  : default mode for listening socket (to get answers if you spoof on a lan)
sniff_promisc : default mode for sniff()
filter   : bpf filter added to every sniffing socket to exclude traffic from analysis
histfile : history file
padding  : includes padding in desassembled packets
except_filter : BPF filter for packets to ignore
debug_match : when 1, store received packet that are not matched into debug.recv
route    : holds the Scapy routing table and provides methods to manipulate it
warning_threshold : how much time between warnings from the same place
ASN1_default_codec: Codec used by default for ASN1 objects
mib      : holds MIB direct access dictionnary
resolve   : holds list of fields for which resolution should be done
noenum    : holds list of enum fields for which conversion to string should NOT be done
AS_resolver: choose the AS resolver class to use
extensions_paths: path or list of paths where extensions are to be looked for
"""
    version = "2.1.1-dev"
    session = ""
    interactive = False
    interactive_shell = ""
    stealth = "not implemented"
    iface = None
    readfunc = None
    layers = LayersList()
    commands = CommandsList()
    logLevel = LogLevel()
    checkIPID = 0
    checkIPsrc = 1
    checkIPaddr = 1
    check_TCPerror_seqack = 0
    verb = 2
    prompt = ">>> "
    promisc = 1
    sniff_promisc = 1
    raw_layer = None
    raw_summary = False
    default_l2 = None
    l2types = Num2Layer()
    l3types = Num2Layer()
    L3socket = None
    L2socket = None
    L2listen = None
    histfile = os.path.join(os.path.expanduser("~"), ".scapy_history")
    padding = 1
    except_filter = ""
    debug_match = 0
    wepkey = ""
    route = None # Filed by route.py
    route6 = None # Filed by route6.py
    auto_fragment = 1
    debug_dissector = 0
    color_theme = Interceptor("color_theme", themes.NoTheme(), _prompt_changer)
    warning_threshold = 5
    prog = ProgPath()
    resolve = Resolve()
    noenum = Resolve()
    emph = Emphasize()
    use_pcap = False
    use_dnet = False
    ipv6_enabled = socket.has_ipv6
    ethertypes = ETHER_TYPES
    protocols = IP_PROTOS
    services_tcp = TCP_SERVICES
    services_udp = UDP_SERVICES
    extensions_paths = "."
    manufdb = MANUFDB
    stats_classic_protocols = []
    stats_dot11_protocols = []
    temp_files = []
    netcache = NetCache()
    load_layers = ["l2", "inet", "dhcp", "dns", "dot11", "gprs", "hsrp", "inet6", "ir", "isakmp", "l2tp",
                   "mgcp", "mobileip", "netbios", "netflow", "ntp", "ppp", "radius", "rip", "rtp",
                   "sebek", "skinny", "smb", "snmp", "tftp", "x509", "bluetooth", "dhcp6", "llmnr", "sctp", "vrrp" ]
    

if not Conf.ipv6_enabled:
    log_scapy.warning("IPv6 support disabled in Python. Cannot load scapy IPv6 layers.")
    for m in ["inet6","dhcp6"]:
        if m in Conf.load_layers:
            Conf.load_layers.remove(m)
    

conf=Conf()
conf.logLevel=30 # 30=Warning


########NEW FILE########
__FILENAME__ = cert
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Arnaud Ebalard <arno@natisbad.org>
## This program is published under a GPLv2 license

"""
Cryptographic certificates.
"""

import os, sys, math, socket, struct, sha, hmac, string, time
import random, popen2, tempfile
from scapy.utils import strxor
try:
    HAS_HASHLIB=True
    import hashlib
except:
    HAS_HASHLIB=False

from Crypto.PublicKey import *
from Crypto.Cipher import *
from Crypto.Hash import *

# Maximum allowed size in bytes for a certificate file, to avoid
# loading huge file when importing a cert
MAX_KEY_SIZE=50*1024
MAX_CERT_SIZE=50*1024
MAX_CRL_SIZE=10*1024*1024   # some are that big

#####################################################################
# Some helpers
#####################################################################

def warning(m):
    print "WARNING: %s" % m

def randstring(l):
    """
    Returns a random string of length l (l >= 0)
    """
    tmp = map(lambda x: struct.pack("B", random.randrange(0, 256, 1)), [""]*l)
    return "".join(tmp)

def zerofree_randstring(l):
    """
    Returns a random string of length l (l >= 0) without zero in it. 
    """
    tmp = map(lambda x: struct.pack("B", random.randrange(1, 256, 1)), [""]*l)
    return "".join(tmp)

def strand(s1, s2):
    """
    Returns the binary AND of the 2 provided strings s1 and s2. s1 and s2
    must be of same length.
    """
    return "".join(map(lambda x,y:chr(ord(x)&ord(y)), s1, s2))

# OS2IP function defined in RFC 3447 for octet string to integer conversion
def pkcs_os2ip(x):
    """
    Accepts a byte string as input parameter and return the associated long
    value:

    Input : x        octet string to be converted

    Output: x        corresponding nonnegative integer

    Reverse function is pkcs_i2osp()
    """
    return RSA.number.bytes_to_long(x) 

# IP2OS function defined in RFC 3447 for octet string to integer conversion
def pkcs_i2osp(x,xLen):
    """
    Converts a long (the first parameter) to the associated byte string
    representation of length l (second parameter). Basically, the length
    parameters allow the function to perform the associated padding.

    Input : x        nonnegative integer to be converted
            xLen     intended length of the resulting octet string

    Output: x        corresponding nonnegative integer

    Reverse function is pkcs_os2ip().
    """
    z = RSA.number.long_to_bytes(x)
    padlen = max(0, xLen-len(z))
    return '\x00'*padlen + z

# for every hash function a tuple is provided, giving access to 
# - hash output length in byte
# - associated hash function that take data to be hashed as parameter
#   XXX I do not provide update() at the moment.
# - DER encoding of the leading bits of digestInfo (the hash value
#   will be concatenated to create the complete digestInfo).
# 
# Notes:
# - MD4 asn.1 value should be verified. Also, as stated in 
#   PKCS#1 v2.1, MD4 should not be used.
# - hashlib is available from http://code.krypto.org/python/hashlib/
# - 'tls' one is the concatenation of both md5 and sha1 hashes used
#   by SSL/TLS when signing/verifying things
_hashFuncParams = {
    "md2"    : (16, 
                lambda x: MD2.new(x).digest(), 
                '\x30\x20\x30\x0c\x06\x08\x2a\x86\x48\x86\xf7\x0d\x02\x02\x05\x00\x04\x10'),
    "md4"    : (16, 
                lambda x: MD4.new(x).digest(), 
                '\x30\x20\x30\x0c\x06\x08\x2a\x86\x48\x86\xf7\x0d\x02\x04\x05\x00\x04\x10'), # is that right ?
    "md5"    : (16, 
                lambda x: MD5.new(x).digest(), 
                '\x30\x20\x30\x0c\x06\x08\x2a\x86\x48\x86\xf7\x0d\x02\x05\x05\x00\x04\x10'),
    "sha1"   : (20,
                lambda x: SHA.new(x).digest(), 
                '\x30\x21\x30\x09\x06\x05\x2b\x0e\x03\x02\x1a\x05\x00\x04\x14'),
    "tls"    : (36,
                lambda x: MD5.new(x).digest() + SHA.new(x).digest(),
                '') }

if HAS_HASHLIB:
    _hashFuncParams["sha224"] = (28, 
                lambda x: hashlib.sha224(x).digest(),
                '\x30\x2d\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x04\x05\x00\x04\x1c')
    _hashFuncParams["sha256"] = (32, 
                lambda x: hashlib.sha256(x).digest(), 
                '\x30\x31\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x01\x05\x00\x04\x20')
    _hashFuncParams["sha384"] = (48, 
                lambda x: hashlib.sha384(x).digest(),
               '\x30\x41\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x02\x05\x00\x04\x30')
    _hashFuncParams["sha512"] = (64, 
               lambda x: hashlib.sha512(x).digest(),
               '\x30\x51\x30\x0d\x06\x09\x60\x86\x48\x01\x65\x03\x04\x02\x03\x05\x00\x04\x40')
else:
    warning("hashlib support is not available. Consider installing it")
    warning("if you need sha224, sha256, sha384 and sha512 algs.")
    
def pkcs_mgf1(mgfSeed, maskLen, h):
    """
    Implements generic MGF1 Mask Generation function as described in
    Appendix B.2.1 of RFC 3447. The hash function is passed by name.
    valid values are 'md2', 'md4', 'md5', 'sha1', 'tls, 'sha256',
    'sha384' and 'sha512'. Returns None on error.

    Input:
       mgfSeed: seed from which mask is generated, an octet string
       maskLen: intended length in octets of the mask, at most 2^32 * hLen
                hLen (see below)
       h      : hash function name (in 'md2', 'md4', 'md5', 'sha1', 'tls',
                'sha256', 'sha384'). hLen denotes the length in octets of
                the hash function output.

    Output:
       an octet string of length maskLen
    """

    # steps are those of Appendix B.2.1
    if not _hashFuncParams.has_key(h):
        warning("pkcs_mgf1: invalid hash (%s) provided")
        return None
    hLen = _hashFuncParams[h][0]
    hFunc = _hashFuncParams[h][1]
    if maskLen > 2**32 * hLen:                               # 1)
        warning("pkcs_mgf1: maskLen > 2**32 * hLen")         
        return None
    T = ""                                                   # 2)
    maxCounter = math.ceil(float(maskLen) / float(hLen))     # 3)
    counter = 0
    while counter < maxCounter:
        C = pkcs_i2osp(counter, 4)
        T += hFunc(mgfSeed + C)
        counter += 1
    return T[:maskLen]


def pkcs_emsa_pss_encode(M, emBits, h, mgf, sLen): 
    """
    Implements EMSA-PSS-ENCODE() function described in Sect. 9.1.1 of RFC 3447

    Input:
       M     : message to be encoded, an octet string
       emBits: maximal bit length of the integer resulting of pkcs_os2ip(EM),
               where EM is the encoded message, output of the function.
       h     : hash function name (in 'md2', 'md4', 'md5', 'sha1', 'tls',
               'sha256', 'sha384'). hLen denotes the length in octets of
               the hash function output. 
       mgf   : the mask generation function f : seed, maskLen -> mask
       sLen  : intended length in octets of the salt

    Output:
       encoded message, an octet string of length emLen = ceil(emBits/8)

    On error, None is returned.
    """

    # 1) is not done
    hLen = _hashFuncParams[h][0]                             # 2)
    hFunc = _hashFuncParams[h][1]
    mHash = hFunc(M)
    emLen = int(math.ceil(emBits/8.))
    if emLen < hLen + sLen + 2:                              # 3)
        warning("encoding error (emLen < hLen + sLen + 2)")
        return None
    salt = randstring(sLen)                                  # 4)
    MPrime = '\x00'*8 + mHash + salt                         # 5)
    H = hFunc(MPrime)                                        # 6)
    PS = '\x00'*(emLen - sLen - hLen - 2)                    # 7)
    DB = PS + '\x01' + salt                                  # 8)
    dbMask = mgf(H, emLen - hLen - 1)                        # 9)
    maskedDB = strxor(DB, dbMask)                            # 10)
    l = (8*emLen - emBits)/8                                 # 11)
    rem = 8*emLen - emBits - 8*l # additionnal bits
    andMask = l*'\x00'
    if rem:
        j = chr(reduce(lambda x,y: x+y, map(lambda x: 1<<x, range(8-rem))))
        andMask += j
        l += 1
    maskedDB = strand(maskedDB[:l], andMask) + maskedDB[l:]
    EM = maskedDB + H + '\xbc'                               # 12)
    return EM                                                # 13)


def pkcs_emsa_pss_verify(M, EM, emBits, h, mgf, sLen):
    """
    Implements EMSA-PSS-VERIFY() function described in Sect. 9.1.2 of RFC 3447

    Input:
       M     : message to be encoded, an octet string
       EM    : encoded message, an octet string of length emLen = ceil(emBits/8)
       emBits: maximal bit length of the integer resulting of pkcs_os2ip(EM)
       h     : hash function name (in 'md2', 'md4', 'md5', 'sha1', 'tls',
               'sha256', 'sha384'). hLen denotes the length in octets of
               the hash function output.
       mgf   : the mask generation function f : seed, maskLen -> mask
       sLen  : intended length in octets of the salt

    Output:
       True if the verification is ok, False otherwise.
    """
    
    # 1) is not done
    hLen = _hashFuncParams[h][0]                             # 2)
    hFunc = _hashFuncParams[h][1]
    mHash = hFunc(M)
    emLen = int(math.ceil(emBits/8.))                        # 3)
    if emLen < hLen + sLen + 2:
        return False
    if EM[-1] != '\xbc':                                     # 4)
        return False
    l = emLen - hLen - 1                                     # 5)
    maskedDB = EM[:l]
    H = EM[l:l+hLen]
    l = (8*emLen - emBits)/8                                 # 6)
    rem = 8*emLen - emBits - 8*l # additionnal bits
    andMask = l*'\xff'
    if rem:
        val = reduce(lambda x,y: x+y, map(lambda x: 1<<x, range(8-rem)))
        j = chr(~val & 0xff)
        andMask += j
        l += 1
    if strand(maskedDB[:l], andMask) != '\x00'*l:
        return False
    dbMask = mgf(H, emLen - hLen - 1)                        # 7)
    DB = strxor(maskedDB, dbMask)                            # 8)
    l = (8*emLen - emBits)/8                                 # 9)
    rem = 8*emLen - emBits - 8*l # additionnal bits
    andMask = l*'\x00'
    if rem:
        j = chr(reduce(lambda x,y: x+y, map(lambda x: 1<<x, range(8-rem))))
        andMask += j
        l += 1
    DB = strand(DB[:l], andMask) + DB[l:]
    l = emLen - hLen - sLen - 1                              # 10)
    if DB[:l] != '\x00'*(l-1) + '\x01':
        return False
    salt = DB[-sLen:]                                        # 11)
    MPrime = '\x00'*8 + mHash + salt                         # 12)
    HPrime = hFunc(MPrime)                                   # 13)
    return H == HPrime                                       # 14)


def pkcs_emsa_pkcs1_v1_5_encode(M, emLen, h): # section 9.2 of RFC 3447
    """
    Implements EMSA-PKCS1-V1_5-ENCODE() function described in Sect.
    9.2 of RFC 3447.

    Input:
       M    : message to be encode, an octet string
       emLen: intended length in octets of the encoded message, at least
              tLen + 11, where tLen is the octet length of the DER encoding
              T of a certain value computed during the encoding operation.
       h    : hash function name (in 'md2', 'md4', 'md5', 'sha1', 'tls',
              'sha256', 'sha384'). hLen denotes the length in octets of
              the hash function output.

    Output:
       encoded message, an octet string of length emLen

    On error, None is returned.
    """
    hLen = _hashFuncParams[h][0]                             # 1)
    hFunc = _hashFuncParams[h][1]
    H = hFunc(M)
    hLeadingDigestInfo = _hashFuncParams[h][2]               # 2)
    T = hLeadingDigestInfo + H
    tLen = len(T)
    if emLen < tLen + 11:                                    # 3)
        warning("pkcs_emsa_pkcs1_v1_5_encode: intended encoded message length too short")
        return None
    PS = '\xff'*(emLen - tLen - 3)                           # 4)
    EM = '\x00' + '\x01' + PS + '\x00' + T                   # 5)
    return EM                                                # 6)


# XXX should add other pgf1 instance in a better fashion.

def create_ca_file(anchor_list, filename):
    """
    Concatenate all the certificates (PEM format for the export) in
    'anchor_list' and write the result to file 'filename'. On success
    'filename' is returned, None otherwise.

    If you are used to OpenSSL tools, this function builds a CAfile
    that can be used for certificate and CRL check.

    Also see create_temporary_ca_file().
    """
    try:
        f = open(filename, "w")
        for a in anchor_list:
            s = a.output(fmt="PEM")
            f.write(s)
        f.close()
    except:
        return None
    return filename

def create_temporary_ca_file(anchor_list):
    """
    Concatenate all the certificates (PEM format for the export) in
    'anchor_list' and write the result to file to a temporary file
    using mkstemp() from tempfile module. On success 'filename' is
    returned, None otherwise.

    If you are used to OpenSSL tools, this function builds a CAfile
    that can be used for certificate and CRL check.

    Also see create_temporary_ca_file().
    """
    try:
        f, fname = tempfile.mkstemp()
        for a in anchor_list:
            s = a.output(fmt="PEM")
            l = os.write(f, s)
        os.close(f)
    except:
        return None
    return fname

def create_temporary_ca_path(anchor_list, folder):
    """
    Create a CA path folder as defined in OpenSSL terminology, by
    storing all certificates in 'anchor_list' list in PEM format
    under provided 'folder' and then creating the associated links
    using the hash as usually done by c_rehash.

    Note that you can also include CRL in 'anchor_list'. In that
    case, they will also be stored under 'folder' and associated
    links will be created.

    In folder, the files are created with names of the form
    0...ZZ.pem. If you provide an empty list, folder will be created
    if it does not already exist, but that's all.

    The number of certificates written to folder is returned on
    success, None on error.
    """
    # We should probably avoid writing duplicate anchors and also
    # check if they are all certs.
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder)
    except:
        return None
    
    l = len(anchor_list)
    if l == 0:
        return None
    fmtstr = "%%0%sd.pem" % math.ceil(math.log(l, 10))
    i = 0
    try:
        for a in anchor_list:
            fname = os.path.join(folder, fmtstr % i)
            f = open(fname, "w")
            s = a.output(fmt="PEM")
            f.write(s)
            f.close()
            i += 1
    except:
        return None

    r,w=popen2.popen2("c_rehash %s" % folder)
    r.close(); w.close()

    return l


#####################################################################
# Public Key Cryptography related stuff
#####################################################################

class OSSLHelper:
    def _apply_ossl_cmd(self, osslcmd, rawdata):
        r,w=popen2.popen2(osslcmd)
        w.write(rawdata)
        w.close()
        res = r.read()
        r.close()
        return res

class _EncryptAndVerify:
    ### Below are encryption methods

    def _rsaep(self, m):
        """
        Internal method providing raw RSA encryption, i.e. simple modular
        exponentiation of the given message representative 'm', a long
        between 0 and n-1.

        This is the encryption primitive RSAEP described in PKCS#1 v2.1,
        i.e. RFC 3447 Sect. 5.1.1.

        Input:
           m: message representative, a long between 0 and n-1, where
              n is the key modulus.

        Output:
           ciphertext representative, a long between 0 and n-1

        Not intended to be used directly. Please, see encrypt() method.
        """

        n = self.modulus
        if type(m) is int:
            m = long(m)
        if type(m) is not long or m > n-1:
            warning("Key._rsaep() expects a long between 0 and n-1")
            return None

        return self.key.encrypt(m, "")[0]


    def _rsaes_pkcs1_v1_5_encrypt(self, M):
        """
        Implements RSAES-PKCS1-V1_5-ENCRYPT() function described in section
        7.2.1 of RFC 3447.

        Input:
           M: message to be encrypted, an octet string of length mLen, where
              mLen <= k - 11 (k denotes the length in octets of the key modulus)

        Output:
           ciphertext, an octet string of length k

        On error, None is returned.
        """

        # 1) Length checking
        mLen = len(M)
        k = self.modulusLen / 8
        if mLen > k - 11:
            warning("Key._rsaes_pkcs1_v1_5_encrypt(): message too "
                    "long (%d > %d - 11)" % (mLen, k))
            return None

        # 2) EME-PKCS1-v1_5 encoding
        PS = zerofree_randstring(k - mLen - 3)      # 2.a)
        EM = '\x00' + '\x02' + PS + '\x00' + M      # 2.b)

        # 3) RSA encryption
        m = pkcs_os2ip(EM)                          # 3.a)
        c = self._rsaep(m)                          # 3.b)
        C = pkcs_i2osp(c, k)                        # 3.c)

        return C                                    # 4)


    def _rsaes_oaep_encrypt(self, M, h=None, mgf=None, L=None):
        """
        Internal method providing RSAES-OAEP-ENCRYPT as defined in Sect.
        7.1.1 of RFC 3447. Not intended to be used directly. Please, see
        encrypt() method for type "OAEP".


        Input:
           M  : message to be encrypted, an octet string of length mLen
                where mLen <= k - 2*hLen - 2 (k denotes the length in octets
                of the RSA modulus and hLen the length in octets of the hash
                function output)
           h  : hash function name (in 'md2', 'md4', 'md5', 'sha1', 'tls',
                'sha256', 'sha384'). hLen denotes the length in octets of
                the hash function output. 'sha1' is used by default if not
                provided.
           mgf: the mask generation function f : seed, maskLen -> mask
           L  : optional label to be associated with the message; the default
                value for L, if not provided is the empty string

        Output:
           ciphertext, an octet string of length k

        On error, None is returned.
        """
        # The steps below are the one described in Sect. 7.1.1 of RFC 3447.
        # 1) Length Checking
                                                    # 1.a) is not done
        mLen = len(M)
        if h is None:
            h = "sha1"
        if not _hashFuncParams.has_key(h):
            warning("Key._rsaes_oaep_encrypt(): unknown hash function %s.", h)
            return None
        hLen = _hashFuncParams[h][0]
        hFun = _hashFuncParams[h][1]
        k = self.modulusLen / 8
        if mLen > k - 2*hLen - 2:                   # 1.b)
            warning("Key._rsaes_oaep_encrypt(): message too long.")
            return None
        
        # 2) EME-OAEP encoding
        if L is None:                               # 2.a)
            L = ""
        lHash = hFun(L)
        PS = '\x00'*(k - mLen - 2*hLen - 2)         # 2.b)
        DB = lHash + PS + '\x01' + M                # 2.c)
        seed = randstring(hLen)                     # 2.d)
        if mgf is None:                             # 2.e)
            mgf = lambda x,y: pkcs_mgf1(x,y,h)
        dbMask = mgf(seed, k - hLen - 1)
        maskedDB = strxor(DB, dbMask)               # 2.f)
        seedMask = mgf(maskedDB, hLen)              # 2.g)
        maskedSeed = strxor(seed, seedMask)         # 2.h)
        EM = '\x00' + maskedSeed + maskedDB         # 2.i)

        # 3) RSA Encryption
        m = pkcs_os2ip(EM)                          # 3.a)
        c = self._rsaep(m)                          # 3.b)
        C = pkcs_i2osp(c, k)                        # 3.c)

        return C                                    # 4)


    def encrypt(self, m, t=None, h=None, mgf=None, L=None):
        """
        Encrypt message 'm' using 't' encryption scheme where 't' can be:

        - None: the message 'm' is directly applied the RSAEP encryption
                primitive, as described in PKCS#1 v2.1, i.e. RFC 3447
                Sect 5.1.1. Simply put, the message undergo a modular
                exponentiation using the public key. Additionnal method
                parameters are just ignored.

        - 'pkcs': the message 'm' is applied RSAES-PKCS1-V1_5-ENCRYPT encryption
                scheme as described in section 7.2.1 of RFC 3447. In that
                context, other parameters ('h', 'mgf', 'l') are not used.

        - 'oaep': the message 'm' is applied the RSAES-OAEP-ENCRYPT encryption
                scheme, as described in PKCS#1 v2.1, i.e. RFC 3447 Sect
                7.1.1. In that context,

                o 'h' parameter provides the name of the hash method to use.
                  Possible values are "md2", "md4", "md5", "sha1", "tls",
                  "sha224", "sha256", "sha384" and "sha512". if none is provided,
                  sha1 is used.

                o 'mgf' is the mask generation function. By default, mgf
                  is derived from the provided hash function using the
                  generic MGF1 (see pkcs_mgf1() for details).

                o 'L' is the optional label to be associated with the
                  message. If not provided, the default value is used, i.e
                  the empty string. No check is done on the input limitation
                  of the hash function regarding the size of 'L' (for
                  instance, 2^61 - 1 for SHA-1). You have been warned.
        """

        if t is None: # Raw encryption
            m = pkcs_os2ip(m)
            c = self._rsaep(m)
            return pkcs_i2osp(c, self.modulusLen/8)
        
        elif t == "pkcs":
            return self._rsaes_pkcs1_v1_5_encrypt(m)
        
        elif t == "oaep":
            return self._rsaes_oaep_encrypt(m, h, mgf, L)

        else:
            warning("Key.encrypt(): Unknown encryption type (%s) provided" % t)
            return None

    ### Below are verification related methods

    def _rsavp1(self, s):
        """
        Internal method providing raw RSA verification, i.e. simple modular
        exponentiation of the given signature representative 'c', an integer
        between 0 and n-1.

        This is the signature verification primitive RSAVP1 described in
        PKCS#1 v2.1, i.e. RFC 3447 Sect. 5.2.2.

        Input:
          s: signature representative, an integer between 0 and n-1,
             where n is the key modulus.

        Output:
           message representative, an integer between 0 and n-1

        Not intended to be used directly. Please, see verify() method.
        """
        return self._rsaep(s)

    def _rsassa_pss_verify(self, M, S, h=None, mgf=None, sLen=None):
        """
        Implements RSASSA-PSS-VERIFY() function described in Sect 8.1.2
        of RFC 3447

        Input:
           M: message whose signature is to be verified
           S: signature to be verified, an octet string of length k, where k
              is the length in octets of the RSA modulus n.

        Output:
           True is the signature is valid. False otherwise.
        """

        # Set default parameters if not provided
        if h is None: # By default, sha1
            h = "sha1"
        if not _hashFuncParams.has_key(h):
            warning("Key._rsassa_pss_verify(): unknown hash function "
                    "provided (%s)" % h)
            return False
        if mgf is None: # use mgf1 with underlying hash function
            mgf = lambda x,y: pkcs_mgf1(x, y, h)
        if sLen is None: # use Hash output length (A.2.3 of RFC 3447)
            hLen = _hashFuncParams[h][0]
            sLen = hLen

        # 1) Length checking
        modBits = self.modulusLen
        k = modBits / 8
        if len(S) != k:
            return False

        # 2) RSA verification
        s = pkcs_os2ip(S)                           # 2.a)
        m = self._rsavp1(s)                         # 2.b)
        emLen = math.ceil((modBits - 1) / 8.)       # 2.c)
        EM = pkcs_i2osp(m, emLen) 

        # 3) EMSA-PSS verification
        Result = pkcs_emsa_pss_verify(M, EM, modBits - 1, h, mgf, sLen)

        return Result                               # 4)


    def _rsassa_pkcs1_v1_5_verify(self, M, S, h):
        """
        Implements RSASSA-PKCS1-v1_5-VERIFY() function as described in
        Sect. 8.2.2 of RFC 3447.

        Input:
           M: message whose signature is to be verified, an octet string
           S: signature to be verified, an octet string of length k, where
              k is the length in octets of the RSA modulus n
           h: hash function name (in 'md2', 'md4', 'md5', 'sha1', 'tls',
                'sha256', 'sha384').
           
        Output:
           True if the signature is valid. False otherwise.
        """

        # 1) Length checking
        k = self.modulusLen / 8
        if len(S) != k:
            warning("invalid signature (len(S) != k)")
            return False

        # 2) RSA verification
        s = pkcs_os2ip(S)                           # 2.a)
        m = self._rsavp1(s)                         # 2.b)
        EM = pkcs_i2osp(m, k)                       # 2.c)

        # 3) EMSA-PKCS1-v1_5 encoding
        EMPrime = pkcs_emsa_pkcs1_v1_5_encode(M, k, h)
        if EMPrime is None:
            warning("Key._rsassa_pkcs1_v1_5_verify(): unable to encode.")
            return False

        # 4) Comparison
        return EM == EMPrime


    def verify(self, M, S, t=None, h=None, mgf=None, sLen=None):
        """
        Verify alleged signature 'S' is indeed the signature of message 'M' using
        't' signature scheme where 't' can be:

        - None: the alleged signature 'S' is directly applied the RSAVP1 signature
                primitive, as described in PKCS#1 v2.1, i.e. RFC 3447 Sect
                5.2.1. Simply put, the provided signature is applied a moular
                exponentiation using the public key. Then, a comparison of the
                result is done against 'M'. On match, True is returned.
                Additionnal method parameters are just ignored.

        - 'pkcs': the alleged signature 'S' and message 'M' are applied
                RSASSA-PKCS1-v1_5-VERIFY signature verification scheme as
                described in Sect. 8.2.2 of RFC 3447. In that context,
                the hash function name is passed using 'h'. Possible values are
                "md2", "md4", "md5", "sha1", "tls", "sha224", "sha256", "sha384"
                and "sha512". If none is provided, sha1 is used. Other additionnal
                parameters are ignored.

        - 'pss': the alleged signature 'S' and message 'M' are applied
                RSASSA-PSS-VERIFY signature scheme as described in Sect. 8.1.2.
                of RFC 3447. In that context,

                o 'h' parameter provides the name of the hash method to use.
                   Possible values are "md2", "md4", "md5", "sha1", "tls", "sha224",
                   "sha256", "sha384" and "sha512". if none is provided, sha1
                   is used. 

                o 'mgf' is the mask generation function. By default, mgf
                   is derived from the provided hash function using the
                   generic MGF1 (see pkcs_mgf1() for details).

                o 'sLen' is the length in octet of the salt. You can overload the
                  default value (the octet length of the hash value for provided
                  algorithm) by providing another one with that parameter.
        """
        if t is None: # RSAVP1
            S = pkcs_os2ip(S)
            n = self.modulus
            if S > n-1:
                warning("Signature to be verified is too long for key modulus")
                return False
            m = self._rsavp1(S)
            if m is None:
                return False
            l = int(math.ceil(math.log(m, 2) / 8.)) # Hack
            m = pkcs_i2osp(m, l)
            return M == m

        elif t == "pkcs": # RSASSA-PKCS1-v1_5-VERIFY
            if h is None:
                h = "sha1"
            return self._rsassa_pkcs1_v1_5_verify(M, S, h)

        elif t == "pss": # RSASSA-PSS-VERIFY
            return self._rsassa_pss_verify(M, S, h, mgf, sLen)

        else:
            warning("Key.verify(): Unknown signature type (%s) provided" % t)
            return None
    
class _DecryptAndSignMethods(OSSLHelper):
    ### Below are decryption related methods. Encryption ones are inherited
    ### from PubKey

    def _rsadp(self, c):
        """
        Internal method providing raw RSA decryption, i.e. simple modular
        exponentiation of the given ciphertext representative 'c', a long
        between 0 and n-1.

        This is the decryption primitive RSADP described in PKCS#1 v2.1,
        i.e. RFC 3447 Sect. 5.1.2.

        Input:
           c: ciphertest representative, a long between 0 and n-1, where
              n is the key modulus.

        Output:
           ciphertext representative, a long between 0 and n-1

        Not intended to be used directly. Please, see encrypt() method.
        """

        n = self.modulus
        if type(c) is int:
            c = long(c)        
        if type(c) is not long or c > n-1:
            warning("Key._rsaep() expects a long between 0 and n-1")
            return None

        return self.key.decrypt(c)    


    def _rsaes_pkcs1_v1_5_decrypt(self, C):
        """
        Implements RSAES-PKCS1-V1_5-DECRYPT() function described in section
        7.2.2 of RFC 3447.

        Input:
           C: ciphertext to be decrypted, an octet string of length k, where
              k is the length in octets of the RSA modulus n.

        Output:
           an octet string of length k at most k - 11

        on error, None is returned.
        """
        
        # 1) Length checking
        cLen = len(C)
        k = self.modulusLen / 8
        if cLen != k or k < 11:
            warning("Key._rsaes_pkcs1_v1_5_decrypt() decryption error "
                    "(cLen != k or k < 11)")
            return None

        # 2) RSA decryption
        c = pkcs_os2ip(C)                           # 2.a)
        m = self._rsadp(c)                          # 2.b)
        EM = pkcs_i2osp(m, k)                       # 2.c)

        # 3) EME-PKCS1-v1_5 decoding

        # I am aware of the note at the end of 7.2.2 regarding error
        # conditions reporting but the one provided below are for _local_
        # debugging purposes. --arno
        
        if EM[0] != '\x00':
            warning("Key._rsaes_pkcs1_v1_5_decrypt(): decryption error "
                    "(first byte is not 0x00)")
            return None

        if EM[1] != '\x02':
            warning("Key._rsaes_pkcs1_v1_5_decrypt(): decryption error "
                    "(second byte is not 0x02)")
            return None

        tmp = EM[2:].split('\x00', 1)
        if len(tmp) != 2:
            warning("Key._rsaes_pkcs1_v1_5_decrypt(): decryption error "
                    "(no 0x00 to separate PS from M)")
            return None

        PS, M = tmp
        if len(PS) < 8:
            warning("Key._rsaes_pkcs1_v1_5_decrypt(): decryption error "
                    "(PS is less than 8 byte long)")
            return None

        return M                                    # 4)


    def _rsaes_oaep_decrypt(self, C, h=None, mgf=None, L=None):
        """
        Internal method providing RSAES-OAEP-DECRYPT as defined in Sect.
        7.1.2 of RFC 3447. Not intended to be used directly. Please, see
        encrypt() method for type "OAEP".


        Input:
           C  : ciphertext to be decrypted, an octet string of length k, where
                k = 2*hLen + 2 (k denotes the length in octets of the RSA modulus
                and hLen the length in octets of the hash function output)
           h  : hash function name (in 'md2', 'md4', 'md5', 'sha1', 'tls',
                'sha256', 'sha384'). 'sha1' is used if none is provided.
           mgf: the mask generation function f : seed, maskLen -> mask
           L  : optional label whose association with the message is to be
                verified; the default value for L, if not provided is the empty
                string.

        Output:
           message, an octet string of length k mLen, where mLen <= k - 2*hLen - 2

        On error, None is returned.
        """
        # The steps below are the one described in Sect. 7.1.2 of RFC 3447.

        # 1) Length Checking
                                                    # 1.a) is not done
        if h is None:
            h = "sha1"
        if not _hashFuncParams.has_key(h):
            warning("Key._rsaes_oaep_decrypt(): unknown hash function %s.", h)
            return None
        hLen = _hashFuncParams[h][0]
        hFun = _hashFuncParams[h][1]
        k = self.modulusLen / 8
        cLen = len(C)
        if cLen != k:                               # 1.b)
            warning("Key._rsaes_oaep_decrypt(): decryption error. "
                    "(cLen != k)")
            return None
        if k < 2*hLen + 2:
            warning("Key._rsaes_oaep_decrypt(): decryption error. "
                    "(k < 2*hLen + 2)")
            return None

        # 2) RSA decryption
        c = pkcs_os2ip(C)                           # 2.a)
        m = self._rsadp(c)                          # 2.b)
        EM = pkcs_i2osp(m, k)                       # 2.c)

        # 3) EME-OAEP decoding
        if L is None:                               # 3.a)
            L = ""
        lHash = hFun(L)
        Y = EM[:1]                                  # 3.b)
        if Y != '\x00':
            warning("Key._rsaes_oaep_decrypt(): decryption error. "
                    "(Y is not zero)")
            return None
        maskedSeed = EM[1:1+hLen]
        maskedDB = EM[1+hLen:]
        if mgf is None:
            mgf = lambda x,y: pkcs_mgf1(x, y, h)
        seedMask = mgf(maskedDB, hLen)              # 3.c)
        seed = strxor(maskedSeed, seedMask)         # 3.d)
        dbMask = mgf(seed, k - hLen - 1)            # 3.e)
        DB = strxor(maskedDB, dbMask)               # 3.f)

        # I am aware of the note at the end of 7.1.2 regarding error
        # conditions reporting but the one provided below are for _local_
        # debugging purposes. --arno

        lHashPrime = DB[:hLen]                      # 3.g)
        tmp = DB[hLen:].split('\x01', 1)
        if len(tmp) != 2:
            warning("Key._rsaes_oaep_decrypt(): decryption error. "
                    "(0x01 separator not found)")
            return None
        PS, M = tmp
        if PS != '\x00'*len(PS):
            warning("Key._rsaes_oaep_decrypt(): decryption error. "
                    "(invalid padding string)")
            return None
        if lHash != lHashPrime:
            warning("Key._rsaes_oaep_decrypt(): decryption error. "
                    "(invalid hash)")
            return None            
        return M                                    # 4)


    def decrypt(self, C, t=None, h=None, mgf=None, L=None):
        """
        Decrypt ciphertext 'C' using 't' decryption scheme where 't' can be:

        - None: the ciphertext 'C' is directly applied the RSADP decryption
                primitive, as described in PKCS#1 v2.1, i.e. RFC 3447
                Sect 5.1.2. Simply, put the message undergo a modular
                exponentiation using the private key. Additionnal method
                parameters are just ignored.

        - 'pkcs': the ciphertext 'C' is applied RSAES-PKCS1-V1_5-DECRYPT
                decryption scheme as described in section 7.2.2 of RFC 3447.
                In that context, other parameters ('h', 'mgf', 'l') are not
                used.

        - 'oaep': the ciphertext 'C' is applied the RSAES-OAEP-DECRYPT decryption
                scheme, as described in PKCS#1 v2.1, i.e. RFC 3447 Sect
                7.1.2. In that context,

                o 'h' parameter provides the name of the hash method to use.
                  Possible values are "md2", "md4", "md5", "sha1", "tls",
                  "sha224", "sha256", "sha384" and "sha512". if none is provided,
                  sha1 is used by default.

                o 'mgf' is the mask generation function. By default, mgf
                  is derived from the provided hash function using the
                  generic MGF1 (see pkcs_mgf1() for details).

                o 'L' is the optional label to be associated with the
                  message. If not provided, the default value is used, i.e
                  the empty string. No check is done on the input limitation
                  of the hash function regarding the size of 'L' (for
                  instance, 2^61 - 1 for SHA-1). You have been warned.        
        """
        if t is None:
            C = pkcs_os2ip(C)
            c = self._rsadp(C)
            l = int(math.ceil(math.log(c, 2) / 8.)) # Hack
            return pkcs_i2osp(c, l)

        elif t == "pkcs":
            return self._rsaes_pkcs1_v1_5_decrypt(C)

        elif t == "oaep":
            return self._rsaes_oaep_decrypt(C, h, mgf, L)

        else:
            warning("Key.decrypt(): Unknown decryption type (%s) provided" % t)
            return None

    ### Below are signature related methods. Verification ones are inherited from
    ### PubKey

    def _rsasp1(self, m):
        """
        Internal method providing raw RSA signature, i.e. simple modular
        exponentiation of the given message representative 'm', an integer
        between 0 and n-1.

        This is the signature primitive RSASP1 described in PKCS#1 v2.1,
        i.e. RFC 3447 Sect. 5.2.1.

        Input:
           m: message representative, an integer between 0 and n-1, where
              n is the key modulus.

        Output:
           signature representative, an integer between 0 and n-1

        Not intended to be used directly. Please, see sign() method.
        """
        return self._rsadp(m)


    def _rsassa_pss_sign(self, M, h=None, mgf=None, sLen=None):
        """
        Implements RSASSA-PSS-SIGN() function described in Sect. 8.1.1 of
        RFC 3447.

        Input:
           M: message to be signed, an octet string

        Output:
           signature, an octet string of length k, where k is the length in
           octets of the RSA modulus n.

        On error, None is returned.
        """

        # Set default parameters if not provided
        if h is None: # By default, sha1
            h = "sha1"
        if not _hashFuncParams.has_key(h):
            warning("Key._rsassa_pss_sign(): unknown hash function "
                    "provided (%s)" % h)
            return None
        if mgf is None: # use mgf1 with underlying hash function
            mgf = lambda x,y: pkcs_mgf1(x, y, h)
        if sLen is None: # use Hash output length (A.2.3 of RFC 3447)
            hLen = _hashFuncParams[h][0]
            sLen = hLen

        # 1) EMSA-PSS encoding
        modBits = self.modulusLen
        k = modBits / 8
        EM = pkcs_emsa_pss_encode(M, modBits - 1, h, mgf, sLen)
        if EM is None:
            warning("Key._rsassa_pss_sign(): unable to encode")
            return None

        # 2) RSA signature
        m = pkcs_os2ip(EM)                          # 2.a)
        s = self._rsasp1(m)                         # 2.b)
        S = pkcs_i2osp(s, k)                        # 2.c)

        return S                                    # 3)


    def _rsassa_pkcs1_v1_5_sign(self, M, h):
        """
        Implements RSASSA-PKCS1-v1_5-SIGN() function as described in
        Sect. 8.2.1 of RFC 3447.

        Input:
           M: message to be signed, an octet string
           h: hash function name (in 'md2', 'md4', 'md5', 'sha1', 'tls'
                'sha256', 'sha384').
           
        Output:
           the signature, an octet string.
        """
        
        # 1) EMSA-PKCS1-v1_5 encoding
        k = self.modulusLen / 8
        EM = pkcs_emsa_pkcs1_v1_5_encode(M, k, h)
        if EM is None:
            warning("Key._rsassa_pkcs1_v1_5_sign(): unable to encode")
            return None

        # 2) RSA signature
        m = pkcs_os2ip(EM)                          # 2.a)
        s = self._rsasp1(m)                         # 2.b)
        S = pkcs_i2osp(s, k)                        # 2.c)

        return S                                    # 3)


    def sign(self, M, t=None, h=None, mgf=None, sLen=None):
        """
        Sign message 'M' using 't' signature scheme where 't' can be:

        - None: the message 'M' is directly applied the RSASP1 signature
                primitive, as described in PKCS#1 v2.1, i.e. RFC 3447 Sect
                5.2.1. Simply put, the message undergo a modular exponentiation
                using the private key. Additionnal method parameters are just
                ignored.

        - 'pkcs': the message 'M' is applied RSASSA-PKCS1-v1_5-SIGN signature
                scheme as described in Sect. 8.2.1 of RFC 3447. In that context,
                the hash function name is passed using 'h'. Possible values are
                "md2", "md4", "md5", "sha1", "tls", "sha224", "sha256", "sha384"
                and "sha512". If none is provided, sha1 is used. Other additionnal 
                parameters are ignored.

        - 'pss' : the message 'M' is applied RSASSA-PSS-SIGN signature scheme as
                described in Sect. 8.1.1. of RFC 3447. In that context,

                o 'h' parameter provides the name of the hash method to use.
                   Possible values are "md2", "md4", "md5", "sha1", "tls", "sha224",
                   "sha256", "sha384" and "sha512". if none is provided, sha1
                   is used. 

                o 'mgf' is the mask generation function. By default, mgf
                   is derived from the provided hash function using the
                   generic MGF1 (see pkcs_mgf1() for details).

                o 'sLen' is the length in octet of the salt. You can overload the
                  default value (the octet length of the hash value for provided
                  algorithm) by providing another one with that parameter.
        """

        if t is None: # RSASP1
            M = pkcs_os2ip(M)
            n = self.modulus
            if M > n-1:
                warning("Message to be signed is too long for key modulus")
                return None
            s = self._rsasp1(M)
            if s is None:
                return None
            return pkcs_i2osp(s, self.modulusLen/8)
        
        elif t == "pkcs": # RSASSA-PKCS1-v1_5-SIGN
            if h is None:
                h = "sha1"
            return self._rsassa_pkcs1_v1_5_sign(M, h)
        
        elif t == "pss": # RSASSA-PSS-SIGN
            return self._rsassa_pss_sign(M, h, mgf, sLen)

        else:
            warning("Key.sign(): Unknown signature type (%s) provided" % t)
            return None




class PubKey(OSSLHelper, _EncryptAndVerify):
    # Below are the fields we recognize in the -text output of openssl
    # and from which we extract information. We expect them in that
    # order. Number of spaces does matter.
    possible_fields = [ "Modulus (",
                        "Exponent:" ]
    possible_fields_count = len(possible_fields)
    
    def __init__(self, keypath):
        error_msg = "Unable to import key."

        # XXX Temporary hack to use PubKey inside Cert
        if type(keypath) is tuple:
            e, m, mLen = keypath
            self.modulus = m
            self.modulusLen = mLen
            self.pubExp = e
            return

        fields_dict = {}
        for k in self.possible_fields:
            fields_dict[k] = None

        self.keypath = None
        rawkey = None

        if (not '\x00' in keypath) and os.path.isfile(keypath): # file
            self.keypath = keypath
            key_size = os.path.getsize(keypath)
            if key_size > MAX_KEY_SIZE:
                raise Exception(error_msg)
            try:
                f = open(keypath)
                rawkey = f.read()
                f.close()
            except:
                raise Exception(error_msg)     
        else:
            rawkey = keypath

        if rawkey is None:
            raise Exception(error_msg)

        self.rawkey = rawkey

        # Let's try to get file format : PEM or DER.
        fmtstr = 'openssl rsa -text -pubin -inform %s -noout '
        convertstr = 'openssl rsa -pubin -inform %s -outform %s 2>/dev/null'
        key_header = "-----BEGIN PUBLIC KEY-----"
        key_footer = "-----END PUBLIC KEY-----"
        l = rawkey.split(key_header, 1)
        if len(l) == 2: # looks like PEM
            tmp = l[1]
            l = tmp.split(key_footer, 1)
            if len(l) == 2:
                tmp = l[0]
                rawkey = "%s%s%s\n" % (key_header, tmp, key_footer)
            else:
                raise Exception(error_msg)
            r,w,e = popen2.popen3(fmtstr % "PEM")
            w.write(rawkey)
            w.close()
            textkey = r.read()
            r.close()
            res = e.read()
            e.close()
            if res == '':
                self.format = "PEM"
                self.pemkey = rawkey
                self.textkey = textkey
                cmd = convertstr % ("PEM", "DER")
                self.derkey = self._apply_ossl_cmd(cmd, rawkey)
            else:
                raise Exception(error_msg)
        else: # not PEM, try DER
            r,w,e = popen2.popen3(fmtstr % "DER")            
            w.write(rawkey)
            w.close()
            textkey = r.read()
            r.close()
            res = e.read()
            if res == '':
                self.format = "DER"
                self.derkey = rawkey
                self.textkey = textkey
                cmd = convertstr % ("DER", "PEM")
                self.pemkey = self._apply_ossl_cmd(cmd, rawkey)
                cmd = convertstr % ("DER", "DER")
                self.derkey = self._apply_ossl_cmd(cmd, rawkey)                
            else:
                try: # Perhaps it is a cert
                    c = Cert(keypath)
                except:
                    raise Exception(error_msg)
                # TODO:
                # Reconstruct a key (der and pem) and provide:
                # self.format
                # self.derkey
                # self.pemkey
                # self.textkey
                # self.keypath

        self.osslcmdbase = 'openssl rsa -pubin -inform %s ' % self.format

        self.keypath = keypath

        # Parse the -text output of openssl to make things available
        l = self.textkey.split('\n', 1)
        if len(l) != 2:
            raise Exception(error_msg)
        cur, tmp = l
        i = 0
        k = self.possible_fields[i] # Modulus (
        cur = cur[len(k):] + '\n'
        while k:
            l = tmp.split('\n', 1)
            if len(l) != 2: # Over
                fields_dict[k] = cur
                break
            l, tmp = l

            newkey = 0
            # skip fields we have already seen, this is the purpose of 'i'
            for j in range(i, self.possible_fields_count):
                f = self.possible_fields[j]
                if l.startswith(f):
                    fields_dict[k] = cur
                    cur = l[len(f):] + '\n'
                    k = f
                    newkey = 1
                    i = j+1
                    break
            if newkey == 1:
                continue
            cur += l + '\n'

        # modulus and modulus length
        v = fields_dict["Modulus ("]
        self.modulusLen = None
        if v:
            v, rem = v.split(' bit):', 1)
            self.modulusLen = int(v)
            rem = rem.replace('\n','').replace(' ','').replace(':','')
            self.modulus = long(rem, 16)
        if self.modulus is None:
            raise Exception(error_msg)
        
        # public exponent
        v = fields_dict["Exponent:"]
        self.pubExp = None
        if v:
            self.pubExp = long(v.split('(', 1)[0])
        if self.pubExp is None:
            raise Exception(error_msg)

        self.key = RSA.construct((self.modulus, self.pubExp, ))

    def __str__(self):
        return self.derkey


class Key(OSSLHelper, _DecryptAndSignMethods, _EncryptAndVerify):
    # Below are the fields we recognize in the -text output of openssl
    # and from which we extract information. We expect them in that
    # order. Number of spaces does matter.
    possible_fields = [ "Private-Key: (",
                        "modulus:",
                        "publicExponent:",
                        "privateExponent:",
                        "prime1:",
                        "prime2:",
                        "exponent1:",
                        "exponent2:",
                        "coefficient:" ]
    possible_fields_count = len(possible_fields)
    
    def __init__(self, keypath):
        error_msg = "Unable to import key."

        fields_dict = {}
        for k in self.possible_fields:
            fields_dict[k] = None

        self.keypath = None
        rawkey = None

        if (not '\x00' in keypath) and os.path.isfile(keypath):
            self.keypath = keypath
            key_size = os.path.getsize(keypath)
            if key_size > MAX_KEY_SIZE:
                raise Exception(error_msg)
            try:
                f = open(keypath)
                rawkey = f.read()
                f.close()
            except:
                raise Exception(error_msg)     
        else:
            rawkey = keypath

        if rawkey is None:
            raise Exception(error_msg)

        self.rawkey = rawkey

        # Let's try to get file format : PEM or DER.
        fmtstr = 'openssl rsa -text -inform %s -noout '
        convertstr = 'openssl rsa -inform %s -outform %s 2>/dev/null'
        key_header = "-----BEGIN RSA PRIVATE KEY-----"
        key_footer = "-----END RSA PRIVATE KEY-----"
        l = rawkey.split(key_header, 1)
        if len(l) == 2: # looks like PEM
            tmp = l[1]
            l = tmp.split(key_footer, 1)
            if len(l) == 2:
                tmp = l[0]
                rawkey = "%s%s%s\n" % (key_header, tmp, key_footer)
            else:
                raise Exception(error_msg)
            r,w,e = popen2.popen3(fmtstr % "PEM")
            w.write(rawkey)
            w.close()
            textkey = r.read()
            r.close()
            res = e.read()
            e.close()
            if res == '':
                self.format = "PEM"
                self.pemkey = rawkey
                self.textkey = textkey
                cmd = convertstr % ("PEM", "DER")
                self.derkey = self._apply_ossl_cmd(cmd, rawkey)
            else:
                raise Exception(error_msg)
        else: # not PEM, try DER
            r,w,e = popen2.popen3(fmtstr % "DER")            
            w.write(rawkey)
            w.close()
            textkey = r.read()
            r.close()
            res = e.read()
            if res == '':
                self.format = "DER"
                self.derkey = rawkey
                self.textkey = textkey
                cmd = convertstr % ("DER", "PEM")
                self.pemkey = self._apply_ossl_cmd(cmd, rawkey)
                cmd = convertstr % ("DER", "DER")
                self.derkey = self._apply_ossl_cmd(cmd, rawkey)
            else:
                raise Exception(error_msg)     

        self.osslcmdbase = 'openssl rsa -inform %s ' % self.format

        r,w,e = popen2.popen3('openssl asn1parse -inform DER ')
        w.write(self.derkey)
        w.close()
        self.asn1parsekey = r.read()
        r.close()
        res = e.read()
        e.close()
        if res != '':
            raise Exception(error_msg)

        self.keypath = keypath

        # Parse the -text output of openssl to make things available
        l = self.textkey.split('\n', 1)
        if len(l) != 2:
            raise Exception(error_msg)
        cur, tmp = l
        i = 0
        k = self.possible_fields[i] # Private-Key: (
        cur = cur[len(k):] + '\n'
        while k:
            l = tmp.split('\n', 1)
            if len(l) != 2: # Over
                fields_dict[k] = cur
                break
            l, tmp = l

            newkey = 0
            # skip fields we have already seen, this is the purpose of 'i'
            for j in range(i, self.possible_fields_count):
                f = self.possible_fields[j]
                if l.startswith(f):
                    fields_dict[k] = cur
                    cur = l[len(f):] + '\n'
                    k = f
                    newkey = 1
                    i = j+1
                    break
            if newkey == 1:
                continue
            cur += l + '\n'

        # modulus length
        v = fields_dict["Private-Key: ("]
        self.modulusLen = None
        if v:
            self.modulusLen = int(v.split(' bit', 1)[0])
        if self.modulusLen is None:
            raise Exception(error_msg)
        
        # public exponent
        v = fields_dict["publicExponent:"]
        self.pubExp = None
        if v:
            self.pubExp = long(v.split('(', 1)[0])
        if self.pubExp is None:
            raise Exception(error_msg)

        tmp = {}
        for k in ["modulus:", "privateExponent:", "prime1:", "prime2:",
                  "exponent1:", "exponent2:", "coefficient:"]:
            v = fields_dict[k]
            if v:
                s = v.replace('\n', '').replace(' ', '').replace(':', '')
                tmp[k] = long(s, 16)
            else:
                raise Exception(error_msg)

        self.modulus     = tmp["modulus:"]
        self.privExp     = tmp["privateExponent:"]
        self.prime1      = tmp["prime1:"]
        self.prime2      = tmp["prime2:"] 
        self.exponent1   = tmp["exponent1:"]
        self.exponent2   = tmp["exponent2:"]
        self.coefficient = tmp["coefficient:"]

        self.key = RSA.construct((self.modulus, self.pubExp, self.privExp))

    def __str__(self):
        return self.derkey


# We inherit from PubKey to get access to all encryption and verification
# methods. To have that working, we simply need Cert to provide 
# modulusLen and key attribute.
# XXX Yes, it is a hack.
class Cert(OSSLHelper, _EncryptAndVerify):
    # Below are the fields we recognize in the -text output of openssl
    # and from which we extract information. We expect them in that
    # order. Number of spaces does matter.
    possible_fields = [ "        Version:",
                        "        Serial Number:",
                        "        Signature Algorithm:",
                        "        Issuer:",
                        "            Not Before:",
                        "            Not After :",
                        "        Subject:",
                        "            Public Key Algorithm:",
                        "                Modulus (",
                        "                Exponent:",
                        "            X509v3 Subject Key Identifier:",
                        "            X509v3 Authority Key Identifier:",
                        "                keyid:",
                        "                DirName:",
                        "                serial:",
                        "            X509v3 Basic Constraints:",
                        "            X509v3 Key Usage:",
                        "            X509v3 Extended Key Usage:",
                        "            X509v3 CRL Distribution Points:",
                        "            Authority Information Access:",
                        "    Signature Algorithm:" ]
    possible_fields_count = len(possible_fields)
    
    def __init__(self, certpath):
        error_msg = "Unable to import certificate."

        fields_dict = {}
        for k in self.possible_fields:
            fields_dict[k] = None

        self.certpath = None
        rawcert = None

        if (not '\x00' in certpath) and os.path.isfile(certpath): # file
            self.certpath = certpath
            cert_size = os.path.getsize(certpath)
            if cert_size > MAX_CERT_SIZE:
                raise Exception(error_msg)
            try:
                f = open(certpath)
                rawcert = f.read()
                f.close()
            except:
                raise Exception(error_msg)     
        else:
            rawcert = certpath
            
        if rawcert is None:
            raise Exception(error_msg)

        self.rawcert = rawcert

        # Let's try to get file format : PEM or DER.
        fmtstr = 'openssl x509 -text -inform %s -noout '
        convertstr = 'openssl x509 -inform %s -outform %s '
        cert_header = "-----BEGIN CERTIFICATE-----"
        cert_footer = "-----END CERTIFICATE-----"
        l = rawcert.split(cert_header, 1)
        if len(l) == 2: # looks like PEM
            tmp = l[1]
            l = tmp.split(cert_footer, 1)
            if len(l) == 2:
                tmp = l[0]
                rawcert = "%s%s%s\n" % (cert_header, tmp, cert_footer)
            else:
                raise Exception(error_msg)
            r,w,e = popen2.popen3(fmtstr % "PEM")
            w.write(rawcert)
            w.close()
            textcert = r.read()
            r.close()
            res = e.read()
            e.close()
            if res == '':
                self.format = "PEM"
                self.pemcert = rawcert
                self.textcert = textcert
                cmd = convertstr % ("PEM", "DER")
                self.dercert = self._apply_ossl_cmd(cmd, rawcert)
            else:
                raise Exception(error_msg)
        else: # not PEM, try DER
            r,w,e = popen2.popen3(fmtstr % "DER")            
            w.write(rawcert)
            w.close()
            textcert = r.read()
            r.close()
            res = e.read()
            if res == '':
                self.format = "DER"
                self.dercert = rawcert
                self.textcert = textcert
                cmd = convertstr % ("DER", "PEM")
                self.pemcert = self._apply_ossl_cmd(cmd, rawcert)
                cmd = convertstr % ("DER", "DER")                
                self.dercert = self._apply_ossl_cmd(cmd, rawcert)
            else:
                raise Exception(error_msg)

        self.osslcmdbase = 'openssl x509 -inform %s ' % self.format
                                                  
        r,w,e = popen2.popen3('openssl asn1parse -inform DER ')
        w.write(self.dercert)
        w.close()
        self.asn1parsecert = r.read()
        r.close()
        res = e.read()
        e.close()
        if res != '':
            raise Exception(error_msg)
        
        # Grab _raw_ X509v3 Authority Key Identifier, if any.
        tmp = self.asn1parsecert.split(":X509v3 Authority Key Identifier", 1)
        self.authorityKeyID = None
        if len(tmp) == 2:
            tmp = tmp[1]
            tmp = tmp.split("[HEX DUMP]:", 1)[1]
            self.authorityKeyID=tmp.split('\n',1)[0]

        # Grab _raw_ X509v3 Subject Key Identifier, if any.
        tmp = self.asn1parsecert.split(":X509v3 Subject Key Identifier", 1)
        self.subjectKeyID = None
        if len(tmp) == 2:
            tmp = tmp[1]
            tmp = tmp.split("[HEX DUMP]:", 1)[1]
            self.subjectKeyID=tmp.split('\n',1)[0]            

        # Get tbsCertificate using the worst hack. output of asn1parse
        # looks like that:
        #
        # 0:d=0  hl=4 l=1298 cons: SEQUENCE          
        # 4:d=1  hl=4 l=1018 cons: SEQUENCE          
        # ...
        #
        l1,l2 = self.asn1parsecert.split('\n', 2)[:2]
        hl1 = int(l1.split("hl=",1)[1].split("l=",1)[0])
        rem = l2.split("hl=",1)[1]
        hl2, rem = rem.split("l=",1)
        hl2 = int(hl2)
        l = int(rem.split("cons",1)[0])
        self.tbsCertificate = self.dercert[hl1:hl1+hl2+l]

        # Parse the -text output of openssl to make things available
        tmp = self.textcert.split('\n', 2)[2]
        l = tmp.split('\n', 1)
        if len(l) != 2:
            raise Exception(error_msg)
        cur, tmp = l
        i = 0
        k = self.possible_fields[i] # Version:
        cur = cur[len(k):] + '\n'
        while k:
            l = tmp.split('\n', 1)
            if len(l) != 2: # Over
                fields_dict[k] = cur
                break
            l, tmp = l

            newkey = 0
            # skip fields we have already seen, this is the purpose of 'i'
            for j in range(i, self.possible_fields_count):
                f = self.possible_fields[j]
                if l.startswith(f):
                    fields_dict[k] = cur
                    cur = l[len(f):] + '\n'
                    k = f
                    newkey = 1
                    i = j+1
                    break
            if newkey == 1:
                continue
            cur += l + '\n'

        # version
        v = fields_dict["        Version:"]
        self.version = None
        if v:
            self.version = int(v[1:2])
        if self.version is None:
            raise Exception(error_msg)

        # serial number
        v = fields_dict["        Serial Number:"]
        self.serial = None
        if v:
            v = v.replace('\n', '').strip()
            if "0x" in v:
                v = v.split("0x", 1)[1].split(')', 1)[0]
            v = v.replace(':', '').upper()
            if len(v) % 2:
                v = '0' + v
            self.serial = v
        if self.serial is None:
            raise Exception(error_msg)

        # Signature Algorithm        
        v = fields_dict["        Signature Algorithm:"]
        self.sigAlg = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.sigAlg = v
        if self.sigAlg is None:
            raise Exception(error_msg)
        
        # issuer
        v = fields_dict["        Issuer:"]
        self.issuer = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.issuer = v
        if self.issuer is None:
            raise Exception(error_msg)

        # not before
        v = fields_dict["            Not Before:"]
        self.notBefore_str = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.notBefore_str = v
        if self.notBefore_str is None:
            raise Exception(error_msg)
        try:
            self.notBefore = time.strptime(self.notBefore_str,
                                           "%b %d %H:%M:%S %Y %Z")
        except:
            self.notBefore = time.strptime(self.notBefore_str,
                                           "%b %d %H:%M:%S %Y")
        self.notBefore_str_simple = time.strftime("%x", self.notBefore)
        
        # not after
        v = fields_dict["            Not After :"]
        self.notAfter_str = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.notAfter_str = v
        if self.notAfter_str is None:
            raise Exception(error_msg)
        try:
            self.notAfter = time.strptime(self.notAfter_str,
                                          "%b %d %H:%M:%S %Y %Z")
        except:
            self.notAfter = time.strptime(self.notAfter_str,
                                          "%b %d %H:%M:%S %Y")            
        self.notAfter_str_simple = time.strftime("%x", self.notAfter)
        
        # subject
        v = fields_dict["        Subject:"]
        self.subject = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.subject = v
        if self.subject is None:
            raise Exception(error_msg)
        
        # Public Key Algorithm
        v = fields_dict["            Public Key Algorithm:"]
        self.pubKeyAlg = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.pubKeyAlg = v
        if self.pubKeyAlg is None:
            raise Exception(error_msg)
        
        # Modulus
        v = fields_dict["                Modulus ("]
        self.modulus = None
        if v:
            v,t = v.split(' bit):',1)
            self.modulusLen = int(v)
            t = t.replace(' ', '').replace('\n', ''). replace(':', '')
            self.modulus_hexdump = t
            self.modulus = long(t, 16)
        if self.modulus is None:
            raise Exception(error_msg)

        # Exponent
        v = fields_dict["                Exponent:"]
        self.exponent = None
        if v:
            v = v.split('(',1)[0]
            self.exponent = long(v)
        if self.exponent is None:
            raise Exception(error_msg)

        # Public Key instance
        self.key = RSA.construct((self.modulus, self.exponent, ))
        
        # Subject Key Identifier

        # Authority Key Identifier: keyid, dirname and serial
        self.authorityKeyID_keyid   = None
        self.authorityKeyID_dirname = None
        self.authorityKeyID_serial  = None
        if self.authorityKeyID: # (hex version already done using asn1parse)
            v = fields_dict["                keyid:"]
            if v:
                v = v.split('\n',1)[0]
                v = v.strip().replace(':', '')
                self.authorityKeyID_keyid = v
            v = fields_dict["                DirName:"]
            if v:
                v = v.split('\n',1)[0]
                self.authorityKeyID_dirname = v
            v = fields_dict["                serial:"]
            if v:
                v = v.split('\n',1)[0]
                v = v.strip().replace(':', '')
                self.authorityKeyID_serial = v                

        # Basic constraints
        self.basicConstraintsCritical = False
        self.basicConstraints=None
        v = fields_dict["            X509v3 Basic Constraints:"]
        if v:
            self.basicConstraints = {}
            v,t = v.split('\n',2)[:2]
            if "critical" in v:
                self.basicConstraintsCritical = True
            if "CA:" in t:
                self.basicConstraints["CA"] = t.split('CA:')[1][:4] == "TRUE"
            if "pathlen:" in t:
                self.basicConstraints["pathlen"] = int(t.split('pathlen:')[1])

        # X509v3 Key Usage
        self.keyUsage = []
        v = fields_dict["            X509v3 Key Usage:"]
        if v:   
            # man 5 x509v3_config
            ku_mapping = {"Digital Signature": "digitalSignature",
                          "Non Repudiation": "nonRepudiation",
                          "Key Encipherment": "keyEncipherment",
                          "Data Encipherment": "dataEncipherment",
                          "Key Agreement": "keyAgreement",
                          "Certificate Sign": "keyCertSign",
                          "CRL Sign": "cRLSign",
                          "Encipher Only": "encipherOnly",
                          "Decipher Only": "decipherOnly"}
            v = v.split('\n',2)[1]
            l = map(lambda x: x.strip(), v.split(','))
            while l:
                c = l.pop()
                if ku_mapping.has_key(c):
                    self.keyUsage.append(ku_mapping[c])
                else:
                    self.keyUsage.append(c) # Add it anyway
                    print "Found unknown X509v3 Key Usage: '%s'" % c
                    print "Report it to arno (at) natisbad.org for addition"

        # X509v3 Extended Key Usage
        self.extKeyUsage = []
        v = fields_dict["            X509v3 Extended Key Usage:"]
        if v:   
            # man 5 x509v3_config:
            eku_mapping = {"TLS Web Server Authentication": "serverAuth",
                           "TLS Web Client Authentication": "clientAuth",
                           "Code Signing": "codeSigning",
                           "E-mail Protection": "emailProtection",
                           "Time Stamping": "timeStamping",
                           "Microsoft Individual Code Signing": "msCodeInd",
                           "Microsoft Commercial Code Signing": "msCodeCom",
                           "Microsoft Trust List Signing": "msCTLSign",
                           "Microsoft Encrypted File System": "msEFS",
                           "Microsoft Server Gated Crypto": "msSGC",
                           "Netscape Server Gated Crypto": "nsSGC",
                           "IPSec End System": "iPsecEndSystem",
                           "IPSec Tunnel": "iPsecTunnel",
                           "IPSec User": "iPsecUser"}
            v = v.split('\n',2)[1]
            l = map(lambda x: x.strip(), v.split(','))
            while l:
                c = l.pop()
                if eku_mapping.has_key(c):
                    self.extKeyUsage.append(eku_mapping[c])
                else:
                    self.extKeyUsage.append(c) # Add it anyway
                    print "Found unknown X509v3 Extended Key Usage: '%s'" % c
                    print "Report it to arno (at) natisbad.org for addition"

        # CRL Distribution points
        self.cRLDistributionPoints = []
        v = fields_dict["            X509v3 CRL Distribution Points:"]
        if v:
            v = v.split("\n\n", 1)[0]
            v = v.split("URI:")[1:]
            self.CRLDistributionPoints = map(lambda x: x.strip(), v)
            
        # Authority Information Access: list of tuples ("method", "location")
        self.authorityInfoAccess = []
        v = fields_dict["            Authority Information Access:"]
        if v:
            v = v.split("\n\n", 1)[0]
            v = v.split("\n")[1:]
            for e in v:
                method, location = map(lambda x: x.strip(), e.split(" - ", 1))
                self.authorityInfoAccess.append((method, location))

        # signature field
        v = fields_dict["    Signature Algorithm:" ]
        self.sig = None
        if v:
            v = v.split('\n',1)[1]
            v = v.replace(' ', '').replace('\n', '')
            self.sig = "".join(map(lambda x: chr(int(x, 16)), v.split(':')))
            self.sigLen = len(self.sig)
        if self.sig is None:
            raise Exception(error_msg)

    def isIssuerCert(self, other):
        """
        True if 'other' issued 'self', i.e.:
          - self.issuer == other.subject
          - self is signed by other
        """
        # XXX should be done on raw values, instead of their textual repr
        if self.issuer != other.subject:
            return False

        # Sanity check regarding modulus length and the
        # signature length
        keyLen = (other.modulusLen + 7)/8
        if keyLen != self.sigLen:
            return False

        unenc = other.encrypt(self.sig) # public key encryption, i.e. decrypt

        # XXX Check block type (00 or 01 and type of padding)
        unenc = unenc[1:]
        if not '\x00' in unenc:
            return False
        pos = unenc.index('\x00')
        unenc = unenc[pos+1:]

        found = None
        for k in _hashFuncParams.keys():
            if self.sigAlg.startswith(k):
                found = k
                break
        if not found:
            return False
        hlen, hfunc, digestInfo =  _hashFuncParams[k]
        
        if len(unenc) != (hlen+len(digestInfo)):
            return False

        if not unenc.startswith(digestInfo):
            return False

        h = unenc[-hlen:]
        myh = hfunc(self.tbsCertificate)

        return h == myh

    def chain(self, certlist):
        """
        Construct the chain of certificates leading from 'self' to the
        self signed root using the certificates in 'certlist'. If the
        list does not provide all the required certs to go to the root
        the function returns a incomplete chain starting with the
        certificate. This fact can be tested by tchecking if the last
        certificate of the returned chain is self signed (if c is the
        result, c[-1].isSelfSigned())
        """
        d = {}
        for c in certlist:
            # XXX we should check if we have duplicate
            d[c.subject] = c
        res = [self]
        cur = self
        while not cur.isSelfSigned():
            if d.has_key(cur.issuer):
                possible_issuer = d[cur.issuer]
                if cur.isIssuerCert(possible_issuer):
                    res.append(possible_issuer)
                    cur = possible_issuer
                else:
                    break
        return res

    def remainingDays(self, now=None):
        """
        Based on the value of notBefore field, returns the number of
        days the certificate will still be valid. The date used for the
        comparison is the current and local date, as returned by 
        time.localtime(), except if 'now' argument is provided another
        one. 'now' argument can be given as either a time tuple or a string
        representing the date. Accepted format for the string version
        are:
        
         - '%b %d %H:%M:%S %Y %Z' e.g. 'Jan 30 07:38:59 2008 GMT'
         - '%m/%d/%y' e.g. '01/30/08' (less precise)

        If the certificate is no more valid at the date considered, then,
        a negative value is returned representing the number of days
        since it has expired.
        
        The number of days is returned as a float to deal with the unlikely
        case of certificates that are still just valid.
        """
        if now is None:
            now = time.localtime()
        elif type(now) is str:
            try:
                if '/' in now:
                    now = time.strptime(now, '%m/%d/%y')
                else:
                    now = time.strptime(now, '%b %d %H:%M:%S %Y %Z')
            except:
                warning("Bad time string provided '%s'. Using current time" % now)
                now = time.localtime()

        now = time.mktime(now)
        nft = time.mktime(self.notAfter)
        diff = (nft - now)/(24.*3600)
        return diff


    # return SHA-1 hash of cert embedded public key
    # !! At the moment, the trailing 0 is in the hashed string if any
    def keyHash(self):
        m = self.modulus_hexdump
        res = []
        i = 0
        l = len(m)
        while i<l: # get a string version of modulus
            res.append(struct.pack("B", int(m[i:i+2], 16)))
            i += 2
        return sha.new("".join(res)).digest()    

    def output(self, fmt="DER"):
        if fmt == "DER":
            return self.dercert
        elif fmt == "PEM":
            return self.pemcert
        elif fmt == "TXT":
            return self.textcert

    def export(self, filename, fmt="DER"):
        """
        Export certificate in 'fmt' format (PEM, DER or TXT) to file 'filename'
        """
        f = open(filename, "wb")
        f.write(self.output(fmt))
        f.close()

    def isSelfSigned(self):
        """
        Return True if the certificate is self signed:
          - issuer and subject are the same
          - the signature of the certificate is valid.
        """
        if self.issuer == self.subject:
            return self.isIssuerCert(self)
        return False

    # Print main informations stored in certificate
    def show(self):
        print "Serial: %s" % self.serial
        print "Issuer: " + self.issuer
        print "Subject: " + self.subject
        print "Validity: %s to %s" % (self.notBefore_str_simple,
                                      self.notAfter_str_simple)

    def __repr__(self):
        return "[X.509 Cert. Subject:%s, Issuer:%s]" % (self.subject, self.issuer)

    def __str__(self):
        return self.dercert

    def verifychain(self, anchors, untrusted=None):
        """
        Perform verification of certificate chains for that certificate. The
        behavior of verifychain method is mapped (and also based) on openssl
        verify userland tool (man 1 verify).
        A list of anchors is required. untrusted parameter can be provided 
        a list of untrusted certificates that can be used to reconstruct the
        chain.

        If you have a lot of certificates to verify against the same
        list of anchor, consider constructing this list as a cafile
        and use .verifychain_from_cafile() instead.
        """
        cafile = create_temporary_ca_file(anchors)
        if not cafile:
            return False
        untrusted_file = None
        if untrusted:
            untrusted_file = create_temporary_ca_file(untrusted) # hack
            if not untrusted_file:
                os.unlink(cafile)
                return False
        res = self.verifychain_from_cafile(cafile, 
                                           untrusted_file=untrusted_file)
        os.unlink(cafile)
        if untrusted_file:
            os.unlink(untrusted_file)
        return res

    def verifychain_from_cafile(self, cafile, untrusted_file=None):
        """
        Does the same job as .verifychain() but using the list of anchors
        from the cafile. This is useful (because more efficient) if
        you have a lot of certificates to verify do it that way: it
        avoids the creation of a cafile from anchors at each call.

        As for .verifychain(), a list of untrusted certificates can be
        passed (as a file, this time)
        """
        u = ""
        if untrusted_file:
            u = "-untrusted %s" % untrusted_file
        try:
            cmd = "openssl verify -CAfile %s %s " % (cafile, u)
            pemcert = self.output(fmt="PEM")
            cmdres = self._apply_ossl_cmd(cmd, pemcert)
        except:
            return False
        return cmdres.endswith("\nOK\n") or cmdres.endswith(": OK\n")

    def verifychain_from_capath(self, capath, untrusted_file=None):
        """
        Does the same job as .verifychain_from_cafile() but using the list
        of anchors in capath directory. The directory should contain
        certificates files in PEM format with associated links as
        created using c_rehash utility (man c_rehash).

        As for .verifychain_from_cafile(), a list of untrusted certificates
        can be passed as a file (concatenation of the certificates in
        PEM format)
        """
        u = ""
        if untrusted_file:
            u = "-untrusted %s" % untrusted_file
        try:
            cmd = "openssl verify -CApath %s %s " % (capath, u)
            pemcert = self.output(fmt="PEM")
            cmdres = self._apply_ossl_cmd(cmd, pemcert)
        except:
            return False
        return cmdres.endswith("\nOK\n") or cmdres.endswith(": OK\n")

    def is_revoked(self, crl_list):
        """
        Given a list of trusted CRL (their signature has already been
        verified with trusted anchors), this function returns True if
        the certificate is marked as revoked by one of those CRL.

        Note that if the Certificate was on hold in a previous CRL and
        is now valid again in a new CRL and bot are in the list, it
        will be considered revoked: this is because _all_ CRLs are 
        checked (not only the freshest) and revocation status is not
        handled.

        Also note that the check on the issuer is performed on the
        Authority Key Identifier if available in _both_ the CRL and the
        Cert. Otherwise, the issuers are simply compared.
        """
        for c in crl_list:
            if (self.authorityKeyID is not None and 
                c.authorityKeyID is not None and
                self.authorityKeyID == c.authorityKeyID):
                return self.serial in map(lambda x: x[0], c.revoked_cert_serials)
            elif (self.issuer == c.issuer):
                return self.serial in map(lambda x: x[0], c.revoked_cert_serials)
        return False

def print_chain(l):
    llen = len(l) - 1
    if llen < 0:
        return ""
    c = l[llen]
    llen -= 1
    s = "_ "
    if not c.isSelfSigned():
        s = "_ ... [Missing Root]\n"
    else:
        s += "%s [Self Signed]\n" % c.subject
    i = 1
    while (llen != -1):
        c = l[llen]
        s += "%s\_ %s" % (" "*i, c.subject)
        if llen != 0:
            s += "\n"
        i += 2
        llen -= 1
    print s

# import popen2
# a=popen2.Popen3("openssl crl -text -inform DER -noout ", capturestderr=True)
# a.tochild.write(open("samples/klasa1.crl").read())
# a.tochild.close()
# a.poll()

class CRL(OSSLHelper):
    # Below are the fields we recognize in the -text output of openssl
    # and from which we extract information. We expect them in that
    # order. Number of spaces does matter.
    possible_fields = [ "        Version",
                        "        Signature Algorithm:",
                        "        Issuer:",
                        "        Last Update:",
                        "        Next Update:",
                        "        CRL extensions:",
                        "            X509v3 Issuer Alternative Name:",
                        "            X509v3 Authority Key Identifier:", 
                        "                keyid:",
                        "                DirName:",
                        "                serial:",
                        "            X509v3 CRL Number:", 
                        "Revoked Certificates:",
                        "No Revoked Certificates.",
                        "    Signature Algorithm:" ]
    possible_fields_count = len(possible_fields)

    def __init__(self, crlpath):
        error_msg = "Unable to import CRL."

        fields_dict = {}
        for k in self.possible_fields:
            fields_dict[k] = None

        self.crlpath = None
        rawcrl = None

        if (not '\x00' in crlpath) and os.path.isfile(crlpath):
            self.crlpath = crlpath
            cert_size = os.path.getsize(crlpath)
            if cert_size > MAX_CRL_SIZE:
                raise Exception(error_msg)
            try:
                f = open(crlpath)
                rawcrl = f.read()
                f.close()
            except:
                raise Exception(error_msg)     
        else:
            rawcrl = crlpath

        if rawcrl is None:
            raise Exception(error_msg)

        self.rawcrl = rawcrl

        # Let's try to get file format : PEM or DER.
        fmtstr = 'openssl crl -text -inform %s -noout '
        convertstr = 'openssl crl -inform %s -outform %s '
        crl_header = "-----BEGIN X509 CRL-----"
        crl_footer = "-----END X509 CRL-----"
        l = rawcrl.split(crl_header, 1)
        if len(l) == 2: # looks like PEM
            tmp = l[1]
            l = tmp.split(crl_footer, 1)
            if len(l) == 2:
                tmp = l[0]
                rawcrl = "%s%s%s\n" % (crl_header, tmp, crl_footer)
            else:
                raise Exception(error_msg)
            r,w,e = popen2.popen3(fmtstr % "PEM")
            w.write(rawcrl)
            w.close()
            textcrl = r.read()
            r.close()
            res = e.read()
            e.close()
            if res == '':
                self.format = "PEM"
                self.pemcrl = rawcrl
                self.textcrl = textcrl
                cmd = convertstr % ("PEM", "DER")
                self.dercrl = self._apply_ossl_cmd(cmd, rawcrl)
            else:
                raise Exception(error_msg)
        else: # not PEM, try DER
            r,w,e = popen2.popen3(fmtstr % "DER")            
            w.write(rawcrl)
            w.close()
            textcrl = r.read()
            r.close()
            res = e.read()
            if res == '':
                self.format = "DER"
                self.dercrl = rawcrl
                self.textcrl = textcrl
                cmd = convertstr % ("DER", "PEM")
                self.pemcrl = self._apply_ossl_cmd(cmd, rawcrl)
                cmd = convertstr % ("DER", "DER")
                self.dercrl = self._apply_ossl_cmd(cmd, rawcrl)
            else:
                raise Exception(error_msg)

        self.osslcmdbase = 'openssl crl -inform %s ' % self.format

        r,w,e = popen2.popen3('openssl asn1parse -inform DER ')
        w.write(self.dercrl)
        w.close()
        self.asn1parsecrl = r.read()
        r.close()
        res = e.read()
        e.close()
        if res != '':
            raise Exception(error_msg)

        # Grab _raw_ X509v3 Authority Key Identifier, if any.
        tmp = self.asn1parsecrl.split(":X509v3 Authority Key Identifier", 1)
        self.authorityKeyID = None
        if len(tmp) == 2:
            tmp = tmp[1]
            tmp = tmp.split("[HEX DUMP]:", 1)[1]
            self.authorityKeyID=tmp.split('\n',1)[0]

        # Parse the -text output of openssl to make things available
        tmp = self.textcrl.split('\n', 1)[1]
        l = tmp.split('\n', 1)
        if len(l) != 2:
            raise Exception(error_msg)
        cur, tmp = l
        i = 0
        k = self.possible_fields[i] # Version
        cur = cur[len(k):] + '\n'
        while k:
            l = tmp.split('\n', 1)
            if len(l) != 2: # Over
                fields_dict[k] = cur
                break
            l, tmp = l

            newkey = 0
            # skip fields we have already seen, this is the purpose of 'i'
            for j in range(i, self.possible_fields_count):
                f = self.possible_fields[j]
                if l.startswith(f):
                    fields_dict[k] = cur
                    cur = l[len(f):] + '\n'
                    k = f
                    newkey = 1
                    i = j+1
                    break
            if newkey == 1:
                continue
            cur += l + '\n'

        # version
        v = fields_dict["        Version"]
        self.version = None
        if v:
            self.version = int(v[1:2])
        if self.version is None:
            raise Exception(error_msg)

        # signature algorithm
        v = fields_dict["        Signature Algorithm:"]
        self.sigAlg = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.sigAlg = v
        if self.sigAlg is None:
            raise Exception(error_msg)

        # issuer
        v = fields_dict["        Issuer:"]
        self.issuer = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.issuer = v
        if self.issuer is None:
            raise Exception(error_msg)

        # last update
        v = fields_dict["        Last Update:"]
        self.lastUpdate_str = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.lastUpdate_str = v
        if self.lastUpdate_str is None:
            raise Exception(error_msg)
        self.lastUpdate = time.strptime(self.lastUpdate_str,
                                       "%b %d %H:%M:%S %Y %Z")
        self.lastUpdate_str_simple = time.strftime("%x", self.lastUpdate)

        # next update
        v = fields_dict["        Next Update:"]
        self.nextUpdate_str = None
        if v:
            v = v.split('\n',1)[0]
            v = v.strip()
            self.nextUpdate_str = v
        if self.nextUpdate_str is None:
            raise Exception(error_msg)
        self.nextUpdate = time.strptime(self.nextUpdate_str,
                                       "%b %d %H:%M:%S %Y %Z")
        self.nextUpdate_str_simple = time.strftime("%x", self.nextUpdate)
        
        # XXX Do something for Issuer Alternative Name

        # Authority Key Identifier: keyid, dirname and serial
        self.authorityKeyID_keyid   = None
        self.authorityKeyID_dirname = None
        self.authorityKeyID_serial  = None
        if self.authorityKeyID: # (hex version already done using asn1parse)
            v = fields_dict["                keyid:"]
            if v:
                v = v.split('\n',1)[0]
                v = v.strip().replace(':', '')
                self.authorityKeyID_keyid = v
            v = fields_dict["                DirName:"]
            if v:
                v = v.split('\n',1)[0]
                self.authorityKeyID_dirname = v
            v = fields_dict["                serial:"]
            if v:
                v = v.split('\n',1)[0]
                v = v.strip().replace(':', '')
                self.authorityKeyID_serial = v

        # number
        v = fields_dict["            X509v3 CRL Number:"]
        self.number = None
        if v:
            v = v.split('\n',2)[1]
            v = v.strip()
            self.number = int(v)

        # Get the list of serial numbers of revoked certificates
        self.revoked_cert_serials = []
        v = fields_dict["Revoked Certificates:"]
        t = fields_dict["No Revoked Certificates."]
        if (t is None and v is not None):
            v = v.split("Serial Number: ")[1:]
            for r in v:
                s,d = r.split('\n', 1)
                s = s.split('\n', 1)[0]
                d = d.split("Revocation Date:", 1)[1]
                d = time.strptime(d.strip(), "%b %d %H:%M:%S %Y %Z")
                self.revoked_cert_serials.append((s,d))

        # signature field
        v = fields_dict["    Signature Algorithm:" ]
        self.sig = None
        if v:
            v = v.split('\n',1)[1]
            v = v.replace(' ', '').replace('\n', '')
            self.sig = "".join(map(lambda x: chr(int(x, 16)), v.split(':')))
            self.sigLen = len(self.sig)
        if self.sig is None:
            raise Exception(error_msg)

    def __str__(self):
        return self.dercrl
        
    # Print main informations stored in CRL
    def show(self):
        print "Version: %d" % self.version
        print "sigAlg: " + self.sigAlg
        print "Issuer: " + self.issuer
        print "lastUpdate: %s" % self.lastUpdate_str_simple
        print "nextUpdate: %s" % self.nextUpdate_str_simple

    def verify(self, anchors):
        """
        Return True if the CRL is signed by one of the provided
        anchors. False on error (invalid signature, missing anchorand, ...)
        """
        cafile = create_temporary_ca_file(anchors)
        if cafile is None:
            return False
        try:
            cmd = self.osslcmdbase + '-noout -CAfile %s 2>&1' % cafile
            cmdres = self._apply_ossl_cmd(cmd, self.rawcrl)
        except:
            os.unlink(cafile)
            return False
        os.unlink(cafile)
        return "verify OK" in cmdres


    

########NEW FILE########
__FILENAME__ = dadict
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Direct Access dictionary.
"""

from error import Scapy_Exception

###############################
## Direct Access dictionnary ##
###############################

def fixname(x):
    if x and x[0] in "0123456789":
        x = "n_"+x
    return x.translate("________________________________________________0123456789_______ABCDEFGHIJKLMNOPQRSTUVWXYZ______abcdefghijklmnopqrstuvwxyz_____________________________________________________________________________________________________________________________________")


class DADict_Exception(Scapy_Exception):
    pass

class DADict:
    def __init__(self, _name="DADict", **kargs):
        self._name=_name
        self.__dict__.update(kargs)
    def fixname(self,val):
        return fixname(val)
    def __contains__(self, val):
        return val in self.__dict__
    def __getitem__(self, attr):
        return getattr(self, attr)
    def __setitem__(self, attr, val):        
        return setattr(self, self.fixname(attr), val)
    def __iter__(self):
        return iter(map(lambda (x,y):y,filter(lambda (x,y):x and x[0]!="_", self.__dict__.items())))
    def _show(self):
        for k in self.__dict__.keys():
            if k and k[0] != "_":
                print "%10s = %r" % (k,getattr(self,k))
    def __repr__(self):
        return "<%s/ %s>" % (self._name," ".join(filter(lambda x:x and x[0]!="_",self.__dict__.keys())))

    def _branch(self, br, uniq=0):
        if uniq and br._name in self:
            raise DADict_Exception("DADict: [%s] already branched in [%s]" % (br._name, self._name))
        self[br._name] = br

    def _my_find(self, *args, **kargs):
        if args and self._name not in args:
            return False
        for k in kargs:
            if k not in self or self[k] != kargs[k]:
                return False
        return True
    
    def _find(self, *args, **kargs):
         return self._recurs_find((), *args, **kargs)
    def _recurs_find(self, path, *args, **kargs):
        if self in path:
            return None
        if self._my_find(*args, **kargs):
            return self
        for o in self:
            if isinstance(o, DADict):
                p = o._recurs_find(path+(self,), *args, **kargs)
                if p is not None:
                    return p
        return None
    def _find_all(self, *args, **kargs):
        return self._recurs_find_all((), *args, **kargs)
    def _recurs_find_all(self, path, *args, **kargs):
        r = []
        if self in path:
            return r
        if self._my_find(*args, **kargs):
            r.append(self)
        for o in self:
            if isinstance(o, DADict):
                p = o._recurs_find_all(path+(self,), *args, **kargs)
                r += p
        return r
    def keys(self):
        return filter(lambda x:x and x[0]!="_", self.__dict__.keys())
        

########NEW FILE########
__FILENAME__ = data
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Global variables and functions for handling external data sets.
"""

import os,sys,re
from dadict import DADict
from error import log_loading

############
## Consts ##
############

ETHER_ANY = "\x00"*6
ETHER_BROADCAST = "\xff"*6

ETH_P_ALL = 3
ETH_P_IP = 0x800
ETH_P_ARP = 0x806
ETH_P_IPV6 = 0x86dd

# From net/if_arp.h
ARPHDR_ETHER = 1
ARPHDR_METRICOM = 23
ARPHDR_PPP = 512
ARPHDR_LOOPBACK = 772
ARPHDR_TUN = 65534


# From net/ipv6.h on Linux (+ Additions)
IPV6_ADDR_UNICAST     = 0x01
IPV6_ADDR_MULTICAST   = 0x02
IPV6_ADDR_CAST_MASK   = 0x0F
IPV6_ADDR_LOOPBACK    = 0x10
IPV6_ADDR_GLOBAL      = 0x00
IPV6_ADDR_LINKLOCAL   = 0x20
IPV6_ADDR_SITELOCAL   = 0x40     # deprecated since Sept. 2004 by RFC 3879
IPV6_ADDR_SCOPE_MASK  = 0xF0
#IPV6_ADDR_COMPATv4   = 0x80     # deprecated; i.e. ::/96
#IPV6_ADDR_MAPPED     = 0x1000   # i.e.; ::ffff:0.0.0.0/96
IPV6_ADDR_6TO4        = 0x0100   # Added to have more specific info (should be 0x0101 ?)
IPV6_ADDR_UNSPECIFIED = 0x10000




MTU = 0x7fff # a.k.a give me all you have

WINDOWS=sys.platform.startswith("win")

 
# file parsing to get some values :

def load_protocols(filename):
    spaces = re.compile("[ \t]+|\n")
    dct = DADict(_name=filename)
    try:
        for l in open(filename):
            try:
                shrp = l.find("#")
                if  shrp >= 0:
                    l = l[:shrp]
                l = l.strip()
                if not l:
                    continue
                lt = tuple(re.split(spaces, l))
                if len(lt) < 2 or not lt[0]:
                    continue
                dct[lt[0]] = int(lt[1])
            except Exception,e:
                log_loading.info("Couldn't parse file [%s]: line [%r] (%s)" % (filename,l,e))
    except IOError:
        log_loading.info("Can't open %s file" % filename)
    return dct

def load_ethertypes(filename):
    spaces = re.compile("[ \t]+|\n")
    dct = DADict(_name=filename)
    try:
        f=open(filename)
        for l in f:
            try:
                shrp = l.find("#")
                if  shrp >= 0:
                    l = l[:shrp]
                l = l.strip()
                if not l:
                    continue
                lt = tuple(re.split(spaces, l))
                if len(lt) < 2 or not lt[0]:
                    continue
                dct[lt[0]] = int(lt[1], 16)
            except Exception,e:
                log_loading.info("Couldn't parse file [%s]: line [%r] (%s)" % (filename,l,e))
        f.close()
    except IOError,msg:
        pass
    return dct

def load_services(filename):
    spaces = re.compile("[ \t]+|\n")
    tdct=DADict(_name="%s-tcp"%filename)
    udct=DADict(_name="%s-udp"%filename)
    try:
        f=open(filename)
        for l in f:
            try:
                shrp = l.find("#")
                if  shrp >= 0:
                    l = l[:shrp]
                l = l.strip()
                if not l:
                    continue
                lt = tuple(re.split(spaces, l))
                if len(lt) < 2 or not lt[0]:
                    continue
                if lt[1].endswith("/tcp"):
                    tdct[lt[0]] = int(lt[1].split('/')[0])
                elif lt[1].endswith("/udp"):
                    udct[lt[0]] = int(lt[1].split('/')[0])
            except Exception,e:
                log_loading.warning("Couldn't file [%s]: line [%r] (%s)" % (filename,l,e))
        f.close()
    except IOError:
        log_loading.info("Can't open /etc/services file")
    return tdct,udct


class ManufDA(DADict):
    def fixname(self, val):
        return val
    def _get_manuf_couple(self, mac):
        oui = ":".join(mac.split(":")[:3]).upper()
        return self.__dict__.get(oui,(mac,mac))
    def _get_manuf(self, mac):
        return self._get_manuf_couple(mac)[1]
    def _get_short_manuf(self, mac):
        return self._get_manuf_couple(mac)[0]
    def _resolve_MAC(self, mac):
        oui = ":".join(mac.split(":")[:3]).upper()
        if oui in self:
            return ":".join([self[oui][0]]+ mac.split(":")[3:])
        return mac
        
        
        

def load_manuf(filename):
    try:
        manufdb=ManufDA(_name=filename)
        for l in open(filename):
            try:
                l = l.strip()
                if not l or l.startswith("#"):
                    continue
                oui,shrt=l.split()[:2]
                i = l.find("#")
                if i < 0:
                    lng=shrt
                else:
                    lng = l[i+2:]
                manufdb[oui] = shrt,lng
            except Exception,e:
                log_loading.warning("Couldn't parse one line from [%s] [%r] (%s)" % (filename, l, e))
    except IOError:
        #log_loading.warning("Couldn't open [%s] file" % filename)
        pass
    return manufdb
    


if WINDOWS:
    ETHER_TYPES=load_ethertypes("ethertypes")
    IP_PROTOS=load_protocols(os.environ["SystemRoot"]+"\system32\drivers\etc\protocol")
    TCP_SERVICES,UDP_SERVICES=load_services(os.environ["SystemRoot"] + "\system32\drivers\etc\services")
    MANUFDB = load_manuf(os.environ["ProgramFiles"] + "\\wireshark\\manuf")
else:
    IP_PROTOS=load_protocols("/etc/protocols")
    ETHER_TYPES=load_ethertypes("/etc/ethertypes")
    TCP_SERVICES,UDP_SERVICES=load_services("/etc/services")
    MANUFDB = load_manuf("/usr/share/wireshark/wireshark/manuf")



#####################
## knowledge bases ##
#####################

class KnowledgeBase:
    def __init__(self, filename):
        self.filename = filename
        self.base = None

    def lazy_init(self):
        self.base = ""

    def reload(self, filename = None):
        if filename is not None:
            self.filename = filename
        oldbase = self.base
        self.base = None
        self.lazy_init()
        if self.base is None:
            self.base = oldbase

    def get_base(self):
        if self.base is None:
            self.lazy_init()
        return self.base
    


########NEW FILE########
__FILENAME__ = error
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Logging subsystem and basic exception class.
"""

#############################
##### Logging subsystem #####
#############################

class Scapy_Exception(Exception):
    pass

import logging,traceback,time

class ScapyFreqFilter(logging.Filter):
    def __init__(self):
        logging.Filter.__init__(self)
        self.warning_table = {}
    def filter(self, record):        
        from config import conf
        wt = conf.warning_threshold
        if wt > 0:
            stk = traceback.extract_stack()
            caller=None
            for f,l,n,c in stk:
                if n == 'warning':
                    break
                caller = l
            tm,nb = self.warning_table.get(caller, (0,0))
            ltm = time.time()
            if ltm-tm > wt:
                tm = ltm
                nb = 0
            else:
                if nb < 2:
                    nb += 1
                    if nb == 2:
                        record.msg = "more "+record.msg
                else:
                    return 0
            self.warning_table[caller] = (tm,nb)
        return 1    

log_scapy = logging.getLogger("scapy")
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
log_scapy.addHandler(console_handler)
log_runtime = logging.getLogger("scapy.runtime")          # logs at runtime
log_runtime.addFilter(ScapyFreqFilter())
log_interactive = logging.getLogger("scapy.interactive")  # logs in interactive functions
log_loading = logging.getLogger("scapy.loading")          # logs when loading scapy


def warning(x):
    log_runtime.warning(x)


########NEW FILE########
__FILENAME__ = fields
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Fields: basic data structures that make up parts of packets.
"""

import struct,copy,socket
from config import conf
from volatile import *
from data import *
from utils import *
from base_classes import BasePacket,Gen,Net


############
## Fields ##
############

class Field:
    """For more informations on how this work, please refer to
       http://www.secdev.org/projects/scapy/files/scapydoc.pdf
       chapter ``Adding a New Field''"""
    islist=0
    holds_packets=0
    def __init__(self, name, default, fmt="H"):
        self.name = name
        if fmt[0] in "@=<>!":
            self.fmt = fmt
        else:
            self.fmt = "!"+fmt
        self.default = self.any2i(None,default)
        self.sz = struct.calcsize(self.fmt)
        self.owners = []

    def register_owner(self, cls):
        self.owners.append(cls)

    def i2len(self, pkt, x):
        """Convert internal value to a length usable by a FieldLenField"""
        return self.sz
    def i2count(self, pkt, x):
        """Convert internal value to a number of elements usable by a FieldLenField.
        Always 1 except for list fields"""
        return 1
    def h2i(self, pkt, x):
        """Convert human value to internal value"""
        return x
    def i2h(self, pkt, x):
        """Convert internal value to human value"""
        return x
    def m2i(self, pkt, x):
        """Convert machine value to internal value"""
        return x
    def i2m(self, pkt, x):
        """Convert internal value to machine value"""
        if x is None:
            x = 0
        return x
    def any2i(self, pkt, x):
        """Try to understand the most input values possible and make an internal value from them"""
        return self.h2i(pkt, x)
    def i2repr(self, pkt, x):
        """Convert internal value to a nice representation"""
        return repr(self.i2h(pkt,x))
    def addfield(self, pkt, s, val):
        """Add an internal value  to a string"""
        return s+struct.pack(self.fmt, self.i2m(pkt,val))
    def getfield(self, pkt, s):
        """Extract an internal value from a string"""
        return  s[self.sz:], self.m2i(pkt, struct.unpack(self.fmt, s[:self.sz])[0])
    def do_copy(self, x):
        if hasattr(x, "copy"):
            return x.copy()
        if type(x) is list:
            x = x[:]
            for i in xrange(len(x)):
                if isinstance(x[i], BasePacket):
                    x[i] = x[i].copy()
        return x
    def __repr__(self):
        return "<Field (%s).%s>" % (",".join(x.__name__ for x in self.owners),self.name)
    def copy(self):
        return copy.deepcopy(self)
    def randval(self):
        """Return a volatile object whose value is both random and suitable for this field"""
        fmtt = self.fmt[-1]
        if fmtt in "BHIQ":
            return {"B":RandByte,"H":RandShort,"I":RandInt, "Q":RandLong}[fmtt]()
        elif fmtt == "s":
            if self.fmt[0] in "0123456789":
                l = int(self.fmt[:-1])
            else:
                l = int(self.fmt[1:-1])
            return RandBin(l)
        else:
            warning("no random class for [%s] (fmt=%s)." % (self.name, self.fmt))
            



class Emph:
    fld = ""
    def __init__(self, fld):
        self.fld = fld
    def __getattr__(self, attr):
        return getattr(self.fld,attr)
    def __hash__(self):
        return hash(self.fld)
    def __eq__(self, other):
        return self.fld == other
    

class ActionField:
    _fld = None
    def __init__(self, fld, action_method, **kargs):
        self._fld = fld
        self._action_method = action_method
        self._privdata = kargs
    def any2i(self, pkt, val):
        getattr(pkt, self._action_method)(val, self._fld, **self._privdata)
        return getattr(self._fld, "any2i")(pkt, val)
    def __getattr__(self, attr):
        return getattr(self._fld,attr)


class ConditionalField:
    fld = None
    def __init__(self, fld, cond):
        self.fld = fld
        self.cond = cond
    def _evalcond(self,pkt):
        return self.cond(pkt)
        
    def getfield(self, pkt, s):
        if self._evalcond(pkt):
            return self.fld.getfield(pkt,s)
        else:
            return s,None
        
    def addfield(self, pkt, s, val):
        if self._evalcond(pkt):
            return self.fld.addfield(pkt,s,val)
        else:
            return s
    def __getattr__(self, attr):
        return getattr(self.fld,attr)
        

class PadField:
    """Add bytes after the proxified field so that it ends at the specified
       alignment from its begining"""
    _fld = None
    def __init__(self, fld, align, padwith=None):
        self._fld = fld
        self._align = align
        self._padwith = padwith or ""

    def getfield(self, pkt, s):
        x = self._fld.getfield(pkt,s)
        padlen = ((self._align - (len(x[1]) % self._align)) % self._align)
        return x[0][padlen:], x[1]

    def addfield(self, pkt, s, val):
        sval = self._fld.addfield(pkt, "", val)
        return s+sval+struct.pack("%is" % (-len(sval)%self._align), self._padwith)
    
    def __getattr__(self, attr):
        return getattr(self._fld,attr)
        

class MACField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "6s")
    def i2m(self, pkt, x):
        if x is None:
            return "\0\0\0\0\0\0"
        return mac2str(x)
    def m2i(self, pkt, x):
        return str2mac(x)
    def any2i(self, pkt, x):
        if type(x) is str and len(x) is 6:
            x = self.m2i(pkt, x)
        return x
    def i2repr(self, pkt, x):
        x = self.i2h(pkt, x)
        if self in conf.resolve:
            x = conf.manufdb._resolve_MAC(x)
        return x
    def randval(self):
        return RandMAC()


class IPField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "4s")
    def h2i(self, pkt, x):
        if type(x) is str:
            try:
                inet_aton(x)
            except socket.error:
                x = Net(x)
        elif type(x) is list:
            x = [self.h2i(pkt, n) for n in x] 
        return x
    def resolve(self, x):
        if self in conf.resolve:
            try:
                ret = socket.gethostbyaddr(x)[0]
            except:
                pass
            else:
                if ret:
                    return ret
        return x
    def i2m(self, pkt, x):
        return inet_aton(x)
    def m2i(self, pkt, x):
        return inet_ntoa(x)
    def any2i(self, pkt, x):
        return self.h2i(pkt,x)
    def i2repr(self, pkt, x):
        return self.resolve(self.i2h(pkt, x))
    def randval(self):
        return RandIP()

class SourceIPField(IPField):
    def __init__(self, name, dstname):
        IPField.__init__(self, name, None)
        self.dstname = dstname
    def i2m(self, pkt, x):
        if x is None:
            iff,x,gw = pkt.route()
            if x is None:
                x = "0.0.0.0"
        return IPField.i2m(self, pkt, x)
    def i2h(self, pkt, x):
        if x is None:
            dst=getattr(pkt,self.dstname)
            if isinstance(dst,Gen):
                r = map(conf.route.route, dst)
                r.sort()
                if r[0] != r[-1]:
                    warning("More than one possible route for %s"%repr(dst))
                iff,x,gw = r[0]
            else:
                iff,x,gw = conf.route.route(dst)
        return IPField.i2h(self, pkt, x)

    


class ByteField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "B")
        
class XByteField(ByteField):
    def i2repr(self, pkt, x):
        return lhex(self.i2h(pkt, x))

class OByteField(ByteField):
    def i2repr(self, pkt, x):
        return "%03o"%self.i2h(pkt, x)

class X3BytesField(XByteField):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "!I")
    def addfield(self, pkt, s, val):
        return s+struct.pack(self.fmt, self.i2m(pkt,val))[1:4]
    def getfield(self, pkt, s):
        return  s[3:], self.m2i(pkt, struct.unpack(self.fmt, "\x00"+s[:3])[0])


class ShortField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "H")

class LEShortField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "<H")

class XShortField(ShortField):
    def i2repr(self, pkt, x):
        return lhex(self.i2h(pkt, x))


class IntField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "I")

class SignedIntField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "i")
    def randval(self):
        return RandSInt()

class LEIntField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "<I")

class LESignedIntField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "<i")
    def randval(self):
        return RandSInt()

class XIntField(IntField):
    def i2repr(self, pkt, x):
        return lhex(self.i2h(pkt, x))


class LongField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "Q")

class XLongField(LongField):
    def i2repr(self, pkt, x):
        return lhex(self.i2h(pkt, x))

class IEEEFloatField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "f")

class IEEEDoubleField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "d")


class StrField(Field):
    def __init__(self, name, default, fmt="H", remain=0):
        Field.__init__(self,name,default,fmt)
        self.remain = remain        
    def i2len(self, pkt, i):
        return len(i)
    def i2m(self, pkt, x):
        if x is None:
            x = ""
        elif type(x) is not str:
            x=str(x)
        return x
    def addfield(self, pkt, s, val):
        return s+self.i2m(pkt, val)
    def getfield(self, pkt, s):
        if self.remain == 0:
            return "",self.m2i(pkt, s)
        else:
            return s[-self.remain:],self.m2i(pkt, s[:-self.remain])
    def randval(self):
        return RandBin(RandNum(0,1200))

class PacketField(StrField):
    holds_packets=1
    def __init__(self, name, default, cls, remain=0):
        StrField.__init__(self, name, default, remain=remain)
        self.cls = cls
    def i2m(self, pkt, i):
        return str(i)
    def m2i(self, pkt, m):
        return self.cls(m)
    def getfield(self, pkt, s):
        i = self.m2i(pkt, s)
        remain = ""
        if 'Padding' in i:
            r = i['Padding']
            del(r.underlayer.payload)
            remain = r.load
        return remain,i
    
class PacketLenField(PacketField):
    holds_packets=1
    def __init__(self, name, default, cls, length_from=None):
        PacketField.__init__(self, name, default, cls)
        self.length_from = length_from
    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        try:
            i = self.m2i(pkt, s[:l])
        except Exception:
            if conf.debug_dissector:
                raise
            i = conf.raw_layer(load=s[:l])
        return s[l:],i


class PacketListField(PacketField):
    islist = 1
    holds_packets=1
    def __init__(self, name, default, cls, count_from=None, length_from=None):
        if default is None:
            default = []  # Create a new list for each instance
        PacketField.__init__(self, name, default, cls)
        self.count_from = count_from
        self.length_from = length_from


    def any2i(self, pkt, x):
        if type(x) is not list:
            return [x]
        else:
            return x
    def i2count(self, pkt, val):
        if type(val) is list:
            return len(val)
        return 1
    def i2len(self, pkt, val):
        return sum( len(p) for p in val )
    def do_copy(self, x):
        return map(lambda p:p.copy(), x)
    def getfield(self, pkt, s):
        c = l = None
        if self.length_from is not None:
            l = self.length_from(pkt)
        elif self.count_from is not None:
            c = self.count_from(pkt)
            
        lst = []
        ret = ""
        remain = s
        if l is not None:
            remain,ret = s[:l],s[l:]
        while remain:
            if c is not None:
                if c <= 0:
                    break
                c -= 1
            try:
                p = self.m2i(pkt,remain)
            except Exception:
                if conf.debug_dissector:
                    raise
                p = conf.raw_layer(load=remain)
                remain = ""
            else:
                if 'Padding' in p:
                    pad = p['Padding']
                    remain = pad.load
                    del(pad.underlayer.payload)
                else:
                    remain = ""
            lst.append(p)
        return remain+ret,lst
    def addfield(self, pkt, s, val):
        return s+"".join(map(str, val))


class StrFixedLenField(StrField):
    def __init__(self, name, default, length=None, length_from=None):
        StrField.__init__(self, name, default)
        self.length_from  = length_from
        if length is not None:
            self.length_from = lambda pkt,length=length: length
    def i2repr(self, pkt, v):
        if type(v) is str:
            v = v.rstrip("\0")
        return repr(v)
    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        return s[l:], self.m2i(pkt,s[:l])
    def addfield(self, pkt, s, val):
        l = self.length_from(pkt)
        return s+struct.pack("%is"%l,self.i2m(pkt, val))
    def randval(self):
        try:
            l = self.length_from(None)
        except:
            l = RandNum(0,200)
        return RandBin(l)

class StrFixedLenEnumField(StrFixedLenField):
    def __init__(self, name, default, length=None, enum=None, length_from=None):
        StrFixedLenField.__init__(self, name, default, length=length, length_from=length_from)
        self.enum = enum
    def i2repr(self, pkt, v):
        r = v.rstrip("\0")
        rr = repr(r)
        if v in self.enum:
            rr = "%s (%s)" % (rr, self.enum[v])
        elif r in self.enum:
            rr = "%s (%s)" % (rr, self.enum[r])
        return rr

class NetBIOSNameField(StrFixedLenField):
    def __init__(self, name, default, length=31):
        StrFixedLenField.__init__(self, name, default, length)
    def i2m(self, pkt, x):
        l = self.length_from(pkt)/2
        if x is None:
            x = ""
        x += " "*(l)
        x = x[:l]
        x = "".join(map(lambda x: chr(0x41+(ord(x)>>4))+chr(0x41+(ord(x)&0xf)), x))
        x = " "+x
        return x
    def m2i(self, pkt, x):
        x = x.strip("\x00").strip(" ")
        return "".join(map(lambda x,y: chr((((ord(x)-1)&0xf)<<4)+((ord(y)-1)&0xf)), x[::2],x[1::2]))

class StrLenField(StrField):
    def __init__(self, name, default, fld=None, length_from=None):
        StrField.__init__(self, name, default)
        self.length_from = length_from
    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        return s[l:], self.m2i(pkt,s[:l])

class FieldListField(Field):
    islist=1
    def __init__(self, name, default, field, length_from=None, count_from=None):
        if default is None:
            default = []  # Create a new list for each instance
        Field.__init__(self, name, default)
        self.count_from = count_from
        self.length_from = length_from
        self.field = field            
            
    def i2count(self, pkt, val):
        if type(val) is list:
            return len(val)
        return 1
    def i2len(self, pkt, val):
        return sum( self.field.i2len(pkt,v) for v in val )
    
    def i2m(self, pkt, val):
        if val is None:
            val = []
        return val
    def any2i(self, pkt, x):
        if type(x) is not list:
            return [x]
        else:
            return x
    def addfield(self, pkt, s, val):
        val = self.i2m(pkt, val)
        for v in val:
            s = self.field.addfield(pkt, s, v)
        return s
    def getfield(self, pkt, s):
        c = l = None
        if self.length_from is not None:
            l = self.length_from(pkt)
        elif self.count_from is not None:
            c = self.count_from(pkt)

        val = []
        ret=""
        if l is not None:
            s,ret = s[:l],s[l:]
            
        while s:
            if c is not None:
                if c <= 0:
                    break
                c -= 1
            s,v = self.field.getfield(pkt, s)
            val.append(v)
        return s+ret, val

class FieldLenField(Field):
    def __init__(self, name, default,  length_of=None, fmt = "H", count_of=None, adjust=lambda pkt,x:x, fld=None):
        Field.__init__(self, name, default, fmt)
        self.length_of=length_of
        self.count_of=count_of
        self.adjust=adjust
        if fld is not None:
            FIELD_LENGTH_MANAGEMENT_DEPRECATION(self.__class__.__name__)
            self.length_of = fld
    def i2m(self, pkt, x):
        if x is None:
            if self.length_of is not None:
                fld,fval = pkt.getfield_and_val(self.length_of)
                f = fld.i2len(pkt, fval)
            else:
                fld,fval = pkt.getfield_and_val(self.count_of)
                f = fld.i2count(pkt, fval)
            x = self.adjust(pkt,f)
        return x

class StrNullField(StrField):
    def addfield(self, pkt, s, val):
        return s+self.i2m(pkt, val)+"\x00"
    def getfield(self, pkt, s):
        l = s.find("\x00")
        if l < 0:
            #XXX \x00 not found
            return "",s
        return s[l+1:],self.m2i(pkt, s[:l])
    def randval(self):
        return RandTermString(RandNum(0,1200),"\x00")

class StrStopField(StrField):
    def __init__(self, name, default, stop, additionnal=0):
        Field.__init__(self, name, default)
        self.stop=stop
        self.additionnal=additionnal
    def getfield(self, pkt, s):
        l = s.find(self.stop)
        if l < 0:
            return "",s
#            raise Scapy_Exception,"StrStopField: stop value [%s] not found" %stop
        l += len(self.stop)+self.additionnal
        return s[l:],s[:l]
    def randval(self):
        return RandTermString(RandNum(0,1200),self.stop)

class LenField(Field):
    def i2m(self, pkt, x):
        if x is None:
            x = len(pkt.payload)
        return x

class BCDFloatField(Field):
    def i2m(self, pkt, x):
        return int(256*x)
    def m2i(self, pkt, x):
        return x/256.0

class BitField(Field):
    def __init__(self, name, default, size):
        Field.__init__(self, name, default)
        self.rev = size < 0 
        self.size = abs(size)
    def reverse(self, val):
        if self.size == 16:
            val = socket.ntohs(val)
        elif self.size == 32:
            val = socket.ntohl(val)
        return val
        
    def addfield(self, pkt, s, val):
        val = self.i2m(pkt, val)
        if type(s) is tuple:
            s,bitsdone,v = s
        else:
            bitsdone = 0
            v = 0
        if self.rev:
            val = self.reverse(val)
        v <<= self.size
        v |= val & ((1L<<self.size) - 1)
        bitsdone += self.size
        while bitsdone >= 8:
            bitsdone -= 8
            s = s+struct.pack("!B", v >> bitsdone)
            v &= (1L<<bitsdone)-1
        if bitsdone:
            return s,bitsdone,v
        else:
            return s
    def getfield(self, pkt, s):
        if type(s) is tuple:
            s,bn = s
        else:
            bn = 0
        # we don't want to process all the string
        nb_bytes = (self.size+bn-1)/8 + 1
        w = s[:nb_bytes]

        # split the substring byte by byte
        bytes = struct.unpack('!%dB' % nb_bytes , w)

        b = 0L
        for c in range(nb_bytes):
            b |= long(bytes[c]) << (nb_bytes-c-1)*8

        # get rid of high order bits
        b &= (1L << (nb_bytes*8-bn)) - 1

        # remove low order bits
        b = b >> (nb_bytes*8 - self.size - bn)

        if self.rev:
            b = self.reverse(b)

        bn += self.size
        s = s[bn/8:]
        bn = bn%8
        b = self.m2i(pkt, b)
        if bn:
            return (s,bn),b
        else:
            return s,b
    def randval(self):
        return RandNum(0,2**self.size-1)


class BitFieldLenField(BitField):
    def __init__(self, name, default, size, length_of=None, count_of=None, adjust=lambda pkt,x:x):
        BitField.__init__(self, name, default, size)
        self.length_of=length_of
        self.count_of=count_of
        self.adjust=adjust
    def i2m(self, pkt, x):
        return FieldLenField.i2m.im_func(self, pkt, x)


class XBitField(BitField):
    def i2repr(self, pkt, x):
        return lhex(self.i2h(pkt,x))


class EnumField(Field):
    def __init__(self, name, default, enum, fmt = "H"):
        i2s = self.i2s = {}
        s2i = self.s2i = {}
        if type(enum) is list:
            keys = xrange(len(enum))
        else:
            keys = enum.keys()
        if filter(lambda x: type(x) is str, keys):
            i2s,s2i = s2i,i2s
        for k in keys:
            i2s[k] = enum[k]
            s2i[enum[k]] = k
        Field.__init__(self, name, default, fmt)
    def any2i_one(self, pkt, x):
        if type(x) is str:
            x = self.s2i[x]
        return x
    def i2repr_one(self, pkt, x):
        if self not in conf.noenum and not isinstance(x,VolatileValue) and x in self.i2s:
            return self.i2s[x]
        return repr(x)
    
    def any2i(self, pkt, x):
        if type(x) is list:
            return map(lambda z,pkt=pkt:self.any2i_one(pkt,z), x)
        else:
            return self.any2i_one(pkt,x)        
    def i2repr(self, pkt, x):
        if type(x) is list:
            return map(lambda z,pkt=pkt:self.i2repr_one(pkt,z), x)
        else:
            return self.i2repr_one(pkt,x)

class CharEnumField(EnumField):
    def __init__(self, name, default, enum, fmt = "1s"):
        EnumField.__init__(self, name, default, enum, fmt)
        k = self.i2s.keys()
        if k and len(k[0]) != 1:
            self.i2s,self.s2i = self.s2i,self.i2s
    def any2i_one(self, pkt, x):
        if len(x) != 1:
            x = self.s2i[x]
        return x

class BitEnumField(BitField,EnumField):
    def __init__(self, name, default, size, enum):
        EnumField.__init__(self, name, default, enum)
        self.rev = size < 0
        self.size = abs(size)
    def any2i(self, pkt, x):
        return EnumField.any2i(self, pkt, x)
    def i2repr(self, pkt, x):
        return EnumField.i2repr(self, pkt, x)

class ShortEnumField(EnumField):
    def __init__(self, name, default, enum):
        EnumField.__init__(self, name, default, enum, "H")

class LEShortEnumField(EnumField):
    def __init__(self, name, default, enum):
        EnumField.__init__(self, name, default, enum, "<H")

class ByteEnumField(EnumField):
    def __init__(self, name, default, enum):
        EnumField.__init__(self, name, default, enum, "B")

class IntEnumField(EnumField):
    def __init__(self, name, default, enum):
        EnumField.__init__(self, name, default, enum, "I")

class SignedIntEnumField(EnumField):
    def __init__(self, name, default, enum):
        EnumField.__init__(self, name, default, enum, "i")
    def randval(self):
        return RandSInt()

class LEIntEnumField(EnumField):
    def __init__(self, name, default, enum):
        EnumField.__init__(self, name, default, enum, "<I")

class XShortEnumField(ShortEnumField):
    def i2repr_one(self, pkt, x):
        if self not in conf.noenum and not isinstance(x,VolatileValue) and x in self.i2s:
            return self.i2s[x]
        return lhex(x)

class MultiEnumField(EnumField):
    def __init__(self, name, default, enum, depends_on, fmt = "H"):
        
        self.depends_on = depends_on
        self.i2s_multi = enum
        self.s2i_multi = {}
        self.s2i_all = {}
        for m in enum:
            self.s2i_multi[m] = s2i = {}
            for k,v in enum[m].iteritems():
                s2i[v] = k
                self.s2i_all[v] = k
        Field.__init__(self, name, default, fmt)
    def any2i_one(self, pkt, x):
        if type (x) is str:
            v = self.depends_on(pkt)
            if v in self.s2i_multi:
                s2i = self.s2i_multi[v]
                if x in s2i:
                    return s2i[x]
            return self.s2i_all[x]
        return x
    def i2repr_one(self, pkt, x):
        v = self.depends_on(pkt)
        if v in self.i2s_multi:
            return self.i2s_multi[v].get(x,x)
        return x

class BitMultiEnumField(BitField,MultiEnumField):
    def __init__(self, name, default, size, enum, depends_on):
        MultiEnumField.__init__(self, name, default, enum)
        self.rev = size < 0
        self.size = abs(size)
    def any2i(self, pkt, x):
        return MultiEnumField.any2i(self, pkt, x)
    def i2repr(self, pkt, x):
        return MultiEnumField.i2repr(self, pkt, x)


# Little endian long field
class LELongField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "<Q")

# Little endian fixed length field
class LEFieldLenField(FieldLenField):
    def __init__(self, name, default,  length_of=None, fmt = "<H", count_of=None, adjust=lambda pkt,x:x, fld=None):
        FieldLenField.__init__(self, name, default, length_of=length_of, fmt=fmt, fld=fld, adjust=adjust)


class FlagsField(BitField):
    def __init__(self, name, default, size, names):
        self.multi = type(names) is list
        if self.multi:
            self.names = map(lambda x:[x], names)
        else:
            self.names = names
        BitField.__init__(self, name, default, size)
    def any2i(self, pkt, x):
        if type(x) is str:
            if self.multi:
                x = map(lambda y:[y], x.split("+"))
            y = 0
            for i in x:
                y |= 1 << self.names.index(i)
            x = y
        return x
    def i2repr(self, pkt, x):
        if type(x) is list or type(x) is tuple:
            return repr(x)
        if self.multi:
            r = []
        else:
            r = ""
        i=0
        while x:
            if x & 1:
                r += self.names[i]
            i += 1
            x >>= 1
        if self.multi:
            r = "+".join(r)
        return r

            


class FixedPointField(BitField):
    def __init__(self, name, default, size, frac_bits=16):
        self.frac_bits = frac_bits
        BitField.__init__(self, name, default, size)

    def any2i(self, pkt, val):
        if val is None:
            return val
        ival = int(val)
        fract = int( (val-ival) * 2**self.frac_bits )
        return (ival << self.frac_bits) | fract

    def i2h(self, pkt, val):
        int_part = val >> self.frac_bits
        frac_part = val & (1L << self.frac_bits) - 1
        frac_part /= 2.0**self.frac_bits
        return int_part+frac_part
    def i2repr(self, pkt, val):
        return self.i2h(pkt, val)

########NEW FILE########
__FILENAME__ = all
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
All layers. Configurable with conf.load_layers.
"""

from scapy.config import conf
from scapy.error import log_loading
import logging
log = logging.getLogger("scapy.loading")

def _import_star(m):
    mod = __import__(m, globals(), locals())
    for k,v in mod.__dict__.iteritems():
        globals()[k] = v

for _l in conf.load_layers:
    log_loading.debug("Loading layer %s" % _l)
    try:
        _import_star(_l)
    except Exception,e:
	log.warning("can't import layer %s: %s" % (_l,e))





########NEW FILE########
__FILENAME__ = bluetooth
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Bluetooth layers, sockets and send/receive functions.
"""

import socket,struct

from scapy.config import conf
from scapy.packet import *
from scapy.fields import *
from scapy.supersocket import SuperSocket
from scapy.data import MTU


class HCI_Hdr(Packet):
    name = "HCI header"
    fields_desc = [ ByteEnumField("type",2,{1:"command",2:"ACLdata",3:"SCOdata",4:"event",5:"vendor"}),]

    def mysummary(self):
        return self.sprintf("HCI %type%")

class HCI_ACL_Hdr(Packet):
    name = "HCI ACL header"
    fields_desc = [ ByteField("handle",0), # Actually, handle is 12 bits and flags is 4.
                    ByteField("flags",0),  # I wait to write a LEBitField
                    LEShortField("len",None), ]
    def post_build(self, p, pay):
        p += pay
        if self.len is None:
            l = len(p)-4
            p = p[:2]+chr(l&0xff)+chr((l>>8)&0xff)+p[4:]
        return p
                    

class L2CAP_Hdr(Packet):
    name = "L2CAP header"
    fields_desc = [ LEShortField("len",None),
                    LEShortEnumField("cid",0,{1:"control"}),]
    
    def post_build(self, p, pay):
        p += pay
        if self.len is None:
            l = len(p)-4
            p = p[:2]+chr(l&0xff)+chr((l>>8)&0xff)+p[4:]
        return p
                    
                

class L2CAP_CmdHdr(Packet):
    name = "L2CAP command header"
    fields_desc = [
        ByteEnumField("code",8,{1:"rej",2:"conn_req",3:"conn_resp",
                                4:"conf_req",5:"conf_resp",6:"disconn_req",
                                7:"disconn_resp",8:"echo_req",9:"echo_resp",
                                10:"info_req",11:"info_resp"}),
        ByteField("id",0),
        LEShortField("len",None) ]
    def post_build(self, p, pay):
        p += pay
        if self.len is None:
            l = len(p)-4
            p = p[:2]+chr(l&0xff)+chr((l>>8)&0xff)+p[4:]
        return p
    def answers(self, other):
        if other.id == self.id:
            if self.code == 1:
                return 1
            if other.code in [2,4,6,8,10] and self.code == other.code+1:
                if other.code == 8:
                    return 1
                return self.payload.answers(other.payload)
        return 0

class L2CAP_ConnReq(Packet):
    name = "L2CAP Conn Req"
    fields_desc = [ LEShortEnumField("psm",0,{1:"SDP",3:"RFCOMM",5:"telephony control"}),
                    LEShortField("scid",0),
                    ]

class L2CAP_ConnResp(Packet):
    name = "L2CAP Conn Resp"
    fields_desc = [ LEShortField("dcid",0),
                    LEShortField("scid",0),
                    LEShortEnumField("result",0,["no_info","authen_pend","author_pend"]),
                    LEShortEnumField("status",0,["success","pend","bad_psm",
                                               "cr_sec_block","cr_no_mem"]),
                    ]
    def answers(self, other):
        return self.scid == other.scid

class L2CAP_CmdRej(Packet):
    name = "L2CAP Command Rej"
    fields_desc = [ LEShortField("reason",0),
                    ]
    

class L2CAP_ConfReq(Packet):
    name = "L2CAP Conf Req"
    fields_desc = [ LEShortField("dcid",0),
                    LEShortField("flags",0),
                    ]

class L2CAP_ConfResp(Packet):
    name = "L2CAP Conf Resp"
    fields_desc = [ LEShortField("scid",0),
                    LEShortField("flags",0),
                    LEShortEnumField("result",0,["success","unaccept","reject","unknown"]),
                    ]
    def answers(self, other):
        return self.scid == other.scid


class L2CAP_DisconnReq(Packet):
    name = "L2CAP Disconn Req"
    fields_desc = [ LEShortField("dcid",0),
                    LEShortField("scid",0), ]

class L2CAP_DisconnResp(Packet):
    name = "L2CAP Disconn Resp"
    fields_desc = [ LEShortField("dcid",0),
                    LEShortField("scid",0), ]
    def answers(self, other):
        return self.scid == other.scid

    

class L2CAP_InfoReq(Packet):
    name = "L2CAP Info Req"
    fields_desc = [ LEShortEnumField("type",0,{1:"CL_MTU",2:"FEAT_MASK"}),
                    StrField("data","")
                    ]


class L2CAP_InfoResp(Packet):
    name = "L2CAP Info Resp"
    fields_desc = [ LEShortField("type",0),
                    LEShortEnumField("result",0,["success","not_supp"]),
                    StrField("data",""), ]
    def answers(self, other):
        return self.type == other.type



bind_layers( HCI_Hdr,       HCI_ACL_Hdr,   type=2)
bind_layers( HCI_Hdr,       Raw,           )
bind_layers( HCI_ACL_Hdr,   L2CAP_Hdr,     )
bind_layers( L2CAP_Hdr,     L2CAP_CmdHdr,      cid=1)
bind_layers( L2CAP_CmdHdr,  L2CAP_CmdRej,      code=1)
bind_layers( L2CAP_CmdHdr,  L2CAP_ConnReq,     code=2)
bind_layers( L2CAP_CmdHdr,  L2CAP_ConnResp,    code=3)
bind_layers( L2CAP_CmdHdr,  L2CAP_ConfReq,     code=4)
bind_layers( L2CAP_CmdHdr,  L2CAP_ConfResp,    code=5)
bind_layers( L2CAP_CmdHdr,  L2CAP_DisconnReq,  code=6)
bind_layers( L2CAP_CmdHdr,  L2CAP_DisconnResp, code=7)
bind_layers( L2CAP_CmdHdr,  L2CAP_InfoReq,     code=10)
bind_layers( L2CAP_CmdHdr,  L2CAP_InfoResp,    code=11)
        
class BluetoothL2CAPSocket(SuperSocket):
    desc = "read/write packets on a connected L2CAP socket"
    def __init__(self, peer):
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW,
                          socket.BTPROTO_L2CAP)
        s.connect((peer,0))
        
        self.ins = self.outs = s

    def recv(self, x=MTU):
        return L2CAP_CmdHdr(self.ins.recv(x))
    

class BluetoothHCISocket(SuperSocket):
    desc = "read/write on a BlueTooth HCI socket"
    def __init__(self, iface=0x10000, type=None):
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)
        s.setsockopt(socket.SOL_HCI, socket.HCI_DATA_DIR,1)
        s.setsockopt(socket.SOL_HCI, socket.HCI_TIME_STAMP,1)
        s.setsockopt(socket.SOL_HCI, socket.HCI_FILTER, struct.pack("IIIh2x", 0xffffffffL,0xffffffffL,0xffffffffL,0)) #type mask, event mask, event mask, opcode
        s.bind((iface,))
        self.ins = self.outs = s
#        s.connect((peer,0))
        

    def recv(self, x):
        return HCI_Hdr(self.ins.recv(x))
    
## Bluetooth


@conf.commands.register
def srbt(peer, pkts, inter=0.1, *args, **kargs):
    """send and receive using a bluetooth socket"""
    s = conf.BTsocket(peer=peer)
    a,b = sndrcv(s,pkts,inter=inter,*args,**kargs)
    s.close()
    return a,b

@conf.commands.register
def srbt1(peer, pkts, *args, **kargs):
    """send and receive 1 packet using a bluetooth socket"""
    a,b = srbt(peer, pkts, *args, **kargs)
    if len(a) > 0:
        return a[0][1]
        
    

conf.BTsocket = BluetoothL2CAPSocket

########NEW FILE########
__FILENAME__ = dhcp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
DHCP (Dynamic Host Configuration Protocol) d BOOTP
"""

import struct

from scapy.packet import *
from scapy.fields import *
from scapy.ansmachine import *
from scapy.layers.inet import UDP,IP
from scapy.layers.l2 import Ether
from scapy.base_classes import Net
from scapy.volatile import RandField

from scapy.arch import get_if_raw_hwaddr
from scapy.sendrecv import srp1

dhcpmagic="c\x82Sc"


class BOOTP(Packet):
    name = "BOOTP"
    fields_desc = [ ByteEnumField("op",1, {1:"BOOTREQUEST", 2:"BOOTREPLY"}),
                    ByteField("htype",1),
                    ByteField("hlen",6),
                    ByteField("hops",0),
                    IntField("xid",0),
                    ShortField("secs",0),
                    FlagsField("flags", 0, 16, "???????????????B"),
                    IPField("ciaddr","0.0.0.0"),
                    IPField("yiaddr","0.0.0.0"),
                    IPField("siaddr","0.0.0.0"),
                    IPField("giaddr","0.0.0.0"),
                    Field("chaddr","", "16s"),
                    Field("sname","","64s"),
                    Field("file","","128s"),
                    StrField("options","") ]
    def guess_payload_class(self, payload):
        if self.options[:len(dhcpmagic)] == dhcpmagic:
            return DHCP
        else:
            return Packet.guess_payload_class(self, payload)
    def extract_padding(self,s):
        if self.options[:len(dhcpmagic)] == dhcpmagic:
            # set BOOTP options to DHCP magic cookie and make rest a payload of DHCP options
            payload = self.options[len(dhcpmagic):]
            self.options = self.options[:len(dhcpmagic)]
            return payload, None
        else:
            return "", None
    def hashret(self):
        return struct.pack("L", self.xid)
    def answers(self, other):
        if not isinstance(other, BOOTP):
            return 0
        return self.xid == other.xid



#DHCP_UNKNOWN, DHCP_IP, DHCP_IPLIST, DHCP_TYPE \
#= range(4)
#

DHCPTypes = {
                1: "discover",
                2: "offer",
                3: "request",
                4: "decline",
                5: "ack",
                6: "nak",
                7: "release",
                8: "inform",
                9: "force_renew",
                10:"lease_query",
                11:"lease_unassigned",
                12:"lease_unknown",
                13:"lease_active",
                }

DHCPOptions = {
    0: "pad",
    1: IPField("subnet_mask", "0.0.0.0"),
    2: "time_zone",
    3: IPField("router","0.0.0.0"),
    4: IPField("time_server","0.0.0.0"),
    5: IPField("IEN_name_server","0.0.0.0"),
    6: IPField("name_server","0.0.0.0"),
    7: IPField("log_server","0.0.0.0"),
    8: IPField("cookie_server","0.0.0.0"),
    9: IPField("lpr_server","0.0.0.0"),
    12: "hostname",
    14: "dump_path",
    15: "domain",
    17: "root_disk_path",
    22: "max_dgram_reass_size",
    23: "default_ttl",
    24: "pmtu_timeout",
    28: IPField("broadcast_address","0.0.0.0"),
    35: "arp_cache_timeout",
    36: "ether_or_dot3",
    37: "tcp_ttl",
    38: "tcp_keepalive_interval",
    39: "tcp_keepalive_garbage",
    40: "NIS_domain",
    41: IPField("NIS_server","0.0.0.0"),
    42: IPField("NTP_server","0.0.0.0"),
    43: "vendor_specific",
    44: IPField("NetBIOS_server","0.0.0.0"),
    45: IPField("NetBIOS_dist_server","0.0.0.0"),
    50: IPField("requested_addr","0.0.0.0"),
    51: IntField("lease_time", 43200),
    54: IPField("server_id","0.0.0.0"),
    55: "param_req_list",
    57: ShortField("max_dhcp_size", 1500),
    58: IntField("renewal_time", 21600),
    59: IntField("rebinding_time", 37800),
    60: "vendor_class_id",
    61: "client_id",
    
    64: "NISplus_domain",
    65: IPField("NISplus_server","0.0.0.0"),
    69: IPField("SMTP_server","0.0.0.0"),
    70: IPField("POP3_server","0.0.0.0"),
    71: IPField("NNTP_server","0.0.0.0"),
    72: IPField("WWW_server","0.0.0.0"),
    73: IPField("Finger_server","0.0.0.0"),
    74: IPField("IRC_server","0.0.0.0"),
    75: IPField("StreetTalk_server","0.0.0.0"),
    76: "StreetTalk_Dir_Assistance",
    82: "relay_agent_Information",
    53: ByteEnumField("message-type", 1, DHCPTypes),
    #             55: DHCPRequestListField("request-list"),
    255: "end"
    }

DHCPRevOptions = {}

for k,v in DHCPOptions.iteritems():
    if type(v) is str:
        n = v
        v = None
    else:
        n = v.name
    DHCPRevOptions[n] = (k,v)
del(n)
del(v)
del(k)
    
    


class RandDHCPOptions(RandField):
    def __init__(self, size=None, rndstr=None):
        if size is None:
            size = RandNumExpo(0.05)
        self.size = size
        if rndstr is None:
            rndstr = RandBin(RandNum(0,255))
        self.rndstr=rndstr
        self._opts = DHCPOptions.values()
        self._opts.remove("pad")
        self._opts.remove("end")
    def _fix(self):
        op = []
        for k in range(self.size):
            o = random.choice(self._opts)
            if type(o) is str:
                op.append((o,self.rndstr*1))
            else:
                op.append((o.name, o.randval()._fix()))
        return op


class DHCPOptionsField(StrField):
    islist=1
    def i2repr(self,pkt,x):
        s = []
        for v in x:
            if type(v) is tuple and len(v) >= 2:
                if  DHCPRevOptions.has_key(v[0]) and isinstance(DHCPRevOptions[v[0]][1],Field):
                    f = DHCPRevOptions[v[0]][1]
                    vv = ",".join(f.i2repr(pkt,val) for val in v[1:])
                else:
                    vv = ",".join(repr(val) for val in v[1:])
                r = "%s=%s" % (v[0],vv)
                s.append(r)
            else:
                s.append(sane(v))
        return "[%s]" % (" ".join(s))
        
    def getfield(self, pkt, s):
        return "", self.m2i(pkt, s)
    def m2i(self, pkt, x):
        opt = []
        while x:
            o = ord(x[0])
            if o == 255:
                opt.append("end")
                x = x[1:]
                continue
            if o == 0:
                opt.append("pad")
                x = x[1:]
                continue
            if len(x) < 2 or len(x) < ord(x[1])+2:
                opt.append(x)
                break
            elif DHCPOptions.has_key(o):
                f = DHCPOptions[o]

                if isinstance(f, str):
                    olen = ord(x[1])
                    opt.append( (f,x[2:olen+2]) )
                    x = x[olen+2:]
                else:
                    olen = ord(x[1])
                    lval = [f.name]
                    try:
                        left = x[2:olen+2]
                        while left:
                            left, val = f.getfield(pkt,left)
                            lval.append(val)
                    except:
                        opt.append(x)
                        break
                    else:
                        otuple = tuple(lval)
                    opt.append(otuple)
                    x = x[olen+2:]
            else:
                olen = ord(x[1])
                opt.append((o, x[2:olen+2]))
                x = x[olen+2:]
        return opt
    def i2m(self, pkt, x):
        if type(x) is str:
            return x
        s = ""
        for o in x:
            if type(o) is tuple and len(o) >= 2:
                name = o[0]
                lval = o[1:]

                if isinstance(name, int):
                    onum, oval = name, "".join(lval)
                elif DHCPRevOptions.has_key(name):
                    onum, f = DHCPRevOptions[name]
                    if  f is not None:
                        lval = [f.addfield(pkt,"",f.any2i(pkt,val)) for val in lval]
                    oval = "".join(lval)
                else:
                    warning("Unknown field option %s" % name)
                    continue

                s += chr(onum)
                s += chr(len(oval))
                s += oval

            elif (type(o) is str and DHCPRevOptions.has_key(o) and 
                  DHCPRevOptions[o][1] == None):
                s += chr(DHCPRevOptions[o][0])
            elif type(o) is int:
                s += chr(o)+"\0"
            elif type(o) is str:
                s += o
            else:
                warning("Malformed option %s" % o)
        return s


class DHCP(Packet):
    name = "DHCP options"
    fields_desc = [ DHCPOptionsField("options","") ]


bind_layers( UDP,           BOOTP,         dport=67, sport=68)
bind_layers( UDP,           BOOTP,         dport=68, sport=67)
bind_bottom_up( UDP, BOOTP, dport=67, sport=67)
bind_layers( BOOTP,         DHCP,          options='c\x82Sc')

def dhcp_request(iface=None,**kargs):
    if conf.checkIPaddr != 0:
        warning("conf.checkIPaddr is not 0, I may not be able to match the answer")
    if iface is None:
        iface = conf.iface
    fam,hw = get_if_raw_hwaddr(iface)
    return srp1(Ether(dst="ff:ff:ff:ff:ff:ff")/IP(src="0.0.0.0",dst="255.255.255.255")/UDP(sport=68,dport=67)
                 /BOOTP(chaddr=hw)/DHCP(options=[("message-type","discover"),"end"]),iface=iface,**kargs)


class BOOTP_am(AnsweringMachine):
    function_name = "bootpd"
    filter = "udp and port 68 and port 67"
    send_function = staticmethod(sendp)
    def parse_options(self, pool=Net("192.168.1.128/25"), network="192.168.1.0/24",gw="192.168.1.1",
                      domain="localnet", renewal_time=60, lease_time=1800):
        if type(pool) is str:
            poom = Net(pool)
        self.domain = domain
        netw,msk = (network.split("/")+["32"])[:2]
        msk = itom(int(msk))
        self.netmask = ltoa(msk)
        self.network = ltoa(atol(netw)&msk)
        self.broadcast = ltoa( atol(self.network) | (0xffffffff&~msk) )
        self.gw = gw
        if isinstance(pool,Gen):
            pool = [k for k in pool if k not in [gw, self.network, self.broadcast]]
            pool.reverse()
        if len(pool) == 1:
            pool, = pool
        self.pool = pool
        self.lease_time = lease_time
        self.renewal_time = renewal_time
        self.leases = {}

    def is_request(self, req):
        if not req.haslayer(BOOTP):
            return 0
        reqb = req.getlayer(BOOTP)
        if reqb.op != 1:
            return 0
        return 1

    def print_reply(self, req, reply):
        print "Reply %s to %s" % (reply.getlayer(IP).dst,reply.dst)

    def make_reply(self, req):        
        mac = req.src
        if type(self.pool) is list:
            if not self.leases.has_key(mac):
                self.leases[mac] = self.pool.pop()
            ip = self.leases[mac]
        else:
            ip = self.pool
            
        repb = req.getlayer(BOOTP).copy()
        repb.op="BOOTREPLY"
        repb.yiaddr = ip
        repb.siaddr = self.gw
        repb.ciaddr = self.gw
        repb.giaddr = self.gw
        del(repb.payload)
        rep=Ether(dst=mac)/IP(dst=ip)/UDP(sport=req.dport,dport=req.sport)/repb
        return rep


class DHCP_am(BOOTP_am):
    function_name="dhcpd"
    def make_reply(self, req):
        resp = BOOTP_am.make_reply(self, req)
        if DHCP in req:
            dhcp_options = [(op[0],{1:2,3:5}.get(op[1],op[1]))
                            for op in req[DHCP].options
                            if type(op) is tuple  and op[0] == "message-type"]
            dhcp_options += [("server_id",self.gw),
                             ("domain", self.domain),
                             ("router", self.gw),
                             ("name_server", self.gw),
                             ("broadcast_address", self.broadcast),
                             ("subnet_mask", self.netmask),
                             ("renewal_time", self.renewal_time),
                             ("lease_time", self.lease_time), 
                             "end"
                             ]
            resp /= DHCP(options=dhcp_options)
        return resp
    


########NEW FILE########
__FILENAME__ = dhcp6
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

## Copyright (C) 2005  Guillaume Valadon <guedou@hongo.wide.ad.jp>
##                     Arnaud Ebalard <arnaud.ebalard@eads.net>

"""
DHCPv6: Dynamic Host Configuration Protocol for IPv6. [RFC 3315]
"""

import socket
from scapy.packet import *
from scapy.fields import *
from scapy.utils6 import *
from scapy.layers.inet6 import *
from scapy.ansmachine import AnsweringMachine

#############################################################################
# Helpers                                                                  ##
#############################################################################

def get_cls(name, fallback_cls):
    return globals().get(name, fallback_cls)


#############################################################################
#############################################################################
###                                DHCPv6                                 ###
#############################################################################
#############################################################################

All_DHCP_Relay_Agents_and_Servers = "ff02::1:2" 
All_DHCP_Servers = "ff05::1:3"  # Site-Local scope : deprecated by 3879

dhcp6opts = { 1: "CLIENTID",  
              2: "SERVERID",
              3: "IA_NA",
              4: "IA_TA",
              5: "IAADDR",
              6: "ORO",
              7: "PREFERENCE",
              8: "ELAPSED_TIME",
              9: "RELAY_MSG",
             11: "AUTH",
             12: "UNICAST",
             13: "STATUS_CODE",
             14: "RAPID_COMMIT",
             15: "USER_CLASS",
             16: "VENDOR_CLASS",
             17: "VENDOR_OPTS",
             18: "INTERFACE_ID",
             19: "RECONF_MSG",
             20: "RECONF_ACCEPT",
             21: "SIP Servers Domain Name List",     #RFC3319
             22: "SIP Servers IPv6 Address List",    #RFC3319
             23: "DNS Recursive Name Server Option", #RFC3646
             24: "Domain Search List option",        #RFC3646
             25: "OPTION_IA_PD",                     #RFC3633
             26: "OPTION_IAPREFIX",                  #RFC3633
             27: "OPTION_NIS_SERVERS",               #RFC3898
             28: "OPTION_NISP_SERVERS",              #RFC3898
             29: "OPTION_NIS_DOMAIN_NAME",           #RFC3898
             30: "OPTION_NISP_DOMAIN_NAME",          #RFC3898
             31: "OPTION_SNTP_SERVERS",              #RFC4075
             32: "OPTION_INFORMATION_REFRESH_TIME",  #RFC4242
             33: "OPTION_BCMCS_SERVER_D",            #RFC4280         
             34: "OPTION_BCMCS_SERVER_A",            #RFC4280
             36: "OPTION_GEOCONF_CIVIC",             #RFC-ietf-geopriv-dhcp-civil-09.txt
             37: "OPTION_REMOTE_ID",                 #RFC4649
             38: "OPTION_SUBSCRIBER_ID",             #RFC4580
             39: "OPTION_CLIENT_FQDN" }              #RFC4704

dhcp6opts_by_code = {  1: "DHCP6OptClientId", 
                       2: "DHCP6OptServerId",
                       3: "DHCP6OptIA_NA",
                       4: "DHCP6OptIA_TA",
                       5: "DHCP6OptIAAddress",
                       6: "DHCP6OptOptReq",
                       7: "DHCP6OptPref",
                       8: "DHCP6OptElapsedTime",
                       9: "DHCP6OptRelayMsg",
                       11: "DHCP6OptAuth",
                       12: "DHCP6OptServerUnicast",
                       13: "DHCP6OptStatusCode",
                       14: "DHCP6OptRapidCommit",
                       15: "DHCP6OptUserClass",
                       16: "DHCP6OptVendorClass",
                       17: "DHCP6OptVendorSpecificInfo",
                       18: "DHCP6OptIfaceId",
                       19: "DHCP6OptReconfMsg",
                       20: "DHCP6OptReconfAccept",
                       21: "DHCP6OptSIPDomains",          #RFC3319
                       22: "DHCP6OptSIPServers",          #RFC3319
                       23: "DHCP6OptDNSServers",          #RFC3646
                       24: "DHCP6OptDNSDomains",          #RFC3646
                       25: "DHCP6OptIA_PD",               #RFC3633
                       26: "DHCP6OptIAPrefix",            #RFC3633
                       27: "DHCP6OptNISServers",          #RFC3898
                       28: "DHCP6OptNISPServers",         #RFC3898
                       29: "DHCP6OptNISDomain",           #RFC3898
                       30: "DHCP6OptNISPDomain",          #RFC3898
                       31: "DHCP6OptSNTPServers",         #RFC4075
                       32: "DHCP6OptInfoRefreshTime",     #RFC4242
                       33: "DHCP6OptBCMCSDomains",        #RFC4280         
                       34: "DHCP6OptBCMCSServers",        #RFC4280
                       #36: "DHCP6OptGeoConf",            #RFC-ietf-geopriv-dhcp-civil-09.txt
                       37: "DHCP6OptRemoteID",            #RFC4649
                       38: "DHCP6OptSubscriberID",        #RFC4580
                       39: "DHCP6OptClientFQDN",          #RFC4704
                       #40: "DHCP6OptPANAAgent",          #RFC-ietf-dhc-paa-option-05.txt
                       #41: "DHCP6OptNewPOSIXTimeZone,    #RFC4833
                       #42: "DHCP6OptNewTZDBTimeZone,     #RFC4833
                       43: "DHCP6OptRelayAgentERO"        #RFC4994
                       #44: "DHCP6OptLQQuery",            #RFC5007
                       #45: "DHCP6OptLQClientData",       #RFC5007
                       #46: "DHCP6OptLQClientTime",       #RFC5007
                       #47: "DHCP6OptLQRelayData",        #RFC5007
                       #48: "DHCP6OptLQClientLink",       #RFC5007
}


# sect 5.3 RFC 3315 : DHCP6 Messages types
dhcp6types = {   1:"SOLICIT",
                 2:"ADVERTISE",
                 3:"REQUEST",
                 4:"CONFIRM",
                 5:"RENEW",
                 6:"REBIND",
                 7:"REPLY",
                 8:"RELEASE",
                 9:"DECLINE",
                10:"RECONFIGURE",
                11:"INFORMATION-REQUEST",
                12:"RELAY-FORW",
                13:"RELAY-REPL" }


#####################################################################
###                  DHCPv6 DUID related stuff                    ###
#####################################################################

duidtypes = { 1: "Link-layer address plus time", 
              2: "Vendor-assigned unique ID based on Enterprise Number",
              3: "Link-layer Address" }

# DUID hardware types - RFC 826 - Extracted from 
# http://www.iana.org/assignments/arp-parameters on 31/10/06
# We should add the length of every kind of address.
duidhwtypes = {  0: "NET/ROM pseudo", # Not referenced by IANA
                 1: "Ethernet (10Mb)",
                 2: "Experimental Ethernet (3Mb)",
                 3: "Amateur Radio AX.25",
                 4: "Proteon ProNET Token Ring",
                 5: "Chaos",
                 6: "IEEE 802 Networks",
                 7: "ARCNET",
                 8: "Hyperchannel",
                 9: "Lanstar",
                10: "Autonet Short Address",
                11: "LocalTalk",
                12: "LocalNet (IBM PCNet or SYTEK LocalNET)",
                13: "Ultra link",
                14: "SMDS",
                15: "Frame Relay",
                16: "Asynchronous Transmission Mode (ATM)",
                17: "HDLC",
                18: "Fibre Channel",
                19: "Asynchronous Transmission Mode (ATM)",
                20: "Serial Line",
                21: "Asynchronous Transmission Mode (ATM)",
                22: "MIL-STD-188-220",
                23: "Metricom",
                24: "IEEE 1394.1995",
                25: "MAPOS",
                26: "Twinaxial",
                27: "EUI-64",
                28: "HIPARP",
                29: "IP and ARP over ISO 7816-3",
                30: "ARPSec",
                31: "IPsec tunnel",
                32: "InfiniBand (TM)",
                33: "TIA-102 Project 25 Common Air Interface (CAI)" }

class UTCTimeField(IntField):
    epoch = (2000, 1, 1, 0, 0, 0, 5, 1, 0) # required Epoch
    def i2repr(self, pkt, x):
        x = self.i2h(pkt, x)
        from time import gmtime, strftime, mktime
        delta = mktime(self.epoch) - mktime(gmtime(0))
        x = x + delta
        t = strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime(x))
        return "%s (%d)" % (t, x)

class _LLAddrField(MACField):
    pass

# XXX We only support Ethernet addresses at the moment. _LLAddrField 
#     will be modified when needed. Ask us. --arno
class DUID_LLT(Packet):  # sect 9.2 RFC 3315
    name = "DUID - Link-layer address plus time"
    fields_desc = [ ShortEnumField("type", 1, duidtypes),
                    XShortEnumField("hwtype", 1, duidhwtypes), 
                    UTCTimeField("timeval", 0), # i.e. 01 Jan 2000
                    _LLAddrField("lladdr", ETHER_ANY) ]

# In fact, IANA enterprise-numbers file available at 
# http//www.iana.org/asignments/enterprise-numbers)
# is simply huge (more than 2Mo and 600Ko in bz2). I'll
# add only most common vendors, and encountered values.
# -- arno
iana_enterprise_num = {    9: "ciscoSystems",
                          35: "Nortel Networks",
                          43: "3Com",
                         311: "Microsoft",
                        2636: "Juniper Networks, Inc.",
                        4526: "Netgear",
                        5771: "Cisco Systems, Inc.",
                        5842: "Cisco Systems",
                       16885: "Nortel Networks" }

class DUID_EN(Packet):  # sect 9.3 RFC 3315
    name = "DUID - Assigned by Vendor Based on Enterprise Number"
    fields_desc = [ ShortEnumField("type", 2, duidtypes),
                    IntEnumField("enterprisenum", 311, iana_enterprise_num),
                    StrField("id","") ] 

class DUID_LL(Packet):  # sect 9.4 RFC 3315
    name = "DUID - Based on Link-layer Address"
    fields_desc = [ ShortEnumField("type", 3, duidtypes),
                    XShortEnumField("hwtype", 1, duidhwtypes), 
                    _LLAddrField("lladdr", ETHER_ANY) ]

duid_cls = { 1: "DUID_LLT",
             2: "DUID_EN",
             3: "DUID_LL"}

#####################################################################
###                   DHCPv6 Options classes                      ###
#####################################################################

class _DHCP6OptGuessPayload(Packet):
    def guess_payload_class(self, payload):
        cls = Raw
        if len(payload) > 2 :
            opt = struct.unpack("!H", payload[:2])[0]
            cls = get_cls(dhcp6opts_by_code.get(opt, "DHCP6OptUnknown"), DHCP6OptUnknown)
        return cls

class DHCP6OptUnknown(_DHCP6OptGuessPayload): # A generic DHCPv6 Option
    name = "Unknown DHCPv6 OPtion"
    fields_desc = [ ShortEnumField("optcode", 0, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="data", fmt="!H"),
                    StrLenField("data", "",
                                length_from = lambda pkt: pkt.optlen)]

class _DUIDField(PacketField):
    holds_packets=1
    def __init__(self, name, default, length_from=None):
        StrField.__init__(self, name, default)
        self.length_from = length_from

    def i2m(self, pkt, i):
        return str(i)

    def m2i(self, pkt, x):
        cls = Raw 
        if len(x) > 4:
            o = struct.unpack("!H", x[:2])[0]
            cls = get_cls(duid_cls.get(o, Raw), "Raw")
        return cls(x)

    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        return s[l:], self.m2i(pkt,s[:l])
 

class DHCP6OptClientId(_DHCP6OptGuessPayload):     # RFC sect 22.2
    name = "DHCP6 Client Identifier Option"
    fields_desc = [ ShortEnumField("optcode", 1, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="duid", fmt="!H"),
                    _DUIDField("duid", "",
                               length_from = lambda pkt: pkt.optlen) ]


class DHCP6OptServerId(DHCP6OptClientId):     # RFC sect 22.3
    name = "DHCP6 Server Identifier Option"
    optcode = 2

# Should be encapsulated in the option field of IA_NA or IA_TA options
# Can only appear at that location.
# TODO : last field IAaddr-options is not defined in the reference document
class DHCP6OptIAAddress(_DHCP6OptGuessPayload):    # RFC sect 22.6
    name = "DHCP6 IA Address Option (IA_TA or IA_NA suboption)"
    fields_desc = [ ShortEnumField("optcode", 5, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="iaaddropts",
                                  fmt="!H", adjust = lambda pkt,x: x+24),
                    IP6Field("addr", "::"),
                    IntField("preflft", 0),
                    IntField("validlft", 0),
                    XIntField("iaid", None),
                    StrLenField("iaaddropts", "",
                                length_from  = lambda pkt: pkt.optlen - 24) ]
    def guess_payload_class(self, payload):
        return Padding

class _IANAOptField(PacketListField):
    def i2len(self, pkt, z):
        if z is None or z == []:
            return 0
        return sum(map(lambda x: len(str(x)) ,z))

    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        lst = []
        remain, payl = s[:l], s[l:]
        while len(remain)>0:
            p = self.m2i(pkt,remain)
            if Padding in p:
                pad = p[Padding]
                remain = pad.load
                del(pad.underlayer.payload)
            else:
                remain = ""
            lst.append(p)
        return payl,lst

class DHCP6OptIA_NA(_DHCP6OptGuessPayload):         # RFC sect 22.4
    name = "DHCP6 Identity Association for Non-temporary Addresses Option"
    fields_desc = [ ShortEnumField("optcode", 3, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="ianaopts",
                                  fmt="!H", adjust = lambda pkt,x: x+12),
                    XIntField("iaid", None),
                    IntField("T1", None),
                    IntField("T2", None),
                    _IANAOptField("ianaopts", [], DHCP6OptIAAddress,
                                  length_from = lambda pkt: pkt.optlen-12) ]

class _IATAOptField(_IANAOptField):
    pass

class DHCP6OptIA_TA(_DHCP6OptGuessPayload):         # RFC sect 22.5
    name = "DHCP6 Identity Association for Temporary Addresses Option"
    fields_desc = [ ShortEnumField("optcode", 4, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="iataopts",
                                  fmt="!H", adjust = lambda pkt,x: x+4),
                    XIntField("iaid", None),
                    _IATAOptField("iataopts", [], DHCP6OptIAAddress,
                                  length_from = lambda pkt: pkt.optlen-4) ]


#### DHCPv6 Option Request Option ###################################

class _OptReqListField(StrLenField):
    islist = 1
    def i2h(self, pkt, x):
        if x is None:
            return []
        return x

    def i2len(self, pkt, x):
        return 2*len(x)

    def any2i(self, pkt, x):
        return x

    def i2repr(self, pkt, x):
        s = []
        for y in self.i2h(pkt, x):
            if dhcp6opts.has_key(y):
                s.append(dhcp6opts[y])
            else:
                s.append("%d" % y)
        return "[%s]" % ", ".join(s) 

    def m2i(self, pkt, x):
        r = []
        while len(x) != 0:
            if len(x)<2:
                warning("Odd length for requested option field. Rejecting last byte")
                return r
            r.append(struct.unpack("!H", x[:2])[0])
            x = x[2:]
        return r
    
    def i2m(self, pkt, x):
        return "".join(map(lambda y: struct.pack("!H", y), x))

# A client may include an ORO in a solicit, Request, Renew, Rebind,
# Confirm or Information-request
class DHCP6OptOptReq(_DHCP6OptGuessPayload):       # RFC sect 22.7
    name = "DHCP6 Option Request Option"
    fields_desc = [ ShortEnumField("optcode", 6, dhcp6opts),
                    FieldLenField("optlen", None, length_of="reqopts", fmt="!H"),
                    _OptReqListField("reqopts", [23, 24],
                                     length_from = lambda pkt: pkt.optlen) ]


#### DHCPv6 Preference Option #######################################

# emise par un serveur pour affecter le choix fait par le client. Dans
# les messages Advertise, a priori
class DHCP6OptPref(_DHCP6OptGuessPayload):       # RFC sect 22.8
    name = "DHCP6 Preference Option"
    fields_desc = [ ShortEnumField("optcode", 7, dhcp6opts), 
                    ShortField("optlen", 1 ),
                    ByteField("prefval",255) ]


#### DHCPv6 Elapsed Time Option #####################################

class _ElapsedTimeField(ShortField):
    def i2repr(self, pkt, x):
        if x == 0xffff:
            return "infinity (0xffff)"
        return "%.2f sec" % (self.i2h(pkt, x)/100.)

class DHCP6OptElapsedTime(_DHCP6OptGuessPayload):# RFC sect 22.9
    name = "DHCP6 Elapsed Time Option"
    fields_desc = [ ShortEnumField("optcode", 8, dhcp6opts), 
                    ShortField("optlen", 2),
                    _ElapsedTimeField("elapsedtime", 0) ]


#### DHCPv6 Relay Message Option ####################################

# Relayed message is seen as a payload.
class DHCP6OptRelayMsg(_DHCP6OptGuessPayload):# RFC sect 22.10
    name = "DHCP6 Relay Message Option"
    fields_desc = [ ShortEnumField("optcode", 9, dhcp6opts), 
                    ShortField("optlen", None ) ]
    def post_build(self, p, pay):
        if self.optlen is None:
            l = len(pay) 
            p = p[:2]+struct.pack("!H", l)
        return p + pay


#### DHCPv6 Authentication Option ###################################

#    The following fields are set in an Authentication option for the
#    Reconfigure Key Authentication Protocol:
#
#       protocol    3
#
#       algorithm   1
#
#       RDM         0
#
#    The format of the Authentication information for the Reconfigure Key
#    Authentication Protocol is:
#
#      0                   1                   2                   3
#      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
#     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#     |     Type      |                 Value (128 bits)              |
#     +-+-+-+-+-+-+-+-+                                               |
#     .                                                               .
#     .                                                               .
#     .                                               +-+-+-+-+-+-+-+-+
#     |                                               |
#     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
#
#       Type    Type of data in Value field carried in this option:
#
#                  1   Reconfigure Key value (used in Reply message).
#
#                  2   HMAC-MD5 digest of the message (used in Reconfigure
#                      message).
#
#       Value   Data as defined by field.


# TODO : Decoding only at the moment
class DHCP6OptAuth(_DHCP6OptGuessPayload):    # RFC sect 22.11
    name = "DHCP6 Option - Authentication"
    fields_desc = [ ShortEnumField("optcode", 11, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="authinfo",
                                  adjust = lambda pkt,x: x+11),
                    ByteField("proto", 3), # TODO : XXX
                    ByteField("alg", 1), # TODO : XXX
                    ByteField("rdm", 0), # TODO : XXX
                    StrFixedLenField("replay", "A"*8, 8), # TODO: XXX
                    StrLenField("authinfo", "",
                                length_from = lambda pkt: pkt.optlen - 11) ]

#### DHCPv6 Server Unicast Option ###################################

class _SrvAddrField(IP6Field):
    def i2h(self, pkt, x):
        if x is None:
            return "::"
        return x
    
    def i2m(self, pkt, x):
        return inet_pton(socket.AF_INET6, self.i2h(pkt,x))

class DHCP6OptServerUnicast(_DHCP6OptGuessPayload):# RFC sect 22.12
    name = "DHCP6 Server Unicast Option"
    fields_desc = [ ShortEnumField("optcode", 12, dhcp6opts), 
                    ShortField("optlen", 16 ),
                    _SrvAddrField("srvaddr",None) ]


#### DHCPv6 Status Code Option ######################################

dhcp6statuscodes = { 0:"Success",      # sect 24.4
                     1:"UnspecFail",
                     2:"NoAddrsAvail",
                     3:"NoBinding",
                     4:"NotOnLink",
                     5:"UseMulticast",
                     6:"NoPrefixAvail"} # From RFC3633

class DHCP6OptStatusCode(_DHCP6OptGuessPayload):# RFC sect 22.13
    name = "DHCP6 Status Code Option"
    fields_desc = [ ShortEnumField("optcode", 13, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="statusmsg",
                                  fmt="!H", adjust = lambda pkt,x:x+2),
                    ShortEnumField("statuscode",None,dhcp6statuscodes),
                    StrLenField("statusmsg", "",
                                length_from = lambda pkt: pkt.optlen-2) ]


#### DHCPv6 Rapid Commit Option #####################################

class DHCP6OptRapidCommit(_DHCP6OptGuessPayload):   # RFC sect 22.14
    name = "DHCP6 Rapid Commit Option"
    fields_desc = [ ShortEnumField("optcode", 14, dhcp6opts),
                    ShortField("optlen", 0)]


#### DHCPv6 User Class Option #######################################

class _UserClassDataField(PacketListField):
    def i2len(self, pkt, z):
        if z is None or z == []:
            return 0
        return sum(map(lambda x: len(str(x)) ,z))

    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        lst = []
        remain, payl = s[:l], s[l:]
        while len(remain)>0:
            p = self.m2i(pkt,remain)
            if Padding in p:
                pad = p[Padding]
                remain = pad.load
                del(pad.underlayer.payload)
            else:
                remain = ""
            lst.append(p)
        return payl,lst


class USER_CLASS_DATA(Packet):
    name = "user class data"
    fields_desc = [ FieldLenField("len", None, length_of="data"),
                    StrLenField("data", "",
                                length_from = lambda pkt: pkt.len) ]
    def guess_payload_class(self, payload):
        return Padding

class DHCP6OptUserClass(_DHCP6OptGuessPayload):# RFC sect 22.15
    name = "DHCP6 User Class Option"
    fields_desc = [ ShortEnumField("optcode", 15, dhcp6opts), 
                    FieldLenField("optlen", None, fmt="!H",
                                  length_of="userclassdata"),
                    _UserClassDataField("userclassdata", [], USER_CLASS_DATA,
                                        length_from = lambda pkt: pkt.optlen) ]


#### DHCPv6 Vendor Class Option #####################################

class _VendorClassDataField(_UserClassDataField):
    pass

class VENDOR_CLASS_DATA(USER_CLASS_DATA):
    name = "vendor class data"

class DHCP6OptVendorClass(_DHCP6OptGuessPayload):# RFC sect 22.16
    name = "DHCP6 Vendor Class Option"
    fields_desc = [ ShortEnumField("optcode", 16, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="vcdata", fmt="!H",
                                  adjust = lambda pkt,x: x+4),
                    IntEnumField("enterprisenum",None , iana_enterprise_num ),
                    _VendorClassDataField("vcdata", [], VENDOR_CLASS_DATA,
                                          length_from = lambda pkt: pkt.optlen-4) ]

#### DHCPv6 Vendor-Specific Information Option ######################

class VENDOR_SPECIFIC_OPTION(_DHCP6OptGuessPayload):
    name = "vendor specific option data"
    fields_desc = [ ShortField("optcode", None),
                    FieldLenField("optlen", None, length_of="optdata"),
                    StrLenField("optdata", "",
                                length_from = lambda pkt: pkt.optlen) ]
    def guess_payload_class(self, payload):
        return Padding

# The third one that will be used for nothing interesting
class DHCP6OptVendorSpecificInfo(_DHCP6OptGuessPayload):# RFC sect 22.17
    name = "DHCP6 Vendor-specific Information Option"
    fields_desc = [ ShortEnumField("optcode", 17, dhcp6opts), 
                    FieldLenField("optlen", None, length_of="vso", fmt="!H",
                                  adjust = lambda pkt,x: x+4),
                    IntEnumField("enterprisenum",None , iana_enterprise_num),
                    _VendorClassDataField("vso", [], VENDOR_SPECIFIC_OPTION,
                                          length_from = lambda pkt: pkt.optlen-4) ]

#### DHCPv6 Interface-ID Option #####################################

# Repasser sur cette option a la fin. Elle a pas l'air d'etre des
# masses critique.
class DHCP6OptIfaceId(_DHCP6OptGuessPayload):# RFC sect 22.18
    name = "DHCP6 Interface-Id Option"
    fields_desc = [ ShortEnumField("optcode", 18, dhcp6opts),
                    FieldLenField("optlen", None, fmt="!H",
                                  length_of="ifaceid"),
                    StrLenField("ifaceid", "",
                                length_from = lambda pkt: pkt.optlen) ]


#### DHCPv6 Reconfigure Message Option ##############################

# A server includes a Reconfigure Message option in a Reconfigure
# message to indicate to the client whether the client responds with a
# renew message or an Informatiion-request message.
class DHCP6OptReconfMsg(_DHCP6OptGuessPayload):       # RFC sect 22.19
    name = "DHCP6 Reconfigure Message Option"
    fields_desc = [ ShortEnumField("optcode", 19, dhcp6opts), 
                    ShortField("optlen", 1 ),
                    ByteEnumField("msgtype", 11, {  5:"Renew Message", 
                                                   11:"Information Request"}) ]


#### DHCPv6 Reconfigure Accept Option ###############################

# A client uses the Reconfigure Accept option to announce to the
# server whether the client is willing to accept Recoonfigure
# messages, and a server uses this option to tell the client whether
# or not to accept Reconfigure messages. The default behavior in the
# absence of this option, means unwillingness to accept reconfigure
# messages, or instruction not to accept Reconfigure messages, for the
# client and server messages, respectively.
class DHCP6OptReconfAccept(_DHCP6OptGuessPayload):   # RFC sect 22.20
    name = "DHCP6 Reconfigure Accept Option"
    fields_desc = [ ShortEnumField("optcode", 20, dhcp6opts),
                    ShortField("optlen", 0)]

# As required in Sect 8. of RFC 3315, Domain Names must be encoded as 
# described in section 3.1 of RFC 1035
# XXX Label should be at most 63 octets in length : we do not enforce it
#     Total length of domain should be 255 : we do not enforce it either
class DomainNameListField(StrLenField):
    islist = 1

    def i2len(self, pkt, x):
        return len(self.i2m(pkt, x))

    def m2i(self, pkt, x):
        res = []
        while x:
            cur = []
            while x and x[0] != '\x00':
                l = ord(x[0])
                cur.append(x[1:l+1])
                x = x[l+1:]
            res.append(".".join(cur))
            if x and x[0] == '\x00':
                x = x[1:]
        return res

    def i2m(self, pkt, x):
        def conditionalTrailingDot(z):
            if z and z[-1] == '\x00':
                return z
            return z+'\x00'
        res = ""
        tmp = map(lambda y: map((lambda z: chr(len(z))+z), y.split('.')), x)
        return "".join(map(lambda x: conditionalTrailingDot("".join(x)), tmp))

class DHCP6OptSIPDomains(_DHCP6OptGuessPayload):       #RFC3319
    name = "DHCP6 Option - SIP Servers Domain Name List"
    fields_desc = [ ShortEnumField("optcode", 21, dhcp6opts),
                    FieldLenField("optlen", None, length_of="sipdomains"),
                    DomainNameListField("sipdomains", [],
                                        length_from = lambda pkt: pkt.optlen) ]

class DHCP6OptSIPServers(_DHCP6OptGuessPayload):          #RFC3319
    name = "DHCP6 Option - SIP Servers IPv6 Address List"
    fields_desc = [ ShortEnumField("optcode", 22, dhcp6opts),
                    FieldLenField("optlen", None, length_of="sipservers"),
                    IP6ListField("sipservers", [], 
                                 length_from = lambda pkt: pkt.optlen) ]

class DHCP6OptDNSServers(_DHCP6OptGuessPayload):          #RFC3646
    name = "DHCP6 Option - DNS Recursive Name Server"
    fields_desc = [ ShortEnumField("optcode", 23, dhcp6opts),
                    FieldLenField("optlen", None, length_of="dnsservers"),
                    IP6ListField("dnsservers", [],
                                 length_from = lambda pkt: pkt.optlen) ]

class DHCP6OptDNSDomains(_DHCP6OptGuessPayload): #RFC3646
    name = "DHCP6 Option - Domain Search List option"
    fields_desc = [ ShortEnumField("optcode", 24, dhcp6opts),
                    FieldLenField("optlen", None, length_of="dnsdomains"),
                    DomainNameListField("dnsdomains", [],
                                        length_from = lambda pkt: pkt.optlen) ]

# TODO: Implement iaprefopts correctly when provided with more 
#       information about it.
class DHCP6OptIAPrefix(_DHCP6OptGuessPayload):                    #RFC3633
    name = "DHCP6 Option - IA_PD Prefix option"
    fields_desc = [ ShortEnumField("optcode", 26, dhcp6opts),
                    FieldLenField("optlen", None, length_of="iaprefopts",
                                  adjust = lambda pkt,x: x+26),
                    IntField("preflft", 0),
                    IntField("validlft", 0),
                    ByteField("plen", 48),  # TODO: Challenge that default value
                    IP6Field("prefix", "2001:db8::"), # At least, global and won't hurt
                    StrLenField("iaprefopts", "",
                                length_from = lambda pkt: pkt.optlen-26) ]

class DHCP6OptIA_PD(_DHCP6OptGuessPayload):                       #RFC3633
    name = "DHCP6 Option - Identity Association for Prefix Delegation"
    fields_desc = [ ShortEnumField("optcode", 25, dhcp6opts),
                    FieldLenField("optlen", None, length_of="iapdopt",
                                  adjust = lambda pkt,x: x+12),
                    IntField("iaid", 0),
                    IntField("T1", 0),
                    IntField("T2", 0),
                    PacketListField("iapdopt", [], DHCP6OptIAPrefix,
                                    length_from = lambda pkt: pkt.optlen-12) ]

class DHCP6OptNISServers(_DHCP6OptGuessPayload):                 #RFC3898
    name = "DHCP6 Option - NIS Servers"
    fields_desc = [ ShortEnumField("optcode", 27, dhcp6opts),
                    FieldLenField("optlen", None, length_of="nisservers"),
                    IP6ListField("nisservers", [],
                                 length_from = lambda pkt: pkt.optlen) ]

class DHCP6OptNISPServers(_DHCP6OptGuessPayload):                #RFC3898
    name = "DHCP6 Option - NIS+ Servers"
    fields_desc = [ ShortEnumField("optcode", 28, dhcp6opts),
                    FieldLenField("optlen", None, length_of="nispservers"),
                    IP6ListField("nispservers", [],
                                 length_from = lambda pkt: pkt.optlen) ]

class DomainNameField(StrLenField):
    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        return s[l:], self.m2i(pkt,s[:l])

    def i2len(self, pkt, x):
        return len(self.i2m(pkt, x))

    def m2i(self, pkt, x):
        save = x
        cur = []
        while x and x[0] != '\x00':
            l = ord(x[0])
            cur.append(x[1:1+l])
            x = x[l+1:]
        if x[0] != '\x00':
            print "Found weird domain: '%s'. Keeping %s" % (save, x)
        return ".".join(cur)

    def i2m(self, pkt, x):
        def conditionalTrailingDot(z):
            if (z and z[-1] == '\x00'):
                return z
            return z+'\x00'
        if not x:
            return ""
        tmp = "".join(map(lambda z: chr(len(z))+z, x.split('.')))
        return conditionalTrailingDot(tmp)

class DHCP6OptNISDomain(_DHCP6OptGuessPayload):             #RFC3898
    name = "DHCP6 Option - NIS Domain Name"
    fields_desc = [ ShortEnumField("optcode", 29, dhcp6opts),
                    FieldLenField("optlen", None, length_of="nisdomain"),
                    DomainNameField("nisdomain", "",
                                    length_from = lambda pkt: pkt.optlen) ]

class DHCP6OptNISPDomain(_DHCP6OptGuessPayload):            #RFC3898
    name = "DHCP6 Option - NIS+ Domain Name"
    fields_desc = [ ShortEnumField("optcode", 30, dhcp6opts),
                    FieldLenField("optlen", None, length_of="nispdomain"),
                    DomainNameField("nispdomain", "",
                                    length_from= lambda pkt: pkt.optlen) ]

class DHCP6OptSNTPServers(_DHCP6OptGuessPayload):                #RFC4075
    name = "DHCP6 option - SNTP Servers"
    fields_desc = [ ShortEnumField("optcode", 31, dhcp6opts),
                    FieldLenField("optlen", None, length_of="sntpservers"),
                    IP6ListField("sntpservers", [],
                                 length_from = lambda pkt: pkt.optlen) ]

IRT_DEFAULT=86400
IRT_MINIMUM=600
class DHCP6OptInfoRefreshTime(_DHCP6OptGuessPayload):    #RFC4242
    name = "DHCP6 Option - Information Refresh Time"
    fields_desc = [ ShortEnumField("optcode", 32, dhcp6opts),
                    ShortField("optlen", 4),
                    IntField("reftime", IRT_DEFAULT)] # One day

class DHCP6OptBCMCSDomains(_DHCP6OptGuessPayload):              #RFC4280         
    name = "DHCP6 Option - BCMCS Domain Name List"
    fields_desc = [ ShortEnumField("optcode", 33, dhcp6opts),
                    FieldLenField("optlen", None, length_of="bcmcsdomains"),
                    DomainNameListField("bcmcsdomains", [],
                                        length_from = lambda pkt: pkt.optlen) ]

class DHCP6OptBCMCSServers(_DHCP6OptGuessPayload):              #RFC4280
    name = "DHCP6 Option - BCMCS Addresses List"
    fields_desc = [ ShortEnumField("optcode", 34, dhcp6opts),
                    FieldLenField("optlen", None, length_of="bcmcsservers"),
                    IP6ListField("bcmcsservers", [],
                                 length_from= lambda pkt: pkt.optlen) ]

# TODO : Does Nothing at the moment
class DHCP6OptGeoConf(_DHCP6OptGuessPayload):               #RFC-ietf-geopriv-dhcp-civil-09.txt
    name = ""
    fields_desc = [ ShortEnumField("optcode", 36, dhcp6opts),
                    FieldLenField("optlen", None, length_of="optdata"),
                    StrLenField("optdata", "",
                                length_from = lambda pkt: pkt.optlen) ]

# TODO: see if we encounter opaque values from vendor devices
class DHCP6OptRemoteID(_DHCP6OptGuessPayload):                   #RFC4649
    name = "DHCP6 Option - Relay Agent Remote-ID"
    fields_desc = [ ShortEnumField("optcode", 37, dhcp6opts),
                    FieldLenField("optlen", None, length_of="remoteid",
                                  adjust = lambda pkt,x: x+4),
                    IntEnumField("enterprisenum", None, iana_enterprise_num),
                    StrLenField("remoteid", "",
                                length_from = lambda pkt: pkt.optlen-4) ]

# TODO : 'subscriberid' default value should be at least 1 byte long
class DHCP6OptSubscriberID(_DHCP6OptGuessPayload):               #RFC4580
    name = "DHCP6 Option - Subscriber ID"
    fields_desc = [ ShortEnumField("optcode", 38, dhcp6opts),
                    FieldLenField("optlen", None, length_of="subscriberid"),
                    StrLenField("subscriberid", "",
                                length_from = lambda pkt: pkt.optlen) ]

# TODO :  "The data in the Domain Name field MUST be encoded
#          as described in Section 8 of [5]"
class DHCP6OptClientFQDN(_DHCP6OptGuessPayload):                 #RFC4704
    name = "DHCP6 Option - Client FQDN"
    fields_desc = [ ShortEnumField("optcode", 39, dhcp6opts),
                    FieldLenField("optlen", None, length_of="fqdn",
                                  adjust = lambda pkt,x: x+1),
                    BitField("res", 0, 5),
                    FlagsField("flags", 0, 3, "SON" ),
                    DomainNameField("fqdn", "",
                                    length_from = lambda pkt: pkt.optlen-1) ]

class DHCP6OptRelayAgentERO(_DHCP6OptGuessPayload):       # RFC4994
    name = "DHCP6 Option - RelayRequest Option"
    fields_desc = [ ShortEnumField("optcode", 43, dhcp6opts),
                    FieldLenField("optlen", None, length_of="reqopts", fmt="!H"),
                    _OptReqListField("reqopts", [23, 24],
                                     length_from = lambda pkt: pkt.optlen) ]

#####################################################################
###                        DHCPv6 messages                        ###
#####################################################################

# Some state parameters of the protocols that should probably be 
# useful to have in the configuration (and keep up-to-date)
DHCP6RelayAgentUnicastAddr=""
DHCP6RelayHopCount=""
DHCP6ServerUnicastAddr=""
DHCP6ClientUnicastAddr=""
DHCP6ClientIA_TA=""
DHCP6ClientIA_NA=""
DHCP6ClientIAID=""
T1="" # Voir 2462
T2="" # Voir 2462
DHCP6ServerDUID=""
DHCP6CurrentTransactionID="" # devrait etre utilise pour matcher une
# reponse et mis a jour en mode client par une valeur aleatoire pour
# laquelle on attend un retour de la part d'un serveur.
DHCP6PrefVal="" # la valeur de preference a utiliser dans
# les options preference

# Emitted by :
# - server : ADVERTISE, REPLY, RECONFIGURE, RELAY-REPL (vers relay)
# - client : SOLICIT, REQUEST, CONFIRM, RENEW, REBIND, RELEASE, DECLINE,
#            INFORMATION REQUEST
# - relay  : RELAY-FORW (toward server)

class _DHCP6GuessPayload(Packet):
    def guess_payload_class(self, payload):
        if len(payload) > 1 :
            print ord(payload[0])
            return get_cls(dhcp6opts.get(ord(payload[0]),"DHCP6OptUnknown"), Raw)
        return Raw

#####################################################################
## DHCPv6 messages sent between Clients and Servers (types 1 to 11)
# Comme specifie en section 15.1 de la RFC 3315, les valeurs de
# transaction id sont selectionnees de maniere aleatoire par le client
# a chaque emission et doivent matcher dans les reponses faites par
# les clients
class DHCP6(_DHCP6OptGuessPayload):
    name = "DHCPv6 Generic Message)"
    fields_desc = [ ByteEnumField("msgtype",None,dhcp6types),
                    X3BytesField("trid",0x000000) ]
    overload_fields = { UDP: {"sport": 546, "dport": 547} }

    def hashret(self):
        return struct.pack("!I", self.trid)[1:4]

#####################################################################
# Solicit Message : sect 17.1.1 RFC3315
# - sent by client
# - must include a client identifier option
# - the client may include IA options for any IAs to which it wants the
#   server to assign address
# - The client use IA_NA options to request the assignment of
#   non-temporary addresses and uses IA_TA options to request the
#   assignment of temporary addresses
# - The client should include an Option Request option to indicate the
#   options the client is interested in receiving (eventually
#   including hints)
# - The client includes a Reconfigure Accept option if is willing to
#   accept Reconfigure messages from the server.
# Le cas du send and reply est assez particulier car suivant la
# presence d'une option rapid commit dans le solicit, l'attente
# s'arrete au premier message de reponse recu ou alors apres un
# timeout. De la meme maniere, si un message Advertise arrive avec une
# valeur de preference de 255, il arrete l'attente et envoie une
# Request.
# - The client announces its intention to use DHCP authentication by
# including an Authentication option in its solicit message. The
# server selects a key for the client based on the client's DUID. The
# client and server use that key to authenticate all DHCP messages
# exchanged during the session

class DHCP6_Solicit(DHCP6):
    name = "DHCPv6 Solicit Message"
    msgtype = 1
    overload_fields = { UDP: {"sport": 546, "dport": 547} }

#####################################################################
# Advertise Message
# - sent by server
# - Includes a server identifier option
# - Includes a client identifier option
# - the client identifier option must match the client's DUID
# - transaction ID must match

class DHCP6_Advertise(DHCP6):
    name = "DHCPv6 Advertise Message"
    msgtype = 2
    overload_fields = { UDP: {"sport": 547, "dport": 546} }
    
    def answers(self, other):
        return (isinstance(other,DHCP6_Solicit) and 
                other.msgtype == 1 and
                self.trid == other.trid)

#####################################################################
# Request Message
# - sent by clients
# - includes a server identifier option
# - the content of Server Identifier option must match server's DUID
# - includes a client identifier option
# - must include an ORO Option (even with hints) p40
# - can includes a reconfigure Accept option indicating whether or
#   not the client is willing to accept Reconfigure messages from
#   the server (p40)
# - When the server receives a Request message via unicast from a
# client to which the server has not sent a unicast option, the server
# discards the Request message and responds with a Reply message
# containinig Status Code option with the value UseMulticast, a Server
# Identifier Option containing the server's DUID, the client
# Identifier option from the client message and no other option.

class DHCP6_Request(DHCP6):
    name = "DHCPv6 Request Message"
    msgtype = 3

#####################################################################
# Confirm Message
# - sent by clients
# - must include a clien identifier option
# - When the server receives a Confirm Message, the server determines
# whether the addresses in the Confirm message are appropriate for the
# link to which the client is attached. cf p50

class DHCP6_Confirm(DHCP6):
    name = "DHCPv6 Confirm Message"
    msgtype = 4
    
#####################################################################
# Renew Message
# - sent by clients
# - must include a server identifier option
# - content of server identifier option must match the server's identifier
# - must include a client identifier option
# - the clients includes any IA assigned to the interface that may
# have moved to a new link, along with the addresses associated with
# those IAs in its confirm messages
# - When the server receives a Renew message that contains an IA
# option from a client, it locates the client's binding and verifies
# that the information in the IA from the client matches the
# information for that client. If the server cannot find a client
# entry for the IA the server returns the IA containing no addresses
# with a status code option est to NoBinding in the Reply message. cf
# p51 pour le reste.

class DHCP6_Renew(DHCP6):
    name = "DHCPv6 Renew Message"
    msgtype = 5
    
#####################################################################
# Rebind Message
# - sent by clients
# - must include a client identifier option
# cf p52

class DHCP6_Rebind(DHCP6):
    name = "DHCPv6 Rebind Message"
    msgtype = 6
    
#####################################################################
# Reply Message
# - sent by servers
# - the message must include a server identifier option
# - transaction-id field must match the value of original message
# The server includes a Rapid Commit option in the Reply message to
# indicate that the reply is in response to a solicit message
# - if the client receives a reply message with a Status code option
# with the value UseMulticast, the client records the receipt of the
# message and sends subsequent messages to the server through the
# interface on which the message was received using multicast. The
# client resends the original message using multicast
# - When the client receives a NotOnLink status from the server in
# response to a Confirm message, the client performs DHCP server
# solicitation as described in section 17 and client-initiated
# configuration as descrribed in section 18 (RFC 3315)
# - when the client receives a NotOnLink status from the server in
# response to a Request, the client can either re-issue the Request
# without specifying any addresses or restart the DHCP server
# discovery process.
# - the server must include a server identifier option containing the
# server's DUID in the Reply message

class DHCP6_Reply(DHCP6):
    name = "DHCPv6 Reply Message"
    msgtype = 7
    
    def answers(self, other):
        return (isinstance(other, DHCP6_InfoRequest) and
                self.trid == other.trid)

#####################################################################
# Release Message
# - sent by clients
# - must include a server identifier option
# cf p53

class DHCP6_Release(DHCP6):
    name = "DHCPv6 Release Message"
    msgtype = 8
    
#####################################################################
# Decline Message
# - sent by clients
# - must include a client identifier option
# - Server identifier option must match server identifier
# - The addresses to be declined must be included in the IAs. Any
# addresses for the IAs the client wishes to continue to use should
# not be in added to the IAs.
# - cf p54 

class DHCP6_Decline(DHCP6):
    name = "DHCPv6 Decline Message"
    msgtype = 9
    
#####################################################################
# Reconfigure Message
# - sent by servers
# - must be unicast to the client
# - must include a server identifier option
# - must include a client identifier option that contains the client DUID
# - must contain a Reconfigure Message Option and the message type
#   must be a valid value
# - the server sets the transaction-id to 0
# - The server must use DHCP Authentication in the Reconfigure
# message. Autant dire que ca va pas etre le type de message qu'on va
# voir le plus souvent.

class DHCP6_Reconf(DHCP6):
    name = "DHCPv6 Reconfigure Message"
    msgtype = 10
    overload_fields = { UDP: { "sport": 547, "dport": 546 } }

    
#####################################################################
# Information-Request Message
# - sent by clients when needs configuration information but no
# addresses. 
# - client should include a client identifier option to identify
# itself. If it doesn't the server is not able to return client
# specific options or the server can choose to not respond to the
# message at all. The client must include a client identifier option
# if the message will be authenticated.
# - client must include an ORO of option she's interested in receiving
# (can include hints)

class DHCP6_InfoRequest(DHCP6):
    name = "DHCPv6 Information Request Message"    
    msgtype = 11 
    
    def hashret(self): 
        return struct.pack("!I", self.trid)[1:3]

#####################################################################
# sent between Relay Agents and Servers 
#
# Normalement, doit inclure une option "Relay Message Option"
# peut en inclure d'autres.
# voir section 7.1 de la 3315

# Relay-Forward Message
# - sent by relay agents to servers
# If the relay agent relays messages to the All_DHCP_Servers multicast
# address or other multicast addresses, it sets the Hop Limit field to
# 32. 

class DHCP6_RelayForward(_DHCP6GuessPayload,Packet):
    name = "DHCPv6 Relay Forward Message (Relay Agent/Server Message)"
    fields_desc = [ ByteEnumField("msgtype", 12, dhcp6types),
                    ByteField("hopcount", None),
                    IP6Field("linkaddr", "::"),
                    IP6Field("peeraddr", "::") ]
    def hashret(self): # we filter on peer address field
        return inet_pton(socket.AF_INET6, self.peeraddr)

#####################################################################
# sent between Relay Agents and Servers 
# Normalement, doit inclure une option "Relay Message Option"
# peut en inclure d'autres.
# Les valeurs des champs hop-count, link-addr et peer-addr
# sont copiees du messsage Forward associe. POur le suivi de session.
# Pour le moment, comme decrit dans le commentaire, le hashret
# se limite au contenu du champ peer address.
# Voir section 7.2 de la 3315.

# Relay-Reply Message
# - sent by servers to relay agents
# - if the solicit message was received in a Relay-Forward message,
# the server constructs a relay-reply message with the Advertise
# message in the payload of a relay-message. cf page 37/101. Envoie de
# ce message en unicast au relay-agent. utilisation de l'adresse ip
# presente en ip source du paquet recu

class DHCP6_RelayReply(DHCP6_RelayForward):
    name = "DHCPv6 Relay Reply Message (Relay Agent/Server Message)"
    msgtype = 13
    def hashret(self): # We filter on peer address field.
        return inet_pton(socket.AF_INET6, self.peeraddr)
    def answers(self, other):
        return (isinstance(other, DHCP6_RelayForward) and
                self.count == other.count and
                self.linkaddr == other.linkaddr and
                self.peeraddr == other.peeraddr )


dhcp6_cls_by_type = {  1: "DHCP6_Solicit",
                       2: "DHCP6_Advertise",
                       3: "DHCP6_Request",
                       4: "DHCP6_Confirm",
                       5: "DHCP6_Renew",
                       6: "DHCP6_Rebind",
                       7: "DHCP6_Reply",
                       8: "DHCP6_Release",
                       9: "DHCP6_Decline",
                      10: "DHCP6_Reconf",
                      11: "DHCP6_InfoRequest",
                      12: "DHCP6_RelayForward",
                      13: "DHCP6_RelayReply" }

def _dhcp6_dispatcher(x, *args, **kargs):
    cls = Raw
    if len(x) >= 2:
        cls = get_cls(dhcp6_cls_by_type.get(ord(x[0]), "Raw"), Raw)
    return cls(x, *args, **kargs)

bind_bottom_up(UDP, _dhcp6_dispatcher, { "dport": 547 } )
bind_bottom_up(UDP, _dhcp6_dispatcher, { "dport": 546 } )



class DHCPv6_am(AnsweringMachine):
    function_name = "dhcp6d"
    filter = "udp and port 546 and port 547" 
    send_function = staticmethod(send)
    def usage(self):
        msg = """
dhcp6d( dns="2001:500::1035", domain="localdomain, local", duid=None)
        iface=conf.iface6, advpref=255, sntpservers=None, 
        sipdomains=None, sipservers=None, 
        nisdomain=None, nisservers=None, 
        nispdomain=None, nispservers=None,
        bcmcsdomain=None, bcmcsservers=None)

   debug : When set, additional debugging information is printed. 

   duid   : some DUID class (DUID_LLT, DUID_LL or DUID_EN). If none
            is provided a DUID_LLT is constructed based on the MAC 
            address of the sending interface and launch time of dhcp6d 
            answering machine. 
  
   iface : the interface to listen/reply on if you do not want to use 
           conf.iface6.

   advpref : Value in [0,255] given to Advertise preference field.
             By default, 255 is used. Be aware that this specific
             value makes clients stops waiting for further Advertise
             messages from other servers.

   dns : list of recursive DNS servers addresses (as a string or list). 
         By default, it is set empty and the associated DHCP6OptDNSServers
         option is inactive. See RFC 3646 for details.
   domain : a list of DNS search domain (as a string or list). By default, 
         it is empty and the associated DHCP6OptDomains option is inactive.
         See RFC 3646 for details.

   sntpservers : a list of SNTP servers IPv6 addresses. By default,
         it is empty and the associated DHCP6OptSNTPServers option 
         is inactive. 

   sipdomains : a list of SIP domains. By default, it is empty and the
         associated DHCP6OptSIPDomains option is inactive. See RFC 3319
         for details.
   sipservers : a list of SIP servers IPv6 addresses. By default, it is 
         empty and the associated DHCP6OptSIPDomains option is inactive. 
         See RFC 3319 for details.

   nisdomain : a list of NIS domains. By default, it is empty and the
         associated DHCP6OptNISDomains option is inactive. See RFC 3898
         for details. See RFC 3646 for details.
   nisservers : a list of NIS servers IPv6 addresses. By default, it is 
         empty and the associated DHCP6OptNISServers option is inactive.
         See RFC 3646 for details.

   nispdomain : a list of NIS+ domains. By default, it is empty and the
         associated DHCP6OptNISPDomains option is inactive. See RFC 3898
         for details.
   nispservers : a list of NIS+ servers IPv6 addresses. By default, it is 
         empty and the associated DHCP6OptNISServers option is inactive.
         See RFC 3898 for details.

   bcmcsdomain : a list of BCMCS domains. By default, it is empty and the
         associated DHCP6OptBCMCSDomains option is inactive. See RFC 4280
         for details.
   bcmcsservers : a list of BCMCS servers IPv6 addresses. By default, it is 
         empty and the associated DHCP6OptBCMCSServers option is inactive.
         See RFC 4280 for details.

   If you have a need for others, just ask ... or provide a patch."""
        print msg

    def parse_options(self, dns="2001:500::1035", domain="localdomain, local",
                      startip="2001:db8::1", endip="2001:db8::20", duid=None,
                      sntpservers=None, sipdomains=None, sipservers=None, 
                      nisdomain=None, nisservers=None, nispdomain=None,
                      nispservers=None, bcmcsservers=None, bcmcsdomains=None,
                      iface=None, debug=0, advpref=255):
        def norm_list(val, param_name):
            if val is None:
                return None
            if type(val) is list:
                return val
            elif type(val) is str:
                l = val.split(',')
                return map(lambda x: x.strip(), l)
            else:
                print "Bad '%s' parameter provided." % param_name
                self.usage()
                return -1

        if iface is None:
            iface = conf.iface6
        
        self.debug = debug

        # Dictionary of provided DHCPv6 options, keyed by option type
        self.dhcpv6_options={}

        for o in [(dns, "dns", 23, lambda x: DHCP6OptDNSServers(dnsservers=x)), 
                  (domain, "domain", 24, lambda x: DHCP6OptDNSDomains(dnsdomains=x)), 
                  (sntpservers, "sntpservers", 31, lambda x: DHCP6OptSNTPServers(sntpservers=x)),
                  (sipservers, "sipservers", 22, lambda x: DHCP6OptSIPServers(sipservers=x)),
                  (sipdomains, "sipdomains", 21, lambda x: DHCP6OptSIPDomains(sipdomains=x)),
                  (nisservers, "nisservers", 27, lambda x: DHCP6OptNISServers(nisservers=x)),
                  (nisdomain, "nisdomain", 29, lambda x: DHCP6OptNISDomain(nisdomain=(x+[""])[0])),
                  (nispservers, "nispservers", 28, lambda x: DHCP6OptNISPServers(nispservers=x)), 
                  (nispdomain, "nispdomain", 30, lambda x: DHCP6OptNISPDomain(nispdomain=(x+[""])[0])),
                  (bcmcsservers, "bcmcsservers", 33, lambda x: DHCP6OptBCMCSServers(bcmcsservers=x)),
                  (bcmcsdomains, "bcmcsdomains", 34, lambda x: DHCP6OptBCMCSDomains(bcmcsdomains=x))]:

            opt = norm_list(o[0], o[1])
            if opt == -1: # Usage() was triggered
                return False
            elif opt is None: # We won't return that option
                pass
            else:
                self.dhcpv6_options[o[2]] = o[3](opt)

        if self.debug:
            print "\n[+] List of active DHCPv6 options:"
            opts = self.dhcpv6_options.keys()
            opts.sort()
            for i in opts:
                print "    %d: %s" % (i, repr(self.dhcpv6_options[i]))

        # Preference value used in Advertise. 
        self.advpref = advpref

        # IP Pool
        self.startip = startip
        self.endip   = endip
        # XXX TODO Check IPs are in same subnet

        ####
        # The interface we are listening/replying on
        self.iface = iface

        ####        
        # Generate a server DUID
        if duid is not None:
            self.duid = duid
        else:
            # Timeval
            from time import gmtime, strftime, mktime
            epoch = (2000, 1, 1, 0, 0, 0, 5, 1, 0)
            delta = mktime(epoch) - mktime(gmtime(0))
            timeval = time.time() - delta

            # Mac Address
            rawmac = get_if_raw_hwaddr(iface)[1]
            mac = ":".join(map(lambda x: "%.02x" % ord(x), list(rawmac)))

            self.duid = DUID_LLT(timeval = timeval, lladdr = mac)
            
        if self.debug:
            print "\n[+] Our server DUID:" 
            self.duid.show(label_lvl=" "*4)

        ####
        # Find the source address we will use
        l = filter(lambda x: x[2] == iface and in6_islladdr(x[0]), 
                   in6_getifaddr())
        if not l:
            warning("Unable to get a Link-Local address")
            return 
        
        self.src_addr = l[0][0]

        ####
        # Our leases
        self.leases = {}
        

        if self.debug:
            print "\n[+] Starting DHCPv6 service on %s:" % self.iface 

    def is_request(self, p):
        if not IPv6 in p:
            return False

        src = p[IPv6].src
        dst = p[IPv6].dst

        p = p[IPv6].payload 
        if not isinstance(p, UDP) or p.sport != 546 or p.dport != 547 :
            return False

        p = p.payload
        if not isinstance(p, DHCP6):
            return False

        # Message we considered client messages :
        # Solicit (1), Request (3), Confirm (4), Renew (5), Rebind (6)
        # Decline (9), Release (8), Information-request (11),
        if not (p.msgtype in [1, 3, 4, 5, 6, 8, 9, 11]):
            return False

        # Message validation following section 15 of RFC 3315

        if ((p.msgtype == 1) or # Solicit 
            (p.msgtype == 6) or # Rebind
            (p.msgtype == 4)):  # Confirm
            if ((not DHCP6OptClientId in p) or
                DHCP6OptServerId in p):
                return False

            if (p.msgtype == 6 or # Rebind
                p.msgtype == 4):  # Confirm   
                # XXX We do not reply to Confirm or Rebind as we 
                # XXX do not support address assignment            
                return False

        elif (p.msgtype == 3 or # Request
              p.msgtype == 5 or # Renew
              p.msgtype == 8):  # Release
        
            # Both options must be present
            if ((not DHCP6OptServerId in p) or
                (not DHCP6OptClientId in p)):
                return False
            # provided server DUID must match ours
            duid = p[DHCP6OptServerId].duid
            if (type(duid) != type(self.duid)):
                return False
            if str(duid) != str(self.duid):
                return False

            if (p.msgtype == 5 or # Renew
                p.msgtype == 8):  # Release
                # XXX We do not reply to Renew or Release as we 
                # XXX do not support address assignment            
                return False

        elif p.msgtype == 9: # Decline
            # XXX We should check if we are tracking that client
            if not self.debug:
                return False

            bo = Color.bold
            g = Color.green + bo
            b = Color.blue + bo
            n = Color.normal
            r = Color.red

            vendor  = in6_addrtovendor(src)
            if (vendor and vendor != "UNKNOWN"):
                vendor = " [" + b + vendor + n + "]"
            else:
                vendor = ""
            src  = bo + src + n

            it = p
            addrs = []
            while it:
                l = []
                if isinstance(it, DHCP6OptIA_NA):
                    l = it.ianaopts
                elif isinstance(it, DHCP6OptIA_TA):
                    l = it.iataopts

                opsaddr = filter(lambda x: isinstance(x, DHCP6OptIAAddress),l)
                a=map(lambda x: x.addr,  opsaddr)
                addrs += a
                it = it.payload
                    
            addrs = map(lambda x: bo + x + n, addrs)
            if debug:
                msg = r + "[DEBUG]" + n + " Received " + g + "Decline" + n 
                msg += " from " + bo + src + vendor + " for "
                msg += ", ".join(addrs)+ n
                print msg

            # See sect 18.1.7

            # Sent by a client to warn us she has determined
            # one or more addresses assigned to her is already
            # used on the link.
            # We should simply log that fact. No messaged should
            # be sent in return.

            # - Message must include a Server identifier option
            # - the content of the Server identifier option must 
            #   match the server's identifier
            # - the message must include a Client Identifier option
            return False

        elif p.msgtype == 11: # Information-Request
            if DHCP6OptServerId in p:
                duid = p[DHCP6OptServerId].duid
                if (type(duid) != type(self.duid)):
                    return False
                if str(duid) != str(self.duid):
                    return False
            if ((DHCP6OptIA_NA in p) or 
                (DHCP6OptIA_TA in p) or
                (DHCP6OptIA_PD in p)):
                    return False
        else:
            return False

        return True

    def print_reply(self, req, reply):
        def norm(s):
            if s.startswith("DHCPv6 "):
                s = s[7:]
            if s.endswith(" Message"):
                s = s[:-8]
            return s
        
        if reply is None:
            return

        bo = Color.bold
        g = Color.green + bo
        b = Color.blue + bo
        n = Color.normal
        reqtype = g + norm(req.getlayer(UDP).payload.name) + n
        reqsrc  = req.getlayer(IPv6).src
        vendor  = in6_addrtovendor(reqsrc)
        if (vendor and vendor != "UNKNOWN"):
            vendor = " [" + b + vendor + n + "]"
        else:
            vendor = ""
        reqsrc  = bo + reqsrc + n
        reptype = g + norm(reply.getlayer(UDP).payload.name) + n

        print "Sent %s answering to %s from %s%s" % (reptype, reqtype, reqsrc, vendor)

    def make_reply(self, req):
        req_mac_src = req.src
        req_mac_dst = req.dst

        p = req[IPv6]
        req_src = p.src
        req_dst = p.dst

        p = p.payload.payload

        msgtype = p.msgtype
        trid = p.trid

        if msgtype == 1: # SOLICIT (See Sect 17.1 and 17.2 of RFC 3315)
            
            # XXX We don't support address or prefix assignment
            # XXX We also do not support relay function           --arno

            client_duid = p[DHCP6OptClientId].duid
            resp  = IPv6(src=self.src_addr, dst=req_src)
            resp /= UDP(sport=547, dport=546)
            
            if p.haslayer(DHCP6OptRapidCommit):
                # construct a Reply packet 
                resp /= DHCP6_Reply(trid=trid)
                resp /= DHCP6OptRapidCommit() # See 17.1.2
                resp /= DHCP6OptServerId(duid = self.duid)
                resp /= DHCP6OptClientId(duid = client_duid)
                
            else: # No Rapid Commit in the packet. Reply with an Advertise                
                
                if (p.haslayer(DHCP6OptIA_NA) or
                    p.haslayer(DHCP6OptIA_TA)):
                    # XXX We don't assign addresses at the moment
                    msg = "Scapy6 dhcp6d does not support address assignment"
                    resp /= DHCP6_Advertise(trid = trid)
                    resp /= DHCP6OptStatusCode(statuscode=2, statusmsg=msg)
                    resp /= DHCP6OptServerId(duid = self.duid)
                    resp /= DHCP6OptClientId(duid = client_duid)                  

                elif p.haslayer(DHCP6OptIA_PD):
                    # XXX We don't assign prefixes at the moment
                    msg = "Scapy6 dhcp6d does not support prefix assignment"
                    resp /= DHCP6_Advertise(trid = trid)
                    resp /= DHCP6OptStatusCode(statuscode=6, statusmsg=msg)
                    resp /= DHCP6OptServerId(duid = self.duid)
                    resp /= DHCP6OptClientId(duid = client_duid)                  

                else: # Usual case, no request for prefixes or addresse
                    resp /= DHCP6_Advertise(trid = trid)
                    resp /= DHCP6OptPref(prefval = self.advpref)
                    resp /= DHCP6OptServerId(duid = self.duid)
                    resp /= DHCP6OptClientId(duid = client_duid)
                    resp /= DHCP6OptReconfAccept()
                    
                    # See which options should be included
                    reqopts = []
                    if p.haslayer(DHCP6OptOptReq): # add only asked ones
                        reqopts = p[DHCP6OptOptReq].reqopts
                        for o in self.dhcpv6_options.keys():
                            if o in reqopts:
                                resp /= self.dhcpv6_options[o]
                    else: # advertise everything we have available
                        for o in self.dhcpv6_options.keys():
                            resp /= self.dhcpv6_options[o]                    

            return resp

        elif msgtype == 3: #REQUEST (INFO-REQUEST is further below)
            client_duid = p[DHCP6OptClientId].duid
            resp  = IPv6(src=self.src_addr, dst=req_src)
            resp /= UDP(sport=547, dport=546)
            resp /= DHCP6_Solicit(trid=trid)
            resp /= DHCP6OptServerId(duid = self.duid)
            resp /= DHCP6OptClientId(duid = client_duid)

            # See which options should be included
            reqopts = []
            if p.haslayer(DHCP6OptOptReq): # add only asked ones
                reqopts = p[DHCP6OptOptReq].reqopts
                for o in self.dhcpv6_options.keys():
                    if o in reqopts:
                        resp /= self.dhcpv6_options[o]
            else: 
                # advertise everything we have available.
                # Should not happen has clients MUST include 
                # and ORO in requests (sec 18.1.1)   -- arno
                for o in self.dhcpv6_options.keys():
                    resp /= self.dhcpv6_options[o]          

            return resp            
        
        elif msgtype == 4: # CONFIRM
            # see Sect 18.1.2
            
            # Client want to check if addresses it was assigned
            # are still appropriate

            # Server must discard any Confirm messages that
            # do not include a Client Identifier option OR
            # THAT DO INCLUDE a Server Identifier Option

            # XXX we must discard the SOLICIT if it is received with
            #     a unicast destination address

            pass

        elif msgtype == 5: # RENEW
            # see Sect 18.1.3
            
            # Clients want to extend lifetime of assigned addresses
            # and update configuration parameters. This message is sent
            # specifically to the server that provided her the info

            # - Received message must include a Server Identifier
            #   option.
            # - the content of server identifier option must match
            #   the server's identifier.
            # - the message must include a Client identifier option

            pass
        
        elif msgtype == 6: # REBIND
            # see Sect 18.1.4
            
            # Same purpose as the Renew message but sent to any
            # available server after he received no response
            # to its previous Renew message.

            
            # - Message must include a Client Identifier Option
            # - Message can't include a Server identifier option

            # XXX we must discard the SOLICIT if it is received with
            #     a unicast destination address

            pass

        elif msgtype == 8: # RELEASE
            # See section 18.1.6

            # Message is sent to the server to indicate that 
            # she will no longer use the addresses that was assigned
            # We should parse the message and verify our dictionary
            # to log that fact.


            # - The message must include a server identifier option
            # - The content of the Server Identifier option must
            #   match the server's identifier
            # - the message must include a Client Identifier option

            pass

        elif msgtype == 9: # DECLINE
            # See section 18.1.7            
            pass

        elif msgtype == 11: # INFO-REQUEST
            client_duid = None
            if not p.haslayer(DHCP6OptClientId):
                if self.debug:
                    warning("Received Info Request message without Client Id option")
            else:
                client_duid = p[DHCP6OptClientId].duid

            resp  = IPv6(src=self.src_addr, dst=req_src)
            resp /= UDP(sport=547, dport=546)
            resp /= DHCP6_Reply(trid=trid)
            resp /= DHCP6OptServerId(duid = self.duid)

            if client_duid:
                resp /= DHCP6OptClientId(duid = client_duid)
                
            # Stack requested options if available
            reqopts = []
            if p.haslayer(DHCP6OptOptReq):
                reqopts = p[DHCP6OptOptReq].reqopts
            for o in self.dhcpv6_options.keys():
                resp /= self.dhcpv6_options[o]

            return resp

        else:
            # what else ?
            pass

        # - We won't support reemission
        # - We won't support relay role, nor relay forwarded messages
        #   at the beginning

########NEW FILE########
__FILENAME__ = dns
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
DNS: Domain Name System.
"""

import socket,struct

from scapy.packet import *
from scapy.fields import *
from scapy.ansmachine import *
from scapy.layers.inet import UDP

class DNSStrField(StrField):

    def h2i(self, pkt, x):
      if x == "":
        return "."
      return x

    def i2m(self, pkt, x):
        if x == ".":
          return "\x00"

        x = [k[:63] for k in x.split(".")] # Truncate chunks that cannot be encoded (more than 63 bytes..)
        x = map(lambda y: chr(len(y))+y, x)
        x = "".join(x)
        if x[-1] != "\x00":
            x += "\x00"
        return x

    def getfield(self, pkt, s):
        n = ""

        if ord(s[0]) == 0:
          return s[1:], "."

        while 1:
            l = ord(s[0])
            s = s[1:]
            if not l:
                break
            if l & 0xc0:
                raise Scapy_Exception("DNS message can't be compressed at this point!")
            else:
                n += s[:l]+"."
                s = s[l:]
        return s, n


class DNSRRCountField(ShortField):
    holds_packets=1
    def __init__(self, name, default, rr):
        ShortField.__init__(self, name, default)
        self.rr = rr
    def _countRR(self, pkt):
        x = getattr(pkt,self.rr)
        i = 0
        while isinstance(x, DNSRR) or isinstance(x, DNSQR):
            x = x.payload
            i += 1
        return i
        
    def i2m(self, pkt, x):
        if x is None:
            x = self._countRR(pkt)
        return x
    def i2h(self, pkt, x):
        if x is None:
            x = self._countRR(pkt)
        return x
    

def DNSgetstr(s,p):
    name = ""
    q = 0
    jpath = [p]
    while 1:
        if p >= len(s):
            warning("DNS RR prematured end (ofs=%i, len=%i)"%(p,len(s)))
            break
        l = ord(s[p])
        p += 1
        if l & 0xc0:
            if not q:
                q = p+1
            if p >= len(s):
                warning("DNS incomplete jump token at (ofs=%i)" % p)
                break
            p = ((l & 0x3f) << 8) + ord(s[p]) - 12
            if p in jpath:
                warning("DNS decompression loop detected")
                break
            jpath.append(p)
            continue
        elif l > 0:
            name += s[p:p+l]+"."
            p += l
            continue
        break
    if q:
        p = q
    return name,p
        

class DNSRRField(StrField):
    holds_packets=1
    def __init__(self, name, countfld, passon=1):
        StrField.__init__(self, name, None)
        self.countfld = countfld
        self.passon = passon
    def i2m(self, pkt, x):
        if x is None:
            return ""
        return str(x)
    def decodeRR(self, name, s, p):
        ret = s[p:p+10]
        type,cls,ttl,rdlen = struct.unpack("!HHIH", ret)
        p += 10
        rr = DNSRR("\x00"+ret+s[p:p+rdlen])
        if rr.type in [2, 3, 4, 5]:
            rr.rdata = DNSgetstr(s,p)[0]
        del(rr.rdlen)
        
        p += rdlen
        
        rr.rrname = name
        return rr,p
    def getfield(self, pkt, s):
        if type(s) is tuple :
            s,p = s
        else:
            p = 0
        ret = None
        c = getattr(pkt, self.countfld)
        if c > len(s):
            warning("wrong value: DNS.%s=%i" % (self.countfld,c))
            return s,""
        while c:
            c -= 1
            name,p = DNSgetstr(s,p)
            rr,p = self.decodeRR(name, s, p)
            if ret is None:
                ret = rr
            else:
                ret.add_payload(rr)
        if self.passon:
            return (s,p),ret
        else:
            return s[p:],ret
            
            
class DNSQRField(DNSRRField):
    holds_packets=1
    def decodeRR(self, name, s, p):
        ret = s[p:p+4]
        p += 4
        rr = DNSQR("\x00"+ret)
        rr.qname = name
        return rr,p
        
        

class RDataField(StrLenField):
    def m2i(self, pkt, s):
        family = None
        if pkt.type == 1:
            family = socket.AF_INET
        elif pkt.type == 28:
            family = socket.AF_INET6
        elif pkt.type == 12:
            s = DNSgetstr(s, 0)[0]
        if family is not None:    
            s = inet_ntop(family, s)
        return s
    def i2m(self, pkt, s):
        if pkt.type == 1:
            if s:
                s = inet_aton(s)
        elif pkt.type == 28:
            if s:
                s = inet_pton(socket.AF_INET6, s)
        elif pkt.type in [2,3,4,5]:
            s = "".join(map(lambda x: chr(len(x))+x, s.split(".")))
            if ord(s[-1]):
                s += "\x00"
        return s

class RDLenField(Field):
    def __init__(self, name):
        Field.__init__(self, name, None, "H")
    def i2m(self, pkt, x):
        if x is None:
            rdataf = pkt.get_field("rdata")
            x = len(rdataf.i2m(pkt, pkt.rdata))
        return x
    def i2h(self, pkt, x):
        if x is None:
            rdataf = pkt.get_field("rdata")
            x = len(rdataf.i2m(pkt, pkt.rdata))
        return x
    

class DNS(Packet):
    name = "DNS"
    fields_desc = [ ShortField("id",0),
                    BitField("qr",0, 1),
                    BitEnumField("opcode", 0, 4, {0:"QUERY",1:"IQUERY",2:"STATUS"}),
                    BitField("aa", 0, 1),
                    BitField("tc", 0, 1),
                    BitField("rd", 0, 1),
                    BitField("ra", 0 ,1),
                    BitField("z", 0, 3),
                    BitEnumField("rcode", 0, 4, {0:"ok", 1:"format-error", 2:"server-failure", 3:"name-error", 4:"not-implemented", 5:"refused"}),
                    DNSRRCountField("qdcount", None, "qd"),
                    DNSRRCountField("ancount", None, "an"),
                    DNSRRCountField("nscount", None, "ns"),
                    DNSRRCountField("arcount", None, "ar"),
                    DNSQRField("qd", "qdcount"),
                    DNSRRField("an", "ancount"),
                    DNSRRField("ns", "nscount"),
                    DNSRRField("ar", "arcount",0) ]
    def answers(self, other):
        return (isinstance(other, DNS)
                and self.id == other.id
                and self.qr == 1
                and other.qr == 0)
        
    def mysummary(self):
        type = ["Qry","Ans"][self.qr]
        name = ""
        if self.qr:
            type = "Ans"
            if self.ancount > 0 and isinstance(self.an, DNSRR):
                name = ' "%s"' % self.an.rdata
        else:
            type = "Qry"
            if self.qdcount > 0 and isinstance(self.qd, DNSQR):
                name = ' "%s"' % self.qd.qname
        return 'DNS %s%s ' % (type, name)

dnstypes = { 0:"ANY", 255:"ALL",
             1:"A", 2:"NS", 3:"MD", 4:"MD", 5:"CNAME", 6:"SOA", 7: "MB", 8:"MG",
             9:"MR",10:"NULL",11:"WKS",12:"PTR",13:"HINFO",14:"MINFO",15:"MX",16:"TXT",
             17:"RP",18:"AFSDB",28:"AAAA", 33:"SRV",38:"A6",39:"DNAME"}

dnsqtypes = {251:"IXFR",252:"AXFR",253:"MAILB",254:"MAILA",255:"ALL"}
dnsqtypes.update(dnstypes)
dnsclasses =  {1: 'IN',  2: 'CS',  3: 'CH',  4: 'HS',  255: 'ANY'}


class DNSQR(Packet):
    name = "DNS Question Record"
    show_indent=0
    fields_desc = [ DNSStrField("qname",""),
                    ShortEnumField("qtype", 1, dnsqtypes),
                    ShortEnumField("qclass", 1, dnsclasses) ]
                    
                    

class DNSRR(Packet):
    name = "DNS Resource Record"
    show_indent=0
    fields_desc = [ DNSStrField("rrname",""),
                    ShortEnumField("type", 1, dnstypes),
                    ShortEnumField("rclass", 1, dnsclasses),
                    IntField("ttl", 0),
                    RDLenField("rdlen"),
                    RDataField("rdata", "", length_from=lambda pkt:pkt.rdlen) ]

bind_layers( UDP,           DNS,           dport=53)
bind_layers( UDP,           DNS,           sport=53)


@conf.commands.register
def dyndns_add(nameserver, name, rdata, type="A", ttl=10):
    """Send a DNS add message to a nameserver for "name" to have a new "rdata"
dyndns_add(nameserver, name, rdata, type="A", ttl=10) -> result code (0=ok)

example: dyndns_add("ns1.toto.com", "dyn.toto.com", "127.0.0.1")
RFC2136
"""
    zone = name[name.find(".")+1:]
    r=sr1(IP(dst=nameserver)/UDP()/DNS(opcode=5,
                                       qd=[DNSQR(qname=zone, qtype="SOA")],
                                       ns=[DNSRR(rrname=name, type="A",
                                                 ttl=ttl, rdata=rdata)]),
          verbose=0, timeout=5)
    if r and r.haslayer(DNS):
        return r.getlayer(DNS).rcode
    else:
        return -1
    
    
    

@conf.commands.register
def dyndns_del(nameserver, name, type="ALL", ttl=10):
    """Send a DNS delete message to a nameserver for "name"
dyndns_del(nameserver, name, type="ANY", ttl=10) -> result code (0=ok)

example: dyndns_del("ns1.toto.com", "dyn.toto.com")
RFC2136
"""
    zone = name[name.find(".")+1:]
    r=sr1(IP(dst=nameserver)/UDP()/DNS(opcode=5,
                                       qd=[DNSQR(qname=zone, qtype="SOA")],
                                       ns=[DNSRR(rrname=name, type=type,
                                                 rclass="ANY", ttl=0, rdata="")]),
          verbose=0, timeout=5)
    if r and r.haslayer(DNS):
        return r.getlayer(DNS).rcode
    else:
        return -1
    

class DNS_am(AnsweringMachine):
    function_name="dns_spoof"
    filter = "udp port 53"

    def parse_options(self, joker="192.168.1.1", match=None):
        if match is None:
            self.match = {}
        else:
            self.match = match
        self.joker=joker

    def is_request(self, req):
        return req.haslayer(DNS) and req.getlayer(DNS).qr == 0
    
    def make_reply(self, req):
        ip = req.getlayer(IP)
        dns = req.getlayer(DNS)
        resp = IP(dst=ip.src, src=ip.dst)/UDP(dport=ip.sport,sport=ip.dport)
        rdata = self.match.get(dns.qd.qname, self.joker)
        resp /= DNS(id=dns.id, qr=1, qd=dns.qd,
                    an=DNSRR(rrname=dns.qd.qname, ttl=10, rdata=rdata))
        return resp



########NEW FILE########
__FILENAME__ = dot11
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Wireless LAN according to IEEE 802.11.
"""

import re,struct

from scapy.packet import *
from scapy.fields import *
from scapy.plist import PacketList
from scapy.layers.l2 import *


try:
    from Crypto.Cipher import ARC4
except ImportError:
    log_loading.info("Can't import python Crypto lib. Won't be able to decrypt WEP.")


### Fields

class Dot11AddrMACField(MACField):
    def is_applicable(self, pkt):
        return 1
    def addfield(self, pkt, s, val):
        if self.is_applicable(pkt):
            return MACField.addfield(self, pkt, s, val)
        else:
            return s        
    def getfield(self, pkt, s):
        if self.is_applicable(pkt):
            return MACField.getfield(self, pkt, s)
        else:
            return s,None

class Dot11Addr2MACField(Dot11AddrMACField):
    def is_applicable(self, pkt):
        if pkt.type == 1:
            return pkt.subtype in [ 0xb, 0xa, 0xe, 0xf] # RTS, PS-Poll, CF-End, CF-End+CF-Ack
        return 1

class Dot11Addr3MACField(Dot11AddrMACField):
    def is_applicable(self, pkt):
        if pkt.type in [0,2]:
            return 1
        return 0

class Dot11Addr4MACField(Dot11AddrMACField):
    def is_applicable(self, pkt):
        if pkt.type == 2:
            if pkt.FCfield & 0x3 == 0x3: # To-DS and From-DS are set
                return 1
        return 0
    

### Layers


class PrismHeader(Packet):
    """ iwpriv wlan0 monitor 3 """
    name = "Prism header"
    fields_desc = [ LEIntField("msgcode",68),
                    LEIntField("len",144),
                    StrFixedLenField("dev","",16),
                    LEIntField("hosttime_did",0),
                  LEShortField("hosttime_status",0),
                  LEShortField("hosttime_len",0),
                    LEIntField("hosttime",0),
                    LEIntField("mactime_did",0),
                  LEShortField("mactime_status",0),
                  LEShortField("mactime_len",0),
                    LEIntField("mactime",0),
                    LEIntField("channel_did",0),
                  LEShortField("channel_status",0),
                  LEShortField("channel_len",0),
                    LEIntField("channel",0),
                    LEIntField("rssi_did",0),
                  LEShortField("rssi_status",0),
                  LEShortField("rssi_len",0),
                    LEIntField("rssi",0),
                    LEIntField("sq_did",0),
                  LEShortField("sq_status",0),
                  LEShortField("sq_len",0),
                    LEIntField("sq",0),
                    LEIntField("signal_did",0),
                  LEShortField("signal_status",0),
                  LEShortField("signal_len",0),
              LESignedIntField("signal",0),
                    LEIntField("noise_did",0),
                  LEShortField("noise_status",0),
                  LEShortField("noise_len",0),
                    LEIntField("noise",0),
                    LEIntField("rate_did",0),
                  LEShortField("rate_status",0),
                  LEShortField("rate_len",0),
                    LEIntField("rate",0),
                    LEIntField("istx_did",0),
                  LEShortField("istx_status",0),
                  LEShortField("istx_len",0),
                    LEIntField("istx",0),
                    LEIntField("frmlen_did",0),
                  LEShortField("frmlen_status",0),
                  LEShortField("frmlen_len",0),
                    LEIntField("frmlen",0),
                    ]
    def answers(self, other):
        if isinstance(other, PrismHeader):
            return self.payload.answers(other.payload)
        else:
            return self.payload.answers(other)

class RadioTap(Packet):
    name = "RadioTap dummy"
    fields_desc = [ ByteField('version', 0),
                    ByteField('pad', 0),
                    FieldLenField('len', None, 'notdecoded', '<H', adjust=lambda pkt,x:x+8),
                    FlagsField('present', None, -32, ['TSFT','Flags','Rate','Channel','FHSS','dBm_AntSignal',
                                                     'dBm_AntNoise','Lock_Quality','TX_Attenuation','dB_TX_Attenuation',
                                                      'dBm_TX_Power', 'Antenna', 'dB_AntSignal', 'dB_AntNoise',
                                                     'b14', 'b15','b16','b17','b18','b19','b20','b21','b22','b23',
                                                     'b24','b25','b26','b27','b28','b29','b30','Ext']),
                    StrLenField('notdecoded', "", length_from= lambda pkt:pkt.len-8) ]



class Dot11SCField(LEShortField):
    def is_applicable(self, pkt):
        return pkt.type != 1 # control frame
    def addfield(self, pkt, s, val):
        if self.is_applicable(pkt):
            return LEShortField.addfield(self, pkt, s, val)
        else:
            return s
    def getfield(self, pkt, s):
        if self.is_applicable(pkt):
            return LEShortField.getfield(self, pkt, s)
        else:
            return s,None

class Dot11(Packet):
    name = "802.11"
    fields_desc = [
                    BitField("subtype", 0, 4),
                    BitEnumField("type", 0, 2, ["Management", "Control", "Data", "Reserved"]),
                    BitField("proto", 0, 2),
                    FlagsField("FCfield", 0, 8, ["to-DS", "from-DS", "MF", "retry", "pw-mgt", "MD", "wep", "order"]),
                    ShortField("ID",0),
                    MACField("addr1", ETHER_ANY),
                    Dot11Addr2MACField("addr2", ETHER_ANY),
                    Dot11Addr3MACField("addr3", ETHER_ANY),
                    Dot11SCField("SC", 0),
                    Dot11Addr4MACField("addr4", ETHER_ANY) 
                    ]
    def mysummary(self):
        return self.sprintf("802.11 %Dot11.type% %Dot11.subtype% %Dot11.addr2% > %Dot11.addr1%")
    def guess_payload_class(self, payload):
        if self.type == 0x02 and (self.subtype >= 0x08 and self.subtype <=0xF and self.subtype != 0xD):
            return Dot11QoS
	elif self.FCfield & 0x40:
            return Dot11WEP
        else:
            return Packet.guess_payload_class(self, payload)
    def answers(self, other):
        if isinstance(other,Dot11):
            if self.type == 0: # management
                if self.addr1.lower() != other.addr2.lower(): # check resp DA w/ req SA
                    return 0
                if (other.subtype,self.subtype) in [(0,1),(2,3),(4,5)]:
                    return 1
                if self.subtype == other.subtype == 11: # auth
                    return self.payload.answers(other.payload)
            elif self.type == 1: # control
                return 0
            elif self.type == 2: # data
                return self.payload.answers(other.payload)
            elif self.type == 3: # reserved
                return 0
        return 0
    def unwep(self, key=None, warn=1):
        if self.FCfield & 0x40 == 0:
            if warn:
                warning("No WEP to remove")
            return
        if  isinstance(self.payload.payload, NoPayload):
            if key or conf.wepkey:
                self.payload.decrypt(key)
            if isinstance(self.payload.payload, NoPayload):
                if warn:
                    warning("Dot11 can't be decrypted. Check conf.wepkey.")
                return
        self.FCfield &= ~0x40
        self.payload=self.payload.payload


class Dot11QoS(Packet):
    name = "802.11 QoS"
    fields_desc = [ BitField("TID",None,4),
                    BitField("EOSP",None,1),
                    BitField("Ack Policy",None,2),
                    BitField("Reserved",None,1),
                    ByteField("TXOP",None) ]
    def guess_payload_class(self, payload):
        if isinstance(self.underlayer, Dot11):
            if self.underlayer.FCfield & 0x40:
                return Dot11WEP
        return Packet.guess_payload_class(self, payload)


capability_list = [ "res8", "res9", "short-slot", "res11",
                    "res12", "DSSS-OFDM", "res14", "res15",
                   "ESS", "IBSS", "CFP", "CFP-req",
                   "privacy", "short-preamble", "PBCC", "agility"]

reason_code = {0:"reserved",1:"unspec", 2:"auth-expired",
               3:"deauth-ST-leaving",
               4:"inactivity", 5:"AP-full", 6:"class2-from-nonauth",
               7:"class3-from-nonass", 8:"disas-ST-leaving",
               9:"ST-not-auth"}

status_code = {0:"success", 1:"failure", 10:"cannot-support-all-cap",
               11:"inexist-asso", 12:"asso-denied", 13:"algo-unsupported",
               14:"bad-seq-num", 15:"challenge-failure",
               16:"timeout", 17:"AP-full",18:"rate-unsupported" }

class Dot11Beacon(Packet):
    name = "802.11 Beacon"
    fields_desc = [ LELongField("timestamp", 0),
                    LEShortField("beacon_interval", 0x0064),
                    FlagsField("cap", 0, 16, capability_list) ]
    

class Dot11Elt(Packet):
    name = "802.11 Information Element"
    fields_desc = [ ByteEnumField("ID", 0, {0:"SSID", 1:"Rates", 2: "FHset", 3:"DSset", 4:"CFset", 5:"TIM", 6:"IBSSset", 16:"challenge",
                                            42:"ERPinfo", 46:"QoS Capability", 47:"ERPinfo", 48:"RSNinfo", 50:"ESRates",221:"vendor",68:"reserved"}),
                    FieldLenField("len", None, "info", "B"),
                    StrLenField("info", "", length_from=lambda x:x.len) ]
    def mysummary(self):
        if self.ID == 0:
            return "SSID=%s"%repr(self.info),[Dot11]
        else:
            return ""

class Dot11ATIM(Packet):
    name = "802.11 ATIM"

class Dot11Disas(Packet):
    name = "802.11 Disassociation"
    fields_desc = [ LEShortEnumField("reason", 1, reason_code) ]

class Dot11AssoReq(Packet):
    name = "802.11 Association Request"
    fields_desc = [ FlagsField("cap", 0, 16, capability_list),
                    LEShortField("listen_interval", 0x00c8) ]


class Dot11AssoResp(Packet):
    name = "802.11 Association Response"
    fields_desc = [ FlagsField("cap", 0, 16, capability_list),
                    LEShortField("status", 0),
                    LEShortField("AID", 0) ]

class Dot11ReassoReq(Packet):
    name = "802.11 Reassociation Request"
    fields_desc = [ FlagsField("cap", 0, 16, capability_list),
                    LEShortField("listen_interval", 0x00c8),
                    MACField("current_AP", ETHER_ANY) ]


class Dot11ReassoResp(Dot11AssoResp):
    name = "802.11 Reassociation Response"

class Dot11ProbeReq(Packet):
    name = "802.11 Probe Request"
    
class Dot11ProbeResp(Packet):
    name = "802.11 Probe Response"
    fields_desc = [ LELongField("timestamp", 0),
                    LEShortField("beacon_interval", 0x0064),
                    FlagsField("cap", 0, 16, capability_list) ]
    
class Dot11Auth(Packet):
    name = "802.11 Authentication"
    fields_desc = [ LEShortEnumField("algo", 0, ["open", "sharedkey"]),
                    LEShortField("seqnum", 0),
                    LEShortEnumField("status", 0, status_code) ]
    def answers(self, other):
        if self.seqnum == other.seqnum+1:
            return 1
        return 0

class Dot11Deauth(Packet):
    name = "802.11 Deauthentication"
    fields_desc = [ LEShortEnumField("reason", 1, reason_code) ]



class Dot11WEP(Packet):
    name = "802.11 WEP packet"
    fields_desc = [ StrFixedLenField("iv", "\0\0\0", 3),
                    ByteField("keyid", 0),
                    StrField("wepdata",None,remain=4),
                    IntField("icv",None) ]

    def post_dissect(self, s):
#        self.icv, = struct.unpack("!I",self.wepdata[-4:])
#        self.wepdata = self.wepdata[:-4]
        self.decrypt()

    def build_payload(self):
        if self.wepdata is None:
            return Packet.build_payload(self)
        return ""

    def post_build(self, p, pay):
        if self.wepdata is None:
            key = conf.wepkey
            if key:
                if self.icv is None:
                    pay += struct.pack("<I",crc32(pay))
                    icv = ""
                else:
                    icv = p[4:8]
                c = ARC4.new(self.iv+key)
                p = p[:4]+c.encrypt(pay)+icv
            else:
                warning("No WEP key set (conf.wepkey).. strange results expected..")
        return p
            

    def decrypt(self,key=None):
        if key is None:
            key = conf.wepkey
        if key:
            c = ARC4.new(self.iv+key)
            self.add_payload(LLC(c.decrypt(self.wepdata)))
                    

bind_layers( PrismHeader,   Dot11,         )
bind_layers( RadioTap,      Dot11,         )
bind_layers( Dot11,         LLC,           type=2)
bind_layers( Dot11QoS,      LLC,           )
bind_layers( Dot11,         Dot11AssoReq,    subtype=0, type=0)
bind_layers( Dot11,         Dot11AssoResp,   subtype=1, type=0)
bind_layers( Dot11,         Dot11ReassoReq,  subtype=2, type=0)
bind_layers( Dot11,         Dot11ReassoResp, subtype=3, type=0)
bind_layers( Dot11,         Dot11ProbeReq,   subtype=4, type=0)
bind_layers( Dot11,         Dot11ProbeResp,  subtype=5, type=0)
bind_layers( Dot11,         Dot11Beacon,     subtype=8, type=0)
bind_layers( Dot11,         Dot11ATIM,       subtype=9, type=0)
bind_layers( Dot11,         Dot11Disas,      subtype=10, type=0)
bind_layers( Dot11,         Dot11Auth,       subtype=11, type=0)
bind_layers( Dot11,         Dot11Deauth,     subtype=12, type=0)
bind_layers( Dot11Beacon,     Dot11Elt,    )
bind_layers( Dot11AssoReq,    Dot11Elt,    )
bind_layers( Dot11AssoResp,   Dot11Elt,    )
bind_layers( Dot11ReassoReq,  Dot11Elt,    )
bind_layers( Dot11ReassoResp, Dot11Elt,    )
bind_layers( Dot11ProbeReq,   Dot11Elt,    )
bind_layers( Dot11ProbeResp,  Dot11Elt,    )
bind_layers( Dot11Auth,       Dot11Elt,    )
bind_layers( Dot11Elt,        Dot11Elt,    )


conf.l2types.register(105, Dot11)
conf.l2types.register_num2layer(801, Dot11)
conf.l2types.register(119, PrismHeader)
conf.l2types.register_num2layer(802, PrismHeader)
conf.l2types.register(127, RadioTap)
conf.l2types.register_num2layer(803, RadioTap)


class WiFi_am(AnsweringMachine):
    """Before using this, initialize "iffrom" and "ifto" interfaces:
iwconfig iffrom mode monitor
iwpriv orig_ifto hostapd 1
ifconfig ifto up
note: if ifto=wlan0ap then orig_ifto=wlan0
note: ifto and iffrom must be set on the same channel
ex:
ifconfig eth1 up
iwconfig eth1 mode monitor
iwconfig eth1 channel 11
iwpriv wlan0 hostapd 1
ifconfig wlan0ap up
iwconfig wlan0 channel 11
iwconfig wlan0 essid dontexist
iwconfig wlan0 mode managed
"""
    function_name = "airpwn"
    filter = None
    
    def parse_options(self, iffrom, ifto, replace, pattern="", ignorepattern=""):
        self.iffrom = iffrom
        self.ifto = ifto
        ptrn = re.compile(pattern)
        iptrn = re.compile(ignorepattern)
        
    def is_request(self, pkt):
        if not isinstance(pkt,Dot11):
            return 0
        if not pkt.FCfield & 1:
            return 0
        if not pkt.haslayer(TCP):
            return 0
        ip = pkt.getlayer(IP)
        tcp = pkt.getlayer(TCP)
        pay = str(tcp.payload)
        if not self.ptrn.match(pay):
            return 0
        if self.iptrn.match(pay):
            return 0

    def make_reply(self, p):
        ip = p.getlayer(IP)
        tcp = p.getlayer(TCP)
        pay = str(tcp.payload)
        del(p.payload.payload.payload)
        p.FCfield="from-DS"
        p.addr1,p.addr2 = p.addr2,p.addr1
        p /= IP(src=ip.dst,dst=ip.src)
        p /= TCP(sport=tcp.dport, dport=tcp.sport,
                 seq=tcp.ack, ack=tcp.seq+len(pay),
                 flags="PA")
        q = p.copy()
        p /= self.replace
        q.ID += 1
        q.getlayer(TCP).flags="RA"
        q.getlayer(TCP).seq+=len(replace)
        return [p,q]
    
    def print_reply(self):
        print p.sprintf("Sent %IP.src%:%IP.sport% > %IP.dst%:%TCP.dport%")

    def send_reply(self, reply):
        sendp(reply, iface=self.ifto, **self.optsend)

    def sniff(self):
        sniff(iface=self.iffrom, **self.optsniff)



plst=[]
def get_toDS():
    global plst
    while 1:
        p,=sniff(iface="eth1",count=1)
        if not isinstance(p,Dot11):
            continue
        if p.FCfield & 1:
            plst.append(p)
            print "."


#    if not ifto.endswith("ap"):
#        print "iwpriv %s hostapd 1" % ifto
#        os.system("iwpriv %s hostapd 1" % ifto)
#        ifto += "ap"
#        
#    os.system("iwconfig %s mode monitor" % iffrom)
#    

def airpwn(iffrom, ifto, replace, pattern="", ignorepattern=""):
    """Before using this, initialize "iffrom" and "ifto" interfaces:
iwconfig iffrom mode monitor
iwpriv orig_ifto hostapd 1
ifconfig ifto up
note: if ifto=wlan0ap then orig_ifto=wlan0
note: ifto and iffrom must be set on the same channel
ex:
ifconfig eth1 up
iwconfig eth1 mode monitor
iwconfig eth1 channel 11
iwpriv wlan0 hostapd 1
ifconfig wlan0ap up
iwconfig wlan0 channel 11
iwconfig wlan0 essid dontexist
iwconfig wlan0 mode managed
"""
    
    ptrn = re.compile(pattern)
    iptrn = re.compile(ignorepattern)
    def do_airpwn(p, ifto=ifto, replace=replace, ptrn=ptrn, iptrn=iptrn):
        if not isinstance(p,Dot11):
            return
        if not p.FCfield & 1:
            return
        if not p.haslayer(TCP):
            return
        ip = p.getlayer(IP)
        tcp = p.getlayer(TCP)
        pay = str(tcp.payload)
#        print "got tcp"
        if not ptrn.match(pay):
            return
#        print "match 1"
        if iptrn.match(pay):
            return
#        print "match 2"
        del(p.payload.payload.payload)
        p.FCfield="from-DS"
        p.addr1,p.addr2 = p.addr2,p.addr1
        q = p.copy()
        p /= IP(src=ip.dst,dst=ip.src)
        p /= TCP(sport=tcp.dport, dport=tcp.sport,
                 seq=tcp.ack, ack=tcp.seq+len(pay),
                 flags="PA")
        q = p.copy()
        p /= replace
        q.ID += 1
        q.getlayer(TCP).flags="RA"
        q.getlayer(TCP).seq+=len(replace)
        
        sendp([p,q], iface=ifto, verbose=0)
#        print "send",repr(p)        
#        print "send",repr(q)
        print p.sprintf("Sent %IP.src%:%IP.sport% > %IP.dst%:%TCP.dport%")

    sniff(iface=iffrom,prn=do_airpwn)

            
        
conf.stats_dot11_protocols += [Dot11WEP, Dot11Beacon, ]


        


class Dot11PacketList(PacketList):
    def __init__(self, res=None, name="Dot11List", stats=None):
        if stats is None:
            stats = conf.stats_dot11_protocols

        PacketList.__init__(self, res, name, stats)
    def toEthernet(self):
        data = map(lambda x:x.getlayer(Dot11), filter(lambda x : x.haslayer(Dot11) and x.type == 2, self.res))
        r2 = []
        for p in data:
            q = p.copy()
            q.unwep()
            r2.append(Ether()/q.payload.payload.payload) #Dot11/LLC/SNAP/IP
        return PacketList(r2,name="Ether from %s"%self.listname)
        
        

########NEW FILE########
__FILENAME__ = gprs
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
GPRS (General Packet Radio Service) for mobile data communication.
"""

from scapy.fields import *
from scapy.packet import *
from scapy.layers.inet import IP

class GPRS(Packet):
    name = "GPRSdummy"
    fields_desc = [
        StrStopField("dummy","","\x65\x00\x00",1)
        ]


bind_layers( GPRS,          IP,            )

########NEW FILE########
__FILENAME__ = hsrp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
HSRP (Hot Standby Router Protocol): proprietary redundancy protocol for Cisco routers.
"""

from scapy.fields import *
from scapy.packet import *
from scapy.layers.inet import UDP

class HSRP(Packet):
    name = "HSRP"
    fields_desc = [
        ByteField("version", 0),
        ByteEnumField("opcode", 0, { 0:"Hello"}),
        ByteEnumField("state", 16, { 16:"Active"}),
        ByteField("hellotime", 3),
        ByteField("holdtime", 10),
        ByteField("priority", 120),
        ByteField("group", 1),
        ByteField("reserved", 0),
        StrFixedLenField("auth","cisco",8),
        IPField("virtualIP","192.168.1.1") ]
        


        
        
bind_layers( UDP,           HSRP,          dport=1985, sport=1985)

########NEW FILE########
__FILENAME__ = inet
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
IPv4 (Internet Protocol v4).
"""

import os,time,struct,re,socket,new
from select import select
from collections import defaultdict
from scapy.utils import checksum
from scapy.layers.l2 import *
from scapy.config import conf
from scapy.fields import *
from scapy.packet import *
from scapy.volatile import *
from scapy.sendrecv import sr,sr1,srp1
from scapy.plist import PacketList,SndRcvList
from scapy.automaton import Automaton,ATMT

import scapy.as_resolvers


####################
## IP Tools class ##
####################

class IPTools:
    """Add more powers to a class that have a "src" attribute."""
    def whois(self):
        os.system("whois %s" % self.src)
    def ottl(self):
        t = [32,64,128,255]+[self.ttl]
        t.sort()
        return t[t.index(self.ttl)+1]
    def hops(self):
        return self.ottl()-self.ttl-1 


_ip_options_names = { 0: "end_of_list",
                      1: "nop",
                      2: "security",
                      3: "loose_source_route",
                      4: "timestamp",
                      5: "extended_security",
                      6: "commercial_security",
                      7: "record_route",
                      8: "stream_id",
                      9: "strict_source_route",
                      10: "experimental_measurement",
                      11: "mtu_probe",
                      12: "mtu_reply",
                      13: "flow_control",
                      14: "access_control",
                      15: "encode",
                      16: "imi_traffic_descriptor",
                      17: "extended_IP",
                      18: "traceroute",
                      19: "address_extension",
                      20: "router_alert",
                      21: "selective_directed_broadcast_mode",
                      23: "dynamic_packet_state",
                      24: "upstream_multicast_packet",
                      25: "quick_start",
                      30: "rfc4727_experiment", 
                      }
                      

class _IPOption_HDR(Packet):
    fields_desc = [ BitField("copy_flag",0, 1),
                    BitEnumField("optclass",0,2,{0:"control",2:"debug"}),
                    BitEnumField("option",0,5, _ip_options_names) ]
    
class IPOption(Packet):
    fields_desc = [ _IPOption_HDR,
                    FieldLenField("length", None, fmt="B",  # Only option 0 and 1 have no length and value
                                  length_of="value", adjust=lambda pkt,l:l+2),
                    StrLenField("value", "",length_from=lambda pkt:pkt.length-2) ]
    
    def extract_padding(self, p):
        return "",p

    registered_ip_options = {}
    @classmethod
    def register_variant(cls):
        cls.registered_ip_options[cls.option.default] = cls
    @classmethod
    def dispatch_hook(cls, pkt=None, *args, **kargs):
        if pkt:
            opt = ord(pkt[0])&0x1f
            if opt in cls.registered_ip_options:
                return cls.registered_ip_options[opt]
        return cls

class IPOption_EOL(IPOption):
    option = 0
    fields_desc = [ _IPOption_HDR ]
    

class IPOption_NOP(IPOption):
    option=1
    fields_desc = [ _IPOption_HDR ]

class IPOption_Security(IPOption):
    copy_flag = 1
    option = 2
    fields_desc = [ _IPOption_HDR,
                    ByteField("length", 11),
                    ShortField("security",0),
                    ShortField("compartment",0),
                    ShortField("handling_restrictions",0),
                    StrFixedLenField("transmission_control_code","xxx",3),
                    ]
    
class IPOption_LSRR(IPOption):
    name = "IP Option Loose Source and Record Route"
    copy_flag = 1
    option = 3
    fields_desc = [ _IPOption_HDR,
                    FieldLenField("length", None, fmt="B",
                                  length_of="routers", adjust=lambda pkt,l:l+3),
                    ByteField("pointer",4), # 4 is first IP
                    FieldListField("routers",[],IPField("","0.0.0.0"), 
                                   length_from=lambda pkt:pkt.length-3)
                    ]
    def get_current_router(self):
        return self.routers[self.pointer/4-1]

class IPOption_RR(IPOption_LSRR):
    name = "IP Option Record Route"
    option = 7

class IPOption_SSRR(IPOption_LSRR):
    name = "IP Option Strict Source and Record Route"
    option = 9

class IPOption_Stream_Id(IPOption):
    name = "IP Option Stream ID"
    option = 8
    fields_desc = [ _IPOption_HDR,
                    ByteField("length", 4),
                    ShortField("security",0), ]
                    
class IPOption_MTU_Probe(IPOption):
    name = "IP Option MTU Probe"
    option = 11
    fields_desc = [ _IPOption_HDR,
                    ByteField("length", 4),
                    ShortField("mtu",0), ]

class IPOption_MTU_Reply(IPOption_MTU_Probe):
    name = "IP Option MTU Reply"
    option = 12

class IPOption_Traceroute(IPOption):
    copy_flag = 1
    option = 18
    fields_desc = [ _IPOption_HDR,
                    ByteField("length", 12),
                    ShortField("id",0),
                    ShortField("outbound_hops",0),
                    ShortField("return_hops",0),
                    IPField("originator_ip","0.0.0.0") ]

class IPOption_Address_Extension(IPOption):
    name = "IP Option Address Extension"
    copy_flag = 1
    option = 19
    fields_desc = [ _IPOption_HDR,
                    ByteField("length", 10),
                    IPField("src_ext","0.0.0.0"),
                    IPField("dst_ext","0.0.0.0") ]

class IPOption_Router_Alert(IPOption):
    name = "IP Option Router Alert"
    copy_flag = 1
    option = 20
    fields_desc = [ _IPOption_HDR,
                    ByteField("length", 4),
                    ShortEnumField("alert",0, {0:"router_shall_examine_packet"}), ]


class IPOption_SDBM(IPOption):
    name = "IP Option Selective Directed Broadcast Mode"
    copy_flag = 1
    option = 21
    fields_desc = [ _IPOption_HDR,
                    FieldLenField("length", None, fmt="B",
                                  length_of="addresses", adjust=lambda pkt,l:l+2),
                    FieldListField("addresses",[],IPField("","0.0.0.0"), 
                                   length_from=lambda pkt:pkt.length-2)
                    ]
    


TCPOptions = (
              { 0 : ("EOL",None),
                1 : ("NOP",None),
                2 : ("MSS","!H"),
                3 : ("WScale","!B"),
                4 : ("SAckOK",None),
                5 : ("SAck","!"),
                8 : ("Timestamp","!II"),
                14 : ("AltChkSum","!BH"),
                15 : ("AltChkSumOpt",None),
                25 : ("Mood","!p")
                },
              { "EOL":0,
                "NOP":1,
                "MSS":2,
                "WScale":3,
                "SAckOK":4,
                "SAck":5,
                "Timestamp":8,
                "AltChkSum":14,
                "AltChkSumOpt":15,
                "Mood":25
                } )

class TCPOptionsField(StrField):
    islist=1
    def getfield(self, pkt, s):
        opsz = (pkt.dataofs-5)*4
        if opsz < 0:
            warning("bad dataofs (%i). Assuming dataofs=5"%pkt.dataofs)
            opsz = 0
        return s[opsz:],self.m2i(pkt,s[:opsz])
    def m2i(self, pkt, x):
        opt = []
        while x:
            onum = ord(x[0])
            if onum == 0:
                opt.append(("EOL",None))
                x=x[1:]
                break
            if onum == 1:
                opt.append(("NOP",None))
                x=x[1:]
                continue
            olen = ord(x[1])
            if olen < 2:
                warning("Malformed TCP option (announced length is %i)" % olen)
                olen = 2
            oval = x[2:olen]
            if TCPOptions[0].has_key(onum):
                oname, ofmt = TCPOptions[0][onum]
                if onum == 5: #SAck
                    ofmt += "%iI" % (len(oval)/4)
                if ofmt and struct.calcsize(ofmt) == len(oval):
                    oval = struct.unpack(ofmt, oval)
                    if len(oval) == 1:
                        oval = oval[0]
                opt.append((oname, oval))
            else:
                opt.append((onum, oval))
            x = x[olen:]
        return opt
    
    def i2m(self, pkt, x):
        opt = ""
        for oname,oval in x:
            if type(oname) is str:
                if oname == "NOP":
                    opt += "\x01"
                    continue
                elif oname == "EOL":
                    opt += "\x00"
                    continue
                elif TCPOptions[1].has_key(oname):
                    onum = TCPOptions[1][oname]
                    ofmt = TCPOptions[0][onum][1]
                    if onum == 5: #SAck
                        ofmt += "%iI" % len(oval)
                    if ofmt is not None and (type(oval) is not str or "s" in ofmt):
                        if type(oval) is not tuple:
                            oval = (oval,)
                        oval = struct.pack(ofmt, *oval)
                else:
                    warning("option [%s] unknown. Skipped."%oname)
                    continue
            else:
                onum = oname
                if type(oval) is not str:
                    warning("option [%i] is not string."%onum)
                    continue
            opt += chr(onum)+chr(2+len(oval))+oval
        return opt+"\x00"*(3-((len(opt)+3)%4))
    def randval(self):
        return [] # XXX
    

class ICMPTimeStampField(IntField):
    re_hmsm = re.compile("([0-2]?[0-9])[Hh:](([0-5]?[0-9])([Mm:]([0-5]?[0-9])([sS:.]([0-9]{0,3}))?)?)?$")
    def i2repr(self, pkt, val):
        if val is None:
            return "--"
        else:
            sec, milli = divmod(val, 1000)
            min, sec = divmod(sec, 60)
            hour, min = divmod(min, 60)
            return "%d:%d:%d.%d" %(hour, min, sec, int(milli))
    def any2i(self, pkt, val):
        if type(val) is str:
            hmsms = self.re_hmsm.match(val)
            if hmsms:
                h,_,m,_,s,_,ms = hmsms = hmsms.groups()
                ms = int(((ms or "")+"000")[:3])
                val = ((int(h)*60+int(m or 0))*60+int(s or 0))*1000+ms
            else:
                val = 0
        elif val is None:
            val = int((time.time()%(24*60*60))*1000)
        return val


class IP(Packet, IPTools):
    name = "IP"
    fields_desc = [ BitField("version" , 4 , 4),
                    BitField("ihl", None, 4),
                    XByteField("tos", 0),
                    ShortField("len", None),
                    ShortField("id", 1),
                    FlagsField("flags", 0, 3, ["MF","DF","evil"]),
                    BitField("frag", 0, 13),
                    ByteField("ttl", 64),
                    ByteEnumField("proto", 0, IP_PROTOS),
                    XShortField("chksum", None),
                    #IPField("src", "127.0.0.1"),
                    Emph(SourceIPField("src","dst")),
                    Emph(IPField("dst", "127.0.0.1")),
                    PacketListField("options", [], IPOption, length_from=lambda p:p.ihl*4-20) ]
    def post_build(self, p, pay):
        ihl = self.ihl
        p += "\0"*((-len(p))%4) # pad IP options if needed
        if ihl is None:
            ihl = len(p)/4
            p = chr(((self.version&0xf)<<4) | ihl&0x0f)+p[1:]
        if self.len is None:
            l = len(p)+len(pay)
            p = p[:2]+struct.pack("!H", l)+p[4:]
        if self.chksum is None:
            ck = checksum(p)
            p = p[:10]+chr(ck>>8)+chr(ck&0xff)+p[12:]
        return p+pay

    def extract_padding(self, s):
        l = self.len - (self.ihl << 2)
        return s[:l],s[l:]

    def send(self, s, slp=0):
        for p in self:
            try:
                s.sendto(str(p), (p.dst,0))
            except socket.error, msg:
                log_runtime.error(msg)
            if slp:
                time.sleep(slp)
    def route(self):
        dst = self.dst
        if isinstance(dst,Gen):
            dst = iter(dst).next()
        return conf.route.route(dst)
    def hashret(self):
        if ( (self.proto == socket.IPPROTO_ICMP)
             and (isinstance(self.payload, ICMP))
             and (self.payload.type in [3,4,5,11,12]) ):
            return self.payload.payload.hashret()
        else:
            if conf.checkIPsrc and conf.checkIPaddr:
                return strxor(inet_aton(self.src),inet_aton(self.dst))+struct.pack("B",self.proto)+self.payload.hashret()
            else:
                return struct.pack("B", self.proto)+self.payload.hashret()
    def answers(self, other):
        if not isinstance(other,IP):
            return 0
        if conf.checkIPaddr and (self.dst != other.src):
            return 0
        if ( (self.proto == socket.IPPROTO_ICMP) and
             (isinstance(self.payload, ICMP)) and
             (self.payload.type in [3,4,5,11,12]) ):
            # ICMP error message
            return self.payload.payload.answers(other)

        else:
            if ( (conf.checkIPaddr and (self.src != other.dst)) or
                 (self.proto != other.proto) ):
                return 0
            return self.payload.answers(other.payload)
    def mysummary(self):
        s = self.sprintf("%IP.src% > %IP.dst% %IP.proto%")
        if self.frag:
            s += " frag:%i" % self.frag
        return s
                 
    def fragment(self, fragsize=1480):
        """Fragment IP datagrams"""
        fragsize = (fragsize+7)/8*8
        lst = []
        fnb = 0
        fl = self
        while fl.underlayer is not None:
            fnb += 1
            fl = fl.underlayer
        
        for p in fl:
            s = str(p[fnb].payload)
            nb = (len(s)+fragsize-1)/fragsize
            for i in range(nb):            
                q = p.copy()
                del(q[fnb].payload)
                del(q[fnb].chksum)
                del(q[fnb].len)
                if i == nb-1:
                    q[IP].flags &= ~1
                else:
                    q[IP].flags |= 1 
                q[IP].frag = i*fragsize/8
                r = Raw(load=s[i*fragsize:(i+1)*fragsize])
                r.overload_fields = p[IP].payload.overload_fields.copy()
                q.add_payload(r)
                lst.append(q)
        return lst


class TCP(Packet):
    name = "TCP"
    fields_desc = [ ShortEnumField("sport", 20, TCP_SERVICES),
                    ShortEnumField("dport", 80, TCP_SERVICES),
                    IntField("seq", 0),
                    IntField("ack", 0),
                    BitField("dataofs", None, 4),
                    BitField("reserved", 0, 4),
                    FlagsField("flags", 0x2, 8, "FSRPAUEC"),
                    ShortField("window", 8192),
                    XShortField("chksum", None),
                    ShortField("urgptr", 0),
                    TCPOptionsField("options", {}) ]
    def post_build(self, p, pay):
        p += pay
        dataofs = self.dataofs
        if dataofs is None:
            dataofs = 5+((len(self.get_field("options").i2m(self,self.options))+3)/4)
            p = p[:12]+chr((dataofs << 4) | ord(p[12])&0x0f)+p[13:]
        if self.chksum is None:
            if isinstance(self.underlayer, IP):
                if self.underlayer.len is not None:
                    ln = self.underlayer.len-20
                else:
                    ln = len(p)
                psdhdr = struct.pack("!4s4sHH",
                                     inet_aton(self.underlayer.src),
                                     inet_aton(self.underlayer.dst),
                                     self.underlayer.proto,
                                     ln)
                ck=checksum(psdhdr+p)
                p = p[:16]+struct.pack("!H", ck)+p[18:]
            elif conf.ipv6_enabled and isinstance(self.underlayer, scapy.layers.inet6.IPv6) or isinstance(self.underlayer, scapy.layers.inet6._IPv6ExtHdr):
                ck = scapy.layers.inet6.in6_chksum(socket.IPPROTO_TCP, self.underlayer, p)
                p = p[:16]+struct.pack("!H", ck)+p[18:]
            else:
                warning("No IP underlayer to compute checksum. Leaving null.")
        return p
    def hashret(self):
        if conf.checkIPsrc:
            return struct.pack("H",self.sport ^ self.dport)+self.payload.hashret()
        else:
            return self.payload.hashret()
    def answers(self, other):
        if not isinstance(other, TCP):
            return 0
        if conf.checkIPsrc:
            if not ((self.sport == other.dport) and
                    (self.dport == other.sport)):
                return 0
        if (abs(other.seq-self.ack) > 2+len(other.payload)):
            return 0
        return 1
    def mysummary(self):
        if isinstance(self.underlayer, IP):
            return self.underlayer.sprintf("TCP %IP.src%:%TCP.sport% > %IP.dst%:%TCP.dport% %TCP.flags%")
        elif conf.ipv6_enabled and isinstance(self.underlayer, scapy.layers.inet6.IPv6):
            return self.underlayer.sprintf("TCP %IPv6.src%:%TCP.sport% > %IPv6.dst%:%TCP.dport% %TCP.flags%")
        else:
            return self.sprintf("TCP %TCP.sport% > %TCP.dport% %TCP.flags%")

class UDP(Packet):
    name = "UDP"
    fields_desc = [ ShortEnumField("sport", 53, UDP_SERVICES),
                    ShortEnumField("dport", 53, UDP_SERVICES),
                    ShortField("len", None),
                    XShortField("chksum", None), ]
    def post_build(self, p, pay):
        p += pay
        l = self.len
        if l is None:
            l = len(p)
            p = p[:4]+struct.pack("!H",l)+p[6:]
        if self.chksum is None:
            if isinstance(self.underlayer, IP):
                if self.underlayer.len is not None:
                    ln = self.underlayer.len-20
                else:
                    ln = len(p)
                psdhdr = struct.pack("!4s4sHH",
                                     inet_aton(self.underlayer.src),
                                     inet_aton(self.underlayer.dst),
                                     self.underlayer.proto,
                                     ln)
                ck=checksum(psdhdr+p)
                p = p[:6]+struct.pack("!H", ck)+p[8:]
            elif isinstance(self.underlayer, scapy.layers.inet6.IPv6) or isinstance(self.underlayer, scapy.layers.inet6._IPv6ExtHdr):
                ck = scapy.layers.inet6.in6_chksum(socket.IPPROTO_UDP, self.underlayer, p)
                p = p[:6]+struct.pack("!H", ck)+p[8:]
            else:
                warning("No IP underlayer to compute checksum. Leaving null.")
        return p
    def extract_padding(self, s):
        l = self.len - 8
        return s[:l],s[l:]
    def hashret(self):
        return self.payload.hashret()
    def answers(self, other):
        if not isinstance(other, UDP):
            return 0
        if conf.checkIPsrc:
            if self.dport != other.sport:
                return 0
        return self.payload.answers(other.payload)
    def mysummary(self):
        if isinstance(self.underlayer, IP):
            return self.underlayer.sprintf("UDP %IP.src%:%UDP.sport% > %IP.dst%:%UDP.dport%")
        elif isinstance(self.underlayer, scapy.layers.inet6.IPv6):
            return self.underlayer.sprintf("UDP %IPv6.src%:%UDP.sport% > %IPv6.dst%:%UDP.dport%")
        else:
            return self.sprintf("UDP %UDP.sport% > %UDP.dport%")    

icmptypes = { 0 : "echo-reply",
              3 : "dest-unreach",
              4 : "source-quench",
              5 : "redirect",
              8 : "echo-request",
              9 : "router-advertisement",
              10 : "router-solicitation",
              11 : "time-exceeded",
              12 : "parameter-problem",
              13 : "timestamp-request",
              14 : "timestamp-reply",
              15 : "information-request",
              16 : "information-response",
              17 : "address-mask-request",
              18 : "address-mask-reply" }

icmpcodes = { 3 : { 0  : "network-unreachable",
                    1  : "host-unreachable",
                    2  : "protocol-unreachable",
                    3  : "port-unreachable",
                    4  : "fragmentation-needed",
                    5  : "source-route-failed",
                    6  : "network-unknown",
                    7  : "host-unknown",
                    9  : "network-prohibited",
                    10 : "host-prohibited",
                    11 : "TOS-network-unreachable",
                    12 : "TOS-host-unreachable",
                    13 : "communication-prohibited",
                    14 : "host-precedence-violation",
                    15 : "precedence-cutoff", },
              5 : { 0  : "network-redirect",
                    1  : "host-redirect",
                    2  : "TOS-network-redirect",
                    3  : "TOS-host-redirect", },
              11 : { 0 : "ttl-zero-during-transit",
                     1 : "ttl-zero-during-reassembly", },
              12 : { 0 : "ip-header-bad",
                     1 : "required-option-missing", }, }
                         
                   


class ICMP(Packet):
    name = "ICMP"
    fields_desc = [ ByteEnumField("type",8, icmptypes),
                    MultiEnumField("code",0, icmpcodes, depends_on=lambda pkt:pkt.type,fmt="B"),
                    XShortField("chksum", None),
                    ConditionalField(XShortField("id",0),  lambda pkt:pkt.type in [0,8,13,14,15,16,17,18]),
                    ConditionalField(XShortField("seq",0), lambda pkt:pkt.type in [0,8,13,14,15,16,17,18]),
                    ConditionalField(ICMPTimeStampField("ts_ori", None), lambda pkt:pkt.type in [13,14]),
                    ConditionalField(ICMPTimeStampField("ts_rx", None), lambda pkt:pkt.type in [13,14]),
                    ConditionalField(ICMPTimeStampField("ts_tx", None), lambda pkt:pkt.type in [13,14]),
                    ConditionalField(IPField("gw","0.0.0.0"),  lambda pkt:pkt.type==5),
                    ConditionalField(ByteField("ptr",0),   lambda pkt:pkt.type==12),
                    ConditionalField(X3BytesField("reserved",0), lambda pkt:pkt.type==12),
                    ConditionalField(IPField("addr_mask","0.0.0.0"), lambda pkt:pkt.type in [17,18]),
                    ConditionalField(IntField("unused",0), lambda pkt:pkt.type not in [0,5,8,12,13,14,15,16,17,18]),
                    
                    ]
    def post_build(self, p, pay):
        p += pay
        if self.chksum is None:
            ck = checksum(p)
            p = p[:2]+chr(ck>>8)+chr(ck&0xff)+p[4:]
        return p
    
    def hashret(self):
        if self.type in [0,8,13,14,15,16,17,18]:
            return struct.pack("HH",self.id,self.seq)+self.payload.hashret()
        return self.payload.hashret()
    def answers(self, other):
        if not isinstance(other,ICMP):
            return 0
        if ( (other.type,self.type) in [(8,0),(13,14),(15,16),(17,18)] and
             self.id == other.id and
             self.seq == other.seq ):
            return 1
        return 0

    def guess_payload_class(self, payload):
        if self.type in [3,4,5,11,12]:
            return IPerror
        else:
            return None
    def mysummary(self):
        if isinstance(self.underlayer, IP):
            return self.underlayer.sprintf("ICMP %IP.src% > %IP.dst% %ICMP.type% %ICMP.code%")
        else:
            return self.sprintf("ICMP %ICMP.type% %ICMP.code%")
    
        



class IPerror(IP):
    name = "IP in ICMP"
    def answers(self, other):
        if not isinstance(other, IP):
            return 0
        if not ( ((conf.checkIPsrc == 0) or (self.dst == other.dst)) and
                 (self.src == other.src) and
                 ( ((conf.checkIPID == 0)
                    or (self.id == other.id)
                    or (conf.checkIPID == 1 and self.id == socket.htons(other.id)))) and
                 (self.proto == other.proto) ):
            return 0
        return self.payload.answers(other.payload)
    def mysummary(self):
        return Packet.mysummary(self)


class TCPerror(TCP):
    name = "TCP in ICMP"
    def answers(self, other):
        if not isinstance(other, TCP):
            return 0
        if conf.checkIPsrc:
            if not ((self.sport == other.sport) and
                    (self.dport == other.dport)):
                return 0
        if conf.check_TCPerror_seqack:
            if self.seq is not None:
                if self.seq != other.seq:
                    return 0
            if self.ack is not None:
                if self.ack != other.ack:
                    return 0
        return 1
    def mysummary(self):
        return Packet.mysummary(self)


class UDPerror(UDP):
    name = "UDP in ICMP"
    def answers(self, other):
        if not isinstance(other, UDP):
            return 0
        if conf.checkIPsrc:
            if not ((self.sport == other.sport) and
                    (self.dport == other.dport)):
                return 0
        return 1
    def mysummary(self):
        return Packet.mysummary(self)

                    

class ICMPerror(ICMP):
    name = "ICMP in ICMP"
    def answers(self, other):
        if not isinstance(other,ICMP):
            return 0
        if not ((self.type == other.type) and
                (self.code == other.code)):
            return 0
        if self.code in [0,8,13,14,17,18]:
            if (self.id == other.id and
                self.seq == other.seq):
                return 1
            else:
                return 0
        else:
            return 1
    def mysummary(self):
        return Packet.mysummary(self)

bind_layers( Ether,         IP,            type=2048)
bind_layers( CookedLinux,   IP,            proto=2048)
bind_layers( GRE,           IP,            proto=2048)
bind_layers( SNAP,          IP,            code=2048)
bind_layers( IPerror,       IPerror,       frag=0, proto=4)
bind_layers( IPerror,       ICMPerror,     frag=0, proto=1)
bind_layers( IPerror,       TCPerror,      frag=0, proto=6)
bind_layers( IPerror,       UDPerror,      frag=0, proto=17)
bind_layers( IP,            IP,            frag=0, proto=4)
bind_layers( IP,            ICMP,          frag=0, proto=1)
bind_layers( IP,            TCP,           frag=0, proto=6)
bind_layers( IP,            UDP,           frag=0, proto=17)
bind_layers( IP,            GRE,           frag=0, proto=47)

conf.l2types.register(101, IP)
conf.l2types.register_num2layer(12, IP)

conf.l3types.register(ETH_P_IP, IP)
conf.l3types.register_num2layer(ETH_P_ALL, IP)


conf.neighbor.register_l3(Ether, IP, lambda l2,l3: getmacbyip(l3.dst))
conf.neighbor.register_l3(Dot3, IP, lambda l2,l3: getmacbyip(l3.dst))


###################
## Fragmentation ##
###################

@conf.commands.register
def fragment(pkt, fragsize=1480):
    """Fragment a big IP datagram"""
    fragsize = (fragsize+7)/8*8
    lst = []
    for p in pkt:
        s = str(p[IP].payload)
        nb = (len(s)+fragsize-1)/fragsize
        for i in range(nb):            
            q = p.copy()
            del(q[IP].payload)
            del(q[IP].chksum)
            del(q[IP].len)
            if i == nb-1:
                q[IP].flags &= ~1
            else:
                q[IP].flags |= 1 
            q[IP].frag = i*fragsize/8
            r = Raw(load=s[i*fragsize:(i+1)*fragsize])
            r.overload_fields = p[IP].payload.overload_fields.copy()
            q.add_payload(r)
            lst.append(q)
    return lst

def overlap_frag(p, overlap, fragsize=8, overlap_fragsize=None):
    if overlap_fragsize is None:
        overlap_fragsize = fragsize
    q = p.copy()
    del(q[IP].payload)
    q[IP].add_payload(overlap)

    qfrag = fragment(q, overlap_fragsize)
    qfrag[-1][IP].flags |= 1
    return qfrag+fragment(p, fragsize)

@conf.commands.register
def defrag(plist):
    """defrag(plist) -> ([not fragmented], [defragmented],
                  [ [bad fragments], [bad fragments], ... ])"""
    frags = defaultdict(PacketList)
    nofrag = PacketList()
    for p in plist:
        ip = p[IP]
        if IP not in p:
            nofrag.append(p)
            continue
        if ip.frag == 0 and ip.flags & 1 == 0:
            nofrag.append(p)
            continue
        uniq = (ip.id,ip.src,ip.dst,ip.proto)
        frags[uniq].append(p)
    defrag = []
    missfrag = []
    for lst in frags.itervalues():
        lst.sort(key=lambda x: x.frag)
        p = lst[0]
        lastp = lst[-1]
        if p.frag > 0 or lastp.flags & 1 != 0: # first or last fragment missing
            missfrag.append(lst)
            continue
        p = p.copy()
        if Padding in p:
            del(p[Padding].underlayer.payload)
        ip = p[IP]
        if ip.len is None or ip.ihl is None:
            clen = len(ip.payload)
        else:
            clen = ip.len - (ip.ihl<<2)
        txt = Raw()
        for q in lst[1:]:
            if clen != q.frag<<3: # Wrong fragmentation offset
                if clen > q.frag<<3:
                    warning("Fragment overlap (%i > %i) %r || %r ||  %r" % (clen, q.frag<<3, p,txt,q))
                missfrag.append(lst)
                break
            if q[IP].len is None or q[IP].ihl is None:
                clen += len(q[IP].payload)
            else:
                clen += q[IP].len - (q[IP].ihl<<2)
            if Padding in q:
                del(q[Padding].underlayer.payload)
            txt.add_payload(q[IP].payload.copy())
        else:
            ip.flags &= ~1 # !MF
            del(ip.chksum)
            del(ip.len)
            p = p/txt
            defrag.append(p)
    defrag2=PacketList()
    for p in defrag:
        defrag2.append(p.__class__(str(p)))
    return nofrag,defrag2,missfrag
            
@conf.commands.register
def defragment(plist):
    """defrag(plist) -> plist defragmented as much as possible """
    frags = defaultdict(lambda:[])
    final = []

    pos = 0
    for p in plist:
        p._defrag_pos = pos
        pos += 1
        if IP in p:
            ip = p[IP]
            if ip.frag != 0 or ip.flags & 1:
                ip = p[IP]
                uniq = (ip.id,ip.src,ip.dst,ip.proto)
                frags[uniq].append(p)
                continue
        final.append(p)

    defrag = []
    missfrag = []
    for lst in frags.itervalues():
        lst.sort(key=lambda x: x.frag)
        p = lst[0]
        lastp = lst[-1]
        if p.frag > 0 or lastp.flags & 1 != 0: # first or last fragment missing
            missfrag += lst
            continue
        p = p.copy()
        if Padding in p:
            del(p[Padding].underlayer.payload)
        ip = p[IP]
        if ip.len is None or ip.ihl is None:
            clen = len(ip.payload)
        else:
            clen = ip.len - (ip.ihl<<2)
        txt = Raw()
        for q in lst[1:]:
            if clen != q.frag<<3: # Wrong fragmentation offset
                if clen > q.frag<<3:
                    warning("Fragment overlap (%i > %i) %r || %r ||  %r" % (clen, q.frag<<3, p,txt,q))
                missfrag += lst
                break
            if q[IP].len is None or q[IP].ihl is None:
                clen += len(q[IP].payload)
            else:
                clen += q[IP].len - (q[IP].ihl<<2)
            if Padding in q:
                del(q[Padding].underlayer.payload)
            txt.add_payload(q[IP].payload.copy())
        else:
            ip.flags &= ~1 # !MF
            del(ip.chksum)
            del(ip.len)
            p = p/txt
            p._defrag_pos = max(x._defrag_pos for x in lst)
            defrag.append(p)
    defrag2=[]
    for p in defrag:
        q = p.__class__(str(p))
        q._defrag_pos = p._defrag_pos
        defrag2.append(q)
    final += defrag2
    final += missfrag
    final.sort(key=lambda x: x._defrag_pos)
    for p in final:
        del(p._defrag_pos)

    if hasattr(plist, "listname"):
        name = "Defragmented %s" % plist.listname
    else:
        name = "Defragmented"
    
    return PacketList(final, name=name)
            
        

### Add timeskew_graph() method to PacketList
def _packetlist_timeskew_graph(self, ip, **kargs):
    """Tries to graph the timeskew between the timestamps and real time for a given ip"""
    res = map(lambda x: self._elt2pkt(x), self.res)
    b = filter(lambda x:x.haslayer(IP) and x.getlayer(IP).src == ip and x.haslayer(TCP), res)
    c = []
    for p in b:
        opts = p.getlayer(TCP).options
        for o in opts:
            if o[0] == "Timestamp":
                c.append((p.time,o[1][0]))
    if not c:
        warning("No timestamps found in packet list")
        return
    d = map(lambda (x,y): (x%2000,((x-c[0][0])-((y-c[0][1])/1000.0))),c)
    g = Gnuplot.Gnuplot()
    g.plot(Gnuplot.Data(d,**kargs))
    return g

PacketList.timeskew_graph = new.instancemethod(_packetlist_timeskew_graph, None, PacketList)


### Create a new packet list
class TracerouteResult(SndRcvList):
    def __init__(self, res=None, name="Traceroute", stats=None):
        PacketList.__init__(self, res, name, stats)
        self.graphdef = None
        self.graphASres = 0
        self.padding = 0
        self.hloc = None
        self.nloc = None

    def show(self):
        return self.make_table(lambda (s,r): (s.sprintf("%IP.dst%:{TCP:tcp%ir,TCP.dport%}{UDP:udp%ir,UDP.dport%}{ICMP:ICMP}"),
                                              s.ttl,
                                              r.sprintf("%-15s,IP.src% {TCP:%TCP.flags%}{ICMP:%ir,ICMP.type%}")))


    def get_trace(self):
        trace = {}
        for s,r in self.res:
            if IP not in s:
                continue
            d = s[IP].dst
            if d not in trace:
                trace[d] = {}
            trace[d][s[IP].ttl] = r[IP].src, ICMP not in r
        for k in trace.values():
            m = filter(lambda x:k[x][1], k.keys())
            if not m:
                continue
            m = min(m)
            for l in k.keys():
                if l > m:
                    del(k[l])
        return trace

    def trace3D(self):
        """Give a 3D representation of the traceroute.
        right button: rotate the scene
        middle button: zoom
        left button: move the scene
        left button on a ball: toggle IP displaying
        ctrl-left button on a ball: scan ports 21,22,23,25,80 and 443 and display the result"""
        trace = self.get_trace()
        import visual

        class IPsphere(visual.sphere):
            def __init__(self, ip, **kargs):
                visual.sphere.__init__(self, **kargs)
                self.ip=ip
                self.label=None
                self.setlabel(self.ip)
            def setlabel(self, txt,visible=None):
                if self.label is not None:
                    if visible is None:
                        visible = self.label.visible
                    self.label.visible = 0
                elif visible is None:
                    visible=0
                self.label=visual.label(text=txt, pos=self.pos, space=self.radius, xoffset=10, yoffset=20, visible=visible)
            def action(self):
                self.label.visible ^= 1

        visual.scene = visual.display()
        visual.scene.exit_on_close(0)
        start = visual.box()
        rings={}
        tr3d = {}
        for i in trace:
            tr = trace[i]
            tr3d[i] = []
            ttl = tr.keys()
            for t in range(1,max(ttl)+1):
                if t not in rings:
                    rings[t] = []
                if t in tr:
                    if tr[t] not in rings[t]:
                        rings[t].append(tr[t])
                    tr3d[i].append(rings[t].index(tr[t]))
                else:
                    rings[t].append(("unk",-1))
                    tr3d[i].append(len(rings[t])-1)
        for t in rings:
            r = rings[t]
            l = len(r)
            for i in range(l):
                if r[i][1] == -1:
                    col = (0.75,0.75,0.75)
                elif r[i][1]:
                    col = visual.color.green
                else:
                    col = visual.color.blue
                
                s = IPsphere(pos=((l-1)*visual.cos(2*i*visual.pi/l),(l-1)*visual.sin(2*i*visual.pi/l),2*t),
                             ip = r[i][0],
                             color = col)
                for trlst in tr3d.values():
                    if t <= len(trlst):
                        if trlst[t-1] == i:
                            trlst[t-1] = s
        forecol = colgen(0.625, 0.4375, 0.25, 0.125)
        for trlst in tr3d.values():
            col = forecol.next()
            start = (0,0,0)
            for ip in trlst:
                visual.cylinder(pos=start,axis=ip.pos-start,color=col,radius=0.2)
                start = ip.pos
        
        movcenter=None
        while 1:
            if visual.scene.kb.keys:
                k = visual.scene.kb.getkey()
                if k == "esc" or k == "q":
                    break
            if visual.scene.mouse.events:
                ev = visual.scene.mouse.getevent()
                if ev.press == "left":
                    o = ev.pick
                    if o:
                        if ev.ctrl:
                            if o.ip == "unk":
                                continue
                            savcolor = o.color
                            o.color = (1,0,0)
                            a,b=sr(IP(dst=o.ip)/TCP(dport=[21,22,23,25,80,443]),timeout=2)
                            o.color = savcolor
                            if len(a) == 0:
                                txt = "%s:\nno results" % o.ip
                            else:
                                txt = "%s:\n" % o.ip
                                for s,r in a:
                                    txt += r.sprintf("{TCP:%IP.src%:%TCP.sport% %TCP.flags%}{TCPerror:%IPerror.dst%:%TCPerror.dport% %IP.src% %ir,ICMP.type%}\n")
                            o.setlabel(txt, visible=1)
                        else:
                            if hasattr(o, "action"):
                                o.action()
                elif ev.drag == "left":
                    movcenter = ev.pos
                elif ev.drop == "left":
                    movcenter = None
            if movcenter:
                visual.scene.center -= visual.scene.mouse.pos-movcenter
                movcenter = visual.scene.mouse.pos
                
                
    def world_trace(self):
        from modules.geo import locate_ip
        ips = {}
        rt = {}
        ports_done = {}
        for s,r in self.res:
            ips[r.src] = None
            if s.haslayer(TCP) or s.haslayer(UDP):
                trace_id = (s.src,s.dst,s.proto,s.dport)
            elif s.haslayer(ICMP):
                trace_id = (s.src,s.dst,s.proto,s.type)
            else:
                trace_id = (s.src,s.dst,s.proto,0)
            trace = rt.get(trace_id,{})
            if not r.haslayer(ICMP) or r.type != 11:
                if ports_done.has_key(trace_id):
                    continue
                ports_done[trace_id] = None
            trace[s.ttl] = r.src
            rt[trace_id] = trace

        trt = {}
        for trace_id in rt:
            trace = rt[trace_id]
            loctrace = []
            for i in range(max(trace.keys())):
                ip = trace.get(i,None)
                if ip is None:
                    continue
                loc = locate_ip(ip)
                if loc is None:
                    continue
#                loctrace.append((ip,loc)) # no labels yet
                loctrace.append(loc)
            if loctrace:
                trt[trace_id] = loctrace

        tr = map(lambda x: Gnuplot.Data(x,with_="lines"), trt.values())
        g = Gnuplot.Gnuplot()
        world = Gnuplot.File(conf.gnuplot_world,with_="lines")
        g.plot(world,*tr)
        return g

    def make_graph(self,ASres=None,padding=0):
        if ASres is None:
            ASres = conf.AS_resolver
        self.graphASres = ASres
        self.graphpadding = padding
        ips = {}
        rt = {}
        ports = {}
        ports_done = {}
        for s,r in self.res:
            r = r.getlayer(IP) or (conf.ipv6_enabled and r[scapy.layers.inet6.IPv6]) or r
            s = s.getlayer(IP) or (conf.ipv6_enabled and s[scapy.layers.inet6.IPv6]) or s
            ips[r.src] = None
            if TCP in s:
                trace_id = (s.src,s.dst,6,s.dport)
            elif UDP in s:
                trace_id = (s.src,s.dst,17,s.dport)
            elif ICMP in s:
                trace_id = (s.src,s.dst,1,s.type)
            else:
                trace_id = (s.src,s.dst,s.proto,0)
            trace = rt.get(trace_id,{})
            ttl = conf.ipv6_enabled and scapy.layers.inet6.IPv6 in s and s.hlim or s.ttl
            if not (ICMP in r and r[ICMP].type == 11) and not (conf.ipv6_enabled and scapy.layers.inet6.IPv6 in r and ICMPv6TimeExceeded in r):
                if trace_id in ports_done:
                    continue
                ports_done[trace_id] = None
                p = ports.get(r.src,[])
                if TCP in r:
                    p.append(r.sprintf("<T%ir,TCP.sport%> %TCP.sport% %TCP.flags%"))
                    trace[ttl] = r.sprintf('"%r,src%":T%ir,TCP.sport%')
                elif UDP in r:
                    p.append(r.sprintf("<U%ir,UDP.sport%> %UDP.sport%"))
                    trace[ttl] = r.sprintf('"%r,src%":U%ir,UDP.sport%')
                elif ICMP in r:
                    p.append(r.sprintf("<I%ir,ICMP.type%> ICMP %ICMP.type%"))
                    trace[ttl] = r.sprintf('"%r,src%":I%ir,ICMP.type%')
                else:
                    p.append(r.sprintf("{IP:<P%ir,proto%> IP %proto%}{IPv6:<P%ir,nh%> IPv6 %nh%}"))
                    trace[ttl] = r.sprintf('"%r,src%":{IP:P%ir,proto%}{IPv6:P%ir,nh%}')
                ports[r.src] = p
            else:
                trace[ttl] = r.sprintf('"%r,src%"')
            rt[trace_id] = trace
    
        # Fill holes with unk%i nodes
        unknown_label = incremental_label("unk%i")
        blackholes = []
        bhip = {}
        for rtk in rt:
            trace = rt[rtk]
            k = trace.keys()
            for n in range(min(k), max(k)):
                if not trace.has_key(n):
                    trace[n] = unknown_label.next()
            if not ports_done.has_key(rtk):
                if rtk[2] == 1: #ICMP
                    bh = "%s %i/icmp" % (rtk[1],rtk[3])
                elif rtk[2] == 6: #TCP
                    bh = "%s %i/tcp" % (rtk[1],rtk[3])
                elif rtk[2] == 17: #UDP                    
                    bh = '%s %i/udp' % (rtk[1],rtk[3])
                else:
                    bh = '%s %i/proto' % (rtk[1],rtk[2]) 
                ips[bh] = None
                bhip[rtk[1]] = bh
                bh = '"%s"' % bh
                trace[max(k)+1] = bh
                blackholes.append(bh)
    
        # Find AS numbers
        ASN_query_list = dict.fromkeys(map(lambda x:x.rsplit(" ",1)[0],ips)).keys()
        if ASres is None:            
            ASNlist = []
        else:
            ASNlist = ASres.resolve(*ASN_query_list)            
    
        ASNs = {}
        ASDs = {}
        for ip,asn,desc, in ASNlist:
            if asn is None:
                continue
            iplist = ASNs.get(asn,[])
            if ip in bhip:
                if ip in ports:
                    iplist.append(ip)
                iplist.append(bhip[ip])
            else:
                iplist.append(ip)
            ASNs[asn] = iplist
            ASDs[asn] = desc
    
    
        backcolorlist=colgen("60","86","ba","ff")
        forecolorlist=colgen("a0","70","40","20")
    
        s = "digraph trace {\n"
    
        s += "\n\tnode [shape=ellipse,color=black,style=solid];\n\n"
    
        s += "\n#ASN clustering\n"
        for asn in ASNs:
            s += '\tsubgraph cluster_%s {\n' % asn
            col = backcolorlist.next()
            s += '\t\tcolor="#%s%s%s";' % col
            s += '\t\tnode [fillcolor="#%s%s%s",style=filled];' % col
            s += '\t\tfontsize = 10;'
            s += '\t\tlabel = "%s\\n[%s]"\n' % (asn,ASDs[asn])
            for ip in ASNs[asn]:
    
                s += '\t\t"%s";\n'%ip
            s += "\t}\n"
    
    
    
    
        s += "#endpoints\n"
        for p in ports:
            s += '\t"%s" [shape=record,color=black,fillcolor=green,style=filled,label="%s|%s"];\n' % (p,p,"|".join(ports[p]))
    
        s += "\n#Blackholes\n"
        for bh in blackholes:
            s += '\t%s [shape=octagon,color=black,fillcolor=red,style=filled];\n' % bh

        if padding:
            s += "\n#Padding\n"
            pad={}
            for snd,rcv in self.res:
                if rcv.src not in ports and rcv.haslayer(Padding):
                    p = rcv.getlayer(Padding).load
                    if p != "\x00"*len(p):
                        pad[rcv.src]=None
            for rcv in pad:
                s += '\t"%s" [shape=triangle,color=black,fillcolor=red,style=filled];\n' % rcv
    
    
            
        s += "\n\tnode [shape=ellipse,color=black,style=solid];\n\n"
    
    
        for rtk in rt:
            s += "#---[%s\n" % `rtk`
            s += '\t\tedge [color="#%s%s%s"];\n' % forecolorlist.next()
            trace = rt[rtk]
            k = trace.keys()
            for n in range(min(k), max(k)):
                s += '\t%s ->\n' % trace[n]
            s += '\t%s;\n' % trace[max(k)]
    
        s += "}\n";
        self.graphdef = s
    
    def graph(self, ASres=None, padding=0, **kargs):
        """x.graph(ASres=conf.AS_resolver, other args):
        ASres=None          : no AS resolver => no clustering
        ASres=AS_resolver() : default whois AS resolver (riswhois.ripe.net)
        ASres=AS_resolver_cymru(): use whois.cymru.com whois database
        ASres=AS_resolver(server="whois.ra.net")
        type: output type (svg, ps, gif, jpg, etc.), passed to dot's "-T" option
        target: filename or redirect. Defaults pipe to Imagemagick's display program
        prog: which graphviz program to use"""
        if ASres is None:
            ASres = conf.AS_resolver
        if (self.graphdef is None or
            self.graphASres != ASres or
            self.graphpadding != padding):
            self.make_graph(ASres,padding)

        return do_graph(self.graphdef, **kargs)



@conf.commands.register
def traceroute(target, dport=80, minttl=1, maxttl=30, sport=RandShort(), l4 = None, filter=None, timeout=2, verbose=None, **kargs):
    """Instant TCP traceroute
traceroute(target, [maxttl=30,] [dport=80,] [sport=80,] [verbose=conf.verb]) -> None
"""
    if verbose is None:
        verbose = conf.verb
    if filter is None:
        # we only consider ICMP error packets and TCP packets with at
        # least the ACK flag set *and* either the SYN or the RST flag
        # set
        filter="(icmp and (icmp[0]=3 or icmp[0]=4 or icmp[0]=5 or icmp[0]=11 or icmp[0]=12)) or (tcp and (tcp[13] & 0x16 > 0x10))"
    if l4 is None:
        a,b = sr(IP(dst=target, id=RandShort(), ttl=(minttl,maxttl))/TCP(seq=RandInt(),sport=sport, dport=dport),
                 timeout=timeout, filter=filter, verbose=verbose, **kargs)
    else:
        # this should always work
        filter="ip"
        a,b = sr(IP(dst=target, id=RandShort(), ttl=(minttl,maxttl))/l4,
                 timeout=timeout, filter=filter, verbose=verbose, **kargs)

    a = TracerouteResult(a.res)
    if verbose:
        a.show()
    return a,b



#############################
## Simple TCP client stack ##
#############################

class TCP_client(Automaton):
    
    def parse_args(self, ip, port, *args, **kargs):
        self.dst = iter(Net(ip)).next()
        self.dport = port
        self.sport = random.randrange(0,2**16)
        self.l4 = IP(dst=ip)/TCP(sport=self.sport, dport=self.dport, flags=0,
                                 seq=random.randrange(0,2**32))
        self.src = self.l4.src
        self.swin=self.l4[TCP].window
        self.dwin=1
        self.rcvbuf=""
        bpf = "host %s  and host %s and port %i and port %i" % (self.src,
                                                                self.dst,
                                                                self.sport,
                                                                self.dport)

#        bpf=None
        Automaton.parse_args(self, filter=bpf, **kargs)

    
    def master_filter(self, pkt):
        return (IP in pkt and
                pkt[IP].src == self.dst and
                pkt[IP].dst == self.src and
                TCP in pkt and
                pkt[TCP].sport == self.dport and
                pkt[TCP].dport == self.sport and
                self.l4[TCP].seq >= pkt[TCP].ack and # XXX: seq/ack 2^32 wrap up
                ((self.l4[TCP].ack == 0) or (self.l4[TCP].ack <= pkt[TCP].seq <= self.l4[TCP].ack+self.swin)) )


    @ATMT.state(initial=1)
    def START(self):
        pass

    @ATMT.state()
    def SYN_SENT(self):
        pass
    
    @ATMT.state()
    def ESTABLISHED(self):
        pass

    @ATMT.state()
    def LAST_ACK(self):
        pass

    @ATMT.state(final=1)
    def CLOSED(self):
        pass

    
    @ATMT.condition(START)
    def connect(self):
        raise self.SYN_SENT()
    @ATMT.action(connect)
    def send_syn(self):
        self.l4[TCP].flags = "S"
        self.send(self.l4)
        self.l4[TCP].seq += 1


    @ATMT.receive_condition(SYN_SENT)
    def synack_received(self, pkt):
        if pkt[TCP].flags & 0x3f == 0x12:
            raise self.ESTABLISHED().action_parameters(pkt)
    @ATMT.action(synack_received)
    def send_ack_of_synack(self, pkt):
        self.l4[TCP].ack = pkt[TCP].seq+1
        self.l4[TCP].flags = "A"
        self.send(self.l4)

    @ATMT.receive_condition(ESTABLISHED)
    def incoming_data_received(self, pkt):
        if not isinstance(pkt[TCP].payload, NoPayload) and not isinstance(pkt[TCP].payload, Padding):
            raise self.ESTABLISHED().action_parameters(pkt)
    @ATMT.action(incoming_data_received)
    def receive_data(self,pkt):
        data = str(pkt[TCP].payload)
        if data and self.l4[TCP].ack == pkt[TCP].seq:
            self.l4[TCP].ack += len(data)
            self.l4[TCP].flags = "A"
            self.send(self.l4)
            self.rcvbuf += data
            if pkt[TCP].flags & 8 != 0: #PUSH
                self.oi.tcp.send(self.rcvbuf)
                self.rcvbuf = ""
    
    @ATMT.ioevent(ESTABLISHED,name="tcp", as_supersocket="tcplink")
    def outgoing_data_received(self, fd):
        raise self.ESTABLISHED().action_parameters(fd.recv())
    @ATMT.action(outgoing_data_received)
    def send_data(self, d):
        self.l4[TCP].flags = "PA"
        self.send(self.l4/d)
        self.l4[TCP].seq += len(d)
        
    
    @ATMT.receive_condition(ESTABLISHED)
    def reset_received(self, pkt):
        if pkt[TCP].flags & 4 != 0:
            raise self.CLOSED()

    @ATMT.receive_condition(ESTABLISHED)
    def fin_received(self, pkt):
        if pkt[TCP].flags & 0x1 == 1:
            raise self.LAST_ACK().action_parameters(pkt)
    @ATMT.action(fin_received)
    def send_finack(self, pkt):
        self.l4[TCP].flags = "FA"
        self.l4[TCP].ack = pkt[TCP].seq+1
        self.send(self.l4)
        self.l4[TCP].seq += 1

    @ATMT.receive_condition(LAST_ACK)
    def ack_of_fin_received(self, pkt):
        if pkt[TCP].flags & 0x3f == 0x10:
            raise self.CLOSED()




#####################
## Reporting stuff ##
#####################

def report_ports(target, ports):
    """portscan a target and output a LaTeX table
report_ports(target, ports) -> string"""
    ans,unans = sr(IP(dst=target)/TCP(dport=ports),timeout=5)
    rep = "\\begin{tabular}{|r|l|l|}\n\\hline\n"
    for s,r in ans:
        if not r.haslayer(ICMP):
            if r.payload.flags == 0x12:
                rep += r.sprintf("%TCP.sport% & open & SA \\\\\n")
    rep += "\\hline\n"
    for s,r in ans:
        if r.haslayer(ICMP):
            rep += r.sprintf("%TCPerror.dport% & closed & ICMP type %ICMP.type%/%ICMP.code% from %IP.src% \\\\\n")
        elif r.payload.flags != 0x12:
            rep += r.sprintf("%TCP.sport% & closed & TCP %TCP.flags% \\\\\n")
    rep += "\\hline\n"
    for i in unans:
        rep += i.sprintf("%TCP.dport% & ? & unanswered \\\\\n")
    rep += "\\hline\n\\end{tabular}\n"
    return rep



def IPID_count(lst, funcID=lambda x:x[1].id, funcpres=lambda x:x[1].summary()):
    idlst = map(funcID, lst)
    idlst.sort()
    classes = [idlst[0]]+map(lambda x:x[1],filter(lambda (x,y): abs(x-y)>50, map(lambda x,y: (x,y),idlst[:-1], idlst[1:])))
    lst = map(lambda x:(funcID(x), funcpres(x)), lst)
    lst.sort()
    print "Probably %i classes:" % len(classes), classes
    for id,pr in lst:
        print "%5i" % id, pr
    
    
def fragleak(target,sport=123, dport=123, timeout=0.2, onlyasc=0):
    load = "XXXXYYYYYYYYYY"
#    getmacbyip(target)
#    pkt = IP(dst=target, id=RandShort(), options="\x22"*40)/UDP()/load
    pkt = IP(dst=target, id=RandShort(), options="\x00"*40, flags=1)/UDP(sport=sport, dport=sport)/load
    s=conf.L3socket()
    intr=0
    found={}
    try:
        while 1:
            try:
                if not intr:
                    s.send(pkt)
                sin,sout,serr = select([s],[],[],timeout)
                if not sin:
                    continue
                ans=s.recv(1600)
                if not isinstance(ans, IP): #TODO: IPv6
                    continue
                if not isinstance(ans.payload, ICMP):
                    continue
                if not isinstance(ans.payload.payload, IPerror):
                    continue
                if ans.payload.payload.dst != target:
                    continue
                if ans.src  != target:
                    print "leak from", ans.src,


#                print repr(ans)
                if not ans.haslayer(Padding):
                    continue

                
#                print repr(ans.payload.payload.payload.payload)
                
#                if not isinstance(ans.payload.payload.payload.payload, Raw):
#                    continue
#                leak = ans.payload.payload.payload.payload.load[len(load):]
                leak = ans.getlayer(Padding).load
                if leak not in found:
                    found[leak]=None
                    linehexdump(leak, onlyasc=onlyasc)
            except KeyboardInterrupt:
                if intr:
                    raise
                intr=1
    except KeyboardInterrupt:
        pass

def fragleak2(target, timeout=0.4, onlyasc=0):
    found={}
    try:
        while 1:
            p = sr1(IP(dst=target, options="\x00"*40, proto=200)/"XXXXYYYYYYYYYYYY",timeout=timeout,verbose=0)
            if not p:
                continue
            if Padding in p:
                leak  = p[Padding].load
                if leak not in found:
                    found[leak]=None
                    linehexdump(leak,onlyasc=onlyasc)
    except:
        pass
    

conf.stats_classic_protocols += [TCP,UDP,ICMP]
conf.stats_dot11_protocols += [TCP,UDP,ICMP]

if conf.ipv6_enabled:
    import scapy.layers.inet6

########NEW FILE########
__FILENAME__ = inet6
#! /usr/bin/env python
#############################################################################
##                                                                         ##
## inet6.py --- IPv6 support for Scapy                                     ##
##              see http://natisbad.org/IPv6/                              ##
##              for more informations                                      ##
##                                                                         ##
## Copyright (C) 2005  Guillaume Valadon <guedou@hongo.wide.ad.jp>         ##
##                     Arnaud Ebalard <arnaud.ebalard@eads.net>            ##
##                                                                         ##
## This program is free software; you can redistribute it and/or modify it ##
## under the terms of the GNU General Public License version 2 as          ##
## published by the Free Software Foundation.                              ##
##                                                                         ##
## This program is distributed in the hope that it will be useful, but     ##
## WITHOUT ANY WARRANTY; without even the implied warranty of              ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU       ##
## General Public License for more details.                                ##
##                                                                         ##
#############################################################################

"""
IPv6 (Internet Protocol v6).
"""


import socket
if not socket.has_ipv6:
    raise socket.error("can't use AF_INET6, IPv6 is disabled")
if not hasattr(socket, "IPPROTO_IPV6"):
    # Workaround for http://bugs.python.org/issue6926
    socket.IPPROTO_IPV6 = 41

from scapy.config import conf
from scapy.layers.l2 import *
from scapy.layers.inet import *
from scapy.fields import *
from scapy.packet import *
from scapy.volatile import *
from scapy.sendrecv import sr,sr1,srp1
from scapy.as_resolvers import AS_resolver_riswhois
from scapy.supersocket import SuperSocket,L3RawSocket
from scapy.arch import *
from scapy.utils6 import *


#############################################################################
# Helpers                                                                  ##
#############################################################################

def get_cls(name, fallback_cls):
    return globals().get(name, fallback_cls)


##########################
## Neighbor cache stuff ##
##########################

conf.netcache.new_cache("in6_neighbor", 120)

def neighsol(addr, src, iface, timeout=1, chainCC=0):
    """
    Sends an ICMPv6 Neighbor Solicitation message to get the MAC address
    of the neighbor with specified IPv6 address addr. 'src' address is 
    used as source of the message. Message is sent on iface. By default,
    timeout waiting for an answer is 1 second.

    If no answer is gathered, None is returned. Else, the answer is 
    returned (ethernet frame).
    """

    nsma = in6_getnsma(inet_pton(socket.AF_INET6, addr))
    d = inet_ntop(socket.AF_INET6, nsma)
    dm = in6_getnsmac(nsma)
    p = Ether(dst=dm)/IPv6(dst=d, src=src, hlim=255)
    p /= ICMPv6ND_NS(tgt=addr)
    p /= ICMPv6NDOptSrcLLAddr(lladdr=get_if_hwaddr(iface))
    res = srp1(p,type=ETH_P_IPV6, iface=iface, timeout=1, verbose=0, 
               chainCC=chainCC)    

    return res

def getmacbyip6(ip6, chainCC=0):
    """
    Returns the mac address to be used for provided 'ip6' peer. 
    neighborCache.get() method is used on instantiated neighbor cache.
    Resolution mechanism is described in associated doc string.

    (chainCC parameter value ends up being passed to sending function
     used to perform the resolution, if needed)
    """

    if in6_ismaddr(ip6): # Multicast 
        mac = in6_getnsmac(inet_pton(socket.AF_INET6, ip6))
        return mac

    iff,a,nh = conf.route6.route(ip6, dev=conf.iface6)

    if iff == LOOPBACK_NAME:
        return "ff:ff:ff:ff:ff:ff"

    if nh != '::': 
        ip6 = nh # Found next hop

    mac = conf.netcache.in6_neighbor.get(ip6)
    if mac:
        return mac

    res = neighsol(ip6, a, iff, chainCC=chainCC)

    if res is not None:
        mac = res.src
        conf.netcache.in6_neighbor[ip6] = mac
        return mac

    return None


#############################################################################
#############################################################################
###              IPv6 addresses manipulation routines                     ###
#############################################################################
#############################################################################

class Net6(Gen): # syntax ex. fec0::/126
    """Generate a list of IPv6s from a network address or a name"""
    name = "ipv6"
    ipaddress = re.compile(r"^([a-fA-F0-9:]+)(/[1]?[0-3]?[0-9])?$")

    def __init__(self, net):
        self.repr = net

        tmp = net.split('/')+["128"]
        if not self.ipaddress.match(net):
            tmp[0]=socket.getaddrinfo(tmp[0], None, socket.AF_INET6)[0][-1][0]

        netmask = int(tmp[1])
        self.net = inet_pton(socket.AF_INET6, tmp[0])
        self.mask = in6_cidr2mask(netmask)
        self.plen = netmask

    def __iter__(self):
        def m8(i):
            if i % 8 == 0:
                return i
        tuple = filter(lambda x: m8(x), xrange(8, 129))

        a = in6_and(self.net, self.mask)
        tmp = map(lambda x:  x, struct.unpack('16B', a))
   
        def parse_digit(a, netmask):
            netmask = min(8,max(netmask,0))
            a = (int(a) & (0xffL<<netmask),(int(a) | (0xffL>>(8-netmask)))+1)
            return a
        self.parsed = map(lambda x,y: parse_digit(x,y), tmp, map(lambda x,nm=self.plen: x-nm, tuple))

        def rec(n, l): 
            if n and  n % 2 == 0:
                sep = ':'
            else:       
                sep = ''
            if n == 16:
                return l
            else:
                ll = []
                for i in xrange(*self.parsed[n]):
                    for y in l:
                        ll += [y+sep+'%.2x'%i]
                return rec(n+1, ll)

        return iter(rec(0, ['']))

    def __repr__(self):
        return "<Net6 %s>" % self.repr






#############################################################################
#############################################################################
###                              IPv6 Class                               ###
#############################################################################
#############################################################################

class IP6Field(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "16s")
    def h2i(self, pkt, x):
        if type(x) is str:
            try:
                x = in6_ptop(x)
            except socket.error:
                x = Net6(x)
        elif type(x) is list:
            x = map(Net6, x)
        return x
    def i2m(self, pkt, x):
        return inet_pton(socket.AF_INET6, x)
    def m2i(self, pkt, x):
        return inet_ntop(socket.AF_INET6, x)
    def any2i(self, pkt, x):
        return self.h2i(pkt,x)
    def i2repr(self, pkt, x):
        if x is None:
            return self.i2h(pkt,x)
        elif not isinstance(x, Net6) and not type(x) is list:
            if in6_isaddrTeredo(x):   # print Teredo info
                server, flag, maddr, mport = teredoAddrExtractInfo(x)     
                return "%s [Teredo srv: %s cli: %s:%s]" % (self.i2h(pkt, x), server, maddr,mport)
            elif in6_isaddr6to4(x):   # print encapsulated address
                vaddr = in6_6to4ExtractAddr(x)
                return "%s [6to4 GW: %s]" % (self.i2h(pkt, x), vaddr)
        return self.i2h(pkt, x)       # No specific information to return
    def randval(self):
        return RandIP6()

class SourceIP6Field(IP6Field):
    def __init__(self, name, dstname):
        IP6Field.__init__(self, name, None)
        self.dstname = dstname
    def i2m(self, pkt, x):
        if x is None:
            dst=getattr(pkt,self.dstname)
            iff,x,nh = conf.route6.route(dst)
        return IP6Field.i2m(self, pkt, x)
    def i2h(self, pkt, x):
        if x is None:
            dst=getattr(pkt,self.dstname)
            if isinstance(dst,Gen):
                r = map(conf.route6.route, dst)
                r.sort()
                if r[0] == r[-1]:
                    x=r[0][1]
                else:
                    warning("More than one possible route for %s"%repr(dst))
                    return None
            else:
                iff,x,nh = conf.route6.route(dst)
        return IP6Field.i2h(self, pkt, x)

ipv6nh = { 0:"Hop-by-Hop Option Header",
           4:"IP",
           6:"TCP",
          17:"UDP",
          41:"IPv6",
          43:"Routing Header",
          44:"Fragment Header",
          47:"GRE",
          50:"ESP Header",
          51:"AH Header",
          58:"ICMPv6",
          59:"No Next Header",
          60:"Destination Option Header",
         135:"Mobility Header"} 

ipv6nhcls = {  0: "IPv6ExtHdrHopByHop",
               4: "IP",
               6: "TCP",
               17: "UDP",
               43: "IPv6ExtHdrRouting",
               44: "IPv6ExtHdrFragment",
              #50: "IPv6ExtHrESP",
              #51: "IPv6ExtHdrAH",
               58: "ICMPv6Unknown", 
               59: "Raw",
               60: "IPv6ExtHdrDestOpt" }

class IP6ListField(StrField):
    islist = 1
    def __init__(self, name, default, count_from=None, length_from=None):
        if default is None:
            default = []
        StrField.__init__(self, name, default)
        self.count_from = count_from
        self.length_from = length_from

    def i2len(self, pkt, i):
        return 16*len(i)

    def i2count(self, pkt, i):
        if type(i) is list:
            return len(i)
        return 0
    
    def getfield(self, pkt, s):
        c = l = None
        if self.length_from is not None:
            l = self.length_from(pkt)
        elif self.count_from is not None:
            c = self.count_from(pkt)
            
        lst = []
        ret = ""
        remain = s
        if l is not None:
            remain,ret = s[:l],s[l:]
        while remain:
            if c is not None:
                if c <= 0:
                    break
                c -= 1
            addr = inet_ntop(socket.AF_INET6, remain[:16])
            lst.append(addr)
            remain = remain[16:]
        return remain+ret,lst

    def i2m(self, pkt, x):
        s = ''
        for y in x:
            try:
                y = inet_pton(socket.AF_INET6, y)
            except:
                y = socket.getaddrinfo(y, None, socket.AF_INET6)[0][-1][0]
                y = inet_pton(socket.AF_INET6, y)
            s += y
        return s

    def i2repr(self,pkt,x):
        s = []
        if x == None:
            return "[]"
        for y in x:
            s.append('%s' % y)
        return "[ %s ]" % (", ".join(s))
        
class _IPv6GuessPayload:        
    name = "Dummy class that implements guess_payload_class() for IPv6"
    def default_payload_class(self,p):
        if self.nh == 58 and len(p) > 2:
            t = ord(p[0])
            if t == 139 or t == 140: # Node Info Query 
                return _niquery_guesser(p)
            return get_cls(icmp6typescls.get(t,"Raw"), "Raw")
        elif self.nh == 135 and len(p) > 3:
            return _mip6_mhtype2cls.get(ord(p[2]), MIP6MH_Generic)
        else:
            return get_cls(ipv6nhcls.get(self.nh,"Raw"), "Raw")

class IPv6(_IPv6GuessPayload, Packet, IPTools):
    name = "IPv6"
    fields_desc = [ BitField("version" , 6 , 4),
                    BitField("tc", 0, 8), #TODO: IPv6, ByteField ?
                    BitField("fl", 0, 20),
                    ShortField("plen", None),
                    ByteEnumField("nh", 59, ipv6nh),
                    ByteField("hlim", 64),
                    SourceIP6Field("src", "dst"), # dst is for src @ selection
                    IP6Field("dst", "::1") ]

    def route(self):
        dst = self.dst
        if isinstance(dst,Gen):
            dst = iter(dst).next()
        return conf.route6.route(dst)

    def mysummary(self):
        return "%s > %s (%i)" % (self.src,self.dst, self.nh)

    def post_build(self, p, pay):
        p += pay
        if self.plen is None:
            l = len(p) - 40
            p = p[:4]+struct.pack("!H", l)+p[6:]
        return p

    def extract_padding(self, s):
        l = self.plen
        return s[:l], s[l:]

    def hashret(self):
        if self.nh == 58 and isinstance(self.payload, _ICMPv6):
            if self.payload.type < 128:
                return self.payload.payload.hashret()
            elif (self.payload.type in [133,134,135,136,144,145]):
                return struct.pack("B", self.nh)+self.payload.hashret()

        nh = self.nh
        sd = self.dst
        ss = self.src
        if self.nh == 43 and isinstance(self.payload, IPv6ExtHdrRouting):
            # With routing header, the destination is the last 
            # address of the IPv6 list if segleft > 0 
            nh = self.payload.nh
            try:
                sd = self.addresses[-1]
            except IndexError:
                sd = '::1'
            # TODO: big bug with ICMPv6 error messages as the destination of IPerror6
            #       could be anything from the original list ...
            if 1:
                sd = inet_pton(socket.AF_INET6, sd)
                for a in self.addresses:
                    a = inet_pton(socket.AF_INET6, a)
                    sd = strxor(sd, a)
                sd = inet_ntop(socket.AF_INET6, sd)

        if self.nh == 44 and isinstance(self.payload, IPv6ExtHdrFragment):
            nh = self.payload.nh 

        if self.nh == 0 and isinstance(self.payload, IPv6ExtHdrHopByHop):
            nh = self.payload.nh 

        if self.nh == 60 and isinstance(self.payload, IPv6ExtHdrDestOpt):
            foundhao = None
            for o in self.payload.options:
                if isinstance(o, HAO):
                    foundhao = o
            if foundhao:
                nh = self.payload.nh # XXX what if another extension follows ?
                ss = foundhao.hoa

        if conf.checkIPsrc and conf.checkIPaddr:
            sd = inet_pton(socket.AF_INET6, sd)
            ss = inet_pton(socket.AF_INET6, self.src)
            return struct.pack("B",nh)+self.payload.hashret()
        else:
            return struct.pack("B", nh)+self.payload.hashret()

    def answers(self, other):
        if not isinstance(other, IPv6): # self is reply, other is request
            return False
        if conf.checkIPaddr: 
            ss = inet_pton(socket.AF_INET6, self.src)
            sd = inet_pton(socket.AF_INET6, self.dst)
            os = inet_pton(socket.AF_INET6, other.src)
            od = inet_pton(socket.AF_INET6, other.dst)
            # request was sent to a multicast address (other.dst)
            # Check reply destination addr matches request source addr (i.e 
            # sd == os) except when reply is multicasted too
            # XXX test mcast scope matching ?
            if in6_ismaddr(other.dst):
                if in6_ismaddr(self.dst):
                    if ((od == sd) or 
                        (in6_isaddrllallnodes(self.dst) and in6_isaddrllallservers(other.dst))):
                         return self.payload.answers(other.payload)
                    return False
                if (os == sd): 
                    return self.payload.answers(other.payload)
                return False
            elif (sd != os): # or ss != od): <- removed for ICMP errors 
                return False
        if self.nh == 58 and isinstance(self.payload, _ICMPv6) and self.payload.type < 128:
            # ICMPv6 Error message -> generated by IPv6 packet
            # Note : at the moment, we jump the ICMPv6 specific class
            # to call answers() method of erroneous packet (over
            # initial packet). There can be cases where an ICMPv6 error
            # class could implement a specific answers method that perform
            # a specific task. Currently, don't see any use ...
            return self.payload.payload.answers(other)
        elif other.nh == 0 and isinstance(other.payload, IPv6ExtHdrHopByHop):
            return self.payload.answers(other.payload.payload) 
        elif other.nh == 44 and isinstance(other.payload, IPv6ExtHdrFragment):
            return self.payload.answers(other.payload.payload) 
        elif other.nh == 43 and isinstance(other.payload, IPv6ExtHdrRouting):
            return self.payload.answers(other.payload.payload) # Buggy if self.payload is a IPv6ExtHdrRouting
        elif other.nh == 60 and isinstance(other.payload, IPv6ExtHdrDestOpt):
            return self.payload.payload.answers(other.payload.payload)
        elif self.nh == 60 and isinstance(self.payload, IPv6ExtHdrDestOpt): # BU in reply to BRR, for instance
            return self.payload.payload.answers(other.payload)
        else:
            if (self.nh != other.nh):
                return False
            return self.payload.answers(other.payload)


conf.neighbor.register_l3(Ether, IPv6, lambda l2,l3: getmacbyip6(l3.dst))


class IPerror6(IPv6):
    name = "IPv6 in ICMPv6"
    def answers(self, other):
        if not isinstance(other, IPv6):
            return False
        sd = inet_pton(socket.AF_INET6, self.dst)
        ss = inet_pton(socket.AF_INET6, self.src)
        od = inet_pton(socket.AF_INET6, other.dst)
        os = inet_pton(socket.AF_INET6, other.src)

        # Make sure that the ICMPv6 error is related to the packet scapy sent
        if isinstance(self.underlayer, _ICMPv6) and self.underlayer.type < 128:
            
            # find upper layer for self (possible citation)
            selfup = self.payload
            while selfup is not None and isinstance(selfup, _IPv6ExtHdr):
                selfup = selfup.payload

            # find upper layer for other (initial packet). Also look for RH
            otherup = other.payload
            request_has_rh = False
            while otherup is not None and isinstance(otherup, _IPv6ExtHdr):
                if isinstance(otherup, IPv6ExtHdrRouting):
                    request_has_rh = True
                otherup = otherup.payload

            if ((ss == os and sd == od) or      # <- Basic case 
                (ss == os and request_has_rh)): # <- Request has a RH : 
                                                #    don't check dst address
            
                # Let's deal with possible MSS Clamping 
                if (isinstance(selfup, TCP) and 
                    isinstance(otherup, TCP) and
                    selfup.options != otherup.options): # seems clamped

                    # Save fields modified by MSS clamping 
                    old_otherup_opts    = otherup.options
                    old_otherup_cksum   = otherup.chksum
                    old_otherup_dataofs = otherup.dataofs
                    old_selfup_opts     = selfup.options
                    old_selfup_cksum    = selfup.chksum
                    old_selfup_dataofs  = selfup.dataofs

                    # Nullify them
                    otherup.options = []
                    otherup.chksum  = 0
                    otherup.dataofs = 0
                    selfup.options  = []
                    selfup.chksum   = 0
                    selfup.dataofs  = 0

                    # Test it and save result
                    s1 = str(selfup)
                    s2 = str(otherup)
                    l = min(len(s1), len(s2))
                    res = s1[:l] == s2[:l]

                    # recall saved values
                    otherup.options = old_otherup_opts
                    otherup.chksum  = old_otherup_cksum
                    otherup.dataofs = old_otherup_dataofs
                    selfup.options  = old_selfup_opts
                    selfup.chksum   = old_selfup_cksum
                    selfup.dataofs  = old_selfup_dataofs

                    return res

                s1 = str(selfup)
                s2 = str(otherup)
                l = min(len(s1), len(s2))
                return s1[:l] == s2[:l]

        return False
            
    def mysummary(self):
        return Packet.mysummary(self)


#############################################################################
#############################################################################
###                 Upper Layer Checksum computation                      ###
#############################################################################
#############################################################################

class PseudoIPv6(Packet): # IPv6 Pseudo-header for checksum computation
    name = "Pseudo IPv6 Header"
    fields_desc = [ IP6Field("src", "::"),
                    IP6Field("dst", "::"),
                    ShortField("uplen", None),
                    BitField("zero", 0, 24),
                    ByteField("nh", 0) ]  

def in6_chksum(nh, u, p):
    """
    Performs IPv6 Upper Layer checksum computation. Provided parameters are:

    - 'nh' : value of upper layer protocol 
    - 'u'  : upper layer instance (TCP, UDP, ICMPv6*, ). Instance must be 
             provided with all under layers (IPv6 and all extension headers, 
             for example)
    - 'p'  : the payload of the upper layer provided as a string

    Functions operate by filling a pseudo header class instance (PseudoIPv6)
    with
    - Next Header value
    - the address of _final_ destination (if some Routing Header with non
    segleft field is present in underlayer classes, last address is used.)
    - the address of _real_ source (basically the source address of an 
    IPv6 class instance available in the underlayer or the source address
    in HAO option if some Destination Option header found in underlayer
    includes this option).
    - the length is the length of provided payload string ('p')
    """

    ph6 = PseudoIPv6()
    ph6.nh = nh
    rthdr = 0
    hahdr = 0
    final_dest_addr_found = 0
    while u != None and not isinstance(u, IPv6):
        if (isinstance(u, IPv6ExtHdrRouting) and
            u.segleft != 0 and len(u.addresses) != 0 and
            final_dest_addr_found == 0):
            rthdr = u.addresses[-1]
            final_dest_addr_found = 1
        elif (isinstance(u, IPv6ExtHdrDestOpt) and (len(u.options) == 1) and
             isinstance(u.options[0], HAO)):
             hahdr  = u.options[0].hoa
        u = u.underlayer
    if u is None:  
        warning("No IPv6 underlayer to compute checksum. Leaving null.")
        return 0
    if hahdr:   
        ph6.src = hahdr
    else:
        ph6.src = u.src
    if rthdr:
        ph6.dst = rthdr
    else:
        ph6.dst = u.dst
    ph6.uplen = len(p)
    ph6s = str(ph6)
    return checksum(ph6s+p)


#############################################################################
#############################################################################
###                         Extension Headers                             ###
#############################################################################
#############################################################################


# Inherited by all extension header classes 
class _IPv6ExtHdr(_IPv6GuessPayload, Packet):
    name = 'Abstract IPV6 Option Header'
    aliastypes = [IPv6, IPerror6] # TODO ...


#################### IPv6 options for Extension Headers #####################

_hbhopts = { 0x00: "Pad1",
             0x01: "PadN",
             0x04: "Tunnel Encapsulation Limit",
             0x05: "Router Alert",
             0x06: "Quick-Start",
             0xc2: "Jumbo Payload",
             0xc9: "Home Address Option" }

class _OTypeField(ByteEnumField):
    """ 
    Modified BytEnumField that displays information regarding the IPv6 option
    based on its option type value (What should be done by nodes that process
    the option if they do not understand it ...)

    It is used by Jumbo, Pad1, PadN, RouterAlert, HAO options 
    """
    pol = {0x00: "00: skip",
           0x40: "01: discard",
           0x80: "10: discard+ICMP",
           0xC0: "11: discard+ICMP not mcast"}
    
    enroutechange = {0x00: "0: Don't change en-route",
                 0x20: "1: May change en-route" }

    def i2repr(self, pkt, x):
        s = self.i2s.get(x, repr(x))
        polstr = self.pol[(x & 0xC0)]
        enroutechangestr = self.enroutechange[(x & 0x20)]
        return "%s [%s, %s]" % (s, polstr, enroutechangestr)

class HBHOptUnknown(Packet): # IPv6 Hop-By-Hop Option
    name = "Scapy6 Unknown Option"
    fields_desc = [_OTypeField("otype", 0x01, _hbhopts), 
                   FieldLenField("optlen", None, length_of="optdata", fmt="B"),
                   StrLenField("optdata", "",
                               length_from = lambda pkt: pkt.optlen) ]    
    def alignment_delta(self, curpos): # By default, no alignment requirement
        """
        As specified in section 4.2 of RFC 2460, every options has 
        an alignment requirement ususally expressed xn+y, meaning 
        the Option Type must appear at an integer multiple of x octest 
        from the start of the header, plus y octet.
        
        That function is provided the current position from the
        start of the header and returns required padding length.
        """
        return 0

class Pad1(Packet): # IPv6 Hop-By-Hop Option
    name = "Pad1"
    fields_desc = [ _OTypeField("otype", 0x00, _hbhopts) ]
    def alignment_delta(self, curpos): # No alignment requirement
        return 0

class PadN(Packet): # IPv6 Hop-By-Hop Option
    name = "PadN" 
    fields_desc = [_OTypeField("otype", 0x01, _hbhopts),
                   FieldLenField("optlen", None, length_of="optdata", fmt="B"),
                   StrLenField("optdata", "",
                               length_from = lambda pkt: pkt.optlen)]
    def alignment_delta(self, curpos): # No alignment requirement
        return 0

class RouterAlert(Packet): # RFC 2711 - IPv6 Hop-By-Hop Option
    name = "Router Alert"
    fields_desc = [_OTypeField("otype", 0x05, _hbhopts),
                   ByteField("optlen", 2), 
                   ShortEnumField("value", None, 
                                  { 0: "Datagram contains a MLD message", 
                                    1: "Datagram contains RSVP message",
                                    2: "Datagram contains an Active Network message" }) ]
    # TODO : Check IANA has not defined new values for value field of RouterAlertOption
    # TODO : now that we have that option, we should do something in MLD class that need it
    def alignment_delta(self, curpos): # alignment requirement : 2n+0
        x = 2 ; y = 0
        delta = x*((curpos - y + x - 1)/x) + y - curpos 
        return delta

class Jumbo(Packet): # IPv6 Hop-By-Hop Option
    name = "Jumbo Payload" 
    fields_desc = [_OTypeField("otype", 0xC2, _hbhopts),
                   ByteField("optlen", 4),
                   IntField("jumboplen", None) ]
    def alignment_delta(self, curpos): # alignment requirement : 4n+2
        x = 4 ; y = 2
        delta = x*((curpos - y + x - 1)/x) + y - curpos 
        return delta

class HAO(Packet): # IPv6 Destination Options Header Option
    name = "Home Address Option"
    fields_desc = [_OTypeField("otype", 0xC9, _hbhopts),
                   ByteField("optlen", 16),
                   IP6Field("hoa", "::") ]
    def alignment_delta(self, curpos): # alignment requirement : 8n+6
        x = 8 ; y = 6
        delta = x*((curpos - y + x - 1)/x) + y - curpos 
        return delta

_hbhoptcls = { 0x00: Pad1,
               0x01: PadN,
               0x05: RouterAlert,
               0xC2: Jumbo,
               0xC9: HAO }


######################## Hop-by-Hop Extension Header ########################

class _HopByHopOptionsField(PacketListField):
    islist = 1
    holds_packet = 1
    def __init__(self, name, default, cls, curpos, count_from=None, length_from=None):
        self.curpos = curpos
        PacketListField.__init__(self, name, default, cls, count_from=count_from, length_from=length_from)
    
    def i2len(self, pkt, i):
        l = len(self.i2m(pkt, i))
        return l

    def i2count(self, pkt, i):
        if type(i) is list:
            return len(i)
        return 0

    def getfield(self, pkt, s):
        c = l = None
        if self.length_from is not None:
            l = self.length_from(pkt)
        elif self.count_from is not None:
            c = self.count_from(pkt)
            
        opt = []
        ret = ""
        x = s
        if l is not None:
            x,ret = s[:l],s[l:]
        while x:
            if c is not None:
                if c <= 0:
                    break
                c -= 1
            o = ord(x[0]) # Option type
            cls = self.cls
            if _hbhoptcls.has_key(o):
                cls = _hbhoptcls[o]
            try:
                op = cls(x)
            except:
                op = self.cls(x)
            opt.append(op)
            if isinstance(op.payload, Raw):
                x = op.payload.load
                del(op.payload)
            else:
                x = ""
        return x+ret,opt

    def i2m(self, pkt, x):
        autopad = None
        try:
            autopad = getattr(pkt, "autopad") # Hack : 'autopad' phantom field
        except:
            autopad = 1
            
        if not autopad:
            return "".join(map(str, x))

        curpos = self.curpos
        s = ""
        for p in x:
            d = p.alignment_delta(curpos)
            curpos += d
            if d == 1:
                s += str(Pad1())
            elif d != 0:
                s += str(PadN(optdata='\x00'*(d-2)))
            pstr = str(p)
            curpos += len(pstr)
            s += pstr
            
        # Let's make the class including our option field
        # a multiple of 8 octets long
        d = curpos % 8
        if d == 0:
            return s
        d = 8 - d
        if d == 1:
            s += str(Pad1())
        elif d != 0:
            s += str(PadN(optdata='\x00'*(d-2)))        

        return s

    def addfield(self, pkt, s, val):
        return s+self.i2m(pkt, val)

class _PhantomAutoPadField(ByteField):
    def addfield(self, pkt, s, val):
        return s

    def getfield(self, pkt, s):
        return s, 1

    def i2repr(self, pkt, x):
        if x:
            return "On"
        return "Off"


class IPv6ExtHdrHopByHop(_IPv6ExtHdr):    
    name = "IPv6 Extension Header - Hop-by-Hop Options Header"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    FieldLenField("len", None, length_of="options", fmt="B",
                                  adjust = lambda pkt,x: (x+2+7)/8 - 1), 
                    _PhantomAutoPadField("autopad", 1), # autopad activated by default
                    _HopByHopOptionsField("options", [], HBHOptUnknown, 2,
                                          length_from = lambda pkt: (8*(pkt.len+1))-2) ]
    overload_fields = {IPv6: { "nh": 0 }}


######################## Destination Option Header ##########################

class IPv6ExtHdrDestOpt(_IPv6ExtHdr):    
    name = "IPv6 Extension Header - Destination Options Header"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    FieldLenField("len", None, length_of="options", fmt="B",
                                  adjust = lambda pkt,x: (x+2+7)/8 - 1), 
                    _PhantomAutoPadField("autopad", 1), # autopad activated by default
                    _HopByHopOptionsField("options", [], HBHOptUnknown, 2,
                                          length_from = lambda pkt: (8*(pkt.len+1))-2) ]
    overload_fields = {IPv6: { "nh": 60 }}


############################# Routing Header ################################

class IPv6ExtHdrRouting(_IPv6ExtHdr):
    name = "IPv6 Option Header Routing"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    FieldLenField("len", None, count_of="addresses", fmt="B",
                                  adjust = lambda pkt,x:2*x), # in 8 bytes blocks
                    ByteField("type", 0),
                    ByteField("segleft", None),
                    BitField("reserved", 0, 32), # There is meaning in this field ...
                    IP6ListField("addresses", [],
                                 length_from = lambda pkt: 8*pkt.len)]
    overload_fields = {IPv6: { "nh": 43 }}

    def post_build(self, pkt, pay):
        if self.segleft is None:
            pkt = pkt[:3]+struct.pack("B", len(self.addresses))+pkt[4:]
        return _IPv6ExtHdr.post_build(self, pkt, pay)

########################### Fragmentation Header ############################

class IPv6ExtHdrFragment(_IPv6ExtHdr):            
    name = "IPv6 Extension Header - Fragmentation header"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    BitField("res1", 0, 8),
                    BitField("offset", 0, 13),
                    BitField("res2", 0, 2),
                    BitField("m", 0, 1),
                    IntField("id", None) ]
    overload_fields = {IPv6: { "nh": 44 }}


def defragment6(pktlist):
    """
    Performs defragmentation of a list of IPv6 packets. Packets are reordered.
    Crap is dropped. What lacks is completed by 'X' characters.
    """
    
    l = filter(lambda x: IPv6ExtHdrFragment in x, pktlist) # remove non fragments
    if not l:
        return []

    id = l[0][IPv6ExtHdrFragment].id 

    llen = len(l)
    l = filter(lambda x: x[IPv6ExtHdrFragment].id == id, l)
    if len(l) != llen:
        warning("defragment6: some fragmented packets have been removed from list")
    llen = len(l)

    # reorder fragments 
    i = 0 
    res = []
    while l:
        min_pos = 0
        min_offset  = l[0][IPv6ExtHdrFragment].offset
        for p in l:
            cur_offset = p[IPv6ExtHdrFragment].offset
            if cur_offset < min_offset:
                min_pos = 0
                min_offset  = cur_offset
        res.append(l[min_pos])
        del(l[min_pos])

    # regenerate the fragmentable part
    fragmentable = ""
    for p in res:
        q=p[IPv6ExtHdrFragment]
        offset = 8*q.offset
        if offset != len(fragmentable):
            warning("Expected an offset of %d. Found %d. Padding with XXXX" % (len(fragmentable), offset))
        fragmentable += "X"*(offset - len(fragmentable))
        fragmentable += str(q.payload)

    # Regenerate the unfragmentable part.
    q = res[0]
    nh = q[IPv6ExtHdrFragment].nh
    q[IPv6ExtHdrFragment].underlayer.nh = nh
    q[IPv6ExtHdrFragment].underlayer.payload = None
    q /= Raw(load=fragmentable)
    
    return IPv6(str(q))


def fragment6(pkt, fragSize):
    """
    Performs fragmentation of an IPv6 packet. Provided packet ('pkt') must already 
    contain an IPv6ExtHdrFragment() class. 'fragSize' argument is the expected
    maximum size of fragments (MTU). The list of packets is returned.

    If packet does not contain an IPv6ExtHdrFragment class, it is returned in
    result list.
    """

    pkt = pkt.copy()
    s = str(pkt) # for instantiation to get upper layer checksum right

    if len(s) <= fragSize:
        return [pkt]

    if not IPv6ExtHdrFragment in pkt:
        # TODO : automatically add a fragment before upper Layer
        #        at the moment, we do nothing and return initial packet
        #        as single element of a list
        return [pkt]

    # Fragmentable part : fake IPv6 for Fragmentable part length computation
    fragPart = pkt[IPv6ExtHdrFragment].payload
    tmp = str(IPv6(src="::1", dst="::1")/fragPart)
    fragPartLen = len(tmp) - 40  # basic IPv6 header length
    fragPartStr = s[-fragPartLen:]

    # Grab Next Header for use in Fragment Header
    nh = IPv6(tmp[:40]).nh

    # Keep fragment header
    fragHeader = pkt[IPv6ExtHdrFragment]
    fragHeader.payload = None # detach payload

    # Unfragmentable Part
    unfragPartLen = len(s) - fragPartLen - 8
    unfragPart = pkt
    pkt[IPv6ExtHdrFragment].underlayer.payload = None # detach payload

    # Cut the fragmentable part to fit fragSize. Inner fragments have 
    # a length that is an integer multiple of 8 octets. last Frag MTU
    # can be anything below MTU
    lastFragSize = fragSize - unfragPartLen - 8
    innerFragSize = lastFragSize - (lastFragSize % 8)
    
    if lastFragSize <= 0 or innerFragSize == 0:
        warning("Provided fragment size value is too low. " + 
                "Should be more than %d" % (unfragPartLen + 8))
        return [unfragPart/fragHeader/fragPart]

    remain = fragPartStr
    res = []
    fragOffset = 0     # offset, incremeted during creation
    fragId = random.randint(0,0xffffffff) # random id ...
    if fragHeader.id is not None:  # ... except id provided by user
        fragId = fragHeader.id
    fragHeader.m = 1
    fragHeader.id = fragId
    fragHeader.nh = nh

    # Main loop : cut, fit to FRAGSIZEs, fragOffset, Id ...
    while True:
        if (len(remain) > lastFragSize):
            tmp = remain[:innerFragSize] 
            remain = remain[innerFragSize:]
            fragHeader.offset = fragOffset    # update offset
            fragOffset += (innerFragSize / 8)  # compute new one
            if IPv6 in unfragPart:  
                unfragPart[IPv6].plen = None
            tempo = unfragPart/fragHeader/Raw(load=tmp)
            res.append(tempo)
        else:
            fragHeader.offset = fragOffset    # update offSet
            fragHeader.m = 0
            if IPv6 in unfragPart:
                unfragPart[IPv6].plen = None
            tempo = unfragPart/fragHeader/Raw(load=remain)
            res.append(tempo)
            break
    return res


############################### AH Header ###################################

# class _AHFieldLenField(FieldLenField):
#     def getfield(self, pkt, s):
#         l = getattr(pkt, self.fld)
#         l = (l*8)-self.shift
#         i = self.m2i(pkt, s[:l])
#         return s[l:],i        

# class _AHICVStrLenField(StrLenField):
#     def i2len(self, pkt, x):
      


# class IPv6ExtHdrAH(_IPv6ExtHdr):
#     name = "IPv6 Extension Header - AH"
#     fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
#                     _AHFieldLenField("len", None, "icv"),
#                     ShortField("res", 0),
#                     IntField("spi", 0),
#                     IntField("sn", 0),
#                     _AHICVStrLenField("icv", None, "len", shift=2) ]
#     overload_fields = {IPv6: { "nh": 51 }}

#     def post_build(self, pkt, pay):
#         if self.len is None:
#             pkt = pkt[0]+struct.pack("!B", 2*len(self.addresses))+pkt[2:]
#         if self.segleft is None:
#             pkt = pkt[:3]+struct.pack("!B", len(self.addresses))+pkt[4:]
#         return _IPv6ExtHdr.post_build(self, pkt, pay)


############################### ESP Header ##################################

# class IPv6ExtHdrESP(_IPv6extHdr):
#     name = "IPv6 Extension Header - ESP"
#     fields_desc = [ IntField("spi", 0),
#                     IntField("sn", 0),
#                     # there is things to extract from IKE work 
#                     ]
#     overloads_fields = {IPv6: { "nh": 50 }}

    

#############################################################################
#############################################################################
###                           ICMPv6* Classes                             ###
#############################################################################
#############################################################################

icmp6typescls = {    1: "ICMPv6DestUnreach",
                     2: "ICMPv6PacketTooBig",
                     3: "ICMPv6TimeExceeded",
                     4: "ICMPv6ParamProblem",
                   128: "ICMPv6EchoRequest",
                   129: "ICMPv6EchoReply",
                   130: "ICMPv6MLQuery", 
                   131: "ICMPv6MLReport",
                   132: "ICMPv6MLDone",
                   133: "ICMPv6ND_RS",
                   134: "ICMPv6ND_RA",
                   135: "ICMPv6ND_NS",
                   136: "ICMPv6ND_NA",
                   137: "ICMPv6ND_Redirect",
                  #138: Do Me - RFC 2894 - Seems painful
                   139: "ICMPv6NIQuery",
                   140: "ICMPv6NIReply",
                   141: "ICMPv6ND_INDSol",
                   142: "ICMPv6ND_INDAdv",
                  #143: Do Me - RFC 3810
                   144: "ICMPv6HAADRequest", 
                   145: "ICMPv6HAADReply",
                   146: "ICMPv6MPSol",
                   147: "ICMPv6MPAdv",
                  #148: Do Me - SEND related - RFC 3971
                  #149: Do Me - SEND related - RFC 3971
                   151: "ICMPv6MRD_Advertisement",
                   152: "ICMPv6MRD_Solicitation",
                   153: "ICMPv6MRD_Termination",
                   }

icmp6types = { 1 : "Destination unreachable",  
               2 : "Packet too big", 
               3 : "Time exceeded",
               4 : "Parameter problem",
             100 : "Private Experimentation",
             101 : "Private Experimentation",
             128 : "Echo Request",
             129 : "Echo Reply",
             130 : "MLD Query",
             131 : "MLD Report",
             132 : "MLD Done",
             133 : "Router Solicitation",
             134 : "Router Advertisement",
             135 : "Neighbor Solicitation",
             136 : "Neighbor Advertisement",
             137 : "Redirect Message",
             138 : "Router Renumbering",
             139 : "ICMP Node Information Query",        
             140 : "ICMP Node Information Response",     
             141 : "Inverse Neighbor Discovery Solicitation Message",
             142 : "Inverse Neighbor Discovery Advertisement Message",
             143 : "Version 2 Multicast Listener Report",
             144 : "Home Agent Address Discovery Request Message",
             145 : "Home Agent Address Discovery Reply Message",
             146 : "Mobile Prefix Solicitation",
             147 : "Mobile Prefix Advertisement",
             148 : "Certification Path Solicitation",
             149 : "Certification Path Advertisement",
             151 : "Multicast Router Advertisement",
             152 : "Multicast Router Solicitation",
             153 : "Multicast Router Termination",
             200 : "Private Experimentation",
             201 : "Private Experimentation" }


class _ICMPv6(Packet):
    name = "ICMPv6 dummy class"
    overload_fields = {IPv6: {"nh": 58}}
    def post_build(self, p, pay):
        p += pay
        if self.cksum == None: 
            chksum = in6_chksum(58, self.underlayer, p)
            p = p[:2]+struct.pack("!H", chksum)+p[4:]
        return p

    def hashret(self):
        return self.payload.hashret()

    def answers(self, other):
        # isinstance(self.underlayer, _IPv6ExtHdr) may introduce a bug ...
        if (isinstance(self.underlayer, IPerror6) or
            isinstance(self.underlayer, _IPv6ExtHdr) and
            isinstance(other, _ICMPv6)):
            if not ((self.type == other.type) and
                    (self.code == other.code)):
                return 0
            return 1
        return 0


class _ICMPv6Error(_ICMPv6):
    name = "ICMPv6 errors dummy class"
    def guess_payload_class(self,p):
        return IPerror6

class ICMPv6Unknown(_ICMPv6):
    name = "Scapy6 ICMPv6 fallback class"
    fields_desc = [ ByteEnumField("type",1, icmp6types),
                    ByteField("code",0),
                    XShortField("cksum", None),
                    StrField("msgbody", "")]    


################################## RFC 2460 #################################

class ICMPv6DestUnreach(_ICMPv6Error):
    name = "ICMPv6 Destination Unreachable"
    fields_desc = [ ByteEnumField("type",1, icmp6types),
                    ByteEnumField("code",0, { 0: "No route to destination",
                                              1: "Communication with destination administratively prohibited",
                                              2: "Beyond scope of source address",
                                              3: "Address unreachable",
                                              4: "Port unreachable" }),
                    XShortField("cksum", None),
                    XIntField("unused",0x00000000)]

class ICMPv6PacketTooBig(_ICMPv6Error):
    name = "ICMPv6 Packet Too Big"
    fields_desc = [ ByteEnumField("type",2, icmp6types),
                    ByteField("code",0),
                    XShortField("cksum", None),
                    IntField("mtu",1280)]
    
class ICMPv6TimeExceeded(_ICMPv6Error):
    name = "ICMPv6 Time Exceeded"
    fields_desc = [ ByteEnumField("type",3, icmp6types),
                    ByteField("code",{ 0: "hop limit exceeded in transit",
                                       1: "fragment reassembly time exceeded"}),
                    XShortField("cksum", None),
                    XIntField("unused",0x00000000)]

# The default pointer value is set to the next header field of 
# the encapsulated IPv6 packet
class ICMPv6ParamProblem(_ICMPv6Error): 
    name = "ICMPv6 Parameter Problem"
    fields_desc = [ ByteEnumField("type",4, icmp6types),
                    ByteEnumField("code",0, {0: "erroneous header field encountered",
                                             1: "unrecognized Next Header type encountered",
                                             2: "unrecognized IPv6 option encountered"}),
                    XShortField("cksum", None),
                    IntField("ptr",6)]

class ICMPv6EchoRequest(_ICMPv6):
    name = "ICMPv6 Echo Request"
    fields_desc = [ ByteEnumField("type", 128, icmp6types),
                    ByteField("code", 0),
                    XShortField("cksum", None),
                    XShortField("id",0),
                    XShortField("seq",0),
                    StrField("data", "")]
    def mysummary(self):
        return self.sprintf("%name% (id: %id% seq: %seq%)")
    def hashret(self):
        return struct.pack("HH",self.id,self.seq)+self.payload.hashret()

    
class ICMPv6EchoReply(ICMPv6EchoRequest):
    name = "ICMPv6 Echo Reply"
    type = 129
    def answers(self, other):
        # We could match data content between request and reply. 
        return (isinstance(other, ICMPv6EchoRequest) and
                self.id == other.id and self.seq == other.seq and
                self.data == other.data)


############ ICMPv6 Multicast Listener Discovery (RFC3810) ##################

# tous les messages MLD sont emis avec une adresse source lien-locale
# -> Y veiller dans le post_build si aucune n'est specifiee
# La valeur de Hop-Limit doit etre de 1
# "and an IPv6 Router Alert option in a Hop-by-Hop Options
# header. (The router alert option is necessary to cause routers to
# examine MLD messages sent to multicast addresses in which the router
# itself has no interest"  
class _ICMPv6ML(_ICMPv6):
    fields_desc = [ ByteEnumField("type", 130, icmp6types),
                    ByteField("code", 0),
                    XShortField("cksum", None),
                    ShortField("mrd", 0),
                    ShortField("reserved", 0),
                    IP6Field("mladdr",None)]

# general queries are sent to the link-scope all-nodes multicast
# address ff02::1, with a multicast address field of 0 and a MRD of
# [Query Response Interval]
# Default value for mladdr is set to 0 for a General Query, and
# overloaded by the user for a Multicast Address specific query
# TODO : See what we can do to automatically include a Router Alert
#        Option in a Destination Option Header.
class ICMPv6MLQuery(_ICMPv6ML): # RFC 2710
    name = "MLD - Multicast Listener Query"
    type   = 130
    mrd    = 10000
    mladdr = "::" # 10s for mrd
    overload_fields = {IPv6: { "dst": "ff02::1", "hlim": 1 }} 
    def hashret(self):
        if self.mladdr != "::":
            return struct.pack("HH",self.mladdr)+self.payload.hashret()
        else:
            return self.payload.hashret()
        
    
# TODO : See what we can do to automatically include a Router Alert
#        Option in a Destination Option Header.
class ICMPv6MLReport(_ICMPv6ML): # RFC 2710
    name = "MLD - Multicast Listener Report"
    type = 131
    overload_fields = {IPv6: {"hlim": 1}}
    # implementer le hashret et le answers
    
# When a node ceases to listen to a multicast address on an interface,
# it SHOULD send a single Done message to the link-scope all-routers
# multicast address (FF02::2), carrying in its multicast address field
# the address to which it is ceasing to listen
# TODO : See what we can do to automatically include a Router Alert
#        Option in a Destination Option Header.
class ICMPv6MLDone(_ICMPv6ML): # RFC 2710
    name = "MLD - Multicast Listener Done"
    type = 132
    overload_fields = {IPv6: { "dst": "ff02::2", "hlim": 1}}


########## ICMPv6 MRD - Multicast Router Discovery (RFC 4286) ###############

# TODO: 
# - 04/09/06 troglocan : find a way to automatically add a router alert
#            option for all MRD packets. This could be done in a specific
#            way when IPv6 is the under layer with some specific keyword
#            like 'exthdr'. This would allow to keep compatibility with
#            providing IPv6 fields to be overloaded in fields_desc.
# 
#            At the moment, if user inserts an IPv6 Router alert option
#            none of the IPv6 default values of IPv6 layer will be set.

class ICMPv6MRD_Advertisement(_ICMPv6):
    name = "ICMPv6 Multicast Router Discovery Advertisement"
    fields_desc = [ByteEnumField("type", 151, icmp6types),
                   ByteField("advinter", 20),
                   XShortField("cksum", None),
                   ShortField("queryint", 0),
                   ShortField("robustness", 0)]
    overload_fields = {IPv6: { "nh": 58, "hlim": 1, "dst": "ff02::2"}}
                       # IPv6 Router Alert requires manual inclusion
    def extract_padding(self, s):
        return s[:8], s[8:]

class ICMPv6MRD_Solicitation(_ICMPv6):
    name = "ICMPv6 Multicast Router Discovery Solicitation"
    fields_desc = [ByteEnumField("type", 152, icmp6types),
                   ByteField("res", 0),
                   XShortField("cksum", None) ]
    overload_fields = {IPv6: { "nh": 58, "hlim": 1, "dst": "ff02::2"}}
                       # IPv6 Router Alert requires manual inclusion
    def extract_padding(self, s):
        return s[:4], s[4:]

class ICMPv6MRD_Termination(_ICMPv6):
    name = "ICMPv6 Multicast Router Discovery Termination"
    fields_desc = [ByteEnumField("type", 153, icmp6types),
                   ByteField("res", 0),
                   XShortField("cksum", None) ]
    overload_fields = {IPv6: { "nh": 58, "hlim": 1, "dst": "ff02::6A"}}  
                       # IPv6 Router Alert requires manual inclusion
    def extract_padding(self, s):
        return s[:4], s[4:]


################### ICMPv6 Neighbor Discovery (RFC 2461) ####################

icmp6ndopts = { 1: "Source Link-Layer Address",
                2: "Target Link-Layer Address",
                3: "Prefix Information",
                4: "Redirected Header",
                5: "MTU",
                6: "NBMA Shortcut Limit Option", # RFC2491
                7: "Advertisement Interval Option",
                8: "Home Agent Information Option",
                9: "Source Address List",
               10: "Target Address List",
               11: "CGA Option",            # RFC 3971
               12: "RSA Signature Option",  # RFC 3971
               13: "Timestamp Option",      # RFC 3971
               14: "Nonce option",          # RFC 3971
               15: "Trust Anchor Option",   # RFC 3971
               16: "Certificate Option",    # RFC 3971
               17: "IP Address Option",                             # RFC 4068
               18: "New Router Prefix Information Option",          # RFC 4068
               19: "Link-layer Address Option",                     # RFC 4068
               20: "Neighbor Advertisement Acknowledgement Option", 
               21: "CARD Request Option", # RFC 4065/4066/4067
               22: "CARD Reply Option",   # RFC 4065/4066/4067
               23: "MAP Option",          # RFC 4140
               24: "Route Information Option",  # RFC 4191
               25: "Recusive DNS Server Option",
               26: "IPv6 Router Advertisement Flags Option"
                }
                  
icmp6ndoptscls = { 1: "ICMPv6NDOptSrcLLAddr",
                   2: "ICMPv6NDOptDstLLAddr",
                   3: "ICMPv6NDOptPrefixInfo",
                   4: "ICMPv6NDOptRedirectedHdr",
                   5: "ICMPv6NDOptMTU",
                   6: "ICMPv6NDOptShortcutLimit",
                   7: "ICMPv6NDOptAdvInterval",
                   8: "ICMPv6NDOptHAInfo",
                   9: "ICMPv6NDOptSrcAddrList",
                  10: "ICMPv6NDOptTgtAddrList",
                  #11: Do Me,
                  #12: Do Me,
                  #13: Do Me,
                  #14: Do Me,
                  #15: Do Me,
                  #16: Do Me,
                  17: "ICMPv6NDOptIPAddr", 
                  18: "ICMPv6NDOptNewRtrPrefix",
                  19: "ICMPv6NDOptLLA",
                  #18: Do Me,
                  #19: Do Me,
                  #20: Do Me,
                  #21: Do Me,
                  #22: Do Me,
                  23: "ICMPv6NDOptMAP",
                  24: "ICMPv6NDOptRouteInfo",
                  25: "ICMPv6NDOptRDNSS",
                  26: "ICMPv6NDOptEFA"
                  }

class _ICMPv6NDGuessPayload:
    name = "Dummy ND class that implements guess_payload_class()"
    def guess_payload_class(self,p):
        if len(p) > 1:
            return get_cls(icmp6ndoptscls.get(ord(p[0]),"Raw"), "Raw") # s/Raw/ICMPv6NDOptUnknown/g ?


# Beginning of ICMPv6 Neighbor Discovery Options.

class ICMPv6NDOptUnknown(_ICMPv6NDGuessPayload, Packet):
    name = "ICMPv6 Neighbor Discovery Option - Scapy Unimplemented"
    fields_desc = [ ByteField("type",None),
                    FieldLenField("len",None,length_of="data",fmt="B",
                                  adjust = lambda pkt,x: x+2),
                    StrLenField("data","",
                                length_from = lambda pkt: pkt.len-2) ]

# NOTE: len includes type and len field. Expressed in unit of 8 bytes
# TODO: Revoir le coup du ETHER_ANY
class ICMPv6NDOptSrcLLAddr(_ICMPv6NDGuessPayload, Packet):
    name = "ICMPv6 Neighbor Discovery Option - Source Link-Layer Address"
    fields_desc = [ ByteField("type", 1),
                    ByteField("len", 1),
                    MACField("lladdr", ETHER_ANY) ]
    def mysummary(self):                        
        return self.sprintf("%name% %lladdr%")

class ICMPv6NDOptDstLLAddr(ICMPv6NDOptSrcLLAddr):
    name = "ICMPv6 Neighbor Discovery Option - Destination Link-Layer Address"
    type = 2

class ICMPv6NDOptPrefixInfo(_ICMPv6NDGuessPayload, Packet):
    name = "ICMPv6 Neighbor Discovery Option - Prefix Information"
    fields_desc = [ ByteField("type",3),
                    ByteField("len",4),
                    ByteField("prefixlen",None),
                    BitField("L",1,1),
                    BitField("A",1,1),
                    BitField("R",0,1),
                    BitField("res1",0,5),
                    XIntField("validlifetime",0xffffffffL),
                    XIntField("preferredlifetime",0xffffffffL),
                    XIntField("res2",0x00000000),
                    IP6Field("prefix","::") ]
    def mysummary(self):                        
        return self.sprintf("%name% %prefix%")

# TODO: We should also limit the size of included packet to something
# like (initiallen - 40 - 2)
class TruncPktLenField(PacketLenField):

    def __init__(self, name, default, cls, cur_shift, length_from=None, shift=0):
        PacketLenField.__init__(self, name, default, cls, length_from=length_from)
        self.cur_shift = cur_shift

    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        i = self.m2i(pkt, s[:l])
        return s[l:],i

    def m2i(self, pkt, m):
        s = None
        try: # It can happen we have sth shorter than 40 bytes
            s = self.cls(m)
        except:
            return Raw(m)
        return s

    def i2m(self, pkt, x):
        s = str(x)
        l = len(s)
        r = (l + self.cur_shift) % 8
        l = l - r
        return s[:l]

    def i2len(self, pkt, i):
        return len(self.i2m(pkt, i))


# Faire un post_build pour le recalcul de la taille (en multiple de 8 octets)
class ICMPv6NDOptRedirectedHdr(_ICMPv6NDGuessPayload, Packet):
    name = "ICMPv6 Neighbor Discovery Option - Redirected Header"
    fields_desc = [ ByteField("type",4),
                    FieldLenField("len", None, length_of="pkt", fmt="B",
                                  adjust = lambda pkt,x:(x+8)/8),
                    StrFixedLenField("res", "\x00"*6, 6),
                    TruncPktLenField("pkt", "", IPv6, 8,
                                     length_from = lambda pkt: 8*pkt.len-8) ]

# See which value should be used for default MTU instead of 1280
class ICMPv6NDOptMTU(_ICMPv6NDGuessPayload, Packet):
    name = "ICMPv6 Neighbor Discovery Option - MTU"
    fields_desc = [ ByteField("type",5),
                    ByteField("len",1),
                    XShortField("res",0),
                    IntField("mtu",1280)]

class ICMPv6NDOptShortcutLimit(_ICMPv6NDGuessPayload, Packet): # RFC 2491
    name = "ICMPv6 Neighbor Discovery Option - NBMA Shortcut Limit"
    fields_desc = [ ByteField("type", 6),
                    ByteField("len", 1),
                    ByteField("shortcutlim", 40), # XXX
                    ByteField("res1", 0),
                    IntField("res2", 0) ]
    
class ICMPv6NDOptAdvInterval(_ICMPv6NDGuessPayload, Packet):
    name = "ICMPv6 Neighbor Discovery - Interval Advertisement"
    fields_desc = [ ByteField("type",7),
                    ByteField("len",1),
                    ShortField("res", 0),
                    IntField("advint", 0) ]
    def mysummary(self):                        
        return self.sprintf("%name% %advint% milliseconds")

class ICMPv6NDOptHAInfo(_ICMPv6NDGuessPayload, Packet): 
    name = "ICMPv6 Neighbor Discovery - Home Agent Information"
    fields_desc = [ ByteField("type",8),
                    ByteField("len",1),
                    ShortField("res", 0),
                    ShortField("pref", 0),
                    ShortField("lifetime", 1)]
    def mysummary(self):                        
        return self.sprintf("%name% %pref% %lifetime% seconds")

# type 9  : See ICMPv6NDOptSrcAddrList class below in IND (RFC 3122) support

# type 10 : See ICMPv6NDOptTgtAddrList class below in IND (RFC 3122) support

class ICMPv6NDOptIPAddr(_ICMPv6NDGuessPayload, Packet):  # RFC 4068
    name = "ICMPv6 Neighbor Discovery - IP Address Option (FH for MIPv6)"
    fields_desc = [ ByteField("type",17),
                    ByteField("len", 3),
                    ByteEnumField("optcode", 1, {1: "Old Care-Of Address",
                                                 2: "New Care-Of Address",
                                                 3: "NAR's IP address" }),
                    ByteField("plen", 64),
                    IntField("res", 0),
                    IP6Field("addr", "::") ]

class ICMPv6NDOptNewRtrPrefix(_ICMPv6NDGuessPayload, Packet): # RFC 4068
    name = "ICMPv6 Neighbor Discovery - New Router Prefix Information Option (FH for MIPv6)"
    fields_desc = [ ByteField("type",18),
                    ByteField("len", 3),
                    ByteField("optcode", 0),
                    ByteField("plen", 64),
                    IntField("res", 0),
                    IP6Field("prefix", "::") ]

_rfc4068_lla_optcode = {0: "Wildcard requesting resolution for all nearby AP",
                        1: "LLA for the new AP",
                        2: "LLA of the MN",
                        3: "LLA of the NAR",
                        4: "LLA of the src of TrSolPr or PrRtAdv msg",
                        5: "AP identified by LLA belongs to current iface of router",
                        6: "No preifx info available for AP identified by the LLA",
                        7: "No fast handovers support for AP identified by the LLA" }

class ICMPv6NDOptLLA(_ICMPv6NDGuessPayload, Packet):     # RFC 4068
    name = "ICMPv6 Neighbor Discovery - Link-Layer Address (LLA) Option (FH for MIPv6)"
    fields_desc = [ ByteField("type", 19),
                    ByteField("len", 1),
                    ByteEnumField("optcode", 0, _rfc4068_lla_optcode),
                    MACField("lla", ETHER_ANY) ] # We only support ethernet

class ICMPv6NDOptMAP(_ICMPv6NDGuessPayload, Packet):     # RFC 4140
    name = "ICMPv6 Neighbor Discovery - MAP Option"
    fields_desc = [ ByteField("type", 23),
                    ByteField("len", 3),
                    BitField("dist", 1, 4),
                    BitField("pref", 15, 4), # highest availability
                    BitField("R", 1, 1),
                    BitField("res", 0, 7),                    
                    IntField("validlifetime", 0xffffffff),
                    IP6Field("addr", "::") ] 


class IP6PrefixField(IP6Field):
    def __init__(self, name, default):
        IP6Field.__init__(self, name, default)
        self.length_from = lambda pkt: 8*(pkt.len - 1)

    def addfield(self, pkt, s, val):
        return s + self.i2m(pkt, val)

    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        p = s[:l]
        if l < 16:
            p += '\x00'*(16-l)
        return s[l:], self.m2i(pkt,p)

    def i2len(self, pkt, x):
        return len(self.i2m(pkt, x))
    
    def i2m(self, pkt, x):
        l = pkt.len

        if x is None:
            x = "::"
            if l is None:
                l = 1
        x = inet_pton(socket.AF_INET6, x)

        if l is None:
            return x
        if l in [0, 1]:
            return ""
        if l in [2, 3]:
            return x[:8*(l-1)]

        return x + '\x00'*8*(l-3)

class ICMPv6NDOptRouteInfo(_ICMPv6NDGuessPayload, Packet): # RFC 4191
    name = "ICMPv6 Neighbor Discovery Option - Route Information Option"
    fields_desc = [ ByteField("type",24),
                    FieldLenField("len", None, length_of="prefix", fmt="B",
                                  adjust = lambda pkt,x: x/8 + 1),
                    ByteField("plen", None),
                    BitField("res1",0,3),
                    BitField("prf",0,2),
                    BitField("res2",0,3),
                    IntField("rtlifetime", 0xffffffff),
                    IP6PrefixField("prefix", None) ]
  
class ICMPv6NDOptRDNSS(_ICMPv6NDGuessPayload, Packet): # RFC 5006
    name = "ICMPv6 Neighbor Discovery Option - Recursive DNS Server Option"
    fields_desc = [ ByteField("type", 25),
                    FieldLenField("len", None, count_of="dns", fmt="B",
                                  adjust = lambda pkt,x: 2*x+1),
                    ShortField("res", None),
                    IntField("lifetime", 0xffffffff),
                    IP6ListField("dns", [], 
                                 length_from = lambda pkt: 8*(pkt.len-1)) ]

class ICMPv6NDOptEFA(_ICMPv6NDGuessPayload, Packet): # RFC 5175 (prev. 5075)
    name = "ICMPv6 Neighbor Discovery Option - Expanded Flags Option"
    fields_desc = [ ByteField("type", 26),
                    ByteField("len", 1),
                    BitField("res", 0, 48) ]

# End of ICMPv6 Neighbor Discovery Options.

class ICMPv6ND_RS(_ICMPv6NDGuessPayload, _ICMPv6):
    name = "ICMPv6 Neighbor Discovery - Router Solicitation"
    fields_desc = [ ByteEnumField("type", 133, icmp6types),
                    ByteField("code",0),
                    XShortField("cksum", None),
                    IntField("res",0) ]
    overload_fields = {IPv6: { "nh": 58, "dst": "ff02::2", "hlim": 255 }}

class ICMPv6ND_RA(_ICMPv6NDGuessPayload, _ICMPv6):
    name = "ICMPv6 Neighbor Discovery - Router Advertisement"
    fields_desc = [ ByteEnumField("type", 134, icmp6types),
                    ByteField("code",0),
                    XShortField("cksum", None),
                    ByteField("chlim",0),
                    BitField("M",0,1),
                    BitField("O",0,1),
                    BitField("H",0,1),
                    BitEnumField("prf",1,2, { 0: "Medium (default)",
                                              1: "High",
                                              2: "Reserved",
                                              3: "Low" } ), # RFC 4191
                    BitField("P",0,1),
                    BitField("res",0,2),                    
                    ShortField("routerlifetime",1800),
                    IntField("reachabletime",0),
                    IntField("retranstimer",0) ]
    overload_fields = {IPv6: { "nh": 58, "dst": "ff02::1", "hlim": 255 }}

    def answers(self, other):
        return isinstance(other, ICMPv6ND_RS)

class ICMPv6ND_NS(_ICMPv6NDGuessPayload, _ICMPv6, Packet):
    name = "ICMPv6 Neighbor Discovery - Neighbor Solicitation"
    fields_desc = [ ByteEnumField("type",135, icmp6types),
                    ByteField("code",0),
                    XShortField("cksum", None),
                    BitField("R",0,1),
                    BitField("S",0,1),
                    BitField("O",0,1),
                    XBitField("res",0,29),
                    IP6Field("tgt","::") ]
    overload_fields = {IPv6: { "nh": 58, "dst": "ff02::1", "hlim": 255 }}

    def mysummary(self):
        return self.sprintf("%name% (tgt: %tgt%)")

    def hashret(self):
        return self.tgt+self.payload.hashret() 

class ICMPv6ND_NA(ICMPv6ND_NS):
    name = "ICMPv6 Neighbor Discovery - Neighbor Advertisement"
    type = 136
    R    = 1
    O    = 1

    def answers(self, other):
        return isinstance(other, ICMPv6ND_NS) and self.tgt == other.tgt

# associated possible options : target link-layer option, Redirected header
class ICMPv6ND_Redirect(_ICMPv6NDGuessPayload, _ICMPv6, Packet):
    name = "ICMPv6 Neighbor Discovery - Redirect"
    fields_desc = [ ByteEnumField("type",137, icmp6types),
                    ByteField("code",0),
                    XShortField("cksum", None),
                    XIntField("res",0),
                    IP6Field("tgt","::"),
                    IP6Field("dst","::") ]
    overload_fields = {IPv6: { "nh": 58, "dst": "ff02::1", "hlim": 255 }}



################ ICMPv6 Inverse Neighbor Discovery (RFC 3122) ###############

class ICMPv6NDOptSrcAddrList(_ICMPv6NDGuessPayload, Packet):
    name = "ICMPv6 Inverse Neighbor Discovery Option - Source Address List"
    fields_desc = [ ByteField("type",9),
                    FieldLenField("len", None, count_of="addrlist", fmt="B",
                                  adjust = lambda pkt,x: 2*x+1),
                    StrFixedLenField("res", "\x00"*6, 6),
                    IP6ListField("addrlist", [],
                                length_from = lambda pkt: 8*(pkt.len-1)) ]

class ICMPv6NDOptTgtAddrList(ICMPv6NDOptSrcAddrList):
    name = "ICMPv6 Inverse Neighbor Discovery Option - Target Address List"
    type = 10 


# RFC3122
# Options requises : source lladdr et target lladdr
# Autres options valides : source address list, MTU
# - Comme precise dans le document, il serait bien de prendre l'adresse L2
#   demandee dans l'option requise target lladdr et l'utiliser au niveau
#   de l'adresse destination ethernet si aucune adresse n'est precisee
# - ca semble pas forcement pratique si l'utilisateur doit preciser toutes
#   les options. 
# Ether() must use the target lladdr as destination
class ICMPv6ND_INDSol(_ICMPv6NDGuessPayload, _ICMPv6):
    name = "ICMPv6 Inverse Neighbor Discovery Solicitation"
    fields_desc = [ ByteEnumField("type",141, icmp6types),
                    ByteField("code",0),
                    XShortField("cksum",None),
                    XIntField("reserved",0) ]
    overload_fields = {IPv6: { "nh": 58, "dst": "ff02::1", "hlim": 255 }}

# Options requises :  target lladdr, target address list
# Autres options valides : MTU
class ICMPv6ND_INDAdv(_ICMPv6NDGuessPayload, _ICMPv6):
    name = "ICMPv6 Inverse Neighbor Discovery Advertisement"
    fields_desc = [ ByteEnumField("type",142, icmp6types),
                    ByteField("code",0),
                    XShortField("cksum",None),
                    XIntField("reserved",0) ]
    overload_fields = {IPv6: { "nh": 58, "dst": "ff02::1", "hlim": 255 }}


###############################################################################
# ICMPv6 Node Information Queries (RFC 4620)
###############################################################################

# [ ] Add automatic destination address computation using computeNIGroupAddr 
#     in IPv6 class (Scapy6 modification when integrated) if :
#     - it is not provided
#     - upper layer is ICMPv6NIQueryName() with a valid value
# [ ] Try to be liberal in what we accept as internal values for _explicit_
#     DNS elements provided by users. Any string should be considered 
#     valid and kept like it has been provided. At the moment, i2repr() will
#     crash on many inputs
# [ ] Do the documentation
# [ ] Add regression tests
# [ ] Perform test against real machines (NOOP reply is proof of implementation). 
# [ ] Check if there are differences between different stacks. Among *BSD, 
#     with others. 
# [ ] Deal with flags in a consistent way.
# [ ] Implement compression in names2dnsrepr() and decompresiion in 
#     dnsrepr2names(). Should be deactivable. 

icmp6_niqtypes = { 0: "NOOP",
                  2: "Node Name",
                  3: "IPv6 Address",
                  4: "IPv4 Address" }


class _ICMPv6NIHashret:
    def hashret(self):
        return self.nonce

class _ICMPv6NIAnswers:
    def answers(self, other):
        return self.nonce == other.nonce

# Buggy; always returns the same value during a session
class NonceField(StrFixedLenField):
    def __init__(self, name, default=None):
        StrFixedLenField.__init__(self, name, default, 8)
        if default is None:
            self.default = self.randval()

# Compute the NI group Address. Can take a FQDN as input parameter
def computeNIGroupAddr(name):
    import md5
    name = name.lower().split(".")[0]
    record = chr(len(name))+name
    h = md5.new(record)
    h = h.digest()
    addr = "ff02::2:%2x%2x:%2x%2x" % struct.unpack("BBBB", h[:4])
    return addr


# Here is the deal. First, that protocol is a piece of shit. Then, we 
# provide 4 classes for the different kinds of Requests (one for every
# valid qtype: NOOP, Node Name, IPv6@, IPv4@). They all share the same
# data field class that is made to be smart by guessing the specifc 
# type of value provided : 
#
# - IPv6 if acceptable for inet_pton(AF_INET6, ): code is set to 0,
#   if not overriden by user
# - IPv4 if acceptable for inet_pton(AF_INET,  ): code is set to 2,
#   if not overriden
# - Name in the other cases: code is set to 0, if not overriden by user
#
# Internal storage, is not only the value, but the a pair providing
# the type and the value (1 is IPv6@, 1 is Name or string, 2 is IPv4@)
#
# Note : I merged getfield() and m2i(). m2i() should not be called 
#        directly anyway. Same remark for addfield() and i2m() 
#
# -- arno 

# "The type of information present in the Data field of a query is 
#  declared by the ICMP Code, whereas the type of information in a 
#  Reply is determined by the Qtype"

def names2dnsrepr(x):
    """
    Take as input a list of DNS names or a single DNS name
    and encode it in DNS format (with possible compression)
    If a string that is already a DNS name in DNS format
    is passed, it is returned unmodified. Result is a string.
    !!!  At the moment, compression is not implemented  !!!
    """
    
    if type(x) is str:
        if x and x[-1] == '\x00': # stupid heuristic
            return x
        x = [x]

    res = []
    for n in x:
        termin = "\x00"
        if n.count('.') == 0: # single-component gets one more
            termin += '\x00' 
        n = "".join(map(lambda y: chr(len(y))+y, n.split("."))) + termin
        res.append(n)
    return "".join(res)


def dnsrepr2names(x):
    """
    Take as input a DNS encoded string (possibly compressed) 
    and returns a list of DNS names contained in it.
    If provided string is already in printable format
    (does not end with a null character, a one element list
    is returned). Result is a list.
    """
    res = []
    cur = ""
    while x:
        l = ord(x[0])
        x = x[1:]
        if l == 0:
            if cur and cur[-1] == '.':
                cur = cur[:-1]
            res.append(cur)
            cur = ""
            if x and ord(x[0]) == 0: # single component
                x = x[1:]
            continue
        if l & 0xc0: # XXX TODO : work on that -- arno
            raise Exception("DNS message can't be compressed at this point!")
        else:
            cur += x[:l]+"."
            x = x[l:]
    return res


class NIQueryDataField(StrField):
    def __init__(self, name, default):
        StrField.__init__(self, name, default)

    def i2h(self, pkt, x):
        if x is None:
            return x
        t,val = x
        if t == 1:
            val = dnsrepr2names(val)[0]
        return val

    def h2i(self, pkt, x):
        if x is tuple and type(x[0]) is int:
            return x

        val = None
        try: # Try IPv6
            inet_pton(socket.AF_INET6, x)
            val = (0, x)
        except:
            try: # Try IPv4
                inet_pton(socket.AF_INET, x)
                val = (2, x)
            except: # Try DNS
                if x is None:
                    x = ""
                x = names2dnsrepr(x)
                val = (1, x)
        return val

    def i2repr(self, pkt, x):
        t,val = x
        if t == 1: # DNS Name
            # we don't use dnsrepr2names() to deal with 
            # possible weird data extracted info
            res = []
            weird = None
            while val:
                l = ord(val[0]) 
                val = val[1:]
                if l == 0:
                    if (len(res) > 1 and val): # fqdn with data behind
                        weird = val
                    elif len(val) > 1: # single label with data behind
                        weird = val[1:]
                    break
                res.append(val[:l]+".")
                val = val[l:]
            tmp = "".join(res)
            if tmp and tmp[-1] == '.':
                tmp = tmp[:-1]
            return tmp
        return repr(val)

    def getfield(self, pkt, s):
        qtype = getattr(pkt, "qtype")
        if qtype == 0: # NOOP
            return s, (0, "")
        else:
            code = getattr(pkt, "code")
            if code == 0:   # IPv6 Addr
                return s[16:], (0, inet_ntop(socket.AF_INET6, s[:16]))
            elif code == 2: # IPv4 Addr
                return s[4:], (2, inet_ntop(socket.AF_INET, s[:4]))
            else:           # Name or Unknown
                return "", (1, s)

    def addfield(self, pkt, s, val):
        if ((type(val) is tuple and val[1] is None) or
            val is None):
            val = (1, "")
        t = val[0]
        if t == 1:
            return s + val[1]
        elif t == 0:
            return s + inet_pton(socket.AF_INET6, val[1])
        else:
            return s + inet_pton(socket.AF_INET, val[1])

class NIQueryCodeField(ByteEnumField):
    def i2m(self, pkt, x):
        if x is None:
            d = pkt.getfieldval("data")
            if d is None:
                return 1
            elif d[0] == 0: # IPv6 address
                return 0
            elif d[0] == 1: # Name
                return 1
            elif d[0] == 2: # IPv4 address
                return 2
            else:
                return 1
        return x
    

_niquery_code = {0: "IPv6 Query", 1: "Name Query", 2: "IPv4 Query"}

#_niquery_flags = {  2: "All unicast addresses", 4: "IPv4 addresses",
#                    8: "Link-local addresses", 16: "Site-local addresses", 
#                   32: "Global addresses" }

# "This NI type has no defined flags and never has a Data Field". Used
# to know if the destination is up and implements NI protocol.
class ICMPv6NIQueryNOOP(_ICMPv6NIHashret, _ICMPv6): 
    name = "ICMPv6 Node Information Query - NOOP Query"
    fields_desc = [ ByteEnumField("type", 139, icmp6types),
                    NIQueryCodeField("code", None, _niquery_code),
                    XShortField("cksum", None),
                    ShortEnumField("qtype", 0, icmp6_niqtypes),
                    BitField("unused", 0, 10),
                    FlagsField("flags", 0, 6, "TACLSG"), 
                    NonceField("nonce", None),
                    NIQueryDataField("data", None) ]

class ICMPv6NIQueryName(ICMPv6NIQueryNOOP): 
    name = "ICMPv6 Node Information Query - IPv6 Name Query"
    qtype = 2 

# We ask for the IPv6 address of the peer 
class ICMPv6NIQueryIPv6(ICMPv6NIQueryNOOP):
    name = "ICMPv6 Node Information Query - IPv6 Address Query"
    qtype = 3
    flags = 0x3E

class ICMPv6NIQueryIPv4(ICMPv6NIQueryNOOP): 
    name = "ICMPv6 Node Information Query - IPv4 Address Query"
    qtype = 4

_nireply_code = { 0: "Successful Reply", 
                  1: "Response Refusal", 
                  3: "Unknown query type" }

_nireply_flags = {  1: "Reply set incomplete", 
                    2: "All unicast addresses", 
                    4: "IPv4 addresses",        
                    8: "Link-local addresses", 
                   16: "Site-local addresses", 
                   32: "Global addresses" }

# Internal repr is one of those :
# (0, "some string") : unknow qtype value are mapped to that one
# (3, [ (ttl, ip6), ... ])
# (4, [ (ttl, ip4), ... ]) 
# (2, [ttl, dns_names]) : dns_names is one string that contains
#     all the DNS names. Internally it is kept ready to be sent 
#     (undissected). i2repr() decode it for user. This is to 
#     make build after dissection bijective.
#
# I also merged getfield() and m2i(), and addfield() and i2m().
class NIReplyDataField(StrField):

    def i2h(self, pkt, x):
        if x is None:
            return x
        t,val = x
        if t == 2:
            ttl, dnsnames = val
            val = [ttl] + dnsrepr2names(dnsnames)
        return val

    def h2i(self, pkt, x):
        qtype = 0 # We will decode it as string if not 
                  # overridden through 'qtype' in pkt

        # No user hint, let's use 'qtype' value for that purpose
        if type(x) is not tuple:
            if pkt is not None:
                qtype = getattr(pkt, "qtype")
        else:
            qtype = x[0]
            x = x[1]

        # From that point on, x is the value (second element of the tuple)

        if qtype == 2: # DNS name
            if type(x) is str: # listify the string
                x = [x]
            if type(x) is list and x and type(x[0]) is not int: # ttl was omitted : use 0
                x = [0] + x
            ttl = x[0]
            names = x[1:]
            return (2, [ttl, names2dnsrepr(names)])

        elif qtype in [3, 4]: # IPv4 or IPv6 addr
            if type(x) is str:
                x = [x] # User directly provided an IP, instead of list

            # List elements are not tuples, user probably
            # omitted ttl value : we will use 0 instead
            def addttl(x):
                if type(x) is str:
                    return (0, x)
                return x

            return (qtype, map(addttl, x))

        return (qtype, x)


    def addfield(self, pkt, s, val):
        t,tmp = val
        if tmp is None:
            tmp = ""
        if t == 2:
            ttl,dnsstr = tmp
            return s+ struct.pack("!I", ttl) + dnsstr
        elif t == 3:
            return s + "".join(map(lambda (x,y): struct.pack("!I", x)+inet_pton(socket.AF_INET6, y), tmp))
        elif t == 4:
            return s + "".join(map(lambda (x,y): struct.pack("!I", x)+inet_pton(socket.AF_INET, y), tmp))
        else:
            return s + tmp
                
    def getfield(self, pkt, s):
        code = getattr(pkt, "code")
        if code != 0:
            return s, (0, "")

        qtype = getattr(pkt, "qtype")        
        if qtype == 0: # NOOP
            return s, (0, "")

        elif qtype == 2:
            if len(s) < 4:
                return s, (0, "")
            ttl = struct.unpack("!I", s[:4])[0]
            return "", (2, [ttl, s[4:]])

        elif qtype == 3: # IPv6 addresses with TTLs
            # XXX TODO : get the real length
            res = []
            while len(s) >= 20: # 4 + 16
                ttl = struct.unpack("!I", s[:4])[0]
                ip  = inet_ntop(socket.AF_INET6, s[4:20])
                res.append((ttl, ip))
                s = s[20:]
            return s, (3, res)

        elif qtype == 4: # IPv4 addresses with TTLs
            # XXX TODO : get the real length
            res = []
            while len(s) >= 8: # 4 + 4 
                ttl = struct.unpack("!I", s[:4])[0]
                ip  = inet_ntop(socket.AF_INET, s[4:8])
                res.append((ttl, ip))
                s = s[8:]
            return s, (4, res)
        else:
            # XXX TODO : implement me and deal with real length
            return "", (0, s)

    def i2repr(self, pkt, x):
        if x is None:
            return "[]"
        
        if type(x) is tuple and len(x) == 2:
            t, val = x
            if t == 2: # DNS names
                ttl,l = val
                l = dnsrepr2names(l)
                return "ttl:%d %s" % (ttl, ", ".join(l))
            elif t == 3 or t == 4:
                return "[ %s ]" % (", ".join(map(lambda (x,y): "(%d, %s)" % (x, y), val)))
            return repr(val)
        return repr(x) # XXX should not happen

# By default, sent responses have code set to 0 (successful) 
class ICMPv6NIReplyNOOP(_ICMPv6NIAnswers, _ICMPv6NIHashret, _ICMPv6): 
    name = "ICMPv6 Node Information Reply - NOOP Reply"
    fields_desc = [ ByteEnumField("type", 140, icmp6types),
                    ByteEnumField("code", 0, _nireply_code),
                    XShortField("cksum", None),
                    ShortEnumField("qtype", 0, icmp6_niqtypes),
                    BitField("unused", 0, 10),
                    FlagsField("flags", 0, 6, "TACLSG"), 
                    NonceField("nonce", None),
                    NIReplyDataField("data", None)]

class ICMPv6NIReplyName(ICMPv6NIReplyNOOP): 
    name = "ICMPv6 Node Information Reply - Node Names"
    qtype = 2

class ICMPv6NIReplyIPv6(ICMPv6NIReplyNOOP): 
    name = "ICMPv6 Node Information Reply - IPv6 addresses"
    qtype = 3

class ICMPv6NIReplyIPv4(ICMPv6NIReplyNOOP): 
    name = "ICMPv6 Node Information Reply - IPv4 addresses"
    qtype = 4

class ICMPv6NIReplyRefuse(ICMPv6NIReplyNOOP):
    name = "ICMPv6 Node Information Reply - Responder refuses to supply answer"
    code = 1

class ICMPv6NIReplyUnknown(ICMPv6NIReplyNOOP):
    name = "ICMPv6 Node Information Reply - Qtype unknown to the responder"
    code = 2


def _niquery_guesser(p):
    cls = Raw
    type = ord(p[0])
    if type == 139: # Node Info Query specific stuff
        if len(p) > 6:
            qtype, = struct.unpack("!H", p[4:6])
            cls = { 0: ICMPv6NIQueryNOOP,
                    2: ICMPv6NIQueryName,
                    3: ICMPv6NIQueryIPv6,
                    4: ICMPv6NIQueryIPv4 }.get(qtype, Raw)
    elif type == 140: # Node Info Reply specific stuff
        code = ord(p[1])
        if code == 0:
            if len(p) > 6:
                qtype, = struct.unpack("!H", p[4:6])
                cls = { 2: ICMPv6NIReplyName,
                        3: ICMPv6NIReplyIPv6,
                        4: ICMPv6NIReplyIPv4 }.get(qtype, ICMPv6NIReplyNOOP)
        elif code == 1:
            cls = ICMPv6NIReplyRefuse
        elif code == 2:
            cls = ICMPv6NIReplyUnknown
    return cls


#############################################################################
#############################################################################
###             Mobile IPv6 (RFC 3775) and Nemo (RFC 3963)                ###
#############################################################################
#############################################################################

# Mobile IPv6 ICMPv6 related classes

class ICMPv6HAADRequest(_ICMPv6):
    name = 'ICMPv6 Home Agent Address Discovery Request'
    fields_desc = [ ByteEnumField("type", 144, icmp6types),
                    ByteField("code", 0),
                    XShortField("cksum", None),
                    XShortField("id", None),
                    BitEnumField("R", 1, 1, {1: 'MR'}),
                    XBitField("res", 0, 15) ]
    def hashret(self):
        return struct.pack("!H",self.id)+self.payload.hashret()

class ICMPv6HAADReply(_ICMPv6): 
    name = 'ICMPv6 Home Agent Address Discovery Reply'
    fields_desc = [ ByteEnumField("type", 145, icmp6types),
                    ByteField("code", 0),
                    XShortField("cksum", None),
                    XShortField("id", None),
                    BitEnumField("R", 1, 1, {1: 'MR'}),
                    XBitField("res", 0, 15),
                    IP6ListField('addresses', None) ]
    def hashret(self):
        return struct.pack("!H",self.id)+self.payload.hashret()

    def answers(self, other):
        if not isinstance(other, ICMPv6HAADRequest):
            return 0
        return self.id == other.id    

class ICMPv6MPSol(_ICMPv6): 
    name = 'ICMPv6 Mobile Prefix Solicitation'
    fields_desc = [ ByteEnumField("type", 146, icmp6types),
                    ByteField("code", 0),
                    XShortField("cksum", None),
                    XShortField("id", None),
                    XShortField("res", 0) ]
    def _hashret(self):
        return struct.pack("!H",self.id)

class ICMPv6MPAdv(_ICMPv6NDGuessPayload, _ICMPv6):
    name = 'ICMPv6 Mobile Prefix Advertisement'
    fields_desc = [ ByteEnumField("type", 147, icmp6types),
                    ByteField("code", 0),
                    XShortField("cksum", None),
                    XShortField("id", None),
                    BitEnumField("flags", 2, 2, {2: 'M', 1:'O'}), 
                    XBitField("res", 0, 14) ]
    def hashret(self):
        return struct.pack("!H",self.id)
    
    def answers(self, other):
        return isinstance(other, ICMPv6MPSol)

# Mobile IPv6 Options classes


_mobopttypes = { 2: "Binding Refresh Advice",
                 3: "Alternate Care-of Address",
                 4: "Nonce Indices",
                 5: "Binding Authorization Data",
                 6: "Mobile Network Prefix (RFC3963)",
                 7: "Link-Layer Address (RFC4068)",
                 8: "Mobile Node Identifier (RFC4283)", 
                 9: "Mobility Message Authentication (RFC4285)",
                 10: "Replay Protection (RFC4285)",
                 11: "CGA Parameters Request (RFC4866)",
                 12: "CGA Parameters (RFC4866)",
                 13: "Signature (RFC4866)",
                 14: "Home Keygen Token (RFC4866)",
                 15: "Care-of Test Init (RFC4866)",
                 16: "Care-of Test (RFC4866)" }


class _MIP6OptAlign: 
    """ Mobile IPv6 options have alignment requirements of the form x*n+y. 
    This class is inherited by all MIPv6 options to help in computing the 
    required Padding for that option, i.e. the need for a Pad1 or PadN 
    option before it. They only need to provide x and y as class 
    parameters. (x=0 and y=0 are used when no alignment is required)"""
    def alignment_delta(self, curpos):
      x = self.x ; y = self.y
      if x == 0 and y ==0:
          return 0
      delta = x*((curpos - y + x - 1)/x) + y - curpos
      return delta
    

class MIP6OptBRAdvice(_MIP6OptAlign, Packet):
    name = 'Mobile IPv6 Option - Binding Refresh Advice' 
    fields_desc = [ ByteEnumField('otype', 2, _mobopttypes),
                    ByteField('olen', 2),
                    ShortField('rinter', 0) ] 
    x = 2 ; y = 0# alignment requirement: 2n

class MIP6OptAltCoA(_MIP6OptAlign, Packet):
    name = 'MIPv6 Option - Alternate Care-of Address'
    fields_desc = [ ByteEnumField('otype', 3, _mobopttypes),
                    ByteField('olen', 16),
                    IP6Field("acoa", "::") ]
    x = 8 ; y = 6 # alignment requirement: 8n+6

class MIP6OptNonceIndices(_MIP6OptAlign, Packet):                 
    name = 'MIPv6 Option - Nonce Indices'
    fields_desc = [ ByteEnumField('otype', 4, _mobopttypes),
                    ByteField('olen', 16),
                    ShortField('hni', 0),
                    ShortField('coni', 0) ]
    x = 2 ; y = 0 # alignment requirement: 2n

class MIP6OptBindingAuthData(_MIP6OptAlign, Packet):              
    name = 'MIPv6 Option - Binding Authorization Data'
    fields_desc = [ ByteEnumField('otype', 5, _mobopttypes),
                    ByteField('olen', 16),
                    BitField('authenticator', 0, 96) ]
    x = 8 ; y = 2 # alignment requirement: 8n+2

class MIP6OptMobNetPrefix(_MIP6OptAlign, Packet): # NEMO - RFC 3963 
    name = 'NEMO Option - Mobile Network Prefix'
    fields_desc = [ ByteEnumField("otype", 6, _mobopttypes),
                    ByteField("olen", 18),
                    ByteField("reserved", 0),
                    ByteField("plen", 64),
                    IP6Field("prefix", "::") ]
    x = 8 ; y = 4 # alignment requirement: 8n+4

class MIP6OptLLAddr(_MIP6OptAlign, Packet): # Sect 6.4.4 of RFC 4068
    name = "MIPv6 Option - Link-Layer Address (MH-LLA)"
    fields_desc = [ ByteEnumField("otype", 7, _mobopttypes),
                    ByteField("olen", 7),
                    ByteEnumField("ocode", 2, _rfc4068_lla_optcode),
                    ByteField("pad", 0),
                    MACField("lla", ETHER_ANY) ] # Only support ethernet
    x = 0 ; y = 0 # alignment requirement: none

class MIP6OptMNID(_MIP6OptAlign, Packet): # RFC 4283
    name = "MIPv6 Option - Mobile Node Identifier"
    fields_desc = [ ByteEnumField("otype", 8, _mobopttypes),
                    FieldLenField("olen", None, length_of="id", fmt="B",
                                  adjust = lambda pkt,x: x+1),
                    ByteEnumField("subtype", 1, {1: "NAI"}),
                    StrLenField("id", "",
                                length_from = lambda pkt: pkt.olen-1) ]
    x = 0 ; y = 0 # alignment requirement: none

# We only support decoding and basic build. Automatic HMAC computation is 
# too much work for our current needs. It is left to the user (I mean ... 
# you). --arno
class MIP6OptMsgAuth(_MIP6OptAlign, Packet): # RFC 4285 (Sect. 5)
    name = "MIPv6 Option - Mobility Message Authentication"
    fields_desc = [ ByteEnumField("otype", 9, _mobopttypes),
                    FieldLenField("olen", None, length_of="authdata", fmt="B",
                                  adjust = lambda pkt,x: x+5),
                    ByteEnumField("subtype", 1, {1: "MN-HA authentication mobility option",
                                                 2: "MN-AAA authentication mobility option"}),
                    IntField("mspi", None),
                    StrLenField("authdata", "A"*12,
                                length_from = lambda pkt: pkt.olen-5) ]
    x = 4 ; y = 1 # alignment requirement: 4n+1

# Extracted from RFC 1305 (NTP) :
# NTP timestamps are represented as a 64-bit unsigned fixed-point number, 
# in seconds relative to 0h on 1 January 1900. The integer part is in the 
# first 32 bits and the fraction part in the last 32 bits.
class NTPTimestampField(LongField):
    epoch = (1900, 1, 1, 0, 0, 0, 5, 1, 0)
    def i2repr(self, pkt, x):
        if x < ((50*31536000)<<32):
            return "Some date a few decades ago (%d)" % x

        # delta from epoch (= (1900, 1, 1, 0, 0, 0, 5, 1, 0)) to 
        # January 1st 1970 :
        delta = -2209075761
        i = int(x >> 32)
        j = float(x & 0xffffffff) * 2.0**-32
        res = i + j + delta
        from time import strftime
        t = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(res))

        return "%s (%d)" % (t, x)

class MIP6OptReplayProtection(_MIP6OptAlign, Packet): # RFC 4285 (Sect. 6)
    name = "MIPv6 option - Replay Protection"
    fields_desc = [ ByteEnumField("otype", 10, _mobopttypes),
                    ByteField("olen", 8),
                    NTPTimestampField("timestamp", 0) ]
    x = 8 ; y = 2 # alignment requirement: 8n+2

class MIP6OptCGAParamsReq(_MIP6OptAlign, Packet): # RFC 4866 (Sect. 5.6)
    name = "MIPv6 option - CGA Parameters Request"
    fields_desc = [ ByteEnumField("otype", 11, _mobopttypes),
                    ByteField("olen", 0) ]
    x = 0 ; y = 0 # alignment requirement: none

# XXX TODO: deal with CGA param fragmentation and build of defragmented
# XXX       version. Passing of a big CGAParam structure should be 
# XXX       simplified. Make it hold packets, by the way  --arno
class MIP6OptCGAParams(_MIP6OptAlign, Packet): # RFC 4866 (Sect. 5.1)
    name = "MIPv6 option - CGA Parameters"
    fields_desc = [ ByteEnumField("otype", 12, _mobopttypes),
                    FieldLenField("olen", None, length_of="cgaparams", fmt="B"),
                    StrLenField("cgaparams", "",
                                length_from = lambda pkt: pkt.olen) ]
    x = 0 ; y = 0 # alignment requirement: none

class MIP6OptSignature(_MIP6OptAlign, Packet): # RFC 4866 (Sect. 5.2)
    name = "MIPv6 option - Signature"
    fields_desc = [ ByteEnumField("otype", 13, _mobopttypes),
                    FieldLenField("olen", None, length_of="sig", fmt="B"),
                    StrLenField("sig", "",
                                length_from = lambda pkt: pkt.olen) ]
    x = 0 ; y = 0 # alignment requirement: none

class MIP6OptHomeKeygenToken(_MIP6OptAlign, Packet): # RFC 4866 (Sect. 5.3)
    name = "MIPv6 option - Home Keygen Token"
    fields_desc = [ ByteEnumField("otype", 14, _mobopttypes),
                    FieldLenField("olen", None, length_of="hkt", fmt="B"),
                    StrLenField("hkt", "",
                                length_from = lambda pkt: pkt.olen) ]
    x = 0 ; y = 0 # alignment requirement: none

class MIP6OptCareOfTestInit(_MIP6OptAlign, Packet): # RFC 4866 (Sect. 5.4)
    name = "MIPv6 option - Care-of Test Init"
    fields_desc = [ ByteEnumField("otype", 15, _mobopttypes),
                    ByteField("olen", 0) ]
    x = 0 ; y = 0 # alignment requirement: none

class MIP6OptCareOfTest(_MIP6OptAlign, Packet): # RFC 4866 (Sect. 5.5)
    name = "MIPv6 option - Care-of Test"
    fields_desc = [ ByteEnumField("otype", 16, _mobopttypes),
                    FieldLenField("olen", None, length_of="cokt", fmt="B"),
                    StrLenField("cokt", '\x00'*8,
                                length_from = lambda pkt: pkt.olen) ]
    x = 0 ; y = 0 # alignment requirement: none

class MIP6OptUnknown(_MIP6OptAlign, Packet):
    name = 'Scapy6 - Unknown Mobility Option'
    fields_desc = [ ByteEnumField("otype", 6, _mobopttypes),
                    FieldLenField("olen", None, length_of="odata", fmt="B"),
                    StrLenField("odata", "",
                                length_from = lambda pkt: pkt.olen) ]
    x = 0 ; y = 0 # alignment requirement: none

moboptcls = {  0: Pad1,
               1: PadN,
               2: MIP6OptBRAdvice,
               3: MIP6OptAltCoA,
               4: MIP6OptNonceIndices,
               5: MIP6OptBindingAuthData,
               6: MIP6OptMobNetPrefix,
               7: MIP6OptLLAddr,
               8: MIP6OptMNID, 
               9: MIP6OptMsgAuth,
              10: MIP6OptReplayProtection,
              11: MIP6OptCGAParamsReq,
              12: MIP6OptCGAParams,
              13: MIP6OptSignature,
              14: MIP6OptHomeKeygenToken,
              15: MIP6OptCareOfTestInit,
              16: MIP6OptCareOfTest }


# Main Mobile IPv6 Classes

mhtypes = {  0: 'BRR',
             1: 'HoTI',
             2: 'CoTI',
             3: 'HoT',
             4: 'CoT',
             5: 'BU',
             6: 'BA',
             7: 'BE',
             8: 'Fast BU',
             9: 'Fast BA',
            10: 'Fast NA' }

# From http://www.iana.org/assignments/mobility-parameters 
bastatus = {   0: 'Binding Update accepted',
               1: 'Accepted but prefix discovery necessary',
             128: 'Reason unspecified',
             129: 'Administratively prohibited',
             130: 'Insufficient resources',
             131: 'Home registration not supported',
             132: 'Not home subnet',
             133: 'Not home agent for this mobile node',
             134: 'Duplicate Address Detection failed',
             135: 'Sequence number out of window',
             136: 'Expired home nonce index',
             137: 'Expired care-of nonce index',
             138: 'Expired nonces',
             139: 'Registration type change disallowed',
             140: 'Mobile Router Operation not permitted',
             141: 'Invalid Prefix',
             142: 'Not Authorized for Prefix',
             143: 'Forwarding Setup failed (prefixes missing)',
             144: 'MIPV6-ID-MISMATCH',
             145: 'MIPV6-MESG-ID-REQD',
             146: 'MIPV6-AUTH-FAIL',
             147: 'Permanent home keygen token unavailable',
             148: 'CGA and signature verification failed',
             149: 'Permanent home keygen token exists',
             150: 'Non-null home nonce index expected' }


class _MobilityHeader(Packet):
    name = 'Dummy IPv6 Mobility Header'
    overload_fields = { IPv6: { "nh": 135 }}

    def post_build(self, p, pay):
        p += pay
        l = self.len
        if self.len is None:
            l = (len(p)-8)/8
        p = p[0] + struct.pack("B", l) + p[2:]
        if self.cksum is None:
            cksum = in6_chksum(135, self.underlayer, p)
        else:
            cksum = self.cksum
        p = p[:4]+struct.pack("!H", cksum)+p[6:]
        return p


class MIP6MH_Generic(_MobilityHeader): # Mainly for decoding of unknown msg
    name = "IPv6 Mobility Header - Generic Message"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    ByteField("len", None),
                    ByteEnumField("mhtype", None, mhtypes),
                    ByteField("res", None),
                    XShortField("cksum", None),
                    StrLenField("msg", "\x00"*2,
                                length_from = lambda pkt: 8*pkt.len-6) ]


    
# TODO: make a generic _OptionsField
class _MobilityOptionsField(PacketListField):
    islist = 1
    holds_packet = 1

    def __init__(self, name, default, cls, curpos, count_from=None, length_from=None):
        self.curpos = curpos
        PacketListField.__init__(self, name, default, cls, count_from=count_from, length_from=length_from)
    
    def getfield(self, pkt, s):
        l = self.length_from(pkt)
        return s[l:],self.m2i(pkt, s[:l])

    def i2len(self, pkt, i):
        return len(self.i2m(pkt, i))

    def m2i(self, pkt, x):
        opt = []
        while x:
            o = ord(x[0]) # Option type
            cls = self.cls
            if moboptcls.has_key(o):
                cls = moboptcls[o]
            try:
                op = cls(x)
            except:
                op = self.cls(x)
            opt.append(op)
            if isinstance(op.payload, Raw):
                x = op.payload.load
                del(op.payload)
            else:
                x = ""
        return opt

    def i2m(self, pkt, x):
        autopad = None
        try:
            autopad = getattr(pkt, "autopad") # Hack : 'autopad' phantom field
        except:
            autopad = 1
            
        if not autopad:
            return "".join(map(str, x))

        curpos = self.curpos
        s = ""
        for p in x:
            d = p.alignment_delta(curpos)
            curpos += d
            if d == 1:
                s += str(Pad1())
            elif d != 0:
                s += str(PadN(optdata='\x00'*(d-2)))
            pstr = str(p)
            curpos += len(pstr)
            s += pstr
            
        # Let's make the class including our option field
        # a multiple of 8 octets long
        d = curpos % 8
        if d == 0:
            return s
        d = 8 - d
        if d == 1:
            s += str(Pad1())
        elif d != 0:
            s += str(PadN(optdata='\x00'*(d-2)))        

        return s

    def addfield(self, pkt, s, val):
        return s+self.i2m(pkt, val)

class MIP6MH_BRR(_MobilityHeader):
    name = "IPv6 Mobility Header - Binding Refresh Request"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    ByteField("len", None),
                    ByteEnumField("mhtype", 0, mhtypes),                    
                    ByteField("res", None),
                    XShortField("cksum", None),
                    ShortField("res2", None),                    
                    _PhantomAutoPadField("autopad", 1), # autopad activated by default
                    _MobilityOptionsField("options", [], MIP6OptUnknown, 8,
                                          length_from = lambda pkt: 8*pkt.len) ]
    overload_fields = { IPv6: { "nh": 135 } }
    def hashret(self): 
        # Hack: BRR, BU and BA have the same hashret that returns the same
        #       value "\x00\x08\x09" (concatenation of mhtypes). This is
        #       because we need match BA with BU and BU with BRR. --arno
        return "\x00\x08\x09"

class MIP6MH_HoTI(_MobilityHeader):
    name = "IPv6 Mobility Header - Home Test Init"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    ByteField("len", None),
                    ByteEnumField("mhtype", 1, mhtypes),                    
                    ByteField("res", None),
                    XShortField("cksum", None),                    
                    StrFixedLenField("cookie", "\x00"*8, 8),
                    _PhantomAutoPadField("autopad", 1), # autopad activated by default
                    _MobilityOptionsField("options", [], MIP6OptUnknown, 16,
                                          length_from = lambda pkt: 8*(pkt.len-1)) ]
    overload_fields = { IPv6: { "nh": 135 } }
    def hashret(self):
        return self.cookie

class MIP6MH_CoTI(MIP6MH_HoTI):
    name = "IPv6 Mobility Header - Care-of Test Init"
    mhtype = 2
    def hashret(self):
        return self.cookie

class MIP6MH_HoT(_MobilityHeader):
    name = "IPv6 Mobility Header - Home Test"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    ByteField("len", None),
                    ByteEnumField("mhtype", 3, mhtypes),                    
                    ByteField("res", None),
                    XShortField("cksum", None),                    
                    ShortField("index", None),
                    StrFixedLenField("cookie", "\x00"*8, 8),
                    StrFixedLenField("token", "\x00"*8, 8),
                    _PhantomAutoPadField("autopad", 1), # autopad activated by default
                    _MobilityOptionsField("options", [], MIP6OptUnknown, 24,
                                          length_from = lambda pkt: 8*(pkt.len-2)) ]
    overload_fields = { IPv6: { "nh": 135 } }
    def hashret(self):
        return self.cookie
    def answers(self):
        if (isinstance(other, MIP6MH_HoTI) and
            self.cookie == other.cookie):
            return 1
        return 0

class MIP6MH_CoT(MIP6MH_HoT):
    name = "IPv6 Mobility Header - Care-of Test"
    mhtype = 4
    def hashret(self):
        return self.cookie

    def answers(self):
        if (isinstance(other, MIP6MH_CoTI) and
            self.cookie == other.cookie):
            return 1
        return 0

class LifetimeField(ShortField):
    def i2repr(self, pkt, x):
        return "%d sec" % (4*x)

class MIP6MH_BU(_MobilityHeader):
    name = "IPv6 Mobility Header - Binding Update"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    ByteField("len", None), # unit == 8 bytes (excluding the first 8 bytes)
                    ByteEnumField("mhtype", 5, mhtypes),
                    ByteField("res", None),
                    XShortField("cksum", None),
                    XShortField("seq", None), # TODO: ShortNonceField
                    FlagsField("flags", "KHA", 7, "PRMKLHA"),
                    XBitField("reserved", 0, 9),
                    LifetimeField("mhtime", 3), # unit == 4 seconds
                    _PhantomAutoPadField("autopad", 1), # autopad activated by default
                    _MobilityOptionsField("options", [], MIP6OptUnknown, 12,
                                          length_from = lambda pkt: 8*pkt.len - 4) ]
    overload_fields = { IPv6: { "nh": 135 } }

    def hashret(self): # Hack: see comment in MIP6MH_BRR.hashret()
        return "\x00\x08\x09"

    def answers(self, other): 
        if isinstance(other, MIP6MH_BRR):
            return 1
        return 0

class MIP6MH_BA(_MobilityHeader):
    name = "IPv6 Mobility Header - Binding ACK"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    ByteField("len", None), # unit == 8 bytes (excluding the first 8 bytes)
                    ByteEnumField("mhtype", 6, mhtypes),
                    ByteField("res", None),
                    XShortField("cksum", None),
                    ByteEnumField("status", 0, bastatus),
                    FlagsField("flags", "K", 3, "PRK"),
                    XBitField("res2", None, 5),
                    XShortField("seq", None), # TODO: ShortNonceField
                    XShortField("mhtime", 0), # unit == 4 seconds
                    _PhantomAutoPadField("autopad", 1), # autopad activated by default
                    _MobilityOptionsField("options", [], MIP6OptUnknown, 12,
                                          length_from = lambda pkt: 8*pkt.len-4) ]
    overload_fields = { IPv6: { "nh": 135 }}

    def hashret(self): # Hack: see comment in MIP6MH_BRR.hashret()
        return "\x00\x08\x09"

    def answers(self, other):
        if (isinstance(other, MIP6MH_BU) and
            other.mhtype == 5 and
            self.mhtype == 6 and
            other.flags & 0x1 and # Ack request flags is set
            self.seq == other.seq):
            return 1
        return 0

_bestatus = { 1: 'Unknown binding for Home Address destination option',
              2: 'Unrecognized MH Type value' }

# TODO: match Binding Error to its stimulus
class MIP6MH_BE(_MobilityHeader):
    name = "IPv6 Mobility Header - Binding Error"
    fields_desc = [ ByteEnumField("nh", 59, ipv6nh),
                    ByteField("len", None), # unit == 8 bytes (excluding the first 8 bytes)
                    ByteEnumField("mhtype", 7, mhtypes),
                    ByteField("res", 0),
                    XShortField("cksum", None),
                    ByteEnumField("status", 0, _bestatus),
                    ByteField("reserved", 0),
                    IP6Field("ha", "::"),
                    _MobilityOptionsField("options", [], MIP6OptUnknown, 24,
                                          length_from = lambda pkt: 8*(pkt.len-2)) ]
    overload_fields = { IPv6: { "nh": 135 }}

_mip6_mhtype2cls = { 0: MIP6MH_BRR,
                     1: MIP6MH_HoTI,
                     2: MIP6MH_CoTI,
                     3: MIP6MH_HoT,
                     4: MIP6MH_CoT,
                     5: MIP6MH_BU,
                     6: MIP6MH_BA,
                     7: MIP6MH_BE }


#############################################################################
#############################################################################
###                             Traceroute6                               ###
#############################################################################
#############################################################################

class  AS_resolver6(AS_resolver_riswhois):
    def _resolve_one(self, ip):
        """
        overloaded version to provide a Whois resolution on the
        embedded IPv4 address if the address is 6to4 or Teredo. 
        Otherwise, the native IPv6 address is passed.
        """

        if in6_isaddr6to4(ip): # for 6to4, use embedded @
            tmp = inet_pton(socket.AF_INET6, ip)
            addr = inet_ntop(socket.AF_INET, tmp[2:6])
        elif in6_isaddrTeredo(ip): # for Teredo, use mapped address
            addr = teredoAddrExtractInfo(ip)[2]
        else:
            addr = ip
        
        _, asn, desc = AS_resolver_riswhois._resolve_one(self, addr)

        return ip,asn,desc        

class TracerouteResult6(TracerouteResult):
    def show(self):
        return self.make_table(lambda (s,r): (s.sprintf("%-42s,IPv6.dst%:{TCP:tcp%TCP.dport%}{UDP:udp%UDP.dport%}{ICMPv6EchoRequest:IER}"), # TODO: ICMPv6 !
                                              s.hlim,
                                              r.sprintf("%-42s,IPv6.src% {TCP:%TCP.flags%}"+
                                                        "{ICMPv6DestUnreach:%ir,type%}{ICMPv6PacketTooBig:%ir,type%}"+
                                                        "{ICMPv6TimeExceeded:%ir,type%}{ICMPv6ParamProblem:%ir,type%}"+
                                                        "{ICMPv6EchoReply:%ir,type%}")))

    def get_trace(self):
        trace = {}

        for s,r in self.res:
            if IPv6 not in s:
                continue
            d = s[IPv6].dst
            if d not in trace:
                trace[d] = {}
               
            t = not (ICMPv6TimeExceeded in r or 
                     ICMPv6DestUnreach in r or
                     ICMPv6PacketTooBig in r or
                     ICMPv6ParamProblem in r)

            trace[d][s[IPv6].hlim] = r[IPv6].src, t

        for k in trace.values():
            m = filter(lambda x: k[x][1], k.keys())
            if not m:
                continue
            m = min(m)
            for l in k.keys():
                if l > m:
                    del(k[l])

        return trace

    def graph(self, ASres=AS_resolver6(), **kargs):
        TracerouteResult.graph(self, ASres=ASres, **kargs)
    
def traceroute6(target, dport=80, minttl=1, maxttl=30, sport=RandShort(), 
                l4 = None, timeout=2, verbose=None, **kargs):
    """
    Instant TCP traceroute using IPv6 :
    traceroute6(target, [maxttl=30], [dport=80], [sport=80]) -> None
    """
    if verbose is None:
        verbose = conf.verb

    if l4 is None:
        a,b = sr(IPv6(dst=target, hlim=(minttl,maxttl))/TCP(seq=RandInt(),sport=sport, dport=dport),
                 timeout=timeout, filter="icmp6 or tcp", verbose=verbose, **kargs)
    else:
        a,b = sr(IPv6(dst=target, hlim=(minttl,maxttl))/l4,
                 timeout=timeout, verbose=verbose, **kargs)

    a = TracerouteResult6(a.res)

    if verbose:
        a.display()

    return a,b

#############################################################################
#############################################################################
###                                Sockets                                ###
#############################################################################
#############################################################################

class L3RawSocket6(L3RawSocket):
    def __init__(self, type = ETH_P_IPV6, filter=None, iface=None, promisc=None, nofilter=0):
        L3RawSocket.__init__(self, type, filter, iface, promisc)
        # NOTE: if fragmentation is needed, it will be done by the kernel (RFC 2292)
        self.outs = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_RAW)
        self.ins = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(type))

def IPv6inIP(dst='203.178.135.36', src=None):
  _IPv6inIP.dst = dst
  _IPv6inIP.src = src
  if not conf.L3socket == _IPv6inIP:
    _IPv6inIP.cls = conf.L3socket
  else:
    del(conf.L3socket)
  return _IPv6inIP

class _IPv6inIP(SuperSocket):
  dst = '127.0.0.1'
  src = None
  cls = None

  def __init__(self, family=socket.AF_INET6, type=socket.SOCK_STREAM, proto=0, **args):
    SuperSocket.__init__(self, family, type, proto)
    self.worker = self.cls(**args)

  def set(self, dst, src=None):
    _IPv6inIP.src = src
    _IPv6inIP.dst = dst

  def nonblock_recv(self):
    p = self.worker.nonblock_recv()
    return self._recv(p)

  def recv(self, x):
    p = self.worker.recv(x)
    return self._recv(p, x)

  def _recv(self, p, x=MTU):
    if p is None:
      return p
    elif isinstance(p, IP):
      # TODO: verify checksum
      if p.src == self.dst and p.proto == socket.IPPROTO_IPV6:
        if isinstance(p.payload, IPv6):
          return p.payload
    return p

  def send(self, x):
    return self.worker.send(IP(dst=self.dst, src=self.src, proto=socket.IPPROTO_IPV6)/x)


#############################################################################
#############################################################################
###                          Layers binding                               ###
#############################################################################
#############################################################################

conf.l3types.register(ETH_P_IPV6, IPv6)
conf.l2types.register(31, IPv6)

bind_layers(Ether,     IPv6,     type = 0x86dd )
bind_layers(CookedLinux, IPv6,   proto = 0x86dd )
bind_layers(IPerror6,  TCPerror, nh = socket.IPPROTO_TCP )
bind_layers(IPerror6,  UDPerror, nh = socket.IPPROTO_UDP )
bind_layers(IPv6,      TCP,      nh = socket.IPPROTO_TCP )
bind_layers(IPv6,      UDP,      nh = socket.IPPROTO_UDP )
bind_layers(IP,        IPv6,     proto = socket.IPPROTO_IPV6 )
bind_layers(IPv6,      IPv6,     nh = socket.IPPROTO_IPV6 )


########NEW FILE########
__FILENAME__ = ir
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
IrDA infrared data communication.
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.l2 import CookedLinux



# IR

class IrLAPHead(Packet):
    name = "IrDA Link Access Protocol Header"
    fields_desc = [ XBitField("Address", 0x7f, 7),
                    BitEnumField("Type", 1, 1, {"Response":0,
                                                "Command":1})]

class IrLAPCommand(Packet):
    name = "IrDA Link Access Protocol Command"
    fields_desc = [ XByteField("Control", 0),
                    XByteField("Format identifier", 0),
                    XIntField("Source address", 0),
                    XIntField("Destination address", 0xffffffffL),
                    XByteField("Discovery flags", 0x1),
                    ByteEnumField("Slot number", 255, {"final":255}),
                    XByteField("Version", 0)]


class IrLMP(Packet):
    name = "IrDA Link Management Protocol"
    fields_desc = [ XShortField("Service hints", 0),
                    XByteField("Character set", 0),
                    StrField("Device name", "") ]


bind_layers( CookedLinux,   IrLAPHead,     proto=23)
bind_layers( IrLAPHead,     IrLAPCommand,  Type=1)
bind_layers( IrLAPCommand,  IrLMP,         )

########NEW FILE########
__FILENAME__ = isakmp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
ISAKMP (Internet Security Association and Key Management Protocol).
"""

import struct
from scapy.packet import *
from scapy.fields import *
from scapy.ansmachine import *
from scapy.layers.inet import IP,UDP
from scapy.sendrecv import sr


# see http://www.iana.org/assignments/ipsec-registry for details
ISAKMPAttributeTypes= { "Encryption":    (1, { "DES-CBC"  : 1,
                                                "IDEA-CBC" : 2,
                                                "Blowfish-CBC" : 3,
                                                "RC5-R16-B64-CBC" : 4,
                                                "3DES-CBC" : 5, 
                                                "CAST-CBC" : 6, 
                                                "AES-CBC" : 7, 
                                                "CAMELLIA-CBC" : 8, }, 0),
                         "Hash":          (2, { "MD5": 1,
                                                "SHA": 2,
                                                "Tiger": 3,
                                                "SHA2-256": 4,
                                                "SHA2-384": 5,
                                                "SHA2-512": 6,}, 0),
                         "Authentication":(3, { "PSK": 1, 
                                                "DSS": 2,
                                                "RSA Sig": 3,
                                                "RSA Encryption": 4,
                                                "RSA Encryption Revised": 5,
                                                "ElGamal Encryption": 6,
                                                "ElGamal Encryption Revised": 7,
                                                "ECDSA Sig": 8,
                                                "HybridInitRSA": 64221,
                                                "HybridRespRSA": 64222,
                                                "HybridInitDSS": 64223,
                                                "HybridRespDSS": 64224,
                                                "XAUTHInitPreShared": 65001,
                                                "XAUTHRespPreShared": 65002,
                                                "XAUTHInitDSS": 65003,
                                                "XAUTHRespDSS": 65004,
                                                "XAUTHInitRSA": 65005,
                                                "XAUTHRespRSA": 65006,
                                                "XAUTHInitRSAEncryption": 65007,
                                                "XAUTHRespRSAEncryption": 65008,
                                                "XAUTHInitRSARevisedEncryption": 65009,
                                                "XAUTHRespRSARevisedEncryptio": 65010, }, 0),
                         "GroupDesc":     (4, { "768MODPgr"  : 1,
                                                "1024MODPgr" : 2, 
                                                "EC2Ngr155"  : 3,
                                                "EC2Ngr185"  : 4,
                                                "1536MODPgr" : 5, 
                                                "2048MODPgr" : 14, 
                                                "3072MODPgr" : 15, 
                                                "4096MODPgr" : 16, 
                                                "6144MODPgr" : 17, 
                                                "8192MODPgr" : 18, }, 0),
                         "GroupType":      (5,  {"MODP":       1,
                                                 "ECP":        2,
                                                 "EC2N":       3}, 0),
                         "GroupPrime":     (6,  {}, 1),
                         "GroupGenerator1":(7,  {}, 1),
                         "GroupGenerator2":(8,  {}, 1),
                         "GroupCurveA":    (9,  {}, 1),
                         "GroupCurveB":    (10, {}, 1),
                         "LifeType":       (11, {"Seconds":     1,
                                                 "Kilobytes":   2,  }, 0),
                         "LifeDuration":   (12, {}, 1),
                         "PRF":            (13, {}, 0),
                         "KeyLength":      (14, {}, 0),
                         "FieldSize":      (15, {}, 0),
                         "GroupOrder":     (16, {}, 1),
                         }

# the name 'ISAKMPTransformTypes' is actually a misnomer (since the table 
# holds info for all ISAKMP Attribute types, not just transforms, but we'll 
# keep it for backwards compatibility... for now at least
ISAKMPTransformTypes = ISAKMPAttributeTypes

ISAKMPTransformNum = {}
for n in ISAKMPTransformTypes:
    val = ISAKMPTransformTypes[n]
    tmp = {}
    for e in val[1]:
        tmp[val[1][e]] = e
    ISAKMPTransformNum[val[0]] = (n,tmp, val[2])
del(n)
del(e)
del(tmp)
del(val)


class ISAKMPTransformSetField(StrLenField):
    islist=1
    def type2num(self, (typ,val)):
        type_val,enc_dict,tlv = ISAKMPTransformTypes.get(typ, (typ,{},0))
        val = enc_dict.get(val, val)
        s = ""
        if (val & ~0xffff):
            if not tlv:
                warning("%r should not be TLV but is too big => using TLV encoding" % typ)
            n = 0
            while val:
                s = chr(val&0xff)+s
                val >>= 8
                n += 1
            val = n
        else:
            type_val |= 0x8000
        return struct.pack("!HH",type_val, val)+s
    def num2type(self, typ, enc):
        val = ISAKMPTransformNum.get(typ,(typ,{}))
        enc = val[1].get(enc,enc)
        return (val[0],enc)
    def i2m(self, pkt, i):
        if i is None:
            return ""
        i = map(self.type2num, i)
        return "".join(i)
    def m2i(self, pkt, m):
        # I try to ensure that we don't read off the end of our packet based
        # on bad length fields we're provided in the packet. There are still
        # conditions where struct.unpack() may not get enough packet data, but
        # worst case that should result in broken attributes (which would
        # be expected). (wam)
        lst = []
        while len(m) >= 4:
            trans_type, = struct.unpack("!H", m[:2])
            is_tlv = not (trans_type & 0x8000)
            if is_tlv:
                # We should probably check to make sure the attribute type we
                # are looking at is allowed to have a TLV format and issue a 
                # warning if we're given an TLV on a basic attribute.
                value_len, = struct.unpack("!H", m[2:4])
                if value_len+4 > len(m):
                    warning("Bad length for ISAKMP tranform type=%#6x" % trans_type)
                value = m[4:4+value_len]
                value = reduce(lambda x,y: (x<<8L)|y, struct.unpack("!%s" % ("B"*len(value),), value),0)
            else:
                trans_type &= 0x7fff
                value_len=0
                value, = struct.unpack("!H", m[2:4])
            m=m[4+value_len:]
            lst.append(self.num2type(trans_type, value))
        if len(m) > 0:
            warning("Extra bytes after ISAKMP transform dissection [%r]" % m)
        return lst


ISAKMP_payload_type = ["None","SA","Proposal","Transform","KE","ID","CERT","CR","Hash",
                       "SIG","Nonce","Notification","Delete","VendorID"]

ISAKMP_exchange_type = ["None","base","identity prot.",
                        "auth only", "aggressive", "info"]


class ISAKMP_class(Packet):
    def guess_payload_class(self, payload):
        np = self.next_payload
        if np == 0:
            return Raw
        elif np < len(ISAKMP_payload_type):
            pt = ISAKMP_payload_type[np]
            return globals().get("ISAKMP_payload_%s" % pt, ISAKMP_payload)
        else:
            return ISAKMP_payload


class ISAKMP(ISAKMP_class): # rfc2408
    name = "ISAKMP"
    fields_desc = [
        StrFixedLenField("init_cookie","",8),
        StrFixedLenField("resp_cookie","",8),
        ByteEnumField("next_payload",0,ISAKMP_payload_type),
        XByteField("version",0x10),
        ByteEnumField("exch_type",0,ISAKMP_exchange_type),
        FlagsField("flags",0, 8, ["encryption","commit","auth_only","res3","res4","res5","res6","res7"]), # XXX use a Flag field
        IntField("id",0),
        IntField("length",None)
        ]

    def guess_payload_class(self, payload):
        if self.flags & 1:
            return Raw
        return ISAKMP_class.guess_payload_class(self, payload)

    def answers(self, other):
        if isinstance(other, ISAKMP):
            if other.init_cookie == self.init_cookie:
                return 1
        return 0
    def post_build(self, p, pay):
        p += pay
        if self.length is None:
            p = p[:24]+struct.pack("!I",len(p))+p[28:]
        return p
       



class ISAKMP_payload_Transform(ISAKMP_class):
    name = "IKE Transform"
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
#        ShortField("len",None),
        ShortField("length",None),
        ByteField("num",None),
        ByteEnumField("id",1,{1:"KEY_IKE"}),
        ShortField("res2",0),
        ISAKMPTransformSetField("transforms",None,length_from=lambda x:x.length-8)
#        XIntField("enc",0x80010005L),
#        XIntField("hash",0x80020002L),
#        XIntField("auth",0x80030001L),
#        XIntField("group",0x80040002L),
#        XIntField("life_type",0x800b0001L),
#        XIntField("durationh",0x000c0004L),
#        XIntField("durationl",0x00007080L),
        ]
    def post_build(self, p, pay):
        if self.length is None:
            l = len(p)
            p = p[:2]+chr((l>>8)&0xff)+chr(l&0xff)+p[4:]
        p += pay
        return p
            


        
class ISAKMP_payload_Proposal(ISAKMP_class):
    name = "IKE proposal"
#    ISAKMP_payload_type = 0
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
        FieldLenField("length",None,"trans","H", adjust=lambda pkt,x:x+8),
        ByteField("proposal",1),
        ByteEnumField("proto",1,{1:"ISAKMP"}),
        FieldLenField("SPIsize",None,"SPI","B"),
        ByteField("trans_nb",None),
        StrLenField("SPI","",length_from=lambda x:x.SPIsize),
        PacketLenField("trans",Raw(),ISAKMP_payload_Transform,length_from=lambda x:x.length-8),
        ]


class ISAKMP_payload(ISAKMP_class):
    name = "ISAKMP payload"
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
        FieldLenField("length",None,"load","H", adjust=lambda pkt,x:x+4),
        StrLenField("load","",length_from=lambda x:x.length-4),
        ]


class ISAKMP_payload_VendorID(ISAKMP_class):
    name = "ISAKMP Vendor ID"
    overload_fields = { ISAKMP: { "next_payload":13 }}
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
        FieldLenField("length",None,"vendorID","H", adjust=lambda pkt,x:x+4),
        StrLenField("vendorID","",length_from=lambda x:x.length-4),
        ]

class ISAKMP_payload_SA(ISAKMP_class):
    name = "ISAKMP SA"
    overload_fields = { ISAKMP: { "next_payload":1 }}
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
        FieldLenField("length",None,"prop","H", adjust=lambda pkt,x:x+12),
        IntEnumField("DOI",1,{1:"IPSEC"}),
        IntEnumField("situation",1,{1:"identity"}),
        PacketLenField("prop",Raw(),ISAKMP_payload_Proposal,length_from=lambda x:x.length-12),
        ]

class ISAKMP_payload_Nonce(ISAKMP_class):
    name = "ISAKMP Nonce"
    overload_fields = { ISAKMP: { "next_payload":10 }}
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
        FieldLenField("length",None,"load","H", adjust=lambda pkt,x:x+4),
        StrLenField("load","",length_from=lambda x:x.length-4),
        ]

class ISAKMP_payload_KE(ISAKMP_class):
    name = "ISAKMP Key Exchange"
    overload_fields = { ISAKMP: { "next_payload":4 }}
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
        FieldLenField("length",None,"load","H", adjust=lambda pkt,x:x+4),
        StrLenField("load","",length_from=lambda x:x.length-4),
        ]

class ISAKMP_payload_ID(ISAKMP_class):
    name = "ISAKMP Identification"
    overload_fields = { ISAKMP: { "next_payload":5 }}
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
        FieldLenField("length",None,"load","H",adjust=lambda pkt,x:x+8),
        ByteEnumField("IDtype",1,{1:"IPv4_addr", 11:"Key"}),
        ByteEnumField("ProtoID",0,{0:"Unused"}),
        ShortEnumField("Port",0,{0:"Unused"}),
#        IPField("IdentData","127.0.0.1"),
        StrLenField("load","",length_from=lambda x:x.length-8),
        ]



class ISAKMP_payload_Hash(ISAKMP_class):
    name = "ISAKMP Hash"
    overload_fields = { ISAKMP: { "next_payload":8 }}
    fields_desc = [
        ByteEnumField("next_payload",None,ISAKMP_payload_type),
        ByteField("res",0),
        FieldLenField("length",None,"load","H",adjust=lambda pkt,x:x+4),
        StrLenField("load","",length_from=lambda x:x.length-4),
        ]



ISAKMP_payload_type_overload = {}
for i in range(len(ISAKMP_payload_type)):
    name = "ISAKMP_payload_%s" % ISAKMP_payload_type[i]
    if name in globals():
        ISAKMP_payload_type_overload[globals()[name]] = {"next_payload":i}

del(i)
del(name)
ISAKMP_class.overload_fields = ISAKMP_payload_type_overload.copy()


bind_layers( UDP,           ISAKMP,        dport=500, sport=500)
def ikescan(ip):
    return sr(IP(dst=ip)/UDP()/ISAKMP(init_cookie=RandString(8),
                                      exch_type=2)/ISAKMP_payload_SA(prop=ISAKMP_payload_Proposal()))


########NEW FILE########
__FILENAME__ = l2
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Classes and functions for layer 2 protocols.
"""

import os,struct,time
from scapy.base_classes import Net
from scapy.config import conf
from scapy.packet import *
from scapy.ansmachine import *
from scapy.plist import SndRcvList
from scapy.fields import *
from scapy.sendrecv import srp,srp1
from scapy.arch import get_if_hwaddr




#################
## Tools       ##
#################


class Neighbor:
    def __init__(self):
        self.resolvers = {}

    def register_l3(self, l2, l3, resolve_method):
        self.resolvers[l2,l3]=resolve_method

    def resolve(self, l2inst, l3inst):
        k = l2inst.__class__,l3inst.__class__
        if k in self.resolvers:
            return self.resolvers[k](l2inst,l3inst)

    def __repr__(self):
        return "\n".join("%-15s -> %-15s" % (l2.__name__, l3.__name__) for l2,l3 in self.resolvers)

conf.neighbor = Neighbor()

conf.netcache.new_cache("arp_cache", 120) # cache entries expire after 120s


@conf.commands.register
def getmacbyip(ip, chainCC=0):
    """Return MAC address corresponding to a given IP address"""
    if isinstance(ip,Net):
        ip = iter(ip).next()
    tmp = map(ord, inet_aton(ip))
    if (tmp[0] & 0xf0) == 0xe0: # mcast @
        return "01:00:5e:%.2x:%.2x:%.2x" % (tmp[1]&0x7f,tmp[2],tmp[3])
    iff,a,gw = conf.route.route(ip)
    if ( (iff == "lo") or (ip == conf.route.get_if_bcast(iff)) ):
        return "ff:ff:ff:ff:ff:ff"
    if gw != "0.0.0.0":
        ip = gw

    mac = conf.netcache.arp_cache.get(ip)
    if mac:
        return mac

    res = srp1(Ether(dst=ETHER_BROADCAST)/ARP(op="who-has", pdst=ip),
               type=ETH_P_ARP,
               iface = iff,
               timeout=2,
               verbose=0,
               chainCC=chainCC,
               nofilter=1)
    if res is not None:
        mac = res.payload.hwsrc
        conf.netcache.arp_cache[ip] = mac
        return mac
    return None



### Fields

class DestMACField(MACField):
    def __init__(self, name):
        MACField.__init__(self, name, None)
    def i2h(self, pkt, x):
        if x is None:
            x = conf.neighbor.resolve(pkt,pkt.payload)
            if x is None:
                x = "ff:ff:ff:ff:ff:ff"
                warning("Mac address to reach destination not found. Using broadcast.")
        return MACField.i2h(self, pkt, x)
    def i2m(self, pkt, x):
        return MACField.i2m(self, pkt, self.i2h(pkt, x))
        
class SourceMACField(MACField):
    def __init__(self, name):
        MACField.__init__(self, name, None)
    def i2h(self, pkt, x):
        if x is None:
            iff,a,gw = pkt.payload.route()
            if iff:
                try:
                    x = get_if_hwaddr(iff)
                except:
                    pass
            if x is None:
                x = "00:00:00:00:00:00"
        return MACField.i2h(self, pkt, x)
    def i2m(self, pkt, x):
        return MACField.i2m(self, pkt, self.i2h(pkt, x))
        
class ARPSourceMACField(MACField):
    def __init__(self, name):
        MACField.__init__(self, name, None)
    def i2h(self, pkt, x):
        if x is None:
            iff,a,gw = pkt.route()
            if iff:
                try:
                    x = get_if_hwaddr(iff)
                except:
                    pass
            if x is None:
                x = "00:00:00:00:00:00"
        return MACField.i2h(self, pkt, x)
    def i2m(self, pkt, x):
        return MACField.i2m(self, pkt, self.i2h(pkt, x))



### Layers


class Ether(Packet):
    name = "Ethernet"
    fields_desc = [ DestMACField("dst"),
                    SourceMACField("src"),
                    XShortEnumField("type", 0x0000, ETHER_TYPES) ]
    def hashret(self):
        return struct.pack("H",self.type)+self.payload.hashret()
    def answers(self, other):
        if isinstance(other,Ether):
            if self.type == other.type:
                return self.payload.answers(other.payload)
        return 0
    def mysummary(self):
        return self.sprintf("%src% > %dst% (%type%)")
    @classmethod
    def dispatch_hook(cls, _pkt=None, *args, **kargs):
        if _pkt and len(_pkt) >= 14:
            if struct.unpack("!H", _pkt[12:14])[0] <= 1500:
                return Dot3
        return cls


class Dot3(Packet):
    name = "802.3"
    fields_desc = [ DestMACField("dst"),
                    MACField("src", ETHER_ANY),
                    LenField("len", None, "H") ]
    def extract_padding(self,s):
        l = self.len
        return s[:l],s[l:]
    def answers(self, other):
        if isinstance(other,Dot3):
            return self.payload.answers(other.payload)
        return 0
    def mysummary(self):
        return "802.3 %s > %s" % (self.src, self.dst)
    @classmethod
    def dispatch_hook(cls, _pkt=None, *args, **kargs):
        if _pkt and len(_pkt) >= 14:
            if struct.unpack("!H", _pkt[12:14])[0] > 1500:
                return Ether
        return cls


class LLC(Packet):
    name = "LLC"
    fields_desc = [ XByteField("dsap", 0x00),
                    XByteField("ssap", 0x00),
                    ByteField("ctrl", 0) ]

conf.neighbor.register_l3(Ether, LLC, lambda l2,l3: conf.neighbor.resolve(l2,l3.payload))
conf.neighbor.register_l3(Dot3, LLC, lambda l2,l3: conf.neighbor.resolve(l2,l3.payload))


class CookedLinux(Packet):
    name = "cooked linux"
    fields_desc = [ ShortEnumField("pkttype",0, {0: "unicast",
                                                 4:"sent-by-us"}), #XXX incomplete
                    XShortField("lladdrtype",512),
                    ShortField("lladdrlen",0),
                    StrFixedLenField("src","",8),
                    XShortEnumField("proto",0x800,ETHER_TYPES) ]
                    
                                   

class SNAP(Packet):
    name = "SNAP"
    fields_desc = [ X3BytesField("OUI",0x000000),
                    XShortEnumField("code", 0x000, ETHER_TYPES) ]

conf.neighbor.register_l3(Dot3, SNAP, lambda l2,l3: conf.neighbor.resolve(l2,l3.payload))


class Dot1Q(Packet):
    name = "802.1Q"
    aliastypes = [ Ether ]
    fields_desc =  [ BitField("prio", 0, 3),
                     BitField("id", 0, 1),
                     BitField("vlan", 1, 12),
                     XShortEnumField("type", 0x0000, ETHER_TYPES) ]
    def answers(self, other):
        if isinstance(other,Dot1Q):
            if ( (self.type == other.type) and
                 (self.vlan == other.vlan) ):
                return self.payload.answers(other.payload)
        else:
            return self.payload.answers(other)
        return 0
    def default_payload_class(self, pay):
        if self.type <= 1500:
            return LLC
        return Raw
    def extract_padding(self,s):
        if self.type <= 1500:
            return s[:self.type],s[self.type:]
        return s,None
    def mysummary(self):
        if isinstance(self.underlayer, Ether):
            return self.underlayer.sprintf("802.1q %Ether.src% > %Ether.dst% (%Dot1Q.type%) vlan %Dot1Q.vlan%")
        else:
            return self.sprintf("802.1q (%Dot1Q.type%) vlan %Dot1Q.vlan%")

            
conf.neighbor.register_l3(Ether, Dot1Q, lambda l2,l3: conf.neighbor.resolve(l2,l3.payload))

class STP(Packet):
    name = "Spanning Tree Protocol"
    fields_desc = [ ShortField("proto", 0),
                    ByteField("version", 0),
                    ByteField("bpdutype", 0),
                    ByteField("bpduflags", 0),
                    ShortField("rootid", 0),
                    MACField("rootmac", ETHER_ANY),
                    IntField("pathcost", 0),
                    ShortField("bridgeid", 0),
                    MACField("bridgemac", ETHER_ANY),
                    ShortField("portid", 0),
                    BCDFloatField("age", 1),
                    BCDFloatField("maxage", 20),
                    BCDFloatField("hellotime", 2),
                    BCDFloatField("fwddelay", 15) ]


class EAPOL(Packet):
    name = "EAPOL"
    fields_desc = [ ByteField("version", 1),
                    ByteEnumField("type", 0, ["EAP_PACKET", "START", "LOGOFF", "KEY", "ASF"]),
                    LenField("len", None, "H") ]
    
    EAP_PACKET= 0
    START = 1
    LOGOFF = 2
    KEY = 3
    ASF = 4
    def extract_padding(self, s):
        l = self.len
        return s[:l],s[l:]
    def hashret(self):
        return chr(self.type)+self.payload.hashret()
    def answers(self, other):
        if isinstance(other,EAPOL):
            if ( (self.type == self.EAP_PACKET) and
                 (other.type == self.EAP_PACKET) ):
                return self.payload.answers(other.payload)
        return 0
    def mysummary(self):
        return self.sprintf("EAPOL %EAPOL.type%")
             

class EAP(Packet):
    name = "EAP"
    fields_desc = [ ByteEnumField("code", 4, {1:"REQUEST",2:"RESPONSE",3:"SUCCESS",4:"FAILURE"}),
                    ByteField("id", 0),
                    ShortField("len",None),
                    ConditionalField(ByteEnumField("type",0, {1:"ID",4:"MD5"}), lambda pkt:pkt.code not in [EAP.SUCCESS, EAP.FAILURE])

                                     ]
    
    REQUEST = 1
    RESPONSE = 2
    SUCCESS = 3
    FAILURE = 4
    TYPE_ID = 1
    TYPE_MD5 = 4
    def answers(self, other):
        if isinstance(other,EAP):
            if self.code == self.REQUEST:
                return 0
            elif self.code == self.RESPONSE:
                if ( (other.code == self.REQUEST) and
                     (other.type == self.type) ):
                    return 1
            elif other.code == self.RESPONSE:
                return 1
        return 0
    
    def post_build(self, p, pay):
        if self.len is None:
            l = len(p)+len(pay)
            p = p[:2]+chr((l>>8)&0xff)+chr(l&0xff)+p[4:]
        return p+pay
             

class ARP(Packet):
    name = "ARP"
    fields_desc = [ XShortField("hwtype", 0x0001),
                    XShortEnumField("ptype",  0x0800, ETHER_TYPES),
                    ByteField("hwlen", 6),
                    ByteField("plen", 4),
                    ShortEnumField("op", 1, {"who-has":1, "is-at":2, "RARP-req":3, "RARP-rep":4, "Dyn-RARP-req":5, "Dyn-RAR-rep":6, "Dyn-RARP-err":7, "InARP-req":8, "InARP-rep":9}),
                    ARPSourceMACField("hwsrc"),
                    SourceIPField("psrc","pdst"),
                    MACField("hwdst", ETHER_ANY),
                    IPField("pdst", "0.0.0.0") ]
    who_has = 1
    is_at = 2
    def answers(self, other):
        if isinstance(other,ARP):
            if ( (self.op == self.is_at) and
                 (other.op == self.who_has) and
                 (self.psrc == other.pdst) ):
                return 1
        return 0
    def route(self):
        dst = self.pdst
        if isinstance(dst,Gen):
            dst = iter(dst).next()
        return conf.route.route(dst)
    def extract_padding(self, s):
        return "",s
    def mysummary(self):
        if self.op == self.is_at:
            return self.sprintf("ARP is at %hwsrc% says %psrc%")
        elif self.op == self.who_has:
            return self.sprintf("ARP who has %pdst% says %psrc%")
        else:
            return self.sprintf("ARP %op% %psrc% > %pdst%")
                 
conf.neighbor.register_l3(Ether, ARP, lambda l2,l3: getmacbyip(l3.pdst))

class GRErouting(Packet):
    name = "GRE routing informations"
    fields_desc = [ ShortField("address_family",0),
                    ByteField("SRE_offset", 0),
                    FieldLenField("SRE_len", None, "routing_info", "B"),
                    StrLenField("routing_info", "", "SRE_len"),
                    ]


class GRE(Packet):
    name = "GRE"
    fields_desc = [ BitField("chksum_present",0,1),
                    BitField("routing_present",0,1),
                    BitField("key_present",0,1),
                    BitField("seqnum_present",0,1),
                    BitField("strict_route_source",0,1),
                    BitField("recursion control",0,3),
                    BitField("flags",0,5),
                    BitField("version",0,3),
                    XShortEnumField("proto", 0x0000, ETHER_TYPES),
                    ConditionalField(XShortField("chksum",None), lambda pkt:pkt.chksum_present==1 or pkt.routing_present==1),
                    ConditionalField(XShortField("offset",None), lambda pkt:pkt.chksum_present==1 or pkt.routing_present==1),
                    ConditionalField(XIntField("key",None), lambda pkt:pkt.key_present==1),
                    ConditionalField(XIntField("seqence_number",None), lambda pkt:pkt.seqnum_present==1),
                    ]
    def post_build(self, p, pay):
        p += pay
        if self.chksum_present and self.chksum is None:
            c = checksum(p)
            p = p[:4]+chr((c>>8)&0xff)+chr(c&0xff)+p[6:]
        return p




bind_layers( Dot3,          LLC,           )
bind_layers( Ether,         LLC,           type=122)
bind_layers( Ether,         Dot1Q,         type=33024)
bind_layers( Ether,         Ether,         type=1)
bind_layers( Ether,         ARP,           type=2054)
bind_layers( Ether,         EAPOL,         type=34958)
bind_layers( Ether,         EAPOL,         dst='01:80:c2:00:00:03', type=34958)
bind_layers( CookedLinux,   LLC,           proto=122)
bind_layers( CookedLinux,   Dot1Q,         proto=33024)
bind_layers( CookedLinux,   Ether,         proto=1)
bind_layers( CookedLinux,   ARP,           proto=2054)
bind_layers( CookedLinux,   EAPOL,         proto=34958)
bind_layers( GRE,           LLC,           proto=122)
bind_layers( GRE,           Dot1Q,         proto=33024)
bind_layers( GRE,           Ether,         proto=1)
bind_layers( GRE,           ARP,           proto=2054)
bind_layers( GRE,           EAPOL,         proto=34958)
bind_layers( GRE,           GRErouting,    { "routing_present" : 1 } )
bind_layers( GRErouting,    Raw,           { "address_family" : 0, "SRE_len" : 0 })
bind_layers( GRErouting,    GRErouting,    { } )
bind_layers( EAPOL,         EAP,           type=0)
bind_layers( LLC,           STP,           dsap=66, ssap=66, ctrl=3)
bind_layers( LLC,           SNAP,          dsap=170, ssap=170, ctrl=3)
bind_layers( SNAP,          Dot1Q,         code=33024)
bind_layers( SNAP,          Ether,         code=1)
bind_layers( SNAP,          ARP,           code=2054)
bind_layers( SNAP,          EAPOL,         code=34958)
bind_layers( SNAP,          STP,           code=267)

conf.l2types.register(ARPHDR_ETHER, Ether)
conf.l2types.register_num2layer(ARPHDR_METRICOM, Ether)
conf.l2types.register_num2layer(ARPHDR_LOOPBACK, Ether)
conf.l2types.register_layer2num(ARPHDR_ETHER, Dot3)
conf.l2types.register(113, CookedLinux)
conf.l2types.register(144, CookedLinux)  # called LINUX_IRDA, similar to CookedLinux

conf.l3types.register(ETH_P_ARP, ARP)




### Technics



@conf.commands.register
def arpcachepoison(target, victim, interval=60):
    """Poison target's cache with (your MAC,victim's IP) couple
arpcachepoison(target, victim, [interval=60]) -> None
"""
    tmac = getmacbyip(target)
    p = Ether(dst=tmac)/ARP(op="who-has", psrc=victim, pdst=target)
    try:
        while 1:
            sendp(p, iface_hint=target)
            if conf.verb > 1:
                os.write(1,".")
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


class ARPingResult(SndRcvList):
    def __init__(self, res=None, name="ARPing", stats=None):
        SndRcvList.__init__(self, res, name, stats)

    def show(self):
        for s,r in self.res:
            print r.sprintf("%19s,Ether.src% %ARP.psrc%")



@conf.commands.register
def arping(net, timeout=2, cache=0, verbose=None, **kargs):
    """Send ARP who-has requests to determine which hosts are up
arping(net, [cache=0,] [iface=conf.iface,] [verbose=conf.verb]) -> None
Set cache=True if you want arping to modify internal ARP-Cache"""
    if verbose is None:
        verbose = conf.verb
    ans,unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=net), verbose=verbose,
                    filter="arp and arp[7] = 2", timeout=timeout, iface_hint=net, **kargs)
    ans = ARPingResult(ans.res)

    if cache and ans is not None:
        for pair in ans:
            arp_cache[pair[1].psrc] = (pair[1].hwsrc, time.time())
    if verbose:
        ans.show()
    return ans,unans

@conf.commands.register
def is_promisc(ip, fake_bcast="ff:ff:00:00:00:00",**kargs):
    """Try to guess if target is in Promisc mode. The target is provided by its ip."""

    responses = srp1(Ether(dst=fake_bcast) / ARP(op="who-has", pdst=ip),type=ETH_P_ARP, iface_hint=ip, timeout=1, verbose=0,**kargs)

    return responses is not None

@conf.commands.register
def promiscping(net, timeout=2, fake_bcast="ff:ff:ff:ff:ff:fe", **kargs):
    """Send ARP who-has requests to determine which hosts are in promiscuous mode
    promiscping(net, iface=conf.iface)"""
    ans,unans = srp(Ether(dst=fake_bcast)/ARP(pdst=net),
                    filter="arp and arp[7] = 2", timeout=timeout, iface_hint=net, **kargs)
    ans = ARPingResult(ans.res, name="PROMISCPing")

    ans.display()
    return ans,unans


class ARP_am(AnsweringMachine):
    function_name="farpd"
    filter = "arp"
    send_function = staticmethod(sendp)

    def parse_options(self, IP_addr=None, iface=None, ARP_addr=None):
        self.IP_addr=IP_addr
        self.iface=iface
        self.ARP_addr=ARP_addr

    def is_request(self, req):
        return (req.haslayer(ARP) and
                req.getlayer(ARP).op == 1 and
                (self.IP_addr == None or self.IP_addr == req.getlayer(ARP).pdst))
    
    def make_reply(self, req):
        ether = req.getlayer(Ether)
        arp = req.getlayer(ARP)
        iff,a,gw = conf.route.route(arp.psrc)
        if self.iface != None:
            iff = iface
        ARP_addr = self.ARP_addr
        IP_addr = arp.pdst
        resp = Ether(dst=ether.src,
                     src=ARP_addr)/ARP(op="is-at",
                                       hwsrc=ARP_addr,
                                       psrc=IP_addr,
                                       hwdst=arp.hwsrc,
                                       pdst=arp.pdst)
        return resp

    def sniff(self):
        sniff(iface=self.iface, **self.optsniff)

@conf.commands.register
def etherleak(target, **kargs):
    """Exploit Etherleak flaw"""
    return srpflood(Ether()/ARP(pdst=target), prn=lambda (s,r): Padding in r and hexstr(r[Padding].load),
                    filter="arp", **kargs)



########NEW FILE########
__FILENAME__ = l2tp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
L2TP (Layer 2 Tunneling Protocol) for VPNs.

[RFC 2661]
"""

import struct

from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import UDP
from scapy.layers.ppp import PPP

class L2TP(Packet):
    fields_desc = [ ShortEnumField("pkt_type",2,{2:"data"}),
                    ShortField("len", None),
                    ShortField("tunnel_id", 0),
                    ShortField("session_id", 0),
                    ShortField("ns", 0),
                    ShortField("nr", 0),
                    ShortField("offset", 0) ]

    def post_build(self, pkt, pay):
        if self.len is None:
            l = len(pkt)+len(pay)
            pkt = pkt[:2]+struct.pack("!H", l)+pkt[4:]
        return pkt+pay


bind_layers( UDP,           L2TP,          sport=1701, dport=1701)
bind_layers( L2TP,          PPP,           )

########NEW FILE########
__FILENAME__ = llmnr
from scapy.fields import *
from scapy.packet import *
from scapy.layers.inet import UDP
from scapy.layers.dns import DNSQRField, DNSRRField, DNSRRCountField

"""
LLMNR (Link Local Multicast Node Resolution).

[RFC 4795]
"""

#############################################################################
###                           LLMNR (RFC4795)                             ###
#############################################################################
# LLMNR is based on the DNS packet format (RFC1035 Section 4)
# RFC also envisions LLMNR over TCP. Like vista, we don't support it -- arno

_LLMNR_IPv6_mcast_Addr = "FF02:0:0:0:0:0:1:3"
_LLMNR_IPv4_mcast_addr = "224.0.0.252"

class LLMNRQuery(Packet):
    name = "Link Local Multicast Node Resolution - Query"
    fields_desc = [ ShortField("id", 0),
                    BitField("qr", 0, 1),
                    BitEnumField("opcode", 0, 4, { 0:"QUERY" }),
                    BitField("c", 0, 1),
                    BitField("tc", 0, 2),
                    BitField("z", 0, 4),
                    BitEnumField("rcode", 0, 4, { 0:"ok" }),
                    DNSRRCountField("qdcount", None, "qd"),
                    DNSRRCountField("ancount", None, "an"),
                    DNSRRCountField("nscount", None, "ns"),
                    DNSRRCountField("arcount", None, "ar"),
                    DNSQRField("qd", "qdcount"),
                    DNSRRField("an", "ancount"),
                    DNSRRField("ns", "nscount"),
                    DNSRRField("ar", "arcount",0)]
    overload_fields = {UDP: {"sport": 5355, "dport": 5355 }}
    def hashret(self):
        return struct.pack("!H", self.id)

class LLMNRResponse(LLMNRQuery):
    name = "Link Local Multicast Node Resolution - Response"
    qr = 1
    fields_desc = []

    def answers(self, other):
        return (isinstance(other, LLMNRQuery) and
                self.id == other.id and
                self.qr == 1 and
                other.qr == 0)

def _llmnr_dispatcher(x, *args, **kargs):
    cls = Raw
    if len(x) >= 3:
        if (ord(x[4]) & 0x80): # Response
            cls = LLMNRResponse
        else:                  # Query
            cls = LLMNRQuery
    return cls(x, *args, **kargs)

bind_bottom_up(UDP, _llmnr_dispatcher, { "dport": 5355 })
bind_bottom_up(UDP, _llmnr_dispatcher, { "sport": 5355 })

# LLMNRQuery(id=RandShort(), qd=DNSQR(qname="vista.")))



########NEW FILE########
__FILENAME__ = mgcp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
MGCP (Media Gateway Control Protocol)

[RFC 2805]
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import UDP

class MGCP(Packet):
    name = "MGCP"
    longname = "Media Gateway Control Protocol"
    fields_desc = [ StrStopField("verb","AUEP"," ", -1),
                    StrFixedLenField("sep1"," ",1),
                    StrStopField("transaction_id","1234567"," ", -1),
                    StrFixedLenField("sep2"," ",1),
                    StrStopField("endpoint","dummy@dummy.net"," ", -1),
                    StrFixedLenField("sep3"," ",1),
                    StrStopField("version","MGCP 1.0 NCS 1.0","\x0a", -1),
                    StrFixedLenField("sep4","\x0a",1),
                    ]
                    
    
#class MGCP(Packet):
#    name = "MGCP"
#    longname = "Media Gateway Control Protocol"
#    fields_desc = [ ByteEnumField("type",0, ["request","response","others"]),
#                    ByteField("code0",0),
#                    ByteField("code1",0),
#                    ByteField("code2",0),
#                    ByteField("code3",0),
#                    ByteField("code4",0),
#                    IntField("trasid",0),
#                    IntField("req_time",0),
#                    ByteField("is_duplicate",0),
#                    ByteField("req_available",0) ]
#
bind_layers( UDP,           MGCP,          dport=2727)
bind_layers( UDP,           MGCP,          sport=2727)

########NEW FILE########
__FILENAME__ = mobileip
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Mobile IP.
"""

from scapy.fields import *
from scapy.packet import *
from scapy.layers.inet import IP,UDP


class MobileIP(Packet):
    name = "Mobile IP (RFC3344)"
    fields_desc = [ ByteEnumField("type", 1, {1:"RRQ", 3:"RRP"}) ]

class MobileIPRRQ(Packet):
    name = "Mobile IP Registration Request (RFC3344)"
    fields_desc = [ XByteField("flags", 0),
                    ShortField("lifetime", 180),
                    IPField("homeaddr", "0.0.0.0"),
                    IPField("haaddr", "0.0.0.0"),
                    IPField("coaddr", "0.0.0.0"),
                    LongField("id", 0), ]

class MobileIPRRP(Packet):
    name = "Mobile IP Registration Reply (RFC3344)"
    fields_desc = [ ByteField("code", 0),
                    ShortField("lifetime", 180),
                    IPField("homeaddr", "0.0.0.0"),
                    IPField("haaddr", "0.0.0.0"),
                    LongField("id", 0), ]

class MobileIPTunnelData(Packet):
    name = "Mobile IP Tunnel Data Message (RFC3519)"
    fields_desc = [ ByteField("nexthdr", 4),
                    ShortField("res", 0) ]


bind_layers( UDP,           MobileIP,           sport=434)
bind_layers( UDP,           MobileIP,           dport=434)
bind_layers( MobileIP,      MobileIPRRQ,        type=1)
bind_layers( MobileIP,      MobileIPRRP,        type=3)
bind_layers( MobileIP,      MobileIPTunnelData, type=4)
bind_layers( MobileIPTunnelData, IP,           nexthdr=4)

########NEW FILE########
__FILENAME__ = netbios
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
NetBIOS over TCP/IP

[RFC 1001/1002]
"""

import struct
from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import UDP,TCP
from scapy.layers.l2 import SourceMACField

class NetBIOS_DS(Packet):
    name = "NetBIOS datagram service"
    fields_desc = [
        ByteEnumField("type",17, {17:"direct_group"}),
        ByteField("flags",0),
        XShortField("id",0),
        IPField("src","127.0.0.1"),
        ShortField("sport",138),
        ShortField("len",None),
        ShortField("ofs",0),
        NetBIOSNameField("srcname",""),
        NetBIOSNameField("dstname",""),
        ]
    def post_build(self, p, pay):
        p += pay
        if self.len is None:
            l = len(p)-14
            p = p[:10]+struct.pack("!H", l)+p[12:]
        return p
        
#        ShortField("length",0),
#        ShortField("Delimitor",0),
#        ByteField("command",0),
#        ByteField("data1",0),
#        ShortField("data2",0),
#        ShortField("XMIt",0),
#        ShortField("RSPCor",0),
#        StrFixedLenField("dest","",16),
#        StrFixedLenField("source","",16),
#        
#        ]
#

#NetBIOS


# Name Query Request
# Node Status Request
class NBNSQueryRequest(Packet):
    name="NBNS query request"
    fields_desc = [ShortField("NAME_TRN_ID",0),
                   ShortField("FLAGS", 0x0110),
                   ShortField("QDCOUNT",1),
                   ShortField("ANCOUNT",0),
                   ShortField("NSCOUNT",0),
                   ShortField("ARCOUNT",0),
                   NetBIOSNameField("QUESTION_NAME","windows"),
                   ShortEnumField("SUFFIX",0x4141,{0x4141:"workstation",0x4141+0x03:"messenger service",0x4141+0x200:"file server service",0x4141+0x10b:"domain master browser",0x4141+0x10c:"domain controller", 0x4141+0x10e:"browser election service"}),
                   ByteField("NULL",0),
                   ShortEnumField("QUESTION_TYPE",0x20, {0x20:"NB",0x21:"NBSTAT"}),
                   ShortEnumField("QUESTION_CLASS",1,{1:"INTERNET"})]

# Name Registration Request
# Name Refresh Request
# Name Release Request or Demand
class NBNSRequest(Packet):
    name="NBNS request"
    fields_desc = [ShortField("NAME_TRN_ID",0),
                   ShortField("FLAGS", 0x2910),
                   ShortField("QDCOUNT",1),
                   ShortField("ANCOUNT",0),
                   ShortField("NSCOUNT",0),
                   ShortField("ARCOUNT",1),
                   NetBIOSNameField("QUESTION_NAME","windows"),
                   ShortEnumField("SUFFIX",0x4141,{0x4141:"workstation",0x4141+0x03:"messenger service",0x4141+0x200:"file server service",0x4141+0x10b:"domain master browser",0x4141+0x10c:"domain controller", 0x4141+0x10e:"browser election service"}),
                   ByteField("NULL",0),
                   ShortEnumField("QUESTION_TYPE",0x20, {0x20:"NB",0x21:"NBSTAT"}),
                   ShortEnumField("QUESTION_CLASS",1,{1:"INTERNET"}),
                   ShortEnumField("RR_NAME",0xC00C,{0xC00C:"Label String Pointer to QUESTION_NAME"}),
                   ShortEnumField("RR_TYPE",0x20, {0x20:"NB",0x21:"NBSTAT"}),
                   ShortEnumField("RR_CLASS",1,{1:"INTERNET"}),
                   IntField("TTL", 0),
                   ShortField("RDLENGTH", 6),
                   BitEnumField("G",0,1,{0:"Unique name",1:"Group name"}),
                   BitEnumField("OWNER_NODE_TYPE",00,2,{00:"B node",01:"P node",02:"M node",03:"H node"}),
                   BitEnumField("UNUSED",0,13,{0:"Unused"}),
                   IPField("NB_ADDRESS", "127.0.0.1")]

# Name Query Response
# Name Registration Response
class NBNSQueryResponse(Packet):
    name="NBNS query response"
    fields_desc = [ShortField("NAME_TRN_ID",0),
                   ShortField("FLAGS", 0x8500),
                   ShortField("QDCOUNT",0),
                   ShortField("ANCOUNT",1),
                   ShortField("NSCOUNT",0),
                   ShortField("ARCOUNT",0),
                   NetBIOSNameField("RR_NAME","windows"),
                   ShortEnumField("SUFFIX",0x4141,{0x4141:"workstation",0x4141+0x03:"messenger service",0x4141+0x200:"file server service",0x4141+0x10b:"domain master browser",0x4141+0x10c:"domain controller", 0x4141+0x10e:"browser election service"}),
                   ByteField("NULL",0),
                   ShortEnumField("QUESTION_TYPE",0x20, {0x20:"NB",0x21:"NBSTAT"}),
                   ShortEnumField("QUESTION_CLASS",1,{1:"INTERNET"}),
                   IntField("TTL", 0x493e0),
                   ShortField("RDLENGTH", 6),
                   ShortField("NB_FLAGS", 0),
                   IPField("NB_ADDRESS", "127.0.0.1")]

# Name Query Response (negative)
# Name Release Response
class NBNSQueryResponseNegative(Packet):
    name="NBNS query response (negative)"
    fields_desc = [ShortField("NAME_TRN_ID",0), 
                   ShortField("FLAGS", 0x8506),
                   ShortField("QDCOUNT",0),
                   ShortField("ANCOUNT",1),
                   ShortField("NSCOUNT",0),
                   ShortField("ARCOUNT",0),
                   NetBIOSNameField("RR_NAME","windows"),
                   ShortEnumField("SUFFIX",0x4141,{0x4141:"workstation",0x4141+0x03:"messenger service",0x4141+0x200:"file server service",0x4141+0x10b:"domain master browser",0x4141+0x10c:"domain controller", 0x4141+0x10e:"browser election service"}),
                   ByteField("NULL",0),
                   ShortEnumField("RR_TYPE",0x20, {0x20:"NB",0x21:"NBSTAT"}),
                   ShortEnumField("RR_CLASS",1,{1:"INTERNET"}),
                   IntField("TTL",0),
                   ShortField("RDLENGTH",6),
                   BitEnumField("G",0,1,{0:"Unique name",1:"Group name"}),
                   BitEnumField("OWNER_NODE_TYPE",00,2,{00:"B node",01:"P node",02:"M node",03:"H node"}),
                   BitEnumField("UNUSED",0,13,{0:"Unused"}),
                   IPField("NB_ADDRESS", "127.0.0.1")]
    
# Node Status Response
class NBNSNodeStatusResponse(Packet):
    name="NBNS Node Status Response"
    fields_desc = [ShortField("NAME_TRN_ID",0), 
                   ShortField("FLAGS", 0x8500),
                   ShortField("QDCOUNT",0),
                   ShortField("ANCOUNT",1),
                   ShortField("NSCOUNT",0),
                   ShortField("ARCOUNT",0),
                   NetBIOSNameField("RR_NAME","windows"),
                   ShortEnumField("SUFFIX",0x4141,{0x4141:"workstation",0x4141+0x03:"messenger service",0x4141+0x200:"file server service",0x4141+0x10b:"domain master browser",0x4141+0x10c:"domain controller", 0x4141+0x10e:"browser election service"}),
                   ByteField("NULL",0),
                   ShortEnumField("RR_TYPE",0x21, {0x20:"NB",0x21:"NBSTAT"}),
                   ShortEnumField("RR_CLASS",1,{1:"INTERNET"}),
                   IntField("TTL",0),
                   ShortField("RDLENGTH",83),
                   ByteField("NUM_NAMES",1)]

# Service for Node Status Response
class NBNSNodeStatusResponseService(Packet):
    name="NBNS Node Status Response Service"
    fields_desc = [StrFixedLenField("NETBIOS_NAME","WINDOWS         ",15),
                   ByteEnumField("SUFFIX",0,{0:"workstation",0x03:"messenger service",0x20:"file server service",0x1b:"domain master browser",0x1c:"domain controller", 0x1e:"browser election service"}),
                   ByteField("NAME_FLAGS",0x4),
                   ByteEnumField("UNUSED",0,{0:"unused"})]

# End of Node Status Response packet
class NBNSNodeStatusResponseEnd(Packet):
    name="NBNS Node Status Response"
    fields_desc = [SourceMACField("MAC_ADDRESS"),
                   BitField("STATISTICS",0,57*8)]

# Wait for Acknowledgement Response
class NBNSWackResponse(Packet):
    name="NBNS Wait for Acknowledgement Response"
    fields_desc = [ShortField("NAME_TRN_ID",0),
                   ShortField("FLAGS", 0xBC07),
                   ShortField("QDCOUNT",0),
                   ShortField("ANCOUNT",1),
                   ShortField("NSCOUNT",0),
                   ShortField("ARCOUNT",0),
                   NetBIOSNameField("RR_NAME","windows"),
                   ShortEnumField("SUFFIX",0x4141,{0x4141:"workstation",0x4141+0x03:"messenger service",0x4141+0x200:"file server service",0x4141+0x10b:"domain master browser",0x4141+0x10c:"domain controller", 0x4141+0x10e:"browser election service"}),
                   ByteField("NULL",0),
                   ShortEnumField("RR_TYPE",0x20, {0x20:"NB",0x21:"NBSTAT"}),
                   ShortEnumField("RR_CLASS",1,{1:"INTERNET"}),
                   IntField("TTL", 2),
                   ShortField("RDLENGTH",2),
                   BitField("RDATA",10512,16)] #10512=0010100100010000

class NBTDatagram(Packet):
    name="NBT Datagram Packet"
    fields_desc= [ByteField("Type", 0x10),
                  ByteField("Flags", 0x02),
                  ShortField("ID", 0),
                  IPField("SourceIP", "127.0.0.1"),
                  ShortField("SourcePort", 138),
                  ShortField("Length", 272),
                  ShortField("Offset", 0),
                  NetBIOSNameField("SourceName","windows"),
                  ShortEnumField("SUFFIX1",0x4141,{0x4141:"workstation",0x4141+0x03:"messenger service",0x4141+0x200:"file server service",0x4141+0x10b:"domain master browser",0x4141+0x10c:"domain controller", 0x4141+0x10e:"browser election service"}),
                  ByteField("NULL",0),
                  NetBIOSNameField("DestinationName","windows"),
                  ShortEnumField("SUFFIX2",0x4141,{0x4141:"workstation",0x4141+0x03:"messenger service",0x4141+0x200:"file server service",0x4141+0x10b:"domain master browser",0x4141+0x10c:"domain controller", 0x4141+0x10e:"browser election service"}),
                  ByteField("NULL",0)]
    

class NBTSession(Packet):
    name="NBT Session Packet"
    fields_desc= [ByteEnumField("TYPE",0,{0x00:"Session Message",0x81:"Session Request",0x82:"Positive Session Response",0x83:"Negative Session Response",0x84:"Retarget Session Response",0x85:"Session Keepalive"}),
                  BitField("RESERVED",0x00,7),
                  BitField("LENGTH",0,17)]

bind_layers( UDP,           NBNSQueryRequest,  dport=137)
bind_layers( UDP,           NBNSRequest,       dport=137)
bind_layers( UDP,           NBNSQueryResponse, sport=137)
bind_layers( UDP,           NBNSQueryResponseNegative, sport=137)
bind_layers( UDP,           NBNSNodeStatusResponse,    sport=137)
bind_layers( NBNSNodeStatusResponse,        NBNSNodeStatusResponseService, )
bind_layers( NBNSNodeStatusResponse,        NBNSNodeStatusResponseService, )
bind_layers( NBNSNodeStatusResponseService, NBNSNodeStatusResponseService, )
bind_layers( NBNSNodeStatusResponseService, NBNSNodeStatusResponseEnd, )
bind_layers( UDP,           NBNSWackResponse, sport=137)
bind_layers( UDP,           NBTDatagram,      dport=138)
bind_layers( TCP,           NBTSession,       dport=139)

########NEW FILE########
__FILENAME__ = netflow
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Cisco NetFlow protocol v1
"""


from scapy.fields import *
from scapy.packet import *

# Cisco Netflow Protocol version 1
class NetflowHeader(Packet):
    name = "Netflow Header"
    fields_desc = [ ShortField("version", 1) ]
    
class NetflowHeaderV1(Packet):
    name = "Netflow Header V1"
    fields_desc = [ ShortField("count", 0),
                    IntField("sysUptime", 0),
                    IntField("unixSecs", 0),
                    IntField("unixNanoSeconds", 0) ]


class NetflowRecordV1(Packet):
    name = "Netflow Record"
    fields_desc = [ IPField("ipsrc", "0.0.0.0"),
                    IPField("ipdst", "0.0.0.0"),
                    IPField("nexthop", "0.0.0.0"),
                    ShortField("inputIfIndex", 0),
                    ShortField("outpuIfIndex", 0),
                    IntField("dpkts", 0),
                    IntField("dbytes", 0),
                    IntField("starttime", 0),
                    IntField("endtime", 0),
                    ShortField("srcport", 0),
                    ShortField("dstport", 0),
                    ShortField("padding", 0),
                    ByteField("proto", 0),
                    ByteField("tos", 0),
                    IntField("padding1", 0),
                    IntField("padding2", 0) ]


bind_layers( NetflowHeader,   NetflowHeaderV1, version=1)
bind_layers( NetflowHeaderV1, NetflowRecordV1, )

########NEW FILE########
__FILENAME__ = ntp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
NTP (Network Time Protocol).
"""

import time
from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import UDP


# seconds between 01-01-1900 and 01-01-1970
_NTP_BASETIME = 2208988800

class TimeStampField(FixedPointField):
    def __init__(self, name, default):
        FixedPointField.__init__(self, name, default, 64, 32)

    def i2repr(self, pkt, val):
        if val is None:
            return "--"
        val = self.i2h(pkt,val)
        if val < _NTP_BASETIME:
            return val
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(val-_NTP_BASETIME))

    def any2i(self, pkt, val):
        if type(val) is str:
            return int(time.mktime(time.strptime(val))) + _NTP_BASETIME + 3600 # XXX
        return FixedPointField.any2i(self,pkt,val)
    
    def i2m(self, pkt, val):
        if val is None:
            val = FixedPointField.any2i(self, pkt, time.time()+_NTP_BASETIME)
        return FixedPointField.i2m(self, pkt, val)
        


class NTP(Packet):
    # RFC 1769
    name = "NTP"
    fields_desc = [ 
         BitEnumField('leap', 0, 2,
                      { 0: 'nowarning',
                        1: 'longminute',
                        2: 'shortminute',
                        3: 'notsync'}),
         BitField('version', 3, 3),
         BitEnumField('mode', 3, 3,
                      { 0: 'reserved',
                        1: 'sym_active',
                        2: 'sym_passive',
                        3: 'client',
                        4: 'server',
                        5: 'broadcast',
                        6: 'control',
                        7: 'private'}),
         BitField('stratum', 2, 8),
         BitField('poll', 0xa, 8),          ### XXX : it's a signed int
         BitField('precision', 0, 8),       ### XXX : it's a signed int
         FixedPointField('delay', 0, size=32, frac_bits=16),
         FixedPointField('dispersion', 0, size=32, frac_bits=16),
         IPField('id', "127.0.0.1"),
         TimeStampField('ref', 0),
         TimeStampField('orig', None),  # None means current time
         TimeStampField('recv', 0),
         TimeStampField('sent', None) 
         ]
    def mysummary(self):
        return self.sprintf("NTP v%ir,NTP.version%, %NTP.mode%")


bind_layers( UDP,           NTP,           dport=123, sport=123)

########NEW FILE########
__FILENAME__ = pflog
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
PFLog: OpenBSD PF packet filter logging.
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import IP
if conf.ipv6_enabled:
    from scapy.layers.inet6 import IPv6
from scapy.config import conf

class PFLog(Packet):
    name = "PFLog"
    # from OpenBSD src/sys/net/pfvar.h and src/sys/net/if_pflog.h
    fields_desc = [ ByteField("hdrlen", 0),
                    ByteEnumField("addrfamily", 2, {socket.AF_INET: "IPv4",
                                                    socket.AF_INET6: "IPv6"}),
                    ByteEnumField("action", 1, {0: "pass", 1: "drop",
                                                2: "scrub", 3: "no-scrub",
                                                4: "nat", 5: "no-nat",
                                                6: "binat", 7: "no-binat",
                                                8: "rdr", 9: "no-rdr",
                                                10: "syn-proxy-drop" }),
                    ByteEnumField("reason", 0, {0: "match", 1: "bad-offset",
                                                2: "fragment", 3: "short",
                                                4: "normalize", 5: "memory",
                                                6: "bad-timestamp",
                                                7: "congestion",
                                                8: "ip-options",
                                                9: "proto-cksum",
                                                10: "state-mismatch",
                                                11: "state-insert",
                                                12: "state-limit",
                                                13: "src-limit",
                                                14: "syn-proxy" }),
                    StrFixedLenField("iface", "", 16),
                    StrFixedLenField("ruleset", "", 16),
                    SignedIntField("rulenumber", 0),
                    SignedIntField("subrulenumber", 0),
                    SignedIntField("uid", 0),
                    IntField("pid", 0),
                    SignedIntField("ruleuid", 0),
                    IntField("rulepid", 0),
                    ByteEnumField("direction", 255, {0: "inout", 1: "in",
                                                     2:"out", 255: "unknown"}),
                    StrFixedLenField("pad", "\x00\x00\x00", 3 ) ]
    def mysummary(self):
        return self.sprintf("%PFLog.addrfamily% %PFLog.action% on %PFLog.iface% by rule %PFLog.rulenumber%")

bind_layers(PFLog, IP, addrfamily=socket.AF_INET)
if conf.ipv6_enabled:
    bind_layers(PFLog, IPv6, addrfamily=socket.AF_INET6)

conf.l2types.register(117, PFLog)

########NEW FILE########
__FILENAME__ = ppp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
PPP (Point to Point Protocol)

[RFC 1661]
"""

import struct
from scapy.packet import *
from scapy.layers.l2 import *
from scapy.layers.inet import *
from scapy.fields import *

class PPPoE(Packet):
    name = "PPP over Ethernet"
    fields_desc = [ BitField("version", 1, 4),
                    BitField("type", 1, 4),
                    ByteEnumField("code", 0, {0:"Session"}),
                    XShortField("sessionid", 0x0),
                    ShortField("len", None) ]

    def post_build(self, p, pay):
        p += pay
        if self.len is None:
            l = len(p)-6
            p = p[:4]+struct.pack("!H", l)+p[6:]
        return p

class PPPoED(PPPoE):
    name = "PPP over Ethernet Discovery"
    fields_desc = [ BitField("version", 1, 4),
                    BitField("type", 1, 4),
                    ByteEnumField("code", 0x09, {0x09:"PADI",0x07:"PADO",0x19:"PADR",0x65:"PADS",0xa7:"PADT"}),
                    XShortField("sessionid", 0x0),
                    ShortField("len", None) ]


_PPP_proto = { 0x0001: "Padding Protocol",
               0x0003: "ROHC small-CID [RFC3095]",
               0x0005: "ROHC large-CID [RFC3095]",
               0x0021: "Internet Protocol version 4",
               0x0023: "OSI Network Layer",
               0x0025: "Xerox NS IDP",
               0x0027: "DECnet Phase IV",
               0x0029: "Appletalk",
               0x002b: "Novell IPX",
               0x002d: "Van Jacobson Compressed TCP/IP",
               0x002f: "Van Jacobson Uncompressed TCP/IP",
               0x0031: "Bridging PDU",
               0x0033: "Stream Protocol (ST-II)",
               0x0035: "Banyan Vines",
               0x0037: "reserved (until 1993) [Typo in RFC1172]",
               0x0039: "AppleTalk EDDP",
               0x003b: "AppleTalk SmartBuffered",
               0x003d: "Multi-Link [RFC1717]",
               0x003f: "NETBIOS Framing",
               0x0041: "Cisco Systems",
               0x0043: "Ascom Timeplex",
               0x0045: "Fujitsu Link Backup and Load Balancing (LBLB)",
               0x0047: "DCA Remote Lan",
               0x0049: "Serial Data Transport Protocol (PPP-SDTP)",
               0x004b: "SNA over 802.2",
               0x004d: "SNA",
               0x004f: "IPv6 Header Compression",
               0x0051: "KNX Bridging Data [ianp]",
               0x0053: "Encryption [Meyer]",
               0x0055: "Individual Link Encryption [Meyer]",
               0x0057: "Internet Protocol version 6 [Hinden]",
               0x0059: "PPP Muxing [RFC3153]",
               0x005b: "Vendor-Specific Network Protocol (VSNP) [RFC3772]",
               0x0061: "RTP IPHC Full Header [RFC3544]",
               0x0063: "RTP IPHC Compressed TCP [RFC3544]",
               0x0065: "RTP IPHC Compressed Non TCP [RFC3544]",
               0x0067: "RTP IPHC Compressed UDP 8 [RFC3544]",
               0x0069: "RTP IPHC Compressed RTP 8 [RFC3544]",
               0x006f: "Stampede Bridging",
               0x0071: "Reserved [Fox]",
               0x0073: "MP+ Protocol [Smith]",
               0x007d: "reserved (Control Escape) [RFC1661]",
               0x007f: "reserved (compression inefficient [RFC1662]",
               0x0081: "Reserved Until 20-Oct-2000 [IANA]",
               0x0083: "Reserved Until 20-Oct-2000 [IANA]",
               0x00c1: "NTCITS IPI [Ungar]",
               0x00cf: "reserved (PPP NLID)",
               0x00fb: "single link compression in multilink [RFC1962]",
               0x00fd: "compressed datagram [RFC1962]",
               0x00ff: "reserved (compression inefficient)",
               0x0201: "802.1d Hello Packets",
               0x0203: "IBM Source Routing BPDU",
               0x0205: "DEC LANBridge100 Spanning Tree",
               0x0207: "Cisco Discovery Protocol [Sastry]",
               0x0209: "Netcs Twin Routing [Korfmacher]",
               0x020b: "STP - Scheduled Transfer Protocol [Segal]",
               0x020d: "EDP - Extreme Discovery Protocol [Grosser]",
               0x0211: "Optical Supervisory Channel Protocol (OSCP)[Prasad]",
               0x0213: "Optical Supervisory Channel Protocol (OSCP)[Prasad]",
               0x0231: "Luxcom",
               0x0233: "Sigma Network Systems",
               0x0235: "Apple Client Server Protocol [Ridenour]",
               0x0281: "MPLS Unicast [RFC3032]  ",
               0x0283: "MPLS Multicast [RFC3032]",
               0x0285: "IEEE p1284.4 standard - data packets [Batchelder]",
               0x0287: "ETSI TETRA Network Protocol Type 1 [Nieminen]",
               0x0289: "Multichannel Flow Treatment Protocol [McCann]",
               0x2063: "RTP IPHC Compressed TCP No Delta [RFC3544]",
               0x2065: "RTP IPHC Context State [RFC3544]",
               0x2067: "RTP IPHC Compressed UDP 16 [RFC3544]",
               0x2069: "RTP IPHC Compressed RTP 16 [RFC3544]",
               0x4001: "Cray Communications Control Protocol [Stage]",
               0x4003: "CDPD Mobile Network Registration Protocol [Quick]",
               0x4005: "Expand accelerator protocol [Rachmani]",
               0x4007: "ODSICP NCP [Arvind]",
               0x4009: "DOCSIS DLL [Gaedtke]",
               0x400B: "Cetacean Network Detection Protocol [Siller]",
               0x4021: "Stacker LZS [Simpson]",
               0x4023: "RefTek Protocol [Banfill]",
               0x4025: "Fibre Channel [Rajagopal]",
               0x4027: "EMIT Protocols [Eastham]",
               0x405b: "Vendor-Specific Protocol (VSP) [RFC3772]",
               0x8021: "Internet Protocol Control Protocol",
               0x8023: "OSI Network Layer Control Protocol",
               0x8025: "Xerox NS IDP Control Protocol",
               0x8027: "DECnet Phase IV Control Protocol",
               0x8029: "Appletalk Control Protocol",
               0x802b: "Novell IPX Control Protocol",
               0x802d: "reserved",
               0x802f: "reserved",
               0x8031: "Bridging NCP",
               0x8033: "Stream Protocol Control Protocol",
               0x8035: "Banyan Vines Control Protocol",
               0x8037: "reserved (until 1993)",
               0x8039: "reserved",
               0x803b: "reserved",
               0x803d: "Multi-Link Control Protocol",
               0x803f: "NETBIOS Framing Control Protocol",
               0x8041: "Cisco Systems Control Protocol",
               0x8043: "Ascom Timeplex",
               0x8045: "Fujitsu LBLB Control Protocol",
               0x8047: "DCA Remote Lan Network Control Protocol (RLNCP)",
               0x8049: "Serial Data Control Protocol (PPP-SDCP)",
               0x804b: "SNA over 802.2 Control Protocol",
               0x804d: "SNA Control Protocol",
               0x804f: "IP6 Header Compression Control Protocol",
               0x8051: "KNX Bridging Control Protocol [ianp]",
               0x8053: "Encryption Control Protocol [Meyer]",
               0x8055: "Individual Link Encryption Control Protocol [Meyer]",
               0x8057: "IPv6 Control Protovol [Hinden]",
               0x8059: "PPP Muxing Control Protocol [RFC3153]",
               0x805b: "Vendor-Specific Network Control Protocol (VSNCP) [RFC3772]",
               0x806f: "Stampede Bridging Control Protocol",
               0x8073: "MP+ Control Protocol [Smith]",
               0x8071: "Reserved [Fox]",
               0x807d: "Not Used - reserved [RFC1661]",
               0x8081: "Reserved Until 20-Oct-2000 [IANA]",
               0x8083: "Reserved Until 20-Oct-2000 [IANA]",
               0x80c1: "NTCITS IPI Control Protocol [Ungar]",
               0x80cf: "Not Used - reserved [RFC1661]",
               0x80fb: "single link compression in multilink control [RFC1962]",
               0x80fd: "Compression Control Protocol [RFC1962]",
               0x80ff: "Not Used - reserved [RFC1661]",
               0x8207: "Cisco Discovery Protocol Control [Sastry]",
               0x8209: "Netcs Twin Routing [Korfmacher]",
               0x820b: "STP - Control Protocol [Segal]",
               0x820d: "EDPCP - Extreme Discovery Protocol Ctrl Prtcl [Grosser]",
               0x8235: "Apple Client Server Protocol Control [Ridenour]",
               0x8281: "MPLSCP [RFC3032]",
               0x8285: "IEEE p1284.4 standard - Protocol Control [Batchelder]",
               0x8287: "ETSI TETRA TNP1 Control Protocol [Nieminen]",
               0x8289: "Multichannel Flow Treatment Protocol [McCann]",
               0xc021: "Link Control Protocol",
               0xc023: "Password Authentication Protocol",
               0xc025: "Link Quality Report",
               0xc027: "Shiva Password Authentication Protocol",
               0xc029: "CallBack Control Protocol (CBCP)",
               0xc02b: "BACP Bandwidth Allocation Control Protocol [RFC2125]",
               0xc02d: "BAP [RFC2125]",
               0xc05b: "Vendor-Specific Authentication Protocol (VSAP) [RFC3772]",
               0xc081: "Container Control Protocol [KEN]",
               0xc223: "Challenge Handshake Authentication Protocol",
               0xc225: "RSA Authentication Protocol [Narayana]",
               0xc227: "Extensible Authentication Protocol [RFC2284]",
               0xc229: "Mitsubishi Security Info Exch Ptcl (SIEP) [Seno]",
               0xc26f: "Stampede Bridging Authorization Protocol",
               0xc281: "Proprietary Authentication Protocol [KEN]",
               0xc283: "Proprietary Authentication Protocol [Tackabury]",
               0xc481: "Proprietary Node ID Authentication Protocol [KEN]"}


class HDLC(Packet):
    fields_desc = [ XByteField("address",0xff),
                    XByteField("control",0x03)  ]

class PPP(Packet):
    name = "PPP Link Layer"
    fields_desc = [ ShortEnumField("proto", 0x0021, _PPP_proto) ]
    @classmethod
    def dispatch_hook(cls, _pkt=None, *args, **kargs):
        if _pkt and _pkt[0] == '\xff':
            cls = HDLC
        return cls

_PPP_conftypes = { 1:"Configure-Request",
                   2:"Configure-Ack",
                   3:"Configure-Nak",
                   4:"Configure-Reject",
                   5:"Terminate-Request",
                   6:"Terminate-Ack",
                   7:"Code-Reject",
                   8:"Protocol-Reject",
                   9:"Echo-Request",
                   10:"Echo-Reply",
                   11:"Discard-Request",
                   14:"Reset-Request",
                   15:"Reset-Ack",
                   }


### PPP IPCP stuff (RFC 1332)

# All IPCP options are defined below (names and associated classes) 
_PPP_ipcpopttypes = {     1:"IP-Addresses (Deprecated)",
                          2:"IP-Compression-Protocol",
                          3:"IP-Address",
                          4:"Mobile-IPv4", # not implemented, present for completeness
                          129:"Primary-DNS-Address",
                          130:"Primary-NBNS-Address",
                          131:"Secondary-DNS-Address",
                          132:"Secondary-NBNS-Address"}


class PPP_IPCP_Option(Packet):
    name = "PPP IPCP Option"
    fields_desc = [ ByteEnumField("type" , None , _PPP_ipcpopttypes),
                    FieldLenField("len", None, length_of="data", fmt="B", adjust=lambda p,x:x+2),
                    StrLenField("data", "", length_from=lambda p:max(0,p.len-2)) ]
    def extract_padding(self, pay):
        return "",pay

    registered_options = {}
    @classmethod
    def register_variant(cls):
        cls.registered_options[cls.type.default] = cls
    @classmethod
    def dispatch_hook(cls, _pkt=None, *args, **kargs):
        if _pkt:
            o = ord(_pkt[0])
            return cls.registered_options.get(o, cls)
        return cls


class PPP_IPCP_Option_IPAddress(PPP_IPCP_Option):
    name = "PPP IPCP Option: IP Address"
    fields_desc = [ ByteEnumField("type" , 3 , _PPP_ipcpopttypes),
                    FieldLenField("len", None, length_of="data", fmt="B", adjust=lambda p,x:x+2),
                    IPField("data","0.0.0.0"),
                    ConditionalField(StrLenField("garbage","", length_from=lambda pkt:pkt.len-6), lambda p:p.len!=6) ]

class PPP_IPCP_Option_DNS1(PPP_IPCP_Option):
    name = "PPP IPCP Option: DNS1 Address"
    fields_desc = [ ByteEnumField("type" , 129 , _PPP_ipcpopttypes),
                    FieldLenField("len", None, length_of="data", fmt="B", adjust=lambda p,x:x+2),
                    IPField("data","0.0.0.0"),
                    ConditionalField(StrLenField("garbage","", length_from=lambda pkt:pkt.len-6), lambda p:p.len!=6) ]

class PPP_IPCP_Option_DNS2(PPP_IPCP_Option):
    name = "PPP IPCP Option: DNS2 Address"
    fields_desc = [ ByteEnumField("type" , 131 , _PPP_ipcpopttypes),
                    FieldLenField("len", None, length_of="data", fmt="B", adjust=lambda p,x:x+2),
                    IPField("data","0.0.0.0"),
                    ConditionalField(StrLenField("garbage","", length_from=lambda pkt:pkt.len-6), lambda p:p.len!=6) ]

class PPP_IPCP_Option_NBNS1(PPP_IPCP_Option):
    name = "PPP IPCP Option: NBNS1 Address"
    fields_desc = [ ByteEnumField("type" , 130 , _PPP_ipcpopttypes),
                    FieldLenField("len", None, length_of="data", fmt="B", adjust=lambda p,x:x+2),
                    IPField("data","0.0.0.0"),
                    ConditionalField(StrLenField("garbage","", length_from=lambda pkt:pkt.len-6), lambda p:p.len!=6) ]

class PPP_IPCP_Option_NBNS2(PPP_IPCP_Option):
    name = "PPP IPCP Option: NBNS2 Address"
    fields_desc = [ ByteEnumField("type" , 132 , _PPP_ipcpopttypes),
                    FieldLenField("len", None, length_of="data", fmt="B", adjust=lambda p,x:x+2),
                    IPField("data","0.0.0.0"),
                    ConditionalField(StrLenField("garbage","", length_from=lambda pkt:pkt.len-6), lambda p:p.len!=6) ]


class PPP_IPCP(Packet):
    fields_desc = [ ByteEnumField("code" , 1, _PPP_conftypes),
		    XByteField("id", 0 ),
                    FieldLenField("len" , None, fmt="H", length_of="options", adjust=lambda p,x:x+4 ),
                    PacketListField("options", [],  PPP_IPCP_Option, length_from=lambda p:p.len-4,) ]


### ECP

_PPP_ecpopttypes = { 0:"OUI",
                     1:"DESE", }

class PPP_ECP_Option(Packet):
    name = "PPP ECP Option"
    fields_desc = [ ByteEnumField("type" , None , _PPP_ecpopttypes),
                    FieldLenField("len", None, length_of="data", fmt="B", adjust=lambda p,x:x+2),
                    StrLenField("data", "", length_from=lambda p:max(0,p.len-2)) ]
    def extract_padding(self, pay):
        return "",pay

    registered_options = {}
    @classmethod
    def register_variant(cls):
        cls.registered_options[cls.type.default] = cls
    @classmethod
    def dispatch_hook(cls, _pkt=None, *args, **kargs):
        if _pkt:
            o = ord(_pkt[0])
            return cls.registered_options.get(o, cls)
        return cls

class PPP_ECP_Option_OUI(PPP_ECP_Option):
    fields_desc = [ ByteEnumField("type" , 0 , _PPP_ecpopttypes),
                    FieldLenField("len", None, length_of="data", fmt="B", adjust=lambda p,x:x+6),
                    StrFixedLenField("oui","",3),
                    ByteField("subtype",0),
                    StrLenField("data", "", length_from=lambda p:p.len-6) ]
                    


class PPP_ECP(Packet):
    fields_desc = [ ByteEnumField("code" , 1, _PPP_conftypes),
		    XByteField("id", 0 ),
                    FieldLenField("len" , None, fmt="H", length_of="options", adjust=lambda p,x:x+4 ),
                    PacketListField("options", [],  PPP_ECP_Option, length_from=lambda p:p.len-4,) ]

bind_layers( Ether,         PPPoED,        type=0x8863)
bind_layers( Ether,         PPPoE,         type=0x8864)
bind_layers( CookedLinux,   PPPoED,        proto=0x8863)
bind_layers( CookedLinux,   PPPoE,         proto=0x8864)
bind_layers( PPPoE,         PPP,           code=0)
bind_layers( HDLC,          PPP,           )
bind_layers( PPP,           IP,            proto=33)
bind_layers( PPP,           PPP_IPCP,      proto=0x8021)
bind_layers( PPP,           PPP_ECP,       proto=0x8053)
bind_layers( Ether,         PPP_IPCP,      type=0x8021)
bind_layers( Ether,         PPP_ECP,       type=0x8053)

########NEW FILE########
__FILENAME__ = radius
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
RADIUS (Remote Authentication Dial In User Service)
"""

import struct
from scapy.packet import *
from scapy.fields import *

class Radius(Packet):
    name = "Radius"
    fields_desc = [ ByteEnumField("code", 1, {1: "Access-Request",
                                              2: "Access-Accept",
                                              3: "Access-Reject",
                                              4: "Accounting-Request",
                                              5: "Accounting-Accept",
                                              6: "Accounting-Status",
                                              7: "Password-Request",
                                              8: "Password-Ack",
                                              9: "Password-Reject",
                                              10: "Accounting-Message",
                                              11: "Access-Challenge",
                                              12: "Status-Server",
                                              13: "Status-Client",
                                              21: "Resource-Free-Request",
                                              22: "Resource-Free-Response",
                                              23: "Resource-Query-Request",
                                              24: "Resource-Query-Response",
                                              25: "Alternate-Resource-Reclaim-Request",
                                              26: "NAS-Reboot-Request",
                                              27: "NAS-Reboot-Response",
                                              29: "Next-Passcode",
                                              30: "New-Pin",
                                              31: "Terminate-Session",
                                              32: "Password-Expired",
                                              33: "Event-Request",
                                              34: "Event-Response",
                                              40: "Disconnect-Request",
                                              41: "Disconnect-ACK",
                                              42: "Disconnect-NAK",
                                              43: "CoA-Request",
                                              44: "CoA-ACK",
                                              45: "CoA-NAK",
                                              50: "IP-Address-Allocate",
                                              51: "IP-Address-Release",
                                              253: "Experimental-use",
                                              254: "Reserved",
                                              255: "Reserved"} ),
                    ByteField("id", 0),
                    ShortField("len", None),
                    StrFixedLenField("authenticator","",16) ]
    def post_build(self, p, pay):
        p += pay
        l = self.len
        if l is None:
            l = len(p)
            p = p[:2]+struct.pack("!H",l)+p[4:]
        return p




########NEW FILE########
__FILENAME__ = rip
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
RIP (Routing Information Protocol).
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import UDP

class RIP(Packet):
    name = "RIP header"
    fields_desc = [
        ByteEnumField("cmd",1,{1:"req",2:"resp",3:"traceOn",4:"traceOff",5:"sun",
                               6:"trigReq",7:"trigResp",8:"trigAck",9:"updateReq",
                               10:"updateResp",11:"updateAck"}),
        ByteField("version",1),
        ShortField("null",0),
        ]

class RIPEntry(Packet):
    name = "RIP entry"
    fields_desc = [
        ShortEnumField("AF",2,{2:"IP"}),
        ShortField("RouteTag",0),
        IPField("addr","0.0.0.0"),
        IPField("mask","0.0.0.0"),
        IPField("nextHop","0.0.0.0"),
        IntEnumField("metric",1,{16:"Unreach"}),
        ]
        


bind_layers( UDP,           RIP,           sport=520)
bind_layers( UDP,           RIP,           dport=520)
bind_layers( RIP,           RIPEntry,      )
bind_layers( RIPEntry,      RIPEntry,      )

########NEW FILE########
__FILENAME__ = rtp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
RTP (Real-time Transport Protocol).
"""

from scapy.packet import *
from scapy.fields import *

_rtp_payload_types = {
    # http://www.iana.org/assignments/rtp-parameters
    0:  'G.711 PCMU',    3:  'GSM',
    4:  'G723',          5:  'DVI4',
    6:  'DVI4',          7:  'LPC',
    8:  'PCMA',          9:  'G722',
    10: 'L16',           11: 'L16',
    12: 'QCELP',         13: 'CN',
    14: 'MPA',           15: 'G728',
    16: 'DVI4',          17: 'DVI4',
    18: 'G729',          25: 'CelB',
    26: 'JPEG',          28: 'nv',
    31: 'H261',          32: 'MPV',
    33: 'MP2T',          34: 'H263' }

class RTP(Packet):
    name="RTP"
    fields_desc = [ BitField('version', 2, 2),
                    BitField('padding', 0, 1),
                    BitField('extension', 0, 1),
                    BitFieldLenField('numsync', None, 4, count_of='sync'),
                    BitField('marker', 0, 1),
                    BitEnumField('payload', 0, 7, _rtp_payload_types),
                    ShortField('sequence', 0),
                    IntField('timestamp', 0),
                    IntField('sourcesync', 0),
                    FieldListField('sync', [], IntField("id",0), count_from=lambda pkt:pkt.numsync) ]
    

########NEW FILE########
__FILENAME__ = sctp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## Copyright (C) 6WIND <olivier.matz@6wind.com>
## This program is published under a GPLv2 license

"""
SCTP (Stream Control Transmission Protocol).
"""

import struct

from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import IP
from scapy.layers.inet6 import IP6Field

IPPROTO_SCTP=132

# crc32-c (Castagnoli) (crc32c_poly=0x1EDC6F41)
crc32c_table = [
    0x00000000, 0xF26B8303, 0xE13B70F7, 0x1350F3F4,
    0xC79A971F, 0x35F1141C, 0x26A1E7E8, 0xD4CA64EB,
    0x8AD958CF, 0x78B2DBCC, 0x6BE22838, 0x9989AB3B,
    0x4D43CFD0, 0xBF284CD3, 0xAC78BF27, 0x5E133C24,
    0x105EC76F, 0xE235446C, 0xF165B798, 0x030E349B,
    0xD7C45070, 0x25AFD373, 0x36FF2087, 0xC494A384,
    0x9A879FA0, 0x68EC1CA3, 0x7BBCEF57, 0x89D76C54,
    0x5D1D08BF, 0xAF768BBC, 0xBC267848, 0x4E4DFB4B,
    0x20BD8EDE, 0xD2D60DDD, 0xC186FE29, 0x33ED7D2A,
    0xE72719C1, 0x154C9AC2, 0x061C6936, 0xF477EA35,
    0xAA64D611, 0x580F5512, 0x4B5FA6E6, 0xB93425E5,
    0x6DFE410E, 0x9F95C20D, 0x8CC531F9, 0x7EAEB2FA,
    0x30E349B1, 0xC288CAB2, 0xD1D83946, 0x23B3BA45,
    0xF779DEAE, 0x05125DAD, 0x1642AE59, 0xE4292D5A,
    0xBA3A117E, 0x4851927D, 0x5B016189, 0xA96AE28A,
    0x7DA08661, 0x8FCB0562, 0x9C9BF696, 0x6EF07595,
    0x417B1DBC, 0xB3109EBF, 0xA0406D4B, 0x522BEE48,
    0x86E18AA3, 0x748A09A0, 0x67DAFA54, 0x95B17957,
    0xCBA24573, 0x39C9C670, 0x2A993584, 0xD8F2B687,
    0x0C38D26C, 0xFE53516F, 0xED03A29B, 0x1F682198,
    0x5125DAD3, 0xA34E59D0, 0xB01EAA24, 0x42752927,
    0x96BF4DCC, 0x64D4CECF, 0x77843D3B, 0x85EFBE38,
    0xDBFC821C, 0x2997011F, 0x3AC7F2EB, 0xC8AC71E8,
    0x1C661503, 0xEE0D9600, 0xFD5D65F4, 0x0F36E6F7,
    0x61C69362, 0x93AD1061, 0x80FDE395, 0x72966096,
    0xA65C047D, 0x5437877E, 0x4767748A, 0xB50CF789,
    0xEB1FCBAD, 0x197448AE, 0x0A24BB5A, 0xF84F3859,
    0x2C855CB2, 0xDEEEDFB1, 0xCDBE2C45, 0x3FD5AF46,
    0x7198540D, 0x83F3D70E, 0x90A324FA, 0x62C8A7F9,
    0xB602C312, 0x44694011, 0x5739B3E5, 0xA55230E6,
    0xFB410CC2, 0x092A8FC1, 0x1A7A7C35, 0xE811FF36,
    0x3CDB9BDD, 0xCEB018DE, 0xDDE0EB2A, 0x2F8B6829,
    0x82F63B78, 0x709DB87B, 0x63CD4B8F, 0x91A6C88C,
    0x456CAC67, 0xB7072F64, 0xA457DC90, 0x563C5F93,
    0x082F63B7, 0xFA44E0B4, 0xE9141340, 0x1B7F9043,
    0xCFB5F4A8, 0x3DDE77AB, 0x2E8E845F, 0xDCE5075C,
    0x92A8FC17, 0x60C37F14, 0x73938CE0, 0x81F80FE3,
    0x55326B08, 0xA759E80B, 0xB4091BFF, 0x466298FC,
    0x1871A4D8, 0xEA1A27DB, 0xF94AD42F, 0x0B21572C,
    0xDFEB33C7, 0x2D80B0C4, 0x3ED04330, 0xCCBBC033,
    0xA24BB5A6, 0x502036A5, 0x4370C551, 0xB11B4652,
    0x65D122B9, 0x97BAA1BA, 0x84EA524E, 0x7681D14D,
    0x2892ED69, 0xDAF96E6A, 0xC9A99D9E, 0x3BC21E9D,
    0xEF087A76, 0x1D63F975, 0x0E330A81, 0xFC588982,
    0xB21572C9, 0x407EF1CA, 0x532E023E, 0xA145813D,
    0x758FE5D6, 0x87E466D5, 0x94B49521, 0x66DF1622,
    0x38CC2A06, 0xCAA7A905, 0xD9F75AF1, 0x2B9CD9F2,
    0xFF56BD19, 0x0D3D3E1A, 0x1E6DCDEE, 0xEC064EED,
    0xC38D26C4, 0x31E6A5C7, 0x22B65633, 0xD0DDD530,
    0x0417B1DB, 0xF67C32D8, 0xE52CC12C, 0x1747422F,
    0x49547E0B, 0xBB3FFD08, 0xA86F0EFC, 0x5A048DFF,
    0x8ECEE914, 0x7CA56A17, 0x6FF599E3, 0x9D9E1AE0,
    0xD3D3E1AB, 0x21B862A8, 0x32E8915C, 0xC083125F,
    0x144976B4, 0xE622F5B7, 0xF5720643, 0x07198540,
    0x590AB964, 0xAB613A67, 0xB831C993, 0x4A5A4A90,
    0x9E902E7B, 0x6CFBAD78, 0x7FAB5E8C, 0x8DC0DD8F,
    0xE330A81A, 0x115B2B19, 0x020BD8ED, 0xF0605BEE,
    0x24AA3F05, 0xD6C1BC06, 0xC5914FF2, 0x37FACCF1,
    0x69E9F0D5, 0x9B8273D6, 0x88D28022, 0x7AB90321,
    0xAE7367CA, 0x5C18E4C9, 0x4F48173D, 0xBD23943E,
    0xF36E6F75, 0x0105EC76, 0x12551F82, 0xE03E9C81,
    0x34F4F86A, 0xC69F7B69, 0xD5CF889D, 0x27A40B9E,
    0x79B737BA, 0x8BDCB4B9, 0x988C474D, 0x6AE7C44E,
    0xBE2DA0A5, 0x4C4623A6, 0x5F16D052, 0xAD7D5351,
    ]

def crc32c(buf):
    crc = 0xffffffff
    for c in buf:
        crc = (crc>>8) ^ crc32c_table[(crc^(ord(c))) & 0xFF]
    crc = (~crc) & 0xffffffff
    # reverse endianness
    return struct.unpack(">I",struct.pack("<I", crc))[0]

# old checksum (RFC2960)
"""
BASE = 65521 # largest prime smaller than 65536
def update_adler32(adler, buf):
    s1 = adler & 0xffff
    s2 = (adler >> 16) & 0xffff
    print s1,s2

    for c in buf:
        print ord(c)
        s1 = (s1 + ord(c)) % BASE
        s2 = (s2 + s1) % BASE
        print s1,s2
    return (s2 << 16) + s1

def sctp_checksum(buf):
    return update_adler32(1, buf)
"""

sctpchunktypescls = {
    0 : "SCTPChunkData",
    1 : "SCTPChunkInit",
    2 : "SCTPChunkInitAck",
    3 : "SCTPChunkSACK",
    4 : "SCTPChunkHeartbeatReq",
    5 : "SCTPChunkHeartbeatAck",
    6 : "SCTPChunkAbort",
    7 : "SCTPChunkShutdown",
    8 : "SCTPChunkShutdownAck",
    9 : "SCTPChunkError",
    10 : "SCTPChunkCookieEcho",
    11 : "SCTPChunkCookieAck",
    14 : "SCTPChunkShutdownComplete",
    }

sctpchunktypes = {
    0 : "data",
    1 : "init",
    2 : "init-ack",
    3 : "sack",
    4 : "heartbeat-req",
    5 : "heartbeat-ack",
    6 : "abort",
    7 : "shutdown",
    8 : "shutdown-ack",
    9 : "error",
    10 : "cookie-echo",
    11 : "cookie-ack",
    14 : "shutdown-complete",
    }

sctpchunkparamtypescls = {
    1 : "SCTPChunkParamHearbeatInfo",
    5 : "SCTPChunkParamIPv4Addr",
    6 : "SCTPChunkParamIPv6Addr",
    7 : "SCTPChunkParamStateCookie",
    8 : "SCTPChunkParamUnrocognizedParam",
    9 : "SCTPChunkParamCookiePreservative",
    11 : "SCTPChunkParamHostname",
    12 : "SCTPChunkParamSupportedAddrTypes",
    32768 : "SCTPChunkParamECNCapable",
    49152 : "SCTPChunkParamFwdTSN",
    49158 : "SCTPChunkParamAdaptationLayer",
    }

sctpchunkparamtypes = {
    1 : "heartbeat-info",
    5 : "IPv4",
    6 : "IPv6",
    7 : "state-cookie",
    8 : "unrecognized-param",
    9 : "cookie-preservative",
    11 : "hostname",
    12 : "addrtypes",
    32768 : "ecn-capable",
    49152 : "fwd-tsn-supported",
    49158 : "adaptation-layer",
    }

############## SCTP header

# Dummy class to guess payload type (variable parameters)
class _SCTPChunkGuessPayload:
    def default_payload_class(self,p):
        if len(p) < 4:
            return Padding
        else:
            t = ord(p[0])
            return globals().get(sctpchunktypescls.get(t, "Raw"), Raw)


class SCTP(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ShortField("sport", None),
                    ShortField("dport", None),
                    XIntField("tag", None),
                    XIntField("chksum", None), ]
    def answers(self, other):
        if not isinstance(other, SCTP):
            return 0
        if conf.checkIPsrc:
            if not ((self.sport == other.dport) and
                    (self.dport == other.sport)):
                return 0
        return 1
    def post_build(self, p, pay):
        p += pay
        if self.chksum is None:
            crc = crc32c(str(p))
            p = p[:8]+struct.pack(">I", crc)+p[12:]
        return p

############## SCTP Chunk variable params

class ChunkParamField(PacketListField):
    islist = 1
    holds_packets=1
    def __init__(self, name, default, count_from=None, length_from=None):
        PacketListField.__init__(self, name, default, Raw, count_from=count_from, length_from=length_from)
    def m2i(self, p, m):
        cls = Raw
        if len(m) >= 4:
            t = ord(m[0]) * 256 + ord(m[1])
            cls = globals().get(sctpchunkparamtypescls.get(t, "Raw"), Raw)
        return cls(m)

# dummy class to avoid Raw() after Chunk params
class _SCTPChunkParam:
    def extract_padding(self, s):
        return "",s[:]

class SCTPChunkParamHearbeatInfo(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 1, sctpchunkparamtypes),
                    FieldLenField("len", None, length_of="data",
                                  adjust = lambda pkt,x:x+4),
                    PadField(StrLenField("data", "",
                                         length_from=lambda pkt: pkt.len-4),
                             4, padwith="\x00"),]

class SCTPChunkParamIPv4Addr(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 5, sctpchunkparamtypes),
                    ShortField("len", 8),
                    IPField("addr","127.0.0.1"), ]

class SCTPChunkParamIPv6Addr(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 6, sctpchunkparamtypes),
                    ShortField("len", 20),
                    IP6Field("addr","::1"), ]

class SCTPChunkParamStateCookie(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 7, sctpchunkparamtypes),
                    FieldLenField("len", None, length_of="cookie",
                                  adjust = lambda pkt,x:x+4),
                    PadField(StrLenField("cookie", "",
                                         length_from=lambda pkt: pkt.len-4),
                             4, padwith="\x00"),]

class SCTPChunkParamUnrocognizedParam(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 8, sctpchunkparamtypes),
                    FieldLenField("len", None, length_of="param",
                                  adjust = lambda pkt,x:x+4),
                    PadField(StrLenField("param", "",
                                         length_from=lambda pkt: pkt.len-4),
                             4, padwith="\x00"),]

class SCTPChunkParamCookiePreservative(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 9, sctpchunkparamtypes),
                    ShortField("len", 8),
                    XIntField("sug_cookie_inc", None), ]

class SCTPChunkParamHostname(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 11, sctpchunkparamtypes),
                    FieldLenField("len", None, length_of="hostname",
                                  adjust = lambda pkt,x:x+4),
                    PadField(StrLenField("hostname", "",
                                         length_from=lambda pkt: pkt.len-4),
                             4, padwith="\x00"), ]

class SCTPChunkParamSupportedAddrTypes(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 12, sctpchunkparamtypes),
                    FieldLenField("len", None, length_of="addr_type_list",
                                  adjust = lambda pkt,x:x+4),
                    PadField(FieldListField("addr_type_list", [ "IPv4" ],
                                            ShortEnumField("addr_type", 5, sctpchunkparamtypes),
                                            length_from=lambda pkt: pkt.len-4),
                             4, padwith="\x00"), ]

class SCTPChunkParamECNCapable(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 32768, sctpchunkparamtypes),
                    ShortField("len", 4), ]

class SCTPChunkParamFwdTSN(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 49152, sctpchunkparamtypes),
                    ShortField("len", 4), ]

class SCTPChunkParamAdaptationLayer(_SCTPChunkParam, Packet):
    fields_desc = [ ShortEnumField("type", 49158, sctpchunkparamtypes),
                    ShortField("len", 8),
                    XIntField("indication", None), ]

############## SCTP Chunks

class SCTPChunkData(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 0, sctpchunktypes),
                    BitField("reserved", None, 4),
                    BitField("delay_sack", 0, 1),
                    BitField("unordered", 0, 1),
                    BitField("beginning", 0, 1),
                    BitField("ending", 0, 1),
                    FieldLenField("len", None, length_of="data", adjust = lambda pkt,x:x+16),
                    XIntField("tsn", None),
                    XShortField("stream_id", None),
                    XShortField("stream_seq", None),
                    XIntField("proto_id", None),
                    PadField(StrLenField("data", None, length_from=lambda pkt: pkt.len-16),
                             4, padwith="\x00"),
                    ]

class SCTPChunkInit(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 1, sctpchunktypes),
                    XByteField("flags", None),
                    FieldLenField("len", None, length_of="params", adjust = lambda pkt,x:x+20),
                    XIntField("init_tag", None),
                    IntField("a_rwnd", None),
                    ShortField("n_out_streams", None),
                    ShortField("n_in_streams", None),
                    XIntField("init_tsn", None),
                    ChunkParamField("params", None, length_from=lambda pkt:pkt.len-20),
                    ]

class SCTPChunkInitAck(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 2, sctpchunktypes),
                    XByteField("flags", None),
                    FieldLenField("len", None, length_of="params", adjust = lambda pkt,x:x+20),
                    XIntField("init_tag", None),
                    IntField("a_rwnd", None),
                    ShortField("n_out_streams", None),
                    ShortField("n_in_streams", None),
                    XIntField("init_tsn", None),
                    ChunkParamField("params", None, length_from=lambda pkt:pkt.len-20),
                    ]

class GapAckField(Field):
    def __init__(self, name, default):
        Field.__init__(self, name, default, "4s")
    def i2m(self, pkt, x):
        if x is None:
            return "\0\0\0\0"
        sta, end = map(int, x.split(":"))
        args = tuple([">HH", sta, end])
        return struct.pack(*args)
    def m2i(self, pkt, x):
        return "%d:%d"%(struct.unpack(">HH", x))
    def any2i(self, pkt, x):
        if type(x) is tuple and len(x) == 2:
            return "%d:%d"%(x)
        return x

class SCTPChunkSACK(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 3, sctpchunktypes),
                    XByteField("flags", None),
                    ShortField("len", None),
                    XIntField("cumul_tsn_ack", None),
                    IntField("a_rwnd", None),
                    FieldLenField("n_gap_ack", None, count_of="gap_ack_list"),
                    FieldLenField("n_dup_tsn", None, count_of="dup_tsn_list"),
                    FieldListField("gap_ack_list", [ ], GapAckField("gap_ack", None), count_from=lambda pkt:pkt.n_gap_ack),
                    FieldListField("dup_tsn_list", [ ], XIntField("dup_tsn", None), count_from=lambda pkt:pkt.n_dup_tsn),
                    ]

    def post_build(self, p, pay):
        if self.len is None:
            p = p[:2] + struct.pack(">H", len(p)) + p[4:]
        return p+pay


class SCTPChunkHeartbeatReq(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 4, sctpchunktypes),
                    XByteField("flags", None),
                    FieldLenField("len", None, length_of="params", adjust = lambda pkt,x:x+4),
                    ChunkParamField("params", None, length_from=lambda pkt:pkt.len-4),
                   ]

class SCTPChunkHeartbeatAck(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 5, sctpchunktypes),
                    XByteField("flags", None),
                    FieldLenField("len", None, length_of="params", adjust = lambda pkt,x:x+4),
                    ChunkParamField("params", None, length_from=lambda pkt:pkt.len-4),
                   ]

class SCTPChunkAbort(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 6, sctpchunktypes),
                    BitField("reserved", None, 7),
                    BitField("TCB", 0, 1),
                    FieldLenField("len", None, length_of="error_causes", adjust = lambda pkt,x:x+4),
                    PadField(StrLenField("error_causes", "", length_from=lambda pkt: pkt.len-4),
                             4, padwith="\x00"),
                   ]

class SCTPChunkShutdown(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 7, sctpchunktypes),
                    XByteField("flags", None),
                    ShortField("len", 8),
                    XIntField("cumul_tsn_ack", None),
                   ]

class SCTPChunkShutdownAck(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 8, sctpchunktypes),
                    XByteField("flags", None),
                    ShortField("len", 4),
                   ]

class SCTPChunkError(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 9, sctpchunktypes),
                    XByteField("flags", None),
                    FieldLenField("len", None, length_of="error_causes", adjust = lambda pkt,x:x+4),
                    PadField(StrLenField("error_causes", "", length_from=lambda pkt: pkt.len-4),
                             4, padwith="\x00"),
                   ]

class SCTPChunkCookieEcho(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 10, sctpchunktypes),
                    XByteField("flags", None),
                    FieldLenField("len", None, length_of="cookie", adjust = lambda pkt,x:x+4),
                    PadField(StrLenField("cookie", "", length_from=lambda pkt: pkt.len-4),
                             4, padwith="\x00"),
                   ]

class SCTPChunkCookieAck(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 11, sctpchunktypes),
                    XByteField("flags", None),
                    ShortField("len", 4),
                   ]

class SCTPChunkShutdownComplete(_SCTPChunkGuessPayload, Packet):
    fields_desc = [ ByteEnumField("type", 12, sctpchunktypes),
                    BitField("reserved", None, 7),
                    BitField("TCB", 0, 1),
                    ShortField("len", 4),
                    ]

bind_layers( IP,           SCTP,          proto=IPPROTO_SCTP)


########NEW FILE########
__FILENAME__ = sebek
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Sebek: Linux kernel module for data collection on honeypots.
"""

from scapy.fields import *
from scapy.packet import *
from scapy.layers.inet import UDP


### SEBEK


class SebekHead(Packet):
    name = "Sebek header"
    fields_desc = [ XIntField("magic", 0xd0d0d0),
                    ShortField("version", 1),
                    ShortEnumField("type", 0, {"read":0, "write":1,
                                             "socket":2, "open":3}),
                    IntField("counter", 0),
                    IntField("time_sec", 0),
                    IntField("time_usec", 0) ]
    def mysummary(self):
        return self.sprintf("Sebek Header v%SebekHead.version% %SebekHead.type%")

# we need this because Sebek headers differ between v1 and v3, and
# between v3 type socket and v3 others

class SebekV1(Packet):
    name = "Sebek v1"
    fields_desc = [ IntField("pid", 0),
                    IntField("uid", 0),
                    IntField("fd", 0),
                    StrFixedLenField("command", "", 12),
                    FieldLenField("data_length", None, "data",fmt="I"),
                    StrLenField("data", "", length_from=lambda x:x.data_length) ]
    def mysummary(self):
        if isinstance(self.underlayer, SebekHead):
            return self.underlayer.sprintf("Sebek v1 %SebekHead.type% (%SebekV1.command%)")
        else:
            return self.sprintf("Sebek v1 (%SebekV1.command%)")

class SebekV3(Packet):
    name = "Sebek v3"
    fields_desc = [ IntField("parent_pid", 0),
                    IntField("pid", 0),
                    IntField("uid", 0),
                    IntField("fd", 0),
                    IntField("inode", 0),
                    StrFixedLenField("command", "", 12),
                    FieldLenField("data_length", None, "data",fmt="I"),
                    StrLenField("data", "", length_from=lambda x:x.data_length) ]
    def mysummary(self):
        if isinstance(self.underlayer, SebekHead):
            return self.underlayer.sprintf("Sebek v%SebekHead.version% %SebekHead.type% (%SebekV3.command%)")
        else:
            return self.sprintf("Sebek v3 (%SebekV3.command%)")

class SebekV2(SebekV3):
    def mysummary(self):
        if isinstance(self.underlayer, SebekHead):
            return self.underlayer.sprintf("Sebek v%SebekHead.version% %SebekHead.type% (%SebekV2.command%)")
        else:
            return self.sprintf("Sebek v2 (%SebekV2.command%)")

class SebekV3Sock(Packet):
    name = "Sebek v2 socket"
    fields_desc = [ IntField("parent_pid", 0),
                    IntField("pid", 0),
                    IntField("uid", 0),
                    IntField("fd", 0),
                    IntField("inode", 0),
                    StrFixedLenField("command", "", 12),
                    IntField("data_length", 15),
                    IPField("dip", "127.0.0.1"),
                    ShortField("dport", 0),
                    IPField("sip", "127.0.0.1"),
                    ShortField("sport", 0),
                    ShortEnumField("call", 0, { "bind":2,
                                                "connect":3, "listen":4,
                                               "accept":5, "sendmsg":16,
                                               "recvmsg":17, "sendto":11,
                                               "recvfrom":12}),
                    ByteEnumField("proto", 0, IP_PROTOS) ]
    def mysummary(self):
        if isinstance(self.underlayer, SebekHead):
            return self.underlayer.sprintf("Sebek v%SebekHead.version% %SebekHead.type% (%SebekV3Sock.command%)")
        else:
            return self.sprintf("Sebek v3 socket (%SebekV3Sock.command%)")

class SebekV2Sock(SebekV3Sock):
    def mysummary(self):
        if isinstance(self.underlayer, SebekHead):
            return self.underlayer.sprintf("Sebek v%SebekHead.version% %SebekHead.type% (%SebekV2Sock.command%)")
        else:
            return self.sprintf("Sebek v2 socket (%SebekV2Sock.command%)")

bind_layers( UDP,           SebekHead,     sport=1101)
bind_layers( UDP,           SebekHead,     dport=1101)
bind_layers( UDP,           SebekHead,     dport=1101, sport=1101)
bind_layers( SebekHead,     SebekV1,       version=1)
bind_layers( SebekHead,     SebekV2Sock,   version=2, type=2)
bind_layers( SebekHead,     SebekV2,       version=2)
bind_layers( SebekHead,     SebekV3Sock,   version=3, type=2)
bind_layers( SebekHead,     SebekV3,       version=3)

########NEW FILE########
__FILENAME__ = skinny
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Cisco Skinny protocol.
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import TCP

# shamelessly ripped from Ethereal dissector
skinny_messages = { 
# Station -> Callmanager
  0x0000: "KeepAliveMessage",
  0x0001: "RegisterMessage",
  0x0002: "IpPortMessage",
  0x0003: "KeypadButtonMessage",
  0x0004: "EnblocCallMessage",
  0x0005: "StimulusMessage",
  0x0006: "OffHookMessage",
  0x0007: "OnHookMessage",
  0x0008: "HookFlashMessage",
  0x0009: "ForwardStatReqMessage",
  0x000A: "SpeedDialStatReqMessage",
  0x000B: "LineStatReqMessage",
  0x000C: "ConfigStatReqMessage",
  0x000D: "TimeDateReqMessage",
  0x000E: "ButtonTemplateReqMessage",
  0x000F: "VersionReqMessage",
  0x0010: "CapabilitiesResMessage",
  0x0011: "MediaPortListMessage",
  0x0012: "ServerReqMessage",
  0x0020: "AlarmMessage",
  0x0021: "MulticastMediaReceptionAck",
  0x0022: "OpenReceiveChannelAck",
  0x0023: "ConnectionStatisticsRes",
  0x0024: "OffHookWithCgpnMessage",
  0x0025: "SoftKeySetReqMessage",
  0x0026: "SoftKeyEventMessage",
  0x0027: "UnregisterMessage",
  0x0028: "SoftKeyTemplateReqMessage",
  0x0029: "RegisterTokenReq",
  0x002A: "MediaTransmissionFailure",
  0x002B: "HeadsetStatusMessage",
  0x002C: "MediaResourceNotification",
  0x002D: "RegisterAvailableLinesMessage",
  0x002E: "DeviceToUserDataMessage",
  0x002F: "DeviceToUserDataResponseMessage",
  0x0030: "UpdateCapabilitiesMessage",
  0x0031: "OpenMultiMediaReceiveChannelAckMessage",
  0x0032: "ClearConferenceMessage",
  0x0033: "ServiceURLStatReqMessage",
  0x0034: "FeatureStatReqMessage",
  0x0035: "CreateConferenceResMessage",
  0x0036: "DeleteConferenceResMessage",
  0x0037: "ModifyConferenceResMessage",
  0x0038: "AddParticipantResMessage",
  0x0039: "AuditConferenceResMessage",
  0x0040: "AuditParticipantResMessage",
  0x0041: "DeviceToUserDataVersion1Message",
# Callmanager -> Station */
  0x0081: "RegisterAckMessage",
  0x0082: "StartToneMessage",
  0x0083: "StopToneMessage",
  0x0085: "SetRingerMessage",
  0x0086: "SetLampMessage",
  0x0087: "SetHkFDetectMessage",
  0x0088: "SetSpeakerModeMessage",
  0x0089: "SetMicroModeMessage",
  0x008A: "StartMediaTransmission",
  0x008B: "StopMediaTransmission",
  0x008C: "StartMediaReception",
  0x008D: "StopMediaReception",
  0x008F: "CallInfoMessage",
  0x0090: "ForwardStatMessage",
  0x0091: "SpeedDialStatMessage",
  0x0092: "LineStatMessage",
  0x0093: "ConfigStatMessage",
  0x0094: "DefineTimeDate",
  0x0095: "StartSessionTransmission",
  0x0096: "StopSessionTransmission",
  0x0097: "ButtonTemplateMessage",
  0x0098: "VersionMessage",
  0x0099: "DisplayTextMessage",
  0x009A: "ClearDisplay",
  0x009B: "CapabilitiesReqMessage",
  0x009C: "EnunciatorCommandMessage",
  0x009D: "RegisterRejectMessage",
  0x009E: "ServerResMessage",
  0x009F: "Reset",
  0x0100: "KeepAliveAckMessage",
  0x0101: "StartMulticastMediaReception",
  0x0102: "StartMulticastMediaTransmission",
  0x0103: "StopMulticastMediaReception",
  0x0104: "StopMulticastMediaTransmission",
  0x0105: "OpenReceiveChannel",
  0x0106: "CloseReceiveChannel",
  0x0107: "ConnectionStatisticsReq",
  0x0108: "SoftKeyTemplateResMessage",
  0x0109: "SoftKeySetResMessage",
  0x0110: "SelectSoftKeysMessage",
  0x0111: "CallStateMessage",
  0x0112: "DisplayPromptStatusMessage",
  0x0113: "ClearPromptStatusMessage",
  0x0114: "DisplayNotifyMessage",
  0x0115: "ClearNotifyMessage",
  0x0116: "ActivateCallPlaneMessage",
  0x0117: "DeactivateCallPlaneMessage",
  0x0118: "UnregisterAckMessage",
  0x0119: "BackSpaceReqMessage",
  0x011A: "RegisterTokenAck",
  0x011B: "RegisterTokenReject",
  0x0042: "DeviceToUserDataResponseVersion1Message",
  0x011C: "StartMediaFailureDetection",
  0x011D: "DialedNumberMessage",
  0x011E: "UserToDeviceDataMessage",
  0x011F: "FeatureStatMessage",
  0x0120: "DisplayPriNotifyMessage",
  0x0121: "ClearPriNotifyMessage",
  0x0122: "StartAnnouncementMessage",
  0x0123: "StopAnnouncementMessage",
  0x0124: "AnnouncementFinishMessage",
  0x0127: "NotifyDtmfToneMessage",
  0x0128: "SendDtmfToneMessage",
  0x0129: "SubscribeDtmfPayloadReqMessage",
  0x012A: "SubscribeDtmfPayloadResMessage",
  0x012B: "SubscribeDtmfPayloadErrMessage",
  0x012C: "UnSubscribeDtmfPayloadReqMessage",
  0x012D: "UnSubscribeDtmfPayloadResMessage",
  0x012E: "UnSubscribeDtmfPayloadErrMessage",
  0x012F: "ServiceURLStatMessage",
  0x0130: "CallSelectStatMessage",
  0x0131: "OpenMultiMediaChannelMessage",
  0x0132: "StartMultiMediaTransmission",
  0x0133: "StopMultiMediaTransmission",
  0x0134: "MiscellaneousCommandMessage",
  0x0135: "FlowControlCommandMessage",
  0x0136: "CloseMultiMediaReceiveChannel",
  0x0137: "CreateConferenceReqMessage",
  0x0138: "DeleteConferenceReqMessage",
  0x0139: "ModifyConferenceReqMessage",
  0x013A: "AddParticipantReqMessage",
  0x013B: "DropParticipantReqMessage",
  0x013C: "AuditConferenceReqMessage",
  0x013D: "AuditParticipantReqMessage",
  0x013F: "UserToDeviceDataVersion1Message",
  }


        
class Skinny(Packet):
    name="Skinny"
    fields_desc = [ LEIntField("len",0),
                    LEIntField("res",0),
                    LEIntEnumField("msg",0,skinny_messages) ]

bind_layers( TCP,           Skinny,        dport=2000)
bind_layers( TCP,           Skinny,        sport=2000)

########NEW FILE########
__FILENAME__ = smb
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
SMB (Server Message Block), also known as CIFS.
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.netbios import NBTSession


# SMB NetLogon Response Header
class SMBNetlogon_Protocol_Response_Header(Packet):
    name="SMBNetlogon Protocol Response Header"
    fields_desc = [StrFixedLenField("Start","\xffSMB",4),
                   ByteEnumField("Command",0x25,{0x25:"Trans"}),
                   ByteField("Error_Class",0x02),
                   ByteField("Reserved",0),
                   LEShortField("Error_code",4),
                   ByteField("Flags",0),
                   LEShortField("Flags2",0x0000),
                   LEShortField("PIDHigh",0x0000),
                   LELongField("Signature",0x0),
                   LEShortField("Unused",0x0),
                   LEShortField("TID",0),
                   LEShortField("PID",0),
                   LEShortField("UID",0),
                   LEShortField("MID",0),
                   ByteField("WordCount",17),
                   LEShortField("TotalParamCount",0),
                   LEShortField("TotalDataCount",112),
                   LEShortField("MaxParamCount",0),
                   LEShortField("MaxDataCount",0),
                   ByteField("MaxSetupCount",0),
                   ByteField("unused2",0),
                   LEShortField("Flags3",0),
                   ByteField("TimeOut1",0xe8),
                   ByteField("TimeOut2",0x03),
                   LEShortField("unused3",0),
                   LEShortField("unused4",0),
                   LEShortField("ParamCount2",0),
                   LEShortField("ParamOffset",0),
                   LEShortField("DataCount",112),
                   LEShortField("DataOffset",92),
                   ByteField("SetupCount", 3),
                   ByteField("unused5", 0)]

# SMB MailSlot Protocol
class SMBMailSlot(Packet):
    name = "SMB Mail Slot Protocol"
    fields_desc = [LEShortField("opcode", 1),
                   LEShortField("priority", 1),
                   LEShortField("class", 2),
                   LEShortField("size", 135),
                   StrNullField("name","\MAILSLOT\NET\GETDC660")]

# SMB NetLogon Protocol Response Tail SAM
class SMBNetlogon_Protocol_Response_Tail_SAM(Packet):
    name = "SMB Netlogon Protocol Response Tail SAM"
    fields_desc = [ByteEnumField("Command", 0x17, {0x12:"SAM logon request", 0x17:"SAM Active directory Response"}),
                   ByteField("unused", 0),
                   ShortField("Data1", 0),
                   ShortField("Data2", 0xfd01),
                   ShortField("Data3", 0),
                   ShortField("Data4", 0xacde),
                   ShortField("Data5", 0x0fe5),
                   ShortField("Data6", 0xd10a),
                   ShortField("Data7", 0x374c),
                   ShortField("Data8", 0x83e2),
                   ShortField("Data9", 0x7dd9),
                   ShortField("Data10", 0x3a16),
                   ShortField("Data11", 0x73ff),
                   ByteField("Data12", 0x04),
                   StrFixedLenField("Data13", "rmff", 4),
                   ByteField("Data14", 0x0),
                   ShortField("Data16", 0xc018),
                   ByteField("Data18", 0x0a),
                   StrFixedLenField("Data20", "rmff-win2k", 10),
                   ByteField("Data21", 0xc0),
                   ShortField("Data22", 0x18c0),
                   ShortField("Data23", 0x180a),
                   StrFixedLenField("Data24", "RMFF-WIN2K", 10),
                   ShortField("Data25", 0),
                   ByteField("Data26", 0x17),
                   StrFixedLenField("Data27", "Default-First-Site-Name", 23),
                   ShortField("Data28", 0x00c0),
                   ShortField("Data29", 0x3c10),
                   ShortField("Data30", 0x00c0),
                   ShortField("Data31", 0x0200),
                   ShortField("Data32", 0x0),
                   ShortField("Data33", 0xac14),
                   ShortField("Data34", 0x0064),
                   ShortField("Data35", 0x0),
                   ShortField("Data36", 0x0),
                   ShortField("Data37", 0x0),
                   ShortField("Data38", 0x0),
                   ShortField("Data39", 0x0d00),
                   ShortField("Data40", 0x0),
                   ShortField("Data41", 0xffff)]                   

# SMB NetLogon Protocol Response Tail LM2.0
class SMBNetlogon_Protocol_Response_Tail_LM20(Packet):
    name = "SMB Netlogon Protocol Response Tail LM20"
    fields_desc = [ByteEnumField("Command",0x06,{0x06:"LM 2.0 Response to logon request"}),
                   ByteField("unused", 0),
                   StrFixedLenField("DblSlash", "\\\\", 2),
                   StrNullField("ServerName","WIN"),
                   LEShortField("LM20Token", 0xffff)]

# SMBNegociate Protocol Request Header
class SMBNegociate_Protocol_Request_Header(Packet):
    name="SMBNegociate Protocol Request Header"
    fields_desc = [StrFixedLenField("Start","\xffSMB",4),
                   ByteEnumField("Command",0x72,{0x72:"SMB_COM_NEGOTIATE"}),
                   ByteField("Error_Class",0),
                   ByteField("Reserved",0),
                   LEShortField("Error_code",0),
                   ByteField("Flags",0x18),
                   LEShortField("Flags2",0x0000),
                   LEShortField("PIDHigh",0x0000),
                   LELongField("Signature",0x0),
                   LEShortField("Unused",0x0),
                   LEShortField("TID",0),
                   LEShortField("PID",1),
                   LEShortField("UID",0),
                   LEShortField("MID",2),
                   ByteField("WordCount",0),
                   LEShortField("ByteCount",12)]

# SMB Negociate Protocol Request Tail
class SMBNegociate_Protocol_Request_Tail(Packet):
    name="SMB Negociate Protocol Request Tail"
    fields_desc=[ByteField("BufferFormat",0x02),
                 StrNullField("BufferData","NT LM 0.12")]

# SMBNegociate Protocol Response Advanced Security
class SMBNegociate_Protocol_Response_Advanced_Security(Packet):
    name="SMBNegociate Protocol Response Advanced Security"
    fields_desc = [StrFixedLenField("Start","\xffSMB",4),
                   ByteEnumField("Command",0x72,{0x72:"SMB_COM_NEGOTIATE"}),
                   ByteField("Error_Class",0),
                   ByteField("Reserved",0),
                   LEShortField("Error_Code",0),
                   ByteField("Flags",0x98),
                   LEShortField("Flags2",0x0000),
                   LEShortField("PIDHigh",0x0000),
                   LELongField("Signature",0x0),
                   LEShortField("Unused",0x0),
                   LEShortField("TID",0),
                   LEShortField("PID",1),
                   LEShortField("UID",0),
                   LEShortField("MID",2),
                   ByteField("WordCount",17),
                   LEShortField("DialectIndex",7),
                   ByteField("SecurityMode",0x03),
                   LEShortField("MaxMpxCount",50),
                   LEShortField("MaxNumberVC",1),
                   LEIntField("MaxBufferSize",16144),
                   LEIntField("MaxRawSize",65536),
                   LEIntField("SessionKey",0x0000),
                   LEShortField("ServerCapabilities",0xf3f9),
                   BitField("UnixExtensions",0,1),
                   BitField("Reserved2",0,7),
                   BitField("ExtendedSecurity",1,1),
                   BitField("CompBulk",0,2),
                   BitField("Reserved3",0,5),
# There have been 127490112000000000 tenths of micro-seconds between 1st january 1601 and 1st january 2005. 127490112000000000=0x1C4EF94D6228000, so ServerTimeHigh=0xD6228000 and ServerTimeLow=0x1C4EF94.
                   LEIntField("ServerTimeHigh",0xD6228000L),
                   LEIntField("ServerTimeLow",0x1C4EF94),
                   LEShortField("ServerTimeZone",0x3c),
                   ByteField("EncryptionKeyLength",0),
                   LEFieldLenField("ByteCount", None, "SecurityBlob", adjust=lambda pkt,x:x-16),
                   BitField("GUID",0,128),
                   StrLenField("SecurityBlob", "", length_from=lambda x:x.ByteCount+16)]

# SMBNegociate Protocol Response No Security
# When using no security, with EncryptionKeyLength=8, you must have an EncryptionKey before the DomainName
class SMBNegociate_Protocol_Response_No_Security(Packet):
    name="SMBNegociate Protocol Response No Security"
    fields_desc = [StrFixedLenField("Start","\xffSMB",4),
                   ByteEnumField("Command",0x72,{0x72:"SMB_COM_NEGOTIATE"}),
                   ByteField("Error_Class",0),
                   ByteField("Reserved",0),
                   LEShortField("Error_Code",0),
                   ByteField("Flags",0x98),
                   LEShortField("Flags2",0x0000),
                   LEShortField("PIDHigh",0x0000),
                   LELongField("Signature",0x0),
                   LEShortField("Unused",0x0),
                   LEShortField("TID",0),
                   LEShortField("PID",1),
                   LEShortField("UID",0),
                   LEShortField("MID",2),
                   ByteField("WordCount",17),
                   LEShortField("DialectIndex",7),
                   ByteField("SecurityMode",0x03),
                   LEShortField("MaxMpxCount",50),
                   LEShortField("MaxNumberVC",1),
                   LEIntField("MaxBufferSize",16144),
                   LEIntField("MaxRawSize",65536),
                   LEIntField("SessionKey",0x0000),
                   LEShortField("ServerCapabilities",0xf3f9),
                   BitField("UnixExtensions",0,1),
                   BitField("Reserved2",0,7),
                   BitField("ExtendedSecurity",0,1),
                   FlagsField("CompBulk",0,2,"CB"),
                   BitField("Reserved3",0,5),
                   # There have been 127490112000000000 tenths of micro-seconds between 1st january 1601 and 1st january 2005. 127490112000000000=0x1C4EF94D6228000, so ServerTimeHigh=0xD6228000 and ServerTimeLow=0x1C4EF94.
                   LEIntField("ServerTimeHigh",0xD6228000L),
                   LEIntField("ServerTimeLow",0x1C4EF94),
                   LEShortField("ServerTimeZone",0x3c),
                   ByteField("EncryptionKeyLength",8),
                   LEShortField("ByteCount",24),
                   BitField("EncryptionKey",0,64),
                   StrNullField("DomainName","WORKGROUP"),
                   StrNullField("ServerName","RMFF1")]
    
# SMBNegociate Protocol Response No Security No Key
class SMBNegociate_Protocol_Response_No_Security_No_Key(Packet):
    namez="SMBNegociate Protocol Response No Security No Key"
    fields_desc = [StrFixedLenField("Start","\xffSMB",4),
                   ByteEnumField("Command",0x72,{0x72:"SMB_COM_NEGOTIATE"}),
                   ByteField("Error_Class",0),
                   ByteField("Reserved",0),
                   LEShortField("Error_Code",0),
                   ByteField("Flags",0x98),
                   LEShortField("Flags2",0x0000),
                   LEShortField("PIDHigh",0x0000),
                   LELongField("Signature",0x0),
                   LEShortField("Unused",0x0),
                   LEShortField("TID",0),
                   LEShortField("PID",1),
                   LEShortField("UID",0),
                   LEShortField("MID",2),
                   ByteField("WordCount",17),
                   LEShortField("DialectIndex",7),
                   ByteField("SecurityMode",0x03),
                   LEShortField("MaxMpxCount",50),
                   LEShortField("MaxNumberVC",1),
                   LEIntField("MaxBufferSize",16144),
                   LEIntField("MaxRawSize",65536),
                   LEIntField("SessionKey",0x0000),
                   LEShortField("ServerCapabilities",0xf3f9),
                   BitField("UnixExtensions",0,1),
                   BitField("Reserved2",0,7),
                   BitField("ExtendedSecurity",0,1),
                   FlagsField("CompBulk",0,2,"CB"),
                   BitField("Reserved3",0,5),
                   # There have been 127490112000000000 tenths of micro-seconds between 1st january 1601 and 1st january 2005. 127490112000000000=0x1C4EF94D6228000, so ServerTimeHigh=0xD6228000 and ServerTimeLow=0x1C4EF94.
                   LEIntField("ServerTimeHigh",0xD6228000L),
                   LEIntField("ServerTimeLow",0x1C4EF94),
                   LEShortField("ServerTimeZone",0x3c),
                   ByteField("EncryptionKeyLength",0),
                   LEShortField("ByteCount",16),
                   StrNullField("DomainName","WORKGROUP"),
                   StrNullField("ServerName","RMFF1")]
    
# Session Setup AndX Request
class SMBSession_Setup_AndX_Request(Packet):
    name="Session Setup AndX Request"
    fields_desc=[StrFixedLenField("Start","\xffSMB",4),
                ByteEnumField("Command",0x73,{0x73:"SMB_COM_SESSION_SETUP_ANDX"}),
                 ByteField("Error_Class",0),
                 ByteField("Reserved",0),
                 LEShortField("Error_Code",0),
                 ByteField("Flags",0x18),
                 LEShortField("Flags2",0x0001),
                 LEShortField("PIDHigh",0x0000),
                 LELongField("Signature",0x0),
                 LEShortField("Unused",0x0),
                 LEShortField("TID",0),
                 LEShortField("PID",1),
                 LEShortField("UID",0),
                 LEShortField("MID",2),
                 ByteField("WordCount",13),
                 ByteEnumField("AndXCommand",0x75,{0x75:"SMB_COM_TREE_CONNECT_ANDX"}),
                 ByteField("Reserved2",0),
                 LEShortField("AndXOffset",96),
                 LEShortField("MaxBufferS",2920),
                 LEShortField("MaxMPXCount",50),
                 LEShortField("VCNumber",0),
                 LEIntField("SessionKey",0),
                 LEFieldLenField("ANSIPasswordLength",None,"ANSIPassword"),
                 LEShortField("UnicodePasswordLength",0),
                 LEIntField("Reserved3",0),
                 LEShortField("ServerCapabilities",0x05),
                 BitField("UnixExtensions",0,1),
                 BitField("Reserved4",0,7),
                 BitField("ExtendedSecurity",0,1),
                 BitField("CompBulk",0,2),
                 BitField("Reserved5",0,5),
                 LEShortField("ByteCount",35),
                 StrLenField("ANSIPassword", "Pass",length_from=lambda x:x.ANSIPasswordLength),
                 StrNullField("Account","GUEST"),
                 StrNullField("PrimaryDomain",  ""),
                 StrNullField("NativeOS","Windows 4.0"),
                 StrNullField("NativeLanManager","Windows 4.0"),
                 ByteField("WordCount2",4),
                 ByteEnumField("AndXCommand2",0xFF,{0xFF:"SMB_COM_NONE"}),
                 ByteField("Reserved6",0),
                 LEShortField("AndXOffset2",0),
                 LEShortField("Flags3",0x2),
                 LEShortField("PasswordLength",0x1),
                 LEShortField("ByteCount2",18),
                 ByteField("Password",0),
                 StrNullField("Path","\\\\WIN2K\\IPC$"),
                 StrNullField("Service","IPC")]

# Session Setup AndX Response
class SMBSession_Setup_AndX_Response(Packet):
    name="Session Setup AndX Response"
    fields_desc=[StrFixedLenField("Start","\xffSMB",4),
                 ByteEnumField("Command",0x73,{0x73:"SMB_COM_SESSION_SETUP_ANDX"}),
                 ByteField("Error_Class",0),
                 ByteField("Reserved",0),
                 LEShortField("Error_Code",0),
                 ByteField("Flags",0x90),
                 LEShortField("Flags2",0x1001),
                 LEShortField("PIDHigh",0x0000),
                 LELongField("Signature",0x0),
                 LEShortField("Unused",0x0),
                 LEShortField("TID",0),
                 LEShortField("PID",1),
                 LEShortField("UID",0),
                 LEShortField("MID",2),
                 ByteField("WordCount",3),
                 ByteEnumField("AndXCommand",0x75,{0x75:"SMB_COM_TREE_CONNECT_ANDX"}),
                 ByteField("Reserved2",0),
                 LEShortField("AndXOffset",66),
                 LEShortField("Action",0),
                 LEShortField("ByteCount",25),
                 StrNullField("NativeOS","Windows 4.0"),
                 StrNullField("NativeLanManager","Windows 4.0"),
                 StrNullField("PrimaryDomain",""),
                 ByteField("WordCount2",3),
                 ByteEnumField("AndXCommand2",0xFF,{0xFF:"SMB_COM_NONE"}),
                 ByteField("Reserved3",0),
                 LEShortField("AndXOffset2",80),
                 LEShortField("OptionalSupport",0x01),
                 LEShortField("ByteCount2",5),
                 StrNullField("Service","IPC"),
                 StrNullField("NativeFileSystem","")]

bind_layers( NBTSession,                           SMBNegociate_Protocol_Request_Header, )
bind_layers( NBTSession,    SMBNegociate_Protocol_Response_Advanced_Security,  ExtendedSecurity=1)
bind_layers( NBTSession,    SMBNegociate_Protocol_Response_No_Security,        ExtendedSecurity=0, EncryptionKeyLength=8)
bind_layers( NBTSession,    SMBNegociate_Protocol_Response_No_Security_No_Key, ExtendedSecurity=0, EncryptionKeyLength=0)
bind_layers( NBTSession,    SMBSession_Setup_AndX_Request, )
bind_layers( NBTSession,    SMBSession_Setup_AndX_Response, )
bind_layers( SMBNegociate_Protocol_Request_Header, SMBNegociate_Protocol_Request_Tail, )
bind_layers( SMBNegociate_Protocol_Request_Tail,   SMBNegociate_Protocol_Request_Tail, )

########NEW FILE########
__FILENAME__ = snmp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
SNMP (Simple Network Management Protocol).
"""

from scapy.asn1packet import *
from scapy.asn1fields import *
from scapy.layers.inet import UDP

##########
## SNMP ##
##########

######[ ASN1 class ]######

class ASN1_Class_SNMP(ASN1_Class_UNIVERSAL):
    name="SNMP"
    PDU_GET = 0xa0
    PDU_NEXT = 0xa1
    PDU_RESPONSE = 0xa2
    PDU_SET = 0xa3
    PDU_TRAPv1 = 0xa4
    PDU_BULK = 0xa5
    PDU_INFORM = 0xa6
    PDU_TRAPv2 = 0xa7


class ASN1_SNMP_PDU_GET(ASN1_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_GET

class ASN1_SNMP_PDU_NEXT(ASN1_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_NEXT

class ASN1_SNMP_PDU_RESPONSE(ASN1_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_RESPONSE

class ASN1_SNMP_PDU_SET(ASN1_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_SET

class ASN1_SNMP_PDU_TRAPv1(ASN1_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_TRAPv1

class ASN1_SNMP_PDU_BULK(ASN1_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_BULK

class ASN1_SNMP_PDU_INFORM(ASN1_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_INFORM

class ASN1_SNMP_PDU_TRAPv2(ASN1_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_TRAPv2


######[ BER codecs ]#######

class BERcodec_SNMP_PDU_GET(BERcodec_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_GET

class BERcodec_SNMP_PDU_NEXT(BERcodec_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_NEXT

class BERcodec_SNMP_PDU_RESPONSE(BERcodec_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_RESPONSE

class BERcodec_SNMP_PDU_SET(BERcodec_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_SET

class BERcodec_SNMP_PDU_TRAPv1(BERcodec_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_TRAPv1

class BERcodec_SNMP_PDU_BULK(BERcodec_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_BULK

class BERcodec_SNMP_PDU_INFORM(BERcodec_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_INFORM

class BERcodec_SNMP_PDU_TRAPv2(BERcodec_SEQUENCE):
    tag = ASN1_Class_SNMP.PDU_TRAPv2



######[ ASN1 fields ]######

class ASN1F_SNMP_PDU_GET(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_SNMP.PDU_GET

class ASN1F_SNMP_PDU_NEXT(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_SNMP.PDU_NEXT

class ASN1F_SNMP_PDU_RESPONSE(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_SNMP.PDU_RESPONSE

class ASN1F_SNMP_PDU_SET(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_SNMP.PDU_SET

class ASN1F_SNMP_PDU_TRAPv1(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_SNMP.PDU_TRAPv1

class ASN1F_SNMP_PDU_BULK(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_SNMP.PDU_BULK

class ASN1F_SNMP_PDU_INFORM(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_SNMP.PDU_INFORM

class ASN1F_SNMP_PDU_TRAPv2(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_SNMP.PDU_TRAPv2



######[ SNMP Packet ]######

SNMP_error = { 0: "no_error",
               1: "too_big",
               2: "no_such_name",
               3: "bad_value",
               4: "read_only",
               5: "generic_error",
               6: "no_access",
               7: "wrong_type",
               8: "wrong_length",
               9: "wrong_encoding",
              10: "wrong_value",
              11: "no_creation",
              12: "inconsistent_value",
              13: "ressource_unavailable",
              14: "commit_failed",
              15: "undo_failed",
              16: "authorization_error",
              17: "not_writable",
              18: "inconsistent_name",
               }

SNMP_trap_types = { 0: "cold_start",
                    1: "warm_start",
                    2: "link_down",
                    3: "link_up",
                    4: "auth_failure",
                    5: "egp_neigh_loss",
                    6: "enterprise_specific",
                    }

class SNMPvarbind(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SEQUENCE( ASN1F_OID("oid","1.3"),
                                ASN1F_field("value",ASN1_NULL(0))
                                )


class SNMPget(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SNMP_PDU_GET( ASN1F_INTEGER("id",0),
                                    ASN1F_enum_INTEGER("error",0, SNMP_error),
                                    ASN1F_INTEGER("error_index",0),
                                    ASN1F_SEQUENCE_OF("varbindlist", [], SNMPvarbind)
                                    )

class SNMPnext(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SNMP_PDU_NEXT( ASN1F_INTEGER("id",0),
                                     ASN1F_enum_INTEGER("error",0, SNMP_error),
                                     ASN1F_INTEGER("error_index",0),
                                     ASN1F_SEQUENCE_OF("varbindlist", [], SNMPvarbind)
                                     )

class SNMPresponse(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SNMP_PDU_RESPONSE( ASN1F_INTEGER("id",0),
                                         ASN1F_enum_INTEGER("error",0, SNMP_error),
                                         ASN1F_INTEGER("error_index",0),
                                         ASN1F_SEQUENCE_OF("varbindlist", [], SNMPvarbind)
                                         )

class SNMPset(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SNMP_PDU_SET( ASN1F_INTEGER("id",0),
                                    ASN1F_enum_INTEGER("error",0, SNMP_error),
                                    ASN1F_INTEGER("error_index",0),
                                    ASN1F_SEQUENCE_OF("varbindlist", [], SNMPvarbind)
                                    )
    
class SNMPtrapv1(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SNMP_PDU_TRAPv1( ASN1F_OID("enterprise", "1.3"),
                                       ASN1F_IPADDRESS("agent_addr","0.0.0.0"),
                                       ASN1F_enum_INTEGER("generic_trap", 0, SNMP_trap_types),
                                       ASN1F_INTEGER("specific_trap", 0),
                                       ASN1F_TIME_TICKS("time_stamp", IntAutoTime()),
                                       ASN1F_SEQUENCE_OF("varbindlist", [], SNMPvarbind)
                                       )

class SNMPbulk(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SNMP_PDU_BULK( ASN1F_INTEGER("id",0),
                                     ASN1F_INTEGER("non_repeaters",0),
                                     ASN1F_INTEGER("max_repetitions",0),
                                     ASN1F_SEQUENCE_OF("varbindlist", [], SNMPvarbind)
                                     )
    
class SNMPinform(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SNMP_PDU_INFORM( ASN1F_INTEGER("id",0),
                                       ASN1F_enum_INTEGER("error",0, SNMP_error),
                                       ASN1F_INTEGER("error_index",0),
                                       ASN1F_SEQUENCE_OF("varbindlist", [], SNMPvarbind)
                                       )
    
class SNMPtrapv2(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SNMP_PDU_TRAPv2( ASN1F_INTEGER("id",0),
                                       ASN1F_enum_INTEGER("error",0, SNMP_error),
                                       ASN1F_INTEGER("error_index",0),
                                       ASN1F_SEQUENCE_OF("varbindlist", [], SNMPvarbind)
                                       )
    

class SNMP(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SEQUENCE(
        ASN1F_enum_INTEGER("version", 1, {0:"v1", 1:"v2c", 2:"v2", 3:"v3"}),
        ASN1F_STRING("community","public"),
        ASN1F_CHOICE("PDU", SNMPget(),
                     SNMPget, SNMPnext, SNMPresponse, SNMPset,
                     SNMPtrapv1, SNMPbulk, SNMPinform, SNMPtrapv2)
        )
    def answers(self, other):
        return ( isinstance(self.PDU, SNMPresponse)    and
                 ( isinstance(other.PDU, SNMPget) or
                   isinstance(other.PDU, SNMPnext) or
                   isinstance(other.PDU, SNMPset)    ) and
                 self.PDU.id == other.PDU.id )

bind_layers( UDP,           SNMP,          sport=161)
bind_layers( UDP,           SNMP,          dport=161)
bind_layers( UDP,           SNMP,          sport=162) 
bind_layers( UDP,           SNMP,          dport=162) 

def snmpwalk(dst, oid="1", community="public"):
    try:
        while 1:
            r = sr1(IP(dst=dst)/UDP(sport=RandShort())/SNMP(community=community, PDU=SNMPnext(varbindlist=[SNMPvarbind(oid=oid)])),timeout=2, chainCC=1, verbose=0, retry=2)
            if ICMP in r:
                print repr(r)
                break
            if r is None:
                print "No answers"
                break
            print "%-40s: %r" % (r[SNMPvarbind].oid.val,r[SNMPvarbind].value)
            oid = r[SNMPvarbind].oid
            
    except KeyboardInterrupt:
        pass


########NEW FILE########
__FILENAME__ = tftp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
TFTP (Trivial File Transfer Protocol).
"""

import os,random
from scapy.packet import *
from scapy.fields import *
from scapy.automaton import *
from scapy.layers.inet import UDP



TFTP_operations = { 1:"RRQ",2:"WRQ",3:"DATA",4:"ACK",5:"ERROR",6:"OACK" }


class TFTP(Packet):
    name = "TFTP opcode"
    fields_desc = [ ShortEnumField("op", 1, TFTP_operations), ]
    


class TFTP_RRQ(Packet):
    name = "TFTP Read Request"
    fields_desc = [ StrNullField("filename", ""),
                    StrNullField("mode", "octet") ]
    def answers(self, other):
        return 0
    def mysummary(self):
        return self.sprintf("RRQ %filename%"),[UDP]
        

class TFTP_WRQ(Packet):
    name = "TFTP Write Request"
    fields_desc = [ StrNullField("filename", ""),
                    StrNullField("mode", "octet") ]
    def answers(self, other):
        return 0
    def mysummary(self):
        return self.sprintf("WRQ %filename%"),[UDP]

class TFTP_DATA(Packet):
    name = "TFTP Data"
    fields_desc = [ ShortField("block", 0) ]
    def answers(self, other):
        return  self.block == 1 and isinstance(other, TFTP_RRQ)
    def mysummary(self):
        return self.sprintf("DATA %block%"),[UDP]

class TFTP_Option(Packet):
    fields_desc = [ StrNullField("oname",""),
                    StrNullField("value","") ]
    def extract_padding(self, pkt):
        return "",pkt

class TFTP_Options(Packet):
    fields_desc = [ PacketListField("options", [], TFTP_Option, length_from=lambda x:None) ]

    
class TFTP_ACK(Packet):
    name = "TFTP Ack"
    fields_desc = [ ShortField("block", 0) ]
    def answers(self, other):
        if isinstance(other, TFTP_DATA):
            return self.block == other.block
        elif isinstance(other, TFTP_RRQ) or isinstance(other, TFTP_WRQ) or isinstance(other, TFTP_OACK):
            return self.block == 0
        return 0
    def mysummary(self):
        return self.sprintf("ACK %block%"),[UDP]

TFTP_Error_Codes = {  0: "Not defined",
                      1: "File not found",
                      2: "Access violation",
                      3: "Disk full or allocation exceeded",
                      4: "Illegal TFTP operation",
                      5: "Unknown transfer ID",
                      6: "File already exists",
                      7: "No such user",
                      8: "Terminate transfer due to option negotiation",
                      }
    
class TFTP_ERROR(Packet):
    name = "TFTP Error"
    fields_desc = [ ShortEnumField("errorcode", 0, TFTP_Error_Codes),
                    StrNullField("errormsg", "")]
    def answers(self, other):
        return (isinstance(other, TFTP_DATA) or
                isinstance(other, TFTP_RRQ) or
                isinstance(other, TFTP_WRQ) or 
                isinstance(other, TFTP_ACK))
    def mysummary(self):
        return self.sprintf("ERROR %errorcode%: %errormsg%"),[UDP]


class TFTP_OACK(Packet):
    name = "TFTP Option Ack"
    fields_desc = [  ]
    def answers(self, other):
        return isinstance(other, TFTP_WRQ) or isinstance(other, TFTP_RRQ)


bind_layers(UDP, TFTP, dport=69)
bind_layers(TFTP, TFTP_RRQ, op=1)
bind_layers(TFTP, TFTP_WRQ, op=2)
bind_layers(TFTP, TFTP_DATA, op=3)
bind_layers(TFTP, TFTP_ACK, op=4)
bind_layers(TFTP, TFTP_ERROR, op=5)
bind_layers(TFTP, TFTP_OACK, op=6)
bind_layers(TFTP_RRQ, TFTP_Options)
bind_layers(TFTP_WRQ, TFTP_Options)
bind_layers(TFTP_OACK, TFTP_Options)
    

class TFTP_read(Automaton):
    def parse_args(self, filename, server, sport = None, port=69, **kargs):
        Automaton.parse_args(self, **kargs)
        self.filename = filename
        self.server = server
        self.port = port
        self.sport = sport


    def master_filter(self, pkt):
        return ( IP in pkt and pkt[IP].src == self.server and UDP in pkt
                 and pkt[UDP].dport == self.my_tid
                 and (self.server_tid is None or pkt[UDP].sport == self.server_tid) )
        
    # BEGIN
    @ATMT.state(initial=1)
    def BEGIN(self):
        self.blocksize=512
        self.my_tid = self.sport or RandShort()._fix()
        bind_bottom_up(UDP, TFTP, dport=self.my_tid)
        self.server_tid = None
        self.res = ""

        self.l3 = IP(dst=self.server)/UDP(sport=self.my_tid, dport=self.port)/TFTP()
        self.last_packet = self.l3/TFTP_RRQ(filename=self.filename, mode="octet")
        self.send(self.last_packet)
        self.awaiting=1
        
        raise self.WAITING()
        
    # WAITING
    @ATMT.state()
    def WAITING(self):
        pass


    @ATMT.receive_condition(WAITING)
    def receive_data(self, pkt):
        if TFTP_DATA in pkt and pkt[TFTP_DATA].block == self.awaiting:
            if self.server_tid is None:
                self.server_tid = pkt[UDP].sport
                self.l3[UDP].dport = self.server_tid
            raise self.RECEIVING(pkt)

    @ATMT.receive_condition(WAITING, prio=1)
    def receive_error(self, pkt):
        if TFTP_ERROR in pkt:
            raise self.ERROR(pkt)
    
        
    @ATMT.timeout(WAITING, 3)
    def timeout_waiting(self):
        raise self.WAITING()
    @ATMT.action(timeout_waiting)
    def retransmit_last_packet(self):
        self.send(self.last_packet)

    @ATMT.action(receive_data)
#    @ATMT.action(receive_error)
    def send_ack(self):
        self.last_packet = self.l3 / TFTP_ACK(block = self.awaiting)
        self.send(self.last_packet)
    

    # RECEIVED
    @ATMT.state()
    def RECEIVING(self, pkt):
        if Raw in pkt:
            recvd = pkt[Raw].load
        else:
            recvd = ""
        self.res += recvd
        self.awaiting += 1
        if len(recvd) == self.blocksize:
            raise self.WAITING()
        raise self.END()

    # ERROR
    @ATMT.state(error=1)
    def ERROR(self,pkt):
        split_bottom_up(UDP, TFTP, dport=self.my_tid)
        return pkt[TFTP_ERROR].summary()
    
    #END
    @ATMT.state(final=1)
    def END(self):
        split_bottom_up(UDP, TFTP, dport=self.my_tid)
        return self.res




class TFTP_write(Automaton):
    def parse_args(self, filename, data, server, sport=None, port=69,**kargs):
        Automaton.parse_args(self, **kargs)
        self.filename = filename
        self.server = server
        self.port = port
        self.sport = sport
        self.blocksize = 512
        self.origdata = data

    def master_filter(self, pkt):
        return ( IP in pkt and pkt[IP].src == self.server and UDP in pkt
                 and pkt[UDP].dport == self.my_tid
                 and (self.server_tid is None or pkt[UDP].sport == self.server_tid) )
        

    # BEGIN
    @ATMT.state(initial=1)
    def BEGIN(self):
        self.data = [ self.origdata[i*self.blocksize:(i+1)*self.blocksize]
                      for i in range( len(self.origdata)/self.blocksize+1) ] 
        self.my_tid = self.sport or RandShort()._fix()
        bind_bottom_up(UDP, TFTP, dport=self.my_tid)
        self.server_tid = None
        
        self.l3 = IP(dst=self.server)/UDP(sport=self.my_tid, dport=self.port)/TFTP()
        self.last_packet = self.l3/TFTP_WRQ(filename=self.filename, mode="octet")
        self.send(self.last_packet)
        self.res = ""
        self.awaiting=0

        raise self.WAITING_ACK()
        
    # WAITING_ACK
    @ATMT.state()
    def WAITING_ACK(self):
        pass

    @ATMT.receive_condition(WAITING_ACK)    
    def received_ack(self,pkt):
        if TFTP_ACK in pkt and pkt[TFTP_ACK].block == self.awaiting:
            if self.server_tid is None:
                self.server_tid = pkt[UDP].sport
                self.l3[UDP].dport = self.server_tid
            raise self.SEND_DATA()

    @ATMT.receive_condition(WAITING_ACK)
    def received_error(self, pkt):
        if TFTP_ERROR in pkt:
            raise self.ERROR(pkt)

    @ATMT.timeout(WAITING_ACK, 3)
    def timeout_waiting(self):
        raise self.WAITING_ACK()
    @ATMT.action(timeout_waiting)
    def retransmit_last_packet(self):
        self.send(self.last_packet)
    
    # SEND_DATA
    @ATMT.state()
    def SEND_DATA(self):
        self.awaiting += 1
        self.last_packet = self.l3/TFTP_DATA(block=self.awaiting)/self.data.pop(0)
        self.send(self.last_packet)
        if self.data:
            raise self.WAITING_ACK()
        raise self.END()
    

    # ERROR
    @ATMT.state(error=1)
    def ERROR(self,pkt):
        split_bottom_up(UDP, TFTP, dport=self.my_tid)
        return pkt[TFTP_ERROR].summary()

    # END
    @ATMT.state(final=1)
    def END(self):
        split_bottom_up(UDP, TFTP, dport=self.my_tid)


class TFTP_WRQ_server(Automaton):

    def parse_args(self, ip=None, sport=None, *args, **kargs):
        Automaton.parse_args(self, *args, **kargs)
        self.ip = ip
        self.sport = sport

    def master_filter(self, pkt):
        return TFTP in pkt and (not self.ip or pkt[IP].dst == self.ip)

    @ATMT.state(initial=1)
    def BEGIN(self):
        self.blksize=512
        self.blk=1
        self.filedata=""
        self.my_tid = self.sport or random.randint(10000,65500)
        bind_bottom_up(UDP, TFTP, dport=self.my_tid)

    @ATMT.receive_condition(BEGIN)
    def receive_WRQ(self,pkt):
        if TFTP_WRQ in pkt:
            raise self.WAIT_DATA().action_parameters(pkt)
        
    @ATMT.action(receive_WRQ)
    def ack_WRQ(self, pkt):
        ip = pkt[IP]
        self.ip = ip.dst
        self.dst = ip.src
        self.filename = pkt[TFTP_WRQ].filename
        options = pkt[TFTP_Options]
        self.l3 = IP(src=ip.dst, dst=ip.src)/UDP(sport=self.my_tid, dport=pkt.sport)/TFTP()
        if options is None:
            self.last_packet = self.l3/TFTP_ACK(block=0)
            self.send(self.last_packet)
        else:
            opt = [x for x in options.options if x.oname.upper() == "BLKSIZE"]
            if opt:
                self.blksize = int(opt[0].value)
                self.debug(2,"Negotiated new blksize at %i" % self.blksize)
            self.last_packet = self.l3/TFTP_OACK()/TFTP_Options(options=opt)
            self.send(self.last_packet)

    @ATMT.state()
    def WAIT_DATA(self):
        pass

    @ATMT.timeout(WAIT_DATA, 1)
    def resend_ack(self):
        self.send(self.last_packet)
        raise self.WAIT_DATA()
        
    @ATMT.receive_condition(WAIT_DATA)
    def receive_data(self, pkt):
        if TFTP_DATA in pkt:
            data = pkt[TFTP_DATA]
            if data.block == self.blk:
                raise self.DATA(data)

    @ATMT.action(receive_data)
    def ack_data(self):
        self.last_packet = self.l3/TFTP_ACK(block = self.blk)
        self.send(self.last_packet)

    @ATMT.state()
    def DATA(self, data):
        self.filedata += data.load
        if len(data.load) < self.blksize:
            raise self.END()
        self.blk += 1
        raise self.WAIT_DATA()

    @ATMT.state(final=1)
    def END(self):
        return self.filename,self.filedata
        split_bottom_up(UDP, TFTP, dport=self.my_tid)
        

class TFTP_RRQ_server(Automaton):
    def parse_args(self, store=None, joker=None, dir=None, ip=None, sport=None, serve_one=False, **kargs):
        Automaton.parse_args(self,**kargs)
        if store is None:
            store = {}
        if dir is not None:
            self.dir = os.path.join(os.path.abspath(dir),"")
        else:
            self.dir = None
        self.store = store
        self.joker = joker
        self.ip = ip
        self.sport = sport
        self.serve_one = serve_one
        self.my_tid = self.sport or random.randint(10000,65500)
        bind_bottom_up(UDP, TFTP, dport=self.my_tid)
        
    def master_filter(self, pkt):
        return TFTP in pkt and (not self.ip or pkt[IP].dst == self.ip)

    @ATMT.state(initial=1)
    def WAIT_RRQ(self):
        self.blksize=512
        self.blk=0

    @ATMT.receive_condition(WAIT_RRQ)
    def receive_rrq(self, pkt):
        if TFTP_RRQ in pkt:
            raise self.RECEIVED_RRQ(pkt)


    @ATMT.state()
    def RECEIVED_RRQ(self, pkt):
        ip = pkt[IP]
        options = pkt[TFTP_Options]
        self.l3 = IP(src=ip.dst, dst=ip.src)/UDP(sport=self.my_tid, dport=ip.sport)/TFTP()
        self.filename = pkt[TFTP_RRQ].filename
        self.blk=1
        self.data = None
        if self.filename in self.store:
            self.data = self.store[self.filename]
        elif self.dir is not None:
            fn = os.path.abspath(os.path.join(self.dir, self.filename))
            if fn.startswith(self.dir): # Check we're still in the server's directory
                try:
                    self.data=open(fn).read()
                except IOError:
                    pass
        if self.data is None:
            self.data = self.joker

        if options:
            opt = [x for x in options.options if x.oname.upper() == "BLKSIZE"]
            if opt:
                self.blksize = int(opt[0].value)
                self.debug(2,"Negotiated new blksize at %i" % self.blksize)
            self.last_packet = self.l3/TFTP_OACK()/TFTP_Options(options=opt)
            self.send(self.last_packet)
                

            

    @ATMT.condition(RECEIVED_RRQ)
    def file_in_store(self):
        if self.data is not None:
            self.blknb = len(self.data)/self.blksize+1
            raise self.SEND_FILE()

    @ATMT.condition(RECEIVED_RRQ)
    def file_not_found(self):
        if self.data is None:
            raise self.WAIT_RRQ()
    @ATMT.action(file_not_found)
    def send_error(self):
        self.send(self.l3/TFTP_ERROR(errorcode=1, errormsg=TFTP_Error_Codes[1]))

    @ATMT.state()
    def SEND_FILE(self):
        self.send(self.l3/TFTP_DATA(block=self.blk)/self.data[(self.blk-1)*self.blksize:self.blk*self.blksize])
        
    @ATMT.timeout(SEND_FILE, 3)
    def timeout_waiting_ack(self):
        raise self.SEND_FILE()
            
    @ATMT.receive_condition(SEND_FILE)
    def received_ack(self, pkt):
        if TFTP_ACK in pkt and pkt[TFTP_ACK].block == self.blk:
            raise self.RECEIVED_ACK()
    @ATMT.state()
    def RECEIVED_ACK(self):
        self.blk += 1

    @ATMT.condition(RECEIVED_ACK)
    def no_more_data(self):
        if self.blk > self.blknb:
            if self.serve_one:
                raise self.END()
            raise self.WAIT_RRQ()
    @ATMT.condition(RECEIVED_ACK, prio=2)
    def data_remaining(self):
        raise self.SEND_FILE()

    @ATMT.state(final=1)
    def END(self):
        split_bottom_up(UDP, TFTP, dport=self.my_tid)
    

        


########NEW FILE########
__FILENAME__ = vrrp
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## Copyright (C) 6WIND <olivier.matz@6wind.com>
## This program is published under a GPLv2 license

"""
VRRP (Virtual Router Redundancy Protocol).
"""

from scapy.packet import *
from scapy.fields import *
from scapy.layers.inet import IP

IPPROTO_VRRP=112

# RFC 3768 - Virtual Router Redundancy Protocol (VRRP)
class VRRP(Packet):
    fields_desc = [
        BitField("version" , 2, 4),
        BitField("type" , 1, 4),
        ByteField("vrid", 1),
        ByteField("priority", 100),
        FieldLenField("ipcount", None, count_of="addrlist", fmt="B"),
        ByteField("authtype", 0),
        ByteField("adv", 1),
        XShortField("chksum", None),
        FieldListField("addrlist", [], IPField("", "0.0.0.0"),
                       count_from = lambda pkt: pkt.ipcount),
        IntField("auth1", 0),
        IntField("auth2", 0) ]

    def post_build(self, p, pay):
        if self.chksum is None:
            ck = checksum(p)
            p = p[:6]+chr(ck>>8)+chr(ck&0xff)+p[8:]
        return p

bind_layers( IP,            VRRP,          proto=IPPROTO_VRRP)

########NEW FILE########
__FILENAME__ = x509
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
X.509 certificates.
"""

from scapy.asn1packet import *
from scapy.asn1fields import *

##########
## X509 ##
##########

######[ ASN1 class ]######

class ASN1_Class_X509(ASN1_Class_UNIVERSAL):
    name="X509"
    CONT0 = 0xa0
    CONT1 = 0xa1
    CONT2 = 0xa2
    CONT3 = 0xa3

class ASN1_X509_CONT0(ASN1_SEQUENCE):
    tag = ASN1_Class_X509.CONT0

class ASN1_X509_CONT1(ASN1_SEQUENCE):
    tag = ASN1_Class_X509.CONT1

class ASN1_X509_CONT2(ASN1_SEQUENCE):
    tag = ASN1_Class_X509.CONT2

class ASN1_X509_CONT3(ASN1_SEQUENCE):
    tag = ASN1_Class_X509.CONT3

######[ BER codecs ]#######

class BERcodec_X509_CONT0(BERcodec_SEQUENCE):
    tag = ASN1_Class_X509.CONT0

class BERcodec_X509_CONT1(BERcodec_SEQUENCE):
    tag = ASN1_Class_X509.CONT1
    
class BERcodec_X509_CONT2(BERcodec_SEQUENCE):
    tag = ASN1_Class_X509.CONT2
    
class BERcodec_X509_CONT3(BERcodec_SEQUENCE):
    tag = ASN1_Class_X509.CONT3

######[ ASN1 fields ]######

class ASN1F_X509_CONT0(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_X509.CONT0
    
class ASN1F_X509_CONT1(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_X509.CONT1
    
class ASN1F_X509_CONT2(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_X509.CONT2
    
class ASN1F_X509_CONT3(ASN1F_SEQUENCE):
    ASN1_tag = ASN1_Class_X509.CONT3

######[ X509 packets ]######

class X509RDN(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SET(
                  ASN1F_SEQUENCE( ASN1F_OID("oid","2.5.4.6"),
                                  ASN1F_PRINTABLE_STRING("value","")
                                  )
                  )

class X509v3Ext(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_field("val",ASN1_NULL(0))
    

class X509Cert(ASN1_Packet):
    ASN1_codec = ASN1_Codecs.BER
    ASN1_root = ASN1F_SEQUENCE(
        ASN1F_SEQUENCE(
            ASN1F_optionnal(ASN1F_X509_CONT0(ASN1F_INTEGER("version",3))),
            ASN1F_INTEGER("sn",1),
            ASN1F_SEQUENCE(ASN1F_OID("sign_algo","1.2.840.113549.1.1.5"),
                           ASN1F_field("sa_value",ASN1_NULL(0))),
            ASN1F_SEQUENCE_OF("issuer",[],X509RDN),
            ASN1F_SEQUENCE(ASN1F_UTC_TIME("not_before",ZuluTime(-600)),  # ten minutes ago
                           ASN1F_UTC_TIME("not_after",ZuluTime(+86400))), # for 24h
            ASN1F_SEQUENCE_OF("subject",[],X509RDN),
            ASN1F_SEQUENCE(
                ASN1F_SEQUENCE(ASN1F_OID("pubkey_algo","1.2.840.113549.1.1.1"),
                               ASN1F_field("pk_value",ASN1_NULL(0))),
                ASN1F_BIT_STRING("pubkey","")
                ),
            ASN1F_optionnal(ASN1F_X509_CONT3(ASN1F_SEQUENCE_OF("x509v3ext",[],X509v3Ext))),
            
        ),
        ASN1F_SEQUENCE(ASN1F_OID("sign_algo2","1.2.840.113549.1.1.5"),
                       ASN1F_field("sa2_value",ASN1_NULL(0))),
        ASN1F_BIT_STRING("signature","")
        )





########NEW FILE########
__FILENAME__ = main
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Main module for interactive startup.
"""

from __future__ import generators
import os,sys
import __builtin__
from error import *
import utils
    

def _probe_config_file(cf):
    cf_path = os.path.join(os.path.expanduser("~"), cf)
    try:
        os.stat(cf_path)
    except OSError:
        return None
    else:
        return cf_path

def _read_config_file(cf):
    log_loading.debug("Loading config file [%s]" % cf)
    try:
        execfile(cf)
    except IOError,e:
        log_loading.warning("Cannot read config file [%s] [%s]" % (cf,e))
    except Exception,e:
        log_loading.exception("Error during evaluation of config file [%s]" % cf)
        

DEFAULT_PRESTART_FILE = _probe_config_file(".scapy_prestart.py")
DEFAULT_STARTUP_FILE = _probe_config_file(".scapy_startup.py")

def _usage():
    print """Usage: scapy.py [-s sessionfile] [-c new_startup_file] [-p new_prestart_file] [-C] [-P]
    -C: do not read startup file
    -P: do not read pre-startup file"""
    sys.exit(0)


from config import conf
from themes import DefaultTheme


######################
## Extension system ##
######################


def _load(module):
    try:
        mod = __import__(module,globals(),locals(),".")
        __builtin__.__dict__.update(mod.__dict__)
    except Exception,e:
        log_interactive.error(e)
        
def load_module(name):
    _load("scapy.modules."+name)

def load_layer(name):
    _load("scapy.layers."+name)

    

##############################
## Session saving/restoring ##
##############################


def save_session(fname=None, session=None, pickleProto=-1):
    if fname is None:
        fname = conf.session
        if not fname:
            conf.session = fname = utils.get_temp_file(keep=True)
            log_interactive.info("Use [%s] as session file" % fname)
    if session is None:
        session = __builtin__.__dict__["scapy_session"]

    to_be_saved = session.copy()
        
    if to_be_saved.has_key("__builtins__"):
        del(to_be_saved["__builtins__"])

    for k in to_be_saved.keys():
        if type(to_be_saved[k]) in [types.TypeType, types.ClassType, types.ModuleType]:
             log_interactive.error("[%s] (%s) can't be saved." % (k, type(to_be_saved[k])))
             del(to_be_saved[k])

    try:
        os.rename(fname, fname+".bak")
    except OSError:
        pass
    f=gzip.open(fname,"wb")
    cPickle.dump(to_be_saved, f, pickleProto)
    f.close()

def load_session(fname=None):
    if fname is None:
        fname = conf.session
    try:
        s = cPickle.load(gzip.open(fname,"rb"))
    except IOError:
        s = cPickle.load(open(fname,"rb"))
    scapy_session = __builtin__.__dict__["scapy_session"]
    scapy_session.clear()
    scapy_session.update(s)

def update_session(fname=None):
    if fname is None:
        fname = conf.session
    try:
        s = cPickle.load(gzip.open(fname,"rb"))
    except IOError:
        s = cPickle.load(open(fname,"rb"))
    scapy_session = __builtin__.__dict__["scapy_session"]
    scapy_session.update(s)


################
##### Main #####
################

def scapy_delete_temp_files():
    for f in conf.temp_files:
        try:
            os.unlink(f)
        except:
            pass

def scapy_write_history_file(readline):
    if conf.histfile:
        try:
            readline.write_history_file(conf.histfile)
        except IOError,e:
            try:
                warning("Could not write history to [%s]\n\t (%s)" % (conf.histfile,e))
                tmp = utils.get_temp_file(keep=True)
                readline.write_history_file(tmp)
                warning("Wrote history to [%s]" % tmp)
            except:
                warning("Cound not write history to [%s]. Discarded" % tmp)


def interact(mydict=None,argv=None,mybanner=None,loglevel=20):
    global session
    import code,sys,cPickle,os,getopt,re
    from config import conf
    conf.interactive = True
    if loglevel is not None:
        conf.logLevel=loglevel

    the_banner = "Welcome to Scapy (%s)"
    if mybanner is not None:
        the_banner += "\n"
        the_banner += mybanner

    if argv is None:
        argv = sys.argv

    import atexit
    try:
        import rlcompleter,readline
    except ImportError:
        log_loading.info("Can't load Python libreadline or completer")
        READLINE=0
    else:
        READLINE=1
        class ScapyCompleter(rlcompleter.Completer):
            def global_matches(self, text):
                matches = []
                n = len(text)
                for lst in [dir(__builtin__), session.keys()]:
                    for word in lst:
                        if word[:n] == text and word != "__builtins__":
                            matches.append(word)
                return matches
        
    
            def attr_matches(self, text):
                m = re.match(r"(\w+(\.\w+)*)\.(\w*)", text)
                if not m:
                    return
                expr, attr = m.group(1, 3)
                try:
                    object = eval(expr)
                except:
                    object = eval(expr, session)
                if isinstance(object, Packet) or isinstance(object, Packet_metaclass):
                    words = filter(lambda x: x[0]!="_",dir(object))
                    words += [x.name for x in object.fields_desc]
                else:
                    words = dir(object)
                    if hasattr( object,"__class__" ):
                        words = words + rlcompleter.get_class_members(object.__class__)
                matches = []
                n = len(attr)
                for word in words:
                    if word[:n] == attr and word != "__builtins__":
                        matches.append("%s.%s" % (expr, word))
                return matches
    
        readline.set_completer(ScapyCompleter().complete)
        readline.parse_and_bind("C-o: operate-and-get-next")
        readline.parse_and_bind("tab: complete")
    
    
    session=None
    session_name=""
    STARTUP_FILE = DEFAULT_STARTUP_FILE
    PRESTART_FILE = DEFAULT_PRESTART_FILE


    iface = None
    try:
        opts=getopt.getopt(argv[1:], "hs:Cc:Pp:d")
        for opt, parm in opts[0]:
            if opt == "-h":
                _usage()
            elif opt == "-s":
                session_name = parm
            elif opt == "-c":
                STARTUP_FILE = parm
            elif opt == "-C":
                STARTUP_FILE = None
            elif opt == "-p":
                PRESTART_FILE = parm
            elif opt == "-P":
                PRESTART_FILE = None
            elif opt == "-d":
                conf.logLevel = max(1,conf.logLevel-10)
        
        if len(opts[1]) > 0:
            raise getopt.GetoptError("Too many parameters : [%s]" % " ".join(opts[1]))


    except getopt.GetoptError, msg:
        log_loading.error(msg)
        sys.exit(1)

    if PRESTART_FILE:
        _read_config_file(PRESTART_FILE)

    scapy_builtins = __import__("all",globals(),locals(),".").__dict__
    __builtin__.__dict__.update(scapy_builtins)
    globkeys = scapy_builtins.keys()
    globkeys.append("scapy_session")
    scapy_builtins=None # XXX replace with "with" statement
    if mydict is not None:
        __builtin__.__dict__.update(mydict)
        globkeys += mydict.keys()
    

    conf.color_theme = DefaultTheme()
    if STARTUP_FILE:
        _read_config_file(STARTUP_FILE)
        
    if session_name:
        try:
            os.stat(session_name)
        except OSError:
            log_loading.info("New session [%s]" % session_name)
        else:
            try:
                try:
                    session = cPickle.load(gzip.open(session_name,"rb"))
                except IOError:
                    session = cPickle.load(open(session_name,"rb"))
                log_loading.info("Using session [%s]" % session_name)
            except EOFError:
                log_loading.error("Error opening session [%s]" % session_name)
            except AttributeError:
                log_loading.error("Error opening session [%s]. Attribute missing" %  session_name)

        if session:
            if "conf" in session:
                conf.configure(session["conf"])
                session["conf"] = conf
        else:
            conf.session = session_name
            session={"conf":conf}
            
    else:
        session={"conf": conf}

    __builtin__.__dict__["scapy_session"] = session


    if READLINE:
        if conf.histfile:
            try:
                readline.read_history_file(conf.histfile)
            except IOError:
                pass
        atexit.register(scapy_write_history_file,readline)
    
    atexit.register(scapy_delete_temp_files)
    
    IPYTHON=False
    if conf.interactive_shell.lower() == "ipython":
        try:
            import IPython
            IPYTHON=True
        except ImportError, e:
            log_loading.warning("IPython not available. Using standard Python shell instead.")
            IPYTHON=False
        
    if IPYTHON:
        banner = the_banner % (conf.version) + " using IPython %s" % IPython.__version__
        args = ['']  # IPython command line args (will be seen as sys.argv)
        ipshell = IPython.Shell.IPShellEmbed(args, banner = banner)
        ipshell(local_ns=session)
    else:
        code.interact(banner = the_banner % (conf.version),
                      local=session, readfunc=conf.readfunc)

    if conf.session:
        save_session(conf.session, session)


    for k in globkeys:
        try:
            del(__builtin__.__dict__[k])
        except:
            pass

if __name__ == "__main__":
    interact()

########NEW FILE########
__FILENAME__ = geoip
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
GeoIP: find out the geographical location of IP addresses
"""

from scapy.data import KnowledgeBase
from scapy.config import conf

conf.IPCountry_base = "GeoIPCountry4Scapy.gz"
conf.countryLoc_base = "countryLoc.csv"
conf.gnuplot_world = "world.dat"


##########################
## IP location database ##
##########################

class IPCountryKnowledgeBase(KnowledgeBase):
    """
How to generate the base :
db = []
for l in open("GeoIPCountryWhois.csv").readlines():
    s,e,c = l.split(",")[2:5]
    db.append((int(s[1:-1]),int(e[1:-1]),c[1:-1]))
cPickle.dump(gzip.open("xxx","w"),db)
"""
    def lazy_init(self):
        self.base = load_object(self.filename)


class CountryLocKnowledgeBase(KnowledgeBase):
    def lazy_init(self):
        f=open(self.filename)
        self.base = {}
        while 1:
            l = f.readline()
            if not l:
                break
            l = l.strip().split(",")
            if len(l) != 3:
                continue
            c,lat,long = l
            
            self.base[c] = (float(long),float(lat))
        f.close()
            
        

@conf.commands.register
def locate_ip(ip):
    """Get geographic coordinates from IP using geoip database"""
    ip=map(int,ip.split("."))
    ip = ip[3]+(ip[2]<<8L)+(ip[1]<<16L)+(ip[0]<<24L)

    cloc = country_loc_kdb.get_base()
    db = IP_country_kdb.get_base()

    d=0
    f=len(db)-1
    while (f-d) > 1:
        guess = (d+f)/2
        if ip > db[guess][0]:
            d = guess
        else:
            f = guess
    s,e,c = db[guess]
    if  s <= ip and ip <= e:
        return cloc.get(c,None)





conf.IP_country_kdb = IPCountryKnowledgeBase(conf.IPCountry_base)
conf.country_loc_kdb = CountryLocKnowledgeBase(conf.countryLoc_base)

########NEW FILE########
__FILENAME__ = nmap
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Clone of Nmap's first generation OS fingerprinting.
"""

import os

from scapy.data import KnowledgeBase
from scapy.config import conf
from scapy.arch import WINDOWS


if WINDOWS:
    conf.nmap_base=os.environ["ProgramFiles"] + "\\nmap\\nmap-os-fingerprints"
else:
    conf.nmap_base ="/usr/share/nmap/nmap-os-fingerprints"


######################
## nmap OS fp stuff ##
######################


class NmapKnowledgeBase(KnowledgeBase):
    def lazy_init(self):
        try:
            f=open(self.filename)
        except IOError:
            return

        self.base = []
        name = None
        try:
            for l in f:
                l = l.strip()
                if not l or l[0] == "#":
                    continue
                if l[:12] == "Fingerprint ":
                    if name is not None:
                        self.base.append((name,sig))
                    name = l[12:].strip()
                    sig={}
                    p = self.base
                    continue
                elif l[:6] == "Class ":
                    continue
                op = l.find("(")
                cl = l.find(")")
                if op < 0 or cl < 0:
                    warning("error reading nmap os fp base file")
                    continue
                test = l[:op]
                s = map(lambda x: x.split("="), l[op+1:cl].split("%"))
                si = {}
                for n,v in s:
                    si[n] = v
                sig[test]=si
            if name is not None:
                self.base.append((name,sig))
        except:
            self.base = None
            warning("Can't read nmap database [%s](new nmap version ?)" % self.filename)
        f.close()

nmap_kdb = NmapKnowledgeBase(conf.nmap_base)

def TCPflags2str(f):
    fl="FSRPAUEC"
    s=""
    for i in range(len(fl)):
        if f & 1:
            s = fl[i]+s
        f >>= 1
    return s

def nmap_tcppacket_sig(pkt):
    r = {}
    if pkt is not None:
#        r["Resp"] = "Y"
        r["DF"] = (pkt.flags & 2) and "Y" or "N"
        r["W"] = "%X" % pkt.window
        r["ACK"] = pkt.ack==2 and "S++" or pkt.ack==1 and "S" or "O"
        r["Flags"] = TCPflags2str(pkt.payload.flags)
        r["Ops"] = "".join(map(lambda x: x[0][0],pkt.payload.options))
    else:
        r["Resp"] = "N"
    return r


def nmap_udppacket_sig(S,T):
    r={}
    if T is None:
        r["Resp"] = "N"
    else:
        r["DF"] = (T.flags & 2) and "Y" or "N"
        r["TOS"] = "%X" % T.tos
        r["IPLEN"] = "%X" % T.len
        r["RIPTL"] = "%X" % T.payload.payload.len
        r["RID"] = S.id == T.payload.payload.id and "E" or "F"
        r["RIPCK"] = S.chksum == T.getlayer(IPerror).chksum and "E" or T.getlayer(IPerror).chksum == 0 and "0" or "F"
        r["UCK"] = S.payload.chksum == T.getlayer(UDPerror).chksum and "E" or T.getlayer(UDPerror).chksum ==0 and "0" or "F"
        r["ULEN"] = "%X" % T.getlayer(UDPerror).len
        r["DAT"] = T.getlayer(Raw) is None and "E" or S.getlayer(Raw).load == T.getlayer(Raw).load and "E" or "F"
    return r
    


def nmap_match_one_sig(seen, ref):
    c = 0
    for k in seen.keys():
        if ref.has_key(k):
            if seen[k] in ref[k].split("|"):
                c += 1
    if c == 0 and seen.get("Resp") == "N":
        return 0.7
    else:
        return 1.0*c/len(seen.keys())
        
        
def nmap_sig(target, oport=80, cport=81, ucport=1):
    res = {}

    tcpopt = [ ("WScale", 10),
               ("NOP",None),
               ("MSS", 256),
               ("Timestamp",(123,0)) ]
    tests = [ IP(dst=target, id=1)/TCP(seq=1, sport=5001, dport=oport, options=tcpopt, flags="CS"),
              IP(dst=target, id=1)/TCP(seq=1, sport=5002, dport=oport, options=tcpopt, flags=0),
              IP(dst=target, id=1)/TCP(seq=1, sport=5003, dport=oport, options=tcpopt, flags="SFUP"),
              IP(dst=target, id=1)/TCP(seq=1, sport=5004, dport=oport, options=tcpopt, flags="A"),
              IP(dst=target, id=1)/TCP(seq=1, sport=5005, dport=cport, options=tcpopt, flags="S"),
              IP(dst=target, id=1)/TCP(seq=1, sport=5006, dport=cport, options=tcpopt, flags="A"),
              IP(dst=target, id=1)/TCP(seq=1, sport=5007, dport=cport, options=tcpopt, flags="FPU"),
              IP(str(IP(dst=target)/UDP(sport=5008,dport=ucport)/(300*"i"))) ]

    ans, unans = sr(tests, timeout=2)
    ans += map(lambda x: (x,None), unans)

    for S,T in ans:
        if S.sport == 5008:
            res["PU"] = nmap_udppacket_sig(S,T)
        else:
            t = "T%i" % (S.sport-5000)
            if T is not None and T.haslayer(ICMP):
                warning("Test %s answered by an ICMP" % t)
                T=None
            res[t] = nmap_tcppacket_sig(T)

    return res

def nmap_probes2sig(tests):
    tests=tests.copy()
    res = {}
    if "PU" in tests:
        res["PU"] = nmap_udppacket_sig(*tests["PU"])
        del(tests["PU"])
    for k in tests:
        res[k] = nmap_tcppacket_sig(tests[k])
    return res
        

def nmap_search(sigs):
    guess = 0,[]
    for os,fp in nmap_kdb.get_base():
        c = 0.0
        for t in sigs.keys():
            if t in fp:
                c += nmap_match_one_sig(sigs[t], fp[t])
        c /= len(sigs.keys())
        if c > guess[0]:
            guess = c,[ os ]
        elif c == guess[0]:
            guess[1].append(os)
    return guess
    
    
@conf.commands.register
def nmap_fp(target, oport=80, cport=81):
    """nmap fingerprinting
nmap_fp(target, [oport=80,] [cport=81,]) -> list of best guesses with accuracy
"""
    sigs = nmap_sig(target, oport, cport)
    return nmap_search(sigs)
        

@conf.commands.register
def nmap_sig2txt(sig):
    torder = ["TSeq","T1","T2","T3","T4","T5","T6","T7","PU"]
    korder = ["Class", "gcd", "SI", "IPID", "TS",
              "Resp", "DF", "W", "ACK", "Flags", "Ops",
              "TOS", "IPLEN", "RIPTL", "RID", "RIPCK", "UCK", "ULEN", "DAT" ]
    txt=[]
    for i in sig.keys():
        if i not in torder:
            torder.append(i)
    for t in torder:
        sl = sig.get(t)
        if sl is None:
            continue
        s = []
        for k in korder:
            v = sl.get(k)
            if v is None:
                continue
            s.append("%s=%s"%(k,v))
        txt.append("%s(%s)" % (t, "%".join(s)))
    return "\n".join(txt)
            
        



########NEW FILE########
__FILENAME__ = p0f
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Clone of p0f passive OS fingerprinting
"""

from scapy.data import KnowledgeBase
from scapy.config import conf
from scapy.layers.inet import IP, TCP, TCPOptions
from scapy.packet import NoPayload

conf.p0f_base ="/etc/p0f/p0f.fp"
conf.p0fa_base ="/etc/p0f/p0fa.fp"
conf.p0fr_base ="/etc/p0f/p0fr.fp"
conf.p0fo_base ="/etc/p0f/p0fo.fp"


###############
## p0f stuff ##
###############

# File format (according to p0f.fp) :
#
# wwww:ttt:D:ss:OOO...:QQ:OS:Details
#
# wwww    - window size
# ttt     - initial TTL
# D       - don't fragment bit  (0=unset, 1=set) 
# ss      - overall SYN packet size
# OOO     - option value and order specification
# QQ      - quirks list
# OS      - OS genre
# details - OS description

class p0fKnowledgeBase(KnowledgeBase):
    def __init__(self, filename):
        KnowledgeBase.__init__(self, filename)
        #self.ttl_range=[255]
    def lazy_init(self):
        try:
            f=open(self.filename)
        except IOError:
            warning("Can't open base %s" % self.filename)
            return
        try:
            self.base = []
            for l in f:
                if l[0] in ["#","\n"]:
                    continue
                l = tuple(l.split(":"))
                if len(l) < 8:
                    continue
                def a2i(x):
                    if x.isdigit():
                        return int(x)
                    return x
                li = map(a2i, l[1:4])
                #if li[0] not in self.ttl_range:
                #    self.ttl_range.append(li[0])
                #    self.ttl_range.sort()
                self.base.append((l[0], li[0], li[1], li[2], l[4], l[5], l[6], l[7][:-1]))
        except:
            warning("Can't parse p0f database (new p0f version ?)")
            self.base = None
        f.close()

p0f_kdb = p0fKnowledgeBase(conf.p0f_base)
p0fa_kdb = p0fKnowledgeBase(conf.p0fa_base)
p0fr_kdb = p0fKnowledgeBase(conf.p0fr_base)
p0fo_kdb = p0fKnowledgeBase(conf.p0fo_base)

def p0f_selectdb(flags):
    # tested flags: S, R, A
    if flags & 0x16 == 0x2:
        # SYN
        return p0f_kdb
    elif flags & 0x16 == 0x12:
        # SYN/ACK
        return p0fa_kdb
    elif flags & 0x16 in [ 0x4, 0x14 ]:
        # RST RST/ACK
        return p0fr_kdb
    elif flags & 0x16 == 0x10:
        # ACK
        return p0fo_kdb
    else:
        return None

def packet2p0f(pkt):
    pkt = pkt.copy()
    pkt = pkt.__class__(str(pkt))
    while pkt.haslayer(IP) and pkt.haslayer(TCP):
        pkt = pkt.getlayer(IP)
        if isinstance(pkt.payload, TCP):
            break
        pkt = pkt.payload
    
    if not isinstance(pkt, IP) or not isinstance(pkt.payload, TCP):
        raise TypeError("Not a TCP/IP packet")
    #if pkt.payload.flags & 0x7 != 0x02: #S,!F,!R
    #    raise TypeError("Not a SYN or SYN/ACK packet")
    
    db = p0f_selectdb(pkt.payload.flags)
    
    #t = p0f_kdb.ttl_range[:]
    #t += [pkt.ttl]
    #t.sort()
    #ttl=t[t.index(pkt.ttl)+1]
    ttl = pkt.ttl
    
    df = (pkt.flags & 2) / 2
    ss = len(pkt)
    # from p0f/config.h : PACKET_BIG = 100
    if ss > 100:
        if db == p0fr_kdb:
            # p0fr.fp: "Packet size may be wildcarded. The meaning of
            #           wildcard is, however, hardcoded as 'size >
            #           PACKET_BIG'"
            ss = '*'
        else:
            ss = 0
    if db == p0fo_kdb:
        # p0fo.fp: "Packet size MUST be wildcarded."
        ss = '*'
    
    ooo = ""
    mss = -1
    qqT = False
    qqP = False
    #qqBroken = False
    ilen = (pkt.payload.dataofs << 2) - 20 # from p0f.c
    for option in pkt.payload.options:
        ilen -= 1
        if option[0] == "MSS":
            ooo += "M" + str(option[1]) + ","
            mss = option[1]
            # FIXME: qqBroken
            ilen -= 3
        elif option[0] == "WScale":
            ooo += "W" + str(option[1]) + ","
            # FIXME: qqBroken
            ilen -= 2
        elif option[0] == "Timestamp":
            if option[1][0] == 0:
                ooo += "T0,"
            else:
                ooo += "T,"
            if option[1][1] != 0:
                qqT = True
            ilen -= 9
        elif option[0] == "SAckOK":
            ooo += "S,"
            ilen -= 1
        elif option[0] == "NOP":
            ooo += "N,"
        elif option[0] == "EOL":
            ooo += "E,"
            if ilen > 0:
                qqP = True
        else:
            if type(option[0]) is str:
                ooo += "?%i," % TCPOptions[1][option[0]]
            else:
                ooo += "?%i," % option[0]
            # FIXME: ilen
    ooo = ooo[:-1]
    if ooo == "": ooo = "."
    
    win = pkt.payload.window
    if mss != -1:
        if mss != 0 and win % mss == 0:
            win = "S" + str(win/mss)
        elif win % (mss + 40) == 0:
            win = "T" + str(win/(mss+40))
    win = str(win)
    
    qq = ""
    
    if db == p0fr_kdb:
        if pkt.payload.flags & 0x10 == 0x10:
            # p0fr.fp: "A new quirk, 'K', is introduced to denote
            #           RST+ACK packets"
            qq += "K"
    # The two next cases should also be only for p0f*r*, but although
    # it's not documented (or I have not noticed), p0f seems to
    # support the '0' and 'Q' quirks on any databases (or at the least
    # "classical" p0f.fp).
    if pkt.payload.seq == pkt.payload.ack:
        # p0fr.fp: "A new quirk, 'Q', is used to denote SEQ number
        #           equal to ACK number."
        qq += "Q"
    if pkt.payload.seq == 0:
        # p0fr.fp: "A new quirk, '0', is used to denote packets
        #           with SEQ number set to 0."
        qq += "0"
    if qqP:
        qq += "P"
    if pkt.id == 0:
        qq += "Z"
    if pkt.options != []:
        qq += "I"
    if pkt.payload.urgptr != 0:
        qq += "U"
    if pkt.payload.reserved != 0:
        qq += "X"
    if pkt.payload.ack != 0:
        qq += "A"
    if qqT:
        qq += "T"
    if db == p0fo_kdb:
        if pkt.payload.flags & 0x20 != 0:
            # U
            # p0fo.fp: "PUSH flag is excluded from 'F' quirk checks"
            qq += "F"
    else:
        if pkt.payload.flags & 0x28 != 0:
            # U or P
            qq += "F"
    if db != p0fo_kdb and not isinstance(pkt.payload.payload, NoPayload):
        # p0fo.fp: "'D' quirk is not checked for."
        qq += "D"
    # FIXME : "!" - broken options segment: not handled yet

    if qq == "":
        qq = "."

    return (db, (win, ttl, df, ss, ooo, qq))

def p0f_correl(x,y):
    d = 0
    # wwww can be "*" or "%nn". "Tnn" and "Snn" should work fine with
    # the x[0] == y[0] test.
    d += (x[0] == y[0] or y[0] == "*" or (y[0][0] == "%" and x[0].isdigit() and (int(x[0]) % int(y[0][1:])) == 0))
    # ttl
    d += (y[1] >= x[1] and y[1] - x[1] < 32)
    for i in [2, 5]:
        d += (x[i] == y[i] or y[i] == '*')
    # '*' has a special meaning for ss
    d += x[3] == y[3]
    xopt = x[4].split(",")
    yopt = y[4].split(",")
    if len(xopt) == len(yopt):
        same = True
        for i in range(len(xopt)):
            if not (xopt[i] == yopt[i] or
                    (len(yopt[i]) == 2 and len(xopt[i]) > 1 and
                     yopt[i][1] == "*" and xopt[i][0] == yopt[i][0]) or
                    (len(yopt[i]) > 2 and len(xopt[i]) > 1 and
                     yopt[i][1] == "%" and xopt[i][0] == yopt[i][0] and
                     int(xopt[i][1:]) % int(yopt[i][2:]) == 0)):
                same = False
                break
        if same:
            d += len(xopt)
    return d


@conf.commands.register
def p0f(pkt):
    """Passive OS fingerprinting: which OS emitted this TCP packet ?
p0f(packet) -> accuracy, [list of guesses]
"""
    db, sig = packet2p0f(pkt)
    if db:
        pb = db.get_base()
    else:
        pb = []
    if not pb:
        warning("p0f base empty.")
        return []
    #s = len(pb[0][0])
    r = []
    max = len(sig[4].split(",")) + 5
    for b in pb:
        d = p0f_correl(sig,b)
        if d == max:
            r.append((b[6], b[7], b[1] - pkt[IP].ttl))
    return r

def prnp0f(pkt):
    # we should print which DB we use
    try:
        r = p0f(pkt)
    except:
        return
    if r == []:
        r = ("UNKNOWN", "[" + ":".join(map(str, packet2p0f(pkt)[1])) + ":?:?]", None)
    else:
        r = r[0]
    uptime = None
    try:
        uptime = pkt2uptime(pkt)
    except:
        pass
    if uptime == 0:
        uptime = None
    res = pkt.sprintf("%IP.src%:%TCP.sport% - " + r[0] + " " + r[1])
    if uptime is not None:
        res += pkt.sprintf(" (up: " + str(uptime/3600) + " hrs)\n  -> %IP.dst%:%TCP.dport% (%TCP.flags%)")
    else:
        res += pkt.sprintf("\n  -> %IP.dst%:%TCP.dport% (%TCP.flags%)")
    if r[2] is not None:
        res += " (distance " + str(r[2]) + ")"
    print res

@conf.commands.register
def pkt2uptime(pkt, HZ=100):
    """Calculate the date the machine which emitted the packet booted using TCP timestamp 
pkt2uptime(pkt, [HZ=100])"""
    if not isinstance(pkt, Packet):
        raise TypeError("Not a TCP packet")
    if isinstance(pkt,NoPayload):
        raise TypeError("Not a TCP packet")
    if not isinstance(pkt, TCP):
        return pkt2uptime(pkt.payload)
    for opt in pkt.options:
        if opt[0] == "Timestamp":
            #t = pkt.time - opt[1][0] * 1.0/HZ
            #return time.ctime(t)
            t = opt[1][0] / HZ
            return t
    raise TypeError("No timestamp option")

def p0f_impersonate(pkt, osgenre=None, osdetails=None, signature=None,
                    extrahops=0, mtu=1500, uptime=None):
    """Modifies pkt so that p0f will think it has been sent by a
specific OS.  If osdetails is None, then we randomly pick up a
personality matching osgenre. If osgenre and signature are also None,
we use a local signature (using p0f_getlocalsigs). If signature is
specified (as a tuple), we use the signature.

For now, only TCP Syn packets are supported.
Some specifications of the p0f.fp file are not (yet) implemented."""
    pkt = pkt.copy()
    #pkt = pkt.__class__(str(pkt))
    while pkt.haslayer(IP) and pkt.haslayer(TCP):
        pkt = pkt.getlayer(IP)
        if isinstance(pkt.payload, TCP):
            break
        pkt = pkt.payload
    
    if not isinstance(pkt, IP) or not isinstance(pkt.payload, TCP):
        raise TypeError("Not a TCP/IP packet")
    
    if uptime is None:
        uptime = random.randint(120,100*60*60*24*365)
    
    db = p0f_selectdb(pkt.payload.flags)
    if osgenre:
        pb = db.get_base()
        if pb is None:
            pb = []
        pb = filter(lambda x: x[6] == osgenre, pb)
        if osdetails:
            pb = filter(lambda x: x[7] == osdetails, pb)
    elif signature:
        pb = [signature]
    else:
        pb = p0f_getlocalsigs()[db]
    if db == p0fr_kdb:
        # 'K' quirk <=> RST+ACK
        if pkt.payload.flags & 0x4 == 0x4:
            pb = filter(lambda x: 'K' in x[5], pb)
        else:
            pb = filter(lambda x: 'K' not in x[5], pb)
    if not pb:
        raise Scapy_Exception("No match in the p0f database")
    pers = pb[random.randint(0, len(pb) - 1)]
    
    # options (we start with options because of MSS)
    ## TODO: let the options already set if they are valid
    options = []
    if pers[4] != '.':
        for opt in pers[4].split(','):
            if opt[0] == 'M':
                # MSS might have a maximum size because of window size
                # specification
                if pers[0][0] == 'S':
                    maxmss = (2L**16-1) / int(pers[0][1:])
                else:
                    maxmss = (2L**16-1)
                # If we have to randomly pick up a value, we cannot use
                # scapy RandXXX() functions, because the value has to be
                # set in case we need it for the window size value. That's
                # why we use random.randint()
                if opt[1:] == '*':
                    options.append(('MSS', random.randint(1,maxmss)))
                elif opt[1] == '%':
                    coef = int(opt[2:])
                    options.append(('MSS', coef*random.randint(1,maxmss/coef)))
                else:
                    options.append(('MSS', int(opt[1:])))
            elif opt[0] == 'W':
                if opt[1:] == '*':
                    options.append(('WScale', RandByte()))
                elif opt[1] == '%':
                    coef = int(opt[2:])
                    options.append(('WScale', coef*RandNum(min=1,
                                                           max=(2L**8-1)/coef)))
                else:
                    options.append(('WScale', int(opt[1:])))
            elif opt == 'T0':
                options.append(('Timestamp', (0, 0)))
            elif opt == 'T':
                if 'T' in pers[5]:
                    # FIXME: RandInt() here does not work (bug (?) in
                    # TCPOptionsField.m2i often raises "OverflowError:
                    # long int too large to convert to int" in:
                    #    oval = struct.pack(ofmt, *oval)"
                    # Actually, this is enough to often raise the error:
                    #    struct.pack('I', RandInt())
                    options.append(('Timestamp', (uptime, random.randint(1,2**32-1))))
                else:
                    options.append(('Timestamp', (uptime, 0)))
            elif opt == 'S':
                options.append(('SAckOK', ''))
            elif opt == 'N':
                options.append(('NOP', None))
            elif opt == 'E':
                options.append(('EOL', None))
            elif opt[0] == '?':
                if int(opt[1:]) in TCPOptions[0]:
                    optname = TCPOptions[0][int(opt[1:])][0]
                    optstruct = TCPOptions[0][int(opt[1:])][1]
                    options.append((optname,
                                    struct.unpack(optstruct,
                                                  RandString(struct.calcsize(optstruct))._fix())))
                else:
                    options.append((int(opt[1:]), ''))
            ## FIXME: qqP not handled
            else:
                warning("unhandled TCP option " + opt)
            pkt.payload.options = options
    
    # window size
    if pers[0] == '*':
        pkt.payload.window = RandShort()
    elif pers[0].isdigit():
        pkt.payload.window = int(pers[0])
    elif pers[0][0] == '%':
        coef = int(pers[0][1:])
        pkt.payload.window = coef * RandNum(min=1,max=(2L**16-1)/coef)
    elif pers[0][0] == 'T':
        pkt.payload.window = mtu * int(pers[0][1:])
    elif pers[0][0] == 'S':
        ## needs MSS set
        MSS = filter(lambda x: x[0] == 'MSS', options)
        if not filter(lambda x: x[0] == 'MSS', options):
            raise Scapy_Exception("TCP window value requires MSS, and MSS option not set")
        pkt.payload.window = filter(lambda x: x[0] == 'MSS', options)[0][1] * int(pers[0][1:])
    else:
        raise Scapy_Exception('Unhandled window size specification')
    
    # ttl
    pkt.ttl = pers[1]-extrahops
    # DF flag
    pkt.flags |= (2 * pers[2])
    ## FIXME: ss (packet size) not handled (how ? may be with D quirk
    ## if present)
    # Quirks
    if pers[5] != '.':
        for qq in pers[5]:
            ## FIXME: not handled: P, I, X, !
            # T handled with the Timestamp option
            if qq == 'Z': pkt.id = 0
            elif qq == 'U': pkt.payload.urgptr = RandShort()
            elif qq == 'A': pkt.payload.ack = RandInt()
            elif qq == 'F':
                if db == p0fo_kdb:
                    pkt.payload.flags |= 0x20 # U
                else:
                    pkt.payload.flags |= RandChoice(8, 32, 40) #P / U / PU
            elif qq == 'D' and db != p0fo_kdb:
                pkt /= Raw(load=RandString(random.randint(1, 10))) # XXX p0fo.fp
            elif qq == 'Q': pkt.payload.seq = pkt.payload.ack
            #elif qq == '0': pkt.payload.seq = 0
        #if db == p0fr_kdb:
        # '0' quirk is actually not only for p0fr.fp (see
        # packet2p0f())
    if '0' in pers[5]:
        pkt.payload.seq = 0
    elif pkt.payload.seq == 0:
        pkt.payload.seq = RandInt()
    
    while pkt.underlayer:
        pkt = pkt.underlayer
    return pkt

def p0f_getlocalsigs():
    """This function returns a dictionary of signatures indexed by p0f
db (e.g., p0f_kdb, p0fa_kdb, ...) for the local TCP/IP stack.

You need to have your firewall at least accepting the TCP packets
from/to a high port (30000 <= x <= 40000) on your loopback interface.

Please note that the generated signatures come from the loopback
interface and may (are likely to) be different than those generated on
"normal" interfaces."""
    pid = os.fork()
    port = random.randint(30000, 40000)
    if pid > 0:
        # parent: sniff
        result = {}
        def addresult(res):
            # TODO: wildcard window size in some cases? and maybe some
            # other values?
            if res[0] not in result:
                result[res[0]] = [res[1]]
            else:
                if res[1] not in result[res[0]]:
                    result[res[0]].append(res[1])
        # XXX could we try with a "normal" interface using other hosts
        iface = conf.route.route('127.0.0.1')[0]
        # each packet is seen twice: S + RA, S + SA + A + FA + A
        # XXX are the packets also seen twice on non Linux systems ?
        count=14
        pl = sniff(iface=iface, filter='tcp and port ' + str(port), count = count, timeout=3)
        map(addresult, map(packet2p0f, pl))
        os.waitpid(pid,0)
    elif pid < 0:
        log_runtime.error("fork error")
    else:
        # child: send
        # XXX erk
        time.sleep(1)
        s1 = socket.socket(socket.AF_INET, type = socket.SOCK_STREAM)
        # S & RA
        try:
            s1.connect(('127.0.0.1', port))
        except socket.error:
            pass
        # S, SA, A, FA, A
        s1.bind(('127.0.0.1', port))
        s1.connect(('127.0.0.1', port))
        # howto: get an RST w/o ACK packet
        s1.close()
        os._exit(0)
    return result


########NEW FILE########
__FILENAME__ = queso
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Clone of queso OS fingerprinting
"""

from scapy.data import KnowledgeBase
from scapy.config import conf
from scapy.layers.inet import IP,TCP
#from 

conf.queso_base ="/etc/queso.conf"


#################
## Queso stuff ##
#################


def quesoTCPflags(flags):
    if flags == "-":
        return "-"
    flv = "FSRPAUXY"
    v = 0
    for i in flags:
        v |= 2**flv.index(i)
    return "%x" % v

class QuesoKnowledgeBase(KnowledgeBase):
    def lazy_init(self):
        try:
            f = open(self.filename)
        except IOError:
            return
        self.base = {}
        p = None
        try:
            for l in f:
                l = l.strip()
                if not l or l[0] == ';':
                    continue
                if l[0] == '*':
                    if p is not None:
                        p[""] = name
                    name = l[1:].strip()
                    p = self.base
                    continue
                if l[0] not in list("0123456"):
                    continue
                res = l[2:].split()
                res[-1] = quesoTCPflags(res[-1])
                res = " ".join(res)
                if not p.has_key(res):
                    p[res] = {}
                p = p[res]
            if p is not None:
                p[""] = name
        except:
            self.base = None
            warning("Can't load queso base [%s]", self.filename)
        f.close()
            
        
queso_kdb = QuesoKnowledgeBase(conf.queso_base)

    
def queso_sig(target, dport=80, timeout=3):
    p = queso_kdb.get_base()
    ret = []
    for flags in ["S", "SA", "F", "FA", "SF", "P", "SEC"]:
        ans, unans = sr(IP(dst=target)/TCP(dport=dport,flags=flags,seq=RandInt()),
                        timeout=timeout, verbose=0)
        if len(ans) == 0:
            rs = "- - - -"
        else:
            s,r = ans[0]
            rs = "%i" % (r.seq != 0)
            if not r.ack:
                r += " 0"
            elif r.ack-s.seq > 666:
                rs += " R" % 0
            else:
                rs += " +%i" % (r.ack-s.seq)
            rs += " %X" % r.window
            rs += " %x" % r.payload.flags
        ret.append(rs)
    return ret
            
def queso_search(sig):
    p = queso_kdb.get_base()
    sig.reverse()
    ret = []
    try:
        while sig:
            s = sig.pop()
            p = p[s]
            if p.has_key(""):
                ret.append(p[""])
    except KeyError:
        pass
    return ret
        

@conf.commands.register
def queso(*args,**kargs):
    """Queso OS fingerprinting
queso(target, dport=80, timeout=3)"""
    return queso_search(queso_sig(*args, **kargs))



########NEW FILE########
__FILENAME__ = voip
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
VoIP (Voice over IP) related functions
"""

import os
###################
## Testing stuff ##
###################

from fcntl import fcntl
from scapy.sendrecv import sniff
from scapy.packet import Raw
from scapy.layers.inet import IP,UDP
from scapy.layers.rtp import RTP
from scapy.utils import get_temp_file


def merge(x,y,sample_size=2):
    if len(x) > len(y):
        y += "\x00"*(len(x)-len(y))
    elif len(x) < len(y):
        x += "\x00"*(len(y)-len(x))
    m = ""
    ss=sample_size
    for i in range(len(x)/ss):
        m += x[ss*i:ss*(i+1)]+y[ss*i:ss*(i+1)]
    return  m
#    return  "".join(map(str.__add__, x, y))


def voip_play(s1,list=None,**kargs):
    FIFO=get_temp_file()
    FIFO1=FIFO % 1
    FIFO2=FIFO % 2
    
    os.mkfifo(FIFO1)
    os.mkfifo(FIFO2)
    try:
        os.system("soxmix -t .ul %s -t .ul %s -t ossdsp /dev/dsp &" % (FIFO1,FIFO2))
        
        c1=open(FIFO1,"w", 4096)
        c2=open(FIFO2,"w", 4096)
        fcntl.fcntl(c1.fileno(),fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(c2.fileno(),fcntl.F_SETFL, os.O_NONBLOCK)
    
    #    dsp,rd = os.popen2("sox -t .ul -c 2 - -t ossdsp /dev/dsp")
        def play(pkt,last=[]):
            if not pkt:
                return 
            if not pkt.haslayer(UDP):
                return 
            ip=pkt.getlayer(IP)
            if s1 in [ip.src, ip.dst]:
                if not last:
                    last.append(pkt)
                    return
                load=last.pop()
    #            x1 = load.load[12:]
                c1.write(load.load[12:])
                if load.getlayer(IP).src == ip.src:
    #                x2 = ""
                    c2.write("\x00"*len(load.load[12:]))
                    last.append(pkt)
                else:
    #                x2 = pkt.load[:12]
                    c2.write(pkt.load[12:])
    #            dsp.write(merge(x1,x2))
    
        if list is None:
            sniff(store=0, prn=play, **kargs)
        else:
            for p in list:
                play(p)
    finally:
        os.unlink(FIFO1)
        os.unlink(FIFO2)



def voip_play1(s1,list=None,**kargs):

    
    dsp,rd = os.popen2("sox -t .ul - -t ossdsp /dev/dsp")
    def play(pkt):
        if not pkt:
            return 
        if not pkt.haslayer(UDP):
            return 
        ip=pkt.getlayer(IP)
        if s1 in [ip.src, ip.dst]:
            dsp.write(pkt.getlayer(Raw).load[12:])
    try:
        if list is None:
            sniff(store=0, prn=play, **kargs)
        else:
            for p in list:
                play(p)
    finally:
        dsp.close()
        rd.close()

def voip_play2(s1,**kargs):
    dsp,rd = os.popen2("sox -t .ul -c 2 - -t ossdsp /dev/dsp")
    def play(pkt,last=[]):
        if not pkt:
            return 
        if not pkt.haslayer(UDP):
            return 
        ip=pkt.getlayer(IP)
        if s1 in [ip.src, ip.dst]:
            if not last:
                last.append(pkt)
                return
            load=last.pop()
            x1 = load.load[12:]
#            c1.write(load.load[12:])
            if load.getlayer(IP).src == ip.src:
                x2 = ""
#                c2.write("\x00"*len(load.load[12:]))
                last.append(pkt)
            else:
                x2 = pkt.load[:12]
#                c2.write(pkt.load[12:])
            dsp.write(merge(x1,x2))
            
    sniff(store=0, prn=play, **kargs)

def voip_play3(lst=None,**kargs):
    dsp,rd = os.popen2("sox -t .ul - -t ossdsp /dev/dsp")
    try:
        def play(pkt, dsp=dsp):
            if pkt and pkt.haslayer(UDP) and pkt.haslayer(Raw):
                dsp.write(pkt.getlayer(RTP).load)
        if lst is None:
            sniff(store=0, prn=play, **kargs)
        else:
            for p in lst:
                play(p)
    finally:
        try:
            dsp.close()
            rd.close()
        except:
            pass


########NEW FILE########
__FILENAME__ = packet
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Packet class. Binding mechanism. fuzz() method.
"""

import time,itertools,os
from fields import StrField,ConditionalField,Emph,PacketListField
from config import conf
from base_classes import BasePacket,Gen,SetGen,Packet_metaclass,NewDefaultValues
from volatile import VolatileValue
from utils import import_hexcap,tex_escape,colgen,get_temp_file
from error import Scapy_Exception,log_runtime

try:
    import pyx
except ImportError:
    pass


class RawVal:
    def __init__(self, val=""):
        self.val = val
    def __str__(self):
        return str(self.val)
    def __repr__(self):
        return "<RawVal [%r]>" % self.val


class Packet(BasePacket):
    __metaclass__ = Packet_metaclass
    name=None

    fields_desc = []

    aliastypes = []
    overload_fields = {}

    underlayer = None

    payload_guess = []
    initialized = 0
    show_indent=1
    explicit = 0

    @classmethod
    def from_hexcap(cls):
        return cls(import_hexcap())

    @classmethod
    def upper_bonds(self):
        for fval,upper in self.payload_guess:
            print "%-20s  %s" % (upper.__name__, ", ".join("%-12s" % ("%s=%r"%i) for i in fval.iteritems()))

    @classmethod
    def lower_bonds(self):
        for lower,fval in self.overload_fields.iteritems():
            print "%-20s  %s" % (lower.__name__, ", ".join("%-12s" % ("%s=%r"%i) for i in fval.iteritems()))

    def __init__(self, _pkt="", post_transform=None, _internal=0, _underlayer=None, **fields):
        self.time  = time.time()
        self.sent_time = 0
        if self.name is None:
            self.name = self.__class__.__name__
        self.aliastypes = [ self.__class__ ] + self.aliastypes
        self.default_fields = {}
        self.overloaded_fields = {}
        self.fields={}
        self.fieldtype={}
        self.packetfields=[]
        self.__dict__["payload"] = NoPayload()
        self.init_fields()
        self.underlayer = _underlayer
        self.initialized = 1
        if _pkt:
            self.dissect(_pkt)
            if not _internal:
                self.dissection_done(self)
        for f in fields.keys():
            self.fields[f] = self.get_field(f).any2i(self,fields[f])
        if type(post_transform) is list:
            self.post_transforms = post_transform
        elif post_transform is None:
            self.post_transforms = []
        else:
            self.post_transforms = [post_transform]

    def init_fields(self):
        self.do_init_fields(self.fields_desc)

    def do_init_fields(self, flist):
        for f in flist:
            self.default_fields[f.name] = f.default
            self.fieldtype[f.name] = f
            if f.holds_packets:
                self.packetfields.append(f)
            
    def dissection_done(self,pkt):
        """DEV: will be called after a dissection is completed"""
        self.post_dissection(pkt)
        self.payload.dissection_done(pkt)
        
    def post_dissection(self, pkt):
        """DEV: is called after the dissection of the whole packet"""
        pass

    def get_field(self, fld):
        """DEV: returns the field instance from the name of the field"""
        return self.fieldtype[fld]
        
    def add_payload(self, payload):
        if payload is None:
            return
        elif not isinstance(self.payload, NoPayload):
            self.payload.add_payload(payload)
        else:
            if isinstance(payload, Packet):
                self.__dict__["payload"] = payload
                payload.add_underlayer(self)
                for t in self.aliastypes:
                    if payload.overload_fields.has_key(t):
                        self.overloaded_fields = payload.overload_fields[t]
                        break
            elif type(payload) is str:
                self.__dict__["payload"] = conf.raw_layer(load=payload)
            else:
                raise TypeError("payload must be either 'Packet' or 'str', not [%s]" % repr(payload))
    def remove_payload(self):
        self.payload.remove_underlayer(self)
        self.__dict__["payload"] = NoPayload()
        self.overloaded_fields = {}
    def add_underlayer(self, underlayer):
        self.underlayer = underlayer
    def remove_underlayer(self,other):
        self.underlayer = None
    def copy(self):
        """Returns a deep copy of the instance."""
        clone = self.__class__()
        clone.fields = self.fields.copy()
        for k in clone.fields:
            clone.fields[k]=self.get_field(k).do_copy(clone.fields[k])
        clone.default_fields = self.default_fields.copy()
        clone.overloaded_fields = self.overloaded_fields.copy()
        clone.overload_fields = self.overload_fields.copy()
        clone.underlayer=self.underlayer
        clone.explicit=self.explicit
        clone.post_transforms=self.post_transforms[:]
        clone.__dict__["payload"] = self.payload.copy()
        clone.payload.add_underlayer(clone)
        return clone

    def getfieldval(self, attr):
        if attr in self.fields:
            return self.fields[attr]
        if attr in self.overloaded_fields:
            return self.overloaded_fields[attr]
        if attr in self.default_fields:
            return self.default_fields[attr]
        return self.payload.getfieldval(attr)
    
    def getfield_and_val(self, attr):
        if attr in self.fields:
            return self.get_field(attr),self.fields[attr]
        if attr in self.overloaded_fields:
            return self.get_field(attr),self.overloaded_fields[attr]
        if attr in self.default_fields:
            return self.get_field(attr),self.default_fields[attr]
        return self.payload.getfield_and_val(attr)
    
    def __getattr__(self, attr):
        if self.initialized:
            fld,v = self.getfield_and_val(attr)
            if fld is not None:
                return fld.i2h(self, v)
            return v
        raise AttributeError(attr)

    def setfieldval(self, attr, val):
        if self.default_fields.has_key(attr):
            fld = self.get_field(attr)
            if fld is None:
                any2i = lambda x,y: y
            else:
                any2i = fld.any2i
            self.fields[attr] = any2i(self, val)
            self.explicit=0
        elif attr == "payload":
            self.remove_payload()
            self.add_payload(val)
        else:
            self.payload.setfieldval(attr,val)

    def __setattr__(self, attr, val):
        if self.initialized:
            try:
                self.setfieldval(attr,val)
            except AttributeError:
                pass
            else:
                return
        self.__dict__[attr] = val

    def delfieldval(self, attr):
        if self.fields.has_key(attr):
            del(self.fields[attr])
            self.explicit=0 # in case a default value must be explicited
        elif self.default_fields.has_key(attr):
            pass
        elif attr == "payload":
            self.remove_payload()
        else:
            self.payload.delfieldval(attr)

    def __delattr__(self, attr):
        if self.initialized:
            try:
                self.delfieldval(attr)
            except AttributeError:
                pass
            else:
                return
        if self.__dict__.has_key(attr):
            del(self.__dict__[attr])
        else:
            raise AttributeError(attr)
            
    def __repr__(self):
        s = ""
        ct = conf.color_theme
        for f in self.fields_desc:
            if isinstance(f, ConditionalField) and not f._evalcond(self):
                continue
            if f.name in self.fields:
                val = f.i2repr(self, self.fields[f.name])
            elif f.name in self.overloaded_fields:
                val =  f.i2repr(self, self.overloaded_fields[f.name])
            else:
                continue
            if isinstance(f, Emph) or f in conf.emph:
                ncol = ct.emph_field_name
                vcol = ct.emph_field_value
            else:
                ncol = ct.field_name
                vcol = ct.field_value

                
            s += " %s%s%s" % (ncol(f.name),
                              ct.punct("="),
                              vcol(val))
        return "%s%s %s %s%s%s"% (ct.punct("<"),
                                  ct.layer_name(self.__class__.__name__),
                                  s,
                                  ct.punct("|"),
                                  repr(self.payload),
                                  ct.punct(">"))
    def __str__(self):
        return self.build()
    def __div__(self, other):
        if isinstance(other, Packet):
            cloneA = self.copy()
            cloneB = other.copy()
            cloneA.add_payload(cloneB)
            return cloneA
        elif type(other) is str:
            return self/conf.raw_layer(load=other)
        else:
            return other.__rdiv__(self)
    def __rdiv__(self, other):
        if type(other) is str:
            return conf.raw_layer(load=other)/self
        else:
            raise TypeError
    def __mul__(self, other):
        if type(other) is int:
            return  [self]*other
        else:
            raise TypeError
    def __rmul__(self,other):
        return self.__mul__(other)
    
    def __nonzero__(self):
        return True
    def __len__(self):
        return len(self.__str__())
    def self_build(self, field_pos_list=None):
        p=""
        for f in self.fields_desc:
            val = self.getfieldval(f.name)
            if isinstance(val, RawVal):
                sval = str(val)
                p += sval
                if field_pos_list is not None:
                    field_pos_list.append( (f.name, sval.encode("string_escape"), len(p), len(sval) ) )
            else:
                p = f.addfield(self, p, val)
        return p

    def do_build_payload(self):
        return self.payload.do_build()

    def do_build(self):
        if not self.explicit:
            self = self.__iter__().next()
        pkt = self.self_build()
        for t in self.post_transforms:
            pkt = t(pkt)
        pay = self.do_build_payload()
        p = self.post_build(pkt,pay)
        return p
    
    def build_padding(self):
        return self.payload.build_padding()

    def build(self):
        p = self.do_build()
        p += self.build_padding()
        p = self.build_done(p)
        return p
    
    def post_build(self, pkt, pay):
        """DEV: called right after the current layer is build."""
        return pkt+pay

    def build_done(self, p):
        return self.payload.build_done(p)

    def do_build_ps(self):
        p=""
        pl = []
        q=""
        for f in self.fields_desc:
            p = f.addfield(self, p, self.getfieldval(f.name) )
            if type(p) is str:
                r = p[len(q):]
                q = p
            else:
                r = ""
            pl.append( (f, f.i2repr(self,self.getfieldval(f.name)), r) )
            
        pkt,lst = self.payload.build_ps(internal=1)
        p += pkt
        lst.append( (self, pl) )
        
        return p,lst
    
    def build_ps(self,internal=0):
        p,lst = self.do_build_ps()
#        if not internal:
#            pkt = self
#            while pkt.haslayer(Padding):
#                pkt = pkt.getlayer(Padding)
#                lst.append( (pkt, [ ("loakjkjd", pkt.load, pkt.load) ] ) )
#                p += pkt.load
#                pkt = pkt.payload
        return p,lst


    def psdump(self, filename=None, **kargs):
        """psdump(filename=None, layer_shift=0, rebuild=1)
Creates an EPS file describing a packet. If filename is not provided a temporary file is created and gs is called."""
        canvas = self.canvas_dump(**kargs)
        if filename is None:
            fname = get_temp_file(autoext=".eps")
            canvas.writeEPSfile(fname)
            subprocess.Popen([conf.prog.psreader, fname+".eps"])
        else:
            canvas.writeEPSfile(filename)

    def pdfdump(self, filename=None, **kargs):
        """pdfdump(filename=None, layer_shift=0, rebuild=1)
        Creates a PDF file describing a packet. If filename is not provided a temporary file is created and xpdf is called."""
        canvas = self.canvas_dump(**kargs)
        if filename is None:
            fname = get_temp_file(autoext=".pdf")
            canvas.writePDFfile(fname)
            subprocess.Popen([conf.prog.pdfreader, fname+".pdf"])
        else:
            canvas.writePDFfile(filename)

        
    def canvas_dump(self, layer_shift=0, rebuild=1):
        canvas = pyx.canvas.canvas()
        if rebuild:
            p,t = self.__class__(str(self)).build_ps()
        else:
            p,t = self.build_ps()
        YTXT=len(t)
        for n,l in t:
            YTXT += len(l)
        YTXT = float(YTXT)
        YDUMP=YTXT

        XSTART = 1
        XDSTART = 10
        y = 0.0
        yd = 0.0
        xd = 0 
        XMUL= 0.55
        YMUL = 0.4
    
        backcolor=colgen(0.6, 0.8, 1.0, trans=pyx.color.rgb)
        forecolor=colgen(0.2, 0.5, 0.8, trans=pyx.color.rgb)
#        backcolor=makecol(0.376, 0.729, 0.525, 1.0)
        
        
        def hexstr(x):
            s = []
            for c in x:
                s.append("%02x" % ord(c))
            return " ".join(s)

                
        def make_dump_txt(x,y,txt):
            return pyx.text.text(XDSTART+x*XMUL, (YDUMP-y)*YMUL, r"\tt{%s}"%hexstr(txt), [pyx.text.size.Large])

        def make_box(o):
            return pyx.box.rect(o.left(), o.bottom(), o.width(), o.height(), relcenter=(0.5,0.5))

        def make_frame(lst):
            if len(lst) == 1:
                b = lst[0].bbox()
                b.enlarge(pyx.unit.u_pt)
                return b.path()
            else:
                fb = lst[0].bbox()
                fb.enlarge(pyx.unit.u_pt)
                lb = lst[-1].bbox()
                lb.enlarge(pyx.unit.u_pt)
                if len(lst) == 2 and fb.left() > lb.right():
                    return pyx.path.path(pyx.path.moveto(fb.right(), fb.top()),
                                         pyx.path.lineto(fb.left(), fb.top()),
                                         pyx.path.lineto(fb.left(), fb.bottom()),
                                         pyx.path.lineto(fb.right(), fb.bottom()),
                                         pyx.path.moveto(lb.left(), lb.top()),
                                         pyx.path.lineto(lb.right(), lb.top()),
                                         pyx.path.lineto(lb.right(), lb.bottom()),
                                         pyx.path.lineto(lb.left(), lb.bottom()))
                else:
                    # XXX
                    gb = lst[1].bbox()
                    if gb != lb:
                        gb.enlarge(pyx.unit.u_pt)
                    kb = lst[-2].bbox()
                    if kb != gb and kb != lb:
                        kb.enlarge(pyx.unit.u_pt)
                    return pyx.path.path(pyx.path.moveto(fb.left(), fb.top()),
                                         pyx.path.lineto(fb.right(), fb.top()),
                                         pyx.path.lineto(fb.right(), kb.bottom()),
                                         pyx.path.lineto(lb.right(), kb.bottom()),
                                         pyx.path.lineto(lb.right(), lb.bottom()),
                                         pyx.path.lineto(lb.left(), lb.bottom()),
                                         pyx.path.lineto(lb.left(), gb.top()),
                                         pyx.path.lineto(fb.left(), gb.top()),
                                         pyx.path.closepath(),)
                                         

        def make_dump(s, shift=0, y=0, col=None, bkcol=None, larg=16):
            c = pyx.canvas.canvas()
            tlist = []
            while s:
                dmp,s = s[:larg-shift],s[larg-shift:]
                txt = make_dump_txt(shift, y, dmp)
                tlist.append(txt)
                shift += len(dmp)
                if shift >= 16:
                    shift = 0
                    y += 1
            if col is None:
                col = pyx.color.rgb.red
            if bkcol is None:
                col = pyx.color.rgb.white
            c.stroke(make_frame(tlist),[col,pyx.deco.filled([bkcol]),pyx.style.linewidth.Thick])
            for txt in tlist:
                c.insert(txt)
            return c, tlist[-1].bbox(), shift, y
                            

        last_shift,last_y=0,0.0
        while t:
            bkcol = backcolor.next()
            proto,fields = t.pop()
            y += 0.5
            pt = pyx.text.text(XSTART, (YTXT-y)*YMUL, r"\font\cmssfont=cmss10\cmssfont{%s}" % proto.name, [ pyx.text.size.Large])
            y += 1
            ptbb=pt.bbox()
            ptbb.enlarge(pyx.unit.u_pt*2)
            canvas.stroke(ptbb.path(),[pyx.color.rgb.black, pyx.deco.filled([bkcol])])
            canvas.insert(pt)
            for fname, fval, fdump in fields:
                col = forecolor.next()
                ft = pyx.text.text(XSTART, (YTXT-y)*YMUL, r"\font\cmssfont=cmss10\cmssfont{%s}" % tex_escape(fname.name))
                if isinstance(fval, str):
                    if len(fval) > 18:
                        fval = fval[:18]+"[...]"
                else:
                    fval=""
                vt = pyx.text.text(XSTART+3, (YTXT-y)*YMUL, r"\font\cmssfont=cmss10\cmssfont{%s}" % tex_escape(fval))
                y += 1.0
                if fdump:
                    dt,target,last_shift,last_y = make_dump(fdump, last_shift, last_y, col, bkcol)

                    dtb = dt.bbox()
                    dtb=target
                    vtb = vt.bbox()
                    bxvt = make_box(vtb)
                    bxdt = make_box(dtb)
                    dtb.enlarge(pyx.unit.u_pt)
                    try:
                        if yd < 0:
                            cnx = pyx.connector.curve(bxvt,bxdt,absangle1=0, absangle2=-90)
                        else:
                            cnx = pyx.connector.curve(bxvt,bxdt,absangle1=0, absangle2=90)
                    except:
                        pass
                    else:
                        canvas.stroke(cnx,[pyx.style.linewidth.thin,pyx.deco.earrow.small,col])
                        
                    canvas.insert(dt)
                
                canvas.insert(ft)
                canvas.insert(vt)
            last_y += layer_shift
    
        return canvas



    def extract_padding(self, s):
        """DEV: to be overloaded to extract current layer's padding. Return a couple of strings (actual layer, padding)"""
        return s,None

    def post_dissect(self, s):
        """DEV: is called right after the current layer has been dissected"""
        return s

    def pre_dissect(self, s):
        """DEV: is called right before the current layer is dissected"""
        return s

    def do_dissect(self, s):
        flist = self.fields_desc[:]
        flist.reverse()
        while s and flist:
            f = flist.pop()
            s,fval = f.getfield(self, s)
            self.fields[f.name] = fval
            
        return s

    def do_dissect_payload(self, s):
        if s:
            cls = self.guess_payload_class(s)
            try:
                p = cls(s, _internal=1, _underlayer=self)
            except KeyboardInterrupt:
                raise
            except:
                if conf.debug_dissector:
                    if isinstance(cls,type) and issubclass(cls,Packet):
                        log_runtime.error("%s dissector failed" % cls.name)
                    else:
                        log_runtime.error("%s.guess_payload_class() returned [%s]" % (self.__class__.__name__,repr(cls)))
                    if cls is not None:
                        raise
                p = conf.raw_layer(s, _internal=1, _underlayer=self)
            self.add_payload(p)

    def dissect(self, s):
        s = self.pre_dissect(s)

        s = self.do_dissect(s)

        s = self.post_dissect(s)
            
        payl,pad = self.extract_padding(s)
        self.do_dissect_payload(payl)
        if pad and conf.padding:
            self.add_payload(Padding(pad))


    def guess_payload_class(self, payload):
        """DEV: Guesses the next payload class from layer bonds. Can be overloaded to use a different mechanism."""
        for t in self.aliastypes:
            for fval, cls in t.payload_guess:
                ok = 1
                for k in fval.keys():
                    if not hasattr(self, k) or fval[k] != self.getfieldval(k):
                        ok = 0
                        break
                if ok:
                    return cls
        return self.default_payload_class(payload)
    
    def default_payload_class(self, payload):
        """DEV: Returns the default payload class if nothing has been found by the guess_payload_class() method."""
        return conf.raw_layer

    def hide_defaults(self):
        """Removes fields' values that are the same as default values."""
        for k in self.fields.keys():
            if self.default_fields.has_key(k):
                if self.default_fields[k] == self.fields[k]:
                    del(self.fields[k])
        self.payload.hide_defaults()
            
    def clone_with(self, payload=None, **kargs):
        pkt = self.__class__()
        pkt.explicit = 1
        pkt.fields = kargs
        pkt.time = self.time
        pkt.underlayer = self.underlayer
        pkt.overload_fields = self.overload_fields.copy()
        pkt.post_transforms = self.post_transforms
        if payload is not None:
            pkt.add_payload(payload)
        return pkt
        

    def __iter__(self):
        def loop(todo, done, self=self):
            if todo:
                eltname = todo.pop()
                elt = self.getfieldval(eltname)
                if not isinstance(elt, Gen):
                    if self.get_field(eltname).islist:
                        elt = SetGen([elt])
                    else:
                        elt = SetGen(elt)
                for e in elt:
                    done[eltname]=e
                    for x in loop(todo[:], done):
                        yield x
            else:
                if isinstance(self.payload,NoPayload):
                    payloads = [None]
                else:
                    payloads = self.payload
                for payl in payloads:
                    done2=done.copy()
                    for k in done2:
                        if isinstance(done2[k], VolatileValue):
                            done2[k] = done2[k]._fix()
                    pkt = self.clone_with(payload=payl, **done2)
                    yield pkt

        if self.explicit:
            todo = []
            done = self.fields
        else:
            todo = [ k for (k,v) in itertools.chain(self.default_fields.iteritems(),
                                                    self.overloaded_fields.iteritems())
                     if isinstance(v, VolatileValue) ] + self.fields.keys()
            done = {}
        return loop(todo, done)

    def __gt__(self, other):
        """True if other is an answer from self (self ==> other)."""
        if isinstance(other, Packet):
            return other < self
        elif type(other) is str:
            return 1
        else:
            raise TypeError((self, other))
    def __lt__(self, other):
        """True if self is an answer from other (other ==> self)."""
        if isinstance(other, Packet):
            return self.answers(other)
        elif type(other) is str:
            return 1
        else:
            raise TypeError((self, other))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        for f in self.fields_desc:
            if f not in other.fields_desc:
                return False
            if self.getfieldval(f.name) != other.getfieldval(f.name):
                return False
        return self.payload == other.payload

    def __ne__(self, other):
        return not self.__eq__(other)

    def hashret(self):
        """DEV: returns a string that has the same value for a request and its answer."""
        return self.payload.hashret()
    def answers(self, other):
        """DEV: true if self is an answer from other"""
        if other.__class__ == self.__class__:
            return self.payload.answers(other.payload)
        return 0

    def haslayer(self, cls):
        """true if self has a layer that is an instance of cls. Superseded by "cls in self" syntax."""
        if self.__class__ == cls or self.__class__.__name__ == cls:
            return 1
        for f in self.packetfields:
            fvalue_gen = self.getfieldval(f.name)
            if fvalue_gen is None:
                continue
            if not f.islist:
                fvalue_gen = SetGen(fvalue_gen,_iterpacket=0)
            for fvalue in fvalue_gen:
                if isinstance(fvalue, Packet):
                    ret = fvalue.haslayer(cls)
                    if ret:
                        return ret
        return self.payload.haslayer(cls)
    def getlayer(self, cls, nb=1, _track=None):
        """Return the nb^th layer that is an instance of cls."""
        if type(cls) is int:
            nb = cls+1
            cls = None
        if type(cls) is str and "." in cls:
            ccls,fld = cls.split(".",1)
        else:
            ccls,fld = cls,None
        if cls is None or self.__class__ == cls or self.__class__.name == ccls:
            if nb == 1:
                if fld is None:
                    return self
                else:
                    return self.getfieldval(fld)
            else:
                nb -=1
        for f in self.packetfields:
            fvalue_gen = self.getfieldval(f.name)
            if fvalue_gen is None:
                continue
            if not f.islist:
                fvalue_gen = SetGen(fvalue_gen,_iterpacket=0)
            for fvalue in fvalue_gen:
                if isinstance(fvalue, Packet):
                    track=[]
                    ret = fvalue.getlayer(cls, nb, _track=track)
                    if ret is not None:
                        return ret
                    nb = track[0]
        return self.payload.getlayer(cls,nb,_track=_track)

    def firstlayer(self):
        q = self
        while q.underlayer is not None:
            q = q.underlayer
        return q

    def __getitem__(self, cls):
        if type(cls) is slice:
            lname = cls.start
            if cls.stop:
                ret = self.getlayer(cls.start, cls.stop)
            else:
                ret = self.getlayer(cls.start)
            if ret is None and cls.step is not None:
                ret = cls.step
        else:
            lname=cls
            ret = self.getlayer(cls)
        if ret is None:
            if type(lname) is Packet_metaclass:
                lname = lname.__name__
            elif type(lname) is not str:
                lname = repr(lname)
            raise IndexError("Layer [%s] not found" % lname)
        return ret

    def __delitem__(self, cls):
        del(self[cls].underlayer.payload)

    def __setitem__(self, cls, val):
        self[cls].underlayer.payload = val
    
    def __contains__(self, cls):
        """"cls in self" returns true if self has a layer which is an instance of cls."""
        return self.haslayer(cls)

    def route(self):
        return (None,None,None)

    def fragment(self, *args, **kargs):
        return self.payload.fragment(*args, **kargs)
    

    def display(self,*args,**kargs):  # Deprecated. Use show()
        """Deprecated. Use show() method."""
        self.show(*args,**kargs)
    def show(self, indent=3, lvl="", label_lvl=""):
        """Prints a hierarchical view of the packet. "indent" gives the size of indentation for each layer."""
        ct = conf.color_theme
        print "%s%s %s %s" % (label_lvl,
                              ct.punct("###["),
                              ct.layer_name(self.name),
                              ct.punct("]###"))
        for f in self.fields_desc:
            if isinstance(f, ConditionalField) and not f._evalcond(self):
                continue
            if isinstance(f, Emph) or f in conf.emph:
                ncol = ct.emph_field_name
                vcol = ct.emph_field_value
            else:
                ncol = ct.field_name
                vcol = ct.field_value
            fvalue = self.getfieldval(f.name)
            if isinstance(fvalue, Packet) or (f.islist and f.holds_packets and type(fvalue) is list):
                print "%s  \\%-10s\\" % (label_lvl+lvl, ncol(f.name))
                fvalue_gen = SetGen(fvalue,_iterpacket=0)
                for fvalue in fvalue_gen:
                    fvalue.show(indent=indent, label_lvl=label_lvl+lvl+"   |")
            else:
                begn = "%s  %-10s%s " % (label_lvl+lvl,
                                        ncol(f.name),
                                        ct.punct("="),)
                reprval = f.i2repr(self,fvalue)
                if type(reprval) is str:
                    reprval = reprval.replace("\n", "\n"+" "*(len(label_lvl)
                                                              +len(lvl)
                                                              +len(f.name)
                                                              +4))
                print "%s%s" % (begn,vcol(reprval))
        self.payload.show(indent=indent, lvl=lvl+(" "*indent*self.show_indent), label_lvl=label_lvl)
    def show2(self):
        """Prints a hierarchical view of an assembled version of the packet, so that automatic fields are calculated (checksums, etc.)"""
        self.__class__(str(self)).show()

    def sprintf(self, fmt, relax=1):
        """sprintf(format, [relax=1]) -> str
where format is a string that can include directives. A directive begins and
ends by % and has the following format %[fmt[r],][cls[:nb].]field%.

fmt is a classic printf directive, "r" can be appended for raw substitution
(ex: IP.flags=0x18 instead of SA), nb is the number of the layer we want
(ex: for IP/IP packets, IP:2.src is the src of the upper IP layer).
Special case : "%.time%" is the creation time.
Ex : p.sprintf("%.time% %-15s,IP.src% -> %-15s,IP.dst% %IP.chksum% "
               "%03xr,IP.proto% %r,TCP.flags%")

Moreover, the format string can include conditionnal statements. A conditionnal
statement looks like : {layer:string} where layer is a layer name, and string
is the string to insert in place of the condition if it is true, i.e. if layer
is present. If layer is preceded by a "!", the result si inverted. Conditions
can be imbricated. A valid statement can be :
  p.sprintf("This is a{TCP: TCP}{UDP: UDP}{ICMP:n ICMP} packet")
  p.sprintf("{IP:%IP.dst% {ICMP:%ICMP.type%}{TCP:%TCP.dport%}}")

A side effect is that, to obtain "{" and "}" characters, you must use
"%(" and "%)".
"""

        escape = { "%": "%",
                   "(": "{",
                   ")": "}" }


        # Evaluate conditions 
        while "{" in fmt:
            i = fmt.rindex("{")
            j = fmt[i+1:].index("}")
            cond = fmt[i+1:i+j+1]
            k = cond.find(":")
            if k < 0:
                raise Scapy_Exception("Bad condition in format string: [%s] (read sprintf doc!)"%cond)
            cond,format = cond[:k],cond[k+1:]
            res = False
            if cond[0] == "!":
                res = True
                cond = cond[1:]
            if self.haslayer(cond):
                res = not res
            if not res:
                format = ""
            fmt = fmt[:i]+format+fmt[i+j+2:]

        # Evaluate directives
        s = ""
        while "%" in fmt:
            i = fmt.index("%")
            s += fmt[:i]
            fmt = fmt[i+1:]
            if fmt and fmt[0] in escape:
                s += escape[fmt[0]]
                fmt = fmt[1:]
                continue
            try:
                i = fmt.index("%")
                sfclsfld = fmt[:i]
                fclsfld = sfclsfld.split(",")
                if len(fclsfld) == 1:
                    f = "s"
                    clsfld = fclsfld[0]
                elif len(fclsfld) == 2:
                    f,clsfld = fclsfld
                else:
                    raise Scapy_Exception
                if "." in clsfld:
                    cls,fld = clsfld.split(".")
                else:
                    cls = self.__class__.__name__
                    fld = clsfld
                num = 1
                if ":" in cls:
                    cls,num = cls.split(":")
                    num = int(num)
                fmt = fmt[i+1:]
            except:
                raise Scapy_Exception("Bad format string [%%%s%s]" % (fmt[:25], fmt[25:] and "..."))
            else:
                if fld == "time":
                    val = time.strftime("%H:%M:%S.%%06i", time.localtime(self.time)) % int((self.time-int(self.time))*1000000)
                elif cls == self.__class__.__name__ and hasattr(self, fld):
                    if num > 1:
                        val = self.payload.sprintf("%%%s,%s:%s.%s%%" % (f,cls,num-1,fld), relax)
                        f = "s"
                    elif f[-1] == "r":  # Raw field value
                        val = getattr(self,fld)
                        f = f[:-1]
                        if not f:
                            f = "s"
                    else:
                        val = getattr(self,fld)
                        if fld in self.fieldtype:
                            val = self.fieldtype[fld].i2repr(self,val)
                else:
                    val = self.payload.sprintf("%%%s%%" % sfclsfld, relax)
                    f = "s"
                s += ("%"+f) % val
            
        s += fmt
        return s

    def mysummary(self):
        """DEV: can be overloaded to return a string that summarizes the layer.
           Only one mysummary() is used in a whole packet summary: the one of the upper layer,
           except if a mysummary() also returns (as a couple) a list of layers whose
           mysummary() must be called if they are present."""
        return ""

    def _do_summary(self):
        found,s,needed = self.payload._do_summary()
        if s:
            s = " / "+s
        ret = ""
        if not found or self.__class__ in needed:
            ret = self.mysummary()
            if type(ret) is tuple:
                ret,n = ret
                needed += n
        if ret or needed:
            found = 1
        if not ret:
            ret = self.__class__.__name__
        if self.__class__ in conf.emph:
            impf = []
            for f in self.fields_desc:
                if f in conf.emph:
                    impf.append("%s=%s" % (f.name, f.i2repr(self, self.getfieldval(f.name))))
            ret = "%s [%s]" % (ret," ".join(impf))
        ret = "%s%s" % (ret,s)
        return found,ret,needed

    def summary(self, intern=0):
        """Prints a one line summary of a packet."""
        found,s,needed = self._do_summary()
        return s

    
    def lastlayer(self,layer=None):
        """Returns the uppest layer of the packet"""
        return self.payload.lastlayer(self)

    def decode_payload_as(self,cls):
        """Reassembles the payload and decode it using another packet class"""
        s = str(self.payload)
        self.payload = cls(s, _internal=1, _underlayer=self)
        pp = self
        while pp.underlayer is not None:
            pp = pp.underlayer
        self.payload.dissection_done(pp)

    def libnet(self):
        """Not ready yet. Should give the necessary C code that interfaces with libnet to recreate the packet"""
        print "libnet_build_%s(" % self.__class__.name.lower()
        det = self.__class__(str(self))
        for f in self.fields_desc:
            val = det.getfieldval(f.name)
            if val is None:
                val = 0
            elif type(val) is int:
                val = str(val)
            else:
                val = '"%s"' % str(val)
            print "\t%s, \t\t/* %s */" % (val,f.name)
        print ");"
    def command(self):
        """Returns a string representing the command you have to type to obtain the same packet"""
        f = []
        for fn,fv in self.fields.items():
            fld = self.get_field(fn)
            if isinstance(fv, Packet):
                fv = fv.command()
            elif fld.islist and fld.holds_packets and type(fv) is list:
                fv = "[%s]" % ",".join( map(Packet.command, fv))
            else:
                fv = repr(fv)
            f.append("%s=%s" % (fn, fv))
        c = "%s(%s)" % (self.__class__.__name__, ", ".join(f))
        pc = self.payload.command()
        if pc:
            c += "/"+pc
        return c                    

class NoPayload(Packet):
    def __new__(cls, *args, **kargs):
        singl = cls.__dict__.get("__singl__")
        if singl is None:
            cls.__singl__ = singl = Packet.__new__(cls)
            Packet.__init__(singl)
        return singl
    def __init__(self, *args, **kargs):
        pass
    def dissection_done(self,pkt):
        return
    def add_payload(self, payload):
        raise Scapy_Exception("Can't add payload to NoPayload instance")
    def remove_payload(self):
        pass
    def add_underlayer(self,underlayer):
        pass
    def remove_underlayer(self,other):
        pass
    def copy(self):
        return self
    def __repr__(self):
        return ""
    def __str__(self):
        return ""
    def __nonzero__(self):
        return False
    def do_build(self):
        return ""
    def build(self):
        return ""
    def build_padding(self):
        return ""
    def build_done(self, p):
        return p
    def build_ps(self, internal=0):
        return "",[]
    def getfieldval(self, attr):
        raise AttributeError(attr)
    def getfield_and_val(self, attr):
        raise AttributeError(attr)
    def setfieldval(self, attr, val):
        raise AttributeError(attr)
    def delfieldval(self, attr):
        raise AttributeError(attr)
    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        elif attr in self.__class__.__dict__:
            return self.__class__.__dict__[attr]
        else:
            raise AttributeError, attr
    def hide_defaults(self):
        pass
    def __iter__(self):
        return iter([])
    def __eq__(self, other):
        if isinstance(other, NoPayload):
            return True
        return False
    def hashret(self):
        return ""
    def answers(self, other):
        return isinstance(other, NoPayload) or isinstance(other, Padding)
    def haslayer(self, cls):
        return 0
    def getlayer(self, cls, nb=1, _track=None):
        if _track is not None:
            _track.append(nb)
        return None
    def fragment(self, *args, **kargs):
        raise Scapy_Exception("cannot fragment this packet")        
    def show(self, indent=3, lvl="", label_lvl=""):
        pass
    def sprintf(self, fmt, relax):
        if relax:
            return "??"
        else:
            raise Scapy_Exception("Format not found [%s]"%fmt)
    def _do_summary(self):
        return 0,"",[]
    def lastlayer(self,layer):
        return layer
    def command(self):
        return ""
    
####################
## packet classes ##
####################

            
class Raw(Packet):
    name = "Raw"
    fields_desc = [ StrField("load", "") ]
    def answers(self, other):
        return 1
#        s = str(other)
#        t = self.load
#        l = min(len(s), len(t))
#        return  s[:l] == t[:l]
    def mysummary(self):
        cs = conf.raw_summary
        if cs:
            if callable(cs):
                return "Raw %s" % cs(self.load)
            else:
                return "Raw %r" % self.load
        return Packet.mysummary(self)
        
class Padding(Raw):
    name = "Padding"
    def self_build(self):
        return ""
    def build_padding(self):
        return self.load+self.payload.build_padding()

conf.raw_layer = Raw
if conf.default_l2 is None:
    conf.default_l2 = Raw

#################
## Bind layers ##
#################


def bind_bottom_up(lower, upper, __fval=None, **fval):
    if __fval is not None:
        fval.update(__fval)
    lower.payload_guess = lower.payload_guess[:]
    lower.payload_guess.append((fval, upper))
    

def bind_top_down(lower, upper, __fval=None, **fval):
    if __fval is not None:
        fval.update(__fval)
    upper.overload_fields = upper.overload_fields.copy()
    upper.overload_fields[lower] = fval
    
@conf.commands.register
def bind_layers(lower, upper, __fval=None, **fval):
    """Bind 2 layers on some specific fields' values"""
    if __fval is not None:
        fval.update(__fval)
    bind_top_down(lower, upper, **fval)
    bind_bottom_up(lower, upper, **fval)

def split_bottom_up(lower, upper, __fval=None, **fval):
    if __fval is not None:
        fval.update(__fval)
    def do_filter((f,u),upper=upper,fval=fval):
        if u != upper:
            return True
        for k in fval:
            if k not in f or f[k] != fval[k]:
                return True
        return False
    lower.payload_guess = filter(do_filter, lower.payload_guess)
        
def split_top_down(lower, upper, __fval=None, **fval):
    if __fval is not None:
        fval.update(__fval)
    if lower in upper.overload_fields:
        ofval = upper.overload_fields[lower]
        for k in fval:
            if k not in ofval or ofval[k] != fval[k]:
                return
        upper.overload_fields = upper.overload_fields.copy()
        del(upper.overload_fields[lower])

@conf.commands.register
def split_layers(lower, upper, __fval=None, **fval):
    """Split 2 layers previously bound"""
    if __fval is not None:
        fval.update(__fval)
    split_bottom_up(lower, upper, **fval)
    split_top_down(lower, upper, **fval)


@conf.commands.register
def ls(obj=None):
    """List  available layers, or infos on a given layer"""
    if obj is None:
        
        import __builtin__
        all = __builtin__.__dict__.copy()
        all.update(globals())
        objlst = sorted(conf.layers, key=lambda x:x.__name__)
        for o in objlst:
            print "%-10s : %s" %(o.__name__,o.name)
    else:
        if isinstance(obj, type) and issubclass(obj, Packet):
            for f in obj.fields_desc:
                print "%-10s : %-20s = (%s)" % (f.name, f.__class__.__name__,  repr(f.default))
        elif isinstance(obj, Packet):
            for f in obj.fields_desc:
                print "%-10s : %-20s = %-15s (%s)" % (f.name, f.__class__.__name__, repr(getattr(obj,f.name)), repr(f.default))
            if not isinstance(obj.payload, NoPayload):
                print "--"
                ls(obj.payload)
                

        else:
            print "Not a packet class. Type 'ls()' to list packet classes."


    
#############
## Fuzzing ##
#############

@conf.commands.register
def fuzz(p, _inplace=0):
    """Transform a layer into a fuzzy layer by replacing some default values by random objects"""
    if not _inplace:
        p = p.copy()
    q = p
    while not isinstance(q, NoPayload):
        for f in q.fields_desc:
            if isinstance(f, PacketListField):
                for r in getattr(q, f.name):
                    print "fuzzing", repr(r)
                    fuzz(r, _inplace=1)
            elif f.default is not None:
                rnd = f.randval()
                if rnd is not None:
                    q.default_fields[f.name] = rnd
        q = q.payload
    return p




########NEW FILE########
__FILENAME__ = plist
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
PacketList: holds several packets and allows to do operations on them.
"""


import os,subprocess
from config import conf
from base_classes import BasePacket,BasePacketList
from packet import Padding
from collections import defaultdict

from utils import do_graph,hexdump,make_table,make_lined_table,make_tex_table,get_temp_file

import arch
if arch.GNUPLOT:
    Gnuplot=arch.Gnuplot



#############
## Results ##
#############

class PacketList(BasePacketList):
    res = []
    def __init__(self, res=None, name="PacketList", stats=None):
        """create a packet list from a list of packets
           res: the list of packets
           stats: a list of classes that will appear in the stats (defaults to [TCP,UDP,ICMP])"""
        if stats is None:
            stats = conf.stats_classic_protocols
        self.stats = stats
        if res is None:
            res = []
        if isinstance(res, PacketList):
            res = res.res
        self.res = res
        self.listname = name
    def _elt2pkt(self, elt):
        return elt
    def _elt2sum(self, elt):
        return elt.summary()
    def _elt2show(self, elt):
        return self._elt2sum(elt)
    def __repr__(self):
#        stats=dict.fromkeys(self.stats,0) ## needs python >= 2.3  :(
        stats = dict(map(lambda x: (x,0), self.stats))
        other = 0
        for r in self.res:
            f = 0
            for p in stats:
                if self._elt2pkt(r).haslayer(p):
                    stats[p] += 1
                    f = 1
                    break
            if not f:
                other += 1
        s = ""
        ct = conf.color_theme
        for p in self.stats:
            s += " %s%s%s" % (ct.packetlist_proto(p.name),
                              ct.punct(":"),
                              ct.packetlist_value(stats[p]))
        s += " %s%s%s" % (ct.packetlist_proto("Other"),
                          ct.punct(":"),
                          ct.packetlist_value(other))
        return "%s%s%s%s%s" % (ct.punct("<"),
                               ct.packetlist_name(self.listname),
                               ct.punct(":"),
                               s,
                               ct.punct(">"))
    def __getattr__(self, attr):
        return getattr(self.res, attr)
    def __getitem__(self, item):
        if isinstance(item,type) and issubclass(item,BasePacket):
            return self.__class__(filter(lambda x: item in self._elt2pkt(x),self.res),
                                  name="%s from %s"%(item.__name__,self.listname))
        if type(item) is slice:
            return self.__class__(self.res.__getitem__(item),
                                  name = "mod %s" % self.listname)
        return self.res.__getitem__(item)
    def __getslice__(self, *args, **kargs):
        return self.__class__(self.res.__getslice__(*args, **kargs),
                              name="mod %s"%self.listname)
    def __add__(self, other):
        return self.__class__(self.res+other.res,
                              name="%s+%s"%(self.listname,other.listname))
    def summary(self, prn=None, lfilter=None):
        """prints a summary of each packet
prn:     function to apply to each packet instead of lambda x:x.summary()
lfilter: truth function to apply to each packet to decide whether it will be displayed"""
        for r in self.res:
            if lfilter is not None:
                if not lfilter(r):
                    continue
            if prn is None:
                print self._elt2sum(r)
            else:
                print prn(r)
    def nsummary(self,prn=None, lfilter=None):
        """prints a summary of each packet with the packet's number
prn:     function to apply to each packet instead of lambda x:x.summary()
lfilter: truth function to apply to each packet to decide whether it will be displayed"""
        for i in range(len(self.res)):
            if lfilter is not None:
                if not lfilter(self.res[i]):
                    continue
            print conf.color_theme.id(i,fmt="%04i"),
            if prn is None:
                print self._elt2sum(self.res[i])
            else:
                print prn(self.res[i])
    def display(self): # Deprecated. Use show()
        """deprecated. is show()"""
        self.show()
    def show(self, *args, **kargs):
        """Best way to display the packet list. Defaults to nsummary() method"""
        return self.nsummary(*args, **kargs)
    
    def filter(self, func):
        """Returns a packet list filtered by a truth function"""
        return self.__class__(filter(func,self.res),
                              name="filtered %s"%self.listname)
    def make_table(self, *args, **kargs):
        """Prints a table using a function that returs for each packet its head column value, head row value and displayed value
        ex: p.make_table(lambda x:(x[IP].dst, x[TCP].dport, x[TCP].sprintf("%flags%")) """
        return make_table(self.res, *args, **kargs)
    def make_lined_table(self, *args, **kargs):
        """Same as make_table, but print a table with lines"""
        return make_lined_table(self.res, *args, **kargs)
    def make_tex_table(self, *args, **kargs):
        """Same as make_table, but print a table with LaTeX syntax"""
        return make_tex_table(self.res, *args, **kargs)

    def plot(self, f, lfilter=None,**kargs):
        """Applies a function to each packet to get a value that will be plotted with GnuPlot. A gnuplot object is returned
        lfilter: a truth function that decides whether a packet must be ploted"""
        g=Gnuplot.Gnuplot()
        l = self.res
        if lfilter is not None:
            l = filter(lfilter, l)
        l = map(f,l)
        g.plot(Gnuplot.Data(l, **kargs))
        return g

    def diffplot(self, f, delay=1, lfilter=None, **kargs):
        """diffplot(f, delay=1, lfilter=None)
        Applies a function to couples (l[i],l[i+delay])"""
        g = Gnuplot.Gnuplot()
        l = self.res
        if lfilter is not None:
            l = filter(lfilter, l)
        l = map(f,l[:-delay],l[delay:])
        g.plot(Gnuplot.Data(l, **kargs))
        return g

    def multiplot(self, f, lfilter=None, **kargs):
        """Uses a function that returns a label and a value for this label, then plots all the values label by label"""
        g=Gnuplot.Gnuplot()
        l = self.res
        if lfilter is not None:
            l = filter(lfilter, l)

        d={}
        for e in l:
            k,v = f(e)
            if k in d:
                d[k].append(v)
            else:
                d[k] = [v]
        data=[]
        for k in d:
            data.append(Gnuplot.Data(d[k], title=k, **kargs))

        g.plot(*data)
        return g
        

    def rawhexdump(self):
        """Prints an hexadecimal dump of each packet in the list"""
        for p in self:
            hexdump(self._elt2pkt(p))

    def hexraw(self, lfilter=None):
        """Same as nsummary(), except that if a packet has a Raw layer, it will be hexdumped
        lfilter: a truth function that decides whether a packet must be displayed"""
        for i in range(len(self.res)):
            p = self._elt2pkt(self.res[i])
            if lfilter is not None and not lfilter(p):
                continue
            print "%s %s %s" % (conf.color_theme.id(i,fmt="%04i"),
                                p.sprintf("%.time%"),
                                self._elt2sum(self.res[i]))
            if p.haslayer(conf.raw_layer):
                hexdump(p.getlayer(conf.raw_layer).load)

    def hexdump(self, lfilter=None):
        """Same as nsummary(), except that packets are also hexdumped
        lfilter: a truth function that decides whether a packet must be displayed"""
        for i in range(len(self.res)):
            p = self._elt2pkt(self.res[i])
            if lfilter is not None and not lfilter(p):
                continue
            print "%s %s %s" % (conf.color_theme.id(i,fmt="%04i"),
                                p.sprintf("%.time%"),
                                self._elt2sum(self.res[i]))
            hexdump(p)

    def padding(self, lfilter=None):
        """Same as hexraw(), for Padding layer"""
        for i in range(len(self.res)):
            p = self._elt2pkt(self.res[i])
            if p.haslayer(Padding):
                if lfilter is None or lfilter(p):
                    print "%s %s %s" % (conf.color_theme.id(i,fmt="%04i"),
                                        p.sprintf("%.time%"),
                                        self._elt2sum(self.res[i]))
                    hexdump(p.getlayer(Padding).load)

    def nzpadding(self, lfilter=None):
        """Same as padding() but only non null padding"""
        for i in range(len(self.res)):
            p = self._elt2pkt(self.res[i])
            if p.haslayer(Padding):
                pad = p.getlayer(Padding).load
                if pad == pad[0]*len(pad):
                    continue
                if lfilter is None or lfilter(p):
                    print "%s %s %s" % (conf.color_theme.id(i,fmt="%04i"),
                                        p.sprintf("%.time%"),
                                        self._elt2sum(self.res[i]))
                    hexdump(p.getlayer(Padding).load)
        

    def conversations(self, getsrcdst=None,**kargs):
        """Graphes a conversations between sources and destinations and display it
        (using graphviz and imagemagick)
        getsrcdst: a function that takes an element of the list and return the source and dest
                   by defaults, return source and destination IP
        type: output type (svg, ps, gif, jpg, etc.), passed to dot's "-T" option
        target: filename or redirect. Defaults pipe to Imagemagick's display program
        prog: which graphviz program to use"""
        if getsrcdst is None:
            getsrcdst = lambda x:(x['IP'].src, x['IP'].dst)
        conv = {}
        for p in self.res:
            p = self._elt2pkt(p)
            try:
                c = getsrcdst(p)
            except:
                #XXX warning()
                continue
            conv[c] = conv.get(c,0)+1
        gr = 'digraph "conv" {\n'
        for s,d in conv:
            gr += '\t "%s" -> "%s"\n' % (s,d)
        gr += "}\n"        
        return do_graph(gr, **kargs)

    def afterglow(self, src=None, event=None, dst=None, **kargs):
        """Experimental clone attempt of http://sourceforge.net/projects/afterglow
        each datum is reduced as src -> event -> dst and the data are graphed.
        by default we have IP.src -> IP.dport -> IP.dst"""
        if src is None:
            src = lambda x: x['IP'].src
        if event is None:
            event = lambda x: x['IP'].dport
        if dst is None:
            dst = lambda x: x['IP'].dst
        sl = {}
        el = {}
        dl = {}
        for i in self.res:
            try:
                s,e,d = src(i),event(i),dst(i)
                if s in sl:
                    n,l = sl[s]
                    n += 1
                    if e not in l:
                        l.append(e)
                    sl[s] = (n,l)
                else:
                    sl[s] = (1,[e])
                if e in el:
                    n,l = el[e]
                    n+=1
                    if d not in l:
                        l.append(d)
                    el[e] = (n,l)
                else:
                    el[e] = (1,[d])
                dl[d] = dl.get(d,0)+1
            except:
                continue

        import math
        def normalize(n):
            return 2+math.log(n)/4.0

        def minmax(x):
            m,M = min(x),max(x)
            if m == M:
                m = 0
            if M == 0:
                M = 1
            return m,M

        mins,maxs = minmax(map(lambda (x,y): x, sl.values()))
        mine,maxe = minmax(map(lambda (x,y): x, el.values()))
        mind,maxd = minmax(dl.values())
    
        gr = 'digraph "afterglow" {\n\tedge [len=2.5];\n'

        gr += "# src nodes\n"
        for s in sl:
            n,l = sl[s]; n = 1+float(n-mins)/(maxs-mins)
            gr += '"src.%s" [label = "%s", shape=box, fillcolor="#FF0000", style=filled, fixedsize=1, height=%.2f,width=%.2f];\n' % (`s`,`s`,n,n)
        gr += "# event nodes\n"
        for e in el:
            n,l = el[e]; n = n = 1+float(n-mine)/(maxe-mine)
            gr += '"evt.%s" [label = "%s", shape=circle, fillcolor="#00FFFF", style=filled, fixedsize=1, height=%.2f, width=%.2f];\n' % (`e`,`e`,n,n)
        for d in dl:
            n = dl[d]; n = n = 1+float(n-mind)/(maxd-mind)
            gr += '"dst.%s" [label = "%s", shape=triangle, fillcolor="#0000ff", style=filled, fixedsize=1, height=%.2f, width=%.2f];\n' % (`d`,`d`,n,n)

        gr += "###\n"
        for s in sl:
            n,l = sl[s]
            for e in l:
                gr += ' "src.%s" -> "evt.%s";\n' % (`s`,`e`) 
        for e in el:
            n,l = el[e]
            for d in l:
                gr += ' "evt.%s" -> "dst.%s";\n' % (`e`,`d`) 
            
        gr += "}"
        return do_graph(gr, **kargs)


    def _dump_document(self, **kargs):
        import pyx
        d = pyx.document.document()
        l = len(self.res)
        for i in range(len(self.res)):
            elt = self.res[i]
            c = self._elt2pkt(elt).canvas_dump(**kargs)
            cbb = c.bbox()
            c.text(cbb.left(),cbb.top()+1,r"\font\cmssfont=cmss12\cmssfont{Frame %i/%i}" % (i,l),[pyx.text.size.LARGE])
            if conf.verb >= 2:
                os.write(1,".")
            d.append(pyx.document.page(c, paperformat=pyx.document.paperformat.A4,
                                       margin=1*pyx.unit.t_cm,
                                       fittosize=1))
        return d
                     
                 

    def psdump(self, filename = None, **kargs):
        """Creates a multipage poscript file with a psdump of every packet
        filename: name of the file to write to. If empty, a temporary file is used and
                  conf.prog.psreader is called"""
        d = self._dump_document(**kargs)
        if filename is None:
            filename = get_temp_file(autoext=".ps")
            d.writePSfile(filename)
            subprocess.Popen([conf.prog.psreader, filename+".ps"])
        else:
            d.writePSfile(filename)
        print
        
    def pdfdump(self, filename = None, **kargs):
        """Creates a PDF file with a psdump of every packet
        filename: name of the file to write to. If empty, a temporary file is used and
                  conf.prog.pdfreader is called"""
        d = self._dump_document(**kargs)
        if filename is None:
            filename = get_temp_file(autoext=".pdf")
            d.writePDFfile(filename)
            subprocess.Popen([conf.prog.pdfreader, filename+".pdf"])
        else:
            d.writePDFfile(filename)
        print

    def sr(self,multi=0):
        """sr([multi=1]) -> (SndRcvList, PacketList)
        Matches packets in the list and return ( (matched couples), (unmatched packets) )"""
        remain = self.res[:]
        sr = []
        i = 0
        while i < len(remain):
            s = remain[i]
            j = i
            while j < len(remain)-1:
                j += 1
                r = remain[j]
                if r.answers(s):
                    sr.append((s,r))
                    if multi:
                        remain[i]._answered=1
                        remain[j]._answered=2
                        continue
                    del(remain[j])
                    del(remain[i])
                    i -= 1
                    break
            i += 1
        if multi:
            remain = filter(lambda x:not hasattr(x,"_answered"), remain)
        return SndRcvList(sr),PacketList(remain)

    def sessions(self, session_extractor=None):
        if session_extractor is None:
            def session_extractor(p):
                sess = "Other"
                if 'Ether' in p:
                    if 'IP' in p:
                        if 'TCP' in p:
                            sess = p.sprintf("TCP %IP.src%:%r,TCP.sport% > %IP.dst%:%r,TCP.dport%")
                        elif 'UDP' in p:
                            sess = p.sprintf("UDP %IP.src%:%r,UDP.sport% > %IP.dst%:%r,UDP.dport%")
                        elif 'ICMP' in p:
                            sess = p.sprintf("ICMP %IP.src% > %IP.dst% type=%r,ICMP.type% code=%r,ICMP.code% id=%ICMP.id%")
                        else:
                            sess = p.sprintf("IP %IP.src% > %IP.dst% proto=%IP.proto%")
                    elif 'ARP' in p:
                        sess = p.sprintf("ARP %ARP.psrc% > %ARP.pdst%")
                    else:
                        sess = p.sprintf("Ethernet type=%04xr,Ether.type%")
                return sess
        sessions = defaultdict(self.__class__)
        for p in self.res:
            sess = session_extractor(self._elt2pkt(p))
            sessions[sess].append(p)
        return dict(sessions)
    
    def replace(self, *args, **kargs):
        """
        lst.replace(<field>,[<oldvalue>,]<newvalue>)
        lst.replace( (fld,[ov],nv),(fld,[ov,]nv),...)
          if ov is None, all values are replaced
        ex:
          lst.replace( IP.src, "192.168.1.1", "10.0.0.1" )
          lst.replace( IP.ttl, 64 )
          lst.replace( (IP.ttl, 64), (TCP.sport, 666, 777), )
        """
        delete_checksums = kargs.get("delete_checksums",False)
        x=PacketList(name="Replaced %s" % self.listname)
        if type(args[0]) is not tuple:
            args = (args,)
        for p in self.res:
            p = self._elt2pkt(p)
            copied = False
            for scheme in args:
                fld = scheme[0]
                old = scheme[1] # not used if len(scheme) == 2
                new = scheme[-1]
                for o in fld.owners:
                    if o in p:
                        if len(scheme) == 2 or p[o].getfieldval(fld.name) == old:
                            if not copied:
                                p = p.copy()
                                if delete_checksums:
                                    p.delete_checksums()
                                copied = True
                            setattr(p[o], fld.name, new)
            x.append(p)
        return x
                
            
        
    
        


class SndRcvList(PacketList):
    def __init__(self, res=None, name="Results", stats=None):
        PacketList.__init__(self, res, name, stats)
    def _elt2pkt(self, elt):
        return elt[1]
    def _elt2sum(self, elt):
        return "%s ==> %s" % (elt[0].summary(),elt[1].summary()) 



    

        
                                                                               

########NEW FILE########
__FILENAME__ = pton_ntop
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Convert IPv6 addresses between textual representation and binary.

These functions are missing when python is compiled
without IPv6 support, on Windows for instance.
"""

import socket,struct

def inet_pton(af, addr):
    """Convert an IP address from text representation into binary form"""
    if af == socket.AF_INET:
        return inet_aton(addr)
    elif af == socket.AF_INET6:
        # IPv6: The use of "::" indicates one or more groups of 16 bits of zeros.
        # We deal with this form of wildcard using a special marker. 
        JOKER = "*"
        while "::" in addr:
            addr = addr.replace("::", ":" + JOKER + ":")
        joker_pos = None 
        
        # The last part of an IPv6 address can be an IPv4 address
        ipv4_addr = None
        if "." in addr:
            ipv4_addr = addr.split(":")[-1]
           
        result = ""
        parts = addr.split(":")
        for part in parts:
            if part == JOKER:
                # Wildcard is only allowed once
                if joker_pos is None:
                   joker_pos = len(result)
                else:
                   raise Exception("Illegal syntax for IP address")
            elif part == ipv4_addr: # FIXME: Make sure IPv4 can only be last part
                # FIXME: inet_aton allows IPv4 addresses with less than 4 octets 
                result += socket.inet_aton(ipv4_addr)
            else:
                # Each part must be 16bit. Add missing zeroes before decoding. 
                try:
                    result += part.rjust(4, "0").decode("hex")
                except TypeError:
                    raise Exception("Illegal syntax for IP address")
                    
        # If there's a wildcard, fill up with zeros to reach 128bit (16 bytes) 
        if JOKER in addr:
            result = (result[:joker_pos] + "\x00" * (16 - len(result))
                      + result[joker_pos:])
    
        if len(result) != 16:
            raise Exception("Illegal syntax for IP address")
        return result 
    else:
        raise Exception("Address family not supported")


def inet_ntop(af, addr):
    """Convert an IP address from binary form into text represenation"""
    if af == socket.AF_INET:
        return inet_ntoa(addr)
    elif af == socket.AF_INET6:
        # IPv6 addresses have 128bits (16 bytes)
        if len(addr) != 16:
            raise Exception("Illegal syntax for IP address")
        parts = []
        for left in [0, 2, 4, 6, 8, 10, 12, 14]:
            try: 
                value = struct.unpack("!H", addr[left:left+2])[0]
                hexstr = hex(value)[2:]
            except TypeError:
                raise Exception("Illegal syntax for IP address")
            parts.append(hexstr.lstrip("0").lower())
        result = ":".join(parts)
        while ":::" in result:
            result = result.replace(":::", "::")
        # Leaving out leading and trailing zeros is only allowed with ::
        if result.endswith(":") and not result.endswith("::"):
            result = result + "0"
        if result.startswith(":") and not result.startswith("::"):
            result = "0" + result
        return result
    else:
        raise Exception("Address family not supported yet")        

########NEW FILE########
__FILENAME__ = route
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Routing and handling of network interfaces.
"""

import socket
from arch import read_routes,get_if_addr,LOOPBACK_NAME
from utils import atol,ltoa,itom
from config import conf
from error import Scapy_Exception,warning

##############################
## Routing/Interfaces stuff ##
##############################

class Route:
    def __init__(self):
        self.resync()
        self.s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cache = {}

    def invalidate_cache(self):
        self.cache = {}

    def resync(self):
        self.invalidate_cache()
        self.routes = read_routes()

    def __repr__(self):
        rt = "Network         Netmask         Gateway         Iface           Output IP\n"
        for net,msk,gw,iface,addr in self.routes:
            rt += "%-15s %-15s %-15s %-15s %-15s\n" % (ltoa(net),
                                              ltoa(msk),
                                              gw,
                                              iface,
                                              addr)
        return rt

    def make_route(self, host=None, net=None, gw=None, dev=None):
        if host is not None:
            thenet,msk = host,32
        elif net is not None:
            thenet,msk = net.split("/")
            msk = int(msk)
        else:
            raise Scapy_Exception("make_route: Incorrect parameters. You should specify a host or a net")
        if gw is None:
            gw="0.0.0.0"
        if dev is None:
            if gw:
                nhop = gw
            else:
                nhop = thenet
            dev,ifaddr,x = self.route(nhop)
        else:
            ifaddr = get_if_addr(dev)
        return (atol(thenet), itom(msk), gw, dev, ifaddr)

    def add(self, *args, **kargs):
        """Ex:
        add(net="192.168.1.0/24",gw="1.2.3.4")
        """
        self.invalidate_cache()
        self.routes.append(self.make_route(*args,**kargs))

        
    def delt(self,  *args, **kargs):
        """delt(host|net, gw|dev)"""
        self.invalidate_cache()
        route = self.make_route(*args,**kargs)
        try:
            i=self.routes.index(route)
            del(self.routes[i])
        except ValueError:
            warning("no matching route found")
             
    def ifchange(self, iff, addr):
        self.invalidate_cache()
        the_addr,the_msk = (addr.split("/")+["32"])[:2]
        the_msk = itom(int(the_msk))
        the_rawaddr = atol(the_addr)
        the_net = the_rawaddr & the_msk
        
        
        for i in range(len(self.routes)):
            net,msk,gw,iface,addr = self.routes[i]
            if iface != iff:
                continue
            if gw == '0.0.0.0':
                self.routes[i] = (the_net,the_msk,gw,iface,the_addr)
            else:
                self.routes[i] = (net,msk,gw,iface,the_addr)
        conf.netcache.flush()
        
                

    def ifdel(self, iff):
        self.invalidate_cache()
        new_routes=[]
        for rt in self.routes:
            if rt[3] != iff:
                new_routes.append(rt)
        self.routes=new_routes
        
    def ifadd(self, iff, addr):
        self.invalidate_cache()
        the_addr,the_msk = (addr.split("/")+["32"])[:2]
        the_msk = itom(int(the_msk))
        the_rawaddr = atol(the_addr)
        the_net = the_rawaddr & the_msk
        self.routes.append((the_net,the_msk,'0.0.0.0',iff,the_addr))


    def route(self,dest,verbose=None):
        if type(dest) is list and dest:
            dest = dest[0]
        if dest in self.cache:
            return self.cache[dest]
        if verbose is None:
            verbose=conf.verb
        # Transform "192.168.*.1-5" to one IP of the set
        dst = dest.split("/")[0]
        dst = dst.replace("*","0") 
        while 1:
            l = dst.find("-")
            if l < 0:
                break
            m = (dst[l:]+".").find(".")
            dst = dst[:l]+dst[l+m:]

            
        dst = atol(dst)
        pathes=[]
        for d,m,gw,i,a in self.routes:
            aa = atol(a)
            if aa == dst:
                pathes.append((0xffffffffL,(LOOPBACK_NAME,a,"0.0.0.0")))
            if (dst & m) == (d & m):
                pathes.append((m,(i,a,gw)))
        if not pathes:
            if verbose:
                warning("No route found (no default route?)")
            return LOOPBACK_NAME,"0.0.0.0","0.0.0.0" #XXX linux specific!
        # Choose the more specific route (greatest netmask).
        # XXX: we don't care about metrics
        pathes.sort()
        ret = pathes[-1][1]
        self.cache[dest] = ret
        return ret
            
    def get_if_bcast(self, iff):
        for net, msk, gw, iface, addr in self.routes:
            if (iff == iface and net != 0L):
                bcast = atol(addr)|(~msk&0xffffffffL); # FIXME: check error in atol()
                return ltoa(bcast);
        warning("No broadcast address found for iface %s\n" % iff);

conf.route=Route()

#XXX use "with"
_betteriface = conf.route.route("0.0.0.0", verbose=0)[0]
if _betteriface != LOOPBACK_NAME:
    conf.iface = _betteriface
del(_betteriface)

########NEW FILE########
__FILENAME__ = route6
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

## Copyright (C) 2005  Guillaume Valadon <guedou@hongo.wide.ad.jp>
##                     Arnaud Ebalard <arnaud.ebalard@eads.net>

"""
Routing and network interface handling for IPv6.
"""

#############################################################################
#############################################################################
###                      Routing/Interfaces stuff                         ###
#############################################################################
#############################################################################

import socket
from config import conf
from utils6 import *
from arch import *


class Route6:

    def __init__(self):
        self.invalidate_cache()
        self.resync()

    def invalidate_cache(self):
        self.cache = {}

    def flush(self):
        self.invalidate_cache()
        self.routes = []

    def resync(self):
        # TODO : At the moment, resync will drop existing Teredo routes
        #        if any. Change that ...
        self.invalidate_cache()
	self.routes = read_routes6()
	if self.routes == []:
	     log_loading.info("No IPv6 support in kernel")
        
    def __repr__(self):
        rtlst = [('Destination', 'Next Hop', "iface", "src candidates")]

        for net,msk,gw,iface,cset in self.routes:
	    rtlst.append(('%s/%i'% (net,msk), gw, iface, ", ".join(cset)))

        colwidth = map(lambda x: max(map(lambda y: len(y), x)), apply(zip, rtlst))
        fmt = "  ".join(map(lambda x: "%%-%ds"%x, colwidth))
        rt = "\n".join(map(lambda x: fmt % x, rtlst))

        return rt


    # Unlike Scapy's Route.make_route() function, we do not have 'host' and 'net'
    # parameters. We only have a 'dst' parameter that accepts 'prefix' and 
    # 'prefix/prefixlen' values.
    # WARNING: Providing a specific device will at the moment not work correctly.
    def make_route(self, dst, gw=None, dev=None):
        """Internal function : create a route for 'dst' via 'gw'.
        """
        prefix, plen = (dst.split("/")+["128"])[:2]
        plen = int(plen)

        if gw is None:
            gw = "::"
        if dev is None:
            dev, ifaddr, x = self.route(gw)
        else:
            # TODO: do better than that
            # replace that unique address by the list of all addresses
            lifaddr = in6_getifaddr()             
            devaddrs = filter(lambda x: x[2] == dev, lifaddr)
            ifaddr = construct_source_candidate_set(prefix, plen, devaddrs, LOOPBACK_NAME)

        return (prefix, plen, gw, dev, ifaddr)

    
    def add(self, *args, **kargs):
        """Ex:
        add(dst="2001:db8:cafe:f000::/56")
        add(dst="2001:db8:cafe:f000::/56", gw="2001:db8:cafe::1")
        add(dst="2001:db8:cafe:f000::/64", gw="2001:db8:cafe::1", dev="eth0")
        """
        self.invalidate_cache()
        self.routes.append(self.make_route(*args, **kargs))


    def delt(self, dst, gw=None):
        """ Ex: 
        delt(dst="::/0") 
        delt(dst="2001:db8:cafe:f000::/56") 
        delt(dst="2001:db8:cafe:f000::/56", gw="2001:db8:deca::1") 
        """
        tmp = dst+"/128"
        dst, plen = tmp.split('/')[:2]
        dst = in6_ptop(dst)
        plen = int(plen)
        l = filter(lambda x: in6_ptop(x[0]) == dst and x[1] == plen, self.routes)
        if gw:
            gw = in6_ptop(gw)
            l = filter(lambda x: in6_ptop(x[0]) == gw, self.routes)
        if len(l) == 0:
            warning("No matching route found")
        elif len(l) > 1:
            warning("Found more than one match. Aborting.")
        else:
            i=self.routes.index(l[0])
            self.invalidate_cache()
            del(self.routes[i])
        
    def ifchange(self, iff, addr):
        the_addr, the_plen = (addr.split("/")+["128"])[:2]
        the_plen = int(the_plen)

        naddr = inet_pton(socket.AF_INET6, the_addr)
        nmask = in6_cidr2mask(the_plen)
        the_net = inet_ntop(socket.AF_INET6, in6_and(nmask,naddr))
        
        for i in range(len(self.routes)):
            net,plen,gw,iface,addr = self.routes[i]
            if iface != iff:
                continue
            if gw == '::':
                self.routes[i] = (the_net,the_plen,gw,iface,the_addr)
            else:
                self.routes[i] = (net,the_plen,gw,iface,the_addr)
        self.invalidate_cache()
        ip6_neigh_cache.flush()

    def ifdel(self, iff):
        """ removes all route entries that uses 'iff' interface. """
        new_routes=[]
        for rt in self.routes:
            if rt[3] != iff:
                new_routes.append(rt)
        self.invalidate_cache()
        self.routes = new_routes


    def ifadd(self, iff, addr):
        """
        Add an interface 'iff' with provided address into routing table.
        
        Ex: ifadd('eth0', '2001:bd8:cafe:1::1/64') will add following entry into 
            Scapy6 internal routing table:

            Destination           Next Hop  iface  Def src @
            2001:bd8:cafe:1::/64  ::        eth0   2001:bd8:cafe:1::1

            prefix length value can be omitted. In that case, a value of 128
            will be used.
        """
        addr, plen = (addr.split("/")+["128"])[:2]
        addr = in6_ptop(addr)
        plen = int(plen)
        naddr = inet_pton(socket.AF_INET6, addr)
        nmask = in6_cidr2mask(plen)
        prefix = inet_ntop(socket.AF_INET6, in6_and(nmask,naddr))
        self.invalidate_cache()
        self.routes.append((prefix,plen,'::',iff,[addr]))

    def route(self, dst, dev=None):
        """
        Provide best route to IPv6 destination address, based on Scapy6 
        internal routing table content.

        When a set of address is passed (e.g. 2001:db8:cafe:*::1-5) an address
        of the set is used. Be aware of that behavior when using wildcards in
        upper parts of addresses !

        If 'dst' parameter is a FQDN, name resolution is performed and result
        is used.

        if optional 'dev' parameter is provided a specific interface, filtering
        is performed to limit search to route associated to that interface.
        """
        # Transform "2001:db8:cafe:*::1-5:0/120" to one IPv6 address of the set
        dst = dst.split("/")[0]
        savedst = dst # In case following inet_pton() fails 
        dst = dst.replace("*","0")
        l = dst.find("-")
        while l >= 0:
            m = (dst[l:]+":").find(":")
            dst = dst[:l]+dst[l+m:]
            l = dst.find("-")
            
        try:
            inet_pton(socket.AF_INET6, dst)
        except socket.error:
            dst = socket.getaddrinfo(savedst, None, socket.AF_INET6)[0][-1][0]
            # TODO : Check if name resolution went well

        # Deal with dev-specific request for cache search
        k = dst
        if dev is not None:
            k = dst + "%%" + dev
        if k in self.cache:
            return self.cache[k]

        pathes = []

        # TODO : review all kinds of addresses (scope and *cast) to see
        #        if we are able to cope with everything possible. I'm convinced 
        #        it's not the case.
        # -- arnaud
        for p, plen, gw, iface, cset in self.routes:
            if dev is not None and iface != dev:
                continue
            if in6_isincluded(dst, p, plen):
                pathes.append((plen, (iface, cset, gw)))
            elif (in6_ismlladdr(dst) and in6_islladdr(p) and in6_islladdr(cset[0])):
                pathes.append((plen, (iface, cset, gw)))
                
        if not pathes:
            warning("No route found for IPv6 destination %s (no default route?)" % dst)
            return (LOOPBACK_NAME, "::", "::") # XXX Linux specific

        # Sort with longest prefix first
        pathes.sort(reverse=True)

        best_plen = pathes[0][0]
        pathes = filter(lambda x: x[0] == best_plen, pathes)

        res = []
        for p in pathes: # Here we select best source address for every route
            tmp = p[1]
            srcaddr = get_source_addr_from_candidate_set(dst, p[1][1])
            if srcaddr is not None:
                res.append((p[0], (tmp[0], srcaddr, tmp[2])))

        # Symptom  : 2 routes with same weight (our weight is plen)
        # Solution : 
        #  - dst is unicast global. Check if it is 6to4 and we have a source 
        #    6to4 address in those available
        #  - dst is link local (unicast or multicast) and multiple output
        #    interfaces are available. Take main one (conf.iface6)
        #  - if none of the previous or ambiguity persists, be lazy and keep
        #    first one
        #  XXX TODO : in a _near_ future, include metric in the game

        if len(res) > 1:
            tmp = []
            if in6_isgladdr(dst) and in6_isaddr6to4(dst):
                # TODO : see if taking the longest match between dst and
                #        every source addresses would provide better results
                tmp = filter(lambda x: in6_isaddr6to4(x[1][1]), res)
            elif in6_ismaddr(dst) or in6_islladdr(dst):
                # TODO : I'm sure we are not covering all addresses. Check that
                tmp = filter(lambda x: x[1][0] == conf.iface6, res)

            if tmp:
                res = tmp
                
        # Fill the cache (including dev-specific request)
        k = dst
        if dev is not None:
            k = dst + "%%" + dev
        self.cache[k] = res[0][1]

        return res[0][1]

conf.route6 = Route6()

_res = conf.route6.route("::/0")
if _res:
    iff, gw, addr = _res
    conf.iface6 = iff
del(_res)


########NEW FILE########
__FILENAME__ = sendrecv
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Functions to send and receive packets.
"""

import cPickle,os,sys,time,subprocess
from select import select
from data import *
import arch
from config import conf
from packet import Gen
from utils import warning,get_temp_file,PcapReader
import plist
from error import log_runtime,log_interactive
from base_classes import SetGen

#################
## Debug class ##
#################

class debug:
    recv=[]
    sent=[]
    match=[]


####################
## Send / Receive ##
####################




def sndrcv(pks, pkt, timeout = None, inter = 0, verbose=None, chainCC=0, retry=0, multi=0):
    if not isinstance(pkt, Gen):
        pkt = SetGen(pkt)
        
    if verbose is None:
        verbose = conf.verb
    debug.recv = plist.PacketList([],"Unanswered")
    debug.sent = plist.PacketList([],"Sent")
    debug.match = plist.SndRcvList([])
    nbrecv=0
    ans = []
    # do it here to fix random fields, so that parent and child have the same
    all_stimuli = tobesent = [p for p in pkt]
    notans = len(tobesent)

    hsent={}
    for i in tobesent:
        h = i.hashret()
        if h in hsent:
            hsent[h].append(i)
        else:
            hsent[h] = [i]
    if retry < 0:
        retry = -retry
        autostop=retry
    else:
        autostop=0


    while retry >= 0:
        found=0
    
        if timeout < 0:
            timeout = None
            
        rdpipe,wrpipe = os.pipe()
        rdpipe=os.fdopen(rdpipe)
        wrpipe=os.fdopen(wrpipe,"w")

        pid=1
        try:
            pid = os.fork()
            if pid == 0:
                try:
                    sys.stdin.close()
                    rdpipe.close()
                    try:
                        i = 0
                        if verbose:
                            print "Begin emission:"
                        for p in tobesent:
                            pks.send(p)
                            i += 1
                            time.sleep(inter)
                        if verbose:
                            print "Finished to send %i packets." % i
                    except SystemExit:
                        pass
                    except KeyboardInterrupt:
                        pass
                    except:
                        log_runtime.exception("--- Error in child %i" % os.getpid())
                        log_runtime.info("--- Error in child %i" % os.getpid())
                finally:
                    try:
                        os.setpgrp() # Chance process group to avoid ctrl-C
                        sent_times = [p.sent_time for p in all_stimuli if p.sent_time]
                        cPickle.dump( (conf.netcache,sent_times), wrpipe )
                        wrpipe.close()
                    except:
                        pass
            elif pid < 0:
                log_runtime.error("fork error")
            else:
                wrpipe.close()
                stoptime = 0
                remaintime = None
                inmask = [rdpipe,pks]
                try:
                    try:
                        while 1:
                            if stoptime:
                                remaintime = stoptime-time.time()
                                if remaintime <= 0:
                                    break
                            r = None
                            if arch.FREEBSD or arch.DARWIN:
                                inp, out, err = select(inmask,[],[], 0.05)
                                if len(inp) == 0 or pks in inp:
                                    r = pks.nonblock_recv()
                            else:
                                inp, out, err = select(inmask,[],[], remaintime)
                                if len(inp) == 0:
                                    break
                                if pks in inp:
                                    r = pks.recv(MTU)
                            if rdpipe in inp:
                                if timeout:
                                    stoptime = time.time()+timeout
                                del(inmask[inmask.index(rdpipe)])
                            if r is None:
                                continue
                            ok = 0
                            h = r.hashret()
                            if h in hsent:
                                hlst = hsent[h]
                                for i in range(len(hlst)):
                                    if r.answers(hlst[i]):
                                        ans.append((hlst[i],r))
                                        if verbose > 1:
                                            os.write(1, "*")
                                        ok = 1                                
                                        if not multi:
                                            del(hlst[i])
                                            notans -= 1;
                                        else:
                                            if not hasattr(hlst[i], '_answered'):
                                                notans -= 1;
                                            hlst[i]._answered = 1;
                                        break
                            if notans == 0 and not multi:
                                break
                            if not ok:
                                if verbose > 1:
                                    os.write(1, ".")
                                nbrecv += 1
                                if conf.debug_match:
                                    debug.recv.append(r)
                    except KeyboardInterrupt:
                        if chainCC:
                            raise
                finally:
                    try:
                        nc,sent_times = cPickle.load(rdpipe)
                    except EOFError:
                        warning("Child died unexpectedly. Packets may have not been sent %i"%os.getpid())
                    else:
                        conf.netcache.update(nc)
                        for p,t in zip(all_stimuli, sent_times):
                            p.sent_time = t
                    os.waitpid(pid,0)
        finally:
            if pid == 0:
                os._exit(0)

        remain = reduce(list.__add__, hsent.values(), [])
        if multi:
            remain = filter(lambda p: not hasattr(p, '_answered'), remain);
            
        if autostop and len(remain) > 0 and len(remain) != len(tobesent):
            retry = autostop
            
        tobesent = remain
        if len(tobesent) == 0:
            break
        retry -= 1
        
    if conf.debug_match:
        debug.sent=plist.PacketList(remain[:],"Sent")
        debug.match=plist.SndRcvList(ans[:])

    #clean the ans list to delete the field _answered
    if (multi):
        for s,r in ans:
            if hasattr(s, '_answered'):
                del(s._answered)
    
    if verbose:
        print "\nReceived %i packets, got %i answers, remaining %i packets" % (nbrecv+len(ans), len(ans), notans)
    return plist.SndRcvList(ans),plist.PacketList(remain,"Unanswered")


def __gen_send(s, x, inter=0, loop=0, count=None, verbose=None, realtime=None, *args, **kargs):
    if type(x) is str:
        x = Raw(load=x)
    if not isinstance(x, Gen):
        x = SetGen(x)
    if verbose is None:
        verbose = conf.verb
    n = 0
    if count is not None:
        loop = -count
    elif not loop:
        loop=-1
    dt0 = None
    try:
        while loop:
            for p in x:
                if realtime:
                    ct = time.time()
                    if dt0:
                        st = dt0+p.time-ct
                        if st > 0:
                            time.sleep(st)
                    else:
                        dt0 = ct-p.time 
                s.send(p)
                n += 1
                if verbose:
                    os.write(1,".")
                time.sleep(inter)
            if loop < 0:
                loop += 1
    except KeyboardInterrupt:
        pass
    s.close()
    if verbose:
        print "\nSent %i packets." % n
        
@conf.commands.register
def send(x, inter=0, loop=0, count=None, verbose=None, realtime=None, *args, **kargs):
    """Send packets at layer 3
send(packets, [inter=0], [loop=0], [verbose=conf.verb]) -> None"""
    __gen_send(conf.L3socket(*args, **kargs), x, inter=inter, loop=loop, count=count,verbose=verbose, realtime=realtime)

@conf.commands.register
def sendp(x, inter=0, loop=0, iface=None, iface_hint=None, count=None, verbose=None, realtime=None, *args, **kargs):
    """Send packets at layer 2
sendp(packets, [inter=0], [loop=0], [verbose=conf.verb]) -> None"""
    if iface is None and iface_hint is not None:
        iface = conf.route.route(iface_hint)[0]
    __gen_send(conf.L2socket(iface=iface, *args, **kargs), x, inter=inter, loop=loop, count=count, verbose=verbose, realtime=realtime)

@conf.commands.register
def sendpfast(x, pps=None, mbps=None, realtime=None, loop=0, file_cache=False, iface=None):
    """Send packets at layer 2 using tcpreplay for performance
    pps:  packets per second
    mpbs: MBits per second
    realtime: use packet's timestamp, bending time with realtime value
    loop: number of times to process the packet list
    file_cache: cache packets in RAM instead of reading from disk at each iteration
    iface: output interface """
    if iface is None:
        iface = conf.iface
    argv = [conf.prog.tcpreplay, "--intf1=%s" % iface ]
    if pps is not None:
        argv.append("--pps=%i" % pps)
    elif mbps is not None:
        argv.append("--mbps=%i" % mbps)
    elif realtime is not None:
        argv.append("--multiplier=%i" % realtime)
    else:
        argv.append("--topspeed")

    if loop:
        argv.append("--loop=%i" % loop)
        if file_cache:
            argv.append("--enable-file-cache")

    f = get_temp_file()
    argv.append(f)
    wrpcap(f, x)
    try:
        subprocess.check_call(argv)
    except KeyboardInterrupt:
        log_interactive.info("Interrupted by user")
    except Exception,e:
        log_interactive.error("while trying to exec [%s]: %s" % (argv[0],e))
    finally:
        os.unlink(f)

        

        
    
@conf.commands.register
def sr(x,filter=None, iface=None, nofilter=0, *args,**kargs):
    """Send and receive packets at layer 3
nofilter: put 1 to avoid use of bpf filters
retry:    if positive, how many times to resend unanswered packets
          if negative, how many times to retry when no more packets are answered
timeout:  how much time to wait after the last packet has been sent
verbose:  set verbosity level
multi:    whether to accept multiple answers for the same stimulus
filter:   provide a BPF filter
iface:    listen answers only on the given interface"""
    if not kargs.has_key("timeout"):
        kargs["timeout"] = -1
    s = conf.L3socket(filter=filter, iface=iface, nofilter=nofilter)
    a,b=sndrcv(s,x,*args,**kargs)
    s.close()
    return a,b

@conf.commands.register
def sr1(x,filter=None,iface=None, nofilter=0, *args,**kargs):
    """Send packets at layer 3 and return only the first answer
nofilter: put 1 to avoid use of bpf filters
retry:    if positive, how many times to resend unanswered packets
          if negative, how many times to retry when no more packets are answered
timeout:  how much time to wait after the last packet has been sent
verbose:  set verbosity level
multi:    whether to accept multiple answers for the same stimulus
filter:   provide a BPF filter
iface:    listen answers only on the given interface"""
    if not kargs.has_key("timeout"):
        kargs["timeout"] = -1
    s=conf.L3socket(filter=filter, nofilter=nofilter, iface=iface)
    a,b=sndrcv(s,x,*args,**kargs)
    s.close()
    if len(a) > 0:
        return a[0][1]
    else:
        return None

@conf.commands.register
def srp(x,iface=None, iface_hint=None, filter=None, nofilter=0, type=ETH_P_ALL, *args,**kargs):
    """Send and receive packets at layer 2
nofilter: put 1 to avoid use of bpf filters
retry:    if positive, how many times to resend unanswered packets
          if negative, how many times to retry when no more packets are answered
timeout:  how much time to wait after the last packet has been sent
verbose:  set verbosity level
multi:    whether to accept multiple answers for the same stimulus
filter:   provide a BPF filter
iface:    work only on the given interface"""
    if not kargs.has_key("timeout"):
        kargs["timeout"] = -1
    if iface is None and iface_hint is not None:
        iface = conf.route.route(iface_hint)[0]
    s = conf.L2socket(iface=iface, filter=filter, nofilter=nofilter, type=type)
    a,b=sndrcv(s ,x,*args,**kargs)
    s.close()
    return a,b

@conf.commands.register
def srp1(*args,**kargs):
    """Send and receive packets at layer 2 and return only the first answer
nofilter: put 1 to avoid use of bpf filters
retry:    if positive, how many times to resend unanswered packets
          if negative, how many times to retry when no more packets are answered
timeout:  how much time to wait after the last packet has been sent
verbose:  set verbosity level
multi:    whether to accept multiple answers for the same stimulus
filter:   provide a BPF filter
iface:    work only on the given interface"""
    if not kargs.has_key("timeout"):
        kargs["timeout"] = -1
    a,b=srp(*args,**kargs)
    if len(a) > 0:
        return a[0][1]
    else:
        return None

def __sr_loop(srfunc, pkts, prn=lambda x:x[1].summary(), prnfail=lambda x:x.summary(), inter=1, timeout=None, count=None, verbose=None, store=1, *args, **kargs):
    n = 0
    r = 0
    ct = conf.color_theme
    if verbose is None:
        verbose = conf.verb
    parity = 0
    ans=[]
    unans=[]
    if timeout is None:
        timeout = min(2*inter, 5)
    try:
        while 1:
            parity ^= 1
            col = [ct.even,ct.odd][parity]
            if count is not None:
                if count == 0:
                    break
                count -= 1
            start = time.time()
            print "\rsend...\r",
            res = srfunc(pkts, timeout=timeout, verbose=0, chainCC=1, *args, **kargs)
            n += len(res[0])+len(res[1])
            r += len(res[0])
            if verbose > 1 and prn and len(res[0]) > 0:
                msg = "RECV %i:" % len(res[0])
                print  "\r"+ct.success(msg),
                for p in res[0]:
                    print col(prn(p))
                    print " "*len(msg),
            if verbose > 1 and prnfail and len(res[1]) > 0:
                msg = "fail %i:" % len(res[1])
                print "\r"+ct.fail(msg),
                for p in res[1]:
                    print col(prnfail(p))
                    print " "*len(msg),
            if verbose > 1 and not (prn or prnfail):
                print "recv:%i  fail:%i" % tuple(map(len, res[:2]))
            if store:
                ans += res[0]
                unans += res[1]
            end=time.time()
            if end-start < inter:
                time.sleep(inter+start-end)
    except KeyboardInterrupt:
        pass
 
    if verbose and n>0:
        print ct.normal("\nSent %i packets, received %i packets. %3.1f%% hits." % (n,r,100.0*r/n))
    return plist.SndRcvList(ans),plist.PacketList(unans)

@conf.commands.register
def srloop(pkts, *args, **kargs):
    """Send a packet at layer 3 in loop and print the answer each time
srloop(pkts, [prn], [inter], [count], ...) --> None"""
    return __sr_loop(sr, pkts, *args, **kargs)

@conf.commands.register
def srploop(pkts, *args, **kargs):
    """Send a packet at layer 2 in loop and print the answer each time
srloop(pkts, [prn], [inter], [count], ...) --> None"""
    return __sr_loop(srp, pkts, *args, **kargs)


def sndrcvflood(pks, pkt, prn=lambda (s,r):r.summary(), chainCC=0, store=1, unique=0):
    if not isinstance(pkt, Gen):
        pkt = SetGen(pkt)
    tobesent = [p for p in pkt]
    received = plist.SndRcvList()
    seen = {}

    hsent={}
    for i in tobesent:
        h = i.hashret()
        if h in hsent:
            hsent[h].append(i)
        else:
            hsent[h] = [i]

    def send_in_loop(tobesent):
        while 1:
            for p in tobesent:
                yield p

    packets_to_send = send_in_loop(tobesent)

    ssock = rsock = pks.fileno()

    try:
        while 1:
            readyr,readys,_ = select([rsock],[ssock],[])
            if ssock in readys:
                pks.send(packets_to_send.next())
                
            if rsock in readyr:
                p = pks.recv(MTU)
                if p is None:
                    continue
                h = p.hashret()
                if h in hsent:
                    hlst = hsent[h]
                    for i in hlst:
                        if p.answers(i):
                            res = prn((i,p))
                            if unique:
                                if res in seen:
                                    continue
                                seen[res] = None
                            if res is not None:
                                print res
                            if store:
                                received.append((i,p))
    except KeyboardInterrupt:
        if chainCC:
            raise
    return received

@conf.commands.register
def srflood(x,filter=None, iface=None, nofilter=None, *args,**kargs):
    """Flood and receive packets at layer 3
prn:      function applied to packets received. Ret val is printed if not None
store:    if 1 (default), store answers and return them
unique:   only consider packets whose print 
nofilter: put 1 to avoid use of bpf filters
filter:   provide a BPF filter
iface:    listen answers only on the given interface"""
    s = conf.L3socket(filter=filter, iface=iface, nofilter=nofilter)
    r=sndrcvflood(s,x,*args,**kargs)
    s.close()
    return r

@conf.commands.register
def srpflood(x,filter=None, iface=None, iface_hint=None, nofilter=None, *args,**kargs):
    """Flood and receive packets at layer 2
prn:      function applied to packets received. Ret val is printed if not None
store:    if 1 (default), store answers and return them
unique:   only consider packets whose print 
nofilter: put 1 to avoid use of bpf filters
filter:   provide a BPF filter
iface:    listen answers only on the given interface"""
    if iface is None and iface_hint is not None:
        iface = conf.route.route(iface_hint)[0]    
    s = conf.L2socket(filter=filter, iface=iface, nofilter=nofilter)
    r=sndrcvflood(s,x,*args,**kargs)
    s.close()
    return r

           


@conf.commands.register
def sniff(count=0, store=1, offline=None, prn = None, lfilter=None, L2socket=None, timeout=None,
          opened_socket=None, stop_filter=None, *arg, **karg):
    """Sniff packets
sniff([count=0,] [prn=None,] [store=1,] [offline=None,] [lfilter=None,] + L2ListenSocket args) -> list of packets

  count: number of packets to capture. 0 means infinity
  store: wether to store sniffed packets or discard them
    prn: function to apply to each packet. If something is returned,
         it is displayed. Ex:
         ex: prn = lambda x: x.summary()
lfilter: python function applied to each packet to determine
         if further action may be done
         ex: lfilter = lambda x: x.haslayer(Padding)
offline: pcap file to read packets from, instead of sniffing them
timeout: stop sniffing after a given time (default: None)
L2socket: use the provided L2socket
opened_socket: provide an object ready to use .recv() on
stop_filter: python function applied to each packet to determine
             if we have to stop the capture after this packet
             ex: stop_filter = lambda x: x.haslayer(TCP)
    """
    c = 0
    
    if opened_socket is not None:
        s = opened_socket
    else:
        if offline is None:
            if L2socket is None:
                L2socket = conf.L2listen
            s = L2socket(type=ETH_P_ALL, *arg, **karg)
        else:
            s = PcapReader(offline)

    lst = []
    if timeout is not None:
        stoptime = time.time()+timeout
    remain = None
    while 1:
        try:
            if timeout is not None:
                remain = stoptime-time.time()
                if remain <= 0:
                    break
            sel = select([s],[],[],remain)
            if s in sel[0]:
                p = s.recv(MTU)
                if p is None:
                    break
                if lfilter and not lfilter(p):
                    continue
                if store:
                    lst.append(p)
                c += 1
                if prn:
                    r = prn(p)
                    if r is not None:
                        print r
                if stop_filter and stop_filter(p):
                    break
                if count > 0 and c >= count:
                    break
        except KeyboardInterrupt:
            break
    if opened_socket is None:
        s.close()
    return plist.PacketList(lst,"Sniffed")

@conf.commands.register
def tshark(*args,**kargs):
    """Sniff packets and print them calling pkt.show(), a bit like text wireshark"""
    sniff(prn=lambda x: x.display(),*args,**kargs)


########NEW FILE########
__FILENAME__ = supersocket
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
SuperSocket.
"""

import socket,time
from config import conf
from data import *
from scapy.error import warning

class _SuperSocket_metaclass(type):
    def __repr__(self):
        if self.desc is not None:
            return "<%s: %s>" % (self.__name__,self.desc)
        else:
            return "<%s>" % self.__name__


class SuperSocket:
    __metaclass__ = _SuperSocket_metaclass
    desc = None
    closed=0
    def __init__(self, family=socket.AF_INET,type=socket.SOCK_STREAM, proto=0):
        self.ins = socket.socket(family, type, proto)
        self.outs = self.ins
        self.promisc=None
    def send(self, x):
        sx = str(x)
        x.sent_time = time.time()
        return self.outs.send(sx)
    def recv(self, x=MTU):
        return conf.raw_layer(self.ins.recv(x))
    def fileno(self):
        return self.ins.fileno()
    def close(self):
        if self.closed:
            return
        self.closed=1
        if self.ins != self.outs:
            if self.outs and self.outs.fileno() != -1:
                self.outs.close()
        if self.ins and self.ins.fileno() != -1:
            self.ins.close()
    def sr(self, *args, **kargs):
        return sendrecv.sndrcv(self, *args, **kargs)
    def sr1(self, *args, **kargs):        
        a,b = sendrecv.sndrcv(self, *args, **kargs)
        if len(a) > 0:
            return a[0][1]
        else:
            return None
    def sniff(self, *args, **kargs):
        return sendrecv.sniff(opened_socket=self, *args, **kargs)

class L3RawSocket(SuperSocket):
    desc = "Layer 3 using Raw sockets (PF_INET/SOCK_RAW)"
    def __init__(self, type = ETH_P_IP, filter=None, iface=None, promisc=None, nofilter=0):
        self.outs = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        self.outs.setsockopt(socket.SOL_IP, socket.IP_HDRINCL, 1)
        self.ins = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(type))
        if iface is not None:
            self.ins.bind((iface, type))
    def recv(self, x=MTU):
        pkt, sa_ll = self.ins.recvfrom(x)
        if sa_ll[2] == socket.PACKET_OUTGOING:
            return None
        if sa_ll[3] in conf.l2types:
            cls = conf.l2types[sa_ll[3]]
            lvl = 2
        elif sa_ll[1] in conf.l3types:
            cls = conf.l3types[sa_ll[1]]
            lvl = 3
        else:
            cls = conf.default_l2
            warning("Unable to guess type (interface=%s protocol=%#x family=%i). Using %s" % (sa_ll[0],sa_ll[1],sa_ll[3],cls.name))
            lvl = 3

        try:
            pkt = cls(pkt)
        except KeyboardInterrupt:
            raise
        except:
            if conf.debug_dissector:
                raise
            pkt = conf.raw_layer(pkt)
        if lvl == 2:
            pkt = pkt.payload
            
        if pkt is not None:
            from arch import get_last_packet_timestamp
            pkt.time = get_last_packet_timestamp(self.ins)
        return pkt
    def send(self, x):
        try:
            sx = str(x)
            x.sent_time = time.time()
            self.outs.sendto(sx,(x.dst,0))
        except socket.error,msg:
            log_runtime.error(msg)

class SimpleSocket(SuperSocket):
    desc = "wrapper arround a classic socket"
    def __init__(self, sock):
        self.ins = sock
        self.outs = sock


class StreamSocket(SimpleSocket):
    desc = "transforms a stream socket into a layer 2"
    def __init__(self, sock, basecls=None):
        if basecls is None:
            basecls = conf.raw_layer
        SimpleSocket.__init__(self, sock)
        self.basecls = basecls
        
    def recv(self, x=MTU):
        pkt = self.ins.recv(x, socket.MSG_PEEK)
        x = len(pkt)
        if x == 0:
            raise socket.error((100,"Underlying stream socket tore down"))
        pkt = self.basecls(pkt)
        pad = pkt.getlayer(Padding)
        if pad is not None and pad.underlayer is not None:
            del(pad.underlayer.payload)
        while pad is not None and not isinstance(pad, NoPayload):
            x -= len(pad.load)
            pad = pad.payload
        self.ins.recv(x)
        return pkt
        


if conf.L3socket is None:
    conf.L3socket = L3RawSocket

import sendrecv

########NEW FILE########
__FILENAME__ = themes
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Color themes for the interactive console.
"""

##################
## Color themes ##
##################

class Color:
    normal = "\033[0m"
    black = "\033[30m"
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    purple = "\033[35m"
    cyan = "\033[36m"
    grey = "\033[37m"

    bold = "\033[1m"
    uline = "\033[4m"
    blink = "\033[5m"
    invert = "\033[7m"
        

def create_styler(fmt=None, before="", after="", fmt2="%s"):
    def do_style(val, fmt=fmt, before=before, after=after, fmt2=fmt2):
        if fmt is None:
            if type(val) is not str:
                val = str(val)
        else:
            val = fmt % val
        return fmt2 % (before+val+after)
    return do_style

class ColorTheme:
    def __repr__(self):
        return "<%s>" % self.__class__.__name__
    def __getattr__(self, attr):
        return create_styler()
        

class NoTheme(ColorTheme):
    pass


class AnsiColorTheme(ColorTheme):
    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        s = "style_%s" % attr 
        if s in self.__class__.__dict__:
            before = getattr(self, s)
            after = self.style_normal
        else:
            before = after = ""

        return create_styler(before=before, after=after)
        
        
    style_normal = ""
    style_prompt = ""
    style_punct = ""
    style_id = ""
    style_not_printable = ""
    style_layer_name = ""
    style_field_name = ""
    style_field_value = ""
    style_emph_field_name = ""
    style_emph_field_value = ""
    style_packetlist_name = ""
    style_packetlist_proto = ""
    style_packetlist_value = ""
    style_fail = ""
    style_success = ""
    style_odd = ""
    style_even = ""
    style_opening = ""
    style_active = ""
    style_closed = ""
    style_left = ""
    style_right = ""

class BlackAndWhite(AnsiColorTheme):
    pass

class DefaultTheme(AnsiColorTheme):
    style_normal = Color.normal
    style_prompt = Color.blue+Color.bold
    style_punct = Color.normal
    style_id = Color.blue+Color.bold
    style_not_printable = Color.grey
    style_layer_name = Color.red+Color.bold
    style_field_name = Color.blue
    style_field_value = Color.purple
    style_emph_field_name = Color.blue+Color.uline+Color.bold
    style_emph_field_value = Color.purple+Color.uline+Color.bold
    style_packetlist_name = Color.red+Color.bold
    style_packetlist_proto = Color.blue
    style_packetlist_value = Color.purple
    style_fail = Color.red+Color.bold
    style_success = Color.blue+Color.bold
    style_even = Color.black+Color.bold
    style_odd = Color.black
    style_opening = Color.yellow
    style_active = Color.black
    style_closed = Color.grey
    style_left = Color.blue+Color.invert
    style_right = Color.red+Color.invert
    
class BrightTheme(AnsiColorTheme):
    style_normal = Color.normal
    style_punct = Color.normal
    style_id = Color.yellow+Color.bold
    style_layer_name = Color.red+Color.bold
    style_field_name = Color.yellow+Color.bold
    style_field_value = Color.purple+Color.bold
    style_emph_field_name = Color.yellow+Color.bold
    style_emph_field_value = Color.green+Color.bold
    style_packetlist_name = Color.red+Color.bold
    style_packetlist_proto = Color.yellow+Color.bold
    style_packetlist_value = Color.purple+Color.bold
    style_fail = Color.red+Color.bold
    style_success = Color.blue+Color.bold
    style_even = Color.black+Color.bold
    style_odd = Color.black
    style_left = Color.cyan+Color.invert
    style_right = Color.purple+Color.invert


class RastaTheme(AnsiColorTheme):
    style_normal = Color.normal+Color.green+Color.bold
    style_prompt = Color.yellow+Color.bold
    style_punct = Color.red
    style_id = Color.green+Color.bold
    style_not_printable = Color.green
    style_layer_name = Color.red+Color.bold
    style_field_name = Color.yellow+Color.bold
    style_field_value = Color.green+Color.bold
    style_emph_field_name = Color.green
    style_emph_field_value = Color.green
    style_packetlist_name = Color.red+Color.bold
    style_packetlist_proto = Color.yellow+Color.bold
    style_packetlist_value = Color.green+Color.bold
    style_fail = Color.red
    style_success = Color.red+Color.bold
    style_even = Color.yellow
    style_odd = Color.green
    style_left = Color.yellow+Color.invert
    style_right = Color.red+Color.invert

class ColorOnBlackTheme(AnsiColorTheme):
    """Color theme for black backgrounds"""
    style_normal = Color.normal
    style_prompt = Color.green+Color.bold
    style_punct = Color.normal
    style_id = Color.green
    style_not_printable = Color.black+Color.bold
    style_layer_name = Color.yellow+Color.bold
    style_field_name = Color.cyan
    style_field_value = Color.purple+Color.bold
    style_emph_field_name = Color.cyan+Color.bold
    style_emph_field_value = Color.red+Color.bold
    style_packetlist_name = Color.black+Color.bold
    style_packetlist_proto = Color.yellow+Color.bold
    style_packetlist_value = Color.purple+Color.bold
    style_fail = Color.red+Color.bold
    style_success = Color.green
    style_even = Color.black+Color.bold
    style_odd = Color.grey
    style_opening = Color.yellow
    style_active = Color.grey+Color.bold
    style_closed = Color.black+Color.bold
    style_left = Color.cyan+Color.bold
    style_right = Color.red+Color.bold


class FormatTheme(ColorTheme):
    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        colfmt = self.__class__.__dict__.get("style_%s" % attr, "%s")
        return create_styler(fmt2 = colfmt)       

class LatexTheme(FormatTheme):
    style_prompt = r"\textcolor{blue}{%s}"
    style_not_printable = r"\textcolor{gray}{%s}"
    style_layer_name = r"\textcolor{red}{\bf %s}"
    style_field_name = r"\textcolor{blue}{%s}"
    style_field_value = r"\textcolor{purple}{%s}"
    style_emph_field_name = r"\textcolor{blue}{\underline{%s}}" #ul
    style_emph_field_value = r"\textcolor{purple}{\underline{%s}}" #ul
    style_packetlist_name = r"\textcolor{red}{\bf %s}"
    style_packetlist_proto = r"\textcolor{blue}{%s}"
    style_packetlist_value = r"\textcolor{purple}{%s}"
    style_fail = r"\textcolor{red}{\bf %s}"
    style_success = r"\textcolor{blue}{\bf %s}"
    style_left = r"\textcolor{blue}{%s}"
    style_right = r"\textcolor{red}{%s}"
#    style_even = r"}{\bf "
#    style_odd = ""

class LatexTheme2(FormatTheme):
    style_prompt = r"@`@textcolor@[@blue@]@@[@%s@]@"
    style_not_printable = r"@`@textcolor@[@gray@]@@[@%s@]@"
    style_layer_name = r"@`@textcolor@[@red@]@@[@@`@bfseries@[@@]@%s@]@"
    style_field_name = r"@`@textcolor@[@blue@]@@[@%s@]@"
    style_field_value = r"@`@textcolor@[@purple@]@@[@%s@]@"
    style_emph_field_name = r"@`@textcolor@[@blue@]@@[@@`@underline@[@%s@]@@]@" 
    style_emph_field_value = r"@`@textcolor@[@purple@]@@[@@`@underline@[@%s@]@@]@" 
    style_packetlist_name = r"@`@textcolor@[@red@]@@[@@`@bfseries@[@@]@%s@]@"
    style_packetlist_proto = r"@`@textcolor@[@blue@]@@[@%s@]@"
    style_packetlist_value = r"@`@textcolor@[@purple@]@@[@%s@]@"
    style_fail = r"@`@textcolor@[@red@]@@[@@`@bfseries@[@@]@%s@]@"
    style_success = r"@`@textcolor@[@blue@]@@[@@`@bfserices@[@@]@%s@]@"
    style_even = r"@`@textcolor@[@gray@]@@[@@`@bfseries@[@@]@%s@]@"
#    style_odd = r"@`@textcolor@[@black@]@@[@@`@bfseries@[@@]@%s@]@"
    style_left = r"@`@textcolor@[@blue@]@@[@%s@]@"
    style_right = r"@`@textcolor@[@red@]@@[@%s@]@"

class HTMLTheme(FormatTheme):
    style_prompt = "<span class=prompt>%s</span>"
    style_not_printable = "<span class=not_printable>%s</span>"
    style_layer_name = "<span class=layer_name>%s</span>"
    style_field_name = "<span class=field_name>%s</span>"
    style_field_value = "<span class=field_value>%s</span>"
    style_emph_field_name = "<span class=emph_field_name>%s</span>"
    style_emph_field_value = "<span class=emph_field_value>%s</span>"
    style_packetlist_name = "<span class=packetlist_name>%s</span>"
    style_packetlist_proto = "<span class=packetlist_proto>%s</span>"
    style_packetlist_value = "<span class=packetlist_value>%s</span>"
    style_fail = "<span class=fail>%s</span>"
    style_success = "<span class=success>%s</span>"
    style_even = "<span class=even>%s</span>"
    style_odd = "<span class=odd>%s</span>"
    style_left = "<span class=left>%s</span>"
    style_right = "<span class=right>%s</span>"

class HTMLTheme2(HTMLTheme):
    style_prompt = "#[#span class=prompt#]#%s#[#/span#]#"
    style_not_printable = "#[#span class=not_printable#]#%s#[#/span#]#"
    style_layer_name = "#[#span class=layer_name#]#%s#[#/span#]#"
    style_field_name = "#[#span class=field_name#]#%s#[#/span#]#"
    style_field_value = "#[#span class=field_value#]#%s#[#/span#]#"
    style_emph_field_name = "#[#span class=emph_field_name#]#%s#[#/span#]#"
    style_emph_field_value = "#[#span class=emph_field_value#]#%s#[#/span#]#"
    style_packetlist_name = "#[#span class=packetlist_name#]#%s#[#/span#]#"
    style_packetlist_proto = "#[#span class=packetlist_proto#]#%s#[#/span#]#"
    style_packetlist_value = "#[#span class=packetlist_value#]#%s#[#/span#]#"
    style_fail = "#[#span class=fail#]#%s#[#/span#]#"
    style_success = "#[#span class=success#]#%s#[#/span#]#"
    style_even = "#[#span class=even#]#%s#[#/span#]#"
    style_odd = "#[#span class=odd#]#%s#[#/span#]#"
    style_left = "#[#span class=left#]#%s#[#/span#]#"
    style_right = "#[#span class=right#]#%s#[#/span#]#"


class ColorPrompt:
    __prompt = ">>> "
    def __str__(self):
        try:
            ct = config.conf.color_theme
            if isinstance(ct, AnsiColorTheme):
                ## ^A and ^B delimit invisible caracters for readline to count right
                return "\001%s\002" % ct.prompt("\002"+config.conf.prompt+"\001")
            else:
                return ct.prompt(config.conf.prompt)
        except:
            return self.__prompt


import config

########NEW FILE########
__FILENAME__ = check_asdis
#! /usr/bin/env python

import getopt

def usage():
    print >>sys.stderr,"""Usage: check_asdis -i <pcap_file> [-o <wrong_packets.pcap>]
    -v   increase verbosity
    -d   hexdiff packets that differ
    -z   compress output pcap
    -a   open pcap file in append mode"""

def main(argv):
    PCAP_IN = None
    PCAP_OUT = None
    COMPRESS=False
    APPEND=False
    DIFF=False
    VERBOSE=0
    try:
        opts=getopt.getopt(argv, "hi:o:azdv")
        for opt, parm in opts[0]:
            if opt == "-h":
                usage()
                raise SystemExit
            elif opt == "-i":
                PCAP_IN = parm
            elif opt == "-o":
                PCAP_OUT = parm
            elif opt == "-v":
                VERBOSE += 1
            elif opt == "-d":
                DIFF = True
            elif opt == "-a":
                APPEND = True
            elif opt == "-z":
                COMPRESS = True
                
                
        if PCAP_IN is None:
            raise getopt.GetoptError("Missing pcap file (-i)")
    
    except getopt.GetoptError,e:
        print >>sys.stderr,"ERROR: %s" % e
        raise SystemExit
    
    

    from scapy.config import conf
    from scapy.utils import RawPcapReader,RawPcapWriter,hexdiff
    from scapy.layers import all


    pcap = RawPcapReader(PCAP_IN)
    pcap_out = None
    if PCAP_OUT:
        pcap_out = RawPcapWriter(PCAP_OUT, append=APPEND, gz=COMPRESS, linktype=pcap.linktype)
        pcap_out._write_header(None)

    LLcls = conf.l2types.get(pcap.linktype)
    if LLcls is None:
        print >>sys.stderr," Unknown link type [%i]. Can't test anything!" % pcap.linktype
        raise SystemExit
    
    
    i=-1
    differ=0
    failed=0
    for p1,meta in pcap:
        i += 1
        try:
            p2d = LLcls(p1)
            p2 = str(p2d)
        except KeyboardInterrupt:
            raise
        except Exception,e:
            print "Dissection error on packet %i" % i
            failed += 1
        else:
            if p1 == p2:
                if VERBOSE >= 2:
                    print "Packet %i ok" % i
                continue
            else:
                print "Packet %i differs" % i
                differ += 1
                if VERBOSE >= 1:
                    print repr(p2d)
                if DIFF:
                    hexdiff(p1,p2)
        if pcap_out is not None:
            pcap_out.write(p1)
    i+=1
    correct = i-differ-failed
    print "%i total packets. %i ok, %i differed, %i failed. %.2f%% correct." % (i, correct, differ,
                                                                                failed, i and 100.0*(correct)/i)
    
        
if __name__ == "__main__":
    import sys
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print >>sys.stderr,"Interrupted by user."

########NEW FILE########
__FILENAME__ = UTscapy
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Unit testing infrastructure for Scapy
"""

import sys,getopt,imp
import bz2, base64, os.path, time, traceback, zlib, sha


#### Import tool ####

def import_module(name):
    name = os.path.realpath(name)
    thepath = os.path.dirname(name)
    name = os.path.basename(name)
    if name.endswith(".py"):
        name = name[:-3]
    f,path,desc = imp.find_module(name,[thepath])
    
    try:
        return imp.load_module(name, f, path, desc)
    finally:
        if f:
            f.close()


#### INTERNAL/EXTERNAL FILE EMBEDDING ####

class File:
    def __init__(self, name, URL, local):
        self.name = name
        self.local = local
        self.URL = URL
    def get_local(self):
        return bz2.decompress(base64.decodestring(self.local))
    def get_URL(self):
        return URL
    def write(self, dir):
        if dir:
            dir += "/"
        open(dir+self.name,"w").write(self.get_local())

        
# Embed a base64 encoded bziped version of js and css files
# to work if you can't reach Internet.
class External_Files:
    UTscapy_js = File("UTscapy.js", "http://www.secdev.org/projects/UTscapy/UTscapy.js",
"""QlpoOTFBWSZTWWVijKQAAXxfgERUYOvAChIhBAC/79+qQAH8AFA0poANAMjQAAAG
ABo0NGEZNBo00BhgAaNDRhGTQaNNAYFURJinplGaKbRkJiekzSenqmpA0Gm1LFMp
RUklVQlK9WUTZYpNFI1IiEWEFT09Sfj5uO+qO6S5DQwKIxM92+Zku94wL6V/1KTK
an2c66Ug6SmVKy1ZIrgauxMVLF5xLH0lJRQuKlqLF10iatlTzqvw7S9eS3+h4lu3
GZyMgoOude3NJ1pQy8eo+X96IYZw+ynehsiPj73m0rnvQ3QXZ9BJQiZQYQ5/uNcl
2WOlC5vyQqV/BWsnr2NZYLYXQLDs/Bffk4ZfR4/SH6GfA5Xlek4xHNHqbSsRbREO
gueXo3kcYi94K6hSO3ldD2O/qJXOFqJ8o3TE2aQahxtQpCVUKQMvODHwu2YkaORY
ZC6gihEallcHDIAtRPScBACAJnUggYhLDX6DEko7nC9GvAw5OcEkiyDUbLdiGCzD
aXWMC2DuQ2Y6sGf6NcRuON7QSbhHsPc4KKmZ/xdyRThQkGVijKQ=""")
    UTscapy_css = File("UTscapy.css","http://www.secdev.org/projects/UTscapy/UTscapy.css",
"""QlpoOTFBWSZTWTbBCNEAAE7fgHxwSB//+Cpj2QC//9/6UAR+63dxbNzO3ccmtGEk
pM0m1I9E/Qp6g9Q09TNQ9QDR6gMgAkiBFG9U9TEGRkGgABoABoBmpJkRAaAxD1AN
Gh6gNADQBzAATJgATCYJhDAEYAEiQkwIyJk0n6qenpqeoaMUeo9RgIxp6pX78kfx
Jx4MUhDHKEb2pJAYAelG1cybiZBBDipH8ocxNyHDAqTUxiQmIAEDE3ApIBUUECAT
7Lvlf4xA/sVK0QHkSlYtT0JmErdOjx1v5NONPYSjrIhQnbl1MbG5m+InMYmVAWJp
uklD9cNdmQv2YigxbEtgUrsY2pDDV/qMT2SHnHsViu2rrp2LA01YJIHZqjYCGIQN
sGNobFxAYHLqqMOj9TI2Y4GRpRCUGu82PnMnXUBgDSkTY4EfmygaqvUwbGMbPwyE
220Q4G+sDvw7+6in3CAOS634pcOEAdREUW+QqMjvWvECrGISo1piv3vqubTGOL1c
ssrFnnSfU4T6KSCbPs98HJ2yjWN4i8Bk5WrM/JmELLNeZ4vgMkA4JVQInNnWTUTe
gmMSlJd/b7JuRwiM5RUzXOBTa0e3spO/rsNJiylu0rCxygdRo2koXdSJzmUVjJUm
BOFIkUKq8LrE+oT9h2qUqqUQ25fGV7e7OFkpmZopqUi0WeIBzlXdYY0Zz+WUJUTC
RC+CIPFIYh1RkopswMAop6ZjuZKRqR0WNuV+rfuF5aCXPpxAm0F14tPyhf42zFMT
GJUMxxowJnoauRq4xGQk+2lYFxbQ0FiC43WZSyYLHMuo5NTJ92QLAgs4FgOyZQqQ
xpsGKMA0cIisNeiootpnlWQvkPzNGUTPg8jqkwTvqQLguZLKJudha1hqfBib1IfO
LNChcU6OqF+3wyPKg5Y5oSbSJPAMcRDANwmS2i9oZm6vsD1pLkWtFGbAkEjjCuEU
W1ev1IsF2UVmWYFtJkqLT708ApUBK/ig3rbJWSq7RGQd3sSrOKu3lyKzTBdkXK2a
BGLV5dS1XURdKxaRkMplLLQxsimBYZEAa8KQkYyI+4EagMqycRR7RgwtZFxJSu0T
1q5wS2JG82iETHplbNj8DYo9IkmKzNAiw4FxK8bRfIYvwrbshbEagL11AQJFsqeZ
WeXDoWEx2FMyyZRAB5QyCFnwYtwtWAQmmITY8aIM2SZyRnHH9Wi8+Sr2qyCscFYo
vzM985aHXOHAxQN2UQZbQkUv3D4Vc+lyvalAffv3Tyg4ks3a22kPXiyeCGweviNX
0K8TKasyOhGsVamTUAZBXfQVw1zmdS4rHDnbHgtIjX3DcCt6UIr0BHTYjdV0JbPj
r1APYgXihjQwM2M83AKIhwQQJv/F3JFOFCQNsEI0QA==""")
    def get_local_dict(cls):
        return dict(map(lambda (x,y): (x, y.name),  filter(lambda (x,y): isinstance(y, File), cls.__dict__.items())))
    get_local_dict = classmethod(get_local_dict)
    def get_URL_dict(cls):
        return dict(map(lambda (x,y): (x, y.URL),  filter(lambda (x,y): isinstance(y, File), cls.__dict__.items())))
    get_URL_dict = classmethod(get_URL_dict)


#### HELPER CLASSES FOR PARAMETRING OUTPUT FORMAT ####

class EnumClass:
    def from_string(cls,x):
        return cls.__dict__[x.upper()]
    from_string = classmethod(from_string)
    
class Format(EnumClass):
    TEXT  = 1
    ANSI  = 2
    HTML  = 3
    LATEX = 4


#### TEST CLASSES ####

class TestClass:
    def __getitem__(self, item):
        return getattr(self, item)
    def add_keywords(self, kw):
        if kw is str:
            self.keywords.append(kw)
        else:
            self.keywords += kw

class TestCampaign(TestClass):
    def __init__(self, title):
        self.title = title
        self.filename = None
        self.headcomments = ""
        self.campaign = []
        self.keywords = []
        self.crc = None
        self.sha = None
        self.preexec = None
        self.preexec_output = None
    def add_testset(self, testset):
        self.campaign.append(testset)
    def __iter__(self):
        return self.campaign.__iter__()
    def all_tests(self):
        for ts in self:
            for t in ts:
                yield t

class TestSet(TestClass):
    def __init__(self, name):
        self.name = name
        self.set = []
        self.comments = ""
        self.keywords = []
        self.crc = None
        self.expand = 1
    def add_test(self, test):
        self.set.append(test)
    def __iter__(self):
        return self.set.__iter__()

class UnitTest(TestClass):
    def __init__(self, name):
        self.name = name
        self.test = ""
        self.comments = ""
        self.result = ""
        self.res = True  # must be True at init to have a different truth value than None
        self.output = ""
        self.num = -1
        self.keywords = []
        self.crc = None
        self.expand = 1
    def __nonzero__(self):
        return self.res


#### PARSE CAMPAIGN ####

def parse_campaign_file(campaign_file):
    test_campaign = TestCampaign("Test campaign")
    test_campaign.filename=  campaign_file.name
    testset = None
    test = None
    testnb = 0

    for l in campaign_file.readlines():
        if l[0] == '#':
            continue
        if l[0] == "~":
            (test or testset or campaign_file).add_keywords(l[1:].split())
        elif l[0] == "%":
            test_campaign.title = l[1:].strip()
        elif l[0] == "+":
            testset = TestSet(l[1:].strip())
            test_campaign.add_testset(testset)
            test = None
        elif l[0] == "=":
            test = UnitTest(l[1:].strip())
            test.num = testnb
            testnb += 1
            testset.add_test(test)
        elif l[0] == "*":
            if test is not None:
                
                test.comments += l[1:]
            elif testset is not None:
                testset.comments += l[1:]
            else:
                test_campaign.headcomments += l[1:]
        else:
            if test is None:
                if l.strip():
                    print >>sys.stderr, "Unkonwn content [%s]" % l.strip()
            else:
                test.test += l
    return test_campaign

def dump_campaign(test_campaign):
    print "#"*(len(test_campaign.title)+6)
    print "## %(title)s ##" % test_campaign
    print "#"*(len(test_campaign.title)+6)
    if test_campaign.sha and test_campaign.crc:
        print "CRC=[%(crc)s] SHA=[%(sha)s]" % test_campaign
    print "from file %(filename)s" % test_campaign
    print
    for ts in test_campaign:
        if ts.crc:
            print "+--[%s]%s(%s)--" % (ts.name,"-"*max(2,80-len(ts.name)-18),ts.crc)
        else:
            print "+--[%s]%s" % (ts.name,"-"*max(2,80-len(ts.name)-6))
        if ts.keywords:
            print "  kw=%s" % ",".join(ts.keywords)
        for t in ts:
            print "%(num)03i %(name)s" % t
            c = k = ""
            if t.keywords:
                k = "kw=%s" % ",".join(t.keywords)
            if t.crc:
                c = "[%(crc)s] " % t
            if c or k:
                print "    %s%s" % (c,k) 

#### COMPUTE CAMPAIGN DIGESTS ####

def crc32(x):
    return "%08X" % (0xffffffffL & zlib.crc32(x))

def sha1(x):
    return sha.sha(x).hexdigest().upper()

def compute_campaign_digests(test_campaign):
    dc = ""
    for ts in test_campaign:
        dts = ""
        for t in ts:
            dt = t.test.strip()
            t.crc = crc32(dt)
            dts += "\0"+dt
        ts.crc = crc32(dts)
        dc += "\0\x01"+dts
    test_campaign.crc = crc32(dc)
    test_campaign.sha = sha1(open(test_campaign.filename).read())


#### FILTER CAMPAIGN #####

def filter_tests_on_numbers(test_campaign, num):
    if num:
        for ts in test_campaign:
            ts.set = filter(lambda t: t.num in num, ts.set)
        test_campaign.campaign = filter(lambda ts: len(ts.set) > 0, test_campaign.campaign)

def filter_tests_keep_on_keywords(test_campaign, kw):
    def kw_match(lst, kw):
        for k in lst:
            if k in kw:
                return True
        return False
    
    if kw:
        for ts in test_campaign:
            ts.set = filter(lambda t: kw_match(t.keywords, kw), ts.set)

def filter_tests_remove_on_keywords(test_campaign, kw):
    def kw_match(lst, kw):
        for k in kw:
            if k not in lst:
                return False
        return True
    
    if kw:
        for ts in test_campaign:
            ts.set = filter(lambda t: not kw_match(t.keywords, kw), ts.set)


def remove_empty_testsets(test_campaign):
    test_campaign.campaign = filter(lambda ts: len(ts.set) > 0, test_campaign.campaign)


#### RUN CAMPAIGN #####

def run_campaign(test_campaign, get_interactive_session, verb=2):
    passed=failed=0
    if test_campaign.preexec:
        test_campaign.preexec_output = get_interactive_session(test_campaign.preexec.strip())[0]
    for testset in test_campaign:
        for t in testset:
            t.output,res = get_interactive_session(t.test.strip())
            the_res = False
            try:
                if res is None or res:
                    the_res= True
            except Exception,msg:
                t.output+="UTscapy: Error during result interpretation:\n"
                t.output+="".join(traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback,))
            if the_res:
                t.res = True
                res = "passed"
                passed += 1
            else:
                t.res = False
                res = "failed"
                failed += 1
            t.result = res
            if verb > 1:
                print >>sys.stderr,"%(result)6s %(crc)s %(name)s" % t
    test_campaign.passed = passed
    test_campaign.failed = failed
    if verb:
        print >>sys.stderr,"Campaign CRC=%(crc)s  SHA=%(sha)s" % test_campaign
        print >>sys.stderr,"PASSED=%i FAILED=%i" % (passed, failed)


#### INFO LINES ####

def info_line(test_campaign):
    filename = test_campaign.filename
    if filename is None:
        return "Run %s by UTscapy" % time.ctime()
    else:
        return "Run %s from [%s] by UTscapy" % (time.ctime(), filename)

def html_info_line(test_campaign):
    filename = test_campaign.filename
    if filename is None:
        return """Run %s by <a href="http://www.secdev.org/projects/UTscapy/">UTscapy</a><br>""" % time.ctime()
    else:
        return """Run %s from [%s] by <a href="http://www.secdev.org/projects/UTscapy/">UTscapy</a><br>""" % (time.ctime(), filename)


#### CAMPAIGN TO something ####

def campaign_to_TEXT(test_campaign):
    output="%(title)s\n" % test_campaign
    output += "-- "+info_line(test_campaign)+"\n\n"
    output += "Passed=%(passed)i\nFailed=%(failed)i\n\n%(headcomments)s\n" % test_campaign
    
    for testset in test_campaign:
        output += "######\n## %(name)s\n######\n%(comments)s\n\n" % testset
        for t in testset:
            if t.expand:
                output += "###(%(num)03i)=[%(result)s] %(name)s\n%(comments)s\n%(output)s\n\n" % t

    return output
 
def campaign_to_ANSI(test_campaign):
    output="%(title)s\n" % test_campaign
    output += "-- "+info_line(test_campaign)+"\n\n"
    output += "Passed=%(passed)i\nFailed=%(failed)i\n\n%(headcomments)s\n" % test_campaign
    
    for testset in test_campaign:
        output += "######\n## %(name)s\n######\n%(comments)s\n\n" % testset
        for t in testset:
            if t.expand:
                output += "###(%(num)03i)=[%(result)s] %(name)s\n%(comments)s\n%(output)s\n\n" % t

    return output


def campaign_to_HTML(test_campaign, local=0):
    output = """<html>
<head>
<title>%(title)s</title>
<link rel="stylesheet" href="%%(UTscapy_css)s" type="text/css">
<script language="JavaScript" src="%%(UTscapy_js)s" type="text/javascript"></script>
</head>
<body>

<h1>%(title)s</h1>

<span class=button onClick="hide_all('tst')">Shrink All</span>
<span class=button onClick="show_all('tst')">Expand All</span>
<span class=button onClick="show_passed('tst')">Expand Passed</span>
<span class=button onClick="show_failed('tst')">Expand Failed</span>
<p>
""" % test_campaign

    if local:
        External_Files.UTscapy_js.write(os.path.dirname(test_campaign.output_file.name))
        External_Files.UTscapy_css.write(os.path.dirname(test_campaign.output_file.name))
        output %= External_Files.get_local_dict()
    else:
        output %= External_Files.get_URL_dict()

    if test_campaign.crc is not None and test_campaign.sha is not None:
        output += "CRC=<span class=crc>%(crc)s</span> SHA=<span class=crc>%(sha)s</span><br>" % test_campaign
    output += "<small><em>"+html_info_line(test_campaign)+"</em></small>"
    output += test_campaign.headcomments +  "\n<p>PASSED=%(passed)i FAILED=%(failed)i<p>\n\n" % test_campaign
    for ts in test_campaign:
        for t in ts:
            output += """<span class=button%(result)s onClick="goto_id('tst%(num)il')">%(num)03i</span>\n""" % t
    output += "\n\n"
    
    for testset in test_campaign:
        output += "<h2>" % testset
        if testset.crc is not None:
            output += "<span class=crc>%(crc)s</span> " % testset
        output += "%(name)s</h2>\n%(comments)s\n<ul>\n" % testset
        for t in testset:
            output += """<li class=%(result)s id="tst%(num)il">\n""" % t
            if t.expand == 2:
                output +="""
<span id="tst%(num)i+" class="button%(result)s" onClick="show('tst%(num)i')" style="POSITION: absolute; VISIBILITY: hidden;">+%(num)03i+</span>
<span id="tst%(num)i-" class="button%(result)s" onClick="hide('tst%(num)i')">-%(num)03i-</span>
""" % t
            else:
                output += """
<span id="tst%(num)i+" class="button%(result)s" onClick="show('tst%(num)i')">+%(num)03i+</span>
<span id="tst%(num)i-" class="button%(result)s" onClick="hide('tst%(num)i')" style="POSITION: absolute; VISIBILITY: hidden;">-%(num)03i-</span>
""" % t
            if t.crc is not None:
                output += "<span class=crc>%(crc)s</span>\n" % t
            output += """%(name)s\n<span class="comment %(result)s" id="tst%(num)i" """ % t
            if t.expand < 2:
                output += """ style="POSITION: absolute; VISIBILITY: hidden;" """
            output += """><br>%(comments)s
<pre>
%(output)s</pre></span>
""" % t
        output += "\n</ul>\n\n"

    output += "</body></html>"
    return output

def campaign_to_LATEX(test_campaign):
    output = r"""\documentclass{report}
\usepackage{alltt}
\usepackage{xcolor}
\usepackage{a4wide}
\usepackage{hyperref}

\title{%(title)s}
\date{%%s}

\begin{document}
\maketitle
\tableofcontents

\begin{description}
\item[Passed:] %(passed)i
\item[Failed:] %(failed)i
\end{description}

%(headcomments)s

""" % test_campaign
    output %= info_line(test_campaign)
    
    for testset in test_campaign:
        output += "\\chapter{%(name)s}\n\n%(comments)s\n\n" % testset
        for t in testset:
            if t.expand:
                output += r"""\section{%(name)s}
            
[%(num)03i] [%(result)s]

%(comments)s
\begin{alltt}
%(output)s
\end{alltt}

""" % t

    output += "\\end{document}\n"
    return output



#### USAGE ####
                      
def usage():
    print >>sys.stderr,"""Usage: UTscapy [-m module] [-f {text|ansi|HTML|LaTeX}] [-o output_file] 
               [-t testfile] [-k keywords [-k ...]] [-K keywords [-K ...]]
               [-l] [-d|-D] [-F] [-q[q]] [-P preexecute_python_code]
               [-s /path/to/scpay]
-l\t\t: generate local files
-F\t\t: expand only failed tests
-d\t\t: dump campaign
-D\t\t: dump campaign and stop
-C\t\t: don't calculate CRC and SHA
-s\t\t: path to scapy.py
-q\t\t: quiet mode
-qq\t\t: [silent mode]
-n <testnum>\t: only tests whose numbers are given (eg. 1,3-7,12)
-m <module>\t: additional module to put in the namespace
-k <kw1>,<kw2>,...\t: include only tests with one of those keywords (can be used many times)
-K <kw1>,<kw2>,...\t: remove tests with one of those keywords (can be used many times)
-P <preexecute_python_code>
"""
    raise SystemExit


#### MAIN ####

def main(argv):
    import __builtin__

    # Parse arguments
    
    FORMAT = Format.ANSI
    TESTFILE = sys.stdin
    OUTPUTFILE = sys.stdout
    LOCAL = 0
    NUM=None
    KW_OK = []
    KW_KO = []
    DUMP = 0
    CRC = 1
    ONLYFAILED = 0
    VERB=2
    PREEXEC=""
    SCAPY="scapy"
    MODULES = []
    try:
        opts = getopt.getopt(argv, "o:t:f:hln:m:k:K:DdCFqP:s:")
        for opt,optarg in opts[0]:
            if opt == "-h":
                usage()
            elif opt == "-F":
                ONLYFAILED = 1
            elif opt == "-q":
                VERB -= 1
            elif opt == "-D":
                DUMP = 2
            elif opt == "-d":
                DUMP = 1
            elif opt == "-C":
                CRC = 0
            elif opt == "-s":
                SCAPY = optarg
            elif opt == "-P":
                PREEXEC += "\n"+optarg
            elif opt == "-f":
                try:
                    FORMAT = Format.from_string(optarg)
                except KeyError,msg:
                    raise getopt.GetoptError("Unknown output format %s" % msg)
            elif opt == "-t":
                TESTFILE = open(optarg)
            elif opt == "-o":
                OUTPUTFILE = open(optarg, "w")
            elif opt == "-l":
                LOCAL = 1
            elif opt == "-n":
                NUM = []
                for v in map( lambda x: x.strip(), optarg.split(",") ):
                    try:
                        NUM.append(int(v))
                    except ValueError:
                        v1,v2 = map(int, v.split("-"))
                        for vv in range(v1,v2+1):
                            NUM.append(vv)
            elif opt == "-m":
                MODULES.append(optarg)
            elif opt == "-k":
                KW_OK.append(optarg.split(","))
            elif opt == "-K":
                KW_KO.append(optarg.split(","))

        
        try:
            from scapy import all as scapy
        except ImportError,e:
            raise getopt.GetoptError("cannot import [%s]: %s" % (SCAPY,e))

        for m in MODULES:
            try:
                mod = import_module(m)
                __builtin__.__dict__.update(mod.__dict__)
            except ImportError,e:
                raise getopt.GetoptError("cannot import [%s]: %s" % (m,e))
                
    except getopt.GetoptError,msg:
        print >>sys.stderr,"ERROR:",msg
        raise SystemExit

    autorun_func = {
        Format.TEXT: scapy.autorun_get_text_interactive_session,
        Format.ANSI: scapy.autorun_get_ansi_interactive_session,
        Format.HTML: scapy.autorun_get_html_interactive_session,
        Format.LATEX: scapy.autorun_get_latex_interactive_session,
        }

    # Parse test file
    test_campaign = parse_campaign_file(TESTFILE)

    # Report parameters
    if PREEXEC:
        test_campaign.preexec = PREEXEC
    

    # Compute campaign CRC and SHA
    if CRC:
        compute_campaign_digests(test_campaign)

    # Filter out unwanted tests
    filter_tests_on_numbers(test_campaign, NUM)
    for k in KW_OK:
        filter_tests_keep_on_keywords(test_campaign, k)
    for k in KW_KO:
        filter_tests_remove_on_keywords(test_campaign, k)

    remove_empty_testsets(test_campaign)


    # Dump campaign
    if DUMP:
        dump_campaign(test_campaign)
        if DUMP > 1:
            sys.exit()

    # Run tests
    test_campaign.output_file = OUTPUTFILE
    run_campaign(test_campaign, autorun_func[FORMAT], verb=VERB)

    # Shrink passed
    if ONLYFAILED:
        for t in test_campaign.all_tests():
            if t:
                t.expand = 0
            else:
                t.expand = 2

    # Generate report
    if FORMAT == Format.TEXT:
        output = campaign_to_TEXT(test_campaign)
    elif FORMAT == Format.ANSI:
        output = campaign_to_ANSI(test_campaign)
    elif FORMAT == Format.HTML:
        output = campaign_to_HTML(test_campaign, local=LOCAL)
    elif FORMAT == Format.LATEX:
        output = campaign_to_LATEX(test_campaign)

    OUTPUTFILE.write(output)
    OUTPUTFILE.close()

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = utils
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
General utility functions.
"""

import os,sys,socket,types
import random,time
import gzip,zlib,cPickle
import re,struct,array
import subprocess

import warnings
warnings.filterwarnings("ignore","tempnam",RuntimeWarning, __name__)

from config import conf
from data import MTU
from error import log_runtime,log_loading,log_interactive
from base_classes import BasePacketList

WINDOWS=sys.platform.startswith("win32")

###########
## Tools ##
###########

def get_temp_file(keep=False, autoext=""):
    f = os.tempnam("","scapy")
    if not keep:
        conf.temp_files.append(f+autoext)
    return f

def sane_color(x):
    r=""
    for i in x:
        j = ord(i)
        if (j < 32) or (j >= 127):
            r=r+conf.color_theme.not_printable(".")
        else:
            r=r+i
    return r

def sane(x):
    r=""
    for i in x:
        j = ord(i)
        if (j < 32) or (j >= 127):
            r=r+"."
        else:
            r=r+i
    return r

def lhex(x):
    if type(x) in (int,long):
        return hex(x)
    elif type(x) is tuple:
        return "(%s)" % ", ".join(map(lhex, x))
    elif type(x) is list:
        return "[%s]" % ", ".join(map(lhex, x))
    else:
        return x

@conf.commands.register
def hexdump(x):
    x=str(x)
    l = len(x)
    i = 0
    while i < l:
        print "%04x  " % i,
        for j in range(16):
            if i+j < l:
                print "%02X" % ord(x[i+j]),
            else:
                print "  ",
            if j%16 == 7:
                print "",
        print " ",
        print sane_color(x[i:i+16])
        i += 16

@conf.commands.register
def linehexdump(x, onlyasc=0, onlyhex=0):
    x = str(x)
    l = len(x)
    if not onlyasc:
        for i in range(l):
            print "%02X" % ord(x[i]),
        print "",
    if not onlyhex:
        print sane_color(x)

def chexdump(x):
    x=str(x)
    print ", ".join(map(lambda x: "%#04x"%ord(x), x))
    
def hexstr(x, onlyasc=0, onlyhex=0):
    s = []
    if not onlyasc:
        s.append(" ".join(map(lambda x:"%02x"%ord(x), x)))
    if not onlyhex:
        s.append(sane(x)) 
    return "  ".join(s)


@conf.commands.register
def hexdiff(x,y):
    """Show differences between 2 binary strings"""
    x=str(x)[::-1]
    y=str(y)[::-1]
    SUBST=1
    INSERT=1
    d={}
    d[-1,-1] = 0,(-1,-1)
    for j in range(len(y)):
        d[-1,j] = d[-1,j-1][0]+INSERT, (-1,j-1)
    for i in range(len(x)):
        d[i,-1] = d[i-1,-1][0]+INSERT, (i-1,-1)

    for j in range(len(y)):
        for i in range(len(x)):
            d[i,j] = min( ( d[i-1,j-1][0]+SUBST*(x[i] != y[j]), (i-1,j-1) ),
                          ( d[i-1,j][0]+INSERT, (i-1,j) ),
                          ( d[i,j-1][0]+INSERT, (i,j-1) ) )
                          

    backtrackx = []
    backtracky = []
    i=len(x)-1
    j=len(y)-1
    while not (i == j == -1):
        i2,j2 = d[i,j][1]
        backtrackx.append(x[i2+1:i+1])
        backtracky.append(y[j2+1:j+1])
        i,j = i2,j2

        

    x = y = i = 0
    colorize = { 0: lambda x:x,
                -1: conf.color_theme.left,
                 1: conf.color_theme.right }
    
    dox=1
    doy=0
    l = len(backtrackx)
    while i < l:
        separate=0
        linex = backtrackx[i:i+16]
        liney = backtracky[i:i+16]
        xx = sum(len(k) for k in linex)
        yy = sum(len(k) for k in liney)
        if dox and not xx:
            dox = 0
            doy = 1
        if dox and linex == liney:
            doy=1
            
        if dox:
            xd = y
            j = 0
            while not linex[j]:
                j += 1
                xd -= 1
            print colorize[doy-dox]("%04x" % xd),
            x += xx
            line=linex
        else:
            print "    ",
        if doy:
            yd = y
            j = 0
            while not liney[j]:
                j += 1
                yd -= 1
            print colorize[doy-dox]("%04x" % yd),
            y += yy
            line=liney
        else:
            print "    ",
            
        print " ",
        
        cl = ""
        for j in range(16):
            if i+j < l:
                if line[j]:
                    col = colorize[(linex[j]!=liney[j])*(doy-dox)]
                    print col("%02X" % ord(line[j])),
                    if linex[j]==liney[j]:
                        cl += sane_color(line[j])
                    else:
                        cl += col(sane(line[j]))
                else:
                    print "  ",
                    cl += " "
            else:
                print "  ",
            if j == 7:
                print "",


        print " ",cl

        if doy or not yy:
            doy=0
            dox=1
            i += 16
        else:
            if yy:
                dox=0
                doy=1
            else:
                i += 16

    
crc32 = zlib.crc32

if struct.pack("H",1) == "\x00\x01": # big endian
    def checksum(pkt):
        if len(pkt) % 2 == 1:
            pkt += "\0"
        s = sum(array.array("H", pkt))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        s = ~s
        return s & 0xffff
else:
    def checksum(pkt):
        if len(pkt) % 2 == 1:
            pkt += "\0"
        s = sum(array.array("H", pkt))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        s = ~s
        return (((s>>8)&0xff)|s<<8) & 0xffff

def warning(x):
    log_runtime.warning(x)

def mac2str(mac):
    return "".join(map(lambda x: chr(int(x,16)), mac.split(":")))

def str2mac(s):
    return ("%02x:"*6)[:-1] % tuple(map(ord, s)) 

def strxor(x,y):
    return "".join(map(lambda x,y:chr(ord(x)^ord(y)),x,y))

# Workarround bug 643005 : https://sourceforge.net/tracker/?func=detail&atid=105470&aid=643005&group_id=5470
try:
    socket.inet_aton("255.255.255.255")
except socket.error:
    def inet_aton(x):
        if x == "255.255.255.255":
            return "\xff"*4
        else:
            return socket.inet_aton(x)
else:
    inet_aton = socket.inet_aton

inet_ntoa = socket.inet_ntoa
try:
    inet_ntop = socket.inet_ntop
    inet_pton = socket.inet_pton
except AttributeError:
    from scapy.pton_ntop import *
    log_loading.info("inet_ntop/pton functions not found. Python IPv6 support not present")


def atol(x):
    try:
        ip = inet_aton(x)
    except socket.error:
        ip = inet_aton(socket.gethostbyname(x))
    return struct.unpack("!I", ip)[0]
def ltoa(x):
    return inet_ntoa(struct.pack("!I", x&0xffffffff))

def itom(x):
    return (0xffffffff00000000L>>x)&0xffffffffL

def do_graph(graph,prog=None,format=None,target=None,type=None,string=None,options=None):
    """do_graph(graph, prog=conf.prog.dot, format="svg",
         target="| conf.prog.display", options=None, [string=1]):
    string: if not None, simply return the graph string
    graph: GraphViz graph description
    format: output type (svg, ps, gif, jpg, etc.), passed to dot's "-T" option
    target: filename or redirect. Defaults pipe to Imagemagick's display program
    prog: which graphviz program to use
    options: options to be passed to prog"""
        
    if format is None:
        if WINDOWS:
            format = "png" # use common format to make sure a viewer is installed
        else:
            format = "svg"
    if string:
        return graph
    if type is not None:
        format=type
    if prog is None:
        prog = conf.prog.dot
    start_viewer=False
    if target is None:
        if WINDOWS:
            tempfile = os.tempnam("", "scapy") + "." + format
            target = "> %s" % tempfile
            start_viewer = True
        else:
            target = "| %s" % conf.prog.display
    if format is not None:
        format = "-T %s" % format
    w,r = os.popen2("%s %s %s %s" % (prog,options or "", format or "", target))
    w.write(graph)
    w.close()
    if start_viewer:
        # Workaround for file not found error: We wait until tempfile is written.
        waiting_start = time.time()
        while not os.path.exists(tempfile):
            time.sleep(0.1)
            if time.time() - waiting_start > 3:
                warning("Temporary file '%s' could not be written. Graphic will not be displayed." % tempfile)
                break
        else:  
            if conf.prog.display == conf.prog._default:
                os.startfile(tempfile)
            else:
                subprocess.Popen([conf.prog.display, tempfile])

_TEX_TR = {
    "{":"{\\tt\\char123}",
    "}":"{\\tt\\char125}",
    "\\":"{\\tt\\char92}",
    "^":"\\^{}",
    "$":"\\$",
    "#":"\\#",
    "~":"\\~",
    "_":"\\_",
    "&":"\\&",
    "%":"\\%",
    "|":"{\\tt\\char124}",
    "~":"{\\tt\\char126}",
    "<":"{\\tt\\char60}",
    ">":"{\\tt\\char62}",
    }
    
def tex_escape(x):
    s = ""
    for c in x:
        s += _TEX_TR.get(c,c)
    return s

def colgen(*lstcol,**kargs):
    """Returns a generator that mixes provided quantities forever
    trans: a function to convert the three arguments into a color. lambda x,y,z:(x,y,z) by default"""
    if len(lstcol) < 2:
        lstcol *= 2
    trans = kargs.get("trans", lambda x,y,z: (x,y,z))
    while 1:
        for i in range(len(lstcol)):
            for j in range(len(lstcol)):
                for k in range(len(lstcol)):
                    if i != j or j != k or k != i:
                        yield trans(lstcol[(i+j)%len(lstcol)],lstcol[(j+k)%len(lstcol)],lstcol[(k+i)%len(lstcol)])

def incremental_label(label="tag%05i", start=0):
    while True:
        yield label % start
        start += 1

#########################
#### Enum management ####
#########################

class EnumElement:
    _value=None
    def __init__(self, key, value):
        self._key = key
        self._value = value
    def __repr__(self):
        return "<%s %s[%r]>" % (self.__dict__.get("_name", self.__class__.__name__), self._key, self._value)
    def __getattr__(self, attr):
        return getattr(self._value, attr)
    def __str__(self):
        return self._key
    def __eq__(self, other):
        return self._value == int(other)


class Enum_metaclass(type):
    element_class = EnumElement
    def __new__(cls, name, bases, dct):
        rdict={}
        for k,v in dct.iteritems():
            if type(v) is int:
                v = cls.element_class(k,v)
                dct[k] = v
                rdict[v] = k
        dct["__rdict__"] = rdict
        return super(Enum_metaclass, cls).__new__(cls, name, bases, dct)
    def __getitem__(self, attr):
        return self.__rdict__[attr]
    def __contains__(self, val):
        return val in self.__rdict__
    def get(self, attr, val=None):
        return self._rdict__.get(attr, val)
    def __repr__(self):
        return "<%s>" % self.__dict__.get("name", self.__name__)



###################
## Object saving ##
###################


def export_object(obj):
    print gzip.zlib.compress(cPickle.dumps(obj,2),9).encode("base64")

def import_object(obj=None):
    if obj is None:
        obj = sys.stdin.read()
    return cPickle.loads(gzip.zlib.decompress(obj.strip().decode("base64")))


def save_object(fname, obj):
    cPickle.dump(obj,gzip.open(fname,"wb"))

def load_object(fname):
    return cPickle.load(gzip.open(fname,"rb"))

@conf.commands.register
def corrupt_bytes(s, p=0.01, n=None):
    """Corrupt a given percentage or number of bytes from a string"""
    s = array.array("B",str(s))
    l = len(s)
    if n is None:
        n = max(1,int(l*p))
    for i in random.sample(xrange(l), n):
        s[i] = (s[i]+random.randint(1,255))%256
    return s.tostring()

@conf.commands.register
def corrupt_bits(s, p=0.01, n=None):
    """Flip a given percentage or number of bits from a string"""
    s = array.array("B",str(s))
    l = len(s)*8
    if n is None:
        n = max(1,int(l*p))
    for i in random.sample(xrange(l), n):
        s[i/8] ^= 1 << (i%8)
    return s.tostring()

    


#############################
## pcap capture file stuff ##
#############################

@conf.commands.register
def wrpcap(filename, pkt, *args, **kargs):
    """Write a list of packets to a pcap file
gz: set to 1 to save a gzipped capture
linktype: force linktype value
endianness: "<" or ">", force endianness"""
    PcapWriter(filename, *args, **kargs).write(pkt)

@conf.commands.register
def rdpcap(filename, count=-1):
    """Read a pcap file and return a packet list
count: read only <count> packets"""
    return PcapReader(filename).read_all(count=count)



class RawPcapReader:
    """A stateful pcap reader. Each packet is returned as a string"""

    def __init__(self, filename):
        self.filename = filename
        try:
            self.f = gzip.open(filename,"rb")
            magic = self.f.read(4)
        except IOError:
            self.f = open(filename,"rb")
            magic = self.f.read(4)
        if magic == "\xa1\xb2\xc3\xd4": #big endian
            self.endian = ">"
        elif  magic == "\xd4\xc3\xb2\xa1": #little endian
            self.endian = "<"
        else:
            raise Scapy_Exception("Not a pcap capture file (bad magic)")
        hdr = self.f.read(20)
        if len(hdr)<20:
            raise Scapy_Exception("Invalid pcap file (too short)")
        vermaj,vermin,tz,sig,snaplen,linktype = struct.unpack(self.endian+"HHIIII",hdr)

        self.linktype = linktype



    def __iter__(self):
        return self

    def next(self):
        """impliment the iterator protocol on a set of packets in a pcap file"""
        pkt = self.read_packet()
        if pkt == None:
            raise StopIteration
        return pkt


    def read_packet(self, size=MTU):
        """return a single packet read from the file
        
        returns None when no more packets are available
        """
        hdr = self.f.read(16)
        if len(hdr) < 16:
            return None
        sec,usec,caplen,wirelen = struct.unpack(self.endian+"IIII", hdr)
        s = self.f.read(caplen)[:MTU]
        return s,(sec,usec,wirelen) # caplen = len(s)


    def dispatch(self, callback):
        """call the specified callback routine for each packet read
        
        This is just a convienience function for the main loop
        that allows for easy launching of packet processing in a 
        thread.
        """
        for p in self:
            callback(p)

    def read_all(self,count=-1):
        """return a list of all packets in the pcap file
        """
        res=[]
        while count != 0:
            count -= 1
            p = self.read_packet()
            if p is None:
                break
            res.append(p)
        return res

    def recv(self, size=MTU):
        """ Emulate a socket
        """
        return self.read_packet(size)[0]

    def fileno(self):
        return self.f.fileno()

    def close(self):
        return self.f.close()

    

class PcapReader(RawPcapReader):
    def __init__(self, filename):
        RawPcapReader.__init__(self, filename)
        try:
            self.LLcls = conf.l2types[self.linktype]
        except KeyError:
            warning("PcapReader: unknown LL type [%i]/[%#x]. Using Raw packets" % (self.linktype,self.linktype))
            self.LLcls = conf.raw_layer
    def read_packet(self, size=MTU):
        rp = RawPcapReader.read_packet(self,size)
        if rp is None:
            return None
        s,(sec,usec,wirelen) = rp
        
        try:
            p = self.LLcls(s)
        except KeyboardInterrupt:
            raise
        except:
            if conf.debug_dissector:
                raise
            p = conf.raw_layer(s)
        p.time = sec+0.000001*usec
        return p
    def read_all(self,count=-1):
        res = RawPcapReader.read_all(self, count)
        import plist
        return plist.PacketList(res,name = os.path.basename(self.filename))
    def recv(self, size=MTU):
        return self.read_packet(size)
        


class RawPcapWriter:
    """A stream PCAP writer with more control than wrpcap()"""
    def __init__(self, filename, linktype=None, gz=False, endianness="", append=False, sync=False):
        """
        linktype: force linktype to a given value. If None, linktype is taken
                  from the first writter packet
        gz: compress the capture on the fly
        endianness: force an endianness (little:"<", big:">"). Default is native
        append: append packets to the capture file instead of truncating it
        sync: do not bufferize writes to the capture file
        """
        
        self.linktype = linktype
        self.header_present = 0
        self.append=append
        self.gz = gz
        self.endian = endianness
        self.filename=filename
        self.sync=sync
        bufsz=4096
        if sync:
            bufsz=0

        self.f = [open,gzip.open][gz](filename,append and "ab" or "wb", gz and 9 or bufsz)
        
    def fileno(self):
        return self.f.fileno()

    def _write_header(self, pkt):
        self.header_present=1

        if self.append:
            # Even if prone to race conditions, this seems to be
            # safest way to tell whether the header is already present
            # because we have to handle compressed streams that
            # are not as flexible as basic files
            g = [open,gzip.open][self.gz](self.filename,"rb")
            if g.read(16):
                return
            
        self.f.write(struct.pack(self.endian+"IHHIIII", 0xa1b2c3d4L,
                                 2, 4, 0, 0, MTU, self.linktype))
        self.f.flush()
    

    def write(self, pkt):
        """accepts a either a single packet or a list of packets
        to be written to the dumpfile
        """
        if not self.header_present:
            self._write_header(pkt)
        if type(pkt) is str:
            self._write_packet(pkt)
        else:
            for p in pkt:
                self._write_packet(p)

    def _write_packet(self, packet, sec=None, usec=None, caplen=None, wirelen=None):
        """writes a single packet to the pcap file
        """
        if caplen is None:
            caplen = len(packet)
        if wirelen is None:
            wirelen = caplen
        if sec is None or usec is None:
            t=time.time()
            it = int(t)
            if sec is None:
                sec = it
            if usec is None:
                usec = int(round((t-it)*1000000))
        self.f.write(struct.pack(self.endian+"IIII", sec, usec, caplen, wirelen))
        self.f.write(packet)
        if self.gz and self.sync:
            self.f.flush()

    def flush(self):
        return self.f.flush()
    def close(self):
        return self.f.close()
                
class PcapWriter(RawPcapWriter):
    def _write_header(self, pkt):
        if self.linktype == None:
            if type(pkt) is list or type(pkt) is tuple or isinstance(pkt,BasePacketList):
                pkt = pkt[0]
            try:
                self.linktype = conf.l2types[pkt.__class__]
            except KeyError:
                warning("PcapWriter: unknown LL type for %s. Using type 1 (Ethernet)" % pkt.__class__.__name__)
                self.linktype = 1
        RawPcapWriter._write_header(self, pkt)

    def _write_packet(self, packet):        
        sec = int(packet.time)
        usec = int(round((packet.time-sec)*1000000))
        s = str(packet)
        caplen = len(s)
        RawPcapWriter._write_packet(self, s, sec, usec, caplen, caplen)


re_extract_hexcap = re.compile("^((0x)?[0-9a-fA-F]{2,}[ :\t]{,3}|) *(([0-9a-fA-F]{2} {,2}){,16})")

def import_hexcap():
    p = ""
    try:
        while 1:
            l = raw_input().strip()
            try:
                p += re_extract_hexcap.match(l).groups()[2]
            except:
                warning("Parsing error during hexcap")
                continue
    except EOFError:
        pass
    
    p = p.replace(" ","")
    return p.decode("hex")
        


@conf.commands.register
def wireshark(pktlist):
    """Run wireshark on a list of packets"""
    f = get_temp_file()
    wrpcap(f, pktlist)
    subprocess.Popen([conf.prog.wireshark, "-r", f])

@conf.commands.register
def hexedit(x):
    x = str(x)
    f = get_temp_file()
    open(f,"w").write(x)
    subprocess.call([conf.prog.hexedit, f])
    x = open(f).read()
    os.unlink(f)
    return x

def __make_table(yfmtfunc, fmtfunc, endline, list, fxyz, sortx=None, sorty=None, seplinefunc=None):
    vx = {} 
    vy = {} 
    vz = {}
    vxf = {}
    vyf = {}
    l = 0
    for e in list:
        xx,yy,zz = map(str, fxyz(e))
        l = max(len(yy),l)
        vx[xx] = max(vx.get(xx,0), len(xx), len(zz))
        vy[yy] = None
        vz[(xx,yy)] = zz

    vxk = vx.keys()
    vyk = vy.keys()
    if sortx:
        vxk.sort(sortx)
    else:
        try:
            vxk.sort(lambda x,y:int(x)-int(y))
        except:
            try:
                vxk.sort(lambda x,y: cmp(atol(x),atol(y)))
            except:
                vxk.sort()
    if sorty:
        vyk.sort(sorty)
    else:
        try:
            vyk.sort(lambda x,y:int(x)-int(y))
        except:
            try:
                vyk.sort(lambda x,y: cmp(atol(x),atol(y)))
            except:
                vyk.sort()


    if seplinefunc:
        sepline = seplinefunc(l, map(lambda x:vx[x],vxk))
        print sepline

    fmt = yfmtfunc(l)
    print fmt % "",
    for x in vxk:
        vxf[x] = fmtfunc(vx[x])
        print vxf[x] % x,
    print endline
    if seplinefunc:
        print sepline
    for y in vyk:
        print fmt % y,
        for x in vxk:
            print vxf[x] % vz.get((x,y), "-"),
        print endline
    if seplinefunc:
        print sepline

def make_table(*args, **kargs):
    __make_table(lambda l:"%%-%is" % l, lambda l:"%%-%is" % l, "", *args, **kargs)
    
def make_lined_table(*args, **kargs):
    __make_table(lambda l:"%%-%is |" % l, lambda l:"%%-%is |" % l, "",
                 seplinefunc=lambda a,x:"+".join(map(lambda y:"-"*(y+2), [a-1]+x+[-2])),
                 *args, **kargs)

def make_tex_table(*args, **kargs):
    __make_table(lambda l: "%s", lambda l: "& %s", "\\\\", seplinefunc=lambda a,x:"\\hline", *args, **kargs)


########NEW FILE########
__FILENAME__ = utils6
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

## Copyright (C) 2005  Guillaume Valadon <guedou@hongo.wide.ad.jp>
##                     Arnaud Ebalard <arnaud.ebalard@eads.net>

"""
Utility functions for IPv6.
"""

from config import conf
from data import *
from utils import *


def construct_source_candidate_set(addr, plen, laddr, loname):
    """
    Given all addresses assigned to a specific interface ('laddr' parameter),
    this function returns the "candidate set" associated with 'addr/plen'.
    
    Basically, the function filters all interface addresses to keep only those
    that have the same scope as provided prefix.
    
    This is on this list of addresses that the source selection mechanism 
    will then be performed to select the best source address associated
    with some specific destination that uses this prefix.
    """
    def cset_sort(x,y):
        x_global = 0
        if in6_isgladdr(x):
            x_global = 1
        y_global = 0
        if in6_isgladdr(y):
            y_global = 1
        res = y_global - x_global
        if res != 0 or y_global != 1:
            return res
        # two global addresses: if one is native, it wins.
        if not in6_isaddr6to4(x):
            return -1;
        return -res

    cset = []
    if in6_isgladdr(addr) or in6_isuladdr(addr):
	cset = filter(lambda x: x[1] == IPV6_ADDR_GLOBAL, laddr)
    elif in6_islladdr(addr):
	cset = filter(lambda x: x[1] == IPV6_ADDR_LINKLOCAL, laddr)
    elif in6_issladdr(addr):
	cset = filter(lambda x: x[1] == IPV6_ADDR_SITELOCAL, laddr)
    elif in6_ismaddr(addr):
	if in6_ismnladdr(addr):
	    cset = [('::1', 16, loname)]
	elif in6_ismgladdr(addr):
	    cset = filter(lambda x: x[1] == IPV6_ADDR_GLOBAL, laddr)
	elif in6_ismlladdr(addr):
	    cset = filter(lambda x: x[1] == IPV6_ADDR_LINKLOCAL, laddr)
	elif in6_ismsladdr(addr):
	    cset = filter(lambda x: x[1] == IPV6_ADDR_SITELOCAL, laddr)
    elif addr == '::' and plen == 0:
	cset = filter(lambda x: x[1] == IPV6_ADDR_GLOBAL, laddr)
    cset = map(lambda x: x[0], cset)
    cset.sort(cmp=cset_sort) # Sort with global addresses first
    return cset            

def get_source_addr_from_candidate_set(dst, candidate_set):
    """
    This function implement a limited version of source address selection
    algorithm defined in section 5 of RFC 3484. The format is very different
    from that described in the document because it operates on a set 
    of candidate source address for some specific route.
    """

    def scope_cmp(a, b):
        """
        Given two addresses, returns -1, 0 or 1 based on comparison of
        their scope
        """
        scope_mapper = {IPV6_ADDR_GLOBAL: 4,
                        IPV6_ADDR_SITELOCAL: 3,
                        IPV6_ADDR_LINKLOCAL: 2,
                        IPV6_ADDR_LOOPBACK: 1}
        sa = in6_getscope(a)
        if sa == -1:
            sa = IPV6_ADDR_LOOPBACK
        sb = in6_getscope(b)
        if sb == -1:
            sb = IPV6_ADDR_LOOPBACK

        sa = scope_mapper[sa]
        sb = scope_mapper[sb]

        if sa == sb:
            return 0
        if sa > sb:
            return 1
        return -1

    def rfc3484_cmp(source_a, source_b):
        """
        The function implements a limited version of the rules from Source
        Address selection algorithm defined section of RFC 3484.
        """

        # Rule 1: Prefer same address
        if source_a == dst:
            return 1
        if source_b == dst:
            return 1

        # Rule 2: Prefer appropriate scope
        tmp = scope_cmp(source_a, source_b)
        if tmp == -1:
            if scope_cmp(source_a, dst) == -1:
                return 1
            else:
                return -1
        elif tmp == 1:
            if scope_cmp(source_b, dst) == -1:
                return 1
            else:
                return -1

        # Rule 3: cannot be easily implemented
        # Rule 4: cannot be easily implemented
        # Rule 5: does not make sense here
        # Rule 6: cannot be implemented
        # Rule 7: cannot be implemented
        
        # Rule 8: Longest prefix match
        tmp1 = in6_get_common_plen(source_a, dst)
        tmp2 = in6_get_common_plen(source_b, dst)
        if tmp1 > tmp2:
            return 1
        elif tmp2 > tmp1:
            return -1
        return 0
    
    if not candidate_set:
	# Should not happen
	return None

    candidate_set.sort(cmp=rfc3484_cmp, reverse=True)
    
    return candidate_set[0]


def find_ifaddr2(addr, plen, laddr):
    dstAddrType = in6_getAddrType(addr)
    
    if dstAddrType == IPV6_ADDR_UNSPECIFIED: # Shouldn't happen as dst addr
        return None

    if dstAddrType == IPV6_ADDR_LOOPBACK: 
        return None

    tmp = [[]] + map(lambda (x,y,z): (in6_getAddrType(x), x, y, z), laddr)
    def filterSameScope(l, t):
        if (t[0] & dstAddrType & IPV6_ADDR_SCOPE_MASK) == 0:
            l.append(t)
        return l
    sameScope = reduce(filterSameScope, tmp)
    
    l =  len(sameScope) 
    if l == 1:  # Only one address for our scope
        return sameScope[0][1]

    elif l > 1: # Muliple addresses for our scope
        stfAddr = filter(lambda x: x[0] & IPV6_ADDR_6TO4, sameScope)
        nativeAddr = filter(lambda x: not (x[0] & IPV6_ADDR_6TO4), sameScope)

        if not (dstAddrType & IPV6_ADDR_6TO4): # destination is not 6to4
           if len(nativeAddr) != 0:
               return nativeAddr[0][1]
           return stfAddr[0][1]

        else:  # Destination is 6to4, try to use source 6to4 addr if any
            if len(stfAddr) != 0:
                return stfAddr[0][1]
            return nativeAddr[0][1]
    else:
        return None

# Think before modify it : for instance, FE::1 does exist and is unicast
# there are many others like that.
# TODO : integrate Unique Local Addresses
def in6_getAddrType(addr):
    naddr = inet_pton(socket.AF_INET6, addr)
    paddr = inet_ntop(socket.AF_INET6, naddr) # normalize
    addrType = 0
    # _Assignable_ Global Unicast Address space
    # is defined in RFC 3513 as those in 2000::/3
    if ((struct.unpack("B", naddr[0])[0] & 0xE0) == 0x20):
        addrType = (IPV6_ADDR_UNICAST | IPV6_ADDR_GLOBAL)
        if naddr[:2] == ' \x02': # Mark 6to4 @
            addrType |= IPV6_ADDR_6TO4
    elif naddr[0] == '\xff': # multicast
        addrScope = paddr[3]
        if addrScope == '2':
            addrType = (IPV6_ADDR_LINKLOCAL | IPV6_ADDR_MULTICAST)
        elif addrScope == 'e':
            addrType = (IPV6_ADDR_GLOBAL | IPV6_ADDR_MULTICAST)
        else:
            addrType = (IPV6_ADDR_GLOBAL | IPV6_ADDR_MULTICAST)
    elif ((naddr[0] == '\xfe') and ((int(paddr[2], 16) & 0xC) == 0x8)):
        addrType = (IPV6_ADDR_UNICAST | IPV6_ADDR_LINKLOCAL)
    elif paddr == "::1":
        addrType = IPV6_ADDR_LOOPBACK
    elif paddr == "::":
        addrType = IPV6_ADDR_UNSPECIFIED
    else:
        # Everything else is global unicast (RFC 3513)
        # Even old deprecated (RFC3879) Site-Local addresses
        addrType = (IPV6_ADDR_GLOBAL | IPV6_ADDR_UNICAST)

    return addrType

def in6_mactoifaceid(mac, ulbit=None):
    """
    Compute the interface ID in modified EUI-64 format associated 
    to the Ethernet address provided as input.
    value taken by U/L bit in the interface identifier is basically 
    the reversed value of that in given MAC address it can be forced
    to a specific value by using optional 'ulbit' parameter.
    """
    if len(mac) != 17: return None
    m = "".join(mac.split(':'))
    if len(m) != 12: return None
    first = int(m[0:2], 16)
    if ulbit is None or not (ulbit == 0 or ulbit == 1):
        ulbit = [1,'-',0][first & 0x02]
    ulbit *= 2
    first = "%.02x" % ((first & 0xFD) | ulbit)
    eui64 = first + m[2:4] + ":" + m[4:6] + "FF:FE" + m[6:8] + ":" + m[8:12]
    return eui64.upper()

def in6_ifaceidtomac(ifaceid): # TODO: finish commenting function behavior
    """
    Extract the mac address from provided iface ID. Iface ID is provided 
    in printable format ("XXXX:XXFF:FEXX:XXXX", eventually compressed). None 
    is returned on error.
    """
    try:
        ifaceid = inet_pton(socket.AF_INET6, "::"+ifaceid)[8:16]
    except:
        return None
    if ifaceid[3:5] != '\xff\xfe':
        return None
    first = struct.unpack("B", ifaceid[:1])[0]
    ulbit = 2*[1,'-',0][first & 0x02]
    first = struct.pack("B", ((first & 0xFD) | ulbit))
    oui = first + ifaceid[1:3]
    end = ifaceid[5:]
    l = map(lambda x: "%.02x" % struct.unpack("B", x)[0], list(oui+end))
    return ":".join(l)

def in6_addrtomac(addr):
    """
    Extract the mac address from provided address. None is returned
    on error.
    """
    mask = inet_pton(socket.AF_INET6, "::ffff:ffff:ffff:ffff")
    x = in6_and(mask, inet_pton(socket.AF_INET6, addr))
    ifaceid = inet_ntop(socket.AF_INET6, x)[2:]
    return in6_ifaceidtomac(ifaceid)

def in6_addrtovendor(addr):
    """
    Extract the MAC address from a modified EUI-64 constructed IPv6
    address provided and use the IANA oui.txt file to get the vendor.
    The database used for the conversion is the one loaded by Scapy,
    based on Wireshark (/usr/share/wireshark/wireshark/manuf)  None
    is returned on error, "UNKNOWN" if the vendor is unknown.
    """
    mac = in6_addrtomac(addr)
    if mac is None:
        return None

    res = conf.manufdb._get_manuf(mac)
    if len(res) == 17 and res.count(':') != 5: # Mac address, i.e. unknown
        res = "UNKNOWN"

    return res

def in6_getLinkScopedMcastAddr(addr, grpid=None, scope=2):
    """
    Generate a Link-Scoped Multicast Address as described in RFC 4489.
    Returned value is in printable notation.

    'addr' parameter specifies the link-local address to use for generating
    Link-scoped multicast address IID.
    
    By default, the function returns a ::/96 prefix (aka last 32 bits of 
    returned address are null). If a group id is provided through 'grpid' 
    parameter, last 32 bits of the address are set to that value (accepted 
    formats : '\x12\x34\x56\x78' or '12345678' or 0x12345678 or 305419896).

    By default, generated address scope is Link-Local (2). That value can 
    be modified by passing a specific 'scope' value as an argument of the
    function. RFC 4489 only authorizes scope values <= 2. Enforcement
    is performed by the function (None will be returned).
    
    If no link-local address can be used to generate the Link-Scoped IPv6
    Multicast address, or if another error occurs, None is returned.
    """
    if not scope in [0, 1, 2]:
        return None    
    try:
        if not in6_islladdr(addr):
            return None
        addr = inet_pton(socket.AF_INET6, addr)
    except:
        warning("in6_getLinkScopedMcastPrefix(): Invalid address provided")
        return None

    iid = addr[8:]

    if grpid is None:
        grpid = '\x00\x00\x00\x00'
    else:
        if type(grpid) is str:
            if len(grpid) == 8:
                try:
                    grpid = int(grpid, 16) & 0xffffffff
                except:
                    warning("in6_getLinkScopedMcastPrefix(): Invalid group id provided")
                    return None
            elif len(grpid) == 4:
                try:
                    grpid = struct.unpack("!I", grpid)[0]
                except:
                    warning("in6_getLinkScopedMcastPrefix(): Invalid group id provided")
                    return None
        grpid = struct.pack("!I", grpid)

    flgscope = struct.pack("B", 0xff & ((0x3 << 4) | scope))
    plen = '\xff'
    res = '\x00'
    a = '\xff' + flgscope + res + plen + iid + grpid

    return inet_ntop(socket.AF_INET6, a)

def in6_get6to4Prefix(addr):
    """
    Returns the /48 6to4 prefix associated with provided IPv4 address
    On error, None is returned. No check is performed on public/private
    status of the address
    """
    try:
        addr = inet_pton(socket.AF_INET, addr)
        addr = inet_ntop(socket.AF_INET6, '\x20\x02'+addr+'\x00'*10)
    except:
        return None
    return addr

def in6_6to4ExtractAddr(addr):
    """
    Extract IPv4 address embbeded in 6to4 address. Passed address must be
    a 6to4 addrees. None is returned on error.
    """
    try:
        addr = inet_pton(socket.AF_INET6, addr)
    except:
        return None
    if addr[:2] != " \x02":
        return None
    return inet_ntop(socket.AF_INET, addr[2:6])
    

def in6_getLocalUniquePrefix():
    """
    Returns a pseudo-randomly generated Local Unique prefix. Function
    follows recommandation of Section 3.2.2 of RFC 4193 for prefix
    generation.
    """
    # Extracted from RFC 1305 (NTP) :
    # NTP timestamps are represented as a 64-bit unsigned fixed-point number, 
    # in seconds relative to 0h on 1 January 1900. The integer part is in the 
    # first 32 bits and the fraction part in the last 32 bits.

    # epoch = (1900, 1, 1, 0, 0, 0, 5, 1, 0) 
    # x = time.time()
    # from time import gmtime, strftime, gmtime, mktime
    # delta = mktime(gmtime(0)) - mktime(self.epoch)
    # x = x-delta

    tod = time.time() # time of day. Will bother with epoch later
    i = int(tod)
    j = int((tod - i)*(2**32))
    tod = struct.pack("!II", i,j)
    # TODO: Add some check regarding system address gathering
    rawmac = get_if_raw_hwaddr(conf.iface6)[1]
    mac = ":".join(map(lambda x: "%.02x" % ord(x), list(rawmac)))
    # construct modified EUI-64 ID
    eui64 = inet_pton(socket.AF_INET6, '::' + in6_mactoifaceid(mac))[8:] 
    import sha
    globalid = sha.new(tod+eui64).digest()[:5]
    return inet_ntop(socket.AF_INET6, '\xfd' + globalid + '\x00'*10)

def in6_getRandomizedIfaceId(ifaceid, previous=None):
    """
    Implements the interface ID generation algorithm described in RFC 3041.
    The function takes the Modified EUI-64 interface identifier generated
    as described in RFC 4291 and an optional previous history value (the
    first element of the output of this function). If no previous interface
    identifier is provided, a random one is generated. The function returns
    a tuple containing the randomized interface identifier and the history
    value (for possible future use). Input and output values are provided in
    a "printable" format as depicted below.
    
    ex: 

    >>> in6_getRandomizedIfaceId('20b:93ff:feeb:2d3')
    ('4c61:76ff:f46a:a5f3', 'd006:d540:db11:b092')

    >>> in6_getRandomizedIfaceId('20b:93ff:feeb:2d3',
                                 previous='d006:d540:db11:b092')
    ('fe97:46fe:9871:bd38', 'eeed:d79c:2e3f:62e')
    """

    s = ""
    if previous is None:
        d = "".join(map(chr, range(256)))
        for i in range(8):
            s += random.choice(d)
        previous = s
    s = inet_pton(socket.AF_INET6, "::"+ifaceid)[8:] + previous
    import md5
    s = md5.new(s).digest()
    s1,s2 = s[:8],s[8:]
    s1 = chr(ord(s1[0]) | 0x04) + s1[1:]  
    s1 = inet_ntop(socket.AF_INET6, "\xff"*8 + s1)[20:]
    s2 = inet_ntop(socket.AF_INET6, "\xff"*8 + s2)[20:]    
    return (s1, s2)


_rfc1924map = [ '0','1','2','3','4','5','6','7','8','9','A','B','C','D','E',
                'F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T',
                'U','V','W','X','Y','Z','a','b','c','d','e','f','g','h','i',
                'j','k','l','m','n','o','p','q','r','s','t','u','v','w','x',
                'y','z','!','#','$','%','&','(',')','*','+','-',';','<','=',
                '>','?','@','^','_','`','{','|','}','~' ]

def in6_ctop(addr):
    """
    Convert an IPv6 address in Compact Representation Notation 
    (RFC 1924) to printable representation ;-)
    Returns None on error.
    """
    if len(addr) != 20 or not reduce(lambda x,y: x and y, 
                                     map(lambda x: x in _rfc1924map, addr)):
        return None
    i = 0
    for c in addr:
        j = _rfc1924map.index(c)
        i = 85*i + j
    res = []
    for j in range(4):
        res.append(struct.pack("!I", i%2**32))
        i = i/(2**32)
    res.reverse()
    return inet_ntop(socket.AF_INET6, "".join(res))

def in6_ptoc(addr):
    """
    Converts an IPv6 address in printable representation to RFC 
    1924 Compact Representation ;-) 
    Returns None on error.
    """    
    try:
        d=struct.unpack("!IIII", inet_pton(socket.AF_INET6, addr))
    except:
        return None
    res = 0
    m = [2**96, 2**64, 2**32, 1]
    for i in range(4):
        res += d[i]*m[i]
    rem = res
    res = []
    while rem:
        res.append(_rfc1924map[rem%85])
        rem = rem/85
    res.reverse()
    return "".join(res)

    
def in6_isaddr6to4(x):
    """
    Return True if provided address (in printable format) is a 6to4
    address (being in 2002::/16).
    """
    x = inet_pton(socket.AF_INET6, x)
    return x[:2] == ' \x02'

conf.teredoPrefix = "2001::" # old one was 3ffe:831f (it is a /32)
conf.teredoServerPort = 3544

def in6_isaddrTeredo(x):
    """
    Return True if provided address is a Teredo, meaning it is under 
    the /32 conf.teredoPrefix prefix value (by default, 2001::).
    Otherwise, False is returned. Address must be passed in printable
    format.
    """
    our = inet_pton(socket.AF_INET6, x)[0:4]
    teredoPrefix = inet_pton(socket.AF_INET6, conf.teredoPrefix)[0:4]
    return teredoPrefix == our

def teredoAddrExtractInfo(x):
    """
    Extract information from a Teredo address. Return value is 
    a 4-tuple made of IPv4 address of Teredo server, flag value (int),
    mapped address (non obfuscated) and mapped port (non obfuscated).
    No specific checks are performed on passed address.
    """
    addr = inet_pton(socket.AF_INET6, x)
    server = inet_ntop(socket.AF_INET, addr[4:8])
    flag = struct.unpack("!H",addr[8:10])[0]
    mappedport = struct.unpack("!H",strxor(addr[10:12],'\xff'*2))[0] 
    mappedaddr = inet_ntop(socket.AF_INET, strxor(addr[12:16],'\xff'*4))
    return server, flag, mappedaddr, mappedport

def in6_iseui64(x):
    """
    Return True if provided address has an interface identifier part
    created in modified EUI-64 format (meaning it matches *::*:*ff:fe*:*). 
    Otherwise, False is returned. Address must be passed in printable
    format.
    """
    eui64 = inet_pton(socket.AF_INET6, '::ff:fe00:0')
    x = in6_and(inet_pton(socket.AF_INET6, x), eui64)
    return x == eui64

def in6_isanycast(x): # RFC 2526
    if in6_iseui64(x):
        s = '::fdff:ffff:ffff:ff80'
        x = in6_and(x, inet_pton(socket.AF_INET6, '::ffff:ffff:ffff:ff80'))
        x = in6_and(x, inet_pton(socket.AF_INET6, s)) 
        return x == inet_pton(socket.AF_INET6, s)
    else:
        # not EUI-64 
        #|              n bits             |    121-n bits    |   7 bits   |
        #+---------------------------------+------------------+------------+
        #|           subnet prefix         | 1111111...111111 | anycast ID |
        #+---------------------------------+------------------+------------+
        #                                  |   interface identifier field  |
        warning('in6_isanycast(): TODO not EUI-64')
        return 0

def _in6_bitops(a1, a2, operator=0):
    a1 = struct.unpack('4I', a1)
    a2 = struct.unpack('4I', a2)
    fop = [ lambda x,y: x | y,
            lambda x,y: x & y,
            lambda x,y: x ^ y
          ]  
    ret = map(fop[operator%len(fop)], a1, a2)
    t = ''.join(map(lambda x: struct.pack('I', x), ret))
    return t

def in6_or(a1, a2):
    """
    Provides a bit to bit OR of provided addresses. They must be 
    passed in network format. Return value is also an IPv6 address
    in network format.
    """
    return _in6_bitops(a1, a2, 0)

def in6_and(a1, a2):
    """
    Provides a bit to bit AND of provided addresses. They must be 
    passed in network format. Return value is also an IPv6 address
    in network format.
    """
    return _in6_bitops(a1, a2, 1)

def in6_xor(a1, a2):
    """
    Provides a bit to bit XOR of provided addresses. They must be 
    passed in network format. Return value is also an IPv6 address
    in network format.
    """
    return _in6_bitops(a1, a2, 2)

def in6_cidr2mask(m):
    """
    Return the mask (bitstring) associated with provided length 
    value. For instance if function is called on 48, return value is
    '\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'.
    
    """
    if m > 128 or m < 0:
        raise Scapy_Exception("value provided to in6_cidr2mask outside [0, 128] domain (%d)" % m)

    t = []
    for i in xrange(0, 4):
        t.append(max(0, 2**32  - 2**(32-min(32, m))))
        m -= 32

    return ''.join(map(lambda x: struct.pack('!I', x), t))

def in6_getnsma(a): 
    """
    Return link-local solicited-node multicast address for given
    address. Passed address must be provided in network format.
    Returned value is also in network format.
    """

    r = in6_and(a, inet_pton(socket.AF_INET6, '::ff:ffff'))
    r = in6_or(inet_pton(socket.AF_INET6, 'ff02::1:ff00:0'), r)
    return r

def in6_getnsmac(a): # return multicast Ethernet address associated with multicast v6 destination
    """
    Return the multicast mac address associated with provided
    IPv6 address. Passed address must be in network format. 
    """

    a = struct.unpack('16B', a)[-4:]
    mac = '33:33:'
    mac += ':'.join(map(lambda x: '%.2x' %x, a))
    return mac

def in6_getha(prefix): 
    """
    Return the anycast address associated with all home agents on a given
    subnet.
    """
    r = in6_and(inet_pton(socket.AF_INET6, prefix), in6_cidr2mask(64))
    r = in6_or(r, inet_pton(socket.AF_INET6, '::fdff:ffff:ffff:fffe'))
    return inet_ntop(socket.AF_INET6, r)

def in6_ptop(str): 
    """
    Normalizes IPv6 addresses provided in printable format, returning the 
    same address in printable format. (2001:0db8:0:0::1 -> 2001:db8::1)
    """
    return inet_ntop(socket.AF_INET6, inet_pton(socket.AF_INET6, str))

def in6_isincluded(addr, prefix, plen):
    """
    Returns True when 'addr' belongs to prefix/plen. False otherwise.
    """
    temp = inet_pton(socket.AF_INET6, addr)
    pref = in6_cidr2mask(plen)
    zero = inet_pton(socket.AF_INET6, prefix)
    return zero == in6_and(temp, pref)

def in6_isdocaddr(str):
    """
    Returns True if provided address in printable format belongs to
    2001:db8::/32 address space reserved for documentation (as defined 
    in RFC 3849).
    """
    return in6_isincluded(str, '2001:db8::', 32)

def in6_islladdr(str):
    """
    Returns True if provided address in printable format belongs to
    _allocated_ link-local unicast address space (fe80::/10)
    """
    return in6_isincluded(str, 'fe80::', 10)

def in6_issladdr(str):
    """
    Returns True if provided address in printable format belongs to
    _allocated_ site-local address space (fec0::/10). This prefix has 
    been deprecated, address being now reserved by IANA. Function 
    will remain for historic reasons.
    """
    return in6_isincluded(str, 'fec0::', 10)

def in6_isuladdr(str):
    """
    Returns True if provided address in printable format belongs to
    Unique local address space (fc00::/7).
    """
    return in6_isincluded(str, 'fc00::', 7)

# TODO : we should see the status of Unique Local addresses against
#        global address space.
#        Up-to-date information is available through RFC 3587. 
#        We should review function behavior based on its content.
def in6_isgladdr(str):
    """
    Returns True if provided address in printable format belongs to
    _allocated_ global address space (2000::/3). Please note that,
    Unique Local addresses (FC00::/7) are not part of global address
    space, and won't match.
    """
    return in6_isincluded(str, '2000::', 3)

def in6_ismaddr(str):
    """
    Returns True if provided address in printable format belongs to 
    allocated Multicast address space (ff00::/8).
    """
    return in6_isincluded(str, 'ff00::', 8)

def in6_ismnladdr(str):
    """
    Returns True if address belongs to node-local multicast address
    space (ff01::/16) as defined in RFC 
    """
    return in6_isincluded(str, 'ff01::', 16)

def in6_ismgladdr(str):
    """
    Returns True if address belongs to global multicast address
    space (ff0e::/16).
    """
    return in6_isincluded(str, 'ff0e::', 16)

def in6_ismlladdr(str):
    """
    Returns True if address balongs to link-local multicast address
    space (ff02::/16)
    """
    return in6_isincluded(str, 'ff02::', 16)

def in6_ismsladdr(str):
    """
    Returns True if address belongs to site-local multicast address
    space (ff05::/16). Site local address space has been deprecated.
    Function remains for historic reasons.
    """
    return in6_isincluded(str, 'ff05::', 16)

def in6_isaddrllallnodes(str):
    """
    Returns True if address is the link-local all-nodes multicast 
    address (ff02::1). 
    """
    return (inet_pton(socket.AF_INET6, "ff02::1") ==
            inet_pton(socket.AF_INET6, str))

def in6_isaddrllallservers(str):
    """
    Returns True if address is the link-local all-servers multicast 
    address (ff02::2). 
    """
    return (inet_pton(socket.AF_INET6, "ff02::2") ==
            inet_pton(socket.AF_INET6, str))

def in6_getscope(addr):
    """
    Returns the scope of the address.
    """
    if in6_isgladdr(addr) or in6_isuladdr(addr):
        scope = IPV6_ADDR_GLOBAL
    elif in6_islladdr(addr):
        scope = IPV6_ADDR_LINKLOCAL
    elif in6_issladdr(addr):
        scope = IPV6_ADDR_SITELOCAL
    elif in6_ismaddr(addr):
        if in6_ismgladdr(addr):
            scope = IPV6_ADDR_GLOBAL
        elif in6_ismlladdr(addr):
            scope = IPV6_ADDR_LINKLOCAL
        elif in6_ismsladdr(addr):
            scope = IPV6_ADDR_SITELOCAL
        elif in6_ismnladdr(addr):
            scope = IPV6_ADDR_LOOPBACK
        else:
            scope = -1
    elif addr == '::1':
        scope = IPV6_ADDR_LOOPBACK
    else:
        scope = -1
    return scope

def in6_get_common_plen(a, b):
    """
    Return common prefix length of IPv6 addresses a and b.
    """
    def matching_bits(byte1, byte2):
        for i in range(8):
            cur_mask = 0x80 >> i
            if (byte1 & cur_mask) != (byte2 & cur_mask):
                return i
        return 8
        
    tmpA = inet_pton(socket.AF_INET6, a)
    tmpB = inet_pton(socket.AF_INET6, b)
    for i in range(16):
        mbits = matching_bits(ord(tmpA[i]), ord(tmpB[i]))
        if mbits != 8:
            return 8*i + mbits
    return 128

########NEW FILE########
__FILENAME__ = volatile
## This file is part of Scapy
## See http://www.secdev.org/projects/scapy for more informations
## Copyright (C) Philippe Biondi <phil@secdev.org>
## This program is published under a GPLv2 license

"""
Fields that hold random numbers.
"""

import random,time,math
from base_classes import Net
from utils import corrupt_bits,corrupt_bytes

####################
## Random numbers ##
####################


class RandomEnumeration:
    """iterate through a sequence in random order.
       When all the values have been drawn, if forever=1, the drawing is done again.
       If renewkeys=0, the draw will be in the same order, guaranteeing that the same
       number will be drawn in not less than the number of integers of the sequence"""
    def __init__(self, inf, sup, seed=None, forever=1, renewkeys=0):
        self.forever = forever
        self.renewkeys = renewkeys
        self.inf = inf
        self.rnd = random.Random(seed)
        self.sbox_size = 256

        self.top = sup-inf+1
    
        n=0
        while (1<<n) < self.top:
            n += 1
        self.n =n

        self.fs = min(3,(n+1)/2)
        self.fsmask = 2**self.fs-1
        self.rounds = max(self.n,3)
        self.turns = 0
        self.i = 0

    def __iter__(self):
        return self
    def next(self):
        while True:
            if self.turns == 0 or (self.i == 0 and self.renewkeys):
                self.cnt_key = self.rnd.randint(0,2**self.n-1)
                self.sbox = [self.rnd.randint(0,self.fsmask) for k in xrange(self.sbox_size)]
            self.turns += 1
            while self.i < 2**self.n:
                ct = self.i^self.cnt_key
                self.i += 1
                for k in range(self.rounds): # Unbalanced Feistel Network
                    lsb = ct & self.fsmask
                    ct >>= self.fs
                    lsb ^= self.sbox[ct%self.sbox_size]
                    ct |= lsb << (self.n-self.fs)
                
                if ct < self.top:
                    return self.inf+ct
            self.i = 0
            if not self.forever:
                raise StopIteration


class VolatileValue:
    def __repr__(self):
        return "<%s>" % self.__class__.__name__
    def __getattr__(self, attr):
        if attr == "__setstate__":
            raise AttributeError(attr)
        elif attr == "__cmp__":
            x = self._fix()
            def cmp2(y,x=x):
                if type(x) != type(y):
                    return -1
                return x.__cmp__(y)
            return cmp2
        return getattr(self._fix(),attr)
    def _fix(self):
        return None


class RandField(VolatileValue):
    pass

class RandNum(RandField):
    """Instances evaluate to random integers in selected range"""
    min = 0
    max = 0
    def __init__(self, min, max):
        self.min = min
        self.max = max
    def _fix(self):
        return random.randrange(self.min, self.max+1)

class RandNumGamma(RandField):
    def __init__(self, alpha, beta):
        self.alpha = alpha
        self.beta = beta
    def _fix(self):
        return int(round(random.gammavariate(self.alpha, self.beta)))

class RandNumGauss(RandField):
    def __init__(self, mu, sigma):
        self.mu = mu
        self.sigma = sigma
    def _fix(self):
        return int(round(random.gauss(self.mu, self.sigma)))

class RandNumExpo(RandField):
    def __init__(self, lambd, base=0):
        self.lambd = lambd
        self.base = base
    def _fix(self):
        return self.base+int(round(random.expovariate(self.lambd)))

class RandEnum(RandNum):
    """Instances evaluate to integer sampling without replacement from the given interval"""
    def __init__(self, min, max):
        self.seq = RandomEnumeration(min,max)
    def _fix(self):
        return self.seq.next()

class RandByte(RandNum):
    def __init__(self):
        RandNum.__init__(self, 0, 2L**8-1)

class RandSByte(RandNum):
    def __init__(self):
        RandNum.__init__(self, -2L**7, 2L**7-1)

class RandShort(RandNum):
    def __init__(self):
        RandNum.__init__(self, 0, 2L**16-1)

class RandSShort(RandNum):
    def __init__(self):
        RandNum.__init__(self, -2L**15, 2L**15-1)

class RandInt(RandNum):
    def __init__(self):
        RandNum.__init__(self, 0, 2L**32-1)

class RandSInt(RandNum):
    def __init__(self):
        RandNum.__init__(self, -2L**31, 2L**31-1)

class RandLong(RandNum):
    def __init__(self):
        RandNum.__init__(self, 0, 2L**64-1)

class RandSLong(RandNum):
    def __init__(self):
        RandNum.__init__(self, -2L**63, 2L**63-1)

class RandEnumByte(RandEnum):
    def __init__(self):
        RandEnum.__init__(self, 0, 2L**8-1)

class RandEnumSByte(RandEnum):
    def __init__(self):
        RandEnum.__init__(self, -2L**7, 2L**7-1)

class RandEnumShort(RandEnum):
    def __init__(self):
        RandEnum.__init__(self, 0, 2L**16-1)

class RandEnumSShort(RandEnum):
    def __init__(self):
        RandEnum.__init__(self, -2L**15, 2L**15-1)

class RandEnumInt(RandEnum):
    def __init__(self):
        RandEnum.__init__(self, 0, 2L**32-1)

class RandEnumSInt(RandEnum):
    def __init__(self):
        RandEnum.__init__(self, -2L**31, 2L**31-1)

class RandEnumLong(RandEnum):
    def __init__(self):
        RandEnum.__init__(self, 0, 2L**64-1)

class RandEnumSLong(RandEnum):
    def __init__(self):
        RandEnum.__init__(self, -2L**63, 2L**63-1)

class RandChoice(RandField):
    def __init__(self, *args):
        if not args:
            raise TypeError("RandChoice needs at least one choice")
        self._choice = args
    def _fix(self):
        return random.choice(self._choice)
    
class RandString(RandField):
    def __init__(self, size=None, chars="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"):
        if size is None:
            size = RandNumExpo(0.01)
        self.size = size
        self.chars = chars
    def _fix(self):
        s = ""
        for i in range(self.size):
            s += random.choice(self.chars)
        return s

class RandBin(RandString):
    def __init__(self, size=None):
        RandString.__init__(self, size, "".join(map(chr,range(256))))


class RandTermString(RandString):
    def __init__(self, size, term):
        RandString.__init__(self, size, "".join(map(chr,range(1,256))))
        self.term = term
    def _fix(self):
        return RandString._fix(self)+self.term
    
    

class RandIP(RandString):
    def __init__(self, iptemplate="0.0.0.0/0"):
        self.ip = Net(iptemplate)
    def _fix(self):
        return self.ip.choice()

class RandMAC(RandString):
    def __init__(self, template="*"):
        template += ":*:*:*:*:*"
        template = template.split(":")
        self.mac = ()
        for i in range(6):
            if template[i] == "*":
                v = RandByte()
            elif "-" in template[i]:
                x,y = template[i].split("-")
                v = RandNum(int(x,16), int(y,16))
            else:
                v = int(template[i],16)
            self.mac += (v,)
    def _fix(self):
        return "%02x:%02x:%02x:%02x:%02x:%02x" % self.mac
    
class RandIP6(RandString):
    def __init__(self, ip6template="**"):
        self.tmpl = ip6template
        self.sp = self.tmpl.split(":")
        for i,v in enumerate(self.sp):
            if not v or v == "**":
                continue
            if "-" in v:
                a,b = v.split("-")
            elif v == "*":
                a=b=""
            else:
                a=b=v

            if not a:
                a = "0"
            if not b:
                b = "ffff"
            if a==b:
                self.sp[i] = int(a,16)
            else:
                self.sp[i] = RandNum(int(a,16), int(b,16))
        self.variable = "" in self.sp
        self.multi = self.sp.count("**")
    def _fix(self):
        done = 0
        nbm = self.multi
        ip = []
        for i,n in enumerate(self.sp):
            if n == "**":
                nbm -= 1
                remain = 8-(len(self.sp)-i-1)-len(ip)+nbm
                if "" in self.sp:
                    remain += 1
                if nbm or self.variable:
                    remain = random.randint(0,remain)
                for j in range(remain):
                    ip.append("%04x" % random.randint(0,65535))
            elif not n:
                ip.append("")
            else:
                ip.append("%04x" % n)
        if len(ip) == 9:
            ip.remove("")
        return ":".join(ip)

class RandOID(RandString):
    def __init__(self, fmt=None, depth=RandNumExpo(0.1), idnum=RandNumExpo(0.01)):
        self.ori_fmt = fmt
        if fmt is not None:
            fmt = fmt.split(".")
            for i in range(len(fmt)):
                if "-" in fmt[i]:
                    fmt[i] = tuple(map(int, fmt[i].split("-")))
        self.fmt = fmt
        self.depth = depth
        self.idnum = idnum
    def __repr__(self):
        if self.ori_fmt is None:
            return "<%s>" % self.__class__.__name__
        else:
            return "<%s [%s]>" % (self.__class__.__name__, self.ori_fmt)
    def _fix(self):
        if self.fmt is None:
            return ".".join(map(str, [self.idnum for i in xrange(1+self.depth)]))
        else:
            oid = []
            for i in self.fmt:
                if i == "*":
                    oid.append(str(self.idnum))
                elif i == "**":
                    oid += map(str, [self.idnum for i in xrange(1+self.depth)])
                elif type(i) is tuple:
                    oid.append(str(random.randrange(*i)))
                else:
                    oid.append(i)
            return ".".join(oid)
            

class RandRegExp(RandField):
    def __init__(self, regexp, lambda_=0.3,):
        self._regexp = regexp
        self._lambda = lambda_

    @staticmethod
    def choice_expand(s): #XXX does not support special sets like (ex ':alnum:')
        m = ""
        invert = s and s[0] == "^"
        while True:
            p = s.find("-")
            if p < 0:
                break
            if p == 0 or p == len(s)-1:
                m = "-"
                if p:
                    s = s[:-1]
                else:
                    s = s[1:]
            else:
                c1 = s[p-1]
                c2 = s[p+1]
                rng = "".join(map(chr, range(ord(c1),ord(c2)+1)))
                s = s[:p-1]+rng+s[p+1:]
        res = m+s
        if invert:
            res = "".join([chr(x) for x in xrange(256) if chr(x) not in res])
        return res

    @staticmethod
    def stack_fix(lst, index):
        r = ""
        mul = 1
        for e in lst:
            if type(e) is list:
                if mul != 1:
                    mul = mul-1
                    r += RandRegExp.stack_fix(e[1:]*mul, index)
                # only the last iteration should be kept for back reference
                f = RandRegExp.stack_fix(e[1:], index)
                for i,idx in enumerate(index):
                    if e is idx:
                        index[i] = f
                r += f
                mul = 1
            elif type(e) is tuple:
                kind,val = e
                if kind == "cite":
                    r += index[val-1]
                elif kind == "repeat":
                    mul = val

                elif kind == "choice":
                    if mul == 1:
                        c = random.choice(val)
                        r += RandRegExp.stack_fix(c[1:], index)
                    else:
                        r += RandRegExp.stack_fix([e]*mul, index)
                        mul = 1
            else:
                if mul != 1:
                    r += RandRegExp.stack_fix([e]*mul, index)
                    mul = 1
                else:
                    r += str(e)
        return r

    def _fix(self):
        stack = [None]
        index = []
        current = stack
        i = 0
        ln = len(self._regexp)
        interp = True
        while i < ln:
            c = self._regexp[i]
            i+=1
            
            if c == '(':
                current = [current]
                current[0].append(current)
            elif c == '|':
                p = current[0]
                ch = p[-1]
                if type(ch) is not tuple:
                    ch = ("choice",[current])
                    p[-1] = ch
                else:
                    ch[1].append(current)
                current = [p]
            elif c == ')':
                ch = current[0][-1]
                if type(ch) is tuple:
                    ch[1].append(current)
                index.append(current)
                current = current[0]
            elif c == '[' or c == '{':
                current = [current]
                current[0].append(current)
                interp = False
            elif c == ']':
                current = current[0]
                choice = RandRegExp.choice_expand("".join(current.pop()[1:]))
                current.append(RandChoice(*list(choice)))
                interp = True
            elif c == '}':
                current = current[0]
                num = "".join(current.pop()[1:])
                e = current.pop()
                if "," not in num:
                    n = int(num)
                    current.append([current]+[e]*n)
                else:
                    num_min,num_max = num.split(",")
                    if not num_min:
                        num_min = "0"
                    if num_max:
                        n = RandNum(int(num_min),int(num_max))
                    else:
                        n = RandNumExpo(self._lambda,base=int(num_min))
                    current.append(("repeat",n))
                    current.append(e)
                interp = True
            elif c == '\\':
                c = self._regexp[i]
                if c == "s":
                    c = RandChoice(" ","\t")
                elif c in "0123456789":
                    c = ("cite",ord(c)-0x30)
                current.append(c)
                i += 1
            elif not interp:
                current.append(c)
            elif c == '+':
                e = current.pop()
                current.append([current]+[e]*(int(random.expovariate(self._lambda))+1))
            elif c == '*':
                e = current.pop()
                current.append([current]+[e]*int(random.expovariate(self._lambda)))
            elif c == '?':
                if random.randint(0,1):
                    current.pop()
            elif c == '.':
                current.append(RandChoice(*[chr(x) for x in xrange(256)]))
            elif c == '$' or c == '^':
                pass
            else:
                current.append(c)

        return RandRegExp.stack_fix(stack[1:], index)
    def __repr__(self):
        return "<%s [%r]>" % (self.__class__.__name__, self._regexp)

class RandSingularity(RandChoice):
    pass
                
class RandSingNum(RandSingularity):
    @staticmethod
    def make_power_of_two(end):
        sign = 1
        if end == 0: 
            end = 1
        if end < 0:
            end = -end
            sign = -1
        end_n = int(math.log(end)/math.log(2))+1
        return set([sign*2**i for i in range(end_n)])            
        
    def __init__(self, mn, mx):
        sing = set([0, mn, mx, int((mn+mx)/2)])
        sing |= self.make_power_of_two(mn)
        sing |= self.make_power_of_two(mx)
        for i in sing.copy():
            sing.add(i+1)
            sing.add(i-1)
        for i in sing.copy():
            if not mn <= i <= mx:
                sing.remove(i)
        self._choice = list(sing)
        

class RandSingByte(RandSingNum):
    def __init__(self):
        RandSingNum.__init__(self, 0, 2L**8-1)

class RandSingSByte(RandSingNum):
    def __init__(self):
        RandSingNum.__init__(self, -2L**7, 2L**7-1)

class RandSingShort(RandSingNum):
    def __init__(self):
        RandSingNum.__init__(self, 0, 2L**16-1)

class RandSingSShort(RandSingNum):
    def __init__(self):
        RandSingNum.__init__(self, -2L**15, 2L**15-1)

class RandSingInt(RandSingNum):
    def __init__(self):
        RandSingNum.__init__(self, 0, 2L**32-1)

class RandSingSInt(RandSingNum):
    def __init__(self):
        RandSingNum.__init__(self, -2L**31, 2L**31-1)

class RandSingLong(RandSingNum):
    def __init__(self):
        RandSingNum.__init__(self, 0, 2L**64-1)

class RandSingSLong(RandSingNum):
    def __init__(self):
        RandSingNum.__init__(self, -2L**63, 2L**63-1)

class RandSingString(RandSingularity):
    def __init__(self):
        self._choice = [ "",
                         "%x",
                         "%%",
                         "%s",
                         "%i",
                         "%n",
                         "%x%x%x%x%x%x%x%x%x",
                         "%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s%s",
                         "%",
                         "%%%",
                         "A"*4096,
                         "\x00"*4096,
                         "\xff"*4096,
                         "\x7f"*4096,
                         "\x80"*4096,
                         " "*4096,
                         "\\"*4096,
                         "("*4096,
                         "../"*1024,
                         "/"*1024,
                         "${HOME}"*512,
                         " or 1=1 --",
                         "' or 1=1 --",
                         '" or 1=1 --',
                         " or 1=1; #",
                         "' or 1=1; #",
                         '" or 1=1; #',
                         ";reboot;",
                         "$(reboot)",
                         "`reboot`",
                         "index.php%00",
                         "\x00",
                         "%00",
                         "\\",
                         "../../../../../../../../../../../../../../../../../etc/passwd",
                         "%2e%2e%2f" * 20 + "etc/passwd",
                         "%252e%252e%252f" * 20 + "boot.ini",
                         "..%c0%af" * 20 + "etc/passwd",
                         "..%c0%af" * 20 + "boot.ini",
                         "//etc/passwd",
                         r"..\..\..\..\..\..\..\..\..\..\..\..\..\..\..\..\..\boot.ini",
                         "AUX:",
                         "CLOCK$",
                         "COM:",
                         "CON:",
                         "LPT:",
                         "LST:",
                         "NUL:",
                         "CON:",
                         r"C:\CON\CON",
                         r"C:\boot.ini",
                         r"\\myserver\share",
                         "foo.exe:",
                         "foo.exe\\", ]
                             

class RandPool(RandField):
    def __init__(self, *args):
        """Each parameter is a volatile object or a couple (volatile object, weight)"""
        pool = []
        for p in args:
            w = 1
            if type(p) is tuple:
                p,w = p
            pool += [p]*w
        self._pool = pool
    def _fix(self):
        r = random.choice(self._pool)
        return r._fix()

# Automatic timestamp

class AutoTime(VolatileValue):
    def __init__(self, base=None):
        if base == None:
            self.diff = 0
        else:
            self.diff = time.time()-base
    def _fix(self):
        return time.time()-self.diff
            
class IntAutoTime(AutoTime):
    def _fix(self):
        return int(time.time()-self.diff)


class ZuluTime(AutoTime):
    def __init__(self, diff=None):
        self.diff=diff
    def _fix(self):
        return time.strftime("%y%m%d%H%M%SZ",time.gmtime(time.time()+self.diff))


class DelayedEval(VolatileValue):
    """ Exemple of usage: DelayedEval("time.time()") """
    def __init__(self, expr):
        self.expr = expr
    def _fix(self):
        return eval(self.expr)


class IncrementalValue(VolatileValue):
    def __init__(self, start=0, step=1, restart=-1):
        self.start = self.val = start
        self.step = step
        self.restart = restart
    def _fix(self):
        v = self.val
        if self.val == self.restart :
            self.val = self.start
        else:
            self.val += self.step
        return v

class CorruptedBytes(VolatileValue):
    def __init__(self, s, p=0.01, n=None):
        self.s = s
        self.p = p
        self.n = n
    def _fix(self):
        return corrupt_bytes(self.s, self.p, self.n)

class CorruptedBits(CorruptedBytes):
    def _fix(self):
        return corrupt_bits(self.s, self.p, self.n)


########NEW FILE########