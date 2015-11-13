__FILENAME__ = examples
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from JSAnimation import IPython_display

def basic_animation(frames=100, interval=30):
    """Plot a basic sine wave with oscillating amplitude"""
    fig = plt.figure()
    ax = plt.axes(xlim=(0, 10), ylim=(-2, 2))
    line, = ax.plot([], [], lw=2)

    x = np.linspace(0, 10, 1000)

    def init():
        line.set_data([], [])
        return line,

    def animate(i):
        y = np.cos(i * 0.02 * np.pi) * np.sin(x - i * 0.02 * np.pi)
        line.set_data(x, y)
        return line,

    return animation.FuncAnimation(fig, animate, init_func=init,
                                   frames=frames, interval=interval)


def lorenz_animation(N_trajectories=20, rseed=1, frames=200, interval=30):
    """Plot a 3D visualization of the dynamics of the Lorenz system"""
    from scipy import integrate
    from mpl_toolkits.mplot3d import Axes3D
    from matplotlib.colors import cnames

    def lorentz_deriv(coords, t0, sigma=10., beta=8./3, rho=28.0):
        """Compute the time-derivative of a Lorentz system."""
        x, y, z = coords
        return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

    # Choose random starting points, uniformly distributed from -15 to 15
    np.random.seed(rseed)
    x0 = -15 + 30 * np.random.random((N_trajectories, 3))

    # Solve for the trajectories
    t = np.linspace(0, 2, 500)
    x_t = np.asarray([integrate.odeint(lorentz_deriv, x0i, t)
                      for x0i in x0])

    # Set up figure & 3D axis for animation
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1], projection='3d')
    ax.axis('off')

    # choose a different color for each trajectory
    colors = plt.cm.jet(np.linspace(0, 1, N_trajectories))

    # set up lines and points
    lines = sum([ax.plot([], [], [], '-', c=c)
                 for c in colors], [])
    pts = sum([ax.plot([], [], [], 'o', c=c, ms=4)
               for c in colors], [])

    # prepare the axes limits
    ax.set_xlim((-25, 25))
    ax.set_ylim((-35, 35))
    ax.set_zlim((5, 55))

    # set point-of-view: specified by (altitude degrees, azimuth degrees)
    ax.view_init(30, 0)

    # initialization function: plot the background of each frame
    def init():
        for line, pt in zip(lines, pts):
            line.set_data([], [])
            line.set_3d_properties([])

            pt.set_data([], [])
            pt.set_3d_properties([])
        return lines + pts

    # animation function: called sequentially
    def animate(i):
        # we'll step two time-steps per frame.  This leads to nice results.
        i = (2 * i) % x_t.shape[1]

        for line, pt, xi in zip(lines, pts, x_t):
            x, y, z = xi[:i + 1].T
            line.set_data(x, y)
            line.set_3d_properties(z)

            pt.set_data(x[-1:], y[-1:])
            pt.set_3d_properties(z[-1:])

        ax.view_init(30, 0.3 * i)
        fig.canvas.draw()
        return lines + pts

    return animation.FuncAnimation(fig, animate, init_func=init,
                                   frames=frames, interval=interval)

########NEW FILE########
__FILENAME__ = html_writer
import os
import sys
import random
import string
import warnings
if sys.version_info < (3, 0):
    from cStringIO import StringIO as InMemory
else:
    from io import BytesIO as InMemory
from matplotlib.animation import writers, FileMovieWriter
from base64 import b64encode


ICON_DIR = os.path.join(os.path.dirname(__file__), 'icons')


class _Icons(object):
    """This class is a container for base64 representations of the icons"""
    icons = ['first', 'prev', 'reverse', 'pause', 'play', 'next', 'last']

    def __init__(self, icon_dir=ICON_DIR, extension='png'):
        self.icon_dir = icon_dir
        self.extension = extension
        for icon in self.icons:
            setattr(self, icon,
                    self._load_base64('{0}.{1}'.format(icon, extension)))

    def _load_base64(self, filename):
        data = open(os.path.join(self.icon_dir, filename), 'rb').read()
        return 'data:image/{0};base64,{1}'.format(self.extension,
                                                  b64encode(data).decode('ascii'))


