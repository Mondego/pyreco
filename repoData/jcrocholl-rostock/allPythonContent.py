__FILENAME__ = deltacode
#!/usr/bin/python
#
# Convert G-code from slic3r to deltacode for Rostock 3D printer.
#
# Deltacode is similar to G-code but with delta geometry for X Y Z.
# Straight lines in G-code are translated to parabolic curves in
# deltacode.  These curves are made from many small linear G1
# moves. This may double the size of the G-code file. In the future
# this translation will be implemented in firmware so we can send
# normal G-code to the delta bot.

__author__ = 'johann@rocholl.net'

CENTER = {'X': 100, 'Y': 100}

import math
import sys


class Vector(object):

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __abs__(self):
        return math.sqrt(self.x * self.x +
                         self.y * self.y +
                         self.z * self.z)

    def __add__(self, other):
        return Vector(self.x + other.x,
                      self.y + other.y,
                      self.z + other.z)

    def __sub__(self, other):
        return Vector(self.x - other.x,
                      self.y - other.y,
                      self.z - other.z)

    def __mul__(self, factor):
        return Vector(self.x * factor,
                      self.y * factor,
                      self.z * factor)

    def gcode(self):
        return 'X%.8g Y%.8g Z%.8g' % (self.x, self.y, self.z)


SIN_60 = math.sin(math.pi / 3)
COS_60 = 0.5

RADIUS = 175 - 33 - 18  # Horizontal distance of diagonal rods when centered.
ZERO_OFFSET = -9  # Print surface is lower than bottom endstops.

TOWER_1 = Vector(-SIN_60 * RADIUS, -COS_60*RADIUS, 0)
TOWER_2 = Vector(SIN_60 * RADIUS, -COS_60*RADIUS, 0)
TOWER_3 = Vector(0, RADIUS, 0)


def delta(v):
    t1 = TOWER_1 - v
    t2 = TOWER_2 - v
    t3 = TOWER_3 - v
    return Vector(
        v.z + math.sqrt(250*250 - t1.x*t1.x - t1.y*t1.y) + ZERO_OFFSET,
        v.z + math.sqrt(250*250 - t2.x*t2.x - t2.y*t2.y) + ZERO_OFFSET,
        v.z + math.sqrt(250*250 - t3.x*t3.x - t3.y*t3.y) + ZERO_OFFSET)


def G1(pos, dest):
    """Convert a long linear cartesian move into many small moves."""
    global num_lines

    for char in 'XYZEF':
        if char not in dest:
            dest[char] = pos[char]

    start = Vector(pos['X'], pos['Y'], pos['Z'])
    finish = Vector(dest['X'], dest['Y'], dest['Z'])

    cartesian_mm = abs(finish - start)
    steps = max(1, int(5 * cartesian_mm))
    cartesian_mm /= steps

    previous = delta(start)
    previous_e = 'E%.8g' % pos['E']
    previous_f = 'F%.5g' % pos['F']
    for step in range(steps):
        fraction = float(step + 1) / steps
        d = delta(start + (finish - start) * fraction)
        print 'G1', d.gcode(),
        # Extruder steps.
        e = pos['E'] + (dest['E'] - pos['E']) * fraction
        e = 'E%.8g' % e
        if e != previous_e:
            previous_e = e
            print e,
        # Feedrate needs to be adjusted for delta geometry.
        f = pos['F'] + (dest['F'] - pos['F']) * fraction
        if abs(cartesian_mm) > 0.1:
            delta_mm = abs(d - previous)
            f *= delta_mm / cartesian_mm
        f = 'F%.5g' % f
        if f != previous_f:
            previous_f = f
            print f,
        print
        previous = d
        num_lines += 1

    for char in 'XYZEF':
        pos[char] = dest[char]



def G28(pos, dest):
    """Home all axes."""
    if 'X' in dest:
        pos['X'] = -100 * SIN_60
        pos['Y'] = 100 * COS_60
        pos['Z'] = 0
    if 'Y' in dest:
        pos['X'] = 100 * SIN_60
        pos['Y'] = 100 * COS_60
        pos['Z'] = 0
    if 'Z' in dest or not dest:
        pos['X'] = 0
        pos['Y'] = 100
        pos['Z'] = 0


