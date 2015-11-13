__FILENAME__ = fabfile
from __future__ import print_function
import yaml
import os
import shutil
from distutils.dir_util import copy_tree

IPYTHON_PATH = os.path.join("..", "ipython")

def _recursive_copy(tree, path=''):
    if isinstance(tree, (str, unicode)):
        old_file = os.path.join('notebooks', path, tree)
        new_file = os.path.join(IPYTHON_PATH, 'examples', path, tree)
        if os.path.isfile(new_file):
            shutil.copy(new_file, old_file)
            print('Copied file "{0}" to "{1}".'.format(new_file, old_file))
        elif os.path.isdir(new_file):
            copy_tree(new_file, old_file)
            print('Copied tree "{0}" to "{1}".'.format(new_file, old_file))
        else:
            print('File "{0}" not found, your whitelist.yml is probably incorrect or old.'.format(new_file))
    elif isinstance(tree, (list, tuple)):
        return [_recursive_copy(v, path) for v in tree]
    else:
        return [_recursive_copy(v, os.path.join(path, k)) for k, v in tree.items()]


def update():
    """Pull the latest documentation from the neighboring /ipython directory.

    This will update the tutorial/example notebooks inside this directory with
    the notebooks listed in the whitelist.yml file.  Any changes pulled from
    the ipython directory will overwrite the old contents in this directory.
    This script does not run `git remote update` or `git checkout master` in the
    ipython repository, instead you are responsible for that."""
    with open('whitelist.yml', 'r') as f:
        _recursive_copy(yaml.load(f))

########NEW FILE########
__FILENAME__ = kapp
"""A simple embedding of an IPython kernel.
"""
#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

import sys

from IPython.lib.kernel import connect_qtconsole
from IPython.kernel.zmq.kernelapp import IPKernelApp

#-----------------------------------------------------------------------------
# Functions and classes
#-----------------------------------------------------------------------------
class SimpleKernelApp(object):
    """A minimal object that uses an IPython kernel and has a few methods
    to manipulate a namespace and open Qt consoles tied to the kernel.
    """

    def __init__(self, gui):
        # Start IPython kernel with GUI event loop support
        self.ipkernel = IPKernelApp.instance()
        self.ipkernel.initialize(['python', '--gui=%s' % gui,
                                  #'--log-level=10'  # for debugging
                                  ])

        # To create and track active qt consoles
        self.consoles = []
        
        # This application will also act on the shell user namespace
        self.namespace = self.ipkernel.shell.user_ns
        # Keys present at startup so we don't print the entire pylab/numpy
        # namespace when the user clicks the 'namespace' button
        self._init_keys = set(self.namespace.keys())

        # Example: a variable that will be seen by the user in the shell, and
        # that the GUI modifies (the 'Counter++' button increments it):
        self.namespace['app_counter'] = 0

    def print_namespace(self, evt=None):
        print("\n***Variables in User namespace***")
        for k, v in self.namespace.iteritems():
            if k not in self._init_keys and not k.startswith('_'):
                print('%s -> %r' % (k, v))
        sys.stdout.flush()

    def new_qt_console(self, evt=None):
        """start a new qtconsole connected to our kernel"""
        return connect_qtconsole(self.ipkernel.connection_file, 
                                 profile=self.ipkernel.profile)

    def count(self, evt=None):
        self.namespace['app_counter'] += 1

    def cleanup_consoles(self, evt=None):
        for c in self.consoles:
            c.kill()

    def start(self):
        self.ipkernel.start()

########NEW FILE########
__FILENAME__ = qtapp_ip
#!/usr/bin/env python
"""Example integrating an IPython kernel into a GUI App.

This trivial GUI application internally starts an IPython kernel, to which Qt
consoles can be connected either by the user at the command line or started
from the GUI itself, via a button.  The GUI can also manipulate one variable in
the kernel's namespace, and print the namespace to the console.

Play with it by running the script and then opening one or more consoles, and
pushing the 'Counter++' and 'Namespace' buttons.

Upon exit, it should automatically close all consoles opened from the GUI.

Consoles attached separately from a terminal will not be terminated, though
they will notice that their kernel died.
"""
#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

from PyQt4 import Qt

from kapp import SimpleKernelApp

