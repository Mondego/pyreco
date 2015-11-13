__FILENAME__ = canvas
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Copyright (C) 2012 Karlisson Bezerra, contact@hacktoon.com

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''

from lib import inkex
from lib import simplestyle

class Canvas:
    """Canvas API helper class"""

    def __init__(self, width, height, context = "ctx"):
        self.obj = context
        self.code = []  #stores the code
        self.style = {}
        self.styleCache = {}  #stores the previous style applied
        self.width = width
        self.height = height

    def write(self, text):
        self.code.append("\t" + text.replace("ctx", self.obj) + "\n")

    def output(self):
        from textwrap import dedent
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
            <title>Inkscape Output</title>
        </head>
        <body>
            <canvas id='canvas' width='%d' height='%d'></canvas>
            <script>
            var %s = document.getElementById("canvas").getContext("2d");
            %s
            </script>
        </body>
        </html>
        """
        return dedent(html) % (self.width, self.height, self.obj, "".join(self.code))

    def putStyleInCache(self, style):
        """Checks if the last style used is the same or there's no style yet"""
        for x in style.values():
            if x != "":
                self.styleCache.update(style)
    


    def beginPath(self):
        self.write("ctx.beginPath();")

    def createLinearGradient(self, href, x1, y1, x2, y2):
        data = (href, x1, y1, x2, y2)
        self.write("var %s = ctx.createLinearGradient(%f,%f,%f,%f);" % data)

    def createRadialGradient(self, href, cx1, cy1, rx, cx2, cy2, ry):
        data = (href, cx1, cy1, rx, cx2, cy2, ry)
        self.write("var %s = ctx.createRadialGradient(%f,%f,%f,%f,%f,%f);" % data)

    def addColorStop(self, href, pos, color):
        self.write("%s.addColorStop(%f, %s);" % (href, pos, color))

    def getColor(self, rgb, a):
        r, g, b = simplestyle.parseColor(rgb)
        a = float(a)
        if a < 1:
            return "'rgba(%d, %d, %d, %.1f)'" % (r, g, b, a)
        else:
            return "'rgb(%d, %d, %d)'" % (r, g, b)

    def setOpacity(self, value):
        self.write("ctx.globalAlpha = %.1f;" % float(value))

    def setFill(self, value):
        try:
            alpha = self.style["fill-opacity"]
        except:
            alpha = 1
        if not value.startswith("url(") and not value.startswith("gradient="):
            fill = self.getColor(value, alpha)
            self.write("ctx.fillStyle = %s;" % fill)
        else:
            if value.startswith("gradient="):
                value = value.replace("gradient=", "")
                self.write("ctx.fillStyle = %s;" % value)

    def setStroke(self, value):
        try:
            alpha = self.style["stroke-opacity"]
        except:
            alpha = 1
        if not value.startswith("url(") and not value.startswith("gradient="):
            stroke = self.getColor(value, alpha)
            self.write("ctx.strokeStyle = %s;" % stroke)
        else:
            if value.startswith("gradient="):
                value = value.replace("gradient=", "")
                self.write("ctx.strokeStyle = %s;" % value)

    def setStrokeWidth(self, value):
        self.write("ctx.lineWidth = %f;" % inkex.unittouu(value))

    def setStrokeLinecap(self, value):
        self.write("ctx.lineCap = '%s';" % value)

    def setStrokeLinejoin(self, value):
        self.write("ctx.lineJoin = '%s';" % value)

    def setStrokeMiterlimit(self, value):
        self.write("ctx.miterLimit = %s;" % value)

    def setFont(self, value):
        self.write("ctx.font = \"%s\";" % value)

    def moveTo(self, x, y):
        self.write("ctx.moveTo(%f, %f);" % (x, y))

    def lineTo(self, x, y):
        self.write("ctx.lineTo(%f, %f);" % (x, y))

    def quadraticCurveTo(self, cpx, cpy, x, y):
        data = (cpx, cpy, x, y)
        self.write("ctx.quadraticCurveTo(%f, %f, %f, %f);" % data)

    def bezierCurveTo(self, x1, y1, x2, y2, x, y):
        data = (x1, y1, x2, y2, x, y)
        self.write("ctx.bezierCurveTo(%f, %f, %f, %f, %f, %f);" % data)

    def rect(self, x, y, w, h, rx = 0, ry = 0):
        if rx or ry:
            #rounded rectangle, starts top-left anticlockwise
            self.moveTo(x, y + ry)
            self.lineTo(x, y+h-ry)
            self.quadraticCurveTo(x, y+h, x+rx, y+h)
            self.lineTo(x+w-rx, y+h)
            self.quadraticCurveTo(x+w, y+h, x+w, y+h-ry)
            self.lineTo(x+w, y+ry)
            self.quadraticCurveTo(x+w, y, x+w-rx, y)
            self.lineTo(x+rx, y)
            self.quadraticCurveTo(x, y, x, y+ry)
        else:
            self.write("ctx.rect(%f, %f, %f, %f);" % (x, y, w, h))

    def arc(self, x, y, r, a1, a2, flag):
        data = (x, y, r, a1, a2, flag)
        self.write("ctx.arc(%f, %f, %f, %f, %.8f, %d);" % data)

    def fillText(self, text, x, y):
        self.write("ctx.fillText(\"%s\", %f, %f);" % (text, x, y))

    def translate(self, cx, cy):
        self.write("ctx.translate(%f, %f);" % (cx, cy))

    def rotate(self, angle):
        self.write("ctx.rotate(%f);" % angle)

    def scale(self, rx, ry):
        self.write("ctx.scale(%f, %f);" % (rx, ry))

    def transform(self, m11, m12, m21, m22, dx, dy):
        data = (m11, m12, m21, m22, dx, dy)
        self.write("ctx.transform(%f, %f, %f, %f, %f, %f);" % data)

    def save(self):
        self.write("ctx.save();")

    def restore(self):
        self.write("ctx.restore();")

    def fill(self):
        if "fill" in self.style and self.style["fill"] != "none":
            self.write("ctx.fill();")
        
    def stroke(self):
        if "stroke" in self.style and self.style["stroke"] != "none":
            self.write("ctx.stroke();")
        
    def closePath(self, is_closed=False):
        if is_closed:
            self.write("ctx.closePath();")
    def clip(self):
        self.write("ctx.clip();")

########NEW FILE########
__FILENAME__ = GradientHelper
from ink2canvas.lib.simpletransform import parseTransform

class GradientHelper(object):
    
    def __init__(self, abstractShape):
        self.abstractShape = abstractShape
      
    def hasGradient(self, key):
        style = self.abstractShape.getStyle()
        
        if key in style:
            styleParamater = style[key]
            if styleParamater.startswith("url(#linear"):
                return "linear"
            if styleParamater.startswith("url(#radial"):
                return "radial"
        return None

    def getGradientHref(self, key):
        style = self.abstractShape.getStyle()
        if key in style:
            return style[key][5:-1]
        return
      
    def setGradientFill(self):
        gradType = self.hasGradient("fill")
        if (gradType):
            gradient = self.setComponentGradient("fill", gradType)
            self.abstractShape.canvasContext.setFill("gradient=grad")           
            if(self.hasGradientTransform(gradient)):
                self.abstractShape.canvasContext.fill();
                self.abstractShape.canvasContext.restore()
                return True
            
    def setGradientStroke(self):   
        gradType = self.hasGradient("stroke")
        if (gradType):
            gradient = self.setComponentGradient("stroke", gradType)
            self.abstractShape.canvasContext.setStroke("gradient=grad")
            if(self.hasGradientTransform(gradient)):
                self.abstractShape.canvasContext.stroke();
                self.abstractShape.canvasContext.restore()
                return True
            
    def hasGradientTransform(self, gradient):
        return bool(gradient.attr("gradientTransform"))
    
    def setGradientTransform(self, gradient):
        dataString = gradient.attr("gradientTransform")
        dataMatrix = parseTransform(dataString)
        m11, m21, dx = dataMatrix[0]
        m12, m22, dy = dataMatrix[1]
        self.abstractShape.canvasContext.transform(m11, m12, m21, m22, dx, dy)
            
    def setComponentGradient(self, key, gradType):
        gradientId = self.getGradientHref(key)
        if(gradType == "linear"):
            gradient = self.abstractShape.rootTree.getLinearGradient(gradientId)
        if(gradType == "radial"):
            gradient = self.abstractShape.rootTree.getRadialGradient(gradientId)
        
        if(gradient.link != None):
            gradient.colorStops = self.abstractShape.rootTree.getLinearGradient(gradient.link).colorStops
            
        if(self.hasGradientTransform(gradient)):
            self.abstractShape.canvasContext.save()
            self.setGradientTransform(gradient)    
            
        if(gradType == "linear"):
            x1, y1, x2, y2 = gradient.getData()
            self.abstractShape.canvasContext.createLinearGradient("grad", x1, y1, x2, y2)
        if(gradType == "radial"):
            cx, cy, fx, fy, r = gradient.getData()
            self.abstractShape.canvasContext.createRadialGradient("grad", cx, cy, 0, fx, fy, r)
            
        for stopKey, stopValue in gradient.colorStops.iteritems():
            offset = float(stopKey)
            color = self.abstractShape.canvasContext.getColor(stopValue.split(";")[0].split(":")[1] , stopValue.split(";")[1].split(":")[1] )
            self.abstractShape.canvasContext.addColorStop("grad", offset, color)

        return gradient
    
    def createLinearGradient(self):
        x1, y1, x2, y2 = self.gradient.getData()
        self.abstractShape.canvasContext.createLinearGradient("grad", x1, y1, x2, y2)
        for stop in self.gradient.stops:
            color = self.canvasContext.getColor(stop.split(";")[0].split(":")[1] , stop.split(";")[1].split(":")[1])
            offset = float(stop.split(";")[2].split(":")[1])
            self.abstractShape.canvasContext.addColorStop("grad", offset, color)    
########NEW FILE########
__FILENAME__ = Ink2CanvasCore
import svg
from ink2canvas.svg.ClipPath import Clippath
from ink2canvas.svg.RadialGradient import Radialgradient
from ink2canvas.svg.LinearGradient import Lineargradient
from ink2canvas.svg import Root, Defs

class Ink2CanvasCore(): 
    
    def __init__(self, inkex, effect):
        self.inkex = inkex
        self.canvas = None
        self.effect = effect
        self.root = Root()
        
    def createClipPathNode(self,element,tag):
        for subTag in tag:
            tagName = self.getNodeTagName(subTag)
            className = tagName.capitalize()

            #if there's not an implemented class, continues
            if not hasattr(svg, className):
                continue
            # creates a instance of 'element'
            tipoDoClip = getattr(svg, className)(tagName, subTag, self.canvas, self.root)

            self.root.addChildClipPath(element.attr("id"),tipoDoClip)
    
    def createLinearGradient(self,element,tag):
        colorStops = {}
        for stop in tag:
            colorStops[stop.get("offset")] = stop.get("style")
        linearGrad = Lineargradient(None, tag, self.canvas, self.root)
        linearGrad.setColorStops(colorStops)
        self.root.addChildLinearGradient(linearGrad.attr("id"), linearGrad)
        if(linearGrad.attr("href","xlink") != None):
            linearGrad.link = linearGrad.attr("href","xlink")[1:]
        
    def createRadialGradient(self,element,tag):
        colorStops = {}
        for stop in tag:
            colorStops[stop.get("offset")] = stop.get("style")
        radialGrad = Radialgradient(None, tag, self.canvas, self.root)
        radialGrad.setColorStops(colorStops)
        self.root.addChildRadialGradient(radialGrad.attr("id"), radialGrad)
        if(radialGrad.attr("href","xlink") != None):
            radialGrad.link = radialGrad.attr("href","xlink")[1:]
    
    def createDrawable(self,element,tag):
        for eachTag in tag:
            elementChild = self.createElement(eachTag)
            if(elementChild == None):
                continue
            elementChild.setParent(element)
            element.addChild(elementChild)
            self.createDrawable(elementChild, eachTag)
                     
    def createModifiers(self,tag):
        for eachTag in tag:
            elementChild = self.createElement(eachTag)
            if(elementChild == None):
                continue
            if(isinstance(elementChild, Clippath)):
                self.createClipPathNode(elementChild,eachTag)
            else:
                if(isinstance(elementChild, Lineargradient)):
                    self.createLinearGradient(elementChild,eachTag)
                else:
                    if(isinstance(elementChild, Radialgradient)):
                        self.createRadialGradient(elementChild,eachTag)

    def createElement(self,tag):
        tagName = self.getNodeTagName(tag)
        className = tagName.capitalize()

        #if there's not an implemented class, continues
        if not hasattr(svg, className):
            return None
        # creates a instance of 'element'
        return  getattr(svg, className)(tagName, tag, self.canvas, self.root)

    def createTree(self,fileSVG):
        for tag in fileSVG:
            element = self.createElement(tag)
            if(element == None):
                continue
            if(isinstance(element, Defs)):
                self.createModifiers(tag)
            else:
                self.root.addChildDrawable(element)
                self.createDrawable(element,tag);
                        
    def getNodeTagName(self, node):
        return node.tag.split("}")[1]

