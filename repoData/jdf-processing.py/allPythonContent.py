__FILENAME__ = pde2py
#!/usr/bin/python
"""
    Utility to do whatever mechanical work can be done in converting
    PDE examples to Python ones.
"""
from __future__ import with_statement

from optparse import OptionParser
import os
import re
import shutil
import sys


def usage():
    print >> sys.stderr, 'Usage: pde2py [-f|--force] srcdir destdir'
    sys.exit(1)

parser = OptionParser()
parser.add_option("-f", "--force",
                  action="store_true", dest="force", default=False,
                  help="overwrite existing files")

(opts, args) = parser.parse_args()

if len(args) < 2:
    usage()

src, dest = args
if not (os.path.exists(src) and os.path.isdir(src)):
    usage()
if not os.path.exists(dest):
    os.makedirs(dest)


def copy_dir(s, d):
    if not os.path.exists(d):
        os.mkdir(d)
    for f in os.listdir(s):
        if f[0] == '.':
            continue
        copy(os.path.join(s, f), os.path.join(d, f))


def copy_file(s, d, xform=None):
    with open(s, 'rb') as f:
        text = f.read()
    if xform:
        (d, text) = xform(d, text)
    if os.path.exists(d):
        if opts.force:
            print >> sys.stderr, 'Overwriting %s.' % d
        else:
            print >> sys.stderr, 'Not overwriting %s.' % d
            return
    else:
        print >> sys.stderr, 'Writing %s.' % d

    with open(d, 'wb') as f:
        f.write(text)


def to_python_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def xform_py(d, text):
    text = re.sub('(?<!:)//', '#', text)
    text = text.replace('  ', '    ')
    text = re.sub(r'for *\((?: *int *)?(\w+) *= *0 *; * \1 *< *([^;]+); *\1\+\+ *\)', r'for \1 in range(\2):', text)
    text = re.sub(r'for *\((?: *int *)?(\w+) *= *(\d+) *; * \1 *< *([^;]+); *\1\+\+ *\)', r'for \1 in range(\2, \3):', text)
    text = re.sub(r'for *\((?: *int *)?(\w+) *= *(\d+) *; * \1 *< *([^;]+); *\1 *\+= *([^\)]+)\)', r'for \1 in range(\2, \3, \4):', text)
    text = re.sub(r'(?m)^(\s*)(?:public *)?(?:void|int|float|String)\s+([a-zA-Z0-9]+)\s*\(([^\)]*)\)',
                  r'\1def \2(\3):',
                  text)
    text = re.sub(r'(?:int|float|String|double|Object)\s+([a-zA-Z0-9]+)\s*([,\)])',
                  r'\1\2',
                  text)
    text = re.sub(r'(?:int|float|String|double|Object)\s+([a-zA-Z0-9]+)\s*=',
                  r'\1 =',
                  text)
    text = re.sub(
        r'(?:abstract +)?class +(\w+)', r'class \1(object):', text)
    text = re.sub(
        r'(?m)^\s*(?:abstract\s+)?class\s+(\S+)\s*extends\s*(\S+)\s*$', r'class \1(\2):', text)
    text = re.sub(r'(?m)^(\s*)(?:void|int|float|String)\s+', r'\1', text)
    text = re.sub(r'[{};] *', '', text)
    text = re.sub(r'\n\n+', '\n', text)
    text = re.sub(r'(?m)^(\s*)if\s*\((.+?)\)\s*$', r'\1if \2:', text)
    text = re.sub(r'(?m)^(\s*)else\s+if\s*\((.+?)\)\s*$', r'\1elif \2:', text)
    text = re.sub(r'(?m)^(\s*)else\s*$', r'\1else:', text)
    text = re.sub(r'/\*+| *\*+/', '"""', text)
    text = re.sub(r'(?m)^ *\* *', '', text)
    text = text.replace('new ', '')
    text = text.replace('true', 'True')
    text = text.replace('false', 'False')
    text = text.replace('this.', 'self.')
    text = text.replace('||', 'or')
    text = text.replace('&&', 'and')
    text = re.sub(r'(\w+)\+\+', r'\1 += 1', text)
    text = re.sub(r'(\w+)--', r'\1 -= 1', text)
    text = re.sub(r'(\w+)\.length\b', r'len(\1)', text)

    parent = os.path.dirname(d)
    parent_name = os.path.basename(parent)
    name, ext = os.path.splitext(os.path.basename(d))
    if name == parent_name:
        newext = '.pyde'
    else:
        newext = '.py'
        name = to_python_case(name)

    d = parent + '/' + name + newext
    return (d, text)


def copy(s, d):
    if os.path.isdir(s):
        copy_dir(s, d)
    elif s.endswith(".pde"):
        copy_file(s, d, xform_py)
    else:
        copy_file(s, d)

copy(src, dest)

########NEW FILE########
__FILENAME__ = MoveEye
"""
 * Move Eye. 
 * by Simon Greenwold.
 * 
 * The camera lifts up (controlled by mouseY) while looking at the same point.
 """
def setup(): 
    size(640, 360, P3D)
    fill(204)
    
def draw(): 
    lights()
    background(0)
    
    # Change height of the camera with mouseY
    camera(30.0, mouseY, 220.0, # eyeX, eyeY, eyeZ
           0.0, 0.0, 0.0,       # centerX, centerY, centerZ
           0.0, 1.0, 0.0)       # upX, upY, upZ
    
    noStroke()
    box(90)
    stroke(255)
    line(-100, 0, 0, 100, 0, 0)
    line(0, -100, 0, 0, 100, 0)
    line(0, 0, -100, 0, 0, 100)

########NEW FILE########
__FILENAME__ = OrthoVSPerspective
"""
 * Ortho vs Perspective.
 *
 * Click to see the difference between orthographic projection
 * and perspective projection as applied to a simple box.
 * The ortho() function sets an orthographic projection and
 * defines a parallel clipping volume. All objects with the
 * same dimension appear the same size, regardless of whether
 * they are near or far from the camera. The parameters to this
 * function specify the clipping volume where left and right
 * are the minimum and maximum x values, top and bottom are the
 * minimum and maximum y values, and near and far are the minimum
 * and maximum z values.
 """
def setup():
    size(640, 360, P3D)
    noStroke()
    fill(204)

def draw():
    background(0)
    lights()

    if mousePressed:
        fov = PI / 3.0
        cameraZ = (height / 2.0) / tan(PI * fov / 360.0)
        perspective(fov, float(width) / float(height),
                                cameraZ / 2.0, cameraZ * 2.0)
    else:
        ortho(-width / 2, width / 2, -height / 2, height / 2, -10, 10)


    translate(width / 2, height / 2, 0)
    rotateX(-PI / 6)
    rotateY(PI / 3)
    box(160)

########NEW FILE########
__FILENAME__ = Perspective
"""
 * Perspective.
 *
 * Move the mouse left and right to change the field of view (fov).
 * Click to modify the aspect ratio. The perspective() function
 * sets a perspective projection applying foreshortening, making
 * distant objects appear smaller than closer ones. The parameters
 * define a viewing volume with the shape of truncated pyramid.
 * Objects near to the front of the volume appear their actual size,
 * while farther objects appear smaller. This projection simulates
 * the perspective of the world more accurately than orthographic projection.
 * The version of perspective without parameters sets the default
 * perspective and the version with four parameters allows the programmer
 * to set the area precisely.
 """
def setup():
    size(640, 360, P3D)
    noStroke()

def draw():
    lights()
    background(204)
    cameraY = height / 2.0
    fov = mouseX / float(width) * PI / 2
    cameraZ = cameraY / max(1, tan(fov / 2.0))
    aspect = float(width) / float(height)
    if mousePressed:
        aspect = aspect / 2.0

    perspective(fov, aspect, cameraZ / 10.0, cameraZ * 10.0)

    translate(width / 2 + 30, height / 2, 0)
    rotateX(-PI / 6)
    rotateY(PI / 3 + mouseY / float(height) * PI)
    box(45)
    translate(0, 0, -50)
    box(30)

########NEW FILE########
__FILENAME__ = bricktower
"""
 * Brick Tower
 * by Ira Greenberg. 
 * 
 * 3D castle tower constructed out of individual bricks.
"""

bricksPerLayer = 16.0
brickLayers = 18.0
brickWidth = 60
brickHeight = 25
brickDepth = 25
radius = 175.0

def setup():
    size(640, 360, OPENGL)

def draw():
  background(0)
  (tempX, tempY, tempZ) = (0, 0, 0)
  fill(182, 62, 29)
  noStroke()
  # Add basic light setup
  lights()
  translate(width / 2, height * 1.2, -380)
  # Tip tower to see inside
  rotateX(radians(-45))
  # Slowly rotate tower
  rotateY(frameCount * PI / 600)
  for i in range(brickLayers):
    # Increment rows
    tempY -= brickHeight
    # Alternate brick seams
    angle = 360.0 / bricksPerLayer * i / 2
    for j in range(bricksPerLayer):
      tempZ = cos(radians(angle)) * radius
      tempX = sin(radians(angle)) * radius
      pushMatrix()
      translate(tempX, tempY, tempZ)
      rotateY(radians(angle))
      # Add crenelation
      if (i == brickLayers - 1):
        if (j % 2 == 0):
          box(brickWidth, brickHeight, brickDepth)
      else:
        # Create main tower
        box(brickWidth, brickHeight, brickDepth)
      popMatrix()
      angle += 360.0 / bricksPerLayer

########NEW FILE########
__FILENAME__ = CubicGrid
"""
    Cubic Grid 
    by Ira Greenberg. 

    3D translucent colored grid uses nested pushMatrix()
    and popMatrix() functions. 
"""
boxSize = 40
margin = boxSize*2
depth = 400

def setup():
    size(640, 360, P3D)
    noStroke()

def draw():
    background(255)
  
    # Center and spin grid
    translate(width/2, height/2, -depth)
    rotateY(frameCount * 0.01)
    rotateX(frameCount * 0.01)
    
    # Build grid using multiple translations
    i = -depth/2+margin
    while i <= depth/2-margin:
        pushMatrix()
        j = -height+margin
        while j <= height-margin:
            pushMatrix()
            k = -width + margin
            while k <= width-margin:
                # Base fill color on counter values, abs function 
                # ensures values stay within legal range
                boxFill = color(abs(i), abs(j), abs(k), 50)
                pushMatrix()
                translate(k, j, i)
                fill(boxFill)
                box(boxSize, boxSize, boxSize)
                popMatrix()
                k += boxSize
            popMatrix()
            j += boxSize
        popMatrix()
        i += boxSize    

########NEW FILE########
__FILENAME__ = Primitives3D
"""
 * Primitives 3D. 
 * 
 * Placing mathematically 3D objects in synthetic space.
 * The lights() method reveals their imagined dimension.
 * The box() and sphere() functions each have one parameter
 * which is used to specify their size. These shapes are
 * positioned using the translate() function.
 """
 
size(640, 360, P3D) 
background(0)
lights()
noStroke()
pushMatrix()
translate(130, height/2, 0)
rotateY(1.25)
rotateX(-0.4)
box(100)
popMatrix()
noFill()
stroke(255)
pushMatrix()
translate(500, height*0.35, -200)
sphere(280)
popMatrix()

########NEW FILE########
__FILENAME__ = RGBCube
"""
 * RGB Cube.
 * 
 * The three primary colors of the additive color model are red, green, and blue.
 * This RGB color cube displays smooth transitions between these colors. 
 """
 
xmag, ymag = (0, 0)
newXmag, newYmag = (0, 0) 
 
def setup(): 
    size(640, 360, P3D) 
    noStroke() 
    colorMode(RGB, 1) 
 
def draw():
    global xmag, ymag, newXmag, newYmag
     
    background(0.5)

    pushMatrix() 
    translate(width / 2, height / 2, -30) 
    
    newXmag = mouseX / float(width) * TWO_PI
    newYmag = mouseY / float(height) * TWO_PI
    
    diff = xmag - newXmag
    if abs(diff) > 0.01:
        xmag -= diff / 4.0 
    
    diff = ymag - newYmag
    if abs(diff) > 0.01:
        ymag -= diff / 4.0 
    
    rotateX(-ymag) 
    rotateY(-xmag) 
    
    scale(90)
    beginShape(QUADS)
    fill(0, 1, 1)
    vertex(-1, 1, 1)
    fill(1, 1, 1)
    vertex(1, 1, 1)
    fill(1, 0, 1)
    vertex(1, -1, 1)
    fill(0, 0, 1)
    vertex(-1, -1, 1)
    fill(1, 1, 1)
    vertex(1, 1, 1)
    fill(1, 1, 0)
    vertex(1, 1, -1)
    fill(1, 0, 0)
    vertex(1, -1, -1)
    fill(1, 0, 1)
    vertex(1, -1, 1)
    fill(1, 1, 0)
    vertex(1, 1, -1)
    fill(0, 1, 0)
    vertex(-1, 1, -1)
    fill(0, 0, 0)
    vertex(-1, -1, -1)
    fill(1, 0, 0)
    vertex(1, -1, -1)
    fill(0, 1, 0)
    vertex(-1, 1, -1)
    fill(0, 1, 1)
    vertex(-1, 1, 1)
    fill(0, 0, 1)
    vertex(-1, -1, 1)
    fill(0, 0, 0)
    vertex(-1, -1, -1)
    fill(0, 1, 0)
    vertex(-1, 1, -1)
    fill(1, 1, 0)
    vertex(1, 1, -1)
    fill(1, 1, 1)
    vertex(1, 1, 1)
    fill(0, 1, 1)
    vertex(-1, 1, 1)
    fill(0, 0, 0)
    vertex(-1, -1, -1)
    fill(1, 0, 0)
    vertex(1, -1, -1)
    fill(1, 0, 1)
    vertex(1, -1, 1)
    fill(0, 0, 1)
    vertex(-1, -1, 1)

    endShape()
    
    popMatrix() 
 

########NEW FILE########
__FILENAME__ = ShapeTransform
"""
  Shape Transform
  by Ira Greenberg.
  (Rewritten in Python by Jonathan Feinberg.)

  Illustrates the geometric relationship
  between Cube, Pyramid, Cone and
  Cylinder 3D primitives.

  Instructions:
  Up Arrow - increases points
  Down Arrow - decreases points
  'p' key toggles between cube/pyramid
 """

# constants
radius = 99
cylinderLength = 95
angleInc = PI / 300.0

# globals that can be chaned by the user
pts = 12
isPyramid = False

def setup():
    size(640, 360, OPENGL)
    noStroke()

def draw():
    background(170, 95, 95)
    lights()
    fill(255, 200, 200)
    translate(width / 2, height / 2)
    rotateX(frameCount * angleInc)
    rotateY(frameCount * angleInc)
    rotateZ(frameCount * angleInc)

    dTheta = TWO_PI / pts
    x = lambda(j): cos(dTheta * j) * radius
    y = lambda(j): sin(dTheta * j) * radius

    # draw cylinder tube
    beginShape(QUAD_STRIP)
    for j in range(pts + 1):
        vertex(x(j), y(j), cylinderLength)
        if isPyramid:
            vertex(0, 0, -cylinderLength)
        else:
            vertex(x(j), y(j), -cylinderLength)
    endShape()
    #draw cylinder ends
    beginShape()
    for j in range(pts + 1):
        vertex(x(j), y(j), cylinderLength)
    endShape(CLOSE)
    if not isPyramid:
        beginShape()
        for j in range(pts + 1):
            vertex(x(j), y(j), -cylinderLength)
        endShape(CLOSE)

"""
 up/down arrow keys control
 polygon detail.
 """
def keyPressed():
    global pts, isPyramid
    if key == CODED:
        if keyCode == UP and pts < 90:
            pts += 1
        elif keyCode == DOWN and pts > 4:
            pts -= 1
    elif key == 'p':
        isPyramid = not isPyramid

########NEW FILE########
__FILENAME__ = Toroid
"""
 * Interactive Toroid
 * PDE by Ira Greenberg, rewritten in Python by Jonathan Feinberg
 *
 * Illustrates the geometric relationship between Toroid, Sphere, and Helix
 * 3D primitives, as well as lathing principal.
 *
 * Instructions:
 * UP arrow key pts++
 * DOWN arrow key pts--
 * LEFT arrow key segments--
 * RIGHT arrow key segments++
 * 'a' key toroid radius--
 * 's' key toroid radius++
 * 'z' key initial polygon radius--
 * 'x' key initial polygon radius++
 * 'w' key toggle wireframe/solid shading
 * 'h' key toggle sphere/helix
 """

pts = 40
radius = 60.0

# lathe segments
segments = 60
latheRadius = 100.0

# for shaded or wireframe rendering
isWireFrame = False

# for optional helix
isHelix = False
helixOffset = 5.0

# The extruded shape as a list of quad strips
strips = []

def setup():
    size(640, 360, OPENGL)

def extrude():
    dTheta = TWO_PI / pts
    helicalOffset = 0
    if isHelix:
        helicalOffset = - (helixOffset * segments) / 2
    vertices = [[latheRadius + sin(dTheta * x) * radius,
                 cos(dTheta * x) * radius + helicalOffset]
                 for x in range(pts + 1)]
    vertices2 = [[0.0, 0.0, 0.0] for x in range(pts + 1)]

    # draw toroid
    latheAngle = 0
    dTheta = TWO_PI / segments
    if isHelix:
        dTheta *= 2
    for i in range(segments + 1):
        verts = []
        for j in range(pts + 1):
            v2 = vertices2[j]
            if i > 0:
                verts.append(v2[:])

            v2[0] = cos(latheAngle) * vertices[j][0]
            v2[1] = sin(latheAngle) * vertices[j][0]
            v2[2] = vertices[j][1]
            # optional helix offset
            if isHelix:
                vertices[j][1] += helixOffset

            verts.append(v2[:])
        strips.append(verts)
        latheAngle += dTheta

def draw():
    if not len(strips):
        extrude()

    background(50, 64, 42)
    # basic lighting setup
    lights()

    # 2 rendering styles
    # wireframe or solid
    if isWireFrame:
        stroke(255, 255, 150)
        noFill()
    else:
        noStroke()
        fill(150, 195, 125)

    text("%s" % frameRate, 20, 40)
    #center and spin toroid
    translate(width / 2, height / 2, -100)
    rotateX(frameCount * PI / 150)
    rotateY(frameCount * PI / 170)
    rotateZ(frameCount * PI / 90)

    # draw toroid
    for strip in strips:
        beginShape(QUAD_STRIP)
        for v in strip:
            vertex(v[0], v[1], v[2])
        endShape()


"""
 left/right arrow keys control ellipse detail
 up/down arrow keys control segment detail.
 'a','s' keys control lathe radius
 'z','x' keys control ellipse radius
 'w' key toggles between wireframe and solid
 'h' key toggles between toroid and helix
 """
def keyPressed():
    global pts, segments, isHelix, isWireFrame, latheRadius, radius
    
    # clear the list of strips, to force a re-evaluation
    del strips[:]

    if key == CODED:
        # pts
        if keyCode == UP:
            if pts < 40:
                pts += 1
        elif keyCode == DOWN:
            if pts > 3:
                pts -= 1
        # extrusion length
        if keyCode == LEFT:
            if segments > 3:
                segments -= 1
        elif keyCode == RIGHT:
            if segments < 80:
                segments += 1
    # lathe radius
    elif key == 'a':
        if latheRadius > 0:
            latheRadius -= 1
    elif key == 's':
        latheRadius += 1
    # ellipse radius
    elif key == 'z':
        if radius > 10:
            radius -= 1
    elif key == 'x':
        radius += 1
    # wireframe
    elif key == 'w':
        isWireFrame = not isWireFrame
    # helix
    elif key == 'h':
        isHelix = not isHelix

########NEW FILE########
__FILENAME__ = Vertices
"""
  Vertices
  by Simon Greenwold.
  (Rewritten in Python by Jonathan Feinberg.)

  Draw a cylinder centered on the y-axis, going down
  from y=0 to y=height. The radius at the top can be
  different from the radius at the bottom, and the
  number of sides drawn is variable.
 """
def setup():
    size(640, 360, P3D)

def draw():
    background(0)
    lights()
    translate(width / 2, height / 2)
    rotateY(map(mouseX, 0, width, 0, PI))
    rotateZ(map(mouseY, 0, height, 0, -PI))
    noStroke()
    fill(255, 255, 255)
    translate(0, -40, 0)
    drawCylinder(10, 180, 200, 16) # Draw a mix between a cylinder and a cone
    #drawCylinder(70, 70, 120, 64) # Draw a cylinder
    #drawCylinder(0, 180, 200, 4) # Draw a pyramid

def drawCylinder(topRadius, bottomRadius, tall, sides):
    angle = 0
    angleIncrement = TWO_PI / sides
    beginShape(QUAD_STRIP)
    for i in range(sides + 1):
        vertex(topRadius * cos(angle), 0, topRadius * sin(angle))
        vertex(bottomRadius * cos(angle), tall, bottomRadius * sin(angle))
        angle += angleIncrement
    endShape()

    # If it is not a cone, draw the circular top cap
    if topRadius:
        angle = 0
        beginShape(TRIANGLE_FAN)
        # Center point
        vertex(0, 0, 0)
        for i in range(sides + 1):
            vertex(topRadius * cos(angle), 0, topRadius * sin(angle))
            angle += angleIncrement
        endShape()

    # If it is not a cone, draw the circular bottom cap
    if bottomRadius:
        angle = 0
        beginShape(TRIANGLE_FAN)
        # Center point
        vertex(0, tall, 0)
        for i in range(sides + 1):
            vertex(bottomRadius * cos(angle), tall, bottomRadius * sin(angle))
            angle += angleIncrement
        endShape()

########NEW FILE########
__FILENAME__ = Explode
"""
  Explode 
  by Daniel Shiffman.
  (Rewritten in Python by Jonathan Feinberg.) 
  
  Mouse horizontal location controls breaking apart of image and 
  Maps pixels from a 2D image into 3D space. Pixel brightness controls 
  translation along z axis. 
 """
 
cellsize = 2 # Dimensions of each cell in the grid
img = loadImage("eames.jpg")
columns = img.width / cellsize  # Calculate # of columns
rows = img.height / cellsize    # Calculate # of rows
def setup():
    size(640, 360, P3D) 

def draw(): 
    background(0)
    for row in range(rows):
        for col in range(columns):
            x = cellsize * col + cellsize / 2
            y = cellsize * row + cellsize / 2
            loc = x + y * img.width  # Pixel array location
            c = img.pixels[loc]      # Grab the color
            # Calculate a z position as a function of mouseX and pixel brightness
            z = (mouseX / float(width)) * brightness(img.pixels[loc]) - 20.0
            # Translate to the location, set fill and stroke, and draw the rect
            pushMatrix()
            translate(x + 200, y + 100, z)
            fill(c, 204)
            noStroke()
            rectMode(CENTER)
            rect(0, 0, cellsize, cellsize)
            popMatrix()

########NEW FILE########
__FILENAME__ = TextureCube
"""
 * TexturedCube
 * based on pde example by Dave Bollinger.
 * 
 * Drag mouse to rotate cube. Demonstrates use of u/v coords in 
 * vertex() and effect on texture().
"""
tex = loadImage("data/berlin-1.jpg")
rotx = PI / 4
roty = PI / 4
rate = 0.01

def setup(): 
    size(640, 360, OPENGL)
    textureMode(NORMAL)
    fill(255)
    stroke(color(44, 48, 32))

def draw(): 
    background(0)
    noStroke()
    translate(width / 2.0, height / 2.0, -100)
    rotateX(rotx)
    rotateY(roty)
    scale(90)
    TexturedCube()

def TexturedCube():
    beginShape(QUADS)
    texture(tex)
    # Given one texture and six faces, we can easily set up the uv coordinates
    # such that four of the faces tile "perfectly" along either u or v, but the other
    # two faces cannot be so aligned.    This code tiles "along" u, "around" the X / Z faces
    # and fudges the Y faces - the Y faces are arbitrarily aligned such that a
    # rotation along the X axis will put the "top" of either texture at the "top"
    # of the screen, but is not otherwised aligned with the X / Z faces. (This
    # just affects what type of symmetry is required if you need seamless
    # tiling all the way around the cube)
    
    # +Z "front" face
    vertex(-1, -1, 1, 0, 0)
    vertex(1, -1, 1, 1, 0)
    vertex(1, 1, 1, 1, 1)
    vertex(-1, 1, 1, 0, 1)
    # -Z "back" face
    vertex(1, -1, -1, 0, 0)
    vertex(-1, -1, -1, 1, 0)
    vertex(-1, 1, -1, 1, 1)
    vertex(1, 1, -1, 0, 1)
    # +Y "bottom" face
    vertex(-1, 1, 1, 0, 0)
    vertex(1, 1, 1, 1, 0)
    vertex(1, 1, -1, 1, 1)
    vertex(-1, 1, -1, 0, 1)
    # -Y "top" face
    vertex(-1, -1, -1, 0, 0)
    vertex(1, -1, -1, 1, 0)
    vertex(1, -1, 1, 1, 1)
    vertex(-1, -1, 1, 0, 1)
    # +X "right" face
    vertex(1, -1, 1, 0, 0)
    vertex(1, -1, -1, 1, 0)
    vertex(1, 1, -1, 1, 1)
    vertex(1, 1, 1, 0, 1)
    # -X "left" face
    vertex(-1, -1, -1, 0, 0)
    vertex(-1, -1, 1, 1, 0)
    vertex(-1, 1, 1, 1, 1)
    vertex(-1, 1, -1, 0, 1)
    endShape()
    
def mouseDragged():
    global rotx, roty
    rotx += (pmouseY - mouseY) * rate
    roty += (mouseX - pmouseX) * rate

########NEW FILE########
__FILENAME__ = KineticType
"""
 Kinetic Type
 by Zach Lieberman.
 Adapted to Python by Jonathan Feinberg
 Using push() and pop() to define the curves of the lines of type.
"""

words = [
          "sometimes it's like", "the lines of text", "are so happy",
          "that they want to dance", "or leave the page or jump",
          "can you blame them?", "living on the page like that",
          "waiting to be read..."
        ]

def setup():
    size(640, 360, OPENGL)
    hint(DISABLE_DEPTH_TEST)
    textFont(loadFont("Univers-66.vlw"), 1.0)
    fill(255)

def draw():
    background(0)
    pushMatrix()
    translate(-200, -50, -450)
    rotateY(0.3)

    # Now animate every line object & draw it...
    for i in range(len(words)):
        f1 = sin((i + 1.0) * (millis() / 10000.0) * TWO_PI)
        f2 = sin((8.0 - i) * (millis() / 10000.0) * TWO_PI)
        line = words[i]
        pushMatrix()
        translate(0.0, i*75, 0.0)
        for j in range(len(line)):
            if j != 0:
                translate(textWidth(line[j - 1]) * 75, 0.0, 0.0)
            rotateY(f1 * 0.005 * f2)
            pushMatrix()
            scale(75.0)
            text(line[j], 0.0, 0.0)
            popMatrix()
        popMatrix()
    popMatrix()

########NEW FILE########
__FILENAME__ = WaveGradient
"""
  Wave Gradient 
  by Ira Greenberg.
  Adapted to python by Jonathan Feinberg  
   
  Generate a gradient along a sin() wave.
"""

amplitude = 30
fillGap = 2.5

def setup():
  size(200, 200)
  background(200, 200, 200)
  noLoop()

def draw():
  frequency = 0
  for i in range(-75, height + 75):
    # Reset angle to 0, so waves stack properly
    angle = 0
    # Increasing frequency causes more gaps
    frequency += .006
    for j in range(width + 75):
      py = i + sin(radians(angle)) * amplitude
      angle += frequency
      c = color(abs(py - i) * 255 / amplitude,
                255 - abs(py - i) * 255 / amplitude,
                j * (255.0 / (width + 50)))
      # Hack to fill gaps. Raise value of fillGap if you increase frequency
      for filler in range(fillGap):
        set(int(j - filler), int(py) - filler, c)
        set(int(j), int(py), c)
        set(int(j + filler), int(py) + filler, c)

########NEW FILE########
__FILENAME__ = AdditiveWave
"""
 Additive Wave
 by Daniel Shiffman.
 (Rewritten in Python by Jonathan Feinberg.)

 Create a more complex wave by adding two waves together.
 """

xspacing = 8    # How far apart should each horizontal location be spaced
maxwaves = 4    # total # of waves to add together
amplitude = []  # Height of wave
dx = []         # Value for incrementing X, to be calculated as a function of period and xspacing
yvalues = []    # Using an array to store height values for the wave (not entirely necessary)

def setup():
    size(200, 200)
    frameRate(30)
    colorMode(RGB, 255, 255, 255, 100)
    smooth()
    for i in range(maxwaves):
        amplitude.append(random(10, 30))
        period = random(100, 300) # How many pixels before the wave repeats
        dx.append((TWO_PI / period) * xspacing)
    for i in range((width + 16) / xspacing):
      yvalues.append(0.0)

def theta():
  # Try different multipliers for 'angular velocity' here
  return frameCount * 0.02

def draw():
    background(0)
    calcWave()
    renderWave()

def calcWave():
    # Set all height values to zero
    for i in range(len(yvalues)):
        yvalues[i] = 0

    # Accumulate wave height values
    for j in range(maxwaves):
        x = theta()
        for i in range(len(yvalues)):
            # Every other wave is cosine instead of sine
            if (j % 2 == 0):
              yvalues[i] += sin(x) * amplitude[j]
            else:
              yvalues[i] += cos(x) * amplitude[j]
            x += dx[j]


def renderWave():
    # A simple way to draw the wave with an ellipse at each location
    noStroke()
    fill(255, 50)
    ellipseMode(CENTER)
    for x in range(len(yvalues)):
        ellipse(x * xspacing, width / 2 + yvalues[x], 16, 16)

########NEW FILE########
__FILENAME__ = noisefield
"""
  noisefield.py - demonstrate Perlin noise
  Jonathan Feinberg
"""
srcSize = 50
destSize = 400
g = None

def setup():
    global g
    size(destSize, destSize)
    g = createGraphics(srcSize, srcSize)
    
def draw():
    t = .0005 * millis()
    g.beginDraw()
    for y in range(srcSize):
        for x in range(srcSize):
            blue = noise(t + .1*x, t + .05*y, .1 * t)
            g.set(x, y, color(0, 0, 255 * blue))
    g.endDraw()
    image(g, 0, 0, destSize, destSize)

########NEW FILE########
__FILENAME__ = NoiseWave
"""
  Noise Wave
  by Daniel Shiffman.

  Using Perlin Noise to generate a wave-like pattern.
"""

xspacing = 8   # How far apart should each horizontal location be spaced

yoff = 0.0       # 2nd dimension of perlin noise
yvalues = None   # Using an array to store height values for the wave (not entirely necessary)

def setup():
    size(200, 200)
    frameRate(30)
    colorMode(RGB, 255, 255, 255, 100)
    smooth()
    global yvalues
    yvalues = [i for i in range((width + 16) / xspacing)]

def draw():
    background(0)
    calcWave()
    renderWave()

def calcWave():
    dx = 0.05
    dy = 0.01
    amplitude = 100.0

    # Increment y ('time')
    global yoff
    yoff += dy

    #xoff = 0.0  # Option #1
    xoff = yoff # Option #2

    for i in range(len(yvalues)):
        # Using 2D noise function
        #yvalues[i] = (2*noise(xoff,yoff)-1)*amplitude
        # Using 1D noise function
        yvalues[i] = (2 * noise(xoff) - 1) * amplitude
        xoff += dx

def renderWave():
    # A simple way to draw the wave with an ellipse at each location
    for x, v in enumerate(yvalues):
        noStroke()
        fill(255, 50)
        ellipseMode(CENTER)
        ellipse(x * xspacing, width / 2 + v, 16, 16)

########NEW FILE########
__FILENAME__ = simple_noisefield
"""
  simple_noisefield.py - demonstrate Perlin noise
  Jonathan Feinberg
"""

def setup():
    size(100, 100)

def draw():
    t = .0005 * millis()
    for y in range(height):
        for x in range(width):
            blue = noise(t + .1*x, t + .05*y, .2*t)
            set(x, y, color(0, 0, 255 * blue))

########NEW FILE########
__FILENAME__ = LoadDisplayShape
"""
 Load and Display a Shape.
 Illustration by George Brower.
 (Rewritten in Python by Jonathan Feinberg.)

 The loadShape() command is used to read simple SVG (Scalable Vector Graphics)
 files into a Processing sketch. This library was specifically tested under
 SVG files created from Adobe Illustrator. For now, we can't guarantee that
 it'll work for SVGs created with anything else.
 """
# The file "bot1.svg" must be in the data folder
# of the current sketch to load successfully
bot = loadShape("bot1.svg")

def setup():
    size(640, 360)
    smooth()
    noLoop() # Only run draw() once

def draw():
    background(102)
    shape(bot, 110, 90, 100, 100)  # Draw at coordinate (10, 10) at size 100 x 100
    shape(bot, 280, 40)            # Draw at coordinate (70, 60) at the default size

########NEW FILE########
__FILENAME__ = ScaleShape
"""
 Scale Shape.
 Illustration by George Brower.
 (Rewritten in Python by Jonathan Feinberg.)

 Move the mouse left and right to zoom the SVG file.
 This shows how, unlike an imported image, the lines
 remain smooth at any size.
 """

# The file "bot1.svg" must be in the data folder
# of the current sketch to load successfully
bot = loadShape("bot1.svg")

def setup():
    size(640, 360)
    smooth()

def draw():
    background(102)
    translate(width / 2, height / 2)
    zoom = map(mouseX, 0, width, 0.1, 4.5)
    scale(zoom)
    shape(bot, -140, -140)

########NEW FILE########
__FILENAME__ = anchors
"""
 *    Anchors and the bridge
 *
 *    by Ricard Marxer
 *
 *    This example shows the use of anchors and distance joints in order
 *    to create a bridge.
 """
from fisica import Fisica, FBody, FBox, FWorld, FCircle, FDistanceJoint

frequency = 5
damping = 1
puenteY = None
stepCount = 20
steps = []
world = []
boxWidth = 400/stepCount - 2

def setup():
    global puenteY, world

    size(400, 400)
    smooth()
    puenteY = height/3
    Fisica.init(this)
    world = FWorld()
    bola = FCircle(40)
    bola.setPosition(width/3, puenteY-10)
    bola.setDensity(0.2)
    bola.setFill(120, 120, 190)
    bola.setNoStroke()
    world.add(bola)
    for i in range(stepCount):
        box = FBox(boxWidth, 10)
        box.setPosition(map(i, 0, stepCount - 1, boxWidth, width-boxWidth), puenteY)
        box.setNoStroke()
        box.setFill(120, 200, 190)
        world.add(box)
        steps.append(box)
    for i in range(1, stepCount):
        junta = FDistanceJoint(steps[i-1], steps[i])
        junta.setAnchor1(boxWidth/2, 0)
        junta.setAnchor2(-boxWidth/2, 0)
        junta.setFrequency(frequency)
        junta.setDamping(damping)
        junta.setFill(0)
        junta.calculateLength()
        world.add(junta)
    left = FCircle(10)
    left.setStatic(True)
    left.setPosition(0, puenteY)
    left.setDrawable(False)
    world.add(left)
    right = FCircle(10)
    right.setStatic(True)
    right.setPosition(width, puenteY)
    right.setDrawable(False)
    world.add(right)
    juntaPrincipio = FDistanceJoint(steps[0], left)
    juntaPrincipio.setAnchor1(-boxWidth/2, 0)
    juntaPrincipio.setAnchor2(0, 0)
    juntaPrincipio.setFrequency(frequency)
    juntaPrincipio.setDamping(damping)
    juntaPrincipio.calculateLength()
    juntaPrincipio.setFill(0)
    world.add(juntaPrincipio)
    juntaFinal = FDistanceJoint(steps[stepCount-1], right)
    juntaFinal.setAnchor1(boxWidth/2, 0)
    juntaFinal.setAnchor2(0, 0)
    juntaFinal.setFrequency(frequency)
    juntaFinal.setDamping(damping)
    juntaFinal.calculateLength()
    juntaFinal.setFill(0)
    world.add(juntaFinal)