JS_INCLUDE = """
<script language="javascript">
  /* Define the Animation class */
  function Animation(frames, img_id, slider_id, interval, loop_select_id){
    this.img_id = img_id;
    this.slider_id = slider_id;
    this.loop_select_id = loop_select_id;
    this.interval = interval;
    this.current_frame = 0;
    this.direction = 0;
    this.timer = null;
    this.frames = new Array(frames.length);

    for (var i=0; i<frames.length; i++)
    {
     this.frames[i] = new Image();
     this.frames[i].src = frames[i];
    }
    document.getElementById(this.slider_id).max = this.frames.length - 1;
    this.set_frame(this.current_frame);
  }

  Animation.prototype.get_loop_state = function(){
    var button_group = document[this.loop_select_id].state;
    for (var i = 0; i < button_group.length; i++) {
        var button = button_group[i];
        if (button.checked) {
            return button.value;
        }
    }
    return undefined;
  }

  Animation.prototype.set_frame = function(frame){
    this.current_frame = frame;
    document.getElementById(this.img_id).src = this.frames[this.current_frame].src;
    document.getElementById(this.slider_id).value = this.current_frame;
  }

  Animation.prototype.next_frame = function()
  {
    this.set_frame(Math.min(this.frames.length - 1, this.current_frame + 1));
  }

  Animation.prototype.previous_frame = function()
  {
    this.set_frame(Math.max(0, this.current_frame - 1));
  }

  Animation.prototype.first_frame = function()
  {
    this.set_frame(0);
  }

  Animation.prototype.last_frame = function()
  {
    this.set_frame(this.frames.length - 1);
  }

  Animation.prototype.slower = function()
  {
    this.interval /= 0.7;
    if(this.direction > 0){this.play_animation();}
    else if(this.direction < 0){this.reverse_animation();}
  }

  Animation.prototype.faster = function()
  {
    this.interval *= 0.7;
    if(this.direction > 0){this.play_animation();}
    else if(this.direction < 0){this.reverse_animation();}
  }

  Animation.prototype.anim_step_forward = function()
  {
    this.current_frame += 1;
    if(this.current_frame < this.frames.length){
      this.set_frame(this.current_frame);
    }else{
      var loop_state = this.get_loop_state();
      if(loop_state == "loop"){
        this.first_frame();
      }else if(loop_state == "reflect"){
        this.last_frame();
        this.reverse_animation();
      }else{
        this.pause_animation();
        this.last_frame();
      }
    }
  }

  Animation.prototype.anim_step_reverse = function()
  {
    this.current_frame -= 1;
    if(this.current_frame >= 0){
      this.set_frame(this.current_frame);
    }else{
      var loop_state = this.get_loop_state();
      if(loop_state == "loop"){
        this.last_frame();
      }else if(loop_state == "reflect"){
        this.first_frame();
        this.play_animation();
      }else{
        this.pause_animation();
        this.first_frame();
      }
    }
  }

  Animation.prototype.pause_animation = function()
  {
    this.direction = 0;
    if (this.timer){
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  Animation.prototype.play_animation = function()
  {
    this.pause_animation();
    this.direction = 1;
    var t = this;
    if (!this.timer) this.timer = setInterval(function(){t.anim_step_forward();}, this.interval);
  }

  Animation.prototype.reverse_animation = function()
  {
    this.pause_animation();
    this.direction = -1;
    var t = this;
    if (!this.timer) this.timer = setInterval(function(){t.anim_step_reverse();}, this.interval);
  }
</script>
"""


