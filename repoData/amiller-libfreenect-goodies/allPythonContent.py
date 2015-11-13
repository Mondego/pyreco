__FILENAME__ = calibkinect
"""
These are some functions to help work with kinect camera calibration and projective
geometry. 

Tasks:
- Convert the kinect depth image to a metric 3D point cloud
- Convert the 3D point cloud to texture coordinates in the RGB image

Notes about the coordinate systems:
 There are three coordinate systems to worry about. 
 1. Kinect depth image:
    u,v,depth
    u and v are image coordinates, (0,0) is the top left corner of the image
                               (640,480) is the bottom right corner of the image
    depth is the raw 11-bit image from the kinect, where 0 is infinitely far away
      and larger numbers are closer to the camera
      (2047 indicates an error pixel)
      
 2. Kinect rgb image:
    u,v
    u and v are image coordinates (0,0) is the top left corner
                              (640,480) is the bottom right corner
                              
 3. XYZ world coordinates:
    x,y,z
    The 3D world coordinates, in meters, relative to the depth camera. 
    (0,0,0) is the camera center. 
    Negative Z values are in front of the camera, and the positive Z direction points
       towards the camera. 
    The X axis points to the right, and the Y axis points up. This is the standard 
       right-handed coordinate system used by OpenGL.
    

"""
import numpy as np


def depth2xyzuv(depth, u=None, v=None):
  """
  Return a point cloud, an Nx3 array, made by projecting the kinect depth map 
    through intrinsic / extrinsic calibration matrices
  Parameters:
    depth - comes directly from the kinect 
    u,v - are image coordinates, same size as depth (default is the original image)
  Returns:
    xyz - 3D world coordinates in meters (Nx3)
    uv - image coordinates for the RGB image (Nx3)
  
  You can provide only a portion of the depth image, or a downsampled version of
    the depth image if you want; just make sure to provide the correct coordinates
    in the u,v arguments. 
    
  Example:
    # This downsamples the depth image by 2 and then projects to metric point cloud
    u,v = mgrid[:480:2,:640:2]
    xyz,uv = depth2xyzuv(freenect.sync_get_depth()[::2,::2], u, v)
    
    # This projects only a small region of interest in the upper corner of the depth image
    u,v = mgrid[10:120,50:80]
    xyz,uv = depth2xyzuv(freenect.sync_get_depth()[v,u], u, v)
  """
  if u is None or v is None:
    u,v = np.mgrid[:480,:640]
  
  # Build a 3xN matrix of the d,u,v data
  C = np.vstack((u.flatten(), v.flatten(), depth.flatten(), 0*u.flatten()+1))

  # Project the duv matrix into xyz using xyz_matrix()
  X,Y,Z,W = np.dot(xyz_matrix(),C)
  X,Y,Z = X/W, Y/W, Z/W
  xyz = np.vstack((X,Y,Z)).transpose()
  xyz = xyz[Z<0,:]

  # Project the duv matrix into U,V rgb coordinates using rgb_matrix() and xyz_matrix()
  U,V,_,W = np.dot(np.dot(uv_matrix(), xyz_matrix()),C)
  U,V = U/W, V/W
  uv = np.vstack((U,V)).transpose()    
  uv = uv[Z<0,:]       

  # Return both the XYZ coordinates and the UV coordinates
  return xyz, uv



def uv_matrix():
  """
  Returns a matrix you can use to project XYZ coordinates (in meters) into
      U,V coordinates in the kinect RGB image
  """
  rot = np.array([[ 9.99846e-01,   -1.26353e-03,   1.74872e-02], 
                  [-1.4779096e-03, -9.999238e-01,  1.225138e-02],
                  [1.747042e-02,   -1.227534e-02,  -9.99772e-01]])
  trans = np.array([[1.9985e-02, -7.44237e-04,-1.0916736e-02]])
  m = np.hstack((rot, -trans.transpose()))
  m = np.vstack((m, np.array([[0,0,0,1]])))
  KK = np.array([[529.2, 0, 329, 0],
                 [0, 525.6, 267.5, 0],
                 [0, 0, 0, 1],
                 [0, 0, 1, 0]])
  m = np.dot(KK, (m))
  return m