########NEW FILE########
__FILENAME__ = inkex
#!/usr/bin/env python
"""
inkex.py
A helper module for creating Inkscape extensions

Copyright (C) 2005,2007 Aaron Spike, aaron@ekips.org

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""
import sys, copy, optparse, random, re
import gettext
from math import *
_ = gettext.gettext

#a dictionary of all of the xmlns prefixes in a standard inkscape doc
NSS = {
u'sodipodi' :u'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
u'cc'       :u'http://creativecommons.org/ns#',
u'ccOLD'    :u'http://web.resource.org/cc/',
u'svg'      :u'http://www.w3.org/2000/svg',
u'dc'       :u'http://purl.org/dc/elements/1.1/',
u'rdf'      :u'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
u'inkscape' :u'http://www.inkscape.org/namespaces/inkscape',
u'xlink'    :u'http://www.w3.org/1999/xlink',
u'xml'      :u'http://www.w3.org/XML/1998/namespace'
}

#a dictionary of unit to user unit conversion factors
uuconv = {'in':90.0, 'pt':1.25, 'px':1, 'mm':3.5433070866, 'cm':35.433070866, 'pc':15.0}
def unittouu(string):
    '''Returns userunits given a string representation of units in another system'''
    unit = re.compile('(%s)$' % '|'.join(uuconv.keys()))
    param = re.compile(r'(([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?)')

    p = param.match(string)
    u = unit.search(string)    
    if p:
        retval = float(p.string[p.start():p.end()])
    else:
        retval = 0.0
    if u:
        try:
            return retval * uuconv[u.string[u.start():u.end()]]
        except KeyError:
            pass
    return retval

def uutounit(val, unit):
    return val/uuconv[unit]

try:
    from lxml import etree
except:
    sys.exit(_('The fantastic lxml wrapper for libxml2 is required by inkex.py and therefore this extension. Please download and install the latest version from http://cheeseshop.python.org/pypi/lxml/, or install it through your package manager by a command like: sudo apt-get install python-lxml'))

def debug(what):
    sys.stderr.write(str(what) + "\n")
    return what

def errormsg(msg):
    """Intended for end-user-visible error messages.
    
       (Currently just writes to stderr with an appended newline, but could do
       something better in future: e.g. could add markup to distinguish error
       messages from status messages or debugging output.)
      
       Note that this should always be combined with translation:

         import gettext
         _ = gettext.gettext
         ...
         inkex.errormsg(_("This extension requires two selected paths."))
    """
    sys.stderr.write((str(msg) + "\n").encode("UTF-8"))

def check_inkbool(option, opt, value):
    if str(value).capitalize() == 'True':
        return True
    elif str(value).capitalize() == 'False':
        return False
    else:
        raise optparse.OptionValueError("option %s: invalid inkbool value: %s" % (opt, value))

def addNS(tag, ns=None):
    val = tag
    if ns!=None and len(ns)>0 and NSS.has_key(ns) and len(tag)>0 and tag[0]!='{':
        val = "{%s}%s" % (NSS[ns], tag)
    return val

class InkOption(optparse.Option):
    TYPES = optparse.Option.TYPES + ("inkbool",)
    TYPE_CHECKER = copy.copy(optparse.Option.TYPE_CHECKER)
    TYPE_CHECKER["inkbool"] = check_inkbool

class Effect:
    """A class for creating Inkscape SVG Effects"""

    def __init__(self, *args, **kwargs):
        self.document=None
        self.ctx=None
        self.selected={}
        self.doc_ids={}
        self.options=None
        self.args=None
        self.OptionParser = optparse.OptionParser(usage="usage: %prog [options] SVGfile",option_class=InkOption)
        self.OptionParser.add_option("--id",
                        action="append", type="string", dest="ids", default=[], 
                        help="id attribute of object to manipulate")

    def effect(self):
        pass

    def getoptions(self,args=sys.argv[1:]):
        """Collect command line arguments"""
        self.options, self.args = self.OptionParser.parse_args(args)

    def parse(self,file=None):
        """Parse document in specified file or on stdin"""
        try:
            try:
                stream = open(file,'r')
            except:
                stream = open(self.svg_file,'r')
        except:
            stream = sys.stdin
        self.document = etree.parse(stream)
        stream.close()

    def getposinlayer(self):
        #defaults
        self.current_layer = self.document.getroot()
        self.view_center = (0.0,0.0)

        layerattr = self.document.xpath('//sodipodi:namedview/@inkscape:current-layer', namespaces=NSS)
        if layerattr:
            layername = layerattr[0]
            layer = self.document.xpath('//svg:g[@id="%s"]' % layername, namespaces=NSS)
            if layer:
                self.current_layer = layer[0]

        xattr = self.document.xpath('//sodipodi:namedview/@inkscape:cx', namespaces=NSS)
        yattr = self.document.xpath('//sodipodi:namedview/@inkscape:cy', namespaces=NSS)
        doc_height = unittouu(self.document.getroot().get('height'))
        if xattr and yattr:
            x = xattr[0]
            y = yattr[0]
            if x and y:
                self.view_center = (float(x), doc_height - float(y)) # FIXME: y-coordinate flip, eliminate it when it's gone in Inkscape

    def getselected(self):
        """Collect selected nodes"""
        for i in self.options.ids:
            path = '//*[@id="%s"]' % i
            for node in self.document.xpath(path, namespaces=NSS):
                self.selected[i] = node

    def getElementById(self, id):
        path = '//*[@id="%s"]' % id
        el_list = self.document.xpath(path, namespaces=NSS)
        if el_list:
          return el_list[0]
        else:
          return None

    def getdocids(self):
        docIdNodes = self.document.xpath('//@id', namespaces=NSS)
        for m in docIdNodes:
            self.doc_ids[m] = 1

    def getNamedView(self):
        return self.document.xpath('//sodipodi:namedview', namespaces=NSS)[0]

    def createGuide(self, posX, posY, angle):
        atts = {
          'position': str(posX)+','+str(posY),
          'orientation': str(sin(radians(angle)))+','+str(-cos(radians(angle)))
          }
        guide = etree.SubElement(
                  self.getNamedView(),
                  addNS('guide','sodipodi'), atts )
        return guide

    def output(self):
        """Serialize document into XML on stdout"""
        self.document.write(sys.stdout)

    def affect(self, args=sys.argv[1:], output=True):
        """Affect an SVG document with a callback effect"""
        self.svg_file = args[-1]
        self.getoptions(args)
        self.parse()
        self.getposinlayer()
        self.getselected()
        self.getdocids()
        self.effect()
        if output: self.output()

    def uniqueId(self, old_id, make_new_id = True):
        new_id = old_id
        if make_new_id:
            while new_id in self.doc_ids:
                new_id += random.choice('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
            self.doc_ids[new_id] = 1
        return new_id

    def xpathSingle(self, path):
        try:
            retval = self.document.xpath(path, namespaces=NSS)[0]
        except:
            errormsg(_("No matching node for expression: %s") % path)
            retval = None
        return retval
            

# vim: expandtab shiftwidth=4 tabstop=8 softtabstop=4 encoding=utf-8 textwidth=99

########NEW FILE########
__FILENAME__ = simplepath
#!/usr/bin/env python
"""
simplepath.py
functions for digesting paths into a simple list structure

Copyright (C) 2005 Aaron Spike, aaron@ekips.org

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""
import re, math

def lexPath(d):
    """
    returns and iterator that breaks path data 
    identifies command and parameter tokens
    """
    offset = 0
    if not d:
        d = ""
    length = len(d)
    delim = re.compile(r'[ \t\r\n,]+')
    command = re.compile(r'[MLHVCSQTAZmlhvcsqtaz]')
    parameter = re.compile(r'(([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?)')
    while 1:
        m = delim.match(d, offset)
        if m:
            offset = m.end()
        if offset >= length:
            break
        m = command.match(d, offset)
        if m:
            yield [d[offset:m.end()], True]
            offset = m.end()
            continue
        m = parameter.match(d, offset)
        if m:
            yield [d[offset:m.end()], False]
            offset = m.end()
            continue
        #TODO: create new exception
        raise Exception, 'Invalid path data!'
'''
pathdefs = {commandfamily:
    [
    implicitnext,
    #params,
    [casts,cast,cast],
    [coord type,x,y,0]
    ]}
'''
pathdefs = {
    'M':['L', 2, [float, float], ['x','y']], 
    'L':['L', 2, [float, float], ['x','y']], 
    'H':['H', 1, [float], ['x']], 
    'V':['V', 1, [float], ['y']], 
    'C':['C', 6, [float, float, float, float, float, float], ['x','y','x','y','x','y']], 
    'S':['S', 4, [float, float, float, float], ['x','y','x','y']], 
    'Q':['Q', 4, [float, float, float, float], ['x','y','x','y']], 
    'T':['T', 2, [float, float], ['x','y']], 
    'A':['A', 7, [float, float, float, int, int, float, float], ['r','r','a',0,'s','x','y']], 
    'Z':['L', 0, [], []]
    }
def parsePath(d):
    """
    Parse SVG path and return an array of segments.
    Removes all shorthand notation.
    Converts coordinates to absolute.
    """
    retval = []
    lexer = lexPath(d)

    pen = (0.0,0.0)
    subPathStart = pen
    lastControl = pen
    lastCommand = ''
    
    while 1:
        try:
            token, isCommand = lexer.next()
        except StopIteration:
            break
        params = []
        needParam = True
        if isCommand:
            if not lastCommand and token.upper() != 'M':
                raise Exception, 'Invalid path, must begin with moveto.'    
            else:                
                command = token
        else:
            #command was omited
            #use last command's implicit next command
            needParam = False
            if lastCommand:
                if lastCommand.isupper():
                    command = pathdefs[lastCommand][0]
                else:
                    command = pathdefs[lastCommand.upper()][0].lower()
            else:
                raise Exception, 'Invalid path, no initial command.'    
        numParams = pathdefs[command.upper()][1]
        while numParams > 0:
            if needParam:
                try: 
                    token, isCommand = lexer.next()
                    if isCommand:
                        raise Exception, 'Invalid number of parameters'
                except StopIteration:
                    raise Exception, 'Unexpected end of path'
            cast = pathdefs[command.upper()][2][-numParams]
            param = cast(token)
            if command.islower():
                if pathdefs[command.upper()][3][-numParams]=='x':
                    param += pen[0]
                elif pathdefs[command.upper()][3][-numParams]=='y':
                    param += pen[1]
            params.append(param)
            needParam = True
            numParams -= 1
        #segment is now absolute so
        outputCommand = command.upper()
    
        #Flesh out shortcut notation    
        if outputCommand in ('H','V'):
            if outputCommand == 'H':
                params.append(pen[1])
            if outputCommand == 'V':
                params.insert(0,pen[0])
            outputCommand = 'L'
        if outputCommand in ('S','T'):
            params.insert(0,pen[1]+(pen[1]-lastControl[1]))
            params.insert(0,pen[0]+(pen[0]-lastControl[0]))
            if outputCommand == 'S':
                outputCommand = 'C'
            if outputCommand == 'T':
                outputCommand = 'Q'

        #current values become "last" values
        if outputCommand == 'M':
            subPathStart = tuple(params[0:2])
            pen = subPathStart
        if outputCommand == 'Z':
            pen = subPathStart
        else:
            pen = tuple(params[-2:])

        if outputCommand in ('Q','C'):
            lastControl = tuple(params[-4:-2])
        else:
            lastControl = pen
        lastCommand = command

        retval.append([outputCommand,params])
    return retval

def formatPath(a):
    """Format SVG path data from an array"""
    return "".join([cmd + " ".join([str(p) for p in params]) for cmd, params in a])

def translatePath(p, x, y):
    for cmd,params in p:
        defs = pathdefs[cmd]
        for i in range(defs[1]):
            if defs[3][i] == 'x':
                params[i] += x
            elif defs[3][i] == 'y':
                params[i] += y

def scalePath(p, x, y):
    for cmd,params in p:
        defs = pathdefs[cmd]
        for i in range(defs[1]):
            if defs[3][i] == 'x':
                params[i] *= x
            elif defs[3][i] == 'y':
                params[i] *= y
            elif defs[3][i] == 'r':         # radius parameter
                params[i] *= x
            elif defs[3][i] == 's':         # sweep-flag parameter
                if x*y < 0:
                    params[i] = 1 - params[i]
            elif defs[3][i] == 'a':         # x-axis-rotation angle
                if y < 0:
                    params[i] = - params[i]

def rotatePath(p, a, cx = 0, cy = 0):
    if a == 0:
        return p
    for cmd,params in p:
        defs = pathdefs[cmd]
        for i in range(defs[1]):
            if defs[3][i] == 'x':
                x = params[i] - cx
                y = params[i + 1] - cy
                r = math.sqrt((x**2) + (y**2))
                if r != 0:
                    theta = math.atan2(y, x) + a
                    params[i] = (r * math.cos(theta)) + cx
                    params[i + 1] = (r * math.sin(theta)) + cy


# vim: expandtab shiftwidth=4 tabstop=8 softtabstop=4 encoding=utf-8 textwidth=99