#-----------------------------------------------------------------------------
# Functions and classes
#-----------------------------------------------------------------------------
class SimpleWindow(Qt.QWidget):

    def __init__(self, app):
        Qt.QWidget.__init__(self)
        self.app = app
        self.kapp = SimpleKernelApp('qt')
        self.add_widgets()

    def add_widgets(self):
        self.setGeometry(300, 300, 400, 70)
        self.setWindowTitle('IPython in your app')

        # Add simple buttons:
        console = Qt.QPushButton('Qt Console', self)
        console.setGeometry(10, 10, 100, 35)
        self.connect(console, Qt.SIGNAL('clicked()'), self.kapp.new_qt_console)

        namespace = Qt.QPushButton('Namespace', self)
        namespace.setGeometry(120, 10, 100, 35)
        self.connect(namespace, Qt.SIGNAL('clicked()'), self.kapp.print_namespace)

        count = Qt.QPushButton('Count++', self)
        count.setGeometry(230, 10, 80, 35)
        self.connect(count, Qt.SIGNAL('clicked()'), self.kapp.count)

        # Quit and cleanup
        quit = Qt.QPushButton('Quit', self)
        quit.setGeometry(320, 10, 60, 35)
        self.connect(quit, Qt.SIGNAL('clicked()'), Qt.qApp, Qt.SLOT('quit()'))

        self.app.connect(self.app, Qt.SIGNAL("lastWindowClosed()"),
                         self.app, Qt.SLOT("quit()"))

        self.app.aboutToQuit.connect(self.kapp.cleanup_consoles)

#-----------------------------------------------------------------------------
# Main script
#-----------------------------------------------------------------------------

if __name__ == "__main__":
    app = Qt.QApplication([])
    # Create our window
    win = SimpleWindow(app)
    win.show()

    # Very important, IPython-specific step: this gets GUI event loop
    # integration going, and it replaces calling app.exec_()
    win.kapp.start()

########NEW FILE########
__FILENAME__ = wxapp_ip
#!/usr/bin/env python
"""Example integrating an IPython kernel into a GUI App.

This trivial GUI application internally starts an IPython kernel, to which Qt
consoles can be connected either by the user at the command line or started
from the GUI itself, via a button.  The GUI can also manipulate one variable in
the kernel's namespace, and print the namespace to the console.

Play with it by running the script and then opening one or more consoles, and
pushing the 'Counter++' and 'Namespace' buttons.

Upon exit, it should automatically close all consoles opened from the GUI.

Consoles attached separately from a terminal will not be terminated, though
they will notice that their kernel died.

Ref: Modified from wxPython source code wxPython/samples/simple/simple.py
"""
#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import sys

import wx

from kapp import SimpleKernelApp

#-----------------------------------------------------------------------------
# Functions and classes
#-----------------------------------------------------------------------------

class MyFrame(wx.Frame):
    """
    This is MyFrame.  It just shows a few controls on a wxPanel,
    and has a simple menu.
    """

    def __init__(self, parent, title):

        # Start the IPython kernel with gui support
        self.kapp = SimpleKernelApp('wx')

        wx.Frame.__init__(self, parent, -1, title,
                          pos=(150, 150), size=(350, 285))

        # Create the menubar
        menuBar = wx.MenuBar()

        # and a menu 
        menu = wx.Menu()

        # add an item to the menu, using \tKeyName automatically
        # creates an accelerator, the third param is some help text
        # that will show up in the statusbar
        menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Exit this simple sample")

        # bind the menu event to an event handler
        self.Bind(wx.EVT_MENU, self.OnTimeToClose, id=wx.ID_EXIT)

        # and put the menu on the menubar
        menuBar.Append(menu, "&File")
        self.SetMenuBar(menuBar)

        self.CreateStatusBar()

        # Now create the Panel to put the other controls on.
        panel = wx.Panel(self)

        # and a few controls
        text = wx.StaticText(panel, -1, "Hello World!")
        text.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD))
        text.SetSize(text.GetBestSize())
        qtconsole_btn = wx.Button(panel, -1, "Qt Console")
        ns_btn = wx.Button(panel, -1, "Namespace")
        count_btn = wx.Button(panel, -1, "Count++")
        close_btn = wx.Button(panel, -1, "Quit")

        # bind the button events to handlers
        self.Bind(wx.EVT_BUTTON, self.kapp.new_qt_console, qtconsole_btn)
        self.Bind(wx.EVT_BUTTON, self.kapp.print_namespace, ns_btn)
        self.Bind(wx.EVT_BUTTON, self.kapp.count, count_btn)
        self.Bind(wx.EVT_BUTTON, self.OnTimeToClose, close_btn)

        # Use a sizer to layout the controls, stacked vertically and with
        # a 10 pixel border around each
        sizer = wx.BoxSizer(wx.VERTICAL)
        for ctrl in [text, qtconsole_btn, ns_btn, count_btn, close_btn]:
            sizer.Add(ctrl, 0, wx.ALL, 10)
        panel.SetSizer(sizer)
        panel.Layout()

    def OnTimeToClose(self, evt):
        """Event handler for the button click."""
        print("See ya later!")
        sys.stdout.flush()
        self.kapp.cleanup_consoles(evt)
        self.Close()
        # Not sure why, but our IPython kernel seems to prevent normal WX
        # shutdown, so an explicit exit() call is needed.
        sys.exit()


