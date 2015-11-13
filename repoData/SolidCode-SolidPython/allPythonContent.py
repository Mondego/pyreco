__FILENAME__ = finger_joint
#! /usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import division
import os, sys, re

# Assumes SolidPython is in site-packages or elsewhwere in sys.path
from solid import *
from solid.utils import *

SEGMENTS = 48

def finger_joint( poly, p_a, p_b, poly_sheet_thick, other_sheet_thick, joint_width=None, kerf=0.1):
    if not joint_width: joint_width = poly_sheet_thick
    
    # Should get this passed in from poly, really
    edge_length = 50
    
    k2 = kerf/2
    points = [  [ 0,-k2],  
                [joint_width + k2, -k2],
                [joint_width + k2, other_sheet_thick - k2],
                [2*(joint_width + k2), other_sheet_thick -k2],
                [2*(joint_width + k2), -k2],
            ]
    

def assembly():
    
    a = finger_joint( p, poly_sheet_thick=4.75, other_sheet_thick=4.75, joint_width=None, kerf=0.1)
    
    return a

if __name__ == '__main__':
    a = assembly()    
    scad_render_to_file( a, file_header='$fn = %s;'%SEGMENTS, include_orig_code=True)

########NEW FILE########
__FILENAME__ = animation_example
#! /usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import division
import os, sys, re

from solid import *
from solid.utils import *

def my_animate( _time=0):
    # _time will range from 0 to 1, not including 1
    rads = _time * 2 * 3.1416
    rad = 15
    c = translate( [rad*cos(rads), rad*sin(rads)])( square( 10))
    
    return c

if __name__ == '__main__':
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    file_out = os.path.join( out_dir, 'animation_example.scad')
    
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    
    # To animate in OpenSCAD: 
    # - Run this program to generate a SCAD file.
    # - Open the generated SCAD file in OpenSCAD
    # - Choose "View -> Animate" 
    # - Enter FPS (frames per second) and Steps in the fields 
    #       at the bottom of the OpenSCAD window
    # - FPS & Steps are flexible.  For a start, set both to 20 
    #       play around from there      
    scad_render_animated_file( my_animate, # A function that takes a float argument in [0,1)
                                           # and returns an OpenSCAD object
                                steps=20,  # Number of steps to create one complete motion
                                back_and_forth=True, # If true, runs the complete motion
                                                     # forward and then in reverse,
                                                     # to avoid discontinuity
                                filepath=file_out,   # Output file 
                                include_orig_code=True ) # Append SolidPython code
                                                         # to the end of the generated
                                                         # OpenSCAD code.

    
########NEW FILE########
__FILENAME__ = append_solidpython_code
#! /usr/bin/python
# -*- coding: UTF-8 -*-
import os, sys

from solid import *
from solid.utils import *

SEGMENTS = 48

def show_appended_python_code():
    a = cylinder( r=10, h=10, center=True) + up(5)( cylinder(r1=10, r2=0, h=10))
    
    return a

if __name__ == '__main__':    
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    file_out = os.path.join( out_dir, 'append_solidpython_code.scad')
    
    a = show_appended_python_code()
    
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    # ================================================================
    # = include_orig_code appends all python code as comments to the
    # = bottom of the generated OpenSCAD code, so the final document
    # = contains the easy-to-read python code as well as the SCAD.
    # = ------------------------------------------------------------ = 
    scad_render_to_file( a, file_out,  include_orig_code=True)        


########NEW FILE########
__FILENAME__ = basic_geometry
#! /usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import division
import os, sys, re

from solid import *
from solid.utils import *

SEGMENTS = 48

def basic_geometry():
    # SolidPython code can look a lot like OpenSCAD code.  It also has 
    # some syntactic sugar built in that can make it look more pythonic.
    # Here are two identical pieces of geometry, one left and one right.
    
    # left_piece uses standard OpenSCAD grammar (note the commas between 
    # block elements; OpenSCAD doesn't require this)
    left_piece =  union()(
                        translate( [-15, 0, 0])(
                            cube( [10, 5, 3], center=True)
                        ),
                        translate( [-10, 0, 0])(
                            difference()(
                                cylinder( r=5, h=15, center=True),
                                cylinder( r=4, h=16, center=True)
                            )
                        )
                    )
    
    # Right piece uses a more Pythonic grammar.  + (plus) is equivalent to union(), 
    # - (minus) is equivalent to difference() and * (star) is equivalent to intersection
    # solid.utils also defines up(), down(), left(), right(), forward(), and back()
    # for common transforms.
    right_piece = right( 15)( cube([10, 5, 3], center=True))
    cyl =  cylinder( r=5, h=15, center=True)  - cylinder( r=4, h=16, center=True) 
    right_piece += right(10)( cyl)
                        
    return union()(left_piece, right_piece)

if __name__ == '__main__':    
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    file_out = os.path.join( out_dir, 'basic_geometry.scad')
    
    a = basic_geometry()
    
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    
    # Adding the file_header argument as shown allows you to change
    # the detail of arcs by changing the SEGMENTS variable.  This can 
    # be expensive when making lots of small curves, but is otherwise
    # useful.
    scad_render_to_file( a, file_out, file_header='$fn = %s;'%SEGMENTS) 
########NEW FILE########
__FILENAME__ = basic_scad_include
#! /usr/bin/python
# -*- coding: utf-8 -*-
import sys, os

from solid import *

# Import OpenSCAD code and call it from Python code.
# The path given to use() (or include()) must be findable in sys.path.
def demo_scad_include():
    # scad_to_include.scad includes a module called steps()
    use( "./scad_to_include.scad") #  could also use 'include', but that has side-effects
    return steps(5)


if __name__ == '__main__':    
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    file_out = os.path.join( out_dir, 'scad_include_example.scad')
    
    a = demo_scad_include()
    
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    
    scad_render_to_file( a, file_out)  
########NEW FILE########
__FILENAME__ = bom_scad
#! /usr/bin/python
# -*- coding: utf-8 -*-

# Basic shape with several repeated parts, demonstrating the use of 
# solid.utils.bill_of_materials() 
#
# Basically:  
#   -- Define every part you want in the Bill of Materials in a function
#   -- Use the 'bom_part' decorator ahead of the definition of each part's function
#           e.g.:  
                # @bom_part()
                # def my_part():
                #     pass
#   -- Optionally, you can add a description and a per-unit cost to the 
#       decorator invocations.  
#
#   -- To generate the bill of materials, call bill_of_materials()
#
#       -ETJ 08 Mar 2011

import os, sys

from solid import *
from solid.utils import *

head_rad = 2.65
head_height = 2.8

nut_height = 2.3
nut_rad = 3

m3_rad = 1.4

doohickey_h = 5

def head():
    return cylinder( h=head_height, r =head_rad)


@bom_part("M3x16 Bolt", 0.12, currency="€")
def m3_16( a=3):
    bolt_height = 16
    m = union()(
            head(),
            translate( [0,0, -bolt_height])(
                cylinder( r=m3_rad, h=bolt_height)
            )
        )
    return m


@bom_part("M3x12 Bolt", 0.09)
def m3_12():
    bolt_height = 12
    m = union()(
            head(),
            translate( [ 0, 0, -bolt_height])(
                cylinder( r=m3_rad, h=bolt_height)
            )
        )
    return m


@bom_part("M3 Nut", 0.04, currency="R$")
def m3_nut():
    hx = cylinder( r=nut_rad, h=nut_height)
    hx.add_param('$fn', 6) # make the nut hexagonal
    n = difference()(
            hx,
            translate([0,0,-EPSILON])(
                cylinder( r=m3_rad, h=nut_height+2*EPSILON )
            )
        )
    return n


@bom_part()
def doohickey():
    hole_cyl = translate([0,0,-EPSILON])(
                    cylinder(r=m3_rad, h=doohickey_h+2*EPSILON )
                )
    d = difference()(
            cube([30, 10, doohickey_h], center=True),
            translate([-10, 0,0])( hole_cyl),
            hole_cyl,
            translate([10,0,0])( hole_cyl)
        )
    return d


def assemble():
    return union()(
                doohickey(),
                translate( [-10, 0, doohickey_h/2])(  m3_12()),
                translate( [ 0, 0, doohickey_h/2])(   m3_16()),
                translate( [10, 0, doohickey_h/2])(   m3_12()),
                # Nuts
                translate( [-10, 0, -nut_height-doohickey_h/2])(  m3_nut()),
                translate( [ 0, 0, -nut_height-doohickey_h/2])(   m3_nut()),
                translate( [10, 0, -nut_height-doohickey_h/2])(   m3_nut()),                
            )

if __name__ == '__main__':    
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    file_out = os.path.join( out_dir, 'BOM_example.scad')
    
    a = assemble()
    
    bom = bill_of_materials()
    
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    print bom
    
    scad_render_to_file( a, file_out)

########NEW FILE########
__FILENAME__ = hole_example
#! /usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import division
import os, sys, re

# Assumes SolidPython is in site-packages or elsewhwere in sys.path
from solid import *
from solid.utils import *

SEGMENTS = 120

def pipe_intersection_hole():
    pipe_od = 12
    pipe_id = 10
    seg_length = 30    
    
    outer = cylinder( r=pipe_od, h=seg_length, center=True)
    inner = cylinder(r=pipe_id, h=seg_length+2, center=True)
    
    # By declaring that the internal void of pipe_a should
    # explicitly remain empty, the combination of both pipes
    # is empty all the way through.
    
    # Any OpenSCAD / SolidPython object can be declared a hole(), 
    # and after that will always be empty
    pipe_a = outer + hole()(inner)
    # Note that "pipe_a = outer - hole()( inner)" would work identically;
    # inner will always be subtracted now that it's a hole
    
    pipe_b =  rotate( a=90, v=FORWARD_VEC)( pipe_a)
    return pipe_a + pipe_b

def pipe_intersection_no_hole():
    pipe_od = 12
    pipe_id = 10
    seg_length = 30    
    
    outer = cylinder( r=pipe_od, h=seg_length, center=True)
    inner = cylinder(r=pipe_id, h=seg_length+2, center=True)
    pipe_a = outer - inner
    
    pipe_b =  rotate( a=90, v=FORWARD_VEC)( pipe_a)
    # pipe_a and pipe_b are both hollow, but because
    # their central voids aren't explicitly holes,
    # the union of both pipes has unwanted internal walls
    
    return pipe_a + pipe_b

def multipart_hole():
    # It's good to be able to keep holes empty, but often we want to put
    # things (bolts, etc.) in them.  The way to do this is to declare the 
    # object containing the hole a "part".  Then, the hole will remain
    # empty no matter what you add to the 'part'.  But if you put an object
    # that is NOT part of the 'part' into the hole, it will still appear.
    
    # On the left (not_part), here's what happens if we try to put an object 
    # into an explicit hole:  the object gets erased by the hole.
    
    # On the right (is_part), we mark the cube-with-hole as a "part",
    # and then insert the same 'bolt' cylinder into it.  The entire
    # bolt rematins.
    
    b = cube( 10, center=True)
    c = cylinder( r=2, h=12, center=True)
    
    # A cube with an explicit hole
    not_part = b - hole()(c) 
    
    # Mark this cube-with-hole as a separate part from the cylinder
    is_part = part()(not_part.copy())
    
    # This fits in the holes
    bolt = cylinder( r=1.5, h=14, center=True) + up(8)( cylinder( r=2.5, h=2.5, center=True))
    
    # The section of the bolt inside not_part disappears.  The section
    # of the bolt inside is_part is still there. 
    a = not_part + bolt + right( 45)( is_part + bolt)
    
    return a   

if __name__ == '__main__':
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    file_out = os.path.join( out_dir, 'hole_example.scad')
    
    # On the left, pipes with no explicit holes, which can give 
    # unexpected walls where we don't want them.
    # On the right, we use the hole() function to fix the problem
    a = pipe_intersection_no_hole() + right( 45)(pipe_intersection_hole())
    
    # Below is an example of how to put objects into holes and have them
    # still appear
    b = up( 40)( multipart_hole())
    a += b
    
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    scad_render_to_file( a, file_out, file_header='$fn = %s;'%SEGMENTS, include_orig_code=True)


########NEW FILE########
__FILENAME__ = koch
#! /usr/bin/python
# -*- coding: utf-8 -*-
import os, sys, re

from solid import *
from solid.utils import *

from euclid import *

ONE_THIRD = 1/3.0

def affine_combination( a, b, weight=0.5):
    '''
    Note that weight is a fraction of the distance between self and other.
    So... 0.33 is a point .33 of the way between self and other.  
    '''
    if hasattr( a, 'z'):
        return Point3(  (1-weight)*a.x + weight*b.x,  
                        (1-weight)*a.y + weight*b.y,
                        (1-weight)*a.z + weight*b.z,
                    )
    else:
        return Point2(  (1-weight)*a.x + weight*b.x,  
                        (1-weight)*a.y + weight*b.y,
                    )        

def kochify_3d( a, b, c, 
            ab_weight=0.5, bc_weight=0.5, ca_weight=0.5, 
            pyr_a_weight=ONE_THIRD, pyr_b_weight=ONE_THIRD, pyr_c_weight=ONE_THIRD,
            pyr_height_weight=ONE_THIRD
            ):
    '''
    Point3s a, b, and c must be coplanar and define a face 
    ab_weight, etc define the subdivision of the original face
    pyr_a_weight, etc define where the point of the new pyramid face will go
    pyr_height determines how far from the face the new pyramid's point will be
    '''
    triangles = []
    new_a = affine_combination( a, b, ab_weight)
    new_b = affine_combination( b, c, bc_weight)
    new_c = affine_combination( c, a, ca_weight)
    
    triangles.extend( [[a, new_a, new_c], [b, new_b, new_a], [c, new_c, new_b]])
    
    avg_pt_x = a.x*pyr_a_weight + b.x*pyr_b_weight + c.x*pyr_c_weight
    avg_pt_y = a.y*pyr_a_weight + b.y*pyr_b_weight + c.y*pyr_c_weight
    avg_pt_z = a.z*pyr_a_weight + b.z*pyr_b_weight + c.z*pyr_c_weight
    
    center_pt = Point3( avg_pt_x, avg_pt_y, avg_pt_z)
    
    # The top of the pyramid will be on a normal 
    ab_vec = b - a
    bc_vec = c - b
    ca_vec = a - c
    normal = ab_vec.cross( bc_vec).normalized()
    avg_side_length = (abs(ab_vec) + abs(bc_vec) + abs(ca_vec))/3
    pyr_h = avg_side_length * pyr_height_weight
    pyr_pt = LineSegment3( center_pt, normal, pyr_h).p2
    
    
    triangles.extend([[new_a, pyr_pt, new_c], [new_b, pyr_pt, new_a], [new_c, pyr_pt, new_b]])
    
    return triangles
    

def kochify( seg, height_ratio=0.33, left_loc= 0.33, midpoint_loc=0.5, right_loc= 0.66): 
    a, b = seg.p1, seg.p2
    l = affine_combination( a, b, left_loc)
    c = affine_combination( a, b, midpoint_loc)
    r = affine_combination( a, b, right_loc)
    # The point of the new triangle will be  height_ratio * abs(seg) long, 
    # and run perpendicular to seg, through c.
    perp = seg.v.cross().normalized()
    
    c_height = height_ratio* abs(seg)
    perp_pt = LineSegment2( c, perp, -c_height).p2
    
    # For the moment, assume perp_pt is on the right side of seg.
    # Will confirm this later if needed
    return [ LineSegment2( a, l),
             LineSegment2( l, perp_pt),
             LineSegment2( perp_pt, r),
             LineSegment2( r, b)]

def main_3d( out_dir):
    gens = 4
    
    # Parameters
    ab_weight = 0.5
    bc_weight = 0.5
    ca_weight = 0.5
    pyr_a_weight = ONE_THIRD
    pyr_b_weight = ONE_THIRD
    pyr_c_weight = ONE_THIRD
    pyr_height_weight = ONE_THIRD
    pyr_height_weight = ONE_THIRD
    # pyr_height_weight = .25 
    
    all_polys = union()
    
    # setup
    ax, ay, az = 100, -100, 100
    bx, by, bz = 100, 100,-100
    cx, cy, cz = -100, 100, 100
    dx, dy, dz = -100, -100, -100
    generations =   [   [[ Point3( ax, ay, az), Point3( bx, by, bz), Point3( cx, cy, cz)],
                         [ Point3( bx, by, bz), Point3( ax, ay, az), Point3( dx, dy, dz)],
                         [ Point3( ax, ay, az), Point3( cx, cy, cz), Point3( dx, dy, dz)],
                         [ Point3( cx, cy, cz), Point3( bx, by, bz), Point3( dx, dy, dz)],
                        ]
                    ]
    
    # Recursively generate snowflake segments
    for g in range(1, gens):
        generations.append([]) 
        for a, b, c in generations[g-1]:
            new_tris = kochify_3d( a, b, c,     
                                   ab_weight, bc_weight, ca_weight,
                                   pyr_a_weight, pyr_b_weight,pyr_c_weight,
                                   pyr_height_weight)
            # new_tris = kochify_3d(  a, b, c)
            generations[g].extend( new_tris)
        
    # Put all generations into SCAD
    orig_length = abs( generations[0][0][1] - generations[0][0][0])
    for g, a_gen in enumerate(generations):
        # Move each generation up in y so it doesn't overlap the others
        h = orig_length *1.5 * g
        
        # Build the points and triangles arrays that SCAD needs
        tris = []
        points = []
        for a,b,c in a_gen:
            points.extend([ [a.x, a.y, a.z], [b.x, b.y, b.z], [c.x, c.y, c.z]])
            t = len(points)
            tris.append([t-3, t-2, t-1])
        
        # Do the SCAD
        edges = [range(len(points))]
        all_polys.add( up( h)(
                polyhedron( points, tris)
            )
        )
    
    file_out = os.path.join( out_dir, 'koch_3d.scad')
    cur_file = __file__
    print "%(cur_file)s: SCAD file written to: %(file_out)s"%vars()
    scad_render_to_file( all_polys, file_out, include_orig_code=True)    

def main( out_dir):
    # Parameters
    midpoint_weight = 0.5
    height_ratio = 0.25
    left_loc = ONE_THIRD
    midpoint_loc = 0.5
    right_loc = 2*ONE_THIRD
    gens = 5
    
    # Results 
    all_polys = union()
    
    # setup
    ax, ay = 0, 0
    bx, by = 100, 0
    cx, cy = 50, 86.6
    base_seg1 = LineSegment2(  Point2( ax, ay), Point2( cx, cy))
    base_seg2 = LineSegment2(  Point2( cx, cy), Point2( bx, by))
    base_seg3 = LineSegment2(  Point2( bx, by), Point2( ax, ay))
    generations = [[base_seg1, base_seg2, base_seg3]]
    
    
    # Recursively generate snowflake segments
    for g in range(1, gens):
        generations.append([]) 
        for seg in generations[g-1]:
            generations[g].extend( kochify( seg, height_ratio, left_loc, midpoint_loc, right_loc))
            # generations[g].extend( kochify( seg))
    
    # # Put all generations into SCAD
    orig_length = abs( generations[0][0])
    for g, a_gen in enumerate(generations):
        points = [s.p1 for s in a_gen ]
        # points.append( a_gen[-1].p2) # add the last point
        
        rect_offset = 10
                
        # Just use arrays for points so SCAD understands
        points = [[p.x, p.y] for p in points]
        
        # Move each generation up in y so it doesn't overlap the others
        h = orig_length *1.5 * g
                
        # Do the SCAD
        edges = [range(len(points))]
        all_polys.add( forward( h)( polygon(points=points, paths=edges )))
                   
    file_out = os.path.join( out_dir,'koch.scad') 
    cur_file = __file__  
    print "%(cur_file)s: SCAD file written to: %(file_out)s "%vars()
    scad_render_to_file( all_polys, file_out, include_orig_code=True )