DISPLAY_TEMPLATE = """
<div class="animation" align="center">
    <img id="_anim_img{id}">
    <br>
    <input id="_anim_slider{id}" type="range" style="width:350px" name="points" min="0" max="1" step="1" value="0" onchange="anim{id}.set_frame(parseInt(this.value));"></input>
    <br>
    <button onclick="anim{id}.slower()">&#8211;</button>
    <button onclick="anim{id}.first_frame()"><img class="anim_icon" src="{icons.first}"></button>
    <button onclick="anim{id}.previous_frame()"><img class="anim_icon" src="{icons.prev}"></button>
    <button onclick="anim{id}.reverse_animation()"><img class="anim_icon" src="{icons.reverse}"></button>
    <button onclick="anim{id}.pause_animation()"><img class="anim_icon" src="{icons.pause}"></button>
    <button onclick="anim{id}.play_animation()"><img class="anim_icon" src="{icons.play}"></button>
    <button onclick="anim{id}.next_frame()"><img class="anim_icon" src="{icons.next}"></button>
    <button onclick="anim{id}.last_frame()"><img class="anim_icon" src="{icons.last}"></button>
    <button onclick="anim{id}.faster()">+</button>
  <form action="#n" name="_anim_loop_select{id}" class="anim_control">
    <input type="radio" name="state" value="once" {once_checked}> Once </input>
    <input type="radio" name="state" value="loop" {loop_checked}> Loop </input>
    <input type="radio" name="state" value="reflect" {reflect_checked}> Reflect </input>
  </form>
</div>


<script language="javascript">
  /* Instantiate the Animation class. */
  /* The IDs given should match those used in the template above. */
  (function() {{
    var img_id = "_anim_img{id}";
    var slider_id = "_anim_slider{id}";
    var loop_select_id = "_anim_loop_select{id}";
    var frames = new Array({Nframes});
    {fill_frames}

    /* set a timeout to make sure all the above elements are created before
       the object is initialized. */
    setTimeout(function() {{
        anim{id} = new Animation(frames, img_id, slider_id, {interval}, loop_select_id);
    }}, 0);
  }})()
</script>
"""

INCLUDED_FRAMES = """
  for (var i=0; i<{Nframes}; i++){{
    frames[i] = "{frame_dir}/frame" + ("0000000" + i).slice(-7) + ".{frame_format}";
  }}
"""


def _included_frames(frame_list, frame_format):
    """frame_list should be a list of filenames"""
    return INCLUDED_FRAMES.format(Nframes=len(frame_list),
                                  frame_dir=os.path.dirname(frame_list[0]),
                                  frame_format=frame_format)


def _embedded_frames(frame_list, frame_format):
    """frame_list should be a list of base64-encoded png files"""
    template = '  frames[{0}] = "data:image/{1};base64,{2}"\n'
    embedded = "\n"
    for i, frame_data in enumerate(frame_list):
        embedded += template.format(i, frame_format,
                                    frame_data.replace('\n', '\\\n'))
    return embedded


