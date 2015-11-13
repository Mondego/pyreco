__FILENAME__ = abstraction
"""
abstraction magics

let's you turn a cell into a function

In [1]: plot(x, f(y))
   ...: xlabel('x')
   ...: ylabel('y')

In [2]: %functionize 1
"""
from IPython.utils.text import indent

def parse_ranges(s):
    blocks = s.split(',')
    ranges = []
    for block in blocks:
        if '-' in block:
            start, stop = [ int(b) for b in block.split('-') ]
            stop = stop + 1 # be inclusive?
        else:
            start = int(block)
            stop = start + 1
        ranges.append((start, stop))
    return ranges

def functionize(line):
    shell = get_ipython()
    splits = line.split(' ', 1)
    range_str = splits[0]
    args = splits[1] if len(splits) > 1 else ''
    
    ranges = parse_ranges(range_str)
    get_range = shell.history_manager.get_range
    
    blocks = ["def cell_function(%s):" % args]
    for start, stop in ranges:
        cursor = get_range(0, start, stop)
        for session_id, cell_id, code in cursor:
            blocks.append(indent(code))
    
    code = '\n'.join(blocks)
    shell.set_next_input(code)


def load_ipython_extension(ip):
    ip.magics_manager.register_function(functionize)
########NEW FILE########
__FILENAME__ = autosave
"""Extension for managing periodic autosave of IPython notebooks

THIS EXTENSION IS OBSOLETE, IPYTHON 1.0 SUPPORTS AUTOSAVE

Usage:

%load_ext autosave

# autosave every 30 seconds:
%autosave 30

# disable autosave:
%autosave 0

# invoke save from Python:
%savenb

"""

from IPython.core.magic import magics_class, line_magic, Magics
from IPython.display import Javascript, display

_autosave_js_t = """

// clear previous interval, if there was one
if (IPython.autosave_extension_interval) {{
    clearInterval(IPython.autosave_extension_interval);
    IPython.autosave_extension_interval = null;
}}

// set new interval
if ({0}) {{
    console.log("scheduling autosave every {0} ms");
    IPython.notebook.save_notebook();
    IPython.autosave_extension_interval = setInterval(function() {{
        console.log("autosave");
        IPython.notebook.save_notebook();
    }}, {0});
}} else {{
    console.log("canceling autosave");
}}
"""

@magics_class
class AutoSaveMagics(Magics):
    
    interval = 60
    enabled = False
    
    @staticmethod
    def autosave_js(interval):
        if interval:
            print("autosaving every %is" % interval)
        else:
            print("autosave disabled")
        display(Javascript(_autosave_js_t.format(1000 * interval)))
    
    @line_magic
    def autosave(self, line):
        """Schedule notebook autosave
        
        Usage:
        
            %autosave [interval]
        
        If `interval` is given, IPython will autosave the notebook every `interval` seconds.
        If `interval` is 0, autosave is disabled.
        
        If no interval is specified, autosave is toggled.
        """
        line = line.strip()
        if not line:
            # empty line, toggle
            self.enabled = bool(1 - self.enabled)
        else:
            interval = int(line)
            if interval:
                self.enabled = True
                self.interval = interval
            else:
                self.enabled = False
        
        self.autosave_js(self.enabled * self.interval)
    
    @line_magic
    def savenb(self, line):
        """save the current notebook
        
        This magic invokes the same javascript as the 'Save' button in the notebook UI.
        """
        display(Javascript("IPython.notebook.save_notebook();"))

def load_ipython_extension(ip):
    """Load the extension in IPython."""
    if "autosave" in ip.magics_manager.magics['line']:
        print ("IPython 1.0 has autosave, this extension is obsolete")
        return
    ip.register_magics(AutoSaveMagics)
    print ("Usage: %autosave [seconds]")


########NEW FILE########
__FILENAME__ = closure
"""
%%closure cell magic for running the cell in a function,
reducing pollution of the namespace

%%forget does the same thing, but explicitly deletes new names,
rather than wrapping the cell in a function.
"""

