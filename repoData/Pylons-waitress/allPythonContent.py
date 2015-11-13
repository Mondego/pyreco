__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# waitress documentation build configuration file
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

# If your extensions are in another directory, add it here. If the
# directory is relative to the documentation root, use os.path.abspath to
# make it absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

import sys, os
import pkg_resources

# Add and use Pylons theme
if 'sphinx-build' in ' '.join(sys.argv): # protect against dumb importers
    from subprocess import call, Popen, PIPE

    p = Popen('which git', shell=True, stdout=PIPE)
    git = p.stdout.read().strip()
    cwd = os.getcwd()
    _themes = os.path.join(cwd, '_themes')

    if not os.path.isdir(_themes):
        call([git, 'clone', 'git://github.com/Pylons/pylons_sphinx_theme.git',
                '_themes'])
    else:
        os.chdir(_themes)
        call([git, 'checkout', 'master'])
        call([git, 'pull'])
        os.chdir(cwd)

    sys.path.append(os.path.abspath('_themes'))

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'waitress'
copyright = '2012, Agendaless Consulting <chrism@plope.com>'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = pkg_resources.get_distribution('waitress').version
# The full version, including alpha/beta/rc tags.
release = version

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
exclude_patterns = ['_themes/README.rst',]

# The reST default role (used for this markup: `text`) to use for all
# documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# Add and use Pylons theme
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'pylons'
html_theme_options = dict(github_url='http://github.com/Pylons/waitress')

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
# html_style = 'repoze.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as
# html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
# html_logo = '.static/logo_hi.gif'

# The name of an image file (within the static path) to use as favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or
# 32x32 pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css".
#html_static_path = ['.static']

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
htmlhelp_basename = 'atemplatedoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, document class [howto/manual]).
latex_documents = [
  ('index', 'waitress.tex', 'waitress Documentation',
   'Pylons Developers', 'manual'),
]

# The name of an image file (relative to this directory) to place at the
# top of the title page.
latex_logo = '.static/logo_hi.gif'

# For "manual" documents, if this is true, then toplevel headings are
# parts, not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = adjustments
##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Adjustments are tunable parameters.
"""
import getopt
import socket
import sys

truthy = frozenset(('t', 'true', 'y', 'yes', 'on', '1'))

def asbool(s):
    """ Return the boolean value ``True`` if the case-lowered value of string
    input ``s`` is any of ``t``, ``true``, ``y``, ``on``, or ``1``, otherwise
    return the boolean value ``False``.  If ``s`` is the value ``None``,
    return ``False``.  If ``s`` is already one of the boolean values ``True``
    or ``False``, return it."""
    if s is None:
        return False
    if isinstance(s, bool):
        return s
    s = str(s).strip()
    return s.lower() in truthy

def asoctal(s):
    """Convert the given octal string to an actual number."""
    return int(s, 8)

def slash_fixed_str(s):
    s = s.strip()
    if s:
        # always have a leading slash, replace any number of leading slashes
        # with a single slash, and strip any trailing slashes
        s = '/' + s.lstrip('/').rstrip('/')
    return s

class Adjustments(object):
    """This class contains tunable parameters.
    """

    _params = (
        ('host', str),
        ('port', int),
        ('threads', int),
        ('trusted_proxy', str),
        ('url_scheme', str),
        ('url_prefix', slash_fixed_str),
        ('backlog', int),
        ('recv_bytes', int),
        ('send_bytes', int),
        ('outbuf_overflow', int),
        ('inbuf_overflow', int),
        ('connection_limit', int),
        ('cleanup_interval', int),
        ('channel_timeout', int),
        ('log_socket_errors', asbool),
        ('max_request_header_size', int),
        ('max_request_body_size', int),
        ('expose_tracebacks', asbool),
        ('ident', str),
        ('asyncore_loop_timeout', int),
        ('asyncore_use_poll', asbool),
        ('unix_socket', str),
        ('unix_socket_perms', asoctal),
    )

    _param_map = dict(_params)

    # hostname or IP address to listen on
    host = '0.0.0.0'

    # TCP port to listen on
    port = 8080

    # mumber of threads available for tasks
    threads = 4

    # Host allowed to overrid ``wsgi.url_scheme`` via header
    trusted_proxy = None

    # default ``wsgi.url_scheme`` value
    url_scheme = 'http'

    # default ``SCRIPT_NAME`` value, also helps reset ``PATH_INFO``
    # when nonempty
    url_prefix = ''

    # server identity (sent in Server: header)
    ident = 'waitress'

    # backlog is the value waitress passes to pass to socket.listen() This is
    # the maximum number of incoming TCP connections that will wait in an OS
    # queue for an available channel.  From listen(1): "If a connection
    # request arrives when the queue is full, the client may receive an error
    # with an indication of ECONNREFUSED or, if the underlying protocol
    # supports retransmission, the request may be ignored so that a later
    # reattempt at connection succeeds."
    backlog = 1024

    # recv_bytes is the argument to pass to socket.recv().
    recv_bytes = 8192

    # send_bytes is the number of bytes to send to socket.send().  Multiples
    # of 9000 should avoid partly-filled packets, but don't set this larger
    # than the TCP write buffer size.  In Linux, /proc/sys/net/ipv4/tcp_wmem
    # controls the minimum, default, and maximum sizes of TCP write buffers.
    send_bytes = 18000

    # A tempfile should be created if the pending output is larger than
    # outbuf_overflow, which is measured in bytes. The default is 1MB.  This
    # is conservative.
    outbuf_overflow = 1048576

    # A tempfile should be created if the pending input is larger than
    # inbuf_overflow, which is measured in bytes. The default is 512K.  This
    # is conservative.
    inbuf_overflow = 524288

    # Stop creating new channels if too many are already active (integer).
    # Each channel consumes at least one file descriptor, and, depending on
    # the input and output body sizes, potentially up to three.  The default
    # is conservative, but you may need to increase the number of file
    # descriptors available to the Waitress process on most platforms in
    # order to safely change it (see ``ulimit -a`` "open files" setting).
    # Note that this doesn't control the maximum number of TCP connections
    # that can be waiting for processing; the ``backlog`` argument controls
    # that.
    connection_limit = 100

    # Minimum seconds between cleaning up inactive channels.
    cleanup_interval = 30

    # Maximum seconds to leave an inactive connection open.
    channel_timeout = 120

    # Boolean: turn off to not log premature client disconnects.
    log_socket_errors = True

    # maximum number of bytes of all request headers combined (256K default)
    max_request_header_size = 262144

    # maximum number of bytes in request body (1GB default)
    max_request_body_size = 1073741824

    # expose tracebacks of uncaught exceptions
    expose_tracebacks = False

    # Path to a Unix domain socket to use.
    unix_socket = None

    # Path to a Unix domain socket to use.
    unix_socket_perms = 0o600

    # The socket options to set on receiving a connection.  It is a list of
    # (level, optname, value) tuples.  TCP_NODELAY disables the Nagle
    # algorithm for writes (Waitress already buffers its writes).
    socket_options = [
        (socket.SOL_TCP, socket.TCP_NODELAY, 1),
    ]

    # The asyncore.loop timeout value
    asyncore_loop_timeout = 1

    # The asyncore.loop flag to use poll() instead of the default select().
    asyncore_use_poll = False

    def __init__(self, **kw):
        for k, v in kw.items():
            if k not in self._param_map:
                raise ValueError('Unknown adjustment %r' % k)
            setattr(self, k, self._param_map[k](v))
        if (sys.platform[:3] == "win" and
                self.host == 'localhost'): # pragma: no cover
            self.host = ''

    @classmethod
    def parse_args(cls, argv):
        """Pre-parse command line arguments for input into __init__.  Note that
        this does not cast values into adjustment types, it just creates a
        dictionary suitable for passing into __init__, where __init__ does the
        casting.
        """
        long_opts = ['help', 'call']
        for opt, cast in cls._params:
            opt = opt.replace('_', '-')
            if cast is asbool:
                long_opts.append(opt)
                long_opts.append('no-' + opt)
            else:
                long_opts.append(opt + '=')

        kw = {
            'help': False,
            'call': False,
        }
        opts, args = getopt.getopt(argv, '', long_opts)
        for opt, value in opts:
            param = opt.lstrip('-').replace('-', '_')
            if param.startswith('no_'):
                param = param[3:]
                kw[param] = 'false'
            elif param in ('help', 'call'):
                kw[param] = True
            elif cls._param_map[param] is asbool:
                kw[param] = 'true'
            else:
                kw[param] = value
        return kw, args

########NEW FILE########
__FILENAME__ = buffers
##############################################################################
#
# Copyright (c) 2001-2004 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Buffers
"""
from io import BytesIO

# copy_bytes controls the size of temp. strings for shuffling data around.
COPY_BYTES = 1 << 18 # 256K

# The maximum number of bytes to buffer in a simple string.
STRBUF_LIMIT = 8192

class FileBasedBuffer(object):

    remain = 0

    def __init__(self, file, from_buffer=None):
        self.file = file
        if from_buffer is not None:
            from_file = from_buffer.getfile()
            read_pos = from_file.tell()
            from_file.seek(0)
            while True:
                data = from_file.read(COPY_BYTES)
                if not data:
                    break
                file.write(data)
            self.remain = int(file.tell() - read_pos)
            from_file.seek(read_pos)
            file.seek(read_pos)

    def __len__(self):
        return self.remain

    def __nonzero__(self):
        return self.remain > 0

    __bool__ = __nonzero__ # py3

    def append(self, s):
        file = self.file
        read_pos = file.tell()
        file.seek(0, 2)
        file.write(s)
        file.seek(read_pos)
        self.remain = self.remain + len(s)

    def get(self, numbytes=-1, skip=False):
        file = self.file
        if not skip:
            read_pos = file.tell()
        if numbytes < 0:
            # Read all
            res = file.read()
        else:
            res = file.read(numbytes)
        if skip:
            self.remain -= len(res)
        else:
            file.seek(read_pos)
        return res

    def skip(self, numbytes, allow_prune=0):
        if self.remain < numbytes:
            raise ValueError("Can't skip %d bytes in buffer of %d bytes" % (
                numbytes, self.remain)
            )
        self.file.seek(numbytes, 1)
        self.remain = self.remain - numbytes

    def newfile(self):
        raise NotImplementedError()

    def prune(self):
        file = self.file
        if self.remain == 0:
            read_pos = file.tell()
            file.seek(0, 2)
            sz = file.tell()
            file.seek(read_pos)
            if sz == 0:
                # Nothing to prune.
                return
        nf = self.newfile()
        while True:
            data = file.read(COPY_BYTES)
            if not data:
                break
            nf.write(data)
        self.file = nf

    def getfile(self):
        return self.file

    def close(self):
        if hasattr(self.file, 'close'):
            self.file.close()
        self.remain = 0

class TempfileBasedBuffer(FileBasedBuffer):

    def __init__(self, from_buffer=None):
        FileBasedBuffer.__init__(self, self.newfile(), from_buffer)

    def newfile(self):
        from tempfile import TemporaryFile
        return TemporaryFile('w+b')

class BytesIOBasedBuffer(FileBasedBuffer):

    def __init__(self, from_buffer=None):
        if from_buffer is not None:
            FileBasedBuffer.__init__(self, BytesIO(), from_buffer)
        else:
            # Shortcut. :-)
            self.file = BytesIO()

    def newfile(self):
        return BytesIO()

class ReadOnlyFileBasedBuffer(FileBasedBuffer):
    # used as wsgi.file_wrapper

    def __init__(self, file, block_size=32768):
        self.file = file
        self.block_size = block_size # for __iter__

    def prepare(self, size=None):
        if hasattr(self.file, 'seek') and hasattr(self.file, 'tell'):
            start_pos = self.file.tell()
            self.file.seek(0, 2)
            end_pos = self.file.tell()
            self.file.seek(start_pos)
            fsize = end_pos - start_pos
            if size is None:
                self.remain = fsize
            else:
                self.remain = min(fsize, size)
        return self.remain

    def get(self, numbytes=-1, skip=False):
        # never read more than self.remain (it can be user-specified)
        if numbytes == -1 or numbytes > self.remain:
            numbytes = self.remain
        file = self.file
        if not skip:
            read_pos = file.tell()
        res = file.read(numbytes)
        if skip:
            self.remain -= len(res)
        else:
            file.seek(read_pos)
        return res

    def __iter__(self): # called by task if self.filelike has no seek/tell
        return self

    def next(self):
        val = self.file.read(self.block_size)
        if not val:
            raise StopIteration
        return val

    __next__ = next # py3

    def append(self, s):
        raise NotImplementedError

class OverflowableBuffer(object):
    """
    This buffer implementation has four stages:
    - No data
    - Bytes-based buffer
    - BytesIO-based buffer
    - Temporary file storage
    The first two stages are fastest for simple transfers.
    """

    overflowed = False
    buf = None
    strbuf = b'' # Bytes-based buffer.

    def __init__(self, overflow):
        # overflow is the maximum to be stored in a StringIO buffer.
        self.overflow = overflow

    def __len__(self):
        buf = self.buf
        if buf is not None:
            # use buf.__len__ rather than len(buf) FBO of not getting
            # OverflowError on Python 2
            return buf.__len__()
        else:
            return self.strbuf.__len__()

    def __nonzero__(self):
        # use self.__len__ rather than len(self) FBO of not getting
        # OverflowError on Python 2
        return self.__len__() > 0

    __bool__ = __nonzero__ # py3

    def _create_buffer(self):
        strbuf = self.strbuf
        if len(strbuf) >= self.overflow:
            self._set_large_buffer()
        else:
            self._set_small_buffer()
        buf = self.buf
        if strbuf:
            buf.append(self.strbuf)
            self.strbuf = b''
        return buf

    def _set_small_buffer(self):
        self.buf = BytesIOBasedBuffer(self.buf)
        self.overflowed = False

    def _set_large_buffer(self):
        self.buf = TempfileBasedBuffer(self.buf)
        self.overflowed = True

    def append(self, s):
        buf = self.buf
        if buf is None:
            strbuf = self.strbuf
            if len(strbuf) + len(s) < STRBUF_LIMIT:
                self.strbuf = strbuf + s
                return
            buf = self._create_buffer()
        buf.append(s)
        # use buf.__len__ rather than len(buf) FBO of not getting
        # OverflowError on Python 2
        sz = buf.__len__()
        if not self.overflowed:
            if sz >= self.overflow:
                self._set_large_buffer()

    def get(self, numbytes=-1, skip=False):
        buf = self.buf
        if buf is None:
            strbuf = self.strbuf
            if not skip:
                return strbuf
            buf = self._create_buffer()
        return buf.get(numbytes, skip)

    def skip(self, numbytes, allow_prune=False):
        buf = self.buf
        if buf is None:
            if allow_prune and numbytes == len(self.strbuf):
                # We could slice instead of converting to
                # a buffer, but that would eat up memory in
                # large transfers.
                self.strbuf = b''
                return
            buf = self._create_buffer()
        buf.skip(numbytes, allow_prune)

    def prune(self):
        """
        A potentially expensive operation that removes all data
        already retrieved from the buffer.
        """
        buf = self.buf
        if buf is None:
            self.strbuf = b''
            return
        buf.prune()
        if self.overflowed:
            # use buf.__len__ rather than len(buf) FBO of not getting
            # OverflowError on Python 2
            sz = buf.__len__()
            if sz < self.overflow:
                # Revert to a faster buffer.
                self._set_small_buffer()

    def getfile(self):
        buf = self.buf
        if buf is None:
            buf = self._create_buffer()
        return buf.getfile()

    def close(self):
        buf = self.buf
        if buf is not None:
            buf.close()

########NEW FILE########
__FILENAME__ = channel
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
import asyncore
import socket
import time
import traceback

from waitress.buffers import (
    OverflowableBuffer,
    ReadOnlyFileBasedBuffer,
)

from waitress.parser import HTTPRequestParser

from waitress.compat import thread

from waitress.task import (
    ErrorTask,
    WSGITask,
)

from waitress.utilities import (
    logging_dispatcher,
    InternalServerError,
)

class HTTPChannel(logging_dispatcher, object):
    """
    Setting self.requests = [somerequest] prevents more requests from being
    received until the out buffers have been flushed.

    Setting self.requests = [] allows more requests to be received.
    """

    task_class = WSGITask
    error_task_class = ErrorTask
    parser_class = HTTPRequestParser

    request = None               # A request parser instance
    last_activity = 0            # Time of last activity
    will_close = False           # set to True to close the socket.
    close_when_flushed = False   # set to True to close the socket when flushed
    requests = ()                # currently pending requests
    sent_continue = False        # used as a latch after sending 100 continue
    force_flush = False          # indicates a need to flush the outbuf

    #
    # ASYNCHRONOUS METHODS (including __init__)
    #

    def __init__(
            self,
            server,
            sock,
            addr,
            adj,
            map=None,
            ):
        self.server = server
        self.adj = adj
        self.outbufs = [OverflowableBuffer(adj.outbuf_overflow)]
        self.creation_time = self.last_activity = time.time()

        # task_lock used to push/pop requests
        self.task_lock = thread.allocate_lock()
        # outbuf_lock used to access any outbuf
        self.outbuf_lock = thread.allocate_lock()

        asyncore.dispatcher.__init__(self, sock, map=map)

        # Don't let asyncore.dispatcher throttle self.addr on us.
        self.addr = addr

    def any_outbuf_has_data(self):
        for outbuf in self.outbufs:
            if bool(outbuf):
                return True
        return False

    def total_outbufs_len(self):
        # genexpr == more funccalls
        # use b.__len__ rather than len(b) FBO of not getting OverflowError
        # on Python 2
        return sum([b.__len__() for b in self.outbufs]) 

    def writable(self):
        # if there's data in the out buffer or we've been instructed to close
        # the channel (possibly by our server maintenance logic), run
        # handle_write
        return self.any_outbuf_has_data() or self.will_close

    def handle_write(self):
        # Precondition: there's data in the out buffer to be sent, or
        # there's a pending will_close request
        if not self.connected:
            # we dont want to close the channel twice
            return

        # try to flush any pending output
        if not self.requests:
            # 1. There are no running tasks, so we don't need to try to lock
            #    the outbuf before sending
            # 2. The data in the out buffer should be sent as soon as possible
            #    because it's either data left over from task output
            #    or a 100 Continue line sent within "received".
            flush = self._flush_some
        elif self.force_flush:
            # 1. There's a running task, so we need to try to lock
            #    the outbuf before sending
            # 2. This is the last chunk sent by the Nth of M tasks in a
            #    sequence on this channel, so flush it regardless of whether
            #    it's >= self.adj.send_bytes.  We need to do this now, or it
            #    won't get done.
            flush = self._flush_some_if_lockable
            self.force_flush = False
        elif (self.total_outbufs_len() >= self.adj.send_bytes):
            # 1. There's a running task, so we need to try to lock
            #    the outbuf before sending
            # 2. Only try to send if the data in the out buffer is larger
            #    than self.adj_bytes to avoid TCP fragmentation
            flush = self._flush_some_if_lockable
        else:
            # 1. There's not enough data in the out buffer to bother to send
            #    right now.
            flush = None

        if flush:
            try:
                flush()
            except socket.error:
                if self.adj.log_socket_errors:
                    self.logger.exception('Socket error')
                self.will_close = True
            except:
                self.logger.exception('Unexpected exception when flushing')
                self.will_close = True

        if self.close_when_flushed and not self.any_outbuf_has_data():
            self.close_when_flushed = False
            self.will_close = True

        if self.will_close:
            self.handle_close()

    def readable(self):
        # We might want to create a new task.  We can only do this if:
        # 1. We're not already about to close the connection.
        # 2. There's no already currently running task(s).
        # 3. There's no data in the output buffer that needs to be sent
        #    before we potentially create a new task.
        return not (self.will_close or self.requests or
                    self.any_outbuf_has_data())

    def handle_read(self):
        try:
            data = self.recv(self.adj.recv_bytes)
        except socket.error:
            if self.adj.log_socket_errors:
                self.logger.exception('Socket error')
            self.handle_close()
            return
        if data:
            self.last_activity = time.time()
            self.received(data)

    def received(self, data):
        """
        Receives input asynchronously and assigns one or more requests to the
        channel.
        """
        # Preconditions: there's no task(s) already running
        request = self.request
        requests = []

        if not data:
            return False

        while data:
            if request is None:
                request = self.parser_class(self.adj)
            n = request.received(data)
            if request.expect_continue and request.headers_finished:
                # guaranteed by parser to be a 1.1 request
                request.expect_continue = False
                if not self.sent_continue:
                    # there's no current task, so we don't need to try to
                    # lock the outbuf to append to it.
                    self.outbufs[-1].append(b'HTTP/1.1 100 Continue\r\n\r\n')
                    self.sent_continue = True
                    self._flush_some()
                    request.completed = False
            if request.completed:
                # The request (with the body) is ready to use.
                self.request = None
                if not request.empty:
                    requests.append(request)
                request = None
            else:
                self.request = request
            if n >= len(data):
                break
            data = data[n:]

        if requests:
            self.requests = requests
            self.server.add_task(self)

        return True

    def _flush_some_if_lockable(self):
        # Since our task may be appending to the outbuf, we try to acquire
        # the lock, but we don't block if we can't.
        locked = self.outbuf_lock.acquire(0)
        if locked:
            try:
                self._flush_some()
            finally:
                self.outbuf_lock.release()

    def _flush_some(self):
        # Send as much data as possible to our client

        sent = 0
        dobreak = False

        while True:
            outbuf = self.outbufs[0]
            # use outbuf.__len__ rather than len(outbuf) FBO of not getting
            # OverflowError on Python 2
            outbuflen = outbuf.__len__()
            if outbuflen <= 0:
                # self.outbufs[-1] must always be a writable outbuf
                if len(self.outbufs) > 1:
                    toclose = self.outbufs.pop(0)
                    try:
                        toclose.close()
                    except:
                        self.logger.exception(
                            'Unexpected error when closing an outbuf')
                    continue # pragma: no cover (coverage bug, it is hit)
                else:
                    dobreak = True

            while outbuflen > 0:
                chunk = outbuf.get(self.adj.send_bytes)
                num_sent = self.send(chunk)
                if num_sent:
                    outbuf.skip(num_sent, True)
                    outbuflen -= num_sent
                    sent += num_sent
                else:
                    dobreak = True
                    break

            if dobreak:
                break

        if sent:
            self.last_activity = time.time()
            return True

        return False

    def handle_close(self):
        for outbuf in self.outbufs:
            try:
                outbuf.close()
            except:
                self.logger.exception(
                    'Unknown exception while trying to close outbuf')
        self.connected = False
        asyncore.dispatcher.close(self)

    def add_channel(self, map=None):
        """See asyncore.dispatcher

        This hook keeps track of opened channels.
        """
        asyncore.dispatcher.add_channel(self, map)
        self.server.active_channels[self._fileno] = self

    def del_channel(self, map=None):
        """See asyncore.dispatcher

        This hook keeps track of closed channels.
        """
        fd = self._fileno # next line sets this to None
        asyncore.dispatcher.del_channel(self, map)
        ac = self.server.active_channels
        if fd in ac:
            del ac[fd]

    #
    # SYNCHRONOUS METHODS
    #

    def write_soon(self, data):
        if data:
            # the async mainloop might be popping data off outbuf; we can
            # block here waiting for it because we're in a task thread
            with self.outbuf_lock:
                if data.__class__ is ReadOnlyFileBasedBuffer:
                    # they used wsgi.file_wrapper
                    self.outbufs.append(data)
                    nextbuf = OverflowableBuffer(self.adj.outbuf_overflow)
                    self.outbufs.append(nextbuf)
                else:
                    self.outbufs[-1].append(data)
            # XXX We might eventually need to pull the trigger here (to
            # instruct select to stop blocking), but it slows things down so
            # much that I'll hold off for now; "server push" on otherwise
            # unbusy systems may suffer.
            return len(data)
        return 0

    def service(self):
        """Execute all pending requests """
        with self.task_lock:
            while self.requests:
                request = self.requests[0]
                if request.error:
                    task = self.error_task_class(self, request)
                else:
                    task = self.task_class(self, request)
                try:
                    task.service()
                except:
                    self.logger.exception('Exception when serving %s' %
                                          task.request.path)
                    if not task.wrote_header:
                        if self.adj.expose_tracebacks:
                            body = traceback.format_exc()
                        else:
                            body = ('The server encountered an unexpected '
                                    'internal server error')
                        req_version = request.version
                        req_headers = request.headers
                        request = self.parser_class(self.adj)
                        request.error = InternalServerError(body)
                        # copy some original request attributes to fulfill
                        # HTTP 1.1 requirements
                        request.version = req_version
                        try:
                            request.headers['CONNECTION'] = req_headers[
                                'CONNECTION']
                        except KeyError:
                            pass
                        task = self.error_task_class(self, request)
                        task.service() # must not fail
                    else:
                        task.close_on_finish = True
                # we cannot allow self.requests to drop to empty til
                # here; otherwise the mainloop gets confused
                if task.close_on_finish:
                    self.close_when_flushed = True
                    for request in self.requests:
                        request.close()
                    self.requests = []
                else:
                    request = self.requests.pop(0)
                    request.close()

        self.force_flush = True
        self.server.pull_trigger()
        self.last_activity = time.time()

    def cancel(self):
        """ Cancels all pending requests """
        self.force_flush = True
        self.last_activity = time.time()
        self.requests = []

    def defer(self):
        pass

########NEW FILE########
__FILENAME__ = compat
import sys
import types

try:
    import urlparse
except ImportError: # pragma: no cover
    from urllib import parse as urlparse

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    long = int
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str
    long = long

if PY3: # pragma: no cover
    from urllib.parse import unquote_to_bytes
    def unquote_bytes_to_wsgi(bytestring):
        return unquote_to_bytes(bytestring).decode('latin-1')
else:
    from urlparse import unquote as unquote_to_bytes
    def unquote_bytes_to_wsgi(bytestring):
        return unquote_to_bytes(bytestring)

def text_(s, encoding='latin-1', errors='strict'):
    """ If ``s`` is an instance of ``binary_type``, return
    ``s.decode(encoding, errors)``, otherwise return ``s``"""
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    return s # pragma: no cover

if PY3: # pragma: no cover
    def tostr(s):
        if isinstance(s, text_type):
            s = s.encode('latin-1')
        return str(s, 'latin-1', 'strict')

    def tobytes(s):
        return bytes(s, 'latin-1')
else:
    tostr = str

    def tobytes(s):
        return s

try:
    from Queue import (
        Queue,
        Empty,
    )
except ImportError: # pragma: no cover
    from queue import (
        Queue,
        Empty,
    )

try:
    import thread
except ImportError: # pragma: no cover
    import _thread as thread

if PY3: # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value is None:
            value = tp
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

    del builtins

else: # pragma: no cover
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

try:
    from StringIO import StringIO as NativeIO
except ImportError: # pragma: no cover
    from io import StringIO as NativeIO

try:
    import httplib
except ImportError: # pragma: no cover
    from http import client as httplib

try:
    MAXINT = sys.maxint
except AttributeError: # pragma: no cover
    MAXINT = sys.maxsize

########NEW FILE########
__FILENAME__ = parser
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""HTTP Request Parser

