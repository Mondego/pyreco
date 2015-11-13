__FILENAME__ = bom
#!/usr/bin/env python

import os
import sys
import shutil
import openscad

class BOM:
    def __init__(self):
        self.count = 1
        self.vitamins = {}
        self.printed = {}
        self.assemblies = {}

    def add_part(self, s):
        if s[-4:] == ".stl":
            parts = self.printed
        else:
            parts = self.vitamins
        if s in parts:
            parts[s] += 1
        else:
            parts[s] = 1

    def add_assembly(self, ass):
        if ass in self.assemblies:
            self.assemblies[ass].count += 1
        else:
            self.assemblies[ass] = BOM()

    def make_name(self, ass):
        if self.count == 1:
            return ass
        return ass.replace("assembly", "assemblies")

    def print_bom(self, breakdown, file = None):
        print >> file, "Vitamins:"
        if breakdown:
            longest = 0
            for ass in self.assemblies:
                name = ass.replace("_assembly","")
                longest = max(longest, len(name))
            for i in range(longest):
                for ass in sorted(self.assemblies):
                    name = ass.replace("_assembly","").replace("_"," ").capitalize()
                    index = i - (longest - len(name))
                    if index < 0:
                        print >> file, "  ",
                    else:
                        print >> file, " %s" % name[index],
                print >> file

        for part in sorted(self.vitamins):
            if ': ' in part:
                part_no, description = part.split(': ')
            else:
                part_no, description = "", part
            if breakdown:
                for ass in sorted(self.assemblies):
                    bom = self.assemblies[ass]
                    if part in bom.vitamins:
                        file.write("%2d|" % bom.vitamins[part])
                    else:
                        file.write("  |")
            print >> file, "%3d" % self.vitamins[part], description

        print >> file
        print >> file, "Printed:"
        for part in sorted(self.printed):
            if breakdown:
                for ass in sorted(self.assemblies):
                    bom = self.assemblies[ass]
                    if part in bom.printed:
                        file.write("%2d|" % bom.printed[part])
                    else:
                        file.write("  |")
            print >> file, "%3d" % self.printed[part], part

        print >> file
        if self.assemblies:
            print >> file, "Sub-assemblies:"
        for ass in sorted(self.assemblies):
            print  >> file, "%3d %s" % (self.assemblies[ass].count, self.assemblies[ass].make_name(ass))

def boms(machine):
    bom_dir = machine + "/bom"
    if os.path.isdir(bom_dir):
        shutil.rmtree(bom_dir)
    os.makedirs(bom_dir)

    f = open("scad/conf/machine.scad","wt")
    f. write("include <%s_config.scad>\n" % machine);
    f.close()

    openscad.run("-D","$bom=2","-o", "dummy.csg", "scad/bom.scad")
    print "Generating bom ...",

    main = BOM()
    stack = []

    for line in open("openscad.log"):
        if line[:7] == 'ECHO: "':
            s = line[7:-2]
            if s[-1] == '/':
                ass = s[:-1]
                if stack:
                    main.assemblies[stack[-1]].add_assembly(ass)    #add to nested BOM
                stack.append(ass)
                main.add_assembly(ass)                              #add to flat BOM
            else:
                if s[0] == '/':
                    if s[1:] != stack[-1]:
                        raise Exception, "Mismatched assembly " + s[1:] + str(stack)
                    stack.pop()
                else:
                    main.add_part(s)
                    if stack:
                        main.assemblies[stack[-1]].add_part(s)

    main.print_bom(True, open(bom_dir + "/bom.txt","wt"))

    for ass in sorted(main.assemblies):
        f = open(bom_dir + "/" + ass + ".txt", "wt");
        bom = main.assemblies[ass]
        print >> f, bom.make_name(ass) + ":"
        bom.print_bom(False, f)
        f.close()

    print " done"

if __name__ == '__main__':
    if len(sys.argv) > 1:
        boms(sys.argv[1])
    else:
        print "usage: bom [mendel|sturdy|your_machine]"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = c14n_stl