if __name__ == '__main__':
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    main_3d( out_dir)
    main( out_dir)
    

########NEW FILE########
__FILENAME__ = inset
from math import *
from trianglemath import *

class Vec2D:
    def __init__(self, x, y):
        self.set(x, y)
    
    def set(self, x, y):
        self.x = x
        self.y = y
    
    def times(self, t):
        return Vec2D(self.x*t, self.y*t)
    
    def add(self, v):
        self.x += v.x
        self.y += v.y
    
    def plus(self, v):
        return Vec2D(self.x+v.x, self.y+v.y)
    
    def minus(self, v):
        return Vec2D(self.x-v.x, self.y-v.y)
    
    def len(self):
        return sqrt(self.x*self.x+self.y*self.y)
    
    def normalize(self):
        l = self.len()
        self.x /= l
        self.y /= l
    
    def asTripple(self,z):
        return [self.x, self.y, z]
    
    def scalarProduct(self, v):
        return self.x*v.x + self.y*v.y
    
    def interpolate(self, v, t):
        return Vec2D(self.x*t+v.x*(1.0-t), self.y*t+v.y*(1.0-t))
    


class MetaCADLine:
    def __init__(self, s, e):
        self.start = Vec2D(s.x, s.y);
        self.end = Vec2D(e.x, e.y);
        self.dir = self.end.minus(self.start);
        self.normal = Vec2D(self.dir.x, self.dir.y);
        self.normal.normalize();
        self.normal.set(-self.normal.y, self.normal.x);
    
    def parallelMove(self, d):
        move = self.normal.times(d);
        self.start.add(move);
        self.end.add(move);
    
    def intersect(self, l):
        solve = LinearSolve2(l.dir.x, -self.dir.x, l.dir.y, -self.dir.y, self.start.x-l.start.x, self.start.y-l.start.y);
        if (solve.error):
            return None
        else:
            point = self.start.plus(self.dir.times(solve.x2));
            return Vec2D(point.x,point.y);
    

# matrix looks like this
# a b
# c d
def det(a, b, c, d):
        return a*d-b*c;

# solves system of 2 linear equations in 2 unknown
class LinearSolve2:
    # the equations look like thsi looks like this
    # x1*a + x2*b = r1
    # x1*c + x2*d = r2
    def __init__(self, a, b, c, d, r1, r2):
        q=det(a,b,c,d);
        if (abs(q) < 0.000000001):
            self.error = True;
        else:
            self.error = False;
            self.x1=det(r1,b,r2,d)/q;
            self.x2=det(a,r1,c,r2)/q;
    

def asVec2D(l):
    return Vec2D(l[0], l[1])

def insetPoly(poly, inset):
    points = []
    inverted = []
    for i in range(0, len(poly)):
            iprev = (i+len(poly)-1)%len(poly);
            inext = (i+1)%len(poly)
            
            prev = MetaCADLine(asVec2D(poly[iprev]), asVec2D(poly[i]));
            oldnorm = Vec2D(prev.normal.x, prev.normal.y)
            next = MetaCADLine(asVec2D(poly[i]), asVec2D(poly[inext]));
            
            prev.parallelMove(inset);
            next.parallelMove(inset);
            
            intersect=prev.intersect(next);
            if intersect ==    None:
                # take parallel moved poly[i]
                # from the line thats longer (in case we    have a degenerate line in there)
                if (prev.dir.length() < next.dir.length()):
                    intersect = Vec2D(next.start.x, next.start.y);
                else:
                    intersect = Vec2D(prev.end.x, prev.end.y);
            points.append(intersect.asTripple(poly[i][2]));
            if (len(points) >= 2):
                 newLine = MetaCADLine(asVec2D(points[iprev]), asVec2D(points[i]));
                 diff = newLine.normal.minus(oldnorm).len()
                 if (diff > 0.1):
                    pass
                    #print "error inverting"
                    #exit()
                 else:
                    pass
                    #print "ok"
    istart = -1
    ilen = 0
    for i in range(0, len(poly)):
        iprev = (i+len(poly)-1)%len(poly);
        inext = (i+1)%len(poly)
        prev = MetaCADLine(asVec2D(poly[iprev]), asVec2D(poly[i]));
        oldnorm = Vec2D(prev.normal.x, prev.normal.y)
        newLine = MetaCADLine(asVec2D(points[iprev]), asVec2D(points[i]));
        diff = newLine.normal.minus(oldnorm).len()
        if (diff > 0.1):
            #print "wrong dir detected"
            if (istart == -1):
                istart = i
                ilen = 1
            else:
                ilen += 1
        else:
            if (ilen > 0):
                if (istart == 0 ):
                    pass
                    #print "oh noes"
                    #exit()
                else:
                    #print "trying to save: ", istart, i
                    idxs = (len(poly)+istart-1)%len(poly)
                    idxe = (i)%len(poly)
                    p1 = points[idxs]
                    p2 = points[idxe]
                    #points[idxs] = p2
                    #points[idxe] = p1
                    for j in range(istart, i):
                        t = float(1+j-istart)/(1+i-istart)
                        #print t
                        points[j] = [p2[0]*t + p1[0]*(1-t), p2[1]*t + p1[1]*(1-t), p2[2]*t + p1[2]*(1-t)]
                    istart = -1
                    ilen = 0
            
            iprev = (i+len(poly)-1)%len(poly);
            inext = (i+1)%len(poly)
            
    
    return points


########NEW FILE########
__FILENAME__ = mazebox_clean2_stable
#   A-Mazing Box, http://www.thingiverse.com/thing:1481
#   Copyright (C) 2009    Philipp Tiefenbacher <wizards23@gmail.com>
#   With very minor changes for SolidPython compatibility, 8 March 2011
#

# Make sure we can import the OpenScad translation module
import sys, os

from math import *
from solid import *
# Requires pypng module, which can be found with 'pip install pypng', 
# 'easy_install pypng', or at http://code.google.com/p/pypng/
from testpng import *
from inset import *
from trianglemath import *

rn = 3*64
#r = 10
innerR=25
gap = 0.5
wall = 1.50
baseH=2
gripH=9
hn=90
s = 0.775


h = hn*s
hone = h/hn

toph = (h-gripH)+3

depth=[]

def flip(img):
  #for l in img:
  #  l.reverse()
  img.reverse()
  return img


for i in range(0, hn):
  depth.append([])
  for j in range(0, rn):
    depth[i].append(0.0)


depth = getPNG('playground/maze7.png')
depth = flip(depth)

def getPx(x, y, default):
  x = int(x)
  y = int(y)
  x = x % len(depth[0])
  if (y >= len(depth)):
    y = len(depth) - 1
  if (x >= 0 and x < len(depth[0]) and y >= 0 and y < len(depth)):
    return depth[y][x]
  return default

def myComp(x, y):
  d = Tripple2Vec3D(y).angle2D() - Tripple2Vec3D(x).angle2D()
  if (d  < 0):
    return -1
  elif (d == 0):
    return 0
  else:
    return 1

def bumpMapCylinder(theR, hn, inset, default):
  pts = []
  trls = []
  for i in xrange(0, hn):
    circ = []
    for j in xrange(0, rn):
        a = j*2*pi/rn
        r = theR - ((255-getPx(j, i, default))/150.0)
        p = [r*cos(a), r*sin(a), i*hone]
        circ.append(p)
    circ = insetPoly(circ, inset)
    #circ.sort(lambda x, y: -1 if (Tripple2Vec3D(y).angle2D() - Tripple2Vec3D(x).angle2D() < 0) else 1)
    aold = Tripple2Vec3D(circ[0]).angle2D()
    for c in circ:
      a = Tripple2Vec3D(c).angle2D()
      #print a
      if (a > aold and (abs(a-aold) < 1*pi)):
        #print a, aold
        #exit()
        pass
      aold = a
      pts.append(c)

  pts.append([0, 0, 0])
  pts.append([0, 0, i*hone])

  for j in range(0, rn):
    t = [j, (j+1)%rn, rn*hn]
    trls.append(t)
    t = [(rn*hn-1)-j, (rn*hn-1)-((j+1)%rn), rn*hn+1]
    trls.append(t)
    for i in range(0, hn-1):
      p1 = i*rn+((j+1)%rn)
      p2 = i*rn+j
      p3 = (i+1)*rn+j
      p4 = (i+1)*rn+((j+1)%rn)
      a1 = angleBetweenPlanes([pts[p1], pts[p2], pts[p3]], [pts[p4], pts[p1], pts[p3]])
      a1 = min(a1, pi-a1)
      a2 = angleBetweenPlanes([pts[p2], pts[p1], pts[p4]], [pts[p2], pts[p3], pts[p4]])
      a2 = min(a2, pi-a2)
      #print a1, a2
      if (a1 < a2):
        t = [p1, p2, p3]
        trls.append(t)
        t = [p4, p1, p3]
        trls.append(t)
      else:
        t = [p2, p4, p1]
        trls.append(t)
        t = [p2, p3, p4]
        trls.append(t)

  return polyhedron(pts, trls, 6)

# to generate the top part
part = 1

# to generate the bottom part
# part = 2

if part==1:
  d = difference()
  u = union()
  u.add(bumpMapCylinder(innerR, hn, 0, 255))
  u.add(cylinder(r=innerR+wall+gap, h=gripH))
  d.add(u)
  #u.add(translate([80,0,0]).add(bumpMapCylinder(innerR, wall)))
  d.add(intersection().add(bumpMapCylinder(innerR, hn+2, wall, 0).set_modifier("")).add(translate([0,0,baseH]).add(cylinder(r=innerR+2*wall,h=h*1.1).set_modifier(""))))
  #u.add()
  print "$fa=2; $fs=0.5;\n"
  print d._render()
elif part==2:
  top = difference()
  u = union()
  u2 = union()
  top.add(u)
  d = difference()
  d.add(cylinder(r = innerR+wall+gap, h=toph))
  d.add(translate([0,0,baseH]).add(cylinder(r = innerR+gap, h=toph)))
  u.add(d)
  top.add(u2)
  for i in range(0,3):
    a = i * 2*pi/3.0
    r = innerR+gap+wall/2
    u.add(translate([(r-0.3)*cos(a),(r-0.3)*sin(a), toph-6]).add(sphere(r=2.4)))
    u2.add(translate([(r+wall-0.3)*cos(a),(r+wall-0.3)*sin(a), toph-6]).add(sphere(r=2.4)))
  #top.add(cylinder(r = innerR+wall+gap, h=h))
  print "$fa=2; $fs=0.5;\n"
  print top._render()
else:
  top = difference()
  u = union()
  u2 = union()
  top.add(u)
  d = difference()
  d.add(cylinder(r = innerR+wall+gap, h=6))
  d.add(translate([0,0,-baseH]).add(cylinder(r = innerR+gap, h=h)))
  u.add(d)
  top.add(u2)
  for i in range(0,3):
    a = i * 2*pi/3.0
    r = innerR+gap+wall/2
    u.add(translate([r*cos(a),r*sin(a), 4]).add(sphere(r=2.3)))
    u2.add(translate([(r+wall)*cos(a),(r+wall)*sin(a), 4]).add(sphere(r=2.3)))
  #top.add(cylinder(r = innerR+wall+gap, h=h))
  print "//$fn=20;\n"
  print top._render()







########NEW FILE########
__FILENAME__ = testpng
import png
import urllib

def getPNG(fn):
  r=png.Reader(file=urllib.urlopen(fn))
  data = r.read()
  pixel = data[2]
  raw = []
  #print data
  for row in pixel:
    #print row
    #exit()
    r = []
    raw.append(r)
    for px in row:
      r.append(px)
  return raw



########NEW FILE########
__FILENAME__ = trianglemath
from math import *

def Tripple2Vec3D(t):
  return Vec3D(t[0], t[1], t[2])

class Vec3D:
  def __init__(self, x, y, z):
    self.set(x, y, z)
  
  def angle2D(self):
    a =  atan2(self.x, self.y)
    if (a < 0):
      a += 2*pi
    return a
  
  def set(self, x, y, z):
    self.x = x
    self.y = y
    self.z = z
  
  def times(self, t):
    return Vec3D(self.x*t, self.y*t, self.z*t)
  
  # changes the objetct itself
  def add(self, v):
    self.x += v.x
    self.y += v.y
    self.z += v.z
  
  def plus(self, v):
    return Vec3D(self.x+v.x, self.y+v.y, self.z+v.z)
  
  def minus(self, v):
    return Vec3D(self.x-v.x, self.y-v.y, self.z-v.z)
  
  def len(self):
    return sqrt(self.x*self.x+self.y*self.y+self.z*self.z)
  
  # changes the object itself
  def normalize(self):
    l = self.len()
    self.x /= l
    self.y /= l
    self.z /= l
  
  def asTripple(self):
    return [self.x, self.y, self.z]
  
  def scalarProduct(self, v):
    return self.x*v.x + self.y*v.y + self.z * v.z
  
  def crossProduct(self, v):
    return Vec3D(self.y*v.z-self.z*v.y,
                 self.z*v.x-self.x*v.z,
                 self.x*v.y-self.y*v.x)
  

def planeNormal(p):
  t1 = Tripple2Vec3D(p[0])
  t2 = Tripple2Vec3D(p[1])
  t3 = Tripple2Vec3D(p[2])
  t1.add(t3.times(-1))
  t2.add(t3.times(-1))
  return t1.crossProduct(t2)


# plane defined by a list of three len 3 lists of points in R3
def angleBetweenPlanes(p1, p2):
  n1 = planeNormal(p1)
  n2 = planeNormal(p2)
  n1.normalize()
  n2.normalize()
  #print n1.asTripple()
  #print n2.asTripple()
  s = n1.scalarProduct(n2)
  #print s
  if (s > 1):
    s = 1
  if (s < -1):
    s = -1
  return acos(s)
  

########NEW FILE########
__FILENAME__ = path_extrude_example
#! /usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import division
import os, sys, re

# Assumes SolidPython is in site-packages or elsewhwere in sys.path
from solid import *
from solid.utils import *

SEGMENTS = 48

def sinusoidal_ring( rad=25, segments=SEGMENTS):
    outline = []
    for i in range( segments):
        angle = i*360/segments
        x = rad * cos( radians(angle))
        y = rad * sin( radians(angle))
        z = 2*sin(radians(angle*6))
        outline.append( Point3(x,y,z))    
    return outline  

def star( num_points=5, outer_rad=15, dip_factor=0.5):
    star_pts = []
    for i in range(2*num_points):
        rad = outer_rad - i%2 * dip_factor*outer_rad
        angle = radians( 360/(2*num_points) * i)
        star_pts.append(Point3( rad*cos(angle), rad*sin(angle), 0)) 
    return star_pts


def extrude_example():
    
    # Note the incorrect triangulation at the two ends of the path.  This 
    # is because star isn't convex, and the triangulation algorithm for
    # the two end caps only works for convex shapes.  
    shape = star( num_points=5)
    path = sinusoidal_ring( rad=50)
    
    # If scale_factors aren't included, they'll default to 
    # no scaling at each step along path.  Here, let's 
    # make the shape twice as big at beginning and end of the path
    scales = [1] * len(path)
    scales[0] = 2
    scales[-1] = 2
    
    extruded = extrude_along_path( shape_pts=shape, path_pts=path, scale_factors=scales)
    
    return extruded

if __name__ == '__main__':    
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    file_out = os.path.join( out_dir, 'path_extrude_example.scad')
    
    a = extrude_example()
    
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    scad_render_to_file( a, file_out, include_orig_code=True)


########NEW FILE########
__FILENAME__ = screw_thread_example
#! /usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import division
import os, sys, re

from solid import *
from solid.utils import *
from solid import screw_thread 

SEGMENTS = 48

inner_rad = 40
screw_height=80
def assembly():
    section = screw_thread.default_thread_section( tooth_height=10, tooth_depth=5)  
    s = screw_thread.thread( outline_pts=section, inner_rad = inner_rad, 
                            pitch= screw_height, length=screw_height, segments_per_rot=SEGMENTS)
                            #, neck_in_degrees=90, neck_out_degrees=90)    
                        
    c = cylinder( r=inner_rad, h=screw_height )
    return s + c

if __name__ == '__main__':    
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    file_out = os.path.join( out_dir, 'screw_thread_example.scad')
    
    a = assembly()
    
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    
    scad_render_to_file( a, file_out, include_orig_code=True)
    

########NEW FILE########
__FILENAME__ = sierpinski
#! /usr/bin/python
# -*- coding: utf-8 -*-
import os, sys

from solid import *
from solid.utils import *

import random
import math

# =========================================================
# = A basic recursive Sierpinski's gasket implementation,
# outputting a file 'gasket_x.scad' to the argv[1] or $PWD
# =========================================================

class SierpinskiTetrahedron(object):
    def __init__(self, four_points):
        self.points = four_points
    
    def segments( self):
        indices = [(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)]
        return [(self.points[a], self.points[b]) for a,b in indices]        
    
    def next_gen( self, midpoint_weight=0.5, jitter_range_vec=None):
        midpoints = [weighted_midpoint( s[0], s[1], weight=midpoint_weight, jitter_range_vec=jitter_range_vec) for s in self.segments()]
        all_points = self.points + midpoints
        new_tet_indices = [ (0, 4, 5, 6), 
                            (4, 1, 7, 8),
                            (5, 2, 9, 7), 
                            (6, 3, 8, 9), ]       
        new_tets = []
        for four_ind in new_tet_indices:
            tet_points = [all_points[i] for i in four_ind]
            new_tets.append( SierpinskiTetrahedron( tet_points))
                                     
        return new_tets
    
    def scale( self, factor):
        
        self.points = [[factor*d for d in p] for p in self.points]
    
    def scad_code( self):
        triangles = [[0,1,2], [0,2,3], [0,3,1], [1,3,2]]
        return polyhedron( points=self.points, triangles=triangles, convexity =1)
    


def distance( a, b):
    return math.sqrt((a[0]-b[0])* (a[0]-b[0])+ (a[1]-b[1])* (a[1]-b[1])+ (a[2]-b[2])* (a[2]-b[2]))

def weighted_midpoint( a, b, weight=0.5, jitter_range_vec=None):
    # ignoring jitter_range_vec for now
    x = weight*a[0] + (1-weight)*b[0]
    y = weight*a[1] + (1-weight)*b[1]
    z = weight*a[2] + (1-weight)*b[2]
    
    dist = distance( a, b)
    
    if jitter_range_vec:
        x += (random.random()-.5) * dist * jitter_range_vec[0]
        y += (random.random()-.5) * dist * jitter_range_vec[1]
        z += (random.random()-.5) * dist * jitter_range_vec[2]
        
    return [x,y,z]

def sierpinski_3d( generation, scale= 1, midpoint_weight=0.5, jitter_range_vec=None):
    orig_tet = SierpinskiTetrahedron(   [ [ 1.0,  1.0,  1.0],
                                [-1.0, -1.0,  1.0],
                                [-1.0,  1.0, -1.0],
                                [ 1.0, -1.0, -1.0]])
    all_tets = [orig_tet]
    for i in range( generation):
        all_tets = [subtet for tet in all_tets for subtet in tet.next_gen( midpoint_weight, jitter_range_vec)]
    
    if scale != 1:
        for tet in all_tets:
            tet.scale(scale)
    return all_tets
    