from IPython.utils.text import indent

def closure(line, cell):
    """run the cell in a function, generating a closure
    
    avoids affecting the user's namespace
    """
    ip = get_ipython()
    func_name = "_closure_magic_f"
    block = '\n'.join([
        "def %s():" % func_name,
        indent(cell),
        "%s()" % func_name
    ])
    ip.run_cell(block)
    ip.user_ns.pop(func_name, None)

def forget(line, cell):
    """cleanup any new variables defined in the cell
    
    avoids UnboundLocals that might show up in %%closure
    
    changes to existing variables are not affected
    """
    ip = get_ipython()
    before = set(ip.user_ns)
    ip.run_cell(cell)
    after = set(ip.user_ns)
    for key in after.difference(before):
        ip.user_ns.pop(key)

def load_ipython_extension(ip):
    mm = ip.magics_manager
    mm.register_function(closure, 'cell')
    mm.register_function(forget, 'cell')

    

########NEW FILE########
__FILENAME__ = disable_autoscroll
"""
Extension for disabling autoscrolling long output, which is super annoying sometimes

Usage:

    %load_ext disable_autoscroll

You can also put the js snippet below in profile_dir/static/js/custom.js
"""

from IPython.display import display, Javascript

disable_js = """
IPython.OutputArea.prototype._should_scroll = function(lines) {
    return false;
}
"""

def load_ipython_extension(ip):
    display(Javascript(disable_js))
    print ("autoscrolling long output is disabled")

########NEW FILE########
__FILENAME__ = editmate
"""
Use TextMate as the editor

THIS EXTENSION IS OBSOLETE

Usage:  %load_ext editmate

Now when you %edit something, it opens in textmate.
This is only necessary because the textmate command-line entrypoint
doesn't support the +L format for linenumbers, it uses `-l L`.

"""

from subprocess import Popen, list2cmdline
from IPython.core.error import TryNext

def edit_in_textmate(self, filename, linenum=None, wait=True):
    cmd = ['mate']
    if wait:
        cmd.append('-w')
    if linenum is not None:
        cmd.extend(['-l', str(linenum)])
    cmd.append(filename)
    
    proc = Popen(list2cmdline(cmd), shell=True)
    if wait and proc.wait() != 0:
        raise TryNext()

def load_ipython_extension(ip):
    try:
        from IPython.lib.editorhooks import mate
    except ImportError:
        ip.set_hook('editor', edit_in_textmate)
    else:
        mate()

########NEW FILE########
__FILENAME__ = gist
"""
This adds a 'share-as-gist' button to the IPython notebook toolbar.

It relies on the `gist` ruby gem, which you can install with `gem install gist`

Loading this Python extension will install its javascript counterparts,
and load them into your custom.js.
"""
from __future__ import print_function

import os
import urllib2

from subprocess import check_output

from IPython.display import display_javascript

load_js = """
// load the gist extension

require(["nbextensions/gistcomm"], function (gist_extension) {
    console.log('gist extension loaded');
    gist_extension.load_extension();
});
"""

def install_nbextension(ip):
    """install the gist javascript extension, and load it in custom.js"""
    
    gist_js = os.path.join(ip.ipython_dir, 'nbextensions', 'gistcomm.js')
    url = "http://rawgithub.com/minrk/ipython_extensions/master/nbextensions/gistcomm.js"
    here = os.path.dirname(__file__)
    if not os.path.exists(gist_js):
        local_gist_js = os.path.join(here, 'gistcomm.js')
        if os.path.exists(local_gist_js):
            print ("installing gistcomm.js from %s" % local_gist_js)
            gist_f = open(local_gist_js)
        else:
            print ("installing gistcomm.js from %s" % url)
            gist_f = urllib2.urlopen(url)
        with open(gist_js, 'w') as f:
            f.write(gist_f.read())
        gist_f.close()
    
    custom_js = os.path.join(ip.profile_dir.location, 'static', 'custom', 'custom.js')
    already_required = False
    if os.path.exists(custom_js):
        with open(custom_js, 'r') as f:
            js = f.read()
        already_required = "nbextensions/gist" in js
    
    if not already_required:
        print("loading gist button into custom.js")
        with open(custom_js, 'a') as f:
            f.write(load_js)
        display_javascript(load_js, raw=True);