def xyz_matrix():
  fx = 594.21
  fy = 591.04
  a = -0.0030711
  b = 3.3309495
  cx = 339.5
  cy = 242.7
  mat = np.array([[1/fx, 0, 0, -cx/fx],
                  [0, -1/fy, 0, cy/fy],
                  [0,   0, 0,    -1],
                  [0,   0, a,     b]])
  return mat
########NEW FILE########
__FILENAME__ = demo_freenect
#!/usr/bin/env python
from freenect import sync_get_depth as get_depth, sync_get_video as get_video
import cv  
import numpy as np
  
def doloop():
    global depth, rgb
    while True:
        # Get a fresh frame
        (depth,_), (rgb,_) = get_depth(), get_video()
        
        # Build a two panel color image
        d3 = np.dstack((depth,depth,depth)).astype(np.uint8)
        da = np.hstack((d3,rgb))
        
        # Simple Downsample
        cv.ShowImage('both',np.array(da[::2,::2,::-1]))
        cv.WaitKey(5)
        
doloop()

"""
IPython usage:
 ipython
 [1]: run -i demo_freenect
 #<ctrl -c>  (to interrupt the loop)
 [2]: %timeit -n100 get_depth(), get_rgb() # profile the kinect capture

"""


########NEW FILE########
__FILENAME__ = demo_pclview
import pykinectwindow as wxwindow
import numpy as np
import pylab
from OpenGL.GL import *
from OpenGL.GLU import *
import time
import freenect
import calibkinect


# I probably need more help with these!
try: 
  TEXTURE_TARGET = GL_TEXTURE_RECTANGLE
except:
  TEXTURE_TARGET = GL_TEXTURE_RECTANGLE_ARB


if not 'win' in globals(): win = wxwindow.Window(size=(640,480))

def refresh(): win.Refresh()

if not 'rotangles' in globals(): rotangles = [0,0]
if not 'zoomdist' in globals(): zoomdist = 1
if not 'projpts' in globals(): projpts = (None, None)
if not 'rgb' in globals(): rgb = None

def create_texture():
  global rgbtex
  rgbtex = glGenTextures(1)
  glBindTexture(TEXTURE_TARGET, rgbtex)
  glTexImage2D(TEXTURE_TARGET,0,GL_RGB,640,480,0,GL_RGB,GL_UNSIGNED_BYTE,None)


if not '_mpos' in globals(): _mpos = None
@win.eventx
def EVT_LEFT_DOWN(event):
  global _mpos
  _mpos = event.Position
  
@win.eventx
def EVT_LEFT_UP(event):
  global _mpos
  _mpos = None
  
@win.eventx
def EVT_MOTION(event):
  global _mpos
  if event.LeftIsDown():
    if _mpos:
      (x,y),(mx,my) = event.Position,_mpos
      rotangles[0] += y-my
      rotangles[1] += x-mx
      refresh()    
    _mpos = event.Position


@win.eventx
def EVT_MOUSEWHEEL(event):
  global zoomdist
  dy = event.WheelRotation
  zoomdist *= np.power(0.95, -dy)
  refresh()
  