def draw():
    background(255)
    world.step()
    world.draw()

def mousePressed():
    radius = random(10, 40)
    bola = FCircle(radius)
    bola.setPosition(mouseX, mouseY)
    bola.setDensity(0.2)
    bola.setFill(120, 120, 190)
    bola.setNoStroke()
    world.add(bola)

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = bubbles
"""
 *    Buttons and bodies
 *
 *    by Ricard Marxer
 *
 *    This example shows how to create a blob.
 """
from fisica import Fisica, FWorld, FPoly, FBlob

world = None
xPos = 0

circleCount = 20
hole = 50
topMargin = 50
bottomMargin = 300
sideMargin = 100

def setup():
    global world

    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    world.setGravity(0, -300)
    l = FPoly()
    l.vertex(width/2-hole/2, 0)
    l.vertex(0, 0)
    l.vertex(0, height)
    l.vertex(0+sideMargin, height)
    l.vertex(0+sideMargin, height-bottomMargin)
    l.vertex(width/2-hole/2, topMargin)
    l.setStatic(True)
    l.setFill(0)
    l.setFriction(0)
    world.add(l)
    r = FPoly()
    r.vertex(width/2+hole/2, 0)
    r.vertex(width, 0)
    r.vertex(width, height)
    r.vertex(width-sideMargin, height)
    r.vertex(width-sideMargin, height-bottomMargin)
    r.vertex(width/2+hole/2, topMargin)
    r.setStatic(True)
    r.setFill(0)
    r.setFriction(0)
    world.add(r)

def draw():
    global xPos
    background(80, 120, 200)
    if (frameCount % 40) == 1:
        b = FBlob()
        s = random(30, 40)
        space = (width-sideMargin*2-s)
        xPos = (xPos + random(s, space/2)) % space
        b.setAsCircle(sideMargin + xPos+s/2, height-random(100), s, 20)
        b.setStroke(0)
        b.setStrokeWeight(2)
        b.setFill(255)
        b.setFriction(0)
        world.add(b)
    world.step()
    world.draw()

########NEW FILE########
__FILENAME__ = buttons
"""
 *    Buttons and bodies
 *
 *    by Ricard Marxer
 *
 *    This example shows how to create bodies.
 *    It also demonstrates the use of bodies as buttons.
 """
from fisica import Fisica, FWorld, FBox, FCircle, FPoly

boxButton = None
circleButton = None
polyButton = None
world = None
buttonColor = color(0x15, 0x5A, 0xAD)
hoverColor = color(0x55, 0xAA, 0x11)
bodyColor = color(0x6E, 0x05, 0x95)

def setup():
    global boxButton, circleButton, polyButton, world

    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    world.setEdges()
    world.remove(world.left)
    world.remove(world.right)
    world.remove(world.top)
    boxButton = FBox(40, 40)
    boxButton.setPosition(width/4, 100)
    boxButton.setStatic(True)
    boxButton.setFillColor(buttonColor)
    boxButton.setNoStroke()
    world.add(boxButton)
    circleButton = FCircle(40)
    circleButton.setPosition(2*width/4, 100)
    circleButton.setStatic(True)
    circleButton.setFillColor(buttonColor)
    circleButton.setNoStroke()
    world.add(circleButton)
    polyButton = FPoly()
    polyButton.vertex(20, 20)
    polyButton.vertex(-20, 20)
    polyButton.vertex(0, -20)
    polyButton.setPosition(3*width/4, 100)
    polyButton.setStatic(True)
    polyButton.setFillColor(buttonColor)
    polyButton.setNoStroke()
    world.add(polyButton)

def draw():
    background(255)
    world.step()
    world.draw()

def mousePressed():
    pressed = world.getBody(mouseX, mouseY)
    if pressed == boxButton:
        myBox = FBox(40, 40)
        myBox.setPosition(width/4, 200)
        myBox.setRotation(random(TWO_PI))
        myBox.setVelocity(0, 200)
        myBox.setFillColor(bodyColor)
        myBox.setNoStroke()
        world.add(myBox)
    elif pressed == circleButton:
        myCircle = FCircle(40)
        myCircle.setPosition(2*width/4, 200)
        myCircle.setRotation(random(TWO_PI))
        myCircle.setVelocity(0, 200)
        myCircle.setFillColor(bodyColor)
        myCircle.setNoStroke()
        world.add(myCircle)
    elif pressed == polyButton:
        myPoly = FPoly()
        myPoly.vertex(20, 20)
        myPoly.vertex(-20, 20)
        myPoly.vertex(0, -20)
        myPoly.setPosition(3*width/4, 200)
        myPoly.setRotation(random(TWO_PI))
        myPoly.setVelocity(0, 200)
        myPoly.setFillColor(bodyColor)
        myPoly.setNoStroke()
        world.add(myPoly)

def mouseMoved():
    hovered = world.getBody(mouseX, mouseY)
    if hovered in (boxButton, circleButton, polyButton):
        hovered.setFillColor(hoverColor)
    else:
        boxButton.setFillColor(buttonColor)
        circleButton.setFillColor(buttonColor)
        polyButton.setFillColor(buttonColor)

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = compound
"""
 *    Compound
 *
 *    by Ricard Marxer
 *
 *    This example shows how to create compound bodies
 *    which are bodies made of multiple shapes.
 """
from fisica import Fisica, FWorld, FCompound, FCircle, FBox

world, pop, cage = None, None, None

def setup():
    global world, pop, cage
    size(400, 400)
    smooth()
    Fisica.init(this)
    Fisica.setScale(10)
    world = FWorld()
    world.setEdges()
    world.remove(world.top)
    pop = createPop()
    pop.setPosition(width/2, height/2)
    pop.setBullet(True)
    world.add(pop)
    cage = createCage()
    cage.setPosition(width/2, height/2)
    cage.setRotation(PI/6)
    cage.setBullet(True)
    world.add(cage)

    for _ in range(10):
        c = FCircle(7)
        c.setPosition(width/2-10+random(-5, 5), height/2-10+random(-5, 5))
        c.setBullet(True)
        c.setNoStroke()
        c.setFillColor(color(0xFF, 0x92, 0x03))
        world.add(c)

    rectMode(CENTER)

def draw():
    background(255)
    world.step()
    world.draw()

def createPop():
    b = FBox(6, 60)
    b.setFillColor(color(0x1F, 0x71, 0x6B))
    b.setNoStroke()
    c = FCircle(20)
    c.setPosition(0, -30)
    c.setFillColor(color(0xFF, 0x00, 0x51))
    c.setNoStroke()

    result = FCompound()
    result.addBody(b)
    result.addBody(c)

    return result

def createCage():
    b1 = FBox(10, 110)
    b1.setPosition(50, 0)
    b1.setFill(0)
    b1.setNoStroke()
    b2 = FBox(10, 110)
    b2.setPosition(-50, 0)
    b2.setFill(0)
    b2.setNoStroke()

    b3 = FBox(110, 10)
    b3.setPosition(0, 50)
    b3.setFill(0)
    b3.setNoStroke()

    b4 = FBox(110, 10)
    b4.setPosition(0, -50)
    b4.setFill(0)
    b4.setNoStroke()

    result = FCompound()
    result.addBody(b1)
    result.addBody(b2)
    result.addBody(b3)
    result.addBody(b4)
    return result

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = contacts
"""
/**
 *  Contacts
 *
 *  by Ricard Marxer
 *
 *  This example shows how to use the contact events.
 */
"""
import fisica

world = None
obstacle = None

def setup():
  global world, obstacle
  size(400, 400)
  smooth()

  fisica.Fisica.init(this)

  world = fisica.FWorld()

  obstacle = fisica.FBox(150,150)
  obstacle.setRotation(PI/4)
  obstacle.setPosition(width/2, height/2)
  obstacle.setStatic(True)
  obstacle.setFill(0)
  obstacle.setRestitution(0)
  world.add(obstacle)

def draw():
  background(255)

  if frameCount % 5 == 0:
    b = fisica.FCircle(20)
    b.setPosition(width/2 + random(-50, 50), 50)
    b.setVelocity(0, 200)
    b.setRestitution(0)
    b.setNoStroke()
    b.setFill(200, 30, 90)
    world.add(b)

  world.draw()
  world.step()

  strokeWeight(1)
  stroke(255)
  for c in obstacle.getContacts():
    line(c.getBody1().getX(), c.getBody1().getY(), c.getBody2().getX(), c.getBody2().getY())

def contactStarted(c):
  ball = None
  if c.getBody1() == obstacle:
    ball = c.getBody2()
  elif c.getBody2() == obstacle:
    ball = c.getBody1()
  if ball:
    ball.setFill(30, 190, 200)

def contactPersisted(c):
  ball = None
  if c.getBody1() == obstacle:
    ball = c.getBody2()
  elif c.getBody2() == obstacle:
    ball = c.getBody1()
  if not ball:
    return

  ball.setFill(30, 120, 200)
  noStroke()
  fill(255, 220, 0)
  ellipse(c.getX(), c.getY(), 10, 10)

def contactEnded(c):
  ball = None
  if c.getBody1() == obstacle:
    ball = c.getBody2()
  elif c.getBody2() == obstacle:
    ball = c.getBody1()
  if ball:
    ball.setFill(200, 30, 90)

def keyPressed():
  saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = contact_remove
"""
 *    ContactRemove
 *
 *    by Ricard Marxer
 *
 *    This example shows how to use the contact events in order to remove bodies.
 """
from fisica import Fisica, FWorld, FBox, FCircle, FBody, FContact

world, pala = None, None

def setup():
    global world, pala
    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    pala = FBox(50, 20)
    pala.setPosition(width/2, height - 40)
    pala.setStatic(True)
    pala.setFill(0)
    pala.setRestitution(0)
    world.add(pala)

def draw():
    background(255)
    if frameCount % 8 == 0:
        b = FCircle(random(5, 20))
        b.setPosition(random(0+10, width-10), 50)
        b.setVelocity(0, 200)
        b.setRestitution(0)
        b.setNoStroke()
        b.setFill(200, 30, 90)
        world.add(b)
    pala.setPosition(mouseX, height - 40)
    world.draw()
    world.step()

def contactStarted(c):
    ball = None
    if c.getBody1() == pala:
        ball = c.getBody2()
    elif c.getBody2() == pala:
        ball = c.getBody1()
    if not ball:
        return
    ball.setFill(30, 190, 200)
    world.remove(ball)

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = contact_resize
"""
 *    ContactRemove
 *
 *    by Ricard Marxer
 *
 *    This example shows how to use the contact events in order to remove bodies.
 """
from fisica import Fisica, FWorld, FCircle, FContact

world = None

def setup():
    global world
    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    world.setGravity(0, 100)
    world.setEdges()

def draw():
    background(255)
    if frameCount % 50 == 0:
        sz = random(30, 60)
        b = FCircle(sz)
        b.setPosition(random(0+30, width-30), 50)
        b.setVelocity(0, 100)
        b.setRestitution(0.7)
        b.setDamping(0.01)
        b.setNoStroke()
        b.setFill(200, 30, 90)
        world.add(b)
    world.draw()
    world.step()

def contactEnded(c):
    for b in (c.getBody1(), c.getBody2()):
        if not b.isStatic() and b.getSize() > 5:
            b.setSize(b.getSize() * 0.9)

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = densities
"""
 *    Densities
 *
 *    by Ricard Marxer
 *
 *    This example shows how the density works.
 *    The density determines the mass per area of a body.
 *    In this example we show a column of balls all of same area and increasing
 *    densities from 0.1 to 0.9.
 *    These balls will collide against another column of balls all with the same
 *    density of 0.9.
 *    We can observe the different behavior of the collisions depending on the
 *    density.
 *
 *    Note that a density of 0.0 corresponds to a mass of 0 and the body will be
 *    considered static.
 """
from fisica import FWorld, Fisica, FCircle

world = None
ballCount = 9

def setup():
    global world
    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    world.setGravity(0, 0)
    world.setEdges()
    world.remove(world.left)
    world.remove(world.top)
    world.remove(world.bottom)
    for i in range(ballCount):
        b = FCircle(25)
        b.setPosition(40, map(i, 0, ballCount-1, 40, height-40))
        b.setDensity(map(i, 0, ballCount-1, 0.1, 0.9))
        b.setVelocity(100, 0)
        b.setDamping(0.0)
        b.setNoStroke()
        b.setFill(map(i, 0, ballCount-1, 120, 0))
        world.add(b)
    for i in range(ballCount):
        b = FCircle(25)
        b.setPosition(width/2, map(i, 0, ballCount-1, 40, height-40))
        b.setVelocity(0, 0)
        b.setDamping(0.0)
        b.setDensity(0.9)
        b.setNoStroke()
        b.setFill(125, 80, 120)
        world.add(b)

def draw():
    background(255)
    world.step()
    world.draw()

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = droppings
"""
 *    Droppings Remade
 *
 *    This example shows how to create a simple remake of my favorite
 *    soundtoy:<br/>
 *
 *        <a href=http:#www.balldroppings.com/>BallDroppings</a>
 *             by Josh Nimoy.
 """

from fisica import FWorld, Fisica, FCircle, FBody, FBox

mundo, caja = None, None
x, y = 0, 0

def setup():
    global mundo
    size(400, 400)
    smooth()

    Fisica.init(this)
    mundo = FWorld()
    mundo.setGravity(0, 200)

    frameRate(24)
    background(0)

def draw():
    fill(0, 100)
    noStroke()
    rect(0, 0, width, height)
    if frameCount % 24 == 0:
        bolita = FCircle(8)
        bolita.setNoStroke()
        bolita.setFill(255)
        bolita.setPosition(100, 20)
        bolita.setVelocity(0, 400)
        bolita.setRestitution(0.9)
        bolita.setDamping(0)
        mundo.add(bolita)
    mundo.step()
    mundo.draw(this)

def mousePressed():
    global caja, x, y
    caja = FBox(4, 4)
    caja.setStaticBody(True)
    caja.setStroke(255)
    caja.setFill(255)
    caja.setRestitution(0.9)
    mundo.add(caja)

    x = mouseX
    y = mouseY

def mouseDragged():
    if not caja:
        return
    ang = atan2(y - mouseY, x - mouseX)
    caja.setRotation(ang)
    caja.setPosition(x+(mouseX-x)/2.0, y+(mouseY-y)/2.0)
    caja.setWidth(dist(mouseX, mouseY, x, y))

def contactStarted(contacto):
    cuerpo1 = contacto.getBody1()
    cuerpo1.setFill(255, 0, 0)
    cuerpo1.setStroke(255, 0, 0)

    noFill()
    stroke(255)
    ellipse(contacto.getX(), contacto.getY(), 30, 30)

def contactEnded(contacto):
    cuerpo1 = contacto.getBody1()
    cuerpo1.setFill(255)
    cuerpo1.setStroke(255)

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = inherit
from fisica import Fisica, FWorld, FBox

class Texto(FBox):
    def __init__(self, _texto):
        FBox.__init__(self, textWidth(_texto), textAscent() + textDescent())
        self.texto = _texto
        self.textOffset = textAscent() - self.getHeight()/2

    def draw(self, applet):
        FBox.draw(self, applet)
        self.preDraw(applet)
        fill(0)
        stroke(0)
        textAlign(CENTER)
        text(self.texto, 0, self.textOffset)
        self.postDraw(applet)

msg = ''
world = None

def setup():
    global world

    size(400, 400)
    smooth()
    Fisica.init(this)
    font = loadFont("FreeMonoBold-24.vlw")
    textFont(font, 24)
    world = FWorld()
    world.setEdges(this, color(120))
    world.remove(world.top)
    world.setGravity(0, 500)
    t = Texto("Type and ENTER")
    t.setPosition(width/2, height/2)
    t.setRotation(random(-1, 1))
    t.setFill(255)
    t.setNoStroke()
    t.setRestitution(0.75)
    world.add(t)

def draw():
    background(120)
    world.step()
    world.draw()

def keyPressed():
    global msg
    if key == ENTER:
        if msg:
            t = Texto(msg)
            t.setPosition(width/2, height/2)
            t.setRotation(random(-1, 1))
            t.setFill(255)
            t.setNoStroke()
            t.setRestitution(0.65)
            world.add(t)
            msg = ''
    elif key == CODED and keyCode == CONTROL:
        saveFrame("screenshot.png")
    else:
        msg += key

########NEW FILE########
__FILENAME__ = joints
"""
 *    Joints
 *
 *    by Ricard Marxer
 *
 *    This example shows how to access all the joints of a given body.
 """
from fisica import Fisica, FWorld, FCircle, FDistanceJoint, FJoint

bodyColor = color(0x6E, 0x05, 0x95)
hoverColor = color(0xF5, 0xB5, 0x02)
spiderCount = 10
mainSize = 40
legCount = 10
legSize = 100

world = None
mains = []

def setup():
    global world
    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    world.setEdges()
    world.setGravity(0, 0)
    for _ in range(spiderCount):
        createSpider()

def draw():
    background(255)
    world.step()
    world.draw()

def mouseMoved():
    hovered = world.getBody(mouseX, mouseY)
    for other in mains:
        if hovered == other:
            setJointsDrawable(other, True)
            setJointsColor(other, hoverColor)
        else:
            setJointsDrawable(other, False)
            setJointsColor(other, bodyColor)

def keyPressed():
    saveFrame("screenshot.png")

def createSpider():
    posX = random(mainSize/2, width-mainSize/2)
    posY = random(mainSize/2, height-mainSize/2)
    main = FCircle(mainSize)
    main.setPosition(posX, posY)
    main.setVelocity(random(-20,20), random(-20,20))
    main.setFillColor(bodyColor)
    main.setNoStroke()
    main.setGroupIndex(2)
    world.add(main)
    mains.append(main)
    for i in range(legCount):
        x = legSize * cos(i*TWO_PI/3) + posX
        y = legSize * sin(i*TWO_PI/3) + posY
        leg = FCircle(mainSize/2)
        leg.setPosition(posX, posY)
        leg.setVelocity(random(-20,20), random(-20,20))
        leg.setFillColor(bodyColor)
        leg.setNoStroke()
        world.add(leg)
        j = FDistanceJoint(main, leg)
        j.setLength(legSize)
        j.setNoStroke()
        j.setStroke(0)
        j.setFill(0)
        j.setDrawable(False)
        j.setFrequency(0.1)
        world.add(j)

def setJointsColor(b, c):
    for j in b.getJoints():
        j.setStrokeColor(c)
        j.setFillColor(c)
        j.getBody1().setFillColor(c)
        j.getBody2().setFillColor(c)

def setJointsDrawable(b, c):
    for j in b.getJoints():
        j.setDrawable(c)

########NEW FILE########
__FILENAME__ = polygons
"""
 *    Polygons
 *
 *    by Ricard Marxer
 *
 *    This example shows how to create polygon bodies.
 """
from fisica import Fisica, FWorld, FPoly, FBody

world, poly = None, None

def setup():
    global world
    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    world.setGravity(0, 800)
    world.setEdges()
    world.remove(world.left)
    world.remove(world.right)
    world.remove(world.top)

    world.setEdgesRestitution(0.5)

def draw():
    background(255)
    world.step()
    world.draw(this)
    # Draw the polygon while
    # while it is being created
    # and hasn't been added to the
    # world yet
    if poly:
        poly.draw(this)

def mousePressed():
    if world.getBody(mouseX, mouseY):
        return
    global poly
    poly = FPoly()
    poly.setStrokeWeight(3)
    poly.setFill(120, 30, 90)
    poly.setDensity(10)
    poly.setRestitution(0.5)
    poly.vertex(mouseX, mouseY)

def mouseDragged():
    if poly:
        poly.vertex(mouseX, mouseY)

def mouseReleased():
    global poly
    if poly:
        world.add(poly)
        poly = None

def keyPressed():
    if key == BACKSPACE:
        hovered = world.getBody(mouseX, mouseY)
        if hovered and not hovered.isStatic():
            world.remove(hovered)
    else:
        saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = raycast
"""
 *    Raycast
 *
 *    by Ricard Marxer
 *
 *    This example shows how to use the raycasts.
 """
from fisica import Fisica, FWorld, FBody, FBox, FRaycastResult

#import org.jbox2d.common.*

world, obstacle = None, None

def setup():
    global world, obstacle
    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    obstacle = FBox(150,150)
    obstacle.setRotation(PI/4)
    obstacle.setPosition(width/2, height/2)
    obstacle.setStatic(True)
    obstacle.setFill(0)
    obstacle.setRestitution(0)
    world.add(obstacle)

def draw():
    background(255)
    world.draw()
    world.step()

    castRay()

def castRay():
    result = FRaycastResult()
    b = world.raycastOne(width/2, height, mouseX, mouseY, result, True)
    stroke(0)
    line(width/2, height, mouseX, mouseY)
    if b:
        b.setFill(120, 90, 120)
        fill(180, 20, 60)
        noStroke()

        x = result.getX()
        y = result.getY()
        ellipse(x, y, 10, 10)
    else:
        obstacle.setFill(0)

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = restitutions
"""
 *    Restitutions
 *
 *    by Ricard Marxer
 *
 *    This example shows how the restitution coefficients works.
 """
from fisica import Fisica, FWorld, FCircle

world = None

ballCount = 10

def setup():
    global world
    size(400, 400)
    smooth()
    Fisica.init(this)
    world = FWorld()
    world.setEdges()
    world.remove(world.left)
    world.remove(world.right)
    world.remove(world.top)
    world.setEdgesRestitution(0.0)
    for i in range(ballCount):
        b = FCircle(25)
        b.setPosition(map(i, 0, ballCount-1, 40, width-40), height/6)
        b.setRestitution(map(i, 0, ballCount-1, 0.0, 1.0))
        b.setNoStroke()
        b.setFill(map(i, 0, ballCount-1, 60, 255), 80, 120)
        world.add(b)

def draw():
    background(255)
    world.step()
    world.draw()

def keyPressed():
    saveFrame("screenshot.png")

########NEW FILE########
__FILENAME__ = LoadSample
"""
 * Load Sample
 * by Damien Di Fede. (Adapted to Python by Jonathan Feinberg)
 *    
 * This sketch demonstrates how to use the <code>loadSample</code> 
 * method of <code>Minim</code>. The <code>loadSample</code> 
 * method allows you to specify the sample you want to load with 
 * a <code>String</code> and optionally specify what you 
 * want the buffer size of the returned <code>AudioSample</code> 
 * to be. If you don't specify a buffer size, the returned sample 
 * will have a buffer size of 1024. Minim is able to load wav files, 
 * au files, aif files, snd files, and mp3 files. When you call 
 * <code>loadSample</code>, if you just specify the filename it will 
 * try to load the sample from the data folder of your sketch. However, 
 * you can also specify an absolute path (such as "C:\foo\bar\thing.wav") 
 * and the file will be loaded from that location (keep in mind that 
 * won't work from an applet). You can also specify a URL (such as 
 * "http:#www.mysite.com/mp3/song.mp3") but keep in mind that if you 
 * run the sketch as an applet you may run in to security restrictions 
 * if the applet is not on the same domain as the file you want to load. 
 * You can get around the restriction by signing the applet. Before you 
 * exit your sketch make sure you call the <code>close</code> method 
 * of any <code>AudioSamples</code>'s you have received from 
 * <code>loadSample</code>.
 *
 * An <code>AudioSample</code> is a special kind of file playback that 
 * allows you to repeatedly <i>trigger</i> an audio file. It does this 
 * by keeping the entire file in an internal buffer and then keeping a 
 * list of trigger points. <code>AudioSample</code> supports up to 20 
 * overlapping triggers, which should be plenty for short sounds. It is 
 * not advised that you use this class for long sounds (like entire songs, 
 * for example) because the entire file is kept in memory.
 * 
 * Press 'k' to trigger the sample.
"""

from ddf.minim import Minim

def setup():
    size(512, 200)
    # always start Minim before you do anything with it
    global minim
    minim = Minim(this)
    global kick
    # load BD.mp3 from the data folder with a 1024 sample buffer
    kick = minim.loadSample("BD.mp3")
    # load BD.mp3 from the data folder, with a 512 sample buffer
    #kick = minim.loadSample("BD.mp3", 2048)

def draw():
    background(0)
    stroke(255)
    # use the mix buffer to draw the waveforms.
    # because these are MONO files, we could have used the left or right buffers and got the same data
    for i in xrange(kick.bufferSize()-1):
        line(i, 100 - kick.left.get(i)*50, i+1, 100 - kick.left.get(i+1)*50)

def keyPressed():
    if key == 'k': kick.trigger()

def stop():
    # always close Minim audio classes when you are done with them
    kick.close()
    minim.stop()


########NEW FILE########
__FILENAME__ = Esfera
"""
 * Esfera
 * by David Pena. (Adapted to Python by Jonathan Feinberg)    
 * 
 * Distribucion aleatoria uniforme sobre la superficie de una esfera. 
"""

# Too slow for original 8000.
cuantos = 4000

class pelo:
    def __init__(self):
        self.z = random(-radio, radio)
        self.phi = random(TWO_PI)
        self.largo = random(1.15, 1.2)
        self.theta = asin(self.z / radio)

    def dibujar(self):
        off = (noise(millis() * 0.0005, sin(self.phi)) - 0.5) * 0.3
        offb = (noise(millis() * 0.0007, sin(self.z) * 0.01) - 0.5) * 0.3

        thetaff = self.theta + off
        phff = self.phi + offb
        x = radio * cos(self.theta) * cos(self.phi)
        y = radio * cos(self.theta) * sin(self.phi)
        z = radio * sin(self.theta)
        msx = screenX(x, y, z)
        msy = screenY(x, y, z)

        xo = radio * cos(thetaff) * cos(phff)
        yo = radio * cos(thetaff) * sin(phff)
        zo = radio * sin(thetaff)

        xb = xo * self.largo
        yb = yo * self.largo
        zb = zo * self.largo
        
        beginShape(LINES)
        stroke(0)
        vertex(x, y, z)
        stroke(200, 150)
        vertex(xb, yb, zb)
        endShape()
    
def setup():
    size(1024, 768, OPENGL)
    global radio, lista, rx, ry
    radio = height / 3.5
    lista = [pelo() for i in range(cuantos)]
    rx, ry = 0.0, 0.0
    noiseDetail(3)

def draw():
    background(0)
    translate(width / 2, height / 2)

    rxp = ((mouseX - (width / 2)) * 0.005)
    ryp = ((mouseY - (height / 2)) * 0.005)
    global rx, ry
    rx = (rx * 0.9) + (rxp * 0.1)
    ry = (ry * 0.9) + (ryp * 0.1)
    rotateY(rx)
    rotateX(ry)
    fill(0)
    noStroke()
    sphere(radio)

    for p in lista:
        p.dibujar()

    





########NEW FILE########
__FILENAME__ = SpaceJunk
"""
 Space Junk
 by Ira Greenberg.
 Zoom suggestion
 by Danny Greenberg.
 (Rewritten in Python by Jonathan Feinberg.)

 Rotating cubes in space.
 Color controlled by light sources.
 Move the mouse left and right to zoom.
"""

# Cube count-lower/raise to test P3D/OPENGL performance
limit = 500

# List of cubes, where each cube is a tuple
# (width, height, depth, x, y, z)
cubes = [(random(-10, 10), random(-10, 10), random(-10, 10),
          random(-140, 140), random(-140, 140), random(-140, 140))
          for i in range(limit)]

def setup():
    size(1024, 768, OPENGL)
    background(0)
    noStroke()

def draw():
    background(0)
    fill(200)

    # Set up some different colored lights
    pointLight(51, 102, 255, 65, 60, 100)
    pointLight(200, 40, 60, -65, -60, -150)

    # Raise overall light in scene
    ambientLight(70, 70, 10)

    # Center geometry in display windwow.
    # you can change 3rd argument ('0')
    # to move block group closer(+)/further(-)
    translate(width / 2, height / 2, -200 + mouseX * 0.65)

    # Rotate around y and x axes
    rotateY(frameCount * .01)
    rotateX(frameCount * .01)

    # Draw cubes
    for cube in cubes:
      pushMatrix()
      translate(cube[3], cube[4], cube[5])
      box(cube[0], cube[1], cube[2])
      popMatrix()
      rotateY(.01)
      rotateX(.01)
      rotateZ(.01)

########NEW FILE########
__FILENAME__ = OneFrame
"""
 * One Frame. 
 * 
 * Saves one PDF with the contents of the display window.
 * Because this example uses beginRecord, the image is shown
 * on the display window and is saved to the file.  
"""

#from processing.pdf import *

size(600, 600)

beginRecord(PDF, "line.pdf") 

background(255)
stroke(0, 20)
strokeWeight(20.0)
line(200, 0, 400, height)

endRecord()



########NEW FILE########
__FILENAME__ = peasycam
from peasy import PeasyCam

def setup():
    size(200, 200, P3D)
    cam = PeasyCam(this, 100)
    cam.setMinimumDistance(50)
    cam.setMaximumDistance(500)

def draw():
    rotateX(-.5)
    rotateY(-.5)
    background(0)
    fill(255,0,0)
    box(30)
    pushMatrix()
    translate(0,0,20)
    fill(0,0,255)
    box(5)
    popMatrix()

########NEW FILE########
__FILENAME__ = andres
nebula = None

def setup():
  size(512, 384, P2D)
 
  global nebula
  nebula = loadShader("nebula.glsl")
  nebula.set("resolution", float(width), float(height))
  shader(nebula) 

def draw():
  nebula.set("time", millis() / 1000.0);
  
  # The rect is needed to make the fragment shader go through every pixel of
  # the screen, but is not used for anything else since the rendering is entirely
  # generated by the shader.
  noStroke()
  fill(0)
  rect(0, 0, width, height)  


########NEW FILE########
__FILENAME__ = colorsketch
"""
Demonstrates using a third-party Python library
author: Jonathan Feinberg
"""
from namethatcolor import NameThatColor

flag = loadImage("flag.jpg")
namer = NameThatColor()

def setup():
    size(200, 200)

def draw():
    background(0)
    image(flag, 75, 40 )
    if mouseX >= 0 and mouseX <= width and mouseY >= 0 and mouseY <= height:
        c = 0x00FFFFFF & get(mouseX, mouseY)
        fill(c >> 16, c >> 8 & 0xFF, c & 0xFF)
        text(namer.name(hex(c)[2:]).name, 75, 120)
########NEW FILE########
__FILENAME__ = NameThatColor
#!/usr/bin/env python
"""
name_that_color.py -- find names for hex colors
Copyright (c) 2010, Jeremiah Dodds <jeremiah.dodds@gmail.com>

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the conditions in LICENSE.txt are met
"""
from collections import namedtuple
import os, re
ColorInfo = namedtuple('ColorInfo',
                       ' '.join(['hex_value', 'name', 'red', 'green', 'blue',
                                 'hue', 'saturation', 'lightness']))
Match = namedtuple('Match', ' '.join(['hex_value', 'name', 'exact',
                                      'original']))
RGB = namedtuple('RGB', ' '.join(['red', 'green', 'blue']))
HSL = namedtuple('HSL', ' '.join(['hue', 'saturation', 'lightness']))


class NameThatColor(object):
    """Utility for finding the closest "human readable" name for a hex color
    """
    def __init__(self, colorfile=None):
        import csv

        self.color_info = []

        data = os.path.dirname(__file__) + '/data/colors.csv'
        reader = csv.reader(open(data))

        for hex_val, name in reader:
            red, green, blue = self.rgb(hex_val.strip())
            hue, saturation, lightness = self.hsl(hex_val.strip())
            self.color_info.append(ColorInfo(hex_val.strip(), name.strip(),
                                             red, green, blue,
                                             hue, saturation, lightness))

    def name(self, color):
        """Return the closest human readable name given a color
        """
        color = color.upper()

        if not 3 < len(color) < 8:
            return Match("#000000", "Invalid Color", False, color)
        elif len(color) % 3 == 0:
            color = "#" + color
        elif len(color) == 4:
            color = ''.join(['#',
                             color[1], color[1],
                             color[2], color[2],
                             color[3], color[3]])

        red, green, blue = self.rgb(color)
        hue, saturation, lightness = self.hsl(color)

        ndf1 = 0
        ndf2 = 0
        ndf = 0
        the_color = Match(None, None, None, None)
        df = -1

        for info in self.color_info:
            if color == info.hex_value:
                return Match(info.hex_value, info.name, True, color)

            ndf1 = (((red - info.red) ** 2) +
                    ((green - info.green) ** 2) +
                    ((blue - info.blue) ** 2))
            ndf2 = (((hue - info.hue) ** 2) +
                    ((saturation - info.saturation) ** 2) +
                    ((lightness - info.lightness) ** 2))
            ndf = ndf1 + ndf2 * 2

            if not 0 < df < ndf:
                df = ndf
                the_color = info

        if not the_color.name:
            return Match("#000000", "Invalid Color", False, color)
        else:
            return Match(the_color.hex_value,
                         the_color.name,
                         False,
                         color)

    def rgb(self, color):
        """Given a hex string representing a color, return an object with
        values representing red, green, and blue.
        """
        return RGB(int(color[1:3], 16),
                   int(color[3:5], 16),
                   int(color[5:7], 16))

    def hsl(self, color):
        """Given a hex string representing a color, return an object with
        attributes representing hue, lightness, and saturation.
        """

        red, green, blue = self.rgb(color)

        red /= 255.0
        green /= 255.0
        blue /= 255.0

        min_color = min(red, min(green, blue))
        max_color = max(red, max(green, blue))
        delta = max_color - min_color
        lightness = (min_color + max_color) / 2

        saturation = 0
        sat_mod = ((2 * lightness) if lightness < 0.5 else (2 - 2 * lightness))

        if 0 < lightness < 1:
            saturation = (delta / sat_mod)

        hue = 0

        if delta > 0:
            if max_color == red and max_color != green:
                hue += (green - blue) / delta
            if max_color == green and max_color != blue:
                hue += (2 + (blue - red) / delta)
            if max_color == blue and max_color != red:
                hue += (4 + (red - green) / delta)
            hue /= 6

        return HSL(int(hue * 255),
                   int(saturation * 255),
                   int(lightness * 255))

def main():
    import json
    import argparse

    output_choices = {
        'match_hex': lambda m: m.hex_value,
        'match_name': lambda m: m.name,
        'is_exact': lambda m: m.exact,
        'original_hex': lambda m: m.original
    }

    format_choices = {
        'json': lambda r: json.dumps(r),
        'raw' : lambda r: r
    }
    
    parser = argparse.ArgumentParser(
        description="Find the closest known color name for a hex value")

    parser.add_argument('-c', '--colors', dest='colors_file',
                        help="a csv file of known color name definitions")

    parser.add_argument('target',
                        help="hex value of the color to search for")

    parser.add_argument('-o', '--output',
                        dest="output",
                        nargs='*',
                        choices=output_choices.keys(),
                        default=['match_hex', 'match_name'],
                        help="what information about the color match to output")

    parser.add_argument('--format',
                        dest="format",
                        choices=format_choices.keys(),
                        default="json",
                        help="what format to return data in")

    args = parser.parse_args()

    Namer = NameThatColor(args.colors_file)
    match = Namer.name(args.target)
    result = {}
    for choice in args.output:
        result[choice] = output_choices[choice](match)
    print format_choices[args.format](result)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = controlp5-demo
# Download ControlP5 from http://www.sojamo.de/libraries/controlP5/
# Drop the controlP5 folder into your processing.py libraries folder.
# This demo is adapted from one of the ControlP5 demos.

from controlP5 import ControlP5
from controlP5 import Slider

myColor = color(0,0,0)
sliderValue = 100
sliderTicks1 = 100
sliderTicks2 = 30

def demo_listener(e):
  print(e)