class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None, "Simple wxPython App")
        self.SetTopWindow(frame)
        frame.Show(True)
        self.kapp = frame.kapp
        return True

#-----------------------------------------------------------------------------
# Main script
#-----------------------------------------------------------------------------

if __name__ == '__main__':
    app = MyApp(redirect=False, clearSigInt=False)

    # Very important, IPython-specific step: this gets GUI event loop
    # integration going, and it replaces calling app.MainLoop()
    app.kapp.start()

########NEW FILE########
__FILENAME__ = colored
from IPython.html.widgets import *
w = HTMLWidget(value="Hello world!")
w.set_css({
    'background': 'red',
    'color': 'yellow',
})
w
########NEW FILE########
__FILENAME__ = data explorer
def plot_iris(a=None, col1=0, col2=0):
    plt.scatter(a[:,col1], a[:,col2])

interact(plot_iris, a=fixed(iris_data.data), col1=(0,3), col2=(0,3));
########NEW FILE########
__FILENAME__ = displaying
from IPython.html.widgets import *
from IPython.display import display
w = TextWidget(value="test")
display(w)
w.keys

########NEW FILE########
__FILENAME__ = link
from IPython.html.widgets import *
from IPython.display import display
from IPython.utils.traitlets import link
code = TextareaWidget(description="Source:", value="Cool math: $\\frac{F}{m}=a$")
preview = LatexWidget()
display(code, preview)
mylink = link((code, 'value'), (preview, 'value'))
########NEW FILE########
__FILENAME__ = on_submit
from IPython.html.widgets import *
w = TextWidget()
def handle_submit(sender):
    print(sender.value)
    sender.value = ''
w.on_submit(handle_submit)
w

########NEW FILE########
__FILENAME__ = on_trait_change
from IPython.html.widgets import *
w = TextWidget()
def handle_submit(name, new):
    print(new)
w.on_trait_change(handle_submit, 'value')
w
########NEW FILE########
__FILENAME__ = param plot 1
def plot_sin(a, b):
    x = np.linspace(0,4*np.pi, 100)
    y = np.sin(a*x+b)
    plt.plot(x,y)

interact(plot_sin, a=(0.0,5.0,0.1), b=(-5.0,5.0,0.1));
########NEW FILE########
__FILENAME__ = param plot 2
@interact(a=(0.0,5.0,0.1), b=(-5.0,5.0,0.1),
         style={'dotted red': 'r.', 'dashed black': 'k--'})
def plot_sin2(a, b, style='r.'):
    x = np.linspace(0,4*np.pi, 100)
    y = np.sin(a*x+b)
    plt.plot(x, y, style)
########NEW FILE########
__FILENAME__ = selection
from IPython.html.widgets import *
from IPython.display import display
w = RadioButtonsWidget(values={"Left": 0, "Center": 1, "Right": 2}, description="Alignment:")
display(w)

print(w.value)
w.value = 1

########NEW FILE########
__FILENAME__ = sliders
from IPython.html.widgets import *
from IPython.display import display
sliders = [FloatSliderWidget(description=str(i), orientation="vertical", value=50.) for i in range(10)]
container = ContainerWidget(children=sliders)
display(container)
container.remove_class('vbox')
container.add_class('hbox')
########NEW FILE########
__FILENAME__ = string sorting
def sort_string(s, reverse=False):
    s = reversed(sorted(s)) if reverse else sorted(s)
    print ''.join(s)

interact(sort_string, s='Hi', reverse=False);

########NEW FILE########
__FILENAME__ = mycircle
class MyCircle(object):

    def __init__(self, center=(0.0,0.0), radius=1.0, color='blue'):
        self.center = center
        self.radius = radius
        self.color = color

    def _repr_html_(self):
        return "&#x25CB; (<b>html</b>)"

    def _repr_svg_(self):
        return """<svg width="100px" height="100px">
           <circle cx="50" cy="50" r="20" stroke="black" stroke-width="1" fill="blue"/>
        </svg>"""
    
    def _repr_latex_(self):
        return r"$\bigcirc \LaTeX$"

    def _repr_javascript_(self):
        return "alert('I am a circle!');"