@writers.register('html')
class HTMLWriter(FileMovieWriter):
    # we start the animation id count at a random number: this way, if two
    # animations are meant to be included on one HTML page, there is a
    # very small chance of conflict.
    rng = random.Random()
    exec_key = 'animation.ffmpeg_path'
    args_key = 'animation.ffmpeg_args'
    supported_formats = ['png', 'jpeg', 'tiff', 'svg']

    @classmethod
    def new_id(cls):
        #return '%16x' % cls.rng.getrandbits(64)
        return ''.join(cls.rng.choice(string.ascii_uppercase)
                       for x in range(16))

    def __init__(self, fps=30, codec=None, bitrate=None, extra_args=None,
                 metadata=None, embed_frames=False, default_mode='loop'):
        self.embed_frames = embed_frames
        self.default_mode = default_mode.lower()

        if self.default_mode not in ['loop', 'once', 'reflect']:
            self.default_mode = 'loop'
            warnings.warn("unrecognized default_mode: using 'loop'")

        self._saved_frames = list()
        super(HTMLWriter, self).__init__(fps, codec, bitrate,
                                         extra_args, metadata)

    def setup(self, fig, outfile, dpi, frame_dir=None):
        if os.path.splitext(outfile)[-1] not in ['.html', '.htm']:
            raise ValueError("outfile must be *.htm or *.html")

        if not self.embed_frames:
            if frame_dir is None:
                frame_dir = outfile.rstrip('.html') + '_frames'
            if not os.path.exists(frame_dir):
                os.makedirs(frame_dir)
            frame_prefix = os.path.join(frame_dir, 'frame')
        else:
            frame_prefix = None

        super(HTMLWriter, self).setup(fig, outfile, dpi,
                                      frame_prefix, clear_temp=False)

    def grab_frame(self, **savefig_kwargs):
        if self.embed_frames:
            suffix = '.' + self.frame_format
            f = InMemory()
            self.fig.savefig(f, format=self.frame_format,
                             dpi=self.dpi, **savefig_kwargs)
            f.seek(0)
            self._saved_frames.append(b64encode(f.read()).decode('ascii'))
        else:
            return super(HTMLWriter, self).grab_frame(**savefig_kwargs)

    def _run(self):
        # make a ducktyped subprocess standin
        # this is called by the MovieWriter base class, but not used here.
        class ProcessStandin(object):
            returncode = 0
            def communicate(self):
                return ('', '')
        self._proc = ProcessStandin()

        # save the frames to an html file
        if self.embed_frames:
            fill_frames = _embedded_frames(self._saved_frames,
                                           self.frame_format)
        else:
            # temp names is filled by FileMovieWriter
            fill_frames = _included_frames(self._temp_names,
                                           self.frame_format)

        mode_dict = dict(once_checked='',
                         loop_checked='',
                         reflect_checked='')
        mode_dict[self.default_mode + '_checked'] = 'checked'

        interval = int(1000. / self.fps)

        with open(self.outfile, 'w') as of:
            of.write(JS_INCLUDE)
            of.write(DISPLAY_TEMPLATE.format(id=self.new_id(),
                                             Nframes=len(self._temp_names),
                                             fill_frames=fill_frames,
                                             interval=interval,
                                             icons=_Icons(),
                                             **mode_dict))

########NEW FILE########
__FILENAME__ = IPython_display
from .html_writer import HTMLWriter
from matplotlib.animation import Animation
import matplotlib.pyplot as plt
import tempfile
import random
import os


__all__ = ['anim_to_html', 'display_animation']


class _NameOnlyTemporaryFile(object):
    """A context-managed temporary file which is not opened.

    The file should be accessible by name on any system.

    Parameters
    ----------
    suffix : string
        The suffix of the temporary file (default = '')
    prefix : string
        The prefix of the temporary file (default = '_tmp_')
    hash_length : string
        The length of the random hash.  The size of the hash space will
        be 16 ** hash_length (default=8)
    seed : integer
        the seed for the random number generator.  If not specified, the
        system time will be used as a seed.
    absolute : boolean
        If true, return an absolute path to a temporary file in the current
        working directory.

    Example
    -------

    >>> with _NameOnlyTemporaryFile(seed=0, absolute=False) as f:
    ...     print(f)
    ...
    _tmp_d82c07cd
    >>> os.path.exists('_tmp_d82c07cd')  # file removed after context
    False

    """
    def __init__(self, prefix='_tmp_', suffix='', hash_length=8,
                 seed=None, absolute=True):
        rng = random.Random(seed)
        self.name = '%s%0*x%s' % (prefix, hash_length,
                                  rng.getrandbits(4 * hash_length), suffix)
        if absolute:
            self.name = os.path.abspath(self.name)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        if os.path.exists(self.name):
            os.remove(self.name)