#!/usr/bin/env python
#
# OpenSCAD produces randomly ordered STL files so source control like GIT can't tell if they have changed or not.
# This scrip orders each triangle to start with the lowest vertex first (comparing x, then y, then z)
# It then sorts the triangles to start with the one with the lowest vertices first (comparing first vertex, second, then third)
# This has no effect on the model but makes the STL consistent. I.e. it makes a canonical form.
#
import sys

class Vertex:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z
        self.key = (float(x), float(y), float(z))

class Normal:
    def __init__(self, dx, dy, dz):
        self.dx, self.dy, self.dz = dx, dy, dz

class Facet:
    def __init__(self, normal, v1, v2, v3):
        self.normal = normal
        if v1.key < v2.key:
            if v1.key < v3.key:
                self.vertices = (v1, v2, v3)    #v1 is the smallest
            else:
                self.vertices = (v3, v1, v2)    #v3 is the smallest
        else:
            if v2.key < v3.key:
                self.vertices = (v2, v3, v1)    #v2 is the smallest
            else:
                self.vertices = (v3, v1, v2)    #v3 is the smallest

    def key(self):
        return (self.vertices[0].x, self.vertices[0].y, self.vertices[0].z,
                self.vertices[1].x, self.vertices[1].y, self.vertices[1].z,
                self.vertices[2].x, self.vertices[2].y, self.vertices[2].z)

class STL:
    def __init__(self, fname):
        self.facets = []

        f = open(fname)
        words = [s.strip() for s in f.read().split()]
        f.close()

        if words[0] == 'solid' and words[1] == 'OpenSCAD_Model':
            i = 2
            while words[i] == 'facet':
                norm = Normal(words[i + 2],  words[i + 3],  words[i + 4])
                v1   = Vertex(words[i + 8],  words[i + 9],  words[i + 10])
                v2   = Vertex(words[i + 12], words[i + 13], words[i + 14])
                v3   = Vertex(words[i + 16], words[i + 17], words[i + 18])
                i += 21
                self.facets.append(Facet(norm, v1, v2, v3))

            self.facets.sort(key = Facet.key)
        else:
            print "Not an OpenSCAD ascii STL file"
            sys.exit(1)

    def write(self, fname):
        f = open(fname,"wt")
        print >> f,'solid OpenSCAD_Model'
        for facet in self.facets:
            print >> f, '  facet normal %s %s %s' % (facet.normal.dx, facet.normal.dy, facet.normal.dz)
            print >> f, '    outer loop'
            for vertex in facet.vertices:
                print >> f, '      vertex %s %s %s' % (vertex.x, vertex.y, vertex.z)
            print  >> f, '    endloop'
            print  >> f, '  endfacet'
        print >> f, 'endsolid OpenSCAD_Model'
        f.close()

def canonicalise(fname):
    stl = STL(fname)
    stl.write(fname)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        canonicalise(sys.argv[1])
    else:
        print "usage: c14n_stl file"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = dxf
#!/usr/bin/env python

from math import *
from svg import *

def parse_dxf(fn):
    f = open(fn)

    # skip to entities section
    s = f.next()
    while s.strip() != 'ENTITIES':
        s = f.next()

    in_line = False
    in_circle = False

    pt_list = []
    cir_list = []

    for line in f:
        line = line.strip()
        # In ENTITIES section, iteration can cease when ENDSEC is reached
        if line == 'ENDSEC':
            break

        elif in_line:
            keys = dict.fromkeys(['8','10','20','30','11','21','31'], 0.0)
            while line != '0':
                if line in keys:
                    keys[line] = float(f.next().strip())
                line = f.next().strip()
            pt_list.append( ((keys['10'], keys['20']), (keys['11'], keys['21'])) )
            in_line = False

        elif in_circle:
            keys = dict.fromkeys(['8','10','20','30','40'], 0.0)
            while line != '0':
                if line in keys:
                    keys[line] = float(f.next().strip())
                line = f.next().strip()
            cir_list.append([[keys['10'], keys['20'], keys['30']], keys['40']])
            in_circle = False

        else:
            if line == 'LINE':
                in_line = True
            elif line == 'CIRCLE' or line == 'ARC':
                in_circle = True
    f.close()
    return pt_list, cir_list