This server uses asyncore to accept connections and do initial
processing but threads to do work.
"""
import re
from io import BytesIO

from waitress.compat import (
    tostr,
    urlparse,
    unquote_bytes_to_wsgi,
)

from waitress.buffers import OverflowableBuffer

from waitress.receiver import (
    FixedStreamReceiver,
    ChunkedReceiver,
)

from waitress.utilities import (
    find_double_newline,
    RequestEntityTooLarge,
    RequestHeaderFieldsTooLarge,
    BadRequest,
)

class ParsingError(Exception):
    pass

class HTTPRequestParser(object):
    """A structure that collects the HTTP request.

    Once the stream is completed, the instance is passed to
    a server task constructor.
    """
    completed = False        # Set once request is completed.
    empty = False            # Set if no request was made.
    expect_continue = False  # client sent "Expect: 100-continue" header
    headers_finished = False # True when headers have been read
    header_plus = b''
    chunked = False
    content_length = 0
    header_bytes_received = 0
    body_bytes_received = 0
    body_rcv = None
    version = '1.0'
    error = None
    connection_close = False

    # Other attributes: first_line, header, headers, command, uri, version,
    # path, query, fragment

    def __init__(self, adj):
        """
        adj is an Adjustments object.
        """
        # headers is a mapping containing keys translated to uppercase
        # with dashes turned into underscores.
        self.headers = {}
        self.adj = adj

    def received(self, data):
        """
        Receives the HTTP stream for one request.  Returns the number of
        bytes consumed.  Sets the completed flag once both the header and the
        body have been received.
        """
        if self.completed:
            return 0 # Can't consume any more.
        datalen = len(data)
        br = self.body_rcv
        if br is None:
            # In header.
            s = self.header_plus + data
            index = find_double_newline(s)
            if index >= 0:
                # Header finished.
                header_plus = s[:index]
                consumed = len(data) - (len(s) - index)
                # Remove preceeding blank lines.
                header_plus = header_plus.lstrip()
                if not header_plus:
                    self.empty = True
                    self.completed = True
                else:
                    try:
                        self.parse_header(header_plus)
                    except ParsingError as e:
                        self.error = BadRequest(e.args[0])
                        self.completed = True
                    else:
                        if self.body_rcv is None:
                            # no content-length header and not a t-e: chunked
                            # request
                            self.completed = True
                        if self.content_length > 0:
                            max_body = self.adj.max_request_body_size
                            # we won't accept this request if the content-length
                            # is too large
                            if self.content_length >= max_body:
                                self.error = RequestEntityTooLarge(
                                    'exceeds max_body of %s' % max_body)
                                self.completed = True
                self.headers_finished = True
                return consumed
            else:
                # Header not finished yet.
                self.header_bytes_received += datalen
                max_header = self.adj.max_request_header_size
                if self.header_bytes_received >= max_header:
                    # malformed header, we need to construct some request
                    # on our own. we disregard the incoming(?) requests HTTP
                    # version and just use 1.0. IOW someone just sent garbage
                    # over the wire
                    self.parse_header(b'GET / HTTP/1.0\n')
                    self.error = RequestHeaderFieldsTooLarge(
                        'exceeds max_header of %s' % max_header)
                    self.completed = True
                self.header_plus = s
                return datalen
        else:
            # In body.
            consumed = br.received(data)
            self.body_bytes_received += consumed
            max_body = self.adj.max_request_body_size
            if self.body_bytes_received >= max_body:
                # this will only be raised during t-e: chunked requests
                self.error = RequestEntityTooLarge(
                    'exceeds max_body of %s' % max_body)
                self.completed = True
            elif br.error:
                # garbage in chunked encoding input probably
                self.error = br.error
                self.completed = True
            elif br.completed:
                # The request (with the body) is ready to use.
                self.completed = True
                if self.chunked:
                    # We've converted the chunked transfer encoding request
                    # body into a normal request body, so we know its content
                    # length; set the header here.  We already popped the
                    # TRANSFER_ENCODING header in parse_header, so this will
                    # appear to the client to be an entirely non-chunked HTTP
                    # request with a valid content-length.
                    self.headers['CONTENT_LENGTH'] = str(br.__len__())
            return consumed

    def parse_header(self, header_plus):
        """
        Parses the header_plus block of text (the headers plus the
        first line of the request).
        """
        index = header_plus.find(b'\n')
        if index >= 0:
            first_line = header_plus[:index].rstrip()
            header = header_plus[index + 1:]
        else:
            first_line = header_plus.rstrip()
            header = b''

        self.first_line = first_line # for testing

        lines = get_header_lines(header)

        headers = self.headers
        for line in lines:
            index = line.find(b':')
            if index > 0:
                key = line[:index]
                value = line[index + 1:].strip()
                key1 = tostr(key.upper().replace(b'-', b'_'))
                # If a header already exists, we append subsequent values
                # seperated by a comma. Applications already need to handle
                # the comma seperated values, as HTTP front ends might do
                # the concatenation for you (behavior specified in RFC2616).
                try:
                    headers[key1] += tostr(b', ' + value)
                except KeyError:
                    headers[key1] = tostr(value)
            # else there's garbage in the headers?

        # command, uri, version will be bytes
        command, uri, version = crack_first_line(first_line)
        version = tostr(version)
        command = tostr(command)
        self.command = command
        self.version = version
        (self.proxy_scheme,
         self.proxy_netloc,
         self.path,
         self.query, self.fragment) = split_uri(uri)
        self.url_scheme = self.adj.url_scheme
        connection = headers.get('CONNECTION', '')

        if version == '1.0':
            if connection.lower() != 'keep-alive':
                self.connection_close = True

        if version == '1.1':
            # since the server buffers data from chunked transfers and clients
            # never need to deal with chunked requests, downstream clients
            # should not see the HTTP_TRANSFER_ENCODING header; we pop it
            # here
            te = headers.pop('TRANSFER_ENCODING', '')
            if te.lower() == 'chunked':
                self.chunked = True
                buf = OverflowableBuffer(self.adj.inbuf_overflow)
                self.body_rcv = ChunkedReceiver(buf)
            expect = headers.get('EXPECT', '').lower()
            self.expect_continue = expect == '100-continue'
            if connection.lower() == 'close':
                self.connection_close = True

        if not self.chunked:
            try:
                cl = int(headers.get('CONTENT_LENGTH', 0))
            except ValueError:
                cl = 0
            self.content_length = cl
            if cl > 0:
                buf = OverflowableBuffer(self.adj.inbuf_overflow)
                self.body_rcv = FixedStreamReceiver(cl, buf)

    def get_body_stream(self):
        body_rcv = self.body_rcv
        if body_rcv is not None:
            return body_rcv.getfile()
        else:
            return BytesIO()

    def close(self):
        body_rcv = self.body_rcv
        if body_rcv is not None:
            body_rcv.getbuf().close()

def split_uri(uri):
    # urlsplit handles byte input by returning bytes on py3, so
    # scheme, netloc, path, query, and fragment are bytes
    scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)
    return (
        tostr(scheme),
        tostr(netloc),
        unquote_bytes_to_wsgi(path),
        tostr(query),
        tostr(fragment),
    )

def get_header_lines(header):
    """
    Splits the header into lines, putting multi-line headers together.
    """
    r = []
    lines = header.split(b'\n')
    for line in lines:
        if line.startswith((b' ', b'\t')):
            if not r:
                # http://corte.si/posts/code/pathod/pythonservers/index.html
                raise ParsingError('Malformed header line "%s"' % tostr(line))
            r[-1] = r[-1] + line[1:]
        else:
            r.append(line)
    return r

first_line_re = re.compile(
    b'([^ ]+) '
    b'((?:[^ :?#]+://[^ ?#/]*(?:[0-9]{1,5})?)?[^ ]+)'
    b'(( HTTP/([0-9.]+))$|$)'
)

def crack_first_line(line):
    m = first_line_re.match(line)
    if m is not None and m.end() == len(line):
        if m.group(3):
            version = m.group(5)
        else:
            version = None
        command = m.group(1).upper()
        uri = m.group(2)
        return command, uri, version
    else:
        return b'', b'', b''

########NEW FILE########
__FILENAME__ = receiver
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Data Chunk Receiver
"""

from waitress.utilities import find_double_newline

from waitress.utilities import BadRequest

class FixedStreamReceiver(object):

    # See IStreamConsumer
    completed = False
    error = None

    def __init__(self, cl, buf):
        self.remain = cl
        self.buf = buf

    def __len__(self):
        return self.buf.__len__()
    
    def received(self, data):
        'See IStreamConsumer'
        rm = self.remain
        if rm < 1:
            self.completed = True # Avoid any chance of spinning
            return 0
        datalen = len(data)
        if rm <= datalen:
            self.buf.append(data[:rm])
            self.remain = 0
            self.completed = True
            return rm
        else:
            self.buf.append(data)
            self.remain -= datalen
            return datalen

    def getfile(self):
        return self.buf.getfile()

    def getbuf(self):
        return self.buf

class ChunkedReceiver(object):

    chunk_remainder = 0
    control_line = b''
    all_chunks_received = False
    trailer = b''
    completed = False
    error = None

    # max_control_line = 1024
    # max_trailer = 65536

    def __init__(self, buf):
        self.buf = buf

    def __len__(self):
        return self.buf.__len__()

    def received(self, s):
        # Returns the number of bytes consumed.
        if self.completed:
            return 0
        orig_size = len(s)
        while s:
            rm = self.chunk_remainder
            if rm > 0:
                # Receive the remainder of a chunk.
                to_write = s[:rm]
                self.buf.append(to_write)
                written = len(to_write)
                s = s[written:]
                self.chunk_remainder -= written
            elif not self.all_chunks_received:
                # Receive a control line.
                s = self.control_line + s
                pos = s.find(b'\n')
                if pos < 0:
                    # Control line not finished.
                    self.control_line = s
                    s = ''
                else:
                    # Control line finished.
                    line = s[:pos]
                    s = s[pos + 1:]
                    self.control_line = b''
                    line = line.strip()
                    if line:
                        # Begin a new chunk.
                        semi = line.find(b';')
                        if semi >= 0:
                            # discard extension info.
                            line = line[:semi]
                        try:
                            sz = int(line.strip(), 16) # hexadecimal
                        except ValueError: # garbage in input
                            self.error = BadRequest(
                                'garbage in chunked encoding input')
                            sz = 0
                        if sz > 0:
                            # Start a new chunk.
                            self.chunk_remainder = sz
                        else:
                            # Finished chunks.
                            self.all_chunks_received = True
                    # else expect a control line.
            else:
                # Receive the trailer.
                trailer = self.trailer + s
                if trailer.startswith(b'\r\n'):
                    # No trailer.
                    self.completed = True
                    return orig_size - (len(trailer) - 2)
                elif trailer.startswith(b'\n'):
                    # No trailer.
                    self.completed = True
                    return orig_size - (len(trailer) - 1)
                pos = find_double_newline(trailer)
                if pos < 0:
                    # Trailer not finished.
                    self.trailer = trailer
                    s = b''
                else:
                    # Finished the trailer.
                    self.completed = True
                    self.trailer = trailer[:pos]
                    return orig_size - (len(trailer) - pos)
        return orig_size

    def getfile(self):
        return self.buf.getfile()

    def getbuf(self):
        return self.buf

########NEW FILE########
__FILENAME__ = runner
##############################################################################
#
# Copyright (c) 2013 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Command line runner.
"""

from __future__ import print_function, unicode_literals

import getopt
import os
import os.path
import re
import sys

from waitress import serve
from waitress.adjustments import Adjustments

HELP = """\
Usage:

    {0} [OPTS] MODULE:OBJECT

Standard options:

    --help
        Show this information.

    --call
        Call the given object to get the WSGI application.

    --host=ADDR
        Hostname or IP address on which to listen, default is '0.0.0.0',
        which means "all IP addresses on this host".

    --port=PORT
        TCP port on which to listen, default is '8080'

    --unix-socket=PATH
        Path of Unix socket. If a socket path is specified, a Unix domain
        socket is made instead of the usual inet domain socket.

        Not available on Windows.

    --unix-socket-perms=PERMS
        Octal permissions to use for the Unix domain socket, default is
        '600'.

    --url-scheme=STR
        Default wsgi.url_scheme value, default is 'http'.

   --url-prefix=STR
        The ``SCRIPT_NAME`` WSGI environment value.  Setting this to anything
        except the empty string will cause the WSGI ``SCRIPT_NAME`` value to be
        the value passed minus any trailing slashes you add, and it will cause
        the ``PATH_INFO`` of any request which is prefixed with this value to
        be stripped of the prefix.  Default is the empty string.

    --ident=STR
        Server identity used in the 'Server' header in responses. Default
        is 'waitress'.

Tuning options:

    --threads=INT
        Number of threads used to process application logic, default is 4.

    --backlog=INT
        Connection backlog for the server. Default is 1024.

    --recv-bytes=INT
        Number of bytes to request when calling socket.recv(). Default is
        8192.

    --send-bytes=INT
        Number of bytes to send to socket.send(). Default is 18000.
        Multiples of 9000 should avoid partly-filled TCP packets.

    --outbuf-overflow=INT
        A temporary file should be created if the pending output is larger
        than this. Default is 1048576 (1MB).

    --inbuf-overflow=INT
        A temporary file should be created if the pending input is larger
        than this. Default is 524288 (512KB).

    --connection-limit=INT
        Stop creating new channelse if too many are already active.
        Default is 100.

    --cleanup-interval=INT
        Minimum seconds between cleaning up inactive channels. Default
        is 30. See '--channel-timeout'.

    --channel-timeout=INT
        Maximum number of seconds to leave inactive connections open.
        Default is 120. 'Inactive' is defined as 'has recieved no data
        from the client and has sent no data to the client'.

    --[no-]log-socket-errors
        Toggle whether premature client disconnect tracepacks ought to be
        logged. On by default.

    --max-request-header-size=INT
        Maximum size of all request headers combined. Default is 262144
        (256KB).

    --max-request-body-size=INT
        Maximum size of request body. Default is 1073741824 (1GB).

    --[no-]expose-tracebacks
        Toggle whether to expose tracebacks of unhandled exceptions to the
        client. Off by default.

    --asyncore-loop-timeout=INT
        The timeout value in seconds passed to asyncore.loop(). Default is 1.

    --asyncore-use-poll
        The use_poll argument passed to ``asyncore.loop()``. Helps overcome
        open file descriptors limit. Default is False.