if __name__ == '__main__':     
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.curdir
    
    generations = 3
    midpoint_weight = 0.5
    # jitter_range_vec adds some randomness to the generated shape,
    # making it more interesting.  Try:
    # jitter_range_vec = [0.5,0, 0]
    jitter_range_vec = None
    all_tets = sierpinski_3d( generations, scale=100, midpoint_weight=midpoint_weight, jitter_range_vec= jitter_range_vec)
    
    t = union()
    for tet in all_tets:
        # Create the scad code for all tetrahedra
        t.add( tet.scad_code())
        # Draw cubes at all intersections to make the shape manifold. 
        for p in tet.points:
            t.add( translate(p).add( cube(5, center=True)))  
                                                            
            
    file_out = os.path.join( out_dir, 'gasket_%s_gen.scad'%generations) 
    print "%(__file__)s: SCAD file written to: \n%(file_out)s"%vars()
    scad_render_to_file( t, file_out)
########NEW FILE########
__FILENAME__ = solidpython_template
#! /usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import division
import os, sys, re

# Assumes SolidPython is in site-packages or elsewhwere in sys.path
from solid import *
from solid.utils import *

SEGMENTS = 48


def assembly():
    # Your code here!
    a = union()
    
    return a

if __name__ == '__main__':
    a = assembly()    
    scad_render_to_file( a, file_header='$fn = %s;'%SEGMENTS, include_orig_code=True)

########NEW FILE########
__FILENAME__ = patch_euclid
import euclid
from euclid import *

from solid.utils import *  # Only needed for EPSILON. Tacky.

# NOTE: The PyEuclid on PyPi doesn't include several elements added to 
# the module as of 13 Feb 2013.  Add them here until euclid supports them

def as_arr_local( self):
    return [ self.x, self.y, self.z]

def set_length_local( self, length):
    d = self.magnitude()
    if d:
        factor = length/d
        self.x *= factor
        self.y *= factor
    
    return self            

def _intersect_line3_line3( A, B):
    # Connect A & B
    # If the length of the connecting segment  is 0, they intersect
    # at the endpoint(s) of the connecting segment
    sol = euclid._connect_line3_line3( A, B)
    # TODO: Ray3 and LineSegment3 would like to be able to know 
    # if their intersection points fall within the segment.
    if sol.magnitude_squared() < EPSILON:
        return sol.p
    else:
        return None 



def run_patch():       
    if 'as_arr' not in dir( Vector3):
        Vector3.as_arr = as_arr_local
    if 'set_length' not in dir( Vector3):
        Vector3.set_length = set_length_local
    if '_intersect_line3' not in dir(Line3):
        Line3._intersect_line3 = _intersect_line3_line3


########NEW FILE########
__FILENAME__ = screw_thread
#! /usr/bin/python
# -*- coding: utf-8 -*-
import os, sys, re

from solid import *
from solid.utils import *
from euclid import *
# NOTE: The PyEuclid on PyPi doesn't include several elements added to 
# the module as of 13 Feb 2013.  Add them here until euclid supports them
# TODO: when euclid updates, remove this cruft. -ETJ 13 Feb 2013
import patch_euclid
patch_euclid.run_patch()

def thread( outline_pts, inner_rad, pitch, length, external=True, segments_per_rot=32,neck_in_degrees=0, neck_out_degrees=0):
    '''
    Sweeps outline_pts (an array of points describing a closed polygon in XY)
    through a spiral. 
    
    This is done by creating and returning one huge polyhedron, with potentially
    thousands of faces.  An alternate approach would make one single polyhedron,
    then repeat it over and over in the spiral shape, unioning them all together.  
    This would create a similar number of SCAD objects and operations, but still
    require a lot of transforms and unions to be done in the SCAD code rather than
    in the python, as here.  Also would take some doing to make the neck-in work
    as well.  Not sure how the two approaches compare in terms of render-time. 
    -ETJ 16 Mar 2011     
    
    outline_pts: a list of points (NOT an OpenSCAD polygon) that define the cross 
            section of the thread
            
    inner_rad: radius of cylinder the screw will wrap around
    pitch: height for one revolution; must be <= the height of outline_pts 
                    bounding box to avoid self-intersection
    length: distance from bottom-most point of screw to topmost
    external: if True, the cross-section is external to a cylinder. If False,
                    the segment is internal to it, and outline_pts will be
                    mirrored right-to-left
    segments_per_rot: segments per rotation
    neck_in_degrees: degrees through which the outer edge of the screw thread will move from 
                    a thickness of zero (inner_rad) to its full thickness
    neck_out_degrees: degrees through which outer edge of the screw thread will move from 
                    full thickness back to zero
                    
    NOTE: if pitch is less than the or equal to the height of each tooth (outline_pts), 
    OpenSCAD will likely crash, since the resulting screw would self-intersect 
    all over the place.  For screws with essentially no space between 
    threads, (i.e., pitch=tooth_height), I use pitch= tooth_height+EPSILON, 
    since pitch=tooth_height will self-intersect for rotations >=1
    '''
    a = union()
    rotations = float(length)/pitch
    
    total_angle = 360.0*rotations
    up_step = float(length) / (rotations*segments_per_rot)
    # Add one to total_steps so we have total_steps *segments*
    total_steps = int(ceil( rotations * segments_per_rot)) + 1
    step_angle = total_angle/ (total_steps -1)
    
    all_points = []
    all_tris = []
    euc_up = Vector3( *UP_VEC)
    poly_sides = len( outline_pts)
    
    # Figure out how wide the tooth profile is
    min_bb, max_bb = bounding_box( outline_pts)
    outline_w = max_bb[0] - min_bb[0]
    outline_h = max_bb[1] - min_bb[1]
    
    min_rad = max( 0, inner_rad-outline_w-EPSILON)    
    max_rad = inner_rad + outline_w + EPSILON
    
    # outline_pts, since they were created in 2D , are in the XY plane.
    # But spirals move a profile in XZ around the Z-axis.  So swap Y and Z
    # co-ords... and hope users know about this
    # Also add inner_rad to the profile
    euc_points = []
    for p in outline_pts:
        # If p is in [x, y] format, make it [x, y, 0]
        if len( p) == 2:
            p.append( 0)
        # [x, y, z] => [ x+inner_rad, z, y]
        external_mult = 1 if external else -1
        s =  Point3( external_mult*p[0], p[2], p[1]) # adding inner_rad, swapping Y & Z
        euc_points.append( s)
        
    for i in range( total_steps):
        angle = i*step_angle
        
        elevation = i*up_step
        if angle > total_angle:
            angle = total_angle
            elevation = length
        
        # Handle the neck-in radius for internal and external threads
        rad = inner_rad
        int_ext_mult = 1 if external else -1
        neck_in_rad = min_rad if external else max_rad
        
        if angle < neck_in_degrees:
            rad = neck_in_rad + int_ext_mult * angle / neck_in_degrees * outline_w
        elif angle > total_angle - neck_in_degrees:
            rad = neck_in_rad + int_ext_mult * (total_angle - angle)/neck_out_degrees * outline_w
        
        elev_vec = Vector3( rad, 0, elevation)
        
        # create new points
        for p in euc_points:
            pt = (p + elev_vec).rotate_around( axis=euc_up, theta=radians( angle))
            all_points.append( pt.as_arr())
        
        # Add the connectivity information
        if i < total_steps -1:
            ind = i*poly_sides
            for j in range( ind, ind + poly_sides - 1):
                all_tris.append( [ j, j+1,   j+poly_sides])
                all_tris.append( [ j+1, j+poly_sides+1, j+poly_sides])
            all_tris.append( [ ind, ind + poly_sides-1+poly_sides, ind + poly_sides-1])
            all_tris.append( [ ind, ind + poly_sides, ind +poly_sides-1+poly_sides])       
        
    # End triangle fans for beginning and end
    last_loop = len(all_points) - poly_sides
    for i in range( poly_sides -2):
        all_tris.append( [ 0,  i+2, i+1])
        all_tris.append( [ last_loop, last_loop + i+1, last_loop + i + 2])
        
        
    # Make the polyhedron
    a = polyhedron( points=all_points, triangles=all_tris)
    
    if external:
        # Intersect with a cylindrical tube to make sure we fit into
        # the correct dimensions
        tube = cylinder( r=inner_rad+outline_w+EPSILON, h=length, segments=segments_per_rot) 
        tube -= cylinder( r=inner_rad, h=length, segments=segments_per_rot)
    else:
        # If the threading is internal, intersect with a central cylinder 
        # to make sure nothing else remains
        tube = cylinder( r=inner_rad, h=length, segments=segments_per_rot)        
    a *= tube
    return render()(a)



def default_thread_section( tooth_height, tooth_depth):
    # An isoceles triangle, tooth_height vertically, tooth_depth wide:
    res = [ [ 0, -tooth_height/2],
             [ tooth_depth, 0],
             [ 0, tooth_height/2]
            ]
    return res


def assembly():
    # Scad code here
    a = union()
    
    rad = 5
    pts = [ [ 0, -1, 0],
            [ 1,  0, 0],
            [ 0,  1, 0],
            [ -1, 0, 0],
            [ -1, -1, 0]    ]
            
    a = thread( pts, inner_rad=10, pitch= 6, length=2, segments_per_rot=31, 
                            neck_in_degrees=30, neck_out_degrees=30)
    
    return a + cylinder( 10+EPSILON, 2)

if __name__ == '__main__':
    a = assembly()    
    scad_render_to_file( a)
########NEW FILE########
__FILENAME__ = solidpython
#! /usr/bin/python
# -*- coding: utf-8 -*-

#    Simple Python OpenSCAD Code Generator
#    Copyright (C) 2009    Philipp Tiefenbacher <wizards23@gmail.com>
#    Amendments & additions, (C) 2011 Evan Jones <evan_t_jones@mac.com>
#
#   License: LGPL 2.1 or later
#


import os, sys, re
import inspect

openscad_builtins = [
    # 2D primitives
    {'name': 'polygon',         'args': ['points', 'paths'], 'kwargs': []} ,
    {'name': 'circle',          'args': [],         'kwargs': ['r', 'segments']} ,
    {'name': 'square',          'args': [],         'kwargs': ['size', 'center']} ,
    
    # 3D primitives
    {'name': 'sphere',          'args': [],         'kwargs': ['r', 'segments']} ,
    {'name': 'cube',            'args': [],         'kwargs': ['size', 'center']} ,
    {'name': 'cylinder',        'args': [],         'kwargs': ['r','h','r1', 'r2', 'center', 'segments']}  ,
    {'name': 'polyhedron',      'args': ['points', 'triangles' ], 'kwargs': ['convexity']} ,
    
    # Boolean operations
    {'name': 'union',           'args': [],         'kwargs': []} ,
    {'name': 'intersection',    'args': [],         'kwargs': []} ,
    {'name': 'difference',      'args': [],         'kwargs': []} ,
    {'name': 'hole',           'args': [],         'kwargs': []} ,
    {'name': 'part',           'args': [],         'kwargs': []} ,
    
    # Transforms
    {'name': 'translate',       'args': [],         'kwargs': ['v']} ,
    {'name': 'scale',           'args': [],         'kwargs': ['v']} ,
    {'name': 'rotate',          'args': [],         'kwargs': ['a', 'v']} ,
    {'name': 'mirror',          'args': ['v'],      'kwargs': []},
    {'name': 'multmatrix',      'args': ['m'],      'kwargs': []},
    {'name': 'color',           'args': ['c'],      'kwargs': []},
    {'name': 'minkowski',       'args': [],         'kwargs': []},
    {'name': 'hull',            'args': [],         'kwargs': []},
    {'name': 'render',          'args': [],         'kwargs': ['convexity']}, 
        
    # 2D to 3D transitions
    {'name': 'linear_extrude',  'args': [],         'kwargs': ['height', 'center', 'convexity', 'twist','slices']} ,
    {'name': 'rotate_extrude',  'args': [],         'kwargs': ['convexity', 'segments']} ,
    {'name': 'dxf_linear_extrude', 'args': ['file'], 'kwargs': ['layer', 'height', 'center', 'convexity', 'twist', 'slices']} ,
    {'name': 'projection',      'args': [],         'kwargs': ['cut']} ,
    {'name': 'surface',         'args': ['file'],   'kwargs': ['center','convexity']} ,
    
    # Import/export
    {'name': 'import_stl',      'args': ['filename'], 'kwargs': ['convexity']} ,
    
    # Modifiers; These are implemented by calling e.g. 
    #   obj.set_modifier( '*') or 
    #   obj.set_modifier('disable') 
    #   disable( obj)
    # on  an existing object.
    # {'name': 'background',      'args': [],         'kwargs': []},     #   %{}
    # {'name': 'debug',           'args': [],         'kwargs': []} ,    #   #{}
    # {'name': 'root',            'args': [],         'kwargs': []} ,    #   !{}
    # {'name': 'disable',         'args': [],         'kwargs': []} ,    #   *{}
    
    {'name': 'intersection_for', 'args': ['n'],     'kwargs': []}  ,    #   e.g.: intersection_for( n=[1..6]){}
    
    # Unneeded
    {'name': 'assign',          'args': [],         'kwargs': []}   # Not really needed for Python.  Also needs a **args argument so it accepts anything
]

# Some functions need custom code in them; put that code here
builtin_literals = {
    'polygon': '''class polygon( openscad_object):
        def __init__( self, points, paths=None):
            if not paths:
                paths = [ range( len( points))]
            openscad_object.__init__( self, 'polygon', {'points':points, 'paths': paths})
        
            ''',
    'hole':'''class hole( openscad_object):
    def __init__( self):
        openscad_object.__init__( self, 'hole', {})
        self.set_hole( True)
    
    ''', 
    'part':'''class part( openscad_object):
    def __init__( self):
        openscad_object.__init__(self, 'part', {})
        self.set_part_root( True)
    '''

}
# These are features added to SolidPython but NOT in OpenSCAD. 
# Mark them for special treatment
non_rendered_classes = ['hole', 'part']

# ================================
# = Modifier Convenience Methods =
# ================================
def debug( openscad_obj):
    openscad_obj.set_modifier("#")
    return openscad_obj

def background( openscad_obj):
    openscad_obj.set_modifier("%")
    return openscad_obj

def root( openscad_obj):
    openscad_obj.set_modifier("!")
    return openscad_obj
    
def disable( openscad_obj):
    openscad_obj.set_modifier("*")
    return openscad_obj



# ===============
# = Including OpenSCAD code =
# =============== 

# use() & include() mimic OpenSCAD's use/include mechanics. 
# -- use() makes methods in scad_file_path.scad available to 
#   be called.
# --include() makes those methods available AND executes all code in
#   scad_file_path.scad, which may have side effects.  
#   Unless you have a specific need, call use(). 
def use( scad_file_path, use_not_include=True):
    '''
    TODO:  doctest needed
    '''
    # Opens scad_file_path, parses it for all usable calls, 
    # and adds them to caller's namespace
    try:
        module = open( scad_file_path)
        contents = module.read()
        module.close()
    except Exception, e:
        raise Exception( "Failed to import SCAD module '%(scad_file_path)s' with error: %(e)s "%vars())
    
    # Once we have a list of all callables and arguments, dynamically
    # add openscad_object subclasses for all callables to the calling module's
    # namespace.
    symbols_dicts = extract_callable_signatures( scad_file_path)
    
    for sd in symbols_dicts:
        class_str = new_openscad_class_str( sd['name'], sd['args'], sd['kwargs'], scad_file_path, use_not_include)
        # If this is called from 'include', we have to look deeper in the stack 
        # to find the right module to add the new class to.
        stack_depth = 2 if use_not_include else 3
        exec class_str in calling_module( stack_depth).__dict__
    
    return True

def include( scad_file_path):
    return use( scad_file_path, use_not_include=False)


# =========================================
# = Rendering Python code to OpenSCAD code=
# =========================================
def _find_include_strings( obj):
    include_strings = set()
    if isinstance( obj, included_openscad_object):
        include_strings.add( obj.include_string )
    for child in obj.children:
        include_strings.update( _find_include_strings( child))
    return include_strings

def scad_render( scad_object, file_header=''):
    # Make this object the root of the tree
    root = scad_object
    
    # Scan the tree for all instances of 
    # included_openscad_object, storing their strings
    include_strings = _find_include_strings( root)
    
    # and render the string
    includes = ''.join(include_strings) + "\n"
    scad_body = root._render()
    return file_header + includes + scad_body

def scad_render_animated_file( func_to_animate, steps=20, back_and_forth=True, filepath=None, file_header='', include_orig_code=True):
    # func_to_animate takes a single float argument, _time in [0, 1], and 
    # returns an openscad_object instance.
    #
    # Outputs an OpenSCAD file with func_to_animate() evaluated at "steps" 
    # points between 0 & 1, with time never evaluated at exactly 1
    
    # If back_and_forth is True, smoothly animate the full extent of the motion
    # and then reverse it to the beginning; this avoids skipping between beginning
    # and end of the animated motion
    
    # NOTE: This is a hacky way to solve a simple problem.  To use OpenSCAD's
    # animation feature, our code needs to respond to changes in the value
    # of the OpenSCAD variable $t, but I can't think of a way to get a 
    # float variable from our code and put it into the actual SCAD code. 
    # Instead, we just evaluate our code at each desired step, and write it
    # all out in the SCAD code for each case, with an if/else tree.  Depending
    # on the number of steps, this could create hundreds of times more SCAD
    # code than is needed.  But... it does work, with minimal Python code, so
    # here it is. Better solutions welcome. -ETJ 28 Mar 2013    
    
    # NOTE: information on the OpenSCAD manual wiki as of November 2012 implies
    # that the OpenSCAD app does its animation irregularly; sometimes it animates
    # one loop in steps iterations, and sometimes in (steps + 1).  Do it here
    # in steps iterations, meaning that we won't officially reach $t =1.
    
    # Note also that we check for ranges of time rather than equality; this
    # should avoid any rounding error problems, and doesn't require the file
    # to be animated with an identical number of steps to the way it was 
    # created. -ETJ 28 Mar 2013
    scad_obj = func_to_animate()
    include_strings = _find_include_strings( scad_obj)    
    # and render the string
    includes = ''.join(include_strings) + "\n"    

    rendered_string = file_header + includes
    
    if back_and_forth: 
        steps *= 2

    for i in range( steps):
        time = i *1.0/steps
        end_time = (i+1)*1.0/steps
        eval_time = time
        # Looping back and forth means there's no jump between the start and 
        # end position
        if back_and_forth:
            if time < 0.5:
                eval_time = time * 2
            else:
                eval_time = 2 - 2*time
        scad_obj = func_to_animate( _time=eval_time)   
        
        scad_str = indent( scad_obj._render())         
        rendered_string += (  "if ($t >= %(time)s && $t < %(end_time)s){"
                        "   %(scad_str)s\n"     
                        "}\n"%vars())
    
    # TODO: Remove code duplication from here to end of method: taken 
    # from scad_render_to_file(). -ETJ 28 Mar 2013
    calling_file = os.path.abspath( calling_module().__file__) 
    
    if include_orig_code:
        rendered_string += sp_code_in_scad_comment( calling_file)
    
    # This write is destructive, and ought to do some checks that the write
    # was successful.
    # If filepath isn't supplied, place a .scad file with the same name
    # as the calling module next to it
    if not filepath:
        filepath = os.path.splitext( calling_file)[0] + '.scad'
    
    f = open( filepath,"w")
    f.write( rendered_string)
    f.close()

