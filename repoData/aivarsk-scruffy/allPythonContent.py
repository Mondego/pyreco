__FILENAME__ = common
# Copyright (C) 2011 by Aivars Kalvans <aivars.kalvans@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import subprocess
from PIL import Image, ImageChops
from operator import attrgetter

def hasFont(font_name):
    """ Checks if font is installed (using fc-list; are there other possibilities?) """
    stdout = subprocess.Popen(['fc-list', font_name], shell=True, stdout=subprocess.PIPE).stdout
    return len(stdout.readlines()) > 0

def defaultScruffyFont():
    """ Returns installed font with scruffy look """
    for font_name in ('Purisa',):
        if hasFont(font_name):
            return font_name
    return None

class Box:
    n = 0
    def __init__(self, name, spec):
        self.name = name
        self.spec = spec
        self.uid = 'A%03d' % Box.n
        Box.n += 1

    def update(self, spec):
        if len(self.spec) < len(spec):
            self.spec = spec
        return self

class Boxes:
    def __init__(self):
        self.boxes = {}

    def addBox(self, spec):
        name = spec.split('|')[0].strip()
        if name not in self.boxes:
            self.boxes[name] = Box(name, spec)
        return self.boxes[name].update(spec)

    def getBoxes(self):
        res = self.boxes.values()
        res.sort(key=attrgetter('uid'))
        return res 

def splitYUML(spec):
    word = ''
    shapeDepth = 0
    for c in spec:
        if c == '[':
            shapeDepth += 1
        elif c == ']':
            shapeDepth -= 1

        if shapeDepth == 1 and c == '[':
            yield word.strip()
            word = c
            continue

        word += c
        if shapeDepth == 0 and c == ']':
            yield word.strip()
            word = ''
    if word:
        yield word.strip()

def crop(fin, fout):
    img = Image.open(fin)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    bg = Image.new('RGB', img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg)
    area = img.crop(diff.getbbox())
    area.save(fout, 'png')

########NEW FILE########
__FILENAME__ = scruffy
#!/usr/bin/env python
# Copyright (C) 2011 by Aivars Kalvans <aivars.kalvans@gmail.com>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Makes SVG shapes look hand-drawn like "scruffy" UML diagrams:
#   http://yuml.me/diagram/scruffy/class/samples
#
# Adds new points (with slight offsets) between existing points.
# Changes font to ..?
# Adds shadows to polygons
# Adds gradient

import sys
import math
import random
import xml.etree.ElementTree as etree

gCoordinates = 'px'

def getPixels(n):
    if gCoordinates == 'px': return n
    elif gCoordinates == 'in': return n * 96.0

def putPixels(n):
    if gCoordinates == 'px': return n
    elif gCoordinates == 'in': return n / 96.0

def parsePoints(points):
    points = points.split()
    return [(getPixels(float(x)), getPixels(float(y))) for x, y in [point.split(',') for point in points]]

def lineLength(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)

def splitLine(p1, p2, l):
    ''' find point on line l points away from p1 '''
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    lp = math.sqrt(dx * dx + dy * dy)
    ax = dx / lp
    ay = dy / lp
    return (p1[0] + l * ax, p1[1] + l * ay)

def frandrange(start, stop):
    ''' random.randrange for floats ''' 
    start, stop = int(start * 10.0), int(stop * 10.0)
    r = random.randrange(start, stop)
    return r / 10.0

SVG_NS = 'http://www.w3.org/2000/svg'
def ns(tag):
    return '{%s}%s' % (SVG_NS, tag)

def transformRect2Polygon(elem):
    elem.tag = ns('polygon')
    x = float(elem.attrib['x'])
    y = float(elem.attrib['y'])
    w = float(elem.attrib['width'])
    h = float(elem.attrib['height'])
    elem.attrib['points'] = '%f,%f %f,%f %f,%f %f,%f' % (
            x, y,
            x + w, y,
            x + w, y + h,
            x, y + h
            )

def transformLine2Polyline(elem):
    elem.tag = ns('polyline')
    elem.attrib['points'] = '%(x1)s,%(y1)s %(x2)s,%(y2)s' % elem.attrib
    for key in ('x1', 'x2', 'y1', 'y2'): del elem.attrib[key]