"""

RUNNER_PATTERN = re.compile(r"""
    ^
    (?P<module>
        [a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*
    )
    :
    (?P<object>
        [a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*
    )
    $
    """, re.I | re.X)

def match(obj_name):
    matches = RUNNER_PATTERN.match(obj_name)
    if not matches:
        raise ValueError("Malformed application '{0}'".format(obj_name))
    return matches.group('module'), matches.group('object')

def resolve(module_name, object_name):
    """Resolve a named object in a module."""
    # We cast each segments due to an issue that has been found to manifest
    # in Python 2.6.6, but not 2.6.8, and may affect other revisions of Python
    # 2.6 and 2.7, whereby ``__import__`` chokes if the list passed in the
    # ``fromlist`` argument are unicode strings rather than 8-bit strings.
    # The error triggered is "TypeError: Item in ``fromlist '' not a string".
    # My guess is that this was fixed by checking against ``basestring``
    # rather than ``str`` sometime between the release of 2.6.6 and 2.6.8,
    # but I've yet to go over the commits. I know, however, that the NEWS
    # file makes no mention of such a change to the behaviour of
    # ``__import__``.
    segments = [str(segment) for segment in object_name.split('.')]
    obj = __import__(module_name, fromlist=segments[:1])
    for segment in segments:
        obj = getattr(obj, segment)
    return obj

def show_help(stream, name, error=None): # pragma: no cover
    if error is not None:
        print('Error: {0}\n'.format(error), file=stream)
    print(HELP.format(name), file=stream)

def run(argv=sys.argv, _serve=serve):
    """Command line runner."""
    name = os.path.basename(argv[0])

    try:
        kw, args = Adjustments.parse_args(argv[1:])
    except getopt.GetoptError as exc:
        show_help(sys.stderr, name, str(exc))
        return 1

    if kw['help']:
        show_help(sys.stdout, name)
        return 0

    if len(args) != 1:
        show_help(sys.stderr, name, 'Specify one application only')
        return 1

    try:
        module, obj_name = match(args[0])
    except ValueError as exc:
        show_help(sys.stderr, name, str(exc))
        return 1

    # Add the current directory onto sys.path
    sys.path.append(os.getcwd())

    # Get the WSGI function.
    try:
        app = resolve(module, obj_name)
    except ImportError:
        show_help(sys.stderr, name, "Bad module '{0}'".format(module))
        return 1
    except AttributeError:
        show_help(sys.stderr, name, "Bad object name '{0}'".format(obj_name))
        return 1
    if kw['call']:
        app = app()

    # These arguments are specific to the runner, not waitress itself.
    del kw['call'], kw['help']

    _serve(app, **kw)
    return 0

########NEW FILE########
__FILENAME__ = server
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import asyncore
import os
import os.path
import socket
import time

from waitress import trigger
from waitress.adjustments import Adjustments
from waitress.channel import HTTPChannel
from waitress.task import ThreadedTaskDispatcher
from waitress.utilities import cleanup_unix_socket, logging_dispatcher

def create_server(application,
                  map=None,
                  _start=True,      # test shim
                  _sock=None,       # test shim
                  _dispatcher=None, # test shim
                  **kw              # adjustments
                  ):
    """
    if __name__ == '__main__':
        server = create_server(app)
        server.run()
    """
    adj = Adjustments(**kw)
    if adj.unix_socket and hasattr(socket, 'AF_UNIX'):
        cls = UnixWSGIServer
    else:
        cls = TcpWSGIServer
    return cls(application, map, _start, _sock, _dispatcher, adj)

class BaseWSGIServer(logging_dispatcher, object):

    channel_class = HTTPChannel
    next_channel_cleanup = 0
    socketmod = socket # test shim
    asyncore = asyncore # test shim
    family = None

    def __init__(self,
                 application,
                 map=None,
                 _start=True,      # test shim
                 _sock=None,       # test shim
                 _dispatcher=None, # test shim
                 adj=None,         # adjustments
                 **kw
                 ):
        if adj is None:
            adj = Adjustments(**kw)
        self.application = application
        self.adj = adj
        self.trigger = trigger.trigger(map)
        if _dispatcher is None:
            _dispatcher = ThreadedTaskDispatcher()
            _dispatcher.set_thread_count(self.adj.threads)
        self.task_dispatcher = _dispatcher
        self.asyncore.dispatcher.__init__(self, _sock, map=map)
        if _sock is None:
            self.create_socket(self.family, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind_server_socket()
        self.effective_host, self.effective_port = self.getsockname()
        self.server_name = self.get_server_name(self.adj.host)
        self.active_channels = {}
        if _start:
            self.accept_connections()

    def bind_server_socket(self):
        raise NotImplementedError # pragma: no cover

    def get_server_name(self, ip):
        """Given an IP or hostname, try to determine the server name."""
        if ip:
            server_name = str(ip)
        else:
            server_name = str(self.socketmod.gethostname())
        # Convert to a host name if necessary.
        for c in server_name:
            if c != '.' and not c.isdigit():
                return server_name
        try:
            if server_name == '0.0.0.0':
                return 'localhost'
            server_name = self.socketmod.gethostbyaddr(server_name)[0]
        except socket.error: # pragma: no cover
            pass
        return server_name

    def getsockname(self):
        raise NotImplementedError # pragma: no cover

    def accept_connections(self):
        self.accepting = True
        self.socket.listen(self.adj.backlog) # Get around asyncore NT limit

    def add_task(self, task):
        self.task_dispatcher.add_task(task)

    def readable(self):
        now = time.time()
        if now >= self.next_channel_cleanup:
            self.next_channel_cleanup = now + self.adj.cleanup_interval
            self.maintenance(now)
        return (self.accepting and len(self._map) < self.adj.connection_limit)

    def writable(self):
        return False

    def handle_read(self):
        pass

    def handle_connect(self):
        pass

    def handle_accept(self):
        try:
            v = self.accept()
            if v is None:
                return
            conn, addr = v
        except socket.error:
            # Linux: On rare occasions we get a bogus socket back from
            # accept.  socketmodule.c:makesockaddr complains that the
            # address family is unknown.  We don't want the whole server
            # to shut down because of this.
            if self.adj.log_socket_errors:
                self.logger.warning('server accept() threw an exception',
                                    exc_info=True)
            return
        self.set_socket_options(conn)
        addr = self.fix_addr(addr)
        self.channel_class(self, conn, addr, self.adj, map=self._map)

    def run(self):
        try:
            self.asyncore.loop(
                timeout=self.adj.asyncore_loop_timeout,
                map=self._map,
                use_poll=self.adj.asyncore_use_poll,
            )
        except (SystemExit, KeyboardInterrupt):
            self.task_dispatcher.shutdown()

    def pull_trigger(self):
        self.trigger.pull_trigger()

    def set_socket_options(self, conn):
        pass

    def fix_addr(self, addr):
        return addr

    def maintenance(self, now):
        """
        Closes channels that have not had any activity in a while.

        The timeout is configured through adj.channel_timeout (seconds).
        """
        cutoff = now - self.adj.channel_timeout
        for channel in self.active_channels.values():
            if (not channel.requests) and channel.last_activity < cutoff:
                channel.will_close = True

class TcpWSGIServer(BaseWSGIServer):

    family = socket.AF_INET

    def bind_server_socket(self):
        self.bind((self.adj.host, self.adj.port))

    def getsockname(self):
        return self.socket.getsockname()

    def set_socket_options(self, conn):
        for (level, optname, value) in self.adj.socket_options:
            conn.setsockopt(level, optname, value)

if hasattr(socket, 'AF_UNIX'):

    class UnixWSGIServer(BaseWSGIServer):

        family = socket.AF_UNIX

        def bind_server_socket(self):
            cleanup_unix_socket(self.adj.unix_socket)
            self.bind(self.adj.unix_socket)
            if os.path.exists(self.adj.unix_socket):
                os.chmod(self.adj.unix_socket, self.adj.unix_socket_perms)

        def getsockname(self):
            return ('unix', self.socket.getsockname())

        def fix_addr(self, addr):
            return ('localhost', None)

# Compatibility alias.
WSGIServer = TcpWSGIServer

########NEW FILE########
__FILENAME__ = task
##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import socket
import sys
import time

from waitress.buffers import ReadOnlyFileBasedBuffer

from waitress.compat import (
    tobytes,
    Queue,
    Empty,
    thread,
    reraise,
)

from waitress.utilities import (
    build_http_date,
    logger,
)

rename_headers = {  # or keep them without the HTTP_ prefix added
    'CONTENT_LENGTH': 'CONTENT_LENGTH',
    'CONTENT_TYPE': 'CONTENT_TYPE',
}

hop_by_hop = frozenset((
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade'
))

class JustTesting(Exception):
    pass

class ThreadedTaskDispatcher(object):
    """A Task Dispatcher that creates a thread for each task.
    """
    stop_count = 0 # Number of threads that will stop soon.
    start_new_thread = thread.start_new_thread
    logger = logger

    def __init__(self):
        self.threads = {} # { thread number -> 1 }
        self.queue = Queue()
        self.thread_mgmt_lock = thread.allocate_lock()

    def handler_thread(self, thread_no):
        threads = self.threads
        try:
            while threads.get(thread_no):
                task = self.queue.get()
                if task is None:
                    # Special value: kill this thread.
                    break
                try:
                    task.service()
                except Exception as e:
                    self.logger.exception(
                        'Exception when servicing %r' % task)
                    if isinstance(e, JustTesting):
                        break
        finally:
            mlock = self.thread_mgmt_lock
            mlock.acquire()
            try:
                self.stop_count -= 1
                threads.pop(thread_no, None)
            finally:
                mlock.release()

    def set_thread_count(self, count):
        mlock = self.thread_mgmt_lock
        mlock.acquire()
        try:
            threads = self.threads
            thread_no = 0
            running = len(threads) - self.stop_count
            while running < count:
                # Start threads.
                while thread_no in threads:
                    thread_no = thread_no + 1
                threads[thread_no] = 1
                running += 1
                self.start_new_thread(self.handler_thread, (thread_no,))
                thread_no = thread_no + 1
            if running > count:
                # Stop threads.
                to_stop = running - count
                self.stop_count += to_stop
                for n in range(to_stop):
                    self.queue.put(None)
                    running -= 1
        finally:
            mlock.release()

    def add_task(self, task):
        try:
            task.defer()
            self.queue.put(task)
        except:
            task.cancel()
            raise

    def shutdown(self, cancel_pending=True, timeout=5):
        self.set_thread_count(0)
        # Ensure the threads shut down.
        threads = self.threads
        expiration = time.time() + timeout
        while threads:
            if time.time() >= expiration:
                self.logger.warning(
                    "%d thread(s) still running" %
                    len(threads))
                break
            time.sleep(0.1)
        if cancel_pending:
            # Cancel remaining tasks.
            try:
                queue = self.queue
                while not queue.empty():
                    task = queue.get()
                    if task is not None:
                        task.cancel()
            except Empty: # pragma: no cover
                pass
            return True
        return False

class Task(object):
    close_on_finish = False
    status = '200 OK'
    wrote_header = False
    start_time = 0
    content_length = None
    content_bytes_written = 0
    logged_write_excess = False
    complete = False
    chunked_response = False
    logger = logger

    def __init__(self, channel, request):
        self.channel = channel
        self.request = request
        self.response_headers = []
        version = request.version
        if version not in ('1.0', '1.1'):
            # fall back to a version we support.
            version = '1.0'
        self.version = version

    def service(self):
        try:
            try:
                self.start()
                self.execute()
                self.finish()
            except socket.error:
                self.close_on_finish = True
                if self.channel.adj.log_socket_errors:
                    raise
        finally:
            pass

    def cancel(self):
        self.close_on_finish = True

    def defer(self):
        pass

    def build_response_header(self):
        version = self.version
        # Figure out whether the connection should be closed.
        connection = self.request.headers.get('CONNECTION', '').lower()
        response_headers = self.response_headers
        content_length_header = None
        date_header = None
        server_header = None
        connection_close_header = None

        for i, (headername, headerval) in enumerate(response_headers):
            headername = '-'.join(
                [x.capitalize() for x in headername.split('-')]
            )
            if headername == 'Content-Length':
                content_length_header = headerval
            if headername == 'Date':
                date_header = headerval
            if headername == 'Server':
                server_header = headerval
            if headername == 'Connection':
                connection_close_header = headerval.lower()
            # replace with properly capitalized version
            response_headers[i] = (headername, headerval)

        if content_length_header is None and self.content_length is not None:
            content_length_header = str(self.content_length)
            self.response_headers.append(
                ('Content-Length', content_length_header)
            )

        def close_on_finish():
            if connection_close_header is None:
                response_headers.append(('Connection', 'close'))
            self.close_on_finish = True

        if version == '1.0':
            if connection == 'keep-alive':
                if not content_length_header:
                    close_on_finish()
                else:
                    response_headers.append(('Connection', 'Keep-Alive'))
            else:
                close_on_finish()

        elif version == '1.1':
            if connection == 'close':
                close_on_finish()

            if not content_length_header:
                response_headers.append(('Transfer-Encoding', 'chunked'))
                self.chunked_response = True
                if not self.close_on_finish:
                    close_on_finish()

            # under HTTP 1.1 keep-alive is default, no need to set the header
        else:
            raise AssertionError('neither HTTP/1.0 or HTTP/1.1')

        # Set the Server and Date field, if not yet specified. This is needed
        # if the server is used as a proxy.
        ident = self.channel.server.adj.ident
        if not server_header:
            response_headers.append(('Server', ident))
        else:
            response_headers.append(('Via', ident))
        if not date_header:
            response_headers.append(('Date', build_http_date(self.start_time)))

        first_line = 'HTTP/%s %s' % (self.version, self.status)
        # NB: sorting headers needs to preserve same-named-header order
        # as per RFC 2616 section 4.2; thus the key=lambda x: x[0] here;
        # rely on stable sort to keep relative position of same-named headers
        next_lines = ['%s: %s' % hv for hv in sorted(
                self.response_headers, key=lambda x: x[0])]
        lines = [first_line] + next_lines
        res = '%s\r\n\r\n' % '\r\n'.join(lines)
        return tobytes(res)

    def remove_content_length_header(self):
        for i, (header_name, header_value) in enumerate(self.response_headers):
            if header_name.lower() == 'content-length':
                del self.response_headers[i]

    def start(self):
        self.start_time = time.time()

    def finish(self):
        if not self.wrote_header:
            self.write(b'')
        if self.chunked_response:
            # not self.write, it will chunk it!
            self.channel.write_soon(b'0\r\n\r\n')

    def write(self, data):
        if not self.complete:
            raise RuntimeError('start_response was not called before body '
                               'written')
        channel = self.channel
        if not self.wrote_header:
            rh = self.build_response_header()
            channel.write_soon(rh)
            self.wrote_header = True
        if data:
            towrite = data
            cl = self.content_length
            if self.chunked_response:
                # use chunked encoding response
                towrite = tobytes(hex(len(data))[2:].upper()) + b'\r\n'
                towrite += data + b'\r\n'
            elif cl is not None:
                towrite = data[:cl - self.content_bytes_written]
                self.content_bytes_written += len(towrite)
                if towrite != data and not self.logged_write_excess:
                    self.logger.warning(
                        'application-written content exceeded the number of '
                        'bytes specified by Content-Length header (%s)' % cl)
                    self.logged_write_excess = True
            if towrite:
                channel.write_soon(towrite)

class ErrorTask(Task):
    """ An error task produces an error response
    """
    complete = True

    def execute(self):
        e = self.request.error
        body = '%s\r\n\r\n%s' % (e.reason, e.body)
        tag = '\r\n\r\n(generated by waitress)'
        body = body + tag
        self.status = '%s %s' % (e.code, e.reason)
        cl = len(body)
        self.content_length = cl
        self.response_headers.append(('Content-Length', str(cl)))
        self.response_headers.append(('Content-Type', 'text/plain'))
        if self.version == '1.1':
            connection = self.request.headers.get('CONNECTION', '').lower()
            if connection == 'close':
                self.response_headers.append(('Connection', 'close'))
            # under HTTP 1.1 keep-alive is default, no need to set the header
        else:
            # HTTP 1.0
            self.response_headers.append(('Connection', 'close'))
        self.close_on_finish = True
        self.write(tobytes(body))

class WSGITask(Task):
    """A WSGI task produces a response from a WSGI application.
    """
    environ = None

    def execute(self):
        env = self.get_environment()

        def start_response(status, headers, exc_info=None):
            if self.complete and not exc_info:
                raise AssertionError("start_response called a second time "
                                     "without providing exc_info.")
            if exc_info:
                try:
                    if self.complete:
                        # higher levels will catch and handle raised exception:
                        # 1. "service" method in task.py
                        # 2. "service" method in channel.py
                        # 3. "handler_thread" method in task.py
                        reraise(exc_info[0], exc_info[1], exc_info[2])
                    else:
                        # As per WSGI spec existing headers must be cleared
                        self.response_headers = []
                finally:
                    exc_info = None

            self.complete = True

            if not status.__class__ is str:
                raise AssertionError('status %s is not a string' % status)

            self.status = status

            # Prepare the headers for output
            for k, v in headers:
                if not k.__class__ is str:
                    raise AssertionError(
                        'Header name %r is not a string in %r' % (k, (k, v))
                    )
                if not v.__class__ is str:
                    raise AssertionError(
                        'Header value %r is not a string in %r' % (v, (k, v))
                    )
                kl = k.lower()
                if kl == 'content-length':
                    self.content_length = int(v)
                elif kl in hop_by_hop:
                    raise AssertionError(
                        '%s is a "hop-by-hop" header; it cannot be used by '
                        'a WSGI application (see PEP 3333)' % k)

            self.response_headers.extend(headers)

            # Return a method used to write the response data.
            return self.write

        # Call the application to handle the request and write a response
        app_iter = self.channel.server.application(env, start_response)

        if app_iter.__class__ is ReadOnlyFileBasedBuffer:
            # NB: do not put this inside the below try: finally: which closes
            # the app_iter; we need to defer closing the underlying file.  It's
            # intention that we don't want to call ``close`` here if the
            # app_iter is a ROFBB; the buffer (and therefore the file) will
            # eventually be closed within channel.py's _flush_some or
            # handle_close instead.
            cl = self.content_length
            size = app_iter.prepare(cl)
            if size:
                if cl != size:
                    if cl is not None:
                        self.remove_content_length_header()
                    self.content_length = size
                self.write(b'') # generate headers
                self.channel.write_soon(app_iter)
                return

        try:
            first_chunk_len = None
            for chunk in app_iter:
                if first_chunk_len is None:
                    first_chunk_len = len(chunk)
                    # Set a Content-Length header if one is not supplied.
                    # start_response may not have been called until first
                    # iteration as per PEP, so we must reinterrogate
                    # self.content_length here
                    if self.content_length is None:
                        app_iter_len = None
                        if hasattr(app_iter, '__len__'):
                            app_iter_len = len(app_iter)
                        if app_iter_len == 1:
                            self.content_length = first_chunk_len
                # transmit headers only after first iteration of the iterable
                # that returns a non-empty bytestring (PEP 3333)
                if chunk:
                    self.write(chunk)

            cl = self.content_length
            if cl is not None:
                if self.content_bytes_written != cl:
                    # close the connection so the client isn't sitting around
                    # waiting for more data when there are too few bytes
                    # to service content-length
                    self.close_on_finish = True
                    if self.request.command != 'HEAD':
                        self.logger.warning(
                            'application returned too few bytes (%s) '
                            'for specified Content-Length (%s) via app_iter' % (
                                self.content_bytes_written, cl),
                        )
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()

    def get_environment(self):
        """Returns a WSGI environment."""
        environ = self.environ
        if environ is not None:
            # Return the cached copy.
            return environ

        request = self.request
        path = request.path
        channel = self.channel
        server = channel.server
        url_prefix = server.adj.url_prefix

        if path.startswith('/'):
            # strip extra slashes at the beginning of a path that starts
            # with any number of slashes
            path = '/' + path.lstrip('/')

        if url_prefix:
            # NB: url_prefix is guaranteed by the configuration machinery to
            # be either the empty string or a string that starts with a single
            # slash and ends without any slashes
            if path == url_prefix:
                # if the path is the same as the url prefix, the SCRIPT_NAME
                # should be the url_prefix and PATH_INFO should be empty
                path = ''
            else:
                # if the path starts with the url prefix plus a slash,
                # the SCRIPT_NAME should be the url_prefix and PATH_INFO should
                # the value of path from the slash until its end
                url_prefix_with_trailing_slash = url_prefix + '/'
                if path.startswith(url_prefix_with_trailing_slash):
                    path = path[len(url_prefix):]

        environ = {}
        environ['REQUEST_METHOD'] = request.command.upper()
        environ['SERVER_PORT'] = str(server.effective_port)
        environ['SERVER_NAME'] = server.server_name
        environ['SERVER_SOFTWARE'] = server.adj.ident
        environ['SERVER_PROTOCOL'] = 'HTTP/%s' % self.version
        environ['SCRIPT_NAME'] = url_prefix
        environ['PATH_INFO'] = path
        environ['QUERY_STRING'] = request.query
        host = environ['REMOTE_ADDR'] = channel.addr[0]

        headers = dict(request.headers)
        if host == server.adj.trusted_proxy:
            wsgi_url_scheme = headers.pop('X_FORWARDED_PROTO',
                                          request.url_scheme)
        else:
            wsgi_url_scheme = request.url_scheme
        if wsgi_url_scheme not in ('http', 'https'):
            raise ValueError('Invalid X_FORWARDED_PROTO value')
        for key, value in headers.items():
            value = value.strip()
            mykey = rename_headers.get(key, None)
            if mykey is None:
                mykey = 'HTTP_%s' % key
            if mykey not in environ:
                environ[mykey] = value

        # the following environment variables are required by the WSGI spec
        environ['wsgi.version'] = (1, 0)
        environ['wsgi.url_scheme'] = wsgi_url_scheme
        environ['wsgi.errors'] = sys.stderr # apps should use the logging module
        environ['wsgi.multithread'] = True
        environ['wsgi.multiprocess'] = False
        environ['wsgi.run_once'] = False
        environ['wsgi.input'] = request.get_body_stream()
        environ['wsgi.file_wrapper'] = ReadOnlyFileBasedBuffer

        self.environ = environ
        return environ

########NEW FILE########
__FILENAME__ = badcl
def app(environ, start_response): # pragma: no cover
    body = b'abcdefghi'
    cl = len(body)
    if environ['PATH_INFO'] == '/short_body':
        cl = len(body) + 1
    if environ['PATH_INFO'] == '/long_body':
        cl = len(body) - 1
    start_response(
        '200 OK',
        [('Content-Length', str(cl)), ('Content-Type', 'text/plain')]
    )
    return [body]

########NEW FILE########
__FILENAME__ = echo
def app(environ, start_response): # pragma: no cover
    cl = environ.get('CONTENT_LENGTH', None)
    if cl is not None:
        cl = int(cl)
    body = environ['wsgi.input'].read(cl)
    cl = str(len(body))
    start_response(
        '200 OK',
        [('Content-Length', cl), ('Content-Type', 'text/plain')]
    )
    return [body]

########NEW FILE########
__FILENAME__ = error
def app(environ, start_response): # pragma: no cover
    cl = environ.get('CONTENT_LENGTH', None)
    if cl is not None:
        cl = int(cl)
    body = environ['wsgi.input'].read(cl)
    cl = str(len(body))
    if environ['PATH_INFO'] == '/before_start_response':
        raise ValueError('wrong')
    write = start_response(
        '200 OK',
        [('Content-Length', cl), ('Content-Type', 'text/plain')]
    )
    if environ['PATH_INFO'] == '/after_write_cb':
        write('abc')
    if environ['PATH_INFO'] == '/in_generator':
        def foo():
            yield 'abc'
            raise ValueError
        return foo()
    raise ValueError('wrong')

########NEW FILE########
__FILENAME__ = filewrapper
import os

here = os.path.dirname(os.path.abspath(__file__))
fn = os.path.join(here, 'groundhog1.jpg')

class KindaFilelike(object): # pragma: no cover

    def __init__(self, bytes):
        self.bytes = bytes

    def read(self, n):
        bytes = self.bytes[:n]
        self.bytes = self.bytes[n:]
        return bytes

def app(environ, start_response): # pragma: no cover
    path_info = environ['PATH_INFO']
    if path_info.startswith('/filelike'):
        f = open(fn, 'rb')
        f.seek(0, 2)
        cl = f.tell()
        f.seek(0)
        if path_info == '/filelike':
            headers = [
                ('Content-Length', str(cl)),
                ('Content-Type', 'image/jpeg'),
            ]
        elif path_info == '/filelike_nocl':
            headers = [('Content-Type', 'image/jpeg')]
        elif path_info == '/filelike_shortcl':
            # short content length
            headers = [
                ('Content-Length', '1'),
                ('Content-Type', 'image/jpeg'),
            ]
        else:
            # long content length (/filelike_longcl)
            headers = [
                ('Content-Length', str(cl + 10)),
                ('Content-Type', 'image/jpeg'),
            ]
    else:
        data = open(fn, 'rb').read()
        cl = len(data)
        f = KindaFilelike(data)
        if path_info == '/notfilelike':
            headers = [
                ('Content-Length', str(len(data))),
                ('Content-Type', 'image/jpeg'),
            ]
        elif path_info == '/notfilelike_nocl':
            headers = [('Content-Type', 'image/jpeg')]
        elif path_info == '/notfilelike_shortcl':
            # short content length
            headers = [
                ('Content-Length', '1'),
                ('Content-Type', 'image/jpeg'),
            ]
        else:
            # long content length (/notfilelike_longcl)
            headers = [
                ('Content-Length', str(cl + 10)),
                ('Content-Type', 'image/jpeg'),
            ]

    start_response(
        '200 OK',
        headers
    )
    return environ['wsgi.file_wrapper'](f, 8192)

########NEW FILE########
__FILENAME__ = getline
import sys

if __name__ == '__main__':
    try:
        from urllib.request import urlopen, URLError
    except ImportError:
        from urllib2 import urlopen, URLError

    url = sys.argv[1]
    headers = {'Content-Type': 'text/plain; charset=utf-8'}
    try:
        resp = urlopen(url)
        line = resp.readline().decode('ascii') # py3
    except URLError:
        line = 'failed to read %s' % url
    sys.stdout.write(line)
    sys.stdout.flush()

########NEW FILE########
__FILENAME__ = nocl
def chunks(l, n): # pragma: no cover
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]

def gen(body): # pragma: no cover
    for chunk in chunks(body, 10):
        yield chunk

def app(environ, start_response): # pragma: no cover
    cl = environ.get('CONTENT_LENGTH', None)
    if cl is not None:
        cl = int(cl)
    body = environ['wsgi.input'].read(cl)
    start_response(
        '200 OK',
        [('Content-Type', 'text/plain')]
    )
    if environ['PATH_INFO'] == '/list':
        return [body]
    if environ['PATH_INFO'] == '/list_lentwo':
        return [body[0:1], body[1:]]
    return gen(body)

########NEW FILE########
__FILENAME__ = runner
def app(): # pragma: no cover
    return None

def returns_app(): # pragma: no cover
    return app

########NEW FILE########
__FILENAME__ = sleepy
import time

def app(environ, start_response): # pragma: no cover
    if environ['PATH_INFO'] == '/sleepy':
        time.sleep(2)
        body = b'sleepy returned'
    else:
        body = b'notsleepy returned'
    cl = str(len(body))
    start_response(
        '200 OK',
        [('Content-Length', cl), ('Content-Type', 'text/plain')]
    )
    return [body]

########NEW FILE########
__FILENAME__ = toolarge
def app(environ, start_response): # pragma: no cover
    body = b'abcdef'
    cl = len(body)
    start_response(
        '200 OK',
        [('Content-Length', str(cl)), ('Content-Type', 'text/plain')]
    )
    return [body]

########NEW FILE########
__FILENAME__ = writecb
def app(environ, start_response): # pragma: no cover
    path_info = environ['PATH_INFO']
    if path_info == '/no_content_length':
        headers = []
    else:
        headers = [('Content-Length', '9')]
    write = start_response('200 OK', headers)
    if path_info == '/long_body':
        write(b'abcdefghij')
    elif path_info == '/short_body':
        write(b'abcdefgh')
    else:
        write(b'abcdefghi')
    return []

########NEW FILE########
__FILENAME__ = test_adjustments
import sys

if sys.version_info[:2] == (2, 6): # pragma: no cover
    import unittest2 as unittest
else: # pragma: no cover
    import unittest

class Test_asbool(unittest.TestCase):

    def _callFUT(self, s):
        from waitress.adjustments import asbool
        return asbool(s)

    def test_s_is_None(self):
        result = self._callFUT(None)
        self.assertEqual(result, False)

    def test_s_is_True(self):
        result = self._callFUT(True)
        self.assertEqual(result, True)

    def test_s_is_False(self):
        result = self._callFUT(False)
        self.assertEqual(result, False)

    def test_s_is_true(self):
        result = self._callFUT('True')
        self.assertEqual(result, True)

    def test_s_is_false(self):
        result = self._callFUT('False')
        self.assertEqual(result, False)

    def test_s_is_yes(self):
        result = self._callFUT('yes')
        self.assertEqual(result, True)

    def test_s_is_on(self):
        result = self._callFUT('on')
        self.assertEqual(result, True)

    def test_s_is_1(self):
        result = self._callFUT(1)
        self.assertEqual(result, True)

class TestAdjustments(unittest.TestCase):

    def _makeOne(self, **kw):
        from waitress.adjustments import Adjustments
        return Adjustments(**kw)

    def test_goodvars(self):
        inst = self._makeOne(
            host='host',
            port='8080',
            threads='5',
            trusted_proxy='192.168.1.1',
            url_scheme='https',
            backlog='20',
            recv_bytes='200',
            send_bytes='300',
            outbuf_overflow='400',
            inbuf_overflow='500',
            connection_limit='1000',
            cleanup_interval='1100',
            channel_timeout='1200',
            log_socket_errors='true',
            max_request_header_size='1300',
            max_request_body_size='1400',
            expose_tracebacks='true',
            ident='abc',
            asyncore_loop_timeout='5',
            asyncore_use_poll=True,
            unix_socket='/tmp/waitress.sock',
            unix_socket_perms='777',
            url_prefix='///foo/',
        )
        self.assertEqual(inst.host, 'host')
        self.assertEqual(inst.port, 8080)
        self.assertEqual(inst.threads, 5)
        self.assertEqual(inst.trusted_proxy, '192.168.1.1')
        self.assertEqual(inst.url_scheme, 'https')
        self.assertEqual(inst.backlog, 20)
        self.assertEqual(inst.recv_bytes, 200)
        self.assertEqual(inst.send_bytes, 300)
        self.assertEqual(inst.outbuf_overflow, 400)
        self.assertEqual(inst.inbuf_overflow, 500)
        self.assertEqual(inst.connection_limit, 1000)
        self.assertEqual(inst.cleanup_interval, 1100)
        self.assertEqual(inst.channel_timeout, 1200)
        self.assertEqual(inst.log_socket_errors, True)
        self.assertEqual(inst.max_request_header_size, 1300)
        self.assertEqual(inst.max_request_body_size, 1400)
        self.assertEqual(inst.expose_tracebacks, True)
        self.assertEqual(inst.asyncore_loop_timeout, 5)
        self.assertEqual(inst.asyncore_use_poll, True)
        self.assertEqual(inst.ident, 'abc')
        self.assertEqual(inst.unix_socket, '/tmp/waitress.sock')
        self.assertEqual(inst.unix_socket_perms, 0o777)
        self.assertEqual(inst.url_prefix, '/foo')

    def test_badvar(self):
        self.assertRaises(ValueError, self._makeOne, nope=True)

class TestCLI(unittest.TestCase):

    def parse(self, argv):
        from waitress.adjustments import Adjustments
        return Adjustments.parse_args(argv)

    def test_noargs(self):
        opts, args = self.parse([])
        self.assertDictEqual(opts, {'call': False, 'help': False})
        self.assertSequenceEqual(args, [])

    def test_help(self):
        opts, args = self.parse(['--help'])
        self.assertDictEqual(opts, {'call': False, 'help': True})
        self.assertSequenceEqual(args, [])

    def test_call(self):
        opts, args = self.parse(['--call'])
        self.assertDictEqual(opts, {'call': True, 'help': False})
        self.assertSequenceEqual(args, [])

    def test_both(self):
        opts, args = self.parse(['--call', '--help'])
        self.assertDictEqual(opts, {'call': True, 'help': True})
        self.assertSequenceEqual(args, [])

    def test_positive_boolean(self):
        opts, args = self.parse(['--expose-tracebacks'])
        self.assertDictContainsSubset({'expose_tracebacks': 'true'}, opts)
        self.assertSequenceEqual(args, [])

    def test_negative_boolean(self):
        opts, args = self.parse(['--no-expose-tracebacks'])
        self.assertDictContainsSubset({'expose_tracebacks': 'false'}, opts)
        self.assertSequenceEqual(args, [])

    def test_cast_params(self):
        opts, args = self.parse([
            '--host=localhost',
            '--port=80',
            '--unix-socket-perms=777'
        ])
        self.assertDictContainsSubset({
            'host': 'localhost',
            'port': '80',
            'unix_socket_perms':'777',
        }, opts)
        self.assertSequenceEqual(args, [])

    def test_bad_param(self):
        import getopt
        self.assertRaises(getopt.GetoptError, self.parse, ['--no-host'])

########NEW FILE########
__FILENAME__ = test_buffers
import unittest
import io

class TestFileBasedBuffer(unittest.TestCase):

    def _makeOne(self, file=None, from_buffer=None):
        from waitress.buffers import FileBasedBuffer
        return FileBasedBuffer(file, from_buffer=from_buffer)

    def test_ctor_from_buffer_None(self):
        inst = self._makeOne('file')
        self.assertEqual(inst.file, 'file')

    def test_ctor_from_buffer(self):
        from_buffer = io.BytesIO(b'data')
        from_buffer.getfile = lambda *x: from_buffer
        f = io.BytesIO()
        inst = self._makeOne(f, from_buffer)
        self.assertEqual(inst.file, f)
        del from_buffer.getfile
        self.assertEqual(inst.remain, 4)
        from_buffer.close()

    def test___len__(self):
        inst = self._makeOne()
        inst.remain = 10
        self.assertEqual(len(inst), 10)

    def test___nonzero__(self):
        inst = self._makeOne()
        inst.remain = 10
        self.assertEqual(bool(inst), True)
        inst.remain = 0
        self.assertEqual(bool(inst), False)

    def test_append(self):
        f = io.BytesIO(b'data')
        inst = self._makeOne(f)
        inst.append(b'data2')
        self.assertEqual(f.getvalue(), b'datadata2')
        self.assertEqual(inst.remain, 5)

    def test_get_skip_true(self):
        f = io.BytesIO(b'data')
        inst = self._makeOne(f)
        result = inst.get(100, skip=True)
        self.assertEqual(result, b'data')
        self.assertEqual(inst.remain, -4)

    def test_get_skip_false(self):
        f = io.BytesIO(b'data')
        inst = self._makeOne(f)
        result = inst.get(100, skip=False)
        self.assertEqual(result, b'data')
        self.assertEqual(inst.remain, 0)

    def test_get_skip_bytes_less_than_zero(self):
        f = io.BytesIO(b'data')
        inst = self._makeOne(f)
        result = inst.get(-1, skip=False)
        self.assertEqual(result, b'data')
        self.assertEqual(inst.remain, 0)

    def test_skip_remain_gt_bytes(self):
        f = io.BytesIO(b'd')
        inst = self._makeOne(f)
        inst.remain = 1
        inst.skip(1)
        self.assertEqual(inst.remain, 0)

    def test_skip_remain_lt_bytes(self):
        f = io.BytesIO(b'd')
        inst = self._makeOne(f)
        inst.remain = 1
        self.assertRaises(ValueError, inst.skip, 2)

    def test_newfile(self):
        inst = self._makeOne()
        self.assertRaises(NotImplementedError, inst.newfile)

    def test_prune_remain_notzero(self):
        f = io.BytesIO(b'd')
        inst = self._makeOne(f)
        inst.remain = 1
        nf = io.BytesIO()
        inst.newfile = lambda *x: nf
        inst.prune()
        self.assertTrue(inst.file is not f)
        self.assertEqual(nf.getvalue(), b'd')

    def test_prune_remain_zero_tell_notzero(self):
        f = io.BytesIO(b'd')
        inst = self._makeOne(f)
        nf = io.BytesIO(b'd')
        inst.newfile = lambda *x: nf
        inst.remain = 0
        inst.prune()
        self.assertTrue(inst.file is not f)
        self.assertEqual(nf.getvalue(), b'd')

    def test_prune_remain_zero_tell_zero(self):
        f = io.BytesIO()
        inst = self._makeOne(f)
        inst.remain = 0
        inst.prune()
        self.assertTrue(inst.file is f)

    def test_close(self):
        f = io.BytesIO()
        inst = self._makeOne(f)
        inst.close()
        self.assertTrue(f.closed)

class TestTempfileBasedBuffer(unittest.TestCase):

    def _makeOne(self, from_buffer=None):
        from waitress.buffers import TempfileBasedBuffer
        return TempfileBasedBuffer(from_buffer=from_buffer)

    def test_newfile(self):
        inst = self._makeOne()
        r = inst.newfile()
        self.assertTrue(hasattr(r, 'fileno')) # file

class TestBytesIOBasedBuffer(unittest.TestCase):

    def _makeOne(self, from_buffer=None):
        from waitress.buffers import BytesIOBasedBuffer
        return BytesIOBasedBuffer(from_buffer=from_buffer)

    def test_ctor_from_buffer_not_None(self):
        f = io.BytesIO()
        f.getfile = lambda *x: f
        inst = self._makeOne(f)
        self.assertTrue(hasattr(inst.file, 'read'))

    def test_ctor_from_buffer_None(self):
        inst = self._makeOne()
        self.assertTrue(hasattr(inst.file, 'read'))

    def test_newfile(self):
        inst = self._makeOne()
        r = inst.newfile()
        self.assertTrue(hasattr(r, 'read'))

class TestReadOnlyFileBasedBuffer(unittest.TestCase):

    def _makeOne(self, file, block_size=8192):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        return ReadOnlyFileBasedBuffer(file, block_size)

    def test_prepare_not_seekable(self):
        f = KindaFilelike(b'abc')
        inst = self._makeOne(f)
        result = inst.prepare()
        self.assertEqual(result, False)
        self.assertEqual(inst.remain, 0)

    def test_prepare_not_seekable_closeable(self):
        f = KindaFilelike(b'abc', close=1)
        inst = self._makeOne(f)
        result = inst.prepare()
        self.assertEqual(result, False)
        self.assertEqual(inst.remain, 0)
        self.assertTrue(hasattr(inst, 'close'))

    def test_prepare_seekable_closeable(self):
        f = Filelike(b'abc', close=1, tellresults=[0, 10])
        inst = self._makeOne(f)
        result = inst.prepare()
        self.assertEqual(result, 10)
        self.assertEqual(inst.remain, 10)
        self.assertEqual(inst.file.seeked, 0)
        self.assertTrue(hasattr(inst, 'close'))

    def test_get_numbytes_neg_one(self):
        f = io.BytesIO(b'abcdef')
        inst = self._makeOne(f)
        inst.remain = 2
        result = inst.get(-1)
        self.assertEqual(result, b'ab')
        self.assertEqual(inst.remain, 2)
        self.assertEqual(f.tell(), 0)

    def test_get_numbytes_gt_remain(self):
        f = io.BytesIO(b'abcdef')
        inst = self._makeOne(f)
        inst.remain = 2
        result = inst.get(3)
        self.assertEqual(result, b'ab')
        self.assertEqual(inst.remain, 2)
        self.assertEqual(f.tell(), 0)

    def test_get_numbytes_lt_remain(self):
        f = io.BytesIO(b'abcdef')
        inst = self._makeOne(f)
        inst.remain = 2
        result = inst.get(1)
        self.assertEqual(result, b'a')
        self.assertEqual(inst.remain, 2)
        self.assertEqual(f.tell(), 0)

    def test_get_numbytes_gt_remain_withskip(self):
        f = io.BytesIO(b'abcdef')
        inst = self._makeOne(f)
        inst.remain = 2
        result = inst.get(3, skip=True)
        self.assertEqual(result, b'ab')
        self.assertEqual(inst.remain, 0)
        self.assertEqual(f.tell(), 2)

    def test_get_numbytes_lt_remain_withskip(self):
        f = io.BytesIO(b'abcdef')
        inst = self._makeOne(f)
        inst.remain = 2
        result = inst.get(1, skip=True)
        self.assertEqual(result, b'a')
        self.assertEqual(inst.remain, 1)
        self.assertEqual(f.tell(), 1)

    def test___iter__(self):
        data = b'a' * 10000
        f = io.BytesIO(data)
        inst = self._makeOne(f)
        r = b''
        for val in inst:
            r += val
        self.assertEqual(r, data)

    def test_append(self):
        inst = self._makeOne(None)
        self.assertRaises(NotImplementedError, inst.append, 'a')

class TestOverflowableBuffer(unittest.TestCase):

    def _makeOne(self, overflow=10):
        from waitress.buffers import OverflowableBuffer
        return OverflowableBuffer(overflow)

    def test___len__buf_is_None(self):
        inst = self._makeOne()
        self.assertEqual(len(inst), 0)

    def test___len__buf_is_not_None(self):
        inst = self._makeOne()
        inst.buf = b'abc'
        self.assertEqual(len(inst), 3)

    def test___nonzero__(self):
        inst = self._makeOne()
        inst.buf = b'abc'
        self.assertEqual(bool(inst), True)
        inst.buf = b''
        self.assertEqual(bool(inst), False)

    def test___nonzero___on_int_overflow_buffer(self):
        inst = self._makeOne()

        class int_overflow_buf(bytes):
            def __len__(self):
                # maxint + 1
                return 0x7fffffffffffffff + 1
        inst.buf = int_overflow_buf()
        self.assertEqual(bool(inst), True)
        inst.buf = b''
        self.assertEqual(bool(inst), False)

    def test__create_buffer_large(self):
        from waitress.buffers import TempfileBasedBuffer
        inst = self._makeOne()
        inst.strbuf = b'x' * 11
        inst._create_buffer()
        self.assertEqual(inst.buf.__class__, TempfileBasedBuffer)
        self.assertEqual(inst.buf.get(100), b'x' * 11)
        self.assertEqual(inst.strbuf, b'')

    def test__create_buffer_small(self):
        from waitress.buffers import BytesIOBasedBuffer
        inst = self._makeOne()
        inst.strbuf = b'x' * 5
        inst._create_buffer()
        self.assertEqual(inst.buf.__class__, BytesIOBasedBuffer)
        self.assertEqual(inst.buf.get(100), b'x' * 5)
        self.assertEqual(inst.strbuf, b'')

    def test_append_with_len_more_than_max_int(self):
        from waitress.compat import MAXINT
        inst = self._makeOne()
        inst.overflowed = True
        buf = DummyBuffer(length=MAXINT)
        inst.buf = buf
        result = inst.append(b'x')
        # we don't want this to throw an OverflowError on Python 2 (see
        # https://github.com/Pylons/waitress/issues/47)
        self.assertEqual(result, None)
        
    def test_append_buf_None_not_longer_than_srtbuf_limit(self):
        inst = self._makeOne()
        inst.strbuf = b'x' * 5
        inst.append(b'hello')
        self.assertEqual(inst.strbuf, b'xxxxxhello')

    def test_append_buf_None_longer_than_strbuf_limit(self):
        inst = self._makeOne(10000)
        inst.strbuf = b'x' * 8192
        inst.append(b'hello')
        self.assertEqual(inst.strbuf, b'')
        self.assertEqual(len(inst.buf), 8197)

    def test_append_overflow(self):
        inst = self._makeOne(10)
        inst.strbuf = b'x' * 8192
        inst.append(b'hello')
        self.assertEqual(inst.strbuf, b'')
        self.assertEqual(len(inst.buf), 8197)

    def test_append_sz_gt_overflow(self):
        from waitress.buffers import BytesIOBasedBuffer
        f = io.BytesIO(b'data')
        inst = self._makeOne(f)
        buf = BytesIOBasedBuffer()
        inst.buf = buf
        inst.overflow = 2
        inst.append(b'data2')
        self.assertEqual(f.getvalue(), b'data')
        self.assertTrue(inst.overflowed)
        self.assertNotEqual(inst.buf, buf)

    def test_get_buf_None_skip_False(self):
        inst = self._makeOne()
        inst.strbuf = b'x' * 5
        r = inst.get(5)
        self.assertEqual(r, b'xxxxx')

    def test_get_buf_None_skip_True(self):
        inst = self._makeOne()
        inst.strbuf = b'x' * 5
        r = inst.get(5, skip=True)
        self.assertFalse(inst.buf is None)
        self.assertEqual(r, b'xxxxx')

    def test_skip_buf_None(self):
        inst = self._makeOne()
        inst.strbuf = b'data'
        inst.skip(4)
        self.assertEqual(inst.strbuf, b'')
        self.assertNotEqual(inst.buf, None)

    def test_skip_buf_None_allow_prune_True(self):
        inst = self._makeOne()
        inst.strbuf = b'data'
        inst.skip(4, True)
        self.assertEqual(inst.strbuf, b'')
        self.assertEqual(inst.buf, None)

    def test_prune_buf_None(self):
        inst = self._makeOne()
        inst.prune()
        self.assertEqual(inst.strbuf, b'')

    def test_prune_with_buf(self):
        inst = self._makeOne()
        class Buf(object):
            def prune(self):
                self.pruned = True
        inst.buf = Buf()
        inst.prune()
        self.assertEqual(inst.buf.pruned, True)

    def test_prune_with_buf_overflow(self):
        inst = self._makeOne()
        class DummyBuffer(io.BytesIO):
            def getfile(self):
                return self
            def prune(self):
                return True
            def __len__(self):
                return 5
        buf = DummyBuffer(b'data')
        inst.buf = buf
        inst.overflowed = True
        inst.overflow = 10
        inst.prune()
        self.assertNotEqual(inst.buf, buf)

    def test_prune_with_buflen_more_than_max_int(self):
        from waitress.compat import MAXINT
        inst = self._makeOne()
        inst.overflowed = True
        buf = DummyBuffer(length=MAXINT+1)
        inst.buf = buf
        result = inst.prune()
        # we don't want this to throw an OverflowError on Python 2 (see
        # https://github.com/Pylons/waitress/issues/47)
        self.assertEqual(result, None)
        
    def test_getfile_buf_None(self):
        inst = self._makeOne()
        f = inst.getfile()
        self.assertTrue(hasattr(f, 'read'))

    def test_getfile_buf_not_None(self):
        inst = self._makeOne()
        buf = io.BytesIO()
        buf.getfile = lambda *x: buf
        inst.buf = buf
        f = inst.getfile()
        self.assertEqual(f, buf)

    def test_close_nobuf(self):
        inst = self._makeOne()
        inst.buf = None
        self.assertEqual(inst.close(), None) # doesnt raise

    def test_close_withbuf(self):
        class Buffer(object):
            def close(self):
                self.closed = True
        buf = Buffer()
        inst = self._makeOne()
        inst.buf = buf
        inst.close()
        self.assertTrue(buf.closed)

class KindaFilelike(object):

    def __init__(self, bytes, close=None, tellresults=None):
        self.bytes = bytes
        self.tellresults = tellresults
        if close is not None:
            self.close = close

class Filelike(KindaFilelike):

    def seek(self, v, whence=0):
        self.seeked = v

    def tell(self):
        v = self.tellresults.pop(0)
        return v

class DummyBuffer(object):
    def __init__(self, length=0):
        self.length = length

    def __len__(self):
        return self.length

    def append(self, s):
        self.length = self.length + len(s)

    def prune(self):
        pass

########NEW FILE########
__FILENAME__ = test_channel
import unittest
import io

class TestHTTPChannel(unittest.TestCase):

    def _makeOne(self, sock, addr, adj, map=None):
        from waitress.channel import HTTPChannel
        server = DummyServer()
        return HTTPChannel(server, sock, addr, adj=adj, map=map)

    def _makeOneWithMap(self, adj=None):
        if adj is None:
            adj = DummyAdjustments()
        sock = DummySock()
        map = {}
        inst = self._makeOne(sock, '127.0.0.1', adj, map=map)
        inst.outbuf_lock = DummyLock()
        return inst, sock, map

    def test_ctor(self):
        inst, _, map = self._makeOneWithMap()
        self.assertEqual(inst.addr, '127.0.0.1')
        self.assertEqual(map[100], inst)

    def test_total_outbufs_len_an_outbuf_size_gt_sys_maxint(self):
        from waitress.compat import MAXINT
        inst, _, map = self._makeOneWithMap()
        class DummyHugeBuffer(object):
            def __len__(self):
                return MAXINT + 1
        inst.outbufs = [DummyHugeBuffer()]
        result = inst.total_outbufs_len()
        # we are testing that this method does not raise an OverflowError
        # (see https://github.com/Pylons/waitress/issues/47)
        self.assertEqual(result, MAXINT+1)

    def test_writable_something_in_outbuf(self):
        inst, sock, map = self._makeOneWithMap()
        inst.outbufs[0].append(b'abc')
        self.assertTrue(inst.writable())

    def test_writable_nothing_in_outbuf(self):
        inst, sock, map = self._makeOneWithMap()
        self.assertFalse(inst.writable())

    def test_writable_nothing_in_outbuf_will_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.will_close = True
        self.assertTrue(inst.writable())

    def test_handle_write_not_connected(self):
        inst, sock, map = self._makeOneWithMap()
        inst.connected = False
        self.assertFalse(inst.handle_write())

    def test_handle_write_with_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = True
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.last_activity, 0)

    def test_handle_write_no_request_with_outbuf(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        inst.outbufs = [DummyBuffer(b'abc')]
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertNotEqual(inst.last_activity, 0)
        self.assertEqual(sock.sent, b'abc')

    def test_handle_write_outbuf_raises_socketerror(self):
        import socket
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        outbuf = DummyBuffer(b'abc', socket.error)
        inst.outbufs = [outbuf]
        inst.last_activity = 0
        inst.logger = DummyLogger()
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.last_activity, 0)
        self.assertEqual(sock.sent, b'')
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(outbuf.closed)

    def test_handle_write_outbuf_raises_othererror(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        outbuf = DummyBuffer(b'abc', IOError)
        inst.outbufs = [outbuf]
        inst.last_activity = 0
        inst.logger = DummyLogger()
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.last_activity, 0)
        self.assertEqual(sock.sent, b'')
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(outbuf.closed)

    def test_handle_write_no_requests_no_outbuf_will_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        outbuf = DummyBuffer(b'')
        inst.outbufs = [outbuf]
        inst.will_close = True
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.connected, False)
        self.assertEqual(sock.closed, True)
        self.assertEqual(inst.last_activity, 0)
        self.assertTrue(outbuf.closed)

    def test_handle_write_no_requests_force_flush(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = [True]
        inst.outbufs = [DummyBuffer(b'abc')]
        inst.will_close = False
        inst.force_flush = True
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.will_close, False)
        self.assertTrue(inst.outbuf_lock.acquired)
        self.assertEqual(inst.force_flush, False)
        self.assertEqual(sock.sent, b'abc')

    def test_handle_write_no_requests_outbuf_gt_send_bytes(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = [True]
        inst.outbufs = [DummyBuffer(b'abc')]
        inst.adj.send_bytes = 2
        inst.will_close = False
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.will_close, False)
        self.assertTrue(inst.outbuf_lock.acquired)
        self.assertEqual(sock.sent, b'abc')

    def test_handle_write_close_when_flushed(self):
        inst, sock, map = self._makeOneWithMap()
        outbuf = DummyBuffer(b'abc')
        inst.outbufs = [outbuf]
        inst.will_close = False
        inst.close_when_flushed = True
        inst.last_activity = 0
        result = inst.handle_write()
        self.assertEqual(result, None)
        self.assertEqual(inst.will_close, True)
        self.assertEqual(inst.close_when_flushed, False)
        self.assertEqual(sock.sent, b'abc')
        self.assertTrue(outbuf.closed)

    def test_readable_no_requests_not_will_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        inst.will_close = False
        self.assertEqual(inst.readable(), True)

    def test_readable_no_requests_will_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        inst.will_close = True
        self.assertEqual(inst.readable(), False)

    def test_readable_with_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = True
        self.assertEqual(inst.readable(), False)

    def test_handle_read_no_error(self):
        inst, sock, map = self._makeOneWithMap()
        inst.will_close = False
        inst.recv = lambda *arg: b'abc'
        inst.last_activity = 0
        L = []
        inst.received = lambda x: L.append(x)
        result = inst.handle_read()
        self.assertEqual(result, None)
        self.assertNotEqual(inst.last_activity, 0)
        self.assertEqual(L, [b'abc'])

    def test_handle_read_error(self):
        import socket
        inst, sock, map = self._makeOneWithMap()
        inst.will_close = False
        def recv(b):
            raise socket.error
        inst.recv = recv
        inst.last_activity = 0
        inst.logger = DummyLogger()
        result = inst.handle_read()
        self.assertEqual(result, None)
        self.assertEqual(inst.last_activity, 0)
        self.assertEqual(len(inst.logger.exceptions), 1)

    def test_write_soon_empty_byte(self):
        inst, sock, map = self._makeOneWithMap()
        wrote = inst.write_soon(b'')
        self.assertEqual(wrote, 0)
        self.assertEqual(len(inst.outbufs[0]), 0)

    def test_write_soon_nonempty_byte(self):
        inst, sock, map = self._makeOneWithMap()
        wrote = inst.write_soon(b'a')
        self.assertEqual(wrote, 1)
        self.assertEqual(len(inst.outbufs[0]), 1)

    def test_write_soon_filewrapper(self):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        f = io.BytesIO(b'abc')
        wrapper = ReadOnlyFileBasedBuffer(f, 8192)
        wrapper.prepare()
        inst, sock, map = self._makeOneWithMap()
        outbufs = inst.outbufs
        orig_outbuf = outbufs[0]
        wrote = inst.write_soon(wrapper)
        self.assertEqual(wrote, 3)
        self.assertEqual(len(outbufs), 3)
        self.assertEqual(outbufs[0], orig_outbuf)
        self.assertEqual(outbufs[1], wrapper)
        self.assertEqual(outbufs[2].__class__.__name__, 'OverflowableBuffer')

    def test__flush_some_empty_outbuf(self):
        inst, sock, map = self._makeOneWithMap()
        result = inst._flush_some()
        self.assertEqual(result, False)

    def test__flush_some_full_outbuf_socket_returns_nonzero(self):
        inst, sock, map = self._makeOneWithMap()
        inst.outbufs[0].append(b'abc')
        result = inst._flush_some()
        self.assertEqual(result, True)

    def test__flush_some_full_outbuf_socket_returns_zero(self):
        inst, sock, map = self._makeOneWithMap()
        sock.send = lambda x: False
        inst.outbufs[0].append(b'abc')
        result = inst._flush_some()
        self.assertEqual(result, False)

    def test_flush_some_multiple_buffers_first_empty(self):
        inst, sock, map = self._makeOneWithMap()
        sock.send = lambda x: len(x)
        buffer = DummyBuffer(b'abc')
        inst.outbufs.append(buffer)
        result = inst._flush_some()
        self.assertEqual(result, True)
        self.assertEqual(buffer.skipped, 3)
        self.assertEqual(inst.outbufs, [buffer])

    def test_flush_some_multiple_buffers_close_raises(self):
        inst, sock, map = self._makeOneWithMap()
        sock.send = lambda x: len(x)
        buffer = DummyBuffer(b'abc')
        inst.outbufs.append(buffer)
        inst.logger = DummyLogger()
        def doraise():
            raise NotImplementedError
        inst.outbufs[0].close = doraise
        result = inst._flush_some()
        self.assertEqual(result, True)
        self.assertEqual(buffer.skipped, 3)
        self.assertEqual(inst.outbufs, [buffer])
        self.assertEqual(len(inst.logger.exceptions), 1)

    def test__flush_some_outbuf_len_gt_sys_maxint(self):
        from waitress.compat import MAXINT
        inst, sock, map = self._makeOneWithMap()
        class DummyHugeOutbuffer(object):
            def __init__(self):
                self.length = MAXINT + 1
            def __len__(self):
                return self.length
            def get(self, numbytes):
                self.length = 0
                return b'123'
            def skip(self, *args): pass
        buf = DummyHugeOutbuffer()
        inst.outbufs = [buf]
        inst.send = lambda *arg: 0
        result = inst._flush_some()
        # we are testing that _flush_some doesn't raise an OverflowError
        # when one of its outbufs has a __len__ that returns gt sys.maxint
        self.assertEqual(result, False)
        
    def test_handle_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.handle_close()
        self.assertEqual(inst.connected, False)
        self.assertEqual(sock.closed, True)

    def test_handle_close_outbuf_raises_on_close(self):
        inst, sock, map = self._makeOneWithMap()
        def doraise():
            raise NotImplementedError
        inst.outbufs[0].close = doraise
        inst.logger = DummyLogger()
        inst.handle_close()
        self.assertEqual(inst.connected, False)
        self.assertEqual(sock.closed, True)
        self.assertEqual(len(inst.logger.exceptions), 1)

    def test_add_channel(self):
        inst, sock, map = self._makeOneWithMap()
        fileno = inst._fileno
        inst.add_channel(map)
        self.assertEqual(map[fileno], inst)
        self.assertEqual(inst.server.active_channels[fileno], inst)

    def test_del_channel(self):
        inst, sock, map = self._makeOneWithMap()
        fileno = inst._fileno
        inst.server.active_channels[fileno] = True
        inst.del_channel(map)
        self.assertEqual(map.get(fileno), None)
        self.assertEqual(inst.server.active_channels.get(fileno), None)

    def test_received(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.server.tasks, [inst])
        self.assertTrue(inst.requests)

    def test_received_no_chunk(self):
        inst, sock, map = self._makeOneWithMap()
        self.assertEqual(inst.received(b''), False)

    def test_received_preq_not_completed(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = False
        preq.empty = True
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.requests, ())
        self.assertEqual(inst.server.tasks, [])

    def test_received_preq_completed_empty(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = True
        preq.empty = True
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, None)
        self.assertEqual(inst.server.tasks, [])

    def test_received_preq_error(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = True
        preq.error = True
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, None)
        self.assertEqual(len(inst.server.tasks), 1)
        self.assertTrue(inst.requests)

    def test_received_preq_completed_connection_close(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = True
        preq.empty = True
        preq.connection_close = True
        inst.received(b'GET / HTTP/1.1\n\n' + b'a' * 50000)
        self.assertEqual(inst.request, None)
        self.assertEqual(inst.server.tasks, [])

    def test_received_preq_completed_n_lt_data(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.completed = True
        preq.empty = False
        line = b'GET / HTTP/1.1\n\n'
        preq.retval = len(line)
        inst.received(line + line)
        self.assertEqual(inst.request, None)
        self.assertEqual(len(inst.requests), 2)
        self.assertEqual(len(inst.server.tasks), 1)

    def test_received_headers_finished_expect_continue_false(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.expect_continue = False
        preq.headers_finished = True
        preq.completed = False
        preq.empty = False
        preq.retval = 1
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, preq)
        self.assertEqual(inst.server.tasks, [])
        self.assertEqual(inst.outbufs[0].get(100), b'')

    def test_received_headers_finished_expect_continue_true(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.expect_continue = True
        preq.headers_finished = True
        preq.completed = False
        preq.empty = False
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, preq)
        self.assertEqual(inst.server.tasks, [])
        self.assertEqual(sock.sent, b'HTTP/1.1 100 Continue\r\n\r\n')
        self.assertEqual(inst.sent_continue, True)
        self.assertEqual(preq.completed, False)

    def test_received_headers_finished_expect_continue_true_sent_true(self):
        inst, sock, map = self._makeOneWithMap()
        inst.server = DummyServer()
        preq = DummyParser()
        inst.request = preq
        preq.expect_continue = True
        preq.headers_finished = True
        preq.completed = False
        preq.empty = False
        inst.sent_continue = True
        inst.received(b'GET / HTTP/1.1\n\n')
        self.assertEqual(inst.request, preq)
        self.assertEqual(inst.server.tasks, [])
        self.assertEqual(sock.sent, b'')
        self.assertEqual(inst.sent_continue, True)
        self.assertEqual(preq.completed, False)

    def test_service_no_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = []
        inst.service()
        self.assertEqual(inst.requests, [])
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)

    def test_service_with_one_request(self):
        inst, sock, map = self._makeOneWithMap()
        request = DummyRequest()
        inst.task_class = DummyTaskClass()
        inst.requests = [request]
        inst.service()
        self.assertEqual(inst.requests, [])
        self.assertTrue(request.serviced)
        self.assertTrue(request.closed)

    def test_service_with_one_error_request(self):
        inst, sock, map = self._makeOneWithMap()
        request = DummyRequest()
        request.error = DummyError()
        inst.error_task_class = DummyTaskClass()
        inst.requests = [request]
        inst.service()
        self.assertEqual(inst.requests, [])
        self.assertTrue(request.serviced)
        self.assertTrue(request.closed)

    def test_service_with_multiple_requests(self):
        inst, sock, map = self._makeOneWithMap()
        request1 = DummyRequest()
        request2 = DummyRequest()
        inst.task_class = DummyTaskClass()
        inst.requests = [request1, request2]
        inst.service()
        self.assertEqual(inst.requests, [])
        self.assertTrue(request1.serviced)
        self.assertTrue(request2.serviced)
        self.assertTrue(request1.closed)
        self.assertTrue(request2.closed)

    def test_service_with_request_raises(self):
        inst, sock, map = self._makeOneWithMap()
        inst.adj.expose_tracebacks = False
        inst.server = DummyServer()
        request = DummyRequest()
        inst.requests = [request]
        inst.task_class = DummyTaskClass(ValueError)
        inst.task_class.wrote_header = False
        inst.error_task_class = DummyTaskClass()
        inst.logger = DummyLogger()
        inst.service()
        self.assertTrue(request.serviced)
        self.assertEqual(inst.requests, [])
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)
        self.assertFalse(inst.will_close)
        self.assertEqual(inst.error_task_class.serviced, True)
        self.assertTrue(request.closed)

    def test_service_with_requests_raises_already_wrote_header(self):
        inst, sock, map = self._makeOneWithMap()
        inst.adj.expose_tracebacks = False
        inst.server = DummyServer()
        request = DummyRequest()
        inst.requests = [request]
        inst.task_class = DummyTaskClass(ValueError)
        inst.error_task_class = DummyTaskClass()
        inst.logger = DummyLogger()
        inst.service()
        self.assertTrue(request.serviced)
        self.assertEqual(inst.requests, [])
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)
        self.assertTrue(inst.close_when_flushed)
        self.assertEqual(inst.error_task_class.serviced, False)
        self.assertTrue(request.closed)

    def test_service_with_requests_raises_didnt_write_header_expose_tbs(self):
        inst, sock, map = self._makeOneWithMap()
        inst.adj.expose_tracebacks = True
        inst.server = DummyServer()
        request = DummyRequest()
        inst.requests = [request]
        inst.task_class = DummyTaskClass(ValueError)
        inst.task_class.wrote_header = False
        inst.error_task_class = DummyTaskClass()
        inst.logger = DummyLogger()
        inst.service()
        self.assertTrue(request.serviced)
        self.assertFalse(inst.will_close)
        self.assertEqual(inst.requests, [])
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)
        self.assertEqual(inst.error_task_class.serviced, True)
        self.assertTrue(request.closed)

    def test_service_with_requests_raises_didnt_write_header(self):
        inst, sock, map = self._makeOneWithMap()
        inst.adj.expose_tracebacks = False
        inst.server = DummyServer()
        request = DummyRequest()
        inst.requests = [request]
        inst.task_class = DummyTaskClass(ValueError)
        inst.task_class.wrote_header = False
        inst.logger = DummyLogger()
        inst.service()
        self.assertTrue(request.serviced)
        self.assertEqual(inst.requests, [])
        self.assertEqual(len(inst.logger.exceptions), 1)
        self.assertTrue(inst.force_flush)
        self.assertTrue(inst.last_activity)
        self.assertTrue(inst.close_when_flushed)
        self.assertTrue(request.closed)

    def test_cancel_no_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = ()
        inst.cancel()
        self.assertEqual(inst.requests, [])

    def test_cancel_with_requests(self):
        inst, sock, map = self._makeOneWithMap()
        inst.requests = [None]
        inst.cancel()
        self.assertEqual(inst.requests, [])

    def test_defer(self):
        inst, sock, map = self._makeOneWithMap()
        self.assertEqual(inst.defer(), None)

class DummySock(object):
    blocking = False
    closed = False

    def __init__(self):
        self.sent = b''

    def setblocking(self, *arg):
        self.blocking = True

    def fileno(self):
        return 100

    def getpeername(self):
        return '127.0.0.1'

    def close(self):
        self.closed = True

    def send(self, data):
        self.sent += data
        return len(data)

class DummyLock(object):

    def __init__(self, acquirable=True):
        self.acquirable = acquirable

    def acquire(self, val):
        self.val = val
        self.acquired = True
        return self.acquirable

    def release(self):
        self.released = True

    def __exit__(self, type, val, traceback):
        self.acquire(True)

    def __enter__(self):
        pass

class DummyBuffer(object):
    closed = False

    def __init__(self, data, toraise=None):
        self.data = data
        self.toraise = toraise

    def get(self, *arg):
        if self.toraise:
            raise self.toraise
        data = self.data
        self.data = b''
        return data

    def skip(self, num, x):
        self.skipped = num

    def __len__(self):
        return len(self.data)

    def close(self):
        self.closed = True

class DummyAdjustments(object):
    outbuf_overflow = 1048576
    inbuf_overflow = 512000
    cleanup_interval = 900
    send_bytes = 9000
    url_scheme = 'http'
    channel_timeout = 300
    log_socket_errors = True
    recv_bytes = 8192
    expose_tracebacks = True
    ident = 'waitress'
    max_request_header_size = 10000

class DummyServer(object):
    trigger_pulled = False
    adj = DummyAdjustments()

    def __init__(self):
        self.tasks = []
        self.active_channels = {}

    def add_task(self, task):
        self.tasks.append(task)

    def pull_trigger(self):
        self.trigger_pulled = True

class DummyParser(object):
    version = 1
    data = None
    completed = True
    empty = False
    headers_finished = False
    expect_continue = False
    retval = None
    error = None
    connection_close = False

    def received(self, data):
        self.data = data
        if self.retval is not None:
            return self.retval
        return len(data)

class DummyRequest(object):
    error = None
    path = '/'
    version = '1.0'
    closed = False

    def __init__(self):
        self.headers = {}

    def close(self):
        self.closed = True

class DummyLogger(object):

    def __init__(self):
        self.exceptions = []

    def exception(self, msg):
        self.exceptions.append(msg)

class DummyError(object):
    code = '431'
    reason = 'Bleh'
    body = 'My body'

class DummyTaskClass(object):
    wrote_header = True
    close_on_finish = False
    serviced = False

    def __init__(self, toraise=None):
        self.toraise = toraise

    def __call__(self, channel, request):
        self.request = request
        return self

    def service(self):
        self.serviced = True
        self.request.serviced = True
        if self.toraise:
            raise self.toraise

########NEW FILE########
__FILENAME__ = test_compat
# -*- coding: utf-8 -*-

import unittest

class Test_unquote_bytes_to_wsgi(unittest.TestCase):

    def _callFUT(self, v):
        from waitress.compat import unquote_bytes_to_wsgi
        return unquote_bytes_to_wsgi(v)

    def test_highorder(self):
        from waitress.compat import PY3
        val = b'/a%C5%9B'
        result = self._callFUT(val)
        if PY3: # pragma: no cover
            # PEP 3333 urlunquoted-latin1-decoded-bytes
            self.assertEqual(result, '/aÅ\x9b')
        else: # pragma: no cover
            # sanity
            self.assertEqual(result, b'/a\xc5\x9b')

########NEW FILE########
__FILENAME__ = test_functional
import errno
import logging
import multiprocessing
import os
import socket
import string
import subprocess
import sys
import time
import unittest
from waitress import server
from waitress.compat import (
    httplib,
    tobytes
)
from waitress.utilities import cleanup_unix_socket

dn = os.path.dirname
here = dn(__file__)

class NullHandler(logging.Handler): # pragma: no cover
    """A logging handler that swallows all emitted messages.
    """
    def emit(self, record):
        pass

def start_server(app, svr, queue, **kwargs): # pragma: no cover
    """Run a fixture application.
    """
    logging.getLogger('waitress').addHandler(NullHandler())
    svr(app, queue, **kwargs).run()

class FixtureTcpWSGIServer(server.TcpWSGIServer):
    """A version of TcpWSGIServer that relays back what it's bound to.
    """

    def __init__(self, application, queue, **kw): # pragma: no cover
        # Coverage doesn't see this as it's ran in a separate process.
        kw['port'] = 0 # Bind to any available port.
        super(FixtureTcpWSGIServer, self).__init__(application, **kw)
        host, port = self.socket.getsockname()
        if os.name == 'nt':
            host = '127.0.0.1'
        queue.put((host, port))

class SubprocessTests(object):

    # For nose: all tests may be ran in separate processes.
    _multiprocess_can_split_ = True

    exe = sys.executable

    server = None

    def start_subprocess(self, target, **kw):
        # Spawn a server process.
        self.queue = multiprocessing.Queue()
        self.proc = multiprocessing.Process(
            target=start_server,
            args=(target, self.server, self.queue),
            kwargs=kw,
        )
        self.proc.start()
        if self.proc.exitcode is not None: # pragma: no cover
            raise RuntimeError("%s didn't start" % str(target))
        # Get the socket the server is listening on.
        self.bound_to = self.queue.get(timeout=5)
        self.sock = self.create_socket()

    def stop_subprocess(self):
        if self.proc.exitcode is None:
            self.proc.terminate()
        self.sock.close()
        # This give us one FD back ...
        self.queue.close()

    def assertline(self, line, status, reason, version):
        v, s, r = (x.strip() for x in line.split(None, 2))
        self.assertEqual(s, tobytes(status))
        self.assertEqual(r, tobytes(reason))
        self.assertEqual(v, tobytes(version))

    def create_socket(self):
        return socket.socket(self.server.family, socket.SOCK_STREAM)

    def connect(self):
        self.sock.connect(self.bound_to)

    def make_http_connection(self):
        raise NotImplementedError # pragma: no cover

    def send_check_error(self, to_send):
        self.sock.send(to_send)

class TcpTests(SubprocessTests):

    server = FixtureTcpWSGIServer

    def make_http_connection(self):
        return httplib.HTTPConnection(*self.bound_to)

class SleepyThreadTests(TcpTests, unittest.TestCase):
    # test that sleepy thread doesnt block other requests

    def setUp(self):
        from waitress.tests.fixtureapps import sleepy
        self.start_subprocess(sleepy.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_it(self):
        getline = os.path.join(here, 'fixtureapps', 'getline.py')
        cmds = (
            [self.exe, getline, 'http://%s:%d/sleepy' % self.bound_to],
            [self.exe, getline, 'http://%s:%d/' % self.bound_to]
        )
        r, w = os.pipe()
        procs = []
        for cmd in cmds:
            procs.append(subprocess.Popen(cmd, stdout=w))
        time.sleep(3)
        for proc in procs:
            if proc.returncode is not None: # pragma: no cover
                proc.terminate()
        # the notsleepy response should always be first returned (it sleeps
        # for 2 seconds, then returns; the notsleepy response should be
        # processed in the meantime)
        result = os.read(r, 10000)
        os.close(r)
        os.close(w)
        self.assertEqual(result, b'notsleepy returnedsleepy returned')

class EchoTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import echo
        self.start_subprocess(echo.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_date_and_server(self):
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 0\n\n")
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('server'), 'waitress')
        self.assertTrue(headers.get('date'))

    def test_bad_host_header(self):
        # http://corte.si/posts/code/pathod/pythonservers/index.html
        to_send = ("GET / HTTP/1.0\n"
                   " Host: 0\n\n")
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '400', 'Bad Request', 'HTTP/1.0')
        self.assertEqual(headers.get('server'), 'waitress')
        self.assertTrue(headers.get('date'))

    def test_send_with_body(self):
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 5\n\n")
        to_send += 'hello'
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), '5')
        self.assertEqual(response_body, b'hello')

    def test_send_empty_body(self):
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 0\n\n")
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), '0')
        self.assertEqual(response_body, b'')

    def test_multiple_requests_with_body(self):
        for x in range(3):
            self.sock = self.create_socket()
            self.test_send_with_body()
            self.sock.close()

    def test_multiple_requests_without_body(self):
        for x in range(3):
            self.sock = self.create_socket()
            self.test_send_empty_body()
            self.sock.close()

    def test_without_crlf(self):
        data = "Echo\nthis\r\nplease"
        s = tobytes(
            "GET / HTTP/1.0\n"
            "Connection: close\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(int(headers['content-length']), len(data))
        self.assertEqual(len(response_body), len(data))
        self.assertEqual(response_body, tobytes(data))

    def test_large_body(self):
        # 1024 characters.
        body = 'This string has 32 characters.\r\n' * 32
        s = tobytes(
            "GET / HTTP/1.0\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(body), body)
        )
        self.connect()
        self.sock.send(s)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), '1024')
        self.assertEqual(response_body, tobytes(body))

    def test_many_clients(self):
        conns = []
        for n in range(50):
            h = self.make_http_connection()
            h.request("GET", "/", headers={"Accept": "text/plain"})
            conns.append(h)
        responses = []
        for h in conns:
            response = h.getresponse()
            self.assertEqual(response.status, 200)
            responses.append(response)
        for response in responses:
            response.read()

    def test_chunking_request_without_content(self):
        header = tobytes(
            "GET / HTTP/1.1\n"
            "Transfer-Encoding: chunked\n\n"
        )
        self.connect()
        self.sock.send(header)
        self.sock.send(b"0\r\n\r\n")
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(response_body, b'')
        self.assertEqual(headers['content-length'], '0')
        self.assertFalse('transfer-encoding' in headers)

    def test_chunking_request_with_content(self):
        control_line = b"20;\r\n" # 20 hex = 32 dec
        s = b'This string has 32 characters.\r\n'
        expected = s * 12
        header = tobytes(
            "GET / HTTP/1.1\n"
            "Transfer-Encoding: chunked\n\n"
        )
        self.connect()
        self.sock.send(header)
        fp = self.sock.makefile('rb', 0)
        for n in range(12):
            self.sock.send(control_line)
            self.sock.send(s)
        self.sock.send(b"0\r\n\r\n")
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(response_body, expected)
        self.assertEqual(headers['content-length'], str(len(expected)))
        self.assertFalse('transfer-encoding' in headers)

    def test_broken_chunked_encoding(self):
        control_line = "20;\r\n" # 20 hex = 32 dec
        s = 'This string has 32 characters.\r\n'
        to_send = "GET / HTTP/1.1\nTransfer-Encoding: chunked\n\n"
        to_send += (control_line + s)
        # garbage in input
        to_send += "GET / HTTP/1.1\nTransfer-Encoding: chunked\n\n"
        to_send += (control_line + s)
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # receiver caught garbage and turned it into a 400
        self.assertline(line, '400', 'Bad Request', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertEqual(sorted(headers.keys()),
            ['content-length', 'content-type', 'date', 'server'])
        self.assertEqual(headers['content-type'], 'text/plain')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_keepalive_http_10(self):
        # Handling of Keep-Alive within HTTP 1.0
        data = "Default: Don't keep me alive"
        s = tobytes(
            "GET / HTTP/1.0\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        connection = response.getheader('Connection', '')
        # We sent no Connection: Keep-Alive header
        # Connection: close (or no header) is default.
        self.assertTrue(connection != 'Keep-Alive')

    def test_keepalive_http10_explicit(self):
        # If header Connection: Keep-Alive is explicitly sent,
        # we want to keept the connection open, we also need to return
        # the corresponding header
        data = "Keep me alive"
        s = tobytes(
            "GET / HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        connection = response.getheader('Connection', '')
        self.assertEqual(connection, 'Keep-Alive')

    def test_keepalive_http_11(self):
        # Handling of Keep-Alive within HTTP 1.1

        # All connections are kept alive, unless stated otherwise
        data = "Default: Keep me alive"
        s = tobytes(
            "GET / HTTP/1.1\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data))
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        self.assertTrue(response.getheader('connection') != 'close')

    def test_keepalive_http11_explicit(self):
        # Explicitly set keep-alive
        data = "Default: Keep me alive"
        s = tobytes(
            "GET / HTTP/1.1\n"
            "Connection: keep-alive\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        self.assertTrue(response.getheader('connection') != 'close')

    def test_keepalive_http11_connclose(self):
        # specifying Connection: close explicitly
        data = "Don't keep me alive"
        s = tobytes(
            "GET / HTTP/1.1\n"
            "Connection: close\n"
            "Content-Length: %d\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(s)
        response = httplib.HTTPResponse(self.sock)
        response.begin()
        self.assertEqual(int(response.status), 200)
        self.assertEqual(response.getheader('connection'), 'close')

class PipeliningTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import echo
        self.start_subprocess(echo.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_pipelining(self):
        s = ("GET / HTTP/1.0\r\n"
             "Connection: %s\r\n"
             "Content-Length: %d\r\n"
             "\r\n"
             "%s")
        to_send = b''
        count = 25
        for n in range(count):
            body = "Response #%d\r\n" % (n + 1)
            if n + 1 < count:
                conn = 'keep-alive'
            else:
                conn = 'close'
            to_send += tobytes(s % (conn, len(body), body))

        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        for n in range(count):
            expect_body = tobytes("Response #%d\r\n" % (n + 1))
            line = fp.readline() # status line
            version, status, reason = (x.strip() for x in line.split(None, 2))
            headers = parse_headers(fp)
            length = int(headers.get('content-length')) or None
            response_body = fp.read(length)
            self.assertEqual(int(status), 200)
            self.assertEqual(length, len(response_body))
            self.assertEqual(response_body, expect_body)

class ExpectContinueTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import echo
        self.start_subprocess(echo.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_expect_continue(self):
        # specifying Connection: close explicitly
        data = "I have expectations"
        to_send = tobytes(
            "GET / HTTP/1.1\n"
            "Connection: close\n"
            "Content-Length: %d\n"
            "Expect: 100-continue\n"
            "\n"
            "%s" % (len(data), data)
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # continue status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        self.assertEqual(int(status), 100)
        self.assertEqual(reason, b'Continue')
        self.assertEqual(version, b'HTTP/1.1')
        fp.readline() # blank line
        line = fp.readline() # next status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        headers = parse_headers(fp)
        length = int(headers.get('content-length')) or None
        response_body = fp.read(length)
        self.assertEqual(int(status), 200)
        self.assertEqual(length, len(response_body))
        self.assertEqual(response_body, tobytes(data))

class BadContentLengthTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import badcl
        self.start_subprocess(badcl.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_short_body(self):
        # check to see if server closes connection when body is too short
        # for cl header
        to_send = tobytes(
            "GET /short_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        headers = parse_headers(fp)
        content_length = int(headers.get('content-length'))
        response_body = fp.read(content_length)
        self.assertEqual(int(status), 200)
        self.assertNotEqual(content_length, len(response_body))
        self.assertEqual(len(response_body), content_length - 1)
        self.assertEqual(response_body, tobytes('abcdefghi'))
        # remote closed connection (despite keepalive header); not sure why
        # first send succeeds
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_long_body(self):
        # check server doesnt close connection when body is too short
        # for cl header
        to_send = tobytes(
            "GET /long_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        headers = parse_headers(fp)
        content_length = int(headers.get('content-length')) or None
        response_body = fp.read(content_length)
        self.assertEqual(int(status), 200)
        self.assertEqual(content_length, len(response_body))
        self.assertEqual(response_body, tobytes('abcdefgh'))
        # remote does not close connection (keepalive header)
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # status line
        version, status, reason = (x.strip() for x in line.split(None, 2))
        headers = parse_headers(fp)
        content_length = int(headers.get('content-length')) or None
        response_body = fp.read(content_length)
        self.assertEqual(int(status), 200)

class NoContentLengthTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import nocl
        self.start_subprocess(nocl.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_http10_generator(self):
        body = string.ascii_letters
        to_send = ("GET / HTTP/1.0\n"
                   "Connection: Keep-Alive\n"
                   "Content-Length: %d\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), None)
        self.assertEqual(headers.get('connection'), 'close')
        self.assertEqual(response_body, tobytes(body))
        # remote closed connection (despite keepalive header), because
        # generators cannot have a content-length divined
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_http10_list(self):
        body = string.ascii_letters
        to_send = ("GET /list HTTP/1.0\n"
                   "Connection: Keep-Alive\n"
                   "Content-Length: %d\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers['content-length'], str(len(body)))
        self.assertEqual(headers.get('connection'), 'Keep-Alive')
        self.assertEqual(response_body, tobytes(body))
        # remote keeps connection open because it divined the content length
        # from a length-1 list
        self.sock.send(to_send)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')

    def test_http10_listlentwo(self):
        body = string.ascii_letters
        to_send = ("GET /list_lentwo HTTP/1.0\n"
                   "Connection: Keep-Alive\n"
                   "Content-Length: %d\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(headers.get('content-length'), None)
        self.assertEqual(headers.get('connection'), 'close')
        self.assertEqual(response_body, tobytes(body))
        # remote closed connection (despite keepalive header), because
        # lists of length > 1 cannot have their content length divined
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_http11_generator(self):
        body = string.ascii_letters
        to_send = ("GET / HTTP/1.1\n"
                   "Content-Length: %s\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        expected = b''
        for chunk in chunks(body, 10):
            expected += tobytes(
                '%s\r\n%s\r\n' % (str(hex(len(chunk))[2:].upper()), chunk)
            )
        expected += b'0\r\n\r\n'
        self.assertEqual(response_body, expected)
        # connection is always closed at the end of a chunked response
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_http11_list(self):
        body = string.ascii_letters
        to_send = ("GET /list HTTP/1.1\n"
                   "Content-Length: %d\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(headers['content-length'], str(len(body)))
        self.assertEqual(response_body, tobytes(body))
        # remote keeps connection open because it divined the content length
        # from a length-1 list
        self.sock.send(to_send)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')

    def test_http11_listlentwo(self):
        body = string.ascii_letters
        to_send = ("GET /list_lentwo HTTP/1.1\n"
                   "Content-Length: %s\n\n" % len(body))
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        expected = b''
        for chunk in (body[0], body[1:]):
            expected += tobytes(
                '%s\r\n%s\r\n' % (str(hex(len(chunk))[2:].upper()), chunk)
            )
        expected += b'0\r\n\r\n'
        self.assertEqual(response_body, expected)
        # connection is always closed at the end of a chunked response
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class WriteCallbackTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import writecb
        self.start_subprocess(writecb.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_short_body(self):
        # check to see if server closes connection when body is too short
        # for cl header
        to_send = tobytes(
            "GET /short_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # server trusts the content-length header (5)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, 9)
        self.assertNotEqual(cl, len(response_body))
        self.assertEqual(len(response_body), cl - 1)
        self.assertEqual(response_body, tobytes('abcdefgh'))
        # remote closed connection (despite keepalive header)
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_long_body(self):
        # check server doesnt close connection when body is too long
        # for cl header
        to_send = tobytes(
            "GET /long_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        content_length = int(headers.get('content-length')) or None
        self.assertEqual(content_length, 9)
        self.assertEqual(content_length, len(response_body))
        self.assertEqual(response_body, tobytes('abcdefghi'))
        # remote does not close connection (keepalive header)
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')

    def test_equal_body(self):
        # check server doesnt close connection when body is equal to
        # cl header
        to_send = tobytes(
            "GET /equal_body HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        content_length = int(headers.get('content-length')) or None
        self.assertEqual(content_length, 9)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        self.assertEqual(content_length, len(response_body))
        self.assertEqual(response_body, tobytes('abcdefghi'))
        # remote does not close connection (keepalive header)
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')

    def test_no_content_length(self):
        # wtf happens when there's no content-length
        to_send = tobytes(
            "GET /no_content_length HTTP/1.0\n"
            "Connection: Keep-Alive\n"
            "Content-Length: 0\n"
            "\n"
        )
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line = fp.readline() # status line
        line, headers, response_body = read_http(fp)
        content_length = headers.get('content-length')
        self.assertEqual(content_length, None)
        self.assertEqual(response_body, tobytes('abcdefghi'))
        # remote closed connection (despite keepalive header)
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class TooLargeTests(object):

    toobig = 1050

    def setUp(self):
        from waitress.tests.fixtureapps import toolarge
        self.start_subprocess(toolarge.app,
                              max_request_header_size=1000,
                              max_request_body_size=1000)

    def tearDown(self):
        self.stop_subprocess()

    def test_request_body_too_large_with_wrong_cl_http10(self):
        body = 'a' * self.toobig
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 5\n\n")
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        # first request succeeds (content-length 5)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # server trusts the content-length header; no pipelining,
        # so request fulfilled, extra bytes are thrown away
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_wrong_cl_http10_keepalive(self):
        body = 'a' * self.toobig
        to_send = ("GET / HTTP/1.0\n"
                   "Content-Length: 5\n"
                   "Connection: Keep-Alive\n\n")
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        # first request succeeds (content-length 5)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        line, headers, response_body = read_http(fp)
        self.assertline(line, '431', 'Request Header Fields Too Large',
                        'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_no_cl_http10(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.0\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # extra bytes are thrown away (no pipelining), connection closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_no_cl_http10_keepalive(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.0\nConnection: Keep-Alive\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # server trusts the content-length header (assumed zero)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        line, headers, response_body = read_http(fp)
        # next response overruns because the extra data appears to be
        # header data
        self.assertline(line, '431', 'Request Header Fields Too Large',
                        'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_wrong_cl_http11(self):
        body = 'a' * self.toobig
        to_send = ("GET / HTTP/1.1\n"
                   "Content-Length: 5\n\n")
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        # first request succeeds (content-length 5)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # second response is an error response
        line, headers, response_body = read_http(fp)
        self.assertline(line, '431', 'Request Header Fields Too Large',
                        'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_wrong_cl_http11_connclose(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.1\nContent-Length: 5\nConnection: close\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # server trusts the content-length header (5)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_no_cl_http11(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.1\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb')
        # server trusts the content-length header (assumed 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # server assumes pipelined requests due to http/1.1, and the first
        # request was assumed c-l 0 because it had no content-length header,
        # so entire body looks like the header of the subsequent request
        # second response is an error response
        line, headers, response_body = read_http(fp)
        self.assertline(line, '431', 'Request Header Fields Too Large',
                        'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_with_no_cl_http11_connclose(self):
        body = 'a' * self.toobig
        to_send = "GET / HTTP/1.1\nConnection: close\n\n"
        to_send += body
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # server trusts the content-length header (assumed 0)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_request_body_too_large_chunked_encoding(self):
        control_line = "20;\r\n" # 20 hex = 32 dec
        s = 'This string has 32 characters.\r\n'
        to_send = "GET / HTTP/1.1\nTransfer-Encoding: chunked\n\n"
        repeat = control_line + s
        to_send += repeat * ((self.toobig // len(repeat)) + 1)
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        # body bytes counter caught a max_request_body_size overrun
        self.assertline(line, '413', 'Request Entity Too Large', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertEqual(headers['content-type'], 'text/plain')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class InternalServerErrorTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import error
        self.start_subprocess(error.app, expose_tracebacks=True)

    def tearDown(self):
        self.stop_subprocess()

    def test_before_start_response_http_10(self):
        to_send = "GET /before_start_response HTTP/1.0\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(headers['connection'], 'close')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_before_start_response_http_11(self):
        to_send = "GET /before_start_response HTTP/1.1\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['content-length', 'content-type', 'date', 'server'])
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_before_start_response_http_11_close(self):
        to_send = tobytes(
            "GET /before_start_response HTTP/1.1\n"
            "Connection: close\n\n")
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['connection', 'content-length', 'content-type', 'date',
             'server'])
        self.assertEqual(headers['connection'], 'close')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_after_start_response_http10(self):
        to_send = "GET /after_start_response HTTP/1.0\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['connection', 'content-length', 'content-type', 'date',
             'server'])
        self.assertEqual(headers['connection'], 'close')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_after_start_response_http11(self):
        to_send = "GET /after_start_response HTTP/1.1\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['content-length', 'content-type', 'date', 'server'])
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_after_start_response_http11_close(self):
        to_send = tobytes(
            "GET /after_start_response HTTP/1.1\n"
            "Connection: close\n\n")
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '500', 'Internal Server Error', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        self.assertTrue(response_body.startswith(b'Internal Server Error'))
        self.assertEqual(sorted(headers.keys()),
            ['connection', 'content-length', 'content-type', 'date',
             'server'])
        self.assertEqual(headers['connection'], 'close')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_after_write_cb(self):
        to_send = "GET /after_write_cb HTTP/1.1\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(response_body, b'')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_in_generator(self):
        to_send = "GET /in_generator HTTP/1.1\n\n"
        to_send = tobytes(to_send)
        self.connect()
        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        self.assertEqual(response_body, b'')
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class FileWrapperTests(object):

    def setUp(self):
        from waitress.tests.fixtureapps import filewrapper
        self.start_subprocess(filewrapper.app)

    def tearDown(self):
        self.stop_subprocess()

    def test_filelike_http11(self):
        to_send = "GET /filelike HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377\330\377' in response_body)
            # connection has not been closed

    def test_filelike_nocl_http11(self):
        to_send = "GET /filelike_nocl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377\330\377' in response_body)
            # connection has not been closed

    def test_filelike_shortcl_http11(self):
        to_send = "GET /filelike_shortcl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, 1)
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377' in response_body)
            # connection has not been closed

    def test_filelike_longcl_http11(self):
        to_send = "GET /filelike_longcl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377\330\377' in response_body)
            # connection has not been closed

    def test_notfilelike_http11(self):
        to_send = "GET /notfilelike HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377\330\377' in response_body)
            # connection has not been closed

    def test_notfilelike_nocl_http11(self):
        to_send = "GET /notfilelike_nocl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed (no content-length)
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_notfilelike_shortcl_http11(self):
        to_send = "GET /notfilelike_shortcl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        for t in range(0, 2):
            self.sock.send(to_send)
            fp = self.sock.makefile('rb', 0)
            line, headers, response_body = read_http(fp)
            self.assertline(line, '200', 'OK', 'HTTP/1.1')
            cl = int(headers['content-length'])
            self.assertEqual(cl, 1)
            self.assertEqual(cl, len(response_body))
            ct = headers['content-type']
            self.assertEqual(ct, 'image/jpeg')
            self.assertTrue(b'\377' in response_body)
            # connection has not been closed

    def test_notfilelike_longcl_http11(self):
        to_send = "GET /notfilelike_longcl HTTP/1.1\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.1')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body) + 10)
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_filelike_http10(self):
        to_send = "GET /filelike HTTP/1.0\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_filelike_nocl_http10(self):
        to_send = "GET /filelike_nocl HTTP/1.0\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_notfilelike_http10(self):
        to_send = "GET /notfilelike HTTP/1.0\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        cl = int(headers['content-length'])
        self.assertEqual(cl, len(response_body))
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

    def test_notfilelike_nocl_http10(self):
        to_send = "GET /notfilelike_nocl HTTP/1.0\n\n"
        to_send = tobytes(to_send)

        self.connect()

        self.sock.send(to_send)
        fp = self.sock.makefile('rb', 0)
        line, headers, response_body = read_http(fp)
        self.assertline(line, '200', 'OK', 'HTTP/1.0')
        ct = headers['content-type']
        self.assertEqual(ct, 'image/jpeg')
        self.assertTrue(b'\377\330\377' in response_body)
        # connection has been closed (no content-length)
        self.send_check_error(to_send)
        self.assertRaises(ConnectionClosed, read_http, fp)

class TcpEchoTests(EchoTests, TcpTests, unittest.TestCase):
    pass

class TcpPipeliningTests(PipeliningTests, TcpTests, unittest.TestCase):
    pass

class TcpExpectContinueTests(ExpectContinueTests, TcpTests, unittest.TestCase):
    pass

class TcpBadContentLengthTests(
        BadContentLengthTests, TcpTests, unittest.TestCase):
    pass

class TcpNoContentLengthTests(
        NoContentLengthTests, TcpTests, unittest.TestCase):
    pass

class TcpWriteCallbackTests(WriteCallbackTests, TcpTests, unittest.TestCase):
    pass

class TcpTooLargeTests(TooLargeTests, TcpTests, unittest.TestCase):
    pass

class TcpInternalServerErrorTests(
        InternalServerErrorTests, TcpTests, unittest.TestCase):
    pass

class TcpFileWrapperTests(FileWrapperTests, TcpTests, unittest.TestCase):
    pass

if hasattr(socket, 'AF_UNIX'):

    class FixtureUnixWSGIServer(server.UnixWSGIServer):
        """A version of UnixWSGIServer that relays back what it's bound to.
        """

        def __init__(self, application, queue, **kw): # pragma: no cover
            # Coverage doesn't see this as it's ran in a separate process.
            # To permit parallel testing, use a PID-dependent socket.
            kw['unix_socket'] = '/tmp/waitress.test-%d.sock' % os.getpid()
            super(FixtureUnixWSGIServer, self).__init__(application, **kw)
            queue.put(self.socket.getsockname())

    class UnixTests(SubprocessTests):

        server = FixtureUnixWSGIServer

        def make_http_connection(self):
            return UnixHTTPConnection(self.bound_to)

        def stop_subprocess(self):
            super(UnixTests, self).stop_subprocess()
            cleanup_unix_socket(self.bound_to)

        def send_check_error(self, to_send):
            # Unlike inet domain sockets, Unix domain sockets can trigger a
            # 'Broken pipe' error when the socket it closed.
            try:
                self.sock.send(to_send)
            except socket.error as exc:
                self.assertEqual(get_errno(exc), errno.EPIPE)

    class UnixEchoTests(EchoTests, UnixTests, unittest.TestCase):
        pass

    class UnixPipeliningTests(PipeliningTests, UnixTests, unittest.TestCase):
        pass

    class UnixExpectContinueTests(
            ExpectContinueTests, UnixTests, unittest.TestCase):
        pass

    class UnixBadContentLengthTests(
            BadContentLengthTests, UnixTests, unittest.TestCase):
        pass

    class UnixNoContentLengthTests(
            NoContentLengthTests, UnixTests, unittest.TestCase):
        pass

    class UnixWriteCallbackTests(
            WriteCallbackTests, UnixTests, unittest.TestCase):
        pass

    class UnixTooLargeTests(TooLargeTests, UnixTests, unittest.TestCase):
        pass

    class UnixInternalServerErrorTests(
            InternalServerErrorTests, UnixTests, unittest.TestCase):
        pass

    class UnixFileWrapperTests(FileWrapperTests, UnixTests, unittest.TestCase):
        pass

def parse_headers(fp):
    """Parses only RFC2822 headers from a file pointer.
    """
    headers = {}
    while True:
        line = fp.readline()
        if line in (b'\r\n', b'\n', b''):
            break
        line = line.decode('iso-8859-1')
        name, value = line.strip().split(':', 1)
        headers[name.lower().strip()] = value.lower().strip()
    return headers

class UnixHTTPConnection(httplib.HTTPConnection):
    """Patched version of HTTPConnection that uses Unix domain sockets.
    """

    def __init__(self, path):
        httplib.HTTPConnection.__init__(self, 'localhost')
        self.path = path

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.path)
        self.sock = sock

class ConnectionClosed(Exception):
    pass

# stolen from gevent
def read_http(fp): # pragma: no cover
    try:
        response_line = fp.readline()
    except socket.error as exc:
        fp.close()
        # errno 104 is ENOTRECOVERABLE, In WinSock 10054 is ECONNRESET
        if get_errno(exc) in (errno.ECONNABORTED, errno.ECONNRESET, 104, 10054):
            raise ConnectionClosed
        raise
    if not response_line:
        raise ConnectionClosed

    header_lines = []
    while True:
        line = fp.readline()
        if line in (b'\r\n', b'\n', b''):
            break
        else:
            header_lines.append(line)
    headers = dict()
    for x in header_lines:
        x = x.strip()
        if not x:
            continue
        key, value = x.split(b': ', 1)
        key = key.decode('iso-8859-1').lower()
        value = value.decode('iso-8859-1')
        assert key not in headers, "%s header duplicated" % key
        headers[key] = value

    if 'content-length' in headers:
        num = int(headers['content-length'])
        body = b''
        left = num
        while left > 0:
            data = fp.read(left)
            if not data:
                break
            body += data
            left -= len(data)
    else:
        # read until EOF
        body = fp.read()

    return response_line, headers, body

# stolen from gevent
def get_errno(exc): # pragma: no cover
    """ Get the error code out of socket.error objects.
    socket.error in <2.5 does not have errno attribute
    socket.error in 3.x does not allow indexing access
    e.args[0] works for all.
    There are cases when args[0] is not errno.
    i.e. http://bugs.python.org/issue6471
    Maybe there are cases when errno is set, but it is not the first argument?
    """
    try:
        if exc.errno is not None:
            return exc.errno
    except AttributeError:
        pass
    try:
        return exc.args[0]
    except IndexError:
        return None

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]

########NEW FILE########
__FILENAME__ = test_init
import unittest

class Test_serve(unittest.TestCase):

    def _callFUT(self, app, **kw):
        from waitress import serve
        return serve(app, **kw)

    def test_it(self):
        server = DummyServerFactory()
        app = object()
        result = self._callFUT(app, _server=server, _quiet=True)
        self.assertEqual(server.app, app)
        self.assertEqual(result, None)
        self.assertEqual(server.ran, True)

class Test_serve_paste(unittest.TestCase):

    def _callFUT(self, app, **kw):
        from waitress import serve_paste
        return serve_paste(app, None, **kw)

    def test_it(self):
        server = DummyServerFactory()
        app = object()
        result = self._callFUT(app, _server=server, _quiet=True)
        self.assertEqual(server.app, app)
        self.assertEqual(result, 0)
        self.assertEqual(server.ran, True)

class DummyServerFactory(object):
    ran = False

    def __call__(self, app, **kw):
        self.adj = DummyAdj(kw)
        self.app = app
        self.kw = kw
        return self

    def run(self):
        self.ran = True

class DummyAdj(object):
    verbose = False

    def __init__(self, kw):
        self.__dict__.update(kw)

########NEW FILE########
__FILENAME__ = test_parser
##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""HTTP Request Parser tests
"""
import unittest

from waitress.compat import (
    text_,
    tobytes,
)

class TestHTTPRequestParser(unittest.TestCase):

    def setUp(self):
        from waitress.parser import HTTPRequestParser
        from waitress.adjustments import Adjustments
        my_adj = Adjustments()
        self.parser = HTTPRequestParser(my_adj)

    def test_get_body_stream_None(self):
        self.parser.body_recv = None
        result = self.parser.get_body_stream()
        self.assertEqual(result.getvalue(), b'')

    def test_get_body_stream_nonNone(self):
        body_rcv = DummyBodyStream()
        self.parser.body_rcv = body_rcv
        result = self.parser.get_body_stream()
        self.assertEqual(result, body_rcv)

    def test_received_nonsense_with_double_cr(self):
        data = b"""\
HTTP/1.0 GET /foobar


"""
        result = self.parser.received(data)
        self.assertEqual(result, 22)
        self.assertTrue(self.parser.completed)
        self.assertEqual(self.parser.headers, {})

    def test_received_bad_host_header(self):
        from waitress.utilities import BadRequest
        data = b"""\
HTTP/1.0 GET /foobar
 Host: foo


"""
        result = self.parser.received(data)
        self.assertEqual(result, 33)
        self.assertTrue(self.parser.completed)
        self.assertEqual(self.parser.error.__class__, BadRequest)

    def test_received_nonsense_nothing(self):
        data = b"""\


"""
        result = self.parser.received(data)
        self.assertEqual(result, 2)
        self.assertTrue(self.parser.completed)
        self.assertEqual(self.parser.headers, {})

    def test_received_no_doublecr(self):
        data = b"""\
GET /foobar HTTP/8.4
"""
        result = self.parser.received(data)
        self.assertEqual(result, 21)
        self.assertFalse(self.parser.completed)
        self.assertEqual(self.parser.headers, {})

    def test_received_already_completed(self):
        self.parser.completed = True
        result = self.parser.received(b'a')
        self.assertEqual(result, 0)

    def test_received_cl_too_large(self):
        from waitress.utilities import RequestEntityTooLarge
        self.parser.adj.max_request_body_size = 2
        data = b"""\
GET /foobar HTTP/8.4
Content-Length: 10

"""
        result = self.parser.received(data)
        self.assertEqual(result, 41)
        self.assertTrue(self.parser.completed)
        self.assertTrue(isinstance(self.parser.error, RequestEntityTooLarge))

    def test_received_headers_too_large(self):
        from waitress.utilities import RequestHeaderFieldsTooLarge
        self.parser.adj.max_request_header_size = 2
        data = b"""\
GET /foobar HTTP/8.4
X-Foo: 1
"""
        result = self.parser.received(data)
        self.assertEqual(result, 30)
        self.assertTrue(self.parser.completed)
        self.assertTrue(isinstance(self.parser.error,
                                   RequestHeaderFieldsTooLarge))

    def test_received_body_too_large(self):
        from waitress.utilities import RequestEntityTooLarge
        self.parser.adj.max_request_body_size = 2
        data = b"""\
GET /foobar HTTP/1.1
Transfer-Encoding: chunked
X-Foo: 1

20;\r\n
This string has 32 characters\r\n
0\r\n\r\n"""
        result = self.parser.received(data)
        self.assertEqual(result, 58)
        self.parser.received(data[result:])
        self.assertTrue(self.parser.completed)
        self.assertTrue(isinstance(self.parser.error,
                                   RequestEntityTooLarge))

    def test_received_error_from_parser(self):
        from waitress.utilities import BadRequest
        data = b"""\
GET /foobar HTTP/1.1
Transfer-Encoding: chunked
X-Foo: 1

garbage
"""
        # header
        result = self.parser.received(data)
        # body
        result = self.parser.received(data[result:])
        self.assertEqual(result, 8)
        self.assertTrue(self.parser.completed)
        self.assertTrue(isinstance(self.parser.error,
                                   BadRequest))

    def test_received_chunked_completed_sets_content_length(self):
        data = b"""\
GET /foobar HTTP/1.1
Transfer-Encoding: chunked
X-Foo: 1

20;\r\n
This string has 32 characters\r\n
0\r\n\r\n"""
        result = self.parser.received(data)
        self.assertEqual(result, 58)
        data = data[result:]
        result = self.parser.received(data)
        self.assertTrue(self.parser.completed)
        self.assertTrue(self.parser.error is None)
        self.assertEqual(self.parser.headers['CONTENT_LENGTH'], '32')
        
    def test_parse_header_gardenpath(self):
        data = b"""\
GET /foobar HTTP/8.4
foo: bar"""
        self.parser.parse_header(data)
        self.assertEqual(self.parser.first_line, b'GET /foobar HTTP/8.4')
        self.assertEqual(self.parser.headers['FOO'], 'bar')

    def test_parse_header_no_cr_in_headerplus(self):
        data = b"GET /foobar HTTP/8.4"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.first_line, data)

    def test_parse_header_bad_content_length(self):
        data = b"GET /foobar HTTP/8.4\ncontent-length: abc"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.body_rcv, None)

    def test_parse_header_11_te_chunked(self):
        # NB: test that capitalization of header value is unimportant
        data = b"GET /foobar HTTP/1.1\ntransfer-encoding: ChUnKed"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.body_rcv.__class__.__name__,
                         'ChunkedReceiver')

    def test_parse_header_11_expect_continue(self):
        data = b"GET /foobar HTTP/1.1\nexpect: 100-continue"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.expect_continue, True)

    def test_parse_header_connection_close(self):
        data = b"GET /foobar HTTP/1.1\nConnection: close\n\n"
        self.parser.parse_header(data)
        self.assertEqual(self.parser.connection_close, True)

    def test_close_with_body_rcv(self):
        body_rcv = DummyBodyStream()
        self.parser.body_rcv = body_rcv
        self.parser.close()
        self.assertTrue(body_rcv.closed)

    def test_close_with_no_body_rcv(self):
        self.parser.body_rcv = None
        self.parser.close() # doesn't raise

