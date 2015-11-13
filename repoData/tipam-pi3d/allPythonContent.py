__FILENAME__ = CreateManyDisplays
#!/usr/bin/python

from __future__ import absolute_import, division, print_function, unicode_literals

import experiment

import pi3d
import sys
import time

from six.moves import xrange

DEFAULT_SLEEP = 0.0
DEFAULT_ITERATIONS = 5000

SLEEP = DEFAULT_SLEEP if len(sys.argv) < 2 else float(sys.argv[1])
ITERATIONS = DEFAULT_ITERATIONS if len(sys.argv) < 3 else float(sys.argv[2])

for i in xrange(ITERATIONS):
  d = pi3d.Display.create()
  d.destroy()
  print(i)
  if SLEEP > 0:
    time.sleep(SLEEP)

########NEW FILE########
__FILENAME__ = experiment
import os
import sys

from os.path import dirname

root = dirname(dirname(__file__))
sys.path.append(root)
os.chdir(root)

########NEW FILE########
__FILENAME__ = LeakTest
from collections import defaultdict
from gc import get_objects

""" This is just the skeleton parts of the memory leak testing routine
suggested by gnibbler  ref 1641280
search stackoverflow 'gnibbler memory leak'
in pi3d the while loop is the Display.loop_running() and print is a p3
type function with braces
"""
str_num = 0
before = defaultdict(int)
after = defaultdict(int)

# Display scene and rotate shape
while True:
  #
  # do something here to create memory leakage
  #
  str_num += 1
  if str_num == 17: # large nough number to give it a chance to 'bed in'
    for i in get_objects():
      before[type(i)] += 1
  if (str_num % 50) == 17: # same number as above
    print "--------------------"
    for i in after:
      after[i] = 0
    for i in get_objects():
      after[type(i)] += 1
    for i in after:
      if after[i] - before[i]:
        print "{} {}".format(i, after[i] - before[i])


########NEW FILE########
__FILENAME__ = RunMultipleMinimals
#!/usr/bin/python
from __future__ import absolute_import, division, print_function, unicode_literals

import subprocess, time

from six.moves import xrange

for i in xrange(500):
  p = subprocess.Popen(["python", "/home/pi/pi3d/demos/Minimal.py"],
          stdin=subprocess.PIPE, stderr=subprocess.PIPE)
  time.sleep(7.0)
  stdoutdata, stderrdata = p.communicate(chr(27))
  with open("/home/pi/pi3d/experiments/minimal_count.txt", "w") as myfile:
    myfile.write(str(i))



########NEW FILE########
__FILENAME__ = Buffer
from __future__ import absolute_import, division, print_function, unicode_literals

import ctypes, itertools
import numpy as np

from ctypes import c_float, c_int

from pi3d.constants import *
from pi3d.util import Log
from pi3d.util import Utility
from pi3d.util.Loadable import Loadable
from pi3d.util.Ctypes import c_floats, c_shorts

LOGGER = Log.logger(__name__)

class Buffer(Loadable):
  """Holds the vertex, normals, incices and tex_coords for each part of
  a Shape that needs to be rendered with a different material or texture
  Shape holds an array of Buffer objects.

  """
  def __init__(self, shape, pts, texcoords, faces, normals=None, smooth=True):
    """Generate a vertex buffer to hold data and indices. If no normals
    are provided then these are generated.

    Arguments:
      *shape*
        Shape object that this Buffer is a child of
      *pts*
        array of vertices tuples i.e. [(x0,y0,z0), (x1,y1,z1),...]
      *texcoords*
        array of texture (uv) coordinates tuples
        i.e. [(u0,v0), (u1,v1),...]
      *faces*
        array of indices (of pts array) defining triangles
        i.e. [(a0,b0,c0), (a1,b1,c1),...]

    Keyword arguments:
      *normals*
        array of vector component tuples defining normals at each
        vertex i.e. [(x0,y0,z0), (x1,y1,z1),...]
      *smooth*
        if calculating normals then average normals for all faces
        meeting at this vertex, otherwise just use first (for speed).

    """
    super(Buffer, self).__init__()

    # Uniform variables all in one array!
    self.unib = (c_float * 12)(0.0, 0.0, 0.0,
                              0.5, 0.5, 0.5,
                              1.0, 1.0, 0.0,
                              0.0, 0.0, 0.0)
    """ pass to shader array of vec3 uniform variables:

    ===== ============================ ==== ==
    vec3        description            python
    ----- ---------------------------- -------
    index                              from to
    ===== ============================ ==== ==
        0  ntile, shiny, blend           0   2
        1  material                      3   5
        2  umult, vmult, point_size      6   8
        3  u_off, v_off (only 2 used)    9  10
    ===== ============================ ==== ==
    """
    #self.shape = shape
    self.textures = []
    pts = np.array(pts, dtype=float)
    texcoords = np.array(texcoords, dtype=float)
    faces = np.array(faces)

    if normals == None: #i.e. normals will only be generated if explictly None
      LOGGER.debug('Calculating normals ...')

      normals = np.zeros(pts.shape, dtype=float) #empty array rights size

      fv = pts[faces] #expand faces with x,y,z values for each vertex
      #cross product of two edges of triangles
      fn = np.cross(fv[:][:][:,1] - fv[:][:][:,0], fv[:][:][:,2] - fv[:][:][:,0])
      fn = Utility.normalize_v3(fn)
      normals[faces[:,0]] += fn #add up all normal vectors for a vertex
      normals[faces[:,1]] += fn
      normals[faces[:,2]] += fn
      normals = Utility.normalize_v3(normals)
    else:
      normals = np.array(normals)
      
    # keep a copy for speeding up the collision testing of ElevationMap
    self.vertices = pts
    self.normals = normals
    self.tex_coords = texcoords
    self.indices = faces
    self.material = (0.5, 0.5, 0.5, 1.0)

    # Pack points,normals and texcoords into tuples and convert to ctype floats.
    n_verts = len(pts)
    if len(texcoords) != n_verts:
      if len(normals) != n_verts:
        self.N_BYTES = 12 # only use pts
        self.array_buffer = c_floats(pts.reshape(-1).tolist())
      else:
        self.N_BYTES = 24 # use pts and normals
        self.array_buffer = c_floats(np.concatenate((pts, normals),
                            axis=1).reshape(-1).tolist())
    else:
      self.N_BYTES = 32 # use all three NB doesn't check that normals are there
      self.array_buffer = c_floats(np.concatenate((pts, normals, texcoords),
                          axis=1).reshape(-1).tolist())

    self.ntris = len(faces)
    self.element_array_buffer = c_shorts(faces.reshape(-1))
    from pi3d.Display import Display
    self.disp = Display.INSTANCE # rely on there always being one!

  def __del__(self):
    #super(Buffer, self).__del__() #TODO supposed to always call super.__del__
    if not self.opengl_loaded:
      return True
    self.disp.vbufs_dict[str(self.vbuf)][1] = 1
    self.disp.ebufs_dict[str(self.ebuf)][1] = 1
    self.disp.tidy_needed = True

  def re_init(self, shape, pts, texcoords, faces, normals=None, smooth=True):
    """Only reset the opengl buffer variables: vertices, tex_coords, indices
    normals (which is generated if not supplied) **NB this method will
    go horribly wrong if you change the size of the arrays supplied in
    the argument as the opengles buffers are reused** Arguments are
    as per __init__()"""
    tmp_unib = (c_float * 12)(self.unib[0], self.unib[1], self.unib[2],
                              self.unib[3], self.unib[4], self.unib[5],
                              self.unib[6], self.unib[7], self.unib[8],
                              self.unib[9], self.unib[10], self.unib[11])
    self.__init__(shape, pts, texcoords, faces, normals, smooth)
    opengles.glBufferData(GL_ARRAY_BUFFER,
                          ctypes.sizeof(self.array_buffer),
                          ctypes.byref(self.array_buffer),
                          GL_STATIC_DRAW)
    opengles.glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                          ctypes.sizeof(self.element_array_buffer),
                          ctypes.byref(self.element_array_buffer),
                          GL_STATIC_DRAW)
    self.opengl_loaded = True
    self.unib = tmp_unib

  def _load_opengl(self):
    self.vbuf = c_int()
    opengles.glGenBuffers(1, ctypes.byref(self.vbuf))
    self.ebuf = c_int()
    opengles.glGenBuffers(1, ctypes.byref(self.ebuf))
    self.disp.vbufs_dict[str(self.vbuf)] = [self.vbuf, 0]
    self.disp.ebufs_dict[str(self.ebuf)] = [self.ebuf, 0]
    self._select()
    opengles.glBufferData(GL_ARRAY_BUFFER,
                          ctypes.sizeof(self.array_buffer),
                          ctypes.byref(self.array_buffer),
                          GL_STATIC_DRAW)
    opengles.glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                          ctypes.sizeof(self.element_array_buffer),
                          ctypes.byref(self.element_array_buffer),
                          GL_STATIC_DRAW)

  def _unload_opengl(self):
    opengles.glDeleteBuffers(1, ctypes.byref(self.vbuf))
    opengles.glDeleteBuffers(1, ctypes.byref(self.ebuf))

  def _select(self):
    """Makes our buffers active."""
    opengles.glBindBuffer(GL_ARRAY_BUFFER, self.vbuf)
    opengles.glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebuf)

  def set_draw_details(self, shader, textures, ntiles=0.0, shiny=0.0,
                       umult=1.0, vmult=1.0):
    """Can be used to set information needed for drawing as a one off
    rather than sending as arguments to draw().

    Arguments:
      *shader*
        Shader object
      *textures*
        array of Texture objects

    Keyword arguments:
      *ntiles*
        multiple for tiling normal map which can be less than or greater
        than 1.0. 0.0 disables the normal mapping, float
      *shiny*
        how strong to make the reflection 0.0 to 1.0, float
      *umult*
        multiplier for tiling the texture in the u direction
      *vmult*
        multiplier for tiling the texture in the v direction
    """
    self.shader = shader
    self.textures = textures # array of Textures
    self.unib[0] = ntiles
    self.unib[1] = shiny
    self.unib[6] = umult
    self.unib[7] = vmult

  def set_material(self, mtrl):
    self.unib[3:6] = mtrl[0:3]

  def set_textures(self, textures):
    self.textures = textures

  def set_offset(self, offset=(0.0, 0.0)):
    self.unib[9:11] = offset

  def draw(self, shape=None, shader=None, textures=None, ntl=None, shny=None, fullset=True):
    """Draw this Buffer, called by the parent Shape.draw()

    Keyword arguments:
      *shape*
        Shape object this Buffer belongs to, has to be passed at draw to avoid
        circular reference
      *shader*
        Shader object
      *textures*
        array of Texture objects
      *ntl*
        multiple for tiling normal map which can be less than or greater
        than 1.0. 0.0 disables the normal mapping, float
      *shiny*
        how strong to make the reflection 0.0 to 1.0, float
    """
    self.load_opengl()

    shader = shader or self.shader
    textures = textures or self.textures
    if ntl:
      self.unib[0] = ntl
    if shny:
      self.unib[1] = shny
    self._select()

    opengles.glVertexAttribPointer(shader.attr_vertex, 3, GL_FLOAT, 0, self.N_BYTES, 0)
    opengles.glEnableVertexAttribArray(shader.attr_vertex)
    if self.N_BYTES > 12:
      opengles.glVertexAttribPointer(shader.attr_normal, 3, GL_FLOAT, 0, self.N_BYTES, 12)
      opengles.glEnableVertexAttribArray(shader.attr_normal)
      if self.N_BYTES > 24:
        opengles.glVertexAttribPointer(shader.attr_texcoord, 2, GL_FLOAT, 0, self.N_BYTES, 24)
        opengles.glEnableVertexAttribArray(shader.attr_texcoord)

    opengles.glDisable(GL_BLEND)

    self.unib[2] = 0.6
    for t, texture in enumerate(textures):
      if (self.disp.last_textures[t] != texture or
            self.disp.last_shader != shader): # very slight speed increase for sprites
        opengles.glActiveTexture(GL_TEXTURE0 + t)
        assert texture.tex(), 'There was an empty texture in your Buffer.'
        opengles.glBindTexture(GL_TEXTURE_2D, texture.tex())
        opengles.glUniform1i(shader.unif_tex[t], t)
        self.disp.last_textures[t] = texture

      if texture.blend or shape.unif[17] < 1.0 or shape.unif[16] < 1.0:
        opengles.glEnable(GL_BLEND)
        # i.e. if any of the textures set to blend then all will for this shader.
        self.unib[2] = 0.05

    self.disp.last_shader = shader

    opengles.glUniform3fv(shader.unif_unib, 4, ctypes.byref(self.unib))

    if self.unib[8] == 0:
      opengles.glDrawElements(GL_TRIANGLES, self.ntris * 3, GL_UNSIGNED_SHORT, 0)
    else:
      opengles.glDrawElements(GL_POINTS, self.ntris * 3, GL_UNSIGNED_SHORT, 0)


########NEW FILE########
__FILENAME__ = Camera
from __future__ import absolute_import, division, print_function, unicode_literals

import ctypes

from numpy import array, dot, copy, tan, cos, sin, radians, degrees, arctan2, sqrt

from pi3d.constants import *
from pi3d.util.Utility import vec_normal, vec_cross, vec_sub, vec_dot
from pi3d.util.DefaultInstance import DefaultInstance

class Camera(DefaultInstance):
  """required object for creating and drawing Shape objects. Default instance
  created if none specified in script prior to creating a Shape
  """
  def __init__(self, at=(0, 0, 0), eye=(0, 0, -0.1), lens=None,
              is_3d=True, scale=1.0):
    """Set up view matrix to look from eye to at including perspective

    Arguments:
      *at*
        tuple (x,y,z) location to look at
      *eye*
        tuple (x,y,z) location to look from
      *lens*
        tuple (near plane dist, far plane dist, **VERTICAL** field of view in degrees,
        display aspect ratio w/h)
      *is_3d*
        determines whether the camera uses a perspective or orthographic
        projection matrix
      *scale*
        number of pixels per unit of size for orthographic camera or divisor
        for fov if perspective
    """
    super(Camera, self).__init__()

    self.at = at
    self.start_eye = eye # for reset with different lens settings
    self.eye = [eye[0], eye[1], eye[2]]
    if lens == None:
      from pi3d.Display import Display
      lens = [Display.INSTANCE.near, Display.INSTANCE.far, Display.INSTANCE.fov,
                  Display.INSTANCE.width / float(Display.INSTANCE.height)]
    self.lens = lens
    self.view = _LookAtMatrix(at, eye, [0, 1, 0])
    if is_3d:
      self.projection = _ProjectionMatrix(lens[0], lens[1], lens[2] / scale, lens[3])
    else:
      self.projection = _OrthographicMatrix(scale=scale)
    self.model_view = dot(self.view, self.projection)
    # Apply transform/rotation first, then shift into perspective space.
    self.mtrx = array(self.model_view, copy=True)
    # self.L_reflect = _LookAtMatrix(at,eye,[0,1,0],reflect=True)
    self.rtn = [0.0, 0.0, 0.0]

    self.was_moved = True

  @staticmethod
  def _default_instance():
    from pi3d.Display import Display

    return Camera((0, 0, 0), (0, 0, -0.1),
                  [Display.INSTANCE.near, Display.INSTANCE.far, Display.INSTANCE.fov,
                  Display.INSTANCE.width / float(Display.INSTANCE.height)])

  def reset(self, lens=None, is_3d=True, scale=1.0):
    """Has to be called each loop if the camera position or rotation changes"""
    if lens != None:
      view = _LookAtMatrix(self.at, self.start_eye, [0, 1, 0])
      projection = _ProjectionMatrix(lens[0], lens[1], lens[2] / scale, lens[3])
      self.model_view = dot(view, projection)
    elif not is_3d:
      view = _LookAtMatrix(self.at, self.start_eye, [0, 1, 0])
      projection = _OrthographicMatrix(scale=scale)
      self.model_view = dot(view, projection)
    # TODO some way of resetting to original matrix
    self.mtrx = copy(self.model_view)
    self.rtn = [0.0, 0.0, 0.0]
    self.was_moved = True

  def point_at(self, target=[0.0, 0.0, 10000.0]):
    """ point the camera at a point also return the tilt and rotation values

    Keyword argument:
      *target*
        Location as [x,y,z] array to point at, defaults to a high +ve z value as
        a kind of compass!
    """
    if target[0] == self.eye[0] and target[1] == self.eye[1] and target[2] == self.eye[2]:
      return
    dx, dy, dz = target[0] - self.eye[0], target[1] - self.eye[1], target[2] - self.eye[2]
    rot = -degrees(arctan2(dx, dz))
    horiz = sqrt(dot([dx,dz], [dx, dz]))
    tilt = degrees(arctan2(dy, horiz))
    self.rotate(tilt, rot, 0)
    return tilt, rot

  def position(self, pt):
    """position camera

    Arguments:
      *pt*
        tuple (x, y, z) floats
    """
    self.mtrx = dot([[1, 0, 0, 0],
                     [0, 1, 0, 0],
                     [0, 0, 1, 0],
                     [-pt[0], -pt[1], -pt[2], 1]],
                    self.mtrx)
    self.eye = [pt[0], pt[1], pt[2]]
    self.was_moved = True

  def rotateZ(self, angle):
    """Rotate camera z axis

    Arguments:
      *angle*
        in degrees
    """
    if angle:
      c = cos(radians(angle))
      s = sin(radians(angle))
      self.mtrx = dot([[c, s, 0, 0],
                       [-s, c, 0, 0],
                       [0, 0, 1, 0],
                       [0, 0, 0, 1]],
                      self.mtrx)
      self.rtn[2] = angle
      self.was_moved = True

  def rotateY(self, angle):
    """Rotate camera y axis

    Arguments:
      *angle*
        in degrees
    """
    if angle:
      c = cos(radians(angle))
      s = sin(radians(angle))
      self.mtrx = dot([[c, 0, -s, 0],
                       [0, 1, 0, 0],
                       [s, 0, c, 0],
                       [0, 0, 0, 1]],
                      self.mtrx)
      self.rtn[1] = angle
      self.was_moved = True

  def rotateX(self, angle):
    """Rotate camera x axis

    Arguments:
      *angle*
        in degrees
    """
    if angle:
      c = cos(radians(angle))
      s = sin(radians(angle))
      self.mtrx = dot([[1, 0, 0, 0],
                       [0, c, s, 0],
                       [0, -s, c, 0],
                       [0, 0, 0, 1]], self.mtrx)
      self.rtn[0] = angle
      self.was_moved = True

  def rotate(self, rx, ry, rz):
    """Rotate camera

    Arguments:
      *rx*
        x rotation in degrees
      *ry*
        y rotation in degrees
      *rz*
        z rotation in degrees
    """
    self.rotateZ(rz)
    self.rotateX(rx)
    self.rotateY(ry)

def _LookAtMatrix(at, eye, up=[0, 1, 0], reflect=False):
  """Define a matrix looking at.

  Arguments:
    *at*
      tuple (x,y,z) of point camera pointed at, floats
    *eye*
      matrix [x,y,z] position of camera, floats

  Keyword arguments:
    *up*
      array vector of up direction
    *eflect*
      boolean if matrix is reflected
  """
  # If reflect, then reflect in plane -20.0 (water depth)
  if reflect:
    depth = -20.0 # Shallower to avoid edge effects
    eye = [eye[0], -eye[1], eye[2]]
    at = [at[0], -at[1], at[2]]
  zaxis = vec_normal(vec_sub(at, eye))
  xaxis = vec_normal(vec_cross(up, zaxis))
  yaxis = vec_cross(zaxis, xaxis)
  xaxis.append(-vec_dot(xaxis, eye))
  yaxis.append(-vec_dot(yaxis, eye))
  zaxis.append(-vec_dot(zaxis, eye))
  z = [0, 0, 0, 1.0]
  return array([[xaxis[a], yaxis[a], zaxis[a], z[a]] for a in range(4)],
               dtype=float)

def _ProjectionMatrix(near, far, fov, aspectRatio):
  """Set up perspective projection matrix

  Keyword arguments:
    *near*
      distance to near plane, float
    *far*
      distance to far plane, float
    *fov*
      **VERTICAL** field of view in degrees, float
    *aspectRatio*
      aspect ratio = width / height of the scene, float
  """
  # Matrices are considered to be M[row][col]
  # Use DirectX convention, so need to do rowvec*Matrix to transform
  size = 1 / tan(radians(fov)/2.0)
  M = [[0] * 4 for i in range(4)]
  M[0][0] = size/aspectRatio
  M[1][1] = size  #negative value reflects scene on the Y axis
  M[2][2] = (far + near) / (far - near)
  M[2][3] = 1
  M[3][2] = -(2 * far * near)/(far - near)
  return array(M, dtype=float)

def _OrthographicMatrix(scale=1.0):
  """Set up orthographic projection matrix

  Keyword argument:
    *scale*
      number of pixels per unit of size

  """
  from pi3d.Display import Display
  M = [[0] * 4 for i in range(4)]
  M[0][0] = 2.0 * scale / Display.INSTANCE.width
  M[1][1] = 2.0 * scale / Display.INSTANCE.height
  #M[2][2] = 2.0 / Display.INSTANCE.width
  M[2][2] = 2.0 / 10000.0
  M[3][2] = -1
  M[3][3] = 1
  return array(M, dtype=float)


########NEW FILE########
__FILENAME__ = egl
"""
This module contains integer constants from a C header file named something
like egl.h.
"""

EGL_SUCCESS = 0x3000
EGL_NOT_INITIALIZED = 0x3001
EGL_BAD_ACCESS = 0x3002
EGL_BAD_ALLOC = 0x3003
EGL_BAD_ATTRIBUTE = 0x3004
EGL_BAD_CONFIG = 0x3005
EGL_BAD_CONTEXT = 0x3006
EGL_BAD_CURRENT_SURFACE = 0x3007
EGL_BAD_DISPLAY = 0x3008
EGL_BAD_MATCH = 0x3009
EGL_BAD_NATIVE_PIXMAP = 0x300A
EGL_BAD_NATIVE_WINDOW = 0x300B
EGL_BAD_PARAMETER = 0x300C
EGL_BAD_SURFACE = 0x300D
EGL_CONTEXT_LOST = 0x300E
EGL_BUFFER_SIZE = 0x3020
EGL_ALPHA_SIZE = 0x3021
EGL_BLUE_SIZE = 0x3022
EGL_GREEN_SIZE = 0x3023
EGL_RED_SIZE = 0x3024
EGL_DEPTH_SIZE = 0x3025
EGL_STENCIL_SIZE = 0x3026
EGL_CONFIG_CAVEAT = 0x3027
EGL_CONFIG_ID = 0x3028
EGL_LEVEL = 0x3029
EGL_MAX_PBUFFER_HEIGHT = 0x302A
EGL_MAX_PBUFFER_PIXELS = 0x302B
EGL_MAX_PBUFFER_WIDTH = 0x302C
EGL_NATIVE_RENDERABLE = 0x302D
EGL_NATIVE_VISUAL_ID = 0x302E
EGL_NATIVE_VISUAL_TYPE = 0x302F
EGL_SAMPLES = 0x3031
EGL_SAMPLE_BUFFERS = 0x3032
EGL_SURFACE_TYPE = 0x3033
EGL_TRANSPARENT_TYPE = 0x3034
EGL_TRANSPARENT_BLUE_VALUE = 0x3035
EGL_TRANSPARENT_GREEN_VALUE = 0x3036
EGL_TRANSPARENT_RED_VALUE = 0x3037
EGL_NONE = 0x3038
EGL_BIND_TO_TEXTURE_RGB = 0x3039
EGL_BIND_TO_TEXTURE_RGBA = 0x303A
EGL_MIN_SWAP_INTERVAL = 0x303B
EGL_MAX_SWAP_INTERVAL = 0x303C
EGL_LUMINANCE_SIZE = 0x303D
EGL_ALPHA_MASK_SIZE = 0x303E
EGL_COLOR_BUFFER_TYPE = 0x303F
EGL_RENDERABLE_TYPE = 0x3040
EGL_MATCH_NATIVE_PIXMAP = 0x3041
EGL_CONFORMANT = 0x3042
EGL_SLOW_CONFIG = 0x3050
EGL_NON_CONFORMANT_CONFIG = 0x3051
EGL_TRANSPARENT_RGB = 0x3052
EGL_RGB_BUFFER = 0x308E
EGL_LUMINANCE_BUFFER = 0x308F
EGL_NO_TEXTURE = 0x305C
EGL_TEXTURE_RGB = 0x305D
EGL_TEXTURE_RGBA = 0x305E
EGL_TEXTURE_2D = 0x305F
EGL_PBUFFER_BIT = 0x0001
EGL_PIXMAP_BIT = 0x0002
EGL_WINDOW_BIT = 0x0004
EGL_VG_COLORSPACE_LINEAR_BIT = 0x0020
EGL_VG_ALPHA_FORMAT_PRE_BIT = 0x0040
EGL_MULTISAMPLE_RESOLVE_BOX_BIT = 0x0200
EGL_SWAP_BEHAVIOR_PRESERVED_BIT = 0x0400
EGL_OPENGL_ES_BIT = 0x0001
EGL_OPENVG_BIT = 0x0002
EGL_OPENGL_ES2_BIT = 0x0004
EGL_OPENGL_BIT = 0x0008
EGL_VENDOR = 0x3053
EGL_VERSION = 0x3054
EGL_EXTENSIONS = 0x3055
EGL_CLIENT_APIS = 0x308D
EGL_HEIGHT = 0x3056
EGL_WIDTH = 0x3057
EGL_LARGEST_PBUFFER = 0x3058
EGL_TEXTURE_FORMAT = 0x3080
EGL_TEXTURE_TARGET = 0x3081
EGL_MIPMAP_TEXTURE = 0x3082
EGL_MIPMAP_LEVEL = 0x3083
EGL_RENDER_BUFFER = 0x3086
EGL_VG_COLORSPACE = 0x3087
EGL_VG_ALPHA_FORMAT = 0x3088
EGL_HORIZONTAL_RESOLUTION = 0x3090
EGL_VERTICAL_RESOLUTION = 0x3091
EGL_PIXEL_ASPECT_RATIO = 0x3092
EGL_SWAP_BEHAVIOR = 0x3093
EGL_MULTISAMPLE_RESOLVE = 0x3099
EGL_BACK_BUFFER = 0x3084
EGL_SINGLE_BUFFER = 0x3085
EGL_VG_COLORSPACE_sRGB = 0x3089
EGL_VG_COLORSPACE_LINEAR = 0x308A
EGL_VG_ALPHA_FORMAT_NONPRE = 0x308B
EGL_VG_ALPHA_FORMAT_PRE = 0x308C
EGL_BUFFER_PRESERVED = 0x3094
EGL_BUFFER_DESTROYED = 0x3095
EGL_OPENVG_IMAGE = 0x3096
EGL_CONTEXT_CLIENT_TYPE = 0x3097
EGL_CONTEXT_CLIENT_VERSION = 0x3098
EGL_MULTISAMPLE_RESOLVE_DEFAULT = 0x309A
EGL_MULTISAMPLE_RESOLVE_BOX = 0x309B
EGL_OPENGL_ES_API = 0x30A0
EGL_OPENVG_API = 0x30A1
EGL_OPENGL_API = 0x30A2
EGL_DRAW = 0x3059
EGL_READ = 0x305A
EGL_CORE_NATIVE_ENGINE = 0x305B

########NEW FILE########
__FILENAME__ = gl
"""
This module contains integer constants from a C header file named something
like gl.h.
"""

GL_DEPTH_BUFFER_BIT = 0x00000100
GL_STENCIL_BUFFER_BIT = 0x00000400
GL_COLOR_BUFFER_BIT = 0x00004000
GL_POINTS = 0x0000
GL_LINES = 0x0001
GL_LINE_LOOP = 0x0002
GL_LINE_STRIP = 0x0003
GL_TRIANGLES = 0x0004
GL_TRIANGLE_STRIP = 0x0005
GL_TRIANGLE_FAN = 0x0006
GL_NEVER = 0x0200
GL_LESS = 0x0201
GL_EQUAL = 0x0202
GL_LEQUAL = 0x0203
GL_GREATER = 0x0204
GL_NOTEQUAL = 0x0205
GL_GEQUAL = 0x0206
GL_ALWAYS = 0x0207
GL_SRC_COLOR = 0x0300
GL_ONE_MINUS_SRC_COLOR = 0x0301
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_DST_ALPHA = 0x0304
GL_ONE_MINUS_DST_ALPHA = 0x0305
GL_DST_COLOR = 0x0306
GL_ONE_MINUS_DST_COLOR = 0x0307
GL_SRC_ALPHA_SATURATE = 0x0308
GL_CLIP_PLANE0 = 0x3000
GL_CLIP_PLANE1 = 0x3001
GL_CLIP_PLANE2 = 0x3002
GL_CLIP_PLANE3 = 0x3003
GL_CLIP_PLANE4 = 0x3004
GL_CLIP_PLANE5 = 0x3005
GL_FRONT = 0x0404
GL_BACK = 0x0405
GL_FRONT_AND_BACK = 0x0408
GL_FOG = 0x0B60
GL_LIGHTING = 0x0B50
GL_TEXTURE_2D = 0x0DE1
GL_CULL_FACE = 0x0B44
GL_ALPHA_TEST = 0x0BC0
GL_BLEND = 0x0BE2
GL_COLOR_LOGIC_OP = 0x0BF2
GL_DITHER = 0x0BD0
GL_STENCIL_TEST = 0x0B90
GL_DEPTH_TEST = 0x0B71
GL_POINT_SMOOTH = 0x0B10
GL_LINE_SMOOTH = 0x0B20
GL_SCISSOR_TEST = 0x0C11
GL_COLOR_MATERIAL = 0x0B57
GL_NORMALIZE = 0x0BA1
GL_RESCALE_NORMAL = 0x803A
GL_POLYGON_OFFSET_FILL = 0x8037
GL_VERTEX_ARRAY = 0x8074
GL_NORMAL_ARRAY = 0x8075
GL_COLOR_ARRAY = 0x8076
GL_TEXTURE_COORD_ARRAY = 0x8078
GL_MULTISAMPLE = 0x809D
GL_SAMPLE_ALPHA_TO_COVERAGE = 0x809E
GL_SAMPLE_ALPHA_TO_ONE = 0x809F
GL_SAMPLE_COVERAGE = 0x80A0
GL_NO_ERROR = 0
GL_INVALID_ENUM = 0x0500
GL_INVALID_VALUE = 0x0501
GL_INVALID_OPERATION = 0x0502
GL_STACK_OVERFLOW = 0x0503
GL_STACK_UNDERFLOW = 0x0504
GL_OUT_OF_MEMORY = 0x0505
GL_INVALID_FRAMEBUFFER_OPERATION = 0x0506
GL_EXP = 0x0800
GL_EXP2 = 0x0801
GL_FOG_DENSITY = 0x0B62
GL_FOG_START = 0x0B63
GL_FOG_END = 0x0B64
GL_FOG_MODE = 0x0B65
GL_FOG_COLOR = 0x0B66
GL_CW = 0x0900
GL_CCW = 0x0901
GL_CURRENT_COLOR = 0x0B00
GL_CURRENT_NORMAL = 0x0B02
GL_CURRENT_TEXTURE_COORDS = 0x0B03
GL_POINT_SIZE = 0x0B11
GL_POINT_SIZE_MIN = 0x8126
GL_POINT_SIZE_MAX = 0x8127
GL_POINT_FADE_THRESHOLD_SIZE = 0x8128
GL_POINT_DISTANCE_ATTENUATION = 0x8129
GL_SMOOTH_POINT_SIZE_RANGE = 0x0B12
GL_LINE_WIDTH = 0x0B21
GL_SMOOTH_LINE_WIDTH_RANGE = 0x0B22
GL_ALIASED_POINT_SIZE_RANGE = 0x846D
GL_ALIASED_LINE_WIDTH_RANGE = 0x846E
GL_CULL_FACE_MODE = 0x0B45
GL_FRONT_FACE = 0x0B46
GL_SHADE_MODEL = 0x0B54
GL_DEPTH_RANGE = 0x0B70
GL_DEPTH_WRITEMASK = 0x0B72
GL_DEPTH_CLEAR_VALUE = 0x0B73
GL_DEPTH_FUNC = 0x0B74
GL_STENCIL_CLEAR_VALUE = 0x0B91
GL_STENCIL_FUNC = 0x0B92
GL_STENCIL_VALUE_MASK = 0x0B93
GL_STENCIL_FAIL = 0x0B94
GL_STENCIL_PASS_DEPTH_FAIL = 0x0B95
GL_STENCIL_PASS_DEPTH_PASS = 0x0B96
GL_STENCIL_REF = 0x0B97
GL_STENCIL_WRITEMASK = 0x0B98
GL_MATRIX_MODE = 0x0BA0
GL_VIEWPORT = 0x0BA2
GL_MODELVIEW_STACK_DEPTH = 0x0BA3
GL_PROJECTION_STACK_DEPTH = 0x0BA4
GL_TEXTURE_STACK_DEPTH = 0x0BA5
GL_MODELVIEW_MATRIX = 0x0BA6
GL_PROJECTION_MATRIX = 0x0BA7
GL_TEXTURE_MATRIX = 0x0BA8
GL_ALPHA_TEST_FUNC = 0x0BC1
GL_ALPHA_TEST_REF = 0x0BC2
GL_BLEND_DST = 0x0BE0
GL_BLEND_SRC = 0x0BE1
GL_LOGIC_OP_MODE = 0x0BF0
GL_SCISSOR_BOX = 0x0C10
GL_SCISSOR_TEST = 0x0C11
GL_COLOR_CLEAR_VALUE = 0x0C22
GL_COLOR_WRITEMASK = 0x0C23
GL_UNPACK_ALIGNMENT = 0x0CF5
GL_PACK_ALIGNMENT = 0x0D05
GL_MAX_LIGHTS = 0x0D31
GL_MAX_CLIP_PLANES = 0x0D32
GL_MAX_TEXTURE_SIZE = 0x0D33
GL_MAX_MODELVIEW_STACK_DEPTH = 0x0D36
GL_MAX_PROJECTION_STACK_DEPTH = 0x0D38
GL_MAX_TEXTURE_STACK_DEPTH = 0x0D39
GL_MAX_VIEWPORT_DIMS = 0x0D3A
GL_MAX_TEXTURE_UNITS = 0x84E2
GL_SUBPIXEL_BITS = 0x0D50
GL_RED_BITS = 0x0D52
GL_GREEN_BITS = 0x0D53
GL_BLUE_BITS = 0x0D54
GL_ALPHA_BITS = 0x0D55
GL_DEPTH_BITS = 0x0D56
GL_STENCIL_BITS = 0x0D57
GL_POLYGON_OFFSET_UNITS = 0x2A00
GL_POLYGON_OFFSET_FILL = 0x8037
GL_POLYGON_OFFSET_FACTOR = 0x8038
GL_TEXTURE_BINDING_2D = 0x8069
GL_VERTEX_ARRAY_SIZE = 0x807A
GL_VERTEX_ARRAY_TYPE = 0x807B
GL_VERTEX_ARRAY_STRIDE = 0x807C
GL_NORMAL_ARRAY_TYPE = 0x807E
GL_NORMAL_ARRAY_STRIDE = 0x807F
GL_COLOR_ARRAY_SIZE = 0x8081
GL_COLOR_ARRAY_TYPE = 0x8082
GL_COLOR_ARRAY_STRIDE = 0x8083
GL_TEXTURE_COORD_ARRAY_SIZE = 0x8088
GL_TEXTURE_COORD_ARRAY_TYPE = 0x8089
GL_TEXTURE_COORD_ARRAY_STRIDE = 0x808A
GL_VERTEX_ARRAY_POINTER = 0x808E
GL_NORMAL_ARRAY_POINTER = 0x808F
GL_COLOR_ARRAY_POINTER = 0x8090
GL_TEXTURE_COORD_ARRAY_POINTER = 0x8092
GL_SAMPLE_BUFFERS = 0x80A8
GL_SAMPLES = 0x80A9
GL_SAMPLE_COVERAGE_VALUE = 0x80AA
GL_SAMPLE_COVERAGE_INVERT = 0x80AB
GL_NUM_COMPRESSED_TEXTURE_FORMATS = 0x86A2
GL_COMPRESSED_TEXTURE_FORMATS = 0x86A3
GL_DONT_CARE = 0x1100
GL_FASTEST = 0x1101
GL_NICEST = 0x1102
GL_PERSPECTIVE_CORRECTION_HINT = 0x0C50
GL_POINT_SMOOTH_HINT = 0x0C51
GL_LINE_SMOOTH_HINT = 0x0C52
GL_FOG_HINT = 0x0C54
GL_GENERATE_MIPMAP_HINT = 0x8192
GL_LIGHT_MODEL_AMBIENT = 0x0B53
GL_LIGHT_MODEL_TWO_SIDE = 0x0B52
GL_AMBIENT = 0x1200
GL_DIFFUSE = 0x1201
GL_SPECULAR = 0x1202
GL_POSITION = 0x1203
GL_SPOT_DIRECTION = 0x1204
GL_SPOT_EXPONENT = 0x1205
GL_SPOT_CUTOFF = 0x1206
GL_CONSTANT_ATTENUATION = 0x1207
GL_LINEAR_ATTENUATION = 0x1208
GL_QUADRATIC_ATTENUATION = 0x1209
GL_BYTE = 0x1400
GL_UNSIGNED_BYTE = 0x1401
GL_SHORT = 0x1402
GL_UNSIGNED_SHORT = 0x1403
GL_FLOAT = 0x1406
GL_FIXED = 0x140C
GL_CLEAR = 0x1500
GL_AND = 0x1501
GL_AND_REVERSE = 0x1502
GL_COPY = 0x1503
GL_AND_INVERTED = 0x1504
GL_NOOP = 0x1505
GL_XOR = 0x1506
GL_OR = 0x1507
GL_NOR = 0x1508
GL_EQUIV = 0x1509
GL_INVERT = 0x150A
GL_OR_REVERSE = 0x150B
GL_COPY_INVERTED = 0x150C
GL_OR_INVERTED = 0x150D
GL_NAND = 0x150E
GL_SET = 0x150F
GL_EMISSION = 0x1600
GL_SHININESS = 0x1601
GL_AMBIENT_AND_DIFFUSE = 0x1602
GL_MODELVIEW = 0x1700
GL_PROJECTION = 0x1701
GL_TEXTURE = 0x1702
GL_ALPHA = 0x1906
GL_RGB = 0x1907
GL_RGBA = 0x1908
GL_LUMINANCE = 0x1909
GL_LUMINANCE_ALPHA = 0x190A
GL_UNPACK_ALIGNMENT = 0x0CF5
GL_PACK_ALIGNMENT = 0x0D05
GL_UNSIGNED_SHORT_4_4_4_4 = 0x8033
GL_UNSIGNED_SHORT_5_5_5_1 = 0x8034
GL_UNSIGNED_SHORT_5_6_5 = 0x8363
GL_FLAT = 0x1D00
GL_SMOOTH = 0x1D01
GL_KEEP = 0x1E00
GL_REPLACE = 0x1E01
GL_INCR = 0x1E02
GL_DECR = 0x1E03
GL_VENDOR = 0x1F00
GL_RENDERER = 0x1F01
GL_VERSION = 0x1F02
GL_EXTENSIONS = 0x1F03
GL_MODULATE = 0x2100
GL_DECAL = 0x2101
GL_ADD = 0x0104
GL_TEXTURE_ENV_MODE = 0x2200
GL_TEXTURE_ENV_COLOR = 0x2201
GL_TEXTURE_ENV = 0x2300
GL_NEAREST = 0x2600
GL_LINEAR = 0x2601
GL_NEAREST_MIPMAP_NEAREST = 0x2700
GL_LINEAR_MIPMAP_NEAREST = 0x2701
GL_NEAREST_MIPMAP_LINEAR = 0x2702
GL_LINEAR_MIPMAP_LINEAR = 0x2703
GL_TEXTURE_MAG_FILTER = 0x2800
GL_TEXTURE_MIN_FILTER = 0x2801
GL_TEXTURE_WRAP_S = 0x2802
GL_TEXTURE_WRAP_T = 0x2803
GL_GENERATE_MIPMAP = 0x8191
GL_TEXTURE0 = 0x84C0
GL_TEXTURE1 = 0x84C1
GL_TEXTURE2 = 0x84C2
GL_TEXTURE3 = 0x84C3
GL_TEXTURE4 = 0x84C4
GL_TEXTURE5 = 0x84C5
GL_TEXTURE6 = 0x84C6
GL_TEXTURE7 = 0x84C7
GL_TEXTURE8 = 0x84C8
GL_TEXTURE9 = 0x84C9
GL_TEXTURE10 = 0x84CA
GL_TEXTURE11 = 0x84CB
GL_TEXTURE12 = 0x84CC
GL_TEXTURE13 = 0x84CD
GL_TEXTURE14 = 0x84CE
GL_TEXTURE15 = 0x84CF
GL_TEXTURE16 = 0x84D0
GL_TEXTURE17 = 0x84D1
GL_TEXTURE18 = 0x84D2
GL_TEXTURE19 = 0x84D3
GL_TEXTURE20 = 0x84D4
GL_TEXTURE21 = 0x84D5
GL_TEXTURE22 = 0x84D6
GL_TEXTURE23 = 0x84D7
GL_TEXTURE24 = 0x84D8
GL_TEXTURE25 = 0x84D9
GL_TEXTURE26 = 0x84DA
GL_TEXTURE27 = 0x84DB
GL_TEXTURE28 = 0x84DC
GL_TEXTURE29 = 0x84DD
GL_TEXTURE30 = 0x84DE
GL_TEXTURE31 = 0x84DF
GL_ACTIVE_TEXTURE = 0x84E0
GL_CLIENT_ACTIVE_TEXTURE = 0x84E1
GL_REPEAT = 0x2901
GL_CLAMP_TO_EDGE = 0x812F
GL_LIGHT0 = 0x4000
GL_LIGHT1 = 0x4001
GL_LIGHT2 = 0x4002
GL_LIGHT3 = 0x4003
GL_LIGHT4 = 0x4004
GL_LIGHT5 = 0x4005
GL_LIGHT6 = 0x4006
GL_LIGHT7 = 0x4007
GL_ARRAY_BUFFER = 0x8892
GL_ELEMENT_ARRAY_BUFFER = 0x8893
GL_ARRAY_BUFFER_BINDING = 0x8894
GL_ELEMENT_ARRAY_BUFFER_BINDING = 0x8895
GL_VERTEX_ARRAY_BUFFER_BINDING = 0x8896
GL_NORMAL_ARRAY_BUFFER_BINDING = 0x8897
GL_COLOR_ARRAY_BUFFER_BINDING = 0x8898
GL_TEXTURE_COORD_ARRAY_BUFFER_BINDING = 0x889A
GL_STATIC_DRAW = 0x88E4
GL_DYNAMIC_DRAW = 0x88E8
GL_BUFFER_SIZE = 0x8764
GL_BUFFER_USAGE = 0x8765
GL_SUBTRACT = 0x84E7
GL_COMBINE = 0x8570
GL_COMBINE_RGB = 0x8571
GL_COMBINE_ALPHA = 0x8572
GL_RGB_SCALE = 0x8573
GL_ADD_SIGNED = 0x8574
GL_INTERPOLATE = 0x8575
GL_CONSTANT = 0x8576
GL_PRIMARY_COLOR = 0x8577
GL_PREVIOUS = 0x8578
GL_OPERAND0_RGB = 0x8590
GL_OPERAND1_RGB = 0x8591
GL_OPERAND2_RGB = 0x8592
GL_OPERAND0_ALPHA = 0x8598
GL_OPERAND1_ALPHA = 0x8599
GL_OPERAND2_ALPHA = 0x859A
GL_ALPHA_SCALE = 0x0D1C
GL_SRC0_RGB = 0x8580
GL_SRC1_RGB = 0x8581
GL_SRC2_RGB = 0x8582
GL_SRC0_ALPHA = 0x8588
GL_SRC1_ALPHA = 0x8589
GL_SRC2_ALPHA = 0x858A
GL_DOT3_RGB = 0x86AE
GL_DOT3_RGBA = 0x86AF
GL_IMPLEMENTATION_COLOR_READ_TYPE_OES = 0x8B9A
GL_IMPLEMENTATION_COLOR_READ_FORMAT_OES = 0x8B9B
GL_PALETTE4_RGB8_OES = 0x8B90
GL_PALETTE4_RGBA8_OES = 0x8B91
GL_PALETTE4_R5_G6_B5_OES = 0x8B92
GL_PALETTE4_RGBA4_OES = 0x8B93
GL_PALETTE4_RGB5_A1_OES = 0x8B94
GL_PALETTE8_RGB8_OES = 0x8B95
GL_PALETTE8_RGBA8_OES = 0x8B96
GL_PALETTE8_R5_G6_B5_OES = 0x8B97
GL_PALETTE8_RGBA4_OES = 0x8B98
GL_PALETTE8_RGB5_A1_OES = 0x8B99
GL_POINT_SIZE_ARRAY_OES = 0x8B9C
GL_POINT_SIZE_ARRAY_TYPE_OES = 0x898A
GL_POINT_SIZE_ARRAY_STRIDE_OES = 0x898B
GL_POINT_SIZE_ARRAY_POINTER_OES = 0x898C
GL_POINT_SIZE_ARRAY_BUFFER_BINDING_OES = 0x8B9F
GL_POINT_SPRITE_OES = 0x8861
GL_COORD_REPLACE_OES = 0x8862

########NEW FILE########
__FILENAME__ = gl2
"""
This module contains integer constants from a C header file named something
like gl2.h.
"""

GL_DEPTH_BUFFER_BIT = 0x00000100
GL_STENCIL_BUFFER_BIT = 0x00000400
GL_COLOR_BUFFER_BIT = 0x00004000
GL_POINTS = 0x0000
GL_LINES = 0x0001
GL_LINE_LOOP = 0x0002
GL_LINE_STRIP = 0x0003
GL_TRIANGLES = 0x0004
GL_TRIANGLE_STRIP = 0x0005
GL_TRIANGLE_FAN = 0x0006
GL_SRC_COLOR = 0x0300
GL_ONE_MINUS_SRC_COLOR = 0x0301
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_DST_ALPHA = 0x0304
GL_ONE_MINUS_DST_ALPHA = 0x0305
GL_DST_COLOR = 0x0306
GL_ONE_MINUS_DST_COLOR = 0x0307
GL_SRC_ALPHA_SATURATE = 0x0308
GL_FUNC_ADD = 0x8006
GL_BLEND_EQUATION = 0x8009
GL_BLEND_EQUATION_RGB = 0x8009
GL_BLEND_EQUATION_ALPHA = 0x883D
GL_FUNC_SUBTRACT = 0x800A
GL_FUNC_REVERSE_SUBTRACT = 0x800B
GL_BLEND_DST_RGB = 0x80C8
GL_BLEND_SRC_RGB = 0x80C9
GL_BLEND_DST_ALPHA = 0x80CA
GL_BLEND_SRC_ALPHA = 0x80CB
GL_CONSTANT_COLOR = 0x8001
GL_ONE_MINUS_CONSTANT_COLOR = 0x8002
GL_CONSTANT_ALPHA = 0x8003
GL_ONE_MINUS_CONSTANT_ALPHA = 0x8004
GL_BLEND_COLOR = 0x8005
GL_ARRAY_BUFFER = 0x8892
GL_ELEMENT_ARRAY_BUFFER = 0x8893
GL_ARRAY_BUFFER_BINDING = 0x8894
GL_ELEMENT_ARRAY_BUFFER_BINDING = 0x8895
GL_STREAM_DRAW = 0x88E0
GL_STATIC_DRAW = 0x88E4
GL_DYNAMIC_DRAW = 0x88E8
GL_BUFFER_SIZE = 0x8764
GL_BUFFER_USAGE = 0x8765
GL_CURRENT_VERTEX_ATTRIB = 0x8626
GL_FRONT = 0x0404
GL_BACK = 0x0405
GL_FRONT_AND_BACK = 0x0408
GL_TEXTURE_2D = 0x0DE1
GL_CULL_FACE = 0x0B44
GL_BLEND = 0x0BE2
GL_DITHER = 0x0BD0
GL_STENCIL_TEST = 0x0B90
GL_DEPTH_TEST = 0x0B71
GL_SCISSOR_TEST = 0x0C11
GL_POLYGON_OFFSET_FILL = 0x8037
GL_SAMPLE_ALPHA_TO_COVERAGE = 0x809E
GL_SAMPLE_COVERAGE = 0x80A0
GL_INVALID_ENUM = 0x0500
GL_INVALID_VALUE = 0x0501
GL_INVALID_OPERATION = 0x0502
GL_OUT_OF_MEMORY = 0x0505
GL_CW = 0x0900
GL_CCW = 0x0901
GL_LINE_WIDTH = 0x0B21
GL_ALIASED_POINT_SIZE_RANGE = 0x846D
GL_ALIASED_LINE_WIDTH_RANGE = 0x846E
GL_CULL_FACE_MODE = 0x0B45
GL_FRONT_FACE = 0x0B46
GL_DEPTH_RANGE = 0x0B70
GL_DEPTH_WRITEMASK = 0x0B72
GL_DEPTH_CLEAR_VALUE = 0x0B73
GL_DEPTH_FUNC = 0x0B74
GL_STENCIL_CLEAR_VALUE = 0x0B91
GL_STENCIL_FUNC = 0x0B92
GL_STENCIL_FAIL = 0x0B94
GL_STENCIL_PASS_DEPTH_FAIL = 0x0B95
GL_STENCIL_PASS_DEPTH_PASS = 0x0B96
GL_STENCIL_REF = 0x0B97
GL_STENCIL_VALUE_MASK = 0x0B93
GL_STENCIL_WRITEMASK = 0x0B98
GL_STENCIL_BACK_FUNC = 0x8800
GL_STENCIL_BACK_FAIL = 0x8801
GL_STENCIL_BACK_PASS_DEPTH_FAIL = 0x8802
GL_STENCIL_BACK_PASS_DEPTH_PASS = 0x8803
GL_STENCIL_BACK_REF = 0x8CA3
GL_STENCIL_BACK_VALUE_MASK = 0x8CA4
GL_STENCIL_BACK_WRITEMASK = 0x8CA5
GL_VIEWPORT = 0x0BA2
GL_SCISSOR_BOX = 0x0C10
GL_COLOR_CLEAR_VALUE = 0x0C22
GL_COLOR_WRITEMASK = 0x0C23
GL_UNPACK_ALIGNMENT = 0x0CF5
GL_PACK_ALIGNMENT = 0x0D05
GL_MAX_TEXTURE_SIZE = 0x0D33
GL_MAX_VIEWPORT_DIMS = 0x0D3A
GL_SUBPIXEL_BITS = 0x0D50
GL_RED_BITS = 0x0D52
GL_GREEN_BITS = 0x0D53
GL_BLUE_BITS = 0x0D54
GL_ALPHA_BITS = 0x0D55
GL_DEPTH_BITS = 0x0D56
GL_STENCIL_BITS = 0x0D57
GL_POLYGON_OFFSET_UNITS = 0x2A00
GL_POLYGON_OFFSET_FACTOR = 0x8038
GL_TEXTURE_BINDING_2D = 0x8069
GL_SAMPLE_BUFFERS = 0x80A8
GL_SAMPLES = 0x80A9
GL_SAMPLE_COVERAGE_VALUE = 0x80AA
GL_SAMPLE_COVERAGE_INVERT = 0x80AB
GL_NUM_COMPRESSED_TEXTURE_FORMATS = 0x86A2
GL_COMPRESSED_TEXTURE_FORMATS = 0x86A3
GL_DONT_CARE = 0x1100
GL_FASTEST = 0x1101
GL_NICEST = 0x1102
GL_GENERATE_MIPMAP_HINT = 0x8192
GL_BYTE = 0x1400
GL_UNSIGNED_BYTE = 0x1401
GL_SHORT = 0x1402
GL_UNSIGNED_SHORT = 0x1403
GL_INT = 0x1404
GL_UNSIGNED_INT = 0x1405
GL_FLOAT = 0x1406
GL_FIXED = 0x140C
GL_DEPTH_COMPONENT = 0x1902
GL_ALPHA = 0x1906
GL_RGB = 0x1907
GL_RGBA = 0x1908
GL_LUMINANCE = 0x1909
GL_LUMINANCE_ALPHA = 0x190A
GL_UNSIGNED_SHORT_4_4_4_4 = 0x8033
GL_UNSIGNED_SHORT_5_5_5_1 = 0x8034
GL_UNSIGNED_SHORT_5_6_5 = 0x8363
GL_FRAGMENT_SHADER = 0x8B30
GL_VERTEX_SHADER = 0x8B31
GL_MAX_VERTEX_ATTRIBS = 0x8869
GL_MAX_VERTEX_UNIFORM_VECTORS = 0x8DFB
GL_MAX_VARYING_VECTORS = 0x8DFC
GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS = 0x8B4D
GL_MAX_VERTEX_TEXTURE_IMAGE_UNITS = 0x8B4C
GL_MAX_TEXTURE_IMAGE_UNITS = 0x8872
GL_MAX_FRAGMENT_UNIFORM_VECTORS = 0x8DFD
GL_SHADER_TYPE = 0x8B4F
GL_DELETE_STATUS = 0x8B80
GL_LINK_STATUS = 0x8B82
GL_VALIDATE_STATUS = 0x8B83
GL_ATTACHED_SHADERS = 0x8B85
GL_ACTIVE_UNIFORMS = 0x8B86
GL_ACTIVE_UNIFORM_MAX_LENGTH = 0x8B87
GL_ACTIVE_ATTRIBUTES = 0x8B89
GL_ACTIVE_ATTRIBUTE_MAX_LENGTH = 0x8B8A
GL_SHADING_LANGUAGE_VERSION = 0x8B8C
GL_CURRENT_PROGRAM = 0x8B8D
GL_NEVER = 0x0200
GL_LESS = 0x0201
GL_EQUAL = 0x0202
GL_LEQUAL = 0x0203
GL_GREATER = 0x0204
GL_NOTEQUAL = 0x0205
GL_GEQUAL = 0x0206
GL_ALWAYS = 0x0207
GL_KEEP = 0x1E00
GL_REPLACE = 0x1E01
GL_INCR = 0x1E02
GL_DECR = 0x1E03
GL_INVERT = 0x150A
GL_INCR_WRAP = 0x8507
GL_DECR_WRAP = 0x8508
GL_VENDOR = 0x1F00
GL_RENDERER = 0x1F01
GL_VERSION = 0x1F02
GL_EXTENSIONS = 0x1F03
GL_NEAREST = 0x2600
GL_LINEAR = 0x2601
GL_NEAREST_MIPMAP_NEAREST = 0x2700
GL_LINEAR_MIPMAP_NEAREST = 0x2701
GL_NEAREST_MIPMAP_LINEAR = 0x2702
GL_LINEAR_MIPMAP_LINEAR = 0x2703
GL_TEXTURE_MAG_FILTER = 0x2800
GL_TEXTURE_MIN_FILTER = 0x2801
GL_TEXTURE_WRAP_S = 0x2802
GL_TEXTURE_WRAP_T = 0x2803
GL_TEXTURE = 0x1702
GL_TEXTURE_CUBE_MAP = 0x8513
GL_TEXTURE_BINDING_CUBE_MAP = 0x8514
GL_TEXTURE_CUBE_MAP_POSITIVE_X = 0x8515
GL_TEXTURE_CUBE_MAP_NEGATIVE_X = 0x8516
GL_TEXTURE_CUBE_MAP_POSITIVE_Y = 0x8517
GL_TEXTURE_CUBE_MAP_NEGATIVE_Y = 0x8518
GL_TEXTURE_CUBE_MAP_POSITIVE_Z = 0x8519
GL_TEXTURE_CUBE_MAP_NEGATIVE_Z = 0x851A
GL_MAX_CUBE_MAP_TEXTURE_SIZE = 0x851C
GL_TEXTURE0 = 0x84C0
GL_TEXTURE1 = 0x84C1
GL_TEXTURE2 = 0x84C2
GL_TEXTURE3 = 0x84C3
GL_TEXTURE4 = 0x84C4
GL_TEXTURE5 = 0x84C5
GL_TEXTURE6 = 0x84C6
GL_TEXTURE7 = 0x84C7
GL_TEXTURE8 = 0x84C8
GL_TEXTURE9 = 0x84C9
GL_TEXTURE10 = 0x84CA
GL_TEXTURE11 = 0x84CB
GL_TEXTURE12 = 0x84CC
GL_TEXTURE13 = 0x84CD
GL_TEXTURE14 = 0x84CE
GL_TEXTURE15 = 0x84CF
GL_TEXTURE16 = 0x84D0
GL_TEXTURE17 = 0x84D1
GL_TEXTURE18 = 0x84D2
GL_TEXTURE19 = 0x84D3
GL_TEXTURE20 = 0x84D4
GL_TEXTURE21 = 0x84D5
GL_TEXTURE22 = 0x84D6
GL_TEXTURE23 = 0x84D7
GL_TEXTURE24 = 0x84D8
GL_TEXTURE25 = 0x84D9
GL_TEXTURE26 = 0x84DA
GL_TEXTURE27 = 0x84DB
GL_TEXTURE28 = 0x84DC
GL_TEXTURE29 = 0x84DD
GL_TEXTURE30 = 0x84DE
GL_TEXTURE31 = 0x84DF
GL_ACTIVE_TEXTURE = 0x84E0
GL_REPEAT = 0x2901
GL_CLAMP_TO_EDGE = 0x812F
GL_MIRRORED_REPEAT = 0x8370
GL_FLOAT_VEC2 = 0x8B50
GL_FLOAT_VEC3 = 0x8B51
GL_FLOAT_VEC4 = 0x8B52
GL_INT_VEC2 = 0x8B53
GL_INT_VEC3 = 0x8B54
GL_INT_VEC4 = 0x8B55
GL_BOOL = 0x8B56
GL_BOOL_VEC2 = 0x8B57
GL_BOOL_VEC3 = 0x8B58
GL_BOOL_VEC4 = 0x8B59
GL_FLOAT_MAT2 = 0x8B5A
GL_FLOAT_MAT3 = 0x8B5B
GL_FLOAT_MAT4 = 0x8B5C
GL_SAMPLER_2D = 0x8B5E
GL_SAMPLER_CUBE = 0x8B60
GL_VERTEX_ATTRIB_ARRAY_ENABLED = 0x8622
GL_VERTEX_ATTRIB_ARRAY_SIZE = 0x8623
GL_VERTEX_ATTRIB_ARRAY_STRIDE = 0x8624
GL_VERTEX_ATTRIB_ARRAY_TYPE = 0x8625
GL_VERTEX_ATTRIB_ARRAY_NORMALIZED = 0x886A
GL_VERTEX_ATTRIB_ARRAY_POINTER = 0x8645
GL_VERTEX_ATTRIB_ARRAY_BUFFER_BINDING = 0x889F
GL_IMPLEMENTATION_COLOR_READ_TYPE = 0x8B9A
GL_IMPLEMENTATION_COLOR_READ_FORMAT = 0x8B9B
GL_COMPILE_STATUS = 0x8B81
GL_INFO_LOG_LENGTH = 0x8B84
GL_SHADER_SOURCE_LENGTH = 0x8B88
GL_SHADER_COMPILER = 0x8DFA
GL_SHADER_BINARY_FORMATS = 0x8DF8
GL_NUM_SHADER_BINARY_FORMATS = 0x8DF9
GL_LOW_FLOAT = 0x8DF0
GL_MEDIUM_FLOAT = 0x8DF1
GL_HIGH_FLOAT = 0x8DF2
GL_LOW_INT = 0x8DF3
GL_MEDIUM_INT = 0x8DF4
GL_HIGH_INT = 0x8DF5
GL_FRAMEBUFFER = 0x8D40
GL_RENDERBUFFER = 0x8D41
GL_RGBA4 = 0x8056
GL_RGB5_A1 = 0x8057
GL_RGB565 = 0x8D62
GL_DEPTH_COMPONENT16 = 0x81A5
GL_STENCIL_INDEX = 0x1901
GL_STENCIL_INDEX8 = 0x8D48
GL_RENDERBUFFER_WIDTH = 0x8D42
GL_RENDERBUFFER_HEIGHT = 0x8D43
GL_RENDERBUFFER_INTERNAL_FORMAT = 0x8D44
GL_RENDERBUFFER_RED_SIZE = 0x8D50
GL_RENDERBUFFER_GREEN_SIZE = 0x8D51
GL_RENDERBUFFER_BLUE_SIZE = 0x8D52
GL_RENDERBUFFER_ALPHA_SIZE = 0x8D53
GL_RENDERBUFFER_DEPTH_SIZE = 0x8D54
GL_RENDERBUFFER_STENCIL_SIZE = 0x8D55
GL_FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE = 0x8CD0
GL_FRAMEBUFFER_ATTACHMENT_OBJECT_NAME = 0x8CD1
GL_FRAMEBUFFER_ATTACHMENT_TEXTURE_LEVEL = 0x8CD2
GL_FRAMEBUFFER_ATTACHMENT_TEXTURE_CUBE_MAP_FACE = 0x8CD3
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_DEPTH_ATTACHMENT = 0x8D00
GL_STENCIL_ATTACHMENT = 0x8D20
GL_FRAMEBUFFER_COMPLETE = 0x8CD5
GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT = 0x8CD6
GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT = 0x8CD7
GL_FRAMEBUFFER_INCOMPLETE_DIMENSIONS = 0x8CD9
GL_FRAMEBUFFER_UNSUPPORTED = 0x8CDD
GL_FRAMEBUFFER_BINDING = 0x8CA6
GL_RENDERBUFFER_BINDING = 0x8CA7
GL_MAX_RENDERBUFFER_SIZE = 0x84E8
GL_INVALID_FRAMEBUFFER_OPERATION = 0x050


########NEW FILE########
__FILENAME__ = gl2ext
"""
This module contains integer constants from a C header file named something
like gl2ext.h.
"""

GL_ETC1_RGB8_OES = 0x8D64
GL_PALETTE4_RGB8_OES = 0x8B90
GL_PALETTE4_RGBA8_OES = 0x8B91
GL_PALETTE4_R5_G6_B5_OES = 0x8B92
GL_PALETTE4_RGBA4_OES = 0x8B93
GL_PALETTE4_RGB5_A1_OES = 0x8B94
GL_PALETTE8_RGB8_OES = 0x8B95
GL_PALETTE8_RGBA8_OES = 0x8B96
GL_PALETTE8_R5_G6_B5_OES = 0x8B97
GL_PALETTE8_RGBA4_OES = 0x8B98
GL_PALETTE8_RGB5_A1_OES = 0x8B99
GL_DEPTH_COMPONENT24_OES = 0x81A6
GL_DEPTH_COMPONENT32_OES = 0x81A7
GL_TEXTURE_EXTERNAL_OES = 0x8D65
GL_SAMPLER_EXTERNAL_OES = 0x8D66
GL_TEXTURE_BINDING_EXTERNAL_OES = 0x8D67
GL_REQUIRED_TEXTURE_IMAGE_UNITS_OES = 0x8D68
GL_UNSIGNED_INT = 0x1405
GL_PROGRAM_BINARY_LENGTH_OES = 0x8741
GL_NUM_PROGRAM_BINARY_FORMATS_OES = 0x87FE
GL_PROGRAM_BINARY_FORMATS_OES = 0x87FF
GL_WRITE_ONLY_OES = 0x88B9
GL_BUFFER_ACCESS_OES = 0x88BB
GL_BUFFER_MAPPED_OES = 0x88BC
GL_BUFFER_MAP_POINTER_OES = 0x88BD
GL_DEPTH_STENCIL_OES = 0x84F9
GL_UNSIGNED_INT_24_8_OES = 0x84FA
GL_DEPTH24_STENCIL8_OES = 0x88F0
GL_RGB8_OES = 0x8051
GL_RGBA8_OES = 0x8058
GL_FRAGMENT_SHADER_DERIVATIVE_HINT_OES = 0x8B8B
GL_STENCIL_INDEX1_OES = 0x8D46
GL_STENCIL_INDEX4_OES = 0x8D47
GL_TEXTURE_WRAP_R_OES = 0x8072
GL_TEXTURE_3D_OES = 0x806F
GL_TEXTURE_BINDING_3D_OES = 0x806A
GL_MAX_3D_TEXTURE_SIZE_OES = 0x8073
GL_SAMPLER_3D_OES = 0x8B5F
GL_FRAMEBUFFER_ATTACHMENT_TEXTURE_3D_ZOFFSET_OES = 0x8CD4
GL_HALF_FLOAT_OES = 0x8D61
GL_VERTEX_ARRAY_BINDING_OES = 0x85B5
GL_UNSIGNED_INT_10_10_10_2_OES = 0x8DF6
GL_INT_10_10_10_2_OES = 0x8DF7
GL_3DC_X_AMD = 0x87F9
GL_3DC_XY_AMD = 0x87FA
GL_ATC_RGB_AMD = 0x8C92
GL_ATC_RGBA_EXPLICIT_ALPHA_AMD = 0x8C93
GL_ATC_RGBA_INTERPOLATED_ALPHA_AMD = 0x87EE
GL_COUNTER_TYPE_AMD = 0x8BC0
GL_COUNTER_RANGE_AMD = 0x8BC1
GL_UNSIGNED_INT64_AMD = 0x8BC2
GL_PERCENTAGE_AMD = 0x8BC3
GL_PERFMON_RESULT_AVAILABLE_AMD = 0x8BC4
GL_PERFMON_RESULT_SIZE_AMD = 0x8BC5
GL_PERFMON_RESULT_AMD = 0x8BC6
GL_Z400_BINARY_AMD = 0x8740
GL_READ_FRAMEBUFFER_ANGLE = 0x8CA8
GL_DRAW_FRAMEBUFFER_ANGLE = 0x8CA9
GL_DRAW_FRAMEBUFFER_BINDING_ANGLE = 0x8CA6
GL_READ_FRAMEBUFFER_BINDING_ANGLE = 0x8CAA
GL_RENDERBUFFER_SAMPLES_ANGLE = 0x8CAB
GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE_ANGLE = 0x8D56
GL_MAX_SAMPLES_ANGLE = 0x8D57
GL_RGB_422_APPLE = 0x8A1F
GL_UNSIGNED_SHORT_8_8_APPLE = 0x85BA
GL_UNSIGNED_SHORT_8_8_REV_APPLE = 0x85BB
GL_RENDERBUFFER_SAMPLES_APPLE = 0x8CAB
GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE_APPLE = 0x8D56
GL_MAX_SAMPLES_APPLE = 0x8D57
GL_READ_FRAMEBUFFER_APPLE = 0x8CA8
GL_DRAW_FRAMEBUFFER_APPLE = 0x8CA9
GL_DRAW_FRAMEBUFFER_BINDING_APPLE = 0x8CA6
GL_READ_FRAMEBUFFER_BINDING_APPLE = 0x8CAA
GL_BGRA_EXT = 0x80E1
GL_TEXTURE_MAX_LEVEL_APPLE = 0x813D
GL_MALI_SHADER_BINARY_ARM = 0x8F60
GL_MIN_EXT = 0x8007
GL_MAX_EXT = 0x8008
GL_COLOR_EXT = 0x1800
GL_DEPTH_EXT = 0x1801
GL_STENCIL_EXT = 0x1802
GL_BGRA_EXT = 0x80E1
GL_UNSIGNED_SHORT_4_4_4_4_REV_EXT = 0x8365
GL_UNSIGNED_SHORT_1_5_5_5_REV_EXT = 0x8366
GL_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FE
GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FF
GL_BGRA_EXT = 0x80E1
GL_UNSIGNED_INT_2_10_10_10_REV_EXT = 0x8368
GL_COMPRESSED_RGB_S3TC_DXT1_EXT = 0x83F0
GL_COMPRESSED_RGBA_S3TC_DXT1_EXT = 0x83F1
GL_UNPACK_ROW_LENGTH = 0x0CF2
GL_UNPACK_SKIP_ROWS = 0x0CF3
GL_UNPACK_SKIP_PIXELS = 0x0CF4
GL_SHADER_BINARY_DMP = 0x9250
GL_SGX_PROGRAM_BINARY_IMG = 0x9130
GL_BGRA_IMG = 0x80E1
GL_UNSIGNED_SHORT_4_4_4_4_REV_IMG = 0x8365
GL_SGX_BINARY_IMG = 0x8C0A
GL_COMPRESSED_RGB_PVRTC_4BPPV1_IMG = 0x8C00
GL_COMPRESSED_RGB_PVRTC_2BPPV1_IMG = 0x8C01
GL_COMPRESSED_RGBA_PVRTC_4BPPV1_IMG = 0x8C02
GL_COMPRESSED_RGBA_PVRTC_2BPPV1_IMG = 0x8C03
GL_RENDERBUFFER_SAMPLES_IMG = 0x9133
GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE_IMG = 0x9134
GL_MAX_SAMPLES_IMG = 0x9135
GL_TEXTURE_SAMPLES_IMG = 0x9136
GL_COVERAGE_COMPONENT_NV = 0x8ED0
GL_COVERAGE_COMPONENT4_NV = 0x8ED1
GL_COVERAGE_ATTACHMENT_NV = 0x8ED2
GL_COVERAGE_BUFFERS_NV = 0x8ED3
GL_COVERAGE_SAMPLES_NV = 0x8ED4
GL_COVERAGE_ALL_FRAGMENTS_NV = 0x8ED5
GL_COVERAGE_EDGE_FRAGMENTS_NV = 0x8ED6
GL_COVERAGE_AUTOMATIC_NV = 0x8ED7
GL_COVERAGE_BUFFER_BIT_NV = 0x8000
GL_DEPTH_COMPONENT16_NONLINEAR_NV = 0x8E2C
GL_MAX_DRAW_BUFFERS_NV = 0x8824
GL_DRAW_BUFFER0_NV = 0x8825
GL_DRAW_BUFFER1_NV = 0x8826
GL_DRAW_BUFFER2_NV = 0x8827
GL_DRAW_BUFFER3_NV = 0x8828
GL_DRAW_BUFFER4_NV = 0x8829
GL_DRAW_BUFFER5_NV = 0x882A
GL_DRAW_BUFFER6_NV = 0x882B
GL_DRAW_BUFFER7_NV = 0x882C
GL_DRAW_BUFFER8_NV = 0x882D
GL_DRAW_BUFFER9_NV = 0x882E
GL_DRAW_BUFFER10_NV = 0x882F
GL_DRAW_BUFFER11_NV = 0x8830
GL_DRAW_BUFFER12_NV = 0x8831
GL_DRAW_BUFFER13_NV = 0x8832
GL_DRAW_BUFFER14_NV = 0x8833
GL_DRAW_BUFFER15_NV = 0x8834
GL_COLOR_ATTACHMENT0_NV = 0x8CE0
GL_COLOR_ATTACHMENT1_NV = 0x8CE1
GL_COLOR_ATTACHMENT2_NV = 0x8CE2
GL_COLOR_ATTACHMENT3_NV = 0x8CE3
GL_COLOR_ATTACHMENT4_NV = 0x8CE4
GL_COLOR_ATTACHMENT5_NV = 0x8CE5
GL_COLOR_ATTACHMENT6_NV = 0x8CE6
GL_COLOR_ATTACHMENT7_NV = 0x8CE7
GL_COLOR_ATTACHMENT8_NV = 0x8CE8
GL_COLOR_ATTACHMENT9_NV = 0x8CE9
GL_COLOR_ATTACHMENT10_NV = 0x8CEA
GL_COLOR_ATTACHMENT11_NV = 0x8CEB
GL_COLOR_ATTACHMENT12_NV = 0x8CEC
GL_COLOR_ATTACHMENT13_NV = 0x8CED
GL_COLOR_ATTACHMENT14_NV = 0x8CEE
GL_COLOR_ATTACHMENT15_NV = 0x8CEF
GL_MAX_COLOR_ATTACHMENTS_NV = 0x8CDF
GL_ALL_COMPLETED_NV = 0x84F2
GL_FENCE_STATUS_NV = 0x84F3
GL_FENCE_CONDITION_NV = 0x84F4
GL_READ_BUFFER_NV = 0x0C02
GL_ALPHA_TEST_QCOM = 0x0BC0
GL_ALPHA_TEST_FUNC_QCOM = 0x0BC1
GL_ALPHA_TEST_REF_QCOM = 0x0BC2
GL_TEXTURE_WIDTH_QCOM = 0x8BD2
GL_TEXTURE_HEIGHT_QCOM = 0x8BD3
GL_TEXTURE_DEPTH_QCOM = 0x8BD4
GL_TEXTURE_INTERNAL_FORMAT_QCOM = 0x8BD5
GL_TEXTURE_FORMAT_QCOM = 0x8BD6
GL_TEXTURE_TYPE_QCOM = 0x8BD7
GL_TEXTURE_IMAGE_VALID_QCOM = 0x8BD8
GL_TEXTURE_NUM_LEVELS_QCOM = 0x8BD9
GL_TEXTURE_TARGET_QCOM = 0x8BDA
GL_TEXTURE_OBJECT_VALID_QCOM = 0x8BDB
GL_STATE_RESTORE = 0x8BDC
GL_PERFMON_GLOBAL_MODE_QCOM = 0x8FA0
GL_WRITEONLY_RENDERING_QCOM = 0x8823
GL_COLOR_BUFFER_BIT0_QCOM = 0x00000001
GL_COLOR_BUFFER_BIT1_QCOM = 0x00000002
GL_COLOR_BUFFER_BIT2_QCOM = 0x00000004
GL_COLOR_BUFFER_BIT3_QCOM = 0x00000008
GL_COLOR_BUFFER_BIT4_QCOM = 0x00000010
GL_COLOR_BUFFER_BIT5_QCOM = 0x00000020
GL_COLOR_BUFFER_BIT6_QCOM = 0x00000040
GL_COLOR_BUFFER_BIT7_QCOM = 0x00000080
GL_DEPTH_BUFFER_BIT0_QCOM = 0x00000100
GL_DEPTH_BUFFER_BIT1_QCOM = 0x00000200
GL_DEPTH_BUFFER_BIT2_QCOM = 0x00000400
GL_DEPTH_BUFFER_BIT3_QCOM = 0x00000800
GL_DEPTH_BUFFER_BIT4_QCOM = 0x00001000
GL_DEPTH_BUFFER_BIT5_QCOM = 0x00002000
GL_DEPTH_BUFFER_BIT6_QCOM = 0x00004000
GL_DEPTH_BUFFER_BIT7_QCOM = 0x00008000
GL_STENCIL_BUFFER_BIT0_QCOM = 0x00010000
GL_STENCIL_BUFFER_BIT1_QCOM = 0x00020000
GL_STENCIL_BUFFER_BIT2_QCOM = 0x00040000
GL_STENCIL_BUFFER_BIT3_QCOM = 0x00080000
GL_STENCIL_BUFFER_BIT4_QCOM = 0x00100000
GL_STENCIL_BUFFER_BIT5_QCOM = 0x00200000
GL_STENCIL_BUFFER_BIT6_QCOM = 0x00400000
GL_STENCIL_BUFFER_BIT7_QCOM = 0x00800000
GL_MULTISAMPLE_BUFFER_BIT0_QCOM = 0x01000000
GL_MULTISAMPLE_BUFFER_BIT1_QCOM = 0x02000000
GL_MULTISAMPLE_BUFFER_BIT2_QCOM = 0x04000000
GL_MULTISAMPLE_BUFFER_BIT3_QCOM = 0x08000000
GL_MULTISAMPLE_BUFFER_BIT4_QCOM = 0x10000000
GL_MULTISAMPLE_BUFFER_BIT5_QCOM = 0x20000000
GL_MULTISAMPLE_BUFFER_BIT6_QCOM = 0x40000000
GL_MULTISAMPLE_BUFFER_BIT7_QCOM = 0x80000000
GL_SHADER_BINARY_VIV = 0x8FC4

########NEW FILE########
__FILENAME__ = glext
"""
This module contains integer constants from a C header file named something
like glext.h.
"""

# TODO: this file is not used anywhere.

GL_BLEND_EQUATION_RGB_OES = 0x8009
GL_BLEND_EQUATION_ALPHA_OES = 0x883D
GL_BLEND_DST_RGB_OES = 0x80C8
GL_BLEND_SRC_RGB_OES = 0x80C9
GL_BLEND_DST_ALPHA_OES = 0x80CA
GL_BLEND_SRC_ALPHA_OES = 0x80CB
GL_BLEND_EQUATION_OES = 0x8009
GL_FUNC_ADD_OES = 0x8006
GL_FUNC_SUBTRACT_OES = 0x800A
GL_FUNC_REVERSE_SUBTRACT_OES = 0x800B
GL_ETC1_RGB8_OES = 0x8D64
GL_DEPTH_COMPONENT24_OES = 0x81A6
GL_DEPTH_COMPONENT32_OES = 0x81A7
GL_TEXTURE_CROP_RECT_OES = 0x8B9D
GL_TEXTURE_EXTERNAL_OES = 0x8D65
GL_TEXTURE_BINDING_EXTERNAL_OES = 0x8D67
GL_REQUIRED_TEXTURE_IMAGE_UNITS_OES = 0x8D68
GL_UNSIGNED_INT = 0x1405
GL_FIXED_OES = 0x140C
GL_FRAMEBUFFER_OES = 0x8D40
GL_RENDERBUFFER_OES = 0x8D41
GL_RGBA4_OES = 0x8056
GL_RGB5_A1_OES = 0x8057
GL_RGB565_OES = 0x8D62
GL_DEPTH_COMPONENT16_OES = 0x81A5
GL_RENDERBUFFER_WIDTH_OES = 0x8D42
GL_RENDERBUFFER_HEIGHT_OES = 0x8D43
GL_RENDERBUFFER_INTERNAL_FORMAT_OES = 0x8D44
GL_RENDERBUFFER_RED_SIZE_OES = 0x8D50
GL_RENDERBUFFER_GREEN_SIZE_OES = 0x8D51
GL_RENDERBUFFER_BLUE_SIZE_OES = 0x8D52
GL_RENDERBUFFER_ALPHA_SIZE_OES = 0x8D53
GL_RENDERBUFFER_DEPTH_SIZE_OES = 0x8D54
GL_RENDERBUFFER_STENCIL_SIZE_OES = 0x8D55
GL_FRAMEBUFFER_ATTACHMENT_OBJECT_TYPE_OES = 0x8CD0
GL_FRAMEBUFFER_ATTACHMENT_OBJECT_NAME_OES = 0x8CD1
GL_FRAMEBUFFER_ATTACHMENT_TEXTURE_LEVEL_OES = 0x8CD2
GL_FRAMEBUFFER_ATTACHMENT_TEXTURE_CUBE_MAP_FACE_OES = 0x8CD3
GL_COLOR_ATTACHMENT0_OES = 0x8CE0
GL_DEPTH_ATTACHMENT_OES = 0x8D00
GL_STENCIL_ATTACHMENT_OES = 0x8D20
GL_FRAMEBUFFER_COMPLETE_OES = 0x8CD5
GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT_OES = 0x8CD6
GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT_OES = 0x8CD7
GL_FRAMEBUFFER_INCOMPLETE_DIMENSIONS_OES = 0x8CD9
GL_FRAMEBUFFER_INCOMPLETE_FORMATS_OES = 0x8CDA
GL_FRAMEBUFFER_UNSUPPORTED_OES = 0x8CDD
GL_FRAMEBUFFER_BINDING_OES = 0x8CA6
GL_RENDERBUFFER_BINDING_OES = 0x8CA7
GL_MAX_RENDERBUFFER_SIZE_OES = 0x84E8
GL_INVALID_FRAMEBUFFER_OPERATION_OES = 0x0506
GL_WRITE_ONLY_OES = 0x88B9
GL_BUFFER_ACCESS_OES = 0x88BB
GL_BUFFER_MAPPED_OES = 0x88BC
GL_BUFFER_MAP_POINTER_OES = 0x88BD
GL_MODELVIEW_MATRIX_FLOAT_AS_INT_BITS_OES = 0x898D
GL_PROJECTION_MATRIX_FLOAT_AS_INT_BITS_OES = 0x898E
GL_TEXTURE_MATRIX_FLOAT_AS_INT_BITS_OES = 0x898F
GL_MAX_VERTEX_UNITS_OES = 0x86A4
GL_MAX_PALETTE_MATRICES_OES = 0x8842
GL_MATRIX_PALETTE_OES = 0x8840
GL_MATRIX_INDEX_ARRAY_OES = 0x8844
GL_WEIGHT_ARRAY_OES = 0x86AD
GL_CURRENT_PALETTE_MATRIX_OES = 0x8843
GL_MATRIX_INDEX_ARRAY_SIZE_OES = 0x8846
GL_MATRIX_INDEX_ARRAY_TYPE_OES = 0x8847
GL_MATRIX_INDEX_ARRAY_STRIDE_OES = 0x8848
GL_MATRIX_INDEX_ARRAY_POINTER_OES = 0x8849
GL_MATRIX_INDEX_ARRAY_BUFFER_BINDING_OES = 0x8B9E
GL_WEIGHT_ARRAY_SIZE_OES = 0x86AB
GL_WEIGHT_ARRAY_TYPE_OES = 0x86A9
GL_WEIGHT_ARRAY_STRIDE_OES = 0x86AA
GL_WEIGHT_ARRAY_POINTER_OES = 0x86AC
GL_WEIGHT_ARRAY_BUFFER_BINDING_OES = 0x889E
GL_DEPTH_STENCIL_OES = 0x84F9
GL_UNSIGNED_INT_24_8_OES = 0x84FA
GL_DEPTH24_STENCIL8_OES = 0x88F0
GL_RGB8_OES = 0x8051
GL_RGBA8_OES = 0x8058
GL_STENCIL_INDEX1_OES = 0x8D46
GL_STENCIL_INDEX4_OES = 0x8D47
GL_STENCIL_INDEX8_OES = 0x8D48
GL_INCR_WRAP_OES = 0x8507
GL_DECR_WRAP_OES = 0x8508
GL_NORMAL_MAP_OES = 0x8511
GL_REFLECTION_MAP_OES = 0x8512
GL_TEXTURE_CUBE_MAP_OES = 0x8513
GL_TEXTURE_BINDING_CUBE_MAP_OES = 0x8514
GL_TEXTURE_CUBE_MAP_POSITIVE_X_OES = 0x8515
GL_TEXTURE_CUBE_MAP_NEGATIVE_X_OES = 0x8516
GL_TEXTURE_CUBE_MAP_POSITIVE_Y_OES = 0x8517
GL_TEXTURE_CUBE_MAP_NEGATIVE_Y_OES = 0x8518
GL_TEXTURE_CUBE_MAP_POSITIVE_Z_OES = 0x8519
GL_TEXTURE_CUBE_MAP_NEGATIVE_Z_OES = 0x851A
GL_MAX_CUBE_MAP_TEXTURE_SIZE_OES = 0x851C
GL_TEXTURE_GEN_MODE_OES = 0x2500
GL_TEXTURE_GEN_STR_OES = 0x8D60
GL_MIRRORED_REPEAT_OES = 0x8370
GL_VERTEX_ARRAY_BINDING_OES = 0x85B5
GL_3DC_X_AMD = 0x87F9
GL_3DC_XY_AMD = 0x87FA
GL_ATC_RGB_AMD = 0x8C92
GL_ATC_RGBA_EXPLICIT_ALPHA_AMD = 0x8C93
GL_ATC_RGBA_INTERPOLATED_ALPHA_AMD = 0x87EE
GL_RENDERBUFFER_SAMPLES_APPLE = 0x8CAB
GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE_APPLE = 0x8D56
GL_MAX_SAMPLES_APPLE = 0x8D57
GL_READ_FRAMEBUFFER_APPLE = 0x8CA8
GL_DRAW_FRAMEBUFFER_APPLE = 0x8CA9
GL_DRAW_FRAMEBUFFER_BINDING_APPLE = 0x8CA6
GL_READ_FRAMEBUFFER_BINDING_APPLE = 0x8CAA
GL_BGRA_EXT = 0x80E1
GL_TEXTURE_MAX_LEVEL_APPLE = 0x813D
GL_MIN_EXT = 0x8007
GL_MAX_EXT = 0x8008
GL_COLOR_EXT = 0x1800
GL_DEPTH_EXT = 0x1801
GL_STENCIL_EXT = 0x1802
GL_BGRA_EXT = 0x80E1
GL_UNSIGNED_SHORT_4_4_4_4_REV_EXT = 0x8365
GL_UNSIGNED_SHORT_1_5_5_5_REV_EXT = 0x8366
GL_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FE
GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT = 0x84FF
GL_BGRA_EXT = 0x80E1
GL_MAX_TEXTURE_LOD_BIAS_EXT = 0x84FD
GL_TEXTURE_FILTER_CONTROL_EXT = 0x8500
GL_TEXTURE_LOD_BIAS_EXT = 0x8501
GL_BGRA_IMG = 0x80E1
GL_UNSIGNED_SHORT_4_4_4_4_REV_IMG = 0x8365
GL_COMPRESSED_RGB_PVRTC_4BPPV1_IMG = 0x8C00
GL_COMPRESSED_RGB_PVRTC_2BPPV1_IMG = 0x8C01
GL_COMPRESSED_RGBA_PVRTC_4BPPV1_IMG = 0x8C02
GL_COMPRESSED_RGBA_PVRTC_2BPPV1_IMG = 0x8C03
GL_MODULATE_COLOR_IMG = 0x8C04
GL_RECIP_ADD_SIGNED_ALPHA_IMG = 0x8C05
GL_TEXTURE_ALPHA_MODULATE_IMG = 0x8C06
GL_FACTOR_ALPHA_MODULATE_IMG = 0x8C07
GL_FRAGMENT_ALPHA_MODULATE_IMG = 0x8C08
GL_ADD_BLEND_IMG = 0x8C09
GL_DOT3_RGBA_IMG = 0x86AF
GL_CLIP_PLANE0_IMG = 0x3000
GL_CLIP_PLANE1_IMG = 0x3001
GL_CLIP_PLANE2_IMG = 0x3002
GL_CLIP_PLANE3_IMG = 0x3003
GL_CLIP_PLANE4_IMG = 0x3004
GL_CLIP_PLANE5_IMG = 0x3005
GL_MAX_CLIP_PLANES_IMG = 0x0D32
GL_RENDERBUFFER_SAMPLES_IMG = 0x9133
GL_FRAMEBUFFER_INCOMPLETE_MULTISAMPLE_IMG = 0x9134
GL_MAX_SAMPLES_IMG = 0x9135
GL_TEXTURE_SAMPLES_IMG = 0x9136
GL_ALL_COMPLETED_NV = 0x84F2
GL_FENCE_STATUS_NV = 0x84F3
GL_FENCE_CONDITION_NV = 0x84F4
GL_TEXTURE_WIDTH_QCOM = 0x8BD2
GL_TEXTURE_HEIGHT_QCOM = 0x8BD3
GL_TEXTURE_DEPTH_QCOM = 0x8BD4
GL_TEXTURE_INTERNAL_FORMAT_QCOM = 0x8BD5
GL_TEXTURE_FORMAT_QCOM = 0x8BD6
GL_TEXTURE_TYPE_QCOM = 0x8BD7
GL_TEXTURE_IMAGE_VALID_QCOM = 0x8BD8
GL_TEXTURE_NUM_LEVELS_QCOM = 0x8BD9
GL_TEXTURE_TARGET_QCOM = 0x8BDA
GL_TEXTURE_OBJECT_VALID_QCOM = 0x8BDB
GL_STATE_RESTORE = 0x8BDC
GL_PERFMON_GLOBAL_MODE_QCOM = 0x8FA0
GL_WRITEONLY_RENDERING_QCOM = 0x8823
GL_COLOR_BUFFER_BIT0_QCOM = 0x00000001
GL_COLOR_BUFFER_BIT1_QCOM = 0x00000002
GL_COLOR_BUFFER_BIT2_QCOM = 0x00000004
GL_COLOR_BUFFER_BIT3_QCOM = 0x00000008
GL_COLOR_BUFFER_BIT4_QCOM = 0x00000010
GL_COLOR_BUFFER_BIT5_QCOM = 0x00000020
GL_COLOR_BUFFER_BIT6_QCOM = 0x00000040
GL_COLOR_BUFFER_BIT7_QCOM = 0x00000080
GL_DEPTH_BUFFER_BIT0_QCOM = 0x00000100
GL_DEPTH_BUFFER_BIT1_QCOM = 0x00000200
GL_DEPTH_BUFFER_BIT2_QCOM = 0x00000400
GL_DEPTH_BUFFER_BIT3_QCOM = 0x00000800
GL_DEPTH_BUFFER_BIT4_QCOM = 0x00001000
GL_DEPTH_BUFFER_BIT5_QCOM = 0x00002000
GL_DEPTH_BUFFER_BIT6_QCOM = 0x00004000
GL_DEPTH_BUFFER_BIT7_QCOM = 0x00008000
GL_STENCIL_BUFFER_BIT0_QCOM = 0x00010000
GL_STENCIL_BUFFER_BIT1_QCOM = 0x00020000
GL_STENCIL_BUFFER_BIT2_QCOM = 0x00040000
GL_STENCIL_BUFFER_BIT3_QCOM = 0x00080000
GL_STENCIL_BUFFER_BIT4_QCOM = 0x00100000
GL_STENCIL_BUFFER_BIT5_QCOM = 0x00200000
GL_STENCIL_BUFFER_BIT6_QCOM = 0x00400000
GL_STENCIL_BUFFER_BIT7_QCOM = 0x00800000
GL_MULTISAMPLE_BUFFER_BIT0_QCOM = 0x01000000
GL_MULTISAMPLE_BUFFER_BIT1_QCOM = 0x02000000
GL_MULTISAMPLE_BUFFER_BIT2_QCOM = 0x04000000
GL_MULTISAMPLE_BUFFER_BIT3_QCOM = 0x08000000
GL_MULTISAMPLE_BUFFER_BIT4_QCOM = 0x10000000
GL_MULTISAMPLE_BUFFER_BIT5_QCOM = 0x20000000
GL_MULTISAMPLE_BUFFER_BIT6_QCOM = 0x40000000
GL_MULTISAMPLE_BUFFER_BIT7_QCOM = 0x80000000

########NEW FILE########
__FILENAME__ = Display
from __future__ import absolute_import, division, print_function, unicode_literals

from ctypes import c_float, byref

import six
import time
import threading
import traceback
import platform

from pi3d.constants import *
from pi3d.util import Log
from pi3d.util import Utility
from pi3d.util.DisplayOpenGL import DisplayOpenGL
from pi3d.Keyboard import Keyboard

if PLATFORM != PLATFORM_PI:
  from pyxlib.x import *
  from pyxlib import xlib

LOGGER = Log.logger(__name__)

ALLOW_MULTIPLE_DISPLAYS = False
RAISE_EXCEPTIONS = True
MARK_CAMERA_CLEAN_ON_EACH_LOOP = True

DEFAULT_FOV = 45.0
DEFAULT_DEPTH = 24
DEFAULT_NEAR = 1.0
DEFAULT_FAR = 1000.0
WIDTH = 0
HEIGHT = 0

class Display(object):
  """This is the central control object of the pi3d system and an instance
  must be created before some of the other class methods are called.
  """
  INSTANCE = None
  """The current unique instance of Display."""

  def __init__(self, tkwin=None):
    """
    Constructs a raw Display.  Use pi3d.Display.create to create an initialized
    Display.

    *tkwin*
      An optional Tk window.

    """
    if Display.INSTANCE:
      assert ALLOW_MULTIPLE_DISPLAYS
      LOGGER.warning('A second instance of Display was created')
    else:
      Display.INSTANCE = self

    self.tkwin = tkwin

    self.sprites = []
    self.sprites_to_load = set()
    self.sprites_to_unload = set()

    self.tidy_needed = False
    self.textures_dict = {}
    self.vbufs_dict = {}
    self.ebufs_dict = {}
    self.last_shader = None
    self.last_textures = [None, None, None] # if more than 3 used this will break in Buffer.draw()
    self.external_mouse = None

    if PLATFORM != PLATFORM_PI:
      self.event_list = []
      self.ev = xlib.XEvent()

    self.opengl = DisplayOpenGL()
    self.max_width, self.max_height = self.opengl.width, self.opengl.height
    self.first_time = True
    self.is_running = True
    self.lock = threading.RLock()

    LOGGER.debug(STARTUP_MESSAGE)

  def loop_running(self):
    """*loop_running* is the main event loop for the Display.

    Most pi3d code will look something like this::

      DISPLAY = Display.create()

      # Initialize objects and variables here.
      # ...

      while DISPLAY.loop_running():
        # Update the frame, using DISPLAY.time for the current time.
        # ...

        # Check for quit, then call DISPLAY.stop.
        if some_quit_condition():
          DISPLAY.stop()

    ``Display.loop_running()`` **must** be called on the main Python thread,
    or else white screens and program crashes are likely.

    The Display loop can run in two different modes - *free* or *framed*.

    If ``DISPLAY.frames_per_second`` is empty or 0 then the loop runs *free* - when
    it finishes one frame, it immediately starts working on the next frame.

    If ``Display.frames_per_second`` is a positive number then the Display is
    *framed* - when the Display finishes one frame before the next frame_time,
    it waits till the next frame starts.

    A free Display gives the highest frame rate, but it will also consume more
    CPU, to the detriment of other threads or other programs.  There is also
    the significant drawback that the framerate will fluctuate as the numbers of
    CPU cycles consumed per loop, resulting in jerky motion and animations.

    A framed Display has a consistent if smaller number of frames, and also
    allows for potentially much smoother motion and animation.  The ability to
    throttle down the number of frames to conserve CPU cycles is essential
    for programs with other important threads like audio.

    ``Display.frames_per_second`` can be set at construction in
    ``Display.create`` or changed on-the-fly during the execution of the
    program.  If ``Display.frames_per_second`` is set too high, the Display
    doesn't attempt to "catch up" but simply runs freely.

    """
    if self.is_running:
      if self.first_time:
        self.time = time.time()
        self.first_time = False
      else:
        self._loop_end()  # Finish the previous loop.
      self._loop_begin()
    else:
      self._loop_end()
      self.destroy()

    return self.is_running

  def resize(self, x=0, y=0, w=0, h=0):
    """Reshape the window with the given coordinates."""
    if w <= 0:
      w = self.max_width
    if h <= 0:
      h = self.max_height
    self.width = w
    self.height = h

    self.left = x
    self.top = y
    self.right = x + w
    self.bottom = y + h
    self.opengl.resize(x, y, w, h)

  def add_sprites(self, *sprites):
    """Add one or more sprites to this Display."""
    with self.lock:
      self.sprites_to_load.update(sprites)

  def remove_sprites(self, *sprites):
    """Remove one or more sprites from this Display."""
    with self.lock:
      self.sprites_to_unload.update(sprites)

  def stop(self):
    """Stop the Display."""
    self.is_running = False

  def destroy(self):
    """Destroy the current Display and reset Display.INSTANCE."""
    self._tidy()
    self.stop()
    try:
      self.opengl.destroy(self)
    except:
      pass
    if self.external_mouse:
      try:
        self.external_mouse.stop()
      except:
        pass_
    try:
      self.mouse.stop()
    except:
      pass
    try:
      self.tkwin.destroy()
    except:
      pass
    Display.INSTANCE = None

  def clear(self):
    """Clear the Display."""
    # opengles.glBindFramebuffer(GL_FRAMEBUFFER,0)
    opengles.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

  def set_background(self, r, g, b, alpha):
    """Set the Display background. **NB the actual drawing of the background
    happens during the rendering of the framebuffer by the shader so if no
    draw() is done by anything during each Display loop the screen will
    remain black** If you want to see just the background you will have to
    draw() something out of view (i.e. behind) the Camera.

    *r, g, b*
      Color values for the display
    *alpha*
      Opacity of the color.  An alpha of 0 means a transparent background,
      an alpha of 1 means full opaque.
    """
    opengles.glClearColor(c_float(r), c_float(g), c_float(b), c_float(alpha))
    opengles.glColorMask(1, 1, 1, int(alpha < 1.0))
    # Switches off alpha blending with desktop (is there a bug in the driver?)

  def mouse_position(self):
    """The current mouse position as a tuple."""
    # TODO: add: Now deprecated in favor of pi3d.events
    if self.mouse:
      return self.mouse.position()
    elif self.tkwin:
      return self.tkwin.winfo_pointerxy()
    else:
      return -1, -1

  def _loop_begin(self):
    # TODO(rec):  check if the window was resized and resize it, removing
    # code from MegaStation to here.
    if PLATFORM != PLATFORM_PI:
      n = xlib.XEventsQueued(self.opengl.d, xlib.QueuedAfterFlush)
      for i in range(n):
        if xlib.XCheckMaskEvent(self.opengl.d, KeyPressMask, self.ev):
          self.event_list.append(self.ev)
        else:
          xlib.XNextEvent(self.opengl.d, self.ev)
          if self.ev.type == ClientMessage:
            if (self.ev.xclient.data.l[0] == self.opengl.WM_DELETE_WINDOW.value):
              self.destroy()
    self.clear()
    with self.lock:
      self.sprites_to_load, to_load = set(), self.sprites_to_load
      self.sprites.extend(to_load)
    self._for_each_sprite(lambda s: s.load_opengl(), to_load)

    if MARK_CAMERA_CLEAN_ON_EACH_LOOP:
      from pi3d.Camera import Camera
      camera = Camera.instance()
      if camera:
        camera.was_moved = False

    if self.tidy_needed:
      self._tidy()

  def _tidy(self):
    to_del = []
    for i in self.textures_dict:
      tex = self.textures_dict[i]
      LOGGER.debug('tex0=%s tex1=%s',tex[0], tex[1])
      if tex[1] == 1:
        opengles.glDeleteTextures(1, byref(tex[0]))
        to_del.append(i)
    for i in to_del:
      del self.textures_dict[i]
    to_del = []
    for i in self.vbufs_dict:
      vbuf = self.vbufs_dict[i]
      if vbuf[1] == 1:
        opengles.glDeleteBuffers(1, byref(vbuf[0]))
        to_del.append(i)
    for i in to_del:
      del self.vbufs_dict[i]
    to_del = []
    for i in self.ebufs_dict:
      ebuf = self.ebufs_dict[i]
      if ebuf[1] == 1:
        opengles.glDeleteBuffers(1, byref(ebuf[0]))
        to_del.append(i)
    for i in to_del:
      del self.ebufs_dict[i]
    self.tidy_needed = False

  def _loop_end(self):
    with self.lock:
      self.sprites_to_unload, to_unload = set(), self.sprites_to_unload
      if to_unload:
        self.sprites = [s for s in self.sprites if s not in to_unload]

    t = time.time()
    self._for_each_sprite(lambda s: s.repaint(t))

    self.swap_buffers()

    for sprite in to_unload:
      sprite.unload_opengl()

    if getattr(self, 'frames_per_second', 0):
      self.time += 1.0 / self.frames_per_second
      delta = self.time - time.time()
      if delta > 0:
        time.sleep(delta)

  def _for_each_sprite(self, function, sprites=None):
    if sprites is None:
      sprites = self.sprites
    for s in sprites:
      try:
        function(s)
      except:
        LOGGER.error(traceback.format_exc())
        if RAISE_EXCEPTIONS:
          raise

  def __del__(self):
    self.destroy()

  def swap_buffers(self):
    self.opengl.swap_buffers()


def create(x=None, y=None, w=None, h=None, near=None, far=None,
           fov=DEFAULT_FOV, depth=DEFAULT_DEPTH, background=None,
           tk=False, window_title='', window_parent=None, mouse=False,
           frames_per_second=None):
  """
  Creates a pi3d Display.

  *x*
    Left x coordinate of the display.  If None, defaults to the x coordinate of
    the tkwindow parent, if any.
  *y*
    Top y coordinate of the display.  If None, defaults to the y coordinate of
    the tkwindow parent, if any.
  *w*
    Width of the display.  If None, full the width of the screen.
  *h*
    Height of the display.  If None, full the height of the screen.
  *near*
    This will be used for the default instance of Camera *near* plane
  *far*
    This will be used for the default instance of Camera *far* plane
  *fov*
    Used to define the Camera lens field of view
  *depth*
    The bit depth of the display - must be 8, 16 or 24.
  *background*
    r,g,b,alpha (opacity)
  *tk*
    Do we use the tk windowing system?
  *window_title*
    A window title for tk windows only.
  *window_parent*
    An optional tk parent window.
  *mouse*
    Automatically create a Mouse.
  *frames_per_second*
    Maximum frames per second to render (None means "free running").
  """
  if tk:
    if PLATFORM != PLATFORM_PI:
      #just use python-xlib same as non-tk but need dummy behaviour
      class DummyTkWin(object):
        def __init__(self):
          self.tkKeyboard = Keyboard()
          self.ev = ""
          self.key = ""
          self.winx, self.winy = 0, 0
          self.width, self.height = 1920, 1180
          self.event_list = []

        def update(self):
          self.key = self.tkKeyboard.read_code()
          if self.key == "":
            self.ev = ""
          else:
            self.ev = "key"

      tkwin = DummyTkWin()
      x = x or 0
      y = y or 0

    else:
      from pi3d.util import TkWin
      if not (w and h):
        # TODO: how do we do full-screen in tk?
        #LOGGER.error('Can't compute default window size when using tk')
        #raise Exception
        # ... just force full screen - TK will automatically fit itself into the screen
        w = 1920
        h = 1180
      tkwin = TkWin.TkWin(window_parent, window_title, w, h)
      tkwin.update()
      if x is None:
        x = tkwin.winx
      if y is None:
        y = tkwin.winy

  else:
    tkwin = None
    x = x or 0
    y = y or 0

  display = Display(tkwin)
  if (w or 0) <= 0:
    w = display.max_width - 2 * x
    if w <= 0:
      w = display.max_width
  if (h or 0) <= 0:
    h = display.max_height - 2 * y
    if h <= 0:
      h = display.max_height
  LOGGER.debug('Display size is w=%d, h=%d', w, h)

  display.frames_per_second = frames_per_second

  if near is None:
    near = DEFAULT_NEAR
  if far is None:
    far = DEFAULT_FAR

  display.width = w
  display.height = h
  display.near = near
  display.far = far
  display.fov = fov

  display.left = x
  display.top = y
  display.right = x + w
  display.bottom = y + h

  display.opengl.create_display(x, y, w, h, depth)
  display.mouse = None

  if mouse:
    from pi3d.Mouse import Mouse
    display.mouse = Mouse(width=w, height=h, restrict=False)
    display.mouse.start()

  if background:
    display.set_background(*background)

  return display

########NEW FILE########
__FILENAME__ = AbsAxisScaling
import array
import fcntl
import struct
from pi3d.event import ioctl

def EVIOCGABS(axis):
  return ioctl._IOR(ord('E'), 0x40 + axis, "ffffff")	# get abs value/limits

class AbsAxisScaling(object):
  """
  Fetches and implements the EV_ABS axis scaling.

  The constructor fetches the scaling values from the given stream for the
  given axis using an ioctl.

  There is a scale method, which scales a given value to the range -1..+1.
  """
  def __init__(self, stream, axis):
    """
    Fetch the scale values for this stream and fill in the instance
    variables accordingly.
    """
    s = array.array("f", [1, 2, 3, 4, 5, 6])
    try:
      x = fcntl.ioctl(stream.filehandle, EVIOCGABS(axis), s)
    except IOError:
      self.value = self.minimum = self.maximum = self.fuzz = self.flat = self.resolution = 1
    else:
      self.value, self.minimum, self.maximum, self.fuzz, self.flat, self.resolution = struct.unpack("ffffff", s)

  def __str__(self):
    return "Value {0} Min {1}, Max {2}, Fuzz {3}, Flat {4}, Res {5}".format(self.value, self.minimum, self.maximum, self.fuzz, self.flat, self.resolution)

  def scale(self, value):
    """
    scales the given value into the range -1..+1
    """
    return (float(value)-float(self.minimum))/float(self.maximum-self.minimum)*2.0 - 1.0


########NEW FILE########
__FILENAME__ = Constants
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03
EV_MSC = 0x04
EV_SW = 0x05
EV_LED = 0x11
EV_SND = 0x12
EV_REP = 0x14
EV_FF = 0x15
EV_PWR = 0x16
EV_FF_STATUS = 0x17

SYN_REPORT = 0
SYN_CONFIG = 1

REL_X = 0x00
REL_Y = 0x01
REL_Z = 0x02
REL_RX = 0x03
REL_RY = 0x04
REL_RZ = 0x05
REL_HWHEEL = 0x06
REL_DIAL = 0x07
REL_WHEEL = 0x08
REL_MISC = 0x09
REL_MAX = 0x0f

ABS_X = 0x00
ABS_Y = 0x01
ABS_Z = 0x02
ABS_RX = 0x03
ABS_RY = 0x04
ABS_RZ = 0x05
ABS_THROTTLE = 0x06
ABS_RUDDER = 0x07
ABS_WHEEL = 0x08
ABS_GAS = 0x09
ABS_BRAKE = 0x0a
ABS_HAT0X = 0x10
ABS_HAT0Y = 0x11
ABS_HAT1X = 0x12
ABS_HAT1Y = 0x13
ABS_HAT2X = 0x14
ABS_HAT2Y = 0x15
ABS_HAT3X = 0x16
ABS_HAT3Y = 0x17
ABS_PRESSURE = 0x18
ABS_DISTANCE = 0x19
ABS_TILT_X = 0x1a
ABS_TILT_Y = 0x1b
ABS_TOOL_WIDTH = 0x1c
ABS_VOLUME = 0x20
ABS_MISC = 0x28
ABS_MAX = 0x3f

########NEW FILE########
__FILENAME__ = Event
import six

from pi3d.event import EventHandler
from pi3d.event import Keys
from pi3d.event.FindDevices import find_devices
from pi3d.event.Constants import *
from pi3d.event.EventStream import EventStream

_KEYS = (k for k in vars(Keys) if not k.startswith('_'))
KEY_CODE = dict((k, getattr(Keys, k)) for k in _KEYS)
CODE_KEY = {}
for v in KEY_CODE:
  CODE_KEY[KEY_CODE[v]] = v

def key_to_code(key):
  return KEY_CODE.get(str(key), -1) if isinstance(key, six.string_types) else key

def code_to_key(code):
  return CODE_KEY.get(code, '')

class InputEvents(object):
  """Encapsulates the entire InputEvents subsystem.

  This is generally all you need to import. For efficiency reasons you may
  want to make use of CodeOf[ ], but everything else is hidden behind this class.

  On instantiation, we open all devices that are keyboards, mice or joysticks.
  That means we might have two of one sort of another, and that might be a problem,
  but it would be rather rare.

  There are several ABS (joystick, touch) events that we do not handle, specifically
  THROTTLE, RUDDER, WHEEL, GAS, BRAKE, HAT1, HAT2, HAT3, PRESSURE,
  DISTANCE, TILT, TOOL_WIDTH. Implementing these is left as an exercise
  for the interested reader. Similarly, we make no attempt to handle multi-touch.

  Handlers can be supplied, in which case they are called for each event, but
  it isn't necessary; API exists for all the events.

  The handler signatures are:

    def mouse_handler_func(sourceType, SourceIndex, x, y, v, h)
    def joystick_handler_func(sourceType, SourceIndex, x1, y1, z1, x2, y2, z2, hatx, haty)
    def key_handler_func(sourceType, SourceIndex, key, value)
    def syn_handler_func(sourceType, SourceIndex, code, value)
    def unhandled_handler_func(event)

  where:
    sourceType:
      the device type string (keyboard, mouse, joystick),

    sourceIndex:
      an incrementing number for each device of that type, starting at zero,
      and event is an EventStruct object.

    key:
      the key code, not its ASCII value or anything simple.

  Use key_to_code() to convert from the name of a key to its code,
  and code_to_key() to convert a code to a name.

  The keys are listed in pi3d.event.Constants.py or /usr/include/linux/input.h
  Note that the key names refer to a US keyboard.
  """
  def __init__(self, keyboardHandler=None, mouseHandler=None, joystickHandler=None, synHandler=None, unhandledHandler=None, wantKeyboard=True, wantMouse=True, wantJoystick=True):
    self.unhandledHandler = unhandledHandler
    self.streams = [ ]
    if wantKeyboard:
      keyboards =  find_devices("kbd")
      for x in keyboards:
        self.streams.append(EventStream(x, "keyboard"))
    else:
      keyboards = [ ]
    print("keyboards =", keyboards)
    if wantMouse:
      mice = find_devices("mouse", butNot=keyboards)
      for x in mice:
        self.streams.append(EventStream(x, "mouse"))
      print("mice = ", mice)
    else:
      mice = [ ]
    if wantJoystick:
      joysticks = find_devices("js", butNot=keyboards+mice)
      for x in joysticks:
        self.streams.append(EventStream(x, "joystick"))
      print("joysticks =", joysticks)
    for x in self.streams:
      x.acquire_abs_info()

    self.handler = EventHandler.EventHandler(
                  keyboardHandler, mouseHandler, joystickHandler, synHandler)

  def do_input_events(self):
    """
    Handle all events that have been triggered since the last call.
    """
    for event in EventStream.allNext(self.streams):
      if self.handler.event(event) and self.unhandledHandler:
        self.unhandledHandler(event)

  def key_state(self, key):
    """
    Returns the state of the given key.

    The returned value will be 0 for key-up, or 1 for key-down. This method
    returns a key-held(2) as 1 to aid in using the returned value as a
    movement distance.

    This function accepts either the key code or the string name of the key.
    It would be more efficient to look-up and store the code of
    the key with KEY_CODE[ ], rather than using the string every time. (Which
    involves a dict look-up keyed with a string for every key_state call, every
    time around the loop.)

    Gamepad keys are:
    Select = BTN_BASE3, Start = BTN_BASE4
    L1 = BTN_TOP       R1 = BTN_BASE
    L2 = BTN_PINKIE    R2 = BTN_BASE2
    The action buttons are:
            BTN_THUMB
    BTN_TRIGGER     BTN_TOP
            BTN_THUMB2
    Analogue Left Button = BTN_BASE5
    Analogue Right Button = BTN_BASE6

    Some of those may clash with extended mouse buttons, so if you are using
    both at once, you'll see some overlap.

    The direction pad is hat0 (see get_hat)
    """
    return self.handler.key_state(key_to_code(key))

  def clear_key(self, key):
    """
    Clears the state of the given key.

    Emulates a key-up, but does not call any handlers.
    """
    return self.handler.clear_key(key_to_code(key))

  def get_keys(self):
    return [code_to_key(k) for k in self.handler.get_keys()]

  def get_joystick(self, index=0):
    """
    Returns the x,y coordinates for a joystick or left gamepad analogue stick.

    index is the device index and defaults to 0 -- the first joystick device

    The values are returned as a tuple. All values are -1.0 to +1.0 with
    0.0 being centred.
    """
    return (self.handler.absx[index], self.handler.absy[index])

  def get_joystick3d(self, index=0):
    """
    Returns the x,y,z coordinates for a joystick or left gamepad analogue stick

    index is the device index and defaults to 0 -- the first joystick device

    The values are returned as a tuple. All values are -1.0 to +1.0 with
    0.0 being centred.
    """
    return (self.handler.absx[index], self.handler.absy[index], self.handler.absz[index])

  def get_joystickR(self, index=0):
    """
    Returns the x,y coordinates for a right gamepad analogue stick.

    index is the device index and defaults to 0 -- the first joystick device

    The values are returned as a tuple. For some odd reason, the gamepad
    returns values in the Z axes of both joysticks, with y being the first.

    All values are -1.0 to +1.0 with 0.0 being centred.
    """
    #return (self.handler.absz2[index], self.handler.absz[index])
    return (self.handler.absx2[index], self.handler.absz2[index])

  def get_joystickB3d(self, index=0):
    """
    Returns the x,y,z coordinates for a 2nd joystick control

    index is the device index and defaults to 0 -- the first joystick device

    The values are returned as a tuple. All values are -1.0 to +1.0 with
    0.0 being centred.
    """
    return (self.handler.absx2[index], self.handler.absy2[index], self.handler.absz2[index])

  def get_hat(self, index=0):
    """
    Returns the x,y coordinates for a joystick hat or gamepad direction pad

    index is the device index and defaults to 0 -- the first joystick device

    The values are returned as a tuple.  All values are -1.0 to +1.0 with
    0.0 being centred.
    """
    return (self.handler.abshatx[index], self.handler.abshaty[index])

  def get_mouse_movement(self, index=0):
    """
    Returns the accumulated mouse movements since the last call.

    index is the device index and defaults to 0 -- the first mouse device

    The returned value is a tuple: (X, Y, WHEEL, H-WHEEL)
    """
    return self.handler.get_rel_movement(index)

  def grab_by_type(self, deviceType, deviceIndex=None, grab=True):
    """
    Grab (or release) exclusive access to all devices of the given type.

    The devices are grabbed if grab is True and released if grab is False.
    If the deviceIndex is given, only that device is grabbed, otherwise all
    the devices of the same type are grabbed.

    All devices are grabbed to begin with. We might want to ungrab the
    keyboard for example to use it for text entry. While not grabbed, all key-down
    and key-hold events are filtered out, but that only works if the events
    are received and handled while the keyboard is still grabbed, and the loop
    may not have been running. So if we are grabbing a device, we call the
    handling loop first, so there are no outstanding events.

    Note that the filtering means that if you trigger the ungrab from a
    key-down event, the corrosponding key-up will be actioned before the
    subsequent grab, and you wont end up looping continuously. However it
    also means that you will see key-up events for all the text entry. Since
    it only affects a user-supplied key-handler, and key-ups do not usually
    trigger actions anyway, this is not likely to be a problem. If it is,
    you will have to filter them yourself.
    """
    if grab:
      self.do_input_events()
    EventStream.grab_by_type(deviceType, deviceIndex, grab, self.streams)

  def release(self):
    """
    Ungrabs all streams and closes all files.

    Only do this when you're finished with this object. You can't use it again.
    """
    for s in self.streams:
      s.release()


########NEW FILE########
__FILENAME__ = EventHandler
import threading

from pi3d.event.Constants import *
from pi3d.event.EventStream import EventStream

class EventHandler(object):
  """
  A class to handle events.

  Four types of events are handled: REL (mouse movement), KEY (keybaord keys and
  other device buttons), ABS (joysticks and gamepad analogue sticks) and SYN
  (delimits simultaneous events such as mouse movements)
  """
  def __init__(self, keyHandler=None, relHandler=None, absHandler=None, synHandler=None):
    self.buttons = dict()
    self.relHandler = relHandler
    self.keyHandler = keyHandler
    self.absHandler = absHandler
    self.synHandler = synHandler

    self.mutex = threading.Lock()

    self.absx = [0.0]*4
    self.absy = [0.0]*4
    self.absz = [0.0]*4
    self.absx2 = [0.0]*4
    self.absy2 = [0.0]*4
    self.absz2 = [0.0]*4
    self.abshatx = [0.0]*4
    self.abshaty = [0.0]*4

    self.relx = [0]*4
    self.rely = [0]*4
    self.relv = [0]*4
    self.relh = [0]*4
    self.reld = [0]*4

  def event(self, event):
    """
    Handles the given event.

    If the event is passed to a handler or otherwise handled then returns None,
    else returns the event. All handlers are optional.

    All key events are handled by putting them in the self.buttons dict, and
    optionally by calling the supplied handler.

    REL X, Y and wheel V and H events are all accumulated internally and
    also optionally passed to the supplied handler. All these events are handled.

    ABS X, Y, Z, RX, RY, RZ, Hat0X, Hat0Y are all accumulated internally and
    also optionally passed to the supplied handler. Other ABS events are not
    handled.

    All SYN events are passed to the supplied handler.

    There are several ABS events that we do not handle. In particular:
    THROTTLE, RUDDER, WHEEL, GAS, BRAKE, HAT1, HAT2, HAT3, PRESSURE,
    DISTANCE, TILT, TOOL_WIDTH. Implementing these is left as an exercise
    for the interested reader.

    Likewise, since one handler is handling all events for all devices, we
    may get the situation where two devices return the same button. The only
    way to handle that would seem to be to have a key dict for every device,
    which seems needlessly profligate for a situation that may never arise.
    """
    ret = event
    self.mutex.acquire()

    try:
      Handled = False
      if event.eventType == EV_SYN:
        if self.synHandler:
          self.synHandler(event.stream.deviceType, event.stream.deviceIndex, event.eventCode, event.eventValue)
          ret = None
      elif event.eventType == EV_KEY:
        if event.stream.grabbed == False and event.eventValue != 0:
          ret = None
        self.buttons[event.eventCode] = event.eventValue
        if self.keyHandler:
          self.keyHandler(event.stream.deviceType, event.stream.deviceIndex, event.eventCode, event.eventValue)
        ret = None
      elif event.eventType == EV_REL:
        if event.eventCode == REL_X:
          self.relx[event.stream.deviceIndex] += event.eventValue
          if self.relHandler:
            self.relHandler(event.stream.deviceType, event.stream.deviceIndex, event.eventValue, 0, 0, 0)
          ret = None
        elif event.eventCode == REL_Y:
          self.rely[event.stream.deviceIndex] += event.eventValue
          if self.relHandler:
            self.relHandler(event.stream.deviceType, event.stream.deviceIndex, 0, event.eventValue, 0, 0)
          ret = None
        elif event.eventCode == REL_WHEEL:
          self.relv[event.stream.deviceIndex] += event.eventValue
          if self.relHandler:
            self.relHandler(event.stream.deviceType, event.stream.deviceIndex, 0, 0, event.eventValue, 0)
          ret = None
        elif event.eventCode == REL_HWHEEL:
          self.relh[event.stream.deviceIndex] += event.eventValue
          if self.relHandler:
            self.relHandler(event.stream.deviceType, event.stream.deviceIndex, 0, 0, 0, event.eventValue)
        elif event.eventCode == REL_DIAL:
          self.relh[event.stream.deviceIndex] += event.eventValue
          if self.relHandler:
            self.relHandler(event.stream.deviceType, event.stream.deviceIndex, 0 ,0, 0, event.eventValue)
          ret = None
      elif event.eventType == EV_ABS:
        if event.eventCode == ABS_X:
          Handled = True
          self.absx[event.stream.deviceIndex] = event.stream.scale(EventStream.axisX, event.eventValue)
        elif event.eventCode == ABS_Y:
          Handled = True
          self.absy[event.stream.deviceIndex] = event.stream.scale(EventStream.axisY, event.eventValue)
        elif event.eventCode == ABS_Z:
          Handled = True
          self.absz[event.stream.deviceIndex] = event.stream.scale(EventStream.axisZ, event.eventValue)
        elif event.eventCode == ABS_RX:
          Handled = True
          self.absx2[event.stream.deviceIndex] = event.stream.scale(EventStream.axisRX, event.eventValue)
        elif event.eventCode == ABS_RY:
          Handled = True
          self.absy2[event.stream.deviceIndex] = event.stream.scale(EventStream.axisRY, event.eventValue)
        elif event.eventCode == ABS_RZ:
          Handled = True
          self.absz2[event.stream.deviceIndex] = event.stream.scale(EventStream.axisRZ, event.eventValue)
        elif event.eventCode == ABS_HAT0X:
          Handled = True
          self.abshatx[event.stream.deviceIndex] = event.stream.scale(EventStream.axisHat0X, event.eventValue)
        elif event.eventCode == ABS_HAT0Y:
          Handled = True
          self.abshaty[event.stream.deviceIndex] = event.stream.scale(EventStream.axisHat0Y, event.eventValue)
        if Handled:
          if self.absHandler:
            self.absHandler(event.stream.deviceType, event.stream.deviceIndex,
              self.absx[event.stream.deviceIndex], self.absy[event.stream.deviceIndex], self.absz[event.stream.deviceIndex],
              self.absx2[event.stream.deviceIndex], self.absy2[event.stream.deviceIndex], self.absz2[event.stream.deviceIndex],
              self.abshatx[event.stream.deviceIndex], self.abshaty[event.stream.deviceIndex])
          ret = None
    finally:
      self.mutex.release()
    return ret

  def get_rel_movement(self, index):
    """
    Returns the accumulated REL (mouse or other relative device) movements
    since the last call.

    The returned value is a tuple: (X, Y, WHEEL, H-WHEEL, DIAL)
    """
    self.mutex.acquire()
    try:
      ret = (self.relx[index], self.rely[index], self.relv[index],
             self.relh[index], self.reld[index])

      self.relx[index] = 0
      self.rely[index] = 0
      self.relv[index] = 0
      self.relh[index] = 0
      self.reld[index] = 0
    finally:
      self.mutex.release()
    return ret

  def key_state(self, buttonCode):
    """
    Returns the last event value for the given key code.

    Key names can be converted to key codes using codeOf[str].
    If the key is pressed the returned value will be 1 (pressed) or 2 (held).
    If the key is not pressed, the returned value will be 0.
    """
    try:
      return self.buttons[buttonCode]
    except KeyError:
      return 0

  def clear_key(self, buttonCode):
    """
    Clears the  event value for the given key code.

    Key names can be converted to key codes using codeOf[str].
    This emulates a key-up but does not generate any events.
    """
    try:
      self.buttons[buttonCode] = 0
    except KeyError:
      pass

  def get_keys(self):
    """
    Returns the first of whichever keys have been pressed.

    Key names can be converted to key codes using codeOf[str].
    This emulates a key-up but does not generate any events.
    """
    k_list = []
    try:
      for k in self.buttons:
        if self.buttons[k] != 0:
          k_list.append(k)
      return k_list
    except KeyError:
      pass
    return k_list


########NEW FILE########
__FILENAME__ = EventStream
import fcntl
import os
import select

from six.moves import filter

from pi3d.event.Constants import *

from pi3d.event import ioctl
from pi3d.event import AbsAxisScaling
from pi3d.event import EventStruct
from pi3d.event import Format
from pi3d.util import Log

LOGGER = Log.logger(__name__)

EVIOCGRAB = ioctl._IOW(ord('E'), 0x90, "i")          # Grab/Release device

class EventStream(object):
  """
  encapsulates the event* file handling

  Each device is represented by a file in /dev/input called eventN, where N is
  a small number. (Actually, a keybaord is/can be represented by two such files.)
  Instances of this class open one of these files and provide means to read
  events from them.

  Class methods also exist to read from multiple files simultaneously, and
  also to grab and ungrab all instances of a given type.
  """
  AllStreams = [ ]
  axisX = 0
  axisY = 1
  axisZ = 2
  axisRX = 3
  axisRY = 4
  axisRZ = 5
  axisHat0X = 6
  axisHat0Y = 7
  axisHat1X = 8
  axisHat1Y = 9
  axisHat2X = 10
  axisHat2Y = 11
  axisHat3X = 12
  axisHat3Y = 13
  axisThrottle = 14
  axisRudder = 15
  axisWheel = 16
  axisGas = 17
  axisBrake = 18
  axisPressure = 19
  axisDistance = 20
  axisTiltX = 21
  axisTiltY = 22
  axisToolWidth = 23
  numAxes = 24

  axisToEvent = [ABS_X, ABS_Y, ABS_Z,  ABS_RX, ABS_RY,  ABS_RZ,
    ABS_HAT0X, ABS_HAT0Y, ABS_HAT1X, ABS_HAT1Y,
    ABS_HAT2X, ABS_HAT2Y, ABS_HAT3X, ABS_HAT3Y,
    ABS_THROTTLE, ABS_RUDDER, ABS_WHEEL, ABS_GAS, ABS_BRAKE,
    ABS_PRESSURE, ABS_DISTANCE, ABS_TILT_X, ABS_TILT_Y, ABS_TOOL_WIDTH]

  def __init__(self, index, deviceType):
    """
    Opens the given /dev/input/event file and grabs it.

    Also adds it to a class-global list of all existing streams.
    The index is a tuple: (deviceIndex, eventIndex). The deviceIndex
    can be used subsequently for differentiating multiple devices of the
    same type.
    """
    self.index = index[1]
    self.deviceIndex = index[0]
    self.deviceType = deviceType
    self.filename = "/dev/input/event"+str(self.index)
    self.filehandle = os.open(self.filename, os.O_RDWR)
    self.grab(True)
    self.grabbed = True
    EventStream.AllStreams.append(self)
    self.absInfo = [None] * EventStream.numAxes

  #def acquire_abs_info(self, axis):
  #  assert (axis < EventStream.numAxes), "Axis number out of range"
  #  self.absinfo[axis] = AbsAxisScaling(EventStream.axisToEvent[axis])

  def acquire_abs_info(self):
    """
    Acquires the axis limits for all the ABS axes.

    This will only be called for joystick-type devices.
    """
    for axis in range(EventStream.numAxes):
      self.absInfo[axis] = AbsAxisScaling.AbsAxisScaling(self, EventStream.axisToEvent[axis])

  def scale(self, axis, value):
    """
    Scale the given value according to the given axis.

    acquire_abs_info must have been previously called to acquire the data to
    do the scaling.
    """
    assert (axis < EventStream.numAxes), "Axis number out of range"
    if self.absInfo[axis]:
      return self.absInfo[axis].scale(value)
    else:
      return value

  def grab(self, grab=True):
    """
    Grab (or release) exclusive access to all devices of the given type.

    The devices are grabbed if grab is True and released if grab is False.

    All devices are grabbed to begin with. We might want to ungrab the
    keyboard for example to use it for text entry. While not grabbed, all key-down
    and key-hold events are filtered out.
    """
    #print "grab(", self, ",", grab,") =", 1 if grab else 0, "with 0x%x"%(EVIOCGRAB)
    fcntl.ioctl(self.filehandle, EVIOCGRAB, 1 if grab else 0)
    self.grabbed = grab
    #flush outstanding events
    #while self.next(): pass

  def __iter__(self):
    """
    Required to make this class an iterator
    """
    return self

  def next(self):
    """
    Returns the next waiting event.

    If no event is waiting, returns None.
    """
    ready = select.select([self.filehandle],[ ], [ ], 0)[0]
    if ready:
      s = os.read(self.filehandle, Format.EventSize)
      if s:
        event = EventStruct.EventStruct(self)
        event.decode(s)
        return event

    return None

  @classmethod
  def grab_by_type(self, deviceType, deviceIndex=None, grab=True, streams=None):
    """
    Grabs all streams of the given type.
    """
    if streams == None:
      streams = EventStream.AllStreams

    for x in streams:
      if x.deviceType == deviceType and (deviceIndex == None or
                                        x.deviceIndex == deviceIndex):
        x.grab(grab)

  @classmethod
  def allNext(cls, streams=None):
    """
    A generator fuction returning all waiting events in the given streams

    If the streams parameter is not given, then all streams are selected.
    """
    if streams == None:
      streams = EventStream.AllStreams

    selectlist = [x.filehandle for x in streams]
    ready = select.select(selectlist, [ ], [ ], 0)[0]
    if not ready: return
    while ready:
      for fd in ready:
        try:
          s = os.read(fd, Format.EventSize)
        except Exception as e:
          failed = getattr(cls, 'failed', None)
          if not failed:
            failed = set()
            setattr(cls, 'failed', failed)
          if fd not in failed:
            LOGGER.error("Couldn't read fd %d %s", fd, e)
            failed.add(fd)
          continue
        if s:
          for x in streams:
            if x.filehandle == fd:
              stream = x
              break
          event = EventStruct.EventStruct(stream)
          event.decode(s)
          yield event
      ready = select.select(selectlist, [ ], [ ], 0)[0]

  def __enter__(self):
    return self

  def release(self):
    """
    Ungrabs the file and closes it.
    """
    try:
      EventStream.AllStreams.remove(self)
      self.grab(False)
      os.close(self.filehandle)
    except:
      pass

  def __exit__(self, type, value, traceback):
    """
    Ungrabs the file and closes it.
    """
    self.release()

########NEW FILE########
__FILENAME__ = EventStruct
import struct

from pi3d.event import Format

class EventStruct(object):
  """
  A single event from the linux input event system.

  Events are tuples: (Time, Type, Code, Value)
  In addition we remember the stream it came from.

  Externally, only the unhandled event handler gets passed the whole event,
  but the SYN handler gets the code and value. (Also the keyboard handler, but
  those are renamed to key and value.)

  This class is responsible for converting the Linux input event structure into
  one of these objects and back again.
  """
  def __init__(self, stream, time=None, eventType=None, eventCode=None,
               eventValue=None):
    """
    Create a new event.

    Generally all but the stream parameter are left out; we will want to
    populate the object from a Linux input event using decode.
    """
    self.stream = stream
    self.time = time
    self.eventType = eventType
    self.eventCode = eventCode
    self.eventValue = eventValue

  def __str__(self):
    """
    Uses the stream to give the device type and whether it is currently grabbed.
    """
    return "Input event %s[%d], %d -- %f: 0x%x(0x%x) = 0x%x" % (
      self.stream.deviceType, self.stream.deviceIndex, self.stream.grabbed,
      self.time, self.eventType, self.eventCode, self.eventValue)

  def __repr__(self):
    return "EventStruct(%s, %f, 0x%x, 0x%x, 0x%x)" % (
      repr(self.stream), self.time, self.eventType, self.eventCode,
      self.eventValue)

  def encode(self):
    """
    Encode this event into a Linux input event structure.

    The output is packed into a string. It is unlikely that this function
    will be required, but it might as well be here.
    """
    tint = long(self.time)
    tfrac = long((self.time - tint)*1000000)
    return struct.pack(Format.Event, tsec, tfrac, self.eventType,
                       self.eventCode, self.eventValue)

  def decode(self, s):
    """
    Decode a Linux input event into the fields of this object.

    Arguments:
      *s*
        A binary structure packed into a string.
    """
    (tsec, tfrac,  self.eventType, self.eventCode,
     self.eventValue) = struct.unpack(Format.Event, s)

    self.time = tsec + tfrac / 1000000.0

########NEW FILE########
__FILENAME__ = FindDevices
import re
from .Constants import *

def test_bit(nlst, b):
  index = b / 32
  bit = b % 32
  if len(nlst) <= index:
    return False
  if nlst[index] & (1 << bit):
    return True
  else:
    return False


def EvToStr(events):
  s = [ ]
  if test_bit(events, EV_SYN):       s.append("EV_SYN")
  if test_bit(events, EV_KEY):       s.append("EV_KEY")
  if test_bit(events, EV_REL):       s.append("EV_REL")
  if test_bit(events, EV_ABS):       s.append("EV_ABS")
  if test_bit(events, EV_MSC):       s.append("EV_MSC")
  if test_bit(events, EV_LED):       s.append("EV_LED")
  if test_bit(events, EV_SND):       s.append("EV_SND")
  if test_bit(events, EV_REP):       s.append("EV_REP")
  if test_bit(events, EV_FF):        s.append("EV_FF" )
  if test_bit(events, EV_PWR):       s.append("EV_PWR")
  if test_bit(events, EV_FF_STATUS): s.append("EV_FF_STATUS")
    
  return s

class DeviceCapabilities(object):
  def __init__(self, firstLine, filehandle):
    self.EV_SYNevents = [ ]
    self.EV_KEYevents = [ ]
    self.EV_RELevents = [ ]
    self.EV_ABSevents = [ ]
    self.EV_MSCevents = [ ]
    self.EV_LEDevents = [ ]
    self.EV_SNDevents = [ ]
    self.EV_REPevents = [ ]
    self.EV_FFevents = [ ]
    self.EV_PWRevents = [ ]
    self.EV_FF_STATUSevents = [ ]
    self.eventTypes = [ ]
    
    match = re.search(".*Bus=([0-9A-Fa-f]+).*Vendor=([0-9A-Fa-f]+).*Product=([0-9A-Fa-f]+).*Version=([0-9A-Fa-f]+).*", firstLine)
    if not match:
      print("Do not understand device ID:", line)
      self.bus = 0
      self.vendor = 0
      self.product = 0
      self.version = 0
    else:
      self.bus = int(match.group(1), base=16)
      self.vendor = int(match.group(2), base=16)
      self.product = int(match.group(3), base=16)
      self.version = int(match.group(4), base=16)
    for line in filehandle:
      if len(line.strip()) == 0:
        break
      if line[0] == "N":
        match = re.search('Name="([^"]+)"', line)
        if match:
          self.name = match.group(1)
        else:
          self.name = "UNKNOWN"
      elif line[0] == "P":
        match = re.search('Phys=(.+)', line)
        if match:
          self.phys = match.group(1)
        else:
          self.phys = "UNKNOWN"
      elif line[0] == "S":
          match = re.search('Sysfs=(.+)', line)
          if match:
              self.sysfs = match.group(1)
          else:
              self.sysfs = "UNKNOWN"
      elif line[0] == "U":
        match = re.search('Uniq=(.*)', line)
        if match:
          self.uniq = match.group(1)
        else:
          self.uniq = "UNKNOWN"
      elif line[0] == "H":
        match = re.search('Handlers=(.+)', line)
        if match:
          self.handlers = match.group(1).split()
        else:
          self.handlers = [ ]
      elif line[:5] == "B: EV":
        eventsNums = [int(x,base=16) for x in line [6:].split()]
        eventsNums.reverse()
        self.eventTypes = eventsNums
      elif line[:6] == "B: KEY":
        eventsNums = [int(x,base=16) for x in line [7:].split()]
        eventsNums.reverse()
        self.EV_KEYevents = eventsNums
      elif line[:6] == "B: ABS":
        eventsNums = [int(x,base=16) for x in line [7:].split()]
        eventsNums.reverse()
        self.EV_ABSevents = eventsNums
      elif line[:6] == "B: MSC":
        eventsNums = [int(x,base=16) for x in line [7:].split()]
        eventsNums.reverse()
        self.EV_MSCevents = eventsNums
      elif line[:6] == "B: REL":
        eventsNums = [int(x,base=16) for x in line [7:].split()]
        eventsNums.reverse()
        self.EV_RELevents = eventsNums
      elif line[:6] == "B: LED":
        eventsNums = [int(x,base=16) for x in line [7:].split()]
        eventsNums.reverse()
        self.EV_LEDevents = eventsNums

    for handler in self.handlers:
      if handler[:5] == "event":
        self.eventIndex = int(handler[5:])

    self.isMouse = False
    self.isKeyboard = False
    self.isJoystick = False

  def doesProduce(self, eventType, eventCode):
    if not test_bit(self.eventTypes, eventType):
      return False
    if eventType == EV_SYN and test_bit(self.EV_SYNevents, eventCode): return True
    if eventType == EV_KEY and test_bit(self.EV_KEYevents, eventCode): return True
    if eventType == EV_REL and test_bit(self.EV_RELevents, eventCode): return True
    if eventType == EV_ABS and test_bit(self.EV_ABSevents, eventCode): return True
    if eventType == EV_MSC and test_bit(self.EV_MSCevents, eventCode): return True
    if eventType == EV_LED and test_bit(self.EV_LEDevents, eventCode): return True
    if eventType == EV_SND and test_bit(self.EV_SNDevents, eventCode): return True
    if eventType == EV_REP and test_bit(self.EV_REPevents, eventCode): return True
    if eventType == EV_FF  and test_bit(self.EV_FFevents, eventCode): return True
    if eventType == EV_PWR and test_bit(self.EV_PWRevents, eventCode): return True
    if eventType == EV_FF_STATUS and test_bit(self.EV_FF_STATUSevents, eventCode): return True
    return False
      
  def __str__(self):
    return self.name+"\nBus: "+str(self.bus)+" Vendor: "+str(self.vendor)+ \
        " Product: "+str(self.product)+" Version: "+str(self.version) + \
        "\nPhys: " + self.phys + "\nSysfs: " + self.sysfs + "\nUniq: " + self.uniq + \
        "\nHandlers: " + str(self.handlers) + " Event Index: "+ str(self.eventIndex) + \
        "\nKeyboard: " + str(self.isKeyboard) + " Mouse: " + str(self.isMouse) + \
        " Joystick: " + str(self.isJoystick) + \
        "\nEvents: " + str(EvToStr(self.eventTypes))
                
        
deviceCapabilities = [ ]

def get_devices(filename="/proc/bus/input/devices"):
  global deviceCapabilities
  with open("/proc/bus/input/devices", "r") as filehandle:
    for line in filehandle:
      if line[0] == "I":
        deviceCapabilities.append(DeviceCapabilities(line, filehandle))
              
  return deviceCapabilities
        
def find_devices(identifier, butNot= [ ]):
  """
  finds the event indecies of all devices that have the given identifier.

  The identifier is a string on the Handlers line of /proc/bus/input/devices.
  Keyboards use "kbd", mice use "mouse" and joysticks (and gamepads) use "js".

  Returns a list of integer indexes N, where /dev/input/eventN is the event
  stream for each device.

  If except is given it holds a list of tuples which the returned values should not match.

  All devices of each type are returned; if you have two mice, they will both
  be used.
  """
  ret = [ ]
  index = 0
  # print "Looking for", identifier
  with open("/proc/bus/input/devices", "r") as filehandle:
    for line in filehandle:
      if line[0] == "H":
        if identifier in line:
          # print line
          match = re.search("event([0-9]+)", line)
          eventindex = match and match.group(1)
          if eventindex:
            for old in butNot:
              if old[1] == int(eventindex):
                # print "Removing", old[1]
                break
              else:
                pass
                # print "No need to remove", old[1]
            else:
              ret.append((index, int(eventindex)))
              index += 1

  return ret

if __name__ == "__main__":
  devs = get_devices()
  for dev in devs:
    print(str(dev))
    print("   ABS: {}".format([x for x in range(64) if test_bit(dev.EV_ABSevents, x)]))
    print("   REL: {}".format([x for x in range(64) if test_bit(dev.EV_RELevents, x)]))
    print("   MSC: {}".format([x for x in range(64) if test_bit(dev.EV_MSCevents, x)]))
    print("   KEY: {}".format([x for x in range(512) if test_bit(dev.EV_KEYevents, x)]))
    print("   LED: {}".format([x for x in range(64) if test_bit(dev.EV_LEDevents, x)]))
    print()

########NEW FILE########
__FILENAME__ = Format
import struct

Event = 'llHHi'
EventSize = struct.calcsize(Event)

########NEW FILE########
__FILENAME__ = ioctl
#define _ASM_GENERIC_IOCTL_H
# I'm not claiming any copyright for transforming this from the above header file
# Copyright is with the original, so it's probably GPLv2.
#
# ioctl command encoding: 32 bits total, command in lower 16 bits,
# size of the parameter structure in the lower 14 bits of the
# upper 16 bits.
# Encoding the size of the parameter structure in the ioctl request
# is useful for catching programs compiled with old versions
# and to avoid overwriting user space outside the user buffer area.
# The highest 2 bits are reserved for indicating the ``access mode''.
# NOTE: This limits the max parameter size to 16kB -1 !
#
#
#
# The following is for compatibility across the various Linux
# platforms.  The generic ioctl numbering scheme doesn't really enforce
# a type field.  De facto, however, the top 8 bits of the lower 16
# bits are indeed used as a type field, so we might just as well make
# this explicit here.  Please be sure to use the decoding macros
# below from now on.
#

import struct
sizeof = struct.calcsize
_IOC_TYPECHECK = sizeof

_IOC_NRBITS	= 8
_IOC_TYPEBITS = 8

# 
# Let any architecture override either of the following before
# including this file.
# 

_IOC_SIZEBITS =	14
_IOC_DIRBITS = 2

_IOC_NRMASK	= ((1 << _IOC_NRBITS)-1)
_IOC_TYPEMASK =	((1 << _IOC_TYPEBITS)-1)
_IOC_SIZEMASK =	((1 << _IOC_SIZEBITS)-1)
_IOC_DIRMASK =	((1 << _IOC_DIRBITS)-1)

_IOC_NRSHIFT	= 0
_IOC_TYPESHIFT	= (_IOC_NRSHIFT+_IOC_NRBITS)
_IOC_SIZESHIFT	= (_IOC_TYPESHIFT+_IOC_TYPEBITS)
_IOC_DIRSHIFT	= (_IOC_SIZESHIFT+_IOC_SIZEBITS)

# 
# Direction bits, which any architecture can choose to override
# before including this file.
# 

_IOC_NONE	= 0
_IOC_WRITE	= 1
_IOC_READ	= 2

def _IOC(dir, type, nr, size):
 return int(((dir)  << _IOC_DIRSHIFT) |
        ((type) << _IOC_TYPESHIFT) |
        ((nr)   << _IOC_NRSHIFT) |
        ((size) << _IOC_SIZESHIFT))

# used to create numbers */
def _IO(type,nr):
  return _IOC(_IOC_NONE,(type),(nr),0)
def _IOR(type,nr,format):
  return _IOC(_IOC_READ,(type),(nr),(_IOC_TYPECHECK(format)))
def _IOW(type,nr,format):
  return _IOC(_IOC_WRITE,(type),(nr),(_IOC_TYPECHECK(format)))
def _IOWR(type,nr,format):
  return _IOC(_IOC_READ|_IOC_WRITE,(type),(nr),(_IOC_TYPECHECK(format)))
def _IOR_BAD(type,nr,format):
  return _IOC(_IOC_READ,(type),(nr),sizeof(format))
def _IOW_BAD(type,nr,format):
  return _IOC(_IOC_WRITE,(type),(nr),sizeof(format))
def _IOWR_BAD(type,nr,format):
  return _IOC(_IOC_READ|_IOC_WRITE,(type),(nr),sizeof(format))

# used to decode ioctl numbers.. */
def _IOC_DIR(nr):
  return (((nr) >> _IOC_DIRSHIFT) & _IOC_DIRMASK)
def _IOC_TYPE(nr):
  return (((nr) >> _IOC_TYPESHIFT) & _IOC_TYPEMASK)
def _IOC_NR(nr):
  return (((nr) >> _IOC_NRSHIFT) & _IOC_NRMASK)
def _IOC_SIZE(nr):
  return (((nr) >> _IOC_SIZESHIFT) & _IOC_SIZEMASK)

# ...and for the drivers/sound files... */

IOC_IN = (_IOC_WRITE << _IOC_DIRSHIFT)
IOC_OUT = (_IOC_READ << _IOC_DIRSHIFT)
IOC_INOUT = ((_IOC_WRITE|_IOC_READ) << _IOC_DIRSHIFT)
IOCSIZE_MASK = (_IOC_SIZEMASK << _IOC_SIZESHIFT)
IOCSIZE_SHIFT = (_IOC_SIZESHIFT)

#endif /* _ASM_GENERIC_IOCTL_H */

########NEW FILE########
__FILENAME__ = Keys
KEY_ESC = 1
KEY_1 = 2
KEY_2 = 3
KEY_3 = 4
KEY_4 = 5
KEY_5 = 6
KEY_6 = 7
KEY_7 = 8
KEY_8 = 9
KEY_9 = 10
KEY_0 = 11
KEY_MINUS = 12
KEY_EQUAL = 13
KEY_BACKSPACE = 14
KEY_TAB = 15
KEY_Q = 16
KEY_W = 17
KEY_E = 18
KEY_R = 19
KEY_T = 20
KEY_Y = 21
KEY_U = 22
KEY_I = 23
KEY_O = 24
KEY_P = 25
KEY_LEFTBRACE = 26
KEY_RIGHTBRACE = 27
KEY_ENTER = 28
KEY_LEFTCTRL = 29
KEY_A = 30
KEY_S = 31
KEY_D = 32
KEY_F = 33
KEY_G = 34
KEY_H = 35
KEY_J = 36
KEY_K = 37
KEY_L = 38
KEY_SEMICOLON = 39
KEY_APOSTROPHE = 40
KEY_GRAVE = 41
KEY_LEFTSHIFT = 42
KEY_BACKSLASH = 43
KEY_Z = 44
KEY_X = 45
KEY_C = 46
KEY_V = 47
KEY_B = 48
KEY_N = 49
KEY_M = 50
KEY_COMMA = 51
KEY_DOT = 52
KEY_SLASH = 53
KEY_RIGHTSHIFT = 54
KEY_KPASTERISK = 55
KEY_LEFTALT = 56
KEY_SPACE = 57
KEY_CAPSLOCK = 58
KEY_F1 = 59
KEY_F2 = 60
KEY_F3 = 61
KEY_F4 = 62
KEY_F5 = 63
KEY_F6 = 64
KEY_F7 = 65
KEY_F8 = 66
KEY_F9 = 67
KEY_F10 = 68
KEY_NUMLOCK = 69
KEY_SCROLLLOCK = 70
KEY_KP7 = 71
KEY_KP8 = 72
KEY_KP9 = 73
KEY_KPMINUS = 74
KEY_KP4 = 75
KEY_KP5 = 76
KEY_KP6 = 77
KEY_KPPLUS = 78
KEY_KP1 = 79
KEY_KP2 = 80
KEY_KP3 = 81
KEY_KP0 = 82
KEY_KPDOT = 83

KEY_ZENKAKUHANKAKU = 85
KEY_102ND = 86
KEY_F11 = 87
KEY_F12 = 88
KEY_RO = 89
KEY_KATAKANA = 90
KEY_HIRAGANA = 91
KEY_HENKAN = 92
KEY_KATAKANAHIRAGANA = 93
KEY_MUHENKAN = 94
KEY_KPJPCOMMA = 95
KEY_KPENTER = 96
KEY_RIGHTCTRL = 97
KEY_KPSLASH = 98
KEY_SYSRQ = 99
KEY_RIGHTALT = 100
KEY_LINEFEED = 101
KEY_HOME = 102
KEY_UP = 103
KEY_PAGEUP = 104
KEY_LEFT = 105
KEY_RIGHT = 106
KEY_END = 107
KEY_DOWN = 108
KEY_PAGEDOWN = 109
KEY_INSERT = 110
KEY_DELETE = 111
KEY_MACRO = 112
KEY_MUTE = 113
KEY_VOLUMEDOWN = 114
KEY_VOLUMEUP = 115
KEY_POWER = 116
KEY_KPEQUAL = 117
KEY_KPPLUSMINUS = 118
KEY_PAUSE = 119

KEY_KPCOMMA = 121
KEY_HANGUEL = 122
KEY_HANJA = 123
KEY_YEN = 124
KEY_LEFTMETA = 125
KEY_RIGHTMETA = 126
KEY_COMPOSE = 127

KEY_STOP = 128
KEY_AGAIN = 129
KEY_PROPS = 130
KEY_UNDO = 131
KEY_FRONT = 132
KEY_COPY = 133
KEY_OPEN = 134
KEY_PASTE = 135
KEY_FIND = 136
KEY_CUT = 137
KEY_HELP = 138
KEY_MENU = 139
KEY_CALC = 140
KEY_SETUP = 141
KEY_SLEEP = 142
KEY_WAKEUP = 143
KEY_FILE = 144
KEY_SENDFILE = 145
KEY_DELETEFILE = 146
KEY_XFER = 147
KEY_PROG1 = 148
KEY_PROG2 = 149
KEY_WWW = 150
KEY_MSDOS = 151
KEY_COFFEE = 152
KEY_DIRECTION = 153
KEY_CYCLEWINDOWS = 154
KEY_MAIL = 155
KEY_BOOKMARKS = 156
KEY_COMPUTER = 157
KEY_BACK = 158
KEY_FORWARD = 159
KEY_CLOSECD = 160
KEY_EJECTCD = 161
KEY_EJECTCLOSECD = 162
KEY_NEXTSONG = 163
KEY_PLAYPAUSE = 164
KEY_PREVIOUSSONG = 165
KEY_STOPCD = 166
KEY_RECORD = 167
KEY_REWIND = 168
KEY_PHONE = 169
KEY_ISO = 170
KEY_CONFIG = 171
KEY_HOMEPAGE = 172
KEY_REFRESH = 173
KEY_EXIT = 174
KEY_MOVE = 175
KEY_EDIT = 176
KEY_SCROLLUP = 177
KEY_SCROLLDOWN = 178
KEY_KPLEFTPAREN = 179
KEY_KPRIGHTPAREN = 180

KEY_F13 = 183
KEY_F14 = 184
KEY_F15 = 185
KEY_F16 = 186
KEY_F17 = 187
KEY_F18 = 188
KEY_F19 = 189
KEY_F20 = 190
KEY_F21 = 191
KEY_F22 = 192
KEY_F23 = 193
KEY_F24 = 194

KEY_PLAYCD = 200
KEY_PAUSECD = 201
KEY_PROG3 = 202
KEY_PROG4 = 203
KEY_SUSPEND = 205
KEY_CLOSE = 206
KEY_PLAY = 207
KEY_FASTFORWARD = 208
KEY_BASSBOOST = 209
KEY_PRINT = 210
KEY_HP = 211
KEY_CAMERA = 212
KEY_SOUND = 213
KEY_QUESTION = 214
KEY_EMAIL = 215
KEY_CHAT = 216
KEY_SEARCH = 217
KEY_CONNECT = 218
KEY_FINANCE = 219
KEY_SPORT = 220
KEY_SHOP = 221
KEY_ALTERASE = 222
KEY_CANCEL = 223
KEY_BRIGHTNESSDOWN = 224
KEY_BRIGHTNESSUP = 225
KEY_MEDIA = 226

KEY_UNKNOWN = 240

BTN_MISC = 0x100
BTN_0 = 0x100
BTN_1 = 0x101
BTN_2 = 0x102
BTN_3 = 0x103
BTN_4 = 0x104
BTN_5 = 0x105
BTN_6 = 0x106
BTN_7 = 0x107
BTN_8 = 0x108
BTN_9 = 0x109

BTN_MOUSE = 0x110
BTN_LEFT = 0x110
BTN_RIGHT = 0x111
BTN_MIDDLE = 0x112
BTN_SIDE = 0x113
BTN_EXTRA = 0x114
BTN_FORWARD = 0x115
BTN_BACK = 0x116
BTN_TASK = 0x117

BTN_JOYSTICK = 0x120
BTN_TRIGGER = 0x120
BTN_THUMB = 0x121
BTN_THUMB2 = 0x122
BTN_TOP = 0x123
BTN_TOP2 = 0x124
BTN_PINKIE = 0x125
BTN_BASE = 0x126
BTN_BASE2 = 0x127
BTN_BASE3 = 0x128
BTN_BASE4 = 0x129
BTN_BASE5 = 0x12a
BTN_BASE6 = 0x12b
BTN_DEAD = 0x12f

BTN_GAMEPAD = 0x130
BTN_A = 0x130
BTN_B = 0x131
BTN_C = 0x132
BTN_X = 0x133
BTN_Y = 0x134
BTN_Z = 0x135
BTN_TL = 0x136
BTN_TR = 0x137
BTN_TL2 = 0x138
BTN_TR2 = 0x139
BTN_SELECT = 0x13a
BTN_START = 0x13b
BTN_MODE = 0x13c
BTN_THUMBL = 0x13d
BTN_THUMBR = 0x13e

BTN_DIGI = 0x140
BTN_TOOL_PEN = 0x140
BTN_TOOL_RUBBER = 0x141
BTN_TOOL_BRUSH = 0x142
BTN_TOOL_PENCIL = 0x143
BTN_TOOL_AIRBRUSH = 0x144
BTN_TOOL_FINGER = 0x145
BTN_TOOL_MOUSE = 0x146
BTN_TOOL_LENS = 0x147
BTN_TOUCH = 0x14a
BTN_STYLUS = 0x14b
BTN_STYLUS2 = 0x14c
BTN_TOOL_DOUBLETAP = 0x14d
BTN_TOOL_TRIPLETAP = 0x14e

BTN_WHEEL = 0x150
BTN_GEAR_DOWN = 0x150
BTN_GEAR_UP = 0x151

KEY_OK = 0x160
KEY_SELECT = 0x161
KEY_GOTO = 0x162
KEY_CLEAR = 0x163
KEY_POWER2 = 0x164
KEY_OPTION = 0x165
KEY_INFO = 0x166
KEY_TIME = 0x167
KEY_VENDOR = 0x168
KEY_ARCHIVE = 0x169
KEY_PROGRAM = 0x16a
KEY_CHANNEL = 0x16b
KEY_FAVORITES = 0x16c
KEY_EPG = 0x16d
KEY_PVR = 0x16e
KEY_MHP = 0x16f
KEY_LANGUAGE = 0x170
KEY_TITLE = 0x171
KEY_SUBTITLE = 0x172
KEY_ANGLE = 0x173
KEY_ZOOM = 0x174
KEY_MODE = 0x175
KEY_KEYBOARD = 0x176
KEY_SCREEN = 0x177
KEY_PC = 0x178
KEY_TV = 0x179
KEY_TV2 = 0x17a
KEY_VCR = 0x17b
KEY_VCR2 = 0x17c
KEY_SAT = 0x17d
KEY_SAT2 = 0x17e
KEY_CD = 0x17f
KEY_TAPE = 0x180
KEY_RADIO = 0x181
KEY_TUNER = 0x182
KEY_PLAYER = 0x183
KEY_TEXT = 0x184
KEY_DVD = 0x185
KEY_AUX = 0x186
KEY_MP3 = 0x187
KEY_AUDIO = 0x188
KEY_VIDEO = 0x189
KEY_DIRECTORY = 0x18a
KEY_LIST = 0x18b
KEY_MEMO = 0x18c
KEY_CALENDAR = 0x18d
KEY_RED = 0x18e
KEY_GREEN = 0x18f
KEY_YELLOW = 0x190
KEY_BLUE = 0x191
KEY_CHANNELUP = 0x192
KEY_CHANNELDOWN = 0x193
KEY_FIRST = 0x194
KEY_LAST = 0x195
KEY_AB = 0x196
KEY_NEXT = 0x197
KEY_RESTART = 0x198
KEY_SLOW = 0x199
KEY_SHUFFLE = 0x19a
KEY_BREAK = 0x19b
KEY_PREVIOUS = 0x19c
KEY_DIGITS = 0x19d
KEY_TEEN = 0x19e
KEY_TWEN = 0x19f

KEY_DEL_EOL = 0x1c0
KEY_DEL_EOS = 0x1c1
KEY_INS_LINE = 0x1c2
KEY_DEL_LINE = 0x1c3

KEY_FN = 0x1d0
KEY_FN_ESC = 0x1d1
KEY_FN_F1 = 0x1d2
KEY_FN_F2 = 0x1d3
KEY_FN_F3 = 0x1d4
KEY_FN_F4 = 0x1d5
KEY_FN_F5 = 0x1d6
KEY_FN_F6 = 0x1d7
KEY_FN_F7 = 0x1d8
KEY_FN_F8 = 0x1d9
KEY_FN_F9 = 0x1da
KEY_FN_F10 = 0x1db
KEY_FN_F11 = 0x1dc
KEY_FN_F12 = 0x1dd
KEY_FN_1 = 0x1de
KEY_FN_2 = 0x1df
KEY_FN_D = 0x1e0
KEY_FN_E = 0x1e1
KEY_FN_F = 0x1e2
KEY_FN_S = 0x1e3
KEY_FN_B = 0x1e4

KEY_MAX = 0x1ff

########NEW FILE########
__FILENAME__ = Test

if __name__ == "__main__":
  def mouse_handler_func(sourceType, sourceIndex, x, y, v, h):
    print("Relative[{:d}] ({:d}, {:d}), ({:d}, {:d})".format(sourceIndex, x, y, v, h))
    pass

  def joystick_handler_func(sourceType, sourceIndex, x1, y1, z1, x2, y2, z2, hatx, haty):
    print("Absolute[{:d}] ({:6.3f}, {:6.3f}, {:6.3f}), ({:6.3f}, {:6.3f}, {:6.3f}), ({:2.0f}, {:2.0f})".format(sourceIndex, x1, y1, z1, x2, y2, z2, hatx, haty))
    pass

  def unhandled_handler_func(event):
    print("Unknown: {}".format(event))
    pass

  def key_handler_func(sourceType, sourceIndex, key, value):
    print("{}[{}]={}".format(nameOf[key], sourceIndex, value))
    pass

  def syn_handler_func(sourceType, sourceIndex, code, value):
    #print("SYN {} {}".format(code,value))
    pass

  inputs = InputEvents( key_handler_func, mouse_handler_func, joystick_handler_func, syn_handler_func, unhandled_handler_func)
  #inputs = InputEvents(key_handler_func)


  while not inputs.key_state("KEY_ESC"):
    inputs.do_input_events()
    if inputs.key_state("KEY_LEFTCTRL"):
      inputs.grab_by_type("keyboard", grab=False)
      print("Name:")
      s = input()
      print("Hello {}".format(s))
      inputs.grab_by_type("keyboard", True)
    if inputs.key_state("BTN_LEFT"):
      v = inputs.get_mouse_movement()
      if v != (0,0,0,0,0):
          print(v)
    if inputs.key_state("BTN_RIGHT"):
      v = inputs.get_mouse_movement(1)
      if v != (0,0,0,0,0):
          print(v)
    if inputs.key_state("BTN_TOP2"):      #gamepad L1
      print(inputs.get_joystick())        #gamepad Left Analogue
    if inputs.key_state("BTN_BASE"):      #gamepad R1
      print(inputs.get_joystickR())      #gamepad Right Analogue
    if inputs.key_state("BTN_PINKIE"):      #gamepad L2
      v = inputs.get_hat()          #gamepad Direction pad
      if v != (0,0):
          print(v)
    if inputs.key_state("BTN_BASE2"):      #gamepad R2
      print(inputs.get_joystickR(1))      #gamepad Right Analogue (2nd device)


########NEW FILE########
__FILENAME__ = Keyboard
from __future__ import absolute_import, division, print_function, unicode_literals

import curses, termios, fcntl, sys, os, platform

from pi3d.constants import *

if PLATFORM != PLATFORM_PI:
  from pyxlib import x

USE_CURSES = True

"""Non-blocking keyboard which requires curses and only works on the current
terminal window or session.
"""
class CursesKeyboard(object):
  def __init__(self):
    self.key = curses.initscr()
    curses.cbreak()
    curses.noecho()
    self.key.keypad(1)
    self.key.nodelay(1)

  def read(self):
    return self.key.getch()

  def close(self):
    curses.nocbreak()
    self.key.keypad(0)
    curses.echo()
    curses.endwin()

  def __del__(self):
    try:
      self.close()
    except:
      pass


"""Blocking keyboard which doesn't require curses and gets any keyboard inputs
regardless of which window is in front.
From http://stackoverflow.com/a/6599441/43839
"""
class SysKeyboard(object):
  def __init__(self):
    self.fd = sys.stdin.fileno()
    # save old state
    self.flags_save = fcntl.fcntl(self.fd, fcntl.F_GETFL)
    self.attrs_save = termios.tcgetattr(self.fd)
    # make raw - the way to do this comes from the termios(3) man page.
    attrs = list(self.attrs_save) # copy the stored version to update
    # iflag
    attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK
                  | termios.ISTRIP | termios.INLCR | termios. IGNCR
                  | termios.ICRNL | termios.IXON )
    # oflag
    attrs[1] &= ~termios.OPOST
    # cflag
    attrs[2] &= ~(termios.CSIZE | termios. PARENB)
    attrs[2] |= termios.CS8
    # lflag
    attrs[3] &= ~(termios.ECHONL | termios.ECHO | termios.ICANON
                  | termios.ISIG | termios.IEXTEN)
    termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
    # turn off non-blocking
    fcntl.fcntl(self.fd, fcntl.F_SETFL, self.flags_save & ~os.O_NONBLOCK)

  def read(self):
    try:
      return ord(sys.stdin.read())
    except KeyboardInterrupt:
      return 0

  def close(self):
    termios.tcsetattr(self.fd, termios.TCSAFLUSH, self.attrs_save)
    fcntl.fcntl(self.fd, fcntl.F_SETFL, self.flags_save)

  def __del__(self):
    try:
      self.close()
    except:
      pass

"""Keyboard using x11 functionality
"""
class x11Keyboard(object):
  KEYBOARD = [[0, ""], [0, ""], [0, ""], [0, ""], [0, ""],
            [0, ""], [0, ""], [0, ""], [0, ""], [27, "Escape"],
            [49, "1"], [50, "2"], [51, "3"], [52, "4"], [53, "5"],
            [54, "6"], [55, "7"], [56, "8"], [57, "9"], [48, "0"],
            [45, "-"], [61, "="], [8, "BackSpace"], [9, "Tab"], [113, "q"],
            [119, "w"], [101, "e"], [114, "r"], [116, "t"], [121, "y"],
            [117, "u"], [105, "i"], [111, "o"], [112, "p"], [91, "["],
            [93, "]"], [13, "Return"], [0, "Control_L"], [97, "a"], [115, "s"],
            [100, "d"], [102, "f"], [103, "g"], [104, "h"], [106, "j"],
            [107, "k"], [108, "l"], [59, ";"], [39, "'"], [96, "`"],
            [0, "Shift_L"], [35, "#"], [122, "z"], [120, "x"], [99, "c"],
            [118, "v"], [98, "b"], [110, "n"], [109, "m"], [44, ","],
            [46, "."], [47, "/"], [0, "Shift_R"], [0, ""], [0, "Alt_L"],
            [32, "space"], [0, "Caps"], [145, "F1"], [146, "F2"], [147, "F3"],
            [148, "F4"], [149, "F5"], [150, "F6"], [151, "F7"], [152, "F8"],
            [153, "F9"], [154, "F10"], [0, "Num_Lock"], [0, ""], [0, ""],
            [0, ""], [0, ""], [0, ""], [0, ""], [0, ""],
            [0, ""], [0, ""], [0, ""], [0, ""], [0, ""],
            [0, ""], [0, ""], [0, ""], [0, ""], [92, "\\"],
            [155, "F11"], [156, "F12"], [0, ""], [0, ""], [0, ""],
            [0, ""], [0, ""], [0, ""], [0, ""], [13, "KP_Enter"],
            [0, "Control_R"], [0, ""], [0, ""], [0, "Alt_R"], [0, ""],
            [129, "Home"], [134, "Up"], [130, "Page_Up"], [136, "Left"], [137, "Right"],
            [132, "End"], [135, "Down"], [133, "Page_Down"], [128, "Insert"], [131, "DEL"]]

  def __init__(self):
    from pi3d.Display import Display
    self.display = Display.INSTANCE
    self.key_num = 0
    self.key_code = ""

  def _update_event(self):
    if not self.display: #Because DummyTkWin Keyboard instance created before Display!
      from pi3d.Display import Display
      self.display = Display.INSTANCE
    n = len(self.display.event_list)
    for i, e in enumerate(self.display.event_list):
      if e.type == x.KeyPress or e.type == x.KeyRelease: #TODO not sure why KeyRelease needed!
        self.display.event_list.pop(i)
        self.key_num = self.KEYBOARD[e.xkey.keycode][0]
        self.key_code = self.KEYBOARD[e.xkey.keycode][1]
        return True
    return False

  def read(self):
    if self._update_event():
      return self.key_num
    else:
      return -1

  def read_code(self):
    if self._update_event():
      return self.key_code
    else:
      return ""

  def close(self):
    pass

  def __del__(self):
    try:
      self.close()
    except:
      pass

def Keyboard(use_curses=USE_CURSES):
  if PLATFORM != PLATFORM_PI:
    return x11Keyboard()
  else:
    return CursesKeyboard() if use_curses else SysKeyboard()


########NEW FILE########
__FILENAME__ = Light
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.util.DefaultInstance import DefaultInstance

class Light(DefaultInstance):
  """ Holds information about lighting to be used in shaders """
  def __init__(self,
               lightpos=(10, -10, 20),
               lightcol=(1.0, 1.0, 1.0),
               lightamb=(0.1, 0.1, 0.2)):
    """ set light values. These are set in Shape.unif as part of the Shape
    constructor. They can be changed using Shape.set_light()
    The pixel shade is calculated as::

      (lightcol * texture) * dot(lightpos, -normal) + (lightamb * texture)

    where * means component multiplying if between two vectors and dot() is
    the dot product of two vectors.

    Arguments:
      *lightpos*
        tuple (x,y,z) vector direction *from* the light i.e. an object at position
        (0,0,0) would appear to be lit from a light at (-3,4,-5) (left, above and
        nearer) if lightpos=(3,-4,5)
      *lightcol*
        tuple (r,g,b) defines shade and brightness
      *lightamb*
        tuple (r,g,b) ambient lighting multiplier
    """
    super(Light, self).__init__()
    self.lightpos = lightpos
    self.lightcol = lightcol
    self.lightamb = lightamb

  def position(self, lightpos):
    self.lightpos = lightpos

  def color(self, lightcol):
    self.lightcol = lightcol

  def ambient(self, lightamb):
    self.lightamb = lightamb

  @staticmethod
  def _default_instance():
    return Light()


########NEW FILE########
__FILENAME__ = loaderEgg
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import re, os

from pi3d import *
from random import randint
from six.moves import xrange
from six import advance_iterator

from pi3d.Texture import Texture
from pi3d.Buffer import Buffer

#########################################################################################
#
# this block added by paddy gaunt 15 June 2012
# Copyright (c) Paddy Gaunt, 2012
#
#########################################################################################
#######################################################################
class vertex():
  def __init__(self, coords_in, UVcoords_in, normal_in):
    self.coords = coords_in
    self.UVcoords = UVcoords_in
    # self.UVtangent = UVtangent_in
    # self.UVbinormal = UVbinormal_in
    self.normal = normal_in

########################################################################
class polygon():
  def __init__(self, normal_in, rgba_in, MRef_in, TRef_in, vertexRef_in, vpkey_in):
    self.normal = [] #should always be three
    for nVal in normal_in:
      self.normal.append(nVal)

    self.rgba = [] #should always be four
    for rgbVal in rgba_in:
      self.rgba.append(rgbVal)

    self.MRef = MRef_in

    self.TRef = TRef_in

    self.vref = [] # variable number of indices
    for v in vertexRef_in:
      self.vref.append(v)

    self.vpKey = vpkey_in

########################################################################


def loadFileEGG(model, fileName):
  """Loads an panda3d egg file to produce Buffer object
  as part of a Shape.

  Arguments:
    *model*
      Model object to add to.
    *fileName*
      Path and name of egg file relative to program file.

  """
  model.coordinateSystem = "Y-up"
  model.materialList = {}
  model.textureList = {}
  model.vertexGroupList = {}
  model.vertexList = []
  model.polygonList = []
  model.childModelList = []
  model.parentModel = None
  model.childModel = [] # don't really need parent and child pointers but will speed up traversing tree
  model.vNormal = False
  model.vGroup = {} # holds the information for each vertex group

  # read in the file and parse into some arrays

  if fileName[0] != '/':
    fileName = sys.path[0] + '/' + fileName
  filePath = os.path.split(os.path.abspath(fileName))[0]
  if VERBOSE:
    print(filePath)
  f = open(fileName, 'r')
  l = f.read() # whole thing as a string in memory this will only work for reasonably small files!!!

  ############### function to parse file as one off process to avoid re-traversing string #########
  # convertes the '<a> b { c <d> e {f} <g> h {i} }' structure
  # into nested arrays ['a', 'b', 'c',[['d','e','',['','','f',[]]],['g','h','',['','','i',[]]]]]
  def pRec(x, bReg, l, i):
    while 1:
      try:
        nxtFind = advance_iterator(bReg)
        j = nxtFind.start()
      except:
        return i+1
      c = l[j]
      if c == "<": # add entry to array at this level
        if len(x[3]) == 0: x[2] = l[i:j].strip() # text after "{" and before "<Tabxyz>"
        i = j+1 # save marker for start of descriptor
        x[3].append(["", "", "", []])

      elif c == "{":
        xn = x[3][len(x[3])-1]
        tx = l[i-1:j].strip().split()
        xn[0] = tx[0] #x[0] & x[1] is the "<Tabxyz>" & "123" prior to "{"
        xn[1] = tx[1] if len(tx) > 1 else ""
        i = pRec(xn, bReg, l, j+1)
      else: #i.e. c="}" # go up one level of recursion
        if len(x[3]) == 0: x[2] = l[i:j].strip()
        return j+1
  ################### end of pRec #################

  ####### go through all the nested <Groups> ####################
  def groupDrill(gp, np):
    structVList = {}
    offsetVList = {}
    structPList = []
    offset = 0
    #numv = 0
    #numi = 0
    for x in gp:
      if len(x) == 0: continue
      if ("<Group>" in x[0]):
        if len(x[1]) > 0:
          nextnp = np+x[1]
        else:
          nextnp = np+str(randint(10000, 99999))
        groupDrill(x[3], nextnp)
      else:
        #build vertex, polygon, normal, triangles, UVs etc etc
        if "<VertexPool>" in x[0]:
          vp = x[1]
          structVList[vp] = []
          offsetVList[vp] = offset
          for v in x[3]:
            #if "<Vertex>" in v[0]: #try with this test first!
            coords = [float(n) for n in v[2].strip().split()] # before first < error if no coords!
            # texture mapping
            UVcoords = []
            normal = []
            for u in v[3]:
              if "<UV>" in u[0]: UVcoords = [float(n) for n in u[2].strip().split()]
              #TODO get UVtangent and UVbinormal out of UVset (and use them!)
              # if ("<Tangent>" in vList[v]): UVtangent = [float(n) for n in (extBracket("<Tangent>", vList[v]))[0].split()] # not sure how to use this at this stage
              #else: UVtangent = []
              # if ("<Binormal>" in vList[v]): UVbinormal = [float(n) for n in (extBracket("<Binormal>", vList[v]))[0].split()] # not sure how to use this at this stage
              #else: UVbinormal = []
              # normals, used in 'smoothing' edges between polygons
              if "<Normal>" in u[0]: normal = [float(n) for n in u[2].strip().split()]
            vInt = int(v[1])
            while (len(structVList[vp]) < (vInt+1)): structVList[vp].append("")
            structVList[vp][vInt] = (vertex(coords, UVcoords, normal))
            offset += 1
    #
      # now go through splitting out the Polygons from this Group same level as vertexGroup
      if "<Polygon>" in x[0]:
        normal = []
        rgba = []
        MRef = ""
        TRef = ""
        for p in x[3]:
          if ("<Normal>" in p[0]): normal = [float(n) for n in p[2].strip().split()]
          if ("<RGBA>" in p[0]): rgba = [float(n) for n in p[2].strip().split()]
          if ("<MRef>" in p[0]): MRef = p[2].strip()
          if ("<TRef>" in p[0]): TRef = p[2].strip()
          if ("<VertexRef>" in p[0]):
            vref = []
            for n in p[2].strip().split():
              vref.append(int(n))
              #numv += 1
              #numi += 3
            #numi -= 6 # number of corners of triangle = (n-2)*3 where n is the number of corners of face
            vpKey = p[3][0][2].strip() # ought to do a for r in p[3]; if "Ref in...
        # add to list
        #while (len(structPList) < (p+1)): structPList.append("")
        #
        structPList.append(polygon(normal, rgba, MRef, TRef, vref, vpKey))

    # now go through the polygons in order of vertexPool+id, trying to ensure that the polygon arrays in each group are built in the order of vertexPool names
    # only cope with one material and one texture per group
    #numv -= 1
    #numi -= 1
    g_vertices = []
    g_normals = []
    g_tex_coords = []
    g_indices = []
    nv = 0 # vertex counter in this material
    #ni = 0 # triangle vertex count in this material

    gMRef = ""
    gTRef = ""
    nP = len(structPList)
    for p in xrange(nP):
      if (len(structPList[p].MRef) > 0): gMRef = structPList[p].MRef
      else: gMRef = ""
      if (len(structPList[p].TRef) > 0): gTRef = structPList[p].TRef
      else: gTRef = ""

      vpKey = structPList[p].vpKey
      vref = structPList[p].vref
      startV = nv
      for j in vref:

        if (len(structVList[vpKey][j].normal) > 0): model.vNormal = True
        else: model.vNormal = False
        if model.coordinateSystem == "z-up":
          thisV = [structVList[vpKey][j].coords[1], structVList[vpKey][j].coords[2], -structVList[vpKey][j].coords[0]]
          if model.vNormal:
            thisN = [structVList[vpKey][j].normal[1], structVList[vpKey][j].normal[2], -structVList[vpKey][j].normal[0]]
        else:
          thisV = [structVList[vpKey][j].coords[0], structVList[vpKey][j].coords[1], -structVList[vpKey][j].coords[2]]
          if model.vNormal:
            thisN = [structVList[vpKey][j].normal[0], structVList[vpKey][j].normal[1], -structVList[vpKey][j].normal[2]]
        g_vertices.append(thisV)
        if model.vNormal: nml = thisN
        else: nml = structPList[p].normal
        g_normals.append(nml)
        uvc = structVList[vpKey][j].UVcoords
        if (len(uvc) == 2):
          g_tex_coords.append(uvc)
        else:
          g_tex_coords.append([0.0, 0.0])
        nv += 1
      n = nv - startV - 1
      for j in range(1, n):
        g_indices.append((startV, startV + j + 1, startV + j))

    ilen = len(g_vertices)
    if ilen > 0:
      if len(g_normals) != len(g_vertices):
        g_normals = None # force Buffer.__init__() to generate normals
      model.buf.append(Buffer(model, g_vertices, g_tex_coords, g_indices, g_normals))
      n = len(model.buf) - 1
      model.vGroup[np] = n

      model.buf[n].indicesLen = ilen
      model.buf[n].material = (0.0, 0.0, 0.0, 0.0)
      model.buf[n].ttype = GL_TRIANGLES

      # load the texture file TODO check if same as previously loaded files (for other loadModel()s)
      if (gTRef in model.textureList):
        model.buf[model.vGroup[np]].textures = [model.textureList[gTRef]["texID"]]
        model.buf[model.vGroup[np]].texFile = model.textureList[gTRef]["filename"]
      else:
        model.buf[model.vGroup[np]].textures = []
        model.buf[model.vGroup[np]].texFile = None
        #TODO  don't create this array if texture being used but should be able to combine
        if (gMRef in model.materialList):
          redVal = float(model.materialList[gMRef]["diffr"])
          grnVal = float(model.materialList[gMRef]["diffg"])
          bluVal = float(model.materialList[gMRef]["diffb"])
          model.buf[model.vGroup[np]].material = (redVal, grnVal, bluVal, 1.0)
          model.buf[model.vGroup[np]].unib[3:6] = [redVal, grnVal, bluVal]

        else: model.buf[model.vGroup[np]].material = (0.0, 0.0, 0.0, 0.0)
    ####### end of groupDrill function #####################

  bReg = re.finditer('[{}<]', l)
  xx = ["", "", "", []]
  pRec(xx, bReg, l, 0)
  l = None #in case it's running out of memory?
  f.close()

  for x in xx[3]:
    if "<Texture>" in x[0]:
      model.textureList[x[1]] = {}
      for i in xrange(len(x[3])): model.textureList[x[1]][x[3][i][1]] = x[3][i][2]
      model.textureList[x[1]]["filename"] = x[2].strip("\"")
      if VERBOSE:
        print(filePath, model.textureList[x[1]]["filename"])
      model.textureList[x[1]]["texID"] = Texture(os.path.join(filePath, model.textureList[x[1]]["filename"]), False, True) # load from file
    if "<CoordinateSystem>" in x[0]:
      model.coordinateSystem = x[2].lower()
    if "<Material>" in x[0]:
      model.materialList[x[1]] = {}
      for i in xrange(len(x[3])): model.materialList[x[1]][x[3][i][1]] = x[3][i][2]
    if "<Group>" in x[0]:
      groupDrill(x[3], x[1])

########NEW FILE########
__FILENAME__ = loaderObj
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import os

from pi3d.constants import *
from pi3d.loader.parse_mtl import parse_mtl
from pi3d.Texture import Texture
from pi3d.Buffer import Buffer
from pi3d.util import Log

LOGGER = Log.logger(__name__)

#########################################################################################
#
# this block added by paddy gaunt 22 August 2012
# Copyright (c) Paddy Gaunt, 2012
# Chunks of this code are based on https://github.com/mrdoob/three.js/ by
# AlteredQualia http://alteredqualia.com
#
#########################################################################################


#########################################################################################
def parse_vertex(text):
  """Parse text chunk specifying single vertex.

  Possible formats:
  *  vertex index
  *  vertex index / texture index
  *  vertex index / texture index / normal index
  *  vertex index / / normal index
  """

  v = 0
  t = 0
  n = 0

  chunks = text.split("/")

  v = int(chunks[0])
  if len(chunks) > 1:
    if chunks[1]:
      t = int(chunks[1])
  if len(chunks) > 2:
    if chunks[2]:
      n = int(chunks[2])

  return { 'v':v, 't':t, 'n':n }

#########################################################################################
def loadFileOBJ(model, fileName):
  """Loads an obj file with associated mtl file to produce Buffer object
  as part of a Shape. Arguments:
    *model*
      Model object to add to.
    *fileName*
      Path and name of obj file relative to program file.
  """
  model.coordinateSystem = "Y-up"
  model.parent = None
  model.childModel = [] # don't really need parent and child pointers but will speed up traversing tree
  model.vNormal = False
  model.vGroup = {} # holds the information for each vertex group

  # read in the file and parse into some arrays

  if fileName[0] != '/':
    fileName = sys.path[0] + '/' + fileName
  filePath = os.path.split(os.path.abspath(fileName))[0]
  print(filePath)
  f = open(fileName, 'r')

  vertices = []
  normals = []
  uvs = []

  faces = {}

  materials = {}
  material = ""
  mcounter = 0
  mcurrent = 0
  numv = [] #number of vertices for each material (nb each vertex will have three coords)
  numi = [] #number of indices (triangle corners) for each material

  mtllib = ""

  # current face state
  group = 0
  objct = 0
  smooth = 0

  for l in f:
    chunks = l.split()
    if len(chunks) > 0:

      # Vertices as (x,y,z) coordinates
      # v 0.123 0.234 0.345
      if chunks[0] == "v" and len(chunks) >= 4:
        x = float(chunks[1])
        y = float(chunks[2])
        z = -float(chunks[3]) # z direction away in gl es 2.0 shaders
        vertices.append((x, y, z))

      # Normals in (x, y, z) form; normals might not be unit
      # vn 0.707 0.000 0.707
      if chunks[0] == "vn" and len(chunks) >= 4:
        x = float(chunks[1])
        y = float(chunks[2])
        z = -float(chunks[3]) # z direction away in gl es 2.0 shaders
        normals.append((x, y, z))

      # Texture coordinates in (u,v)
      # vt 0.500 -1.352
      if chunks[0] == "vt" and len(chunks) >= 3:
        u = float(chunks[1])
        v = float(chunks[2])
        uvs.append((u, v))

      # Face
      if chunks[0] == "f" and len(chunks) >= 4:
        vertex_index = []
        uv_index = []
        normal_index = []


        # Precompute vert / normal / uv lists
        # for negative index lookup
        vertlen = len(vertices) + 1
        normlen = len(normals) + 1
        uvlen = len(uvs) + 1

        if len(numv) < (mcurrent+1): numv.append(0)
        if len(numi) < (mcurrent+1): numi.append(0)

        for v in chunks[1:]:
          numv[mcurrent] += 1
          numi[mcurrent] += 3
          vertex = parse_vertex(v)
          if vertex['v']:
            if vertex['v'] < 0:
              vertex['v'] += vertlen
            vertex_index.append(vertex['v'])
          if vertex['t']:
            if vertex['t'] < 0:
              vertex['t'] += uvlen
            uv_index.append(vertex['t'])
          if vertex['n']:
            if vertex['n'] < 0:
              vertex['n'] += normlen
            normal_index.append(vertex['n'])
        numi[mcurrent] -= 6 # number of corners of triangle = (n-2)*3 where n is the number of corners of face
        if not mcurrent in faces: faces[mcurrent] = []

        faces[mcurrent].append({
          'vertex':vertex_index,
          'uv':uv_index,
          'normal':normal_index,

          'group':group,
          'object':objct,
          'smooth':smooth,
          })

      # Group
      if chunks[0] == "g" and len(chunks) == 2:
        group = chunks[1]

      # Object
      if chunks[0] == "o" and len(chunks) == 2:
        objct = chunks[1]

      # Materials definition
      if chunks[0] == "mtllib" and len(chunks) == 2:
        mtllib = chunks[1]

      # Material
      if chunks[0] == "usemtl":
        if len(chunks) > 1:
          material = chunks[1]
        else:
          material = ""
        if not material in materials:
          mcurrent = mcounter
          materials[material] = mcounter
          mcounter += 1
        else:
          mcurrent = materials[material]

      # Smooth shading
      if chunks[0] == "s" and len(chunks) == 2:
        smooth = chunks[1]
        
  if VERBOSE:
    print("materials:  ", materials)
    print("numv: ", numv)
    
  for g in faces:
    numv[g] -= 1
    numi[g] -= 1

    g_vertices = []
    g_normals = []
    g_tex_coords = []
    g_indices = []
    i = 0 # vertex counter in this material
    if VERBOSE:
      print("len uv=", len(vertices))
    for f in faces[g]:
      iStart = i
      length = len(f['vertex'])
      length_n = len(f['normal'])
      #for component in 'normal', 'uv':
      #  if length > len(f[component]):
      #    LOGGER.error('There were more vertices than %ss: %d > %d',
      #                 component, length, len(f[component]))
      #    length = len(f[component])

      for v in range(length):
        g_vertices.append(vertices[f['vertex'][v] - 1])
        if length_n == length: #only use normals if there is one for each vertex
          g_normals.append(normals[f['normal'][v] - 1])
        if (len(f['uv']) > 0 and len(uvs[f['uv'][v] - 1]) == 2):
          g_tex_coords.append(uvs[f['uv'][v] - 1])
        i += 1
      n = i - iStart - 1
      for t in range(1, n):
        g_indices.append((iStart, iStart + t + 1, iStart + t))
    if len(g_normals) != len(g_vertices):
      g_normals = None # force Buffer.__init__() to generate normals
    model.buf.append(Buffer(model, g_vertices, g_tex_coords, g_indices, g_normals))
    n = len(model.buf) - 1
    model.vGroup[g] = n

    model.buf[n].indicesLen = len(model.buf[n].indices)
    model.buf[n].material = (0.0, 0.0, 0.0, 0.0)
    model.buf[n].ttype = GL_TRIANGLES

    if VERBOSE:
      print()
      print("indices=", len(model.buf[n].indices))
      print("vertices=", len(model.buf[n].vertices))
      print("normals=", len(model.buf[n].normals))
      print("tex_coords=", len(model.buf[n].tex_coords))

  try:
    material_lib = parse_mtl(open(os.path.join(filePath, mtllib), 'r'))
    for m in materials:
      if VERBOSE:
        print(m)
      if 'mapDiffuse' in material_lib[m]:
        tfileName = material_lib[m]['mapDiffuse']
        model.buf[model.vGroup[materials[m]]].texFile = tfileName
        model.buf[model.vGroup[materials[m]]].textures = [Texture(filePath + '/' + tfileName, blend=False, flip=True)] # load from file
      else:
        model.buf[model.vGroup[materials[m]]].texFile = None
        model.buf[model.vGroup[materials[m]]].textures = []
        if 'colorDiffuse' in material_lib[m]:#TODO don't create this array if texture being used though not exclusive.
        #TODO check this works with appropriate mtl file
          redVal = material_lib[m]['colorDiffuse'][0]
          grnVal = material_lib[m]['colorDiffuse'][1]
          bluVal = material_lib[m]['colorDiffuse'][2]
          model.buf[model.vGroup[materials[m]]].material = (redVal, grnVal, bluVal, 1.0)
          model.buf[model.vGroup[materials[m]]].unib[3:6] = [redVal, grnVal, bluVal]
  except:
    print('no material specified')

########NEW FILE########
__FILENAME__ = parse_mtl
from collections import namedtuple

from pi3d.util import Log

RAISE_EXCEPTION_ON_ERROR = True
LOGGER = Log.logger(__name__)

def _error(args, exception=None):
  LOGGER.error(*args)
  if RAISE_EXCEPTION_ON_ERROR:
    raise exception or Exception()

class Materials(object):
  NEW_MATERIAL_CHUNK = 'newmtl'

  float3_f = lambda x, y, z: [float(x), float(y), float(z)]
  float_f = lambda x: float(x)
  int_f = lambda x: int(x)
  str_f = lambda x: str(x)

  Prop = namedtuple('Prop', ['name', 'func'])
  PROPERTIES = {
    'Ka': Prop('colorAmbient', float3_f),
    'Kd': Prop('colorDiffuse', float3_f),
    'Ks': Prop('colorSpecular', float3_f),
    'Ni': Prop('opticalDensity', float_f),
    'Ns': Prop('specularCoef', float_f),
    'Tr': Prop('transparency', float_f),
    'bump': Prop('mapBump', str_f),
    'd': Prop('transparency', float_f),
    'illum': Prop('illumination', int_f),
    'map_Ka': Prop('mapAmbient', str_f),
    'map_Kd': Prop('mapDiffuse', str_f),
    'map_Ks': Prop('mapSpecular', str_f),
    'map_bump': Prop('mapBump', str_f),
    'map_d': Prop('mapAlpha', str_f),
    }

  def __init__(self):
    self.identifier = None
    self.materials = {}
    self.material = {}

  def parse_lines(self, lines):
    for line in lines:
      self.parse_line(line)
    return self.materials

  def parse_line(self, line):
    line = line.strip()
    if not line.startswith('#'):
      chunks = line.strip().split()
      if chunks:
        name = chunks[0]
        args = chunks[1:]
        if name == Materials.NEW_MATERIAL_CHUNK:
          self.set_identifier(args, line)
        else:
          self.set_property(name, args)

  def set_identifier(self, args, line):
    if not args:
      self.identifier = ''
    else:
      self.identifier = args[0].strip()
      if len(args) > 1:
        LOGGER.warning('too many arguments in identifier line "%s"', line)
    self.material = self.materials.get(self.identifier, {})
    self.materials[self.identifier] = self.material

  def set_property(self, name, args):
    prop = Materials.PROPERTIES.get(name, None)
    if not prop:
      LOGGER.error('ERROR: Don\'t understand property "%s"', name)
      if RAISE_EXCEPTION_ON_ERROR:
        raise Exception()
    else:
      if prop.name in self.material:
        LOGGER.warning('duplicate property %s in %s', prop.name, name)
      try:
        self.material[prop.name] = prop.func(*args)
      except:
        LOGGER.error('Couldn\'t set %s with args "%s"', name, args)
        if RAISE_EXCEPTION_ON_ERROR:
          raise

def parse_mtl(lines):
  """Parse MTL file.
  """
  return Materials().parse_lines(lines)

########NEW FILE########
__FILENAME__ = parse_mtl_test
import unittest

from pi3d.loader.parse_mtl import parse_mtl

class ParseMtlTest(unittest.TestCase):
  def setUp(self):
    pass

  def test_cow(self):
    self.assertEqual(COW_RESULT, parse_mtl(COW_MTL.splitlines()))

  def test_teapot(self):
    self.assertEqual(TEAPOT_RESULT, parse_mtl(TEAPOT_MTL.splitlines()))

if __name__ == '__main__':
    unittest.main()

COW_MTL = """
# Blender3D MTL File: LD_COW_CC0_2012.blend
# Material Count: 1
newmtl Material_rock1.jpg
Ns 96.078431
Ka 0.000000 0.000000 0.000000
Kd 0.471461 0.471461 0.471461
Ks 0.500000 0.500000 0.500000
Ni 1.000000
d 1.000000
illum 2
map_Kd ../textures/rock1.jpg
"""

COW_RESULT = {
  'Material_rock1.jpg': {
    'colorAmbient': [0.0, 0.0, 0.0],
    'colorDiffuse': [0.471461, 0.471461, 0.471461],
    'colorSpecular': [0.5, 0.5, 0.5],
    'illumination': 2,
    'mapDiffuse': '../textures/rock1.jpg',
    'opticalDensity': 1.0,
    'specularCoef': 96.078431,
    'transparency': 1.0,
    }
    }

TEAPOT_MTL = """
# Blender MTL File: 'None'
# Material Count: 1
newmtl
Ns 0
Ka 0.000000 0.000000 0.000000
Kd 0.8 0.8 0.8
Ks 0.8 0.8 0.8
d 1
illum 2
map_Kd ../textures/Raspi256x256.png
"""

TEAPOT_RESULT = {
  '': {
    'colorAmbient': [0.0, 0.0, 0.0],
    'colorDiffuse': [0.8, 0.8, 0.8],
    'colorSpecular': [0.8, 0.8, 0.8],
    'illumination': 2,
    'mapDiffuse': '../textures/Raspi256x256.png',
    'specularCoef': 0.0,
    'transparency': 1.0,
    }}

########NEW FILE########
__FILENAME__ = Mouse
from __future__ import absolute_import, division, print_function, unicode_literals

import threading
import six

from pi3d.util import Log

LOGGER = Log.logger(__name__)

class _Mouse(threading.Thread):
  """holds Mouse object, see also (the preferred) events methods"""
  BUTTON_1 = 1 << 1
  BUTTON_2 = 1 << 2
  BUTTONS = BUTTON_1 & BUTTON_2
  HEADER = 1 << 3
  XSIGN = 1 << 4
  YSIGN = 1 << 5
  INSTANCE = None

  def __init__(self, mouse='mice', restrict=True, width=1920, height=1200):
    """
    Arguments:
      *mouse*
        /dev/input/ device name
      *restrict*
        stops or allows the mouse x and y values to carry on going beyond:
      *width*
        mouse x limit
      *height*
        mouse y limit
    """
    super(_Mouse, self).__init__()
    self.fd = open('/dev/input/' + mouse, 'rb')
    self.running = False
    self.buffr = '' if six.PY3 else b''
    self.lock = threading.RLock()
    self.width = width
    self.height = height
    self.restrict = restrict

    #create a pointer to this so Display.destroy can stop the thread
    from pi3d.Display import Display
    Display.INSTANCE.external_mouse = self

    self.reset()

  def reset(self):
    with self.lock:
      self._x = self._y = self._dx = self._dy = 0
    self.button = False

  def start(self):
    if not self.running:
      self.running = True
      super(_Mouse, self).start()

  def run(self):
    while self.running:
      self._check_event()
    self.fd.close()

  def position(self):
    with self.lock:
      return self._x, self._y

  def velocity(self):
    with self.lock:
      return self._dx, self._dy

  def _check_event(self):
    if len(self.buffr) >= 3:
      buttons = ord(self.buffr[0])
      self.buffr = self.buffr[1:]
      if buttons & _Mouse.HEADER:
        dx, dy = map(ord, self.buffr[0:2])
        self.buffr = self.buffr[2:]
        self.button = buttons & _Mouse.BUTTONS
        if buttons & _Mouse.XSIGN:
          dx -= 256
        if buttons & _Mouse.YSIGN:
          dy -= 256

        x = self._x + dx
        y = self._y + dy
        if self.restrict:
          x = min(max(x, 0), self.width - 1)
          y = min(max(y, 0), self.height - 1)

        with self.lock:
          self._x, self._y, self._dx, self._dy = x, y, dx, dy

    else:
      try:
        strn = self.fd.read(3).decode("latin-1")
        self.buffr += strn
      except Exception as e:
        print("exception is: {}".format(e))
        self.stop()
        return

  def stop(self):
    self.running = False

def Mouse(*args, **kwds):
  if not _Mouse.INSTANCE:
    _Mouse.INSTANCE = _Mouse(*args, **kwds)
  return _Mouse.INSTANCE

########NEW FILE########
__FILENAME__ = Shader
from __future__ import absolute_import, division, print_function, unicode_literals

import ctypes
import six
import sys, os

from pi3d.constants import *
from pi3d.util.Ctypes import c_chars
from pi3d.util import Log
from pi3d.util import Loadable

# This class based on Peter de Rivaz's mandlebrot example + Tim Skillman's work on pi3d2
LOGGER = Log.logger(__name__)

MAX_LOG_SIZE = 1024

def _opengl_log(shader, function, caption):
  log = c_chars(MAX_LOG_SIZE)
  loglen = ctypes.c_int()
  function(shader, MAX_LOG_SIZE, ctypes.byref(loglen), ctypes.byref(log))
  LOGGER.info('%s: %s', caption, log.value)

class Shader(object):
  """This compiles and holds the shaders to be used to render the Shape Buffers
  using their draw() methods. Generally you will choose and load the Shader
  explicitly as part of the program, however some i.e. defocus are loaded
  automatically when you create an instance of the Defocus class. Shaders can
  be 're-used' to draw different objects and the same object can be drawn using
  different Shaders.

  The shaders included with the pi3d module fall into two categories:

  * Textured - generally defined using the **uv** prefix, where an image needs
    to be loaded via the Texture class which is then mapped to the surface
    of the object. The **2d_flat** shader is a special case of a textured shader
    which maps pixels in an image to pixels on the screen with an optional
    scaling and offset.

  * Material - generally defined using the **mat** prefix, where a material
    shade (rgb) has to be set for the object to be rendered

  Within these categories the shaders have been subdivided with a postfix to
  give full names like uv_flat, mat_bump etc:

  * flat - no lighting is used, the shade rendered is the rgb value of the
    texture or material

  * light - Light direction, shade and ambient shade are used give a 3D effect
    to the surface

  * bump - a normal map texture needs to be loaded as well and this will be
    used to give much finer 3D effect to the surface than can be defined by
    the resolution of the vertices. The effect of the normal map drops with
    distance to give a detailed foreground without tiling artifacts in the
    distance. The shader is passed a variable to use for tiling the normal
    map which may be different from the tiling of the general texture. If
    set to 0.0 then no normal mapping will occur.

  * reflect - in addition to a normal map an image needs to be supplied to
    act as a reflection. The shader is passed a value from 0.0 to 1.0 to
    determine the strength of the reflection.

  The reason for using a host of different shaders rather than one that can
  do everything is that 'if' statements within the shader language are **very**
  time consuming.
  """
  def __init__(self, shfile=None, vshader_source=None, fshader_source=None):
    """
    Arguments:
      *shfile*
        Pathname without vs or fs ending i.e. "shaders/uv_light"

      *vshader_source*
        String with the code for the vertex shader.

      *vshader_source*
        String with the code for the fragment shader.
    """
    assert Loadable.is_display_thread()

    # TODO: the rest of the constructor should be split into load_disk
    # and load_opengl so that we can delete that assert.

    self.program = opengles.glCreateProgram()
    self.shfile = shfile

    def make_shader(src, suffix, shader_type):
      src = src or self.loadShader(shfile + suffix)
      characters = ctypes.c_char_p(src.encode())
      shader = opengles.glCreateShader(shader_type)
      opengles.glShaderSource(shader, 1, ctypes.byref(characters), 0)
      opengles.glCompileShader(shader)
      self.showshaderlog(shader)
      opengles.glAttachShader(self.program, shader)
      return shader, src

    self.vshader_source, self.vshader = make_shader(
      vshader_source, '.vs', GL_VERTEX_SHADER)

    self.fshader_source, self.fshader = make_shader(
      fshader_source, '.fs', GL_FRAGMENT_SHADER)

    opengles.glLinkProgram(self.program)
    self.showprogramlog(self.program)

    self.attr_vertex = opengles.glGetAttribLocation(self.program, b'vertex')
    self.attr_normal = opengles.glGetAttribLocation(self.program, b'normal')

    self.unif_modelviewmatrix = opengles.glGetUniformLocation(
      self.program, b'modelviewmatrix')
    self.unif_cameraviewmatrix = opengles.glGetUniformLocation(
      self.program, b'cameraviewmatrix')

    self.unif_unif = opengles.glGetUniformLocation(self.program, b'unif')
    self.unif_unib = opengles.glGetUniformLocation(self.program, b'unib')

    self.attr_texcoord = opengles.glGetAttribLocation(self.program, b'texcoord')
    opengles.glEnableVertexAttribArray(self.attr_texcoord)
    self.unif_tex = []
    self.textures = []
    for s in [b'tex0', b'tex1', b'tex2']:
      self.unif_tex.append(opengles.glGetUniformLocation(self.program, s))
      self.textures.append(None)
      """
      *NB*
        for *uv* shaders tex0=texture tex1=normal map tex2=reflection

        for *mat* shaders tex0=normal map tex1=reflection
      """
    self.use()

  def use(self):
    """Makes this shader active"""
    opengles.glUseProgram(self.program)

  def showshaderlog(self, shader):
    """Prints the compile log for a shader"""
    N = 1024
    log = (ctypes.c_char * N)()
    loglen = ctypes.c_int()
    opengles.glGetShaderInfoLog(
      shader, N, ctypes.byref(loglen), ctypes.byref(log))
    print('shader {}, {}'.format(self.shfile, log.value))

  def showprogramlog(self, shader):
    """Prints the compile log for a program"""
    N = 1024
    log = (ctypes.c_char * N)()
    loglen = ctypes.c_int()
    opengles.glGetProgramInfoLog(
      shader, N, ctypes.byref(loglen), ctypes.byref(log))

  def loadShader(self, sfile):
    for p in sys.path:
      if os.path.isfile(p + '/' + sfile):
        return open(p + '/' + sfile, 'r').read()
      elif os.path.isfile(p + '/shaders/' + sfile):
        return open(p + '/shaders/' + sfile, 'r').read()
      elif os.path.isfile(p + '/pi3d/shaders/' + sfile):
        return open(p + '/pi3d/shaders/' + sfile, 'r').read()

########NEW FILE########
__FILENAME__ = Building
from __future__ import absolute_import, division, print_function, unicode_literals

# Silo project using pi3d module
# =====================================
# Copyright (c) 2012-2013 Richard Urwin
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The above license is the 2-clause BSD license, which is compatible with both
# version 2 and 3 of the GPL. (Unlike versions 2 and 3 of the GPL ;-)
# http://www.gnu.org/licenses/license-list.html
#
# I aim to make all infrastructure of the Silo project open and free, although the
# finished game may contain none-free or otherwise restricted elements such as level maps.
#
# Based on code in the Forest Walk example
# Copyright (c) 2012 - Tim Skillman
# Version 0.04 - 20Jul12
#
# This example does not reflect the finished pi3d module in any way whatsoever!
# It merely aims to demonstrate a working concept in simplfying 3D programming on the Pi
import os.path

from pi3d.constants import *
import math, random, sys
from six.moves import filter

from PIL import ImageOps, ImageDraw, Image

from pi3d.shape.MergeShape import MergeShape
from pi3d.shape.Cuboid import Cuboid
from pi3d.shape.Plane import Plane
from pi3d.Shape import Shape
from pi3d.Buffer import Buffer
from pi3d.Texture import Texture

from pi3d.util import Log

LOGGER = Log.logger(__name__)

rads = 0.017453292512 # degrees to radians

class xyz(object):
  """
  Encapsulates a 3D point-type triple.
  """
  def __init__(self, x,y=None,z=None):
    """
    Constructor
    Can be initialised either with one of these or by with three things that can be cast to floats.
    """
    if isinstance(x, xyz):
      self.x = x.x
      self.y = x.y
      self.x = x.z
    else:
      self.x = float(x)
      self.y = float(y)
      self.z = float(z)

def __str__(self):
      return "({0}, {1}, {2})".format(self.x, self.y, self.z)


class Size(xyz):
  """
  Encapsulates a 3D size.
  Works together with Position to provide intelligent typing. A position plus a
  size is a position, whereas a position minus a position is a size.
  """
  def __init__(self, x,y=None,z=None):
    super(Size,self).__init__(x, y, z)

  def __add__(self, a):
    if isinstance(a, Position):
      return Position(self.x + a.x, self.y + a.y, self.z + a.z)
    if isinstance(a, Size):
      return Size(self.x + a.x, self.y + a.y, self.z + a.z)
    else:
      raise TypeException

  def __sub__(self,a):
    if isinstance(a, Position):
      return Position(self.x - a.x, self.y - a.y, self.z - a.z)
    if isinstance(a, Size):
      return Size(self.x - a.x, self.y - a.y, self.z - a.z)
    else:
      raise TypeError

  def __div__(self, a):
    return Size(self.x / a, self.y / a, self.z / a)

  def __truediv__(self, a):
    return self.__div__(a)


class Position(xyz):
  """
  Encapsulates a 3D position.
  Works together with Size to provide intelligent typing. A position plus a
  size is a position, whereas a position minus a position is a size.
  """
  def __init__(self, x,y=None,z=None):
    super(Position,self).__init__(x,y,z)

  def __add__(self, a):
    if isinstance(a, Size):
      return Position(self.x + a.x, self.y + a.y, self.z + a.z)
    if isinstance(a, Position):
      return Size(self.x + a.x, self.y + a.y, self.z + a.z)
    else:
      raise TypeException

  def __sub__(self,a):
    if isinstance(a, Size):
      return Position(self.x - a.x, self.y - a.y, self.z - a.z)
    if isinstance(a, Position):
      return Size(self.x - a.x, self.y - a.y, self.z - a.z)
    else:
      raise TypeError

  def setvalue(self,p):
    if not isinstance(p, Position): raise TypeError
    self.x = p.x
    self.y = p.y
    self.z = p.z

def _overlap(x1, w1, x2, w2):
  """
  A utility function for testing for overlap on a single axis. Returns true
  if a line w1 above and below point x1 overlaps a line w2 above and below point x2.
  """
  if x1+w1 < x2-w2: return False
  if x1-w1 > x2+w2: return False

  return True

class ObjectCuboid(object):
  """
  An ObjectCuboid has a size and position (of its centre) and a bulk.
  The size is its extent beyond the centre on the three axes, the position is the position of its centre.
  Note that this is different from the size of an ObjectCuboid. The bulk
  is an aura around it that the auras of other objects can not enter. The bulk can be zero.
  """
  def __init__(self, name, s, p, bulk):
    """
    Constructor
    """
    if not isinstance(s, Size): raise TypeError
    if not isinstance(p, Position): raise TypeError
    self.name = name
    self.size = s
    self.position = p
    self.bulk = bulk

  def x(self):
    """
    Returns the x coordinate of the centre of this object
    """
    return self.position.x

  def y(self):
    """
    Returns the x coordinate of the centre of this object
    """
    return self.position.y

  def top_y(self):
      """
      Returns the y coordinate of the top of this object
      """
      return self.position.y + self.size.y + self.bulk

  def bottom_y(self):
      """
      Returns the y coordinate of the top of this object
      """
      return self.position.y - self.size.y - self.bulk

  def z(self):
    """
    Returns the x coordinate of the centre of this object
    """
    return self.position.z

  def w(self):
    """
    Returns size of this object along the x axis -- its width
    """
    return self.size.x

  def h(self):
    """
    Returns size of this object along the y axis -- its height
    """
    return self.size.y

  def d(self):
    """
    Returns size of this object along the z axis -- its depth
    """
    return self.size.z

  def move(self, p):
    """
    Moves this object to the given position.
    """
    self.position.setvalue(p)

  def Overlaps(self, o, pos=None):
    """
    Returns true if the current ObjectCuboid overlaps the given ObjectCuboid.
    If the pos argument is specified then it is used as the position of the
    given ObjectCuboid instead of its actual position.

    Clear as mud?

    Without a pos argument: "does object o overlap me?"
    With a pos argument: "would object o overlap me if it was at position 'pos'?"
    """
    if pos == None:
      pos = o.position
    return _overlap(self.position.x-self.bulk, self.size.x+2*self.bulk, pos.x-o.bulk, o.size.x+o.bulk*2) and \
      _overlap(self.position.y-self.bulk, self.size.y+2*self.bulk, pos.y-o.bulk, o.size.y+o.bulk*2) and \
      _overlap(self.position.z-self.bulk, self.size.z+2*self.bulk, pos.z-o.bulk, o.size.z+o.bulk*2)


class SolidObject(ObjectCuboid):
  """
  A solid object is one that the avatar can not walk through. It has a size, a position and a bulk.
  The size is its total size on the three axes, the position is the position of its centre.
  The bulk is the aura around it into which the avatar's aura is not allowed to enter. A zero bulk works fine.

  Each solid object can have an optional model associated with it. Each SolidObject created is added to a
  list of SolidObjects. All the models of all the objects in the list can be drawn with a single method call (drawall).
  If a solid object does not have an associated model then drawall() does not attempt to draw it. That
  applies to the avatar and to any objects that are part of merged shapes for example.
  """
  objectlist = []

  def __init__(self,name,s,p, bulk):
    """
    Constructor
    """
    super(SolidObject, self).__init__(name, s / 2, p, bulk)
    type(self).objectlist.append(self)
    self.model = None
    self.details = None

  def remove(self):
    try:
      type(self).objectlist.remove(self)
    except:
      LOGGER.error('Tried to remove %s twice.', self)

  def CollisionList(self, p):
    """
    Returns a list of the objects that would overlap with the current oject,
    if the current object was at the given position. (With the exception of the current
    oject of course.)
    This can be used for any moving object to ensure that its proposed new position is available,
    or maybe to determine when a missile should explode and what it should destroy.
    """
    if not isinstance(p, Position): raise TypeError
    r = list(filter(lambda x: x.Overlaps(self,p), type(self).objectlist))
    try:
        r.remove(self)
    except ValueError:
        pass
    return r

  def setmodel(self, model, details):
    """
    Sets the associated model and the details with which to draw it. If the model is set
    then drawall() will draw this object. If it isn't, it wont.
    """
    self.model = model
    self.details = details
    self.model.set_draw_details(details[0], details[1], details[2], details[3], details[4], details[5])

  @classmethod
  def drawall(self):
    """
    Draw all solid objects to which models (and detailss) have been associated.
    """
    for x in self.objectlist:
      if x.model:
        x.model.draw()

class createMyCuboid(Cuboid):
    """
    A bodge because my cuboids appear to be out of position with respect to my collision
    system. Fortunately it does not seem to happen with planes. Probably my fault.
    """
    def __init__(self,w,h,d, name="", x=0.0,y=0.0,z=0.0, rx=0.0,ry=0.0,rz=0.0, cx=0.0,cy=0.0,cz=0.0):
      fact = 0
      if w > fact:
        fact = w
      if h > fact:
        fact = h
      if d > fact:
        fact = d
      super(createMyCuboid,self).__init__(w=w, h=h, d=d, name=name, x=x+0.125, y=y, z=z-1.125,
        rx=rx, ry=ry, rz=rz, cx=cx, cy=cy, cz=cz, tw=w / fact, th=h / fact, td=d / fact)

wallnum=0
def corridor(x,z, emap, width=10, length=10, height=10, details=None, walls="ns", name="wall", mergeshape=None):
  """
  Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
  The north and south walls are parallel with the x axis, with north being more positive. The east and
  west walls are parallel with the z axis, with east being more positive.
  The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
  "length" along the x axis, and "height" high. All walls and ceiling is a cuboid, 1 unit thick. There is no floor.

  Use this function when having the walls as planes is a problem, such as when their zero thinkness is visible.
  Otherwise corridor_planes() is more efficient.

  Which walls to create are specified by the string argument "walls". This should contain the letters n,e,s,w to draw the
  corresponding wall, or "o" (for open) if no ceiling is required.
  For example a N-S corridor section would use "ew", and a simple corner in the SE with no roof would be "seo"

  If mergeshape is None then the resulting objects are drawn with SolidObject.drawall(), if mergeshape is set then the
  objects are added to it and SolidObject.drawall() will not draw it.

  The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
  """
  global wallnum
  n = z + width / 2
  s = z - width / 2
  e = x + length / 2
  w = x - length / 2

  solid_objects = []

  if "n" in walls:
    # TODO: abstract out the mostly-duplicate code in these cases...
    nwall = SolidObject(name+str(wallnum),
                        Size(length, height, 1),
                        Position(x, emap.calcHeight(x, z) + height / 2, n-0.5), 0)
    solid_objects.append(nwall)
    nwallmodel = createMyCuboid(nwall.w() * 2, nwall.h() * 2, nwall.d() * 2,
          name=name+str(wallnum),
          x=nwall.x(),y=nwall.y(),z=nwall.z(),
          rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0)
    if mergeshape:
      mergeshape.add(nwallmodel)
    else:
      nwall.setmodel(nwallmodel, details)


    wallnum += 1

  if "s" in walls:
    swall = SolidObject(name+str(wallnum), Size(length, height, 1), Position(x, emap.calcHeight(x, z)+height / 2, s+0.5), 0)
    solid_objects.append(swall)
    swallmodel = createMyCuboid(swall.w()*2, swall.h()*2, swall.d()*2,
                                name=name+str(wallnum),
                                x=swall.x(), y=swall.y(), z=swall.z(),
                                rx=0.0, ry=0.0, rz=0.0, cx=0.0,cy=0.0, cz=0.0)
    if mergeshape:
      mergeshape.add(swallmodel)
    else:
      swall.setmodel(swallmodel, details)

    wallnum += 1

  if "e" in walls:
    ewall = SolidObject(name+str(wallnum), Size(1, height, width), Position(e-0.5, emap.calcHeight(x, z)+height / 2, z), 0)
    solid_objects.append(ewall)
    ewallmodel = createMyCuboid(ewall.w()*2, ewall.h()*2, ewall.d()*2,
          name=name+str(wallnum),
          x=ewall.x(), y=ewall.y(), z=ewall.z(),
          rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0)
    if mergeshape:
      mergeshape.add(ewallmodel)
    else:
      ewall.setmodel(ewallmodel, details)

    wallnum += 1

  if "w" in walls:
    wwall = SolidObject(name+str(wallnum), Size(1, height, width), Position(w+0.5, emap.calcHeight(x, z)+height / 2, z), 0)
    solid_objects.append(wwall)
    wwallmodel = createMyCuboid(wwall.w()*2, wwall.h()*2, wwall.d()*2,
          name=name+str(wallnum),
          x=wwall.x(), y=wwall.y(), z=wwall.z(),
          rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0)
    if mergeshape:
      mergeshape.add(wwallmodel)
    else:
      wwall.setmodel(wwallmodel, details)
    wallnum += 1

  if "o" not in walls:
    ceiling = SolidObject(name+str(wallnum), Size(length, 1, width), Position(x, emap.calcHeight(x, z)+height+0.5, z), 0)
    solid_objects.append(ceiling)
    ceilingmodel = createMyCuboid(ceiling.w()*2, ceiling.h()*2, ceiling.d()*2,
          name=name+str(wallnum),
          x=ceiling.x(), y=ceiling.y(), z=ceiling.z(),
          rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0)
    if mergeshape:
      mergeshape.add(ceilingmodel)
    else:
      ceiling.setmodel(ceilingmodel, details)

    wallnum += 1

  return solid_objects


class Building (object):

  # baseScheme : black is wall, white is corridor or room, there is one model
  baseScheme = {"#models": 1,
          (0,None): [["R",0]],
          (1,None): [["R",0], ["C",0]],
          (0,0,"edge"): [["W",0], ["CE", 0]],
          (1,0,"edge"): [["W",0], ["CE", 0]],
          (1,0):[["W",0], ["CE", 0]]}

  # openSectionScheme: black is wall, white is corridor or room, grey has no ceiling, there is one model
  openSectionScheme = {"#models": 1,
              (0,None) : [["R",0]],           # black cell has a roof
              (2,None):[["C", 0], ["R", 0]],      # white cell has a ceiling and roof
              (0,0,"edge"):[["W",0], ["CE", 0]],    # black cell on the edge next to a black cell has a wall and ceiling edge
              (1,0,"edge"):[["W",0], ["CE", 0]],    # grey cell on the edge next to a black cell has a wall and ceiling edge
              (2,0,"edge"):[["W",0], ["CE", 0]],    # white cell on the edge next to a black cell has a wall and ceiling edge
              (2,2,"edge"):[["CE", 0]],         # white cell on the edge next to a white cell a ceiling edge
              (2,0):[["W", 0]],             # white cell next to a black cell has a wall
              (1,0):[["W", 0], ["CE", 0]],       # grey cell next to a black cell has a wall and ceiling edge
              (1,2):[["CE", 0]] }            # grey cell next to a white cell has a ceiling edge

  def __init__(self, mapfile, xpos, zpos, emap, width=10.0, depth=10.0, height=10.0, name="building", draw_details=None, yoff=0.0, scheme=None):
    """
    Creates a building at the given location. Each pixel of the image is one cell of the building
    If the cell is white then the cell is open, if it is black then it is wall. If it is grey
    then it is open and has no ceiling.
    The building is centred at xpos, zpos (which gets renamed herin to x,y to match the image coords)
    Each cell is width on the x axis and depth on the z axis, and the walls are height high on the y axis.

    The function returns a merged shape with the entire building in it.
    """
    self.xpos = xpos
    self.zpos = zpos
    self.width = width
    self.depth = depth
    self.height = height
    self.name = name
    self.ceilingthickness = 1.0
    self.walls = []

    if scheme == None:
      self.scheme = Building.baseScheme
    else:
      self.scheme = scheme

    # We don't have to be rigorous here, this should only be a draw_details or an iterable of draw_details.
    if hasattr(draw_details, "__getitem__") or hasattr(draw_details, "__iter__"):
      assert (len(draw_details) == self.scheme["#models"])
      self.details = draw_details
    else:
      self.details = [draw_details for x in range(self.scheme["#models"])]
    # having a method like this allows draw details to be set later

    self.yoff = yoff

    self.model = [MergeShape(name=name+"."+str(x)) for x in range(self.scheme["#models"])]

    if mapfile[0] != '/':
      mapfile = sys.path[0] + '/' + mapfile
    print("Loading building map ...", mapfile)

    im = Image.open(mapfile)
    im = ImageOps.invert(im)
    ix,iy = im.size

    print("image size", ix, ",", iy)

    startx = xpos - ix / 2 * width
    starty = zpos - ix / 2 * depth

    yoff += emap.calcHeight(-xpos,-zpos)

    if not im.mode == "P":
        im = im.convert('P', palette=Image.ADAPTIVE)
    im = im.transpose(Image.FLIP_TOP_BOTTOM)
    im = im.transpose(Image.FLIP_LEFT_RIGHT)
    pixels = im.load()

    for y in range(1,iy-1):
      print(".", end='')
      for x in range(1,ix-1):
          colour = pixels[x,y]

          if x == 1:
            self._executeScheme(x, y, startx, starty, (colour, pixels[x-1,y], "edge"), wallfunc=self.west_wall, ceilingedgefunc=self.west_edge, ceilingfunc=self.ceiling, rooffunc=self.roof)
          else:
            self._executeScheme(x, y, startx, starty, (colour, pixels[x-1,y]), wallfunc=self.west_wall, ceilingedgefunc=self.west_edge, ceilingfunc=self.ceiling, rooffunc=self.roof)

          if x == ix-2:
            self._executeScheme(x, y, startx, starty, (colour, pixels[x+1,y], "edge"), wallfunc=self.east_wall, ceilingedgefunc=self.east_edge, ceilingfunc=self.ceiling, rooffunc=self.roof)
          else:
            self._executeScheme(x, y, startx, starty, (colour, pixels[x+1,y]), wallfunc=self.east_wall, ceilingedgefunc=self.east_edge, ceilingfunc=self.ceiling, rooffunc=self.roof)

          if y == 1:
            self._executeScheme(x, y, startx, starty, (colour, pixels[x,y-1], "edge"), wallfunc=self.south_wall, ceilingedgefunc=self.south_edge, ceilingfunc=self.ceiling, rooffunc=self.roof)
          else:
            self._executeScheme(x, y, startx, starty, (colour, pixels[x,y-1]), wallfunc=self.south_wall, ceilingedgefunc=self.south_edge, ceilingfunc=self.ceiling, rooffunc=self.roof)

          if y == iy-2:
            self._executeScheme(x, y, startx, starty, (colour, pixels[x, y+1], "edge"), wallfunc=self.north_wall, ceilingedgefunc=self.north_edge, ceilingfunc=self.ceiling, rooffunc=self.roof)
          else:
            self._executeScheme(x, y, startx, starty, (colour, pixels[x,y+1]), wallfunc=self.north_wall, ceilingedgefunc=self.north_edge, ceilingfunc=self.ceiling, rooffunc=self.roof)

          self._executeScheme(x, y, startx, starty, (colour, None), wallfunc=None, ceilingedgefunc=None, ceilingfunc=self.ceiling, rooffunc=self.roof)

    self.set_draw_details(self.details) # after models created otherwise
                                        # details lost by merging


  def remove_walls(self):
    for w in self.walls:
      w.remove()
    self.walls = []

  def drawAll(self):
    """
    Draws all the models that comprise the building
    """
    for x in range(len(self.model)):
      self.model[x].draw()

  def set_draw_details(self, details):
    """
    Set the shader, textures, ntiles and reflection strength
    """
    for x in range(len(self.model)):
      self.model[x].set_draw_details(details[x][0], details[x][1], details[x][2], details[x][3], details[x][4], details[x][5])

  def _executeScheme (self, x, y, startx, starty, key, wallfunc=None, ceilingedgefunc=None, ceilingfunc=None, rooffunc=None):
    """
    Calls the functions defined for the given key in the scheme.
    Each operation consists of a string and a model index. If the string is W then a wall is created and added to the indexed model.
    If the string is CE then a ceiling edge is created and added to the indexed model.
    If the string is R then a roof is created and if C then a ceiling is created.
    The key has one of three forms:
    (n1, n2) The first number is the colour of the current cell.
      The second number is the colour of the adjacent cell (on the other side of the prospective wall.)
      This is used once per direction to create upto four walls (and ceiling edges).
    (n1, n2, "edge") As (n1,n2), but the cell is on the edge of the building.
    (n, None) The number is the colour of the current cell. This is used once per cell to create the ceiling and roof.
    """

    if key in self.scheme:
      for op in self.scheme[key]:
        if op[0] == "W" and wallfunc:
          wallfunc(x*self.width + startx, self.yoff, y*self.depth + starty,
               self.width, self.depth, self.height,
               self.details[op[1]], mergeshape=self.model[op[1]])
        elif op[0] == "C" and ceilingfunc:
          ceilingfunc(x*self.width + startx, self.yoff, y*self.depth + starty,
               self.width, self.depth, self.height,
               self.details[op[1]], mergeshape=self.model[op[1]])
        elif op[0] == "R" and rooffunc:
          rooffunc(x*self.width + startx, self.yoff, y*self.depth + starty,
               self.width, self.depth, self.height,
               self.details[op[1]], mergeshape=self.model[op[1]])
        elif op[0] == "CE" and ceilingedgefunc:
          ceilingedgefunc(x*self.width + startx, self.yoff, y*self.depth + starty,
               self.width, self.depth, self.height,
               self.details[op[1]], mergeshape=self.model[op[1]])

  def north_wall(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    nwall = SolidObject(name+str(wallnum), Size(length, height, 1), Position(x, y + height / 2, n), 0)
    self.walls.append(nwall)
    model = Plane(w=nwall.w()*2, h=nwall.h()*2, name=name+str(wallnum))
    mergeshape.add(model, nwall.x(), nwall.y(), nwall.z())


    wallnum += 1

  def north_edge(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    model = Plane(w=length, h=self.ceilingthickness, name=name+str(wallnum))
    mergeshape.add(model, x, y+height+self.ceilingthickness / 2, n)

    wallnum += 1

  def south_wall(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    swall = SolidObject(name+str(wallnum), Size(length, height, 1), Position(x, y+height / 2, s), 0)
    self.walls.append(swall)
    model = Plane(w=swall.w()*2, h=swall.h()*2, name=name+str(wallnum))
    mergeshape.add(model, swall.x(),swall.y(),swall.z(), rx=0.0,ry=0.0,rz=0.0)

    wallnum += 1

  def south_edge(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    model = Plane(w=length, h=self.ceilingthickness, name=name+str(wallnum))
    mergeshape.add(model, x,y+height+self.ceilingthickness / 2,s, rx=0.0,ry=0.0,rz=0.0)

    wallnum += 1

  def east_wall(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    ewall = SolidObject(name+str(wallnum), Size(1, height, width), Position(e, y+height / 2, z), 0)
    self.walls.append(ewall)
    model = Plane(w=ewall.d()*2, h=ewall.h()*2, name=name+str(wallnum))
    mergeshape.add(model, ewall.x(),ewall.y(),ewall.z(), rx=0.0,ry=90.0,rz=0.0)

    wallnum += 1

  def east_edge(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    model = Plane(w=width, h=self.ceilingthickness, name=name+str(wallnum))
    mergeshape.add(model, e,y+height+self.ceilingthickness / 2,z, rx=0.0,ry=90.0,rz=0.0)

    wallnum += 1

  def west_wall(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    wwall = SolidObject(name+str(wallnum), Size(1, height, width), Position(w, y+height / 2, z), 0)
    self.walls.append(wwall)
    model = Plane(w=wwall.d()*2, h=wwall.h()*2, name=name+str(wallnum))
    mergeshape.add(model, wwall.x(),wwall.y(),wwall.z(),rx=0.0,ry=90.0,rz=0.0)

    wallnum += 1

  def west_edge(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    model = Plane(w=width, h=self.ceilingthickness, name=name+str(wallnum))
    mergeshape.add(model, w,y+height+self.ceilingthickness / 2,z,rx=0.0,ry=90.0,rz=0.0)

    wallnum += 1

  def ceiling(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None, makeroof=True, makeceiling=True):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The resulting object is added to the given mergeshape

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.
    """
    global wallnum
    n = z + width / 2
    s = z - width / 2
    e = x + length / 2
    w = x - length / 2

    ceilingmodel = Plane(w=length, h=width, name=name+str(wallnum))
    mergeshape.add(ceilingmodel,x,y+height,z,rx=90.0,ry=0.0,rz=0.0)

    wallnum += 1

  def roof(self, x, y, z, width=10, length=10, height=10, details=None, name="wall", mergeshape=None, makeroof=True, makeceiling=True):
    """
    Creates a cell consisting of optional north, south, east and west walls and an optional ceiling.
    The north and south walls are parallel with the x axis, with north being more positive. The east and
    west walls are parallel with the z axis, with east being more positive.
    The cell is centred at (x,y,z). The cell is "width" along the z axis, (so north and south walls are that far apart,)
    "length" along the x axis, and "height" high. Each wall is a plane, but the ceiling is a cuboid, 1 unit high. There is no floor.

    The objects are named with the given name argument as a prefix and a globally incrementing number as the suffix.

    The resulting objects are added to the given mergeshape
    """
    global wallnum

    roof = SolidObject(name+str(wallnum), Size(length, 1, width), Position(x, y+height+self.ceilingthickness / 2, z), 0)
    self.walls.append(roof)
    roofmodel = Plane(w=length, h=width, name=name+str(wallnum))
    mergeshape.add(roofmodel,x,y+height+self.ceilingthickness,z,rx=90.0,ry=0.0,rz=0.0)

    wallnum += 1

########NEW FILE########
__FILENAME__ = Canvas
from pi3d.constants import *
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class Canvas(Shape):
  """ 3d model inherits from Shape. The simplest possible shape: a single
  triangle designed to fill the screen completely
  """
  def __init__(self, camera=None, light=None, name="", z=0.1):
    """Uses standard constructor for Shape but only one position variable is
    available as Keyword argument:

      *z*
        The depth that the shape will be constructed as an actual z offset
        distance in the vertices. As the Canvas is intended for use with
        2d shaders there is no way to change its location as no matrix
        multiplication will happen in the vertex shader.
    """
    super(Canvas, self).__init__(camera, light, name, x=0.0, y=0.0, z=0.0,
                                rx=0.0, ry=0.0, rz=0.0, sx=1.0, sy=1.0, sz=1.0,
                                cx=0.0, cy=0.0, cz=0.0)
    self.ttype = GL_TRIANGLES
    self.verts = []
    self.norms = []
    self.texcoords = []
    self.inds = []
    self.depth = z

    ww = 20.0
    hh = 20.0

    self.verts = ((-ww, -hh, z), (0.0, hh, z), (ww, -hh, z))
    self.norms = ((0, 0, -1), (0, 0, -1),  (0, 0, -1))
    self.texcoords = ((0.0, 0.0), (0.5, 1.0), (1.0, 0.0))

    self.inds = ((0, 1, 2), ) #python quirk: comma for tuple with only one val

    self.buf = []
    self.buf.append(Buffer(self, self.verts, self.texcoords, self.inds, self.norms))

  def set_texture(self, tex):
    self.buf[0].textures = [tex]

  def repaint(self, t):
    self.draw()

  def _load_opengl(self):
    self.buf[0].textures[0].load_opengl()

  def _unload_opengl(self):
    self.buf[0].textures[0].unload_opengl()

########NEW FILE########
__FILENAME__ = Cone
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Shape import Shape

class Cone(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self, camera=None, light=None, radius=1.0, height=2.0, sides=12, name="",
               x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *radius*
        radius at bottom
      *height*
        height
      *sides*
        number of sides
    """
    super(Cone, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                               sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating Cone ...")

    path = []
    path.append((0.0, height * .5))
    path.append((0.0001, height * .5))
    path.append((radius, -height * .4999))
    path.append((radius, -height * .5))
    path.append((0.0001, -height * .5))
    path.append((0.0, -height * .5))

    self.radius = radius
    self.height = height
    self.ttype = GL_TRIANGLES

    self.buf = []
    self.buf.append(self._lathe(path, sides))

########NEW FILE########
__FILENAME__ = Cuboid
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class Cuboid(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self,  camera=None, light=None, w=1.0, h=1.0, d=1.0,
               name="", x=0.0, y=0.0, z=0.0,
               rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0, tw=1.0, th=1.0, td=1.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *w*
        width
      *h*
        height
      *d*
        depth
      *tw*
        scale width
      *th*
        scale height
      *td*
        scale depth

    The scale factors are the multiple of the texture to show along that
    dimension. For no distortion of the image the scale factors need to be
    proportional to the relative dimension.
    """
    super(Cuboid, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                1.0, 1.0, 1.0, cx, cy, cz)

    if VERBOSE:
      print("Creating cuboid ...")

    self.width = w
    self.height = h
    self.depth = d
    self.ssize = 36
    self.ttype = GL_TRIANGLES

    ww = w / 2.0
    hh = h / 2.0
    dd = d / 2.0

    #cuboid data - faces are separated out for texturing..

    self.vertices = ((-ww, hh, dd), (ww, hh, dd), (ww, -hh, dd), (-ww, -hh, dd),
        (ww, hh, dd),  (ww, hh, -dd),  (ww, -hh, -dd), (ww, -hh, dd),
        (-ww, hh, dd), (-ww, hh, -dd), (ww, hh, -dd),  (ww, hh, dd),
        (ww, -hh, dd), (ww, -hh, -dd), (-ww, -hh, -dd),(-ww, -hh, dd),
        (-ww, -hh, dd),(-ww, -hh, -dd),(-ww, hh, -dd), (-ww, hh, dd),
        (-ww, hh, -dd),(ww, hh, -dd),  (ww, -hh, -dd), (-ww,-hh,-dd))
    self.normals = ((0.0, 0.0, 1),    (0.0, 0.0, 1),   (0.0, 0.0, 1),  (0.0, 0.0, 1),
        (1, 0.0, 0),  (1, 0.0, 0),    (1, 0.0, 0),     (1, 0.0, 0),
        (0.0, 1, 0),  (0.0, 1, 0),    (0.0, 1, 0),     (0.0, 1, 0),
        (0.0, -1, 0), (0,- 1, 0),     (0.0, -1, 0),    (0.0, -1, 0),
        (-1, 0.0, 0),  (-1, 0.0, 0),  (-1, 0.0, 0),    (-1, 0.0, 0),
        (0.0, 0.0, -1),(0.0, 0.0, -1),(0.0, 0.0, -1),  (0.0, 0.0, -1))

    self.indices = ((1, 0, 3), (1, 3, 2), (5, 4, 7),  (5, 7, 6),
        (9, 8, 11),  (9, 11, 10), (13, 12, 15), (13, 15, 14),
        (19, 18, 17),(19, 17, 16),(20, 21, 22), (20, 22, 23))

    #texture scales (each set to 1 would stretch it over face)
    tw = tw / 2.0
    th = th / 2.0
    td = td / 2.0

    self.tex_coords = ((0.5-tw, 0.5-th),        (0.5+tw, 0.5-th),        (0.5+tw, 0.5+th),        (0.5-tw, 0.5+th), #tw x th
        (0.5-td, 0.5-th),        (0.5+td, 0.5-th),        (0.5+td, 0.5+th),        (0.5-td, 0.5+th), # td x th
        (0.5+tw, 0.5-th),        (0.5-tw, 0.5-th),        (0.5-tw, 0.5+th),        (0.5+tw, 0.5+th), # tw x th
        (0.5-tw, 0.5-td),        (0.5+tw, 0.5-td),        (0.5+tw, 0.5+td),        (0.5-tw, 0.5+td), # tw x td
        (0.5+td, 0.5+th),        (0.5-td, 0.5+th),        (0.5-td, 0.5-th),        (0.5+td, 0.5-th), # td x th
        (0.5+tw, 0.5-th),        (0.5-tw, 0.5-th),        (0.5-tw, 0.5+th),        (0.5+tw, 0.5+th)) # tw x th

    self.buf = []
    self.buf.append(Buffer(self, self.vertices, self.tex_coords, self.indices, self.normals))


########NEW FILE########
__FILENAME__ = Cylinder
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Shape import Shape

class Cylinder(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self, camera=None, light=None, radius=1.0, height=2.0,
               sides=12, name="",
               x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *sides*
        number of edges for the end polygons
    """
    super(Cylinder, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                   sx, sy, sz, cx, cy, cz)
    if VERBOSE:
      print("Creating Cylinder ...")

    path = []
    path.append((0, height * .5))
    path.append((radius, height * .5))
    path.append((radius, height * .4999))
    path.append((radius, -height * .4999))
    path.append((radius, -height * .5))
    path.append((0, -height * .5))

    self.radius = radius
    self.height = height
    self.ttype = GL_TRIANGLES

    self.buf = []
    self.buf.append(self._lathe(path, sides))

########NEW FILE########
__FILENAME__ = Disk
from __future__ import absolute_import, division, print_function, unicode_literals

from math import pi

from pi3d.constants import *
from pi3d.Buffer import Buffer
from pi3d.util import Utility
from pi3d.Shape import Shape

class Disk(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self, camera=None, light=None, radius=1, sides=12, name="", x=0.0, y=0.0, z=0.0,
               rx=0.0, ry=0.0, rz=0.0, sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *radius*
        Radius of disk.
      *sides*
        Number of sides to polygon representing disk.
    """
    super(Disk, self).__init__(camera, light, name, x, y, z, rx, ry, rz, sx, sy, sz,
                               cx, cy, cz)

    if VERBOSE:
      print("Creating disk ...")

    self.verts = []
    self.norms = []
    self.inds = []
    self.texcoords = []
    self.ttype = GL_TRIANGLES
    self.sides = sides

    st = 2 * pi / sides
    for j in range(-1, 1):
      self.verts.append((0.0, -0.1*j, 0.0))
      self.norms.append((0.0, -j, 0.0))
      self.texcoords.append((0.5, 0.5))
      for r in range(sides+1):
        ca, sa = Utility.from_polar_rad(r * st)
        self.verts.append((radius * sa, 0.0, radius * ca))
        self.norms.append((0.0, -j - 0.1*j, 0.0))
        self.texcoords.append((sa * 0.5 + 0.5, ca * 0.5 + 0.5))
      if j == -1:
        v0, v1, v2 = 0, 1, 2
      else:
        v0, v1, v2 = sides + 2, sides + 4, sides + 3 # i.e. reverse direction to show on back
      for r in range(sides):
        self.inds.append((v0, r + v1, r + v2))

    self.but = []
    self.buf.append(Buffer(self, self.verts, self.texcoords, self.inds, self.norms))

########NEW FILE########
__FILENAME__ = ElevationMap
from __future__ import absolute_import, division, print_function, unicode_literals

import math
import sys

from six.moves import xrange

from PIL import Image, ImageOps

from numpy import cross, dot, sqrt, array, arctan2, arcsin, degrees, subtract

from pi3d import *
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape
from pi3d.util import Utility

# a rectangular surface where elevation is defined by a greyscal image
class ElevationMap(Shape):
  """ 3d model inherits from Shape
  """
  def __init__(self, mapfile, camera=None, light=None,
               width=100.0, depth=100.0, height=10.0,
               divx=0, divy=0, ntiles=1.0, name="",
               x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0, smooth=True, cubic=False):
    """uses standard constructor for Shape

    Arguments:
      *mapfile*
        Greyscale image path/file, string.

    Keyword arguments:
      *width, depth, height*
        Of the map in world units.
      *divx, divy*
        Number of divisions into which the map will be divided.
        to create vertices
      *ntiles*
        Number of repeats for tiling the texture image.
      *smooth*
        Calculate normals with averaging rather than pointing
        straight up, slightly faster if false.
    """
    super(ElevationMap, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                       sx, sy, sz, cx, cy, cz)
    if divx > 200 or divy > 200:
      print("... Map size can't be bigger than 200x200 divisions")
      divx = 200
      divy = 200
    if issubclass(type(mapfile), type("")): #HORRIBLE. Only way to cope with python2v3
      if mapfile[0] != '/':
        mapfile = sys.path[0] + '/' + mapfile
      if VERBOSE:
        print("Loading height map ...", mapfile)

      im = Image.open(mapfile)
      im = ImageOps.invert(im)
    else:
      im = mapfile #allow image files to be passed as mapfile
    ix, iy = im.size
    if (ix > 200 and divx == 0) or (divx > 0):
      if divx == 0:
        divx = 200
        divy = 200
      im = im.resize((divx, divy), Image.ANTIALIAS)
      ix, iy = im.size
    if not im.mode == "P":
      im = im.convert('P', palette=Image.ADAPTIVE)

    im = im.transpose(Image.FLIP_TOP_BOTTOM)
    im = im.transpose(Image.FLIP_LEFT_RIGHT)
    self.pixels = im.load()
    self.width = width
    self.depth = depth
    self.height = height
    self.ix = ix
    self.iy = iy
    self.ttype = GL_TRIANGLE_STRIP

    if VERBOSE:
      print("Creating Elevation Map ...", ix, iy)

    wh = width * 0.5
    hh = depth * 0.5
    ws = width / ix
    hs = depth / iy
    ht = height / 255.0
    tx = 1.0*ntiles / ix
    ty = 1.0*ntiles / iy

    verts = []
    norms = []
    tex_coords = []
    idx = []

    for y in xrange(0, iy):
      for x in xrange(0, ix):
        hgt = (self.pixels[x, y])*ht
        this_x = -wh + x*ws
        this_z = -hh + y*hs
        if cubic:
          """ this is a bit experimental. It tries to make the map either zero
          or height high. Vertices are moved 'under' adjacent ones if there is
          a step to make vertical walls. Goes wrong in places - mainly because
          it doesn't check diagonals
          """
          if hgt > height / 2:
            hgt = height
          else:
            hgt = 0.0
          if hgt == 0 and y > 0 and y < iy-1 and x > 0 and x < ix-1:
            if self.pixels[x-1, y] > 127:
              this_x = -wh + (x-1)*ws
            elif self.pixels[x+1, y] > 127:
              this_x = -wh + (x+1)*ws
            elif self.pixels[x, y-1] > 127:
              this_z = -hh + (y-1)*hs
            elif self.pixels[x, y+1] > 127:
              this_z = -hh + (y+1)*hs
            elif self.pixels[x-1, y-1] > 127:
              this_x = -wh + (x-1)*ws
              this_z = -hh + (y-1)*hs
            elif self.pixels[x-1, y+1] > 127:
              this_x = -wh + (x-1)*ws
              this_z = -hh + (y+1)*hs
            elif self.pixels[x+1, y-1] > 127:
              this_x = -wh + (x+1)*ws
              this_z = -hh + (y-1)*hs
            elif self.pixels[x+1, y+1] > 127:
              this_x = -wh + (x+1)*ws
              this_z = -hh + (y+1)*hs
        verts.append((this_x, hgt, this_z))
        tex_coords.append(((ix-x) * tx,(iy-y) * ty))

    s = 0
    #create one long triangle_strip by alternating X directions
    for y in range(0, iy-1):
      for x in range(0, ix-1):
        i = (y * ix)+x
        idx.append((i, i+ix, i+ix+1))
        idx.append((i+ix+1, i+1, i))
        s += 2

    self.buf = []
    self.buf.append(Buffer(self, verts, tex_coords, idx, None, smooth))

  def dropOn(self, px, pz):
    """determines approximately how high an object is when dropped on the map
     (providing it's inside the map area)
    """
    #adjust for map not set at origin
    px -= self.unif[0]
    pz -= self.unif[2]

    wh = self.width * 0.5
    hh = self.depth * 0.5
    ws = self.width / self.ix
    hs = self.depth / self.iy
    ht = self.height / 255.0

    if px > -wh and px < wh and pz > -hh and pz < hh:
      pixht = self.pixels[(wh + px) / ws,(hh + pz) / hs] * ht

    return pixht + self.unif[1]

  def calcHeight(self, px, pz):
    """accurately return the hight of the map at the point specified

    Arguments:
      *px, pz*
        Location of the point in world coordinates to calculate height.
    """
    #adjust for map not set at origin
    px -= self.unif[0]
    pz -= self.unif[2]

    wh = self.width * 0.5
    hh = self.depth * 0.5
    ws = self.width / self.ix
    hs = self.depth / self.iy
    ht = self.height / 255.0
    #round off to nearest integer
    px = (wh + px) / ws
    pz = (hh + pz) / hs
    x = math.floor(px)
    z = math.floor(pz)
    if x < 0: x = 0
    if x > (self.ix-2): x = self.ix-2
    if z < 0: z = 0
    if z > (self.iy-2): z = self.iy-2
    # use actual vertex location rather than recreate it from pixel*ht
    p0 = int(z*self.ix + x) #offset 1 to get y values
    p1 = p0 + 1
    p2 = p0 + self.ix
    p3 = p0 + self.ix + 1

    if pz > (z + 1 - px + x): #i.e. this point is in the triangle on the
    #opposite side of the diagonal so swap base corners
      x0, y0, z0 = x + 1, self.buf[0].vertices[p3][1], z + 1
    else:
      x0, y0, z0 = x, self.buf[0].vertices[p0][1], z
    return self.unif[1] + intersect_triangle((x0, y0, z0),
                            (x + 1, self.buf[0].vertices[p1][1], z),
                            (x, self.buf[0].vertices[p2][1], z + 1),
                            (px, 0, pz))


  # TODO these functions will be scrambled by any scaling, rotation or offset,
  #either print warning or stop these operations applying
  def clashTest(self, px, py, pz, rad):
    """Works out if an object at a given location and radius will overlap
    with the map surface. Returns four values:

    * boolean whether there is a clash
    * x, y, z components of the normal vector
    * the amount of overlap at the x,z location

    Arguments:
      *px, py, pz*
        Location of object to test in world coordinates.
      *rad*
        Radius of object to test.
    """
    radSq = rad**2
    # adjust for map not set at origin
    px -= self.unif[0]
    py -= self.unif[1]
    pz -= self.unif[2]
    ht = self.height/255
    halfw = self.width/2.0
    halfd = self.depth/2.0
    dx = self.width/self.ix
    dz = self.depth/self.iy

    # work out x and z ranges to check, x0 etc correspond with vertex indices in grid
    x0 = int(math.floor((halfw + px - rad)/dx + 0.5)) - 1
    if x0 < 0: x0 = 0
    x1 = int(math.floor((halfw + px + rad)/dx + 0.5)) + 1
    if x1 > self.ix-1: x1 = self.ix-1
    z0 = int(math.floor((halfd + pz - rad)/dz + 0.5)) - 1
    if z0 < 0: z0 = 0
    z1 = int(math.floor((halfd + pz + rad)/dz + 0.5)) + 1
    if z1 > self.iy-1: z1 = self.iy-1

    # go through grid around px, pz
    minDist, minLoc = 1000000, (0, 0)
    for i in xrange(x0+1, x1):
      for j in xrange(z0+1, z1):
        # use the locations stored in the one dimensional vertices matrix
        #generated in __init__. 3 values for each location
        p = j*self.ix + i # pointer to the start of xyz for i,j in the vertices array
        p1 = j*self.ix + i - 1 # pointer to the start of xyz for i-1,j
        p2 = (j-1)*self.ix + i # pointer to the start of xyz for i, j-1
        vertp = self.buf[0].vertices[p]
        normp = self.buf[0].normals[p]
        # work out distance squared from this vertex to the point
        distSq = (px - vertp[0])**2 + (py - vertp[1])**2 + (pz - vertp[2])**2
        if distSq < minDist: # this vertex is nearest so keep a record
          minDist = distSq
          minLoc = (i, j)
        #now find the distance between the point and the plane perpendicular
        #to the normal at this vertex
        pDist = dot([px - vertp[0], py - vertp[1], pz - vertp[2]],
                    [-normp[0], -normp[1], -normp[2]])
        #and the position where the normal from point crosses the plane
        xIsect = px - normp[0]*pDist
        zIsect = pz - normp[2]*pDist

        #if the intersection point is in this rectangle then the x,z values
        #will lie between edges
        if xIsect > self.buf[0].vertices[p1][0] and \
           xIsect < self.buf[0].vertices[p][0] and \
           zIsect > self.buf[0].vertices[p2][2] and \
           zIsect < self.buf[0].vertices[p][2]:
          pDistSq = pDist**2
          # finally if the perpendicular distance is less than the nearest so far
          #keep a record
          if pDistSq < minDist:
            minDist = pDistSq
            minLoc = (i,j)

    gLevel = self.calcHeight(px, pz) #check it hasn't tunnelled through by going fast
    if gLevel > (py-rad):
      minDist = py - gLevel
      minLoc = (int((x0+x1)/2), int((z0+z1)/2))

    if minDist <= radSq: #i.e. near enough to clash so return normal
      p = minLoc[1]*self.ix + minLoc[0]
      normp = self.buf[0].normals[p]
      if minDist < 0:
        jump = rad - minDist
      else:
        jump = 0
      return(True, normp[0], normp[1], normp[2],  jump)
    else:
      return (False, 0, 0, 0, 0)

  def pitch_roll(self, px, pz):
    """works out the pitch (rx) and roll (rz) to apply to an object
    on the surface of the map at this point

    * returns a tuple (pitch, roll) in degrees

    Arguments:
      *px*
        x location
      *pz*
        z location
    """
    px -= self.unif[0]
    pz -= self.unif[2]
    halfw = self.width/2.0
    halfd = self.depth/2.0
    dx = self.width/self.ix
    dz = self.depth/self.iy
    x0 = int(math.floor((halfw + px)/dx + 0.5))
    if x0 < 0: x0 = 0
    if x0 > self.ix-1: x0 = self.ix-1
    z0 = int(math.floor((halfd + pz)/dz + 0.5))
    if z0 < 0: z0 = 0
    if z0 > self.iy-1: z0 = self.iy-1
    normp = array(self.buf[0].normals[z0*self.ix + x0])
    # slight simplification to working out cross products as dirctn always 0,0,1
    #sidev = cross(normp, dirctn)
    sidev = array([normp[1], -normp[0], 0.0])
    sidev = sidev / sqrt(sidev.dot(sidev))
    #forwd = cross(sidev, normp)
    forwd = array([-normp[2]*normp[0], -normp[2]*normp[1],
                  normp[0]*normp[0] + normp[1]*normp[1]])
    forwd = forwd / sqrt(forwd.dot(forwd))
    return (degrees(arcsin(-forwd[1])), degrees(arctan2(sidev[1], normp[1])))


def intersect_triangle(v1, v2, v3, pos):
  """calculates the y intersection of a point on a triangle and returns the y
  value of the intersection of the line defined by x,z of pos through the
  triange defined by v1,v2,v3

  Arguments:
    *v1,v2,v3*
      tuples (x1,y1,z1), (x2,y2,z2).. defining the corners of the triangle
    *pos*
      tuple (x,y,z) defining the x,z of the vertical line intersecting triangle
  """
  #calc normal from two edge vectors v2-v1 and v3-v1
  nVec = cross(subtract(v2, v1), subtract(v3, v1))
  #equation of plane: Ax + By + Cz = kVal where A,B,C are components of normal. x,y,z for point v1 to find kVal
  kVal = dot(nVec,v1)
  #return y val i.e. y = (kVal - Ax - Cz)/B
  return (kVal - nVec[0]*pos[0] - nVec[2]*pos[2])/nVec[1]

########NEW FILE########
__FILENAME__ = EnvironmentCube
import os.path

from pi3d import *
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape
from pi3d.Texture import Texture

CUBE_PARTS = ['front', 'right', 'top', 'bottom', 'left', 'back']
BOTTOM_INDEX = 3

def loadECfiles(path, fname, suffix='jpg', nobottom=False):
  """Helper for loading environment cube faces.
  TODO nobottom will redraw the top on the bottom of cube. It really should
  substitute a blank (black) texture instead!
  
  Arguments:
    *path*
      to the image files relative to the top directory.
    *fname*
      The stem of the file name without the _top, _bottom, _right etc.
  
  Keyword arguments:
    *suffix*
      String to add after the '_top','_bottom' has been added to the stem.
    *nobottom*
      If True then only load five parts into array the bottom will be
      drawn with the previous image i.e. top.
  """
  if nobottom:
    parts = [p for p in CUBE_PARTS if p != 'bottom']
  else:
    parts = CUBE_PARTS

  files = (os.path.join(path, '%s_%s.%s' % (fname, p, suffix)) for p in parts)
  return [Texture(f) for f in files]

class EnvironmentCube(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self, camera=None, light=None, size=500.0, maptype="HALFCROSS", name="", x=0.0, y=0.0, z=0.0,
               rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0, nobottom=False):
    """uses standard constructor for Shape extra Keyword arguments:
    
      *size*
        Dimensions of the cube
      *maptype*
        HALFCROSS (default) or CROSS any other defaults to CUBE type
        and will require 6 (or 5 with nobottom) image files to render it
    """
    super(EnvironmentCube, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                1.0, 1.0, 1.0, cx, cy, cz)

    self.width = size
    self.height = size
    self.depth = size
    self.ssize = 36
    self.ttype = GL_TRIANGLES
    self.nobottom = nobottom

    ww = size / 2.0
    hh = size / 2.0
    dd = size / 2.0

    #cuboid data - faces are separated out for texturing..

    self.vertices = ((-ww, hh, dd), (ww, hh, dd), (ww, -hh, dd), (-ww, -hh, dd),
        (ww, hh, dd),  (ww, hh, -dd),  (ww, -hh, -dd), (ww, -hh, dd),
        (-ww, hh, dd), (-ww, hh, -dd), (ww, hh, -dd),  (ww, hh, dd),
        (ww, -hh, dd), (ww, -hh, -dd), (-ww, -hh, -dd),(-ww, -hh, dd),
        (-ww, -hh, dd),(-ww, -hh, -dd),(-ww, hh, -dd), (-ww, hh, dd),
        (-ww, hh, -dd),(ww, hh, -dd),  (ww, -hh, -dd), (-ww,-hh,-dd))
    self.normals = ((0.0, 0.0, 1),    (0.0, 0.0, 1),   (0.0, 0.0, 1),  (0.0, 0.0, 1),
        (1, 0.0, 0),  (1, 0.0, 0),    (1, 0.0, 0),     (1, 0.0, 0),
        (0.0, 1, 0),  (0.0, 1, 0),    (0.0, 1, 0),     (0.0, 1, 0),
        (0.0, -1, 0), (0,- 1, 0),     (0.0, -1, 0),    (0.0, -1, 0),
        (-1, 0.0, 0),  (-1, 0.0, 0),  (-1, 0.0, 0),    (-1, 0.0, 0),
        (0.0, 0.0, -1),(0.0, 0.0, -1),(0.0, 0.0, -1),  (0.0, 0.0, -1))
    self.indices = ((3, 0, 1), (2, 3, 1), (7, 4, 5),  (6, 7, 5),
        (11, 8, 9),  (10, 11, 9), (15, 12, 13), (14, 15, 13),
        (17, 18, 19),(16, 17, 19),(22, 21, 20), (23, 22, 20))

    if maptype == "CROSS":
      self.tex_coords = ((1.0, 0.34), (0.75, 0.34), (0.75, 0.661), (1.0, 0.661), #front
        (0.75, 0.34), (0.5, 0.34), (0.5, 0.661), (0.75, 0.661), #right
        (0.251, 0.0), (0.251, 0.34), (0.498, 0.34), (0.498, 0.0), #top
        (0.498, 0.998), (0.498, 0.66), (0.251, 0.66), (0.251, 0.998), #bottom
        (0.0, 0.661), (0.25, 0.661), (0.25, 0.34), (0.0, 0.34), #left
        (0.25, 0.34), (0.5, 0.34), (0.5, 0.661), (0.25, 0.661)) #back

      self.buf = []
      self.buf.append(Buffer(self, self.vertices, self.tex_coords, self.indices, self.normals))

    elif maptype == "HALFCROSS":
      self.tex_coords = ((0.25, 0.25), (0.25, 0.75), (-0.25, 0.75), (-0.25, 0.25), #front
        (0.25, 0.75), (0.75, 0.75), (0.75, 1.25), (0.25, 1.25), #right
        (0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75), #top
        (0, 0), (1, 0), (1, 1), (0, 1), #bottom
        (0.25, -0.25), (0.75, -0.25), (0.75, 0.25), (0.25, 0.25), #left
        (0.75, 0.25), (0.75, 0.75), (1.25, 0.75), (1.25, 0.25)) #back

      self.buf = []
      self.buf.append(Buffer(self, self.vertices, self.tex_coords, self.indices, self.normals))

    elif maptype == "BLENDER":
      self.tex_coords = ((0.999, 0.502), (0.668, 0.502), (0.668, 0.999), (0.999, 0.999), #front
        (0.333, 0.001), (0.001, 0.001), (0.001, 0.499), (0.333, 0.499), #right
        (0.666, 0.999), (0.666, 0.502), (0.335, 0.502), (0.335, 0.999), #top
        (0.001, 0.502), (0.001, 0.999), (0.332, 0.999), (0.332, 0.502), #bottom
        (0.668, 0.499), (0.999, 0.499), (0.999, 0.001), (0.668, 0.001), #left
        (0.335, 0.001), (0.666, 0.001), (0.666, 0.499), (0.335, 0.499)) #back

      self.buf = []
      self.buf.append(Buffer(self, self.vertices, self.tex_coords, self.indices, self.normals))

    else:
      self.tex_coords = ((0.002, 0.002), (0.998, 0.002), (0.998, 0.998),(0.002, 0.998),
            (0.002, 0.002), (0.998, 0.002), (0.998, 0.998), (0.002, 0.998),
            (0.002, 0.998), (0.002, 0.002), (0.998, 0.002), (0.998, 0.998),
            (0.998, 0.002), (0.998, 0.998), (0.002, 0.998), (0.002, 0.002),
            (0.998, 0.998), (0.002, 0.998), (0.002, 0.002), (0.998, 0.002),
            (0.998, 0.002), (0.002, 0.002), (0.002, 0.998), (0.998, 0.998))

      self.buf = []
      self.buf.append(Buffer(self, self.vertices[0:4], self.tex_coords[0:4], ((3, 0, 1), (2, 3, 1)), self.normals[0:4])) #front
      self.buf.append(Buffer(self, self.vertices[4:8], self.tex_coords[4:8], ((3, 0, 1), (2, 3, 1)), self.normals[4:8])) #right
      self.buf.append(Buffer(self, self.vertices[8:12], self.tex_coords[8:12], ((3,0,1), (2, 3, 1)), self.normals[8:12])) #top
      self.buf.append(Buffer(self, self.vertices[12:16], self.tex_coords[12:16], ((3, 0, 1), (2, 3, 1)), self.normals[12:16])) #bottom
      self.buf.append(Buffer(self, self.vertices[16:20], self.tex_coords[16:20], ((3, 0, 1), (2, 3, 1)), self.normals[16:20])) #left
      self.buf.append(Buffer(self, self.vertices[20:24], self.tex_coords[20:24], ((3, 1, 0), (2, 1, 3)), self.normals[20:24])) #back

  def set_draw_details(self, shader, textures, ntiles=0.0, shiny=0.0, umult=1.0, vmult=1.0):
    """overrides this method in Shape to cope with nobottom option"""
    self.shader = shader
    if not (type(textures) is list):
      textures = [textures]
    elif len(textures) == 5:
      # this should be the only circumstance. Saves setting it in the constructor
      self.nobottom = True

    for i, b in enumerate(self.buf):
      j = i - 1 if (self.nobottom and i >= BOTTOM_INDEX) else i
      b.set_draw_details(shader, [textures[j]], ntiles, shiny, umult, vmult)


########NEW FILE########
__FILENAME__ = Extrude
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Buffer import Buffer

from pi3d.Shape import Shape

class Extrude(Shape):
  """ 3d model inherits from Shape
  NB this shape has an array of three Buffers representing each end face
  and the sides of the prism. Each can be textured seperately for drawing.
  """
  def __init__(self, camera=None, light=None, path=None, height=1.0, name="", x=0.0, y=0.0, z=0.0,
               rx=0.0, ry=0.0, rz=0.0, sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *path*
        Coordinates defining crossection of prism [(x0,z0),(x1,z1)..]
      *height*
        Distance between end faces in the y direction.
    """
    super(Extrude, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                  sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating Extrude ...")

    s = len(path) if path != None else 0
    ht = height * 0.5

    self.verts = []
    self.norms = []
    self.botface = []
    self.topface = []
    self.sidefaces = []
    self.tex_coords = []
    self.edges = s
    self.ttype = GL_TRIANGLES

    minx = path[0][0]
    maxx = path[0][0]
    minz = path[0][1]
    maxz = path[0][1]

    #find min/max values for texture coords
    for p in range(0, s):
      px = path[p][0]
      pz = path[p][1]
      minx = min(minx, px)
      minz = min(minz, pz)
      maxx = max(maxx, px)
      maxz = max(maxz, pz)

    tx = 1.0 / (maxx - minx)
    tz = 1.0 / (maxz - minz)

    #vertices for sides
    for p in range(s):
      px = path[p][0]
      pz = path[p][1]
      dx = path[(p+1)%s][0] - px
      dz = path[(p+1)%s][1] - pz
      #TODO normalize these vector components, not needed for shadows = 0:2s
      for i in (-1, 1):
        self.verts.append((px, i*ht, pz))
        self.norms.append((-dz, 0.0, dx))
        self.tex_coords.append((1.0*p/s, i*0.5))

    #vertices for edges of top and bottom, bottom first (n=2s to 3s-1) 2s:3s then top (3s+1 to 4s) 3s+1:4s+1
    for i in (-1, 1):
      for p in range(s):
        px = path[p][0]
        pz = path[p][1]
        self.verts.append((px, i*ht, pz))
        self.norms.append((0.0, i, 0.0))
        self.tex_coords.append(((px - minx) * tx, (pz - minz) * tz))
      #top and bottom face mid points verts number 3*s and 4*s+1 (bottom and top respectively)
      self.verts.append(((minx+maxx)/2, i*ht, (minz+maxz)/2))
      self.norms.append((0, i, 0))
      self.tex_coords.append((0.5, 0.5))


    for p in range(s):    #sides - triangle strip
      v0, v1, v2, v3 = 2*p, 2*p+1, (2*p+2)%(2*s), (2*p+3)%(2*s)
      self.sidefaces.append((v0, v2, v1))
      self.sidefaces.append((v1, v2, v3))

    for p in range(s):    #bottom face indices - triangle fan
      self.botface.append((s, (p+1)%s, p))

    for p in range(s):    #top face indices - triangle fan
      self.topface.append((s, p, (p+1)%s))


    # sides, top, bottom
    self.buf = [Buffer(self, self.verts[0:(2*s)], self.tex_coords[0:(2*s)], self.sidefaces, self.norms[0:(2*s)]),
          Buffer(self, self.verts[(2*s):(3*s+1)], self.tex_coords[(2*s):(3*s+1)], self.botface, self.norms[(2*s):(3*s+1)]),
          Buffer(self, self.verts[(3*s+1):(4*s+2)], self.tex_coords[(3*s+1):(4*s+2)], self.topface, self.norms[(3*s+1):(4*s+2)])]


########NEW FILE########
__FILENAME__ = Helix
from __future__ import absolute_import, division, print_function, unicode_literals

import math

from pi3d.constants import *
from pi3d.Shape import Shape

class Helix(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self, camera=None, light=None, radius=1.0, thickness=0.2, ringrots=6, sides=12, rise=1.0,
               loops=2.0, name="", x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *radius*
        Radius of helix.
      *thickness*
        Radius of 'bar' being 'bent' to form the helical shape.
      *ringrots*
        Number of sides for the circlular secon of the 'bar'.
      *sides*
        Number of sides for Shape._lathe() to use.
      *rise*
        Distance between 'threads'.
      *loops*
        Number of turns that the helix makes.
    """
    super(Helix, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating Helix ...", radius, thickness, ringrots, sides)

    path = []
    st = (math.pi * 2) / ringrots
    hr = rise * 0.5
    for r in range(ringrots + 1):
      path.append((radius + thickness * math.sin(r * st),
                   thickness * math.cos(r * st) - hr))
      if VERBOSE:
        print("path:", path[r][0], path[r][1])

    self.radius = radius
    self.thickness = thickness
    self.ringrots = ringrots
    self.ttype = GL_TRIANGLES

    self.buf = []
    self.buf.append(self._lathe(path, sides, rise=rise, loops=loops))

########NEW FILE########
__FILENAME__ = Lathe
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Shape import Shape

class Lathe(Shape):
  """ 3d model inherits from Shape.
  Makes a shape by rotating a path of x,y locations around the y axis
  NB the path should start at the top of the object to generate the correct normals
  also in order for edges to show correctly include a tiny bevel
  i.e. [..(0,2),(2,1),(1.5,0)..] has a sharp corner at 2,1 and should be entered as
  [..(0,2),(2,1),(2,0.999),(1.5,0)..] to get good shading
  """
  def __init__(self, camera=None, light=None, path=None, sides=12, name="", x=0.0, y=0.0, z=0.0,
               rx=0.0, ry=0.0, rz=0.0, sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *path*
        Array of coordinates rotated to form shape [(x0,y0),(x1,y1)..]
      *sides*
        Number of sides for Shape._lathe() to use.
    """
    super(Lathe, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating lathe ...")

    self.path = path if path != None else []
    self.ttype = GL_TRIANGLES

    self.buf = []
    self.buf.append(self._lathe(path, sides))

  # TODO intervene in call to Buffer.draw() so that face culling can be disabled
  #this draw method disables face culling which allows the backs of faces to show,
  #however the normals will be wrong and it will look as if it is illuminated from the opposite direction to the light source
  #def draw(self, tex=None, shl=GL_UNSIGNED_SHORT):
  #  opengles.glDisable(GL_CULL_FACE)
  #  super(Lathe, self).draw(tex, shl)
  #  opengles.glEnable(GL_CULL_FACE)

########NEW FILE########
__FILENAME__ = LodSprite
from pi3d.constants import *
from pi3d.Texture import Texture
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class LodSprite(Shape):
  """ 3d model inherits from Shape, differs from Plane in being single sided
  Also has the ability to divide into more triangle (than 2) to allow some
  post processing in the vertex shader"""
  def __init__(self, camera=None, light=None, w=1.0, h=1.0, name="",
               x=0.0, y=0.0, z=20.0,
               rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0, n=1):
    """Uses standard constructor for Shape. Extra Keyword arguments:

      *w*
        Width.
      *h*
        Height.
      *n*
        How many cells to divide the plane into
    """
    super(LodSprite, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                 sx, sy, sz, cx, cy, cz)
    self.width = w
    self.height = h
    self.ttype = GL_TRIANGLES
    self.verts = []
    self.norms = []
    self.texcoords = []
    self.inds = []

    ww = w / 2.0
    hh = h / 2.0

    for a in range(n):
      j = float(a)
      for b in range(n):
        i = float(b)
        c = [[i / n, (n - j) / n],
            [(i + 1.0) / n, (n - j) / n],
            [(i + 1.0) / n, (n - 1.0 - j) / n],
            [i / n, (n - 1.0 - j) / n]]
        self.verts.extend([[-ww + c[0][0] * w, -hh + c[0][1] * h, 0.0],
                          [-ww + c[1][0] * w, -hh + c[1][1] * h, 0.0],
                          [-ww + c[2][0] * w, -hh + c[2][1] * h, 0.0],
                          [-ww + c[3][0] * w, -hh + c[3][1] * h, 0.0]])
        self.norms.extend([[0.0, 0.0, -1.0],
                          [0.0, 0.0, -1.0],
                          [0.0, 0.0, -1.0],
                          [0.0, 0.0, -1.0]])
        self.texcoords.extend([[c[0][0], 1.0 - c[0][1]],
                          [c[1][0], 1.0 - c[1][1]],
                          [c[2][0], 1.0 - c[2][1]],
                          [c[3][0], 1.0 - c[3][1]]])
        tri_n = (a * n + b) * 4 # integers
        self.inds.extend([[tri_n , tri_n + 1, tri_n + 3],
                          [tri_n + 1, tri_n + 2, tri_n + 3]])
    self.buf = []
    self.buf.append(Buffer(self, self.verts, self.texcoords, self.inds, self.norms))

  def repaint(self, t):
    self.draw()

########NEW FILE########
__FILENAME__ = MergeShape
from __future__ import absolute_import, division, print_function, unicode_literals

import ctypes
import math
import random

from pi3d.constants import *
from pi3d.Buffer import Buffer

from pi3d.Shape import Shape
from pi3d.util.RotateVec import rotate_vec

class MergeShape(Shape):
  """ 3d model inherits from Shape. As there is quite a time penalty for
  doing the matrix recalculations and changing the variables being sent to
  the shader, each time an object is drawn, it is MUCH faster to use a MergeShape
  where several objects will always remain in the same positions relative to
  each other. i.e. trees in a forest.

  Where the objects have multiple Buffers, each needing a different texture
  (i.e. more complex Model objects) each must be combined into a different
  MergeShape
  """
  def __init__(self, camera=None, light=None, name="",
               x=0.0, y=0.0, z=0.0,
               rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape"""
    super(MergeShape, self).__init__(camera, light, name, x, y, z,
                                   rx, ry, rz, sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating Merge Shape ...")

    self.vertices = []
    self.normals = []
    self.tex_coords = []
    self.indices = []    #stores all indices for single render

    self.buf = []
    self.buf.append(Buffer(self, self.vertices, self.tex_coords, self.indices, self.normals))

  def merge(self, bufr, x=0.0, y=0.0, z=0.0,
            rx=0.0, ry=0.0, rz=0.0,
            sx=1.0, sy=1.0, sz=1.0):
    """merge the vertices, normals etc from this Buffer with those already there
    the position, rotation, scale, offset are set according to the origin of
    the MergeShape. If bufr is not a Buffer then it will be treated as if it
    is a Shape and its first Buffer object will be merged. Argument additional
    to standard Shape:

      *bufr*
        Buffer object or Shape with a member buf[0] that is a Buffer object.
        OR an array or tuple where each element is an array or tuple with
        the required arguments i.e. [[bufr1, x1, y1, z1, rx1, ry1....],
        [bufr2, x2, y2...],[bufr3, x3, y3...]] this latter is a more efficient
        way of building a MergeShape from lots of elements. If multiple
        Buffers are passed in this way then the subsequent arguments (x,y,z etc)
        will be ignored.
    """
    if not isinstance(bufr, list) and not isinstance(bufr, tuple):
      buflist = [[bufr, x, y, z, rx, ry, rz, sx, sy, sz]]
    else:
      buflist = bufr

    for b in buflist:
      if not(type(b[0]) is Buffer):
        bufr = b[0].buf[0]
      else:
        bufr = b[0]

      #assert shape.ttype == GL_TRIANGLES # this is always true of Buffer objects
      assert len(bufr.vertices) == len(bufr.normals)

      if VERBOSE:
        print("Merging", bufr.name)

      original_vertex_count = len(self.vertices)

      for v in range(0, len(bufr.vertices)):
        # Scale, offset and store vertices
        vx, vy, vz = rotate_vec(b[4], b[5], b[6], bufr.vertices[v])
        self.vertices.append((vx * b[7] + b[1], vy * b[8] + b[2], vz * b[9] + b[3]))

        # Rotate normals
        self.normals.append(rotate_vec(b[4], b[5], b[6], bufr.normals[v]))

      self.tex_coords.extend(bufr.tex_coords)

      ctypes.restype = ctypes.c_short  # TODO: remove this side-effect.
      indices = [(i[0] + original_vertex_count, i[1] + original_vertex_count,
                  i[2] + original_vertex_count) for i in bufr.indices]
      self.indices.extend(indices)

    self.buf = []
    self.buf.append(Buffer(self, self.vertices, self.tex_coords, self.indices, self.normals))

  def add(self, bufr, x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
          sx=1.0, sy=1.0, sz=1.0):
    """wrapper to alias merge method"""
    self.merge(bufr, x, y, z, rx, ry, rz, sx, sy, sz)

  def cluster(self, bufr, elevmap, xpos, zpos, w, d, count, options, minscl, maxscl):
    """generates a random cluster on an ElevationMap.

    Arguments:
      *bufr*
        Buffer object to merge.
      *elevmap*
        ElevationMap object to merge onto.
      *xpos, zpos*
        x and z location of centre of cluster.
      *w, d*
        x and z direction size of the cluster.
      *count*
        Number of objects to generate.
      *options*
        Deprecated.
      *minscl*
        The minimum scale value for random selection.
      *maxscl*
        The maximum scale value for random selection.
    """
    #create a cluster of shapes on an elevation map
    blist = []
    for v in range(count):
      x = xpos + random.random() * w - w * 0.5
      z = zpos + random.random() * d - d * 0.5
      rh = random.random() * (maxscl - minscl) + minscl
      rt = random.random() * 360.0
      y = elevmap.calcHeight(x, z) + rh * 2
      blist.append([bufr, x, y, z, 0.0, rt, 0.0, rh, rh, rh])

    #self.merge(bufr, x, y, z, 0.0, rt, 0.0, rh, rh, rh)
    self.merge(blist)

  def radialCopy(self, bufr, x=0, y=0, z=0, startRadius=2.0, endRadius=2.0,
                 startAngle=0.0, endAngle=360.0, step=12):
    """generates a radially copied cluster, axix is in the y direction.

    Arguments:
      *bufr*
        Buffer object to merge.

    Keyword arguments:
      *x,y,z*
        Location of centre of cluster relative to origin of MergeShape.
      *startRadius*
        Start radius.
      *endRadius*
        End radius.
      *startAngle*
        Start angle for merging 0 is in +ve x direction.
      *andAngle*
        End angle for merging, degrees. Rotation is clockwise
        looking up the y axis.
      *step*
        Angle between each copy, degrees NB *NOT* number of steps.
    """
    st = (endAngle - startAngle) / step
    rst = (endRadius - startRadius) / int(st)
    rd = startRadius
    sta = startAngle

    blist = []
    for r in range(int(st)):
      print("merging ", r)
      ca = math.cos(math.radians(sta))
      sa = math.sin(math.radians(sta))
      sta += step
      rd += rst
      blist.append([bufr, x + ca * rd, y, z + sa * rd,
                0, sta, 0, 1.0, 1.0, 1.0])

    self.merge(blist)
    print("merged all")

########NEW FILE########
__FILENAME__ = Model
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *

from pi3d.loader import loaderEgg
from pi3d.loader import loaderObj
from pi3d.Shape import Shape

class Model(Shape):
  """ 3d model inherits from Shape
  loads vertex, normal, uv, index, texture and material data from obj or egg files
  at the moment it doesn't fully implement the features such as animation,
  reflectivity etc
  """
  def __init__(self, camera=None, light=None, file_string=None,
               name="", x=0.0, y=0.0, z=0.0,
               rx=0.0, ry=0.0, rz=0.0, sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *file_string*
        path and name of obj or egg file
    """
    super(Model, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)
    if '__clone__' in file_string:
      # Creating a copy but with pointer to buf.
      return
    self.exf = file_string[-3:].lower()
    if VERBOSE:
      print("Loading ",file_string)

    if self.exf == 'egg':
      self.model = loaderEgg.loadFileEGG(self, file_string)
    elif self.exf == 'obj':
      self.model = loaderObj.loadFileOBJ(self, file_string)
    else:
      print(self.exf, "file not supported")

  def clone(self, camera = None, light = None):
    """create a new Model but buf points to same array of Buffers
    so much quicker to create than reloading all the vertices etc
    """
    newModel = Model(file_string = "__clone__", x=self.unif[0], y=self.unif[1], z=self.unif[2],
               rx=self.unif[3], ry=self.unif[4], rz=self.unif[5], sx=self.unif[6], sy=self.unif[7], sz=self.unif[8],
               cx=self.unif[9], cy=self.unif[10], cz=self.unif[11])
    newModel.buf = self.buf
    newModel.vGroup = self.vGroup
    newModel.shader = self.shader
    newModel.textures = self.textures
    return newModel

  def reparentTo(self, parent):
    #TODO functionality not implemented would need to cope with Shape methods
    if self not in parent.childModel:
      parent.childModel.append(self)

########NEW FILE########
__FILENAME__ = MultiSprite
from pi3d.constants import *
from pi3d.Texture import Texture
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class MultiSprite(Shape):
  """ 3d model inherits from Shape, this is a series of Sprites
  edge to edge to allow larger images than the maximum size of 1920
  imposed by the Texture class
  """
  def __init__(self, textures, shader, camera=None, light=None, w=1.0, h=1.0, name="",
               x=0.0, y=0.0, z=20.0,
               rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0):
    """Uses standard constructor for Shape. Arguments:
      *textures*
        must be a two dimensional list of lists of textures or strings 
        (which must be the path/names of image files) The array runs left
        to right then down so six textures in spreadsheet notation would be
        
        [[R1C1, R1C2], [R2C1, R2C2], [R3C1, R3C2]]
        
      *shader*
        shader to use
        
      Extra keyword arguments:  
        
      *w*
        Width.
      *h*
        Height.
    """
    try:
      nh = len(textures)
      nw = len(textures[0])
      super(MultiSprite, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                   sx, sy, sz, cx, cy, cz)
      self.width = w
      self.height = h
      self.ttype = GL_TRIANGLES
      self.verts = []
      self.norms = []
      self.texcoords = []
      self.inds = []

      ww = w / 2.0 / nw
      hh = h / 2.0 / nh
      self.buf = []
      for i in range(nw):
        for j in range(nh):
          offw = w * ((1.0 - nw) / 2.0 + i) / nw
          offh = -h * ((1.0 - nh) / 2.0 + j) / nh
          self.verts = ((-ww + offw, hh + offh, 0.0), 
                        (ww + offw, hh + offh, 0.0), 
                        (ww + offw, -hh + offh, 0.0), 
                        (-ww + offw, -hh + offh, 0.0))
          self.norms = ((0, 0, -1), (0, 0, -1),  (0, 0, -1), (0, 0, -1))
          self.texcoords = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0 , 1.0))

          self.inds = ((0, 1, 3), (1, 2, 3))

          thisbuf = Buffer(self, self.verts, self.texcoords, self.inds, self.norms)
          if not isinstance(textures[j][i], Texture): # i.e. can load from file name
            textures[j][i] = Texture(textures[j][i])
          thisbuf.textures = [textures[j][i]]
          self.buf.append(thisbuf)
      self.set_shader(shader)
      self.set_2d_size() # method in Shape, default full window size
    except IndexError:
      print('Must supply a list of lists of Textures or strings')
      return

########NEW FILE########
__FILENAME__ = Plane
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class Plane(Shape):
  """ 3d model inherits from Shape, differs from Sprite in being two sided"""
  def __init__(self, camera=None, light=None, w=1.0, h=1.0, name="",
               x=0.0, y=0.0, z=0.0,
               rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *w*
        width
      *h*
        height
    """
    super(Plane, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating plane ...")

    self.width = w
    self.height = h
    self.ttype = GL_TRIANGLES
    self.verts = []
    self.norms = []
    self.texcoords = []
    self.inds = []

    ww = w / 2.0
    hh = h / 2.0

    self.verts = ((-ww, hh, 0.0), (ww, hh, 0.0), (ww, -hh, 0.0), (-ww, -hh, 0.0),
                  (-ww, hh, 0.0), (ww, hh, 0.0), (ww, -hh, 0.0), (-ww, -hh, 0.0))
    self.norms = ((0.0, 0.0, -1), (0.0, 0.0, -1),  (0.0, 0.0, -1), (0.0, 0.0, -1),
                  (0.0, 0.0, 1), (0.0, 0.0, 1),  (0.0, 0.0, 1), (0.0, 0.0, 1))
    self.texcoords = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0),
                      (0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))

    self.inds = ((0, 1, 3), (1, 2, 3), (5, 4, 7), (6, 5, 7))

    self.buf = []
    self.buf.append(Buffer(self, self.verts, self.texcoords, self.inds, self.norms))

########NEW FILE########
__FILENAME__ = Points
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class Points(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self,  camera=None, light=None, vertices=[], material=(1.0,1.0,1.0),
               point_size = 1, name="", x=0.0, y=0.0, z=0.0, sx=1.0, sy=1.0, sz=1.0,
               rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *vertices*
        array of tuples [(x0,y0,z0),(x1,y1,z1)..]
      *material*
        tuple (r,g,b)
      *point_size*
        set to 1 if absent or set to a value less than 1
    """
    super(Points, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating Points ...")

    self.vertices = vertices
    self.normals = []
    n_v = len(vertices)
    self.indices = [(a, a + 1, a + 2) for a in range(0, n_v, 3)]
    self.tex_coords = []
    self.buf = [Buffer(self, self.vertices, self.tex_coords, self.indices,
                self.normals, smooth=False)]

    if point_size < 1:
      self.set_point_size(1)
    else:
      self.set_point_size(point_size)
    self.set_material(material)


########NEW FILE########
__FILENAME__ = Sphere
from __future__ import absolute_import, division, print_function, unicode_literals

import math

from pi3d.constants import *
from pi3d.util import Utility
from pi3d.Shape import Shape

class Sphere(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self, camera=None, light=None,
               radius=1, slices=12, sides=12, hemi=0.0, name="",
               x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0, invert=False):
    """uses standard constructor for Shape extra Keyword arguments:

      *radius*
        radius of sphere
      *slices*
        number of latitude edges
      *hemi*
        if set to 0.5 it will only construct the top half of sphere
      *sides*
        number of sides for Shape._lathe() to use
      *invert*
        normals will face inwards, Texture will need flip=True
    """
    super(Sphere, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating sphere ...")

    path = []
    #extra points added at poles to reduce distortion (mainly normals)
    st = ((math.pi - 0.002) * (1.0 - hemi)) / slices
    path.append((0.0, radius))
    for r in range(slices + 1):
      x, y = Utility.from_polar_rad(r * st + 0.001, radius)
      path.append((y, x))
    x, y = Utility.from_polar_rad(r * st + 0.002, radius)
    path.append((y, x))
    if invert:
      path.reverse()

    self.radius = radius
    self.slices = slices
    self.hemi = hemi
    self.ttype = GL_TRIANGLES

    self.buf = []
    self.buf.append(self._lathe(path, sides))

########NEW FILE########
__FILENAME__ = Sprite
from pi3d.constants import *
from pi3d.Texture import Texture
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class Sprite(Shape):
  """ 3d model inherits from Shape, differs from Plane in being single sided"""
  def __init__(self, camera=None, light=None, w=1.0, h=1.0, name="",
               x=0.0, y=0.0, z=20.0,
               rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0,
               cx=0.0, cy=0.0, cz=0.0):
    """Uses standard constructor for Shape. Extra Keyword arguments:

      *w*
        Width.
      *h*
        Height.
    """
    super(Sprite, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                 sx, sy, sz, cx, cy, cz)
    self.width = w
    self.height = h
    self.ttype = GL_TRIANGLES
    self.verts = []
    self.norms = []
    self.texcoords = []
    self.inds = []

    ww = w / 2.0
    hh = h / 2.0

    self.verts = ((-ww, hh, 0.0), (ww, hh, 0.0), (ww, -hh, 0.0), (-ww, -hh, 0.0))
    self.norms = ((0, 0, -1), (0, 0, -1),  (0, 0, -1), (0, 0, -1))
    self.texcoords = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0 , 1.0))

    self.inds = ((0, 1, 3), (1, 2, 3))

    self.buf = []
    self.buf.append(Buffer(self, self.verts, self.texcoords, self.inds, self.norms))

  def repaint(self, t):
    self.draw()


class ImageSprite(Sprite):
  """A 2D sprite containing a texture and shader. The constructor also
  calls set_2d_size so that ImageSprite objects can be used directly to draw
  on a Canvas shape (if shader=2d_flat). Additional arguments:

    *texture*
      either a Texture object or, if not a Texture, will attempt to load
      a file using texture as a path and name to an image.
    *shader*
      a Shader object
  """
  def __init__(self, texture, shader, **kwds):
    super(ImageSprite, self).__init__(**kwds)
    if not isinstance(texture, Texture): # i.e. can load from file name
      texture = Texture(texture)
    self.set_shader(shader)
    self.buf[0].set_draw_details(shader, [texture])
    self.set_2d_size() # method in Shape, default full window size

  def _load_opengl(self):
    self.buf[0].textures[0].load_opengl()

  def _unload_opengl(self):
    self.buf[0].textures[0].unload_opengl()

########NEW FILE########
__FILENAME__ = TCone
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Shape import Shape

class TCone(Shape):
  """ 3d model inherits from Shape, creates truncated cone axis y direction"""
  def __init__(self, camera=None, light=None,
               radiusBot=1.2, radiusTop=0.8, height=2.0, sides=12,
               name="", x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *radiusBot*
        Radius of the bottom.
      *radiusTop*
        Radius at the top.
      *height*
        Height.
      *sides*
        Number of sides to divide edges of polygons.
    """
    super(TCone, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating Truncated Cone ...")

    path = []
    path.append((0, height * .5))
    path.append((radiusTop, height * .5))
    path.append((radiusTop, height * .4999))
    path.append((radiusBot, -height * .4999))
    path.append((radiusBot, -height * .5))
    path.append((0, -height * .5))

    self.radiusBot = radiusBot
    self.radiusTop = radiusTop
    self.height = height
    self.ttype = GL_TRIANGLES

    self.buf = []
    self.buf.append(self._lathe(path, sides))

########NEW FILE########
__FILENAME__ = Tetrahedron
from pi3d.constants import *
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class Tetrahedron(Shape):
  """ 3d model inherits from Shape. The simplest 3D shape
  """
  def __init__(self,  camera=None, light=None, name="", 
                corners=((-1.0, -0.57735, -0.57735),
                         (1.0, -0.57735, -0.57735),
                         (0.0, -0.57735, 1.15470),
                         (0.0, 1.15470, 0.0)),
                x=0.0, y=0.0, z=0.0, sx=1.0, sy=1.0, sz=1.0,
                rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0):
    """Uses standard constructor for Shape with ability to position corners.
    The uv mapping is taken from four equilateral triangles arranged on a
    square forming an upwards pointing arrow ^. Starting at the left bottom
    corner of the image the first three triangles are unwrapped from around
    the top of the tetrahedron and the right bottom triangle is the base
    (if the corners are arranged as per the default) Keyword argument:

      *corners*
        A tuple of four (xyz) tuples defining the corners
    """
    super(Tetrahedron, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)
    self.ttype = GL_TRIANGLES
    c = corners # alias
    self.verts = (c[0], c[3], c[1], c[2], c[3], c[0],
                  c[1], c[3], c[2], c[0], c[1], c[2])
    self.texcoords = ((0.0, 0.0), (0.0, 0.57735), (0.5, 0.288675),
                      (0.0, 0.57735), (0.5, 0.866025), (0.5, 0.288675),
                      (0.5, 0.866025), (1.0, 0.57735), (0.5, 0.288675),
                      (0.5, 0.288675), (1.0, 0.57735), (1.0, 0.0))
    self.inds = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11))

    self.buf = []
    self.buf.append(Buffer(self, self.verts, self.texcoords, self.inds, normals=None, smooth=False))

########NEW FILE########
__FILENAME__ = Torus
from __future__ import absolute_import, division, print_function, unicode_literals

import math

from pi3d.constants import *
from pi3d.util import Utility
from pi3d.Shape import Shape

class Torus(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self, camera=None, light=None, radius=2.0, thickness=0.5, ringrots=6, sides=12, name="",
               x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *radius*
        Major radius of torus
      *thickness*
        Minor radius, section through one side of torus
      *ringrots*
        Sides around minor radius circle
      *sides*
        Number of sides for Shape._lathe() to use
    """
    super(Torus,self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                               sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating Torus ...")

    path = []
    st = (math.pi * 2)/ringrots
    for r in range(ringrots + 1):
      x, y = Utility.from_polar_rad(r * st, thickness)
      path.append((radius + y, x))  # TODO: why the reversal?

    self.radius = radius
    self.thickness = thickness
    self.ringrots = ringrots
    self.ttype = GL_TRIANGLES

    self.buf = []
    self.buf.append(self._lathe(path, sides))

########NEW FILE########
__FILENAME__ = Triangle
from pi3d.constants import *
from pi3d.Buffer import Buffer
from pi3d.Shape import Shape

class Triangle(Shape):
  """ 3d model inherits from Shape. The simplest possible shape: a single
  triangle
  """
  def __init__(self,  camera=None, light=None, name="", 
                corners=((-0.5, -0.28868), (0.0, 0.57735), (0.5, -0.28868)),
                x=0.0, y=0.0, z=0.0, sx=1.0, sy=1.0, sz=1.0,
                rx=0.0, ry=0.0, rz=0.0, cx=0.0, cy=0.0, cz=0.0):
    """Uses standard constructor for Shape with ability to position corners.
    The corners must be arranged clockwise (for the Triangle to face -z direction)
    The uv mapping is taken from an equilateral triangles base 0,0 to 1,0
    peak at 0.5, 0.86603 Keyword argument:

      *corners*
        A tuple of three (xy) tuples defining the corners
    """
    super(Triangle, self).__init__(camera, light, name, x, y, z, rx, ry, rz,
                                sx, sy, sz, cx, cy, cz)
    self.ttype = GL_TRIANGLES
    self.verts = []
    self.norms = []
    self.texcoords = []
    self.inds = []
    c = corners # alias for convenience

    self.verts = ((c[0][0], c[0][1], 0.0), (c[1][0], c[1][1], 0.0), (c[2][0], c[2][1], 0.0))
    self.norms = ((0, 0, -1), (0, 0, -1),  (0, 0, -1))
    self.texcoords = ((0.0, 0.0), (0.5, 0.86603), (1.0, 0.0))

    self.inds = ((0, 1, 2), ) #python quirk: comma for tuple with only one val

    self.buf = []
    self.buf.append(Buffer(self, self.verts, self.texcoords, self.inds, self.norms))

########NEW FILE########
__FILENAME__ = Tube
from __future__ import absolute_import, division, print_function, unicode_literals

from pi3d.constants import *
from pi3d.Shape import Shape

class Tube(Shape):
  """ 3d model inherits from Shape"""
  def __init__(self, camera=None, light=None, radius=1.0, thickness=0.5, height=2.0, sides=12, name="",
               x=0.0, y=0.0, z=0.0, rx=0.0, ry=0.0, rz=0.0,
               sx=1.0, sy=1.0, sz=1.0, cx=0.0, cy=0.0, cz=0.0):
    """uses standard constructor for Shape extra Keyword arguments:

      *radius*
        Radius of to mid point of wall.
      *thickness*
        of wall of tube.
      *height*
        Length of tube.
      *sides*
        Number of sides for Shape._lathe() to use.
    """
    super(Tube, self).__init__(camera, light, name, x, y, z, rx, ry, rz, sx, sy, sz, cx, cy, cz)

    if VERBOSE:
      print("Creating Tube ...")

    t = thickness * 0.5
    path = []
    path.append((radius - t, height * .5))
    path.append((radius + t, height * .5))
    path.append((radius + t, height * .4999))
    path.append((radius + t, -height * .4999))
    path.append((radius + t, -height * .5))
    path.append((radius - t, -height * .5))
    path.append((radius - t, -height * .4999))
    path.append((radius - t, height * .4999))
    path.append((radius - t, height * .5))

    self.radius = radius
    self.thickness = thickness
    self.height = height
    self.ttype = GL_TRIANGLES

    self.buf = []
    self.buf.append(self._lathe(path, sides))

########NEW FILE########
__FILENAME__ = Shape
from __future__ import absolute_import, division, print_function, unicode_literals

import ctypes

from numpy import array, dot
from math import radians, pi, sin, cos

from pi3d.constants import *
from pi3d.Buffer import Buffer
from pi3d.Light import Light
from pi3d.util import Utility
from pi3d.util.Ctypes import c_floats

from pi3d.util.Loadable import Loadable

class Shape(Loadable):
  """inherited by all shape objects, including simple 2D sprite types"""
  def __init__(self, camera, light, name, x, y, z,
               rx, ry, rz, sx, sy, sz, cx, cy, cz):
    """
    Arguments:
      *light*
        Light instance: if None then Light.instance() will be used.
      *name*
        Name string for identification.
      *x, y, z*
        Location of the origin of the shape, stored in a uniform array.
      *rx, ry, rz*
        Rotation of shape in degrees about each axis.
      *sx, sy, sz*
        Scale in each direction.
      *cx, cy, cz*
        Offset vertices from origin in each direction.
    """
    super(Shape, self).__init__()
    self.name = name
    light = light or Light.instance()
    # uniform variables all in one array (for Shape and one for Buffer)
    self.unif = (ctypes.c_float * 60)(
      x, y, z, rx, ry, rz,
      sx, sy, sz, cx, cy, cz,
      0.5, 0.5, 0.5, 5000.0, 0.8, 1.0,
      0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
      light.lightpos[0], light.lightpos[1], light.lightpos[2],
      light.lightcol[0], light.lightcol[1], light.lightcol[2],
      light.lightamb[0], light.lightamb[1], light.lightamb[2])
    """ pass to shader array of vec3 uniform variables:

    ===== ========================================== ==== ==
    vec3  description                                python
    ----- ------------------------------------------ -------
    index                                            from to
    ===== ========================================== ==== ==
       0  location                                     0   2
       1  rotation                                     3   5
       2  scale                                        6   8
       3  offset                                       9  11
       4  fog shade                                   12  14
       5  fog distance, fog alpha, shape alpha        15  17
       6  camera position                             18  20
       7  unused: custom data space                   21  23
       8  light0 position, direction vector           24  26
       9  light0 strength per shade                   27  29
      10  light0 ambient values                       30  32
      11  light1 position, direction vector           33  35
      12  light1 strength per shade                   36  38
      13  light1 ambient values                       39  41
      14  defocus dist, amount (only 2 used)          42  43
      15  defocus frame width, height (only 2 used)   45  46
      16  custom data space                           48  50
      17  custom data space                           51  53
      18  custom data space                           54  56
      19  custom data space                           57  59
    ===== ========================================== ==== ==

    Shape holds matrices that are updated each time it is moved or rotated
    this saves time recalculating them each frame as the Shape is drawn
    """
    self.tr1 = array([[1.0, 0.0, 0.0, 0.0],
                      [0.0, 1.0, 0.0, 0.0],
                      [0.0, 0.0, 1.0, 0.0],
                      [self.unif[0] - self.unif[9], self.unif[1] - self.unif[10], self.unif[2] - self.unif[11], 1.0]])
    """translate to position - offset"""
    s, c = sin(radians(self.unif[3])), cos(radians(self.unif[3]))
    self.rox = array([[1.0, 0.0, 0.0, 0.0],
                      [0.0, c, s, 0.0],
                      [0.0, -s, c, 0.0],
                      [0.0, 0.0, 0.0, 1.0]])
    """rotate about x axis"""
    s, c = sin(radians(self.unif[4])), cos(radians(self.unif[4]))
    self.roy = array([[c, 0.0, -s, 0.0],
                      [0.0, 1.0, 0.0, 0.0],
                      [s, 0.0, c, 0.0],
                      [0.0, 0.0, 0.0, 1.0]])
    """rotate about y axis"""
    s, c = sin(radians(self.unif[5])), cos(radians(self.unif[5]))
    self.roz = array([[c, s, 0.0, 0.0],
                      [-s, c, 0.0, 0.0],
                      [0.0, 0.0, 1.0, 0.0],
                      [0.0, 0.0, 0.0, 1.0]])
    """rotate about z axis"""
    self.scl = array([[self.unif[6], 0.0, 0.0, 0.0],
                      [0.0, self.unif[7], 0.0, 0.0],
                      [0.0, 0.0, self.unif[8], 0.0],
                      [0.0, 0.0, 0.0, 1.0]])
    """scale"""
    self.tr2 = array([[1.0, 0.0, 0.0, 0.0],
                      [0.0, 1.0, 0.0, 0.0],
                      [0.0, 0.0, 1.0, 0.0],
                      [self.unif[9], self.unif[10], self.unif[11], 1.0]])
    """translate to offset"""
    self.MFlg = True
    self.M = (ctypes.c_float * 32)(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    self._camera = camera
    self.shader = None
    self.textures = []

    self.buf = []
    """self.buf contains a buffer for each part of this shape that needs
    rendering with a different Shader/Texture. self.draw() relies on objects
    inheriting from this filling buf with at least one element.
    """
    
    self.children = []

  def draw(self, shader=None, txtrs=None, ntl=None, shny=None, camera=None, mlist=[]):
    """If called without parameters, there has to have been a previous call to
    set_draw_details() for each Buffer in buf[].
    NB there is no facility for setting umult and vmult with draw: they must be
    set using set_draw_details or Buffer.set_draw_details.
    """
    self.load_opengl() # really just to set the flag so _unload_opengl runs

    from pi3d.Camera import Camera

    camera = camera or self._camera or Camera.instance()
    shader = shader or self.shader
    shader.use()

    if self.MFlg == True or len(mlist):
      # Calculate rotation and translation matrix for this model using numpy.
      self.MRaw = dot(self.tr2,
        dot(self.scl,
            dot(self.roy,
                dot(self.rox,
                    dot(self.roz, self.tr1)))))
      # child drawing addition #############
      newmlist = [m for m in mlist]
      newmlist.append(self.MRaw)
      if len(self.children) > 0:
        for c in self.children:
          c.draw(shader, txtrs, ntl, shny, camera, newmlist)
      for m in mlist[-1::-1]:
        self.MRaw = dot(self.MRaw, m)
      ######################################
      self.M[0:16] = self.MRaw.ravel()
      #self.M[0:16] = c_floats(self.MRaw.reshape(-1).tolist()) #pypy version
      self.M[16:32] = dot(self.MRaw, camera.mtrx).ravel()
      #self.M[16:32] = c_floats(dot(self.MRaw, camera.mtrx).reshape(-1).tolist()) #pypy
      self.MFlg = False

    elif camera.was_moved:
      # Only do this if it's not done because model moved.
      self.M[16:32] = dot(self.MRaw, camera.mtrx).ravel()

    if camera.was_moved:
      self.unif[18:21] = camera.eye[0:3]

    opengles.glUniformMatrix4fv(shader.unif_modelviewmatrix, 2,
                                ctypes.c_int(0),
                                ctypes.byref(self.M))

    opengles.glUniform3fv(shader.unif_unif, 20, ctypes.byref(self.unif))
    for b in self.buf:
      # Shape.draw has to be passed either parameter == None or values to pass
      # on.
      b.draw(self, shader, txtrs, ntl, shny)

  def set_shader(self, shader):
    """Wrapper method to set just the Shader for all the Buffer objects of
    this Shape. Used, for instance, in a Model where the Textures have been
    defined in the obj & mtl files, so you can't use set_draw_details.

    Arguments:

      *shader*
        Shader to use

    """

    self.shader = shader
    for b in self.buf:
      b.shader = shader

  def set_normal_shine(self, normtex, ntiles=1.0, shinetex=None,
                       shiny=0.0, is_uv=True):
    """Used to set some of the draw details for all Buffers in Shape.
    This is useful where a Model object has been loaded from an obj file and
    the textures assigned automatically.

    Arguments:
      *normtex*
        Normal map Texture to use.

    Keyword arguments:
      *ntiles*
        Multiplier for the tiling of the normal map.
      *shinetex*
        Reflection Texture to use.
      *shiny*
        Strength of reflection (ranging from 0.0 to 1.0).
      *is_uv*
        If True then the normtex will be textures[1] and shinetex will be
        textures[2] i.e. if using a 'uv' type Shader. However, for 'mat' type
        Shaders they are moved down one, as the basic shade is defined by
        material rgb rather than from a Texture.
    """
    ofst = 0 if is_uv else -1
    for b in self.buf:
      b.textures = b.textures or []
      if is_uv and not b.textures:
        b.textures = [normtex]
      while len(b.textures) < (2 + ofst):
        b.textures.append(None)
      b.textures[1 + ofst] = normtex
      b.unib[0] = ntiles
      if shinetex:
        while len(b.textures) < (3 + ofst):
          b.textures.append(None)
        b.textures[2 + ofst] = shinetex
        b.unib[1] = shiny

  def set_draw_details(self, shader, textures, ntiles = 0.0, shiny = 0.0,
                      umult=1.0, vmult=1.0):
    """Wrapper to call set_draw_details() for each Buffer object.

    Arguments:
      *shader*
        Shader object
      *textures*
        array of Texture objects
    """
    self.shader = shader
    for b in self.buf:
      b.set_draw_details(shader, textures, ntiles, shiny, umult, vmult)

  def set_material(self, material):
    """Wrapper for setting material shade in each Buffer object.

    Arguments:
      *material*
        tuple (rgb)
    """
    for b in self.buf:
      b.set_material(material)

  def set_offset(self, offset):
    """Wrapper for setting uv texture offset in each Buffer object.

    Arguments:
      *offset*
        tuple (u_off, v_off) values between 0.0 and 1.0 to offset the texture
        sampler by
    """
    for b in self.buf:
      b.set_offset(offset)

  def offset(self):
    """Get offset as (u, v) tuple of (first) buf uv. Doesnt check that buf array
    exists and has at least one value and only returns offset for that value"""
    return self.buf[0].unib[9:11]


  def set_fog(self, fogshade, fogdist):
    """Set fog for this Shape only, it uses the shader smoothblend function from
    1/3 fogdist to fogdist.

    Arguments:
      *fogshade*
        tuple (rgba)
      *fogdist*
        distance from Camera at which Shape is 100% fogshade
    """
    self.unif[12:15] = fogshade[0:3]
    self.unif[15] = fogdist
    self.unif[16] = fogshade[3]

  def set_alpha(self, alpha=1.0):
    """Set alpha for this Shape only

    Arguments:
      *alpha*
        alpha value between 0.0 and 1.0 (default)
    """
    self.unif[17] = alpha

  def alpha(self):
    """Get value of alpha"""
    return self.unif[17]

  def set_light(self, light, num=0):
    """Set the values of the lights.

    Arguments:
      *light*
        Light object to use
      *num*
        number of the light to set
    """
    #TODO (pg) need MAXLIGHTS global variable, room for two now but shader
    # only uses 1.
    if num > 1 or num < 0:
      num = 0
    stn = 24 + num * 9
    self.unif[stn:(stn + 3)] = light.lightpos[0:3]
    self.unif[(stn + 3):(stn + 6)] = light.lightcol[0:3]
    self.unif[(stn + 6):(stn + 9)] = light.lightamb[0:3]

  def set_2d_size(self, w=None, h=None, x=0, y=0):
    """saves size to be drawn and location in pixels for use by 2d shader

    Keyword arguments:

      *w*
        Width, pixels.
      *h*
        Height, pixels.
      *x*
        Left edge of image from left edge of display, pixels.
      *y*
        Top of image from top of display, pixels

    """
    from pi3d.Display import Display
    if w == None:
      w = Display.INSTANCE.width
    if h == None:
      h = Display.INSTANCE.height
    self.unif[42:44] = [x, y]
    self.unif[45:48] = [w, h, Display.INSTANCE.height]

  def set_2d_location(self, x, y):
    """saves location in pixels for use by 2d shader

    Arguments:

      *x*
        Left edge of image from left edge of display, pixels.
      *y*
        Top of image from top of display, pixels

    """
    self.unif[42:44] = [x, y]

  def set_custom_data(self, index_from, data):
    """save general purpose custom data for use by any shader **NB it is up
    to the user to provide data in the form of a suitable array of values
    that will fit into the space available in the unif array**

    Arguments:

      *index_from*
        start index in unif array for filling data should be 48 to 59 though
        42 to 47 could be used if they do not conflict with existing shaders
        i.e. 2d_flat, defocus etc
      *data*
        array of values to put in
    """
    self.unif[index_from:(index_from + len(data))] = data

  def set_point_size(self, point_size=0.0):
    """if this is > 0.0  the vertices will be drawn as points"""
    for b in self.buf:
      b.unib[8] = point_size

  def add_child(self, child):
    """puts a Shape into the children list"""
    self.children.append(child)

  def x(self):
    """get value of x"""
    return self.unif[0]

  def y(self):
    """get value of y"""
    return self.unif[1]

  def z(self):
    """get value of z"""
    return self.unif[2]

  def get_bounds(self):
    """Find the limits of vertices in three dimensions. Returns a tuple
    (left, bottom, front, right, top, back)
    """
    left, bottom, front  = 10000, 10000, 10000
    right, top, back = -10000, -10000, -10000
    for b in self.buf:
      for v in b.vertices:
        if v[0] < left:
          left = v[0]
        if v[0] > right:
          right = v[0]
        if v[1] < bottom:
          bottom = v[1]
        if v[1] > top:
          top = v[1]
        if v[2] < front:
          front = v[2]
        if v[2] > back:
          back = v[2]

    return (left, bottom, front, right, top, back)

  def scale(self, sx, sy, sz):
    """Arguments:

      *sx*
        x scale
      *sy*
        y scale
      *sz*
        z scale
    """
    self.scl[0, 0] = sx
    self.scl[1, 1] = sy
    self.scl[2, 2] = sz
    self.unif[6:9] = sx, sy, sz
    self.MFlg = True

  def position(self, x, y, z):
    """Arguments:

      *x*
        x position
      *y*
        y position
      *z*
        z position
    """
    self.tr1[3, 0] = x - self.unif[9]
    self.tr1[3, 1] = y - self.unif[10]
    self.tr1[3, 2] = z - self.unif[11]
    self.unif[0:3] = x, y, z
    self.MFlg = True

  def positionX(self, v):
    """Arguments:

      *v*
        x position
    """
    self.tr1[3, 0] = v - self.unif[9]
    self.unif[0] = v
    self.MFlg = True

  def positionY(self, v):
    """Arguments:

      *v*
        y position
    """
    self.tr1[3, 1] = v - self.unif[10]
    self.unif[1] = v
    self.MFlg = True

  def positionZ(self, v):
    """Arguments:

      *v*
        z position
    """
    self.tr1[3, 2] = v - self.unif[11]
    self.unif[2] = v
    self.MFlg = True

  def translate(self, dx, dy, dz):
    """Arguments:

      *dx*
        x translation
      *dy*
        y translation
      *dz*
        z translation
    """
    self.tr1[3, 0] += dx
    self.tr1[3, 1] += dy
    self.tr1[3, 2] += dz
    self.MFlg = True
    self.unif[0] += dx
    self.unif[1] += dy
    self.unif[2] += dz

  def translateX(self, v):
    """Arguments:

      *v*
        x translation
    """
    self.tr1[3, 0] += v
    self.unif[0] += v
    self.MFlg = True

  def translateY(self, v):
    """Arguments:

      *v*
        y translation
    """
    self.tr1[3, 1] += v
    self.unif[1] += v
    self.MFlg = True

  def translateZ(self, v):
    """Arguments:

      *v*
        z translation
    """
    self.tr1[3, 2] += v
    self.unif[2] += v
    self.MFlg = True

  def rotateToX(self, v):
    """Arguments:

      *v*
        x rotation
    """
    s, c = sin(radians(v)), cos(radians(v))
    self.rox[1, 1] = self.rox[2, 2] = c
    self.rox[1, 2] = s
    self.rox[2, 1] = -s
    self.unif[3] = v
    self.MFlg = True

  def rotateToY(self, v):
    """Arguments:

      *v*
        y rotation
    """
    s, c = sin(radians(v)), cos(radians(v))
    self.roy[0, 0] = self.roy[2, 2] = c
    self.roy[0, 2] = -s
    self.roy[2, 0] = s
    self.unif[4] = v
    self.MFlg = True

  def rotateToZ(self, v):
    """Arguments:

      *v*
        z rotation
    """
    s, c = sin(radians(v)), cos(radians(v))
    self.roz[0, 0] = self.roz[1, 1] = c
    self.roz[0, 1] = s
    self.roz[1, 0] = -s
    self.unif[5] = v
    self.MFlg = True

  def rotateIncX(self, v):
    """Arguments:

      *v*
        x rotational increment
    """
    self.unif[3] += v
    s, c = sin(radians(self.unif[3])), cos(radians(self.unif[3]))
    self.rox[1, 1] = self.rox[2, 2] = c
    self.rox[1, 2] = s
    self.rox[2, 1] = -s
    self.MFlg = True

  def rotateIncY(self, v):
    """Arguments:

      *v*
        y rotational increment
    """
    self.unif[4] += v
    s, c = sin(radians(self.unif[4])), cos(radians(self.unif[4]))
    self.roy[0, 0] = self.roy[2, 2] = c
    self.roy[0, 2] = -s
    self.roy[2, 0] = s
    self.MFlg = True

  def rotateIncZ(self, v):
    """Arguments:

      *v*
        z rotational increment
    """
    self.unif[5] += v
    s, c = sin(radians(self.unif[5])), cos(radians(self.unif[5]))
    self.roz[0, 0] = self.roz[1, 1] = c
    self.roz[0, 1] = s
    self.roz[1, 0] = -s
    self.MFlg = True

  def _lathe(self, path, sides=12, rise=0.0, loops=1.0):
    """Returns a Buffer object by rotating the points defined in path.

    Arguments:
      *path*
        An array of points [(x0, y0), (x1, y1) ...] to rotate around
        the y axis.

    Keyword arguments:
      *sides*
        Number of sides to divide each rotation into.
      *rise*
        Amount to increment the path y values for each rotation (ie helix)
      *loops*
        Number of times to rotate the path by 360 (ie helix).

    """
    self.sides = sides

    s = len(path)
    rl = int(self.sides * loops)

    pn = 0
    pp = 0
    tcx = 1.0 / self.sides
    pr = (pi / self.sides) * 2.0
    rdiv = rise / rl

    # Find largest and smallest y of the path used for stretching the texture
    miny = path[0][1]
    maxy = path[s-1][1]
    for p in range(s):
      if path[p][1] < miny:
        miny = path[p][1]
      if path[p][1] > maxy:
        maxy = path[p][1]

    verts = []
    norms = []
    idx = []
    tex_coords = []

    opx = path[0][0]
    opy = path[0][1]

    for p in range(s):

      px = path[p][0] * 1.0
      py = path[p][1] * 1.0

      tcy = 1.0 - ((py - miny) / (maxy - miny))

      # Normalized 2D vector between path points
      dx, dy = Utility.vec_normal(Utility.vec_sub((px, py), (opx, opy)))

      for r in range (0, rl):
        sinr = sin(pr * r)
        cosr = cos(pr * r)
        verts.append((px * sinr, py, px * cosr))
        norms.append((-sinr * dy, dx, -cosr * dy))
        tex_coords.append((1.0 - tcx * r, tcy))
        py += rdiv

      # Last path profile (tidies texture coords).
      verts.append((0, py, px))
      norms.append((0, dx, -dy))
      tex_coords.append((0, tcy))

      if p < s - 1:
        pn += (rl + 1)
        for r in range(rl):
          idx.append((pp + r + 1, pp + r, pn + r))
          idx.append((pn + r, pn + r + 1, pp + r + 1))
        pp += (rl + 1)

      opx = px
      opy = py

    return Buffer(self, verts, tex_coords, idx, norms)

########NEW FILE########
__FILENAME__ = Ball
from pi3d.Display import Display
from numpy import dot

from pi3d.shape.Sprite import ImageSprite

class Ball(ImageSprite):
  """ This class is used to take some of the functionality of the CollisionBalls
  demo out of the main file. It inherits from the ImageSprite class that is
  passed (in addition to standard Shape constructor arguments) the Shader and
  the [Texture] to use.
  In order to fit the Display dimensions the z value has to be set to 1000
  This allows the Ball dimensions to be set in approximately pixel sizes
  """
  def __init__(self, camera=None, light=None, shader=None, texture=None,
               radius=0.0, x=0.0, y=0.0, z=1000, vx=0.0, vy=0.0, decay=0.001):
    super(Ball, self).__init__(texture=texture, shader=shader,
                              camera=camera, light=light, w=2.0*radius,
                              h=2.0*radius, name="",x=x, y=y, z=z)
    self.radius = radius
    #self.unif[0] = x
    #self.unif[1] = y
    #self.unif[2] = z
    self.vx = vx
    self.vy = vy
    self.mass = radius * radius
    self.decay = decay

  def move(self):
    self.translateX(self.vx)
    self.translateY(self.vy)

  def hit(self, otherball):
    """Used for pre-checking ball positions."""
    dx = (self.unif[0] + self.vx) - (otherball.unif[0] + otherball.vx)
    dy = (self.unif[1] + self.vy) - (otherball.unif[1] + otherball.vy)
    rd = self.radius + otherball.radius
    return dot(dx, dy) < (rd * rd)

  def bounce_collision(self, otherball):
    """work out resultant velocities using 17th.C phsyics"""
    # relative positions
    dx = self.unif[0] - otherball.unif[0]
    dy = self.unif[1] - otherball.unif[1]
    rd = self.radius + otherball.radius
    # check sign of a.b to see if converging
    dotP = dot([dx, dy, 0.0],
               [self.vx - otherball.vx, self.vy - otherball.vy, 0.0])
    if dx * dx + dy * dy <= rd * rd and dotP < 0:
      R = otherball.mass / self.mass #ratio of masses
      """Glancing angle for equating angular momentum before and after collision.
      Three more simultaneous equations for x and y components of momentum and
      kinetic energy give:
      """
      if dy:
        D = dx / dy
        delta2y = 2 * (D * self.vx + self.vy -
                       D * otherball.vx - otherball.vy) / (
          (1 + D * D) * (R + 1))
        delta2x = D * delta2y
        delta1y = -1 * R * delta2y
        delta1x = -1 * R * D * delta2y
      elif dx:
        # Same code as above with x and y reversed.
        D = dy / dx
        delta2x = 2 * (D * self.vy + self.vx -
                       D * otherball.vy - otherball.vx) / (
          (1 + D * D) * (R + 1))
        delta2y = D * delta2x
        delta1x = -1 * R * delta2x
        delta1y = -1 * R * D * delta2x
      else:
        delta1x = delta1y = delta2x = delta2y = 0

      self.vx += delta1x
      self.vy += delta1y
      otherball.vx += delta2x
      otherball.vy += delta2y

  def bounce_wall(self, width, height):
    left, right, top, bottom = -width/2.0, width/2.0, height/2.0, -height/2.0
    if self.unif[0] > (right - self.radius):
      self.vx = -abs(self.vx)
    elif self.unif[0] < (left + self.radius):
      self.vx = abs(self.vx)

    if self.unif[1] > (top - self.radius):
      self.vy = -abs(self.vy)
    elif self.unif[1] < (bottom + self.radius):
      self.vy = abs(self.vy)

  def repaint(self, t):
    self.move()
    self.bounce_wall(Display.INSTANCE.width, Display.INSTANCE.height)
    self.draw()

########NEW FILE########
__FILENAME__ = Missile
from math import atan

from pi3d.constants import *
from pi3d.shape.Plane import Plane

# TODO: This code isn't used anywhere else.

class Missile(object):
  def __init__(self, w=1.0, h=1.0):
    self.isActive = False
    self.x = 0.0
    self.y = 0.0
    self.z = 0.0
    self.dx = 0.0
    self.dy = 0.0
    self.dz = 0.0
    self.w = w
    self.h = h
    self.countDown = 0
    self.picture = Plane(w, h)

  #initialise the launch of the missile
  def fire(self, x, y, z, dx, dy, dz, cnt=10):
    self.isActive = True
    self.x = x
    self.y = y
    self.z = z
    self.dx = dx
    self.dy = dy
    self.dz = dz
    self.countDown = cnt
    self.picture.position(x, y, z)
    self.picture.rotateToY(atan(dx/dz))

  #move and draw
  def move(self, tex):
    if self.countDown > 0:
      self.picture.translate(self.dx, self.dy, self.dz)
      self.picture.rotateIncY(32)
      self.picture.draw(tex)
      self.countDown -= 1

########NEW FILE########
__FILENAME__ = ScissorBall
import ctypes
from numpy import dot

from pi3d.constants import *

from pi3d.sprite.Ball import Ball
from pi3d.Display import Display

class ScissorBall(Ball):
  """ This class is basically the same as pi3d.sprite.Ball but uses glScissor
  to only render the small area of Display around itself
  """
  def __init__(self, camera=None, light=None, shader=None, texture=None,
               radius=0.0, x=0.0, y=0.0, z=1000, vx=0.0, vy=0.0, decay=0.001):
    super(ScissorBall, self).__init__(camera=camera, light=light, shader=shader,
        texture=texture, radius=radius, x=x, y=y, z=z, vx=vx, vy=vy, decay=decay)
    self.w = 2.0 * radius
    self.h = 2.0 * radius
    self.or_x = Display.INSTANCE.width / 2.0 # coord origin
    self.or_y = Display.INSTANCE.height / 2.0
    opengles.glEnable(GL_SCISSOR_TEST)

  def repaint(self, t):
    self.move()
    self.bounce_wall(Display.INSTANCE.width, Display.INSTANCE.height)
    if t == 0: #TODO this is not good but there needs to be a way to say last ball!
      opengles.glScissor(0, 0, ctypes.c_int(int(Display.INSTANCE.width)), 
                        ctypes.c_int(int(Display.INSTANCE.height)))
      #NB the screen coordinates for glScissor have origin in BOTTOM left
    else:
      opengles.glScissor(ctypes.c_int(int(self.or_x + self.unif[0] - self.radius - 5)),
                        ctypes.c_int(int(self.or_y + self.unif[1] - self.radius - 5)),
                        ctypes.c_int(int(self.w + 10)), ctypes.c_int(int(self.h + 10)))
    self.draw()

########NEW FILE########
__FILENAME__ = Texture
#from __future__ import absolute_import, division, print_function, unicode_literals
from __future__ import print_function

import ctypes
import sys

from six.moves import xrange

from PIL import Image

from pi3d.constants import *
from pi3d.util.Ctypes import c_ints
from pi3d.util.Loadable import Loadable

MAX_SIZE = 1920
DEFER_TEXTURE_LOADING = True
WIDTHS = [4, 8, 16, 32, 48, 64, 72, 96, 128, 144, 192, 256,
           288, 384, 512, 576, 640, 720, 768, 800, 960, 1024, 1080, 1920]

def round_up_to_power_of_2(x):
  p = 1
  while p <= x:
    p += p
  return p

class Texture(Loadable):
  """loads an image file from disk and converts it into an array that
  can be used by shaders. It inherits from Loadable in order that the
  file access work can happen in another thread. and the conversion
  to opengl format can happen just in time when tex() is first called.

  NB images loaded as textures can cause distortion effects unless they
  are certain sizes (below). **If the image width is a value not in this
  list then it will be rescaled with a resulting loss of clarity**

  Allowed widths 4, 8, 16, 32, 48, 64, 72, 96, 128, 144, 192, 256, 288,
  384, 512, 576, 640, 720, 768, 800, 960, 1024, 1080, 1920
  """
  def __init__(self, file_string, blend=False, flip=False, size=0,
               defer=DEFER_TEXTURE_LOADING, mipmap=True):
    """
    Arguments:
      *file_string*
        path and name of image file relative to top dir
      *blend*
        controls if low alpha pixels are discarded (if False) or drawn
        by the shader. If set to true then this texture needs to be
        drawn AFTER other objects that are FURTHER AWAY
      *flip*
        flips the image
      *size*
        to resize image to
      *defer*
        can load from file in other thread and defer opengl work until
        texture needed, default True
      *mipmap*
        use linear interpolation for mipmaps, if set False then nearest
        pixel values will be used. This is needed for exact pixel represent-
        ation of images. **NB BECAUSE THIS BEHAVIOUR IS SET GLOBALLY AT
        THE TIME THAT THE TEXTURE IS LOADED IT WILL BE SET BY THE LAST
        TEXTURE TO BE LOADED PRIOR TO DRAWING**
        TODO possibly reset in Buffer.draw() each time a texture is loaded?
    """
    super(Texture, self).__init__()
    if file_string[0] == '/': #absolute address
      self.file_string = file_string
    else:
      self.file_string = sys.path[0] + '/' + file_string
    self.blend = blend
    self.flip = flip
    self.size = size
    self.mipmap = mipmap
    self.byte_size = 0
    if defer:
      self.load_disk()
    else:
      self.load_opengl()

  def __del__(self):
    super(Texture, self).__del__()
    try:
      from pi3d.Display import Display
      if Display.INSTANCE:
        Display.INSTANCE.textures_dict[str(self._tex)][1] = 1
        Display.INSTANCE.tidy_needed = True
    except:
      print("couldn't set to delete") #TODO debug messages here

  def tex(self):
    """do the deferred opengl work and return texture"""
    self.load_opengl()
    return self._tex

  def _load_disk(self):
    """overrides method of Loadable
    Pngfont, Font, Defocus and ShadowCaster inherit from Texture but
    don't do all this so have to override this
    """
    s = self.file_string + ' '
    im = Image.open(self.file_string)

    self.ix, self.iy = im.size
    s += '(%s)' % im.mode
    self.alpha = (im.mode == 'RGBA' or im.mode == 'LA')

    if self.mipmap:
      resize_type = Image.BICUBIC
    else:
      resize_type = Image.NEAREST

    # work out if sizes > MAX_SIZE or coerce to golden values in WIDTHS
    if self.iy > self.ix and self.iy > MAX_SIZE: # fairly rare circumstance
      im = im.resize((int((MAX_SIZE * self.ix) / self.iy), MAX_SIZE))
      self.ix, self.iy = im.size
    n = len(WIDTHS)
    for i in xrange(n-1, 0, -1):
      if self.ix == WIDTHS[i]:
        break # no need to resize as already a golden size
      if self.ix > WIDTHS[i]:
        im = im.resize((WIDTHS[i], int((WIDTHS[i] * self.iy) / self.ix)),
                        resize_type)
        self.ix, self.iy = im.size
        break

    if VERBOSE:
      print('Loading ...{}'.format(s))

    if self.flip:
      im = im.transpose(Image.FLIP_TOP_BOTTOM)

    RGBs = 'RGBA' if self.alpha else 'RGB'
    self.image = im.convert(RGBs).tostring('raw', RGBs)
    self._tex = ctypes.c_int()
    if 'fonts/' in self.file_string:
      self.im = im

  def _load_opengl(self):
    """overrides method of Loadable"""
    opengles.glGenTextures(4, ctypes.byref(self._tex), 0)
    from pi3d.Display import Display
    if Display.INSTANCE:
      Display.INSTANCE.textures_dict[str(self._tex)] = [self._tex, 0]
    opengles.glBindTexture(GL_TEXTURE_2D, self._tex)
    RGBv = GL_RGBA if self.alpha else GL_RGB
    opengles.glTexImage2D(GL_TEXTURE_2D, 0, RGBv, self.ix, self.iy, 0, RGBv,
                          GL_UNSIGNED_BYTE,
                          ctypes.string_at(self.image, len(self.image)))
    opengles.glEnable(GL_TEXTURE_2D)
    opengles.glGenerateMipmap(GL_TEXTURE_2D)
    opengles.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    if self.mipmap:
      opengles.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                               GL_LINEAR_MIPMAP_NEAREST)
      opengles.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
                               GL_LINEAR)
    else:
      opengles.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                               GL_NEAREST)
      opengles.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
                               GL_NEAREST)
    opengles.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S,
                             GL_MIRRORED_REPEAT)
    opengles.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T,
                             GL_MIRRORED_REPEAT)


  def _unload_opengl(self):
    """clear it out"""
    opengles.glDeleteTextures(1, ctypes.byref(self._tex))


class TextureCache(object):
  def __init__(self, max_size=None): #TODO use max_size in some way
    self.clear()

  def clear(self):
    self.cache = {}

  def create(self, file_string, blend=False, flip=False, size=0, **kwds):
    key = file_string, blend, flip, size
    texture = self.cache.get(key, None)
    if not texture:
      texture = Texture(*key, **kwds)
      self.cache[key] = texture

    return texture

########NEW FILE########
__FILENAME__ = Clashtest
import ctypes

from six.moves import xrange

from PIL import Image

from pi3d.constants import *

from pi3d.Shader import Shader
from pi3d.util.OffScreenTexture import OffScreenTexture

class Clashtest(OffScreenTexture):
  def __init__(self):
    """ calls Texture.__init__ but doesn't need to set file name as
    texture generated from the framebuffer
    """
    super(Clashtest, self).__init__("clashtest")
    # load clashtest shader
    self.shader = Shader("clashtest")

    self.img = (ctypes.c_char * (self.ix * 3))()
    self.step = 3 * int(self.ix / 50)
    self.img_sz = len(self.img)-3
    self.s_flg = False
    self.y0 = int(self.iy / 2)

  def draw(self, shape):
    """ draw the shape using the clashtest Shader

    Arguments:
      *shape*
        Shape object that will be drawn
    """
    if not self.s_flg:
      opengles.glEnable(GL_SCISSOR_TEST)
      opengles.glScissor(ctypes.c_int(int(0)), ctypes.c_int(self.y0),
                    ctypes.c_int(self.ix), ctypes.c_int(1))
      self.s_flg = True
    shape.draw(shader=self.shader)

  def check(self, grain=50):
    """ checks the pixels of the texture to see if there is any change from the
    first pixel sampled; in which case returns True else returns False.

    Keyword argument:
      *grain*
        Number of locations to check over the whole image
    """
    opengles.glDisable(GL_SCISSOR_TEST)
    self.s_flg = False
    opengles.glReadPixels(0, self.y0, self.ix, 1,
                               GL_RGB, GL_UNSIGNED_BYTE,
                               ctypes.byref(self.img))
    r0 = self.img[0:3]
    for i in xrange(0, self.img_sz, self.step):
      if self.img[i:(i+3)] != r0:
        return True

    return False

########NEW FILE########
__FILENAME__ = Ctypes
from ctypes import c_byte, c_char, c_float, c_int, c_short

"""
Converts iterables of Python types into tuple of types from ctypes.

We need this because we do all our calculations in Python types but then pass
them to an external C library which wants ctypes.

"""

def c_bytes(x):
  """Return a tuple of c_byte, converted from a list of Python variables."""
  return (c_byte * len(x))(*x)

def c_chars(x):
  """Return a tuple of c_char, converted from a list of Python variables."""
  return (c_char * len(x))(*x)

def c_floats(x):
  return (c_float * len(x))(*x)
  """Return a tuple of c_float, converted from a list of Python variables."""

def c_ints(x):
  """Return a tuple of c_int, converted from a list of Python variables."""
  return (c_int * len(x))(*x)

def c_shorts(x):
  """Return a tuple of c_short, converted from a list of Python variables."""
  return (c_short * len(x))(*x)


########NEW FILE########
__FILENAME__ = DefaultInstance
from __future__ import absolute_import, division, print_function, unicode_literals

# Copied from echomesh.util.DefaultInstance.

class DefaultInstance(object):
  @classmethod
  def instance(cls):
    i = getattr(cls, '_INSTANCE', None)
    if i:
      return i
    else:
      cls._INSTANCE = cls._default_instance()
      return cls._INSTANCE

  def __init__(self):
    cls = type(self)
    if not getattr(cls, '_INSTANCE', None):
      cls._INSTANCE = self

  def _default_instance(self):
    raise Exception('Class %s needs to define the method _default_instance' %
                    type(self))

########NEW FILE########
__FILENAME__ = Defocus
import ctypes
from PIL import Image

from pi3d.constants import *
from pi3d.Shader import Shader
from pi3d.util.OffScreenTexture import OffScreenTexture

class Defocus(OffScreenTexture):
  """For creating a depth-of-field blurring effect on selected objects"""
  def __init__(self):
    """ calls Texture.__init__ but doesn't need to set file name as
    texture generated from the framebuffer
    """
    super(Defocus, self).__init__("defocus")
    # load blur shader
    self.shader = Shader("defocus")

  def start_blur(self):
    """ after calling this method all object.draw()s will rendered
    to this texture and not appear on the display. If you want blurred
    edges you will have to capture the rendering of an object and its
    background then re-draw them using the blur() method. Large objects
    will obviously take a while to draw and re-draw
    """
    super(Defocus, self)._start()

  def end_blur(self):
    """ stop capturing to texture and resume normal rendering to default
    """
    super(Defocus, self)._end()

  def blur(self, shape, dist_fr, dist_to, amount):
    """ draw the shape using the saved texture
    Arguments:
    
      *shape*
        Shape object that will be drawn
      *dist_fr*
        distance from zero plane that will be in focus, float
      *dist_to*
        distance beyond which everything will be at max blur, float
      *amount*
        degree of max blur, float. Values over 5 will cause banding
    """
    shape.unif[42] = dist_fr # shader unif[14]
    shape.unif[43] = dist_to
    shape.unif[44] = amount
    shape.unif[45] = 1.0/self.ix # shader unif[15]
    shape.unif[46] = 1.0/self.iy
    shape.draw(self.shader, [self], 0.0, 0.0)


########NEW FILE########
__FILENAME__ = DisplayOpenGL
import ctypes
import platform

from ctypes import c_int, c_float
from six.moves import xrange

from pi3d.constants import *

from pi3d.util.Ctypes import c_ints

if PLATFORM != PLATFORM_PI:
  from pyxlib import xlib
  from pyxlib.x import *

class DisplayOpenGL(object):
  def __init__(self):
    if PLATFORM != PLATFORM_PI:
      self.d = xlib.XOpenDisplay(None)
      self.screen = xlib.XDefaultScreenOfDisplay(self.d)
      self.width, self.height = xlib.XWidthOfScreen(self.screen), xlib.XHeightOfScreen(self.screen)
    else:
      b = bcm.bcm_host_init()
      assert b >= 0

      # Get the width and height of the screen
      w = c_int()
      h = c_int()
      s = bcm.graphics_get_display_size(0, ctypes.byref(w), ctypes.byref(h))
      assert s >= 0
      self.width, self.height = w.value, h.value

  def create_display(self, x=0, y=0, w=0, h=0, depth=24):
    self.display = openegl.eglGetDisplay(EGL_DEFAULT_DISPLAY)
    assert self.display != EGL_NO_DISPLAY

    r = openegl.eglInitialize(self.display, 0, 0)
    #assert r == EGL_FALSE

    attribute_list = c_ints((EGL_RED_SIZE, 8,
                             EGL_GREEN_SIZE, 8,
                             EGL_BLUE_SIZE, 8,
                             EGL_DEPTH_SIZE, depth,
                             EGL_ALPHA_SIZE, 8,
                             EGL_BUFFER_SIZE, 32,
                             EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
                             EGL_NONE))
    numconfig = c_int()
    self.config = ctypes.c_void_p()
    r = openegl.eglChooseConfig(self.display,
                                ctypes.byref(attribute_list),
                                ctypes.byref(self.config), 1,
                                ctypes.byref(numconfig))

    context_attribs = c_ints((EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE))
    self.context = openegl.eglCreateContext(self.display, self.config,
                                            EGL_NO_CONTEXT, ctypes.byref(context_attribs) )
    assert self.context != EGL_NO_CONTEXT

    self.create_surface(x, y, w, h)

    opengles.glDepthRangef(c_float(-1.0), c_float(1.0))
    opengles.glClearColor (c_float(0.3), c_float(0.3), c_float(0.7), c_float(1.0))
    opengles.glBindFramebuffer(GL_FRAMEBUFFER, 0)

    #Setup default hints
    opengles.glEnable(GL_CULL_FACE)
    opengles.glEnable(GL_DEPTH_TEST)
    opengles.glCullFace(GL_FRONT)
    opengles.glHint(GL_GENERATE_MIPMAP_HINT, GL_NICEST)

    # Switches off alpha blending problem with desktop - is there a bug in the
    # driver?
    # Thanks to Roland Humphries who sorted this one!!
    opengles.glColorMask(1, 1, 1, 0)

    #opengles.glEnableClientState(GL_VERTEX_ARRAY)
    #opengles.glEnableClientState(GL_NORMAL_ARRAY)
    self.active = True

  def create_surface(self, x=0, y=0, w=0, h=0):
    #Set the viewport position and size
    dst_rect = c_ints((x, y, w, h))
    src_rect = c_ints((x, y, w << 16, h << 16))

    if PLATFORM != PLATFORM_PI:
      self.width, self.height = w, h

      # Set some WM info
      root = xlib.XRootWindowOfScreen(self.screen)
      self.window = xlib.XCreateSimpleWindow(self.d, root, x, y, w, h, 1, 0, 0)

      s = ctypes.create_string_buffer(b'WM_DELETE_WINDOW')
      self.WM_DELETE_WINDOW = ctypes.c_ulong(xlib.XInternAtom(self.d, s, 0))
      #TODO add functions to xlib for these window manager libx11 functions
      #self.window.set_wm_name('pi3d xlib window')
      #self.window.set_wm_icon_name('pi3d')
      #self.window.set_wm_class('draw', 'XlibExample')

      xlib.XSetWMProtocols(self.d, self.window, ctypes.byref(self.WM_DELETE_WINDOW), 1)
      #self.window.set_wm_hints(flags = Xutil.StateHint,
      #                         initial_state = Xutil.NormalState)

      #self.window.set_wm_normal_hints(flags = (Xutil.PPosition | Xutil.PSize
      #                                         | Xutil.PMinSize),
      #                                min_width = 20,
      #                                min_height = 20)

      xlib.XSelectInput(self.d, self.window, KeyPressMask)
      xlib.XMapWindow(self.d, self.window)
      self.surface = openegl.eglCreateWindowSurface(self.display, self.config, self.window, 0)

    else:
      self.dispman_display = bcm.vc_dispmanx_display_open(0) #LCD setting
      self.dispman_update = bcm.vc_dispmanx_update_start(0)
      self.dispman_element = bcm.vc_dispmanx_element_add(
        self.dispman_update,
        self.dispman_display,
        0, ctypes.byref(dst_rect),
        0, ctypes.byref(src_rect),
        DISPMANX_PROTECTION_NONE,
        0, 0, 0)

      nativewindow = c_ints((self.dispman_element, w, h + 1))
      bcm.vc_dispmanx_update_submit_sync(self.dispman_update)

      nw_p = ctypes.pointer(nativewindow)
      self.nw_p = nw_p

      self.surface = openegl.eglCreateWindowSurface(self.display, self.config, self.nw_p, 0)
    assert self.surface != EGL_NO_SURFACE

    r = openegl.eglMakeCurrent(self.display, self.surface, self.surface,
                               self.context)
    assert r

    #Create viewport
    opengles.glViewport(0, 0, w, h)

  def resize(self, x=0, y=0, w=0, h=0):
    # Destroy current surface and native window
    openegl.eglSwapBuffers(self.display, self.surface)
    if PLATFORM == PLATFORM_PI:
      openegl.eglDestroySurface(self.display, self.surface)

      self.dispman_update = bcm.vc_dispmanx_update_start(0)
      bcm.vc_dispmanx_element_remove(self.dispman_update,
                                     self.dispman_element)
      bcm.vc_dispmanx_update_submit_sync(self.dispman_update)
      bcm.vc_dispmanx_display_close(self.dispman_display)

      #Now recreate the native window and surface
      self.create_surface(x, y, w, h)


  def destroy(self, display=None):
    if self.active:
      ###### brute force tidying experiment TODO find nicer way ########
      if display:
        func_list = [[opengles.glIsBuffer, opengles.glDeleteBuffers,
            dict(display.vbufs_dict.items() + display.ebufs_dict.items())],
            [opengles.glIsTexture, opengles.glDeleteTextures,
            display.textures_dict],
            [opengles.glIsProgram, opengles.glDeleteProgram, 0],
            [opengles.glIsShader, opengles.glDeleteShader, 0]]
        i_ct = (ctypes.c_int * 1)(0) #convoluted 0
        for func in func_list:
          max_streak = 100
          streak_start = 0
          if func[2]: # list to work through
            for i in func[2]:
              if func[0](func[2][i][0]) == 1: #check if i exists as a name
                func[1](1, ctypes.byref(func[2][i][0]))
          else: # just do sequential numbers
            for i in xrange(10000):
              if func[0](i) == 1: #check if i exists as a name
                i_ct[0] = i #convoluted 1
                func[1](ctypes.byref(i_ct))
                streak_start = i
              elif i > (streak_start + 100):
                break
      ##################################################################
      openegl.eglSwapBuffers(self.display, self.surface)
      openegl.eglMakeCurrent(self.display, EGL_NO_SURFACE, EGL_NO_SURFACE,
                             EGL_NO_CONTEXT)
      openegl.eglDestroySurface(self.display, self.surface)
      openegl.eglDestroyContext(self.display, self.context)
      openegl.eglTerminate(self.display)
      if PLATFORM == PLATFORM_PI:
        self.dispman_update = bcm.vc_dispmanx_update_start(0)
        bcm.vc_dispmanx_element_remove(self.dispman_update, self.dispman_element)
        bcm.vc_dispmanx_update_submit_sync(self.dispman_update)
        bcm.vc_dispmanx_display_close(self.dispman_display)

      self.active = False
      if PLATFORM != PLATFORM_PI:
        xlib.XCloseDisplay(self.d)

  def swap_buffers(self):
    #opengles.glFlush()
    #opengles.glFinish()
    #clear_matrices
    openegl.eglSwapBuffers(self.display, self.surface)


########NEW FILE########
__FILENAME__ = Font
from __future__ import absolute_import, division, print_function, unicode_literals

import ctypes
import itertools
import os.path
import sys
if sys.version_info[0] == 3:
  unichr = chr

try:
  from PIL import Image, ImageDraw, ImageFont
except:
  print('Unable to import libraries from PIL')

from pi3d.constants import *
from pi3d.Texture import Texture

MAX_SIZE = 1920

class Font(Texture):
  """
  A Font contains a TrueType font ready to be rendered in OpenGL.

  A font is just a mapping from codepoints (single Unicode characters) to glyphs
  (graphical representations of those characters).

  Font packs one whole font into a single Texture using PIL.ImageFont,
  then creates a table mapping codepoints to subrectangles of that Texture."""

  def __init__(self, font, color=(255,255,255,255), codepoints=None,
               add_codepoints=None, font_size=48, image_size=512,
               italic_adjustment=1.1, background_color=None):
    """Arguments:
    *font*:
      File path/name to a TrueType font file.

    *color*:
      Color in standard hex format #RRGGBB

    *font_size*:
      Point size for drawing the letters on the internal Texture

    *codepoints*:
      Iterable list of characters. All these formats will work:

        'ABCDEabcde '
        [65, 66, 67, 68, 69, 97, 98, 99, 100, 101, 145, 148, 172, 32]
        [c for c in range(65, 173)]

      Note that Font will ONLY use the codepoints in this list - if you
      forget to list a codepoint or character here, it won't be displayed.
      If you just want to add a few missing codepoints, you're probably better
      off using the *add_codepoints* parameter.

      If the string version is used then the program file might need to
      have the coding defined at the top:  # -*- coding: utf-8 -*-

      The default is *codepoints*=range(256).

    *add_codepoints*:
      If you are only wanting to add a few codepoints that are missing, you
      should use the *add_codepoints* parameter, which just adds codepoints or
      characters to the default list of codepoints (range(256). All the other
      comments for the *codepoints* parameter still apply.

    *image_size*:
      Width and height of the Texture that backs the image.
      If it doesn't fit then a larger size will be tried up to MAX_SIZE.
      The isses are: maximum image size supported by the gpu (2048x2048?)
      gpu memory usage and time to load by working up the size required
      in 256 pixel steps.

    *italic_adjustment*:
      Adjusts the bounding width to take italics into account.  The default
      value is 1.1; you can get a tighter bounding if you set this down
      closer to 1, but italics might get cut off at the right.
    """
    super(Font, self).__init__(font)
    self.font = font
    try:
      imgfont = ImageFont.truetype(font, font_size)
    except IOError:
      abspath = os.path.abspath(font)
      msg = "Couldn't find font file '%s'" % font
      if font != abspath:
        msg = "%s - absolute path is '%s'" % (msg, abspath)

      raise Exception(msg)

    pipew, pipeh = imgfont.getsize('|') # TODO this is a horrible hack
    #to cope with a bug in Pillow where ascender depends on char height!
    ascent, descent = imgfont.getmetrics()
    self.height = ascent + descent

    codepoints = (codepoints and list(codepoints)) or list(range(256))
    if add_codepoints:
      codepoints += list(add_codepoints)

    all_fits = False
    while image_size < MAX_SIZE and not all_fits:
      self.im = Image.new("RGBA", (image_size, image_size), background_color)
      self.alpha = True
      self.ix, self.iy = image_size, image_size

      self.glyph_table = {}

      draw = ImageDraw.Draw(self.im)

      curX = 0.0
      curY = 0.0
      characters = []
      
      for i in itertools.chain([0], codepoints):
        try:
          ch = unichr(i)
        except TypeError:
          ch = i
        # TODO: figure out how to skip missing characters entirely.
        # if imgfont.font.getabc(ch)[0] <= 0 and ch != zero:
        #   print('skipping', ch)
        #   continue
        chstr = '|' + ch # TODO horrible hack
        chwidth, chheight = imgfont.getsize(chstr)

        if curX + chwidth * italic_adjustment >= image_size:
          curX = 0.0
          curY += self.height + 1.0 #leave 1 pixel gap
          if curY >= image_size: #run out of space try again with bigger img
            all_fits = False
            image_size += 256
            break

        draw.text((curX, curY), chstr, font=imgfont, fill=color)
        x = (curX + pipew + 0.0) / self.ix
        y = (curY + self.height + 0.0) / self.iy
        tw = (chwidth - pipew + 0.0) / self.ix
        th = (self.height + 0.0) / self.iy
        w = image_size
        h = image_size

        table_entry = [
          chwidth - pipew,
          chheight,
          [[x + tw, y - th], [x, y - th], [x, y], [x + tw, y]],
          [[chwidth, 0, 0], [pipew, 0, 0], [pipew, -self.height, 0], [chwidth, -self.height, 0]]
          ]

        self.glyph_table[ch] = table_entry

        # Correct the character width for italics.
        curX += chwidth * italic_adjustment
        all_fits = True

    RGBs = 'RGBA' if self.alpha else 'RGB'
    self.image = self.im.convert(RGBs).tostring('raw', RGBs)
    self._tex = ctypes.c_int()

  def _load_disk(self):
    """
    we need to stop the normal file loading by overriding this method
    """

########NEW FILE########
__FILENAME__ = Gui
from __future__ import absolute_import, division, print_function, unicode_literals

import six, sys, os, time

import pi3d

DT = 0.25 #minimum time between mouse clicks or key strokes

class Gui(object):
  def __init__(self, font):
    """hold information on all widgets and the pointer, creates a 2D Camera
    and uv_flat shader. Needs to have a Font object passed to it keeps track
    of when the last mouse click or key stroke to avoid double counting.
    Arguments

      *font*
        pi3d.Font object

    A Gui instance has to be passed to each gui widget (Button, Menu etc)
    as it is created to allow resources to the used and for checking.
    """
    self.shader = pi3d.Shader("uv_flat")
    dummycam = pi3d.Camera.instance() # in case this is prior to one being created 
    self.camera = pi3d.Camera(is_3d=False)
    self.widgets = []
    self.font = font
    self.font.blend = True
    self.focus = None
    for p in sys.path:
      icon_path = p + '/pi3d/util/icons/'
      if os.path.exists(icon_path):
        self.icon_path = icon_path
        break
    tex = pi3d.Texture(self.icon_path + "pointer.png", blend=True, mipmap=False)
    self.pointer = pi3d.Sprite(camera=self.camera, w=tex.ix, h=tex.iy, z=0.5)
    self.pointer.set_draw_details(self.shader, [tex])
    self.p_dx, self.p_dy = tex.ix/2.0, -tex.iy/2.0
    self.next_tm = time.time() + DT

  def draw(self, x, y):
    """draw all visible widges and pointer at x, y
    """
    for w in self.widgets:
      if w.visible:
        w.draw()
    self.pointer.position(x + self.p_dx, y + self.p_dy, 0.5)
    self.pointer.draw()

  def check(self, x, y):
    tm = time.time()
    if tm < self.next_tm:
      return
    self.next_tm = tm + DT
    for w in self.widgets:
      if w.visible and w.check(x, y):
        self.focus = w
        break

  def checkkey(self, k):
    tm = time.time()
    if tm < self.next_tm:
      return
    self.next_tm = tm + DT
    if type(self.focus) is TextBox:
      self.focus._click(k)
    else:
      for w in self.widgets:
        if w.visible and w.checkkey(k):
          self.focus = w
          break

class Widget(object):
  def __init__(self, gui, shapes, x, y, callback=None, label=None,
               label_pos='left', shortcut=None):
    """contains functionality of buttons and is inherited by other gui
    components. Arguments:

      *gui*
        Gui object parent to this widget
      *shapes*
        drawable object such as Sprite or String, or list of two to toggle
      *x,y*
        location of top left corner of this widget
      *label*
        string to use as label
      *label_pos*
        position of label 'left', 'right', 'above', 'below'
      *shortcut*
        shortcut key to have same effect as clicking wit mouse???
    """
    if not (type(shapes) is list or type(shapes) is tuple):
      self.shapes = [shapes]
    else:
      self.shapes = shapes
    self.toggle = len(self.shapes) > 1 #this widget can toggle between two
    self.clicked = False
    self.callback = callback
    self.shortcut = shortcut
    self.label_pos = label_pos
    if label:
      self.labelobj = pi3d.String(font=gui.font, string=label, is_3d=False,
                              camera=gui.camera, justify='L')
      self.labelobj.set_shader(gui.shader)
    else:
      self.labelobj = None
    self.relocate(x, y)
    if not (self in gui.widgets): #because TextBox re-runs Widget.__init__
      gui.widgets.append(self)
    self.visible = True

  def relocate(self, x, y):
    b = self.shapes[0].get_bounds()
    self.bounds = [x, y - b[4] + b[1], x + b[3] - b[0], y]
    for s in self.shapes:
      s.position(x - b[0], y - b[4], 1.0)
    if self.labelobj:
      b = self.labelobj.get_bounds()
      if self.label_pos == 'above':
        self.labelobj.position((x + self.bounds[2] - b[3] - b[0]) / 2.0,
                              y - b[1], 1.0)
      elif self.label_pos == 'below':
        self.labelobj.position((x + self.bounds[2] - b[3] - b[0]) / 2.0,
                              self.bounds[1] - b[4], 1.0)
      elif self.label_pos == 'right':
        self.labelobj.position(self.bounds[2] + b[0] - 5.0,
                  (y + self.bounds[1] - b[1] - b[4]) / 2.0, 1.0)
      else:
        self.labelobj.position(x - b[3] - 5.0,
                  (y + self.bounds[1] - b[1] - b[4]) / 2.0, 1.0)      

  def draw(self):
    if self.toggle and self.clicked:
      self.shapes[1].draw()
    else:
      self.shapes[0].draw()
    for s in self.shapes[2:]:
      s.draw()
    if self.labelobj:
      self.labelobj.draw()

  def check(self, x, y):
    if x > self.bounds[0] and x < self.bounds[2] and y > self.bounds[1] and y < self.bounds[3]:
      self._click(x, y)
      return True
    return False

  def checkkey(self, k):
    if k == self.shortcut:
      self._click(k)
      return True
    return False

  def _click(self, *args):
    if self.toggle:
      self.clicked = not self.clicked
    if self.callback:
      self.callback(args)

class Button(Widget):
  def __init__(self, gui, imgs, x, y, callback=None, label=None,
               label_pos='left', shortcut=None):
    """This inherits pretty much everything it needs from Widget, it just
    takes a list of images rather than Shapes. Otherwise same Arguments.

      *imgs*
        list of strings. If these exist as files using the path and file
        name then those will be used. Otherwise the pi3d/util/icons path
        will be prepended
    """
    if not (type(imgs) is list or type(imgs) is tuple):
      imgs = [imgs]
    shapes = []
    for i in imgs:
      if not os.path.isfile(i):
        i = gui.icon_path + i
      tex = pi3d.Texture(i, blend=True, mipmap=False)
      shape = pi3d.Sprite(camera=gui.camera, w=tex.ix, h=tex.iy, z=2.0)
      shape.set_draw_details(gui.shader, [tex])
      shapes.append(shape)
    super(Button, self).__init__(gui, shapes, x, y, callback=callback,
                  label=label, label_pos=label_pos, shortcut=shortcut)

class Radio(Button):
  def __init__(self, gui, x, y, callback=None, label=None,
               label_pos='left', shortcut=None):
    """This is a toggle button with two checkbox images. Same Arguments
    as Widget but missing the list of Shapes completely.
    """
    super(Radio, self).__init__(gui, ['cba0.gif', 'cba1.gif'], x, y,
        callback=callback, label=label, label_pos=label_pos, shortcut=shortcut)

class Scrollbar(Widget):
  def __init__(self, gui, x, y, width, start_val=None, callback=None, label=None,
               label_pos='left', shortcut=None):
    """This consists of four Shapes but the first one is duplicated so
    the Widget.draw() method can be used unchanged. The images are hard
    coded so no list of Shapes or images needs to be supplied however
    arguments additional to those for Widget are

      *width*
        width of the scroll (excluding buttons on either end)
      *start_val*
        proportion of the way across i.e. if width = 200 then start_val
        of 150 would be three quarters

    NB the callback is called with *args equal to the position of the slider
    so the function needs to be defined with this in mind i.e.
    ``def cb(*args):`` args will then be available as a tuple (0.343,)
    """
    imgs = ["scroll.gif", "scroll.gif", "scroll_lh.gif", "scroll_rh.gif",
            "scroll_thumb.gif"]
    shapes = []
    end_w = 0
    for i, im in enumerate(imgs):
      tex = pi3d.Texture(gui.icon_path + im, blend=True, mipmap=False)
      w = tex.ix if i > 0 else width
      if i == 2:
        end_w = tex.ix #offsets for end buttons
      if i == 4:
        thumb_w = tex.ix / 2.0 #offset for thumb
      shape = pi3d.Sprite(camera=gui.camera, w=w, h=tex.iy, z=2.0)
      shape.set_draw_details(gui.shader, [tex])
      shapes.append(shape)
    super(Scrollbar, self).__init__(gui, shapes, x, y, callback=callback,
            label=label, label_pos=label_pos, shortcut=shortcut)
    self.toggle = False
    self.t_stop = [self.bounds[0] + thumb_w, self.bounds[2] - thumb_w]
    if not start_val:
      start_val = width / 2.0
    self.thumbpos = start_val / width * (self.t_stop[1] - self.t_stop[0])
    self.shapes[4].positionX(self.t_stop[0] + self.thumbpos)
    self.shapes[4].translateZ(-0.1)
    self.shapes[2].translateX((-width - end_w) / 2.0)
    self.shapes[3].translateX((width + end_w) / 2.0)
    self.bounds[0] -= end_w
    self.bounds[2] += end_w
    if self.labelobj:
      if label_pos == 'left':
        self.labelobj.translateX(-end_w)
      elif label_pos == 'right':
        self.labelobj.translateX(end_w)
        
  def _click(self, *args):
    thumb_x = self.t_stop[0] + self.thumbpos
    if len(args) == 2:
      x, y = args
      if x < thumb_x and thumb_x > self.t_stop[0]:
        self.thumbpos -= (thumb_x - x) / 2.0
      if x > thumb_x and thumb_x < self.t_stop[1]:
        self.thumbpos += (x - thumb_x) / 2.0
      if self.thumbpos < 0:
        self.thumbpos = 0
      if self.thumbpos > (self.t_stop[1] - self.t_stop[0]):
        self.thumbpos = (self.t_stop[1] - self.t_stop[0])
      self.shapes[4].positionX(self.t_stop[0] + self.thumbpos)
      
    if self.callback:
      self.callback((thumb_x - self.t_stop[0])/(self.t_stop[1] - self.t_stop[0]))

class MenuItem(Widget):
  def __init__(self, gui, text, callback=None, shortcut=None):
    """These are the clickable Widgets of the menu system. Instead of a
    list of Shapes they have a string argument, there is no label or
    label_pos and the x and y values are obtained from the position and
    orientation of the parent Menu.

      *text*
        string used to construct a pi3d.String
        
    """
    menu_text = pi3d.String(font=gui.font, string=text, is_3d=False,
                              camera=gui.camera, justify='L')
    menu_text.set_shader(gui.shader)
    super(MenuItem, self).__init__(gui, [menu_text], 0, 0,
        callback=callback, shortcut=shortcut)
    self.child_menu = None
    self.own_menu = None

  def _click(self, *args):
    for item in self.own_menu.menuitems:
      if item != self and item.child_menu:
        item.child_menu.hide()
    if self.child_menu:
      if self.child_menu.visible:
        self.child_menu.hide()
      else:
        self.child_menu.show()
    super(MenuItem, self)._click(args)

class Menu(object):
  def __init__(self, parent_item=None, menuitems=[], x=0, y=0, horiz=True,
                position='right', visible=True):
    """Container for MenuItems, forming either a horizontal or vertical
    bar. Arguments

      *parent_item*
        a MenuItem that will make this Menu visible when clicked
      *menuitems*
        a list of MenuItems to be displayed in this Menu
      *x*
        x location will be overwritten unless parent_item == None
      *y*
        similarly the y location
      *horiz*
        set True (default) for horizontal layout on the menu bar, False
        for vertical listing
      *position*
        relative to the MenuItem that gives rise to this Menu when clicked
        'right' or any other text interpreted as below
      *visible*
        when an alternative branch of the menu tree is selected or the
        parent_item is re-clicked this menu is hidden, along with all
        its children recursively. They are set to visible = False and
        not drawn and not checked for mouse clicks.
        
    """
    self.visible = visible
    self.parent_item = parent_item
    if parent_item:
      parent_item.child_menu = self
      if position == 'right':
        self.x = parent_item.bounds[2] + 5
        self.y = parent_item.bounds[3]
      else:
        self.x = parent_item.bounds[0]
        self.y = parent_item.bounds[1]
    else:
      self.x = x
      self.y = y
    i_x = self.x
    i_y = self.y
    for item in menuitems:
      item.own_menu = self
      item.relocate(i_x, i_y)
      item.visible = visible
      if horiz:
        i_x = item.bounds[2] + 5
      else:
        i_y = item.bounds[1]
    self.menuitems = menuitems
    if parent_item != None:
      self.hide()

  def hide(self):
    self.visible = False
    for i in self.menuitems:
      i.visible = False
      if i.child_menu:
        i.child_menu.hide()

  def show(self):
    self.visible = True
    for i in self.menuitems:
      i.visible = True

class TextBox(Widget):
  def __init__(self, gui, txt, x, y, callback=None, label=None,
               label_pos='left', shortcut=None):
    self.gui = gui
    self.txt = txt
    self.x = x
    self.y = y
    self.callback = callback
    self.label = label
    self.label_pos = label_pos
    self.shortcut = shortcut
    self.cursor = len(txt)
    tex = pi3d.Texture(gui.icon_path + 'tool_stop.gif', blend=True, mipmap=False)
    self.cursor_shape = pi3d.Sprite(camera=gui.camera, w=tex.ix/10.0,
                          h=tex.iy, z=1.1)
    self.cursor_shape.set_draw_details(gui.shader, [tex])
    self.recreate()

  def recreate(self):
    self.c_lookup = [] #mapping between clicked char and char in string
    for i, l in enumerate(self.txt):
      if l != '\n':
        self.c_lookup.append(i)
    textbox = pi3d.String(font=self.gui.font, string=self.txt, is_3d=False,
                              camera=self.gui.camera, justify='L', z=1.0)
    textbox.set_shader(self.gui.shader)
    super(TextBox, self).__init__(self.gui, [textbox], self.x, self.y,
                        callback=self.callback, label=self.label,
                        label_pos=self.label_pos, shortcut=self.shortcut)

  def _get_charindex(self, x, y):
    """Find the x,y location of each letter's bottom left and top right
    vertices to return a character index of the click x,y
    """
    verts = self.shapes[0].buf[0].vertices
    x = x - self.x + verts[2][0]
    y = y - self.y + verts[0][1]
    nv = len(verts)
    for i in range(0, nv, 4):
      vtr = verts[i] # top right
      vbl = verts[i + 2] # bottom left
      if x >= vbl[0] and x < vtr[0] and y >= vbl[1] and y < vtr[1]:
        i = int(i / 4)
        c_i = self.c_lookup[i]
        if c_i == (len(self.txt) - 1) or self.c_lookup[i + 1] > c_i + 1:
          if (vtr[0] - x) < (x - vbl[0]):
            c_i += 1
        return c_i
    return len(self.txt)

  def _get_cursor_loc(self, i):
    verts = self.shapes[0].buf[0].vertices
    maxi = int(len(verts) / 4 - 1)
    if maxi < 0:
      return self.x, self.y
    if i > maxi:
      x = self.x - verts[2][0] + verts[maxi * 4][0]
      y = self.y - verts[0][1] + (verts[maxi * 4][1] + verts[maxi * 4 + 2][1]) / 2.0
    else:
      x = self.x - verts[2][0] + verts[i * 4 + 2][0]
      y = self.y - verts[0][1] + (verts[i * 4][1] + verts[i * 4 + 2][1]) / 2.0
    return x, y

  def checkkey(self, k):
    """have to use a slightly different version without the _click() call
    """
    if k == self.shortcut:
      return True
    return False

  def _click(self, *args):
    if len(args) == 2: #mouse click
      x, y = args
      self.cursor = self._get_charindex(x, y)
    else: #keyboard input
      k = args[0]
      if k == '\t': #backspace use tab char
        self.txt = self.txt[:(self.cursor - 1)] + self.txt[self.cursor:]
        self.cursor -= 1
      elif k == '\r': #delete use car ret char
        self.txt = self.txt[:self.cursor] + self.txt[(self.cursor + 1):]
      else:
        self.txt = self.txt[:self.cursor] + k + self.txt[(self.cursor):]
        self.cursor += 1
      self.recreate()
    super(TextBox, self)._click()

  def draw(self):
    if self.gui.focus == self:
      x, y = self._get_cursor_loc(self.cursor)
      self.cursor_shape.position(x, y, 1.1)
      self.cursor_shape.draw()
    super(TextBox, self).draw()

########NEW FILE########
__FILENAME__ = Loadable
from __future__ import absolute_import, division, print_function, unicode_literals

import threading

from pi3d import Display
from pi3d.util import Log

LOGGER = Log.logger(__name__)

CHECK_IF_DISPLAY_THREAD = True
DISPLAY_THREAD = threading.current_thread()

def is_display_thread():
  return not CHECK_IF_DISPLAY_THREAD or (
    DISPLAY_THREAD is threading.current_thread())

class Loadable(object):
  def __init__(self):
    LOGGER.debug('__init__: %s', self)
    self.disk_loaded = False
    self.opengl_loaded = False

  def __del__(self):
    LOGGER.debug('__del__: %s', self)
    try:
      if not self.unload_opengl(False):  # Why does this sometimes fail?
        Display.display.unload_opengl(self)
    except:
      # Many legit reasons why this might fail, particularly during shutdown.
      pass

  def load_disk(self):
    if not self.disk_loaded:
      self._load_disk()
      self.disk_loaded = True

  def load_opengl(self):
    self.load_disk()
    if not self.opengl_loaded:
      if is_display_thread():
        self._load_opengl()
        self.opengl_loaded = True
      else:
        LOGGER.error('load_opengl must be called on main thread for %s', self)

  def unload_opengl(self, report_error=True):
    if not self.opengl_loaded:
      return True

    try:
      if is_display_thread():
        self._unload_opengl()
        self.opengl_loaded = False
        return True
      elif report_error:
        LOGGER.error('unload_opengl must be called on main thread for %s', self)
        return False
    except:
      pass  # Throws exception if called during shutdown.

  def _load_disk(self):
    """Override this to load assets from disk."""
    pass

  def _load_opengl(self):
    """Override this to load assets into Open GL."""
    pass

  def _unload_opengl(self):
    """Override this to unload assets from Open GL."""
    pass

########NEW FILE########
__FILENAME__ = Log
from __future__ import absolute_import, division, print_function, unicode_literals

import errno
import logging
import os
import os.path

# To get debug messages, set LOG_LEVEL to be 'DEBUG'.
#
# Possible levels are:
#   DEBUG
#   INFO
#   WARNING
#   ERROR
#   CRITICAL

LOG_LEVEL = 'INFO'
LOG_FILE = ''
LOG_FORMAT = '%(asctime)s %(levelname)s: %(name)s: %(message)s'

def parent_makedirs(file):
  path = os.path.dirname(os.path.expanduser(file))
  try:
    os.makedirs(path)
  except OSError as exc:
    if exc.errno == errno.EEXIST:
      pass
    else:
      raise

def set_logs(level=None, file=None, format=None):
  """

  You can redirect, filter or reformat your logging by calling Log.set_logs().
  Log.set_logs() has three optional parameters:

    level:
      can be one of 'DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'.
      Everything that's the current log level or greater is displayed -
      for example, if your current log level is 'WARNING', then you'll display
      all warning, error, or critical messages.

    file:
       is the name of a file to which to redirect messages.

    format:
       controls what information is in the output messages.  The default is
         `'%(asctime)s %(levelname)s: %(name)s: %(message)s'`
       which results in output looking like this:
        `time LEVEL: filename: Your Message Here.`"""

  global HANDLER, LOG_LEVEL, LOG_FILE, LOG_FORMAT
  LOG_LEVEL = (level or LOG_LEVEL).upper()
  LOG_FILE = file or LOG_FILE
  LOG_FORMAT = format or LOG_FORMAT

  logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT)

  if LOG_FILE:
    parent_makedirs(LOG_FILE)
    HANDLER = logging.FileHandler(LOG_FILE)
  else:
    HANDLER = None

set_logs()

def logger(name=None):
  """
  The typical usage of the Log module has a single LOGGER per Python file.

  At the top of the file is typically:

    LOGGER = Log.logger(__name__)

  and then later on you can do things like:

    * LOGGER.debug('stuff here')
    * LOGGER.info('Some information about %s', some_name)
    * LOGGER.error('Not everything was displayed, sorry!')
    * LOGGER.error('You died with error code %d, message %s', error_code, msg)
    * LOGGER.critical('Your machine is about to explode.  Leave the building.')

  (Note that the values for the format string, like "some_name", "error_code" or
  "msg" are passed in as arguments - that's so you never even construct the
  message if it isn't going to be displayed.)
  """

  log = logging.getLogger(name or 'logging')
  if HANDLER and HANDLER not in log.handlers:
    log.addHandler(HANDLER)

  return log

LOGGER = logger(__name__)
LOGGER.debug('Log level is %s', LOG_LEVEL)

########NEW FILE########
__FILENAME__ = OffScreenTexture
import ctypes, time
from PIL import Image

from pi3d.constants import *
from pi3d.Texture import Texture

class OffScreenTexture(Texture):
  """For creating special effect after rendering to texture rather than
  onto the display. Used by Defocus, ShadowCaster, Clashtest etc
  """
  def __init__(self, name):
    """ calls Texture.__init__ but doesn't need to set file name as
    texture generated from the framebuffer
    """
    super(OffScreenTexture, self).__init__(name)
    from pi3d.Display import Display
    self.ix, self.iy = Display.INSTANCE.width, Display.INSTANCE.height
    self.im = Image.new("RGBA",(self.ix, self.iy))
    self.image = self.im.convert("RGBA").tostring('raw', "RGBA")
    self.alpha = True
    self.blend = False

    self._tex = ctypes.c_int()
    self.framebuffer = (ctypes.c_int * 1)()
    opengles.glGenFramebuffers(1, self.framebuffer)
    self.depthbuffer = (ctypes.c_int * 1)()
    opengles.glGenRenderbuffers(1, self.depthbuffer)

  def _load_disk(self):
    """ have to override this
    """

  def _start(self):
    """ after calling this method all object.draw()s will rendered
    to this texture and not appear on the display. Large objects
    will obviously take a while to draw and re-draw
    """
    opengles.glBindFramebuffer(GL_FRAMEBUFFER, self.framebuffer[0])
    opengles.glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                GL_TEXTURE_2D, self._tex.value, 0)
    #thanks to PeterO c.o. RPi forum for pointing out missing depth attchmnt
    opengles.glBindRenderbuffer(GL_RENDERBUFFER, self.depthbuffer[0])
    opengles.glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT16,
                self.ix, self.iy)
    opengles.glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                GL_RENDERBUFFER, self.depthbuffer[0])
    opengles.glClear(GL_DEPTH_BUFFER_BIT | GL_COLOR_BUFFER_BIT)

    #assert opengles.glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE

  def _end(self):
    """ stop capturing to texture and resume normal rendering to default
    """
    opengles.glBindTexture(GL_TEXTURE_2D, 0)
    opengles.glBindFramebuffer(GL_FRAMEBUFFER, 0)

    
  def delete_buffers(self):
    opengles.glDeleteFramebuffers(1, self.framebuffer)
    opengles.glDeleteRenderbuffers(1, self.depthbuffer)


########NEW FILE########
__FILENAME__ = Pngfont
import ctypes

from PIL import ImageDraw

from pi3d.constants import *
from pi3d.Texture import Texture

# Text and fonts
# TODO TEXTURES NEED CLEANING UP

class Pngfont(Texture):
  def __init__(self, font, color=(255,255,255,255)):
    """

    A method of writing in pi3d using 'hand designed' fonts, where the top
    line of the texture contains metainformation about each character.

    Mainly superseded by the Font class.

    Arguments:
      *font*
        The name of a file containing a PNG texture.
      *color*
        A hex string representing a color.

    """
    if not font.endswith('.png'):
      font += '.png'
    super(Pngfont, self).__init__("fonts/%s" % font)
    self.font = font
    pixels = self.im.load()

    self.glyph_table = {}
    # Extract font information from top scanline of font image;  create width,
    # height, tex_coord and vertices for each character.
    for v in range(95):
      x = (pixels[v * 2, 0][0] * 2.0) / self.ix
      y = ((pixels[v * 2, 0][1] + 8) * 2.0) / self.iy
      width = float(pixels[v * 2 + 1, 0][0])
      height = float(pixels[v * 2 + 1, 0][1])
      width_scale = width / self.ix
      height_scale = height / self.iy

      self.glyph_table[v] = [width, height,
        [(x + width_scale, y - height_scale),
         (x, y - height_scale),
         (x, y),
         (x + width_scale, y)],
        [(width, 0, 0), (0, 0, 0), (0, -height, 0), (width, -height, 0)]]

    alph = self.im.split()[-1]  #keep alpha
    draw = ImageDraw.Draw(self.im)
    draw.rectangle((0, 1, self.ix, self.iy), fill=color)
    self.im.putalpha(alph)

    RGBs = 'RGBA' if self.alpha else 'RGB'
    self.image = self.im.convert(RGBs).tostring('raw', RGBs)
    self._tex = ctypes.c_int()

########NEW FILE########
__FILENAME__ = PostProcess
import ctypes
from PIL import Image

from pi3d.constants import *
from pi3d.Shader import Shader
from pi3d.Camera import Camera
from pi3d.shape.LodSprite import LodSprite
from pi3d.util.OffScreenTexture import OffScreenTexture

class PostProcess(OffScreenTexture):
  """For creating a an offscreen texture that can be redrawn using shaders
  as required by the developer"""
  def __init__(self, shader="post_base", mipmap=False, add_tex=None,
              scale=1.0, camera=None, divide=1):
    """ calls Texture.__init__ but doesn't need to set file name as
    texture generated from the framebuffer. Keyword Arguments:

      *shader*
        to use when drawing sprite, defaults to post_base, a simple
        3x3 convolution that does basic edge detection. Can be copied to
        project directory and modified as required.

      *mipmap*
        can be set to True with slight cost to speed, or use fxaa shader

      *add_tex*
        list of textures. If additional textures can be used by the shader
        then they can be added here.
        
      *scale*
        will only render this proportion of the full screen which will
        then be mapped to the full uv of the Sprite. The camera object
        passed (below) will need to have the same scale set to avoid
        perspective distortion
        
      *camera*
        the camera to use for rendering to the offscreen texture
        
      *divide*
        allow the sprite to be created with intermediate vertices to allow
        interesting vertex shader effects
     
    """
    super(PostProcess, self).__init__("postprocess")
    self.scale = scale
    # load shader
    self.shader = Shader(shader)
    if camera == None:
      self.viewcam = Camera.instance() # in case this is prior to one being created
    else:
      self.viewcam = camera
    self.camera = Camera(is_3d=False)
    self.sprite = LodSprite(z=20.0, w=self.ix, h=self.iy, n=divide)
    self.sprite.set_2d_size(w=self.ix, h=self.iy)
    for b in self.sprite.buf:
      b.unib[6] = self.scale # ufact
      b.unib[7] = self.scale # vfact
      b.unib[9] = (1.0 - self.scale) * 0.5 # uoffset
      b.unib[10] = (1.0 - self.scale) * 0.5 # voffset
    self.alpha = False
    self.blend = True
    self.mipmap = mipmap
    self.tex_list = [self] # TODO check if this self reference causes graphics memory leaks
    if add_tex:
      self.tex_list.extend(add_tex)

  def start_capture(self):
    """ after calling this method all object.draw()s will rendered
    to this texture and not appear on the display. Large objects
    will obviously take a while to draw and re-draw
    """
    super(PostProcess, self)._start()
    from pi3d.Display import Display
    xx = Display.INSTANCE.width / 2.0 * (1.0 - self.scale)
    yy = Display.INSTANCE.height / 2.0 * (1.0 - self.scale)
    ww = Display.INSTANCE.width * self.scale
    hh = Display.INSTANCE.height * self.scale
    opengles.glEnable(GL_SCISSOR_TEST)
    opengles.glScissor(ctypes.c_int(int(xx)), ctypes.c_int(int(yy)),
                  ctypes.c_int(int(ww)), ctypes.c_int(int(hh)))

  def end_capture(self):
    """ stop capturing to texture and resume normal rendering to default
    """
    super(PostProcess, self)._end()
    opengles.glDisable(GL_SCISSOR_TEST)

  def draw(self, unif_vals=None):
    """ draw the shape using the saved texture
    Keyword Argument:
    
      *unif_vals*
        dictionay object i.e. {a:unif[a], b:unif[b], c:unif[c]} where a,b,c
        are subscripts of the unif array in Shape available for user
        custom space i.e. unif[48]...unif[59] corresponding with the vec3
        uniform variables unif[16][0] to unit[19][2]
    """
    if unif_vals:
      for i in unif_vals:
        self.sprite.unif[i] = unif_vals[i]
    self.sprite.draw(self.shader, self.tex_list, 0.0, 0.0, self.camera)


########NEW FILE########
__FILENAME__ = RotateVec
from pi3d.util.Utility import from_polar

"""Calculate position or direction 3D vector after rotation about axis"""
def rotate_vec(rx, ry, rz, xyz):
  x, y, z = xyz
  if ry:
    ca, sa = from_polar(ry)
    zz = z * ca - x * sa
    x = z * sa + x * ca
    z = zz
  if rx:
    ca, sa = from_polar(rx)
    yy = y * ca - z * sa
    z = y * sa + z * ca
    y = yy
  if rz:
    ca, sa = from_polar(rz)
    xx = x * ca - y * sa
    y = x * sa + y * ca
    x = xx
  return x, y, z
"""
# no longer used anywhere

def rotate_vec_x(r, xyz):
  ca, sa = from_polar(r)
  return xyz[0], xyz[1] * ca - xyz[2] * sa, xyz[1] * sa + xyz[2] * ca

def rotate_vec_y(r, xyz):
  ca, sa = from_polar(r)
  return xyz[2] * sa + xyz[0] * ca, xyz[1], xyz[2] * ca - xyz[0] * sa

def rotate_vec_z(r, xyz):
  ca, sa = from_polar(r)
  return xyz[0] * ca - xyz[1] * sa, xyz[0] * sa + xyz[1] * ca, xyz[2]
"""

########NEW FILE########
__FILENAME__ = Screenshot
from __future__ import absolute_import, division, print_function, unicode_literals

import ctypes
from PIL import Image

from pi3d.constants import *
from pi3d.util import Log

LOGGER = Log.logger(__name__)

def screenshot(filestring):
  """
  Save whatever's in the display to a file.

  Will save whatever has been rendered since the last call to Display.clear().

  The file will be saved in the top-level directory if you don't add a path
  to it!
  """

  from pi3d.Display import Display
  LOGGER.info('Taking screenshot of "%s"', filestring)

  w, h = Display.INSTANCE.width, Display.INSTANCE.height
  size = h * w * 3
  img = (ctypes.c_char * size)()
  opengles.glReadPixels(0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, ctypes.byref(img))

  im = Image.frombuffer('RGB', (w, h), img, 'raw', 'RGB', 0, 1)
  im = im.transpose(Image.FLIP_TOP_BOTTOM)
  im.save(filestring)


########NEW FILE########
__FILENAME__ = ShadowCaster
import ctypes
from PIL import Image

from pi3d.constants import *
from pi3d.Shader import Shader
from pi3d.util.OffScreenTexture import OffScreenTexture
from pi3d.Camera import Camera

class ShadowCaster(OffScreenTexture):
  """For creating a depth-of-field blurring effect on selected objects"""
  def __init__(self, emap, light):
    """ calls Texture.__init__ but doesn't need to set file name as
    texture generated from the framebuffer
    """
    super(ShadowCaster, self).__init__("shadow_caster")
    # load shader for casting shadows and camera
    self.cshader = Shader("uv_flat")
    self.mshader = Shader("mat_flat")
    # keep copy of ElevationMap
    self.emap = emap
    self.emap.set_material((0.0, 0.0, 0.0)) # hide bits below ground
    #TODO doesn't cope with  z light positions
    self.eye = [-500.0 * i for i in light.lightpos] # good distance away
    if self.eye[1] <= 0: # must have +ve y
      self.eye[1] = 500.0
    if abs(self.eye[0]) > abs(self.eye[2]): #x val is bigger than z val
      #change scale so map just fits on screen
      if self.eye[0] < 0:
        su, sv  = 1.0, 1.0
      else:
        su, sv  = -1.0, -1.0
      self.scaleu = float(self.iy) / self.emap.width
      self.scalev = float(self.ix)/ self.emap.depth
      self.eye[2] = 0
      self.scaleu = self.scaleu / self.eye[1] * (self.eye[0]**2 + self.eye[1]**2)**0.5
      self.emap.unif[50] = 1.0 #orientation flag
      self.emap.unif[53] = -3.0 * su / self.emap.width * self.eye[0] / self.eye[1] #height adjustment
    else:
      #change scale so map just fits on screen
      if self.eye[2] < 0:
        su, sv  = 1.0, -1.0
      else:
        su, sv  = -1.0, 1.0
      self.scaleu = float(self.iy) / self.emap.depth
      self.scalev = float(self.ix)/ self.emap.width
      self.eye[0] = 0
      self.scaleu = self.scaleu / self.eye[1] * (self.eye[2]**2 + self.eye[1]**2)**0.5
      self.emap.unif[50] = 0.0
      self.emap.unif[53] = -3.0 * su / self.emap.width * self.eye[2] / self.eye[1]
    if abs(self.scaleu) > abs(self.scalev):
      self.scale = 3.0 * self.scalev # multiplication factor to reduce pixeliness
    else:
      self.scale = 3.0 * self.scaleu
    self.scaleu = su * self.scale / self.scaleu # reused later in end_cast
    self.scalev = sv * self.scale / self.scalev
    self.camera0 = Camera() # default instance created as normal, just in case!
    self.camera = Camera(is_3d=False, eye=self.eye, scale=self.scale)
    # load shader for drawing map with shadows
    self.dshader = Shader("shadowcast")

  def start_cast(self, location=(0.0, 0.0,  0.0)):
    """ after calling this method all object.draw()s will rendered
    to this texture and not appear on the display. If you want blurred
    edges you will have to capture the rendering of an object and its
    background then re-draw them using the blur() method. Large objects
    will obviously take a while to draw and re-draw
    """
    opengles.glClearColor(ctypes.c_float(0.0), ctypes.c_float(0.0), 
                        ctypes.c_float(0.0), ctypes.c_float(1.0))
    super(ShadowCaster, self)._start()
    self.camera.reset(is_3d=False, scale=self.scale)
    self.camera.position((location[0], 0, location[2]))
    self.location = location

  def end_cast(self):
    """ stop capturing to texture and resume normal rendering to default
    """
    #draw the actual map
    self.emap.draw(shader=self.mshader, camera=self.camera)
    super(ShadowCaster, self)._end()
    # set third texture to this ShadowCaster texture
    texs = self.emap.buf[0].textures
    if len(texs) == 2:
      texs.append(self)
    else:
      texs[2] = self
    # change background back to blue
    opengles.glClearColor(ctypes.c_float(0.4), ctypes.c_float(0.8), 
                        ctypes.c_float(0.8), ctypes.c_float(1.0))
    # work out left, top, right, bottom for shader
    self.emap.unif[48] = 0.5 * (1.0 + self.scaleu) # left [16][0]
    self.emap.unif[49] = 0.5 * (1.0 + self.scalev) # top [16][1]
    self.emap.unif[51] = 1.0 - self.emap.unif[48] # right [17][0]
    self.emap.unif[52] = 1.0 - self.emap.unif[49] # bottom [17][1]
    
    du = float(self.location[0] / self.emap.width)
    dv = float(self.location[2] / self.emap.depth)
    self.emap.unif[48] -= self.scaleu * (du if self.emap.unif[50] == 1.0 else dv)
    self.emap.unif[49] += self.scalev * (dv if self.emap.unif[50] == 1.0 else du)
    self.emap.unif[51] -= self.scaleu * (du if self.emap.unif[50] == 1.0 else dv)
    self.emap.unif[52] += self.scalev * (dv if self.emap.unif[50] == 1.0 else du)

  def add_shadow(self, shape):
    shape.draw(shader=self.cshader, camera=self.camera)
    
  def draw_shadow(self):
    self.emap.draw(shader=self.dshader)

########NEW FILE########
__FILENAME__ = String
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
if sys.version_info[0] == 3:
  unichr = chr
  text_type = str
else:
  text_type = unicode

from pi3d import *

from pi3d.Buffer import Buffer
from pi3d.Shape import Shape
from pi3d.util import Utility

DOTS_PER_INCH = 72.0
DEFAULT_FONT_SIZE = 0.24
DEFAULT_FONT_SCALE = DEFAULT_FONT_SIZE / DOTS_PER_INCH
GAP = 1.0

_NORMALS = [[0.0, 0.0, 1.0], [0.0, 0.0, 1.0], [0.0, 0.0, 1.0], [0.0, 0.0, 1.0]]

class String(Shape):
  """Shape used for writing text on screen. It is a flat, one sided rectangualar plane"""
  def __init__(self, camera=None, light=None, font=None, string=None,
               x=0.0, y=0.0, z=1.0,
               sx=DEFAULT_FONT_SCALE, sy=DEFAULT_FONT_SCALE,
               is_3d=True, size=DEFAULT_FONT_SIZE,
               rx=0.0, ry=0.0, rz=0.0, justify="C"):
    """Standard Shape constructor without the facility to change z scale or
    any of the offset values. Additional keyword arguments:

      *font*
        Pngfont or Font class object.
      *string*
        of ASCI characters in range(32, 128) plus 10 = \n Line Feed
      *sx, sy*
        These change the actual vertex positions of the shape rather than being
        used as scaling factors. This is to avoid distortion when the string is
        drawn using an orthographic camera
      *is_3d*
        alters the values of sx and sy to give reasonable sizes with 2D or 3D
        drawing
      *size*
        approximate size of the characters in inches - obviously for 3D drawing
        of strings this will depend on camera fov, display size and how far away
        the string is placed
      *justify*
        default C for central, can be R for right or L for left
    """
    if not is_3d:
      sy = sx = size * 4.0
    super(String, self).__init__(camera, light, "", x, y, z,
                                 rx, ry, rz,  1.0, 1.0, 1.0,  0.0, 0.0, 0.0)

    if VERBOSE:
      print("Creating string ...")

    self.verts = []
    self.texcoords = []
    self.norms = []
    self.inds = []
    temp_verts = []

    xoff = 0.0
    yoff = 0.0
    lines = 0
    if not isinstance(string, text_type):
      string = string.decode('utf-8')
    nlines = string.count("\n") + 1

    def make_verts(): #local function to justify each line
      if justify.upper() == "C":
        cx = xoff / 2.0
      elif justify.upper() == "L":
        cx = 0.0
      else:
        cx = xoff
      for j in temp_verts:
        self.verts.append([(j[0] - cx) * sx,
                           (j[1] + nlines * font.height * GAP / 2.0 - yoff) * sy,
                           j[2]])

    default = font.glyph_table.get(unichr(0), None)
    for i, c in enumerate(string):
      if c == '\n':
        make_verts()
        yoff += font.height * GAP
        xoff = 0.0
        temp_verts = []
        lines += 1
        continue #don't attempt to draw this character!

      glyph = font.glyph_table.get(c, default)
      if not glyph:
        continue
      w, h, texc, verts = glyph
      for j in verts:
        temp_verts.append((j[0]+xoff, j[1], j[2]))
      xoff += w
      for j in texc:
        self.texcoords.append(j)
      self.norms.extend(_NORMALS)

      # Take Into account unprinted \n characters
      stv = 4 * (i - lines)
      self.inds.extend([[stv, stv + 2, stv + 1], [stv, stv + 3, stv + 2]])

    make_verts()

    self.buf = []
    self.buf.append(Buffer(self, self.verts, self.texcoords, self.inds, self.norms))
    self.buf[0].textures = [font]
    self.buf[0].unib[1] = -1.0

########NEW FILE########
__FILENAME__ = TkWin
import os

from pi3d import *
from six.moves import tkinter

class TkWin(tkinter.Tk):
  """
  *TkWin* encapsulates a Tk window and keeps track of the mouse and keyboard.

  """
  def __init__(self, parent, title, width, height):
    """
    Arguments:

    *parent*
      Parent Tk window or Null for none.
    *title*
      Title for window.
    *width, height*
      Dimensions of window.
    """
    display = os.environ.get('DISPLAY', None)
    if not display:
      os.environ['DISPLAY'] = ':0'

    tkinter.Tk.__init__(self, parent)

    def mouseclick_callback(event):
      if not self.resized:
        self.ev = 'click'
        self.x = event.x
        self.y = event.y

    def mousemove_callback(event):
      if not self.resized:
        self.ev = 'move'
        self.x = event.x
        self.y = event.y

    def mousewheel_callback(event):
      if not self.resized:
        self.ev = 'wheel'
        self.num = event.num
        self.delta = event.delta

    def drag_callback(event):
      if not self.resized:
        self.ev = 'drag'
        self.x = event.x
        self.y = event.y
        mouserot = event.x

    def resize_callback(event):
      self.ev = 'resized'
      self.winx = self.winfo_x()
      self.winy = self.winfo_y()
      self.width = event.width
      self.height = event.height
      self.resized = True

    def key_callback(event):
      if not self.resized:
        self.ev = 'key'
        self.key = event.keysym
        self.char = event.char

    tkinter.Tk.bind(self, '<Button-1>', mouseclick_callback)
    tkinter.Tk.bind(self, '<B1-Motion>', drag_callback)
    tkinter.Tk.bind(self, '<Motion>', mousemove_callback)
    tkinter.Tk.bind(self, '<MouseWheel>', mousewheel_callback)
    tkinter.Tk.bind(self, '<Configure>', resize_callback)
    tkinter.Tk.bind_all(self, '<Key>', key_callback)
    tkinter.Tk.geometry(self, str(width) + 'x' + str(height))

    self.title(title)
    self.ev = ''
    self.resized = False


########NEW FILE########
__FILENAME__ = Utility
import copy
import bisect

from ctypes import c_float
from numpy import subtract, dot, divide, sqrt as npsqrt
from math import sqrt, sin, cos, tan, radians, pi, acos

from pi3d.constants import *
from pi3d.util.Ctypes import c_bytes

def normalize_v3(arr):
    ''' Normalize a numpy array of 3 component vectors shape=(n,3) '''
    lens = npsqrt( arr[:,0]**2 + arr[:,1]**2 + arr[:,2]**2)
    return divide(arr.T, lens).T

def magnitude(*args):
  """Return the magnitude (root mean square) of the vector."""
  return sqrt(dot(args, args))

def distance(v1, v2):
  """Return the distance between two points."""
  return magnitude(*subtract(v2, v1))

def from_polar(direction=0.0, magnitude=1.0):
  """
  Convert polar coordinates into Cartesian (x, y) coordinates.

  Arguments:

  *direction*
    Vector angle in degrees.
  *magnitude*
    Vector length.
  """
  return from_polar_rad(radians(direction), magnitude)

def from_polar_rad(direction=0.0, magnitude=1.0):
  """
  Convert polar coordinates into Cartesian (x, y) coordinates.

  Arguments:

  *direction*
    Vector angle in radians.
  *magnitude*
    Vector length.
  """
  return magnitude * cos(direction), magnitude * sin(direction)


def vec_sub(x, y):
  """Return the difference between two vectors."""
  return [a - b for a, b in zip(x, y)]

def vec_dot(x, y):
  """Return the dot product of two vectors."""
  return sum(a * b for a, b in zip(x, y))

def vec_cross(a,b):
  """Return the cross product of two vectors."""
  return [a[1] * b[2] - a[2] * b[1],
          a[2] * b[0] - a[0] * b[2],
          a[0] * b[1] - a[1] * b[0]]

def vec_normal(vec):
  """Return a vector normalized to unit length for a vector of non-zero length,
  otherwise returns the original vector."""
  n = sqrt(sum(x ** 2 for x in vec)) or 1
  return [x / n for x in vec]


def draw_level_of_detail(here, there, mlist):
  """
  Level Of Detail checking and rendering.  The shader and texture information
  must be set for all the buf objects in each model before draw_level_of_detail
  is called.

  Arguments:
    *here*
      An (x, y, z) tuple or array of view point.
    *there*
      An (x, y, z) tuple or array of model position.
    *mlist*
      A list of (distance, model) pairs with increasing distance, e.g.::

        [[20, model1], [100, model2], [250, None]]

      draw_level_of_detail() selects the first model that is more distant than
      the distance between the two points *here* and *there*, falling back to
      the last model otherwise.  The model None is not rendered and is a good
      way to make sure that nothing is drawn past a certain distance.
  """
  dist = distance(here, there)

  index = bisect.bisect_left(mlist, [dist, None])
  model = mlist[min(index, len(mlist) - 1)][1]
  model.position(there[0], there[1], there[2])
  model.draw()

"""
# TODO: None of these functions is actually called in the codebase.

def ctype_resize(array, new_size):
  resize(array, sizeof(array._type_) * new_size)
  return (array._type_ * new_size).from_address(addressof(array))

def showerror():
  return opengles.glGetError()

def limit(x, below, above):
  return max(min(x, above), below)

def angle_vecs(x1, y1, x2, y2, x3, y3):
  a = x2 - x1
  b = y2 - y1
  c = x2 - x3
  d = y2 - y3

  sqab = magnitude(a, b)
  sqcd = magnitude(c, d)
  l = sqab * sqcd
  if l == 0.0:  # TODO: comparison between floats.
    l = 0.0001
  aa = ((a * c) + (b * d)) / l
  if aa == -1.0:  # TODO: comparison between floats.
    return pi
  if aa == 0.0:   # TODO: comparison between floats.
    return 0.0
  dist = (a * y3 - b * x3 + x1 * b - y1 * a) / sqab
  angle = acos(aa)

  if dist > 0.0:
    return pi * 2 - angle
  else:
    return angle

def calc_normal(x1, y1, z1, x2, y2, z2):
  dx = x2 - x1
  dy = y2 - y1
  dz = z2 - z1
  mag = magnitude(dx, dy, dz)
  return (dx / mag, dy / mag, dz / mag)

def rotate(rotx, roty, rotz):
  # TODO: why the reverse order?
  rotatef(rotz, 0, 0, 1)
  rotatef(roty, 0, 1, 0)
  rotatef(rotx, 1, 0, 0)

def angle_between(x1, y1, x2, y2, x3, y3):
  #Return the angle between two 3-vectors, or 0.0 if one or the other vector is
  #empty.

  #Arguments:
  #  *x1, y1, z1*
  #    The coordinates of the first vector.
  #  *x2, y2, z2*
  #    The coordinates of the second vector.
  
  a = x2 - x1
  b = y2 - y1
  c = x2 - x3
  d = y2 - y3

  sqab = sqrt(a * a + b * b)
  sqcd = sqrt(c * c + d * d)
  l = sqab * sqcd
  if l == 0.0:
    return 0.0

  aa = (a * c + b * d) / l
  if aa == -1.0:
    return pi
  if aa == 0.0:
    return pi / 2
    # TODO: this was originally 0!  But if two vectors have a dot product
    # of zero, they are surely at right angles?

  dist = (a * y3 - b * x3  +  x1 * b - y1 * a) / sqab
  angle = acos(aa)

  if dist > 0.0:
    return pi / 2.0 - angle
  else:
    return angle

def translate(matrix, vec):
  
  #Translate a 4x4 matrix by a 3-vector

  #Arguments:
  #  *matrix*
  #    The 4x4 matrix to translate.
  #  *vec*
  #    A 3-vector translation in x, y, z axes.
  
  return mat_mult([[1, 0, 0, 0],
                   [0, 1, 0, 0],
                   [0, 0, 1, 0],
                   [vec[0], vec[1], vec[2], 1]], matrix)

def transform(matrix, x, y, z, rx, ry, rz, sx, sy, sz, cx, cy, cz):
  #""
  Rotate, scale and translate a 4x4 matrix.

  Arguments:
    *matrix*
      A 4x4 matrix to transform.
    *x, y, z*
      Translation in x, y and z axes.
    *rx, ry, rx*
      Rotations in x, y, and x axes.
    *sx, sy, sz*
      Scale factor in x, y, z axes.
    *cx, cy, cz*
      Center of the rotation.
  #""
  # TODO: do we really need this?  Wouldn't the separate parts suffice?
  #
  # TODO: the idea of translating then scaling then performing an inverse
  # translation seems like it wouldn't work?
  #

  matrix = copy.deepcopy(matrix)
  # TODO: is a copy really needed?  Surely translate returns a new matrix?

  matrix = translate(matrix, (x - cx, y - cy, z - cz))
  matrix = rotate(matrix, rx, ry, rz)
  if sx != 1.0 or sy != 1.0 or sz != 1.0:
    matrix = scale(matrix, sx, sy, sz)
  return translate(matrix, (cx, cy, cz))

def scale(matrix, sx, sy, sz):
  #""
  Scale a 4x4 matrix.

  Arguments:
    *sx, sy, sz*
      Scale factor in x, y, z axes.
  #""
  return mat_mult([[sx, 0, 0, 0],
                   [0, sy, 0, 0],
                   [0, 0, sz, 0],
                   [0, 0, 0, 1]], matrix)

def rotate(matrix, rx, ry, rz):
  #""
  Rotate a 4x4 matrix.

  Arguments:
    *matrix*
      A 4x4 matrix.
    *rx, ry, rx*
      Rotations in x, y, and x axes.
  #""
  if rz:
    matrix = rotateZ(matrix, rz)
  if rx:
    matrix = rotateX(matrix, rx)
  if ry:
    matrix = rotateY(matrix, ry)
  return matrix

def rotateX(matrix, angle):
  #""
  Rotate a 4x4 matrix around the x axis.

  Arguments:
    *matrix*
      A 4x4 matrix.
    *angle*
      Angle of rotation around the x axis.
  #""
  angle = radians(angle)
  c = cos(angle)
  s = sin(angle)
  return mat_mult([[1, 0, 0, 0],
                   [0, c, s, 0],
                   [0, -s, c, 0],
                   [0, 0, 0, 1]],
                  matrix)

def rotateY(matrix, angle):
  #""
  #Rotate a 4x4 matrix around the y axis.#

  #Arguments:
  #  *matrix*
  #    A 4x4 matrix.
  #  *angle*
  #    Angle of rotation around the y axis.
  #""
  angle = radians(angle)
  c = cos(angle)
  s = sin(angle)
  return mat_mult([[c, 0, -s, 0],
                   [0, 1, 0, 0],
                   [s, 0, c, 0],
                   [0, 0, 0, 1]],
                  matrix)

def rotateZ(matrix, angle):
  
  #Rotate a 4x4 matrix around the z axis.

  #Arguments:
  #  *matrix*
  #    A 4x4 matrix.
  #  *angle*
  #    Angle of rotation around the z axis.
  
  angle = radians(angle)
  c = cos(angle)
  s = sin(angle)
  return mat_mult([[c, s, 0, 0],
                   [-s, c, 0, 0],
                   [0, 0, 1, 0],
                   [0, 0, 0, 1]],
                  matrix)

def billboard_matrix():
  ""Return a matrix that copies x, y and sets z to 0.9.""
  return [[1.0, 0.0, 0.0, 0.0],
          [0.0, 1.0, 0.0, 0.0],
          [0.0, 0.0, 0.0, 0.0],
          [0.0, 0.0, 0.9, 1.0]]

# TODO: We should use numpy for all of these.
def mat_mult(x, y):
  ""Return the product of two 4x4 matrices.""
  return [[sum(x[i][j] * y[j][k] for j in range(4))
          for k in range(4)]
          for i in range(4)]

def mat_transpose(x):
  ""Return the transposition of a 4x4 matrix.""
  return [[x[k][i] for k in range(4)] for i in range(4)]

def vec_mat_mult(vec, mat):
  ""Return the product of a 4-d vector and a 4x4 matrix.

  Arguments:
    *vec*
      A vector of length 4.
    *mat*
      A 4x4 matrix.

  ""
  return [sum(vec[j] * mat[j][k] for j in range(4)) for k in range(4)]

def translate_matrix(vec):
  ""Return a matrix that translates by the given vector.""
  m = [[0] * 4] * 4
  for i in range(4):
    m[i][i] = 1.0
  for i in range(3):
    m[3][i] = vec[i]
  return m

RECT_NORMALS = c_bytes((0, 0, -1,
                        0, 0, -1,
                        0, 0, -1,
                        0, 0, -1))

RECT_TRIANGLES = c_bytes((3, 0, 1,
                          3, 1, 2))

def rect_triangles():
  opengles.glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_BYTE, RECT_TRIANGLES)

def sqsum(*args):
  ""Return the sum of the squares of its arguments.

  DEPRECATED:  use dot(x, x).
  ""
  return dot(args, args)

def load_identity():
  opengles.glLoadIdentity()

def dotproduct(x1, y1, z1, x2, y2, z2):
  ""Return the dot product of two 3-dimensional vectors given by coordinates.
  ""
  return x1 * x2 + y1 * y2 + z1 * z2

def crossproduct(x1, y1, z1, x2, y2, z2):
  ""Return the cross product of two 3-dimensional vectors given by coordinates.
  ""
  return y1 * z2 - z1 * y2, z1 * x2 - x1 * z2, x1 * y2 - y1 * x2

"""

########NEW FILE########
__FILENAME__ = x
from ctypes import *

X_PROTOCOL = 11
X_PROTOCOL_REVISION = 0

#~ /* Resources */

#~ /*
 #~ * _XSERVER64 must ONLY be defined when compiling X server sources on
 #~ * systems where unsigned long is not 32 bits, must NOT be used in
 #~ * client or library code.
 #~ */

#~ typedef unsigned long XID;
#~ typedef unsigned long Mask;
#~ typedef unsigned long Atom;  /* Also in Xdefs.h */
#~ typedef unsigned long VisualID;
#~ typedef unsigned long Time;
XID = c_ulong
Mask = c_ulong
Atom = c_ulong
VisualID = c_ulong
Time = c_ulong

#~ typedef XID Window;
#~ typedef XID Drawable;
#~ typedef XID Font;
#~ typedef XID Pixmap;
#~ typedef XID Cursor;
#~ typedef XID Colormap;
#~ typedef XID GContext;
#~ typedef XID KeySym;
Window = XID
Drawable = XID
Font = XID
Pixmap = XID
Cursor = XID
Colormap = XID
GContext = XID
KeySym = XID

#~ typedef unsigned char KeyCode;
KeyCode = c_ubyte

# ****************************************************************
# * RESERVED RESOURCE AND CONSTANT DEFINITIONS
# ****************************************************************

NULL = None

#ifndef None
NONE = 0 # universal null resource or null atom 
#endif

ParentRelative = 1 # background pixmap in CreateWindow
#     and ChangeWindowAttributes 

CopyFromParent = 0 # border pixmap in CreateWindow
#        and ChangeWindowAttributes
#       special VisualID and special window
#        class passed to CreateWindow 

PointerWindow = 0 # destination window in SendEvent 
InputFocus = 1 # destination window in SendEvent 

PointerRoot = 1 # focus window in SetInputFocus 

AnyPropertyType = 0 # special Atom, passed to GetProperty 

AnyKey = 0 # special Key Code, passed to GrabKey 

AnyButton = 0 # special Button Code, passed to GrabButton 

AllTemporary = 0 # special Resource ID passed to KillClient 

CurrentTime = 0 # special Time 

NoSymbol = 0 # special KeySym 

# ****************************************************************
# * EVENT DEFINITIONS
# ****************************************************************

#  Input Event Masks. Used as event-mask window attribute and as arguments
#   to Grab requests.  Not to be confused with event names.  

NoEventMask =  0
KeyPressMask =   (1<<0)
KeyReleaseMask =   (1<<1)
ButtonPressMask =  (1<<2)
ButtonReleaseMask =  (1<<3)
EnterWindowMask =  (1<<4)
LeaveWindowMask =  (1<<5)
PointerMotionMask =  (1<<6)
PointerMotionHintMask =  (1<<7)
Button1MotionMask  = (1<<8)
Button2MotionMask = (1<<9)
Button3MotionMask = (1<<10)
Button4MotionMask = (1<<11)
Button5MotionMask = (1<<12)
ButtonMotionMask = (1<<13)
KeymapStateMask  = (1<<14)
ExposureMask  = (1<<15)
VisibilityChangeMask = (1<<16)
StructureNotifyMask = (1<<17)
ResizeRedirectMask = (1<<18)
SubstructureNotifyMask = (1<<19)
SubstructureRedirectMask= (1<<20)
FocusChangeMask  = (1<<21)
PropertyChangeMask = (1<<22)
ColormapChangeMask = (1<<23)
OwnerGrabButtonMask = (1<<24)

#  Event names.  Used in "type" field in XEvent structures.  Not to be
#confused with event masks above.  They start from 2 because 0 and 1
#are reserved in the protocol for errors and replies. 

KeyPress = 2
KeyRelease = 3
ButtonPress = 4
ButtonRelease = 5
MotionNotify = 6
EnterNotify = 7
LeaveNotify = 8
FocusIn  = 9
FocusOut = 10
KeymapNotify = 11
Expose  = 12
GraphicsExpose = 13
NoExpose = 14
VisibilityNotify =15
CreateNotify = 16
DestroyNotify = 17
UnmapNotify  =18
MapNotify  =19
MapRequest = 20
ReparentNotify = 21
ConfigureNotify = 22
ConfigureRequest =23
GravityNotify = 24
ResizeRequest = 25
CirculateNotify = 26
CirculateRequest= 27
PropertyNotify = 28
SelectionClear = 29
SelectionRequest= 30
SelectionNotify = 31
ColormapNotify = 32
ClientMessage = 33
MappingNotify = 34
GenericEvent = 35
LASTEvent = 36 # must be bigger than any event # 


#  Key masks. Used as modifiers to GrabButton and GrabKey, results of QueryPointer,
#   state in various key-, mouse-, and button-related events. 

ShiftMask = (1<<0)
LockMask = (1<<1)
ControlMask = (1<<2)
Mod1Mask = (1<<3)
Mod2Mask = (1<<4)
Mod3Mask = (1<<5)
Mod4Mask = (1<<6)
Mod5Mask = (1<<7)

#  modifier names.  Used to build a SetModifierMapping request or
#   to read a GetModifierMapping request.  These correspond to the
#   masks defined above. 
ShiftMapIndex = 0
LockMapIndex = 1
ControlMapIndex = 2
Mod1MapIndex = 3
Mod2MapIndex = 4
Mod3MapIndex = 5
Mod4MapIndex = 6
Mod5MapIndex = 7


#  button masks.  Used in same manner as Key masks above. Not to be confused
#   with button names below. 

Button1Mask = (1<<8)
Button2Mask  =(1<<9)
Button3Mask = (1<<10)
Button4Mask = (1<<11)
Button5Mask = (1<<12)

AnyModifier = (1<<15)  # used in GrabButton, GrabKey 


#  button names. Used as arguments to GrabButton and as detail in ButtonPress
#   and ButtonRelease events.  Not to be confused with button masks above.
#   Note that 0 is already defined above as "AnyButton".  

Button1  = 1
Button2  = 2
Button3  = 3
Button4  = 4
Button5  = 5

#  Notify modes 

NotifyNormal = 0
NotifyGrab = 1
NotifyUngrab = 2
NotifyWhileGrabbed= 3

NotifyHint = 1 # for MotionNotify events 

#  Notify detail 

NotifyAncestor = 0
NotifyVirtual = 1
NotifyInferior = 2
NotifyNonlinear = 3
NotifyNonlinearVirtual = 4
NotifyPointer = 5
NotifyPointerRoot =6
NotifyDetailNone =7

#  Visibility notify 

VisibilityUnobscured = 0
VisibilityPartiallyObscured= 1
VisibilityFullyObscured = 2

#  Circulation request 

PlaceOnTop = 0
PlaceOnBottom = 1

#  protocol families 

FamilyInternet = 0 # IPv4 
FamilyDECnet = 1
FamilyChaos = 2
FamilyInternet6 = 6 # IPv6 

#  authentication families not tied to a specific protocol 
FamilyServerInterpreted = 5

#  Property notification 

PropertyNewValue =0
PropertyDelete =1

#  Color Map notification 

ColormapUninstalled= 0
ColormapInstalled =1

#  GrabPointer, GrabButton, GrabKeyboard, GrabKey Modes 

GrabModeSync = 0
GrabModeAsync = 1

#  GrabPointer, GrabKeyboard reply status 

GrabSuccess = 0
AlreadyGrabbed = 1
GrabInvalidTime = 2
GrabNotViewable = 3
GrabFrozen = 4

#  AllowEvents modes 

AsyncPointer = 0
SyncPointer  = 1
ReplayPointer = 2
AsyncKeyboard = 3
SyncKeyboard = 4
ReplayKeyboard = 5
AsyncBoth = 6
SyncBoth = 7

#  Used in SetInputFocus, GetInputFocus 

RevertToNone = NONE
RevertToPointerRoot = PointerRoot
RevertToParent = 2

# ****************************************************************
# * ERROR CODES
# ****************************************************************

Success    = 0 # everything's okay 
BadRequest   = 1 # bad request code 
BadValue   = 2 # int parameter out of range 
BadWindow   = 3 # parameter not a Window 
BadPixmap   = 4 # parameter not a Pixmap 
BadAtom    = 5 # parameter not an Atom 
BadCursor   = 6 # parameter not a Cursor 
BadFont    = 7 # parameter not a Font 
BadMatch   = 8 # parameter mismatch 
BadDrawable   = 9 # parameter not a Pixmap or Window 
BadAccess   = 10 # depending on context:
#     - key/button already grabbed
#     - attempt to free an illegal
#       cmap entry
#    - attempt to store into a read-only
#       color map entry.
#     - attempt to modify the access control
#       list from other than the local host.
#    
BadAlloc  = 11 # insufficient resources 
BadColor  = 12 # no such colormap 
BadGC   = 13 # parameter not a GC 
BadIDChoice  = 14 # choice not in range or already used 
BadName   = 15 # font or color name doesn't exist 
BadLength  = 16 # Request length incorrect 
BadImplementation = 17 # server is defective 

FirstExtensionError = 128
LastExtensionError = 255

# ****************************************************************
# * WINDOW DEFINITIONS
# ****************************************************************

#  Window classes used by CreateWindow 
#  Note that CopyFromParent is already defined as 0 above 

InputOutput  = 1
InputOnly  = 2

#  Window attributes for CreateWindow and ChangeWindowAttributes 

CWBackPixmap=  (1<<0)
CWBackPixel = (1<<1)
CWBorderPixmap = (1<<2)
CWBorderPixel =    (1<<3)
CWBitGravity = (1<<4)
CWWinGravity = (1<<5)
CWBackingStore   =    (1<<6)
CWBackingPlanes   =   (1<<7)
CWBackingPixel   =   (1<<8)
CWOverrideRedirect =(1<<9)
CWSaveUnder = (1<<10)
CWEventMask = (1<<11)
CWDontPropagate   =   (1<<12)
CWColormap = (1<<13)
CWCursor  =    (1<<14)

#  ConfigureWindow structure 

CWX  = (1<<0)
CWY  = (1<<1)
CWWidth  = (1<<2)
CWHeight = (1<<3)
CWBorderWidth = (1<<4)
CWSibling = (1<<5)
CWStackMode = (1<<6)


#  Bit Gravity 

ForgetGravity = 0
NorthWestGravity =1
NorthGravity  =2
NorthEastGravity= 3
WestGravity = 4
CenterGravity = 5
EastGravity  =6
SouthWestGravity= 7
SouthGravity = 8
SouthEastGravity= 9
StaticGravity = 10

#  Window gravity + bit gravity above 

UnmapGravity = 0

#  Used in CreateWindow for backing-store hint 

NotUseful   =   0
WhenMapped   =  1
Always    =  2

#  Used in GetWindowAttributes reply 

IsUnmapped = 0
IsUnviewable = 1
IsViewable = 2

#  Used in ChangeSaveSet 

SetModeInsert   =  0
SetModeDelete =    1

#  Used in ChangeCloseDownMode 

DestroyAll    =    0
RetainPermanent   =   1
RetainTemporary   =   2

#  Window stacking method (in configureWindow) 

Above     =  0
Below    =   1
TopIf    =   2
BottomIf    =   3
Opposite     =  4

#  Circulation direction 

RaiseLowest    =   0
LowerHighest   =   1

#  Property modes 

PropModeReplace =  0
PropModePrepend =  1
PropModeAppend  =  2

# ****************************************************************
# * GRAPHICS DEFINITIONS
# ****************************************************************

#  graphics functions, as in GC.alu 

GXclear =  0x0  # 0 
GXand =  0x1  # src AND dst 
GXandReverse=  0x2  # src AND NOT dst 
GXcopy  = 0x3  # src 
GXandInverted = 0x4  # NOT src AND dst 
GXnoop=   0x5  # dst 
GXxor =  0x6  # src XOR dst 
GXor =  0x7  # src OR dst 
GXnor =  0x8  # NOT src AND NOT dst 
GXequiv =  0x9  # NOT src XOR dst 
GXinvert = 0xa  # NOT dst 
GXorReverse = 0xb  # src OR NOT dst 
GXcopyInverted = 0xc  # NOT src 
GXorInverted = 0xd  # NOT src OR dst 
GXnand  = 0xe  # NOT src OR NOT dst 
GXset =  0xf  # 1 

#  LineStyle 

LineSolid = 0
LineOnOffDash = 1
LineDoubleDash = 2

#  capStyle 

CapNotLast = 0
CapButt  = 1
CapRound = 2
CapProjecting = 3

#  joinStyle 

JoinMiter = 0
JoinRound = 1
JoinBevel = 2

#  fillStyle 

FillSolid = 0
FillTiled = 1
FillStippled = 2
FillOpaqueStippled =3

#  fillRule 

EvenOddRule = 0
WindingRule  =1

#  subwindow mode 

ClipByChildren = 0
IncludeInferiors= 1

#  SetClipRectangles ordering 

Unsorted = 0
YSorted  = 1
YXSorted = 2
YXBanded = 3

#  CoordinateMode for drawing routines 

CoordModeOrigin = 0 # relative to the origin 
CoordModePrevious =   1 # relative to previous point 

#  Polygon shapes 

Complex  = 0 # paths may intersect 
Nonconvex = 1 # no paths intersect, but not convex 
Convex  = 2 # wholly convex 

#  Arc modes for PolyFillArc 

ArcChord = 0 # join endpoints of arc 
ArcPieSlice = 1 # join endpoints to center of arc 

#  GC components: masks used in CreateGC, CopyGC, ChangeGC, OR'ed into
#   GC.stateChanges 

GCFunction   =  (1<<0)
GCPlaneMask   =    (1<<1)
GCForeground  =    (1<<2)
GCBackground  =    (1<<3)
GCLineWidth   =    (1<<4)
GCLineStyle   =    (1<<5)
GCCapStyle    =    (1<<6)
GCJoinStyle  =(1<<7)
GCFillStyle  =(1<<8)
GCFillRule = (1<<9)
GCTile   =(1<<10)
GCStipple  =(1<<11)
GCTileStipXOrigin= (1<<12)
GCTileStipYOrigin =(1<<13)
GCFont   = (1<<14)
GCSubwindowMode = (1<<15)
GCGraphicsExposures = (1<<16)
GCClipXOrigin = (1<<17)
GCClipYOrigin = (1<<18)
GCClipMask = (1<<19)
GCDashOffset = (1<<20)
GCDashList = (1<<21)
GCArcMode = (1<<22)

GCLastBit = 22
# ****************************************************************
# * FONTS
# ****************************************************************

#  used in QueryFont -- draw direction 

FontLeftToRight = 0
FontRightToLeft = 1

FontChange = 255

# ****************************************************************
# *  IMAGING
# ****************************************************************

#  ImageFormat -- PutImage, GetImage 

XYBitmap = 0 # depth 1, XYFormat 
XYPixmap = 1 # depth == drawable depth 
ZPixmap  = 2 # depth == drawable depth 

# ****************************************************************
# *  COLOR MAP STUFF
# ****************************************************************

#  For CreateColormap 

AllocNone = 0 # create map with no entries 
AllocAll = 1 # allocate entire map writeable 


#  Flags used in StoreNamedColor, StoreColors 

DoRed  = (1<<0)
DoGreen  = (1<<1)
DoBlue  = (1<<2)

# ****************************************************************
# * CURSOR STUFF
# ****************************************************************

#  QueryBestSize Class 

CursorShape = 0 # largest size that can be displayed 
TileShape = 1 # size tiled fastest 
StippleShape = 2 # size stippled fastest 

# ****************************************************************
# * KEYBOARD/POINTER STUFF
# ****************************************************************

AutoRepeatModeOff= 0
AutoRepeatModeOn= 1
AutoRepeatModeDefault =2

LedModeOff = 0
LedModeOn = 1

#  masks for ChangeKeyboardControl 

KBKeyClickPercent= (1<<0)
KBBellPercent = (1<<1)
KBBellPitch  = (1<<2)
KBBellDuration = (1<<3)
KBLed  = (1<<4)
KBLedMode = (1<<5)
KBKey  = (1<<6)
KBAutoRepeatMode =(1<<7)

MappingSuccess =  0
MappingBusy    =  1
MappingFailed = 2

MappingModifier  = 0
MappingKeyboard  = 1
MappingPointer  = 2

# ****************************************************************
# * SCREEN SAVER STUFF
# ****************************************************************

DontPreferBlanking= 0
PreferBlanking  = 1
DefaultBlanking  = 2

DisableScreenSaver = 0
DisableScreenInterval = 0

DontAllowExposures = 0
AllowExposures  = 1
DefaultExposures = 2

#  for ForceScreenSaver 

ScreenSaverReset = 0
ScreenSaverActive = 1

# ****************************************************************
# * HOSTS AND CONNECTIONS
# ****************************************************************

#  for ChangeHosts 

HostInsert = 0
HostDelete  = 1

#  for ChangeAccessControl 

EnableAccess = 1
DisableAccess = 0

#  Display classes  used in opening the connection
# * Note that the statically allocated ones are even numbered and the
# * dynamically changeable ones are odd numbered 

StaticGray = 0
GrayScale = 1
StaticColor = 2
PseudoColor = 3
TrueColor = 4
DirectColor = 5


#  Byte order  used in imageByteOrder and bitmapBitOrder 

LSBFirst = 0
MSBFirst = 1

########NEW FILE########
__FILENAME__ = xcomposite

import ctypes

from xlib import Window, Display

libXcomposite = ctypes.CDLL('libXcomposite.so.1')


# void XCompositeRedirectSubwindows(Display *dpy, Window window, int update);
XCompositeRedirectSubwindows = libXcomposite.XCompositeRedirectSubwindows
XCompositeRedirectSubwindows.argtypes = [ctypes.POINTER(Display), Window, ctypes.c_int]
# Window XCompositeGetOverlayWindow(Display *dpy, Window window);
XCompositeGetOverlayWindow = libXcomposite.XCompositeGetOverlayWindow
XCompositeGetOverlayWindow.argtypes = [ctypes.POINTER(Display), Window]
XCompositeGetOverlayWindow.restype = Window


#define CompositeRedirectAutomatic		0
CompositeRedirectAutomatic = 0
#define CompositeRedirectManual			1
CompositeRedirectManual = 1


########NEW FILE########
__FILENAME__ = xfixes

import ctypes

from xlib import Window, Display, XID, XRectangle


libXFixes = ctypes.CDLL('libXfixes.so.3')


# void XFixesHideCursor(Display *dpy, Window window);
XFixesHideCursor = libXFixes.XFixesHideCursor
XFixesHideCursor.argtypes = [ctypes.POINTER(Display), Window]
# XserverRegion XFixesCreateRegion(Display *dpy, XRectangle *rectangles, int nrectangles);
XserverRegion = XID
XFixesCreateRegion = libXFixes.XFixesCreateRegion
XFixesCreateRegion.argtypes = [ctypes.POINTER(Display), ctypes.POINTER(XRectangle), ctypes.c_int]
XFixesCreateRegion.restype = XserverRegion
# void XFixesSetWindowShapeRegion(Display *dpy, Window win, int shape_kind, int x_off, int y_off, XserverRegion region);
XFixesSetWindowShapeRegion = libXFixes.XFixesSetWindowShapeRegion
XFixesSetWindowShapeRegion.argtypes = [ctypes.POINTER(Display), Window, ctypes.c_int, ctypes.c_int, ctypes.c_int, XserverRegion]
# void XFixesDestroyRegion (Display *dpy, XserverRegion region);
XFixesDestroyRegion = libXFixes.XFixesDestroyRegion
XFixesDestroyRegion.argtypes = [ctypes.POINTER(Display), XserverRegion]


#define ShapeBounding		0
ShapeBounding = 0
#define ShapeClip			1
ShapeClip = 1
#define ShapeInput			2
ShapeInput = 2


########NEW FILE########
__FILENAME__ = xlib
from six.moves import xrange

from ctypes import *
from .x import *

libX11 = CDLL('libX11.so.6')

#/*
# *  Xlib.h - Header definition and support file for the C subroutine
# *  interface library (Xlib) to the X Window System Protocol (V11).
# *  Structures and symbols starting with "_" are private to the library.
# */

XlibSpecificationRelease = 6

#~ #ifdef USG
#~ #ifndef __TYPES__
#~ #include <sys/types.h>      /* forgot to protect it... */
#~ #define __TYPES__
#~ #endif /* __TYPES__ */
#~ #else
#~ #if defined(_POSIX_SOURCE) && defined(MOTOROLA)
#~ #undef _POSIX_SOURCE
#~ #include <sys/types.h>
#~ #define _POSIX_SOURCE
#~ #else
#~ #include <sys/types.h>
#~ #endif
#~ #endif /* USG */

#~ #if defined(__SCO__) || defined(__UNIXWARE__)
#~ #include <stdint.h>
#~ #endif

#~ #include <X11/X.h>

#/* applications should not depend on these two headers being included! */
#~ #include <X11/Xfuncproto.h>
#~ #include <X11/Xosdefs.h>

#~ #ifndef X_WCHAR
#~ #ifdef X_NOT_STDC_ENV
#~ #ifndef ISC
#~ #define X_WCHAR
#~ #endif
#~ #endif
#~ #endif

#~ #ifndef X_WCHAR
#~ #include <stddef.h>
#~ #else
#~ #ifdef __UNIXOS2__
#~ #include <stdlib.h>
#~ #else
#~ /* replace this with #include or typedef appropriate for your system */
#~ typedef unsigned long wchar_t;
#~ #endif
#~ #endif

#~ #if defined(ISC) && defined(USE_XMBTOWC)
#~ #define wctomb(a,b)  _Xwctomb(a,b)
#~ #define mblen(a,b)  _Xmblen(a,b)
#~ #ifndef USE_XWCHAR_STRING
#~ #define mbtowc(a,b,c)  _Xmbtowc(a,b,c)
#~ #endif
#~ #endif

#~ extern int
#~ _Xmblen(
#~ #ifdef ISC
    #~ char const *str,
    #~ size_t len
#~ #else
    #~ char *str,
    #~ int len
#~ #endif
    #~ );

#/* API mentioning "UTF8" or "utf8" is an XFree86 extension, introduced in
#   November 2000. Its presence is indicated through the following macro. */
X_HAVE_UTF8_STRING = 1

#typedef char *XPointer;
XPointer = c_char_p

#define Bool int
Bool = c_int

#define Status int
Status = c_int

#~ #define True 1
#~ #define False 0

QueuedAlready = 0
QueuedAfterReading = 1
QueuedAfterFlush = 2

#define ConnectionNumber(dpy)   (((_XPrivDisplay)dpy)->fd)
#define RootWindow(dpy, scr)   (ScreenOfDisplay(dpy,scr)->root)
#define DefaultScreen(dpy)   (((_XPrivDisplay)dpy)->default_screen)
#define DefaultRootWindow(dpy)   (ScreenOfDisplay(dpy,DefaultScreen(dpy))->root)
#define DefaultVisual(dpy, scr) (ScreenOfDisplay(dpy,scr)->root_visual)
#define DefaultGC(dpy, scr)   (ScreenOfDisplay(dpy,scr)->default_gc)
#define BlackPixel(dpy, scr)   (ScreenOfDisplay(dpy,scr)->black_pixel)
#define WhitePixel(dpy, scr)   (ScreenOfDisplay(dpy,scr)->white_pixel)
#define AllPlanes     ((unsigned long)~0L)
#define QLength(dpy)     (((_XPrivDisplay)dpy)->qlen)
#define DisplayWidth(dpy, scr)   (ScreenOfDisplay(dpy,scr)->width)
#define DisplayHeight(dpy, scr) (ScreenOfDisplay(dpy,scr)->height)
#define DisplayWidthMM(dpy, scr)(ScreenOfDisplay(dpy,scr)->mwidth)
#define DisplayHeightMM(dpy, scr)(ScreenOfDisplay(dpy,scr)->mheight)
#define DisplayPlanes(dpy, scr) (ScreenOfDisplay(dpy,scr)->root_depth)
#define DisplayCells(dpy, scr)   (DefaultVisual(dpy,scr)->map_entries)
#define ScreenCount(dpy)   (((_XPrivDisplay)dpy)->nscreens)
#define ServerVendor(dpy)   (((_XPrivDisplay)dpy)->vendor)
#define ProtocolVersion(dpy)   (((_XPrivDisplay)dpy)->proto_major_version)
#define ProtocolRevision(dpy)   (((_XPrivDisplay)dpy)->proto_minor_version)
#define VendorRelease(dpy)   (((_XPrivDisplay)dpy)->release)
#define DisplayString(dpy)   (((_XPrivDisplay)dpy)->display_name)
#define DefaultDepth(dpy, scr)   (ScreenOfDisplay(dpy,scr)->root_depth)
#define DefaultColormap(dpy, scr)(ScreenOfDisplay(dpy,scr)->cmap)
#define BitmapUnit(dpy)   (((_XPrivDisplay)dpy)->bitmap_unit)
#define BitmapBitOrder(dpy)   (((_XPrivDisplay)dpy)->bitmap_bit_order)
#define BitmapPad(dpy)     (((_XPrivDisplay)dpy)->bitmap_pad)
#define ImageByteOrder(dpy)   (((_XPrivDisplay)dpy)->byte_order)
#ifdef CRAY /* unable to get WORD64 without pulling in other symbols */
#define NextRequest(dpy)  XNextRequest(dpy)
#else
#define NextRequest(dpy)  (((_XPrivDisplay)dpy)->request + 1)
#endif
#define LastKnownRequestProcessed(dpy)  (((_XPrivDisplay)dpy)->last_request_read)

#/* macros for screen oriented applications (toolkit) */

#define ScreenOfDisplay(dpy, scr)(&((_XPrivDisplay)dpy)->screens[scr])
#define DefaultScreenOfDisplay(dpy) ScreenOfDisplay(dpy,DefaultScreen(dpy))
#define DisplayOfScreen(s)  ((s)->display)
#define RootWindowOfScreen(s)  ((s)->root)
#define BlackPixelOfScreen(s)  ((s)->black_pixel)
#define WhitePixelOfScreen(s)  ((s)->white_pixel)
#define DefaultColormapOfScreen(s)((s)->cmap)
#define DefaultDepthOfScreen(s)  ((s)->root_depth)
#define DefaultGCOfScreen(s)  ((s)->default_gc)
#define DefaultVisualOfScreen(s)((s)->root_visual)
#define WidthOfScreen(s)  ((s)->width)
#define HeightOfScreen(s)  ((s)->height)
#define WidthMMOfScreen(s)  ((s)->mwidth)
#define HeightMMOfScreen(s)  ((s)->mheight)
#define PlanesOfScreen(s)  ((s)->root_depth)
#define CellsOfScreen(s)  (DefaultVisualOfScreen((s))->map_entries)
#define MinCmapsOfScreen(s)  ((s)->min_maps)
#define MaxCmapsOfScreen(s)  ((s)->max_maps)
#define DoesSaveUnders(s)  ((s)->save_unders)
#define DoesBackingStore(s)  ((s)->backing_store)
#define EventMaskOfScreen(s)  ((s)->root_input_mask)

#/*
# * Extensions need a way to hang private data on some structures.
# */
#~ typedef struct _XExtData {
  #~ int number;    /* number returned by XRegisterExtension */
  #~ struct _XExtData *next;  /* next item on list of data for structure */
  #~ int (*free_private)(  /* called to free private storage */
  #~ struct _XExtData *extension
  #~ );
  #~ XPointer private_data;  /* data private to this extension. */
#~ } XExtData;
class _XExtData(Structure): pass
_XExtData._fields_ = [
  ('number', c_int),
  ('next', POINTER(_XExtData)),
  ('free_private', c_void_p),
  ('private_data', XPointer),
]
XExtData = _XExtData

#/*
# * This file contains structures used by the extension mechanism.
# */
#~ typedef struct {    /* public to extension, cannot be changed */
  #~ int extension;    /* extension number */
  #~ int major_opcode;  /* major op-code assigned by server */
  #~ int first_event;  /* first event number for the extension */
  #~ int first_error;  /* first error number for the extension */
#~ } XExtCodes;
class XExtCodes(Structure):
  _fields_ = [
    ('extension', c_int),
    ('major_opcode', c_int),
    ('first_event', c_int),
    ('first_error', c_int),
  ]

#/*
# * Data structure for retrieving info about pixmap formats.
# */

#~ typedef struct {
    #~ int depth;
    #~ int bits_per_pixel;
    #~ int scanline_pad;
#~ } XPixmapFormatValues;
class XPixmapFormatValues(Structure):
  _fields_ = [
    ('depth', c_int),
    ('bits_per_pixel', c_int),
    ('scanline_pad', c_int),
  ]

#/*
# * Data structure for setting graphics context.
# */
#~ typedef struct {
  #~ int function;    /* logical operation */
  #~ unsigned long plane_mask;/* plane mask */
  #~ unsigned long foreground;/* foreground pixel */
  #~ unsigned long background;/* background pixel */
  #~ int line_width;    /* line width */
  #~ int line_style;     /* LineSolid, LineOnOffDash, LineDoubleDash */
  #~ int cap_style;      /* CapNotLast, CapButt,
           #~ CapRound, CapProjecting */
  #~ int join_style;     /* JoinMiter, JoinRound, JoinBevel */
  #~ int fill_style;     /* FillSolid, FillTiled,
           #~ FillStippled, FillOpaeueStippled */
  #~ int fill_rule;      /* EvenOddRule, WindingRule */
  #~ int arc_mode;    /* ArcChord, ArcPieSlice */
  #~ Pixmap tile;    /* tile pixmap for tiling operations */
  #~ Pixmap stipple;    /* stipple 1 plane pixmap for stipping */
  #~ int ts_x_origin;  /* offset for tile or stipple operations */
  #~ int ts_y_origin;
        #~ Font font;          /* default text font for text operations */
  #~ int subwindow_mode;     /* ClipByChildren, IncludeInferiors */
  #~ Bool graphics_exposures;/* boolean, should exposures be generated */
  #~ int clip_x_origin;  /* origin for clipping */
  #~ int clip_y_origin;
  #~ Pixmap clip_mask;  /* bitmap clipping; other calls for rects */
  #~ int dash_offset;  /* patterned/dashed line information */
  #~ char dashes;
#~ } XGCValues;
class XGCValues(Structure):
  _fields_ = [
    ('function', c_int),
    ('plane_mask', c_ulong),
    ('foreground', c_ulong),
    ('background', c_ulong),
    ('line_width', c_int),
    ('line_style', c_int),
    ('cap_style', c_int),
    ('join_style', c_int),
    ('fill_style', c_int),
    ('fill_rule', c_int),
    ('arc_mode', c_int),
    ('tile', Pixmap),
    ('stipple', Pixmap),
    ('ts_x_origin', c_int),
    ('ts_y_origin', c_int),
    ('font', Font),
    ('subwindow_mode', c_int),
    ('graphics_exposures', Bool),
    ('clip_x_origin', c_int),
    ('clip_y_origin', c_int),
    ('clip_mask', Pixmap),
    ('dash_offset', c_int),
    ('dashes', c_char),
  ]

#/*
# * Graphics context.  The contents of this structure are implementation
# * dependent.  A GC should be treated as opaque by application code.
# */

#~ typedef struct _XGC
#~ #ifdef XLIB_ILLEGAL_ACCESS
#~ {
    #~ XExtData *ext_data;  /* hook for extension to hang data */
    #~ GContext gid;  /* protocol ID for graphics context */
    #~ /* there is more to this structure, but it is private to Xlib */
#~ }
#~ #endif
#~ *GC;
class _XGC(Structure):
  _fields_ = [
    ('ext_data', POINTER(XExtData)),
    ('gid', GContext),
  ]
GC = POINTER(_XGC)

#/*
# * Visual structure; contains information about colormapping possible.
# */
#~ typedef struct {
  #~ XExtData *ext_data;  /* hook for extension to hang data */
  #~ VisualID visualid;  /* visual id of this visual */
#~ #if defined(__cplusplus) || defined(c_plusplus)
  #~ int c_class;    /* C++ class of screen (monochrome, etc.) */
#~ #else
  #~ int class;    /* class of screen (monochrome, etc.) */
#~ #endif
  #~ unsigned long red_mask, green_mask, blue_mask;  /* mask values */
  #~ int bits_per_rgb;  /* log base 2 of distinct color values */
  #~ int map_entries;  /* color map entries */
#~ } Visual;
class Visual(Structure):
  _fields_ = [
    ('ext_data', POINTER(XExtData)),
    ('visualid', VisualID),
    ('c_class', c_int),
    ('red_mask', c_ulong),
    ('green_mask', c_ulong),
    ('blue_mask', c_ulong),
    ('bits_per_rgb', c_int),
    ('map_entries', c_int),
  ]

#/*
# * Depth structure; contains information for each possible depth.
# */
#~ typedef struct {
  #~ int depth;    /* this depth (Z) of the depth */
  #~ int nvisuals;    /* number of Visual types at this depth */
  #~ Visual *visuals;  /* list of visuals possible at this depth */
#~ } Depth;
class Depth(Structure):
  _fields_ = [
    ('depth', c_int),
    ('nvisuals', c_int),
    ('visuals', POINTER(Visual)),
  ]

#/*
# * Information about the screen.  The contents of this structure are
# * implementation dependent.  A Screen should be treated as opaque
# * by application code.
# */

#~ struct _XDisplay;    /* Forward declare before use for C++ */
class _XDisplay(Structure): pass
#_XDisplay._pack_ = 1

#~ typedef struct {
  #~ XExtData *ext_data;  /* hook for extension to hang data */
  #~ struct _XDisplay *display;/* back pointer to display structure */
  #~ Window root;    /* Root window id. */
  #~ int width, height;  /* width and height of screen */
  #~ int mwidth, mheight;  /* width and height of  in millimeters */
  #~ int ndepths;    /* number of depths possible */
  #~ Depth *depths;    /* list of allowable depths on the screen */
  #~ int root_depth;    /* bits per pixel */
  #~ Visual *root_visual;  /* root visual */
  #~ GC default_gc;    /* GC for the root root visual */
  #~ Colormap cmap;    /* default color map */
  #~ unsigned long white_pixel;
  #~ unsigned long black_pixel;  /* White and Black pixel values */
  #~ int max_maps, min_maps;  /* max and min color maps */
  #~ int backing_store;  /* Never, WhenMapped, Always */
  #~ Bool save_unders;
  #~ long root_input_mask;  /* initial root input mask */
#~ } Screen;
class Screen(Structure):
  _fields_ = [
    ('ext_data', POINTER(XExtData)),
    ('display', POINTER(_XDisplay)),
    ('root', Window),
    ('width', c_int),
    ('height', c_int),
    ('mwidth', c_int),
    ('mheight', c_int),
    ('ndepths', c_int),
    ('depths', POINTER(Depth)),
    ('root_depth', c_int),
    ('root_visual', POINTER(Visual)),
    ('default_gc', GC),
    ('cmap', Colormap),
    ('white_pixel', c_ulong),
    ('black_pixel', c_ulong),
    ('max_maps', c_int),
    ('min_maps', c_int),
    ('backing_store', c_int),
    ('save_unders', Bool),
    ('root_input_mask', c_long),
  ]

#/*
# * Format structure; describes ZFormat data the screen will understand.
# */
#~ typedef struct {
  #~ XExtData *ext_data;  /* hook for extension to hang data */
  #~ int depth;    /* depth of this image format */
  #~ int bits_per_pixel;  /* bits/pixel at this depth */
  #~ int scanline_pad;  /* scanline must padded to this multiple */
#~ } ScreenFormat;
class ScreenFormat(Structure):
  _fields_ = [
    ('ext_data', POINTER(XExtData)),
    ('depth', c_int),
    ('bits_per_pixel', c_int),
    ('scanline_pad', c_int),
  ]

#/*
# * Data structure for setting window attributes.
# */
#~ typedef struct {
    #~ Pixmap background_pixmap;  /* background or None or ParentRelative */
    #~ unsigned long background_pixel;  /* background pixel */
    #~ Pixmap border_pixmap;  /* border of the window */
    #~ unsigned long border_pixel;  /* border pixel value */
    #~ int bit_gravity;    /* one of bit gravity values */
    #~ int win_gravity;    /* one of the window gravity values */
    #~ int backing_store;    /* NotUseful, WhenMapped, Always */
    #~ unsigned long backing_planes;/* planes to be preseved if possible */
    #~ unsigned long backing_pixel;/* value to use in restoring planes */
    #~ Bool save_under;    /* should bits under be saved? (popups) */
    #~ long event_mask;    /* set of events that should be saved */
    #~ long do_not_propagate_mask;  /* set of events that should not propagate */
    #~ Bool override_redirect;  /* boolean value for override-redirect */
    #~ Colormap colormap;    /* color map to be associated with window */
    #~ Cursor cursor;    /* cursor to be displayed (or None) */
#~ } XSetWindowAttributes;
class XSetWindowAttributes(Structure):
  _fields_ = [
    ('background_pixmap', Pixmap),
    ('background_pixel', c_ulong),
    ('border_pixmap', Pixmap),
    ('border_pixel', c_ulong),
    ('bit_gravity', c_int),
    ('win_gravity', c_int),
    ('backing_store', c_int),
    ('backing_planes', c_ulong),
    ('backing_pixel', c_ulong),
    ('save_under', Bool),
    ('event_mask', c_long),
    ('do_not_propagate_mask', c_long),
    ('override_redirect', Bool),
    ('colormap', Colormap),
    ('cursor', Cursor),
  ]

#~ typedef struct {
    #~ int x, y;      /* location of window */
    #~ int width, height;    /* width and height of window */
    #~ int border_width;    /* border width of window */
    #~ int depth;            /* depth of window */
    #~ Visual *visual;    /* the associated visual structure */
    #~ Window root;          /* root of screen containing window */
#~ #if defined(__cplusplus) || defined(c_plusplus)
    #~ int c_class;    /* C++ InputOutput, InputOnly*/
#~ #else
    #~ int class;      /* InputOutput, InputOnly*/
#~ #endif
    #~ int bit_gravity;    /* one of bit gravity values */
    #~ int win_gravity;    /* one of the window gravity values */
    #~ int backing_store;    /* NotUseful, WhenMapped, Always */
    #~ unsigned long backing_planes;/* planes to be preserved if possible */
    #~ unsigned long backing_pixel;/* value to be used when restoring planes */
    #~ Bool save_under;    /* boolean, should bits under be saved? */
    #~ Colormap colormap;    /* color map to be associated with window */
    #~ Bool map_installed;    /* boolean, is color map currently installed*/
    #~ int map_state;    /* IsUnmapped, IsUnviewable, IsViewable */
    #~ long all_event_masks;  /* set of events all people have interest in*/
    #~ long your_event_mask;  /* my event mask */
    #~ long do_not_propagate_mask; /* set of events that should not propagate */
    #~ Bool override_redirect;  /* boolean value for override-redirect */
    #~ Screen *screen;    /* back pointer to correct screen */
#~ } XWindowAttributes;
class XWindowAttributes(Structure):
  _fields_ = [
    ('x', c_int),
    ('y', c_int),
    ('width', c_int),
    ('height', c_int),
    ('border_width', c_int),
    ('depth', c_int),
    ('visual', POINTER(Visual)),
    ('root', Window),
    ('c_class', c_int),
    ('bit_gravity', c_int),
    ('win_gravity', c_int),
    ('backing_store', c_int),
    ('backing_planes', c_ulong),
    ('backing_pixel', c_ulong),
    ('save_under', Bool),
    ('colormap', Colormap),
    ('map_installed', Bool),
    ('map_state', c_int),
    ('all_event_masks', c_long),
    ('your_event_mask', c_long),
    ('do_not_propagate_mask', c_long),
    ('override_redirect', Bool),
    ('screen', POINTER(Screen)),
  ]

#/*
# * Data structure for host setting; getting routines.
# *
# */

#~ typedef struct {
  #~ int family;    /* for example FamilyInternet */
  #~ int length;    /* length of address, in bytes */
  #~ char *address;    /* pointer to where to find the bytes */
#~ } XHostAddress;
class XHostAddress(Structure):
  _fields_ = [
    ('family', c_int),
    ('length', c_int),
    ('address', c_char_p),
  ]

#/*
# * Data structure for ServerFamilyInterpreted addresses in host routines
# */
#~ typedef struct {
  #~ int typelength;    /* length of type string, in bytes */
  #~ int valuelength;  /* length of value string, in bytes */
  #~ char *type;    /* pointer to where to find the type string */
  #~ char *value;    /* pointer to where to find the address */
#~ } XServerInterpretedAddress;
class XServerInterpretedAddress(Structure):
  _fields_ = [
    ('typelength', c_int),
    ('valuelength', c_int),
    ('type', c_char_p),
    ('value', c_char_p),
  ]

#/*
# * Data structure for "image" data, used by image manipulation routines.
# */
#~ typedef struct _XImage {
    #~ int width, height;    /* size of image */
    #~ int xoffset;    /* number of pixels offset in X direction */
    #~ int format;      /* XYBitmap, XYPixmap, ZPixmap */
    #~ char *data;      /* pointer to image data */
    #~ int byte_order;    /* data byte order, LSBFirst, MSBFirst */
    #~ int bitmap_unit;    /* quant. of scanline 8, 16, 32 */
    #~ int bitmap_bit_order;  /* LSBFirst, MSBFirst */
    #~ int bitmap_pad;    /* 8, 16, 32 either XY or ZPixmap */
    #~ int depth;      /* depth of image */
    #~ int bytes_per_line;    /* accelarator to next line */
    #~ int bits_per_pixel;    /* bits per pixel (ZPixmap) */
    #~ unsigned long red_mask;  /* bits in z arrangment */
    #~ unsigned long green_mask;
    #~ unsigned long blue_mask;
    #~ XPointer obdata;    /* hook for the object routines to hang on */
    #~ struct funcs {    /* image manipulation routines */
  #~ struct _XImage *(*create_image)(
    #~ struct _XDisplay* /* display */,
    #~ Visual*    /* visual */,
    #~ unsigned int  /* depth */,
    #~ int    /* format */,
    #~ int    /* offset */,
    #~ char*    /* data */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ int    /* bitmap_pad */,
    #~ int    /* bytes_per_line */);
  #~ int (*destroy_image)        (struct _XImage *);
  #~ unsigned long (*get_pixel)  (struct _XImage *, int, int);
  #~ int (*put_pixel)            (struct _XImage *, int, int, unsigned long);
  #~ struct _XImage *(*sub_image)(struct _XImage *, int, int, unsigned int, unsigned int);
  #~ int (*add_pixel)            (struct _XImage *, long);
  #~ } f;
#~ } XImage;
class funcs(Structure):
  _fields_ = [
    ('create_image', c_void_p),
    ('destroy_image', c_void_p),
    ('get_pixel', c_void_p),
    ('put_pixel', c_void_p),
    ('sub_image', c_void_p),
    ('add_pixel', c_void_p),
  ]

class _XImage(Structure): pass
_XImage._fields_ = [
  ('width', c_int),
  ('height', c_int),
  ('xoffset', c_int),
  ('format', c_int),
  ('data', c_char_p),
  ('byte_order', c_int),
  ('bitmap_unit', c_int),
  ('bitmap_bit_order', c_int),
  ('bitmap_pad', c_int),
  ('depth', c_int),
  ('bytes_per_line', c_int),
  ('bits_per_pixel', c_int),
  ('red_mask', c_ulong),
  ('green_mask', c_ulong),
  ('blue_mask', c_ulong),
  ('obdata', XPointer),
  ('f', funcs),
]
XImage = _XImage

#/*
# * Data structure for XReconfigureWindow
# */
#~ typedef struct {
    #~ int x, y;
    #~ int width, height;
    #~ int border_width;
    #~ Window sibling;
    #~ int stack_mode;
#~ } XWindowChanges;
class XWindowChanges(Structure):
  _fields_ = [
    ('x', c_int),
    ('y', c_int),
    ('width', c_int),
    ('height', c_int),
    ('border_width', c_int),
    ('sibling', Window),
    ('stack_mode', c_int),
  ]

#/*
# * Data structure used by color operations
# */
#~ typedef struct {
  #~ unsigned long pixel;
  #~ unsigned short red, green, blue;
  #~ char flags;  /* do_red, do_green, do_blue */
  #~ char pad;
#~ } XColor;
class XColor(Structure):
  _fields_ = [
    ('pixel', c_ulong),
    ('red', c_ushort),
    ('green', c_ushort),
    ('blue', c_ushort),
    ('flags', c_byte),
    ('pad', c_byte),
  ]

#/*
# * Data structures for graphics operations.  On most machines, these are
# * congruent with the wire protocol structures, so reformatting the data
# * can be avoided on these architectures.
# */
#~ typedef struct {
    #~ short x1, y1, x2, y2;
#~ } XSegment;
class XSegment(Structure):
  _fields_ = [
    ('x1', c_short),
    ('y1', c_short),
    ('x2', c_short),
    ('y2', c_short),
  ]

#~ typedef struct {
    #~ short x, y;
#~ } XPoint;
class XPoint(Structure):
  _fields_ = [
    ('x', c_short),
    ('y', c_short),
  ]

#~ typedef struct {
    #~ short x, y;
    #~ unsigned short width, height;
#~ } XRectangle;
class XRectangle(Structure):
  _fields_ = [
    ('x', c_short),
    ('y', c_short),
    ('width', c_ushort),
    ('height', c_ushort),
  ]

#~ typedef struct {
    #~ short x, y;
    #~ unsigned short width, height;
    #~ short angle1, angle2;
#~ } XArc;
class XArc(Structure):
  _fields_ = [
    ('x', c_short),
    ('y', c_short),
    ('width', c_ushort),
    ('height', c_ushort),
    ('angle1', c_short),
    ('angle2', c_short),
  ]

#/* Data structure for XChangeKeyboardControl */

#~ typedef struct {
        #~ int key_click_percent;
        #~ int bell_percent;
        #~ int bell_pitch;
        #~ int bell_duration;
        #~ int led;
        #~ int led_mode;
        #~ int key;
        #~ int auto_repeat_mode;   /* On, Off, Default */
#~ } XKeyboardControl;
class XKeyboardControl(Structure):
  _fields_ = [
    ('key_click_percent', c_int),
    ('bell_percent', c_int),
    ('bell_pitch', c_int),
    ('bell_duration', c_int),
    ('led', c_int),
    ('led_mode', c_int),
    ('key', c_int),
    ('auto_repeat_mode', c_int),
  ]

#/* Data structure for XGetKeyboardControl */

#~ typedef struct {
        #~ int key_click_percent;
  #~ int bell_percent;
  #~ unsigned int bell_pitch, bell_duration;
  #~ unsigned long led_mask;
  #~ int global_auto_repeat;
  #~ char auto_repeats[32];
#~ } XKeyboardState;
class XKeyboardState(Structure):
  _fields_ = [
    ('key_click_percent', c_int),
    ('bell_percent', c_int),
    ('bell_pitch', c_uint),
    ('bell_duration', c_uint),
    ('led_mask', c_ulong),
    ('global_auto_repeat', c_int),
    ('auto_repeats', c_char * 32),
  ]

#/* Data structure for XGetMotionEvents.  */

#~ typedef struct {
        #~ Time time;
  #~ short x, y;
#~ } XTimeCoord;
class XTimeCoord(Structure):
  _fields_ = [
    ('time', Time),
    ('x', c_short),
    ('y', c_short),
  ]

#/* Data structure for X{Set,Get}ModifierMapping */

#~ typedef struct {
   #~ int max_keypermod;  /* The server's max # of keys per modifier */
   #~ KeyCode *modifiermap;  /* An 8 by max_keypermod array of modifiers */
#~ } XModifierKeymap;
class XModifierKeymap(Structure):
  _fields_ = [
    ('max_keypermod', c_int),
    ('modifiermap', POINTER(KeyCode)),
  ]

#/*
# * Display datatype maintaining display specific data.
# * The contents of this structure are implementation dependent.
# * A Display should be treated as opaque by application code.
# */
#ifndef XLIB_ILLEGAL_ACCESS
#~ typedef struct _XDisplay Display;
#endif

#~ struct _XPrivate;    /* Forward declare before use for C++ */
class _XPrivate(Structure): pass

#~ struct _XrmHashBucketRec;
class _XrmHashBucketRec(Structure): pass

#~ typedef struct
#~ #ifdef XLIB_ILLEGAL_ACCESS
#~ _XDisplay
#~ #endif
#~ {
  #~ XExtData *ext_data;  /* hook for extension to hang data */
  #~ struct _XPrivate *private1;
  #~ int fd;      /* Network socket. */
  #~ int private2;
  #~ int proto_major_version;/* major version of server's X protocol */
  #~ int proto_minor_version;/* minor version of servers X protocol */
  #~ char *vendor;    /* vendor of the server hardware */
        #~ XID private3;
  #~ XID private4;
  #~ XID private5;
  #~ int private6;
  #~ XID (*resource_alloc)(  /* allocator function */
    #~ struct _XDisplay*
  #~ );
  #~ int byte_order;    /* screen byte order, LSBFirst, MSBFirst */
  #~ int bitmap_unit;  /* padding and data requirements */
  #~ int bitmap_pad;    /* padding requirements on bitmaps */
  #~ int bitmap_bit_order;  /* LeastSignificant or MostSignificant */
  #~ int nformats;    /* number of pixmap formats in list */
  #~ ScreenFormat *pixmap_format;  /* pixmap format list */
  #~ int private8;
  #~ int release;    /* release of the server */
  #~ struct _XPrivate *private9, *private10;
  #~ int qlen;    /* Length of input event queue */
  #~ unsigned long last_request_read; /* seq number of last event read */
  #~ unsigned long request;  /* sequence number of last request. */
  #~ XPointer private11;
  #~ XPointer private12;
  #~ XPointer private13;
  #~ XPointer private14;
  #~ unsigned max_request_size; /* maximum number 32 bit words in request*/
  #~ struct _XrmHashBucketRec *db;
  #~ int (*private15)(
    #~ struct _XDisplay*
    #~ );
  #~ char *display_name;  /* "host:display" string used on this connect*/
  #~ int default_screen;  /* default screen for operations */
  #~ int nscreens;    /* number of screens on this server*/
  #~ Screen *screens;  /* pointer to list of screens */
  #~ unsigned long motion_buffer;  /* size of motion buffer */
  #~ unsigned long private16;
  #~ int min_keycode;  /* minimum defined keycode */
  #~ int max_keycode;  /* maximum defined keycode */
  #~ XPointer private17;
  #~ XPointer private18;
  #~ int private19;
  #~ char *xdefaults;  /* contents of defaults from server */
  #~ /* there is more to this structure, but it is private to Xlib */
#~ }
#~ #ifdef XLIB_ILLEGAL_ACCESS
#~ Display,
#~ #endif
#~ *_XPrivDisplay;
_XDisplay._fields_ = [
  ('ext_data', POINTER(XExtData)),
  ('private1', POINTER(_XPrivate)),
  ('fd', c_int),
  ('private2', c_int),
  ('proto_major_version', c_int),
  ('proto_minor_version', c_int),
  ('vendor', c_char_p),
  ('private3', XID),
  ('private4', XID),
  ('private5', XID),
  ('private6', c_int),
  ('resource_alloc', c_void_p),
  ('byte_order', c_int),
  ('bitmap_unit', c_int),
  ('bitmap_pad', c_int),
  ('bitmap_bit_order', c_int),
  ('nformats', c_int),
  ('pixmap_format', POINTER(ScreenFormat)),
  ('private8', c_int),
  ('release', c_int),
  ('private9', POINTER(_XPrivate)),
  ('private10', POINTER(_XPrivate)),
  ('qlen', c_int),
  ('last_request_read', c_ulong),
  ('request', c_ulong),
  ('private11', XPointer),
  ('private12', XPointer),
  ('private13', XPointer),
  ('private14', XPointer),
  ('max_request_size', c_uint),
  ('db', POINTER(_XrmHashBucketRec)),
  ('private15', c_void_p),
  ('display_name', c_char_p),
  ('default_screen', c_int),
  ('nscreens', c_int),
  ('screens', POINTER(Screen)),
  ('motion_buffer', c_ulong),
  ('private16', c_ulong),
  ('min_keycode', c_int),
  ('max_keycode', c_int),
  ('private17', XPointer),
  ('private18', XPointer),
  ('private19', c_int),
  ('xdefaults', c_char_p),
]
Display = _XDisplay
_XPrivDisplay = POINTER(_XDisplay)

#undef _XEVENT_
#ifndef _XEVENT_
#/*
# * Definitions of specific events.
# */
#~ typedef struct {
  #~ int type;    /* of event */
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;          /* "event" window it is reported relative to */
  #~ Window root;          /* root window that the event occurred on */
  #~ Window subwindow;  /* child window */
  #~ Time time;    /* milliseconds */
  #~ int x, y;    /* pointer x, y coordinates in event window */
  #~ int x_root, y_root;  /* coordinates relative to root */
  #~ unsigned int state;  /* key or button mask */
  #~ unsigned int keycode;  /* detail */
  #~ Bool same_screen;  /* same screen flag */
#~ } XKeyEvent;
#~ typedef XKeyEvent XKeyPressedEvent;
#~ typedef XKeyEvent XKeyReleasedEvent;
class XKeyEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('root', Window),
    ('subwindow', Window),
    ('time', Time),
    ('x', c_int),
    ('y', c_int),
    ('x_root', c_int),
    ('y_root', c_int),
    ('state', c_uint),
    ('keycode', c_uint),
    ('same_screen', Bool),
  ]
XKeyPressedEvent = XKeyEvent
XKeyReleasedEvent = XKeyEvent

#~ typedef struct {
  #~ int type;    /* of event */
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;          /* "event" window it is reported relative to */
  #~ Window root;          /* root window that the event occurred on */
  #~ Window subwindow;  /* child window */
  #~ Time time;    /* milliseconds */
  #~ int x, y;    /* pointer x, y coordinates in event window */
  #~ int x_root, y_root;  /* coordinates relative to root */
  #~ unsigned int state;  /* key or button mask */
  #~ unsigned int button;  /* detail */
  #~ Bool same_screen;  /* same screen flag */
#~ } XButtonEvent;
#~ typedef XButtonEvent XButtonPressedEvent;
#~ typedef XButtonEvent XButtonReleasedEvent;
class XButtonEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('root', Window),
    ('subwindow', Window),
    ('time', Time),
    ('x', c_int),
    ('y', c_int),
    ('x_root', c_int),
    ('y_root', c_int),
    ('state', c_uint),
    ('button', c_uint),
    ('same_screen', Bool),
  ]
XButtonPressedEvent = XButtonEvent
XButtonReleasedEvent = XButtonEvent

#~ typedef struct {
  #~ int type;    /* of event */
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;          /* "event" window reported relative to */
  #~ Window root;          /* root window that the event occurred on */
  #~ Window subwindow;  /* child window */
  #~ Time time;    /* milliseconds */
  #~ int x, y;    /* pointer x, y coordinates in event window */
  #~ int x_root, y_root;  /* coordinates relative to root */
  #~ unsigned int state;  /* key or button mask */
  #~ char is_hint;    /* detail */
  #~ Bool same_screen;  /* same screen flag */
#~ } XMotionEvent;
#~ typedef XMotionEvent XPointerMovedEvent;
class XMotionEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('root', Window),
    ('subwindow', Window),
    ('time', Time),
    ('x', c_int),
    ('y', c_int),
    ('x_root', c_int),
    ('y_root', c_int),
    ('state', c_uint),
    ('is_hint', c_char),
    ('same_screen', Bool),
  ]
XPointerMovedEvent = XMotionEvent

#~ typedef struct {
  #~ int type;    /* of event */
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;          /* "event" window reported relative to */
  #~ Window root;          /* root window that the event occurred on */
  #~ Window subwindow;  /* child window */
  #~ Time time;    /* milliseconds */
  #~ int x, y;    /* pointer x, y coordinates in event window */
  #~ int x_root, y_root;  /* coordinates relative to root */
  #~ int mode;    /* NotifyNormal, NotifyGrab, NotifyUngrab */
  #~ int detail;
  #~ /*
   #~ * NotifyAncestor, NotifyVirtual, NotifyInferior,
   #~ * NotifyNonlinear,NotifyNonlinearVirtual
   #~ */
  #~ Bool same_screen;  /* same screen flag */
  #~ Bool focus;    /* boolean focus */
  #~ unsigned int state;  /* key or button mask */
#~ } XCrossingEvent;
#~ typedef XCrossingEvent XEnterWindowEvent;
#~ typedef XCrossingEvent XLeaveWindowEvent;
class XCrossingEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('root', Window),
    ('subwindow', Window),
    ('time', Time),
    ('x', c_int),
    ('y', c_int),
    ('x_root', c_int),
    ('y_root', c_int),
    ('mode', c_int),
    ('detail', c_int),
    ('same_screen', Bool),
    ('focus', Bool),
    ('state', c_uint),
  ]
XEnterWindowEvent = XCrossingEvent
XLeaveWindowEvent = XCrossingEvent

#~ typedef struct {
  #~ int type;    /* FocusIn or FocusOut */
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;    /* window of event */
  #~ int mode;    /* NotifyNormal, NotifyWhileGrabbed,
           #~ NotifyGrab, NotifyUngrab */
  #~ int detail;
  #~ /*
   #~ * NotifyAncestor, NotifyVirtual, NotifyInferior,
   #~ * NotifyNonlinear,NotifyNonlinearVirtual, NotifyPointer,
   #~ * NotifyPointerRoot, NotifyDetailNone
   #~ */
#~ } XFocusChangeEvent;
#~ typedef XFocusChangeEvent XFocusInEvent;
#~ typedef XFocusChangeEvent XFocusOutEvent;
class XFocusChangeEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('mode', c_int),
    ('detail', c_int),
  ]
XFocusInEvent = XFocusChangeEvent
XFocusOutEvent = XFocusChangeEvent

#/* generated on EnterWindow and FocusIn  when KeyMapState selected */
#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;
  #~ char key_vector[32];
#~ } XKeymapEvent;
class XKeymapEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('key_vector', c_char * 32),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;
  #~ int x, y;
  #~ int width, height;
  #~ int count;    /* if non-zero, at least this many more */
#~ } XExposeEvent;
class XExposeEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('x', c_int),
    ('y', c_int),
    ('width', c_int),
    ('height', c_int),
    ('count', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Drawable drawable;
  #~ int x, y;
  #~ int width, height;
  #~ int count;    /* if non-zero, at least this many more */
  #~ int major_code;    /* core is CopyArea or CopyPlane */
  #~ int minor_code;    /* not defined in the core */
#~ } XGraphicsExposeEvent;
class XGraphicsExposeEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('drawable', Drawable),
    ('x', c_int),
    ('y', c_int),
    ('width', c_int),
    ('height', c_int),
    ('count', c_int),
    ('major_code', c_int),
    ('minor_code', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Drawable drawable;
  #~ int major_code;    /* core is CopyArea or CopyPlane */
  #~ int minor_code;    /* not defined in the core */
#~ } XNoExposeEvent;
class XNoExposeEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('drawable', Drawable),
    ('major_code', c_int),
    ('minor_code', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;
  #~ int state;    /* Visibility state */
#~ } XVisibilityEvent;
class XVisibilityEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('state', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window parent;    /* parent of the window */
  #~ Window window;    /* window id of window created */
  #~ int x, y;    /* window location */
  #~ int width, height;  /* size of window */
  #~ int border_width;  /* border width */
  #~ Bool override_redirect;  /* creation should be overridden */
#~ } XCreateWindowEvent;
class XCreateWindowEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('parent', Window),
    ('window', Window),
    ('x', c_int),
    ('y', c_int),
    ('width', c_int),
    ('height', c_int),
    ('border_width', c_int),
    ('override_redirect', Bool),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window event;
  #~ Window window;
#~ } XDestroyWindowEvent;
class XDestroyWindowEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('event', Window),
    ('window', Window),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window event;
  #~ Window window;
  #~ Bool from_configure;
#~ } XUnmapEvent;
class XUnmapEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('event', Window),
    ('window', Window),
    ('from_configure', Bool),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window event;
  #~ Window window;
  #~ Bool override_redirect;  /* boolean, is override set... */
#~ } XMapEvent;
class XMapEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('event', Window),
    ('window', Window),
    ('override_redirect', Bool),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window parent;
  #~ Window window;
#~ } XMapRequestEvent;
class XMapRequestEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('event', Window),
    ('window', Window),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window event;
  #~ Window window;
  #~ Window parent;
  #~ int x, y;
  #~ Bool override_redirect;
#~ } XReparentEvent;
class XReparentEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('event', Window),
    ('window', Window),
    ('parent', Window),
    ('x', c_int),
    ('y', c_int),
    ('override_redirect', Bool),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window event;
  #~ Window window;
  #~ int x, y;
  #~ int width, height;
  #~ int border_width;
  #~ Window above;
  #~ Bool override_redirect;
#~ } XConfigureEvent;
class XConfigureEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('event', Window),
    ('window', Window),
    ('x', c_int),
    ('y', c_int),
    ('width', c_int),
    ('height', c_int),
    ('border_width', c_int),
    ('above', Window),
    ('override_redirect', Bool),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window event;
  #~ Window window;
  #~ int x, y;
#~ } XGravityEvent;
class XGravityEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('event', Window),
    ('window', Window),
    ('x', c_int),
    ('y', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;
  #~ int width, height;
#~ } XResizeRequestEvent;
class XResizeRequestEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('width', c_int),
    ('height', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window parent;
  #~ Window window;
  #~ int x, y;
  #~ int width, height;
  #~ int border_width;
  #~ Window above;
  #~ int detail;    /* Above, Below, TopIf, BottomIf, Opposite */
  #~ unsigned long value_mask;
#~ } XConfigureRequestEvent;
class XConfigureRequestEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('parent', Window),
    ('window', Window),
    ('x', c_int),
    ('y', c_int),
    ('width', c_int),
    ('height', c_int),
    ('border_width', c_int),
    ('above', Window),
    ('detail', c_int),
    ('value_mask', c_ulong),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window event;
  #~ Window window;
  #~ int place;    /* PlaceOnTop, PlaceOnBottom */
#~ } XCirculateEvent;
class XCirculateEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('event', Window),
    ('window', Window),
    ('place', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window parent;
  #~ Window window;
  #~ int place;    /* PlaceOnTop, PlaceOnBottom */
#~ } XCirculateRequestEvent;
class XCirculateRequestEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('parent', Window),
    ('window', Window),
    ('place', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;
  #~ Atom atom;
  #~ Time time;
  #~ int state;    /* NewValue, Deleted */
#~ } XPropertyEvent;
class XPropertyEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('atom', Atom),
    ('time', Time),
    ('state', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;
  #~ Atom selection;
  #~ Time time;
#~ } XSelectionClearEvent;
class XSelectionClearEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('selection', Atom),
    ('time', Time),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window owner;
  #~ Window requestor;
  #~ Atom selection;
  #~ Atom target;
  #~ Atom property;
  #~ Time time;
#~ } XSelectionRequestEvent;
class XSelectionRequestEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('owner', Window),
    ('requestor', Window),
    ('selection', Atom),
    ('target', Atom),
    ('property', Atom),
    ('time', Time),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window requestor;
  #~ Atom selection;
  #~ Atom target;
  #~ Atom property;    /* ATOM or None */
  #~ Time time;
#~ } XSelectionEvent;
class XSelectionEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('requestor', Window),
    ('selection', Atom),
    ('target', Atom),
    ('property', Atom),
    ('time', Time),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;
  #~ Colormap colormap;  /* COLORMAP or None */
#~ #if defined(__cplusplus) || defined(c_plusplus)
  #~ Bool c_new;    /* C++ */
#~ #else
  #~ Bool new;
#~ #endif
  #~ int state;    /* ColormapInstalled, ColormapUninstalled */
#~ } XColormapEvent;
class XColormapEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('colormap', Colormap),
    ('c_new', Bool),
    ('state', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;
  #~ Atom message_type;
  #~ int format;
  #~ union {
    #~ char b[20];
    #~ short s[10];
    #~ long l[5];
    #~ } data;
#~ } XClientMessageEvent;
class _U(Union):
  _fields_ = [
    ('b', c_char * 20),
    ('s', c_short * 10),
    ('l', c_long * 5),
  ]

class XClientMessageEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('message_type', Atom),
    ('format', c_int),
    ('data', _U),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;  /* Display the event was read from */
  #~ Window window;    /* unused */
  #~ int request;    /* one of MappingModifier, MappingKeyboard,
           #~ MappingPointer */
  #~ int first_keycode;  /* first keycode */
  #~ int count;    /* defines range of change w. first_keycode*/
#~ } XMappingEvent;
class XMappingEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
    ('request', c_int),
    ('first_keycode', c_int),
    ('count', c_int),
  ]

#~ typedef struct {
  #~ int type;
  #~ Display *display;  /* Display the event was read from */
  #~ XID resourceid;    /* resource id */
  #~ unsigned long serial;  /* serial number of failed request */
  #~ unsigned char error_code;  /* error code of failed request */
  #~ unsigned char request_code;  /* Major op-code of failed request */
  #~ unsigned char minor_code;  /* Minor op-code of failed request */
#~ } XErrorEvent;
class XErrorEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('display', POINTER(Display)),
    ('resourceid', XID),
    ('serial', c_ulong),
    ('error_code', c_ubyte),
    ('request_code', c_ubyte),
    ('minor_code', c_ubyte),
  ]

#~ typedef struct {
  #~ int type;
  #~ unsigned long serial;  /* # of last request processed by server */
  #~ Bool send_event;  /* true if this came from a SendEvent request */
  #~ Display *display;/* Display the event was read from */
  #~ Window window;  /* window on which event was requested in event mask */
#~ } XAnyEvent;
class XAnyEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('window', Window),
  ]


#/***************************************************************
# *
# * GenericEvent.  This event is the standard event for all newer extensions.
# */

#~ typedef struct
    #~ {
    #~ int            type;         /* of event. Always GenericEvent */
    #~ unsigned long  serial;       /* # of last request processed */
    #~ Bool           send_event;   /* true if from SendEvent request */
    #~ Display        *display;     /* Display the event was read from */
    #~ int            extension;    /* major opcode of extension that caused the event */
    #~ int            evtype;       /* actual event type. */
    #~ } XGenericEvent;
class XGenericEvent(Structure):
  _fields_ = [
    ('type', c_int),
    ('serial', c_ulong),
    ('send_event', Bool),
    ('display', POINTER(Display)),
    ('extension', c_int),
    ('evtype', c_int),
  ]

#/*
# * this union is defined so Xlib can always use the same sized
# * event structure internally, to avoid memory fragmentation.
# */
#~ typedef union _XEvent {
        #~ int type;    /* must not be changed; first element */
  #~ XAnyEvent xany;
  #~ XKeyEvent xkey;
  #~ XButtonEvent xbutton;
  #~ XMotionEvent xmotion;
  #~ XCrossingEvent xcrossing;
  #~ XFocusChangeEvent xfocus;
  #~ XExposeEvent xexpose;
  #~ XGraphicsExposeEvent xgraphicsexpose;
  #~ XNoExposeEvent xnoexpose;
  #~ XVisibilityEvent xvisibility;
  #~ XCreateWindowEvent xcreatewindow;
  #~ XDestroyWindowEvent xdestroywindow;
  #~ XUnmapEvent xunmap;
  #~ XMapEvent xmap;
  #~ XMapRequestEvent xmaprequest;
  #~ XReparentEvent xreparent;
  #~ XConfigureEvent xconfigure;
  #~ XGravityEvent xgravity;
  #~ XResizeRequestEvent xresizerequest;
  #~ XConfigureRequestEvent xconfigurerequest;
  #~ XCirculateEvent xcirculate;
  #~ XCirculateRequestEvent xcirculaterequest;
  #~ XPropertyEvent xproperty;
  #~ XSelectionClearEvent xselectionclear;
  #~ XSelectionRequestEvent xselectionrequest;
  #~ XSelectionEvent xselection;
  #~ XColormapEvent xcolormap;
  #~ XClientMessageEvent xclient;
  #~ XMappingEvent xmapping;
  #~ XErrorEvent xerror;
  #~ XKeymapEvent xkeymap;
  #~ long pad[24];
#~ } XEvent;
#endif
class _XEvent(Union): pass
_XEvent._fields_ = [
  ('type', c_int),
  ('xany', XAnyEvent),
  ('xkey', XKeyEvent),
  ('xbutton', XButtonEvent),
  ('xmotion', XMotionEvent),
  ('xcrossing', XCrossingEvent),
  ('xfocus', XFocusChangeEvent),
  ('xexpose', XExposeEvent),
  ('xgraphicsexpose', XGraphicsExposeEvent),
  ('xnoexpose', XNoExposeEvent),
  ('xvisibility', XVisibilityEvent),
  ('xcreatewindow', XCreateWindowEvent),
  ('xdestroywindow', XDestroyWindowEvent),
  ('xunmap', XUnmapEvent),
  ('xmap', XMapEvent),
  ('xmaprequest', XMapRequestEvent),
  ('xreparent', XReparentEvent),
  ('xconfigure', XConfigureEvent),
  ('xgravity', XGravityEvent),
  ('xresizerequest', XResizeRequestEvent),
  ('xconfigurerequest', XConfigureRequestEvent),
  ('xcirculate', XCirculateEvent),
  ('xcirculaterequest', XCirculateRequestEvent),
  ('xproperty', XPropertyEvent),
  ('xselectionclear', XSelectionClearEvent),
  ('xselectionrequest', XSelectionRequestEvent),
  ('xselection', XSelectionEvent),
  ('xcolormap', XColormapEvent),
  ('xclient', XClientMessageEvent),
  ('xmapping', XMappingEvent),
  ('xerror', XErrorEvent),
  ('xkeymap', XKeymapEvent),
  ('pad', c_long * 24),
]
XEvent = _XEvent

#define XAllocID(dpy) ((*((_XPrivDisplay)dpy)->resource_alloc)((dpy)))

#/*
# * per character font metric information.
# */
#~ typedef struct {
    #~ short  lbearing;  /* origin to left edge of raster */
    #~ short  rbearing;  /* origin to right edge of raster */
    #~ short  width;    /* advance to next char's origin */
    #~ short  ascent;    /* baseline to top edge of raster */
    #~ short  descent;  /* baseline to bottom edge of raster */
    #~ unsigned short attributes;  /* per char flags (not predefined) */
#~ } XCharStruct;
class XCharStruct(Structure):
   _fields_ = [
    ('lbearing', c_short),
    ('rbearing', c_short),
    ('width', c_short),
    ('ascent', c_short),
    ('descent', c_short),
    ('attributes', c_ushort),
   ]

#/*
# * To allow arbitrary information with fonts, there are additional properties
# * returned.
# */
#~ typedef struct {
    #~ Atom name;
    #~ unsigned long card32;
#~ } XFontProp;
class XFontProp(Structure):
   _fields_ = [
    ('name', Atom),
    ('card32', c_ulong),
   ]

#~ typedef struct {
    #~ XExtData  *ext_data;  /* hook for extension to hang data */
    #~ Font        fid;            /* Font id for this font */
    #~ unsigned  direction;  /* hint about direction the font is painted */
    #~ unsigned  min_char_or_byte2;/* first character */
    #~ unsigned  max_char_or_byte2;/* last character */
    #~ unsigned  min_byte1;  /* first row that exists */
    #~ unsigned  max_byte1;  /* last row that exists */
    #~ Bool  all_chars_exist;/* flag if all characters have non-zero size*/
    #~ unsigned  default_char;  /* char to print for undefined character */
    #~ int         n_properties;   /* how many properties there are */
    #~ XFontProp  *properties;  /* pointer to array of additional properties*/
    #~ XCharStruct  min_bounds;  /* minimum bounds over all existing char*/
    #~ XCharStruct  max_bounds;  /* maximum bounds over all existing char*/
    #~ XCharStruct  *per_char;  /* first_char to last_char information */
    #~ int    ascent;    /* log. extent above baseline for spacing */
    #~ int    descent;  /* log. descent below baseline for spacing */
#~ } XFontStruct;
class XFontStruct(Structure):
   _fields_ = [
    ('ext_data', POINTER(XExtData)),
    ('fid', Font),
    ('direction', c_uint),
    ('min_char_or_byte2', c_uint),
    ('max_char_or_byte2', c_uint),
    ('min_byte1', c_uint),
    ('max_byte1', c_uint),
    ('all_chars_exist', Bool),
    ('default_char', c_uint),
    ('n_properties', c_int),
    ('properties', POINTER(XFontProp)),
    ('min_bounds', XCharStruct),
    ('max_bounds', XCharStruct),
    ('per_char', POINTER(XCharStruct)),
    ('ascent', c_int),
    ('descent', c_int),
   ]

#/*
# * PolyText routines take these as arguments.
# */
#~ typedef struct {
    #~ char *chars;    /* pointer to string */
    #~ int nchars;      /* number of characters */
    #~ int delta;      /* delta between strings */
    #~ Font font;      /* font to print it in, None don't change */
#~ } XTextItem;
class XTextItem(Structure):
   _fields_ = [
    ('chars', c_char_p),
    ('nchars', c_int),
    ('delta', c_int),
    ('font', Font),
   ]

#~ typedef struct {    /* normal 16 bit characters are two bytes */
    #~ unsigned char byte1;
    #~ unsigned char byte2;
#~ } XChar2b;
class XChar2b(Structure):
   _fields_ = [
    ('byte1', c_ubyte),
    ('byte2', c_ubyte),
   ]

#~ typedef struct {
    #~ XChar2b *chars;    /* two byte characters */
    #~ int nchars;      /* number of characters */
    #~ int delta;      /* delta between strings */
    #~ Font font;      /* font to print it in, None don't change */
#~ } XTextItem16;
class XTextItem16(Structure):
   _fields_ = [
    ('chars', POINTER(XChar2b)),
    ('nchars', c_int),
    ('delta', c_int),
    ('font', Font),
   ]

#~ typedef union { Display *display;
    #~ GC gc;
    #~ Visual *visual;
    #~ Screen *screen;
    #~ ScreenFormat *pixmap_format;
    #~ XFontStruct *font; } XEDataObject;
class XEDataObject(Union):
   _fields_ = [
    ('display', POINTER(Display)),
    ('gc', GC),
    ('visual', POINTER(Visual)),
    ('screen', POINTER(Screen)),
    ('pixmap_format', POINTER(ScreenFormat)),
    ('font', POINTER(XFontStruct)),
   ]

#~ typedef struct {
    #~ XRectangle      max_ink_extent;
    #~ XRectangle      max_logical_extent;
#~ } XFontSetExtents;
class XFontSetExtents(Structure):
   _fields_ = [
    ('max_ink_extent', XRectangle),
    ('max_logical_extent', XRectangle),
   ]

#/* unused:
#typedef void (*XOMProc)();
# */

#~ typedef struct _XOM *XOM;
class _XOM(Structure): pass
XOM = POINTER(_XOM)

#~ typedef struct _XOC *XOC, *XFontSet;
class _XOC(Structure): pass
XOC = POINTER(_XOC)
XFontSet = POINTER(_XOC)

#~ typedef struct {
    #~ char           *chars;
    #~ int             nchars;
    #~ int             delta;
    #~ XFontSet        font_set;
#~ } XmbTextItem;
class XmbTextItem(Structure):
   _fields_ = [
    ('chars', c_char_p),
    ('nchars', c_int),
    ('delta', c_int),
    ('font_set', XFontSet),
   ]

#~ typedef struct {
    #~ wchar_t        *chars;
    #~ int             nchars;
    #~ int             delta;
    #~ XFontSet        font_set;
#~ } XwcTextItem;
class XwcTextItem(Structure):
   _fields_ = [
    ('chars', c_wchar_p),
    ('nchars', c_int),
    ('delta', c_int),
    ('font_set', XFontSet),
   ]

XNRequiredCharSet = "requiredCharSet"
XNQueryOrientation = "queryOrientation"
XNBaseFontName = "baseFontName"
XNOMAutomatic = "omAutomatic"
XNMissingCharSet = "missingCharSet"
XNDefaultString = "defaultString"
XNOrientation = "orientation"
XNDirectionalDependentDrawing = "directionalDependentDrawing"
XNContextualDrawing = "contextualDrawing"
XNFontInfo = "fontInfo"

#~ typedef struct {
    #~ int charset_count;
    #~ char **charset_list;
#~ } XOMCharSetList;
class XOMCharSetList(Structure):
   _fields_ = [
    ('charset_count', c_int),
    ('charset_list', POINTER(c_char_p)),
   ]

#~ typedef enum {
    #~ XOMOrientation_LTR_TTB,
    #~ XOMOrientation_RTL_TTB,
    #~ XOMOrientation_TTB_LTR,
    #~ XOMOrientation_TTB_RTL,
    #~ XOMOrientation_Context
#~ } XOrientation;
XOrientation = c_int
(
  XOMOrientation_LTR_TTB,
  XOMOrientation_RTL_TTB,
  XOMOrientation_TTB_LTR,
  XOMOrientation_TTB_RTL,
  XOMOrientation_Context
) = map(c_int, xrange(5))

#~ typedef struct {
    #~ int num_orientation;
    #~ XOrientation *orientation;  /* Input Text description */
#~ } XOMOrientation;
class XOMOrientation(Structure):
   _fields_ = [
    ('num_orientation', c_int),
    ('orientation', POINTER(XOrientation)),
   ]

#~ typedef struct {
    #~ int num_font;
    #~ XFontStruct **font_struct_list;
    #~ char **font_name_list;
#~ } XOMFontInfo;
class XOMFontInfo(Structure):
   _fields_ = [
    ('num_font', c_int),
    ('font_struct_list', POINTER(POINTER(XFontStruct))),
    ('font_name_list', POINTER(c_char_p)),
   ]

#~ typedef struct _XIM *XIM;
class _XIM(Structure): pass
XIM = POINTER(_XIM)

#~ typedef struct _XIC *XIC;
class _XIC(Structure): pass
XIC = POINTER(_XIC)

#~ typedef void (*XIMProc)(
    #~ XIM,
    #~ XPointer,
    #~ XPointer
#~ );
XIMProc = c_void_p

#~ typedef Bool (*XICProc)(
    #~ XIC,
    #~ XPointer,
    #~ XPointer
#~ );
XICProc = c_void_p

#~ typedef void (*XIDProc)(
    #~ Display*,
    #~ XPointer,
    #~ XPointer
#~ );
XIDProc = c_void_p

#~ typedef unsigned long XIMStyle;
XIMStyle = c_ulong

#~ typedef struct {
    #~ unsigned short count_styles;
    #~ XIMStyle *supported_styles;
#~ } XIMStyles;
class XIMStyles(Structure):
   _fields_ = [
    ('count_styles', c_ushort),
    ('supported_styles', POINTER(XIMStyle)),
   ]

XIMPreeditArea    = 0x0001
XIMPreeditCallbacks  = 0x0002
XIMPreeditPosition  = 0x0004
XIMPreeditNothing  = 0x0008
XIMPreeditNone    = 0x0010
XIMStatusArea    = 0x0100
XIMStatusCallbacks  = 0x0200
XIMStatusNothing  = 0x0400
XIMStatusNone    = 0x0800

XNVaNestedList = "XNVaNestedList"
XNQueryInputStyle = "queryInputStyle"
XNClientWindow = "clientWindow"
XNInputStyle = "inputStyle"
XNFocusWindow = "focusWindow"
XNResourceName = "resourceName"
XNResourceClass = "resourceClass"
XNGeometryCallback = "geometryCallback"
XNDestroyCallback = "destroyCallback"
XNFilterEvents = "filterEvents"
XNPreeditStartCallback = "preeditStartCallback"
XNPreeditDoneCallback = "preeditDoneCallback"
XNPreeditDrawCallback = "preeditDrawCallback"
XNPreeditCaretCallback = "preeditCaretCallback"
XNPreeditStateNotifyCallback = "preeditStateNotifyCallback"
XNPreeditAttributes = "preeditAttributes"
XNStatusStartCallback = "statusStartCallback"
XNStatusDoneCallback = "statusDoneCallback"
XNStatusDrawCallback = "statusDrawCallback"
XNStatusAttributes = "statusAttributes"
XNArea = "area"
XNAreaNeeded = "areaNeeded"
XNSpotLocation = "spotLocation"
XNColormap = "colorMap"
XNStdColormap = "stdColorMap"
XNForeground = "foreground"
XNBackground = "background"
XNBackgroundPixmap = "backgroundPixmap"
XNFontSet = "fontSet"
XNLineSpace = "lineSpace"
XNCursor = "cursor"

XNQueryIMValuesList = "queryIMValuesList"
XNQueryICValuesList = "queryICValuesList"
XNVisiblePosition = "visiblePosition"
XNR6PreeditCallback = "r6PreeditCallback"
XNStringConversionCallback = "stringConversionCallback"
XNStringConversion = "stringConversion"
XNResetState = "resetState"
XNHotKey = "hotKey"
XNHotKeyState = "hotKeyState"
XNPreeditState = "preeditState"
XNSeparatorofNestedList = "separatorofNestedList"

XBufferOverflow  = -1
XLookupNone = 1
XLookupChars = 2
XLookupKeySym = 3
XLookupBoth = 4

#~ typedef void *XVaNestedList;
XVaNestedList = c_void_p

#~ typedef struct {
    #~ XPointer client_data;
    #~ XIMProc callback;
#~ } XIMCallback;
class XIMCallback(Structure):
   _fields_ = [
    ('client_data', XPointer),
    ('callback', XIMProc),
   ]

#~ typedef struct {
    #~ XPointer client_data;
    #~ XICProc callback;
#~ } XICCallback;
class XICCallback(Structure):
   _fields_ = [
    ('client_data', XPointer),
    ('callback', XICProc),
   ]

#~ typedef unsigned long XIMFeedback;
XIMFeedback = c_ulong

XIMReverse = 1
XIMUnderline = (1<<1)
XIMHighlight = (1<<2)
XIMPrimary = (1<<5)
XIMSecondary = (1<<6)
XIMTertiary  = (1<<7)
XIMVisibleToForward = (1<<8)
XIMVisibleToBackword = (1<<9)
XIMVisibleToCenter = (1<<10)

#~ typedef struct _XIMText {
    #~ unsigned short length;
    #~ XIMFeedback *feedback;
    #~ Bool encoding_is_wchar;
    #~ union {
  #~ char *multi_byte;
  #~ wchar_t *wide_char;
    #~ } string;
#~ } XIMText;
class _string(Union):
   _fields_ = [
    ('multi_byte', c_char_p),
    ('wide_char', c_wchar_p),
   ]

class _XIMText(Structure):
   _fields_ = [
    ('length', c_ushort),
    ('feedback', POINTER(XIMFeedback)),
    ('encoding_is_wchar', Bool),
    ('string', _string),
   ]
XIMText = _XIMText

#~ typedef  unsigned long   XIMPreeditState;
XIMPreeditState = c_ulong

XIMPreeditUnKnown = 0
XIMPreeditEnable = 1
XIMPreeditDisable = (1<<1)

#~ typedef  struct  _XIMPreeditStateNotifyCallbackStruct {
    #~ XIMPreeditState state;
#~ } XIMPreeditStateNotifyCallbackStruct;
class _XIMPreeditStateNotifyCallbackStruct(Structure):
   _fields_ = [
    ('state', XIMPreeditState),
   ]
XIMPreeditStateNotifyCallbackStruct = _XIMPreeditStateNotifyCallbackStruct

#~ typedef  unsigned long   XIMResetState;
XIMResetState = c_ulong

XIMInitialState  = 1
XIMPreserveState = (1<<1)

#~ typedef unsigned long XIMStringConversionFeedback;
XIMStringConversionFeedback = c_ulong

XIMStringConversionLeftEdge = (0x00000001)
XIMStringConversionRightEdge = (0x00000002)
XIMStringConversionTopEdge = (0x00000004)
XIMStringConversionBottomEdge = (0x00000008)
XIMStringConversionConcealed = (0x00000010)
XIMStringConversionWrapped = (0x00000020)

#~ typedef struct _XIMStringConversionText {
    #~ unsigned short length;
    #~ XIMStringConversionFeedback *feedback;
    #~ Bool encoding_is_wchar;
    #~ union {
  #~ char *mbs;
  #~ wchar_t *wcs;
    #~ } string;
#~ } XIMStringConversionText;
class _string(Union):
   _fields_ = [
    ('mbs', c_char_p),
    ('wcs', c_wchar_p),
   ]

class _XIMStringConversionText(Structure):
  _fields_ = [
    ('length', c_ushort),
    ('feedback', POINTER(XIMStringConversionFeedback)),
    ('encoding_is_wchar', Bool),
    ('string', _string),
  ]
XIMStringConversionText = _XIMStringConversionText

#~ typedef  unsigned short  XIMStringConversionPosition;
XIMStringConversionPosition = c_ushort

#~ typedef  unsigned short  XIMStringConversionType;
XIMStringConversionType = c_ushort

XIMStringConversionBuffer =(0x0001)
XIMStringConversionLine = (0x0002)
XIMStringConversionWord = (0x0003)
XIMStringConversionChar = (0x0004)

#~ typedef  unsigned short  XIMStringConversionOperation;
XIMStringConversionOperation = c_ushort

XIMStringConversionSubstitution = (0x0001)
XIMStringConversionRetrieval = (0x0002)

#~ typedef enum {
    #~ XIMForwardChar, XIMBackwardChar,
    #~ XIMForwardWord, XIMBackwardWord,
    #~ XIMCaretUp, XIMCaretDown,
    #~ XIMNextLine, XIMPreviousLine,
    #~ XIMLineStart, XIMLineEnd,
    #~ XIMAbsolutePosition,
    #~ XIMDontChange
#~ } XIMCaretDirection;
XIMCaretDirection = c_int
(
  XIMForwardChar,
  XIMBackwardChar,
  XIMForwardWord,
  XIMBackwardWord,
  XIMCaretUp,
  XIMCaretDown,
  XIMNextLine,
  XIMPreviousLine,
  XIMLineStart,
  XIMLineEnd,
  XIMAbsolutePosition,
  XIMDontChange
) = map(c_int, xrange(12))

#~ typedef struct _XIMStringConversionCallbackStruct {
    #~ XIMStringConversionPosition position;
    #~ XIMCaretDirection direction;
    #~ XIMStringConversionOperation operation;
    #~ unsigned short factor;
    #~ XIMStringConversionText *text;
#~ } XIMStringConversionCallbackStruct;
class _XIMStringConversionCallbackStruct(Structure):
  _fields_ = [
    ('position', XIMStringConversionPosition),
    ('direction', XIMCaretDirection),
    ('operation', XIMStringConversionOperation),
    ('factor', c_ushort),
    ('text', POINTER(XIMStringConversionText)),
  ]
XIMStringConversionCallbackStruct = _XIMStringConversionCallbackStruct

#~ typedef struct _XIMPreeditDrawCallbackStruct {
    #~ int caret;    /* Cursor offset within pre-edit string */
    #~ int chg_first;  /* Starting change position */
    #~ int chg_length;  /* Length of the change in character count */
    #~ XIMText *text;
#~ } XIMPreeditDrawCallbackStruct;
class _XIMPreeditDrawCallbackStruct(Structure):
  _fields_ = [
    ('caret', c_int),
    ('chg_first', c_int),
    ('chg_length', c_int),
    ('text', POINTER(XIMText)),
  ]
XIMPreeditDrawCallbackStruct = _XIMPreeditDrawCallbackStruct

#~ typedef enum {
    #~ XIMIsInvisible,  /* Disable caret feedback */
    #~ XIMIsPrimary,  /* UI defined caret feedback */
    #~ XIMIsSecondary  /* UI defined caret feedback */
#~ } XIMCaretStyle;
XIMCaretStyle = c_int
(
  XIMIsInvisible,
  XIMIsPrimary,
  XIMIsSecondary
) = map(c_int, xrange(3))

#~ typedef struct _XIMPreeditCaretCallbackStruct {
    #~ int position;     /* Caret offset within pre-edit string */
    #~ XIMCaretDirection direction; /* Caret moves direction */
    #~ XIMCaretStyle style;   /* Feedback of the caret */
#~ } XIMPreeditCaretCallbackStruct;
class _XIMPreeditCaretCallbackStruct(Structure):
  _fields_ = [
    ('position', c_int),
    ('direction', XIMCaretDirection),
    ('style', XIMCaretStyle),
  ]
XIMPreeditCaretCallbackStruct = _XIMPreeditCaretCallbackStruct

#~ typedef enum {
    #~ XIMTextType,
    #~ XIMBitmapType
#~ } XIMStatusDataType;
XIMStatusDataType = c_int
(
  XIMTextType,
  XIMBitmapType
) = map(c_int, xrange(2))


#~ typedef struct _XIMStatusDrawCallbackStruct {
    #~ XIMStatusDataType type;
    #~ union {
  #~ XIMText *text;
  #~ Pixmap  bitmap;
    #~ } data;
#~ } XIMStatusDrawCallbackStruct;
class _data(Union):
  _fields_ = [
    ('text', POINTER(XIMText)),
    ('bitmap', Pixmap),
  ]

class _XIMStatusDrawCallbackStruct(Structure):
  _fields_ = [
    ('type', XIMStatusDataType),
    ('data', _data),
  ]
XIMStatusDrawCallbackStruct = _XIMStatusDrawCallbackStruct

#~ typedef struct _XIMHotKeyTrigger {
    #~ KeySym   keysym;
    #~ int     modifier;
    #~ int     modifier_mask;
#~ } XIMHotKeyTrigger;
class _XIMHotKeyTrigger(Structure):
  _fields_ = [
    ('keysym', KeySym),
    ('modifier', c_int),
    ('modifier_mask', c_int),
  ]
XIMHotKeyTrigger = _XIMHotKeyTrigger

#~ typedef struct _XIMHotKeyTriggers {
    #~ int       num_hot_key;
    #~ XIMHotKeyTrigger  *key;
#~ } XIMHotKeyTriggers;
class _XIMHotKeyTriggers(Structure):
  _fields_ = [
    ('num_hot_key', c_int),
    ('key', POINTER(XIMHotKeyTrigger)),
  ]
XIMHotKeyTriggers = _XIMHotKeyTriggers

#~ typedef  unsigned long   XIMHotKeyState;
XIMHotKeyState = c_ulong

XIMHotKeyStateON = (0x0001)
XIMHotKeyStateOFF = (0x0002)

#~ typedef struct {
    #~ unsigned short count_values;
    #~ char **supported_values;
#~ } XIMValuesList;
class XIMValuesList(Structure):
  _fields_ = [
    ('count_values', c_ushort),
    ('supported_values', POINTER(c_char_p)),
  ]

#if defined(WIN32) && !defined(_XLIBINT_)
#define _Xdebug (*_Xdebug_p)
#endif
#~ extern int _Xdebug;

#~ extern XFontStruct *XLoadQueryFont(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* name */
#~ );
XLoadQueryFont = libX11.XLoadQueryFont
XLoadQueryFont.restype = POINTER(XFontStruct)
XLoadQueryFont.argtypes = [POINTER(Display), XID]

#~ extern XFontStruct *XQueryFont(
    #~ Display*    /* display */,
    #~ XID      /* font_ID */
#~ );
XQueryFont = libX11.XQueryFont
XQueryFont.restype = POINTER(XFontStruct)
XQueryFont.argtypes = [POINTER(Display), XID]

#~ extern XTimeCoord *XGetMotionEvents(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Time    /* start */,
    #~ Time    /* stop */,
    #~ int*    /* nevents_return */
#~ );
XGetMotionEvents = libX11.XGetMotionEvents
XGetMotionEvents.restype = POINTER(XTimeCoord)
XGetMotionEvents.argtypes = [POINTER(Display), Window, Time, Time, POINTER(c_int)]

#~ extern XModifierKeymap *XDeleteModifiermapEntry(
    #~ XModifierKeymap*  /* modmap */,
#~ #if NeedWidePrototypes
    #~ unsigned int  /* keycode_entry */,
#~ #else
    #~ KeyCode    /* keycode_entry */,
#~ #endif
    #~ int      /* modifier */
#~ );
XDeleteModifiermapEntry = libX11.XDeleteModifiermapEntry
XDeleteModifiermapEntry.restype = POINTER(XModifierKeymap)
XDeleteModifiermapEntry.argtypes = [POINTER(XModifierKeymap), KeyCode, c_int]

#~ extern XModifierKeymap  *XGetModifierMapping(
    #~ Display*    /* display */
#~ );
XGetModifierMapping = libX11.XGetModifierMapping
XGetModifierMapping.restype = POINTER(XModifierKeymap)
XGetModifierMapping.argtypes = [POINTER(Display)]

#~ extern XModifierKeymap  *XInsertModifiermapEntry(
    #~ XModifierKeymap*  /* modmap */,
#~ #if NeedWidePrototypes
    #~ unsigned int  /* keycode_entry */,
#~ #else
    #~ KeyCode    /* keycode_entry */,
#~ #endif
    #~ int      /* modifier */
#~ );
XInsertModifiermapEntry = libX11.XInsertModifiermapEntry
XInsertModifiermapEntry.restype = POINTER(XModifierKeymap)
XInsertModifiermapEntry.argtypes = [POINTER(XModifierKeymap), KeyCode, c_int]

#~ extern XModifierKeymap *XNewModifiermap(
    #~ int      /* max_keys_per_mod */
#~ );
XNewModifiermap = libX11.XNewModifiermap
XNewModifiermap.restype = POINTER(XModifierKeymap)
XNewModifiermap.argtypes = [c_int]

#~ extern XImage *XCreateImage(
    #~ Display*    /* display */,
    #~ Visual*    /* visual */,
    #~ unsigned int  /* depth */,
    #~ int      /* format */,
    #~ int      /* offset */,
    #~ char*    /* data */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ int      /* bitmap_pad */,
    #~ int      /* bytes_per_line */
#~ );
XCreateImage = libX11.XCreateImage
XCreateImage.restype = POINTER(XImage)
XCreateImage.argtypes = [POINTER(Display), POINTER(Visual), c_uint, c_int, c_int, c_char_p, c_uint, c_uint, c_int, c_int]

#~ extern Status XInitImage(
    #~ XImage*    /* image */
#~ );
XInitImage = libX11.XInitImage
XInitImage.restype = Status
XInitImage.argtypes = [POINTER(XImage)]

#~ extern XImage *XGetImage(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned long  /* plane_mask */,
    #~ int      /* format */
#~ );
XGetImage = libX11.XGetImage
XGetImage.restype = POINTER(XImage)
XGetImage.argtypes = [POINTER(Display), Drawable, c_int, c_int, c_uint, c_uint, c_ulong, c_int]

#~ extern XImage *XGetSubImage(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned long  /* plane_mask */,
    #~ int      /* format */,
    #~ XImage*    /* dest_image */,
    #~ int      /* dest_x */,
    #~ int      /* dest_y */
#~ );
XGetSubImage = libX11.XGetSubImage
XGetSubImage.restype = POINTER(XImage)
XGetSubImage.argtypes = [POINTER(Display), Drawable, c_int, c_int, c_uint, c_uint, c_ulong, c_int, POINTER(XImage), c_int, c_int]

#/*
# * X function declarations.
# */

#~ extern Display *XOpenDisplay(
    #~ _Xconst char*  /* display_name */
#~ );
XOpenDisplay = libX11.XOpenDisplay
XOpenDisplay.restype = POINTER(Display)
XOpenDisplay.argtypes = [c_char_p]

#~ extern void XrmInitialize(
    #~ void
#~ );
XrmInitialize = libX11.XrmInitialize

#~ extern char *XFetchBytes(
    #~ Display*    /* display */,
    #~ int*    /* nbytes_return */
#~ );
XFetchBytes = libX11.XFetchBytes
XFetchBytes.restype = c_char_p
XFetchBytes.argtypes = [POINTER(Display), POINTER(c_int)]

#~ extern char *XFetchBuffer(
    #~ Display*    /* display */,
    #~ int*    /* nbytes_return */,
    #~ int      /* buffer */
#~ );
XFetchBuffer = libX11.XFetchBuffer
XFetchBuffer.restype = c_char_p
XFetchBuffer.argtypes = [POINTER(Display), POINTER(c_int), c_int]

#~ extern char *XGetAtomName(
    #~ Display*    /* display */,
    #~ Atom    /* atom */
#~ );
XGetAtomName = libX11.XGetAtomName
XGetAtomName.restype = c_char_p
XGetAtomName.argtypes = [POINTER(Display), Atom]

#~ extern Status XGetAtomNames(
    #~ Display*    /* dpy */,
    #~ Atom*    /* atoms */,
    #~ int      /* count */,
    #~ char**    /* names_return */
#~ );
XGetAtomNames = libX11.XGetAtomNames
XGetAtomNames.restype = Status
XGetAtomNames.argtypes = [POINTER(Display), POINTER(Atom), c_int, POINTER(c_char_p)]

#~ extern char *XGetDefault(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* program */,
    #~ _Xconst char*  /* option */
#~ );
XGetDefault = libX11.XGetDefault
XGetDefault.restype = c_char_p
XGetDefault.argtypes = [POINTER(Display), c_char_p, c_char_p]

#~ extern char *XDisplayName(
    #~ _Xconst char*  /* string */
#~ );
XDisplayName = libX11.XDisplayName
XDisplayName.restype = c_char_p
XDisplayName.argtypes = [c_char_p]

#~ extern char *XKeysymToString(
    #~ KeySym    /* keysym */
#~ );
XKeysymToString = libX11.XKeysymToString
XKeysymToString.restype = c_char_p
XKeysymToString.argtypes = [KeySym]

#~ extern int (*XSynchronize(
    #~ Display*    /* display */,
    #~ Bool    /* onoff */
#~ ))(
    #~ Display*    /* display */
#~ );
XSynchronize = c_void_p

#~ extern int (*XSetAfterFunction(
    #~ Display*    /* display */,
    #~ int (*) (
       #~ Display*  /* display */
            #~ )    /* procedure */
#~ ))(
    #~ Display*    /* display */
#~ );
XSetAfterFunction = c_void_p

#~ extern Atom XInternAtom(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* atom_name */,
    #~ Bool    /* only_if_exists */
#~ );
XInternAtom = libX11.XInternAtom
XInternAtom.restype = Atom
XInternAtom.argtypes = [POINTER(Display), c_char_p, Bool]

#~ extern Status XInternAtoms(
    #~ Display*    /* dpy */,
    #~ char**    /* names */,
    #~ int      /* count */,
    #~ Bool    /* onlyIfExists */,
    #~ Atom*    /* atoms_return */
#~ );
XInternAtoms = libX11.XInternAtoms
XInternAtoms.restype = Status
XInternAtoms.argtypes = [POINTER(Display), POINTER(c_char_p), c_int, Bool, POINTER(Atom)]

#~ extern Colormap XCopyColormapAndFree(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */
#~ );
XCopyColormapAndFree = libX11.XCopyColormapAndFree
XCopyColormapAndFree.restype = Colormap
XCopyColormapAndFree.argtypes = [POINTER(Display), Colormap]

#~ extern Colormap XCreateColormap(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Visual*    /* visual */,
    #~ int      /* alloc */
#~ );
XCreateColormap = libX11.XCreateColormap
XCreateColormap.restype = Colormap
XCreateColormap.argtypes = [POINTER(Display), Window, POINTER(Visual), c_int]

#~ extern Cursor XCreatePixmapCursor(
    #~ Display*    /* display */,
    #~ Pixmap    /* source */,
    #~ Pixmap    /* mask */,
    #~ XColor*    /* foreground_color */,
    #~ XColor*    /* background_color */,
    #~ unsigned int  /* x */,
    #~ unsigned int  /* y */
#~ );
XCreatePixmapCursor = libX11.XCreatePixmapCursor
XCreatePixmapCursor.restype = Cursor
XCreatePixmapCursor.argtypes = [POINTER(Display), Pixmap, Pixmap, POINTER(XColor), POINTER(XColor), c_uint, c_uint]

#~ extern Cursor XCreateGlyphCursor(
    #~ Display*    /* display */,
    #~ Font    /* source_font */,
    #~ Font    /* mask_font */,
    #~ unsigned int  /* source_char */,
    #~ unsigned int  /* mask_char */,
    #~ XColor _Xconst *  /* foreground_color */,
    #~ XColor _Xconst *  /* background_color */
#~ );
XCreateGlyphCursor = libX11.XCreateGlyphCursor
XCreateGlyphCursor.restype = Cursor
XCreateGlyphCursor.argtypes = [POINTER(Display), Font, Font, c_uint, c_uint, POINTER(XColor), POINTER(XColor)]

#~ extern Cursor XCreateFontCursor(
    #~ Display*    /* display */,
    #~ unsigned int  /* shape */
#~ );
XCreateFontCursor = libX11.XCreateFontCursor
XCreateFontCursor.restype = Cursor
XCreateFontCursor.argtypes = [POINTER(Display), c_uint]

#~ extern Font XLoadFont(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* name */
#~ );
XLoadFont = libX11.XLoadFont
XLoadFont.restype = Font
XLoadFont.argtypes = [POINTER(Display), c_char_p]

#~ extern GC XCreateGC(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ unsigned long  /* valuemask */,
    #~ XGCValues*    /* values */
#~ );
XCreateGC = libX11.XCreateGC
XCreateGC.restype = GC
XCreateGC.argtypes = [POINTER(Display), Drawable, c_ulong, POINTER(XGCValues)]

#~ extern GContext XGContextFromGC(
    #~ GC      /* gc */
#~ );
XGContextFromGC = libX11.XGContextFromGC
XGContextFromGC.restype = GContext
XGContextFromGC.argtypes = [GC]

#~ extern void XFlushGC(
    #~ Display*    /* display */,
    #~ GC      /* gc */
#~ );
XFlushGC = libX11.XFlushGC
XFlushGC.argtypes = [POINTER(Display), GC]

#~ extern Pixmap XCreatePixmap(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned int  /* depth */
#~ );
XCreatePixmap = libX11.XCreatePixmap
XCreatePixmap.restype = Pixmap
XCreatePixmap.argtypes = [POINTER(Display), Drawable, c_uint, c_uint, c_uint]

#~ extern Pixmap XCreateBitmapFromData(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ _Xconst char*  /* data */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */
#~ );
XCreateBitmapFromData = libX11.XCreateBitmapFromData
XCreateBitmapFromData.restype = Pixmap
XCreateBitmapFromData.argtypes = [POINTER(Display), Drawable, c_char_p, c_uint, c_uint]

#~ extern Pixmap XCreatePixmapFromBitmapData(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ char*    /* data */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned long  /* fg */,
    #~ unsigned long  /* bg */,
    #~ unsigned int  /* depth */
#~ );
XCreatePixmapFromBitmapData = libX11.XCreatePixmapFromBitmapData
XCreatePixmapFromBitmapData.restype = Pixmap
XCreatePixmapFromBitmapData.argtypes = [POINTER(Display), Drawable, c_char_p, c_uint, c_uint, c_ulong, c_ulong, c_uint]

#~ extern Window XCreateSimpleWindow(
    #~ Display*    /* display */,
    #~ Window    /* parent */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned int  /* border_width */,
    #~ unsigned long  /* border */,
    #~ unsigned long  /* background */
#~ );
XCreateSimpleWindow = libX11.XCreateSimpleWindow
XCreateSimpleWindow.restype = Window
XCreateSimpleWindow.argtypes = [POINTER(Display), Window, c_int, c_int, c_uint, c_uint, c_uint, c_ulong, c_ulong]

#~ extern Window XGetSelectionOwner(
    #~ Display*    /* display */,
    #~ Atom    /* selection */
#~ );
XGetSelectionOwner = libX11.XGetSelectionOwner
XGetSelectionOwner.restype = Window
XGetSelectionOwner.argtypes = [POINTER(Display), Atom]

#~ extern Window XCreateWindow(
    #~ Display*    /* display */,
    #~ Window    /* parent */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned int  /* border_width */,
    #~ int      /* depth */,
    #~ unsigned int  /* class */,
    #~ Visual*    /* visual */,
    #~ unsigned long  /* valuemask */,
    #~ XSetWindowAttributes*  /* attributes */
#~ );
XCreateWindow = libX11.XCreateWindow
XCreateWindow.restype = Window
XCreateWindow.argtypes = [POINTER(Display), Window, c_int, c_int, c_uint, c_uint, c_uint, c_int, c_uint, POINTER(Visual), c_ulong, POINTER(XSetWindowAttributes)]

#~ extern Colormap *XListInstalledColormaps(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int*    /* num_return */
#~ );
XListInstalledColormaps = libX11.XListInstalledColormaps
XListInstalledColormaps.restype = POINTER(Colormap)
XListInstalledColormaps.argtypes = [POINTER(Display), Window, POINTER(c_int)]

#~ extern char **XListFonts(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* pattern */,
    #~ int      /* maxnames */,
    #~ int*    /* actual_count_return */
#~ );
XListFonts = libX11.XListFonts
XListFonts.restype = POINTER(c_char_p)
XListFonts.argtypes = [POINTER(Display), c_char_p, c_int, POINTER(c_int)]

#~ extern char **XListFontsWithInfo(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* pattern */,
    #~ int      /* maxnames */,
    #~ int*    /* count_return */,
    #~ XFontStruct**  /* info_return */
#~ );
XListFontsWithInfo = libX11.XListFontsWithInfo
XListFontsWithInfo.restype = POINTER(c_char_p)
XListFontsWithInfo.argtypes = [POINTER(Display), c_char_p, c_int, POINTER(c_int), POINTER(POINTER(XFontStruct))]

#~ extern char **XGetFontPath(
    #~ Display*    /* display */,
    #~ int*    /* npaths_return */
#~ );
XGetFontPath = libX11.XGetFontPath
XGetFontPath.restype = POINTER(c_char_p)
XGetFontPath.argtypes = [POINTER(Display), POINTER(c_int)]

#~ extern char **XListExtensions(
    #~ Display*    /* display */,
    #~ int*    /* nextensions_return */
#~ );
XListExtensions = libX11.XListExtensions
XListExtensions.restype = POINTER(c_char_p)
XListExtensions.argtypes = [POINTER(Display), POINTER(c_int)]

#~ extern Atom *XListProperties(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int*    /* num_prop_return */
#~ );
XListProperties = libX11.XListProperties
XListProperties.restype = POINTER(Atom)
XListProperties.argtypes = [POINTER(Display), Window, POINTER(c_int)]

#~ extern XHostAddress *XListHosts(
    #~ Display*    /* display */,
    #~ int*    /* nhosts_return */,
    #~ Bool*    /* state_return */
#~ );
XListHosts = libX11.XListHosts
XListHosts.restype = POINTER(XHostAddress)
XListHosts.argtypes = [POINTER(Display), POINTER(c_int), POINTER(Bool)]

#~ extern KeySym XKeycodeToKeysym(
    #~ Display*    /* display */,
#~ #if NeedWidePrototypes
    #~ unsigned int  /* keycode */,
#~ #else
    #~ KeyCode    /* keycode */,
#~ #endif
    #~ int      /* index */
#~ );
XKeycodeToKeysym = libX11.XKeycodeToKeysym
XKeycodeToKeysym.restype = KeySym
XKeycodeToKeysym.argtypes = [POINTER(Display), KeyCode, c_int]

#~ extern KeySym XLookupKeysym(
    #~ XKeyEvent*    /* key_event */,
    #~ int      /* index */
#~ );
XLookupKeysym = libX11.XLookupKeysym
XLookupKeysym.restype = KeySym
XLookupKeysym.argtypes = [POINTER(XKeyEvent), c_int]

#~ extern KeySym *XGetKeyboardMapping(
    #~ Display*    /* display */,
#~ #if NeedWidePrototypes
    #~ unsigned int  /* first_keycode */,
#~ #else
    #~ KeyCode    /* first_keycode */,
#~ #endif
    #~ int      /* keycode_count */,
    #~ int*    /* keysyms_per_keycode_return */
#~ );
XGetKeyboardMapping = libX11.XGetKeyboardMapping
XGetKeyboardMapping.restype = POINTER(KeySym)
XGetKeyboardMapping.argtypes = [POINTER(Display), KeyCode, c_int, POINTER(c_int)]

#~ extern KeySym XStringToKeysym(
    #~ _Xconst char*  /* string */
#~ );
XStringToKeysym = libX11.XStringToKeysym
XStringToKeysym.restype = KeySym
XStringToKeysym.argtypes = [c_char_p]

#~ extern long XMaxRequestSize(
    #~ Display*    /* display */
#~ );
XMaxRequestSize = libX11.XMaxRequestSize
XMaxRequestSize.restype = c_long
XMaxRequestSize.argtypes = [POINTER(Display)]

#~ extern long XExtendedMaxRequestSize(
    #~ Display*    /* display */
#~ );
XExtendedMaxRequestSize = libX11.XExtendedMaxRequestSize
XExtendedMaxRequestSize.restype = c_long
XExtendedMaxRequestSize.argtypes = [POINTER(Display)]

#~ extern char *XResourceManagerString(
    #~ Display*    /* display */
#~ );
XResourceManagerString = libX11.XResourceManagerString
XResourceManagerString.restype = c_char_p
XResourceManagerString.argtypes = [POINTER(Display)]

#~ extern char *XScreenResourceString(
  #~ Screen*    /* screen */
#~ );
XScreenResourceString = libX11.XScreenResourceString
XScreenResourceString.restype = c_char_p
XScreenResourceString.argtypes = [POINTER(Screen)]

#~ extern unsigned long XDisplayMotionBufferSize(
    #~ Display*    /* display */
#~ );
XDisplayMotionBufferSize = libX11.XDisplayMotionBufferSize
XDisplayMotionBufferSize.restype = c_ulong
XDisplayMotionBufferSize.argtypes = [POINTER(Display)]

#~ extern VisualID XVisualIDFromVisual(
    #~ Visual*    /* visual */
#~ );
XVisualIDFromVisual = libX11.XVisualIDFromVisual
XVisualIDFromVisual.restype = VisualID
XVisualIDFromVisual.argtypes = [POINTER(Visual)]

#~ /* multithread routines */

#~ extern Status XInitThreads(
    #~ void
#~ );
XInitThreads = libX11.XInitThreads

#~ extern void XLockDisplay(
    #~ Display*    /* display */
#~ );
XLockDisplay = libX11.XLockDisplay
XLockDisplay.argtypes = [POINTER(Display)]

#~ extern void XUnlockDisplay(
    #~ Display*    /* display */
#~ );
XUnlockDisplay = libX11.XUnlockDisplay
XUnlockDisplay.argtypes = [POINTER(Display)]

#~ /* routines for dealing with extensions */

#~ extern XExtCodes *XInitExtension(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* name */
#~ );
XInitExtension = libX11.XInitExtension
XInitExtension.restype = POINTER(XExtCodes)
XInitExtension.argtypes = [POINTER(Display), c_char_p]

#~ extern XExtCodes *XAddExtension(
    #~ Display*    /* display */
#~ );
XAddExtension = libX11.XAddExtension
XAddExtension.restype = POINTER(XExtCodes)
XAddExtension.argtypes = [POINTER(Display)]

#~ extern XExtData *XFindOnExtensionList(
    #~ XExtData**    /* structure */,
    #~ int      /* number */
#~ );
XFindOnExtensionList = libX11.XFindOnExtensionList
XFindOnExtensionList.restype = POINTER(XExtCodes)
XFindOnExtensionList.argtypes = [POINTER(POINTER(XExtCodes)), c_int]

#~ extern XExtData **XEHeadOfExtensionList(
    #~ XEDataObject  /* object */
#~ );
XEHeadOfExtensionList = libX11.XEHeadOfExtensionList
XEHeadOfExtensionList.restype = POINTER(POINTER(XExtCodes))
XEHeadOfExtensionList.argtypes = [XEDataObject]

#~ /* these are routines for which there are also macros */
#~ extern Window XRootWindow(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XRootWindow = libX11.XRootWindow
XRootWindow.restype = Window
XRootWindow.argtypes = [POINTER(Display), c_int]

#~ extern Window XDefaultRootWindow(
    #~ Display*    /* display */
#~ );
XDefaultRootWindow = libX11.XDefaultRootWindow
XDefaultRootWindow.restype = Window
XDefaultRootWindow.argtypes = [POINTER(Display)]

#~ extern Window XRootWindowOfScreen(
    #~ Screen*    /* screen */
#~ );
XRootWindowOfScreen = libX11.XRootWindowOfScreen
XRootWindowOfScreen.restype = Window
XRootWindowOfScreen.argtypes = [POINTER(Screen)]

#~ extern Visual *XDefaultVisual(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDefaultVisual = libX11.XDefaultVisual
XDefaultVisual.restype = POINTER(Visual)
XDefaultVisual.argtypes = [POINTER(Display), c_int]

#~ extern Visual *XDefaultVisualOfScreen(
    #~ Screen*    /* screen */
#~ );
XDefaultVisualOfScreen = libX11.XDefaultVisualOfScreen
XDefaultVisualOfScreen.restype = POINTER(Visual)
XDefaultVisualOfScreen.argtypes = [POINTER(Screen)]

#~ extern GC XDefaultGC(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDefaultGC = libX11.XDefaultGC
XDefaultGC.restype = GC
XDefaultGC.argtypes = [POINTER(Display), c_int]

#~ extern GC XDefaultGCOfScreen(
    #~ Screen*    /* screen */
#~ );
XDefaultGCOfScreen = libX11.XDefaultGCOfScreen
XDefaultGCOfScreen.restype = GC
XDefaultGCOfScreen.argtypes = [POINTER(Screen)]

#~ extern unsigned long XBlackPixel(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XBlackPixel = libX11.XBlackPixel
XBlackPixel.restype = c_ulong
XBlackPixel.argtypes = [POINTER(Display), c_int]

#~ extern unsigned long XWhitePixel(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XWhitePixel = libX11.XWhitePixel
XWhitePixel.restype = c_ulong
XWhitePixel.argtypes = [POINTER(Display), c_int]

#~ extern unsigned long XAllPlanes(
    #~ void
#~ );
XAllPlanes = libX11.XAllPlanes
XAllPlanes.restype = c_ulong
XAllPlanes.argtypes = []

#~ extern unsigned long XBlackPixelOfScreen(
    #~ Screen*    /* screen */
#~ );
XBlackPixelOfScreen = libX11.XBlackPixelOfScreen
XBlackPixelOfScreen.restype = c_ulong
XBlackPixelOfScreen.argtypes = [POINTER(Screen)]

#~ extern unsigned long XWhitePixelOfScreen(
    #~ Screen*    /* screen */
#~ );
XWhitePixelOfScreen = libX11.XWhitePixelOfScreen
XWhitePixelOfScreen.restype = c_ulong
XWhitePixelOfScreen.argtypes = [POINTER(Screen)]

#~ extern unsigned long XNextRequest(
    #~ Display*    /* display */
#~ );
XNextRequest = libX11.XNextRequest
XNextRequest.restype = c_ulong
XNextRequest.argtypes = [POINTER(Display)]

#~ extern unsigned long XLastKnownRequestProcessed(
    #~ Display*    /* display */
#~ );
XLastKnownRequestProcessed = libX11.XLastKnownRequestProcessed
XLastKnownRequestProcessed.restype = c_ulong
XLastKnownRequestProcessed.argtypes = [POINTER(Display)]

#~ extern char *XServerVendor(
    #~ Display*    /* display */
#~ );
XServerVendor = libX11.XServerVendor
XServerVendor.restype = c_char_p
XServerVendor.argtypes = [POINTER(Display)]

#~ extern char *XDisplayString(
    #~ Display*    /* display */
#~ );
XDisplayString = libX11.XDisplayString
XDisplayString.restype = c_char_p
XDisplayString.argtypes = [POINTER(Display)]

#~ extern Colormap XDefaultColormap(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDefaultColormap = libX11.XDefaultColormap
XDefaultColormap.restype = Colormap
XDefaultColormap.argtypes = [POINTER(Display), c_int]

#~ extern Colormap XDefaultColormapOfScreen(
    #~ Screen*    /* screen */
#~ );
XDefaultColormapOfScreen = libX11.XDefaultColormapOfScreen
XDefaultColormapOfScreen.restype = Colormap
XDefaultColormapOfScreen.argtypes = [POINTER(Screen)]

#~ extern Display *XDisplayOfScreen(
    #~ Screen*    /* screen */
#~ );
XDisplayOfScreen = libX11.XDisplayOfScreen
XDisplayOfScreen.restype = POINTER(Display)
XDisplayOfScreen.argtypes = [POINTER(Screen)]

#~ extern Screen *XScreenOfDisplay(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XScreenOfDisplay = libX11.XScreenOfDisplay
XScreenOfDisplay.restype = POINTER(Screen)
XScreenOfDisplay.argtypes = [POINTER(Display), c_int]

#~ extern Screen *XDefaultScreenOfDisplay(
    #~ Display*    /* display */
#~ );
XDefaultScreenOfDisplay = libX11.XDefaultScreenOfDisplay
XDefaultScreenOfDisplay.restype = POINTER(Screen)
XDefaultScreenOfDisplay.argtypes = [POINTER(Display)]

#~ extern long XEventMaskOfScreen(
    #~ Screen*    /* screen */
#~ );
XEventMaskOfScreen = libX11.XEventMaskOfScreen
XEventMaskOfScreen.restype = c_long
XEventMaskOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XScreenNumberOfScreen(
    #~ Screen*    /* screen */
#~ );
XScreenNumberOfScreen = libX11.XScreenNumberOfScreen
XScreenNumberOfScreen.restype = c_int
XScreenNumberOfScreen.argtypes = [POINTER(Screen)]

#~ typedef int (*XErrorHandler) (      /* WARNING, this type not in Xlib spec */
    #~ Display*    /* display */,
    #~ XErrorEvent*  /* error_event */
#~ );
XErrorHandler = c_void_p

#~ extern XErrorHandler XSetErrorHandler (
    #~ XErrorHandler  /* handler */
#~ );
XSetErrorHandler = libX11.XSetErrorHandler
XSetErrorHandler.restype = XErrorHandler
XSetErrorHandler.argtypes = [XErrorHandler]

#~ typedef int (*XIOErrorHandler) (    /* WARNING, this type not in Xlib spec */
    #~ Display*    /* display */
#~ );
XIOErrorHandler = c_void_p

#~ extern XIOErrorHandler XSetIOErrorHandler (
    #~ XIOErrorHandler  /* handler */
#~ );
XSetIOErrorHandler = libX11.XSetIOErrorHandler
XSetIOErrorHandler.restype = XIOErrorHandler
XSetIOErrorHandler.argtypes = [XIOErrorHandler]

#~ extern XPixmapFormatValues *XListPixmapFormats(
    #~ Display*    /* display */,
    #~ int*    /* count_return */
#~ );
XListPixmapFormats = libX11.XListPixmapFormats
XListPixmapFormats.restype = POINTER(XPixmapFormatValues)
XListPixmapFormats.argtypes = [POINTER(Display), POINTER(c_int)]

#~ extern int *XListDepths(
    #~ Display*    /* display */,
    #~ int      /* screen_number */,
    #~ int*    /* count_return */
#~ );
XListDepths = libX11.XListDepths
XListDepths.restype = POINTER(c_int)
XListDepths.argtypes = [POINTER(Display), c_int, POINTER(c_int)]

#~ #/* ICCCM routines for things that don't require special include files; */
#~ #/* other declarations are given in Xutil.h                             */
#~ extern Status XReconfigureWMWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* screen_number */,
    #~ unsigned int  /* mask */,
    #~ XWindowChanges*  /* changes */
#~ );
XReconfigureWMWindow = libX11.XReconfigureWMWindow
XReconfigureWMWindow.restype = Status
XReconfigureWMWindow.argtypes = [POINTER(Display), Window, c_int, c_uint, POINTER(XWindowChanges)]

#~ extern Status XGetWMProtocols(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Atom**    /* protocols_return */,
    #~ int*    /* count_return */
#~ );
XGetWMProtocols = libX11.XGetWMProtocols
XGetWMProtocols.restype = Status
XGetWMProtocols.argtypes = [POINTER(Display), Window, POINTER(POINTER(Atom)), POINTER(c_int)]

#~ extern Status XSetWMProtocols(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Atom*    /* protocols */,
    #~ int      /* count */
#~ );
XSetWMProtocols = libX11.XSetWMProtocols
XSetWMProtocols.restype = Status
XSetWMProtocols.argtypes = [POINTER(Display), Window, POINTER(Atom), c_int]

#~ extern Status XIconifyWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* screen_number */
#~ );
XIconifyWindow = libX11.XIconifyWindow
XIconifyWindow.restype = Status
XIconifyWindow.argtypes = [POINTER(Display), Window, c_int]

#~ extern Status XWithdrawWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* screen_number */
#~ );
XWithdrawWindow = libX11.XWithdrawWindow
XWithdrawWindow.restype = Status
XWithdrawWindow.argtypes = [POINTER(Display), Window, c_int]

#~ extern Status XGetCommand(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ char***    /* argv_return */,
    #~ int*    /* argc_return */
#~ );
XGetCommand = libX11.XGetCommand
XGetCommand.restype = Status
XGetCommand.argtypes = [POINTER(Display), Window, POINTER(POINTER(c_char_p)), POINTER(c_int)]

#~ extern Status XGetWMColormapWindows(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Window**    /* windows_return */,
    #~ int*    /* count_return */
#~ );
XGetWMColormapWindows = libX11.XGetWMColormapWindows
XGetWMColormapWindows.restype = Status
XGetWMColormapWindows.argtypes = [POINTER(Display), Window, POINTER(POINTER(Window)), POINTER(c_int)]

#~ extern Status XSetWMColormapWindows(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Window*    /* colormap_windows */,
    #~ int      /* count */
#~ );
XSetWMColormapWindows = libX11.XSetWMColormapWindows
XSetWMColormapWindows.restype = Status
XSetWMColormapWindows.argtypes = [POINTER(Display), Window, POINTER(Window), c_int]

#~ extern void XFreeStringList(
    #~ char**    /* list */
#~ );
XFreeStringList = libX11.XFreeStringList
XFreeStringList.argtypes = [POINTER(c_char_p)]

#~ extern int XSetTransientForHint(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Window    /* prop_window */
#~ );
XSetTransientForHint = libX11.XSetTransientForHint
XSetTransientForHint.restype = c_int
XSetTransientForHint.argtypes = [POINTER(Display), Window, Window]

#~ /* The following are given in alphabetical order */

#~ extern int XActivateScreenSaver(
    #~ Display*    /* display */
#~ );
XActivateScreenSaver = libX11.XActivateScreenSaver
XActivateScreenSaver.restype = c_int
XActivateScreenSaver.argtypes = [POINTER(Display)]

#~ extern int XAddHost(
    #~ Display*    /* display */,
    #~ XHostAddress*  /* host */
#~ );
XAddHost = libX11.XAddHost
XAddHost.restype = c_int
XAddHost.argtypes = [POINTER(Display), POINTER(XHostAddress)]

#~ extern int XAddHosts(
    #~ Display*    /* display */,
    #~ XHostAddress*  /* hosts */,
    #~ int      /* num_hosts */
#~ );
XAddHosts = libX11.XAddHosts
XAddHosts.restype = c_int
XAddHosts.argtypes = [POINTER(Display), POINTER(XHostAddress), c_int]

#~ extern int XAddToExtensionList(
    #~ struct _XExtData**  /* structure */,
    #~ XExtData*    /* ext_data */
#~ );
XAddToExtensionList = libX11.XAddToExtensionList
XAddToExtensionList.restype = c_int
XAddToExtensionList.argtypes = [POINTER(POINTER(_XExtData)), POINTER(XExtData)]

#~ extern int XAddToSaveSet(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XAddToSaveSet = libX11.XAddToSaveSet
XAddToSaveSet.restype = c_int
XAddToSaveSet.argtypes = [POINTER(Display), Window]

#~ extern Status XAllocColor(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ XColor*    /* screen_in_out */
#~ );
XAllocColor = libX11.XAllocColor
XAllocColor.restype = Status
XAllocColor.argtypes = [POINTER(Display), Colormap,POINTER(XColor)]

#~ extern Status XAllocColorCells(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ Bool          /* contig */,
    #~ unsigned long*  /* plane_masks_return */,
    #~ unsigned int  /* nplanes */,
    #~ unsigned long*  /* pixels_return */,
    #~ unsigned int   /* npixels */
#~ );
XAllocColorCells = libX11.XAllocColorCells
XAllocColorCells.restype = Status
XAllocColorCells.argtypes = [POINTER(Display), Colormap, Bool, POINTER(c_ulong), c_int, POINTER(c_ulong), c_int]

#~ extern Status XAllocColorPlanes(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ Bool    /* contig */,
    #~ unsigned long*  /* pixels_return */,
    #~ int      /* ncolors */,
    #~ int      /* nreds */,
    #~ int      /* ngreens */,
    #~ int      /* nblues */,
    #~ unsigned long*  /* rmask_return */,
    #~ unsigned long*  /* gmask_return */,
    #~ unsigned long*  /* bmask_return */
#~ );
XAllocColorPlanes = libX11.XAllocColorPlanes
XAllocColorPlanes.restype = Status
XAllocColorPlanes.argtypes = [POINTER(Display), Colormap, Bool, POINTER(c_ulong), c_int, c_int, c_int, c_int, POINTER(c_ulong), POINTER(c_ulong), POINTER(c_ulong)]

#~ extern Status XAllocNamedColor(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ _Xconst char*  /* color_name */,
    #~ XColor*    /* screen_def_return */,
    #~ XColor*    /* exact_def_return */
#~ );
XAllocNamedColor = libX11.XAllocNamedColor
XAllocNamedColor.restype = Status
XAllocNamedColor.argtypes = [POINTER(Display), Colormap, c_char_p, POINTER(XColor), POINTER(XColor)]

#~ extern int XAllowEvents(
    #~ Display*    /* display */,
    #~ int      /* event_mode */,
    #~ Time    /* time */
#~ );
XAllowEvents = libX11.XAllowEvents
XAllowEvents.restype = c_int
XAllowEvents.argtypes = [POINTER(Display), c_int, Time]

#~ extern int XAutoRepeatOff(
    #~ Display*    /* display */
#~ );
XAutoRepeatOff = libX11.XAutoRepeatOff
XAutoRepeatOff.restype = c_int
XAutoRepeatOff.argtypes = [POINTER(Display)]

#~ extern int XAutoRepeatOn(
    #~ Display*    /* display */
#~ );
XAutoRepeatOn = libX11.XAutoRepeatOn
XAutoRepeatOn.restype = c_int
XAutoRepeatOn.argtypes = [POINTER(Display)]

#~ extern int XBell(
    #~ Display*    /* display */,
    #~ int      /* percent */
#~ );
XBell = libX11.XBell
XBell.restype = c_int
XBell.argtypes = [POINTER(Display), c_int]

#~ extern int XBitmapBitOrder(
    #~ Display*    /* display */
#~ );
XBitmapBitOrder = libX11.XBitmapBitOrder
XBitmapBitOrder.restype = c_int
XBitmapBitOrder.argtypes = [POINTER(Display)]

#~ extern int XBitmapPad(
    #~ Display*    /* display */
#~ );
XBitmapPad = libX11.XBitmapPad
XBitmapPad.restype = c_int
XBitmapPad.argtypes = [POINTER(Display)]

#~ extern int XBitmapUnit(
    #~ Display*    /* display */
#~ );
XBitmapUnit = libX11.XBitmapUnit
XBitmapUnit.restype = c_int
XBitmapUnit.argtypes = [POINTER(Display)]

#~ extern int XCellsOfScreen(
    #~ Screen*    /* screen */
#~ );
XCellsOfScreen = libX11.XCellsOfScreen
XCellsOfScreen.restype = c_int
XCellsOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XChangeActivePointerGrab(
    #~ Display*    /* display */,
    #~ unsigned int  /* event_mask */,
    #~ Cursor    /* cursor */,
    #~ Time    /* time */
#~ );
XChangeActivePointerGrab = libX11.XChangeActivePointerGrab
XChangeActivePointerGrab.restype = c_int
XChangeActivePointerGrab.argtypes = [POINTER(Display), c_uint, Cursor, Time]

#~ extern int XChangeGC(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ unsigned long  /* valuemask */,
    #~ XGCValues*    /* values */
#~ );
XChangeGC = libX11.XChangeGC
XChangeGC.restype = c_int
XChangeGC.argtypes = [POINTER(Display), GC, c_ulong, POINTER(XGCValues)]

#~ extern int XChangeKeyboardControl(
    #~ Display*    /* display */,
    #~ unsigned long  /* value_mask */,
    #~ XKeyboardControl*  /* values */
#~ );
XChangeKeyboardControl = libX11.XChangeKeyboardControl
XChangeKeyboardControl.restype = c_int
XChangeKeyboardControl.argtypes = [POINTER(Display), c_ulong, POINTER(XKeyboardControl)]

#~ extern int XChangeKeyboardMapping(
    #~ Display*    /* display */,
    #~ int      /* first_keycode */,
    #~ int      /* keysyms_per_keycode */,
    #~ KeySym*    /* keysyms */,
    #~ int      /* num_codes */
#~ );
XChangeKeyboardMapping = libX11.XChangeKeyboardMapping
XChangeKeyboardMapping.restype = c_int
XChangeKeyboardMapping.argtypes = [POINTER(Display), c_int, c_int, POINTER(KeySym), c_int]

#~ extern int XChangePointerControl(
    #~ Display*    /* display */,
    #~ Bool    /* do_accel */,
    #~ Bool    /* do_threshold */,
    #~ int      /* accel_numerator */,
    #~ int      /* accel_denominator */,
    #~ int      /* threshold */
#~ );
XChangePointerControl = libX11.XChangePointerControl
XChangePointerControl.restype = c_int
XChangePointerControl.argtypes = [POINTER(Display), Bool, Bool, c_int, c_int, c_int]

#~ extern int XChangeProperty(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Atom    /* property */,
    #~ Atom    /* type */,
    #~ int      /* format */,
    #~ int      /* mode */,
    #~ _Xconst unsigned char*  /* data */,
    #~ int      /* nelements */
#~ );
XChangeProperty = libX11.XChangeProperty
XChangeProperty.restype = c_int
XChangeProperty.argtypes = [POINTER(Display), Window, Atom, Atom, c_int, c_int, c_char_p, c_int]

#~ extern int XChangeSaveSet(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* change_mode */
#~ );
XChangeSaveSet = libX11.XChangeSaveSet
XChangeSaveSet.restype = c_int
XChangeSaveSet.argtypes = [POINTER(Display), Window, c_int]

#~ extern int XChangeWindowAttributes(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ unsigned long  /* valuemask */,
    #~ XSetWindowAttributes* /* attributes */
#~ );
XChangeWindowAttributes = libX11.XChangeWindowAttributes
XChangeWindowAttributes.restype = c_int
XChangeWindowAttributes.argtypes = [POINTER(Display), Window, c_ulong, POINTER(XSetWindowAttributes)]

#~ extern Bool XCheckIfEvent(
    #~ Display*    /* display */,
    #~ XEvent*    /* event_return */,
    #~ Bool (*) (
         #~ Display*      /* display */,
               #~ XEvent*      /* event */,
               #~ XPointer      /* arg */
             #~ )    /* predicate */,
    #~ XPointer    /* arg */
#~ );
XCheckIfEvent = libX11.XCheckIfEvent
XCheckIfEvent.restype = Bool
XCheckIfEvent.argtypes = [POINTER(Display), POINTER(XEvent), c_void_p]

#~ extern Bool XCheckMaskEvent(
    #~ Display*    /* display */,
    #~ long    /* event_mask */,
    #~ XEvent*    /* event_return */
#~ );
XCheckMaskEvent = libX11.XCheckMaskEvent
XCheckMaskEvent.restype = Bool
XCheckMaskEvent.argtypes = [POINTER(Display), c_long, POINTER(XEvent)]

#~ extern Bool XCheckTypedEvent(
    #~ Display*    /* display */,
    #~ int      /* event_type */,
    #~ XEvent*    /* event_return */
#~ );
XCheckTypedEvent = libX11.XCheckTypedEvent
XCheckTypedEvent.restype = Bool
XCheckTypedEvent.argtypes = [POINTER(Display), c_int, POINTER(XEvent)]

#~ extern Bool XCheckTypedWindowEvent(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* event_type */,
    #~ XEvent*    /* event_return */
#~ );
XCheckTypedWindowEvent = libX11.XCheckTypedWindowEvent
XCheckTypedWindowEvent.restype = Bool
XCheckTypedWindowEvent.argtypes = [POINTER(Display), Window, c_int, POINTER(XEvent)]

#~ extern Bool XCheckWindowEvent(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ long    /* event_mask */,
    #~ XEvent*    /* event_return */
#~ );
XCheckWindowEvent = libX11.XCheckWindowEvent
XCheckWindowEvent.restype = Bool
XCheckWindowEvent.argtypes = [POINTER(Display), Window, c_long, POINTER(XEvent)]

#~ extern int XCirculateSubwindows(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* direction */
#~ );
XCirculateSubwindows = libX11.XCirculateSubwindows
XCirculateSubwindows.restype = c_int
XCirculateSubwindows.argtypes = [POINTER(Display), Window, c_int]

#~ extern int XCirculateSubwindowsDown(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XCirculateSubwindowsDown = libX11.XCirculateSubwindowsDown
XCirculateSubwindowsDown.restype = c_int
XCirculateSubwindowsDown.argtypes = [POINTER(Display), Window]

#~ extern int XCirculateSubwindowsUp(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XCirculateSubwindowsUp = libX11.XCirculateSubwindowsUp
XCirculateSubwindowsUp.restype = c_int
XCirculateSubwindowsUp.argtypes = [POINTER(Display), Window]

#~ extern int XClearArea(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ Bool    /* exposures */
#~ );
XClearArea = libX11.XClearArea
XClearArea.restype = c_int
XClearArea.argtypes = [POINTER(Display), Window, c_int, c_int, c_uint, c_uint, Bool]

#~ extern int XClearWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XClearWindow = libX11.XClearWindow
XClearWindow.restype = c_int
XClearWindow.argtypes = [POINTER(Display), Window]

#~ extern int XCloseDisplay(
    #~ Display*    /* display */
#~ );
XCloseDisplay = libX11.XCloseDisplay
XCloseDisplay.restype = c_int
XCloseDisplay.argtypes = [POINTER(Display)]

#~ extern int XConfigureWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ unsigned int  /* value_mask */,
    #~ XWindowChanges*  /* values */
#~ );
XConfigureWindow = libX11.XConfigureWindow
XConfigureWindow.restype = c_int
XConfigureWindow.argtypes = [POINTER(Display), Window, c_uint, POINTER(XWindowChanges)]

#~ extern int XConnectionNumber(
    #~ Display*    /* display */
#~ );
XConnectionNumber = libX11.XConnectionNumber
XConnectionNumber.restype = c_int
XConnectionNumber.argtypes = [POINTER(Display)]

#~ extern int XConvertSelection(
    #~ Display*    /* display */,
    #~ Atom    /* selection */,
    #~ Atom     /* target */,
    #~ Atom    /* property */,
    #~ Window    /* requestor */,
    #~ Time    /* time */
#~ );
XConvertSelection = libX11.XConvertSelection
XConvertSelection.restype = c_int
XConvertSelection.argtypes = [POINTER(Display), Atom, Atom, Atom, Window, Time]

#~ extern int XCopyArea(
    #~ Display*    /* display */,
    #~ Drawable    /* src */,
    #~ Drawable    /* dest */,
    #~ GC      /* gc */,
    #~ int      /* src_x */,
    #~ int      /* src_y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ int      /* dest_x */,
    #~ int      /* dest_y */
#~ );
XCopyArea = libX11.XCopyArea
XCopyArea.restype = c_int
XCopyArea.argtypes = [POINTER(Display), Drawable, Drawable, GC, c_int, c_int, c_uint, c_uint, c_int, c_int]

#~ extern int XCopyGC(
    #~ Display*    /* display */,
    #~ GC      /* src */,
    #~ unsigned long  /* valuemask */,
    #~ GC      /* dest */
#~ );
XCopyGC = libX11.XCopyGC
XCopyGC.restype = c_int
XCopyGC.argtypes = [POINTER(Display), GC, c_ulong, GC]

#~ extern int XCopyPlane(
    #~ Display*    /* display */,
    #~ Drawable    /* src */,
    #~ Drawable    /* dest */,
    #~ GC      /* gc */,
    #~ int      /* src_x */,
    #~ int      /* src_y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ int      /* dest_x */,
    #~ int      /* dest_y */,
    #~ unsigned long  /* plane */
#~ );
XCopyPlane = libX11.XCopyPlane
XCopyPlane.restype = c_int
XCopyPlane.argtypes = [POINTER(Display), Drawable, Drawable, GC, c_int, c_int, c_uint, c_uint, c_int, c_int, c_ulong]

#~ extern int XDefaultDepth(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDefaultDepth = libX11.XDefaultDepth
XDefaultDepth.restype = c_int
XDefaultDepth.argtypes = [POINTER(Display), c_int]

#~ extern int XDefaultDepthOfScreen(
    #~ Screen*    /* screen */
#~ );
XDefaultDepthOfScreen = libX11.XDefaultDepthOfScreen
XDefaultDepthOfScreen.restype = c_int
XDefaultDepthOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XDefaultScreen(
    #~ Display*    /* display */
#~ );
XDefaultScreen = libX11.XDefaultScreen
XDefaultScreen.restype = c_int
XDefaultScreen.argtypes = [POINTER(Display)]

#~ extern int XDefineCursor(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Cursor    /* cursor */
#~ );
XDefineCursor = libX11.XDefineCursor
XDefineCursor.restype = c_int
XDefineCursor.argtypes = [POINTER(Display), Window, Cursor]

#~ extern int XDeleteProperty(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Atom    /* property */
#~ );
XDeleteProperty = libX11.XDeleteProperty
XDeleteProperty.restype = c_int
XDeleteProperty.argtypes = [POINTER(Display), Window, Atom]

#~ extern int XDestroyWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XDestroyWindow = libX11.XDestroyWindow
XDestroyWindow.restype = c_int
XDestroyWindow.argtypes = [POINTER(Display), Window]

#~ extern int XDestroySubwindows(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XDestroySubwindows = libX11.XDestroySubwindows
XDestroySubwindows.restype = c_int
XDestroySubwindows.argtypes = [POINTER(Display), Window]

#~ extern int XDoesBackingStore(
    #~ Screen*    /* screen */
#~ );
XDoesBackingStore = libX11.XDoesBackingStore
XDoesBackingStore.restype = c_int
XDoesBackingStore.argtypes = [POINTER(Screen)]

#~ extern Bool XDoesSaveUnders(
    #~ Screen*    /* screen */
#~ );
XDoesSaveUnders = libX11.XDoesSaveUnders
XDoesSaveUnders.restype = Bool
XDoesSaveUnders.argtypes = [POINTER(Screen)]

#~ extern int XDisableAccessControl(
    #~ Display*    /* display */
#~ );
XDisableAccessControl = libX11.XDisableAccessControl
XDisableAccessControl.restype = c_int
XDisableAccessControl.argtypes = [POINTER(Display)]

#~ extern int XDisplayCells(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDisplayCells = libX11.XDisplayCells
XDisplayCells.restype = c_int
XDisplayCells.argtypes = [POINTER(Display), c_int]

#~ extern int XDisplayHeight(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDisplayHeight = libX11.XDisplayHeight
XDisplayHeight.restype = c_int
XDisplayHeight.argtypes = [POINTER(Display), c_int]

#~ extern int XDisplayHeightMM(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDisplayHeightMM = libX11.XDisplayHeightMM
XDisplayHeightMM.restype = c_int
XDisplayHeightMM.argtypes = [POINTER(Display), c_int]

#~ extern int XDisplayKeycodes(
    #~ Display*    /* display */,
    #~ int*    /* min_keycodes_return */,
    #~ int*    /* max_keycodes_return */
#~ );
XDisplayKeycodes = libX11.XDisplayKeycodes
XDisplayKeycodes.restype = c_int
XDisplayKeycodes.argtypes = [POINTER(Display), POINTER(c_int), POINTER(c_int)]

#~ extern int XDisplayPlanes(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDisplayPlanes = libX11.XDisplayPlanes
XDisplayPlanes.restype = c_int
XDisplayPlanes.argtypes = [POINTER(Display), c_int]

#~ extern int XDisplayWidth(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDisplayWidth = libX11.XDisplayWidth
XDisplayWidth.restype = c_int
XDisplayWidth.argtypes = [POINTER(Display), c_int]

#~ extern int XDisplayWidthMM(
    #~ Display*    /* display */,
    #~ int      /* screen_number */
#~ );
XDisplayWidthMM = libX11.XDisplayWidthMM
XDisplayWidthMM.restype = c_int
XDisplayWidthMM.argtypes = [POINTER(Display), c_int]

#~ extern int XDrawArc(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ int      /* angle1 */,
    #~ int      /* angle2 */
#~ );
XDrawArc = libX11.XDrawArc
XDrawArc.restype = c_int
XDrawArc.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, c_uint, c_uint, c_int, c_int]

#~ extern int XDrawArcs(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XArc*    /* arcs */,
    #~ int      /* narcs */
#~ );
XDrawArcs = libX11.XDrawArcs
XDrawArcs.restype = c_int
XDrawArcs.argtypes = [POINTER(Display), Drawable, GC, POINTER(XArc), c_int]

#~ extern int XDrawImageString(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst char*  /* string */,
    #~ int      /* length */
#~ );
XDrawImageString = libX11.XDrawImageString
XDrawImageString.restype = c_int
XDrawImageString.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, c_char_p, c_int]

#~ extern int XDrawImageString16(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst XChar2b*  /* string */,
    #~ int      /* length */
#~ );
XDrawImageString16 = libX11.XDrawImageString16
XDrawImageString16.restype = c_int
XDrawImageString16.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, POINTER(XChar2b), c_int]

#~ extern int XDrawLine(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x1 */,
    #~ int      /* y1 */,
    #~ int      /* x2 */,
    #~ int      /* y2 */
#~ );
XDrawLine = libX11.XDrawLine
XDrawLine.restype = c_int
XDrawLine.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, c_int, c_int]

#~ extern int XDrawLines(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XPoint*    /* points */,
    #~ int      /* npoints */,
    #~ int      /* mode */
#~ );
XDrawLines = libX11.XDrawLines
XDrawLines.restype = c_int
XDrawLines.argtypes = [POINTER(Display), Drawable, GC, POINTER(XPoint), c_int, c_int]

#~ extern int XDrawPoint(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */
#~ );
XDrawPoint = libX11.XDrawPoint
XDrawPoint.restype = c_int
XDrawPoint.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int]

#~ extern int XDrawPoints(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XPoint*    /* points */,
    #~ int      /* npoints */,
    #~ int      /* mode */
#~ );
XDrawPoints = libX11.XDrawPoints
XDrawPoints.restype = c_int
XDrawPoints.argtypes = [POINTER(Display), Drawable, GC, POINTER(XPoint), c_int, c_int]

#~ extern int XDrawRectangle(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */
#~ );
XDrawRectangle = libX11.XDrawRectangle
XDrawRectangle.restype = c_int
XDrawRectangle.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, c_uint, c_uint]

#~ extern int XDrawRectangles(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XRectangle*    /* rectangles */,
    #~ int      /* nrectangles */
#~ );
XDrawRectangles = libX11.XDrawRectangles
XDrawRectangles.restype = c_int
XDrawRectangles.argtypes = [POINTER(Display), Drawable, GC, POINTER(XRectangle), c_int]

#~ extern int XDrawSegments(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XSegment*    /* segments */,
    #~ int      /* nsegments */
#~ );
XDrawSegments = libX11.XDrawSegments
XDrawSegments.restype = c_int
XDrawSegments.argtypes = [POINTER(Display), Drawable, GC, POINTER(XSegment), c_int]

#~ extern int XDrawString(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst char*  /* string */,
    #~ int      /* length */
#~ );
XDrawString = libX11.XDrawString
XDrawString.restype = c_int
XDrawString.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, c_char_p, c_int]

#~ extern int XDrawString16(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst XChar2b*  /* string */,
    #~ int      /* length */
#~ );
XDrawString16 = libX11.XDrawString16
XDrawString16.restype = c_int
XDrawString16.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, POINTER(XChar2b), c_int]

#~ extern int XDrawText(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ XTextItem*    /* items */,
    #~ int      /* nitems */
#~ );
XDrawText = libX11.XDrawText
XDrawText.restype = c_int
XDrawText.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, POINTER(XTextItem), c_int]

#~ extern int XDrawText16(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ XTextItem16*  /* items */,
    #~ int      /* nitems */
#~ );
XDrawText16 = libX11.XDrawText16
XDrawText16.restype = c_int
XDrawText16.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, POINTER(XTextItem), c_int]

#~ extern int XEnableAccessControl(
    #~ Display*    /* display */
#~ );
XEnableAccessControl = libX11.XEnableAccessControl
XEnableAccessControl.restype = c_int
XEnableAccessControl.argtypes = [POINTER(Display)]

#~ extern int XEventsQueued(
    #~ Display*    /* display */,
    #~ int      /* mode */
#~ );
XEventsQueued = libX11.XEventsQueued
XEventsQueued.restype = c_int
XEventsQueued.argtypes = [POINTER(Display), c_int]

#~ extern Status XFetchName(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ char**    /* window_name_return */
#~ );
XFetchName = libX11.XFetchName
XFetchName.restype = Status
XFetchName.argtypes = [POINTER(Display), Window, POINTER(c_char_p)]

#~ extern int XFillArc(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ int      /* angle1 */,
    #~ int      /* angle2 */
#~ );
XFillArc = libX11.XFillArc
XFillArc.restype = c_int
XFillArc.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, c_uint, c_uint, c_int, c_int]

#~ extern int XFillArcs(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XArc*    /* arcs */,
    #~ int      /* narcs */
#~ );
XFillArcs = libX11.XFillArcs
XFillArcs.restype = c_int
XFillArcs.argtypes = [POINTER(Display), Drawable, GC, POINTER(XArc), c_int]

#~ extern int XFillPolygon(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XPoint*    /* points */,
    #~ int      /* npoints */,
    #~ int      /* shape */,
    #~ int      /* mode */
#~ );
XFillPolygon = libX11.XFillPolygon
XFillPolygon.restype = c_int
XFillPolygon.argtypes = [POINTER(Display), Drawable, GC, POINTER(XPoint), c_int, c_int, c_int]

#~ extern int XFillRectangle(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */
#~ );
XFillRectangle = libX11.XFillRectangle
XFillRectangle.restype = c_int
XFillRectangle.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, c_uint, c_uint]

#~ extern int XFillRectangles(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XRectangle*    /* rectangles */,
    #~ int      /* nrectangles */
#~ );
XFillRectangles = libX11.XFillRectangles
XFillRectangles.restype = c_int
XFillRectangles.argtypes = [POINTER(Display), Drawable, GC, POINTER(XRectangle), c_int]

#~ extern int XFlush(
    #~ Display*    /* display */
#~ );
XFlush = libX11.XFlush
XFlush.restype = c_int
XFlush.argtypes = [POINTER(Display)]

#~ extern int XForceScreenSaver(
    #~ Display*    /* display */,
    #~ int      /* mode */
#~ );
XForceScreenSaver = libX11.XForceScreenSaver
XForceScreenSaver.restype = c_int
XForceScreenSaver.argtypes = [POINTER(Display), c_int]

#~ extern int XFree(
    #~ void*    /* data */
#~ );
XFree = libX11.XFree
XFree.restype = c_int
XFree.argtypes = [c_void_p]

#~ extern int XFreeColormap(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */
#~ );
XFreeColormap = libX11.XFreeColormap
XFreeColormap.restype = c_int
XFreeColormap.argtypes = [POINTER(Display), Colormap]

#~ extern int XFreeColors(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ unsigned long*  /* pixels */,
    #~ int      /* npixels */,
    #~ unsigned long  /* planes */
#~ );
XFreeColors = libX11.XFreeColors
XFreeColors.restype = c_int
XFreeColors.argtypes = [POINTER(Display), Colormap, POINTER(c_ulong), c_int, c_ulong]

#~ extern int XFreeCursor(
    #~ Display*    /* display */,
    #~ Cursor    /* cursor */
#~ );
XFreeCursor = libX11.XFreeCursor
XFreeCursor.restype = c_int
XFreeCursor.argtypes = [POINTER(Display), Cursor]

#~ extern int XFreeExtensionList(
    #~ char**    /* list */
#~ );
XFreeExtensionList = libX11.XFreeExtensionList
XFreeExtensionList.restype = c_int
XFreeExtensionList.argtypes = [POINTER(c_char_p)]

#~ extern int XFreeFont(
    #~ Display*    /* display */,
    #~ XFontStruct*  /* font_struct */
#~ );
XFreeFont = libX11.XFreeFont
XFreeFont.restype = c_int
XFreeFont.argtypes = [POINTER(Display), POINTER(XFontStruct)]

#~ extern int XFreeFontInfo(
    #~ char**    /* names */,
    #~ XFontStruct*  /* free_info */,
    #~ int      /* actual_count */
#~ );
XFreeFontInfo = libX11.XFreeFontInfo
XFreeFontInfo.restype = c_int
XFreeFontInfo.argtypes = [POINTER(c_char_p), POINTER(XFontStruct), c_int]

#~ extern int XFreeFontNames(
    #~ char**    /* list */
#~ );
XFreeFontNames = libX11.XFreeFontNames
XFreeFontNames.restype = c_int
XFreeFontNames.argtypes = [POINTER(c_char_p)]

#~ extern int XFreeFontPath(
    #~ char**    /* list */
#~ );
XFreeFontPath = libX11.XFreeFontPath
XFreeFontPath.restype = c_int
XFreeFontPath.argtypes = [POINTER(c_char_p)]

#~ extern int XFreeGC(
    #~ Display*    /* display */,
    #~ GC      /* gc */
#~ );
XFreeGC = libX11.XFreeGC
XFreeGC.restype = c_int
XFreeGC.argtypes = [POINTER(Display), GC]

#~ extern int XFreeModifiermap(
    #~ XModifierKeymap*  /* modmap */
#~ );
XFreeModifiermap = libX11.XFreeModifiermap
XFreeModifiermap.restype = c_int
XFreeModifiermap.argtypes = [POINTER(XModifierKeymap)]

#~ extern int XFreePixmap(
    #~ Display*    /* display */,
    #~ Pixmap    /* pixmap */
#~ );
XFreePixmap = libX11.XFreePixmap
XFreePixmap.restype = c_int
XFreePixmap.argtypes = [POINTER(Display), Pixmap]

#~ extern int XGeometry(
    #~ Display*    /* display */,
    #~ int      /* screen */,
    #~ _Xconst char*  /* position */,
    #~ _Xconst char*  /* default_position */,
    #~ unsigned int  /* bwidth */,
    #~ unsigned int  /* fwidth */,
    #~ unsigned int  /* fheight */,
    #~ int      /* xadder */,
    #~ int      /* yadder */,
    #~ int*    /* x_return */,
    #~ int*    /* y_return */,
    #~ int*    /* width_return */,
    #~ int*    /* height_return */
#~ );
XGeometry = libX11.XGeometry
XGeometry.restype = c_int
XGeometry.argtypes = [POINTER(Display), c_int, c_char_p, c_char_p, c_uint, c_uint, c_uint, c_int, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int)]

#~ extern int XGetErrorDatabaseText(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* name */,
    #~ _Xconst char*  /* message */,
    #~ _Xconst char*  /* default_string */,
    #~ char*    /* buffer_return */,
    #~ int      /* length */
#~ );
XGetErrorDatabaseText = libX11.XGetErrorDatabaseText
XGetErrorDatabaseText.restype = c_int
XGetErrorDatabaseText.argtypes = [POINTER(Display), c_char_p, c_char_p, c_char_p, c_char_p, c_int]

#~ extern int XGetErrorText(
    #~ Display*    /* display */,
    #~ int      /* code */,
    #~ char*    /* buffer_return */,
    #~ int      /* length */
#~ );
XGetErrorText = libX11.XGetErrorText
XGetErrorText.restype = c_int
XGetErrorText.argtypes = [POINTER(Display), c_int, c_char_p, c_int]

#~ extern Bool XGetFontProperty(
    #~ XFontStruct*  /* font_struct */,
    #~ Atom    /* atom */,
    #~ unsigned long*  /* value_return */
#~ );
XGetFontProperty = libX11.XGetFontProperty
XGetFontProperty.restype = Bool
XGetFontProperty.argtypes = [POINTER(XFontStruct), Atom, POINTER(c_ulong)]

#~ extern Status XGetGCValues(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ unsigned long  /* valuemask */,
    #~ XGCValues*    /* values_return */
#~ );
XGetGCValues = libX11.XGetGCValues
XGetGCValues.restype = Status
XGetGCValues.argtypes = [POINTER(Display), GC, c_ulong, POINTER(XGCValues)]

#~ extern Status XGetGeometry(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ Window*    /* root_return */,
    #~ int*    /* x_return */,
    #~ int*    /* y_return */,
    #~ unsigned int*  /* width_return */,
    #~ unsigned int*  /* height_return */,
    #~ unsigned int*  /* border_width_return */,
    #~ unsigned int*  /* depth_return */
#~ );
XGetGeometry = libX11.XGetGeometry
XGetGeometry.restype = Status
XGetGeometry.argtypes = [POINTER(Display), Drawable, POINTER(Window), POINTER(c_int), POINTER(c_int), POINTER(c_uint), POINTER(c_uint), POINTER(c_uint), POINTER(c_uint)]

#~ extern Status XGetIconName(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ char**    /* icon_name_return */
#~ );
XGetIconName = libX11.XGetIconName
XGetIconName.restype = Status
XGetIconName.argtypes = [POINTER(Display), Window, POINTER(c_char_p)]

#~ extern int XGetInputFocus(
    #~ Display*    /* display */,
    #~ Window*    /* focus_return */,
    #~ int*    /* revert_to_return */
#~ );
XGetInputFocus = libX11.XGetInputFocus
XGetInputFocus.restype = c_int
XGetInputFocus.argtypes = [POINTER(Display), POINTER(Window), POINTER(c_int)]

#~ extern int XGetKeyboardControl(
    #~ Display*    /* display */,
    #~ XKeyboardState*  /* values_return */
#~ );
XGetKeyboardControl = libX11.XGetKeyboardControl
XGetKeyboardControl.restype = c_int
XGetKeyboardControl.argtypes = [POINTER(Display), POINTER(XKeyboardState)]

#~ extern int XGetPointerControl(
    #~ Display*    /* display */,
    #~ int*    /* accel_numerator_return */,
    #~ int*    /* accel_denominator_return */,
    #~ int*    /* threshold_return */
#~ );
XGetPointerControl = libX11.XGetPointerControl
XGetPointerControl.restype = c_int
XGetPointerControl.argtypes = [POINTER(Display), POINTER(c_int), POINTER(c_int), POINTER(c_int)]

#~ extern int XGetPointerMapping(
    #~ Display*    /* display */,
    #~ unsigned char*  /* map_return */,
    #~ int      /* nmap */
#~ );
XGetPointerMapping = libX11.XGetPointerMapping
XGetPointerMapping.restype = c_int
XGetPointerMapping.argtypes = [POINTER(Display), c_char_p, c_int]

#~ extern int XGetScreenSaver(
    #~ Display*    /* display */,
    #~ int*    /* timeout_return */,
    #~ int*    /* interval_return */,
    #~ int*    /* prefer_blanking_return */,
    #~ int*    /* allow_exposures_return */
#~ );
XGetScreenSaver = libX11.XGetScreenSaver
XGetScreenSaver.restype = c_int
XGetScreenSaver.argtypes = [POINTER(Display), POINTER(c_int), POINTER(c_int), POINTER(c_int)]

#~ extern Status XGetTransientForHint(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Window*    /* prop_window_return */
#~ );
XGetTransientForHint = libX11.XGetTransientForHint
XGetTransientForHint.restype = c_int
XGetTransientForHint.argtypes = [POINTER(Display), Window, POINTER(Window)]

#~ extern int XGetWindowProperty(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Atom    /* property */,
    #~ long    /* long_offset */,
    #~ long    /* long_length */,
    #~ Bool    /* delete */,
    #~ Atom    /* req_type */,
    #~ Atom*    /* actual_type_return */,
    #~ int*    /* actual_format_return */,
    #~ unsigned long*  /* nitems_return */,
    #~ unsigned long*  /* bytes_after_return */,
    #~ unsigned char**  /* prop_return */
#~ );
XGetWindowProperty = libX11.XGetWindowProperty
XGetWindowProperty.restype = c_int
XGetWindowProperty.argtypes = [POINTER(Display), Window, Atom, c_long, c_long, Bool, Atom, POINTER(Atom), POINTER(c_int), POINTER(c_long), POINTER(c_long), POINTER(c_char_p)]

#~ extern Status XGetWindowAttributes(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ XWindowAttributes*  /* window_attributes_return */
#~ );
XGetWindowAttributes = libX11.XGetWindowAttributes
XGetWindowAttributes.restype = Status
XGetWindowAttributes.argtypes = [POINTER(Display), Window, POINTER(XWindowAttributes)]

#~ extern int XGrabButton(
    #~ Display*    /* display */,
    #~ unsigned int  /* button */,
    #~ unsigned int  /* modifiers */,
    #~ Window    /* grab_window */,
    #~ Bool    /* owner_events */,
    #~ unsigned int  /* event_mask */,
    #~ int      /* pointer_mode */,
    #~ int      /* keyboard_mode */,
    #~ Window    /* confine_to */,
    #~ Cursor    /* cursor */
#~ );
XGrabButton = libX11.XGrabButton
XGrabButton.restype = c_int
XGrabButton.argtypes = [POINTER(Display), c_uint, c_uint, Window, Bool, c_uint, c_int, c_int, Window, Cursor]

#~ extern int XGrabKey(
    #~ Display*    /* display */,
    #~ int      /* keycode */,
    #~ unsigned int  /* modifiers */,
    #~ Window    /* grab_window */,
    #~ Bool    /* owner_events */,
    #~ int      /* pointer_mode */,
    #~ int      /* keyboard_mode */
#~ );
XGrabKey = libX11.XGrabKey
XGrabKey.restype = c_int
XGrabKey.argtypes = [POINTER(Display), c_int, c_uint, Window, Bool, c_int, c_int]

#~ extern int XGrabKeyboard(
    #~ Display*    /* display */,
    #~ Window    /* grab_window */,
    #~ Bool    /* owner_events */,
    #~ int      /* pointer_mode */,
    #~ int      /* keyboard_mode */,
    #~ Time    /* time */
#~ );
XGrabKeyboard = libX11.XGrabKeyboard
XGrabKeyboard.restype = c_int
XGrabKeyboard.argtypes = [POINTER(Display), Window, Bool, c_int, c_int, Time]

#~ extern int XGrabPointer(
    #~ Display*    /* display */,
    #~ Window    /* grab_window */,
    #~ Bool    /* owner_events */,
    #~ unsigned int  /* event_mask */,
    #~ int      /* pointer_mode */,
    #~ int      /* keyboard_mode */,
    #~ Window    /* confine_to */,
    #~ Cursor    /* cursor */,
    #~ Time    /* time */
#~ );
XGrabPointer = libX11.XGrabPointer
XGrabPointer.restype = c_int
XGrabPointer.argtypes = [POINTER(Display), Window, Bool, c_uint, c_int, c_int, Window, Cursor, Time]

#~ extern int XGrabServer(
    #~ Display*    /* display */
#~ );
XGrabServer = libX11.XGrabServer
XGrabServer.restype = c_int
XGrabServer.argtypes = [POINTER(Display)]

#~ extern int XHeightMMOfScreen(
    #~ Screen*    /* screen */
#~ );
XHeightMMOfScreen = libX11.XHeightMMOfScreen
XHeightMMOfScreen.restype = c_int
XHeightMMOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XHeightOfScreen(
    #~ Screen*    /* screen */
#~ );
XHeightOfScreen = libX11.XHeightOfScreen
XHeightOfScreen.restype = c_int
XHeightOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XIfEvent(
    #~ Display*    /* display */,
    #~ XEvent*    /* event_return */,
    #~ Bool (*) (
         #~ Display*      /* display */,
               #~ XEvent*      /* event */,
               #~ XPointer      /* arg */
             #~ )    /* predicate */,
    #~ XPointer    /* arg */
#~ );
XIfEvent = libX11.XIfEvent
XIfEvent.restype = c_int
XIfEvent.argtypes = [POINTER(Display), XEvent, c_void_p, XPointer]

#~ extern int XImageByteOrder(
    #~ Display*    /* display */
#~ );
XImageByteOrder = libX11.XImageByteOrder
XImageByteOrder.restype = c_int
XImageByteOrder.argtypes = [POINTER(Display)]

#~ extern int XInstallColormap(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */
#~ );
XInstallColormap = libX11.XInstallColormap
XInstallColormap.restype = c_int
XInstallColormap.argtypes = [POINTER(Display), Colormap]

#~ extern KeyCode XKeysymToKeycode(
    #~ Display*    /* display */,
    #~ KeySym    /* keysym */
#~ );
XKeysymToKeycode = libX11.XKeysymToKeycode
XKeysymToKeycode.restype = c_int
XKeysymToKeycode.argtypes = [POINTER(Display), KeySym]

#~ extern int XKillClient(
    #~ Display*    /* display */,
    #~ XID      /* resource */
#~ );
XKillClient = libX11.XKillClient
XKillClient.restype = c_int
XKillClient.argtypes = [POINTER(Display), XID]

#~ extern Status XLookupColor(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ _Xconst char*  /* color_name */,
    #~ XColor*    /* exact_def_return */,
    #~ XColor*    /* screen_def_return */
#~ );
XLookupColor = libX11.XLookupColor
XLookupColor.restype = Status
XLookupColor.argtypes = [POINTER(Display), Colormap, c_char_p, POINTER(XColor), POINTER(XColor)]

#~ extern int XLowerWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XLowerWindow = libX11.XLowerWindow
XLowerWindow.restype = c_int
XLowerWindow.argtypes = [POINTER(Display), Window]

#~ extern int XMapRaised(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XMapRaised = libX11.XMapRaised
XMapRaised.restype = c_int
XMapRaised.argtypes = [POINTER(Display), Window]

#~ extern int XMapSubwindows(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XMapSubwindows = libX11.XMapSubwindows
XMapSubwindows.restype = c_int
XMapSubwindows.argtypes = [POINTER(Display), Window]

#~ extern int XMapWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XMapWindow = libX11.XMapWindow
XMapWindow.restype = c_int
XMapWindow.argtypes = [POINTER(Display), Window]

#~ extern int XMaskEvent(
    #~ Display*    /* display */,
    #~ long    /* event_mask */,
    #~ XEvent*    /* event_return */
#~ );
XMaskEvent = libX11.XMaskEvent
XMaskEvent.restype = c_int
XMaskEvent.argtypes = [POINTER(Display), c_long, POINTER(XEvent)]

#~ extern int XMaxCmapsOfScreen(
    #~ Screen*    /* screen */
#~ );
XMaxCmapsOfScreen = libX11.XMaxCmapsOfScreen
XMaxCmapsOfScreen.restype = c_int
XMaxCmapsOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XMinCmapsOfScreen(
    #~ Screen*    /* screen */
#~ );
XMinCmapsOfScreen = libX11.XMinCmapsOfScreen
XMinCmapsOfScreen.restype = c_int
XMinCmapsOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XMoveResizeWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */
#~ );
XMoveResizeWindow = libX11.XMoveResizeWindow
XMoveResizeWindow.restype = c_int
XMoveResizeWindow.argtypes = [POINTER(Display), Window, c_int, c_int, c_uint, c_uint]

#~ extern int XMoveWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ int      /* x */,
    #~ int      /* y */
#~ );
XMoveWindow = libX11.XMoveWindow
XMoveWindow.restype = c_int
XMoveWindow.argtypes = [POINTER(Display), Window, c_int, c_int]

#~ extern int XNextEvent(
    #~ Display*    /* display */,
    #~ XEvent*    /* event_return */
#~ );
XNextEvent = libX11.XNextEvent
XNextEvent.restype = c_int
XNextEvent.argtypes = [POINTER(Display), POINTER(XEvent)]

#~ extern int XNoOp(
    #~ Display*    /* display */
#~ );
XNoOp = libX11.XNoOp
XNoOp.restype = c_int
XNoOp.argtypes = [POINTER(Display)]

#~ extern Status XParseColor(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ _Xconst char*  /* spec */,
    #~ XColor*    /* exact_def_return */
#~ );
XParseColor = libX11.XParseColor
XParseColor.restype = Status
XParseColor.argtypes = [POINTER(Display), Colormap, c_char_p, POINTER(XColor)]

#~ extern int XParseGeometry(
    #~ _Xconst char*  /* parsestring */,
    #~ int*    /* x_return */,
    #~ int*    /* y_return */,
    #~ unsigned int*  /* width_return */,
    #~ unsigned int*  /* height_return */
#~ );
XParseGeometry = libX11.XParseGeometry
XParseGeometry.restype = c_int
XParseGeometry.argtypes = [c_char_p, POINTER(c_int), POINTER(c_int), POINTER(c_uint), POINTER(c_uint)]

#~ extern int XPeekEvent(
    #~ Display*    /* display */,
    #~ XEvent*    /* event_return */
#~ );
XPeekEvent = libX11.XPeekEvent
XPeekEvent.restype = c_int
XPeekEvent.argtypes = [POINTER(Display), POINTER(XEvent)]

#~ extern int XPeekIfEvent(
    #~ Display*    /* display */,
    #~ XEvent*    /* event_return */,
    #~ Bool (*) (
         #~ Display*    /* display */,
               #~ XEvent*    /* event */,
               #~ XPointer    /* arg */
             #~ )    /* predicate */,
    #~ XPointer    /* arg */
#~ );
XPeekIfEvent = libX11.XPeekIfEvent
XPeekIfEvent.restype = c_int
XPeekIfEvent.argtypes = [POINTER(Display), POINTER(XEvent), c_void_p, XPointer]

#~ extern int XPending(
    #~ Display*    /* display */
#~ );
XPending = libX11.XPending
XPending.restype = c_int
XPending.argtypes = [POINTER(Display)]

#~ extern int XPlanesOfScreen(
    #~ Screen*    /* screen */
#~ );
XPlanesOfScreen = libX11.XPlanesOfScreen
XPlanesOfScreen.restype = c_int
XPlanesOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XProtocolRevision(
    #~ Display*    /* display */
#~ );
XProtocolRevision = libX11.XProtocolRevision
XProtocolRevision.restype = c_int
XProtocolRevision.argtypes = [POINTER(Display)]

#~ extern int XProtocolVersion(
    #~ Display*    /* display */
#~ );
XProtocolVersion = libX11.XProtocolVersion
XProtocolVersion.restype = c_int
XProtocolVersion.argtypes = [POINTER(Display)]

#~ extern int XPutBackEvent(
    #~ Display*    /* display */,
    #~ XEvent*    /* event */
#~ );
XPutBackEvent = libX11.XPutBackEvent
XPutBackEvent.restype = c_int
XPutBackEvent.argtypes = [POINTER(Display), POINTER(XEvent)]

#~ extern int XPutImage(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ XImage*    /* image */,
    #~ int      /* src_x */,
    #~ int      /* src_y */,
    #~ int      /* dest_x */,
    #~ int      /* dest_y */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */
#~ );
XPutImage = libX11.XPutImage
XPutImage.restype = c_int
XPutImage.argtypes = [POINTER(Display), Drawable, GC, POINTER(XImage), c_int, c_int, c_int, c_int, c_uint, c_uint]

#~ extern int XQLength(
    #~ Display*    /* display */
#~ );
XQLength = libX11.XQLength
XQLength.restype = c_int
XQLength.argtypes = [POINTER(Display)]

#~ extern Status XQueryBestCursor(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ unsigned int        /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned int*  /* width_return */,
    #~ unsigned int*  /* height_return */
#~ );
XQueryBestCursor = libX11.XQueryBestCursor
XQueryBestCursor.restype = Status
XQueryBestCursor.argtypes = [POINTER(Display), Drawable, c_uint, c_uint, POINTER(c_uint), POINTER(c_uint)]

#~ extern Status XQueryBestSize(
    #~ Display*    /* display */,
    #~ int      /* class */,
    #~ Drawable    /* which_screen */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned int*  /* width_return */,
    #~ unsigned int*  /* height_return */
#~ );
XQueryBestSize = libX11.XQueryBestSize
XQueryBestSize.restype = Status
XQueryBestSize.argtypes = [POINTER(Display), c_int, Drawable, c_uint, c_uint, POINTER(c_uint), POINTER(c_uint)]

#~ extern Status XQueryBestStipple(
    #~ Display*    /* display */,
    #~ Drawable    /* which_screen */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned int*  /* width_return */,
    #~ unsigned int*  /* height_return */
#~ );
XQueryBestStipple = libX11.XQueryBestStipple
XQueryBestStipple.restype = Status
XQueryBestStipple.argtypes = [POINTER(Display), Drawable, c_uint, c_uint, POINTER(c_uint), POINTER(c_uint)]

#~ extern Status XQueryBestTile(
    #~ Display*    /* display */,
    #~ Drawable    /* which_screen */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ unsigned int*  /* width_return */,
    #~ unsigned int*  /* height_return */
#~ );
XQueryBestTile = libX11.XQueryBestTile
XQueryBestTile.restype = Status
XQueryBestTile.argtypes = [POINTER(Display), Drawable, c_uint, c_uint, POINTER(c_uint), POINTER(c_uint)]

#~ extern int XQueryColor(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ XColor*    /* def_in_out */
#~ );
XQueryColor = libX11.XQueryColor
XQueryColor.restype = c_int
XQueryColor.argtypes = [POINTER(Display), Colormap, POINTER(XColor)]

#~ extern int XQueryColors(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ XColor*    /* defs_in_out */,
    #~ int      /* ncolors */
#~ );
XQueryColors = libX11.XQueryColors
XQueryColors.restype = c_int
XQueryColors.argtypes = [POINTER(Display), Colormap, POINTER(XColor), c_int]

#~ extern Bool XQueryExtension(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* name */,
    #~ int*    /* major_opcode_return */,
    #~ int*    /* first_event_return */,
    #~ int*    /* first_error_return */
#~ );
XQueryExtension = libX11.XQueryExtension
XQueryExtension.restype = Bool
XQueryExtension.argtypes = [POINTER(Display), c_char_p, POINTER(c_int), POINTER(c_int), POINTER(c_int)]

#~ extern int XQueryKeymap(
    #~ Display*    /* display */,
    #~ char [32]    /* keys_return */
#~ );
XQueryKeymap = libX11.XQueryKeymap
XQueryKeymap.restype = c_int
XQueryKeymap.argtypes = [POINTER(Display), c_char * 32]

#~ extern Bool XQueryPointer(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Window*    /* root_return */,
    #~ Window*    /* child_return */,
    #~ int*    /* root_x_return */,
    #~ int*    /* root_y_return */,
    #~ int*    /* win_x_return */,
    #~ int*    /* win_y_return */,
    #~ unsigned int*       /* mask_return */
#~ );
XQueryPointer = libX11.XQueryPointer
XQueryPointer.restype = Bool
XQueryPointer.argtypes = [POINTER(Display), Window, POINTER(Window), POINTER(Window), POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(c_uint)]

#~ extern int XQueryTextExtents(
    #~ Display*    /* display */,
    #~ XID      /* font_ID */,
    #~ _Xconst char*  /* string */,
    #~ int      /* nchars */,
    #~ int*    /* direction_return */,
    #~ int*    /* font_ascent_return */,
    #~ int*    /* font_descent_return */,
    #~ XCharStruct*  /* overall_return */
#~ );
XQueryTextExtents = libX11.XQueryTextExtents
XQueryTextExtents.restype = c_int
XQueryTextExtents.argtypes = [POINTER(Display), XID, c_char_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(XCharStruct)]

#~ extern int XQueryTextExtents16(
    #~ Display*    /* display */,
    #~ XID      /* font_ID */,
    #~ _Xconst XChar2b*  /* string */,
    #~ int      /* nchars */,
    #~ int*    /* direction_return */,
    #~ int*    /* font_ascent_return */,
    #~ int*    /* font_descent_return */,
    #~ XCharStruct*  /* overall_return */
#~ );
XQueryTextExtents16 = libX11.XQueryTextExtents16
XQueryTextExtents16.restype = c_int
XQueryTextExtents16.argtypes = [POINTER(Display), XID, POINTER(XChar2b), c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(XCharStruct)]

#~ extern Status XQueryTree(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Window*    /* root_return */,
    #~ Window*    /* parent_return */,
    #~ Window**    /* children_return */,
    #~ unsigned int*  /* nchildren_return */
#~ );
XQueryTree = libX11.XQueryTree
XQueryTree.restype = Status
XQueryTree.argtypes = [POINTER(Display), Window, POINTER(Window), POINTER(Window), POINTER(POINTER(Window)), POINTER(c_uint)]

#~ extern int XRaiseWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XRaiseWindow = libX11.XRaiseWindow
XRaiseWindow.restype = c_int
XRaiseWindow.argtypes = [POINTER(Display), Window]

#~ extern int XReadBitmapFile(
    #~ Display*    /* display */,
    #~ Drawable     /* d */,
    #~ _Xconst char*  /* filename */,
    #~ unsigned int*  /* width_return */,
    #~ unsigned int*  /* height_return */,
    #~ Pixmap*    /* bitmap_return */,
    #~ int*    /* x_hot_return */,
    #~ int*    /* y_hot_return */
#~ );
XReadBitmapFile = libX11.XReadBitmapFile
XReadBitmapFile.restype = c_int
XReadBitmapFile.argtypes = [POINTER(Display), Drawable, c_char_p, POINTER(c_uint), POINTER(c_uint), POINTER(Pixmap), POINTER(c_int), POINTER(c_int)]

#~ extern int XReadBitmapFileData(
    #~ _Xconst char*  /* filename */,
    #~ unsigned int*  /* width_return */,
    #~ unsigned int*  /* height_return */,
    #~ unsigned char**  /* data_return */,
    #~ int*    /* x_hot_return */,
    #~ int*    /* y_hot_return */
#~ );
XReadBitmapFileData = libX11.XReadBitmapFileData
XReadBitmapFileData.restype = c_int
XReadBitmapFileData.argtypes = [c_char_p, POINTER(c_uint), POINTER(c_uint), POINTER(c_char_p), POINTER(c_int), POINTER(c_int)]

#~ extern int XRebindKeysym(
    #~ Display*    /* display */,
    #~ KeySym    /* keysym */,
    #~ KeySym*    /* list */,
    #~ int      /* mod_count */,
    #~ _Xconst unsigned char*  /* string */,
    #~ int      /* bytes_string */
#~ );
XRebindKeysym = libX11.XRebindKeysym
XRebindKeysym.restype = c_int
XRebindKeysym.argtypes = [POINTER(Display), KeySym, POINTER(KeySym), c_int, c_char_p, c_int]

#~ extern int XRecolorCursor(
    #~ Display*    /* display */,
    #~ Cursor    /* cursor */,
    #~ XColor*    /* foreground_color */,
    #~ XColor*    /* background_color */
#~ );
XRecolorCursor = libX11.XRecolorCursor
XRecolorCursor.restype = c_int
XRecolorCursor.argtypes = [POINTER(Display), Cursor, POINTER(XColor), POINTER(XColor)]

#~ extern int XRefreshKeyboardMapping(
    #~ XMappingEvent*  /* event_map */
#~ );
XRefreshKeyboardMapping = libX11.XRefreshKeyboardMapping
XRefreshKeyboardMapping.restype = c_int
XRefreshKeyboardMapping.argtypes = [POINTER(XMappingEvent)]

#~ extern int XRemoveFromSaveSet(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XRemoveFromSaveSet = libX11.XRemoveFromSaveSet
XRemoveFromSaveSet.restype = c_int
XRemoveFromSaveSet.argtypes = [POINTER(Display), Window]

#~ extern int XRemoveHost(
    #~ Display*    /* display */,
    #~ XHostAddress*  /* host */
#~ );
XRemoveHost = libX11.XRemoveHost
XRemoveHost.restype = c_int
XRemoveHost.argtypes = [POINTER(Display), POINTER(XHostAddress)]

#~ extern int XRemoveHosts(
    #~ Display*    /* display */,
    #~ XHostAddress*  /* hosts */,
    #~ int      /* num_hosts */
#~ );
XRemoveHosts = libX11.XRemoveHosts
XRemoveHosts.restype = c_int
XRemoveHosts.argtypes = [POINTER(Display), POINTER(XHostAddress), c_int]

#~ extern int XReparentWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Window    /* parent */,
    #~ int      /* x */,
    #~ int      /* y */
#~ );
XReparentWindow = libX11.XReparentWindow
XReparentWindow.restype = c_int
XReparentWindow.argtypes = [POINTER(Display), Window, Window, c_int, c_int]

#~ extern int XResetScreenSaver(
    #~ Display*    /* display */
#~ );
XResetScreenSaver = libX11.XResetScreenSaver
XResetScreenSaver.restype = c_int
XResetScreenSaver.argtypes = [POINTER(Display)]

#~ extern int XResizeWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */
#~ );
XResizeWindow = libX11.XResizeWindow
XResizeWindow.restype = c_int
XResizeWindow.argtypes = [POINTER(Display), Window, c_uint, c_uint]

#~ extern int XRestackWindows(
    #~ Display*    /* display */,
    #~ Window*    /* windows */,
    #~ int      /* nwindows */
#~ );
XRestackWindows = libX11.XRestackWindows
XRestackWindows.restype = c_int
XRestackWindows.argtypes = [POINTER(Display), POINTER(Window), c_int]

#~ extern int XRotateBuffers(
    #~ Display*    /* display */,
    #~ int      /* rotate */
#~ );
XRotateBuffers = libX11.XRotateBuffers
XRotateBuffers.restype = c_int
XRotateBuffers.argtypes = [POINTER(Display), c_int]

#~ extern int XRotateWindowProperties(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Atom*    /* properties */,
    #~ int      /* num_prop */,
    #~ int      /* npositions */
#~ );
XRotateWindowProperties = libX11.XRotateWindowProperties
XRotateWindowProperties.restype = c_int
XRotateWindowProperties.argtypes = [POINTER(Display), Window, POINTER(Atom), c_int, c_int]

#~ extern int XScreenCount(
    #~ Display*    /* display */
#~ );
XScreenCount = libX11.XScreenCount
XScreenCount.restype = c_int
XScreenCount.argtypes = [POINTER(Display)]

#~ extern int XSelectInput(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ long    /* event_mask */
#~ );
XSelectInput = libX11.XSelectInput
XSelectInput.restype = c_int
XSelectInput.argtypes = [POINTER(Display), Window, c_long]

#~ extern Status XSendEvent(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Bool    /* propagate */,
    #~ long    /* event_mask */,
    #~ XEvent*    /* event_send */
#~ );
XSendEvent = libX11.XSendEvent
XSendEvent.restype = Status
XSendEvent.argtypes = [POINTER(Display), Window, Bool, c_long, POINTER(XEvent)]

#~ extern int XSetAccessControl(
    #~ Display*    /* display */,
    #~ int      /* mode */
#~ );
XSetAccessControl = libX11.XSetAccessControl
XSetAccessControl.restype = c_int
XSetAccessControl.argtypes = [POINTER(Display), c_int]

#~ extern int XSetArcMode(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* arc_mode */
#~ );
XSetArcMode = libX11.XSetArcMode
XSetArcMode.restype = c_int
XSetArcMode.argtypes = [POINTER(Display), GC, c_int]

#~ extern int XSetBackground(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ unsigned long  /* background */
#~ );
XSetBackground = libX11.XSetBackground
XSetBackground.restype = c_int
XSetBackground.argtypes = [POINTER(Display), GC, c_ulong]

#~ extern int XSetClipMask(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ Pixmap    /* pixmap */
#~ );
XSetClipMask = libX11.XSetClipMask
XSetClipMask.restype = c_int
XSetClipMask.argtypes = [POINTER(Display), GC, Pixmap]

#~ extern int XSetClipOrigin(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* clip_x_origin */,
    #~ int      /* clip_y_origin */
#~ );
XSetClipOrigin = libX11.XSetClipOrigin
XSetClipOrigin.restype = c_int
XSetClipOrigin.argtypes = [POINTER(Display), GC, c_int, c_int]

#~ extern int XSetClipRectangles(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* clip_x_origin */,
    #~ int      /* clip_y_origin */,
    #~ XRectangle*    /* rectangles */,
    #~ int      /* n */,
    #~ int      /* ordering */
#~ );
XSetClipRectangles = libX11.XSetClipRectangles
XSetClipRectangles.restype = c_int
XSetClipRectangles.argtypes = [POINTER(Display), GC, c_int, c_int, POINTER(XRectangle), c_int, c_int]

#~ extern int XSetCloseDownMode(
    #~ Display*    /* display */,
    #~ int      /* close_mode */
#~ );
XSetCloseDownMode = libX11.XSetCloseDownMode
XSetCloseDownMode.restype = c_int
XSetCloseDownMode.argtypes = [POINTER(Display), c_int]

#~ extern int XSetCommand(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ char**    /* argv */,
    #~ int      /* argc */
#~ );
XSetCommand = libX11.XSetCommand
XSetCommand.restype = c_int
XSetCommand.argtypes = [POINTER(Display), Window, POINTER(c_char_p), c_int]

#~ extern int XSetDashes(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* dash_offset */,
    #~ _Xconst char*  /* dash_list */,
    #~ int      /* n */
#~ );
XSetDashes = libX11.XSetDashes
XSetDashes.restype = c_int
XSetDashes.argtypes = [POINTER(Display), GC, c_int, c_char_p, c_int]

#~ extern int XSetFillRule(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* fill_rule */
#~ );
XSetFillRule = libX11.XSetFillRule
XSetFillRule.restype = c_int
XSetFillRule.argtypes = [POINTER(Display), GC, c_int]

#~ extern int XSetFillStyle(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* fill_style */
#~ );
XSetFillStyle = libX11.XSetFillStyle
XSetFillStyle.restype = c_int
XSetFillStyle.argtypes = [POINTER(Display), GC, c_int]

#~ extern int XSetFont(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ Font    /* font */
#~ );
XSetFont = libX11.XSetFont
XSetFont.restype = c_int
XSetFont.argtypes = [POINTER(Display), GC, Font]

#~ extern int XSetFontPath(
    #~ Display*    /* display */,
    #~ char**    /* directories */,
    #~ int      /* ndirs */
#~ );
XSetFontPath = libX11.XSetFontPath
XSetFontPath.restype = c_int
XSetFontPath.argtypes = [POINTER(Display), POINTER(c_char_p), c_int]

#~ extern int XSetForeground(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ unsigned long  /* foreground */
#~ );
XSetForeground = libX11.XSetForeground
XSetForeground.restype = c_int
XSetForeground.argtypes = [POINTER(Display), GC, c_ulong]

#~ extern int XSetFunction(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* function */
#~ );
XSetFunction = libX11.XSetFunction
XSetFunction.restype = c_int
XSetFunction.argtypes = [POINTER(Display), GC, c_int]

#~ extern int XSetGraphicsExposures(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ Bool    /* graphics_exposures */
#~ );
XSetGraphicsExposures = libX11.XSetGraphicsExposures
XSetGraphicsExposures.restype = c_int
XSetGraphicsExposures.argtypes = [POINTER(Display), GC, Bool]

#~ extern int XSetIconName(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ _Xconst char*  /* icon_name */
#~ );
XSetIconName = libX11.XSetIconName
XSetIconName.restype = c_int
XSetIconName.argtypes = [POINTER(Display), Window, c_char_p]

#~ extern int XSetInputFocus(
    #~ Display*    /* display */,
    #~ Window    /* focus */,
    #~ int      /* revert_to */,
    #~ Time    /* time */
#~ );
XSetInputFocus = libX11.XSetInputFocus
XSetInputFocus.restype = c_int
XSetInputFocus.argtypes = [POINTER(Display), Window, c_int, Time]

#~ extern int XSetLineAttributes(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ unsigned int  /* line_width */,
    #~ int      /* line_style */,
    #~ int      /* cap_style */,
    #~ int      /* join_style */
#~ );
XSetLineAttributes = libX11.XSetLineAttributes
XSetLineAttributes.restype = c_int
XSetLineAttributes.argtypes = [POINTER(Display), GC, c_uint, c_int, c_int, c_int]

#~ extern int XSetModifierMapping(
    #~ Display*    /* display */,
    #~ XModifierKeymap*  /* modmap */
#~ );
XSetModifierMapping = libX11.XSetModifierMapping
XSetModifierMapping.restype = c_int
XSetModifierMapping.argtypes = [POINTER(Display), POINTER(XModifierKeymap)]

#~ extern int XSetPlaneMask(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ unsigned long  /* plane_mask */
#~ );
XSetPlaneMask = libX11.XSetPlaneMask
XSetPlaneMask.restype = c_int
XSetPlaneMask.argtypes = [POINTER(Display), GC, c_ulong]

#~ extern int XSetPointerMapping(
    #~ Display*    /* display */,
    #~ _Xconst unsigned char*  /* map */,
    #~ int      /* nmap */
#~ );
XSetPointerMapping = libX11.XSetPointerMapping
XSetPointerMapping.restype = c_int
XSetPointerMapping.argtypes = [POINTER(Display), c_char_p, c_int]

#~ extern int XSetScreenSaver(
    #~ Display*    /* display */,
    #~ int      /* timeout */,
    #~ int      /* interval */,
    #~ int      /* prefer_blanking */,
    #~ int      /* allow_exposures */
#~ );
XSetScreenSaver = libX11.XSetScreenSaver
XSetScreenSaver.restype = c_int
XSetScreenSaver.argtypes = [POINTER(Display), c_int, c_int, c_int, c_int]

#~ extern int XSetSelectionOwner(
    #~ Display*    /* display */,
    #~ Atom          /* selection */,
    #~ Window    /* owner */,
    #~ Time    /* time */
#~ );
XSetSelectionOwner = libX11.XSetSelectionOwner
XSetSelectionOwner.restype = c_int
XSetSelectionOwner.argtypes = [POINTER(Display), Atom, Window, Time]

#~ extern int XSetState(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ unsigned long   /* foreground */,
    #~ unsigned long  /* background */,
    #~ int      /* function */,
    #~ unsigned long  /* plane_mask */
#~ );
XSetState = libX11.XSetState
XSetState.restype = c_int
XSetState.argtypes = [POINTER(Display), GC, c_ulong, c_ulong, c_int, c_ulong]

#~ extern int XSetStipple(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ Pixmap    /* stipple */
#~ );
XSetStipple = libX11.XSetStipple
XSetStipple.restype = c_int
XSetStipple.argtypes = [POINTER(Display), GC, Pixmap]

#~ extern int XSetSubwindowMode(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* subwindow_mode */
#~ );
XSetSubwindowMode = libX11.XSetSubwindowMode
XSetSubwindowMode.restype = c_int
XSetSubwindowMode.argtypes = [POINTER(Display), GC, c_int]

#~ extern int XSetTSOrigin(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ int      /* ts_x_origin */,
    #~ int      /* ts_y_origin */
#~ );
XSetTSOrigin = libX11.XSetTSOrigin
XSetTSOrigin.restype = c_int
XSetTSOrigin.argtypes = [POINTER(Display), GC, c_int, c_int]

#~ extern int XSetTile(
    #~ Display*    /* display */,
    #~ GC      /* gc */,
    #~ Pixmap    /* tile */
#~ );
XSetTile = libX11.XSetTile
XSetTile.restype = c_int
XSetTile.argtypes = [POINTER(Display), GC, Pixmap]

#~ extern int XSetWindowBackground(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ unsigned long  /* background_pixel */
#~ );
XSetWindowBackground = libX11.XSetWindowBackground
XSetWindowBackground.restype = c_int
XSetWindowBackground.argtypes = [POINTER(Display), Window, c_ulong]

#~ extern int XSetWindowBackgroundPixmap(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Pixmap    /* background_pixmap */
#~ );
XSetWindowBackgroundPixmap = libX11.XSetWindowBackgroundPixmap
XSetWindowBackgroundPixmap.restype = c_int
XSetWindowBackgroundPixmap.argtypes = [POINTER(Display), Window, Pixmap]

#~ extern int XSetWindowBorder(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ unsigned long  /* border_pixel */
#~ );
XSetWindowBorder = libX11.XSetWindowBorder
XSetWindowBorder.restype = c_int
XSetWindowBorder.argtypes = [POINTER(Display), Window, c_ulong]

#~ extern int XSetWindowBorderPixmap(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Pixmap    /* border_pixmap */
#~ );
XSetWindowBorderPixmap = libX11.XSetWindowBorderPixmap
XSetWindowBorderPixmap.restype = c_int
XSetWindowBorderPixmap.argtypes = [POINTER(Display), Window, Pixmap]

#~ extern int XSetWindowBorderWidth(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ unsigned int  /* width */
#~ );
XSetWindowBorderWidth = libX11.XSetWindowBorderWidth
XSetWindowBorderWidth.restype = c_int
XSetWindowBorderWidth.argtypes = [POINTER(Display), Window, c_uint]

#~ extern int XSetWindowColormap(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ Colormap    /* colormap */
#~ );
XSetWindowColormap = libX11.XSetWindowColormap
XSetWindowColormap.restype = c_int
XSetWindowColormap.argtypes = [POINTER(Display), Window, Colormap]

#~ extern int XStoreBuffer(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* bytes */,
    #~ int      /* nbytes */,
    #~ int      /* buffer */
#~ );
XStoreBuffer = libX11.XStoreBuffer
XStoreBuffer.restype = c_int
XStoreBuffer.argtypes = [POINTER(Display), c_char_p, c_int, c_int]

#~ extern int XStoreBytes(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* bytes */,
    #~ int      /* nbytes */
#~ );
XStoreBytes = libX11.XStoreBytes
XStoreBytes.restype = c_int
XStoreBytes.argtypes = [POINTER(Display), c_char_p, c_int]

#~ extern int XStoreColor(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ XColor*    /* color */
#~ );
XStoreColor = libX11.XStoreColor
XStoreColor.restype = c_int
XStoreColor.argtypes = [POINTER(Display), Colormap, POINTER(XColor)]

#~ extern int XStoreColors(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ XColor*    /* color */,
    #~ int      /* ncolors */
#~ );
XStoreColors = libX11.XStoreColors
XStoreColors.restype = c_int
XStoreColors.argtypes = [POINTER(Display), Colormap, POINTER(XColor), c_int]

#~ extern int XStoreName(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ _Xconst char*  /* window_name */
#~ );
XStoreName = libX11.XStoreName
XStoreName.restype = c_int
XStoreName.argtypes = [POINTER(Display), Window, c_char_p]

#~ extern int XStoreNamedColor(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */,
    #~ _Xconst char*  /* color */,
    #~ unsigned long  /* pixel */,
    #~ int      /* flags */
#~ );
XStoreNamedColor = libX11.XStoreNamedColor
XStoreNamedColor.restype = c_int
XStoreNamedColor.argtypes = [POINTER(Display), Colormap, c_char_p, c_ulong, c_int]

#~ extern int XSync(
    #~ Display*    /* display */,
    #~ Bool    /* discard */
#~ );
XSync = libX11.XSync
XSync.restype = c_int
XSync.argtypes = [POINTER(Display), Bool]

#~ extern int XTextExtents(
    #~ XFontStruct*  /* font_struct */,
    #~ _Xconst char*  /* string */,
    #~ int      /* nchars */,
    #~ int*    /* direction_return */,
    #~ int*    /* font_ascent_return */,
    #~ int*    /* font_descent_return */,
    #~ XCharStruct*  /* overall_return */
#~ );
XTextExtents = libX11.XTextExtents
XTextExtents.restype = c_int
XTextExtents.argtypes = [POINTER(XFontStruct), c_char_p, c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(XCharStruct)]

#~ extern int XTextExtents16(
    #~ XFontStruct*  /* font_struct */,
    #~ _Xconst XChar2b*  /* string */,
    #~ int      /* nchars */,
    #~ int*    /* direction_return */,
    #~ int*    /* font_ascent_return */,
    #~ int*    /* font_descent_return */,
    #~ XCharStruct*  /* overall_return */
#~ );
XTextExtents16 = libX11.XTextExtents16
XTextExtents16.restype = c_int
XTextExtents16.argtypes = [POINTER(XFontStruct), POINTER(XChar2b), c_int, POINTER(c_int), POINTER(c_int), POINTER(c_int), POINTER(XCharStruct)]

#~ extern int XTextWidth(
    #~ XFontStruct*  /* font_struct */,
    #~ _Xconst char*  /* string */,
    #~ int      /* count */
#~ );
XTextWidth = libX11.XTextWidth
XTextWidth.restype = c_int
XTextWidth.argtypes = [POINTER(XFontStruct),  c_char_p, c_int]

#~ extern int XTextWidth16(
    #~ XFontStruct*  /* font_struct */,
    #~ _Xconst XChar2b*  /* string */,
    #~ int      /* count */
#~ );
XTextWidth16 = libX11.XTextWidth16
XTextWidth16.restype = c_int
XTextWidth16.argtypes = [POINTER(XFontStruct), POINTER(XChar2b), c_int]

#~ extern Bool XTranslateCoordinates(
    #~ Display*    /* display */,
    #~ Window    /* src_w */,
    #~ Window    /* dest_w */,
    #~ int      /* src_x */,
    #~ int      /* src_y */,
    #~ int*    /* dest_x_return */,
    #~ int*    /* dest_y_return */,
    #~ Window*    /* child_return */
#~ );
XTranslateCoordinates = libX11.XTranslateCoordinates
XTranslateCoordinates.restype = Bool
XTranslateCoordinates.argtypes = [POINTER(Display), Window, Window, c_int, c_int, POINTER(c_int), POINTER(c_int), POINTER(Window)]

#~ extern int XUndefineCursor(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XUndefineCursor = libX11.XUndefineCursor
XUndefineCursor.restype = c_int
XUndefineCursor.argtypes = [POINTER(Display), Window]

#~ extern int XUngrabButton(
    #~ Display*    /* display */,
    #~ unsigned int  /* button */,
    #~ unsigned int  /* modifiers */,
    #~ Window    /* grab_window */
#~ );
XUngrabButton = libX11.XUngrabButton
XUngrabButton.restype = c_int
XUngrabButton.argtypes = [POINTER(Display), c_uint, c_uint, Window]

#~ extern int XUngrabKey(
    #~ Display*    /* display */,
    #~ int      /* keycode */,
    #~ unsigned int  /* modifiers */,
    #~ Window    /* grab_window */
#~ );
XUngrabKey = libX11.XUngrabKey
XUngrabKey.restype = c_int
XUngrabKey.argtypes = [POINTER(Display), c_int, c_uint, Window]

#~ extern int XUngrabKeyboard(
    #~ Display*    /* display */,
    #~ Time    /* time */
#~ );
XUngrabKeyboard = libX11.XUngrabKeyboard
XUngrabKeyboard.restype = c_int
XUngrabKeyboard.argtypes = [POINTER(Display), Time]

#~ extern int XUngrabPointer(
    #~ Display*    /* display */,
    #~ Time    /* time */
#~ );
XUngrabPointer = libX11.XUngrabPointer
XUngrabPointer.restype = c_int
XUngrabPointer.argtypes = [POINTER(Display), Time]

#~ extern int XUngrabServer(
    #~ Display*    /* display */
#~ );
XUngrabServer = libX11.XUngrabServer
XUngrabServer.restype = c_int
XUngrabServer.argtypes = [POINTER(Display)]

#~ extern int XUninstallColormap(
    #~ Display*    /* display */,
    #~ Colormap    /* colormap */
#~ );
XUninstallColormap = libX11.XUninstallColormap
XUninstallColormap.restype = c_int
XUninstallColormap.argtypes = [POINTER(Display), Colormap]

#~ extern int XUnloadFont(
    #~ Display*    /* display */,
    #~ Font    /* font */
#~ );
XUnloadFont = libX11.XUnloadFont
XUnloadFont.restype = c_int
XUnloadFont.argtypes = [POINTER(Display), Font]

#~ extern int XUnmapSubwindows(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XUnmapSubwindows = libX11.XUnmapSubwindows
XUnmapSubwindows.restype = c_int
XUnmapSubwindows.argtypes = [POINTER(Display), Window]

#~ extern int XUnmapWindow(
    #~ Display*    /* display */,
    #~ Window    /* w */
#~ );
XUnmapWindow = libX11.XUnmapWindow
XUnmapWindow.restype = c_int
XUnmapWindow.argtypes = [POINTER(Display), Window]

#~ extern int XVendorRelease(
    #~ Display*    /* display */
#~ );
XVendorRelease = libX11.XVendorRelease
XVendorRelease.restype = c_int
XVendorRelease.argtypes = [POINTER(Display)]

#~ extern int XWarpPointer(
    #~ Display*    /* display */,
    #~ Window    /* src_w */,
    #~ Window    /* dest_w */,
    #~ int      /* src_x */,
    #~ int      /* src_y */,
    #~ unsigned int  /* src_width */,
    #~ unsigned int  /* src_height */,
    #~ int      /* dest_x */,
    #~ int      /* dest_y */
#~ );
XWarpPointer = libX11.XWarpPointer
XWarpPointer.restype = c_int
XWarpPointer.argtypes = [POINTER(Display), Window, Window, c_int, c_int, c_uint, c_uint, c_int, c_int]

#~ extern int XWidthMMOfScreen(
    #~ Screen*    /* screen */
#~ );
XWidthMMOfScreen = libX11.XWidthMMOfScreen
XWidthMMOfScreen.restype = c_int
XWidthMMOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XWidthOfScreen(
    #~ Screen*    /* screen */
#~ );
XWidthOfScreen = libX11.XWidthOfScreen
XWidthOfScreen.restype = c_int
XWidthOfScreen.argtypes = [POINTER(Screen)]

#~ extern int XWindowEvent(
    #~ Display*    /* display */,
    #~ Window    /* w */,
    #~ long    /* event_mask */,
    #~ XEvent*    /* event_return */
#~ );
XWindowEvent = libX11.XWindowEvent
XWindowEvent.restype = c_int
XWindowEvent.argtypes = [POINTER(Display), Window, c_long, POINTER(XEvent)]

#~ extern int XWriteBitmapFile(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* filename */,
    #~ Pixmap    /* bitmap */,
    #~ unsigned int  /* width */,
    #~ unsigned int  /* height */,
    #~ int      /* x_hot */,
    #~ int      /* y_hot */
#~ );
XWriteBitmapFile = libX11.XWriteBitmapFile
XWriteBitmapFile.restype = c_int
XWriteBitmapFile.argtypes = [POINTER(Display), c_char_p, Pixmap, c_uint, c_uint, c_int, c_int]

#~ extern Bool XSupportsLocale (void);
XSupportsLocale = libX11.XSupportsLocale
XSupportsLocale.restype = Bool
XSupportsLocale.argtypes = []

#~ extern char *XSetLocaleModifiers(
    #~ const char*    /* modifier_list */
#~ );
XSetLocaleModifiers = libX11.XSetLocaleModifiers
XSetLocaleModifiers.restype = c_char_p
XSetLocaleModifiers.argtypes = [c_char_p]

#~ extern XOM XOpenOM(
    #~ Display*      /* display */,
    #~ struct _XrmHashBucketRec*  /* rdb */,
    #~ _Xconst char*    /* res_name */,
    #~ _Xconst char*    /* res_class */
#~ );
XOpenOM = libX11.XOpenOM
XOpenOM.restype = XOM
XOpenOM.argtypes = [POINTER(Display), POINTER(_XrmHashBucketRec), c_char_p, c_char_p]

#~ extern Status XCloseOM(
    #~ XOM      /* om */
#~ );
XCloseOM = libX11.XCloseOM
XCloseOM.restype = Status
XCloseOM.argtypes = [XOM]

#~ extern char *XSetOMValues(
    #~ XOM      /* om */,
    #~ ...
#~ ) _X_SENTINEL(0);
XSetOMValues = libX11.XSetOMValues
XSetOMValues.restype = c_char_p
XSetOMValues.argtypes = [XOM]

#~ extern char *XGetOMValues(
    #~ XOM      /* om */,
    #~ ...
#~ ) _X_SENTINEL(0);
XGetOMValues = libX11.XGetOMValues
XGetOMValues.restype = c_char_p
XGetOMValues.argtypes = [XOM]

#~ extern Display *XDisplayOfOM(
    #~ XOM      /* om */
#~ );
XDisplayOfOM = libX11.XDisplayOfOM
XDisplayOfOM.restype = Display
XDisplayOfOM.argtypes = [XOM]

#~ extern char *XLocaleOfOM(
    #~ XOM      /* om */
#~ );
XLocaleOfOM = libX11.XLocaleOfOM
XLocaleOfOM.restype = c_char_p
XLocaleOfOM.argtypes = [XOM]

#~ extern XOC XCreateOC(
    #~ XOM      /* om */,
    #~ ...
#~ ) _X_SENTINEL(0);
XCreateOC = libX11.XCreateOC
XCreateOC.restype = XOC
XCreateOC.argtypes = [XOM]

#~ extern void XDestroyOC(
    #~ XOC      /* oc */
#~ );
XDestroyOC = libX11.XDestroyOC
XDestroyOC.argtypes = [XOC]

#~ extern XOM XOMOfOC(
    #~ XOC      /* oc */
#~ );
XOMOfOC = libX11.XOMOfOC
XOMOfOC.restype = XOM
XOMOfOC.argtypes = [XOC]

#~ extern char *XSetOCValues(
    #~ XOC      /* oc */,
    #~ ...
#~ ) _X_SENTINEL(0);
XSetOCValues = libX11.XSetOCValues
XSetOCValues.restype = c_char_p
XSetOCValues.argtypes = [XOC]

#~ extern char *XGetOCValues(
    #~ XOC      /* oc */,
    #~ ...
#~ ) _X_SENTINEL(0);
XGetOCValues = libX11.XGetOCValues
XGetOCValues.restype = c_char_p
XGetOCValues.argtypes = [XOC]

#~ extern XFontSet XCreateFontSet(
    #~ Display*    /* display */,
    #~ _Xconst char*  /* base_font_name_list */,
    #~ char***    /* missing_charset_list */,
    #~ int*    /* missing_charset_count */,
    #~ char**    /* def_string */
#~ );
XCreateFontSet = libX11.XCreateFontSet
XCreateFontSet.restype = XFontSet
XCreateFontSet.argtypes = [POINTER(Display), c_char_p, POINTER(POINTER(c_char_p)), POINTER(c_int), POINTER(c_char_p)]

#~ extern void XFreeFontSet(
    #~ Display*    /* display */,
    #~ XFontSet    /* font_set */
#~ );
XFreeFontSet = libX11.XFreeFontSet
XFreeFontSet.argtypes = [POINTER(Display), XFontSet]

#~ extern int XFontsOfFontSet(
    #~ XFontSet    /* font_set */,
    #~ XFontStruct***  /* font_struct_list */,
    #~ char***    /* font_name_list */
#~ );
XFontsOfFontSet = libX11.XFontsOfFontSet
XFontsOfFontSet.restype = c_int
XFontsOfFontSet.argtypes = [XFontSet, POINTER(POINTER(POINTER(XFontStruct))), POINTER(POINTER(c_char_p))]

#~ extern char *XBaseFontNameListOfFontSet(
    #~ XFontSet    /* font_set */
#~ );
XBaseFontNameListOfFontSet = libX11.XBaseFontNameListOfFontSet
XBaseFontNameListOfFontSet.restype = c_char_p
XBaseFontNameListOfFontSet.argtypes = [XFontSet]

#~ extern char *XLocaleOfFontSet(
    #~ XFontSet    /* font_set */
#~ );
XLocaleOfFontSet = libX11.XLocaleOfFontSet
XLocaleOfFontSet.restype = c_char_p
XLocaleOfFontSet.argtypes = [XFontSet]

#~ extern Bool XContextDependentDrawing(
    #~ XFontSet    /* font_set */
#~ );
XContextDependentDrawing = libX11.XContextDependentDrawing
XContextDependentDrawing.restype = Bool
XContextDependentDrawing.argtypes = [XFontSet]

#~ extern Bool XDirectionalDependentDrawing(
    #~ XFontSet    /* font_set */
#~ );
XDirectionalDependentDrawing = libX11.XDirectionalDependentDrawing
XDirectionalDependentDrawing.restype = Bool
XDirectionalDependentDrawing.argtypes = [XFontSet]

#~ extern Bool XContextualDrawing(
    #~ XFontSet    /* font_set */
#~ );
XContextualDrawing = libX11.XContextualDrawing
XContextualDrawing.restype = Bool
XContextualDrawing.argtypes = [XFontSet]

#~ extern XFontSetExtents *XExtentsOfFontSet(
    #~ XFontSet    /* font_set */
#~ );
XExtentsOfFontSet = libX11.XExtentsOfFontSet
XExtentsOfFontSet.restype = POINTER(XFontSetExtents)
XExtentsOfFontSet.argtypes = [XFontSet]

#~ extern int XmbTextEscapement(
    #~ XFontSet    /* font_set */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */
#~ );
XmbTextEscapement = libX11.XmbTextEscapement
XmbTextEscapement.restype = c_int
XmbTextEscapement.argtypes = [XFontSet, c_char_p, c_int]

#~ extern int XwcTextEscapement(
    #~ XFontSet    /* font_set */,
    #~ _Xconst wchar_t*  /* text */,
    #~ int      /* num_wchars */
#~ );
XwcTextEscapement = libX11.XwcTextEscapement
XwcTextEscapement.restype = c_int
XwcTextEscapement.argtypes = [XFontSet, c_char_p, c_int]

#~ extern int Xutf8TextEscapement(
    #~ XFontSet    /* font_set */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */
#~ );
Xutf8TextEscapement = libX11.Xutf8TextEscapement
Xutf8TextEscapement.restype = c_int
Xutf8TextEscapement.argtypes = [XFontSet, c_char_p, c_int]

#~ extern int XmbTextExtents(
    #~ XFontSet    /* font_set */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */,
    #~ XRectangle*    /* overall_ink_return */,
    #~ XRectangle*    /* overall_logical_return */
#~ );
XmbTextExtents = libX11.XmbTextExtents
XmbTextExtents.restype = c_int
XmbTextExtents.argtypes = [XFontSet, c_char_p, c_int, POINTER(XRectangle), POINTER(XRectangle)]

#~ extern int XwcTextExtents(
    #~ XFontSet    /* font_set */,
    #~ _Xconst wchar_t*  /* text */,
    #~ int      /* num_wchars */,
    #~ XRectangle*    /* overall_ink_return */,
    #~ XRectangle*    /* overall_logical_return */
#~ );
XwcTextExtents = libX11.XwcTextExtents
XwcTextExtents.restype = c_int
XwcTextExtents.argtypes = [XFontSet, c_wchar_p, c_int, POINTER(XRectangle), POINTER(XRectangle)]

#~ extern int Xutf8TextExtents(
    #~ XFontSet    /* font_set */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */,
    #~ XRectangle*    /* overall_ink_return */,
    #~ XRectangle*    /* overall_logical_return */
#~ );
Xutf8TextExtents = libX11.Xutf8TextExtents
Xutf8TextExtents.restype = c_int
Xutf8TextExtents.argtypes = [XFontSet, c_char_p, c_int, POINTER(XRectangle), POINTER(XRectangle)]

#~ extern Status XmbTextPerCharExtents(
    #~ XFontSet    /* font_set */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */,
    #~ XRectangle*    /* ink_extents_buffer */,
    #~ XRectangle*    /* logical_extents_buffer */,
    #~ int      /* buffer_size */,
    #~ int*    /* num_chars */,
    #~ XRectangle*    /* overall_ink_return */,
    #~ XRectangle*    /* overall_logical_return */
#~ );
XmbTextPerCharExtents = libX11.XmbTextPerCharExtents
XmbTextPerCharExtents.restype = Status
XmbTextPerCharExtents.argtypes = [XFontSet, c_char_p, c_int, POINTER(XRectangle), POINTER(XRectangle), c_int, POINTER(c_int), POINTER(XRectangle), POINTER(XRectangle)]

#~ extern Status XwcTextPerCharExtents(
    #~ XFontSet    /* font_set */,
    #~ _Xconst wchar_t*  /* text */,
    #~ int      /* num_wchars */,
    #~ XRectangle*    /* ink_extents_buffer */,
    #~ XRectangle*    /* logical_extents_buffer */,
    #~ int      /* buffer_size */,
    #~ int*    /* num_chars */,
    #~ XRectangle*    /* overall_ink_return */,
    #~ XRectangle*    /* overall_logical_return */
#~ );
XwcTextPerCharExtents = libX11.XwcTextPerCharExtents
XwcTextPerCharExtents.restype = Status
XwcTextPerCharExtents.argtypes = [XFontSet, c_wchar_p, c_int, POINTER(XRectangle), POINTER(XRectangle), c_int, POINTER(c_int), POINTER(XRectangle), POINTER(XRectangle)]

#~ extern Status Xutf8TextPerCharExtents(
    #~ XFontSet    /* font_set */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */,
    #~ XRectangle*    /* ink_extents_buffer */,
    #~ XRectangle*    /* logical_extents_buffer */,
    #~ int      /* buffer_size */,
    #~ int*    /* num_chars */,
    #~ XRectangle*    /* overall_ink_return */,
    #~ XRectangle*    /* overall_logical_return */
#~ );
Xutf8TextPerCharExtents = libX11.Xutf8TextPerCharExtents
Xutf8TextPerCharExtents.restype = Status
Xutf8TextPerCharExtents.argtypes = [XFontSet, c_char_p, c_int, POINTER(XRectangle), POINTER(XRectangle), c_int, POINTER(c_int), POINTER(XRectangle), POINTER(XRectangle)]

#~ extern void XmbDrawText(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ XmbTextItem*  /* text_items */,
    #~ int      /* nitems */
#~ );
XmbDrawText = libX11.XmbDrawText
XmbDrawText.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, POINTER(XmbTextItem), c_int]

#~ extern void XwcDrawText(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ XwcTextItem*  /* text_items */,
    #~ int      /* nitems */
#~ );
XwcDrawText = libX11.XwcDrawText
XwcDrawText.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, POINTER(XwcTextItem), c_int]

#~ extern void Xutf8DrawText(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ XmbTextItem*  /* text_items */,
    #~ int      /* nitems */
#~ );
Xutf8DrawText = libX11.Xutf8DrawText
Xutf8DrawText.argtypes = [POINTER(Display), Drawable, GC, c_int, c_int, POINTER(XmbTextItem), c_int]

#~ extern void XmbDrawString(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ XFontSet    /* font_set */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */
#~ );
XmbDrawString = libX11.XmbDrawString
XmbDrawString.argtypes = [POINTER(Display), Drawable, XFontSet, GC, c_int, c_int, c_char_p, c_int]

#~ extern void XwcDrawString(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ XFontSet    /* font_set */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst wchar_t*  /* text */,
    #~ int      /* num_wchars */
#~ );
XwcDrawString = libX11.XwcDrawString
XwcDrawString.argtypes = [POINTER(Display), Drawable, XFontSet, GC, c_int, c_int, c_wchar_p, c_int]

#~ extern void Xutf8DrawString(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ XFontSet    /* font_set */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */
#~ );
Xutf8DrawString = libX11.Xutf8DrawString
Xutf8DrawString.argtypes = [POINTER(Display), Drawable, XFontSet, GC, c_int, c_int, c_char_p, c_int]

#~ extern void XmbDrawImageString(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ XFontSet    /* font_set */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */
#~ );
XmbDrawImageString = libX11.XmbDrawImageString
XmbDrawImageString.argtypes = [POINTER(Display), Drawable, XFontSet, GC, c_int, c_int, c_char_p, c_int]

#~ extern void XwcDrawImageString(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ XFontSet    /* font_set */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst wchar_t*  /* text */,
    #~ int      /* num_wchars */
#~ );
XwcDrawImageString = libX11.XwcDrawImageString
XwcDrawImageString.argtypes = [POINTER(Display), Drawable, XFontSet, GC, c_int, c_int, c_wchar_p, c_int]

#~ extern void Xutf8DrawImageString(
    #~ Display*    /* display */,
    #~ Drawable    /* d */,
    #~ XFontSet    /* font_set */,
    #~ GC      /* gc */,
    #~ int      /* x */,
    #~ int      /* y */,
    #~ _Xconst char*  /* text */,
    #~ int      /* bytes_text */
#~ );
Xutf8DrawImageString = libX11.Xutf8DrawImageString
Xutf8DrawImageString.argtypes = [POINTER(Display), Drawable, XFontSet, GC, c_int, c_int, c_char_p, c_int]

#~ extern XIM XOpenIM(
    #~ Display*      /* dpy */,
    #~ struct _XrmHashBucketRec*  /* rdb */,
    #~ char*      /* res_name */,
    #~ char*      /* res_class */
#~ );
XOpenIM = libX11.XOpenIM
XOpenIM.restype = XIM
XOpenIM.argtypes = [POINTER(Display), POINTER(_XrmHashBucketRec), c_char_p, c_char_p]

#~ extern Status XCloseIM(
    #~ XIM /* im */
#~ );
XCloseIM = libX11.XCloseIM
XCloseIM.restype = Status
XCloseIM.argtypes = [XIM]

#~ extern char *XGetIMValues(
    #~ XIM /* im */, ...
#~ ) _X_SENTINEL(0);
XGetIMValues = libX11.XGetIMValues
XGetIMValues.restype = c_char_p
XGetIMValues.argtypes = [XIM]

#~ extern char *XSetIMValues(
    #~ XIM /* im */, ...
#~ ) _X_SENTINEL(0);
XSetIMValues = libX11.XSetIMValues
XSetIMValues.restype = c_char_p
XSetIMValues.argtypes = [XIM]

#~ extern Display *XDisplayOfIM(
    #~ XIM /* im */
#~ );
XDisplayOfIM = libX11.XDisplayOfIM
XDisplayOfIM.restype = POINTER(Display)
XDisplayOfIM.argtypes = [XIM]

#~ extern char *XLocaleOfIM(
    #~ XIM /* im*/
#~ );
XLocaleOfIM = libX11.XLocaleOfIM
XLocaleOfIM.restype = c_char_p
XLocaleOfIM.argtypes = [XIM]

#~ extern XIC XCreateIC(
    #~ XIM /* im */, ...
#~ ) _X_SENTINEL(0);
XCreateIC = libX11.XCreateIC
XCreateIC.restype = XIC
XCreateIC.argtypes = [XIM]

#~ extern void XDestroyIC(
    #~ XIC /* ic */
#~ );
XDestroyIC = libX11.XDestroyIC
XDestroyIC.argtypes = [XIC]

#~ extern void XSetICFocus(
    #~ XIC /* ic */
#~ );
XSetICFocus = libX11.XSetICFocus
XSetICFocus.argtypes = [XIC]

#~ extern void XUnsetICFocus(
    #~ XIC /* ic */
#~ );
XUnsetICFocus = libX11.XUnsetICFocus
XUnsetICFocus.argtypes = [XIC]

#~ extern wchar_t *XwcResetIC(
    #~ XIC /* ic */
#~ );
XwcResetIC = libX11.XwcResetIC
XwcResetIC.restype = c_wchar_p
XwcResetIC.argtypes = [XIC]

#~ extern char *XmbResetIC(
    #~ XIC /* ic */
#~ );
XmbResetIC = libX11.XmbResetIC
XmbResetIC.restype = c_char_p
XmbResetIC.argtypes = [XIC]

#~ extern char *Xutf8ResetIC(
    #~ XIC /* ic */
#~ );
Xutf8ResetIC = libX11.Xutf8ResetIC
Xutf8ResetIC.restype = c_char_p
Xutf8ResetIC.argtypes = [XIC]

#~ extern char *XSetICValues(
    #~ XIC /* ic */, ...
#~ ) _X_SENTINEL(0);
XSetICValues = libX11.XSetICValues
XSetICValues.restype = c_char_p
XSetICValues.argtypes = [XIC]

#~ extern char *XGetICValues(
    #~ XIC /* ic */, ...
#~ ) _X_SENTINEL(0);
XGetICValues = libX11.XGetICValues
XGetICValues.restype = c_char_p
XGetICValues.argtypes = [XIC]

#~ extern XIM XIMOfIC(
    #~ XIC /* ic */
#~ );
XIMOfIC = libX11.XIMOfIC
XIMOfIC.restype = XIM
XIMOfIC.argtypes = [XIC]

#~ extern Bool XFilterEvent(
    #~ XEvent*  /* event */,
    #~ Window  /* window */
#~ );
XFilterEvent = libX11.XFilterEvent
XFilterEvent.restype = Bool
XFilterEvent.argtypes = [POINTER(XEvent), Window]

#~ extern int XmbLookupString(
    #~ XIC      /* ic */,
    #~ XKeyPressedEvent*  /* event */,
    #~ char*    /* buffer_return */,
    #~ int      /* bytes_buffer */,
    #~ KeySym*    /* keysym_return */,
    #~ Status*    /* status_return */
#~ );
XmbLookupString = libX11.XmbLookupString
XmbLookupString.restype = c_int
XmbLookupString.argtypes = [XIC, POINTER(XKeyPressedEvent), c_char_p, c_int, POINTER(KeySym), POINTER(Status)]

#~ extern int XwcLookupString(
    #~ XIC      /* ic */,
    #~ XKeyPressedEvent*  /* event */,
    #~ wchar_t*    /* buffer_return */,
    #~ int      /* wchars_buffer */,
    #~ KeySym*    /* keysym_return */,
    #~ Status*    /* status_return */
#~ );
XwcLookupString = libX11.XwcLookupString
XwcLookupString.restype = c_int
XwcLookupString.argtypes = [XIC, POINTER(XKeyPressedEvent), c_wchar_p, c_int, POINTER(KeySym), POINTER(Status)]

#~ extern int Xutf8LookupString(
    #~ XIC      /* ic */,
    #~ XKeyPressedEvent*  /* event */,
    #~ char*    /* buffer_return */,
    #~ int      /* bytes_buffer */,
    #~ KeySym*    /* keysym_return */,
    #~ Status*    /* status_return */
#~ );
Xutf8LookupString = libX11.Xutf8LookupString
Xutf8LookupString.restype = c_int
Xutf8LookupString.argtypes = [XIC, POINTER(XKeyPressedEvent), c_char_p, c_int, POINTER(KeySym), POINTER(Status)]

#~ extern XVaNestedList XVaCreateNestedList(
    #~ int /*unused*/, ...
#~ ) _X_SENTINEL(0);
XVaCreateNestedList = libX11.XVaCreateNestedList
XVaCreateNestedList.restype = XVaNestedList
XVaCreateNestedList.argtypes = [c_int]

#~ /* internal connections for IMs */

#~ extern Bool XRegisterIMInstantiateCallback(
    #~ Display*      /* dpy */,
    #~ struct _XrmHashBucketRec*  /* rdb */,
    #~ char*      /* res_name */,
    #~ char*      /* res_class */,
    #~ XIDProc      /* callback */,
    #~ XPointer      /* client_data */
#~ );
XRegisterIMInstantiateCallback = libX11.XRegisterIMInstantiateCallback
XRegisterIMInstantiateCallback.restype = Bool
XRegisterIMInstantiateCallback.argtypes = [POINTER(Display), POINTER(_XrmHashBucketRec), c_char_p, c_char_p, XIDProc, XPointer]

#~ extern Bool XUnregisterIMInstantiateCallback(
    #~ Display*      /* dpy */,
    #~ struct _XrmHashBucketRec*  /* rdb */,
    #~ char*      /* res_name */,
    #~ char*      /* res_class */,
    #~ XIDProc      /* callback */,
    #~ XPointer      /* client_data */
#~ );
XUnregisterIMInstantiateCallback = libX11.XUnregisterIMInstantiateCallback
XUnregisterIMInstantiateCallback.restype = Bool
XUnregisterIMInstantiateCallback.argtypes = [POINTER(Display), POINTER(_XrmHashBucketRec), c_char_p, c_char_p, XIDProc, XPointer]

#~ typedef void (*XConnectionWatchProc)(
    #~ Display*      /* dpy */,
    #~ XPointer      /* client_data */,
    #~ int        /* fd */,
    #~ Bool      /* opening */,   /* open or close flag */
    #~ XPointer*      /* watch_data */ /* open sets, close uses */
#~ );
XConnectionWatchProc = c_void_p

#~ extern Status XInternalConnectionNumbers(
    #~ Display*      /* dpy */,
    #~ int**      /* fd_return */,
    #~ int*      /* count_return */
#~ );
XInternalConnectionNumbers = libX11.XInternalConnectionNumbers
XInternalConnectionNumbers.restype = Status
XInternalConnectionNumbers.argtypes = [POINTER(Display), POINTER(POINTER(c_int)), POINTER(c_int)]

#~ extern void XProcessInternalConnection(
    #~ Display*      /* dpy */,
    #~ int        /* fd */
#~ );
XProcessInternalConnection = libX11.XProcessInternalConnection
XProcessInternalConnection.argtypes = [POINTER(Display), c_int]

#~ extern Status XAddConnectionWatch(
    #~ Display*      /* dpy */,
    #~ XConnectionWatchProc  /* callback */,
    #~ XPointer      /* client_data */
#~ );
XAddConnectionWatch = libX11.XAddConnectionWatch
XAddConnectionWatch.restype = Status
XAddConnectionWatch.argtypes = [POINTER(Display), XConnectionWatchProc, XPointer]

#~ extern void XRemoveConnectionWatch(
    #~ Display*      /* dpy */,
    #~ XConnectionWatchProc  /* callback */,
    #~ XPointer      /* client_data */
#~ );
XRemoveConnectionWatch = libX11.XRemoveConnectionWatch
XRemoveConnectionWatch.argtypes = [POINTER(Display), XConnectionWatchProc, XPointer]

#~ extern void XSetAuthorization(
    #~ char *      /* name */,
    #~ int        /* namelen */,
    #~ char *      /* data */,
    #~ int        /* datalen */
#~ );
XSetAuthorization = libX11.XSetAuthorization
XSetAuthorization.argtypes = [c_char_p, c_int, c_char_p, c_int]

#~ extern int _Xmbtowc(
    #~ wchar_t *      /* wstr */,
#~ #ifdef ISC
    #~ char const *    /* str */,
    #~ size_t      /* len */
#~ #else
    #~ char *      /* str */,
    #~ int        /* len */
#~ #endif
#~ );
_Xmbtowc = libX11._Xmbtowc
_Xmbtowc.restype = c_int
_Xmbtowc.argtypes = [c_wchar_p, c_char_p, c_ulong]

#~ extern int _Xwctomb(
    #~ char *      /* str */,
    #~ wchar_t      /* wc */
#~ );
_Xwctomb = libX11._Xwctomb
_Xwctomb.restype = c_int
_Xwctomb.argtypes = [c_char_p, c_wchar]

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2013 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.3.0"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result)
        # This is a bit ugly, but it avoids running this again.
        delattr(tp, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(types.ModuleType):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    ####### following two added
    MovedModule("urllib_parse", "urllib", "urllib.parse"),
    MovedModule("urllib_request", "urllib", "urllib.request"),
    #######
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
del attr

moves = sys.modules[__name__ + ".moves"] = _MovedItems("moves")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

########NEW FILE########
__FILENAME__ = Test
import unittest

from pi3d.loader.parse_mtl_test import ParseMtlTest

def test_suite():
  suite = unittest.TestLoader().loadTestsFromTestCase(ParseMtlTest)
  return suite

if __name__ == '__main__':
  unittest.TextTestRunner().run(test_suite())

########NEW FILE########
__FILENAME__ = TestKeyboard
import sys

from pi3d import Keyboard

USE_CURSES = len(sys.argv) == 1 or sys.argv[1] == 'yes' or sys.argv[1] == 'true'

if USE_CURSES:
  print 'Using curses keyboard'
else:
  print 'Using system keyboard'

keyboard = Keyboard.Keyboard(use_curses=USE_CURSES)

while True:
  ch = keyboard.read()
  if ch > 0:
    print(ch, chr(ch))
    if ch == 17:
      break

########NEW FILE########