########NEW FILE########
__FILENAME__ = simplestyle
#!/usr/bin/env python
"""
simplestyle.py
Two simple functions for working with inline css
and some color handling on top.

Copyright (C) 2005 Aaron Spike, aaron@ekips.org

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

svgcolors={
    'aliceblue':'#f0f8ff',
    'antiquewhite':'#faebd7',
    'aqua':'#00ffff',
    'aquamarine':'#7fffd4',
    'azure':'#f0ffff',
    'beige':'#f5f5dc',
    'bisque':'#ffe4c4',
    'black':'#000000',
    'blanchedalmond':'#ffebcd',
    'blue':'#0000ff',
    'blueviolet':'#8a2be2',
    'brown':'#a52a2a',
    'burlywood':'#deb887',
    'cadetblue':'#5f9ea0',
    'chartreuse':'#7fff00',
    'chocolate':'#d2691e',
    'coral':'#ff7f50',
    'cornflowerblue':'#6495ed',
    'cornsilk':'#fff8dc',
    'crimson':'#dc143c',
    'cyan':'#00ffff',
    'darkblue':'#00008b',
    'darkcyan':'#008b8b',
    'darkgoldenrod':'#b8860b',
    'darkgray':'#a9a9a9',
    'darkgreen':'#006400',
    'darkgrey':'#a9a9a9',
    'darkkhaki':'#bdb76b',
    'darkmagenta':'#8b008b',
    'darkolivegreen':'#556b2f',
    'darkorange':'#ff8c00',
    'darkorchid':'#9932cc',
    'darkred':'#8b0000',
    'darksalmon':'#e9967a',
    'darkseagreen':'#8fbc8f',
    'darkslateblue':'#483d8b',
    'darkslategray':'#2f4f4f',
    'darkslategrey':'#2f4f4f',
    'darkturquoise':'#00ced1',
    'darkviolet':'#9400d3',
    'deeppink':'#ff1493',
    'deepskyblue':'#00bfff',
    'dimgray':'#696969',
    'dimgrey':'#696969',
    'dodgerblue':'#1e90ff',
    'firebrick':'#b22222',
    'floralwhite':'#fffaf0',
    'forestgreen':'#228b22',
    'fuchsia':'#ff00ff',
    'gainsboro':'#dcdcdc',
    'ghostwhite':'#f8f8ff',
    'gold':'#ffd700',
    'goldenrod':'#daa520',
    'gray':'#808080',
    'grey':'#808080',
    'green':'#008000',
    'greenyellow':'#adff2f',
    'honeydew':'#f0fff0',
    'hotpink':'#ff69b4',
    'indianred':'#cd5c5c',
    'indigo':'#4b0082',
    'ivory':'#fffff0',
    'khaki':'#f0e68c',
    'lavender':'#e6e6fa',
    'lavenderblush':'#fff0f5',
    'lawngreen':'#7cfc00',
    'lemonchiffon':'#fffacd',
    'lightblue':'#add8e6',
    'lightcoral':'#f08080',
    'lightcyan':'#e0ffff',
    'lightgoldenrodyellow':'#fafad2',
    'lightgray':'#d3d3d3',
    'lightgreen':'#90ee90',
    'lightgrey':'#d3d3d3',
    'lightpink':'#ffb6c1',
    'lightsalmon':'#ffa07a',
    'lightseagreen':'#20b2aa',
    'lightskyblue':'#87cefa',
    'lightslategray':'#778899',
    'lightslategrey':'#778899',
    'lightsteelblue':'#b0c4de',
    'lightyellow':'#ffffe0',
    'lime':'#00ff00',
    'limegreen':'#32cd32',
    'linen':'#faf0e6',
    'magenta':'#ff00ff',
    'maroon':'#800000',
    'mediumaquamarine':'#66cdaa',
    'mediumblue':'#0000cd',
    'mediumorchid':'#ba55d3',
    'mediumpurple':'#9370db',
    'mediumseagreen':'#3cb371',
    'mediumslateblue':'#7b68ee',
    'mediumspringgreen':'#00fa9a',
    'mediumturquoise':'#48d1cc',
    'mediumvioletred':'#c71585',
    'midnightblue':'#191970',
    'mintcream':'#f5fffa',
    'mistyrose':'#ffe4e1',
    'moccasin':'#ffe4b5',
    'navajowhite':'#ffdead',
    'navy':'#000080',
    'oldlace':'#fdf5e6',
    'olive':'#808000',
    'olivedrab':'#6b8e23',
    'orange':'#ffa500',
    'orangered':'#ff4500',
    'orchid':'#da70d6',
    'palegoldenrod':'#eee8aa',
    'palegreen':'#98fb98',
    'paleturquoise':'#afeeee',
    'palevioletred':'#db7093',
    'papayawhip':'#ffefd5',
    'peachpuff':'#ffdab9',
    'peru':'#cd853f',
    'pink':'#ffc0cb',
    'plum':'#dda0dd',
    'powderblue':'#b0e0e6',
    'purple':'#800080',
    'red':'#ff0000',
    'rosybrown':'#bc8f8f',
    'royalblue':'#4169e1',
    'saddlebrown':'#8b4513',
    'salmon':'#fa8072',
    'sandybrown':'#f4a460',
    'seagreen':'#2e8b57',
    'seashell':'#fff5ee',
    'sienna':'#a0522d',
    'silver':'#c0c0c0',
    'skyblue':'#87ceeb',
    'slateblue':'#6a5acd',
    'slategray':'#708090',
    'slategrey':'#708090',
    'snow':'#fffafa',
    'springgreen':'#00ff7f',
    'steelblue':'#4682b4',
    'tan':'#d2b48c',
    'teal':'#008080',
    'thistle':'#d8bfd8',
    'tomato':'#ff6347',
    'turquoise':'#40e0d0',
    'violet':'#ee82ee',
    'wheat':'#f5deb3',
    'white':'#ffffff',
    'whitesmoke':'#f5f5f5',
    'yellow':'#ffff00',
    'yellowgreen':'#9acd32'
}

def parseStyle(s):
    """Create a dictionary from the value of an inline style attribute"""
    if s is None:
      return {}
    else:
      return dict([i.split(":") for i in s.split(";") if len(i)])
def formatStyle(a):
    """Format an inline style attribute from a dictionary"""
    return ";".join([att+":"+str(val) for att,val in a.iteritems()])
def isColor(c):
    """Determine if its a color we can use. If not, leave it unchanged."""
    if c.startswith('#') and (len(c)==4 or len(c)==7):
        return True
    if c.lower() in svgcolors.keys():
        return True
    #might be "none" or some undefined color constant or rgb()
    #however, rgb() shouldnt occur at this point
    return False

def parseColor(c):
    """Creates a rgb int array"""
    tmp = svgcolors.get(c.lower())
    if tmp is not None:
        c = tmp
    elif c.startswith('#') and len(c)==4:
        c='#'+c[1:2]+c[1:2]+c[2:3]+c[2:3]+c[3:]+c[3:]
    elif c.startswith('rgb('):
        # remove the rgb(...) stuff
        tmp = c.strip()[4:-1]
        numbers = [number.strip() for number in tmp.split(',')]
        converted_numbers = []
        if len(numbers) == 3:
            for num in numbers:
                if num.endswith(r'%'):
                    converted_numbers.append( int(int(num[0:-1])*255/100))
                else:
                    converted_numbers.append(int(num))
            return tuple(converted_numbers)
        else:    
            return (0,0,0)
        
    r=int(c[1:3],16)
    g=int(c[3:5],16)
    b=int(c[5:],16)
    return (r,g,b)

def formatColoria(a):
    """int array to #rrggbb"""
    return '#%02x%02x%02x' % (a[0],a[1],a[2])
def formatColorfa(a):
    """float array to #rrggbb"""
    return '#%02x%02x%02x' % (int(round(a[0]*255)),int(round(a[1]*255)),int(round(a[2]*255)))
def formatColor3i(r,g,b):
    """3 ints to #rrggbb"""
    return '#%02x%02x%02x' % (r,g,b)
def formatColor3f(r,g,b):
    """3 floats to #rrggbb"""
    return '#%02x%02x%02x' % (int(round(r*255)),int(round(g*255)),int(round(b*255)))


# vim: expandtab shiftwidth=4 tabstop=8 softtabstop=4 encoding=utf-8 textwidth=99

########NEW FILE########
__FILENAME__ = simpletransform
#!/usr/bin/env python
'''
Copyright (C) 2006 Jean-Francois Barraud, barraud@math.univ-lille1.fr

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
barraud@math.univ-lille1.fr

This code defines several functions to make handling of transform
attribute easier.
'''
import inkex, cubicsuperpath, bezmisc, simplestyle
import copy, math, re

def parseTransform(transf,mat=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]):
    if transf=="" or transf==None:
        return(mat)
    stransf = transf.strip()
    result=re.match("(translate|scale|rotate|skewX|skewY|matrix)\s*\(([^)]*)\)\s*,?",stransf)
#-- translate --
    if result.group(1)=="translate":
        args=result.group(2).replace(',',' ').split()
        dx=float(args[0])
        if len(args)==1:
            dy=0.0
        else:
            dy=float(args[1])
        matrix=[[1,0,dx],[0,1,dy]]
#-- scale --
    if result.group(1)=="scale":
        args=result.group(2).replace(',',' ').split()
        sx=float(args[0])
        if len(args)==1:
            sy=sx
        else:
            sy=float(args[1])
        matrix=[[sx,0,0],[0,sy,0]]
#-- rotate --
    if result.group(1)=="rotate":
        args=result.group(2).replace(',',' ').split()
        a=float(args[0])*math.pi/180
        if len(args)==1:
            cx,cy=(0.0,0.0)
        else:
            cx,cy=map(float,args[1:])
        matrix=[[math.cos(a),-math.sin(a),cx],[math.sin(a),math.cos(a),cy]]
        matrix=composeTransform(matrix,[[1,0,-cx],[0,1,-cy]])
#-- skewX --
    if result.group(1)=="skewX":
        a=float(result.group(2))*math.pi/180
        matrix=[[1,math.tan(a),0],[0,1,0]]
#-- skewY --
    if result.group(1)=="skewY":
        a=float(result.group(2))*math.pi/180
        matrix=[[1,0,0],[math.tan(a),1,0]]
#-- matrix --
    if result.group(1)=="matrix":
        a11,a21,a12,a22,v1,v2=result.group(2).replace(',',' ').split()
        matrix=[[float(a11),float(a12),float(v1)], [float(a21),float(a22),float(v2)]]

    matrix=composeTransform(mat,matrix)
    if result.end() < len(stransf):
        return(parseTransform(stransf[result.end():], matrix))
    else:
        return matrix

def formatTransform(mat):
    return ("matrix(%f,%f,%f,%f,%f,%f)" % (mat[0][0], mat[1][0], mat[0][1], mat[1][1], mat[0][2], mat[1][2]))

def composeTransform(M1,M2):
    a11 = M1[0][0]*M2[0][0] + M1[0][1]*M2[1][0]
    a12 = M1[0][0]*M2[0][1] + M1[0][1]*M2[1][1]
    a21 = M1[1][0]*M2[0][0] + M1[1][1]*M2[1][0]
    a22 = M1[1][0]*M2[0][1] + M1[1][1]*M2[1][1]

    v1 = M1[0][0]*M2[0][2] + M1[0][1]*M2[1][2] + M1[0][2]
    v2 = M1[1][0]*M2[0][2] + M1[1][1]*M2[1][2] + M1[1][2]
    return [[a11,a12,v1],[a21,a22,v2]]

def applyTransformToNode(mat,node):
    m=parseTransform(node.get("transform"))
    newtransf=formatTransform(composeTransform(mat,m))
    node.set("transform", newtransf)

def applyTransformToPoint(mat,pt):
    x = mat[0][0]*pt[0] + mat[0][1]*pt[1] + mat[0][2]
    y = mat[1][0]*pt[0] + mat[1][1]*pt[1] + mat[1][2]
    pt[0]=x
    pt[1]=y

def applyTransformToPath(mat,path):
    for comp in path:
        for ctl in comp:
            for pt in ctl:
                applyTransformToPoint(mat,pt)

def fuseTransform(node):
    if node.get('d')==None:
        #FIXME: how do you raise errors?
        raise AssertionError, 'can not fuse "transform" of elements that have no "d" attribute'
    t = node.get("transform")
    if t == None:
        return
    m = parseTransform(t)
    d = node.get('d')
    p = cubicsuperpath.parsePath(d)
    applyTransformToPath(m,p)
    node.set('d', cubicsuperpath.formatPath(p))
    del node.attrib["transform"]

####################################################################
##-- Some functions to compute a rough bbox of a given list of objects.
##-- this should be shipped out in an separate file...

def boxunion(b1,b2):
    if b1 is None:
        return b2
    elif b2 is None:
        return b1    
    else:
        return((min(b1[0],b2[0]), max(b1[1],b2[1]), min(b1[2],b2[2]), max(b1[3],b2[3])))

def roughBBox(path):
    xmin,xMax,ymin,yMax = path[0][0][0][0],path[0][0][0][0],path[0][0][0][1],path[0][0][0][1]
    for pathcomp in path:
        for ctl in pathcomp:
            for pt in ctl:
                xmin = min(xmin,pt[0])
                xMax = max(xMax,pt[0])
                ymin = min(ymin,pt[1])
                yMax = max(yMax,pt[1])
    return xmin,xMax,ymin,yMax

def computeBBox(aList,mat=[[1,0,0],[0,1,0]]):
    bbox=None
    for node in aList:
        m = parseTransform(node.get('transform'))
        m = composeTransform(mat,m)
        #TODO: text not supported!
        d = None
        if node.get("d"):
            d = node.get('d')
        elif node.get('points'):
            d = 'M' + node.get('points')
        elif node.tag in [ inkex.addNS('rect','svg'), 'rect' ]:
            d = 'M' + node.get('x', '0') + ',' + node.get('y', '0') + \
                'h' + node.get('width') + 'v' + node.get('height') + \
                'h-' + node.get('width')
        elif node.tag in [ inkex.addNS('line','svg'), 'line' ]:
            d = 'M' + node.get('x1') + ',' + node.get('y1') + \
                ' ' + node.get('x2') + ',' + node.get('y2')
        elif node.tag in [ inkex.addNS('circle','svg'), 'circle', \
                            inkex.addNS('ellipse','svg'), 'ellipse' ]:
            rx = node.get('r')
            if rx is not None:
                ry = rx
            else:
                rx = node.get('rx')
                ry = node.get('ry')
            cx = float(node.get('cx', '0'))
            cy = float(node.get('cy', '0'))
            x1 = cx - float(rx)
            x2 = cx + float(rx)
            d = 'M %f %f ' % (x1, cy) + \
                'A' + rx + ',' + ry + ' 0 1 0 %f,%f' % (x2, cy) + \
                'A' + rx + ',' + ry + ' 0 1 0 %f,%f' % (x1, cy)
 
        if d is not None:
            p = cubicsuperpath.parsePath(d)
            applyTransformToPath(m,p)
            bbox=boxunion(roughBBox(p),bbox)

        elif node.tag == inkex.addNS('use','svg') or node.tag=='use':
            refid=node.get(inkex.addNS('href','xlink'))
            path = '//*[@id="%s"]' % refid[1:]
            refnode = node.xpath(path)
            bbox=boxunion(computeBBox(refnode,m),bbox)
            
        bbox=boxunion(computeBBox(node,m),bbox)
    return bbox