def setup():
  size(700,400)
  noStroke()
  cp5 = ControlP5(this)

  # add a horizontal sliders, the value of this slider will be linked
  # to variable 'sliderValue'
  cp5.addSlider("sliderValue").setPosition(100,50).setRange(0,255) \
      .addListener(demo_listener)

  # create another slider with tick marks, now without
  # default value, the initial value will be set according to
  # the value of variable sliderTicks2 then.
  cp5.addSlider("sliderTicks1").setPosition(100,140).setSize(20,100) \
      .setRange(0,255).setNumberOfTickMarks(5).addListener(demo_listener)

  # add a vertical slider
  cp5.addSlider("slider").setPosition(100,305).setSize(200,20) \
      .setRange(0,200).setValue(128).addListener(demo_listener)


  # reposition the Label for controller 'slider'
  cp5.getController("slider").getValueLabel() \
      .align(ControlP5.LEFT, ControlP5.BOTTOM_OUTSIDE).setPaddingX(0)
  cp5.getController("slider").getCaptionLabel() \
      .align(ControlP5.RIGHT, ControlP5.BOTTOM_OUTSIDE).setPaddingX(0)

  cp5.addSlider("sliderTicks2").setPosition(100,370).setWidth(400) \
     .setRange(255,0).setValue(128).setNumberOfTickMarks(7) \
     .setSliderMode(Slider.FLEXIBLE).addListener(demo_listener)

def draw():
  background(sliderTicks1)

  fill(sliderValue)
  rect(0,0,width,100)

  fill(myColor)
  rect(0,280,width,70)

  fill(sliderTicks2)
  rect(0,350,width,50)

########NEW FILE########
__FILENAME__ = directory_list
"""
 * Listing files in directories and subdirectories
 * inspired by an example by Daniel Shiffman.
 *
 * 1) List the names of files in a directory
 * 2) List the names along with metadata (size, lastModified)
 *        of files in a directory
 * 3) List the names along with metadata (size, lastModified)
 *        of files in a directory and all subdirectories (using recursion)
"""

from datetime import datetime
import os

def sizeof_fmt(num):
    for fmt in ['%3d bytes', '%3dK', '%3.1fM', '%3.1fG']:
        if num < 1024.0:
            return fmt % num
        num /= 1024.0

def print_file_details(f, depth=0):
    if os.path.basename(f)[0] == '.':
        return            # no dotfiles
    print '  ' * depth,   # funny Python syntax: trailing comma means no newline
    if os.path.isdir(f):
        print "+%s" % os.path.basename(f)
    else:
        mtime = datetime.fromtimestamp(os.path.getmtime(f))
        info = '%s, modified %s' % (sizeof_fmt(os.path.getsize(f)),
                                    mtime.strftime("%Y-%m-%d %H:%M:%S"))
        print "%-30s %s" % (os.path.basename(f), info)

def list_recursively(f, depth=0):
    if os.path.basename(f)[0] == '.':
        return # no dotfiles
    print_file_details(f, depth)
    if os.path.isdir(f):
        for g in os.listdir(f):
            path = os.path.join(f, g)
            list_recursively(path, depth + 1)

topdir = os.getcwd()

print "Listing names of all files in %s:" % topdir
for f in os.listdir(topdir):
    print f

print "Listing info about all files in %s:" % topdir
for f in os.listdir(topdir):
    print_file_details(f)

print "---------------------------------------"
print "Descending into %s:" % topdir
list_recursively(topdir)

exit()

########NEW FILE########
__FILENAME__ = list_example
"""
 * List of objects
 * based on ArrayListClass Daniel Shiffman.
 *
 * This example demonstrates how to use a Python list to store
 * a variable number of objects.    Items can be added and removed
 * from the list.
 *
 * Click the mouse to add bouncing balls.
"""

balls = []
ballWidth = 48

# Simple bouncing ball class

class Ball:
    def __init__(self, tempX, tempY, tempW):
        self.x = tempX
        self.y = tempY
        self.w = tempW
        self.speed = 0
        self.gravity = 0.1
        self.life = 255

    def move(self):
        # Add gravity to speed
        self.speed = self.speed + self.gravity
        # Add speed to y location
        self.y = self.y + self.speed
        # If square reaches the bottom
        # Reverse speed
        if self.y > height:
            # Dampening
            self.speed = self.speed * -0.8
            self.y = height

        self.life -= 1

    def finished(self):
        # Balls fade out
        return self.life < 0

    def display(self):
        # Display the circle
        fill(0, self.life)
        #stroke(0,life)
        ellipse(self.x, self.y, self.w, self.w)

def setup():
    size(200, 200)
    smooth()
    noStroke()

    # Start by adding one element
    balls.append(Ball(width / 2, 0, ballWidth))

def draw():
    background(255)

    # Count down backwards from the end of the list
    for ball in reversed(balls):
        ball.move()
        ball.display()
        if ball.finished():
            balls.remove(ball)

def mousePressed():
    # A new ball object is added to the list (by default to the end)
    balls.append(Ball(mouseX, mouseY, ballWidth))

########NEW FILE########
__FILENAME__ = Metaball
"""
  Metaball Demo Effect
  by luis2048. (Adapted to Python by Jonathan Feinberg)

  Organic-looking n-dimensional objects. The technique for rendering
  metaballs was invented by Jim Blinn in the early 1980s. Each metaball
  is defined as a function in n-dimensions.
"""

numBlobs = 3

# Position vector for each blob
blogPx = [0, 90, 90]
blogPy = [0, 120, 45]

# Movement vector for each blob
blogDx = [1, 1, 1]
blogDy = [1, 1, 1]

pg = None 
def setup():
    global pg
    size(640, 360)
    pg = createGraphics(160, 90)

    frame.setTitle("Processing.py")


def draw():
    vx, vy = [], []
    for i in range(numBlobs):
        blogPx[i] += blogDx[i]
        blogPy[i] += blogDy[i]

        # bounce across screen
        if blogPx[i] < 0: blogDx[i] = 1
        if blogPx[i] > pg.width: blogDx[i] = -1
        if blogPy[i] < 0: blogDy[i] = 1
        if blogPy[i] > pg.height: blogDy[i] = -1

        vx.append(tuple(sq(blogPx[i] - x) for x in xrange(pg.width)))
        vy.append(tuple(sq(blogPy[i] - y) for y in xrange(pg.height)))

  # Output into a buffered image for reuse
    pg.beginDraw()
    for y in range(pg.height):
        for x in range(pg.width):
            m = 1
            for i in range(numBlobs):
                # Increase this number to make your blobs bigger
                m += 60000 / (vy[i][y] + vx[i][x] + 1)
                pg.set(x, y, color(0, m + x, (x + m + y) / 2))
    pg.endDraw()

  # Display the results
    image(pg, 0, 0, width, height)

########NEW FILE########
__FILENAME__ = EdgeDetection
"""
 * Edge Detection. 
 * 
 * Exposing areas of contrast within an image 
 * by processing it through a high-pass filter. 
"""
kernel = (( -1, -1, -1 ),
          ( -1,  9, -1 ),
          ( -1, -1, -1 ))

size(200, 200)
img = loadImage("house.jpg") # Load the original image
image(img, 0, 0)             # Displays the image from point (0,0) 
img.loadPixels();
# Create an opaque image of the same size as the original
edgeImg = createImage(img.width, img.height, RGB)
# Loop through every pixel in the image.
for y in range(1, img.height-1):  # Skip top and bottom edges
    for x in range(1, img.width-1): # Skip left and right edges
        sum = 0  # Kernel sum for this pixel
        for ky in (-1, 0, 1):
            for kx in (-1, 0, 1):
                # Calculate the adjacent pixel for this kernel point
                pos = (y + ky)*img.width + (x + kx)
                # Image is grayscale, red/green/blue are identical
                val = red(img.pixels[pos])
                # Multiply adjacent pixels based on the kernel values
                sum += kernel[ky+1][kx+1] * val
        # For this pixel in the new image, set the gray value
        # based on the sum from the kernel
        edgeImg.pixels[y*img.width + x] = color(sum)

# State that there are changes to edgeImg.pixels[]
edgeImg.updatePixels()
image(edgeImg, 100, 0) # Draw the new image

########NEW FILE########
__FILENAME__ = astpp
"""
A pretty-printing dump function for the ast module.  The code was copied from
the ast.dump function and modified slightly to pretty-print.

Alex Leone (acleone ~AT~ gmail.com), 2010-01-30

From http://alexleone.blogspot.co.uk/2010/01/python-ast-pretty-printer.html
"""

from ast import *

def dump(node, annotate_fields=True, include_attributes=False, indent='  '):
    """
    Return a formatted dump of the tree in *node*.  This is mainly useful for
    debugging purposes.  The returned string will show the names and the values
    for fields.  This makes the code impossible to evaluate, so if evaluation is
    wanted *annotate_fields* must be set to False.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    *include_attributes* can be set to True.
    """
    def _format(node, level=0):
        if isinstance(node, AST):
            fields = [(a, _format(b, level)) for a, b in iter_fields(node)]
            if include_attributes and node._attributes:
                fields.extend([(a, _format(getattr(node, a), level))
                               for a in node._attributes])
            return ''.join([
                node.__class__.__name__,
                '(',
                ', '.join(('%s=%s' % field for field in fields)
                           if annotate_fields else
                           (b for a, b in fields)),
                ')'])
        elif isinstance(node, list):
            lines = ['[']
            lines.extend((indent * (level + 2) + _format(x, level + 2) + ','
                         for x in node))
            if len(lines) > 1:
                lines.append(indent * (level + 1) + ']')
            else:
                lines[-1] += ']'
            return '\n'.join(lines)
        return repr(node)

    if not isinstance(node, AST):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    return _format(node)

def parseprint(code, filename="<string>", mode="exec", **kwargs):
    """Parse some code from a string and pretty-print it."""
    node = parse(code, mode=mode)   # An ode to the code
    print(dump(node, **kwargs))

# Short name: pdp = parse, dump, print
pdp = parseprint

def load_ipython_extension(ip):
    from IPython.core.magic import Magics, magics_class, cell_magic
    from IPython.core import magic_arguments

    @magics_class
    class AstMagics(Magics):

        @magic_arguments.magic_arguments()
        @magic_arguments.argument(
            '-m', '--mode', default='exec',
            help="The mode in which to parse the code. Can be exec (the default), "
                 "eval or single."
        )
        @cell_magic
        def dump_ast(self, line, cell):
            """Parse the code in the cell, and pretty-print the AST."""
            args = magic_arguments.parse_argstring(self.dump_ast, line)
            parseprint(cell, mode=args.mode)

    ip.register_magics(AstMagics)

########NEW FILE########
__FILENAME__ = module
class MovingBall(object):

    # Constructor
    def __init__(self, xOffset, yOffset, x, y, speed, unit):
        self.xOffset = xOffset
        self.yOffset = yOffset
        self.x = x
        self.y = y
        self.speed = speed
        self.unit = unit
        self.xDirection = 1
        self.yDirection = 1

    # Custom method for updating the variables
    def update(self):
        self.x += (self.speed * self.xDirection)
        if self.x >= self.unit or self.x <= 0:
            self.xDirection *= -1
            self.x += self.xDirection
            self.y += self.yDirection
        if self.y >= self.unit or self.y <= 0:
            self.yDirection *= -1
            self.y += self.yDirection

    # Custom method for drawing the object
    def draw(self):
        fill(255)
        ellipse(self.xOffset + self.x, self.yOffset + self.y, 6, 6)


########NEW FILE########
__FILENAME__ = eye
class Eye:

    def __init__(self, tx, ty, ts):
        self.x = tx
        self.y = ty
        self.size = ts
        self.angle = 0.0

    def update(self, mx,  my):
        self.angle = atan2(my - self.y, mx - self.x)

    def display(self):
        pushMatrix()
        translate(self.x, self.y)
        fill(255)
        ellipse(0, 0, self.size, self.size)
        rotate(self.angle)
        fill(153, 204, 0)
        ellipse(self.size / 4, 0, self.size / 2, self.size / 2)
        popMatrix()


########NEW FILE########
__FILENAME__ = particle
class Particle:

    def __init__(self, sprite):
        self.gravity = PVector(0, 0.1)
        self.lifespan = 255
        partSize = random(10, 60)
        self.part = createShape()
        self.part.beginShape(QUAD)
        self.part.noStroke()
        self.part.texture(sprite)
        self.part.normal(0, 0, 1)
        self.part.vertex(-partSize / 2, -partSize / 2, 0, 0)
        self.part.vertex(+partSize / 2, -partSize / 2, sprite.width, 0)
        self.part.vertex(+partSize / 2, +partSize / 2,
                         sprite.width, sprite.height)
        self.part.vertex(-partSize / 2, +partSize / 2, 0, sprite.height)
        self.part.endShape()

        self.rebirth(width / 2, height / 2)
        self.lifespan = random(255)

    def getShape(self):
        return self.part

    def rebirth(self, x, y):
        a = random(TWO_PI)
        speed = random(0.5, 4)
        self.velocity = PVector(cos(a), sin(a))
        self.velocity.mult(speed)
        self.lifespan = 255
        self.part.resetMatrix()
        self.part.translate(x, y)

    def isDead(self):
        return self.lifespan < 0

    def update(self):
        self.lifespan -= 1
        self.velocity.add(self.gravity)
        self.part.setTint(color(255, self.lifespan))
        self.part.translate(self.velocity.x, self.velocity.y)


########NEW FILE########
__FILENAME__ = particle_system
from particle import Particle


class ParticleSystem:

    def __init__(self, n, sprite):
        self.particles = []
        self.particleShape = createShape(PShape.GROUP)
        for i in range(n):
            p = Particle(sprite)
            self.particles.append(p)
            self.particleShape.addChild(p.getShape())

    def update(self):
        for p in self.particles:
            p.update()

    def setEmitter(self, x, y):
        for p in self.particles:
            if p.isDead():
                p.rebirth(x, y)

    def display(self):
        shape(self.particleShape)


########NEW FILE########
__FILENAME__ = gesture
from java.awt import Polygon

from vec3f import Vec3f

capacity = 600
damp = 5.0
dampInv = 1.0 / damp
damp1 = damp - 1
INIT_TH = 14


class Gesture(object):

    def __init__(self, mw, mh):
        self.w = mw
        self.h = mh
        self.path = [Vec3f() for _ in range(capacity)]
        self.polygons = [Polygon() for _ in range(capacity)]
        for p in self.polygons:
            p.npoints = 4
        self.crosses = [0, ] * capacity
        self.nPolys = 0
        self.jumpDx = 0
        self.jumpDy = 0

        self.clear()

    def clear(self):
        self.nPoints = 0
        self.exists = False
        self.thickness = INIT_TH

    def clearPolys(self):
        self.nPolys = 0

    def addPoint(self, x, y):
        if self.nPoints >= capacity:
            # there are all sorts of possible solutions here,
            # but for abject simplicity, I don't do anything.
            pass
        else:
            v = self.distToLast(x, y)
            p = self.getPressureFromVelocity(v)
            self.path[self.nPoints].set(x, y, p)
            self.nPoints += 1
            if self.nPoints > 1:
                self.exists = True
                self.jumpDx = self.path[self.nPoints - 1].x - self.path[0].x
                self.jumpDy = self.path[self.nPoints - 1].y - self.path[0].y

    def getPressureFromVelocity(self, v):
        scale = 18
        minP = 0.02
        if self.nPoints > 0:
            oldP = self.path[self.nPoints - 1].p
        else:
            oldP = 0
        return ((minP + max(0, 1.0 - v / scale)) + (damp1 * oldP)) * dampInv

    def setPressures():
        # pressures vary from 0...1
        t = 0
        u = 1.0 / (self.nPoints - 1) * TWO_PI
        for i in range(self.nPoints):
            self.path[i].p = sqrt((1.0 - cos(t)) * 0.5)
            t += u

    def distToLast(self, ix, iy):
        if self.nPoints > 0:
            v = self.path[self.nPoints - 1]
            dx = v.x - ix
            dy = v.y - iy
            return mag(dx, dy)
        else:
            return 30

    def compile(self):
        # compute the polygons from the path of Vec3f's
        if not self.exists:
            return
        self.clearPolys()
        taper = 1.0
        nPathPoints = self.nPoints - 1
        lastPolyIndex = nPathPoints - 1
        npm1finv = 1.0 / max(1, nPathPoints - 1)
        # handle the first point
        p0 = self.path[0]
        p1 = self.path[1]
        radius0 = p0.p * self.thickness
        dx01 = p1.x - p0.x
        dy01 = p1.y - p0.y
        hp01 = sqrt(dx01 * dx01 + dy01 * dy01)
        if hp01 == 0:
            hp01 = 0.0001

        co01 = radius0 * dx01 / hp01
        si01 = radius0 * dy01 / hp01
        ax = p0.x - si01
        ay = p0.y + co01
        bx = p0.x + si01
        by = p0.y - co01
        xpts = []
        ypts = []
        LC = 20
        RC = self.w - LC
        TC = 20
        BC = self.h - TC
        mint = 0.618
        tapow = 0.4
        # handle the middle points
        i = 1
        for i in range(1, nPathPoints):
            taper = pow((lastPolyIndex - i) * npm1finv, tapow)
            p0 = self.path[i - 1]
            p1 = self.path[i]
            p2 = self.path[i + 1]
            p1x = p1.x
            p1y = p1.y
            radius1 = max(mint, taper * p1.p * self.thickness)
            # assumes all segments are roughly the same length...
            dx02 = p2.x - p0.x
            dy02 = p2.y - p0.y
            hp02 = sqrt(dx02 * dx02 + dy02 * dy02)
            if hp02 != 0:
                hp02 = radius1 / hp02

            co02 = dx02 * hp02
            si02 = dy02 * hp02
            # translate the integer coordinates to the viewing rectangle
            axi = axip = ax
            ayi = ayip = ay
            axi = self.w - (-axi % self.w) if axi < 0 else axi % self.w
            axid = axi - axip
            ayi = self.h - (-ayi % self.h) if ayi < 0 else ayi % self.h
            ayid = ayi - ayip
            # set the vertices of the polygon
            apoly = self.polygons[self.nPolys]
            self.nPolys += 1
            xpts = apoly.xpoints
            ypts = apoly.ypoints
            axi = int(axid + axip)
            xpts[0] = axi
            bxi = int(axid + bx)
            xpts[1] = bxi
            cx = p1x + si02
            cxi = int(axid + cx)
            xpts[2] = cxi
            dx = p1x - si02
            dxi = int(axid + dx)
            xpts[3] = dxi
            ayi = int(ayid + ayip)
            ypts[0] = ayi
            byi = int(ayid + by)
            ypts[1] = byi
            cy = p1y - co02
            cyi = int(ayid + cy)
            ypts[2] = cyi
            dy = p1y + co02
            dyi = int(ayid + dy)
            ypts[3] = dyi
            # keep a record of where we cross the edge of the screen
            self.crosses[i] = 0
            if (axi <= LC) or (bxi <= LC) or (cxi <= LC) or (dxi <= LC):
                self.crosses[i] |= 1

            if (axi >= RC) or (bxi >= RC) or (cxi >= RC) or (dxi >= RC):
                self.crosses[i] |= 2

            if (ayi <= TC) or (byi <= TC) or (cyi <= TC) or (dyi <= TC):
                self.crosses[i] |= 4

            if (ayi >= BC) or (byi >= BC) or (cyi >= BC) or (dyi >= BC):
                self.crosses[i] |= 8

            # swap data for next time
            ax = dx
            ay = dy
            bx = cx
            by = cy

        # handle the last point
        p2 = self.path[nPathPoints]
        apoly = self.polygons[self.nPolys]
        self.nPolys += 1
        xpts = apoly.xpoints
        ypts = apoly.ypoints
        xpts[0] = int(ax)
        xpts[1] = int(bx)
        xpts[2] = int(p2.x)
        xpts[3] = int(p2.x)
        ypts[0] = int(ay)
        ypts[1] = int(by)
        ypts[2] = int(p2.y)
        ypts[3] = int(p2.y)

    def smooth(self):
        # average neighboring points
        weight = 18
        scale = 1.0 / (weight + 2)
        for i in range(1, self.nPoints - 2):
            lower = self.path[i - 1]
            center = self.path[i]
            upper = self.path[i + 1]
            center.x = (lower.x + weight * center.x + upper.x) * scale
            center.y = (lower.y + weight * center.y + upper.y) * scale


########NEW FILE########
__FILENAME__ = vec3f
class Vec3f(object):

    def __init__(self):
        self.set(0, 0, 0)

    def __repr__(self):
        return '<Vec3f x:%f y:%f p:%f>' % (self.x, self.y, self.p)

    def set(self, ix, iy, ip):
        self.x = ix
        self.y = iy
        self.p = ip


########NEW FILE########
__FILENAME__ = animation
# Class for animating a sequence of GIFs
class Animation(object):

    def __init__(self, imagePrefix, count):
        self.frame = 0
        self.imageCount = count
        self.images = [PImage] * self.imageCount
        for i in range(self.imageCount):
            # Use nf() to number format 'i' into four digits
            filename = imagePrefix + nf(i, 4) + ".gif"
            self.images[i] = loadImage(filename)

    def display(self, xpos, ypos):
        self.frame = (self.frame + 1) % self.imageCount
        image(self.images[self.frame], xpos, ypos)

    def getWidth(self):
        return self.images[0].width


########NEW FILE########
__FILENAME__ = autopep8
#!/usr/bin/env python
#
# Copyright (C) 2010-2011 Hideo Hattori
# Copyright (C) 2011-2013 Hideo Hattori, Steven Myint
# Copyright (C) 2013-2014 Hideo Hattori, Steven Myint, Bill Wendling
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Automatically formats Python code to conform to the PEP 8 style guide.

Fixes that only need be done once can be added by adding a function of the form
"fix_<code>(source)" to this module. They should return the fixed source code.
These fixes are picked up by apply_global_fixes().

Fixes that depend on pep8 should be added as methods to FixPEP8. See the class
documentation for more information.

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import bisect
import codecs
import collections
import copy
import difflib
import fnmatch
import inspect
import io
import itertools
import keyword
import locale
import os
import re
import signal
import sys
import token
import tokenize

import pep8


try:
    unicode
except NameError:
    unicode = str


__version__ = '1.0.1a0'


CR = '\r'
LF = '\n'
CRLF = '\r\n'


PYTHON_SHEBANG_REGEX = re.compile(r'^#!.*\bpython[23]?\b\s*$')


# For generating line shortening candidates.
SHORTEN_OPERATOR_GROUPS = frozenset([
    frozenset([',']),
    frozenset(['%']),
    frozenset([',', '(', '[', '{']),
    frozenset(['%', '(', '[', '{']),
    frozenset([',', '(', '[', '{', '%', '+', '-', '*', '/', '//']),
    frozenset(['%', '+', '-', '*', '/', '//']),
])


DEFAULT_IGNORE = 'E24'
DEFAULT_INDENT_SIZE = 4


# W602 is handled separately due to the need to avoid "with_traceback".
CODE_TO_2TO3 = {
    'E721': ['idioms'],
    'W601': ['has_key'],
    'W603': ['ne'],
    'W604': ['repr'],
    'W690': ['apply',
             'except',
             'exitfunc',
             'import',
             'numliterals',
             'operator',
             'paren',
             'reduce',
             'renames',
             'standarderror',
             'sys_exc',
             'throw',
             'tuple_params',
             'xreadlines']}


def open_with_encoding(filename, encoding=None, mode='r'):
    """Return opened file with a specific encoding."""
    if not encoding:
        encoding = detect_encoding(filename)

    return io.open(filename, mode=mode, encoding=encoding,
                   newline='')  # Preserve line endings


def detect_encoding(filename):
    """Return file encoding."""
    return 'utf-8'  # modified for processing.py


def readlines_from_file(filename):
    """Return contents of file."""
    with open_with_encoding(filename) as input_file:
        return input_file.readlines()


def extended_blank_lines(logical_line,
                         blank_lines,
                         indent_level,
                         previous_logical):
    """Check for missing blank lines after class declaration."""
    if previous_logical.startswith('class '):
        if (
            logical_line.startswith(('def ', 'class ', '@')) or
            pep8.DOCSTRING_REGEX.match(logical_line)
        ):
            if indent_level and not blank_lines:
                yield (0, 'E309 expected 1 blank line after class declaration')
    elif previous_logical.startswith('def '):
        if blank_lines and pep8.DOCSTRING_REGEX.match(logical_line):
            yield (0, 'E303 too many blank lines ({0})'.format(blank_lines))
    elif pep8.DOCSTRING_REGEX.match(previous_logical):
        # Missing blank line between class docstring and method declaration.
        if (
            indent_level and
            not blank_lines and
            logical_line.startswith(('def ')) and
            '(self' in logical_line
        ):
            yield (0, 'E301 expected 1 blank line, found 0')
pep8.register_check(extended_blank_lines)


def continued_indentation(logical_line, tokens, indent_level, indent_char,
                          noqa):
    """Override pep8's function to provide indentation information."""
    first_row = tokens[0][2][0]
    nrows = 1 + tokens[-1][2][0] - first_row
    if noqa or nrows == 1:
        return

    # indent_next tells us whether the next block is indented. Assuming
    # that it is indented by 4 spaces, then we should not allow 4-space
    # indents on the final continuation line. In turn, some other
    # indents are allowed to have an extra 4 spaces.
    indent_next = logical_line.endswith(':')

    row = depth = 0
    valid_hangs = (
        (DEFAULT_INDENT_SIZE,)
        if indent_char != '\t' else (DEFAULT_INDENT_SIZE,
                                     2 * DEFAULT_INDENT_SIZE)
    )

    # Remember how many brackets were opened on each line.
    parens = [0] * nrows

    # Relative indents of physical lines.
    rel_indent = [0] * nrows

    # For each depth, collect a list of opening rows.
    open_rows = [[0]]
    # For each depth, memorize the hanging indentation.
    hangs = [None]

    # Visual indents.
    indent_chances = {}
    last_indent = tokens[0][2]
    indent = [last_indent[1]]

    last_token_multiline = None
    line = None
    last_line = ''
    last_line_begins_with_multiline = False
    for token_type, text, start, end, line in tokens:

        newline = row < start[0] - first_row
        if newline:
            row = start[0] - first_row
            newline = (not last_token_multiline and
                       token_type not in (tokenize.NL, tokenize.NEWLINE))
            last_line_begins_with_multiline = last_token_multiline

        if newline:
            # This is the beginning of a continuation line.
            last_indent = start

            # Record the initial indent.
            rel_indent[row] = pep8.expand_indent(line) - indent_level

            # Identify closing bracket.
            close_bracket = (token_type == tokenize.OP and text in ']})')

            # Is the indent relative to an opening bracket line?
            for open_row in reversed(open_rows[depth]):
                hang = rel_indent[row] - rel_indent[open_row]
                hanging_indent = hang in valid_hangs
                if hanging_indent:
                    break
            if hangs[depth]:
                hanging_indent = (hang == hangs[depth])

            visual_indent = (not close_bracket and hang > 0 and
                             indent_chances.get(start[1]))

            if close_bracket and indent[depth]:
                # Closing bracket for visual indent.
                if start[1] != indent[depth]:
                    yield (start, 'E124 {0}'.format(indent[depth]))
            elif close_bracket and not hang:
                pass
            elif indent[depth] and start[1] < indent[depth]:
                # Visual indent is broken.
                yield (start, 'E128 {0}'.format(indent[depth]))
            elif (hanging_indent or
                  (indent_next and
                   rel_indent[row] == 2 * DEFAULT_INDENT_SIZE)):
                # Hanging indent is verified.
                if close_bracket:
                    yield (start, 'E123 {0}'.format(indent_level +
                                                    rel_indent[open_row]))
                hangs[depth] = hang
            elif visual_indent is True:
                # Visual indent is verified.
                indent[depth] = start[1]
            elif visual_indent in (text, unicode):
                # Ignore token lined up with matching one from a previous line.
                pass
            else:
                one_indented = (indent_level + rel_indent[open_row] +
                                DEFAULT_INDENT_SIZE)
                # Indent is broken.
                if hang <= 0:
                    error = ('E122', one_indented)
                elif indent[depth]:
                    error = ('E127', indent[depth])
                elif hang > DEFAULT_INDENT_SIZE:
                    error = ('E126', one_indented)
                else:
                    hangs[depth] = hang
                    error = ('E121', one_indented)

                yield (start, '{0} {1}'.format(*error))

        # Look for visual indenting.
        if (parens[row] and token_type not in (tokenize.NL, tokenize.COMMENT)
                and not indent[depth]):
            indent[depth] = start[1]
            indent_chances[start[1]] = True
        # Deal with implicit string concatenation.
        elif (token_type in (tokenize.STRING, tokenize.COMMENT) or
              text in ('u', 'ur', 'b', 'br')):
            indent_chances[start[1]] = unicode
        # Special case for the "if" statement because len("if (") is equal to
        # 4.
        elif not indent_chances and not row and not depth and text == 'if':
            indent_chances[end[1] + 1] = True
        elif text == ':' and line[end[1]:].isspace():
            open_rows[depth].append(row)

        # Keep track of bracket depth.
        if token_type == tokenize.OP:
            if text in '([{':
                depth += 1
                indent.append(0)
                hangs.append(None)
                if len(open_rows) == depth:
                    open_rows.append([])
                open_rows[depth].append(row)
                parens[row] += 1
            elif text in ')]}' and depth > 0:
                # Parent indents should not be more than this one.
                prev_indent = indent.pop() or last_indent[1]
                hangs.pop()
                for d in range(depth):
                    if indent[d] > prev_indent:
                        indent[d] = 0
                for ind in list(indent_chances):
                    if ind >= prev_indent:
                        del indent_chances[ind]
                del open_rows[depth + 1:]
                depth -= 1
                if depth:
                    indent_chances[indent[depth]] = True
                for idx in range(row, -1, -1):
                    if parens[idx]:
                        parens[idx] -= 1
                        break
            assert len(indent) == depth + 1
            if (
                start[1] not in indent_chances and
                # This is for purposes of speeding up E121 (GitHub #90).
                not last_line.rstrip().endswith(',')
            ):
                # Allow to line up tokens.
                indent_chances[start[1]] = text

        last_token_multiline = (start[0] != end[0])
        if last_token_multiline:
            rel_indent[end[0] - first_row] = rel_indent[row]

        last_line = line

    if (
        indent_next and
        not last_line_begins_with_multiline and
        pep8.expand_indent(line) == indent_level + DEFAULT_INDENT_SIZE
    ):
        pos = (start[0], indent[0] + 4)
        yield (pos, 'E125 {0}'.format(indent_level +
                                      2 * DEFAULT_INDENT_SIZE))
del pep8._checks['logical_line'][pep8.continued_indentation]
pep8.register_check(continued_indentation)