class Test_split_uri(unittest.TestCase):

    def _callFUT(self, uri):
        from waitress.parser import split_uri
        (self.proxy_scheme,
         self.proxy_netloc,
         self.path,
         self.query, self.fragment) = split_uri(uri)

    def test_split_uri_unquoting_unneeded(self):
        self._callFUT(b'http://localhost:8080/abc def')
        self.assertEqual(self.path, '/abc def')

    def test_split_uri_unquoting_needed(self):
        self._callFUT(b'http://localhost:8080/abc%20def')
        self.assertEqual(self.path, '/abc def')

    def test_split_url_with_query(self):
        self._callFUT(b'http://localhost:8080/abc?a=1&b=2')
        self.assertEqual(self.path, '/abc')
        self.assertEqual(self.query, 'a=1&b=2')

    def test_split_url_with_query_empty(self):
        self._callFUT(b'http://localhost:8080/abc?')
        self.assertEqual(self.path, '/abc')
        self.assertEqual(self.query, '')

    def test_split_url_with_fragment(self):
        self._callFUT(b'http://localhost:8080/#foo')
        self.assertEqual(self.path, '/')
        self.assertEqual(self.fragment, 'foo')

    def test_split_url_https(self):
        self._callFUT(b'https://localhost:8080/')
        self.assertEqual(self.path, '/')
        self.assertEqual(self.proxy_scheme, 'https')
        self.assertEqual(self.proxy_netloc, 'localhost:8080')