def scad_render_to_file( scad_object, filepath=None, file_header='', include_orig_code=True):
    rendered_string = scad_render( scad_object, file_header)
    
    try:
        calling_file = os.path.abspath( calling_module().__file__) 
    
        if include_orig_code:
            rendered_string += sp_code_in_scad_comment( calling_file)
    
        # This write is destructive, and ought to do some checks that the write
        # was successful.
        # If filepath isn't supplied, place a .scad file with the same name
        # as the calling module next to it
        if not filepath:
            filepath = os.path.splitext( calling_file)[0] + '.scad'
    except AttributeError, e:
        # If no calling_file was found, this is being called from the terminal.
        # We can't read original code from a file, so don't try, 
        # and can't read filename from the calling file either, so just save to
        # solid.scad.
        if not filepath:
            filepath = os.path.abspath('.') + "/solid.scad"
        
    f = open( filepath,"w")
    f.write( rendered_string)
    f.close()

def sp_code_in_scad_comment( calling_file):
    # Once a SCAD file has been created, it's difficult to reconstruct
    # how it got there, since it has no variables, modules, etc.  So, include
    # the Python code that generated the scad code as comments at the end of 
    # the SCAD code    
    pyopenscad_str = open(calling_file, 'r').read()

    # TODO: optimally, this would also include a version number and
    # git hash (& date & github URL?) for the version of solidpython used 
    # to create a given file; That would future-proof any given SP-created
    # code because it would point to the relevant dependencies as well as 
    # the actual code
    pyopenscad_str = ("\n"
        "/***********************************************\n"
        "******      SolidPython code:      *************\n"
        "************************************************\n"
        " \n"
        "%(pyopenscad_str)s \n"
        " \n"
        "***********************************************/\n")%vars()     
    return pyopenscad_str



# =========================
# = Internal Utilities    =
# =========================
class openscad_object( object):
    def __init__(self, name, params):
        self.name = name
        self.params = params
        self.children = []
        self.modifier = ""
        self.parent= None
        self.is_hole = False
        self.has_hole_children = False
        self.is_part_root = False
    
    def set_hole( self, is_hole=True):
        self.is_hole = is_hole
        return self
    
    def set_part_root( self, is_root=True):
        self.is_part_root = is_root
        return self
    
    def find_hole_children( self, path=None):
        # Because we don't force a copy every time we re-use a node
        # (e.g a = cylinder(2, 6);  b = right( 10) (a)          
        #  the identical 'a' object appears in the tree twice),
        # we can't count on an object's 'parent' field to trace its
        # path to the root.  Instead, keep track explicitly
        path = path if path else [self]
        hole_kids = []

        for child in self.children:
            path.append( child)
            if child.is_hole:
                hole_kids.append( child)
                # Mark all parents as having a hole child
                for p in path:
                    p.has_hole_children = True
            # Don't append holes from separate parts below us                   
            elif child.is_part_root:
                continue
            # Otherwise, look below us for children
            else:
                hole_kids += child.find_hole_children( path)
            path.pop( )
        
        return hole_kids
        
        
    def set_modifier(self, m):
        # Used to add one of the 4 single-character modifiers: #(debug)  !(root) %(background) or *(disable)
        string_vals = { 'disable':      '*',
                        'debug':        '#',
                        'background':   '%',
                        'root':         '!',
                        '*':'*',
                        '#':'#',
                        '%':'%',
                        '!':'!'}
         
        self.modifier = string_vals.get(m.lower(), '')
        return self
    
    def _render(self, render_holes=False):
        '''
        NOTE: In general, you won't want to call this method. For most purposes,
        you really want scad_render(), 
        Calling obj._render won't include necessary 'use' or 'include' statements
        '''      
        # First, render all children
        s = ""
        for child in self.children:
            # Don't immediately render hole children.
            # Add them to the parent's hole list,
            # And render after everything else
            if not render_holes and child.is_hole:
                continue
            s += child._render( render_holes)
                
        # Then render self and prepend/wrap it around the children
        # I've added designated parts and explicit holes to SolidPython.
        # OpenSCAD has neither, so don't render anything from these objects                
        if self.name in non_rendered_classes:
            pass
        elif not self.children:
            s = self._render_str_no_children() + ";"
        else:
            s = self._render_str_no_children() + " {" + indent( s) + "\n}"
            
        # If this is the root object or the top of a separate part,
        # find all holes and subtract them after all positive geometry
        # is rendered
        if (not self.parent) or self.is_part_root:
            hole_children = self.find_hole_children()
            
            if len(hole_children) > 0:
                s += "\n/* Holes Below*/"
                s += self._render_hole_children()
                
                # wrap everything in the difference
                s = "\ndifference(){" + indent(s) + " /* End Holes */ \n}"
        return s
    
    def _render_str_no_children( self):
        s = "\n" + self.modifier + self.name + "("
        first = True
            
        # OpenSCAD doesn't have a 'segments' argument, but it does 
        # have '$fn'.  Swap one for the other
        if 'segments' in self.params:
            self.params['$fn'] = self.params.pop('segments')
            
        valid_keys = self.params.keys()
            
        # intkeys are the positional parameters
        intkeys = filter(lambda x: type(x)==int, valid_keys)
        intkeys.sort()
        
        # named parameters
        nonintkeys = filter(lambda x: not type(x)==int, valid_keys)
        
        for k in intkeys+nonintkeys:
            v = self.params[k]
            if v == None:
                continue
            
            if not first:
                s += ", "
            first = False
            
            if type(k)==int:
                s += py2openscad(v)
            else:
                s += k + " = " + py2openscad(v)
                
        s += ")"
        return s
    def _render_hole_children( self):
        # Run down the tree, rendering only those nodes
        # that are holes or have holes beneath them
        if not self.has_hole_children:
            return ""
        s = ""    
        for child in self.children:
            if child.is_hole:
                s += child._render( render_holes=True)
            elif child.has_hole_children:
                # Holes exist in the compiled tree in two pieces:
                # The shapes of the holes themselves, ( an object for which
                # obj.is_hole is True, and all its children) and the 
                # transforms necessary to put that hole in place, which
                # are inherited from non-hole geometry.
                
                # Non-hole Intersections & differences can change (shrink) 
                # the size of holes, and that shouldn't happen: an 
                # intersection/difference with an empty space should be the
                # entirety of the empty space.
                #  In fact, the intersection of two empty spaces should be
                # everything contained in both of them:  their union.
                # So... replace all super-hole intersection/diff transforms
                # with union in the hole segment of the compiled tree.
                # And if you figure out a better way to explain this, 
                # please, please do... because I think this works, but I
                # also think my rationale is shaky and imprecise. -ETJ 19 Feb 2013
                s = s.replace( "intersection", "union")
                s = s.replace( "difference", "union")
                s += child._render_hole_children()
        if self.name in non_rendered_classes:
            pass
        else:
            s = self._render_str_no_children() + "{" + indent( s) + "\n}"
        return s
    
    def add(self, child):
        '''
        if child is a single object, assume it's an openscad_object and 
        add it to self.children
        
        if child is a list, assume its members are all openscad_objects and
        add them all to self.children
        '''
        if isinstance( child, (list, tuple)):
            # __call__ passes us a list inside a tuple, but we only care
            # about the list, so skip single-member tuples containing lists
            if len( child) == 1 and isinstance(child[0], (list, tuple)):
                child = child[0]
            [self.add( c ) for c in child]
        else:
            self.children.append( child)
            child.set_parent( self)
        return self
    
    def set_parent( self, parent):
        self.parent = parent
    
    def add_param(self, k, v):
        self.params[k] = v
        return self
    
    def copy( self):
        # Provides a copy of this object and all children, 
        # but doesn't copy self.parent, meaning the new object belongs
        # to a different tree
        # If we're copying a scad object, we know it is an instance of 
        # a dynamically created class called self.name.  
        # Initialize an instance of that class with the same params
        # that created self, the object being copied.
        
        # Python can't handle an '$fn' argument, while openSCAD only wants
        # '$fn'.  Swap back and forth as needed; the final renderer will
        # sort this out. 
        if '$fn' in self.params:
            self.params['segments'] = self.params.pop('$fn')
        
        other = globals()[ self.name]( **self.params)
        other.set_modifier( self.modifier)
        other.set_hole( self.is_hole)
        other.set_part_root( self.is_part_root)
        other.has_hole_children = self.has_hole_children
        for c in self.children:
            other.add( c.copy())
        return other
    
    def __call__( self, *args):
        '''
        Adds all objects in args to self.  This enables OpenSCAD-like syntax,
        e.g.:
        union()(
            cube(),
            sphere()
        )
        '''
        return self.add(args)
    
    def __add__(self, x):
        '''
        This makes u = a+b identical to:
        u = union()( a, b )
        '''
        return union()(self, x)
    
    def __sub__(self, x):
        '''
        This makes u = a - b identical to:
        u = difference()( a, b )
        '''        
        return difference()(self, x)
    
    def __mul__(self, x):
        '''
        This makes u = a * b identical to:
        u = intersection()( a, b )
        '''        
        return intersection()(self, x)
    

class included_openscad_object( openscad_object):
    '''
    Identical to openscad_object, but each subclass of included_openscad_object
    represents imported scad code, so each instance needs to store the path
    to the scad file it's included from.
    '''
    def __init__( self, name, params, include_file_path, use_not_include=False, **kwargs):
        self.include_file_path = self._get_include_path( include_file_path)
                    
        if use_not_include:
            self.include_string = 'use <%s>\n'%self.include_file_path
        else:
            self.include_string = 'include <%s>\n'%self.include_file_path
        
        # Just pass any extra arguments straight on to OpenSCAD; it'll accept them
        if kwargs:
            params.update( kwargs)

        openscad_object.__init__( self, name, params)
    
    def _get_include_path( self, include_file_path):
        # Look through sys.path for anyplace we can find a valid file ending
        # in include_file_path.  Return that absolute path
        if os.path.isabs( include_file_path): 
            return include_file_path
        else:
            for p in sys.path:       
                whole_path = os.path.join( p, include_file_path)
                if os.path.isfile( whole_path):
                    return os.path.abspath(whole_path)
            
        # No loadable SCAD file was found in sys.path.  Raise an error
        raise( ValueError, "Unable to find included SCAD file: "
                            "%(include_file_path)s in sys.path"%vars())
    

def calling_module( stack_depth=2):
    '''
    Returns the module *2* back in the frame stack.  That means:
    code in module A calls code in module B, which asks calling_module()
    for module A.
    
    This means that we have to know exactly how far back in the stack
    our desired module is; if code in module B calls another function in 
    module B, we have to increase the stack_depth argument to account for
    this.
    
    Got that?
    '''
    frm = inspect.stack()[stack_depth]
    calling_mod = inspect.getmodule( frm[0])
    return calling_mod

def new_openscad_class_str( class_name, args=[], kwargs=[], include_file_path=None, use_not_include=True):
    args_str = ''
    args_pairs = ''
    
    for arg in args:
        args_str += ', '+arg
        args_pairs += "'%(arg)s':%(arg)s, "%vars()
        
    # kwargs have a default value defined in their SCAD versions.  We don't 
    # care what that default value will be (SCAD will take care of that), just
    # that one is defined.
    for kwarg in kwargs:
        args_str += ', %(kwarg)s=None'%vars()
        args_pairs += "'%(kwarg)s':%(kwarg)s, "%vars()
    
    if include_file_path:
        # NOTE the explicit import of 'solid' below. This is a fix for:
        # https://github.com/SolidCode/SolidPython/issues/20 -ETJ 16 Jan 2014
        result = ("import solid\n"
        "class %(class_name)s( solid.included_openscad_object):\n"
        "   def __init__(self%(args_str)s, **kwargs):\n"
        "       solid.included_openscad_object.__init__(self, '%(class_name)s', {%(args_pairs)s }, include_file_path='%(include_file_path)s', use_not_include=%(use_not_include)s, **kwargs )\n"
        "   \n"
        "\n"%vars())
    else:
        result = ("class %(class_name)s( openscad_object):\n"
        "   def __init__(self%(args_str)s):\n"
        "       openscad_object.__init__(self, '%(class_name)s', {%(args_pairs)s })\n"
        "   \n"
        "\n"%vars())
                
    return result

def py2openscad(o):
    if type(o) == bool:
        return str(o).lower()
    if type(o) == float:
        return "%.10f" % o
    if type(o) == list or type(o) == tuple:
        s = "["
        first = True
        for i in o:
            if not first:
                s +=    ", "
            first = False
            s += py2openscad(i)
        s += "]"
        return s
    if type(o) == str:
        return '"' + o + '"'
    return str(o)

def indent(s):
    return s.replace("\n", "\n\t")


# ===========
# = Parsing =
# ===========
def extract_callable_signatures( scad_file_path):
    scad_code_str = open(scad_file_path).read()
    return parse_scad_callables( scad_code_str)

def parse_scad_callables( scad_code_str): 
    callables = []
    
    # Note that this isn't comprehensive; tuples or nested data structures in 
    # a module definition will defeat it.  
    
    # Current implementation would throw an error if you tried to call a(x, y) 
    # since Python would expect a( x);  OpenSCAD itself ignores extra arguments, 
    # but that's not really preferable behavior 
    
    # TODO:  write a pyparsing grammar for OpenSCAD, or, even better, use the yacc parse grammar
    # used by the language itself.  -ETJ 06 Feb 2011   
           
    no_comments_re = r'(?mxs)(//.*?\n|/\*.*?\*/)'
    
    # Also note: this accepts: 'module x(arg) =' and 'function y(arg) {', both of which are incorrect syntax
    mod_re  = r'(?mxs)^\s*(?:module|function)\s+(?P<callable_name>\w+)\s*\((?P<all_args>.*?)\)\s*(?:{|=)'
    
    # This is brittle.  To get a generally applicable expression for all arguments,
    # we'd need a real parser to handle nested-list default args or parenthesized statements.  
    # For the moment, assume a maximum of one square-bracket-delimited list 
    args_re = r'(?mxs)(?P<arg_name>\w+)(?:\s*=\s*(?P<default_val>[\w.-]+|\[.*\]))?(?:,|$)'
             
    # remove all comments from SCAD code
    scad_code_str = re.sub(no_comments_re,'', scad_code_str)
    # get all SCAD callables
    mod_matches = re.finditer( mod_re, scad_code_str)
    
    for m in mod_matches:
        callable_name = m.group('callable_name')
        args = []
        kwargs = []        
        all_args = m.group('all_args')
        if all_args:
            arg_matches = re.finditer( args_re, all_args)
            for am in arg_matches:
                arg_name = am.group('arg_name')
                if am.group('default_val'):
                    kwargs.append( arg_name)
                else:
                    args.append( arg_name)
        
        callables.append( { 'name':callable_name, 'args': args, 'kwargs':kwargs})
        
    return callables


# Dynamically add all builtins to this namespace on import
for sym_dict in openscad_builtins:
    # entries in 'builtin_literals' override the entries in 'openscad_builtins'
    if sym_dict['name'] in builtin_literals:
        class_str = builtin_literals[ sym_dict['name']]
    else:
        class_str = new_openscad_class_str( sym_dict['name'], sym_dict['args'], sym_dict['kwargs'])
    
    exec class_str 
    

########NEW FILE########
__FILENAME__ = test_screw_thread
#! /usr/bin/python
# -*- coding: UTF-8 -*-
from __future__ import division
import os, sys, re

# Assumes SolidPython is in site-packages or elsewhwere in sys.path
import unittest
from solid import *
from solid.screw_thread import thread, default_thread_section

SEGMENTS = 8
class TestScrewThread( unittest.TestCase):
    def test_thread( self):
        tooth_height = 10
        tooth_depth = 5
        outline = default_thread_section( tooth_height=tooth_height, tooth_depth=tooth_depth)
        actual_obj = thread( outline_pts=outline, inner_rad=20, pitch=tooth_height, 
                            length=0.75*tooth_height, segments_per_rot=SEGMENTS,
                            neck_in_degrees=45, neck_out_degrees=45)
        actual = scad_render( actual_obj)
        expected = '\n\nrender() {\n\tintersection() {\n\t\tpolyhedron(points = [[14.9900000000, 0.0000000000, -5.0000000000], [19.9900000000, 0.0000000000, 0.0000000000], [14.9900000000, 0.0000000000, 5.0000000000], [14.1421356237, 14.1421356237, -3.7500000000], [17.6776695297, 17.6776695297, 1.2500000000], [14.1421356237, 14.1421356237, 6.2500000000], [0.0000000000, 20.0000000000, -2.5000000000], [0.0000000000, 25.0000000000, 2.5000000000], [0.0000000000, 20.0000000000, 7.5000000000], [-14.1421356237, 14.1421356237, -1.2500000000], [-17.6776695297, 17.6776695297, 3.7500000000], [-14.1421356237, 14.1421356237, 8.7500000000], [-20.0000000000, 0.0000000000, 0.0000000000], [-25.0000000000, 0.0000000000, 5.0000000000], [-20.0000000000, 0.0000000000, 10.0000000000], [-14.1421356237, -14.1421356237, 1.2500000000], [-17.6776695297, -17.6776695297, 6.2500000000], [-14.1421356237, -14.1421356237, 11.2500000000], [-0.0000000000, -14.9900000000, 2.5000000000], [-0.0000000000, -19.9900000000, 7.5000000000], [-0.0000000000, -14.9900000000, 12.5000000000]], triangles = [[0, 1, 3], [1, 4, 3], [1, 2, 4], [2, 5, 4], [0, 5, 2], [0, 3, 5], [3, 4, 6], [4, 7, 6], [4, 5, 7], [5, 8, 7], [3, 8, 5], [3, 6, 8], [6, 7, 9], [7, 10, 9], [7, 8, 10], [8, 11, 10], [6, 11, 8], [6, 9, 11], [9, 10, 12], [10, 13, 12], [10, 11, 13], [11, 14, 13], [9, 14, 11], [9, 12, 14], [12, 13, 15], [13, 16, 15], [13, 14, 16], [14, 17, 16], [12, 17, 14], [12, 15, 17], [15, 16, 18], [16, 19, 18], [16, 17, 19], [17, 20, 19], [15, 20, 17], [15, 18, 20], [0, 2, 1], [18, 19, 20]]);\n\t\tdifference() {\n\t\t\tcylinder($fn = 8, h = 7.5000000000, r = 25.0100000000);\n\t\t\tcylinder($fn = 8, h = 7.5000000000, r = 20);\n\t\t}\n\t}\n}'
        self.assertEqual( expected, actual)
    
    def test_thread_internal( self):
        tooth_height = 10
        tooth_depth = 5
        outline = default_thread_section( tooth_height=tooth_height, tooth_depth=tooth_depth)
        actual_obj = thread( outline_pts=outline, inner_rad=20, pitch=2*tooth_height, 
                                length=2*tooth_height, segments_per_rot=SEGMENTS,
                                neck_in_degrees=45, neck_out_degrees=45,
                                external=False)
        actual = scad_render( actual_obj)
        expected = '\n\nrender() {\n\tintersection() {\n\t\tpolyhedron(points = [[25.0100000000, 0.0000000000, -5.0000000000], [20.0100000000, 0.0000000000, 0.0000000000], [25.0100000000, 0.0000000000, 5.0000000000], [14.1421356237, 14.1421356237, -2.5000000000], [10.6066017178, 10.6066017178, 2.5000000000], [14.1421356237, 14.1421356237, 7.5000000000], [0.0000000000, 20.0000000000, 0.0000000000], [0.0000000000, 15.0000000000, 5.0000000000], [0.0000000000, 20.0000000000, 10.0000000000], [-14.1421356237, 14.1421356237, 2.5000000000], [-10.6066017178, 10.6066017178, 7.5000000000], [-14.1421356237, 14.1421356237, 12.5000000000], [-20.0000000000, 0.0000000000, 5.0000000000], [-15.0000000000, 0.0000000000, 10.0000000000], [-20.0000000000, 0.0000000000, 15.0000000000], [-14.1421356237, -14.1421356237, 7.5000000000], [-10.6066017178, -10.6066017178, 12.5000000000], [-14.1421356237, -14.1421356237, 17.5000000000], [-0.0000000000, -20.0000000000, 10.0000000000], [-0.0000000000, -15.0000000000, 15.0000000000], [-0.0000000000, -20.0000000000, 20.0000000000], [14.1421356237, -14.1421356237, 12.5000000000], [10.6066017178, -10.6066017178, 17.5000000000], [14.1421356237, -14.1421356237, 22.5000000000], [25.0100000000, -0.0000000000, 15.0000000000], [20.0100000000, -0.0000000000, 20.0000000000], [25.0100000000, -0.0000000000, 25.0000000000]], triangles = [[0, 1, 3], [1, 4, 3], [1, 2, 4], [2, 5, 4], [0, 5, 2], [0, 3, 5], [3, 4, 6], [4, 7, 6], [4, 5, 7], [5, 8, 7], [3, 8, 5], [3, 6, 8], [6, 7, 9], [7, 10, 9], [7, 8, 10], [8, 11, 10], [6, 11, 8], [6, 9, 11], [9, 10, 12], [10, 13, 12], [10, 11, 13], [11, 14, 13], [9, 14, 11], [9, 12, 14], [12, 13, 15], [13, 16, 15], [13, 14, 16], [14, 17, 16], [12, 17, 14], [12, 15, 17], [15, 16, 18], [16, 19, 18], [16, 17, 19], [17, 20, 19], [15, 20, 17], [15, 18, 20], [18, 19, 21], [19, 22, 21], [19, 20, 22], [20, 23, 22], [18, 23, 20], [18, 21, 23], [21, 22, 24], [22, 25, 24], [22, 23, 25], [23, 26, 25], [21, 26, 23], [21, 24, 26], [0, 2, 1], [24, 25, 26]]);\n\t\tcylinder($fn = 8, h = 20, r = 20);\n\t}\n}'
        self.assertEqual( expected, actual)        
        
    def test_default_thread_section( self):
        expected = [[0, -5], [5, 0], [0, 5]]
        actual = default_thread_section( tooth_height=10, tooth_depth=5)
        self.assertEqual( expected, actual)
    


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_solidpython
#! /usr/bin/python
# -*- coding: UTF-8 -*-
import os, sys, re