def transformPolyline(elem):
    points = parsePoints(elem.attrib['points'])
    newPoints = []
    for i in xrange(len(points) - 1):
        p1, p2 = points[i], points[i + 1]

        newPoints.append(p1)
        l = lineLength(p1, p2)
        if l > 10:
            p = splitLine(p1, p2, frandrange(4, l - 4))
            newPoints.append((
                p[0] + frandrange(0.5, 2) * random.choice([1, -1]),
                p[1] + frandrange(0.5, 2) * random.choice([1, -1])
            ))

    newPoints.append(points[-1])

    elem.attrib['points'] = ' '.join(['%f,%f' % (putPixels(p[0]), putPixels(p[1])) for p in newPoints])

_usedColors = {}

def transformPolygon(elem):
    transformPolyline(elem)
    fill = elem.get('fill', '')
    if not fill or fill == 'none':
        elem.attrib['fill'] = 'white'

def transformText(elem, font):
    elem.attrib['font-family'] = font

def transformAddShade(root, elem):
    if elem.get('fill', '') == 'white' and elem.get('stroke', '') == 'white':
        # Graphviz puts everything in one big polygon. Skip it!
        return

    # Need to prepend element of the same shape
    shade = root.makeelement(elem.tag, elem.attrib)
    for i, child in enumerate(root):
        if child == elem:
            root.insert(i, shade)
            break

    shade.attrib['fill'] = '#999999'
    shade.attrib['stroke'] = '#999999'
    shade.attrib['stroke-width'] = shade.attrib.get('stroke-width', '1')
    # check for transform
    #shade.attrib['transform'] = 'translate(%f, %f)' % (putPixels(4), putPixels(-4))
    shade.attrib['transform'] = 'translate(%f, %f) ' % (putPixels(4), putPixels(4))
    #shade.attrib['style'] = 'opacity:0.75;filter:url(#filterBlur)'

def transformAddGradient(elem):
    if elem.get('fill', '') == 'white' and elem.get('stroke', '') == 'white':
        # Graphviz puts everything in one big polygon. Skip it!
        return

    fill = elem.get('fill', '')
    if fill == 'none':
        elem.attrib['fill'] = 'white'
    elif fill != 'black' and fill:
        _usedColors[fill] = True
        elem.attrib['style'] = 'fill:url(#' + fill + ');' + elem.attrib.get('style', '')

def _transform(root, options, level=0):
    for child in root[:]:
        if child.tag == ns('rect'):
            transformRect2Polygon(child)
        elif child.tag == ns('line'):
            transformLine2Polyline(child)

        # Skip background rect/polygon
        if child.tag == ns('polygon') and level != 0:
            transformPolygon(child)
            if options.shadow:
                transformAddShade(root, child)
            transformAddGradient(child)

        elif child.tag == ns('path'):
            #transformAddShade(root, child)
            pass
        elif child.tag == ns('polyline'):
            transformPolyline(child)
            #see class diagram - shade of inside line
            #transformAddShade(root, child)
        elif child.tag == ns('text'):
            if options.font:
                transformText(child, options.font)

        _transform(child, options, level + 1)

    if level == 0:
        defs = root.makeelement(ns('defs'), {})
        root.insert(0, defs)
        filterBlur = etree.SubElement(defs, ns('filter'), {'id': 'filterBlur'})
        etree.SubElement(filterBlur, ns('feGaussianBlur'), {'stdDeviation': '0.69', 'id':'feGaussianBlurBlur'})
        for name in _usedColors:
            gradient = etree.SubElement(defs, ns('linearGradient'), {'id': name, 'x1':"0%", 'xy':"0%", 'x2':"100%", 'y2':"100%"})
            etree.SubElement(gradient, ns('stop'), {'offset':'0%', 'style':'stop-color:white;stop-opacity:1'}) 
            etree.SubElement(gradient, ns('stop'), {'offset':'50%', 'style':'stop-color:%s;stop-opacity:1' % name}) 

