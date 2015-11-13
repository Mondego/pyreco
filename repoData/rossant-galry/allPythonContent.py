__FILENAME__ = benchmark01_points
"""Benchmark 01: Displaying points.

"""

from galry import *
from numpy import *
from numpy.random import *

figure(display_fps=True, momentum=False)
x, y = .2 * randn(2, 1e6)
plot(x, y, ',', ms=1)
show()

########NEW FILE########
__FILENAME__ = sample
import sys
from OpenGL.GLUT import *
from OpenGL.GL import *
from OpenGL.GLU import *

def display():
    glClear(GL_COLOR_BUFFER_BIT)
    glFlush()

def init():
    glClearColor(0, 0, 0, 0)
    
def resize(w, h):
    pass

glutInit(sys.argv)
glutInitDisplayMode(GLUT_SINGLE | GLUT_RGBA)
glutInitWindowSize(600, 600)
glutInitWindowPosition(100, 100)
glutCreateWindow("Sample")
init()
glutDisplayFunc(display)
glutReshapeFunc(resize)
glutMainLoop()

########NEW FILE########
__FILENAME__ = build
import os
from shutil import copy, rmtree
# from distutils.core import run_setup
from subprocess import call, Popen, PIPE

def symlink(source, target):
    """Cross-platform symlink"""
    os_symlink = getattr(os, "symlink", None)
    if callable(os_symlink):
        os_symlink(source, target)
    else:
        import ctypes
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        flags = 1 if os.path.isdir(source) else 0
        if csl(target, source, flags) == 0:
            raise ctypes.WinError()

pathname = os.path.abspath(os.path.dirname(__file__))
os.chdir(pathname)

# work from root
os.chdir('../../')

# clean up first
for dir in os.listdir('.'):
    if dir.endswith('egg-info'):
        rmtree(dir)

# create symlink to dependencies
links = [(os.path.realpath('../qtools/qtools'), 'qtools')]
for source, target in links:
    if not os.path.exists(target):
        symlink(source, target)

# copy setup.py and remove commented lines so that external dependencies
# are built into the package
copy('setup.py', 'setup.bak')
uncomment = False
with open('setup.py', 'r') as fr:
    with open('setup_dev.py', 'w') as fw:
        for line in fr:
            if line.strip() == '#<':
                uncomment = True
                # pass this line
                fw.write(line)
                continue
            elif line.strip() == '#>':
                uncomment = False
            # uncomment lines
            if uncomment:
                fw.write(line.replace('# ', ''))
            # or copy lines
            else:
                fw.write(line)
# override setup.py with the uncommented lines, so that this new file is
# included in the packages
copy('setup_dev.py', 'setup.py')
            
# build the distribution
# call('python setup.py bdist_wininst sdist --formats=gztar,zip')
call('python setup.py sdist --formats=gztar,zip')

# use the original setup.py
copy('setup.bak', 'setup.py')

# clean up
os.remove('setup.bak')
os.remove('setup_dev.py')

########NEW FILE########
__FILENAME__ = upload
import os
from shutil import copy, rmtree
# from distutils.core import run_setup
from subprocess import call, Popen, PIPE

def symlink(source, target):
    """Cross-platform symlink"""
    os_symlink = getattr(os, "symlink", None)
    if callable(os_symlink):
        os_symlink(source, target)
    else:
        import ctypes
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        flags = 1 if os.path.isdir(source) else 0
        if csl(target, source, flags) == 0:
            raise ctypes.WinError()

pathname = os.path.abspath(os.path.dirname(__file__))
os.chdir(pathname)

# work from root
os.chdir('../../')

# clean up first
for dir in os.listdir('.'):
    if dir.endswith('egg-info'):
        rmtree(dir)

# create symlink to dependencies
links = [(os.path.realpath('../qtools/qtools'), 'qtools')]
for source, target in links:
    if not os.path.exists(target):
        symlink(source, target)

# copy setup.py and remove commented lines so that external dependencies
# are built into the package
copy('setup.py', 'setup.bak')
uncomment = False
with open('setup.py', 'r') as fr:
    with open('setup_dev.py', 'w') as fw:
        for line in fr:
            if line.strip() == '#<':
                uncomment = True
                # pass this line
                fw.write(line)
                continue
            elif line.strip() == '#>':
                uncomment = False
            # uncomment lines
            if uncomment:
                fw.write(line.replace('# ', ''))
            # or copy lines
            else:
                fw.write(line)
# override setup.py with the uncommented lines, so that this new file is
# included in the packages
copy('setup_dev.py', 'setup.py')
            
# build the distribution
# call('python setup.py bdist_wininst sdist --formats=gztar,zip')
call('python setup.py sdist upload')

# use the original setup.py
copy('setup.bak', 'setup.py')

# clean up
os.remove('setup.bak')
os.remove('setup_dev.py')

########NEW FILE########
__FILENAME__ = 3dcube
"""3D cube example."""

from galry import *
import numpy as np

# cube creation function
def create_cube(color, scale=1.):
    """Create a cube as a set of independent triangles.
    
    Arguments:
      * color: the colors of each face, as a 6*4 array.
      * scale: the scale of the cube, the ridge length is 2*scale.
    
    Returns:
      * position: a Nx3 array with the positions of the vertices.
      * normal: a Nx3 array with the normals for each vertex.
      * color: a Nx3 array with the color for each vertex.
    
    """
    position = np.array([
        # Front
        [-1., -1., -1.],
        [1., -1., -1.],
        [-1., 1., -1.],
        
        [1., 1., -1.],
        [-1., 1., -1.],
        [1., -1., -1.],
        
        # Right
        [1., -1., -1.],
        [1., -1., 1.],
        [1., 1., -1.],
        
        [1., 1., 1.],
        [1., 1., -1.],
        [1., -1., 1.],
        
        # Back
        [1., -1., 1.],
        [-1., -1., 1.],
        [1., 1., 1.],
        
        [-1., 1., 1.],
        [1., 1., 1.],
        [-1., -1., 1.],
        
        # Left
        [-1., -1., 1.],
        [-1., -1., -1.],
        [-1., 1., 1.],
        
        [-1., 1., -1.],
        [-1., 1., 1.],
        [-1., -1., -1.],
        
        # Bottom
        [1., -1., 1.],
        [1., -1., -1.],
        [-1., -1., 1.],
        
        [-1., -1., -1.],
        [-1., -1., 1.],
        [1., -1., -1.],
        
        # Top
        [-1., 1., -1.],
        [-1., 1., 1.],
        [1., 1., -1.],
        
        [1., 1., 1.],
        [1., 1., -1.],
        [-1., 1., 1.],
    ])
    
    normal = np.array([
        # Front
        [0., 0., -1.],
        [0., 0., -1.],
        [0., 0., -1.],

        [0., 0., -1.],
        [0., 0., -1.],
        [0., 0., -1.],
        
        # Right
        [1., 0., 0.],
        [1., 0., 0.],
        [1., 0., 0.],

        [1., 0., 0.],
        [1., 0., 0.],
        [1., 0., 0.],
        
        # Back
        [0., 0., 1.],
        [0., 0., 1.],
        [0., 0., 1.],

        [0., 0., 1.],
        [0., 0., 1.],
        [0., 0., 1.],
        
        # Left
        [-1., 0., 0.],
        [-1., 0., 0.],
        [-1., 0., 0.],
        
        [-1., 0., 0.],
        [-1., 0., 0.],
        [-1., 0., 0.],
        
        # Bottom
        [0., -1., 0.],
        [0., -1., 0.],
        [0., -1., 0.],
        
        [0., -1., 0.],
        [0., -1., 0.],
        [0., -1., 0.],
        
        # Top
        [0., 1., 0.],
        [0., 1., 0.],
        [0., 1., 0.],
        
        [0., 1., 0.],
        [0., 1., 0.],
        [0., 1., 0.],
    ])    
    position *= scale
    color = np.repeat(color, 6, axis=0)
    return position, normal, color

# face colors
color = np.ones((6, 4))
color[0,[0,1]] = 0
color[1,[0,2]] = 0
color[2,[1,2]] = 0
color[3,[0]] = 0
color[4,[1]] = 0
color[5,[2]] = 0

# create the cube
position, normal, color = create_cube(color)

# render it as a set of triangles
mesh(position=position, color=color, normal=normal)
   
show()

########NEW FILE########
__FILENAME__ = brownian
"""Animated brownian motion."""
import numpy as np
from matplotlib.colors import hsv_to_rgb
from galry import *

class MyVisual(Visual):
    def initialize(self, X, color, T):
        n = X.shape[0]
        
        self.n = n
        self.size = n
        self.bounds = [0, n]
        self.primitive_type = 'LINE_STRIP'
        
        self.add_attribute('position', vartype='float', ndim=2, data=X)
        self.add_attribute('color', vartype='float', ndim=3, data=color)
        self.add_attribute('i', vartype='float', ndim=1, data=i)
        
        self.add_varying('vcolor', vartype='float', ndim=3)
        self.add_varying('vi', vartype='float', ndim=1)
        
        self.add_uniform('t', vartype='float', ndim=1, data=0.)
        
        self.add_vertex_main("""
        vcolor = color;
        vi = i;
        """)
        
        self.add_fragment_main("""
        out_color.rgb = vcolor;
        out_color.a = .1 * ceil(clamp(t - vi, 0, 1));
        """)

# number of steps
n = 1e6

# duration of the animation
T = 30.

b = np.array(np.random.rand(n, 2) < .5, dtype=np.float32)
b[b == True] = 1
b[b == False] = -1
X = np.cumsum(b, axis=0)

# print X
# exit()

# generate colors by varying linearly the hue, and convert from HSV to RGB
h = np.linspace(0., 1., n)
hsv = np.ones((1, n, 3))
hsv[0,:,0] = h
color = hsv_to_rgb(hsv)[0,...]
i = np.linspace(0., T, n)

m = X.min(axis=0)
M = X.max(axis=0)
center = (M + m)/2
X = 2 * (X - center) / (max(M) - min(m))

# current camera position
x = np.array([0., 0.])
y = np.array([0., 0.])

# filtering parameter
dt = .015

# zoom level
dx = .25

def anim(fig, params):
    global x, y, dx
    t, = params
    i = int(n * t / T) + 15000
    # follow the current position
    if i < n:
        y = X[i,:]
    # or unzoom at the end
    else:
        y *= (1 - dt)
        dx = np.clip(dx + dt * (1 - dx), 0, 1)
    if dx < .99:
        # filter the current position to avoid "camera shaking"
        x = x * (1 - dt) + dt * y    
        viewbox = [x[0] - dx, x[1] - dx, x[0] + dx, x[1] + dx]
        # set the viewbox
        fig.process_interaction('SetViewbox', viewbox)
        fig.set_data(t=t)

figure(constrain_ratio=True, toolbar=False)
visual(MyVisual, X, color, T)
animate(anim, dt=.01)
show()

########NEW FILE########
__FILENAME__ = dashed
"""Dash line example with binary texture."""

from galry import *
import numpy as np

# sin(x) function
x = np.linspace(-10., 10., 1000)
y = np.sin(x)

# to make dashes, we use a 1D texture with B&W colors...
color = np.array(get_color(['k', 'w']))

# and a lookup colormap index with alternating 0 and 1
index = np.zeros(len(x))
index[::2] = 1

# we then plot the graph and specify the texture and the colormap
plot(x=x, y=y, color_array_index=index, color=color,)

show()
########NEW FILE########
__FILENAME__ = filter
"""GPU-based image processing filters."""
import os
from galry import *
import pylab as plt

# we define a list of 3x3 image filter kernels
KERNELS = dict(
    original=np.array([[0,0,0],[0,1,0],[0,0,0]]),
    sharpen=np.array([[0,-1,0],[-1,5,-1],[0,-1,0]]),
    sobel=np.array([[1,0,-1],[2,0,-1],[1,0,-1]]),
    emboss=np.array([[-2,-1,0],[-1,1,1],[0,1,2]]),
    blur=np.array([[1,2,1],[2,4,2],[1,2,1]]),
    derivex=np.array([[0,0,0],[-1,0,1],[0,0,0]]),
    edges=np.array([[0,1,0],[1,-4,1],[0,1,0]]),
)

# current kernel index
CURRENT_KERNEL_IDX = 0

# we specialize the texture visual (which displays a 2D image) to add
# GPU filtering capabilities
class FilterVisual(TextureVisual):
    def initialize_fragment(self):
        # elementary step in the texture, where the coordinates are normalized
        # in [0, 1]. The step is then 1/size of the texture.
        self.add_uniform("step", data=1. / self.texsize[0])
        
        # uniform 3x3 matrix variable
        self.add_uniform("kernel", vartype="float", ndim=(3,3),
            data=KERNELS['original'])
            
        # we add some code in the fragment shader which computes the filtered
        # texture
        self.add_fragment_main("""
        /* Compute the convolution of the texture with the kernel */
        
        // The output color is a vec4 variable called `out_color`.
        out_color = vec4(0., 0., 0., 1.);
        
        // We compute the convolution.
        for (int i = 0; i < 3; i++)
        {
            for (int j = 0; j < 3; j++)
            {
                // The variables are those defined in the base class
                // TextureVisual.
                out_color.xyz += kernel[i][j] * texture2D(tex_sampler, 
                    varying_tex_coords + step * vec2(j - 1, i - 1)).xyz;
            }
        }
        """)

def change_kernel(figure, parameter):
    # we update the kernel index
    global CURRENT_KERNEL_IDX
    CURRENT_KERNEL_IDX += parameter
    CURRENT_KERNEL_IDX = np.mod(CURRENT_KERNEL_IDX, len(KERNELS))
    # we get the kernel name and matrix
    name = KERNELS.keys()[CURRENT_KERNEL_IDX]
    kernel = np.array(KERNELS[name], dtype=np.float32)
    # we normalize the kernel
    if kernel.sum() != 0:
        kernel = kernel / float(kernel.sum())
    # now we change the kernel variable in the image
    figure.set_data(kernel=kernel, visual='image')
    # and the text in the legend
    figure.set_data(text="%s filter" % name, visual='legend')

# create square figure
figure(constrain_ratio=True, constrain_navigation=True, figsize=(512,512))

# load the texture from an image thanks to matplotlib
path = os.path.dirname(os.path.realpath(__file__))
texture = plt.imread(os.path.join(path, "images/lena.png"))

# we add our custom visual
visual(FilterVisual, texture=texture, name='image')

# we add some text
text(text='original filter', name='legend', coordinates=(0,.95), is_static=True)

# add left and right arrow action handler
action('KeyPress', change_kernel, key='Left', param_getter=-1)
action('KeyPress', change_kernel, key='Right', param_getter=1)

show()

########NEW FILE########
__FILENAME__ = fountain
"""Particle system example."""
from galry import *
import pylab as plt
import numpy as np
import numpy.random as rdn
import time
import timeit
import os

class ParticleVisual(Visual):
    def get_position_update_code(self):
        return """
        // update position
        position.x += velocities.x * tloc;
        position.y += velocities.y * tloc - 0.5 * g * tloc * tloc;
        """
        
    def get_color_update_code(self):
        return """
        // pass the color and point size to the fragment shader
        varying_color = color;
        varying_color.w = alpha;
        """
    
    def base_fountain(self, initial_positions=None,
        velocities=None, color=None, alpha=None, delays=None):
        
        self.size = initial_positions.shape[0]
        self.primitive_type = 'POINTS'
        # load texture
        path = os.path.dirname(os.path.realpath(__file__))
        particle = plt.imread(os.path.join(path, "images/particle.png"))
        
        size = float(max(particle.shape))
        
        # create the dataset
        self.add_uniform("point_size", vartype="float", ndim=1, data=size)
        self.add_uniform("t", vartype="float", ndim=1, data=0.)
        self.add_uniform("color", vartype="float", ndim=4, data=color)
        
        # add the different data buffers
        self.add_attribute("initial_positions", vartype="float", ndim=2, data=initial_positions)
        self.add_attribute("velocities", vartype="float", ndim=2, data=velocities)
        self.add_attribute("delays", vartype="float", ndim=1, data=delays)
        self.add_attribute("alpha", vartype="float", ndim=1, data=alpha)
        
        self.add_varying("varying_color", vartype="float", ndim=4)
        
        # add particle texture
        self.add_texture("tex_sampler", size=particle.shape[:2],
            ncomponents=particle.shape[2], ndim=2, data=particle)
            
        vs = """
        // compute local time
        const float tmax = 5.;
        const float tlocmax = 2.;
        const float g = %G_CONSTANT%;
        
        // Local time.
        float tloc = mod(t - delays, tmax);
        
        vec2 position = initial_positions;
        
        if ((tloc >= 0) && (tloc <= tlocmax))
        {
            // position update
            %POSITION_UPDATE%
            
            %COLOR_UPDATE%
        }
        else
        {
            varying_color = vec4(0., 0., 0., 0.);
        }
        
        gl_PointSize = point_size;
        """
            
        vs = vs.replace('%POSITION_UPDATE%', self.get_position_update_code())
        vs = vs.replace('%COLOR_UPDATE%', self.get_color_update_code())
        vs = vs.replace('%G_CONSTANT%', '3.')
            
        self.add_vertex_main(vs)    

        self.add_fragment_main(
        """
            out_color = texture2D(tex_sampler, gl_PointCoord) * varying_color;
        """)

    def initialize(self, **kwargs):
        self.base_fountain(**kwargs)
    

def update(figure, parameter):
    t = parameter[0]
    figure.set_data(t=t)

if __name__ == '__main__':        
    figure()

    # number of particles
    n = 50000

    # initial positions
    positions = .02 * rdn.randn(n, 2)

    # initial velocities
    velocities = np.zeros((n, 2))
    v = 1.5 + .5 * rdn.rand(n)
    angles = .1 * rdn.randn(n) + np.pi / 2
    velocities[:,0] = v * np.cos(angles)
    velocities[:,1] = v * np.sin(angles)

    # transparency
    alpha = .2 * rdn.rand(n)

    # color
    color = (0.70,0.75,.98,1.)

    # random delays
    delays = 10 * rdn.rand(n)


    figure(constrain_navigation=True)

    # create the visual
    visual(ParticleVisual, 
        initial_positions=positions,
        velocities=velocities,
        alpha=alpha,
        color=color,
        delays=delays
        )


    animate(update, dt=.02)

    show()


########NEW FILE########
__FILENAME__ = fountain2
"""Particle system example bis with user interaction."""
from galry import *
import pylab as plt
import numpy as np
import numpy.random as rdn
import os
import time
import timeit
from fountain import ParticleVisual

class Particle2Visual(ParticleVisual):
    def get_position_update_code(self):
        return """
        // update position
        position.x += (velocities.x + v.x) * tloc;
        position.y += (velocities.y + v.y) * tloc - 0.5 * g * tloc * tloc;
        """
        
    def initialize(self, v=None, **kwargs):
        if v is None:
            v = (0., 0.)
        self.base_fountain(**kwargs)
        self.add_uniform("v", vartype="float", ndim=2, data=v)
        


def update(figure, parameter):
    t = parameter[0]
    v = getattr(figure, 'v', (0., 0.))
    figure.set_data(t=t, v=v)

def change_v(figure, parameter):
    figure.v = parameter
    


figure(constrain_navigation=True)


# number of particles
n = 20000

# initial positions
positions = .02 * rdn.randn(n, 2)

# initial velocities
velocities = .2 * rdn.rand(n, 2)
v = (0., 0.)

# transparency
alpha = .5 * rdn.rand(n)

# color
color = (0.70,0.75,.98,1.)

# random delays
delays = 10 * rdn.rand(n)

# create the dataset
visual(Particle2Visual, 
    initial_positions=positions,
    velocities=velocities,
    v=v,
    alpha=alpha,
    color=color,
    delays=delays
    )

action('Move', change_v,
       param_getter=lambda p: 
            (2 * p["mouse_position"][0],
             2 * p["mouse_position"][1]))


animate(update, dt=.02)

show()


########NEW FILE########
__FILENAME__ = gallery
"""Display all images in a directory."""

import Image
import numpy as np
import os
import sys
from galry import *

# load an image
def load(file, size=None):
    img = Image.open(file)
    if size is not None:
        img.thumbnail((size, size))
    return np.array(img)

# update the pointer to the next image
i = 0
def next(parameter=1):
    global i
    i = np.mod(i + parameter, len(files))

# return the current image and image ratio
def current():
    img = load(os.path.join(folder, files[i]), 5148/4)
    hi, wi, _ = img.shape
    ar = float(wi) / hi
    return img, ar

# callback function for the gallery navigation
def gotonext(figure, parameter):
    next(parameter)
    img, ar = current()
    figure.set_data(texture=img)
    figure.set_rendering_options(constrain_ratio=ar)
    figure.resizeGL(*figure.size)

# get list of images in the folder
if len(sys.argv) > 1:
    folder = sys.argv[1]
else:
    folder = '.'
files = sorted(filter(lambda f: f.lower().endswith('.jpg'), os.listdir(folder)))

if files:
    # get first image
    img, ar = current()

    # create a figure and show the filtered image    
    figure(constrain_ratio=ar, constrain_navigation=True)
    imshow(img, points=(-1., -1., 1., 1.), filter=True)

    # previous/next images with keyboard
    action('KeyPress', gotonext, key='Left', param_getter=-1)
    action('KeyPress', gotonext, key='Right', param_getter=1)

    show()

########NEW FILE########
__FILENAME__ = graph
"""Display an interactive graph with force-based dynamical layout. Nodes
can be moved with the mouse."""
from galry import *
import numpy.random as rdn
import networkx as nx
from networkx import adjacency_matrix
import itertools

def update(figure, parameter):
    
    x = figure.nodes_positions
    M = figure.M
    
    # figure.forces = -.05 * x#np.dot(M, x)
    
    u = x[:,0] - x[:,0].reshape((-1, 1))
    v = x[:,1] - x[:,1].reshape((-1, 1))
    r = np.sqrt(u ** 2 + v ** 2) ** 3
    # dist = np.sqrt(x[:,0] ** 2 + x[:,1] ** 2)
    
    # ind = r==0.
    r[r<.01] = .01
    
    u1 = u / r
    # u[ind] = 0
    u1 = u1.sum(axis=1)
    
    v1 = v / r
    # v[ind] = 0
    v1 = v1.sum(axis=1)
    
    r[r>10] = 10
    
    u *= M
    v *= M
    
    u2 = u * r
    v2 = v * r
    
    u2 = u2.sum(axis=1)
    v2 = v2.sum(axis=1)
    
    # repulsion (coulomb)
    a = -.5
    
    # attraction (spring)
    b = 5.
    
    c = .1
    
    # damping
    damp = .95
    
    figure.forces = np.empty((len(x), 2))
    figure.forces[:,0] = -c * x[:,0] + a * u1.ravel() + b * u2
    figure.forces[:,1] = -c * x[:,1] + a * v1.ravel() + b * v2
    
    v = damp * (figure.velocities + figure.forces * figure.dt)
    if getattr(figure, 'selected_node', None) is not None:
        v[figure.selected_node] = figure.velocities[figure.selected_node]
    figure.velocities = v
    
    e = (figure.velocities ** 2).sum()
    if e > 2e-3:
        
        figure.nodes_positions += figure.velocities * figure.dt
        figure.set_data(position=figure.nodes_positions, visual='graph_edges')

    if not hasattr(figure, '_viewbox'):
        figure._viewbox = (-10., -10., 10., 10.)
        figure.process_interaction('SetViewbox', figure._viewbox)
        
def node_moved(figure, parameter):
    x0, y0, x, y = parameter
    x0, y0 = figure.get_processor('navigation').get_data_coordinates(x0, y0)
    x, y = figure.get_processor('navigation').get_data_coordinates(x,y)
    p = getattr(figure, 'nodes_positions')
    if getattr(figure, 'selected_node', None) is None:
        r = (p[:,0] - x0) ** 2 + (p[:,1] - y0) ** 2
        figure.selected_node = r.argmin()
    p[figure.selected_node,:] = (x, y)
    figure.set_data(position=p, visual='edges')

def end_moved(figure, parameter):        
    if getattr(figure, 'selected_node', None) is not None:
        figure.selected_node = None
    
        
            
f = figure(antialiasing=True)


n = 100
# we define a random graph with networkx
# g = nx.barabasi_albert_graph(n, 5)

# g = nx.erdos_renyi_graph(n, 0.01)
g=nx.watts_strogatz_graph(n, 3, 0.5)
# g=nx.barabasi_albert_graph(n,5)
# g=nx.random_lobster(n, 0.9, 0.9)

# edges = itertools.combinations(g.subgraph(range(20)), 2)
# g.add_edges_from(edges)

f.M = adjacency_matrix(g)
f.Ms = f.M.sum(axis=1)

# get the array with the positions of all nodes
# positions = np.vstack([pos[i] for i in xrange(len(pos))]) - .5
positions = rdn.randn(n, 2) * .2

# get the array with the positions of all edges.
edges = np.vstack(g.edges()).ravel()

# random colors for the nodes
color = np.random.rand(len(positions), 4)
color[:,-1] = 1

coledges = (1., 1., 1., .25)

size = np.random.randint(low=50, high=200, size=n)

graph(position=positions, edges=edges, color=color, edges_color=coledges,
    node_size=size, name='graph')

    
f.edges = edges
f.nodes_positions = positions
f.velocities = np.zeros((len(positions), 2))
f.forces = np.zeros((len(positions), 2))
f.dt = .02



action('MiddleClickMove', 'NodeMoved',
       param_getter=lambda p: p["mouse_press_position"] + p["mouse_position"])
action('LeftClickMove', 'NodeMoved',
       key_modifier='Control',
       param_getter=lambda p: p["mouse_press_position"] + p["mouse_position"])

event('NodeMoved', node_moved)
event(None, end_moved)

animate(update, dt=f.dt)

print "Move nodes with middle-click + move"

show()
########NEW FILE########
__FILENAME__ = hsv
"""GPU-based HSV color space example."""

FSH = """
vec3 Hue(float H)
{
    float R = abs(H * 6 - 3) - 1;
    float G = 2 - abs(H * 6 - 2);
    float B = 2 - abs(H * 6 - 4);
    return vec3(clamp(R, 0, 1), clamp(G, 0, 1), clamp(B, 0, 1));
}

vec4 HSVtoRGB(vec3 HSV)
{
    return vec4(((Hue(HSV.x) - 1) * HSV.y + 1) * HSV.z,1);
}

vec4 RGBtoHSV(vec3 RGB)
{
    vec3 HSV = vec3(0., 0., 0.);
    HSV.z = max(RGB.r, max(RGB.g, RGB.b));
    float M = min(RGB.r, min(RGB.g, RGB.b));
    float C = HSV.z - M;
    if (C != 0)
    {
        HSV.y = C / HSV.z;
        vec3 Delta = (HSV.z - RGB) / C;
        Delta.rgb -= Delta.brg;
        Delta.rg += vec2(2,4);
        if (RGB.r >= HSV.z)
            HSV.x = Delta.b;
        else if (RGB.g >= HSV.z)
            HSV.x = Delta.r;
        else
            HSV.x = Delta.g;
        HSV.x = fract(HSV.x / 6);
    }
    return vec4(HSV,1);
}
"""

VS = """
//gl_PointSize = 600;
//tr = vec4(translation, scale);
//position = (position/scale-translation);

"""

FS = """
vec2 v = varying_tex_coords;
/*vec2 t = vec2(tr.x,-tr.y);
v = (v-t)/tr.zw;*/

out_color = HSVtoRGB(vec3(v.x,v.y,u));
"""

import numpy as np
from galry import *

class MV(TextureVisual):
    def initialize(self, *args, **kwargs):
        super(MV, self).initialize(*args, **kwargs)
        self.add_uniform('u', ndim=1, data=u)
        # pos = np.zeros((1, 2))
        # self.size = 1
        # self.primitive_type = 'POINTS'
        # self.add_attribute('position', ndim=2, vartype='float', data=pos)
        # self.add_varying('tr', ndim=4)
        
    def initialize_fragment(self):
        self.add_fragment_header(FSH)
        # self.add_vertex_main(VS)
        self.add_fragment_main(FS)
        
u = 1.
def change_color(fig, param):
    global u
    du = param
    u += du
    fig.set_data(u=u)

figure(constrain_navigation=True)
visual(MV)
action('KeyPress', change_color, key='Up', key_modifier='Shift', param_getter=.01)
action('KeyPress', change_color, key='Down', key_modifier='Shift', param_getter=-.01)
show()



########NEW FILE########
__FILENAME__ = image
"""Download an image and show it."""
# Necessary for future Python 3 compatibility
from __future__ import print_function
import os
from galry import *
from numpy import *
try:
    from PIL import Image
except Exception as e:
    raise ImportError("You need PIL for this example.")
import urllib, cStringIO

def load_image(url):
    """Download an image from an URL."""
    print("Downloading image... ", end="")
    file = cStringIO.StringIO(urllib.urlopen(url).read())
    print("Done!")
    return Image.open(file)
   
# new figure with ration constraining
figure(constrain_ratio=True, constrain_navigation=False,)

# download the image and convert it into a Numpy array
url = "http://earthobservatory.nasa.gov/blogs/elegantfigures/files/2011/10/globe_west_2048.jpg"
image = array(load_image(url))

# display the image
imshow(image, filter=True)

# show the image
show()



########NEW FILE########
__FILENAME__ = imshow
from galry import *
import numpy as np

x = 10 * np.random.rand(100, 50)
imshow(x)

show()
########NEW FILE########
__FILENAME__ = mandelbrot
"""GPU-based interactive Mandelbrot fractal example."""
from galry import *
import numpy as np
import numpy.random as rdn

FSH = """
// take a position and a number of iterations, and
// returns the first iteration where the system escapes a box of size N.
int mandelbrot_escape(vec2 pos, int iterations)
{
vec2 z = vec2(0., 0.);
int n = 0;
int N = 10;
int N2 = N * N;
float r2 = 0.;
for (int i = 0; i < iterations; i++)
{
    float zx = z.x * z.x - z.y * z.y + pos.x;
    float zy = 2 * z.x * z.y + pos.y;
    r2 = zx * zx + zy * zy;
    if (r2 > N2)
    {
        n = i;
        break;
    }
    z = vec2(zx, zy);
}
return n;
}
"""

FS = """
// this vector contains the coordinates of the current pixel
// varying_tex_coords contains a position in [0,1]^2
vec2 pos = vec2(-2.0 + 3. * varying_tex_coords.x, 
                -1.5 + 3. * varying_tex_coords.y);

// run mandelbrot system
int n = mandelbrot_escape(pos, iterations);

float c = log(float(n)) / log(float(iterations));

// compute the red value as a function of n
out_color = vec4(c, 0., 0., 1.);
"""

def get_iterations(zoom=1):
    return int(500 * np.log(1 + zoom))

class MandelbrotVisual(TextureVisual):
    def initialize_fragment(self):
        self.add_fragment_header(FSH)
        self.add_fragment_main(FS)
    
    def base_mandelbrot(self, iterations=None):
        if iterations is None:
            iterations = get_iterations()
        self.add_uniform("iterations", vartype="int", ndim=1, data=iterations)
        
    def initialize(self, *args, **kwargs):
        iterations = kwargs.pop('iterations', None)
        super(MandelbrotVisual, self).initialize(*args, **kwargs)
        self.base_mandelbrot(iterations)

def update(figure, parameter):
    zoom = figure.get_processor('navigation').sx
    figure.set_data(iterations=get_iterations(zoom))
        
figure(constrain_ratio=True,
       constrain_navigation=True,)

visual(MandelbrotVisual)

# event('Pan', pan)
event('Zoom', update)

show()
########NEW FILE########
__FILENAME__ = markers
"""Markers example."""

from galry import *
from numpy.random import *

# We generate 10,000 points randomly according to a standard normal random
# variable.
x, y = randn(2, 10000)

# We assign one color for each point, with random RGBA components.
color = rand(10000, 4)

# We plot x wrt. y, with a '+' marker of size 20 (in pixels).
plot(x, y, '+', ms=20, color=color)

# We specify the axes as (x0, x1, y0, y1).
axes(-5, -5, 5, 5)

show()

########NEW FILE########
__FILENAME__ = modern_art
"""Modern art."""
from galry import *
import numpy.random as rdn

figure(constrain_ratio=True, antialiasing=True)

# random positions
positions = .25 * rdn.randn(1000, 2)

# random colors
colors = rdn.rand(len(positions),4)

# TRIANGLES: three consecutive points = one triangle, no overlap
plot(primitive_type='TRIANGLES', position=positions, color=colors)

show()

########NEW FILE########
__FILENAME__ = plot
"""Test plotting capabilities."""
from galry import *
from numpy import *
from numpy.random import randn

# multiple plots in a single call (most efficient)
Y = .05 * randn(10, 1000) + 1.5
plot(Y)

n = 10000
x = linspace(0, 1, n)

# scatter plot
y1 = .25 * random.randn(n)
plot(x, y1, 'oy')

# sine thick wave
y2 = sin(10 * x)
plot(x, y2, thickness=.01, color='r.5')

# static text
text("Hello World!", coordinates=(0, .9), is_static=True)

# specify the window boundaries
xlim(0, 1)
ylim(-2, 2)

# show the grid by default
grid()

show()



########NEW FILE########
__FILENAME__ = points3d
"""Example with 3D points."""
from galry import *
import numpy as np

n = 100000
position = np.random.randn(n, 3)
color = np.random.rand(n, 4)
normal = np.zeros((n, 3))

vertex_shader = """
gl_Position = vec4(position, 1.0);
varying_color = color;
gl_PointSize = 1.0;
"""

figure()
mesh(position=position, color=color, normal=normal,
     primitive_type='POINTS',
     vertex_shader=vertex_shader)
show()


########NEW FILE########
__FILENAME__ = pong
"""Pong video game example, can be played with two players on the
same computer.

Controls:
    Left player: D/C keys
    Right player: Up/Down arrows
    F for fullscreen

"""
import os
from galry import *
import pylab as plt

# time interval
DT = .01

# ball velocity
V = 1

# half-size of the racket
DL = .15

def get_tex(n):
    # ball texture
    tex = np.ones((n, n, 4))
    tex[:,:,0] = 1
    x = np.linspace(-1., 1., n)
    X, Y = np.meshgrid(x, x)
    R = X ** 2 + Y ** 2
    R = np.minimum(1, 3 * np.exp(-5*R))
    tex[:,:,-1] = R
    return tex
        
def get_player_pos(who):
    return (pos[who][0,1] + pos[who][0,3]) / 2.

def move_player(fig, who, dy):
    if np.abs(get_player_pos(who) + dy) > .95:
        return
    pos[who][0,[1,3]] += dy
    fig.set_data(visual=who, coordinates=pos[who])
    
def move_player_right(fig, dy):
    move_player(fig, 'right', dy)
def move_player_left(fig, dy):
    move_player(fig, 'left', dy)
    
def new_game(figure, parameter=None):
    pos['left'] = np.array([[-.9, -DL, -.85, DL]])
    pos['right'] = np.array([[.9, -DL, .85, DL]])
    
    # ball position and velocity
    
    global ball_pos, ball_v
    
    ball_pos = np.array([[0., 0.]])
    ball_v = np.array([[V, 0.]])  

    figure.set_data(visual='left', coordinates=pos['left'])
    figure.set_data(visual='right', coordinates=pos['right'])
    figure.set_data(visual='score', text="%d - %d" % (score_left, score_right))

def move_ball(figure):
    global ball_pos, ball_v
    global score_left, score_right
    
    x, y = ball_pos[0,:]
    v = ball_v
    
    # top/bottom collision
    if np.abs(y) >= .95:
        ball_v[0,1] *= -1
    
    # right collision
    py = None
    if x >= .82:
        py = get_player_pos('right')
        
    # left collision
    if x <= -.82:
        py = get_player_pos('left')
        
    if py is not None:
        # update ball velocity
        if np.abs(y - py) <= DL:
            ball_v[0,0] *= -1
            # rebound angle depending on the position of the rebound on 
            # the racket
            ball_v[0,1] = 3 * (y - py)
    
    # one player wins, next game
    if x >= .95:
        score_left += 1
        new_game(figure)
    if x <= -.95:
        score_right += 1
        new_game(figure)
    
    # ball position update
    ball_pos += ball_v * DT
        
def update(figure, parameter):
    t = parameter[0]
    move_ball(figure)
    figure.set_data(visual='ball', position=ball_pos)
    
fig = figure(toolbar=False)

ball_pos = np.array([[0., 0.]])
ball_v = np.array([[0, 0.]])  

# player positions
pos = {}

# scores
score_left = 0
score_right = 0

# text visual
visual(TextVisual, coordinates=(0., .9), text='',
    fontsize=32, name='score', color=(1.,) * 4)
    
# visuals
rectangles(coordinates=(0.,) * 4,
    color=(1.,) * 4, name='left')
rectangles(coordinates=(0.,) * 4,
    color=(1.,) * 4, name='right')
sprites(position=np.zeros((1, 2)), texture=get_tex(32),
    color=(1.,) * 4, name='ball')

dx = .05

# left player bindings
action('KeyPress', 'LeftPlayerMove', key='D',
    param_getter=lambda p: dx)
action('KeyPress', 'LeftPlayerMove', key='C',
    param_getter=lambda p: -dx)

# right player bindings
action('KeyPress', 'RightPlayerMove', key='Up',
    param_getter=lambda p: dx)
action('KeyPress', 'RightPlayerMove', key='Down',
    param_getter=lambda p: -dx)

event('RightPlayerMove', move_player_right)
event('LeftPlayerMove', move_player_left)

event('NewGame', new_game)
event('Initialize', new_game)

animate(update, dt=DT)

print "Left player: D/C keys\nRight player: Up/Down arrows\nF for fullscreen"
show()

########NEW FILE########
__FILENAME__ = qtintegration
import numpy as np
from galry import *

class MyPaintManager(PlotPaintManager):
    def initialize(self):
        x = np.linspace(-1., 1., 1000)
        y = np.random.randn(1000)
        self.add_visual(PlotVisual, x=x, y=y)

class MyWidget(GalryWidget):
    def initialize(self):
        self.set_bindings(PlotBindings)
        self.set_companion_classes(
            paint_manager=MyPaintManager,
            interaction_manager=PlotInteractionManager,)
        self.initialize_companion_classes()

class Window(QtGui.QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.initUI()
        
    def initUI(self):
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(MyWidget())
        vbox.addWidget(MyWidget())
        self.setLayout(vbox)    
        
        self.setGeometry(300, 300, 600, 600)  
        self.show()
        
show_window(Window)

########NEW FILE########
__FILENAME__ = realtime
"""Real-time example.

This example shows how a real-time visualizer of digital signals can
be written with Galry.

"""
import numpy as np
from galry import *

# initial values
t = np.linspace(-1., 1., 1000)
x = .1 * np.random.randn(1000)

# this function returns 10 new values at each call
def get_new_data():
    return .1 * np.random.randn(10)

# this function updates the plot at each call
def anim(fig, _):
    # append new data to the signal
    global x
    x = np.hstack((x[10:], get_new_data()))
    
    # create the new 1000x2 position array with x, y values at each row
    position = np.vstack((t, x)).T
    
    # update the position of the plot
    fig.set_data(position=position)

# plot the signal
plot(t, x)

# animate the plot: anim is called every 25 milliseconds
animate(anim, dt=.025)

# show the figure
show()

########NEW FILE########
__FILENAME__ = realtime_multi
"""Real-time example.

This example shows how a real-time visualizer of multiple digital signals can
be written with Galry.

"""
import numpy as np
from galry import *

# initial values
nsamples = 1000
nplots = 10
t = np.tile(np.linspace(-1., 1., nsamples), (nplots, 1))
x = .01 * np.random.randn(nplots, nsamples) + np.linspace(-.75, .75, nplots)[:,np.newaxis]

# this function returns 10*nplots new values at each call
def get_new_data():
    return .01 * np.random.randn(nplots, 10) + np.linspace(-.75, .75, nplots)[:,np.newaxis]

# this function updates the plot at each call
def anim(fig, _):
    # append new data to the signal
    global x
    x = np.hstack((x[:,10:], get_new_data()))
    
    # create the new 1000*nplots*2 position array with x, y values at each row
    position = np.vstack((t.flatten(), x.flatten())).T
    
    # update the position of the plot
    fig.set_data(position=position)

# plot the signal
plot(t, x)

# animate the plot: anim is called every 25 milliseconds
animate(anim, dt=.025)

# show the figure
show()

########NEW FILE########
__FILENAME__ = surface
from galry import *
import numpy as np

n = 300

# generate grid
x = np.linspace(-1., 1., n)
y = np.linspace(-1., 1., n)
X, Y = np.meshgrid(x, y)

# surface function
Z = .1*np.cos(10*X) * np.sin(10*Y)

surface(Z)

show()

########NEW FILE########
__FILENAME__ = _run
"""Run all examples successively."""
from galry import run_all_scripts
run_all_scripts(ignore=['gallery.py'])

########NEW FILE########
__FILENAME__ = backend_galry
"""
This is a fully functional do nothing backend to provide a template to
backend writers.  It is fully functional in that you can select it as
a backend with

  import matplotlib
  matplotlib.use('Template')

and your matplotlib scripts will (should!) run without error, though
no output is produced.  This provides a nice starting point for
backend writers because you can selectively implement methods
(draw_rectangle, draw_lines, etc...) and slowly see your figure come
to life w/o having to have a full blown implementation before getting
any results.

Copy this to backend_xxx.py and replace all instances of 'template'
with 'xxx'.  Then implement the class methods and functions below, and
add 'xxx' to the switchyard in matplotlib/backends/__init__.py and
'xxx' to the backends list in the validate_backend methon in
matplotlib/__init__.py and you're off.  You can use your backend with::

  import matplotlib
  matplotlib.use('xxx')
  from pylab import *
  plot([1,2,3])
  show()

matplotlib also supports external backends, so you can place you can
use any module in your PYTHONPATH with the syntax::

  import matplotlib
  matplotlib.use('module://my_backend')

where my_backend.py is your module name.  Thus syntax is also
recognized in the rc file and in the -d argument in pylab, eg::

  python simple_plot.py -dmodule://my_backend

The files that are most relevant to backend_writers are

  matplotlib/backends/backend_your_backend.py
  matplotlib/backend_bases.py
  matplotlib/backends/__init__.py
  matplotlib/__init__.py
  matplotlib/_pylab_helpers.py

Naming Conventions

  * classes Upper or MixedUpperCase

  * varables lower or lowerUpper

  * functions lower or underscore_separated

"""

from __future__ import division, print_function

import matplotlib
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import RendererBase, GraphicsContextBase,\
     FigureManagerBase, FigureCanvasBase
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox


from galry import *


class RendererGalry(RendererBase):
    """
    The renderer handles drawing/rendering operations.

    This is a minimal do-nothing class that can be used to get started when
    writing a new backend. Refer to backend_bases.RendererBase for
    documentation of the classes methods.
    """
    def __init__(self, dpi):
        self.dpi = dpi

    def draw_path(self, gc, path, transform, rgbFace=None):
        pass

    # draw_markers is optional, and we get more correct relative
    # timings by leaving it out.  backend implementers concerned with
    # performance will probably want to implement it
#     def draw_markers(self, gc, marker_path, marker_trans, path, trans, rgbFace=None):
#         pass

    # draw_path_collection is optional, and we get more correct
    # relative timings by leaving it out. backend implementers concerned with
    # performance will probably want to implement it
#     def draw_path_collection(self, gc, master_transform, paths,
#                              all_transforms, offsets, offsetTrans, facecolors,
#                              edgecolors, linewidths, linestyles,
#                              antialiaseds):
#         pass

    # draw_quad_mesh is optional, and we get more correct
    # relative timings by leaving it out.  backend implementers concerned with
    # performance will probably want to implement it
#     def draw_quad_mesh(self, gc, master_transform, meshWidth, meshHeight,
#                        coordinates, offsets, offsetTrans, facecolors,
#                        antialiased, edgecolors):
#         pass

    def draw_image(self, gc, x, y, im):
        pass

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False):
        pass

    def flipy(self):
        return True

    def get_canvas_width_height(self):
        return 100, 100

    def get_text_width_height_descent(self, s, prop, ismath):
        return 1, 1, 1

    def new_gc(self):
        return GraphicsContextGalry()

    def points_to_pixels(self, points):
        # if backend doesn't have dpi, eg, postscript or svg
        return points
        # elif backend assumes a value for pixels_per_inch
        #return points/72.0 * self.dpi.get() * pixels_per_inch/72.0
        # else
        #return points/72.0 * self.dpi.get()


class GraphicsContextGalry(GraphicsContextBase):
    """
    The graphics context provides the color, line styles, etc...  See the gtk
    and postscript backends for examples of mapping the graphics context
    attributes (cap styles, join styles, line widths, colors) to a particular
    backend.  In GTK this is done by wrapping a gtk.gdk.GC object and
    forwarding the appropriate calls to it using a dictionary mapping styles
    to gdk constants.  In Postscript, all the work is done by the renderer,
    mapping line styles to postscript calls.

    If it's more appropriate to do the mapping at the renderer level (as in
    the postscript backend), you don't need to override any of the GC methods.
    If it's more appropriate to wrap an instance (as in the GTK backend) and
    do the mapping here, you'll need to override several of the setter
    methods.

    The base GraphicsContext stores colors as a RGB tuple on the unit
    interval, eg, (0.5, 0.0, 1.0). You may need to map this to colors
    appropriate for your backend.
    """
    pass


    
def _get_paint_manager(figure):
    raise Exception()
    return PaintManager
    
    

########################################################################
#
# The following functions and classes are for pylab and implement
# window/figure managers, etc...
#
########################################################################

def draw_if_interactive():
    """
    For image backends - is not required
    For GUI backends - this should be overriden if drawing should be done in
    interactive python mode
    """
    pass

def show():
    """
    For image backends - is not required
    For GUI backends - show() is usually the last line of a pylab script and
    tells the backend that it is time to draw.  In interactive mode, this may
    be a do nothing func.  See the GTK backend for an example of how to handle
    interactive versus batch mode
    """
    for manager in Gcf.get_all_fig_managers():
        # do something to display the GUI
        # show_basic_window()
        paint_manager = _get_paint_manager(manager.canvas.figure)
        print(paint_manager)

def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """
    # if a main-level app must be created, this (and
    # new_figure_manager_given_figure) is the usual place to
    # do it -- see backend_wx, backend_wxagg and backend_tkagg for
    # examples.  Not all GUIs require explicit instantiation of a
    # main-level app (egg backend_gtk, backend_gtkagg) for pylab
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)
    return new_figure_manager_given_figure(num, thisFig)


def new_figure_manager_given_figure(num, figure):
    """
    Create a new figure manager instance for the given figure.
    """
    canvas = FigureCanvasGalry(figure)
    manager = FigureManagerGalry(canvas, num)
    return manager


class FigureCanvasGalry(FigureCanvasBase):
    """
    The canvas the figure renders into.  Calls the draw and print fig
    methods, creates the renderers, etc...

    Public attribute

      figure - A Figure instance

    Note GUI templates will want to connect events for button presses,
    mouse movements and key presses to functions that call the base
    class methods button_press_event, button_release_event,
    motion_notify_event, key_press_event, and key_release_event.  See,
    eg backend_gtk.py, backend_wx.py and backend_tkagg.py
    """

    def draw(self):
        """
        Draw the figure using the renderer
        """
        renderer = RendererGalry(self.figure.dpi)
        self.figure.draw(renderer)

    # You should provide a print_xxx function for every file format
    # you can write.

    # If the file type is not in the base set of filetypes,
    # you should add it to the class-scope filetypes dictionary as follows:
    filetypes = FigureCanvasBase.filetypes.copy()
    filetypes['foo'] = 'My magic Foo format'

    def print_foo(self, filename, *args, **kwargs):
        """
        Write out format foo.  The dpi, facecolor and edgecolor are restored
        to their original values after this call, so you don't need to
        save and restore them.
        """
        pass

    def get_default_filetype(self):
        return 'foo'

class FigureManagerGalry(FigureManagerBase):
    """
    Wrap everything up into a window for the pylab interface

    For non interactive backends, the base class does all the work
    """
    pass

########################################################################
#
# Now just provide the standard names that backend.__init__ is expecting
#
########################################################################


FigureManager = FigureManagerGalry


########NEW FILE########
__FILENAME__ = backend_test


import matplotlib
matplotlib.use('module://backend_galry')


import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(-1., 1., 1000)
y = np.sin(20 * x)

plt.plot(x, y)
plt.show()


########NEW FILE########
__FILENAME__ = depth
import numpy as np
from galry import *

class DepthVisual(Visual):
    def initialize(self, position, color):
        self.size = position.shape[0]
        self.add_attribute('position', ndim=3, data=position)
        self.add_attribute('color', ndim=4, data=color)
        self.add_varying('vcolor', ndim=4)
        self.primitive_type = 'POINTS'
        self.depth_enabled = True
        self.add_vertex_main("""
        gl_PointSize = 100.;
        vcolor = color;
        """)
        self.add_fragment_main("""
        out_color = vcolor;
        """)

figure(activate3D=True)

position = np.zeros((10, 3))
position[:,0] = position[:,1] = np.linspace(-.5, .5, 10)
position[:,2] = np.linspace(0., 1., 10)

color = np.tile(np.linspace(0., 1., 10).reshape((-1, 1)), (1, 4))
color[:,-1] = 0.5
visual(DepthVisual, position, color)

show()


########NEW FILE########
__FILENAME__ = fbo
from galry import *
import pylab as plt
import numpy as np
import numpy.random as rdn
import time
import timeit
import os

# f = 2.




class ParticleVisual(Visual):
    def get_position_update_code(self):
        return """
        // update position
        position.x += velocities.x * tloc;
        position.y += velocities.y * tloc - 0.5 * g * tloc * tloc;
        """
        
    def get_color_update_code(self):
        return """
        // pass the color and point size to the fragment shader
        varying_color = color;
        varying_color.w = .20;
        """
    
    def base_fountain(self, initial_positions=None,
        velocities=None, color=None, delays=None, 
        ):
        
        self.size = initial_positions.shape[0]
        self.primitive_type = 'POINTS'
        # load texture
        path = os.path.dirname(os.path.realpath(__file__))
        particle = plt.imread(os.path.join(path, "../examples/images/particle.png"))
        
        size = float(max(particle.shape))
        
        # create the dataset
        self.add_uniform("point_size", vartype="float", ndim=1, data=size)
        self.add_uniform("t", vartype="float", ndim=1, data=0.)
        self.add_uniform("color", vartype="float", ndim=4, data=color)
        
        # add the different data buffers
        self.add_attribute("initial_positions", vartype="float", ndim=2, data=initial_positions)
        self.add_attribute("velocities", vartype="float", ndim=2, data=velocities)
        self.add_attribute("delays", vartype="float", ndim=1, data=delays)
        
        self.add_varying("varying_color", vartype="float", ndim=4)
        
        # add particle texture
        self.add_texture("tex", size=particle.shape[:2],
            ncomponents=particle.shape[2], ndim=2, data=particle)
            
        vs = """
        // compute local time
        const float tmax = 5.;
        const float tlocmax = 2.;
        const float g = %G_CONSTANT%;
        
        // Local time.
        float tloc = mod(t - delays, tmax);
        
        vec2 position = initial_positions;
        
        if ((tloc >= 0) && (tloc <= tlocmax))
        {
            // position update
            %POSITION_UPDATE%
            
            %COLOR_UPDATE%
        }
        else
        {
            varying_color = vec4(0., 0., 0., 0.);
        }
        
        gl_PointSize = point_size;
        """
            
        vs = vs.replace('%POSITION_UPDATE%', self.get_position_update_code())
        vs = vs.replace('%COLOR_UPDATE%', self.get_color_update_code())
        vs = vs.replace('%G_CONSTANT%', '3.')
            
        self.add_vertex_main(vs)    
        
        self.add_fragment_main(
        """
            vec4 col = texture2D(tex, gl_PointCoord) * varying_color;
            out_color = col;
        """)

    def initialize(self, **kwargs):
        self.base_fountain(**kwargs)

class MyVisual(Visual):
    def initialize(self, shape=None):
        if shape is None:
            shape = (600, 600)
        
        self.add_texture('singletex', ncomponents=3, ndim=2,
            shape=shape,
            data=np.zeros((shape[0], shape[1], 3))
            )
            
        self.add_texture('fulltex', ncomponents=3, ndim=2,
            shape=shape,
            data=np.zeros((shape[0], shape[1], 3))
            )
        
        points = (-1, -1, 1, 1)
        x0, y0, x1, y1 = points
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        
        position = np.zeros((4,2))
        position[0,:] = (x0, y0)
        position[1,:] = (x1, y0)
        position[2,:] = (x0, y1)
        position[3,:] = (x1, y1)
        
        tex_coords = np.zeros((4,2))
        tex_coords[0,:] = (0, 0)
        tex_coords[1,:] = (1, 0)
        tex_coords[2,:] = (0, 1)
        tex_coords[3,:] = (1, 1)
    
        self.size = 4
        self.primitive_type = 'TRIANGLE_STRIP'
        
        # texture coordinates
        self.add_attribute("tex_coords", vartype="float", ndim=2,
            data=tex_coords)
        self.add_varying("vtex_coords", vartype="float", ndim=2)
        
        self.add_attribute("position", vartype="float", ndim=2, data=position)
        self.add_vertex_main("""vtex_coords = tex_coords;""")
        
        FS = """
        vec4 out0 = texture2D(singletex, vtex_coords);
        vec4 out1 = texture2D(fulltex, vtex_coords);
        float a = .05;
        out_color = a * out0 + (1-a) * out1;
        if (out_color.x + out_color.y + out_color.z < .04)
            out_color = vec4(0, 0, 0, 0);
        """
        self.add_fragment_main(FS)
            
def update(figure, parameter):
    t = parameter[0]
    
    figure.set_data(t=t, visual='fountain')
    
    figure.copy_texture(RefVar('singlefbo', 'fbotex0'), 'singletex', visual='myvisual')
    figure.copy_texture(RefVar('fullfbo', 'fbotex0'), 'fulltex', visual='myvisual')

if __name__ == '__main__':
    
        
    # number of particles
    n = 50000

    # initial positions
    positions = .02 * rdn.randn(n, 2)

    # initial velocities
    velocities = np.zeros((n, 2))
    v = 1.5 + .5 * rdn.rand(n)
    angles = .1 * rdn.randn(n) + np.pi / 2
    velocities[:,0] = v * np.cos(angles)
    velocities[:,1] = v * np.sin(angles)

    # color
    color = (0.60,0.65,.98,1.)

    # random delays
    delays = 10 * rdn.rand(n)
    
    # # create the visual
    visual(ParticleVisual, 
        initial_positions=positions,
        velocities=velocities,
        color=color,
        delays=delays,
        is_static=True,
        name='fountain',
        )

    framebuffer(name='singlefbo', display=False)
    framebuffer(name='fullfbo', is_static=True)
        
    # # FBO #0 => #1
    visual(MyVisual, name='myvisual', framebuffer=1,
        is_static=True,)
    
    animate(update, dt=.01)

    show()


########NEW FILE########
__FILENAME__ = fireworks
from galry import *
import pylab as plt
import numpy as np
import numpy.random as rdn
import time
import timeit
import os

from OpenGL import GL as gl

class ParticleVisual(Visual):
    def get_position_update_code(self):
        return """
        // update position
        position.x += velocities.x * tloc;
        position.y += velocities.y * tloc - 0.5 * g * tloc * tloc;
        """
        
    def get_color_update_code(self):
        return """
        // pass the color and point size to the fragment shader
        varying_color = color;
        varying_color.w = alpha;
        """
    
    def base_fountain(self, initial_positions=None,
        velocities=None, color=None, alpha=None, delays=None):
        
        self.size = initial_positions.shape[0]
        self.primitive_type = 'POINTS'
        # load texture
        path = os.path.dirname(os.path.realpath(__file__))
        particle = plt.imread(os.path.join(path, "../examples/images/particle.png"))
        
        size = float(max(particle.shape))
        
        # create the dataset
        self.add_uniform("point_size", vartype="float", ndim=1, data=size)
        self.add_uniform("t", vartype="float", ndim=1, data=0.)
        self.add_uniform("color", vartype="float", ndim=4, data=color)
        
        # add the different data buffers
        self.add_attribute("initial_positions", vartype="float", ndim=2, data=initial_positions)
        self.add_attribute("velocities", vartype="float", ndim=2, data=velocities)
        self.add_attribute("delays", vartype="float", ndim=1, data=delays)
        self.add_attribute("alpha", vartype="float", ndim=1, data=alpha)
        
        self.add_varying("varying_color", vartype="float", ndim=4)
        
        # add particle texture
        self.add_texture("tex", size=particle.shape[:2],
            ncomponents=particle.shape[2], ndim=2, data=particle)
            
        vs = """
        // compute local time
        const float tmax = 5.;
        const float tlocmax = 2.;
        const float g = %G_CONSTANT%;
        
        // Local time.
        float tloc = mod(t - delays, tmax);
        
        vec2 position = initial_positions;
        
        if ((tloc >= 0) && (tloc <= tlocmax))
        {
            // position update
            %POSITION_UPDATE%
            
            %COLOR_UPDATE%
        }
        else
        {
            varying_color = vec4(0., 0., 0., 0.);
        }
        
        gl_PointSize = point_size;
        """
            
        vs = vs.replace('%POSITION_UPDATE%', self.get_position_update_code())
        vs = vs.replace('%COLOR_UPDATE%', self.get_color_update_code())
        vs = vs.replace('%G_CONSTANT%', '3.')
            
        # self.add_uniform('cycle', vartype='int', data=0)
            
        self.add_vertex_main(vs)    
        
        self.add_fragment_main(
        """
            vec4 col = texture2D(tex, gl_PointCoord) * varying_color;
            out_color = col;
        """)

    def initialize(self, **kwargs):
        self.base_fountain(**kwargs)

        
        
def update(figure, parameter):
    t = parameter[0]
    # if not hasattr(figure, 'cycle'):
        # figure.cycle = 0
    # figure.cycle = np.mod(figure.cycle + 1, 2)
    # figure.set_data(t=t, cycle=figure.cycle, visual='fountain')
    figure.set_data(t=t, visual='fountain')

if __name__ == '__main__':        
    figure()

    # number of particles
    n = 50000

    # initial positions
    positions = .02 * rdn.randn(n, 2)

    # initial velocities
    velocities = np.zeros((n, 2))
    v = 1.5 + .5 * rdn.rand(n)
    angles = .1 * rdn.randn(n) + np.pi / 2
    velocities[:,0] = v * np.cos(angles)
    velocities[:,1] = v * np.sin(angles)

    # transparency
    alpha = .2 * rdn.rand(n)

    # color
    color = (0.70,0.75,.98,1.)

    # random delays
    delays = 10 * rdn.rand(n)
    
    figure()
            
    # framebuffer(display=False)
    # framebuffer(name='sc', framebuffer=1)
    # imshow(RefVar('sc', 'fbotex0'), #points=(-.5,-.5,.5,.5),
    # # imshow(np.random.rand(4,4,4), points=(-.5,-.5,.5,.5),
        # is_static=True)#, beforeclear=True)
    
    # # create the visual
    visual(ParticleVisual, 
        initial_positions=positions,
        velocities=velocities,
        alpha=alpha,
        color=color,
        delays=delays,
        is_static=True,
        name='fountain',
        )

    # TODO: beginning: copy sc => prev.1
    framebuffer(ntextures=2, coeffs=[1., .9], framebuffer=1)
    framebuffer(name='sc')
        
    # imshow(RefVar('framebuffer', 'fbotex0'), points=(-.5,.5,.5,-.5),
    # # imshow(np.random.rand(4,4,4), points=(-.5,-.5,.5,.5),
        # is_static=True, framebuffer='screen')#, beforeclear=True)
    
    animate(update, dt=.02)

    show()


########NEW FILE########
__FILENAME__ = gallery
"""Display all images in a directory."""

import Image
import numpy as np
import os
import sys
from galry import *
from qtools import inthread, inprocess

# load an image
def load(file, size=None):
    img = Image.open(file)
    if size is not None:
        img.thumbnail((size, size))
    return np.array(img)

def get_aspect_ratio(image):
    hi, wi, _ = image.shape
    return float(wi) / hi


class Loader(object):
    def load(self, key, path):
        print "loading", key, path[-8:]
        img = load(path, 1366)
        return img
        
    @staticmethod
    def load_done(key=None, path=None, _result=None):
        CACHE[key] = _result


class Navigator(object):
    def __init__(self, n, steps):
        self.n = n
        self.steps = steps
        self.i = 0
        self.dir = 0
    
    def set(self, i):
        self.i = i
        self.dir = 0
    
    def next(self):
        if self.i < self.n - 1:
            self.i += 1
        self.dir = 1
        
    def previous(self):
        if self.i > 0:
            self.i -= 1
        self.dir = -1
    
    def current(self):
        return self.i
    
    def indices(self):
        steps = self.steps
        before = range(max(0, self.i - steps), self.i)
        after = range(self.i + 1, min(self.n - 1, self.i + steps) + 1)
        current = [self.i]
        if dir >= 0:
            return current + after + before
        else:
            return current + before + after
        
    
class PictureViewer(object):
    EMPTY = np.zeros((2, 2, 3))
    
    def __init__(self, folder=None):
        # get list of images in the folder
        if len(sys.argv) > 1:
            folder = sys.argv[1]
        else:
            folder = '.'
        self.folder = folder
        self.files = sorted(filter(lambda f: f.lower().endswith('.jpg'), os.listdir(folder)))
        self.cache = {}
        self.n = len(self.files)
        # Number of images to keep forward/backward in cache.
        self.steps = 2
        self.loader = inprocess(Loader)()
        self.nav = Navigator(self.n, self.steps)
        self.set_index(0)
        
    def set_index(self, i):
        self.nav.set(i)
        indices = self.nav.indices()
        paths = [(j, os.path.join(self.folder, self.files[j])) for j in indices 
            if j not in self.cache]# or self.cache[j] is None]
        # Tag keys that are being loaded so that they're not loaded once again.
        for j in indices:
            if j not in self.cache:
                self.cache[j] = None
        [self.loader.load(j, path) for j, path in paths]
    
    def next(self):
        self.nav.next()
        self.set_index(self.nav.current())
    
    def previous(self):
        self.nav.previous()
        self.set_index(self.nav.current())
    
    def current(self):
        return self[self.nav.current()]
    
    def __getitem__(self, key):
        img = self.cache.get(key, None)
        return img
        # if img is None:
            # return self.EMPTY
        # else:
            # return img
        
    def __setitem__(self, key, value):
        self.cache[key] = value
        

def show_image(figure, img):
    if img is None:
        return
    ar = get_aspect_ratio(img)
    figure.set_data(texture=img)
    figure.set_rendering_options(constrain_ratio=ar)
    figure.resizeGL(*figure.size)

def next(fig, params):
    pw.next()
    global CURRENT_IMAGE
    CURRENT_IMAGE = pw.current()
    show_image(fig, CURRENT_IMAGE)
    
def previous(fig, params):
    pw.previous()
    global CURRENT_IMAGE
    CURRENT_IMAGE = pw.current()
    show_image(fig, CURRENT_IMAGE)

def anim(fig, (t,)):
    global CURRENT_IMAGE
    image_last_loaded = pw.current()
    # Skip if current image in memory is None.
    if image_last_loaded is None or np.array_equal(image_last_loaded, pw.EMPTY):
        return
    # Update only if current displayed image is empty, and current image in
    # memory is not empty.
    if (CURRENT_IMAGE is None or np.array_equal(CURRENT_IMAGE, pw.EMPTY)):
        print "update"
        CURRENT_IMAGE = pw.current()
        show_image(fig, CURRENT_IMAGE)


if __name__ == '__main__':

    pw = PictureViewer()
    CACHE = pw.cache
    CURRENT_IMAGE = pw.EMPTY
        
    # create a figure and show the filtered image    
    figure(constrain_ratio=1, constrain_navigation=True, toolbar=False)
    imshow(np.zeros((2,2,3)), points=(-1., -1., 1., 1.), 
                mipmap=False,
                minfilter='LINEAR',
                magfilter='LINEAR')

    # previous/next images with keyboard
    action('KeyPress', previous, key='Left')
    action('KeyPress', next, key='Right')
    animate(anim, dt=.01)


    show()


    pw.loader.join()

########NEW FILE########
__FILENAME__ = gldebug
"""Debug script for finding out the OpenGL version.

Instructions:
  
  * run in a console:
  
        python gldebug.py
        
  * Send me the `galry_gldebug.txt` file created in the folder where
    you executed this script from.

"""
import os
import sys
import pprint

import numpy as np

from galry import *

# Capture stdout and stderr
class writer(object):
    log = []
    def write(self, data):
        self.log.append(data)
    def save(self, filename):
        with open(filename, 'w') as f:
            for line in self.log:
                f.write(line)

logger = writer()
sys.stdout = logger
sys.stderr = logger

class DebugVisual(PlotVisual):
    def initialize(self):
        super(DebugVisual, self).initialize(np.zeros(2))
        pprint.pprint(GLVersion.get_renderer_info())
        
figure(autodestruct=1)
visual(DebugVisual)
show()

filename = os.path.realpath('./galry_gldebug.txt')
logger.save(filename)


########NEW FILE########
__FILENAME__ = highlevel
# import galry.plot as plt
from galry import *
from galry.plot import PlotWidget

import numpy as np
import numpy.random as rdn

info_level()

widget = PlotWidget()

n = 1000
k = 3
X = np.linspace(-1., 1., n).reshape((1, -1))
X = np.tile(X, (k, 1))
Y = .1 * np.sin(20. * X)
Y += np.arange(k).reshape((-1, 1)) * .1

widget.paint_manager.add_plot(X, Y, color=['r1','y','b'])

win = create_basic_window(widget)
show_window(win)



# plt.figure()
# plt.subplot(121)  # LATER: subplot
# plt.text("Hello world",
        # x=0, # centered
        # y=1, # top
        # size=18, # font size
        # color='g',  # color
        # alpha=1.,  # transparency channel
        # bgcolor='w',  # background color
        # bgalpha=.5,  # background transparency
        # )
# # X and Y are NxM matrices
# plt.plot(X, Y,  # N plots
         # '-',  # style .-+xo
         # colors=colors,  # colors is a list of colors, one color for one line
         # size=5, # size of points or markers only
         # )

# plt.barplot(x, y, color='g')  # LATER
# plt.axes(0., 0.)  # LATER: display H/V data axes, going through that point
# plt.xlim(-1., 1.)  # LATER

# plt.show()  # data normalization happens here
########NEW FILE########
__FILENAME__ = load
import numpy as np
from galry import *
from galry.galryplot import GalryPlot

"""
%load_ext ipynbgalry
from IPython.display import display
from galry.galryplot import GalryPlot
a = GalryPlot()
display(a)
"""

# Python handler
def get_json(plot=None):
    """This function takes the displayed object and returns a JSON string
    which will be loaded by the Javascript handler."""
    return plot.serialize(handler='GalryPlotHandler')
    
_loaded = False

def load_ipython_extension(ip):
    """Load the extension in IPython."""
    global _loaded
    if not _loaded:
        # Get the formatter.
        mime = 'application/json'
        formatter = ip.display_formatter.formatters[mime]

        # Register handlers.
        # The first argument is the full module name where the class is defined.
        # The second argument is the class name.
        # The third argument is the Python handler that takes an instance of
        # this class, and returns a JSON string.
        formatter.for_type_by_name('galry.galryplot', 'GalryPlot', get_json)

        _loaded = True

    
########NEW FILE########
__FILENAME__ = generate_scene
from galry import *
s = SceneCreator()

x = np.linspace(-1., 1., 1000)
y = np.sin(20 * x) * .2 - .5

x = np.vstack((x, x))
y = np.vstack((y, y + 1))

color = np.array([[1., 0., 0., 1.],
                  [0., 0., 1., 1.]], dtype=np.float32)

s.add_visual(PlotVisual, x, y, color=color)
scene_json = s.serialize()

print type(scene_json)

# write JS file
# f = open('scene.js', 'w')
# f.write("scene_json = '%s';" % scene_json)
# f.close()


########NEW FILE########
__FILENAME__ = leap
from galry import *
from numpy import *

# create 10 discs
plot(zeros(10), zeros(10), 'o', ms=50, is_static=True)

# position of 10 fingers
fingers = zeros((10, 2))

def anim(fig, param):
    # print LEAP
    # return
    # retrive the Leap motion frame
    frame = LEAP['frame']
    # raise Exception()
    # update the finger positions
    fingers[:,:] = 10
    for i in xrange(len(frame.fingers)):
        pos = frame.fingers[i].tip_position
        x, y = pos.x / 255., pos.y / 255. - 1
        fingers[i,:] = (x, y)

    fig.set_data(position=fingers)

animate(anim, dt=.01)

show()


########NEW FILE########
__FILENAME__ = leapnav
from galry import *
from numpy import *

def get_pos(vec):
    return array((vec.x, vec.y, vec.z))

def get_hand_pos(hand):
    pos = get_pos(hand.palm_position)
    if hand.fingers:
        pos = array([get_pos(finger.tip_position) for finger in hand.fingers])
    return pos
    
figure(constrain_navigation=True)
plot(random.randn(10000))
ylim(-5, 5)

h = None
dh = None
dhnew = 0.

h_fil = zeros(3)
dh_fil = 0.
dt = .1
h2n = None

def anim(fig, param):
    frame = LEAP['frame']
    
    if not frame:
        return
    
    global h, dh, dhnew, h_fil, dh_fil, h2n
        
    if frame.hands[0].fingers:
        
        pos = get_hand_pos(frame.hands[0]) / 100.
        hnew = pos.mean(axis=0)
        # dhnew = mean(abs(pos - hnew).sum(axis=1))
    
        if len(frame.hands) >= 2:
            pos2 = get_hand_pos(frame.hands[1]) / 100.
            h2new = pos2.mean(axis=0)
            dhnew = sum(abs(h2new - hnew))
            if h2n is None:
                h2n = dhnew
            dhnew = dhnew - h2n
            # print dhnew, h2n
        else:
            dh = None
            h2n = None
            # dhnew = dh
            
    
        if h is None:
            h = hnew
        if dh is None:
            dh = dhnew
        
        h_ = hnew - h
        h[:] = hnew
        dh_ = dhnew - dh
        dh = dhnew

        # filtering
        h_fil = h_fil + dt * (-h_fil + h_)
        dh_fil = dh_fil + dt * (-dh_fil + dh_)

        pan = (h_fil[0], 0)
        fig.process_interaction('Pan', pan)
        
        zoom = (dh_fil, 0, 0, 0)
        fig.process_interaction('Zoom', zoom)
        
        
    else:
        h = None
        dh = None
    

animate(anim, dt=.02)

show()


########NEW FILE########
__FILENAME__ = plot
# import galry.plot as plt
from galry import *
import numpy as np

# fig = figure()

X = np.random.randn(2, 1000)

# fig.imshow(np.random.rand(10, 10, 4), is_static=True)

plot(X, color=['r', 'y'])
text("Hello world!", coordinates=(.0, .9), is_static=True)

def callback(figure, parameters):
    print figure, parameters
    
# action('LeftClick', 'MyEvent')
# event('MyEvent', callback)

action('LeftClick', callback)

show()


########NEW FILE########
__FILENAME__ = rainbow
from galry import *
import numpy as np
from matplotlib.colors import hsv_to_rgb

def colormap(x):
    """Colorize a 2D grayscale array.
    
    Arguments: 
      * x:an NxM array with values in [0,1] 
    
    Returns:
      * y: an NxMx3 array with a rainbow color palette.
    
    """
    x = np.clip(x, 0., 1.)
    
    # initial and final gradient colors, here rainbow gradient
    col0 = np.array([.67, .91, .65]).reshape((1, 1, -1))
    col1 = np.array([0., 1., 1.]).reshape((1, 1, -1))
    
    col0 = np.tile(col0, x.shape + (1,))
    col1 = np.tile(col1, x.shape + (1,))
    
    x = np.tile(x.reshape(x.shape + (1,)), (1, 1, 3))
    
    return hsv_to_rgb(col0 + (col1 - col0) * x)
    
figure(constrain_ratio=True, constrain_navigation=True)


n = 256
# create linear values as 2D texture
data = np.linspace(0., 1., n * n).reshape((n, n))
# colorize the texture
texture = colormap(data)
imshow(texture)


show()
########NEW FILE########
__FILENAME__ = surface
from galry import *
import numpy as np
from matplotlib.colors import hsv_to_rgb

def colormap(x):
    """Colorize a 2D grayscale array.
    
    Arguments: 
      * x:an NxM array with values in [0,1] 
    
    Returns:
      * y: an NxMx3 array with a rainbow color palette.
    
    """
    x = np.clip(x, 0., 1.)
    
    # initial and final gradient colors, here rainbow gradient
    col0 = np.array([.67, .91, .65]).reshape((1, 1, -1))
    col1 = np.array([0., 1., 1.]).reshape((1, 1, -1))
    
    col0 = np.tile(col0, x.shape + (1,))
    col1 = np.tile(col1, x.shape + (1,))
    
    x = np.tile(x.reshape(x.shape + (1,)), (1, 1, 3))
    
    return hsv_to_rgb(col0 + (col1 - col0) * x)

n = 300

# generate grid
x = np.linspace(-1., 1., n)
y = np.linspace(-1., 1., n)
X, Y = np.meshgrid(x, y)

# surface function
Z = .1*np.cos(10*X) * np.sin(10*Y)

# generate vertices positions
position = np.hstack((X.reshape((-1, 1)), Z.reshape((-1, 1)), Y.reshape((-1, 1)),))

#color
Znormalized = (Z - Z.min()) / (Z.max() - Z.min())
color = colormap(Znormalized).reshape((-1, 3))
color = np.hstack((color, np.ones((n*n,1))))

# normal
U = np.dstack((X[:,1:] - X[:,:-1],
               Y[:,1:] - Y[:,:-1],
               Z[:,1:] - Z[:,:-1]))
V = np.dstack((X[1:,:] - X[:-1,:],
               Y[1:,:] - Y[:-1,:],
               Z[1:,:] - Z[:-1,:]))
U = np.hstack((U, U[:,-1,:].reshape((-1,1,3))))
V = np.vstack((V, V[-1,:,:].reshape((1,-1,3))))
W = np.cross(U, V)
normal0 = W.reshape((-1, 3))
normal = np.zeros_like(normal0)
normal[:,0] = normal0[:,0]
normal[:,1] = normal0[:,2]
normal[:,2] = normal0[:,1]

# tesselation of the grid
index = []
for i in xrange(n-1):
    for j in xrange(n-1):
        index.extend([i*n+j, (i+1)*n+j, i*n+j+1,
                      (i+1)*n+j, i*n+j+1, (i+1)*n+j+1])
index = np.array(index)

# plot the mesh
mesh(position=position,
        normal=normal,
        color=color, 
        index=index,
        )

show()

########NEW FILE########
__FILENAME__ = thick
from galry import *
from numpy import *

n = 10000
x = linspace(-1., 1., n)

plot(x, np.sin(10*x), thickness=.02)

show()

########NEW FILE########
__FILENAME__ = vbosize
from PyQt4 import QtGui, QtCore, QtOpenGL
from PyQt4.QtOpenGL import QGLWidget
import OpenGL.GL as gl
# import OpenGL.arrays.vbo as glvbo

    
count = 10
samples = 5000000
N = count * samples


class GLPlotWidget(QGLWidget):
    width, height = 600, 600
    
    def set_data(self, data):
        self.data = data
        self.size = data.shape[0]
        self.color = np.array(np.ones((self.size, 4)), dtype=np.float32)
    
    def initializeGL(self):
        gl.glClearColor(0,0,0,0)
        self.vbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.data, gl.GL_DYNAMIC_DRAW)
        
        self.cbo = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.cbo)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, self.color, gl.GL_DYNAMIC_DRAW)
        
        self.count = count
        self.first = np.array(np.arange(0, self.size, samples), dtype=np.int32)
        self.counts = samples * np.ones(count, dtype=np.int32)
        
    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo)
        gl.glVertexPointer(2, gl.GL_FLOAT, 0, None)
        
        gl.glEnableClientState(gl.GL_COLOR_ARRAY)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.cbo)
        gl.glColorPointer(4, gl.GL_FLOAT, 0, None)
        
        gl.glMultiDrawArrays(gl.GL_LINE_STRIP, self.first, self.counts, self.count)
        
    def resizeGL(self, width, height):
        self.width, self.height = width, height
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(-1, 1, -1, 1, -1, 1)
        
if __name__ == '__main__':
    import sys
    import numpy as np
    import numpy.random as rdn

    class TestWindow(QtGui.QMainWindow):
        def __init__(self):
            super(TestWindow, self).__init__()
            data = .05 * np.array(rdn.randn(1, 2), dtype=np.float32)
            data = np.tile(data, (N, 1))
            data[-1,:] += .5
            self.widget = GLPlotWidget()
            self.widget.set_data(data)
            self.setGeometry(100, 100, self.widget.width, self.widget.height)
            self.setCentralWidget(self.widget)
            self.show()
    
    app = QtGui.QApplication(sys.argv)
    window = TestWindow()
    window.show()
    app.exec_()
    
########NEW FILE########
__FILENAME__ = wave
from galry import *
import numpy as np

n = 100

# normal: (df/dx, df/dy, -1)

surface(np.zeros((n, n)), vertex_shader="""
float t = ambient_light;

// convert the position from 3D to 4D.
gl_Position = vec4(position, 1.0);
float x = position.x;
float y = position.z;

float c = .1;
float d = 10;
float r = sqrt(x*x+y*y);
float u = mod(t*.5, 6.28/d);
float z = c * cos(d*(r-u));
float tmp = -d*sin(d*(r-u))*(-1/r);
float dx = tmp*x;
float dy = tmp*y;

vec3 normal2 = vec3(c*dx, 1, c*dy);
vec4 color2 = vec4((x+1)/2, (y+1)/2, (z+1)/2,1);
//color2.xyz = normal2;

gl_Position.y = z;

// compute the amount of light
float light = dot(light_direction, normalize(mat3(camera) * mat3(transform) * normal2));
//light = clamp(light, 0, 1);
light = abs(clamp(light, -1, 1));
// add the ambient term
light = clamp(.25 + light, 0, 1);

// compute the final color
varying_color = color2 * light;

// keep the transparency
varying_color.w = color2.w;
""")

def anim(fig, t):
    fig.set_data(ambient_light=t[0])

animate(anim, dt=.02)

show()

########NEW FILE########
__FILENAME__ = bindingmanager
from qtools.qtpy import QtCore, QtGui
from qtools.qtpy.QtCore import Qt 
from galry import Manager, ordict
import numpy as np


__all__ = ['BindingManager', 'Bindings']


class BindingManager(Manager):
    """Manager several sets of bindings (or interaction modes) and allows
    to switch between several modes.
    """
    def reset(self):
        """Reset the modes."""
        self.bindings = []
        self.index = 0
    
    def add(self, *bindings):
        """Add one or several bindings to the binding manager.
        
        Arguments:
          * bindings: a list of classes deriving from UserActionBinding.
          
        """
        bindings = [b for b in bindings if b not in self.bindings]
        self.bindings.extend(bindings)
        
    def remove(self, binding):
        """Remove a binding.
        
        Arguments:
          * binding: the binding to remove.
          
        """
        if binding in self.bindings:
            self.bindings.remove(binding)
            
    def set(self, binding):
        """Set the given binding as the active one.
        
        Arguments:
          * binding: the current binding.
          
        """
        if not isinstance(binding, Bindings):
            # here, we assume that binding is a class, so we take the first
            # existing binding that is an instance of this class
            binding = [b for b in self.bindings if isinstance(b, binding)][0]
        self.add(binding)
        self.index = self.bindings.index(binding)
        return self.get()
            
    def get(self):
        """Return the current binding."""
        if self.index < len(self.bindings):
            return self.bindings[self.index]
        else:
            return None
            
    def switch(self):
        """Switch the active binding. The bindings cycle through all bindings.
        
        """
        self.index = np.mod(self.index + 1, len(self.bindings))
        return self.get()
  
  
class Bindings(object):
    """Base class for action-events bindings set.
    
    An instance of this class contains all bindings between user actions, and
    interaction events, that are possible within a given interaction mode. 
    An interaction mode is entirely defined by such set of bindings.
    The GalryWidget provides a mechanism for switching between successive
    modes.
    
    """
    def __init__(self):
        self.base_cursor = 'ArrowCursor'
        self.text = None
        self.binding = ordict()
        self.descriptions = ordict()
        self.initialize_default()
        self.initialize()
        
    def set_base_cursor(self, cursor=None):
        """Define the base cursor in this mode."""
        if cursor is None:
            cursor = 'OpenHandCursor'
        # set the base cursor
        self.base_cursor = cursor

    def get_base_cursor(self):
        return self.base_cursor
        
    def initialize_default(self):
        """Set bindings that are common to any interaction mode."""
        self.set('KeyPress', 'SwitchInteractionMode', key='I')
        
    def initialize(self):
        """Registers all bindings through commands to self.set().
        
        To be overriden.
        
        """
        pass
        
    def set(self, action, event, key_modifier=None, key=None,
                            param_getter=None, description=None):
        """Register an action-event binding.
        
        Arguments:
          * action: a UserAction string.
          * event: a InteractionEvent string.
          * key_modifier=None: the key modifier as a string.
          * key=None: when the action is KeyPress, the key that was 
            pressed.
          * param_getter=None: a function that takes an ActionParameters dict 
            as argument and returns a parameter object that will be passed 
            to InteractionManager.process_event(event, parameter)
            
        """
        if isinstance(key, basestring):
            key = getattr(Qt, 'Key_' + key)
        if isinstance(key_modifier, basestring):
            key_modifier = getattr(Qt, 'Key_' + key_modifier)
        # if param_getter is a value and not a function, we convert it
        # to a constant function
        if not hasattr(param_getter, '__call__'):
            param = param_getter
            param_getter = lambda p: param
        self.binding[(action, key_modifier, key)] = (event, param_getter)
        if description:
            self.descriptions[(action, key_modifier, key)] = description
        
    def get(self, action, key_modifier=None, key=None):
        """Return the event and parameter getter function associated to
        a function.
        
        Arguments:
          * action: the user action.
          * key_modifier=None: the key modifier.
          * key=None: the key if the action is `KeyPress`.
          
        """
        return self.binding.get((action, key_modifier, key), (None, None))
    
    def get_description(self, action, key_modifier=None, key=None):
        return self.descriptions.get((action, key_modifier, key), None)
    
    
    # Help methods
    # ------------
    def generate_text(self):
        special_keys = {
            None: '',
            QtCore.Qt.Key_Control: 'CTRL',
            QtCore.Qt.Key_Shift: 'SHIFT',
            QtCore.Qt.Key_Alt: 'ALT',
        }
        
        texts = {}
        for (action, key_modifier, key), (event, _) in self.binding.iteritems():
            desc = self.get_description(action, key_modifier, key)
            
            # key string
            if key:
                key = QtGui.QKeySequence(key).toString()
            else:
                key = ''
            
            # key modifier
            key_modifier = special_keys[key_modifier]
            if key_modifier:
                key_modifier = key_modifier + ' + '

            # get binding text
            if action == 'KeyPress':
                bstr = 'Press ' + key_modifier + key + ' : ' + event
            else:
                bstr = key_modifier + action + ' : ' + event
            
            if desc:
                bstr += ' ' + desc
            
            if event not in texts:
                texts[event] = []
            texts[event].append(bstr)
            
        # sort events
        self.text = "\n".join(["\n".join(sorted(texts[key])) for key in sorted(texts.iterkeys())])
        
    def get_text(self):
        if not self.text:
            self.generate_text()
        return self.text
    
    def __repr__(self):
        return self.get_text()
    
    
########NEW FILE########
__FILENAME__ = colors
import re
import numpy as np

__all__ = ['get_color', 'get_next_color']

HEX = '0123456789abcdef'
HEX2 = dict((a+b, (HEX.index(a)*16 + HEX.index(b)) / 255.) \
             for a in HEX for b in HEX)

def rgb(triplet):
    triplet = triplet.lower()
    if triplet[0] == '#':
        triplet = triplet[1:]
    if len(triplet) == 6:
        return (HEX2[triplet[0:2]], HEX2[triplet[2:4]], HEX2[triplet[4:6]],
                1.)
    elif len(triplet) == 8:
        return (HEX2[triplet[0:2]], HEX2[triplet[2:4]], HEX2[triplet[4:6]],
                HEX2[triplet[6:8]])

def triplet(rgb):
    return format((rgb[0]<<16)|(rgb[1]<<8)|rgb[2], '06x')

BASIC_COLORS_STRING = "rgbcymkw"
BASIC_COLORS = [
    (1., 0., 0.),
    (0., 1., 0.),
    (0., 0., 1.),
    (0., 1., 1.),
    (1., 1., 0.),
    (1., 0., 1.),
    (0., 0., 0.),
    (1., 1., 1.),
]
COLORMAP = [4, 1, 0, 3, 2, 5]

def get_next_color(i):
    return BASIC_COLORS[COLORMAP[np.mod(i, 6)]]

def get_basic_color(color):
    col = BASIC_COLORS[BASIC_COLORS_STRING.index(color)]
    return col + (1.,)
    
def get_basic_color_alpha(color):
    r = re.match("([a-z])([0-9\.]*)", color)
    if r is not None:
        col, alpha = r.groups()
        col = BASIC_COLORS[BASIC_COLORS_STRING.index(col)]
        return col + (float(alpha),)

def get_hexa_color(color):
    return rgb(color)
    
PATTERNS = {
    '^[a-z]{1}$': get_basic_color,
    '^[a-z]{1}[0-9\.]*$': get_basic_color_alpha,
    '^[#a-z0-9]{6,9}$': get_hexa_color,
}
  
def get_color(color):
    """Return a color RGBA normalized coefficients from any of the following
    possible inputs:
      * (r, g, b) or (r, g, b, a) with r, g, b, a between 0 and 1.
      * a string with one of the following characters: rgbcymkw for the
        primary colors, and optionnaly a floating number between 0 and 1 for 
        the alpha channel, ie 'r.75' for red at 75%.
      * a string with an hexadecimal code.
      * a list of colors
    
    """
    if type(color) == int:
        color = get_next_color(color)
    if isinstance(color, basestring):
        color = color.lower()
        for pattern, fun in PATTERNS.iteritems():
            r = re.match(pattern, color)
            if r is not None:
                break
        return fun(color)
    elif type(color) is tuple:
        assert color
        if len(color) == 3:
            color = color + (1.,)
        assert len(color) == 4
        return color
    elif type(color) is list:
        assert color
        if color and (type(color[0]) != tuple) and (3 <= len(color) <= 4):
            color = tuple(color)
        return map(get_color, color)
    else:
        return color

if __name__ == '__main__':
    
    print get_color(['r','y.5'])
    
   


########NEW FILE########
__FILENAME__ = cursors
from qtools.qtpy.QtCore import Qt 
from qtools.qtpy import QtGui, QT_BINDING, QT_BINDING_VERSION
import os

__all__ = ['get_cursor']

getpath = lambda file: os.path.join(os.path.dirname(__file__), file)

# HACK: cursors bug on Linux + PySide <= 1.1.1
if QT_BINDING == 'pyside' and QT_BINDING_VERSION <= '1.1.1':
    def get_cursor(name):
        return None
else:
    def get_cursor(name):
        if name is None:
            name = 'ArrowCursor'
        if name == 'MagnifyingGlassCursor':
            MagnifyingGlassPixmap = QtGui.QPixmap(getpath("cursors/glass.png"))
            MagnifyingGlassPixmap.setMask(QtGui.QBitmap(\
                                          QtGui.QPixmap(getpath("cursors/glassmask.png"))))
            MagnifyingGlassCursor = QtGui.QCursor(MagnifyingGlassPixmap)
            return MagnifyingGlassCursor
        else:
            return QtGui.QCursor(getattr(Qt, name))
        
########NEW FILE########
__FILENAME__ = datanormalizer
import numpy as np

__all__ = ['DataNormalizer']

class DataNormalizer(object):
    """Handles normalizing data so that it fits the fixed [-1,1]^2 viewport."""
    def __init__(self, data=None):
        self.data = data
    
    def normalize(self, initial_viewbox=None, symmetric=False):
        """Normalize data given the initial view box.
        
        This function also defines the four following methods:
          * `(un)normalize_[x|y]`: normalize or un-normalize in the x or y
            dimension. Un-normalization can be useful for e.g. retrieving the
            original coordinates of a point in the window.
        
        Arguments:
          * initial_viewbox=None: the initial view box is a 4-tuple
            (x0, y0, x1, y1) describing the initial view of the data and
            defining the normalization. By default, it is the bounding box of the
            data (min/max x/y). x0 and/or y0 can be None, meaning no
            normalization for that dimension.
        
        Returns:
          * normalized_data: the normalized data.
        
        """
        if not initial_viewbox:
            initial_viewbox = (None, None, None, None)
        dx0, dy0, dx1, dy1 = initial_viewbox
        
        if self.data is not None:
            x, y = self.data[:,0], self.data[:,1]
            # default: replace None by min/max
            if self.data.size == 0:
                dx0 = dy0 = dx1 = dy1 = 0.
            else:
                if dx0 is None:
                    dx0 = x.min()
                if dy0 is None:
                    dy0 = y.min()
                if dx1 is None:
                    dx1 = x.max()
                if dy1 is None:
                    dy1 = y.max()
        else:
            if dx0 is None:
                dx0 = -1.
            if dy0 is None:
                dy0 = -1.
            if dx1 is None:
                dx1 = 1.
            if dy1 is None:
                dy1 = 1.
            
        if dx0 == dx1:
            dx0 -= .5
            dx1 += .5
        if dy0 == dy1:
            dy0 -= .5
            dy1 += .5
        
        # force a symmetric viewbox
        if symmetric:
            vx = max(np.abs(dx0), np.abs(dx1))
            vy = max(np.abs(dy0), np.abs(dy1))
            dx0, dx1 = -vx, vx
            dy0, dy1 = -vy, vy
            
        if dx0 is None:
            self.normalize_x = self.unnormalize_x = lambda X: X
        else:
            self.normalize_x = lambda X: -1+2*(X-dx0)/(dx1-dx0)
            self.unnormalize_x = lambda X: dx0 + (dx1 - dx0) * (1+X)/2.
        if dy0 is None:
            self.normalize_y = self.unnormalize_y = lambda Y: Y
        else:
            self.normalize_y = lambda Y: -1+2*(Y-dy0)/(dy1-dy0)
            self.unnormalize_y = lambda Y: dy0 + (dy1 - dy0) * (1+Y)/2.
            
        if self.data is not None:
            data_normalized = np.empty(self.data.shape, dtype=self.data.dtype)
            data_normalized[:,0] = self.normalize_x(x)
            data_normalized[:,1] = self.normalize_y(y)
            return data_normalized
        
        
########NEW FILE########
__FILENAME__ = debugtools
import logging
import os.path
import traceback
import sys

# Debug switch.
DEBUG = False

__all__ = ['log_debug', 'log_info', 'log_warn',
           'debug_level', 'info_level', 'warning_level',
           'DEBUG']

def setup_logging(level):
    """Set the logging level among debug, info, warn."""
    if level == logging.DEBUG:
        logging.basicConfig(level=level,
                            format="%(asctime)s,%(msecs)03d  \
%(levelname)-7s  %(message)s",
                            datefmt='%H:%M:%S')
    else:
        logging.basicConfig(level=level,
                            # stream=sys.stdout,
                            format="%(levelname)-7s:  %(message)s")
    return logging.getLogger('galry')

def get_caller():
    """Return the line and module of the caller function."""
    tb = traceback.extract_stack()[-3]
    module = os.path.splitext(os.path.basename(tb[0]))[0].ljust(18)
    line = str(tb[1]).ljust(4)
    return "L:%s  %s" % (line, module)

    
# Logging methods
# ---------------
def log_debug(obj):
    """Debug log."""
    if level == logging.DEBUG:
        string = str(obj)
        string = get_caller() + string
        logger.debug(string)
        
def log_info(obj):
    """Info log."""
    if level == logging.DEBUG:
        obj = get_caller() + str(obj)
    logger.info(obj)

def log_warn(obj):
    """Warn log."""
    if level == logging.DEBUG:
        obj = get_caller() + str(obj)
    logger.warn(obj)

    
# Logging level methods
# ---------------------
def debug_level():
    logger.setLevel(logging.DEBUG)

def info_level():
    logger.setLevel(logging.INFO)

def warning_level():
    logger.setLevel(logging.WARNING)

# default level
if DEBUG:
    level = logging.DEBUG
else:
    level = logging.WARNING
logger = setup_logging(level)
logger.setLevel(level)
# DEBUG
# info_level()


if __name__ == '__main__':
    log_debug("hello world")
    log_info("hello world")

########NEW FILE########
__FILENAME__ = galrywidget
import sys
import os
import re
import time
import timeit
import numpy as np
import numpy.random as rdn
from qtools.qtpy import QtCore, QtGui
from qtools.qtpy.QtCore import Qt, pyqtSignal
from qtools import show_window
from galry import DEBUG, log_debug, log_info, log_warn
try:
    from qtools.qtpy.QtOpenGL import QGLWidget, QGLFormat
except Exception as e:
    log_warn((("The Qt-OpenGL bindings are not available. "
    "On Ubuntu, please install python-qt4-gl (PyQt4) or "
    "python-pyside.qtopengl (PySide). "
    "Original exception was: %s" % e)))
    # mock QGLWidget
    class QGLWidget(QtGui.QWidget):
        def initializeGL(self):
            pass
        def paintGL(self):
            pass
        def updateGL(self):
            pass
        def resizeGL(self):
            pass
    QGLFormat = None
from galry import get_cursor, FpsCounter, PaintManager, \
    InteractionManager, BindingManager, \
    UserActionGenerator, PlotBindings, Bindings, FpsCounter, \
    show_window, get_icon

__all__ = [
'GalryWidget',
'GalryTimerWidget',
'AutodestructibleWindow',
'create_custom_widget',
'create_basic_window',
'show_basic_window',
]

# # DEBUG: raise errors if Numpy arrays are unnecessarily copied
# from OpenGL.arrays import numpymodule
# try:
    # numpymodule.NumpyHandler.ERROR_ON_COPY = True
# except Exception as e:
    # print "WARNING: unable to set the Numpy-OpenGL copy warning"

# Set to True or to a number of milliseconds to have all windows automatically
# killed after a fixed time. It is useful for automatic debugging or
# benchmarking.
AUTODESTRUCT = False
DEFAULT_AUTODESTRUCT = 1000

# Display the FPS or not.
DISPLAY_FPS = DEBUG == True

# Default manager classes.
DEFAULT_MANAGERS = dict(
    paint_manager=PaintManager,
    binding_manager=BindingManager,
    interaction_manager=InteractionManager,
)



# Main Galry class.
class GalryWidget(QGLWidget):
    """Efficient interactive 2D visualization widget.
    
    This QT widget is based on OpenGL and depends on both PyQT (or PySide)
    and PyOpenGL. It implements low-level mechanisms for interaction processing
    and acts as a glue between the different managers (PaintManager, 
    BindingManager, InteractionManager).
    
    """
    
    w = 600.
    h = 600.
    
    # Initialization methods
    # ----------------------
    def __init__(self, format=None, autosave=None, getfocus=True, **kwargs):
        """Constructor. Call `initialize` and initialize the companion classes
        as well."""
        if format is not None:
            super(GalryWidget, self).__init__(format)
        else:
            super(GalryWidget, self).__init__()
        
        self.initialized = False
        self.just_initialized = False
        
        self.i = 0
        
        # background color as a 4-tuple (R,G,B,A)
        self.bgcolor = (0, 0, 0, 0)
        self.autosave = None
        
        # default window size
        # self.width, self.height = 600, 600
        
        # FPS counter, used for debugging
        self.fps_counter = FpsCounter()
        self.display_fps = DISPLAY_FPS
        self.activate3D = None

        # widget creation parameters
        self.bindings = None
        self.companion_classes_initialized = False
        
        # constrain width/height ratio when resizing of zooming
        self.constrain_ratio = False
        self.constrain_navigation = False
        self.momentum = False
        self.activate_help = True
        self.activate_grid = False
        self.block_refresh = False
        
        # Capture keyboard events.
        if getfocus:
            self.setFocusPolicy(Qt.WheelFocus)
        
        # Capture mouse events.
        self.setMouseTracking(True)
        
        # Capture touch events.
        self.setAcceptTouchEvents = True
        self.grabGesture(QtCore.Qt.PinchGesture)
        self.mouse_blocked = False  # True during a pinch gesture
        
        # Initialize the objects providing the core features of the widget.
        self.user_action_generator = UserActionGenerator()
        
        self.is_fullscreen = False
        
        self.events_to_signals = {}
        
        # keyword arguments without "_manager" => passed to initialize                  
        self.initialize(**kwargs)
        
        # initialize companion classes if it has not been done in initialize
        if not self.companion_classes_initialized:
            self.initialize_companion_classes()
        self.initialize_bindings()
        
        # update rendering options
        self.paint_manager.set_rendering_options(
                        activate3D=self.activate3D,
                        constrain_ratio=self.constrain_ratio,
                        )
        
        self.autosave = autosave
        
    def set_bindings(self, *bindings):
        """Set the interaction mode by specifying the binding object.
        
        Several binding objects can be given for the binding manager, such that
        the first one is the currently active one.
        
        Arguments:
          * bindings: a list of classes instances deriving from
            Bindings.
            
        """
        bindings = list(bindings)
        if not bindings:
            bindings = [PlotBindings()]
        # if type(bindings) is not list and type(bindings) is not tuple:
            # bindings = [bindings]
        # if binding is a class, try instanciating it
        for i in xrange(len(bindings)):
            if not isinstance(bindings[i], Bindings):
                bindings[i] = bindings[i]()
        self.bindings = bindings
        
    def set_companion_classes(self, **kwargs):
        """Set specified companion classes, unspecified ones are set to
        default classes.
        
        Arguments:
          * **kwargs: the naming convention is: `paint_manager=PaintManager`.
            The key `paint_manager` is the name the manager is accessed from 
            this widget and from all other companion classes. The value
            is the name of the class, it should end with `Manager`.
        
        """
        if not hasattr(self, "companion_classes"):
            self.companion_classes = {}
            
        self.companion_classes.update(kwargs)
        
        # default companion classes
        self.companion_classes.update([(k,v) for k,v in \
            DEFAULT_MANAGERS.iteritems() if k not in self.companion_classes])
        
    def initialize_bindings(self):
        """Initialize the interaction bindings."""
        if self.bindings is None:
            self.set_bindings()
        self.binding_manager.add(*self.bindings)
        
    def initialize_companion_classes(self):
        """Initialize companion classes."""
        # default companion classes
        if not getattr(self, "companion_classes", None):
            self.set_companion_classes()
        
        # create the managers
        for key, val in self.companion_classes.iteritems():
            log_debug("Initializing '%s'" % key)
            obj = val(self)
            setattr(self, key, obj)
        
        # link all managers
        for key, val in self.companion_classes.iteritems():
            for child_key, child_val in self.companion_classes.iteritems():
                # no self-reference
                if child_key == key:
                    continue
                obj = getattr(self, key)
                setattr(obj, child_key, getattr(self, child_key))
        
        self.interaction_manager.constrain_navigation = self.constrain_navigation        
        self.companion_classes_initialized = True
        
    def initialize(self, **kwargs):
        """Initialize the widget.
        
        Parameters such as bindings, companion_classes can be
        set here, by overriding this method. If initializations must be done
        after companion classes instanciation, then
        self.initialize_companion_classes can be called here.
        Otherwise, it will be called automatically after initialize().
        
        """
        pass
        
    def clear(self):
        """Clear the view."""
        self.paint_manager.reset()
        
    def reinit(self):
        """Reinitialize OpenGL.
        
        The clear method should be called before.
        
        """
        self.initializeGL()
        self.resizeGL(self.w, self.h)
        self.updateGL()
        
        
    # OpenGL widget methods
    # ---------------------
    def initializeGL(self):
        """Initialize OpenGL parameters."""
        self.paint_manager.initializeGL()
        self.initialized = True
        self.just_initialized = True
        
    def paintGL(self):
        """Paint the scene.
        
        Called as soon as the window needs to be painted (e.g. call to 
        `updateGL()`).
        
        This method calls the `paint_all` method of the PaintManager.
        
        """
        if self.just_initialized:
            self.process_interaction('Initialize', do_update=False)
        # paint fps
        if self.display_fps:
            self.paint_fps()
        # paint everything
        self.paint_manager.paintGL()
        # compute FPS
        self.fps_counter.tick()
        if self.autosave:
            if '%' in self.autosave:
                autosave = self.autosave % self.i
            else:
                autosave = self.autosave
            self.save_image(autosave, update=False)
        self.just_initialized = False
        self.i += 1
        
    def paint_fps(self):
        """Display the FPS on the top-left of the screen."""
        self.paint_manager.update_fps(int(self.fps_counter.get_fps()))
        
    def resizeGL(self, width, height):
        self.w, self.h = width, height
        self.paint_manager.resizeGL(width, height)
        
    def sizeHint(self):
        return QtCore.QSize(self.w, self.h)
        
        
    # Event methods
    # -------------
    def event(self, e):
        r = super(GalryWidget, self).event(e)
        if e.type() == QtCore.QEvent.Gesture:
            e.accept()
            gesture = e.gesture(QtCore.Qt.PinchGesture)
            self.pinchEvent(gesture)
            if gesture.state() == Qt.GestureStarted:
                self.mouse_blocked = True
            elif gesture.state() == Qt.GestureFinished:
                self.mouse_blocked = False
            return False
        return r
    
    def pinchEvent(self, e):
        self.user_action_generator.pinchEvent(e)
        self.process_interaction()
    
    def mousePressEvent(self, e):
        if self.mouse_blocked:
            return
        self.user_action_generator.mousePressEvent(e)
        self.process_interaction()
        
    def mouseReleaseEvent(self, e):
        if self.mouse_blocked:
            return
        self.user_action_generator.mouseReleaseEvent(e)
        self.process_interaction()
        
    def mouseDoubleClickEvent(self, e):
        if self.mouse_blocked:
            return
        self.user_action_generator.mouseDoubleClickEvent(e)
        self.process_interaction()
        
    def mouseMoveEvent(self, e):
        if self.mouse_blocked:
            return
        self.user_action_generator.mouseMoveEvent(e)
        self.process_interaction()
        
    def keyPressEvent(self, e):
        self.user_action_generator.keyPressEvent(e)
        self.process_interaction()
        # Close the application when pressing Q
        if e.key() == QtCore.Qt.Key_Q:
            if hasattr(self, 'window'):
                self.close_widget()
        
    def keyReleaseEvent(self, e):
        self.user_action_generator.keyReleaseEvent(e)
        
    def wheelEvent(self, e):
        self.user_action_generator.wheelEvent(e)
        self.process_interaction()
        
    def reset_action_generator(self):
        self.user_action_generator.reset()
        
    def leaveEvent (self, e):
        self.process_interaction(None)
        
        
    # Normalization methods
    # ---------------------
    def normalize_position(self, x, y):
        """Window coordinates ==> world coordinates."""
        if not hasattr(self.paint_manager, 'renderer'):
            return (0, 0)
        vx, vy = self.paint_manager.renderer.viewport
        x = -vx + 2 * vx * x / float(self.w)
        y = -(-vy + 2 * vy * y / float(self.h))
        return x, y
             
    def normalize_diff_position(self, x, y):
        """Normalize the coordinates of a difference vector between two
        points.
        """
        if not hasattr(self.paint_manager, 'renderer'):
            return (0, 0)
        vx, vy = self.paint_manager.renderer.viewport
        x = 2 * vx * x/float(self.w)
        y = -2 * vy * y/float(self.h)
        return x, y
        
    def normalize_action_parameters(self, parameters):
        """Normalize points in the action parameters object in the window
        coordinate system.
        
        Arguments:
          * parameters: the action parameters object, containing all
            variables related to user actions.
            
        Returns:
           * parameters: the updated parameters object with normalized
             coordinates.
             
        """
        parameters["mouse_position"] = self.normalize_position(\
                                                *parameters["mouse_position"])
        parameters["mouse_position_diff"] = self.normalize_diff_position(\
                                            *parameters["mouse_position_diff"])
        parameters["mouse_press_position"] = self.normalize_position(\
                                            *parameters["mouse_press_position"])
        parameters["pinch_position"] = self.normalize_position(\
                                            *parameters["pinch_position"])
        parameters["pinch_start_position"] = self.normalize_position(\
                                            *parameters["pinch_start_position"])
        return parameters
    
    
    # Signal methods
    # --------------
    def connect_events(self, arg1, arg2):
        """Makes a connection between a QT signal and an interaction event.
        
        The signal parameters must correspond to the event parameters.
        
        Arguments:
          * arg1: a QT bound signal or an interaction event.
          * arg2: an interaction event or a QT bound signal.
        
        """
        if type(arg1) == str:
            self.connect_event_to_signal(arg1, arg2)
        elif type(arg2) == str:
            self.connect_signal_to_event(arg1, arg2)
    
    def connect_signal_to_event(self, signal, event):
        """Connect a QT signal to an interaction event.
        
        The event parameters correspond to the signal parameters.
        
        Arguments:
          * signal: a QT signal.
          * event: an InteractionEvent string.
        
        """
        if signal is None:
            raise Exception("The signal %s is not defined" % signal)
        slot = lambda *args, **kwargs: \
                self.process_interaction(event, args, **kwargs)
        signal.connect(slot)
        
    def connect_event_to_signal(self, event, signal):
        """Connect an interaction event to a QT signal.
        
        The event parameters correspond to the signal parameters.
        
        Arguments:
          * event: an InteractionEvent string.
          * signal: a QT signal.
        
        """
        self.events_to_signals[event] = signal
        
        
    # Binding mode methods
    # --------------------
    def switch_interaction_mode(self):
        """Switch the interaction mode."""
        binding = self.binding_manager.switch()
        # set base cursor
        # self.interaction_manager.base_cursor = binding.base_cursor
        return binding
    
    def set_interaction_mode(self, mode):
        """Set the interaction mode.
        
        Arguments:
          * mode: either a class deriving from `Bindings` and which has been
            specified in `set_bindings`, or directly a `Bindings` instance.
        
        """
        binding = self.binding_manager.set(mode)
        # set base cursor
        # self.interaction_manager.base_cursor = binding.base_cursor
        return binding
        
        
    # Interaction methods
    # -------------------
    def get_current_action(self):
        """Return the current user action with the action parameters."""
        # get current action
        action = self.user_action_generator.action
        
        # get current key if the action was KeyPress
        key = self.user_action_generator.key
        
        # get key modifier
        key_modifier = self.user_action_generator.key_modifier
        
        # retrieve action parameters and normalize using the window size
        parameters = self.normalize_action_parameters(
                        self.user_action_generator.get_action_parameters())
        return action, key, key_modifier, parameters
        
    def get_current_event(self):
        """Return the current interaction event corresponding to the current
        user action."""
        # get the current interaction mode
        binding = self.binding_manager.get()
        
        # get current user action
        action, key, key_modifier, parameters = self.get_current_action()
        
        # get the associated interaction event
        event, param_getter = binding.get(action, key=key,
                                                  key_modifier=key_modifier)
        
        # get the parameter object by calling the param getter
        if param_getter is not None and parameters is not None:
            args = param_getter(parameters)
        else:
            args = None
            
        return event, args
        
    def set_current_cursor(self):
        cursor = self.interaction_manager.get_cursor()
        # if no cursor set, then use the default one in the current binding
        # mode
        if cursor is None:
            cursor = self.binding_manager.get().get_base_cursor()
        qcursor = get_cursor(cursor)
        if qcursor:
            self.setCursor(qcursor)
        
    def process_interaction(self, event=None, args=None, do_update=None):
        """Process user interaction.
        
        This method is called after each user action (mouse, keyboard...).
        It finds the right action associated to the command, then the event 
        associated to that action.
        
        Arguments:
          * event=None: if None, the current event associated to the current
            user action is retrieved. Otherwise, an event can be directly
            passed here to force the trigger of any interaction event.
          * args=None: the arguments of the event if event is not None.
        
        """
        if event is None:
            # get current event from current user action
            event, args = self.get_current_event()
        
        
        if event == 'Animate' and self.block_refresh:
            return
        
        
        prev_event = self.interaction_manager.prev_event
        
        # handle interaction mode change
        if event == 'SwitchInteractionMode':
            binding = self.switch_interaction_mode()
            log_debug("Switching interaction mode to %s." % \
                binding.__class__.__name__)
        
        # process the interaction event
        self.interaction_manager.process_event(event, args)
        
        # raise a signal if there is one associated to the current event
        if event in self.events_to_signals:
            self.events_to_signals[event].emit(*args)
        
        # set cursor
        self.set_current_cursor()
        
        # clean current action (unique usage)
        self.user_action_generator.clean_action()
        
        # update the OpenGL view
        if do_update is None:
            do_update = (
                # (not isinstance(self, GalryTimerWidget)) and
                (event is not None or prev_event is not None))
                
        if do_update:
            self.updateGL()

            
    # Miscellaneous
    # -------------
    def save_image(self, file=None, update=True):
        """Save a screenshot of the widget in the specified file."""
        if file is None:
            file = "image.png"
        if update:
            self.updateGL()
        image = self.grabFrameBuffer()
        image.save(file, "PNG")
    
    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            if hasattr(self.window, 'showFullScreen'):
                self.window.showFullScreen()
        else:
            if hasattr(self.window, 'showNormal'):
                self.window.showNormal()
                
    def close_widget(self):
        self.user_action_generator.close()
        if hasattr(self, 'window'):
            if hasattr(self.window, 'close'):
                self.window.close()
    
    
    # Focus methods
    # -------------
    def focusOutEvent(self, event):
        self.user_action_generator.focusOutEvent(event)


class GalryTimerWidget(GalryWidget):
    timer = None
    
    """Special widget with periodic timer used to update the scene at 
    regular intervals."""
    def initialize_timer(self, dt=1.):
        """Initialize the timer.
        
        This method *must* be called in the `initialize` method of the widget.
        
        Arguments:
          * dt=1.: the timer interval in seconds.
          
        """
        self.t = 0.
        self.dt = dt
        # start simulation after initialization completes
        self.timer = QtCore.QTimer()
        self.timer.setInterval(dt * 1000)
        self.timer.timeout.connect(self.update_callback)
        self.paint_manager.t = self.t
        
    def update_callback(self):
        """Callback function for the timer.
        
        Calls `paint_manager.update_callback`, so this latter method should be 
        implemented in the paint manager. The attribute `self.t` is 
        available here and in the paint manager.
        
        """
        self.t = timeit.default_timer() - self.t0
        self.process_interaction('Animate', (self.t,))
        
    def start_timer(self):
        """Start the timer."""
        if self.timer:
            self.t0 = timeit.default_timer()
            self.timer.start()
        
    def stop_timer(self):
        """Stop the timer."""
        if self.timer:
            self.timer.stop()
        
    def showEvent(self, e):
        """Called when the window is shown (for the first time or after
        minimization). It starts the timer."""
        # start simulation when showing window
        self.start_timer()
        
    def hideEvent(self, e):
        """Called when the window is hidden (e.g. minimized). It stops the
        timer."""
        # stop simulation when hiding window
        self.stop_timer()
    
    
# Basic widgets helper functions and classes
# ------------------------------------------
def create_custom_widget(bindings=None,
                         antialiasing=False,
                         constrain_ratio=False,
                         constrain_navigation=False,
                         activate_help=True,
                         activate_grid=False,
                         show_grid=False,
                         display_fps=False,
                         activate3D=False,
                         animation_interval=None,
                         momentum=False,
                         autosave=None,
                         getfocus=True,
                         figure=None,
                        **companion_classes):
    """Helper function to create a custom widget class from various parameters.
    
    Arguments:
      * bindings=None: the bindings class, instance, or a list of those.
      * antialiasing=False: whether to activate antialiasing or not. It can
        hurt performance.
      * constrain_ratio=False: if True, the ratio is 1:1 at all times.
      * constrain_navigation=True: if True, the viewbox cannot be greater
        than [-1,1]^2 by default (but it can be customized in 
        interactionmanager.MAX_VIEWBOX).
      * display_fps=False: whether to display the FPS.
      * animation_interval=None: if not None, a special widget with automatic
        timer update is created. This variable then refers to the time interval
        between two successive updates (in seconds).
      * **companion_classes: keyword arguments with the companion classes.
    
    """
    if momentum and animation_interval is None:
        animation_interval = .01
    
    # use the GalryTimerWidget if animation_interval is not None
    if animation_interval is not None:
        baseclass = GalryTimerWidget
    else:
        baseclass = GalryWidget
    
    if bindings is None:
        bindings = []
    if type(bindings) != list and type(bindings) != tuple:
        bindings = [bindings]
    
    # create the custom widget class
    class MyWidget(baseclass):
        """Automatically-created Galry widget."""
        def __init__(self):
            # antialiasing
            if QGLFormat is not None:
                format = QGLFormat()
            else:
                format = None
            if antialiasing:
                if hasattr(format, 'setSampleBuffers'):
                    format.setSampleBuffers(True)
            super(MyWidget, self).__init__(format=format, autosave=autosave,
                getfocus=getfocus)
        
        def initialize(self):
            if figure:
                figure.widget = self
            self.set_bindings(*bindings)
            self.set_companion_classes(**companion_classes)
            self.constrain_ratio = constrain_ratio
            self.constrain_navigation = constrain_navigation
            self.activate_help = activate_help
            self.activate_grid = activate_grid
            self.show_grid = show_grid
            self.activate3D = activate3D
            self.momentum = momentum
            self.display_fps = display_fps
            self.initialize_companion_classes()
            if animation_interval is not None:
                self.initialize_timer(dt=animation_interval)

    return MyWidget
    
class AutodestructibleWindow(QtGui.QMainWindow):
    """Special QT window that can be destroyed automatically after a given
    timeout. Useful for automatic debugging or benchmarking."""
    autodestruct = None
    
    def __init__(self, **kwargs):
        super(AutodestructibleWindow, self).__init__()
        # This is important in interaction sessions: it allows the widget
        # to clean everything up as soon as we close the window (otherwise
        # it is just hidden).
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.initialize(**kwargs)
        
    def set_autodestruct(self, autodestruct=None):
        # by default, use global variable
        if autodestruct is None:
            # use the autodestruct option in command line by default
            autodestruct = "autodestruct" in sys.argv
            if autodestruct is False:
                global AUTODESTRUCT
                autodestruct = AUTODESTRUCT
        # option for autodestructing the window after a fixed number of 
        # seconds: useful for automatic testing
        if autodestruct is True:
            # 3 seconds by default, if True
            global DEFAULT_AUTODESTRUCT
            autodestruct = DEFAULT_AUTODESTRUCT
        if autodestruct:
            log_info("window autodestruction in %d second(s)" % (autodestruct / 1000.))
        self.autodestruct = autodestruct
        
    def initialize(self, **kwargs):
        pass
        
    def kill(self):
        if self.autodestruct:
            self.timer.stop()
            self.close()
        
    def showEvent(self, e):
        if self.autodestruct:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(self.autodestruct)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.kill)
            self.timer.start()
            
def create_basic_window(widget=None, size=None, position=(20, 20),
                        autodestruct=None,
                        toolbar=False):
    """Create a basic QT window with a Galry widget inside.
    
    Arguments:
      * widget: a class or instance deriving from GalryWidget.
      * size=None: the size of the window as a tuple (width, height).
      * position=(100, 100): the initial position of the window on the screen,
        in pixels (x, y).
      * autodestruct=None: if not None, it is the time, in seconds, before the
        window closes itself.
    
    """
    class BasicWindow(AutodestructibleWindow):
        """Automatically-created QT window."""
        def initialize(self, widget=widget, size=size, position=position,
                       autodestruct=autodestruct):
            """Create a basic window to display a single widget.
            
            Arguments:
              * widget: a class or instance deriving from GalryWidget.
              * size=None: the size of the window as a tuple (width, height).
              * position=(100, 100): the initial position of the window on the screen,
                in pixels (x, y).
              * autodestruct=None: if not None, it is the time, in seconds, before the
                window closes itself.
              
            """
            self.set_autodestruct(autodestruct)
            # default widget
            if widget is None:
                widget = GalryWidget()
            # if widget is not an instance of GalryWidget, maybe it's a class,
            # then try to instanciate it
            if not isinstance(widget, GalryWidget):
                widget = widget()
            widget.window = self
            # create widget
            self.widget = widget
            if toolbar:
                self.add_toolbar()
            # if size is None:
                # size = self.widget.w, self.widget.h
            if size is not None:
                self.widget.w, self.widget.h = size
            self.setCentralWidget(self.widget)
            self.setWindowTitle("Galry")
            self.move(*position)
            # ensure the main window size is adjusted so that the widget size
            # is equal to the specified size
            self.resize(self.sizeHint())
            self.show()
            
        def toggle_toolbar(self):
            self.toolbar.setVisible(not self.toolbar.isVisible())#not )
            
        def add_toolbar(self):
            """Add navigation toolbar"""
            
            # reset
            reset_action = QtGui.QAction("Reset view (R)", self)
            reset_action.setIcon(get_icon('home'))
            self.widget.connect_events(reset_action.triggered, 'Reset')
            
            # show grid
            grid_action = QtGui.QAction("Show grid (G)", self)
            grid_action.setIcon(get_icon('grid'))
            self.widget.connect_events(grid_action.triggered, 'Grid')

            # fullscreen
            fullscreen_action = QtGui.QAction("Fullscreen (F)", self)
            fullscreen_action.setIcon(get_icon('fullscreen'))
            self.widget.connect_events(fullscreen_action.triggered, 'Fullscreen')

            # save image
            save_action = QtGui.QAction("Save image (S)", self)
            save_action.setIcon(get_icon('save'))
            save_action.setShortcut("S")
            save_action.triggered.connect(self.save)            
            
            toolbar_action = QtGui.QAction("Toggle toolbar visibility (T)", self)
            toolbar_action.setIcon(get_icon('toolbar'))
            toolbar_action.setShortcut("T")
            toolbar_action.triggered.connect(self.toggle_toolbar)
            # self.toolbar_action = toolbar_action
            
            # help
            help_action = QtGui.QAction("Show help (H)", self)
            help_action.setIcon(get_icon('help'))
            self.widget.connect_events(help_action.triggered, 'Help')
            
            # exit
            exit_action = QtGui.QAction("Exit (Q)", self)
            exit_action.setIcon(get_icon('exit'))
            exit_action.triggered.connect(self.close)
            
            # add toolbar
            mytoolbar = QtGui.QToolBar(self.widget)        
            mytoolbar.setIconSize(QtCore.QSize(32, 32))
            
            for action in [reset_action, grid_action, fullscreen_action,
                toolbar_action, save_action, help_action, exit_action]:
                self.addAction(action)
                mytoolbar.addAction(action)
            
            mytoolbar.setStyleSheet("""
            QToolBar, QToolButton
            {
                background: #000000;
                border-color: #000000;
                color: #ffffff;
            }
            QToolButton
            {
                margin-left: 5px;
            }
            QToolButton:hover
            {
                background: #2a2a2a;
            }
            """)
            mytoolbar.setMovable(False)
            mytoolbar.setFloatable(False)
            self.toolbar = mytoolbar
            self.addToolBar(mytoolbar)
            
        def save(self):
            """Open a file dialog and save the current image in the specified
            PNG file."""
            initial_filename = 'screen'
            existing = filter(lambda f: f.startswith(initial_filename), os.listdir('.'))
            i = 0
            if existing:
                for f in existing:
                    r = re.match('screen([0-9]*).png', f)
                    i = max(i, int(r.groups()[0]))
                i += 1
                # if last:
                    # last = int(last)
                    # i = last + 1
            filename, _ = QtGui.QFileDialog.getSaveFileName(self,
                "Save the current view in a PNG image",
                initial_filename + str(i) + '.png',
                # '*.png',
                # '*.png',
                # QtGui.QFileDialog.AnyFile,
                )
            if filename:
                self.widget.save_image(str(filename))
            
        def closeEvent(self, e):
            """Clean up memory upon closing."""
            self.widget.user_action_generator.close()
            self.widget.paint_manager.cleanup()
            super(BasicWindow, self).closeEvent(e)
            
        def contextMenuEvent(self, e):
            return
        
    return BasicWindow
    
def show_basic_window(widget_class=None, window_class=None, size=None,
            position=(20, 20), autodestruct=None, toolbar=False, **kwargs):
    """Create a custom widget and/or window and show it immediately.
    
    Arguments:
      * widget_class=None: the class deriving from GalryWidget.
      * window_class=None: the window class, deriving from `QMainWindow`.
      * size=None: the size of the window as a tuple (width, height).
      * position=(100, 100): the initial position of the window on the screen,
        in pixels (x, y).
      * autodestruct=None: if not None, it is the time, in seconds, before the
        window closes itself.
      * **kwargs: keyword arguments with the companion classes and other 
        parameters that are passed to `create_custom_widget`.
    
    """
    # default widget class
    if widget_class is None:
        widget_class = create_custom_widget(**kwargs)
    # defaut window class
    if window_class is None:
        window_class = create_basic_window(widget_class, size=size,
            position=position, autodestruct=autodestruct, toolbar=toolbar,
            )
    # create and show window
    return show_window(window_class)
    

########NEW FILE########
__FILENAME__ = glrenderer
try:
    import OpenGL.GL as gl
except:
    from galry import log_warn
    log_warn(("PyOpenGL is not available and Galry won't be"
        " able to render plots."))
    class _gl(object):
        def mock(*args, **kwargs):
            return None
        def __getattr__(self, name):
            return self.mock
    gl = _gl()
from collections import OrderedDict
import numpy as np
import sys
from galry import enforce_dtype, DataNormalizer, log_info, log_debug, \
    log_warn, RefVar

    
__all__ = ['GLVersion', 'GLRenderer']
    
    
# GLVersion class
# ---------------
class GLVersion(object):
    """Methods related to the GL version."""
    # self.version_header = '#version 120'
    # self.precision_header = 'precision mediump float;'
    @staticmethod
    def get_renderer_info():
        """Return information about the client renderer.
        
        Arguments:
          * info: a dictionary with the following keys:
              * renderer_name
              * opengl_version
              * glsl_version
              
        """
        return {
            'renderer_name': gl.glGetString(gl.GL_RENDERER),
            'opengl_version': gl.glGetString(gl.GL_VERSION),
            'glsl_version': gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION)
        }
    
    @staticmethod
    def version_header():
        if GLVersion.get_renderer_info()['opengl_version'][0:3] < '2.1':
            return '#version 110\n'
        else:
            return '#version 120\n'
        
    @staticmethod
    def precision_header():
        if GLVersion.get_renderer_info()['glsl_version'] >= '1.3':
            return 'precision mediump float;'
        else:
            return ''
    
    
# Low-level OpenGL functions to initialize/load variables
# -------------------------------------------------------
class Attribute(object):
    """Contains OpenGL functions related to attributes."""
    @staticmethod
    def create():
        """Create a new buffer and return a `buffer` index."""
        return gl.glGenBuffers(1)
    
    @staticmethod
    def get_gltype(index=False):
        if not index:
            return gl.GL_ARRAY_BUFFER
        else:
            return gl.GL_ELEMENT_ARRAY_BUFFER
        
    @staticmethod
    def bind(buffer, location=None, index=False):
        """Bind a buffer and associate a given location."""
        gltype = Attribute.get_gltype(index)
        gl.glBindBuffer(gltype, buffer)
        if location >= 0:
            gl.glEnableVertexAttribArray(location)
        
    @staticmethod
    def set_attribute(location, ndim):
        """Specify the type of the attribute before rendering."""
        gl.glVertexAttribPointer(location, ndim, gl.GL_FLOAT, gl.GL_FALSE, 0, None)
    
    @staticmethod
    def convert_data(data, index=False):
        """Force 32-bit floating point numbers for data."""
        if not index:
            return enforce_dtype(data, np.float32)
        else:
            return np.array(data, np.int32)
        
    
    @staticmethod
    def load(data, index=False):
        """Load data in the buffer for the first time. The buffer must
        have been bound before."""
        data = Attribute.convert_data(data, index=index)
        gltype = Attribute.get_gltype(index)
        gl.glBufferData(gltype, data, gl.GL_DYNAMIC_DRAW)
        
    @staticmethod
    def update(data, onset=0, index=False):
        """Update data in the currently bound buffer."""
        gltype = Attribute.get_gltype(index)
        data = Attribute.convert_data(data, index=index)
        # convert onset into bytes count
        if data.ndim == 1:
            ndim = 1
        elif data.ndim == 2:
            ndim = data.shape[1]
        onset *= ndim * data.itemsize
        gl.glBufferSubData(gltype, int(onset), data)
    
    @staticmethod
    def delete(*buffers):
        """Delete buffers."""
        if buffers:
            gl.glDeleteBuffers(len(buffers), buffers)
        
        
class Uniform(object):
    """Contains OpenGL functions related to uniforms."""
    float_suffix = {True: 'f', False: 'i'}
    array_suffix = {True: 'v', False: ''}
    # glUniform[Matrix]D[f][v]
    
    @staticmethod
    def convert_data(data):
        if isinstance(data, np.ndarray):
            data = enforce_dtype(data, np.float32)
        if type(data) == np.float64:
            data = np.float32(data)
        if type(data) == np.int64:
            data = np.int32(data)
        if type(data) == list:
            data = map(Uniform.convert_data, data)
        if type(data) == tuple:
            data = tuple(map(Uniform.convert_data, data))
        return data
    
    @staticmethod
    def load_scalar(location, data):
        data = Uniform.convert_data(data)
        is_float = (type(data) == float) or (type(data) == np.float32)
        funname = 'glUniform1%s' % Uniform.float_suffix[is_float]
        getattr(gl, funname)(location, data)

    @staticmethod
    def load_vector(location, data):
        if len(data) > 0:
            data = Uniform.convert_data(data)
            is_float = (type(data[0]) == float) or (type(data[0]) == np.float32)
            ndim = len(data)
            funname = 'glUniform%d%s' % (ndim, Uniform.float_suffix[is_float])
            getattr(gl, funname)(location, *data)
    
    @staticmethod
    def load_array(location, data):
        data = Uniform.convert_data(data)
        is_float = (data.dtype == np.float32)
        size, ndim = data.shape
        funname = 'glUniform%d%sv' % (ndim, Uniform.float_suffix[is_float])
        getattr(gl, funname)(location, size, data)
        
    @staticmethod
    def load_matrix(location, data):
        data = Uniform.convert_data(data)
        is_float = (data.dtype == np.float32)
        n, m = data.shape
        # TODO: arrays of matrices?
        if n == m:
            funname = 'glUniformMatrix%d%sv' % (n, Uniform.float_suffix[is_float])
        else:
            funname = 'glUniformMatrix%dx%d%sv' % (n, m, Uniform.float_suffix[is_float])
        getattr(gl, funname)(location, 1, False, data)


class Texture(object):
    """Contains OpenGL functions related to textures."""
    @staticmethod
    def create(ndim=2, mipmap=False, minfilter=None, magfilter=None):
        """Create a texture with the specifyed number of dimensions."""
        buffer = gl.glGenTextures(1)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        Texture.bind(buffer, ndim)
        textype = getattr(gl, "GL_TEXTURE_%dD" % ndim)
        gl.glTexParameteri(textype, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP)
        gl.glTexParameteri(textype, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP)
        
        if mipmap:
            if hasattr(gl, 'glGenerateMipmap'):
                gl.glGenerateMipmap(textype)
            else:
                minfilter = 'NEAREST'
                magfilter = 'NEAREST'
            
        if minfilter is None:
            minfilter = 'NEAREST'
        if magfilter is None:
            magfilter = 'NEAREST'
            
        minfilter = getattr(gl, 'GL_' + minfilter)
        magfilter = getattr(gl, 'GL_' + magfilter)
            
        gl.glTexParameteri(textype, gl.GL_TEXTURE_MIN_FILTER, minfilter)
        gl.glTexParameteri(textype, gl.GL_TEXTURE_MAG_FILTER, magfilter)
        
        return buffer
        
    @staticmethod
    def bind(buffer, ndim):
        """Bind a texture buffer."""
        textype = getattr(gl, "GL_TEXTURE_%dD" % ndim)
        gl.glBindTexture(textype, buffer)
    
    @staticmethod
    def get_info(data):
        """Return information about texture data."""
        # find shape, ndim, ncomponents
        shape = data.shape
        if shape[0] == 1:
            ndim = 1
        elif shape[0] > 1:
            ndim = 2
        # ndim = 2
        ncomponents = shape[2]
        # ncomponents==1 ==> GL_R, 3 ==> GL_RGB, 4 ==> GL_RGBA
        component_type = getattr(gl, ["GL_INTENSITY8", None, "GL_RGB", "GL_RGBA"] \
                                            [ncomponents - 1])
        return ndim, ncomponents, component_type

    @staticmethod    
    def convert_data(data):
        """convert data in a array of uint8 in [0, 255]."""
        if data.dtype == np.float32 or data.dtype == np.float64:
            return np.array(255 * data, dtype=np.uint8)
        elif data.dtype == np.uint8:
            return data
        else:
            raise ValueError("The texture is in an unsupported format.")
    
    @staticmethod
    def copy(fbo, tex_src, tex_dst, width, height):
        
        # /// bind the FBO
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, fbo)
        # /// attach the source texture to the fbo
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0,
                                gl.GL_TEXTURE_2D, tex_src, 0)
        # /// bind the destination texture
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_dst)
        # /// copy from framebuffer (here, the FBO!) to the bound texture
        gl.glCopyTexSubImage2D(gl.GL_TEXTURE_2D, 0, 0, 0, 0, 0, width, height)
        # /// unbind the FBO
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        
        # # ncomponents==1 ==> GL_R, 3 ==> GL_RGB, 4 ==> GL_RGBA
        # component_type = getattr(gl, ["GL_INTENSITY8", None, "GL_RGB", "GL_RGBA"] \
                                            # [ncomponents - 1])
        # gl.glCopyTexImage2D(gl.GL_TEXTURE_2D,
            # 0,  # level
            # component_type, 
            # 0, 0,  # x, y offsets
            # 0, 0,  # x, y
            # w, h, # width, height
            # 0  # border
            # )
            
    # @staticmethod
    # def read_buffer(index=0):
        # gl.glReadBuffer(getattr(gl, 'GL_COLOR_ATTACHMENT%d' % index))
            
    # @staticmethod
    # def draw_buffer():
        # gl.glDrawBuffer(gl.GL_FRONT)
            
    @staticmethod
    def load(data):
        """Load texture data in a bound texture buffer."""
        # convert data in a array of uint8 in [0, 255]
        data = Texture.convert_data(data)
        shape = data.shape
        # get texture info
        ndim, ncomponents, component_type = Texture.get_info(data)
        textype = getattr(gl, "GL_TEXTURE_%dD" % ndim)
        # print ndim, shape, data.shape
        # load data in the buffer
        if ndim == 1:
            gl.glTexImage1D(textype, 0, component_type, shape[1], 0, component_type,
                            gl.GL_UNSIGNED_BYTE, data)
        elif ndim == 2:
            # width, height == shape[1], shape[0]: Thanks to the Confusion Club
            gl.glTexImage2D(textype, 0, component_type, shape[1], shape[0], 0,
                            component_type, gl.GL_UNSIGNED_BYTE, data)
        
    @staticmethod
    def update(data):
        """Update a texture."""
        # convert data in a array of uint8 in [0, 255]
        data = Texture.convert_data(data)
        shape = data.shape
        # get texture info
        ndim, ncomponents, component_type = Texture.get_info(data)
        textype = getattr(gl, "GL_TEXTURE_%dD" % ndim)
        # update buffer
        if ndim == 1:
            gl.glTexSubImage1D(textype, 0, 0, shape[1],
                               component_type, gl.GL_UNSIGNED_BYTE, data)
        elif ndim == 2:
            gl.glTexSubImage2D(textype, 0, 0, 0, shape[1], shape[0],
                               component_type, gl.GL_UNSIGNED_BYTE, data)

    @staticmethod
    def delete(*buffers):
        """Delete texture buffers."""
        gl.glDeleteTextures(buffers)


class FrameBuffer(object):
    """Contains OpenGL functions related to FBO."""
    @staticmethod
    def create():
        """Create a FBO."""
        if hasattr(gl, 'glGenFramebuffers') and gl.glGenFramebuffers:
            buffer = gl.glGenFramebuffers(1)
        else:
            buffer = None
        return buffer
        
    @staticmethod
    def bind(buffer=None):
        """Bind a FBO."""
        if buffer is None:
            buffer = 0
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, buffer)
        
    @staticmethod
    def bind_texture(texture, i=0):
        gl.glFramebufferTexture2D(gl.GL_FRAMEBUFFER,
            getattr(gl, 'GL_COLOR_ATTACHMENT%d' % i),
            gl.GL_TEXTURE_2D, texture, 0)

    @staticmethod
    def draw_buffers(n):
        gl.glDrawBuffers([getattr(gl, 'GL_COLOR_ATTACHMENT%d' % i) for i in xrange(n)])
            
    @staticmethod
    def unbind():
        """Unbind a FBO."""
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

        
# Shader manager
# --------------
class ShaderManager(object):
    """Handle vertex and fragment shaders.
    
    TODO: integrate in the renderer the shader code creation module.
    
    """
    
    # Initialization methods
    # ----------------------
    def __init__(self, vertex_shader, fragment_shader):
        """Compile shaders and create a program."""
        # add headers
        vertex_shader = GLVersion.version_header() + vertex_shader
        fragment_shader = GLVersion.version_header() + fragment_shader
        # set shader source
        self.vertex_shader = vertex_shader
        self.fragment_shader = fragment_shader
        # compile shaders
        self.compile()
        # create program
        self.program = self.create_program()

    def compile_shader(self, source, shader_type):
        """Compile a shader (vertex or fragment shader).
        
        Arguments:
          * source: the shader source code as a string.
          * shader_type: either gl.GL_VERTEX_SHADER or gl.GL_FRAGMENT_SHADER.
        
        """
        # compile shader
        shader = gl.glCreateShader(shader_type)
        gl.glShaderSource(shader, source)
        gl.glCompileShader(shader)
        
        result = gl.glGetShaderiv(shader, gl.GL_COMPILE_STATUS)
        infolog = gl.glGetShaderInfoLog(shader)
        if infolog:
            infolog = "\n" + infolog.strip()
        # check compilation error
        if not(result) and infolog:
            msg = "Compilation error for %s." % str(shader_type)
            if infolog is not None:
                msg += infolog
            msg += source
            raise RuntimeError(msg)
        else:
            log_debug("Compilation succeeded for %s.%s" % (str(shader_type), infolog))
        return shader
        
    def compile(self):
        """Compile the shaders."""
        # print self.vertex_shader
        # print self.fragment_shader
        self.vs = self.compile_shader(self.vertex_shader, gl.GL_VERTEX_SHADER)
        self.fs = self.compile_shader(self.fragment_shader, gl.GL_FRAGMENT_SHADER)
        
    def create_program(self):
        """Create shader program and attach shaders."""
        program = gl.glCreateProgram()
        gl.glAttachShader(program, self.vs)
        gl.glAttachShader(program, self.fs)
        gl.glLinkProgram(program)

        result = gl.glGetProgramiv(program, gl.GL_LINK_STATUS)
        # check linking error
        if not(result):
            msg = "Shader program linking error:"
            info = gl.glGetProgramInfoLog(program)
            if info:
                msg += info
                raise RuntimeError(msg)
        
        self.program = program
        return program
        
    def get_attribute_location(self, name):
        """Return the location of an attribute after the shaders have compiled."""
        return gl.glGetAttribLocation(self.program, name)
  
    def get_uniform_location(self, name):
        """Return the location of a uniform after the shaders have compiled."""
        return gl.glGetUniformLocation(self.program, name)
  
  
    # Activation methods
    # ------------------
    def activate_shaders(self):
        """Activate shaders for the rest of the rendering call."""
        # try:
        gl.glUseProgram(self.program)
            # return True
        # except Exception as e:
            # log_info("Error while activating the shaders: " + e.message)
            # return False
        
    def deactivate_shaders(self):
        """Deactivate shaders for the rest of the rendering call."""
        # try:
        gl.glUseProgram(0)
            # return True
        # except Exception as e:
            # log_info("Error while activating the shaders: " + e.message)
            # return True
        
        
    # Cleanup methods
    # ---------------
    def detach_shaders(self):
        """Detach shaders from the program."""
        if gl.glIsProgram(self.program):
            gl.glDetachShader(self.program, self.vs)
            gl.glDetachShader(self.program, self.fs)
            
    def delete_shaders(self):
        """Delete the vertex and fragment shaders."""
        if gl.glIsProgram(self.program):
            gl.glDeleteShader(self.vs)
            gl.glDeleteShader(self.fs)

    def delete_program(self):
        """Delete the shader program."""
        if gl.glIsProgram(self.program):
            gl.glDeleteProgram(self.program)
        
    def cleanup(self):
        """Clean up all shaders."""
        self.detach_shaders()
        self.delete_shaders()
        self.delete_program()
        
        
# Slicing classes
# ---------------
MAX_VBO_SIZE = 65000

class Slicer(object):
    """Handle attribute slicing, necessary because of the size
    of buffer objects which is limited on some GPUs."""
    @staticmethod
    def _get_slices(size, maxsize=None):
        """Return a list of slices for a given dataset size.
        
        Arguments:
          * size: the size of the dataset, i.e. the number of points.
          
        Returns:
          * slices: a list of pairs `(position, slice_size)` where `position`
            is the position of this slice in the original buffer, and
            `slice_size` the slice size.
        
        """
        if maxsize is None:
            maxsize = MAX_VBO_SIZE
        if maxsize > 0:
            nslices = int(np.ceil(size / float(maxsize)))
        else:
            nslices = 0
        return [(i*maxsize, min(maxsize+1, size-i*maxsize)) for i in xrange(nslices)]

    @staticmethod
    def _slice_bounds(bounds, position, slice_size, regular=False):
        """Slice data bounds in a *single* slice according to the VBOs slicing.
        
        Arguments:
          * bounds: the bounds as specified by the user in `create_dataset`.
          * position: the position of the current slice.
          * slice_size: the size of the current slice.
        
        Returns:
          * bounds_sliced: the bounds for the current slice. It is a list an
            1D array of integer indices.
        
        """
        # first bound index after the sliced VBO: nothing to paint
        if bounds[0] >= position + slice_size:
            bounds_sliced = None
        # last bound index before the sliced VBO: nothing to paint
        elif bounds[-1] < position:
            bounds_sliced = None
        # the current sliced VBO intersects the bounds: something to paint
        else:
            
            bounds_sliced = bounds
            
            if not regular:
                # get the bounds that fall within the sliced VBO
                ind = (bounds_sliced>=position) & (bounds_sliced<position + slice_size)
                bounds_sliced = bounds_sliced[ind]
            # HACK: more efficient algorithm when the bounds are regularly
            # spaced
            else:
                d = float(regular)
                p = position
                b0 = bounds_sliced[0]
                b1 = bounds_sliced[-1]
                s = slice_size
                i0 = max(0, int(np.ceil((p-b0)/d)))
                i1 = max(0, int(np.floor((p+s-b0)/d)))
                bounds_sliced = bounds_sliced[i0:i1+1].copy()
                ind = ((b0 >= p) and (b0 < p+s), (b1 >= p) and (b1 < p+s))
                """
                bounds_sliced = [b0 + d*i]
                (p-b0)/d <= i0 < (p+s-b0)/d
                i0 = ceil((p-b0)/d), i1 = floor((p+s-b0)/d)
                ind = (bs[0] >= p & < p+s, bs[-1])
                """
            
            # remove the onset (first index of the sliced VBO)
            bounds_sliced -= position
            # handle the case when the slice cuts between two bounds
            if not ind[0]:
                bounds_sliced = np.hstack((0, bounds_sliced))
            if not ind[-1]:
                bounds_sliced = np.hstack((bounds_sliced, slice_size))
        return enforce_dtype(bounds_sliced, np.int32)
        
    def set_size(self, size, doslice=True):
        """Update the total size of the buffer, and update
        the slice information accordingly."""
        # deactivate slicing by using a maxsize number larger than the
        # actual size
        if not doslice:
            maxsize = 2 * size
        else:
            maxsize = None
        self.size = size
        # if not hasattr(self, 'bounds'):
            # self.bounds = np.array([0, size], dtype=np.int32)
        # compute the data slicing with respect to bounds (specified in the
        # template) and to the maximum size of a VBO.
        self.slices = self._get_slices(self.size, maxsize)
        # print self.size, maxsize
        # print self.slices
        self.slice_count = len(self.slices)
    
    def set_bounds(self, bounds=None):
        """Update the bound size, and update the slice information
        accordingly."""
        if bounds is None:
            bounds = np.array([0, self.size], dtype=np.int32)
        self.bounds = bounds
        
        # is regular?
        d = np.diff(bounds)
        r = False
        if len(d) > 0:
            dm, dM = d.min(), d.max()
            if dm == dM:
                r = dm
                # log_info("Regular bounds")
        
        self.subdata_bounds = [self._slice_bounds(self.bounds, pos, size, r) \
            for pos, size in self.slices]
       
       
class SlicedAttribute(object):
    """Encapsulate methods for slicing an attribute and handling several
    buffer objects for a single attribute."""
    def __init__(self, slicer, location, buffers=None):
        self.slicer = slicer
        self.location = location
        if buffers is None:
            # create the sliced buffers
            self.create()
        else:
            log_debug("Creating sliced attribute with existing buffers " +
                str(buffers))
            # or use existing buffers
            self.load_buffers(buffers)
        
    def create(self):
        """Create the sliced buffers."""
        self.buffers = [Attribute.create() for _ in self.slicer.slices]
    
    def load_buffers(self, buffers):
        """Load existing buffers instead of creating new ones."""
        self.buffers = buffers
    
    def delete_buffers(self):
        """Delete all sub-buffers."""
        # for buffer in self.buffers:
        Attribute.delete(*self.buffers)
    
    def load(self, data):
        """Load data on all sliced buffers."""
        for buffer, (pos, size) in zip(self.buffers, self.slicer.slices):
            # WARNING: putting self.location instead of None ==> SEGFAULT on Linux with Nvidia drivers
            Attribute.bind(buffer, None)
            Attribute.load(data[pos:pos + size,...])

    def bind(self, slice=None):
        if slice is None:
            slice = 0
        Attribute.bind(self.buffers[slice], self.location)
        
    def update(self, data, mask=None):
        """Update data on all sliced buffers."""
        # NOTE: the slicer needs to be updated if the size of the data changes
        # default mask
        if mask is None:
            mask = np.ones(self.slicer.size, dtype=np.bool)
        # is the current subVBO within the given [onset, offset]?
        within = False
        # update VBOs
        for buffer, (pos, size) in zip(self.buffers, self.slicer.slices):
            subdata = data[pos:pos + size,...]
            submask = mask[pos:pos + size]
            # if there is at least one True in the slice mask (submask)
            if submask.any():
                # this sub-buffer contains updated indices
                subonset = submask.argmax()
                suboffset = len(submask) - 1 - submask[::-1].argmax()
                Attribute.bind(buffer, self.location)
                Attribute.update(subdata[subonset:suboffset + 1,...], subonset)

    
# Painter class
# -------------
class Painter(object):
    """Provides low-level methods for calling OpenGL rendering commands."""
    
    @staticmethod
    def draw_arrays(primtype, offset, size):
        """Render an array of primitives."""
        gl.glDrawArrays(primtype, offset, size)
        
    @staticmethod
    def draw_multi_arrays(primtype, bounds):
        """Render several arrays of primitives."""
        first = bounds[:-1]
        count = np.diff(bounds)
        primcount = len(bounds) - 1
        gl.glMultiDrawArrays(primtype, first, count, primcount)
        
    @staticmethod
    def draw_indexed_arrays(primtype, size):
        gl.glDrawElements(primtype, size, gl.GL_UNSIGNED_INT, None)


# Visual renderer
# ---------------
class GLVisualRenderer(object):
    """Handle rendering of one visual"""
    
    def __init__(self, renderer, visual):
        """Initialize the visual renderer, create the slicer, initialize
        all variables and the shaders."""
        # register the master renderer (to access to other visual renderers)
        # and register the scene dictionary
        self.renderer = renderer
        self.scene = renderer.scene
        # register the visual dictionary
        self.visual = visual
        self.framebuffer = visual.get('framebuffer', None)
        # self.beforeclear = visual.get('beforeclear', None)
        # options
        self.options = visual.get('options', {})
        # hold all data changes until the next rendering pass happens
        self.data_updating = {}
        self.textures_to_copy = []
        # set the primitive type from its name
        self.set_primitive_type(self.visual['primitive_type'])
        # indexed mode? set in initialize_variables
        self.use_index = None
        # whether to use slicing? always True except when indexing should not
        # be used, but slicing neither
        self.use_slice = True
        # self.previous_size = None
        # set the slicer
        self.slicer = Slicer()
        # used when slicing needs to be deactivated (like for indexed arrays)
        self.noslicer = Slicer()
        # get size and bounds
        size = self.visual['size']
        bounds = np.array(self.visual.get('bounds', [0, size]), np.int32)
        # self.update_size(size, bounds)
        self.slicer.set_size(size)
        self.slicer.set_bounds(bounds)
        self.noslicer.set_size(size, doslice=False)
        self.noslicer.set_bounds(bounds)
        # compile and link the shaders
        self.shader_manager = ShaderManager(self.visual['vertex_shader'],
                                            self.visual['fragment_shader'])
                                            
        # DEBUG
        # log_info(self.shader_manager.vertex_shader)
        # log_info(self.shader_manager.fragment_shader)
                                            
        # initialize all variables
        # self.initialize_normalizers()
        self.initialize_variables()
        self.initialize_fbocopy()
        self.load_variables()
        
    def set_primitive_type(self, primtype):
        """Set the primitive type from its name (without the GL_ prefix)."""
        self.primitive_type = getattr(gl, "GL_%s" % primtype.upper())
    
    def getarg(self, name):
        """Get a visual parameter."""
        return self.visual.get(name, None)
    
    
    # Variable methods
    # ----------------
    def get_visuals(self):
        """Return all visuals defined in the scene."""
        return self.scene['visuals']
        
    def get_visual(self, name):
        """Return a visual dictionary from its name."""
        visuals = [v for v in self.get_visuals() if v.get('name', '') == name]
        if not visuals:
            return None
        return visuals[0]
        
    def get_variables(self, shader_type=None):
        """Return all variables defined in the visual."""
        if not shader_type:
            return self.visual.get('variables', [])
        else:
            return [var for var in self.get_variables() \
                            if var['shader_type'] == shader_type]
        
    def get_variable(self, name, visual=None):
        """Return a variable by its name, and for any given visual which 
        is specified by its name."""
        # get the variables list
        if visual is None:
            variables = self.get_variables()
        else:
            variables = self.get_visual(visual)['variables']
        variables = [v for v in variables if v.get('name', '') == name]
        if not variables:
            return None
        return variables[0]
        
    def resolve_reference(self, refvar):
        """Resolve a reference variable: return its true value (a Numpy array).
        """
        return self.get_variable(refvar.variable, visual=refvar.visual)
        
        
    # Initialization methods
    # ----------------------
    def initialize_fbocopy(self):
        """Create a FBO used when copying textures."""
        self.fbocopy = FrameBuffer.create()
    
    def initialize_variables(self):
        """Initialize all variables, after the shaders have compiled."""
        # find out whether indexing is used or not, because in this case
        # the slicing needs to be deactivated
        if self.get_variables('index'):
            # deactivate slicing
            self.slicer = self.noslicer
            log_debug("deactivating slicing because there's an indexed buffer")
            self.use_index = True
        else:
            self.use_index = False
        # initialize all variables
        for var in self.get_variables():
            shader_type = var['shader_type']
            # skip varying
            if shader_type == 'varying':
                continue
            name = var['name']
            # call initialize_***(name) to initialize that variable
            getattr(self, 'initialize_%s' % shader_type)(name)
        # special case for uniforms: need to load them the first time
        uniforms = self.get_variables('uniform')
        self.set_data(**dict([(v['name'], v.get('data', None)) for v in uniforms]))
    
    def initialize_attribute(self, name):
        """Initialize an attribute: get the shader location, create the
        sliced buffers, and load the data."""
        # retrieve the location of that attribute in the shader
        location = self.shader_manager.get_attribute_location(name)
        variable = self.get_variable(name)
        variable['location'] = location
        # deal with reference attributes: share the same buffers between 
        # several different visuals
        if isinstance(variable.get('data', None), RefVar):
            
            # HACK: if the targeted attribute is indexed, we should
            # deactivate slicing here
            if self.renderer.visual_renderers[variable['data'].visual].use_index:
                log_debug("deactivating slicing")
                self.slicer = self.noslicer
            
            # use the existing buffers from the target variable
            target = self.resolve_reference(variable['data'])
            variable['sliced_attribute'] = SlicedAttribute(self.slicer, location,
                buffers=target['sliced_attribute'].buffers)
        else:
            # initialize the sliced buffers
            variable['sliced_attribute'] = SlicedAttribute(self.slicer, location)
        
    def initialize_index(self, name):
        variable = self.get_variable(name)
        variable['buffer'] = Attribute.create()
        
    def initialize_texture(self, name):
        variable = self.get_variable(name)
        # handle reference variable to texture
        if isinstance(variable.get('data', None), RefVar):
            target = self.resolve_reference(variable['data'])
            variable['buffer'] = target['buffer']
            variable['location'] = target['location']
        else:
            variable['buffer'] = Texture.create(variable['ndim'],
                mipmap=variable.get('mipmap', None),
                minfilter=variable.get('minfilter', None),
                magfilter=variable.get('magfilter', None),
                )
            # NEW
            # get the location of the sampler uniform
            location = self.shader_manager.get_uniform_location(name)
            variable['location'] = location
    
    def initialize_framebuffer(self, name):
        variable = self.get_variable(name)
        variable['buffer'] = FrameBuffer.create()
        
        # bind the frame buffer
        FrameBuffer.bind(variable['buffer'])
        
        # variable['texture'] is a list of texture names in the current visual
        if isinstance(variable['texture'], basestring):
            variable['texture'] = [variable['texture']]
            
        # draw as many buffers as there are textures in that frame buffer
        FrameBuffer.draw_buffers(len(variable['texture']))
            
        for i, texname in enumerate(variable['texture']):
            # get the texture variable: 
            texture = self.get_variable(texname)
            # link the texture to the frame buffer
            FrameBuffer.bind_texture(texture['buffer'], i)
        
        # unbind the frame buffer
        FrameBuffer.unbind()
        
    def initialize_uniform(self, name):
        """Initialize an uniform: get the location after the shaders have
        been compiled."""
        location = self.shader_manager.get_uniform_location(name)
        variable = self.get_variable(name)
        variable['location'] = location
    
    def initialize_compound(self, name):
        pass
        
        
    # Normalization methods
    # ---------------------
    # def initialize_normalizers(self):
        # self.normalizers = {}
        
        
    # Loading methods
    # ---------------
    def load_variables(self):
        """Load data for all variables at initialization."""
        for var in self.get_variables():
            shader_type = var['shader_type']
            # skip uniforms
            if shader_type == 'uniform' or shader_type == 'varying' or shader_type == 'framebuffer':
                continue
            # call load_***(name) to load that variable
            getattr(self, 'load_%s' % shader_type)(var['name'])
        
    def load_attribute(self, name, data=None):
        """Load data for an attribute variable."""
        variable = self.get_variable(name)
        if variable['sliced_attribute'].location < 0:
            log_debug(("Variable '%s' could not be loaded, probably because "
                      "it is not used in the shaders") % name)
            return
        olddata = variable.get('data', None)
        if isinstance(olddata, RefVar):
            log_debug("Skipping loading data for attribute '%s' since it "
                "references a target variable." % name)
            return
        if data is None:
            data = olddata
        if data is not None:
            # normalization
            # if name in self.options.get('normalizers', {}):
                # viewbox = self.options['normalizers'][name]
                # if viewbox:
                    # self.normalizers[name] = DataNormalizer(data)
                    # # normalize data with the specified viewbox, None by default
                    # # meaning that the natural bounds of the data are used.
                    # data = self.normalizers[name].normalize(viewbox)
            variable['sliced_attribute'].load(data)
        
    def load_index(self, name, data=None):
        """Load data for an index variable."""
        variable = self.get_variable(name)
        if data is None:
            data = variable.get('data', None)
        if data is not None:
            self.indexsize = len(data)
            Attribute.bind(variable['buffer'], index=True)
            Attribute.load(data, index=True)
        
    def load_texture(self, name, data=None):
        """Load data for a texture variable."""
        variable = self.get_variable(name)
        
        if variable['buffer'] < 0:
            log_debug(("Variable '%s' could not be loaded, probably because "
                      "it is not used in the shaders") % name)
            return
        
        if data is None:
            data = variable.get('data', None)
            
        # NEW: update sampler location
        self.update_samplers = True
        
        if isinstance(data, RefVar):
            log_debug("Skipping loading data for texture '%s' since it "
                "references a target variable." % name)
            return
            
        if data is not None:
            Texture.bind(variable['buffer'], variable['ndim'])
            Texture.load(data)
            
    def load_uniform(self, name, data=None):
        """Load data for an uniform variable."""
        variable = self.get_variable(name)
        location = variable['location']
        
        if location < 0:
            log_debug(("Variable '%s' could not be loaded, probably because "
                      "it is not used in the shaders") % name)
            return
        
        if data is None:
            data = variable.get('data', None)
        if data is not None:
            ndim = variable['ndim']
            size = variable.get('size', None)
            # one value
            if not size:
                # scalar or vector
                if type(ndim) == int or type(ndim) == long:
                    if ndim == 1:
                        Uniform.load_scalar(location, data)
                    else:
                        Uniform.load_vector(location, data)
                # matrix 
                elif type(ndim) == tuple:
                    Uniform.load_matrix(location, data)
            # array
            else:
                # scalar or vector
                if type(ndim) == int or type(ndim) == long:
                    Uniform.load_array(location, data)
            
    def load_compound(self, name, data=None):
        pass
            
            
    # Updating methods
    # ----------------
    def update_variable(self, name, data, **kwargs):
        """Update data of a variable."""
        variable = self.get_variable(name)
        if variable is None:
            log_debug("Variable '%s' was not found, unable to update it." % name)
        else:
            shader_type = variable['shader_type']
            # skip compound, which is handled in set_data
            if shader_type == 'compound' or shader_type == 'varying' or shader_type == 'framebuffer':
                pass
            else:
                getattr(self, 'update_%s' % shader_type)(name, data, **kwargs)
    
    def update_attribute(self, name, data):#, bounds=None):
        """Update data for an attribute variable."""
        variable = self.get_variable(name)
        
        if variable['sliced_attribute'].location < 0:
            log_debug(("Variable '%s' could not be updated, probably because "
                      "it is not used in the shaders") % name)
            return
        
        # handle reference variable
        olddata = variable.get('data', None)
        if isinstance(olddata, RefVar):
            raise ValueError("Unable to load data for a reference " +
                "attribute. Use the target variable directly.""")
        variable['data'] = data
        att = variable['sliced_attribute']
        
        if olddata is None:
            oldshape = 0
        else:
            oldshape = olddata.shape
        
        # print name, oldshape, data.shape
        
        # handle size changing
        if data.shape[0] != oldshape[0]:
            log_debug(("Creating new buffers for variable %s, old size=%s,"
                "new size=%d") % (name, oldshape[0], data.shape[0]))
            # update the size only when not using index arrays
            if self.use_index:
                newsize = self.slicer.size
            else:
                newsize = data.shape[0]
            # update the slicer size and bounds
            self.slicer.set_size(newsize, doslice=not(self.use_index))
            
            # HACK: update the bounds only if there are no bounds basically
            # (ie. 2 bounds only), otherwise we assume the bounds have been
            # changed explicitely
            if len(self.slicer.bounds) == 2:
                self.slicer.set_bounds()
                
            # delete old buffers
            att.delete_buffers()
            # create new buffers
            att.create()
            # load data
            att.load(data)
            # forget previous size
            # self.previous_size = None            
        else:
            # update data
            att.update(data)
        
    def update_index(self, name, data):
        """Update data for a index variable."""
        variable = self.get_variable(name)
        prevsize = len(variable['data'])
        variable['data'] = data
        newsize = len(data)
        # handle size changing
        if newsize != prevsize:
            # update the total size (in slicer)
            # self.slicer.set_size(newsize, doslice=False)
            self.indexsize = newsize
            # delete old buffers
            Attribute.delete(variable['buffer'])
            # create new buffer
            variable['buffer'] = Attribute.create()
            # load data
            Attribute.bind(variable['buffer'], variable['ndim'], index=True)
            Attribute.load(data, index=True)
        else:
            # update data
            Attribute.bind(variable['buffer'], variable['ndim'], index=True)
            Attribute.update(data, index=True)
        
    def update_texture(self, name, data):
        """Update data for a texture variable."""
        variable = self.get_variable(name)
        
        if variable['buffer'] < 0:
            log_debug(("Variable '%s' could not be loaded, probably because "
                      "it is not used in the shaders") % name)
            return
        
        prevshape = variable['data'].shape
        variable['data'] = data
        # handle size changing
        if data.shape != prevshape:
            # delete old buffers
            # Texture.delete(variable['buffer'])
            variable['ndim'], variable['ncomponents'], _ = Texture.get_info(data)
            # create new buffer
            # variable['buffer'] = Texture.create(variable['ndim'],
                # mipmap=variable.get('mipmap', None),
                # minfilter=variable.get('minfilter', None),
                # magfilter=variable.get('magfilter', None),)
            # load data
            Texture.bind(variable['buffer'], variable['ndim'])
            Texture.load(data)
        else:
            # update data
            Texture.bind(variable['buffer'], variable['ndim'])
            Texture.update(data)
        
    def update_uniform(self, name, data):
        """Update data for an uniform variable."""
        variable = self.get_variable(name)
        variable['data'] = data
        # the uniform interface is the same for load/update
        self.load_uniform(name, data)
        
    special_keywords = ['visible',
                        'size',
                        'bounds',
                        'primitive_type',
                        'constrain_ratio',
                        'constrain_navigation',
                        ]
    def set_data(self, **kwargs):
        """Load data for the specified visual. Uploading does not happen here
        but in `update_all_variables` instead, since this needs to happen
        after shader program binding in the paint method.
        
        Arguments:
          * **kwargs: the data to update as name:value pairs. name can be
            any field of the visual, plus one of the following keywords:
              * visible: whether this visual should be visible,
              * size: the size of the visual,
              * primitive_type: the GL primitive type,
              * constrain_ratio: whether to constrain the ratio of the visual,
              * constrain_navigation: whether to constrain the navigation,
        
        """
        
        # handle compound variables
        kwargs2 = kwargs.copy()
        for name, data in kwargs2.iteritems():
            variable = self.get_variable(name)
            if variable is None:
                # log_info("variable '%s' unknown" % name)
                continue
            if variable is not None and variable['shader_type'] == 'compound':
                fun = variable['fun']
                kwargs.pop(name)
                # HACK: if the target variable in the compound is a special
                # keyword, we update it in kwargs, otherwise we update the
                # data in self.data_updating
                # print name, fun(data)
                # if name in self.special_keywords:
                    # kwargs.update(**fun(data))
                # else:
                    # self.data_updating.update(**fun(data))
                kwargs.update(**fun(data))
            # remove non-visible variables
            if not variable.get('visible', True):
                kwargs.pop(name)
        
        # handle visual visibility
        visible = kwargs.pop('visible', None)
        if visible is not None:
            self.visual['visible'] = visible
        
        # handle size keyword
        size = kwargs.pop('size', None)
        # print size
        if size is not None:
            self.slicer.set_size(size)
        
        # handle bounds keyword
        bounds = kwargs.pop('bounds', None)
        if bounds is not None:
            self.slicer.set_bounds(bounds)
            
        # handle primitive type special keyword
        primitive_type = kwargs.pop('primitive_type', None)
        if primitive_type is not None:
            self.visual['primitive_type'] = primitive_type
            self.set_primitive_type(primitive_type)
        
        # handle constrain_ratio keyword
        constrain_ratio = kwargs.pop('constrain_ratio', None)
        if constrain_ratio is not None:
            self.visual['constrain_ratio'] = constrain_ratio
        
        # handle constrain_navigation keyword
        constrain_navigation = kwargs.pop('constrain_navigation', None)
        if constrain_navigation is not None:
            self.visual['constrain_navigation'] = constrain_navigation
        
        # flag the other variables as to be updated
        self.data_updating.update(**kwargs)
        
    def copy_texture(self, tex1, tex2):
        self.textures_to_copy.append((tex1, tex2))
        
    def update_all_variables(self):
        """Upload all new data that needs to be updated."""
        # # current size, that may change following variable updating
        # if not self.previous_size:
            # self.previous_size = self.slicer.size
        # go through all data changes
        for name, data in self.data_updating.iteritems():
            if data is not None:
                # log_info("Updating variable '%s'" % name)
                self.update_variable(name, data)
            else:
                log_debug("Data for variable '%s' is None" % name)
        # reset the data updating dictionary
        self.data_updating.clear()
        
    def copy_all_textures(self):
        # copy textures
        for tex1, tex2 in self.textures_to_copy:
            # tex1 = self.get_variable(tex1)
            tex1 = self.resolve_reference(tex1)
            tex2 = self.get_variable(tex2)
            # tex2 = self.resolve_reference(tex2)
            
            # # Texture.read_buffer()
            # Texture.bind(tex2['buffer'], tex2['ndim'])
            # copy(fbo, tex_src, tex_dst, width, height)
            Texture.copy(self.fbocopy, tex1['buffer'], tex2['buffer'],
                tex1['shape'][0], tex1['shape'][1])
        self.textures_to_copy = []


    # Binding methods
    # ---------------
    def bind_attributes(self, slice=None):
        """Bind all attributes of the visual for the given slice.
        This method is used during rendering."""
        # find all visual variables with shader type 'attribute'
        attributes = self.get_variables('attribute')
        # for each attribute, bind the sub buffer corresponding to the given
        # slice
        for variable in attributes:
            loc = variable['location']
            if loc < 0:
                log_debug(("Unable to bind attribute '%s', probably because "
                "it is not used in the shaders.") % variable['name'])
                continue
            variable['sliced_attribute'].bind(slice)
            Attribute.set_attribute(loc, variable['ndim'])
            
    def bind_indices(self):
        indices = self.get_variables('index')
        for variable in indices:
            Attribute.bind(variable['buffer'], index=True)
            
    def bind_textures(self):
        """Bind all textures of the visual.
        This method is used during rendering."""
        
        textures = self.get_variables('texture')
        for i, variable in enumerate(textures):
            buffer = variable.get('buffer', None)
            if buffer is not None:
                
                # HACK: we update the sampler values here
                if self.update_samplers and not isinstance(variable['data'], RefVar):
                    Uniform.load_scalar(variable['location'], i)
                
                # NEW
                gl.glActiveTexture(getattr(gl, 'GL_TEXTURE%d' % i))
                
                Texture.bind(buffer, variable['ndim'])
            else:
                log_debug("Texture '%s' was not properly initialized." % \
                         variable['name'])
        # deactivate all textures if there are not textures
        if not textures:
            Texture.bind(0, 1)
            Texture.bind(0, 2)
        
        # no need to update the samplers after the first execution of this 
        # method
        self.update_samplers = False

    
    # Paint methods
    # -------------
    def paint(self):
        """Paint the visual slice by slice."""
        # do not display non-visible visuals
        if not self.visual.get('visible', True):
            return
            
        # activate the shaders
        try:
            self.shader_manager.activate_shaders()
        # if the shaders could not be successfully activated, stop the
        # rendering immediately
        except Exception as e:
            log_info("Error while activating the shaders: " + str(e))
            return
            
        # update all variables
        self.update_all_variables()
        # bind all texturex for that slice
        self.bind_textures()
        # paint using indices
        if self.use_index:
            self.bind_attributes()
            self.bind_indices()
            Painter.draw_indexed_arrays(self.primitive_type, self.indexsize)
        # or paint without
        elif self.use_slice:
            # draw all sliced buffers
            for slice in xrange(len(self.slicer.slices)):
                # get slice bounds
                slice_bounds = self.slicer.subdata_bounds[slice]
                # print slice, slice_bounds
                # bind all attributes for that slice
                self.bind_attributes(slice)
                # call the appropriate OpenGL rendering command
                # if len(self.slicer.bounds) <= 2:
                # print "slice bounds", slice_bounds
                if len(slice_bounds) <= 2:
                    Painter.draw_arrays(self.primitive_type, slice_bounds[0], 
                        slice_bounds[1] -  slice_bounds[0])
                else:
                    Painter.draw_multi_arrays(self.primitive_type, slice_bounds)
        
        self.copy_all_textures()
        
        # deactivate the shaders
        self.shader_manager.deactivate_shaders()


    # Cleanup methods
    # ---------------
    def cleanup_attribute(self, name):
        """Cleanup a sliced attribute (all sub-buffers)."""
        variable = self.get_variable(name)
        variable['sliced_attribute'].delete_buffers()
    
    def cleanup_texture(self, name):
        """Cleanup a texture."""
        variable = self.get_variable(name)
        Texture.delete(variable['buffer'])
        
    def cleanup(self):
        """Clean up all variables."""
        log_debug("Cleaning up all variables.")
        for variable in self.get_variables():
            shader_type = variable['shader_type']
            if shader_type in ('attribute', 'texture'):
                getattr(self, 'cleanup_%s' % shader_type)(variable['name'])
        # clean up shaders
        self.shader_manager.cleanup()
        
        
# Scene renderer
# --------------
class GLRenderer(object):
    """OpenGL renderer for a Scene.
    
    This class takes a Scene object (dictionary) as an input, and
    renders the scene. It provides methods to update the data in real-time.
    
    """
    # Initialization
    # --------------
    def __init__(self, scene):
        """Initialize the renderer using the information on the scene.
        
        Arguments:
          * scene: a Scene dictionary with a `visuals` field containing
            the list of visuals.
        
        """
        self.scene = scene
        self.viewport = (1., 1.)
        self.visual_renderers = {}
    
    def set_renderer_options(self):
        """Set the OpenGL options."""
        options = self.scene.get('renderer_options', {})
        
        # use vertex buffer object
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)

        # used for multisampling (antialiasing)
        if options.get('antialiasing', None):
            gl.glEnable(gl.GL_MULTISAMPLE)
            
        # used for sprites
        if options.get('sprites', True):
            gl.glEnable(gl.GL_VERTEX_PROGRAM_POINT_SIZE)
            gl.glEnable(gl.GL_POINT_SPRITE)
        
        # enable transparency
        if options.get('transparency', True):
            gl.glEnable(gl.GL_BLEND)
            blendfunc = options.get('transparency_blendfunc',
                ('SRC_ALPHA', 'ONE_MINUS_SRC_ALPHA')
                # ('ONE_MINUS_DST_ALPHA', 'ONE')
                )
            blendfunc = [getattr(gl, 'GL_' + x) for x in blendfunc]
            gl.glBlendFunc(*blendfunc)
            
        # enable depth buffer, necessary for 3D rendering
        if options.get('activate3D', None):
            gl.glEnable(gl.GL_DEPTH_TEST)
            gl.glDepthMask(gl.GL_TRUE)
            gl.glDepthFunc(gl.GL_LEQUAL)
            gl.glDepthRange(0.0, 1.0)
            # TODO: always enable??
            gl.glClearDepth(1.0)
    
        # Paint the background with the specified color (black by default)
        background = options.get('background', (0, 0, 0, 0))
        gl.glClearColor(*background)
        
    def get_renderer_option(self, name):
        return self.scene.get('renderer_options', {}).get(name, None)
        
        
    # Visual methods
    # --------------
    def get_visuals(self):
        """Return all visuals defined in the scene."""
        return self.scene.get('visuals', [])
        
    def get_visual(self, name):
        """Return a visual by its name."""
        visuals = [v for v in self.get_visuals() if v.get('name', '') == name]
        if not visuals:
            raise ValueError("The visual %s has not been found" % name)
        return visuals[0]
        
        
    # Data methods
    # ------------
    def set_data(self, name, **kwargs):
        """Load data for the specified visual. Uploading does not happen here
        but in `update_all_variables` instead, since this needs to happen
        after shader program binding in the paint method.
        
        Arguments:
          * visual: the name of the visual as a string, or a visual dict.
          * **kwargs: the data to update as name:value pairs. name can be
            any field of the visual, plus one of the following keywords:
              * size: the size of the visual,
              * primitive_type: the GL primitive type,
              * constrain_ratio: whether to constrain the ratio of the visual,
              * constrain_navigation: whether to constrain the navigation,
        
        """
        # call set_data on the given visual renderer
        if name in self.visual_renderers:
            self.visual_renderers[name].set_data(**kwargs)
        
    def copy_texture(self, name, tex1, tex2):
        self.visual_renderers[name].copy_texture(tex1, tex2)
    
        
    # Rendering methods
    # -----------------
    def initialize(self):
        """Initialize the renderer."""
        # print the renderer information
        for key, value in GLVersion.get_renderer_info().iteritems():
            if key is not None and value is not None:
                log_debug(key + ": " + value)
        # initialize the renderer options using the options set in the Scene
        self.set_renderer_options()
        # create the VisualRenderer objects
        self.visual_renderers = OrderedDict()
        for visual in self.get_visuals():
            name = visual['name']
            self.visual_renderers[name] = GLVisualRenderer(self, visual)
            
        # detect FBO
        self.fbos = []
        for name, vr in self.visual_renderers.iteritems():
            fbos = vr.get_variables('framebuffer')
            if fbos:
                self.fbos.extend([fbo['buffer'] for fbo in fbos])
            
    def clear(self):
        """Clear the scene."""
        # clear the buffer (and depth buffer is 3D is activated)
        if self.scene.get('renderer_options', {}).get('activate3D', None):
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        else:
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        
    def paint(self):
        """Paint the scene."""
        
        # non-FBO rendering
        if not self.fbos:
            self.clear()
            for name, visual_renderer in self.visual_renderers.iteritems():
                visual_renderer.paint()
        
        
        # render each FBO separately, then non-VBO
        else:
            for fbo in self.fbos:
                FrameBuffer.bind(fbo)
                
                # fbo index
                ifbo = self.fbos.index(fbo)
                
                # clear
                self.clear()
                
                # paint all visual renderers
                for name, visual_renderer in self.visual_renderers.iteritems():
                    if visual_renderer.framebuffer == ifbo:
                        # print ifbo, visual_renderer
                        visual_renderer.paint()
    
            # finally, paint screen
            FrameBuffer.unbind()
    
            # render screen (non-FBO) visuals
            self.clear()
            for name, visual_renderer in self.visual_renderers.iteritems():
                if visual_renderer.framebuffer == 'screen':
                    # print "screen", visual_renderer
                    visual_renderer.paint()
        
            # print
        
    def resize(self, width, height):
        """Resize the canvas and make appropriate changes to the scene."""
        # paint within the whole window
        gl.glViewport(0, 0, width, height)
        # compute the constrained viewport
        x = y = 1.0
        if self.get_renderer_option('constrain_ratio'):
            if height > 0:
                aw = float(width) / height
                ar = self.get_renderer_option('constrain_ratio')
                if ar is True:
                    ar = 1.
                if ar < aw:
                    x, y = aw / ar, 1.
                else:
                    x, y = 1., ar / aw
        self.viewport = x, y
        width = float(width)
        height = float(height)
        # update the viewport and window size for all visuals
        for visual in self.get_visuals():
            self.set_data(visual['name'],
                          viewport=self.viewport,
                          window_size=(width, height))
    
    
    # Cleanup methods
    # ---------------
    def cleanup(self):
        """Clean up all allocated OpenGL objects."""
        for name, renderer in self.visual_renderers.iteritems():
            renderer.cleanup()
        

########NEW FILE########
__FILENAME__ = icons
import os
from qtools.qtpy import QtCore
from qtools.qtpy import QtGui

__all__ = ['get_icon']

def get_icon(name):
    path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(path, "icons/%s.png" % name)
    icon = QtGui.QIcon(path)
    return icon


########NEW FILE########
__FILENAME__ = interactionmanager
import inspect
# from collections import OrderedDict as odict
import numpy as np
from galry import Manager, TextVisual, get_color, NavigationEventProcessor, \
    DefaultEventProcessor, EventProcessor, GridEventProcessor, ordict, \
    log_debug, log_info, log_warn


__all__ = ['InteractionManager']


class InteractionManager(Manager):
    """This class implements the processing of the raised interaction events.
    
    To be overriden.
    
    """
    
    # Initialization methods
    # ----------------------
    def __init__(self, parent):
        super(InteractionManager, self).__init__(parent)
        self.cursor = None
        self.prev_event = None
        self.processors = ordict()
        self.initialize_default(
            constrain_navigation=self.parent.constrain_navigation,
            momentum=self.parent.momentum)
        self.initialize()
        
    def initialize(self):
        """Initialize the InteractionManager.
        
        To be overriden.
        """
        pass
        
    def initialize_default(self, **kwargs):
        pass
        
        
    # Processor methods
    # -----------------
    def get_processors(self):
        """Return all processors."""
        return self.processors
        
    def get_processor(self, name):
        """Return a processor from its name."""
        if name is None:
            name = 'processor0'
        return self.processors.get(name, None)
        
    def add_processor(self, cls, *args, **kwargs):
        """Add a new processor, which handles processing of interaction events.
        Several processors can be defined in an InteractionManager instance.
        One event can be handled by several processors.
        """
        # get the name of the visual from kwargs
        name = kwargs.pop('name', 'processor%d' % (len(self.get_processors())))
        if self.get_processor(name):
            raise ValueError("Processor name '%s' already exists." % name)
        activated = kwargs.pop('activated', True)
        processor = cls(self, *args, **kwargs)
        self.processors[name] = processor
        processor.activate(activated)
        return processor
        
    def add_default_processor(self):
        """Add a default processor, useful to add handlers for events
        in the InteractionManager without explicitely creating a new
        processor."""
        return self.add_processor(EventProcessor, name='default_processor')
        
    def register(self, event, method):
        """Register a new handler for an event, using the manager's default
        processor."""
        processor = self.get_processor('default_processor')
        if processor is None:
            processor = self.add_default_processor()
        processor.register(event, method)
        
        
    # Event processing methods
    # ------------------------
    def process_event(self, event, parameter):
        """Process an event.
        
        This is the main method of this class. It is called as soon as an 
        interaction event is raised by an user action.
        
        Arguments:
          * event: the event to process, an InteractionEvent string.
          * parameter: the parameter returned by the param_getter function
            specified in the related binding.
        
        """
        # process None events in all processors
        if event is None and self.prev_event is not None:
            for name, processor in self.get_processors().iteritems():
                processor.process_none()
            self.cursor = None
        
        # process events in all processors
        if event is not None:
            for name, processor in self.get_processors().iteritems():
                if processor.activated and processor.registered(event):
                    # print name, event
                    processor.process(event, parameter)
                    cursor = processor.get_cursor()
                    if self.cursor is None:
                        self.cursor = cursor
        self.prev_event = event
        
    def get_cursor(self):
        return self.cursor
        
        
        
        
        
########NEW FILE########
__FILENAME__ = manager
class Manager(object):
    """Manager base class for all managers."""
    def __init__(self, parent):
        self.parent = parent
        self.reset()
        
    def reset(self):
        """To be implemented."""

########NEW FILE########
__FILENAME__ = default_manager
from galry.processors import NavigationEventProcessor, DefaultEventProcessor
from galry import PaintManager, InteractionManager, GridEventProcessor, \
    RectanglesVisual, GridVisual, TextVisual, Bindings, get_color


class DefaultInteractionManager(InteractionManager):
    def initialize_default(self, **kwargs):
        super(DefaultInteractionManager, self).initialize_default(**kwargs)
        self.add_processor(DefaultEventProcessor, name='widget')


class DefaultPaintManager(PaintManager):
    def initialize_default(self, **kwargs):
        super(DefaultPaintManager, self).initialize_default(**kwargs)
        # Help
        if self.parent.activate_help:
            self.add_visual(TextVisual, coordinates=(-.95, .95),
                            fontsize=14, color=get_color('w'),
                            interline=37., letter_spacing=320.,
                            depth=-1., background_transparent=False,
                            is_static=True, prevent_constrain=True,
                            text='', name='help', visible=False)
        
        
class DefaultBindings(Bindings):
    def set_fullscreen(self):
        self.set('KeyPress', 'Fullscreen', key='F')
        
    def set_help(self):
        self.set('KeyPress', 'Help', key='H')
    
    def initialize_default(self):
        super(DefaultBindings, self).initialize_default()
        self.set_fullscreen()
        self.set_help()
        
        
        
########NEW FILE########
__FILENAME__ = mesh_manager
from galry import NavigationEventProcessor, InteractionManager, \
    PaintManager, \
    GridEventProcessor, scale_matrix, rotation_matrix, translation_matrix, \
    MeshNavigationEventProcessor
from default_manager import DefaultPaintManager, DefaultInteractionManager, \
    DefaultBindings
from plot_manager import PlotBindings
import numpy as np


def load_mesh(filename):
    """Load vertices and faces from a wavefront .obj file and generate
    normals.
    
    """
    data = np.genfromtxt(filename, dtype=[('type', np.character, 1),
                                          ('points', np.float32, 3)])

    # Get vertices and faces
    vertices = data['points'][data['type'] == 'v']
    faces = (data['points'][data['type'] == 'f']-1).astype(np.uint32)

    # Build normals
    T = vertices[faces]
    N = np.cross(T[::,1 ]-T[::,0], T[::,2]-T[::,0])
    L = np.sqrt(N[:,0]**2+N[:,1]**2+N[:,2]**2)
    N /= L[:, np.newaxis]
    normals = np.zeros(vertices.shape)
    normals[faces[:,0]] += N
    normals[faces[:,1]] += N
    normals[faces[:,2]] += N
    L = np.sqrt(normals[:,0]**2+normals[:,1]**2+normals[:,2]**2)
    normals /= L[:, np.newaxis]

    # Scale vertices such that object is contained in [-1:+1,-1:+1,-1:+1]
    vmin, vmax =  vertices.min(), vertices.max()
    vertices = 2*(vertices-vmin)/(vmax-vmin) - 1

    return vertices, normals, faces

         
class MeshInteractionManager(DefaultInteractionManager):
    def initialize_default(self, constrain_navigation=None, momentum=None):
        super(MeshInteractionManager, self).initialize_default()
        self.add_processor(MeshNavigationEventProcessor, name='navigation')
        self.add_processor(GridEventProcessor, name='grid')
        
        
class MeshPaintManager(DefaultPaintManager):
    def initialize_default(self, *args, **kwargs):
        super(MeshPaintManager, self).initialize_default(*args, **kwargs)
        self.set_rendering_options(activate3D=True)
        
        
class MeshBindings(PlotBindings):
    def initialize(self):
        super(MeshBindings, self).initialize()
        self.set_rotation_mouse()
        self.set_rotation_keyboard()
    
    def set_panning_mouse(self):
        # Panning: CTRL + left button mouse
        self.set('LeftClickMove', 'Pan',
                    # key_modifier='Control',
                    param_getter=lambda p: (-4*p["mouse_position_diff"][0],
                                            -4*p["mouse_position_diff"][1]))
        
    def set_rotation_mouse(self):
        # Rotation: left button mouse
        self.set('MiddleClickMove', 'Rotation',
                    param_getter=lambda p: (3*p["mouse_position_diff"][0],
                                            3*p["mouse_position_diff"][1]))    

        self.set('LeftClickMove', 'Rotation',
                    key_modifier='Control',
                    param_getter=lambda p: (3*p["mouse_position_diff"][0],
                                            3*p["mouse_position_diff"][1]))    
             
    def set_rotation_keyboard(self):
        """Set zooming bindings with the keyboard."""
        # Rotation: ALT + key arrows
        self.set('KeyPress', 'Rotation',
                    key='Left', key_modifier='Shift', 
                    param_getter=lambda p: (-.25, 0))
        self.set('KeyPress', 'Rotation',
                    key='Right', key_modifier='Shift', 
                    param_getter=lambda p: (.25, 0))
        self.set('KeyPress', 'Rotation',
                    key='Up', key_modifier='Shift', 
                    param_getter=lambda p: (0, .25))
        self.set('KeyPress', 'Rotation',
                    key='Down', key_modifier='Shift', 
                    param_getter=lambda p: (0, -.25))
                    
    def set_zoombox_mouse(self):
        """Deactivate zoombox."""
        pass

    def set_zoombox_keyboard(self):
        """Deactivate zoombox."""
        pass
    
    def extend(self):
        """Set rotation interactions with mouse and keyboard."""
        self.set_rotation_mouse()
        self.set_rotation_keyboard()
        
        
########NEW FILE########
__FILENAME__ = plot_manager
import numpy as np
from galry.processors import NavigationEventProcessor
from default_manager import DefaultPaintManager, DefaultInteractionManager, \
    DefaultBindings
from galry import GridEventProcessor, RectanglesVisual, GridVisual, Bindings, \
    DataNormalizer


class PlotPaintManager(DefaultPaintManager):
    def initialize_default(self):
        super(PlotPaintManager, self).initialize_default()
        # Navigation rectangle
        self.add_visual(RectanglesVisual, coordinates=(0.,) * 4,
                        # depth=1.,
                        color=self.navigation_rectangle_color, 
                        is_static=True,
                        name='navigation_rectangle',
                        visible=False)
        
        # Grid
        if self.parent.activate_grid:
            # show_grid = self.parent.show_grid
            # show_grid = getattr(self.parent, 'show_grid', False)
            self.add_visual(GridVisual, name='grid', visible=False)

    def finalize(self):
        if not hasattr(self, 'normalization_viewbox'):
            self.normalization_viewbox = (None,) * 4
        # compute the global viewbox
        visuals = self.get_visuals()
        xmin, ymin, xmax, ymax = self.normalization_viewbox
        # print xmin, ymin, xmax, ymax
        nx0 = xmin is None
        nx1 = xmax is None
        ny0 = ymin is None
        ny1 = ymax is None
        alldata = []
        for visual in visuals:
            vars = visual['variables']
            attrs = [var for var in vars if var['shader_type'] == 'attribute']
            datalist = [attr['data'] for attr in attrs if 'data' in attr and \
                isinstance(attr['data'], np.ndarray) and \
                attr['data'].size > 0 and attr['data'].ndim == 2 and \
                attr.get('autonormalizable', None)]
            alldata.extend(datalist)
            for data in datalist:
                # print visual['name'], data.shape
                # continue
                # if xmin is None:
                    # x0 = data[:,0].min()
                # else:
                    # x0 = xmin
                if nx0:
                    x0 = data[:,0].min()
                    if xmin is None:
                        xmin = x0
                    else:
                        xmin = min(xmin, x0)
                        
                if nx1:
                    x1 = data[:,0].max()
                    if xmax is None:
                        xmax = x1
                    else:
                        xmax = max(xmax, x1)
                        
                if ny0:
                    y0 = data[:,1].min()
                    if ymin is None:
                        ymin = y0
                    else:
                        ymin = min(ymin, y0)
                if ny1:
                    
                    y1 = data[:,1].max()
                    if ymax is None:
                        ymax = y1
                    else:
                        ymax = max(ymax, y1)
                # x0, x1 = data[:,0].min(), data[:,0].max()
                # y0, y1 = data[:,1].min(), data[:,1].max()
                # print x0, y0, x1, y1
        # print xmin, ymin, xmax, ymax
        self.normalization_viewbox = (xmin, ymin, xmax, ymax)
        normalizer = DataNormalizer()
        normalizer.normalize(self.normalization_viewbox)
        tr_x = normalizer.normalize_x
        tr_y = normalizer.normalize_y
        for data in alldata:
            data[:,0] = tr_x(data[:,0])
            data[:,1] = tr_y(data[:,1])
            

class PlotInteractionManager(DefaultInteractionManager):
    def initialize_default(self, constrain_navigation=None,
        momentum=False,
        # normalization_viewbox=None
        ):
        super(PlotInteractionManager, self).initialize_default()
        self.add_processor(NavigationEventProcessor,
            constrain_navigation=constrain_navigation, 
            # normalization_viewbox=normalization_viewbox,
            momentum=momentum,
            name='navigation')
        self.add_processor(GridEventProcessor, name='grid')#, activated=False)
        
        
class PlotBindings(DefaultBindings):
    """A default set of bindings for interactive navigation.
    
    This binding set makes use of the keyboard and the mouse.
    
    """
    def set_grid(self):
        self.set('KeyPress', 'Grid', key='G')
    
    def set_panning_mouse(self):
        """Set panning bindings with the mouse."""
        # Panning: left button mouse
        self.set('LeftClickMove', 'Pan',
                    param_getter=lambda p: (p["mouse_position_diff"][0],
                                            p["mouse_position_diff"][1]))
        
    def set_panning_keyboard(self):
        """Set panning bindings with the keyboard."""
        # Panning: keyboard arrows
        self.set('KeyPress', 'Pan',
                    key='Left', description='Left',
                    param_getter=lambda p: (.24, 0))
        self.set('KeyPress', 'Pan',
                    key='Right', description='Right',
                    param_getter=lambda p: (-.24, 0))
        self.set('KeyPress', 'Pan',
                    key='Up', description='Up',
                    param_getter=lambda p: (0, -.24))
        self.set('KeyPress', 'Pan',
                    key='Down', description='Down',
                    param_getter=lambda p: (0, .24))
                
    def set_zooming_mouse(self):
        """Set zooming bindings with the mouse."""
        # Zooming: right button mouse
        self.set('RightClickMove', 'Zoom',
                    param_getter=lambda p: (p["mouse_position_diff"][0]*2.5,
                                            p["mouse_press_position"][0],
                                            p["mouse_position_diff"][1]*2.5,
                                            p["mouse_press_position"][1]))
    
    def set_zoombox_mouse(self):
        """Set zoombox bindings with the mouse."""
        # Zooming: zoombox (drag and drop)
        self.set('MiddleClickMove', 'ZoomBox',
                    param_getter=lambda p: (p["mouse_press_position"][0],
                                            p["mouse_press_position"][1],
                                            p["mouse_position"][0],
                                            p["mouse_position"][1]))
    
    def set_zoombox_keyboard(self):
        """Set zoombox bindings with the keyboard."""
        # Idem but with CTRL + left button mouse 
        self.set('LeftClickMove', 'ZoomBox',
                    key_modifier='Control',
                    param_getter=lambda p: (p["mouse_press_position"][0],
                                            p["mouse_press_position"][1],
                                            p["mouse_position"][0],
                                            p["mouse_position"][1]))
                 
    def set_zooming_keyboard(self):
        """Set zooming bindings with the keyboard."""
        # Zooming: ALT + key arrows
        self.set('KeyPress', 'Zoom',
                    key='Left', description='X-', key_modifier='Control', 
                    param_getter=lambda p: (-.25, 0, 0, 0))
        self.set('KeyPress', 'Zoom',
                    key='Right', description='X+', key_modifier='Control', 
                    param_getter=lambda p: (.25, 0, 0, 0))
        self.set('KeyPress', 'Zoom',
                    key='Up', description='Y+', key_modifier='Control', 
                    param_getter=lambda p: (0, 0, .25, 0))
        self.set('KeyPress', 'Zoom',
                    key='Down', description='Y-', key_modifier='Control', 
                    param_getter=lambda p: (0, 0, -.25, 0))
        
    def set_zooming_wheel(self):
        """Set zooming bindings with the wheel."""
        # Zooming: wheel
        self.set('Wheel', 'Zoom',
                    param_getter=lambda p: (
                                    p["wheel"]*.002, 
                                    p["mouse_position"][0],
                                    p["wheel"]*.002, 
                                    p["mouse_position"][1]))
        
    def set_zooming_pinch(self):
        self.set('Pinch', 'Zoom', param_getter=lambda p: 
            (
            # pinch position does not appear to be well calibrated
             p["pinch_scale_diff"],
             0, # p["pinch_start_position"][0],  
             p["pinch_scale_diff"],
             0, # p["pinch_start_position"][1],
             ))

    def set_reset(self):
        """Set reset bindings."""
        # Reset view
        self.set('KeyPress', 'Reset', key='R')
        # Reset zoom
        self.set('DoubleClick', 'Reset')
        
    def initialize_default(self):
        super(PlotBindings, self).initialize_default()
        """Initialize all bindings. Can be overriden."""
        self.set_base_cursor()
        self.set_grid()
        # panning
        self.set_panning_mouse()
        self.set_panning_keyboard()
        # zooming
        self.set_zooming_mouse()
        self.set_zoombox_mouse()
        self.set_zoombox_keyboard()
        self.set_zooming_keyboard()
        self.set_zooming_wheel()
        self.set_zooming_pinch()
        # reset
        self.set_reset()
        # Extended bindings
        # self.extend()
        
    # def extend(self):
        # """Initialize custom bindings. Can be overriden."""
        # pass
        
        
########NEW FILE########
__FILENAME__ = paintmanager
import numpy as np
import OpenGL.GL as gl
from galry import log_debug, log_info, log_warn, get_color, GLRenderer, \
    Manager, TextVisual, RectanglesVisual, SceneCreator, serialize, \
    GridVisual

__all__ = ['PaintManager']


# PaintManager class
# ------------------                   
class PaintManager(Manager):
    """Defines what to render in the widget."""
    
    # Background color.
    bgcolor = (0., 0., 0., 0.)
    
    # Color of the zoombox rectangle.
    navigation_rectangle_color = (1., 1., 1., .25)
    
    
    # Initialization methods
    # ----------------------
    def reset(self):
        """Reset the scene."""
        # create the scene creator
        self.scene_creator = SceneCreator(
                    constrain_ratio=self.parent.constrain_ratio)
        self.data_updating = {}
        
    def set_rendering_options(self, **kwargs):
        """Set rendering options in the scene."""
        self.scene_creator.get_scene()['renderer_options'].update(**kwargs)
        
    # def initialize(self):
        # """Define the scene. To be overriden."""
        
    def initialize_default(self, **kwargs):
        # FPS
        if self.parent.display_fps:
            self.add_visual(TextVisual, text='FPS: 000', name='fps',
                            fontsize=18,
                            coordinates=(-.80, .92),
                            visible=False,
                            is_static=True)
        
        
    # Visual methods
    # --------------
    def get_visuals(self):
        """Return all visuals defined in the scene."""
        return self.scene_creator.get_visuals()
        
    def get_visual(self, name):
        return self.scene_creator.get_visual(name)
        
    # def get_variables(self, visual):
        # visual['variables']
        
    
    # Navigation rectangle methods
    # ----------------------------
    def show_navigation_rectangle(self, coordinates):
        """Show the navigation rectangle with the specified coordinates 
        (in relative window coordinates)."""
        self.set_data(coordinates=coordinates, visible=True,
                      visual='navigation_rectangle')
            
    def hide_navigation_rectangle(self):
        """Hide the navigation rectangle."""
        self.set_data(visible=False, visual='navigation_rectangle')
        
        
    # Visual reinitialization methods
    # -------------------------------
    def reinitialize_visual(self, visual=None, **kwargs):
        """Reinitialize a visual, by calling visual.initialize() after
        initialization, just to update the data.
        
        This function retrieves the data of all variables, as specified in
        visual.initialize(), and call paint_manager.set_data with this 
        information.
        
        """
        if visual is None:
            visual = 'visual0'
        name = visual
        # retrieve the visual dictionary
        visual = self.scene_creator.get_visual_object(visual)
        # tell the visual we want to reinitialize it
        visual.reinit()
        # resolve the reference variables
        kwargs = visual.resolve_references(**kwargs)
        # handle special keywords (TODO: improve this, maybe by storing this
        # list somewhere)
        data_updating = {}
        data_updating0 = {}
        special_keywords = ['visible',
                            'size',
                            'bounds',
                            'primitive_type',
                            'constrain_ratio',
                            'constrain_navigation',
                            ]
        for kw in special_keywords:
            if kw in kwargs:
                data_updating0[kw] = kwargs.pop(kw)
        # extract common parameters
        # kwargs = visual.extract_common_parameters(**kwargs)
        # call initialize with the new arguments
        visual.initialize(**kwargs)
        # call finalize again in the visual
        visual.finalize()
        # retrieve the updated data for all variables
        data_updating.update(visual.get_data_updating())
        # keywords given here in kwargs have higher priority than those in
        # get_data_updating
        data_updating.update(data_updating0)
        # finally, call set_data
        self.set_data(visual=name, **data_updating)
        
        
    # Visual creation methods
    # -----------------------
    def add_visual(self, visual_class, *args, **kwargs):
        """Add a visual. This method should be called in `self.initialize`.
        
        A visual is an instanciation of a `Visual`. A Visual
        defines a pattern for one, or a homogeneous set of plotting objects.
        Example: a text string, a set of rectangles, a set of triangles,
        a set of curves, a set of points. A set of points and rectangles
        does not define a visual since it is not an homogeneous set of
        objects. The technical reason for this distinction is that OpenGL
        allows for very fast rendering of homogeneous objects by calling
        a single rendering command (even if several objects of the same type
        need to be rendered, e.g. several rectangles). The lower the number
        of rendering calls, the better the performance.
        
        Hence, a visual is defined by a particular Visual, and by
        specification of fields in this visual (positions of the points,
        colors, text string for the example of the TextVisual, etc.). It
        also comes with a number `N` which is the number of vertices contained
        in the visual (N=4 for one rectangle, N=len(text) for a text since 
        every character is rendered independently, etc.)
        
        Several visuals can be created in the PaintManager, but performance
        decreases with the number of visuals, so that all homogeneous 
        objects to be rendered on the screen at the same time should be
        grouped into a single visual (e.g. multiple line plots).
        
        Arguments:
          * visual_class=None: the visual class, deriving from
            `Visual` (or directly from the base class `DataVisual`
            if you don't want the navigation-related functionality).
          * visible=True: whether this visual should be rendered. Useful
            for showing/hiding a transient element. When hidden, the visual
            does not go through the rendering pipeline at all.
          
        Returns:
          * visual: a dictionary containing all the information about
            the visual, and that can be used in `set_data`.
        
        """
        self.scene_creator.add_visual(visual_class, *args, **kwargs)
        
    def set_data(self, visual=None, **kwargs):
        """Specify or change the data associated to particular visual
        fields.
        
        Actual data upload on the GPU will occur during the rendering process, 
        in `paintGL`. It is just recorded here for later use.
        
        Arguments:
          * visual=None: the relevant visual. By default, the first one
            that has been created in `initialize`.
          * **kwargs: keyword arguments as `visual_field_name: value` pairs.
        
        """
        # default name
        if visual is None:
            visual = 'visual0'
        # if this method is called in initialize (the renderer is then not
        # defined) we save the data to be updated later
        # print hasattr(self, 'renderer'), kwargs
        if not hasattr(self, 'renderer'):
            self.data_updating[visual] = kwargs
        else:
            self.renderer.set_data(visual, **kwargs)
            # empty data_updating
            if visual in self.data_updating:
                self.data_updating[visual] = {}
    
    def copy_texture(self, tex1, tex2, visual=None):
        # default name
        if visual is None:
            visual = 'visual0'
        self.renderer.copy_texture(visual, tex1, tex2)
    
    def update_fps(self, fps):
        """Update the FPS in the corresponding text visual."""
        self.set_data(visual='fps', text="FPS: %03d" % fps, visible=True)
 
 
    # Rendering methods
    # -----------------
    def initializeGL(self):
        # initialize the scene
        self.initialize()
        self.initialize_default()
        # finalize
        self.finalize()
        # initialize the renderer
        self.renderer = GLRenderer(self.scene_creator.get_scene())
        self.renderer.initialize()
        # update the variables (with set_data in paint_manager.initialize())
        # after initialization
        for visual, kwargs in self.data_updating.iteritems():
            self.set_data(visual=visual, **kwargs)
 
    def paintGL(self):
        if hasattr(self, 'renderer'):
            self.renderer.paint()
        gl.glFlush()
 
    def resizeGL(self, width, height):
        if hasattr(self, 'renderer'):
            self.renderer.resize(width, height)
        gl.glFlush()
        
    def updateGL(self):
        """Call updateGL in the parent widget."""
        self.parent.updateGL()
        
        
    # Cleanup methods
    # ---------------
    def cleanup(self):
        """Cleanup all visuals."""
        if hasattr(self, 'renderer'):
            self.renderer.cleanup()
        
        
    # Methods to be overriden
    # -----------------------
    def initialize(self):
        """Initialize the scene creation. To be overriden.

        This method can make calls to `add_visual` and `set_data` methods.
        
        """
        pass
        
    def finalize(self):
        """Finalize the scene creation. To be overriden.
        """
        pass

        
    # Serialization methods
    # ---------------------
    def serialize(self):
        return self.scene_creator.serialize()
        
        
        
########NEW FILE########
__FILENAME__ = default_processor
import inspect
import numpy as np
from processor import EventProcessor
from galry import Manager, TextVisual, get_color, ordict


class DefaultEventProcessor(EventProcessor):
    def initialize(self):
        self.register('Fullscreen', self.process_toggle_fullscreen)
        self.register('Help', self.process_help_event)
        self.help_visible = False
        
    def process_toggle_fullscreen(self, parameter):
        self.parent.toggle_fullscreen()
        
    def process_help_event(self, parameter):
        self.help_visible = not(self.help_visible)
        text = self.parent.binding_manager.get().get_text()
        self.set_data(visual='help', visible=self.help_visible, text=text)
        
        
########NEW FILE########
__FILENAME__ = grid_processor
import inspect
# from collections import OrderedDict as odict
import numpy as np
from processor import EventProcessor
from galry import DataNormalizer

NTICKS = 10

__all__ = ['GridEventProcessor']


# http://books.google.co.uk/books?id=fvA7zLEFWZgC&lpg=PA61&hl=fr&pg=PA62#v=onepage&q&f=false
def nicenum(x, round=False):
    e = np.floor(np.log10(x))
    f = x / 10 ** e
    eps = 1e-6
    if round:
        if f < 1.5:
            nf = 1.
        elif f < 3:
            nf = 2.
        elif f < 7.:
            nf = 5.
        else:
            nf = 10.
    else:
        if f < 1 - eps:
            nf = 1.
        elif f < 2 - eps:
            nf = 2.
        elif f < 5 - eps:
            nf = 5.
        else:
            nf = 10.
    return nf * 10 ** e
    
def get_ticks(x0, x1):
    nticks = NTICKS
    r = nicenum(x1 - x0, False)
    d = nicenum(r / (nticks - 1), True)
    g0 = np.floor(x0 / d) * d
    g1 = np.ceil(x1 / d) * d
    nfrac = int(max(-np.floor(np.log10(d)), 0))
    return np.arange(g0, g1 + .5 * d, d), nfrac
  
def format_number(x, nfrac=None):
    if nfrac is None:
        nfrac = 2
    
    if np.abs(x) < 1e-15:
        return "0"
        
    elif np.abs(x) > 100.001:
        return "%.3e" % x
        
    if nfrac <= 2:
        return "%.2f" % x
    else:
        nfrac = nfrac + int(np.log10(np.abs(x)))
        return ("%." + str(nfrac) + "e") % x

def get_ticks_text(x0, y0, x1, y1):
    ticksx, nfracx = get_ticks(x0, x1)
    ticksy, nfracy = get_ticks(y0, y1)
    n = len(ticksx)
    text = [format_number(x, nfracx) for x in ticksx]
    text += [format_number(x, nfracy) for x in ticksy]
    # position of the ticks
    coordinates = np.zeros((len(text), 2))
    coordinates[:n, 0] = ticksx
    coordinates[n:, 1] = ticksy
    return text, coordinates, n
    
    
class GridEventProcessor(EventProcessor):
    def initialize(self):
        self.register('Initialize', self.update_axes)
        self.register('Pan', self.update_axes)
        self.register('Zoom', self.update_axes)
        self.register('Reset', self.update_axes)
        self.register('Animate', self.update_axes)
        self.register(None, self.update_axes)
        
    def update_axes(self, parameter):
        nav = self.get_processor('navigation')
        # print nav
        if not nav:
            return
        
        viewbox = nav.get_viewbox()
        
        # nvb = nav.normalization_viewbox
        nvb = getattr(self.parent.paint_manager, 'normalization_viewbox', None)
        # print nvb
        # initialize the normalizer
        if nvb is not None:
            if not hasattr(self, 'normalizer'):
                # normalization viewbox
                self.normalizer = DataNormalizer()
                self.normalizer.normalize(nvb)
            x0, y0, x1, y1 = viewbox
            x0 = self.normalizer.unnormalize_x(x0)
            y0 = self.normalizer.unnormalize_y(y0)
            x1 = self.normalizer.unnormalize_x(x1)
            y1 = self.normalizer.unnormalize_y(y1)
            viewbox = (x0, y0, x1, y1)
            # print nvb, viewbox
        
        text, coordinates, n = get_ticks_text(*viewbox)
        
        if nvb is not None:
            coordinates[:,0] = self.normalizer.normalize_x(coordinates[:,0])
            coordinates[:,1] = self.normalizer.normalize_y(coordinates[:,1])
        
        
        # here: coordinates contains positions centered on the static
        # xy=0 axes of the screen
        position = np.repeat(coordinates, 2, axis=0)
        position[:2 * n:2,1] = -1
        position[1:2 * n:2,1] = 1
        position[2 * n::2,0] = -1
        position[2 * n + 1::2,0] = 1
        
        axis = np.zeros(len(position))
        axis[2 * n:] = 1
        
        self.set_data(visual='grid_lines', position=position, axis=axis)
        
        coordinates[n:, 0] = -.95
        coordinates[:n, 1] = -.95
    
        t = "".join(text)
        n1 = len("".join(text[:n]))
        n2 = len("".join(text[n:]))
        
        axis = np.zeros(n1+n2)
        axis[n1:] = 1
        
        self.set_data(visual='grid_text', text=text,
            coordinates=coordinates,
            axis=axis)
            
########NEW FILE########
__FILENAME__ = mesh_processor
from navigation_processor import NavigationEventProcessor
from galry import scale_matrix, rotation_matrix, translation_matrix
import numpy as np

def get_transform(translation, rotation, scale):
    """Return the transformation matrix corresponding to a given
    translation, rotation, and scale.
    
    Arguments:
      * translation: the 3D translation vector,
      * rotation: the 2D rotation coefficients
      * scale: a float with the scaling coefficient.
    
    Returns:
      * M: the 4x4 transformation matrix.
      
    """
    # translation is a vec3, rotation a vec2, scale a float
    S = scale_matrix(scale, scale, scale)
    R = rotation_matrix(rotation[0], axis=1)
    R = np.dot(R, rotation_matrix(rotation[1], axis=0))
    T = translation_matrix(*translation)
    return np.dot(S, np.dot(R, T))
    

class MeshNavigationEventProcessor(NavigationEventProcessor):
    def pan(self, parameter):
        """3D pan (only x,y)."""
        self.tx += parameter[0]
        self.ty += parameter[1]
        
    def zoom(self, parameter):
        """Zoom."""
        dx, px, dy, py = parameter
        if (dx >= 0) and (dy >= 0):
            dx, dy = (max(dx, dy),) * 2
        elif (dx <= 0) and (dy <= 0):
            dx, dy = (min(dx, dy),) * 2
        else:
            dx = dy = 0
        self.sx *= np.exp(dx)
        self.sy *= np.exp(dy)
        self.sxl = self.sx
        self.syl = self.sy
        
    def get_translation(self):
        return self.tx, self.ty, self.tz
        
    def transform_view(self):
        """Upload the transformation matrices as a function of the
        interaction variables in the InteractionManager."""
        translation = self.get_translation()
        rotation = self.get_rotation()
        scale = self.get_scaling()
        for visual in self.paint_manager.get_visuals():
            if not visual.get('is_static', False):
                self.set_data(visual=visual['name'], 
                              transform=get_transform(translation, rotation, scale[0]))
                              
                         
########NEW FILE########
__FILENAME__ = navigation_processor
import inspect
import time
import numpy as np
from processor import EventProcessor
from galry import Manager, TextVisual, get_color


__all__ = ['NavigationEventProcessor']

      
# Maximum viewbox allowed when constraining navigation.
MAX_VIEWBOX = (-1., -1., 1., 1.)

class NavigationEventProcessor(EventProcessor):
    """Handle navigation-related events."""
    def initialize(self, constrain_navigation=False,
        normalization_viewbox=None, momentum=False):
        # zoom box
        self.navigation_rectangle = None
        self.constrain_navigation = constrain_navigation
        self.normalization_viewbox = normalization_viewbox
        
        self.reset()
        self.set_navigation_constraints()
        self.activate_navigation_constrain()
        
        # register events processors
        self.register('Pan', self.process_pan_event)
        self.register('Rotation', self.process_rotation_event)
        self.register('Zoom', self.process_zoom_event)
        self.register('ZoomBox', self.process_zoombox_event)
        self.register('Reset', self.process_reset_event)
        self.register('ResetZoom', self.process_resetzoom_event)
        self.register('SetPosition', self.process_setposition_event)
        self.register('SetViewbox', self.process_setviewbox_event)
        
        # Momentum
        if momentum:
            self.register('Animate', self.process_animate_event)
            
        self.pan_list = []
        self.pan_list_maxsize = 10
        self.pan_vec = np.zeros(2)
        self.is_panning = False
        self.momentum = False
        
        self.register('Grid', self.process_grid_event)
        self.grid_visible = getattr(self.parent, 'show_grid', False)
        self.activate_grid()
        
    def activate_grid(self):
        self.set_data(visual='grid_lines', visible=self.grid_visible)
        self.set_data(visual='grid_text', visible=self.grid_visible)
        processor = self.get_processor('grid')
        # print processor
        if processor:
            processor.activate(self.grid_visible)
            if self.grid_visible:
                processor.update_axes(None)
        
    def process_grid_event(self, parameter):
        self.grid_visible = not(self.grid_visible)
        self.activate_grid()
        
    def transform_view(self):
        """Change uniform variables to implement interactive navigation."""
        translation = self.get_translation()
        scale = self.get_scaling()
        # update all non static visuals
        for visual in self.paint_manager.get_visuals():
            if not visual.get('is_static', False):
                self.set_data(visual=visual['name'], 
                              scale=scale, translation=translation)
        
        
    # Event processing methods
    # ------------------------
    def process_none(self):
        """Process the None event, i.e. where there is no event. Useful
        to trigger an action at the end of a long-lasting event."""
        # when zoombox event finished: set_relative_viewbox
        if (self.navigation_rectangle is not None):
            self.set_relative_viewbox(*self.navigation_rectangle)
            self.paint_manager.hide_navigation_rectangle()
        self.navigation_rectangle = None
        # Trigger panning momentum
        if self.is_panning:
            self.is_panning = False
            if len(self.pan_list) >= self.pan_list_maxsize:
                self.momentum = True
        self.parent.block_refresh = False
        # self.set_cursor(None)
        self.transform_view()

    def add_pan(self, parameter):
        # Momentum.
        self.pan_list.append(parameter)
        if len(self.pan_list) > self.pan_list_maxsize:
            del self.pan_list[0]
        self.pan_vec = np.array(self.pan_list).mean(axis=0)
        
    def process_pan_event(self, parameter):
        # Momentum.
        self.is_panning = True
        self.momentum = False
        self.parent.block_refresh = False
        self.add_pan(parameter)
        
        self.pan(parameter)
        self.set_cursor('ClosedHandCursor')
        self.transform_view()

    def process_animate_event(self, parameter):
        # Momentum.
        if self.is_panning:
            self.add_pan((0., 0.))
        if self.momentum:
            self.pan(self.pan_vec)
            self.pan_vec *= .975
            # End momentum.
            if (np.abs(self.pan_vec) < .0001).all():
                self.momentum = False
                self.parent.block_refresh = True
                self.pan_list = []
                self.pan_vec = np.zeros(2)
            self.transform_view()
    
    def process_rotation_event(self, parameter):
        self.rotate(parameter)
        self.set_cursor('ClosedHandCursor')
        self.transform_view()

    def process_zoom_event(self, parameter):
        self.zoom(parameter)
        self.parent.block_refresh = False
        # Block momentum when zooming.
        self.momentum = False
        self.set_cursor('MagnifyingGlassCursor')
        self.transform_view()
        
    def process_zoombox_event(self, parameter):
        self.zoombox(parameter)
        self.parent.block_refresh = False
        self.set_cursor('MagnifyingGlassCursor')
        self.transform_view()
    
    def process_reset_event(self, parameter):
        self.reset()
        self.parent.block_refresh = False
        self.set_cursor(None)
        self.transform_view()

    def process_resetzoom_event(self, parameter):
        self.reset_zoom()
        self.parent.block_refresh = False
        self.set_cursor(None)
        self.transform_view()
        
    def process_setposition_event(self, parameter):
        self.set_position(*parameter)
        self.parent.block_refresh = False
        self.transform_view()
        
    def process_setviewbox_event(self, parameter):
        self.set_viewbox(*parameter)
        self.parent.block_refresh = False
        self.transform_view()
    
        
    # Navigation methods
    # ------------------    
    def set_navigation_constraints(self, constraints=None, maxzoom=1e6):
        """Set the navigation constraints.
        
        Arguments:
          * constraints=None: the coordinates of the bounding box as 
            (xmin, ymin, xmax, ymax), by default (+-1).
        
        """
        if not constraints:
            constraints = MAX_VIEWBOX
        # view constraints
        self.xmin, self.ymin, self.xmax, self.ymax = constraints
        # minimum zoom allowed
        self.sxmin = 1./min(self.xmax, -self.xmin)
        self.symin = 1./min(self.ymax, -self.ymin)
        # maximum zoom allowed
        self.sxmax = self.symax = maxzoom
        
    def reset(self):
        """Reset the navigation."""
        self.tx, self.ty, self.tz = 0., 0., 0.
        self.sx, self.sy = 1., 1.
        self.sxl, self.syl = 1., 1.
        self.rx, self.ry = 0., 0.
        self.navigation_rectangle = None
    
    def pan(self, parameter):
        """Pan along the x,y coordinates.
        
        Arguments:
          * parameter: (dx, dy)
        
        """
        self.tx += parameter[0] / self.sx
        self.ty += parameter[1] / self.sy
    
    def rotate(self, parameter):
        self.rx += parameter[0]
        self.ry += parameter[1]
    
    def zoom(self, parameter):
        """Zoom along the x,y coordinates.
        
        Arguments:
          * parameter: (dx, px, dy, py)
        
        """
        dx, px, dy, py = parameter
        if self.parent.constrain_ratio:
            if (dx >= 0) and (dy >= 0):
                dx, dy = (max(dx, dy),) * 2
            elif (dx <= 0) and (dy <= 0):
                dx, dy = (min(dx, dy),) * 2
            else:
                dx = dy = 0
        self.sx *= np.exp(dx)
        self.sy *= np.exp(dy)
        
        # constrain scaling
        if self.constrain_navigation:
            self.sx = np.clip(self.sx, self.sxmin, self.sxmax)
            self.sy = np.clip(self.sy, self.symin, self.symax)
        
        self.tx += -px * (1./self.sxl - 1./self.sx)
        self.ty += -py * (1./self.syl - 1./self.sy)
        self.sxl = self.sx
        self.syl = self.sy
    
    def zoombox(self, parameter):
        """Indicate to draw a zoom box.
        
        Arguments:
          * parameter: the box coordinates (xmin, ymin, xmax, ymax)
        
        """
        self.navigation_rectangle = parameter
        self.paint_manager.show_navigation_rectangle(parameter)
    
    def reset_zoom(self):
        """Reset the zoom."""
        self.sx, self.sy = 1, 1
        self.sxl, self.syl = 1, 1
        self.navigation_rectangle = None
    
    def get_viewbox(self, scale=1.):
        """Return the coordinates of the current view box.
        
        Returns:
          * (xmin, ymin, xmax, ymax): the current view box in data coordinate
            system.
            
        """
        x0, y0 = self.get_data_coordinates(-scale, -scale)
        x1, y1 = self.get_data_coordinates(scale, scale)
        return (x0, y0, x1, y1)
    
    def get_data_coordinates(self, x, y):
        """Convert window relative coordinates into data coordinates.
        
        Arguments:
          * x, y: coordinates in [-1, 1] of a point in the window.
          
        Returns:
          * x', y': coordinates of this point in the data coordinate system.
        
        """
        return x/self.sx - self.tx, y/self.sy - self.ty
        
    def get_window_coordinates(self, x, y):
        """Inverse of get_data_coordinates.
        """
        return (x + self.tx) * self.sx, (y + self.ty) * self.sy
    
    def constrain_viewbox(self, x0, y0, x1, y1):
        """Constrain the viewbox ratio."""
        if (x1-x0) > (y1-y0):
            d = ((x1-x0)-(y1-y0))/2
            y0 -= d
            y1 += d
        else:
            d = ((y1-y0)-(x1-x0))/2
            x0 -= d
            x1 += d
        return x0, y0, x1, y1
    
    def set_viewbox(self, x0, y0, x1, y1):
        """Set the view box in the data coordinate system.
        
        Arguments:
          * x0, y0, x1, y1: viewbox coordinates in the data coordinate system.
        
        """
        # force the zoombox to keep its original ratio
        if self.parent.constrain_ratio:
            x0, y0, x1, y1 = self.constrain_viewbox(x0, y0, x1, y1)
        if (x1-x0) and (y1-y0):
            self.tx = -(x1+x0)/2
            self.ty = -(y1+y0)/2
            self.sx = 2./abs(x1-x0)
            self.sy = 2./abs(y1-y0)
            self.sxl, self.syl = self.sx, self.sy
    
    def set_relative_viewbox(self, x0, y0, x1, y1):
        """Set the view box in the window coordinate system.
        
        Arguments:
          * x0, y0, x1, y1: viewbox coordinates in the window coordinate system.
            These coordinates are all in [-1, 1].
        
        """
        # prevent too small zoombox
        if (np.abs(x1 - x0) < .07) & (np.abs(y1 - y0) < .07):
            return
        # force the zoombox to keep its original ratio
        if self.parent.constrain_ratio:
            x0, y0, x1, y1 = self.constrain_viewbox(x0, y0, x1, y1)
        if (x1-x0) and (y1-y0):
            self.tx += -(x1+x0)/(2*self.sx)
            self.ty += -(y1+y0)/(2*self.sy)
            self.sx *= 2./abs(x1-x0)
            self.sy *= 2./abs(y1-y0)
            self.sxl, self.syl = self.sx, self.sy
    
    def set_position(self, x, y):
        """Set the current position.
        
        Arguments:
          * x, y: coordinates in the data coordinate system.
        
        """
        self.tx = -x
        self.ty = -y
    
    def activate_navigation_constrain(self):
        """Constrain the navigation to a bounding box."""
        if self.constrain_navigation:
            # constrain scaling
            self.sx = np.clip(self.sx, self.sxmin, self.sxmax)
            self.sy = np.clip(self.sy, self.symin, self.symax)
            # constrain translation
            self.tx = np.clip(self.tx, 1./self.sx - self.xmax,
                                      -1./self.sx - self.xmin)
            self.ty = np.clip(self.ty, 1./self.sy + self.ymin,
                                      -1./self.sy + self.ymax)
        else:
            # constrain maximum zoom anyway
            self.sx = min(self.sx, self.sxmax)
            self.sy = min(self.sy, self.symax)
    
    def get_translation(self):
        """Return the translation vector.
        
        Returns:
          * tx, ty: translation coordinates.
        
        """
        self.activate_navigation_constrain()
        return self.tx, self.ty
    
    def get_rotation(self):
        return self.rx, self.ry
    
    def get_scaling(self):
        """Return the scaling vector.
        
        Returns:
          * sx, sy: scaling coordinates.
        
        """
        if self.constrain_navigation:
            self.activate_navigation_constrain()
        return self.sx, self.sy

 

########NEW FILE########
__FILENAME__ = processor
import inspect
import numpy as np
from galry import Manager, TextVisual, get_color
# from galry import InteractionManager
import galry

__all__ = ['EventProcessor']

class EventProcessor(object):
    """Process several related events."""
    def __init__(self, interaction_manager, *args, **kwargs):
        self.interaction_manager = interaction_manager
        self.parent = interaction_manager.parent
        self.handlers = {}
        
        # current cursor and base cursor for the active interaction mode
        self.cursor = None
        # self.base_cursor = None
        
        self.activate()
        
        self.initialize(*args, **kwargs)
        
    def get_processor(self, name):
        """Return a processor in the Manager from its name."""
        return self.interaction_manager.get_processor(name)
        
        
    # Paint Manager methods
    # ---------------------
    def _get_paint_manager(self):
        return self.interaction_manager.paint_manager
    paint_manager = property(_get_paint_manager)
        
    def set_data(self, *args, **kwargs):
        """PaintManager.set_data."""
        # shortcut to paint_manager.set_data
        return self.parent.paint_manager.set_data(*args, **kwargs)
        
    def get_visual(self, name):
        """Get a visual in the PaintManager from its name."""
        return self.parent.paint_manager.get_visual(name)
        
    def add_visual(self, *args, **kwargs):
        """Add a new visual in the paint manager."""
        name = kwargs.get('name')
        if not self.get_visual(name):
            self.parent.paint_manager.add_visual(*args, **kwargs)
        
        
    # Cursor methods
    # --------------
    def set_cursor(self, cursor):
        self.cursor = cursor
        
    def get_cursor(self):
        """Return the current cursor."""
        return self.cursor


    # Activation methods
    # ------------------
    def activate(self, boo=True):
        """Activate or deactivate a processor."""
        self.activated = boo
    
    def deactivate(self):
        """Deactive the processor."""
        self.activated = False
    
    
    # Handlers methods
    # ----------------
    def register(self, event, method):
        """Register a handler for the event."""
        self.handlers[event] = method
        
    def registered(self, event):
        """Return whether the specified event has been registered by this
        processor."""
        return self.handlers.get(event, None) is not None
        
    def process(self, event, parameter):
        """Process an event by calling the registered handler if there's one.
        """
        method = self.handlers.get(event, None)
        if method:
            # if the method is a method of a class deriving from EventProcessor
            # we pass just parameter
            if (inspect.ismethod(method) and 
                (EventProcessor in inspect.getmro(method.im_class) or
                 galry.InteractionManager in inspect.getmro(method.im_class))):
                method(parameter)
            else:
                fig = self.interaction_manager.figure
                # HACK: give access to paint_manager.set_data to the figure,
                # so that event processors can change the data
                # BAD SMELL HERE :(
                if not hasattr(fig, 'set_data'):
                    fig.set_data = self.parent.paint_manager.set_data
                    fig.copy_texture = self.parent.paint_manager.copy_texture
                    fig.set_rendering_options = self.parent.paint_manager.set_rendering_options
                    fig.get_processor = self.interaction_manager.get_processor
                    fig.get_visual = self.paint_manager.get_visual
                    fig.process_interaction = self.parent.process_interaction
                
                fig.resizeGL = self.parent.paint_manager.resizeGL
                # here, we are using the high level interface and figure
                # is the Figure object we pass to this function
                method(fig, parameter)

    def process_none(self):
        """Process the None event, occuring when there's no event, or when
        an event has just finished."""
        self.process(None, None)
        
        
    # Methods to override
    # -------------------
    def initialize(self, *args, **kwargs):
        """Initialize the event processor by calling self.register to register
        handlers for different events."""
        pass
        
        

########NEW FILE########
__FILENAME__ = pyplot
import numpy as np
# from collections import OrderedDict as odict
import inspect

from galry import GalryWidget, show_basic_window, get_color, PaintManager,\
    InteractionManager, ordict, get_next_color
import galry.managers as mgs
import galry.processors as ps
import galry.visuals as vs

__all__ = ['figure', 'Figure', 'get_current_figure',
           'plot', 'text', 'rectangles', 'imshow', 'graph', 'mesh', 'barplot', 'surface',
           'sprites',
           'visual',
           'axes', 'xlim', 'ylim',
           'grid', 'animate',
           'event', 'action',
           'framebuffer',
           'show']

def get_marker_texture(marker, size=None):
    """Create a marker texture."""
    # if size is None:
        # size = 1
        
    if marker == '.':
        marker = ','
        if size is None:
            size = 2
    
    if size is None:
        if marker == ',':
            size = 1
        else:
            size = 5
        
    texture = np.zeros((size, size, 4))
    
    if marker == ',':
        texture[:] = 1
        
    elif marker == '+':
        # force odd number
        size -= (np.mod(size, 2) - 1)
        texture[size / 2, :, :] = 1
        texture[:, size / 2, :] = 1
        
    elif marker == 'x':
        # force even number
        size -= (np.mod(size, 2))
        texture[range(size), range(size), :] = 1
        texture[range(size - 1, -1, -1), range(size), :] = 1
        
    elif marker == '-':
        texture[size / 2, :, :] = 1
        
    elif marker == '|':
        texture[:, size / 2, :] = 1
        
    elif marker == 'o':
        # force even number
        size -= (np.mod(size, 2))
        # fill with white
        texture[:, :, :-1] = 1
        x = np.linspace(-1., 1., size)
        X, Y = np.meshgrid(x, x)
        R = X ** 2 + Y ** 2
        R = np.minimum(1, 20 * np.exp(-8*R))
        # disc-shaped alpha channel
        texture[:size,:size,-1] = R
    
    return texture


# Manager creator classes
# -----------------------
class PaintManagerCreator(object):
    @staticmethod
    def create(figure, baseclass=None, update=None):
        if baseclass is None:
            baseclass = mgs.PlotPaintManager
        visuals = figure.visuals
        if not update:
            class MyPaintManager(baseclass):
                def initialize(self):
                    self.figure = figure
                    self.normalization_viewbox = figure.viewbox
                    for name, (args, kwargs) in visuals.iteritems():
                        self.add_visual(*args, **kwargs)
                        
                def resizeGL(self, w, h):
                    super(MyPaintManager, self).resizeGL(w, h)
                    self.figure.size = w, h
                    
        else:
            class MyPaintManager(baseclass):
                def initialize(self):
                    self.normalization_viewbox = figure.viewbox
                    for name, (args, kwargs) in visuals.iteritems():
                        self.add_visual(*args, **kwargs)
        return MyPaintManager

class InteractionManagerCreator(object):
    @staticmethod
    def create(figure, baseclass=None):
        if baseclass is None:
            baseclass = mgs.PlotInteractionManager
        handlers = figure.handlers
        processors = figure.processors
        
        class MyInteractionManager(baseclass):
            # def initialize_default(self,
                # constrain_navigation=None,
                # normalization_viewbox=None):
                # super(MyInteractionManager, self).initialize_default(
                    # constrain_navigation=constrain_navigation,
                    # normalization_viewbox=figure.viewbox)
            
            def initialize(self):
                # use this to pass this Figure instance to the handler function
                # as a first argument (in EventProcessor.process)
                self.figure = figure
                # add all handlers
                for event, method in handlers.iteritems():
                    self.register(event, method)
                # add all event processors
                for name, (args, kwargs) in processors.iteritems():
                    self.add_processor(*args, **kwargs)
                    
        return MyInteractionManager

class BindingCreator(object):
    @staticmethod
    def create(figure, baseclass=None):
        if baseclass is None:
            baseclass = PlotBindings
        bindings = figure.bindings
        class MyBindings(baseclass):
            def initialize(self):
                super(MyBindings, self).initialize()
                for (args, kwargs) in bindings:
                    self.set(*args, **kwargs)
        return MyBindings
        

# Figure class
# ------------
class Figure(object):

    # Initialization methods
    # ----------------------
    def __init__(self, *args, **kwargs):
        self.visuals = ordict()
        self.handlers = ordict()
        self.processors = ordict()
        self.bindings = []
        self.viewbox = (None, None, None, None)
        
        self.constrain_ratio = None
        self.constrain_navigation = None
        self.display_fps = None
        self.activate3D = None
        self.antialiasing = None
        self.activate_grid = True
        self.show_grid = False
        self.activate_help = True
        self.momentum = False
        self.figsize = (GalryWidget.w, GalryWidget.h)
        self.toolbar = True
        self.autosave = None
        self.autodestruct = None
        
        self.pmclass = kwargs.pop('paint_manager', mgs.PlotPaintManager)
        self.imclass = kwargs.pop('interaction_manager', mgs.PlotInteractionManager)
        self.bindingsclass = kwargs.pop('bindings', mgs.PlotBindings)
        
        self.initialize(*args, **kwargs)
        
        if self.momentum:
            self.animation_interval = .01
        else:
            self.animation_interval = None
        
    def initialize(self, **kwargs):
        for name, value in kwargs.iteritems():
            setattr(self, name, value)
    
    
    # Internal visual methods
    # -----------------------
    def add_visual(self, *args, **kwargs):
        name = kwargs.get('name', 'visual%d' % len(self.visuals))
        
        # give the autocolor (colormap index) only if it
        # is requested
        _args, _, _, _ = inspect.getargspec(args[0].initialize)
        if 'autocolor' in _args:
            if kwargs.get('color', None) is None:
                kwargs['autocolor'] = len(self.visuals)
            
        self.visuals[name] = (args, kwargs)
    
    def get_visual_class(self, name):
        return self.visuals[name][0][0]
        
    def update_visual(self, name, **kwargs):
        self.visuals[name][1].update(kwargs)
        
        
    # Internal interaction methods
    # ----------------------------
    def add_event_processor(self, *args, **kwargs):
        name = kwargs.get('name', 'processor%d' % len(self.processors))
        self.processors[name] = (args, kwargs)
        
        
    # Normalization methods
    # ---------------------
    def axes(self, *viewbox):
        """Set the axes with (x0, y0, x1, y1)."""
        if len(viewbox) == 1:
            viewbox = viewbox[0]
        x0, y0, x1, y1 = viewbox
        px0, py0, px1, py1 = self.viewbox
        if x0 is None:
            x0 = px0
        if x1 is None:
            x1 = px1
        if y0 is None:
            y0 = py0
        if y1 is None:
            y1 = py1
        self.viewbox = (x0, y0, x1, y1)
    
    def xlim(self, x0, x1):
        """Set the x limits x0 and x1."""
        self.axes(x0, None, x1, None)
    
    def ylim(self, y0, y1):
        """Set the y limits y0 and y1."""
        self.axes(None, y0, None, y1)
    
        
    # Public visual methods
    # ---------------------
    def plot(self, *args, **kwargs):
        """Plot lines, curves, scatter plots, or any sequence of basic
        OpenGL primitives.
        
        Arguments:
        
          * x, y: 1D vectors of the same size with point coordinates, or
            2D arrays where each row is plotted as an independent plot.
            If only x is provided, then it contains the y coordinates and the
            x coordinates are assumed to be linearly spaced.
          * options: a string with shorcuts for the options: color and marker.
            The color can be any char among: `rgbycmkw`.
            The marker can be any char among: `,.+-|xo`. 
          * color: the color of the line(s), or a list/array of colors for each 
            independent primitive.
          * marker, or m: the type of the marker as a char, or a NxMx3 texture.
          * marker_size, or ms: the size of the marker.
          * thickness: None by default, or the thickness of the line.
          * primitive_type: the OpenGL primitive type of the visual. Can be:
          
              * `LINES`: a segment is rendered for each pair of successive
                points
              * `LINE_STRIP`: a sequence of segments from one point to the
                next.
              * `LINE_LOOP`: like `LINE_STRIP` but closed.
              * `POINTS`: each point is rendered as a pixel.
              * `TRIANGLES`: each successive triplet of points is rendered as
                a triangle.
              * `TRIANGLE_STRIP`: one triangle is rendered from a point to the
                next (i.e. successive triangles share two vertices out of
                three).
              * `TRIANGLE_FAN`: the first vertex is shared by all triangles.
        
        """
        # deal with special string argument containing options
        lenargs = len(args)
        opt = ''
        # we look for the index in args such that args[i] is a string
        for i in xrange(lenargs):
            if isinstance(args[i], basestring):
                opt = args[i]
                break
        if opt:
            # we remove the options from the arguments
            l = list(args)
            l.remove(opt)
            args = tuple(l)
            kwargs['options'] = opt
        
        # process marker type, 'o' or 'or'
        marker = kwargs.pop('marker', kwargs.pop('m', None))
        if marker is None:
            if opt and opt[0] in ',.+-|xo':
                marker = opt[0]
        if marker is not None:
            cls = vs.SpriteVisual
            texsize = kwargs.pop('marker_size', kwargs.pop('ms', None))
            # marker string
            if isinstance(marker, basestring): 
                kwargs['texture'] = get_marker_texture(marker, texsize)
            # or custom texture marker
            else:
                kwargs['texture'] = marker
            kwargs.pop('options', None)
            # process marker color in options
            if 'color' not in kwargs and len(opt) == 2:
                kwargs['color'] = get_color(opt[1])
        else:
            cls = vs.PlotVisual
        
        self.add_visual(cls, *args, **kwargs)
        
    def barplot(self, *args, **kwargs):
        """Render a bar plot (histogram).
        
        Arguments:
        
          * values: a 1D vector of bar plot values, or a 2D array where each
            row is an independent bar plot.
          * offset: a 2D vector where offset[i,:] contains the x, y coordinates
            of bar plot #i.
        
        """
        self.add_visual(vs.BarVisual, *args, **kwargs)
        
    def text(self, *args, **kwargs):
        """Render text.
        
        Arguments:
        
          * text: a string or a list of strings
          * coordinates: a tuple with x, y coordinates of the text, or a list 
            with coordinates for each string.
          * fontsize=24: the font size
          * color: the color of the text
          * letter_spacing: the letter spacing
          * interline=0.: the interline when there are several independent 
            texts
        
        """
        self.add_visual(vs.TextVisual, *args, **kwargs)
        
    def rectangles(self, *args, **kwargs):
        """Render one or multiple rectangles.
        
        Arguments:
        
          * coordinates: a 4-tuple with (x0, y0, x1, y1) coordinates, or a list
            of such coordinates for rendering multiple rectangles.
          * color: color(s) of the rectangle(s).
        
        """
        self.add_visual(vs.RectanglesVisual, *args, **kwargs)
    
    def sprites(self, *args, **kwargs):
        """"""
        self.add_visual(vs.SpriteVisual, *args, **kwargs)
       
    def imshow(self, *args, **kwargs):
        """Draw an image.
        
        Arguments:
        
          * texture: a NxMx3 or NxMx4 array with RGB(A) components.
          * points: a 4-tuple with (x0, y0, x1, y1) coordinates of the texture.
          * filter=False: if True, linear filtering and mimapping is used
            if supported by the OpenGL implementation.
        
        """
        filter = kwargs.pop('filter', None)
        if filter:
            kwargs.update(
                mipmap=True,
                minfilter='LINEAR_MIPMAP_NEAREST',
                magfilter='LINEAR',)
        self.add_visual(vs.TextureVisual, *args, **kwargs)
        
    def graph(self, *args, **kwargs):
        """Draw a graph.
        
        Arguments:
        
          * position: a Nx2 array with the coordinates of all nodes.
          * edges: a Nx2-long vector where each row is an edge with the
            nodes indices (integers).
          * color: the color of all nodes, or an array where each row is a 
            node's color.
          * edges_color: the color of all edges, or an array where each row is
            an edge's color.
          * node_size: the node size for all nodes.
        
        """
        
        self.add_visual(vs.GraphVisual, *args, **kwargs)
        
    def mesh(self, *args, **kwargs):
        """Draw a 3D mesh.
        
        Arguments:
        
          * position: the positions as 3D vertices,
          * normal: the normals as 3D vectors,
          * color: the color of each vertex, as 4D vertices.
          * camera_angle: the view angle of the camera, in radians.
          * camera_ratio: the W/H ratio of the camera.
          * camera_zrange: a pair with the far and near z values for the camera
            projection.
        
        """
        self.pmclass = mgs.MeshPaintManager
        self.imclass = mgs.MeshInteractionManager
        self.antialiasing = True
        self.bindingsclass = mgs.MeshBindings
        self.add_visual(vs.MeshVisual, *args, **kwargs)
    
    def surface(self, Z, *args, **kwargs):
        self.pmclass = mgs.MeshPaintManager
        self.imclass = mgs.MeshInteractionManager
        self.antialiasing = True
        self.bindingsclass = mgs.MeshBindings
        self.add_visual(vs.SurfaceVisual, Z, *args, **kwargs)
        
    
    def visual(self, visualcls, *args, **kwargs):
        """Render a custom visual.
        
        Arguments:
        
          * visual_class: the Visual class.
          * *args, **kwargs: the arguments to `visual_class.initialize`.
        
        """
        self.add_visual(visualcls, *args, **kwargs)
    
    def grid(self, *args, **kwargs):
        """Activate the grid."""
        self.show_grid = True
        
        
    # Public interaction methods
    # --------------------------
    def event(self, event, method):
        """Connect an event to a callback method."""
        # self.add_handler(event, method)
        self.handlers[event] = method
        
    def action(self, action, event, *args, **kwargs):
        """Connect an action to an event or a callback method."""
        # first case: event is a function or a method, and directly bind the
        # action to that function
        if not isinstance(event, basestring):
            callback = event
            # we create a custom event
            event = getattr(callback, '__name__', 'CustomEvent%d' % len(self.bindings))
            # we bind the action to that event
            # we also pass the full User Action Parameters object to the
            # callback
            if 'param_getter' not in kwargs:
                kwargs['param_getter'] = lambda p: p
            self.action(action, event, *args, **kwargs)
            # and we bind that event to the specified callback
            self.event(event, callback)
        else:
            args = (action, event) + args
            # self.add_binding(event, method)
            self.bindings.append((args, kwargs))
        
    def animate(self, method, dt=None):
        """Connect a callback method to the Animate event.
        
        Arguments:
        
          * method: the callback method,
          * dt: the time step in seconds.
        
        """
        if dt is None:
            dt = .02
        self.animation_interval = dt
        self.event('Animate', method)

    
    # Frame buffer methods
    # --------------------
    def framebuffer(self, *args, **kwargs):
        if 'framebuffer' not in kwargs:
            kwargs['framebuffer'] = 'screen'
        if 'name' not in kwargs:
            kwargs['name'] = 'framebuffer'
        self.visual(vs.FrameBufferVisual, *args, **kwargs)

        
    # Rendering methods
    # -----------------
    def show(self, position=(20,20) ):
        """Show the figure."""
        # self.update_normalization()
        pm = PaintManagerCreator.create(self, self.pmclass)
        im = InteractionManagerCreator.create(self, self.imclass)
        bindings = BindingCreator.create(self, self.bindingsclass)
        window = show_basic_window(
            figure=self,
            paint_manager=pm,
            interaction_manager=im,
            bindings=bindings,
            constrain_ratio=self.constrain_ratio,
            constrain_navigation=self.constrain_navigation,
            display_fps=self.display_fps,
            activate3D=self.activate3D,
            antialiasing=self.antialiasing,
            activate_grid=self.activate_grid,
            momentum=self.momentum,
            show_grid=self.show_grid,
            activate_help=self.activate_help,
            animation_interval=self.animation_interval,
            size=self.figsize,
            position=position,
            toolbar=self.toolbar,
            autosave=self.autosave,
            autodestruct=self.autodestruct,
            )
        return window


# Public figure methods
# ---------------------
def figure(*args, **kwargs):
    """Create a new figure.
    
    Arguments:
    
      * constrain_ratio: constrain the W/H ratio when zooming and resizing
        the window.
      * constrain_navigation: prevent zooming outside the scene.
      * display_fps: display frames per second or not.
      * antialiasing: activate antialiasing or not.
      * size: figure size.
      * toolbar: show the toolbar by default or not.
      
    """
    fig = Figure(*args, **kwargs)
    global _FIGURE
    _FIGURE = fig
    return fig

# Default figure in the namespace
_FIGURE = None
def get_current_figure():
    global _FIGURE
    if not _FIGURE:
        _FIGURE = figure()
    return _FIGURE

    
# Visual methods
# --------------
def plot(*args, **kwargs):
    fig = get_current_figure()
    fig.plot(*args, **kwargs)
    
def barplot(*args, **kwargs):
    fig = get_current_figure()
    fig.barplot(*args, **kwargs)
    
def text(*args, **kwargs):
    fig = get_current_figure()
    fig.text(*args, **kwargs)
    
def rectangles(*args, **kwargs):
    fig = get_current_figure()
    fig.rectangles(*args, **kwargs)
    
def sprites(*args, **kwargs):
    fig = get_current_figure()
    fig.sprites(*args, **kwargs)
    
def imshow(*args, **kwargs):
    fig = get_current_figure()
    fig.imshow(*args, **kwargs)

def graph(*args, **kwargs):
    fig = get_current_figure()
    fig.graph(*args, **kwargs)
    
def mesh(*args, **kwargs):
    fig = get_current_figure()
    fig.mesh(*args, **kwargs)
    
def surface(*args, **kwargs):
    fig = get_current_figure()
    fig.surface(*args, **kwargs)
    
def visual(*args, **kwargs):
    fig = get_current_figure()
    fig.visual(*args, **kwargs)
    

# Axes methods
# ------------
def grid(*args, **kwargs):
    fig = get_current_figure()
    fig.grid(*args, **kwargs)
    
def axes(*args, **kwargs):
    fig = get_current_figure()
    fig.axes(*args, **kwargs)
    
def xlim(*args, **kwargs):
    fig = get_current_figure()
    fig.xlim(*args, **kwargs)
    
def ylim(*args, **kwargs):
    fig = get_current_figure()
    fig.ylim(*args, **kwargs)
    
    
# Event methods
# -------------
def event(*args, **kwargs):
    fig = get_current_figure()
    fig.event(*args, **kwargs)
    
def action(*args, **kwargs):
    fig = get_current_figure()
    fig.action(*args, **kwargs)
    
def animate(*args, **kwargs):
    fig = get_current_figure()
    fig.animate(*args, **kwargs)


# Frame buffer
# ------------
def framebuffer(*args, **kwargs):
    fig = get_current_figure()
    fig.framebuffer(*args, **kwargs)
    
    

def show(*args, **kwargs):
    fig = get_current_figure()
    fig.show(*args, **kwargs)



    
########NEW FILE########
__FILENAME__ = scene
import numpy as np
import base64
import json
from galry import CompoundVisual

__all__ = ['SceneCreator', 
           'encode_data', 'decode_data', 'serialize', 'deserialize', ]


# Scene creator
# -------------
class SceneCreator(object):
    """Construct a scene with `add_*` methods."""
    def __init__(self, constrain_ratio=False,):
        """Initialize the scene."""
        
        # options
        self.constrain_ratio = constrain_ratio
        
        # create an empty scene
        self.scene = {'visuals': [], 'renderer_options': {}}
        self.visual_objects = {}
        
        
    # Visual methods
    # --------------
    def get_visuals(self):
        """Return all visuals defined in the scene."""
        return self.scene['visuals']
        
    def get_visual_object(self, name):
        """Get a visual object from its name."""
        return self.visual_objects[name]
        
    def get_visual(self, name):
        """Get a visual dictionary from its name."""
        visuals = [v for v in self.get_visuals() if v.get('name', '') == name]
        if not visuals:
            return None
        return visuals[0]
        
    
    # Visual creation methods
    # -----------------------
    def add_visual(self, visual_class, *args, **kwargs):
        """Add a visual. This method should be called in `self.initialize`.
        
        A visual is an instanciation of a `Visual`. A Visual
        defines a pattern for one, or a homogeneous set of plotting objects.
        Example: a text string, a set of rectangles, a set of triangles,
        a set of curves, a set of points. A set of points and rectangles
        does not define a visual since it is not an homogeneous set of
        objects. The technical reason for this distinction is that OpenGL
        allows for very fast rendering of homogeneous objects by calling
        a single rendering command (even if several objects of the same type
        need to be rendered, e.g. several rectangles). The lower the number
        of rendering calls, the better the performance.
        
        Hence, a visual is defined by a particular Visual, and by
        specification of fields in this visual (positions of the points,
        colors, text string for the example of the TextVisual, etc.). It
        also comes with a number `N` which is the number of vertices contained
        in the visual (N=4 for one rectangle, N=len(text) for a text since 
        every character is rendered independently, etc.)
        
        Several visuals can be created in the PaintManager, but performance
        decreases with the number of visuals, so that all homogeneous 
        objects to be rendered on the screen at the same time should be
        grouped into a single visual (e.g. multiple line plots).
        
        Arguments:
          * visual_class=None: the visual class, deriving from
            `Visual` (or directly from the base class `Visual`
            if you don't want the navigation-related functionality).
          * visible=True: whether this visual should be rendered. Useful
            for showing/hiding a transient element. When hidden, the visual
            does not go through the rendering pipeline at all.
          * **kwargs: keyword arguments for the visual `initialize` method.
          
        Returns:
          * visual: a dictionary containing all the information about
            the visual, and that can be used in `set_data`.
        
        """
        
        if 'name' not in kwargs:
            kwargs['name'] = 'visual%d' % (len(self.get_visuals()))
        
        # handle compound visual, where we add all sub visuals
        # as defined in CompoundVisual.initialize()
        if issubclass(visual_class, CompoundVisual):
            visual = visual_class(self.scene, *args, **kwargs)
            for sub_cls, sub_args, sub_kwargs in visual.visuals:
                self.add_visual(sub_cls, *sub_args, **sub_kwargs)
            return visual
            
        # get the name of the visual from kwargs
        name = kwargs.pop('name')
        if self.get_visual(name):
            raise ValueError("Visual name '%s' already exists." % name)
        
        # pass constrain_ratio to all visuals
        if 'constrain_ratio' not in kwargs:
            kwargs['constrain_ratio'] = self.constrain_ratio
        # create the visual object
        visual = visual_class(self.scene, *args, **kwargs)
        # get the dictionary version
        dic = visual.get_dic()
        dic['name'] = name
        # append the dic to the visuals list of the scene
        self.get_visuals().append(dic)
        # also, record the visual object
        self.visual_objects[name] = visual
        return visual
        
        
    # Output methods
    # --------------
    def get_scene(self):
        """Return the scene dictionary."""
        return self.scene

    def serialize(self, **kwargs):
        """Return the JSON representation of the scene."""
        self.scene.update(**kwargs)
        return serialize(self.scene)
        
    def from_json(self, scene_json):
        """Import the scene from a JSON string."""
        self.scene = deserialize(scene_json)
        

# Scene serialization methods
# ---------------------------
def encode_data(data):
    """Return the Base64 encoding of a Numpy array."""
    return base64.b64encode(data)
        
def decode_data(s, dtype=np.float32):
    """Return a Numpy array from its encoded Base64 string. The dtype
    must be provided (float32 by default)."""
    return np.fromstring(base64.b64decode(s), dtype=dtype)

class ArrayEncoder(json.JSONEncoder):
    """JSON encoder that handles Numpy arrays and serialize them with base64
    encoding."""
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return encode_data(obj)
        return json.JSONEncoder.default(self, obj)
        
def is_str(obj):
    tp = type(obj)
    return tp == str or tp == unicode
        
def serialize(scene):
    """Serialize a scene."""
    
    # HACK: force all attributes to float32
    # for visual in scene.get('visuals', []):
        # if isinstance(visual.get('bounds', None), np.ndarray):
            # visual['bounds'] = encode_data(visual['bounds'])
        # for variable in visual.get('variables', []):
            # if isinstance(variable.get('data', None), np.ndarray):
                # # vartype = variable.get('vartype', 'float')
                # # if vartype == 'int':
                    # # dtype = np.int32
                # # elif vartype == 'float':
                    # # dtype = np.float32
                # variable['data'] = encode_data(np.array(variable['data'], dtype=np.float32))
    
    scene_json = json.dumps(scene, cls=ArrayEncoder, ensure_ascii=True)
    # scene_json = scene_json.replace('\\n', '\\\\n')
    return scene_json

def deserialize(scene_json):
    """Deserialize a scene."""
    scene = json.loads(scene_json)
    for visual in scene.get('visuals', []):
        if is_str(visual.get('bounds', None)):
            visual['bounds'] = decode_data(visual['bounds'], np.int32)
        for variable in visual.get('variables', []):
            if is_str(variable.get('data', None)):
                vartype = variable.get('vartype', 'float')
                if vartype == 'int':
                    dtype = np.int32
                elif vartype == 'float':
                    dtype = np.float32
                variable['data'] = decode_data(variable['data'], dtype)
    return scene

    
########NEW FILE########
__FILENAME__ = empty_test
import unittest
from galry import *
from test import GalryTest

class EmptyTest(GalryTest):
    def test(self):
        self.show()
    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = plot_colormap_test
import unittest
from galry import *
import numpy as np
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        x = np.array([-.5, .5, .5, .5, .5, -.5, -.5, -.5]).reshape((4, 2))
        y = np.array([-.5, -.5, -.5, .5, .5, .5, .5, -.5]).reshape((4, 2))
        color = np.zeros((4, 3))
        color[0,:] = (1, 0, 0)
        color[1,:] = (0, 1, 0)
        color[2,:] = (0, 0, 1)
        color[3,:] = (1, 1, 1)
        index = [3, 3, 3, 3, 3, 3, 3, 3]
        self.add_visual(PlotVisual, x=x, y=y, color=color,
            color_array_index=index,
            primitive_type='LINES')

class PlotColormapTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)

########NEW FILE########
__FILENAME__ = plot_default_test
import unittest
from galry import *
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        self.add_visual(PlotVisual, x=[-.5, .5, .5, -.5, -.5],
                y=[-.5, -.5, .5, .5, -.5], color=(1., 1., 1., 1.))

class PlotDefaultTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = plot_double_test
import unittest
import numpy as np
from galry import *
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        color = (1.,) * 4
        x = [-.5, .5, .5]
        y = [-.5, -.5, .5]
        self.add_visual(PlotVisual, x=x, y=y, color=color)
        x2 = [.5, -.5, -.5]
        y2 = [.5, .5, -.5]
        self.add_visual(PlotVisual, x=x2, y=y2, color=color)

class PlotDoubleTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    
########NEW FILE########
__FILENAME__ = plot_indexed_test
import unittest
from galry import *
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        position = np.zeros((4, 2))
        position[:,0] = [-.5, .5, .5, -.5]
        position[:,1] = [-.5, -.5, .5, .5]
        self.add_visual(PlotVisual, position=position, color=(1., 1., 1., 1.),
            primitive_type='LINES', index=[0, 1, 0, 3, 1, 2, 3, 2])

class PlotIndexedTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = plot_lines_test
import unittest
from galry import *
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        x = [-.5, .5, .5, .5, .5, -.5, -.5, -.5]
        y = [-.5, -.5, -.5, .5, .5, .5, .5, -.5]
        self.add_visual(PlotVisual, x=x, y=y, color=(1., 1., 1., 1.),
            primitive_type='LINES')

class PlotLinesTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = plot_multi_slice_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

import galry.glrenderer
galry.glrenderer.MAX_VBO_SIZE = 1000


class PM(PaintManager):
    def initialize(self):
        n = 20000#16325
        v = np.linspace(-.5, .5, n)
        w = .5 * np.ones(n)
        x = np.vstack((v, -v, w, -w))
        y = np.vstack((-w, w, v, -v))
        
        x = np.vstack((x,) * 4)
        y = np.vstack((y,) * 4)
        
        color = np.ones((x.shape[0], 4))
        
        self.add_visual(PlotVisual, x=x, y=y, color=color,
            primitive_type='LINE_STRIP')

class PlotSliceTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)

########NEW FILE########
__FILENAME__ = plot_multi_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        x = np.empty((4, 2))
        x[0,:] = (.5, -.5)
        x[1,:] = (.5, .5)
        x[2,:] = (.5, -.5)
        x[3,:] = (-.5, -.5)
        
        y = np.empty((4, 2))
        y[0,:] = (-.5, -.5)
        y[1,:] = (.5, -.5)
        y[2,:] = (.5, .5)
        y[3,:] = (-.5, .5)
        
        color = np.ones((5, 4))
        color[-1, :] = 0
        
        self.add_visual(PlotVisual, x=x, y=y, color=color)

class PlotMultiTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = plot_points_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        n = 100000
        x0 = np.linspace(-.5, .5, n)
        x1 = .5 * np.ones(n)
        x = np.hstack((x0, x1, x0, -x1))
        
        y0 = -.5 * np.ones(n)
        y1 = np.linspace(-.5, .5, n)
        y = np.hstack((y0, y1, -y0, y1))
        
        self.add_visual(PlotVisual, x=x, y=y, color=(1., 1., 1., 1.),
            primitive_type='POINTS')

class PlotPointsTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = plot_ref_test
import unittest
from galry import *
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        # we first add a plot with square coordinates but black
        self.add_visual(PlotVisual, x=[-.5, .5, .5, -.5, -.5],
                y=[-.5, -.5, .5, .5, -.5], color=(0.,) * 4)
        # add a new visual where the position variable refers to the position
        # variable of the first visual. The same memory buffer is shared
        # for both visuals on system memory and graphics memory.
        self.add_visual(PlotVisual, position=RefVar('visual0', 'position'), 
            color=(1.,) * 4)
        
class PlotRefTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = plot_ref_update_test
import unittest
import numpy as np
from galry import *
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        position = np.zeros((4, 2))
        position[:,0] = [-.5, .5, .5, -.5]
        position[:,1] = [-.5, -.5, .5, .5]

        # we first add a plot with square coordinates but black
        self.add_visual(PlotVisual, position=np.random.randn(4, 2)*.2, color=(1.,) * 4)
        # add a new visual where the position variable refers to the position
        # variable of the first visual. The same memory buffer is shared
        # for both visuals on system memory and graphics memory.
        self.add_visual(PlotVisual, position=RefVar('visual0', 'position'), 
            color=(1.,) * 4)
        self.set_data(position=position, visual='visual0', primitive_type='LINE_LOOP')
        
class PlotRefUpdateTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = plot_reinit_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        position = np.random.randn(1, 2) * .2
        self.add_visual(PlotVisual, position=position, primitive_type='POINTS',
            color=(1., 1., 1., 1.))
        # initialize the visual again, but takes only the data defined in
        # visual.initialize()
        self.reinitialize_visual(x=[-.5, .5, .5, -.5, -.5],
                                 y=[-.5, -.5, .5, .5, -.5],
                                 primitive_type='LINE_STRIP',
                                 color=(1.,) * 4)

class PlotReinitTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)
    
########NEW FILE########
__FILENAME__ = plot_slice_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        n = 100000
        v = .5 * np.ones(n)
        x = np.hstack((-v, v, v, -v, -v))
        y = np.hstack((-v, -v, v, v, -v))
        
        self.add_visual(PlotVisual, x=x, y=y, color=(1., 1., 1., 1.),
            primitive_type='LINE_STRIP')

class PlotSliceTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = plot_update_indexed_test
import unittest
from galry import *
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        position = np.zeros((4, 2))
        position[:,0] = [-.5, .5, .5, -.5]
        position[:,1] = [-.5, -.5, .5, .5]
        
        # update the index to a bigger array
        index0 = [0, 2, 1]
        index1 = [0, 1, 2, 3, 0]
        
        self.add_visual(PlotVisual, position=position, color=(1., 1., 1., 1.),
            primitive_type='LINE_STRIP', index=index0)
        self.set_data(index=index1)
            
class PlotUpdateIndexedTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)

########NEW FILE########
__FILENAME__ = rectangles_default_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        d = 4e-3
        coordinates = np.array([[-.5, -.5, .5, .5],
                                [-.5 + d, -.5 + d, .5 - d, .5 - d]])
        color = np.array([[1., 1., 1., 1.],
                          [0., 0., 0., 1.]])
        self.add_visual(RectanglesVisual, coordinates=coordinates,
            color=color)

class RectanglesDefaultTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    # unittest.main()    
    show_basic_window(paint_manager=PM)

########NEW FILE########
__FILENAME__ = sprite_default_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        n = 1000
        x0 = np.linspace(-.5, .5, n)
        x1 = .5 * np.ones(n)
        x = np.hstack((x0, x1, x0, -x1))
        
        y0 = -.5 * np.ones(n)
        y1 = np.linspace(-.5, .5, n)
        y = np.hstack((y0, y1, -y0, y1))
        
        position = np.hstack((x.reshape((-1, 1)), y.reshape((-1, 1))))
        
        tex = np.zeros((11, 11, 4))
        tex[5, 5, :] = 1
        
        self.add_visual(SpriteVisual, position=position, 
            color=(1., 1., 1., 1.), texture=tex)

class SpriteDefaultTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)

########NEW FILE########
__FILENAME__ = test
"""Galry unit tests.

Every test shows a GalryWidget with a white square (non filled) and a black
background. Every test uses a different technique to show the same picture
on the screen. Then, the output image is automatically saved as a PNG file and
it is then compared to the ground truth.

"""
import unittest
import os
import re
from galry import *
from matplotlib.pyplot import imread

def get_image_path(filename=''):
    path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(path, 'autosave/%s' % filename)

REFIMG = imread(get_image_path('_REF.png'))

# maximum accepted difference between the sums of the test and 
# reference images
TOLERANCE = 10

def erase_images():
    log_info("Erasing all non reference images.")
    # erase all non ref png at the beginning
    l = filter(lambda f: not(f.endswith('REF.png')),# and f != '_REF.png', 
        os.listdir(get_image_path()))
    [os.remove(get_image_path(f)) for f in l]

def compare_subimages(img1, img2):
    """Compare the sum of the values in the two images."""
    return np.abs(img1.sum() - img2.sum()) <= TOLERANCE
    
def compare_images(img1, img2):
    """Compare the sum of the values in the two images and in two
    quarter subimages in opposite corners."""
    n, m, k = img1.shape
    boo = compare_subimages(img1, img2)
    boo = boo and compare_subimages(img1[:n/2, :m/2, ...], img2[:n/2, :m/2, ...])
    boo = boo and compare_subimages(img1[n/2:, m/2:, ...], img2[n/2:, m/2:, ...])
    return boo
          
class GalryTest(unittest.TestCase):
    """Base class for the tests. Child classes should call `self.show` with
    the same keyword arguments as those of `show_basic_window`.
    The window will be open for a short time and the image will be recorded
    for automatic comparison with the ground truth."""
        
    # in milliseconds
    autodestruct = 100
    
    def log_header(self, s):
        s += '\n' + ('-' * (len(s) + 10))
        log_info(s)
        
    def setUp(self):
        self.log_header("Running test %s..." % self.classname())
        
    def tearDown(self):
        self.log_header("Test %s finished!" % self.classname())
        
    def classname(self):
        """Return the class name."""
        return self.__class__.__name__
        
    def filename(self):
        """Return the filename of the output image, depending on this class
        name."""
        return get_image_path(self.classname() + '.png')
        
    def reference_image(self):
        filename = get_image_path(self.classname() + '.REF.png')
        if os.path.exists(filename):
            return imread(filename)
        else:
            return REFIMG
        
    def _show(self, **kwargs):
        """Show the window during a short period of time, and save the output
        image."""
        return show_basic_window(autosave=self.filename(),
                autodestruct=self.autodestruct, **kwargs)

    def show(self, **kwargs):
        """Create a window with the given parameters."""
        window = self._show(**kwargs)
        # make sure the output image is the same as the reference image
        img = imread(self.filename())
        boo = compare_images(img, self.reference_image())
        self.assertTrue(boo)
        return window

class MyTestSuite(unittest.TestSuite):
    def run(self, *args, **kwargs):
        erase_images()
        super(MyTestSuite, self).run(*args, **kwargs)

def all_tests(pattern=None, folder=None):
    if folder is None:
        folder = os.path.dirname(os.path.realpath(__file__))
    if pattern is None:
        pattern = '*_test.py'
    suites = unittest.TestLoader().discover(folder, pattern=pattern)
    allsuites = MyTestSuite(suites)
    return allsuites

def test(pattern=None, folder=None):
    # unittest.main(defaultTest='all_tests')
    unittest.TextTestRunner(verbosity=2).run(all_tests(folder=folder,
        pattern=pattern))

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = texture1D_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        texture = np.ones((1, 10, 3))
        self.add_visual(TextureVisual, texture=texture,
            points=(-.5,-.5-1./600,.5,-.5+1./600))
        self.add_visual(TextureVisual, texture=texture,
            points=(-.5,.5-1./600,.5,.5+1./600))
        self.add_visual(TextureVisual, texture=texture,
            points=(-.5-1./600,-.5,-.5+1./600, .5))
        self.add_visual(TextureVisual, texture=texture,
            points=(.5-1./600,-.5,.5+1./600, .5))

class TextureDefaultTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()    
    # show_basic_window(paint_manager=PM)
########NEW FILE########
__FILENAME__ = texture_default_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        texture = np.zeros((600, 600, 4))
        texture[150, 150:-150, :] = 1
        texture[-150, 150:-150, :] = 1
        texture[150:-150, 150, :] = 1
        texture[150:-150, -150, :] = 1
        self.add_visual(TextureVisual, texture=texture)

class TextureDefaultTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()    

########NEW FILE########
__FILENAME__ = texture_reinit_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        self.add_visual(TextureVisual, texture=np.zeros((2, 2, 3)))
        self.set_data(texture=np.zeros((2, 2, 3)))
        # initialize the visual again, but takes only the data defined in
        # visual.initialize()
        self.update_test()

    def update_test(self):
        tex = np.zeros((600, 600, 3))
        a = 150
        tex[a:-a,a:-a,:] = 1
        tex[a+1:-a-1,a+1:-a-1,:] = 0
        self.reinitialize_visual(texture=tex)
        
class PlotReinitTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # w = show_basic_window(paint_manager=PM)
    
########NEW FILE########
__FILENAME__ = text_default_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        self.add_visual(TextVisual, text='Hello World!')

class TextDefaultTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)

########NEW FILE########
__FILENAME__ = text_multi_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        text = ["Hello", "world! :)"]
        self.add_visual(TextVisual, text=text,
            coordinates=[(0., 0.), (0., .5)])


class TextMultiTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)

########NEW FILE########
__FILENAME__ = threedimensions_default_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        position = np.array([[-.5, -.5, 0],
                             [.5, -.5, 0],
                             [-.5, .5, 0],
                             [.5, .5, 0]])
                             
        normal = np.zeros((4, 3))
        normal[:, 2] = -1
        color = np.ones((10, 4))
        
        self.add_visual(MeshVisual, position=position,
            normal=normal, color=color, primitive_type='TRIANGLE_STRIP')

class ThreeDimensionsDefaultTest(GalryTest):
    def test(self):
        self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)
########NEW FILE########
__FILENAME__ = update_default_test
import unittest
from galry import *
from test import GalryTest
import numpy as np

class PM(PaintManager):
    def initialize(self):
        # random data
        position = np.random.randn(10, 2) * .2
        self.add_visual(PlotVisual, position=position, color=(1., 1., 1., 1.))
        # then we update to have a square
        x = np.array([-.5, .5, .5, -.5, -.5])
        y = np.array([-.5, -.5, .5, .5, -.5])
        position = np.hstack((x.reshape((-1, 1)), y.reshape((-1, 1))))
        self.set_data(position=position)
        
class UpdateDefaultTest(GalryTest):
    def test(self):
        window = self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)
########NEW FILE########
__FILENAME__ = update_texture_rectangle_test
import unittest
import numpy as np
from pylab import imread
from galry import *
from test import GalryTest, get_image_path

class PM(PaintManager):
    def initialize(self):
        texture0 = np.zeros((2, 10, 4))
        texture1 = imread(get_image_path('_REF.png'))
        texture1 = texture1[:,75:-75,:]
        
        self.add_visual(TextureVisual, texture=texture0,
            points=(-.75, -1., .75, 1.))
        self.set_data(texture=texture1)
        
class UpdateTextureRectangleTest(GalryTest):
    def test(self):
        window = self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)
    

########NEW FILE########
__FILENAME__ = update_texture_test
import unittest
import numpy as np
from pylab import imread
from galry import *
from test import GalryTest, get_image_path

class PM(PaintManager):
    def initialize(self):
        texture0 = np.zeros((100, 100, 4))
        texture1 = imread(get_image_path('_REF.png'))
        
        self.add_visual(TextureVisual, texture=texture0)
        self.set_data(texture=texture1)
        
class UpdateTextureTest(GalryTest):
    def test(self):
        window = self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)
    

########NEW FILE########
__FILENAME__ = update_text_test
import unittest
from galry import *
from test import GalryTest

class PM(PaintManager):
    def initialize(self):
        # test buffer updating with different sizes
        self.add_visual(TextVisual, text="short")
        self.set_data(coordinates=(0., .5), text="long text!")
        
class UpdateTextTest(GalryTest):
    def test(self):
        window = self.show(paint_manager=PM)

if __name__ == '__main__':
    unittest.main()
    # show_basic_window(paint_manager=PM)

########NEW FILE########
__FILENAME__ = tools
import sys
import inspect
import os
import numpy as np
import time
import timeit
import collections
import subprocess
from qtools.qtpy import QtCore, QtGui
from qtools.utils import get_application, show_window
from functools import wraps
from galry import log_debug, log_info, log_warn
from collections import OrderedDict as ordict

# try importing numexpr
try:
    import numexpr
except:
    numexpr = None
    
__all__ = [
    'get_application',
    'get_intermediate_classes',
    'show_window',
    'run_all_scripts',
    'enforce_dtype',
    'FpsCounter',
    'ordict',
]
    

def hsv_to_rgb(hsv):
    """
    convert hsv values in a numpy array to rgb values
    both input and output arrays have shape (M,N,3)
    """
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    r = np.empty_like(h)
    g = np.empty_like(h)
    b = np.empty_like(h)

    i = (h * 6.0).astype(np.int)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    idx = i % 6 == 0
    r[idx] = v[idx]
    g[idx] = t[idx]
    b[idx] = p[idx]

    idx = i == 1
    r[idx] = q[idx]
    g[idx] = v[idx]
    b[idx] = p[idx]

    idx = i == 2
    r[idx] = p[idx]
    g[idx] = v[idx]
    b[idx] = t[idx]

    idx = i == 3
    r[idx] = p[idx]
    g[idx] = q[idx]
    b[idx] = v[idx]

    idx = i == 4
    r[idx] = t[idx]
    g[idx] = p[idx]
    b[idx] = v[idx]

    idx = i == 5
    r[idx] = v[idx]
    g[idx] = p[idx]
    b[idx] = q[idx]

    idx = s == 0
    r[idx] = v[idx]
    g[idx] = v[idx]
    b[idx] = v[idx]

    rgb = np.empty_like(hsv)
    rgb[:, :, 0] = r
    rgb[:, :, 1] = g
    rgb[:, :, 2] = b
    return rgb
    
def get_intermediate_classes(cls, baseclass):
    """Return all intermediate classes in the OO hierarchy between a base 
    class and a child class."""
    classes = inspect.getmro(cls)
    classes = [c for c in classes if issubclass(c, baseclass)]
    return classes
     
def run_all_scripts(dir=".", autodestruct=True, condition=None, ignore=[]):
    """Run all scripts successively."""
    if condition is None:
        condition = lambda file: file.endswith(".py") and not file.startswith("_")
    os.chdir(dir)
    files = sorted([file for file in os.listdir(dir) if condition(file)])
    for file in files:
        if file in ignore:
            continue
        print "Running %s..." % file
        args = ["python", file]
        if autodestruct:
            args += ["autodestruct"]
        subprocess.call(args)
        print "Done!"
        print

def enforce_dtype(arr, dtype, msg=""):
    """Force the dtype of a Numpy array."""
    if isinstance(arr, np.ndarray):
        if arr.dtype is not np.dtype(dtype):
            log_debug("enforcing dtype for array %s %s" % (str(arr.dtype), msg))
            return np.array(arr, dtype)
    return arr
    
def memoize(func):
    """Decorator for memoizing a function."""
    cache = {}
    @wraps(func)
    def wrap(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrap
    
def nid(x):
    """Return the address of an array data, used to check whether two arrays
    refer to the same data in memory."""
    return x.__array_interface__['data'][0]
    
class FpsCounter(object):
    """Count FPS."""
    # memory for the FPS counter
    maxlen = 10
    
    def __init__(self, maxlen=None):
        if maxlen is None:
            maxlen = self.maxlen
        self.times = collections.deque(maxlen=maxlen)
        self.fps = 0.
        self.delta = 0.
        
    def tick(self):
        """Record the current time stamp.
        
        To be called by paintGL().
        
        """
        self.times.append(timeit.default_timer())
        
    def get_fps(self):
        """Return the current FPS."""
        if len(self.times) >= 2:
            dif = np.diff(self.times)
            fps = 1. / dif.min()
            # if the FPS crosses 500, do not update it
            if fps <= 500:
                self.fps = fps
            return self.fps
        else:
            return 0.
            

########NEW FILE########
__FILENAME__ = useractions
from qtools.qtpy.QtCore import Qt 

__all__ = ['UserActionGenerator', 'LEAP']


def get_maximum_norm(p1, p2):
    """Return the inf norm between two points."""
    return max(abs(p1[0]-p2[0]), abs(p1[1]-p2[1]))
    
# try importing leap motion SDK    
try:
    import Leap
    LEAP = {}
    LEAP['frame'] = None
    class LeapListener(Leap.Listener):
        def on_frame(self, controller):
            try:
                LEAP['frame'] = controller.frame()
            except:
                pass
except:
    # leap SDK not available
    LEAP = {}
    
class UserActionGenerator(object):
    """Raise user action events.
    
    Define what is the current user action, from the QT events related to mouse 
    and keyboard.
    
    """
    def get_pos(self, pos):
        """Return the coordinate of a position object."""
        return (pos.x(), pos.y())
        
    def __init__(self):
        self.reset()
        
    def reset(self):
        """Reinitialize the actions."""
        self.action = None
        self.key = None
        self.key_modifier = None
        self.mouse_button = 0
        self.mouse_position = (0, 0)
        self.mouse_position_diff = (0, 0)
        self.mouse_press_position = (0, 0)
        
        self.pinch_position = (0, 0)
        self.pinch_rotation = 0.
        self.pinch_scale = 1.
        self.pinch_scale_diff = 0.
        self.pinch_start_position = (0, 0)
        
        self.wheel = 0
        self.init_leap()
        
    def init_leap(self):
        if LEAP:
            self.leap_listener = LeapListener()
            self.leap_controller = Leap.Controller()
            self.leap_controller.add_listener(self.leap_listener)
        
    def get_action_parameters(self):
        """Return an action parameter object."""
        mp = self.mouse_position
        mpd = self.mouse_position_diff
        mpp = self.mouse_press_position
        if not mp:
            mp = (0, 0)
        if not mpd:
            mpd = (0, 0)
        if not mpp:
            mpp = (0, 0)
        parameters = dict(mouse_position=mp,
                            mouse_position_diff=mpd,
                            mouse_press_position=mpp,
                            
                            pinch_start_position=self.pinch_start_position,
                            pinch_position=self.pinch_position,
                            pinch_rotation=self.pinch_rotation,
                            pinch_scale=self.pinch_scale,
                            pinch_scale_diff=self.pinch_scale_diff,
                            
                            wheel=self.wheel,
                            key_modifier=self.key_modifier,
                            key=self.key)
        return parameters
                    
    def clean_action(self):
        """Reset the current action."""
        self.action = None

    def pinchEvent(self, e):
        if e.state() == Qt.GestureStarted:
            self.action = 'Pinch'
            self.pinch_start_position = (0, 0)
        elif e.state() == Qt.GestureUpdated:
            self.action = 'Pinch'
            self.pinch_position = self.get_pos(e.centerPoint())
            # Save the pinch start position at the first GestureUpdated event
            if self.pinch_start_position == (0, 0):
                self.pinch_start_position = self.pinch_position
            self.pinch_rotation_diff = e.rotationAngle()
            self.pinch_rotation = e.totalRotationAngle()
            self.pinch_scale_diff = e.scaleFactor() - 1
            self.pinch_scale = e.totalScaleFactor()
        elif e.state() == Qt.GestureFinished:
            self.action = None
            self.pinch_position = (0, 0)
            self.pinch_rotation = 0.
            self.pinch_scale = 1.
            self.pinch_scale_diff = 0.
            self.pinch_start_position = (0, 0)

    def mousePressEvent(self, e):
        self.mouse_button = e.button()
        self.mouse_press_position = self.mouse_position = self.get_pos(e.pos())
        
    def mouseDoubleClickEvent(self, e):
        self.action = 'DoubleClick'
        
    def mouseReleaseEvent(self, e):
        if get_maximum_norm(self.mouse_position,
                    self.mouse_press_position) < 10:
            if self.mouse_button == Qt.LeftButton:
                self.action = 'LeftClick'
            elif self.mouse_button == Qt.MiddleButton:
                self.action = 'MiddleClick'
            elif self.mouse_button == Qt.RightButton:
                self.action = 'RightClick'
        # otherwise, terminate the current action
        else:
            self.action = None
        self.mouse_button = 0
        
    def mouseMoveEvent(self, e):
        pos = self.get_pos(e.pos())
        self.mouse_position_diff = (pos[0] - self.mouse_position[0],
                                    pos[1] - self.mouse_position[1])
        self.mouse_position = pos
        if self.mouse_button == Qt.LeftButton:
            self.action = 'LeftClickMove'
        elif self.mouse_button == Qt.MiddleButton:
            self.action = 'MiddleClickMove'
        elif self.mouse_button == Qt.RightButton:
            self.action = 'RightClickMove'
        else:
            self.action = 'Move'
            
    def keyPressEvent(self, e):
        key = e.key()
        # set key_modifier only if it is Ctrl, Shift, Alt or AltGr    
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_AltGr):
            self.key_modifier = key
        else:
            self.action = 'KeyPress'
            self.key = key
            
    def keyReleaseEvent(self, e):
        if e.key() in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_AltGr):
            self.key_modifier = None
        else:
            self.key = None
            
    def wheelEvent(self, e):
        self.wheel = e.delta()
        self.action = 'Wheel'
    
    def focusOutEvent(self, e):
        # reset all actions when the focus goes out
        self.reset()
        
    def close(self):
        if LEAP:
            self.leap_controller.remove_listener(self.leap_listener)
        
        
########NEW FILE########
__FILENAME__ = bar_visual
from plot_visual import PlotVisual
import numpy as np

__all__ = ['BarVisual']

def get_histogram_points(hist):
    """Tesselates histograms.
    
    Arguments:
      * hist: a N x Nsamples array, where each line contains an histogram.
      
    Returns:
      * X, Y: two N x (5 * Nsamples + 1) arrays with the coordinates of the
        histograms, to be rendered as a TriangleStrip.
      
    """
    n, nsamples = hist.shape
    dx = 1. / nsamples
    
    x0 = dx * np.arange(nsamples)
    
    x = np.zeros((n, 5 * nsamples + 1))
    y = np.zeros((n, 5 * nsamples + 1))
    
    x[:,0:-1:5] = x0
    x[:,1::5] = x0
    x[:,2::5] = x0 + dx
    x[:,3::5] = x0
    x[:,4::5] = x0 + dx
    x[:,-1] = 1
    
    y[:,1::5] = hist
    y[:,2::5] = hist
    
    return x, y


class BarVisual(PlotVisual):
    def initialize(self, values=None, offset=None, **kwargs):
    
        if values.ndim == 1:
            values = values.reshape((1, -1))
            
        # compute histogram points
        x, y = get_histogram_points(values)
        
        if offset is not None:
            x += offset[:,0].reshape((-1, 1))
            y += offset[:,1].reshape((-1, 1))
        
        # add the bar plot
        super(BarVisual, self).initialize(x=x, y=y, **kwargs)

        self.primitive_type='TRIANGLE_STRIP'
########NEW FILE########
__FILENAME__ = tools
import sys
import os
import re
import numpy as np
from galry import log_info, log_debug
import re

"""Font atlas tools for loading files generated by AngelCode Bitmap Font
Generator 1.13.

The link is: http://www.angelcode.com/products/bmfont/


"""

__all__ = ["load_png", "load_fnt", "get_text_map", "load_font"]

def find_best_size(font="segoe", size=32):
    """Find the closest font size in the existing font files."""
    filename = font + str(size)
    path = os.path.dirname(os.path.realpath(__file__))
    fnt = os.path.join(path, "%s.fnt" % filename)
    if os.path.exists(fnt):
        return size
    else:
        # we go through all .fnt files
        files = [file for file in os.listdir(path) if file.startswith(font) \
            and file.endswith('.fnt')]
        files.sort()
        # we take the largest existing size that is smaller to the requested
        # size
        newsize = 0
        for file in files:
            m = re.match(font + "([0-9]+)", file)
            if m:
                if int(m.group(1)) > size:
                    break
                newsize = int(m.group(1))
        log_debug("font %s %d does not exist, loading size %d instead" % \
            (font, size, newsize))
        return newsize

def get_font_filenames(font="segoe", size=32):
    """Return the texture and FNT file names."""
    size = find_best_size(font, size)
    filename = font + str(size)
    path = os.path.dirname(os.path.realpath(__file__))
    fnt = os.path.join(path, "%s.fnt" % filename)
    png = os.path.join(path, "%s_0.png" % filename)
    return png, fnt

def load_png(filename):
    """Load a PNG texture."""
    import matplotlib.image as mpimg
    return mpimg.imread(filename)
    
def load_fnt(filename):
    """Load a bitmap font file.
    
    Returns:
      * M: an array where each line contains:
            charid, x, y, w, h
        x and y are the top-left coordinates
        w and h are the width and height of the character
    
    """
    pattern = "char id=([0-9]+)[ ]+x=([0-9]+)[ ]+y=([0-9]+)[ ]+width=([0-9]+)[ ]+height=([0-9]+)"

    f = open(filename, "r")

    # look for coordinates and sizes of all characters, along with the 
    # character ASCII indices
    values = []
    for line in f:
        if line.startswith("char "):
            m = re.search(pattern, line)
            if m:
                values.append(m.group(*xrange(1,6)))
    f.close()
    M0 = np.array(values, dtype=np.int32)
    M = np.zeros((M0[:,0].max() + 1, M0.shape[1]), dtype=np.int32)
    M[M0[:,0],:] = M0
    return M

def load_font(font=None, size=None):
    """Load a font and return the texture and map getter function.
    
    Arguments:
      * font: the font name
      * size: the size (if the size does not exist in the font files, a close
        size will be used)
        
    Returns:
      * tex: the texture as a NxMx4 image
      * get_map: a function that takes a string and returns the text map, i.e.
        a matrix where line i contains the position and size of character i in
        that string.
        
    """
    png, fnt = get_font_filenames(font, size)
    matrix = load_fnt(fnt)
    tex = load_png(png)
    texsize = tex.shape[:2]
    get_map = lambda text: get_text_map(text, matrix=matrix)
    # normalize the matrix so that coordinates are in [0,1]
    size = np.array(np.tile(texsize, (1, 2)), dtype=np.float32)
    matrix = np.array(matrix, dtype=np.float32)
    matrix[:,1:] /= size
    return tex, matrix, get_map
    
def get_text_map(text, matrix):#, texsize=None):#, font=None, size=None):
    """Return the text map of a string.
    
    Arguments:
      * text: the text string
      * matrix: the font matrix
      * texsize: the texture size
    
    Returns:
      * matrix: a matrix where line i contains the position and size of
        character i in that string.
    
    """
    chars = map(ord, (text))
    return matrix[chars,1:]
    

########NEW FILE########
__FILENAME__ = framebuffer_visual
from visual import Visual
import numpy as np

class FrameBufferVisual(Visual):
    def initialize(self, shape=None, ntextures=1, coeffs=None, display=True):
        if shape is None:
            shape = (600, 600)
        
        for i in xrange(ntextures):
            self.add_texture('fbotex%d' % i, ncomponents=3, ndim=2, shape=shape,
                data=np.zeros((shape[0], shape[1], 3)))
        # self.add_texture('fbotex2', ncomponents=3, ndim=2, shape=shape,
            # data=np.zeros((shape[0], shape[1], 3)))
        # self.add_framebuffer('fbo', texture=['fbotex', 'fbotex2'])
        self.add_framebuffer('fbo', texture=['fbotex%d' % i for i in xrange(ntextures)])
        
        if not display:
            self.add_attribute('position', ndim=2)#, data=np.zeros((1, 2)))
            self.size = 0
            return
        
        points = (-1, -1, 1, 1)
        x0, y0, x1, y1 = points
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        
        position = np.zeros((4,2))
        position[0,:] = (x0, y0)
        position[1,:] = (x1, y0)
        position[2,:] = (x0, y1)
        position[3,:] = (x1, y1)
        
        tex_coords = np.zeros((4,2))
        tex_coords[0,:] = (0, 0)
        tex_coords[1,:] = (1, 0)
        tex_coords[2,:] = (0, 1)
        tex_coords[3,:] = (1, 1)
    
        self.size = 4
        self.primitive_type = 'TRIANGLE_STRIP'
        
        # texture coordinates
        self.add_attribute("tex_coords", vartype="float", ndim=2,
            data=tex_coords)
        self.add_varying("vtex_coords", vartype="float", ndim=2)
        
        self.add_attribute("position", vartype="float", ndim=2, data=position)
        self.add_vertex_main("""vtex_coords = tex_coords;""")
        
        if coeffs is None:
            self.add_fragment_main("""
            out_color = texture2D(fbotex0, vtex_coords);
            """)
        else:
            FS = ""
            for i in xrange(ntextures):
                FS += """
                vec4 out%d = texture2D(fbotex%d, vtex_coords);
                """ % (i, i)
            FS += "out_color = " + " + ".join(["%.5f * out%d" % (coeffs[i], i) for i in xrange(ntextures)]) + ";"
            self.add_fragment_main(FS)
            

########NEW FILE########
__FILENAME__ = graph_visual
from visual import CompoundVisual, RefVar
from sprite_visual import SpriteVisual
from plot_visual import PlotVisual
from galry import get_color
import numpy as np

__all__ = ['GraphVisual']

def get_tex(n):
    """Create a texture for the nodes. It may be simpler to just use an image!
    
    It returns a n*n*4 Numpy array with values in [0, 1]. The transparency
    channel should contain the shape of the node, where the other channels
    should encode the color.
    
    """
    tex = np.ones((n, n, 4))
    tex[:,:,0] = 1
    x = np.linspace(-1., 1., n)
    X, Y = np.meshgrid(x, x)
    R = X ** 2 + Y ** 2
    R = np.minimum(1, 3 * np.exp(-3*R))
    tex[:,:,-1] = R
    return tex

class GraphVisual(CompoundVisual):
    def initialize(self, position=None, edges=None, color=None,
        edges_color=None, node_size=None, autocolor=None, **kwargs):
        
        if autocolor is not None:
            color = get_color(autocolor)
        
        if node_size is None:
            node_size = 8.
        if color is None:
            color = (1., 1., 1., .25)

        # relative indexing
        edges = np.array(edges, dtype=np.int32).reshape((-1, 2))
        # uedges = np.unique(edges)
        # edges[:,0] = np.digitize(edges[:,0], uedges) - 1
        # edges[:,1] = np.digitize(edges[:,1], uedges) - 1
        
        # edges
        self.add_visual(PlotVisual, position=position,
            primitive_type='LINES', color=edges_color,
            index=edges.ravel(), name='edges')
        
        if isinstance(node_size, np.ndarray):
            texsize = int(node_size.max())
        else:
            texsize = node_size
        
        # nodes
        self.add_visual(SpriteVisual,
            position=RefVar(self.name + '_edges', 'position'),
            point_size=node_size, zoomable=True,
            color=color, texture=get_tex(texsize * 4), name='nodes')


########NEW FILE########
__FILENAME__ = grid_visual
from visual import Visual, CompoundVisual
from text_visual import TextVisual
from plot_visual import PlotVisual
import numpy as np

# Axes
# ----
class AxesVisual(Visual):
    """Axes visual."""
    def initialize_navigation(self):
        self.add_uniform("scale", vartype="float", ndim=2, data=(1., 1.))
        self.add_uniform("translation", vartype="float", ndim=2, data=(0., 0.))
                             
        self.add_vertex_main("""
            vec2 position_tr = position;
            if (axis == 0)
                position_tr.y = scale.y * (position.y + translation.y);
            else if (axis == 1)
                position_tr.x = scale.x * (position.x + translation.x);
            gl_Position = vec4(position_tr, 0., 1.);
            """, position='last', name='navigation')
            
    def initialize(self):
        position = np.array([[-1, 0],
                             [1, 0.],
                             [0, -1],
                             [0., 1]])
                             
        self.size = position.shape[0]
        self.primitive_type = 'LINES'
        self.default_color = (1., 1., 1., .5)
        
        axis = np.zeros(self.size, dtype=np.int32)
        axis[2:] = 1
        
        self.add_attribute("position", ndim=2, data=position)
        self.add_attribute("axis", ndim=1, vartype='int', data=axis)

            
class TicksTextVisual(TextVisual):
    def text_compound(self, text):
        d = super(TicksTextVisual, self).text_compound(text)
        d["text_width"] = 0.#-.2
        return d
    
    def initialize_navigation(self):
        self.add_uniform("scale", vartype="float", ndim=2, data=(1., 1.))
        self.add_uniform("translation", vartype="float", ndim=2, data=(0., 0.))
            
        self.add_vertex_main("""
        
            gl_Position = vec4(position, 0., 1.);
            
            if (axis < .5) {
                gl_Position.x = scale.x * (position.x + translation.x);
            }
            else {
                gl_Position.y = scale.y * (position.y + translation.y);
            }
            
            """,
            position='last', name='navigation')

    def initialize(self, *args, **kwargs):
        super(TicksTextVisual, self).initialize(*args, **kwargs)
        axis = np.zeros(self.size)
        self.add_attribute("axis", ndim=1, vartype="int", data=axis)

        
class TicksLineVisual(PlotVisual):
    def initialize_navigation(self):
        self.add_uniform("scale", vartype="float", ndim=2, data=(1., 1.))
        self.add_uniform("translation", vartype="float", ndim=2, data=(0., 0.))
            
        self.add_vertex_main("""
        
            gl_Position = vec4(position, 0., 1.);
            
            // highlight x.y = 0 axes
            /*if ((abs(gl_Position.x) < .0000000001) || 
                (abs(gl_Position.y) < .0000000001))
                vcolor = vec4(1, 1, 1, .75);
            else*/
            vcolor = vec4(1, 1, 1, .25);
                
            if (axis < .5) {
                gl_Position.x = scale.x * (position.x + translation.x);
            }
            else {
                gl_Position.y = scale.y * (position.y + translation.y);
            }
            
            """,
            position='last', name='navigation')

    def initialize(self, *args, **kwargs):
        # kwargs.update(primitive_type='LINES')
        super(TicksLineVisual, self).initialize(*args, **kwargs)
        self.primitive_type = 'LINES'
        
        axis = np.zeros(self.size)
        self.add_attribute("axis", ndim=1, vartype="int", data=axis)
        
        self.add_varying('vcolor', ndim=4)
        self.add_fragment_main("""
            out_color = vcolor;
        """)
        
        
class GridVisual(CompoundVisual):
    def initialize(self, background_transparent=True, letter_spacing=250.,
        *args, **kwargs):
        # add lines visual
        self.add_visual(TicksLineVisual, name='lines',
            position=np.zeros((1,2)),
            **kwargs)
            
        # add the text visual
        self.add_visual(TicksTextVisual, text='',
            fontsize=14, color=(1., 1., 1., .75), name='text',
            letter_spacing=letter_spacing,
            background_transparent=background_transparent,
            **kwargs)
        
        

########NEW FILE########
__FILENAME__ = mesh_visual
import numpy as np
from visual import Visual
from galry import get_color

__all__ = ['normalize',
           'projection_matrix', 'rotation_matrix', 'scale_matrix',
           'translation_matrix', 'camera_matrix',
           'MeshVisual']

def normalize(x):
    """Normalize a vector or a set of vectors.
    
    Arguments:
      * x: a 1D array (vector) or a 2D array, where each row is a vector.
      
    Returns:
      * y: normalized copies of the original vector(s).
      
    """
    if x.ndim == 1:
        return x / np.sqrt(np.sum(x ** 2))
    elif x.ndim == 2:
        return x / np.sqrt(np.sum(x ** 2, axis=1)).reshape((-1, 1))

def projection_matrix(angle, ratio, znear, zfar):
    """Return a 4D projection matrix.
    
    Arguments:
      * angle: angle of the field of view, in radians.
      * ratio: W/H ratio of the field of view.
      * znear, zfar: near and far projection planes.
    
    Returns:
      * P: the 4x4 projection matrix.
      
    """
    return np.array([[1. / np.tan(angle), 0, 0, 0],
                     [0, ratio / np.tan(angle), 0, 0],
                     [0, 0, (zfar + znear) / (zfar - znear), 1],
                     [0, 0, -2. * zfar * znear / (zfar - znear), 0]])

def rotation_matrix(angle, axis=0):
    """Return a rotation matrix.
    
    Arguments:
      * angle: the angle of the rotation, in radians.
      * axis=0: the axis around which the rotation is made. It can be
        0 (rotation around x), 1 (rotation around y), 2 (rotation around z).
    
    Returns:
      * R: the 4x4 rotation matrix.
    
    """
    mat = np.eye(4)
    ind = np.array(sorted(list(set(range(3)).difference([axis]))))
    mat[np.ix_(ind,ind)] = np.array([[np.cos(angle), np.sin(angle)],
                               [-np.sin(angle), np.cos(angle)]])
    return mat
    
def scale_matrix(x, y, z):
    """Return a scaling matrix.
    
    Arguments:
      * x, y, z: the scaling coefficients in each direction.
      
    Returns:
      * S: the 4x4 projection matrix.
      
    """
    return np.diag([x, y, z, 1.])
    
def translation_matrix(x, y, z):
    """Return a translation matrix.
    
    Arguments:
      * x, y, z: the translation coefficients in each direction.
      
    Returns:
      * S: the 4x4 translation matrix.
      
    """
    return np.array([
      [1,      0,      0,       0],
      [0,      1,      0,       0], 
      [0,      0,      1,       0],
      [-x, -y, -z,  1]
    ])
    
def camera_matrix(eye, target=None, up=None):
    """Return a camera matrix.
    
    Arguments:
      * eye: the position of the camera as a 3-vector.
      * target: the position of the view target of the camera, as a 3-vector.
      * up: a normalized vector pointing in the up direction, as a 3-vector.
      
    Returns:
      * S: the 4x4 camera matrix.
      
    """
    if target is None:
        target = np.zeros(3)
    if up is None:
        target = np.array([0., 1., 0.])
    zaxis = normalize(target - eye)  # look at vector
    xaxis = normalize(np.cross(up, zaxis))  # right vector
    yaxis = normalize(np.cross(zaxis, xaxis))  # up vector
    
    orientation = np.array([
        [xaxis[0], yaxis[0], zaxis[0],     0],
        [xaxis[1], yaxis[1], zaxis[1],     0],
        [xaxis[2], yaxis[2], zaxis[2],     0],
        [      0,       0,       0,     1]
        ])
     
    translation = translation_matrix(*eye)
 
    return np.dot(translation, orientation)
    

class MeshVisual(Visual):
    """Template for basic 3D rendering.
    
    This template allows to render 3D vertices with 3D perspective and basic
    diffusive and ambient lighting.
    
    """
    def initialize_navigation(self, is_static=False):
        """Add static or dynamic position transformation."""
        
        # dynamic navigation
        if not is_static:
            self.add_uniform("transform", vartype="float", ndim=(4,4),
                size=None, data=np.eye(4))
            
            self.add_vertex_main("""
                gl_Position = projection * camera * transform * gl_Position;""",
                    position='last')
        # static
        else:
            self.add_vertex_main("""
                gl_Position = projection * camera * gl_Position;""")
        
    def initialize_default(self, is_static=False, constrain_ratio=False, **kwargs): 
        """Default initialization with navigation-related code."""
        self.is_static = is_static
        self.constrain_ratio = constrain_ratio
        self.initialize_navigation(is_static)
    
    def initialize(self, camera_angle=None, camera_ratio=None, autocolor=None,
        camera_zrange=None, position=None, color=None, normal=None, index=None,
        vertex_shader=None):
        """Initialize the template.
        
        Arguments:
          * camera_angle: the view angle of the camera, in radians.
          * camera_ratio: the W/H ratio of the camera.
          * camera_zrange: a pair with the far and near z values for the camera
            projection.
        
        Template fields are:
          * `position`: an attribute with the positions as 3D vertices,
          * `normal`: an attribute with the normals as 3D vectors,
          * `color`: an attribute with the color of each vertex, as 4D vertices.
          * `projection`: an uniform with the 4x4 projection matrix, returned by
            `projection_matrix()`.
          * `camera`: an uniform with the 4x4 camera matrix, returned by
            `camera_matrix()`.
          * `transform`: an uniform with the 4x4 transform matrix, returned by
            a dot product of `scale_matrix()`, `rotation_matrix()` and
            `translation_matrix()`.
          * `light_direction`: the direction of the diffuse light as a
            3-vector.
          * `ambient_light`: the amount of ambient light (white color).
            
        """
        
        if autocolor is not None:
            color = get_color(autocolor)
        
        
        # default camera parameters
        if camera_angle is None:
            camera_angle = np.pi / 4
        if camera_ratio is None:
            camera_ratio = 4./3.
        if camera_zrange is None:
            camera_zrange = (.5, 10.)
            
        self.size = position.shape[0]
        if self.primitive_type is None:
            self.primitive_type = 'TRIANGLES'
        
        # attributes
        self.add_attribute("position", vartype="float", ndim=3, data=position)
        self.add_attribute("normal", vartype="float", ndim=3, data=normal)
        self.add_attribute("color", vartype="float", ndim=4, data=color)
        if index is not None:
            self.add_index("index", data=index)
        
        # varying color
        self.add_varying("varying_color", vartype="float", ndim=4)
        
        # default matrices
        projection = projection_matrix(camera_angle, camera_ratio, *camera_zrange)
        camera = camera_matrix(np.array([0., 0., -4.]),  # position
                               np.zeros(3),              # look at
                               np.array([0., 1., 0.]))   # top
        transform = np.eye(4)
                
        # matrix uniforms
        self.add_uniform("projection", ndim=(4, 4), size=None, data=projection)
        self.add_uniform("camera", ndim=(4, 4), size=None, data=camera)
        self.add_uniform("transform", ndim=(4, 4), size=None, data=transform)
        
        # diffuse and ambient light
        light_direction = normalize(np.array([0., 0., -1.]))
        ambient_light = .25
        self.add_uniform("light_direction", size=None, ndim=3, data=light_direction)
        self.add_uniform("ambient_light", size=None, ndim=1, data=ambient_light)
        
        # vertex shader with transformation matrices and basic lighting
        if not vertex_shader:
            vertex_shader = """
            // convert the position from 3D to 4D.
            gl_Position = vec4(position, 1.0);
            // compute the amount of light
            float light = dot(light_direction, normalize(mat3(camera) * mat3(transform) * normal));
            light = clamp(light, 0, 1);
            // add the ambient term
            light = clamp(ambient_light + light, 0, 1);
            // compute the final color
            varying_color = color * light;
            // keep the transparency
            varying_color.w = color.w;
            """
        self.add_vertex_main(vertex_shader)
        
        # basic fragment shader
        self.add_fragment_main("""
            out_color = varying_color;
        """)
        
        # self.initialize_viewport(True)
########NEW FILE########
__FILENAME__ = plot_visual
import numpy as np
from galry import get_color, get_next_color
from visual import Visual

__all__ = ['process_coordinates', 'PlotVisual']

def process_coordinates(x=None, y=None, thickness=None):
    # handle the case where x is defined and not y: create x
    if y is None and x is not None:
        if x.ndim == 1:
            x = x.reshape((1, -1))
        nplots, nsamples = x.shape
        y = x
        x = np.tile(np.linspace(0., 1., nsamples).reshape((1, -1)), (nplots, 1))
        
    # convert into arrays
    x = np.array(x, dtype=np.float32)#.squeeze()
    y = np.array(y, dtype=np.float32)#.squeeze()
    
    # x and y should have the same shape
    assert x.shape == y.shape
    
    # enforce 2D for arrays
    if x.ndim == 1:
        x = x.reshape((1, -1))
        y = y.reshape((1, -1))
    
    # create the position matrix
    position = np.empty((x.size, 2), dtype=np.float32)
    position[:, 0] = x.ravel()
    position[:, 1] = y.ravel()
    
    
    return position, x.shape
    

class PlotVisual(Visual):
    def initialize(self, x=None, y=None, color=None, point_size=1.0,
            position=None, nprimitives=None, index=None,
            color_array_index=None, thickness=None,
            options=None, autocolor=None, autonormalizable=True):
            
        # if position is specified, it contains x and y as column vectors
        if position is not None:
            position = np.array(position, dtype=np.float32)
            if thickness:
                shape = (2 * position.shape[0], 1)
            else:
                shape = (1, position.shape[0])
        else:
            position, shape = process_coordinates(x=x, y=y)
            if thickness:
                shape = (shape[0], 2 * shape[1])
        
        
        # register the size of the data
        self.size = np.prod(shape)
        
        # there is one plot per row
        if not nprimitives:
            nprimitives = shape[0]
            nsamples = shape[1]
        else:
            nsamples = self.size // nprimitives
        
        
        # handle thickness
        if thickness and position.shape[0] >= 2:
            w = thickness
            n = self.size
            X = position
            Y = np.zeros((n, 2))
            u = np.zeros((n/2, 2))
            X2 = np.vstack((X, 2*X[-1,:]-X[-2,:]))
            u[:,0] = -np.diff(X2[:,1])
            u[:,1] = np.diff(X2[:,0])
            r = (u[:,0] ** 2 + u[:,1] ** 2) ** .5
            rm = r.mean()
            r[r == 0.] = rm
            # print u
            # print r
            # ind = np.nonzero(r == 0.)[0]
            # print ind, ind-1
            # r[ind] = r[ind - 1]
            u[:,0] /= r
            u[:,1] /= r
            Y[::2,:] = X - w * u
            Y[1::2,:] = X + w * u
            position = Y
            x = Y[:,0]
            y = Y[:,1]
            # print x
            # print y
            self.primitive_type = 'TRIANGLE_STRIP'
            
            
        # register the bounds
        if nsamples <= 1:
            self.bounds = [0, self.size]
        else:
            self.bounds = np.arange(0, self.size + 1, nsamples)
        
        # normalize position
        # if viewbox:
            # self.add_normalizer('position', viewbox)
        
        # by default, use the default color
        if color is None:
            if nprimitives <= 1:
                color = self.default_color
        
        # automatic color with color map
        if autocolor is not None:
            if nprimitives <= 1:
                color = get_next_color(autocolor)
            else:
                color = [get_next_color(i + autocolor) for i in xrange(nprimitives)]
            
            
        # # handle the case where the color is a string where each character
        # # is a color (eg. 'ry')
        # if isinstance(color, basestring):
            # color = list(color)
        color = get_color(color)
        # handle the case where there is a single color given as a list of
        # RGB components instead of a tuple
        if type(color) is list:
            if color and (type(color[0]) != tuple) and (3 <= len(color) <= 4):
                color = tuple(color)
            else:
                color = np.array(color)
        # first, initialize use_color_array to False except if
        # color_array_index is not None
        use_color_array = color_array_index is not None
        if isinstance(color, np.ndarray):
            colors_ndim = color.shape[1]
            # first case: one color per point
            if color.shape[0] == self.size:
                single_color = False
            # second case: use a color array so that each plot has a single
            # color, this saves memory since there is a single color in
            # memory for any plot
            else:
                use_color_array = True
                single_color = False
        elif type(color) is tuple:
            single_color = True
            colors_ndim = len(color)
        
        # set position attribute
        self.add_attribute("position", ndim=2, data=position, 
            autonormalizable=autonormalizable)
        
        if index is not None:
            index = np.array(index)
            # self.size = len(index)
            self.add_index("index", data=index)
        
        # single color case: no need for a color buffer, just use default color
        if single_color and not use_color_array:
            self.add_uniform("color", ndim=colors_ndim, data=color)
            if colors_ndim == 3:
                self.add_fragment_main("""
            out_color = vec4(color, 1.0);
                """)
            elif colors_ndim == 4:
                self.add_fragment_main("""
            out_color = color;
                """)
        
        # multiple colors case: color attribute
        elif not use_color_array:
            self.add_attribute("color", ndim=colors_ndim, data=color)
            self.add_varying("varying_color", vartype="float", ndim=colors_ndim)
            
            self.add_vertex_main("""
            varying_color = color;
            """)
            
            if colors_ndim == 3:
                self.add_fragment_main("""
            out_color = vec4(varying_color, 1.0);
                """)
            elif colors_ndim == 4:
                self.add_fragment_main("""
            out_color = varying_color;
                """)
        
        # multiple colors, but with a color array to save memory
        elif use_color_array:
            if color_array_index is None:
                color_array_index = np.repeat(np.arange(nprimitives), nsamples)
            color_array_index = np.array(color_array_index)
                
            ncolors = color.shape[0]
            ncomponents = color.shape[1]
            color = color.reshape((1, ncolors, ncomponents))
            
            dx = 1. / ncolors
            offset = dx / 2.
            
            self.add_texture('colormap', ncomponents=ncomponents, ndim=1, data=color)
            self.add_attribute('index', ndim=1, vartype='int', data=color_array_index)
            self.add_varying('vindex', vartype='int', ndim=1)
            
            self.add_vertex_main("""
            vindex = index;
            """)
            
            self.add_fragment_main("""
            float coord = %.5f + vindex * %.5f;
            vec4 color = texture1D(colormap, coord);
            out_color = color;
            """ % (offset, dx))

        # add point size uniform (when it's not specified, there might be some
        # bugs where its value is obtained from other datasets...)
        self.add_uniform("point_size", data=point_size)
        self.add_vertex_main("""gl_PointSize = point_size;""")
        

########NEW FILE########
__FILENAME__ = rectangles_visual
import numpy as np
from plot_visual import PlotVisual
from galry import get_color
    
class RectanglesVisual(PlotVisual):
    """Template for displaying one or several rectangles. This template
    derives from PlotTemplate."""
    
    def coordinates_compound(self, data):
        """Compound function for the coordinates variable.
        
        Arguments:
          * data: a Nx4 array where each line contains the coordinates of the
            rectangle corners as (x0, y0, x1, y1)
        
        Returns:
          * dict(position=position): the coordinates of all vertices used
            to render the rectangles as TriangleStrips.
        
        """
        if type(data) is tuple:
            data = np.array(data, dtype=np.float32).reshape((1, -1))
        # reorder coordinates to make sure that first corner is lower left
        # corner
        data[:,0], data[:,2] = data[:,[0, 2]].min(axis=1), data[:,[0, 2]].max(axis=1)
        data[:,1], data[:,3] = data[:,[1, 3]].min(axis=1), data[:,[1, 3]].max(axis=1)
        
        nprimitives = data.shape[0]
        x0, y0, x1, y1 = data.T
        
        # create vertex positions, 4 per rectangle
        position = np.zeros((4 * nprimitives, 2), dtype=np.float32)
        position[0::4,0] = x0
        position[0::4,1] = y0
        position[1::4,0] = x1
        position[1::4,1] = y0
        position[2::4,0] = x0
        position[2::4,1] = y1
        position[3::4,0] = x1
        position[3::4,1] = y1
        
        return dict(position=position)
    
    def initialize(self, coordinates=None, color=None, autocolor=None,
        depth=None, autonormalizable=True):
        
        if type(coordinates) is tuple:
            coordinates = np.array(coordinates, dtype=np.float32).reshape((1, -1))
        nprimitives = coordinates.shape[0]
        
        if autocolor is not None:
            color = get_color(autocolor)
        
        if color is None:
            color = self.default_color
            
        # If there is one color per rectangle, repeat the color array so
        # that there is one color per vertex.
        if isinstance(color, np.ndarray):
            if color.shape[0] == nprimitives:
                color = np.repeat(color, 4, axis=0)
        
        # there are four vertices per rectangle
        self.size = 4 * nprimitives
        self.primitive_type = 'TRIANGLE_STRIP'
        self.bounds = np.arange(0, self.size + 1, 4)
        

        position = self.coordinates_compound(coordinates)['position']
        
        super(RectanglesVisual, self).initialize(position=position, 
            color=color, nprimitives=nprimitives,
            autonormalizable=autonormalizable)# depth=depth)
            
        self.add_compound("coordinates", fun=self.coordinates_compound, 
            data=coordinates)
            
        self.depth = depth
########NEW FILE########
__FILENAME__ = sprite_visual
import numpy as np
from visual import Visual
from plot_visual import process_coordinates
from galry import get_color, get_next_color
    
class SpriteVisual(Visual):
    """Template displaying one texture in multiple positions with
    different colors."""
    
    def initialize(self, x=None, y=None, color=None, autocolor=None,
            texture=None, position=None, point_size=None, zoomable=False):
            
        # if position is specified, it contains x and y as column vectors
        if position is not None:
            position = np.array(position, dtype=np.float32)
            # shape = (position.shape[0], 1)
        else:
            position, shape = process_coordinates(x=x, y=y)
            
        texsize = float(max(texture.shape[:2]))
        shape = texture.shape
        ncomponents = texture.shape[2]
        self.size = position.shape[0]
        
        if shape[0] == 1:
            self.ndim = 1
        elif shape[0] > 1:
            self.ndim = 2
        
        self.primitive_type = 'POINTS'
        
        # normalize position
        # if viewbox:
            # self.add_normalizer('position', viewbox)
        # self.normalize = normalize
            
        # default color
        if color is None:
            color = self.default_color
        
        
        # automatic color with color map
        if autocolor is not None:
            color = get_next_color(autocolor)
            
        
        color = get_color(color)
        
        # handle the case where there is a single color given as a list of
        # RGB components instead of a tuple
        if type(color) is list:
            if color and (type(color[0]) != tuple) and (3 <= len(color) <= 4):
                color = tuple(color)
            else:
                color = np.array(color)
        if isinstance(color, np.ndarray):
            colors_ndim = color.shape[1]
            # one color per point
            single_color = False
        elif type(color) is tuple:
            single_color = True
            colors_ndim = len(color)
            
            
        texture_shader = """
        out_color = texture%NDIM%(tex_sampler, gl_PointCoord%POINTCOORD%) * %COLOR%;
        """
            
        
        shader_ndim = "%dD" % self.ndim
        if self.ndim == 1:
            shader_pointcoord = ".x"
        else:
            shader_pointcoord = ""
            
        # single color case: no need for a color buffer, just use default color
        if single_color:
            self.add_uniform("color", ndim=colors_ndim, data=color)   
            shader_color_name = "color"
        # multiple colors case: color attribute
        else:
            self.add_attribute("color", ndim=colors_ndim, data=color)
            self.add_varying("varying_color", vartype="float", ndim=colors_ndim)
            self.add_vertex_main("""
            varying_color = color;
            """)
            shader_color_name = "varying_color"
            
        if colors_ndim == 3:
            shader_color = "vec4(%s, 1.0)" % shader_color_name
        elif colors_ndim == 4:
            shader_color = shader_color_name
        
        texture_shader = texture_shader.replace('%COLOR%', shader_color)
        texture_shader = texture_shader.replace('%NDIM%', shader_ndim)
        texture_shader = texture_shader.replace('%POINTCOORD%', shader_pointcoord)
        self.add_fragment_main(texture_shader)
        
        # add variables
        self.add_attribute("position", vartype="float", ndim=2, data=position,
            autonormalizable=True)
        self.add_texture("tex_sampler", size=shape, ndim=self.ndim,
            ncomponents=ncomponents)
        self.add_compound("texture", fun=lambda texture: \
                         dict(tex_sampler=texture), data=texture)
        
        # size
        if point_size is None:
            point_size = texsize
        
        if isinstance(point_size, np.ndarray):
            self.add_attribute("point_size", vartype="float", ndim=1,
                data=point_size)
        else:
            self.add_uniform("point_size", vartype="float", ndim=1, data=point_size)
        
        # Vertex shader
        if zoomable:
            # The size of the points increases with zoom.
            self.add_vertex_main("""
            gl_PointSize = point_size * max(scale.x, scale.y);
            """)
        else:
            self.add_vertex_main("""
            gl_PointSize = point_size;
            """)
            
        
########NEW FILE########
__FILENAME__ = surface_visual
import numpy as np
from visual import Visual
from mesh_visual import MeshVisual

from galry.tools import hsv_to_rgb

def colormap(x):
    """Colorize a 2D grayscale array.
    
    Arguments: 
      * x:an NxM array with values in [0,1] 
    
    Returns:
      * y: an NxMx3 array with a rainbow color palette.
    
    """
    x = np.clip(x, 0., 1.)
    
    # initial and final gradient colors, here rainbow gradient
    col0 = np.array([.67, .91, .65]).reshape((1, 1, -1))
    col1 = np.array([0., 1., 1.]).reshape((1, 1, -1))
    
    col0 = np.tile(col0, x.shape + (1,))
    col1 = np.tile(col1, x.shape + (1,))
    
    x = np.tile(x.reshape(x.shape + (1,)), (1, 1, 3))
    
    return hsv_to_rgb(col0 + (col1 - col0) * x)

    
__all__ = ['SurfaceVisual']

class SurfaceVisual(MeshVisual):
    def initialize(self, Z, *args, **kwargs):
        
        assert Z.ndim == 2, "Z must have exactly two dimensions"
        
        n, m = Z.shape

        # generate grid
        x = np.linspace(-1., 1., m)
        y = np.linspace(-1., 1., n)
        X, Y = np.meshgrid(x, y)

        # generate vertices positions
        position = np.hstack((X.reshape((-1, 1)), Z.reshape((-1, 1)), Y.reshape((-1, 1)),))

        #color
        m, M = Z.min(), Z.max()
        if m != M:
            Znormalized = (Z - m) / (M - m)
        else:
            Znormalized = Z
        color = colormap(Znormalized).reshape((-1, 3))
        color = np.hstack((color, np.ones((n*n,1))))

        # normal
        U = np.dstack((X[:,1:] - X[:,:-1],
                       Y[:,1:] - Y[:,:-1],
                       Z[:,1:] - Z[:,:-1]))
        V = np.dstack((X[1:,:] - X[:-1,:],
                       Y[1:,:] - Y[:-1,:],
                       Z[1:,:] - Z[:-1,:]))
        U = np.hstack((U, U[:,-1,:].reshape((-1,1,3))))
        V = np.vstack((V, V[-1,:,:].reshape((1,-1,3))))
        W = np.cross(U, V)
        normal0 = W.reshape((-1, 3))
        normal = np.zeros_like(normal0)
        normal[:,0] = normal0[:,0]
        normal[:,1] = normal0[:,2]
        normal[:,2] = normal0[:,1]

        # tesselation of the grid
        index = []
        for i in xrange(n-1):
            for j in xrange(n-1):
                index.extend([i*n+j, (i+1)*n+j, i*n+j+1,
                              (i+1)*n+j, i*n+j+1, (i+1)*n+j+1])
        index = np.array(index)

        kwargs.update(
            position=position,
            normal=normal,
            color=color, 
            index=index,
        )        
        super(SurfaceVisual, self).initialize(*args, **kwargs)
    
        
    
    
    
    
########NEW FILE########
__FILENAME__ = texture_visual
import numpy as np
from visual import Visual, RefVar
    
from galry.tools import hsv_to_rgb

def colormap(x):
    """Colorize a 2D grayscale array.
    
    Arguments: 
      * x:an NxM array with values in [0,1] 
    
    Returns:
      * y: an NxMx3 array with a rainbow color palette.
    
    """
    x = np.clip(x, 0., 1.)
    
    # initial and final gradient colors, here rainbow gradient
    col0 = np.array([.67, .91, .65]).reshape((1, 1, -1))
    col1 = np.array([0., 1., 1.]).reshape((1, 1, -1))
    
    col0 = np.tile(col0, x.shape + (1,))
    col1 = np.tile(col1, x.shape + (1,))
    
    x = np.tile(x.reshape(x.shape + (1,)), (1, 1, 3))
    
    return hsv_to_rgb(col0 + (col1 - col0) * x)

    
    
class TextureVisual(Visual):
    """Visual that displays a colored texture."""
    
    def points_compound(self, points=None):
        """Compound function for the coordinates of the texture."""
        if points is None:
            points = (-1, -1, 1, 1)
        x0, y0, x1, y1 = points
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        
        position = np.zeros((4,2))
        position[0,:] = (x0, y0)
        position[1,:] = (x1, y0)
        position[2,:] = (x0, y1)
        position[3,:] = (x1, y1)

        return dict(position=position)
        
    def texture_compound(self, texture):
        """Compound variable for the texture data."""
        return dict(tex_sampler=texture)
    
    def initialize_fragment(self):
        """Set the fragment shader code."""
        # if self.ndim == 1:
            # shader_pointcoord = ".x"
        # else:
            # shader_pointcoord = ""
        shader_pointcoord = ""
        fragment = """
        out_color = texture%dD(tex_sampler, varying_tex_coords%s);
        """ % (self.ndim, shader_pointcoord)
        # print fragment
        self.add_fragment_main(fragment)
    
    def initialize(self, texture=None, points=None,
            mipmap=None, minfilter=None, magfilter=None):
        
        if isinstance(texture, RefVar):
            targettex = self.resolve_reference(texture)['data']
            shape, ncomponents = targettex.shape[:2], targettex.shape[2]
        elif texture is not None:
            
            if texture.ndim == 2:
                m, M = texture.min(), texture.max()
                if m < M:
                    texture = (texture - m) / (M - m)
                texture = colormap(texture)
                
            shape = texture.shape[:2]
            ncomponents = texture.shape[2]
        else:
            shape = (2, 2)
            ncomponents = 3
        if shape[0] == 1:
            ndim = 1
        elif shape[0] > 1:
            ndim = 2
        self.ndim = ndim
        
        # four points for a rectangle containing the texture
        # the rectangle is made up by 2 triangles
        self.size = 4
        self.texsize = shape
        self.primitive_type = 'TRIANGLE_STRIP'
        
        if points is None:
            ratio = shape[1] / float(shape[0])
            if ratio < 1:
                a = ratio
                points = (-a, -1., a, 1.)
            else:
                a = 1. / ratio
                points = (-1., -a, 1., a)
        
        # texture coordinates, interpolated in the fragment shader within the
        # rectangle primitive
        if self.ndim == 1:
            tex_coords = np.array([0, 1, 0, 1])
        elif self.ndim == 2:
            tex_coords = np.zeros((4,2))
            tex_coords[0,:] = (0, 1)
            tex_coords[1,:] = (1, 1)
            tex_coords[2,:] = (0, 0)
            tex_coords[3,:] = (1, 0)
        
        # contains the position of the points
        self.add_attribute("position", vartype="float", ndim=2)
        self.add_compound("points", fun=self.points_compound,
            data=points)
        
        # texture coordinates
        self.add_attribute("tex_coords", vartype="float", ndim=ndim,
            data=tex_coords)
        self.add_varying("varying_tex_coords", vartype="float", ndim=ndim)
        
        if texture is not None:
            self.add_texture("tex_sampler", size=shape, ndim=ndim,
                ncomponents=ncomponents,
                mipmap=mipmap,
                minfilter=minfilter,
                magfilter=magfilter,
                )
            # HACK: to avoid conflict in GLSL shader with the "texture" function
            # we redirect the "texture" variable here to "tex_sampler" which
            # is the real name of the variable in the shader
            self.add_compound("texture", fun=self.texture_compound, data=texture)

        # pass the texture coordinates to the varying variable
        self.add_vertex_main("""
            varying_tex_coords = tex_coords;
        """)
        
        # initialize the fragment code
        self.initialize_fragment()
            
        
########NEW FILE########
__FILENAME__ = text_visual
import numpy as np
import os
from galry import log_debug, log_info, log_warn, get_color
from fontmaps import load_font
from visual import Visual

__all__ = ['TextVisual']

VS = """
gl_Position.x += (offset - text_width / 2) * spacing.x / window_size.x;
gl_Position.y -= index * spacing.y / window_size.y;

gl_Position.xy = gl_Position.xy + posoffset / window_size;

gl_PointSize = point_size;
flat_text_map = text_map;
"""

def FS(background_transparent=True):
    if background_transparent:
        background_transparent_shader = "letter_alpha"
    else:
        background_transparent_shader = "1."
    fs = """
// relative coordinates of the pixel within the sprite (in [0,1])
float x = gl_PointCoord.x;
float y = gl_PointCoord.y;

// size of the corresponding character
float w = flat_text_map.z;
float h = flat_text_map.w;

// display the character at the left of the sprite
float delta = h / w;
x = delta * x;
if ((x >= 0) && (x <= 1))
{
    // coordinates of the character in the font atlas
    vec2 coord = flat_text_map.xy + vec2(w * x, h * y);
    float letter_alpha = texture2D(tex_sampler, coord).a;
    out_color = color * letter_alpha;
    out_color.a = %s;
}
else
    out_color = vec4(0, 0, 0, 0);
""" % background_transparent_shader
    return fs


class TextVisual(Visual):
    """Template for displaying short text on a single line.
    
    It uses the following technique: each character is rendered as a sprite,
    i.e. a pixel with a large point size, and a single texture for every point.
    The texture contains a font atlas, i.e. all characters in a given font.
    Every point comes with coordinates that indicate which small portion
    of the font atlas to display (that portion corresponds to the character).
    This is all done automatically, thanks to a font atlas stored in the
    `fontmaps` folder. There needs to be one font atlas per font and per font
    size. Also, there is a configuration text file with the coordinates and
    size of every character. The software used to generate font maps is
    AngelCode Bitmap Font Generator.
    
    For now, there is only the Segoe font.
    
    """
                
    def position_compound(self, coordinates=None):
        """Compound variable with the position of the text. All characters
        are at the exact same position, and are then shifted in the vertex
        shader."""
        if coordinates is None:
            coordinates = (0., 0.)
        if type(coordinates) == tuple:
            coordinates = [coordinates]
            
        coordinates = np.array(coordinates)
        position = np.repeat(coordinates, self.textsizes, axis=0)
        return dict(position=position)
    
    def text_compound(self, text):
        """Compound variable for the text string. It changes the text map,
        the character position, and the text width."""
        
        coordinates = self.coordinates
        
        if "\n" in text:
            text = text.split("\n")
            
        if type(text) == list:
            self.textsizes = [len(t) for t in text]
            text = "".join(text)
            if type(coordinates) != list:
                coordinates = [coordinates] * len(self.textsizes)
            index = np.repeat(np.arange(len(self.textsizes)), self.textsizes)
            text_map = self.get_map(text)
            
            # offset for all characters in the merging of all texts
            offset = np.hstack((0., np.cumsum(text_map[:, 2])[:-1]))
            
            # for each text, the cumsum of the length of all texts strictly
            # before
            d = np.hstack(([0], np.cumsum(self.textsizes)[:-1]))
            
            # compensate the offsets for the length of each text
            offset -= np.repeat(offset[d], self.textsizes)
            
            text_width = 0.
                
        else:
            self.textsizes = len(text)
            text_map = self.get_map(text)
            offset = np.hstack((0., np.cumsum(text_map[:, 2])[:-1]))    
            text_width = offset[-1]
            index = np.zeros(len(text))
            
        self.size = len(text)
        
        d = dict(text_map=text_map, offset=offset, text_width=text_width,
            index=index)
        d.update(self.position_compound(coordinates))
        
        return d
    
    def initialize_font(self, font, fontsize):
        """Initialize the specified font at a given size."""
        self.texture, self.matrix, self.get_map = load_font(font, fontsize)

    def initialize(self, text, coordinates=(0., 0.), font='segoe', fontsize=24,
            color=None, letter_spacing=None, interline=0., autocolor=None,
            background_transparent=True,
            prevent_constrain=False, depth=None, posoffset=None):
        """Initialize the text template."""
        
        if prevent_constrain:
            self.constrain_ratio = False
            
        if autocolor is not None:
            color = get_color(autocolor)
            
        if color is None:
            color = self.default_color
        
        self.size = len(text)
        self.primitive_type = 'POINTS'
        self.interline = interline
        
        text_length = self.size
        self.initialize_font(font, fontsize)
        self.coordinates = coordinates
        
        point_size = float(self.matrix[:,4].max() * self.texture.shape[1])

        # template attributes and varyings
        self.add_attribute("position", vartype="float", ndim=2, data=np.zeros((self.size, 2)))
            
        self.add_attribute("offset", vartype="float", ndim=1)
        self.add_attribute("index", vartype="float", ndim=1)
        self.add_attribute("text_map", vartype="float", ndim=4)
        self.add_varying("flat_text_map", vartype="float", flat=True, ndim=4)
       
        if posoffset is None:
            posoffset = (0., 0.)
        self.add_uniform('posoffset', vartype='float', ndim=2, data=posoffset)
       
        # texture
        self.add_texture("tex_sampler", size=self.texture.shape[:2], ndim=2,
                            ncomponents=self.texture.shape[2],
                            data=self.texture)
        
        # pure heuristic (probably bogus)
        if letter_spacing is None:
            letter_spacing = (100 + 17. * fontsize)
        self.add_uniform("spacing", vartype="float", ndim=2,
                            data=(letter_spacing, interline))
        self.add_uniform("point_size", vartype="float", ndim=1,
                            data=point_size)
        # one color per
        if isinstance(color, np.ndarray) and color.ndim > 1:
            self.add_attribute('color0', vartype="float", ndim=4, data=color)
            self.add_varying('color', vartype="float", ndim=4)
            self.add_vertex_main('color = color0;')
        else:
            self.add_uniform("color", vartype="float", ndim=4, data=color)
        self.add_uniform("text_width", vartype="float", ndim=1)
        
        # compound variables
        self.add_compound("text", fun=self.text_compound, data=text)
        self.add_compound("coordinates", fun=self.position_compound, data=coordinates)

        # vertex shader
        self.add_vertex_main(VS, after='viewport')

        # fragment shader
        self.add_fragment_main(FS(background_transparent))
        
        self.depth = depth
########NEW FILE########
__FILENAME__ = visual
import numpy as np
import collections
from textwrap import dedent

__all__ = ['OLDGLSL', 'RefVar', 'Visual', 'CompoundVisual']

# HACK: if True, activate the OpenGL ES syntax, which is deprecated in the
# desktop version. However with the appropriate #version command in the shader
# most drivers should accept this syntax in the compatibility profile.
# Another option would be to activate/deactivate this variable depending
# on the OpenGL version: TODO
OLDGLSL = True


# Shader templates
# ----------------
if not OLDGLSL:
    VS_TEMPLATE = """
//%GLSL_VERSION_HEADER%
//%GLSL_PRECISION_HEADER%

%VERTEX_HEADER%
void main()
{
    %VERTEX_MAIN%
}

"""

    FS_TEMPLATE = """
//%GLSL_VERSION_HEADER%
//%GLSL_PRECISION_HEADER%

%FRAGMENT_HEADER%
out vec4 out_color;
void main()
{
    %FRAGMENT_MAIN%
}

"""

else:
    VS_TEMPLATE = """
//%GLSL_VERSION_HEADER%
//%GLSL_PRECISION_HEADER%

%VERTEX_HEADER%
void main()
{
    %VERTEX_MAIN%
}

"""

    FS_TEMPLATE = """
//%GLSL_VERSION_HEADER%
//%GLSL_PRECISION_HEADER%

%FRAGMENT_HEADER%
void main()
{
    vec4 out_color = vec4%DEFAULT_COLOR%;
    %FRAGMENT_MAIN%
    %FRAG%
}

"""

def _get_shader_type(varinfo):
    """Return the GLSL variable declaration statement from a variable 
    information.
    
    Arguments:
      * varinfo: a dictionary with the information about the variable,
        in particular the type (int/float) and the number of dimensions
        (scalar, vector or matrix).
    
    Returns:
      * declaration: the string containing the variable declaration.
        
    """
    if type(varinfo["ndim"]) == int or type(varinfo["ndim"]) == long:
        if varinfo["ndim"] == 1:
            shader_type = varinfo["vartype"]
        elif varinfo["ndim"] >= 2:
            shader_type = "vec%d" % varinfo["ndim"]
            if varinfo["vartype"] != "float":
                shader_type = "i" + shader_type
    # matrix: (2,2) or (3,3) or (4,4)
    elif type(varinfo["ndim"]) == tuple:
        shader_type = "mat%d" % varinfo["ndim"][0]
    return shader_type
    
# for OLDGLSL: no int possible in attributes or varyings, so we force float
# for uniforms, no problem with int
if OLDGLSL:
    def _get_shader_type_noint(varinfo):
        """Like `_get_shader_type` but only with floats, not int. Used
        in OpenGL ES (OLDGLSL)."""
        if varinfo["ndim"] == 1:
            shader_type = "float"
        elif varinfo["ndim"] >= 2:
            shader_type = "vec%d" % varinfo["ndim"]
        # matrix: (2,2) or (3,3) or (4,4)
        elif type(varinfo["ndim"]) == tuple:
            shader_type = "mat%d" % varinfo["ndim"][0]
        return shader_type
    

# Variable information
# --------------------
# Correspondance between Python data types and GLSL types.    
VARINFO_DICT = {
    # floats
    float: 'float',
    np.float32: 'float',
    np.float64: 'float',
    np.dtype('float32'): 'float',
    np.dtype('float64'): 'float',
    
    # integers
    int: 'int',
    long: 'int',
    np.int32: 'int',
    np.int64: 'int',
    np.dtype('int32'): 'int',
    np.dtype('int64'): 'int',
    
    # booleans
    bool: 'bool',
    np.bool: 'bool',
}

def _get_vartype(scalar):
    """Return the GLSL type of a scalar value."""
    return VARINFO_DICT[type(scalar)]
    
def _get_varinfo(data):
    """Infer variable information (type, number of components) from data.
    
    Arguments:
      * data: any value to be uploaded on the GPU.
    
    Returns:
      * varinfo: a dictionary with the information related to the data type.
      
    """
    
    # handle scalars
    if not hasattr(data, '__len__'):
        return dict(vartype=_get_vartype(data), ndim=1, size=None)
    
    # convert lists into array
    if type(data) == list:
        data = np.array(data)
        
    # handle tuples
    if type(data) == tuple:
        return dict(vartype=_get_vartype(data[0]),
            ndim=len(data), size=None)
    
    # handle arrays
    if isinstance(data, np.ndarray):
        vartype = VARINFO_DICT[data.dtype]
        if data.ndim == 1:
            ndim = 1
            size = len(data)
        elif data.ndim == 2:
            ndim = data.shape[1]
            size = data.shape[0]
        return dict(vartype=vartype, ndim=ndim, size=size)
    
def _get_texinfo(data):
    """Return the texture information of a texture data.
    
    Arguments:
      * data: the texture data as an array.
    
    Returns:
      * texinfo: a dictionary with the information related to the texture data.
      
    """
    assert data.ndim == 3
    size = data.shape[:2]
    if size[0] == 1:
        ndim = 1
    elif size[0] > 1:
        ndim = 2
    ncomponents = data.shape[2]
    return dict(size=size, ndim=ndim, ncomponents=ncomponents)
    
def _update_varinfo(varinfo, data):
    """Update incomplete varinfo dict from data.
    
    Arguments:
      * varinfo: a potentially incomplete variable information dictionary.
      * data: the associated data, used to complete the information.
      
    Returns:
      * varinfo: the completed information dictionary.
      
    """
    varinfo_data = _get_varinfo(data)
    if "vartype" not in varinfo:
        varinfo.update(vartype=varinfo_data['vartype'])
    if "ndim" not in varinfo:
        varinfo.update(ndim=varinfo_data['ndim'])
    if "size" not in varinfo:
        varinfo.update(size=varinfo_data['size'])
    return varinfo
    
def _update_texinfo(texinfo, data):
    """Update incomplete texinfo dict from data.
    
    Arguments:
      * texinfo: a potentially incomplete texture information dictionary.
      * data: the associated data, used to complete the information.
      
    Returns:
      * texinfo: the completed information dictionary.
      
    """
    texinfo_data = _get_texinfo(data)
    if "ncomponents" not in texinfo:
        texinfo.update(ncomponents=texinfo_data['ncomponents'])
    if "ndim" not in texinfo:
        texinfo.update(ndim=texinfo_data['ndim'])
    if "size" not in texinfo:
        texinfo.update(size=texinfo_data['size'])
    return texinfo
    
def _get_uniform_function_name(varinfo):
    """Return the name of the GL function used to update the uniform data.
    
    Arguments:
      * varinfo: the information dictionary about the variable.
    
    Returns:
      * funname: the name of the OpenGL function.
      * args: the tuple of arguments to this function. The data must be 
        appended to this tuple.
    
    """
    # NOTE: varinfo == dict(vartype=vartype, ndim=ndim, size=size)
    float_suffix = {True: 'f', False: 'i'}
    array_suffix = {True: 'v', False: ''}
        
    vartype = varinfo["vartype"]
    ndim = varinfo["ndim"]
    size = varinfo.get("size", None)
    args = ()
    
    # scalar or vector uniform
    if type(ndim) == int or type(ndim) == long:
        # find function name
        funname = "glUniform%d%s%s" % (ndim, \
                                       float_suffix[vartype == "float"], \
                                       array_suffix[size is not None])

        # find function arguments
        if size is not None:
            args += (size,)
            
    # matrix uniform
    elif type(ndim) == tuple:
        # find function name
        funname = "glUniformMatrix%dfv" % (ndim[0])
        args += (1, False,)
        
    return funname, args

    
# GLSL declaration functions
# --------------------------
def get_attribute_declaration(attribute):
    """Return the GLSL attribute declaration."""
    if not OLDGLSL:
        declaration = "layout(location = %d) in %s %s;\n" % \
                        (attribute["location"],
                         _get_shader_type(attribute), 
                         attribute["name"])
    else:
        declaration = "attribute %s %s;\n" % \
                        (_get_shader_type_noint(attribute), 
                         attribute["name"])
        
    return declaration
    
def get_uniform_declaration(uniform):
    """Return the GLSL uniform declaration."""
    tab = ""
    size = uniform.get("size", None)
    if size is not None:
        tab = "[%d]" % max(1, size)  # ensure that the size is always >= 1
    # add uniform declaration
    declaration = "uniform %s %s%s;\n" % \
        (_get_shader_type(uniform),
         uniform["name"],
         tab)
    return declaration
    
def get_texture_declaration(texture):
    """Return the GLSL texture declaration."""
    declaration = "uniform sampler%dD %s;\n" % (texture["ndim"], texture["name"])
    return declaration
    
def get_varying_declarations(varying):
    """Return the GLSL varying declarations for both vertex and fragment
    shaders."""
    vs_declaration = ""
    fs_declaration = ""
    
    if not OLDGLSL:
        shadertype = _get_shader_type(varying)
    else:
        shadertype = _get_shader_type_noint(varying)
    
    s = "%%s %s %s;\n" % \
        (shadertype, varying["name"])
         
    if not OLDGLSL:
        vs_declaration = s % "out"
        fs_declaration = s % "in"
    else:
        vs_declaration = s % "varying"
        fs_declaration = s % "varying"
    
    if not OLDGLSL:
        if varying.get("flat", None):
            vs_declaration = "flat " + vs_declaration
            fs_declaration = "flat " + fs_declaration
        
    return vs_declaration, fs_declaration


# Shader creator
# --------------
class ShaderCreator(object):
    """Create the shader codes using the defined variables in the visual."""
    def __init__(self):
        self.version_header = '#version 120'
        self.precision_header = 'precision mediump float;'
        
        # list of headers and main code portions of the vertex shader
        # self.vs_headers = []
        # self.vs_mains = []
        self.headers = {'vertex': [], 'fragment': []}
        self.mains = {'vertex': [], 'fragment': []}
        
        self.fragdata = None
        
    def set_variables(self, **kwargs):
        # record all visual variables in the shader creator
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        
        
    # Header-related methods
    # ----------------------
    def add_header(self, code, shader=None):
        code = dedent(code)
        self.headers[shader].append(code)
        
    def add_vertex_header(self, code):
        """Add code in the header of the vertex shader. Generally used to
        define custom functions, to be used in the main shader code."""
        self.add_header(code, 'vertex')
        
    def add_fragment_header(self, code):
        """Add code in the header of the fragment shader. Generally used to
        define custom functions, to be used in the main shader code."""
        self.add_header(code, 'fragment')
        
    def get_header(self, shader=None):
        header = "".join(self.headers[shader])
        if shader == 'vertex':
            header += "".join([get_uniform_declaration(uniform) for uniform in self.uniforms])
            header += "".join([get_attribute_declaration(attribute) for attribute in self.attributes])
        elif shader == 'fragment':
            header += "".join([get_uniform_declaration(uniform) for uniform in self.uniforms])
            header += "".join([get_texture_declaration(texture) for texture in self.textures])
        return header
        
        
    # Main-related methods
    # --------------------
    def add_main(self, code, shader=None, name=None, after=None, position=None):
        if name is None:
            name = '%s_main_%d' % (shader, len(self.mains[shader]))
        code = dedent(code)
        self.mains[shader].append(dict(name=name, code=code, after=after, position=position))
    
    def add_vertex_main(self, *args, **kwargs):
        """Add code in the main function of the vertex shader.
        At the end of the code, the vec2 variable `position` must have been
        defined, either as an attribute or uniform, or declared in the main
        code. It contains the position of the current vertex.
        Other output variables include `gl_PointSize` for the size of vertices
        in the case when the primitive type is `Points`.
        
        Arguments:
          * code: the GLSL code as a string.
          * index=None: the index of that code snippet in the final main
            function. By default (index=None), the code is appended at the end
            of the main function. With index=0, it is at the beginning of the
            main function. Other integer values may be used when using several
            calls to `add_vertex_main`. Or it can be 'end'.
        
        """
        kwargs['shader'] = 'vertex'
        self.add_main(*args, **kwargs)
        
    def add_fragment_main(self, *args, **kwargs):
        """Add code in the main function of the fragment shader.
        At the end of the code, the vec4 variable `out_color` must have been
        defined. It contains the color of the current pixel.
        
        Arguments:
          * code: the GLSL code as a string.
          * index=None: the index of that code snippet in the final main
            function. By default (index=None), the code is appended at the end
            of the main function. With index=0, it is at the beginning of the
            main function. Other integer values may be used when using several
            calls to `add_fragment_main`.
        
        """
        kwargs['shader'] = 'fragment'
        self.add_main(*args, **kwargs)
    
    def get_main(self, shader=None):
        mains = self.mains[shader]
        # first, all snippet names which do not have 'after' keyword, and which are not last
        order = [m['name'] for m in mains if m['after'] is None and m['position'] is None]
        # then, those which do not have 'after' keyword, but are last
        order += [m['name'] for m in mains if m['after'] is None and m['position'] == 'last']
        # then, get the final order with the "after" snippets
        for m in mains:
            if m['after']:
                # which index for "after"?
                if m['after'] in order:
                    index = order.index(m['after'])
                else:
                    index = len(order) - 1
                order.insert(index + 1, m['name'])
        # finally, get the final code
        main = ""
        for name in order:
            main += [m['code'] for m in mains if m['name'] == name][0]
        return main
    
    
    # Shader creation
    # ---------------
    def set_fragdata(self, fragdata):
        self.fragdata = fragdata
    
    def get_shader_codes(self):
        """Build the vertex and fragment final codes, using the declarations
        of all template variables."""
        vs = VS_TEMPLATE
        fs = FS_TEMPLATE
        
        # Shader headers
        vs_header = self.get_header('vertex')
        fs_header = self.get_header('fragment')
        
        # Varyings
        for varying in self.varyings:
            s1, s2 = get_varying_declarations(varying)
            vs_header += s1
            fs_header += s2
        
        # vs_header += "".join(self.vs_headers)
        # fs_header += "".join(self.fs_headers)
        
        # Integrate shader headers
        vs = vs.replace("%VERTEX_HEADER%", vs_header)
        fs = fs.replace("%FRAGMENT_HEADER%", fs_header)
        
        # Vertex and fragment main code
        vs_main = self.get_main('vertex')
        fs_main = self.get_main('fragment')
        
        # Integrate shader headers
        vs = vs.replace("%VERTEX_MAIN%", vs_main)
        fs = fs.replace("%FRAGMENT_MAIN%", fs_main)
        
        # frag color or frag data
        if self.fragdata is None:
            fs = fs.replace('%FRAG%', """gl_FragColor = out_color;""")
        else:
            fs = fs.replace('%FRAG%', """gl_FragData[%d] = out_color;""" % self.fragdata)
        
        # Make sure there are no Windows carriage returns
        vs = vs.replace(b"\r\n", b"\n")
        fs = fs.replace(b"\r\n", b"\n")
        
        # OLDGLSL does not know the texture function
        if not OLDGLSL:
            fs = fs.replace("texture1D(", "texture(" % 2)
            fs = fs.replace("texture2D(", "texture(" % 2)
        
        # set default color
        fs = fs.replace('%DEFAULT_COLOR%', str(self.default_color))
        
        # replace GLSL version header
        vs = vs.replace('%GLSL_VERSION_HEADER%', self.version_header)
        fs = fs.replace('%GLSL_VERSION_HEADER%', self.version_header)
        
        # replace GLSL precision header
        vs = vs.replace('%GLSL_PRECISION_HEADER%', self.precision_header)
        fs = fs.replace('%GLSL_PRECISION_HEADER%', self.precision_header)
    
        return vs, fs
    
    
    
# Reference variable
# ------------------
class RefVar(object):
    """Defines a reference variable to an attribute of any visual.
    This allows one attribute value to refer to the same memory buffer
    in both system and graphics memory."""
    def __init__(self, visual, variable):
        self.visual = visual
        self.variable = variable
        
    def __repr__(self):
        return "<reference variable to '%s.%s'>" % (self.visual, self.variable)
        
    
# Visual creator
# --------------
class BaseVisual(object):
    def __init__(self, scene, *args, **kwargs):
        self.scene = scene
        # default options
        self.kwargs = self.extract_common_parameters(**kwargs)
        
    def extract_common_parameters(self, **kwargs):
        self.size = kwargs.pop('size', 0)
        self.default_color = kwargs.pop('default_color', (1., 1., 0., 1.))
        self.bounds = kwargs.pop('bounds', None)
        self.is_static = kwargs.pop('is_static', False)
        self.position_attribute_name = kwargs.pop('position_attribute_name', 'position')
        self.primitive_type = kwargs.pop('primitive_type', None)
        self.constrain_ratio = kwargs.pop('constrain_ratio', False)
        self.constrain_navigation = kwargs.pop('constrain_navigation', False)
        self.visible = kwargs.pop('visible', True)
        # self.normalize = kwargs.pop('normalize', None)
        self.framebuffer = kwargs.pop('framebuffer', 0)
        self.fragdata = kwargs.pop('fragdata', None)
        return kwargs
        
    
class Visual(BaseVisual):
    """This class defines a visual to be displayed in the scene. It should
    be overriden."""
    def __init__(self, scene, *args, **kwargs):
        super(Visual, self).__init__(scene, *args, **kwargs)
        kwargs = self.kwargs
        self.variables = collections.OrderedDict()
        self.options = {}
        self.is_position_3D = False
        self.depth = None
        # initialize the shader creator
        self.shader_creator = ShaderCreator()
        self.reinitialization = False
        kwargs = self.resolve_references(**kwargs)
        # initialize the visual
        self.initialize(*args, **kwargs)
        self.initialize_default()
        # initialize the shader creator
        self.shader_creator.set_variables(
            attributes=self.get_variables('attribute'),
            uniforms=self.get_variables('uniform'),
            textures=self.get_variables('texture'),
            varyings=self.get_variables('varying'),
            default_color = self.default_color,
        )
        # finalize to make sure all variables and shader codes are well defined
        self.finalize()
        # create the shader source codes
        self.vertex_shader, self.fragment_shader = \
            self.shader_creator.get_shader_codes()
    
    
    # Reference variables methods
    # ---------------------------
    def get_visuals(self):
        """Return all visuals defined in the scene."""
        return self.scene['visuals']
        
    def get_visual(self, name):
        """Return a visual dictionary from its name."""
        visuals = [v for v in self.get_visuals() if v.get('name', '') == name]
        if not visuals:
            return None
        return visuals[0]
        
    def get_variable(self, name, visual=None):
        """Return a variable by its name, and for any given visual which 
        is specified by its name."""
        # get the variables list
        if visual is None:
            variables = self.variables.values()
        else:
            variables = self.get_visual(visual)['variables']
        variables = [v for v in variables if v.get('name', '') == name]
        if not variables:
            return None
        return variables[0]
        
    def resolve_reference(self, refvar):
        """Resolve a reference variable: return its true value (a Numpy array).
        """
        return self.get_variable(refvar.variable, visual=refvar.visual)
       
    def resolve_references(self, **kwargs):
        """Resolve all references in the visual initializer."""
        # deal with reference variables
        self.references = {}
        # record all reference variables in the references dictionary
        for name, value in kwargs.iteritems():
            if isinstance(value, RefVar):
                self.references[name] = value
                # then, resolve the reference value on the CPU only, so that
                # it can be used in initialize(). The reference variable will
                # still be registered in the visual dictionary, for later use
                # by the GL renderer.
                kwargs[name] = self.resolve_reference(value)['data']
        return kwargs
    
    
    # Reinitialization methods
    # ------------------------
    def reinit(self):
        """Begin a reinitialization process, where paint_manager.initialize()
        is called after initialization. The visual initializer is then
        called again, but it is only used to update the data, not to create
        the visual variables and the shader, which have already been created
        in the first place."""
        self.data_updating = {}
        self.reinitialization = True
        # force the bounds to be defined again
        self.bounds = None
       
    def get_data_updating(self):
        """Return the dictionary with the updated variable data."""
        # add some special keywords, if they are specified in self.initialize
        special_keywords = ['size', 'bounds', 'primitive_type']
        for keyword in special_keywords:
            val = getattr(self, keyword)
            if val is not None and keyword not in self.data_updating:
                self.data_updating[keyword] = val
        return self.data_updating
       
        
    # Variable methods
    # ----------------
    def add_foo(self, shader_type, name, **kwargs):
        # for reinitialization, just record the data
        if self.reinitialization:
            if 'data' in kwargs:
                self.data_updating[name] = kwargs['data']
            return
        # otherwise, add the variable normally
        kwargs['shader_type'] = shader_type
        kwargs['name'] = name
        # default parameters
        kwargs['vartype'] = kwargs.get('vartype', 'float')
        kwargs['size'] = kwargs.get('size', None)
        kwargs['ndim'] = kwargs.get('ndim', 1)
        self.variables[name] = kwargs
        
    def add_attribute(self, name, **kwargs):
        self.add_foo('attribute', name, **kwargs)
        
    def add_uniform(self, name, **kwargs):
        self.add_foo('uniform', name, **kwargs)
        
    def add_texture(self, name, **kwargs):
        # NEW: add texture index
        # if 'index' not in kwargs:
            # kwargs['index'] = len(self.get_variables('texture'))
        self.add_foo('texture', name, **kwargs)
        
    def add_framebuffer(self, name, **kwargs):
        # NEW: add texture index
        # if 'index' not in kwargs:
            # kwargs['index'] = len(self.get_variables('texture'))
        self.add_foo('framebuffer', name, **kwargs)
        
    def add_index(self, name, **kwargs):
        self.add_foo('index', name, **kwargs)
        
    def add_varying(self, name, **kwargs):
        self.add_foo('varying', name, **kwargs)
        
    def add_compound(self, name, **kwargs):
        # add the compound as a variable
        self.add_foo('compound', name, **kwargs)
        # process the compound: add the associated data in the corresponding
        # variables
        fun = kwargs['fun']
        data = kwargs['data']
        kwargs = fun(data)
        for name, value in kwargs.iteritems():
            self.variables[name]['data'] = value
        
    
    # Option methods
    # --------------
    def add_options(self, **kwargs):
        self.options.update(kwargs)
        
    # def add_normalizer(self, name, viewbox=None):
        # """Add a data normalizer for attribute 'name'."""
        # # option_name = '%s_normalizer' % name
        # # self.add_option(option_name=(name, viewbox))
        # if 'normalizers' not in self.options:
            # self.options['normalizers'] = {}
        # self.options['normalizers'][name] = viewbox
        
        
    # Variable methods
    # ----------------
    def get_variables(self, shader_type=None):
        """Return all variables defined in the visual."""
        if not shader_type:
            return self.variables
        else:
            return [var for (_, var) in self.variables.iteritems() \
                            if var['shader_type'] == shader_type]
        
        
    # Shader methods
    # --------------
    def add_vertex_header(self, *args, **kwargs):
        if not self.reinitialization:
            self.shader_creator.add_vertex_header(*args, **kwargs)
        
    def add_vertex_main(self, *args, **kwargs):
        if not self.reinitialization:
            self.shader_creator.add_vertex_main(*args, **kwargs)
        
    def add_fragment_header(self, *args, **kwargs):
        if not self.reinitialization:
            self.shader_creator.add_fragment_header(*args, **kwargs)
        
    def add_fragment_main(self, *args, **kwargs):
        if not self.reinitialization:
            self.shader_creator.add_fragment_main(*args, **kwargs)
        
    def set_fragdata(self, fragdata):
        self.shader_creator.set_fragdata(fragdata)
        
        
    # Default visual methods
    # ----------------------
    def initialize_default(self):
        """Default initialization for all child visuals."""
        self.initialize_navigation()
        self.initialize_viewport()
        
    def initialize_viewport(self):
        """Handle window resize in shaders."""
        self.add_uniform('viewport', vartype="float", ndim=2, data=(1., 1.))
        self.add_uniform('window_size', vartype="float", ndim=2)#, data=(600., 600.))
        if self.constrain_ratio:
            self.add_vertex_main("gl_Position.xy = gl_Position.xy / viewport;",
                position='last', name='viewport')
        
    def initialize_navigation(self):
        """Handle interactive navigation in shaders."""
        # dynamic navigation
        if not self.is_static:
            self.add_uniform("scale", vartype="float", ndim=2, data=(1., 1.))
            self.add_uniform("translation", vartype="float", ndim=2, data=(0., 0.))
            
            self.add_vertex_header("""
                // Transform a position according to a given scaling and translation.
                vec2 transform_position(vec2 position, vec2 scale, vec2 translation)
                {
                return scale * (position + translation);
                }
            """)
            
        if not self.is_static:            
            pos = "transform_position(%s.xy, scale, translation)" % self.position_attribute_name
        else:
            pos = "%s.xy" % self.position_attribute_name
        
        if self.is_position_3D:
            vs = """gl_Position = vec4(%s, %s.z, 1.);""" % (pos,
                self.position_attribute_name)
        else:
            vs = """gl_Position = vec4(%s, 0., 1.);""" % (pos)
        
        if self.depth is not None:
            vs += """gl_Position.z = %.4f;""" % self.depth
        
        self.add_vertex_main(vs, position='last', name='navigation')
        
        
    # Initialization methods
    # ----------------------
    def initialize(self, *args, **kwargs):
        """The visual should be defined here."""
    
    def finalize(self):
        """Finalize the template to make sure that shaders are compilable.
        
        This is the place to implement any post-processing algorithm on the
        shader sources, like custom template replacements at runtime.
        
        """
        
        # self.size is a mandatory variable
        assert self.size is not None
        
        # default rendering options
        if self.bounds is None:
            self.bounds = [0, self.size]
        # ensure the type of bounds
        self.bounds = np.array(self.bounds, dtype=np.int32)
    
        if self.fragdata is not None:
            self.set_fragdata(self.fragdata)
    
        if self.primitive_type is None:
            self.primitive_type = 'LINE_STRIP'
    
    
    # Output methods
    # --------------
    def get_variables_list(self):
        """Return the list of variables, to be used in the output dictionary
        containing all the visual information."""
        variables = self.variables.values()
        # handle reference variables
        for variable in variables:
            name = variable['name']
            if name in self.references:
                variable['data'] = self.references[name]
        return variables
    
    def get_dic(self):
        """Return the dict representation of the visual."""
        dic = {
            'size': self.size,
            'bounds': self.bounds,
            'visible': self.visible,
            'is_static': self.is_static,
            'options': self.options,
            'primitive_type': self.primitive_type,
            'constrain_ratio': self.constrain_ratio,
            'constrain_navigation': self.constrain_navigation,
            'framebuffer': self.framebuffer,
            # 'beforeclear': self.beforeclear,
            'variables': self.get_variables_list(),
            'vertex_shader': self.vertex_shader,
            'fragment_shader': self.fragment_shader,
        }
        return dic
        
    
class CompoundVisual(BaseVisual):
    def __init__(self, scene, *args, **kwargs):
        # super(CompoundVisual, self).__init__(scene, *args, **kwargs)
        self.visuals = []
        self.name = kwargs.pop('name')
        self.initialize(*args, **kwargs)
    
    def add_visual(self, visual_class, *args, **kwargs):
        name = kwargs.get('name', 'visual%d' % len(self.visuals))
        # prefix the visual name with the compound name
        kwargs['name'] = self.name + "_" + name
        self.visuals.append((visual_class, args, kwargs))
    
    def initialize(self, *args, **kwargs):
        pass
        
        
        
########NEW FILE########
__FILENAME__ = tut1-1
"""Tutorial 1.1: Pylab-style plotting.

In this tutorial, we show how to plot a basic figure with a pylab-/matlab- 
like high-level interface.

"""

from galry import *
from numpy import *

# We define a curve x -> sin(x) on [-10., 10.].
x = linspace(-10., 10., 10000)
y = .5 * sin(x)

# We plot this function.
plot(x, y)

# We set the limits for the y-axis.
ylim(-1, 1)

# Experiment with the default user actions! All actions can be changed but
# this would be the subject of a more advanced tutorial.
print("Press H to see all keyboard shortcuts and mouse movements!")

# Finally, we show the window. Internally, the real job happens here.
show()

########NEW FILE########
__FILENAME__ = tut1-2
"""Tutorial 1.2: Multiple curves.

In this tutorial, we show how to plot several curves efficiently.

"""

from galry import *
from numpy import *

# We'll plot 10 curves with 10,000 points in each.
m = 10
n = 10000

# z contains m signals with n random values in each. Each row is a signal.
z = .1 * random.randn(m, n)

# We shift the y coordinates in each line, so that each signal is shown
# separately.
z += arange(m).reshape((-1, 1))

# `color` is an m x 3 matrix, where each line contains the RGB components
# of the corresponding line. We also could use an alpha channel
# (transparency) with an m x 4 matrix.
color = random.rand(m, 3)

# We disable zooming out more than what the figure contains.
figure(constrain_navigation=True)

# We plot all signals and specify the color.
# Note: it is much faster to have a single plot command, rather than one plot
# per curve, especially if there are a lot of curves (like hundreds or
# thousands).
plot(z, color=color, options='r')

# We show the figure.
show()

########NEW FILE########
__FILENAME__ = tut1-3
"""Tutorial 1.3: Rasterplot.

In this tutorial, we show how to plot a raster plot using point sprites.
"""

from galry import *
from numpy import *

# Total number of spikes.
spikecount = 20000

# Total number of neurons.
n = 100

# Random neuron index for each spike.
neurons = random.randint(low=0, high=n, size=spikecount)

# One Poisson spike train with all spikes.
spiketimes = cumsum(random.exponential(scale=.01, size=spikecount))

# Neurons colors.
colors = random.rand(n, 3)

# New figure.
figure(constrain_navigation=True)

# We plot the neuron index wrt. spike times, with a | marker and the specified
# color.
plot(spiketimes, neurons, '|', ms = 5., color=colors[neurons, :])

# We specify the y axis limits.
ylim(-1, n)

# We plot the figure.
show()

########NEW FILE########
__FILENAME__ = tut1-4
"""Tutorial 1.4: Images.

In this tutorial, we show how to plot images.

"""

import os
from galry import *
from numpy import *
from matplotlib.pyplot import imread

# Specify that we want to constrain the ratio of the figure while navigating,
# since we'll show an image.
figure(constrain_ratio=True)

# We load the texture from an image using imread, which refers directly to
# the Matplotlib function.
path = os.path.dirname(os.path.realpath(__file__))
image = imread(os.path.join(path, 'images/earth.png'))

# We display the image and apply linear filtering and mipmapping.
# Zoom in and try filter=False to see the difference.
# You can fine-tune the filtering with the mipmap, minfilter, magfilter
# arguments. When filter=True, the values are:
#   * mipmap=True,
#   * minfilter='LINEAR_MIPMAP_NEAREST',
#   * magfilter='LINEAR'.
imshow(image, filter=True)

show()

########NEW FILE########
__FILENAME__ = tut1-5
"""Tutorial 1.5: Graphs.

In this tutorial we show how to plot graphs.

"""

from galry import *
from numpy import *

# We use networkx because it provides convenient functions to create and
# manipulate graphs, but this library is not required by Galry.
import networkx as nx

# We create a complete graph.      
g = nx.complete_graph(50)

# We compute a circular layout and get an array with the positions
# of all nodes.
pos = nx.circular_layout(g)
position = np.vstack([pos[i] for i in xrange(len(pos))]) - .5

# We retrieve the edges as an array where each line contains the two node
# indices of an edge, the indices referring to the `position` array.
edges = np.vstack(g.edges())

# We define random colors for all nodes, with an alpha channel to 1.
color = np.random.rand(len(position), 4)
color[:,-1] = 1

# We define the edges colors: the color in line i is the color of all
# edges linking node i to any other node. If an edge has two different colors
# at its two ends, then its color will be a gradient between the two colors.
# Here, we simply use the same color for nodes and edges, but with an
# alpha channel at 0.25.
edges_color = color.copy()
edges_color[:,-1] = .25

figure(constrain_ratio=True)

# We plot the graph.
graph(position=position, edges=edges, color=color, edges_color=edges_color)

show()

########NEW FILE########
__FILENAME__ = tut1-6
"""Tutorial 1.6: Bar plots.

In this tutorial we show how to plot efficiently several bar plots.

"""

from galry import *
from numpy import *
from numpy.random import *

# We generate 10 random bar plots of 100 values in each.
values = rand(10, 100)

# Offsets of histograms: we stack them vertically.
offset = vstack((zeros(10), arange(10))).T

# We plot the histograms with random colors.
barplot(values, offset=offset, color=rand(10, 3))

show()

########NEW FILE########
__FILENAME__ = tut1-7
"""Tutorial 1.7: 3D mesh.

In this tutorial we show how to plot a 3D mesh.

It is adapted from an example in the Glumpy package:
http://code.google.com/p/glumpy/

"""

from galry import *
from numpy import *

# load a 3D mesh from a OBJ file
vertices, normals, faces = load_mesh("images/mesh.obj")
n = len(vertices)

# face colors
color = (vertices + 1) / 2.
color = np.hstack((color, np.ones((n, 1))))

# display the mesf
mesh(position=vertices, color=color, normal=normals, index=faces.ravel())

show()

########NEW FILE########
__FILENAME__ = tut2-1
"""Tutorial 2.1: Text and interaction.

In this tutorial, we show how to display text and we give a first example
of the interaction system.

"""

from galry import *
from numpy import *

# This function takes x, y coordinates of the mouse and return a text.
def get_text(*pos):
    return "The mouse is at ({0:.2f}, {1:.2f}).".format(*pos)

# This is a callback function for the MouseMoveAction. The first parameter
# is the figure, the second a dictionary with parameters about the user
# actions (mouse, keyboard, etc.).
def mousemove(fig, params):
    # We get the text to display.
    text = get_text(*params['mouse_position'])
    
    # We update the text dynamically.
    fig.set_data(text=text, visual='mytext')

# We display a text and give it a unique name 'mytext' so that we can 
# refer to this visual in the mouse move callback. We also specify that
# this text should be fixed and not transformed while panning and zooming.
text("Move your mouse!", name='mytext', fontsize=22, is_static=True)

# We bind the mouse move action to the mousemove callback.
action('Move', mousemove)

show()

########NEW FILE########
__FILENAME__ = tut2-2
"""Tutorial 2.2: Animation.

In this tutorial, we show how to animate objects to smoothly follow the
cursor.

"""

from galry import *
from numpy import *

# Number of discs.
n = 100

# Display n static discs with an opacity gradient.
color = ones((n, 4))
color[:,2] = 0
color[:,3] = linspace(0.01, 0.1, n)
plot(zeros(n), zeros(n), 'o', color=color, ms=50, is_static=True)

# Global variable with the current disc positions.
position = zeros((n, 2))

# Global variable with the current mouse position.
mouse = zeros((1, 2))

# Animation weights for each disc, smaller = slower movement.
w = linspace(0.03, 0.1, n).reshape((-1, 1))

# Update the mouse position.
def mousemove(fig, param):
    global mouse
    mouse[0,:] = param['mouse_position']

# Animate the object.
def anim(fig, param):
    # The disc position is obtained through a simple linear filter of the
    # mouse position.
    global position
    position += w * (-position + mouse)
    fig.set_data(position=position)
    
# We bind the "Move" action to the "mousemove" callback.
action('Move', mousemove)

# We bind the "Animate" event to the "anim" callback.
animate(anim, dt=.01)

show()

########NEW FILE########
__FILENAME__ = tut2-3
"""Tutorial 2.3: Convay's Game of Life.

In this tutorial, we show how to simulate the Convay's Game of Life
by animating a texture at regular intervals.

"""

from galry import *
from numpy import *

# Grid size.
size = 64

# We define the function used to update the system. The system is defined
# as a matrix with 0s (dead cells) and 1s (alive cells).
def iterate(Z):
    """Perform an iteration of the system."""
    # code from http://dana.loria.fr/doc/numpy-to-dana.html
    # find number of neighbours that each square has
    N = zeros(Z.shape)
    N[1:, 1:] += Z[:-1, :-1]
    N[1:, :-1] += Z[:-1, 1:]
    N[:-1, 1:] += Z[1:, :-1]
    N[:-1, :-1] += Z[1:, 1:]
    N[:-1, :] += Z[1:, :]
    N[1:, :] += Z[:-1, :]
    N[:, :-1] += Z[:, 1:]
    N[:, 1:] += Z[:, :-1]
    # a live cell is killed if it has fewer than 2 or more than 3 neighbours.
    part1 = ((Z == 1) & (N < 4) & (N > 1))
    # a new cell forms if a square has exactly three members
    part2 = ((Z == 0) & (N == 3))
    Z = (part1 | part2).astype(int)
    return Z

# We define the update function which updates the texture and legend text
# at every iteration.
def update(figure, parameter):
    """Update the figure at every iteration."""
    # We initialize the iteration to 0 at the beginning.
    if not hasattr(figure, 'iteration'):
        figure.iteration = 0
    # We iterate the matrix.
    mat[:,:,0] = iterate(mat[:,:,0])
    # We update the texture and the iteration text.
    figure.set_data(texture=mat, visual='image')
    figure.set_data(text="Iteration %d" % figure.iteration, visual='iteration')
    figure.iteration += 1

# We create a figure with constrained ratio and navigation.
figure(constrain_ratio=True, constrain_navigation=True,)

# We create the initial matrix with random values, and we only update the 
# red channel.
mat = zeros((size, size, 3))
mat[:,:,0] = random.rand(size,size) < .2

# We show the image.
imshow(mat, name='image')

# We show the iteration text at the top.
text(fontsize=18, name='iteration', text='Iteration',
    coordinates=(0., .95), is_static=True)

# We animate the figure, with the update function called every 0.05 seconds
# (i.e. 20 FPS).
animate(update, dt=.05)

show()

########NEW FILE########
__FILENAME__ = _run
"""Run all tutorials successively."""
from galry import run_all_scripts
run_all_scripts()

########NEW FILE########