import unittest
import tempfile
from solid import *

scad_test_case_templates = [
{'name': 'polygon',     'kwargs': {'paths': [[0, 1, 2]]}, 'expected': '\n\npolygon(paths = [[0, 1, 2]], points = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]);', 'args': {'points': [[0, 0, 0], [1, 0, 0], [0, 1, 0]]}, },
{'name': 'circle',      'kwargs': {'segments': 12, 'r': 1}, 'expected': '\n\ncircle(r = 1, $fn = 12);', 'args': {}, },
{'name': 'square',      'kwargs': {'center': False, 'size': 1}, 'expected': '\n\nsquare(center = false, size = 1);', 'args': {}, },
{'name': 'sphere',      'kwargs': {'segments': 12, 'r': 1}, 'expected': '\n\nsphere(r = 1, $fn = 12);', 'args': {}, },
{'name': 'cube',        'kwargs': {'center': False, 'size': 1}, 'expected': '\n\ncube(center = false, size = 1);', 'args': {}, },
{'name': 'cylinder',    'kwargs': {'r1': None, 'r2': None, 'h': 1, 'segments': 12, 'r': 1, 'center': False}, 'expected': '\n\ncylinder($fn = 12, h = 1, r = 1, center = false);', 'args': {}, },
{'name': 'polyhedron',  'kwargs': {'convexity': None}, 'expected': '\n\npolyhedron(points = [[0, 0, 0], [1, 0, 0], [0, 1, 0]], triangles = [[0, 1, 2]]);', 'args': {'points': [[0, 0, 0], [1, 0, 0], [0, 1, 0]], 'triangles': [[0, 1, 2]]}, },
{'name': 'union',       'kwargs': {}, 'expected': '\n\nunion();', 'args': {}, },
{'name': 'intersection','kwargs': {}, 'expected': '\n\nintersection();', 'args': {}, },
{'name': 'difference',  'kwargs': {}, 'expected': '\n\ndifference();', 'args': {}, },
{'name': 'translate',   'kwargs': {'v': [1, 0, 0]}, 'expected': '\n\ntranslate(v = [1, 0, 0]);', 'args': {}, },
{'name': 'scale',       'kwargs': {'v': 0.5}, 'expected': '\n\nscale(v = 0.5000000000);', 'args': {}, },
{'name': 'rotate',      'kwargs': {'a': 45, 'v': [0, 0, 1]}, 'expected': '\n\nrotate(a = 45, v = [0, 0, 1]);', 'args': {}, },
{'name': 'mirror',      'kwargs': {}, 'expected': '\n\nmirror(v = [0, 0, 1]);', 'args': {'v': [0, 0, 1]}, },
{'name': 'multmatrix',  'kwargs': {}, 'expected': '\n\nmultmatrix(m = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]);', 'args': {'m': [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]}, },
{'name': 'color',       'kwargs': {}, 'expected': '\n\ncolor(c = [1, 0, 0]);', 'args': {'c': [1, 0, 0]}, },
{'name': 'minkowski',   'kwargs': {}, 'expected': '\n\nminkowski();', 'args': {}, },
{'name': 'hull',        'kwargs': {}, 'expected': '\n\nhull();', 'args': {}, },
{'name': 'render',      'kwargs': {'convexity': None}, 'expected': '\n\nrender();', 'args': {}, },
{'name': 'projection',  'kwargs': {'cut': None}, 'expected': '\n\nprojection();', 'args': {}, },
{'name': 'surface',     'kwargs': {'center': False, 'convexity': None}, 'expected': '\n\nsurface(center = false, file = "/Path/to/dummy.dxf");', 'args': {'file': "'/Path/to/dummy.dxf'"}, },
{'name': 'import_stl',  'kwargs': {'convexity': None}, 'expected': '\n\nimport_stl(filename = "/Path/to/dummy.dxf");', 'args': {'filename': "'/Path/to/dummy.dxf'"}, },
{'name': 'linear_extrude',      'kwargs': {'twist': None, 'slices': None, 'center': False, 'convexity': None, 'height': 1}, 'expected': '\n\nlinear_extrude(center = false, height = 1);', 'args': {}, },
{'name': 'rotate_extrude',      'kwargs': {'convexity': None}, 'expected': '\n\nrotate_extrude();', 'args': {}, },
{'name': 'dxf_linear_extrude',  'kwargs': {'layer': None, 'center': False, 'slices': None, 'height': 1, 'twist': None, 'convexity': None}, 'expected': '\n\ndxf_linear_extrude(center = false, height = 1, file = "/Path/to/dummy.dxf");', 'args': {'file': "'/Path/to/dummy.dxf'"}, },
{'name': 'intersection_for',    'kwargs': {}, 'expected': '\n\nintersection_for(n = [0, 1, 2]);', 'args': {'n': [0, 1, 2]}, },
]

class TestSolidPython( unittest.TestCase):
    # test cases will be dynamically added to this instance
    def test_infix_union( self):
        a = cube(2)
        b = sphere( 2)
        expected = '\n\nunion() {\n\tcube(size = 2);\n\tsphere(r = 2);\n}'
        actual = scad_render( a+b)
        self.assertEqual( expected, actual)
    
    def test_infix_difference( self):
        a = cube(2)
        b = sphere( 2)
        expected = '\n\ndifference() {\n\tcube(size = 2);\n\tsphere(r = 2);\n}'
        actual = scad_render( a-b)
        self.assertEqual( expected, actual)
    
    def test_infix_intersection( self):
        a = cube(2)
        b = sphere( 2)
        expected = '\n\nintersection() {\n\tcube(size = 2);\n\tsphere(r = 2);\n}'
        actual = scad_render( a*b)
        self.assertEqual( expected, actual)
    
    def test_parse_scad_callables( self):
        test_str = (""
        "module hex (width=10, height=10,    \n"
        "            flats= true, center=false){}\n"
        "function righty (angle=90) = 1;\n"
        "function lefty( avar) = 2;\n"
        "module more( a=[something, other]) {}\n"
        "module pyramid(side=10, height=-1, square=false, centerHorizontal=true, centerVertical=false){}\n"
        "module no_comments( arg=10,   //test comment\n"
        "other_arg=2, /* some extra comments\n"
        "on empty lines */\n"
        "last_arg=4){}\n"
        "module float_arg( arg=1.0){}\n")
        expected = [{'args': [], 'name': 'hex', 'kwargs': ['width', 'height', 'flats', 'center']}, {'args': [], 'name': 'righty', 'kwargs': ['angle']}, {'args': ['avar'], 'name': 'lefty', 'kwargs': []}, {'args': [], 'name': 'more', 'kwargs': ['a']}, {'args': [], 'name': 'pyramid', 'kwargs': ['side', 'height', 'square', 'centerHorizontal', 'centerVertical']}, {'args': [], 'name': 'no_comments', 'kwargs': ['arg', 'other_arg', 'last_arg']}, {'args': [], 'name': 'float_arg', 'kwargs': ['arg']}]
        actual = parse_scad_callables( test_str)
        self.assertEqual( expected, actual)
        
    def test_use( self):
        include_file = "../examples/scad_to_include.scad"
        use( include_file)
        a = steps(3)
        actual = scad_render( a)
        
        abs_path = a._get_include_path( include_file)        
        expected = "use <%s>\n\n\nsteps(howmany = 3);"%abs_path
        self.assertEqual( expected, actual)     
        
    def test_include( self):
        include_file = "../examples/scad_to_include.scad"
        include( include_file)
        a = steps(3)
        
        actual = scad_render( a)
        abs_path = a._get_include_path( include_file)        
        expected = "include <%s>\n\n\nsteps(howmany = 3);"%abs_path
        self.assertEqual( expected, actual)        
    
    def test_extra_args_to_included_scad( self):
        include_file = "../examples/scad_to_include.scad"
        use( include_file)
        a = steps( 3, external_var=True)
        actual = scad_render( a)
        
        abs_path = a._get_include_path( include_file)        
        expected = "use <%s>\n\n\nsteps(howmany = 3, external_var = true);"%abs_path
        self.assertEqual( expected, actual)         
    
    def test_background( self):
        a = cube(10)
        expected = '\n\n%cube(size = 10);'
        actual = scad_render( background( a))
        self.assertEqual( expected, actual)
    
    def test_debug( self):
        a = cube(10)
        expected =  '\n\n#cube(size = 10);'
        actual = scad_render( debug( a))
        self.assertEqual( expected, actual)
    
    def test_disable( self):
        a = cube(10)
        expected =  '\n\n*cube(size = 10);'
        actual = scad_render( disable( a))
        self.assertEqual( expected, actual)
    
    def test_root( self):
        a = cube(10)
        expected = '\n\n!cube(size = 10);'
        actual = scad_render( root( a))
        self.assertEqual( expected, actual)
    
    def test_explicit_hole( self):
        a = cube( 10, center=True) + hole()( cylinder(2, 20, center=True))        
        expected = '\n\ndifference(){\n\tunion() {\n\t\tcube(center = true, size = 10);\n\t}\n\t/* Holes Below*/\n\tunion(){\n\t\tcylinder(h = 20, r = 2, center = true);\n\t} /* End Holes */ \n}'
        actual = scad_render( a)
        self.assertEqual( expected, actual)
    
    def test_hole_transform_propagation( self):
        # earlier versions of holes had problems where a hole
        # that was used a couple places wouldn't propagate correctly.
        # Confirm that's still happening as it's supposed to
        h = hole()( 
                rotate( a=90, v=[0, 1, 0])( 
                    cylinder(2, 20, center=True)
                )
            )
    
        h_vert = rotate( a=-90, v=[0, 1, 0])(
                    h
                )
    
        a = cube( 10, center=True) + h + h_vert
        expected = '\n\ndifference(){\n\tunion() {\n\t\tunion() {\n\t\t\tcube(center = true, size = 10);\n\t\t}\n\t\trotate(a = -90, v = [0, 1, 0]) {\n\t\t}\n\t}\n\t/* Holes Below*/\n\tunion(){\n\t\tunion(){\n\t\t\trotate(a = 90, v = [0, 1, 0]) {\n\t\t\t\tcylinder(h = 20, r = 2, center = true);\n\t\t\t}\n\t\t}\n\t\trotate(a = -90, v = [0, 1, 0]){\n\t\t\trotate(a = 90, v = [0, 1, 0]) {\n\t\t\t\tcylinder(h = 20, r = 2, center = true);\n\t\t\t}\n\t\t}\n\t} /* End Holes */ \n}'
        actual = scad_render( a)
        self.assertEqual( expected, actual)


    def test_separate_part_hole( self):
        # Make two parts, a block with hole, and a cylinder that 
        # fits inside it.  Make them separate parts, meaning
        # holes will be defined at the level of the part_root node,
        # not the overall node.  This allows us to preserve holes as
        # first class space, but then to actually fill them in with 
        # the parts intended to fit in them.
        b = cube( 10, center=True)
        c = cylinder( r=2, h=12, center=True)
        p1 = b - hole()(c)
        
        # Mark this cube-with-hole as a separate part from the cylinder
        p1 = part()(p1)
        
        # This fits in the hole.  If p1 is set as a part_root, it will all appear.
        # If not, the portion of the cylinder inside the cube will not appear,
        # since it would have been removed by the hole in p1
        p2 = cylinder( r=1.5, h=14, center=True)
        
        a = p1 + p2
        
        expected = '\n\nunion() {\n\tdifference(){\n\t\tdifference() {\n\t\t\tcube(center = true, size = 10);\n\t\t}\n\t\t/* Holes Below*/\n\t\tdifference(){\n\t\t\tcylinder(h = 12, r = 2, center = true);\n\t\t} /* End Holes */ \n\t}\n\tcylinder(h = 14, r = 1.5000000000, center = true);\n}'
        actual = scad_render( a)
        self.assertEqual( expected, actual)
    
    def test_scad_render_animated_file( self):
        def my_animate( _time=0):
            import math
            # _time will range from 0 to 1, not including 1
            rads = _time * 2 * math.pi
            rad = 15
            c = translate( [rad*math.cos(rads), rad*math.sin(rads)])( square( 10))
            return c
        tmp = tempfile.NamedTemporaryFile()
        
        scad_render_animated_file( my_animate, steps=2, back_and_forth=False, 
                filepath=tmp.name, include_orig_code=False)
        tmp.seek(0)
        actual = tmp.read()
        expected = '\nif ($t >= 0.0 && $t < 0.5){   \n\ttranslate(v = [15.0000000000, 0.0000000000]) {\n\t\tsquare(size = 10);\n\t}\n}\nif ($t >= 0.5 && $t < 1.0){   \n\ttranslate(v = [-15.0000000000, 0.0000000000]) {\n\t\tsquare(size = 10);\n\t}\n}\n'
        tmp.close()
        self.assertEqual( expected, actual)
        
    def test_scad_render_to_file( self):
        a = circle(10)
        
        # No header, no included original code
        tmp = tempfile.NamedTemporaryFile()
        scad_render_to_file( a, filepath=tmp.name, include_orig_code=False)
        tmp.seek(0)
        actual = tmp.read()
        expected = '\n\ncircle(r = 10);'
        tmp.close()
        self.assertEqual( expected, actual)
        
        # Header
        tmp = tempfile.NamedTemporaryFile()
        scad_render_to_file( a, filepath=tmp.name, include_orig_code=False,
                     file_header='$fn = 24;')
        tmp.seek(0)
        actual = tmp.read()
        expected = '$fn = 24;\n\ncircle(r = 10);'
        tmp.close()
        self.assertEqual( expected, actual)
        
        # TODO: test include_orig_code=True, but that would have to
        # be done from a separate file, or include everything in this one
    
        
def single_test( test_dict):
    name, args, kwargs, expected = test_dict['name'], test_dict['args'], test_dict['kwargs'], test_dict['expected']
    
    def test( self):
        call_str= name + "(" 
        for k, v in args.items():
            call_str += "%s=%s, "%(k,v)
        for k, v in kwargs.items():
            call_str += "%s=%s, "%(k,v)
        call_str += ')'
        
        scad_obj = eval( call_str)
        actual = scad_render( scad_obj)
        
        self.assertEqual( expected, actual)
    
    return test
    
def generate_cases_from_templates():
    for test_dict in scad_test_case_templates:
        test = single_test( test_dict)
        test_name = "test_%(name)s"%test_dict
        setattr( TestSolidPython, test_name, test)     


if __name__ == '__main__':
    generate_cases_from_templates()                           
    unittest.main()
########NEW FILE########
__FILENAME__ = test_utils
#! /usr/bin/python
# -*- coding: UTF-8 -*-
import os, sys, re

import unittest

from solid import *
from solid.utils import *
from euclid import *

tri = [Point3( 0,0,0), Point3( 10,0,0), Point3(0,10,0)]

scad_test_cases = [
    (                               up,                 [2],   '\n\ntranslate(v = [0, 0, 2]);'),
    (                               down,               [2],   '\n\ntranslate(v = [0, 0, -2]);'),
    (                               left,               [2],   '\n\ntranslate(v = [-2, 0, 0]);'),
    (                               right,              [2],   '\n\ntranslate(v = [2, 0, 0]);'),
    (                               forward,            [2],   '\n\ntranslate(v = [0, 2, 0]);'),
    (                               back,               [2],   '\n\ntranslate(v = [0, -2, 0]);'),   
    (                               arc,                [10, 0, 90, 24], '\n\ndifference() {\n\tcircle(r = 10, $fn = 24);\n\trotate(a = 0) {\n\t\ttranslate(v = [0, -10, 0]) {\n\t\t\tsquare(center = true, size = [30, 20]);\n\t\t}\n\t}\n\trotate(a = -90) {\n\t\ttranslate(v = [0, -10, 0]) {\n\t\t\tsquare(center = true, size = [30, 20]);\n\t\t}\n\t}\n}'),
    (                               arc_inverted,       [10, 0, 90, 24], '\n\ndifference() {\n\tintersection() {\n\t\trotate(a = 0) {\n\t\t\ttranslate(v = [-990, 0]) {\n\t\t\t\tsquare(center = false, size = [1000, 1000]);\n\t\t\t}\n\t\t}\n\t\trotate(a = 90) {\n\t\t\ttranslate(v = [-990, -1000]) {\n\t\t\t\tsquare(center = false, size = [1000, 1000]);\n\t\t\t}\n\t\t}\n\t}\n\tcircle(r = 10, $fn = 24);\n}'),
    ( 'transform_to_point_scad',    transform_to_point, [cube(2), [2,2,2], [3,3,1]], '\n\nmultmatrix(m = [[0.7071067812, -0.1622214211, -0.6882472016, 2], [-0.7071067812, -0.1622214211, -0.6882472016, 2], [0.0000000000, 0.9733285268, -0.2294157339, 2], [0, 0, 0, 1.0000000000]]) {\n\tcube(size = 2);\n}'),
    ( 'offset_polygon_inside',      offset_polygon,     [tri, 2, True], '\n\npolygon(paths = [[0, 1, 2]], points = [[2.0000000000, 2.0000000000, 0.0000000000], [5.1715728753, 2.0000000000, 0.0000000000], [2.0000000000, 5.1715728753, 0.0000000000]]);'),
    ( 'offset_polygon_outside',     offset_polygon,     [tri, 2, False], '\n\npolygon(paths = [[0, 1, 2]], points = [[-2.0000000000, -2.0000000000, 0.0000000000], [14.8284271247, -2.0000000000, 0.0000000000], [-2.0000000000, 14.8284271247, 0.0000000000]]);'),
    ( 'extrude_along_path',         extrude_along_path, [tri, [[0,0,0],[0,20,0]]], '\n\npolyhedron(points = [[0.0000000000, 0.0000000000, 0.0000000000], [10.0000000000, 0.0000000000, 0.0000000000], [0.0000000000, 0.0000000000, 10.0000000000], [0.0000000000, 20.0000000000, 0.0000000000], [10.0000000000, 20.0000000000, 0.0000000000], [0.0000000000, 20.0000000000, 10.0000000000]], triangles = [[0, 3, 1], [1, 3, 4], [1, 4, 2], [2, 4, 5], [0, 2, 5], [0, 5, 3], [0, 1, 2], [3, 5, 4]]);'),
    ( 'extrude_along_path_vertical',extrude_along_path, [tri, [[0,0,0],[0,0,20]]], '\n\npolyhedron(points = [[0.0000000000, 0.0000000000, 0.0000000000], [-10.0000000000, 0.0000000000, 0.0000000000], [0.0000000000, 10.0000000000, 0.0000000000], [0.0000000000, 0.0000000000, 20.0000000000], [-10.0000000000, 0.0000000000, 20.0000000000], [0.0000000000, 10.0000000000, 20.0000000000]], triangles = [[0, 3, 1], [1, 3, 4], [1, 4, 2], [2, 4, 5], [0, 2, 5], [0, 5, 3], [0, 1, 2], [3, 5, 4]]);'),

]   