class Test_get_header_lines(unittest.TestCase):

    def _callFUT(self, data):
        from waitress.parser import get_header_lines
        return get_header_lines(data)

    def test_get_header_lines(self):
        result = self._callFUT(b'slam\nslim')
        self.assertEqual(result, [b'slam', b'slim'])

    def test_get_header_lines_tabbed(self):
        result = self._callFUT(b'slam\n\tslim')
        self.assertEqual(result, [b'slamslim'])

    def test_get_header_lines_malformed(self):
        # http://corte.si/posts/code/pathod/pythonservers/index.html
        from waitress.parser import ParsingError
        self.assertRaises(ParsingError,
                          self._callFUT, b' Host: localhost\r\n\r\n')

class Test_crack_first_line(unittest.TestCase):

    def _callFUT(self, line):
        from waitress.parser import crack_first_line
        return crack_first_line(line)

    def test_crack_first_line_matchok(self):
        result = self._callFUT(b'get / HTTP/1.0')
        self.assertEqual(result, (b'GET', b'/', b'1.0'))

    def test_crack_first_line_nomatch(self):
        result = self._callFUT(b'get / bleh')
        self.assertEqual(result, (b'', b'', b''))

    def test_crack_first_line_missing_version(self):
        result = self._callFUT(b'get /')
        self.assertEqual(result, (b'GET', b'/', None))

