__FILENAME__ = app
# app.py
# Chris Barker
# CMU S13 15-112 Term Project

import Tkinter
from Tkinter import N, E, S, W, ALL, BOTH

class App(object):
    """ docstring """
    def __init__(self, width=750, height=500, name='App', bg_color = '#000000'):
        (self.width, self.height) = width, height
        self.name = name
        
        self.clock = 0
        self.dragging = False
        self.drag_val = (0,0)
        self.prev_mouse = (0,0)
        self.bg_color = bgColor

        self.create_window()
        self.bind_events()
        self.init_wrapper()
        self.timer_wrapper()
        
        self.root.mainloop()
        
    def create_window(self):
        self.root = Tkinter.Tk()
        self.root.title(self.name)
        self.canvas = Tkinter.Canvas(self.root, width=self.width,
                                     height=self.height, background=self.bg_color)
        self.canvas.pack(expand=True, fill=BOTH)
        
    def unbind_all(self):
        for event, tag in self.bindings:
            self.root.unbind(event, tag)
        self.bindings = [ ]
        
    def quit(self):
        self.unbind_all()
        self.canvas.after_cancel(self.after)
        self.root.quit()
        
    def bind_events(self):
        self.bindings = [ ('<Button-1>', self.mouse_pressed_wrapper),
            ('<KeyPress>', self.key_pressed_wrapper),
            ('<KeyRelease>', self.key_released_wrapper),
            ('<ButtonRelease-1>', self.mouse_pressed_wrapper),
            ('<B1-Motion>', self.mouse_moved_wrapper),
        ]
        
        for i in xrange(len(self.bindings)):
            event = self.bindings[i][0]
            fn = self.bindings[i][1]
            # Store the binding as the event name and the Tkinter tag
            self.bindings[i] = (event, self.root.bind(event, fn))
            
    def init_wrapper(self):
        self.delay = 20
        self.init()
    def init(self): pass
    
    def timer_fired(self): pass
    def timer_wrapper(self):
        self.redraw_all_wrapper()
        self.timer_fired()
        self.clock += 1
        self.after = self.canvas.after(self.delay, lambda: self.timer_wrapper())
    
    def redraw_all(self): pass
    def redraw_all_wrapper(self):
        self.redraw_all()

    def key_pressed(self, event): pass        
    def key_pressed_wrapper(self, event):
        if event.keysym == 'Escape':
            if hasattr(self, 'cube'):
                if self.cube.help_state != self.cube.INGAME:
                    self.cube.help_state = self.cube.INGAME
                    self.cube.redraw()
                    return
            self.quit()
        else:
            self.key_pressed(event)
            if hasattr(self, 'inCam'):
                if self.in_cam:
                    print event.keysym
            self.redraw_all_wrapper()

    def key_released(self, event): pass
    def key_released_wrapper(self, event):
        self.key_released(event)
        self.redraw_all_wrapper()
        
    def mouse_pressed(self, event): pass
    def mouse_pressed_wrapper(self, event):
        self.dragging = True
        #self.dragVal = (0,0)
        self.prev_mouse = (event.x, event.y)
        self.mouse_pressed(event)

    def mouse_moved(self, event): pass
    def mouse_moved_wrapper(self, event):
        ndx = self.drag_val[0] if abs(self.drag_val[0]) > abs(event.x-self.prev_mouse[0]) else (event.x-self.prev_mouse[0])
        ndy = self.drag_val[1] if abs(self.drag_val[1]) > abs(event.y-self.prev_mouse[1]) else (event.y-self.prev_mouse[1])
        self.drag_val = (ndx, ndy)
        self.prev_mouse = (event.x, event.y)
        self.mouse_moved(event)

    def mouse_released(self, event): pass
    def mouse_released_wrapper(self, event):
        self.mouse_released(event)
        self.dragging = False

    def __str__(self):
        return 'App object size %sx%s' % (self.width, self.height)

########NEW FILE########
__FILENAME__ = color
#
#
# This module is provided as a sample with OpenCV
# I did not write any of it
#
#
# This is provided in the OpenCV-2.4.4 release
# Go here for OpenCV downloads: http://opencv.org/downloads.html
#
#


#/usr/bin/env python

'''
This sample demonstrates Canny edge detection.

Usage:
  edge.py [<video source>]

  Trackbars control edge thresholds.

'''

import cv2
import sys


if __name__ == '__main__':
    print __doc__

    try: fn = sys.argv[1]
    except: fn = 0

    def nothing(*arg):
        pass

    cv2.namedWindow('edge')
    cv2.createTrackbar('thrs1', 'edge', 2000, 5000, nothing)
    cv2.createTrackbar('thrs2', 'edge', 4000, 5000, nothing)

def create_capture(source = 0):
    '''source: <int> or '<int>|<filename>|synth [:<param_name>=<value> [:...]]'
    '''
    source = str(source).strip()
    chunks = source.split(':')
    # hanlde drive letter ('c:', ...)
    if len(chunks) > 1 and len(chunks[0]) == 1 and chunks[0].isalpha():
        chunks[1] = chunks[0] + ':' + chunks[1]
        del chunks[0]

    source = chunks[0]
    
    # Source is 0
    
    try: source = int(source)
    except ValueError: pass
    params = dict( s.split('=') for s in chunks[1:] )

    cap = None
    if source == 'synth':
        Class = classes.get(params.get('class', None), VideoSynthBase)
        try: cap = Class(**params)
        except: pass
    else:
        # Here is where the actual Video Capture is created
        cap = cv2.VideoCapture(source)
        if 'size' in params:
            w, h = map(int, params['size'].split('x'))
            cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, h)
    if cap is None or not cap.isOpened():
        print 'Warning: unable to open video source: ', source
        if fallback is not None:
            return create_capture(fallback, None)
    return cap

    cap = create_capture(fn)
    while True:
        flag, img = cap.read()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thrs1 = cv2.getTrackbarPos('thrs1', 'edge')
        thrs2 = cv2.getTrackbarPos('thrs2', 'edge')
        edge = cv2.Canny(gray, thrs1, thrs2, apertureSize=5)
        vis = img.copy()
        vis /= 2
        vis[edge != 0] = (0, 255, 0)
        cv2.imshow('edge', vis)
        ch = cv2.waitKey(5)
        if ch == 27:
            break
    cv2.destroyAllWindows()


########NEW FILE########
__FILENAME__ = coloranalytics
# coloranalytics.py
# Chris Barker
# CMU S13 15-112 Term Project

from math import e

class Profile(object):
    def __init__(self, color, meanSat, meanHue, meanVal, meanSqSat, meanSqHue, meanSqVal):
        self.color = color
        self.meanSat = meanSat
        self.meanHue = meanHue
        self.meanVal = meanVal
        self.meanSqSat = meanSqSat
        self.meanSqHue = meanSqHue
        self.meanSqVal = meanSqVal

    def probability(self, h, s, v, hOff):
        h -= hOff
        hWeight = float(self.meanSqSat) / (max(self.meanSqHue, 1))
        vWeight = float(self.meanSqVal) / (max(self.meanSqVal, 1))
        sWeight = 1.

        weightSum = hWeight + sWeight + vWeight
        hWeight = hWeight / weightSum
        sWeight = sWeight / weightSum
        vWeight = vWeight / weightSum

        hWeight = 1.
        sWeight = vWeight = 0.

        devsH = ((h - self.meanHue) ** 2) / max(1., self.meanSqHue)
        devsS = ((s - self.meanSat) ** 2) / max(1., self.meanSqSat)
        devsV = ((v - self.meanVal) ** 2) / max(1., self.meanSqVal)

        prob = 0
        prob += hWeight * (e ** (-abs(devsH)))
        prob += sWeight * (e ** (-abs(devsS)))
        prob += vWeight * (e ** (-abs(devsV)))

        return prob

class Profiles(object):
    def __init__(self):
        with open('coloranalytics.txt') as file:
            data = eval(file.read())

        self.colorProfiles = [ ]
        self.hueOffset = 0
        self.rgbOffset = (0,0,0)

        for color in data:
            profile = [ ]
            profile.append(color)
            sats = [i[0] for i in data[color]]
            hues = [i[1] for i in data[color]]
            vals = [i[2] for i in data[color]]

            meanSat = float(sum(sats)) / len(sats)
            meanHue = float(sum(hues)) / len(hues)
            meanVal = float(sum(vals)) / len(vals)

            sqsSat = [(sat - meanSat)**2 for sat in sats]
            meanSqSat = float(sum(sqsSat)) / len(sqsSat)

            sqsHue = [(hue - meanHue)**2 for hue in hues]
            meanSqHue = float(sum(sqsHue)) / len(sqsHue)

            sqsVal = [(val - meanVal)**2 for val in vals]
            meanSqVal = float(sum(sqsVal)) / len(sqsVal)

            self.colorProfiles.append(Profile(color, meanSat, meanHue, meanVal,
                                            meanSqSat, meanSqHue, meanSqVal))

    def getColor(self, h, s, v):

        maxProb = -1
        maxProfile = None
        for profile in self.colorProfiles:
            prob = profile.probability(h,s,v, self.hueOffset)
            if prob > maxProb:
                maxProfile = profile
                maxProb = prob
        return maxProfile.color

def colorByHSV(hue, sat, val):
    # this is an optional feature not used in this release.
    return profiles.getColor(hue, sat, val)

def colorByRGB(*args):

    if len(args) == 4:
        (rgb, h, s, v) = args
    elif len(args) == 2:
        (rgb, hsv) = args
        (h, s, v) = hsv

    (blue, green, red) = rgb
    (blueOff, greenOff, redOff) = profiles.rgbOffset
    red += redOff
    green += greenOff
    blue += blueOff

    green = float(max(green, 1))
    red = float(max(red, 1))
    blue = float(max(blue, 1))

    if blue / red > 2 and blue / green > 2: 
        return 'blue'
    elif green / red > 2:
        return 'green'

    if h > 150 : #or h < 6:
        return 'red'
    elif h < 20 and s < 150:
        return 'white'
    elif h < 20:
        return 'orange'
    elif h < 50:
        return 'yellow'

    return 'white'

profiles = Profiles()

def updateWhite(rgb):
    (red, green, blue) = rgb
    avg = (red + green + blue) / 3
    profiles.rgbOffset = (avg - red, avg - green, avg - blue)
########NEW FILE########
__FILENAME__ = common
#
#
# This module is provided as a sample with OpenCV
# I did not write any of it
#
#
# This is provided in the OpenCV-2.4.4 release
# Go here for OpenCV downloads: http://opencv.org/downloads.html
#
#

#/usr/bin/env python

'''
This module contais some common routines used by other samples.
'''

import numpy as np
import cv2
import os
from contextlib import contextmanager
import itertools as it

image_extensions = ['.bmp', '.jpg', '.jpeg', '.png', '.tif', '.tiff', '.pbm', '.pgm', '.ppm']

class Bunch(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)
    def __str__(self):
        return str(self.__dict__)

def splitfn(fn):
    path, fn = os.path.split(fn)
    name, ext = os.path.splitext(fn)
    return path, name, ext

def anorm2(a):
    return (a*a).sum(-1)
def anorm(a):
    return np.sqrt( anorm2(a) )

def homotrans(H, x, y):
    xs = H[0, 0]*x + H[0, 1]*y + H[0, 2]
    ys = H[1, 0]*x + H[1, 1]*y + H[1, 2]
    s  = H[2, 0]*x + H[2, 1]*y + H[2, 2]
    return xs/s, ys/s

def to_rect(a):
    a = np.ravel(a)
    if len(a) == 2:
        a = (0, 0, a[0], a[1])
    return np.array(a, np.float64).reshape(2, 2)

def rect2rect_mtx(src, dst):
    src, dst = to_rect(src), to_rect(dst)
    cx, cy = (dst[1] - dst[0]) / (src[1] - src[0])
    tx, ty = dst[0] - src[0] * (cx, cy)
    M = np.float64([[ cx,  0, tx],
                    [  0, cy, ty],
                    [  0,  0,  1]])
    return M


def lookat(eye, target, up = (0, 0, 1)):
    fwd = np.asarray(target, np.float64) - eye
    fwd /= anorm(fwd)
    right = np.cross(fwd, up)
    right /= anorm(right)
    down = np.cross(fwd, right)
    R = np.float64([right, down, fwd])
    tvec = -np.dot(R, eye)
    return R, tvec

def mtx2rvec(R):
    w, u, vt = cv2.SVDecomp(R - np.eye(3))
    p = vt[0] + u[:,0]*w[0]    # same as np.dot(R, vt[0])
    c = np.dot(vt[0], p)
    s = np.dot(vt[1], p)
    axis = np.cross(vt[0], vt[1])
    return axis * np.arctan2(s, c)

def draw_str(dst, (x, y), s):
    cv2.putText(dst, s, (x+1, y+1), cv2.FONT_HERSHEY_PLAIN, 1.0, (0, 0, 0), thickness = 2, lineType=cv2.CV_AA)
    cv2.putText(dst, s, (x, y), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), lineType=cv2.CV_AA)

class Sketcher:
    def __init__(self, windowname, dests, colors_func):
        self.prev_pt = None
        self.windowname = windowname
        self.dests = dests
        self.colors_func = colors_func
        self.dirty = False
        self.show()
        cv2.setMouseCallback(self.windowname, self.on_mouse)

    def show(self):
        cv2.imshow(self.windowname, self.dests[0])

    def on_mouse(self, event, x, y, flags, param):
        pt = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            self.prev_pt = pt
        if self.prev_pt and flags & cv2.EVENT_FLAG_LBUTTON:
            for dst, color in zip(self.dests, self.colors_func()):
                cv2.line(dst, self.prev_pt, pt, color, 5)
            self.dirty = True
            self.prev_pt = pt
            self.show()
        else:
            self.prev_pt = None


# palette data from matplotlib/_cm.py
_jet_data =   {'red':   ((0., 0, 0), (0.35, 0, 0), (0.66, 1, 1), (0.89,1, 1),
                         (1, 0.5, 0.5)),
               'green': ((0., 0, 0), (0.125,0, 0), (0.375,1, 1), (0.64,1, 1),
                         (0.91,0,0), (1, 0, 0)),
               'blue':  ((0., 0.5, 0.5), (0.11, 1, 1), (0.34, 1, 1), (0.65,0, 0),
                         (1, 0, 0))}

cmap_data = { 'jet' : _jet_data }

def make_cmap(name, n=256):
    data = cmap_data[name]
    xs = np.linspace(0.0, 1.0, n)
    channels = []
    eps = 1e-6
    for ch_name in ['blue', 'green', 'red']:
        ch_data = data[ch_name]
        xp, yp = [], []
        for x, y1, y2 in ch_data:
            xp += [x, x+eps]
            yp += [y1, y2]
        ch = np.interp(xs, xp, yp)
        channels.append(ch)
    return np.uint8(np.array(channels).T*255)

def nothing(*arg, **kw):
    pass

def clock():
    return cv2.getTickCount() / cv2.getTickFrequency()

@contextmanager
def Timer(msg):
    print msg, '...',
    start = clock()
    try:
        yield
    finally:
        print "%.2f ms" % ((clock()-start)*1000)

class StatValue:
    def __init__(self, smooth_coef = 0.5):
        self.value = None
        self.smooth_coef = smooth_coef
    def update(self, v):
        if self.value is None:
            self.value = v
        else:
            c = self.smooth_coef
            self.value = c * self.value + (1.0-c) * v

class RectSelector:
    def __init__(self, win, callback):
        self.win = win
        self.callback = callback
        cv2.setMouseCallback(win, self.onmouse)
        self.drag_start = None
        self.drag_rect = None
    def onmouse(self, event, x, y, flags, param):
        x, y = np.int16([x, y]) # BUG
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drag_start = (x, y)
        if self.drag_start:
            if flags & cv2.EVENT_FLAG_LBUTTON:
                xo, yo = self.drag_start
                x0, y0 = np.minimum([xo, yo], [x, y])
                x1, y1 = np.maximum([xo, yo], [x, y])
                self.drag_rect = None
                if x1-x0 > 0 and y1-y0 > 0:
                    self.drag_rect = (x0, y0, x1, y1)
            else:
                rect = self.drag_rect
                self.drag_start = None
                self.drag_rect = None
                if rect:
                    self.callback(rect)
    def draw(self, vis):
        if not self.drag_rect:
            return False
        x0, y0, x1, y1 = self.drag_rect
        cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 0), 2)
        return True
    @property
    def dragging(self):
        return self.drag_rect is not None