def is_circle(path):
    points = len(path)
    if points < 9:
        return None
    for i in range(points) :
        p1 = path[0]
        p2 = path[int(points /3 )]
        p3 = path[int(points * 2 / 3)]
        if p1[0] != p2[0] and p2[0] != p3[0]:
            ma = (p2[1] - p1[1]) / (p2[0] - p1[0])
            mb = (p3[1] - p2[1]) / (p3[0] - p2[0])
            if ma == mb:
                return None
            x = (ma * mb *(p1[1] - p3[1]) + mb * (p1[0] + p2[0]) - ma * (p2[0] + p3[0])) / (2 * (mb - ma))
            if ma == 0:
                y = -(x - (p2[0] + p3[0]) / 2) / mb + (p2[1] + p3[1]) / 2
            else:
                y = -(x - (p1[0] + p2[0]) / 2) / ma + (p1[1] + p2[1]) / 2
            r = sqrt((p1[0] - x) * (p1[0] - x) + (p1[1] - y) * (p1[1] - y))
            for p in path:
                if abs(sqrt((p[0] - x) * (p[0] - x) + (p[1] - y) * (p[1] - y)) - r) > 0.1:
                    #print "error too big", abs(sqrt((p[0] - x) * (p[0] - x) + (p[1] - y) * (p[1] - y)) - r), points, 2 * r
                    #print p, path
                    return None
            return [x,y, 2 * r, points]
        path = path[1:] + path[:1]                  #rotate and try again
    return None

def dxf_to_svg(fn):
    ptList, cirList = parse_dxf(fn)

    loops = []
    for pt1, pt2 in ptList:
        found = False
        for i in range(len(loops)):
            loop = loops[i]
            p0 = loop[0]
            p1 = loop[-1]
            if pt1 == p0:
                loops[i] = [pt2] + loop; found = True
            elif pt2 == p0:
                loops[i] = [pt1] + loop; found = True
            elif pt1 == p1:
                loops[i] = loop + [pt2]; found = True
            elif pt2 == p1:
                loops[i] = loop + [pt2]; found = True
        if not found:
            loops.append([pt1, pt2])

    xmax = ymax = 0
    xmin = ymin = 99999999
    for loop in loops:
        if len(loop) < 4 or loop[0] != loop[-1]:
            raise Exception, "loop not closed " + str(loop)
        for point in loop:
            if point[0] > xmax: xmax = point[0]
            if point[0] < xmin: xmin = point[0]
            if point[1] > ymax: ymax = point[1]
            if point[1] < ymin: ymin = point[1]

    def p(x, y): return (x - xmin, ymax - y)

    print xmin, ymin, xmax, ymax
    scene = Scene(fn[:-4], ceil(ymax - ymin + 10), ceil(xmax - xmin + 10))
    for loop in loops:
        circle = is_circle(loop)
        if circle:
            x ,y, d, n = circle
            scene.add(Circle(p(x, y), d / 2, (255,0,0)))
            scene.add(Line( p(x + d, y), p(x - d, y) ))
            scene.add(Line( p(x, y + d), p(x, y - d) ))
            scene.add(Text( p(x + d / 2, y + d / 2), str(round(d,1)) ))
            #scene.add(Text( p(x + d, y - d - 3), "[%0.1f, %0.1f]" % (x, y), 12 ))
        else:
            last = loop[-1]
            for point in loop:
                scene.add(Line(p(last[0],last[1]),p(point[0],point[1])))
                last = point
    scene.write_svg()

if __name__ == '__main__':
    import sys
    dxf_to_svg(sys.argv[1])

########NEW FILE########
__FILENAME__ = InkCL
#!/usr/bin/env python
#from http://kaioa.com/node/42

import os, subprocess, sys