class GistExtension(object):
    def __init__(self, comm, msg=None):
        self.comm = comm
        self.comm.on_msg(self.handler)
    
    def handler(self, msg):
        data = msg['content']['data']
        name = data['name']
        root = data['root']
        path = data['path']
        cmd = ['gist']
        if data.get('gist_id'):
            cmd.extend(['-u', data['gist_id']])
        cmd.append(os.path.join(root, path, name))
        try:
            output = check_output(cmd).decode('utf8').strip()
        except Exception as e:
            reply = dict(
                status='failed',
                message=str(e)
            )
        else:
            reply = dict(
                status='ok',
                gist_id = output.replace('https://gist.github.com/', '')
            )
        self.comm.send(reply)

def gist(line=''):
    display_javascript("IPython.gist_button.publish_gist()", raw=True)

def load_ipython_extension(ip):
    install_nbextension(ip)
    ip.magics_manager.register_function(gist)
    comms = getattr(ip, 'comm_manager', None)
    if comms:
        comms.register_target('gist', GistExtension)
    
########NEW FILE########
__FILENAME__ = inactive
# encoding: utf-8
"""
Does *not* execute the cell ("inactive"). Usefull to temporary disable a cell.

Authors:

* Jan Schulz
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from IPython.core.magic import (Magics, magics_class, cell_magic)
from IPython.testing.skipdoctest import skip_doctest
from IPython.core.error import UsageError

@magics_class
class InactiveMagics(Magics):
    """Magic to *not* execute a cell."""

    @skip_doctest
    @cell_magic
    def inactive(self, parameter_s='', cell=None):
        """Does *not* exeutes a cell.
        
        Usage:
          %%inactive
          code...
                
        This magic can be used to mark a cell (temporary) as inactive.
        """
        if cell is None:
            raise UsageError('empty cell, nothing to ignore :-)')
        print("Cell inactive: not executed!")
        

            
def load_ipython_extension(ip):
    ip.register_magics(InactiveMagics)
    print ("'inactive' magic loaded.")
########NEW FILE########
__FILENAME__ = inspector
import inspect
import linecache
import os
import sys

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

from IPython.core.magic import Magics, magics_class, line_magic

from IPython.display import display, HTML

@magics_class
class InspectorMagics(Magics):
    
    def __init__(self, **kwargs):
        super(InspectorMagics, self).__init__(**kwargs)
        self.formatter = HtmlFormatter()
        self.lexer = PythonLexer()
        self.style_name = "default"
    
    @line_magic
    def showsrc(self, line):
        line = line.strip()
        filename, identifier = line.rsplit(None, 1)
        modname, ext = os.path.splitext(filename)
        mod = __import__(modname)
        reload(mod)
        linecache.checkcache()
        obj = getattr(mod, identifier)
        lines, lineno = inspect.getsourcelines(obj)
        self.formatter.linenos = True
        self.formatter.linenostart = lineno
        html = "<span class='inspector-header'>"
        html += "<span class='inspector-filename'>%s: </span>" % filename
        html += "<span class='inspector-lineno'>%i-%i</span>" % (lineno, lineno + len(lines))
        html += "</span>"
        html += highlight(''.join(lines), self.lexer, self.formatter)
        display(HTML(html))
    
    @line_magic
    def showsrcstyle(self, line):
        """publish the CSS for highlighting used in %showsrc
        
        Takes a """
        
        name = line.strip()
        if not name:
            name = "default"
        self.style_name = name
        self.formatter = HtmlFormatter(style=name)
        display(HTML("""<style type='text/css'>
        span.inspector-header {
            font-family: monospace;
            border-bottom: 1px solid #555;
        }
        table.highlighttable, .highlighttable td, .highlighttable tr {
            border: 0px;
        }
        .highlighttable td.linenos {
            border-right: 1px solid #555;
        }
        
        span.inspector-filename {
            text-decoration: italic;
        }
        span.inspector-lineno {
            font-weight: bold;
        }
        %s
        </style>
        """ % self.formatter.get_style_defs()
        ))

def load_ipython_extension(ip):
    ip.register_magics(InspectorMagics)
    ip.magic("showsrcstyle")

########NEW FILE########
__FILENAME__ = msgmagic
"""
Illustration of a configurable Magics class