clearcolor = [0,0,0,0]
@win.event
def on_draw():  
  if not 'rgbtex' in globals():
    create_texture()

  xyz, uv = projpts
  if xyz is None: return

  if not rgb is None:
    rgb_ = (rgb.astype(np.float32) * 4 + 70).clip(0,255).astype(np.uint8)
    glBindTexture(TEXTURE_TARGET, rgbtex)
    glTexSubImage2D(TEXTURE_TARGET, 0, 0, 0, 640, 480, GL_RGB, GL_UNSIGNED_BYTE, rgb_);

  glClearColor(*clearcolor)
  glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
  glEnable(GL_DEPTH_TEST)

  # flush that stack in case it's broken from earlier
  glPushMatrix()

  glMatrixMode(GL_PROJECTION)
  glLoadIdentity()
  gluPerspective(60, 4/3., 0.3, 200)

  glMatrixMode(GL_MODELVIEW)
  glLoadIdentity()

  def mouse_rotate(xAngle, yAngle, zAngle):
    glRotatef(xAngle, 1.0, 0.0, 0.0);
    glRotatef(yAngle, 0.0, 1.0, 0.0);
    glRotatef(zAngle, 0.0, 0.0, 1.0);
  glScale(zoomdist,zoomdist,1)
  glTranslate(0, 0,-3.5)
  mouse_rotate(rotangles[0], rotangles[1], 0);
  glTranslate(0,0,1.5)
  #glTranslate(0, 0,-1)

  # Draw some axes
  if 0:
    glBegin(GL_LINES)
    glColor3f(1,0,0); glVertex3f(0,0,0); glVertex3f(1,0,0)
    glColor3f(0,1,0); glVertex3f(0,0,0); glVertex3f(0,1,0)
    glColor3f(0,0,1); glVertex3f(0,0,0); glVertex3f(0,0,1)
    glEnd()

  # We can either project the points ourselves, or embed it in the opengl matrix
  if 0:
    dec = 4
    v,u = mgrid[:480,:640].astype(np.uint16)
    points = np.vstack((u[::dec,::dec].flatten(),
                        v[::dec,::dec].flatten(),
                        depth[::dec,::dec].flatten())).transpose()
    points = points[points[:,2]<2047,:]
    
    glMatrixMode(GL_TEXTURE)
    glLoadIdentity()
    glMultMatrixf(calibkinect.uv_matrix().transpose())
    glMultMatrixf(calibkinect.xyz_matrix().transpose())
    glTexCoordPointers(np.array(points))
    
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glMultMatrixf(calibkinect.xyz_matrix().transpose())
    glVertexPointers(np.array(points))
  else:
    glMatrixMode(GL_TEXTURE)
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glVertexPointerf(xyz)
    glTexCoordPointerf(uv)

  # Draw the points
  glPointSize(2)
  glEnableClientState(GL_VERTEX_ARRAY)
  glEnableClientState(GL_TEXTURE_COORD_ARRAY)
  glEnable(TEXTURE_TARGET)
  glColor3f(1,1,1)
  glDrawElementsui(GL_POINTS, np.array(range(xyz.shape[0])))
  glDisableClientState(GL_VERTEX_ARRAY)
  glDisableClientState(GL_TEXTURE_COORD_ARRAY)
  glDisable(TEXTURE_TARGET)
  glPopMatrix()

  #
  if 0:
      inds = np.nonzero(xyz[:,2]>-0.55)
      glPointSize(10)
      glColor3f(0,1,1)
      glEnableClientState(GL_VERTEX_ARRAY)
      glDrawElementsui(GL_POINTS, np.array(inds))
      glDisableClientState(GL_VERTEX_ARRAY)

  if 0:
      # Draw only the points in the near plane
      glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
      glEnable(GL_BLEND)
      glColor(0.9,0.9,1.0,0.8)
      glPushMatrix()
      glTranslate(0,0,-0.55)
      glScale(0.6,0.6,1)
      glBegin(GL_QUADS)
      glVertex3f(-1,-1,0); glVertex3f( 1,-1,0);
      glVertex3f( 1, 1,0); glVertex3f(-1, 1,0);
      glEnd()
      glPopMatrix()
      glDisable(GL_BLEND)

  glPopMatrix()


# A silly loop that shows you can busy the ipython thread while opengl runs
def playcolors():
  while 1:
    global clearcolor
    clearcolor = [np.random.random(),0,0,0]
    time.sleep(0.1)
    refresh()

# Update the point cloud from the shell or from a background thread!

