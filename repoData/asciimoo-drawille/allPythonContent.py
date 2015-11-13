__FILENAME__ = drawille
# -*- coding: utf-8 -*-

# drawille is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# drawille is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with drawille. If not, see < http://www.gnu.org/licenses/ >.
#
# (C) 2014- by Adam Tauber, <asciimoo@gmail.com>

import math
import os
from sys import version_info
from collections import defaultdict

IS_PY3 = version_info[0] == 3

if IS_PY3:
    unichr = chr

"""

http://www.alanwood.net/unicode/braille_patterns.html

dots:
   ,___,
   |1 4|
   |2 5|
   |3 6|
   |7 8|
   `````
"""

pixel_map = ((0x01, 0x08),
             (0x02, 0x10),
             (0x04, 0x20),
             (0x40, 0x80))

# braille unicode characters starts at 0x2800
braille_char_offset = 0x2800


# http://stackoverflow.com/questions/566746/how-to-get-console-window-width-in-python
def getTerminalSize():
    """Returns terminal width, height
    """
    import os
    env = os.environ

    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except:
            return
        return cr

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)

    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass

    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

    return int(cr[1]), int(cr[0])


def normalize(coord):
    coord_type = type(coord)

    if coord_type == int:
        return coord
    elif coord_type == float:
        return int(round(coord))
    else:
        raise TypeError("Unsupported coordinate type <{0}>".format(type(coord)))


def intdefaultdict():
    return defaultdict(int)


def get_pos(x, y):
    """Convert x, y to cols, rows"""
    return normalize(x) // 2, normalize(y) // 4


class Canvas(object):
    """This class implements the pixel surface."""

    def __init__(self, line_ending=os.linesep):
        super(Canvas, self).__init__()
        self.clear()
        self.line_ending = line_ending


    def clear(self):
        """Remove all pixels from the :class:`Canvas` object."""
        self.chars = defaultdict(intdefaultdict)


    def set(self, x, y):
        """Set a pixel of the :class:`Canvas` object.

        :param x: x coordinate of the pixel
        :param y: y coordinate of the pixel
        """
        x = normalize(x)
        y = normalize(y)
        col, row = get_pos(x, y)

        if type(self.chars[row][col]) != int:
            return

        self.chars[row][col] |= pixel_map[y % 4][x % 2]


    def unset(self, x, y):
        """Unset a pixel of the :class:`Canvas` object.

        :param x: x coordinate of the pixel
        :param y: y coordinate of the pixel
        """
        x = normalize(x)
        y = normalize(y)
        col, row = get_pos(x, y)

        if type(self.chars[row][col]) == int:
            self.chars[row][col] &= ~pixel_map[y % 4][x % 2]

        if type(self.chars[row][col]) != int or self.chars[row][col] == 0:
            del(self.chars[row][col])

        if not self.chars.get(row):
            del(self.chars[row])


    def toggle(self, x, y):
        """Toggle a pixel of the :class:`Canvas` object.

        :param x: x coordinate of the pixel
        :param y: y coordinate of the pixel
        """
        x = normalize(x)
        y = normalize(y)
        col, row = get_pos(x, y)

        if type(self.chars[row][col]) != int or self.chars[row][col] & pixel_map[y % 4][x % 2]:
            self.unset(x, y)
        else:
            self.set(x, y)


    def set_text(self, x, y, text):
        """Set text to the given coords.

        :param x: x coordinate of the text start position
        :param y: y coordinate of the text start position
        """
        col, row = get_pos(x, y)

        for i,c in enumerate(text):
            self.chars[row][col+i] = c


    def get(self, x, y):
        """Get the state of a pixel. Returns bool.

        :param x: x coordinate of the pixel
        :param y: y coordinate of the pixel
        """
        x = normalize(x)
        y = normalize(y)
        dot_index = pixel_map[y % 4][x % 2]
        col, row = get_pos(x, y)
        char = self.chars.get(row, {}).get(col)

        if not char:
            return False

        if type(char) != int:
            return True

        return bool(char & dot_index)


    def rows(self, min_x=None, min_y=None, max_x=None, max_y=None):
        """Returns a list of the current :class:`Canvas` object lines.

        :param min_x: (optional) minimum x coordinate of the canvas
        :param min_y: (optional) minimum y coordinate of the canvas
        :param max_x: (optional) maximum x coordinate of the canvas
        :param max_y: (optional) maximum y coordinate of the canvas
        """

        if not self.chars.keys():
            return []

        minrow = min_y // 4 if min_y != None else min(self.chars.keys())
        maxrow = (max_y - 1) // 4 if max_y != None else max(self.chars.keys())
        mincol = min_x // 2 if min_x != None else min(min(x.keys()) for x in self.chars.values())
        maxcol = (max_x - 1) // 2 if max_x != None else max(max(x.keys()) for x in self.chars.values())
        ret = []

        for rownum in range(minrow, maxrow+1):
            if not rownum in self.chars:
                ret.append('')
                continue

            maxcol = (max_x - 1) // 2 if max_x != None else max(self.chars[rownum].keys())
            row = []

            for x in  range(mincol, maxcol+1):
                char = self.chars[rownum].get(x)

                if not char:
                    row.append(' ')
                elif type(char) != int:
                    row.append(char)
                else:
                    row.append(unichr(braille_char_offset+char))

            ret.append(''.join(row))

        return ret


    def frame(self, min_x=None, min_y=None, max_x=None, max_y=None):
        """String representation of the current :class:`Canvas` object pixels.

        :param min_x: (optional) minimum x coordinate of the canvas
        :param min_y: (optional) minimum y coordinate of the canvas
        :param max_x: (optional) maximum x coordinate of the canvas
        :param max_y: (optional) maximum y coordinate of the canvas
        """
        ret = self.line_ending.join(self.rows(min_x, min_y, max_x, max_y))

        if IS_PY3:
            return ret

        return ret.encode('utf-8')