To use:

%load_ext msgmagic
%msg
%config MsgMagic
%config MsgMagic.message = "Hello, there!"
%msg
"""
from IPython.config import Configurable
from IPython.core.magic import magics_class, Magics, line_magic

from IPython.utils.traitlets import Unicode

@magics_class
class MsgMagic(Magics, Configurable):
    message = Unicode("my message", config=True, help="The message printed by `%msg`")
    
    def __init__(self, shell):
        Configurable.__init__(self, parent=shell)
        Magics.__init__(self, shell)
        # this adds me to the `%config` list:
        shell.configurables.append(self)
    
    @line_magic
    def msg(self, line):
        print(self.message)

def load_ipython_extension(ip):
    ip.magics_manager.register(MsgMagic)

########NEW FILE########
__FILENAME__ = namespaces
"""namespace magic

Shorthand for initializing the user namespace in IPython with my common imports.
"""

from IPython import get_ipython
from IPython.utils.importstring import import_item

namespaces = {
    'numpy' : {
        'np' : 'numpy',
        'numpy' : 'numpy',
    },
    'pandas' : {
        'pandas' : 'pandas',
        'pd' : 'pandas',
    },
    'matplotlib' : {
        'mpl' : 'matplotlib',
        'matplotlib' : 'matplotlib',
        'plt' : 'matplotlib.pyplot',
    },
    'stdlib' : {
        'os' : 'os',
        're' : 're',
        'sys' : 'sys',
        'time' : 'time',
        'pjoin' : 'os.path.join',
        'dt' : 'datetime',
        'datetime' : 'datetime',
    }
}
aliases = {
    'mpl' : 'matplotlib',
    'pd' : 'pandas',
    'np' : 'numpy',
}

def import_ns(d):
    """turn a dict of import strings into a dict of objects"""
    ns = {}
    for key, s in d.items():
        ns[key] = import_item(s)
    return ns

def load_namespace(names):
    """Load one or more predefined namespace
    
    Usage:
    
        %namespace numpy pandas mpl
    """
    ip = get_ipython()
    user_ns = ip.user_ns
    for name in names.split():
        if name in aliases:
            name = aliases[name]
        d = namespaces[name]
        ns = import_ns(d)
        user_ns.update(ns)


def load_ipython_extension(ip):
    ip.magics_manager.register_function(load_namespace, 'line', 'namespace')
########NEW FILE########
__FILENAME__ = nbinput
"""

THIS MODULE IS OBSOLETE WITH IPYTHON 1.0, which supports raw_input

Simple getpass / raw_input workarounds for the IPython notebook using jQueryUI dialogs.
Not awesome, because they don't *return* the response, they store them in a variable,
but it should suffice in a few situations while we implement the real thing.

"""

from IPython.display import display, Javascript

def nbgetpass(prompt="Enter Password", name='passwd'):
    display(Javascript("""