# vim: expandtab shiftwidth=4 tabstop=8 softtabstop=4 encoding=utf-8 textwidth=99

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
Copyright (C) 2012 Karlisson Bezerra, contact@hacktoon.com

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
'''

import sys
import inkex
from canvas import Canvas
from Ink2CanvasCore import Ink2CanvasCore
 
class Ink2Canvas(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        self.core = Ink2CanvasCore(inkex, self)


    def effect(self):
        svgRoot = self.document.getroot()
        
        tmpWidth = svgRoot.get("width")
        if tmpWidth == None:        
            width = inkex.unittouu("800")
        else:
            width = inkex.unittouu(tmpWidth)
            
        tmpHeight = svgRoot.get("height")
        if tmpHeight == None:
            height = inkex.unittouu("600")
        else:
            height = inkex.unittouu(tmpHeight)
            
        self.core.canvas = Canvas(width, height)
        self.core.createTree(svgRoot)
        for drawable in self.core.root.getDrawable():
            drawable.runDraw()

    def output(self):
        content = self.core.canvas.output()
        sys.stdout.write(content.encode("utf-8"))

    
if __name__ == "__main__":
    i2c = Ink2Canvas()
    i2c.affect()


########NEW FILE########
__FILENAME__ = AbstractShape
from ink2canvas.svg.Element import Element
from ink2canvas.lib import simplestyle
from ink2canvas.lib.simpletransform import parseTransform
from ink2canvas.GradientHelper import GradientHelper

class AbstractShape(Element):
    def __init__(self, command, node, canvasContext, rootTree):
        Element.__init__(self)
        self.node = node
        self.command = command
        self.canvasContext = canvasContext
        self.rootTree = rootTree
        self.gradientHelper = GradientHelper(self)

    def getId(self):
        return self.attr("id")    
    
    def getData(self):
        return

    def getStyle(self):
        style = simplestyle.parseStyle(self.attr("style"))
        if style == {}:
            parent = self.getParent()
            while (parent != None and style == {}):
                style = simplestyle.parseStyle(parent.attr("style"))
                parent = parent.getParent()        
        
        #remove any trailing space in dict keys/values
        style = dict([(str.strip(k), str.strip(v)) for k,v in style.items()])
        return style

    def setStyle(self, style):
        """Translates style properties names into method calls"""
        self.canvasContext.style = style
        for key in style:
            tmp_list = map(str.capitalize, key.split("-"))
            method = "set" + "".join(tmp_list)
            if hasattr(self.canvasContext, method) and style[key] != "none":
                getattr(self.canvasContext, method)(style[key])
        #saves style to compare in next iteration
        self.canvasContext.style_cache = style

    def hasTransform(self):
        return bool(self.attr("transform"))

    def getTransform(self):
        data = self.node.get("transform")
        if not data:
            return
        matrix = parseTransform(data)
        m11, m21, dx = matrix[0]
        m12, m22, dy = matrix[1]
        return m11, m12, m21, m22, dx, dy   

    def getClipId(self):
        return self.attr("clip-path")[5:-1]

    def initDraw(self):
        self.canvasContext.write("\n// #%s" % self.attr("id"))
        if self.hasTransform() or self.hasClip():
            self.canvasContext.save()
        
    def draw(self, isClip=False):
        data = self.getData()
        if self.hasTransform():
            transMatrix = self.getTransform()
            self.canvasContext.transform(*transMatrix)
            
        if not isClip:
            style = self.getStyle()
            self.setStyle(style)
            self.canvasContext.beginPath()       
                
        getattr(self.canvasContext, self.command)(*data)

        gradientFill = self.gradientHelper.setGradientFill()
        gradientStroke = self.gradientHelper.setGradientStroke()
        
        if not isClip: 
            self.canvasContext.closePath()
            if(not gradientFill):        
                self.canvasContext.fill()
            if(not gradientStroke):
                self.canvasContext.stroke()

    def drawClip(self):
        clipId = self.getClipId()
        elementClip = self.rootTree.getClipPath(clipId)
        self.canvasContext.beginPath()
        if (self.hasTransform()):
            self.canvasContext.save()
            transMatrix = self.getTransform()
            self.canvasContext.transform(*transMatrix)
        #DRAW
        elementClip.runDraw(True)
        if (self.hasTransform()):
            self.canvasContext.restore()
        self.canvasContext.clip()   

    def endDraw(self):
        if self.hasTransform() or self.hasClip():
            self.canvasContext.restore()
########NEW FILE########
__FILENAME__ = Circle
from ink2canvas.svg.AbstractShape import AbstractShape

class Circle(AbstractShape):
    def __init__(self, command, node, canvasContext, rootTree):
        AbstractShape.__init__(self, command, node, canvasContext, rootTree)
        self.command = "arc"

    def getData(self):
        import math
        cx = self.attr("cx")
        cy = self.attr("cy")
        r = self.attr("r")
        return cx, cy, r, 0, math.pi * 2, True
########NEW FILE########
__FILENAME__ = ClipPath
from ink2canvas.svg import Element

class Clippath(Element):

    def __init__(self, command, node, canvasContext, root):
        Element.__init__(self)
        self.node = node
########NEW FILE########
__FILENAME__ = Defs
from ink2canvas.svg.Element import Element

class Defs(Element):
    def __init__(self, command, node, canvasContext, root):
        Element.__init__(self)
        self.command = command
        self.node = node
        self.canvasContext = canvasContext
        self.root = root
########NEW FILE########
__FILENAME__ = Element
from ink2canvas.lib import inkex

class Element:
    def __init__(self):
        self.children = []
        self.parent = None
        
    def setParent(self, parent):
        self.parent = parent
    
    def getParent(self):
        return self.parent
    
    def getChildren(self):
        return self.children
    
    def addChild(self, child):
        self.children.append(child)
        
    def initDraw(self):
        pass
    
    def draw(self):
        pass
    
    def endDraw(self):
        pass
    
    def drawClip(self):
        pass
    
    def runDraw(self, isClip = False):
        self.initDraw()
        if self.hasClip():
            self.drawClip()        
        self.draw(isClip)
        for child in self.children:
            child.runDraw()
        self.endDraw()
    
    def hasClip(self):
        return bool(self.attr("clip-path"))
    
    def attr(self, val, ns=""):
        if ns:
            val = inkex.addNS(val, ns)
        try:
            attr = float(self.node.get(val))
        except:
            attr = self.node.get(val)
        return attr
########NEW FILE########
__FILENAME__ = Ellipse
from ink2canvas.svg.AbstractShape import AbstractShape

class Ellipse(AbstractShape):
    def getData(self):
        cx = self.attr("cx")
        cy = self.attr("cy")
        rx = self.attr("rx")
        ry = self.attr("ry")
        return cx, cy, rx, ry

    def draw(self, isClip=False):
        import math
        cx, cy, rx, ry = self.getData()
        if not isClip:
            style = self.getStyle()
            self.setStyle(style)
            self.canvasContext.beginPath()
        if self.hasTransform():
            trans_matrix = self.getTransform()
            self.canvasContext.transform(*trans_matrix) # unpacks argument list

        auxiliarNumber = 4 * ((math.sqrt(2) - 1) / 3)
        self.canvasContext.moveTo(cx, cy - ry)
        self.canvasContext.bezierCurveTo(cx + (auxiliarNumber * rx), cy - ry,  cx + rx, cy - (auxiliarNumber * ry), cx + rx, cy)
        self.canvasContext.bezierCurveTo(cx + rx, cy + (auxiliarNumber * ry), cx + (auxiliarNumber * rx), cy + ry, cx, cy + ry)
        self.canvasContext.bezierCurveTo(cx - (auxiliarNumber * rx), cy + ry, cx - rx, cy + (auxiliarNumber * ry), cx - rx, cy)
        self.canvasContext.bezierCurveTo(cx - rx, cy - (auxiliarNumber * ry), cx - (auxiliarNumber * rx), cy - ry, cx, cy - ry)

        gradientFill = self.gradientHelper.setGradientFill()
        gradientStroke = self.gradientHelper.setGradientStroke()
        
        if not isClip: 
            self.canvasContext.closePath()
            if(not gradientFill):        
                self.canvasContext.fill()
            if(not gradientStroke):
                self.canvasContext.stroke()
            
########NEW FILE########
__FILENAME__ = G
from ink2canvas.svg.AbstractShape import AbstractShape

class G(AbstractShape):       
        
    def draw(self, isClip=False):
        #get layer label, if exists
        gtype = self.attr("groupmode", "inkscape") or "group"
        if self.hasTransform():
            transMatrix = self.getTransform()
            self.canvasContext.transform(*transMatrix)
########NEW FILE########
__FILENAME__ = Image
from ink2canvas.svg.AbstractShape import AbstractShape

class Image(AbstractShape):

    def get_data(self):
        x = self.attr("x")
        y = self.attr("y")
        width = self.attr("width")
        height = self.attr("height")
        href = self.attr("href","xlink")
        return x, y, width, height, href
    
    def draw(self, isClip=False):
        if self.has_transform():
            trans_matrix = self.get_transform()
            self.ctx.transform(*trans_matrix) # unpacks argument list
        if not isClip:
            style = self.get_style()
            self.set_style(style)
            self.ctx.beginPath()

        x, y, width, height, href = self.get_data()
        
        self.ctx.write("\n\tvar image = new Image();")
        self.ctx.write("\n\timage.src = '" + href +"';")
        self.ctx.write("\n\tctx.drawImage(image, %f,%f,%f,%f);" %(x,y,width, height))
        
        if not isClip: 
            self.ctx.closePath()
        
        



########NEW FILE########
__FILENAME__ = Line
from ink2canvas.svg.Path import Path

class Line(Path):
    def getData(self):
        x1 = self.attr("x1")
        y1 = self.attr("y1")
        x2 = self.attr("x2")
        y2 = self.attr("y2")
        return (("M", (x1, y1)), ("L", (x2, y2)))
########NEW FILE########
__FILENAME__ = LinearGradient
from ink2canvas.svg.Defs import Defs

class Lineargradient(Defs):
    def __init__(self, command, node, canvasContext, root):
        Defs.__init__(self, command, node, canvasContext, root)
        self.colorStops = {}
        self.link = None
        self.x1 = 0
        self.y1 = 0
        self.x2 = 0
        self.y2 = 0
        
    def setColorStops(self, colorStops):
        self.colorStops = colorStops
    
    def getData(self):
        x1 = self.attr("x1")
        y1 = self.attr("y1")
        x2 = self.attr("x2")
        y2 = self.attr("y2")
        return (x1, y1, x2, y2)
########NEW FILE########
__FILENAME__ = Path
from ink2canvas.svg.AbstractShape import AbstractShape
from ink2canvas.lib.simplepath import parsePath

class Path(AbstractShape):
    def getData(self):
        #path data is already converted to float
        return parsePath(self.attr("d"))

    def pathMoveTo(self, data):
        self.canvasContext.moveTo(data[0], data[1])
        self.currentPosition = data[0], data[1]

    def pathLineTo(self, data):
        self.canvasContext.lineTo(data[0], data[1])
        self.currentPosition = data[0], data[1]

    def pathCurveTo(self, data):
        x1, y1, x2, y2 = data[0], data[1], data[2], data[3]
        x, y = data[4], data[5]
        self.canvasContext.bezierCurveTo(x1, y1, x2, y2, x, y)
        self.currentPosition = x, y

    def pathArcTo(self, data):
        #http://www.w3.org/TR/SVG11/implnote.html#ArcImplementationNotes
        # code adapted from http://code.google.com/p/canvg/
        import math
        x1 = self.currentPosition[0]
        y1 = self.currentPosition[1]
        x2 = data[5]
        y2 = data[6]
        rx = data[0]
        ry = data[1]
        angle = data[2] * (math.pi / 180.0)
        arcFlag = data[3]
        sweepFlag = data[4]

        if x1 == x2 and y1 == y2:
            return

        #compute (x1', y1')
        _x1 = math.cos(angle) * (x1 - x2) / 2.0 + math.sin(angle) * (y1 - y2) / 2.0
        _y1 = -math.sin(angle) * (x1 - x2) / 2.0 + math.cos(angle) * (y1 - y2) / 2.0

        #adjust radii
        l = _x1**2 / rx**2 + _y1**2 / ry**2
        if l > 1:
            rx *= math.sqrt(l)
            ry *= math.sqrt(l)

        #compute (cx', cy')
        numr = (rx**2 * ry**2) - (rx**2 * _y1**2) - (ry**2 * _x1**2)
        demr = (rx**2 * _y1**2) + (ry**2 * _x1**2)
        sig = -1 if arcFlag == sweepFlag else 1
        sig = sig * math.sqrt(numr / demr)
        if math.isnan(sig): sig = 0;
        _cx = sig * rx * _y1 / ry
        _cy = sig * -ry * _x1 / rx

        #compute (cx, cy) from (cx', cy')
        cx = (x1 + x2) / 2.0 + math.cos(angle) * _cx - math.sin(angle) * _cy
        cy = (y1 + y2) / 2.0 + math.sin(angle) * _cx + math.cos(angle) * _cy

        #compute startAngle & endAngle
        #vector magnitude
        m = lambda v: math.sqrt(v[0]**2 + v[1]**2)
        #ratio between two vectors
        r = lambda u, v: (u[0] * v[0] + u[1] * v[1]) / (m(u) * m(v))
        #angle between two vectors
        a = lambda u, v: (-1 if u[0]*v[1] < u[1]*v[0] else 1) * math.acos(r(u,v))
        #initial angle
        a1 = a([1,0], [(_x1 - _cx) / rx, (_y1 - _cy)/ry])
        #angle delta
        u = [(_x1 - _cx) / rx, (_y1 - _cy) / ry]
        v = [(-_x1 - _cx) / rx, (-_y1 - _cy) / ry]
        ad = a(u, v)
        if r(u,v) <= -1: ad = math.pi
        if r(u,v) >= 1: ad = 0

        if sweepFlag == 0 and ad > 0: ad = ad - 2 * math.pi;
        if sweepFlag == 1 and ad < 0: ad = ad + 2 * math.pi;

        r = rx if rx > ry else ry
        sx = 1 if rx > ry else rx / ry
        sy = ry / rx if rx > ry else 1

        self.canvasContext.translate(cx, cy)
        self.canvasContext.rotate(angle)
        self.canvasContext.scale(sx, sy)
        self.canvasContext.arc(0, 0, r, a1, a1 + ad, 1 - sweepFlag)
        self.canvasContext.scale(1/sx, 1/sy)
        self.canvasContext.rotate(-angle)
        self.canvasContext.translate(-cx, -cy)
        self.currentPosition = x2, y2

    def draw(self, isClip=False):
        path = self.getData()
        if not isClip:
            style = self.getStyle()
            self.setStyle(style)
            self.canvasContext.beginPath()
        if self.hasTransform():
            transMatrix = self.getTransform()
            self.canvasContext.transform(*transMatrix) # unpacks argument list

        #Draws path commands
        pathCommand = {"M": self.pathMoveTo,
                       "L": self.pathLineTo,
                       "C": self.pathCurveTo,
                       "A": self.pathArcTo}
        for pt in path:
            comm, data = pt
            if comm in pathCommand:
                pathCommand[comm](data)

        gradientFill = self.gradientHelper.setGradientFill()
        gradientStroke = self.gradientHelper.setGradientStroke()
        
        if not isClip: 
            self.canvasContext.closePath(comm == "Z")
            if(not gradientFill):        
                self.canvasContext.fill()
            if(not gradientStroke):
                self.canvasContext.stroke()
########NEW FILE########
__FILENAME__ = Polygon
from ink2canvas.svg.Path import Path

class Polygon(Path):
    def getData(self):
        points = self.attr("points").strip().split(" ")
        points = map(lambda x: x.split(","), points)
        comm = []
        for pt in points:           # creating path command similar
            pt = map(float, pt)
            comm.append(["L", pt])
        comm[0][0] = "M"            # first command must be a 'M' => moveTo
        return comm
########NEW FILE########
__FILENAME__ = Polyline
from ink2canvas.svg.Polygon import Polygon

class Polyline(Polygon):
    pass
########NEW FILE########
__FILENAME__ = RadialGradient
from ink2canvas.svg.Defs import Defs

class Radialgradient(Defs):
    def __init__(self, command, node, canvasContext, root):
        Defs.__init__(self, command, node, canvasContext, root)
        self.colorStops = []
        self.cx= 0
        self.cy= 0
        self.fx= 0
        self.fy= 0
        self.r = 0
    
    def setColorStops(self, colorStops):
        self.colorStops = colorStops
    
    def getData(self):
        cx = self.attr("cx")
        cy = self.attr("cy")
        fx = self.attr("fx")    
        fy = self.attr("fy")
        r = self.attr("r")
        return (cx, cy, fx, fy, r)

    def draw(self):
        pass
########NEW FILE########
__FILENAME__ = Rect
from ink2canvas.svg.AbstractShape import AbstractShape

class Rect(AbstractShape):
    def getData(self):
        x = self.attr("x")
        y = self.attr("y")
        w = self.attr("width")
        h = self.attr("height")
        rx = self.attr("rx") or 0
        ry = self.attr("ry") or 0
        return x, y, w, h, rx, ry
########NEW FILE########
__FILENAME__ = Root
'''
Created on 16/05/2012