def line(x1, y1, x2, y2):
    """Returns the coords of the line between (x1, y1), (x2, y2)

    :param x1: x coordinate of the startpoint
    :param y1: y coordinate of the startpoint
    :param x2: x coordinate of the endpoint
    :param y2: y coordinate of the endpoint
    """

    x1 = normalize(x1)
    y1 = normalize(y1)
    x2 = normalize(x2)
    y2 = normalize(y2)

    xdiff = max(x1, x2) - min(x1, x2)
    ydiff = max(y1, y2) - min(y1, y2)
    xdir = 1 if x1 <= x2 else -1
    ydir = 1 if y1 <= y2 else -1

    r = max(xdiff, ydiff)

    for i in range(r+1):
        x = x1
        y = y1

        if ydiff:
            y += (float(i) * ydiff) / r * ydir
        if xdiff:
            x += (float(i) * xdiff) / r * xdir

        yield (x, y)


def polygon(center_x=0, center_y=0, sides=4, radius=4):
    degree = float(360) / sides

    for n in range(sides):
        a = n * degree
        b = (n + 1) * degree
        x1 = (center_x + math.cos(math.radians(a))) * (radius + 1) / 2
        y1 = (center_y + math.sin(math.radians(a))) * (radius + 1) / 2
        x2 = (center_x + math.cos(math.radians(b))) * (radius + 1) / 2
        y2 = (center_y + math.sin(math.radians(b))) * (radius + 1) / 2

        for x, y in line(x1, y1, x2, y2):
            yield x, y


class Turtle(Canvas):
    """Turtle graphics interface
    http://en.wikipedia.org/wiki/Turtle_graphics
    """

    def __init__(self, pos_x=0, pos_y=0):
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.rotation = 0
        self.brush_on = True
        super(Turtle, self).__init__()


    def up(self):
        """Pull the brush up."""
        self.brush_on = False


    def down(self):
        """Push the brush down."""
        self.brush_on = True


    def forward(self, step):
        """Move the turtle forward.

        :param step: Integer. Distance to move forward.
        """
        x = self.pos_x + math.cos(math.radians(self.rotation)) * step
        y = self.pos_y + math.sin(math.radians(self.rotation)) * step
        prev_brush_state = self.brush_on
        self.brush_on = True
        self.move(x, y)
        self.brush_on = prev_brush_state


    def move(self, x, y):
        """Move the turtle to a coordinate.

        :param x: x coordinate
        :param y: y coordinate
        """
        if self.brush_on:
            for lx, ly in line(self.pos_x, self.pos_y, x, y):
                self.set(lx, ly)

        self.pos_x = x
        self.pos_y = y


    def right(self, angle):
        """Rotate the turtle (positive direction).

        :param angle: Integer. Rotation angle in degrees.
        """
        self.rotation += angle


    def left(self, angle):
        """Rotate the turtle (negative direction).

        :param angle: Integer. Rotation angle in degrees.
        """
        self.rotation -= angle


    def back(self, step):
        """Move the turtle backwards.

        :param step: Integer. Distance to move backwards.
        """
        self.forward(-step)


    # aliases
    pu = up
    pd = down
    fd = forward
    mv = move
    rt = right
    lt = left
    bk = back