var dialog = $('<div/>').append(
    $('<input/>')
    .attr('id', 'password')
    .attr('name', 'password')
    .attr('type', 'password')
    .attr('value', '')
);
$(document).append(dialog);
dialog.dialog({
    resizable: false,
    modal: true,
    title: "%s",
    closeText: '',
    buttons : {
        "Okay": function () {
            IPython.notebook.kernel.execute(
                "%s = '" + $("input#password").attr('value') + "'"
            );
            $(this).dialog('close');
            dialog.remove();
        },
        "Cancel": function () {
            $(this).dialog('close');
            dialog.remove();
        }
    }
});
""" % (prompt, name)), include=['application/javascript'])
                                  
def nb_raw_input(prompt, name="raw_input_reply"):
    display(Javascript("""
var dialog = $('<div/>').append(
    $('<input/>')
    .attr('id', 'theinput')
    .attr('value', '')
);
$(document).append(dialog);
dialog.dialog({
    resizable: false,
    modal: true,
    title: "%s",
    closeText: '',
    buttons : {
        "Okay": function () {
            IPython.notebook.kernel.execute(
                "%s = '" + $("input#theinput").attr('value') + "'"
            );
            $(this).dialog('close');
            dialog.remove();
        },
        "Cancel": function () {
            $(this).dialog('close');
            dialog.remove();
        }
    }
});
""" % (prompt, name)), include=['application/javascript'])

def load_ipython_extension(ip):
    import IPython
    if int(IPython.__version__.split()[0]) >= 1:
        print ("IPython notebook 1.0 supports plain raw_input, this extension is obsolete")
    
    ip.user_ns['nb_raw_input'] = nb_raw_input
    ip.user_ns['nbgetpass'] = nbgetpass

########NEW FILE########
__FILENAME__ = nbtoc
"""Table-of-contents magic
for IPython Notebook

Just do:

%load_ext nbtoc
%nbtoc

to get a floating table of contents

To redownload the files from GitHub, use %update_nbtoc

All the interesting code, c/o @magican and @nonamenix:
https://gist.github.com/magican/5574556

"""

import io
import os
import urllib2

from IPython.display import display_html, display_javascript

here = os.path.abspath(os.path.dirname(__file__))
nbtoc_js = ""
nbtoc_html = ""

def download(fname, redownload=False):
    """download a file
    
    if redownload=False, the file will not be downloaded if it already exists.
    """
    dest = os.path.join(here, fname)
    if os.path.exists(dest) and not redownload:
        return
    url = 'https://raw.github.com/minrk/ipython_extensions/master/extensions/' + fname
    print("Downloading %s to %s" % (url, dest))
    
    filein  = urllib2.urlopen(url)
    fileout = open(dest, "wb")
    chunk = filein.read(1024)
    while chunk:
        fileout.write(chunk)
        chunk = filein.read(1024)
    filein.close()
    fileout.close()

def load_file(fname, redownload=False):
    """load global variable from a file"""
    download(fname, redownload)
    with io.open(os.path.join(here, fname)) as f:
        globals()[fname.replace('.', '_')] = f.read()

load_file('nbtoc.js')
load_file('nbtoc.html')

def nbtoc(line):
    """add a table of contents to an IPython Notebook"""
    display_html(nbtoc_html, raw=True)
    display_javascript(nbtoc_js, raw=True)

def update_nbtoc(line):
    """download the latest version of the nbtoc extension from GitHub"""
    download('nbtoc.py', True)
    download('nbtoc.js', True)
    download('nbtoc.html', True)
    get_ipython().extension_manager.reload_extension("nbtoc")
    
def load_ipython_extension(ip):
    ip.magics_manager.register_function(nbtoc)
    ip.magics_manager.register_function(update_nbtoc)


########NEW FILE########
__FILENAME__ = pil_display
"""
PNG formatter for various Image objects (PIL, OpenCV, numpy arrays that look like image data)

Usage:  %load_ext pil_display

Now when displayhook gets an image, it will be drawn in the browser.

