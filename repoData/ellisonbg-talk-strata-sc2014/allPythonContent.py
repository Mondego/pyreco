__FILENAME__ = eventful_dict
import time

class EventfulDict(dict):
    """Eventful dictionary"""

    def __init__(self, *args, **kwargs):
        """Sleep is an optional float that allows you to tell the
        dictionary to hang for the given amount of seconds on each
        event.  This is usefull for animations."""
        self._sleep = kwargs.get('sleep', 0.0)
        self._add_callbacks = []
        self._del_callbacks = []
        self._set_callbacks = []
        dict.__init__(self, *args, **kwargs)
        
    def on_add(self, callback, remove=False):
        self._register_callback(self._add_callbacks, callback, remove)
    def on_del(self, callback, remove=False):
        self._register_callback(self._del_callbacks, callback, remove)
    def on_set(self, callback, remove=False):
        self._register_callback(self._set_callbacks, callback, remove)
    def _register_callback(self, callback_list, callback, remove=False):
        if callable(callback):
            if remove and callback in callback_list:
                callback_list.remove(callback)
            elif not remove and not callback in callback_list:
                callback_list.append(callback)
        else:
            raise Exception('Callback must be callable.')

    def _handle_add(self, key, value):
        self._try_callbacks(self._add_callbacks, key, value)
        self._try_sleep()
    def _handle_del(self, key):
        self._try_callbacks(self._del_callbacks, key)
        self._try_sleep()
    def _handle_set(self, key, value):
        self._try_callbacks(self._set_callbacks, key, value)
        self._try_sleep()
    def _try_callbacks(self, callback_list, *pargs, **kwargs):
        for callback in callback_list:
            callback(*pargs, **kwargs)
            
    def _try_sleep(self):
        if self._sleep > 0.0:
            time.sleep(self._sleep)
    
    def __setitem__(self, key, value):
        return_val = None
        exists = False
        if key in self:
            exists = True
            
        # If the user sets the property to a new dict, make the dict
        # eventful and listen to the changes of it ONLY if it is not
        # already eventful.  Any modification to this new dict will
        # fire a set event of the parent dict.
        if isinstance(value, dict) and not isinstance(value, EventfulDict):
            new_dict = EventfulDict(value)
            
            def handle_change(*pargs, **kwargs):
                self._try_callbacks(self._set_callbacks, key, dict.__getitem__(self, key))
                
            new_dict.on_add(handle_change)
            new_dict.on_del(handle_change)
            new_dict.on_set(handle_change)
            return_val = dict.__setitem__(self, key, new_dict)
        else:
            return_val = dict.__setitem__(self, key, value)
        
        if exists:
            self._handle_set(key, value)
        else:
            self._handle_add(key, value)
        return return_val
        
    def __delitem__(self, key):
        return_val = dict.__delitem__(self, key)
        self._handle_del(key)
        return return_val

    def pop(self, key):
        return_val = dict.pop(self, key)
        if key in self:
            self._handle_del(key)
        return return_val

    def popitem(self):
        popped = dict.popitem(self)
        if popped is not None and popped[0] is not None:
            self._handle_del(popped[0])
        return popped

    def update(self, other_dict):
        for (key, value) in other_dict.items():
            self[key] = value
            
    def clear(self):
        for key in list(self.keys()):
            del self[key]
########NEW FILE########
__FILENAME__ = eventful_graph
"""NetworkX graphs do not have events that can be listened to.  In order to 
watch the NetworkX graph object for changes a custom eventful graph object must 
be created.  The custom eventful graph object will inherit from the base graph 
object and use special eventful dictionaries instead of standard Python dict 
instances.  Because NetworkX nests dictionaries inside dictionaries, it's 
important that the eventful dictionary is capable of recognizing when a 
dictionary value is set to another dictionary instance.  When this happens, the 
eventful dictionary needs to also make the new dictionary an eventful 
dictionary.  This allows the eventful dictionary to listen to changes made to 
dictionaries within dictionaries."""
import networkx
from networkx.generators.classic import empty_graph

from eventful_dict import EventfulDict

class EventfulGraph(networkx.Graph):

    _constructed_callback = None

    @staticmethod
    def on_constructed(callback):
        """Register a callback to be called when a graph is constructed."""
        if callback is None or callable(callback):
            EventfulGraph._constructed_callback = callback
    
    def __init__(self, *pargs, **kwargs):
        """Initialize a graph with edges, name, graph attributes.
        
        Parameters
        sleep: float
            optional float that allows you to tell the
        dictionary to hang for the given amount of seconds on each
        event.  This is usefull for animations."""
        super(EventfulGraph, self).__init__(*pargs, **kwargs)

        # Override internal dictionaries with custom eventful ones.
        sleep = kwargs.get('sleep', 0.0)
        self.graph = EventfulDict(self.graph, sleep=sleep)
        self.node = EventfulDict(self.node, sleep=sleep)
        self.adj = EventfulDict(self.adj, sleep=sleep)

        # Notify callback of construction event.
        if EventfulGraph._constructed_callback:
            EventfulGraph._constructed_callback(self)