########NEW FILE########
__FILENAME__ = basic
from __future__ import print_function
from drawille import Canvas
import math


s = Canvas()

for x in range(1800):
    s.set(x/10, math.sin(math.radians(x)) * 10)

print(s.frame())

s.clear()

for x in range(0, 1800, 10):
    s.set(x/10, 10 + math.sin(math.radians(x)) * 10)
    s.set(x/10, 10 + math.cos(math.radians(x)) * 10)

print(s.frame())

s.clear()

for x in range(0, 3600, 20):
    s.set(x/20, 4 + math.sin(math.radians(x)) * 4)

print(s.frame())

s.clear()

for x in range(0, 360, 4):
    s.set(x/4, 30 + math.sin(math.radians(x)) * 30)

for x in range(30):
    for y in range(30):
        s.set(x,y)
        s.toggle(x+30, y+30)
        s.toggle(x+60, y)

print(s.frame())

########NEW FILE########
__FILENAME__ = flappy_birds
# -*- coding: utf-8 -*-
import curses
from drawille import Canvas, line
from time import sleep
from thread import start_new_thread
from Queue import Queue
import locale
from random import randint

locale.setlocale(locale.LC_ALL,"")

stdscr = curses.initscr()
stdscr.refresh()

keys = Queue()

speed = 0.0
fps = 20
frame_no = 0
score = 0
delta = frame_no / fps

height = 100
width = 100
position = height / 2

bird_map = [
#1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
[0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,0,0], #1
[0,0,0,0,0,1,1,0,0,0,0,1,0,0,0,1,0,0,0,0,0], #2
[0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0], #3
[0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,1,0,1,0,0,0], #4
[0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,1,0,0], #5
[0,1,1,1,1,1,1,1,1,0,1,0,0,0,0,1,0,0,1,0,0], #6
[1,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,1,0,0], #7
[1,0,0,0,0,0,0,1,0,0,0,0,1,1,1,1,1,1,1,1,0], #8
[1,0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0,0,1], #9
[1,0,0,0,0,0,1,0,0,0,0,0,1,1,1,1,1,1,1,1,0], #0
[0,1,1,1,1,1,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0], #1
[0,0,0,0,0,0,1,0,0,0,0,0,1,1,1,1,1,1,1,0,0], #2
[0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0], #3
]
bird = []
for y, row in enumerate(bird_map):
    for x,col in enumerate(row):
        if col:
            bird.append((x, y))

def read_keys(stdscr):
    while 1:
        c = stdscr.getch()
        keys.put(c)