def update(dt=0):
  global projpts, rgb, depth
  depth,_ = freenect.sync_get_depth()
  rgb,_ = freenect.sync_get_video()
  q = depth
  X,Y = np.meshgrid(range(640),range(480))
  # YOU CAN CHANGE THIS AND RERUN THE PROGRAM!
  # Point cloud downsampling
  d = 4
  projpts = calibkinect.depth2xyzuv(q[::d,::d],X[::d,::d],Y[::d,::d])
  refresh()
  
def update_join():
  update_on()
  try:
    _thread.join()
  except:
    update_off()
  
def update_on():
  global _updating
  if not '_updating' in globals(): _updating = False
  if _updating: return
  
  _updating = True
  from threading import Thread
  global _thread
  def _run():
    while _updating:
      update()
  _thread = Thread(target=_run)
  _thread.start()
  
def update_off():
  global _updating
  _updating = False
  
  
# Get frames in a loop and display with opencv
def loopcv():
  import cv
  while 1:
    cv.ShowImage('hi',get_depth().astype(np.uint8))
    cv.WaitKey(10)

update() 
#update_on()





########NEW FILE########
__FILENAME__ = pykinectwindow
# This module requires IPython to work! It is meant to be used from an IPython environment with: 
#   ipython -wthread and -pylab
# See demo_pykinect.py for an example

import wx
from wx import glcanvas
from OpenGL.GL import *

# Get the app ourselves so we can attach it to each window
if not '__myapp' in wx.__dict__:
  wx.__myapp = wx.PySimpleApp()
app = wx.__myapp

class Window(wx.Frame):
  
    # wx events can be put in directly
    def eventx(self, target):
        def wrapper(*args, **kwargs):
          target(*args, **kwargs)
        self.canvas.Bind(wx.__dict__[target.__name__], wrapper)
  
    # Events special to this class, just add them this way
    def event(self, target):
        def wrapper(*args, **kwargs):
          target(*args, **kwargs)   
        self.__dict__[target.__name__] = wrapper
        
    def _wrap(self, name, *args, **kwargs):
      try:
        self.__getattribute__(name)
      except AttributeError:
        pass
      else:
        self.__getattribute__(name)(*args, **kwargs)
            

    def __init__(self, title='WxWindow', id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE,
                 name='frame'):
                 
        style = wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE

        super(Window,self).__init__(None, id, title, pos, size, style, name)

        attribList = (glcanvas.WX_GL_RGBA, # RGBA
                      glcanvas.WX_GL_DOUBLEBUFFER, # Double Buffered
                      glcanvas.WX_GL_DEPTH_SIZE, 24) # 24 bit
              
        self.canvas = glcanvas.GLCanvas(self, attribList=attribList)

        self.canvas.Bind(wx.EVT_ERASE_BACKGROUND, self.processEraseBackgroundEvent)
        self.canvas.Bind(wx.EVT_SIZE, self.processSizeEvent)
        self.canvas.Bind(wx.EVT_PAINT, self.processPaintEvent)
        self.Show()

    def processEraseBackgroundEvent(self, event):
        """Process the erase background event."""
        pass # Do nothing, to avoid flashing on MSWin

    def processSizeEvent(self, event):
        """Process the resize event."""
        if self.canvas.GetContext():
            # Make sure the frame is shown before calling SetCurrent.
            #self.Show()
            self.canvas.SetCurrent()
            size = self.GetClientSize()
            self.OnReshape(size.width, size.height)
            #self.canvas.Refresh(False)
        event.Skip()

    def processPaintEvent(self, event=None):
        """Process the drawing event."""
        self.canvas.SetCurrent()
        self._wrap('on_draw')
        self.canvas.SwapBuffers()
        if event: event.Skip()

    def OnReshape(self, width, height):
        """Reshape the OpenGL viewport based on the dimensions of the window."""
        glViewport(0, 0, width, height)
########NEW FILE########