def run(*args):
    print "inkscape",
    for arg in args:
        print arg,
    print
    run = subprocess.Popen(["inkscape"] + list(args) + [" -z"], shell = False, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out,err=[e.splitlines() for e in run.communicate()]
    return run.returncode, out, err

if __name__=='__main__':
    r = run(sys.argv[1:])
    if not r[0]==0:
        print 'return code:',r[0]
    for l in r[1]:
        print l
    for l in r[2]:
        print l

########NEW FILE########
__FILENAME__ = make_machine
#!/usr/bin/env python

import sys
from bom import boms
from sheets import sheets
from stls import stls
from plates import plates

def make_machine(machine):
    boms(machine)
    sheets(machine)
    stls(machine)
    plates(machine)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        make_machine(sys.argv[1])
    else:
        print "usage: make_machine [mendel|sturdy|your_machine]"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = openscad
import subprocess

def run(*args):
    print "openscad",
    for arg in args:
        print arg,
    print
    log = open("openscad.log", "w")
    subprocess.call(["openscad"] + list(args), stdout = log, stderr = log)
    log.close()

########NEW FILE########
__FILENAME__ = plates
#!/usr/bin/env python

import sys
import os
import shutil
from stls import stls, bom_to_stls

plate_list = [
    "cal.stl",
    "atx_brackets.stl",
    "bar_clamps.stl",
    "cable_clips.stl",
    "d_motor_brackets.stl",
    "fixing_blocks.stl",
    "ribbon_clamps.stl",
    "small_bits.stl",
    "spool_holder_brackets.stl",
    "wades_extruder.stl",
    "x_carriage_parts.stl",
    "y_bearing_mounts.stl",
    "y_belt_anchors.stl",
    "z_motor_brackets.stl"
]

def plates(machine):
    #
    # Make the target directory
    #
    target_dir = machine + "/stls/printed"
    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)
    #
    # Make the stls in the list
    #
    if machine == "dibond" or machine == "huxley":
        plate_list.remove("cable_clips.stl");
    used = stls(machine, plate_list)
    #
    # Move them to the plates directory
    #
    for file in plate_list:
        shutil.move(machine + "/stls/"+ file, target_dir + "/" + file)
    #
    # Copy all the stls that are not in the plates to the plates directory
    #
    for file in bom_to_stls(machine):
        path = machine + "/stls/"+ file
        if not file in used:
            if os.path.isfile(path):
                shutil.copy(path, target_dir + "/" + file)
            else:
                print "can't find %s to copy" % path

if __name__ == '__main__':
    if len(sys.argv) > 1:
        plates(sys.argv[1])
    else:
        print "usage: plates [mendel|sturdy|your_machine]"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = render
#!/usr/bin/env python

import os
import sys
import shutil
import subprocess

def render(machine):
    stl_dir = machine + os.sep + "stls"
    render_dir = machine + os.sep + "render"

    if os.path.isdir(render_dir):
        shutil.rmtree(render_dir)   #clear out any dross
    os.makedirs(render_dir)
    #
    # List of individual part files
    #
    stls = [i[:-4] for i in os.listdir(stl_dir) if i[-4:] == ".stl"]
    #
    # Add the multipart files
    #
    for i in  os.listdir(stl_dir + os.sep + "printed"):
        if not i[:-4] in stls:
            stls.append("printed" + os.sep + i[:-4])

    for i in stls:
        command = 'blender -b  utils' + os.sep + 'render.blend -P utils' + os.sep + 'viz.py -- ' + \
            stl_dir + os.sep + i + '.stl ' + render_dir + os.sep + i + '.png'
        print(command)
        subprocess.check_output(command.split())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        render(sys.argv[1])
    else:
        print "usage: render [mendel|sturdy|your_machine]"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = sheets
#!/usr/bin/env python

import os
import openscad
import InkCL
import shutil
import sys
from dxf import *

source_dir = "scad"