class Bar():


    def __init__(self, bar_width, cap_height=4, space=3*13):
        self.height = randint(cap_height+space+1, height-1-cap_height)
        self.width = bar_width
        self.cap_height = cap_height
        self.x = width - bar_width - 1
        self.space = space


    def draw(self):
        for x,y in line(self.x,
                        self.height,
                        self.x+self.width,
                        self.height):
            yield x, y
        for x,y in line(self.x,
                        self.height,
                        self.x,
                        self.height+self.cap_height):
            yield x, y
        for x,y in line(self.x+self.width,
                        self.height,
                        x+self.width,
                        self.height+self.cap_height):
            yield x, y
        for x,y in line(self.x,
                        self.height+self.cap_height,
                        self.x+2,
                        self.height+self.cap_height):
            yield x, y
        for x,y in line(self.x+self.width-2,
                        self.height+self.cap_height,
                        self.x+self.width,
                        self.height+self.cap_height):
            yield x, y
        for x,y in line(self.x+2,
                        self.height+self.cap_height,
                        self.x+2,
                        height):
            yield x, y
        for x,y in line(self.x+self.width-2,
                        self.height+self.cap_height,
                        self.x+self.width-2,
                        height):
            yield x, y

        for x,y in line(self.x,
                        self.height-self.space,
                        self.x+self.width,
                        self.height-self.space):
            yield x, y
        for x,y in line(self.x,
                        self.height-self.space,
                        self.x,
                        self.height-self.cap_height-self.space):
            yield x, y
        for x,y in line(self.x+self.width,
                        self.height-self.space,
                        x+self.width,
                        self.height-self.cap_height-self.space):
            yield x, y
        for x,y in line(self.x,
                        self.height-self.cap_height-self.space,
                        self.x+2,
                        self.height-self.cap_height-self.space):
            yield x, y
        for x,y in line(self.x+self.width-2,
                        self.height-self.cap_height-self.space,
                        self.x+self.width,
                        self.height-self.cap_height-self.space):
            yield x, y
        for x,y in line(self.x+2,
                        self.height-self.cap_height-self.space,
                        self.x+2,
                        0):
            yield x, y
        for x,y in line(self.x+self.width-2,
                        self.height-self.cap_height-self.space,
                        self.x+self.width-2,
                        0):
            yield x, y

def check_collision(bird_pos, bar):
    # TODO more efficient collision detection
    if bar.x > 21:
        return False
    if bar.height <= bird_pos-13 and bar.height+bar.space > bird_pos:
        return False
    for bar_x, bar_y in bar.draw():
        for bird_x, bird_y in bird:
            if int(bird_x) == int(bar_x) and int(bird_y+bird_pos) == int(bar_y):
                return True
    return False

def main(stdscr):
    global frame_no, speed, fps, position, delta, score
    c = Canvas()
    bar_width = 16
    bars = [Bar(bar_width)]
    stdscr.refresh()

    while True:
        frame_no += 1
        for bar in bars:
            if check_collision(position, bar):
                return
        while not keys.empty():
            if keys.get() == 113:
                return
            speed = 32.0

        c.set(0,0)
        c.set(width, height)
        if frame_no % 50 == 0:
            bars.append(Bar(bar_width))
        for x,y in bird:
            c.set(x,y+position)
        for bar_index, bar in enumerate(bars):
            if bar.x < 1:
                bars.pop(bar_index)
                score += 1
            else:
                bars[bar_index].x -= 1
                for x,y in bar.draw():
                    c.set(x,y)
        f = c.frame()+'\n'
        stdscr.addstr(0, 0, f)
        stdscr.addstr(height/4+1, 0, 'score: {0}'.format(score))
        stdscr.refresh()
        c.clear()

        speed -= 2

        position -= speed/10

        if position < 0:
            position = 0
            speed = 0.0
        elif position > height-13:
            position = height-13
            speed = 0.0


        sleep(1.0/fps)


if __name__ == '__main__':
    start_new_thread(read_keys, (stdscr,))
    curses.wrapper(main)
    print('Final score: {0}'.format(score))


########NEW FILE########
__FILENAME__ = image2term
# example:
# $  PYTHONPATH=`pwd` python examples/image2term.py http://fc00.deviantart.net/fs71/f/2011/310/5/a/giant_nyan_cat_by_daieny-d4fc8u1.png -t 100 -r 0.01

try:
    from PIL import Image
except:
    from sys import stderr, exit
    stderr.write('[E] PIL not installed')
    exit(1)
from drawille import Canvas
from StringIO import StringIO
import urllib2


def getTerminalSize():
    import os
    env = os.environ

    def ioctl_GWINSZ(fd):
        import fcntl
        import termios
        import struct
        cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))
    return int(cr[1]), int(cr[0])