other_test_cases = [
    (                                   euclidify,      [[0,0,0]],          'Vector3(0.00, 0.00, 0.00)'),
    ( 'euclidify_recursive',            euclidify,      [[[0,0,0], [1,0,0]]], '[Vector3(0.00, 0.00, 0.00), Vector3(1.00, 0.00, 0.00)]'),
    ( 'euclidify_Vector',               euclidify,      [Vector3(0,0,0)], 'Vector3(0.00, 0.00, 0.00)'),
    ( 'euclidify_recursive_Vector',     euclidify,      [[Vector3( 0,0,0), Vector3( 0,0,1)]],  '[Vector3(0.00, 0.00, 0.00), Vector3(0.00, 0.00, 1.00)]'),
    (                                   euc_to_arr,     [Vector3(0,0,0)], '[0, 0, 0]'),
    ( 'euc_to_arr_recursive',           euc_to_arr,     [[Vector3( 0,0,0), Vector3( 0,0,1)]], '[[0, 0, 0], [0, 0, 1]]'),
    ( 'euc_to_arr_arr',                 euc_to_arr,     [[0,0,0]], '[0, 0, 0]'),
    ( 'euc_to_arr_arr_recursive',       euc_to_arr,     [[[0,0,0], [1,0,0]]], '[[0, 0, 0], [1, 0, 0]]'),
    (                                   is_scad,        [cube(2)], 'True'),
    ( 'is_scad_false',                  is_scad,        [2], 'False'),
    ( 'transform_to_point_single_arr',  transform_to_point, [[1,0,0], [2,2,2], [3,3,1]], 'Point3(2.71, 1.29, 2.00)'),
    ( 'transform_to_point_single_pt3',  transform_to_point, [Point3(1,0,0), [2,2,2], [3,3,1]], 'Point3(2.71, 1.29, 2.00)'),
    ( 'transform_to_point_arr_arr',     transform_to_point, [[[1,0,0], [0,1,0], [0,0,1]]  , [2,2,2], [3,3,1]], '[Point3(2.71, 1.29, 2.00), Point3(1.84, 1.84, 2.97), Point3(1.31, 1.31, 1.77)]'),
    ( 'transform_to_point_pt3_arr',     transform_to_point, [[Point3(1,0,0), Point3(0,1,0), Point3(0,0,1)], [2,2,2], [3,3,1]], '[Point3(2.71, 1.29, 2.00), Point3(1.84, 1.84, 2.97), Point3(1.31, 1.31, 1.77)]') ,
    ( 'transform_to_point_redundant',   transform_to_point, [ [Point3( 0,0,0), Point3( 10,0,0), Point3(0,10,0)], [2,2,2], Vector3(0,0,1), Point3(0,0,0), Vector3(0,1,0), Vector3(0,0,1)], '[Point3(2.00, 2.00, 2.00), Point3(-8.00, 2.00, 2.00), Point3(2.00, 12.00, 2.00)]'),
    ( 'offset_points_inside',           offset_points,  [tri, 2, True],  '[Point3(2.00, 2.00, 0.00), Point3(5.17, 2.00, 0.00), Point3(2.00, 5.17, 0.00)]'),
    ( 'offset_points_outside',          offset_points,  [tri, 2, False], '[Point3(-2.00, -2.00, 0.00), Point3(14.83, -2.00, 0.00), Point3(-2.00, 14.83, 0.00)]'),
    ( 'offset_points_open_poly',        offset_points,  [tri, 2, False, False], '[Point3(0.00, -2.00, 0.00), Point3(14.83, -2.00, 0.00), Point3(1.41, 11.41, 0.00)]'),
]


class TestSPUtils( unittest.TestCase):
    # Test cases will be dynamically added to this instance
    # using the test case arrays above
    
    def test_split_body_planar(self):
        offset = [10, 10, 10]
        body = translate( offset)( sphere( 20))
        body_bb = BoundingBox( [40, 40, 40], offset)
        actual = []
        for split_dir in [ RIGHT_VEC, FORWARD_VEC, UP_VEC]:
            actual_tuple = split_body_planar( body, body_bb, cutting_plane_normal=split_dir, cut_proportion=0.25)
            actual.append( actual_tuple)
        
        # Ignore the bounding box object that come back, taking only the SCAD objects
        actual = [scad_render( a) for splits in actual for a in splits[::2] ]
        
        expected = ['\n\nintersection() {\n\ttranslate(v = [10, 10, 10]) {\n\t\tsphere(r = 20);\n\t}\n\ttranslate(v = [-5.0000000000, 10, 10]) {\n\t\tcube(center = true, size = [10.0000000000, 40, 40]);\n\t}\n}',
                    '\n\nintersection() {\n\ttranslate(v = [10, 10, 10]) {\n\t\tsphere(r = 20);\n\t}\n\ttranslate(v = [15.0000000000, 10, 10]) {\n\t\tcube(center = true, size = [30.0000000000, 40, 40]);\n\t}\n}',
                    '\n\nintersection() {\n\ttranslate(v = [10, 10, 10]) {\n\t\tsphere(r = 20);\n\t}\n\ttranslate(v = [10, -5.0000000000, 10]) {\n\t\tcube(center = true, size = [40, 10.0000000000, 40]);\n\t}\n}',
                    '\n\nintersection() {\n\ttranslate(v = [10, 10, 10]) {\n\t\tsphere(r = 20);\n\t}\n\ttranslate(v = [10, 15.0000000000, 10]) {\n\t\tcube(center = true, size = [40, 30.0000000000, 40]);\n\t}\n}',
                    '\n\nintersection() {\n\ttranslate(v = [10, 10, 10]) {\n\t\tsphere(r = 20);\n\t}\n\ttranslate(v = [10, 10, -5.0000000000]) {\n\t\tcube(center = true, size = [40, 40, 10.0000000000]);\n\t}\n}',
                    '\n\nintersection() {\n\ttranslate(v = [10, 10, 10]) {\n\t\tsphere(r = 20);\n\t}\n\ttranslate(v = [10, 10, 15.0000000000]) {\n\t\tcube(center = true, size = [40, 40, 30.0000000000]);\n\t}\n}'
                    ]
        self.assertEqual( actual, expected)
    
    def test_fillet_2d_add( self):
        pts = [  [0,5], [5,5], [5,0], [10,0], [10,10], [0,10],]
        p = polygon( pts)
        newp = fillet_2d( euclidify(pts[0:3], Point3), orig_poly=p, fillet_rad=2, remove_material=False)
        expected = '\n\nunion() {\n\tpolygon(paths = [[0, 1, 2, 3, 4, 5]], points = [[0, 5], [5, 5], [5, 0], [10, 0], [10, 10], [0, 10]]);\n\ttranslate(v = [3.0000000000, 3.0000000000, 0.0000000000]) {\n\t\tdifference() {\n\t\t\tintersection() {\n\t\t\t\trotate(a = 358.0000000000) {\n\t\t\t\t\ttranslate(v = [-998, 0]) {\n\t\t\t\t\t\tsquare(center = false, size = [1000, 1000]);\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\trotate(a = 452.0000000000) {\n\t\t\t\t\ttranslate(v = [-998, -1000]) {\n\t\t\t\t\t\tsquare(center = false, size = [1000, 1000]);\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n\t\t\tcircle(r = 2);\n\t\t}\n\t}\n}'
        actual = scad_render( newp)
        self.assertEqual( expected, actual)
    
    def test_fillet_2d_remove( self):
        pts = tri
        poly = polygon( euc_to_arr( tri))
        
        newp = fillet_2d( tri, orig_poly=poly, fillet_rad=2, remove_material=True)
        expected = '\n\ndifference() {\n\tpolygon(paths = [[0, 1, 2]], points = [[0, 0, 0], [10, 0, 0], [0, 10, 0]]);\n\ttranslate(v = [5.1715728753, 2.0000000000, 0.0000000000]) {\n\t\tdifference() {\n\t\t\tintersection() {\n\t\t\t\trotate(a = 268.0000000000) {\n\t\t\t\t\ttranslate(v = [-998, 0]) {\n\t\t\t\t\t\tsquare(center = false, size = [1000, 1000]);\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\trotate(a = 407.0000000000) {\n\t\t\t\t\ttranslate(v = [-998, -1000]) {\n\t\t\t\t\t\tsquare(center = false, size = [1000, 1000]);\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t}\n\t\t\tcircle(r = 2);\n\t\t}\n\t}\n}'
        actual = scad_render( newp)
        self.assertEqual( expected, actual)
        


           
def test_generator_scad( func, args, expected):
    def test_scad(self):
        scad_obj = func( *args)
        actual = scad_render( scad_obj)
        self.assertEqual( expected, actual)
    
    return test_scad

def test_generator_no_scad( func, args, expected):
    def test_no_scad( self):
        actual = str( func( *args))
        self.assertEqual( expected, actual)
    
    return test_no_scad

def read_test_tuple( test_tuple):
    if len( test_tuple) == 3:
        # If test name not supplied, create it programmatically
        func, args, expected = test_tuple
        test_name = 'test_%s'%func.__name__
    elif len( test_tuple) == 4:
        test_name, func, args, expected = test_tuple
        test_name = 'test_%s'%test_name
    else:
        print "test_tuple has %d args :%s"%( len(test_tuple), test_tuple)    
    return test_name, func, args, expected    

def create_tests( ):
    for test_tuple in scad_test_cases:
        test_name, func, args, expected = read_test_tuple( test_tuple)
        test = test_generator_scad( func, args, expected)
        setattr( TestSPUtils, test_name, test)     
        
    for test_tuple in other_test_cases:
        test_name, func, args, expected = read_test_tuple( test_tuple)
        test = test_generator_no_scad( func, args, expected)
        setattr( TestSPUtils, test_name, test)      

if __name__ == '__main__':
    create_tests( )
    unittest.main()

########NEW FILE########
__FILENAME__ = t_slots
#! /usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import division
import os, sys, re

# Assumes SolidPython is in site-packages or elsewhwere in sys.path
from solid import *
from solid.utils import *

SEGMENTS = 24

# FIXME: ought to be 5
DFM = 5 # Default Material thickness

tab_width = 5
tab_offset = 4
tab_curve_rad = .35

# TODO: Slots & tabs make it kind of difficult to align pieces, since we
# always need the slot piece to overlap the tab piece by a certain amount.
# It might be easier to have the edges NOT overlap at all and then have tabs
# for the slots added programmatically.  -ETJ 06 Mar 2013

def t_slot_holes( poly, point=None, edge_vec=RIGHT_VEC, screw_vec=DOWN_VEC, screw_type='m3', screw_length=16, material_thickness=DFM, kerf=0 ):
    '''
    Cuts a screw hole and two notches in poly so they'll 
    interface with the features cut by t_slot()
    
    Returns a copy of poly with holes removed
        
    -- material_thickness is the thickness of the material *that will
    be attached** to the t-slot, NOT necessarily the material that poly
    will be cut on.  
    
    -- screw_vec is the direction the screw through poly will face; normal to poly      
    -- edge_vec orients the holes to the edge they run parallel to
        
    TODO: add kerf calculations
    '''
    point = point if point else ORIGIN
    point     = euclidify( point, Point3)
    screw_vec = euclidify( screw_vec, Vector3)
    edge_vec  = euclidify( edge_vec, Vector3) 
    
    src_up = screw_vec.cross( edge_vec)   

    
    a_hole = square( [tab_width, material_thickness], center=True)
    move_hole = tab_offset + tab_width/2
    tab_holes = left( move_hole)( a_hole) + right( move_hole)( a_hole) 
                
    
    # Only valid for m3-m5 screws now
    screw_dict = screw_dimensions.get( screw_type.lower())
    if screw_dict:
        screw_w = screw_dict['screw_outer_diam']
    else:
        raise ValueError( "Don't have screw dimensions for requested screw size %s"%screw_type)        
            
    # add the screw hole
    tab_holes += circle( screw_w/2) # NOTE: needs any extra space?
    
    tab_holes  = transform_to_point( tab_holes,  point, dest_normal=screw_vec, src_normal=UP_VEC, src_up=src_up)
    
    return poly - tab_holes

def t_slot(       poly, point=None, screw_vec=DOWN_VEC, face_normal=UP_VEC, screw_type='m3', screw_length=16, material_thickness=DFM, kerf=0 ):
    '''
    Cuts a t-shaped shot in poly and adds two tabs
    on the outside edge of poly.  
    
    Needs to be combined with t_slot_holes() on another
    poly to make a valid t-slot connection
    
    -- material_thickness is the thickness of the material *that will
    be attached** to the t-slot, NOT necessarily the material that poly
    will be cut on.
    
    -- This method will align the t-slots where you tell them to go, 
    using point, screw_vec (the direction the screw will be inserted), and
    face_normal, a vector normal to the face being altered.  To avoid confusion,
    it's often easiest to work on the XY plane. 
    
    
    TODO: include kerf in calculations
    '''
    point = point if point else ORIGIN
    point = euclidify( point, Point3)
    screw_vec   = euclidify( screw_vec, Vector3)
    face_normal = euclidify( face_normal, Vector3)

    tab = tab_poly( material_thickness=material_thickness)
    slot = nut_trap_slot( screw_type, screw_length, material_thickness=material_thickness)
    
    # NOTE: dest_normal & src_normal are the same.  This should matter, right?
    tab  = transform_to_point( tab,  point, dest_normal=face_normal, src_normal=face_normal, src_up=-screw_vec)
    slot = transform_to_point( slot, point, dest_normal=face_normal, src_normal=face_normal, src_up=-screw_vec)
            
    return poly + tab - slot
    
def tab_poly( material_thickness=DFM):
    
    r = [   [ tab_width + tab_offset,   -EPSILON],
            [ tab_offset,               -EPSILON],                
            [ tab_offset,               material_thickness],
            [ tab_width + tab_offset,   material_thickness],]
            
    l = [ [-rp[0], rp[1]]  for rp in r]
    tab_pts = l + r

    tab_faces = [[0,1,2,3], [4,5,6,7]]
    tab = polygon( tab_pts, tab_faces)
    
    # Round off the top points so tabs slide in more easily
    round_tabs = False
    if round_tabs:
        points_to_round = [ [r[1], r[2], r[3]],
                            [r[2], r[3], r[0]],
                            [l[1], l[2], l[3]],
                            [l[2], l[3], l[0]],
                            ]
        tab = fillet_2d( three_point_sets=points_to_round, orig_poly=tab, 
                            fillet_rad=1, remove_material=True)
    
    return tab


def nut_trap_slot( screw_type='m3', screw_length=16, material_thickness=DFM):
    # This shape has a couple uses.
    # 1) Right angle joint between two pieces of material.
    # A bolt goes through the second piece and into the first. 
    
    # 2) Set-screw for attaching to motor spindles. 
    # Bolt goes full length into a sheet of material.  Set material_thickness
    # to something small (1-2 mm) to make sure there's adequate room to 
    # tighten onto the shaft
    
    
    # Only valid for m3-m5 screws now
    screw_dict = screw_dimensions.get( screw_type.lower())
    if screw_dict:
        screw_w = screw_dict['screw_outer_diam']
        screw_w2 = screw_w/2
        nut_hole_x = (screw_dict[ 'nut_inner_diam'] + 0.2)/2 # NOTE: How are these tolerances?
        nut_hole_h = screw_dict['nut_thickness'] + 0.5
        slot_depth = material_thickness - screw_length - 0.5
        # If a nut isn't far enough into the material, the sections
        # that hold the nut in may break off.  Make sure it's at least
        # half a centimeter.  More would be better, actually
        nut_loc = -5
    else:
        raise ValueError( "Don't have screw dimensions for requested screw size %s"%screw_type)
    
    slot_pts = [[ screw_w2, EPSILON ],
                [ screw_w2, nut_loc],
                [ nut_hole_x, nut_loc], 
                [ nut_hole_x, nut_loc - nut_hole_h],
                [ screw_w2, nut_loc - nut_hole_h],
                [ screw_w2, slot_depth],    
                ]
    # mirror the slot points on the left
    slot_pts += [[-x, y] for x,y in slot_pts][ -1::-1]
            
    # TODO: round off top corners of slot
    
    # Add circles around t edges to prevent acrylic breakage
    slot = polygon( slot_pts)
    slot = union()(
                slot,
                translate( [nut_hole_x, nut_loc])( circle( tab_curve_rad)),
                translate( [-nut_hole_x, nut_loc])( circle( tab_curve_rad))
            )
    return render()(slot)

def assembly():
    a = union()
    
    return a

if __name__ == '__main__':
    a = assembly()    
    scad_render_to_file( a, file_header='$fn = %s;'%SEGMENTS, include_orig_code=True)

########NEW FILE########
__FILENAME__ = utils
#! /usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import division
import os, sys, re
from solid import *
from math import *

RIGHT, TOP, LEFT, BOTTOM = range(4)
EPSILON = 0.01
TAU = 2*pi

X, Y, Z = range(3)

ORIGIN      = ( 0, 0, 0)
UP_VEC      = ( 0, 0, 1)
RIGHT_VEC   = ( 1, 0, 0)
FORWARD_VEC = ( 0, 1, 0)
DOWN_VEC    = ( 0, 0,-1)
LEFT_VEC    = (-1, 0, 0)
BACK_VEC    = ( 0,-1, 0)

# ==========
# = Colors =
# ========== 
Red         = ( 1, 0, 0)
Green       = ( 0, 1, 0)
Blue        = ( 0, 0, 1)
Cyan        = ( 0, 1, 1)
Magenta     = ( 1, 0, 1)
Yellow      = ( 1, 1, 0)
Black       = ( 0, 0, 0)
White       = ( 1, 1, 1)
Oak         = (0.65, 0.50, 0.40)
Pine        = (0.85, 0.70, 0.45)
Birch       = (0.90, 0.80, 0.60)
FiberBoard  = (0.70, 0.67, 0.60)
BlackPaint  = (0.20, 0.20, 0.20)
Iron        = (0.36, 0.33, 0.33)
Steel       = (0.65, 0.67, 0.72)
Stainless   = (0.45, 0.43, 0.50)
Aluminum    = (0.77, 0.77, 0.80)
Brass       = (0.88, 0.78, 0.50)
Transparent = (1,    1,    1,   0.2)