class FixPEP8(object):

    """Fix invalid code.

    Fixer methods are prefixed "fix_". The _fix_source() method looks for these
    automatically.

    The fixer method can take either one or two arguments (in addition to
    self). The first argument is "result", which is the error information from
    pep8. The second argument, "logical", is required only for logical-line
    fixes.

    The fixer method can return the list of modified lines or None. An empty
    list would mean that no changes were made. None would mean that only the
    line reported in the pep8 error was modified. Note that the modified line
    numbers that are returned are indexed at 1. This typically would correspond
    with the line number reported in the pep8 error information.

    [fixed method list]
        - e121,e122,e123,e124,e125,e126,e127,e128,e129
        - e201,e202,e203
        - e211
        - e221,e222,e223,e224,e225
        - e231
        - e251
        - e261,e262
        - e271,e272,e273,e274
        - e301,e302,e303
        - e401
        - e502
        - e701,e702
        - e711
        - w291

    """

    def __init__(self, filename,
                 options,
                 contents=None,
                 long_line_ignore_cache=None):
        self.filename = filename
        if contents is None:
            self.source = readlines_from_file(filename)
        else:
            sio = io.StringIO(contents)
            self.source = sio.readlines()
        self.options = options
        self.indent_word = _get_indentword(''.join(self.source))

        self.long_line_ignore_cache = (
            set() if long_line_ignore_cache is None
            else long_line_ignore_cache)

        # Many fixers are the same even though pep8 categorizes them
        # differently.
        self.fix_e121 = self._fix_reindent
        self.fix_e122 = self._fix_reindent
        self.fix_e123 = self._fix_reindent
        self.fix_e124 = self._fix_reindent
        self.fix_e126 = self._fix_reindent
        self.fix_e127 = self._fix_reindent
        self.fix_e128 = self._fix_reindent
        self.fix_e129 = self._fix_reindent
        self.fix_e202 = self.fix_e201
        self.fix_e203 = self.fix_e201
        self.fix_e211 = self.fix_e201
        self.fix_e221 = self.fix_e271
        self.fix_e222 = self.fix_e271
        self.fix_e223 = self.fix_e271
        self.fix_e226 = self.fix_e225
        self.fix_e227 = self.fix_e225
        self.fix_e228 = self.fix_e225
        self.fix_e241 = self.fix_e271
        self.fix_e242 = self.fix_e224
        self.fix_e261 = self.fix_e262
        self.fix_e272 = self.fix_e271
        self.fix_e273 = self.fix_e271
        self.fix_e274 = self.fix_e271
        self.fix_e309 = self.fix_e301
        self.fix_e501 = (
            self.fix_long_line_logically if
            options and (options.aggressive >= 2 or options.experimental) else
            self.fix_long_line_physically)
        self.fix_e703 = self.fix_e702

        self._ws_comma_done = False

    def _fix_source(self, results):
        try:
            (logical_start, logical_end) = _find_logical(self.source)
            logical_support = True
        except (SyntaxError, tokenize.TokenError):  # pragma: no cover
            logical_support = False

        completed_lines = set()
        for result in sorted(results, key=_priority_key):
            if result['line'] in completed_lines:
                continue

            fixed_methodname = 'fix_' + result['id'].lower()
            if hasattr(self, fixed_methodname):
                fix = getattr(self, fixed_methodname)

                line_index = result['line'] - 1
                original_line = self.source[line_index]

                is_logical_fix = len(inspect.getargspec(fix).args) > 2
                if is_logical_fix:
                    logical = None
                    if logical_support:
                        logical = _get_logical(self.source,
                                               result,
                                               logical_start,
                                               logical_end)
                        if logical and set(range(
                            logical[0][0] + 1,
                            logical[1][0] + 1)).intersection(
                                completed_lines):
                            continue

                    modified_lines = fix(result, logical)
                else:
                    modified_lines = fix(result)

                if modified_lines is None:
                    # Force logical fixes to report what they modified.
                    assert not is_logical_fix

                    if self.source[line_index] == original_line:
                        modified_lines = []

                if modified_lines:
                    completed_lines.update(modified_lines)
                elif modified_lines == []:  # Empty list means no fix
                    if self.options.verbose >= 2:
                        print(
                            '--->  Not fixing {f} on line {l}'.format(
                                f=result['id'], l=result['line']),
                            file=sys.stderr)
                else:  # We assume one-line fix when None.
                    completed_lines.add(result['line'])
            else:
                if self.options.verbose >= 3:
                    print(
                        "--->  '{0}' is not defined.".format(fixed_methodname),
                        file=sys.stderr)

                    info = result['info'].strip()
                    print('--->  {0}:{1}:{2}:{3}'.format(self.filename,
                                                         result['line'],
                                                         result['column'],
                                                         info),
                          file=sys.stderr)

    def fix(self):
        """Return a version of the source code with PEP 8 violations fixed."""
        pep8_options = {
            'ignore': self.options.ignore,
            'select': self.options.select,
            'max_line_length': self.options.max_line_length,
        }
        results = _execute_pep8(pep8_options, self.source)

        if self.options.verbose:
            progress = {}
            for r in results:
                if r['id'] not in progress:
                    progress[r['id']] = set()
                progress[r['id']].add(r['line'])
            print('--->  {n} issue(s) to fix {progress}'.format(
                n=len(results), progress=progress), file=sys.stderr)

        if self.options.line_range:
            start, end = self.options.line_range
            results = [r for r in results
                       if start <= r['line'] <= end]

        self._fix_source(filter_results(source=''.join(self.source),
                                        results=results,
                                        aggressive=self.options.aggressive))

        if self.options.line_range:
            # If number of lines has changed then change line_range.
            count = sum(sline.count('\n')
                        for sline in self.source[start - 1:end])
            self.options.line_range[1] = start + count - 1

        return ''.join(self.source)

    def _fix_reindent(self, result):
        """Fix a badly indented line.

        This is done by adding or removing from its initial indent only.

        """
        num_indent_spaces = int(result['info'].split()[1])
        line_index = result['line'] - 1
        target = self.source[line_index]

        self.source[line_index] = ' ' * num_indent_spaces + target.lstrip()

    def fix_e125(self, result):
        """Fix indentation undistinguish from the next logical line."""
        num_indent_spaces = int(result['info'].split()[1])
        line_index = result['line'] - 1
        target = self.source[line_index]

        spaces_to_add = num_indent_spaces - len(_get_indentation(target))
        indent = len(_get_indentation(target))
        modified_lines = []

        while len(_get_indentation(self.source[line_index])) >= indent:
            self.source[line_index] = (' ' * spaces_to_add +
                                       self.source[line_index])
            modified_lines.append(1 + line_index)  # Line indexed at 1.
            line_index -= 1

        return modified_lines

    def fix_e201(self, result):
        """Remove extraneous whitespace."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        # Avoid pep8 bug (https://github.com/jcrocholl/pep8/issues/268).
        if offset < 0:
            return []

        if is_probably_part_of_multiline(target):
            return []

        fixed = fix_whitespace(target,
                               offset=offset,
                               replacement='')

        self.source[line_index] = fixed

    def fix_e224(self, result):
        """Remove extraneous whitespace around operator."""
        target = self.source[result['line'] - 1]
        offset = result['column'] - 1
        fixed = target[:offset] + target[offset:].replace('\t', ' ')
        self.source[result['line'] - 1] = fixed

    def fix_e225(self, result):
        """Fix missing whitespace around operator."""
        target = self.source[result['line'] - 1]
        offset = result['column'] - 1
        fixed = target[:offset] + ' ' + target[offset:]

        # Only proceed if non-whitespace characters match.
        # And make sure we don't break the indentation.
        if (
            fixed.replace(' ', '') == target.replace(' ', '') and
            _get_indentation(fixed) == _get_indentation(target)
        ):
            self.source[result['line'] - 1] = fixed
        else:
            return []

    def fix_e231(self, result):
        """Add missing whitespace."""
        # Optimize for comma case. This will fix all commas in the full source
        # code in one pass. Don't do this more than once. If it fails the first
        # time, there is no point in trying again.
        if ',' in result['info'] and not self._ws_comma_done:
            self._ws_comma_done = True
            original = ''.join(self.source)
            new = refactor(original, ['ws_comma'])
            if original.strip() != new.strip():
                self.source = [new]
                return range(1, 1 + len(original))

        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column']
        fixed = target[:offset] + ' ' + target[offset:]
        self.source[line_index] = fixed

    def fix_e251(self, result):
        """Remove whitespace around parameter '=' sign."""
        line_index = result['line'] - 1
        target = self.source[line_index]

        # This is necessary since pep8 sometimes reports columns that goes
        # past the end of the physical line. This happens in cases like,
        # foo(bar\n=None)
        c = min(result['column'] - 1,
                len(target) - 1)

        if target[c].strip():
            fixed = target
        else:
            fixed = target[:c].rstrip() + target[c:].lstrip()

        # There could be an escaped newline
        #
        #     def foo(a=\
        #             1)
        if fixed.endswith(('=\\\n', '=\\\r\n', '=\\\r')):
            self.source[line_index] = fixed.rstrip('\n\r \t\\')
            self.source[line_index + 1] = self.source[line_index + 1].lstrip()
            return [line_index + 1, line_index + 2]  # Line indexed at 1

        self.source[result['line'] - 1] = fixed

    def fix_e262(self, result):
        """Fix spacing after comment hash."""
        target = self.source[result['line'] - 1]
        offset = result['column']

        code = target[:offset].rstrip(' \t#')
        comment = target[offset:].lstrip(' \t#')

        fixed = code + ('  # ' + comment if comment.strip() else '\n')

        self.source[result['line'] - 1] = fixed

    def fix_e271(self, result):
        """Fix extraneous whitespace around keywords."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        if is_probably_part_of_multiline(target):
            return []

        fixed = fix_whitespace(target,
                               offset=offset,
                               replacement=' ')

        if fixed == target:
            return []
        else:
            self.source[line_index] = fixed

    def fix_e301(self, result):
        """Add missing blank line."""
        cr = '\n'
        self.source[result['line'] - 1] = cr + self.source[result['line'] - 1]

    def fix_e302(self, result):
        """Add missing 2 blank lines."""
        add_linenum = 2 - int(result['info'].split()[-1])
        cr = '\n' * add_linenum
        self.source[result['line'] - 1] = cr + self.source[result['line'] - 1]

    def fix_e303(self, result):
        """Remove extra blank lines."""
        delete_linenum = int(result['info'].split('(')[1].split(')')[0]) - 2
        delete_linenum = max(1, delete_linenum)

        # We need to count because pep8 reports an offset line number if there
        # are comments.
        cnt = 0
        line = result['line'] - 2
        modified_lines = []
        while cnt < delete_linenum and line >= 0:
            if not self.source[line].strip():
                self.source[line] = ''
                modified_lines.append(1 + line)  # Line indexed at 1
                cnt += 1
            line -= 1

        return modified_lines

    def fix_e304(self, result):
        """Remove blank line following function decorator."""
        line = result['line'] - 2
        if not self.source[line].strip():
            self.source[line] = ''

    def fix_e401(self, result):
        """Put imports on separate lines."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        if not target.lstrip().startswith('import'):
            return []

        indentation = re.split(pattern=r'\bimport\b',
                               string=target, maxsplit=1)[0]
        fixed = (target[:offset].rstrip('\t ,') + '\n' +
                 indentation + 'import ' + target[offset:].lstrip('\t ,'))
        self.source[line_index] = fixed

    def fix_long_line_logically(self, result, logical):
        """Try to make lines fit within --max-line-length characters."""
        if (
            not logical or
            len(logical[2]) == 1 or
            self.source[result['line'] - 1].lstrip().startswith('#')
        ):
            return self.fix_long_line_physically(result)

        start_line_index = logical[0][0]
        end_line_index = logical[1][0]
        logical_lines = logical[2]

        previous_line = get_item(self.source, start_line_index - 1, default='')
        next_line = get_item(self.source, end_line_index + 1, default='')

        single_line = join_logical_line(''.join(logical_lines))

        try:
            fixed = self.fix_long_line(
                target=single_line,
                previous_line=previous_line,
                next_line=next_line,
                original=''.join(logical_lines))
        except (SyntaxError, tokenize.TokenError):
            return self.fix_long_line_physically(result)

        if fixed:
            for line_index in range(start_line_index, end_line_index + 1):
                self.source[line_index] = ''
            self.source[start_line_index] = fixed
            return range(start_line_index + 1, end_line_index + 1)
        else:
            return []

    def fix_long_line_physically(self, result):
        """Try to make lines fit within --max-line-length characters."""
        line_index = result['line'] - 1
        target = self.source[line_index]

        previous_line = get_item(self.source, line_index - 1, default='')
        next_line = get_item(self.source, line_index + 1, default='')

        try:
            fixed = self.fix_long_line(
                target=target,
                previous_line=previous_line,
                next_line=next_line,
                original=target)
        except (SyntaxError, tokenize.TokenError):
            return []

        if fixed:
            self.source[line_index] = fixed
            return [line_index + 1]
        else:
            return []

    def fix_long_line(self, target, previous_line,
                      next_line, original):
        cache_entry = (target, previous_line, next_line)
        if cache_entry in self.long_line_ignore_cache:
            return []

        if target.lstrip().startswith('#'):
            # Wrap commented lines.
            return shorten_comment(
                line=target,
                max_line_length=self.options.max_line_length,
                last_comment=not next_line.lstrip().startswith('#'))

        fixed = get_fixed_long_line(
            target=target,
            previous_line=previous_line,
            original=original,
            indent_word=self.indent_word,
            max_line_length=self.options.max_line_length,
            aggressive=self.options.aggressive,
            experimental=self.options.experimental,
            verbose=self.options.verbose)
        if fixed and not code_almost_equal(original, fixed):
            return fixed
        else:
            self.long_line_ignore_cache.add(cache_entry)
            return None

    def fix_e502(self, result):
        """Remove extraneous escape of newline."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        self.source[line_index] = target.rstrip('\n\r \t\\') + '\n'

    def fix_e701(self, result):
        """Put colon-separated compound statement on separate lines."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        c = result['column']

        # Avoid pep8 bug (https://github.com/jcrocholl/pep8/issues/268).
        if line_index > 0 and '\\' in self.source[line_index - 1]:
            return []

        fixed_source = (target[:c] + '\n' +
                        _get_indentation(target) + self.indent_word +
                        target[c:].lstrip('\n\r \t\\'))
        self.source[result['line'] - 1] = fixed_source
        return [result['line'], result['line'] + 1]

    def fix_e702(self, result, logical):
        """Put semicolon-separated compound statement on separate lines."""
        if not logical:
            return []  # pragma: no cover
        logical_lines = logical[2]

        line_index = result['line'] - 1
        target = self.source[line_index]

        if target.rstrip().endswith('\\'):
            # Normalize '1; \\\n2' into '1; 2'.
            self.source[line_index] = target.rstrip('\n \r\t\\')
            self.source[line_index + 1] = self.source[line_index + 1].lstrip()
            return [line_index + 1, line_index + 2]

        if target.rstrip().endswith(';'):
            self.source[line_index] = target.rstrip('\n \r\t;') + '\n'
            return [line_index + 1]

        offset = result['column'] - 1
        first = target[:offset].rstrip(';').rstrip()
        second = (_get_indentation(logical_lines[0]) +
                  target[offset:].lstrip(';').lstrip())

        self.source[line_index] = first + '\n' + second
        return [line_index + 1]

    def fix_e711(self, result):
        """Fix comparison with None."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        right_offset = offset + 2
        if right_offset >= len(target):
            return []

        left = target[:offset].rstrip()
        center = target[offset:right_offset]
        right = target[right_offset:].lstrip()

        if not right.startswith('None'):
            return []

        if center.strip() == '==':
            new_center = 'is'
        elif center.strip() == '!=':
            new_center = 'is not'
        else:
            return []

        self.source[line_index] = ' '.join([left, new_center, right])

    def fix_e712(self, result):
        """Fix comparison with boolean."""
        line_index = result['line'] - 1
        target = self.source[line_index]
        offset = result['column'] - 1

        # Handle very easy "not" special cases.
        if re.match(r'^\s*if \w+ == False:$', target):
            self.source[line_index] = re.sub(r'if (\w+) == False:',
                                             r'if not \1:', target, count=1)
        elif re.match(r'^\s*if \w+ != True:$', target):
            self.source[line_index] = re.sub(r'if (\w+) != True:',
                                             r'if not \1:', target, count=1)
        else:
            right_offset = offset + 2
            if right_offset >= len(target):
                return []

            left = target[:offset].rstrip()
            center = target[offset:right_offset]
            right = target[right_offset:].lstrip()

            # Handle simple cases only.
            new_right = None
            if center.strip() == '==':
                if re.match(r'\bTrue\b', right):
                    new_right = re.sub(r'\bTrue\b *', '', right, count=1)
            elif center.strip() == '!=':
                if re.match(r'\bFalse\b', right):
                    new_right = re.sub(r'\bFalse\b *', '', right, count=1)

            if new_right is None:
                return []

            if new_right[0].isalnum():
                new_right = ' ' + new_right

            self.source[line_index] = left + new_right

    def fix_w291(self, result):
        """Remove trailing whitespace."""
        fixed_line = self.source[result['line'] - 1].rstrip()
        self.source[result['line'] - 1] = fixed_line + '\n'


def get_fixed_long_line(target, previous_line, original,
                        indent_word='    ', max_line_length=79,
                        aggressive=False, experimental=False, verbose=False):
    """Break up long line and return result.

    Do this by generating multiple reformatted candidates and then
    ranking the candidates to heuristically select the best option.

    """
    indent = _get_indentation(target)
    source = target[len(indent):]
    assert source.lstrip() == source

    # Check for partial multiline.
    tokens = list(generate_tokens(source))

    candidates = shorten_line(
        tokens, source, indent,
        indent_word,
        max_line_length,
        aggressive=aggressive,
        experimental=experimental,
        previous_line=previous_line)

    # Also sort alphabetically as a tie breaker (for determinism).
    candidates = sorted(
        sorted(set(candidates).union([target, original])),
        key=lambda x: line_shortening_rank(x,
                                           indent_word,
                                           max_line_length))

    if verbose >= 4:
        print(('-' * 79 + '\n').join([''] + candidates + ['']),
              file=codecs.getwriter('utf-8')(sys.stderr.buffer
                                             if hasattr(sys.stderr,
                                                        'buffer')
                                             else sys.stderr))

    if candidates:
        return candidates[0]


def join_logical_line(logical_line):
    """Return single line based on logical line input."""
    indentation = _get_indentation(logical_line)

    return indentation + untokenize_without_newlines(
        generate_tokens(logical_line.lstrip())) + '\n'


def untokenize_without_newlines(tokens):
    """Return source code based on tokens."""
    text = ''
    last_row = 0
    last_column = -1

    for t in tokens:
        token_string = t[1]
        (start_row, start_column) = t[2]
        (end_row, end_column) = t[3]

        if start_row > last_row:
            last_column = 0
        if (
            (start_column > last_column or token_string == '\n') and
            not text.endswith(' ')
        ):
            text += ' '

        if token_string != '\n':
            text += token_string

        last_row = end_row
        last_column = end_column

    return text


def _find_logical(source_lines):
    # Make a variable which is the index of all the starts of lines.
    logical_start = []
    logical_end = []
    last_newline = True
    parens = 0
    for t in generate_tokens(''.join(source_lines)):
        if t[0] in [tokenize.COMMENT, tokenize.DEDENT,
                    tokenize.INDENT, tokenize.NL,
                    tokenize.ENDMARKER]:
            continue
        if not parens and t[0] in [tokenize.NEWLINE, tokenize.SEMI]:
            last_newline = True
            logical_end.append((t[3][0] - 1, t[2][1]))
            continue
        if last_newline and not parens:
            logical_start.append((t[2][0] - 1, t[2][1]))
            last_newline = False
        if t[0] == tokenize.OP:
            if t[1] in '([{':
                parens += 1
            elif t[1] in '}])':
                parens -= 1
    return (logical_start, logical_end)


def _get_logical(source_lines, result, logical_start, logical_end):
    """Return the logical line corresponding to the result.

    Assumes input is already E702-clean.

    """
    row = result['line'] - 1
    col = result['column'] - 1
    ls = None
    le = None
    for i in range(0, len(logical_start), 1):
        assert logical_end
        x = logical_end[i]
        if x[0] > row or (x[0] == row and x[1] > col):
            le = x
            ls = logical_start[i]
            break
    if ls is None:
        return None
    original = source_lines[ls[0]:le[0] + 1]
    return ls, le, original


def get_item(items, index, default=None):
    if 0 <= index < len(items):
        return items[index]
    else:
        return default


def reindent(source, indent_size):
    """Reindent all lines."""
    reindenter = Reindenter(source)
    return reindenter.run(indent_size)


def code_almost_equal(a, b):
    """Return True if code is similar.

    Ignore whitespace when comparing specific line.

    """
    split_a = split_and_strip_non_empty_lines(a)
    split_b = split_and_strip_non_empty_lines(b)

    if len(split_a) != len(split_b):
        return False

    for index in range(len(split_a)):
        if ''.join(split_a[index].split()) != ''.join(split_b[index].split()):
            return False

    return True


def split_and_strip_non_empty_lines(text):
    """Return lines split by newline.

    Ignore empty lines.

    """
    return [line.strip() for line in text.splitlines() if line.strip()]


def fix_e265(source, aggressive=False):  # pylint: disable=unused-argument
    """Format block comments."""
    if '#' not in source:
        # Optimization.
        return source

    ignored_line_numbers = multiline_string_lines(
        source,
        include_docstrings=True) | set(commented_out_code_lines(source))

    fixed_lines = []
    sio = io.StringIO(source)
    for (index, line) in enumerate(sio.readlines()):
        line_number = index + 1 # processing.py
        if (
            line.lstrip().startswith('#') and
            line_number not in ignored_line_numbers
        ):
            indentation = _get_indentation(line)
            line = line.lstrip()

            # Normalize beginning if not a shebang.
            if len(line) > 1:
                if (
                    # Leave multiple spaces like '#    ' alone.
                    (line.count('#') > 1 or line[1].isalnum())
                    # Leave stylistic outlined blocks alone.
                    and not line.rstrip().endswith('#')
                ):
                    line = '# ' + line.lstrip('# \t')

            fixed_lines.append(indentation + line)
        else:
            fixed_lines.append(line)

    return ''.join(fixed_lines)


def refactor(source, fixer_names, ignore=None):
    """Return refactored code using lib2to3.

    Skip if ignore string is produced in the refactored code.

    """
    return source # processing.py


def code_to_2to3(select, ignore):
    fixes = set()
    for code, fix in CODE_TO_2TO3.items():
        if code_match(code, select=select, ignore=ignore):
            fixes |= set(fix)
    return fixes


def fix_2to3(source, aggressive=True, select=None, ignore=None):
    """Fix various deprecated code (via lib2to3)."""
    if not aggressive:
        return source

    select = select or []
    ignore = ignore or []

    return refactor(source,
                    code_to_2to3(select=select,
                                 ignore=ignore))


def fix_w602(source, aggressive=True):
    """Fix deprecated form of raising exception."""
    if not aggressive:
        return source

    return refactor(source, ['raise'],
                    ignore='with_traceback')


def find_newline(source):
    """Return type of newline used in source.

    Input is a list of lines.

    """
    assert not isinstance(source, unicode)

    counter = collections.defaultdict(int)
    for line in source:
        if line.endswith(CRLF):
            counter[CRLF] += 1
        elif line.endswith(CR):
            counter[CR] += 1
        elif line.endswith(LF):
            counter[LF] += 1

    return (sorted(counter, key=counter.get, reverse=True) or [LF])[0]


def _get_indentword(source):
    """Return indentation type."""
    indent_word = '    '  # Default in case source has no indentation
    try:
        for t in generate_tokens(source):
            if t[0] == token.INDENT:
                indent_word = t[1]
                break
    except (SyntaxError, tokenize.TokenError):
        pass
    return indent_word


def _get_indentation(line):
    """Return leading whitespace."""
    if line.strip():
        non_whitespace_index = len(line) - len(line.lstrip())
        return line[:non_whitespace_index]
    else:
        return ''


def get_diff_text(old, new, filename):
    """Return text of unified diff between old and new."""
    newline = '\n'
    diff = difflib.unified_diff(
        old, new,
        'original/' + filename,
        'fixed/' + filename,
        lineterm=newline)

    text = ''
    for line in diff:
        text += line

        # Work around missing newline (http://bugs.python.org/issue2142).
        if text and not line.endswith(newline):
            text += newline + r'\ No newline at end of file' + newline

    return text


def _priority_key(pep8_result):
    """Key for sorting PEP8 results.

    Global fixes should be done first. This is important for things like
    indentation.

    """
    priority = [
        # Fix multiline colon-based before semicolon based.
        'e701',
        # Break multiline statements early.
        'e702',
        # Things that make lines longer.
        'e225', 'e231',
        # Remove extraneous whitespace before breaking lines.
        'e201',
        # Shorten whitespace in comment before resorting to wrapping.
        'e262'
    ]
    middle_index = 10000
    lowest_priority = [
        # We need to shorten lines last since the logical fixer can get in a
        # loop, which causes us to exit early.
        'e501'
    ]
    key = pep8_result['id'].lower()
    try:
        return priority.index(key)
    except ValueError:
        try:
            return middle_index + lowest_priority.index(key) + 1
        except ValueError:
            return middle_index


def shorten_line(tokens, source, indentation, indent_word, max_line_length,
                 aggressive=False, experimental=False, previous_line=''):
    """Separate line at OPERATOR.

    Multiple candidates will be yielded.

    """
    for candidate in _shorten_line(tokens=tokens,
                                   source=source,
                                   indentation=indentation,
                                   indent_word=indent_word,
                                   aggressive=aggressive,
                                   previous_line=previous_line):
        yield candidate

    if aggressive:
        for key_token_strings in SHORTEN_OPERATOR_GROUPS:
            shortened = _shorten_line_at_tokens(
                tokens=tokens,
                source=source,
                indentation=indentation,
                indent_word=indent_word,
                key_token_strings=key_token_strings,
                aggressive=aggressive)

            if shortened is not None and shortened != source:
                yield shortened

    if experimental:
        for shortened in _shorten_line_at_tokens_new(
                tokens=tokens,
                source=source,
                indentation=indentation,
                max_line_length=max_line_length):

            yield shortened


def _shorten_line(tokens, source, indentation, indent_word,
                  aggressive=False, previous_line=''):
    """Separate line at OPERATOR.

    The input is expected to be free of newlines except for inside multiline
    strings and at the end.

    Multiple candidates will be yielded.

    """
    for (token_type,
         token_string,
         start_offset,
         end_offset) in token_offsets(tokens):

        if (
            token_type == tokenize.COMMENT and
            not is_probably_part_of_multiline(previous_line) and
            not is_probably_part_of_multiline(source) and
            not source[start_offset + 1:].strip().lower().startswith(
                ('noqa', 'pragma:', 'pylint:'))
        ):
            # Move inline comments to previous line.
            first = source[:start_offset]
            second = source[start_offset:]
            yield (indentation + second.strip() + '\n' +
                   indentation + first.strip() + '\n')
        elif token_type == token.OP and token_string != '=':
            # Don't break on '=' after keyword as this violates PEP 8.

            assert token_type != token.INDENT

            first = source[:end_offset]

            second_indent = indentation
            if first.rstrip().endswith('('):
                second_indent += indent_word
            elif '(' in first:
                second_indent += ' ' * (1 + first.find('('))
            else:
                second_indent += indent_word

            second = (second_indent + source[end_offset:].lstrip())
            if (
                not second.strip() or
                second.lstrip().startswith('#')
            ):
                continue

            # Do not begin a line with a comma
            if second.lstrip().startswith(','):
                continue
            # Do end a line with a dot
            if first.rstrip().endswith('.'):
                continue
            if token_string in '+-*/':
                fixed = first + ' \\' + '\n' + second
            else:
                fixed = first + '\n' + second

            # Only fix if syntax is okay.
            if check_syntax(normalize_multiline(fixed)
                            if aggressive else fixed):
                yield indentation + fixed


# A convenient way to handle tokens.
Token = collections.namedtuple('Token', ['token_type', 'token_string',
                                         'spos', 'epos', 'line'])


class ReformattedLines(object):

    """The reflowed lines of atoms.

    Each part of the line is represented as an "atom." They can be moved
    around when need be to get the optimal formatting.

    """

    ###########################################################################
    # Private Classes

    class _Indent(object):

        """Represent an indentation in the atom stream."""

        def __init__(self, indent_amt):
            self._indent_amt = indent_amt

        def emit(self):
            return ' ' * self._indent_amt

        @property
        def size(self):
            return self._indent_amt

    class _Space(object):

        """Represent a space in the atom stream."""

        def emit(self):
            return ' '

        @property
        def size(self):
            return 1

    class _LineBreak(object):

        """Represent a line break in the atom stream."""

        def emit(self):
            return '\n'

        @property
        def size(self):
            return 0

    def __init__(self, max_line_length):
        self._max_line_length = max_line_length
        self._lines = []
        self._bracket_depth = 0
        self._prev_item = None
        self._prev_prev_item = None

    def __repr__(self):
        return self.emit()

    ###########################################################################
    # Public Methods

    def add(self, obj, indent_amt, break_after_open_bracket):
        if isinstance(obj, Atom):
            self._add_item(obj, indent_amt)
            return

        self._add_container(obj, indent_amt, break_after_open_bracket)

    def add_comment(self, item):
        self._lines.append(self._Space())
        self._lines.append(self._Space())
        self._lines.append(item)

    def add_indent(self, indent_amt):
        self._lines.append(self._Indent(indent_amt))

    def add_line_break(self, indent):
        self._lines.append(self._LineBreak())
        self.add_indent(len(indent))

    def add_line_break_at(self, index, indent_amt):
        self._lines.insert(index, self._LineBreak())
        self._lines.insert(index + 1, self._Indent(indent_amt))

    def add_space_if_needed(self, curr_text, equal=False):
        if (
            not self._lines or isinstance(
                self._lines[-1], (self._LineBreak, self._Indent, self._Space))
        ):
            return

        prev_text = unicode(self._prev_item)
        prev_prev_text = (
            unicode(self._prev_prev_item) if self._prev_prev_item else '')

        if (
            # The previous item was a keyword or identifier and the current
            # item isn't an operator that doesn't require a space.
            ((self._prev_item.is_keyword or self._prev_item.is_string or
              self._prev_item.is_name or self._prev_item.is_number) and
             (curr_text[0] not in '([{.,:}])' or
              (curr_text[0] == '=' and equal))) or

            # Don't place spaces around a '.', unless it's in an 'import'
            # statement.
            ((prev_prev_text != 'from' and prev_text[-1] != '.' and
              curr_text != 'import') and

             # Don't place a space before a colon.
             curr_text[0] != ':' and

             # Don't split up ending brackets by spaces.
             ((prev_text[-1] in '}])' and curr_text[0] not in '.,}])') or

              # Put a space after a colon or comma.
              prev_text[-1] in ':,' or

              # Put space around '=' if asked to.
              (equal and prev_text == '=') or

              # Put spaces around non-unary arithmetic operators.
              ((self._prev_prev_item and
                (prev_text not in '+-' and
                 (self._prev_prev_item.is_name or
                  self._prev_prev_item.is_number or
                  self._prev_prev_item.is_string)) and
                prev_text in ('+', '-', '%', '*', '/', '//', '**')))))
        ):
            self._lines.append(self._Space())

    def previous_item(self):
        """Return the previous non-whitespace item."""
        return self._prev_item

    def fits_on_current_line(self, item_extent):
        return self.current_size() + item_extent <= self._max_line_length

    def current_size(self):
        """The size of the current line minus the indentation."""
        size = 0
        for item in reversed(self._lines):
            size += item.size
            if isinstance(item, self._LineBreak):
                break

        return size

    def line_empty(self):
        return (self._lines and
                isinstance(self._lines[-1],
                           (self._LineBreak, self._Indent)))

    def emit(self):
        string = ''
        for item in self._lines:
            if isinstance(item, self._LineBreak):
                string = string.rstrip()
            string += item.emit()

        return string.rstrip() + '\n'

    ###########################################################################
    # Private Methods

    def _add_item(self, item, indent_amt):
        """Add an item to the line.

        Reflow the line to get the best formatting after the item is
        inserted. The bracket depth indicates if the item is being
        inserted inside of a container or not.

        """
        if self._prev_item and self._prev_item.is_string and item.is_string:
            # Place consecutive string literals on separate lines.
            self._lines.append(self._LineBreak())
            self._lines.append(self._Indent(indent_amt))

        item_text = unicode(item)
        if self._lines and self._bracket_depth:
            # Adding the item into a container.
            self._prevent_default_initializer_splitting(item, indent_amt)

            if item_text in '.,)]}':
                self._split_after_delimiter(item, indent_amt)

        elif self._lines and not self.line_empty():
            # Adding the item outside of a container.
            if self.fits_on_current_line(len(item_text)):
                self._enforce_space(item)

            else:
                # Line break for the new item.
                self._lines.append(self._LineBreak())
                self._lines.append(self._Indent(indent_amt))

        self._lines.append(item)
        self._prev_item, self._prev_prev_item = item, self._prev_item

        if item_text in '([{':
            self._bracket_depth += 1

        elif item_text in '}])':
            self._bracket_depth -= 1
            assert self._bracket_depth >= 0

    def _add_container(self, container, indent_amt, break_after_open_bracket):
        actual_indent = indent_amt + 1

        if (
            unicode(self._prev_item) != '=' and
            not self.line_empty() and
            not self.fits_on_current_line(
                container.size + self._bracket_depth + 2)
        ):

            if unicode(container)[0] == '(' and self._prev_item.is_name:
                # Don't split before the opening bracket of a call.
                break_after_open_bracket = True
                actual_indent = indent_amt + 4
            elif (
                break_after_open_bracket or
                unicode(self._prev_item) not in '([{'
            ):
                # If the container doesn't fit on the current line and the
                # current line isn't empty, place the container on the next
                # line.
                self._lines.append(self._LineBreak())
                self._lines.append(self._Indent(indent_amt))
                break_after_open_bracket = False
        else:
            actual_indent = self.current_size() + 1
            break_after_open_bracket = False

        if isinstance(container, (ListComprehension, IfExpression)):
            actual_indent = indent_amt

        # Increase the continued indentation only if recursing on a
        # container.
        container.reflow(self, ' ' * actual_indent,
                         break_after_open_bracket=break_after_open_bracket)

    def _prevent_default_initializer_splitting(self, item, indent_amt):
        """Prevent splitting between a default initializer.

        When there is a default initializer, it's best to keep it all on
        the same line. It's nicer and more readable, even if it goes
        over the maximum allowable line length. This goes back along the
        current line to determine if we have a default initializer, and,
        if so, to remove extraneous whitespaces and add a line
        break/indent before it if needed.

        """
        if unicode(item) == '=':
            # This is the assignment in the initializer. Just remove spaces for
            # now.
            self._delete_whitespace()
            return

        if (not self._prev_item or not self._prev_prev_item or
                unicode(self._prev_item) != '='):
            return

        self._delete_whitespace()
        prev_prev_index = self._lines.index(self._prev_prev_item)

        if (
            isinstance(self._lines[prev_prev_index - 1], self._Indent) or
            self.fits_on_current_line(item.size + 1)
        ):
            # The default initializer is already the only item on this line.
            # Don't insert a newline here.
            return

        # Replace the space with a newline/indent combo.
        if isinstance(self._lines[prev_prev_index - 1], self._Space):
            del self._lines[prev_prev_index - 1]

        self.add_line_break_at(self._lines.index(self._prev_prev_item),
                               indent_amt)

    def _split_after_delimiter(self, item, indent_amt):
        """Split the line only after a delimiter."""
        self._delete_whitespace()

        if self.fits_on_current_line(item.size):
            return

        last_space = None
        for item in reversed(self._lines):
            if (
                last_space and
                (not isinstance(item, Atom) or not item.is_colon)
            ):
                break
            else:
                last_space = None
            if isinstance(item, self._Space):
                last_space = item
            if isinstance(item, (self._LineBreak, self._Indent)):
                return

        if not last_space:
            return

        self.add_line_break_at(self._lines.index(last_space), indent_amt)

    def _enforce_space(self, item):
        """Enforce a space in certain situations.

        There are cases where we will want a space where normally we
        wouldn't put one. This just enforces the addition of a space.

        """
        if isinstance(self._lines[-1],
                      (self._Space, self._LineBreak, self._Indent)):
            return

        if not self._prev_item:
            return

        item_text = unicode(item)
        prev_text = unicode(self._prev_item)

        # Prefer a space around a '.' in an import statement, and between the
        # 'import' and '('.
        if (
            (item_text == '.' and prev_text == 'from') or
            (item_text == 'import' and prev_text == '.') or
            (item_text == '(' and prev_text == 'import')
        ):
            self._lines.append(self._Space())

    def _delete_whitespace(self):
        """Delete all whitespace from the end of the line."""
        while isinstance(self._lines[-1], (self._Space, self._LineBreak,
                                           self._Indent)):
            del self._lines[-1]


class Atom(object):

    """The smallest unbreakable unit that can be reflowed."""

    def __init__(self, atom):
        self._atom = atom

    def __repr__(self):
        return self._atom.token_string

    def __len__(self):
        return self.size

    def reflow(
        self, reflowed_lines, continued_indent, extent,
        break_after_open_bracket=False,
        is_list_comp_or_if_expr=False,
        next_is_dot=False
    ):
        if self._atom.token_type == tokenize.COMMENT:
            reflowed_lines.add_comment(self)
            return

        total_size = extent if extent else self.size

        if self._atom.token_string not in ',:([{}])':
            # Some atoms will need an extra 1-sized space token after them.
            total_size += 1

        prev_item = reflowed_lines.previous_item()
        if (
            not is_list_comp_or_if_expr and
            not reflowed_lines.fits_on_current_line(total_size) and
            not (next_is_dot and
                 reflowed_lines.fits_on_current_line(self.size + 1)) and
            not reflowed_lines.line_empty() and
            not self.is_colon and
            not (prev_item and prev_item.is_name and
                 unicode(self) == '(')
        ):
            # Start a new line if there is already something on the line and
            # adding this atom would make it go over the max line length.
            reflowed_lines.add_line_break(continued_indent)
        else:
            reflowed_lines.add_space_if_needed(unicode(self))

        reflowed_lines.add(self, len(continued_indent),
                           break_after_open_bracket)

    def emit(self):
        return self.__repr__()

    @property
    def is_keyword(self):
        return keyword.iskeyword(self._atom.token_string)

    @property
    def is_string(self):
        return self._atom.token_type == tokenize.STRING

    @property
    def is_name(self):
        return self._atom.token_type == tokenize.NAME

    @property
    def is_number(self):
        return self._atom.token_type == tokenize.NUMBER

    @property
    def is_comma(self):
        return self._atom.token_string == ','

    @property
    def is_colon(self):
        return self._atom.token_string == ':'

    @property
    def size(self):
        return len(self._atom.token_string)


class Container(object):

    """Base class for all container types."""

    def __init__(self, items):
        self._items = items

    def __repr__(self):
        string = ''
        last_was_keyword = False

        for item in self._items:
            if item.is_comma:
                string += ', '
            elif item.is_colon:
                string += ': '
            else:
                item_string = unicode(item)
                if (
                    string and
                    (last_was_keyword or
                     (not string.endswith(tuple('([{,.:}]) ')) and
                      not item_string.startswith(tuple('([{,.:}])'))))
                ):
                    string += ' '
                string += item_string

            last_was_keyword = item.is_keyword
        return string

    def __iter__(self):
        for element in self._items:
            yield element

    def __getitem__(self, idx):
        return self._items[idx]

    def reflow(self, reflowed_lines, continued_indent,
               break_after_open_bracket=False):
        last_was_container = False
        for (index, item) in enumerate(self._items):
            next_item = get_item(self._items, index + 1)

            if isinstance(item, Atom):
                is_list_comp_or_if_expr = (
                    isinstance(self, (ListComprehension, IfExpression)))
                item.reflow(reflowed_lines, continued_indent,
                            self._get_extent(index),
                            is_list_comp_or_if_expr=is_list_comp_or_if_expr,
                            next_is_dot=(next_item and
                                         unicode(next_item) == '.'))
                if last_was_container and item.is_comma:
                    reflowed_lines.add_line_break(continued_indent)
                last_was_container = False
            else:  # isinstance(item, Container)
                reflowed_lines.add(item, len(continued_indent),
                                   break_after_open_bracket)
                last_was_container = not isinstance(item, (ListComprehension,
                                                           IfExpression))

            if (
                break_after_open_bracket and index == 0 and
                # Prefer to keep empty containers together instead of
                # separating them.
                unicode(item) == self.open_bracket and
                (not next_item or unicode(next_item) != self.close_bracket) and
                (len(self._items) != 3 or not isinstance(next_item, Atom))
            ):
                reflowed_lines.add_line_break(continued_indent)
                break_after_open_bracket = False
            else:
                next_next_item = get_item(self._items, index + 2)
                if (
                    unicode(item) not in ['.', '%', 'in'] and
                    next_item and not isinstance(next_item, Container) and
                    unicode(next_item) != ':' and
                    next_next_item and (not isinstance(next_next_item, Atom) or
                                        unicode(next_item) == 'not') and
                    not reflowed_lines.line_empty() and
                    not reflowed_lines.fits_on_current_line(
                        self._get_extent(index + 1) + 2)
                ):
                    reflowed_lines.add_line_break(continued_indent)

    def _get_extent(self, index):
        """The extent of the full element.

        E.g., the length of a function call or keyword.

        """
        extent = 0
        prev_item = get_item(self._items, index - 1)
        seen_dot = prev_item and unicode(prev_item) == '.'
        while index < len(self._items):
            item = get_item(self._items, index)
            index += 1

            if isinstance(item, (ListComprehension, IfExpression)):
                break

            if isinstance(item, Container):
                if prev_item and prev_item.is_name:
                    if seen_dot:
                        extent += 1
                    else:
                        extent += item.size

                    prev_item = item
                    continue
            elif (unicode(item) not in ['.', '=', ':', 'not'] and
                  not item.is_name and not item.is_string):
                break

            if unicode(item) == '.':
                seen_dot = True

            extent += item.size
            prev_item = item

        return extent

    @property
    def is_string(self):
        return False

    @property
    def size(self):
        return len(self.__repr__())

    @property
    def is_keyword(self):
        return False

    @property
    def is_name(self):
        return False

    @property
    def is_comma(self):
        return False

    @property
    def is_colon(self):
        return False

    @property
    def open_bracket(self):
        return None

    @property
    def close_bracket(self):
        return None