def anim_to_html(anim, fps=None, embed_frames=True, default_mode='loop'):
    """Generate HTML representation of the animation"""
    if fps is None and hasattr(anim, '_interval'):
        # Convert interval in ms to frames per second
        fps = 1000. / anim._interval

    plt.close(anim._fig)
    if hasattr(anim, "_html_representation"):
        return anim._html_representation
    else:
        # tempfile can't be used here: we need a filename, and this
        # fails on windows.  Instead, we use a custom filename generator
        #with tempfile.NamedTemporaryFile(suffix='.html') as f:
        with _NameOnlyTemporaryFile(suffix='.html') as f:
            anim.save(f.name,  writer=HTMLWriter(fps=fps,
                                                 embed_frames=embed_frames,
                                                 default_mode=default_mode))
            html = open(f.name).read()

        anim._html_representation = html
        return html


def display_animation(anim, **kwargs):
    """Display the animation with an IPython HTML object"""
    from IPython.display import HTML
    return HTML(anim_to_html(anim, **kwargs))


# This is the magic that makes animations display automatically in the
# IPython notebook.  The _repr_html_ method is a special method recognized
# by IPython.
Animation._repr_html_ = anim_to_html

########NEW FILE########
__FILENAME__ = make_animation
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation
from JSAnimation import HTMLWriter


fig = plt.figure(figsize=(4, 3))
ax = plt.axes(xlim=(0, 10), ylim=(-2, 2))
line, = ax.plot([], [], lw=2)

def init():
    line.set_data([], [])
    return line,

def animate(i):
    x = np.linspace(0, 10, 1000)
    y = np.cos(i * 0.02 * np.pi) * np.sin(x - i * 0.02 * np.pi)
    line.set_data(x, y)
    return line,

anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=100, interval=20, blit=True)

# set embed_frames=True to embed base64-encoded frames directly in the HTML
anim.save('animation.html', writer=HTMLWriter(embed_frames=True))

########NEW FILE########
__FILENAME__ = make_lorenz_animation
"""
Lorenz animation

Adapted from http://jakevdp.github.io/blog/2013/02/16/animating-the-lorentz-system-in-3d/
"""

import numpy as np
from scipy import integrate

from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import cnames
from matplotlib import animation

from JSAnimation import HTMLWriter

N_trajectories = 20


def lorentz_deriv((x, y, z), t0, sigma=10., beta=8./3, rho=28.0):
    """Compute the time-derivative of a Lorentz system."""
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]


# Choose random starting points, uniformly distributed from -15 to 15
np.random.seed(1)
x0 = -15 + 30 * np.random.random((N_trajectories, 3))

# Solve for the trajectories
t = np.linspace(0, 2, 500)
x_t = np.asarray([integrate.odeint(lorentz_deriv, x0i, t)
                  for x0i in x0])

# Set up figure & 3D axis for animation
fig = plt.figure(figsize=(4, 3))
ax = fig.add_axes([0, 0, 1, 1], projection='3d')
ax.axis('off')

# choose a different color for each trajectory
colors = plt.cm.jet(np.linspace(0, 1, N_trajectories))

# set up lines and points
lines = sum([ax.plot([], [], [], '-', c=c)
             for c in colors], [])
pts = sum([ax.plot([], [], [], 'o', c=c, ms=4)
           for c in colors], [])

# prepare the axes limits
ax.set_xlim((-25, 25))
ax.set_ylim((-35, 35))
ax.set_zlim((5, 55))

# set point-of-view: specified by (altitude degrees, azimuth degrees)
ax.view_init(30, 0)

# initialization function: plot the background of each frame
def init():
    for line, pt in zip(lines, pts):
        line.set_data([], [])
        line.set_3d_properties([])

        pt.set_data([], [])
        pt.set_3d_properties([])
    return lines + pts