def sheets(machine):
    #
    # Make the target directory
    #
    target_dir = machine + "/sheets"
    if os.path.isdir(target_dir):
        try:
            shutil.rmtree(target_dir)
            os.makedirs(target_dir)
        except:
            pass
    else:
        os.makedirs(target_dir)

    #
    # Set the target machine
    #
    f = open("scad/conf/machine.scad","wt")
    f. write("include <%s_config.scad>\n" % machine);
    f.close()

    #
    # Find all the scad files
    #
    for filename in os.listdir(source_dir):
        if filename[-5:] == ".scad":
            #
            # find any modules ending in _dxf
            #
            for line in open(source_dir + "/" + filename, "r").readlines():
                words = line.split()
                if(len(words) and words[0] == "module"):
                    module = words[1].split('(')[0]
                    if module[-4:] == "_dxf":
                        #
                        # make a file to use the module
                        #
                        dxf_maker_name = target_dir + "/" + module + ".scad"
                        f = open(dxf_maker_name, "w")
                        f.write("use <../../%s/%s>\n" % (source_dir, filename))
                        f.write("%s();\n" % module);
                        f.close()
                        #
                        # Run openscad on the created file
                        #
                        base_name = target_dir + "/" + module[:-4]
                        dxf_name = base_name + ".dxf"
                        openscad.run("-o", dxf_name, dxf_maker_name)
                        #
                        # Make SVG drill template
                        #
                        dxf_to_svg(dxf_name)
                        #
                        # Make PDF for printing
                        #
                        InkCL.run("-f", base_name + ".svg", "-A", base_name + ".pdf")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        sheets(sys.argv[1])
    else:
        print "usage: sheets [mendel|sturdy|your_machine]"
        sys.exit(1)

########NEW FILE########
__FILENAME__ = stls
#!/usr/bin/env python

import os
import openscad
import shutil
import sys
import c14n_stl

source_dir = "scad"

def bom_to_stls(machine):
    #
    # Make a list of all the stls in the BOM
    #
    stl_files = []
    for line in open(machine + "/bom/bom.txt", "rt").readlines():
        words = line.split()
        if words:
            last_word = words[-1]
            if len(last_word) > 4 and last_word[-4:] == ".stl":
                stl_files.append(last_word)
    return stl_files

def stls(machine, parts = None):
    #
    # Make the target directory
    #
    target_dir = machine + "/stls"
    if os.path.isdir(target_dir):
        if not parts:
            shutil.rmtree(target_dir)   #if making the BOM clear the directory first
            os.makedirs(target_dir)
    else:
        os.makedirs(target_dir)

    #
    # Set the target machine
    #
    f = open("scad/conf/machine.scad","wt")
    f. write("include <%s_config.scad>\n" % machine);
    f.close()

    #
    # Decide which files to make
    #
    if parts:
        targets = list(parts)           #copy the list so we dont modify the list passed in
    else:
        targets = bom_to_stls(machine)
    #
    # Find all the scad files
    #
    used = []
    for filename in os.listdir(source_dir):
        if filename[-5:] == ".scad":
            #
            # find any modules ending in _stl
            #
            for line in open(source_dir + "/" + filename, "r").readlines():
                words = line.split()
                if(len(words) and words[0] == "module"):
                    module = words[1].split('(')[0]
                    stl = module.replace("_stl", ".stl")
                    if stl in targets:
                        #
                        # make a file to use the module
                        #
                        stl_maker_name = source_dir + "/stl.scad"
                        f = open(stl_maker_name, "w")
                        f.write("use <%s>\n" % filename)
                        f.write("%s();\n" % module);
                        f.close()
                        #
                        # Run openscad on the created file
                        #
                        stl_name = target_dir + "/" + module[:-4] + ".stl"
                        openscad.run("-D$bom=1","-o", stl_name, stl_maker_name)
                        c14n_stl.canonicalise(stl_name)
                        targets.remove(stl)
                        #
                        # Add the files on the BOM to the used list for plates.py
                        #
                        for line in open("openscad.log"):
                            if line[:7] == 'ECHO: "' and line[-6:] == '.stl"\n':
                                used.append(line[7:-2])
    #
    # List the ones we didn't find
    #
    for module in targets:
        print "Could not find", module
    return used