# ========================
# = Degrees <==> Radians =
# ========================
def degrees( x_radians):
    return 360.0*x_radians/TAU

def radians( x_degrees):
    return x_degrees/360.0*TAU


# ==============
# = Grid Plane =
# ==============
def grid_plane( grid_unit=12, count=10, line_weight=0.1, plane='xz'):
    
    # Draws a grid of thin lines in the specified plane.  Helpful for 
    # reference during debugging.  
    l = count*grid_unit
    t = union()
    t.set_modifier('background')
    for i in range(-count/2, count/2+1):
        if 'xz' in plane:
            # xz-plane
            h = up(   i*grid_unit)( cube( [ l, line_weight, line_weight], center=True))
            v = right(i*grid_unit)( cube( [ line_weight, line_weight, l], center=True))
            t.add([h,v])
        
        # xy plane
        if 'xy' in plane:
            h = forward(i*grid_unit)( cube([ l, line_weight, line_weight], center=True))
            v = right(  i*grid_unit)( cube( [ line_weight, l, line_weight], center=True))
            t.add([h,v])
            
        # yz plane
        if 'yz' in plane:
            h = up(      i*grid_unit)( cube([ line_weight, l, line_weight], center=True))
            v = forward( i*grid_unit)( cube([ line_weight, line_weight, l], center=True))
            
            t.add([h,v])
            
    return t
    

def distribute_in_grid( objects, max_bounding_box, rows_and_cols=None):
    # Translate each object in objects in a grid with each cell of size
    # max_bounding_box.  
    # If 
    # objects:  array of SCAD objects
    # max_bounding_box: 2-tuple with x & y dimensions of grid cells.
    #   if a single number is passed, x  & y will both use it
    # rows_and_cols: 2-tuple of how many rows and columns to use. If 
    #       not supplied, rows_and_cols will be the smallest square that
    #       can contain all members of objects (e.g, if len(objects) == 80, 
    #       rows_and_cols will default to (9,9))

    # Distributes object in a grid in the xy plane
    # with objects spaced max_bounding_box apart
    if isinstance( max_bounding_box, (list, tuple)):
        x_trans, y_trans = max_bounding_box[0:2]
    elif isinstance(max_bounding_box, (int, long, float, complex)):
        x_trans = y_trans = max_bounding_box
    else: 
        pass # TypeError
    
    # If we only got passed one object, just return it
    try:
        l = len(objects)
    except:
        return objects
    
    ret = []
    if rows_and_cols:
        grid_w, grid_h = rows_and_cols
    else:
        grid_w = grid_h = int(ceil( sqrt(len(objects))))
        
    objs_placed = 0
    for y in range( grid_h):
        for x in range( grid_w):
            if objs_placed < len(objects):
                ret.append(translate( [x*x_trans, y*y_trans])( objects[objs_placed]))
                objs_placed += 1
            else:
                break
    return union()(ret)

# ==============
# = Directions =
# ==============
def up( z):
    return translate( [0,0,z])

def down( z):
    return translate( [0,0,-z])

def right( x):
    return translate( [x, 0,0])

def left( x):
    return translate( [-x, 0,0])

def forward(y):
    return translate( [0,y,0])

def back( y):
    return translate( [0,-y,0])


# ===========================
# = Box-alignment rotations =
# ===========================
def rot_z_to_up( obj):
    # NOTE: Null op
    return rotate( a=0, v=FORWARD_VEC)(obj)

def rot_z_to_down( obj):
    return rotate( a=180, v=FORWARD_VEC)(obj)

def rot_z_to_right( obj):
    return rotate( a=90, v=FORWARD_VEC)(obj)

def rot_z_to_left( obj):
    return rotate( a=-90, v=FORWARD_VEC)(obj)

def rot_z_to_forward( obj):
    return rotate( a=-90, v=RIGHT_VEC)(obj)

def rot_z_to_back( obj):
    return rotate( a=90, v=RIGHT_VEC)(obj)



# ================================
# = Box-aligment and translation =
# ================================
def box_align( obj, direction_func=up, distance=0 ):
    # Given a box side (up, left, etc) and a distance,
    # rotate obj (assumed to be facing up) in the 
    # correct direction and move it distance in that
    # direction
    trans_and_rot = {
        up:         rot_z_to_up, # Null
        down:       rot_z_to_down,
        right:      rot_z_to_right,
        left:       rot_z_to_left,
        forward:    rot_z_to_forward,
        back:       rot_z_to_back,
    }

    assert( direction_func in trans_and_rot)
    rot = trans_and_rot[ direction_func]
    return direction_func( distance)( rot( obj))

# =======================
# = 90-degree Rotations =
# =======================
def rot_z_to_x( obj):
    return rotate( a=90, v=FORWARD_VEC)(obj)

def rot_z_to_neg_x( obj):
    return rotate( a=-90, v=FORWARD_VEC)(obj)

def rot_z_to_neg_y( obj):
    return rotate( a=90, v=RIGHT_VEC)(obj)

def rot_z_to_y( obj):
    return rotate( a=-90, v=RIGHT_VEC)(obj)

def rot_x_to_y( obj):
    return rotate( a=90, v=UP_VEC)(obj)

def rot_x_to_neg_y( obj):
    return rotate( a=-90, v=UP_VEC)(obj)

# =======
# = Arc =
# =======
def arc( rad, start_degrees, end_degrees, segments=None):
    # Note: the circle that this arc is drawn from gets segments,
    # not the arc itself.  That means a quarter-circle arc will
    # have segments/4 segments.
    
    bottom_half_square = back( rad)(square( [3*rad, 2*rad], center=True))
    top_half_square = forward( rad)( square( [3*rad, 2*rad], center=True))
    
    start_shape = circle( rad, segments=segments)

    if abs( (end_degrees - start_degrees)%360) <=  180:
        end_angle = end_degrees - 180
        ret = difference()(
            start_shape,
            rotate( a=start_degrees)(   bottom_half_square.copy()),
            rotate( a= end_angle)(      bottom_half_square.copy())
        )
    else:
        ret = intersection( )(
            start_shape,
            union()(
                rotate( a=start_degrees)(   top_half_square.copy()),
                rotate( a=end_degrees)(     bottom_half_square.copy())
            )
        )
     
    return ret
    
def arc_inverted( rad, start_degrees, end_degrees, segments=None):
    # Return the segment of an arc *outside* the circle of radius rad,
    # bounded by two tangents to the circle.  This is the shape
    # needed for fillets.
    
    # Note: the circle that this arc is drawn from gets segments,
    # not the arc itself.  That means a quarter-circle arc will
    # have segments/4 segments.
    
    # Leave the portion of a circumscribed square of sides
    # 2*rad that is NOT in the arc behind.  This is most useful for 90-degree
    # segments, since it's what you'll add to create fillets and take away
    # to create rounds. 
    
    # NOTE: an inverted arc is only valid for end_degrees-start_degrees <= 180.
    # If this isn't true, end_degrees and start_degrees will be swapped so
    # that an acute angle can be found.  end_degrees-start_degrees == 180
    # will yield a long rectangle of width 2*radius, since the tangent lines
    # will be parallel and never meet.
    
    # Fix start/end degrees as needed; find a way to make an acute angle
    if end_degrees < start_degrees:
        end_degrees += 360
    
    if end_degrees - start_degrees >= 180:
        start_degrees, end_degrees = end_degrees, start_degrees        
        
    # We want the area bounded by:  
    # -- the circle from start_degrees to end_degrees
    # -- line tangent to the circle at start_degrees
    # -- line tangent to the circle at end_degrees
    # Note that this shape is only valid if end_degrees - start_degrees < 180,
    # since if the two angles differ by more than 180 degrees,
    # the tangent lines don't converge
    if end_degrees - start_degrees == 180:
        raise ValueError( "Unable to draw inverted arc over 180 or more "
                        "degrees. start_degrees: %s end_degrees: %s"
                        %(start_degrees, end_degrees))
        
    wide = 1000
    high = 1000
        
    top_half_square    =  translate( [-(wide-rad), 0])( square([wide, high], center=False))
    bottom_half_square =  translate( [-(wide-rad), -high])( square([wide, high], center=False))
        
    a = rotate( start_degrees)( top_half_square)
    b = rotate( end_degrees)( bottom_half_square)
    
    ret = (a*b) - circle( rad, segments=segments)

    return ret

# TODO: arc_to that creates an arc from point to another point.
# This is useful for making paths.  See the SVG path command:
# See: http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes

# ======================
# = Bounding Box Class =
# ======================
class BoundingBox(object):
    # A basic Bounding Box representation to enable some more introspection about
    # objects.  For instance, a BB will let us say "put this new object on top of
    # that old one".  Bounding Boxes *can't* be relied on for boolean operations 
    # without compiling in OpenSCAD, so they're limited, but good for some purposes.
    # Be careful to understand what things this BB implementation can and can't do -ETJ 15 Oct 2013

    # Basically you can use a BoundingBox to describe the extents of an object
    # the moment it's created, but once you perform any CSG operation on it, it's 
    # more or less useless.
    def __init__( self, size, loc=None):
        loc = loc if loc else [0,0,0]
        # self.w, self.h, self.d = size
        # self.x, self.y, self.z = loc
        self.set_size( size) 
        self.set_position( loc)
    
    def size( self):
        return [ self.w, self.h, self.d]
    
    def position( self):
        return [ self.x, self.y, self.z]
    
    def set_position( self, position):
        self.x, self.y, self.z = position
        
    def set_size(self, size):
         self.w, self.h, self.d = size
    
    def split_planar( self, cutting_plane_normal= RIGHT_VEC, cut_proportion=0.5, add_wall_thickness=0):
        cpd = {RIGHT_VEC: 0, LEFT_VEC:0, FORWARD_VEC:1, BACK_VEC:1, UP_VEC:2, DOWN_VEC:2}
        cutting_plane = cpd.get( cutting_plane_normal, 2)
        
        # Figure what  the cutting plane offset should be
        dim_center = self.position()[cutting_plane]
        dim = self.size()[cutting_plane]
        dim_min = dim_center - dim/2
        dim_max = dim_center + dim/2
        cut_point = (cut_proportion) * dim_min + (1-cut_proportion)*dim_max
        
        # Now create bounding boxes with the appropriate sizes
        part_bbs = []
        a_sum = 0
        for i, part in enumerate([ cut_proportion, (1-cut_proportion)]):
            part_size = self.size()
            part_size[cutting_plane] = part_size[ cutting_plane] * part
            
            part_loc = self.position()
            part_loc[ cutting_plane] = dim_min + a_sum + dim * (part/2)
            
            # If extra walls are requested around the slices, add them here
            if add_wall_thickness != 0:
                # Expand the walls as requested
                for j in [X, Y, Z]:
                    part_size[j] += 2*add_wall_thickness
                # Don't expand in the direction of the cutting_plane, only away from it
                part_size[cutting_plane] -= add_wall_thickness 
                
                # add +/- add_wall_thickness/2 to the location in the
                # slicing dimension so we stay at the center of the piece
                loc_offset = -add_wall_thickness/2 + i*add_wall_thickness
                part_loc[ cutting_plane] += loc_offset
                           
            part_bbs.append( BoundingBox( part_size, part_loc))
            
            a_sum += part * dim      
            
        return part_bbs  
    
    def cube( self, larger=False):
        c_size = self.size() if not larger else [s + 2*EPSILON for s in self.size()]
        c = translate( self.position())(
            cube( c_size, center=True)
        )
        return c
    



    def min( self, which_dim=None):
        min_pt = [p-s/2 for p, s in zip( self.position(), self.size())]
        if which_dim:
            return min_pt[ which_dim]
        else:
            return min_pt
    
    def max( self, which_dim=None):
        max_pt = [p+s/2 for p, s in zip( self.position(), self.size())]
        if which_dim:
            return max_pt[ which_dim]
        else:
            return max_pt
    

# ===================
# = Model Splitting =
# ===================
def split_body_planar( obj, obj_bb, cutting_plane_normal=UP_VEC, cut_proportion=0.5, dowel_holes=False, dowel_rad=4.5, hole_depth=15, add_wall_thickness=0):
    # Split obj along the specified plane, returning two pieces and 
    # general bounding boxes for each.  
    # Note that the bounding boxes are NOT accurate to the sections,
    # they just indicate which portion of the original BB is in each 
    # section.  Given the limits of OpenSCAD, this is the best we can do -ETJ 17 Oct 2013

    # Optionally, leave holes in both bodies to allow the pieces to be put
    # back together with short dowels.
    
    # Find the splitting bounding boxes
    part_bbs = obj_bb.split_planar( cutting_plane_normal, cut_proportion, add_wall_thickness=add_wall_thickness)
    
    # And intersect the bounding boxes with the object itself
    slices = [obj*part_bb.cube() for part_bb in part_bbs]
    
    # Make holes for dowels if requested. 
    # In case the bodies need to be aligned properly, make two holes, 
    # separated by one dowel-width
    if dowel_holes:
        cpd = {RIGHT_VEC: 0, LEFT_VEC:0, FORWARD_VEC:1, BACK_VEC:1, UP_VEC:2, DOWN_VEC:2}
        cutting_plane = cpd.get( cutting_plane_normal, 2)
        
        dowel = cylinder( r=dowel_rad, h=hole_depth*2, center=True)
        # rotate dowels to correct axis
        if cutting_plane != 2:
            rot_vec = RIGHT_VEC if cutting_plane == 1 else FORWARD_VEC
            dowel = rotate( a=90, v=rot_vec)( dowel)
        
        cut_point = part_bbs[0].position()[ cutting_plane] + part_bbs[0].size()[ cutting_plane]/2
        
        # Move dowels away from center of face by 2*dowel_rad in each
        # appropriate direction
        dowel_trans_a = part_bbs[0].position()
        dowel_trans_a[ cutting_plane] = cut_point
        separation_index = {0:1, 1:2, 2:0}[cutting_plane]
        dowel_trans_a[ separation_index] -= 2*dowel_rad
        dowel_trans_b = dowel_trans_a[:]
        dowel_trans_b[ separation_index] += 4*dowel_rad
        
        dowel_a = translate( dowel_trans_a)(dowel)
        dowel_b = translate( dowel_trans_b)(dowel)
        
        dowels = dowel_a + dowel_b
        # subtract dowels from each slice
        slices = [ s - dowels for s in slices]
    
    slices_and_bbs = [slices[0], part_bbs[0], slices[1], part_bbs[1]]
    return slices_and_bbs
    
def section_cut_xz( body, y_cut_point=0):
    big_w = 10000
    d = 2
    c = forward( d/2 + y_cut_point)( cube( [big_w, d, big_w], center=True))
    return c * body

# =====================
# = Bill of Materials =
# =====================
#   Any part defined in a method can be automatically counted using the 
# @bom_part() decorator. After all parts have been created, call 
# bill_of_materials()
# to generate a report.  Se examples/bom_scad.py for usage
g_parts_dict = {}
def bom_part( description='', per_unit_price=None, currency='US$'):
    def wrap(f):
        name = description if description else f.__name__
        g_parts_dict[name] = [0, currency, per_unit_price]
        def wrapped_f( *args):
            name = description if description else f.__name__
            g_parts_dict[name][0] += 1
            return f(*args)
        
        return wrapped_f
    
    return wrap

def bill_of_materials():
    res = ''
    res +=  "%8s\t%8s\t%8s\t%8s\n"%("Desc.", "Count", "Unit Price", "Total Price")
    all_costs = {}
    for desc,(count, currency, price) in g_parts_dict.items():
        if count > 0:
            if price:
                total = price*count
                try:
                  all_costs[currency] += total
                except:
                  all_costs[currency] = total
                  
                res += "%8s\t%8d\t%s %8f\t%s %8.2f\n"%(desc, count, currency, price, currency, total)
            else:
                res += "%8s\t%8d\n"%(desc, count)
    if all_costs > 0:
        res += "_"*60+'\n'
        res += "Total Cost:\n"
        for currency in all_costs.keys():
          res += "\t\t%s %.2f\n"%(currency, all_costs[currency])
        res+="\n"
    return res


#FIXME: finish this.
def bill_of_materials_justified():
    res = ''
    columns = [s.rjust(8) for s in ("Desc.", "Count", "Unit Price", "Total Price")]
    all_costs = {}
    for desc, (count, currency, price) in g_parts_dict.items():
        if count > 0:
            if price:
                total = price*count
                try: 
                    all_costs[currency] += total
                except: 
                    all_costs[currency] = total
                    
                res += "%(desc)s %(count)s %(currency)s %(price)s %(currency)s %(total)s \n"%vars()
            else:
                res += "%(desc)s %(count)s "%vars()  
    if all_costs > 0:
        res += "_"*60+'\n'
        res += "Total Cost:\n"
        for currency in all_costs.keys():
          res += "\t\t%s %.2f\n"%(currency, all_costs[currency])
        res+="\n"
    return res

# ================
# = Bounding Box =
# ================ 
def bounding_box( points):
    all_x = []; all_y = []; all_z = []
    for p in points:
        all_x.append( p[0])
        all_y.append( p[1])
        if len(p) > 2:
            all_z.append( p[2])
        else:
            all_z.append(0)
    
    return [ [min(all_x), min(all_y), min(all_z)], [max(all_x), max(all_y), max(all_z)]]
    


# =======================
# = Hardware dimensions =
# =======================
screw_dimensions = {
    'm3': { 'nut_thickness':2.4, 'nut_inner_diam': 5.4, 'nut_outer_diam':6.1, 'screw_outer_diam':3.0, 'cap_diam':5.5 ,'cap_height':3.0 },
    'm4': { 'nut_thickness':3.1, 'nut_inner_diam': 7.0, 'nut_outer_diam':7.9, 'screw_outer_diam':4.0, 'cap_diam':6.9 ,'cap_height':3.9 },
    'm5': { 'nut_thickness':4.7, 'nut_inner_diam': 7.9, 'nut_outer_diam':8.8, 'screw_outer_diam':5.0, 'cap_diam':8.7 ,'cap_height':5 },
    
}

def screw( screw_type='m3', screw_length=16):
    dims = screw_dimensions[screw_type.lower()]
    shaft_rad  = dims['screw_outer_diam']/2
    cap_rad    = dims['cap_diam']/2
    cap_height = dims['cap_height']
    
    ret = union()(
        cylinder( shaft_rad, screw_length),
        up(screw_length)(
            cylinder( cap_rad, cap_height)
        )
    )
    return ret

def nut( screw_type='m3'):
    dims = screw_dimensions[screw_type.lower()]
    outer_rad = dims['nut_outer_diam']
    inner_rad = dims['screw_outer_diam']
    
    ret = difference()(
        circle( outer_rad, segments=6),
        circle( inner_rad)
    )
    return ret