def transform(fin, fout, options):
    '''
        Read svg from file object fin, write output to file object fout

        options.png (boolean)   Try to produce PNG output
        options.font (string)   Font family to use (Ubuntu: Purisa)
    '''
    etree.register_namespace('', 'http://www.w3.org/2000/svg')
    root = etree.parse(fin).getroot()


    w, h = root.attrib.get('width', ''), root.attrib.get('height', '')
    if w.endswith('in') or h.endswith('in'):
        global gCoordinates
        gCoordinates = 'in'

    _transform(root, options)

    scruffySvg = etree.tostring(root) + '\n'

    if options.png:
        import subprocess
        png = subprocess.Popen(['rsvg-convert', '-f', 'png'], stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(input=scruffySvg)[0]
        fout.write(png)
    else:
        fout.write(scruffySvg)

def main():
    import optparse

    parser = optparse.OptionParser(usage='usage: %prog [options] [input file]')
    parser.add_option('-p', '--png', action='store_true', dest='png',
                    help='create a png file (requires rsvg-convert)')
    parser.add_option('-o', '--output', action='store', dest='output',
                    help='output file name')
    parser.add_option('--font-family', action='store', dest='font',
                    help='set output font family')
    (options, args) = parser.parse_args()

    if len(args) > 1:
        parser.error('Too many arguments')

    fin, fout = sys.stdin, sys.stdout
    if options.output:
        fout = open(options.output, 'wb')

    if len(args) > 0:
        fin = open(args[0])

    transform(fin, fout, options)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = suml2pic
#!/usr/bin/env python
# Copyright (C) 2011 by Aivars Kalvans <aivars.kalvans@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

'''
[class]
[class]message>[class]
[class]<message[class]
'''

import os
import common

sequence_pic = os.path.join(os.path.dirname(__file__), 'sequence.pic')

def sumlExpr(spec):
    expr = []
    for part in common.splitYUML(spec):
        if not part: continue
        if part == ',':
            if expr: yield expr
            expr = []

        # [something like this]
        elif part[0] == '[' and part[-1] == ']':
            part = part[1:-1]
            expr.append(('record', part.strip()))
        # <message
        # >message
        elif part[0] in '<>':
            expr.append((part[0], part[1:].strip()))
        # message>
        # message<
        elif part[-1] in '<>':
            expr.append((part[-1], part[:-1].strip()))

    if expr: yield expr

def getFontWidth():
    return 0.13

def suml2pic(spec, options):
    boxes = common.Boxes()
    exprs = list(sumlExpr(spec))

    pic = []
    pic.append('.PS')
    pic.append('copy "%s";' % (sequence_pic))
    pic.append('underline=0;')

    messages = []
    for expr in exprs:
        assert len(expr) in (1, 3)
        if len(expr) == 1:
            assert expr[0][0] == 'record'
            boxes.addBox(expr[0][1])

        elif len(expr) == 3:
            assert expr[0][0] == 'record'
            assert expr[2][0] == 'record'

            box1 = boxes.addBox(expr[0][1])
            box2 = boxes.addBox(expr[2][1])

            msgType = expr[1][0]
            if msgType == '>':
                messages.append('message(%s,%s,"%s");' % (box1.uid, box2.uid, expr[1][1]))
            elif msgType == '<':
                messages.append('message(%s,%s,"%s");' % (box2.uid, box1.uid, expr[1][1]))

    all_boxes = boxes.getBoxes()

    for box in all_boxes:
        #pic.append('object(%s,"%s");' % (box.uid, box.spec))
        pic.append('object3(%s,"%s",%f);' % (box.uid, box.spec, getFontWidth() * len(box.spec)))
    pic.append('step();')
    for box in all_boxes:
        pic.append('active(%s);' % (box.uid))

    pic.extend(messages)

    pic.append('step();')
    for box in all_boxes:
        pic.append('complete(%s);' % (box.uid))

    pic.append('.PE')
    return '\n'.join(pic) + '\n'

def transform(expr, fout, options):
    pic = suml2pic(expr, options)

    if options.png or options.svg:
        import subprocess
        import StringIO

        if options.scruffy:
            import scruffy

            svg = subprocess.Popen(['pic2plot', '-Tsvg'], stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(input=pic)[0]
            if options.png:
                tocrop = StringIO.StringIO()
                scruffy.transform(StringIO.StringIO(svg), tocrop, options)
                common.crop(StringIO.StringIO(tocrop.getvalue()), fout)
            else:
                scruffy.transform(StringIO.StringIO(svg), fout, options)
        elif options.png:
            png = subprocess.Popen(['pic2plot', '-Tpng'], stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(input=pic)[0]
            common.crop(StringIO.StringIO(png), fout)
        elif options.svg:
            subprocess.Popen(['pic2plot', '-Tsvg'], stdin=subprocess.PIPE, stdout=fout).communicate(input=pic)
    else:
        fout.write(pic)

########NEW FILE########
__FILENAME__ = yuml2dot
#!/usr/bin/env python
# Copyright (C) 2011 by Aivars Kalvans <aivars.kalvans@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Creates class diagrams in .dot format from yUML syntax
#   http://yuml.me/diagram/class/draw

'''
Class   [Customer]
Directional [Customer]->[Order]
Bidirectional   [Customer]<->[Order]
Aggregation [Customer]+-[Order] or [Customer]<>-[Order]
Composition [Customer]++-[Order]
Inheritance [Customer]^[Cool Customer], [Customer]^[Uncool Customer]
Dependencies    [Customer]uses-.->[PaymentStrategy]
Cardinality [Customer]<1-1..2>[Address]
Labels  [Person]customer-billingAddress[Address]
Notes   [Person]-[Address],[Address]-[note: Value Object]
Full Class  [Customer|Forename;Surname;Email|Save()]
Splash of Colour    [Customer{bg:orange}]<>1->*[Order{bg:green}]
Comment:        // Comments

[Foo|valueProp]
[Foo]entityRef->[Bar]
[Foo]entityComp++->ownedBy[Baz]
[Foo]oneToMany->*[FooBar]
[Bar|name]
[FooBar|value]
[FooBar]^[Bar]

'''

import textwrap
import common

def escape_label(label):
    """ Escape label string for DOT
        TODO: check spec if everything is here
    """
    label = label.replace('{', '\\{').replace('}', '\\}')
    label = label.replace(';', '\\n')
    label = label.replace(' ', '\\ ')
    label = label.replace('<', '\\<').replace('>', '\\>')
    label = label.replace('\\n\\n', '\\n')
    return label

def yumlExpr(spec):
    expr = []
    for part in common.splitYUML(spec):
        if not part: continue
        # End of line, eat multiple empty lines (part is like ',,,,')
        if len(part) > 0 \
                and (len(part.strip(',')) == 0 or part.strip(',').startswith('//')):
            if expr: yield expr
            expr = []
        elif part == '^':
            expr.append(('edge', 'empty', '', 'none', '', 'solid'))

        # [something like this]
        # [something like this {bg:color}]
        # [note: something like this {bg:color}]
        elif part[0] == '[' and part[-1] == ']':
            part = part[1:-1]
            bg = ''
            if part[-1] == '}':
                x = part.split('{bg:')
                assert len(x) == 2
                part = x[0]
                bg = x[1][:-1]

            if part.startswith('note:'):
                expr.append(('note', part[5:].strip(), bg))
            elif '[' in part and ']' in part:
                p = part.split('[')
                part = p[0]
                nodes = [node.replace(']', '').strip() for node in p[1:]]
                expr.append(('cluster', part.strip(), bg, nodes))
            else:
                expr.append(('record', part.strip(), bg))
        elif '-' in part:
            if '-.-' in part:
                style = 'dashed'
                x = part.split('-.-')
            else:
                style = 'solid'
                x = part.split('-')

            assert len(x) == 2
            left, right = x

            def processLeft(left):
                if left.startswith('<>'):
                    return ('odiamond', left[2:])
                elif left.startswith('++'):
                    return ('diamond', left[2:])
                elif left.startswith('+'):
                    return ('odiamond', left[1:])
                elif left.startswith('<') or left.startswith('>'):
                    return ('vee', left[1:])
                elif left.startswith('^'):
                    return ('empty', left[1:])
                else:
                    return ('none', left )

            lstyle, ltext = processLeft(left)

            if right.endswith('<>'):
                rstyle = 'odiamond'
                rtext = right[:-2]
            elif right.endswith('++'):
                rstyle = 'diamond'
                rtext = right[:-2]
            elif right.endswith('+'):
                rstyle = 'odiamond'
                rtext = right[:-1]
            elif right.endswith('>'):
                rstyle = 'vee'
                rtext = right[:-1]
            elif right.endswith('^'):
                rstyle = 'empty'
                rtext = right[:-1]
            else:
                # zOMG, it seams valid
                rstyle, rtext = processLeft(right)

            expr.append(('edge', lstyle, ltext, rstyle, rtext, style))
    if expr: yield expr

def recordName(label):
    # for classes/records allow first entry with all attributes and later only with class name
    name = label.split('|')[0].strip()
    return name

def yuml2dot(spec, options):
    uids = {}
    class Foo:
        def __init__(self, label):
            self.uid = label

    exprs = list(yumlExpr(spec))

    if len(exprs) > 5: options.rankdir = 'TD'
    else: options.rankdir = 'LR'

    dot = []
    dot.append('digraph G {')
    dot.append('    ranksep = 1')
    dot.append('    rankdir = %s' % (options.rankdir))

    for expr in exprs:
        for elem in expr:
            if elem[0] == 'cluster':
                label = elem[1]
                if recordName(label) in uids: continue
                uid = 'cluster_A' + str(len(uids))
                uids[recordName(label)] = Foo(uid)

                dot.append('    subgraph %s {' % (uid))
                dot.append('        label = "%s"' % (label))
                dot.append('        fontsize = 10')

                if options.font:
                    dot.append('        fontname = "%s"' % (options.font))
                for node in elem[3]:
                    dot.append('        %s' % (uids[node].uid))
                dot.append('    }')
            elif elem[0] in ('note', 'record'):
                label = elem[1]
                if recordName(label) in uids: continue
                uid = 'A' + str(len(uids))
                uids[recordName(label)] = Foo(uid)

                dot.append('    node [')
                dot.append('        shape = "%s"' % (elem[0]))
                dot.append('        height = 0.50')
                #dot.append('        margin = 0.11,0.055')
                dot.append('        fontsize = 10')
                if options.font:
                    dot.append('        fontname = "%s"' % (options.font))
                dot.append('        margin = "0.20,0.05"')
                dot.append('    ]')
                dot.append('    %s [' % (uid))

                # Looks like table / class with attributes and methods
                if '|' in label:
                    label = label + '\\n'
                    label = label.replace('|', '\\n|')
                else:
                    lines = []
                    for line in label.split(';'):
                        lines.extend(textwrap.wrap(line, 20, break_long_words=False))
                    label = '\\n'.join(lines)

                label = escape_label(label)

                if '|' in label and options.rankdir == 'TD':
                    label = '{' + label + '}'

                dot.append('        label = "%s"' % (label))
                if elem[2]:
                    dot.append('        style = "filled"')
                    dot.append('        fillcolor = "%s"' % (elem[2]))
                dot.append('    ]')

        if len(expr) == 3 and expr[1][0] == 'edge':
            elem = expr[1]
            dot.append('    edge [')
            dot.append('        shape = "%s"' % (elem[0]))
            dot.append('        dir = "both"')
            # Dashed style for notes
            if expr[0][0] == 'note' or expr[2][0] == 'note':
                dot.append('        style = "dashed"')
            else:
                dot.append('        style = "%s"' % (elem[5]))
            dot.append('        arrowtail = "%s"' % (elem[1]))
            dot.append('        taillabel = "%s"' % (elem[2]))
            dot.append('        arrowhead = "%s"' % (elem[3]))
            dot.append('        headlabel = "%s"' % (elem[4]))
            dot.append('        labeldistance = 2')
            dot.append('        fontsize = 10')
            if options.font:
                dot.append('        fontname = "%s"' % (options.font))
            dot.append('    ]')
            dot.append('    %s -> %s' % (uids[recordName(expr[0][1])].uid, uids[recordName(expr[2][1])].uid))

    dot.append('}')
    return '\n'.join(dot) + '\n'

def transform(expr, fout, options):
    dot = yuml2dot(expr, options)

    if options.png or options.svg:
        import subprocess

        if options.scruffy:
            import StringIO
            import scruffy

            svg = subprocess.Popen(['dot', '-Tsvg'], stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(input=dot)[0]
            scruffy.transform(StringIO.StringIO(svg), fout, options)
        elif options.png:
            subprocess.Popen(['dot', '-Tpng'], stdin=subprocess.PIPE, stdout=fout).communicate(input=dot)
        elif options.svg:
            subprocess.Popen(['dot', '-Tsvg'], stdin=subprocess.PIPE, stdout=fout).communicate(input=dot)
    else:
        fout.write(dot)

########NEW FILE########