def empty_eventfulgraph_hook(*pargs, **kwargs):
    def wrapped(*wpargs, **wkwargs):
        """Wrapper for networkx.generators.classic.empty_graph(...)"""
        wkwargs['create_using'] = EventfulGraph(*pargs, **kwargs)
        return empty_graph(*wpargs, **wkwargs)
    return wrapped

########NEW FILE########
__FILENAME__ = frontmatter
from IPython.display import display, Image, HTML

class _ellisonbg(object):


    def _repr_html_(self):
        s = '<h3><a href="http://www.brianegranger.com" target="_blank">Brian E. Granger</a></h3>'
        s += '<h3><a href="http://calpoly.edu" target="_blank">Cal Poly</a> <a href="http://physics.calpoly.edu/" target="_blank">Physics Department</a></h3>'
        s += '<h3><a href="http://ipython.org" target="_blank">IPython Project</a></h3>'
        s += '<h3><a href="https://twitter.com/ellisonbg" target="_blank">@ellisonbg</a></h3>'
        return s
    
    def __repr__(self):
        s = "Brian E. Granger\n"
        s += "Cal Poly Physics Department\n"
        s += "IPython Project"
        s += "@ellisonbg"
        return s

_bio_text = """Brian Granger is an Assistant Professor of Physics at Cal Poly State University in San
Luis Obispo, CA. He has a background in theoretical atomic, molecular and optical physics,
with a Ph.D from the University of Colorado. His current research interests include
quantum computing, parallel and distributed computing and interactive computing
environments for scientific and technical computing. He is a core developer of the IPython
project and is an active contributor to a number of other open source projects focused on
scientific computing in Python. He is @ellisonbg on Twitter and GitHub."""

class _bio(object):
    
    def _repr_html_(self):
        return _bio_text
    
    def __repr__(self):
        return _bio_text

def whoami():
    display(_ellisonbg())

def bio():
    display(_bio())

def logos():
    display(Image('images/calpoly_logo.png'))
    display(Image('images/ipython_logo.png'))


    
########NEW FILE########
__FILENAME__ = ipythonproject
from IPython.display import HTML, display

devs = [
    ('Fernando Perez', 'fperez.jpg'),
    ('Brian Granger', 'ellisonbg.jpg'),
    ('Min Ragan-Kelley', 'minrk.jpg'),
    ('Thomas Kluyver', 'takluyver.jpg'),
    ('Matthias Bussonnier', 'matthias.jpg'),
    ('Jonathan Frederic', 'jdfreder.jpg'),
    ('Paul Ivanov', 'ivanov.jpg'),
    ('Evan Patterson', 'epatters.jpg'),
    ('Damian Avila', 'damianavila.jpg'),
    ('Brad Froehle', 'brad.jpg'),
    ('Zach Sailer', 'zsailer.jpg'),
    ('Robert Kern', 'rkern.jpg'),
    ('Jorgen Stenarson', 'jorgen.jpg'),
    ('Jonathan March', 'jdmarch.jpg'),
    ('Kyle Kelley', 'rgbkrk.jpg')
]

def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]

s = "<table>"

for row in chunks(devs, 4):
    s += "<tr>"
    for person in row:
        s += "<td>"
        s += '<img src="ipythonteam/{image}" style="height: 150px; text-align: center; margin-left: auto; margin-right: auto;"/>'.format(image=person[1])
        s += '<h3 style="text-align: center;">{name}</h3>'.format(name=person[0])
        s += "</td>"
    s += "</tr>"
    
s += "</table>"

def core_devs():
    display(HTML(s))
########NEW FILE########
__FILENAME__ = load_style
from IPython.display import display, HTML
import requests

def load_style(s):
    """Load a CSS stylesheet in the notebook by URL or filename.

    Examples::
    
        %load_style mystyle.css
        %load_style http://ipynbstyles.com/otherstyle.css
    """
    if s.startswith('http'):
        r =requests.get(s)
        style = r.text
    else:
        with open(s, 'r') as f:
            style = f.read()
    s = '<style>\n{style}\n</style>'.format(style=style)
    display(HTML(s))

def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magic_function(load_style)
########NEW FILE########
__FILENAME__ = lorenz
import numpy as np
from scipy import integrate

from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import cnames
from matplotlib import animation