class Tuple(Container):

    """A high-level representation of a tuple."""

    @property
    def open_bracket(self):
        return '('

    @property
    def close_bracket(self):
        return ')'


class List(Container):

    """A high-level representation of a list."""

    @property
    def open_bracket(self):
        return '['

    @property
    def close_bracket(self):
        return ']'


class DictOrSet(Container):

    """A high-level representation of a dictionary or set."""

    @property
    def open_bracket(self):
        return '{'

    @property
    def close_bracket(self):
        return '}'


class ListComprehension(Container):

    """A high-level representation of a list comprehension."""

    @property
    def size(self):
        length = 0
        for item in self._items:
            if isinstance(item, IfExpression):
                break
            length += item.size
        return length


class IfExpression(Container):

    """A high-level representation of an if-expression."""


def _parse_container(tokens, index, for_or_if=None):
    """Parse a high-level container, such as a list, tuple, etc."""

    # Store the opening bracket.
    items = [Atom(Token(*tokens[index]))]
    index += 1

    num_tokens = len(tokens)
    while index < num_tokens:
        tok = Token(*tokens[index])

        if tok.token_string in ',)]}':
            # First check if we're at the end of a list comprehension or
            # if-expression. Don't add the ending token as part of the list
            # comprehension or if-expression, because they aren't part of those
            # constructs.
            if for_or_if == 'for':
                return (ListComprehension(items), index - 1)

            elif for_or_if == 'if':
                return (IfExpression(items), index - 1)

            # We've reached the end of a container.
            items.append(Atom(tok))

            # If not, then we are at the end of a container.
            if tok.token_string == ')':
                # The end of a tuple.
                return (Tuple(items), index)

            elif tok.token_string == ']':
                # The end of a list.
                return (List(items), index)

            elif tok.token_string == '}':
                # The end of a dictionary or set.
                return (DictOrSet(items), index)

        elif tok.token_string in '([{':
            # A sub-container is being defined.
            (container, index) = _parse_container(tokens, index)
            items.append(container)

        elif tok.token_string == 'for':
            (container, index) = _parse_container(tokens, index, 'for')
            items.append(container)

        elif tok.token_string == 'if':
            (container, index) = _parse_container(tokens, index, 'if')
            items.append(container)

        else:
            items.append(Atom(tok))

        index += 1

    return (None, None)


def _parse_tokens(tokens):
    """Parse the tokens.

    This converts the tokens into a form where we can manipulate them
    more easily.

    """

    index = 0
    parsed_tokens = []

    num_tokens = len(tokens)
    while index < num_tokens:
        tok = Token(*tokens[index])

        assert tok.token_type != token.INDENT
        if tok.token_type == tokenize.NEWLINE:
            # There's only one newline and it's at the end.
            break

        if tok.token_string in '([{':
            (container, index) = _parse_container(tokens, index)
            if not container:
                return None
            parsed_tokens.append(container)
        else:
            parsed_tokens.append(Atom(tok))

        index += 1

    return parsed_tokens


def _reflow_lines(parsed_tokens, indentation, max_line_length,
                  start_on_prefix_line):
    """Reflow the lines so that it looks nice."""

    if unicode(parsed_tokens[0]) == 'def':
        # A function definition gets indented a bit more.
        continued_indent = indentation + ' ' * 2 * DEFAULT_INDENT_SIZE
    else:
        continued_indent = indentation + ' ' * DEFAULT_INDENT_SIZE

    break_after_open_bracket = not start_on_prefix_line

    lines = ReformattedLines(max_line_length)
    lines.add_indent(len(indentation.lstrip('\r\n')))

    if not start_on_prefix_line:
        # If splitting after the opening bracket will cause the first element
        # to be aligned weirdly, don't try it.
        first_token = get_item(parsed_tokens, 0)
        second_token = get_item(parsed_tokens, 1)

        if (
            first_token and second_token and
            unicode(second_token)[0] == '(' and
            len(indentation) + len(first_token) + 1 == len(continued_indent)
        ):
            return None

    for item in parsed_tokens:
        lines.add_space_if_needed(unicode(item), equal=True)

        save_continued_indent = continued_indent
        if start_on_prefix_line and isinstance(item, Container):
            start_on_prefix_line = False
            continued_indent = ' ' * (lines.current_size() + 1)

        item.reflow(lines, continued_indent, break_after_open_bracket)
        continued_indent = save_continued_indent

    return lines.emit()


def _shorten_line_at_tokens_new(tokens, source, indentation,
                                max_line_length):
    """Shorten the line taking its length into account.

    The input is expected to be free of newlines except for inside
    multiline strings and at the end.

    """
    # Yield the original source so to see if it's a better choice than the
    # shortened candidate lines we generate here.
    yield indentation + source

    parsed_tokens = _parse_tokens(tokens)

    if parsed_tokens:
        # Perform two reflows. The first one starts on the same line as the
        # prefix. The second starts on the line after the prefix.
        fixed = _reflow_lines(parsed_tokens, indentation, max_line_length,
                              start_on_prefix_line=True)
        if fixed and check_syntax(normalize_multiline(fixed.lstrip())):
            yield fixed

        fixed = _reflow_lines(parsed_tokens, indentation, max_line_length,
                              start_on_prefix_line=False)
        if fixed and check_syntax(normalize_multiline(fixed.lstrip())):
            yield fixed


def _shorten_line_at_tokens(tokens, source, indentation, indent_word,
                            key_token_strings, aggressive):
    """Separate line by breaking at tokens in key_token_strings.

    The input is expected to be free of newlines except for inside
    multiline strings and at the end.

    """
    offsets = []
    for (index, _t) in enumerate(token_offsets(tokens)):
        (token_type,
         token_string,
         start_offset,
         end_offset) = _t

        assert token_type != token.INDENT

        if token_string in key_token_strings:
            # Do not break in containers with zero or one items.
            unwanted_next_token = {
                '(': ')',
                '[': ']',
                '{': '}'}.get(token_string)
            if unwanted_next_token:
                if (
                    get_item(tokens,
                             index + 1,
                             default=[None, None])[1] == unwanted_next_token or
                    get_item(tokens,
                             index + 2,
                             default=[None, None])[1] == unwanted_next_token
                ):
                    continue

            if (
                index > 2 and token_string == '(' and
                tokens[index - 1][1] in ',(%['
            ):
                # Don't split after a tuple start, or before a tuple start if
                # the tuple is in a list.
                continue

            if end_offset < len(source) - 1:
                # Don't split right before newline.
                offsets.append(end_offset)
        else:
            # Break at adjacent strings. These were probably meant to be on
            # separate lines in the first place.
            previous_token = get_item(tokens, index - 1)
            if (
                token_type == tokenize.STRING and
                previous_token and previous_token[0] == tokenize.STRING
            ):
                offsets.append(start_offset)

    current_indent = None
    fixed = None
    for line in split_at_offsets(source, offsets):
        if fixed:
            fixed += '\n' + current_indent + line

            for symbol in '([{':
                if line.endswith(symbol):
                    current_indent += indent_word
        else:
            # First line.
            fixed = line
            assert not current_indent
            current_indent = indent_word

    assert fixed is not None

    if check_syntax(normalize_multiline(fixed)
                    if aggressive > 1 else fixed):
        return indentation + fixed
    else:
        return None


def token_offsets(tokens):
    """Yield tokens and offsets."""
    end_offset = 0
    previous_end_row = 0
    previous_end_column = 0
    for t in tokens:
        token_type = t[0]
        token_string = t[1]
        (start_row, start_column) = t[2]
        (end_row, end_column) = t[3]

        # Account for the whitespace between tokens.
        end_offset += start_column
        if previous_end_row == start_row:
            end_offset -= previous_end_column

        # Record the start offset of the token.
        start_offset = end_offset

        # Account for the length of the token itself.
        end_offset += len(token_string)

        yield (token_type,
               token_string,
               start_offset,
               end_offset)

        previous_end_row = end_row
        previous_end_column = end_column


def normalize_multiline(line):
    """Normalize multiline-related code that will cause syntax error.

    This is for purposes of checking syntax.

    """
    if line.startswith('def ') and line.rstrip().endswith(':'):
        return line + ' pass'
    elif line.startswith('return '):
        return 'def _(): ' + line
    elif line.startswith('@'):
        return line + 'def _(): pass'
    elif line.startswith('class '):
        return line + ' pass'
    else:
        return line


def fix_whitespace(line, offset, replacement):
    """Replace whitespace at offset and return fixed line."""
    # Replace escaped newlines too
    left = line[:offset].rstrip('\n\r \t\\')
    right = line[offset:].lstrip('\n\r \t\\')
    if right.startswith('#'):
        return line
    else:
        return left + replacement + right


def _execute_pep8(pep8_options, source):
    """Execute pep8 via python method calls."""
    class QuietReport(pep8.BaseReport):

        """Version of checker that does not print."""

        def __init__(self, options):
            super(QuietReport, self).__init__(options)
            self.__full_error_results = []

        def error(self, line_number, offset, text, _):
            """Collect errors."""
            code = super(QuietReport, self).error(line_number, offset, text, _)
            if code:
                self.__full_error_results.append(
                    {'id': code,
                     'line': line_number,
                     'column': offset + 1,
                     'info': text})

        def full_error_results(self):
            """Return error results in detail.

            Results are in the form of a list of dictionaries. Each
            dictionary contains 'id', 'line', 'column', and 'info'.

            """
            return self.__full_error_results

    checker = pep8.Checker('', lines=source,
                           reporter=QuietReport, **pep8_options)
    checker.check_all()
    return checker.report.full_error_results()


def _remove_leading_and_normalize(line):
    return line.lstrip().rstrip(CR + LF) + '\n'