if __name__ == '__main__':
    if len(sys.argv) > 1:
        stls(sys.argv[1], sys.argv[2:])
    else:
        print "usage: stls [mendel|sturdy|your_machine] [part.stl ...]"
    sys.exit(1)

########NEW FILE########
__FILENAME__ = svg
## {{{ http://code.activestate.com/recipes/325823/ (r1)
#!/usr/bin/env python
"""\
SVG.py - Construct/display SVG scenes.

The following code is a lightweight wrapper around SVG files. The metaphor
is to construct a scene, add objects to it, and then write it to a file
to display it.
"""

import os

class Scene:
    def __init__(self,name="svg",height=400,width=400):
        self.name = name
        self.items = []
        self.height = height
        self.width = width
        return

    def add(self,item): self.items.append(item)

    def strarray(self):
        var = ["<?xml version=\"1.0\"?>\n",
               '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" height="%dmm" width="%dmm" >\n' % (self.height,self.width),
               ' <g style="fill-opacity:1.0; stroke:black; stroke-width:1;">\n'
              ]
        for item in self.items: var += item.strarray()
        var += [" </g>\n</svg>\n"]
        return var

    def write_svg(self,filename=None):
        if filename:
            self.svgname = filename
        else:
            self.svgname = self.name + ".svg"
        file = open(self.svgname,'w')
        file.writelines(self.strarray())
        file.close()
        return

    def display(self):
        os.system("%s" % (self.svgname))
        return


class Line:
    def __init__(self,start,end):
        self.start = start #xy tuple
        self.end = end     #xy tuple
        return

    def strarray(self):
        return ['  <line x1="%fmm" y1="%fmm" x2="%fmm" y2="%fmm" />\n' % (self.start[0],self.start[1],self.end[0],self.end[1])]


class Circle:
    def __init__(self,center,radius,color):
        self.center = center #xy tuple
        self.radius = radius
        self.color = color   #rgb tuple in range(0,256)
        return

    def strarray(self):
        return ['  <circle cx="%fmm" cy="%fmm" r="%fmm" fill="none"/>\n' % (self.center[0],self.center[1],self.radius)]

class Rectangle:
    def __init__(self,origin,height,width,color):
        self.origin = origin
        self.height = height
        self.width = width
        self.color = color
        return

    def strarray(self):
        return ['  <rect x="%dmm" y="%dmm" height="%dmm"\n' % (self.origin[0],self.origin[1],self.height),
                '    width="%dmm" style="fill:%s;" />\n' % (self.width,colorstr(self.color))]

class Text:
    def __init__(self,origin,text,size=24):
        self.origin = origin
        self.text = text
        self.size = size
        return

    def strarray(self):
        return ['  <text x="%dmm" y="%dmm" font-size="%d">\n' % (self.origin[0],self.origin[1],self.size),
                '   %s\n' % self.text,
                '  </text>\n']


def colorstr(rgb): return "#%x%x%x" % (rgb[0]/16,rgb[1]/16,rgb[2]/16)

def test():
    scene = Scene('test')
    scene.add(Rectangle((50,50),100,100,(0,255,255)))
    scene.add(Line((100,100),(150,100)))
    scene.add(Line((100,100),( 50,100)))
    scene.add(Line((100,100),(100,150)))
    scene.add(Line((100,100),(100, 50)))
    scene.add(Circle((100,100),15,(0,0,255)))
    scene.add(Circle((100,150),15,(0,255,0)))
    scene.add(Circle((150,100),15,(255,0,0)))
    scene.add(Circle(( 50,100),15,(255,255,0)))
    scene.add(Circle((100, 50),15,(255,0,255)))
    scene.add(Text((25,25),"Testing SVG"))
    scene.write_svg()
    scene.display()
    return

if __name__ == '__main__': test()
## end of http://code.activestate.com/recipes/325823/ }}}

########NEW FILE########
__FILENAME__ = viz
import bpy
import sys

global ob
global cam_target
mat = 'abs'