pos = {}
for char in 'XYZEF':
    pos[char] = 0.0

num_lines = 0
for line in sys.stdin:
    words = line.split()
    if not words:
        print
        continue
    dest = {}
    for word in words[1:]:
        if word.startswith(';'):
            break
        for char in 'XYZF':
            if word.startswith(char):
                dest[char] = float(word[1:]) - CENTER.get(char, 0)
    if words[0] == 'G1':
        print ';', line.strip()
        G1(pos, dest)
        if num_lines > 10000:
            sys.exit(0)
    elif words[0] == 'G28':
        G28(pos, dest)
        print line.strip()
    else:
        print line.rstrip()

########NEW FILE########
__FILENAME__ = demo
#!/usr/bin/python

import math


class Vector(object):

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __abs__(self):
        return math.sqrt(self.x * self.x +
                         self.y * self.y +
                         self.z * self.z)

    def __add__(self, other):
        return Vector(self.x + other.x,
                      self.y + other.y,
                      self.z + other.z)

    def __sub__(self, other):
        return Vector(self.x - other.x,
                      self.y - other.y,
                      self.z - other.z)

    def __mul__(self, factor):
        return Vector(self.x * factor,
                      self.y * factor,
                      self.z * factor)

    def gcode(self):
        return 'X%.3f Y%.3f Z%.3f' % (self.x, self.y, self.z)


SIN_60 = math.sin(math.pi / 3)
COS_60 = 0.5

RADIUS = 175 - 33 - 18
ZERO_OFFSET = -7
TOWER_1 = Vector(-SIN_60 * RADIUS, -COS_60*RADIUS, 0)
TOWER_2 = Vector(SIN_60 * RADIUS, -COS_60*RADIUS, 0)
TOWER_3 = Vector(0, RADIUS, 0)


def delta(v):
    t1 = TOWER_1 - v
    t2 = TOWER_2 - v
    t3 = TOWER_3 - v
    return Vector(
        v.z + math.sqrt(250*250 - t1.x*t1.x - t1.y*t1.y) + ZERO_OFFSET,
        v.z + math.sqrt(250*250 - t2.x*t2.x - t2.y*t2.y) + ZERO_OFFSET,
        v.z + math.sqrt(250*250 - t3.x*t3.x - t3.y*t3.y) + ZERO_OFFSET)


def linear(start, stop, speed):
    cartesian_mm = abs(stop - start)
    steps = max(1, int(cartesian_mm * 50 / min(speed, 200)))
    cartesian_mm /= steps
    previous = delta(start)
    for step in range(steps):
        d = delta(start + (stop - start) * (float(step + 1) / steps))
        print 'G1', d.gcode(),
        delta_mm = abs(d - previous)
        factor = delta_mm / cartesian_mm
        print 'F%.3f' % (60 * speed * factor)
        previous = d


print 'G21 ; set units to millimeters'
print 'G90 ; use absolute positioning'
print 'G28 ; home all axes'

SIZE = 60
SIZE2 = SIZE * math.sqrt(2)  # diagonal

previous = Vector(0, 0, 0)
print 'G1 F3000'

speeds = [100, 200, 300, 400]
for speed in speeds:
    print 'G1 F%d' % (speed * 60)
    z = 0  # (speed - 100) / 5
    for a in xrange(0, 1441, min(speed/100, 3)):
        v = Vector(math.sin(a * math.pi / 180) * SIZE,
                   math.cos(a * math.pi / 180) * SIZE,
                   z)
        d = delta(v)
        print 'G1', d.gcode()
        previous = v
    for y in xrange(-int(SIZE2), int(SIZE2), 10):
        x = SIZE2 - abs(y)
        vector = Vector(-x, y, z)
        linear(previous, vector, speed)
        previous = vector
        vector = Vector(x, y, z)
        linear(previous, vector, speed)
        previous = vector

# linear(previous, Vector(0, 0, 0), 300)
print 'G1 X400 Y400 Z400'
print 'M84 ; all motors off'

########NEW FILE########