########NEW FILE########
__FILENAME__ = mycircle_png
ip = get_ipython()
png_f = ip.display_formatter.formatters['image/png']
png_f.for_type(MyCircle, circle_to_png)
########NEW FILE########
__FILENAME__ = ndarray_png
ip = get_ipython()
png_f = ip.display_formatter.formatters['image/png']
png_f.for_type(np.ndarray, ndarray_to_png)
########NEW FILE########
__FILENAME__ = italicstr
class ItalicStr(str):
    def _repr_html_(self):
        return '<i>%s</i>' % self
    
ItalicStr('Hello World')
########NEW FILE########
__FILENAME__ = lnum
%%file lnum.py
#!/usr/bin/env python
import sys
for i, line in enumerate(sys.stdin.readlines()):
    print i+1, ':', line,
    
print '\n---- END ---'
########NEW FILE########
__FILENAME__ = load
%matplotlb inline

%load http://matplotlib.org/mpl_examples/api/hinton_demo.py
########NEW FILE########
__FILENAME__ = mymagics
# -*- encoding: utf-8 -*-

import io
import os
import time

from IPython.nbformat import current

class TicToc(object):
    def __init__(self):
        self.tic()

    def tic(self, line=''):
        self.t0 = time.time()

    def toc(self, line=''):
        print self.format_time(time.time() - self.t0)

    def format_time(self, dt):
        if dt < 1e-6:
            return u"%.3g ns" % (dt * 1e9)
        elif dt < 1e-3:
            return u"%.3g µs" % (dt * 1e6)
        elif dt < 1:
            return u"%.3g ms" % (dt * 1e3)
        else:
            return "%.3g s" % dt


def load_notebook(filename):
    """load a notebook object from a filename"""
    if not os.path.exists(filename) and not filename.endswith(".ipynb"):
        filename = filename + ".ipynb"
    with io.open(filename) as f:
        return current.read(f, 'json')

def nbrun(line):
    """given a filename, execute the notebook in IPython"""
    nb = load_notebook(line)
    ip = get_ipython()
    for cell in nb.worksheets[0].cells:
        if cell.cell_type == 'code':
            ip.run_cell(cell.input, silent=True)
    
def load_ipython_extension(ip):
    tictoc = TicToc()
    ip.register_magic_function(tictoc.tic)
    ip.register_magic_function(tictoc.toc)
    ip.register_magic_function(nbrun)
    ip.user_ns['load_notebook'] = load_notebook
    
########NEW FILE########
__FILENAME__ = nbrun
def nbrun(line):
    """given a filename, execute the notebook in IPython"""
    nb = load_notebook(line)
    ip = get_ipython()
    for cell in nb.worksheets[0].cells:
        if cell.cell_type == 'code':
            ip.run_cell(cell.input, silent=True)
    
get_ipython().register_magic_function(nbrun)
########NEW FILE########
__FILENAME__ = nestedloop
# To parallelize every call with map, you just need to get a list for each argument.
# You can use `itertools.product` + `zip` to get this:


import itertools

product = list(itertools.product(widths, heights))
# [(1, 6), (1, 7), (2, 6), (2, 7), (3, 6), (3, 7)]

# So we have a "list of pairs", 
# but what we really want is a single list for each argument, i.e. a "pair of lists".
# This is exactly what the slightly weird `zip(*product)` syntax gets us:

allwidths, allheights = zip(*itertools.product(widths, heights))

print " widths", allwidths
print "heights", allheights

# Now we just map our function onto those two lists, to parallelize nested for loops:

ar = lview.map_async(area, allwidths, allheights)

########NEW FILE########
__FILENAME__ = plotscale
def plot_scale_magic(line, cell):
    """run a cell block with a variety of input values,

    and plot the result.
    """
    name, values = parse_magic_line(line)
    ns = get_ipython().user_ns
    times = []
    for v in values:
        assignment = "%s=%r" % (name, v)
        print assignment
        ns[name] = v
        sys.stdout.flush()
        tic = time.time()
        exec cell in ns
        toc = time.time()
        dt = toc - tic
        times.append(dt)
        print "%.3f ms" % (1000 * dt)
        sys.stdout.flush()
    plot_scale(values, times, name)

ip.register_magic_function(plot_scale_magic, "cell", "plotscale")
########NEW FILE########
__FILENAME__ = remote_iter
from IPython import parallel