def image2term(image, threshold=128, ratio=None, invert=False):
    if image.startswith('http://') or image.startswith('https://'):
        i = Image.open(StringIO(urllib2.urlopen(image).read())).convert('L')
    else:
        i = Image.open(open(image)).convert('L')
    w, h = i.size
    if ratio:
        w = int(w * ratio)
        h = int(h * ratio)
        i = i.resize((w, h), Image.ANTIALIAS)
    else:
        tw, th = getTerminalSize()
        tw *= 2
        th *= 2
        if tw < w:
            ratio = tw / float(w)
            w = tw
            h = int(h * ratio)
            i = i.resize((w, h), Image.ANTIALIAS)
    can = Canvas()
    x = y = 0

    try:
         i_converted = i.tobytes()
    except AttributeError:
         i_converted = i.tostring()

    for pix in i_converted:
        if invert:
            if ord(pix) > threshold:
                can.set(x, y)
        else:
            if ord(pix) < threshold:
                can.set(x, y)
        x += 1
        if x >= w:
            y += 1
            x = 0
    return can.frame(0, 0)


def argparser():
    import argparse
    from sys import stdout
    argp = argparse.ArgumentParser(description='drawille - image to terminal example script')
    argp.add_argument('-o', '--output'
                     ,help      = 'Output file - default is STDOUT'
                     ,metavar   = 'FILE'
                     ,default   = stdout
                     ,type      = argparse.FileType('w')
                     )
    argp.add_argument('-r', '--ratio'
                     ,help      = 'Image resize ratio'
                     ,default   = None
                     ,action    = 'store'
                     ,type      = float
                     ,metavar   = 'N'
                     )
    argp.add_argument('-t', '--threshold'
                     ,help      = 'Color threshold'
                     ,default   = 128
                     ,action    = 'store'
                     ,type      = int
                     ,metavar   = 'N'
                     )
    argp.add_argument('-i', '--invert'
                     ,help      = 'Invert colors'
                     ,default   = False
                     ,action    = 'store_true'
                     )
    argp.add_argument('image'
                     ,metavar   = 'FILE'
                     ,help      = 'Image file path/url'
                     )
    return vars(argp.parse_args())


def __main__():
    args = argparser()
    args['output'].write(image2term(args['image'], args['threshold'], args['ratio'], args['invert']))
    args['output'].write('\n')


if __name__ == '__main__':
    __main__()

########NEW FILE########
__FILENAME__ = rotating_cube
from drawille import Canvas, line
import curses
import math
from time import sleep
import locale

locale.setlocale(locale.LC_ALL,"")

stdscr = curses.initscr()
stdscr.refresh()