"""

from io import BytesIO
import os
import tempfile

def pil2imgdata(img, format='PNG'):
    """convert a PIL Image to png bytes"""
    fp = BytesIO()
    img.save(fp, format=format)
    return fp.getvalue()

def array2imgdata_pil(A, format='PNG'):
    """get png data from array via converting to PIL Image"""
    from PIL import Image
    if A.shape[2] == 3:
        mode = 'RGB'
    elif A.shape[2] == 4:
        mode = 'RGBA'
    else:
        mode = 'L'
    img = Image.fromstring(mode, A.shape[:2], A.tostring())
    return pil2imgdata(img, format)

def array2imgdata_fs(A, format='PNG'):
    """get png data via filesystem, using cv2.imwrite
    
    This is much faster than in-memory conversion with PIL on the rPi for some reason.
    """
    import cv2
    fname = os.path.join(tempfile.gettempdir(), "_ipdisplay.%s" % format)
    cv2.imwrite(fname, A)
    with open(fname) as f:
        data = f.read()
    os.unlink(fname)
    return data

def display_image_array(a):
    """If an array looks like RGB[A] data, display it as an image."""
    import numpy as np
    if len(a.shape) != 3 or a.shape[2] not in {3,4} or a.dtype != np.uint8:
        return
    return array2imgdata_pil(a)

def display_cv_image(cvimg):
    """display an OpenCV cvmat object as an image"""
    import numpy as np
    return array2imgdata_fs(np.asarray(cvimg))

def load_ipython_extension(ip):
    png_formatter = ip.display_formatter.formatters['image/png']
    # both, in case of pillow or true PIL
    png_formatter.for_type_by_name('PIL.Image', 'Image', pil2imgdata)
    png_formatter.for_type_by_name('Image', 'Image', pil2imgdata)
    png_formatter.for_type_by_name('cv2.cv', 'iplimage', display_cv_image)
    png_formatter.for_type_by_name('cv2.cv', 'cvmat', display_cv_image)
    png_formatter.for_type_by_name("numpy", "ndarray", display_image_array)

########NEW FILE########
__FILENAME__ = print_page
"""Disable the IPython notebook pager

turn paged output into print statements
"""

from __future__ import print_function
from IPython.core import page

_save_page = None

def load_ipython_extension(ip):
    global _save_page
    if not hasattr(ip, 'kernel'):
        # not in a kernel, nothing to do
        return
    _save_page = page
    page.page = print

def unload_ipython_extension(ip):
    if _save_page is not None:
        page.page = _save_page

########NEW FILE########
__FILENAME__ = retina
"""
Enable Retina (2x) PNG figures with matplotlib

Usage:  %load_ext retina
"""

import struct
from base64 import encodestring
from io import BytesIO

def pngxy(data):
    """read the width/height from a PNG header"""
    ihdr = data.index(b'IHDR')
    # next 8 bytes are width/height
    w4h4 = data[ihdr+4:ihdr+12]
    return struct.unpack('>ii', w4h4)

def print_figure(fig, fmt='png', dpi=None):
    """Convert a figure to svg or png for inline display."""
    import matplotlib
    fc = fig.get_facecolor()
    ec = fig.get_edgecolor()
    bytes_io = BytesIO()
    dpi = dpi or matplotlib.rcParams['savefig.dpi']
    fig.canvas.print_figure(bytes_io, format=fmt, dpi=dpi,
                            bbox_inches='tight',
                            facecolor=fc, edgecolor=ec,
    )
    data = bytes_io.getvalue()
    return data

def png2x(fig):
    """render figure to 2x PNG via HTML"""
    import matplotlib
    if not fig.axes and not fig.lines:
        return
    # double DPI
    dpi = 2 * matplotlib.rcParams['savefig.dpi']
    pngbytes = print_figure(fig, fmt='png', dpi=dpi)
    x,y = pngxy(pngbytes)
    x2x = x // 2
    y2x = y // 2
    png64 = encodestring(pngbytes).decode('ascii')
    return u"<img src='data:image/png;base64,%s' width=%i height=%i/>" % (png64, x2x, y2x)

def enable_retina(ip):
    """enable retina figures"""
    from matplotlib.figure import Figure

    
    # unregister existing formatter(s):
    png_formatter = ip.display_formatter.formatters['image/png']
    png_formatter.type_printers.pop(Figure, None)
    svg_formatter = ip.display_formatter.formatters['image/svg+xml']
    svg_formatter.type_printers.pop(Figure, None)
    
    # register png2x as HTML formatter
    html_formatter = ip.display_formatter.formatters['text/html']
    html_formatter.for_type(Figure, png2x)

def disable_retina(ip):
    from matplotlib.figure import Figure
    from IPython.core.pylabtools import select_figure_format
    select_figure_format(ip, 'png')
    html_formatter = ip.display_formatter.formatters['text/html']
    html_formatter.type_printers.pop(Figure, None)

def load_ipython_extension(ip):
    try:
        enable_retina(ip)
    except Exception as e:
        print "Failed to load retina extension: %s" % e

def unload_ipython_extension(ip):
    disable_retina(ip)


########NEW FILE########
__FILENAME__ = timers
# coding: utf-8
"""Extension for simple stack-based tic/toc timers