def solve_lorenz(N=10, angle=0.0, max_time=4.0, sigma=10.0, beta=8./3, rho=28.0):

    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1], projection='3d')
    ax.axis('off')

    # prepare the axes limits
    ax.set_xlim((-25, 25))
    ax.set_ylim((-35, 35))
    ax.set_zlim((5, 55))
    
    def lorenz_deriv((x, y, z), t0, sigma=sigma, beta=beta, rho=rho):
        """Compute the time-derivative of a Lorentz system."""
        return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

    # Choose random starting points, uniformly distributed from -15 to 15
    np.random.seed(1)
    x0 = -15 + 30 * np.random.random((N, 3))

    # Solve for the trajectories
    t = np.linspace(0, max_time, int(250*max_time))
    x_t = np.asarray([integrate.odeint(lorenz_deriv, x0i, t)
                      for x0i in x0])
    
    # choose a different color for each trajectory
    colors = plt.cm.jet(np.linspace(0, 1, N))

    for i in range(N):
        x, y, z = x_t[i,:,:].T
        lines = ax.plot(x, y, z, '-', c=colors[i])
        plt.setp(lines, linewidth=2)

    ax.view_init(30, angle)
    plt.show()

    return t, x_t

########NEW FILE########
__FILENAME__ = talktools

from IPython.display import HTML, display, YouTubeVideo

def prefix(url):
    prefix = '' if url.startswith('http') else 'http://'
    return prefix + url


def simple_link(url, name=None):
    name = url if name is None else name
    url = prefix(url)
    return '<a href="%s">%s</a>' % (url, name)


def html_link(url, name=None):
    return HTML(simple_link(url, name))


# Utility functions
def website(url, name=None, width=800, height=450):
    html = []
    name = url if name == 'auto' else name
    if name:
        html.extend(['<div style="margin-bottom:10px">',
                     simple_link(url, name),
                     '</div>'] )

    html.append('<iframe src="%s"  width="%s" height="%s">' % 
                (prefix(url), width, height))
    html.append('</iframe>')
    return HTML('\n'.join(html))


def nbviewer(url=None, gist=None, name=None, width=800, height=450):
    if url:
        return website('nbviewer.ipython.org/url/' + url, name, width, height)
    elif gist:
        return website('nbviewer.ipython.org/' + str(gist), name, width, height)


########NEW FILE########
__FILENAME__ = widget_forcedirectedgraph
from IPython.html import widgets # Widget definitions
from IPython.utils.traitlets import Unicode, CInt, CFloat # Import the base Widget class and the traitlets Unicode class.
from IPython.display import display, Javascript

def publish_js():
    with open('./widget_forcedirectedgraph.js', 'r') as f:
        display(Javascript(data=f.read()))


# Define our ForceDirectedGraphWidget and its target model and default view.
class ForceDirectedGraphWidget(widgets.DOMWidget):
    _view_name = Unicode('D3ForceDirectedGraphView', sync=True)
    
    width = CInt(400, sync=True)
    height = CInt(300, sync=True)
    charge = CFloat(270., sync=True)
    distance = CInt(30., sync=True)
    strength = CInt(0.3, sync=True)
    
    def __init__(self, eventful_graph, *pargs, **kwargs):
        widgets.DOMWidget.__init__(self, *pargs, **kwargs)
        
        self._eventful_graph = eventful_graph
        self._send_dict_changes(eventful_graph.graph, 'graph')
        self._send_dict_changes(eventful_graph.node, 'node')
        self._send_dict_changes(eventful_graph.adj, 'adj')

    def _ipython_display_(self, *pargs, **kwargs):
        
        # Show the widget, then send the current state
        widgets.DOMWidget._ipython_display_(self, *pargs, **kwargs)
        for (key, value) in self._eventful_graph.graph.items():
            self.send({'dict': 'graph', 'action': 'add', 'key': key, 'value': value})
        for (key, value) in self._eventful_graph.node.items():
            self.send({'dict': 'node', 'action': 'add', 'key': key, 'value': value})
        for (key, value) in self._eventful_graph.adj.items():
            self.send({'dict': 'adj', 'action': 'add', 'key': key, 'value': value})

    def _send_dict_changes(self, eventful_dict, dict_name):
        def key_add(key, value):
            self.send({'dict': dict_name, 'action': 'add', 'key': key, 'value': value})
        def key_set(key, value):
            self.send({'dict': dict_name, 'action': 'set', 'key': key, 'value': value})
        def key_del(key):
            self.send({'dict': dict_name, 'action': 'del', 'key': key})
        eventful_dict.on_add(key_add)
        eventful_dict.on_set(key_set)
        eventful_dict.on_del(key_del)

########NEW FILE########