class Point3D:
    def __init__(self, x = 0, y = 0, z = 0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def rotateX(self, angle):
        """ Rotates the point around the X axis by the given angle in degrees. """
        rad = angle * math.pi / 180
        cosa = math.cos(rad)
        sina = math.sin(rad)
        y = self.y * cosa - self.z * sina
        z = self.y * sina + self.z * cosa
        return Point3D(self.x, y, z)

    def rotateY(self, angle):
        """ Rotates the point around the Y axis by the given angle in degrees. """
        rad = angle * math.pi / 180
        cosa = math.cos(rad)
        sina = math.sin(rad)
        z = self.z * cosa - self.x * sina
        x = self.z * sina + self.x * cosa
        return Point3D(x, self.y, z)

    def rotateZ(self, angle):
        """ Rotates the point around the Z axis by the given angle in degrees. """
        rad = angle * math.pi / 180
        cosa = math.cos(rad)
        sina = math.sin(rad)
        x = self.x * cosa - self.y * sina
        y = self.x * sina + self.y * cosa
        return Point3D(x, y, self.z)

    def project(self, win_width, win_height, fov, viewer_distance):
        """ Transforms this 3D point to 2D using a perspective projection. """
        factor = fov / (viewer_distance + self.z)
        x = self.x * factor + win_width / 2
        y = -self.y * factor + win_height / 2
        return Point3D(x, y, 1)


vertices = [
    Point3D(-20,20,-20),
    Point3D(20,20,-20),
    Point3D(20,-20,-20),
    Point3D(-20,-20,-20),
    Point3D(-20,20,20),
    Point3D(20,20,20),
    Point3D(20,-20,20),
    Point3D(-20,-20,20)
]

# Define the vertices that compose each of the 6 faces. These numbers are
# indices to the vertices list defined above.
faces = [(0,1,2,3),(1,5,6,2),(5,4,7,6),(4,0,3,7),(0,4,5,1),(3,2,6,7)]


def __main__(stdscr, projection=False):
    angleX, angleY, angleZ = 0, 0, 0
    c = Canvas()
    while 1:
        # Will hold transformed vertices.
        t = []

        for v in vertices:
            # Rotate the point around X axis, then around Y axis, and finally around Z axis.
            p = v.rotateX(angleX).rotateY(angleY).rotateZ(angleZ)
            if projection:
                # Transform the point from 3D to 2D
                p = p.project(50, 50, 50, 50)
             #Put the point in the list of transformed vertices
            t.append(p)

        for f in faces:
            for x,y in line(t[f[0]].x, t[f[0]].y, t[f[1]].x, t[f[1]].y):
                c.set(x,y)
            for x,y in line(t[f[1]].x, t[f[1]].y, t[f[2]].x, t[f[2]].y):
                c.set(x,y)
            for x,y in line(t[f[2]].x, t[f[2]].y, t[f[3]].x, t[f[3]].y):
                c.set(x,y)
            for x,y in line(t[f[3]].x, t[f[3]].y, t[f[0]].x, t[f[0]].y):
                c.set(x,y)

        f = c.frame(-40, -40, 80, 80)
        stdscr.addstr(0, 0, '{0}\n'.format(f))
        stdscr.refresh()

        angleX += 2
        angleY += 3
        angleZ += 5
        sleep(1.0/20)
        c.clear()

if __name__ == '__main__':
    from sys import argv
    projection = False
    if '-p' in argv:
        projection = True
    curses.wrapper(__main__, projection)

########NEW FILE########
__FILENAME__ = sine_tracking
from __future__ import print_function
from drawille import Canvas, line
import math
from time import sleep
import curses
import locale

locale.setlocale(locale.LC_ALL,"")

stdscr = curses.initscr()
stdscr.refresh()


def __main__(stdscr):
    i = 0
    c = Canvas()
    height = 40
    while True:

        for x,y in line(0, height, 180, int(math.sin(math.radians(i)) * height + height)):
            c.set(x,y)

        for x in range(0, 360, 2):
            coords = (x/2, height + int(round(math.sin(math.radians(x+i)) * height)))
            c.set(*coords)

        f = c.frame()
        stdscr.addstr(0, 0, '{0}\n'.format(f))
        stdscr.refresh()

        i += 2
        sleep(1.0/24)
        c.clear()


if __name__ == '__main__':
    curses.wrapper(__main__)

########NEW FILE########
__FILENAME__ = speed_test
from drawille import Canvas
from timeit import timeit

c = Canvas()

frames = 1000 * 10

sizes = ((0, 0),
         (10, 10),
         (20, 20),
         (20, 40),
         (40, 20),
         (40, 40),
         (100, 100))

for x, y in sizes:
    c.set(0, 0)

    for i in range(y):
        c.set(x, i)

    r = timeit(c.frame, number=frames)
    print('{0}x{1}\t{2}'.format(x, y, r))
    c.clear()

########NEW FILE########
__FILENAME__ = xkcd
# -*- coding: utf-8 -*-

from sys import argv, exit
try:
    from PIL import Image
except:
    from sys import stderr
    stderr.write('[E] PIL not installed')
    exit(1)
from StringIO import StringIO
import urllib2
import re
from drawille import Canvas


def getTerminalSize():
    import os
    env = os.environ

    def ioctl_GWINSZ(fd):
        import fcntl
        import termios
        import struct
        cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))
    return int(cr[1]), int(cr[0])


def usage():
    print('Usage: %s <url/id>')
    exit()