Each %tic starts a timer,
each %toc prints the time since the last tic

`%tic label` results in 'label: ' being printed at the corresponding %toc.

Usage:

In [6]: %tic outer
   ...: for i in range(4):
   ...:     %tic
   ...:     time.sleep(2 * random.random())
   ...:     %toc
   ...: %toc
  459 ms
  250 ms
  509 ms
  1.79 s
outer:   3.01 s
"""

import sys
import time

from IPython.core.magic import magics_class, line_magic, cell_magic, Magics
from IPython.core.magics.execution import _format_time

@magics_class
class TimerMagics(Magics):
    
    timers = None
    tics = None
    
    def __init__(self, *args, **kwargs):
        super(TimerMagics, self).__init__(*args, **kwargs)
        self.timers = {}
        self.tics = []
        self.labels = []
    
    @line_magic
    def tic(self, line):
        """Start a timer
        
        Usage:
        
            %tic [label]
        
        """
        label = line.strip() or None
        now = self.time()
        if label in self.timers:
            # %tic on an existing name prints the time,
            # but does not affect the stack
            self.print_time(now - self.timers[label], label)
            return
        
        if label:
            self.timers[label] = now
        self.tics.insert(0, self.time())
        self.labels.insert(0, label)
    
    @line_magic
    def toc(self, line):
        """Stop and print the timer started by the last call to %tic
        
        Usage:
        
            %toc
        
        """
        now = self.time()
        tic = self.tics.pop(0)
        label = self.labels.pop(0)
        self.timers.pop(label, None)
        
        self.print_time(now - tic, label)
    
    def print_time(self, dt, label):
        ts = _format_time(dt)
        msg = "%8s" % ts
        if label:
            msg = "%s: %s" % (label, msg)
        print ('%s%s' % ('  ' * len(self.tics), msg))
    
    @staticmethod
    def time():
        """time.clock seems preferable on Windows"""
        if sys.platform.startswith('win'):
            return time.clock()
        else:
            return time.time()
    
def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(TimerMagics)


########NEW FILE########
__FILENAME__ = writeandexecute
# encoding: utf-8
"""
Writes a cell to a designated *.py file and executes the cell afterwards.

Authors:

* Jan Schulz
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2013  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import os
import io

from IPython.utils import py3compat

from IPython.core.magic import (Magics, magics_class, cell_magic)
from IPython.testing.skipdoctest import skip_doctest
from IPython.core.error import UsageError