@author: tasso
'''

from ink2canvas.svg.G import G

class Root(object):

    def __init__(self):
        self.drawable = []
        self.clipPath = {}
        self.linearGradient = {}
        self.radialGradient = {}

    def searchElementById(self,idQueTenhoQueAchar,nosQueDevemSerDesenhados):
        retorno = None
        for noEmQuestao in nosQueDevemSerDesenhados:
            if(noEmQuestao.getId() == idQueTenhoQueAchar):
                return noEmQuestao
            if(isinstance(noEmQuestao, G)):
                retorno = self.searchElementById(idQueTenhoQueAchar, noEmQuestao.children)
                if(retorno!=None):
                    break
        return retorno

    def addChildDrawable(self, child):
        self.drawable.append(child)

    def addChildClipPath(self, key, value):
        self.clipPath[key] = value;

    def addChildLinearGradient(self, key, value):
        self.linearGradient[key] = value;

    def addChildRadialGradient(self, key, value):
        self.radialGradient[key] = value;
    
    def getDrawable(self):
        return self.drawable

    def getClipPath(self, key):
        return self.clipPath[key]

    def getLinearGradient(self, key):
        return self.linearGradient[key]

    def getRadialGradient(self, key):
        return self.radialGradient[key]





########NEW FILE########
__FILENAME__ = Text
from ink2canvas.svg.AbstractShape import AbstractShape

class Text(AbstractShape):
    def textHelper(self, tspan):
        val = ""
        if tspan.text:
            val += tspan.text
        for ts in tspan:
            val += self.textHelper(ts)
        if tspan.tail:
            val += tspan.tail
        return val

    def setTextStyle(self, style):
        keys = ("font-style", "font-weight", "font-size", "font-family")
        text = []
        for key in keys:
            if key in style:
                text.append(style[key])
        self.canvasContext.setFont(" ".join(text))

    def getData(self):
        x = self.attr("x")
        y = self.attr("y")
        return x, y

    def draw(self, isClip=False):
        x, y = self.getData()
        style = self.getStyle()
        if self.hasTransform():
            transMatrix = self.getTransform()
            self.canvasContext.transform(*transMatrix) # unpacks argument list
        self.setStyle(style)
        self.setTextStyle(style)

        for tspan in self.node:
            text = self.textHelper(tspan)
            _x = float(tspan.get("x"))
            _y = float(tspan.get("y"))
            self.canvasContext.fillText(text, _x, _y)
        
        self.gradientHelper.setGradientFill()
        self.gradientHelper.setGradientStroke()

########NEW FILE########
__FILENAME__ = Use
from ink2canvas.svg.AbstractShape import AbstractShape

class Use(AbstractShape):
    
    def drawClone(self):
        drawables = self.rootTree.getDrawable()
        OriginName = self.getCloneId()
        OriginObject = self.rootTree.searchElementById(OriginName,drawables)
        OriginObject.runDraw()
      
    def draw(self, isClip=False):
        if self.hasTransform():
            transMatrix = self.getTransform()
            self.canvasContext.transform(*transMatrix)
        self.drawClone()
        
    def getCloneId(self):
        return self.attr("href","xlink")[1:]
########NEW FILE########
__FILENAME__ = standalone
# -*- encoding: utf-8 -#-

"""
This script runs Ink2Canvas without needing to open Inkscape
"""

from ink2canvas.main import Ink2Canvas
import sys

i2c = Ink2Canvas()

#catch first argument
try:
    svg_input = sys.argv[1]
except IndexError:
    print "Provide a SVG file to be parsed.\n"
    print "Usage: python standalone.py INPUT [OUTPUT]"
    sys.exit()

#catch optional second argument for output file
try:
    html_output = sys.argv[2]
except IndexError:
    html_output = "%s.html" % svg_input.replace(".svg", "")

#creates a svg element tree
i2c.parse(svg_input)

#applies the extension effect
i2c.effect()

output_file = open(html_output, "w")
#get the html code
content = i2c.core.canvas.output()
output_file.write(content.encode("utf-8"))
output_file.close()

########NEW FILE########
__FILENAME__ = unit_test_canvas
import sys
import unittest

sys.path.append('..')
from ink2canvas.canvas import Canvas


class TestCanvas(unittest.TestCase):
    def setUp(self):
        self.canvas = Canvas(100.0, 200.0)
        self.canvasWithContext = Canvas(100.0, 200.0, "foo")
        self.canvas.code = []
        self.string_rgb = "FFBBAA"
        self.rgb = [251, 186, 10]
        
    def testBeginPathIfWritesRight(self):
        self.canvas.beginPath()
        self.assertEqual(self.canvas.code, ["\tctx.beginPath();\n"])
        
        
    def testBeginPathIfWritesRightWithNewCtx(self):
        self.canvasWithContext.beginPath()
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.beginPath();\n"])
        
    def testPutStyleinCacheFirstElement(self):
        self.canvas.putStyleInCache({'foo': "bar"}) 
        self.assertEqual(self.canvas.styleCache, {'foo': "bar"})

    def testPutStyleInCacheAddSecondElement(self):
        self.canvas.putStyleInCache({'foo': "bar"}) 
        self.canvas.putStyleInCache({'fooo': "baar"}) 
        self.assertEqual(self.canvas.styleCache, {'fooo': "baar", 'foo':"bar"})
        
    def testPutStyleInCacheChangingValue(self):
        self.canvas.putStyleInCache({'foo': "bar"}) 
        self.canvas.putStyleInCache({'foo': "baar"}) 
        self.assertEqual(self.canvas.styleCache, {'foo': "baar"})
        
    def testPutStyleInCacheWithNULLValue(self):
        self.canvas.putStyleInCache({'foo': "bar"})
        self.canvas.putStyleInCache({'foo':""}) 
        self.assertEqual(self.canvas.styleCache, {'foo': "bar"})

    def testGetColorWithALowerThenOne(self): 
        retorno = self.canvas.getColor(self.string_rgb, 0)
        self.assertEqual(retorno, "'rgba(%d, %d, %d, %.1f)'" % (251, 186, 10, 0))
                  
    def testGetColorWithAHigherThenOne(self):
        retorno = self.canvas.getColor(self.string_rgb, 2)
        self.assertEqual(retorno, "'rgb(%d, %d, %d)'" % (251, 186, 10))
        
    def testGetColorWithAEqualToOne(self):
        retorno = self.canvas.getColor(self.string_rgb, 1)
        self.assertEqual(retorno, "'rgb(%d, %d, %d)'" % (251, 186, 10))
        
    def testBezierCurveTo(self):
        self.canvas.bezierCurveTo(4, 6, 2.3, -4, 1, 2)
        self.assertEqual(self.canvas.code, ["\tctx.bezierCurveTo(%f, %f, %f, %f, %f, %f);\n" % (4, 6, 2.3, -4, 1, 2)])
        
    def testBezierCurveToWithNewCtx(self):
        self.canvasWithContext.bezierCurveTo(4, 6, 2, 4, 1, 2)
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.bezierCurveTo(%f, %f, %f, %f, %f, %f);\n" % (4, 6, 2, 4, 1, 2)])
        
    def testRectWithRXAndRY(self):
        self.canvas.rect(4, 6, 2, 4, 1, 2)
        self.assertEqual(self.canvas.code, ['\tctx.moveTo(4.000000, 8.000000);\n', '\tctx.lineTo(4.000000, 8.000000);\n', '\tctx.quadraticCurveTo(4.000000, 10.000000, 5.000000, 10.000000);\n', '\tctx.lineTo(5.000000, 10.000000);\n', '\tctx.quadraticCurveTo(6.000000, 10.000000, 6.000000, 8.000000);\n', '\tctx.lineTo(6.000000, 8.000000);\n', '\tctx.quadraticCurveTo(6.000000, 6.000000, 5.000000, 6.000000);\n', '\tctx.lineTo(5.000000, 6.000000);\n', '\tctx.quadraticCurveTo(4.000000, 6.000000, 4.000000, 8.000000);\n'])
        
    def testRectWithRXAndRYCtx(self):
        self.canvasWithContext.rect(4, 6, 2, 4, 1, 2)
        self.assertEqual(self.canvasWithContext.code, ['\tfoo.moveTo(4.000000, 8.000000);\n', '\tfoo.lineTo(4.000000, 8.000000);\n', '\tfoo.quadraticCurveTo(4.000000, 10.000000, 5.000000, 10.000000);\n', '\tfoo.lineTo(5.000000, 10.000000);\n', '\tfoo.quadraticCurveTo(6.000000, 10.000000, 6.000000, 8.000000);\n', '\tfoo.lineTo(6.000000, 8.000000);\n', '\tfoo.quadraticCurveTo(6.000000, 6.000000, 5.000000, 6.000000);\n', '\tfoo.lineTo(5.000000, 6.000000);\n', '\tfoo.quadraticCurveTo(4.000000, 6.000000, 4.000000, 8.000000);\n'])
    
    def testRectWithoutRXAndRY(self):
        self.canvas.rect(4, 6, 2, 4)
        self.assertEqual(self.canvas.code, ["\tctx.rect(%f, %f, %f, %f);\n" % (4, 6, 2, 4)])
        
    def testRectWithoutRXAndRYCtx(self):
        self.canvasWithContext.rect(4, 6, 2, 4)
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.rect(%f, %f, %f, %f);\n" % (4, 6, 2, 4)])
                
    def testRectWithRX(self):
        self.canvas.rect(4, 6, 2, 4, 1)
        self.assertEqual(self.canvas.code, ['\tctx.moveTo(4.000000, 6.000000);\n', '\tctx.lineTo(4.000000, 10.000000);\n', '\tctx.quadraticCurveTo(4.000000, 10.000000, 5.000000, 10.000000);\n', '\tctx.lineTo(5.000000, 10.000000);\n', '\tctx.quadraticCurveTo(6.000000, 10.000000, 6.000000, 10.000000);\n', '\tctx.lineTo(6.000000, 6.000000);\n', '\tctx.quadraticCurveTo(6.000000, 6.000000, 5.000000, 6.000000);\n', '\tctx.lineTo(5.000000, 6.000000);\n', '\tctx.quadraticCurveTo(4.000000, 6.000000, 4.000000, 6.000000);\n'])
        
    def testRectWithRXCtx(self):
        self.canvasWithContext.rect(4, 6, 2, 4, 1)
        self.assertEqual(self.canvasWithContext.code, ['\tfoo.moveTo(4.000000, 6.000000);\n', '\tfoo.lineTo(4.000000, 10.000000);\n', '\tfoo.quadraticCurveTo(4.000000, 10.000000, 5.000000, 10.000000);\n', '\tfoo.lineTo(5.000000, 10.000000);\n', '\tfoo.quadraticCurveTo(6.000000, 10.000000, 6.000000, 10.000000);\n', '\tfoo.lineTo(6.000000, 6.000000);\n', '\tfoo.quadraticCurveTo(6.000000, 6.000000, 5.000000, 6.000000);\n', '\tfoo.lineTo(5.000000, 6.000000);\n', '\tfoo.quadraticCurveTo(4.000000, 6.000000, 4.000000, 6.000000);\n'])
        
    def testLineTo(self):
        self.canvas.lineTo(4, 6)
        self.assertEqual(self.canvas.code, ["\tctx.lineTo(%f, %f);\n" % (4, 6)])
        
    def testLineToWithNewCtx(self):
        self.canvasWithContext.lineTo(4, 6)
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.lineTo(%f, %f);\n" % (4, 6)])
 
    def testMoveTo(self):
        self.canvas.moveTo(4, 6)
        self.assertEqual(self.canvas.code, ["\tctx.moveTo(%f, %f);\n" % (4, 6)])
        
    def testMoveToWithNewCtx(self):
        self.canvasWithContext.moveTo(4, 6)
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.moveTo(%f, %f);\n" % (4, 6)])
 
    def testSetStrokeMiterlimit(self):
        self.canvas.setStrokeMiterlimit("banana")
        self.assertEqual(self.canvas.code, ["\tctx.miterLimit = %s;\n" % "banana"])
        
    def testSetStrokeMiterlimitNewCtx(self):
        self.canvasWithContext.setStrokeMiterlimit("banana")
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.miterLimit = %s;\n" % "banana"])
        
    def testSetStrokeLinejoin(self):
        self.canvas.setStrokeLinejoin("banana")
        self.assertEqual(self.canvas.code, ["\tctx.lineJoin = '%s';\n" % "banana"])
        
    def testSetStrokeLinejoinNewCtx(self):
        self.canvasWithContext.setStrokeLinejoin("banana")
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.lineJoin = '%s';\n" % "banana"])
        
    def testSetStrokeLinecap(self):
        self.canvas.setStrokeLinecap("banana")
        self.assertEqual(self.canvas.code, ["\tctx.lineCap = '%s';\n" % "banana"])
        
    def testSetStrokeLinecapNewCtx(self):
        self.canvasWithContext.setStrokeLinecap("banana")
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.lineCap = '%s';\n" % "banana"])
    
    def testSetStrokeWidth(self):
        self.canvas.setStrokeWidth("2px")
        self.assertEqual(self.canvas.code, ["\tctx.lineWidth = %f;\n" % 2])
        
    def testSetStrokeWidthNewCtx(self):
        self.canvasWithContext.setStrokeWidth("2px")
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.lineWidth = %f;\n" % 2])

    def testQuadraticCurveTo(self):
        self.canvas.quadraticCurveTo(4, 6, 2.3, -4)
        self.assertEqual(self.canvas.code, ["\tctx.quadraticCurveTo(%f, %f, %f, %f);\n" % (4, 6, 2.3, -4)])
        
    def testQuadraticCurveToWithNewCtx(self):
        self.canvasWithContext.quadraticCurveTo(4, 6, 2, 4)
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.quadraticCurveTo(%f, %f, %f, %f);\n" % (4, 6, 2, 4)])
       
    def testFillText(self):
        self.canvas.fillText("batata", 4, 6)
        self.assertEqual(self.canvas.code, ["\tctx.fillText(\"%s\", %f, %f);\n" % ("batata", 4, 6)])
        
    def testFillTextWithNewCtx(self):
        self.canvasWithContext.fillText("batata", 4, 6)
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.fillText(\"%s\", %f, %f);\n" % ("batata", 4, 6)])
   
    def testSave(self):
        self.canvas.save()
        self.assertEqual(self.canvas.code, ["\tctx.save();\n"])
        
    def testSaveWithNewCtx(self):
        self.canvasWithContext.save()
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.save();\n"])
     
    def testClip(self):
        self.canvas.clip()
        self.assertEqual(self.canvas.code, ["\tctx.clip();\n"])
        
    def testClipWithNewCtx(self):
        self.canvasWithContext.clip()
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.clip();\n"]) 
    
    def testArc(self):
        self.canvas.arc(1, 2, 3, 4, 5, 1)
        self.assertEqual(self.canvas.code, ["\tctx.arc(%f, %f, %f, %f, %.8f, %d);\n" % (1, 2, 3, 4, 5, 1)])
        
    def testArcWithNewCtx(self):
        self.canvasWithContext.arc(1, 2, 3, 4, 5, 1)
        self.assertEqual(self.canvasWithContext.code, ["\tfoo.arc(%f, %f, %f, %f, %.8f, %d);\n" % (1, 2, 3, 4, 5, 1)])
    
    def testWriteCorrectInsertion(self):
        text = "ctx.Texto"
        self.canvas.write(text)
        self.assertEqual(self.canvas.code[0], "\t" + text + "\n")
    
    def testWriteCorrectInsertionWithNewCtx(self):
        text = "ctx.Texto"
        self.canvasWithContext.write(text)
        self.assertEqual(self.canvasWithContext.code[0], "\t" + text.replace("ctx", self.canvasWithContext.obj) + "\n")
    
    def testOutput(self):
        from textwrap import dedent
        output = self.canvas.output()
        expected_output = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
            <title>Inkscape Output</title>
        </head>
        <body>
            <canvas id='canvas' width='%d' height='%d'></canvas>
            <script>
            var %s = document.getElementById("canvas").getContext("2d");
            %s
            </script>
        </body>
        </html>
        """
        expected_output = dedent(expected_output) % (self.canvas.width, self.canvas.height, self.canvas.obj, "".join(self.canvas.code))
        self.assertEqual(output, expected_output)
    
    def testCreateLinearGradient(self):
        href = "str"
        x1, y1, x2, y2 = 0.0 , 2.0 , 3.0, 4.0
        data = (href, x1, y1, x2, y2)
        expectedList = ["\tvar %s = ctx.createLinearGradient(%f,%f,%f,%f);\n" % data]
        self.canvas.createLinearGradient(href,x1, y1, x2, y2)
        self.assertEqual(self.canvas.code, expectedList)          
    
    def testCreateRadialGradient(self):
        href = "str"
        cx1, cy1, rx, cx2, cy2, ry = 0.0 , 2.0, 3.0, 4.0, 5.0, 6.0
        data = (href, cx1, cy1, rx, cx2, cy2, ry)
        expectedList = ["\tvar %s = ctx.createRadialGradient(%f,%f,%f,%f,%f,%f);\n" % data]
        self.canvas.createRadialGradient(href, cx1, cy1, rx, cx2, cy2, ry)
        self.assertEqual(self.canvas.code, expectedList)
    
    def testAddColorStop(self):
        href, pos, color = "href" , 2.0, "color"
        data = (href, pos, color)
        expectedList = ["\t%s.addColorStop(%f, %s);\n" % data]
        self.canvas.addColorStop(href, pos, color)
        self.assertEqual(self.canvas.code, expectedList)
           
    def testSetOpacity(self):
        #Float Test
        value = 2.5
        expectedReturn = "\tctx.globalAlpha = %.1f;\n" % float(value)
        self.canvas.setOpacity(value)
        self.assertEqual(self.canvas.code[0], expectedReturn)
        
        #Integer Test
        value = 2
        expectedReturn = "\tctx.globalAlpha = %.1f;\n" % float(value)
        self.canvas.setOpacity(value)
        self.assertEqual(self.canvas.code[1], expectedReturn)
        
    def testSetFillNoOpacity(self):
        value = "url()"
        self.canvas.setFill(value)
        self.assertEqual(self.canvas.code, [])
        
        value = "0 0 255"
        fill = self.canvas.getColor(value, 1)
        self.canvas.setFill(value)
        self.assertEqual(self.canvas.code[0], "\tctx.fillStyle = %s;\n" % fill)
        
        value = "0 0 254"
        fill = self.canvas.getColor(value, 1)
        self.assertNotEqual(self.canvas.code[0], "\tctx.fillStyle = %s;\n" % fill)
        
    def testSetFillWithOpacity(self):
        self.canvas.style["fill-opacity"] = 0.5
        
        value = "url()"
        self.canvas.setFill(value)
        self.assertEqual(self.canvas.code, [])
        
        value = "0 0 255"
        fill = self.canvas.getColor(value, 0.5)
        self.canvas.setFill(value)
        self.assertEqual(self.canvas.code[0], "\tctx.fillStyle = %s;\n" % fill)
        
        value = "0 0 254"
        fill = self.canvas.getColor(value, 0.5)
        self.assertNotEqual(self.canvas.code[0], "\tctx.fillStyle = %s;\n" % fill)
        
    def testSetStroke(self):
        value = "0 0 255"
        self.canvas.setStroke(value)
        self.assertEqual(self.canvas.code[0], "\tctx.strokeStyle = %s;\n" % self.canvas.getColor(value, 1))
        
        value = "0 0 254"
        self.assertNotEqual(self.canvas.code[0], "\tctx.strokeStyle = %s;\n" % self.canvas.getColor(value, 1))
        
        self.canvas.style["stroke-opacity"] = 0.5
        
        value = "0 0 255"
        self.canvas.setStroke(value)
        self.assertEqual(self.canvas.code[1], "\tctx.strokeStyle = %s;\n" % self.canvas.getColor(value, 0.5))
        
        value = "0 0 254"
        self.assertNotEqual(self.canvas.code[0], "\tctx.strokeStyle = %s;\n" % self.canvas.getColor(value, 0.5))

    def testSetFont(self):
        value = "Fonte"
        self.canvas.setFont(value)
        self.assertEqual(self.canvas.code[0],"\tctx.font = \"%s\";\n" % value)
    
    def testTranslate(self):
        cx = cy = 1.0
        self.canvas.translate(cx, cy)
        self.assertEqual(self.canvas.code[0],"\tctx.translate(%f, %f);\n" % (cx, cy))
        
    def testRotate(self):
        angle = 1.0
        self.canvas.rotate(angle)
        self.assertEqual(self.canvas.code[0],"\tctx.rotate(%f);\n" % angle)

    def testsScale(self):
        rx, ry = 1.0, 2.0
        self.canvas.scale(rx, ry)
        self.assertEqual(self.canvas.code[0],"\tctx.scale(%f, %f);\n" % (rx, ry))

    def testsTransform(self):
        m11, m12, m21, m22, dx, dy = 1.0, 2.0, 3.0, 4.0, 5.0, 6.0
        self.canvas.transform(m11, m12, m21, m22, dx, dy)
        self.assertEqual(self.canvas.code[0],"\tctx.transform(%f, %f, %f, %f, %f, %f);\n" % (m11, m12, m21, m22, dx, dy))
                                    
    def testRestore(self):
        self.canvas.restore()
        self.assertEqual(self.canvas.code[0],"\tctx.restore();\n")
                    
    def testClosePath(self):
        text = "ctx.closePath();"
        self.canvas.closePath(False)
        self.assertEquals(self.canvas.code, [])
        
        self.canvas.closePath(True)                                    
        self.assertEqual(self.canvas.code[0],"\t"+text+"\n")
        
    def testFillWithValue(self):
        text = "ctx.fill();"
        self.canvas.style["fill"] = "fill"
        self.canvas.fill()
        self.assertEqual(self.canvas.code[0],"\t"+text+"\n")
    
    def testFillWithoutValue(self):
        self.canvas.style["fill"] = "none"
        self.canvas.fill()
        self.assertEqual(self.canvas.code,[])
    
    def testStrokeWithValue(self):
        text = "ctx.stroke();"
        self.canvas.style["stroke"] = "stroke"
        self.canvas.stroke()
        self.assertEqual(self.canvas.code[0],"\t"+text+"\n")
    
    def testStrokeWithoutValue(self):
        self.canvas.style["stroke"] = "none"
        self.canvas.stroke()
        self.assertEqual(self.canvas.code,[])
        
        
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = unit_test_svg_abstractShape
import sys
import unittest

sys.path.append('..')
from inkex import Effect
from ink2canvas.svg.AbstractShape import AbstractShape
from ink2canvas.svg.Rect import Rect
from ink2canvas.canvas import Canvas


class TestSvgAbstractShape(unittest.TestCase):
    
    def returnsGnode(self, root, tag):
        for node in root:
            nodeTag = node.tag.split("}")[1]
            if(nodeTag == 'g'):
                root = node
                break
        for node in root:
            nodeTag = node.tag.split("}")[1]
            if(nodeTag == tag):
                return node

    def setUp(self):
        self.canvas = Canvas(0,0)
        self.effect = Effect()
        self.document = self.effect.parse("TestFiles/unit_test_svg_abstractShape.svg")
        self.root = self.effect.document.getroot()
        self.node = self.returnsGnode(self.root,"path")
        self.abstractShape = AbstractShape( None,self.node,self.canvas, None)

    def testGetStyle(self):
        style = self.abstractShape.getStyle()
        strStyle = "fill:#ff0000;fill-rule:evenodd;stroke:#000000;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1"
        hashStyle = dict([i.split(":") for i in strStyle.split(";") if len(i)])
        self.assertEqual(hashStyle,style)

        strStyle = "fill:ff0000;fill-rule:evenodd;stroke:#000000;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1"
        hashStyle = dict([i.split(":") for i in strStyle.split(";") if len(i)])
        self.assertNotEqual(hashStyle,style)

    def testSetStyle(self):
        canvas = Canvas(0,0)
        canvas.setStrokeLinejoin("miter")
        canvas.setStroke("#000000")
        canvas.setStrokeLinecap("butt")
        canvas.setStrokeWidth("1px")
        canvas.setFill("#ff0000")
                      
        stringStyle =self.abstractShape.getStyle() 
        self.abstractShape.setStyle(stringStyle)
        
        self.assertEqual(canvas.code, self.abstractShape.canvasContext.code)
        self.assertEqual(self.abstractShape.canvasContext.style,stringStyle) 
        
    def testHasTransform(self):
        self.assertNotEqual(True, self.abstractShape.hasTransform())
        
        canvas = Canvas(0,1)
        canvas.effect = Effect()
        canvas.document = canvas.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado.svg")
        canvas.root = canvas.effect.document.getroot()
        canvas.node = self.returnsGnode(canvas.root,"rect")
        canvas.abstractShape = AbstractShape( None,canvas.node,self.canvas, None)
        
        self.assertEqual(True, canvas.abstractShape.hasTransform())

    def testGetTransform(self):
        
        m11 = (float(1),float(0),float(0.3802532),float(0.92488243),0.0,0.0)
        
        canvas = Canvas(0,1)
        canvas.effect = Effect()
        canvas.document = canvas.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado.svg")
        canvas.root = canvas.effect.document.getroot()
        canvas.node = self.returnsGnode(canvas.root,"rect")
        canvas.abstractShape = AbstractShape( None,canvas.node,self.canvas, None)
        
        vetor = canvas.abstractShape.getTransform()
        
        self.assertEqual(m11, vetor)
        
    def testHasGradient(self):
        
        canvas = Canvas(0,1)
        canvas.effect = Effect()
        canvas.document = canvas.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado_GradienteLinear.svg")
        canvas.root = canvas.effect.document.getroot()
        canvas.node = self.returnsGnode(canvas.root,"path")
        canvas.abstractShape = AbstractShape( None,canvas.node,self.canvas, None)
        
        self.assertEqual(canvas.abstractShape.gradientHelper.hasGradient("fill"), "linear")
        
        canvas.document = canvas.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado_GradienteRadial.svg")
        canvas.root = canvas.effect.document.getroot()
        canvas.node = self.returnsGnode(canvas.root,"path")
        canvas.abstractShape = AbstractShape( None,canvas.node,self.canvas, None)
        
        self.assertEqual(canvas.abstractShape.gradientHelper.hasGradient("fill"), "radial")
        
        self.assertNotEqual(self.abstractShape.gradientHelper.hasGradient("fill"),"linear")
        
    def testGetGradientHref(self):
        returnValue ="linearGradient3022"
        canvas = Canvas(0,1)
        canvas.effect = Effect()
        canvas.document = canvas.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado_GradienteLinear.svg")
        canvas.root = canvas.effect.document.getroot()
        canvas.node = self.returnsGnode(canvas.root,"path")
        canvas.abstractShape = AbstractShape( None,canvas.node,self.canvas, None)
        
        self.assertEqual(returnValue,canvas.abstractShape.gradientHelper.getGradientHref("fill"))
        
        returnValue ="ovalGradient3022"
        self.assertNotEqual(returnValue,canvas.abstractShape.gradientHelper.getGradientHref("fill"))
    
    def testHasClip(self):
        canvas = Canvas(0,1)
        canvas.effect = Effect()
        canvas.document = canvas.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado_Clip.svg")
        canvas.root = canvas.effect.document.getroot()
        canvas.node = self.returnsGnode(canvas.root,"path")
        canvas.abstractShape = AbstractShape( None,canvas.node,self.canvas, None)
        
        self.assertTrue(canvas.abstractShape.hasClip())
        self.assertFalse(self.abstractShape.hasClip())
        
    def testGetClipHref(self):
        returnValue = "clipPath3191"
        canvas = Canvas(0,1)
        canvas.effect = Effect()
        canvas.document = canvas.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado_Clip.svg")
        canvas.root = canvas.effect.document.getroot()
        canvas.node = self.returnsGnode(canvas.root,"path")
        canvas.abstractShape = AbstractShape( None,canvas.node,self.canvas, None)
        
        self.assertEqual(canvas.abstractShape.getClipId(),returnValue)
        
    def testStart(self):
        canvas2 = Canvas(0,2)
        canvas2.write("\n// #path3033")
        self.abstractShape.initDraw()
        
        self.assertEqual(self.abstractShape.canvasContext.code,canvas2.code)

        canvas3 = Canvas(0,3)
        canvas3.effect = Effect()
        canvas3.document = canvas3.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado_Clip.svg")
        canvas3.root = canvas3.effect.document.getroot()
        canvas3.node = self.returnsGnode(canvas3.root,"path")
        canvas3.abstractShape = AbstractShape( None,canvas3.node,canvas3, None)
        
        canvas4 = Canvas(0,4)
        canvas4.write("\n// #path2987")
        canvas4.save()
               
        canvas3.abstractShape.initDraw()
        self.assertEqual(canvas3.abstractShape.canvasContext.code,canvas4.code)
                        
    def testDraw(self):
        canvas = Canvas(0,1)
        canvas.effect = Effect()
        canvas.document = canvas.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado.svg")
        canvas.root = canvas.effect.document.getroot()
        canvas.node = self.returnsGnode(canvas.root,"rect")
        rect = Rect("rect",canvas.node,canvas, None)
        
        rect.draw()
        
        self.assertEqual(rect.canvasContext.code,['\tctx.transform(1.000000, 0.000000, 0.380253, 0.924882, 0.000000, 0.000000);\n', "\tctx.lineJoin = 'miter';\n", "\tctx.strokeStyle = 'rgb(0, 0, 0)';\n", "\tctx.lineCap = 'butt';\n", '\tctx.lineWidth = 1.012632;\n', "\tctx.fillStyle = 'rgb(0, 0, 255)';\n", '\tctx.beginPath();\n', '\tctx.moveTo(-60.184902, 299.915122);\n', '\tctx.lineTo(-60.184902, 677.860048);\n', '\tctx.quadraticCurveTo(-60.184902, 683.719660, -60.184902, 683.719660);\n', '\tctx.lineTo(431.239998, 683.719660);\n', '\tctx.quadraticCurveTo(431.239998, 683.719660, 431.239998, 677.860048);\n', '\tctx.lineTo(431.239998, 299.915122);\n', '\tctx.quadraticCurveTo(431.239998, 294.055510, 431.239998, 294.055510);\n', '\tctx.lineTo(-60.184902, 294.055510);\n', '\tctx.quadraticCurveTo(-60.184902, 294.055510, -60.184902, 299.915122);\n', '\tctx.fill();\n', '\tctx.stroke();\n'])
        
    def testEnd(self):
        self.abstractShape.endDraw()
        self.assertEqual(self.abstractShape.canvasContext.code, [])
        
        canvas1 = Canvas(0,3)
        canvas1.effect = Effect()
        canvas1.document = canvas1.effect.parse("TestFiles/unit_test_svg_abstractShape_transformado.svg")
        canvas1.root = canvas1.effect.document.getroot()
        canvas1.node = self.returnsGnode(canvas1.root,"rect")
        canvas1.abstractShape = AbstractShape( None,canvas1.node,canvas1, None)
        canvas1.abstractShape.endDraw()
        
        canvas2 = Canvas(0,2)
        canvas2.restore()
        
        self.assertEqual(canvas1.abstractShape.canvasContext.code, canvas2.code)
         
        
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = unit_test_svg_circle
import sys
import unittest

sys.path.append('..') 
from inkex import Effect
from ink2canvas.svg.Circle import Circle


class TestSvgCircle(unittest.TestCase):
    def setUp(self):
        self.circle = Circle(12, 12, 12, None)
        self.effect = Effect()
        self.document = self.effect.parse("TestFiles/unit_test_svg_circle.svg")
        root = self.effect.document.getroot()
        
        for node in root:
            tag = node.tag.split("}")[1]
            if(tag == 'circle'):
                self.node = node
                break
 
    def testGetDataCx(self):
        self.circle.node = self.node
        data = self.circle.getData()
        self.assertEqual(data[0], 600)
        
    def testGetDataCy(self):
        self.circle.node = self.node
        data = self.circle.getData()
        self.assertEqual(data[1], 200)
        
    def testGetDataR(self):
        self.circle.node = self.node
        data = self.circle.getData()
        self.assertEqual(data[2], 100)

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = unit_test_svg_clone
import unittest

from ink2canvas.main import Ink2Canvas
from ink2canvas.svg import Use, G


class TestSvgClone(unittest.TestCase):
    
    def setUp(self):
        self.ink2canvas = Ink2Canvas()
        svgInput = "TestFiles/unit_test_clone_quadrados.svg"
        self.ink2canvas.parse(svgInput)
        self.ink2canvas.effect()
        self.root = self.ink2canvas.core.root 
        self.ListofUses = []
                
    def createUseList(self, nodesThatShouldBeDrawn):
       
        for presentNode in nodesThatShouldBeDrawn:
            if(isinstance(presentNode, Use)):
                self.ListofUses.append(presentNode)
            if(isinstance(presentNode, G)):
                self.createUseList(presentNode.children)
                    
    def searchForUSETag(self, nodesThatShouldBeDrawn):
        returnValue = False
        for presentNode in nodesThatShouldBeDrawn:
            if(isinstance(presentNode, Use)):
                return True
            if(isinstance(presentNode, G)):
                returnValue = self.searchForUSETag(presentNode.children)
                if(returnValue):
                    break
        return returnValue
        
    def testCloneCreate(self):
        rootTree = self.root
        boolean = self.searchForUSETag(rootTree.getDrawable())
        self.assertEqual(boolean, True) 
    
    def testSearchCloneId(self):
        self.createUseList(self.root.getDrawable())
        for eachUSETag in self.ListofUses:
            targetId = eachUSETag.getCloneId()
            self.assertIsNotNone(targetId)
            IdElement = self.ink2canvas.core.root.searchElementById(targetId, self.root.getDrawable())
            self.assertIsNotNone(IdElement)
    
    def testCLoneBuffer(self):
        svg_input = "TestFiles/unit_test_clone_identico.svg"
        self.ink2canvas.parse(svg_input)
        self.ink2canvas.effect()
        self.root = self.ink2canvas.core.root 
        self.ListofUses = []
        pass
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testCLoneCreate']
    unittest.main()

########NEW FILE########
__FILENAME__ = unit_test_svg_element
import sys
import unittest

sys.path.append('..')
from inkex import Effect
from ink2canvas.svg.Element import Element


class TestSvgElement(unittest.TestCase):
    def setUp(self):
        self.element = Element()
        self.effect = Effect()
        self.document = self.effect.parse("TestFiles/unit_test_svg_element.svg")
        self.node = self.effect.document.getroot()
        
    def testAttrWithNs(self):
        self.element.node = self.node
        returnValue = self.element.attr("width", "ns")
        self.assertEqual(returnValue, "12cm")
        
        
    def testAttrWithoutNs(self):
        self.element.node = self.node
        returnValue = self.element.attr("width")
        self.assertEqual(returnValue, "12cm")
   
if __name__ == '__main__':
    unittest.main()
    

########NEW FILE########
__FILENAME__ = unit_test_svg_ellipse
import sys
import unittest

sys.path.append('..')
from inkex import Effect
from ink2canvas.canvas import Canvas
from ink2canvas.svg.Ellipse import Ellipse


class TestSvgEllipse(unittest.TestCase):
    def setUp(self):
        self.effect = Effect()
        self.document = self.effect.parse("TestFiles/unit_test_svg_ellipse.svg")
        root = self.effect.document.getroot()
        self.node = self.findTag(root, "ellipse")
        self.canvas = Canvas(0, 0)    
        self.ellipse = Ellipse(None, self.node, self.canvas, None)
        
    def findTag(self, root, no):
        for node in root:
            tag = node.tag.split("}")[1]
            if tag == no:
                return node
        return ""  
 
    def testGetData(self):
        x, y, z, w = self.ellipse.getData()
        self.assertEqual(x, 60)
        self.assertEqual(y, 70)
        self.assertEqual(z, 250)
        self.assertEqual(w, 100)
        
    def testDraw(self):
        self.ellipse.draw(False)
        self.assertEqual(self.ellipse.canvasContext.code, ["\tctx.fillStyle = 'rgb(255, 0, 0)';\n", '\tctx.beginPath();\n', '\tctx.transform(0.866025, -0.500000, 0.500000, 0.866025, 900.000000, 200.000000);\n', '\tctx.moveTo(60.000000, -30.000000);\n', '\tctx.bezierCurveTo(198.071187, -30.000000, 310.000000, 14.771525, 310.000000, 70.000000);\n', '\tctx.bezierCurveTo(310.000000, 125.228475, 198.071187, 170.000000, 60.000000, 170.000000);\n', '\tctx.bezierCurveTo(-78.071187, 170.000000, -190.000000, 125.228475, -190.000000, 70.000000);\n', '\tctx.bezierCurveTo(-190.000000, 14.771525, -78.071187, -30.000000, 60.000000, -30.000000);\n', '\tctx.fill();\n'])
        
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = unit_test_svg_g
import unittest
import sys

sys.path.append('..')
from inkex import Effect
from ink2canvas.svg.G import G
from ink2canvas.canvas import Canvas


class TestSvgG(unittest.TestCase):

    def setUp(self):
        self.effect = Effect()
        
        self.document = self.effect.parse("TestFiles/unit_test_svg_g.svg")
        root = self.effect.document.getroot()   
        self.node = self.findTag(root, "g")
            
        self.canvas = Canvas(0, 0)
        self.g = G(None, self.node, self.canvas, None)

    def findTag(self, root, no):
        for node in root:
            tag = node.tag.split("}")[1]
            if tag == no:
                return node
        return ""   

    def testDraw(self):
        self.g.draw(False);
        self.assertEqual(self.g.canvasContext.code, ['\tctx.transform(-0.866025, 0.500000, -0.500000, -0.866025, 0.000000, 0.000000);\n'])

if __name__ == "__main__":
    unittest.main()
########NEW FILE########
__FILENAME__ = unit_test_svg_group
import sys
import unittest

sys.path.append('..')
from ink2canvas.main import Ink2Canvas


class TestSvgGroup(unittest.TestCase):
    def setUp(self):
        self.ink2canvasGrouped = Ink2Canvas()
        file2 = "TestFiles/unit_test_group_grouped.svg"
        self.ink2canvasGrouped.parse(file2)
        self.ink2canvasGrouped.effect()

        self.ink2canvasGroupedEdited = Ink2Canvas()
        file3 = "TestFiles/unit_test_group_grouped_edited.svg"
        self.ink2canvasGroupedEdited.parse(file3)
        self.ink2canvasGroupedEdited.effect()

    def testCompareUngroupedAndGroupedEquals(self):
        self.assertEquals(self.ink2canvasGroupedEdited.core.canvas.output(), 
                          self.ink2canvasGrouped.core.canvas.output())
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = unit_test_svg_image
import sys
import unittest

sys.path.append('..')
from inkex import Effect
from ink2canvas.canvas import Canvas
from ink2canvas.svg.Image  import Image


class TestSvg_image_unit_test(unittest.TestCase):


    def setUp(self):
        self.effect = Effect()
        self.document = self.effect.parse("TestFiles/unit_test_image2.svg")
        root = self.effect.document.getroot()   
        self.node = self.findTag(root, "g")
        self.node = self.findTag(self.node, "image")    
        self.canvas = Canvas(0, 0)
        self.image = Image(None, self.node, self.canvas, None);
        
    def findTag(self, root, no):
        for node in root:
            tag = node.tag.split("}")[1]
            if tag == no:
                return node
        return ""   
    
    def testGetData(self):
        x, y, weight, height, href = self.image.get_data()
        href = href[-12:]
        array = [x ,y, weight, height, href]
        imageArray = [97.285713, 255.6479, 554, 422, "5_images.jpg"]
        self.assertEqual(array, imageArray)
        
if __name__ == '__main__':
    unittest.main()      
########NEW FILE########
__FILENAME__ = unit_test_svg_Ink2CanvasCore

import unittest
import sys

sys.path.append('..')


class TestSvgInk2Canvas(unittest.TestCase):

    def setUp(self):
        pass

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = unit_test_svg_line
import sys
import unittest

sys.path.append('..')
from inkex import Effect
from ink2canvas.canvas import Canvas
from ink2canvas.svg.Line import Line


class TestSvgLine(unittest.TestCase):
    def setUp(self):
        self.effect = Effect()
        self.document = self.effect.parse("TestFiles/unit_test_svg_line.svg")
        root = self.effect.document.getroot()
        self.node = self.findTag(root, "line")

        self.canvas = Canvas(0, 0)    
        self.line = Line(None, self.node, self.canvas, None)
        
    def findTag(self, root, no):
        for node in root:
            tag = node.tag.split("}")[1]
            if tag == no:
                return node
        return ""  
 
    def testGetData(self):
        x, y = self.line.getData()
        self.assertEqual(x, ('M', (100.0, 300.0)) )
        self.assertEqual(y, ('L', (300.0, 100.0)) )
        
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = unit_test_svg_linearGradient
import sys
import unittest
import filecmp

sys.path.append('..')
from ink2canvas.main import Ink2Canvas


class TestSvgLinearGradient(unittest.TestCase):
    
    def setUp(self):
        self.ink2canvas = Ink2Canvas()
        file = "TestFiles/unit_test_svg_linearGradient.svg"
        self.ink2canvas.parse(file)
        self.ink2canvas.effect()
        
    def testIfTheLinearGradientNodeIsCreated(self):
        linearGradientDictionary = self.ink2canvas.core.root.linearGradient
        for linearGradientKey, linearGradientValue in linearGradientDictionary.iteritems():
            if linearGradientValue.link == None:
                self.assertNotEqual([], linearGradientValue.colorStops)
            else:
                self.assertNotEqual(None, linearGradientValue.link)
        
    def testIfLinearGradientColorsAreCorrect(self):
        linearGradientDictionary = self.ink2canvas.core.root.linearGradient
        self.assertEqual(linearGradientDictionary["linearGradient2987"].colorStops["1"], "stop-color:#80e900;stop-opacity:1;") 
        self.assertEqual(linearGradientDictionary["linearGradient2987"].colorStops["0.5"], "stop-color:#807400;stop-opacity:1;") 
        self.assertEqual(linearGradientDictionary["linearGradient2987"].colorStops["0"], "stop-color:#800000;stop-opacity:1;")
    
    def testSetLinearGradient(self):
        output_file = open("TestFiles/unit_test_svg_linearGradient.html", "w")
        content = self.ink2canvas.core.canvas.output()
        output_file.write(content.encode("utf-8"))
        output_file.close()
        self.assertTrue(filecmp.cmp("TestFiles/unit_test_svg_linearGradient.html", "TestFiles/unit_test_svg_linearGradientQueDeveriaSair.html"))

    
if __name__ == "__main__":
    unittest.main()
########NEW FILE########
__FILENAME__ = unit_test_svg_path
import sys
import unittest

sys.path.append('..')
from inkex import Effect
from ink2canvas.canvas import Canvas
from ink2canvas.svg.Path import Path


class TestSvgPath(unittest.TestCase):
    def setUp(self):
        self.effect = Effect()
        self.document = self.effect.parse("TestFiles/unit_test_svg_path.svg")
        root = self.effect.document.getroot()   
        self.node = self.findTag(root, "g")
        self.node = self.findTag(self.node, "path")    
        self.canvas = Canvas(0, 0)
        '''Fictional data used in methods such as pathlineto, pathcurveto, pathmoveto, patharcto. we made it so that
        the 5th parameters (600) is larger then the others, guaranteeing this way that the sqrt value is not a negative
        value in patharcto.'''
        self.data =[1.0, 2.0, 3.0, 4.0, 5.0, 600.0, 7.0]
        self.path = Path(None, self.node, self.canvas, None)
        
    def findTag(self, root, no):
        for node in root:
            tag = node.tag.split("}")[1]
            if tag == no:
                return node
        return ""   
    
    def testGetData(self):
        vetor = self.path.getData()
        vetorDaElipse = [['M', [447.49757, 166.4584]], ['A', [197.48482, 67.680222, 0.0, 1, 1, 52.527939, 166.4584]], ['A', [197.48482, 67.680222, 0.0, 1, 1, 447.49757, 166.4584]], ['Z', []]]
        self.assertEqual(vetor, vetorDaElipse)
        
    def testPathMoveTo(self):
        self.path.pathMoveTo(self.data)
        self.assertEqual(self.path.canvasContext.code, ['\tctx.moveTo(1.000000, 2.000000);\n'])

        
    def testPathLineTo(self):
        self.path.pathLineTo(self.data)
        self.assertEqual(self.path.canvasContext.code, ['\tctx.lineTo(1.000000, 2.000000);\n'])
        
    def testPathCurveTo(self):
        self.path.pathCurveTo(self.data)
        self.assertEqual(self.path.canvasContext.code, ['\tctx.bezierCurveTo(1.000000, 2.000000, 3.000000, 4.000000, 5.000000, 600.000000);\n'])
        
    def testPathArcTo(self):         
        self.path.currentPosition = [600.0, 7.0]
        self.path.pathArcTo(self.data)
        self.assertEqual(self.path.canvasContext.code, [])
        self.path.currentPosition = [0.25, 0.25]
        self.path.pathArcTo(self.data)
        self.assertEqual(self.path.canvasContext.code, ['\tctx.translate(300.125000, 3.625000);\n', '\tctx.rotate(0.052360);\n', '\tctx.scale(0.500000, 1.000000);\n', '\tctx.arc(0.000000, 0.000000, 599.408034, 3.121031, 6.26262379, -4);\n', '\tctx.scale(2.000000, 1.000000);\n', '\tctx.rotate(-0.052360);\n', '\tctx.translate(-300.125000, -3.625000);\n'])

    def testDraw(self):
        self.maxDiff = None
        self.path.draw(False)
        self.assertEqual(self.path.canvasContext.code, ["\tctx.lineJoin = 'miter';\n", "\tctx.strokeStyle = 'rgb(0, 0, 0)';\n", "\tctx.lineCap = 'butt';\n", '\tctx.lineWidth = 1.000000;\n', "\tctx.fillStyle = 'rgb(255, 0, 0)';\n", '\tctx.beginPath();\n', '\tctx.transform(0.707107, -0.707107, 0.707107, 0.707107, -44.476826, 225.540250);\n', '\tctx.moveTo(447.497570, 166.458400);\n', '\tctx.translate(250.012754, 166.472848);\n', '\tctx.rotate(0.000000);\n', '\tctx.scale(1.000000, 0.342711);\n', '\tctx.arc(0.000000, 0.000000, 197.484820, -0.000213, 3.14180613, 0);\n', '\tctx.scale(1.000000, 2.917910);\n', '\tctx.rotate(-0.000000);\n', '\tctx.translate(-250.012754, -166.472848);\n', '\tctx.translate(250.012754, 166.443952);\n', '\tctx.rotate(0.000000);\n', '\tctx.scale(1.000000, 0.342711);\n', '\tctx.arc(0.000000, 0.000000, 197.484820, 3.141379, 6.28339879, 0);\n', '\tctx.scale(1.000000, 2.917910);\n', '\tctx.rotate(-0.000000);\n', '\tctx.translate(-250.012754, -166.443952);\n', '\tctx.closePath();\n', '\tctx.fill();\n', '\tctx.stroke();\n'])
       
if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = unit_test_svg_rect

import unittest
import sys

sys.path.append('..')
from inkex import Effect
from ink2canvas.svg.Rect import Rect
from ink2canvas.canvas import Canvas


class TestRect(unittest.TestCase):
    def setUp(self):
        self.effect = Effect()
        self.document = None
        self.effect.parse("TestFiles/unit_test_svg_Rect_WithRxRy.svg")
        self.node = None
        self.canvas = Canvas(0, 0)
              
    def findNodeInG(self, root, tag):
        for node in root:
            nodeTag = node.tag.split("}")[1]
            if(nodeTag == 'g'):
                root = node
                break
        for node in root:
            nodeTag = node.tag.split("}")[1]
            if(nodeTag == tag):
                return node
        
    def testExitWithoutRxRy(self):
        self.document = self.effect.parse("TestFiles/unit_test_svg_Rect_WithoutRxRy.svg")
        root = self.effect.document.getroot()
        self.rect = Rect(None, self.node, self.canvas, None)
        self.rect.node = self.findNodeInG(root, 'rect')
        x, y, w, h, rx, ry = self.rect.getData()
        self.assertEqual(x, 40.0)
        self.assertEqual(y, 30.0)
        self.assertEqual(w, 100.0)
        self.assertEqual(h, 150.0)
        self.assertEqual(rx, 0)
        self.assertEqual(ry, 0)
        
    def testExitWithRxRy(self):
        self.document = self.effect.parse("TestFiles/unit_test_svg_Rect_WithRxRy.svg")
        root = self.effect.document.getroot()
        self.rect = Rect(None, self.node, self.canvas, None)
        self.rect.node = self.findNodeInG(root, 'rect')
        x, y, w, h, rx, ry = self.rect.getData()
        self.assertEqual(x, 40.0)
        self.assertEqual(y, 30.0)
        self.assertEqual(w, 100.0)
        self.assertEqual(h, 150.0)
        self.assertEqual(rx, 5.0)
        self.assertEqual(ry, 10.0)
    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
########NEW FILE########
__FILENAME__ = unit_test_svg_text
import sys
import unittest

sys.path.append('..')
from inkex import Effect
from ink2canvas.svg.Text import Text
from ink2canvas.canvas import Canvas

class TestText(unittest.TestCase):
    
    def setUp(self):
        self.effect = Effect()
        self.document = self.effect.parse("TestFiles/unit_test_svg_text.svg")
        self.root = self.effect.document.getroot()
        self.canvas = Canvas(0,0)
        self.node = self.findNodeInG(self.root,"text")   
        self.text = Text( None,self.node,self.canvas, None)

    def findNodeInG(self, root, tag):
        for node in root:
            nodeTag = node.tag.split("}")[1]
            if(nodeTag == 'g'):
                root = node
                break
        for node in root:
            nodeTag = node.tag.split("}")[1]
            if(nodeTag == tag):
                return node

    def testGetData(self):
        x, y = self.text.getData()
        self.assertEqual(x, 188.89853)
        self.assertEqual(y, 117.97108)
    
    def testTextHelper(self):
        stringRetornada = self.text.textHelper(self.node)
        self.assertEqual(stringRetornada, "TESTE\n  ")
        
        
    def testSetTextStyle(self):
        self.text.setTextStyle(self.text.getStyle())
        self.assertEqual(self.text.canvasContext.code, ['\tctx.font = "normal normal 40px Sans";\n'])
    
    def testDraw(self):
        self.text.draw(False)
        self.assertEqual(self.text.canvasContext.code, ['\tctx.transform(0.707107, -0.707107, 0.707107, 0.707107, -44.476826, 225.540250);\n', "\tctx.fillStyle = 'rgb(0, 0, 0)';\n", '\tctx.font = "normal normal 40px Sans";\n', '\tctx.fillText("TESTE", 188.898530, 117.971080);\n'])
    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