class TestHTTPRequestParserIntegration(unittest.TestCase):

    def setUp(self):
        from waitress.parser import HTTPRequestParser
        from waitress.adjustments import Adjustments
        my_adj = Adjustments()
        self.parser = HTTPRequestParser(my_adj)

    def feed(self, data):
        parser = self.parser
        for n in range(100): # make sure we never loop forever
            consumed = parser.received(data)
            data = data[consumed:]
            if parser.completed:
                return
        raise ValueError('Looping') # pragma: no cover

    def testSimpleGET(self):
        data = b"""\
GET /foobar HTTP/8.4
FirstName: mickey
lastname: Mouse
content-length: 7

Hello.
"""
        parser = self.parser
        self.feed(data)
        self.assertTrue(parser.completed)
        self.assertEqual(parser.version, '8.4')
        self.assertFalse(parser.empty)
        self.assertEqual(parser.headers,
                         {'FIRSTNAME': 'mickey',
                          'LASTNAME': 'Mouse',
                          'CONTENT_LENGTH': '7',
                          })
        self.assertEqual(parser.path, '/foobar')
        self.assertEqual(parser.command, 'GET')
        self.assertEqual(parser.query, '')
        self.assertEqual(parser.proxy_scheme, '')
        self.assertEqual(parser.proxy_netloc, '')
        self.assertEqual(parser.get_body_stream().getvalue(), b'Hello.\n')

    def testComplexGET(self):
        data = b"""\
GET /foo/a+%2B%2F%C3%A4%3D%26a%3Aint?d=b+%2B%2F%3D%26b%3Aint&c+%2B%2F%3D%26c%3Aint=6 HTTP/8.4
FirstName: mickey
lastname: Mouse
content-length: 10

Hello mickey.
"""
        parser = self.parser
        self.feed(data)
        self.assertEqual(parser.command, 'GET')
        self.assertEqual(parser.version, '8.4')
        self.assertFalse(parser.empty)
        self.assertEqual(parser.headers,
                         {'FIRSTNAME': 'mickey',
                          'LASTNAME': 'Mouse',
                          'CONTENT_LENGTH': '10',
                          })
        # path should be utf-8 encoded
        self.assertEqual(tobytes(parser.path).decode('utf-8'),
                         text_(b'/foo/a++/\xc3\xa4=&a:int', 'utf-8'))
        self.assertEqual(parser.query,
                         'd=b+%2B%2F%3D%26b%3Aint&c+%2B%2F%3D%26c%3Aint=6')
        self.assertEqual(parser.get_body_stream().getvalue(), b'Hello mick')

    def testProxyGET(self):
        data = b"""\
GET https://example.com:8080/foobar HTTP/8.4
content-length: 7

Hello.
"""
        parser = self.parser
        self.feed(data)
        self.assertTrue(parser.completed)
        self.assertEqual(parser.version, '8.4')
        self.assertFalse(parser.empty)
        self.assertEqual(parser.headers,
                         {'CONTENT_LENGTH': '7',
                          })
        self.assertEqual(parser.path, '/foobar')
        self.assertEqual(parser.command, 'GET')
        self.assertEqual(parser.proxy_scheme, 'https')
        self.assertEqual(parser.proxy_netloc, 'example.com:8080')
        self.assertEqual(parser.command, 'GET')
        self.assertEqual(parser.query, '')
        self.assertEqual(parser.get_body_stream().getvalue(), b'Hello.\n')

    def testDuplicateHeaders(self):
        # Ensure that headers with the same key get concatenated as per
        # RFC2616.
        data = b"""\
GET /foobar HTTP/8.4
x-forwarded-for: 10.11.12.13
x-forwarded-for: unknown,127.0.0.1
X-Forwarded_for: 255.255.255.255
content-length: 7

Hello.
"""
        self.feed(data)
        self.assertTrue(self.parser.completed)
        self.assertEqual(self.parser.headers, {
            'CONTENT_LENGTH': '7',
            'X_FORWARDED_FOR':
                '10.11.12.13, unknown,127.0.0.1, 255.255.255.255',
        })

class DummyBodyStream(object):

    def getfile(self):
        return self

    def getbuf(self):
        return self

    def close(self):
        self.closed = True

########NEW FILE########
__FILENAME__ = test_receiver
import unittest

class TestFixedStreamReceiver(unittest.TestCase):

    def _makeOne(self, cl, buf):
        from waitress.receiver import FixedStreamReceiver
        return FixedStreamReceiver(cl, buf)

    def test_received_remain_lt_1(self):
        buf = DummyBuffer()
        inst = self._makeOne(0, buf)
        result = inst.received('a')
        self.assertEqual(result, 0)
        self.assertEqual(inst.completed, True)

    def test_received_remain_lte_datalen(self):
        buf = DummyBuffer()
        inst = self._makeOne(1, buf)
        result = inst.received('aa')
        self.assertEqual(result, 1)
        self.assertEqual(inst.completed, True)
        self.assertEqual(inst.completed, 1)
        self.assertEqual(inst.remain, 0)
        self.assertEqual(buf.data, ['a'])

    def test_received_remain_gt_datalen(self):
        buf = DummyBuffer()
        inst = self._makeOne(10, buf)
        result = inst.received('aa')
        self.assertEqual(result, 2)
        self.assertEqual(inst.completed, False)
        self.assertEqual(inst.remain, 8)
        self.assertEqual(buf.data, ['aa'])

    def test_getfile(self):
        buf = DummyBuffer()
        inst = self._makeOne(10, buf)
        self.assertEqual(inst.getfile(), buf)

    def test_getbuf(self):
        buf = DummyBuffer()
        inst = self._makeOne(10, buf)
        self.assertEqual(inst.getbuf(), buf)

    def test___len__(self):
        buf = DummyBuffer(['1', '2'])
        inst = self._makeOne(10, buf)
        self.assertEqual(inst.__len__(), 2)