# ==================
# = PyEuclid Utils =
# = -------------- =
try:
    import euclid
    from euclid import *    
    # NOTE: The PyEuclid on PyPi doesn't include several elements added to 
    # the module as of 13 Feb 2013.  Add them here until euclid supports them
    # TODO: when euclid updates, remove this cruft. -ETJ 13 Feb 2013
    import patch_euclid
    patch_euclid.run_patch()
    
    def euclidify( an_obj, intended_class=Vector3):
        # If an_obj is an instance of the appropriate PyEuclid class,
        # return it.  Otherwise, try to turn an_obj into the appropriate
        # class and throw an exception on failure
        
        # Since we often want to convert an entire array
        # of objects (points, etc.) accept arrays of arrays
        
        ret = an_obj
        
        # See if this is an array of arrays.  If so, convert all sublists 
        if isinstance( an_obj, (list, tuple)): 
            if isinstance( an_obj[0], (list,tuple)):
                ret = [intended_class(*p) for p in an_obj]
            elif isinstance( an_obj[0], intended_class):
                # this array is already euclidified; return it
                ret = an_obj
            else:
                try:
                    ret = intended_class( *an_obj)
                except:
                    raise TypeError( "Object: %s ought to be PyEuclid class %s or "
                    "able to form one, but is not."%(an_obj, intended_class.__name__))
        elif not isinstance( an_obj, intended_class):
            try:
                ret = intended_class( *an_obj)
            except:
                raise TypeError( "Object: %s ought to be PyEuclid class %s or "
                "able to form one, but is not."%(an_obj, intended_class.__name__))
        return ret
    
    def euc_to_arr( euc_obj_or_list): # Inverse of euclidify()
        # Call as_arr on euc_obj_or_list or on all its members if it's a list
        if hasattr(euc_obj_or_list, "as_arr"):
            return euc_obj_or_list.as_arr()
        elif isinstance( euc_obj_or_list, (list, tuple)) and hasattr(euc_obj_or_list[0], 'as_arr'):
            return [euc_to_arr( p) for p in euc_obj_or_list]
        else:
            # euc_obj_or_list is neither an array-based PyEuclid object,
            # nor a list of them.  Assume it's a list of points or vectors,
            # and return the list unchanged.  We could be wrong about this, though.
            return euc_obj_or_list
    
    def is_scad( obj):
        return isinstance( obj, openscad_object)
    
    def scad_matrix( euclid_matrix4):
        a = euclid_matrix4
        return [[a.a, a.b, a.c, a.d],
                [a.e, a.f, a.g, a.h],
                [a.i, a.j, a.k, a.l],
                [a.m, a.n, a.o, a.p]
               ]
    

    # ==============
    # = Transforms =
    # ==============
    def transform_to_point( body, dest_point, dest_normal, src_point=Point3(0,0,0), src_normal=Vector3(0,1,0), src_up=Vector3(0,0,1)):
        # Transform body to dest_point, looking at dest_normal. 
        # Orientation & offset can be changed by supplying the src arguments
        
        # Body may be:  
        #   -- an openSCAD object
        #   -- a list of 3-tuples  or PyEuclid Point3s
        #   -- a single 3-tuple or Point3
        dest_point = euclidify( dest_point, Point3)
        dest_normal = euclidify( dest_normal, Vector3)
        at = dest_point + dest_normal
        
        EUC_UP = euclidify( UP_VEC)
        EUC_FORWARD = euclidify( FORWARD_VEC)
        EUC_ORIGIN = euclidify( ORIGIN, Vector3)
        # if dest_normal and src_up are parallel, the transform collapses
        # all points to dest_point.  Instead, use EUC_FORWARD if needed
        if dest_normal.cross( src_up) == EUC_ORIGIN:
            if src_up.cross( EUC_UP) == EUC_ORIGIN:
                src_up = EUC_FORWARD
            else: src_up = EUC_UP
            
        look_at_matrix = Matrix4.new_look_at( eye=dest_point, at=at, up=src_up )
        
        if is_scad( body):
            # If the body being altered is a SCAD object, do the matrix mult
            # in OpenSCAD
            sc_matrix = scad_matrix( look_at_matrix)
            res = multmatrix( m=sc_matrix)( body) 
        else:
            body = euclidify( body, Point3)
            if isinstance( body, (list, tuple)):
                res = [look_at_matrix * p for p in body]  
            else:
                res = look_at_matrix *  body
        return res
                     
    
    # ========================================
    # = Vector drawing: 3D arrow from a line =
    # = -------------- =======================
    def draw_segment( euc_line=None, endless=False, arrow_rad=7, vec_color=None):
        # Draw a tradtional arrow-head vector in 3-space.
        vec_arrow_rad = arrow_rad
        vec_arrow_head_rad = vec_arrow_rad * 1.5
        vec_arrow_head_length = vec_arrow_rad * 3
        
        if isinstance( euc_line, Vector3):
            p = Point3( *ORIGIN)
            v = euc_line
        elif isinstance( euc_line, Line3): 
            p = euc_line.p
            v = -euc_line.v
        elif isinstance( euc_line, list) or isinstance( euc_line, tuple):
            # TODO: This assumes p & v are PyEuclid classes.  
            # Really, they could as easily be two 3-tuples. Should
            # check for this.   
            p, v = euc_line[0], euc_line[1]
                 
        shaft_length = v.magnitude() - vec_arrow_head_length    
        arrow = cylinder( r= vec_arrow_rad, h = shaft_length)
        arrow += up( shaft_length )( 
                    cylinder(r1=vec_arrow_head_rad, r2=0, h = vec_arrow_head_length)
                 )
        if endless:
            endless_length = max( v.magnitude()*10, 200)
            arrow += cylinder( r=vec_arrow_rad/3, h = endless_length, center=True)
        
        arrow = transform_to_point( body=arrow, dest_point=p, dest_normal=v)
        
        if vec_color:
            arrow = color( vec_color)(arrow)
        
        return arrow
    
    # ==========
    # = Offset =
    # = ------ = 
    LEFT, RIGHT = radians(90), radians(-90)
    def offset_polygon( point_arr, offset, inside=True, closed_poly=True):
        # returns a closed solidPython polygon offset by offset distance
        # from the polygon described by point_arr.
        op = offset_points( point_arr, offset=offset, inside=inside, closed_poly=closed_poly)
        return polygon( euc_to_arr(op))
    
    def offset_points( point_arr, offset, inside=True, closed_poly=True):
        # Given a set of points, return a set of points offset from 
        # them.  
        # To get reasonable results, the points need to be all in a plane.
        # ( Non-planar point_arr will still return results, but what constitutes
        # 'inside' or 'outside' would be different in that situation.)
        #
        # What direction inside and outside lie in is determined by the first
        # three points (first corner).  In a convex closed shape, this corresponds
        # to inside and outside.  If the first three points describe a concave
        # portion of a closed shape, inside and outside will be switched.  
        #
        # Basically this means that if you're offsetting a complicated shape,
        # you'll likely have to try both directions (inside=True/False) to 
        # figure out which direction you're offsetting to. 
        #
        # CAD programs generally require an interactive user choice about which
        # side is outside and which is inside.  Robust behavior with this
        # function will require similar checking.  
        
        # Also note that short segments or narrow areas can cause problems
        # as well.  This method suffices for most planar convex figures where
        # segment length is greater than offset, but changing any of those
        # assumptions will cause unattractive results.  If you want real 
        # offsets, use SolidWorks.
        
        # TODO: check for self-intersections in the line connecting the 
        # offset points, and remove them.
        
        # Using the first three points in point_arr, figure out which direction
        # is inside and what plane to put the points in
        point_arr = euclidify( point_arr[:], Point3)
        in_dir = _inside_direction(   *point_arr[0:3])
        normal = _three_point_normal( *point_arr[0:3])
        direction = in_dir if inside else _other_dir( in_dir)
        
        # Generate offset points for the correct direction
        # for all of point_arr.
        segs = []  
        offset_pts = []
        point_arr += point_arr[ 0:2] # Add first two points to the end as well
        if closed_poly:
            for i in range( len(point_arr) - 1):
                a, b = point_arr[i:i+2]
                par_seg = _parallel_seg( a, b, normal=normal, offset=offset, direction=direction )
                segs.append( par_seg)
                if len(segs) > 1:
                    int_pt = segs[-2].intersect(segs[-1])
                    if int_pt:
                        offset_pts.append( int_pt)

            # When calculating based on a closed curve, we can't find the 
            # first offset point until all others have been calculated.  
            # Now that we've done so, put the last point back to first place
            last = offset_pts[-1]
            offset_pts.insert( 0, last)
            del( offset_pts[-1])
                                
        else:
            for i in range( len(point_arr)-2):
                a, b = point_arr[i:i+2]
                par_seg = _parallel_seg( a, b, normal=normal, offset=offset, direction=direction )
                segs.append( par_seg)
                # In an open poly, first and last points will be parallel 
                # to the first and last segments, not intersecting other segs
                if i == 0:
                    offset_pts.append( par_seg.p1)    
                elif i == len(point_arr) - 3:
                    offset_pts.append( segs[-2].p2)
                else:
                    int_pt = segs[-2].intersect(segs[-1])
                    if int_pt:
                        offset_pts.append( int_pt)                    
            
        return offset_pts
    
    # ==================
    # = Offset helpers =
    # ==================
    def _parallel_seg( p, q, offset, normal=Vector3( 0, 0, 1), direction=LEFT):
        # returns a PyEuclid Line3 parallel to pq, in the plane determined
        # by p,normal, to the left or right of pq.
        v = q - p
        angle = direction

        rot_v = v.rotate_around( axis=normal, theta=angle)
        rot_v.set_length( offset)
        return Line3( p+rot_v, v )
    
    def _inside_direction( a, b, c, offset=10):
        # determines which direction (LEFT, RIGHT) is 'inside' the triangle
        # made by a, b, c.  If ab and bc are parallel, return LEFT
        x = _three_point_normal( a, b, c)
        
        # Make two vectors (left & right) for each segment.
        l_segs = [_parallel_seg( p, q, normal=x, offset=offset, direction=LEFT) for p,q in ( (a,b), (b,c))]
        r_segs = [_parallel_seg( p, q, normal=x, offset=offset, direction=RIGHT) for p,q in ( (a,b), (b,c))]
        
        # Find their intersections.  
        p1 = l_segs[0].intersect( l_segs[1])
        p2 = r_segs[0].intersect( r_segs[1])
        
        # The only way I've figured out to determine which direction is 
        # 'inside' or 'outside' a joint is to calculate both inner and outer
        # vectors and then to find the intersection point closest to point a.
        # This ought to work but it seems like there ought to be a more direct
        # way to figure this out. -ETJ 21 Dec 2012
        
        # The point that's closer to point a is the inside point. 
        if a.distance( p1) <= a.distance( p2):
            return LEFT
        else:
            return RIGHT
    
    def _other_dir( left_or_right):
        if left_or_right == LEFT: 
            return RIGHT
        else:
            return LEFT
    
    def _three_point_normal( a, b, c):
        ab = b - a
        bc = c - b
        
        seg_ab = Line3( a, ab)
        seg_bc = Line3( b, bc)
        x = seg_ab.v.cross( seg_bc.v)   
        return x
    
    # =============
    # = 2D Fillet =
    # =============
    def _widen_angle_for_fillet( start_degrees, end_degrees):
        # Fix start/end degrees as needed; find a way to make an acute angle
        if end_degrees < start_degrees:
            end_degrees += 360
    
        if end_degrees - start_degrees >= 180:
            start_degrees, end_degrees = end_degrees, start_degrees    
        
        epsilon_degrees = 2
        return start_degrees - epsilon_degrees, end_degrees + epsilon_degrees
    
    def fillet_2d( three_point_sets, orig_poly, fillet_rad, remove_material=True):
        # NOTE: three_point_sets must be a list of sets of three points
        # (i.e., a list of 3-tuples of points), even if only one fillet is being done:
        # e.g.  [[a, b, c]]
        # a, b, and c are three points that form a corner at b.  
        # Return a negative arc (the area NOT covered by a circle) of radius rad
        # in the direction of the more acute angle between 
    
        # Note that if rad is greater than a.distance(b) or c.distance(b), for a 
        # 90-degree corner, the returned shape will include a jagged edge. 
    
        # TODO: use fillet_rad = min( fillet_rad, a.distance(b), c.distance(b))
    
        # If a shape is being filleted in several places, it is FAR faster
        # to add/ remove its set of shapes all at once rather than 
        # to cycle through all the points, since each method call requires
        # a relatively complex boolean with the original polygon.
        # So... three_point_sets is either a list of three Euclid points that 
        # determine the corner to be filleted, OR, a list of those lists, in 
        # which case everything will be removed / added at once.
        # NOTE that if material is being added (fillets) or removed (rounds)
        # each must be called separately. 
    
        if len( three_point_sets) == 3 and isinstance( three_point_sets[0], (Vector2, Vector3)):
            three_point_sets = [three_point_sets]
    
        arc_objs = []
        for three_points in three_point_sets:
    
            assert len(three_points) in (2,3)
            # make two vectors out of the three points passed in
            a, b, c = euclidify( three_points, Point3)

            # Find the center of the arc we'll have to make
            offset = offset_points( [a, b, c], offset=fillet_rad, inside=True)
            center_pt = offset[1]   
    
    
            a2, b2, c2, cp2 = [Point2( p.x, p.y) for p in (a,b,c, center_pt)]
    
            a2b2 = LineSegment2( a2, b2)
            c2b2 = LineSegment2( c2, b2)
    
            # Find the point on each segment where the arc starts; Point2.connect()
            # returns a segment with two points; Take the one that's not the center
            afs = cp2.connect( a2b2)
            cfs = cp2.connect( c2b2)
    
            afp, cfp = [seg.p1 if seg.p1 != cp2 else seg.p2 for seg in (afs, cfs)]
    
            a_degs, c_degs = [ (degrees(math.atan2( seg.v.y, seg.v.x)))%360 for seg in (afs, cfs)]
    
            start_degs = a_degs 
            end_degs = c_degs 
    
            # Widen start_degs and end_degs slightly so they overlap the areas
            # they're supposed to join/ remove.
            start_degs, end_degs = _widen_angle_for_fillet( start_degs, end_degs)
    
            arc_obj = translate( center_pt.as_arr() )(
                            arc_inverted( rad=fillet_rad, start_degrees=start_degs, end_degrees=end_degs)
                        )

            arc_objs.append( arc_obj)
        
        if remove_material:
            poly = orig_poly - arc_objs
        else:
            poly = orig_poly + arc_objs
    
        return poly

    
    # ==========================
    # = Extrusion along a path =
    # = ---------------------- =
    def extrude_along_path( shape_pts, path_pts, scale_factors=None): # Possible: twist
        # Extrude the convex curve defined by shape_pts along path_pts.
        # -- For predictable results, shape_pts must be planar, convex, and lie
        # in the XY plane centered around the origin.
        #
        # -- len( scale_factors) should equal len( path_pts).  If not present, scale
        #       will be assumed to be 1.0 for each point in path_pts
        # -- Future additions might include corner styles (sharp, flattened, round)
        #       or a twist factor
        polyhedron_pts = []
        facet_indices = []
        
        if not scale_factors:
            scale_factors = [1.0] * len(path_pts)
        
        # Make sure we've got Euclid Point3's for all elements
        shape_pts = euclidify( shape_pts, Point3)
        path_pts =  euclidify( path_pts, Point3)
        
        src_up = Vector3( *UP_VEC)
        
        for which_loop in range( len( path_pts) ):
            path_pt = path_pts[which_loop]
            scale = scale_factors[which_loop]
            
            # calculate the tangent to the curve at this point
            if which_loop > 0 and which_loop < len(path_pts) - 1:
                prev_pt = path_pts[which_loop-1]
                next_pt = path_pts[which_loop+1]
                
                v_prev = path_pt - prev_pt
                v_next = next_pt - path_pt
                tangent = v_prev + v_next
            elif which_loop == 0:
                tangent = path_pts[which_loop+1] - path_pt
            elif which_loop == len( path_pts) - 1:
                tangent = path_pt - path_pts[ which_loop -1]
            
            # Scale points
            if scale != 1.0:
                this_loop = [ (scale*sh) for sh in shape_pts]
                # Convert this_loop back to points; scaling changes them to Vectors
                this_loop= [Point3(v.x, v.y, v.z) for v in this_loop]    
            else:
                this_loop = shape_pts[:]
            
            
            # Rotate & translate            
            this_loop = transform_to_point( this_loop, dest_point=path_pt, dest_normal=tangent, src_up=src_up)
         
            # Add the transformed points to our final list
            polyhedron_pts += this_loop
            # And calculate the facet indices
            shape_pt_count = len(shape_pts)
            segment_start = which_loop*shape_pt_count
            segment_end = segment_start + shape_pt_count - 1
            if which_loop < len(path_pts) - 1:
                for i in range( segment_start, segment_end):
                    facet_indices.append( [i, i+shape_pt_count, i+1])
                    facet_indices.append( [i+1, i+shape_pt_count, i+shape_pt_count+1])
                facet_indices.append( [segment_start, segment_end, segment_end + shape_pt_count])
                facet_indices.append( [segment_start, segment_end + shape_pt_count, segment_start+shape_pt_count])
            
        # Cap the start of the polyhedron
        for i in range(1, shape_pt_count - 1):
            facet_indices.append( [0, i, i+1])
        
        # And the end ( could be rolled into the earlier loop)
        # FIXME: concave cross-sections will cause this end-capping algorithm to fail
        end_cap_base = len( polyhedron_pts) - shape_pt_count
        for i in range( end_cap_base + 1, len(polyhedron_pts) -1):
            facet_indices.append( [ end_cap_base, i+1, i])
        
        return polyhedron( points = euc_to_arr(polyhedron_pts), triangles=facet_indices)
    

except:
    # euclid isn't available; these methods won't be either
    pass

## {{{ http://code.activestate.com/recipes/577068/ (r1)
def frange(*args):
    """frange([start, ] end [, step [, mode]]) -> generator
    
    A float range generator. If not specified, the default start is 0.0
    and the default step is 1.0.
    
    Optional argument mode sets whether frange outputs an open or closed
    interval. mode must be an int. Bit zero of mode controls whether start is
    included (on) or excluded (off); bit one does the same for end. Hence:
        
        0 -> open interval (start and end both excluded)
        1 -> half-open (start included, end excluded)
        2 -> half open (start excluded, end included)
        3 -> closed (start and end both included)
    
    By default, mode=1 and only start is included in the output.
    """
    mode = 1  # Default mode is half-open.
    n = len(args)
    if n == 1:
        args = (0.0, args[0], 1.0)
    elif n == 2:
        args = args + (1.0,)
    elif n == 4:
        mode = args[3]
        args = args[0:3]
    elif n != 3:
        raise TypeError('frange expects 1-4 arguments, got %d' % n)
    assert len(args) == 3
    try:
        start, end, step = [a + 0.0 for a in args]
    except TypeError:
        raise TypeError('arguments must be numbers')
    if step == 0.0:
        raise ValueError('step must not be zero')
    if not isinstance(mode, int):
        raise TypeError('mode must be an int')
    if mode & 1:
        i, x = 0, start
    else:
        i, x = 1, start+step
    if step > 0:
        if mode & 2:
            from operator import le as comp
        else:
            from operator import lt as comp
    else:
        if mode & 2:
            from operator import ge as comp
        else:
            from operator import gt as comp
    while comp(x, end):
        yield x
        i += 1
        x = start + i*step

## end of http://code.activestate.com/recipes/577068/ }}}

# =====================
# = D e b u g g i n g =
# =====================
def obj_tree_str( sp_obj, vars_to_print=None):
    # For debugging.  This prints a string of all of an object's
    # children, with whatever attributes are specified in vars_to_print
    
    # Takes an optional list (vars_to_print) of variable names to include in each
    # element (e.g. ['is_part_root', 'is_hole', 'name'])
    if not vars_to_print: vars_to_print = []
    
    # Signify if object has parent or not
    parent_sign = "\nL " if sp_obj.parent else "\n* "
    
    # Print object 
    s = parent_sign + str( sp_obj) + "\t"
    
    # Extra desired fields
    for v in vars_to_print:
        if hasattr( sp_obj, v):
            s += "%s: %s\t"%( v, getattr(sp_obj, v))
   
    # Add all children
    for c in sp_obj.children:
        s += indent( obj_tree_str(c, vars_to_print))
    
    return s

########NEW FILE########