@magics_class
class WriteAndExecuteMagics(Magics):
    """Magic to save a cell into a .py file."""

    @skip_doctest
    @cell_magic
    def writeandexecute(self, parameter_s='', cell=None):
        """Writes the content of the cell to a file and then executes the cell.
        
        Usage:
          %%writeandexecute [-d] -i <indentifier> <filename>
          code
          code...
        
        Options:
        -i <indentifier>: surround the code with a line containing the 
        indentifier (needed to replace code)
        
        <filename>: the file where the code should be written to. Can be 
        specified without a extension and can also include a directory 
        (`dir/file`)

        -d: Write some debugging output
        Default: -- (no debugging output)
        
        This magic can be used to write the content of a cell to a .py 
        file and afterwards execute the cell. This can be used as a 
        replacement for the --script parameter to the notebook server.

        Code is replaced on the next execution (using the needed identifier) 
        and other code can be appended by using the same file name.

        Examples
        --------
        %%writeandexecute -i <identifier> <filename>
        print "Hello world"

        This would create a file "filename.py" with the following content
        ```
        # -*- coding: utf-8 -*-


        # -- ==import_time== --
        print "Hello world"

        # -- ==import_time== --
        ```

        Cell content is transformed, so %%magic commands are executed, but 
        `get_ipython()` must be available.
        """
        
        opts,args = self.parse_options(parameter_s,'i:d')
        if cell is None:
            raise UsageError('Nothing to save!')
        if not ('i' in opts) or not opts['i']:
            raise UsageError('Missing indentifier: include "-i=<indentifier>"')
        identifier = opts['i']
        debug = False if not "d" in opts else True
        if not args:
            raise UsageError('Missing filename')
        filename = args
        code_content = self.shell.input_transformer_manager.transform_cell(cell)
        self._save_to_file(filename, identifier, code_content, debug=debug)

        ip = get_ipython()
        ip.run_cell(cell)
        
    def ensure_dir(self, f):
        d = os.path.dirname(f)
        if d and not os.path.exists(d):
            os.makedirs(d)  
            
    def _save_to_file(self, path, identifier, content, debug=False):
            pypath = os.path.splitext(path)[0] + '.py'
            code_identifier = "# -- ==%s== --" % identifier
            new_content = []
            if not os.path.isfile(pypath):
                # The file does not exist, so simple create a new one
                if debug:
                    print("Created new file: %s" % pypath)
                new_content.extend([u'# -*- coding: utf-8 -*-\n\n', code_identifier , content, code_identifier])
            else:
                # If file exist, read in the content and either replace the code or append it
                in_code_block = False
                included_new = False
                lineno = 0
                with io.open(pypath,'r', encoding='utf-8') as f:
                    for line in f:
                        if line[-1] == "\n":
                            line = line[:-1]
                        lineno += 1
                        if line.strip() == code_identifier:
                            if included_new and not in_code_block:
                                # we found a third one -> Error!
                                raise Exception("Found more than two lines with identifiers in file '%s' in line %s. "
                                    "Please fix the file so that the identifier is included exactly two times." % (pypath, lineno))
                            # Now we are either in the codeblock or just outside
                            # Switch the state to either "in our codeblock" or outside again
                            in_code_block = True if not in_code_block else False
                            if not included_new:
                                # The code was not included yet, so add it here...
                                # No need to add a code indentifier to the end as we just add the ending indentifier from the last 
                                # time when the state is switched again.
                                new_content.extend([code_identifier, content])
                                included_new = True
                        # This is something from other code cells, so just include it. All code 
                        # "in_code_block" is replace, so do not include it
                        if not in_code_block:
                            new_content.append(line)
                # And if we didn't include out code yet, lets append it to the end...
                if not included_new:
                    new_content.extend(["\n", code_identifier, content, code_identifier, "\n"])
            
            new_content = unicode(u'\n'.join(new_content))
            
            #Now write the complete code back to the file
            self.ensure_dir(pypath)
            with io.open(pypath,'w', encoding='utf-8') as f:
                if not py3compat.PY3 and not isinstance(new_content, unicode):
                    # this branch is likely only taken for JSON on Python 2
                    new_content = py3compat.str_to_unicode(new_content)
                f.write(new_content)
                if debug:
                    print("Wrote cell to file: %s" % pypath)


            
def load_ipython_extension(ip):
    ip.register_magics(WriteAndExecuteMagics)
    print ("'writeandexecute' magic loaded.")
########NEW FILE########