class TestChunkedReceiver(unittest.TestCase):

    def _makeOne(self, buf):
        from waitress.receiver import ChunkedReceiver
        return ChunkedReceiver(buf)

    def test_alreadycompleted(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        inst.completed = True
        result = inst.received(b'a')
        self.assertEqual(result, 0)
        self.assertEqual(inst.completed, True)

    def test_received_remain_gt_zero(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        inst.chunk_remainder = 100
        result = inst.received(b'a')
        self.assertEqual(inst.chunk_remainder, 99)
        self.assertEqual(result, 1)
        self.assertEqual(inst.completed, False)

    def test_received_control_line_notfinished(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        result = inst.received(b'a')
        self.assertEqual(inst.control_line, b'a')
        self.assertEqual(result, 1)
        self.assertEqual(inst.completed, False)

    def test_received_control_line_finished_garbage_in_input(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        result = inst.received(b'garbage\n')
        self.assertEqual(result, 8)
        self.assertTrue(inst.error)

    def test_received_control_line_finished_all_chunks_not_received(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        result = inst.received(b'a;discard\n')
        self.assertEqual(inst.control_line, b'')
        self.assertEqual(inst.chunk_remainder, 10)
        self.assertEqual(inst.all_chunks_received, False)
        self.assertEqual(result, 10)
        self.assertEqual(inst.completed, False)

    def test_received_control_line_finished_all_chunks_received(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        result = inst.received(b'0;discard\n')
        self.assertEqual(inst.control_line, b'')
        self.assertEqual(inst.all_chunks_received, True)
        self.assertEqual(result, 10)
        self.assertEqual(inst.completed, False)

    def test_received_trailer_startswith_crlf(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        inst.all_chunks_received = True
        result = inst.received(b'\r\n')
        self.assertEqual(result, 2)
        self.assertEqual(inst.completed, True)

    def test_received_trailer_startswith_lf(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        inst.all_chunks_received = True
        result = inst.received(b'\n')
        self.assertEqual(result, 1)
        self.assertEqual(inst.completed, True)

    def test_received_trailer_not_finished(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        inst.all_chunks_received = True
        result = inst.received(b'a')
        self.assertEqual(result, 1)
        self.assertEqual(inst.completed, False)

    def test_received_trailer_finished(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        inst.all_chunks_received = True
        result = inst.received(b'abc\r\n\r\n')
        self.assertEqual(inst.trailer, b'abc\r\n\r\n')
        self.assertEqual(result, 7)
        self.assertEqual(inst.completed, True)

    def test_getfile(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        self.assertEqual(inst.getfile(), buf)

    def test_getbuf(self):
        buf = DummyBuffer()
        inst = self._makeOne(buf)
        self.assertEqual(inst.getbuf(), buf)

    def test___len__(self):
        buf = DummyBuffer(['1', '2'])
        inst = self._makeOne(buf)
        self.assertEqual(inst.__len__(), 2)
        
class DummyBuffer(object):

    def __init__(self, data=None):
        if data is None:
            data = []
        self.data = data

    def append(self, s):
        self.data.append(s)

    def getfile(self):
        return self

    def __len__(self):
        return len(self.data)

########NEW FILE########
__FILENAME__ = test_regression
##############################################################################
#
# Copyright (c) 2005 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Tests for waitress.channel maintenance logic
"""
import doctest

class FakeSocket: # pragma: no cover
    data = ''
    setblocking = lambda *_: None
    close = lambda *_: None

    def __init__(self, no):
        self.no = no

    def fileno(self):
        return self.no

    def getpeername(self):
        return ('localhost', self.no)

    def send(self, data):
        self.data += data
        return len(data)

    def recv(self, data):
        return 'data'

def zombies_test():
    """Regression test for HTTPChannel.maintenance method

    Bug: This method checks for channels that have been "inactive" for a
    configured time. The bug was that last_activity is set at creation time
    but never updated during async channel activity (reads and writes), so
    any channel older than the configured timeout will be closed when a new
    channel is created, regardless of activity.

    >>> import time
    >>> import waitress.adjustments
    >>> config = waitress.adjustments.Adjustments()

    >>> from waitress.server import HTTPServer
    >>> class TestServer(HTTPServer):
    ...     def bind(self, (ip, port)):
    ...         print "Listening on %s:%d" % (ip or '*', port)
    >>> sb = TestServer('127.0.0.1', 80, start=False, verbose=True)
    Listening on 127.0.0.1:80

    First we confirm the correct behavior, where a channel with no activity
    for the timeout duration gets closed.

    >>> from waitress.channel import HTTPChannel
    >>> socket = FakeSocket(42)
    >>> channel = HTTPChannel(sb, socket, ('localhost', 42))

    >>> channel.connected
    True

    >>> channel.last_activity -= int(config.channel_timeout) + 1

    >>> channel.next_channel_cleanup[0] = channel.creation_time - int(
    ...     config.cleanup_interval) - 1

    >>> socket2 = FakeSocket(7)
    >>> channel2 = HTTPChannel(sb, socket2, ('localhost', 7))

    >>> channel.connected
    False

    Write Activity
    --------------

    Now we make sure that if there is activity the channel doesn't get closed
    incorrectly.

    >>> channel2.connected
    True

    >>> channel2.last_activity -= int(config.channel_timeout) + 1

    >>> channel2.handle_write()

    >>> channel2.next_channel_cleanup[0] = channel2.creation_time - int(
    ...     config.cleanup_interval) - 1

    >>> socket3 = FakeSocket(3)
    >>> channel3 = HTTPChannel(sb, socket3, ('localhost', 3))

    >>> channel2.connected
    True

    Read Activity
    --------------

    We should test to see that read activity will update a channel as well.

    >>> channel3.connected
    True

    >>> channel3.last_activity -= int(config.channel_timeout) + 1

    >>> import waitress.parser
    >>> channel3.parser_class = (
    ...    waitress.parser.HTTPRequestParser)
    >>> channel3.handle_read()

    >>> channel3.next_channel_cleanup[0] = channel3.creation_time - int(
    ...     config.cleanup_interval) - 1

    >>> socket4 = FakeSocket(4)
    >>> channel4 = HTTPChannel(sb, socket4, ('localhost', 4))

    >>> channel3.connected
    True

    Main loop window
    ----------------

    There is also a corner case we'll do a shallow test for where a
    channel can be closed waiting for the main loop.

    >>> channel4.last_activity -= 1

    >>> last_active = channel4.last_activity

    >>> channel4.set_async()

    >>> channel4.last_activity != last_active
    True

"""

def test_suite():
    return doctest.DocTestSuite()

########NEW FILE########
__FILENAME__ = test_runner
import contextlib
import os
import sys

if sys.version_info[:2] == (2, 6): # pragma: no cover
    import unittest2 as unittest
else: # pragma: no cover
    import unittest

from waitress import runner

class Test_match(unittest.TestCase):

    def test_empty(self):
        self.assertRaisesRegexp(
            ValueError, "^Malformed application ''$",
            runner.match, '')

    def test_module_only(self):
        self.assertRaisesRegexp(
            ValueError, r"^Malformed application 'foo\.bar'$",
            runner.match, 'foo.bar')

    def test_bad_module(self):
        self.assertRaisesRegexp(
            ValueError,
            r"^Malformed application 'foo#bar:barney'$",
            runner.match, 'foo#bar:barney')

    def test_module_obj(self):
        self.assertTupleEqual(
            runner.match('foo.bar:fred.barney'),
            ('foo.bar', 'fred.barney'))

class Test_resolve(unittest.TestCase):

    def test_bad_module(self):
        self.assertRaises(
            ImportError,
            runner.resolve, 'nonexistent', 'nonexistent_function')

    def test_nonexistent_function(self):
        self.assertRaisesRegexp(
            AttributeError,
            r"^'module' object has no attribute 'nonexistent_function'$",
            runner.resolve, 'os.path', 'nonexistent_function')

    def test_simple_happy_path(self):
        from os.path import exists
        self.assertIs(runner.resolve('os.path', 'exists'), exists)

    def test_complex_happy_path(self):
        # Ensure we can recursively resolve object attributes if necessary.
        self.assertEquals(
            runner.resolve('os.path', 'exists.__name__'),
            'exists')

class Test_run(unittest.TestCase):

    def match_output(self, argv, code, regex):
        argv = ['waitress-serve'] + argv
        with capture() as captured:
            self.assertEqual(runner.run(argv=argv), code)
        self.assertRegexpMatches(captured.getvalue(), regex)
        captured.close()

    def test_bad(self):
        self.match_output(
            ['--bad-opt'],
            1,
            '^Error: option --bad-opt not recognized')

    def test_help(self):
        self.match_output(
            ['--help'],
            0,
            "^Usage:\n\n    waitress-serve")

    def test_no_app(self):
        self.match_output(
            [],
            1,
            "^Error: Specify one application only")

    def test_multiple_apps_app(self):
        self.match_output(
            ['a:a', 'b:b'],
            1,
            "^Error: Specify one application only")

    def test_bad_apps_app(self):
        self.match_output(
            ['a'],
            1,
            "^Error: Malformed application 'a'")

    def test_bad_app_module(self):
        self.match_output(
            ['nonexistent:a'],
            1,
            "^Error: Bad module 'nonexistent'")

    def test_cwd_added_to_path(self):
        def null_serve(app, **kw):
            pass
        sys_path = sys.path
        current_dir = os.getcwd()
        try:
            os.chdir(os.path.dirname(__file__))
            argv = [
                'waitress-serve',
                'fixtureapps.runner:app',
            ]
            self.assertEqual(runner.run(argv=argv, _serve=null_serve), 0)
        finally:
            sys.path = sys_path
            os.chdir(current_dir)

    def test_bad_app_object(self):
        self.match_output(
            ['waitress.tests.fixtureapps.runner:a'],
            1,
            "^Error: Bad object name 'a'")

    def test_simple_call(self):
        import waitress.tests.fixtureapps.runner as _apps
        def check_server(app, **kw):
            self.assertIs(app, _apps.app)
            self.assertDictEqual(kw, {'port': '80'})
        argv = [
            'waitress-serve',
            '--port=80',
            'waitress.tests.fixtureapps.runner:app',
        ]
        self.assertEqual(runner.run(argv=argv, _serve=check_server), 0)

    def test_returned_app(self):
        import waitress.tests.fixtureapps.runner as _apps
        def check_server(app, **kw):
            self.assertIs(app, _apps.app)
            self.assertDictEqual(kw, {'port': '80'})
        argv = [
            'waitress-serve',
            '--port=80',
            '--call',
            'waitress.tests.fixtureapps.runner:returns_app',
        ]
        self.assertEqual(runner.run(argv=argv, _serve=check_server), 0)

@contextlib.contextmanager
def capture():
    from waitress.compat import NativeIO
    fd = NativeIO()
    sys.stdout = fd
    sys.stderr = fd
    yield fd
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

########NEW FILE########
__FILENAME__ = test_server
import errno
import socket
import unittest

class TestWSGIServer(unittest.TestCase):

    def _makeOne(self, application, host='127.0.0.1', port=0,
                 _dispatcher=None, adj=None, map=None, _start=True,
                 _sock=None, _server=None):
        from waitress.server import create_server
        return create_server(
            application,
            host=host,
            port=port,
            map=map,
            _dispatcher=_dispatcher,
            _start=_start,
            _sock=_sock)

    def _makeOneWithMap(self, adj=None, _start=True, host='127.0.0.1',
                        port=0, app=None):
        sock = DummySock()
        task_dispatcher = DummyTaskDispatcher()
        map = {}
        return self._makeOne(
            app,
            host=host,
            port=port,
            map=map,
            _sock=sock,
            _dispatcher=task_dispatcher,
            _start=_start,
        )

    def test_ctor_start_true(self):
        inst = self._makeOneWithMap(_start=True)
        self.assertEqual(inst.accepting, True)
        self.assertEqual(inst.socket.listened, 1024)

    def test_ctor_makes_dispatcher(self):
        inst = self._makeOne(None, _start=False, map={})
        self.assertEqual(inst.task_dispatcher.__class__.__name__,
                         'ThreadedTaskDispatcher')

    def test_ctor_start_false(self):
        inst = self._makeOneWithMap(_start=False)
        self.assertEqual(inst.accepting, False)

    def test_get_server_name_empty(self):
        inst = self._makeOneWithMap(_start=False)
        result = inst.get_server_name('')
        self.assertTrue(result)

    def test_get_server_name_with_ip(self):
        inst = self._makeOneWithMap(_start=False)
        result = inst.get_server_name('127.0.0.1')
        self.assertTrue(result)

    def test_get_server_name_with_hostname(self):
        inst = self._makeOneWithMap(_start=False)
        result = inst.get_server_name('fred.flintstone.com')
        self.assertEqual(result, 'fred.flintstone.com')

    def test_get_server_name_0000(self):
        inst = self._makeOneWithMap(_start=False)
        result = inst.get_server_name('0.0.0.0')
        self.assertEqual(result, 'localhost')

    def test_run(self):
        inst = self._makeOneWithMap(_start=False)
        inst.asyncore = DummyAsyncore()
        inst.task_dispatcher = DummyTaskDispatcher()
        inst.run()
        self.assertTrue(inst.task_dispatcher.was_shutdown)

    def test_pull_trigger(self):
        inst = self._makeOneWithMap(_start=False)
        inst.trigger = DummyTrigger()
        inst.pull_trigger()
        self.assertEqual(inst.trigger.pulled, True)

    def test_add_task(self):
        task = DummyTask()
        inst = self._makeOneWithMap()
        inst.add_task(task)
        self.assertEqual(inst.task_dispatcher.tasks, [task])
        self.assertFalse(task.serviced)

    def test_readable_not_accepting(self):
        inst = self._makeOneWithMap()
        inst.accepting = False
        self.assertFalse(inst.readable())

    def test_readable_maplen_gt_connection_limit(self):
        inst = self._makeOneWithMap()
        inst.accepting = True
        inst.adj = DummyAdj
        inst._map = {'a': 1, 'b': 2}
        self.assertFalse(inst.readable())

    def test_readable_maplen_lt_connection_limit(self):
        inst = self._makeOneWithMap()
        inst.accepting = True
        inst.adj = DummyAdj
        inst._map = {}
        self.assertTrue(inst.readable())

    def test_readable_maintenance_false(self):
        import time
        inst = self._makeOneWithMap()
        then = time.time() + 1000
        inst.next_channel_cleanup = then
        L = []
        inst.maintenance = lambda t: L.append(t)
        inst.readable()
        self.assertEqual(L, [])
        self.assertEqual(inst.next_channel_cleanup, then)

    def test_readable_maintenance_true(self):
        inst = self._makeOneWithMap()
        inst.next_channel_cleanup = 0
        L = []
        inst.maintenance = lambda t: L.append(t)
        inst.readable()
        self.assertEqual(len(L), 1)
        self.assertNotEqual(inst.next_channel_cleanup, 0)

    def test_writable(self):
        inst = self._makeOneWithMap()
        self.assertFalse(inst.writable())

    def test_handle_read(self):
        inst = self._makeOneWithMap()
        self.assertEqual(inst.handle_read(), None)

    def test_handle_connect(self):
        inst = self._makeOneWithMap()
        self.assertEqual(inst.handle_connect(), None)

    def test_handle_accept_wouldblock_socket_error(self):
        inst = self._makeOneWithMap()
        ewouldblock = socket.error(errno.EWOULDBLOCK)
        inst.socket = DummySock(toraise=ewouldblock)
        inst.handle_accept()
        self.assertEqual(inst.socket.accepted, False)

    def test_handle_accept_other_socket_error(self):
        inst = self._makeOneWithMap()
        eaborted = socket.error(errno.ECONNABORTED)
        inst.socket = DummySock(toraise=eaborted)
        inst.adj = DummyAdj
        def foo():
            raise socket.error
        inst.accept = foo
        inst.logger = DummyLogger()
        inst.handle_accept()
        self.assertEqual(inst.socket.accepted, False)
        self.assertEqual(len(inst.logger.logged), 1)

    def test_handle_accept_noerror(self):
        inst = self._makeOneWithMap()
        innersock = DummySock()
        inst.socket = DummySock(acceptresult=(innersock, None))
        inst.adj = DummyAdj
        L = []
        inst.channel_class = lambda *arg, **kw: L.append(arg)
        inst.handle_accept()
        self.assertEqual(inst.socket.accepted, True)
        self.assertEqual(innersock.opts, [('level', 'optname', 'value')])
        self.assertEqual(L, [(inst, innersock, None, inst.adj)])

    def test_maintenance(self):
        inst = self._makeOneWithMap()

        class DummyChannel(object):
            requests = []
        zombie = DummyChannel()
        zombie.last_activity = 0
        zombie.running_tasks = False
        inst.active_channels[100] = zombie
        inst.maintenance(10000)
        self.assertEqual(zombie.will_close, True)

    def test_backward_compatibility(self):
        from waitress.server import WSGIServer, TcpWSGIServer
        from waitress.adjustments import Adjustments
        self.assertTrue(WSGIServer is TcpWSGIServer)
        inst = WSGIServer(None, _start=False, port=1234)
        # Ensure the adjustment was actually applied.
        self.assertNotEqual(Adjustments.port, 1234)
        self.assertEqual(inst.adj.port, 1234)

if hasattr(socket, 'AF_UNIX'):

    class TestUnixWSGIServer(unittest.TestCase):
        unix_socket = '/tmp/waitress.test.sock'

        def _makeOne(self, _start=True, _sock=None):
            from waitress.server import create_server
            return create_server(
                None,
                map={},
                _start=_start,
                _sock=_sock,
                _dispatcher=DummyTaskDispatcher(),
                unix_socket=self.unix_socket,
                unix_socket_perms='600'
            )

        def _makeDummy(self, *args, **kwargs):
            sock = DummySock(*args, **kwargs)
            sock.family = socket.AF_UNIX
            return sock

        def test_unix(self):
            inst = self._makeOne(_start=False)
            self.assertEqual(inst.socket.family, socket.AF_UNIX)
            self.assertEqual(inst.socket.getsockname(), self.unix_socket)

        def test_handle_accept(self):
            # Working on the assumption that we only have to test the happy path
            # for Unix domain sockets as the other paths should've been covered
            # by inet sockets.
            client = self._makeDummy()
            listen = self._makeDummy(acceptresult=(client, None))
            inst = self._makeOne(_sock=listen)
            self.assertEqual(inst.accepting, True)
            self.assertEqual(inst.socket.listened, 1024)
            L = []
            inst.channel_class = lambda *arg, **kw: L.append(arg)
            inst.handle_accept()
            self.assertEqual(inst.socket.accepted, True)
            self.assertEqual(client.opts, [])
            self.assertEqual(
                L,
                [(inst, client, ('localhost', None), inst.adj)]
            )

class DummySock(object):
    accepted = False
    blocking = False
    family = socket.AF_INET

    def __init__(self, toraise=None, acceptresult=(None, None)):
        self.toraise = toraise
        self.acceptresult = acceptresult
        self.bound = None
        self.opts = []

    def bind(self, addr):
        self.bound = addr

    def accept(self):
        if self.toraise:
            raise self.toraise
        self.accepted = True
        return self.acceptresult

    def setblocking(self, x):
        self.blocking = True

    def fileno(self):
        return 10

    def getpeername(self):
        return '127.0.0.1'

    def setsockopt(self, *arg):
        self.opts.append(arg)

    def getsockopt(self, *arg):
        return 1

    def listen(self, num):
        self.listened = num

    def getsockname(self):
        return self.bound

class DummyTaskDispatcher(object):

    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def shutdown(self):
        self.was_shutdown = True

class DummyTask(object):
    serviced = False
    start_response_called = False
    wrote_header = False
    status = '200 OK'

    def __init__(self):
        self.response_headers = {}
        self.written = ''

    def service(self): # pragma: no cover
        self.serviced = True

class DummyAdj:
    connection_limit = 1
    log_socket_errors = True
    socket_options = [('level', 'optname', 'value')]
    cleanup_interval = 900
    channel_timeout = 300

class DummyAsyncore(object):

    def loop(self, timeout=30.0, use_poll=False, map=None, count=None):
        raise SystemExit

class DummyTrigger(object):

    def pull_trigger(self):
        self.pulled = True

class DummyLogger(object):

    def __init__(self):
        self.logged = []

    def warning(self, msg, **kw):
        self.logged.append(msg)

########NEW FILE########
__FILENAME__ = test_task
import unittest
import io

class TestThreadedTaskDispatcher(unittest.TestCase):

    def _makeOne(self):
        from waitress.task import ThreadedTaskDispatcher
        return ThreadedTaskDispatcher()

    def test_handler_thread_task_is_None(self):
        inst = self._makeOne()
        inst.threads[0] = True
        inst.queue.put(None)
        inst.handler_thread(0)
        self.assertEqual(inst.stop_count, -1)
        self.assertEqual(inst.threads, {})

    def test_handler_thread_task_raises(self):
        from waitress.task import JustTesting
        inst = self._makeOne()
        inst.threads[0] = True
        inst.logger = DummyLogger()
        task = DummyTask(JustTesting)
        inst.logger = DummyLogger()
        inst.queue.put(task)
        inst.handler_thread(0)
        self.assertEqual(inst.stop_count, -1)
        self.assertEqual(inst.threads, {})
        self.assertEqual(len(inst.logger.logged), 1)

    def test_set_thread_count_increase(self):
        inst = self._makeOne()
        L = []
        inst.start_new_thread = lambda *x: L.append(x)
        inst.set_thread_count(1)
        self.assertEqual(L, [(inst.handler_thread, (0,))])

    def test_set_thread_count_increase_with_existing(self):
        inst = self._makeOne()
        L = []
        inst.threads = {0: 1}
        inst.start_new_thread = lambda *x: L.append(x)
        inst.set_thread_count(2)
        self.assertEqual(L, [(inst.handler_thread, (1,))])

    def test_set_thread_count_decrease(self):
        inst = self._makeOne()
        inst.threads = {'a': 1, 'b': 2}
        inst.set_thread_count(1)
        self.assertEqual(inst.queue.qsize(), 1)
        self.assertEqual(inst.queue.get(), None)

    def test_set_thread_count_same(self):
        inst = self._makeOne()
        L = []
        inst.start_new_thread = lambda *x: L.append(x)
        inst.threads = {0: 1}
        inst.set_thread_count(1)
        self.assertEqual(L, [])

    def test_add_task(self):
        task = DummyTask()
        inst = self._makeOne()
        inst.add_task(task)
        self.assertEqual(inst.queue.qsize(), 1)
        self.assertTrue(task.deferred)

    def test_add_task_defer_raises(self):
        task = DummyTask(ValueError)
        inst = self._makeOne()
        self.assertRaises(ValueError, inst.add_task, task)
        self.assertEqual(inst.queue.qsize(), 0)
        self.assertTrue(task.deferred)
        self.assertTrue(task.cancelled)

    def test_shutdown_one_thread(self):
        inst = self._makeOne()
        inst.threads[0] = 1
        inst.logger = DummyLogger()
        task = DummyTask()
        inst.queue.put(task)
        self.assertEqual(inst.shutdown(timeout=.01), True)
        self.assertEqual(inst.logger.logged, ['1 thread(s) still running'])
        self.assertEqual(task.cancelled, True)

    def test_shutdown_no_threads(self):
        inst = self._makeOne()
        self.assertEqual(inst.shutdown(timeout=.01), True)

    def test_shutdown_no_cancel_pending(self):
        inst = self._makeOne()
        self.assertEqual(inst.shutdown(cancel_pending=False, timeout=.01),
                         False)

class TestTask(unittest.TestCase):

    def _makeOne(self, channel=None, request=None):
        if channel is None:
            channel = DummyChannel()
        if request is None:
            request = DummyParser()
        from waitress.task import Task
        return Task(channel, request)

    def test_ctor_version_not_in_known(self):
        request = DummyParser()
        request.version = '8.4'
        inst = self._makeOne(request=request)
        self.assertEqual(inst.version, '1.0')

    def test_cancel(self):
        inst = self._makeOne()
        inst.cancel()
        self.assertTrue(inst.close_on_finish)

    def test_defer(self):
        inst = self._makeOne()
        self.assertEqual(inst.defer(), None)

    def test_build_response_header_bad_http_version(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '8.4'
        self.assertRaises(AssertionError, inst.build_response_header)

    def test_build_response_header_v10_keepalive_no_content_length(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.request.headers['CONNECTION'] = 'keep-alive'
        inst.version = '1.0'
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], b'HTTP/1.0 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')
        self.assertEqual(inst.close_on_finish, True)
        self.assertTrue(('Connection', 'close') in inst.response_headers)

    def test_build_response_header_v10_keepalive_with_content_length(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.request.headers['CONNECTION'] = 'keep-alive'
        inst.response_headers = [('Content-Length', '10')]
        inst.version = '1.0'
        inst.content_length = 0
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.0 200 OK')
        self.assertEqual(lines[1], b'Connection: Keep-Alive')
        self.assertEqual(lines[2], b'Content-Length: 10')
        self.assertTrue(lines[3].startswith(b'Date:'))
        self.assertEqual(lines[4], b'Server: waitress')
        self.assertEqual(inst.close_on_finish, False)

    def test_build_response_header_v11_connection_closed_by_client(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.1'
        inst.request.headers['CONNECTION'] = 'close'
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.1 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')
        self.assertEqual(lines[4], b'Transfer-Encoding: chunked')
        self.assertTrue(('Connection', 'close') in inst.response_headers)
        self.assertEqual(inst.close_on_finish, True)

    def test_build_response_header_v11_connection_keepalive_by_client(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.request.headers['CONNECTION'] = 'keep-alive'
        inst.version = '1.1'
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.1 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')
        self.assertEqual(lines[4], b'Transfer-Encoding: chunked')
        self.assertTrue(('Connection', 'close') in inst.response_headers)
        self.assertEqual(inst.close_on_finish, True)

    def test_build_response_header_v11_200_no_content_length(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.1'
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.1 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')
        self.assertEqual(lines[4], b'Transfer-Encoding: chunked')
        self.assertEqual(inst.close_on_finish, True)
        self.assertTrue(('Connection', 'close') in inst.response_headers)

    def test_build_response_header_via_added(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.0'
        inst.response_headers = [('Server', 'abc')]
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], b'HTTP/1.0 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: abc')
        self.assertEqual(lines[4], b'Via: waitress')

    def test_build_response_header_date_exists(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.0'
        inst.response_headers = [('Date', 'date')]
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], b'HTTP/1.0 200 OK')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')

    def test_build_response_header_preexisting_content_length(self):
        inst = self._makeOne()
        inst.request = DummyParser()
        inst.version = '1.1'
        inst.content_length = 100
        result = inst.build_response_header()
        lines = filter_lines(result)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], b'HTTP/1.1 200 OK')
        self.assertEqual(lines[1], b'Content-Length: 100')
        self.assertTrue(lines[2].startswith(b'Date:'))
        self.assertEqual(lines[3], b'Server: waitress')

    def test_remove_content_length_header(self):
        inst = self._makeOne()
        inst.response_headers = [('Content-Length', '70')]
        inst.remove_content_length_header()
        self.assertEqual(inst.response_headers, [])

    def test_start(self):
        inst = self._makeOne()
        inst.start()
        self.assertTrue(inst.start_time)

    def test_finish_didnt_write_header(self):
        inst = self._makeOne()
        inst.wrote_header = False
        inst.complete = True
        inst.finish()
        self.assertTrue(inst.channel.written)

    def test_finish_wrote_header(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.finish()
        self.assertFalse(inst.channel.written)

    def test_finish_chunked_response(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.chunked_response = True
        inst.finish()
        self.assertEqual(inst.channel.written, b'0\r\n\r\n')

    def test_write_wrote_header(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.complete = True
        inst.content_length = 3
        inst.write(b'abc')
        self.assertEqual(inst.channel.written, b'abc')

    def test_write_header_not_written(self):
        inst = self._makeOne()
        inst.wrote_header = False
        inst.complete = True
        inst.write(b'abc')
        self.assertTrue(inst.channel.written)
        self.assertEqual(inst.wrote_header, True)

    def test_write_start_response_uncalled(self):
        inst = self._makeOne()
        self.assertRaises(RuntimeError, inst.write, b'')

    def test_write_chunked_response(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.chunked_response = True
        inst.complete = True
        inst.write(b'abc')
        self.assertEqual(inst.channel.written, b'3\r\nabc\r\n')

    def test_write_preexisting_content_length(self):
        inst = self._makeOne()
        inst.wrote_header = True
        inst.complete = True
        inst.content_length = 1
        inst.logger = DummyLogger()
        inst.write(b'abc')
        self.assertTrue(inst.channel.written)
        self.assertEqual(inst.logged_write_excess, True)
        self.assertEqual(len(inst.logger.logged), 1)

class TestWSGITask(unittest.TestCase):

    def _makeOne(self, channel=None, request=None):
        if channel is None:
            channel = DummyChannel()
        if request is None:
            request = DummyParser()
        from waitress.task import WSGITask
        return WSGITask(channel, request)

    def test_service(self):
        inst = self._makeOne()
        def execute():
            inst.executed = True
        inst.execute = execute
        inst.complete = True
        inst.service()
        self.assertTrue(inst.start_time)
        self.assertTrue(inst.close_on_finish)
        self.assertTrue(inst.channel.written)
        self.assertEqual(inst.executed, True)

    def test_service_server_raises_socket_error(self):
        import socket
        inst = self._makeOne()
        def execute():
            raise socket.error
        inst.execute = execute
        self.assertRaises(socket.error, inst.service)
        self.assertTrue(inst.start_time)
        self.assertTrue(inst.close_on_finish)
        self.assertFalse(inst.channel.written)

    def test_execute_app_calls_start_response_twice_wo_exc_info(self):
        def app(environ, start_response):
            start_response('200 OK', [])
            start_response('200 OK', [])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_app_calls_start_response_w_exc_info_complete(self):
        def app(environ, start_response):
            start_response('200 OK', [], [ValueError, ValueError(), None])
        inst = self._makeOne()
        inst.complete = True
        inst.channel.server.application = app
        self.assertRaises(ValueError, inst.execute)

    def test_execute_app_calls_start_response_w_exc_info_incomplete(self):
        def app(environ, start_response):
            start_response('200 OK', [], [ValueError, None, None])
            return [b'a']
        inst = self._makeOne()
        inst.complete = False
        inst.channel.server.application = app
        inst.execute()
        self.assertTrue(inst.complete)
        self.assertEqual(inst.status, '200 OK')
        self.assertTrue(inst.channel.written)

    def test_execute_bad_header_key(self):
        def app(environ, start_response):
            start_response('200 OK', [(None, 'a')])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_bad_header_value(self):
        def app(environ, start_response):
            start_response('200 OK', [('a', None)])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_hopbyhop_header(self):
        def app(environ, start_response):
            start_response('200 OK', [('Connection', 'close')])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_preserve_header_value_order(self):
        def app(environ, start_response):
            write = start_response('200 OK', [('C', 'b'), ('A', 'b'), ('A', 'a')])
            write(b'abc')
            return []
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertTrue(b'A: b\r\nA: a\r\nC: b\r\n' in inst.channel.written)

    def test_execute_bad_status_value(self):
        def app(environ, start_response):
            start_response(None, [])
        inst = self._makeOne()
        inst.channel.server.application = app
        self.assertRaises(AssertionError, inst.execute)

    def test_execute_with_content_length_header(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '1')])
            return [b'a']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(inst.content_length, 1)

    def test_execute_app_calls_write(self):
        def app(environ, start_response):
            write = start_response('200 OK', [('Content-Length', '3')])
            write(b'abc')
            return []
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(inst.channel.written[-3:], b'abc')

    def test_execute_app_returns_len1_chunk_without_cl(self):
        def app(environ, start_response):
            start_response('200 OK', [])
            return [b'abc']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(inst.content_length, 3)

    def test_execute_app_returns_empty_chunk_as_first(self):
        def app(environ, start_response):
            start_response('200 OK', [])
            return ['', b'abc']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(inst.content_length, None)

    def test_execute_app_returns_too_many_bytes(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '1')])
            return [b'abc']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.logger = DummyLogger()
        inst.execute()
        self.assertEqual(inst.close_on_finish, True)
        self.assertEqual(len(inst.logger.logged), 1)

    def test_execute_app_returns_too_few_bytes(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '3')])
            return [b'a']
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.logger = DummyLogger()
        inst.execute()
        self.assertEqual(inst.close_on_finish, True)
        self.assertEqual(len(inst.logger.logged), 1)

    def test_execute_app_do_not_warn_on_head(self):
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '3')])
            return [b'']
        inst = self._makeOne()
        inst.request.command = 'HEAD'
        inst.channel.server.application = app
        inst.logger = DummyLogger()
        inst.execute()
        self.assertEqual(inst.close_on_finish, True)
        self.assertEqual(len(inst.logger.logged), 0)

    def test_execute_app_returns_closeable(self):
        class closeable(list):
            def close(self):
                self.closed = True
        foo = closeable([b'abc'])
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '3')])
            return foo
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertEqual(foo.closed, True)

    def test_execute_app_returns_filewrapper_prepare_returns_True(self):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        f = io.BytesIO(b'abc')
        app_iter = ReadOnlyFileBasedBuffer(f, 8192)
        def app(environ, start_response):
            start_response('200 OK', [('Content-Length', '3')])
            return app_iter
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertTrue(inst.channel.written) # header
        self.assertEqual(inst.channel.otherdata, [app_iter])

    def test_execute_app_returns_filewrapper_prepare_returns_True_nocl(self):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        f = io.BytesIO(b'abc')
        app_iter = ReadOnlyFileBasedBuffer(f, 8192)
        def app(environ, start_response):
            start_response('200 OK', [])
            return app_iter
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.execute()
        self.assertTrue(inst.channel.written) # header
        self.assertEqual(inst.channel.otherdata, [app_iter])
        self.assertEqual(inst.content_length, 3)

    def test_execute_app_returns_filewrapper_prepare_returns_True_badcl(self):
        from waitress.buffers import ReadOnlyFileBasedBuffer
        f = io.BytesIO(b'abc')
        app_iter = ReadOnlyFileBasedBuffer(f, 8192)
        def app(environ, start_response):
            start_response('200 OK', [])
            return app_iter
        inst = self._makeOne()
        inst.channel.server.application = app
        inst.content_length = 10
        inst.response_headers = [('Content-Length', '10')]
        inst.execute()
        self.assertTrue(inst.channel.written) # header
        self.assertEqual(inst.channel.otherdata, [app_iter])
        self.assertEqual(inst.content_length, 3)
        self.assertEqual(dict(inst.response_headers)['Content-Length'], '3')

    def test_get_environment_already_cached(self):
        inst = self._makeOne()
        inst.environ = object()
        self.assertEqual(inst.get_environment(), inst.environ)

    def test_get_environment_path_startswith_more_than_one_slash(self):
        inst = self._makeOne()
        request = DummyParser()
        request.path = '///abc'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '/abc')

    def test_get_environment_path_empty(self):
        inst = self._makeOne()
        request = DummyParser()
        request.path = ''
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '')

    def test_get_environment_no_query(self):
        inst = self._makeOne()
        request = DummyParser()
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['QUERY_STRING'], '')

    def test_get_environment_with_query(self):
        inst = self._makeOne()
        request = DummyParser()
        request.query = 'abc'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['QUERY_STRING'], 'abc')

    def test_get_environ_with_url_prefix_miss(self):
        inst = self._makeOne()
        inst.channel.server.adj.url_prefix = '/foo'
        request = DummyParser()
        request.path = '/bar'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '/bar')
        self.assertEqual(environ['SCRIPT_NAME'], '/foo')

    def test_get_environ_with_url_prefix_hit(self):
        inst = self._makeOne()
        inst.channel.server.adj.url_prefix = '/foo'
        request = DummyParser()
        request.path = '/foo/fuz'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '/fuz')
        self.assertEqual(environ['SCRIPT_NAME'], '/foo')

    def test_get_environ_with_url_prefix_empty_path(self):
        inst = self._makeOne()
        inst.channel.server.adj.url_prefix = '/foo'
        request = DummyParser()
        request.path = '/foo'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['PATH_INFO'], '')
        self.assertEqual(environ['SCRIPT_NAME'], '/foo')

    def test_get_environment_values(self):
        import sys
        inst = self._makeOne()
        request = DummyParser()
        request.headers = {
            'CONTENT_TYPE': 'abc',
            'CONTENT_LENGTH': '10',
            'X_FOO': 'BAR',
            'CONNECTION': 'close',
        }
        request.query = 'abc'
        inst.request = request
        environ = inst.get_environment()

        # nail the keys of environ
        self.assertEqual(sorted(environ.keys()), [
            'CONTENT_LENGTH', 'CONTENT_TYPE', 'HTTP_CONNECTION', 'HTTP_X_FOO',
            'PATH_INFO', 'QUERY_STRING', 'REMOTE_ADDR', 'REQUEST_METHOD',
            'SCRIPT_NAME', 'SERVER_NAME', 'SERVER_PORT', 'SERVER_PROTOCOL',
            'SERVER_SOFTWARE', 'wsgi.errors', 'wsgi.file_wrapper', 'wsgi.input',
            'wsgi.multiprocess', 'wsgi.multithread', 'wsgi.run_once',
            'wsgi.url_scheme', 'wsgi.version'])

        self.assertEqual(environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(environ['SERVER_PORT'], '80')
        self.assertEqual(environ['SERVER_NAME'], 'localhost')
        self.assertEqual(environ['SERVER_SOFTWARE'], 'waitress')
        self.assertEqual(environ['SERVER_PROTOCOL'], 'HTTP/1.0')
        self.assertEqual(environ['SCRIPT_NAME'], '')
        self.assertEqual(environ['HTTP_CONNECTION'], 'close')
        self.assertEqual(environ['PATH_INFO'], '/')
        self.assertEqual(environ['QUERY_STRING'], 'abc')
        self.assertEqual(environ['REMOTE_ADDR'], '127.0.0.1')
        self.assertEqual(environ['CONTENT_TYPE'], 'abc')
        self.assertEqual(environ['CONTENT_LENGTH'], '10')
        self.assertEqual(environ['HTTP_X_FOO'], 'BAR')
        self.assertEqual(environ['wsgi.version'], (1, 0))
        self.assertEqual(environ['wsgi.url_scheme'], 'http')
        self.assertEqual(environ['wsgi.errors'], sys.stderr)
        self.assertEqual(environ['wsgi.multithread'], True)
        self.assertEqual(environ['wsgi.multiprocess'], False)
        self.assertEqual(environ['wsgi.run_once'], False)
        self.assertEqual(environ['wsgi.input'], 'stream')
        self.assertEqual(inst.environ, environ)

    def test_get_environment_values_w_scheme_override_untrusted(self):
        inst = self._makeOne()
        request = DummyParser()
        request.headers = {
            'CONTENT_TYPE': 'abc',
            'CONTENT_LENGTH': '10',
            'X_FOO': 'BAR',
            'X_FORWARDED_PROTO': 'https',
            'CONNECTION': 'close',
        }
        request.query = 'abc'
        inst.request = request
        environ = inst.get_environment()
        self.assertEqual(environ['wsgi.url_scheme'], 'http')

    def test_get_environment_values_w_scheme_override_trusted(self):
        import sys
        inst = self._makeOne()
        inst.channel.addr = ['192.168.1.1']
        inst.channel.server.adj.trusted_proxy = '192.168.1.1'
        request = DummyParser()
        request.headers = {
            'CONTENT_TYPE': 'abc',
            'CONTENT_LENGTH': '10',
            'X_FOO': 'BAR',
            'X_FORWARDED_PROTO': 'https',
            'CONNECTION': 'close',
        }
        request.query = 'abc'
        inst.request = request
        environ = inst.get_environment()

        # nail the keys of environ
        self.assertEqual(sorted(environ.keys()), [
            'CONTENT_LENGTH', 'CONTENT_TYPE', 'HTTP_CONNECTION', 'HTTP_X_FOO',
            'PATH_INFO', 'QUERY_STRING', 'REMOTE_ADDR', 'REQUEST_METHOD',
            'SCRIPT_NAME', 'SERVER_NAME', 'SERVER_PORT', 'SERVER_PROTOCOL',
            'SERVER_SOFTWARE', 'wsgi.errors', 'wsgi.file_wrapper', 'wsgi.input',
            'wsgi.multiprocess', 'wsgi.multithread', 'wsgi.run_once',
            'wsgi.url_scheme', 'wsgi.version'])

        self.assertEqual(environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(environ['SERVER_PORT'], '80')
        self.assertEqual(environ['SERVER_NAME'], 'localhost')
        self.assertEqual(environ['SERVER_SOFTWARE'], 'waitress')
        self.assertEqual(environ['SERVER_PROTOCOL'], 'HTTP/1.0')
        self.assertEqual(environ['SCRIPT_NAME'], '')
        self.assertEqual(environ['HTTP_CONNECTION'], 'close')
        self.assertEqual(environ['PATH_INFO'], '/')
        self.assertEqual(environ['QUERY_STRING'], 'abc')
        self.assertEqual(environ['REMOTE_ADDR'], '192.168.1.1')
        self.assertEqual(environ['CONTENT_TYPE'], 'abc')
        self.assertEqual(environ['CONTENT_LENGTH'], '10')
        self.assertEqual(environ['HTTP_X_FOO'], 'BAR')
        self.assertEqual(environ['wsgi.version'], (1, 0))
        self.assertEqual(environ['wsgi.url_scheme'], 'https')
        self.assertEqual(environ['wsgi.errors'], sys.stderr)
        self.assertEqual(environ['wsgi.multithread'], True)
        self.assertEqual(environ['wsgi.multiprocess'], False)
        self.assertEqual(environ['wsgi.run_once'], False)
        self.assertEqual(environ['wsgi.input'], 'stream')
        self.assertEqual(inst.environ, environ)

    def test_get_environment_values_w_bogus_scheme_override(self):
        inst = self._makeOne()
        inst.channel.addr = ['192.168.1.1']
        inst.channel.server.adj.trusted_proxy = '192.168.1.1'
        request = DummyParser()
        request.headers = {
            'CONTENT_TYPE': 'abc',
            'CONTENT_LENGTH': '10',
            'X_FOO': 'BAR',
            'X_FORWARDED_PROTO': 'http://p02n3e.com?url=http',
            'CONNECTION': 'close',
        }
        request.query = 'abc'
        inst.request = request
        self.assertRaises(ValueError, inst.get_environment)

class TestErrorTask(unittest.TestCase):

    def _makeOne(self, channel=None, request=None):
        if channel is None:
            channel = DummyChannel()
        if request is None:
            request = DummyParser()
            request.error = DummyError()
        from waitress.task import ErrorTask
        return ErrorTask(channel, request)

    def test_execute_http_10(self):
        inst = self._makeOne()
        inst.execute()
        lines = filter_lines(inst.channel.written)
        self.assertEqual(len(lines), 9)
        self.assertEqual(lines[0], b'HTTP/1.0 432 Too Ugly')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertEqual(lines[2], b'Content-Length: 43')
        self.assertEqual(lines[3], b'Content-Type: text/plain')
        self.assertTrue(lines[4])
        self.assertEqual(lines[5], b'Server: waitress')
        self.assertEqual(lines[6], b'Too Ugly')
        self.assertEqual(lines[7], b'body')
        self.assertEqual(lines[8], b'(generated by waitress)')

    def test_execute_http_11(self):
        inst = self._makeOne()
        inst.version = '1.1'
        inst.execute()
        lines = filter_lines(inst.channel.written)
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0], b'HTTP/1.1 432 Too Ugly')
        self.assertEqual(lines[1], b'Content-Length: 43')
        self.assertEqual(lines[2], b'Content-Type: text/plain')
        self.assertTrue(lines[3])
        self.assertEqual(lines[4], b'Server: waitress')
        self.assertEqual(lines[5], b'Too Ugly')
        self.assertEqual(lines[6], b'body')
        self.assertEqual(lines[7], b'(generated by waitress)')

    def test_execute_http_11_close(self):
        inst = self._makeOne()
        inst.version = '1.1'
        inst.request.headers['CONNECTION'] = 'close'
        inst.execute()
        lines = filter_lines(inst.channel.written)
        self.assertEqual(len(lines), 9)
        self.assertEqual(lines[0], b'HTTP/1.1 432 Too Ugly')
        self.assertEqual(lines[1], b'Connection: close')
        self.assertEqual(lines[2], b'Content-Length: 43')
        self.assertEqual(lines[3], b'Content-Type: text/plain')
        self.assertTrue(lines[4])
        self.assertEqual(lines[5], b'Server: waitress')
        self.assertEqual(lines[6], b'Too Ugly')
        self.assertEqual(lines[7], b'body')
        self.assertEqual(lines[8], b'(generated by waitress)')

    def test_execute_http_11_keep(self):
        inst = self._makeOne()
        inst.version = '1.1'
        inst.request.headers['CONNECTION'] = 'keep-alive'
        inst.execute()
        lines = filter_lines(inst.channel.written)
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[0], b'HTTP/1.1 432 Too Ugly')
        self.assertEqual(lines[1], b'Content-Length: 43')
        self.assertEqual(lines[2], b'Content-Type: text/plain')
        self.assertTrue(lines[3])
        self.assertEqual(lines[4], b'Server: waitress')
        self.assertEqual(lines[5], b'Too Ugly')
        self.assertEqual(lines[6], b'body')
        self.assertEqual(lines[7], b'(generated by waitress)')


class DummyError(object):
    code = '432'
    reason = 'Too Ugly'
    body = 'body'

class DummyTask(object):
    serviced = False
    deferred = False
    cancelled = False

    def __init__(self, toraise=None):
        self.toraise = toraise

    def service(self):
        self.serviced = True
        if self.toraise:
            raise self.toraise

    def defer(self):
        self.deferred = True
        if self.toraise:
            raise self.toraise

    def cancel(self):
        self.cancelled = True

class DummyAdj(object):
    log_socket_errors = True
    ident = 'waitress'
    host = '127.0.0.1'
    port = 80
    url_prefix = ''
    trusted_proxy = None

class DummyServer(object):
    server_name = 'localhost'
    effective_port = 80

    def __init__(self):
        self.adj = DummyAdj()

class DummyChannel(object):
    closed_when_done = False
    adj = DummyAdj()
    creation_time = 0
    addr = ['127.0.0.1']

    def __init__(self, server=None):
        if server is None:
            server = DummyServer()
        self.server = server
        self.written = b''
        self.otherdata = []

    def write_soon(self, data):
        if isinstance(data, bytes):
            self.written += data
        else:
            self.otherdata.append(data)
        return len(data)

class DummyParser(object):
    version = '1.0'
    command = 'GET'
    path = '/'
    query = ''
    url_scheme = 'http'
    expect_continue = False
    headers_finished = False

    def __init__(self):
        self.headers = {}

    def get_body_stream(self):
        return 'stream'

def filter_lines(s):
    return list(filter(None, s.split(b'\r\n')))

class DummyLogger(object):

    def __init__(self):
        self.logged = []

    def warning(self, msg):
        self.logged.append(msg)

    def exception(self, msg):
        self.logged.append(msg)

########NEW FILE########
__FILENAME__ = test_trigger
import unittest
import os
import sys

if not sys.platform.startswith("win"):

    class Test_trigger(unittest.TestCase):

        def _makeOne(self, map):
            from waitress.trigger import trigger
            return trigger(map)

        def test__close(self):
            map = {}
            inst = self._makeOne(map)
            fd = os.open(os.path.abspath(__file__), os.O_RDONLY)
            inst._fds = (fd,)
            inst.close()
            self.assertRaises(OSError, os.read, fd, 1)

        def test__physical_pull(self):
            map = {}
            inst = self._makeOne(map)
            inst._physical_pull()
            r = os.read(inst._fds[0], 1)
            self.assertEqual(r, b'x')

        def test_readable(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.readable(), True)

        def test_writable(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.writable(), False)

        def test_handle_connect(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.handle_connect(), None)

        def test_close(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.close(), None)
            self.assertEqual(inst._closed, True)

        def test_handle_close(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.handle_close(), None)
            self.assertEqual(inst._closed, True)

        def test_pull_trigger_nothunk(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.pull_trigger(), None)
            r = os.read(inst._fds[0], 1)
            self.assertEqual(r, b'x')

        def test_pull_trigger_thunk(self):
            map = {}
            inst = self._makeOne(map)
            self.assertEqual(inst.pull_trigger(True), None)
            self.assertEqual(len(inst.thunks), 1)
            r = os.read(inst._fds[0], 1)
            self.assertEqual(r, b'x')

        def test_handle_read_socket_error(self):
            map = {}
            inst = self._makeOne(map)
            result = inst.handle_read()
            self.assertEqual(result, None)

        def test_handle_read_no_socket_error(self):
            map = {}
            inst = self._makeOne(map)
            inst.pull_trigger()
            result = inst.handle_read()
            self.assertEqual(result, None)

        def test_handle_read_thunk(self):
            map = {}
            inst = self._makeOne(map)
            inst.pull_trigger()
            L = []
            inst.thunks = [lambda: L.append(True)]
            result = inst.handle_read()
            self.assertEqual(result, None)
            self.assertEqual(L, [True])
            self.assertEqual(inst.thunks, [])

        def test_handle_read_thunk_error(self):
            map = {}
            inst = self._makeOne(map)
            def errorthunk():
                raise ValueError
            inst.pull_trigger(errorthunk)
            L = []
            inst.log_info = lambda *arg: L.append(arg)
            result = inst.handle_read()
            self.assertEqual(result, None)
            self.assertEqual(len(L), 1)
            self.assertEqual(inst.thunks, [])

########NEW FILE########
__FILENAME__ = test_utilities
##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

import unittest

class Test_parse_http_date(unittest.TestCase):

    def _callFUT(self, v):
        from waitress.utilities import parse_http_date
        return parse_http_date(v)

    def test_rfc850(self):
        val = 'Tuesday, 08-Feb-94 14:15:29 GMT'
        result = self._callFUT(val)
        self.assertEqual(result, 760716929)

    def test_rfc822(self):
        val = 'Sun, 08 Feb 1994 14:15:29 GMT'
        result = self._callFUT(val)
        self.assertEqual(result, 760716929)

    def test_neither(self):
        val = ''
        result = self._callFUT(val)
        self.assertEqual(result, 0)

class Test_build_http_date(unittest.TestCase):

    def test_rountdrip(self):
        from waitress.utilities import build_http_date, parse_http_date
        from time import time
        t = int(time())
        self.assertEqual(t, parse_http_date(build_http_date(t)))

class Test_unpack_rfc850(unittest.TestCase):

    def _callFUT(self, val):
        from waitress.utilities import unpack_rfc850, rfc850_reg
        return unpack_rfc850(rfc850_reg.match(val.lower()))

    def test_it(self):
        val = 'Tuesday, 08-Feb-94 14:15:29 GMT'
        result = self._callFUT(val)
        self.assertEqual(result, (1994, 2, 8, 14, 15, 29, 0, 0, 0))

class Test_unpack_rfc_822(unittest.TestCase):

    def _callFUT(self, val):
        from waitress.utilities import unpack_rfc822, rfc822_reg
        return unpack_rfc822(rfc822_reg.match(val.lower()))

    def test_it(self):
        val = 'Sun, 08 Feb 1994 14:15:29 GMT'
        result = self._callFUT(val)
        self.assertEqual(result, (1994, 2, 8, 14, 15, 29, 0, 0, 0))

class Test_find_double_newline(unittest.TestCase):

    def _callFUT(self, val):
        from waitress.utilities import find_double_newline
        return find_double_newline(val)

    def test_empty(self):
        self.assertEqual(self._callFUT(b''), -1)

    def test_one_linefeed(self):
        self.assertEqual(self._callFUT(b'\n'), -1)

    def test_double_linefeed(self):
        self.assertEqual(self._callFUT(b'\n\n'), 2)

    def test_one_crlf(self):
        self.assertEqual(self._callFUT(b'\r\n'), -1)

    def test_double_crfl(self):
        self.assertEqual(self._callFUT(b'\r\n\r\n'), 4)

    def test_mixed(self):
        self.assertEqual(self._callFUT(b'\n\n00\r\n\r\n'), 2)

class Test_logging_dispatcher(unittest.TestCase):

    def _makeOne(self):
        from waitress.utilities import logging_dispatcher
        return logging_dispatcher(map={})

    def test_log_info(self):
        import logging
        inst = self._makeOne()
        logger = DummyLogger()
        inst.logger = logger
        inst.log_info('message', 'warning')
        self.assertEqual(logger.severity, logging.WARN)
        self.assertEqual(logger.message, 'message')

class TestBadRequest(unittest.TestCase):

    def _makeOne(self):
        from waitress.utilities import BadRequest
        return BadRequest(1)

    def test_it(self):
        inst = self._makeOne()
        self.assertEqual(inst.body, 1)

class DummyLogger(object):

    def log(self, severity, message):
        self.severity = severity
        self.message = message

########NEW FILE########
__FILENAME__ = trigger
##############################################################################
#
# Copyright (c) 2001-2005 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################

import asyncore
import os
import socket
import errno

from waitress.compat import thread

# Wake up a call to select() running in the main thread.
#
# This is useful in a context where you are using Medusa's I/O
# subsystem to deliver data, but the data is generated by another
# thread.  Normally, if Medusa is in the middle of a call to
# select(), new output data generated by another thread will have
# to sit until the call to select() either times out or returns.
# If the trigger is 'pulled' by another thread, it should immediately
# generate a READ event on the trigger object, which will force the
# select() invocation to return.
#
# A common use for this facility: letting Medusa manage I/O for a
# large number of connections; but routing each request through a
# thread chosen from a fixed-size thread pool.  When a thread is
# acquired, a transaction is performed, but output data is
# accumulated into buffers that will be emptied more efficiently
# by Medusa. [picture a server that can process database queries
# rapidly, but doesn't want to tie up threads waiting to send data
# to low-bandwidth connections]
#
# The other major feature provided by this class is the ability to
# move work back into the main thread: if you call pull_trigger()
# with a thunk argument, when select() wakes up and receives the
# event it will call your thunk from within that thread.  The main
# purpose of this is to remove the need to wrap thread locks around
# Medusa's data structures, which normally do not need them.  [To see
# why this is true, imagine this scenario: A thread tries to push some
# new data onto a channel's outgoing data queue at the same time that
# the main thread is trying to remove some]

class _triggerbase(object):
    """OS-independent base class for OS-dependent trigger class."""

    kind = None # subclass must set to "pipe" or "loopback"; used by repr

    def __init__(self):
        self._closed = False

        # `lock` protects the `thunks` list from being traversed and
        # appended to simultaneously.
        self.lock = thread.allocate_lock()

        # List of no-argument callbacks to invoke when the trigger is
        # pulled.  These run in the thread running the asyncore mainloop,
        # regardless of which thread pulls the trigger.
        self.thunks = []

    def readable(self):
        return True

    def writable(self):
        return False

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    # Override the asyncore close() method, because it doesn't know about
    # (so can't close) all the gimmicks we have open.  Subclass must
    # supply a _close() method to do platform-specific closing work.  _close()
    # will be called iff we're not already closed.
    def close(self):
        if not self._closed:
            self._closed = True
            self.del_channel()
            self._close() # subclass does OS-specific stuff

    def pull_trigger(self, thunk=None):
        if thunk:
            self.lock.acquire()
            try:
                self.thunks.append(thunk)
            finally:
                self.lock.release()
        self._physical_pull()

    def handle_read(self):
        try:
            self.recv(8192)
        except (OSError, socket.error):
            return
        self.lock.acquire()
        try:
            for thunk in self.thunks:
                try:
                    thunk()
                except:
                    nil, t, v, tbinfo = asyncore.compact_traceback()
                    self.log_info(
                        'exception in trigger thunk: (%s:%s %s)' %
                        (t, v, tbinfo))
            self.thunks = []
        finally:
            self.lock.release()

if os.name == 'posix':

    class trigger(_triggerbase, asyncore.file_dispatcher):
        kind = "pipe"

        def __init__(self, map):
            _triggerbase.__init__(self)
            r, self.trigger = self._fds = os.pipe()
            asyncore.file_dispatcher.__init__(self, r, map=map)

        def _close(self):
            for fd in self._fds:
                os.close(fd)
            self._fds = []

        def _physical_pull(self):
            os.write(self.trigger, b'x')

else: # pragma: no cover
    # Windows version; uses just sockets, because a pipe isn't select'able
    # on Windows.

    class trigger(_triggerbase, asyncore.dispatcher):
        kind = "loopback"

        def __init__(self, map):
            _triggerbase.__init__(self)

            # Get a pair of connected sockets.  The trigger is the 'w'
            # end of the pair, which is connected to 'r'.  'r' is put
            # in the asyncore socket map.  "pulling the trigger" then
            # means writing something on w, which will wake up r.

            w = socket.socket()
            # Disable buffering -- pulling the trigger sends 1 byte,
            # and we want that sent immediately, to wake up asyncore's
            # select() ASAP.
            w.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            count = 0
            while True:
                count += 1
                # Bind to a local port; for efficiency, let the OS pick
                # a free port for us.
                # Unfortunately, stress tests showed that we may not
                # be able to connect to that port ("Address already in
                # use") despite that the OS picked it.  This appears
                # to be a race bug in the Windows socket implementation.
                # So we loop until a connect() succeeds (almost always
                # on the first try).  See the long thread at
                # http://mail.zope.org/pipermail/zope/2005-July/160433.html
                # for hideous details.
                a = socket.socket()
                a.bind(("127.0.0.1", 0))
                connect_address = a.getsockname() # assigned (host, port) pair
                a.listen(1)
                try:
                    w.connect(connect_address)
                    break # success
                except socket.error as detail:
                    if detail[0] != errno.WSAEADDRINUSE:
                        # "Address already in use" is the only error
                        # I've seen on two WinXP Pro SP2 boxes, under
                        # Pythons 2.3.5 and 2.4.1.
                        raise
                    # (10048, 'Address already in use')
                    # assert count <= 2 # never triggered in Tim's tests
                    if count >= 10: # I've never seen it go above 2
                        a.close()
                        w.close()
                        raise RuntimeError("Cannot bind trigger!")
                    # Close `a` and try again.  Note:  I originally put a short
                    # sleep() here, but it didn't appear to help or hurt.
                    a.close()

            r, addr = a.accept() # r becomes asyncore's (self.)socket
            a.close()
            self.trigger = w
            asyncore.dispatcher.__init__(self, r, map=map)

        def _close(self):
            # self.socket is r, and self.trigger is w, from __init__
            self.socket.close()
            self.trigger.close()

        def _physical_pull(self):
            self.trigger.send(b'x')

########NEW FILE########
__FILENAME__ = utilities
##############################################################################
#
# Copyright (c) 2004 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Utility functions
"""

import asyncore
import errno
import logging
import os
import re
import stat
import time
import calendar

logger = logging.getLogger('waitress')

def find_double_newline(s):
    """Returns the position just after a double newline in the given string."""
    pos1 = s.find(b'\n\r\n') # One kind of double newline
    if pos1 >= 0:
        pos1 += 3
    pos2 = s.find(b'\n\n')   # Another kind of double newline
    if pos2 >= 0:
        pos2 += 2

    if pos1 >= 0:
        if pos2 >= 0:
            return min(pos1, pos2)
        else:
            return pos1
    else:
        return pos2

def concat(*args):
    return ''.join(args)

def join(seq, field=' '):
    return field.join(seq)

def group(s):
    return '(' + s + ')'

short_days = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
long_days = ['sunday', 'monday', 'tuesday', 'wednesday',
             'thursday', 'friday', 'saturday']

short_day_reg = group(join(short_days, '|'))
long_day_reg = group(join(long_days, '|'))

daymap = {}
for i in range(7):
    daymap[short_days[i]] = i
    daymap[long_days[i]] = i

hms_reg = join(3 * [group('[0-9][0-9]')], ':')

months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul',
          'aug', 'sep', 'oct', 'nov', 'dec']

monmap = {}
for i in range(12):
    monmap[months[i]] = i + 1

months_reg = group(join(months, '|'))

# From draft-ietf-http-v11-spec-07.txt/3.3.1
#       Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
#       Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
#       Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format

# rfc822 format
rfc822_date = join(
    [concat(short_day_reg, ','),            # day
     group('[0-9][0-9]?'),                  # date
     months_reg,                            # month
     group('[0-9]+'),                       # year
     hms_reg,                               # hour minute second
     'gmt'
     ],
    ' '
)

rfc822_reg = re.compile(rfc822_date)

def unpack_rfc822(m):
    g = m.group
    return (
        int(g(4)),             # year
        monmap[g(3)],          # month
        int(g(2)),             # day
        int(g(5)),             # hour
        int(g(6)),             # minute
        int(g(7)),             # second
        0,
        0,
        0,
    )

# rfc850 format
rfc850_date = join(
    [concat(long_day_reg, ','),
     join(
         [group('[0-9][0-9]?'),
          months_reg,
          group('[0-9]+')
          ],
         '-'
     ),
     hms_reg,
     'gmt'
     ],
    ' '
)

rfc850_reg = re.compile(rfc850_date)
# they actually unpack the same way
def unpack_rfc850(m):
    g = m.group
    yr = g(4)
    if len(yr) == 2:
        yr = '19' + yr
    return (
        int(yr),             # year
        monmap[g(3)],        # month
        int(g(2)),           # day
        int(g(5)),           # hour
        int(g(6)),           # minute
        int(g(7)),           # second
        0,
        0,
        0
    )

# parsdate.parsedate - ~700/sec.
# parse_http_date    - ~1333/sec.

weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
monthname = [None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def build_http_date(when):
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(when)
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        weekdayname[wd],
        day, monthname[month], year,
        hh, mm, ss)

def parse_http_date(d):
    d = d.lower()
    m = rfc850_reg.match(d)
    if m and m.end() == len(d):
        retval = int(calendar.timegm(unpack_rfc850(m)))
    else:
        m = rfc822_reg.match(d)
        if m and m.end() == len(d):
            retval = int(calendar.timegm(unpack_rfc822(m)))
        else:
            return 0
    return retval

class logging_dispatcher(asyncore.dispatcher):
    logger = logger

    def log_info(self, message, type='info'):
        severity = {
            'info': logging.INFO,
            'warning': logging.WARN,
            'error': logging.ERROR,
        }
        self.logger.log(severity.get(type, logging.INFO), message)

def cleanup_unix_socket(path):
    try:
        st = os.stat(path)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise # pragma: no cover
    else:
        if stat.S_ISSOCK(st.st_mode):
            try:
                os.remove(path)
            except OSError: # pragma: no cover
                # avoid race condition error during tests
                pass

class Error(object):

    def __init__(self, body):
        self.body = body

class BadRequest(Error):
    code = 400
    reason = 'Bad Request'

class RequestHeaderFieldsTooLarge(BadRequest):
    code = 431
    reason = 'Request Header Fields Too Large'

class RequestEntityTooLarge(BadRequest):
    code = 413
    reason = 'Request Entity Too Large'

class InternalServerError(Error):
    code = 500
    reason = 'Internal Server Error'

########NEW FILE########