def grouper(n, iterable, fillvalue=None):
    '''grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx'''
    args = [iter(iterable)] * n
    return it.izip_longest(fillvalue=fillvalue, *args)

def mosaic(w, imgs):
    '''Make a grid from images.

    w    -- number of grid columns
    imgs -- images (must have same size and format)
    '''
    imgs = iter(imgs)
    img0 = imgs.next()
    pad = np.zeros_like(img0)
    imgs = it.chain([img0], imgs)
    rows = grouper(w, imgs, pad)
    return np.vstack(map(np.hstack, rows))

def getsize(img):
    h, w = img.shape[:2]
    return w, h

def mdot(*args):
    return reduce(np.dot, args)

def draw_keypoints(vis, keypoints, color = (0, 255, 255)):
    for kp in keypoints:
            x, y = kp.pt
            cv2.circle(vis, (int(x), int(y)), 2, color)


########NEW FILE########
__FILENAME__ = cube
# cube.py
# Chris Barker
# CMU S13 15-112 Term Project

from Tkinter import *
from geometry import *
import heapq
import copy
import random
import solutions
import math
from math import sin, cos, pi

class Struct(object): pass

def loadObject(path, index):
    with open(path) as file:
        try: data = file.read()
        except Exception as e:
            print 'Error reading data!', e
    return eval(data)[index]

def drawChevron(canvas, cx, cy, r):
    coords = (cx - 0.3 * r, cy - 0.5 * r, 
              cx - 0.2 * r, cy - 0.5 * r,
              cx + 0.3 * r, cy,
              cx - 0.2 * r, cy + 0.5 * r,
              cx - 0.3 * r, cy + 0.5 * r,
              cx - 0.3 * r, cy + 0.4 * r,
              cx + 0.2 * r, cy,
              cx - 0.3 * r, cy - 0.4 * r)
    canvas.create_polygon(*coords, fill='white', state='disabled')

def brief(L):
    s = ''
    for e in L:
        s += str(e[0])
    return s

def reversal(move):
    if type(move) == tuple:
        move = move[0]
    if type(move) == str:
        if "'" in move:
            move = move[0]
        else:
            move = move + "'"
    return move

def darken(color):
    if color[0] != '#':
        if color == 'white':
            color = '#ffffff'
        elif color == 'orange':
            color = '#ffa500'
        elif color == 'red':
            color = '#ff0000'
        elif color == 'blue':
            color = '#0000ff'
        elif color == 'green':
            color = '#00ff00'
        elif color == 'yellow':
            color = '#ffff00'
        else: return color
        return darken(color)
    else:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
        red /= 2
        green /= 2
        blue /= 2
        return '#%02x%02x%02x' % (red, green, blue)

class CenterPiece(object):
    def __init__(self, vec, parent):
        self.vec = vec
        self.parent = parent
    def callback(self, e):
        self.parent.addMoves([self.vec], self.PLAYING)