def remote_iterator(view, name):
    """Return an iterator on an object living on a remote engine."""
    it_name = '_%s_iter' % name
    view.execute('%s = iter(%s)' % (it_name,name), block=True)
    ref = parallel.Reference(it_name)
    while True:
        try:
            yield view.apply_sync(lambda x: x.next(), ref)
        # This causes the StopIteration exception to be raised.
        except parallel.RemoteError as e:
            if e.ename == 'StopIteration':
                raise StopIteration
            else:
                raise e

########NEW FILE########
__FILENAME__ = remote_iter_hint
from IPython.display import display

t_minus = range(10,0,-1)

def lazy_iterator(name):
    seq = eval(name)
    it = iter(seq)
    while True:
        try:
            yield it.next()
        # this looks silly locally, but it will be useful for the remote version:
        except StopIteration:
            raise StopIteration

lzit = lazy_iterator('t_minus')
display(lzit)
list(lzit)
########NEW FILE########
__FILENAME__ = remote_iter_slightly_better
from IPython import parallel

def remote_iterator(view, name):
    """Return an iterator on an object living on a remote engine."""
    it_name = '_%s_iter' % name
    view.execute('%s = iter(%s)' % (it_name,name), block=True)
    next_ref = parallel.Reference(it_name + '.next')
    while True:
        try:
            yield view.apply_sync(next_ref)
        # This causes the StopIteration exception to be raised.
        except parallel.RemoteError as e:
            if e.ename == 'StopIteration':
                raise StopIteration
            else:
                raise e

########NEW FILE########
__FILENAME__ = scalemagic
def scale_magic(line, cell):
    """run a cell block with a variety of input values"""
    name, values = parse_magic_line(line)
    ns = get_ipython().user_ns
    for v in values:
        assignment = "%s=%r" % (name, v)
        print assignment
        ns[name] = v
        sys.stdout.flush()
        %tic
        exec cell in ns
        %toc

ip = get_ipython()
ip.register_magic_function(scale_magic, "cell", "scale")
########NEW FILE########
__FILENAME__ = soundcloud
from IPython.display import HTML
h = HTML("""<iframe width="100%" height="166" scrolling="no" frameborder="no" src="https://w.soundcloud.com/player/?url=http%3A%2F%2Fapi.soundcloud.com%2Ftracks%2F94543639"></iframe>""")
display(h)
########NEW FILE########
__FILENAME__ = taylor
# For an expression made from elementary functions, we must first make it into
# a callable function, the simplest way is to use the Python lambda construct.
plot_taylor_approximations(lambda x: 1/cos(x), 0, [2,4,6], (0, 2*pi), (-5,5))
########NEW FILE########
__FILENAME__ = tictoc
# -*- coding: utf-8 -*-
import time

class TicToc(object):
    def __init__(self):
        self.tic()

    def tic(self, line=''):
        self.t0 = time.time()

    def toc(self, line=''):
        print self.format_time(time.time() - self.t0)

    def format_time(self, dt):
        if dt < 1e-6:
            return u"%.3g ns" % (dt * 1e9)
        elif dt < 1e-3:
            return u"%.3g µs" % (dt * 1e6)
        elif dt < 1:
            return u"%.3g ms" % (dt * 1e3)
        else:
            return "%.3g s" % dt

tictoc = TicToc()

ip = get_ipython()
ip.register_magic_function(tictoc.tic)
ip.register_magic_function(tictoc.toc)

########NEW FILE########
__FILENAME__ = tictocf
# -*- coding: utf-8 -*-
import time

def format_time(dt):
    if dt < 1e-6:
        return u"%.3g ns" % (dt * 1e9)
    elif dt < 1e-3:
        return u"%.3g µs" % (dt * 1e6)
    elif dt < 1:
        return u"%.3g ms" % (dt * 1e3)
    else:
        return "%.3g s" % dt

def tic(line):
    global t0
    t0 = time.time()

def toc(line):
    global t0
    print (format_time(time.time() - t0))

ip = get_ipython()
ip.register_magic_function(tic)
ip.register_magic_function(toc)

########NEW FILE########
__FILENAME__ = nbmerge
"""
usage:

python nbmerge.py A.ipynb B.ipynb C.ipynb > merged.ipynb
"""

import io
import os
import sys

from IPython.nbformat import current

def merge_notebooks(filenames):
    merged = None
    for fname in filenames:
        with io.open(fname, 'r', encoding='utf-8') as f:
            nb = current.read(f, 'json')
        if merged is None:
            merged = nb
        else:
            merged.worksheets[0].cells.extend(nb.worksheets[0].cells)
    merged.metadata.name += "_merged"
    print current.writes(merged, 'json')

if __name__ == '__main__':
    merge_notebooks(sys.argv[1:])

########NEW FILE########