if __name__ == '__main__':
    if len(argv) < 2:
        url = 'http://xkcd.com/'
    elif argv[1] in ['-h', '--help']:
        usage()
    elif argv[1].startswith('http'):
        url = argv[1]
    else:
        url = 'http://xkcd.com/%s/' % argv[1]
    c = urllib2.urlopen(url).read()
    img_url = re.findall('http:\/\/imgs.xkcd.com\/comics\/[^"\']+', c)[0]
    i = Image.open(StringIO(urllib2.urlopen(img_url).read())).convert('L')
    w, h = i.size
    tw, th = getTerminalSize()
    tw *= 2
    th *= 2
    if tw < w:
        ratio = tw / float(w)
        w = tw
        h = int(h * ratio)
        i = i.resize((w, h), Image.ANTIALIAS)
    can = Canvas()
    x = y = 0

    try:
         i_converted = i.tobytes()
    except AttributeError:
         i_converted = i.tostring()

    for pix in i_converted:
        if ord(pix) < 128:
            can.set(x, y)
        x += 1
        if x >= w:
            y += 1
            x = 0
    print(can.frame())

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from drawille import Canvas, line, Turtle
from unittest import TestCase, main


class CanvasTestCase(TestCase):


    def test_set(self):
        c = Canvas()
        c.set(0, 0)
        self.assertTrue(0 in c.chars and 0 in c.chars[0])


    def test_unset_empty(self):
        c = Canvas()
        c.set(1, 1)
        c.unset(1, 1)
        self.assertEqual(len(c.chars), 0)


    def test_unset_nonempty(self):
        c = Canvas()
        c.set(0, 0)
        c.set(0, 1)
        c.unset(0, 1)
        self.assertEqual(c.chars[0][0], 1)


    def test_clear(self):
        c = Canvas()
        c.set(1, 1)
        c.clear()
        self.assertEqual(c.chars, dict())


    def test_toggle(self):
        c = Canvas()
        c.toggle(0, 0)
        self.assertEqual(c.chars, {0: {0: 1}})
        c.toggle(0, 0)
        self.assertEqual(c.chars, dict())


    def test_set_text(self):
        c = Canvas()
        c.set_text(0, 0, "asdf")
        self.assertEqual(c.frame(), "asdf")


    def test_frame(self):
        c = Canvas()
        self.assertEqual(c.frame(), '')
        c.set(0, 0)
        self.assertEqual(c.frame(), '⠁')


    def test_max_min_limits(self):
        c = Canvas()
        c.set(0, 0)
        self.assertEqual(c.frame(min_x=2), '')
        self.assertEqual(c.frame(max_x=0), '')


    def test_get(self):
        c = Canvas()
        self.assertEqual(c.get(0, 0), False)
        c.set(0, 0)
        self.assertEqual(c.get(0, 0), True)
        self.assertEqual(c.get(0, 1), False)
        self.assertEqual(c.get(1, 0), False)
        self.assertEqual(c.get(1, 1), False)


class LineTestCase(TestCase):


    def test_single_pixel(self):
        self.assertEqual(list(line(0, 0, 0, 0)), [(0, 0)])


    def test_row(self):
        self.assertEqual(list(line(0, 0, 1, 0)), [(0, 0), (1, 0)])


    def test_column(self):
        self.assertEqual(list(line(0, 0, 0, 1)), [(0, 0), (0, 1)])


    def test_diagonal(self):
        self.assertEqual(list(line(0, 0, 1, 1)), [(0, 0), (1, 1)])


class TurtleTestCase(TestCase):


    def test_position(self):
        t = Turtle()
        self.assertEqual(t.pos_x, 0)
        self.assertEqual(t.pos_y, 0)
        t.move(1, 1)
        self.assertEqual(t.pos_x, 1)
        self.assertEqual(t.pos_y, 1)


    def test_rotation(self):
        t = Turtle()
        self.assertEqual(t.rotation, 0)
        t.right(30)
        self.assertEqual(t.rotation, 30)
        t.left(30)
        self.assertEqual(t.rotation, 0)


    def test_brush(self):
        t = Turtle()
        self.assertFalse(t.get(t.pos_x, t.pos_y))
        t.forward(1)
        self.assertTrue(t.get(0, 0))
        self.assertTrue(t.get(t.pos_x, t.pos_y))
        t.up()
        t.move(2, 0)
        self.assertFalse(t.get(t.pos_x, t.pos_y))
        t.down()
        t.move(3, 0)
        self.assertTrue(t.get(t.pos_x, t.pos_y))


if __name__ == '__main__':
    main()

########NEW FILE########