# animation function.  This will be called sequentially with the frame number
def animate(i):
    # we'll step two time-steps per frame.  This leads to nice results.
    i = (2 * i) % x_t.shape[1]

    for line, pt, xi in zip(lines, pts, x_t):
        x, y, z = xi[:i + 1].T
        line.set_data(x, y)
        line.set_3d_properties(z)

        pt.set_data(x[-1:], y[-1:])
        pt.set_3d_properties(z[-1:])

    ax.view_init(30, 0.3 * i)
    fig.canvas.draw()
    return lines + pts

# instantiate the animator.
anim = animation.FuncAnimation(fig, animate, init_func=init,
                               frames=200, interval=30, blit=True)

# set embed_frames=False so that frames will be stored individually
anim.save('lorenz_animation.html', writer=HTMLWriter(embed_frames=False))



########NEW FILE########
__FILENAME__ = make_frames
"""
Create some sample animation frames for testing
"""
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 10, 1000)

fig, ax = plt.subplots(figsize=(4, 3))
line, = plt.plot(x, np.sin(x), '-b', lw=2)
ax.set_xlim(0, 10)
ax.set_ylim(-2, 2)

for i in range(100):
    line.set_data(x, np.cos(i * 0.02 * np.pi) * np.sin(x - i * 0.02 * np.pi))
    fig.savefig('frames/frame%.03i.png' % (i + 1))

########NEW FILE########
__FILENAME__ = make_lorenz_frames
import numpy as np
from scipy import integrate

from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.colors import cnames
from matplotlib import animation

N_trajectories = 20


def lorentz_deriv((x, y, z), t0, sigma=10., beta=8./3, rho=28.0):
    """Compute the time-derivative of a Lorentz system."""
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]


# Choose random starting points, uniformly distributed from -15 to 15
np.random.seed(1)
x0 = -15 + 30 * np.random.random((N_trajectories, 3))

# Solve for the trajectories
t = np.linspace(0, 4, 1000)
x_t = np.asarray([integrate.odeint(lorentz_deriv, x0i, t)
                  for x0i in x0])

# Set up figure & 3D axis for animation
fig = plt.figure()
ax = fig.add_axes([0, 0, 1, 1], projection='3d')
ax.axis('off')

# choose a different color for each trajectory
colors = plt.cm.jet(np.linspace(0, 1, N_trajectories))

# set up lines and points
lines = sum([ax.plot([], [], [], '-', c=c)
             for c in colors], [])
pts = sum([ax.plot([], [], [], 'o', c=c)
           for c in colors], [])

# prepare the axes limits
ax.set_xlim((-25, 25))
ax.set_ylim((-35, 35))
ax.set_zlim((5, 55))

# set point-of-view: specified by (altitude degrees, azimuth degrees)
ax.view_init(30, 0)

# initialization function: plot the background of each frame
def init():
    for line, pt in zip(lines, pts):
        line.set_data([], [])
        line.set_3d_properties([])

        pt.set_data([], [])
        pt.set_3d_properties([])
    return lines + pts

# animation function.  This will be called sequentially with the frame number
def animate(i):
    # we'll step two time-steps per frame.  This leads to nice results.
    i = (2 * i) % x_t.shape[1]

    for line, pt, xi in zip(lines, pts, x_t):
        x, y, z = xi[:i].T
        line.set_data(x, y)
        line.set_3d_properties(z)

        pt.set_data(x[-1:], y[-1:])
        pt.set_3d_properties(z[-1:])

    ax.view_init(30, 0.3 * i)
    fig.canvas.draw()
    return lines + pts

# instantiate the animator.
#anim = animation.FuncAnimation(fig, animate, init_func=init,
#                               frames=500, interval=30, blit=True)

# Save as mp4. This requires mplayer or ffmpeg to be installed
#anim.save('lorentz_attractor.mp4', fps=15, extra_args=['-vcodec', 'libx264'])

#plt.show()

for i in range(100):
    animate(2 * i + 1)
    fig.savefig('frames/frame%.03i.png' % (i + 1), dpi=80)


########NEW FILE########