def load_stl(file_path):
    global cam_target,ob
    # load
    bpy.ops.import_mesh.stl(filepath=file_path)
    # select properly
    ob = bpy.context.selected_objects[0]
    print(ob)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select = True
    # remove doubles and clean
    #py.ops.object.editmode_toggle()
    #bpy.ops.mesh.select_all(action='TOGGLE')
    #bpy.ops.mesh.remove_doubles(limit=0.0001)
    #bpy.ops.mesh.normals_make_consistent(inside=False)
    #bpy.ops.object.editmode_toggle()
    bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')
    # place
    z_dim = ob.dimensions[2]
    print(z_dim)
    bpy.ops.transform.translate(value=(0,0,z_dim/2.0))
    cam_target = (0,0,z_dim/3.0)
    # assign material
    ob.material_slots.data.active_material = bpy.data.materials[mat]

def place_camera():
    global cam_target
    max_dim = max(ob.dimensions[0] * 0.75, ob.dimensions[1] * 0.75,  ob.dimensions[2])
    print(max_dim)
    bpy.data.objects['target'].location = cam_target
    cam = bpy.data.objects['Camera'].location.x = max_dim * 2.4

def render_thumb(image,gl=False,anim=False):
    if gl:
        if anim:
            bpy.data.scenes['Scene'].render.filepath = "/tmp/"+ob.name+"#"
            bpy.ops.render.opengl(animation=True)
        else:
            bpy.ops.render.opengl(write_still=True)
            bpy.data.images['Render Result'].save_render(filepath=image)
    else:
        if anim:
            bpy.data.scenes['Scene'].render.filepath = "/tmp/"+ob.name+"#"
            bpy.ops.render.render(animation=True)
        else:
            bpy.ops.render.render(write_still=True)
            bpy.data.images['Render Result'].save_render(filepath=image)

image = sys.argv[-1]
stl = sys.argv[-2]
print(stl)
print(image)

load_stl(stl)
place_camera()
render_thumb(image,gl=False)
#bpy.ops.object.delete()

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python

import os
import sys
import shutil
import openscad



def views(machine):
    scad_dir = "views"
    render_dir = machine + os.sep + "views"

    if not os.path.isdir(render_dir):
        os.makedirs(render_dir)
    #
    # Set the target machine
    #
    f = open("scad/conf/machine.scad","wt")
    f.write("include <%s_config.scad>\n" % machine);
    f.close()
    #
    # List of individual part files
    #
    scads = [i for i in os.listdir(scad_dir) if i[-5:] == ".scad"]

    for scad in scads:
        scad_name = scad_dir + os.sep + scad
        png_name = render_dir + os.sep + scad[:-4] + "png"

        for line in open(scad_name, "r").readlines():
            words = line.split()
            if len(words) > 10 and words[0] == "//":
                cmd = words[1]
                if cmd == "view" or cmd == "assembled" or cmd == "assembly":
                    w = int(words[2]) * 2
                    h = int(words[3]) * 2

                    dx = -float(words[4])
                    dy = -float(words[5])
                    dz = -float(words[6])

                    rx = 360.0 - float(words[7]) + 90
                    ry = 360.0 - float(words[8])
                    rz = 360.0 - float(words[9])

                    d = float(words[10])
                    camera = "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f" % (dx, dy, dz, rx, ry, rz, d)

                    exploded = "0"
                    if cmd == "assembly":
                        exploded = "1"

                    if cmd == "assembled":
                        png_name = png_name.replace("assembly","assembled")

                    if not os.path.isfile(png_name) or os.path.getmtime(png_name) < os.path.getmtime(scad_name):
                        openscad.run("--projection=p",
                                    ("--imgsize=%d,%d" % (w, h)),
                                     "--camera=" + camera,
                                      "-D$exploded=" + exploded,
                                      "-o", png_name, scad_name)
                        print

if __name__ == '__main__':
    if len(sys.argv) > 1:
        views(sys.argv[1])
    else:
        print "usage: views [mendel|sturdy|your_machine]"
        sys.exit(1)

########NEW FILE########