class Reindenter(object):

    """Reindents badly-indented code to uniformly use four-space indentation.

    Released to the public domain, by Tim Peters, 03 October 2000.

    """

    def __init__(self, input_text):
        sio = io.StringIO(input_text)
        source_lines = sio.readlines()

        self.string_content_line_numbers = multiline_string_lines(input_text)

        # File lines, rstripped & tab-expanded. Dummy at start is so
        # that we can use tokenize's 1-based line numbering easily.
        # Note that a line is all-blank iff it is a newline.
        self.lines = []
        for index, line in enumerate(source_lines):
            line_number = index + 1 # processing.py
            # Do not modify if inside a multiline string.
            if line_number in self.string_content_line_numbers:
                self.lines.append(line)
            else:
                # Only expand leading tabs.
                self.lines.append(_get_indentation(line).expandtabs() +
                                  _remove_leading_and_normalize(line))

        self.lines.insert(0, None)
        self.index = 1  # index into self.lines of next line
        self.input_text = input_text

    def run(self, indent_size=DEFAULT_INDENT_SIZE):
        """Fix indentation and return modified line numbers.

        Line numbers are indexed at 1.

        """
        if indent_size < 1:
            return self.input_text

        try:
            stats = _reindent_stats(tokenize.generate_tokens(self.getline))
        except (SyntaxError, tokenize.TokenError):
            return self.input_text
        # Remove trailing empty lines.
        lines = self.lines
        while lines and lines[-1] == '\n':
            lines.pop()
        # Sentinel.
        stats.append((len(lines), 0))
        # Map count of leading spaces to # we want.
        have2want = {}
        # Program after transformation.
        after = []
        # Copy over initial empty lines -- there's nothing to do until
        # we see a line with *something* on it.
        i = stats[0][0]
        after.extend(lines[1:i])
        for i in range(len(stats) - 1):
            thisstmt, thislevel = stats[i]
            nextstmt = stats[i + 1][0]
            have = _leading_space_count(lines[thisstmt])
            want = thislevel * indent_size
            if want < 0:
                # A comment line.
                if have:
                    # An indented comment line. If we saw the same
                    # indentation before, reuse what it most recently
                    # mapped to.
                    want = have2want.get(have, -1)
                    if want < 0:
                        # Then it probably belongs to the next real stmt.
                        for j in range(i + 1, len(stats) - 1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                if have == _leading_space_count(lines[jline]):
                                    want = jlevel * indent_size
                                break
                    if want < 0:            # Maybe it's a hanging
                                            # comment like this one,
                        # in which case we should shift it like its base
                        # line got shifted.
                        for j in range(i - 1, -1, -1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                want = (have + _leading_space_count(
                                        after[jline - 1]) -
                                        _leading_space_count(lines[jline]))
                                break
                    if want < 0:
                        # Still no luck -- leave it alone.
                        want = have
                else:
                    want = 0
            assert want >= 0
            have2want[have] = want
            diff = want - have
            if diff == 0 or have == 0:
                after.extend(lines[thisstmt:nextstmt])
            else:
                for index, line in enumerate(lines[thisstmt:nextstmt]):
                    line_number = index + thisstmt
                    if line_number in self.string_content_line_numbers:
                        after.append(line)
                    elif diff > 0:
                        if line == '\n':
                            after.append(line)
                        else:
                            after.append(' ' * diff + line)
                    else:
                        remove = min(_leading_space_count(line), -diff)
                        after.append(line[remove:])

        return ''.join(after)

    def getline(self):
        """Line-getter for tokenize."""
        if self.index >= len(self.lines):
            line = ''
        else:
            line = self.lines[self.index]
            self.index += 1
        return line


def _reindent_stats(tokens):
    """Return list of (lineno, indentlevel) pairs.

    One for each stmt and comment line. indentlevel is -1 for comment lines, as
    a signal that tokenize doesn't know what to do about them; indeed, they're
    our headache!

    """
    find_stmt = 1  # Next token begins a fresh stmt?
    level = 0  # Current indent level.
    stats = []

    for t in tokens:
        token_type = t[0]
        sline = t[2][0]
        line = t[4]

        if token_type == tokenize.NEWLINE:
            # A program statement, or ENDMARKER, will eventually follow,
            # after some (possibly empty) run of tokens of the form
            #     (NL | COMMENT)* (INDENT | DEDENT+)?
            find_stmt = 1

        elif token_type == tokenize.INDENT:
            find_stmt = 1
            level += 1

        elif token_type == tokenize.DEDENT:
            find_stmt = 1
            level -= 1

        elif token_type == tokenize.COMMENT:
            if find_stmt:
                stats.append((sline, -1))
                # But we're still looking for a new stmt, so leave
                # find_stmt alone.

        elif token_type == tokenize.NL:
            pass

        elif find_stmt:
            # This is the first "real token" following a NEWLINE, so it
            # must be the first token of the next program statement, or an
            # ENDMARKER.
            find_stmt = 0
            if line:   # Not endmarker.
                stats.append((sline, level))

    return stats


def _leading_space_count(line):
    """Return number of leading spaces in line."""
    i = 0
    while i < len(line) and line[i] == ' ':
        i += 1
    return i


def refactor_with_2to3(source_text, fixer_names):
    """Use lib2to3 to refactor the source.

    Return the refactored source code.

    """
    from lib2to3.refactor import RefactoringTool
    fixers = ['lib2to3.fixes.fix_' + name for name in fixer_names]
    tool = RefactoringTool(fixer_names=fixers, explicit=fixers)

    from lib2to3.pgen2 import tokenize as lib2to3_tokenize
    try:
        return unicode(tool.refactor_string(source_text, name=''))
    except lib2to3_tokenize.TokenError:
        return source_text


def check_syntax(code):
    """Return True if syntax is okay."""
    try:
        return compile(code, '<string>', 'exec')
    except (SyntaxError, TypeError, UnicodeDecodeError):
        return False


def filter_results(source, results, aggressive):
    """Filter out spurious reports from pep8.

    If aggressive is True, we allow possibly unsafe fixes (E711, E712).

    """
    non_docstring_string_line_numbers = multiline_string_lines(
        source, include_docstrings=False)
    all_string_line_numbers = multiline_string_lines(
        source, include_docstrings=True)

    commented_out_code_line_numbers = commented_out_code_lines(source)

    for r in results:
        issue_id = r['id'].lower()

        if r['line'] in non_docstring_string_line_numbers:
            if issue_id.startswith(('e1', 'e501', 'w191')):
                continue

        if r['line'] in all_string_line_numbers:
            if issue_id in ['e501']:
                continue

        # We must offset by 1 for lines that contain the trailing contents of
        # multiline strings.
        if not aggressive and (r['line'] + 1) in all_string_line_numbers:
            # Do not modify multiline strings in non-aggressive mode. Remove
            # trailing whitespace could break doctests.
            if issue_id.startswith(('w29', 'w39')):
                continue

        if aggressive <= 0:
            if issue_id.startswith(('e711', 'w6')):
                continue

        if aggressive <= 1:
            if issue_id.startswith(('e712', )):
                continue

        if r['line'] in commented_out_code_line_numbers:
            if issue_id.startswith(('e26', 'e501')):
                continue

        yield r


def multiline_string_lines(source, include_docstrings=False):
    """Return line numbers that are within multiline strings.

    The line numbers are indexed at 1.

    Docstrings are ignored.

    """
    line_numbers = set()
    previous_token_type = ''
    try:
        for t in generate_tokens(source):
            token_type = t[0]
            start_row = t[2][0]
            end_row = t[3][0]

            if token_type == tokenize.STRING and start_row != end_row:
                if (
                    include_docstrings or
                    previous_token_type != tokenize.INDENT
                ):
                    # We increment by one since we want the contents of the
                    # string.
                    line_numbers |= set(range(1 + start_row, 1 + end_row))

            previous_token_type = token_type
    except (SyntaxError, tokenize.TokenError):
        pass

    return line_numbers


def commented_out_code_lines(source):
    """Return line numbers of comments that are likely code.

    Commented-out code is bad practice, but modifying it just adds even more
    clutter.

    """
    line_numbers = []
    try:
        for t in generate_tokens(source):
            token_type = t[0]
            token_string = t[1]
            start_row = t[2][0]
            line = t[4]

            # Ignore inline comments.
            if not line.lstrip().startswith('#'):
                continue

            if token_type == tokenize.COMMENT:
                stripped_line = token_string.lstrip('#').strip()
                if (
                    ' ' in stripped_line and
                    '#' not in stripped_line and
                    check_syntax(stripped_line)
                ):
                    line_numbers.append(start_row)
    except (SyntaxError, tokenize.TokenError):
        pass

    return line_numbers


def shorten_comment(line, max_line_length, last_comment=False):
    """Return trimmed or split long comment line.

    If there are no comments immediately following it, do a text wrap.
    Doing this wrapping on all comments in general would lead to jagged
    comment text.

    """
    assert len(line) > max_line_length
    line = line.rstrip()

    # PEP 8 recommends 72 characters for comment text.
    indentation = _get_indentation(line) + '# '
    max_line_length = min(max_line_length,
                          len(indentation) + 72)

    MIN_CHARACTER_REPEAT = 5
    if (
        len(line) - len(line.rstrip(line[-1])) >= MIN_CHARACTER_REPEAT and
        not line[-1].isalnum()
    ):
        # Trim comments that end with things like ---------
        return line[:max_line_length] + '\n'
    elif last_comment and re.match(r'\s*#+\s*\w+', line):
        import textwrap
        split_lines = textwrap.wrap(line.lstrip(' \t#'),
                                    initial_indent=indentation,
                                    subsequent_indent=indentation,
                                    width=max_line_length,
                                    break_long_words=False,
                                    break_on_hyphens=False)
        return '\n'.join(split_lines) + '\n'
    else:
        return line + '\n'


def normalize_line_endings(lines, newline):
    """Return fixed line endings.

    All lines will be modified to use the most common line ending.

    """
    return [line.rstrip('\n\r') + newline for line in lines]


def mutual_startswith(a, b):
    return b.startswith(a) or a.startswith(b)


def code_match(code, select, ignore):
    if ignore:
        assert not isinstance(ignore, unicode)
        for ignored_code in [c.strip() for c in ignore]:
            if mutual_startswith(code.lower(), ignored_code.lower()):
                return False

    if select:
        assert not isinstance(select, unicode)
        for selected_code in [c.strip() for c in select]:
            if mutual_startswith(code.lower(), selected_code.lower()):
                return True
        return False

    return True


def fix_code(source, options=None):
    """Return fixed source code."""
    if not options:
        options = parse_args([''])

    if not isinstance(source, unicode):
        source = source.decode(locale.getpreferredencoding(False))

    sio = io.StringIO(source)
    return fix_lines(sio.readlines(), options=options)


def fix_lines(source_lines, options, filename=''):
    """Return fixed source code."""
    # Transform everything to line feed. Then change them back to original
    # before returning fixed source code.
    original_newline = find_newline(source_lines)
    tmp_source = ''.join(normalize_line_endings(source_lines, '\n'))

    # Keep a history to break out of cycles.
    previous_hashes = set()

    if options.line_range:
        fixed_source = apply_local_fixes(tmp_source, options)
    else:
        # Apply global fixes only once (for efficiency).
        fixed_source = apply_global_fixes(tmp_source, options)

    passes = 0
    long_line_ignore_cache = set()
    while hash(fixed_source) not in previous_hashes:
        if options.pep8_passes >= 0 and passes > options.pep8_passes:
            break
        passes += 1

        previous_hashes.add(hash(fixed_source))

        tmp_source = copy.copy(fixed_source)

        fix = FixPEP8(
            filename,
            options,
            contents=tmp_source,
            long_line_ignore_cache=long_line_ignore_cache)

        fixed_source = fix.fix()

    sio = io.StringIO(fixed_source)
    return ''.join(normalize_line_endings(sio.readlines(), original_newline))


def fix_file(filename, options=None, output=None):
    if not options:
        options = parse_args([filename])

    original_source = readlines_from_file(filename)

    fixed_source = original_source

    if options.in_place or output:
        encoding = detect_encoding(filename)

    if output:
        output = codecs.getwriter(encoding)(output.buffer
                                            if hasattr(output, 'buffer')
                                            else output)

        output = LineEndingWrapper(output)

    fixed_source = fix_lines(fixed_source, options, filename=filename)

    if options.diff:
        new = io.StringIO(fixed_source)
        new = new.readlines()
        diff = get_diff_text(original_source, new, filename)
        if output:
            output.write(diff)
            output.flush()
        else:
            return diff
    elif options.in_place:
        fp = open_with_encoding(filename, encoding=encoding,
                                mode='w')
        fp.write(fixed_source)
        fp.close()
    else:
        if output:
            output.write(fixed_source)
            output.flush()
        else:
            return fixed_source


def global_fixes():
    """Yield multiple (code, function) tuples."""
    for function in globals().values():
        if inspect.isfunction(function):
            arguments = inspect.getargspec(function)[0]
            if arguments[:1] != ['source']:
                continue

            code = extract_code_from_function(function)
            if code:
                yield (code, function)


def apply_global_fixes(source, options, where='global'):
    """Run global fixes on source code.

    These are fixes that only need be done once (unlike those in
    FixPEP8, which are dependent on pep8).

    """
    if code_match('E101', select=options.select, ignore=options.ignore):
        source = reindent(source,
                          indent_size=options.indent_size)

    for (code, function) in global_fixes():
        if code_match(code, select=options.select, ignore=options.ignore):
            if options.verbose:
                print('--->  Applying {0} fix for {1}'.format(where,
                                                              code.upper()),
                      file=sys.stderr)
            source = function(source,
                              aggressive=options.aggressive)

    source = fix_2to3(source,
                      aggressive=options.aggressive,
                      select=options.select,
                      ignore=options.ignore)

    return source


def apply_local_fixes(source, options):
    """Ananologus to apply_global_fixes, but runs only those which makes sense
    for the given line_range.

    Do as much as we can without breaking code.

    """
    def find_ge(a, x):
        """Find leftmost item greater than or equal to x."""
        i = bisect.bisect_left(a, x)
        if i != len(a):
            return i, a[i]
        return len(a) - 1, a[-1]

    def find_le(a, x):
        """Find rightmost value less than or equal to x."""
        i = bisect.bisect_right(a, x)
        if i:
            return i - 1, a[i - 1]
        return 0, a[0]

    def local_fix(source, start_log, end_log,
                  start_lines, end_lines, indents, last_line):
        """apply_global_fixes to the source between start_log and end_log.

        The subsource must be the correct syntax of a complete python program
        (but all lines may share an indentation). The subsource's shared indent
        is removed, fixes are applied and the indent prepended back. Taking
        care to not reindent strings.

        last_line is the strict cut off (options.line_range[1]), so that
        lines after last_line are not modified.

        """
        if end_log < start_log:
            return source

        ind = indents[start_log]
        indent = _get_indentation(source[start_lines[start_log]])

        sl = slice(start_lines[start_log], end_lines[end_log] + 1)

        subsource = source[sl]
        # Remove indent from subsource.
        if ind:
            for line_no in start_lines[start_log:end_log + 1]:
                pos = line_no - start_lines[start_log]
                subsource[pos] = subsource[pos][ind:]

        # Fix indentation of subsource.
        fixed_subsource = apply_global_fixes(''.join(subsource),
                                             options,
                                             where='local')
        fixed_subsource = fixed_subsource.splitlines(True)

        # Add back indent for non multi-line strings lines.
        msl = multiline_string_lines(''.join(fixed_subsource),
                                     include_docstrings=False)
        for i, line in enumerate(fixed_subsource):
            if not i + 1 in msl:
                fixed_subsource[i] = indent + line if line != '\n' else line

        # We make a special case to look at the final line, if it's a multiline
        # *and* the cut off is somewhere inside it, we take the fixed
        # subset up until last_line, this assumes that the number of lines
        # does not change in this multiline line.
        changed_lines = len(fixed_subsource)
        if (start_lines[end_log] != end_lines[end_log]
                and end_lines[end_log] > last_line):
            after_end = end_lines[end_log] - last_line
            fixed_subsource = (fixed_subsource[:-after_end] +
                               source[sl][-after_end:])
            changed_lines -= after_end

            options.line_range[1] = (options.line_range[0] +
                                     changed_lines - 1)

        return (source[:start_lines[start_log]] +
                fixed_subsource +
                source[end_lines[end_log] + 1:])

    def is_continued_stmt(line,
                          continued_stmts=frozenset(['else', 'elif',
                                                     'finally', 'except'])):
        return re.split('[ :]', line.strip(), 1)[0] in continued_stmts

    assert options.line_range
    start, end = options.line_range
    start -= 1
    end -= 1
    last_line = end  # We shouldn't modify lines after this cut-off.

    logical = _find_logical(source)

    if not logical[0]:
        # Just blank lines, this should imply that it will become '\n' ?
        return apply_global_fixes(source, options)

    start_lines, indents = zip(*logical[0])
    end_lines, _ = zip(*logical[1])

    source = source.splitlines(True)

    start_log, start = find_ge(start_lines, start)
    end_log, end = find_le(start_lines, end)

    # Look behind one line, if it's indented less than current indent
    # then we can move to this previous line knowing that its
    # indentation level will not be changed.
    if (start_log > 0
            and indents[start_log - 1] < indents[start_log]
            and not is_continued_stmt(source[start_log - 1])):
        start_log -= 1
        start = start_lines[start_log]

    while start < end:

        if is_continued_stmt(source[start]):
            start_log += 1
            start = start_lines[start_log]
            continue

        ind = indents[start_log]
        for t in itertools.takewhile(lambda t: t[1][1] >= ind,
                                     enumerate(logical[0][start_log:])):
            n_log, n = start_log + t[0], t[1][0]
        # start shares indent up to n.

        if n <= end:
            source = local_fix(source, start_log, n_log,
                               start_lines, end_lines,
                               indents, last_line)
            start_log = n_log if n == end else n_log + 1
            start = start_lines[start_log]
            continue

        else:
            # Look at the line after end and see if allows us to reindent.
            after_end_log, after_end = find_ge(start_lines, end + 1)

            if indents[after_end_log] > indents[start_log]:
                start_log, start = find_ge(start_lines, start + 1)
                continue

            if (indents[after_end_log] == indents[start_log]
                    and is_continued_stmt(source[after_end])):
                # find n, the beginning of the last continued statement
                # Apply fix to previous block if there is one.
                only_block = True
                for n, n_ind in logical[0][start_log:end_log + 1][::-1]:
                    if n_ind == ind and not is_continued_stmt(source[n]):
                        n_log = start_lines.index(n)
                        source = local_fix(source, start_log, n_log - 1,
                                           start_lines, end_lines,
                                           indents, last_line)
                        start_log = n_log + 1
                        start = start_lines[start_log]
                        only_block = False
                        break
                if only_block:
                    end_log, end = find_le(start_lines, end - 1)
                continue

            source = local_fix(source, start_log, end_log,
                               start_lines, end_lines,
                               indents, last_line)
            break

    return ''.join(source)


def extract_code_from_function(function):
    """Return code handled by function."""
    if not function.__name__.startswith('fix_'):
        return None

    code = re.sub('^fix_', '', function.__name__)
    if not code:
        return None

    try:
        int(code[1:])
    except ValueError:
        return None

    return code


def create_parser():
    """Return command-line parser."""
    # Do import locally to be friendly to those who use autopep8 as a library
    # and are supporting Python 2.6.
    import argparse

    parser = argparse.ArgumentParser(description=docstring_summary(__doc__),
                                     prog='autopep8')
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    parser.add_argument('-v', '--verbose', action='count', dest='verbose',
                        default=0,
                        help='print verbose messages; '
                        'multiple -v result in more verbose messages')
    parser.add_argument('-d', '--diff', action='store_true', dest='diff',
                        help='print the diff for the fixed source')
    parser.add_argument('-i', '--in-place', action='store_true',
                        help='make changes to files in place')
    parser.add_argument('-r', '--recursive', action='store_true',
                        help='run recursively over directories; '
                        'must be used with --in-place or --diff')
    parser.add_argument('-j', '--jobs', type=int, metavar='n', default=1,
                        help='number of parallel jobs; '
                        'match CPU count if value is less than 1')
    parser.add_argument('-p', '--pep8-passes', metavar='n',
                        default=-1, type=int,
                        help='maximum number of additional pep8 passes '
                        '(default: infinite)')
    parser.add_argument('-a', '--aggressive', action='count', default=0,
                        help='enable non-whitespace changes; '
                        'multiple -a result in more aggressive changes')
    parser.add_argument('--experimental', action='store_true',
                        help='enable experimental fixes')
    parser.add_argument('--exclude', metavar='globs',
                        help='exclude file/directory names that match these '
                        'comma-separated globs')
    parser.add_argument('--list-fixes', action='store_true',
                        help='list codes for fixes; '
                        'used by --ignore and --select')
    parser.add_argument('--ignore', metavar='errors', default='',
                        help='do not fix these errors/warnings '
                        '(default: {0})'.format(DEFAULT_IGNORE))
    parser.add_argument('--select', metavar='errors', default='',
                        help='fix only these errors/warnings (e.g. E4,W)')
    parser.add_argument('--max-line-length', metavar='n', default=79, type=int,
                        help='set maximum allowed line length '
                        '(default: %(default)s)')
    parser.add_argument('--range', metavar='line', dest='line_range',
                        default=None, type=int, nargs=2,
                        help='only fix errors found within this inclusive '
                        'range of line numbers (e.g. 1 99); '
                        'line numbers are indexed at 1')
    parser.add_argument('--indent-size', default=DEFAULT_INDENT_SIZE,
                        type=int, metavar='n',
                        help='number of spaces per indent level '
                             '(default %(default)s)')
    parser.add_argument('files', nargs='*',
                        help="files to format or '-' for standard in")

    return parser


def parse_args(arguments):
    """Parse command-line options."""
    parser = create_parser()
    args = parser.parse_args(arguments)

    if not args.files and not args.list_fixes:
        parser.error('incorrect number of arguments')

    args.files = [decode_filename(name) for name in args.files]

    if '-' in args.files:
        if len(args.files) > 1:
            parser.error('cannot mix stdin and regular files')

        if args.diff:
            parser.error('--diff cannot be used with standard input')

        if args.in_place:
            parser.error('--in-place cannot be used with standard input')

        if args.recursive:
            parser.error('--recursive cannot be used with standard input')

    if len(args.files) > 1 and not (args.in_place or args.diff):
        parser.error('autopep8 only takes one filename as argument '
                     'unless the "--in-place" or "--diff" args are '
                     'used')

    if args.recursive and not (args.in_place or args.diff):
        parser.error('--recursive must be used with --in-place or --diff')

    if args.exclude and not args.recursive:
        parser.error('--exclude is only relevant when used with --recursive')

    if args.in_place and args.diff:
        parser.error('--in-place and --diff are mutually exclusive')

    if args.max_line_length <= 0:
        parser.error('--max-line-length must be greater than 0')

    if args.select:
        args.select = args.select.split(',')

    if args.ignore:
        args.ignore = args.ignore.split(',')
    elif not args.select:
        if args.aggressive:
            # Enable everything by default if aggressive.
            args.select = ['E', 'W']
        else:
            args.ignore = DEFAULT_IGNORE.split(',')

    if args.exclude:
        args.exclude = args.exclude.split(',')
    else:
        args.exclude = []

    if args.jobs < 1:
        # Do not import multiprocessing globally in case it is not supported
        # on the platform.
        import multiprocessing
        args.jobs = multiprocessing.cpu_count()

    if args.jobs > 1 and not args.in_place:
        parser.error('parallel jobs requires --in-place')

    return args


def decode_filename(filename):
    """Return Unicode filename."""
    if isinstance(filename, unicode):
        return filename
    else:
        return filename.decode(sys.getfilesystemencoding())


def supported_fixes():
    """Yield pep8 error codes that autopep8 fixes.

    Each item we yield is a tuple of the code followed by its
    description.

    """
    yield ('E101', docstring_summary(reindent.__doc__))

    instance = FixPEP8(filename=None, options=None, contents='')
    for attribute in dir(instance):
        code = re.match('fix_([ew][0-9][0-9][0-9])', attribute)
        if code:
            yield (
                code.group(1).upper(),
                re.sub(r'\s+', ' ',
                       docstring_summary(getattr(instance, attribute).__doc__))
            )

    for (code, function) in sorted(global_fixes()):
        yield (code.upper() + (4 - len(code)) * ' ',
               re.sub(r'\s+', ' ', docstring_summary(function.__doc__)))

    for code in sorted(CODE_TO_2TO3):
        yield (code.upper() + (4 - len(code)) * ' ',
               re.sub(r'\s+', ' ', docstring_summary(fix_2to3.__doc__)))


def docstring_summary(docstring):
    """Return summary of docstring."""
    return docstring.split('\n')[0]


def line_shortening_rank(candidate, indent_word, max_line_length):
    """Return rank of candidate.

    This is for sorting candidates.

    """
    if not candidate.strip():
        return 0

    rank = 0
    lines = candidate.split('\n')

    offset = 0
    if (
        not lines[0].lstrip().startswith('#') and
        lines[0].rstrip()[-1] not in '([{'
    ):
        for (opening, closing) in ('()', '[]', '{}'):
            # Don't penalize empty containers that aren't split up. Things like
            # this "foo(\n    )" aren't particularly good.
            opening_loc = lines[0].find(opening)
            closing_loc = lines[0].find(closing)
            if opening_loc >= 0:
                if closing_loc < 0 or closing_loc != opening_loc + 1:
                    offset = max(offset, 1 + opening_loc)

    current_longest = max(offset + len(x.strip()) for x in lines)

    rank += 4 * max(0, current_longest - max_line_length)

    rank += len(lines)

    # Too much variation in line length is ugly.
    rank += 2 * standard_deviation(len(line) for line in lines)

    bad_staring_symbol = {
        '(': ')',
        '[': ']',
        '{': '}'}.get(lines[0][-1])

    if len(lines) > 1:
        if (
            bad_staring_symbol and
            lines[1].lstrip().startswith(bad_staring_symbol)
        ):
            rank += 20

    for lineno, current_line in enumerate(lines):
        current_line = current_line.strip()

        if current_line.startswith('#'):
            continue

        for bad_start in ['.', '%', '+', '-', '/']:
            if current_line.startswith(bad_start):
                rank += 100

            # Do not tolerate operators on their own line.
            if current_line == bad_start:
                rank += 1000

        if current_line.endswith(('(', '[', '{', '.')):
            # Avoid lonely opening. They result in longer lines.
            if len(current_line) <= len(indent_word):
                rank += 100

            # Avoid the ugliness of ", (\n".
            if (
                current_line.endswith('(') and
                current_line[:-1].rstrip().endswith(',')
            ):
                rank += 100

            # Also avoid the ugliness of "foo.\nbar"
            if current_line.endswith('.'):
                rank += 100

            if has_arithmetic_operator(current_line):
                rank += 100

        if current_line.endswith(('%', '(', '[', '{')):
            rank -= 20

        # Try to break list comprehensions at the "for".
        if current_line.startswith('for '):
            rank -= 50

        if current_line.endswith('\\'):
            # If a line ends in \-newline, it may be part of a
            # multiline string. In that case, we would like to know
            # how long that line is without the \-newline. If it's
            # longer than the maximum, or has comments, then we assume
            # that the \-newline is an okay candidate and only
            # penalize it a bit.
            total_len = len(current_line)
            lineno += 1
            while lineno < len(lines):
                total_len += len(lines[lineno])

                if lines[lineno].lstrip().startswith('#'):
                    total_len = max_line_length
                    break

                if not lines[lineno].endswith('\\'):
                    break

                lineno += 1

            if total_len < max_line_length:
                rank += 10
            else:
                rank += 1

        # Prefer breaking at commas rather than colon.
        if ',' in current_line and current_line.endswith(':'):
            rank += 10

        rank += 10 * count_unbalanced_brackets(current_line)

    return max(0, rank)


def standard_deviation(numbers):
    """Return standard devation."""
    numbers = list(numbers)
    if not numbers:
        return 0
    mean = sum(numbers) / len(numbers)
    return (sum((n - mean) ** 2 for n in numbers) /
            len(numbers)) ** .5


def has_arithmetic_operator(line):
    """Return True if line contains any arithmetic operators."""
    for operator in pep8.ARITHMETIC_OP:
        if operator in line:
            return True

    return False


def count_unbalanced_brackets(line):
    """Return number of unmatched open/close brackets."""
    count = 0
    for opening, closing in ['()', '[]', '{}']:
        count += abs(line.count(opening) - line.count(closing))

    return count


def split_at_offsets(line, offsets):
    """Split line at offsets.

    Return list of strings.

    """
    result = []

    previous_offset = 0
    current_offset = 0
    for current_offset in sorted(offsets):
        if current_offset < len(line) and previous_offset != current_offset:
            result.append(line[previous_offset:current_offset].strip())
        previous_offset = current_offset

    result.append(line[current_offset:])

    return result


class LineEndingWrapper(object):

    r"""Replace line endings to work with sys.stdout.

    It seems that sys.stdout expects only '\n' as the line ending, no matter
    the platform. Otherwise, we get repeated line endings.

    """

    def __init__(self, output):
        self.__output = output

    def write(self, s):
        self.__output.write(s.replace('\r\n', '\n').replace('\r', '\n'))

    def flush(self):
        self.__output.flush()


def match_file(filename, exclude):
    """Return True if file is okay for modifying/recursing."""
    base_name = os.path.basename(filename)

    if base_name.startswith('.'):
        return False

    for pattern in exclude:
        if fnmatch.fnmatch(base_name, pattern):
            return False

    if not os.path.isdir(filename) and not is_python_file(filename):
        return False

    return True


def find_files(filenames, recursive, exclude):
    """Yield filenames."""
    while filenames:
        name = filenames.pop(0)
        if recursive and os.path.isdir(name):
            for root, directories, children in os.walk(name):
                filenames += [os.path.join(root, f) for f in children
                              if match_file(os.path.join(root, f),
                                            exclude)]
                directories[:] = [d for d in directories
                                  if match_file(os.path.join(root, d),
                                                exclude)]
        else:
            yield name


def _fix_file(parameters):
    """Helper function for optionally running fix_file() in parallel."""
    if parameters[1].verbose:
        print('[file:{0}]'.format(parameters[0]), file=sys.stderr)
    try:
        fix_file(*parameters)
    except IOError as error:
        print(unicode(error), file=sys.stderr)


def fix_multiple_files(filenames, options, output=None):
    """Fix list of files.

    Optionally fix files recursively.

    """
    filenames = find_files(filenames, options.recursive, options.exclude)
    if options.jobs > 1:
        import multiprocessing
        pool = multiprocessing.Pool(options.jobs)
        pool.map(_fix_file,
                 [(name, options) for name in filenames])
    else:
        for name in filenames:
            _fix_file((name, options, output))


def is_python_file(filename):
    """Return True if filename is Python file."""
    if filename.endswith('.py'):
        return True

    try:
        with open_with_encoding(filename) as f:
            first_line = f.readlines(1)[0]
    except (IOError, IndexError):
        return False

    if not PYTHON_SHEBANG_REGEX.match(first_line):
        return False

    return True


def is_probably_part_of_multiline(line):
    """Return True if line is likely part of a multiline string.

    When multiline strings are involved, pep8 reports the error as being
    at the start of the multiline string, which doesn't work for us.

    """
    return (
        '"""' in line or
        "'''" in line or
        line.rstrip().endswith('\\')
    )


def main():
    """Tool main."""
    try:
        # Exit on broken pipe.
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except AttributeError:  # pragma: no cover
        # SIGPIPE is not available on Windows.
        pass

    try:
        args = parse_args(sys.argv[1:])

        if args.list_fixes:
            for code, description in sorted(supported_fixes()):
                print('{code} - {description}'.format(
                    code=code, description=description))
            return 0

        if args.files == ['-']:
            assert not args.in_place

            # LineEndingWrapper is unnecessary here due to the symmetry between
            # standard in and standard out.
            sys.stdout.write(fix_code(sys.stdin.read(), args))
        else:
            if args.in_place or args.diff:
                args.files = list(set(args.files))
            else:
                assert len(args.files) == 1
                assert not args.recursive

            fix_multiple_files(args.files, args, sys.stdout)
    except KeyboardInterrupt:
        return 1  # pragma: no cover


class CachedTokenizer(object):

    """A one-element cache around tokenize.generate_tokens().

    Original code written by Ned Batchelder, in coverage.py.

    """

    def __init__(self):
        self.last_text = None
        self.last_tokens = None

    def generate_tokens(self, text):
        """A stand-in for tokenize.generate_tokens()."""
        if text != self.last_text:
            string_io = io.StringIO(text)
            self.last_tokens = list(
                tokenize.generate_tokens(string_io.readline)
            )
            self.last_text = text
        return self.last_tokens

_cached_tokenizer = CachedTokenizer()
generate_tokens = _cached_tokenizer.generate_tokens


if __name__ == '__main__':
    sys.exit(main())
########NEW FILE########
__FILENAME__ = format_server
from __future__ import print_function

import socket
from struct import pack, unpack
import sys
import autopep8

PORT = 10011

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('localhost', 10011)
sock.bind(server_address)
sock.listen(1)
print('Format server up on %s port %s' % server_address, file=sys.stderr)
while True:
    connection, client_address = sock.accept()
    try:
        buf = b''
        while len(buf) < 4:
            buf += connection.recv(4 - len(buf))
        (size,) = unpack('>i', buf)
        if size == -1:
            print('Format server exiting.', file=sys.stderr)
            sys.exit(0)
        src = b''
        while len(src) < size:
            src += connection.recv(4096)
        src = src.decode('utf-8')
        reformatted = autopep8.fix_code(src)
        encoded = reformatted.encode('utf-8')
        connection.sendall(pack('>i', len(encoded)))
        connection.sendall(encoded)
    finally:
        connection.close()

########NEW FILE########
__FILENAME__ = pep8
#!/usr/bin/env python
# pep8.py - Check Python source code formatting, according to PEP 8
# Copyright (C) 2006-2009 Johann C. Rocholl <johann@rocholl.net>
# Copyright (C) 2009-2014 Florent Xicluna <florent.xicluna@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

r"""
Check Python source code formatting, according to PEP 8.

For usage and a list of options, try this:
$ python pep8.py -h

This program and its regression test suite live here:
http://github.com/jcrocholl/pep8

Groups of errors and warnings:
E errors
W warnings
100 indentation
200 whitespace
300 blank lines
400 imports
500 line length
600 deprecation
700 statements
900 syntax error
"""
from __future__ import with_statement

__version__ = '1.5.3a0'

import os
import sys
import re
import time
import inspect
import keyword
import tokenize
from optparse import OptionParser
from fnmatch import fnmatch
try:
    from configparser import RawConfigParser
    from io import TextIOWrapper
except ImportError:
    from ConfigParser import RawConfigParser

DEFAULT_EXCLUDE = '.svn,CVS,.bzr,.hg,.git,__pycache__'
DEFAULT_IGNORE = 'E123,E226,E24'
if sys.platform == 'win32':
    DEFAULT_CONFIG = os.path.expanduser(r'~\.pep8')
else:
    DEFAULT_CONFIG = os.path.join(os.getenv('XDG_CONFIG_HOME') or
                                  os.path.expanduser('~/.config'), 'pep8')
PROJECT_CONFIG = ('setup.cfg', 'tox.ini', '.pep8')
TESTSUITE_PATH = os.path.join(os.path.dirname(__file__), 'testsuite')
MAX_LINE_LENGTH = 79
REPORT_FORMAT = {
    'default': '%(path)s:%(row)d:%(col)d: %(code)s %(text)s',
    'pylint': '%(path)s:%(row)d: [%(code)s] %(text)s',
}

PyCF_ONLY_AST = 1024
SINGLETONS = frozenset(['False', 'None', 'True'])
KEYWORDS = frozenset(keyword.kwlist + ['print']) - SINGLETONS
UNARY_OPERATORS = frozenset(['>>', '**', '*', '+', '-'])
ARITHMETIC_OP = frozenset(['**', '*', '/', '//', '+', '-'])
WS_OPTIONAL_OPERATORS = ARITHMETIC_OP.union(['^', '&', '|', '<<', '>>', '%'])
WS_NEEDED_OPERATORS = frozenset([
    '**=', '*=', '/=', '//=', '+=', '-=', '!=', '<>', '<', '>',
    '%=', '^=', '&=', '|=', '==', '<=', '>=', '<<=', '>>=', '='])
WHITESPACE = frozenset(' \t')
SKIP_TOKENS = frozenset([tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                         tokenize.INDENT, tokenize.DEDENT])
BENCHMARK_KEYS = ['directories', 'files', 'logical lines', 'physical lines']

INDENT_REGEX = re.compile(r'([ \t]*)')
RAISE_COMMA_REGEX = re.compile(r'raise\s+\w+\s*,')
RERAISE_COMMA_REGEX = re.compile(r'raise\s+\w+\s*,.*,\s*\w+\s*$')
ERRORCODE_REGEX = re.compile(r'\b[A-Z]\d{3}\b')
DOCSTRING_REGEX = re.compile(r'u?r?["\']')
EXTRANEOUS_WHITESPACE_REGEX = re.compile(r'[[({] | []}),;:]')
WHITESPACE_AFTER_COMMA_REGEX = re.compile(r'[,;:]\s*(?:  |\t)')
COMPARE_SINGLETON_REGEX = re.compile(r'([=!]=)\s*(None|False|True)')
COMPARE_NEGATIVE_REGEX = re.compile(r'\b(not)\s+[^[({ ]+\s+(in|is)\s')
COMPARE_TYPE_REGEX = re.compile(r'(?:[=!]=|is(?:\s+not)?)\s*type(?:s.\w+Type'
                                r'|\s*\(\s*([^)]*[^ )])\s*\))')
KEYWORD_REGEX = re.compile(r'(\s*)\b(?:%s)\b(\s*)' % r'|'.join(KEYWORDS))
OPERATOR_REGEX = re.compile(r'(?:[^,\s])(\s*)(?:[-+*/|!<=>%&^]+)(\s*)')
LAMBDA_REGEX = re.compile(r'\blambda\b')
HUNK_REGEX = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@.*$')

# Work around Python < 2.6 behaviour, which does not generate NL after
# a comment which is on a line by itself.
COMMENT_WITH_NL = tokenize.generate_tokens(['#\n'].pop).send(None)[1] == '#\n'


##############################################################################
# Plugins (check functions) for physical lines
##############################################################################


def tabs_or_spaces(physical_line, indent_char):
    r"""Never mix tabs and spaces.

    The most popular way of indenting Python is with spaces only.  The
    second-most popular way is with tabs only.  Code indented with a mixture
    of tabs and spaces should be converted to using spaces exclusively.  When
    invoking the Python command line interpreter with the -t option, it issues
    warnings about code that illegally mixes tabs and spaces.  When using -tt
    these warnings become errors.  These options are highly recommended!

    Okay: if a == 0:\n        a = 1\n        b = 1
    E101: if a == 0:\n        a = 1\n\tb = 1
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    for offset, char in enumerate(indent):
        if char != indent_char:
            return offset, "E101 indentation contains mixed spaces and tabs"


def tabs_obsolete(physical_line):
    r"""For new projects, spaces-only are strongly recommended over tabs.

    Okay: if True:\n    return
    W191: if True:\n\treturn
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    if '\t' in indent:
        return indent.index('\t'), "W191 indentation contains tabs"


def trailing_whitespace(physical_line):
    r"""Trailing whitespace is superfluous.

    The warning returned varies on whether the line itself is blank, for easier
    filtering for those who want to indent their blank lines.

    Okay: spam(1)\n#
    W291: spam(1) \n#
    W293: class Foo(object):\n    \n    bang = 12
    """
    physical_line = physical_line.rstrip('\n')    # chr(10), newline
    physical_line = physical_line.rstrip('\r')    # chr(13), carriage return
    physical_line = physical_line.rstrip('\x0c')  # chr(12), form feed, ^L
    stripped = physical_line.rstrip(' \t\v')
    if physical_line != stripped:
        if stripped:
            return len(stripped), "W291 trailing whitespace"
        else:
            return 0, "W293 blank line contains whitespace"


def trailing_blank_lines(physical_line, lines, line_number):
    r"""Trailing blank lines are superfluous.

    Okay: spam(1)
    W391: spam(1)\n
    """
    if not physical_line.rstrip() and line_number == len(lines):
        return 0, "W391 blank line at end of file"


def missing_newline(physical_line):
    r"""The last line should have a newline.

    Reports warning W292.
    """
    if physical_line.rstrip() == physical_line:
        return len(physical_line), "W292 no newline at end of file"


def maximum_line_length(physical_line, max_line_length, multiline):
    r"""Limit all lines to a maximum of 79 characters.

    There are still many devices around that are limited to 80 character
    lines; plus, limiting windows to 80 characters makes it possible to have
    several windows side-by-side.  The default wrapping on such devices looks
    ugly.  Therefore, please limit all lines to a maximum of 79 characters.
    For flowing long blocks of text (docstrings or comments), limiting the
    length to 72 characters is recommended.

    Reports error E501.
    """
    line = physical_line.rstrip()
    length = len(line)
    if length > max_line_length and not noqa(line):
        # Special case for long URLs in multi-line docstrings or comments,
        # but still report the error when the 72 first chars are whitespaces.
        chunks = line.split()
        if ((len(chunks) == 1 and multiline) or
            (len(chunks) == 2 and chunks[0] == '#')) and \
                len(line) - len(chunks[-1]) < max_line_length - 7:
            return
        if hasattr(line, 'decode'):   # Python 2
            # The line could contain multi-byte characters
            try:
                length = len(line.decode('utf-8'))
            except UnicodeError:
                pass
        if length > max_line_length:
            return (max_line_length, "E501 line too long "
                    "(%d > %d characters)" % (length, max_line_length))


##############################################################################
# Plugins (check functions) for logical lines
##############################################################################


def blank_lines(logical_line, blank_lines, indent_level, line_number,
                blank_before, previous_logical, previous_indent_level):
    r"""Separate top-level function and class definitions with two blank lines.

    Method definitions inside a class are separated by a single blank line.

    Extra blank lines may be used (sparingly) to separate groups of related
    functions.  Blank lines may be omitted between a bunch of related
    one-liners (e.g. a set of dummy implementations).

    Use blank lines in functions, sparingly, to indicate logical sections.

    Okay: def a():\n    pass\n\n\ndef b():\n    pass
    Okay: def a():\n    pass\n\n\n# Foo\n# Bar\n\ndef b():\n    pass

    E301: class Foo:\n    b = 0\n    def bar():\n        pass
    E302: def a():\n    pass\n\ndef b(n):\n    pass
    E303: def a():\n    pass\n\n\n\ndef b(n):\n    pass
    E303: def a():\n\n\n\n    pass
    E304: @decorator\n\ndef a():\n    pass
    """
    if line_number < 3 and not previous_logical:
        return  # Don't expect blank lines before the first line
    if previous_logical.startswith('@'):
        if blank_lines:
            yield 0, "E304 blank lines found after function decorator"
    elif blank_lines > 2 or (indent_level and blank_lines == 2):
        yield 0, "E303 too many blank lines (%d)" % blank_lines
    elif logical_line.startswith(('def ', 'class ', '@')):
        if indent_level:
            if not (blank_before or previous_indent_level < indent_level or
                    DOCSTRING_REGEX.match(previous_logical)):
                yield 0, "E301 expected 1 blank line, found 0"
        elif blank_before != 2:
            yield 0, "E302 expected 2 blank lines, found %d" % blank_before


def extraneous_whitespace(logical_line):
    r"""Avoid extraneous whitespace.

    Avoid extraneous whitespace in these situations:
    - Immediately inside parentheses, brackets or braces.
    - Immediately before a comma, semicolon, or colon.

    Okay: spam(ham[1], {eggs: 2})
    E201: spam( ham[1], {eggs: 2})
    E201: spam(ham[ 1], {eggs: 2})
    E201: spam(ham[1], { eggs: 2})
    E202: spam(ham[1], {eggs: 2} )
    E202: spam(ham[1 ], {eggs: 2})
    E202: spam(ham[1], {eggs: 2 })

    E203: if x == 4: print x, y; x, y = y , x
    E203: if x == 4: print x, y ; x, y = y, x
    E203: if x == 4 : print x, y; x, y = y, x
    """
    line = logical_line
    for match in EXTRANEOUS_WHITESPACE_REGEX.finditer(line):
        text = match.group()
        char = text.strip()
        found = match.start()
        if text == char + ' ':
            # assert char in '([{'
            yield found + 1, "E201 whitespace after '%s'" % char
        elif line[found - 1] != ',':
            code = ('E202' if char in '}])' else 'E203')  # if char in ',;:'
            yield found, "%s whitespace before '%s'" % (code, char)


def whitespace_around_keywords(logical_line):
    r"""Avoid extraneous whitespace around keywords.

    Okay: True and False
    E271: True and  False
    E272: True  and False
    E273: True and\tFalse
    E274: True\tand False
    """
    for match in KEYWORD_REGEX.finditer(logical_line):
        before, after = match.groups()

        if '\t' in before:
            yield match.start(1), "E274 tab before keyword"
        elif len(before) > 1:
            yield match.start(1), "E272 multiple spaces before keyword"

        if '\t' in after:
            yield match.start(2), "E273 tab after keyword"
        elif len(after) > 1:
            yield match.start(2), "E271 multiple spaces after keyword"


def missing_whitespace(logical_line):
    r"""Each comma, semicolon or colon should be followed by whitespace.

    Okay: [a, b]
    Okay: (3,)
    Okay: a[1:4]
    Okay: a[:4]
    Okay: a[1:]
    Okay: a[1:4:2]
    E231: ['a','b']
    E231: foo(bar,baz)
    E231: [{'a':'b'}]
    """
    line = logical_line
    for index in range(len(line) - 1):
        char = line[index]
        if char in ',;:' and line[index + 1] not in WHITESPACE:
            before = line[:index]
            if char == ':' and before.count('[') > before.count(']') and \
                    before.rfind('{') < before.rfind('['):
                continue  # Slice syntax, no space required
            if char == ',' and line[index + 1] == ')':
                continue  # Allow tuple with only one element: (3,)
            yield index, "E231 missing whitespace after '%s'" % char


def indentation(logical_line, previous_logical, indent_char,
                indent_level, previous_indent_level):
    r"""Use 4 spaces per indentation level.

    For really old code that you don't want to mess up, you can continue to
    use 8-space tabs.

    Okay: a = 1
    Okay: if a == 0:\n    a = 1
    E111:   a = 1

    Okay: for item in items:\n    pass
    E112: for item in items:\npass

    Okay: a = 1\nb = 2
    E113: a = 1\n    b = 2
    """
    if indent_char == ' ' and indent_level % 4:
        yield 0, "E111 indentation is not a multiple of four"
    indent_expect = previous_logical.endswith(':')
    if indent_expect and indent_level <= previous_indent_level:
        yield 0, "E112 expected an indented block"
    if indent_level > previous_indent_level and not indent_expect:
        yield 0, "E113 unexpected indentation"


def continued_indentation(logical_line, tokens, indent_level, hang_closing,
                          indent_char, noqa, verbose):
    r"""Continuation lines indentation.

    Continuation lines should align wrapped elements either vertically
    using Python's implicit line joining inside parentheses, brackets
    and braces, or using a hanging indent.

    When using a hanging indent these considerations should be applied:
    - there should be no arguments on the first line, and
    - further indentation should be used to clearly distinguish itself as a
      continuation line.

    Okay: a = (\n)
    E123: a = (\n    )

    Okay: a = (\n    42)
    E121: a = (\n   42)
    E122: a = (\n42)
    E123: a = (\n    42\n    )
    E124: a = (24,\n     42\n)
    E125: if (\n    b):\n    pass
    E126: a = (\n        42)
    E127: a = (24,\n      42)
    E128: a = (24,\n    42)
    E129: if (a or\n    b):\n    pass
    E131: a = (\n    42\n 24)
    """
    first_row = tokens[0][2][0]
    nrows = 1 + tokens[-1][2][0] - first_row
    if noqa or nrows == 1:
        return

    # indent_next tells us whether the next block is indented; assuming
    # that it is indented by 4 spaces, then we should not allow 4-space
    # indents on the final continuation line; in turn, some other
    # indents are allowed to have an extra 4 spaces.
    indent_next = logical_line.endswith(':')

    row = depth = 0
    valid_hangs = (4,) if indent_char != '\t' else (4, 8)
    # remember how many brackets were opened on each line
    parens = [0] * nrows
    # relative indents of physical lines
    rel_indent = [0] * nrows
    # for each depth, collect a list of opening rows
    open_rows = [[0]]
    # for each depth, memorize the hanging indentation
    hangs = [None]
    # visual indents
    indent_chances = {}
    last_indent = tokens[0][2]
    visual_indent = None
    # for each depth, memorize the visual indent column
    indent = [last_indent[1]]
    if verbose >= 3:
        print(">>> " + tokens[0][4].rstrip())

    for token_type, text, start, end, line in tokens:

        newline = row < start[0] - first_row
        if newline:
            row = start[0] - first_row
            newline = (not last_token_multiline and
                       token_type not in (tokenize.NL, tokenize.NEWLINE))

        if newline:
            # this is the beginning of a continuation line.
            last_indent = start
            if verbose >= 3:
                print("... " + line.rstrip())

            # record the initial indent.
            rel_indent[row] = expand_indent(line) - indent_level

            # identify closing bracket
            close_bracket = (token_type == tokenize.OP and text in ']})')

            # is the indent relative to an opening bracket line?
            for open_row in reversed(open_rows[depth]):
                hang = rel_indent[row] - rel_indent[open_row]
                hanging_indent = hang in valid_hangs
                if hanging_indent:
                    break
            if hangs[depth]:
                hanging_indent = (hang == hangs[depth])
            # is there any chance of visual indent?
            visual_indent = (not close_bracket and hang > 0 and
                             indent_chances.get(start[1]))

            if close_bracket and indent[depth]:
                # closing bracket for visual indent
                if start[1] != indent[depth]:
                    yield (start, "E124 closing bracket does not match "
                           "visual indentation")
            elif close_bracket and not hang:
                # closing bracket matches indentation of opening bracket's line
                if hang_closing:
                    yield start, "E133 closing bracket is missing indentation"
            elif indent[depth] and start[1] < indent[depth]:
                if visual_indent is not True:
                    # visual indent is broken
                    yield (start, "E128 continuation line "
                           "under-indented for visual indent")
            elif hanging_indent or (indent_next and rel_indent[row] == 8):
                # hanging indent is verified
                if close_bracket and not hang_closing:
                    yield (start, "E123 closing bracket does not match "
                           "indentation of opening bracket's line")
                hangs[depth] = hang
            elif visual_indent is True:
                # visual indent is verified
                indent[depth] = start[1]
            elif visual_indent in (text, str):
                # ignore token lined up with matching one from a previous line
                pass
            else:
                # indent is broken
                if hang <= 0:
                    error = "E122", "missing indentation or outdented"
                elif indent[depth]:
                    error = "E127", "over-indented for visual indent"
                elif not close_bracket and hangs[depth]:
                    error = "E131", "unaligned for hanging indent"
                else:
                    hangs[depth] = hang
                    if hang > 4:
                        error = "E126", "over-indented for hanging indent"
                    else:
                        error = "E121", "under-indented for hanging indent"
                yield start, "%s continuation line %s" % error

        # look for visual indenting
        if (parens[row] and token_type not in (tokenize.NL, tokenize.COMMENT)
                and not indent[depth]):
            indent[depth] = start[1]
            indent_chances[start[1]] = True
            if verbose >= 4:
                print("bracket depth %s indent to %s" % (depth, start[1]))
        # deal with implicit string concatenation
        elif (token_type in (tokenize.STRING, tokenize.COMMENT) or
              text in ('u', 'ur', 'b', 'br')):
            indent_chances[start[1]] = str
        # special case for the "if" statement because len("if (") == 4
        elif not indent_chances and not row and not depth and text == 'if':
            indent_chances[end[1] + 1] = True
        elif text == ':' and line[end[1]:].isspace():
            open_rows[depth].append(row)

        # keep track of bracket depth
        if token_type == tokenize.OP:
            if text in '([{':
                depth += 1
                indent.append(0)
                hangs.append(None)
                if len(open_rows) == depth:
                    open_rows.append([])
                open_rows[depth].append(row)
                parens[row] += 1
                if verbose >= 4:
                    print("bracket depth %s seen, col %s, visual min = %s" %
                          (depth, start[1], indent[depth]))
            elif text in ')]}' and depth > 0:
                # parent indents should not be more than this one
                prev_indent = indent.pop() or last_indent[1]
                hangs.pop()
                for d in range(depth):
                    if indent[d] > prev_indent:
                        indent[d] = 0
                for ind in list(indent_chances):
                    if ind >= prev_indent:
                        del indent_chances[ind]
                del open_rows[depth + 1:]
                depth -= 1
                if depth:
                    indent_chances[indent[depth]] = True
                for idx in range(row, -1, -1):
                    if parens[idx]:
                        parens[idx] -= 1
                        break
            assert len(indent) == depth + 1
            if start[1] not in indent_chances:
                # allow to line up tokens
                indent_chances[start[1]] = text

        last_token_multiline = (start[0] != end[0])
        if last_token_multiline:
            rel_indent[end[0] - first_row] = rel_indent[row]

    if indent_next and expand_indent(line) == indent_level + 4:
        pos = (start[0], indent[0] + 4)
        if visual_indent:
            code = "E129 visually indented line"
        else:
            code = "E125 continuation line"
        yield pos, "%s with same indent as next logical line" % code


def whitespace_before_parameters(logical_line, tokens):
    r"""Avoid extraneous whitespace.

    Avoid extraneous whitespace in the following situations:
    - before the open parenthesis that starts the argument list of a
      function call.
    - before the open parenthesis that starts an indexing or slicing.

    Okay: spam(1)
    E211: spam (1)

    Okay: dict['key'] = list[index]
    E211: dict ['key'] = list[index]
    E211: dict['key'] = list [index]
    """
    prev_type, prev_text, __, prev_end, __ = tokens[0]
    for index in range(1, len(tokens)):
        token_type, text, start, end, __ = tokens[index]
        if (token_type == tokenize.OP and
            text in '([' and
            start != prev_end and
            (prev_type == tokenize.NAME or prev_text in '}])') and
            # Syntax "class A (B):" is allowed, but avoid it
            (index < 2 or tokens[index - 2][1] != 'class') and
                # Allow "return (a.foo for a in range(5))"
                not keyword.iskeyword(prev_text)):
            yield prev_end, "E211 whitespace before '%s'" % text
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_operator(logical_line):
    r"""Avoid extraneous whitespace around an operator.

    Okay: a = 12 + 3
    E221: a = 4  + 5
    E222: a = 4 +  5
    E223: a = 4\t+ 5
    E224: a = 4 +\t5
    """
    for match in OPERATOR_REGEX.finditer(logical_line):
        before, after = match.groups()

        if '\t' in before:
            yield match.start(1), "E223 tab before operator"
        elif len(before) > 1:
            yield match.start(1), "E221 multiple spaces before operator"

        if '\t' in after:
            yield match.start(2), "E224 tab after operator"
        elif len(after) > 1:
            yield match.start(2), "E222 multiple spaces after operator"


def missing_whitespace_around_operator(logical_line, tokens):
    r"""Surround operators with a single space on either side.

    - Always surround these binary operators with a single space on
      either side: assignment (=), augmented assignment (+=, -= etc.),
      comparisons (==, <, >, !=, <=, >=, in, not in, is, is not),
      Booleans (and, or, not).

    - If operators with different priorities are used, consider adding
      whitespace around the operators with the lowest priorities.

    Okay: i = i + 1
    Okay: submitted += 1
    Okay: x = x * 2 - 1
    Okay: hypot2 = x * x + y * y
    Okay: c = (a + b) * (a - b)
    Okay: foo(bar, key='word', *args, **kwargs)
    Okay: alpha[:-i]

    E225: i=i+1
    E225: submitted +=1
    E225: x = x /2 - 1
    E225: z = x **y
    E226: c = (a+b) * (a-b)
    E226: hypot2 = x*x + y*y
    E227: c = a|b
    E228: msg = fmt%(errno, errmsg)
    """
    parens = 0
    need_space = False
    prev_type = tokenize.OP
    prev_text = prev_end = None
    for token_type, text, start, end, line in tokens:
        if token_type in (tokenize.NL, tokenize.NEWLINE, tokenize.ERRORTOKEN):
            # ERRORTOKEN is triggered by backticks in Python 3
            continue
        if text in ('(', 'lambda'):
            parens += 1
        elif text == ')':
            parens -= 1
        if need_space:
            if start != prev_end:
                # Found a (probably) needed space
                if need_space is not True and not need_space[1]:
                    yield (need_space[0],
                           "E225 missing whitespace around operator")
                need_space = False
            elif text == '>' and prev_text in ('<', '-'):
                # Tolerate the "<>" operator, even if running Python 3
                # Deal with Python 3's annotated return value "->"
                pass
            else:
                if need_space is True or need_space[1]:
                    # A needed trailing space was not found
                    yield prev_end, "E225 missing whitespace around operator"
                else:
                    code, optype = 'E226', 'arithmetic'
                    if prev_text == '%':
                        code, optype = 'E228', 'modulo'
                    elif prev_text not in ARITHMETIC_OP:
                        code, optype = 'E227', 'bitwise or shift'
                    yield (need_space[0], "%s missing whitespace "
                           "around %s operator" % (code, optype))
                need_space = False
        elif token_type == tokenize.OP and prev_end is not None:
            if text == '=' and parens:
                # Allow keyword args or defaults: foo(bar=None).
                pass
            elif text in WS_NEEDED_OPERATORS:
                need_space = True
            elif text in UNARY_OPERATORS:
                # Check if the operator is being used as a binary operator
                # Allow unary operators: -123, -x, +1.
                # Allow argument unpacking: foo(*args, **kwargs).
                if prev_type == tokenize.OP:
                    binary_usage = (prev_text in '}])')
                elif prev_type == tokenize.NAME:
                    binary_usage = (prev_text not in KEYWORDS)
                else:
                    binary_usage = (prev_type not in SKIP_TOKENS)

                if binary_usage:
                    need_space = None
            elif text in WS_OPTIONAL_OPERATORS:
                need_space = None

            if need_space is None:
                # Surrounding space is optional, but ensure that
                # trailing space matches opening space
                need_space = (prev_end, start != prev_end)
            elif need_space and start == prev_end:
                # A needed opening space was not found
                yield prev_end, "E225 missing whitespace around operator"
                need_space = False
        prev_type = token_type
        prev_text = text
        prev_end = end


def whitespace_around_comma(logical_line):
    r"""Avoid extraneous whitespace after a comma or a colon.

    Note: these checks are disabled by default

    Okay: a = (1, 2)
    E241: a = (1,  2)
    E242: a = (1,\t2)
    """
    line = logical_line
    for m in WHITESPACE_AFTER_COMMA_REGEX.finditer(line):
        found = m.start() + 1
        if '\t' in m.group():
            yield found, "E242 tab after '%s'" % m.group()[0]
        else:
            yield found, "E241 multiple spaces after '%s'" % m.group()[0]


def whitespace_around_named_parameter_equals(logical_line, tokens):
    r"""Don't use spaces around the '=' sign in function arguments.

    Don't use spaces around the '=' sign when used to indicate a
    keyword argument or a default parameter value.

    Okay: def complex(real, imag=0.0):
    Okay: return magic(r=real, i=imag)
    Okay: boolean(a == b)
    Okay: boolean(a != b)
    Okay: boolean(a <= b)
    Okay: boolean(a >= b)

    E251: def complex(real, imag = 0.0):
    E251: return magic(r = real, i = imag)
    """
    parens = 0
    no_space = False
    prev_end = None
    message = "E251 unexpected spaces around keyword / parameter equals"
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.NL:
            continue
        if no_space:
            no_space = False
            if start != prev_end:
                yield (prev_end, message)
        elif token_type == tokenize.OP:
            if text == '(':
                parens += 1
            elif text == ')':
                parens -= 1
            elif parens and text == '=':
                no_space = True
                if start != prev_end:
                    yield (prev_end, message)
        prev_end = end


def whitespace_before_comment(logical_line, tokens):
    r"""Separate inline comments by at least two spaces.

    An inline comment is a comment on the same line as a statement.  Inline
    comments should be separated by at least two spaces from the statement.
    They should start with a # and a single space.

    Each line of a block comment starts with a # and a single space
    (unless it is indented text inside the comment).

    Okay: x = x + 1  # Increment x
    Okay: x = x + 1    # Increment x
    Okay: # Block comment
    E261: x = x + 1 # Increment x
    E262: x = x + 1  #Increment x
    E262: x = x + 1  #  Increment x
    E265: #Block comment
    """
    prev_end = (0, 0)
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.COMMENT:
            inline_comment = line[:start[1]].strip()
            if inline_comment:
                if prev_end[0] == start[0] and start[1] < prev_end[1] + 2:
                    yield (prev_end,
                           "E261 at least two spaces before inline comment")
            symbol, sp, comment = text.partition(' ')
            bad_prefix = symbol not in ('#', '#:')
            if inline_comment:
                if bad_prefix or comment[:1].isspace():
                    yield start, "E262 inline comment should start with '# '"
            elif bad_prefix:
                if text.rstrip('#') and (start[0] > 1 or symbol[1] != '!'):
                    yield start, "E265 block comment should start with '# '"
        elif token_type != tokenize.NL:
            prev_end = end


def imports_on_separate_lines(logical_line):
    r"""Imports should usually be on separate lines.

    Okay: import os\nimport sys
    E401: import sys, os

    Okay: from subprocess import Popen, PIPE
    Okay: from myclas import MyClass
    Okay: from foo.bar.yourclass import YourClass
    Okay: import myclass
    Okay: import foo.bar.yourclass
    """
    line = logical_line
    if line.startswith('import '):
        found = line.find(',')
        if -1 < found and ';' not in line[:found]:
            yield found, "E401 multiple imports on one line"


def compound_statements(logical_line):
    r"""Compound statements (on the same line) are generally discouraged.

    While sometimes it's okay to put an if/for/while with a small body
    on the same line, never do this for multi-clause statements.
    Also avoid folding such long lines!

    Okay: if foo == 'blah':\n    do_blah_thing()
    Okay: do_one()
    Okay: do_two()
    Okay: do_three()

    E701: if foo == 'blah': do_blah_thing()
    E701: for x in lst: total += x
    E701: while t < 10: t = delay()
    E701: if foo == 'blah': do_blah_thing()
    E701: else: do_non_blah_thing()
    E701: try: something()
    E701: finally: cleanup()
    E701: if foo == 'blah': one(); two(); three()

    E702: do_one(); do_two(); do_three()
    E703: do_four();  # useless semicolon
    """
    line = logical_line
    last_char = len(line) - 1
    found = line.find(':')
    while -1 < found < last_char:
        before = line[:found]
        if (before.count('{') <= before.count('}') and  # {'a': 1} (dict)
            before.count('[') <= before.count(']') and  # [1:2] (slice)
            before.count('(') <= before.count(')') and  # (Python 3 annotation)
                not LAMBDA_REGEX.search(before)):       # lambda x: x
            yield found, "E701 multiple statements on one line (colon)"
        found = line.find(':', found + 1)
    found = line.find(';')
    while -1 < found:
        if found < last_char:
            yield found, "E702 multiple statements on one line (semicolon)"
        else:
            yield found, "E703 statement ends with a semicolon"
        found = line.find(';', found + 1)


def explicit_line_join(logical_line, tokens):
    r"""Avoid explicit line join between brackets.

    The preferred way of wrapping long lines is by using Python's implied line
    continuation inside parentheses, brackets and braces.  Long lines can be
    broken over multiple lines by wrapping expressions in parentheses.  These
    should be used in preference to using a backslash for line continuation.

    E502: aaa = [123, \\n       123]
    E502: aaa = ("bbb " \\n       "ccc")

    Okay: aaa = [123,\n       123]
    Okay: aaa = ("bbb "\n       "ccc")
    Okay: aaa = "bbb " \\n    "ccc"
    """
    prev_start = prev_end = parens = 0
    for token_type, text, start, end, line in tokens:
        if start[0] != prev_start and parens and backslash:
            yield backslash, "E502 the backslash is redundant between brackets"
        if end[0] != prev_end:
            if line.rstrip('\r\n').endswith('\\'):
                backslash = (end[0], len(line.splitlines()[-1]) - 1)
            else:
                backslash = None
            prev_start = prev_end = end[0]
        else:
            prev_start = start[0]
        if token_type == tokenize.OP:
            if text in '([{':
                parens += 1
            elif text in ')]}':
                parens -= 1


def comparison_to_singleton(logical_line, noqa):
    r"""Comparison to singletons should use "is" or "is not".

    Comparisons to singletons like None should always be done
    with "is" or "is not", never the equality operators.

    Okay: if arg is not None:
    E711: if arg != None:
    E712: if arg == True:

    Also, beware of writing if x when you really mean if x is not None --
    e.g. when testing whether a variable or argument that defaults to None was
    set to some other value.  The other value might have a type (such as a
    container) that could be false in a boolean context!
    """
    match = not noqa and COMPARE_SINGLETON_REGEX.search(logical_line)
    if match:
        same = (match.group(1) == '==')
        singleton = match.group(2)
        msg = "'if cond is %s:'" % (('' if same else 'not ') + singleton)
        if singleton in ('None',):
            code = 'E711'
        else:
            code = 'E712'
            nonzero = ((singleton == 'True' and same) or
                       (singleton == 'False' and not same))
            msg += " or 'if %scond:'" % ('' if nonzero else 'not ')
        yield match.start(1), ("%s comparison to %s should be %s" %
                               (code, singleton, msg))


def comparison_negative(logical_line):
    r"""Negative comparison should be done using "not in" and "is not".

    Okay: if x not in y:\n    pass
    Okay: assert (X in Y or X is Z)
    Okay: if not (X in Y):\n    pass
    Okay: zz = x is not y
    E713: Z = not X in Y
    E713: if not X.B in Y:\n    pass
    E714: if not X is Y:\n    pass
    E714: Z = not X.B is Y
    """
    match = COMPARE_NEGATIVE_REGEX.search(logical_line)
    if match:
        pos = match.start(1)
        if match.group(2) == 'in':
            yield pos, "E713 test for membership should be 'not in'"
        else:
            yield pos, "E714 test for object identity should be 'is not'"


def comparison_type(logical_line):
    r"""Object type comparisons should always use isinstance().

    Do not compare types directly.

    Okay: if isinstance(obj, int):
    E721: if type(obj) is type(1):

    When checking if an object is a string, keep in mind that it might be a
    unicode string too! In Python 2.3, str and unicode have a common base
    class, basestring, so you can do:

    Okay: if isinstance(obj, basestring):
    Okay: if type(a1) is type(b1):
    """
    match = COMPARE_TYPE_REGEX.search(logical_line)
    if match:
        inst = match.group(1)
        if inst and isidentifier(inst) and inst not in SINGLETONS:
            return  # Allow comparison for types which are not obvious
        yield match.start(), "E721 do not compare types, use 'isinstance()'"


def python_3000_has_key(logical_line, noqa):
    r"""The {}.has_key() method is removed in Python 3: use the 'in' operator.

    Okay: if "alph" in d:\n    print d["alph"]
    W601: assert d.has_key('alph')
    """
    pos = logical_line.find('.has_key(')
    if pos > -1 and not noqa:
        yield pos, "W601 .has_key() is deprecated, use 'in'"


def python_3000_raise_comma(logical_line):
    r"""When raising an exception, use "raise ValueError('message')".

    The older form is removed in Python 3.

    Okay: raise DummyError("Message")
    W602: raise DummyError, "Message"
    """
    match = RAISE_COMMA_REGEX.match(logical_line)
    if match and not RERAISE_COMMA_REGEX.match(logical_line):
        yield match.end() - 1, "W602 deprecated form of raising exception"


def python_3000_not_equal(logical_line):
    r"""New code should always use != instead of <>.

    The older syntax is removed in Python 3.

    Okay: if a != 'no':
    W603: if a <> 'no':
    """
    pos = logical_line.find('<>')
    if pos > -1:
        yield pos, "W603 '<>' is deprecated, use '!='"


def python_3000_backticks(logical_line):
    r"""Backticks are removed in Python 3: use repr() instead.

    Okay: val = repr(1 + 2)
    W604: val = `1 + 2`
    """
    pos = logical_line.find('`')
    if pos > -1:
        yield pos, "W604 backticks are deprecated, use 'repr()'"


##############################################################################
# Helper functions
##############################################################################


if '' == ''.encode():
    # Python 2: implicit encoding.
    def readlines(filename):
        """Read the source code."""
        with open(filename) as f:
            return f.readlines()
    isidentifier = re.compile(r'[a-zA-Z_]\w*').match
    stdin_get_value = sys.stdin.read
else:
    # Python 3
    def readlines(filename):
        """Read the source code."""
        try:
            with open(filename, 'rb') as f:
                (coding, lines) = tokenize.detect_encoding(f.readline)
                f = TextIOWrapper(f, coding, line_buffering=True)
                return [l.decode(coding) for l in lines] + f.readlines()
        except (LookupError, SyntaxError, UnicodeError):
            # Fall back if file encoding is improperly declared
            with open(filename, encoding='latin-1') as f:
                return f.readlines()
    isidentifier = str.isidentifier

    def stdin_get_value():
        return TextIOWrapper(sys.stdin.buffer, errors='ignore').read()
noqa = re.compile(r'# no(?:qa|pep8)\b', re.I).search


def expand_indent(line):
    r"""Return the amount of indentation.

    Tabs are expanded to the next multiple of 8.

    >>> expand_indent('    ')
    4
    >>> expand_indent('\t')
    8
    >>> expand_indent('       \t')
    8
    >>> expand_indent('        \t')
    16
    """
    if '\t' not in line:
        return len(line) - len(line.lstrip())
    result = 0
    for char in line:
        if char == '\t':
            result = result // 8 * 8 + 8
        elif char == ' ':
            result += 1
        else:
            break
    return result


def mute_string(text):
    """Replace contents with 'xxx' to prevent syntax matching.

    >>> mute_string('"abc"')
    '"xxx"'
    >>> mute_string("'''abc'''")
    "'''xxx'''"
    >>> mute_string("r'abc'")
    "r'xxx'"
    """
    # String modifiers (e.g. u or r)
    start = text.index(text[-1]) + 1
    end = len(text) - 1
    # Triple quotes
    if text[-3:] in ('"""', "'''"):
        start += 2
        end -= 2
    return text[:start] + 'x' * (end - start) + text[end:]


def parse_udiff(diff, patterns=None, parent='.'):
    """Return a dictionary of matching lines."""
    # For each file of the diff, the entry key is the filename,
    # and the value is a set of row numbers to consider.
    rv = {}
    path = nrows = None
    for line in diff.splitlines():
        if nrows:
            if line[:1] != '-':
                nrows -= 1
            continue
        if line[:3] == '@@ ':
            hunk_match = HUNK_REGEX.match(line)
            (row, nrows) = [int(g or '1') for g in hunk_match.groups()]
            rv[path].update(range(row, row + nrows))
        elif line[:3] == '+++':
            path = line[4:].split('\t', 1)[0]
            if path[:2] == 'b/':
                path = path[2:]
            rv[path] = set()
    return dict([(os.path.join(parent, path), rows)
                 for (path, rows) in rv.items()
                 if rows and filename_match(path, patterns)])


def normalize_paths(value, parent=os.curdir):
    """Parse a comma-separated list of paths.

    Return a list of absolute paths.
    """
    if not value or isinstance(value, list):
        return value
    paths = []
    for path in value.split(','):
        if '/' in path:
            path = os.path.abspath(os.path.join(parent, path))
        paths.append(path.rstrip('/'))
    return paths


def filename_match(filename, patterns, default=True):
    """Check if patterns contains a pattern that matches filename.

    If patterns is unspecified, this always returns True.
    """
    if not patterns:
        return default
    return any(fnmatch(filename, pattern) for pattern in patterns)


if COMMENT_WITH_NL:
    def _is_eol_token(token):
        return (token[0] in (tokenize.NEWLINE, tokenize.NL) or
                (token[0] == tokenize.COMMENT and token[1] == token[4]))
else:
    def _is_eol_token(token):
        return token[0] in (tokenize.NEWLINE, tokenize.NL)


##############################################################################
# Framework to run all checks
##############################################################################


_checks = {'physical_line': {}, 'logical_line': {}, 'tree': {}}


def register_check(check, codes=None):
    """Register a new check object."""
    def _add_check(check, kind, codes, args):
        if check in _checks[kind]:
            _checks[kind][check][0].extend(codes or [])
        else:
            _checks[kind][check] = (codes or [''], args)
    if inspect.isfunction(check):
        args = inspect.getargspec(check)[0]
        if args and args[0] in ('physical_line', 'logical_line'):
            if codes is None:
                codes = ERRORCODE_REGEX.findall(check.__doc__ or '')
            _add_check(check, args[0], codes, args)
    elif inspect.isclass(check):
        if inspect.getargspec(check.__init__)[0][:2] == ['self', 'tree']:
            _add_check(check, 'tree', codes, None)


def init_checks_registry():
    """Register all globally visible functions.

    The first argument name is either 'physical_line' or 'logical_line'.
    """
    mod = inspect.getmodule(register_check)
    for (name, function) in inspect.getmembers(mod, inspect.isfunction):
        register_check(function)
init_checks_registry()


class Checker(object):
    """Load a Python source file, tokenize it, check coding style."""

    def __init__(self, filename=None, lines=None,
                 options=None, report=None, **kwargs):
        if options is None:
            options = StyleGuide(kwargs).options
        else:
            assert not kwargs
        self._io_error = None
        self._physical_checks = options.physical_checks
        self._logical_checks = options.logical_checks
        self._ast_checks = options.ast_checks
        self.max_line_length = options.max_line_length
        self.multiline = False  # in a multiline string?
        self.hang_closing = options.hang_closing
        self.verbose = options.verbose
        self.filename = filename
        if filename is None:
            self.filename = 'stdin'
            self.lines = lines or []
        elif filename == '-':
            self.filename = 'stdin'
            self.lines = stdin_get_value().splitlines(True)
        elif lines is None:
            try:
                self.lines = readlines(filename)
            except IOError:
                (exc_type, exc) = sys.exc_info()[:2]
                self._io_error = '%s: %s' % (exc_type.__name__, exc)
                self.lines = []
        else:
            self.lines = lines
        if self.lines:
            ord0 = ord(self.lines[0][0])
            if ord0 in (0xef, 0xfeff):  # Strip the UTF-8 BOM
                if ord0 == 0xfeff:
                    self.lines[0] = self.lines[0][1:]
                elif self.lines[0][:3] == '\xef\xbb\xbf':
                    self.lines[0] = self.lines[0][3:]
        self.report = report or options.report
        self.report_error = self.report.error

    def report_invalid_syntax(self):
        """Check if the syntax is valid."""
        (exc_type, exc) = sys.exc_info()[:2]
        if len(exc.args) > 1:
            offset = exc.args[1]
            if len(offset) > 2:
                offset = offset[1:3]
        else:
            offset = (1, 0)
        self.report_error(offset[0], offset[1] or 0,
                          'E901 %s: %s' % (exc_type.__name__, exc.args[0]),
                          self.report_invalid_syntax)

    def readline(self):
        """Get the next line from the input buffer."""
        self.line_number += 1
        if self.line_number > len(self.lines):
            return ''
        line = self.lines[self.line_number - 1]
        if self.indent_char is None and line[:1] in WHITESPACE:
            self.indent_char = line[0]
        return line

    def run_check(self, check, argument_names):
        """Run a check plugin."""
        arguments = []
        for name in argument_names:
            arguments.append(getattr(self, name))
        return check(*arguments)

    def check_physical(self, line):
        """Run all physical checks on a raw input line."""
        self.physical_line = line
        for name, check, argument_names in self._physical_checks:
            result = self.run_check(check, argument_names)
            if result is not None:
                (offset, text) = result
                self.report_error(self.line_number, offset, text, check)
                if text[:4] == 'E101':
                    self.indent_char = line[0]

    def build_tokens_line(self):
        """Build a logical line from tokens."""
        mapping = []
        logical = []
        comments = []
        length = 0
        previous = None
        for token in self.tokens:
            (token_type, text) = token[0:2]
            if token_type == tokenize.COMMENT:
                comments.append(text)
                continue
            if token_type in SKIP_TOKENS:
                continue
            if token_type == tokenize.STRING:
                text = mute_string(text)
            if previous:
                (end_row, end) = previous[3]
                (start_row, start) = token[2]
                if end_row != start_row:    # different row
                    prev_text = self.lines[end_row - 1][end - 1]
                    if prev_text == ',' or (prev_text not in '{[('
                                            and text not in '}])'):
                        logical.append(' ')
                        length += 1
                elif end != start:  # different column
                    fill = self.lines[end_row - 1][end:start]
                    logical.append(fill)
                    length += len(fill)
            mapping.append((length, token))
            logical.append(text)
            length += len(text)
            previous = token
        self.logical_line = ''.join(logical)
        self.noqa = comments and noqa(''.join(comments))
        return mapping or [(0, self.tokens[0])]

    def check_logical(self):
        """Build a line from tokens and run all logical checks on it."""
        self.report.increment_logical_line()
        mapping = self.build_tokens_line()
        (start_row, start_col) = mapping[0][1][2]
        start_line = self.lines[start_row - 1]
        self.indent_level = expand_indent(start_line[:start_col])
        if self.blank_before < self.blank_lines:
            self.blank_before = self.blank_lines
        if self.verbose >= 2:
            print(self.logical_line[:80].rstrip())
        for name, check, argument_names in self._logical_checks:
            if self.verbose >= 4:
                print('   ' + name)
            for result in self.run_check(check, argument_names) or ():
                (offset, text) = result
                if isinstance(offset, tuple):
                    (li_number, li_offset) = offset
                else:
                    for (token_offset, token) in mapping:
                        if offset < token_offset:
                            break
                    li_number = token[2][0]
                    li_offset = (token[2][1] + offset - token_offset)
                self.report_error(li_number, li_offset, text, check)
        if self.logical_line:
            self.previous_indent_level = self.indent_level
            self.previous_logical = self.logical_line
        self.blank_lines = 0
        self.tokens = []

    def check_ast(self):
        """Build the file's AST and run all AST checks."""
        try:
            tree = compile(''.join(self.lines), '', 'exec', PyCF_ONLY_AST)
        except (SyntaxError, TypeError):
            return self.report_invalid_syntax()
        for name, cls, __ in self._ast_checks:
            checker = cls(tree, self.filename)
            for lineno, offset, text, check in checker.run():
                if not self.lines or not noqa(self.lines[lineno - 1]):
                    self.report_error(lineno, offset, text, check)

    def generate_tokens(self):
        """Tokenize the file, run physical line checks and yield tokens."""
        if self._io_error:
            self.report_error(1, 0, 'E902 %s' % self._io_error, readlines)
        tokengen = tokenize.generate_tokens(self.readline)
        try:
            for token in tokengen:
                self.maybe_check_physical(token)
                yield token
        except (SyntaxError, tokenize.TokenError):
            self.report_invalid_syntax()

    def maybe_check_physical(self, token):
        """If appropriate (based on token), check current physical line(s)."""
        # Called after every token, but act only on end of line.
        if _is_eol_token(token):
            # Obviously, a newline token ends a single physical line.
            self.check_physical(token[4])
        elif token[0] == tokenize.STRING and '\n' in token[1]:
            # Less obviously, a string that contains newlines is a
            # multiline string, either triple-quoted or with internal
            # newlines backslash-escaped. Check every physical line in the
            # string *except* for the last one: its newline is outside of
            # the multiline string, so we consider it a regular physical
            # line, and will check it like any other physical line.
            #
            # Subtleties:
            # - we don't *completely* ignore the last line; if it contains
            #   the magical "# noqa" comment, we disable all physical
            #   checks for the entire multiline string
            # - have to wind self.line_number back because initially it
            #   points to the last line of the string, and we want
            #   check_physical() to give accurate feedback
            if noqa(token[4]):
                return
            self.multiline = True
            self.line_number = token[2][0]
            for line in token[1].split('\n')[:-1]:
                self.check_physical(line + '\n')
                self.line_number += 1
            self.multiline = False

    def check_all(self, expected=None, line_offset=0):
        """Run all checks on the input file."""
        self.report.init_file(self.filename, self.lines, expected, line_offset)
        if self._ast_checks:
            self.check_ast()
        self.line_number = 0
        self.indent_char = None
        self.indent_level = self.previous_indent_level = 0
        self.previous_logical = ''
        self.tokens = []
        self.blank_lines = self.blank_before = 0
        parens = 0
        for token in self.generate_tokens():
            self.tokens.append(token)
            token_type, text = token[0:2]
            if self.verbose >= 3:
                if token[2][0] == token[3][0]:
                    pos = '[%s:%s]' % (token[2][1] or '', token[3][1])
                else:
                    pos = 'l.%s' % token[3][0]
                print('l.%s\t%s\t%s\t%r' %
                      (token[2][0], pos, tokenize.tok_name[token[0]], text))
            if token_type == tokenize.OP:
                if text in '([{':
                    parens += 1
                elif text in '}])':
                    parens -= 1
            elif not parens:
                if token_type == tokenize.NEWLINE:
                    self.check_logical()
                    self.blank_before = 0
                elif token_type == tokenize.NL:
                    if len(self.tokens) == 1:
                        # The physical line contains only this token.
                        self.blank_lines += 1
                        del self.tokens[0]
                    else:
                        self.check_logical()
                elif COMMENT_WITH_NL and token_type == tokenize.COMMENT:
                    if len(self.tokens) == 1:
                        # The comment also ends a physical line
                        text = text.rstrip('\r\n')
                        self.tokens = [(token_type, text) + token[2:]]
                        self.check_logical()
        return self.report.get_file_results()


class BaseReport(object):
    """Collect the results of the checks."""

    print_filename = False

    def __init__(self, options):
        self._benchmark_keys = options.benchmark_keys
        self._ignore_code = options.ignore_code
        # Results
        self.elapsed = 0
        self.total_errors = 0
        self.counters = dict.fromkeys(self._benchmark_keys, 0)
        self.messages = {}

    def start(self):
        """Start the timer."""
        self._start_time = time.time()

    def stop(self):
        """Stop the timer."""
        self.elapsed = time.time() - self._start_time

    def init_file(self, filename, lines, expected, line_offset):
        """Signal a new file."""
        self.filename = filename
        self.lines = lines
        self.expected = expected or ()
        self.line_offset = line_offset
        self.file_errors = 0
        self.counters['files'] += 1
        self.counters['physical lines'] += len(lines)

    def increment_logical_line(self):
        """Signal a new logical line."""
        self.counters['logical lines'] += 1

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = text[:4]
        if self._ignore_code(code):
            return
        if code in self.counters:
            self.counters[code] += 1
        else:
            self.counters[code] = 1
            self.messages[code] = text[5:]
        # Don't care about expected errors or warnings
        if code in self.expected:
            return
        if self.print_filename and not self.file_errors:
            print(self.filename)
        self.file_errors += 1
        self.total_errors += 1
        return code

    def get_file_results(self):
        """Return the count of errors and warnings for this file."""
        return self.file_errors

    def get_count(self, prefix=''):
        """Return the total count of errors and warnings."""
        return sum([self.counters[key]
                    for key in self.messages if key.startswith(prefix)])

    def get_statistics(self, prefix=''):
        """Get statistics for message codes that start with the prefix.

        prefix='' matches all errors and warnings
        prefix='E' matches all errors
        prefix='W' matches all warnings
        prefix='E4' matches all errors that have to do with imports
        """
        return ['%-7s %s %s' % (self.counters[key], key, self.messages[key])
                for key in sorted(self.messages) if key.startswith(prefix)]

    def print_statistics(self, prefix=''):
        """Print overall statistics (number of errors and warnings)."""
        for line in self.get_statistics(prefix):
            print(line)

    def print_benchmark(self):
        """Print benchmark numbers."""
        print('%-7.2f %s' % (self.elapsed, 'seconds elapsed'))
        if self.elapsed:
            for key in self._benchmark_keys:
                print('%-7d %s per second (%d total)' %
                      (self.counters[key] / self.elapsed, key,
                       self.counters[key]))


class FileReport(BaseReport):
    """Collect the results of the checks and print only the filenames."""
    print_filename = True


class StandardReport(BaseReport):
    """Collect and print the results of the checks."""

    def __init__(self, options):
        super(StandardReport, self).__init__(options)
        self._fmt = REPORT_FORMAT.get(options.format.lower(),
                                      options.format)
        self._repeat = options.repeat
        self._show_source = options.show_source
        self._show_pep8 = options.show_pep8

    def init_file(self, filename, lines, expected, line_offset):
        """Signal a new file."""
        self._deferred_print = []
        return super(StandardReport, self).init_file(
            filename, lines, expected, line_offset)

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = super(StandardReport, self).error(line_number, offset,
                                                 text, check)
        if code and (self.counters[code] == 1 or self._repeat):
            self._deferred_print.append(
                (line_number, offset, code, text[5:], check.__doc__))
        return code

    def get_file_results(self):
        """Print the result and return the overall count for this file."""
        self._deferred_print.sort()
        for line_number, offset, code, text, doc in self._deferred_print:
            print(self._fmt % {
                'path': self.filename,
                'row': self.line_offset + line_number, 'col': offset + 1,
                'code': code, 'text': text,
            })
            if self._show_source:
                if line_number > len(self.lines):
                    line = ''
                else:
                    line = self.lines[line_number - 1]
                print(line.rstrip())
                print(re.sub(r'\S', ' ', line[:offset]) + '^')
            if self._show_pep8 and doc:
                print('    ' + doc.strip())
        return self.file_errors


class DiffReport(StandardReport):
    """Collect and print the results for the changed lines only."""

    def __init__(self, options):
        super(DiffReport, self).__init__(options)
        self._selected = options.selected_lines

    def error(self, line_number, offset, text, check):
        if line_number not in self._selected[self.filename]:
            return
        return super(DiffReport, self).error(line_number, offset, text, check)


class StyleGuide(object):
    """Initialize a PEP-8 instance with few options."""

    def __init__(self, *args, **kwargs):
        # build options from the command line
        self.checker_class = kwargs.pop('checker_class', Checker)
        parse_argv = kwargs.pop('parse_argv', False)
        config_file = kwargs.pop('config_file', None)
        parser = kwargs.pop('parser', None)
        # build options from dict
        options_dict = dict(*args, **kwargs)
        arglist = None if parse_argv else options_dict.get('paths', None)
        options, self.paths = process_options(
            arglist, parse_argv, config_file, parser)
        if options_dict:
            options.__dict__.update(options_dict)
            if 'paths' in options_dict:
                self.paths = options_dict['paths']

        self.runner = self.input_file
        self.options = options

        if not options.reporter:
            options.reporter = BaseReport if options.quiet else StandardReport

        options.select = tuple(options.select or ())
        if not (options.select or options.ignore or
                options.testsuite or options.doctest) and DEFAULT_IGNORE:
            # The default choice: ignore controversial checks
            options.ignore = tuple(DEFAULT_IGNORE.split(','))
        else:
            # Ignore all checks which are not explicitly selected
            options.ignore = ('',) if options.select else tuple(options.ignore)
        options.benchmark_keys = BENCHMARK_KEYS[:]
        options.ignore_code = self.ignore_code
        options.physical_checks = self.get_checks('physical_line')
        options.logical_checks = self.get_checks('logical_line')
        options.ast_checks = self.get_checks('tree')
        self.init_report()

    def init_report(self, reporter=None):
        """Initialize the report instance."""
        self.options.report = (reporter or self.options.reporter)(self.options)
        return self.options.report

    def check_files(self, paths=None):
        """Run all checks on the paths."""
        if paths is None:
            paths = self.paths
        report = self.options.report
        runner = self.runner
        report.start()
        try:
            for path in paths:
                if os.path.isdir(path):
                    self.input_dir(path)
                elif not self.excluded(path):
                    runner(path)
        except KeyboardInterrupt:
            print('... stopped')
        report.stop()
        return report

    def input_file(self, filename, lines=None, expected=None, line_offset=0):
        """Run all checks on a Python source file."""
        if self.options.verbose:
            print('checking %s' % filename)
        fchecker = self.checker_class(
            filename, lines=lines, options=self.options)
        return fchecker.check_all(expected=expected, line_offset=line_offset)

    def input_dir(self, dirname):
        """Check all files in this directory and all subdirectories."""
        dirname = dirname.rstrip('/')
        if self.excluded(dirname):
            return 0
        counters = self.options.report.counters
        verbose = self.options.verbose
        filepatterns = self.options.filename
        runner = self.runner
        for root, dirs, files in os.walk(dirname):
            if verbose:
                print('directory ' + root)
            counters['directories'] += 1
            for subdir in sorted(dirs):
                if self.excluded(subdir, root):
                    dirs.remove(subdir)
            for filename in sorted(files):
                # contain a pattern that matches?
                if ((filename_match(filename, filepatterns) and
                     not self.excluded(filename, root))):
                    runner(os.path.join(root, filename))

    def excluded(self, filename, parent=None):
        """Check if the file should be excluded.

        Check if 'options.exclude' contains a pattern that matches filename.
        """
        if not self.options.exclude:
            return False
        basename = os.path.basename(filename)
        if filename_match(basename, self.options.exclude):
            return True
        if parent:
            filename = os.path.join(parent, filename)
        filename = os.path.abspath(filename)
        return filename_match(filename, self.options.exclude)

    def ignore_code(self, code):
        """Check if the error code should be ignored.

        If 'options.select' contains a prefix of the error code,
        return False.  Else, if 'options.ignore' contains a prefix of
        the error code, return True.
        """
        if len(code) < 4 and any(s.startswith(code)
                                 for s in self.options.select):
            return False
        return (code.startswith(self.options.ignore) and
                not code.startswith(self.options.select))

    def get_checks(self, argument_name):
        """Get all the checks for this category.

        Find all globally visible functions where the first argument name
        starts with argument_name and which contain selected tests.
        """
        checks = []
        for check, attrs in _checks[argument_name].items():
            (codes, args) = attrs
            if any(not (code and self.ignore_code(code)) for code in codes):
                checks.append((check.__name__, check, args))
        return sorted(checks)


def get_parser(prog='pep8', version=__version__):
    parser = OptionParser(prog=prog, version=version,
                          usage="%prog [options] input ...")
    parser.config_options = [
        'exclude', 'filename', 'select', 'ignore', 'max-line-length',
        'hang-closing', 'count', 'format', 'quiet', 'show-pep8',
        'show-source', 'statistics', 'verbose']
    parser.add_option('-v', '--verbose', default=0, action='count',
                      help="print status messages, or debug with -vv")
    parser.add_option('-q', '--quiet', default=0, action='count',
                      help="report only file names, or nothing with -qq")
    parser.add_option('-r', '--repeat', default=True, action='store_true',
                      help="(obsolete) show all occurrences of the same error")
    parser.add_option('--first', action='store_false', dest='repeat',
                      help="show first occurrence of each error")
    parser.add_option('--exclude', metavar='patterns', default=DEFAULT_EXCLUDE,
                      help="exclude files or directories which match these "
                           "comma separated patterns (default: %default)")
    parser.add_option('--filename', metavar='patterns', default='*.py',
                      help="when parsing directories, only check filenames "
                           "matching these comma separated patterns "
                           "(default: %default)")
    parser.add_option('--select', metavar='errors', default='',
                      help="select errors and warnings (e.g. E,W6)")
    parser.add_option('--ignore', metavar='errors', default='',
                      help="skip errors and warnings (e.g. E4,W)")
    parser.add_option('--show-source', action='store_true',
                      help="show source code for each error")
    parser.add_option('--show-pep8', action='store_true',
                      help="show text of PEP 8 for each error "
                           "(implies --first)")
    parser.add_option('--statistics', action='store_true',
                      help="count errors and warnings")
    parser.add_option('--count', action='store_true',
                      help="print total number of errors and warnings "
                           "to standard error and set exit code to 1 if "
                           "total is not null")
    parser.add_option('--max-line-length', type='int', metavar='n',
                      default=MAX_LINE_LENGTH,
                      help="set maximum allowed line length "
                           "(default: %default)")
    parser.add_option('--hang-closing', action='store_true',
                      help="hang closing bracket instead of matching "
                           "indentation of opening bracket's line")
    parser.add_option('--format', metavar='format', default='default',
                      help="set the error format [default|pylint|<custom>]")
    parser.add_option('--diff', action='store_true',
                      help="report only lines changed according to the "
                           "unified diff received on STDIN")
    group = parser.add_option_group("Testing Options")
    if os.path.exists(TESTSUITE_PATH):
        group.add_option('--testsuite', metavar='dir',
                         help="run regression tests from dir")
        group.add_option('--doctest', action='store_true',
                         help="run doctest on myself")
    group.add_option('--benchmark', action='store_true',
                     help="measure processing speed")
    return parser


def read_config(options, args, arglist, parser):
    """Read both user configuration and local configuration."""
    config = RawConfigParser()

    user_conf = options.config
    if user_conf and os.path.isfile(user_conf):
        if options.verbose:
            print('user configuration: %s' % user_conf)
        config.read(user_conf)

    local_dir = os.curdir
    parent = tail = args and os.path.abspath(os.path.commonprefix(args))
    while tail:
        if config.read([os.path.join(parent, fn) for fn in PROJECT_CONFIG]):
            local_dir = parent
            if options.verbose:
                print('local configuration: in %s' % parent)
            break
        (parent, tail) = os.path.split(parent)

    pep8_section = parser.prog
    if config.has_section(pep8_section):
        option_list = dict([(o.dest, o.type or o.action)
                            for o in parser.option_list])

        # First, read the default values
        (new_options, __) = parser.parse_args([])

        # Second, parse the configuration
        for opt in config.options(pep8_section):
            if options.verbose > 1:
                print("  %s = %s" % (opt, config.get(pep8_section, opt)))
            if opt.replace('_', '-') not in parser.config_options:
                print("Unknown option: '%s'\n  not in [%s]" %
                      (opt, ' '.join(parser.config_options)))
                sys.exit(1)
            normalized_opt = opt.replace('-', '_')
            opt_type = option_list[normalized_opt]
            if opt_type in ('int', 'count'):
                value = config.getint(pep8_section, opt)
            elif opt_type == 'string':
                value = config.get(pep8_section, opt)
                if normalized_opt == 'exclude':
                    value = normalize_paths(value, local_dir)
            else:
                assert opt_type in ('store_true', 'store_false')
                value = config.getboolean(pep8_section, opt)
            setattr(new_options, normalized_opt, value)

        # Third, overwrite with the command-line options
        (options, __) = parser.parse_args(arglist, values=new_options)
    options.doctest = options.testsuite = False
    return options


def process_options(arglist=None, parse_argv=False, config_file=None,
                    parser=None):
    """Process options passed either via arglist or via command line args."""
    if not parser:
        parser = get_parser()
    if not parser.has_option('--config'):
        if config_file is True:
            config_file = DEFAULT_CONFIG
        group = parser.add_option_group("Configuration", description=(
            "The project options are read from the [%s] section of the "
            "tox.ini file or the setup.cfg file located in any parent folder "
            "of the path(s) being processed.  Allowed options are: %s." %
            (parser.prog, ', '.join(parser.config_options))))
        group.add_option('--config', metavar='path', default=config_file,
                         help="user config file location (default: %default)")
    # Don't read the command line if the module is used as a library.
    if not arglist and not parse_argv:
        arglist = []
    # If parse_argv is True and arglist is None, arguments are
    # parsed from the command line (sys.argv)
    (options, args) = parser.parse_args(arglist)
    options.reporter = None

    if options.ensure_value('testsuite', False):
        args.append(options.testsuite)
    elif not options.ensure_value('doctest', False):
        if parse_argv and not args:
            if options.diff or any(os.path.exists(name)
                                   for name in PROJECT_CONFIG):
                args = ['.']
            else:
                parser.error('input not specified')
        options = read_config(options, args, arglist, parser)
        options.reporter = parse_argv and options.quiet == 1 and FileReport

    options.filename = options.filename and options.filename.split(',')
    options.exclude = normalize_paths(options.exclude)
    options.select = options.select and options.select.split(',')
    options.ignore = options.ignore and options.ignore.split(',')

    if options.diff:
        options.reporter = DiffReport
        stdin = stdin_get_value()
        options.selected_lines = parse_udiff(stdin, options.filename, args[0])
        args = sorted(options.selected_lines)

    return options, args


def _main():
    """Parse options and run checks on Python source."""
    pep8style = StyleGuide(parse_argv=True, config_file=True)
    options = pep8style.options
    if options.doctest or options.testsuite:
        from testsuite.support import run_tests
        report = run_tests(pep8style)
    else:
        report = pep8style.check_files()
    if options.statistics:
        report.print_statistics()
    if options.benchmark:
        report.print_benchmark()
    if options.testsuite and not options.quiet:
        report.print_results()
    if report.total_errors:
        if options.count:
            sys.stderr.write(str(report.total_errors) + '\n')
        sys.exit(1)

if __name__ == '__main__':
    _main()

########NEW FILE########
__FILENAME__ = add_global_statements
import ast


class NameAccumulator(ast.NodeVisitor):

    """
    NameAccumulator walks an AST "target" node, recursively gathering the 'id'
    properties of all of the Names it finds.
    """

    def __init__(self):
        self.names = set()

    def visit_Name(self, name):
        self.names.add(name.id)


def get_module_globals(module):
    """
    Examines all of the top-level nodes in the module, and returns the names
    of all variables assigned to.
    """
    acc = NameAccumulator()
    for node in module.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                acc.visit(t)
    return acc.names


class FindFunctionAssignments(ast.NodeVisitor):

    """
    Finds assignments in a function body, and accumulates the
    names of the assigned-to entities.
    """

    def __init__(self):
        self.acc = NameAccumulator()

    def visit_Assign(self, node):
        for t in node.targets:
            self.acc.visit(t)

    def visit_AugAssign(self, node):
        self.acc.visit(node.target)

    def find(self, func):
        self.visit(func)
        return self.acc.names


def insert_global_statements(module):
    """
    Finds all of the function definitions in a module, and inserts global
    statements in those that assign to names that are the same as existing
    module globals.

    For example, insert_global_statements will transform the AST for

      x = 0
      def draw():
          x = (x + 1) % width

    into the AST for

      x = 0
      def draw():
          global x
          x = (x + 1) % width
    """
    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            args = set(name.id for name in node.args.args)
            assigned_names = FindFunctionAssignments().find(node)
            globals = get_module_globals(module)
            needed = assigned_names.difference(args).intersection(globals)
            if needed:
                node.body.insert(0, __global__(needed))

module = ast.parse(__processing_source__ + "\n\n", filename=__file__)
insert_global_statements(module)

# This doesn't seem to be necessary for compilation. A nice result is
# that line numbers in the original source code are not affected by
# the inserted global statements.
# module = ast.fix_missing_locations(module)

codeobj = compile(module, __file__, mode='exec')
exec(codeobj)


########NEW FILE########
__FILENAME__ = core
# We expose many Processing-related names as builtins, so that no imports
# are necessary, even in auxilliary modules.
import __builtin__

# PAppletJythonDriver is a PApplet that knows how to interpret a Python
# Processing sketch, and which delegates Processing callbacks (such as
# setup(), draw(), keyPressed(), etc.) to the appropriate Python code.
from jycessing import PAppletJythonDriver

# Bring all of the core Processing classes by name into the builtin namespace.
from processing.core import PApplet
__builtin__.PApplet = PApplet

from processing.core import PConstants
__builtin__.PConstants = PConstants

from processing.core import PFont
__builtin__.PFont = PFont

from processing.core import PGraphics
__builtin__.PGraphics = PGraphics

from processing.core import PGraphicsJava2D
__builtin__.PGraphicsJava2D = PGraphicsJava2D

from processing.core import PGraphicsRetina2D
__builtin__.PGraphicsRetina2D = PGraphicsRetina2D

from processing.core import PImage
__builtin__.PImage = PImage

from processing.core import PMatrix
__builtin__.PMatrix = PMatrix

from processing.core import PMatrix2D
__builtin__.PMatrix2D = PMatrix2D

from processing.core import PMatrix3D
__builtin__.PMatrix3D = PMatrix3D

from processing.core import PShape
__builtin__.PShape = PShape

from processing.core import PShapeOBJ
__builtin__.PShapeOBJ = PShapeOBJ

from processing.core import PShapeSVG
__builtin__.PShapeSVG = PShapeSVG

from processing.core import PStyle
__builtin__.PStyle = PStyle

from processing.opengl import FontTexture
__builtin__.FontTexture = FontTexture

from processing.opengl import FrameBuffer
__builtin__.FrameBuffer = FrameBuffer

from processing.opengl import LinePath
__builtin__.LinePath = LinePath

from processing.opengl import LineStroker
__builtin__.LineStroker = LineStroker

from processing.opengl import PGL
__builtin__.PGL = PGL

from processing.opengl import PGraphics2D
__builtin__.PGraphics2D = PGraphics2D

from processing.opengl import PGraphics3D
__builtin__.PGraphics3D = PGraphics3D

from processing.opengl import PGraphicsOpenGL
__builtin__.PGraphicsOpenGL = PGraphicsOpenGL

from processing.opengl import PJOGL
__builtin__.PJOGL = PJOGL

from processing.opengl import PShader
__builtin__.PShader = PShader

from processing.opengl import PShapeOpenGL
__builtin__.PShapeOpenGL = PShapeOpenGL

from processing.opengl import Texture
__builtin__.Texture = Texture



# PVector requires special handling, because it exposes the same method names
# as static methods and instance methods.
from processing.core import PVector as __pvector__
class PVector(object):
    @classmethod
    def __new__(cls, *args):
        return __pvector__(*args[1:])

    @classmethod
    def add(cls, a, b, dest=None):
        return __pvector__.add(a, b, dest)

    @classmethod
    def sub(cls, a, b, dest=None):
        return __pvector__.sub(a, b, dest)

    @classmethod
    def mult(cls, a, b, dest=None):
        return __pvector__.mult(a, float(b), dest)

    @classmethod
    def div(cls, a, b, dest=None):
        return __pvector__.div(a, float(b), dest)

    @classmethod
    def cross(cls, a, b, dest=None):
        return __pvector__.cross(a, b, dest)

    @classmethod
    def dist(cls, a, b):
        return __pvector__.dist(a, b)

    @classmethod
    def dot(cls, a, b):
        return __pvector__.dot(a, b)

    @classmethod
    def angleBetween(cls, a, b):
        return __pvector__.angleBetween(a, b)

    @classmethod
    def random2D(cls):
        return __pvector__.random2D()

    @classmethod
    def random3D(cls):
        return __pvector__.random3D()

    @classmethod
    def fromAngle(cls, a, target=None):
        return __pvector__.fromAngle(a, target)

# Thanks, Guido!
# http://mail.python.org/pipermail/python-dev/2008-January/076194.html
def monkeypatch_method(cls):
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func
    return decorator

@monkeypatch_method(__pvector__)
def __sub__(a, b):
    return __pvector__.sub(a, b, None)

@monkeypatch_method(__pvector__)
def __isub__(a, b):
    a.sub(b)
    return a

@monkeypatch_method(__pvector__)
def __add__(a, b):
    return __pvector__.add(a, b, None)

@monkeypatch_method(__pvector__)
def __iadd__(a, b):
    a.add(b)
    return a

@monkeypatch_method(__pvector__)
def __mul__(a, b):
    if isinstance(b, __pvector__):
        raise TypeError("The * operator can only be used to multiply a PVector by a scalar")
    return __pvector__.mult(a, float(b), None)

@monkeypatch_method(__pvector__)
def __rmul__(a, b):
    if isinstance(b, __pvector__):
        raise TypeError("The * operator can only be used to multiply a PVector by a scalar")
    return __pvector__.mult(a, float(b), None)

@monkeypatch_method(__pvector__)
def __imul__(a, b):
    if isinstance(b, __pvector__):
        raise TypeError("The *= operator can only be used to multiply a PVector by a scalar")
    a.mult(float(b))
    return a

@monkeypatch_method(__pvector__)
def __div__(a, b):
    if isinstance(b, __pvector__):
        raise TypeError("The / operator can only be used to divide a PVector by a scalar")
    return __pvector__.div(a, float(b), None)

@monkeypatch_method(__pvector__)
def __idiv__(a, b):
    if isinstance(b, __pvector__):
        raise TypeError("The /= operator can only be used to divide a PVector by a scalar")
    a.div(float(b))
    return a

@monkeypatch_method(__pvector__)
def __magSq__(a):
    return __pvector__.magSq(a)

@monkeypatch_method(__pvector__)
def __eq__(a, b):
    return a.x == b.x and a.y == b.y and a.z == b.z

@monkeypatch_method(__pvector__)
def __lt__(a, b):
    return a.magSq() < b.magSq()

@monkeypatch_method(__pvector__)
def __le__(a, b):
    return a.magSq() <= b.magSq()

@monkeypatch_method(__pvector__)
def __gt__(a, b):
    return a.magSq() > b.magSq()

@monkeypatch_method(__pvector__)
def __ge__(a, b):
    return a.magSq() >= b.magSq()

del __sub__, __isub__, __add__, __iadd__, __mul__, __rmul__, __imul__, __div__, __idiv__, __magSq__

# Now expose the funky PVector class as a builtin.
__builtin__.PVector = PVector

# Construct the PApplet.
__papplet__ = PAppletJythonDriver(__interp__, __path__, __source__)
# Make it available to sketches by the name "this", to better match existing
# Java-based documentation for third-party libraries, and such.
__builtin__.this = __papplet__


# Expose all of the builtin Processing methods. Credit is due to
# https://github.com/kazimuth/python-mode-processing for the
# technique of exploiting Jython's bound methods, which is tidy
# and simple.
__builtin__.ambient = __papplet__.ambient
__builtin__.ambientLight = __papplet__.ambientLight
__builtin__.applyMatrix = __papplet__.applyMatrix
__builtin__.arc = __papplet__.arc
__builtin__.background = __papplet__.background
__builtin__.beginCamera = __papplet__.beginCamera
__builtin__.beginContour = __papplet__.beginContour
__builtin__.beginRaw = __papplet__.beginRaw
__builtin__.beginRecord = __papplet__.beginRecord
__builtin__.beginShape = __papplet__.beginShape
__builtin__.bezier = __papplet__.bezier
__builtin__.bezierDetail = __papplet__.bezierDetail
__builtin__.bezierPoint = __papplet__.bezierPoint
__builtin__.bezierTangent = __papplet__.bezierTangent
__builtin__.bezierVertex = __papplet__.bezierVertex
__builtin__.blend = __papplet__.blend
__builtin__.blendMode = __papplet__.blendMode
__builtin__.box = __papplet__.box
__builtin__.camera = __papplet__.camera
__builtin__.clear = __papplet__.clear
__builtin__.colorMode = __papplet__.colorMode
__builtin__.copy = __papplet__.copy
__builtin__.createFont = __papplet__.createFont
__builtin__.createGraphics = __papplet__.createGraphics
__builtin__.createImage = __papplet__.createImage
__builtin__.createInput = __papplet__.createInput
__builtin__.createOutput = __papplet__.createOutput
__builtin__.createReader = __papplet__.createReader
__builtin__.createShape = __papplet__.createShape
__builtin__.createWriter = __papplet__.createWriter
__builtin__.cursor = __papplet__.cursor
__builtin__.curve = __papplet__.curve
__builtin__.curveDetail = __papplet__.curveDetail
__builtin__.curvePoint = __papplet__.curvePoint
__builtin__.curveTangent = __papplet__.curveTangent
__builtin__.curveTightness = __papplet__.curveTightness
__builtin__.curveVertex = __papplet__.curveVertex
__builtin__.delay = __papplet__.delay
__builtin__.directionalLight = __papplet__.directionalLight
__builtin__.ellipse = __papplet__.ellipse
__builtin__.ellipseMode = __papplet__.ellipseMode
__builtin__.emissive = __papplet__.emissive
__builtin__.endCamera = __papplet__.endCamera
__builtin__.endContour = __papplet__.endContour
__builtin__.endRaw = __papplet__.endRaw
__builtin__.endRecord = __papplet__.endRecord
__builtin__.endShape = __papplet__.endShape
__builtin__.exit = __papplet__.exit
__builtin__.fill = __papplet__.fill

# We handle filter() by hand to permit both P5's filter() and Python's filter().
#__builtin__.filter = __papplet__.filter

__builtin__.frameRate = __papplet__.frameRate
__builtin__.frustum = __papplet__.frustum

__builtin__.hint = __papplet__.hint
__builtin__.image = __papplet__.image
__builtin__.imageMode = __papplet__.imageMode

__builtin__.lightFalloff = __papplet__.lightFalloff
__builtin__.lightSpecular = __papplet__.lightSpecular
__builtin__.lights = __papplet__.lights
__builtin__.line = __papplet__.line
__builtin__.link = __papplet__.link
__builtin__.loadBytes = __papplet__.loadBytes
__builtin__.loadFont = __papplet__.loadFont
__builtin__.loadImage = __papplet__.loadImage
__builtin__.loadJSONArray = __papplet__.loadJSONArray
__builtin__.loadJSONObject = __papplet__.loadJSONObject
__builtin__.loadPixels = __papplet__.loadPixels
__builtin__.loadShader = __papplet__.loadShader
__builtin__.loadShape = __papplet__.loadShape
__builtin__.loadStrings = __papplet__.loadStrings
__builtin__.loadTable = __papplet__.loadTable
__builtin__.loadXML = __papplet__.loadXML
__builtin__.loop = __papplet__.loop
__builtin__.millis = __papplet__.millis
__builtin__.modelX = __papplet__.modelX
__builtin__.modelY = __papplet__.modelY
__builtin__.modelZ = __papplet__.modelZ
__builtin__.noCursor = __papplet__.noCursor
__builtin__.noFill = __papplet__.noFill
__builtin__.noLights = __papplet__.noLights
__builtin__.noLoop = __papplet__.noLoop
__builtin__.noSmooth = __papplet__.noSmooth
__builtin__.noStroke = __papplet__.noStroke
__builtin__.noTint = __papplet__.noTint
__builtin__.noise = __papplet__.noise
__builtin__.noiseDetail = __papplet__.noiseDetail
__builtin__.noiseSeed = __papplet__.noiseSeed
__builtin__.normal = __papplet__.normal
__builtin__.ortho = __papplet__.ortho
__builtin__.parseXML = __papplet__.parseXML
__builtin__.perspective = __papplet__.perspective
__builtin__.point = __papplet__.point
__builtin__.pointLight = __papplet__.pointLight
__builtin__.popMatrix = __papplet__.popMatrix
__builtin__.popStyle = __papplet__.popStyle
__builtin__.printArray = __papplet__.printArray
__builtin__.printCamera = __papplet__.printCamera
__builtin__.printMatrix = __papplet__.printMatrix
__builtin__.printProjection = __papplet__.printProjection
__builtin__.pushMatrix = __papplet__.pushMatrix
__builtin__.pushStyle = __papplet__.pushStyle
__builtin__.quad = __papplet__.quad
__builtin__.quadraticVertex = __papplet__.quadraticVertex
__builtin__.random = __papplet__.random
__builtin__.randomGaussian = __papplet__.randomGaussian
__builtin__.randomSeed = __papplet__.randomSeed
__builtin__.rect = __papplet__.rect
__builtin__.rectMode = __papplet__.rectMode
__builtin__.redraw = __papplet__.redraw
__builtin__.requestImage = __papplet__.requestImage
__builtin__.resetMatrix = __papplet__.resetMatrix
__builtin__.resetShader = __papplet__.resetShader
__builtin__.rotate = __papplet__.rotate
__builtin__.rotateX = __papplet__.rotateX
__builtin__.rotateY = __papplet__.rotateY
__builtin__.rotateZ = __papplet__.rotateZ
__builtin__.save = __papplet__.save
__builtin__.saveBytes = __papplet__.saveBytes
__builtin__.saveFrame = __papplet__.saveFrame
__builtin__.saveJSONArray = __papplet__.saveJSONArray
__builtin__.saveJSONObject = __papplet__.saveJSONObject
__builtin__.saveStream = __papplet__.saveStream
__builtin__.saveStrings = __papplet__.saveStrings
__builtin__.saveTable = __papplet__.saveTable
__builtin__.saveXML = __papplet__.saveXML
__builtin__.scale = __papplet__.scale
__builtin__.screenX = __papplet__.screenX
__builtin__.screenY = __papplet__.screenY
__builtin__.screenZ = __papplet__.screenZ
__builtin__.selectFolder = __papplet__.selectFolder
__builtin__.selectInput = __papplet__.selectInput
__builtin__.selectOutput = __papplet__.selectOutput
__builtin__.shader = __papplet__.shader
__builtin__.shape = __papplet__.shape
__builtin__.shapeMode = __papplet__.shapeMode
__builtin__.shearX = __papplet__.shearX
__builtin__.shearY = __papplet__.shearY
__builtin__.shininess = __papplet__.shininess
__builtin__.size = __papplet__.size
__builtin__.smooth = __papplet__.smooth
__builtin__.specular = __papplet__.specular
__builtin__.sphere = __papplet__.sphere
__builtin__.sphereDetail = __papplet__.sphereDetail
__builtin__.spotLight = __papplet__.spotLight
__builtin__.stroke = __papplet__.stroke
__builtin__.strokeCap = __papplet__.strokeCap
__builtin__.strokeJoin = __papplet__.strokeJoin
__builtin__.strokeWeight = __papplet__.strokeWeight

# Because of two 5-arg text() methods, we have to do this in Java.
#__builtin__.text = __papplet__.text

__builtin__.textAlign = __papplet__.textAlign
__builtin__.textAscent = __papplet__.textAscent
__builtin__.textDescent = __papplet__.textDescent
__builtin__.textFont = __papplet__.textFont
__builtin__.textLeading = __papplet__.textLeading
__builtin__.textMode = __papplet__.textMode
__builtin__.textSize = __papplet__.textSize
__builtin__.textWidth = __papplet__.textWidth
__builtin__.texture = __papplet__.texture
__builtin__.textureMode = __papplet__.textureMode
__builtin__.tint = __papplet__.tint
__builtin__.translate = __papplet__.translate
__builtin__.triangle = __papplet__.triangle
__builtin__.updatePixels = __papplet__.updatePixels
__builtin__.vertex = __papplet__.vertex

'''
In order to get colors to behave reasonably, they have to be cast to positive
long quantities on their way into Python, and 32-bit signed quantities on
their way into Java.
'''
# We have to provide a funky get() because of int/long conversion woes.
#__builtin__.get = __papplet__.get

# We handle lerpColor by hand because there's an instance method and a static method.
#__builtin__.lerpColor = __papplet__.lerpColor

def __long_color__(*args):
    return 0xFFFFFFFF & __papplet__.color(*args)
__builtin__.color = __long_color__

# These must all be implemented in Java to properly downcast our unsigned longs.
'''
__builtin__.alpha = __papplet__.alpha
__builtin__.red = __papplet__.red
__builtin__.green = __papplet__.green
__builtin__.blue = __papplet__.blue
__builtin__.hue = __papplet__.hue
__builtin__.saturation = __papplet__.saturation
__builtin__.brightness = __papplet__.brightness
'''

# And these are PApplet static methods. Some are commented out to indicate
# that we prefer or require Jython's implementation.
__builtin__.abs = PApplet.abs
__builtin__.acos = PApplet.acos
__builtin__.append = PApplet.append
__builtin__.arrayCopy = PApplet.arrayCopy
__builtin__.asin = PApplet.asin
__builtin__.atan = PApplet.atan
__builtin__.atan2 = PApplet.atan2
__builtin__.binary = PApplet.binary
__builtin__.blendColor = PApplet.blendColor
__builtin__.ceil = PApplet.ceil
__builtin__.concat = PApplet.concat
__builtin__.constrain = PApplet.constrain
__builtin__.cos = PApplet.cos
__builtin__.createInput = PApplet.createInput
__builtin__.createOutput = PApplet.createOutput
__builtin__.createReader = PApplet.createReader
__builtin__.createWriter = PApplet.createWriter
__builtin__.day = PApplet.day
__builtin__.debug = PApplet.debug
__builtin__.degrees = PApplet.degrees
__builtin__.dist = PApplet.dist
#__builtin__.exec = PApplet.exec
__builtin__.exp = PApplet.exp
__builtin__.expand = PApplet.expand
__builtin__.floor = PApplet.floor

__original_hex__ = hex
def __bogus_hex__(x):
    s = __original_hex__(x).upper()
    if s[0] == '-':
        s = '-' + s[3:]
    else:
        s = s[2:]
    if s[-1] == 'L':
        return s[:-1]
    return s
__builtin__.hex = __bogus_hex__
del __bogus_hex__

__builtin__.hour = PApplet.hour
__builtin__.join = PApplet.join
__builtin__.lerp = PApplet.lerp
__builtin__.loadBytes = PApplet.loadBytes
__builtin__.loadStrings = PApplet.loadStrings
__builtin__.log = PApplet.log
__builtin__.mag = PApplet.mag
# We permit both Python and P5's map()s.
#__builtin__.map = PApplet.map
__builtin__.match = PApplet.match
__builtin__.matchAll = PApplet.matchAll
#__builtin__.max = PApplet.max
#__builtin__.min = PApplet.min
__builtin__.minute = PApplet.minute
__builtin__.month = PApplet.month
__builtin__.nf = PApplet.nf
__builtin__.nfc = PApplet.nfc
__builtin__.nfp = PApplet.nfp
__builtin__.nfs = PApplet.nfs
__builtin__.norm = PApplet.norm
__builtin__.pow = PApplet.pow
#__builtin__.print = PApplet.print
__builtin__.println = PApplet.println
__builtin__.radians = PApplet.radians
__builtin__.reverse = PApplet.reverse
#__builtin__.round = PApplet.round
__builtin__.saveBytes = PApplet.saveBytes
__builtin__.saveStream = PApplet.saveStream
__builtin__.saveStrings = PApplet.saveStrings
__builtin__.second = PApplet.second
__builtin__.shorten = PApplet.shorten
__builtin__.sin = PApplet.sin
__builtin__.sort = PApplet.sort
__builtin__.splice = PApplet.splice
__builtin__.split = PApplet.split
__builtin__.splitTokens = PApplet.splitTokens
__builtin__.sq = PApplet.sq
__builtin__.sqrt = PApplet.sqrt
__builtin__.subset = PApplet.subset
__builtin__.tan = PApplet.tan
__builtin__.trim = PApplet.trim
__builtin__.unbinary = PApplet.unbinary
__builtin__.unhex = lambda x: int(x, base=16)
__builtin__.year = PApplet.year

del monkeypatch_method, PAppletJythonDriver

# Due to a seeming bug in Jython, the print builtin ignores the the setting of
# interp.setOut and interp.setErr.

class FakeStdOut():
    def write(self, s):
        __papplet__.printout(s)
sys.stdout = FakeStdOut()

class FakeStdErr():
    def write(self, s):
        __papplet__.printerr(s)
sys.stderr = FakeStdErr()

del FakeStdOut, FakeStdErr

########NEW FILE########
__FILENAME__ = launcher
import sys


# Our virtual "launcher" name space 
class __launcher(object):
    @staticmethod
    def create(
            name = "Launcher",
            bundle = [],
            platforms=["mac", "win"], 
            outdir="dist.platforms", 
            ignorelibs=["*video*"]
        ):
        """Creates a launcher for the given platform"""

        # Our own imports 
        import jycessing.launcher.LaunchHelper as LaunchHelper
        import jycessing.Runner as Runner
        import java.lang.System as System
        import os, shutil, zipfile, sys, inspect, stat, glob, errno

        main = System.getProperty("python.main")
        mainroot = System.getProperty("python.main.root")

        outdir = mainroot + "/" + outdir

        # Quick check if we are already deployed. In that case, 
        # don't do anything
        if "--internal" in sys.argv: return

        # Clean the outdir ...
        try: shutil.rmtree(outdir) 
        except: pass


        def copyeverything(src, dst):
            """The Machine That Copies EVERYTHING.
            https://www.youtube.com/watch?v=ibEdgQJEdTA
            """
            import shutil, errno
        
            try:
                shutil.copytree(src, dst)
            except OSError as exc:
                if exc.errno == errno.ENOTDIR:
                    shutil.copy(src, dst)
                else: raise

        def copyjars(root):
            """Copy jars & co"""
            _mainjar = Runner.getMainJarFile()
            mainjar, mainjarname = _mainjar.getAbsolutePath(), _mainjar.getName()
            libraries = Runner.getLibrariesDir().getAbsolutePath()

            shutil.copyfile(mainjar, root + "/" + mainjarname)
            shutil.copytree(libraries, root + "/libraries", ignore=shutil.ignore_patterns(*ignorelibs))


        def copydata(runtimedir):
            """Copy the main script and the given data"""
            # Create runtime directory 

            try: os.mkdir(runtimedir)
            except: pass

            # Copy bundled files
            for data in bundle:
                for f in list(glob.iglob(mainroot + "/" + data)):
                    copyeverything(f, runtimedir + "/" + f.replace(mainroot, ""))


            # Eventually copy the main file
            shutil.copyfile(main, runtimedir + "/sketch.py")


        # ... and recreate it
        os.mkdir(outdir)
        for platform in platforms: 

            pdir = outdir + "/" + platform
            tmpfile = pdir + ".zip"

            os.mkdir(pdir)

            # Copy archive
            LaunchHelper.copyResourceTo("launcher." + platform + ".zip", tmpfile)
            
            # Unzip
            z = zipfile.ZipFile(tmpfile, "r")
            z.extractall(pdir)
            z.close()

            # Try to remove the platform file we created
            try:
                os.remove(tmpfile)
            except Exception, e:
                print("Could not remove %s we used for creating the launcher. Please report." % tmpfile, e)
            


        # Now the platform specific logic
        if "mac" in platforms:    
            root = outdir + "/mac/Processing.app/Contents/"            

            # Set launcher permissions ... mmhm, when created on Windows this 
            # might lead to trouble ... Any ideas?
            mode = os.stat(root + "/MacOS/JavaAppLauncher").st_mode
            os.chmod(root + "/MacOS/JavaAppLauncher", mode | stat.S_IXUSR)
        
            # Copy the jars and app
            copyjars(root + "Java")    
            copydata(root + "/Runtime")
        
            # Adjust Info.plist
            # TODO

            os.rename(outdir + "/mac/Processing.app", outdir + "/mac/" + name + ".app/")


        if "win" in platforms:    
            root = outdir + "/win/"    

            # Copy the jars and app
            copyjars(root)    
            copydata(root + "/runtime")

            os.mkdir(root + "/jre/")

            JREREADME = open(root + "/jre/README.txt", "w")            
            JREREADME.write("In the future, you can place your JRE in here (not implemented yet).")
            JREREADME.close()

            # Adjust the launcher.ini
            # TODO

            # delete the console version (for now)
            os.remove(root + "/launcherc.exe")

            os.rename(root + "/launcher.exe", root + "/" + name.lower() + ".exe")
            os.rename(root + "/launcher.ini", root + "/" + name.lower() + ".ini")


        # We dont want to return
        System.exit(0)

            
# Set the name space 
sys.modules["launcher"] = __launcher

########NEW FILE########
__FILENAME__ = imported_module
def return_twelve():
    return 12
########NEW FILE########
__FILENAME__ = imported_module_with_pvector
def sayok():
    a = PVector(5, 7, 11)
    b = PVector(13, 17, 23)
    assert a - b == PVector(-8.0, -10.0, -12.0)
    print "OK"

########NEW FILE########
__FILENAME__ = test_autoglobal
x = 0

def setup():
    size(100, 100)
    noLoop()
    x += 1

def draw():
    assert x == 1
    print 'OK'
    exit()
########NEW FILE########
__FILENAME__ = test_color
# Make sure that the result of color() is an unsigned long, and
# compatible with pixels[] and get().

background(0)
loadPixels()
assert get(50, 50) == color(0,0,0)
assert pixels[50 * 100 + 50] == get(50, 50)
assert 0xFF000000 == color(0, 0, 0)

a = color(255, 128, 0)
assert hex(a) == 'FFFF8000'
assert alpha(a) == 255.0
assert red(a) == 255.0
assert green(a) == 128.0
assert blue(a) == 0

print 'OK'
exit()

########NEW FILE########
__FILENAME__ = test_exit
def setup():
    size(48, 48, P2D)

def draw():
    print 'OK'
    exit()

########NEW FILE########
__FILENAME__ = test_filter
def setup():
    size(48, 48, P2D)
    global img, emboss
    img = loadImage("data/python.png")
    emboss = loadShader("data/emboss.glsl")

def draw():
    global img, emboss
    # Processing builtins
    # filter(PShader)
    image(img, 0, 0)
    filter(emboss)

    # filter(kind)
    filter(BLUR)

    # filter(kind, param)
    filter(POSTERIZE, 4)

    # Python builtin
    a = filter(lambda x: x == 'banana',
               ['apple', 'grape', 'banana', 'banana'])
    assert a == ['banana', 'banana']

    print 'OK'

    exit()

########NEW FILE########
__FILENAME__ = test_hex
assert hex(unhex(hex(0xcafebabe))) == 'CAFEBABE'
assert unhex(hex(unhex('0xcafebabe'))) == 0xCAFEBABE
assert hex(unhex(hex(0xdecaf))) == 'DECAF'
assert unhex(hex(unhex('DECAF'))) == 0xDECAF
print 'OK'
exit()
########NEW FILE########
__FILENAME__ = test_import
import imported_module

assert imported_module.return_twelve() == 12
print 'OK'
exit()
########NEW FILE########
__FILENAME__ = test_inherit_str
class Foo(str):
    def __init__(self, arg):
        self.arg = arg

    def __repr__(self):
        return self.arg
    
foo = Foo('cosmic')
print foo
print str(12)
print str([12,13])
exit()
########NEW FILE########
__FILENAME__ = test_launcher
import launcher
import jycessing.Runner as Runner

rval = ""

try:
    # At the moment there is no lightweight way to test these ...s
    rval += "C" if "create" in dir(launcher) else "c"
    rval += "M" if "getMainJarFile" in dir(Runner) else "m"
    rval += "L" if "getLibraries" in dir(Runner) else "l"    
    rval += "X" if "DOES_NOT_EXIST" in dir(Runner) else "x"    
except Exception:
    pass
print(rval)
exit()
########NEW FILE########
__FILENAME__ = test_load_in_initializer
font = loadFont("data/Cabal1-48.vlw")
def setup():
    size(10, 10, P3D)
    noLoop()
    print 'OK'
    exit()

########NEW FILE########
__FILENAME__ = test_map
# Processing builtin
# map(value, low1, high1, low2, high2)
print int(map(5, 0, 10, 0, 100))
#expect 50

# Python builtin
print map(lambda x: x + 1, (12, 16, 22))[0]
#expect 13
exit()

########NEW FILE########
__FILENAME__ = test_md5
import md5

hex = md5.new("Nobody inspects the spammish repetition").hexdigest()
assert hex == 'bb649c83dd1ea5c9d9dec9a18df0ffe9'
print 'OK'
exit()

########NEW FILE########
__FILENAME__ = test_millis
start = millis()
delay(2)
assert millis() > 2
print 'OK'
exit()

########NEW FILE########
__FILENAME__ = test_pcore
print PVector(1, 2, 3)
print PFont
exit()

########NEW FILE########
__FILENAME__ = test_pixels
size(100, 100)
noStroke()

fill('#0000FF')
rect(10, 10, 10, 10)
assert get(15, 15) == 0xFF0000FF

fill(255)
rect(20, 10, 10, 10)
assert get(25, 15) == 0xFFFFFFFF

fill(0xFF00FF00)
rect(30, 10, 10, 10)
assert get(35, 15) == 0xFF00FF00

fill(lerpColor(0, 255, .5))
rect(40, 10, 10, 10)
assert get(45, 15) == 0xFF7F7F7F

fill(lerpColor('#0000FF', '#FF0000', .5))
rect(50, 10, 10, 10)
assert get(55, 15) == 0xFF7F007F

# Fill a pink square the hard way.
loadPixels()
assert pixels[15 * width + 15] == 0xFF0000FF
for x in range(60, 70):
    for y in range(10, 20):
        pixels[y * width + x] = 0xFFDD00DD
updatePixels()
assert get(65, 15) == 0xFFDD00DD

# Fill a yellow square the almost as hard way.
for x in range(70, 80):
    for y in range(10, 20):
        set(x, y, '#EEEE00')
assert get(75, 15) == 0xFFEEEE00

print 'OK'
exit()
########NEW FILE########
__FILENAME__ = test_primitives
import jycessing.primitives.PrimitiveFloat as PF
p = PF(66.0)
p.value += .7
print(p)
exit()
########NEW FILE########
__FILENAME__ = test_pvector
a = PVector(5, 7, 11)
b = PVector(13, 17, 23)
assert a - b == PVector(-8.0, -10.0, -12.0)
assert b - a == PVector(8, 10, 12)
c = PVector(18, 24, 34)
assert b + a == c
assert a + b == c
assert PVector.add(a, b) == c
assert PVector.add(a, b) == c
a.add(b)
assert a == c
a.add(b)
assert a == PVector(31.0, 41.0, 57.0)

try:
    print a * b
    raise AssertionError("That shouldn't have happened.")
except TypeError:
    pass

c = PVector(310.0, 410.0, 570.0)
assert a * 10 == c
assert a * 10 == c
assert PVector.mult(a, 10) == c
assert PVector.mult(a, 10) == c
a.mult(10)
assert a == c

assert int(1000 * PVector.dist(a, b)) == 736116
assert PVector.cross(a, b) == PVector(-260.0, 280.0, -60.0)
assert a.cross(b) == PVector(-260.0, 280.0, -60.0)
assert PVector.dot(a, b) == 24110.0

d = a.get()
d += b
assert d == a + b
d = a.get()
d -= c
assert d == a - c
d = a.get()
d *= 5.0
assert d == a * 5.0
d = a.get()
d /= 5.0
assert d == a / 5.0

assert b * 5 == b * 5.0
assert b / 5 == b / 5.0
d = b.get()
d *= 391
assert d == b * 391.0
d = b.get()
d /= 10203
assert d == b / 10203.0

d = a.get()
d += a + a
assert d == a + a + a

assert a * 57.0 == 57.0 * a

assert (a / 5.0) == (1.0 / 5.0) * a

m, n = b, c
a += b * 5 - c / 2 + PVector(0, 1, 2)
assert (m, n) == (b, c)

import copy
x = [a, b]
y = copy.deepcopy(x)

assert x == y
x[0].sub(PVector(100, 100, 100))
assert x != y

a = PVector(1, 1)
b = PVector(-2, -2)
assert a < b
assert a <= b
assert b > a
assert b >= a
a = PVector(1, 2, 3)
b = PVector(3, 2, 1)
assert a != b
assert a >= b
assert b >= a
assert a.magSq() == b.magSq()

print 'OK'

exit()

########NEW FILE########
__FILENAME__ = test_pvector_in_imported_module
import imported_module_with_pvector as m

m.sayok()
exit()

########NEW FILE########
__FILENAME__ = test_set
# Processing builtin
# set(x, y, c)
set(10, 10, color(0, 0, 128))

assert get(10,10) & 0x00FFFFFF == 128

# Python builtin
s = set()
s.add('banana')
assert 'banana' in s
assert len(s) == 1
assert 'apple' not in s

# subclass
class MySet(set):
    def __init__(self):
        set.__init__(self)
assert issubclass(MySet, set)
foo = MySet()
foo.add('baz')
assert 'baz' in foo

a = set([1, 2, 3])
b = set([3, 4, 5])
c = a.intersection(b)
import sys
assert 3 in c
assert len(c) == 1

print 'OK'
exit()

########NEW FILE########
__FILENAME__ = test_static_size
size(10, 10)
print 'OK'
exit()

########NEW FILE########
__FILENAME__ = test_unicode
text(u"ö", 0, 20)
print(u'OK')
exit()

########NEW FILE########
__FILENAME__ = test_urllib
import urllib
print "OK"
exit()

########NEW FILE########
__FILENAME__ = test_urllib2
import urllib2
print "OK"
exit()

########NEW FILE########
__FILENAME__ = example

import jycessing.primitives.PrimitiveFloat as Float


# Enable this to create a standalone version
#import launcher
#launcher.create()

# Use this for libraries such as "Ani"
f = Float(10.0) 

# Little test that the console output (or redirection 
# if started with "--redirect") works
print("You should see this in your debug output:", f)



def sketchFullScreen():
    """Override fullscreen"""
    return True


def setup():
	"""Override setup()"""
	size(displayWidth, displayHeight, P3D)

	frame.setTitle("Simple Test Application");


def draw():
	"""Override draw()"""
	# background(0)
	ellipse(mouseX, mouseY, f.value, f.value)

########NEW FILE########