class Cube(object):
    directions = { I_HAT : 'green',
                  -I_HAT : 'blue',
                   J_HAT : 'red',
                  -J_HAT : 'orange',
                   K_HAT : 'yellow',
                  -K_HAT : 'white'}

    helpStrings = { 
        'general': 'Welcome to Cubr!\nHover over a button below to view help for it.\n\n\
The Rubik\'s Cube, invented in 1974 by Erno Rubik, is one of the most popular toys of all time.\n\
It consists of six independently rotating faces, each with nine colored stickers.\n\
The goal is to arrange the cube so that each face contains only one color.\n\
In 1981 David Singmaster published his popular three-layer solution method, which is used in this program.\n\
With practice, most people could solve the cube in under a minute. Since then, speedcubing has taken off and the current record is held by \n\
Mats Valk, who solved the cube in 5.55 seconds. In 2010, Tomas Rokicki proved that any Rubik\'s cube can be solved in 20 face rotations or less.\n\n\
This program will interactively guide you through the three-layer solution algorithm.\n\
At each step of the solution, you will be given information describing the step you are completing.\n\
You may either work with a randomly generated Rubik\'s Cube, or use your webcam to input the current configuration of your own cube!\n\n\
Many people think of solving the cube as moving the 54 stickers into place. However, it is much more helpful to think about it as\n\
moving 20 "blocks" (12 edges, 8 corners) into place. The centers of each face always stay in the same orientation relative to each other,\n\
and the stickers on each block always stay in place relative to each other.\n\
Solving the first layer means getting four edges and four corners in place so that one face is all the same color.\n\
This is intuitive for many people, but by being conscious of the algorithms you use, you can improve your time and consistency.\n\
The second layer of blocks requires only one algorithm, and involves moving only four edge pieces into place.\n\
The third and final layer is the most complicated, and requires separate algorithms for orienting (getting the stickers facing the right way)\n\
and for permuting (getting the individual blocks into place). With enough practice, you can be an expert cube solver!\n\
',

        'pause': 'During a guided solution, press this button to pause your progress.',
        'play': 'During a guided solution, press this button to resume solving the cube.',
        'reverse': 'During a guided solution, press this button to reverse the moves made so far.',
        'back': 'Press this button to step one move backward.',
        'step': 'Press this button to step one move forward.',
        'speedUp': 'Press this button to increase the rotation speed during a guided solution.',
        'slowDown': 'Press this button to decrease the rotation speed during a guided solution.',
        'fromCamera': 'Press this button to start the camera and input the configuration of your Rubik\'s cube.\n\
Tip: When inputting your cube through the camera, tilt the cube up or down to reduce glare from the screen.\n\
More tips: If the program misrecognizes a color, press the spacebar anyway to record the colors. Then, click on the misrecognized\n\
color and select the correct color from the list of colors that will pop up. Make sure you copy the movement of the virtual cube when it\n\
rotates to the next face so that your cube will be interpreted accurately.',
        'guide': 'guides through solution',
        'guideFast': 'guides through solution more quickly',
        'reset': 'resets the cube to a solved state',
        'shuffle': 'shuffles the cube',
        'solve': 'solves the cube',
        'info': 'reopen this screen',
        'stats': 'shows statistics'
    }

    faceColors = { }

    @classmethod
    def setFaceColors(cls):
        cls.faceColors = {}
        for z in xrange(3):
            for y in xrange(3):
                for x in xrange(3):
                    pieceId = z * 9 + y * 3 + x + 1
                    cls.faceColors[pieceId] = [ ]
                    (X, Y, Z) = (x - 1, y - 1, z - 1)
                    pos = Vector(X,Y,Z)
                    for vec in [Vector(0,0,1), Vector(0,1,0), Vector(1,0,0)]:
                        for direction in cls.directions:
                            if direction // vec:
                                if direction ** pos > 0:
                                    cls.faceColors[pieceId].append(cls.directions[direction])
    
    def __init__(self, canvas, controlPane, app, mode='solved'):
        Cube.setFaceColors()

        self.state = CubeState(mode)
        self.faces = { }
        self.size = 3
        self.center = Vector(0,0,0)
        self.app = app

        (self.PAUSED, self.PLAYING, self.REVERSING, self.STEP, self.BACK) = (1,2,3,4,5)
        self.status = self.PAUSED

        (self.INGAME, self.SHOWINGINFO, self.SHOWINGSTATS) = range(3)
        self.helpState = self.INGAME
        self.statString = ''
        self.helpIndex = 'general'

        self.shuffling = False

        self.delay = 100
        self.direction = (0, 0)
        self.after = 0
        self.debug = False
        self.message = ""
        self.sol = ''
        self.shuffleLen = 200

        self.moveList = [ ]
        self.moveIndex = -1

        self.controlPane = controlPane
        self.timeBetweenRotations = 0
        self.timeUntilNextRotation = 0

        self.rotating = False
        self.rotationAxis = False
        self.rotationDirection = False
        self.rotationCount = 0
        self.maxRot = 5
        self.rotationQueue = [ ]
        self.rotatingValues = [ ]
        self.sensitivity = 0.04 # click and drag

        self.showingPB = False
        self.pbMin = 0
        self.pbVal = 0
        self.pbMax = 0

        self.paused = False

        self.configureControls(controlPane)

        self.configureWindow(canvas)
        self.showInWindow()

    @property
    def maxRot(self):
        return self.maxRotationCount
    @maxRot.setter
    def maxRot(self, value):
        self.maxRotationCount = value
        self.rotationDTheta = math.pi / (2. * self.maxRotationCount)
    @maxRot.deleter
    def maxRot(self):
        pass
 
    def configureControls(self, pane):

        pane.delete(ALL)

        width = int(pane.cget('width'))
        height = int(pane.cget('height'))

        r = 16

        #
        # PAUSE
        #
        (cx, cy) = (width/2, height/2)
        pauseButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(pauseButton, '<Button-1>', self.pause)
        pane.create_rectangle(cx - (r * 0.35), cy - (r * 0.5), 
                              cx - (r * 0.10), cy + (r * 0.5), fill='#ffffff',
                              state='disabled')
        pane.create_rectangle(cx + (r * 0.35), cy - (r * 0.5), 
                              cx + (r * 0.10), cy + (r * 0.5), fill='#ffffff',
                              state='disabled')

        pane.tag_bind(pauseButton, '<Enter>', lambda e: self.assignHelp('pause'))
        pane.tag_bind(pauseButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # PLAY
        #
        (cx, cy) = (width/2 + r*2.4, height/2)
        playButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(playButton, '<Button-1>', self.play)
        pane.create_polygon(cx - r * 0.35, cy - r * 0.5,
                            cx + r * 0.55, cy,
                            cx - r * 0.35, cy + r * 0.5, fill='#ffffff',
                            state='disabled')
        pane.tag_bind(playButton, '<Enter>', lambda e: self.assignHelp('play'))
        pane.tag_bind(playButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # REVERSE
        #
        (cx, cy) = (width/2 - r*2.4, height/2)
        reverseButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(reverseButton, '<Button-1>', self.reverse)
        pane.create_polygon(cx + r * 0.35, cy - r * 0.5,
                            cx - r * 0.55, cy,
                            cx + r * 0.35, cy + r * 0.5, fill='#ffffff',
                            state='disabled')
        pane.tag_bind(reverseButton, '<Enter>', lambda e: self.assignHelp('reverse'))
        pane.tag_bind(reverseButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # SPEED UP
        #
        (cx, cy) = (width/2 + r * 10.0, height/2)
        speedUpButton = pane.create_rectangle(cx - r, cy - r, cx + r, cy + r,
                                              fill='#0088ff', activefill='#00ffff',
                                              outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(speedUpButton, '<Button-1>', self.speedUp)
        drawChevron(pane, cx, cy, r)
        drawChevron(pane, cx - 0.3 * r, cy, r * 0.8)
        drawChevron(pane, cx + 0.3 * r, cy, r * 1.2)
        pane.tag_bind(speedUpButton, '<Enter>', lambda e: self.assignHelp('speedUp'))
        pane.tag_bind(speedUpButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # SLOW DOWN
        #
        (cx, cy) = (width/2 + r * 7.5, height/2)
        slowDownButton = pane.create_rectangle(cx - r, cy - r, cx + r, cy + r,
                                              fill='#0088ff', activefill='#00ffff',
                                              outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(slowDownButton, '<Button-1>', self.slowDown)
        drawChevron(pane, cx - 0.3 * r, cy, r * 0.8)
        drawChevron(pane, cx, cy, r)
        pane.tag_bind(slowDownButton, '<Enter>', lambda e: self.assignHelp('slowDown'))
        pane.tag_bind(slowDownButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # SHUFFLE
        #
        (cx, cy) = (r * 1.5, height/2)
        shuffleButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(shuffleButton, '<Button-1>', self.shuffle)
        coords = (cx - 0.6 * r, cy - 0.4 * r, 
                  cx - 0.6 * r, cy - 0.2 * r,
                  cx - 0.2 * r, cy - 0.2 * r,
                  cx + 0.2 * r, cy + 0.4 * r,
                  cx + 0.6 * r, cy + 0.4 * r,
                  cx + 0.6 * r, cy + 0.6 * r,
                  cx + 0.8 * r, cy + 0.3 * r,
                  cx + 0.6 * r, cy - 0.0 * r,
                  cx + 0.6 * r, cy + 0.2 * r,
                  cx + 0.2 * r, cy + 0.2 * r,
                  cx - 0.2 * r, cy - 0.4 * r,
                  cx - 0.4 * r, cy - 0.4 * r)

        pane.create_polygon(*coords, outline='#ffffff', fill='#0000ff', state='disabled')

        coords = (cx - 0.6 * r, cy + 0.4 * r, 
                  cx - 0.6 * r, cy + 0.2 * r,
                  cx - 0.2 * r, cy + 0.2 * r,
                  cx + 0.2 * r, cy - 0.4 * r,
                  cx + 0.6 * r, cy - 0.4 * r,
                  cx + 0.6 * r, cy - 0.6 * r,
                  cx + 0.8 * r, cy - 0.3 * r,
                  cx + 0.6 * r, cy - 0.0 * r,
                  cx + 0.6 * r, cy - 0.2 * r,
                  cx + 0.2 * r, cy - 0.2 * r,
                  cx - 0.2 * r, cy + 0.4 * r,
                  cx - 0.4 * r, cy + 0.4 * r)

        pane.create_polygon(*coords, outline='#ffffff', fill='#0000ff', state='disabled')
        pane.tag_bind(shuffleButton, '<Enter>', lambda e: self.assignHelp('shuffle'))
        pane.tag_bind(shuffleButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # SOLVE
        #
        (cx, cy) = (r * 4.0, height/2)
        solveButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(solveButton, '<Button-1>', self.solve)
        pane.create_text(cx, cy, text='Solve', fill='white', state='disabled', font='Arial 10') 
        pane.tag_bind(solveButton, '<Enter>', lambda e: self.assignHelp('solve'))
        pane.tag_bind(solveButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # RESET
        #
        (cx, cy) = (r * 6.5, height/2)
        resetButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(resetButton, '<Button-1>', self.reset)

        pane.create_text(cx, cy, text='Reset', fill='white', state='disabled', font='Arial 10')
        pane.tag_bind(resetButton, '<Enter>', lambda e: self.assignHelp('reset'))
        pane.tag_bind(resetButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # FROM CAMERA
        #
        (cx, cy) = (r * 9.0, height/2)
        fromcamButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(fromcamButton, '<Button-1>', self.fromCamera)

        pane.create_text(cx, cy-12, text='From', fill='white', state='disabled', font='Arial 9')
        pane.create_text(cx, cy, text='Camera', fill='white', state='disabled', font='Arial 9')
        pane.tag_bind(fromcamButton, '<Enter>', lambda e: self.assignHelp('fromCamera'))
        pane.tag_bind(fromcamButton, '<Leave>', lambda e: self.assignHelp('general'))
        #
        # GUIDE
        #
        (cx, cy) = (r * 12.5, height/2)
        guideButton = pane.create_rectangle(cx - 2*r, cy - r, cx + 2*r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(guideButton, '<Button-1>', self.guideThrough)

        pane.create_text(cx, cy-12, text='Guide Through', fill='white', state='disabled', font='Arial 8')
        pane.create_text(cx, cy, text='Solution', fill='white', state='disabled', font='Arial 8')
        pane.tag_bind(guideButton, '<Enter>', lambda e: self.assignHelp('guide'))
        pane.tag_bind(guideButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # GUIDE FASTER
        #
        (cx, cy) = (r * 17, height/2)
        guideFastButton = pane.create_rectangle(cx - 2*r, cy - r, cx + 2*r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(guideFastButton, '<Button-1>', self.guideFastThrough)

        pane.create_text(cx, cy-12, text='Guide Through', fill='white', state='disabled', font='Arial 8')
        pane.create_text(cx, cy, text='Solution (Faster)', fill='white', state='disabled', font='Arial 8')
        pane.tag_bind(guideFastButton, '<Enter>', lambda e: self.assignHelp('guideFast'))
        pane.tag_bind(guideFastButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # BACK
        #
        r = 8
        (cx, cy) = (width/2 - r*7.5, height/2)
        backButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(backButton, '<Button-1>', self.back)
        pane.create_polygon(cx + r * 0.35, cy - r * 0.5,
                            cx - r * 0.55, cy,
                            cx + r * 0.35, cy + r * 0.5, fill='#ffffff',
                            state='disabled')
        pane.tag_bind(backButton, '<Enter>', lambda e: self.assignHelp('back'))
        pane.tag_bind(backButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # FORWARD
        #
        (cx, cy) = (width/2 + r*7.5, height/2)
        stepButton = pane.create_oval(cx - r, cy - r, cx + r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(stepButton, '<Button-1>', self.step)
        pane.create_polygon(cx - r * 0.35, cy - r * 0.5,
                            cx + r * 0.55, cy,
                            cx - r * 0.35, cy + r * 0.5, fill='#ffffff',
                            state='disabled')
        pane.tag_bind(stepButton, '<Enter>', lambda e: self.assignHelp('step'))
        pane.tag_bind(stepButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # INFO
        #
        (cx, cy) = (width - r * 3.5, height/2)
        helpButton = pane.create_rectangle(cx - 2*r, cy - r, cx + 2*r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(helpButton, '<Button-1>', lambda e: self.assignHelpState(self.SHOWINGINFO))

        pane.create_text(cx, cy, text='Help', fill='white', state='disabled')
        pane.tag_bind(helpButton, '<Enter>', lambda e: self.assignHelp('info'))
        pane.tag_bind(helpButton, '<Leave>', lambda e: self.assignHelp('general'))

        #
        # STATS
        #
        (cx, cy) = (width - r * 8.0, height/2)
        statsButton = pane.create_rectangle(cx - 2*r, cy - r, cx + 2*r, cy + r,
                                       fill='#0088ff', activefill='#00ffff', 
                                       outline='#ffffff', width=1, activewidth=3)
        pane.tag_bind(statsButton, '<Button-1>', self.showStats)

        pane.create_text(cx, cy, text='Stats', fill='white', state='disabled')
        pane.tag_bind(statsButton, '<Enter>', lambda e: self.assignHelp('stats'))
        pane.tag_bind(statsButton, '<Leave>', lambda e: self.assignHelp('general'))

    def configureWindow(self, canvas):
        if canvas == None:
            self.root = Tk()
            (self.width, self.height) = (450, 450)
            self.canvas = Canvas(self.root, width=self.width, height=self.height, background='#333333')
            self.needsLoop = True
        else:
            self.root = canvas._root()
            self.canvas = canvas
            (self.width, self.height) = (int(canvas.cget('width')), int(canvas.cget('height')))
            self.needsLoop = False

        self.dim = {'width': self.width, 'height': self.height}
    
    def speedUp(self, e):
         self.maxRot = max(1, self.maxRot - 1)
    def slowDown(self, e):
        self.maxRot += 1

    def timer(self):
        needsRedraw = self.move() or (not self.status == self.PAUSED)

        if self.rotating:
            self.rotationCount -= 1
            if self.rotationCount <= 0:
                self.rotating = False
                self.rotatingValues = [ ]
                self.state.rotate(self.rotationItem)
                del self.rotationItem
            needsRedraw = True

        if self.timeUntilNextRotation > 0:
            self.timeUntilNextRotation -= 1

        if (not self.rotating) and (self.timeUntilNextRotation <= 0):
            if (self.status == self.PLAYING) or (self.status == self.STEP):
                if self.moveIndex >= (len(self.moveList) - 1):
                    self.status = self.PAUSED
                    self.updateMessage('')
                    self.shuffling = False
                else:
                    self.moveIndex += 1
                    needsRedraw = self.makeMove(self.moveList[self.moveIndex],
                        animate = not self.shuffling, 
                        render = not self.shuffling or (self.moveIndex % 20 == 0))

            if (self.status == self.REVERSING) or (self.status == self.BACK):
                if self.moveIndex < 0:
                    self.status = self.PAUSED
                else:
                    needsRedraw = self.makeMove(reversal(self.moveList[self.moveIndex]))
                    self.moveIndex -= 1

            if (self.status == self.STEP) or (self.status == self.BACK):
                self.status = self.PAUSED
            self.timeUntilNextRotation = self.timeBetweenRotations


        if needsRedraw:
            try:
                self.redraw()
            except:
                self.updateMessage('Could not read cube.')
                self.state.setSolved()
                self.redraw()

    def updateMessage(self, msg):
        self.message = msg

    def updateSol(self, msg):
        self.sol = msg

    def showInWindow(self):
        self.canvas.pack()
        self.camera = Camera(Vector(4,-6.5,-7), Vector(0,0,0), pi/5, self.dim)
        self.amt = self.camera.sensitivity * self.camera.pos.dist(self.camera.origin)
        self.redraw()
        if self.needsLoop: root.mainloop()
        
    def cleanup(self):
        for pg in self.faces.values():
                self.canvas.itemconfig(pg, state='hidden')

    def move(self):
        self.amt = self.camera.sensitivity * self.camera.pos.dist(self.camera.origin)
        redraw = False
        if self.direction != (0, 0):
            self.camera.rotate(self.direction)
            redraw = True
        if self.app.resized:
            self.app.dragVal = (0,0)
            self.app.resized = False
            redraw = True
        elif self.app.dragVal != (0,0):
            self.camera.rotate((-self.sensitivity * self.app.dragVal[0],
                                -self.sensitivity * self.app.dragVal[1]))
            redraw = True
            self.app.dragVal = (self.app.dragVal[0] * 0.7,
                                self.app.dragVal[1] * 0.7)            
            if self.app.dragVal[0] < 0.01 and self.app.dragVal[1] < 0.01:
                self.app.dragVal = (0,0)
        return redraw

    @staticmethod
    def corners(center, direction, *args):
        if len(args) == 0:
            if direction // Vector(0,1,0): # parallel
                norm1 = Vector(1, 0, 0)
            else: norm1 = Vector(0,1,0)
            norm2 = 2 * direction * norm1
        else: (norm1, norm2) = args

        corners = [ ]
        for coef1 in xrange(-1, 2, 2):
            for coef2 in xrange(coef1, -2 * coef1, -2*coef1):
                corner = center + (0.5 * norm1 * coef1 +
                                   0.5 * norm2 * coef2)
                corners.append(corner)
        return corners

    def pieceOffset(self, x, y, z):
        z -= 1
        y -= 1
        x -= 1
        return Vector(x,y,z)
        
    def redraw(self):
        self.canvas.delete(ALL)

        # Top message
        self.canvas.create_text(self.camera.width/2, 40, text=self.message, fill='white', font='Arial 13 bold')

        # Bottom message
        sol = self.sol
        lineWidth = 100
        margin = 15
        y = self.camera.height - margin - 20
        while len(sol) > 0:
            self.canvas.create_text(self.camera.width/2, 
                y, text=sol[-lineWidth:], fill='white', font='Courier 12')
            y -= margin
            sol = sol[:-lineWidth]

        # Progress bar
        if self.showingPB:
            w = (self.width * (self.moveIndex - self.pbMin + 1) / 
                    (max(1, self.pbMax - self.pbMin)))
            self.canvas.create_rectangle(0, self.height-20, w, self.height, fill='#00ff66')

        toDraw = [ ]

        for z in xrange(self.size):
            for y in xrange(self.size):
                for x in xrange(self.size):
                    try:
                        (pieceID, rotationKey) = self.state.state[z][y][x]
                    except:
                        pieceID = 1
                        rotationKey = 210

                    pieceCenter = self.center + self.pieceOffset(x, y, z)
                    outDirections = [d for d in Cube.directions if d**pieceCenter > 0]
                    sod = [ ] #sorted out directions
                    for od in outDirections:
                        if od // CubeState.keys[rotationKey / 100]:
                            sod.append(od)
                    for od in outDirections:
                        if od // CubeState.keys[(rotationKey / 10) % 10]:
                            sod.append(od)
                    for od in outDirections:
                        if od // CubeState.keys[rotationKey % 10]:
                            sod.append(od)

                    pieceRotation = Vector(0,0,0)
                    theta = 0.

                    if pieceID in self.rotatingValues:
                        oldCenter = pieceCenter
                        pieceOffset = pieceCenter - (pieceCenter > self.rotationAxis)
                        pieceRotation = self.rotationAxis * pieceOffset
                        theta = self.rotationDTheta * (self.maxRot - self.rotationCount)

                        if self.rotationDirection:
                            theta *= -1

                        pieceCenter = (pieceCenter > self.rotationAxis)
                        pieceCenter = pieceCenter + cos(theta) * pieceOffset
                        pieceCenter = pieceCenter + sin(theta) * pieceRotation

                    faceColors = Cube.faceColors[pieceID]
                    for direc, color in zip(sod, faceColors):
                        axes = ()
                        faceCenter = pieceCenter + (direc / 2)

                        if pieceID in self.rotatingValues:
                            if direc // self.rotationAxis:
                                faceCenter = pieceCenter + (direc / 2)
                                if self.rotationAxis // Vector(0,1,0):
                                    axis0temp = Vector(1,0,0)
                                else:
                                    axis0temp = Vector(0,1,0)
                                axis1temp = direc * axis0temp
                                axis0 = axis0temp * cos(theta) + axis1temp * sin(theta)
                                axis1 = axis0 * direc
                                axes = (axis0, axis1)
                            else:
                                perp = -1 * (direc * self.rotationAxis)
                                perp = perp ^ (direc.mag)
                                faceCenter = pieceCenter + (sin(theta) * (perp / 2) + 
                                                            cos(theta) * (direc / 2))
                                axis0 = self.rotationAxis
                                axis1 = (faceCenter - pieceCenter) * self.rotationAxis * 2
                                axes = (axis0, axis1)
                            
                        visible = (faceCenter - pieceCenter) ** (faceCenter - self.camera.pos) < 0
                        corners = self.corners(faceCenter, pieceCenter - faceCenter, *axes)
                        corners = [corner.flatten(self.camera) for corner in corners]
                        state = 'disabled' # if visible else 'hidden'
                        outline = '#888888' if visible else 'gray'
                        if not visible: color = 'gray'
                        a = 0 if visible else 1000
                        spec = (corners, color, state, outline)
                        toDraw.append(((pieceCenter-self.camera.pos).mag + a, spec))
                        #a = self.canvas.create_polygon(corners, fill=color, 
                        #                            width=2, state=state, outline='#888888'
                        #                            #,activewidth=4, activefill=darken(color)
                        #                            )
                        if self.debug:
                            self.canvas.create_text(faceCenter.flatten(self.camera), text=str(pieceID))

                        #if pieceCenter.mag() == 1:
                        #    b = CenterPiece(pieceCenter, self)
                        #    self.canvas.tag_bind(a, '<Button-1>', b.callback)

                        """
                        newCorners = ()
                        for corner in corners: newCorners += corner.flatten(self.camera)
                        if visible:
                            self.canvas.create_polygon(self.faces[(pieceID,color)], newCorners)
                        #self.canvas.itemconfig(self.faces[(pieceID,color)], state=state)
              
                        """

            toDraw.sort(lambda a,b: cmp(b,a))
            for polygon in toDraw:
                spec = polygon[1]
                (corners, color, state, outline) = spec
                self.canvas.create_polygon(corners, fill=color, width=2, state=state, outline=outline)

        self.drawHelp()


    def gatherStats(self):
        self.statString = 'Unable to fetch solution logs.'
        stats = None
        try:
            with open('solutionLogs.txt') as file:
                stats = eval(file.read())
        except: return
        if stats is not None:
            self.statString = ''

            stats = [s.split(';') for s in stats]

            moves = [stat[-1] for stat in stats] # Gets last element
            moves = [mv[6:] for mv in moves] # Remove "Moves:"
            moves = [int(mv) for mv in moves]
            if len(moves) == 0:
                self.statString += "No solutions generated yet."
                return
            self.statString += "%d solution%s logged.\n" % (len(moves), '' if len(moves)==1 else 's')
            avgMoves = sum(moves)/len(moves)
            self.statString += "Average number of 90 degree face rotations per solution: %d\n" % (avgMoves)

            times = [stat[-2] for stat in stats] # gets 2nd to last element
            times = [tm[6:-4] for tm in times] # removes "Time: " ... " sec"
            times = [float(tm) for tm in times]
            avgTime = sum(times)/(max(1, len(times)))
            self.statString += "Average time needed to generate a solution: %0.4f seconds" % (avgTime)

    def resetStats(self):
        try:
            with open('solutionLogs.txt', 'r+') as file:
                file.seek(0) # beginning
                file.truncate()
                file.writelines(['[]'])
        except: return

    def showStats(self, *args):
        self.gatherStats()
        self.helpState = self.SHOWINGSTATS

    def drawHelp(self):
        ## MAGIC NUMBERS EVERYWHERE
        if self.helpState == self.SHOWINGINFO:
            canvas = self.canvas
            canvas.create_rectangle(100, 100, self.width-100, self.height-100,
                fill='#888888', outline='#ccccff', width=4)
            canvas.create_rectangle(110, 110, 140, 140, fill='#880000', activefill='#aa0000')
            canvas.create_text(125, 125, text='X', fill='black', state='disabled')

            canvas.create_rectangle(self.width/2-50, self.height-140, 
                                    self.width/2+50, self.height-110, 
                                    fill='#008800', activefill='#00aa00')
            canvas.create_text(self.width/2, self.height-125, text='Start', fill='black', state='disabled')

            canvas.create_text(self.width/2, 130, text="Welcome to Cubr!",
                font='Arial 25 bold')

            canvas.create_text(self.width/2, self.height/2, text=self.helpStrings[self.helpIndex], font ='Arial 8')

        elif self.helpState == self.SHOWINGSTATS:
            canvas = self.canvas
            canvas.create_rectangle(100, 100, self.width-100, self.height-100,
                fill='#888888', outline='#ccccff', width=4)
            canvas.create_rectangle(110, 110, 140, 140, fill='#880000', activefill='#aa0000')
            canvas.create_text(125, 125, text='X', fill='black', state='disabled')

            canvas.create_rectangle(self.width/2-50, self.height-140, 
                                    self.width/2+50, self.height-110, 
                                    fill='#008800', activefill='#00aa00')
            canvas.create_text(self.width/2, self.height-125, text='Back', fill='black', state='disabled')

            canvas.create_rectangle(142, self.height-130, 168, self.height-115, fill='#aaffaa', activefill='#ffffff')
            canvas.create_text(225, self.height-130, text="These statistics are generated dynamically.\nClick here to reset your data logs.", state='disabled', font = 'Arial 12')

            canvas.create_text(self.width/2, self.height/2, text=self.statString, font='Arial 14 bold')

    def click(self, event):
        if self.helpState == self.SHOWINGINFO or self.helpState == self.SHOWINGSTATS:
            if 110 < event.x < 140 and 110 < event.y < 140:
                self.helpState = self.INGAME
                self.redraw()
            elif self.width/2-50 < event.x < self.width/2+50 and \
                 self.height-140 < event.y < self.height-110:
                 self.helpState = self.INGAME
                 self.redraw()
        if self.helpState == self.SHOWINGSTATS:
            if 147 < event.x < 178 and self.height-130 < event.y < self.height-115:
                self.resetStats()
                self.showStats()
                self.redraw()

    def assignHelp(self, key):
        self.helpIndex = key
        self.redraw()

    def assignHelpState(self, state):
        self.helpState = state
        self.redraw()

    def setConfig(self, config):
        try:
            self.state = CubeState('barebones')

            if self.debug:
                print self.state

            # Modify the state to include [(color, direction), (color, direction), ...]
            # And then parse pieceId and orientationKey out of that

            def faceToAxis(face):
                if self.debug:
                    print face
                center = face[1][1]
                axis = [vec for vec in Cube.directions if 
                        Cube.directions[vec].lower() == center.lower()][0]
                return axis

            def setAxes(normal, known, dirString):
                dirString = dirString.lower()
                if dirString == 'up':
                    up = known
                elif dirString == 'down':
                    up = known * -1
                elif dirString == 'left':
                    up = (normal * known)
                elif dirString == 'right':
                    up = (known * normal)

                down = up * -1
                left = (up * normal)
                right = left * -1

                return (up, down, left, right)

            timesTouched = [[[0,0,0],[0,0,0],[0,0,0]],[[0,0,0],[0,0,0],[0,0,0]],[[0,0,0],[0,0,0],[0,0,0]]]

            for faceInfo in config:
                axis = faceToAxis(faceInfo.currentFace)
                prevAxis = nextAxis = None
                if faceInfo.prevFace:
                    prevAxis = faceToAxis(faceInfo.prevFace)
                if faceInfo.nextFace:
                    nextAxis = faceToAxis(faceInfo.nextFace)
                prevTurn = faceInfo.prevTurn
                nextTurn = faceInfo.nextTurn

                if self.debug:
                    print 'axis:', axis, Cube.directions[axis]
                    print 'prevAxis:', prevAxis,
                    if prevAxis:
                        print Cube.directions[prevAxis]
                    print 'nextAxis:', nextAxis, 
                    if nextAxis:
                        print Cube.directions[nextAxis]
                    print 'prevTurn:', prevTurn 
                    print 'nextTurn:', nextTurn

                if prevTurn:
                    (up, down, left, right) = setAxes(axis, prevAxis, prevTurn)
                elif nextTurn:
                    (up, down, left, right) = setAxes(axis, nextAxis * -1, nextTurn)

                if self.debug:
                    print 'up:', up, Cube.directions[up]
                    print 'down:', down, Cube.directions[down]
                    print 'left:', left, Cube.directions[left]
                    print 'right:', right, Cube.directions[right]

                for row in xrange(3):
                    for col in xrange(3):
                        pos = axis
                        pos = pos + (down * (row - 1))
                        pos = pos + (right * (col - 1))

                        (x, y, z) = pos.components
                        (x, y, z) = (int(x+1), int(y+1), int(z+1))
                        if self.debug:
                            print 'x,y,z', x, y, z,
                            print 'pos=', pos

                        timesTouched[z][y][x] += 1

                        cell = self.state.state[z][y][x]
                        if type(cell) == list:
                            cell.append((faceInfo.currentFace[row][col], axis))

            if self.debug:
                print 'state=', self.state
                print 'times', timesTouched

            # Cast each [ ] list to a ( ) tuple
            # [(color,dir),(color,dir),(color,dir)] ----> (pieceId, orientationKey)

            reverseZ = -1 if self.camera.view ** Vector(0,0,1) < 0 else 1
            reverseY = -1 if self.camera.view ** Vector(0,1,0) < 0 else 1
            reverseX = -1 if self.camera.view ** Vector(1,0,0) < 0 else 1

            zRange = range(3)[::reverseZ]
            yRange = range(3)[::reverseY]
            xRange = range(3)[::reverseX]


            for z in zRange:
                for y in yRange:
                    for x in xRange:
                        
                        cell = self.state.state[z][y][x]
                        if type(cell) == list:
                            pieceId = -1
                            colors = set()
                            for i in cell:
                                colors.add(i[0])
                            for key in Cube.faceColors:
                                if set(Cube.faceColors[key]) == colors:
                                    pieceId = key
                                    break
                            if pieceId >= 0:
                                desiredColorOrder = Cube.faceColors[pieceId]
                                currentOrder = [ ]
                                ori = 0
                                notAdded = set([0,1,2])

                                cell.sort(lambda a,b: cmp(desiredColorOrder.index(a[0]),
                                                          desiredColorOrder.index(b[0])))

                                for i in cell:
                                    ori *= 10
                                    if i[1] // Vector(0,0,1):
                                        ori += 2
                                        notAdded.discard(2)
                                    elif i[1] // Vector(0,1,0):
                                        ori += 1
                                        notAdded.discard(1)
                                    elif i[1] // Vector(1,0,0):
                                        ori += 0
                                        notAdded.discard(0)

                                while len(notAdded) > 0:
                                    ori *= 10
                                    ori += notAdded.pop()

                                orientationKey = ori

                            else:
                                raise ValueError('Invalid Cube')

                            if pieceId in (5, 11, 13, 14, 15, 17, 23):
                                raise ValueError('Invalid Cube') # Center piece

                            desired = Cube.faceColors[CubeState.solvedState[z][y][x][0]]

                            if self.debug:
                                print 'The piece with colors %s is at the position of %s' % (colors, desired)
                                print 'setting (%d,%d,%d) to (%s, %s)' % (z,y,x,pieceId,orientationKey)

                            self.state.state[z][y][x] = (pieceId, orientationKey)
        except:
            self.updateMessage('Unable to read camera input.')
            self.state.setSolved()
            self.redraw()
        if self.debug:
            print 'final state=', self.state
                
        self.redraw()
        
    def addMoves(self, moves, status=-1):
        self.moveList[self.moveIndex+1:] = [ ]
        self.moveList.extend(moves)
        if status != -1:
            self.status = status

    def rotate(self, axis):
        self.showingPB = False
        self.addMoves([axis], self.PLAYING)

    def makeMove(self, move, render=True, animate=True):
        if type(move) == tuple:
            self.updateMessage(move[1])
            axis = move[0]
        else:
            axis = move

        self.rotationItem = self.state.rotationInfo(axis)

        if animate:
            self.rotating = True

            self.rotationAxis = self.rotationItem.rotationAxis
            self.rotatingValues = self.rotationItem.rotatingValues
            self.rotationDirection = self.rotationItem.rotationDirection
            self.rotationCount = self.maxRot

        else:
            self.rotating = False
            self.state.rotate(self.rotationItem)
            while (self.moveIndex + 1) % 20 != 0:
                if self.moveIndex == len(self.moveList) - 1:
                    self.updateMessage('')
                    break
                self.moveIndex += 1
                move = self.moveList[self.moveIndex]
                if type(move) == tuple:
                    self.updateMessage(move[1])
                    axis = move[0]
                else:
                    axis = move
                self.rotationItem = self.state.rotationInfo(axis)
                self.state.rotate(self.rotationItem)

        return render

    def pause(self, e):
        self.status = self.PAUSED
    def play(self, e):
        self.status = self.PLAYING
    def step(self, e):
        self.timeUntilNextRotation
        self.status = self.STEP
    def back(self, e):
        self.timeUntilNextRotation = 0
        self.status = self.BACK
    def reverse(self, e):
        self.status = self.REVERSING
    def fromCamera(self, e):
        if not self.app.inCam:
            self.app.fromCamera()
        
    def reset(self, e):
        self.moveList = [ ]
        self.moveIndex = 0
        self.shuffling = False
        self.showingPB = False
        self.state.setSolved()
        self.redraw()

    def solve(self, *args):
        try:
            solution = self.getSolution()
        except Exception as e:
            import traceback, sys
            txt = 'Error finding solution. Make sure your cube is configured legally and was input accurately.'
            print 'error:', e
            traceback.print_exc(file=sys.stdout)
            self.updateMessage(txt)
            self.redraw()
        else:
            if not self.showingPB:
                self.addMoves(solution, self.PLAYING)
                self.showingPB = True
                self.pbMin = len(self.moveList) - len(solution)
                self.pbMax = len(self.moveList)
                self.updateSol('With F as Red and U as Yellow: Solution: '+brief(solution))
            self.maxRot = 5
            self.timeBetweenRotations = 0
            self.timeUntilNextRotation = 0

    def guideThrough(self, *args):
        if not self.showingPB:
            self.solve()
        self.maxRot = 20
        self.timeBetweenRotations = 35
        self.timeUntilNextRotation = 15

    def guideFastThrough(self, *args):
        if not self.showingPB:
            self.solve()
        self.maxRot = 13
        self.timeBetweenRotations = 18
        self.timeUntilNextRotation = 5

    def shuffle(self, *args):
        self.showingPB = False
        n = self.shuffleLen
        delay = 5
        moves = ["U", "L", "D", "R", "F", "B",
                 "U'", "L'", "D'", "R'", "F'", "B'"
        ]
        moveList = [(random.choice(moves), "Shuffling step %d of %d" % (i+1,n)) for i in xrange(n)]
        self.addMoves(moveList, self.PLAYING)
        self.shuffling = True
        self.status = self.PLAYING

    def getSolution(self, method='beginner'):
        if method == 'beginner':
            solution = solutions.beginner3Layer(self.state.copy())
        return solution

class CubeState(object):
    """Container for a 3D list representing the cube's state.
Non-graphical; meant for algorithmic purposes."""

    # Each element is in the form (pieceID, orientationKey)
    # Orientation Keys:
        # CORNERS
            # 2 == Z
            # 1 == Y
            # 0 == X
        # orientationKey = [first priority][second priority][third priority]
        # 210 = ZYX
        # 021 = XZY
        # etc.

    solvedState = [[[ ( 1, 210), ( 2, 210), ( 3, 210) ],
                    [ ( 4, 210), ( 5, 210), ( 6, 210) ],
                    [ ( 7, 210), ( 8, 210), ( 9, 210) ]],

                   [[ (10, 210), (11, 210), (12, 210) ],
                    [ (13, 210), (14, 210), (15, 210) ],
                    [ (16, 210), (17, 210), (18, 210) ]],

                   [[ (19, 210), (20, 210), (21, 210) ],
                    [ (22, 210), (23, 210), (24, 210) ],
                    [ (25, 210), (26, 210), (27, 210) ]]]

    barebones = [[[          [],        [],        [] ],
                  [          [], ( 5, 210),        [] ],
                  [          [],        [],        [] ]],

                 [[          [], (11, 210),        [] ],
                  [ (13, 210), (14, 210), (15, 210) ],
                  [         [], (17, 210),         [] ]],

                 [[          [],        [],       [] ],
                  [          [], ( 23, 210),      [] ],
                  [          [],        [],       [] ]]]
    keys = { 2: Vector(0,0,1),
             1: Vector(0,1,0),
             0: Vector(1,0,0)}
    perpendiculars = { Vector(0,0,1): [0, 1],
                       Vector(0,1,0): [0, 2],
                       Vector(1,0,0): [1, 2]}

    movementCodes = solutions.MOVE_CODES
    movementKeys = {
                    "U": Vector(0,0,1),
                    "D": Vector(0,0,-1),
                    "L": Vector(-1,0,0),
                    "R": Vector(1,0,0),
                    "F": Vector(0,1,0),
                    "B": Vector(0,-1,0)
                  }

    def __init__(self, state='solved'):
        self.state = state
        self.size = 3
        if self.state == 'solved':
            self.setSolved()
        elif self.state == 'barebones':
            self.setBare()
    def __str__(self):
        s = ''
        for z in xrange(self.size):
            for y in xrange(self.size):
                for x in xrange(self.size):
                    item = str(self.state[z][y][x])
                    s += item
                s += '\n'
            s += '\n'
        return s

    def condense(self):
        s = 'State:'
        for z in xrange(self.size):
            for y in xrange(self.size):
                for x in xrange(self.size):
                    item = self.state[z][y][x]
                    item2 = str(item[0]) + "'" + str(item[1])
                    s += item2
                    s += ','
                s += ','
            s += ','
        return s

    @classmethod
    def getPerps(cls, p):
        for key in cls.perpendiculars:
            if key // p: return cls.perpendiculars[key]

    @staticmethod
    def kthDigit(num, k):
        num /= (10**k)
        return num % 10

    @staticmethod
    def swapDigits(num, i, j):
        ithDigit = CubeState.kthDigit(num, i)
        num -= ithDigit * int(10**i)
        jthDigit = CubeState.kthDigit(num, j)
        num -= jthDigit * int(10**j)
        num += ithDigit * int(10**j)
        num += jthDigit * int(10**i)
        return num

    def rotationInfo(self, axis):
        isNeg = False
        if type(axis) == str and "'" in axis:
            isNeg = True
            axis = axis[0]

        if type(axis) == str:
            axis = CubeState.movementKeys[axis]

        rotationIndcs = [ ]
        for x in xrange(self.size):
            for y in xrange(self.size):
                for z in xrange(self.size):
                    pos = Vector(x-1,y-1,z-1)
                    if pos**axis > 0 and pos == axis:
                        rotationIndcs.append((x,y,z))

        oldValues = { }
        for i in rotationIndcs:
            oldValues[i] = self.state[i[2]][i[1]][i[0]]

        rot = Struct()
        rot.rotationAxis = axis
        rot.rotatingValues =[val[0] for val in oldValues.values()]
        rot.rotationDirection = isNeg
        rot.oldValues = oldValues
        rot.rotationIndcs = rotationIndcs
        return rot

    def rotate(self, r):

        # Vector axis of rotation

        axis = r.rotationAxis
        isNeg = r.rotationDirection
        rotationIndcs = r.rotationIndcs
        oldValues = r.oldValues

        for idx in rotationIndcs:
            pos = Vector(idx[0]-1, idx[1]-1, idx[2]-1)
            posn = pos - (pos > axis)
            newn = axis * posn
            if isNeg:
                newn = newn * -1.
            new = newn + (pos > axis)

            # Alter the rotationkey
            (oldId, oldKey) = oldValues[idx]
            perps = CubeState.getPerps(axis)
            toSwap = [ ]
            for perp in perps:
                for i in xrange(self.size):
                    if CubeState.kthDigit(oldKey, i) == perp:
                        toSwap.append(i)
            newKey = CubeState.swapDigits(oldKey, *toSwap)
            newValue = (oldId, newKey)

            newi = (int(new.x+1), int(new.y+1), int(new.z+1))
            self.state[newi[2]][newi[1]][newi[0]] = newValue

    def copy(self):
        return CubeState(copy.deepcopy(self.state))

    def setBare(self):
        self.state = copy.deepcopy(CubeState.barebones)

    def setSolved(self):
        self.state = copy.deepcopy(CubeState.solvedState)

########NEW FILE########
__FILENAME__ = geometry
# geometry.py
# Chris Barker
# CMU S13 15-112 Term Project

from math import pi, tan, acos, atan

class Vector(object):
    """An n-dimensional vector has a list of n components.
    <a,b,c> + <d,e,f> == <a+d, b+e, c+f>
    <a,b,c> ** <d,e,f> == ad+be+cf
    A*B = A x B
    <a,b,c> * n = <an,bn,cn>
    A ^ m returns a vector in the direction of A with magnitude m
    A // B returns True if A and B are parallel and False otherwise
    ~A returns and arbitrary vector perpendicular to A
    A > B returns the projection of A onto B
    """
    
    epsilon = 1e-6

    @staticmethod
    def cross(x1, y1, z1, x2, y2, z2):
        """Returns the cross product of two 3-dimensional vectors."""
        return Vector(y1 * z2 - z1 * y2,
                      z1 * x2 - x1 * z2,
                      x1 * y2 - y1 * x2)

    @staticmethod
    def almostEqual(a, b):
        """Compares two floating point values for near-equality."""
        return abs(a - b) < Vector.epsilon

    def __init__(self, *components):
        if type(components[0]) == Vector:
            # Instantiate a vector with another vector.
            self.components = components[0].components
        elif hasattr(components[0], '__iter__'):
            # Passed in an iterable
            self = Vector(components[0])
        else:
            self.components = [ float(q) for q in components ]

    def __str__(self):
        """a.__str__ <==> str(a)"""
        return '<%s>' % (','.join([str(c) for c in self.components]))
        
    def __repr__(self):
        """a.__repr__ <==> repr(a)"""
        return 'Vector(%r)' % (self.components)

    def __hash__(self):
        """a.__hash__ <==> hash(a)"""
        return hash(tuple(self.components))

    # Component properties
    @property
    def x(self):
        if len(self.components) < 1: return 0
        return self.components[0]
    @x.setter
    def x(self, value):
        if len(self.components) > 0:
            self.components[0] = value
    @x.deleter
    def x(self):
        if len(self.components) > 0:
            self.components[0] = 0

    @property
    def y(self):
        if len(self.components) < 2: return 0
        return self.components[1]
    @y.setter
    def y(self, value):
        if len(self.components) > 1:
            self.components[1] = value
    @y.deleter
    def y(self):
        if len(self.components) > 1:
            self.components[1] = 0

    @property
    def z(self):
        if len(self.components) < 3: return 0
        return self.components[2]
    @z.setter
    def z(self, value):
        if len(self.components > 2):
            self.components[2] = value
    @z.deleter
    def z(self):
        if len(self.components) > 2:
            self.components[2] = 0

    @property
    def mag(self):
        return (self.x**2 + self.y**2 + self.z**2)**0.5

    @mag.setter
    def mag(self, value):
        self = self.unit() * value

    @mag.deleter
    def mag(self):
        pass

    def mag2(self):
        """Returns the square of the magnitude of a."""
        return self.x**2 + self.y**2 + self.z**2

    def __mul__(self, other):
        if type(other) == int or type(other) == float or type(other) == long:
            return Vector(*[comp * other for comp in self.components])
        elif type(other) == Vector: # Cross product
            return Vector.cross(*(self.components[:3] + other.components[:3]))

    def __rmul__(self, other):
        return self * other
    
    def __pow__(self, other):
        if type(other) == int or type(other) == float or type(other) == long:
            return Vector(*[comp ** other for comp in self.components])
        elif type(other) == Vector: # Dot product
            return sum([a*b for a, b in zip(self.components, other.components)])

    def __imul__(self, other):
        return self * other

    def __eq__(self, other):
        """a.__eq__(b) <==> a==b"""
        if not isinstance(other, Vector):
            if other == 0: return self.isZero()
        else:
            if len(self.components) != len(other.components): return False
            return [Vector.almostEqual(a,b) for (a,b) in zip(self.components,other.components)]

    def __neq__(self, other):
        return not (self == other)


    def __add__(self, other):
        addends = [ self.components, other.components ]
        total = [ 0 ] * max([len(addend) for addend in addends])
        for compList in addends:
            for i in xrange(len(compList)):
                total[i] += compList[i]
        return Vector(*total)

    def __iadd__(self, other):
        return self + other

    def __sub__(self, other):
        return self + (-1 * other)

    def __neg__(self):
        return self * -1

    def __pos__(self):
        return self * +1

    def __isub__(self, other):
        return self - other

    def __xor__(self, other):
        if isinstance(other, (int, long, float)):
            return self.unit() * other

    def __ixor__(self, other):
        return self ^ other

    def __invert__(self):
        return self.perp()

    def __floordiv__(self, other):
        if isinstance(other, (int, long, float)):
            return self / other
        elif isinstance(other, Vector):
            return self.isParallel(other)

    def __div__(self, other):
        if isinstance(other, (int, long, float)):
            return self * (1./other)

    def __rdiv__(self, other):
        return self / other

    def __gt__(self, other):
        return self.project(other)

    def dot(self, other):
        return self.x*other.x + self.y*other.y + self.z*other.z

    def isZero(self):
        for comp in self.components:
            if not comp == 0:
                 return False
        return True

    def dist(self, other):
        return (self - other).mag

    def dist0(self, other):
        return self.mag()

    def unit(self):
        if self.isZero(): return self
        return self * (1./self.mag)

    def project(self, other):
        return other * ((self ** other) / other.mag2())

    def isEqual(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z

    def isNegation(self, other):
        return self.scalar(-1).isEqual(other)

    def isParallel(self, other):
        return (self * other).mag < Vector.epsilon

    def isPerpendicular(self, other):
        return self.dot(other) == 0

    def angleBetween(self, other):
        return acos(self.dot(other) / (self.mag * other.mag))

    def perp(self):
        """Returns an arbitrary perpendicular vector"""
        vect = Vector(1,0,0) - (Vector(1,0,0) > self)
        if not vect.isZero():
            return vect
        else:
            return Vector(0,1,0) - (Vector(1,0,0) > self)

    def flatten(self, camera):
        """Returns 2D 'film' coordinates given a 3D position vector and a camera"""
        view = camera.view
        up = camera.up
        right = camera.right
        field = camera.field
        cameraPos = camera.pos
        width = camera.width
        height = camera.height

        displacement = self - cameraPos
        horiz = displacement - (displacement > up)
        vertic = displacement - (displacement > right)
        forward = horiz > view
        edge = forward + (right ^ (forward.mag * field))
        rightComp = edge - forward
        horizComp = horiz - forward
        ratio = horizComp.mag / rightComp.mag
        if rightComp ** horizComp < 0:
            ratio *= -1
        length = min(width, height)
        x = (width/2) + (ratio*length)

        forward = vertic > view
        edge = forward + (up ^ (vertic.mag * field))
        topComp = edge - forward
        verticComp = vertic - forward
        ratio = verticComp.mag / topComp.mag
        if topComp ** verticComp < 0:
            ratio *= -1
        y = (height/2) + (ratio*length)

        return (x,y)


I_HAT = Vector(+1, 0, 0)
J_HAT = Vector( 0,+1, 0)
K_HAT = Vector( 0, 0,+1)


class Camera(object):
    def __init__(self, pos, origin, angle, dim, sensitivity=0.2):
        self.pos = pos
        self.origin = origin
        self.field = tan(angle)
        self.angle = angle
        self.view = (origin - pos) ^ 1
        self.right = (~self.view) ^ 1
        self.up = (self.right * self.view) ^ 1
        self.width = dim['width']
        self.height = dim['height']
        self.sensitivity = sensitivity

    def rotate(self, direction):
        (x, y) = direction
        zoom = self.pos.mag
        right = self.view * self.up
        self.pos = self.pos + (self.up * y)
        self.view = self.origin - self.pos
        self.pos = self.pos ^ zoom
        self.up = (right * self.view) ^ self.up.mag
        self.pos = self.pos + (right * x)
        self.pos = self.pos ^ zoom
        self.view = (self.origin - self.pos) ^ 1
        self.up = (right * self.view) ^ 1
        self.right = (self.view * self.up) ^ 1

    def fisheye(self, inc):
        factor = inc
        self.angle *= factor
        self.field = tan(self.angle)
        self.pos.mag = self.pos.mag / factor
        self.view = (self.origin - self.pos) ^ 1
########NEW FILE########
__FILENAME__ = qbr
# qbr.py
# Chris Barker
# CMU S13 15-112 Term Project

from app import App
import Tkinter
import screenGrabber
from cube import Cube

class Cubr(App):

    def init(self):
        self.resized = False
        self.inCam = False
        ctrlPaneHeight = 60
        ctrlPaneColor = '#222222'

        # Canvas for holding buttons
        self.controlPane = Tkinter.Canvas(self.root, width = self.width,
                              height = ctrlPaneHeight, background=ctrlPaneColor)

        # Event handlers for window resizing
        self.controlPane.bind('<Configure>', self.controlResize)
        self.canvas.bind('<Configure>', self.resize)

        # Superclass deals with packing canvas
        self.controlPane.pack(expand=1, fill=Tkinter.BOTH)
        self.newCube()

    def newCube(self):
        # replaces self.cube with a new Cube() object
        if hasattr(self, 'cube'):
            self.cube.cleanup()
            del self.cube
        self.cube = Cube(self.canvas, self.controlPane, self)

    def received(self, cube):
        # callback handler for the screenGrabber module
        # sets self.cube's configuration based on the Streamer cube
        self.inCam = False
        self.cube.helpState = self.cube.INGAME
        if self.cube.debug:
            print cube.events
        try:
            self.cube.setConfig(cube)
        except:
            # Something went wrong setting the configuration
            self.cube.state.setSolved()

    def fromCamera(self):
        # Create "Starting webcam..." popup while we wait for webcam to turn on
        self.canvas.create_rectangle(self.width/2 - 200, self.height/2 - 50,
                                     self.width/2 + 200, self.height/2 + 50,
                                     fill='#123456', outline='#abcdef', width=5)
        self.canvas.create_text(self.width/2, self.height/2, fill='#ffffff',
            font='Arial 36 bold', text='Starting webcam...')

        self.canvas.update()
        self.newCube()
        self.inCam = True

        # Hand over control to the screenGrabber
        screenGrabber.cubeFromCam(app=self, callback=self.received)

    def timerFired(self):
        # cube.timer wrapper -- only calls if we are not in screenGrabber
        if not self.inCam:
            self.cube.timer()

    def debug(self):
        # toggle whether debug is on or off. this feature is disabled in release builds.
        self.cube.debug = not self.cube.debug
        self.cube.redraw()

    def resize(self, event):
        # Event binding for canvas resizing
        self.width = event.width
        self.height = event.height
        self.resized = True
        self.cube.width = self.width
        self.cube.height = self.height
        self.cube.camera.width = self.width
        self.cube.camera.height = self.height

    def mousePressed(self, event):
        # Wrapper for cube.click
        self.cube.click(event)

    def controlResize(self, event):
        # Event binding for controlPane resizing
        # Adjust size, and compensate for border
        borderX, borderY = -7, -6
        self.controlPane.config(width=event.width+borderX,
                                height=event.height+borderY)
        self.cube.configureControls(self.controlPane)

    def keyPressed(self, event):
        # key event handler

        # Adjust viewmode. only available in debug.
        if self.cube.debug:
            if event.keysym == 'o':
                self.cube.camera.fisheye(+1.2)
                self.cube.redraw()
            elif event.keysym == 'p':
                self.cube.camera.fisheye(+0.8)
                self.cube.redraw()

        amt = self.cube.amt # Delta value for rotation sensitivity
        if event.keysym == 'Left': self.cube.direction = (amt, self.cube.direction[1])
        elif event.keysym == 'Right': self.cube.direction = (-amt, self.cube.direction[1])
        elif event.keysym == 'Up': self.cube.direction = (self.cube.direction[0], amt)
        elif event.keysym == 'Down': self.cube.direction = (self.cube.direction[0], -amt)
        # command for clockwise rotation of a face
        elif event.keysym in 'rdlufb': self.cube.rotate(event.keysym.upper())
        # command for counterclockwise rotation of a face
        elif event.keysym in 'RDLUFB': self.cube.rotate(event.keysym + "'")
        else:
            if self.cube.debug:
                print event.keysym

    def keyReleased(self, event):
        if event.keysym in ['Left', 'Right', 'Down', 'Up']:
            # stopping rotation
            self.cube.direction = (0, 0)

if __name__ == '__main__':
    game = Cubr(name="Cubr")

########NEW FILE########
__FILENAME__ = screenGrabber
# solutions.py
# Chris Barker
# CMU S13 15-112 Term Project

# Some code in this module is adapted from color_histogram.py,
# which is provided in the OpenCV-2.4.4 release
# Go here for OpenCV downloads: http://opencv.org/downloads.html
# The code that I did not write is clearly marked as follows:

            # I did not write this code:
            ##############################
            # " Code I didn't write"
            ##############################

# I also did not write any of the numpy, cv, cv2, video, 
# sys, Tkinter, or getopt modules.

import numpy as np
import cv, cv2
import video
import sys
import getopt
from coloranalytics import colorByHSV, colorByRGB
from Tkinter import Label
from geometry import *

fnt = cv2.FONT_HERSHEY_PLAIN

# Quick mapping from string to hex for cube sticker colors
colorCodes = {
    'red': '#ff0000',
    'green': '#00ff00',
    'blue': '#0000ff',
    'orange': '#ff8800',
    'yellow': '#ffff00',
    'white': '#ffffff',
    'gray': '#888888'
}

# Object attribute container
class Struct(): pass

def colorTuple(s):
    # Converts a color string to a color tuple.

    if type(s) == tuple:
        return s
    elif type(s) != str:
        # fallback value
        s = '#888888'

    s = s.lower()
    if s[0] != '#':
        if s in colorCodes:
            s = colorCodes[s]
        else:
            # fallback value
            s = '#888888'

    base = 0x10
    red = int(s[1:3], base)
    green = int(s[3:5], base)
    blue = int(s[5:7], base)
    return (blue, green, red) # OpenCV uses BGR

def selectionColor(x, y, data):
    # Takes a click (x,y) and returns the color of the palette at that point
    if (data.colorSelectionStartY <= y <= 
        data.colorSelectionStartY + data.colorSelectionHeight):
        xNow = data.colorSelectionStartX
        for color in data.colorSelections:
            if xNow <= x <= xNow + data.colorSelectionWidth:
                return color
            xNow += data.colorSelectionWidth

def suff(i):
    return 'st' if i==1 else 'nd' if i==2 else 'rd' if i==3 else 'th'

def onMouse(e, x, y, flags, param, data):
    if e == 0:
        # Movement
        pass
    elif e == 1:
        # Click down
        pass
    elif e == 4:
        # Release mouse button
        index = data.cube.faceClicked(x, y)
        print 'index', index
        if index is not None:
            data.showingSelector = True
            print 'now showing selector!'
            data.selectionIndex= index
        else:
            if data.showingSelector:
                newColor = selectionColor(x, y, data)
                if newColor is not None:
                    data.cube.setColor(data.selectionIndex, newColor)

class Streamer(object):
    def __init__(self, stream):
        self.index = 0
        self.stream = stream
    def __iter__(self):
        return self
    def next(self):
        while self.index != len(self.stream.events):
            if self.stream.events[self.index][0] == 'face':
                break
            self.index += 1
        else:
            raise StopIteration
        
        prevTurnIndex = self.index
        prevTurn = None
        while prevTurnIndex >= 0:
            if self.stream.events[prevTurnIndex][0] == 'turn':
                prevTurn = self.stream.events[prevTurnIndex][1]
                break
            prevTurnIndex -= 1

        prevFaceIndex = self.index - 1
        prevFace = None
        while prevFaceIndex >= 0:
            if self.stream.events[prevFaceIndex][0] == 'face':
                prevFace = self.stream.events[prevFaceIndex][1]
                break
            prevFaceIndex -= 1

        nextTurnIndex = self.index
        nextTurn = None
        while nextTurnIndex < len(self.stream.events):
            if self.stream.events[nextTurnIndex][0] == 'turn':
                nextTurn = self.stream.events[nextTurnIndex][1]
                break
            nextTurnIndex += 1

        nextFaceIndex = self.index + 1
        nextFace = None
        while nextFaceIndex < len(self.stream.events):
            if self.stream.events[nextFaceIndex][0] == 'face':
                nextFace = self.stream.events[nextFaceIndex][1]
                break
            nextFaceIndex += 1

        currentFace = self.stream.events[self.index][1]

        data = Struct()
        data.currentFace = currentFace
        data.prevFace = prevFace
        data.nextFace = nextFace
        data.prevTurn = prevTurn
        data.nextTurn = nextTurn

        self.index += 1

        return data

class Stream(object):
    def __init__(self):
        self.events = [ ]
    def logFace(self, a):
        L = [ a[:3], a[3:6], a[6:] ]
        self.events.append(('face', L))
    def logTurn(self, turn):
        self.events.append(('turn', turn))
    def __iter__(self):
        return Streamer(self)

def averageRGB(img):
    red = 0
    green = 0
    blue = 0
    num = 0
    for y in xrange(len(img)):
        if y%10 == 0:
            a = img[y]
            for x in xrange(len(a)):
                if x%10 == 0:
                    b = img[y][x]
                    num += 1
                    red += b[0]
                    green += b[1]
                    blue += b[2]
    red /= num
    green /= num
    blue /= num
    return (red, green, blue)

def histMode(hist, maxAmt):
    bin_count = int(hist.shape[0])
    maxAmount = int(hist[0])
    maxIndex = 0
    numZero = 0
    numTotal = 0
    for i in xrange(bin_count):
        h = int(hist[i])
        if h == 0: numZero += 1
        numTotal += 1
        if h > maxAmount:
            maxIndex = i
            maxAmount = h
    val = int(maxAmt * maxIndex / bin_count)
    return val

class DemoCube(object):
    directions = (K_HAT, J_HAT, I_HAT, -J_HAT, -I_HAT, -K_HAT)
    ups = (-J_HAT, K_HAT, K_HAT, K_HAT, K_HAT, -I_HAT)
    rights = (I_HAT, I_HAT, -J_HAT, -I_HAT, J_HAT, J_HAT)

    def __init__(self):
        self.colors = ['gray'] * 54
        (self.width, self.height) = (400, 500)
        self.dim = {'width': self.width, 'height': self.height}
        self.faceIndex = 0
        self.transitionSpeed = 1
        self.camera = Camera(Vector(2, -4, 10), Vector(0,0,0), pi/5, self.dim)

    @staticmethod
    def faceInfo(i):
        faceIndex = i / 9
        norm = DemoCube.directions[faceIndex]
        up = DemoCube.ups[faceIndex]
        right = DemoCube.rights[faceIndex]
        faceCenter = norm * 1.5
        faceCenter = faceCenter - ((i / 3)%3 - 1) * up
        faceCenter = faceCenter - (i%3 - 1) * right
        return (faceCenter, norm, up, right)

    def adjustCamera(self):
        destination = (DemoCube.directions[self.faceIndex]) ^ 1
        current = (self.camera.view) ^ 1
        if destination ** current < 0.6:
            currentPos = self.camera.pos
            destinationPos = self.camera.origin + destination * (currentPos.mag)
            deltaY = destinationPos ** self.camera.up
            deltaX = destinationPos ** self.camera.right
            deltaX *= 0.1
            deltaY *= 0.1
            self.camera.rotate((deltaX, deltaY))

    def faceClicked(self, x, y):
        for i in xrange(len(self.colors)):
            (center, norm, up, right) = self.faceInfo(i)
            if norm ** (center - self.camera.pos) < 0:
                corners = (center + up * 0.5 + right * 0.5,
                           center + up * 0.5 - right * 0.5,
                           center - up * 0.5 - right * 0.5,
                           center - up * 0.5 + right * 0.5)
                corners = [corner.flatten(self.camera) for corner in corners]
                corners = [(int(corner[0]), int(corner[1])) for corner in corners]
                for corner in xrange(len(corners) - 1):
                    prev = (corner - 1) % len(corners)
                    cursor = Vector(x - corners[corner][0], y - corners[corner][1], 0)
                    prevVect = Vector(corners[prev][0] - corners[corner][0],
                                      corners[prev][1] - corners[corner][1], 0)
                    nextVect = Vector(corners[corner+1][0] - corners[corner][0],
                                      corners[corner+1][1] - corners[corner][1], 0)
                    if ((prevVect * cursor) ** (cursor * nextVect) < 0):
                        break
                else:
                    return i

    def draw(self, vis):
        self.adjustCamera()
        for i in xrange(len(self.colors)):
            (center, norm, up, right) = self.faceInfo(i)
            if norm ** (center - self.camera.pos) < 0:
                corners = (center + up * 0.5 + right * 0.5,
                           center + up * 0.5 - right * 0.5,
                           center - up * 0.5 - right * 0.5,
                           center - up * 0.5 + right * 0.5)
                corners = [corner.flatten(self.camera) for corner in corners]
                corners = [(int(corner[0]), int(corner[1])) for corner in corners]
                cv.FillConvexPoly(cv.fromarray(vis), 
                    corners, colorTuple(self.colors[i]), lineType=4, shift=0)

        for i in xrange(len(self.colors)):
            (center, norm, up, right) = self.faceInfo(i)
            if norm ** (center - self.camera.pos) < 0:
                corners = (center + up * 0.5 + right * 0.5,
                           center + up * 0.5 - right * 0.5,
                           center - up * 0.5 - right * 0.5,
                           center - up * 0.5 + right * 0.5)
                corners = [corner.flatten(self.camera) for corner in corners]
                corners = [(int(corner[0]), int(corner[1])) 
                            for corner in corners]

                for j in xrange(len(corners)):
                    k = (j + 1) % (len(corners))
                    cv.Line(cv.fromarray(vis), corners[j], corners[k], (0,0,0))

    def setColors(self, colors, faceIndex):
        if faceIndex > 5:
            return
        i = faceIndex * 9
        for c in colors:
            self.colors[i] = c
            i += 1

    def setColor(self, index, color):
        self.colors[index] = color

    def toStream(self):
        stream = Stream()
        stream.logFace(self.colors[:9])
        stream.logTurn('up')
        stream.logFace(self.colors[9:18])
        stream.logTurn('right')
        stream.logFace(self.colors[18:27])
        stream.logTurn('right')
        stream.logFace(self.colors[27:36])
        stream.logTurn('right')
        stream.logFace(self.colors[36:45])
        stream.logTurn('up')
        stream.logFace(self.colors[45:])
        return stream



def cubeFromCam(app=None, callback=None):

    # I did not write this code:
    ##############################
    try:
        video_src = sys.argv[1]
    except:
        video_src = 0
    ##############################

    data = Struct()

    data.app = app
    data.after = None
    data.waiting = False
    data.callback = callback

    # I did not write this code:
    ##############################
    data.cam = video.create_capture(video_src)
    cv2.namedWindow('Cube Input')
    ##############################

    data.stream = Stream()
    data.delay = 20
    data.colorSelections = ['red', 'orange', 'yellow', 
                            'green', 'blue', 'white']
    data.colorSelectionStartX = 20
    data.colorSelectionStartY = 400
    data.colorSelectionWidth = 40
    data.colorSelectionHeight = 40
    data.cube = DemoCube()
    data.numLogged = 0
    data.showingSelector = False
    data.selectionIndex= 0
    mouse = lambda e,x,y,f,p: onMouse(e,x,y,f,p, data)
    cv2.setMouseCallback('Cube Input', mouse)

    (x, y, dx, dy, margin, rows, cols) = (400, 100, 150, 150, 10, 3, 3)
    data.regions = [ ]
    for row in xrange(rows):
        for col in xrange(cols):
            data.regions.append((x + col * dx + margin,
                                 y + row * dy + margin,
                                 x + (col + 1) * dx - margin,
                                 y + (row + 1) * dy - margin))

    while timer(data): pass

def timer(data):
    # I did not write this code:
    ##############################
    ret, frame = data.cam.read()
    vis = frame.copy()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(hsv, np.array((0., 60., 50.)),
                            np.array((180., 255., 255.)))
    ##############################

    mask2 = cv2.inRange(hsv, np.array((0., 0., 0.)), 
                             np.array((180., 255., 255.)))

    texts = [ ]
    colors = [ ]

    for (x0, y0, x1, y1) in data.regions:
        (w, h) = (x1 - x0, y1 - y0)
        (x0m, y0m, x1m, y1m) = (x0 + w/5, y0 + h/5, x1 - w/5, y1 - h/5)

        # I did not write this code:
        ##############################
        hsv_roi = hsv[y0m:y1m, x0m:x1m]
        mask_roi = mask[y0m:y1m, x0m:x1m]
        ##############################

        mask_roi2 = mask2[y0m:y1m, x0m:x1m]

        # I did not write this code:
        ##############################
        histHue = cv2.calcHist( [hsv_roi], [0], mask_roi, [50], [0, 180] )
        ##############################

        histSat = cv2.calcHist( [hsv_roi], [1], mask_roi2, [50], [0, 180] )
        histVal = cv2.calcHist( [hsv_roi], [2], mask_roi2, [50], [0, 180] )

        # I did not write this code:
        ##############################
        cv2.normalize(histHue, histHue, 0, 255, cv2.NORM_MINMAX);
        histHue = histHue.reshape(-1)
        ##############################

        histSat = histSat.reshape(-1)
        histVal = histVal.reshape(-1)

        hue = histMode(histHue, 180.)
        sat = histMode(histSat, 255.)
        val = histMode(histVal, 255.)

        rgb_inRegion = vis[y0m:y1m, x0m:x1m]

        avghsv = (hue, sat, val)
        avgrgb = averageRGB(rgb_inRegion)

        color = colorByRGB(avgrgb, avghsv)
        colors.append(color)

        cv2.rectangle(vis, (x0, y0), (x1, y1), (255, 255, 255))
        texts.append((vis.shape[1] - (x0+x1) / 2, (y0 + y1) / 2, str(color)))

    vis = vis[::,::-1].copy()

    for (x, y, color) in texts:
        fill = (255,255,255) if color in ('blue', 'green', 'red') else (0,0,0)
        cv2.putText(vis, color, (x, y), cv2.FONT_HERSHEY_PLAIN, 1, fill)

    cv2.rectangle(vis, (0, 0), (400, 1200), (0,0,0), -1)
    wid = vis.shape[1]
    cv2.rectangle(vis, (wid-400, 0), (wid, 1200), (0,0,0), -1)

    data.cube.setColors(colors, data.numLogged)
    data.cube.draw(vis)

    if data.waiting:
        help = ["Press spacebar to advance", 
                "to the next face.", 
                "or click on a square", 
                "to change its color."]
    else:
        i = data.numLogged+1
        help = ["Press spacebar to", 
                "lock this face.",
                "You may manually adjust", 
                "the cube once it is locked.",
                "You are currently logging the %d%s face." % (i, suff(i))]

    startY = 25
    startX = 25

    for h in help:
        white = (255,255,255)
        cv2.putText(vis, h,(startX, startY), fnt, 1, white)
        startY += 20

    tips = [ "Red looks like orange?",
    "Move somewhere with more light.",
    "Non-white looks like white?",
    "Tilt your cube up, down, left, or right.",
    "Still not working",
    "Press spacebar and then click on the",
    "incorrect color to manually select the",
    "color it should be.",
    "",
    "Press ESC to close this window."
    ]

    startY = 25
    startX = wid - 375

    for tip in tips:
        white = (255,255,255)
        cv2.putText(vis, tip, (startX, startY), fnt, 1, white)
        startY += 20

    if data.showingSelector:
        xNow = data.colorSelectionStartX
        yNow = data.colorSelectionStartY
        (wNow, hNow) = (data.colorSelectionWidth, data.colorSelectionHeight)
        for colorSelect in data.colorSelections:
            p1 = (xNow, yNow)
            p2 = (xNow + wNow, yNow + hNow)
            cv2.rectangle(vis, p1, p2, colorTuple(colorSelect), -1)
            xNow += wNow

    # I did not write this code:
    ##############################
    cv2.imshow('Cube Input', vis)

    ch = 0xff & cv2.waitKey(20) # Gets keyboard input
    ##############################

    if ch == 32: # Spacebar
        data.showingSelector = False
        if data.waiting:
            data.cube.faceIndex += 1
        else:
            data.stream.logFace(colors)
            data.numLogged += 1
        data.waiting = not data.waiting

        if data.numLogged in (1, 5):
            data.stream.logTurn('up')
        else:
            data.stream.logTurn('right')

    if ch == 27 or data.cube.faceIndex == 6: # Escape key
        data.callback(data.cube.toStream())
        # I did not write this code:
        ##############################
        cv2.destroyAllWindows()
        ##############################
        return False

    return True
########NEW FILE########
__FILENAME__ = solutions
# solutions.py
# Chris Barker
# CMU S13 15-112 Term Project

# solutions.beginner3Layer(state) takes a CubeState (see cube.py)
# and returns a list of moves.

from geometry import *
import time
import datetime

SOLVED_STATE = [[[ ( 1, 210), ( 2, 210), ( 3, 210) ],
                [ ( 4, 210), ( 5, 210), ( 6, 210) ],
                [ ( 7, 210), ( 8, 210), ( 9, 210) ]],

               [[ (10, 210), (11, 210), (12, 210) ],
                [ (13, 210), (14, 210), (15, 210) ],
                [ (16, 210), (17, 210), (18, 210) ]],

               [[ (19, 210), (20, 210), (21, 210) ],
                [ (22, 210), (23, 210), (24, 210) ],
                [ (25, 210), (26, 210), (27, 210) ]]]
CUBE_DIMENSION = 3
MOVE_CODES = { K_HAT: 'U',
              -K_HAT: 'D',
              -I_HAT: 'L',
               I_HAT: 'R',
               J_HAT: 'F',
              -J_HAT: 'B'}

COLOR_CODES =    { I_HAT : 'green',
                  -I_HAT : 'blue',
                   J_HAT : 'red',
                  -J_HAT : 'orange',
                   K_HAT : 'yellow',
                  -K_HAT : 'white'}

def valueAtPos(vec, state):
    (x, y, z) = vec.components
    (x, y, z) = (int(x+1), int(y+1), int(z+1))
    return state.state[z][y][x]
def solutionAtPos(vec):
    (x, y, z) = vec.components
    (x, y, z) = (int(x+1), int(y+1), int(z+1))
    return SOLVED_STATE[z][y][x]
def posOfVal(val, state):
    for z in xrange(CUBE_DIMENSION):
        for y in xrange(CUBE_DIMENSION):
            for x in xrange(CUBE_DIMENSION):
                if hasattr(state, 'state'):
                    if state.state[z][y][x][0] == val:
                        return Vector(x-1, y-1, z-1)
                else:
                    if state[z][y][x][0] == val:
                        return Vector(x-1, y-1, z-1)
def makeMoves(axes, state, moves, status='Solving'):
    for axis in axes:
        move = MOVE_CODES[axis[0]]
        if axis[1]: move += "'"
        state.rotate(state.rotationInfo(move))
        move = (move, status)
        moves.append(move)

class Struct(): pass

def getPerpendicular(vec):
    if vec // K_HAT:
        val = +J_HAT
    else: val = +K_HAT
    return val

def refine(L):
    while True:
        for i in xrange(len(L) - 1):
            if i+2 != len(L) and L[i][0] == L[i+1][0] == L[i+2][0]:
                if "'" in L[i][0]:
                    L[i:i+3] = [(L[i][0][0], L[i][1])]
                else:
                    L[i:i+3] = [(L[i][0] + "'", L[i][1])]
                break
            if L[i][0] == L[i+1][0] + "'" or L[i+1][0] == L[i][0] + "'":
                L[i:i+2] = []
                break
        else:
            break

def determineFixTXB(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    orientation = info.orientation
    posOfValue = info.posOfValue

    if desiredValue == currentValue:
        # Correct location
        if desiredOrientation == currentOrientation:
            return retain
        else:
            return flipTopCrossBeginner
    else:
        # Incorrect location
        if posOfValue ** topLayer > 0:
            # Elsewhere on the top layer
            if orientation / 100 == desiredOrientation / 100:
                # Same color facing upward
                return relocateTopLayerTXB
            else:
                # Top-layer color not facing up
                return reorientTopLayerTXB

        elif posOfValue ** topLayer == 0:
            return secondLayerTXB

        else:
            if orientation / 100 == desiredOrientation / 100:
                return relocateBottomLayerTXB
            else:
                return reorientBottomLayerTXB

def determineFixTCB(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    if desiredValue == currentValue:
        if desiredOrientation == currentOrientation:
            # Already where we want it
            return retain
        else:
            return flipTopTCB
    else:
        if posOfValue ** topLayer > 0:
            # Elsewhere on the top layer
            return moveCornerDown

        else:
            # On the bottom layer
            return moveCornerUp

def determineFixSLB(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    if desiredValue == currentValue:
        desO = list(str(desiredOrientation))
        curO = list(str(currentOrientation))
        desO.remove('2')
        curO.remove('2')
        if desO == curO:
            return retain
        else:
            return moveSecondLayerDown
    else:
        if posOfValue ** topLayer < 0:
            return moveSecondLayerUp
        else:
            return moveSecondLayerDown

def retain(info): return

def named(pieceId):
    pos = posOfVal(pieceId, SOLVED_STATE)
    colors = [COLOR_CODES[k] for k in COLOR_CODES if k**pos > 0]

    if len(colors) == 2:
        return 'the %s and %s edge piece' % (colors[0], colors[1])
    elif len(colors) == 3:
        msg = 'the %s, %s, and %s corner piece'
        return msg % (colors[0], colors[1], colors[2])
    else:
        return str(colors)

def flipTopCrossBeginner(info):
    axesToRotate = [
                    # Put the piece on the second layer
                    (info.pos - (info.pos > info.topLayer), False),
                    (info.topLayer, True), # Rotate the top layer
                    # Put the piece back on the top layer
                    (info.pos * info.topLayer, False), 
                    (info.topLayer, False) # Put the top layer back
                ]
    msg = "Flipping %s on the first layer." % (named(info.desiredValue))
    makeMoves(axesToRotate, info.state, info.moves, msg)

def relocateTopLayerTXB(info):
    desiredAxis = info.pos - (info.pos > info.topLayer)
    currentAxis = info.posOfValue - (info.posOfValue > info.topLayer)
    if desiredAxis // currentAxis: # Opposite side
        numRotations = 2
    elif (desiredAxis * currentAxis) ** info.topLayer < 0:
        numRotations = -1
    else:
        numRotations = 1
    axesToRotate = [ ]
    axesToRotate.append((currentAxis, False))
    for i in xrange(abs(numRotations)):
        axesToRotate.append((info.topLayer, numRotations < 0))
    axesToRotate.append((currentAxis, True))
    for i in xrange(abs(numRotations)):
        axesToRotate.append((info.topLayer, numRotations > 0))
    msg = 'Moving %s into place.' % named(info.desiredValue)
    makeMoves(axesToRotate, info.state, info.moves, msg)

def reorientTopLayerTXB(info):
    desiredAxis = info.pos - (info.pos > info.topLayer)
    currentAxis = info.posOfValue - (info.posOfValue > info.topLayer)
    if desiredAxis // currentAxis: # Opposite side
        numRotations = 1
    elif (desiredAxis * currentAxis) ** info.topLayer < 0:
        numRotations = 2
    else:
        numRotations = 0
    axesToRotate = [ ]
    axesToRotate.append((currentAxis, False))
    for i in xrange(abs(numRotations)):
        axesToRotate.append((info.topLayer, numRotations < 0))
    axesToRotate.append((currentAxis * info.topLayer, False))
    for i in xrange(abs(numRotations)):
        axesToRotate.append((info.topLayer, numRotations > 0))

    msg = "Relocating %s on the first layer." % (named(info.desiredValue))

    makeMoves(axesToRotate, info.state, info.moves, msg)

def secondLayerTXB(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    orientation = str(orientation)
    orientation = list(orientation)
    orientation.remove('2')
    if len(orientation) == 2: # The top-facing is on the y-face
        rotating = +I_HAT
    else: rotating = +J_HAT
    if rotating ** posOfValue < 0:
        rotating = rotating * -1
    cclock = False
    if (rotating * topLayer) ** posOfValue > 0:
        cclock = True

    desiredAxis = pos - (pos > topLayer)
    currentAxis = rotating
    if desiredAxis // currentAxis:
        if desiredAxis ** currentAxis > 0:
            numRotations = 0
        else:
            numRotations = 2
    elif (desiredAxis * currentAxis) ** topLayer < 0:
        numRotations = 1
    else:
        numRotations = -1
    axesToRotate = [ ]
    for i in xrange(abs(numRotations)):
        axesToRotate.append((topLayer, numRotations > 0))
    axesToRotate.append((currentAxis, cclock))
    for i in xrange(abs(numRotations)):
        axesToRotate.append((topLayer, numRotations < 0))

    task = 'Moving %s from the second layer to the first layer.' 
    msg = task % (named(info.desiredValue))

    makeMoves(axesToRotate, state, moves, msg)

def relocateBottomLayerTXB(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    desiredAxis = pos - (pos > topLayer)
    currentAxis = posOfValue - (posOfValue > topLayer)
    if desiredAxis // currentAxis:
        if desiredAxis ** currentAxis > 0:
            numRotations = 0
        else:
            numRotations = 2
    elif (desiredAxis * currentAxis) ** topLayer < 0:
        numRotations = 1
    else:
        numRotations = -1

    axesToRotate = [ ]
    for i in xrange(abs(numRotations)):
        axesToRotate.append(( -1 * topLayer, numRotations > 0))
    axesToRotate.append((desiredAxis, True))
    axesToRotate.append((desiredAxis, True))
    task = 'Moving %s from the third layer to the first layer.'
    msg = task % (named(info.desiredValue))
    makeMoves(axesToRotate, state, moves, msg)

def reorientBottomLayerTXB(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    desiredAxis = pos - (pos > topLayer)
    currentAxis = posOfValue - (posOfValue > topLayer)
    if desiredAxis // currentAxis:
        if desiredAxis ** currentAxis > 0:
            numRotations = 0
        else:
            numRotations = 2
    elif (desiredAxis * currentAxis) ** topLayer < 0:
        numRotations = 1
    else:
        numRotations = -1

    axesToRotate = [ ]
    for i in xrange(abs(numRotations)):
        # Rotate top to correct position
        axesToRotate.append(( topLayer, numRotations > 0))

    # Move piece up to second layer
    axesToRotate.append((currentAxis, False)) 

    # Move open space on top layer accordingly
    axesToRotate.append((topLayer, False))
    axesToRotate.append((topLayer * currentAxis, True))
    axesToRotate.append((topLayer, True))
    for i in xrange(abs(numRotations)):
        axesToRotate.append(( topLayer, numRotations < 0))
    task = 'Moving %s from the third layer to the first layer.'
    msg =  task % (named(info.desiredValue))
    makeMoves(axesToRotate, state, moves, msg)

def flipTopTCB(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    orientation = str(orientation)
    orientation = list(orientation)
    if len(orientation) == 2:
        orientation = ['0'] + orientation
    if orientation[0] == '0': # The top-facing is on the x-face
        (rotating, other) = (+I_HAT, +J_HAT)
    else: (rotating, other) = (+J_HAT, +I_HAT)
    if rotating ** posOfValue < 0:
        rotating = rotating * -1
    if other ** posOfValue < 0:
        other = other * -1

    cclock = (rotating * other) ** topLayer > 0

    axesToRotate = [ ]

    axesToRotate.append((rotating, cclock))
    axesToRotate.append((topLayer * -1, cclock))
    axesToRotate.append((rotating, not cclock))
    axesToRotate.append((topLayer * -1, not cclock))
    axesToRotate.append((rotating, cclock))
    axesToRotate.append((topLayer * -1, cclock))
    axesToRotate.append((rotating, not cclock))

    msg = 'Rotating %s on the first layer.' % named(info.desiredValue)

    makeMoves(axesToRotate, state, moves, msg)

def moveCornerDown(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    (axis0, axis1) = (+I_HAT, +J_HAT)
    if axis0 ** posOfValue < 0:
        axis0 = axis0 * -1
    if axis1 ** posOfValue < 0:
        axis1 = axis1 * -1

    if (axis1 * axis0) ** topLayer < 0:
        (axis1, axis0) = (axis0, axis1)

    axesToRotate = [ ]
    axesToRotate.append((axis1, True))
    axesToRotate.append((topLayer * -1, False))
    axesToRotate.append((axis1, False))

    task = 'Moving %s from the first layer to the third layer.'
    msg = task % named(info.desiredValue)

    makeMoves(axesToRotate, state, moves, msg)

def moveCornerUp(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    (axis0, axis1) = (+I_HAT, +J_HAT)
    if axis0 ** pos < 0:
        axis0 = axis0 * -1
    if axis1 ** pos < 0:
        axis1 = axis1 * -1
    if (axis1 * axis0) ** topLayer < 0:
        (axis1, axis0) = (axis0, axis1)

    pos = pos - (pos > topLayer)
    posOfValue = posOfValue - (posOfValue > topLayer)
    if (pos * posOfValue) ** topLayer > 0:
        numRotations = 1
    elif (pos * posOfValue) ** topLayer < 0:
        numRotations = -1
    else:
        if pos ** posOfValue > 0:
            numRotations = 0
        else:
            numRotations = 2

    axesToRotate = [ ]
    for i in xrange(abs(numRotations)):
        axesToRotate.append((topLayer * -1, numRotations < 0))
    axesToRotate.append((axis1, True))
    axesToRotate.append((topLayer * -1, True))
    axesToRotate.append((axis1, False))

    task = 'Moving %s from the third layer to the first layer.'
    msg = task % named(info.desiredValue)

    makeMoves(axesToRotate, state, moves, msg)

def moveSecondLayerDown(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    (axis0, axis1) = (+I_HAT, +J_HAT)
    if axis0 ** posOfValue < 0:
        axis0 = axis0 * -1
    if axis1 ** posOfValue < 0:
        axis1 = axis1 * -1
    if (axis1 * axis0) ** topLayer < 0:
        (axis1, axis0) = (axis0, axis1)

    axesToRotate = [ ]
    axesToRotate.append((axis1, True))
    axesToRotate.append((topLayer * -1, False))
    axesToRotate.append((axis1, False))
    axesToRotate.append((topLayer * -1, False))
    axesToRotate.append((axis0, False))
    axesToRotate.append((topLayer * -1, True))
    axesToRotate.append((axis0, True))

    task = 'Moving %s from the second layer to the third layer temporarily.'
    msg = task % named(info.desiredValue)

    makeMoves(axesToRotate, state, moves, msg)

def moveSecondLayerUp(info):
    pos = info.pos
    desiredValue = info.desiredValue
    desiredOrientation = info.desiredOrientation
    currentValue = info.currentValue
    currentOrientation = info.currentOrientation
    topLayer = info.topLayer
    state = info.state
    moves = info.moves
    orientation = info.orientation
    posOfValue = info.posOfValue

    currentAxis = posOfValue - (posOfValue > topLayer)

    (axis0, axis1) = (+I_HAT, +J_HAT)
    if axis0 ** pos < 0:
        axis0 = axis0 * -1
    if axis1 ** pos < 0:
        axis1 = axis1 * -1
    if (axis1 * axis0) ** topLayer < 0:
        (axis1, axis0) = (axis0, axis1)

    orientation = list(str(orientation))
    # what matters is whether z comes first or not
    if len(orientation) == 2:
        orientation = ['0'] + orientation
    if posOfValue ** I_HAT == 0:
        orientation.remove('0')
    if posOfValue ** J_HAT == 0:
        orientation.remove('1')

    if orientation[0] == '2':
        # The Y value is displayed on the Z axis
        # So the X value is displayed above
        setupAxis = pos > I_HAT
    else:
        setupAxis = pos > J_HAT
    

    if setupAxis // currentAxis:
        if setupAxis ** currentAxis > 0:
            numRotations = 0
        else:
            numRotations = 2
    elif (setupAxis * currentAxis) ** topLayer < 0:
        numRotations = 1
    else:
        numRotations = -1

    axesToRotate = [ ]

    for i in xrange(abs(numRotations)):
        axesToRotate.append((-1 * topLayer, numRotations > 0))

    if (setupAxis * pos) ** topLayer > 0:
        # Right side
        axesToRotate.append((topLayer * -1, False))
        axesToRotate.append((axis0, False))
        axesToRotate.append((topLayer * -1, True))
        axesToRotate.append((axis0, True))
        axesToRotate.append((topLayer * -1, True))
        axesToRotate.append((axis1, True))
        axesToRotate.append((topLayer * -1, False))
        axesToRotate.append((axis1, False))
    else:
        # Left side
        axesToRotate.append((topLayer * -1, True))
        axesToRotate.append((axis1, True))
        axesToRotate.append((topLayer * -1, False))
        axesToRotate.append((axis1, False))
        axesToRotate.append((topLayer * -1, False))
        axesToRotate.append((axis0, False))
        axesToRotate.append((topLayer * -1, True))
        axesToRotate.append((axis0, True))

    msg = 'Moving %s from the third layer to the second layer.' % (
        named(info.desiredValue))

    makeMoves(axesToRotate, state, moves, msg)

def topCrossBeginner(state, topLayer, log):
    moves = [ ]

    axis0 = getPerpendicular(topLayer)
    axis1 = topLayer * axis0
    topCross = [ topLayer + axis0 ,
                 topLayer - axis0 ,
                 topLayer + axis1 ,
                 topLayer - axis1]

    for pos in topCross:

        (desiredValue, desiredOrientation) = solutionAtPos(pos)
        (currentValue, currentOrientation) = valueAtPos(pos, state)
        posOfValue = posOfVal(desiredValue, state)
        orientation = valueAtPos(posOfValue, state)[1]

        info = Struct()
        info.desiredValue = desiredValue
        info.desiredOrientation = desiredOrientation
        info.pos = pos
        info.moves = moves
        info.currentValue = currentValue
        info.currentOrientation = currentOrientation
        info.state = state
        info.orientation = orientation
        info.topLayer = topLayer
        info.posOfValue = posOfValue

        fix = determineFixTXB(info)
        fix(info)

    log.append('TXB:%d' % (len(moves)))
    return moves

def topCornersBeginner(state, topLayer, log):
    moves = [ ]

    axis0 = getPerpendicular(topLayer)
    axis1 = topLayer * axis0

    topCorners = [ topLayer + axis0 + axis1,
                   topLayer + axis0 - axis1,
                   topLayer - axis0 + axis1,
                   topLayer - axis0 - axis1 ]

    doneUp = done = False

    while not done:

        changedThisRound = False

        for pos in topCorners:

            fix = None
            count = 0

            (desiredValue, desiredOrientation) = solutionAtPos(pos)
            (currentValue, currentOrientation) = valueAtPos(pos, state)
            posOfValue = posOfVal(desiredValue, state)
            orientation = valueAtPos(posOfValue, state)[1]

            info = Struct()
            info.desiredValue = desiredValue
            info.desiredOrientation = desiredOrientation
            info.pos = pos
            info.moves = moves
            info.currentValue = currentValue
            info.currentOrientation = currentOrientation
            info.state = state
            info.orientation = orientation
            info.topLayer = topLayer
            info.posOfValue = posOfValue

            fix = determineFixTCB(info)

            if (((fix == flipTopTCB) or (fix == moveCornerDown))
                    and (not doneUp)):
                continue
            else:
                fix(info)
                changedThisRound = changedThisRound or fix != retain

        done = (not changedThisRound) and doneUp
        doneUp = not changedThisRound

    log.append('TCB:%d' % (len(moves)))
    return moves

def secondLayerBeginner(state, topLayer, log):
    moves = [ ]

    axis0 = getPerpendicular(topLayer)
    axis1 = topLayer * axis0
    secondLayer = [axis0 + axis1,
                   axis0 - axis1,
                   (-1 * axis0) + axis1,
                   (-1 * axis0) - axis1]


    doneUp = False
    done = False

    while not done:

        changedThisRound = False
        for pos in secondLayer:

            fix = None
            count = 0

            (desiredValue, desiredOrientation) = solutionAtPos(pos)
            (currentValue, currentOrientation) = valueAtPos(pos, state)
            posOfValue = posOfVal(desiredValue, state)
            orientation = valueAtPos(posOfValue, state)[1]

            info = Struct()
            info.desiredValue = desiredValue
            info.desiredOrientation = desiredOrientation
            info.pos = pos
            info.moves = moves
            info.currentValue = currentValue
            info.currentOrientation = currentOrientation
            info.state = state
            info.orientation = orientation
            info.topLayer = topLayer
            info.posOfValue = posOfValue

            fix = determineFixSLB(info)
            if fix == moveSecondLayerDown and not doneUp:
                continue
            else:
                fix(info)
                changedThisRound = changedThisRound or fix != retain

        done = (not changedThisRound) and doneUp
        doneUp = not changedThisRound

    log.append('SLB:%d' % (len(moves)))
    return moves

def thirdLayerCornerOrientation(state, topLayer, log):
    moves = [ ]

    axis0 = getPerpendicular(topLayer)
    axis1 = topLayer * axis0

    bottomLayer = topLayer * -1
    bottomCorners = [ bottomLayer + axis0 + axis1,
                   bottomLayer + axis0 - axis1,
                   bottomLayer - axis0 + axis1,
                   bottomLayer - axis0 - axis1 ]

    # Bottom, right, top, left
    axes = [ axis0, axis1, -1 * axis0, -1 * axis1]

    count = 50
    while count > 0:
        orientations = [valueAtPos(corner,state)[1] for 
                        corner in bottomCorners]
        facingDowns = [i for i in bottomCorners if valueAtPos(i,state)[1] > 200]
        facingXs = [i for i in bottomCorners if valueAtPos(i,state)[1] < 100]
        facingYs = [i for i in bottomCorners if 100 < valueAtPos(i,state)[1] < 200]
        numFacingDown = len(facingDowns)
        if numFacingDown == 4:
            break
        elif numFacingDown == 3:
            raise ValueError('Impossible cube!')
        elif numFacingDown == 2:
            pos0 = facingDowns[0]
            pos1 = facingDowns[1]
            if pos0 // pos1:
                pos = facingDowns[0]
                pos = pos - (pos > bottomLayer)
                operator = ((bottomLayer * pos) + pos) / 2
            else:
                if len(facingXs) == 2:
                    if ((I_HAT ** facingXs[0]) * 
                        (I_HAT ** facingXs[1]) > 0):
                        operator = (facingXs[0] > -I_HAT) ^ 1
                    else:
                        pos = facingXs[0] + facingXs[1]
                        operator = (bottomLayer * pos) ^ 1
                elif len(facingYs) == 2:
                    if ((J_HAT ** facingYs[0]) *
                        (J_HAT ** facingYs[1]) > 0):
                        operator = (facingYs[0] > -J_HAT) ^ 1
                    else:
                        pos = facingYs[0] + facingYs[1]
                        operator = (bottomLayer * pos) ^ 1
                else:
                    operator = +I_HAT

                
        elif numFacingDown == 1:
            pos = facingDowns[0]
            pos = pos - (pos > bottomLayer) 
            operator = ((bottomLayer * pos) - pos) / 2
        elif numFacingDown == 0:
            if len(facingXs) == 4:
                operator = +I_HAT
            elif len(facingXs) == 0:
                operator = +J_HAT
            else:
                if ((I_HAT ** facingXs[0]) * 
                    (I_HAT ** facingXs[1]) > 0):
                    # The Xs are facing the same direction
                    unequals = (facingXs[0] > I_HAT) ^ 1
                else:
                    unequals = (facingYs[0] > J_HAT) ^ 1
                pos = unequals - (unequals > bottomLayer)
                operator = ((pos * bottomLayer) ^ 1)

        try:
            s = MOVE_CODES[operator]
        except:
            print 'UNTREATED CASE.',
            print 'numFacingDown = %d.' % (numFacingDown),
            print 'facingXs=%s, facingYs%s, facingDowns%s' % (
                facingXs, facingYs, facingDowns)
            break

        axesToRotate = [ (operator, True), (bottomLayer, True),
                         (operator, False), (bottomLayer, True), 
                         (operator, True), (bottomLayer, True),
                         (bottomLayer, True), (operator, False) ]

        msg = 'Orienting the third layer corners by rotating %s and %s.' % (
            COLOR_CODES[operator], COLOR_CODES[bottomLayer])

        makeMoves(axesToRotate, state, moves, msg)

        count -= 1
    else:
        raise ValueError('Could not generate solution.')

    log.append('BCO:%d' % (len(moves)))

    return moves

def thirdLayerEdgeOrientation(state, topLayer, log):
    moves = [ ]

    axis0 = getPerpendicular(topLayer)
    axis1 = topLayer * axis0

    bottomLayer = topLayer * -1
    bottomEdges = [ bottomLayer + axis0,
                    bottomLayer - axis0,
                    bottomLayer + axis1,
                    bottomLayer - axis1]

    count = 50
    while count > 0:
        orientations = [valueAtPos(edge,state)[1] for edge in bottomEdges]
        facingDowns = [ ]
        facingXs = [ ]
        facingYs = [ ]
        for edge in bottomEdges:
            (pos, orient) = valueAtPos(edge, state)
            orient = list(str(orient))
            if len(orient) == 2:
                orient = ['0'] + orient
            if edge ** I_HAT == 0:
                orient.remove('0')
            if edge ** J_HAT == 0:
                orient.remove('1')
            if edge ** K_HAT == 0:
                orient.remove('2')

            if orient[0] == '2':
                facingDowns.append(edge)
            elif orient[0] == '1':
                facingYs.append(edge)
            elif orient[0] == '0':
                facingXs.append(edge)

        numFacingDown = len(facingDowns)

        if numFacingDown == 4:
            break
        elif numFacingDown == 3:
            return
            raise ValueError('Impossible cube! 3 down')
        elif numFacingDown == 2:
            if len(facingXs) == 1:
                # Diagonal case
                if (facingXs[0] * facingYs[0]) ** bottomLayer < 0:
                    operator = facingXs[0] > (-I_HAT)
                else:
                    operator = facingYs[0] > (-J_HAT)
            else:
                if len(facingXs) == 2:
                    operator = +J_HAT
                else:
                    operator = +I_HAT
        elif numFacingDown == 1:
            return
            raise ValueError('Impossible cube! Only 1 down')
        elif numFacingDown == 0:
            operator = +I_HAT

        axesToRotate = [ ]
        
        front = operator
        right = front * bottomLayer

        axesToRotate.append((right, True))
        axesToRotate.append((bottomLayer, True))
        axesToRotate.append((front, True))
        axesToRotate.append((bottomLayer, False))
        axesToRotate.append((front, False))
        axesToRotate.append((right, False))

        msg = 'Orienting third layer edges.'

        makeMoves(axesToRotate, state, moves, msg)

        count -= 1
    else:
        raise ValueError('Could not generate solution.')

    log.append('BEO:%d' % (len(moves)))
    return moves

def thirdLayerCornerPermutation(state, topLayer, log):
    moves = [ ]

    axis0 = getPerpendicular(topLayer)
    axis1 = topLayer * axis0

    bottomLayer = topLayer * -1
    bottomCorners = [ bottomLayer + axis0 + axis1,
                   bottomLayer + axis0 - axis1,
                   bottomLayer - axis0 - axis1,
                   bottomLayer - axis0 + axis1 ]

    count = 50
    while count > 0:
        adjacentPairs = [ ]

        for i in xrange(len(bottomCorners)):
            corner1 = bottomCorners[i]
            corner2 = bottomCorners[(i+1) % (len(bottomCorners))]

            # what we have at corner 1 right now
            (currentValue1, currentOrientation1) = valueAtPos(corner1, state)
            # where that piece should be
            desired1 = posOfVal(currentValue1, SOLVED_STATE)

            # what we have at corner 2 right now
            (currentValue2, currentOrientation2) = valueAtPos(corner2, state)
            # where that piece should be
            desired2 = posOfVal(currentValue2, SOLVED_STATE)

            if not ((desired1 - bottomLayer) // (desired2 - bottomLayer)):
                # they are adjacent corners
                if (((desired1 - bottomLayer) * (desired2 - bottomLayer)) ** 
                    ((corner1 - bottomLayer) * (corner2 - bottomLayer))) > 0:
                    # correct orientation
                    adjacentPairs.append((corner1, corner2))

        if len(adjacentPairs) == 4:
            break
        elif len(adjacentPairs) == 0:
            operator = +I_HAT
        elif len(adjacentPairs) == 1:
            (corner1, corner2) = adjacentPairs[0]
            nonOp = (corner1 - bottomLayer) + (corner2 - bottomLayer)
            operator = (-1 * nonOp) / 2
        else:
            print adjacentPairs
            print state
            raise ValueError('bad corners')

        top = bottomLayer
        front = operator
        back = operator * -1
        right = operator * bottomLayer

        axesToRotate = [ (right,  True), (front, False), (right,  True),
                         ( back,  True), ( back,  True), (right, False),
                         (front,  True), (right,  True), ( back,  True),
                         ( back,  True), (right,  True), (right,  True) ]

        task = 'Permuting third layer corners.'
        msg='%s. So far, %d %s permuted correctly.' % (
            task, len(adjacentPairs), 'pair is' if 
            len(adjacentPairs) == 1 else 'pairs are')

        makeMoves(axesToRotate, state, moves, msg)
        count -= 1
    else:
        raise ValueError('Could not generate solution.')

    posOfValue = bottomCorners[0]
    val = valueAtPos(posOfValue, state)
    solvedPos = posOfVal(val[0], SOLVED_STATE)

    if (solvedPos * posOfValue) ** topLayer > 0:
        numRotations = 1
    elif (solvedPos * posOfValue) ** topLayer < 0:
        numRotations = -1
    else:
        if solvedPos ** posOfValue > 0:
            numRotations = 0
        else:
            numRotations = 2

    axesToRotate = [ ]
    for i in xrange(abs(numRotations)):
        axesToRotate.append((bottomLayer, numRotations < 0))

    msg = 'Rotating third layer to align corners.'

    makeMoves(axesToRotate, state, moves, msg)


    log.append('BCP:%d' % (len(moves)))
    return moves

def thirdLayerEdgePermutation(state, topLayer, log):
    moves = [ ]

    axis0 = getPerpendicular(topLayer)
    axis1 = topLayer * axis0

    bottomLayer = topLayer * -1
    bottomEdges = [ bottomLayer + axis0,
                bottomLayer - axis0,
                bottomLayer + axis1,
                bottomLayer - axis1]

    count = 10
    while count != 0:
        corrects = [ ]
        for pos in bottomEdges:
            if valueAtPos(pos, state)[0] == solutionAtPos(pos)[0]:
                corrects.append(pos)

        if len(corrects) == 4:
            break
        elif len(corrects) == 0:
            operator = +I_HAT
        elif len(corrects) == 1:
            operator = (corrects[0] - bottomLayer) * (-1)

        front = operator
        top = bottomLayer
        right = operator * bottomLayer

        axesToRotate = [
            (right, False), (  top, False), (right,  True),
            (  top, False), (right, False), (  top, False),
            (  top, False), (right,  True), (front,  True),
            (  top,  True), (front, False), (  top,  True),
            (front,  True), (  top,  True), (  top,  True),
            (front, False),
        ]

        msg='Rotating third layer edges. So far, %d %s permuted correctly.'%(
            len(corrects), 'edge is' if len(corrects) == 1 else 'edges are')

        makeMoves(axesToRotate, state, moves, msg)

        count -= 1
    else:
        raise ValueError("Could not generate solution.")

    log.append('BEP:%d' % (len(moves)))
    return moves

def beginner3Layer(state, topLayer=+K_HAT):
    """A simple human-based algorithm that combines intuition for the
    first layer with short algorithms for the next layers. Here the
    intuition has been made into an algorithm."""
    start = time.time()

    moves = [ ]
    log = [ ]

    # The log records information about solution
    # generations and saves it in solutionLogs.txt
    log.extend([str(datetime.datetime.now()), 'Beginner', state.condense()])

    steps = [topCrossBeginner,
             topCornersBeginner,
             secondLayerBeginner,
             thirdLayerEdgeOrientation,
             thirdLayerCornerOrientation,
             thirdLayerCornerPermutation,
             thirdLayerEdgePermutation]

    for step in steps:
        moves.extend(step(state, topLayer, log))

    refine(moves)

    strMoves = [move[0] for move in moves]
    log.append(''.join(strMoves))
    log.append('Time: ' + str(time.time() - start) + " sec")
    log.append('Moves:' + str(len(moves)))
    log = [str(e) for e in log]
    log = ';'.join(log)

    with open('solutionLogs.txt', 'r+') as file:
        logs = eval(file.read())
        logs.append(log)
        file.seek(0)
        file.truncate()
        file.write("# Datetime, method_name, initial_state, move_data,\
move_string, time_elapsed, total_moves\n")
        file.write(repr(logs))

    return moves
########NEW FILE########
__FILENAME__ = unittests
# unittests.py
# Chris Barker
# CMU S13 15-112 Term Project

from geometry import Vector

def testGeometry():
    print 'testing geometry...',
    vec1 = Vector(1, 2, 3)
    vec2 = Vector(-2, 4, 5)
    assert vec1 + vec2 == Vector(-1, 6, 8)
    assert vec1 ** vec2 == -2 + 8 + 15
    assert vec1 * vec2 == -1 * (vec2 * vec1)
    assert vec1 * -1 == Vector(-1, -2, -3)
    print 'passed!'


if __name__ == '__main__':
    testGeometry()

########NEW FILE########
__FILENAME__ = video
#
#
# This module is provided as a sample with OpenCV
# I did not write any of it
#
#
# This is provided in the OpenCV-2.4.4 release
# Go here for OpenCV downloads: http://opencv.org/downloads.html
#
#


#/usr/bin/env python

'''
Video capture sample.

Sample shows how VideoCapture class can be used to acquire video
frames from a camera of a movie file. Also the sample provides
an example of procedural video generation by an object, mimicking
the VideoCapture interface (see Chess class).

'create_capture' is a convinience function for capture creation,
falling back to procedural video in case of error.

Usage:
    video.py [--shotdir <shot path>] [source0] [source1] ...'

    sourceN is an
     - integer number for camera capture
     - name of video file
     - synth:<params> for procedural video

Synth examples:
    synth:bg=../cpp/lena.jpg:noise=0.1
    synth:class=chess:bg=../cpp/lena.jpg:noise=0.1:size=640x480

Keys:
    ESC    - exit
    SPACE  - save current frame to <shot path> directory

'''

import numpy as np
import cv2
from time import clock
from numpy import pi, sin, cos
import common

class VideoSynthBase(object):
    def __init__(self, size=None, noise=0.0, bg = None, **params):
        self.bg = None
        self.frame_size = (640, 480)
        if bg is not None:
            self.bg = cv2.imread(bg, 1)
            h, w = self.bg.shape[:2]
            self.frame_size = (w, h)

        if size is not None:
            w, h = map(int, size.split('x'))
            self.frame_size = (w, h)
            self.bg = cv2.resize(self.bg, self.frame_size)

        self.noise = float(noise)

    def render(self, dst):
        pass

    def read(self, dst=None):
        w, h = self.frame_size

        if self.bg is None:
            buf = np.zeros((h, w, 3), np.uint8)
        else:
            buf = self.bg.copy()

        self.render(buf)

        if self.noise > 0.0:
            noise = np.zeros((h, w, 3), np.int8)
            cv2.randn(noise, np.zeros(3), np.ones(3)*255*self.noise)
            buf = cv2.add(buf, noise, dtype=cv2.CV_8UC3)
        return True, buf

    def isOpened(self):
        return True

class Chess(VideoSynthBase):
    def __init__(self, **kw):
        super(Chess, self).__init__(**kw)

        w, h = self.frame_size

        self.grid_size = sx, sy = 10, 7
        white_quads = []
        black_quads = []
        for i, j in np.ndindex(sy, sx):
            q = [[j, i, 0], [j+1, i, 0], [j+1, i+1, 0], [j, i+1, 0]]
            [white_quads, black_quads][(i + j) % 2].append(q)
        self.white_quads = np.float32(white_quads)
        self.black_quads = np.float32(black_quads)

        fx = 0.9
        self.K = np.float64([[fx*w, 0, 0.5*(w-1)],
                        [0, fx*w, 0.5*(h-1)],
                        [0.0,0.0,      1.0]])

        self.dist_coef = np.float64([-0.2, 0.1, 0, 0])
        self.t = 0

    def draw_quads(self, img, quads, color = (0, 255, 0)):
        img_quads = cv2.projectPoints(quads.reshape(-1, 3), 
            self.rvec, self.tvec, self.K, self.dist_coef) [0]
        img_quads.shape = quads.shape[:2] + (2,)
        for q in img_quads:
            cv2.fillConvexPoly(img, np.int32(q*4), color, cv2.CV_AA, shift=2)

    def render(self, dst):
        t = self.t
        self.t += 1.0/30.0

        sx, sy = self.grid_size
        center = np.array([0.5*sx, 0.5*sy, 0.0])
        phi = pi/3 + sin(t*3)*pi/8
        c, s = cos(phi), sin(phi)
        ofs = np.array([sin(1.2*t), cos(1.8*t), 0]) * sx * 0.2
        eye_pos = center + np.array([cos(t)*c, sin(t)*c, s]) * 15.0 + ofs
        target_pos = center + ofs

        R, self.tvec = common.lookat(eye_pos, target_pos)
        self.rvec = common.mtx2rvec(R)

        self.draw_quads(dst, self.white_quads, (245, 245, 245))
        self.draw_quads(dst, self.black_quads, (10, 10, 10))


classes = dict(chess=Chess)

presets = dict(
    empty = 'synth:',
    lena = 'synth:bg=../cpp/lena.jpg:noise=0.1',
    chess = 'synth:class=chess:bg=../cpp/lena.jpg:noise=0.1:size=640x480'
)


def create_capture(source = 0, fallback = presets['chess']):
    '''source: <int> or '<int>|<filename>|synth [:<param_name>=<value> [:...]]'
    '''
    source = str(source).strip()
    chunks = source.split(':')
    # hanlde drive letter ('c:', ...)
    if len(chunks) > 1 and len(chunks[0]) == 1 and chunks[0].isalpha():
        chunks[1] = chunks[0] + ':' + chunks[1]
        del chunks[0]

    source = chunks[0]
    try: source = int(source)
    except ValueError: pass
    params = dict( s.split('=') for s in chunks[1:] )

    cap = None
    if source == 'synth':
        Class = classes.get(params.get('class', None), VideoSynthBase)
        try: cap = Class(**params)
        except: pass
    else:
        cap = cv2.VideoCapture(source)
        if 'size' in params:
            w, h = map(int, params['size'].split('x'))
            cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, h)
    if cap is None or not cap.isOpened():
        print 'Warning: unable to open video source: ', source
        if fallback is not None:
            return create_capture(fallback, None)
    return cap

if __name__ == '__main__':
    import sys
    import getopt

    print __doc__

    args, sources = getopt.getopt(sys.argv[1:], '', 'shotdir=')
    args = dict(args)
    shotdir = args.get('--shotdir', '.')
    if len(sources) == 0:
        sources = [ 0 ]

    caps = map(create_capture, sources)
    shot_idx = 0
    while True:
        imgs = []
        for i, cap in enumerate(caps):
            ret, img = cap.read()
            imgs.append(img)
            cv2.imshow('capture %d' % i, img)
        ch = 0xFF & cv2.waitKey(1)
        if ch == 27:
            break
        if ch == ord(' '):
            for i, img in enumerate(imgs):
                fn = '%s/shot_%d_%03d.bmp' % (shotdir, i, shot_idx)
                cv2.imwrite(fn, img)
                print fn, 'saved'
            shot_idx += 1
    cv2.destroyAllWindows()

########NEW FILE########
